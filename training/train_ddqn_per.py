"""
DQN implementation snippet for CloudScaleRL.
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
from collections import deque

class QNetwork(nn.Module):
    def __init__(self, state_size, action_size):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, action_size)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class DQNAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95    # discount rate
        self.epsilon = 1.0  # exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.model = QNetwork(state_size, action_size)
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        self.criterion = nn.MSELoss()

    def memorize(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state, mask=None):
        if np.random.rand() <= self.epsilon:
            if mask:
                valid_actions = [i for i, m in enumerate(mask) if m == 1]
                return random.choice(valid_actions)
            return random.randrange(self.action_size)
            
        state = torch.FloatTensor(state).unsqueeze(0)
        act_values = self.model(state)
        
        if mask:
            act_values = act_values.detach().numpy()[0]
            for i, m in enumerate(mask):
                if m == 0:
                    act_values[i] = -float('inf')
            return np.argmax(act_values)
            
        return torch.argmax(act_values[0]).item()

    def replay(self, batch_size):
        if len(self.memory) < batch_size:
            return
            
        minibatch = random.sample(self.memory, batch_size)
        
        # Simple training loop for snippet purposes
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:
                next_state_tensor = torch.FloatTensor(next_state).unsqueeze(0)
                target = (reward + self.gamma * torch.max(self.model(next_state_tensor)).item())
                
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            target_f = self.model(state_tensor)
            
            target_f_clone = target_f.clone().detach()
            target_f_clone[0][action] = target
            
            self.optimizer.zero_grad()
            loss = self.criterion(target_f, target_f_clone)
            loss.backward()
            self.optimizer.step()
            
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
