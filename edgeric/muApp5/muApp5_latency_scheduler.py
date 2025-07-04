#!/usr/bin/env python3
"""
muApp5: Real-time Latency-Optimized Scheduler
==============================================

This muApp provides real-time scheduling decisions optimized for latency
using the same state space as muApp1 (no conversion needed).

Key features:
- Direct integration with muApp1's state format
- Real-time latency estimation and optimization
- Adaptive scheduling based on backlog, CQI, and inferred latency
- No model conversion required
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

import redis
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from edgeric_messenger import *

# Global variables for tracking metrics
total_brate = []
avg_CQIs = []
latency_history = deque(maxlen=100)  # Rolling window for latency estimation
ue_priorities = defaultdict(float)  # Track UE priorities over time
backlog_history = defaultdict(lambda: deque(maxlen=10))  # Track backlog changes


class LatencyOptimizedScheduler:
    """
    Real-time latency-optimized scheduler that works directly with muApp1 state space
    """
    
    def __init__(self, config=None):
        self.config = config or {
            'target_latency_ms': 10,  # Target latency in milliseconds
            'backlog_weight': 0.3,    # Weight for backlog in scheduling decision
            'cqi_weight': 0.4,        # Weight for CQI in scheduling decision
            'latency_weight': 0.3,    # Weight for latency priority
            'fairness_factor': 0.1,   # Fairness adjustment
            'history_window': 10,     # Window size for trend analysis
        }
        
        # Initialize tracking variables
        self.ue_latency_estimates = {}
        self.ue_service_history = defaultdict(lambda: deque(maxlen=20))
        self.last_scheduling_time = time.time()
        
    def estimate_latency(self, ue_id, backlog, cqi, buffer_size):
        """
        Estimate latency for a UE based on current conditions
        
        Latency estimation considers:
        - Backlog size (more backlog = higher latency)
        - CQI (better channel = lower latency)
        - Historical service patterns
        """
        
        # Base latency estimation
        # Higher backlog increases latency
        backlog_factor = min(backlog / 100000, 5.0)  # Normalize backlog
        
        # Better CQI reduces latency
        cqi_factor = max(1.0, 15.0 - cqi) / 15.0
        
        # Historical service factor
        recent_services = list(self.ue_service_history[ue_id])
        if recent_services:
            avg_service_interval = np.mean(recent_services) if recent_services else 1.0
            service_factor = min(avg_service_interval / 1000, 2.0)  # Normalize
        else:
            service_factor = 1.0
        
        # Combined latency estimate (in milliseconds)
        estimated_latency = (
            self.config['target_latency_ms'] * 
            (1 + backlog_factor * cqi_factor * service_factor)
        )
        
        # Store estimate for this UE
        self.ue_latency_estimates[ue_id] = estimated_latency
        
        return estimated_latency
    
    def calculate_latency_priority(self, ue_id, backlog, cqi, buffer_size):
        """
        Calculate latency-based priority for scheduling
        
        Higher priority = more urgent for latency optimization
        """
        
        # Estimate current latency
        estimated_latency = self.estimate_latency(ue_id, backlog, cqi, buffer_size)
        
        # Priority factors
        latency_urgency = max(0, estimated_latency - self.config['target_latency_ms'])
        backlog_urgency = min(backlog / buffer_size, 1.0) if buffer_size > 0 else 0
        channel_opportunity = cqi / 15.0  # Normalize CQI
        
        # Combined priority score
        priority = (
            self.config['latency_weight'] * latency_urgency +
            self.config['backlog_weight'] * backlog_urgency +
            self.config['cqi_weight'] * channel_opportunity
        )
        
        return priority
    
    def calculate_scheduling_weights(self, ue_data):
        """
        Calculate scheduling weights optimized for latency
        
        Args:
            ue_data: Dictionary with UE metrics {rnti: {CQI, Backlog, Tx_brate, ...}}
        
        Returns:
            weights: Array of [RNTI, weight, RNTI, weight, ...]
        """
        
        if not ue_data:
            return np.array([])
        
        num_ues = len(ue_data)
        weights = np.zeros(num_ues * 2)
        
        # Extract metrics
        RNTIs = list(ue_data.keys())
        CQIs = [data['CQI'] for data in ue_data.values()]
        BLs = [data['Backlog'] for data in ue_data.values()]
        
        # Calculate priorities for each UE
        priorities = []
        for i, rnti in enumerate(RNTIs):
            buffer_size = 300000  # Default buffer size (same as muApp1)
            priority = self.calculate_latency_priority(
                rnti, BLs[i], CQIs[i], buffer_size
            )
            priorities.append(priority)
            
            # Update service history
            current_time = time.time()
            if rnti in self.ue_service_history:
                last_service = self.ue_service_history[rnti][-1] if self.ue_service_history[rnti] else current_time
                service_interval = current_time - last_service
                self.ue_service_history[rnti].append(service_interval)
            else:
                self.ue_service_history[rnti].append(0)
        
        # Convert priorities to weights
        priorities = np.array(priorities)
        
        # Avoid division by zero
        if np.sum(priorities) == 0:
            # Equal weights if no priority differentiation
            normalized_weights = np.ones(num_ues) / num_ues
        else:
            # Normalize priorities to weights
            normalized_weights = priorities / np.sum(priorities)
            
            # Apply fairness adjustment
            fairness_adjustment = self.config['fairness_factor'] / num_ues
            normalized_weights = (
                normalized_weights * (1 - self.config['fairness_factor']) +
                fairness_adjustment
            )
        
        # Fill the weights array
        for i in range(num_ues):
            weights[i * 2] = RNTIs[i]
            weights[i * 2 + 1] = normalized_weights[i]
        
        return weights
    
    def log_metrics(self, ue_data, weights):
        """Log scheduling metrics for analysis"""
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate average estimated latency
        avg_estimated_latency = np.mean(list(self.ue_latency_estimates.values())) if self.ue_latency_estimates else 0
        
        # Log to file
        log_entry = {
            'timestamp': current_time,
            'num_ues': len(ue_data),
            'avg_estimated_latency': avg_estimated_latency,
            'ue_latencies': dict(self.ue_latency_estimates),
            'weights': weights.tolist() if len(weights) > 0 else [],
            'total_throughput': sum(data['Tx_brate'] for data in ue_data.values())
        }
        
        # Write to log file
        with open('muApp5_latency_log.txt', 'a') as f:
            f.write(f"{log_entry}\n")


def muapp5_latency_scheduler(eval_episodes, scheduler_config=None):
    """
    Main scheduling loop for muApp5 latency optimization
    """
    
    global total_brate, avg_CQIs
    
    # Initialize scheduler
    scheduler = LatencyOptimizedScheduler(scheduler_config)
    
    print(f"🚀 Starting muApp5 Latency-Optimized Scheduler")
    print(f"📊 Target latency: {scheduler.config['target_latency_ms']}ms")
    print(f"🔄 Running for {eval_episodes} episodes")
    
    for episode in range(eval_episodes):
        try:
            # Get current UE metrics
            ue_data = get_metrics_multi()
            
            if not ue_data:
                print("⚠️  No UE data available, skipping episode")
                time.sleep(0.1)
                continue
            
            # Calculate latency-optimized weights
            weights = scheduler.calculate_scheduling_weights(ue_data)
            
            if len(weights) > 0:
                # Send scheduling weights to EdgeRIC
                send_scheduling_weight(weights, True)
                
                # Log metrics
                scheduler.log_metrics(ue_data, weights)
                
                # Update global metrics for compatibility
                txb = [data['Tx_brate'] for data in ue_data.values()]
                total_brate.append(np.sum(txb))
                
                # Log progress
                if episode % 100 == 0:
                    avg_latency = np.mean(list(scheduler.ue_latency_estimates.values()))
                    print(f"Episode {episode}: {len(ue_data)} UEs, Avg Est. Latency: {avg_latency:.1f}ms")
                    
                    # Show current scheduling decision
                    for i in range(0, len(weights), 2):
                        rnti = int(weights[i])
                        weight = weights[i+1]
                        est_latency = scheduler.ue_latency_estimates.get(rnti, 0)
                        print(f"  UE {rnti}: weight={weight:.3f}, est_latency={est_latency:.1f}ms")
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.001)  # 1ms delay
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping muApp5 scheduler...")
            break
        except Exception as e:
            print(f"❌ Error in episode {episode}: {e}")
            time.sleep(0.1)
    
    print(f"✅ muApp5 completed {episode + 1} episodes")
    return total_brate


def main():
    """Main function for muApp5 latency scheduler"""
    
    parser = argparse.ArgumentParser(description="muApp5 Real-time Latency-Optimized Scheduler")
    parser.add_argument("--episodes", type=int, default=10000, 
                       help="Number of scheduling episodes to run")
    parser.add_argument("--target-latency", type=float, default=10.0,
                       help="Target latency in milliseconds")
    parser.add_argument("--latency-weight", type=float, default=0.3,
                       help="Weight for latency in scheduling decisions")
    parser.add_argument("--backlog-weight", type=float, default=0.3,
                       help="Weight for backlog in scheduling decisions")
    parser.add_argument("--cqi-weight", type=float, default=0.4,
                       help="Weight for CQI in scheduling decisions")
    parser.add_argument("--fairness-factor", type=float, default=0.1,
                       help="Fairness adjustment factor")
    parser.add_argument("--config-file", type=str, default=None,
                       help="JSON configuration file")
    
    args = parser.parse_args()
    
    # Build scheduler configuration
    scheduler_config = {
        'target_latency_ms': args.target_latency,
        'backlog_weight': args.backlog_weight,
        'cqi_weight': args.cqi_weight,
        'latency_weight': args.latency_weight,
        'fairness_factor': args.fairness_factor,
        'history_window': 10,
    }
    
    # Load config file if provided
    if args.config_file and os.path.exists(args.config_file):
        import json
        with open(args.config_file, 'r') as f:
            file_config = json.load(f)
            scheduler_config.update(file_config)
    
    print("🎯 muApp5: Real-time Latency-Optimized Scheduler")
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
    algorithm_name = "muApp5 Latency Scheduler"
    try:
        redis_db.set("algo", algorithm_name)
        print(f"📝 Algorithm set in Redis: {algorithm_name}")
    except:
        pass
    
    # Run the scheduler
    start_time = time.time()
    throughput_history = muapp5_latency_scheduler(args.episodes, scheduler_config)
    end_time = time.time()
    
    # Summary statistics
    print("\n📊 muApp5 Execution Summary")
    print("=" * 50)
    print(f"⏱️  Total runtime: {end_time - start_time:.2f} seconds")
    print(f"🔄 Episodes completed: {args.episodes}")
    print(f"📈 Average throughput: {np.mean(throughput_history):.2f} bps")
    print(f"📊 Total data transferred: {np.sum(throughput_history):.2f} bytes")
    print(f"📁 Log file: muApp5_latency_log.txt")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
