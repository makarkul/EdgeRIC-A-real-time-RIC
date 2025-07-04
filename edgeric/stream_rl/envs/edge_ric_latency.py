import numpy as np
import pandas as pd
import torch
import gym
from gym.spaces import MultiDiscrete, Box, Discrete
from stream_rl.registry import register_env, create_reward
from ray.rllib.env.env_context import EnvContext
from collections import deque
import random
import zmq
import time
import sys
import os

# Add the edgeric directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from edgeric_messenger import *

gym.logger.set_level(40)


@register_env("EdgeRIC_Latency")
class EdgeRICLatency(gym.Env):
    """EdgeRIC Latency-Optimized Env: Focuses on latency minimization for real-time applications"""

    def __init__(self, config: EnvContext):
        self.seed = config["seed"]
        if self.seed != -1:
            random.seed(self.seed)
            np.random.seed(self.seed)
        self.T = config["T"]
        self.t = None
        self.num_UEs = config["num_UEs"]
        self.numArms = config["num_UEs"]
        self.numParams = 4  # backlog, cqi, latency, tx_bytes
        self.total_rbgs = config["num_RBGs"]
        self.cqi_map = config["cqi_map"]
        self.stall = 0
        
        # Latency-specific configuration
        self.latency_config = config.get("latency_config", {})
        
        # Delay mechanism
        self.state_delay = config["delay_state"]
        self.action_delay = config["delay_action"]
        self.state_history = deque(
            [np.array([0, 0, 0, 0] * self.num_UEs)] * (self.state_delay + 1),
            maxlen=self.state_delay + 1,
        )
        self.action_history = deque(
            [np.zeros(shape=(self.num_UEs,))] * (self.action_delay + 1),
            maxlen=self.action_delay + 1,
        )

        # Backlog Buffer Elements
        self.max_len_backlog = int(config["base_station"]["max_len"])
        self.backlog_lens = []
        self.backlog_population_params = config["backlog_population"]
        if (
            len(self.backlog_population_params) != self.num_UEs
        ):  # same params to all UEs backlog population
            self.backlog_population_params = [
                self.backlog_population_params
            ] * self.num_UEs

        # CQI Elements
        self.cqis = []
        self.mbs = []
        
        # Latency tracking
        self.latencies = []  # Per-UE latency values
        self.latency_history = deque(maxlen=100)  # Rolling window for average latency
        
        self.action_space = Box(
            low=0.0, high=1.0, shape=(self.num_UEs,), dtype=np.float32
        )
        
        # Extended observation space to include latency
        # [backlog, cqi, latency, tx_bytes] per UE
        max_latency = 100000  # 100ms max latency in microseconds
        max_tx_bytes = 10000000  # 10MB max
        
        self.observation_space = Box(
            low=np.array([0, 0, 0, 0] * self.num_UEs),
            high=np.array([self.max_len_backlog, 15, max_latency, max_tx_bytes] * self.num_UEs),
            dtype=np.float32,
        )
       
        self.augment_state_space = config["augment_state_space"]
        if self.augment_state_space:
            # Include additional latency-derived features
            self.observation_space = Box(
                low=np.array([0, 0, 0, 0, 0] * self.num_UEs),
                high=np.array([
                    self.max_len_backlog, 15, max_latency, max_tx_bytes, 
                    15 * max_latency  # latency-cqi product for priority
                ] * self.num_UEs),
                dtype=np.float32,
            )

        self.reward_func = create_reward(config["reward"])

    def reset(self):
        self.t = 0
        self.stall = 0
        
        self.backlog_lens = [0] * self.num_UEs
        self.cqis = [1] * self.num_UEs
        self.mbs = [3000000] * self.num_UEs
        self.latencies = [0] * self.num_UEs
        self.latency_history.clear()
        
        if self.augment_state_space:
            # Include latency-priority features
            self.latency_priorities = [
                cqi * latency if latency > 0 else 0
                for cqi, latency in zip(self.cqis, self.latencies)
            ]
            init_state = np.array(
                [
                    param[ue]
                    for ue in range(self.num_UEs)
                    for param in (self.backlog_lens, self.cqis, self.latencies, self.mbs, self.latency_priorities)
                ],
                dtype=np.float32,
            )  # [BL1, CQI1, LAT1, MB1, LP1, BL2, CQI2, LAT2, MB2, LP2, ...]
        else:
            init_state = np.array(
                [
                    param[ue]
                    for ue in range(self.num_UEs)
                    for param in (self.backlog_lens, self.cqis, self.latencies, self.mbs)
                ],
                dtype=np.float32,
            )  # [BL1, CQI1, LAT1, MB1, BL2, CQI2, LAT2, MB2, ...]

        self.state_history.append(init_state)
        return self.state_history[0]

    def get_current_latencies(self):
        """Get latency metrics from EdgeRIC system"""
        try:
            # Get metrics from EdgeRIC
            ue_data = get_metrics_multi()
            current_latencies = []
            
            for rnti in sorted(ue_data.keys()):
                # Extract latency for each UE (assuming latency is in microseconds)
                latency = ue_data[rnti].get('Latency', 0)
                current_latencies.append(latency)
            
            return current_latencies
        except Exception as e:
            print(f"Error getting latency metrics: {e}")
            # Return default latencies if metrics unavailable
            return [10000] * self.num_UEs  # 10ms default

    def step(self, action, RNTIs, CQIs, BLs, tx_bytes, MBs):
        
        action = np.clip(
            action, a_min=0.00000001, a_max=1.0
        )  # Project action back to action space + add epsilon to prevent divide by zero error

        # Add delay to action
        self.action_history.append(action)
        action = self.action_history[0]

        # Update time
        self.t += 1
        
        num_ues = len(RNTIs)
        
        # Get current latency metrics
        current_latencies = self.get_current_latencies()
        
        for ue in range(min(num_ues, len(current_latencies))): 
            self.mbs[ue] = MBs[ue] if ue < len(MBs) else 3000000
            self.cqis[ue] = CQIs[ue] if ue < len(CQIs) else 1
            self.backlog_lens[ue] = BLs[ue] if ue < len(BLs) else 0
            self.latencies[ue] = current_latencies[ue]

        # Calculate average latency for reward function
        avg_latency = np.mean(self.latencies) if self.latencies else 10000
        self.latency_history.append(avg_latency)
        
        # Latency-aware reward calculation
        if hasattr(self.reward_func, '__name__') and 'latency' in self.reward_func.__name__:
            reward = self.reward_func(
                tx_bytes, 
                self.backlog_lens, 
                self.stall, 
                avg_latency=avg_latency,
                latency_config=self.latency_config
            )
        else:
            # Fallback to standard reward
            reward = self.reward_func(tx_bytes, self.backlog_lens, self.stall)
      
        self.stall = 0
        
        if self.augment_state_space:
            # Calculate latency-based priorities
            self.latency_priorities = [
                cqi * latency if latency > 0 else 0
                for cqi, latency in zip(self.cqis, self.latencies)
            ]
            next_state = np.array(
                [
                    param[ue]
                    for ue in range(num_ues)
                    for param in (self.backlog_lens, self.cqis, self.latencies, self.mbs, self.latency_priorities)
                ],
                dtype=np.float32,
            )
        else:
            next_state = np.array(
                [
                    param[ue]
                    for ue in range(num_ues)
                    for param in (self.backlog_lens, self.cqis, self.latencies, self.mbs)
                ],
                dtype=np.float32,
            )

        done = self.t == self.T
        
        # Additional info for debugging and analysis
        info = {
            'avg_latency': avg_latency,
            'max_latency': max(self.latencies) if self.latencies else 0,
            'min_latency': min(self.latencies) if self.latencies else 0,
            'latency_std': np.std(self.latencies) if self.latencies else 0,
            'throughput': tx_bytes
        }
     
        self.state_history.append(next_state)  # Add delay to state observation
        return self.state_history[0], reward, done, info
