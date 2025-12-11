"""
Tour Package Schema Definitions
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
from fastapi import UploadFile


class TourPackageBase(BaseModel):
    """Base schema for tour package"""
    package_name: str = Field(..., min_length=1, max_length=255, description="Tên gói tour")
    destination: str = Field(..., min_length=1, max_length=255, description="Điểm đến")
    description: str = Field(..., min_length=1, description="Mô tả chi tiết")
    duration_days: int = Field(..., gt=0, description="Số ngày tour")
    price: float = Field(..., gt=0, description="Giá tour")
    available_slots: int = Field(..., ge=0, description="Số chỗ còn trống")
    start_date: date = Field(..., description="Ngày bắt đầu")
    end_date: date = Field(..., description="Ngày kết thúc")
    image_urls: Optional[str] = Field(default=None, description="URL hình ảnh (phân cách bằng |)")
    cuisine: Optional[str] = Field(default=None, max_length=500, description="Ẩm thực")
    suitable_for: Optional[str] = Field(default=None, max_length=500, description="Phù hợp cho")
    is_active: bool = Field(default=True, description="Trạng thái kích hoạt")


class TourPackageCreate(TourPackageBase):
    """Schema for creating a new tour package"""
    pass


class TourPackageUpdate(BaseModel):
    """Schema for updating tour package (all fields optional)"""
    package_name: Optional[str] = Field(None, min_length=1, max_length=255)
    destination: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    duration_days: Optional[int] = Field(None, gt=0)
    price: Optional[float] = Field(None, gt=0)
    available_slots: Optional[int] = Field(None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    image_urls: Optional[str] = None
    cuisine: Optional[str] = Field(None, max_length=500)
    suitable_for: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class TourPackageResponse(TourPackageBase):
    """Schema for tour package response"""
    package_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TourPackageListResponse(BaseModel):
    """Schema for list of tour packages"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    total: int = Field(..., description="Tổng số tour packages")
    packages: List[TourPackageResponse] = Field(..., description="Danh sách tour packages")


class TourPackageDetailResponse(BaseModel):
    """Schema for single tour package detail"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    package: Optional[TourPackageResponse] = None


class TourPackageCreateResponse(BaseModel):
    """Schema for create tour package response"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    package: Optional[TourPackageResponse] = None


class TourPackageUpdateResponse(BaseModel):
    """Schema for update tour package response"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    package: Optional[TourPackageResponse] = None


class TourPackageDeleteResponse(BaseModel):
    """Schema for delete tour package response"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")


class TourPackageBulkCreateResponse(BaseModel):
    """Schema for bulk create tour packages response"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    total_processed: int = Field(..., description="Tổng số dòng được xử lý")
    successful: int = Field(..., description="Số lượng tạo thành công")
    failed: int = Field(..., description="Số lượng tạo thất bại")
    created_packages: List[TourPackageResponse] = Field(default=[], description="Danh sách packages đã tạo")
    errors: List[str] = Field(default=[], description="Danh sách lỗi")
    parsing_errors: Optional[List[str]] = Field(default=None, description="Lỗi parse CSV")
      
      
class TourPackageSearchRequest(BaseModel):
    """Schema for search tour packages request"""
    q: str = Field(..., min_length=1, description="Từ khóa tìm kiếm (ví dụ: 'Tôi muốn đi Đà Lạt')")
    max_price: Optional[float] = Field(None, ge=0, description="Giá tối đa (VND)")
    duration: Optional[int] = Field(None, ge=1, le=30, description="Số ngày tour")
    destination: Optional[str] = Field(None, description="Lọc theo điểm đến")
    limit: int = Field(10, ge=1, le=50, description="Số lượng kết quả")


class TourPackageRecommendRequest(BaseModel):
    """Schema for recommend tour packages request"""
    user_id: str = Field(..., min_length=1, description="User ID để lấy đặc điểm từ Mem0")
    k: int = Field(5, ge=1, le=10, description="Số lượng tour được recommend (1-10)")


class TourPackageSearchResponse(BaseModel):
    """Schema for search tour packages response"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    found: int = Field(..., description="Số lượng tour packages tìm thấy")
    packages: List[dict] = Field(..., description="Danh sách tour packages với scores")


# ============================================================================
# Admin Recommendation Schemas
# ============================================================================

class AdminRecommendationConfig(BaseModel):
    """Schema for admin recommendation configuration"""
    enabled: bool = Field(..., description="Admin Mode enabled (True) or AI Mode (False)")
    featured_tours: List[dict] = Field(..., description="List of featured tour packages")
    total_featured: int = Field(..., description="Total number of featured tours")


class AdminRecommendationUpdate(BaseModel):
    """Schema for updating admin recommendation settings"""
    enabled: Optional[bool] = Field(None, description="Toggle Admin/AI mode")
    tour_package_ids: Optional[List[UUID]] = Field(None, description="List of package IDs to set as featured (will unset others)")


class AdminRecommendationResponse(BaseModel):
    """Schema for admin recommendation API response"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    data: Optional[AdminRecommendationConfig] = Field(None, description="Configuration data")
