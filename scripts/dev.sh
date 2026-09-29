#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
conda run --no-capture-output -n vision-lab python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8018 --reload &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM
cd frontend
npm run dev
