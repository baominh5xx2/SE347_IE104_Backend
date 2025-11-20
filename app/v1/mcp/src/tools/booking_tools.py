"""
MCP Tools - Booking Tools
Interactive booking collection và management
"""
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from src.resources.supabase import get_supabase_client

# Logger
logger = logging.getLogger(__name__)


async def _create_booking_impl(
    user_phone: str,
    package_id: str,
    number_of_people: int,
    special_requests: Optional[str] = None
) -> Dict[str, Any]:
    """
    Implementation of create_booking tool.
    
    This is separated from the decorator for easier testing.
    """
    try:
        supabase = get_supabase_client()
        
        # Validate required parameters with clear messages for LLM
        if not package_id:
            return {
                "success": False,
                "error": "Missing required parameter: package_id. Please get package_id from tour recommendation results before creating booking.",
                "missing_parameter": "package_id",
                "action": "Get package_id from recommendation results and call create_booking again."
            }
        
        if not number_of_people or number_of_people <= 0:
            return {
                "success": False,
                "error": f"Invalid number_of_people: {number_of_people}. Must be a positive integer greater than 0.",
                "invalid_parameter": "number_of_people",
                "received": number_of_people,
                "action": "Ask user for correct number of people and call create_booking again."
            }
        
        # 1. Check if user exists, nếu không thì tạo mới
        user_response = supabase.table("users")\
            .select("*")\
            .eq("phone_number", user_phone)\
            .execute()
        
        if not user_response.data or len(user_response.data) == 0:
            # Auto-create user with phone only
            new_user = {
                "phone_number": user_phone,
                "full_name": f"Khách hàng {user_phone[-4:]}",  # Tạm thời dùng 4 số cuối
                "email": f"{user_phone}@temp.com"
            }
            user_response = supabase.table("users").insert(new_user).execute()
            
            if not user_response.data or len(user_response.data) == 0:
                logger.error(f"❌ Failed to create user for phone {user_phone}")
                return {
                    "success": False,
                    "error": "Không thể tạo user trong database"
                }
            
            user = user_response.data[0]
            logger.info(f"✅ Created new user {user['user_id']} for phone {user_phone}")
        else:
            user = user_response.data[0]
            logger.debug(f"Found existing user {user['user_id']} for phone {user_phone}")
        
        # 2. Get tour package by package_id (from parameter)
        logger.debug(f"🔍 Looking up package {package_id} in database")
        package_response = supabase.table("tour_packages")\
            .select("*")\
            .eq("package_id", package_id)\
            .eq("is_active", True)\
            .execute()
        
        if not package_response.data or len(package_response.data) == 0:
            logger.warning(f"⚠️ Package {package_id} not found or inactive")
            return {
                "success": False,
                "error": f"Tour package not found: '{package_id}'. Package may be inactive or ID is incorrect.",
                "package_id_provided": package_id,
                "action": "Verify package_id from recommendation results. Package may no longer be available."
            }
        
        package = package_response.data[0]
        logger.debug(f"✅ Found package: {package.get('package_name', package_id)} with {package.get('available_slots', 0)} available slots")
        
        # 3. Check available slots
        if package['available_slots'] < number_of_people:
            return {
                "success": False,
                "error": f"Insufficient slots: Tour only has {package['available_slots']} available slots, but {number_of_people} people requested.",
                "available_slots": package['available_slots'],
                "requested": number_of_people,
                "action": f"Suggest booking for {package['available_slots']} people or less, or recommend another available tour package."
            }
        
        # 4. Calculate total amount
        total_amount = float(package['price']) * number_of_people
        
        # 5. Create booking with special_requests
        booking_data = {
            "user_id": user['user_id'],
            "package_id": package_id,
            "number_of_people": number_of_people,
            "total_amount": total_amount,
            "contact_name": user.get('full_name', user_phone),
            "contact_phone": user_phone,
            "special_requests": special_requests or "",  # Use provided special_requests
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 5. Create booking
        logger.info(f"📝 Creating booking in database: user_phone={user_phone}, package_id={package_id}, number_of_people={number_of_people}")
        logger.debug(f"Booking data: {booking_data}")
        
        try:
            booking_response = supabase.table("bookings").insert(booking_data).execute()
            
            # Supabase execute() automatically commits - verify response
            # Response should have .data array if successful
            if not hasattr(booking_response, 'data') or not booking_response.data or len(booking_response.data) == 0:
                logger.error(f"❌ Database insert failed - booking_response.data is empty or None")
                logger.error(f"Response object: {type(booking_response)}")
                logger.error(f"Response attributes: {dir(booking_response)}")
                
                # Try to get error from response
                error_msg = "Unknown error"
                if hasattr(booking_response, 'error'):
                    error_msg = str(booking_response.error)
                elif hasattr(booking_response, 'message'):
                    error_msg = str(booking_response.message)
                
                return {
                    "success": False,
                    "error": f"Không thể tạo booking - database insert failed: {error_msg}",
                    "error_type": "DatabaseError",
                    "action": "Please check database connection, permissions, and try again."
                }
            
            booking = booking_response.data[0]
            booking_id = booking.get('booking_id', 'unknown')
            
            # Verify booking_id exists (proves data was saved)
            if not booking_id or booking_id == 'unknown':
                logger.error(f"❌ Booking created but missing booking_id: {booking}")
                return {
                    "success": False,
                    "error": "Không thể tạo booking - missing booking_id in response",
                    "error_type": "DatabaseError",
                    "response_data": booking
                }
            
            logger.info(f"✅ Booking {booking_id} CREATED AND SAVED in database")
            logger.info(f"   Booking details: user_id={booking.get('user_id')}, package_id={booking.get('package_id')}, status={booking.get('status')}")
            logger.debug(f"Full booking data: {booking}")
            
        except Exception as e:
            logger.error(f"❌ Exception during booking insert: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": f"Không thể tạo booking - database error: {str(e)}",
                "error_type": type(e).__name__,
                "action": "Please check database connection and try again."
            }
        
        # 6. Update available slots - IMPORTANT: Must commit to database
        new_slots = package['available_slots'] - number_of_people
        logger.info(f"📝 Updating available_slots for package {package_id}: {package['available_slots']} -> {new_slots}")
        
        try:
            update_response = supabase.table("tour_packages")\
                .update({"available_slots": new_slots})\
                .eq("package_id", package_id)\
                .execute()
            
            # Verify update was successful - Supabase execute() auto-commits
            if not hasattr(update_response, 'data') or not update_response.data or len(update_response.data) == 0:
                # Booking was created but slots update failed - this is a data inconsistency issue
                logger.warning(f"⚠️ Booking {booking_id} created but failed to update available_slots for package {package_id}")
                logger.warning(f"Update response: {type(update_response)} - {update_response}")
                # Could optionally rollback booking here, but for now just log the issue
            else:
                updated_package = update_response.data[0]
                updated_slots = updated_package.get('available_slots', 'unknown')
                logger.info(f"✅ Updated available_slots for package {package_id}: {package['available_slots']} -> {new_slots} (verified: {updated_slots})")
                logger.debug(f"Updated package: {updated_package}")
        except Exception as e:
            logger.error(f"❌ Exception during slots update: {type(e).__name__}: {str(e)}")
            # Log error but don't fail booking since booking was already created
            import traceback
            logger.error(traceback.format_exc())
        
        # Final verification - query back from database to confirm
        try:
            verify_response = supabase.table("bookings")\
                .select("booking_id, user_id, package_id, status")\
                .eq("booking_id", booking_id)\
                .execute()
            
            if verify_response.data and len(verify_response.data) > 0:
                verified_booking = verify_response.data[0]
                logger.info(f"✅ VERIFIED: Booking {booking_id} EXISTS in database")
                logger.info(f"   Verified: user_id={verified_booking.get('user_id')}, package_id={verified_booking.get('package_id')}, status={verified_booking.get('status')}")
            else:
                logger.error(f"❌ WARNING: Booking {booking_id} NOT FOUND when verifying in database!")
        except Exception as e:
            logger.warning(f"⚠️ Could not verify booking in database: {str(e)}")
        
        logger.info(f"✅ Booking {booking_id} successfully saved to database") 
        
        # Skip FalkorDB for now to prevent timeouts
        falkordb_result = {"success": False, "disabled": True}
        
        # 8. Return success with full details
        return {
            "success": True,
            "booking_id": booking['booking_id'],
            "message": "✅ ĐẶT TOUR THÀNH CÔNG!",
            "saved_to_falkordb": falkordb_result.get('success', False) if 'falkordb_result' in locals() else False,
            "confirmation": {
                "booking_id": booking['booking_id'],
                "user_name": user['full_name'],
                "user_phone": user['phone_number'],
                "tour_name": package['package_name'],
                "destination": package['destination'],
                "tour_dates": f"{package['start_date']} đến {package['end_date']}",
                "duration": f"{package['duration_days']} ngày {package['duration_days']-1} đêm",
                "number_of_people": number_of_people,
                "total_amount": total_amount,
                "contact_name": booking['contact_name'],
                "contact_phone": booking['contact_phone'],
                "special_requests": special_requests or "Không có",
                "status": "Đang chờ xác nhận",
                "next_steps": [
                    "Chúng tôi sẽ liên hệ với bạn qua số điện thoại đã cung cấp trong vòng 24h",
                    "Vui lòng chuẩn bị thanh toán cọc 30% tổng giá trị tour",
                    "Còn lại 70% sẽ thanh toán trước ngày khởi hành 3 ngày"
                ]
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create booking: {str(e)}",
            "error_type": type(e).__name__,
            "action": "Please verify all information is correct and try again, or contact support if the issue persists."
        }


def register_booking_tools(mcp: FastMCP):
    """Register booking-related tools"""
    
    @mcp.tool()
    async def create_booking(
        user_phone: str,
        package_id: str,
        number_of_people: int,
        special_requests: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new tour booking for a user.
        
        ⚠️ CRITICAL: package_id MUST be the EXACT UUID from search_tour_packages results!
        DO NOT make up package IDs like "pkg_nhatrang_1" or "tour_dalat_3days"!
        
        THIS TOOL AUTOMATICALLY HANDLES ALL LOGIC:
        - Finds or creates user account if needed
        - Validates tour package and availability
        - Checks available slots
        - Calculates total amount
        - Creates booking and updates inventory
        
        WORKFLOW:
        1. First call search_tour_packages to find tours
        2. Get the package_id (UUID format) from search results
        3. Then call create_booking with that EXACT package_id
        
        YOU ONLY NEED TO: Collect these information from user and call this tool:
        - user_phone: User's phone number
        - package_id: UUID from search results (NOT a made-up string!)
        - number_of_people: Number of people traveling
        - special_requests: Optional special requests
        
        Args:
            user_phone (str): User's phone number. Example: "0912345678"
            package_id (str): **IMPORTANT**: UUID of tour package from search/recommendation results.
                              MUST be the EXACT package_id value returned by search_tour_packages tool.
                              Example: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
                              DO NOT make up or modify this ID - use the exact value from search results!
            number_of_people (int): Number of people traveling. Must be > 0. Example: 2
            special_requests (str, optional): Special requests or requirements. Example: "Window seat preferred"
        
        Returns:
            Dict with:
            - success (bool): Whether booking was created successfully
            - booking_id (str): Booking ID if successful
            - message (str): Success or error message
            - confirmation (dict): Complete booking confirmation with all details
            - error (str): Clear error message if failed (with suggestions on what to do)
        
        Example success response:
        {
            "success": True,
            "booking_id": "booking_abc123",
            "message": "✅ ĐẶT TOUR THÀNH CÔNG!",
            "confirmation": {...}
        }
        """
        return await _create_booking_impl(user_phone, package_id, number_of_people, special_requests)
    
   
