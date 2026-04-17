#!/usr/bin/env python3
"""
Intelligent Decision Core Node.
Implements Dec-POMDP model (Eq. 3.5-3.9) and MARL correction (Eq. 3.16-3.22).
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import Float64MultiArray, Bool
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from swarm_msgs.msg import SwarmState, TaskAssignment, DecisionOutput
import numpy as np
from typing import Dict, List, Tuple
import torch
import torch.nn as nn
from collections import deque
import json


class DecPOMDPSolver:
    """
    Decentralized Partially Observable Markov Decision Process solver.
    Implements equations 3.5-3.9 from Chapter 3.
    """
    def __init__(self, state_dim: int, action_dim: int, horizon: int = 10):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.horizon = horizon
        self.gamma = 0.95  # Discount factor (Eq. 3.6)
        
        # Transition and observation models (learned or predefined)
        self.transition_model = self._init_transition_model()
        self.observation_model = self._init_observation_model()
        
    def _init_transition_model(self) -> np.ndarray:
        """Initialize transition probability matrix P(s'|s,a)"""
        # Simplified: in practice, learned from simulation
        return np.random.rand(self.state_dim, self.action_dim, self.state_dim)
    
    def _init_observation_model(self) -> np.ndarray:
        """Initialize observation probability matrix O(o|s,a)"""
        return np.random.rand(self.state_dim, self.action_dim, self.state_dim)
    
    def compute_utility(self, state: np.ndarray, action: np.ndarray, 
                       swarm_state: SwarmState) -> float:
        """
        Compute utility function (Eq. 3.1-3.4).
        U = w1*U_time + w2*U_energy + w3*U_safety + w4*U_connectivity
        """
        weights = np.array([0.4, 0.3, 0.2, 0.1])
        
        # Time efficiency (inverse of estimated completion time)
        u_time = 1.0 / (np.linalg.norm(state[:2]) + 1e-6)
        
        # Energy consumption (based on action magnitude)
        u_energy = 1.0 / (np.linalg.norm(action) + 1e-6)
        
        # Safety (inverse of collision risk)
        u_safety = self._compute_safety_metric(swarm_state)
        
        # Connectivity (graph connectivity coefficient)
        u_connectivity = self._compute_connectivity_metric(swarm_state)
        
        utilities = np.array([u_time, u_energy, u_safety, u_connectivity])
        return float(np.dot(weights, utilities))
    
    def _compute_safety_metric(self, swarm_state: SwarmState) -> float:
        """Compute safety metric based on obstacle distances"""
        min_dist = min([obs.distance for obs in swarm_state.obstacles]) if swarm_state.obstacles else 10.0
        return min(min_dist / 5.0, 1.0)  # Normalize to [0,1]
    
    def _compute_connectivity_metric(self, swarm_state: SwarmState) -> float:
        """Compute connectivity coefficient (Eq. 3.23)"""
        if len(swarm_state.agents) <= 1:
            return 1.0
        connected_pairs = 0
        total_pairs = len(swarm_state.agents) * (len(swarm_state.agents) - 1) / 2
        # Count connected pairs based on communication range
        for i in range(len(swarm_state.agents)):
            for j in range(i+1, len(swarm_state.agents)):
                dist = np.linalg.norm(
                    np.array(swarm_state.agents[i].position) - 
                    np.array(swarm_state.agents[j].position)
                )
                if dist < 100.0:  # Communication range
                    connected_pairs += 1
        return connected_pairs / total_pairs if total_pairs > 0 else 0.0


class MARLAgent(nn.Module):
    """
    Multi-Agent Reinforcement Learning agent.
    Implements neural network for policy correction (Eq. 3.16-3.22).
    """
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 128):
        super(MARLAgent, self).__init__()
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, action_dim)
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=-1)
        
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.softmax(self.fc3(x))
        return x
    
    def select_action(self, state: torch.Tensor, exploration_rate: float = 0.1) -> int:
        if np.random.random() < exploration_rate:
            return np.random.randint(0, self.fc3.out_features)
        with torch.no_grad():
            probs = self.forward(state.unsqueeze(0))
            return torch.multinomial(probs, 1).item()


class DecisionCoreNode(Node):
    """Main decision-making node integrating Dec-POMDP and MARL."""
    
    def __init__(self):
        super().__init__('decision_core')
        
        # Parameters
        self.declare_parameter('use_marl', True)
        self.declare_parameter('model_path', '')
        self.declare_parameter('dec_pomdp_horizon', 10)
        self.declare_parameter('exploration_rate', 0.1)
        
        self.use_marl = self.get_parameter('use_marl').get_parameter_value().bool_value
        self.model_path = self.get_parameter('model_path').get_parameter_value().string_value
        self.horizon = self.get_parameter('dec_pomdp_horizon').get_parameter_value().integer_value
        self.exploration_rate = self.get_parameter('exploration_rate').get_parameter_value().double_value
        
        # Initialize Dec-POMDP solver
        self.dec_pomdp = DecPOMDPSolver(state_dim=12, action_dim=6, horizon=self.horizon)
        
        # Initialize MARL agent if enabled
        if self.use_marl:
            self.marl_agent = MARLAgent(state_dim=12, action_dim=6)
            if self.model_path and os.path.exists(self.model_path):
                self.marl_agent.load_state_dict(torch.load(self.model_path))
                self.get_logger().info(f'Loaded MARL model from {self.model_path}')
            else:
                self.get_logger().warn('MARL model not found, using random policy')
        else:
            self.marl_agent = None
        
        # State buffer for temporal reasoning
        self.state_buffer = deque(maxlen=10)
        self.current_state = None
        
        # QoS profile for reliable communication
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Subscribers
        self.swarm_state_sub = self.create_subscription(
            SwarmState,
            '/swarm/state',
            self.swarm_state_callback,
            qos_profile
        )
        
        self.odom_sub = self.create_subscription(
            Odometry,
            'odom',
            self.odom_callback,
            qos_profile
        )
        
        # Publishers
        self.decision_pub = self.create_publisher(
            DecisionOutput,
            '/agent/decision',
            qos_profile
        )
        
        self.cmd_vel_pub = self.create_publisher(
            Twist,
            'cmd_vel',
            qos_profile
        )
        
        # Timer for decision loop (10 Hz)
        self.timer = self.create_timer(0.1, self.decision_loop)
        
        self.get_logger().info('Decision Core Node initialized')
    
    def swarm_state_callback(self, msg: SwarmState):
        """Process global swarm state"""
        self.current_state = msg
    
    def odom_callback(self, msg: Odometry):
        """Process local odometry"""
        state_vector = self._odom_to_state_vector(msg)
        self.state_buffer.append(state_vector)
    
    def _odom_to_state_vector(self, odom: Odometry) -> np.ndarray:
        """Convert odometry to state vector for neural network"""
        pos = odom.pose.pose.position
        orient = odom.pose.pose.orientation
        vel = odom.twist.twist.linear
        
        return np.array([
            pos.x, pos.y, pos.z,
            orient.x, orient.y, orient.z, orient.w,
            vel.x, vel.y, vel.z
        ], dtype=np.float32)
    
    def decision_loop(self):
        """Main decision-making loop (executes at 10 Hz)"""
        if self.current_state is None or len(self.state_buffer) == 0:
            return
        
        # Get current state
        recent_states = np.array(list(self.state_buffer))
        current_state_vec = recent_states[-1]
        
        # Compute utility for possible actions
        actions = self._generate_candidate_actions()
        best_action = None
        best_utility = -np.inf
        
        for action in actions:
            utility = self.dec_pomdp.compute_utility(
                current_state_vec, action, self.current_state
            )
            
            # MARL correction if enabled
            if self.use_marl and self.marl_agent is not None:
                state_tensor = torch.FloatTensor(current_state_vec)
                marl_correction = self.marl_agent.select_action(
                    state_tensor, self.exploration_rate
                )
                # Apply correction (Eq. 3.20-3.22)
                utility *= (1.0 + 0.1 * marl_correction)
            
            if utility > best_utility:
                best_utility = utility
                best_action = action
        
        # Publish decision
        if best_action is not None:
            self._publish_decision(best_action, best_utility)
            self._publish_velocity_command(best_action)
    
    def _generate_candidate_actions(self) -> List[np.ndarray]:
        """Generate candidate actions for evaluation"""
        # Discretized action space: 6 directions + stop
        actions = [
            np.array([1.0, 0.0, 0.0]),   # Forward
            np.array([-1.0, 0.0, 0.0]),  # Backward
            np.array([0.0, 1.0, 0.0]),   # Left
            np.array([0.0, -1.0, 0.0]),  # Right
            np.array([0.0, 0.0, 1.0]),   # Up (for UAV)
            np.array([0.0, 0.0, 0.0]),   # Stop
        ]
        return actions
    
    def _publish_decision(self, action: np.ndarray, utility: float):
        """Publish decision output"""
        msg = DecisionOutput()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.action_vector = action.tolist()
        msg.utility = utility
        msg.decision_method = 'dec_pomdp_marl' if self.use_marl else 'dec_pomdp'
        self.decision_pub.publish(msg)
    
    def _publish_velocity_command(self, action: np.ndarray):
        """Publish velocity command to low-level controller"""
        cmd = Twist()
        cmd.linear.x = float(action[0]) * 1.0  # m/s
        cmd.linear.y = float(action[1]) * 1.0
        cmd.linear.z = float(action[2]) * 0.5 if len(action) > 2 else 0.0
        self.cmd_vel_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = DecisionCoreNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()