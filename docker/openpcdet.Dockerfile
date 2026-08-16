FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
WORKDIR /workspace

ENV CUDA_HOME=/usr/local/cuda
ENV TORCH_CUDA_ARCH_LIST="12.0"

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace

# python dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common git build-essential cmake ninja-build curl \
    pkg-config libcairo2-dev libgl1 libglib2.0-0 \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update && apt-get install -y \
    python3.9 python3.9-dev python3.9-distutils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/pip/3.9/get-pip.py | python3.9

RUN ln -sf /usr/bin/python3.9 /usr/bin/python && \
    ln -sf /usr/local/bin/pip /usr/bin/pip

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# clone OpenPCDet && remove error causes
RUN git clone https://github.com/open-mmlab/OpenPCDet.git /workspace/OpenPCDet \
    && sed -i '/from \.argo2\.argo2_dataset import Argo2Dataset/d' \
       /workspace/OpenPCDet/pcdet/datasets/__init__.py \
    && sed -i "/['\"]Argo2Dataset['\"]: Argo2Dataset/d" \
       /workspace/OpenPCDet/pcdet/datasets/__init__.py

# download model
RUN pip install gdown
RUN mkdir -p /workspace/models && \
    gdown --fuzzy "https://drive.google.com/file/d/1wMxWTpU1qUoY3DsCH31WJmvJxcjFXKlm/view" \
    -O /workspace/models/pointpillars.pth

# install OpenPCCDet dependencies
RUN pip install --no-cache-dir --ignore-installed blinker av2==0.3.6 open3d==0.19.0 pycairo==1.28.0 spconv==2.3.8
RUN pip install --no-cache-dir torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu128

WORKDIR /workspace/OpenPCDet
RUN sed -i 's/^opencv-python$/opencv-python==4.10.0.84/' /workspace/OpenPCDet/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# install src dependencies
COPY src/requirements.txt /workspace/src/requirements.txt
COPY src/openpcdet/requirements.txt /workspace/src/openpcdet/requirements.txt
RUN pip install --no-cache-dir -r /workspace/src/requirements.txt && \
    pip install --no-cache-dir -r /workspace/src/openpcdet/requirements.txt

# TODO: REMOVE
RUN pip show torch torchvision torchaudio && \
    pip check
RUN python -c "import torch; import torchvision; print('torch:', torch.__version__); print('torchvision:', torchvision.__version__); print('torch CUDA:', torch.version.cuda); print('architectures:', torch.cuda.get_arch_list()); from torchvision.ops import nms; print('torchvision NMS OK')"

# compile OpenPCDet
WORKDIR /workspace/OpenPCDet
RUN MAX_JOBS=32 pip install --no-cache-dir -e . --no-build-isolation

# copy execution script
COPY src/scripts/run_openpcdet.sh /workspace/run_openpcdet.sh
RUN chmod +x /workspace/run_openpcdet.sh

# create workspace user
ARG HOST_UID=1000
ARG HOST_GID=1000

RUN groupadd --gid "${HOST_GID}" dockeruser && \
    useradd --uid "${HOST_UID}" --gid "${HOST_GID}" --create-home --shell /bin/bash dockeruser
RUN chown -R "${HOST_UID}:${HOST_GID}" /workspace
RUN git config --system --add safe.directory /workspace/OpenPCDet
ENV HOME=/home/dockeruser

USER dockeruser

# execute
ENTRYPOINT ["/workspace/run_openpcdet.sh"]