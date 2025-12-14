"""
User Profile Schemas
Pydantic models for user self-service profile endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserProfile(BaseModel):
    """User profile data"""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    phone_number: Optional[str] = Field(None, description="User phone number")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Account creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "c388f154-3064-4443-8004-84631710a99a",
                "email": "user@example.com",
                "full_name": "Nguyen Van A",
                "phone_number": "0901234567",
                "profile_picture": "https://...",
                "role": "user",
                "is_active": True,
                "created_at": "2025-12-14T10:00:00",
                "updated_at": "2025-12-14T15:00:00"
            }
        }


class UserProfileResponse(BaseModel):
    """Response for get profile"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: Optional[UserProfile] = None


class UserProfileUpdateRequest(BaseModel):
    """Request for update profile (allowlist fields only)"""
    full_name: Optional[str] = Field(None, description="User full name", max_length=255)
    phone_number: Optional[str] = Field(None, description="User phone number", max_length=15)
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Nguyen Van B",
                "phone_number": "0909876543",
                "profile_picture": "https://cloudinary.com/..."
            }
        }


class UserProfileUpdateResponse(BaseModel):
    """Response for update profile"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: Optional[UserProfile] = None


class ChangePasswordRequest(BaseModel):
    """Request for changing password"""
    current_password: str = Field(..., description="Current password", min_length=6)
    new_password: str = Field(..., description="New password", min_length=6, max_length=255)

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newpassword456"
            }
        }


class ChangePasswordResponse(BaseModel):
    """Response for change password"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
