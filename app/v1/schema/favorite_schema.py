"""
Favorite Tour Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class FavoriteToggleRequest(BaseModel):
    """Schema for toggling favorite status"""
    package_id: UUID = Field(..., description="ID của tour package cần toggle favorite")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "package_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c"
            }
        }
    )


class FavoriteResponse(BaseModel):
    """Schema for favorite toggle response"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    is_favorite: bool = Field(..., description="Trạng thái favorite sau khi toggle (True = đã favorite, False = đã bỏ favorite)")


class FavoriteCheckResponse(BaseModel):
    """Schema for checking favorite status"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    is_favorite: bool = Field(..., description="Trạng thái favorite (True = đã favorite, False = chưa favorite)")


class FavoriteListResponse(BaseModel):
    """Schema for list of favorite tours"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    total: int = Field(..., description="Tổng số tours yêu thích")
    packages: List[dict] = Field(..., description="Danh sách tour packages đã favorite (sắp xếp theo created_at DESC)")

