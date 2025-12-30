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
    contact_email: Optional[str] = Field(None, description="Email liên hệ (cho OTP)")
    special_requests: Optional[str] = Field(None, max_length=500, description="Yêu cầu đặc biệt")
    user_id: UUID = Field(..., description="ID của người dùng đặt tour")
    promotion_id: Optional[UUID] = Field(None, description="ID của mã khuyến mãi (nếu có) - dùng promotion_id HOẶC promotion_code")
    promotion_code: Optional[str] = Field(None, description="Mã khuyến mãi 8 ký tự (VD: ABC12345) - ưu tiên dùng code thay vì ID")


class BookingCreate(BookingBase):
    """Schema for creating a new booking"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "package_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c",
                "number_of_people": 3,
                "contact_name": "Nguyen Van B",
                "contact_phone": "0123456789",
                "contact_email": "user@example.com",
                "special_requests": "Phòng view đẹp",
                "user_id": "9b3d0691-eccd-4a81-9f43-383f5be344b8",
                "promotion_code": "ABC12345"
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
                "contact_email": "newemail@example.com",
                "promotion_code": "XYZ98765",
                "status": "confirmed"
            }
        }
    )
    
    number_of_people: Optional[int] = Field(None, ge=1, description="Số lượng người (total_amount sẽ tự động cập nhật)")
    contact_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Tên người liên hệ")
    contact_phone: Optional[str] = Field(None, min_length=10, max_length=20, description="Số điện thoại")
    contact_email: Optional[str] = Field(None, description="Email liên hệ")
    special_requests: Optional[str] = Field(None, max_length=500, description="Yêu cầu đặc biệt")
    promotion_id: Optional[UUID] = Field(None, description="ID mã khuyến mãi (total_amount sẽ tự động tính lại)")
    promotion_code: Optional[str] = Field(None, description="Mã khuyến mãi 8 ký tự (ưu tiên dùng code)")
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
    contact_email: Optional[str] = Field(None, description="Email liên hệ")
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


class BookingCancelRequest(BaseModel):
    """Schema for cancelling a booking"""
    reason: Optional[str] = Field(None, max_length=500, description="Lý do hủy booking")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "Có việc bận không thể đi được"
            }
        }
    )


class BookingCancelResponse(BaseModel):
    """Response schema for booking cancellation"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[BookingResponse] = None


# ============================================
# Schemas for UC-USER-03: Quản lý Tour Đã Đăng Ký
# ============================================

class TourPackageInfo(BaseModel):
    """Schema for tour package information in booking response"""
    package_id: UUID
    package_name: str = Field(..., description="Tên tour package")
    destination: str = Field(..., description="Điểm đến")
    description: Optional[str] = Field(None, description="Mô tả tour")
    duration_days: int = Field(..., description="Số ngày tour")
    start_date: Optional[str] = Field(None, description="Ngày bắt đầu")
    end_date: Optional[str] = Field(None, description="Ngày kết thúc")
    price: float = Field(..., description="Giá tour")
    image_urls: Optional[str] = Field(None, description="URLs hình ảnh (phân cách bằng |)")
    
    model_config = ConfigDict(from_attributes=True)


class MyBookingListItem(BaseModel):
    """Schema for booking item in user's booking list"""
    booking_id: UUID
    tour_name: str = Field(..., description="Tên tour")
    destination: str = Field(..., description="Điểm đến")
    start_date: Optional[str] = Field(None, description="Ngày bắt đầu tour")
    end_date: Optional[str] = Field(None, description="Ngày kết thúc tour")
    number_of_people: int = Field(..., description="Số lượng người")
    total_amount: float = Field(..., description="Tổng số tiền")
    status: str = Field(..., description="Trạng thái: pending/confirmed/cancelled/completed")
    created_at: datetime = Field(..., description="Ngày tạo booking")
    
    model_config = ConfigDict(from_attributes=True)


class MyBookingDetail(BaseModel):
    """Schema for detailed booking information"""
    booking_id: UUID
    status: str = Field(..., description="Trạng thái booking")
    number_of_people: int = Field(..., description="Số lượng người")
    total_amount: float = Field(..., description="Tổng số tiền")
    contact_name: str = Field(..., description="Tên người liên hệ")
    contact_phone: str = Field(..., description="Số điện thoại liên hệ")
    contact_email: Optional[str] = Field(None, description="Email liên hệ")
    special_requests: Optional[str] = Field(None, description="Yêu cầu đặc biệt")
    created_at: datetime = Field(..., description="Ngày tạo")
    updated_at: datetime = Field(..., description="Ngày cập nhật")
    tour_package: Optional[TourPackageInfo] = Field(None, description="Thông tin tour package")
    
    model_config = ConfigDict(from_attributes=True)


class MyBookingListResponse(BaseModel):
    """Response schema for user's booking list"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[list[MyBookingListItem]] = None
    total: Optional[int] = None


class MyBookingDetailResponse(BaseModel):
    """Response schema for user's booking detail"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[MyBookingDetail] = None


class AdminBookingListItem(BaseModel):
    """Schema for booking item in admin's booking list (includes user info)"""
    booking_id: UUID
    user_id: UUID = Field(..., description="ID của user")
    user_email: Optional[str] = Field(None, description="Email của user")
    user_full_name: Optional[str] = Field(None, description="Tên đầy đủ của user")
    tour_name: str = Field(..., description="Tên tour")
    destination: str = Field(..., description="Điểm đến")
    start_date: Optional[str] = Field(None, description="Ngày bắt đầu tour")
    number_of_people: int = Field(..., description="Số lượng người")
    total_amount: float = Field(..., description="Tổng số tiền")
    status: str = Field(..., description="Trạng thái")
    created_at: datetime = Field(..., description="Ngày tạo booking")
    
    model_config = ConfigDict(from_attributes=True)


class AdminBookingListResponse(BaseModel):
    """Response schema for admin's booking list"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[list[AdminBookingListItem]] = None
    total: Optional[int] = None


class AdminBookingDetailResponse(BaseModel):
    """Response schema for admin's booking detail"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[MyBookingDetail] = None


# ============================================
# Schemas for OTP Booking Flow
# ============================================

class BookingCreateWithOTP(BaseModel):
    """Schema for creating booking with OTP (user tự gửi user_id)"""
    package_id: UUID = Field(..., description="ID của tour package")
    number_of_people: int = Field(..., ge=1, description="Số lượng người (tối thiểu 1)")
    contact_name: str = Field(..., min_length=2, max_length=100, description="Tên người liên hệ")
    contact_phone: str = Field(..., min_length=10, max_length=20, description="Số điện thoại liên hệ")
    contact_email: str = Field(..., description="Email để nhận OTP")
    special_requests: Optional[str] = Field(None, max_length=500, description="Yêu cầu đặc biệt")
    user_id: UUID = Field(..., description="ID của người dùng đặt tour (bắt buộc)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "package_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c",
                "number_of_people": 2,
                "contact_name": "Nguyen Van A",
                "contact_phone": "0901234567",
                "contact_email": "user@example.com",
                "special_requests": "Phòng view đẹp",
                "user_id": "abfdf6b6-b58a-4cb7-9703-a7641454fd94"
            }
        }
    )


class VerifyOTPRequest(BaseModel):
    """Schema for verifying OTP"""
    booking_id: UUID = Field(..., description="ID của booking cần verify")
    otp_code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$", description="Mã OTP 6 số")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "booking_id": "123e4567-e89b-12d3-a456-426614174000",
                "otp_code": "123456"
            }
        }
    )


class AdminBookingCreate(BaseModel):
    """Schema for admin creating booking without OTP (status = pending)"""
    package_id: UUID = Field(..., description="ID của tour package")
    number_of_people: int = Field(..., ge=1, description="Số lượng người (tối thiểu 1)")
    contact_name: str = Field(..., min_length=2, max_length=100, description="Tên người liên hệ")
    contact_phone: str = Field(..., min_length=10, max_length=20, description="Số điện thoại liên hệ")
    contact_email: Optional[str] = Field(None, description="Email liên hệ (optional, không cần cho OTP)")
    special_requests: Optional[str] = Field(None, max_length=500, description="Yêu cầu đặc biệt")
    user_id: UUID = Field(..., description="ID của người dùng đặt tour (bắt buộc)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "package_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c",
                "number_of_people": 2,
                "contact_name": "Nguyen Van A",
                "contact_phone": "0901234567",
                "contact_email": "user@example.com",
                "special_requests": "Phòng view đẹp",
                "user_id": "abfdf6b6-b58a-4cb7-9703-a7641454fd94"
            }
        }
    )


class BookingOTPResponse(BaseModel):
    """Response schema for OTP booking operations"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[dict] = Field(None, description="Response data")


class ResendOTPRequest(BaseModel):
    """Schema for resending OTP"""
    booking_id: UUID = Field(..., description="ID của booking cần gửi lại OTP")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "booking_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
    )
