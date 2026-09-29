#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
conda env create -f environment-mediapipe.yml
