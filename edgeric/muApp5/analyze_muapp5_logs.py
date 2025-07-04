#!/usr/bin/env python3
"""
muApp5 Log Analysis Tool
========================

Analyzes muApp5 latency scheduler logs to provide insights on performance.
"""

import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

def parse_log_file(log_file):
    """Parse muApp5 log file and extract metrics"""
    
    data = []
    with open(log_file, 'r') as f:
        for line in f:
            try:
                # Each line is a JSON-like string
                entry = eval(line.strip())
                data.append(entry)
            except:
                continue
    
    return data

def analyze_latency_performance(data):
    """Analyze latency performance metrics"""
    
    print("📊 Latency Performance Analysis")
    print("=" * 40)
    
    if not data:
        print("No data available for analysis")
        return [], []
    
    # Extract latency estimates
    latency_estimates = []
    timestamps = []
    
    for entry in data:
        if 'avg_estimated_latency' in entry:
            latency_estimates.append(entry['avg_estimated_latency'])
            timestamps.append(entry['timestamp'])
    
    if latency_estimates:
        avg_latency = np.mean(latency_estimates)
        min_latency = np.min(latency_estimates)
        max_latency = np.max(latency_estimates)
        std_latency = np.std(latency_estimates)
        
        print(f"📈 Average Latency: {avg_latency:.2f} ms")
        print(f"📉 Min Latency: {min_latency:.2f} ms")
        print(f"📊 Max Latency: {max_latency:.2f} ms")
        print(f"📏 Std Deviation: {std_latency:.2f} ms")
        print(f"📋 Total Samples: {len(latency_estimates)}")
        
        # Latency distribution
        low_latency = sum(1 for l in latency_estimates if l < 10)
        medium_latency = sum(1 for l in latency_estimates if 10 <= l < 20)
        high_latency = sum(1 for l in latency_estimates if l >= 20)
        
        print(f"\n📊 Latency Distribution:")
        print(f"  < 10ms: {low_latency} ({low_latency/len(latency_estimates)*100:.1f}%)")
        print(f"  10-20ms: {medium_latency} ({medium_latency/len(latency_estimates)*100:.1f}%)")
        print(f"  > 20ms: {high_latency} ({high_latency/len(latency_estimates)*100:.1f}%)")
    
    return latency_estimates, timestamps

def analyze_scheduling_decisions(data):
    """Analyze scheduling decision patterns"""
    
    print("\n📊 Scheduling Decision Analysis")
    print("=" * 40)
    
    if not data:
        return
    
    # Extract scheduling weights
    weight_distributions = []
    num_ues_over_time = []
    
    for entry in data:
        if 'weights' in entry and 'num_ues' in entry:
            weights = entry['weights']
            num_ues = entry['num_ues']
            
            num_ues_over_time.append(num_ues)
            
            # Extract weight values (every other element)
            if len(weights) > 0:
                weight_values = [weights[i] for i in range(1, len(weights), 2)]
                weight_distributions.append(weight_values)
    
    if weight_distributions:
        # Flatten all weight values
        all_weights = [w for dist in weight_distributions for w in dist]
        
        if all_weights:
            avg_weight = np.mean(all_weights)
            min_weight = np.min(all_weights)
            max_weight = np.max(all_weights)
            
            print(f"⚖️  Average Weight: {avg_weight:.3f}")
            print(f"⚖️  Min Weight: {min_weight:.3f}")
            print(f"⚖️  Max Weight: {max_weight:.3f}")
            
            # Weight fairness analysis
            weight_std = np.std(all_weights)
            print(f"📊 Weight Std Dev: {weight_std:.3f}")
            print(f"📊 Fairness Score: {1 - weight_std:.3f}" if weight_std < 1 else "📊 Fairness Score: 0.00")
    
    if num_ues_over_time:
        avg_ues = np.mean(num_ues_over_time)
        print(f"👥 Average UEs: {avg_ues:.1f}")
        print(f"👥 Max UEs: {max(num_ues_over_time)}")
        print(f"👥 Min UEs: {min(num_ues_over_time)}")

def analyze_throughput_performance(data):
    """Analyze throughput performance"""
    
    print("\n📊 Throughput Performance Analysis")
    print("=" * 40)
    
    if not data:
        return []
    
    throughputs = []
    for entry in data:
        if 'total_throughput' in entry:
            throughputs.append(entry['total_throughput'])
    
    if throughputs:
        avg_throughput = np.mean(throughputs)
        min_throughput = np.min(throughputs)
        max_throughput = np.max(throughputs)
        
        print(f"📈 Average Throughput: {avg_throughput:.2f} bps")
        print(f"📉 Min Throughput: {min_throughput:.2f} bps")
        print(f"📊 Max Throughput: {max_throughput:.2f} bps")
        print(f"📏 Total Data: {sum(throughputs):.2f} bytes")
    
    return throughputs

def plot_metrics(latency_estimates, timestamps, throughputs, output_file=None):
    """Create visualizations of the metrics"""
    
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot latency over time
        if latency_estimates and timestamps:
            ax1.plot(range(len(latency_estimates)), latency_estimates, 'b-', linewidth=1)
            ax1.set_title('Estimated Latency Over Time')
            ax1.set_xlabel('Episode')
            ax1.set_ylabel('Latency (ms)')
            ax1.grid(True)
            ax1.axhline(y=10, color='r', linestyle='--', alpha=0.7, label='Target (10ms)')
            ax1.legend()
        
        # Plot throughput over time
        if throughputs:
            ax2.plot(range(len(throughputs)), throughputs, 'g-', linewidth=1)
            ax2.set_title('Throughput Over Time')
            ax2.set_xlabel('Episode')
            ax2.set_ylabel('Throughput (bps)')
            ax2.grid(True)
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"📊 Plot saved to: {output_file}")
        else:
            plt.show()
            
    except ImportError:
        print("⚠️  Matplotlib not available. Skipping plots.")

def main():
    parser = argparse.ArgumentParser(description="Analyze muApp5 latency scheduler logs")
    parser.add_argument("log_file", help="Path to muApp5 log file")
    parser.add_argument("--plot", action="store_true", help="Generate plots")
    parser.add_argument("--output", help="Output file for plots")
    parser.add_argument("--summary", action="store_true", help="Show summary only")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.log_file):
        print(f"❌ Log file not found: {args.log_file}")
        return 1
    
    print("🔍 muApp5 Log Analysis Tool")
    print("=" * 40)
    print(f"📁 Log file: {args.log_file}")
    print()
    
    # Parse log file
    data = parse_log_file(args.log_file)
    
    if not data:
        print("❌ No valid data found in log file")
        return 1
    
    print(f"📊 Total log entries: {len(data)}")
    
    # Analyze different aspects
    latency_estimates, timestamps = analyze_latency_performance(data)
    
    if not args.summary:
        analyze_scheduling_decisions(data)
        throughputs = analyze_throughput_performance(data)
        
        # Generate plots if requested
        if args.plot:
            plot_metrics(latency_estimates, timestamps, throughputs, args.output)
    
    print("\n✅ Analysis complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
