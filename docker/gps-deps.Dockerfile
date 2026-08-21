# syntax=docker/dockerfile:1

# ============================================================
# Builder
# ============================================================
FROM python:3.10-slim-bookworm AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# Build-time dependencies
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
    libpng-dev

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

COPY src/gps/requirements.txt /workspace/gps_requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install --prefix=/install -r /workspace/gps_requirements.txt


# ============================================================
# Runtime
# ============================================================
FROM python:3.10-slim-bookworm AS runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace

WORKDIR /workspace

# runtime required libraries
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1 \
    libglib2.0-0 \
    libfreetype6 \
    libpng16-16

# copy python dependencies
COPY --from=builder /install /usr/local