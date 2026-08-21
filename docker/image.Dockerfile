ARG IMAGE_DEPS_IMAGE=pdb-image-deps:latest
FROM ${IMAGE_DEPS_IMAGE}

ENV HOME=/home/dockeruser

WORKDIR /workspace

# user
ARG HOST_UID=1000
ARG HOST_GID=1000

RUN groupadd --gid "${HOST_GID}" dockeruser && \
    useradd --uid "${HOST_UID}" --gid "${HOST_GID}" --create-home --shell /bin/bash dockeruser

# RUN chown -R "${HOST_UID}:${HOST_GID}" /workspace/src

USER dockeruser

ENTRYPOINT ["bash", "/workspace/src/scripts/run_image.sh"]