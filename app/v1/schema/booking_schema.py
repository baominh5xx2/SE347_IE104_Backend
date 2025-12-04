"""
Booking Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class BookingBase(BaseModel):
    """Base booking schema"""
    package_id: UUID = Field(..., description="ID của tour package")
    number_of_people: int = Field(..., ge=1, description="Số lượng người (tối thiểu 1)")
    contact_name: str = Field(..., min_length=2, max_length=100, description="Tên người liên hệ")
    contact_phone: str = Field(..., min_length=10, max_length=20, description="Số điện thoại liên hệ")
    special_requests: Optional[str] = Field(None, max_length=500, description="Yêu cầu đặc biệt")
    user_id: UUID = Field(..., description="ID của người dùng đặt tour")
    promotion_id: Optional[UUID] = Field(None, description="ID của mã khuyến mãi (nếu có)")


class BookingCreate(BookingBase):
    """Schema for creating a new booking"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "package_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c",
                "number_of_people": 3,
                "contact_name": "Nguyen Van B",
                "contact_phone": "0123456789",
                "special_requests": "Phòng view đẹp",
                "user_id": "9b3d0691-eccd-4a81-9f43-383f5be344b8",
                "promotion_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )

class BookingUpdate(BaseModel):
    """Schema for updating booking"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "number_of_people": 3,
                "contact_phone": "0987654321",
                "promotion_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "confirmed"
            }
        }
    )
    
    number_of_people: Optional[int] = Field(None, ge=1, description="Số lượng người (total_amount sẽ tự động cập nhật)")
    contact_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Tên người liên hệ")
    contact_phone: Optional[str] = Field(None, min_length=10, max_length=20, description="Số điện thoại")
    special_requests: Optional[str] = Field(None, max_length=500, description="Yêu cầu đặc biệt")
    promotion_id: Optional[UUID] = Field(None, description="ID mã khuyến mãi (total_amount sẽ tự động tính lại)")
    status: Optional[str] = Field(None, description="Trạng thái booking (pending/confirmed/cancelled/completed)")


class BookingResponse(BaseModel):
    """Schema for booking response"""
    booking_id: UUID
    package_id: UUID
    user_id: UUID
    number_of_people: int
    total_amount: float = Field(..., description="Tổng số tiền sau khuyến mãi")
    contact_name: str
    contact_phone: str
    special_requests: Optional[str]
    promotion_id: Optional[UUID] = Field(None, description="ID mã khuyến mãi đã áp dụng")
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class BookingListResponse(BaseModel):
    """Response schema for list of bookings"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[list[BookingResponse]] = None
    total: Optional[int] = None


class BookingDetailResponse(BaseModel):
    """Response schema for single booking detail"""    
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[BookingResponse] = None


class BookingCreateResponse(BaseModel):
    """Response schema for booking creation"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[BookingResponse] = None


class BookingUpdateResponse(BaseModel):
    """Response schema for booking update"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[BookingResponse] = None


class BookingDeleteResponse(BaseModel):
    """Response schema for booking deletion"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
