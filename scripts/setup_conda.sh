#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
conda env create -f environment.yml
conda run -n vision-lab python -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cpu
conda run -n vision-lab python -m pip install -r backend/requirements-models.txt
# 第三方包同时声明普通/无界面 OpenCV；最终以同版本 contrib 补全 CSRT/条码实现。
conda run -n vision-lab python -m pip install --force-reinstall --no-deps opencv-contrib-python==4.13.0.92
conda env create -f environment-mediapipe.yml
cd frontend
npm ci
npm run build
