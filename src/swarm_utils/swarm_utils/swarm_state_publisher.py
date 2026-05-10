#!/usr/bin/env python3
"""Deterministic lightweight swarm-state source for logical experiments."""
import math
import random

import rclpy
from geometry_msgs.msg import Point, Twist
from rclpy.node import Node
from std_msgs.msg import Header
from swarm_msgs.msg import AgentState, SwarmState


class SwarmStatePublisher(Node):
    def __init__(self):
        super().__init__('swarm_state_publisher')
        self.declare_parameter('num_uavs', 5)
        self.declare_parameter('num_ugvs', 3)
        self.declare_parameter('num_agents', 8)
        self.declare_parameter('scenario_id', 'S1')
        self.declare_parameter('seed', 42)
        self.declare_parameter('agent_failure_ratio', 0.0)
        self.declare_parameter('simulation_mode', 'gazebo_headless')
        self.declare_parameter('headless_fast', False)

        self.num_uavs = int(self.get_parameter('num_uavs').value)
        self.num_ugvs = int(self.get_parameter('num_ugvs').value)
        self.num_agents = int(self.get_parameter('num_agents').value or (self.num_uavs + self.num_ugvs))
        self.scenario_id = str(self.get_parameter('scenario_id').value)
        self.seed = int(self.get_parameter('seed').value)
        self.agent_failure_ratio = float(self.get_parameter('agent_failure_ratio').value)
        self.simulation_mode = str(self.get_parameter('simulation_mode').value)
        self.headless_fast = bool(self.get_parameter('headless_fast').value)
        self.rng = random.Random(self.seed)
        self.start_time = self.get_clock().now()

        self.publisher = self.create_publisher(SwarmState, '/swarm/state', 10)
        self.timer = self.create_timer(0.5, self.publish_state)
        self.get_logger().info(f'Swarm state publisher: {self.num_agents} agents, scenario={self.scenario_id}')

    def publish_state(self):
        elapsed = (self.get_clock().now() - self.start_time).nanoseconds * 1e-9
        msg = SwarmState()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'

        if self.headless_fast or self.simulation_mode == 'headless_fast_kinematic':
            radius = 10.0 + 0.85 * min(elapsed, 60.0)
            angular_rate = 0.22
        else:
            radius = 16.0 + 0.12 * min(elapsed, 120.0)
            angular_rate = 0.10
        failed_count = int(round(self.num_agents * self.agent_failure_ratio)) if elapsed > 60.0 else 0
        for i in range(self.num_agents):
            angle = 2 * math.pi * i / max(1, self.num_agents) + elapsed * angular_rate
            agent = AgentState()
            agent.id = f'agent_{i}'
            agent.type = 'uav' if i < self.num_uavs else 'ugv'
            agent.status = 'failed' if i < failed_count else 'active'
            z = 8.0 + (i % max(1, self.num_uavs)) if agent.type == 'uav' else 0.0
            jitter_x = self.rng.uniform(-0.25, 0.25)
            jitter_y = self.rng.uniform(-0.25, 0.25)
            agent.position = Point(
                x=radius * math.cos(angle) + jitter_x,
                y=radius * math.sin(angle) + jitter_y,
                z=z,
            )
            agent.velocity = Twist()
            agent.velocity.linear.x = -radius * angular_rate * math.sin(angle)
            agent.velocity.linear.y = radius * angular_rate * math.cos(angle)
            agent.velocity.linear.z = 0.0
            msg.agents.append(agent)

        active = [a for a in msg.agents if a.status == 'active']
        msg.connectivity_coefficient = self._connectivity(active)
        self.publisher.publish(msg)

    @staticmethod
    def _connectivity(agents, comm_range=55.0):
        if not agents:
            return 0.0
        if len(agents) == 1:
            return 1.0
        total = len(agents) * (len(agents) - 1) / 2.0
        connected = 0
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                p_i = agents[i].position
                p_j = agents[j].position
                if math.dist((p_i.x, p_i.y, p_i.z), (p_j.x, p_j.y, p_j.z)) <= comm_range:
                    connected += 1
        return float(connected / total)


def main(args=None):
    rclpy.init(args=args)
    node = SwarmStatePublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
