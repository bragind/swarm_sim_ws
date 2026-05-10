#!/usr/bin/env python3
#!/usr/bin/env python3
"""
MARL Agent Implementation. PyTorch-based policy network.
Corresponds to Eq. 3.16-3.22 (Actor-Critic with PPO objective).
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class MARLPPOAgent(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim=128, lr=3e-4, gamma=0.99, clip_epsilon=0.2):
        super().__init__()
        self.gamma = gamma
        self.clip_epsilon = clip_epsilon
        
        # Actor (Policy)
        self.actor = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
        # Critic (Value)
        self.critic = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        
        self.optimizer = optim.Adam(list(self.actor.parameters()) + list(self.critic.parameters()), lr=lr)
        
    def select_action(self, state, exploration=True):
        with torch.no_grad():
            state = torch.FloatTensor(state)
            probs = self.actor(state)
            dist = torch.distributions.Categorical(probs)
            action = dist.sample() if exploration else torch.argmax(probs)
            return action.item(), dist.log_prob(action).item()
            
    def compute_loss(self, states, actions, old_log_probs, returns, advantages):
        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        old_log_probs = torch.FloatTensor(old_log_probs)
        returns = torch.FloatTensor(returns)
        advantages = torch.FloatTensor(advantages)
        
        # Critic loss
        values = self.critic(states).squeeze()
        critic_loss = nn.MSELoss()(values, returns)
        
        # Actor loss (PPO clipped objective)
        probs = self.actor(states)
        dist = torch.distributions.Categorical(probs)
        log_probs = dist.log_prob(actions)
        ratio = torch.exp(log_probs - old_log_probs)
        
        actor_loss1 = ratio * advantages
        actor_loss2 = torch.clamp(ratio, 1-self.clip_epsilon, 1+self.clip_epsilon) * advantages
        actor_loss = -torch.min(actor_loss1, actor_loss2).mean()
        
        loss = actor_loss + 0.5 * critic_loss
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item()