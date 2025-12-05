"""
Booking Service
Handles booking CRUD operations
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from supabase import Client
from .promotion_service import PromotionService

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
            
            # Apply promotion if provided
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
                "status": "pending",
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
            
            # Recalculate total_amount if number_of_people or promotion_id changed
            if "number_of_people" in update_data or "promotion_id" in update_data:
                # Get the final number of people (new or old)
                final_people = update_data.get('number_of_people', old_booking['number_of_people'])
                
                # Calculate original amount
                original_amount = package['price'] * final_people
                final_amount = original_amount
                
                # Check promotion
                promotion_id = update_data.get('promotion_id', old_booking.get('promotion_id'))
                
                # If explicitly setting promotion_id to None, remove discount
                if "promotion_id" in update_data and update_data['promotion_id'] is None:
                    promotion_id = None
                    update_data['promotion_id'] = None
                elif "promotion_id" in update_data and update_data['promotion_id'] is not None:
                    # Convert UUID to string for database
                    update_data['promotion_id'] = str(update_data['promotion_id'])
                    promotion_id = update_data['promotion_id']
                
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
    
    async def delete_booking(self, booking_id: str) -> Dict[str, Any]:
        """
        Delete a booking (and restore package slots)
        
        Args:
            booking_id: UUID of the booking
            
        Returns:
            Dict with EC and EM
        """
        try:
            # Get booking data first
            existing = await self.get_booking_by_id(booking_id)
            if existing["EC"] != 0:
                return existing
            
            booking = existing["data"]
            
            # Delete booking
            result = self.supabase.table('bookings') \
                .delete() \
                .eq('booking_id', booking_id) \
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Failed to delete booking"
                }
            
            # Restore package slots if booking was pending or confirmed
            if booking['status'] in ['pending', 'confirmed']:
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
            
            logger.info(f"Deleted booking {booking_id}")
            
            return {
                "EC": 0,
                "EM": "Booking deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting booking {booking_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error deleting booking: {str(e)}"
            }
