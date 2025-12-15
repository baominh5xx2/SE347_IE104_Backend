"""
Admin User Management Service
Business logic for admin customer management operations
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from supabase import Client

logger = logging.getLogger(__name__)


class AdminUserService:
    """Service for admin user management operations"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile by ID
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            # Query user from database
            response = self.supabase.table("users").select(
                "user_id, email, full_name, phone_number, profile_picture, role, is_active, created_at, updated_at, last_access_time"
            ).eq("user_id", user_id).execute()
            
            if not response.data or len(response.data) == 0:
                return {
                    "EC": 1,
                    "EM": "User not found",
                    "data": None
                }
            
            user = response.data[0]
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "user_id": str(user["user_id"]),
                    "email": user.get("email", ""),
                    "full_name": user.get("full_name"),
                    "phone_number": user.get("phone_number"),
                    "profile_picture": user.get("profile_picture"),
                    "role": user.get("role", "user"),
                    "is_active": user.get("is_active", True),
                    "created_at": user.get("created_at"),
                    "updated_at": user.get("updated_at"),
                    "last_access_time": user.get("last_access_time")
                }
            }
        except Exception as e:
            logger.error(f"Error getting user profile {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error retrieving user profile: {str(e)}",
                "data": None
            }
    
    def get_user_bookings(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        sort: str = "created_at_desc"
    ) -> Dict[str, Any]:
        """
        Get user bookings with pagination and filters
        
        Args:
            user_id: User ID
            page: Page number (>=1)
            limit: Items per page (1-100)
            status: Optional status filter
            from_date: Optional start date filter (ISO format)
            to_date: Optional end date filter (ISO format)
            sort: Sort order
            
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            # Build query
            query = self.supabase.table("bookings").select(
                """
                booking_id,
                user_id,
                package_id,
                number_of_people,
                total_amount,
                status,
                created_at,
                tour_packages!inner(package_name, start_date, end_date)
                """,
                count="exact"
            ).eq("user_id", user_id)
            
            # Apply filters
            if status:
                query = query.eq("status", status)
            if from_date:
                query = query.gte("created_at", from_date)
            if to_date:
                query = query.lte("created_at", to_date)
            
            # Apply sorting
            if sort == "start_date_desc":
                query = query.order("tour_packages(start_date)", desc=True)
            elif sort == "start_date_asc":
                query = query.order("tour_packages(start_date)", desc=False)
            else:  # created_at_desc (default)
                query = query.order("created_at", desc=True)
            
            # Apply pagination
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)
            
            response = query.execute()
            
            # Transform data
            items = []
            for booking in response.data:
                package = booking.get("tour_packages", {})
                items.append({
                    "booking_id": booking.get("booking_id"),
                    "user_id": str(booking.get("user_id")),
                    "package_id": str(booking.get("package_id")),
                    "package_name": package.get("package_name", ""),
                    "start_date": package.get("start_date"),
                    "end_date": package.get("end_date"),
                    "number_of_people": booking.get("number_of_people", 0),
                    "total_price": float(booking.get("total_amount", 0)),
                    "currency": "VND",
                    "status": booking.get("status", ""),
                    "created_at": booking.get("created_at")
                })
            
            total = response.count or 0
            total_pages = (total + limit - 1) // limit if total > 0 else 0
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "items": items,
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": total_pages
                }
            }
        except Exception as e:
            logger.error(f"Error getting user bookings {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error retrieving user bookings: {str(e)}",
                "data": None
            }
    
    def set_user_active(
        self,
        user_id: str,
        is_active: bool,
        reason: Optional[str] = None,
        admin_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user active status
        
        Args:
            user_id: User ID
            is_active: New active status
            reason: Optional reason for change
            admin_id: Admin user ID performing the action
            
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            # Update user status
            response = self.supabase.table("users").update({
                "is_active": is_active,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
            
            if not response.data:
                return {
                    "EC": 1,
                    "EM": "User not found",
                    "data": None
                }
            
            # Log the action (optional, for audit trail)
            if reason:
                logger.info(
                    f"Admin {admin_id} {'disabled' if not is_active else 'enabled'} "
                    f"user {user_id}. Reason: {reason}"
                )
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "user_id": user_id,
                    "is_active": is_active
                }
            }
        except Exception as e:
            logger.error(f"Error updating user status {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error updating user status: {str(e)}",
                "data": None
            }
    
    def get_user_summary(
        self,
        user_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive user summary with KPIs and recent activities
        
        Args:
            user_id: User ID
            from_date: Optional start date for KPI filtering
            to_date: Optional end date for KPI filtering
            
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            # Get user profile
            profile_result = self.get_user_profile(user_id)
            if profile_result["EC"] != 0:
                return profile_result
            
            user_profile = profile_result["data"]
            
            # Build booking query for KPIs
            booking_query = self.supabase.table("bookings").select(
                "booking_id, status, total_amount, created_at"
            ).eq("user_id", user_id)
            
            if from_date:
                booking_query = booking_query.gte("created_at", from_date)
            if to_date:
                booking_query = booking_query.lte("created_at", to_date)
            
            bookings_response = booking_query.execute()
            bookings = bookings_response.data or []
            
            # Calculate KPIs
            total_bookings = len(bookings)
            completed_tours = len([b for b in bookings if b.get("status") == "completed"])
            cancelled_bookings = len([b for b in bookings if b.get("status") == "cancelled"])
            pending_bookings = len([b for b in bookings if b.get("status") == "pending"])
            confirmed_bookings = len([b for b in bookings if b.get("status") == "confirmed"])
            
            # Get payments sum
            payment_query = self.supabase.table("payments").select(
                "amount, payment_status"
            ).eq("user_id", user_id).in_("payment_status", ["completed"])
            
            if from_date:
                payment_query = payment_query.gte("paid_at", from_date)
            if to_date:
                payment_query = payment_query.lte("paid_at", to_date)
            
            payments_response = payment_query.execute()
            payments = payments_response.data or []
            
            total_paid_amount = sum(float(p.get("amount", 0)) for p in payments)
            
            # Get recent bookings (last 10)
            recent_bookings_response = self.supabase.table("bookings").select(
                """
                booking_id,
                package_id,
                status,
                total_amount,
                created_at,
                tour_packages!inner(package_name)
                """
            ).eq("user_id", user_id).order("created_at", desc=True).limit(10).execute()
            
            recent_bookings = []
            for booking in (recent_bookings_response.data or []):
                package = booking.get("tour_packages", {})
                recent_bookings.append({
                    "booking_id": booking.get("booking_id"),
                    "package_id": str(booking.get("package_id")),
                    "package_name": package.get("package_name", ""),
                    "status": booking.get("status", ""),
                    "total_price": float(booking.get("total_amount", 0)),
                    "created_at": booking.get("created_at")
                })
            
            # Get recent payments (last 10)
            recent_payments_response = self.supabase.table("payments").select(
                "payment_id, amount, payment_status, paid_at"
            ).eq("user_id", user_id).order("paid_at", desc=True).limit(10).execute()
            
            recent_payments = [
                {
                    "payment_id": p.get("payment_id"),
                    "amount": float(p.get("amount", 0)),
                    "status": p.get("payment_status", ""),
                    "paid_at": p.get("paid_at")
                }
                for p in (recent_payments_response.data or [])
            ]
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "user": user_profile,
                    "kpi": {
                        "total_paid_amount": total_paid_amount,
                        "currency": "VND",
                        "total_bookings": total_bookings,
                        "completed_tours": completed_tours,
                        "cancelled_bookings": cancelled_bookings,
                        "pending_bookings": pending_bookings,
                        "confirmed_bookings": confirmed_bookings
                    },
                    "recent": {
                        "recent_bookings": recent_bookings,
                        "recent_payments": recent_payments
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error getting user summary {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error retrieving user summary: {str(e)}",
                "data": None
            }
    
    def get_user_chat_history(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's chat history grouped by chat rooms
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            # Get all chat rooms for user
            rooms_response = self.supabase.table("chat_rooms").select(
                "room_id, title, created_at, updated_at"
            ).eq("user_id", user_id).order("updated_at", desc=True).execute()
            
            rooms_data = []
            
            for room in (rooms_response.data or []):
                room_id = room.get("room_id")
                
                # Get messages for this room (last 50 messages)
                messages_response = self.supabase.table("chat_history").select(
                    "message_id, role, content, intent, created_at"
                ).eq("conversation_id", room_id).order("created_at", desc=False).limit(50).execute()
                
                messages = [
                    {
                        "message_id": str(msg.get("message_id")),
                        "role": msg.get("role", ""),
                        "content": msg.get("content", ""),
                        "intent": msg.get("intent"),
                        "created_at": msg.get("created_at")
                    }
                    for msg in (messages_response.data or [])
                ]
                
                # Get total message count for this room
                count_response = self.supabase.table("chat_history").select(
                    "message_id", count="exact"
                ).eq("conversation_id", room_id).execute()
                
                rooms_data.append({
                    "room_id": room_id,
                    "title": room.get("title"),
                    "created_at": room.get("created_at"),
                    "updated_at": room.get("updated_at"),
                    "message_count": count_response.count or 0,
                    "messages": messages
                })
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "user_id": user_id,
                    "total_rooms": len(rooms_data),
                    "rooms": rooms_data
                }
            }
        except Exception as e:
            logger.error(f"Error getting user chat history {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error retrieving user chat history: {str(e)}",
                "data": None
            }
    
    def get_all_users(self) -> Dict[str, Any]:
        """
        Get all users in the database (admin only)
        
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            response = self.supabase.table("users").select(
                "user_id, email, full_name, phone_number, profile_picture, role, is_active, created_at, updated_at, last_access_time"
            ).order("created_at", desc=True).execute()
            
            users = []
            for user in (response.data or []):
                users.append({
                    "user_id": str(user["user_id"]),
                    "email": user.get("email", ""),
                    "full_name": user.get("full_name"),
                    "phone_number": user.get("phone_number"),
                    "profile_picture": user.get("profile_picture"),
                    "role": user.get("role", "user"),
                    "is_active": user.get("is_active", True),
                    "created_at": user.get("created_at"),
                    "updated_at": user.get("updated_at"),
                    "last_access_time": user.get("last_access_time")
                })
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "users": users,
                    "total": len(users)
                }
            }
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error retrieving users: {str(e)}",
                "data": None
            }


def get_admin_user_service() -> AdminUserService:
    """Dependency to get AdminUserService instance"""
    from ..core.supabase import get_supabase_client
    supabase = get_supabase_client()
    return AdminUserService(supabase)
