"""
gRPC User Service Implementation (Member 1 Responsibility).
Handles demo authentication, user profile lookups, and role verification.
"""
import grpc
from typing import Optional

from backend.grpc_server.generated import auction_service_pb2, auction_service_pb2_grpc
from backend.grpc_server.repositories.user_repository import UserRepository

class UserServiceServicer(auction_service_pb2_grpc.UserServiceServicer):
    def __init__(self, user_repo: Optional[UserRepository] = None):
        self.user_repo = user_repo or UserRepository()

    def Login(self, request: auction_service_pb2.LoginRequest, context: grpc.ServicerContext) -> auction_service_pb2.LoginResponse:
        username = request.username.strip() if request.username else ""
        
        if not username:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Username must not be empty.")
            return auction_service_pb2.LoginResponse(
                success=False,
                error_message="Username must not be empty."
            )

        user = self.user_repo.find_user_by_username(username)
        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"User account '{username}' was not found.")
            return auction_service_pb2.LoginResponse(
                success=False,
                error_message=f"User account '{username}' was not found. Please choose a demo user."
            )

        return auction_service_pb2.LoginResponse(
            success=True,
            error_message="",
            user_id=user["user_id"],
            username=user["username"],
            display_name=user["display_name"],
            role=user["role"]
        )

    def GetUserProfile(self, request: auction_service_pb2.UserProfileRequest, context: grpc.ServicerContext) -> auction_service_pb2.UserProfileResponse:
        user_id = request.user_id.strip() if request.user_id else ""
        if not user_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("User ID must not be empty.")
            return auction_service_pb2.UserProfileResponse(found=False)

        user = self.user_repo.find_user_by_id(user_id)
        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("User profile not found.")
            return auction_service_pb2.UserProfileResponse(found=False)

        return auction_service_pb2.UserProfileResponse(
            found=True,
            user_id=user["user_id"],
            username=user["username"],
            display_name=user["display_name"],
            role=user["role"]
        )
