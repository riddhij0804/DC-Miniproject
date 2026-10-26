"""
Auctions API endpoints.
Bridges HTTP client queries to gRPC AuctionService.
"""
from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, List, Dict, Any

from backend.web_gateway.grpc_client import grpc_client

router = APIRouter(prefix="/api", tags=["auctions"])

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
