"""
Authentication & User API endpoints.
Translates browser HTTP login requests to native gRPC calls.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from backend.web_gateway.grpc_client import grpc_client

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequestModel(BaseModel):
    username: str = Field(..., description="Demo username or account handle")

class LoginResponseModel(BaseModel):
    success: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    role: Optional[str] = None
    error_message: Optional[str] = None

@router.post("/login", response_model=LoginResponseModel)
async def login_endpoint(payload: LoginRequestModel):
    username = payload.username.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must not be empty."
        )

    result = grpc_client.login(username)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if result.get("status_code") == "NOT_FOUND" else status.HTTP_400_BAD_REQUEST,
            detail=result.get("error_message", "Authentication failed.")
        )

    return LoginResponseModel(
        success=True,
        user_id=result.get("user_id"),
        username=result.get("username"),
        display_name=result.get("display_name"),
        role=result.get("role")
    )

@router.get("/demo-users")
async def get_demo_users():
    """Returns curated demo users to display on the login selection screen."""
    return [
        {
            "username": "buyer_eleanor",
            "display_name": "Eleanor Vance",
            "role": "BUYER",
            "bio": "Fine art collector specializing in 19th Century French painting"
        },
        {
            "username": "buyer_marcus",
            "display_name": "Marcus Sterling",
            "role": "BUYER",
            "bio": "Private antiquity & classical bronze investor"
        },
        {
            "username": "collector_sophia",
            "display_name": "Sophia Loren",
            "role": "BUYER",
            "bio": "Connoisseur of vintage horology & avant-garde works"
        },
        {
            "username": "art_lover",
            "display_name": "Julian Croft",
            "role": "BUYER",
            "bio": "Contemporary ceramic enthusiast"
        },
        {
            "username": "admin_arthur",
            "display_name": "Arthur Pendelton (Curator)",
            "role": "ADMIN",
            "bio": "Senior Auctioneer & Gallery Administrator"
        }
    ]
