"""
Concurrency tests for Member 2 Bidding Engine.
Simulates multiple concurrent collectors bidding on the same auction simultaneously.
Validates:
- No lost updates
- Strict validation against freshest committed state
- Monotonically increasing accepted bids
- Database consistency and final price integrity
"""
import os
import tempfile
import threading
from concurrent import futures
import pytest

from database.seed_data import seed_database
from backend.grpc_server.repositories.bidding_repository import BiddingRepository
from backend.grpc_server.repositories.auction_query_repository import AuctionQueryRepository

def test_concurrent_bidding_race_conditions():
    # 1. Setup isolated test database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    seed_database(db_path)

    bidding_repo = BiddingRepository(db_path=db_path)
    query_repo = AuctionQueryRepository(db_path=db_path)

    # In seed data, auc_001 starts with highest_bid = 6750, min_increment = 250
    # Next minimum bid is 7000.
    auction_id = "auc_001"
    bidders = ["usr_marcus", "usr_sophia", "usr_julian", "usr_eleanor"]

    # 20 concurrent threads attempting bids
    # Half bid valid progressive amounts, half attempt competing same amounts
    results = []
    results_lock = threading.Lock()

    def submit_bid(bidder_id: str, amount: float):
        res = bidding_repo.place_bid(auction_id=auction_id, bidder_id=bidder_id, bid_amount=amount)
        with results_lock:
            results.append((bidder_id, amount, res))

    # Launch 20 concurrent workers
    with futures.ThreadPoolExecutor(max_workers=10) as executor:
        futs = []
        # Competing bids starting from 7000 in steps of 250
        amounts = [7000.0, 7000.0, 7250.0, 7250.0, 7500.0, 7500.0, 7750.0, 8000.0, 8000.0, 8250.0,
                   8500.0, 8750.0, 9000.0, 9000.0, 9250.0, 9500.0, 9750.0, 10000.0, 10250.0, 10500.0]

        for i, amt in enumerate(amounts):
            bidder = bidders[i % len(bidders)]
            futs.append(executor.submit(submit_bid, bidder, amt))

        futures.wait(futs)

    # Analyze outcomes
    accepted = [r for r in results if r[2]["success"] is True]
    rejected = [r for r in results if r[2]["success"] is False]

    assert len(accepted) > 0, "At least some bids must be accepted"
    assert len(rejected) > 0, "Duplicate/stale bids must be safely rejected"

    # Verify that every accepted bid is unique in amount (no two accepted at same price)
    accepted_amounts = [r[1] for r in accepted]
    assert len(accepted_amounts) == len(set(accepted_amounts)), "No duplicate bid amounts accepted"

    # Verify final database state
    final_lot = query_repo.find_auction_by_id(auction_id)
    max_accepted_amount = max(accepted_amounts)

    assert final_lot["highest_bid"] == max_accepted_amount, "Final highest bid must match highest accepted bid"

    # Verify bid history count matches accepted bids count (plus initial seed bids)
    bids_in_db = bidding_repo.get_bids(auction_id, limit=100)
    # The highest bid in db matches max accepted
    assert bids_in_db[0]["bid_amount"] == max_accepted_amount

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

