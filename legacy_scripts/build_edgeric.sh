#!/bin/bash

# EdgeRIC Build Script
# This script starts a Docker container and builds the EdgeRIC project

set -e  # Exit on any error

echo "🔨 Building EdgeRIC inside Docker container..."

# Setup X11 forwarding and system settings
echo "🔧 Setting up system configuration..."
if command -v xhost &> /dev/null; then
    xhost +local:docker
else
    echo "⚠️  xhost not found (likely on macOS), skipping X11 setup"
fi
sudo systemctl stop firewalld 2>/dev/null || true  # Ignore if firewalld is not installed
sudo sysctl -w net.ipv4.ip_forward=1

# Check if container is already running
if docker ps --filter "name=edgeric_build" --format "table {{.Names}}" | grep -q "edgeric_build"; then
    echo "⚠️  Build container already running. Stopping it first..."
    docker stop edgeric_build
    docker rm edgeric_build
fi

echo "🚀 Starting container and building EdgeRIC..."

# Start container and run build command
docker run --rm --network=host --name edgeric_build \
    --privileged=true \
    -e DISPLAY=$DISPLAY \
    --env=NVIDIA_DRIVER_CAPABILITIES=all \
    --env=NVIDIA_VISIBLE_DEVICES=all \
    --env=QT_X11_NO_MITSHM=1 \
    -v $(pwd):/home/EdgeRIC-A-real-time-RIC:rw \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v /dev:/dev \
    nlpurnhyun/edgeric_base_oaic \
    /bin/bash -c "cd /home/EdgeRIC-A-real-time-RIC && ./make_ran_improved.sh"

if [ $? -eq 0 ]; then
    echo "✅ Build completed successfully!"
else
    echo "❌ Build failed!"
    exit 1
fi
