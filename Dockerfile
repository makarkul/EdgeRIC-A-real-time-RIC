FROM ubuntu:20.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    screen \
    vim \
    git \
    wget \
    curl \
    build-essential \
    cmake \
    libzmq3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set up workspace
WORKDIR /workspace

# Copy requirements and install Python dependencies
COPY requirements.txt* ./
RUN pip3 install --upgrade pip && \
    pip3 install torch torchvision torchaudio && \
    pip3 install gym hydra-core zmq debugpy matplotlib numpy scipy && \
    if [ -f requirements.txt ]; then pip3 install -r requirements.txt; fi

# Copy project files
COPY . /workspace

# Create necessary directories
RUN mkdir -p /workspace/outputs && \
    mkdir -p /workspace/logs

# Set Python path
ENV PYTHONPATH="/workspace:$PYTHONPATH"

# Expose ports for debugging and communication
EXPOSE 5000 8888 5678

CMD ["/bin/bash"]
