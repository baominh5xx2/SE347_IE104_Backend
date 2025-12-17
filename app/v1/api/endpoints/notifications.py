"""
Notification API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID

from ...schema.notification_schema import (
    NotificationListResponse,
    NotificationMarkReadResponse,
    NotificationUnreadCountResponse
)
from ...services.notification_service import NotificationService
from ...core.supabase import get_supabase_client
from ...core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def get_notification_service():
    """Dependency to get NotificationService instance"""
    supabase = get_supabase_client()
    return NotificationService(supabase)


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    unread_only: bool = Query(False, description="Chỉ lấy thông báo chưa đọc"),
    limit: Optional[int] = Query(50, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Lấy danh sách notifications của user hiện tại
    
    Args:
        unread_only: Chỉ lấy thông báo chưa đọc
        limit: Số lượng kết quả
        offset: Bỏ qua số lượng
        current_user: User hiện tại (từ auth)
        service: Notification service instance
        
    Returns:
        NotificationListResponse với danh sách notifications
    """
    try:
        user_id = current_user.get("user_id")
        
        result = await service.get_user_notifications(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset
        )
        
        return NotificationListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_notifications endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# IMPORTANT: Static paths MUST come before dynamic path parameters
@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Lấy số lượng thông báo chưa đọc
    
    Args:
        current_user: User hiện tại (từ auth)
        service: Notification service instance
        
    Returns:
        NotificationUnreadCountResponse với count
    """
    try:
        user_id = current_user.get("user_id")
        result = await service.get_unread_count(user_id)
        
        return NotificationUnreadCountResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_unread_count endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read-all", response_model=NotificationMarkReadResponse)
async def mark_all_notifications_as_read(
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Đánh dấu tất cả thông báo của user là đã đọc
    
    Args:
        current_user: User hiện tại (từ auth)
        service: Notification service instance
        
    Returns:
        NotificationMarkReadResponse
    """
    try:
        user_id = current_user.get("user_id")
        result = await service.mark_all_as_read(user_id)
        
        return NotificationMarkReadResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in mark_all_notifications_as_read endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Dynamic path parameters MUST come after static paths
@router.post("/{notification_id}/read", response_model=NotificationMarkReadResponse)
async def mark_notification_as_read(
    notification_id: UUID,
    service: NotificationService = Depends(get_notification_service)
):
    """
    Đánh dấu một thông báo là đã đọc
    
    Args:
        notification_id: UUID của notification
        service: Notification service instance
        
    Returns:
        NotificationMarkReadResponse
    """
    try:
        result = await service.mark_as_read(str(notification_id))
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return NotificationMarkReadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in mark_notification_as_read endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
