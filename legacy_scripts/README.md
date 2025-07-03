# Legacy Scripts Directory

This directory contains legacy build scripts that are no longer actively used in the unified EdgeRIC build system.

## Legacy Scripts

- `build_edgeric.sh` - Old build script for EdgeRIC
- `build_edgeric_vscode.sh` - Old VS Code specific build script
- `make_ran.sh` - Original build script for srsRAN components
- `dockerbuild_edgeric_oaic.sh` - Legacy Docker build script
- `dockerexec_edgeric_oaic.sh` - Legacy Docker exec script
- `dockerrun_edgeric_oaic.sh` - Legacy Docker run script
- `start_container.sh` - Legacy container startup script
- `build_trial.sh` - Trial build scripts from srsran-enb and srsran-ue

## Migration to Unified Build System

The new unified build system uses:
- `../build.sh` - Main build script
- `../make_ran_improved.sh` - Updated build script for srsRAN components

## Why These Scripts Are Deprecated

These scripts have been replaced by the unified build system which:
1. Provides better error handling
2. Automatically manages Docker containers
3. Generates all protobuf files correctly
4. Supports clean builds and incremental builds
5. Provides better user feedback
6. Simplifies the development workflow

## If You Need to Use Legacy Scripts

These scripts are preserved for reference but may not work with the current codebase structure. If you need to use them, you may need to:
1. Update paths and dependencies
2. Ensure protobuf files are generated
3. Handle container management manually

**Recommendation**: Use the unified build system instead: `../build.sh`
