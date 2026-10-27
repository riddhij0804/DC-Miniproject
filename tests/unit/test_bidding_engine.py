"""
Unit tests for Member 2 Bidding Engine and Auction Management Repository.
Covers:
- Auction creation and seller authorization
- Bid validation, minimum increment enforcement, deadline handling
- Auction closure, winner selection, and idempotence
"""
import os
import tempfile
import pytest
from datetime import datetime, timezone, timedelta

from database.seed_data import seed_database
from database.db import get_connection
from backend.grpc_server.repositories.bidding_repository import BiddingRepository
from backend.grpc_server.repositories.auction_query_repository import AuctionQueryRepository
from backend.grpc_server.services.auction_lifecycle import AuctionLifecycleManager

@pytest.fixture
def temp_repo():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    seed_database(db_path)
    bidding_repo = BiddingRepository(db_path=db_path)
    query_repo = AuctionQueryRepository(db_path=db_path)
    yield bidding_repo, query_repo, db_path
    if os.path.exists(db_path):
        os.remove(db_path)

# ==========================================
# 1. Auction Creation Tests
# ==========================================

def test_create_auction_authorized_seller(temp_repo):
    bidding_repo, query_repo, _ = temp_repo
    res = bidding_repo.create_auction(
        title="Soleil Levant Nocturne",
        description="Exceptional impressionist landscape with gold dust glaze.",
        category="Paintings",
        artist_name="Pierre-Auguste Renoir (Circle)",
        image_path="/assets/images/artwork_003.svg",
        seller_id="usr_galerie",  # Role SELLER
        starting_price=3500.0,
        min_increment=150.0,
        duration_hours=12.0
    )
    assert res["success"] is True
    assert res["auction_id"].startswith("auc_")

    # Verify lot exists in database catalog
    lot = query_repo.find_auction_by_id(res["auction_id"])
    assert lot is not None
    assert lot["title"] == "Soleil Levant Nocturne"
    assert lot["starting_price"] == 3500.0
    assert lot["min_increment"] == 150.0
    assert lot["status"] == "ACTIVE"
    assert lot["highest_bid"] == 0.0

def test_create_auction_authorized_admin(temp_repo):
    bidding_repo, query_repo, _ = temp_repo
    res = bidding_repo.create_auction(
        title="Antique Chronograph 1928",
        description="Rare rose gold dual-register chronograph with column-wheel caliber.",
        category="Vintage",
        artist_name="Patek Philippe (Atelier)",
        image_path="/assets/images/artwork_004.svg",
        seller_id="usr_arthur",  # Role ADMIN
        starting_price=12000.0,
        min_increment=500.0
    )
    assert res["success"] is True
    assert res["auction_id"].startswith("auc_")

def test_create_auction_unauthorized_buyer(temp_repo):
    bidding_repo, _, _ = temp_repo
    res = bidding_repo.create_auction(
        title="Unauthorized Submission",
        description="A buyer attempting to act as a gallery seller.",
        category="Art",
        artist_name="Unknown",
        image_path="",
        seller_id="usr_eleanor",  # Role BUYER
        starting_price=500.0
    )
    assert res["success"] is False
    assert "Only authorized SELLERS or ADMINS" in res["error_message"]

def test_create_auction_validation_empty_fields(temp_repo):
    bidding_repo, _, _ = temp_repo
    res = bidding_repo.create_auction(
        title="",
        description="Description with no title",
        category="Art",
        artist_name="",
        image_path="",
        seller_id="usr_galerie",
        starting_price=100.0
    )
    assert res["success"] is False
    assert "title cannot be empty" in res["error_message"].lower()

def test_create_auction_invalid_dates(temp_repo):
    bidding_repo, _, _ = temp_repo
    now = datetime.now(timezone.utc)
    res = bidding_repo.create_auction(
        title="Invalid Timing Lot",
        description="End time before start time",
        category="Art",
        artist_name="Artist",
        image_path="",
        seller_id="usr_galerie",
        starting_price=100.0,
        start_time=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_time=(now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    assert res["success"] is False
    assert "end time must be after start time" in res["error_message"].lower()

# ==========================================
# 2. Bidding Engine Validation Tests
# ==========================================

def test_place_valid_bid_on_active_auction(temp_repo):
    bidding_repo, query_repo, _ = temp_repo
    # auc_001 is ACTIVE in seed data: highest_bid=6750, min_increment=250, next min=7000
    res = bidding_repo.place_bid(
        auction_id="auc_001",
        bidder_id="usr_marcus",
        bid_amount=7000.0
    )
    assert res["success"] is True
    assert res["current_highest_bid"] == 7000.0
    assert "placed successfully" in res["message"].lower()

    # Verify database state
    lot = query_repo.find_auction_by_id("auc_001")
    assert lot["highest_bid"] == 7000.0
    assert lot["highest_bidder_id"] == "usr_marcus"
    assert lot["min_next_bid"] == 7250.0
    assert lot["total_bids"] >= 1

def test_place_insufficient_bid_rejected(temp_repo):
    bidding_repo, _, _ = temp_repo
    # auc_001 requires at least 7000
    res = bidding_repo.place_bid(
        auction_id="auc_001",
        bidder_id="usr_marcus",
        bid_amount=6800.0  # Only +50 instead of required +250
    )
    assert res["success"] is False
    assert "insufficient" in res["message"].lower()
    assert res["current_highest_bid"] == 6750.0

def test_seller_cannot_bid_on_own_auction(temp_repo):
    bidding_repo, _, _ = temp_repo
    # auc_001 seller is usr_galerie
    res = bidding_repo.place_bid(
        auction_id="auc_001",
        bidder_id="usr_galerie",
        bid_amount=8000.0
    )
    assert res["success"] is False
    assert "prohibited from bidding on their own lots" in res["message"].lower()

def test_bidding_on_closed_auction_rejected(temp_repo):
    bidding_repo, _, _ = temp_repo
    # Close auction first
    bidding_repo.close_auction("auc_001")

    res = bidding_repo.place_bid(
        auction_id="auc_001",
        bidder_id="usr_marcus",
        bid_amount=10000.0
    )
    assert res["success"] is False
    assert "auction is closed" in res["message"].lower()

def test_bidding_on_unknown_auction(temp_repo):
    bidding_repo, _, _ = temp_repo
    res = bidding_repo.place_bid(
        auction_id="auc_nonexistent",
        bidder_id="usr_marcus",
        bid_amount=5000.0
    )
    assert res["success"] is False
    assert "was not found" in res["message"].lower()

def test_bidding_with_unknown_user(temp_repo):
    bidding_repo, _, _ = temp_repo
    res = bidding_repo.place_bid(
        auction_id="auc_001",
        bidder_id="usr_ghost",
        bid_amount=7500.0
    )
    assert res["success"] is False
    assert "not recognized" in res["message"].lower()

# ==========================================
# 3. Auction Closure & Winner Selection Tests
# ==========================================

def test_close_auction_with_winner(temp_repo):
    bidding_repo, query_repo, _ = temp_repo
    # Place a bid to establish winner
    bidding_repo.place_bid("auc_001", "usr_sophia", 7500.0)

    # Authorized close by seller
    res = bidding_repo.close_auction(auction_id="auc_001", user_id="usr_galerie")
    assert res["success"] is True
    assert res["status"] == "CLOSED"
    assert res["winner_id"] == "usr_sophia"
    assert res["final_price"] == 7500.0

    lot = query_repo.find_auction_by_id("auc_001")
    assert lot["status"] == "CLOSED"
    assert lot["highest_bidder_id"] == "usr_sophia"

def test_close_auction_idempotence(temp_repo):
    bidding_repo, _, _ = temp_repo
    # Close once
    res1 = bidding_repo.close_auction("auc_001")
    assert res1["success"] is True

    # Close second time
    res2 = bidding_repo.close_auction("auc_001")
    assert res2["success"] is True
    assert res1["closed_now"] is True
    assert res2["closed_now"] is False
    assert res2["status"] == "CLOSED"
    assert "already closed" in res2["message"].lower()
    assert res2["final_price"] == res1["final_price"]
    assert res2["winner_id"] == res1["winner_id"]

def test_close_auction_unauthorized_user(temp_repo):
    bidding_repo, _, _ = temp_repo
    # Regular buyer trying to close
    res = bidding_repo.close_auction(auction_id="auc_001", user_id="usr_marcus")
    assert res["success"] is False
    assert "permission denied" in res["message"].lower()

def test_get_bids_history(temp_repo):
    bidding_repo, _, _ = temp_repo
    bidding_repo.place_bid("auc_001", "usr_marcus", 7000.0)
    bidding_repo.place_bid("auc_001", "usr_sophia", 7250.0)
    bidding_repo.place_bid("auc_001", "usr_marcus", 7500.0)

    bids = bidding_repo.get_bids("auc_001", limit=10)
    assert len(bids) >= 3
    # Ordered by amount descending
    assert bids[0]["bid_amount"] == 7500.0
    assert bids[0]["bidder_name"] == "Marcus Sterling"
    assert bids[1]["bid_amount"] == 7250.0


class RecordingAuctionEvents:
    def __init__(self):
        self.events = []

    def publish_auction_event(self, event_type, auction_id):
        self.events.append((event_type, auction_id))


def test_lifecycle_recovery_persists_expired_auction_result(temp_repo):
    bidding_repo, query_repo, db_path = temp_repo
    old_deadline = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    connection = get_connection(db_path)
    try:
        connection.execute(
            "UPDATE auctions SET status = 'ACTIVE', end_time = ? WHERE auction_id = ?;",
            (old_deadline, "auc_001"),
        )
        connection.commit()
    finally:
        connection.close()

    events = RecordingAuctionEvents()
    manager = AuctionLifecycleManager(query_repo, bidding_repo, events)
    manager.recover()
    manager.recover()

    persisted = AuctionQueryRepository(db_path).find_auction_by_id("auc_001")
    assert persisted["status"] == "CLOSED"
    assert persisted["highest_bidder_id"] == "usr_eleanor"
    assert persisted["highest_bid"] == 6750.0
    assert events.events == [("AUCTION_CLOSED", "auc_001")]


def test_lifecycle_activates_upcoming_auction_without_changing_deadline(temp_repo):
    bidding_repo, query_repo, _ = temp_repo
    now = datetime.now(timezone.utc)
    start_time = (now + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    created = bidding_repo.create_auction(
        title="Scheduled Lifecycle Test",
        description="Checks server-side scheduled activation.",
        category="Art",
        artist_name="Test",
        image_path="/assets/images/artwork_001.svg",
        seller_id="usr_galerie",
        starting_price=100.0,
        start_time=start_time,
        end_time=end_time,
    )
    assert created["success"] is True

    events = RecordingAuctionEvents()
    manager = AuctionLifecycleManager(query_repo, bidding_repo, events)
    manager.process_due_auctions(now=now + timedelta(minutes=6))

    persisted = query_repo.find_auction_by_id(created["auction_id"])
    assert persisted["status"] == "ACTIVE"
    assert persisted["start_time"] == start_time
    assert persisted["end_time"] == end_time
    assert events.events == [("AUCTION_STATUS_CHANGED", created["auction_id"])]


def test_lifecycle_closes_expired_auction_without_bids(temp_repo):
    bidding_repo, query_repo, db_path = temp_repo
    created = bidding_repo.create_auction(
        title="Expired Unsold Lifecycle Test",
        description="Checks an expired auction with no bids.",
        category="Art",
        artist_name="Test",
        image_path="/assets/images/artwork_001.svg",
        seller_id="usr_galerie",
        starting_price=100.0,
        duration_hours=1.0,
    )
    assert created["success"] is True

    old_deadline = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    connection = get_connection(db_path)
    try:
        connection.execute(
            "UPDATE auctions SET status = 'ACTIVE', end_time = ? WHERE auction_id = ?;",
            (old_deadline, created["auction_id"]),
        )
        connection.commit()
    finally:
        connection.close()

    events = RecordingAuctionEvents()
    manager = AuctionLifecycleManager(query_repo, bidding_repo, events)
    manager.process_due_auctions()

    persisted = query_repo.find_auction_by_id(created["auction_id"])
    assert persisted["status"] == "CLOSED"
    assert persisted["highest_bid"] == 0.0
    assert persisted["highest_bidder_id"] == ""
    result = bidding_repo.close_auction(created["auction_id"])
    assert result["success"] is True
    assert result["winner_id"] == ""
    assert result["final_price"] == 0.0
    assert events.events == [("AUCTION_CLOSED", created["auction_id"])]
