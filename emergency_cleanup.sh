#!/bin/bash

echo "Emergency EdgeRIC cleanup - stopping all EdgeRIC related processes and containers"

# Stop all EdgeRIC containers
echo "Stopping all EdgeRIC containers..."
docker ps -q --filter "name=edgeric" | xargs -r docker stop

# Remove all EdgeRIC containers
echo "Removing all EdgeRIC containers..."
docker ps -a -q --filter "name=edgeric" | xargs -r docker rm

# Kill any remaining EdgeRIC processes on host
echo "Killing any remaining EdgeRIC processes on host..."
sudo pkill -f "edgeric" 2>/dev/null || true
sudo pkill -f "python3.*muApp" 2>/dev/null || true
sudo pkill -f "redis-server" 2>/dev/null || true
sudo pkill -f "iperf.*ue" 2>/dev/null || true

# Clean up screen sessions on host (if any)
echo "Cleaning up any screen sessions..."
screen -ls | grep -i edgeric | cut -d. -f1 | awk '{print $1}' | xargs -I {} screen -X -S {} quit 2>/dev/null || true

# Reset network settings that might have been modified
echo "Resetting network settings..."
sudo sysctl -w net.ipv4.ip_forward=0 2>/dev/null || true

# Clean up any network namespaces that might have been created
echo "Cleaning up network namespaces..."
sudo ip netns del ue1 2>/dev/null || true
sudo ip netns del ue2 2>/dev/null || true

# Restart firewall if it was stopped
echo "Restarting firewall..."
sudo systemctl start firewalld 2>/dev/null || true

# Show final status
echo ""
echo "=== Cleanup Summary ==="
echo "Docker containers:"
docker ps -a --filter "name=edgeric" --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "Network namespaces:"
ip netns list 2>/dev/null | grep -E "(ue1|ue2)" || echo "No EdgeRIC network namespaces found"

echo ""
echo "Screen sessions:"
screen -ls 2>/dev/null | grep -i edgeric || echo "No EdgeRIC screen sessions found"

echo ""
echo "Emergency cleanup completed!"
echo "All EdgeRIC processes and containers should now be stopped."
