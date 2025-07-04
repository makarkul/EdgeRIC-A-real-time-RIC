#!/usr/bin/env python3
"""
muApp5: Real-time Latency-Optimized Scheduler
==============================================

This muApp uses trained models from muApp4 for real-time latency-optimized scheduling.
It loads the latency-optimized model and applies it to live EdgeRIC data.

Key features:
- Uses trained models from muApp4 (latency-optimized)
- Real-time inference with latency optimization
- Same state space as muApp1 but with latency focus
- Automatic model loading and deployment
"""

import argparse
import os
import pickle
import sys
from collections import defaultdict, deque
from datetime import datetime
from threading import Thread
import numpy as np
import time
import torch

import redis
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from edgeric_messenger import *

# Global variables for tracking metrics
total_brate = []
avg_CQIs = []
latency_history = deque(maxlen=100)

class LatencyModelScheduler:
    """
    Real-time scheduler using latency-optimized models from muApp4
    """
    
    def __init__(self, model_path=None, config=None):
        self.config = config or {
            'default_latency_ms': 10,  # Default latency estimate when not available
            'model_path': model_path or 'muApp5_trained_model.pt',
            'use_algorithmic_fallback': True,  # Fallback to algorithmic if model fails
        }
        
        # Load the trained model
        self.model = None
        self.load_model()
        
        # Fallback algorithmic scheduler
        self.algorithmic_scheduler = AlgorithmicLatencyScheduler()
        
        # Tracking variables
        self.model_success_count = 0
        self.model_failure_count = 0
        self.use_model = True
        
    def load_model(self):
        """Load the trained latency-optimized model from muApp4"""
        
        model_path = self.config['model_path']
        
        # Try multiple possible locations
        possible_paths = [
            model_path,
            os.path.join(os.path.dirname(__file__), model_path),
            os.path.join(os.path.dirname(__file__), '..', 'muApp4', 'outputs', '**', 'model_best.pt'),
            os.path.join(os.path.dirname(__file__), 'muApp5_trained_model.pt')
        ]
        
        for path in possible_paths:
            if '*' in path:
                # Handle wildcard paths
                import glob
                matches = glob.glob(path, recursive=True)
                if matches:
                    path = matches[0]  # Use the first match
                else:
                    continue
            
            if os.path.exists(path):
                try:
                    print(f"📦 Loading model from: {path}")
                    self.model = torch.load(path, map_location=torch.device('cpu'))
                    self.model.eval()
                    print(f"✅ Model loaded successfully")
                    return
                except Exception as e:
                    print(f"❌ Error loading model from {path}: {e}")
                    continue
        
        print(f"⚠️  No trained model found. Available options:")
        print(f"   1. Train a model using muApp4")
        print(f"   2. Use algorithmic fallback")
        
        if self.config['use_algorithmic_fallback']:
            print(f"🔄 Using algorithmic fallback scheduler")
            self.use_model = False
        else:
            raise FileNotFoundError(f"No model found and algorithmic fallback disabled")
    
    def get_model_input(self, ue_data):
        """
        Convert UE data to model input format
        
        For muApp4 trained models, we need: [BL, CQI, LAT, MB, LP] per UE
        But we only have [BL, CQI, MB] from real system, so we estimate LAT and LP
        """
        
        if not ue_data:
            return None
        
        num_ues = len(ue_data)
        
        # Extract available metrics
        RNTIs = list(ue_data.keys())
        CQIs = [data['CQI'] for data in ue_data.values()]
        BLs = [data['Backlog'] for data in ue_data.values()]
        
        # Use default buffer size (same as muApp1)
        MBs = [300000] * num_ues
        
        # Estimate latency (simple heuristic)
        estimated_latencies = []
        for i in range(num_ues):
            # Estimate latency based on backlog and CQI
            backlog_factor = min(BLs[i] / 100000, 2.0)  # Normalize backlog
            cqi_factor = max(1.0, 15.0 - CQIs[i]) / 15.0  # Better CQI = lower latency
            estimated_latency = self.config['default_latency_ms'] * 1000 * (1 + backlog_factor * cqi_factor)  # Convert to microseconds
            estimated_latencies.append(estimated_latency)
        
        # Calculate latency priorities (CQI * Latency)
        latency_priorities = [CQIs[i] * estimated_latencies[i] for i in range(num_ues)]
        
        # Create model input: [BL1, CQI1, LAT1, MB1, LP1, BL2, CQI2, LAT2, MB2, LP2, ...]
        model_input = []
        for i in range(num_ues):
            model_input.extend([
                BLs[i],
                CQIs[i], 
                estimated_latencies[i],
                MBs[i],
                latency_priorities[i]
            ])
        
        return np.array(model_input, dtype=np.float32)
    
    def get_scheduling_weights(self, ue_data):
        """Get scheduling weights using the trained model or algorithmic fallback"""
        
        if not ue_data:
            return np.array([])
        
        num_ues = len(ue_data)
        weights = np.zeros(num_ues * 2)
        RNTIs = list(ue_data.keys())
        
        try:
            if self.use_model and self.model is not None:
                # Use trained model
                model_input = self.get_model_input(ue_data)
                if model_input is not None:
                    # Convert to tensor
                    input_tensor = torch.from_numpy(model_input).unsqueeze(0)
                    
                    # Get action from model
                    with torch.no_grad():
                        action = self.model.select_action(input_tensor)
                        action = torch.squeeze(action).numpy()
                    
                    # Convert action to weights
                    if len(action) == num_ues:
                        normalized_action = action / np.sum(action) if np.sum(action) > 0 else np.ones(num_ues) / num_ues
                        
                        # Fill weights array
                        for i in range(num_ues):
                            weights[i * 2] = RNTIs[i]
                            weights[i * 2 + 1] = normalized_action[i]
                        
                        self.model_success_count += 1
                        return weights
                    else:
                        print(f"⚠️  Model output size mismatch: got {len(action)}, expected {num_ues}")
                        
            # Fallback to algorithmic scheduler
            self.model_failure_count += 1
            return self.algorithmic_scheduler.get_scheduling_weights(ue_data)
            
        except Exception as e:
            print(f"❌ Model inference error: {e}")
            self.model_failure_count += 1
            return self.algorithmic_scheduler.get_scheduling_weights(ue_data)


class AlgorithmicLatencyScheduler:
    """
    Fallback algorithmic scheduler for when model is not available
    """
    
    def __init__(self):
        self.ue_service_history = defaultdict(lambda: deque(maxlen=20))
        
    def get_scheduling_weights(self, ue_data):
        """Calculate scheduling weights using latency-focused algorithm"""
        
        if not ue_data:
            return np.array([])
        
        num_ues = len(ue_data)
        weights = np.zeros(num_ues * 2)
        
        # Extract metrics
        RNTIs = list(ue_data.keys())
        CQIs = [data['CQI'] for data in ue_data.values()]
        BLs = [data['Backlog'] for data in ue_data.values()]
        
        # Calculate latency-based priorities
        priorities = []
        for i in range(num_ues):
            # Priority based on backlog urgency and channel quality
            backlog_urgency = min(BLs[i] / 100000, 1.0)  # Normalize backlog
            channel_quality = CQIs[i] / 15.0  # Normalize CQI
            
            # Higher priority for high backlog and good channel
            priority = backlog_urgency * 0.6 + channel_quality * 0.4
            priorities.append(priority)
        
        # Normalize priorities to weights
        priorities = np.array(priorities)
        if np.sum(priorities) > 0:
            normalized_weights = priorities / np.sum(priorities)
        else:
            normalized_weights = np.ones(num_ues) / num_ues
        
        # Fill weights array
        for i in range(num_ues):
            weights[i * 2] = RNTIs[i]
            weights[i * 2 + 1] = normalized_weights[i]
        
        return weights


def muapp5_model_scheduler(eval_episodes, model_path=None, config=None):
    """
    Main scheduling loop for muApp5 using trained models
    """
    
    global total_brate
    
    # Initialize scheduler
    scheduler = LatencyModelScheduler(model_path, config)
    
    print(f"🚀 Starting muApp5 Model-based Latency Scheduler")
    print(f"� Model: {'Loaded' if scheduler.model else 'Algorithmic Fallback'}")
    print(f"🔄 Running for {eval_episodes} episodes")
    
    for episode in range(eval_episodes):
        try:
            # Get current UE metrics
            ue_data = get_metrics_multi()
            
            if not ue_data:
                if episode % 1000 == 0:
                    print("⚠️  No UE data available")
                time.sleep(0.1)
                continue
            
            # Get scheduling weights
            weights = scheduler.get_scheduling_weights(ue_data)
            
            if len(weights) > 0:
                # Send scheduling weights to EdgeRIC
                send_scheduling_weight(weights, True)
                
                # Update global metrics
                txb = [data['Tx_brate'] for data in ue_data.values()]
                total_brate.append(np.sum(txb))
                
                # Log progress
                if episode % 100 == 0:
                    model_success_rate = scheduler.model_success_count / (scheduler.model_success_count + scheduler.model_failure_count) * 100 if (scheduler.model_success_count + scheduler.model_failure_count) > 0 else 0
                    print(f"Episode {episode}: {len(ue_data)} UEs, Model Success: {model_success_rate:.1f}%")
                    
                    # Show current scheduling decision
                    for i in range(0, len(weights), 2):
                        rnti = int(weights[i])
                        weight = weights[i+1]
                        print(f"  UE {rnti}: weight={weight:.3f}")
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.001)  # 1ms delay
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping muApp5 scheduler...")
            break
        except Exception as e:
            print(f"❌ Error in episode {episode}: {e}")
            time.sleep(0.1)
    
    # Final statistics
    total_episodes = scheduler.model_success_count + scheduler.model_failure_count
    if total_episodes > 0:
        print(f"\n📊 Final Statistics:")
        print(f"  Model Success: {scheduler.model_success_count}/{total_episodes} ({scheduler.model_success_count/total_episodes*100:.1f}%)")
        print(f"  Algorithmic Fallback: {scheduler.model_failure_count}/{total_episodes} ({scheduler.model_failure_count/total_episodes*100:.1f}%)")
    
    print(f"✅ muApp5 completed {episode + 1} episodes")
    return total_brate


def main():
    """Main function for muApp5 model-based scheduler"""
    
    parser = argparse.ArgumentParser(description="muApp5 Model-based Latency Scheduler")
    parser.add_argument("--episodes", type=int, default=10000,
                       help="Number of scheduling episodes to run")
    parser.add_argument("--model-path", type=str, default="muApp5_trained_model.pt",
                       help="Path to the trained model file")
    parser.add_argument("--default-latency", type=float, default=10.0,
                       help="Default latency estimate in milliseconds")
    parser.add_argument("--no-fallback", action="store_true",
                       help="Disable algorithmic fallback")
    
    args = parser.parse_args()
    
    # Build scheduler configuration
    scheduler_config = {
        'default_latency_ms': args.default_latency,
        'model_path': args.model_path,
        'use_algorithmic_fallback': not args.no_fallback,
    }
    
    print("🎯 muApp5: Model-based Latency Scheduler")
    print("=" * 50)
    print("Configuration:")
    for key, value in scheduler_config.items():
        print(f"  {key}: {value}")
    print("=" * 50)
    
    # Initialize Redis connection
    try:
        redis_db = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_db.ping()
        print("✅ Redis connection established")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("   Continuing without Redis integration...")
    
    # Set algorithm identifier
    algorithm_name = "muApp5 Model-based Latency Scheduler"
    try:
        redis_db.set("algo", algorithm_name)
        print(f"📝 Algorithm set in Redis: {algorithm_name}")
    except:
        pass
    
    # Run the scheduler
    start_time = time.time()
    throughput_history = muapp5_model_scheduler(args.episodes, args.model_path, scheduler_config)
    end_time = time.time()
    
    # Summary statistics
    print("\n📊 muApp5 Execution Summary")
    print("=" * 50)
    print(f"⏱️  Total runtime: {end_time - start_time:.2f} seconds")
    print(f"🔄 Episodes completed: {args.episodes}")
    print(f"📈 Average throughput: {np.mean(throughput_history):.2f} bps")
    print(f"📊 Total data transferred: {np.sum(throughput_history):.2f} bytes")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
