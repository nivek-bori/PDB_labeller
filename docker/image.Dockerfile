FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
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

# copy source code
COPY src /workspace/src
COPY models /workspace/models
COPY src/scripts/run_image.sh /workspace/run_image.sh

# execute
RUN chmod +x /workspace/run_image.sh

ENTRYPOINT ["/workspace/run_image.sh"]
