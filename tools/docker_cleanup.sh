#!/usr/bin/env bash

set -euo pipefail

DELETE_GPS=0
DELETE_IMAGE=0
DELETE_OPENPCDET=0
DELETE_AB3DMOT=0

for arg in "$@"; do
  if [[ "$arg" == "--delete_gps" ]]; then
    DELETE_GPS=1
    break
  fi
  if [[ "$arg" == "--delete_image" ]]; then
    DELETE_IMAGE=1
    break
  fi
  if [[ "$arg" == "--delete_openpcdet" ]]; then
    DELETE_OPENPCDET=1
    break
  fi
  if [[ "$arg" == "--delete_ab3dmot" ]]; then
    DELETE_AB3DMOT=1
    break
  fi
  if [[ "$arg" == "--delete_lidar" ]]; then
    DELETE_OPENPCDET=1
    DELETE_AB3DMOT=1
    break
  fi
done

if [[ $DELETE_GPS -eq 1 ]]; then
  docker image rm pdb-gps:latest pdb-gps-deps:py310-v1 || true
fi
if [[ $DELETE_IMAGE -eq 1 ]]; then
  docker image rm pdb-image:latest pdb-image-deps:py310-v1 || true
fi
if [[ $DELETE_OPENPCDET -eq 1 ]]; then
  docker image rm pdb-openpcdet:latest pdb-openpcdet-deps:torch2.7.1-cu128-sm120-pcdet-233f849 || true
fi
if [[ $DELETE_AB3DMOT -eq 1 ]]; then
  docker image rm pdb-ab3dmot:latest pdb-ab3dmot-deps:py310-v1 || true
fi

docker container prune -f
docker image prune -f
docker builder prune -f --filter "until=168h"
