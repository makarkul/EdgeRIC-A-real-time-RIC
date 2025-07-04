#!/usr/bin/env python3
"""
TCP Bridge for EdgeRIC ZMQ Metrics
Bridges IPC sockets to TCP sockets so host can access container metrics
"""

import os
# Fix protobuf compatibility issue
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

import zmq
import time
import threading
import signal
import sys
import metrics_pb2

class TCPBridge:
    def __init__(self, ipc_address="ipc:///tmp/socket_snr_cqi", tcp_port=5555):
        self.ipc_address = ipc_address
        self.tcp_port = tcp_port
        self.context = zmq.Context()
        self.running = False
        
        # IPC subscriber (connects to EdgeRIC)
        self.ipc_subscriber = self.context.socket(zmq.SUB)
        self.ipc_subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
        self.ipc_subscriber.setsockopt(zmq.CONFLATE, 1)
        
        # TCP publisher (for host to connect to)
        self.tcp_publisher = self.context.socket(zmq.PUB)
        
    def start(self):
        """Start the TCP bridge"""
        print(f"Starting TCP bridge: {self.ipc_address} -> tcp://*:{self.tcp_port}")
        
        try:
            # Connect to IPC socket
            self.ipc_subscriber.connect(self.ipc_address)
            print(f"Connected to IPC: {self.ipc_address}")
            
            # Bind TCP socket
            self.tcp_publisher.bind(f"tcp://*:{self.tcp_port}")
            print(f"TCP publisher bound to port {self.tcp_port}")
            
            self.running = True
            
            # Start bridging
            self.bridge_loop()
            
        except Exception as e:
            print(f"Error starting bridge: {e}")
            self.stop()
    
    def bridge_loop(self):
        """Main bridge loop"""
        message_count = 0
        
        print("Starting bridge loop...")
        
        while self.running:
            try:
                # Receive from IPC with timeout
                if self.ipc_subscriber.poll(timeout=1000):  # 1 second timeout
                    message = self.ipc_subscriber.recv(zmq.NOBLOCK)
                    
                    # Forward to TCP
                    self.tcp_publisher.send(message)
                    
                    message_count += 1
                    
                    if message_count % 100 == 0:
                        # Parse and display some info
                        try:
                            metrics = metrics_pb2.Metrics()
                            metrics.ParseFromString(message)
                            print(f"✓ Bridged {message_count} messages. Latest TTI: {metrics.tti_cnt}, UEs: {len(metrics.ue_metrics)}")
                        except Exception as e:
                            print(f"✓ Bridged {message_count} messages. Parse error: {e}")
                else:
                    # No message available, short sleep
                    time.sleep(0.1)
                            
            except zmq.Again:
                # No message available, continue
                continue
            except Exception as e:
                print(f"Error in bridge loop: {e}")
                break
    
    def stop(self):
        """Stop the bridge"""
        print("Stopping TCP bridge...")
        self.running = False
        
        if self.ipc_subscriber:
            self.ipc_subscriber.close()
        if self.tcp_publisher:
            self.tcp_publisher.close()
        if self.context:
            self.context.term()
        
        print("TCP bridge stopped")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nReceived interrupt signal, stopping bridge...")
    bridge.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Create bridge
    bridge = TCPBridge()
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start bridge
    bridge.start()
