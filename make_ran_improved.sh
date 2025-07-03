#!/bin/bash

# EdgeRIC Improved Build Script
# Supports incremental builds and proper protobuf generation

FORCE_CLEAN=${1:-false}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔨 EdgeRIC Improved Build Script${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

if [ "$FORCE_CLEAN" = "true" ] || [ "$FORCE_CLEAN" = "clean" ]; then
    echo -e "${YELLOW}🧹 Force clean build requested${NC}"
    CLEAN_BUILD=true
else
    echo -e "${GREEN}⚡ Incremental build (use './make_ran_improved.sh clean' for clean build)${NC}"
    CLEAN_BUILD=false
fi

echo ""

# Function to build a component
build_component() {
    local component=$1
    local clean=$2
    
    echo -e "${BLUE}📦 Building $component...${NC}"
    cd "$SCRIPT_DIR/$component"
    
    if [ "$clean" = "true" ] || [ ! -d "build" ]; then
        echo -e "${YELLOW}  🧹 Cleaning previous build...${NC}"
        rm -rf build
        mkdir build
        cd build
        echo -e "${YELLOW}  🔧 Running cmake...${NC}"
        cmake ../
    else
        echo -e "${GREEN}  ⚡ Using existing build directory...${NC}"
        cd build
    fi
    
    echo -e "${YELLOW}  🔨 Compiling with make -j$(nproc)...${NC}"
    if make -j $(nproc); then
        echo -e "${GREEN}  ✅ $component built successfully!${NC}"
        cd "$SCRIPT_DIR"
        return 0
    else
        echo -e "${RED}  ❌ $component build failed!${NC}"
        cd "$SCRIPT_DIR"
        return 1
    fi
}

# Generate protobuf files (this should be done in the container where protoc is available)
echo -e "${BLUE}🔄 Generating protobuf files...${NC}"
if command -v protoc &> /dev/null; then
    echo -e "${GREEN}  ✅ protoc found, regenerating protobuf files...${NC}"
    
    # Generate C++ protobuf files for srsran-enb
    echo -e "${YELLOW}  📦 Generating C++ protobuf files...${NC}"
    cd "$SCRIPT_DIR/srsran-enb/srsenb"
    protoc -I=protobufs --cpp_out=rtagent protobufs/metrics.proto
    protoc -I=protobufs --cpp_out=rtagent protobufs/scheduling_weights.proto
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✅ C++ protobuf files generated${NC}"
    else
        echo -e "${RED}  ❌ Failed to generate C++ protobuf files${NC}"
        exit 1
    fi
    
    # Generate Python protobuf files for edgeric
    echo -e "${YELLOW}  🐍 Generating Python protobuf files...${NC}"
    cd "$SCRIPT_DIR/edgeric"
    protoc --python_out=. metrics.proto
    protoc --python_out=. control_actions.proto
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✅ Python protobuf files generated${NC}"
    else
        echo -e "${RED}  ❌ Failed to generate Python protobuf files${NC}"
        exit 1
    fi
    
    cd "$SCRIPT_DIR"
else
    echo -e "${YELLOW}  ⚠️  protoc not found, assuming protobuf files are up to date${NC}"
    echo -e "${YELLOW}  ⚠️  Make sure to run this script inside the container where protoc is available${NC}"
fi
echo ""

# Build srsran-enb
if ! build_component "srsran-enb" "$CLEAN_BUILD"; then
    echo -e "${RED}❌ Build failed at srsran-enb${NC}"
    exit 1
fi

echo ""

# Build srsran-ue  
if ! build_component "srsran-ue" "$CLEAN_BUILD"; then
    echo -e "${RED}❌ Build failed at srsran-ue${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 All components built successfully!${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""
echo -e "${BLUE}Usage tips:${NC}"
echo -e "  • For incremental builds: ${YELLOW}./make_ran_improved.sh${NC}"
echo -e "  • For clean builds: ${YELLOW}./make_ran_improved.sh clean${NC}"
echo ""
