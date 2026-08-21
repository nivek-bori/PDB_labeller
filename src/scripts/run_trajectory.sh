#!/usr/bin/env bash
set -euo pipefail

exec python -m src.trajectory.inference "$DATA_DIR_PATH"