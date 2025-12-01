"""
MCP Tools - Booking Tools
Interactive booking collection và management
"""
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from app.v1.core.supabase import get_supabase_client
from pydantic import ValidationError
from app.v1.mcp.src.schema import (
    CreateBookingInput,
    UpdateBookingInput,
    DeleteBookingInput,
    GetUserBookingsInput
)

# Logger
logger = logging.getLogger(__name__)


async def _create_booking_impl(
    user_phone: str,
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

        # 3. Create Booking
        total_amount = float(package['price']) * number_of_people
        booking_data = {
            "user_id": user['user_id'],
            "package_id": package_id,
            "number_of_people": number_of_people,
            "total_amount": total_amount,
            "contact_name": user.get('full_name', user_phone),
            "contact_phone": user_phone,
            "special_requests": special_requests or "",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        booking_res = supabase.table("bookings").insert(booking_data).execute()
        if not booking_res.data:
             return {"success": False, "error": "Database error: Failed to insert booking."}
        
        booking = booking_res.data[0]

        # 4. Update Slots
        new_slots = package['available_slots'] - number_of_people
        supabase.table("tour_packages").update({"available_slots": new_slots}).eq("package_id", package_id).execute()

        # 5. Return Success
        return {
            "success": True,
            "booking_id": booking['booking_id'],
            "message": "✅ ĐẶT TOUR THÀNH CÔNG!",
            "confirmation": {
                "booking_id": booking['booking_id'],
                "tour_name": package['package_name'],
                "destination": package['destination'],
                "start_date": package['start_date'],
                "number_of_people": number_of_people,
                "total_amount": total_amount,
                "status": "pending",
                "contact_phone": user_phone
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
        package_id: str,
        number_of_people: int,
        special_requests: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new tour booking for a user.
        """
        try:
            validated = CreateBookingInput(
                user_phone=user_phone,
                package_id=package_id,
                number_of_people=number_of_people,
                special_requests=special_requests,
                user_id=user_id
            )
            return await _create_booking_impl(
                user_phone=validated.user_phone,
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
    
   
