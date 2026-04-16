#!/usr/bin/env python3
"""
Perception Node. Publishes raw sensor data and preprocesses point clouds.
Implements sensor noise model from Sec 3.1.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, PointCloud2
from std_msgs.msg import Header
import numpy as np

class PerceptionNode(Node):
    def __init__(self):
        super().__init__('perception_node')
        self.declare_parameter('noise_sigma', 0.05)
        self.sigma = self.get_parameter('noise_sigma').get_parameter_value().double_value
        
        self.scan_pub = self.create_publisher(LaserScan, 'sensor_raw/lidar', 10)
        self.timer = self.create_timer(0.1, self.publish_simulated_scan)
        
    def publish_simulated_scan(self):
        msg = LaserScan()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_laser'
        msg.angle_min = -np.pi
        msg.angle_max = np.pi
        msg.angle_increment = 0.05
        msg.time_increment = 0.0
        msg.scan_time = 0.1
        msg.range_min = 0.1
        msg.range_max = 30.0
        
        # Simulated ranges with Gaussian noise (Eq. 3.1)
        num_beams = int((msg.angle_max - msg.angle_min) / msg.angle_increment)
        msg.ranges = (np.ones(num_beams) * 15.0 + np.random.normal(0, self.sigma, num_beams)).tolist()
        msg.intensities = [0.0] * num_beams
        
        self.scan_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()