"""
Conversation Memory
Handles conversation memory and Graphiti integration
"""
from typing import Dict, Optional
from langchain_community.chat_message_histories import ChatMessageHistory
from .falkor_personalization import falkor_personalization_service
import logging

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation memory across agents
    
    Provides:
    - Per-conversation memory storage
    - Graphiti episode tracking
    """
    
    def __init__(self):
        """Initialize conversation memory"""
        self.memory_storage: Dict[str, ChatMessageHistory] = {}
        logger.info("✅ ConversationMemory initialized")
    
    def get_memory(self, conversation_id: str) -> ChatMessageHistory:
        """
        Get or create memory for a conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            ChatMessageHistory instance
        """
        if conversation_id not in self.memory_storage:
            self.memory_storage[conversation_id] = ChatMessageHistory()
        return self.memory_storage[conversation_id]
    
    async def store_episode(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Store conversation episode to Graphiti
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            user_message: User's message
            assistant_response: Assistant's response
            metadata: Optional metadata
            
        Returns:
            Episode ID
        """
        try:
            episode_id = await falkor_personalization_service.add_episode(
                conversation_id=conversation_id,
                user_message=user_message,
                assistant_response=assistant_response,
                user_id=user_id,
                metadata=metadata or {}
            )
            logger.info(f"✅ Episode {episode_id} stored in Graphiti")
            return episode_id
        except Exception as e:
            logger.error(f"❌ Error storing episode to Graphiti: {str(e)}")
            return f"ep_error_{conversation_id}"


# Singleton instance
conversation_memory = ConversationMemory()
