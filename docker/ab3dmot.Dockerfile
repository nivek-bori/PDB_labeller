FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace/AB3DMOT:/workspace/Xinshuo_PyToolbox:/workspace

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

# Clone Xinshuo_PyToolbox
RUN git clone https://github.com/xinshuoweng/Xinshuo_PyToolbox /workspace/Xinshuo_PyToolbox

# Install AB3DMOT dependencies
RUN pip install -r /workspace/AB3DMOT/requirements.txt && \
    pip install -r /workspace/Xinshuo_PyToolbox/requirements.txt

# install src dependencies
COPY src/requirements.txt /workspace/src/requirements.txt
COPY src/ab3dmot/requirements.txt /workspace/src/ab3dmot/requirements.txt
RUN pip install --no-cache-dir -r /workspace/src/requirements.txt && \
    pip install --no-cache-dir -r /workspace/src/ab3dmot/requirements.txt

# copy execution script
COPY src/scripts/run_ab3dmot.sh /workspace/run_ab3dmot.sh
RUN chmod +x /workspace/run_ab3dmot.sh

# user
ARG HOST_UID=1000
ARG HOST_GID=1000

RUN groupadd --gid "${HOST_GID}" dockeruser && \
    useradd --uid "${HOST_UID}" --gid "${HOST_GID}" --create-home --shell /bin/bash dockeruser
RUN chown -R "${HOST_UID}:${HOST_GID}" /workspace
RUN git config --system --add safe.directory /workspace/AB3DMOT
RUN git config --system --add safe.directory /workspace/Xinshuo_PyToolbox
ENV HOME=/home/dockeruser

USER dockeruser

# execute
ENTRYPOINT ["/workspace/run_ab3dmot.sh"]