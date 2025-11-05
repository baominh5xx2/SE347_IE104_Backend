"""
Recommendation Engine
Uses MCP tools for tour recommendations
"""
from typing import Dict, List, Optional
import logging
from .falkor_personalization import falkor_personalization_service
from app.v1.services.agent_services.mcp_intergation import mcp_client

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Recommendation engine sử dụng MCP tools
    
    Current strategy:
    - Semantic vector search via MCP search_tour_packages tool
    - FalkorDB personalization context (optional)
    """
    
    def __init__(self):
        """Initialize recommendation engine"""
        self.falkor_service = falkor_personalization_service
    
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
            
            # Search for relevant episodes using MCP tool (for personalization)
            personalization_context = None
            episodes = []
            
            if user_id:
                try:
                    # Use search_episodes tool from MCP to find relevant episodes
                    from app.v1.services.agent_services.tools.mcp_tools import search_episodes_tool
                    
                    episodes_tool = search_episodes_tool()
                    
                    # Search episodes related to user query for personalization
                    episodes_result = await episodes_tool.ainvoke(
                        {
                            "query_text": user_message,
                            "user_id": user_id,
                            "limit": 5
                        },
                        config={"callbacks": [agent_callback]} if agent_callback else {}
                    )
                    
                    episodes = episodes_result.get("episodes", []) if isinstance(episodes_result, dict) else []
                    
                    if episodes:
                        personalization_context = {
                            "user_id": user_id,
                            "episodes": episodes,
                            "has_data": True
                        }
                        logger.info(f"✅ Found {len(episodes)} relevant episodes for personalization")
                    else:
                        logger.info("📊 No relevant episodes found for personalization")
                        personalization_context = {
                            "user_id": user_id,
                            "episodes": [],
                            "has_data": False
                        }
                except Exception as e:
                    logger.warning(f"⚠️ RECOMMENDATION ENGINE: Could not search episodes: {str(e)}")
                    personalization_context = None
            
            # Build query với personalization context from episodes
            enhanced_query = user_message
            if personalization_context and personalization_context.get("has_data"):
                episodes = personalization_context.get("episodes", [])
                if episodes:
                    # Enhance query with user history from episodes
                    episode_preferences = []
                    for ep in episodes[:10]:  # Use top 10 episodes
                        episode_body = ep.get('episode_body', '') or ep.get('name', '')
                        if episode_body:
                            # Extract key preferences (first 100 chars)
                            episode_preferences.append(episode_body)
                    
                    if episode_preferences:
                        enhanced_query = f"{user_message}. Dựa trên lịch sử: {', '.join(episode_preferences)}"
                        logger.info(f"✅ Enhanced query with {len(episode_preferences)} episode contexts")
            
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
            episodes = personalization_context.get("episodes", [])
            if episodes:
                return f"Dựa trên lịch sử chat của bạn ({len(episodes)} cuộc hội thoại), tôi gợi ý {num_results} tour phù hợp:"
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
        Track user interaction by adding episode to Graphiti
        
        DISABLED: Conversation tracking to Graphiti is currently disabled
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            user_message: User's message
            assistant_response: Assistant's response
            metadata: Additional metadata (intent, destinations, etc.)
        """
        # Disabled: conversation tracking to Graphiti
        logger.debug(f"📊 Tracking interaction disabled: user {user_id}, conversation {conversation_id}")
        return


# Singleton instance
recommendation_engine = RecommendationEngine()

