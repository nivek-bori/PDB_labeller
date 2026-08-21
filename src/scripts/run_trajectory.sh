#!/usr/bin/env bash
set -euo pipefail

exec python -m src.gps.gps "$DATA_DIR_PATH"