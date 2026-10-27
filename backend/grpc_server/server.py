"""
Native gRPC Server for the Online Auction System.
Hosts UserService and AuctionService on port 50051 (or GRPC_SERVER_PORT).
"""
import os
import sys
import signal
from concurrent import futures
import grpc

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db import init_db, get_db_path
from database.seed_data import seed_database
from backend.grpc_server.generated import auction_service_pb2_grpc
from backend.grpc_server.services.user_service import UserServiceServicer
from backend.grpc_server.services.auction_query_service import AuctionQueryServiceServicer
from backend.grpc_server.services.auction_lifecycle import AuctionLifecycleManager

def serve(host: str = "0.0.0.0", port: int = 50051):
    # Ensure database is initialized
    db_file = get_db_path()
    if not os.path.exists(db_file):
        print(f"[gRPC Server] Database not found at {db_file}. Initializing and seeding...")
        seed_database(db_file)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Register services
    user_servicer = UserServiceServicer()
    auction_servicer = AuctionQueryServiceServicer()
    lifecycle_manager = AuctionLifecycleManager(
        auction_repo=auction_servicer.auction_repo,
        bidding_repo=auction_servicer.bidding_repo,
        event_service=auction_servicer,
    )
    lifecycle_manager.recover()

    auction_service_pb2_grpc.add_UserServiceServicer_to_server(user_servicer, server)
    auction_service_pb2_grpc.add_AuctionServiceServicer_to_server(auction_servicer, server)

    listen_addr = f"{host}:{port}"
    server.add_insecure_port(listen_addr)
    server.start()
    lifecycle_manager.start()
    print(f"==================================================")
    print(f" [gRPC Server] Online Auction House Server Started")
    print(f" [gRPC Server] Listening on: {listen_addr}")
    print(f" [gRPC Server] Services: UserService, AuctionService")
    print(f"==================================================")

    def handle_shutdown(signum, frame):
        print("\n[gRPC Server] Stopping gracefully...")
        lifecycle_manager.stop()
        server.stop(grace=3)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(grace=0)
    finally:
        lifecycle_manager.stop()

if __name__ == "__main__":
    host = os.environ.get("GRPC_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("GRPC_SERVER_PORT", "50051"))
    serve(host=host, port=port)
