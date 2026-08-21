ARG OPENPCDET_DEPS_IMAGE=pdb-openpcdet-deps:latest
FROM ${OPENPCDET_DEPS_IMAGE}

ENV HOME=/home/dockeruser

WORKDIR /workspace

ARG HOST_UID=1000
ARG HOST_GID=1000

RUN groupadd --gid "${HOST_GID}" dockeruser && \
    useradd \
        --uid "${HOST_UID}" \
        --gid "${HOST_GID}" \
        --create-home \
        --shell /bin/bash \
        dockeruser && \
    git config --system --add safe.directory /workspace/OpenPCDet

USER dockeruser

ENTRYPOINT ["bash", "/workspace/src/scripts/run_openpcdet.sh"]