#!/usr/bin/env bash
set -e

if [[ -n "${LIDAR_SOURCE_PATH:-}" ]]; then
    python -m src.openpcdet.preprocess_data "${LIDAR_SOURCE_PATH}"
fi

echo "Preprocessing LiDAR data..."
python -m src.openpcdet.preprocess_data "$@"

echo "Running OpenPCDet..."
cd /workspace/OpenPCDet

python -c "import platform; print('machine:', platform.machine())"
python -c "import numpy; print('numpy:', numpy.__version__)"
python -c "import torch; print('torch:', torch.__version__, torch.version.cuda, torch.cuda.is_available())"
python -c "import spconv; print('spconv imported')"
python -c "import pcdet; print('pcdet imported')"
python -c "import av2; print('av2 imported')"

python tools/test.py \
  --cfg_file /workspace/data/intermediate/lidar/model.yaml \
  --ckpt /workspace/models/pointpillars.pth \
  --batch_size 1 \
  --workers 0

echo "Done."