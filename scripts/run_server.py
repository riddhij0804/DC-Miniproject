#!/usr/bin/env python3
"""
Starts the Native Python gRPC Server on port 50051.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.grpc_server.server import serve

if __name__ == "__main__":
    host = os.environ.get("GRPC_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("GRPC_SERVER_PORT", "50051"))
    serve(host=host, port=port)
