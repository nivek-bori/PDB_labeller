# syntax=docker/dockerfile:1

# ============================================================
# Builder
# ============================================================
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    CUDA_HOME=/usr/local/cuda \
    TORCH_CUDA_ARCH_LIST=12.0 \
    TZ=Etc/UTC \
    PATH=/opt/venv/bin:$PATH

WORKDIR /workspace

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    git \
    build-essential \
    cmake \
    ninja-build

RUN python3 -m venv /opt/venv

RUN --mount=type=cache,target=/root/.cache/pip pip install --upgrade pip setuptools wheel

# clone openpcdet
ARG OPENPCDET_COMMIT

RUN git clone https://github.com/open-mmlab/OpenPCDet.git /workspace/OpenPCDet && \
    cd /workspace/OpenPCDet && \
    git checkout "${OPENPCDET_COMMIT}" && \
    sed -i '/from \.argo2\.argo2_dataset import Argo2Dataset/d' /workspace/OpenPCDet/pcdet/datasets/__init__.py && \
    sed -i "/['\"]Argo2Dataset['\"]: Argo2Dataset/d" /workspace/OpenPCDet/pcdet/datasets/__init__.py && \
    sed -i 's/^opencv-python$/opencv-python-headless==4.10.0.84/' /workspace/OpenPCDet/requirements.txt

# install cuda & openpcdet dependencies
# maybe needed: pycairo==1.28.0
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128 && \
    pip install blinker open3d==0.19.0 spconv==2.3.8

# install project dependencies
COPY src/openpcdet/requirements.txt /workspace/src/openpcdet/requirements.txt
COPY src/openpcdet/constraints.txt /workspace/src/openpcdet/constraints.txt

RUN --mount=type=cache,target=/root/.cache/pip pip install -r /workspace/OpenPCDet/requirements.txt -r /workspace/src/openpcdet/requirements.txt -c /workspace/src/openpcdet/constraints.txt

WORKDIR /workspace/OpenPCDet

RUN --mount=type=cache,target=/root/.cache/pip MAX_JOBS=32 pip install -e . --no-build-isolation


# ============================================================
# Dependency runtime image
# ============================================================
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace:/workspace/OpenPCDet

WORKDIR /workspace

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    git

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /workspace/OpenPCDet /workspace/OpenPCDet