#!/usr/bin/env python3
"""
Intelligent Decision Core Node.
Implements Dec-POMDP model (Eq. 3.5-3.9) and MARL correction (Eq. 3.16-3.22).
Supports multiple control architectures: central_a_star, reactive, rule_dec, marl_decpomdp.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import Float64MultiArray, Bool, String
from geometry_msgs.msg import PoseStamped, Twist, Point
from nav_msgs.msg import Odometry, Path
from swarm_msgs.msg import SwarmState, AgentState, TaskAssignment, DecisionOutput, Obstacle
import numpy as np
from typing import Dict, List, Tuple, Optional
import torch
import torch.nn as nn
import os
from collections import deque
import json
import random


# ============================================================================
# Dec-POMDP Solver (Eq. 3.5-3.9)
# ============================================================================
class DecPOMDPSolver:
    """
    Decentralized Partially Observable Markov Decision Process solver.
    Implements equations 3.5-3.9 from Chapter 3.
    """
    def __init__(self, state_dim: int, action_dim: int, horizon: int = 10, seed: int = 42):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.horizon = horizon
        self.gamma = 0.95  # Discount factor (Eq. 3.6)
        self.rng = np.random.default_rng(seed)
        
        # Transition and observation models (learned or predefined)
        self.transition_model = self._init_transition_model()
        self.observation_model = self._init_observation_model()
        
    def _init_transition_model(self) -> np.ndarray:
        """Initialize transition probability matrix P(s'|s,a)"""
        # Simplified: in practice, learned from simulation
        return self.rng.random((self.state_dim, self.action_dim, self.state_dim))
    
    def _init_observation_model(self) -> np.ndarray:
        """Initialize observation probability matrix O(o|s,a)"""
        return self.rng.random((self.state_dim, self.action_dim, self.state_dim))
    
    def compute_utility(self, state: np.ndarray, action: np.ndarray, 
                       swarm_state: SwarmState, scenario_id: str = "S1") -> float:
        """
        Compute utility function (Eq. 3.1-3.4).
        U = w1*U_time + w2*U_energy + w3*U_safety + w4*U_connectivity
        Weights adapt based on scenario.
        """
        # Scenario-adaptive weights (Section 4.4)
        scenario_weights = {
            "S1": np.array([0.4, 0.3, 0.2, 0.1]),  # Basic navigation
            "S2": np.array([0.3, 0.2, 0.4, 0.1]),  # Dense obstacles → safety priority
            "S3": np.array([0.2, 0.2, 0.3, 0.3]),  # Comms degradation → connectivity priority
            "S4": np.array([0.3, 0.4, 0.2, 0.1]),  # Agent failures → energy priority
            "S5": np.array([0.2, 0.5, 0.2, 0.1]),  # Energy constraints
            "S6": np.array([0.25, 0.25, 0.25, 0.25]),  # Combined stress
        }
        weights = scenario_weights.get(scenario_id, scenario_weights["S1"])
        
        # Time efficiency (inverse of estimated completion time)
        u_time = 1.0 / (np.linalg.norm(state[:2]) + 1e-6)
        
        # Energy consumption (based on action magnitude)
        u_energy = 1.0 / (np.linalg.norm(action) + 1e-6)
        
        # Safety (inverse of collision risk)
        u_safety = self._compute_safety_metric(swarm_state)
        
        # Connectivity (graph connectivity coefficient, Eq. 3.23)
        u_connectivity = self._compute_connectivity_metric(swarm_state)
        
        utilities = np.array([u_time, u_energy, u_safety, u_connectivity])
        return float(np.dot(weights, utilities))
    
    def _compute_safety_metric(self, swarm_state: SwarmState) -> float:
        """Compute safety metric based on obstacle distances"""
        if not hasattr(swarm_state, 'obstacles') or not swarm_state.obstacles:
            return 1.0
        min_dist = min([getattr(obs, 'distance', 10.0) for obs in swarm_state.obstacles])
        return min(min_dist / 5.0, 1.0)  # Normalize to [0,1]
    
    def _compute_connectivity_metric(self, swarm_state: SwarmState, comm_range: float = 100.0) -> float:
        """Compute connectivity coefficient (Eq. 3.23)"""
        agents = getattr(swarm_state, 'agents', [])
        if len(agents) <= 1:
            return 1.0
        connected_pairs = 0
        total_pairs = len(agents) * (len(agents) - 1) / 2
        for i in range(len(agents)):
            for j in range(i+1, len(agents)):
                pos_i = np.array([agents[i].position.x, agents[i].position.y, agents[i].position.z])
                pos_j = np.array([agents[j].position.x, agents[j].position.y, agents[j].position.z])
                dist = np.linalg.norm(pos_i - pos_j)
                if dist < comm_range:
                    connected_pairs += 1
        return connected_pairs / total_pairs if total_pairs > 0 else 0.0


# ============================================================================
# MARL Agent (Eq. 3.16-3.22)
# ============================================================================
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
    
    def get_correction(self, state: torch.Tensor) -> float:
        """Return scalar correction factor in [-1, 1] for utility adjustment"""
        with torch.no_grad():
            probs = self.forward(state.unsqueeze(0))
            # Use entropy of distribution as confidence measure
            entropy = -torch.sum(probs * torch.log(probs + 1e-8))
            max_entropy = np.log(self.fc3.out_features)
            confidence = (entropy / max_entropy).item()
            # Map confidence to correction: high confidence → small correction
            return float(1.0 - 2.0 * confidence)  # Range [-1, 1]


# ============================================================================
# Architecture-Specific Decision Strategies
# ============================================================================
class ArchitectureStrategy:
    """Base class for architecture-specific decision logic"""
    def __init__(self, node: Node):
        self.node = node
        self.rng = random.Random()
    
    def set_seed(self, seed: int):
        self.rng.seed(seed)
        np.random.seed(seed)
    
    def select_action(self, state: np.ndarray, swarm_state: SwarmState, 
                     scenario_id: str, **kwargs) -> Tuple[np.ndarray, float, str]:
        """
        Select action based on architecture.
        Returns: (action_vector, utility_score, method_name)
        """
        raise NotImplementedError


class CentralAStarStrategy(ArchitectureStrategy):
    """
    Centralized A* planning strategy.
    Global planner with full state knowledge, no MARL/Dec-POMDP.
    """
    def select_action(self, state: np.ndarray, swarm_state: SwarmState,
                     scenario_id: str, goal: Optional[np.ndarray] = None, **kwargs) -> Tuple[np.ndarray, float, str]:
        if goal is None:
            goal = np.array([100.0, 100.0, 0.0])  # Default goal
        
        # Simple A*-like heuristic: move toward goal
        direction = goal[:2] - state[:2]
        if np.linalg.norm(direction) < 1.0:
            action = np.array([0.0, 0.0, 0.0])  # Stop at goal
        else:
            action = direction / (np.linalg.norm(direction) + 1e-6)
            action = np.clip(action, -1.0, 1.0)
            action = np.array([action[0], action[1], 0.0])  # 2D movement
        
        # Utility: inverse distance to goal
        utility = 1.0 / (np.linalg.norm(state[:2] - goal[:2]) + 1e-6)
        return action, utility, "central_a_star"


class ReactiveStrategy(ArchitectureStrategy):
    """
    Reactive local behavior strategy.
    No global planning, only local obstacle avoidance.
    """
    def select_action(self, state: np.ndarray, swarm_state: SwarmState,
                     scenario_id: str, avoidance_range: float = 5.0, **kwargs) -> Tuple[np.ndarray, float, str]:
        # Default forward motion
        action = np.array([1.0, 0.0, 0.0])
        
        # Local obstacle avoidance (potential field)
        if hasattr(swarm_state, 'obstacles') and swarm_state.obstacles:
            repulsion = np.zeros(3)
            for obs in swarm_state.obstacles:
                obs_pos = np.array([obs.position.x, obs.position.y, obs.position.z])
                agent_pos = state[:3]
                dist = np.linalg.norm(obs_pos - agent_pos)
                if dist < avoidance_range and dist > 0.1:
                    repulsion += (agent_pos - obs_pos) / (dist ** 2)
            if np.linalg.norm(repulsion) > 0.1:
                action = repulsion / (np.linalg.norm(repulsion) + 1e-6)
                action = np.clip(action, -1.0, 1.0)
        
        # Simple utility: based on clearance
        utility = min(1.0, avoidance_range / (np.linalg.norm(repulsion) + 1e-6))
        return action, utility, "reactive"


class RuleDecStrategy(ArchitectureStrategy):
    """
    Decentralized rule-based strategy.
    Heuristic rules for coordination without central planner.
    """
    def select_action(self, state: np.ndarray, swarm_state: SwarmState,
                     scenario_id: str, comm_range: float = 100.0, **kwargs) -> Tuple[np.ndarray, float, str]:
        action = np.zeros(3)
        agents = getattr(swarm_state, 'agents', [])
        
        # Rule 1: Maintain formation with neighbors
        if len(agents) > 1:
            neighbor_offsets = []
            for agent in agents:
                if agent.id != getattr(swarm_state, 'self_id', 'agent_0'):
                    pos = np.array([agent.position.x, agent.position.y, agent.position.z])
                    dist = np.linalg.norm(pos - state[:3])
                    if dist < comm_range:
                        # Desired offset in formation (simple grid)
                        desired_offset = np.array([10.0, 0.0, 0.0])  # Example
                        neighbor_offsets.append(desired_offset - (pos - state[:3]))
            
            if neighbor_offsets:
                formation_correction = np.mean(neighbor_offsets, axis=0)[:2]
                action[:2] = np.clip(formation_correction / 10.0, -1.0, 1.0)
        
        # Rule 2: Basic goal seeking
        goal = kwargs.get('goal', np.array([100.0, 100.0, 0.0]))
        goal_dir = (goal[:2] - state[:2])
        if np.linalg.norm(goal_dir) > 5.0:
            action[:2] += 0.5 * goal_dir / (np.linalg.norm(goal_dir) + 1e-6)
        
        action = np.clip(action, -1.0, 1.0)
        utility = 0.5 + 0.5 * (1.0 - np.linalg.norm(action))  # Prefer smooth actions
        return action, utility, "rule_dec"


class MARLDecPOMDPStrategy(ArchitectureStrategy):
    """
    Hybrid MARL + Dec-POMDP strategy (proposed method).
    Combines probabilistic reasoning with learned policy correction.
    """
    def __init__(self, node: Node, dec_pomdp: DecPOMDPSolver, marl_agent: Optional[MARLAgent] = None):
        super().__init__(node)
        self.dec_pomdp = dec_pomdp
        self.marl_agent = marl_agent
    
    def select_action(self, state: np.ndarray, swarm_state: SwarmState,
                     scenario_id: str, exploration_rate: float = 0.1, 
                     **kwargs) -> Tuple[np.ndarray, float, str]:
        actions = self._generate_candidate_actions()
        best_action = None
        best_utility = -np.inf
        
        for action in actions:
            utility = self.dec_pomdp.compute_utility(state, action, swarm_state, scenario_id)
            
            # MARL correction (Eq. 3.20-3.22)
            if self.marl_agent is not None:
                state_tensor = torch.FloatTensor(state)
                correction = self.marl_agent.get_correction(state_tensor)
                # Adaptive correction strength based on scenario uncertainty
                uncertainty_factor = {"S3": 1.5, "S4": 1.3, "S6": 1.4}.get(scenario_id, 1.0)
                utility *= (1.0 + 0.1 * uncertainty_factor * correction)
            
            if utility > best_utility:
                best_utility = utility
                best_action = action
        
        if best_action is None:
            best_action = np.zeros(3)
            best_utility = 0.0
        
        return best_action, best_utility, "marl_decpomdp"
    
    def _generate_candidate_actions(self) -> List[np.ndarray]:
        """Generate discretized action candidates"""
        return [
            np.array([1.0, 0.0, 0.0]),   # Forward
            np.array([-1.0, 0.0, 0.0]),  # Backward
            np.array([0.0, 1.0, 0.0]),   # Left
            np.array([0.0, -1.0, 0.0]),  # Right
            np.array([0.0, 0.0, 1.0]),   # Up (UAV)
            np.array([0.0, 0.0, 0.0]),   # Stop
        ]


# ============================================================================
# Main Decision Core Node
# ============================================================================
class DecisionCoreNode(Node):
    """Main decision-making node supporting multiple control architectures."""
    
    def __init__(self):
        super().__init__('decision_core')
        
        # === NEW: Architecture selection parameters ===
        self.declare_parameter('architecture_id', 'marl_decpomdp')
        self.declare_parameter('planner_mode', 'hybrid')
        self.declare_parameter('use_dec_pomdp', True)
        self.declare_parameter('use_marl', True)
        self.declare_parameter('scenario_id', 'S1')
        self.declare_parameter('seed', 42)
        
        # Existing parameters
        self.declare_parameter('model_path', '')
        self.declare_parameter('dec_pomdp_horizon', 10)
        self.declare_parameter('exploration_rate', 0.1)
        
        # Read parameters
        self.architecture_id = self.get_parameter('architecture_id').value
        self.planner_mode = self.get_parameter('planner_mode').value
        self.use_dec_pomdp = self.get_parameter('use_dec_pomdp').value
        self.use_marl = self.get_parameter('use_marl').value
        self.scenario_id = self.get_parameter('scenario_id').value
        self.seed = self.get_parameter('seed').value
        self.model_path = self.get_parameter('model_path').value
        self.horizon = self.get_parameter('dec_pomdp_horizon').value
        self.exploration_rate = self.get_parameter('exploration_rate').value
        
        # Set random seeds for reproducibility
        random.seed(self.seed)
        np.random.seed(self.seed)
        if torch.cuda.is_available():
            torch.manual_seed(self.seed)
        
        self.get_logger().info(f'Architecture: {self.architecture_id}, Scenario: {self.scenario_id}, Seed: {self.seed}')
        
        # Initialize Dec-POMDP solver (used by marl_decpomdp and optionally others)
        self.dec_pomdp = DecPOMDPSolver(state_dim=12, action_dim=6, horizon=self.horizon, seed=self.seed)
        
        # Initialize MARL agent
        self.marl_agent = None
        if self.use_marl and self.architecture_id == 'marl_decpomdp':
            self.marl_agent = MARLAgent(state_dim=12, action_dim=6)
            if self.model_path and os.path.exists(self.model_path):
                try:
                    self.marl_agent.load_state_dict(torch.load(self.model_path, map_location='cpu', weights_only=False))
                    self.get_logger().info(f'✓ Loaded MARL model from {self.model_path}')
                except Exception as e:
                    self.get_logger().error(f'Failed to load MARL model: {e}')
            else:
                self.get_logger().warn('⚠ MARL model not found, using untrained policy')
        
        # === Initialize architecture-specific strategy ===
        self.strategy = self._create_strategy()
        self.strategy.set_seed(self.seed)
        
        # State management
        self.state_buffer = deque(maxlen=10)
        self.current_state: Optional[SwarmState] = None
        self.goal_position: Optional[np.ndarray] = None
        
        # Communication parameters (from launch/config)
        self.comm_range = 100.0  # Default, can be updated via parameter
        self.declare_parameter('communication_range', 100.0)
        
        # QoS profile
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Subscribers
        self.swarm_state_sub = self.create_subscription(
            SwarmState, '/swarm/state', self.swarm_state_callback, qos_profile
        )
        self.odom_sub = self.create_subscription(
            Odometry, 'odom', self.odom_callback, qos_profile
        )
        self.goal_sub = self.create_subscription(
            PoseStamped, '/goal', self.goal_callback, qos_profile
        )
        
        # Publishers
        self.decision_pub = self.create_publisher(DecisionOutput, '/agent/decision', qos_profile)
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', qos_profile)
        self.swarm_state_pub = self.create_publisher(SwarmState, "/swarm/state", 10)
        self.arch_info_pub = self.create_publisher(String, '/agent/architecture_info', 10)
        
        # Timers
        self.timer = self.create_timer(0.1, self.decision_loop)  # 10 Hz decision
        self.create_timer(1.0, self.publish_swarm_state)  # 1 Hz logging
        self.create_timer(5.0, self.publish_arch_info)  # 0.2 Hz architecture info
        
        self.get_logger().info(f'✓ Decision Core Node initialized [{self.architecture_id}]')
    
    def _create_strategy(self) -> ArchitectureStrategy:
        """Factory method to create architecture-specific strategy"""
        if self.architecture_id == 'central_a_star':
            return CentralAStarStrategy(self)
        elif self.architecture_id == 'reactive':
            return ReactiveStrategy(self)
        elif self.architecture_id == 'rule_dec':
            return RuleDecStrategy(self)
        elif self.architecture_id == 'marl_decpomdp':
            return MARLDecPOMDPStrategy(self, self.dec_pomdp, self.marl_agent)
        else:
            self.get_logger().warn(f'Unknown architecture "{self.architecture_id}", falling back to marl_decpomdp')
            return MARLDecPOMDPStrategy(self, self.dec_pomdp, self.marl_agent)
    
    def publish_arch_info(self):
        """Publish current architecture configuration for logging/analysis"""
        msg = String()
        msg.data = json.dumps({
            'architecture_id': self.architecture_id,
            'planner_mode': self.planner_mode,
            'use_marl': self.use_marl,
            'use_dec_pomdp': self.use_dec_pomdp,
            'scenario_id': self.scenario_id,
            'seed': self.seed,
            'comm_range': self.comm_range
        })
        self.arch_info_pub.publish(msg)
    
    def publish_swarm_state(self):
        """Publish current swarm state for logging"""
        if self.current_state is None:
            msg = SwarmState()
        else:
            msg = self.current_state
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        if not msg.agents:
            # Mock agents for testing
            for i in range(8):
                agent = AgentState()
                agent.id = f"agent_{i}"
                agent.position.x = float(i * 10)
                agent.position.y = float(i * 5)
                agent.status = "active"
                msg.agents.append(agent)
        self.swarm_state_pub.publish(msg)
    
    def swarm_state_callback(self, msg: SwarmState):
        """Process global swarm state"""
        self.current_state = msg
    
    def odom_callback(self, msg: Odometry):
        """Process local odometry"""
        state_vector = self._odom_to_state_vector(msg)
        self.state_buffer.append(state_vector)
    
    def goal_callback(self, msg: PoseStamped):
        """Receive goal position for planning"""
        self.goal_position = np.array([
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z
        ])
    
    def _odom_to_state_vector(self, odom: Odometry) -> np.ndarray:
        """Convert odometry to state vector for neural network"""
        pos = odom.pose.pose.position
        orient = odom.pose.pose.orientation
        vel = odom.twist.twist.linear
        return np.array([
            pos.x, pos.y, pos.z,
            orient.x, orient.y, orient.z, orient.w,
            vel.x, vel.y, vel.z,
            0.0  # Placeholder for energy/other
        ], dtype=np.float32)
    
    def decision_loop(self):
        """Main decision-making loop (10 Hz)"""
        if len(self.state_buffer) == 0:
            return
        
        current_state_vec = np.array(self.state_buffer[-1], dtype=np.float32)
        
        # Prepare kwargs for strategy
        kwargs = {
            'scenario_id': self.scenario_id,
            'comm_range': self.comm_range,
            'exploration_rate': self.exploration_rate,
        }
        if self.goal_position is not None:
            kwargs['goal'] = self.goal_position
        
        # Select action via architecture-specific strategy
        action, utility, method = self.strategy.select_action(
            current_state_vec, 
            self.current_state or SwarmState(),
            **kwargs
        )
        
        # Publish results
        self._publish_decision(action, utility, method)
        self._publish_velocity_command(action)
    
    def _publish_decision(self, action: np.ndarray, utility: float, method: str):
        """Publish decision output with metadata"""
        msg = DecisionOutput()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.action_vector = action.tolist()
        msg.utility = float(utility)
        msg.decision_method = method
        msg.architecture_id = self.architecture_id
        msg.scenario_id = self.scenario_id
        self.decision_pub.publish(msg)
    
    def _publish_velocity_command(self, action: np.ndarray):
        """Publish velocity command to low-level controller"""
        cmd = Twist()
        cmd.linear.x = float(np.clip(action[0], -1.0, 1.0))
        cmd.linear.y = float(np.clip(action[1], -1.0, 1.0))
        cmd.linear.z = float(np.clip(action[2], -0.5, 0.5)) if len(action) > 2 else 0.0
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