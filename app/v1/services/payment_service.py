"""
Payment Service
Service xử lý CRUD operations cho payments
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from supabase import Client

from .vnpay_service import VNPayService

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for managing payments"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize PaymentService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        self.vnpay_service = VNPayService()
    
    async def create_payment(
        self,
        booking_id: str,
        payment_method: str = "vnpay",
        ip_addr: str = "127.0.0.1",
        client_return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tạo payment mới và generate VNPay URL
        
        Args:
            booking_id: ID của booking
            payment_method: Phương thức thanh toán (vnpay)
            ip_addr: IP address của user
            
        Returns:
            Dict with EC, EM, data (including payment_url)
        """
        try:
            # 1. Kiểm tra booking tồn tại và lấy thông tin
            booking_result = self.supabase.table('bookings')\
                .select('booking_id, total_amount, status, user_id, tour_packages(package_name)')\
                .eq('booking_id', booking_id)\
                .execute()
            
            if not booking_result.data:
                return {
                    "EC": 1,
                    "EM": "Booking not found",
                    "data": None
                }
            
            booking = booking_result.data[0]
            
            # 2. Kiểm tra booking status
            if booking['status'] not in ['pending', 'confirmed']:
                return {
                    "EC": 2,
                    "EM": f"Cannot create payment for booking with status: {booking['status']}",
                    "data": None
                }
            
            # 3. Kiểm tra đã có payment pending chưa
            existing_payment = self.supabase.table('payments')\
                .select('payment_id, payment_status')\
                .eq('booking_id', booking_id)\
                .in_('payment_status', ['pending', 'completed'])\
                .execute()
            
            if existing_payment.data:
                existing = existing_payment.data[0]
                if existing['payment_status'] == 'completed':
                    return {
                        "EC": 3,
                        "EM": "Booking already paid",
                        "data": None
                    }
                # Return existing pending payment
                return await self._regenerate_payment_url(existing['payment_id'], booking, ip_addr)
            
            # 4. Tạo payment record
            amount = float(booking['total_amount'])
            now = datetime.now(timezone.utc).isoformat()
            
            payment_data = {
                "booking_id": booking_id,
                "amount": amount,
                "payment_method": payment_method,
                "payment_status": "pending",
                "created_at": now
            }
            
            result = self.supabase.table('payments').insert(payment_data).execute()
            
            if not result.data:
                return {
                    "EC": 4,
                    "EM": "Failed to create payment",
                    "data": None
                }
            
            payment = result.data[0]
            payment_id = payment['payment_id']
            
            # 5. Generate VNPay URL
            tour_pkg = booking.get('tour_packages', {})
            if isinstance(tour_pkg, list) and tour_pkg:
                tour_pkg = tour_pkg[0]
            tour_name = tour_pkg.get('package_name', 'Tour') if isinstance(tour_pkg, dict) else 'Tour'
            
            order_info = f"Thanh toan tour {tour_name}"
            
            payment_url = self.vnpay_service.create_payment_url(
                payment_id=payment_id,
                amount=amount,
                order_info=order_info,
                ip_addr=ip_addr,
                client_return_url=client_return_url
            )
            
            # 6. Return response with payment_url
            payment['payment_url'] = payment_url
            
            logger.info(f"Created payment {payment_id} for booking {booking_id}")
            
            return {
                "EC": 0,
                "EM": "Payment created successfully",
                "data": payment
            }
            
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error creating payment: {str(e)}",
                "data": None
            }
    
    async def _regenerate_payment_url(
        self,
        payment_id: str,
        booking: Dict[str, Any],
        ip_addr: str
    ) -> Dict[str, Any]:
        """Regenerate payment URL for existing pending payment"""
        try:
            amount = float(booking['total_amount'])
            
            tour_pkg = booking.get('tour_packages', {})
            if isinstance(tour_pkg, list) and tour_pkg:
                tour_pkg = tour_pkg[0]
            tour_name = tour_pkg.get('package_name', 'Tour') if isinstance(tour_pkg, dict) else 'Tour'
            
            order_info = f"Thanh toan tour {tour_name}"
            
            payment_url = self.vnpay_service.create_payment_url(
                payment_id=payment_id,
                amount=amount,
                order_info=order_info,
                ip_addr=ip_addr
            )
            
            # Get payment record
            payment_result = self.supabase.table('payments')\
                .select('*')\
                .eq('payment_id', payment_id)\
                .execute()
            
            payment = payment_result.data[0] if payment_result.data else {}
            payment['payment_url'] = payment_url
            
            return {
                "EC": 0,
                "EM": "Payment URL regenerated",
                "data": payment
            }
            
        except Exception as e:
            logger.error(f"Error regenerating payment URL: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error: {str(e)}",
                "data": None
            }
    
    async def get_payment_by_id(self, payment_id: str) -> Dict[str, Any]:
        """
        Lấy payment theo ID
        
        Args:
            payment_id: UUID của payment
            
        Returns:
            Dict with EC, EM, data
        """
        try:
            result = self.supabase.table('payments')\
                .select('*')\
                .eq('payment_id', payment_id)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Payment not found",
                    "data": None
                }
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting payment {payment_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error: {str(e)}",
                "data": None
            }
    
    async def get_payment_by_booking_id(self, booking_id: str) -> Dict[str, Any]:
        """
        Lấy payment theo booking_id
        
        Args:
            booking_id: UUID của booking
            
        Returns:
            Dict with EC, EM, data
        """
        try:
            result = self.supabase.table('payments')\
                .select('*')\
                .eq('booking_id', booking_id)\
                .order('created_at', desc=True)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Payment not found for this booking",
                    "data": None
                }
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting payment for booking {booking_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error: {str(e)}",
                "data": None
            }
    
    async def update_payment_status(
        self,
        payment_id: str,
        status: str,
        transaction_id: Optional[str] = None,
        paid_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update payment status
        
        Args:
            payment_id: UUID của payment
            status: Trạng thái mới (pending/completed/failed)
            transaction_id: Mã giao dịch từ VNPay
            paid_at: Thời gian thanh toán
            
        Returns:
            Dict with EC, EM, data
        """
        try:
            update_data = {"payment_status": status}
            
            if transaction_id:
                update_data["transaction_id"] = transaction_id
            
            if paid_at:
                update_data["paid_at"] = paid_at
            elif status == "completed":
                update_data["paid_at"] = datetime.now(timezone.utc).isoformat()
            
            result = self.supabase.table('payments')\
                .update(update_data)\
                .eq('payment_id', payment_id)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Payment not found",
                    "data": None
                }
            
            logger.info(f"Updated payment {payment_id} status to {status}")
            
            return {
                "EC": 0,
                "EM": "Payment status updated",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error updating payment {payment_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error: {str(e)}",
                "data": None
            }
    
    async def verify_and_complete_payment(
        self,
        callback_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify VNPay callback và complete payment
        
        Args:
            callback_data: Data từ VNPay callback
            
        Returns:
            Dict with EC, EM, data, is_success
        """
        try:
            # 1. Verify signature
            verify_result = self.vnpay_service.verify_payment_response(callback_data)
            
            if not verify_result['is_valid']:
                return {
                    "EC": 97,
                    "EM": "Invalid signature",
                    "data": None,
                    "is_success": False
                }
            
            payment_id = verify_result['payment_id']
            response_code = verify_result['response_code']
            transaction_status = verify_result['transaction_status']
            transaction_id = verify_result['transaction_id']
            
            # 2. Get payment record
            payment_result = await self.get_payment_by_id(payment_id)
            
            if payment_result['EC'] != 0:
                return {
                    "EC": 1,
                    "EM": "Payment not found",
                    "data": None,
                    "is_success": False
                }
            
            payment = payment_result['data']
            
            # 3. Check if already processed
            if payment['payment_status'] == 'completed':
                return {
                    "EC": 0,
                    "EM": "Payment already completed",
                    "data": payment,
                    "is_success": True
                }
            
            # 4. Verify amount
            callback_amount = verify_result['amount']
            if float(payment['amount']) != callback_amount:
                logger.warning(f"Amount mismatch: expected {payment['amount']}, got {callback_amount}")
                return {
                    "EC": 4,
                    "EM": "Amount mismatch",
                    "data": None,
                    "is_success": False
                }
            
            # 5. Update payment status based on response
            is_success = self.vnpay_service.is_payment_success(response_code, transaction_status)
            
            new_status = "completed" if is_success else "failed"
            
            # Parse pay_date
            pay_date = verify_result.get('pay_date')
            paid_at = None
            if pay_date and is_success:
                try:
                    paid_at = datetime.strptime(pay_date, '%Y%m%d%H%M%S').isoformat()
                except:
                    paid_at = datetime.now(timezone.utc).isoformat()
            
            update_result = await self.update_payment_status(
                payment_id=payment_id,
                status=new_status,
                transaction_id=transaction_id,
                paid_at=paid_at
            )
            
            # 6. Update booking status if payment successful
            if is_success:
                booking_id = payment['booking_id']
                self.supabase.table('bookings')\
                    .update({"status": "confirmed"})\
                    .eq('booking_id', booking_id)\
                    .execute()
                logger.info(f"Booking {booking_id} confirmed after payment")
            
            message = self.vnpay_service.get_response_message(response_code)
            
            return {
                "EC": 0 if is_success else int(response_code),
                "EM": message,
                "data": update_result.get('data'),
                "is_success": is_success
            }
            
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return {
                "EC": 99,
                "EM": f"Error: {str(e)}",
                "data": None,
                "is_success": False
            }
    
    async def get_user_payments(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lấy payment history của user
        
        Args:
            user_id: ID của user
            status: Filter theo status
            limit: Số lượng tối đa
            offset: Số bản ghi bỏ qua
            
        Returns:
            Dict with EC, EM, data, total
        """
        try:
            # Get user's bookings first
            bookings_result = self.supabase.table('bookings')\
                .select('booking_id')\
                .eq('user_id', user_id)\
                .execute()
            
            if not bookings_result.data:
                return {
                    "EC": 0,
                    "EM": "No bookings found",
                    "data": [],
                    "total": 0
                }
            
            booking_ids = [b['booking_id'] for b in bookings_result.data]
            
            # Get payments for those bookings
            query = self.supabase.table('payments')\
                .select('*, bookings(tour_packages(package_name, destination))', count='exact')\
                .in_('booking_id', booking_ids)
            
            if status:
                query = query.eq('payment_status', status)
            
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            query = query.order('created_at', desc=True)
            
            result = query.execute()
            
            # Format data
            formatted_data = []
            for payment in result.data:
                booking_info = payment.get('bookings', {})
                if isinstance(booking_info, list) and booking_info:
                    booking_info = booking_info[0]
                
                tour_pkg = booking_info.get('tour_packages', {}) if booking_info else {}
                if isinstance(tour_pkg, list) and tour_pkg:
                    tour_pkg = tour_pkg[0]
                
                formatted_data.append({
                    "payment_id": payment['payment_id'],
                    "booking_id": payment['booking_id'],
                    "amount": float(payment['amount']),
                    "payment_method": payment['payment_method'],
                    "payment_status": payment['payment_status'],
                    "transaction_id": payment.get('transaction_id'),
                    "paid_at": payment.get('paid_at'),
                    "created_at": payment['created_at'],
                    "tour_name": tour_pkg.get('package_name') if isinstance(tour_pkg, dict) else None,
                    "destination": tour_pkg.get('destination') if isinstance(tour_pkg, dict) else None
                })
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": formatted_data,
                "total": result.count
            }
            
        except Exception as e:
            logger.error(f"Error getting user payments: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error: {str(e)}",
                "data": None,
                "total": 0
            }
    
    # ================== ADMIN PAYMENT METHODS ==================
    
    async def create_payment_by_admin(
        self,
        booking_id: str,
        admin_id: str,
        payment_method: str = "bank_transfer",
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tạo payment thủ công bởi admin (bypass VNPay)
        
        Args:
            booking_id: ID của booking
            admin_id: ID của admin tạo payment
            payment_method: Phương thức thanh toán
            transaction_id: Mã giao dịch (optional)
            
        Returns:
            Dict with EC, EM, data
        """
        try:
            # 1. Kiểm tra booking tồn tại và lấy thông tin
            booking_result = self.supabase.table('bookings')\
                .select('booking_id, total_amount, status, user_id')\
                .eq('booking_id', booking_id)\
                .execute()
            
            if not booking_result.data:
                return {
                    "EC": 1,
                    "EM": "Booking not found",
                    "data": None
                }
            
            booking = booking_result.data[0]
            
            # 2. Validate booking status
            if booking['status'] not in ['pending', 'confirmed']:
                return {
                    "EC": 2,
                    "EM": f"Cannot create payment for booking with status '{booking['status']}'",
                    "data": None
                }
            
            # 3. Kiểm tra đã có payment completed chưa
            existing_payment = self.supabase.table('payments')\
                .select('payment_id, payment_status')\
                .eq('booking_id', booking_id)\
                .in_('payment_status', ['completed'])\
                .execute()
            
            if existing_payment.data:
                return {
                    "EC": 3,
                    "EM": "Payment already exists for this booking",
                    "data": None
                }
            
            # 4. Tạo payment với status completed
            now = datetime.now(timezone.utc).isoformat()
            payment_data = {
                "booking_id": booking_id,
                "amount": booking['total_amount'],
                "payment_method": payment_method,
                "payment_status": "completed",
                "transaction_id": transaction_id,
                "paid_at": now,
                "created_by_admin_id": admin_id,
                "created_at": now
            }
            
            payment_result = self.supabase.table('payments')\
                .insert(payment_data)\
                .execute()
            
            if not payment_result.data:
                return {
                    "EC": 4,
                    "EM": "Failed to create payment",
                    "data": None
                }
            
            # 5. Cập nhật booking status thành confirmed
            self.supabase.table('bookings')\
                .update({"status": "confirmed"})\
                .eq('booking_id', booking_id)\
                .execute()
            
            logger.info(f"Admin {admin_id} created payment for booking {booking_id}")
            
            return {
                "EC": 0,
                "EM": "Payment created successfully",
                "data": payment_result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error creating payment by admin: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error: {str(e)}",
                "data": None
            }
    
    async def confirm_cash_payment_by_admin(
        self,
        booking_id: str,
        admin_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Admin xác nhận khách hàng đã thanh toán tiền mặt cho booking
        
        Flow:
        1. Kiểm tra booking tồn tại và có status "pending" (sau khi verify OTP)
        2. Kiểm tra chưa có payment completed
        3. Tạo payment với payment_method="cash", status="completed"
        4. Cập nhật booking status thành "confirmed"
        5. Doanh thu tự động được tính từ bookings confirmed có payment completed
        
        Args:
            booking_id: ID của booking cần xác nhận thanh toán
            admin_id: ID của admin xác nhận
            notes: Ghi chú của admin (optional)
            
        Returns:
            Dict with EC, EM, data
        """
        try:
            # 1. Kiểm tra booking tồn tại và lấy thông tin
            booking_result = self.supabase.table('bookings')\
                .select('booking_id, total_amount, status, user_id')\
                .eq('booking_id', booking_id)\
                .execute()
            
            if not booking_result.data:
                return {
                    "EC": 1,
                    "EM": "Booking not found",
                    "data": None
                }
            
            booking = booking_result.data[0]
            
            # 2. Validate booking status - chỉ cho phép booking có status "pending" (sau khi verify OTP)
            if booking['status'] != 'pending':
                return {
                    "EC": 2,
                    "EM": f"Chỉ có thể xác nhận thanh toán cho booking có status 'pending'. Booking hiện tại có status '{booking['status']}'",
                    "data": None
                }
            
            # 3. Kiểm tra đã có payment chưa (bất kỳ status)
            existing_payment = self.supabase.table('payments')\
                .select('payment_id, payment_status, payment_method')\
                .eq('booking_id', booking_id)\
                .execute()
            
            now = datetime.now(timezone.utc).isoformat()
            
            if existing_payment.data:
                payment = existing_payment.data[0]
                
                # Nếu đã có payment completed → Báo lỗi
                if payment['payment_status'] == 'completed':
                    return {
                        "EC": 3,
                        "EM": "Booking này đã có payment completed. Không thể tạo payment mới.",
                        "data": None
                    }
                
                # Nếu có payment pending/failed → Update thành completed với cash method
                update_data = {
                    "payment_method": "cash",
                    "payment_status": "completed",
                    "paid_at": now,
                    "created_by_admin_id": admin_id,
                    "transaction_id": None  # Tiền mặt không có transaction_id
                }
                
                payment_result = self.supabase.table('payments')\
                    .update(update_data)\
                    .eq('payment_id', payment['payment_id'])\
                    .execute()
                
                if not payment_result.data:
                    return {
                        "EC": 4,
                        "EM": "Failed to update payment",
                        "data": None
                    }
                
                # Lấy payment đã update
                updated_payment = payment_result.data[0]
                
            else:
                # 4. Chưa có payment → Tạo mới với payment_method="cash", status="completed"
                payment_data = {
                    "booking_id": booking_id,
                    "amount": booking['total_amount'],
                    "payment_method": "cash",  # Mặc định là tiền mặt
                    "payment_status": "completed",
                    "transaction_id": None,  # Tiền mặt không có transaction_id
                    "paid_at": now,
                    "created_by_admin_id": admin_id,
                    "created_at": now
                }
                
                payment_result = self.supabase.table('payments')\
                    .insert(payment_data)\
                    .execute()
                
                if not payment_result.data:
                    return {
                        "EC": 4,
                        "EM": "Failed to create payment",
                        "data": None
                    }
                
                updated_payment = payment_result.data[0]
            
            # 5. Cập nhật booking status thành "confirmed"
            self.supabase.table('bookings')\
                .update({"status": "confirmed"})\
                .eq('booking_id', booking_id)\
                .execute()
            
            # Log với notes nếu có
            log_message = f"Admin {admin_id} confirmed cash payment for booking {booking_id}. Amount: {booking['total_amount']}"
            if notes:
                log_message += f" Notes: {notes}"
            logger.info(log_message)
            
            return {
                "EC": 0,
                "EM": "Đã xác nhận thanh toán tiền mặt thành công. Booking đã được xác nhận.",
                "data": updated_payment
            }
            
        except Exception as e:
            logger.error(f"Error confirming cash payment by admin: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error: {str(e)}",
                "data": None
            }
    
    async def refund_payment_by_admin(
        self,
        payment_id: str,
        admin_id: str,
        refund_reason: str
    ) -> Dict[str, Any]:
        """
        Hoàn tiền payment bởi admin
        
        Args:
            payment_id: ID của payment cần hoàn tiền
            admin_id: ID của admin thực hiện hoàn tiền
            refund_reason: Lý do hoàn tiền
            
        Returns:
            Dict with EC, EM, data
        """
        try:
            # 1. Lấy thông tin payment
            payment_result = self.supabase.table('payments')\
                .select('payment_id, booking_id, amount, payment_status, refunded_at')\
                .eq('payment_id', payment_id)\
                .execute()
            
            if not payment_result.data:
                return {
                    "EC": 1,
                    "EM": "Payment not found",
                    "data": None
                }
            
            payment = payment_result.data[0]
            
            # 2. Validate payment status
            if payment['payment_status'] != 'completed':
                return {
                    "EC": 2,
                    "EM": f"Cannot refund payment with status '{payment['payment_status']}'",
                    "data": None
                }
            
            # 3. Kiểm tra đã refund chưa
            if payment['refunded_at'] is not None:
                return {
                    "EC": 3,
                    "EM": "Payment already refunded",
                    "data": None
                }
            
            # 4. Lấy thông tin booking
            booking_result = self.supabase.table('bookings')\
                .select('booking_id, status')\
                .eq('booking_id', payment['booking_id'])\
                .execute()
            
            if not booking_result.data:
                return {
                    "EC": 4,
                    "EM": "Booking not found",
                    "data": None
                }
            
            booking = booking_result.data[0]
            
            # 5. Validate booking status (không refund nếu đã cancelled hoặc completed)
            if booking['status'] in ['cancelled', 'completed']:
                return {
                    "EC": 5,
                    "EM": f"Cannot refund payment for booking with status '{booking['status']}'",
                    "data": None
                }
            
            # 6. Update payment với thông tin refund
            now = datetime.now(timezone.utc).isoformat()
            refund_data = {
                "payment_status": "refunded",
                "refunded_by": admin_id,
                "refunded_at": now,
                "refund_amount": payment['amount'],
                "refund_reason": refund_reason
            }
            
            refund_result = self.supabase.table('payments')\
                .update(refund_data)\
                .eq('payment_id', payment_id)\
                .execute()
            
            if not refund_result.data:
                return {
                    "EC": 6,
                    "EM": "Failed to refund payment",
                    "data": None
                }
            
            # 7. Update booking status về pending
            self.supabase.table('bookings')\
                .update({"status": "pending"})\
                .eq('booking_id', payment['booking_id'])\
                .execute()
            
            logger.info(f"Admin {admin_id} refunded payment {payment_id} for booking {payment['booking_id']}")
            
            return {
                "EC": 0,
                "EM": "Payment refunded successfully",
                "data": refund_result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error refunding payment by admin: {str(e)}")
            return {
                "EC": 7,
                "EM": f"Error: {str(e)}",
                "data": None
            }
    
    async def get_all_payments_admin(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lấy danh sách tất cả payments cho admin với thông tin chi tiết
        
        Args:
            status: Filter theo payment_status
            user_id: Filter theo user_id
            limit: Số lượng kết quả tối đa
            offset: Bỏ qua số lượng bản ghi
            
        Returns:
            Dict with EC, EM, data, total
        """
        try:
            # Build query with joins
            query = self.supabase.table('payments')\
                .select(
                    """
                    payment_id,
                    booking_id,
                    amount,
                    payment_method,
                    payment_status,
                    transaction_id,
                    paid_at,
                    created_at,
                    created_by_admin_id,
                    refunded_by,
                    refunded_at,
                    bookings(
                        user_id,
                        contact_phone,
                        contact_email,
                        tour_packages(
                            package_name,
                            start_date
                        )
                    )
                    """,
                    count='exact'
                )
            
            # Apply filters
            if status:
                query = query.eq('payment_status', status)
            
            if user_id:
                query = query.eq('bookings.user_id', user_id)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            # Order by created_at descending
            query = query.order('created_at', desc=True)
            
            result = query.execute()
            
            # Format data - flatten nested structure
            formatted_data = []
            for payment in result.data:
                booking = payment.get('bookings', {}) or {}
                tour_pkg = booking.get('tour_packages', {}) or {}
                
                # Handle if tour_packages is a list
                if isinstance(tour_pkg, list):
                    tour_pkg = tour_pkg[0] if tour_pkg else {}
                
                formatted_data.append({
                    "payment_id": payment['payment_id'],
                    "booking_id": payment['booking_id'],
                    "user_id": booking.get('user_id'),
                    "amount": payment['amount'],
                    "payment_method": payment['payment_method'],
                    "payment_status": payment['payment_status'],
                    "transaction_id": payment.get('transaction_id'),
                    "paid_at": payment.get('paid_at'),
                    "created_at": payment['created_at'],
                    "tour_name": tour_pkg.get('package_name') if isinstance(tour_pkg, dict) else None,
                    "start_date": tour_pkg.get('start_date') if isinstance(tour_pkg, dict) else None,
                    "user_name": None,  # Would need to join users table separately
                    "contact_phone": booking.get('contact_phone'),
                    "contact_email": booking.get('contact_email'),
                    "created_by_admin_id": payment.get('created_by_admin_id'),
                    "refunded_by": payment.get('refunded_by'),
                    "refunded_at": payment.get('refunded_at')
                })
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": formatted_data,
                "total": result.count
            }
            
        except Exception as e:
            logger.error(f"Error getting all payments for admin: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error: {str(e)}",
                "data": None,
                "total": 0
            }

