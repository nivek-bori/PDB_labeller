#!/usr/bin/env bash
set -euo pipefail

# Prefer positional argument over environment variable
DATA_DIR_PATH_ARG="${1:-}"

if [[ -n "$DATA_DIR_PATH_ARG" ]]; then
    DATA_DIR_PATH="$DATA_DIR_PATH_ARG"
elif [[ -n "${DATA_DIR_PATH:-}" ]]; then
    DATA_DIR_PATH="$DATA_DIR_PATH"
else
    echo "ERROR: DATA_DIR_PATH environment variable or position 1 argument must be set." >&2
    exit 1
fi

exec python -m src.gps.gps "$DATA_DIR_PATH"