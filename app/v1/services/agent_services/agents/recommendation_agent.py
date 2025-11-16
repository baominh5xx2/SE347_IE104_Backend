"""
Recommendation Agent
Specialized agent for tour recommendations
"""
from typing import Dict, List, Optional
import logging
from langchain_core.messages import HumanMessage
from app.v1.core.prompts import prompt_manager
from app.v1.services.agent_services.memory import recommendation_engine
from app.v1.services.agent_services.agents.base_agent import BaseAgent
from app.v1.services.agent_services.tools.mcp_tools import search_tour_packages_tool
from app.v1.core.logging_config import get_current_agent_callback

logger = logging.getLogger(__name__)


class RecommendationAgent(BaseAgent):
    """
    Recommendation Agent - Analyzes and recommends tour packages
    Uses semantic search + FalkorDB personalization
    
    Inherits from BaseAgent for common functionality
    """
    
    def __init__(self):
        """Initialize Recommendation Agent"""
        super().__init__(
            name="Recommendation Agent",
            temperature=1.0  # Lower temperature for more focused recommendations
        )
        self.recommendation_engine = recommendation_engine
        # Add search_tour_packages tool for automatic logging
        self.search_tool = search_tour_packages_tool()
    
    def _extract_user_query(self, requirements: Dict) -> str:
        """
        Extract natural language query from requirements
        
        Args:
            requirements: User requirements dict
            
        Returns:
            Natural language query string
        """
        query_parts = []
        
        if requirements.get("destination"):
            query_parts.append(f"Tôi muốn đi {requirements['destination']}")
        
        if requirements.get("budget"):
            budget = float(requirements["budget"])
            query_parts.append(f"ngân sách khoảng {budget:,.0f} VND")
        
        if requirements.get("duration"):
            duration = int(requirements["duration"])
            query_parts.append(f"trong {duration} ngày")
        
        if requirements.get("people"):
            people = int(requirements["people"])
            query_parts.append(f"cho {people} người")
        
        # Combine into natural query
        if query_parts:
            return ". ".join(query_parts)
        else:
            return "Tìm tour du lịch phù hợp"
    
    def _build_filters(self, requirements: Dict) -> Dict:
        """
        Build filters dict for recommendation engine
        
        Args:
            requirements: User requirements
            
        Returns:
            Filters dict
        """
        filters = {}
        
        if requirements.get("budget"):
            filters["max_price"] = float(requirements["budget"])
        
        if requirements.get("duration"):
            filters["duration"] = int(requirements["duration"])
        
        if requirements.get("destination"):
            filters["destination"] = requirements["destination"]
        
        return filters
    
    async def recommend(
        self, 
        user_requirements: Dict,
        user_id: Optional[str] = None,
        user_message: Optional[str] = None
    ) -> Dict:
        """
        Generate tour package recommendations based on user requirements
        
        Args:
            user_requirements: Dict with destination, budget, duration, people, etc.
            user_id: Optional user ID for personalization
            user_message: Optional user's original message for semantic search
            
        Returns:
            dict with recommendations, reasoning, and thinking process
        """
        try:
            thinking_steps = []
            
            # Step 1: Extract query and filters
            thinking_steps.append("🔍 Đang phân tích yêu cầu...")
            
            # Use provided message or extract from requirements
            query = user_message or self._extract_user_query(user_requirements)
            filters = self._build_filters(user_requirements)
            
            # Step 2: Get recommendations from recommendation engine
            thinking_steps.append("🚀 Đang tìm kiếm tour với semantic search...")
            
            result = await self.recommendation_engine.get_recommendations(
                user_message=query,
                user_id=user_id,
                filters=filters,
                limit=2
            )
            
            recommendations = result.get("recommendations", [])
            reasoning = result.get("reasoning", "")
            personalized = result.get("personalized", False)
            
            if personalized:
                thinking_steps.append("✓ Đã áp dụng personalization từ lịch sử user")
            
            thinking_steps.append(f"✓ Tìm thấy {len(recommendations)} gói tour phù hợp")
            
            # Use reasoning from recommendation engine directly (no LLM enhancement for speed)
            if not recommendations:
                reasoning = "Không tìm thấy gói tour phù hợp với yêu cầu của bạn. Vui lòng thử điều chỉnh tiêu chí tìm kiếm."
                logger.warning(f"⚠️ RECOMMENDATION AGENT: No recommendations found")
            
            thinking_steps.append("✓ Hoàn thành")
            
            return {
                "recommendations": recommendations,
                "reasoning": reasoning,  # Use base reasoning for speed
                "thinking_process": thinking_steps,
                "total_found": len(recommendations),
                "personalized": personalized,
                "search_query": query
            }
            
        except Exception as e:
            logger.error(f"❌ Error in recommend: {str(e)}")
            return {
                "recommendations": [],
                "reasoning": f"Đã xảy ra lỗi khi tìm kiếm tour: {str(e)}",
                "thinking_process": ["❌ Lỗi trong quá trình tìm kiếm"],
                "total_found": 0,
                "personalized": False
            }
    
    def _enhance_reasoning_with_llm(
        self,
        recommendations: List[Dict],
        requirements: Dict,
        base_reasoning: str
    ) -> str:
        """
        Use LLM to enhance the reasoning with more details
        
        Args:
            recommendations: List of recommended tours
            requirements: User requirements
            base_reasoning: Base reasoning from recommendation engine
            
        Returns:
            Enhanced reasoning text
        """
        try:
            # Format recommendations for LLM
            tours_info = []
            for i, tour in enumerate(recommendations[:3], 1):
                package_id = tour.get('package_id', 'N/A')
                tours_info.append(
                    f"{i}. {tour.get('package_name', 'N/A')} - "
                    f"{tour.get('destination', 'N/A')} - "
                    f"{tour.get('duration_days', 'N/A')} ngày - "
                    f"{tour.get('price', 0):,.0f} VND - "
                    f"[Package ID: {package_id}]"
                )
            
            tours_text = "\n".join(tours_info)
            requirements_str = ", ".join([f"{k}: {v}" for k, v in requirements.items() if v])
            
            # Use prompt from agent.yaml
            # Reads from: agents[name='recommendation_agent'].config.prompts.reasoning_generation
            prompt = prompt_manager.get_prompt(
                'recommendation_agent',
                'reasoning_generation',
                requirements=requirements_str,
                packages=tours_text
            )
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            enhanced = response.content.strip()
            
            return enhanced if enhanced else base_reasoning
            
        except Exception as e:
            logger.warning(f"⚠️ Could not enhance reasoning with LLM: {str(e)}")
            return base_reasoning
    
    async def process(self, state: Dict[str, any]) -> Dict[str, any]:
        """
        Process recommendation request (implements BaseAgent interface)
        
        Args:
            state: Agent state
            
        Returns:
            Updated state
        """
        recommendation_params = state.get("recommendation_params", {})
        user_query = recommendation_params.get("user_query", "")
        
        # Build user requirements from params
        user_requirements = {}
        if recommendation_params.get("destination"):
            user_requirements["destination"] = recommendation_params["destination"]
        if recommendation_params.get("budget"):
            user_requirements["budget"] = recommendation_params["budget"]
        if recommendation_params.get("duration"):
            user_requirements["duration"] = recommendation_params["duration"]
        
        # Get recommendations
        result = await self.recommend(
            user_requirements=user_requirements,
            user_id=state.get("user_id", ""),
            user_message=user_query
        )
        
        # Update state with recommendations
        state["recommendation_result"] = result
        state["final_response"] = result.get("reasoning", "")
        
        return state


# Singleton instance
recommendation_agent = RecommendationAgent()
