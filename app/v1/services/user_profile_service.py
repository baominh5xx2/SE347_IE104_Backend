"""
User Profile Service
Business logic for user self-service profile operations
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from supabase import Client

from ..core.cloudinary_config import CloudinaryConfig

logger = logging.getLogger(__name__)


class UserProfileService:
    """Service for user profile self-service operations"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def get_my_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get current user's profile by user_id from JWT
        
        Args:
            user_id: User ID from JWT token
            
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            # Query user from database
            response = self.supabase.table("users").select(
                "user_id, email, full_name, phone_number, profile_picture, role, is_active, created_at, updated_at"
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
                    "updated_at": user.get("updated_at")
                }
            }
        except Exception as e:
            logger.error(f"Error getting user profile {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error retrieving user profile: {str(e)}",
                "data": None
            }
    
    def update_my_profile(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        profile_picture: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update current user's profile (allowlist fields only)
        
        Args:
            user_id: User ID from JWT token
            full_name: Optional new full name
            phone_number: Optional new phone number
            profile_picture: Optional new profile picture URL
            
        Returns:
            Dict with EC, EM, data keys
        """
        try:
            # Build update data (only provided fields)
            update_data = {
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if full_name is not None:
                update_data["full_name"] = full_name
            if phone_number is not None:
                update_data["phone_number"] = phone_number
            if profile_picture is not None:
                update_data["profile_picture"] = profile_picture
            
            # Check if any fields to update
            if len(update_data) == 1:  # Only updated_at
                return {
                    "EC": 1,
                    "EM": "No fields to update",
                    "data": None
                }
            
            # Update user profile
            response = self.supabase.table("users").update(update_data).eq("user_id", user_id).execute()
            
            if not response.data or len(response.data) == 0:
                return {
                    "EC": 1,
                    "EM": "User not found",
                    "data": None
                }
            
            # Return updated profile
            return self.get_my_profile(user_id)
            
        except Exception as e:
            logger.error(f"Error updating user profile {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error updating user profile: {str(e)}",
                "data": None
            }

    def upload_profile_picture(
        self,
        user_id: str,
        file_bytes: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Upload a profile picture to Cloudinary and persist the URL
        """
        try:
            upload_result = CloudinaryConfig.upload_image(
                file_content=file_bytes,
                filename=filename,
                folder="profile_pictures"
            )

            if not upload_result or not upload_result.get("url"):
                return {
                    "EC": 2,
                    "EM": "Failed to upload image",
                    "data": None
                }

            update_payload = {
                "profile_picture": upload_result["url"],
                "updated_at": datetime.utcnow().isoformat()
            }

            response = (
                self.supabase
                .table("users")
                .update(update_payload)
                .eq("user_id", user_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                return {
                    "EC": 1,
                    "EM": "User not found",
                    "data": None
                }

            return self.get_my_profile(user_id)

        except Exception as e:
            logger.error(f"Error uploading profile picture for {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error uploading profile picture: {str(e)}",
                "data": None
            }

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Change user password after verifying current password
        
        Args:
            user_id: User ID from JWT token
            current_password: Current password to verify
            new_password: New password to set
            
        Returns:
            Dict with EC, EM keys
        """
        try:
            import bcrypt
            
            # Get current user password hash
            response = self.supabase.table("users").select("password_hash").eq("user_id", user_id).execute()
            
            if not response.data or len(response.data) == 0:
                return {
                    "EC": 1,
                    "EM": "User not found"
                }
            
            stored_password = response.data[0].get("password_hash")
            
            # Verify current password
            if not bcrypt.checkpw(current_password.encode('utf-8'), stored_password.encode('utf-8')):
                return {
                    "EC": 1,
                    "EM": "Current password is incorrect"
                }
            
            # Hash new password
            new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Update password
            update_response = self.supabase.table("users").update({
                "password_hash": new_password_hash,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
            
            if not update_response.data or len(update_response.data) == 0:
                return {
                    "EC": 2,
                    "EM": "Failed to update password"
                }
            
            return {
                "EC": 0,
                "EM": "Password changed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error changing password for {user_id}: {str(e)}", exc_info=True)
            return {
                "EC": 2,
                "EM": f"Error changing password: {str(e)}"
            }


def get_user_profile_service() -> UserProfileService:
    """Dependency to get UserProfileService instance"""
    from ..core.supabase import get_supabase_client
    supabase = get_supabase_client()
    return UserProfileService(supabase)
