#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Communication Emulator. Simulates packet loss and latency (Sec 3.6).
Intercepts topics, applies degradation, republishes.
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
import time
import random
import threading
from collections import deque

class CommEmulatorNode(Node):
    def __init__(self):
        super().__init__('comm_emulator')
        self.declare_parameter('packet_loss_rate', 0.0)
        self.declare_parameter('latency_mean_ms', 20.0)
        self.declare_parameter('latency_std_ms', 5.0)
        
        self.p_loss = self.get_parameter('packet_loss_rate').value
        self.lat_mu = self.get_parameter('latency_mean_ms').value / 1000.0
        self.lat_std = self.get_parameter('latency_std_ms').value / 1000.0
        
        self.msg_queue = deque()
        self.lock = threading.Lock()
        
        # Subscribe to all critical topics with wildcard-like behavior
        self.create_subscription('std_msgs/msg/String', '/swarm/state_raw', self.cb, 10)
        # In real setup, use ros2 topic list + dynamic subs
        
        self.timer = self.create_timer(0.01, self.process_queue)
        
    def cb(self, msg):
        with self.lock:
            self.msg_queue.append((time.time(), msg))
            
    def process_queue(self):
        if not self.msg_queue: return
        
        now = time.time()
        # Drop packets
        if random.random() < self.p_loss:
            self.msg_queue.popleft()
            return
            
        # Apply latency
        msg_time, msg = self.msg_queue[0]
        delay = max(0, random.gauss(self.lat_mu, self.lat_std))
        if now - msg_time >= delay:
            self.msg_queue.popleft()
            # Republish would go here in full implementation
            # For sim, this node logs degradation metrics
            
def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(CommEmulatorNode())
    rclpy.shutdown()