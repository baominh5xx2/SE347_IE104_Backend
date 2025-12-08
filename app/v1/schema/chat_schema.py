"""
Chat Schemas
Schemas cho Chat Room Management System
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ChatRoomCreate(BaseModel):
    """Schema for creating a new chat room"""
    title: Optional[str] = Field(None, description="Tiêu đề conversation (auto-generate nếu không có)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Hỏi về tour Đà Lạt"
            }
        }
    )


class ChatMessageResponse(BaseModel):
    """Schema for chat message response"""
    message_id: UUID
    room_id: UUID
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Nội dung message")
    created_at: datetime
    message_order: int = Field(..., description="Thứ tự message trong room")
    intent: Optional[str] = None
    entities: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class ChatRoomResponse(BaseModel):
    """Schema for chat room response"""
    room_id: UUID
    user_id: UUID
    title: str = Field(..., description="Tiêu đề conversation")
    created_at: datetime
    updated_at: datetime
    is_archived: bool = Field(default=False, description="Đã archive chưa")
    message_count: Optional[int] = Field(None, description="Số lượng messages")
    last_message: Optional[str] = Field(None, description="Message cuối cùng")
    last_message_at: Optional[datetime] = Field(None, description="Thời gian message cuối")
    metadata: Optional[dict] = Field(default_factory=dict, description="Metadata bổ sung")
    
    model_config = ConfigDict(from_attributes=True)


class ChatRoomListResponse(BaseModel):
    """Response schema for chat room list"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: List[ChatRoomResponse] = Field(default_factory=list, description="Danh sách chat rooms")
    total: int = Field(..., description="Tổng số rooms")


class ChatRoomDetailResponse(BaseModel):
    """Response schema for chat room detail"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[ChatRoomResponse] = None


class ChatRoomUpdateRequest(BaseModel):
    """Schema for updating chat room"""
    title: Optional[str] = None
    is_archived: Optional[bool] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Tour Đà Lạt 2024",
                "is_archived": False
            }
        }
    )


class ChatMessagesResponse(BaseModel):
    """Response schema for chat messages list"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: List[ChatMessageResponse] = Field(default_factory=list, description="Danh sách messages")
    total: int = Field(..., description="Tổng số messages")
    limit: int = Field(..., description="Limit per page")
    offset: int = Field(..., description="Offset")


class ChatRoomCreateResponse(BaseModel):
    """Response schema for creating chat room"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[ChatRoomResponse] = None

