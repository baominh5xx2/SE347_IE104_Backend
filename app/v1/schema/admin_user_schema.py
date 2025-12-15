"""
Admin User Management Schemas
Pydantic models for admin customer management endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class AdminUserProfile(BaseModel):
    """User profile for admin view"""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    phone_number: Optional[str] = Field(None, description="User phone number")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Account creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    last_access_time: Optional[datetime] = Field(None, description="Last access time")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "9b3d0691-eccd-4a81-9f43-383f5be344b8",
                "email": "user@example.com",
                "full_name": "Nguyễn Văn A",
                "phone_number": "0901234567",
                "profile_picture": "https://...",
                "role": "user",
                "is_active": True,
                "created_at": "2025-12-01T10:00:00Z",
                "updated_at": "2025-12-10T15:30:00Z",
                "last_access_time": "2025-12-15T08:30:00Z"
            }
        }


class AdminUserProfileResponse(BaseModel):
    """Response for get user profile"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: AdminUserProfile


class AdminUserBookingItem(BaseModel):
    """Single booking item in admin view"""
    booking_id: str = Field(..., description="Booking ID")
    user_id: str = Field(..., description="User ID")
    package_id: str = Field(..., description="Package ID")
    package_name: str = Field(..., description="Tour package name")
    start_date: datetime = Field(..., description="Tour start date")
    end_date: datetime = Field(..., description="Tour end date")
    number_of_people: int = Field(..., description="Number of people")
    total_price: float = Field(..., description="Total price")
    currency: str = Field("VND", description="Currency")
    status: str = Field(..., description="Booking status")
    created_at: datetime = Field(..., description="Booking creation time")

    class Config:
        json_schema_extra = {
            "example": {
                "booking_id": "bk_123456",
                "user_id": "9b3d0691-eccd-4a81-9f43-383f5be344b8",
                "package_id": "pkg_001",
                "package_name": "Du lịch Đà Nẵng 3N2Đ",
                "start_date": "2026-01-10T00:00:00Z",
                "end_date": "2026-01-12T00:00:00Z",
                "number_of_people": 2,
                "total_price": 3500000,
                "currency": "VND",
                "status": "completed",
                "created_at": "2025-12-01T10:00:00Z"
            }
        }


class AdminUserBookingsData(BaseModel):
    """Paginated bookings data"""
    items: List[AdminUserBookingItem] = Field(..., description="List of bookings")
    page: int = Field(..., ge=1, description="Current page")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total items")
    total_pages: int = Field(..., ge=0, description="Total pages")


class AdminUserBookingsResponse(BaseModel):
    """Response for get user bookings"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: AdminUserBookingsData


class AdminUserStatusPatchRequest(BaseModel):
    """Request body for updating user status"""
    is_active: bool = Field(..., description="New active status")
    reason: Optional[str] = Field(None, description="Reason for status change")

    class Config:
        json_schema_extra = {
            "example": {
                "is_active": False,
                "reason": "User requested account deactivation"
            }
        }


class AdminUserStatusData(BaseModel):
    """Data for status update response"""
    user_id: str = Field(..., description="User ID")
    is_active: bool = Field(..., description="New active status")


class AdminUserStatusResponse(BaseModel):
    """Response for update user status"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: AdminUserStatusData


class AdminUserKPI(BaseModel):
    """KPI metrics for user summary"""
    total_paid_amount: float = Field(..., description="Total amount paid")
    currency: str = Field("VND", description="Currency")
    total_bookings: int = Field(..., description="Total number of bookings")
    completed_tours: int = Field(..., description="Number of completed tours")
    cancelled_bookings: int = Field(..., description="Number of cancelled bookings")
    pending_bookings: int = Field(..., description="Number of pending bookings")
    confirmed_bookings: int = Field(..., description="Number of confirmed bookings")

    class Config:
        json_schema_extra = {
            "example": {
                "total_paid_amount": 12500000,
                "currency": "VND",
                "total_bookings": 8,
                "completed_tours": 3,
                "cancelled_bookings": 1,
                "pending_bookings": 2,
                "confirmed_bookings": 2
            }
        }


class RecentBookingItem(BaseModel):
    """Recent booking for summary"""
    booking_id: str
    package_id: str
    package_name: str
    status: str
    total_price: float
    created_at: datetime


class RecentPaymentItem(BaseModel):
    """Recent payment for summary"""
    payment_id: str
    amount: float
    status: str
    paid_at: datetime


class AdminUserRecent(BaseModel):
    """Recent activities"""
    recent_bookings: List[RecentBookingItem] = Field(..., description="Recent bookings (max 10)")
    recent_payments: List[RecentPaymentItem] = Field(..., description="Recent payments (max 10)")


class AdminUserSummaryData(BaseModel):
    """Complete summary data"""
    user: AdminUserProfile
    kpi: AdminUserKPI
    recent: AdminUserRecent


class AdminUserSummaryResponse(BaseModel):
    """Response for get user summary"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: AdminUserSummaryData


# ============================================
# CHAT HISTORY SCHEMAS
# ============================================

class ChatMessage(BaseModel):
    """Single chat message"""
    message_id: str = Field(..., description="Message ID")
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    intent: Optional[str] = Field(None, description="Message intent")
    created_at: datetime = Field(..., description="Message timestamp")


class ChatRoom(BaseModel):
    """Chat room with messages"""
    room_id: str = Field(..., description="Chat room ID")
    title: Optional[str] = Field(None, description="Room title")
    created_at: datetime = Field(..., description="Room creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    message_count: int = Field(0, description="Total messages in room")
    messages: List[ChatMessage] = Field(default_factory=list, description="Recent messages (last 50)")


class AdminUserChatHistoryData(BaseModel):
    """Chat history data for admin"""
    user_id: str = Field(..., description="User ID")
    total_rooms: int = Field(0, description="Total chat rooms")
    rooms: List[ChatRoom] = Field(default_factory=list, description="Chat rooms with messages")


class AdminUserChatHistoryResponse(BaseModel):
    """Response for get user chat history"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: AdminUserChatHistoryData


# ============================================
# GET ALL USERS SCHEMAS
# ============================================

class AdminUserListItem(BaseModel):
    """Single user item in list"""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    phone_number: Optional[str] = Field(None, description="User phone number")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Account creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    last_access_time: Optional[datetime] = Field(None, description="Last access time")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "9b3d0691-eccd-4a81-9f43-383f5be344b8",
                "email": "user@example.com",
                "full_name": "Nguyễn Văn A",
                "phone_number": "0901234567",
                "profile_picture": "https://...",
                "role": "user",
                "is_active": True,
                "created_at": "2025-12-01T10:00:00Z",
                "updated_at": "2025-12-10T15:30:00Z",
                "last_access_time": "2025-12-15T08:30:00Z"
            }
        }


class AdminUsersListData(BaseModel):
    """Data for get all users"""
    users: List[AdminUserListItem] = Field(..., description="List of all users")
    total: int = Field(..., ge=0, description="Total number of users")


class AdminUsersListResponse(BaseModel):
    """Response for get all users"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: AdminUsersListData


# ============================================
# DELETE USER SCHEMAS
# ============================================

class AdminDeleteUserData(BaseModel):
    """Data for delete user response"""
    user_id: str = Field(..., description="Deleted user ID")
    email: Optional[str] = Field(None, description="Deleted user email")
    full_name: Optional[str] = Field(None, description="Deleted user full name")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "9b3d0691-eccd-4a81-9f43-383f5be344b8",
                "email": "user@example.com",
                "full_name": "Nguyễn Văn A"
            }
        }


class AdminDeleteUserResponse(BaseModel):
    """Response for delete user"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: AdminDeleteUserData


# ============================================
# CREATE USER SCHEMAS
# ============================================

class AdminCreateUserRequest(BaseModel):
    """Request body for creating a new user"""
    email: str = Field(..., description="User email (must be unique)")
    full_name: Optional[str] = Field(None, description="User full name")
    phone_number: Optional[str] = Field(None, description="User phone number")
    password: Optional[str] = Field(None, min_length=6, description="User password (optional, will generate random if not provided)")
    role: str = Field("user", description="User role (user or admin)")
    is_active: bool = Field(True, description="Account active status")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "full_name": "Nguyễn Văn B",
                "phone_number": "0901234567",
                "password": "password123",
                "role": "user",
                "is_active": True
            }
        }


class AdminCreateUserData(BaseModel):
    """Data for create user response"""
    user_id: str = Field(..., description="Created user ID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    phone_number: Optional[str] = Field(None, description="User phone number")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    password: Optional[str] = Field(None, description="Generated password (only returned if password was auto-generated)")


class AdminCreateUserResponse(BaseModel):
    """Response for create user"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: AdminCreateUserData


# ============================================
# UPDATE USER SCHEMAS
# ============================================

class AdminUpdateUserRequest(BaseModel):
    """Request body for updating user information"""
    email: Optional[str] = Field(None, description="New email (must be unique if provided)")
    full_name: Optional[str] = Field(None, description="New full name")
    phone_number: Optional[str] = Field(None, description="New phone number")
    role: Optional[str] = Field(None, description="New role (user or admin)")
    is_active: Optional[bool] = Field(None, description="New active status")
    password: Optional[str] = Field(None, min_length=6, description="New password (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "updated@example.com",
                "full_name": "Nguyễn Văn C",
                "phone_number": "0987654321",
                "role": "user",
                "is_active": True,
                "password": "newpassword123"
            }
        }


class AdminUpdateUserData(BaseModel):
    """Data for update user response"""
    user_id: str = Field(..., description="Updated user ID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    phone_number: Optional[str] = Field(None, description="User phone number")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    updated_at: Optional[datetime] = Field(None, description="Last update time")


class AdminUpdateUserResponse(BaseModel):
    """Response for update user"""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: AdminUpdateUserData
