"""
Integration tests for gRPC server + FastAPI Web Gateway + SQLite database.
Tests the complete distributed RPC round-trip for Member 1 and Member 2 features.
"""
import pytest
import os
import queue
import tempfile
import socket
import time
from concurrent import futures
import grpc
from fastapi.testclient import TestClient

from database.seed_data import seed_database
from backend.grpc_server.generated import auction_service_pb2, auction_service_pb2_grpc
from backend.grpc_server.services.user_service import UserServiceServicer
from backend.grpc_server.services.auction_query_service import AuctionQueryServiceServicer
from backend.grpc_server.repositories.user_repository import UserRepository
from backend.grpc_server.repositories.auction_query_repository import AuctionQueryRepository
from backend.grpc_server.repositories.bidding_repository import BiddingRepository
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
    bidding_repo = BiddingRepository(db_path=db_path)

    auction_service_pb2_grpc.add_UserServiceServicer_to_server(
        UserServiceServicer(user_repo=user_repo), server
    )
    auction_service_pb2_grpc.add_AuctionServiceServicer_to_server(
        AuctionQueryServiceServicer(auction_repo=auction_repo, bidding_repo=bidding_repo), server
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

# ==========================================
# Member 1 Integration Tests
# ==========================================

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

# ==========================================
# Member 2 Integration Tests: Auction Creation & Bidding Flow
# ==========================================

def test_gateway_create_auction_authorized_seller(distributed_env):
    test_client, _ = distributed_env
    payload = {
        "title": "A Venetian Sunset Study",
        "description": "Luminous oil study of the Grand Canal during twilight.",
        "category": "Paintings",
        "artist_name": "J.M.W. Turner (Follower)",
        "seller_id": "usr_galerie",
        "starting_price": 4000.0,
        "min_increment": 200.0,
        "duration_hours": 12.0
    }
    res = test_client.post("/api/auctions", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["auction_id"].startswith("auc_")
    assert "telemetry" in data
    assert data["telemetry"]["protocol"] == "gRPC Unary (Port 50051)"

    # Verify lot is immediately queryable via GET
    get_res = test_client.get(f"/api/auctions/{data['auction_id']}")
    assert get_res.status_code == 200
    lot_data = get_res.json()
    assert lot_data["title"] == "A Venetian Sunset Study"
    assert lot_data["starting_price"] == 4000.0

def test_gateway_create_auction_unauthorized_buyer(distributed_env):
    test_client, _ = distributed_env
    payload = {
        "title": "Unauthorized Artwork",
        "description": "Should fail role check",
        "category": "Art",
        "artist_name": "None",
        "seller_id": "usr_eleanor",  # BUYER
        "starting_price": 500.0
    }
    res = test_client.post("/api/auctions", json=payload)
    assert res.status_code == 400
    assert "Only authorized SELLERS or ADMINS" in res.json()["detail"]

def test_gateway_place_bid_accepted(distributed_env):
    test_client, _ = distributed_env
    # auc_001 requires at least 7000
    bid_res = test_client.post("/api/auctions/auc_001/bid", json={
        "bidder_id": "usr_marcus",
        "amount": 7250.0
    })
    assert bid_res.status_code == 200
    data = bid_res.json()
    assert data["success"] is True
    assert data["current_highest_bid"] == 7250.0
    assert data["telemetry"]["tx_status"] == "COMMITTED"
    assert "Marcus Sterling" in data["message"]

    # Verify auction state updated
    detail_res = test_client.get("/api/auctions/auc_001")
    assert detail_res.status_code == 200
    assert detail_res.json()["highest_bid"] == 7250.0
    assert detail_res.json()["highest_bidder_id"] == "usr_marcus"

def test_gateway_place_bid_insufficient_rejected(distributed_env):
    test_client, _ = distributed_env
    # Bidding below current highest bid of 7250
    bid_res = test_client.post("/api/auctions/auc_001/bid", json={
        "bidder_id": "usr_sophia",
        "amount": 7100.0
    })
    assert bid_res.status_code == 200
    data = bid_res.json()
    assert data["success"] is False
    assert "insufficient" in data["message"].lower()
    assert data["telemetry"]["tx_status"] == "REJECTED"

def test_gateway_get_auction_bids(distributed_env):
    test_client, _ = distributed_env
    res = test_client.get("/api/auctions/auc_001/bids")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["total_bids"] >= 1
    assert len(data["bids"]) >= 1
    assert data["bids"][0]["bid_amount"] >= 7250.0

def test_gateway_close_auction_and_winner(distributed_env):
    test_client, _ = distributed_env
    # Close auc_001 by seller
    close_res = test_client.post("/api/auctions/auc_001/close", json={
        "user_id": "usr_galerie"
    })
    assert close_res.status_code == 200
    data = close_res.json()
    assert data["success"] is True
    assert data["status"] == "CLOSED"
    assert data["winner_id"] == "usr_marcus"
    assert data["final_price"] == 7250.0
    assert "Auction closed successfully" in data["message"]

    # Verify that further bids are rejected
    post_close_bid = test_client.post("/api/auctions/auc_001/bid", json={
        "bidder_id": "usr_sophia",
        "amount": 8000.0
    })
    assert post_close_bid.status_code == 200
    assert post_close_bid.json()["success"] is False
    assert "closed" in post_close_bid.json()["message"].lower()

def test_bidirectional_stream_routes_persisted_bid_to_matching_subscribers(distributed_env):
    test_client, client = distributed_env

    def create_lot(title):
        response = test_client.post("/api/auctions", json={
            "title": title,
            "description": "Streaming integration test lot.",
            "category": "Art",
            "seller_id": "usr_galerie",
            "starting_price": 100.0,
            "min_increment": 10.0,
            "duration_hours": 1.0,
        })
        assert response.status_code == 201
        return response.json()["auction_id"]

    auction_id = create_lot("Streaming Test Lot")
    unrelated_auction_id = create_lot("Unrelated Streaming Lot")
    channel = grpc.insecure_channel(client.target)
    stub = auction_service_pb2_grpc.AuctionServiceStub(channel)

    def subscribe(target_auction_id):
        requests = queue.Queue()

        def request_iterator():
            while True:
                request = requests.get()
                if request is None:
                    return
                yield request

        call = stub.AuctionStream(request_iterator(), timeout=10.0)
        requests.put(auction_service_pb2.AuctionStreamRequest(
            action=auction_service_pb2.AuctionStreamRequest.SUBSCRIBE,
            auction_id=target_auction_id,
        ))
        initial_event = next(call)
        assert initial_event.event_type == "AUCTION_STATE"
        return call, requests

    first_call, first_requests = subscribe(auction_id)
    second_call, second_requests = subscribe(auction_id)
    unrelated_call, unrelated_requests = subscribe(unrelated_auction_id)

    with futures.ThreadPoolExecutor(max_workers=3) as executor:
        first_event = executor.submit(next, first_call)
        second_event = executor.submit(next, second_call)
        unrelated_event = executor.submit(next, unrelated_call)

        bid_result = client.place_bid(auction_id, "usr_marcus", 100.0)
        assert bid_result["success"] is True
        first_bid_event = first_event.result(timeout=3)
        second_bid_event = second_event.result(timeout=3)
        assert first_bid_event.event_type == "BID_ACCEPTED"
        assert first_bid_event.auction.highest_bid == 100.0
        assert second_bid_event.event_type == "BID_ACCEPTED"

        time.sleep(0.2)
        assert not unrelated_event.done()

        first_close_event = executor.submit(next, first_call)
        second_close_event = executor.submit(next, second_call)
        close_result = client.close_auction(auction_id, "usr_galerie")
        assert close_result["success"] is True
        assert first_close_event.result(timeout=3).event_type == "AUCTION_CLOSED"
        assert second_close_event.result(timeout=3).event_type == "AUCTION_CLOSED"
        assert close_result["winner_id"] == "usr_marcus"
        assert close_result["final_price"] == 100.0

        first_call.cancel()
        second_call.cancel()
        unrelated_call.cancel()
        first_requests.put(None)
        second_requests.put(None)
        unrelated_requests.put(None)

    reconnect_call, reconnect_requests = subscribe(auction_id)
    try:
        recovered_snapshot = next(reconnect_call)
        assert recovered_snapshot.event_type == "AUCTION_STATE"
        assert recovered_snapshot.auction.status == "CLOSED"
        assert recovered_snapshot.auction.highest_bid == 100.0
        assert recovered_snapshot.auction.highest_bidder_id == "usr_marcus"
    finally:
        reconnect_call.cancel()
        reconnect_requests.put(None)
    channel.close()
