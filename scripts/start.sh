#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f frontend/dist/index.html ]]; then
  (cd frontend && npm ci && npm run build)
fi
exec conda run --no-capture-output -n vision-lab python -m uvicorn app.main:app --app-dir backend --host "${VISION_HOST:-127.0.0.1}" --port "${VISION_PORT:-8018}"
