#!/usr/bin/env bash
set -euo pipefail

cd /workspace/AB3DMOT

python main.py --dataset detection_results --split test --det_name pointpillars