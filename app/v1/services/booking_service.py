"""
Booking Service
Handles booking CRUD operations
"""
import logging
import random
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from supabase import Client
from .promotion_service import PromotionService
from .otp_service import get_otp_service

logger = logging.getLogger(__name__)


class BookingService:
    """Service for managing tour bookings"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize BookingService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        self.promotion_service = PromotionService(supabase_client)
    
    async def get_all_bookings(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all bookings with optional filters
        
        Args:
            user_id: Filter by user ID
            status: Filter by booking status
            limit: Maximum number of results
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            query = self.supabase.table('bookings').select('*', count='exact')
            
            # Apply filters
            if user_id:
                query = query.eq('user_id', user_id)
            if status:
                query = query.eq('status', status)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            # Order by created_at descending
            query = query.order('created_at', desc=True)
            
            result = query.execute()
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": result.data,
                "total": result.count
            }
            
        except Exception as e:
            logger.error(f"Error getting bookings: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving bookings: {str(e)}",
                "data": None,
                "total": 0
            }
    
    async def get_booking_by_id(self, booking_id: str) -> Dict[str, Any]:
        """
        Get booking by ID
        
        Args:
            booking_id: UUID of the booking
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            result = self.supabase.table('bookings') \
                .select('*') \
                .eq('booking_id', booking_id) \
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Booking not found",
                    "data": None
                }
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting booking {booking_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving booking: {str(e)}",
                "data": None
            }
    
    async def create_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new booking
        
        Args:
            booking_data: Dictionary containing booking information
                - package_id: UUID
                - user_id: UUID
                - number_of_people: int
                - contact_name: str
                - contact_phone: str
                - special_requests: Optional[str]
                - promotion_id: Optional[UUID] - Mã khuyến mãi
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            # Verify package exists, has available slots, and get price
            package_result = self.supabase.table('tour_packages') \
                .select('available_slots, is_active, price') \
                .eq('package_id', str(booking_data['package_id'])) \
                .execute()
            
            if not package_result.data:
                return {
                    "EC": 1,
                    "EM": "Tour package not found",
                    "data": None
                }
            
            package = package_result.data[0]
            
            if not package['is_active']:
                return {
                    "EC": 2,
                    "EM": "Tour package is not active",
                    "data": None
                }
            
            if package['available_slots'] < booking_data['number_of_people']:
                return {
                    "EC": 3,
                    "EM": f"Not enough slots available. Only {package['available_slots']} slots left",
                    "data": None
                }
            
            # Calculate original total amount
            original_amount = package['price'] * booking_data['number_of_people']
            final_amount = original_amount
            discount_amount = 0
            promotion_id = booking_data.get('promotion_id')
            promotion_code = booking_data.get('promotion_code')
            
            # Resolve promotion: prioritize code over id
            if promotion_code:
                # Get promotion by code
                promo_lookup = await self.promotion_service.get_promotion_by_code(promotion_code)
                if promo_lookup['EC'] == 0:
                    promotion_id = promo_lookup['promotion']['promotion_id']
                    logger.info(f"Resolved promotion code {promotion_code} to ID {promotion_id}")
                else:
                    logger.warning(f"Invalid promotion code: {promotion_code}")
                    promotion_id = None
            
            # Apply promotion if we have a valid ID
            if promotion_id:
                promo_result = await self.promotion_service.apply_promotion_to_booking(
                    str(promotion_id),
                    original_amount
                )
                
                if promo_result['EC'] == 0:
                    # Promotion applied successfully
                    final_amount = promo_result['final_price']
                    discount_amount = promo_result['discount_amount']
                    logger.info(f"Applied promotion {promotion_id}: {original_amount} -> {final_amount}")
                else:
                    # Promotion failed, log warning but continue with original price
                    logger.warning(f"Could not apply promotion {promotion_id}: {promo_result['EM']}")
                    promotion_id = None  # Don't save invalid promotion
            
            # Prepare booking data
            now = datetime.now(timezone.utc).isoformat()
            booking_insert = {
                "package_id": str(booking_data['package_id']),
                "number_of_people": booking_data['number_of_people'],
                "total_amount": final_amount,  # Giá sau khi áp dụng khuyến mãi
                "contact_name": booking_data['contact_name'],
                "contact_phone": booking_data['contact_phone'],
                "special_requests": booking_data.get('special_requests'),
                "user_id": str(booking_data['user_id']),
                "status": booking_data.get("status", "pending"),  # Allow custom status
                "created_at": now,
                "updated_at": now
            }
            
            # Add promotion_id if applied successfully
            if promotion_id:
                booking_insert["promotion_id"] = str(promotion_id)
            
            # Insert booking
            result = self.supabase.table('bookings').insert(booking_insert).execute()
            
            if not result.data:
                return {
                    "EC": 4,
                    "EM": "Failed to create booking",
                    "data": None
                }
            
            # Update available slots
            new_slots = package['available_slots'] - booking_data['number_of_people']
            self.supabase.table('tour_packages') \
                .update({"available_slots": new_slots}) \
                .eq('package_id', str(booking_data['package_id'])) \
                .execute()
            
            logger.info(f"Created booking {result.data[0]['booking_id']} (Original: {original_amount}, Final: {final_amount}, Discount: {discount_amount})")
            
            return {
                "EC": 0,
                "EM": "Booking created successfully",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error creating booking: {str(e)}",
                "data": None
            }
    
    async def update_booking(
        self, 
        booking_id: str, 
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update booking information
        
        Args:
            booking_id: UUID of the booking
            update_data: Dictionary containing fields to update
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            # Check if booking exists
            existing = await self.get_booking_by_id(booking_id)
            if existing["EC"] != 0:
                return existing
            
            old_booking = existing["data"]
            
            # Get package info for price calculation
            package_result = self.supabase.table('tour_packages') \
                .select('available_slots, price') \
                .eq('package_id', old_booking['package_id']) \
                .execute()
            
            if not package_result.data:
                return {
                    "EC": 1,
                    "EM": "Tour package not found",
                    "data": None
                }
            
            package = package_result.data[0]
            
            # Handle number_of_people change (update available slots)
            if "number_of_people" in update_data:
                old_people = old_booking['number_of_people']
                new_people = update_data['number_of_people']
                people_diff = new_people - old_people
                
                if people_diff != 0:
                    current_slots = package['available_slots']
                    
                    if people_diff > 0 and current_slots < people_diff:
                        return {
                            "EC": 1,
                            "EM": f"Not enough slots. Only {current_slots} available",
                            "data": None
                        }
                    
                    # Update package slots
                    new_slots = current_slots - people_diff
                    self.supabase.table('tour_packages') \
                        .update({"available_slots": new_slots}) \
                        .eq('package_id', old_booking['package_id']) \
                        .execute()
            
            # Recalculate total_amount if number_of_people or promotion_id/code changed
            if "number_of_people" in update_data or "promotion_id" in update_data or "promotion_code" in update_data:
                # Get the final number of people (new or old)
                final_people = update_data.get('number_of_people', old_booking['number_of_people'])
                
                # Calculate original amount
                original_amount = package['price'] * final_people
                final_amount = original_amount
                
                # Resolve promotion: prioritize code over id
                promotion_id = None
                promotion_code = update_data.get('promotion_code')
                
                if promotion_code:
                    # Get promotion by code
                    promo_lookup = await self.promotion_service.get_promotion_by_code(promotion_code)
                    if promo_lookup['EC'] == 0:
                        promotion_id = promo_lookup['promotion']['promotion_id']
                        logger.info(f"Resolved promotion code {promotion_code} to ID {promotion_id}")
                        update_data['promotion_id'] = str(promotion_id)
                    else:
                        logger.warning(f"Invalid promotion code: {promotion_code}")
                        promotion_id = None
                    # Remove promotion_code from update_data (not a DB column)
                    del update_data['promotion_code']
                elif "promotion_id" in update_data:
                    # Use promotion_id directly
                    promotion_id = update_data.get('promotion_id')
                    # If explicitly setting promotion_id to None, remove discount
                    if promotion_id is None:
                        update_data['promotion_id'] = None
                    else:
                        # Convert UUID to string for database
                        update_data['promotion_id'] = str(promotion_id)
                else:
                    # Keep old promotion if neither code nor id provided
                    promotion_id = old_booking.get('promotion_id')
                
                # Apply promotion if exists
                if promotion_id:
                    promo_result = await self.promotion_service.apply_promotion_to_booking(
                        str(promotion_id),
                        original_amount
                    )
                    
                    if promo_result['EC'] == 0:
                        final_amount = promo_result['final_price']
                        logger.info(f"Applied promotion {promotion_id} to booking {booking_id}: {original_amount} -> {final_amount}")
                    else:
                        logger.warning(f"Could not apply promotion {promotion_id}: {promo_result['EM']}")
                        # Don't update promotion_id if it failed
                        update_data['promotion_id'] = old_booking.get('promotion_id')
                
                # Update total_amount
                update_data['total_amount'] = final_amount
            
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Update booking
            result = self.supabase.table('bookings') \
                .update(update_data) \
                .eq('booking_id', booking_id) \
                .execute()
            
            if not result.data:
                return {
                    "EC": 2,
                    "EM": "Failed to update booking",
                    "data": None
                }
            
            logger.info(f"Updated booking {booking_id}")
            
            return {
                "EC": 0,
                "EM": "Booking updated successfully",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error updating booking {booking_id}: {str(e)}")
            return {
                "EC": 3,
                "EM": f"Error updating booking: {str(e)}",
                "data": None
            }
    
    async def cancel_booking(
        self, 
        booking_id: str, 
        reason: Optional[str] = None,
        cancelled_by: str = "user"
    ) -> Dict[str, Any]:
        """
        Cancel a booking (soft delete - update status to 'cancelled')
        Also inserts record to booking_cancellations table and restores slots.
        
        Can cancel bookings with status: 'otp_sent', 'pending', or 'confirmed'
        - 'otp_sent': User created booking but hasn't verified OTP yet
        - 'pending': Booking confirmed, waiting for payment
        - 'confirmed': Booking fully confirmed
        
        Args:
            booking_id: UUID of the booking
            reason: Optional cancellation reason
            cancelled_by: Who cancelled - 'user', 'admin', or 'system'
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            # Get booking data first
            existing = await self.get_booking_by_id(booking_id)
            if existing["EC"] != 0:
                return existing
            
            booking = existing["data"]
            
            # Check if already cancelled
            if booking['status'] == 'cancelled':
                return {
                    "EC": 3,
                    "EM": "Booking is already cancelled",
                    "data": None
                }
            
            # Check if can be cancelled (otp_sent, pending, or confirmed)
            if booking['status'] not in ['otp_sent', 'pending', 'confirmed']:
                return {
                    "EC": 4,
                    "EM": f"Cannot cancel booking with status '{booking['status']}'",
                    "data": None
                }
            
            # 1. Insert to booking_cancellations table (full booking snapshot)
            cancellation_data = {
                "booking_id": booking_id,
                "user_id": booking['user_id'],
                "package_id": booking['package_id'],
                # Booking snapshot
                "number_of_people": booking['number_of_people'],
                "total_amount": booking.get('total_amount'),
                "contact_name": booking.get('contact_name'),
                "contact_phone": booking.get('contact_phone'),
                "contact_email": booking.get('contact_email'),
                "special_requests": booking.get('special_requests'),
                "previous_status": booking['status'],  # Status before cancel
                "promotion_id": booking.get('promotion_id'),
                "booking_created_at": booking.get('created_at'),
                # Cancellation info
                "reason": reason,
                "cancelled_by": cancelled_by
            }
            
            self.supabase.table('booking_cancellations') \
                .insert(cancellation_data) \
                .execute()
            
            # 2. Update booking status to cancelled (soft delete)
            update_result = self.supabase.table('bookings') \
                .update({"status": "cancelled", "updated_at": "now()"}) \
                .eq('booking_id', booking_id) \
                .execute()
            
            if not update_result.data:
                return {
                    "EC": 1,
                    "EM": "Failed to cancel booking"
                }
            
            # 3. Restore package slots
            package_result = self.supabase.table('tour_packages') \
                .select('available_slots') \
                .eq('package_id', booking['package_id']) \
                .execute()
            
            if package_result.data:
                current_slots = package_result.data[0]['available_slots']
                new_slots = current_slots + booking['number_of_people']
                
                self.supabase.table('tour_packages') \
                    .update({"available_slots": new_slots}) \
                    .eq('package_id', booking['package_id']) \
                    .execute()
                
                logger.info(f"Restored {booking['number_of_people']} slots to package {booking['package_id']}")
            
            logger.info(f"Cancelled booking {booking_id} by {cancelled_by}")
            
            return {
                "EC": 0,
                "EM": "Booking cancelled successfully",
                "data": update_result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error cancelling booking {booking_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error cancelling booking: {str(e)}",
                "data": None
            }
    
    async def delete_booking(self, booking_id: str) -> Dict[str, Any]:
        """
        Delete a booking - DEPRECATED, use cancel_booking instead
        This now calls cancel_booking for backward compatibility
        
        Args:
            booking_id: UUID of the booking
            
        Returns:
            Dict with EC and EM
        """
        logger.warning(f"delete_booking is deprecated, use cancel_booking instead. Booking: {booking_id}")
        result = await self.cancel_booking(booking_id, reason="Deleted via deprecated method", cancelled_by="system")
        return result
    
    async def create_booking_with_otp(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create booking with OTP verification flow (copy logic from MCP chatbot)
        
        Args:
            booking_data: Dictionary containing booking information including contact_email
            
        Returns:
            Dict with EC, EM, and data (includes booking_id, awaiting_otp flag)
        """
        try:
            contact_email = booking_data.get('contact_email')
            contact_phone = booking_data.get('contact_phone')
            
            if not contact_email:
                return {
                    "EC": 1,
                    "EM": "Email is required for OTP verification",
                    "data": None
                }
            
            # 1. Verify package exists, has available slots, and get price
            package_result = self.supabase.table('tour_packages') \
                .select('available_slots, is_active, price, package_name') \
                .eq('package_id', str(booking_data['package_id'])) \
                .execute()
            
            if not package_result.data:
                return {
                    "EC": 1,
                    "EM": "Tour package not found",
                    "data": None
                }
            
            package = package_result.data[0]
            
            if not package['is_active']:
                return {
                    "EC": 2,
                    "EM": "Tour package is not active",
                    "data": None
                }
            
            if package['available_slots'] < booking_data['number_of_people']:
                return {
                    "EC": 3,
                    "EM": f"Not enough slots available. Only {package['available_slots']} slots left",
                    "data": None
                }
            
            # 2. Calculate amount
            total_amount = package['price'] * booking_data['number_of_people']
            
            # 3. Create booking with status "otp_sent"
            now = datetime.now(timezone.utc).isoformat()
            booking_insert = {
                "package_id": str(booking_data['package_id']),
                "number_of_people": booking_data['number_of_people'],
                "total_amount": total_amount,
                "contact_name": booking_data['contact_name'],
                "contact_phone": contact_phone,
                "contact_email": contact_email,  # Lưu email vào booking
                "special_requests": booking_data.get('special_requests'),
                "user_id": str(booking_data['user_id']),
                "status": "otp_sent",  # OTP flow status
                "created_at": now,
                "updated_at": now
            }
            
            result = self.supabase.table('bookings').insert(booking_insert).execute()
            
            if not result.data:
                return {
                    "EC": 4,
                    "EM": "Failed to create booking",
                    "data": None
                }
            
            booking = result.data[0]
            booking_id = booking['booking_id']
            
            # 4. Generate OTP (6 digits)
            otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # 5. Store OTP in database
            otp_data = {
                "booking_id": booking_id,
                "otp_code": otp_code,
                "phone_number": contact_phone
            }
            
            try:
                otp_insert_res = self.supabase.table("otp_verifications").insert(otp_data).execute()
                if not otp_insert_res.data:
                    logger.error("Failed to insert OTP record")
                    # Rollback booking
                    self.supabase.table("bookings").delete().eq("booking_id", booking_id).execute()
                    return {"EC": 5, "EM": "Failed to create OTP record", "data": None}
            except Exception as e:
                logger.error(f"Error inserting OTP: {str(e)}")
                # Rollback booking
                self.supabase.table("bookings").delete().eq("booking_id", booking_id).execute()
                return {"EC": 5, "EM": f"Failed to create OTP: {str(e)}", "data": None}
            
            # 6. Send OTP via email
            otp_service = get_otp_service()
            email_sent = otp_service.send_otp_email(
                email=contact_email,
                otp=otp_code,
                tour_name=package['package_name']
            )
            
            if not email_sent:
                logger.warning(f"⚠️ Failed to send OTP email to {contact_email}, but booking created. OTP: {otp_code}")
            
            # 7. Update package slots
            new_slots = package['available_slots'] - booking_data['number_of_people']
            self.supabase.table('tour_packages') \
                .update({"available_slots": new_slots}) \
                .eq('package_id', str(booking_data['package_id'])) \
                .execute()
            
            logger.info(f"Created booking {booking_id} with OTP flow")
            
            # 8. Return response
            return {
                "EC": 0,
                "EM": "📧 Mã OTP đã được gửi về email của bạn. Vui lòng kiểm tra email và nhập mã OTP để xác nhận đặt tour.",
                "data": {
                    "booking_id": booking_id,
                    "awaiting_otp": True,
                    "status": "otp_sent",
                    "contact_email": contact_email,
                    "total_amount": total_amount
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating booking with OTP: {str(e)}")
            return {
                "EC": 6,
                "EM": f"Error creating booking: {str(e)}",
                "data": None
            }
    
    async def create_booking_by_admin(self, booking_data: Dict[str, Any], admin_id: str) -> Dict[str, Any]:
        """
        Admin tạo booking cho khách hàng (bỏ qua OTP, status = pending)
        
        Flow:
        1. Validate package & check slots
        2. Create booking với status="pending" (không cần OTP)
        3. Update package slots
        4. Return booking_id
        
        Args:
            booking_data: Dictionary containing booking information
            admin_id: ID của admin tạo booking
            
        Returns:
            Dict with EC, EM, and data (includes booking_id, status="pending")
        """
        try:
            # 1. Verify package exists, has available slots, and get price
            package_result = self.supabase.table('tour_packages') \
                .select('available_slots, is_active, price, package_name') \
                .eq('package_id', str(booking_data['package_id'])) \
                .execute()
            
            if not package_result.data:
                return {
                    "EC": 1,
                    "EM": "Tour package not found",
                    "data": None
                }
            
            package = package_result.data[0]
            
            if not package['is_active']:
                return {
                    "EC": 2,
                    "EM": "Tour package is not active",
                    "data": None
                }
            
            if package['available_slots'] < booking_data['number_of_people']:
                return {
                    "EC": 3,
                    "EM": f"Not enough slots available. Only {package['available_slots']} slots left",
                    "data": None
                }
            
            # 2. Calculate amount
            total_amount = package['price'] * booking_data['number_of_people']
            
            # 3. Create booking with status "pending" (không cần OTP)
            now = datetime.now(timezone.utc).isoformat()
            booking_insert = {
                "package_id": str(booking_data['package_id']),
                "number_of_people": booking_data['number_of_people'],
                "total_amount": total_amount,
                "contact_name": booking_data['contact_name'],
                "contact_phone": booking_data.get('contact_phone'),
                "contact_email": booking_data.get('contact_email'),  # Optional
                "special_requests": booking_data.get('special_requests'),
                "user_id": str(booking_data['user_id']),
                "status": "pending",  # Status pending ngay, không cần OTP
                "created_at": now,
                "updated_at": now
            }
            
            result = self.supabase.table('bookings').insert(booking_insert).execute()
            
            if not result.data:
                return {
                    "EC": 4,
                    "EM": "Failed to create booking",
                    "data": None
                }
            
            booking = result.data[0]
            booking_id = booking['booking_id']
            
            # 4. Update package slots
            new_slots = package['available_slots'] - booking_data['number_of_people']
            self.supabase.table('tour_packages') \
                .update({"available_slots": new_slots}) \
                .eq('package_id', str(booking_data['package_id'])) \
                .execute()
            
            # 5. Tự động tạo payment với status "pending" và payment_method="cash"
            payment_data = {
                "booking_id": booking_id,
                "amount": total_amount,
                "payment_method": "cash",
                "payment_status": "pending",  # Chờ thanh toán
                "transaction_id": None,
                "created_by_admin_id": admin_id,
                "created_at": now
            }
            
            try:
                payment_result = self.supabase.table('payments').insert(payment_data).execute()
                if payment_result.data:
                    logger.info(f"Auto-created pending payment for booking {booking_id} (cash method)")
                else:
                    logger.warning(f"Failed to auto-create payment for booking {booking_id}, but booking created")
            except Exception as e:
                # Nếu tạo payment thất bại, vẫn tiếp tục (booking đã tạo thành công)
                logger.error(f"Error auto-creating payment for booking {booking_id}: {str(e)}")
            
            logger.info(f"Admin {admin_id} created booking {booking_id} with status pending (no OTP)")
            
            # 6. Return response
            return {
                "EC": 0,
                "EM": "Đã tạo booking thành công. Booking đang ở trạng thái pending, chờ thanh toán.",
                "data": {
                    "booking_id": booking_id,
                    "status": "pending",
                    "total_amount": total_amount,
                    "contact_name": booking_data['contact_name'],
                    "contact_phone": booking_data.get('contact_phone'),
                    "contact_email": booking_data.get('contact_email')
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating booking by admin: {str(e)}")
            return {
                "EC": 6,
                "EM": f"Error creating booking: {str(e)}",
                "data": None
            }
    
    async def verify_otp(self, booking_id: str, otp_code: str) -> Dict[str, Any]:
        """
        Verify OTP and confirm booking (copy logic from MCP chatbot)
        
        Args:
            booking_id: UUID of the booking
            otp_code: 6-digit OTP code
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            # 1. Get OTP record
            booking_check = self.supabase.table("otp_verifications")\
                .select("*")\
                .eq("booking_id", booking_id)\
                .execute()
            
            if not booking_check.data:
                return {"EC": 1, "EM": "Không tìm thấy mã OTP cho booking này", "data": None}
            
            # 2. Get OTP record with correct code and not verified
            otp_res = self.supabase.table("otp_verifications")\
                .select("*")\
                .eq("booking_id", booking_id)\
                .eq("otp_code", otp_code)\
                .eq("is_verified", False)\
                .execute()
            
            if not otp_res.data:
                # OTP code is wrong - increment attempts
                existing_otp = self.supabase.table("otp_verifications")\
                    .select("attempts, otp_code, expires_at, created_at")\
                    .eq("booking_id", booking_id)\
                    .execute()
                
                if existing_otp.data:
                    otp_info = existing_otp.data[0]
                    current_attempts = otp_info.get("attempts", 0)
                    
                    # Increment attempts
                    self.supabase.table("otp_verifications")\
                        .update({"attempts": current_attempts + 1})\
                        .eq("booking_id", booking_id)\
                        .execute()
                    
                    # Check if expired
                    expires_at_str = otp_info.get('expires_at')
                    if expires_at_str:
                        if isinstance(expires_at_str, str):
                            if expires_at_str.endswith('Z'):
                                expires_at_str = expires_at_str.replace('Z', '+00:00')
                            expires_at = datetime.fromisoformat(expires_at_str)
                        else:
                            expires_at = expires_at_str
                        
                        if expires_at.tzinfo is None:
                            expires_at = expires_at.replace(tzinfo=timezone.utc)
                        else:
                            expires_at = expires_at.astimezone(timezone.utc)
                        
                        now_utc = datetime.now(timezone.utc)
                        if now_utc > expires_at:
                            return {"EC": 2, "EM": "Mã OTP đã hết hạn", "data": None}
                    
                    return {"EC": 3, "EM": "Mã OTP không đúng", "data": None}
                
                return {"EC": 3, "EM": "Mã OTP không đúng", "data": None}
            
            otp_record = otp_res.data[0]
            
            # 3. Check expiry
            expires_at_str = otp_record['expires_at']
            
            if isinstance(expires_at_str, str):
                if expires_at_str.endswith('Z'):
                    expires_at_str = expires_at_str.replace('Z', '+00:00')
                expires_at = datetime.fromisoformat(expires_at_str)
            else:
                expires_at = expires_at_str
            
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at = expires_at.astimezone(timezone.utc)
            
            now_utc = datetime.now(timezone.utc)
            
            if now_utc > expires_at:
                return {"EC": 2, "EM": "Mã OTP đã hết hạn", "data": None}
            
            # 4. Check attempts (max 3)
            if otp_record.get('attempts', 0) >= 3:
                return {"EC": 4, "EM": "Đã vượt quá số lần nhập OTP cho phép", "data": None}
            
            # 5. Mark OTP as verified
            self.supabase.table("otp_verifications")\
                .update({
                    "is_verified": True,
                    "verified_at": datetime.now().isoformat()
                })\
                .eq("booking_id", booking_id)\
                .execute()
            
            # 6. Update booking status to "pending" (waiting for payment)
            self.supabase.table("bookings")\
                .update({"status": "pending"})\
                .eq("booking_id", booking_id)\
                .execute()
            
            # 7. Get booking details
            booking_res = self.supabase.table("bookings")\
                .select("*, tour_packages(package_name, destination, start_date, price)")\
                .eq("booking_id", booking_id)\
                .execute()
            
            booking = booking_res.data[0] if booking_res.data else {}
            pkg = booking.get('tour_packages', {})
            if isinstance(pkg, list) and pkg:
                pkg = pkg[0]
            elif not isinstance(pkg, dict):
                pkg = {}
            
            logger.info(f"OTP verified for booking {booking_id}")
            
            return {
                "EC": 0,
                "EM": "✅ Xác thực thành công! Đặt tour của bạn đã được xác nhận. Vui lòng thanh toán để hoàn tất đặt tour.",
                "data": {
                    "booking_id": booking_id,
                    "status": "pending",
                    "tour_name": pkg.get('package_name', 'Unknown Tour'),
                    "destination": pkg.get('destination', 'Unknown'),
                    "start_date": pkg.get('start_date'),
                    "number_of_people": booking.get('number_of_people'),
                    "total_amount": booking.get('total_amount')
                }
            }
            
        except Exception as e:
            logger.error(f"Error verifying OTP for booking {booking_id}: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error verifying OTP: {str(e)}",
                "data": None
            }
    
    async def resend_otp(self, booking_id: str) -> Dict[str, Any]:
        """
        Resend OTP for a booking (when OTP expired or not received)
        
        Args:
            booking_id: UUID of the booking
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            # 1. Get booking info
            booking_res = self.supabase.table("bookings")\
                .select("*, tour_packages(package_name)")\
                .eq("booking_id", booking_id)\
                .execute()
            
            if not booking_res.data:
                return {"EC": 1, "EM": "Booking not found", "data": None}
            
            booking = booking_res.data[0]
            
            # Check status - only allow resend for otp_sent status
            if booking['status'] != 'otp_sent':
                return {
                    "EC": 2, 
                    "EM": f"Cannot resend OTP. Booking status is '{booking['status']}'. OTP can only be resent for status 'otp_sent'.",
                    "data": None
                }
            
            contact_phone = booking['contact_phone']
            contact_email = booking.get('contact_email')
            
            # 2. Validate email exists
            if not contact_email:
                return {"EC": 3, "EM": "Email not found in booking record. Cannot resend OTP.", "data": None}
            
            # 3. Delete old OTP records for this booking
            self.supabase.table("otp_verifications")\
                .delete()\
                .eq("booking_id", booking_id)\
                .execute()
            
            # 4. Generate new OTP
            otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # 5. Store new OTP (without email - email stored in booking)
            otp_data = {
                "booking_id": booking_id,
                "otp_code": otp_code,
                "phone_number": contact_phone,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            otp_insert_res = self.supabase.table("otp_verifications").insert(otp_data).execute()
            if not otp_insert_res.data:
                return {"EC": 5, "EM": "Failed to create new OTP record", "data": None}
            
            # 6. Get package name for email
            pkg = booking.get('tour_packages', {})
            if isinstance(pkg, list) and pkg:
                pkg = pkg[0]
            elif not isinstance(pkg, dict):
                pkg = {}
            
            tour_name = pkg.get('package_name', 'Tour')
            
            # 7. Send OTP via email
            otp_service = get_otp_service()
            email_sent = otp_service.send_otp_email(
                email=contact_email,
                otp=otp_code,
                tour_name=tour_name
            )
            
            if not email_sent:
                logger.warning(f"⚠️ Failed to send OTP email to {contact_email}, but OTP created. OTP code: {otp_code}")
            
            logger.info(f"OTP resent for booking {booking_id}")
            
            return {
                "EC": 0,
                "EM": "📧 Mã OTP mới đã được gửi về email của bạn. Vui lòng kiểm tra email.",
                "data": {
                    "booking_id": booking_id,
                    "contact_email": contact_email,
                    "message": "OTP resent successfully"
                }
            }
            
        except Exception as e:
            logger.error(f"Error resending OTP for booking {booking_id}: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error resending OTP: {str(e)}",
                "data": None
            }
