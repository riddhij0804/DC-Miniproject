"""
Unit tests for AuctionQueryServiceServicer (Member 1 gRPC implementation).
"""
import pytest
import os
import tempfile
import grpc

from database.seed_data import seed_database
from backend.grpc_server.repositories.auction_query_repository import AuctionQueryRepository
from backend.grpc_server.services.auction_query_service import AuctionQueryServiceServicer
from backend.grpc_server.generated import auction_service_pb2

class MockServicerContext:
    def __init__(self):
        self.code = grpc.StatusCode.OK
        self.details = ""

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details

@pytest.fixture(scope="module")
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    seed_database(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_list_auctions_retrieves_records(temp_db):
    servicer = AuctionQueryServiceServicer(auction_repo=AuctionQueryRepository(db_path=temp_db))
    context = MockServicerContext()
    req = auction_service_pb2.ListAuctionsRequest(page=1, page_size=20)
    
    resp = servicer.ListAuctions(req, context)
    assert resp.total_count >= 8
    assert len(resp.auctions) == resp.total_count
    assert resp.page == 1

def test_list_auctions_category_filter(temp_db):
    servicer = AuctionQueryServiceServicer(auction_repo=AuctionQueryRepository(db_path=temp_db))
    context = MockServicerContext()
    req = auction_service_pb2.ListAuctionsRequest(category="Sculptures")
    
    resp = servicer.ListAuctions(req, context)
    assert resp.total_count > 0
    for a in resp.auctions:
        assert a.category == "Sculptures"

def test_list_auctions_status_filter(temp_db):
    servicer = AuctionQueryServiceServicer(auction_repo=AuctionQueryRepository(db_path=temp_db))
    context = MockServicerContext()
    req = auction_service_pb2.ListAuctionsRequest(status="ACTIVE")
    
    resp = servicer.ListAuctions(req, context)
    assert resp.total_count > 0
    for a in resp.auctions:
        assert a.status == "ACTIVE"

def test_get_auction_valid_id(temp_db):
    servicer = AuctionQueryServiceServicer(auction_repo=AuctionQueryRepository(db_path=temp_db))
    context = MockServicerContext()
    req = auction_service_pb2.GetAuctionRequest(auction_id="auc_001")
    
    resp = servicer.GetAuction(req, context)
    assert resp.found is True
    assert resp.auction.auction_id == "auc_001"
    assert resp.auction.title == "The Whispering Pines at Dusk"
    assert resp.auction.starting_price == 4500.0
    assert resp.auction.highest_bid == 6750.0
    assert resp.auction.min_next_bid == 7000.0 # 6750 + 250
    assert resp.auction.total_bids == 3
    assert context.code == grpc.StatusCode.OK

def test_get_auction_unknown_id(temp_db):
    servicer = AuctionQueryServiceServicer(auction_repo=AuctionQueryRepository(db_path=temp_db))
    context = MockServicerContext()
    req = auction_service_pb2.GetAuctionRequest(auction_id="auc_invalid_999")
    
    resp = servicer.GetAuction(req, context)
    assert resp.found is False
    assert context.code == grpc.StatusCode.NOT_FOUND

def test_list_auctions_empty_results(temp_db):
    servicer = AuctionQueryServiceServicer(auction_repo=AuctionQueryRepository(db_path=temp_db))
    context = MockServicerContext()
    req = auction_service_pb2.ListAuctionsRequest(search="NoMatchingArtTermXYZ")
    
    resp = servicer.ListAuctions(req, context)
    assert resp.total_count == 0
    assert len(resp.auctions) == 0
