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

### Legacy Build Scripts

The following legacy build scripts are still available but deprecated:
- `build_edgeric.sh` / `build_edgeric_vscode.sh` - Legacy build scripts
- `make_ran.sh` / `make_ran_improved.sh` - Direct container build scripts

**Note:** These may not include all the latest protobuf generation steps. Use `build.sh` for the most reliable build process.

## Features

### Latency Monitoring

EdgeRIC now includes latency monitoring capabilities:
- Real-time latency metrics collection from srsRAN eNB
- Latency data display in EdgeRIC Python controller
- Integrated protobuf messaging for latency values

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
