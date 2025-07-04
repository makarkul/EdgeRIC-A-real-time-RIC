#!/usr/bin/env python3
"""
EdgeRIC Multi-Metric Dashboard - Shows all metrics in separate subplots
"""

import os
# Fix protobuf compatibility issue
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

import zmq
import time
import threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import CheckButtons
from collections import deque, defaultdict
import signal
import sys

# Add the edgeric directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'edgeric'))

try:
    import metrics_pb2
    print("✓ Successfully imported metrics_pb2")
except ImportError as e:
    print(f"✗ Failed to import metrics_pb2: {e}")
    print("Make sure you're running this from the EdgeRIC root directory")
    sys.exit(1)

class MultiMetricDashboard:
    def __init__(self, tcp_host="localhost", tcp_port=5555, time_window=300, max_points=5000):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.time_window = time_window  # seconds to display (unused in sequence mode)
        self.max_points = max_points  # number of points to show in rolling window
        self.context = zmq.Context()
        self.subscriber = None
        self.running = False
        
        # Data storage with longer history
        self.ue_data = defaultdict(lambda: {
            'backlog': deque(maxlen=self.max_points),
            'latency': deque(maxlen=self.max_points),
            'throughput': deque(maxlen=self.max_points),
            'cqi': deque(maxlen=self.max_points),
            'snr': deque(maxlen=self.max_points),
            'timestamps': deque(maxlen=self.max_points)
        })
        
        # UI state
        self.active_ues = set()
        
        # Threading
        self.data_thread = None
        self.data_lock = threading.Lock()
        
        # Statistics
        self.message_count = 0
        self.last_update = time.time()
        self.start_time = time.time()
        
        # Set up matplotlib with multiple subplots
        plt.style.use('seaborn-v0_8')
        self.fig = plt.figure(figsize=(12, 9))  # Reduced from (16, 12) to 75% size
        self.fig.suptitle('EdgeRIC Real-Time Metrics Dashboard - Multi-Metric View', fontsize=14, fontweight='bold')  # Reduced font size
        
        # Create subplots in a 2x3 grid
        self.ax_latency = plt.subplot(2, 3, 1)
        self.ax_backlog = plt.subplot(2, 3, 2)
        self.ax_throughput = plt.subplot(2, 3, 3)
        self.ax_cqi = plt.subplot(2, 3, 4)
        self.ax_snr = plt.subplot(2, 3, 5)
        self.ax_stats = plt.subplot(2, 3, 6)
        
        self.setup_plots()
        self.setup_controls()
        
    def setup_plots(self):
        """Configure all subplot axes"""
        # All x-axes are now sample index, rolling window
        self.ax_latency.set_title('UE Latency', fontsize=12, fontweight='bold')
        self.ax_latency.set_xlabel('Sample Index (rolling window)')
        self.ax_latency.set_ylabel('Latency (μs)')
        self.ax_latency.grid(True, alpha=0.3)

        self.ax_backlog.set_title('UE Backlog', fontsize=12, fontweight='bold')
        self.ax_backlog.set_xlabel('Sample Index (rolling window)')
        self.ax_backlog.set_ylabel('Backlog (bytes)')
        self.ax_backlog.grid(True, alpha=0.3)

        self.ax_throughput.set_title('UE TX Bytes', fontsize=12, fontweight='bold')
        self.ax_throughput.set_xlabel('Sample Index (rolling window)')
        self.ax_throughput.set_ylabel('TX Bytes')
        self.ax_throughput.grid(True, alpha=0.3)

        self.ax_cqi.set_title('Channel Quality (CQI)', fontsize=12, fontweight='bold')
        self.ax_cqi.set_xlabel('Sample Index (rolling window)')
        self.ax_cqi.set_ylabel('CQI')
        self.ax_cqi.grid(True, alpha=0.3)

        self.ax_snr.set_title('Signal Quality (SNR)', fontsize=12, fontweight='bold')
        self.ax_snr.set_xlabel('Sample Index (rolling window)')
        self.ax_snr.set_ylabel('SNR (dB)')
        self.ax_snr.grid(True, alpha=0.3)

        self.ax_stats.set_title('Dashboard Stats', fontsize=12, fontweight='bold')
        self.ax_stats.axis('off')
        
    def setup_controls(self):
        """Setup control area"""
        # Add checkboxes for UE selection (will be populated dynamically)
        self.ue_checkboxes = None
        
        # Status text
        self.status_text = self.ax_stats.text(0.1, 0.8, 'Status: Connecting...', 
                                            fontsize=10, transform=self.ax_stats.transAxes)
        self.stats_text = self.ax_stats.text(0.1, 0.6, 'Messages: 0\nRate: 0.0/s', 
                                           fontsize=10, transform=self.ax_stats.transAxes)
        self.time_text = self.ax_stats.text(0.1, 0.4, f'Max Points: {self.max_points}', 
                                          fontsize=10, transform=self.ax_stats.transAxes)
        self.ue_count_text = self.ax_stats.text(0.1, 0.2, 'Active UEs: 0', 
                                              fontsize=10, transform=self.ax_stats.transAxes)
        
    def connect_to_bridge(self):
        """Connect to the TCP bridge"""
        try:
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
            self.subscriber.setsockopt(zmq.CONFLATE, 1)
            self.subscriber.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            
            tcp_address = f"tcp://{self.tcp_host}:{self.tcp_port}"
            self.subscriber.connect(tcp_address)
            
            print(f"✓ Connected to TCP bridge at {tcp_address}")
            self.status_text.set_text('Status: Connected')
            return True
            
        except Exception as e:
            print(f"✗ Failed to connect to TCP bridge: {e}")
            self.status_text.set_text(f'Status: Failed - {str(e)[:30]}...')
            return False
    
    def start_data_collection(self):
        """Start the data collection thread"""
        if not self.connect_to_bridge():
            return False
            
        self.running = True
        self.data_thread = threading.Thread(target=self.data_collection_loop)
        self.data_thread.daemon = True
        self.data_thread.start()
        
        print("✓ Data collection started")
        return True
    
    def data_collection_loop(self):
        """Main data collection loop"""
        while self.running:
            try:
                # Receive message with timeout
                message = self.subscriber.recv(zmq.NOBLOCK)
                self.process_message(message)
                
            except zmq.Again:
                # No message available, continue
                continue
            except Exception as e:
                print(f"Error in data collection: {e}")
                break
    
    def process_message(self, message):
        """Process a received metrics message"""
        try:
            metrics = metrics_pb2.Metrics()
            metrics.ParseFromString(message)
            
            current_time = time.time()
            
            with self.data_lock:
                self.message_count += 1
                
                # Process per-UE metrics
                for ue_metrics in metrics.ue_metrics:
                    rnti = ue_metrics.rnti
                    
                    # Add to active UEs
                    self.active_ues.add(rnti)
                    
                    # Store metrics
                    self.ue_data[rnti]['throughput'].append(ue_metrics.tx_bytes)
                    self.ue_data[rnti]['latency'].append(ue_metrics.latency)
                    self.ue_data[rnti]['backlog'].append(ue_metrics.backlog)
                    self.ue_data[rnti]['cqi'].append(ue_metrics.cqi)
                    self.ue_data[rnti]['snr'].append(ue_metrics.snr)
                    self.ue_data[rnti]['timestamps'].append(current_time)
                
            # Update statistics
            if self.message_count % 20 == 0:
                self.update_stats()
                
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def update_stats(self):
        """Update statistics display"""
        current_time = time.time()
        elapsed = current_time - self.last_update
        
        if elapsed > 0:
            rate = 20 / elapsed  # Messages per second (we update every 20 messages)
            self.stats_text.set_text(f'Messages: {self.message_count}\nRate: {rate:.1f}/s')
            self.last_update = current_time
            
        self.ue_count_text.set_text(f'Active UEs: {len(self.active_ues)}')
    
    def update_plots(self, frame):
        """Update all plots with current data, using sample index as x-axis (rolling window of last N points)."""
        with self.data_lock:
            colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
            # Clear all plots
            for ax in [self.ax_latency, self.ax_backlog, self.ax_throughput, self.ax_cqi, self.ax_snr]:
                ax.clear()
            self.setup_plots()
            
            # Find the maximum number of points across all UEs to set x-axis
            max_data_points = 0
            for rnti in self.active_ues:
                if rnti in self.ue_data:
                    max_data_points = max(max_data_points, len(self.ue_data[rnti]['latency']))
            
            # Set x-axis based on actual data, but limit to max_points
            if max_data_points > 0:
                x_max = min(max_data_points, self.max_points) - 1
                x_min = 0
            else:
                x_max = self.max_points - 1
                x_min = 0
            
            for i, rnti in enumerate(sorted(self.active_ues)):
                if rnti not in self.ue_data:
                    continue
                # Get last N points for each metric
                latency_data = list(self.ue_data[rnti]['latency'])
                backlog_data = list(self.ue_data[rnti]['backlog'])
                throughput_data = list(self.ue_data[rnti]['throughput'])
                cqi_data = list(self.ue_data[rnti]['cqi'])
                snr_data = list(self.ue_data[rnti]['snr'])
                
                n_points = len(latency_data)
                if n_points == 0:
                    continue
                    
                # X-axis starts from 1, not 0
                x_vals = list(range(1, n_points + 1))
                color = colors[i % len(colors)]
                label = f'UE {rnti}'
                
                if latency_data:
                    self.ax_latency.plot(x_vals, latency_data, color=color, label=label, linewidth=2, alpha=0.8, marker='o', markersize=2)
                if backlog_data:
                    self.ax_backlog.plot(x_vals, backlog_data, color=color, label=label, linewidth=2, alpha=0.8, marker='s', markersize=2)
                if throughput_data:
                    self.ax_throughput.plot(x_vals, throughput_data, color=color, label=label, linewidth=2, alpha=0.8, marker='^', markersize=2)
                if cqi_data:
                    self.ax_cqi.plot(x_vals, cqi_data, color=color, label=label, linewidth=2, alpha=0.8, marker='d', markersize=2)
                if snr_data:
                    self.ax_snr.plot(x_vals, snr_data, color=color, label=label, linewidth=2, alpha=0.8, marker='*', markersize=3)
            
            # Set x-axis for all subplots dynamically based on data
            for ax in [self.ax_latency, self.ax_backlog, self.ax_throughput, self.ax_cqi, self.ax_snr]:
                if max_data_points > 0:
                    ax.set_xlim(1, max(max_data_points, 10))  # Show at least 10 points on x-axis
                    # Set reasonable tick intervals
                    if max_data_points <= 20:
                        tick_interval = 2
                    elif max_data_points <= 50:
                        tick_interval = 5
                    else:
                        tick_interval = 10
                    ticks = list(range(1, max_data_points + 1, tick_interval))
                    if max_data_points not in ticks:
                        ticks.append(max_data_points)
                    ax.set_xticks(ticks)
                    ax.set_xticklabels([str(t) for t in ticks])
                else:
                    ax.set_xlim(1, self.max_points)
                    ax.set_xticks(list(range(1, self.max_points + 1, max(1, self.max_points // 10))))
                    
                ax.legend(loc='upper right', fontsize=8)
                ax.grid(True, alpha=0.3)
            
            # Update info text
            self.ax_snr.set_xlabel(f'Sample Index (showing last {max_data_points} points, max {self.max_points})')
            
            # If no data, show empty window
            if not any(self.ue_data[rnti]['latency'] for rnti in self.active_ues):
                for ax in [self.ax_latency, self.ax_backlog, self.ax_throughput, self.ax_cqi, self.ax_snr]:
                    ax.set_xlim(1, self.max_points)
                    ax.legend(loc='upper right', fontsize=8)
                    ax.grid(True, alpha=0.3)
                self.ax_snr.set_xlabel('Sample Index (waiting for data...)')
    
    def run(self):
        """Run the dashboard"""
        print(f"Starting EdgeRIC Multi-Metric Dashboard (Max Points: {self.max_points})...")
        
        # Start data collection
        if not self.start_data_collection():
            print("Failed to start data collection")
            return
        
        # Start animation with slower update rate for better performance
        self.ani = FuncAnimation(self.fig, self.update_plots, interval=1000, cache_frame_data=False)
        
        # Adjust layout and show plot
        plt.tight_layout()
        plt.show()
    
    def stop(self):
        """Stop the dashboard"""
        print("Stopping dashboard...")
        self.running = False
        
        if self.data_thread:
            self.data_thread.join(timeout=1)
        
        if self.subscriber:
            self.subscriber.close()
        
        if self.context:
            self.context.term()
        
        print("Dashboard stopped")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nReceived interrupt signal, stopping dashboard...")
    if 'dashboard' in globals():
        dashboard.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run dashboard with 5000 points max
    dashboard = MultiMetricDashboard(max_points=5000)
    dashboard.run()
