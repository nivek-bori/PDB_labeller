#!/usr/bin/env bash
set -euo pipefail

# Prefer positional arguments over environment variables
DATA_DIR_PATH_ARG="${1:-}"
IMG_DIR_RPATH_ARG="${2:-}"

if [[ -n "$DATA_DIR_PATH_ARG" ]]; then
    DATA_DIR_PATH="$DATA_DIR_PATH_ARG"
elif [[ -n "${DATA_DIR_PATH:-}" ]]; then
    DATA_DIR_PATH="$DATA_DIR_PATH"
else
    echo "ERROR: DATA_DIR_PATH environment variable or position 1 argument must be set." >&2
    exit 1
fi

if [[ -n "$IMG_DIR_RPATH_ARG" ]]; then
    IMG_DIR_RPATH="$IMG_DIR_RPATH_ARG"
elif [[ -n "${IMG_DIR_RPATH:-}" ]]; then
    IMG_DIR_RPATH="$IMG_DIR_RPATH"
else
    echo "ERROR: IMG_DIR_RPATH environment variable or position 2 argument must be set." >&2
    exit 1
fi

exec python -m src.image.image "$DATA_DIR_PATH" "$IMG_DIR_RPATH"