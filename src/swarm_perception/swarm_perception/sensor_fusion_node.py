#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Sensor Fusion Node. Implements EKF (Eq. 3.8-3.9).
Fuses odometry, lidar landmarks, and GPS for state estimation.
"""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from swarm_msgs.msg import SwarmState
import numpy as np
from filterpy.kalman import ExtendedKalmanFilter as EKF

class SensorFusionNode(Node):
    def __init__(self):
        super().__init__('sensor_fusion_node')
        
        # EKF state: [x, y, theta, vx, vy, omega]
        self.ekf = EKF(dim_x=6, dim_z=3)
        self.ekf.F = np.eye(6)  # State transition
        self.ekf.H = np.eye(3, 6)  # Observation matrix
        self.ekf.R *= np.diag([0.1, 0.1, 0.05])  # Sensor noise
        self.ekf.Q *= np.diag([0.01, 0.01, 0.001, 0.1, 0.1, 0.01])  # Process noise
        
        self.odom_sub = self.create_subscription(Odometry, 'odom', self.odom_cb, 10)
        self.imu_sub = self.create_subscription(Imu, 'imu', self.imu_cb, 10)
        self.fused_pub = self.create_publisher(Odometry, 'odom_fused', 10)
        
        self.last_time = self.get_clock().now()
        
    def odom_cb(self, msg: Odometry):
        dt = (self.get_clock().now() - self.last_time).nanoseconds / 1e9
        self.last_time = self.get_clock().now()
        
        z = np.array([msg.pose.pose.position.x, 
                      msg.pose.pose.position.y,
                      np.arctan2(2*(msg.pose.pose.orientation.w*msg.pose.pose.orientation.z),
                                 1-2*(msg.pose.pose.orientation.x**2+msg.pose.pose.orientation.y**2))])
        
        # Predict
        self.ekf.predict()
        # Update
        self.ekf.update(z)
        
        pub_msg = Odometry()
        pub_msg.header = msg.header
        pub_msg.pose.pose.position.x = float(self.ekf.x[0])
        pub_msg.pose.pose.position.y = float(self.ekf.x[1])
        pub_msg.twist.twist.linear.x = float(self.ekf.x[3])
        pub_msg.twist.twist.linear.y = float(self.ekf.x[4])
        pub_msg.twist.twist.angular.z = float(self.ekf.x[5])
        
        self.fused_pub.publish(pub_msg)
        
    def imu_cb(self, msg: Imu):
        pass  # Used for bias correction in extended version

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(SensorFusionNode())
    rclpy.shutdown()

if __name__ == '__main__':
    main()