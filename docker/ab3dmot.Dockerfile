FROM python:3.9-slim

ENV DEBIAN_FRONTEND=noninteractive
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
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

RUN git clone https://github.com/xinshuoweng/AB3DMOT.git /workspace/AB3DMOT

WORKDIR /workspace/AB3DMOT

RUN pip install \
    numpy==1.26.4 \
    scipy \
    scikit-learn \
    filterpy \
    numba \
    matplotlib \
    pyyaml \
    pillow \
    opencv-python-headless

WORKDIR /workspace

COPY src /workspace/src
COPY src/scripts/run_ab3dmot.sh /workspace/run_ab3dmot.sh

RUN chmod +x /workspace/run_ab3dmot.sh

ENTRYPOINT ["/workspace/run_ab3dmot.sh"]