#!/bin/bash

echo "EdgeRIC Metrics Dashboard Launcher"
echo "=================================="
echo ""
echo "Available monitoring options:"
echo ""
echo "1. Multi-Metric Dashboard (Host) - All metrics in subplots with 5000 point rolling window"
echo "2. Web Dashboard (Host) - Browser-based with Plotly Dash, 5000 point rolling window"
echo "3. Start TCP Bridge (Container) - Required for options 1 and 2"
echo ""
echo "Choose an option (1-3):"

read -r choice

case $choice in
    1)
        echo "Starting Multi-Metric Dashboard..."
        echo "Note: Shows all metrics in separate subplots with 5000-point rolling window"
        echo "X-axis shows sample index (1, 2, 3, ..., N) instead of time"
        source .venv/bin/activate 2>/dev/null || echo "Note: Virtual environment not found, using system Python"
        export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
        python3 multi_metric_dashboard.py
        ;;
    2)
        echo "Starting Web Dashboard..."
        echo "Note: Browser-based dashboard with Plotly Dash"
        echo "Dashboard will be available at: http://localhost:8050"
        echo "X-axis shows sample index (1, 2, 3, ..., N) with configurable rolling window"
        source .venv/bin/activate 2>/dev/null || echo "Note: Virtual environment not found, using system Python"
        export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
        python3 web_dashboard.py
        ;;
    3)
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
        echo "Invalid choice. Please select 1-3."
        ;;
esac
