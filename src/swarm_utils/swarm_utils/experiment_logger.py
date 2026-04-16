#!/usr/bin/env python3
"""
Experiment Logger Node.
Records metrics to CSV for statistical analysis (Section 4.5).
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64, Bool
from nav_msgs.msg import Odometry
from swarm_msgs.msg import SwarmState, ExperimentMetrics
import csv
import os
from datetime import datetime
import json


class ExperimentLogger(Node):
    def __init__(self):
        super().__init__('experiment_logger')
        
        # Parameters
        self.declare_parameter('log_path', '/tmp/swarm_experiments')
        self.declare_parameter('scenario_id', 'S1')
        self.declare_parameter('seed', 42)
        self.declare_parameter('csv_output', True)
        
        self.log_path = self.get_parameter('log_path').get_parameter_value().string_value
        self.scenario_id = self.get_parameter('scenario_id').get_parameter_value().string_value
        self.seed = self.get_parameter('seed').get_parameter_value().integer_value
        
        # Create log directory
        os.makedirs(self.log_path, exist_ok=True)
        
        # Generate unique run ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.run_id = f"{self.scenario_id}_{timestamp}_{self.seed}"
        self.csv_file = os.path.join(self.log_path, f"{self.run_id}.csv")
        
        # Initialize metrics
        self.metrics = {
            'run_id': self.run_id,
            'scenario_id': self.scenario_id,
            'seed': self.seed,
            'start_time': None,
            'end_time': None,
            'mission_time_s': 0.0,
            'success_flag': 0,
            'collisions_count': 0,
            'total_energy_wh': 0.0,
            'avg_latency_ms': 0.0,
            'packet_loss_ratio': 0.0,
            'connectivity_coeff': 1.0,
            'num_agents': 0
        }
        
        # CSV header
        self.csv_header = list(self.metrics.keys())
        
        # Subscribers
        self.create_subscription(SwarmState, '/swarm/state', self.swarm_state_callback, 10)
        self.create_subscription(ExperimentMetrics, '/swarm/metrics', self.metrics_callback, 10)
        self.create_subscription(Bool, '/experiment/complete', self.experiment_complete_callback, 10)
        
        # Timer for periodic logging
        self.create_timer(1.0, self.log_periodic)
        
        self.get_logger().info(f'Experiment logger initialized. Logging to: {self.csv_file}')
    
    def swarm_state_callback(self, msg: SwarmState):
        if self.metrics['start_time'] is None:
            self.metrics['start_time'] = self.get_clock().now().nanoseconds / 1e9
            self.metrics['num_agents'] = len(msg.agents)
        
        # Update connectivity
        self.metrics['connectivity_coeff'] = self._compute_connectivity(msg)
    
    def metrics_callback(self, msg: ExperimentMetrics):
        self.metrics['collisions_count'] = msg.collisions
        self.metrics['total_energy_wh'] += msg.energy_consumption
        self.metrics['avg_latency_ms'] = msg.avg_latency
        self.metrics['packet_loss_ratio'] = msg.packet_loss
    
    def experiment_complete_callback(self, msg: Bool):
        if msg.data:
            self.finalize_experiment(success=True)
    
    def _compute_connectivity(self, swarm_state: SwarmState) -> float:
        """Compute graph connectivity coefficient"""
        n = len(swarm_state.agents)
        if n <= 1:
            return 1.0
        
        connected = 0
        total = n * (n - 1) / 2
        
        for i in range(n):
            for j in range(i + 1, n):
                dist = ((swarm_state.agents[i].position.x - swarm_state.agents[j].position.x) ** 2 +
                       (swarm_state.agents[i].position.y - swarm_state.agents[j].position.y) ** 2) ** 0.5
                if dist < 100.0:  # Communication range
                    connected += 1
        
        return connected / total if total > 0 else 0.0
    
    def log_periodic(self):
        """Log current metrics to CSV"""
        if not self.get_parameter('csv_output').get_parameter_value().bool_value:
            return
        
        file_exists = os.path.isfile(self.csv_file)
        
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_header)
            if not file_exists:
                writer.writeheader()
            
            # Write current snapshot
            row = {k: v for k, v in self.metrics.items()}
            writer.writerow(row)
    
    def finalize_experiment(self, success: bool = True):
        """Finalize experiment and compute final metrics"""
        end_time = self.get_clock().now().nanoseconds / 1e9
        
        if self.metrics['start_time'] is not None:
            self.metrics['mission_time_s'] = end_time - self.metrics['start_time']
        
        self.metrics['end_time'] = end_time
        self.metrics['success_flag'] = 1 if success else 0
        
        # Write final metrics
        self.log_periodic()
        
        # Also save as JSON for easy parsing
        json_file = self.csv_file.replace('.csv', '.json')
        with open(json_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        self.get_logger().info(f'Experiment completed. Results saved to {self.csv_file}')
        self.get_logger().info(f'Mission time: {self.metrics["mission_time_s"]:.2f}s, '
                              f'Success: {success}, Collisions: {self.metrics["collisions_count"]}')


def main(args=None):
    rclpy.init(args=args)
    node = ExperimentLogger()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()