"""
FastAPI Web Gateway for the Online Auction System.
Translates HTTP browser requests to native gRPC unary/streaming calls.
Also serves frontend static assets and exposes a WebSocket hub for live events.
"""
import os
import sys
from typing import List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.web_gateway.routers import auth, auctions
from backend.web_gateway.grpc_client import grpc_client

app = FastAPI(
    title="Online Auction System - Web Gateway",
    description="HTTP and WebSocket gateway proxying browser traffic to the native Python gRPC server",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(auctions.router)

# Mount static asset directories
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

# Frontend HTML Page Routes
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root():
    return RedirectResponse(url="/marketplace")

@app.api_route("/login", methods=["GET", "HEAD"], include_in_schema=False)
async def login_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "pages", "login.html"))

@app.api_route("/marketplace", methods=["GET", "HEAD"], include_in_schema=False)
async def marketplace_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "pages", "marketplace.html"))

@app.api_route("/auction-details", methods=["GET", "HEAD"], include_in_schema=False)
async def auction_details_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "pages", "auction-details.html"))

@app.api_route("/auction/{auction_id}", methods=["GET", "HEAD"], include_in_schema=False)
async def auction_details_by_id(auction_id: str):
    return FileResponse(os.path.join(FRONTEND_DIR, "pages", "auction-details.html"))

# Health & Diagnostics
@app.get("/health")
async def health_check():
    grpc_ok = grpc_client.ping()
    return {
        "gateway_status": "healthy",
        "grpc_backend_connected": grpc_ok,
        "grpc_target": grpc_client.target
    }

# ==========================================
# WebSocket Live Events Hub (Member 3 Integration Point)
# ==========================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections.discard(connection)

ws_manager = ConnectionManager()

@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for live auction event broadcasts.
    Teammates (Member 3) can push gRPC streaming events here to broadcast to all browser clients.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial confirmation message
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to Online Auction House Live Event Stream"
        })
        while True:
            # Keep socket open and accept incoming ping/pong or client subscriptions
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
