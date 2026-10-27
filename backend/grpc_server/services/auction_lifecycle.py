"""Server-side auction activation, expiration, and startup recovery."""
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Protocol

from backend.grpc_server.repositories.auction_query_repository import AuctionQueryRepository
from backend.grpc_server.repositories.bidding_repository import BiddingRepository

logger = logging.getLogger(__name__)


class AuctionEventPublisher(Protocol):
    def publish_auction_event(self, event_type: str, auction_id: str) -> None: ...


class AuctionLifecycleManager:
    def __init__(
        self,
        auction_repo: AuctionQueryRepository,
        bidding_repo: BiddingRepository,
        event_service: AuctionEventPublisher,
        poll_interval: float = 1.0,
    ):
        self.auction_repo = auction_repo
        self.bidding_repo = bidding_repo
        self.event_service = event_service
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def process_due_auctions(self, now: Optional[datetime] = None) -> None:
        current_time = now or datetime.now(timezone.utc)
        for auction in self.auction_repo.find_auctions_for_lifecycle():
            auction_id = auction["auction_id"]
            end_time = self.bidding_repo._parse_iso_datetime(auction["end_time"])
            if end_time is None:
                logger.warning("Skipping auction %s with an invalid end time.", auction_id)
                continue

            if current_time >= end_time:
                result = self.bidding_repo.close_auction(auction_id)
                if not result["success"]:
                    logger.error("Could not close expired auction %s: %s", auction_id, result["message"])
                elif result.get("closed_now"):
                    self.event_service.publish_auction_event("AUCTION_CLOSED", auction_id)
                continue

            if auction["status"] == "UPCOMING":
                start_time = self.bidding_repo._parse_iso_datetime(auction["start_time"])
                if start_time is None:
                    logger.warning("Skipping auction %s with an invalid start time.", auction_id)
                    continue
                if current_time >= start_time and self.bidding_repo.activate_auction_if_due(
                    auction_id, now=current_time
                ):
                    self.event_service.publish_auction_event("AUCTION_STATUS_CHANGED", auction_id)

    def recover(self) -> None:
        self.process_due_auctions()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="auction-lifecycle",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._stop_event.wait(self.poll_interval):
            try:
                self.process_due_auctions()
            except Exception:
                logger.exception("Auction lifecycle sweep failed.")
