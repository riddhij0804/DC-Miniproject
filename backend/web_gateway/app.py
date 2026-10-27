"""
FastAPI Web Gateway for the Online Auction System.
Translates HTTP browser requests to native gRPC unary/streaming calls.
Also serves frontend static assets and exposes a WebSocket hub for live events.
"""
import asyncio
import json
import logging
import os
import queue
import sys
import threading
from typing import List, Set
import grpc
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
from backend.grpc_server.generated import auction_service_pb2

logger = logging.getLogger(__name__)

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

ws_manager = ConnectionManager()

@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    """
    Bridges each browser's subscriptions to a genuine bidirectional gRPC stream.
    """
    await ws_manager.connect(websocket)
    loop = asyncio.get_running_loop()
    outgoing = asyncio.Queue()
    incoming = queue.Queue()
    stop_event = threading.Event()
    grpc_call = []

    def grpc_requests():
        while not stop_event.is_set():
            try:
                request = incoming.get(timeout=0.25)
            except queue.Empty:
                continue
            if request is None:
                return
            yield request

    def queue_outgoing(message):
        outgoing.put_nowait(message)

    def read_grpc_events():
        try:
            if stop_event.is_set():
                return
            call = grpc_client.auction_stream(grpc_requests())
            grpc_call.append(call)
            if stop_event.is_set():
                call.cancel()
                return
            for event in call:
                loop.call_soon_threadsafe(
                    queue_outgoing,
                    grpc_client.auction_stream_event_to_dict(event),
                )
            if not stop_event.is_set():
                loop.call_soon_threadsafe(queue_outgoing, {
                    "type": "STREAM_ERROR",
                    "message": "The live auction stream ended. Reconnecting…",
                })
        except grpc.RpcError:
            if not stop_event.is_set():
                loop.call_soon_threadsafe(queue_outgoing, {
                    "type": "STREAM_ERROR",
                    "message": "Live auction updates are temporarily unavailable.",
                })
        except Exception:
            if not stop_event.is_set():
                logger.exception("WebSocket-to-gRPC auction stream failed.")
                loop.call_soon_threadsafe(queue_outgoing, {
                    "type": "STREAM_ERROR",
                    "message": "Live auction updates are temporarily unavailable.",
                })

    stream_thread = threading.Thread(
        target=read_grpc_events,
        name="gateway-auction-stream",
        daemon=True,
    )
    stream_thread.start()

    async def send_events():
        while True:
            await websocket.send_json(await outgoing.get())

    async def receive_subscriptions():
        while True:
            try:
                payload = json.loads(await websocket.receive_text())
            except json.JSONDecodeError:
                await outgoing.put({
                    "type": "ERROR",
                    "message": "Subscription message must be valid JSON.",
                })
                continue

            if not isinstance(payload, dict):
                await outgoing.put({
                    "type": "ERROR",
                    "message": "Subscription message must be a JSON object.",
                })
                continue
            action = payload.get("action")
            auction_id = payload.get("auction_id")
            if action not in ("subscribe", "unsubscribe") or not isinstance(auction_id, str) or not auction_id.strip():
                await outgoing.put({
                    "type": "ERROR",
                    "message": "Send subscribe/unsubscribe with a valid auction_id.",
                })
                continue

            incoming.put(auction_service_pb2.AuctionStreamRequest(
                action=(
                    auction_service_pb2.AuctionStreamRequest.SUBSCRIBE
                    if action == "subscribe"
                    else auction_service_pb2.AuctionStreamRequest.UNSUBSCRIBE
                ),
                auction_id=auction_id.strip(),
            ))

    tasks = [
        asyncio.create_task(send_events()),
        asyncio.create_task(receive_subscriptions()),
    ]
    try:
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            try:
                task.result()
            except WebSocketDisconnect:
                pass
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket live-event session failed.")
    finally:
        stop_event.set()
        incoming.put(None)
        if grpc_call:
            grpc_call[0].cancel()
        ws_manager.disconnect(websocket)
