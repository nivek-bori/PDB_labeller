#!/usr/bin/env bash
set -euo pipefail

# parse arguements
DATA_DIR_PATH_ARG="${1:-}"
LIDAR_RPATH_INDEX_ARG="${2:-}"

if [[ -n "$DATA_DIR_PATH_ARG" ]]; then
    DATA_DIR_PATH="$DATA_DIR_PATH_ARG"
elif [[ -n "${DATA_DIR_PATH:-}" ]]; then
    DATA_DIR_PATH="$DATA_DIR_PATH"
else
    echo "ERROR: DATA_DIR_PATH environment variable or position 1 argument must be set." >&2
    exit 1
fi

if [[ -n "$LIDAR_RPATH_INDEX_ARG" ]]; then
    LIDAR_RPATH_INDEX="$LIDAR_RPATH_INDEX_ARG"
elif [[ -n "${LIDAR_RPATH_INDEX:-}" ]]; then
    LIDAR_RPATH_INDEX="$LIDAR_RPATH_INDEX"
else
    echo "ERROR: LIDAR_RPATH_INDEX environment variable or position 2 argument must be set." >&2
    exit 1
fi

cd /workspace
python -m src.ab3dmot.prep_input "$DATA_DIR_PATH" "$LIDAR_RPATH_INDEX"

cd /workspace/AB3DMOT
python main.py --dataset detection_results --split test --det_name pointpillars

cd /workspace
python -m src.ab3dmot.format_output "$DATA_DIR_PATH" "$LIDAR_RPATH_INDEX"