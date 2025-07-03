#!/bin/bash

# Check if container name parameter is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <container_name>"
    echo "Example: $0 test"
    exit 1
fi

CONTAINER_NAME="edgeric_$1"

echo "Stopping EdgeRIC container: $CONTAINER_NAME"

# Check if container is running
if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
    echo "Container $CONTAINER_NAME is running. Stopping gracefully..."
    
    # Try to kill screen sessions inside the container first
    echo "Killing screen sessions inside container..."
    docker exec $CONTAINER_NAME bash -c "
        # Kill all screen sessions
        screen -ls | grep edgeric | cut -d. -f1 | awk '{print \$1}' | xargs -I {} screen -X -S {} quit 2>/dev/null
        
        # Kill any remaining processes
        pkill -f python3 2>/dev/null
        pkill -f redis-server 2>/dev/null
        pkill -f iperf 2>/dev/null
        pkill -f srsenb 2>/dev/null
        pkill -f srsue 2>/dev/null
        pkill -f srsepc 2>/dev/null
        
        echo 'All processes killed inside container'
    " 2>/dev/null

    # Give it a moment to clean up
    sleep 2
    
    # Stop the container
    echo "Stopping Docker container..."
    docker stop $CONTAINER_NAME
    
    # Wait for container to stop
    echo "Waiting for container to stop..."
    docker wait $CONTAINER_NAME 2>/dev/null
    
    echo "Container $CONTAINER_NAME stopped successfully"
    
else
    echo "Container $CONTAINER_NAME is not running"
fi

# Clean up any remaining containers with the same name
if docker ps -a -q -f name=$CONTAINER_NAME | grep -q .; then
    echo "Removing stopped container..."
    docker rm $CONTAINER_NAME 2>/dev/null
    echo "Container $CONTAINER_NAME removed"
fi

# Clean up any orphaned processes on host (optional)
echo "Cleaning up host processes..."
sudo pkill -f "edgeric_$1" 2>/dev/null || true

echo "EdgeRIC cleanup completed!"
echo ""
echo "Summary:"
echo "- Screen sessions terminated"
echo "- Container processes killed"
echo "- Docker container stopped and removed"
echo "- Host cleanup performed"
