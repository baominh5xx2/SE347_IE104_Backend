"""
Admin User Management Endpoints
API endpoints for admin customer management
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any

from ...core.dependencies import get_current_admin
from ...services.admin_user_service import get_admin_user_service, AdminUserService
from ...schema.admin_user_schema import (
    AdminUserProfileResponse,
    AdminUserBookingsResponse,
    AdminUserStatusPatchRequest,
    AdminUserStatusResponse,
    AdminUserSummaryResponse,
    AdminUserChatHistoryResponse,
    AdminUsersListResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=AdminUsersListResponse)
async def get_all_users(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminUserService = Depends(get_admin_user_service)
):
    """
    Get all users in the database (admin only)
    
    Args:
        current_admin: Current admin user from JWT
        service: AdminUserService instance
        
    Returns:
        List of all users with last_access_time
        
    Raises:
        403: Not admin
    """
    result = service.get_all_users()
    
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    
    return result


@router.get("/{user_id}", response_model=AdminUserProfileResponse)
async def get_user_profile(
    user_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminUserService = Depends(get_admin_user_service)
):
    """
    Get user profile by ID (admin only)
    
    Args:
        user_id: User ID
        current_admin: Current admin user from JWT
        service: AdminUserService instance
        
    Returns:
        User profile data
        
    Raises:
        404: User not found
        403: Not admin
    """
    result = service.get_user_profile(user_id)
    
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    
    return result


@router.get("/{user_id}/bookings", response_model=AdminUserBookingsResponse)
async def get_user_bookings(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by booking status"),
    from_date: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    sort: str = Query("created_at_desc", description="Sort order"),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminUserService = Depends(get_admin_user_service)
):
    """
    Get user bookings with pagination and filters (admin only)
    
    Args:
        user_id: User ID
        page: Page number (>=1)
        limit: Items per page (1-100)
        status: Optional status filter (pending/confirmed/completed/cancelled)
        from_date: Optional start date filter (ISO format)
        to_date: Optional end date filter (ISO format)
        sort: Sort order (created_at_desc/start_date_desc/start_date_asc)
        current_admin: Current admin user from JWT
        service: AdminUserService instance
        
    Returns:
        Paginated list of user bookings
        
    Raises:
        403: Not admin
    """
    result = service.get_user_bookings(
        user_id=user_id,
        page=page,
        limit=limit,
        status=status,
        from_date=from_date,
        to_date=to_date,
        sort=sort
    )
    
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    
    return result


@router.patch("/{user_id}/status", response_model=AdminUserStatusResponse)
async def update_user_status(
    user_id: str,
    request: AdminUserStatusPatchRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminUserService = Depends(get_admin_user_service)
):
    """
    Update user active status (admin only)
    
    Args:
        user_id: User ID
        request: Status update request body
        current_admin: Current admin user from JWT
        service: AdminUserService instance
        
    Returns:
        Updated status
        
    Raises:
        404: User not found
        403: Not admin
    """
    admin_id = current_admin.get("user_id")
    
    result = service.set_user_active(
        user_id=user_id,
        is_active=request.is_active,
        reason=request.reason,
        admin_id=admin_id
    )
    
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    
    return result


@router.get("/{user_id}/summary", response_model=AdminUserSummaryResponse)
async def get_user_summary(
    user_id: str,
    from_date: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminUserService = Depends(get_admin_user_service)
):
    """
    Get comprehensive user summary with KPIs and recent activities (admin only)
    
    Args:
        user_id: User ID
        from_date: Optional start date for KPI filtering (ISO format)
        to_date: Optional end date for KPI filtering (ISO format)
        current_admin: Current admin user from JWT
        service: AdminUserService instance
        
    Returns:
        Complete user summary with profile, KPIs, and recent activities
        
    Raises:
        404: User not found
        403: Not admin
    """
    result = service.get_user_summary(
        user_id=user_id,
        from_date=from_date,
        to_date=to_date
    )
    
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    
    return result


@router.get("/{user_id}/chat-history", response_model=AdminUserChatHistoryResponse)
async def get_user_chat_history(
    user_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminUserService = Depends(get_admin_user_service)
):
    """
    Get user's chat history grouped by chat rooms (admin only)
    
    Args:
        user_id: User ID
        current_admin: Current admin user from JWT
        service: AdminUserService instance
        
    Returns:
        Chat history grouped by rooms with last 50 messages per room
        
    Raises:
        404: User not found
        403: Not admin
    """
    result = service.get_user_chat_history(user_id)
    
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    
    return result
