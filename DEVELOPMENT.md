# EdgeRIC Development Workspace

## Overview

This EdgeRIC repository is now configured with a comprehensive VS Code workspace setup for easy development and collaboration.

## What's Included

### VS Code Configuration

- **tasks.json** - Build tasks, run tasks, and debugging tasks
- **launch.json** - Debug configurations for Python and C++ components
- **settings.json** - Project-specific settings and C++ IntelliSense
- **extensions.json** - Recommended extensions for EdgeRIC development
- **EdgeRIC.code-workspace** - Multi-root workspace configuration

### Key Features

1. **Unified Build System**: Single `./build.sh` script handles everything
2. **Clean Organization**: Legacy scripts moved to `legacy_scripts/`
3. **Developer-Friendly**: Proper .gitignore, excluded build artifacts
4. **IntelliSense Support**: C++ and Python code completion configured
5. **Docker Integration**: Container management through VS Code tasks

## Quick Start for New Developers

1. **Clone and Open:**
   ```bash
   git clone <repository-url>
   cd EdgeRIC-A-real-time-RIC
   code .
   ```

2. **Install Extensions:**
   VS Code will prompt to install recommended extensions

3. **Build:**
   - Press `Ctrl+Shift+P` → "Tasks: Run Build Task"
   - Or run `./build.sh` in terminal

4. **Run:**
   - Use "Start EdgeRIC" task from Command Palette
   - Or run `./start_edgeric_with_screen.sh bridge test`

## Available VS Code Tasks

- **Build EdgeRIC** - Main build task (default)
- **Build EdgeRIC (Clean)** - Clean build
- **Start EdgeRIC** - Start the complete system
- **Stop EdgeRIC** - Stop running components
- **Check EdgeRIC Status** - Check Docker container status
- **Open EdgeRIC Terminal** - Open shell in container
- **Attach to EdgeRIC Screen** - Attach to running screen session
- **Emergency Cleanup** - Force cleanup containers

## Debug Configurations

- **EdgeRIC PPO Training** - Debug ML training components
- **EdgeRIC Debug with Attach** - Remote debugging in container
- **muApp1 DL Scheduling** - Debug scheduling application
- **muApp3 Monitor** - Debug monitoring application

## Development Benefits

### For Individual Developers
- Consistent build environment
- Proper IntelliSense and debugging
- Easy task execution
- Container management automation

### For Teams
- Standardized development environment
- Shared VS Code configuration
- Consistent build process
- Easy onboarding for new developers

## Essential EdgeRIC Scripts

### Core Build & Operation Scripts (Required)
- `build.sh` - **Main unified build script**
- `make_ran_improved.sh` - srsRAN build script (called by build.sh)
- `start_edgeric.sh` - Start EdgeRIC components
- `start_edgeric_with_screen.sh` - Start EdgeRIC with screen sessions
- `stop_edgeric.sh` - Stop EdgeRIC components
- `emergency_cleanup.sh` - Force cleanup containers and processes

### Network & Traffic Scripts (Required)
- `run_enb.sh` - Start srsRAN eNB
- `run_epc.sh` - Start srsRAN EPC
- `run_srsran_2ue.sh` - Start 2-UE srsRAN configuration
- `run_srsran_4ue.sh` - Start 4-UE srsRAN configuration
- `stop_ran.sh` - Stop RAN components
- `traffic-generator/` - Network traffic generation scripts

### GNURadio Scripts (Required)
- `top_block_2ue_23.04MHz.py` - 2-UE GNURadio configuration
- `top_block_2ue_no_gui.py` - 2-UE headless GNURadio
- `top_block_4ue_23.04MHz.py` - 4-UE GNURadio configuration
- `top_block_4ue_no_gui.py` - 4-UE headless GNURadio

### Configuration Files (Required)
- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker container configuration
- `zmq.h`, `zmq.hpp` - ZMQ headers for compilation

### Legacy Scripts (Deprecated)
- `legacy_scripts/` - All old build scripts moved here
- Use `build.sh` instead of any legacy scripts

## Repository Structure

```
EdgeRIC-A-real-time-RIC/
├── .vscode/                    # VS Code configuration
├── .devcontainer/              # Dev container configuration
├── legacy_scripts/             # Deprecated build scripts
├── edgeric/                    # EdgeRIC controller
├── srsran-enb/                 # Modified srsRAN eNB
├── srsran-ue/                  # Modified srsRAN UE
├── build.sh                    # Unified build script
├── EdgeRIC.code-workspace      # VS Code workspace
└── README.md                   # Main documentation
```

## Migration Notes

### From Legacy Scripts
- `build_edgeric.sh` → `build.sh`
- `build_edgeric_vscode.sh` → VS Code "Build EdgeRIC" task
- `make_ran.sh` → Integrated into `build.sh`
- Manual container management → Automated in `build.sh`

### Benefits of New System
- Single command build process
- Automatic protobuf generation
- Better error handling and feedback
- Consistent development environment
- Easier debugging and development

## VS Code Extensions

### Essential Extensions (Auto-recommended)
- **C/C++** - IntelliSense, debugging, code navigation
- **Python** - Python support, IntelliSense, debugging
- **CMake Tools** - CMake integration
- **Protocol Buffers** - .proto file syntax support
- **Docker** - Docker container management

### Useful Extensions
- **Code Runner** - Quick code execution
- **TODO Tree** - Track TODO/FIXME comments
- **Serial Monitor** - Hardware debugging
- **Hex Editor** - Binary file inspection

## Best Practices

1. **Always use `build.sh`** for building - it handles all dependencies
2. **Use VS Code tasks** for common operations
3. **Commit VS Code configuration** changes that benefit the team
4. **Keep legacy_scripts** for reference but prefer unified build system
5. **Use the integrated terminal** for Docker operations

## Troubleshooting

### Build Issues
- Run `./build.sh clean` for clean build
- Check Docker is running
- Verify container permissions

### VS Code Issues
- Reload window if IntelliSense isn't working
- Check recommended extensions are installed
- Verify workspace is opened correctly

### Container Issues
- Use "Emergency Cleanup" task
- Check `docker ps` for running containers
- Restart Docker if needed

## Support

For issues with the development environment:
1. Check the main README.md
2. Review legacy_scripts/README.md for migration notes
3. Use VS Code's integrated terminal for debugging
4. Check Docker logs: `docker logs edgeric_build`

---

This workspace configuration makes EdgeRIC development more accessible and consistent across different development environments.
