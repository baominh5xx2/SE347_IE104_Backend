"""
News Agent API Endpoints
API để chat với AI agent search tin tức/cẩm nang du lịch
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel, Field

from app.v1.services.search_new_agent.search_news_agent import get_news_search_agent
from app.v1.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class NewsAgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User message/query")


class NewsAgentChatResponse(BaseModel):
    EC: int
    EM: str
    response: str
    sources: list[str] = []
    destination: Optional[str] = None


@router.post("/chat", response_model=NewsAgentChatResponse)
async def chat_with_news_agent(
    request: NewsAgentChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat với AI agent để tìm tin tức/cẩm nang du lịch.
    Yêu cầu user phải đăng nhập.
    
    Args:
        request: NewsAgentChatRequest với message từ user
        current_user: Current authenticated user (from JWT token)
        
    Returns:
        NewsAgentChatResponse với response từ agent và sources
    """
    try:
        user_id = str(current_user["user_id"])
        
        # Get agent instance
        agent = get_news_search_agent()
        
        # Call agent chat
        result = await agent.chat(user_id=user_id, message=request.message)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to process request")
            )
        
        return NewsAgentChatResponse(
            EC=0,
            EM="Success",
            response=result.get("response", ""),
            sources=result.get("sources", []),
            destination=result.get("destination")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat_with_news_agent endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/clear")
async def clear_conversation(
    current_user: dict = Depends(get_current_user)
):
    """
    Clear conversation history cho user hiện tại.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        user_id = str(current_user["user_id"])
        agent = get_news_search_agent()
        agent.clear_conversation(user_id)
        
        return {
            "EC": 0,
            "EM": "Conversation cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear conversation: {str(e)}"
        )
