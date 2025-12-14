"""
News Search Agent Service
Agent để search tin tức/cẩm nang du lịch bằng Perplexity với conversation memory
"""
import logging
import threading
import time
from typing import Dict, Any, Optional, List

# Import LangChain components
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.v1.services.search_new_agent.perflexity_services import get_news_perplexity_service
from app.v1.services.agent_services.llm_providers import create_llm_provider
from app.v1.services.agent_services.config import agent_config

logger = logging.getLogger(__name__)


class InMemoryChatMessageHistory(BaseChatMessageHistory):
    """
    In-memory chat message history using LangChain's BaseChatMessageHistory.
    Stores conversation history in RAM with max_history limit.
    """
    def __init__(self, max_history: int = 10):
        self._messages: List[BaseMessage] = []
        self.max_history = max_history
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the store"""
        self._messages.append(message)
        # Keep only last max_history messages
        if len(self._messages) > self.max_history * 2:  # *2 because each turn has 2 messages (human + AI)
            self._messages = self._messages[-(self.max_history * 2):]
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Get all messages"""
        return self._messages
    
    def clear(self) -> None:
        """Clear all messages"""
        self._messages = []


class ConversationMemoryManager:
    """
    Manage short-term memory per user_id.
    Thread-safe để tránh race condition khi nhiều users.
    """
    _lock = threading.Lock()
    _memories: Dict[str, InMemoryChatMessageHistory] = {}
    _last_access: Dict[str, float] = {}
    _max_history: int = 10  # Giữ tối đa N turns
    _ttl_seconds: int = 1800  # Auto-cleanup sau 30 phút
    
    def get_memory(self, user_id: str) -> InMemoryChatMessageHistory:
        """Get or create memory for user_id"""
        with self._lock:
            self._cleanup_stale()
            if user_id not in self._memories:
                self._memories[user_id] = InMemoryChatMessageHistory(max_history=self._max_history)
            self._last_access[user_id] = time.time()
            return self._memories[user_id]
    
    def clear_memory(self, user_id: str) -> None:
        """Clear memory for a specific user"""
        with self._lock:
            if user_id in self._memories:
                del self._memories[user_id]
            if user_id in self._last_access:
                del self._last_access[user_id]
    
    def _cleanup_stale(self) -> None:
        """Remove stale sessions (inactive > TTL)"""
        now = time.time()
        stale = [
            uid for uid, ts in self._last_access.items()
            if now - ts > self._ttl_seconds
        ]
        for uid in stale:
            if uid in self._memories:
                del self._memories[uid]
            if uid in self._last_access:
                del self._last_access[uid]
            logger.debug(f"Cleaned up stale memory for user_id: {uid}")


class NewsSearchAgent:
    """
    Agent search tin tức/cẩm nang bằng Perplexity.
    Dùng LangChain memory để maintain conversation context.
    """
    
    def __init__(self):
        """Initialize NewsSearchAgent"""
        self.perplexity = get_news_perplexity_service()
        self.memory_manager = ConversationMemoryManager()
        
        # Initialize LLM for response formatting (optional)
        try:
            provider = create_llm_provider()
            self.llm = provider.get_llm(
                model=agent_config.model,
                api_key=agent_config.api_key
            )
        except Exception as e:
            logger.warning(f"Failed to initialize LLM for formatting: {e}")
            self.llm = None
    
    async def chat(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Chat với agent để tìm tin tức/cẩm nang du lịch
        
        Args:
            user_id: User ID để isolate conversation
            message: User message/query
            
        Returns:
            Dict với response và sources
        """
        try:
            # 1. Get memory for this user
            memory = self.memory_manager.get_memory(user_id)
            
            # 2. Get conversation history for context (optional, for future use)
            history = memory.messages
            
            # 3. Extract search query from message
            # For now, use message directly as destination/query
            # In future, could use LLM to extract intent
            search_query = message.strip()
            
            # 4. Call NewsPerplexityService directly
            # Use search_news_info with the user query
            # This will search for travel news/guides related to the query
            result = await self.perplexity.search_news_info(
                query=search_query,
                query_type="latest"
            )
            
            if not result.get("success"):
                error_msg = result.get("error", "Không tìm thấy thông tin")
                # Save error to memory
                memory.add_message(HumanMessage(content=message))
                memory.add_message(AIMessage(content=f"Xin lỗi, {error_msg}"))
                return {
                    "success": False,
                    "error": error_msg,
                    "response": f"Xin lỗi, {error_msg}",
                    "sources": []
                }
            
            # 5. Format response từ Perplexity result
            response_parts = []
            
            # Add highlights (tin tức nổi bật)
            highlights = result.get("highlights", [])
            if highlights:
                response_parts.append("**Tin tức & Thông tin nổi bật:**")
                for i, highlight in enumerate(highlights[:5], 1):
                    response_parts.append(f"{i}. {highlight}")
            
            # Add tips (cẩm nang, lưu ý)
            tips = result.get("tips", [])
            if tips:
                response_parts.append("\n**Cẩm nang & Lưu ý du lịch:**")
                for i, tip in enumerate(tips[:5], 1):
                    response_parts.append(f"{i}. {tip}")
            
            # If no structured data, use raw results
            if not response_parts:
                raw_results = result.get("raw_results", [])
                if raw_results:
                    response_parts.append("**Thông tin tìm được:**")
                    for i, item in enumerate(raw_results[:5], 1):
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        if title:
                            response_parts.append(f"{i}. **{title}**")
                        if snippet:
                            response_parts.append(f"   {snippet[:200]}...")
            
            response = "\n".join(response_parts) if response_parts else "Đã tìm thấy thông tin liên quan đến yêu cầu của bạn."
            
            # 6. Save to memory using LangChain messages
            memory.add_message(HumanMessage(content=message))
            memory.add_message(AIMessage(content=response))
            
            # 7. Get sources
            sources = result.get("sources", [])
            
            return {
                "success": True,
                "response": response,
                "sources": sources,
                "destination": search_query  # Use query as destination for news search
            }
            
        except Exception as e:
            logger.error(f"Error in NewsSearchAgent.chat: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Lỗi khi xử lý yêu cầu: {str(e)}",
                "response": "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau.",
                "sources": []
            }
    
    def clear_conversation(self, user_id: str) -> None:
        """Clear conversation history for a user"""
        self.memory_manager.clear_memory(user_id)


# Singleton instance
_news_search_agent = None


def get_news_search_agent() -> NewsSearchAgent:
    """Get singleton NewsSearchAgent instance"""
    global _news_search_agent
    if _news_search_agent is None:
        _news_search_agent = NewsSearchAgent()
    return _news_search_agent
