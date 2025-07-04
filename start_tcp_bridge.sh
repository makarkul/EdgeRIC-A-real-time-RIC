#!/bin/bash

# Start TCP Bridge for EdgeRIC
# This script should be run inside the EdgeRIC container

echo "Starting EdgeRIC TCP Bridge..."

# Check if we're inside the container
if [ ! -f "/home/EdgeRIC-A-real-time-RIC/edgeric/tcp_bridge.py" ]; then
    echo "Error: TCP bridge script not found. Make sure you're running this inside the EdgeRIC container."
    exit 1
fi

# Change to the EdgeRIC directory
cd /home/EdgeRIC-A-real-time-RIC/edgeric

# Run the TCP bridge
python3 tcp_bridge.py

echo "TCP bridge stopped."
