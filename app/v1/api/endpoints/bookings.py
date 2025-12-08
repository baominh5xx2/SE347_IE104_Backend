"""
Booking API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID

from ...schema.booking_schema import (
    BookingCreate,
    BookingUpdate,
    BookingListResponse,
    BookingDetailResponse,
    BookingCreateResponse,
    BookingUpdateResponse,
    BookingDeleteResponse
)
from ...services.booking_service import BookingService
from ...core.supabase import get_supabase_client
from ...core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def get_booking_service():
    """Dependency to get BookingService instance"""
    supabase = get_supabase_client()
    return BookingService(supabase)


@router.get("/", response_model=BookingListResponse)
async def get_bookings(
    user_id: Optional[str] = Query(None, description="Lọc theo user ID"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (pending/confirmed/cancelled/completed)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    service: BookingService = Depends(get_booking_service)
):
    """
    Lấy danh sách bookings
    
    Args:
        user_id: Lọc theo user ID
        status: Lọc theo trạng thái (pending/confirmed/cancelled/completed)
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        service: Booking service instance
        
    Returns:
        BookingListResponse với danh sách bookings
        
    Example:
        GET /api/v1/bookings?user_id=bcde5ff1-5fd7-49e0-8790-05463092d54e
        GET /api/v1/bookings?status=pending&limit=10
    """
    try:
        result = await service.get_all_bookings(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
        return BookingListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_bookings endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{booking_id}", response_model=BookingDetailResponse)
async def get_booking(
    booking_id: UUID,
    service: BookingService = Depends(get_booking_service)
):
    """
    Lấy thông tin chi tiết một booking
    
    Args:
        booking_id: UUID của booking
        service: Booking service instance
        
    Returns:
        BookingDetailResponse với thông tin chi tiết booking
        
    Example:
        GET /api/v1/bookings/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.get_booking_by_id(str(booking_id))
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        
        return BookingDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_booking endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=BookingCreateResponse, status_code=201)
async def create_booking(
    booking: BookingCreate,
    current_user: dict = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service)
):
    """
    Tạo booking mới. `total_amount` tự tính = `price * number_of_people`.
    
    - Admin: Tạo booking ngay với status "confirmed", không cần OTP
    - User thường: Tạo booking với status "pending", cần OTP (nhưng API này không gửi OTP, chỉ có Chat Agent mới gửi)
    
    Args:
        booking: Dữ liệu booking (package_id, number_of_people, contact_name, contact_phone, user_id, special_requests?)
        current_user: Current authenticated user (from JWT token)
        service: Booking service instance
    
    Returns:
        BookingCreateResponse: Kết quả tạo booking, bao gồm `total_amount` đã tính và thông tin booking
    """
    try:
        booking_data = booking.model_dump()
        
        # Check role
        user_role = current_user.get("role", "user")
        
        if user_role == "admin":
            # Admin: skip OTP, tạo booking confirmed ngay
            booking_data["status"] = "confirmed"
        else:
            # User thường qua API: tạo pending (không có OTP flow ở API)
            booking_data["status"] = "pending"
        
        result = await service.create_booking(booking_data)
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return BookingCreateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_booking endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{booking_id}", response_model=BookingUpdateResponse)
async def update_booking(
    booking_id: UUID,
    booking: BookingUpdate,
    service: BookingService = Depends(get_booking_service)
):
    """
    Cập nhật booking. Đổi `number_of_people` sẽ tự tính lại `total_amount`.
    
    Args:
        booking_id: UUID của booking cần cập nhật
        booking: Dữ liệu cập nhật (number_of_people, status, contact_name/phone, special_requests)
        service: Booking service instance
    
    Returns:
        BookingUpdateResponse: Kết quả cập nhật với thông tin booking sau khi thay đổi
    """
    try:
        update_data = booking.model_dump(exclude_unset=True)
        
        result = await service.update_booking(str(booking_id), update_data)
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return BookingUpdateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_booking endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{booking_id}", response_model=BookingDeleteResponse)
async def delete_booking(
    booking_id: UUID,
    service: BookingService = Depends(get_booking_service)
):
    """
    Xóa một booking (và hoàn trả lại số slot cho tour package)
    
    Args:
        booking_id: UUID của booking cần xóa
        service: Booking service instance
        
    Returns:
        BookingDeleteResponse với kết quả xóa
        
    Example:
        DELETE /api/v1/bookings/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.delete_booking(str(booking_id))
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return BookingDeleteResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_booking endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
