"""
Recommendation Agent Nodes
Node functions for Recommendation Agent
"""
from langchain_core.messages import HumanMessage, AIMessage
import logging
from app.v1.services.agent_services.state import AgentState
from app.v1.services.agent_services.agents import recommendation_agent

logger = logging.getLogger(__name__)


class RecommendationAgentNodes:
    """
    Node functions for Recommendation Agent
    """
    
    async def recommendation_node(self, state: AgentState) -> AgentState:
        """
        Recommendation Agent: Provide tour recommendations
        
        This is called when Chat Agent requests recommendations via request_recommendation tool.
        Recommendation Agent communicates results back to Chat Agent.
        """
        # Get recommendation params from Chat Agent's tool call
        recommendation_params = state.get("recommendation_params", {})
        user_query = recommendation_params.get("user_query", "")
        
        # Extract user message from state messages as fallback
        if not user_query:
            for msg in state.get("messages", []):
                if isinstance(msg, HumanMessage):
                    user_query = msg.content
                    break
        
        try:
            # Build user requirements from Chat Agent's params
            user_requirements = {}
            if recommendation_params.get("destination"):
                user_requirements["destination"] = recommendation_params["destination"]
            if recommendation_params.get("budget"):
                user_requirements["budget"] = recommendation_params["budget"]
            if recommendation_params.get("duration"):
                user_requirements["duration"] = recommendation_params["duration"]
            
            # Get recommendations from recommendation agent
            recommendations = await recommendation_agent.recommend(
                user_requirements=user_requirements,
                user_id=state.get("user_id", ""),
                user_message=user_query
            )
            
            # Build detailed recommendation message with full tour information
            packages = recommendations.get('recommendations', [])
            reasoning = recommendations.get('reasoning', '')
            
            # Debug: Log how many packages were found
            logger.info(f"🎯 RECOMMENDATION NODE: Received {len(packages)} tour packages from Recommendation Agent")
            
            # Format detailed tour information for Chat Agent
            if packages:
                package_ids = [pkg.get('package_id') for pkg in packages[:5] if pkg.get('package_id')]
                if package_ids:
                    state["recommended_package_ids"] = package_ids
                
                # Store full tour packages in state for API response
                state["tour_packages"] = packages[:5]
                
                # Build detailed message with tour info (show top 5 tours)
                tour_details = []
                for i, pkg in enumerate(packages[:5], 1):
                    # Get full description or truncate if too long
                    description = pkg.get('description', 'N/A')
                    # Get start_date and end_date from package (these are FIXED dates, not user choice)
                    start_date = pkg.get('start_date', 'N/A')
                    end_date = pkg.get('end_date', 'N/A')
                    
                    # Format dates if available
                    date_info = ""
                    if start_date != 'N/A' and end_date != 'N/A':
                        date_info = f"\n   - Ngày bắt đầu: {start_date}\n   - Ngày kết thúc: {end_date}"
                    elif start_date != 'N/A':
                        date_info = f"\n   - Ngày bắt đầu: {start_date}"
                    
                    # NOTE: Package ID is stored internally in state["tour_packages"] for backend use
                    # Do NOT include Package ID in user-facing message
                    tour_info = f"""
{i}. {pkg.get('package_name', 'N/A')}
   - Địa điểm: {pkg.get('destination', 'N/A')}
   - Thời gian: {pkg.get('duration_days', 'N/A')} ngày{date_info}
   - Giá: {pkg.get('price', 0):,.0f} VND
   - Mô tả: {description}
"""
                    tour_details.append(tour_info)
                
                # Create comprehensive recommendation message for Chat Agent
                # IMPORTANT: Chat Agent MUST display ALL tours in this message
                num_shown = min(len(packages), 5)
                logger.info(f"🎯 RECOMMENDATION NODE: Formatting {num_shown} tours for Chat Agent (total found: {len(packages)})")
                recommendation_message = f"""Tôi đã tìm thấy {len(packages)} tour phù hợp, đây là top {num_shown} tour tốt nhất:

{''.join(tour_details)}

Lý do đề xuất: {reasoning}

QUAN TRỌNG: Vui lòng hiển thị TẤT CẢ {num_shown} tour ở trên cho user, đừng tóm tắt hay bỏ qua tour nào.

CRITICAL - VỀ NGÀY KHỞI HÀNH:
- Mỗi tour package đã có NGÀY BẮT ĐẦU và NGÀY KẾT THÚC CỐ ĐỊNH (đã hiển thị ở trên)
- KHÔNG hỏi user về "ngày dự kiến khởi hành" - ngày đã được quy định sẵn trong package
- Ngày bắt đầu và ngày kết thúc lấy từ thông tin package (start_date, end_date), KHÔNG phải user chọn

Sau khi hiển thị đầy đủ, hỏi user:
- Bạn thích tour nào trong số những tour trên? (chỉ cần nói số hoặc tên tour, ví dụ: "tour 1" hoặc "Đà Lạt")
- Số người đi
- Số điện thoại liên hệ
- Yeu cầu khác (nếu có)
- KHÔNG hỏi Package ID - đó là chi tiết kỹ thuật nội bộ

KHÔNG hỏi về ngày khởi hành - ngày đã được quy định trong package."""
            else:
                recommendation_message = reasoning if reasoning else "Không tìm thấy tour phù hợp với yêu cầu của bạn."
            
            # Add recommendation response as AI message (Chat Agent will format this into natural response)
            recommendation_msg = AIMessage(content=recommendation_message)
            current_messages = state.get("messages", [])
            state["messages"] = current_messages + [recommendation_msg]
            
            # Debug: Log recommendation message length
            logger.info(f"🎯 RECOMMENDATION NODE: Created recommendation message ({len(recommendation_message)} chars)")
            
            # Don't set final_response here - let Chat Agent create it
            
            return state
            
        except Exception as e:
            logger.error(f"🎯 RECOMMENDATION AGENT: Error generating recommendations: {str(e)}")
            error_msg = f"Xin lỗi, tôi không thể tìm tour recommendations lúc này. Vui lòng thử lại sau."
            state["final_response"] = error_msg
            
            error_ai_msg = AIMessage(content=error_msg)
            current_messages = state.get("messages", [])
            state["messages"] = current_messages + [error_ai_msg]
            return state
