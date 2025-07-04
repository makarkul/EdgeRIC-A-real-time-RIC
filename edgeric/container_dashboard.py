#!/usr/bin/env python3
"""
EdgeRIC Container Dashboard
Real-time metrics display for use inside the EdgeRIC Docker container
"""

import sys
import os
import time
from datetime import datetime
from collections import deque, defaultdict

# Add the EdgeRIC path
sys.path.append('/home/EdgeRIC-A-real-time-RIC/edgeric')

try:
    from edgeric_messenger import get_metrics_multi
    DIRECT_ACCESS = True
except ImportError as e:
    DIRECT_ACCESS = False
    print(f"EdgeRIC access not available: {e}")
    sys.exit(1)

class ContainerDashboard:
    def __init__(self, history_size=20):
        self.history_size = history_size
        self.data = defaultdict(lambda: {
            'latency': deque(maxlen=history_size),
            'backlog': deque(maxlen=history_size),
            'tx_brate': deque(maxlen=history_size),
            'rx_brate': deque(maxlen=history_size),
            'cqi': deque(maxlen=history_size),
            'snr': deque(maxlen=history_size),
            'timestamps': deque(maxlen=history_size)
        })
        self.start_time = time.time()
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear')
        
    def format_value(self, value, unit, decimals=1):
        """Format values with appropriate units"""
        if isinstance(value, (int, float)):
            return f"{value:.{decimals}f}{unit}"
        return f"{value}{unit}"
    
    def draw_sparkline(self, values, width=20):
        """Create a simple ASCII sparkline"""
        if not values or len(values) < 2:
            return '─' * width
            
        min_val, max_val = min(values), max(values)
        if max_val == min_val:
            return '─' * width
            
        chars = '▁▂▃▄▅▆▇█'
        spark = ''
        
        for val in values[-width:]:
            if max_val > min_val:
                normalized = (val - min_val) / (max_val - min_val)
                char_idx = min(int(normalized * (len(chars) - 1)), len(chars) - 1)
                spark += chars[char_idx]
            else:
                spark += chars[0]
                
        return spark.ljust(width)
    
    def draw_bar(self, value, max_value, width=20, char='█'):
        """Create a horizontal bar chart"""
        if max_value == 0:
            return '░' * width
            
        filled = int((value / max_value) * width)
        return char * filled + '░' * (width - filled)
    
    def update_display(self):
        """Update the dashboard display"""
        try:
            ue_data = get_metrics_multi()
            current_time = time.time() - self.start_time
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            if not ue_data:
                self.clear_screen()
                print("╔═══════════════════════════════════════════════════════════════════════════════╗")
                print("║                        EdgeRIC Container Dashboard                           ║")
                print("╠═══════════════════════════════════════════════════════════════════════════════╣")
                print(f"║ Time: {timestamp}        Runtime: {current_time:8.1f}s                              ║")
                print("╠═══════════════════════════════════════════════════════════════════════════════╣")
                print("║                              No UE Data Available                            ║")
                print("╚═══════════════════════════════════════════════════════════════════════════════╝")
                return
            
            # Update data
            for ue_id, data in ue_data.items():
                self.data[ue_id]['timestamps'].append(current_time)
                self.data[ue_id]['latency'].append(data.get('Latency', 0) / 1000.0)  # ms
                self.data[ue_id]['backlog'].append(data.get('Backlog', 0) / 1024.0)  # KB
                self.data[ue_id]['tx_brate'].append(data.get('Tx_brate', 0) * 8.0 / 1000000.0)  # Mbps
                self.data[ue_id]['rx_brate'].append(data.get('Rx_brate', 0) * 8.0 / 1000000.0)  # Mbps
                self.data[ue_id]['cqi'].append(data.get('CQI', 0))
                self.data[ue_id]['snr'].append(data.get('SNR', 0))
            
            # Display
            self.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════════╗")
            print("║                        EdgeRIC Container Dashboard                           ║")
            print("╠═══════════════════════════════════════════════════════════════════════════════╣")
            print(f"║ Time: {timestamp}        Runtime: {current_time:8.1f}s        UEs: {len(ue_data)}               ║")
            print("╠═══════════════════════════════════════════════════════════════════════════════╣")
            
            for ue_id in sorted(ue_data.keys()):
                data = ue_data[ue_id]
                history = self.data[ue_id]
                
                # Current values
                latency_ms = data.get('Latency', 0) / 1000.0
                backlog_kb = data.get('Backlog', 0) / 1024.0
                tx_mbps = data.get('Tx_brate', 0) * 8.0 / 1000000.0
                rx_mbps = data.get('Rx_brate', 0) * 8.0 / 1000000.0
                cqi = data.get('CQI', 0)
                snr = data.get('SNR', 0)
                
                print(f"║ UE {ue_id:3d} ───────────────────────────────────────────────────────────────────────── ║")
                
                # Latency with sparkline
                latency_spark = self.draw_sparkline(list(history['latency']), 15)
                print(f"║   Latency:  {latency_ms:8.1f}ms  [{latency_spark}] Trend                 ║")
                
                # Backlog with bar
                max_backlog = max(list(history['backlog'])) if history['backlog'] else 1
                backlog_bar = self.draw_bar(backlog_kb, max(max_backlog, backlog_kb), 15)
                print(f"║   Backlog:  {backlog_kb:8.1f}KB  [{backlog_bar}] Max: {max_backlog:.0f}KB        ║")
                
                # Throughput
                tx_spark = self.draw_sparkline(list(history['tx_brate']), 15)
                print(f"║   TX Rate:  {tx_mbps:8.1f}Mbps [{tx_spark}] Trend                 ║")
                
                rx_spark = self.draw_sparkline(list(history['rx_brate']), 15)
                print(f"║   RX Rate:  {rx_mbps:8.1f}Mbps [{rx_spark}] Trend                 ║")
                
                # Radio metrics
                cqi_bar = self.draw_bar(cqi, 15, 15, '▓')
                snr_display = f"{snr:.1f}" if isinstance(snr, (int, float)) else str(snr)
                print(f"║   CQI:      {cqi:8d}     [{cqi_bar}] SNR: {snr_display:>6}dB          ║")
                
                # Statistics
                if len(history['latency']) > 1:
                    avg_latency = sum(history['latency']) / len(history['latency'])
                    min_latency = min(history['latency'])
                    max_latency = max(history['latency'])
                    print(f"║   Stats:    Avg: {avg_latency:5.1f}ms  Min: {min_latency:5.1f}ms  Max: {max_latency:5.1f}ms            ║")
                
                print("║" + "─" * 79 + "║")
            
            print("╠═══════════════════════════════════════════════════════════════════════════════╣")
            print("║ Legend: Sparklines show trends, Bars show current vs max values              ║")
            print("║ Press Ctrl+C to exit                                                         ║")
            print("╚═══════════════════════════════════════════════════════════════════════════════╝")
            
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def run(self):
        """Run the dashboard"""
        print("Starting EdgeRIC Container Dashboard...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                self.update_display()
                time.sleep(1.0)  # Update every second
                
        except KeyboardInterrupt:
            print("\n\nStopping dashboard...")
        except Exception as e:
            print(f"\nError: {e}")

def main():
    """Main function"""
    if not DIRECT_ACCESS:
        print("Error: Cannot access EdgeRIC messaging")
        print("Make sure you're running this inside the EdgeRIC container")
        return
        
    dashboard = ContainerDashboard(history_size=30)
    dashboard.run()

if __name__ == "__main__":
    main()
