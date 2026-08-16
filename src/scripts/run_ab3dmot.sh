#!/usr/bin/env bash
set -euo pipefail

cd /workspace
python -m src.ab3dmot.prep_input

cd /workspace/AB3DMOT
python main.py --dataset detection_results --split test --det_name pointpillars