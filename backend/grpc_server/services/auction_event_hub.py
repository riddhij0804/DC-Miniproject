"""Thread-safe fan-out for auction events to subscribed gRPC streams."""
from dataclasses import dataclass, field
import queue
import threading
from typing import Set

from backend.grpc_server.generated import auction_service_pb2


@dataclass(eq=False)
class AuctionEventSubscriber:
    events: queue.Queue = field(default_factory=queue.Queue)
    auction_ids: Set[str] = field(default_factory=set)


class AuctionEventHub:
    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: Set[AuctionEventSubscriber] = set()

    def register(self) -> AuctionEventSubscriber:
        subscriber = AuctionEventSubscriber()
        with self._lock:
            self._subscribers.add(subscriber)
        return subscriber

    def unregister(self, subscriber: AuctionEventSubscriber) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)
            subscriber.auction_ids.clear()

    def subscribe(self, subscriber: AuctionEventSubscriber, auction_id: str) -> None:
        with self._lock:
            if subscriber in self._subscribers:
                subscriber.auction_ids.add(auction_id)

    def unsubscribe(self, subscriber: AuctionEventSubscriber, auction_id: str) -> None:
        with self._lock:
            subscriber.auction_ids.discard(auction_id)

    def publish(self, event: auction_service_pb2.AuctionStreamEvent) -> None:
        with self._lock:
            subscribers = [
                subscriber
                for subscriber in self._subscribers
                if event.auction_id in subscriber.auction_ids
            ]

        for subscriber in subscribers:
            subscriber.events.put(event)
