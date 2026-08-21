ARG AB3DMOT_DEPS_IMAGE=pdb-ab3dmot-deps:latest
FROM ${AB3DMOT_DEPS_IMAGE}

ENV HOME=/home/dockeruser

WORKDIR /workspace

# user
ARG HOST_UID=1000
ARG HOST_GID=1000

RUN groupadd --gid "${HOST_GID}" dockeruser && \
    useradd --uid "${HOST_UID}" --gid "${HOST_GID}" --create-home --shell /bin/bash dockeruser && \
    git config --system --add safe.directory /workspace/AB3DMOT && \
    git config --system --add safe.directory /workspace/Xinshuo_PyToolbox

USER dockeruser

ENTRYPOINT ["bash", "/workspace/src/scripts/run_ab3dmot.sh"]