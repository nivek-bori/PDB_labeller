# syntax=docker/dockerfile:1

# ============================================================
# Builder
# ============================================================
FROM python:3.10-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    cmake \
    pkg-config \
    libgl1 \
    libglib2.0-0 \
    libfreetype6-dev \
    libpng-dev \
    libgomp1

RUN python -m venv /opt/venv

ENV PATH=/opt/venv/bin:$PATH

RUN --mount=type=cache,target=/root/.cache/pip pip install --upgrade pip setuptools wheel

# clone ab3dmot & xinshuo pytoolbox
RUN git clone --depth 1 https://github.com/nivek-bori/AB3DMOT.git /workspace/AB3DMOT && \
    git clone --depth 1 https://github.com/xinshuoweng/Xinshuo_PyToolbox.git /workspace/Xinshuo_PyToolbox

# install project, ab3dmot & xinsuo pytoolbox dependencies
COPY src/ab3dmot/requirements.txt /workspace/src/ab3dmot/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install \
        -r /workspace/src/ab3dmot/requirements.txt \
        -r /workspace/AB3DMOT/requirements.txt \
        -r /workspace/Xinshuo_PyToolbox/requirements.txt

# ============================================================
# Runtime
# ============================================================
FROM python:3.10-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/AB3DMOT:/workspace/Xinshuo_PyToolbox:/workspace \
    PATH=/opt/venv/bin:$PATH

WORKDIR /workspace

# install runtime only dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1 \
    libglib2.0-0 \
    libfreetype6 \
    libpng16-16 \
    libgomp1

# copy python dependencies
COPY --from=builder /opt/venv /opt/venv

# copy ab3dmot & xinshou pytoolbox
COPY --from=builder /workspace/AB3DMOT /workspace/AB3DMOT
COPY --from=builder /workspace/Xinshuo_PyToolbox /workspace/Xinshuo_PyToolbox