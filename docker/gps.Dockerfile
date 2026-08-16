FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /workspace

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace

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

# copy execution scriopt
COPY src/scripts/run_gps.sh /workspace/run_gps.sh
RUN chmod +x /workspace/run_gps.sh
    
# user
ARG HOST_UID=1000
ARG HOST_GID=1000

RUN groupadd --gid "${HOST_GID}" dockeruser && \
    useradd --uid "${HOST_UID}" --gid "${HOST_GID}" --create-home --shell /bin/bash dockeruser
RUN chown -R "${HOST_UID}:${HOST_GID}" /workspace
RUN git config --system --add safe.directory /workspace/OpenPCDet
ENV HOME=/home/dockeruser

USER dockeruser

    # execute
ENTRYPOINT ["/workspace/run_gps.sh"]