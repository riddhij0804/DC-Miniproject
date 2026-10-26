"""
gRPC Auction Query Service Implementation (Member 1 Responsibility).
Handles catalog retrieval, search, category/status filtering, and single auction lookup.
"""
import math
import grpc
from typing import Optional, Dict, Any

from backend.grpc_server.generated import auction_service_pb2, auction_service_pb2_grpc
from backend.grpc_server.repositories.auction_query_repository import AuctionQueryRepository

def dict_to_proto_auction(d: Dict[str, Any]) -> auction_service_pb2.Auction:
    return auction_service_pb2.Auction(
        auction_id=str(d.get("auction_id", "")),
        title=str(d.get("title", "")),
        description=str(d.get("description", "")),
        category=str(d.get("category", "")),
        artist_name=str(d.get("artist_name", "")),
        image_path=str(d.get("image_path", "")),
        seller_id=str(d.get("seller_id", "")),
        seller_name=str(d.get("seller_name", "")),
        starting_price=float(d.get("starting_price", 0.0)),
        min_increment=float(d.get("min_increment", 50.0)),
        highest_bid=float(d.get("highest_bid", 0.0)),
        highest_bidder_id=str(d.get("highest_bidder_id", "") or ""),
        highest_bidder_name=str(d.get("highest_bidder_name", "") or ""),
        start_time=str(d.get("start_time", "")),
        end_time=str(d.get("end_time", "")),
        status=str(d.get("status", "UPCOMING")),
        min_next_bid=float(d.get("min_next_bid", 0.0)),
        total_bids=int(d.get("total_bids", 0))
    )

class AuctionQueryServiceServicer(auction_service_pb2_grpc.AuctionServiceServicer):
    def __init__(self, auction_repo: Optional[AuctionQueryRepository] = None):
        self.auction_repo = auction_repo or AuctionQueryRepository()

    def ListAuctions(
        self,
        request: auction_service_pb2.ListAuctionsRequest,
        context: grpc.ServicerContext
    ) -> auction_service_pb2.ListAuctionsResponse:
        page = request.page if request.page > 0 else 1
        page_size = request.page_size if request.page_size > 0 else 12

        search = request.search.strip() if request.search else None
        category = request.category.strip() if request.category else None
        status = request.status.strip() if request.status else None

        items, total_count = self.auction_repo.find_auctions(
            search=search,
            category=category,
            status=status,
            page=page,
            page_size=page_size
        )

        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        proto_auctions = [dict_to_proto_auction(item) for item in items]

        return auction_service_pb2.ListAuctionsResponse(
            auctions=proto_auctions,
            total_count=total_count,
            page=page,
            total_pages=total_pages
        )

    def GetAuction(
        self,
        request: auction_service_pb2.GetAuctionRequest,
        context: grpc.ServicerContext
    ) -> auction_service_pb2.GetAuctionResponse:
        auction_id = request.auction_id.strip() if request.auction_id else ""
        if not auction_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Auction ID cannot be empty.")
            return auction_service_pb2.GetAuctionResponse(
                found=False,
                error_message="Auction ID cannot be empty."
            )

        auction_dict = self.auction_repo.find_auction_by_id(auction_id)
        if not auction_dict:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Auction lot '{auction_id}' was not found.")
            return auction_service_pb2.GetAuctionResponse(
                found=False,
                error_message=f"Auction lot '{auction_id}' was not found."
            )

        return auction_service_pb2.GetAuctionResponse(
            found=True,
            auction=dict_to_proto_auction(auction_dict),
            error_message=""
        )

    def GetCategories(
        self,
        request: auction_service_pb2.GetCategoriesRequest,
        context: grpc.ServicerContext
    ) -> auction_service_pb2.GetCategoriesResponse:
        categories = self.auction_repo.get_distinct_categories()
        return auction_service_pb2.GetCategoriesResponse(categories=categories)
