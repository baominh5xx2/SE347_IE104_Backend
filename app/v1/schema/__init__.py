"""Schema package initialization"""
# Agent schema has been removed - only auth schema remains
from .auth_schema import (
    RegisterRequest,
    LoginRequest,
    VerifyTokenRequest,
    RegisterResponse,
    LoginResponse,
    VerifyTokenResponse,
    GoogleLoginRequest,
    GoogleCallbackRequest,
    GoogleAuthURLResponse
)

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "VerifyTokenRequest",
    "RegisterResponse",
    "LoginResponse",
    "VerifyTokenResponse",
    "GoogleLoginRequest",
    "GoogleCallbackRequest",
    "GoogleAuthURLResponse"
]
