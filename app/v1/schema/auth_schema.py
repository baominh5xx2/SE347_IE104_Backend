"""
Authentication Schemas
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    """Register request schema"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Nguyen Van A",
                "email": "a.nguyen@example.com",
                "password": "password123",
                "phone_number": "0123456789"
            }
        }
    )
    
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the user")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")


class LoginRequest(BaseModel):
    """Login request schema"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "a.nguyen@example.com",
                "password": "password123"
            }
        }
    )
    
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class VerifyTokenRequest(BaseModel):
    """Verify token request schema"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )
    
    token: str = Field(..., description="JWT access token")


class UserResponse(BaseModel):
    """User response schema"""
    user_id: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    is_activate: bool
    role_id: Optional[str] = None
    login_type: str
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    """Login response schema"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "EC": 0,
                "EM": "Login successful",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "user_id": "bcde5ff1-5fd7-49e0-8790-05463092d54e",
                    "email": "a.nguyen@example.com",
                    "full_name": "Nguyen Van A"
                }
            }
        }
    )
    
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    access_token: Optional[str] = None
    user: Optional[dict] = None


class RegisterResponse(BaseModel):
    """Register response schema"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "EC": 0,
                "EM": "User registered successfully",
                "user": {
                    "user_id": "bcde5ff1-5fd7-49e0-8790-05463092d54e",
                    "email": "a.nguyen@example.com",
                    "full_name": "Nguyen Van A"
                }
            }
        }
    )
    
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    user: Optional[dict] = None


class VerifyTokenResponse(BaseModel):
    """Verify token response schema"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "EC": 0,
                "EM": "Token is valid",
                "data": {
                    "email": "a.nguyen@example.com",
                    "full_name": "Nguyen Van A",
                    "exp": 1730361234
                }
            }
        }
    )
    
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[dict] = None
