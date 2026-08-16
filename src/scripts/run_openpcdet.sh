#!/usr/bin/env bash
set -euo pipefail

# parse arguements
DATA_DIR_PATH_ARG="${1:-}"
LIDAR_SOURCE_PATH_ARG="${2:-}"

if [[ -n "$DATA_DIR_PATH_ARG" ]]; then
    DATA_DIR_PATH="$DATA_DIR_PATH_ARG"
elif [[ -n "${DATA_DIR_PATH:-}" ]]; then
    DATA_DIR_PATH="$DATA_DIR_PATH"
else
    echo "ERROR: DATA_DIR_PATH environment variable or position 1 argument must be set." >&2
    exit 1
fi

if [[ -n "$LIDAR_SOURCE_PATH_ARG" ]]; then
    LIDAR_SOURCE_PATH="$LIDAR_SOURCE_PATH_ARG"
elif [[ -n "${LIDAR_SOURCE_PATH:-}" ]]; then
    LIDAR_SOURCE_PATH="$LIDAR_SOURCE_PATH"
else
    echo "ERROR: LIDAR_SOURCE_PATH environment variable or position 2 argument must be set." >&2
    exit 1
fi

# preprocess lidar data
echo "run_openpcdet.sh >>> preprocessing LIDAR data..."
python -m src.openpcdet.prep_input "$DATA_DIR_PATH" "$LIDAR_SOURCE_PATH"

# execute inference
echo "run_openpcdet.sh >>> running OpenPCDet..."
python /workspace/src/openpcdet/inference.py \
  --cfg_file /workspace/data/intermediate/openpcdet/model.yaml \
  --ckpt /workspace/models/pointpillars.pth \
  --data_path /workspace/data/intermediate/openpcdet/points \
  --output_path /workspace/data/intermediate/openpcdet/detections \
  --ext .npy

echo "Done."