# EdgeRIC
This repository currently contains the codebase built with the srsRAN-4G Project. We will update this repository with the srsRAN-5G Project shortly!

Refer to full paper: https://www.usenix.org/system/files/nsdi24-ko.pdf

Refer to EdgeRIC documentation: https://edgeric.github.io/

Refer to how to run the repository: https://edgeric.github.io/edgeric-workshop-tutorial.html

## Quick Start

### VS Code Setup (Recommended)

This repository includes VS Code configuration for easy development:

1. **Clone and Open:**
   ```bash
   git clone <repository-url>
   cd EdgeRIC-A-real-time-RIC
   code .
   ```

2. **Install Recommended Extensions:**
   - VS Code will prompt to install recommended extensions
   - These include C/C++, Python, Docker, and Protocol Buffers support

3. **Build with VS Code:**
   - Press `Ctrl+Shift+P` → "Tasks: Run Build Task"
   - Or use the "Build EdgeRIC" task from the Command Palette

### Building EdgeRIC

**Recommended:** Use the unified build script for all builds:

```bash
./build.sh
```

This script will:
- Start the development container if needed
- Generate all protobuf files
- Build srsRAN eNB and UE components
- Build EdgeRIC controller
- Verify the build completed successfully

### Running EdgeRIC

After building, start the complete EdgeRIC setup:

```bash
./start_edgeric_with_screen.sh bridge test
```

This will start all EdgeRIC components including:
- GNU Radio simulator
- srsRAN EPC and eNB
- srsRAN UE instances
- Traffic generators
- EdgeRIC applications
- **TCP bridge for web dashboard (starts automatically after 10-second delay)**
- **Web dashboard (starts automatically in Window 11)**

### Web Dashboard

EdgeRIC includes a modern web-based dashboard that **runs automatically inside the container**:

#### Accessing the Dashboard

After starting EdgeRIC with the startup script, the web dashboard is immediately available at:

**http://localhost:8050**

No additional setup required! The dashboard automatically:
- Connects to the EdgeRIC system via TCP bridge
- Shows real-time metrics from all active UEs
- Updates every second with live data

#### Manual Dashboard Launch

If you need to run the dashboard manually (for debugging or development):

```bash
# Option 1: Use the launcher script (shows all options)
./launch_dashboard.sh

# Option 2: Run directly on host (requires EdgeRIC container running)
python3 web_dashboard.py
```

#### Dashboard Features

- **Real-time Metrics**: Latency, backlog, throughput, CQI, and SNR
- **Rolling Window**: Configurable sample count (100-5000 points)
- **Running Averages**: Configurable averaging window (10-100 samples)
- **Multi-UE Support**: RNTI selection with multi-select dropdown
- **Connection Monitoring**: Real-time connection status with LED indicator
- **Modern UI**: Clean, responsive interface with monospace fonts

#### Accessing the Dashboard

Open your browser and navigate to: **http://localhost:8050**

The dashboard will automatically connect to the EdgeRIC system and display real-time metrics from all active UEs.

### Legacy Build Scripts

The following legacy build scripts are still available but deprecated:
- `build_edgeric.sh` / `build_edgeric_vscode.sh` - Legacy build scripts
- `make_ran.sh` / `make_ran_improved.sh` - Direct container build scripts

**Note:** These may not include all the latest protobuf generation steps. Use `build.sh` for the most reliable build process.

## Features

### EdgeRIC Applications (muApps)

EdgeRIC includes several intelligent scheduling applications:

- **muApp1**: Real-time inference using pre-trained RL models
- **muApp2**: Reinforcement learning training for throughput optimization  
- **muApp3**: Advanced scheduling algorithms and baselines
- **muApp4**: Latency-aware RL training with specialized reward functions
- **muApp5**: Real-time algorithmic latency optimization (no training required)

### Latency Monitoring

EdgeRIC now includes comprehensive latency monitoring capabilities:
- Real-time latency metrics collection from srsRAN eNB
- Latency data display in EdgeRIC Python controller
- Integrated protobuf messaging for latency values
- Web dashboard visualization of latency trends

## Development

### Repository Structure

- `edgeric/` - EdgeRIC controller and ML components
- `srsran-enb/` - Modified srsRAN eNB with EdgeRIC integration
- `srsran-ue/` - Modified srsRAN UE components
- `traffic-generator/` - Network traffic generation tools
- `build.sh` - Unified build script (recommended)

### Contributing

1. Use `build.sh` for all builds to ensure consistency
2. Run tests after making changes
3. Follow the protobuf integration patterns for new metrics
