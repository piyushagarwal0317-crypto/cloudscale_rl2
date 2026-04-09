"""
PPO implementation snippet for CloudScaleRL.
"""
import torch
import torch.nn as nn
from torch.distributions import Categorical

class ActorCritic(nn.Module):
    def __init__(self, state_size, action_size):
        super(ActorCritic, self).__init__()
        
        # Actor
        self.actor = nn.Sequential(
            nn.Linear(state_size, 64),
            nn.Tanh(),
            nn.Linear(64, 64),
            nn.Tanh(),
            nn.Linear(64, action_size),
            nn.Softmax(dim=-1)
        )
        
        # Critic
        self.critic = nn.Sequential(
            nn.Linear(state_size, 64),
            nn.Tanh(),
            nn.Linear(64, 64),
            nn.Tanh(),
            nn.Linear(64, 1)
        )
        
    def forward(self):
        raise NotImplementedError
        
    def act(self, state, mask=None):
        state = torch.FloatTensor(state)
        action_probs = self.actor(state)
        
        if mask is not None:
            mask_tensor = torch.FloatTensor(mask)
            action_probs = action_probs * mask_tensor
            # Renormalize
            sum_probs = torch.sum(action_probs)
            if sum_probs > 0:
                action_probs = action_probs / sum_probs
            else:
                # Fallback if masking zeroes everything (shouldn't happen with proper masking)
                action_probs = torch.ones_like(action_probs) / len(action_probs)
                
        dist = Categorical(action_probs)
        action = dist.sample()
        
        action_logprob = dist.log_prob(action)
        state_val = self.critic(state)
        
        return action.detach().item(), action_logprob.detach().item(), state_val.detach().item()

    def evaluate(self, state, action):
        action_probs = self.actor(state)
        dist = Categorical(action_probs)
        
        action_logprobs = dist.log_prob(action)
        dist_entropy = dist.entropy()
        state_values = self.critic(state)
        
        return action_logprobs, state_values, dist_entropy
