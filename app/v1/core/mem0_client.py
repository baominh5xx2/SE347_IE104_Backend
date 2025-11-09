"""
Mem0 Client Wrapper
Thread-safe singleton client for Mem0 AI Memory
"""
import logging
from typing import Optional, List, Dict, Any
from threading import Lock
import os
from dotenv import load_dotenv
from mem0 import MemoryClient

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Mem0Client:
    """
    Thread-safe singleton wrapper for Mem0 AI Memory
    
    Features:
    - Singleton pattern to ensure single client instance
    - Thread-safe initialization with double-checked locking
    - User isolation through user_id parameter
    - Graceful error handling
    - Conversation context tracking
    """
    
    _instance: Optional['Mem0Client'] = None
    _lock = Lock()
    
    def __new__(cls):
        """Singleton implementation with thread-safe double-checked locking"""
        if cls._instance is None:
            with cls._lock:
                # Double-check inside lock to prevent race condition
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Mem0 client (only once due to singleton)"""
        # Skip re-initialization if already done
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = False
        self._client: Optional[MemoryClient] = None
        
        try:
            # Get API key from environment
            api_key = os.getenv("MEM0_API_KEY")
            
            if not api_key:
                logger.warning("⚠️ MEM0_API_KEY not found in environment. Mem0 features will be disabled.")
                return
            
            # Initialize Mem0 client - simple!
            self._client = MemoryClient(api_key=api_key)
            self._initialized = True
            logger.info("✅ Mem0 client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Mem0 client: {str(e)}")
            self._client = None
    
    @property
    def is_available(self) -> bool:
        """Check if Mem0 client is available"""
        return self._initialized and self._client is not None
    
    def add(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Add conversation messages to Mem0 memory
        
        Args:
            messages: List of message dicts with 'role' and 'content'
                     Example: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            user_id: Unique user identifier for memory isolation
            metadata: Optional metadata to attach (e.g., conversation_id, timestamps)
        
        Returns:
            Response from Mem0 API or None if failed
        """
        if not self.is_available:
            logger.warning("Mem0 client not available, skipping add operation")
            return None
        
        try:
            # Add metadata for conversation tracking
            full_metadata = metadata or {}
            full_metadata["user_id"] = user_id
            
            # Call Mem0 API
            result = self._client.add(
                messages=messages,
                user_id=user_id,
                metadata=full_metadata
            )
            
            logger.info(f"✅ Added {len(messages)} messages to Mem0 for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to add messages to Mem0: {str(e)}")
            return None
    
    def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search Mem0 memory for relevant context
        
        Args:
            query: Search query (natural language)
            user_id: User identifier for memory isolation
            limit: Maximum number of results
            filters: Optional filters (e.g., {"conversation_id": "conv_123"})
        
        Returns:
            List of memory results with scores and metadata
        """
        if not self.is_available:
            logger.warning("Mem0 client not available, returning empty results")
            return []
        
        try:
            # Build filters with Mem0 v2 format
            query_filters = {
                "AND": [
                    {"user_id": user_id}
                ]
            }
            
            # Add additional filters if provided
            # conversation_id should be in metadata, not top-level
            if filters:
                for key, value in filters.items():
                    if key == "conversation_id":
                        # conversation_id goes in metadata
                        query_filters["AND"].append({
                            "metadata": {"conversation_id": value}
                        })
                    elif key != "user_id":  # Already added
                        # Other allowed fields
                        query_filters["AND"].append({key: value})
            
            # Call Mem0 search API v2
            raw_results = self._client.search(
                query=query,
                user_id=user_id,
                limit=limit,
                version="v2",
                filters=query_filters
            )

            # Normalize response shape (Mem0 v2 returns {"results": [...]})
            if isinstance(raw_results, dict):
                results = raw_results.get("results", [])
            else:
                results = raw_results

            # Validate results type
            if not isinstance(results, list):
                logger.warning(
                    f"⚠️ Unexpected search result type: {type(results)}, value: {results}"
                )
                return []
            
            # Debug: Log first result structure
            if results and len(results) > 0:
                logger.debug(f"📋 First search result structure: type={type(results[0])}, value={results[0]}")
            
            logger.info(f"🔍 Found {len(results)} memories for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to search Mem0: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def get_all(
        self,
        user_id: str,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all memories for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of memories to retrieve
            filters: Optional filters (e.g., conversation_id)
        
        Returns:
            List of all memories for the user
        """
        if not self.is_available:
            logger.warning("Mem0 client not available, returning empty list")
            return []
        
        try:
            # Build filters with Mem0 v2 format
            query_filters = {
                "AND": [
                    {"user_id": user_id}
                ]
            }
            
            # Add additional filters if provided
            # conversation_id should be in metadata, not top-level
            if filters:
                for key, value in filters.items():
                    if key == "conversation_id":
                        # conversation_id goes in metadata
                        query_filters["AND"].append({
                            "metadata": {"conversation_id": value}
                        })
                    elif key != "user_id":  # Already added
                        # Other allowed fields
                        query_filters["AND"].append({key: value})
            
            # Get all memories
            raw_memories = self._client.get_all(
                user_id=user_id,
                limit=limit,
                filters=query_filters
            )

            # Normalize response shape (Mem0 v2 returns {"results": [...]})
            if isinstance(raw_memories, dict):
                memories = raw_memories.get("results", [])
            else:
                memories = raw_memories

            # Validate results type
            if not isinstance(memories, list):
                logger.warning(
                    f"⚠️ Unexpected get_all result type: {type(memories)}, value: {memories}"
                )
                return []
            
            # Debug: Log first memory structure
            if memories and len(memories) > 0:
                logger.debug(f"📋 First memory structure: type={type(memories[0])}, value={memories[0]}")
            
            logger.info(f"📚 Retrieved {len(memories)} memories for user {user_id}")
            return memories
            
        except Exception as e:
            logger.error(f"❌ Failed to get all memories: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def delete(
        self,
        memory_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a specific memory
        
        Args:
            memory_id: Memory ID to delete
            user_id: User identifier for verification
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            logger.warning("Mem0 client not available, skipping delete")
            return False
        
        try:
            self._client.delete(memory_id=memory_id, user_id=user_id)
            logger.info(f"🗑️ Deleted memory {memory_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete memory: {str(e)}")
            return False


# Singleton instance
mem0_client = Mem0Client()
