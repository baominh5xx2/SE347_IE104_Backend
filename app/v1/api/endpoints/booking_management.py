"""
Booking Management API Endpoints
Endpoints cho UC-USER-03: Quản lý Tour Đã Đăng Ký
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID

from ...schema.booking_schema import (
    MyBookingListResponse,
    MyBookingDetailResponse,
    AdminBookingListResponse,
    AdminBookingDetailResponse
)
from ...services.booking_management_service import BookingManagementService
from ...core.supabase import get_supabase_client
from ...core.dependencies import get_current_user, get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter()


def get_booking_management_service():
    """Dependency to get BookingManagementService instance"""
    supabase = get_supabase_client()
    return BookingManagementService(supabase)


# ============================================
# User Endpoints (Đặt chỗ của tôi)
# ============================================

@router.get("/my-bookings", response_model=MyBookingListResponse)
async def get_my_bookings(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (pending/confirmed/cancelled/completed)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_user: dict = Depends(get_current_user),
    service: BookingManagementService = Depends(get_booking_management_service)
):
    """
    User: Lấy danh sách tất cả tour mà user đã đăng ký
    
    Args:
        status: Lọc theo trạng thái (pending/confirmed/cancelled/completed)
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        current_user: Current authenticated user (từ token)
        service: BookingManagementService instance
        
    Returns:
        MyBookingListResponse với danh sách bookings kèm thông tin tour
        
    Example:
        GET /api/v1/bookings/my-bookings?status=confirmed
        GET /api/v1/bookings/my-bookings?status=pending&limit=10
    """
    try:
        user_id = current_user["user_id"]
        
        result = await service.get_user_bookings(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return MyBookingListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_my_bookings endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-bookings/{booking_id}", response_model=MyBookingDetailResponse)
async def get_my_booking_detail(
    booking_id: UUID,
    current_user: dict = Depends(get_current_user),
    service: BookingManagementService = Depends(get_booking_management_service)
):
    """
    User: Lấy chi tiết 1 booking của user
    
    Args:
        booking_id: UUID của booking
        current_user: Current authenticated user (từ token)
        service: BookingManagementService instance
        
    Returns:
        MyBookingDetailResponse với thông tin chi tiết booking và tour package
        
    Example:
        GET /api/v1/bookings/my-bookings/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        user_id = current_user["user_id"]
        
        result = await service.get_user_booking_detail(
            booking_id=str(booking_id),
            user_id=user_id
        )
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])
        
        return MyBookingDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_my_booking_detail endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Admin Endpoints
# ============================================

@router.get("/admin/all", response_model=AdminBookingListResponse)
async def get_all_bookings_admin(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (pending/confirmed/cancelled/completed)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_admin: dict = Depends(get_current_admin),
    service: BookingManagementService = Depends(get_booking_management_service)
):
    """
    Admin: Lấy tất cả bookings trong hệ thống
    
    Args:
        status: Lọc theo trạng thái (pending/confirmed/cancelled/completed)
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        current_admin: Current authenticated admin (từ token)
        service: BookingManagementService instance
        
    Returns:
        AdminBookingListResponse với danh sách bookings kèm thông tin user và tour
        
    Example:
        GET /api/v1/bookings/admin/all?status=pending
        GET /api/v1/bookings/admin/all?status=confirmed&limit=20
    """
    try:
        result = await service.get_all_bookings_admin(
            status=status,
            limit=limit,
            offset=offset
        )
        
        return AdminBookingListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_all_bookings_admin endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/user/{user_id}", response_model=AdminBookingListResponse)
async def get_user_bookings_admin(
    user_id: UUID,
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (pending/confirmed/cancelled/completed)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_admin: dict = Depends(get_current_admin),
    service: BookingManagementService = Depends(get_booking_management_service)
):
    """
    Admin: Lấy tất cả bookings của 1 user cụ thể
    
    Args:
        user_id: UUID của user cần xem bookings
        status: Lọc theo trạng thái (pending/confirmed/cancelled/completed)
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        current_admin: Current authenticated admin (từ token)
        service: BookingManagementService instance
        
    Returns:
        AdminBookingListResponse với danh sách bookings của user đó
        
    Example:
        GET /api/v1/bookings/admin/user/123e4567-e89b-12d3-a456-426614174000?status=confirmed
    """
    try:
        result = await service.get_user_bookings_admin(
            user_id=str(user_id),
            status=status,
            limit=limit,
            offset=offset
        )
        
        return AdminBookingListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_user_bookings_admin endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/cancellations")
async def get_booking_cancellations_admin(
    cancelled_by: Optional[str] = Query(None, description="Filter by who cancelled (user/admin/system)"),
    limit: Optional[int] = Query(100, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(0, ge=0, description="Bỏ qua số lượng"),
    current_admin: dict = Depends(get_current_admin),
    service: BookingManagementService = Depends(get_booking_management_service)
):
    """
    Admin: Lấy danh sách tất cả booking cancellations trong hệ thống
    
    Returns:
        List of booking cancellations with tour and user info
    """
    try:
        result = await service.get_all_cancellations_admin(
            cancelled_by=cancelled_by,
            limit=limit,
            offset=offset
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_booking_cancellations_admin endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/{booking_id}", response_model=AdminBookingDetailResponse)
async def get_booking_detail_admin(
    booking_id: UUID,
    current_admin: dict = Depends(get_current_admin),
    service: BookingManagementService = Depends(get_booking_management_service)
):
    """
    Admin: Lấy chi tiết bất kỳ booking nào
    
    Args:
        booking_id: UUID của booking
        current_admin: Current authenticated admin (từ token)
        service: BookingManagementService instance
        
    Returns:
        AdminBookingDetailResponse với thông tin chi tiết booking và tour package
        
    Example:
        GET /api/v1/bookings/admin/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.get_booking_detail_admin(
            booking_id=str(booking_id)
        )
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])
        
        return AdminBookingDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_booking_detail_admin endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

