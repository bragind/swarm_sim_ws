#!/usr/bin/env python3
"""Simple mission supervisor for reproducible WKR experiments."""
import json
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MissionSupervisor(Node):
    def __init__(self):
        super().__init__('mission_supervisor')
        self.declare_parameter('run_id', '')
        self.declare_parameter('scenario_id', 'S1')
        self.declare_parameter('architecture', '')
        self.declare_parameter('architecture_id', '')
        self.declare_parameter('seed', 42)
        self.declare_parameter('mission_timeout_s', 120.0)
        self.declare_parameter('experiment_profile', 'full')
        self.declare_parameter('success_criteria_profile', 'full')
        self.declare_parameter('coverage_threshold', 0.75)
        self.declare_parameter('connectivity_threshold', 0.55)
        self.declare_parameter('min_active_agents', 6)

        self.run_id = str(self.get_parameter('run_id').value)
        self.scenario_id = str(self.get_parameter('scenario_id').value)
        self.architecture = str(self.get_parameter('architecture').value or self.get_parameter('architecture_id').value)
        self.seed = int(self.get_parameter('seed').value)
        self.timeout_s = float(self.get_parameter('mission_timeout_s').value)
        self.experiment_profile = str(self.get_parameter('experiment_profile').value)
        self.success_criteria_profile = str(self.get_parameter('success_criteria_profile').value)
        self.coverage_threshold = float(self.get_parameter('coverage_threshold').value)
        self.connectivity_threshold = float(self.get_parameter('connectivity_threshold').value)
        self.min_active_agents = int(self.get_parameter('min_active_agents').value)

        self.start_time = time.time()
        self.completed = False
        self.complete_payload = None
        self.complete_republish_count = 0
        self.start_sent = False
        self.latest_metrics = {}

        self.start_pub = self.create_publisher(String, '/experiment/start', 10)
        self.complete_pub = self.create_publisher(String, '/experiment/complete', 10)
        self.create_subscription(String, '/swarm/metrics_json', self.metrics_callback, 10)
        self.create_timer(0.5, self.publish_start)
        self.create_timer(1.0, self.evaluate)

    def publish_start(self):
        if self.start_sent:
            return
        msg = String()
        msg.data = json.dumps({
            'run_id': self.run_id,
            'scenario_id': self.scenario_id,
            'architecture': self.architecture,
            'seed': self.seed,
            'start_time': self.start_time,
        })
        self.start_pub.publish(msg)
        self.start_sent = True

    def metrics_callback(self, msg: String):
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError:
            self.latest_metrics = {}
            return
        if payload.get('run_id') != self.run_id:
            return
        self.latest_metrics = payload

    def evaluate(self):
        if self.completed:
            if self.complete_payload is not None and self.complete_republish_count < 10:
                out = String()
                out.data = json.dumps(self.complete_payload)
                self.complete_pub.publish(out)
                self.complete_republish_count += 1
            return
        elapsed = time.time() - self.start_time
        coverage = float(self.latest_metrics.get('coverage_ratio', 0.0) or 0.0)
        connectivity = float(self.latest_metrics.get('connectivity_coeff_mean', 0.0) or 0.0)
        active_agents = int(self.latest_metrics.get('active_agents', 0) or 0)
        timeout = elapsed >= self.timeout_s
        success = (
            coverage >= self.coverage_threshold
            and connectivity >= self.connectivity_threshold
            and active_agents >= self.min_active_agents
            and not timeout
        )
        if success or timeout:
            self.completed = True
            payload = {
                'run_id': self.run_id,
                'scenario_id': self.scenario_id,
                'experiment_profile': self.experiment_profile,
                'success_criteria_profile': self.success_criteria_profile,
                'success_flag': success,
                'timeout_flag': timeout,
                'mission_timeout_reached': timeout,
                'runner_timeout_reached': False,
                'scenario_completed': True,
                'complete_reason': 'mission_success' if success else 'mission_timeout',
                'validity_class': 'valid_success' if success else 'valid_failure',
                'mission_time_s': elapsed,
                'coverage_ratio': coverage,
                'connectivity_coeff_mean': connectivity,
                'active_agents': active_agents,
            }
            out = String()
            out.data = json.dumps(payload)
            self.complete_payload = payload
            self.complete_pub.publish(out)
            self.get_logger().info(f'Mission complete for {self.run_id}: {payload["complete_reason"]}')


def main(args=None):
    rclpy.init(args=args)
    node = MissionSupervisor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
