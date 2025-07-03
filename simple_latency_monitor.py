#!/usr/bin/env python3
"""
Simple Latency Extractor for EdgeRIC
Extracts and displays latency values from EdgeRIC in real-time
"""

import sys
import time
import json
from datetime import datetime
from collections import defaultdict, deque

# Add the EdgeRIC path
sys.path.append('/home/EdgeRIC-A-real-time-RIC/edgeric')

try:
    from edgeric_messenger import get_metrics_multi
    DIRECT_ACCESS = True
    print("Using direct EdgeRIC access")
except ImportError as e:
    DIRECT_ACCESS = False
    print(f"Direct access not available: {e}")

class SimpleLatencyMonitor:
    def __init__(self, history_size=50):
        self.history_size = history_size
        self.latency_history = defaultdict(lambda: deque(maxlen=history_size))
        self.start_time = time.time()
        
    def update_data(self, ue_data):
        """Update latency data and display"""
        current_time = time.time() - self.start_time
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"\n[{timestamp}] UE Latency Report (t={current_time:.1f}s)")
        print("=" * 60)
        
        for ue_id, data in ue_data.items():
            if 'Latency' in data:
                latency_us = data['Latency']
                latency_ms = latency_us / 1000.0
                
                # Store in history
                self.latency_history[ue_id].append(latency_ms)
                
                # Calculate statistics
                history = list(self.latency_history[ue_id])
                if len(history) > 1:
                    avg = sum(history) / len(history)
                    min_val = min(history)
                    max_val = max(history)
                    trend = "↑" if history[-1] > history[-2] else "↓" if history[-1] < history[-2] else "→"
                else:
                    avg = min_val = max_val = latency_ms
                    trend = "→"
                
                # Display with other metrics
                cqi = data.get('CQI', 'N/A')
                snr = data.get('SNR', 'N/A')
                tx_brate = data.get('Tx_brate', 'N/A')
                backlog = data.get('Backlog', 'N/A')
                
                print(f"UE {ue_id:3d}: {latency_ms:8.1f}ms {trend} "
                      f"(avg: {avg:6.1f}, min: {min_val:6.1f}, max: {max_val:6.1f}) "
                      f"CQI:{cqi:2} SNR:{snr} Tx:{tx_brate} Backlog:{backlog}")
        
        print("-" * 60)
        
    def run_direct_monitoring(self):
        """Monitor using direct EdgeRIC access"""
        print("Starting direct EdgeRIC monitoring...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                ue_data = get_metrics_multi()
                if ue_data:
                    self.update_data(ue_data)
                else:
                    print("No UE data available")
                
                time.sleep(1.0)  # Update every second
                
        except KeyboardInterrupt:
            print("\nStopping monitor...")
            
    def save_to_csv(self, filename=None):
        """Save collected data to CSV"""
        if filename is None:
            filename = f"latency_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        try:
            with open(filename, 'w') as f:
                f.write("UE_ID,Timestamp,Latency_ms\n")
                
                for ue_id, history in self.latency_history.items():
                    for i, latency in enumerate(history):
                        timestamp = i  # Simple timestamp
                        f.write(f"{ue_id},{timestamp},{latency:.3f}\n")
                        
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving to CSV: {e}")

def create_gnuplot_script():
    """Create a gnuplot script for real-time plotting"""
    script = """#!/usr/bin/gnuplot
# Real-time latency plotting script
set terminal x11 persist
set title "UE Latency Monitor"
set xlabel "Time (seconds)"
set ylabel "Latency (ms)"
set grid
set autoscale
set key outside

# Real-time plotting loop
while (1) {
    plot "latency_data.txt" using 1:2 with linespoints title "UE 70", \\
         "latency_data.txt" using 1:3 with linespoints title "UE 71"
    pause 1
}
"""
    with open("plot_latency.gnu", "w") as f:
        f.write(script)
    print("Created plot_latency.gnu - run with: gnuplot plot_latency.gnu")

def main():
    """Main function"""
    print("EdgeRIC Simple Latency Monitor")
    print("==============================")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--gnuplot":
        create_gnuplot_script()
        return
    
    monitor = SimpleLatencyMonitor()
    
    if DIRECT_ACCESS:
        # Test connection first
        try:
            test_data = get_metrics_multi()
            if test_data:
                print(f"Found {len(test_data)} UEs")
            else:
                print("Warning: No UE data available")
        except Exception as e:
            print(f"Error: {e}")
            return
            
        monitor.run_direct_monitoring()
    else:
        print("Direct access not available. Run this script inside the EdgeRIC container:")
        print("docker exec -it edgeric_test python3 /path/to/this/script.py")

if __name__ == "__main__":
    main()
