# EdgeRIC Host Dashboard Setup

This document explains how to run the EdgeRIC dashboard from the host system (outside the Docker container).

## Problem

The EdgeRIC system uses IPC (Inter-Process Communication) sockets for internal communication, which cannot be accessed from outside the Docker container. This prevents the dashboard from running directly on the host.

## Solution

We've implemented a TCP bridge that runs inside the container and forwards the ZMQ metrics to a TCP socket that can be accessed from the host.

## Architecture

```
Container:              Host:
EdgeRIC → IPC Socket → TCP Bridge → TCP Socket → Host Dashboard
```

## Setup Steps

### 1. Restart EdgeRIC Container with Port Forwarding

The container needs to be restarted with port 5555 exposed:

```bash
./stop_edgeric.sh test
./start_edgeric_with_screen.sh bridge test
```

The startup script has been updated to include `-p 5555:5555` to expose the TCP port.

### 2. Start the TCP Bridge (Inside Container)

In a new terminal, start the TCP bridge inside the container:

```bash
# Method 1: Using the launcher script
./launch_dashboard.sh
# Then select option 6

# Method 2: Direct command
docker exec -it edgeric_test /home/EdgeRIC-A-real-time-RIC/start_tcp_bridge.sh
```

### 3. Start the Host Dashboard (On Host)

In another terminal, start the host dashboard:

```bash
# Method 1: Using the launcher script
./launch_dashboard.sh
# Then select option 2

# Method 2: Direct command
source .venv/bin/activate
python3 host_dashboard.py
```

## Available Dashboard Options

| Option | Name | Location | Description |
|--------|------|----------|-------------|
| 1 | Interactive Dashboard | Host | Original dashboard (connection issues) |
| 2 | Host Dashboard | Host | New TCP bridge version |
| 3 | Container Dashboard | Container | Terminal-based with sparklines |
| 4 | Simple Latency Monitor | Host | Basic console output |
| 5 | Log-based Monitor | Host | Parse Docker logs |
| 6 | Start TCP Bridge | Container | Required for option 2 |

## Features of Host Dashboard

- **Real-time metrics**: Throughput, latency, and backlog per UE
- **Interactive controls**: Radio buttons to switch between metrics
- **Per-UE selection**: Checkboxes to show/hide individual UEs
- **Total metrics**: Combined view of all UEs
- **Connection status**: Shows connection state and message rates
- **Graceful shutdown**: Handles Ctrl+C properly

## Troubleshooting

### TCP Bridge Not Connecting

1. Check that EdgeRIC is running:
   ```bash
   docker ps --filter name=edgeric
   ```

2. Check that the container has the port exposed:
   ```bash
   docker port edgeric_test
   ```

3. Check that the metrics are being generated:
   ```bash
   docker exec -it edgeric_test python3 /home/EdgeRIC-A-real-time-RIC/edgeric/muApp3/live_latency_ticker.py
   ```

### Host Dashboard Not Receiving Data

1. Verify the TCP bridge is running and showing messages
2. Check that port 5555 is accessible from the host:
   ```bash
   nc -zv localhost 5555
   ```
3. Try running the container dashboard first to verify metrics are flowing

### Dependencies

Make sure you have the required Python packages:

```bash
source .venv/bin/activate
pip install zmq matplotlib numpy
```

## Files Modified/Created

- `host_dashboard.py` - New host-compatible dashboard
- `edgeric/tcp_bridge.py` - TCP bridge for IPC-to-TCP forwarding
- `start_tcp_bridge.sh` - Script to start TCP bridge
- `start_edgeric_with_screen.sh` - Updated to expose port 5555
- `launch_dashboard.sh` - Updated with new options
- `HOST_DASHBOARD_SETUP.md` - This documentation file

## Next Steps

1. Test the TCP bridge connection
2. Verify the host dashboard displays real-time data
3. Optional: Add more metrics or visualization features
4. Optional: Create a Docker Compose setup for easier deployment
