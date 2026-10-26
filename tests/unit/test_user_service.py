"""
Unit tests for UserServiceServicer (Member 1 gRPC implementation).
"""
import pytest
import os
import tempfile
import grpc

from database.seed_data import seed_database
from backend.grpc_server.repositories.user_repository import UserRepository
from backend.grpc_server.services.user_service import UserServiceServicer
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

def test_login_known_demo_user(temp_db):
    servicer = UserServiceServicer(user_repo=UserRepository(db_path=temp_db))
    context = MockServicerContext()
    req = auction_service_pb2.LoginRequest(username="buyer_eleanor")
    
    resp = servicer.Login(req, context)
    assert resp.success is True
    assert resp.username == "buyer_eleanor"
    assert resp.display_name == "Eleanor Vance"
    assert resp.role == "BUYER"
    assert resp.user_id == "usr_eleanor"
    assert context.code == grpc.StatusCode.OK

def test_login_admin_user_role(temp_db):
    servicer = UserServiceServicer(user_repo=UserRepository(db_path=temp_db))
    context = MockServicerContext()
    req = auction_service_pb2.LoginRequest(username="admin_arthur")
    
    resp = servicer.Login(req, context)
    assert resp.success is True
    assert resp.role == "ADMIN"
    assert resp.display_name == "Arthur Pendelton (Curator)"

def test_login_unknown_user(temp_db):
    servicer = UserServiceServicer(user_repo=UserRepository(db_path=temp_db))
    context = MockServicerContext()
    req = auction_service_pb2.LoginRequest(username="unknown_guest")
    
    resp = servicer.Login(req, context)
    assert resp.success is False
    assert "not found" in resp.error_message.lower()
    assert context.code == grpc.StatusCode.NOT_FOUND

def test_login_empty_username(temp_db):
    servicer = UserServiceServicer(user_repo=UserRepository(db_path=temp_db))
    context = MockServicerContext()
    req = auction_service_pb2.LoginRequest(username="   ")
    
    resp = servicer.Login(req, context)
    assert resp.success is False
    assert context.code == grpc.StatusCode.INVALID_ARGUMENT
