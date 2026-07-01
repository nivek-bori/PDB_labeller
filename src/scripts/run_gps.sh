#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${GPS_FILE_PATH:-}" ]]; then
    exec python -m src.gps.interpolate "${GPS_FILE_PATH}"
fi

exec python -m src.gps.interpolate "$@"
