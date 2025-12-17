"""
Notification Service
Handles user notifications for bookings, tours, payments
"""
import logging
from typing import Dict, Any, Optional, List
from supabase import Client

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing user notifications"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize NotificationService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    async def create_notification(
        self,
        user_id: str,
        type: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new notification for a user
        
        Args:
            user_id: UUID of the user
            type: Notification type ('tour_cancelled', 'booking_cancelled', etc)
            title: Notification title
            message: Notification message
            metadata: Optional metadata (package_id, booking_id, etc)
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            notification_data = {
                "user_id": user_id,
                "type": type,
                "title": title,
                "message": message,
                "metadata": metadata or {},
                "is_read": False
            }
            
            result = self.supabase.table('notifications') \
                .insert(notification_data) \
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Failed to create notification",
                    "data": None
                }
            
            logger.info(f"Created notification for user {user_id}: {type}")
            
            return {
                "EC": 0,
                "EM": "Notification created successfully",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error creating notification: {str(e)}",
                "data": None
            }
    
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: Optional[int] = 50,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get notifications for a user
        
        Args:
            user_id: UUID of the user
            unread_only: If True, only return unread notifications
            limit: Maximum number of notifications to return
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            query = self.supabase.table('notifications') \
                .select('*', count='exact') \
                .eq('user_id', user_id)
            
            if unread_only:
                query = query.eq('is_read', False)
            
            if limit:
                query = query.limit(limit)
            
            if offset:
                query = query.offset(offset)
            
            query = query.order('created_at', desc=True)
            
            result = query.execute()
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": result.data,
                "total": result.count
            }
            
        except Exception as e:
            logger.error(f"Error getting notifications for user {user_id}: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving notifications: {str(e)}",
                "data": None,
                "total": 0
            }
    
    async def mark_as_read(self, notification_id: str) -> Dict[str, Any]:
        """
        Mark a notification as read
        
        Args:
            notification_id: UUID of the notification
            
        Returns:
            Dict with EC and EM
        """
        try:
            result = self.supabase.table('notifications') \
                .update({"is_read": True}) \
                .eq('notification_id', notification_id) \
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Notification not found"
                }
            
            return {
                "EC": 0,
                "EM": "Notification marked as read"
            }
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error: {str(e)}"
            }
    
    async def mark_all_as_read(self, user_id: str) -> Dict[str, Any]:
        """
        Mark all notifications as read for a user
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dict with EC, EM, and updated count
        """
        try:
            result = self.supabase.table('notifications') \
                .update({"is_read": True}) \
                .eq('user_id', user_id) \
                .eq('is_read', False) \
                .execute()
            
            updated_count = len(result.data) if result.data else 0
            
            return {
                "EC": 0,
                "EM": f"Marked {updated_count} notifications as read",
                "updated": updated_count
            }
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error: {str(e)}",
                "updated": 0
            }
    
    async def get_unread_count(self, user_id: str) -> Dict[str, Any]:
        """
        Get count of unread notifications for a user
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dict with EC, EM, and count
        """
        try:
            result = self.supabase.table('notifications') \
                .select('*', count='exact') \
                .eq('user_id', user_id) \
                .eq('is_read', False) \
                .execute()
            
            return {
                "EC": 0,
                "EM": "Success",
                "count": result.count or 0
            }
            
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error: {str(e)}",
                "count": 0
            }
