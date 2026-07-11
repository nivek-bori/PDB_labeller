FROM python:3.8-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace/AB3DMOT:/workspace/Xinshuo_PyToolbox:/workspace/src

WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    pkg-config \
    libgl1 \
    libglib2.0-0 \
    libfreetype6-dev \
    libpng-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

# Clone AB3DMOT
RUN git clone https://github.com/nivek-bori/AB3DMOT.git /workspace/AB3DMOT

# Install AB3DMOT dependencies
RUN pip install \
    numpy==1.24.4 \
    scipy \
    scikit-learn \
    filterpy==1.4.5 \
    matplotlib \
    pyyaml \
    pillow \
    opencv-python-headless \
    glob2==0.6 \
    easydict==1.9 \
    numba==0.57.1 \
    llvmlite==0.40.1

# Clone Xinshuo_PyToolbox
RUN git clone https://github.com/xinshuoweng/Xinshuo_PyToolbox /workspace/Xinshuo_PyToolbox

# Install Xinshuo dependencies
WORKDIR /workspace/Xinshuo_PyToolbox

RUN pip install \
    numpy==1.24.4 \
    scipy \
    matplotlib \
    pillow \
    opencv-python-headless \
    pyyaml \
    easydict

# Execution Script
WORKDIR /workspace

COPY src /workspace/src
COPY src/scripts/run_ab3dmot.sh /workspace/run_ab3dmot.sh

RUN chmod +x /workspace/run_ab3dmot.sh

ENTRYPOINT ["/workspace/run_ab3dmot.sh"]