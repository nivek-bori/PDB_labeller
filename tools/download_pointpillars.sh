#!/bin/bash

read -p "Confirm download at ./models/pointpillars.pth? [y/N] " confirm
[[ "$confirm" =~ ^([yY]|[yY][eE][sS])$ ]] || exit 0

pip install -q gdown
mkdir -p ./model
gdown "https://drive.google.com/uc?id=1wMxWTpU1qUoY3DsCH31WJmvJxcjFXKlm" -O ./models/pointpillars.pth
pip uninstall -y -q gdown