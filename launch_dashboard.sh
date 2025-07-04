#!/bin/bash

echo "EdgeRIC Metrics Dashboard Launcher"
echo "=================================="
echo ""
echo "NOTE: The web dashboard now runs automatically inside the EdgeRIC container!"
echo ""
echo "To start the complete EdgeRIC system with web dashboard:"
echo "  ./start_edgeric_with_screen.sh bridge test"
echo ""
echo "Once running, the dashboard will be available at:"
echo "  http://localhost:8050"
echo ""
echo "The dashboard includes:"
echo "  - Real-time metrics visualization"
echo "  - Rolling window plotting (configurable 100-5000 samples)"
echo "  - Running averages (configurable 10-100 window)"
echo "  - Multi-UE RNTI selection"
echo "  - Connection status monitoring"
echo ""
echo "If you need to run the dashboard manually (for debugging):"
echo ""
echo "Choose an option:"
echo "1. Run web dashboard on host (requires EdgeRIC container running)"
echo "2. Start TCP bridge manually (inside container)"
echo "3. Exit"
echo ""
echo "Enter your choice (1-3):"

read -r choice

case $choice in
    1)
        echo "Starting Web Dashboard on host..."
        echo "Note: Make sure EdgeRIC container is running with TCP bridge"
        echo "Dashboard will be available at: http://localhost:8050"
        source .venv/bin/activate 2>/dev/null || echo "Note: Virtual environment not found, using system Python"
        export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
        python3 web_dashboard.py
        ;;
    2)
        echo "Starting TCP Bridge inside container..."
        echo "This will start the TCP bridge that enables dashboard access"
        if command -v docker &> /dev/null; then
            docker exec -it edgeric_test /home/EdgeRIC-A-real-time-RIC/start_tcp_bridge.sh
        else
            echo "Docker not found. Run manually inside container:"
            echo "docker exec -it edgeric_test /home/EdgeRIC-A-real-time-RIC/start_tcp_bridge.sh"
        fi
        ;;
    3)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice. Please select 1-3."
        ;;
esac
