#!/usr/bin/env python3
"""
Live Latency Ticker - Real-time display of UE latency values
"""

import sys
import time
import os
from datetime import datetime
from collections import deque

# Add path for EdgeRIC imports
sys.path.append('/home/EdgeRIC-A-real-time-RIC/edgeric')

from edgeric_messenger import get_metrics_multi

class LiveLatencyTicker:
    def __init__(self):
        self.latency_history = {}
        self.max_history = 20
        self.start_time = time.time()
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear')
        
    def format_latency(self, latency_us):
        """Format latency with appropriate units"""
        if latency_us < 1000:
            return f"{latency_us:.0f}μs"
        elif latency_us < 1000000:
            return f"{latency_us/1000:.1f}ms"
        else:
            return f"{latency_us/1000000:.2f}s"
    
    def update_display(self):
        """Update the live display"""
        try:
            ue_data = get_metrics_multi()
            current_time = time.time() - self.start_time
            
            self.clear_screen()
            print("╔" + "═" * 78 + "╗")
            print("║" + " EdgeRIC Live Latency Monitor".center(78) + "║")
            print("╠" + "═" * 78 + "╣")
            print(f"║ Runtime: {current_time:8.1f}s    Time: {datetime.now().strftime('%H:%M:%S')}".ljust(78) + "║")
            print("╠" + "═" * 78 + "╣")
            
            if ue_data:
                # Header
                print("║ UE │     Latency     │    CQI │    SNR │   Tx Rate │   Backlog   ║")
                print("╠════╪═════════════════╪════════╪════════╪═══════════╪═════════════╣")
                
                for ue_id, data in sorted(ue_data.items()):
                    latency_us = data.get('Latency', 0)
                    cqi = data.get('CQI', 'N/A')
                    snr = data.get('SNR', 'N/A')
                    tx_brate = data.get('Tx_brate', 'N/A')
                    backlog = data.get('Backlog', 'N/A')
                    
                    # Store latency history
                    if ue_id not in self.latency_history:
                        self.latency_history[ue_id] = deque(maxlen=self.max_history)
                    self.latency_history[ue_id].append(latency_us)
                    
                    # Calculate trend
                    history = list(self.latency_history[ue_id])
                    if len(history) >= 2:
                        if history[-1] > history[-2] * 1.1:
                            trend = "↗"
                        elif history[-1] < history[-2] * 0.9:
                            trend = "↘"
                        else:
                            trend = "→"
                    else:
                        trend = "→"
                    
                    # Format values
                    latency_str = f"{self.format_latency(latency_us)} {trend}".ljust(15)
                    cqi_str = f"{cqi}".rjust(6)
                    snr_str = f"{snr:.1f}" if isinstance(snr, (int, float)) else str(snr).rjust(6)
                    tx_str = f"{tx_brate}".rjust(9)
                    backlog_str = f"{backlog}".rjust(11)
                    
                    print(f"║ {ue_id:2d} │ {latency_str} │ {cqi_str} │ {snr_str:>6} │ {tx_str} │ {backlog_str} ║")
                
                print("╠" + "═" * 78 + "╣")
                
                # Show recent latency trends
                print("║ Recent Latency Trends:".ljust(78) + "║")
                for ue_id in sorted(ue_data.keys()):
                    if ue_id in self.latency_history:
                        history = list(self.latency_history[ue_id])
                        recent = history[-min(10, len(history)):]
                        trend_str = " ".join([f"{lat/1000:.0f}" for lat in recent])
                        print(f"║ UE {ue_id:2d}: {trend_str}".ljust(78) + "║")
                        
            else:
                print("║ No UE data available".ljust(78) + "║")
                
            print("╚" + "═" * 78 + "╝")
            print("\nPress Ctrl+C to stop")
            
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def run(self):
        """Run the live ticker"""
        print("Starting EdgeRIC Live Latency Ticker...")
        print("Press Ctrl+C to stop")
        time.sleep(2)
        
        try:
            while True:
                self.update_display()
                time.sleep(1.0)  # Update every second
                
        except KeyboardInterrupt:
            print("\n\nStopping latency monitor...")
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    ticker = LiveLatencyTicker()
    ticker.run()
