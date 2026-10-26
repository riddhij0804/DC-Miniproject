"""
Integration tests for gRPC server + FastAPI Web Gateway + SQLite database.
Tests the complete distributed RPC round-trip.
"""
import pytest
import os
import tempfile
import socket
from concurrent import futures
import grpc
from fastapi.testclient import TestClient

from database.seed_data import seed_database
from backend.grpc_server.generated import auction_service_pb2_grpc
from backend.grpc_server.services.user_service import UserServiceServicer
from backend.grpc_server.services.auction_query_service import AuctionQueryServiceServicer
from backend.grpc_server.repositories.user_repository import UserRepository
from backend.grpc_server.repositories.auction_query_repository import AuctionQueryRepository
from backend.web_gateway.grpc_client import GrpcAuctionClient
import backend.web_gateway.routers.auth as auth_router
import backend.web_gateway.routers.auctions as auctions_router
from backend.web_gateway.app import app

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

@pytest.fixture(scope="module")
def distributed_env():
    # 1. Setup temporary database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    seed_database(db_path)

    # 2. Setup gRPC server on dynamic port
    port = find_free_port()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    
    user_repo = UserRepository(db_path=db_path)
    auction_repo = AuctionQueryRepository(db_path=db_path)

    auction_service_pb2_grpc.add_UserServiceServicer_to_server(
        UserServiceServicer(user_repo=user_repo), server
    )
    auction_service_pb2_grpc.add_AuctionServiceServicer_to_server(
        AuctionQueryServiceServicer(auction_repo=auction_repo), server
    )

    server.add_insecure_port(f"127.0.0.1:{port}")
    server.start()

    # 3. Point web gateway client to test server
    client = GrpcAuctionClient(target=f"127.0.0.1:{port}")
    auth_router.grpc_client = client
    auctions_router.grpc_client = client
    import backend.web_gateway.app as app_module
    app_module.grpc_client = client

    # 4. Create FastAPI test client
    test_client = TestClient(app)

    yield test_client, client

    # Cleanup
    client.close()
    server.stop(grace=0)
    if os.path.exists(db_path):
        os.remove(db_path)

def test_gateway_health(distributed_env):
    test_client, _ = distributed_env
    res = test_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["gateway_status"] == "healthy"
    assert data["grpc_backend_connected"] is True

def test_gateway_login_success(distributed_env):
    test_client, _ = distributed_env
    res = test_client.post("/api/auth/login", json={"username": "buyer_eleanor"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["username"] == "buyer_eleanor"
    assert data["display_name"] == "Eleanor Vance"
    assert data["role"] == "BUYER"

def test_gateway_login_invalid_user(distributed_env):
    test_client, _ = distributed_env
    res = test_client.post("/api/auth/login", json={"username": "fake_intruder"})
    assert res.status_code == 404

def test_gateway_list_auctions(distributed_env):
    test_client, _ = distributed_env
    res = test_client.get("/api/auctions")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["total_count"] >= 8
    assert len(data["auctions"]) > 0

def test_gateway_filter_by_category(distributed_env):
    test_client, _ = distributed_env
    res = test_client.get("/api/auctions?category=Vintage")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    for a in data["auctions"]:
        assert a["category"] == "Vintage"

def test_gateway_get_auction_detail(distributed_env):
    test_client, _ = distributed_env
    res = test_client.get("/api/auctions/auc_001")
    assert res.status_code == 200
    data = res.json()
    assert data["auction_id"] == "auc_001"
    assert data["title"] == "The Whispering Pines at Dusk"
    assert data["highest_bid"] > 0
    assert data["min_next_bid"] > data["highest_bid"]

def test_gateway_get_unknown_auction(distributed_env):
    test_client, _ = distributed_env
    res = test_client.get("/api/auctions/auc_does_not_exist_999")
    assert res.status_code == 404

def test_gateway_serves_pages_and_assets(distributed_env):
    test_client, _ = distributed_env
    
    # 1. Login page
    login_res = test_client.get("/login")
    assert login_res.status_code == 200
    assert "Access Auction House" in login_res.text
    assert "Vermilion &amp; Co." in login_res.text

    # 2. Marketplace page
    market_res = test_client.get("/marketplace")
    assert market_res.status_code == 200
    assert "Discover Art" in market_res.text
    assert "auction-grid" in market_res.text

    # 3. Auction details page
    details_res = test_client.get("/auction/auc_001")
    assert details_res.status_code == 200
    assert "Lot Details" in details_res.text

    # 4. Root redirect
    root_res = test_client.get("/", follow_redirects=False)
    assert root_res.status_code in [302, 307]
    assert root_res.headers["location"] == "/marketplace"

    # 5. Static artwork asset
    asset_res = test_client.get("/assets/images/artwork_001.svg")
    assert asset_res.status_code == 200
    assert "<svg" in asset_res.text
