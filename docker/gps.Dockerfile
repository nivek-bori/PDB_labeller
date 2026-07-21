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

# install dependencies
RUN pip install --upgrade pip setuptools wheel

COPY src/requirements.txt /workspace/requirements.txt
COPY src/gps/requirements.txt /workspace/gps_requirements.txt
RUN pip install -r /workspace/requirements.txt && \
    pip install -r /workspace/gps_requirements.txt

# copy source code
COPY src /workspace/src
COPY src/scripts/run_gps.sh /workspace/run_gps.sh

# execute
RUN chmod +x /workspace/run_gps.sh

WORKDIR /workspace

ENTRYPOINT ["/workspace/run_gps.sh"]