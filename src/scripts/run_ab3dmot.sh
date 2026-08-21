#!/usr/bin/env bash
set -euo pipefail

LIDAR_RPATH_INDEX_ARG="${1:-}"

if [[ -n "$LIDAR_RPATH_INDEX_ARG" ]]; then
    LIDAR_RPATH_INDEX="$LIDAR_RPATH_INDEX_ARG"
elif [[ -n "${LIDAR_RPATH_INDEX:-}" ]]; then
    LIDAR_RPATH_INDEX="$LIDAR_RPATH_INDEX"
else
    echo "ERROR: LIDAR_RPATH_INDEX environment variable or position 1 argument must be set." >&2
    exit 1
fi

cd /workspace
python -m src.ab3dmot.prep_input

cd /workspace/AB3DMOT
python main.py --dataset detection_results --split test --det_name pointpillars

cd /workspace
python -m src.ab3dmot.format_output "$LIDAR_RPATH_INDEX"