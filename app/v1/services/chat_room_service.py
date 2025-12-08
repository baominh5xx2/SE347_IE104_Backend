"""
Chat Room Service
Service để quản lý chat rooms và messages
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from supabase import Client

logger = logging.getLogger(__name__)


class ChatRoomService:
    """Service để quản lý chat rooms và messages"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize ChatRoomService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    def create_room(self, user_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Tạo chat room mới
        
        Args:
            user_id: ID của user
            title: Tiêu đề room (optional, sẽ auto-generate nếu không có)
            
        Returns:
            Dict với room data hoặc error
        """
        try:
            room_data = {
                "user_id": user_id,
                "title": title or "Cuộc trò chuyện mới",
                "is_archived": False,
                "metadata": {}
            }
            
            result = self.supabase.table('chat_rooms').insert(room_data).execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Failed to create chat room",
                    "data": None
                }
            
            room = result.data[0]
            logger.info(f"Created chat room {room['room_id']} for user {user_id}")
            
            return {
                "EC": 0,
                "EM": "Chat room created successfully",
                "data": room
            }
            
        except Exception as e:
            logger.error(f"Error creating chat room: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error creating chat room: {str(e)}",
                "data": None
            }
    
    def get_user_rooms(
        self, 
        user_id: str, 
        archived: Optional[bool] = False,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Lấy danh sách chat rooms của user
        
        Args:
            user_id: ID của user
            archived: Filter theo archived status (None = all, True = archived only, False = not archived)
            limit: Số lượng rooms tối đa
            offset: Offset cho pagination
            
        Returns:
            Dict với list rooms và metadata
        """
        try:
            query = self.supabase.table('chat_rooms').select("*").eq('user_id', user_id)
            
            if archived is not None:
                query = query.eq('is_archived', archived)
            
            # Get total count
            count_query = self.supabase.table('chat_rooms').select("*", count="exact").eq('user_id', user_id)
            if archived is not None:
                count_query = count_query.eq('is_archived', archived)
            count_result = count_query.execute()
            total = count_result.count if hasattr(count_result, 'count') else 0
            
            # Get rooms with pagination
            result = query.order('updated_at', desc=True).limit(limit).offset(offset).execute()
            
            rooms = result.data or []
            
            if not rooms:
                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": [],
                    "total": total
                }
            
            # Tối ưu: Lấy tất cả room_ids để query một lần
            room_ids = [room['room_id'] for room in rooms]
            
            # Tối ưu: Query message counts và last messages trong batch
            # Sử dụng IN query thay vì loop
            msg_counts = {}
            last_messages = {}
            
            try:
                # Get message counts cho tất cả rooms trong 1 query bằng cách group by
                # Supabase không hỗ trợ RPC tốt, nên dùng cách khác
                # Query tất cả messages của các rooms này và group by
                all_messages_result = self.supabase.table('chat_history')\
                    .select("room_id")\
                    .in_('room_id', room_ids)\
                    .execute()
                
                # Count messages per room
                for msg in (all_messages_result.data or []):
                    room_id = msg['room_id']
                    msg_counts[room_id] = msg_counts.get(room_id, 0) + 1
                
                # Set 0 cho rooms không có messages
                for room_id in room_ids:
                    if room_id not in msg_counts:
                        msg_counts[room_id] = 0
                
            except Exception as e:
                logger.warning(f"Error getting message counts: {str(e)}")
                # Fallback: set all to 0
                for room_id in room_ids:
                    msg_counts[room_id] = 0
            
            try:
                # Get last messages - query tất cả và filter trong Python
                # Hoặc dùng window function nếu Supabase hỗ trợ
                # Tạm thời query batch và sort trong code
                all_last_messages_result = self.supabase.table('chat_history')\
                    .select("room_id, content, created_at")\
                    .in_('room_id', room_ids)\
                    .order('created_at', desc=True)\
                    .execute()
                
                # Group by room_id và lấy message đầu tiên (mới nhất) của mỗi room
                seen_rooms = set()
                for msg in (all_last_messages_result.data or []):
                    room_id = msg['room_id']
                    if room_id not in seen_rooms:
                        last_messages[room_id] = {
                            'content': msg.get('content'),
                            'created_at': msg.get('created_at')
                        }
                        seen_rooms.add(room_id)
                        
            except Exception as e:
                logger.warning(f"Error getting last messages: {str(e)}")
            
            # Enrich rooms với data đã query
            enriched_rooms = []
            for room in rooms:
                room_id = room['room_id']
                message_count = msg_counts.get(room_id, 0)
                last_msg_data = last_messages.get(room_id, {})
                
                enriched_room = {
                    **room,
                    "message_count": message_count,
                    "last_message": last_msg_data.get('content'),
                    "last_message_at": last_msg_data.get('created_at')
                }
                enriched_rooms.append(enriched_room)
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": enriched_rooms,
                "total": total
            }
            
        except Exception as e:
            logger.error(f"Error getting user rooms: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error getting rooms: {str(e)}",
                "data": [],
                "total": 0
            }
    
    def get_room_by_id(self, room_id: str, user_id: str) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết một room
        
        Args:
            room_id: ID của room
            user_id: ID của user (để check authorization)
            
        Returns:
            Dict với room data hoặc error
        """
        try:
            result = self.supabase.table('chat_rooms')\
                .select("*")\
                .eq('room_id', room_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 404,
                    "EM": "Chat room not found or access denied",
                    "data": None
                }
            
            room = result.data[0]
            
            # Enrich với message count
            msg_count_result = self.supabase.table('chat_history')\
                .select("*", count="exact")\
                .eq('room_id', room_id)\
                .execute()
            message_count = msg_count_result.count if hasattr(msg_count_result, 'count') else 0
            
            enriched_room = {
                **room,
                "message_count": message_count
            }
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": enriched_room
            }
            
        except Exception as e:
            logger.error(f"Error getting room: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error getting room: {str(e)}",
                "data": None
            }
    
    def update_room(
        self, 
        room_id: str, 
        user_id: str, 
        title: Optional[str] = None,
        is_archived: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Cập nhật room
        
        Args:
            room_id: ID của room
            user_id: ID của user (để check authorization)
            title: Tiêu đề mới (optional)
            is_archived: Archive status (optional)
            
        Returns:
            Dict với updated room data hoặc error
        """
        try:
            # Check room exists and user owns it
            check_result = self.get_room_by_id(room_id, user_id)
            if check_result["EC"] != 0:
                return check_result
            
            # Build update data
            update_data = {}
            if title is not None:
                update_data["title"] = title
            if is_archived is not None:
                update_data["is_archived"] = is_archived
            
            if not update_data:
                return {
                    "EC": 400,
                    "EM": "No fields to update",
                    "data": None
                }
            
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table('chat_rooms')\
                .update(update_data)\
                .eq('room_id', room_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Failed to update room",
                    "data": None
                }
            
            logger.info(f"Updated room {room_id} for user {user_id}")
            
            return {
                "EC": 0,
                "EM": "Room updated successfully",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error updating room: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error updating room: {str(e)}",
                "data": None
            }
    
    def delete_room(self, room_id: str, user_id: str) -> Dict[str, Any]:
        """
        Xóa room và tất cả messages
        
        Args:
            room_id: ID của room
            user_id: ID của user (để check authorization)
            
        Returns:
            Dict với success message hoặc error
        """
        try:
            # Check room exists and user owns it
            check_result = self.get_room_by_id(room_id, user_id)
            if check_result["EC"] != 0:
                return check_result
            
            # Delete room (messages will be cascade deleted)
            result = self.supabase.table('chat_rooms')\
                .delete()\
                .eq('room_id', room_id)\
                .eq('user_id', user_id)\
                .execute()
            
            logger.info(f"Deleted room {room_id} for user {user_id}")
            
            return {
                "EC": 0,
                "EM": "Room deleted successfully",
                "data": {"room_id": room_id}
            }
            
        except Exception as e:
            logger.error(f"Error deleting room: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error deleting room: {str(e)}",
                "data": None
            }
    
    def get_room_messages(
        self,
        room_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Lấy lịch sử messages của một room
        
        Args:
            room_id: ID của room
            user_id: ID của user (để check authorization)
            limit: Số lượng messages tối đa
            offset: Offset cho pagination
            
        Returns:
            Dict với list messages và metadata
        """
        try:
            # Check room exists and user owns it
            check_result = self.get_room_by_id(room_id, user_id)
            if check_result["EC"] != 0:
                return {
                    "EC": check_result["EC"],
                    "EM": check_result["EM"],
                    "data": [],
                    "total": 0,
                    "limit": limit,
                    "offset": offset
                }
            
            # Get total count
            count_result = self.supabase.table('chat_history')\
                .select("*", count="exact")\
                .eq('room_id', room_id)\
                .execute()
            total = count_result.count if hasattr(count_result, 'count') else 0
            
            # Get messages
            result = self.supabase.table('chat_history')\
                .select("*")\
                .eq('room_id', room_id)\
                .order('message_order', desc=False)\
                .order('created_at', desc=False)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            
            messages = result.data or []
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": messages,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Error getting room messages: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error getting messages: {str(e)}",
                "data": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }
    
    def save_message(
        self,
        room_id: str,
        user_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        entities: Optional[dict] = None,
        message_order: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lưu message vào database
        
        Args:
            room_id: ID của room
            user_id: ID của user
            role: 'user' or 'assistant'
            content: Nội dung message
            intent: Intent (optional)
            entities: Entities (optional)
            message_order: Thứ tự message (auto-increment nếu None)
            
        Returns:
            Dict với message data hoặc error
        """
        try:
            # Auto-increment message_order if not provided
            if message_order is None:
                max_order_result = self.supabase.table('chat_history')\
                    .select("message_order")\
                    .eq('room_id', room_id)\
                    .order('message_order', desc=True)\
                    .limit(1)\
                    .execute()
                
                if max_order_result.data and max_order_result.data[0].get('message_order') is not None:
                    message_order = max_order_result.data[0]['message_order'] + 1
                else:
                    message_order = 1
            
            message_data = {
                "room_id": room_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "message_order": message_order,
                "conversation_id": room_id  # Keep for backward compatibility
            }
            
            if intent:
                message_data["intent"] = intent
            if entities:
                message_data["entities"] = entities
            
            result = self.supabase.table('chat_history').insert(message_data).execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Failed to save message",
                    "data": None
                }
            
            logger.info(f"Saved message to room {room_id}")
            
            return {
                "EC": 0,
                "EM": "Message saved successfully",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error saving message: {str(e)}",
                "data": None
            }
    
    def auto_generate_title(self, first_message: str) -> str:
        """
        Auto-generate title từ message đầu tiên
        
        Args:
            first_message: Message đầu tiên của conversation
            
        Returns:
            Title string
        """
        # Clean message
        cleaned = first_message.strip()
        
        # Remove markdown và HTML tags
        import re
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'#+\s*', '', cleaned)
        
        # Limit length
        if len(cleaned) > 50:
            cleaned = cleaned[:47] + "..."
        
        return cleaned or "Cuộc trò chuyện mới"

