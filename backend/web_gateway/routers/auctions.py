"""
Auctions API endpoints.
Bridges HTTP client queries to gRPC AuctionService.
Includes:
- Member 1: List auctions, Get auction, Get categories
- Member 2: Create auction, Place bid, Close auction, Get bid history
"""
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

from backend.web_gateway.grpc_client import grpc_client

router = APIRouter(prefix="/api", tags=["auctions"])

# ==========================================
# Request Models
# ==========================================

class CreateAuctionRequestModel(BaseModel):
    title: str = Field(..., description="Title / Lot name")
    description: str = Field(..., description="Detailed catalog description & provenance")
    category: str = Field("Art", description="Art Category ('Paintings', 'Sculptures', 'Vintage', 'Collectibles', 'Art')")
    artist_name: Optional[str] = Field("Unknown Master", description="Artist or attribution")
    image_path: Optional[str] = Field("/assets/images/artwork_001.svg", description="Path to visual asset")
    seller_id: str = Field(..., description="ID or username of the seller")
    starting_price: float = Field(..., ge=0, description="Opening bid price")
    min_increment: Optional[float] = Field(50.0, gt=0, description="Minimum price advance per bid")
    start_time: Optional[str] = Field(None, description="ISO 8601 start time")
    end_time: Optional[str] = Field(None, description="ISO 8601 end time")
    duration_hours: Optional[float] = Field(24.0, description="Auction duration in hours if start/end omitted")

class PlaceBidRequestModel(BaseModel):
    bidder_id: str = Field(..., description="ID or username of bidder")
    amount: float = Field(..., gt=0, description="Bid amount")

class CloseAuctionRequestModel(BaseModel):
    user_id: Optional[str] = Field(None, description="ID or username of seller or admin executing close")

# ==========================================
# Member 1 Endpoints
# ==========================================

@router.get("/auctions")
async def list_auctions_endpoint(
    search: Optional[str] = Query(None, description="Search term in title, artist, or description"),
    category: Optional[str] = Query(None, description="Filter by art category"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, UPCOMING, CLOSED, ALL)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Items per page")
):
    result = grpc_client.list_auctions(
        search=search,
        category=category,
        status=status,
        page=page,
        page_size=page_size
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("error_message", "Unable to communicate with gRPC Auction Server.")
        )

    return result

@router.get("/auctions/{auction_id}")
async def get_auction_endpoint(auction_id: str):
    if not auction_id or not auction_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auction ID is required.")

    result = grpc_client.get_auction(auction_id.strip())
    if not result.get("found"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error_message", f"Auction '{auction_id}' was not found.")
        )

    return result.get("auction")

@router.get("/categories")
async def get_categories_endpoint():
    categories = grpc_client.get_categories()
    return {"categories": categories}

# ==========================================
# Member 2 Endpoints
# ==========================================

@router.post("/auctions", status_code=status.HTTP_201_CREATED)
async def create_auction_endpoint(payload: CreateAuctionRequestModel):
    """
    Creates a new auction lot via gRPC CreateAuction RPC.
    Enforces seller authorization and inputs validation.
    """
    start_time = payload.start_time
    end_time = payload.end_time

    if not start_time or not end_time:
        now = datetime.now(timezone.utc)
        hours = payload.duration_hours if payload.duration_hours and payload.duration_hours > 0 else 24.0
        start_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time = (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

    res = grpc_client.create_auction(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        artist_name=payload.artist_name or "Unknown Master",
        image_path=payload.image_path or "/assets/images/artwork_001.svg",
        seller_id=payload.seller_id,
        starting_price=payload.starting_price,
        min_increment=payload.min_increment or 50.0,
        start_time=start_time,
        end_time=end_time
    )

    if not res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("error_message", "Failed to create auction lot.")
        )

    return {
        "success": True,
        "auction_id": res.get("auction_id"),
        "message": f"Auction lot '{res.get('auction_id')}' created successfully.",
        "telemetry": {
            "protocol": res.get("protocol"),
            "latency_ms": res.get("latency_ms"),
            "path": "Client -> Web Gateway (:8000) -> gRPC CreateAuction (:50051) -> SQLite (WAL)"
        }
    }

@router.post("/auctions/{auction_id}/bid")
async def place_bid_endpoint(auction_id: str, payload: PlaceBidRequestModel):
    """
    Places a bid on an auction lot via gRPC PlaceBid RPC.
    Synchronizes concurrent bids and validates against fresh committed state.
    """
    if not auction_id or not auction_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auction ID cannot be empty.")

    res = grpc_client.place_bid(
        auction_id=auction_id.strip(),
        bidder_id=payload.bidder_id.strip(),
        bid_amount=payload.amount
    )

    # Return result with rich telemetry for activity panel
    return {
        "success": res.get("success", False),
        "message": res.get("message", ""),
        "current_highest_bid": res.get("current_highest_bid", 0.0),
        "timestamp": res.get("timestamp", ""),
        "telemetry": {
            "protocol": res.get("protocol", "gRPC Unary"),
            "latency_ms": res.get("latency_ms", 0.0),
            "tx_status": res.get("tx_status", "UNKNOWN"),
            "path": "Client -> Web Gateway (:8000) -> gRPC PlaceBid (:50051) -> SQLite (WAL)"
        }
    }

@router.post("/auctions/{auction_id}/close")
async def close_auction_endpoint(auction_id: str, payload: CloseAuctionRequestModel):
    """
    Closes an auction via gRPC CloseAuction RPC, recording final price and winner.
    """
    if not auction_id or not auction_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auction ID cannot be empty.")

    res = grpc_client.close_auction(
        auction_id=auction_id.strip(),
        user_id=(payload.user_id or "").strip()
    )

    if not res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("message", "Failed to close auction.")
        )

    return {
        "success": True,
        "message": res.get("message"),
        "auction_id": res.get("auction_id"),
        "status": res.get("status"),
        "winner_id": res.get("winner_id"),
        "winner_name": res.get("winner_name"),
        "final_price": res.get("final_price"),
        "total_bids": res.get("total_bids"),
        "telemetry": {
            "protocol": res.get("protocol"),
            "latency_ms": res.get("latency_ms"),
            "path": "Client -> Web Gateway (:8000) -> gRPC CloseAuction (:50051) -> SQLite (WAL)"
        }
    }

@router.get("/auctions/{auction_id}/bids")
async def get_auction_bids_endpoint(auction_id: str, limit: int = Query(50, ge=1, le=100)):
    """
    Retrieves the bid placement history for an auction lot.
    """
    if not auction_id or not auction_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auction ID cannot be empty.")

    bids = grpc_client.get_bids(auction_id.strip(), limit=limit)
    return {
        "success": True,
        "auction_id": auction_id,
        "total_bids": len(bids),
        "bids": bids
    }
