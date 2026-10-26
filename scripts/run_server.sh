#!/usr/bin/env bash
# Start native gRPC server
set -e
cd "$(dirname "$0")/.."
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
python3 scripts/run_server.py
