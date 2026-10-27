"""
gRPC Auction Service Implementation.
Covers:
- Member 1: Catalog retrieval, search, category/status filtering, and single auction lookup.
- Member 2: Auction creation, atomic bid placement, concurrency control, auction closure, and bid history.
- Member 3: Bidirectional auction event subscriptions.
"""
import logging
import math
import queue
import grpc
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from backend.grpc_server.generated import auction_service_pb2, auction_service_pb2_grpc
from backend.grpc_server.repositories.auction_query_repository import AuctionQueryRepository
from backend.grpc_server.repositories.bidding_repository import BiddingRepository
from backend.grpc_server.services.auction_event_hub import AuctionEventHub

logger = logging.getLogger(__name__)

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
    def __init__(
        self,
        auction_repo: Optional[AuctionQueryRepository] = None,
        bidding_repo: Optional[BiddingRepository] = None,
        event_hub: Optional[AuctionEventHub] = None,
    ):
        self.auction_repo = auction_repo or AuctionQueryRepository()
        self.bidding_repo = bidding_repo or BiddingRepository()
        self.event_hub = event_hub or AuctionEventHub()

    def _auction_event(
        self,
        event_type: str,
        auction_id: str,
        message: str = "",
        bid_amount: float = 0.0,
    ) -> auction_service_pb2.AuctionStreamEvent:
        auction = self.auction_repo.find_auction_by_id(auction_id)
        if auction is None:
            return auction_service_pb2.AuctionStreamEvent(
                event_type="ERROR",
                auction_id=auction_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                message="Auction state is unavailable.",
            )

        return auction_service_pb2.AuctionStreamEvent(
            event_type=event_type,
            auction_id=auction_id,
            auction=dict_to_proto_auction(auction),
            timestamp=datetime.now(timezone.utc).isoformat(),
            message=message,
            bid_amount=bid_amount,
        )

    def publish_auction_event(
        self,
        event_type: str,
        auction_id: str,
        message: str = "",
        bid_amount: float = 0.0,
    ) -> None:
        try:
            event = self._auction_event(event_type, auction_id, message, bid_amount)
            if event.event_type == "ERROR":
                logger.error("Could not publish %s for auction %s: %s", event_type, auction_id, event.message)
                return
            self.event_hub.publish(event)
        except Exception:
            logger.exception("Could not publish %s for auction %s.", event_type, auction_id)

    # ==========================================
    # Member 1: Marketplace & Catalog RPCs
    # ==========================================

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

    def AuctionStream(self, request_iterator, context):
        """Streams auction snapshots and updates to clients subscribed by auction ID."""
        subscriber = self.event_hub.register()

        def consume_requests():
            try:
                for request in request_iterator:
                    if not context.is_active():
                        break
                    auction_id = request.auction_id.strip()
                    if not auction_id:
                        subscriber.events.put(auction_service_pb2.AuctionStreamEvent(
                            event_type="ERROR",
                            message="Auction ID is required for a stream subscription.",
                        ))
                        continue

                    if request.action == auction_service_pb2.AuctionStreamRequest.SUBSCRIBE:
                        self.event_hub.subscribe(subscriber, auction_id)
                        initial_event = self._auction_event("AUCTION_STATE", auction_id)
                        if initial_event.event_type == "ERROR":
                            self.event_hub.unsubscribe(subscriber, auction_id)
                        subscriber.events.put(initial_event)
                    elif request.action == auction_service_pb2.AuctionStreamRequest.UNSUBSCRIBE:
                        self.event_hub.unsubscribe(subscriber, auction_id)
                    else:
                        subscriber.events.put(auction_service_pb2.AuctionStreamEvent(
                            event_type="ERROR",
                            auction_id=auction_id,
                            message="Unsupported auction stream action.",
                        ))
            except Exception:
                if context.is_active():
                    logger.exception("Auction stream request processing failed.")
                    subscriber.events.put(auction_service_pb2.AuctionStreamEvent(
                        event_type="ERROR",
                        message="Auction stream request processing failed.",
                    ))

        request_thread = threading.Thread(
            target=consume_requests,
            name="auction-stream-requests",
            daemon=True,
        )
        request_thread.start()
        try:
            while context.is_active():
                try:
                    event = subscriber.events.get(timeout=0.25)
                except queue.Empty:
                    continue
                yield event
        finally:
            self.event_hub.unregister(subscriber)

    # ==========================================
    # Member 2: Bidding Engine & Auction Management
    # ==========================================

    def PlaceBid(
        self,
        request: auction_service_pb2.PlaceBidRequest,
        context: grpc.ServicerContext
    ) -> auction_service_pb2.PlaceBidResponse:
        result = self.bidding_repo.place_bid(
            auction_id=request.auction_id,
            bidder_id=request.bidder_id,
            bid_amount=request.bid_amount
        )
        auction_id = request.auction_id.strip()
        if result.get("closed_now"):
            self.publish_auction_event("AUCTION_CLOSED", auction_id)
        elif result["success"]:
            if result.get("status_changed"):
                self.publish_auction_event("AUCTION_STATUS_CHANGED", auction_id)
            self.publish_auction_event(
                "BID_ACCEPTED",
                auction_id,
                message=result["message"],
                bid_amount=float(result["current_highest_bid"]),
            )

        return auction_service_pb2.PlaceBidResponse(
            success=result["success"],
            message=result["message"],
            current_highest_bid=float(result.get("current_highest_bid", 0.0)),
            timestamp=result.get("timestamp", "")
        )

    def CreateAuction(
        self,
        request: auction_service_pb2.CreateAuctionRequest,
        context: grpc.ServicerContext
    ) -> auction_service_pb2.CreateAuctionResponse:
        result = self.bidding_repo.create_auction(
            title=request.title,
            description=request.description,
            category=request.category,
            artist_name=request.artist_name,
            image_path=request.image_path,
            seller_id=request.seller_id,
            starting_price=request.starting_price,
            min_increment=request.min_increment,
            start_time=request.start_time if request.start_time else None,
            end_time=request.end_time if request.end_time else None
        )

        return auction_service_pb2.CreateAuctionResponse(
            success=result["success"],
            auction_id=result.get("auction_id", ""),
            error_message=result.get("error_message", "")
        )

    def CloseAuction(
        self,
        request: auction_service_pb2.CloseAuctionRequest,
        context: grpc.ServicerContext
    ) -> auction_service_pb2.CloseAuctionResponse:
        result = self.bidding_repo.close_auction(
            auction_id=request.auction_id,
            user_id=request.user_id if request.user_id else None
        )
        if result.get("success") and result.get("closed_now"):
            self.publish_auction_event(
                "AUCTION_CLOSED",
                request.auction_id.strip(),
                message=result["message"],
            )

        return auction_service_pb2.CloseAuctionResponse(
            success=result["success"],
            message=result["message"],
            auction_id=result.get("auction_id", ""),
            status=result.get("status", "CLOSED"),
            winner_id=result.get("winner_id", ""),
            winner_name=result.get("winner_name", ""),
            final_price=float(result.get("final_price", 0.0)),
            total_bids=int(result.get("total_bids", 0))
        )

    def GetBids(
        self,
        request: auction_service_pb2.GetBidsRequest,
        context: grpc.ServicerContext
    ) -> auction_service_pb2.GetBidsResponse:
        records = self.bidding_repo.get_bids(
            auction_id=request.auction_id,
            limit=request.limit if request.limit > 0 else 50
        )
        proto_records = [
            auction_service_pb2.BidRecord(
                bid_id=str(r.get("bid_id", "")),
                auction_id=str(r.get("auction_id", "")),
                bidder_id=str(r.get("bidder_id", "")),
                bidder_name=str(r.get("bidder_name", "")),
                bidder_username=str(r.get("bidder_username", "")),
                bid_amount=float(r.get("bid_amount", 0.0)),
                timestamp=str(r.get("timestamp", ""))
            )
            for r in records
        ]
        return auction_service_pb2.GetBidsResponse(bids=proto_records)
