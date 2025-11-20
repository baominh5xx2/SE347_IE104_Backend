"""
Recommendation Engine
Uses MCP tools for tour recommendations with Mem0 personalization
"""
from typing import Dict, List, Optional
import logging
from app.v1.services.agent_services.memory import conversation_memory

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Recommendation engine sử dụng MCP tools với Mem0 personalization
    
    Current strategy:
    - Semantic vector search via MCP search_tour_packages tool
    - Mem0 personalization context (user history)
    """
    
    def __init__(self):
        """Initialize recommendation engine"""
        self.memory = conversation_memory
    
    async def get_recommendations(self,
                           user_message: str,
                           user_id: Optional[str] = None,
                           filters: Optional[Dict] = None,
                           limit: int = 5) -> Dict:
        """
        Get tour recommendations using semantic search
        
        Args:
            user_message: User's query (e.g., "Tôi muốn đi Đà Nẵng")
            user_id: Optional user ID for personalization
            filters: Optional filters (price, duration, destination)
            limit: Number of recommendations
            
        Returns:
            Dict containing:
            - recommendations: List of recommended tours
            - total: Total number of results
            - reasoning: Explanation for recommendations
            - personalized: Whether personalization was applied
        """
        try:
            # Import callback handler for tool logging
            from app.v1.core.logging_config import get_current_agent_callback
            agent_callback = get_current_agent_callback()
            
            # Search for relevant context using Mem0 semantic search
            personalization_context = None
            relevant_memories = []
            
            if user_id:
                try:
                    # Use Mem0 to search for relevant conversation context
                    relevant_memories = await self.memory.search_context(
                        query=user_message,
                        user_id=user_id,
                        limit=2
                    )
                    
                    if relevant_memories:
                        personalization_context = {
                            "user_id": user_id,
                            "memories": relevant_memories,
                            "has_data": True
                        }
                        logger.info(f"✅ Found {len(relevant_memories)} relevant memories for personalization")
                    else:
                        logger.info("📊 No relevant memories found for personalization")
                        personalization_context = {
                            "user_id": user_id,
                            "memories": [],
                            "has_data": False
                        }
                except Exception as e:
                    logger.warning(f"⚠️ RECOMMENDATION ENGINE: Could not search memories: {str(e)}")
                    personalization_context = None
            
            # Build query với personalization context from Mem0
            enhanced_query = user_message
            if personalization_context and personalization_context.get("has_data"):
                memories = personalization_context.get("memories", [])
                if memories:
                    # Enhance query with user history from memories
                    memory_contexts = []
                    for mem in memories[:5]:  # Use top 5 memories
                        memory_content = mem.get('memory', '') or mem.get('content', '')
                        if memory_content:
                            # Extract key preferences (first 100 chars)
                            memory_contexts.append(memory_content[:100])
                    
                    if memory_contexts:
                        enhanced_query = f"{user_message}. Dựa trên lịch sử: {', '.join(memory_contexts)}"
                        logger.info(f"✅ Enhanced query with {len(memory_contexts)} memory contexts")
            
            # Perform semantic search via MCP tool (for automatic logging via callback handler)
            # Use tool instead of direct mcp_client call so callback handler can log it
            from app.v1.services.agent_services.tools.mcp_tools import search_tour_packages_tool
            
            search_tool = search_tour_packages_tool()
            
            # Call tool with callback handler for automatic logging
            search_result = await search_tool.ainvoke(
                {
                    "user_message": enhanced_query,
                    "max_price": filters.get("max_price") if filters else None,
                    "duration": filters.get("duration") if filters else None,
                    "destination": filters.get("destination") if filters else None,
                    "limit": limit
                },
                config={"callbacks": [agent_callback]} if agent_callback else {}
            )
            
            results = search_result.get("packages", [])
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                personalization_context,
                len(results)
            )
            
            response = {
                "recommendations": results,
                "total": len(results),
                "reasoning": reasoning,
                "personalized": bool(personalization_context and personalization_context.get("has_data"))
            }
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error getting recommendations: {str(e)}")
            return {
                "recommendations": [],
                "total": 0,
                "reasoning": "Xin lỗi, đã có lỗi xảy ra khi tìm kiếm tour.",
                "personalized": False
            }
    
    def _generate_reasoning(self,
                          personalization_context: Optional[Dict],
                          num_results: int) -> str:
        """
        Generate reasoning text for recommendations
        
        Args:
            personalization_context: User personalization data
            num_results: Number of results found
            
        Returns:
            Reasoning text
        """
        if num_results == 0:
            return "Không tìm thấy tour phù hợp. Vui lòng thử với từ khóa khác."
        
        if personalization_context and personalization_context.get("has_data"):
            memories = personalization_context.get("memories", [])
            if memories:
                return f"Dựa trên lịch sử chat của bạn ({len(memories)} cuộc hội thoại), tôi gợi ý {num_results} tour phù hợp:"
            else:
                return f"Dựa trên sở thích của bạn, tôi tìm thấy {num_results} tour phù hợp:"
        else:
            return f"Tôi tìm thấy {num_results} tour phù hợp với yêu cầu của bạn:"
    
    async def track_interaction(self,
                         user_id: str,
                         conversation_id: str,
                         user_message: str,
                         assistant_response: str,
                         metadata: Optional[Dict] = None):
        """
        Track user interaction by storing to Mem0
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            user_message: User's message
            assistant_response: Assistant's response
            metadata: Additional metadata (intent, destinations, etc.)
        """
        try:
            await self.memory.store_episode(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=user_message,
                assistant_response=assistant_response,
                metadata=metadata
            )
            logger.info(f"✅ Tracked interaction for user {user_id}, conversation {conversation_id}")
        except Exception as e:
            logger.error(f"❌ Failed to track interaction: {str(e)}")


# Singleton instance
recommendation_engine = RecommendationEngine()
