#!/bin/bash
# filepath: /Users/makarand/EdgeRIC-A-real-time-RIC/start_edgeric.sh

echo "Starting EdgeRIC with screen sessions..."

# Start screen session
screen -dmS edgeric -s /bin/bash

# Window 0: RAN Simulator (if you have one)
screen -S edgeric -X screen -t "RAN-Simulator"
screen -S edgeric -p "RAN-Simulator" -X stuff "echo 'RAN Simulator would start here'\n"

# Window 1: EdgeRIC Controller
screen -S edgeric -X screen -t "EdgeRIC-Controller"
screen -S edgeric -p "EdgeRIC-Controller" -X stuff "cd /workspace/edgeric/muApp2\n"
screen -S edgeric -p "EdgeRIC-Controller" -X stuff "python muApp2_train_RL_DL_scheduling.py\n"

# Window 2: ZMQ Monitor (optional)
screen -S edgeric -X screen -t "ZMQ-Monitor"
screen -S edgeric -p "ZMQ-Monitor" -X stuff "echo 'ZMQ Monitor - watch network traffic here'\n"

# Window 3: Logs
screen -S edgeric -X screen -t "Logs"
screen -S edgeric -p "Logs" -X stuff "cd /workspace && tail -f logs/*.log 2>/dev/null || echo 'No logs yet'\n"

echo "Screen sessions started. Use 'screen -r edgeric' to attach."
echo "Screen windows:"
echo "  0: RAN-Simulator"
echo "  1: EdgeRIC-Controller"  
echo "  2: ZMQ-Monitor"
echo "  3: Logs"
echo ""
echo "Navigation:"
echo "  Ctrl+a then c: Create new window"
echo "  Ctrl+a then n: Next window"
echo "  Ctrl+a then p: Previous window"
echo "  Ctrl+a then \": List windows"
echo "  Ctrl+a then d: Detach from screen"
