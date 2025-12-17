"""
Notification Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class NotificationResponse(BaseModel):
    """Schema for notification response"""
    notification_id: UUID
    user_id: UUID
    type: str = Field(..., description="Notification type")
    title: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    is_read: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Response schema for list of notifications"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[list[NotificationResponse]] = None
    total: Optional[int] = None


class NotificationMarkReadResponse(BaseModel):
    """Response for mark as read"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")


class NotificationUnreadCountResponse(BaseModel):
    """Response for unread count"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    count: int = Field(..., description="Unread notification count")
