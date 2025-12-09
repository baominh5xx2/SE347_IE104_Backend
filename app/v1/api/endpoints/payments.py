"""
Payment API Endpoints
Endpoints cho thanh toán VNPay
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from typing import Optional
from uuid import UUID

from ...schema.payment_schema import (
    PaymentCreate,
    PaymentCreateResponse,
    PaymentStatusResponse,
    PaymentListResponse,
    VNPayIPNResponse
)
from ...services.payment_service import PaymentService
from ...services.vnpay_service import VNPayService
from ...core.supabase import get_supabase_client
from ...core.dependencies import get_current_user
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def get_payment_service():
    """Dependency to get PaymentService instance"""
    supabase = get_supabase_client()
    return PaymentService(supabase)


def get_vnpay_service():
    """Dependency to get VNPayService instance"""
    return VNPayService()


@router.post("/create", response_model=PaymentCreateResponse)
async def create_payment(
    payment: PaymentCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service)
):
    """
    Tạo payment request và nhận VNPay URL
    
    Args:
        payment: Dữ liệu payment (booking_id, payment_method)
        request: FastAPI request object
        current_user: Current authenticated user
        service: PaymentService instance
        
    Returns:
        PaymentCreateResponse với payment_url để redirect
        
    Example:
        POST /api/v1/payments/create
        {
            "booking_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c",
            "payment_method": "vnpay"
        }
    """
    try:
        # Get client IP
        client_ip = request.client.host if request.client else "127.0.0.1"
        
        # Verify user owns the booking
        supabase = get_supabase_client()
        booking_result = supabase.table('bookings')\
            .select('user_id')\
            .eq('booking_id', str(payment.booking_id))\
            .execute()
        
        if not booking_result.data:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        booking_data = booking_result.data[0]
        
        # Check if booking has user_id
        if 'user_id' not in booking_data or booking_data['user_id'] is None:
            logger.error(f"Booking {payment.booking_id} does not have user_id")
            raise HTTPException(status_code=400, detail="Booking does not have user_id")
        
        # Convert to string for comparison (UUID might be different types)
        booking_user_id = str(booking_data['user_id'])
        current_user_id = str(current_user['user_id'])
        
        logger.info(f"Checking ownership: booking_user_id={booking_user_id}, current_user_id={current_user_id}")
        
        if booking_user_id != current_user_id:
            logger.warning(f"Access denied: booking user_id={booking_user_id}, current user_id={current_user_id}")
            raise HTTPException(status_code=403, detail="Access denied. You can only create payment for your own bookings.")
        
        # Prefer return_url from payload; fallback to Referer header so user quay về trang trước khi thanh toán
        client_return_url = payment.return_url or request.headers.get("referer")
        
        result = await service.create_payment(
            booking_id=str(payment.booking_id),
            payment_method=payment.payment_method,
            ip_addr=client_ip,
            client_return_url=client_return_url
        )
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return PaymentCreateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_payment endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.api_route("/vnpay/ipn", methods=["GET", "POST"])
async def vnpay_ipn(
    request: Request,
    service: PaymentService = Depends(get_payment_service)
):
    """
    VNPay IPN Callback (Instant Payment Notification)
    
    VNPay gọi endpoint này để thông báo kết quả thanh toán (server-to-server)
    VNPay có thể gửi qua POST body hoặc query params
    
    Args:
        request: FastAPI request với VNPay callback params
        service: PaymentService instance
        
    Returns:
        VNPayIPNResponse với RspCode và Message
    """
    try:
        # VNPay có thể gửi qua query params hoặc form data
        if request.query_params:
            callback_data = dict(request.query_params)
        else:
            # Try to get from form data
            form_data = await request.form()
            callback_data = dict(form_data)
        
        logger.info(f"VNPay IPN callback received: {callback_data}")
        
        # Verify and process payment
        result = await service.verify_and_complete_payment(callback_data)
        
        # Return response to VNPay
        if result['EC'] == 97:
            return {"RspCode": "97", "Message": "Invalid signature"}
        elif result['EC'] == 1:
            return {"RspCode": "01", "Message": "Order not found"}
        elif result['EC'] == 4:
            return {"RspCode": "04", "Message": "Invalid amount"}
        elif result['is_success']:
            return {"RspCode": "00", "Message": "Confirm Success"}
        else:
            return {"RspCode": "00", "Message": "Confirm Success"}  # Still confirm receipt
            
    except Exception as e:
        logger.error(f"Error in VNPay IPN: {str(e)}")
        return {"RspCode": "99", "Message": "Unknown error"}


@router.get("/vnpay/return")
async def vnpay_return(
    request: Request,
    service: PaymentService = Depends(get_payment_service),
    vnpay_service: VNPayService = Depends(get_vnpay_service)
):
    """
    VNPay Return URL Handler - FOLLOW Y CHANG CODE USER ĐƯA
    
    VNPay redirect user về URL này sau khi thanh toán
    
    Args:
        request: FastAPI request với VNPay callback params
        service: PaymentService instance
        vnpay_service: VNPayService instance
        
    Returns:
        Redirect to frontend với payment status
    """
    try:
        # Y CHANG code user: inputData = request.GET
        inputData = dict(request.query_params)
        
        # Y CHANG code user: if inputData:
        if inputData:
            # Y CHANG code user: Extract data (dùng ['key'] không dùng .get())
            # Các tham số bắt buộc từ Return URL
            order_id = inputData['vnp_TxnRef']
            amount = int(inputData['vnp_Amount']) / 100
            order_desc = inputData['vnp_OrderInfo']
            vnp_TransactionNo = inputData['vnp_TransactionNo']
            vnp_ResponseCode = inputData['vnp_ResponseCode']
            vnp_TmnCode = inputData['vnp_TmnCode']
            vnp_PayDate = inputData['vnp_PayDate']
            vnp_BankCode = inputData['vnp_BankCode']
            vnp_CardType = inputData.get('vnp_CardType', '')  # Optional
            # Tham số quan trọng: vnp_TransactionStatus (có trong Return URL)
            vnp_TransactionStatus = inputData.get('vnp_TransactionStatus', '')
            vnp_BankTranNo = inputData.get('vnp_BankTranNo', '')  # Optional
            
            # Y CHANG code user: vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY)
            verify_result = vnpay_service.verify_payment_response(inputData)
            is_valid = verify_result['is_valid']
            
            # Build redirect URL to frontend (configurable). If redirect param is present, prefer it.
            redirect_param = inputData.get("redirect")
            frontend_base_url = redirect_param or settings.FRONTEND_BASE_URL or "http://localhost:3000"
            
            # Y CHANG code user: if vnp.validate_response(...)
            if is_valid:
                # Y CHANG code user: if vnp_ResponseCode == "00"
                # Kiểm tra cả vnp_ResponseCode và vnp_TransactionStatus (theo tài liệu VNPay)
                if vnp_ResponseCode == "00" and vnp_TransactionStatus == "00":
                    # Thành công - Y CHANG code user
                    # Process payment completion
                    await service.verify_and_complete_payment(inputData)
                    redirect_url = f"{frontend_base_url}/payment/success?payment_id={order_id}&amount={amount}&order_desc={order_desc}&transaction_no={vnp_TransactionNo}&response_code={vnp_ResponseCode}&transaction_status={vnp_TransactionStatus}"
                else:
                    # Lỗi từ VNPay - Y CHANG code user
                    redirect_url = f"{frontend_base_url}/payment/failed?payment_id={order_id}&amount={amount}&order_desc={order_desc}&transaction_no={vnp_TransactionNo}&response_code={vnp_ResponseCode}&transaction_status={vnp_TransactionStatus}"
            else:
                # Sai checksum - Y CHANG code user
                redirect_url = f"{frontend_base_url}/payment/failed?payment_id={order_id}&amount={amount}&order_desc={order_desc}&transaction_no={vnp_TransactionNo}&response_code={vnp_ResponseCode}&transaction_status={vnp_TransactionStatus}&msg=Sai+checksum"
            
            return RedirectResponse(url=redirect_url, status_code=303)
        else:
            # Y CHANG code user: else (không có inputData)
            frontend_base_url = inputData.get("redirect") or settings.FRONTEND_BASE_URL or "http://localhost:3000"
            redirect_url = f"{frontend_base_url}/payment/failed?result="
            return RedirectResponse(url=redirect_url, status_code=303)
        
    except KeyError as e:
        logger.error(f"VNPay return: Missing required field {str(e)}")
        frontend_base_url = inputData.get("redirect") or settings.FRONTEND_BASE_URL or "http://localhost:3000"
        redirect_url = f"{frontend_base_url}/payment/failed?error=missing_field&field={str(e)}"
        return RedirectResponse(url=redirect_url, status_code=303)
    except Exception as e:
        logger.error(f"Error in VNPay return: {str(e)}")
        frontend_base_url = inputData.get("redirect") or settings.FRONTEND_BASE_URL or "http://localhost:3000"
        redirect_url = f"{frontend_base_url}/payment/failed?error=unknown"
        return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/my-payments", response_model=PaymentListResponse)
async def get_my_payments(
    status: Optional[str] = Query(None, description="Filter theo status (pending/completed/failed)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_user: dict = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service)
):
    """
    Get payment history của user
    
    Args:
        status: Filter theo status (pending/completed/failed)
        limit: Số lượng kết quả tối đa
        offset: Số bản ghi bỏ qua
        current_user: Current authenticated user
        service: PaymentService instance
        
    Returns:
        PaymentListResponse với danh sách payments
        
    Example:
        GET /api/v1/payments/my-payments?status=completed&limit=10
    """
    try:
        user_id = current_user["user_id"]
        
        result = await service.get_user_payments(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return PaymentListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_my_payments endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/booking/{booking_id}", response_model=PaymentStatusResponse)
async def get_payment_by_booking(
    booking_id: UUID,
    current_user: dict = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service)
):
    """
    Get payment by booking_id
    
    Args:
        booking_id: UUID của booking
        current_user: Current authenticated user
        service: PaymentService instance
        
    Returns:
        PaymentStatusResponse với thông tin payment
        
    Example:
        GET /api/v1/payments/booking/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        # Verify user owns the booking
        supabase = get_supabase_client()
        booking_result = supabase.table('bookings')\
            .select('user_id')\
            .eq('booking_id', str(booking_id))\
            .execute()
        
        if not booking_result.data:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Convert to string for comparison
        booking_user_id = str(booking_result.data[0]['user_id'])
        current_user_id = str(current_user['user_id'])
        
        if booking_user_id != current_user_id:
            if current_user.get('role') != 'admin':
                raise HTTPException(status_code=403, detail="Access denied")
        
        result = await service.get_payment_by_booking_id(str(booking_id))
        
        if result["EC"] != 0:
            raise HTTPException(status_code=404, detail=result["EM"])
        
        return PaymentStatusResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_payment_by_booking endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{payment_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: UUID,
    current_user: dict = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service)
):
    """
    Check payment status
    
    Args:
        payment_id: UUID của payment
        current_user: Current authenticated user
        service: PaymentService instance
        
    Returns:
        PaymentStatusResponse với thông tin payment
        
    Example:
        GET /api/v1/payments/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.get_payment_by_id(str(payment_id))
        
        if result["EC"] != 0:
            raise HTTPException(status_code=404, detail=result["EM"])
        
        # Verify user owns the payment's booking
        payment = result['data']
        supabase = get_supabase_client()
        booking_result = supabase.table('bookings')\
            .select('user_id')\
            .eq('booking_id', payment['booking_id'])\
            .execute()
        
        # Convert to string for comparison
        if booking_result.data:
            booking_user_id = str(booking_result.data[0]['user_id'])
            current_user_id = str(current_user['user_id'])
            if booking_user_id != current_user_id:
                # Allow admin to view any payment
                if current_user.get('role') != 'admin':
                    raise HTTPException(status_code=403, detail="Access denied")
        
        return PaymentStatusResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_payment_status endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
async def get_my_payments(
    status: Optional[str] = Query(None, description="Filter theo status (pending/completed/failed)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_user: dict = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service)
):
    """
    Get payment history của user
    
    Args:
        status: Filter theo status (pending/completed/failed)
        limit: Số lượng kết quả tối đa
        offset: Số bản ghi bỏ qua
        current_user: Current authenticated user
        service: PaymentService instance
        
    Returns:
        PaymentListResponse với danh sách payments
        
    Example:
        GET /api/v1/payments/my-payments?status=completed&limit=10
    """
    try:
        user_id = current_user["user_id"]
        
        result = await service.get_user_payments(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return PaymentListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_my_payments endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

