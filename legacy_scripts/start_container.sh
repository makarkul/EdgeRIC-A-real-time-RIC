#!/bin/bash

# EdgeRIC Container Start Script
# This script starts the EdgeRIC container for development

set -e  # Exit on any error

echo "🚀 Starting EdgeRIC development container..."

# Setup X11 forwarding and system settings
echo "🔧 Setting up system configuration..."
if command -v xhost &> /dev/null; then
    xhost +local:docker
else
    echo "⚠️  xhost not found (likely on macOS), skipping X11 setup"
fi

# Try to set system settings (with sudo)
echo "Note: You may need to run these commands manually if they fail:"
echo "  sudo systemctl stop firewalld"
echo "  sudo sysctl -w net.ipv4.ip_forward=1"

sudo systemctl stop firewalld 2>/dev/null || echo "⚠️  Could not stop firewalld (may not be installed)"
sudo sysctl -w net.ipv4.ip_forward=1 || echo "⚠️  Could not set ip_forward"

# Check if container is already running
if docker ps --filter "name=edgeric_dev" --format "table {{.Names}}" | grep -q "edgeric_dev"; then
    echo "⚠️  Development container already running. Stopping it first..."
    docker stop edgeric_dev
    docker rm edgeric_dev
fi

echo "🚀 Starting development container..."

# Start container interactively
docker run -it --rm --network=host --name edgeric_dev \
    --privileged=true \
    -e DISPLAY=$DISPLAY \
    --env=NVIDIA_DRIVER_CAPABILITIES=all \
    --env=NVIDIA_VISIBLE_DEVICES=all \
    --env=QT_X11_NO_MITSHM=1 \
    -v $(pwd):/home/EdgeRIC-A-real-time-RIC:rw \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v /dev:/dev \
    nlpurnhyun/edgeric_base_oaic \
    bash
