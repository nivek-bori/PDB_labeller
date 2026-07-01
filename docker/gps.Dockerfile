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

COPY src /workspace/src
COPY src/scripts/run_gps.sh /workspace/run_gps.sh

RUN pip install -r /workspace/src/gps/requirements.txt

RUN chmod +x /workspace/run_gps.sh

WORKDIR /workspace

ENTRYPOINT ["/workspace/run_gps.sh"]