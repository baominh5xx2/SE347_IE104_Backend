"""
Admin User Management Service
Business logic for admin customer management operations
"""
import logging
import bcrypt
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from supabase import Client

logger = logging.getLogger(__name__)


class AdminUserService:
    """Service for admin user management operations"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.salt_rounds = 10
    
    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        salt = bcrypt.gensalt(rounds=self.salt_rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
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
    
    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """
        Delete user by ID (admin only)
        Only allows deletion if user has no related records (bookings, payments, reviews, chat_rooms)
        
        Args:
            user_id: User ID to delete
            
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            # First, check if user exists
            user_response = self.supabase.table("users").select("user_id, email, full_name").eq("user_id", user_id).execute()
            
            if not user_response.data or len(user_response.data) == 0:
                return {
                    "EC": 1,
                    "EM": "User not found",
                    "data": None
                }
            
            user = user_response.data[0]
            
            # Check for related records that would violate foreign key constraints
            # 1. Check bookings
            bookings_response = self.supabase.table("bookings").select("booking_id", count="exact").eq("user_id", user_id).limit(1).execute()
            bookings_count = bookings_response.count if hasattr(bookings_response, 'count') else len(bookings_response.data or [])
            
            if bookings_count > 0:
                return {
                    "EC": 3,
                    "EM": f"Cannot delete user: User has {bookings_count} booking(s). Please cancel or complete all bookings first.",
                    "data": None
                }
            
            # 2. Check payments
            payments_response = self.supabase.table("payments").select("payment_id", count="exact").eq("user_id", user_id).limit(1).execute()
            payments_count = payments_response.count if hasattr(payments_response, 'count') else len(payments_response.data or [])
            
            if payments_count > 0:
                return {
                    "EC": 3,
                    "EM": f"Cannot delete user: User has {payments_count} payment record(s). Please resolve all payment records first.",
                    "data": None
                }
            
            # 3. Check reviews
            reviews_response = self.supabase.table("reviews").select("review_id", count="exact").eq("user_id", user_id).limit(1).execute()
            reviews_count = reviews_response.count if hasattr(reviews_response, 'count') else len(reviews_response.data or [])
            
            if reviews_count > 0:
                return {
                    "EC": 3,
                    "EM": f"Cannot delete user: User has {reviews_count} review(s). Please delete all reviews first.",
                    "data": None
                }
            
            # 4. Check chat_rooms
            chat_rooms_response = self.supabase.table("chat_rooms").select("room_id", count="exact").eq("user_id", user_id).limit(1).execute()
            chat_rooms_count = chat_rooms_response.count if hasattr(chat_rooms_response, 'count') else len(chat_rooms_response.data or [])
            
            if chat_rooms_count > 0:
                return {
                    "EC": 3,
                    "EM": f"Cannot delete user: User has {chat_rooms_count} chat room(s). Please delete all chat rooms first.",
                    "data": None
                }
            
            # 5. Check otp_verifications (optional, but good to check)
            otp_response = self.supabase.table("otp_verifications").select("otp_id", count="exact").eq("user_id", user_id).limit(1).execute()
            otp_count = otp_response.count if hasattr(otp_response, 'count') else len(otp_response.data or [])
            
            if otp_count > 0:
                return {
                    "EC": 3,
                    "EM": f"Cannot delete user: User has {otp_count} OTP verification record(s). Please resolve all OTP records first.",
                    "data": None
                }
            
            # All checks passed - safe to delete
            delete_response = self.supabase.table("users").delete().eq("user_id", user_id).execute()
            
            if not delete_response.data:
                return {
                    "EC": 2,
                    "EM": "Failed to delete user",
                    "data": None
                }
            
            logger.info(f"Admin deleted user {user_id} ({user.get('email', 'N/A')})")
            
            return {
                "EC": 0,
                "EM": "User deleted successfully",
                "data": {
                    "user_id": user_id,
                    "email": user.get("email"),
                    "full_name": user.get("full_name")
                }
            }
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error deleting user: {str(e)}",
                "data": None
            }
    
    def create_user(
        self,
        email: str,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        password: Optional[str] = None,
        role: str = "user",
        is_active: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new user (admin only)
        
        Args:
            email: User email (required, must be unique)
            full_name: User full name (optional)
            phone_number: User phone number (optional)
            password: User password (optional, will generate random if not provided)
            role: User role (default: "user", can be "user" or "admin")
            is_active: Account active status (default: True)
            
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            # Check if email already exists
            existing_user = self.supabase.table("users").select("user_id, email").eq("email", email).execute()
            
            if existing_user.data and len(existing_user.data) > 0:
                return {
                    "EC": 1,
                    "EM": "Email already exists",
                    "data": None
                }
            
            # Generate random password if not provided
            import secrets
            import string
            if not password:
                # Generate random 12-character password
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for i in range(12))
            
            # Hash password
            hashed_password = self._hash_password(password)
            
            # Create user
            current_time = datetime.now(timezone.utc).isoformat()
            user_data = {
                "email": email,
                "full_name": full_name or email.split('@')[0],  # Use email prefix if no name provided
                "phone_number": phone_number,
                "password_hash": hashed_password,
                "role": role,
                "is_active": is_active,
                "is_activate": is_active,  # Legacy field
                "login_type": "TRADITIONAL",
                "security_2fa_enabled": False,
                "created_at": current_time,
                "updated_at": current_time,
                "last_access_time": None
            }
            
            result = self.supabase.table("users").insert(user_data).execute()
            
            if not result.data or len(result.data) == 0:
                return {
                    "EC": 2,
                    "EM": "Failed to create user",
                    "data": None
                }
            
            user = result.data[0]
            logger.info(f"Admin created user {user['user_id']} ({email})")
            
            return {
                "EC": 0,
                "EM": "User created successfully",
                "data": {
                    "user_id": str(user["user_id"]),
                    "email": user.get("email"),
                    "full_name": user.get("full_name"),
                    "phone_number": user.get("phone_number"),
                    "role": user.get("role", "user"),
                    "is_active": user.get("is_active", True),
                    "password": password  # Return generated password for admin to share with user
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error creating user: {str(e)}",
                "data": None
            }
    
    def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user information (admin only)
        
        Args:
            user_id: User ID to update
            email: New email (optional, must be unique if provided)
            full_name: New full name (optional)
            phone_number: New phone number (optional)
            role: New role (optional, must be "user" or "admin")
            is_active: New active status (optional)
            password: New password (optional, will be hashed)
            
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            # Check if user exists
            user_response = self.supabase.table("users").select("user_id, email").eq("user_id", user_id).execute()
            
            if not user_response.data or len(user_response.data) == 0:
                return {
                    "EC": 1,
                    "EM": "User not found",
                    "data": None
                }
            
            # Check if email is being changed and if new email already exists
            if email:
                existing_user = self.supabase.table("users").select("user_id, email").eq("email", email).execute()
                if existing_user.data:
                    existing_user_id = str(existing_user.data[0]["user_id"])
                    if existing_user_id != user_id:
                        return {
                            "EC": 1,
                            "EM": "Email already exists",
                            "data": None
                        }
            
            # Validate role if provided
            if role and role not in ["user", "admin"]:
                return {
                    "EC": 2,
                    "EM": "Invalid role. Must be 'user' or 'admin'",
                    "data": None
                }
            
            # Build update data
            update_data = {
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if email is not None:
                update_data["email"] = email
            if full_name is not None:
                update_data["full_name"] = full_name
            if phone_number is not None:
                update_data["phone_number"] = phone_number
            if role is not None:
                update_data["role"] = role
            if is_active is not None:
                update_data["is_active"] = is_active
                update_data["is_activate"] = is_active  # Legacy field
            if password is not None:
                update_data["password_hash"] = self._hash_password(password)
            
            # Update user
            result = self.supabase.table("users").update(update_data).eq("user_id", user_id).execute()
            
            if not result.data or len(result.data) == 0:
                return {
                    "EC": 2,
                    "EM": "Failed to update user",
                    "data": None
                }
            
            updated_user = result.data[0]
            logger.info(f"Admin updated user {user_id}")
            
            return {
                "EC": 0,
                "EM": "User updated successfully",
                "data": {
                    "user_id": str(updated_user["user_id"]),
                    "email": updated_user.get("email"),
                    "full_name": updated_user.get("full_name"),
                    "phone_number": updated_user.get("phone_number"),
                    "role": updated_user.get("role", "user"),
                    "is_active": updated_user.get("is_active", True),
                    "updated_at": updated_user.get("updated_at")
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error updating user: {str(e)}",
                "data": None
            }


def get_admin_user_service() -> AdminUserService:
    """Dependency to get AdminUserService instance"""
    from ..core.supabase import get_supabase_client
    supabase = get_supabase_client()
    return AdminUserService(supabase)
