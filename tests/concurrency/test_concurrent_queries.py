"""
Concurrency tests for AuctionQueryRepository and UserRepository.
Ensures thread-safe queries under concurrent load with SQLite WAL mode.
"""
import pytest
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

from database.seed_data import seed_database
from backend.grpc_server.repositories.auction_query_repository import AuctionQueryRepository
from backend.grpc_server.repositories.user_repository import UserRepository

@pytest.fixture(scope="module")
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    seed_database(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_concurrent_auction_queries(temp_db):
    repo = AuctionQueryRepository(db_path=temp_db)
    
    def worker(worker_id):
        # Alternate queries
        if worker_id % 3 == 0:
            return repo.find_auctions(category="Paintings")
        elif worker_id % 3 == 1:
            return repo.find_auction_by_id("auc_001")
        else:
            return repo.find_auctions(status="ACTIVE")

    # Run 25 concurrent worker threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(25)]
        for f in as_completed(futures):
            res = f.result()
            assert res is not None

def test_concurrent_user_logins(temp_db):
    repo = UserRepository(db_path=temp_db)
    
    usernames = ["buyer_eleanor", "buyer_marcus", "collector_sophia", "art_lover", "admin_arthur"]
    
    def login_worker(i):
        uname = usernames[i % len(usernames)]
        return repo.find_user_by_username(uname)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(login_worker, i) for i in range(30)]
        for f in as_completed(futures):
            user = f.result()
            assert user is not None
            assert user["username"] in usernames
