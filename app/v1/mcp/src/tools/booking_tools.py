"""
MCP Tools - Booking Tools
Interactive booking collection và management
"""
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import random
from app.v1.core.supabase import get_supabase_client
from app.v1.services.otp_service import get_otp_service
from app.v1.services.payment_service import PaymentService
from app.v1.services.agent_services.utils.ui_generator import generate_payment_button_html
from pydantic import ValidationError
from app.v1.mcp.src.schema import (
    CreateBookingInput,
    UpdateBookingInput,
    DeleteBookingInput,
    GetUserBookingsInput,
    VerifyOTPInput,
    CreatePaymentInput
)

# Logger
logger = logging.getLogger(__name__)


async def _create_booking_impl(
    user_phone: str,
    user_email: str,
    package_id: str,
    number_of_people: int,
    special_requests: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Implementation of create_booking tool.
    """
    logger.info(f"Creating booking: phone={user_phone}, pkg={package_id}, user_id={user_id}")
    try:
        supabase = get_supabase_client()
        
        # 1. Validate Package & Check Slots
        package_res = supabase.table("tour_packages").select("*").eq("package_id", package_id).eq("is_active", True).execute()
        if not package_res.data:
            return {"success": False, "error": f"Tour package '{package_id}' not found or inactive."}
        
        package = package_res.data[0]
        if package['available_slots'] < number_of_people:
            return {
                "success": False, 
                "error": f"Insufficient slots. Available: {package['available_slots']}, Requested: {number_of_people}"
            }

        # 2. Get or Create User
        user = None
        
        # Priority 1: Check by user_id if provided
        if user_id:
            logger.info(f"Checking user by ID: {user_id}")
            user_res = supabase.table("users").select("user_id, full_name, phone_number").eq("user_id", user_id).execute()
            if user_res.data:
                user = user_res.data[0]
                logger.info(f"Found user by ID: {user}")
        
        # Priority 2: Check by phone_number if user not found yet
        if not user:
            logger.info(f"Checking user by phone: {user_phone}")
            user_res = supabase.table("users").select("user_id, full_name, phone_number").eq("phone_number", user_phone).execute()
            if user_res.data:
                user = user_res.data[0]
                logger.info(f"Found user by phone: {user}")
                # WARNING: If user_id was provided but we found a DIFFERENT user by phone, we have a conflict.
                # We use the existing user, effectively ignoring the provided user_id.
                if user_id and user['user_id'] != user_id:
                    logger.warning(f"User ID mismatch! Requested: {user_id}, Found existing: {user['user_id']}")
            else:
                # Create new user
                logger.info("Creating new user...")
                new_user = {
                    "phone_number": user_phone,
                    "full_name": f"Khách hàng {user_phone[-4:]}",
                    "email": f"{user_phone}@temp.com"
                }
                # If user_id was provided but not found, use it for the new user
                if user_id:
                    new_user["user_id"] = user_id
                    logger.info(f"Using provided user_id for new user: {user_id}")
                    
                create_res = supabase.table("users").insert(new_user).execute()
                if not create_res.data:
                    return {"success": False, "error": "Failed to create user profile."}
                user = create_res.data[0]
                logger.info(f"Created user: {user}")

        # 3. Create Booking với status "otp_sent"
        total_amount = float(package['price']) * number_of_people
        booking_data = {
            "user_id": user['user_id'],
            "package_id": package_id,
            "number_of_people": number_of_people,
            "total_amount": total_amount,
            "contact_name": user.get('full_name', user_phone),
            "contact_phone": user_phone,
            "special_requests": special_requests or "",
            "status": "otp_sent",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        booking_res = supabase.table("bookings").insert(booking_data).execute()
        if not booking_res.data:
             return {"success": False, "error": "Database error: Failed to insert booking."}
        
        booking = booking_res.data[0]
        booking_id = booking['booking_id']

        # 4. Generate OTP (6 số)
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # 5. Lưu OTP vào otp_verifications table
        otp_data = {
            "booking_id": booking_id,
            "otp_code": otp_code,
            "phone_number": user_phone
            # expires_at sẽ tự động set bởi trigger (created_at + 5 phút)
            # Note: user_id không có trong schema otp_verifications table
        }
        try:
            otp_insert_res = supabase.table("otp_verifications").insert(otp_data).execute()
            if not otp_insert_res.data:
                logger.error("Failed to insert OTP record")
                # Rollback booking
                supabase.table("bookings").delete().eq("booking_id", booking_id).execute()
                return {"success": False, "error": "Failed to create OTP record"}
        except Exception as e:
            logger.error(f"Error inserting OTP: {str(e)}")
            # Rollback booking
            supabase.table("bookings").delete().eq("booking_id", booking_id).execute()
            return {"success": False, "error": f"Failed to create OTP: {str(e)}"}
        
        # 6. Gửi OTP qua email bằng SendGrid
        otp_service = get_otp_service()
        email_sent = otp_service.send_otp_email(
            email=user_email,
            otp=otp_code,
            tour_name=package['package_name']
        )
        
        if not email_sent:
            logger.warning(f"⚠️ Failed to send OTP email to {user_email}, but booking and OTP record created. OTP code: {otp_code}")
            logger.warning("⚠️ User can still verify OTP manually if they know the code, but email notification failed.")

        # 7. Update Slots
        new_slots = package['available_slots'] - number_of_people
        supabase.table("tour_packages").update({"available_slots": new_slots}).eq("package_id", package_id).execute()

        # 8. Return Success với awaiting_otp flag
        return {
            "success": True,
            "booking_id": booking_id,
            "message": "📧 Mã OTP đã được gửi về email của bạn. Vui lòng kiểm tra email và nhập mã OTP để xác nhận đặt tour.",
            "awaiting_otp": True,
            "confirmation": {
                "booking_id": booking_id,
                "tour_name": package['package_name'],
                "destination": package['destination'],
                "start_date": package['start_date'],
                "number_of_people": number_of_people,
                "total_amount": total_amount,
                "status": "otp_sent",
                "contact_phone": user_phone,
                "email": user_email
            }
        }

    except Exception as e:
        logger.error(f"Booking error: {str(e)}")
        return {"success": False, "error": f"System error: {str(e)}"}


async def _get_user_bookings_impl(user_id: Optional[str]) -> Dict[str, Any]:
    """Implementation of get_user_bookings tool"""
    # Validate input early: user_id must be provided in API or auto-injected
    if not user_id:
        return {"success": False, "error": "User ID is missing. Cannot retrieve bookings."}

    try:
        supabase = get_supabase_client()
        
        # 1. Get Bookings with Package Info
        bookings_res = supabase.table("bookings")\
            .select("*, tour_packages(package_name, destination, start_date, price)")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
            
        if not bookings_res.data:
            return {"success": True, "bookings": [], "message": "No bookings found for this user."}

        # 2. Format Result
        bookings = []
        for b in bookings_res.data:
            pkg = b.get('tour_packages', {})
            # Handle case where pkg might be None or list (though single relation usually dict)
            if isinstance(pkg, list) and pkg: pkg = pkg[0]
            elif not isinstance(pkg, dict): pkg = {}

            bookings.append({
                "booking_id": b['booking_id'],
                "tour_name": pkg.get('package_name', 'Unknown Tour'),
                "destination": pkg.get('destination', 'Unknown'),
                "start_date": pkg.get('start_date'),
                "number_of_people": b['number_of_people'],
                "total_amount": b['total_amount'],
                "status": b['status'],
                "created_at": b['created_at']
            })

        return {"success": True, "bookings": bookings}

    except Exception as e:
        logger.error(f"Get bookings error: {str(e)}")
        return {"success": False, "error": f"System error: {str(e)}"}


async def _update_booking_impl(
    booking_id: str, 
    number_of_people: Optional[int] = None, 
    special_requests: Optional[str] = None
) -> Dict[str, Any]:
    """Implementation of update_booking tool"""
    try:
        supabase = get_supabase_client()
        
        # 1. Get Booking
        booking_res = supabase.table("bookings").select("*").eq("booking_id", booking_id).execute()
        if not booking_res.data:
            return {"success": False, "error": f"Booking {booking_id} not found."}
        booking = booking_res.data[0]
        
        updates = {}
        
        # 2. Handle Number of People Change
        if number_of_people is not None and number_of_people != booking['number_of_people']:
            package_id = booking['package_id']
            package_res = supabase.table("tour_packages").select("*").eq("package_id", package_id).execute()
            if not package_res.data:
                return {"success": False, "error": "Associated tour package not found."}
            package = package_res.data[0]
            
            diff = number_of_people - booking['number_of_people']
            
            # Check slots if increasing
            if diff > 0 and package['available_slots'] < diff:
                return {
                    "success": False, 
                    "error": f"Insufficient slots for increase. Available: {package['available_slots']}, Needed: {diff}"
                }
            
            # Update slots
            new_slots = package['available_slots'] - diff
            supabase.table("tour_packages").update({"available_slots": new_slots}).eq("package_id", package_id).execute()
            
            # Update booking amount
            updates['number_of_people'] = number_of_people
            updates['total_amount'] = float(package['price']) * number_of_people
            
        # 3. Handle Special Requests
        if special_requests is not None:
            updates['special_requests'] = special_requests
            
        if not updates:
            return {"success": True, "message": "No changes requested."}
            
        updates['updated_at'] = datetime.now().isoformat()
        
        # 4. Update Booking
        res = supabase.table("bookings").update(updates).eq("booking_id", booking_id).execute()
        if not res.data:
            return {"success": False, "error": "Failed to update booking in database."}
            
        return {"success": True, "message": "Booking updated successfully", "booking": res.data[0]}

    except Exception as e:
        logger.error(f"Update booking error: {str(e)}")
        return {"success": False, "error": f"System error: {str(e)}"}


async def _delete_booking_impl(booking_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Implementation of delete_booking tool"""
    try:
        supabase = get_supabase_client()
        
        # 1. Get Booking
        booking_res = supabase.table("bookings").select("*").eq("booking_id", booking_id).execute()
        if not booking_res.data:
            return {"success": False, "error": f"Booking {booking_id} not found."}
        booking = booking_res.data[0]
        
        if booking['status'] == 'cancelled':
             return {"success": False, "error": "Booking is already cancelled."}

        # 2. Restore Slots
        package_id = booking['package_id']
        package_res = supabase.table("tour_packages").select("available_slots").eq("package_id", package_id).execute()
        if package_res.data:
            current_slots = package_res.data[0]['available_slots']
            new_slots = current_slots + booking['number_of_people']
            supabase.table("tour_packages").update({"available_slots": new_slots}).eq("package_id", package_id).execute()

        # 3. Delete Booking (Hard Delete)
        res = supabase.table("bookings").delete().eq("booking_id", booking_id).execute()
        
        return {"success": True, "message": f"Booking {booking_id} deleted successfully."}

    except Exception as e:
        logger.error(f"Delete booking error: {str(e)}")
        return {"success": False, "error": f"System error: {str(e)}"}


def register_booking_tools(mcp: FastMCP):
    """Register booking-related tools"""
    
    @mcp.tool()
    async def create_booking(
        user_phone: str,
        user_email: str,
        package_id: str,
        number_of_people: int,
        special_requests: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new tour booking for a user.
        
        REQUIRED PARAMETERS:
        - user_phone: User's phone number (Vietnamese format, e.g., '0901234567')
        - user_email: User's email address (REQUIRED - OTP will be sent to this email)
        - package_id: Tour package UUID (exactly as returned from search_tour_packages)
        - number_of_people: Number of people (1-50)
        
        OPTIONAL PARAMETERS:
        - special_requests: Special requests or dietary restrictions
        - user_id: User ID if available (for authenticated users, auto-injected if not provided)
        
        IMPORTANT: You MUST collect user_email from the user before calling this tool.
        After calling, system will send OTP code to user_email and return awaiting_otp=True.
        """
        try:
            validated = CreateBookingInput(
                user_phone=user_phone,
                user_email=user_email,
                package_id=package_id,
                number_of_people=number_of_people,
                special_requests=special_requests,
                user_id=user_id
            )
            return await _create_booking_impl(
                user_phone=validated.user_phone,
                user_email=validated.user_email,
                package_id=validated.package_id,
                number_of_people=validated.number_of_people,
                special_requests=validated.special_requests,
                user_id=validated.user_id
            )
        except ValidationError as e:
            return {"success": False, "error": f"Input Validation Error: {str(e)}"}

    @mcp.tool()
    async def get_user_bookings(user_id: str) -> Dict[str, Any]:
        """
        Get all bookings for a specific user by user ID.
        you only call that tool without input from user. The user_id was retrieved from the agent state.
        Do not ask user anymore.
        """
        try:
            validated = GetUserBookingsInput(user_id=user_id)
            return await _get_user_bookings_impl(user_id=validated.user_id)
        except ValidationError as e:
            return {"success": False, "error": f"Input Validation Error: {str(e)}"}

    @mcp.tool()
    async def update_booking(
        booking_id: str,
        number_of_people: Optional[int] = None,
        special_requests: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing booking (change number of people or special requests).
        """
        try:
            validated = UpdateBookingInput(
                booking_id=booking_id,
                number_of_people=number_of_people,
                special_requests=special_requests
            )
            return await _update_booking_impl(
                booking_id=validated.booking_id,
                number_of_people=validated.number_of_people,
                special_requests=validated.special_requests
            )
        except ValidationError as e:
            return {"success": False, "error": f"Input Validation Error: {str(e)}"}

    async def _verify_otp_impl(booking_id: str, otp_code: str) -> Dict[str, Any]:
        """Verify OTP và confirm booking"""
        try:
            supabase = get_supabase_client()
            
            # 1. Get OTP record - First check if booking exists
            booking_check = supabase.table("otp_verifications")\
                .select("*")\
                .eq("booking_id", booking_id)\
                .execute()
            
            if not booking_check.data:
                return {"success": False, "error": "Không tìm thấy mã OTP cho booking này"}
            
            # 2. Get OTP record with correct code and not verified
            # NOTE: Do NOT filter by expires_at in query - check expiry in code after getting record
            # This allows us to distinguish between wrong code vs expired
            otp_res = supabase.table("otp_verifications")\
                .select("*")\
                .eq("booking_id", booking_id)\
                .eq("otp_code", otp_code)\
                .eq("is_verified", False)\
                .execute()
            
            if not otp_res.data:
                # OTP code is wrong - increment attempts
                existing_otp = supabase.table("otp_verifications")\
                    .select("attempts, otp_code, expires_at, created_at")\
                    .eq("booking_id", booking_id)\
                    .execute()
                
                if existing_otp.data:
                    otp_info = existing_otp.data[0]
                    current_attempts = otp_info.get("attempts", 0)
                    stored_otp = otp_info.get("otp_code", "")
                    
                    # Increment attempts
                    supabase.table("otp_verifications")\
                        .update({"attempts": current_attempts + 1})\
                        .eq("booking_id", booking_id)\
                        .execute()
                    
                    # Check if it's wrong code vs expired
                    expires_at_str = otp_info.get('expires_at')
                    if expires_at_str:
                        from datetime import timezone
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
                            logger.warning(f"OTP expired: expires_at={expires_at}, now={now_utc}")
                            return {"success": False, "error": "Mã OTP đã hết hạn"}
                    
                    logger.warning(f"Wrong OTP code: provided={otp_code}, stored={stored_otp}")
                    return {"success": False, "error": "Mã OTP không đúng"}
                
                return {"success": False, "error": "Mã OTP không đúng"}
            
            otp_record = otp_res.data[0]
            
            # 3. Check expiry - Fix timezone comparison issue
            expires_at_str = otp_record['expires_at']
            created_at_str = otp_record.get('created_at')
            
            from datetime import timezone
            
            # Parse expires_at and ensure UTC timezone
            if isinstance(expires_at_str, str):
                # Handle different datetime formats from database
                if expires_at_str.endswith('Z'):
                    expires_at_str = expires_at_str.replace('Z', '+00:00')
                expires_at = datetime.fromisoformat(expires_at_str)
            else:
                expires_at = expires_at_str
            
            # Ensure expires_at is timezone-aware (assume UTC if not)
            if expires_at.tzinfo is None:
                # If no timezone, assume UTC (database TIMESTAMP without timezone defaults to UTC in Supabase)
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC for consistent comparison
                expires_at = expires_at.astimezone(timezone.utc)
            
            # Get current time in UTC
            now_utc = datetime.now(timezone.utc)
            
            # Log for debugging - show raw values and parsed values
            logger.info(f"🔍 OTP expiry check for booking {booking_id}:")
            logger.info(f"   Raw expires_at from DB: {expires_at_str}")
            logger.info(f"   Parsed expires_at (UTC): {expires_at}")
            logger.info(f"   Current time (UTC): {now_utc}")
            logger.info(f"   Created_at: {created_at_str}")
            
            remaining_seconds = (expires_at - now_utc).total_seconds()
            logger.info(f"   ⏱️ Time remaining: {remaining_seconds:.2f} seconds ({remaining_seconds/60:.2f} minutes)")
            
            # Compare in UTC - only expire if current time is AFTER expires_at
            if now_utc > expires_at:
                time_diff = (now_utc - expires_at).total_seconds()
                logger.error(f"❌ OTP EXPIRED: expires_at={expires_at}, now={now_utc}, expired by {time_diff:.2f} seconds")
                return {"success": False, "error": "Mã OTP đã hết hạn"}
            
            logger.info(f"✅ OTP is still valid - {remaining_seconds:.2f} seconds remaining")
            
            # 3. Check attempts (max 3)
            if otp_record.get('attempts', 0) >= 3:
                return {"success": False, "error": "Đã vượt quá số lần nhập OTP cho phép"}
            
            # 4. Mark OTP as verified
            supabase.table("otp_verifications")\
                .update({
                    "is_verified": True,
                    "verified_at": datetime.now().isoformat()
                })\
                .eq("booking_id", booking_id)\
                .execute()
            
            # 5. Set booking status to "pending" (waiting for payment)
            supabase.table("bookings")\
                .update({"status": "pending"})\
                .eq("booking_id", booking_id)\
                .execute()
            
            # 6. Get booking details for response
            booking_res = supabase.table("bookings")\
                .select("*, tour_packages(package_name, destination, start_date, price)")\
                .eq("booking_id", booking_id)\
                .execute()
            
            booking = booking_res.data[0] if booking_res.data else {}
            pkg = booking.get('tour_packages', {})
            if isinstance(pkg, list) and pkg:
                pkg = pkg[0]
            elif not isinstance(pkg, dict):
                pkg = {}
            
            return {
                "success": True,
                "message": "✅ Xác thực thành công! Đặt tour của bạn đã được xác nhận. Vui lòng thanh toán để hoàn tất đặt tour.",
                "booking_id": booking_id,
                "confirmation": {
                    "booking_id": booking_id,
                    "tour_name": pkg.get('package_name', 'Unknown Tour'),
                    "destination": pkg.get('destination', 'Unknown'),
                    "start_date": pkg.get('start_date'),
                    "number_of_people": booking.get('number_of_people'),
                    "total_amount": booking.get('total_amount'),
                    "status": "pending"
                }
            }
        except Exception as e:
            logger.error(f"Verify OTP error: {str(e)}")
            return {"success": False, "error": f"System error: {str(e)}"}

    @mcp.tool()
    async def verify_otp_and_confirm_booking(
        booking_id: str,
        otp_code: str
    ) -> Dict[str, Any]:
        """
        Verify OTP code and confirm booking.
        Use this tool when user provides the OTP code from their email.
        """
        try:
            validated = VerifyOTPInput(
                booking_id=booking_id,
                otp_code=otp_code
            )
            return await _verify_otp_impl(
                booking_id=validated.booking_id,
                otp_code=validated.otp_code
            )
        except ValidationError as e:
            return {"success": False, "error": f"Input Validation Error: {str(e)}"}

    @mcp.tool()
    async def delete_booking(booking_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel (delete) a booking and restore available slots.
        """
        try:
            validated = DeleteBookingInput(booking_id=booking_id, reason=reason)
            return await _delete_booking_impl(booking_id=validated.booking_id, reason=validated.reason)
        except ValidationError as e:
            return {"success": False, "error": f"Input Validation Error: {str(e)}"}

    @mcp.tool()
    async def create_payment(
        booking_id: str,
        payment_method: str = "vnpay"
    ) -> Dict[str, Any]:
        """
        Tạo payment request và generate VNPay URL cho booking.
        Use this tool after OTP verification succeeds (status='pending') to create payment link.
        After successful payment, booking status will be updated to 'confirmed'.
        """
        try:
            validated = CreatePaymentInput(
                booking_id=booking_id,
                payment_method=payment_method
            )
            return await _create_payment_impl(
                booking_id=validated.booking_id,
                payment_method=validated.payment_method
            )
        except ValidationError as e:
            return {"success": False, "error": f"Input Validation Error: {str(e)}"}

    @mcp.tool()
    async def generate_payment_ui(
        payment_url: str,
        booking_id: str,
        total_amount: float,
        tour_name: str,
        payment_method: str = "vnpay"
    ) -> Dict[str, Any]:
        """
        Generate payment button UI component for user to click and pay.
        Use this tool after create_payment succeeds to show payment button to user.
        """
        try:
            return await _generate_payment_ui_impl(
                payment_url=payment_url,
                booking_id=booking_id,
                total_amount=total_amount,
                tour_name=tour_name,
                payment_method=payment_method
            )
        except Exception as e:
            return {"success": False, "error": f"Error generating payment UI: {str(e)}"}
    
    logger.info("✅ Booking tools registered (including payment tools)")


async def _create_payment_impl(booking_id: str, payment_method: str = "vnpay") -> Dict[str, Any]:
    """Create payment và generate VNPay URL"""
    try:
        supabase = get_supabase_client()
        payment_service = PaymentService(supabase)
        
        # Get client IP (default to 127.0.0.1 if not available in context)
        # In MCP context, we don't have direct access to request, so use default
        ip_addr = "127.0.0.1"
        
        # Call payment service
        result = await payment_service.create_payment(
            booking_id=booking_id,
            payment_method=payment_method,
            ip_addr=ip_addr
        )
        
        if result["EC"] != 0:
            return {
                "success": False,
                "error": result["EM"],
                "error_code": result["EC"]
            }
        
        payment_data = result["data"]
        payment_url = payment_data.get("payment_url")
        
        if not payment_url:
            return {
                "success": False,
                "error": "Payment URL not generated"
            }
        
        # Get booking details for response
        booking_res = supabase.table("bookings")\
            .select("*, tour_packages(package_name, destination, start_date, price)")\
            .eq("booking_id", booking_id)\
            .execute()
        
        booking = booking_res.data[0] if booking_res.data else {}
        pkg = booking.get('tour_packages', {})
        if isinstance(pkg, list) and pkg:
            pkg = pkg[0]
        elif not isinstance(pkg, dict):
            pkg = {}
        
        return {
            "success": True,
            "message": "Payment URL đã được tạo thành công. Bạn có thể thanh toán ngay.",
            "booking_id": booking_id,
            "payment_id": payment_data.get("payment_id"),
            "payment_url": payment_url,
            "payment_method": payment_method,
            "amount": payment_data.get("amount"),
            "booking_info": {
                "booking_id": booking_id,
                "tour_name": pkg.get('package_name', 'Unknown Tour'),
                "destination": pkg.get('destination', 'Unknown'),
                "total_amount": booking.get('total_amount'),
                "number_of_people": booking.get('number_of_people')
            }
        }
    except Exception as e:
        logger.error(f"Create payment error: {str(e)}")
        return {"success": False, "error": f"System error: {str(e)}"}


async def _generate_payment_ui_impl(
    payment_url: str,
    booking_id: str,
    total_amount: float,
    tour_name: str,
    payment_method: str = "vnpay"
) -> Dict[str, Any]:
    """Generate payment button UI component"""
    try:
        html = generate_payment_button_html(
            payment_url=payment_url,
            booking_id=booking_id,
            total_amount=total_amount,
            tour_name=tour_name,
            payment_method=payment_method
        )
        
        return {
            "success": True,
            "html": html,
            "ui_resource": {
                "uri": f"payment://{booking_id}",
                "mimeType": "text/html",
                "type": "payment_button",
                "metadata": {
                    "booking_id": booking_id,
                    "total_amount": total_amount,
                    "tour_name": tour_name,
                    "payment_method": payment_method
                }
            }
        }
    except Exception as e:
        logger.error(f"Generate payment UI error: {str(e)}")
        return {"success": False, "error": f"System error: {str(e)}"}


    
   
