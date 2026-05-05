#!/usr/bin/env python3
"""Lightweight communication degradation telemetry for batch experiments."""
import json
import random
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64, String


class CommEmulatorNode(Node):
    def __init__(self):
        super().__init__('comm_emulator')
        self.declare_parameter('scenario_id', 'S1')
        self.declare_parameter('seed', 42)
        self.declare_parameter('packet_loss_rate', 0.0)
        self.declare_parameter('packet_loss', -1.0)
        self.declare_parameter('latency_mean_ms', 20.0)
        self.declare_parameter('latency_ms', -1.0)
        self.declare_parameter('latency_std_ms', 5.0)
        self.declare_parameter('enabled', True)

        self.scenario_id = str(self.get_parameter('scenario_id').value)
        self.seed = int(self.get_parameter('seed').value)
        self.p_loss = float(self.get_parameter('packet_loss').value)
        if self.p_loss < 0:
            self.p_loss = float(self.get_parameter('packet_loss_rate').value)
        self.latency_mean_ms = float(self.get_parameter('latency_ms').value)
        if self.latency_mean_ms < 0:
            self.latency_mean_ms = float(self.get_parameter('latency_mean_ms').value)
        self.latency_std_ms = float(self.get_parameter('latency_std_ms').value)
        self.enabled = bool(self.get_parameter('enabled').value)
        self.rng = random.Random(self.seed)

        self.latency_pub = self.create_publisher(Float64, '/swarm/avg_latency', 10)
        self.loss_pub = self.create_publisher(Float64, '/swarm/packet_loss', 10)
        self.diag_pub = self.create_publisher(String, '/swarm/communication_diagnostics', 10)
        self.create_subscription(String, '/experiment/start', self.start_callback, 10)
        self.create_timer(1.0, self.publish_diagnostics)
        self.get_logger().info(f'Communication emulator: loss={self.p_loss}, latency={self.latency_mean_ms} ms')

    def start_callback(self, msg: String):
        try:
            payload = json.loads(msg.data)
            self.seed = int(payload.get('seed', self.seed))
            self.rng.seed(self.seed)
        except (json.JSONDecodeError, ValueError):
            pass

    def publish_diagnostics(self):
        latency = max(0.0, self.rng.gauss(self.latency_mean_ms, self.latency_std_ms)) if self.enabled else 0.0
        loss = min(1.0, max(0.0, self.p_loss)) if self.enabled else 0.0
        lat_msg = Float64()
        lat_msg.data = latency
        loss_msg = Float64()
        loss_msg.data = loss
        self.latency_pub.publish(lat_msg)
        self.loss_pub.publish(loss_msg)
        diag = String()
        diag.data = json.dumps({
            'scenario_id': self.scenario_id,
            'avg_latency_ms': latency,
            'packet_loss_ratio': loss,
            'timestamp': time.time(),
        })
        self.diag_pub.publish(diag)


def main(args=None):
    rclpy.init(args=args)
    node = CommEmulatorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
