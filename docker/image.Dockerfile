FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace
ENV PIP_NO_CACHE_DIR=1

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# install dependencies
COPY src/requirements.txt /workspace/requirements.txt
COPY src/image/requirements.txt /workspace/image_requirements.txt
RUN pip install -r /workspace/requirements.txt && \
    pip install -r /workspace/image_requirements.txt

RUN pip install --upgrade pip setuptools wheel

# copy execution script
COPY src/scripts/run_image.sh /workspace/run_image.sh
RUN chmod +x /workspace/run_image.sh

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
ENTRYPOINT ["/workspace/run_image.sh"]
