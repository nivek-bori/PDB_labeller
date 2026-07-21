#!/usr/bin/env bash
set -euo pipefail

# PREPROCESS LIDAR

# Prefer positional arguments over environment variables
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

echo "run_openpcdet.sh >>> preprocessing LIDAR data..."
python -m src.openpcdet.prep_openpcdet_in "$DATA_DIR_PATH" "$LIDAR_SOURCE_PATH"

# OPENPCDET
python -m openpcdet.datasets.custom.custom_dataset create_custom_infos openpcdet/tools/cfgs/dataset_configs/custom_dataset.yaml

echo "run_openpcdet.sh >>> running OpenPCDet..."
cd /workspace/OpenPCDet

python tools/test.py \
  --cfg_file /workspace/data/intermediate/lidar/model.yaml \
  --ckpt /workspace/models/pointpillars.pth \
  --batch_size 1 \
  --workers 0

echo "Done."