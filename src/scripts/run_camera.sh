#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${IMG_SOURCE_PATH:-}" ]]; then
    exec python -m src.scripts.track_2d "${IMG_SOURCE_PATH}"
fi

exec python -m src.scripts.track_2d "$@"
