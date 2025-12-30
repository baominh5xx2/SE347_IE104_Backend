"""
Booking API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID

from ...schema.booking_schema import (
    BookingUpdate,
    BookingListResponse,
    BookingDetailResponse,
    BookingUpdateResponse,
    BookingDeleteResponse,
    BookingCancelRequest,
    BookingCancelResponse,
    BookingCreateWithOTP,
    AdminBookingCreate,
    VerifyOTPRequest,
    BookingOTPResponse,
    ResendOTPRequest
)
from ...services.booking_service import BookingService
from ...core.supabase import get_supabase_client
from ...core.dependencies import get_current_user, get_current_admin

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


@router.post("/{booking_id}/cancel", response_model=BookingCancelResponse)
async def cancel_booking(
    booking_id: UUID,
    cancel_request: BookingCancelRequest = None,
    service: BookingService = Depends(get_booking_service)
):
    """
    Hủy một booking (soft delete - chuyển status thành 'cancelled')
    
    - Chỉ có thể hủy booking có status 'otp_sent', 'pending' hoặc 'confirmed'
    - Lưu lại lịch sử hủy vào bảng booking_cancellations
    - Hoàn trả lại số slot cho tour package
    
    Args:
        booking_id: UUID của booking cần hủy
        cancel_request: Lý do hủy (optional)
        service: Booking service instance
        
    Returns:
        BookingCancelResponse với thông tin booking sau khi hủy
        
    Example:
        POST /api/v1/bookings/123e4567-e89b-12d3-a456-426614174000/cancel
        Body: {"reason": "Có việc bận không thể đi được"}
    """
    try:
        reason = cancel_request.reason if cancel_request else None
        result = await service.cancel_booking(str(booking_id), reason=reason, cancelled_by="user")
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] == 3:
            raise HTTPException(status_code=400, detail=result["EM"])  # Already cancelled
        elif result["EC"] == 4:
            raise HTTPException(status_code=400, detail=result["EM"])  # Invalid status
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return BookingCancelResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cancel_booking endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{booking_id}", response_model=BookingDeleteResponse)
async def delete_booking(
    booking_id: UUID,
    service: BookingService = Depends(get_booking_service)
):
    """
    Xóa một booking - DEPRECATED, sử dụng POST /{booking_id}/cancel thay thế
    
    Endpoint này giờ chỉ gọi cancel_booking để soft delete.
    
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


@router.post("/create-with-otp", response_model=BookingOTPResponse, status_code=201)
async def create_booking_with_otp(
    booking: BookingCreateWithOTP,
    service: BookingService = Depends(get_booking_service)
):
    """
    Tạo booking mới với OTP verification (giống flow của chatbot).
    
    **KHÔNG YÊU CẦU AUTHENTICATION**: User tự gửi user_id trong request body.
    
    Flow:
    1. Validate package & check slots
    2. Create booking với status="otp_sent"
    3. Generate OTP (6 số)
    4. Store OTP vào database
    5. Send OTP qua email
    6. Update package slots
    7. Return booking_id và awaiting_otp=True
    
    Args:
        booking: Booking data (requires contact_email và user_id)
        service: Booking service instance
    
    Returns:
        BookingOTPResponse với booking_id và awaiting_otp flag
        
    Example:
        POST /api/v1/bookings/create-with-otp
        Body: {
            "package_id": "uuid",
            "number_of_people": 2,
            "contact_name": "Nguyen Van A",
            "contact_phone": "0901234567",
            "contact_email": "user@example.com",
            "special_requests": "Phòng view đẹp",
            "user_id": "uuid"
        }
    """
    try:
        booking_data = booking.model_dump()
        
        # Validate user_id is provided
        if not booking_data.get('user_id'):
            raise HTTPException(status_code=400, detail="user_id is required")
        
        result = await service.create_booking_with_otp(booking_data)
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return BookingOTPResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_booking_with_otp endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/create", response_model=BookingOTPResponse, status_code=201)
async def create_booking_by_admin(
    booking: AdminBookingCreate,
    current_admin: dict = Depends(get_current_admin),
    service: BookingService = Depends(get_booking_service)
):
    """
    Admin tạo booking cho khách hàng (bỏ qua OTP, status = pending)
    
    **REQUIRE ADMIN AUTHENTICATION**
    
    Flow:
    1. Validate package & check slots
    2. Create booking với status="pending" (không cần OTP)
    3. Update package slots
    4. Return booking_id với status="pending"
    
    Khác với /create-with-otp:
    - Không cần OTP verification
    - Status = "pending" ngay (thay vì "otp_sent")
    - Email là optional (không bắt buộc)
    - Yêu cầu admin authentication
    
    Args:
        booking: AdminBookingCreate với booking data
        current_admin: Admin info từ authentication
        service: Booking service instance
    
    Returns:
        BookingOTPResponse với booking_id và status="pending"
        
    Example:
        POST /api/v1/bookings/admin/create
        Authorization: Bearer <admin-token>
        Body: {
            "package_id": "uuid",
            "number_of_people": 2,
            "contact_name": "Nguyen Van A",
            "contact_phone": "0901234567",
            "contact_email": "user@example.com",  // optional
            "special_requests": "Phòng view đẹp",
            "user_id": "uuid"
        }
    """
    try:
        booking_data = booking.model_dump()
        admin_id = current_admin.get("user_id")
        
        # Validate user_id is provided
        if not booking_data.get('user_id'):
            raise HTTPException(status_code=400, detail="user_id is required")
        
        result = await service.create_booking_by_admin(booking_data, admin_id)
        
        if result["EC"] != 0:
            status_codes = {
                1: 404,  # Package not found
                2: 400,  # Package not active
                3: 400,  # Not enough slots
                4: 500,  # Failed to create
                5: 500   # Error
            }
            raise HTTPException(
                status_code=status_codes.get(result["EC"], 400),
                detail=result["EM"]
            )
        
        return BookingOTPResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_booking_by_admin endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-otp", response_model=BookingOTPResponse)
async def verify_otp(
    verify_request: VerifyOTPRequest,
    service: BookingService = Depends(get_booking_service)
):
    """
    Verify OTP code và confirm booking (giống flow của chatbot).
    
    Flow:
    1. Get OTP record từ database
    2. Validate OTP code
    3. Check expiry (5 minutes)
    4. Check attempts (max 3)
    5. Mark OTP as verified
    6. Update booking status: "otp_sent" → "pending"
    7. Return booking confirmation
    
    Args:
        verify_request: Booking ID và OTP code
        service: Booking service instance
    
    Returns:
        BookingOTPResponse với booking confirmation
        
    Example:
        POST /api/v1/bookings/verify-otp
        {
            "booking_id": "uuid",
            "otp_code": "123456"
        }
    """
    try:
        result = await service.verify_otp(
            booking_id=str(verify_request.booking_id),
            otp_code=verify_request.otp_code
        )
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return BookingOTPResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in verify_otp endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resend-otp", response_model=BookingOTPResponse)
async def resend_otp(
    resend_request: ResendOTPRequest,
    service: BookingService = Depends(get_booking_service)
):
    """
    Gửi lại OTP khi mã cũ hết hạn hoặc không nhận được.
    
    Flow:
    1. Get booking info và validate status (phải là "otp_sent")
    2. Get email từ OTP record cũ
    3. Delete OTP records cũ
    4. Generate OTP mới
    5. Store OTP mới vào database
    6. Send OTP qua email
    7. Return confirmation
    
    Args:
        resend_request: Booking ID
        service: Booking service instance
    
    Returns:
        BookingOTPResponse với confirmation
        
    Example:
        POST /api/v1/bookings/resend-otp
        {
            "booking_id": "uuid"
        }
    """
    try:
        result = await service.resend_otp(
            booking_id=str(resend_request.booking_id)
        )
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return BookingOTPResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in resend_otp endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
