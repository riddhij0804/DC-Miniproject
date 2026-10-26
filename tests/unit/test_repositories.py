"""
Unit tests for UserRepository and AuctionQueryRepository using SQLite.
"""
import pytest
import os
import tempfile
from database.db import init_db
from database.seed_data import seed_database
from backend.grpc_server.repositories.user_repository import UserRepository
from backend.grpc_server.repositories.auction_query_repository import AuctionQueryRepository

@pytest.fixture(scope="module")
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    seed_database(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_user_repository_find_existing_user(temp_db):
    repo = UserRepository(db_path=temp_db)
    user = repo.find_user_by_username("buyer_eleanor")
    assert user is not None
    assert user["username"] == "buyer_eleanor"
    assert user["display_name"] == "Eleanor Vance"
    assert user["role"] == "BUYER"

def test_user_repository_find_admin_user(temp_db):
    repo = UserRepository(db_path=temp_db)
    admin = repo.find_user_by_username("admin_arthur")
    assert admin is not None
    assert admin["role"] == "ADMIN"

def test_user_repository_unknown_user(temp_db):
    repo = UserRepository(db_path=temp_db)
    user = repo.find_user_by_username("non_existent_user_123")
    assert user is None

def test_user_repository_empty_username(temp_db):
    repo = UserRepository(db_path=temp_db)
    assert repo.find_user_by_username("") is None
    assert repo.find_user_by_username("   ") is None

def test_auction_query_repository_list_all(temp_db):
    repo = AuctionQueryRepository(db_path=temp_db)
    items, total = repo.find_auctions(page=1, page_size=20)
    assert total >= 8
    assert len(items) == total

def test_auction_query_repository_filter_category(temp_db):
    repo = AuctionQueryRepository(db_path=temp_db)
    paintings, total = repo.find_auctions(category="Paintings")
    assert total > 0
    for p in paintings:
        assert p["category"].lower() == "paintings"

def test_auction_query_repository_filter_status(temp_db):
    repo = AuctionQueryRepository(db_path=temp_db)
    active, total = repo.find_auctions(status="ACTIVE")
    assert total > 0
    for a in active:
        assert a["status"] == "ACTIVE"

def test_auction_query_repository_search(temp_db):
    repo = AuctionQueryRepository(db_path=temp_db)
    items, total = repo.find_auctions(search="Corot")
    assert total >= 1
    assert "Corot" in items[0]["artist_name"] or "Corot" in items[0]["title"]

def test_auction_query_repository_find_by_id(temp_db):
    repo = AuctionQueryRepository(db_path=temp_db)
    lot = repo.find_auction_by_id("auc_001")
    assert lot is not None
    assert lot["auction_id"] == "auc_001"
    assert lot["title"] == "The Whispering Pines at Dusk"
    assert lot["min_next_bid"] > lot["highest_bid"]

def test_auction_query_repository_unknown_id(temp_db):
    repo = AuctionQueryRepository(db_path=temp_db)
    assert repo.find_auction_by_id("auc_non_existent") is None
