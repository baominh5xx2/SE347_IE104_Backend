"""
Review Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class ReviewBase(BaseModel):
    """Base review schema"""
    booking_id: UUID = Field(..., description="ID của booking")
    package_id: UUID = Field(..., description="ID của tour package")
    rating: int = Field(..., ge=1, le=5, description="Đánh giá từ 1-5 sao")
    comment: Optional[str] = Field(None, max_length=2000, description="Bình luận đánh giá")


class ReviewCreate(ReviewBase):
    """Schema for creating a new review"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "booking_id": "123e4567-e89b-12d3-a456-426614174000",
                "package_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c",
                "rating": 5,
                "comment": "Tour rất tuyệt vời, hướng dẫn viên nhiệt tình!"
            }
        }
    )


class ReviewUpdate(BaseModel):
    """Schema for updating review"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating": 4,
                "comment": "Cập nhật bình luận",
                "is_approved": True
            }
        }
    )
    
    rating: Optional[int] = Field(None, ge=1, le=5, description="Đánh giá từ 1-5 sao")
    comment: Optional[str] = Field(None, max_length=2000, description="Bình luận đánh giá")
    is_approved: Optional[bool] = Field(None, description="Trạng thái phê duyệt (admin only)")


class ReviewResponse(BaseModel):
    """Schema for review response"""
    review_id: UUID
    booking_id: UUID
    user_id: UUID
    package_id: UUID
    rating: int
    comment: Optional[str]
    is_approved: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class ReviewWithUserInfo(ReviewResponse):
    """Review response with user information"""
    user_full_name: Optional[str] = Field(None, description="Tên đầy đủ của user")
    user_email: Optional[str] = Field(None, description="Email của user")
    user_profile_picture: Optional[str] = Field(None, description="Ảnh đại diện của user")
    package_name: Optional[str] = Field(None, description="Tên tour package")


class ReviewWithPackageInfo(ReviewResponse):
    """Review response with package information"""
    package_name: Optional[str] = Field(None, description="Tên tour package")
    destination: Optional[str] = Field(None, description="Điểm đến")


class ReviewDetailResponse(ReviewResponse):
    """Review response with full details"""
    user_full_name: Optional[str] = Field(None, description="Tên đầy đủ của user")
    user_email: Optional[str] = Field(None, description="Email của user")
    user_profile_picture: Optional[str] = Field(None, description="Ảnh đại diện của user")
    package_name: Optional[str] = Field(None, description="Tên tour package")
    destination: Optional[str] = Field(None, description="Điểm đến")


class ReviewListResponse(BaseModel):
    """Response schema for list of reviews"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[list[ReviewWithUserInfo]] = None
    total: Optional[int] = None


class ReviewDetailResponseWrapper(BaseModel):
    """Response schema for single review detail"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[ReviewDetailResponse] = None


class ReviewCreateResponse(BaseModel):
    """Response schema for review creation"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[ReviewResponse] = None


class ReviewUpdateResponse(BaseModel):
    """Response schema for review update"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[ReviewResponse] = None


class ReviewDeleteResponse(BaseModel):
    """Response schema for review deletion"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")


class ReviewStatsResponse(BaseModel):
    """Response schema for review statistics"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[dict] = Field(None, description="Statistics data")


class ReviewApproveRequest(BaseModel):
    """Schema for approving a review"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_approved": True
            }
        }
    )
    is_approved: bool = Field(True, description="Trạng thái phê duyệt (True = approve, False = reject)")


class ReviewApproveResponse(BaseModel):
    """Response schema for review approval/rejection"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[ReviewResponse] = None
