#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${IMG_SOURCE_PATH:-}" ]]; then
    exec python -m src.camera.ultralytics "${IMG_SOURCE_PATH}"
fi

exec python -m src.camera.ultralytics "$@"
