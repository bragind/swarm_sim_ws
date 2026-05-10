#!/usr/bin/env python3
"""
Run-scoped experiment metrics for WKR validation.

The node publishes periodic metrics at 1 Hz and resets all accumulators when a
new /experiment/start message is received. Missing measurements are represented
as NaN; zeros are used only for physically valid zero values.
"""
import json
import math
import random
import time
from typing import Dict, Set, Tuple

import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from swarm_msgs.msg import ExperimentMetrics, SwarmState


class MetricsCalculator(Node):
    def __init__(self):
        super().__init__('metrics_calculator')
        self.declare_parameter('scenario_id', 'S1')
        self.declare_parameter('architecture', '')
        self.declare_parameter('architecture_id', '')
        self.declare_parameter('seed', 42)
        self.declare_parameter('num_agents', 8)
        self.declare_parameter('sensor_range', 18.0)
        self.declare_parameter('comm_range', 55.0)
        self.declare_parameter('mission_area_min_x', -60.0)
        self.declare_parameter('mission_area_max_x', 60.0)
        self.declare_parameter('mission_area_min_y', -60.0)
        self.declare_parameter('mission_area_max_y', 60.0)
        self.declare_parameter('coverage_grid_m', 10.0)
        self.declare_parameter('packet_loss', 0.0)
        self.declare_parameter('latency_ms', 20.0)
        self.declare_parameter('agent_failure_ratio', 0.0)
        self.declare_parameter('obstacle_density', 0.35)
        self.declare_parameter('simulation_mode', 'gazebo_headless')

        self.scenario_id = str(self.get_parameter('scenario_id').value)
        self.architecture = str(self.get_parameter('architecture').value or self.get_parameter('architecture_id').value)
        self.seed = int(self.get_parameter('seed').value)
        self.num_agents = int(self.get_parameter('num_agents').value)
        self.sensor_range = float(self.get_parameter('sensor_range').value)
        self.comm_range = float(self.get_parameter('comm_range').value)
        self.area = (
            float(self.get_parameter('mission_area_min_x').value),
            float(self.get_parameter('mission_area_max_x').value),
            float(self.get_parameter('mission_area_min_y').value),
            float(self.get_parameter('mission_area_max_y').value),
        )
        self.grid_m = float(self.get_parameter('coverage_grid_m').value)
        self.packet_loss = float(self.get_parameter('packet_loss').value)
        self.latency_ms = float(self.get_parameter('latency_ms').value)
        self.agent_failure_ratio = float(self.get_parameter('agent_failure_ratio').value)
        self.obstacle_density = float(self.get_parameter('obstacle_density').value)
        self.simulation_mode = str(self.get_parameter('simulation_mode').value)
        self.last_start_run_id = None

        self.metrics_pub = self.create_publisher(ExperimentMetrics, '/swarm/metrics', 10)
        self.metrics_json_pub = self.create_publisher(String, '/swarm/metrics_json', 10)
        self.create_subscription(SwarmState, '/swarm/state', self.state_callback, 10)
        self.create_subscription(String, '/experiment/start', self.start_callback, 10)

        self.rng = random.Random(self.seed)
        self.reset_run(run_id='')
        self.create_timer(1.0, self.publish_metrics)
        self.get_logger().info(f'Metrics calculator ready for {self.scenario_id}/{self.architecture}')

    def reset_run(self, run_id: str):
        self.run_id = run_id
        self.started_at = time.time()
        self.last_state = None
        self.previous_positions: Dict[str, Tuple[float, float, float]] = {}
        self.visited_cells: Set[Tuple[int, int]] = set()
        self.collisions_count = 0
        self.total_energy_wh = 0.0
        self.connectivity_samples = []
        self.active_agents = self.num_agents
        self.failed_agents = 0
        self._last_energy_time = self.started_at

    def start_callback(self, msg: String):
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError:
            payload = {}
        run_id = str(payload.get('run_id', ''))
        if run_id and run_id != self.last_start_run_id:
            self.last_start_run_id = run_id
            self.reset_run(run_id)

    def state_callback(self, msg: SwarmState):
        self.last_state = msg
        now = time.time()
        dt_h = max(0.0, now - self._last_energy_time) / 3600.0
        self._last_energy_time = now

        active = [a for a in msg.agents if str(a.status).lower() != 'failed']
        self.active_agents = len(active)
        expected_failed = int(round(self.num_agents * self.agent_failure_ratio))
        observed_failed = len(msg.agents) - len(active)
        self.failed_agents = max(expected_failed, observed_failed)

        positions = {}
        for agent in active:
            p = agent.position
            pos = (float(p.x), float(p.y), float(p.z))
            positions[agent.id] = pos
            self._mark_covered_cells(pos)
            speed = math.sqrt(
                float(agent.velocity.linear.x) ** 2
                + float(agent.velocity.linear.y) ** 2
                + float(agent.velocity.linear.z) ** 2
            )
            power_w = 35.0 + 4.0 * speed ** 2
            self.total_energy_wh += power_w * dt_h

        self.previous_positions = positions
        conn = self._compute_connectivity(list(positions.values()))
        if not math.isnan(conn):
            self.connectivity_samples.append(conn)

        self.collisions_count = max(self.collisions_count, self._estimate_collision_count(list(positions.values())))

    def _mark_covered_cells(self, pos):
        min_x, max_x, min_y, max_y = self.area
        cx, cy, _ = pos
        radius_cells = int(math.ceil(self.sensor_range / self.grid_m))
        base_x = int(math.floor((cx - min_x) / self.grid_m))
        base_y = int(math.floor((cy - min_y) / self.grid_m))
        for dx in range(-radius_cells, radius_cells + 1):
            for dy in range(-radius_cells, radius_cells + 1):
                gx, gy = base_x + dx, base_y + dy
                cell_x = min_x + (gx + 0.5) * self.grid_m
                cell_y = min_y + (gy + 0.5) * self.grid_m
                if min_x <= cell_x <= max_x and min_y <= cell_y <= max_y:
                    if math.hypot(cell_x - cx, cell_y - cy) <= self.sensor_range:
                        self.visited_cells.add((gx, gy))

    def _total_cells(self):
        min_x, max_x, min_y, max_y = self.area
        return max(1, int(math.ceil((max_x - min_x) / self.grid_m)) * int(math.ceil((max_y - min_y) / self.grid_m)))

    def _compute_connectivity(self, positions):
        n = len(positions)
        if n == 0:
            return float('nan')
        if n == 1:
            return 1.0
        pairs = n * (n - 1) / 2.0
        connected = 0
        for i in range(n):
            for j in range(i + 1, n):
                if math.dist(positions[i], positions[j]) <= self.comm_range:
                    connected += 1
        loss_penalty = max(0.0, min(1.0, 1.0 - self.packet_loss))
        return max(0.0, min(1.0, connected / pairs * loss_penalty))

    def _estimate_collision_count(self, positions):
        count = 0
        threshold = max(1.2, 1.0 + self.obstacle_density)
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                if math.dist(positions[i], positions[j]) < threshold:
                    count += 1
        return count

    def _coverage_ratio(self):
        return max(0.0, min(1.0, len(self.visited_cells) / self._total_cells()))

    def publish_metrics(self):
        connectivity = self.connectivity_samples[-1] if self.connectivity_samples else float('nan')
        avg_latency = self.latency_ms if self.packet_loss <= 1.0 else float('nan')
        packet_loss = self.packet_loss if 0.0 <= self.packet_loss <= 1.0 else float('nan')
        coverage = self._coverage_ratio()

        msg = ExperimentMetrics()
        msg.collisions = int(self.collisions_count)
        msg.energy_consumption = float(self.total_energy_wh)
        msg.avg_latency = float(avg_latency)
        msg.packet_loss = float(packet_loss)
        msg.active_agents = int(self.active_agents)
        self.metrics_pub.publish(msg)

        payload = {
            'run_id': self.run_id,
            'scenario_id': self.scenario_id,
            'architecture': self.architecture,
            'collisions_count': self.collisions_count,
            'total_energy_wh': self.total_energy_wh,
            'avg_latency_ms': avg_latency,
            'packet_loss_ratio': packet_loss,
            'connectivity_coeff': connectivity,
            'connectivity_coeff_mean': float(np.mean(self.connectivity_samples)) if self.connectivity_samples else float('nan'),
            'connectivity_coeff_min': float(np.min(self.connectivity_samples)) if self.connectivity_samples else float('nan'),
            'coverage_ratio': coverage,
            'active_agents': self.active_agents,
            'failed_agents': self.failed_agents,
            'simulation_mode': self.simulation_mode,
            'timestamp': time.time(),
        }
        out = String()
        out.data = json.dumps(payload, allow_nan=True)
        self.metrics_json_pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = MetricsCalculator()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
