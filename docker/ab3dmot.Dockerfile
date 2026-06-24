FROM nvidia/cuda:11.7.1-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
WORKDIR /workspace

ENV CUDA_HOME=/usr/local/cuda
ENV TORCH_CUDA_ARCH_LIST="7.5 8.0 8.6"

# python dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-dev python3-pip git build-essential cmake ninja-build \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

RUN pip install --upgrade pip setuptools wheel

# install AB3DMOT
RUN git clone https://github.com/xinshuoweng/AB3DMOT.git
WORKDIR /workspace/AB3DMOT

RUN pip install -r requirements.txt

# # execute script
WORKDIR /workspace

COPY src /workspace/src
COPY src/scripts/run_ab3dmot.sh /workspace/run_ab3dmot.sh

RUN chmod +x /workspace/run_ab3dmot.sh

ENTRYPOINT ["/workspace/run_ab3dmot.sh"]

CMD ["bin/bash"]