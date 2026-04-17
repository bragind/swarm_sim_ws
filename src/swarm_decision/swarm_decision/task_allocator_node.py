#!/usr/bin/env python3
"""
Task Allocator Node. Implements auction-based allocation (Alg. 3.2, Eq. 3.2-3.4).
Distributes waypoints to agents based on utility function U = w1*T + w2*E + w3*S.
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from swarm_msgs.msg import TaskAssignment, SwarmState
import numpy as np
from collections import defaultdict

class TaskAllocatorNode(Node):
    def __init__(self):
        super().__init__('task_allocator')
        self.declare_parameter('utility_weights', [0.5, 0.3, 0.2])  # time, energy, safety
        self.weights = np.array(self.get_parameter('utility_weights').value)
        
        self.tasks_sub = self.create_subscription(PoseStamped, '/mission/tasks', self.task_cb, 10)
        self.state_sub = self.create_subscription(SwarmState, '/swarm/state', self.state_cb, 10)
        self.alloc_pub = self.create_publisher(TaskAssignment, '/swarm/task_allocation', 10)
        
        self.pending_tasks = []
        self.agent_states = {}
        
    def task_cb(self, msg):
        self.pending_tasks.append(msg)
        self.allocate_tasks()
        
    def state_cb(self, msg):
        for agent in msg.agents:
            self.agent_states[agent.id] = np.array([agent.position.x, agent.position.y])
            
    def allocate_tasks(self):
        if not self.pending_tasks or len(self.agent_states) == 0:
            return
            
        alloc_msg = TaskAssignment()
        for task in self.pending_tasks:
            best_agent = None
            best_utility = -np.inf
            
            task_pos = np.array([task.pose.position.x, task.pose.position.y])
            
            for agent_id, pos in self.agent_states.items():
                dist = np.linalg.norm(task_pos - pos)
                utility = self._compute_utility(dist)
                if utility > best_utility:
                    best_utility = utility
                    best_agent = agent_id
                    
            if best_agent:
                alloc_msg.agent_ids.append(best_agent)
                alloc_msg.tasks.append(task)
                
        self.alloc_pub.publish(alloc_msg)
        self.pending_tasks.clear()
        
    def _compute_utility(self, distance):
        # Simplified utility: U = -w1*d + w2*energy_margin + w3*safety
        time_cost = -self.weights[0] * distance / 15.0  # max speed 15 m/s
        energy_cost = self.weights[1] * 0.8
        safety_bonus = self.weights[2] * 0.9
        return time_cost + energy_cost + safety_bonus

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(TaskAllocatorNode())
    rclpy.shutdown()