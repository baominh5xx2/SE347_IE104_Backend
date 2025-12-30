"""
Payment Schemas
Schemas cho UC Payment: Thanh toán VNPay
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class PaymentCreate(BaseModel):
    """Schema for creating a new payment"""
    booking_id: UUID = Field(..., description="ID của booking cần thanh toán")
    payment_method: str = Field(default="vnpay", description="Phương thức thanh toán (vnpay)")
    return_url: Optional[str] = Field(
        default=None,
        description="Optional: URL frontend muốn quay lại sau thanh toán. Sẽ được append vào VNPAY_RETURN_URL dưới dạng redirect param."
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "booking_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c",
                "payment_method": "vnpay"
            }
        }
    )


class PaymentResponse(BaseModel):
    """Schema for payment response"""
    payment_id: UUID
    booking_id: UUID
    amount: float = Field(..., description="Số tiền thanh toán")
    payment_method: str = Field(..., description="Phương thức thanh toán")
    payment_status: str = Field(..., description="Trạng thái: pending/completed/failed")
    transaction_id: Optional[str] = Field(None, description="Mã giao dịch từ VNPay")
    payment_url: Optional[str] = Field(None, description="URL redirect đến VNPay")
    paid_at: Optional[datetime] = Field(None, description="Thời gian thanh toán thành công")
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PaymentCreateResponse(BaseModel):
    """Response schema for payment creation"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[PaymentResponse] = None


class PaymentStatusResponse(BaseModel):
    """Response schema for payment status check"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[PaymentResponse] = None


class PaymentListItem(BaseModel):
    """Schema for payment item in list"""
    payment_id: UUID
    booking_id: UUID
    amount: float
    payment_method: str
    payment_status: str
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    # Booking info
    tour_name: Optional[str] = Field(None, description="Tên tour")
    destination: Optional[str] = Field(None, description="Điểm đến")
    
    model_config = ConfigDict(from_attributes=True)


class PaymentListResponse(BaseModel):
    """Response schema for payment list"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[list[PaymentListItem]] = None
    total: Optional[int] = None


class VNPayCallbackData(BaseModel):
    """Schema for VNPay callback data"""
    vnp_TmnCode: Optional[str] = None
    vnp_Amount: Optional[str] = None
    vnp_BankCode: Optional[str] = None
    vnp_BankTranNo: Optional[str] = None
    vnp_CardType: Optional[str] = None
    vnp_PayDate: Optional[str] = None
    vnp_OrderInfo: Optional[str] = None
    vnp_TransactionNo: Optional[str] = None
    vnp_ResponseCode: Optional[str] = None
    vnp_TransactionStatus: Optional[str] = None
    vnp_TxnRef: Optional[str] = None  # payment_id
    vnp_SecureHash: Optional[str] = None
    vnp_SecureHashType: Optional[str] = None
    
    model_config = ConfigDict(extra="allow")


class VNPayIPNResponse(BaseModel):
    """Response schema for VNPay IPN"""
    RspCode: str = Field(..., description="Response code: 00=success, 97=invalid signature, etc.")
    Message: str = Field(..., description="Response message")


# ================== ADMIN PAYMENT SCHEMAS ==================

class AdminPaymentCreate(BaseModel):
    """Schema for admin manual payment creation"""
    booking_id: UUID = Field(..., description="ID của booking cần tạo payment")
    payment_method: str = Field(default="bank_transfer", description="Phương thức thanh toán (bank_transfer, momo, vnpay, zalopay)")
    transaction_id: Optional[str] = Field(None, description="Mã giao dịch (nếu có)")
    notes: Optional[str] = Field(None, description="Ghi chú của admin")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "booking_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c",
                "payment_method": "bank_transfer",
                "transaction_id": "BANK123456",
                "notes": "Khách chuyển khoản ngân hàng"
            }
        }
    )


class AdminConfirmCashPayment(BaseModel):
    """Schema for admin confirming cash payment"""
    booking_id: UUID = Field(..., description="ID của booking cần xác nhận thanh toán tiền mặt")
    notes: Optional[str] = Field(None, description="Ghi chú của admin (optional)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "booking_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c",
                "notes": "Khách thanh toán tiền mặt tại quầy"
            }
        }
    )


class AdminPaymentRefund(BaseModel):
    """Schema for admin payment refund"""
    refund_reason: str = Field(..., description="Lý do hoàn tiền")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refund_reason": "Khách yêu cầu hủy do có việc đột xuất"
            }
        }
    )


class AdminPaymentResponse(PaymentResponse):
    """Extended payment response with admin tracking info"""
    created_by_admin_id: Optional[str] = Field(None, description="Admin ID đã tạo payment thủ công")
    refunded_by: Optional[str] = Field(None, description="Admin ID đã hoàn tiền")
    refunded_at: Optional[datetime] = Field(None, description="Thời gian hoàn tiền")
    refund_amount: Optional[float] = Field(None, description="Số tiền đã hoàn")
    refund_reason: Optional[str] = Field(None, description="Lý do hoàn tiền")


class AdminPaymentCreateResponse(BaseModel):
    """Response schema for admin payment creation"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[AdminPaymentResponse] = None


class AdminPaymentRefundResponse(BaseModel):
    """Response schema for admin payment refund"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[AdminPaymentResponse] = None


class AdminPaymentListItem(BaseModel):
    """Schema for payment item in admin list with full details"""
    payment_id: UUID
    booking_id: UUID
    user_id: Optional[UUID] = None
    # Payment info
    amount: float
    payment_method: str
    payment_status: str
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    # Tour info
    tour_name: Optional[str] = None
    start_date: Optional[str] = None
    # User/Contact info
    user_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    # Admin tracking
    created_by_admin_id: Optional[str] = None
    refunded_by: Optional[str] = None
    refunded_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AdminPaymentListResponse(BaseModel):
    """Response schema for admin payment list"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[list[AdminPaymentListItem]] = None
    total: Optional[int] = None

