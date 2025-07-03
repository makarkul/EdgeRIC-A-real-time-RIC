#!/bin/bash

# EdgeRIC Build Script
# Now supports incremental builds by default, clean builds with 'clean' argument

FORCE_CLEAN=${1:-false}

echo "🔨 EdgeRIC Build Script"
echo "======================"

if [ "$FORCE_CLEAN" = "true" ] || [ "$FORCE_CLEAN" = "clean" ]; then
    echo "🧹 Force clean build requested"
    CLEAN_BUILD=true
else
    echo "⚡ Incremental build (use './make_ran.sh clean' for clean build)"
    CLEAN_BUILD=false
fi

echo ""

# Generate protobuf files first (if protoc is available)
echo "🔄 Generating protobuf files..."
if command -v protoc &> /dev/null; then
    echo "  ✅ protoc found, regenerating protobuf files..."
    
    # Generate C++ protobuf files for srsran-enb
    cd srsran-enb/srsenb
    protoc -I=protobufs --cpp_out=rtagent protobufs/metrics.proto
    
    # Generate Python protobuf files for edgeric
    cd ../../edgeric
    protoc --python_out=. metrics.proto
    
    cd ..
    echo "  ✅ Protobuf files generated"
else
    echo "  ⚠️  protoc not found, assuming protobuf files are up to date"
fi

echo ""

# Build srsran-enb
echo "📦 Building srsran-enb..."
cd srsran-enb

if [ "$CLEAN_BUILD" = "true" ] || [ ! -d "build" ]; then
    echo "  🧹 Cleaning previous build..."
    rm -rf build
    mkdir build
    cd build
    echo "  🔧 Running cmake..."
    cmake ../
else
    echo "  ⚡ Using existing build directory..."
    cd build
fi

echo "  🔨 Compiling with make -j$(nproc)..."
make -j $(nproc)
cd ../..

echo ""

# Build srsran-ue
echo "📦 Building srsran-ue..."
cd srsran-ue

if [ "$CLEAN_BUILD" = "true" ] || [ ! -d "build" ]; then
    echo "  🧹 Cleaning previous build..."
    rm -rf build
    mkdir build
    cd build
    echo "  🔧 Running cmake..."
    cmake ../
else
    echo "  ⚡ Using existing build directory..."
    cd build
fi

echo "  🔨 Compiling with make -j$(nproc)..."
make -j $(nproc)
cd ../..

echo ""
echo "🎉 Build completed successfully!"
echo "Usage: ./make_ran.sh [clean]"
