#!/bin/bash

echo "EdgeRIC Metrics Dashboard Launcher"
echo "=================================="
echo ""
echo "Available monitoring options:"
echo ""
echo "1. Web Dashboard (Host) - Browser-based with Plotly Dash"
echo "2. Start TCP Bridge (Container) - Required for option 1"
echo ""
echo "Choose an option (1-2):"

read -r choice

case $choice in
    1)
        echo "Starting Web Dashboard..."
        echo "Note: Browser-based dashboard with Plotly Dash"
        echo "Dashboard will be available at: http://localhost:8050"
        source .venv/bin/activate 2>/dev/null || echo "Note: Virtual environment not found, using system Python"
        export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
        python3 web_dashboard.py
        ;;
    2)
        echo "Starting TCP Bridge inside container..."
        echo "This will start the TCP bridge that enables host dashboard access"
        if command -v docker &> /dev/null; then
            docker exec -it edgeric_test /home/EdgeRIC-A-real-time-RIC/start_tcp_bridge.sh
        else
            echo "Docker not found. Run manually inside container:"
            echo "docker exec -it edgeric_test /home/EdgeRIC-A-real-time-RIC/start_tcp_bridge.sh"
        fi
        ;;
    *)
        echo "Invalid choice. Please select 1-2."
        ;;
esac
