"""
gRPC client wrapper for the Web Gateway.
Maintains communication channel with native gRPC server and translates responses to native Python dicts.
"""
import os
import grpc
from typing import Optional, Dict, Any, List

from backend.grpc_server.generated import auction_service_pb2, auction_service_pb2_grpc

DEFAULT_GRPC_HOST = os.environ.get("GRPC_SERVER_HOST", "127.0.0.1")
DEFAULT_GRPC_PORT = os.environ.get("GRPC_SERVER_PORT", "50051")

class GrpcAuctionClient:
    def __init__(self, target: Optional[str] = None):
        self.target = target or f"{DEFAULT_GRPC_HOST}:{DEFAULT_GRPC_PORT}"
        self._channel = None
        self._user_stub = None
        self._auction_stub = None

    @property
    def channel(self) -> grpc.Channel:
        if self._channel is None:
            self._channel = grpc.insecure_channel(self.target)
        return self._channel

    @property
    def user_stub(self) -> auction_service_pb2_grpc.UserServiceStub:
        if self._user_stub is None:
            self._user_stub = auction_service_pb2_grpc.UserServiceStub(self.channel)
        return self._user_stub

    @property
    def auction_stub(self) -> auction_service_pb2_grpc.AuctionServiceStub:
        if self._auction_stub is None:
            self._auction_stub = auction_service_pb2_grpc.AuctionServiceStub(self.channel)
        return self._auction_stub

    def close(self):
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._user_stub = None
            self._auction_stub = None

    @staticmethod
    def _proto_auction_to_dict(pb_auction: auction_service_pb2.Auction) -> Dict[str, Any]:
        return {
            "auction_id": pb_auction.auction_id,
            "title": pb_auction.title,
            "description": pb_auction.description,
            "category": pb_auction.category,
            "artist_name": pb_auction.artist_name,
            "image_path": pb_auction.image_path,
            "seller_id": pb_auction.seller_id,
            "seller_name": pb_auction.seller_name,
            "starting_price": pb_auction.starting_price,
            "min_increment": pb_auction.min_increment,
            "highest_bid": pb_auction.highest_bid,
            "highest_bidder_id": pb_auction.highest_bidder_id,
            "highest_bidder_name": pb_auction.highest_bidder_name,
            "start_time": pb_auction.start_time,
            "end_time": pb_auction.end_time,
            "status": pb_auction.status,
            "min_next_bid": pb_auction.min_next_bid,
            "total_bids": pb_auction.total_bids
        }

    def login(self, username: str) -> Dict[str, Any]:
        """Calls UserService.Login over gRPC unary RPC."""
        req = auction_service_pb2.LoginRequest(username=username)
        try:
            resp = self.user_stub.Login(req, timeout=5.0)
            return {
                "success": resp.success,
                "error_message": resp.error_message,
                "user_id": resp.user_id,
                "username": resp.username,
                "display_name": resp.display_name,
                "role": resp.role
            }
        except grpc.RpcError as e:
            code = e.code()
            details = e.details()
            return {
                "success": False,
                "error_message": details or f"gRPC Error: {code.name}",
                "status_code": code.name
            }

    def list_auctions(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 12
    ) -> Dict[str, Any]:
        """Calls AuctionService.ListAuctions over gRPC unary RPC."""
        req = auction_service_pb2.ListAuctionsRequest(
            search=search or "",
            category=category or "",
            status=status or "",
            page=page,
            page_size=page_size
        )
        try:
            resp = self.auction_stub.ListAuctions(req, timeout=5.0)
            return {
                "success": True,
                "auctions": [self._proto_auction_to_dict(a) for a in resp.auctions],
                "total_count": resp.total_count,
                "page": resp.page,
                "total_pages": resp.total_pages
            }
        except grpc.RpcError as e:
            return {
                "success": False,
                "error_message": e.details() or f"gRPC Error: {e.code().name}",
                "auctions": [],
                "total_count": 0,
                "page": page,
                "total_pages": 1
            }

    def get_auction(self, auction_id: str) -> Dict[str, Any]:
        """Calls AuctionService.GetAuction over gRPC unary RPC."""
        req = auction_service_pb2.GetAuctionRequest(auction_id=auction_id)
        try:
            resp = self.auction_stub.GetAuction(req, timeout=5.0)
            if not resp.found:
                return {
                    "found": False,
                    "error_message": resp.error_message or "Auction not found"
                }
            return {
                "found": True,
                "auction": self._proto_auction_to_dict(resp.auction)
            }
        except grpc.RpcError as e:
            return {
                "found": False,
                "error_message": e.details() or f"gRPC Error: {e.code().name}",
                "grpc_code": e.code().name
            }

    def get_categories(self) -> List[str]:
        """Calls AuctionService.GetCategories over gRPC unary RPC."""
        req = auction_service_pb2.GetCategoriesRequest()
        try:
            resp = self.auction_stub.GetCategories(req, timeout=5.0)
            return list(resp.categories)
        except grpc.RpcError:
            return ["Art", "Paintings", "Sculptures", "Vintage", "Collectibles"]

    def ping(self) -> bool:
        """Verifies connection to the gRPC server."""
        try:
            resp = self.auction_stub.GetCategories(auction_service_pb2.GetCategoriesRequest(), timeout=2.0)
            return True
        except Exception:
            return False

# Global singleton client instance
grpc_client = GrpcAuctionClient()
