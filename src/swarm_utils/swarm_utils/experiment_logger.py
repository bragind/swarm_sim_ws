#!/usr/bin/env python3
"""Experiment logger with separate time-series and final CSV outputs."""
import csv
import json
import math
import os
import time
from datetime import datetime, timezone

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from swarm_msgs.msg import ExperimentMetrics, SwarmState


FINAL_FIELDS = [
    'run_id', 'scenario_id', 'experiment_profile', 'success_criteria_profile',
    'simulation_mode', 'architecture_requested', 'architecture', 'architecture_effective', 'seed',
    'num_agents', 'num_uavs', 'num_ugvs', 'start_time', 'end_time',
    'mission_time_s', 'mission_timeout_s', 'success_flag', 'timeout_flag',
    'mission_timeout_reached', 'runner_timeout_reached', 'scenario_completed',
    'complete_reason', 'collisions_count', 'total_energy_wh', 'avg_latency_ms',
    'packet_loss_ratio', 'connectivity_coeff_mean', 'connectivity_coeff_min',
    'coverage_ratio', 'agents_failed_count', 'marl_model_path', 'marl_model_exists',
    'marl_model_loaded', 'marl_model_allowed_for_proof', 'marl_model_type',
    'validity_class'
]

TIMESERIES_FIELDS = [
    'run_id', 'scenario_id', 'experiment_profile', 'architecture', 'architecture_effective',
    'seed', 'timestamp',
    'mission_time_s', 'collisions_count', 'total_energy_wh', 'avg_latency_ms',
    'packet_loss_ratio', 'connectivity_coeff', 'coverage_ratio',
    'active_agents', 'failed_agents'
]


class ExperimentLogger(Node):
    def __init__(self):
        super().__init__('experiment_logger')
        self.declare_parameter('log_dir', os.path.expanduser('~/sim_storage/experiments'))
        self.declare_parameter('log_path', '')
        self.declare_parameter('run_id', '')
        self.declare_parameter('scenario_id', 'S1')
        self.declare_parameter('architecture', '')
        self.declare_parameter('architecture_id', '')
        self.declare_parameter('architecture_effective', '')
        self.declare_parameter('experiment_profile', 'full')
        self.declare_parameter('success_criteria_profile', 'full')
        self.declare_parameter('simulation_mode', 'gazebo_headless')
        self.declare_parameter('seed', 42)
        self.declare_parameter('num_agents', 8)
        self.declare_parameter('num_uavs', 5)
        self.declare_parameter('num_ugvs', 3)
        self.declare_parameter('mission_timeout_s', 120.0)
        self.declare_parameter('logger_timeout_s', 0.0)
        self.declare_parameter('marl_model_loaded', False)
        self.declare_parameter('marl_model_path', '')
        self.declare_parameter('marl_model_exists', False)
        self.declare_parameter('marl_model_allowed_for_proof', False)
        self.declare_parameter('marl_model_type', 'unknown')
        self.declare_parameter('validity_class', '')

        self.log_dir = str(self.get_parameter('log_dir').value or self.get_parameter('log_path').value)
        self.run_id = str(self.get_parameter('run_id').value) or self._default_run_id()
        self.scenario_id = str(self.get_parameter('scenario_id').value)
        self.architecture = str(self.get_parameter('architecture').value or self.get_parameter('architecture_id').value)
        self.architecture_requested = self.architecture
        self.architecture_effective = str(self.get_parameter('architecture_effective').value or self.architecture)
        self.experiment_profile = str(self.get_parameter('experiment_profile').value)
        self.success_criteria_profile = str(self.get_parameter('success_criteria_profile').value)
        self.simulation_mode = str(self.get_parameter('simulation_mode').value)
        self.seed = int(self.get_parameter('seed').value)
        self.num_agents = int(self.get_parameter('num_agents').value)
        self.num_uavs = int(self.get_parameter('num_uavs').value)
        self.num_ugvs = int(self.get_parameter('num_ugvs').value)
        self.timeout_s = float(self.get_parameter('mission_timeout_s').value)
        self.logger_timeout_s = float(self.get_parameter('logger_timeout_s').value) or self.timeout_s + 5.0
        self.marl_model_loaded = as_bool(self.get_parameter('marl_model_loaded').value)
        self.marl_model_path = str(self.get_parameter('marl_model_path').value)
        self.marl_model_exists = as_bool(self.get_parameter('marl_model_exists').value)
        self.marl_model_allowed_for_proof = as_bool(self.get_parameter('marl_model_allowed_for_proof').value)
        self.marl_model_type = str(self.get_parameter('marl_model_type').value)
        self.initial_validity_class = str(self.get_parameter('validity_class').value)

        os.makedirs(self.log_dir, exist_ok=True)
        self.final_csv = os.path.join(self.log_dir, 'final_metrics.csv')
        self.timeseries_csv = os.path.join(self.log_dir, 'timeseries_metrics.csv')

        self.start_time = time.time()
        self.end_time = None
        self.final_written = False
        self.last_metrics = {}
        self.connectivity_samples = []
        self.baseline_collisions = 0
        self.baseline_energy = 0.0

        self.create_subscription(String, '/swarm/metrics_json', self.metrics_json_callback, 10)
        self.create_subscription(ExperimentMetrics, '/swarm/metrics', self.metrics_callback, 10)
        self.create_subscription(SwarmState, '/swarm/state', self.state_callback, 10)
        self.create_subscription(String, '/agent/architecture_info', self.arch_info_callback, 10)
        self.create_subscription(String, '/experiment/complete', self.complete_callback, 10)
        self.start_pub = self.create_publisher(String, '/experiment/start', 10)
        self.create_timer(0.2, self.publish_start_once)
        self.create_timer(1.0, self.timeout_check)

        self._ensure_header(self.final_csv, FINAL_FIELDS)
        self._ensure_header(self.timeseries_csv, TIMESERIES_FIELDS)
        self.get_logger().info(f'Logging run {self.run_id} to {self.log_dir}')

    def _default_run_id(self):
        return f'run_{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}'

    def publish_start_once(self):
        if getattr(self, '_start_sent', False):
            return
        msg = String()
        msg.data = json.dumps({
            'run_id': self.run_id,
            'scenario_id': self.scenario_id,
            'architecture': self.architecture,
            'experiment_profile': self.experiment_profile,
            'seed': self.seed,
            'start_time': self.start_time,
        })
        self.start_pub.publish(msg)
        self._start_sent = True

    def _ensure_header(self, path, fields):
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with open(path, 'w', newline='') as f:
                csv.DictWriter(f, fieldnames=fields).writeheader()

    def metrics_callback(self, msg: ExperimentMetrics):
        self.last_metrics.update({
            'collisions_count': int(msg.collisions),
            'total_energy_wh': float(msg.energy_consumption),
            'avg_latency_ms': float(msg.avg_latency),
            'packet_loss_ratio': float(msg.packet_loss),
            'active_agents': int(msg.active_agents),
        })

    def metrics_json_callback(self, msg: String):
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        if payload.get('run_id') != self.run_id:
            return
        self.last_metrics.update(payload)
        conn = payload.get('connectivity_coeff')
        if self._is_number(conn):
            self.connectivity_samples.append(float(conn))
        self.write_timeseries_row()

    def state_callback(self, msg: SwarmState):
        if self._is_number(msg.connectivity_coefficient):
            self.connectivity_samples.append(float(msg.connectivity_coefficient))

    def arch_info_callback(self, msg: String):
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        if payload.get('run_id') != self.run_id:
            return
        self.architecture_effective = payload.get('architecture_effective', self.architecture_effective)
        self.architecture_requested = payload.get('architecture_requested', payload.get('architecture', self.architecture_requested))
        self.marl_model_loaded = as_bool(payload.get('marl_model_loaded', self.marl_model_loaded))
        self.marl_model_path = payload.get('marl_model_path', self.marl_model_path)
        self.marl_model_exists = as_bool(payload.get('marl_model_exists', self.marl_model_exists))
        self.marl_model_allowed_for_proof = as_bool(payload.get('marl_model_allowed_for_proof', self.marl_model_allowed_for_proof))
        self.marl_model_type = payload.get('marl_model_type', self.marl_model_type)
        if payload.get('validity_class'):
            self.initial_validity_class = payload['validity_class']

    def complete_callback(self, msg: String):
        if self.final_written:
            return
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError:
            payload = {}
        self.write_final(payload)
        rclpy.shutdown()

    def timeout_check(self):
        if not self.final_written and time.time() - self.start_time >= self.logger_timeout_s:
            self.write_final({
                'success_flag': False,
                'timeout_flag': True,
                'mission_timeout_reached': False,
                'runner_timeout_reached': True,
                'scenario_completed': False,
                'complete_reason': 'timeout_no_experiment_complete',
                'validity_class': 'incomplete_or_timeout',
            })
            rclpy.shutdown()

    def write_timeseries_row(self):
        row = {
            'run_id': self.run_id,
            'scenario_id': self.scenario_id,
            'experiment_profile': self.experiment_profile,
            'architecture': self.architecture,
            'architecture_effective': self.architecture_effective,
            'seed': self.seed,
            'timestamp': time.time(),
            'mission_time_s': time.time() - self.start_time,
            'collisions_count': self.last_metrics.get('collisions_count', float('nan')),
            'total_energy_wh': self.last_metrics.get('total_energy_wh', float('nan')),
            'avg_latency_ms': self.last_metrics.get('avg_latency_ms', float('nan')),
            'packet_loss_ratio': self.last_metrics.get('packet_loss_ratio', float('nan')),
            'connectivity_coeff': self.last_metrics.get('connectivity_coeff', float('nan')),
            'coverage_ratio': self.last_metrics.get('coverage_ratio', float('nan')),
            'active_agents': self.last_metrics.get('active_agents', ''),
            'failed_agents': self.last_metrics.get('failed_agents', ''),
        }
        with open(self.timeseries_csv, 'a', newline='') as f:
            csv.DictWriter(f, fieldnames=TIMESERIES_FIELDS).writerow(row)

    def write_final(self, completion):
        if self.final_written:
            return
        self.end_time = time.time()
        timeout_flag = bool(completion.get('timeout_flag', False))
        runner_timeout_reached = bool(completion.get('runner_timeout_reached', False))
        mission_timeout_reached = bool(completion.get('mission_timeout_reached', timeout_flag and not runner_timeout_reached))
        scenario_completed = bool(completion.get('scenario_completed', not runner_timeout_reached))
        success_flag = bool(completion.get('success_flag', False)) and not timeout_flag
        conn_values = [v for v in self.connectivity_samples if self._is_number(v)]
        validity_class = completion.get('validity_class') or self.initial_validity_class
        if not validity_class:
            validity_class = 'valid_success' if success_flag else ('incomplete_or_timeout' if timeout_flag else 'valid_completed')

        collisions = self.last_metrics.get('collisions_count', float('nan'))
        energy = self.last_metrics.get('total_energy_wh', float('nan'))
        if self._is_number(collisions) and collisions < self.baseline_collisions:
            validity_class = 'diagnostic_metric_accumulation'
        if self._is_number(energy) and energy < self.baseline_energy:
            validity_class = 'diagnostic_metric_accumulation'
        if self.architecture_requested == 'marl_decpomdp' and not self.marl_model_loaded:
            validity_class = 'diagnostic_marl_model_missing'
        elif self.architecture_requested == 'marl_decpomdp' and self.marl_model_type == 'test_integration_checkpoint':
            validity_class = 'diagnostic_test_marl_model'

        row = {
            'run_id': self.run_id,
            'scenario_id': self.scenario_id,
            'experiment_profile': completion.get('experiment_profile', self.experiment_profile),
            'success_criteria_profile': completion.get('success_criteria_profile', self.success_criteria_profile),
            'simulation_mode': self.last_metrics.get('simulation_mode', self.simulation_mode),
            'architecture_requested': self.architecture_requested,
            'architecture': self.architecture,
            'architecture_effective': self.architecture_effective,
            'seed': self.seed,
            'num_agents': self.num_agents,
            'num_uavs': self.num_uavs,
            'num_ugvs': self.num_ugvs,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'mission_time_s': self.end_time - self.start_time,
            'mission_timeout_s': self.timeout_s,
            'success_flag': int(success_flag),
            'timeout_flag': int(mission_timeout_reached),
            'mission_timeout_reached': int(mission_timeout_reached),
            'runner_timeout_reached': int(runner_timeout_reached),
            'scenario_completed': int(scenario_completed),
            'complete_reason': completion.get('complete_reason', 'experiment_complete'),
            'collisions_count': collisions,
            'total_energy_wh': energy,
            'avg_latency_ms': self.last_metrics.get('avg_latency_ms', float('nan')),
            'packet_loss_ratio': self.last_metrics.get('packet_loss_ratio', float('nan')),
            'connectivity_coeff_mean': self.last_metrics.get('connectivity_coeff_mean', completion.get('connectivity_coeff_mean', float(np_mean(conn_values)))),
            'connectivity_coeff_min': self.last_metrics.get('connectivity_coeff_min', completion.get('connectivity_coeff_mean', float(np_min(conn_values)))),
            'coverage_ratio': self.last_metrics.get('coverage_ratio', completion.get('coverage_ratio', 0.0)),
            'agents_failed_count': self.last_metrics.get('failed_agents', 0),
            'marl_model_path': self.marl_model_path,
            'marl_model_exists': str(bool(self.marl_model_exists)).lower(),
            'marl_model_loaded': str(bool(self.marl_model_loaded)).lower(),
            'marl_model_allowed_for_proof': str(bool(self.marl_model_allowed_for_proof)).lower(),
            'marl_model_type': self.marl_model_type,
            'validity_class': validity_class,
        }
        with open(self.final_csv, 'a', newline='') as f:
            csv.DictWriter(f, fieldnames=FINAL_FIELDS).writerow(row)
        self.final_written = True
        self.get_logger().info(f'Final metrics written for {self.run_id}: {validity_class}')

    @staticmethod
    def _is_number(value):
        try:
            return not math.isnan(float(value))
        except (TypeError, ValueError):
            return False


def np_mean(values):
    return sum(values) / len(values) if values else float('nan')


def np_min(values):
    return min(values) if values else float('nan')


def as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes'}


def main(args=None):
    rclpy.init(args=args)
    node = ExperimentLogger()
    try:
        rclpy.spin(node)
    finally:
        if rclpy.ok() and not node.final_written:
            node.write_final({'success_flag': False, 'timeout_flag': True, 'mission_timeout_reached': False, 'runner_timeout_reached': True, 'scenario_completed': False, 'complete_reason': 'shutdown_before_complete', 'validity_class': 'incomplete_or_timeout'})
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
