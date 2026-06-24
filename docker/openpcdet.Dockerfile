FROM nvidia/cuda:11.7.1-cudnn8-devel-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
WORKDIR /workspace

ENV CUDA_HOME=/usr/local/cuda
ENV TORCH_CUDA_ARCH_LIST="7.5 8.0 8.6"

# python dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    git build-essential cmake ninja-build curl \
    libgl1 libglib2.0-0 \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update && apt-get install -y \
    python3.9 python3.9-dev python3.9-distutils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/pip/3.9/get-pip.py | python3.9

RUN ln -sf /usr/bin/python3.9 /usr/bin/python && \
    ln -sf /usr/local/bin/pip /usr/bin/pip

RUN pip install --upgrade pip setuptools wheel

# install OpenPCDet
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117
RUN pip install cumm-cu117 spconv-cu117

RUN git clone https://github.com/open-mmlab/OpenPCDet.git
WORKDIR /workspace/OpenPCDet

RUN pip install -r requirements.txt
RUN MAX_JOBS=5 pip install -e . --no-build-isolation

# install additional dependencies
RUN pip install av2==0.3.6 gdown
RUN pip install numpy==1.26.4

# download model
RUN mkdir -p /workspace/models && \
    gdown --fuzzy "https://drive.google.com/file/d/1wMxWTpU1qUoY3DsCH31WJmvJxcjFXKlm/view" \
    -O /workspace/models/pointpillars.pth

# execute script
WORKDIR /workspace

COPY src /workspace/src
COPY src/scripts/run_openpcdet.sh /workspace/run_openpcdet.sh

RUN chmod +x /workspace/run_openpcdet.sh

ENTRYPOINT ["/workspace/run_openpcdet.sh"]