#!/usr/bin/env python3
"""
Log-based Latency Monitor for EdgeRIC
Extracts latency values from EdgeRIC log output and creates real-time plots
"""

import re
import sys
import time
import subprocess
import threading
from collections import deque, defaultdict
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime

class LogLatencyMonitor:
    def __init__(self, max_points=500):
        self.max_points = max_points
        self.latency_data = defaultdict(lambda: deque(maxlen=max_points))
        self.time_data = defaultdict(lambda: deque(maxlen=max_points))
        self.start_time = time.time()
        
        # Setup matplotlib
        plt.style.use('seaborn-v0_8')
        self.fig, self.ax = plt.subplots(figsize=(14, 8))
        self.lines = {}
        self.colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'cyan', 'magenta']
        
        # Setup plot
        self.ax.set_xlabel('Time (seconds)')
        self.ax.set_ylabel('Latency (milliseconds)')
        self.ax.set_title('Real-time UE Latency Monitor (from EdgeRIC logs)')
        self.ax.grid(True, alpha=0.3)
        
        # Data collection control
        self.running = True
        self.latest_values = {}
        
    def parse_ue_data(self, line):
        """Parse UE data from log line"""
        # Look for pattern: UE Dictionary: {70: {'CQI': 11, ..., 'Latency': 2851473}, 71: {...}}
        pattern = r"UE Dictionary: \{([^}]+)\}"
        match = re.search(pattern, line)
        
        if match:
            ue_dict_str = match.group(1)
            # Parse individual UE entries
            ue_pattern = r"(\d+):\s*\{[^}]*'Latency':\s*(\d+)[^}]*\}"
            ue_matches = re.findall(ue_pattern, ue_dict_str)
            
            result = {}
            for ue_id, latency in ue_matches:
                result[int(ue_id)] = int(latency)
            
            return result
        return None
    
    def initialize_ue(self, ue_id):
        """Initialize plotting line for a UE"""
        if ue_id not in self.lines:
            color = self.colors[len(self.lines) % len(self.colors)]
            line, = self.ax.plot([], [], color=color, label=f'UE {ue_id}', 
                               linewidth=2, marker='o', markersize=3)
            self.lines[ue_id] = line
            
    def update_latency_data(self, ue_id, latency_us):
        """Update latency data for a UE"""
        self.initialize_ue(ue_id)
        
        current_time = time.time() - self.start_time
        latency_ms = latency_us / 1000.0  # Convert to milliseconds
        
        self.latency_data[ue_id].append(latency_ms)
        self.time_data[ue_id].append(current_time)
        self.latest_values[ue_id] = latency_ms
        
    def monitor_docker_logs(self):
        """Monitor Docker container logs for latency data"""
        print("Starting Docker log monitoring...")
        
        process = None
        try:
            # Follow the EdgeRIC container logs
            process = subprocess.Popen(
                ['docker', 'logs', '-f', 'edgeric_test'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if not self.running:
                        break
                        
                    # Parse UE data from the line
                    ue_data = self.parse_ue_data(line)
                    if ue_data:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] Latency: ", end="")
                        
                        for ue_id, latency_us in ue_data.items():
                            self.update_latency_data(ue_id, latency_us)
                            print(f"UE{ue_id}: {latency_us/1000:.1f}ms ", end="")
                        print()
                    
        except Exception as e:
            print(f"Error monitoring Docker logs: {e}")
        finally:
            if process:
                process.terminate()
                
    def update_plot(self, frame):
        """Update the matplotlib plot"""
        try:
            # Update all lines
            for ue_id in self.latency_data:
                if len(self.latency_data[ue_id]) > 0:
                    times = list(self.time_data[ue_id])
                    latencies = list(self.latency_data[ue_id])
                    self.lines[ue_id].set_data(times, latencies)
            
            # Auto-scale the plot
            if any(len(data) > 0 for data in self.latency_data.values()):
                self.ax.relim()
                self.ax.autoscale_view()
                
                # Update title with latest values
                if self.latest_values:
                    title_text = "Real-time UE Latency Monitor - Latest: "
                    for ue_id, latency in self.latest_values.items():
                        title_text += f"UE{ue_id}: {latency:.1f}ms "
                    self.ax.set_title(title_text)
                
            # Update legend
            self.ax.legend(loc='upper right')
            
        except Exception as e:
            print(f"Error updating plot: {e}")
            
        return list(self.lines.values())
    
    def start_monitoring(self):
        """Start the real-time monitoring"""
        print("Starting EdgeRIC Log-based Latency Monitor...")
        print("This will monitor Docker container logs for latency data")
        print("Press Ctrl+C to stop")
        
        # Start log monitoring thread
        log_thread = threading.Thread(target=self.monitor_docker_logs)
        log_thread.daemon = True
        log_thread.start()
        
        # Start animation
        try:
            ani = FuncAnimation(self.fig, self.update_plot, interval=500, 
                              blit=False, save_count=100)
            plt.tight_layout()
            plt.show()
        except KeyboardInterrupt:
            print("\nStopping monitor...")
        finally:
            self.running = False

def main():
    """Main function"""
    print("EdgeRIC Log-based Latency Monitor")
    print("=================================")
    
    # Check if Docker container is running
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=edgeric_test'], 
                              capture_output=True, text=True)
        if 'edgeric_test' not in result.stdout:
            print("Error: EdgeRIC container 'edgeric_test' is not running")
            print("Please start EdgeRIC first")
            return
        else:
            print("Found running EdgeRIC container")
    except Exception as e:
        print(f"Error checking Docker: {e}")
        return
    
    # Start monitoring
    monitor = LogLatencyMonitor(max_points=500)
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
