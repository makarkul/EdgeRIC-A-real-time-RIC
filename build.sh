#!/bin/bash

# EdgeRIC Unified Build Script
# Handles container management and building automatically

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="edgeric_build"
IMAGE_NAME="nlpurnhyun/edgeric_base_oaic"

# Print header
echo -e "${BLUE}🚀 EdgeRIC Unified Build System${NC}"
echo -e "${BLUE}===============================${NC}"
echo ""

# Parse arguments
CLEAN_BUILD=false
FORCE_REBUILD=false

for arg in "$@"; do
    case $arg in
        clean)
            CLEAN_BUILD=true
            echo -e "${YELLOW}🧹 Clean build requested${NC}"
            ;;
        rebuild)
            FORCE_REBUILD=true
            echo -e "${YELLOW}🔄 Force rebuild requested${NC}"
            ;;
        help|-h|--help)
            echo -e "${BLUE}Usage:${NC}"
            echo -e "  ${YELLOW}./build.sh${NC}          - Incremental build"
            echo -e "  ${YELLOW}./build.sh clean${NC}     - Clean build"
            echo -e "  ${YELLOW}./build.sh rebuild${NC}   - Force rebuild everything"
            echo -e "  ${YELLOW}./build.sh help${NC}      - Show this help"
            echo ""
            echo -e "${BLUE}What this script does:${NC}"
            echo -e "  • Automatically manages Docker containers"
            echo -e "  • Generates all protobuf files"
            echo -e "  • Builds srsran-enb and srsran-ue"
            echo -e "  • Cleans up when done"
            exit 0
            ;;
    esac
done

echo ""

# Function to check if container is running
is_container_running() {
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"
}

# Function to cleanup container
cleanup_container() {
    echo -e "${YELLOW}🧹 Cleaning up container...${NC}"
    if docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"; then
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
}

# Function to start container
start_container() {
    echo -e "${BLUE}🐳 Starting build container...${NC}"
    
    # Setup X11 forwarding (without sudo for compatibility)
    if command -v xhost &> /dev/null; then
        xhost +local:docker >/dev/null 2>&1 || true
    fi
    
    # Start container
    docker run -d --name "$CONTAINER_NAME" \
        --network=host \
        --privileged=true \
        -e DISPLAY=${DISPLAY:-:0} \
        --env=NVIDIA_DRIVER_CAPABILITIES=all \
        --env=NVIDIA_VISIBLE_DEVICES=all \
        --env=QT_X11_NO_MITSHM=1 \
        -v "$SCRIPT_DIR:/home/EdgeRIC-A-real-time-RIC:rw" \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -v /dev:/dev \
        "$IMAGE_NAME" \
        tail -f /dev/null
    
    echo -e "${GREEN}✅ Container started${NC}"
}

# Function to run command in container
run_in_container() {
    docker exec "$CONTAINER_NAME" bash -c "cd /home/EdgeRIC-A-real-time-RIC && $1"
}

# Function to generate protobuf files
generate_protobuf() {
    echo -e "${BLUE}🔄 Generating protobuf files...${NC}"
    
    # Generate C++ protobuf files
    echo -e "${YELLOW}  📦 Generating C++ protobuf files...${NC}"
    run_in_container "cd srsran-enb/srsenb && protoc -I=protobufs --cpp_out=rtagent protobufs/metrics.proto"
    run_in_container "cd srsran-enb/srsenb && protoc -I=protobufs --cpp_out=rtagent protobufs/scheduling_weights.proto"
    
    # Generate Python protobuf files
    echo -e "${YELLOW}  🐍 Generating Python protobuf files...${NC}"
    run_in_container "cd edgeric && protoc --python_out=. metrics.proto"
    run_in_container "cd edgeric && protoc --python_out=. control_actions.proto"
    
    echo -e "${GREEN}✅ Protobuf files generated${NC}"
}

# Function to build component
build_component() {
    local component=$1
    
    echo -e "${BLUE}📦 Building $component...${NC}"
    
    if [ "$CLEAN_BUILD" = "true" ] || [ "$FORCE_REBUILD" = "true" ]; then
        echo -e "${YELLOW}  🧹 Cleaning previous build...${NC}"
        run_in_container "cd $component && rm -rf build"
    fi
    
    # Create build directory and run cmake if needed
    run_in_container "cd $component && mkdir -p build && cd build && cmake ../"
    
    # Build with make
    echo -e "${YELLOW}  🔨 Compiling $component...${NC}"
    run_in_container "cd $component/build && make -j\$(nproc)"
    
    echo -e "${GREEN}✅ $component built successfully${NC}"
}

# Function to verify build
verify_build() {
    echo -e "${BLUE}🔍 Verifying build...${NC}"
    
    # Check if binaries exist
    if run_in_container "test -f srsran-enb/build/srsenb/src/srsenb"; then
        echo -e "${GREEN}✅ srsenb binary exists${NC}"
    else
        echo -e "${RED}❌ srsenb binary missing${NC}"
        return 1
    fi
    
    if run_in_container "test -f srsran-ue/build/srsue/src/srsue"; then
        echo -e "${GREEN}✅ srsue binary exists${NC}"
    else
        echo -e "${RED}❌ srsue binary missing${NC}"
        return 1
    fi
    
    # Test protobuf integration
    if run_in_container "cd edgeric && python3 -c 'import metrics_pb2; import control_actions_pb2; print(\"Protobuf OK\")'"; then
        echo -e "${GREEN}✅ Protobuf integration working${NC}"
    else
        echo -e "${RED}❌ Protobuf integration failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Build verification passed${NC}"
}

# Main build process
main() {
    # Cleanup any existing container
    cleanup_container
    
    # Start fresh container
    start_container
    
    # Generate protobuf files
    generate_protobuf
    
    echo ""
    
    # Build components
    build_component "srsran-enb"
    echo ""
    build_component "srsran-ue"
    
    echo ""
    
    # Verify build
    verify_build
    
    echo ""
    echo -e "${GREEN}🎉 Build completed successfully!${NC}"
    echo -e "${GREEN}============================${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "  • Run EdgeRIC: ${YELLOW}./start_edgeric.sh${NC}"
    echo -e "  • Check status: ${YELLOW}docker ps${NC}"
    echo -e "  • View logs: ${YELLOW}docker logs $CONTAINER_NAME${NC}"
    echo ""
    
    # Keep container running for development
    echo -e "${BLUE}💡 Container '$CONTAINER_NAME' is kept running for development${NC}"
    echo -e "${BLUE}   To stop it: ${YELLOW}docker stop $CONTAINER_NAME${NC}"
    echo -e "${BLUE}   To clean up: ${YELLOW}docker rm $CONTAINER_NAME${NC}"
}

# Handle cleanup on script exit
trap cleanup_on_exit EXIT

cleanup_on_exit() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo ""
        echo -e "${RED}❌ Build failed!${NC}"
        echo -e "${YELLOW}💡 Container logs: ${YELLOW}docker logs $CONTAINER_NAME${NC}"
        echo -e "${YELLOW}💡 Debug shell: ${YELLOW}docker exec -it $CONTAINER_NAME /bin/bash${NC}"
    fi
}

# Run main function
main "$@"
