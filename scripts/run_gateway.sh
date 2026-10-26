#!/usr/bin/env bash
# Start FastAPI Web Gateway
set -e
cd "$(dirname "$0")/.."
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
python3 scripts/run_gateway.py
