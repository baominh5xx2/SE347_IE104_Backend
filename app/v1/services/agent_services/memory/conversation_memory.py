"""
Conversation Memory with Mem0
Handles conversation memory using Mem0 AI with per-user isolation
and thread-safe operations to prevent race conditions
"""
from typing import Dict, Optional, List, Any
from threading import RLock
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.v1.core.mem0_client import mem0_client
import logging

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation memory using Mem0 AI
    
    Features:
    - Per-user memory isolation via user_id
    - Thread-safe operations with RLock
    - Conversation context tracking
    - Automatic user_id prefix for conversation keys
    """
    
    def __init__(self):
        """Initialize conversation memory"""
        self._lock = RLock()
        logger.info("✅ ConversationMemory initialized with Mem0")
    
    def _make_key(self, conversation_id: str, user_id: Optional[str]) -> str:
        """Create unique key for user-conversation pair"""
        if not conversation_id:
            raise ValueError("conversation_id is required")
        user_key = user_id or "anonymous_user"
        return f"{user_key}::{conversation_id}"

    async def get_memory(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get conversation memory from Mem0
        
        Args:
            conversation_id: Conversation identifier
            user_id: User identifier for isolation
            limit: Maximum memories to retrieve
            
        Returns:
            List of memory objects with 'role' and 'content'
        """
        user_key = user_id or "anonymous_user"
        
        with self._lock:
            try:
                # Search Mem0 for this conversation
                memories = mem0_client.get_all(
                    user_id=user_key,
                    limit=limit,
                    filters={"conversation_id": conversation_id}
                )
                
                logger.info(f"📚 Retrieved {len(memories)} memories for conversation {conversation_id}")
                return memories
                
            except Exception as e:
                logger.error(f"❌ Error retrieving memory: {str(e)}")
                return []
    
    async def get_messages(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> List[BaseMessage]:
        """
        Get conversation messages as LangChain BaseMessage objects
        
        Args:
            conversation_id: Conversation identifier
            user_id: User identifier
            
        Returns:
            List of BaseMessage (HumanMessage, AIMessage)
        """
        user_key = user_id or "anonymous_user"
        
        with self._lock:
            try:
                # Get memories from Mem0
                memories = await self.get_memory(conversation_id, user_key)
                
                # Convert to LangChain messages
                messages = []
                for mem in memories:
                    # Handle both dict and string formats from Mem0
                    if isinstance(mem, str):
                        # If memory is a string, treat it as content
                        content = mem
                        metadata = {}
                        role = "user"
                    elif isinstance(mem, dict):
                        # Mem0 stores messages with 'user' and 'assistant' roles
                        content = mem.get("memory", "") or mem.get("content", "")
                        metadata = mem.get("metadata", {})
                        role = metadata.get("role", "user")
                    else:
                        logger.warning(f"⚠️ Unexpected memory format: {type(mem)}")
                        continue
                    
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(
                            content=content,
                            additional_kwargs={"metadata": metadata}
                        ))
                
                return messages
                
            except Exception as e:
                logger.error(f"❌ Error converting memories to messages: {str(e)}")
                return []
    
    async def search_context(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search conversation context using semantic search
        
        Args:
            query: Search query
            user_id: User identifier
            conversation_id: Optional conversation filter
            limit: Maximum results
            
        Returns:
            List of relevant memories with scores
        """
        with self._lock:
            try:
                # Build filters
                filters = {}
                if conversation_id:
                    filters["conversation_id"] = conversation_id
                
                # Search Mem0
                results = mem0_client.search(
                    query=query,
                    user_id=user_id,
                    limit=limit,
                    filters=filters
                )
                
                logger.info(f"🔍 Found {len(results)} relevant memories for query: {query[:50]}...")
                return results
                
            except Exception as e:
                logger.error(f"❌ Error searching context: {str(e)}")
                return []

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Delete all memories for a conversation
        
        Args:
            conversation_id: Conversation to delete
            user_id: User identifier
            
        Returns:
            True if successful
        """
        user_key = user_id or "anonymous_user"
        
        with self._lock:
            try:
                # Get all memories for this conversation
                memories = await self.get_memory(conversation_id, user_key)
                
                # Delete each memory
                for mem in memories:
                    memory_id = mem.get("id")
                    if memory_id:
                        mem0_client.delete(memory_id=memory_id, user_id=user_key)
                
                logger.info(f"🗑️ Deleted {len(memories)} memories for conversation {conversation_id}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error deleting conversation: {str(e)}")
                return False
    
    async def store_episode(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Store conversation episode to Mem0 (USER MESSAGE ONLY)
        
        We only store user messages to track what users are interested in,
        not AI responses. This keeps memory focused on user preferences.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID for isolation
            user_message: User's message (STORED)
            assistant_response: Assistant's response (NOT STORED, kept for compatibility)
            metadata: Optional metadata (e.g., recommendations, timestamps)
            
        Returns:
            Episode ID or None if failed
        """
        with self._lock:
            try:
                # Store ONLY user message (not assistant response)
                messages = [
                    {"role": "user", "content": user_message}
                ]
                
                # Prepare metadata
                episode_metadata = {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    **(metadata or {})
                }
                
                # Add to Mem0
                result = mem0_client.add(
                    messages=messages,
                    user_id=user_id,
                    metadata=episode_metadata
                )
                
                if result:
                    episode_id = result.get("id", f"ep_{conversation_id}")
                    logger.info(f"✅ User message stored to Mem0 for user {user_id} (conversation: {conversation_id})")
                    return episode_id
                else:
                    logger.warning(f"⚠️ No result from Mem0 add operation")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Error storing episode to Mem0: {str(e)}")
                return None


# Singleton instance
conversation_memory = ConversationMemory()