#!/usr/bin/env python3
"""
Real-time Latency Monitor for EdgeRIC
Extracts and plots UE latency values in real-time
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
from collections import deque
import time
from datetime import datetime

# Add the EdgeRIC path to import the messaging module
sys.path.append('/Users/makarand/EdgeRIC-A-real-time-RIC/edgeric')
from edgeric_messenger import get_metrics_multi

class LatencyMonitor:
    def __init__(self, max_points=500):
        self.max_points = max_points
        self.latency_data = {}  # Per-UE latency data
        self.time_data = {}     # Per-UE time data
        self.start_time = time.time()
        
        # Setup matplotlib
        plt.style.use('seaborn-v0_8')
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.lines = {}
        self.colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        # Setup plot
        self.ax.set_xlabel('Time (seconds)')
        self.ax.set_ylabel('Latency (microseconds)')
        self.ax.set_title('Real-time UE Latency Monitor')
        self.ax.grid(True, alpha=0.3)
        self.ax.legend()
        
        # Data collection thread control
        self.running = True
        
    def initialize_ue(self, rnti):
        """Initialize data structures for a new UE"""
        if rnti not in self.latency_data:
            self.latency_data[rnti] = deque(maxlen=self.max_points)
            self.time_data[rnti] = deque(maxlen=self.max_points)
            
            # Create line for this UE
            color = self.colors[len(self.lines) % len(self.colors)]
            line, = self.ax.plot([], [], color=color, label=f'UE {rnti}', 
                               linewidth=2, marker='o', markersize=3)
            self.lines[rnti] = line
            
    def update_latency_data(self, rnti, latency_us):
        """Update latency data for a UE"""
        if rnti not in self.latency_data:
            self.initialize_ue(rnti)
            
        current_time = time.time() - self.start_time
        self.latency_data[rnti].append(latency_us)
        self.time_data[rnti].append(current_time)
        
    def data_collection_thread(self):
        """Background thread to collect data from EdgeRIC"""
        print("Starting data collection thread...")
        
        while self.running:
            try:
                ue_data = get_metrics_multi()
                
                if ue_data:
                    for rnti, data in ue_data.items():
                        if 'Latency' in data:
                            latency_us = data['Latency']
                            self.update_latency_data(rnti, latency_us)
                            
                    # Print current values for debugging
                    current_time = datetime.now().strftime("%H:%M:%S")
                    print(f"[{current_time}] Latency values: ", end="")
                    for rnti, data in ue_data.items():
                        if 'Latency' in data:
                            latency_ms = data['Latency'] / 1000.0  # Convert to ms
                            print(f"UE{rnti}: {latency_ms:.1f}ms ", end="")
                    print()
                    
            except Exception as e:
                print(f"Error in data collection: {e}")
                
            time.sleep(0.1)  # 100ms update rate
            
    def update_plot(self, frame):
        """Update the matplotlib plot"""
        try:
            # Update all lines
            for rnti in self.latency_data:
                if len(self.latency_data[rnti]) > 0:
                    times = list(self.time_data[rnti])
                    latencies = list(self.latency_data[rnti])
                    self.lines[rnti].set_data(times, latencies)
            
            # Auto-scale the plot
            if any(len(data) > 0 for data in self.latency_data.values()):
                self.ax.relim()
                self.ax.autoscale_view()
                
            # Update legend
            self.ax.legend(loc='upper right')
            
        except Exception as e:
            print(f"Error updating plot: {e}")
            
        return list(self.lines.values())
    
    def start_monitoring(self):
        """Start the real-time monitoring"""
        print("Starting EdgeRIC Latency Monitor...")
        print("Press Ctrl+C to stop")
        
        # Start data collection thread
        data_thread = threading.Thread(target=self.data_collection_thread)
        data_thread.daemon = True
        data_thread.start()
        
        # Start animation
        try:
            ani = FuncAnimation(self.fig, self.update_plot, interval=100, 
                              blit=False, save_count=100)
            plt.tight_layout()
            plt.show()
        except KeyboardInterrupt:
            print("\nStopping monitor...")
        finally:
            self.running = False

def main():
    """Main function"""
    print("EdgeRIC Real-time Latency Monitor")
    print("=================================")
    
    # Check if EdgeRIC is running
    try:
        test_data = get_metrics_multi()
        if not test_data:
            print("Warning: No data received from EdgeRIC. Make sure EdgeRIC is running.")
        else:
            print(f"Found {len(test_data)} UEs in EdgeRIC")
    except Exception as e:
        print(f"Error connecting to EdgeRIC: {e}")
        print("Make sure EdgeRIC is running and accessible.")
        return
    
    # Start monitoring
    monitor = LatencyMonitor(max_points=500)
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
