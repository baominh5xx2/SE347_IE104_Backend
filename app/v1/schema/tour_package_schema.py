"""
Tour Package Schema Definitions
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID


class TourPackageBase(BaseModel):
    """Base schema for tour package"""
    package_name: str = Field(..., min_length=1, max_length=255, description="Tên gói tour")
    destination: str = Field(..., min_length=1, max_length=255, description="Điểm đến")
    description: str = Field(..., min_length=1, description="Mô tả chi tiết")
    duration_days: int = Field(..., gt=0, description="Số ngày tour")
    price: float = Field(..., gt=0, description="Giá tour")
    available_slots: int = Field(..., ge=0, description="Số chỗ còn trống")
    departure_location: str = Field(..., min_length=1, max_length=255, description="Điểm khởi hành")
    start_date: date = Field(..., description="Ngày bắt đầu")
    end_date: date = Field(..., description="Ngày kết thúc")
    includes: List[str] = Field(..., description="Các dịch vụ bao gồm")
    excludes: Optional[List[str]] = Field(default=None, description="Các dịch vụ không bao gồm")
    itinerary: Optional[dict] = Field(default=None, description="Lịch trình theo ngày (JSONB)")
    image_url: Optional[str] = Field(default=None, max_length=500, description="URL hình ảnh")
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
    departure_location: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    includes: Optional[List[str]] = None
    excludes: Optional[List[str]] = None
    itinerary: Optional[dict] = None
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class TourPackageResponse(TourPackageBase):
    """Schema for tour package response"""
    package_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
