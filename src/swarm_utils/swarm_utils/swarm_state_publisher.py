#!/usr/bin/env python3
"""
Swarm State Publisher Node.
Publishes mock swarm state for logging and visualization.
"""

import rclpy
from rclpy.node import Node
from swarm_msgs.msg import SwarmState, AgentState
from geometry_msgs.msg import Point, Quaternion, Twist
from std_msgs.msg import Header
import math
import random


class SwarmStatePublisher(Node):
    def __init__(self):
        super().__init__('swarm_state_publisher')
        
        # Publisher
        self.publisher = self.create_publisher(SwarmState, '/swarm/state', 10)
        
        # Timer to publish state at 2 Hz
        self.timer = self.create_timer(0.5, self.publish_state)
        
        # Инициализация позиций агентов (8 штук)
        self.agent_positions = []
        for i in range(8):
            angle = 2 * math.pi * i / 8
            self.agent_positions.append({
                'x': 10.0 * math.cos(angle),
                'y': 10.0 * math.sin(angle),
                'z': 0.0,
                'vx': 0.5,
                'vy': 0.2,
                'vz': 0.0
            })
        
        self.get_logger().info('Swarm State Publisher initialized')
    
    def publish_state(self):
        msg = SwarmState()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        
        # Обновляем позиции (имитация движения по окружности с небольшим дрейфом)
        for i, pos in enumerate(self.agent_positions):
            angle = 2 * math.pi * i / 8 + self.get_clock().now().nanoseconds * 1e-9 * 0.1
            pos['x'] = 10.0 * math.cos(angle) + random.uniform(-0.5, 0.5)
            pos['y'] = 10.0 * math.sin(angle) + random.uniform(-0.5, 0.5)
            
            agent = AgentState()
            agent.id = f'agent_{i}'
            agent.position = Point(x=pos['x'], y=pos['y'], z=pos['z'])
            agent.velocity = Twist()
            agent.velocity.linear.x = pos['vx']
            agent.velocity.linear.y = pos['vy']
            agent.velocity.linear.z = pos['vz']
            agent.status = 'active'
            msg.agents.append(agent)
        
        # Коэффициент связности (случайный в разумных пределах)
        msg.connectivity_coefficient = 0.8 + 0.2 * random.random()
        
        self.publisher.publish(msg)
        self.get_logger().debug(f'Published state for {len(msg.agents)} agents')


def main(args=None):
    rclpy.init(args=args)
    node = SwarmStatePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()