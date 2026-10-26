#!/usr/bin/env python3
"""
Starts the FastAPI Web Gateway using uvicorn on port 8000.
"""
import os
import sys
import uvicorn

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    host = os.environ.get("WEB_GATEWAY_HOST", "127.0.0.1")
    port = int(os.environ.get("WEB_GATEWAY_PORT", "8000"))
    print(f"==================================================")
    print(f" [Web Gateway] Starting HTTP & WebSocket Gateway")
    print(f" [Web Gateway] Serving on: http://{host}:{port}")
    print(f" [Web Gateway] Browser Access: http://{host}:{port}/marketplace")
    print(f"==================================================")
    uvicorn.run("backend.web_gateway.app:app", host=host, port=port, reload=False)
