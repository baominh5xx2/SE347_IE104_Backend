"""
Admin Agent API Endpoints
Natural language database queries for admin
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from ...core.dependencies import get_current_user
from ...services.agent_support_admin import get_admin_agent

logger = logging.getLogger(__name__)

router = APIRouter()


class AdminQueryRequest(BaseModel):
    """Request schema for admin query"""
    message: str = Field(
        ...,
        description="Natural language query, e.g. 'Cho tôi thống kê booking tháng này'",
        min_length=1,
        max_length=1000
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for conversation memory"
    )


class AdminQueryResponse(BaseModel):
    """Response schema for admin query"""
    success: bool
    response: Optional[str] = None
    tool_calls: Optional[list] = None
    error: Optional[str] = None
    query: str


def require_admin(current_user: dict = Depends(get_current_user)):
    """
    Dependency to require admin role
    
    Raises HTTPException if user is not admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user


@router.post("/query", response_model=AdminQueryResponse)
async def admin_query(
    request: AdminQueryRequest,
    current_user: dict = Depends(require_admin)
):
    """
    Process natural language query for admin.
    
    The AI will generate SQL queries automatically based on your request.
    
    Example queries:
    - "Cho tôi danh sách 10 bookings gần nhất"
    - "Thống kê revenue theo tháng trong năm 2024"
    - "Top 5 tour có nhiều booking nhất"
    - "Số lượng users đăng ký trong tuần này"
    - "Tổng doanh thu của tháng 12"
    
    Args:
        request: Query request with natural language message
        current_user: Current admin user (injected by dependency)
        
    Returns:
        Query results as formatted response
    """
    try:
        user_id = str(current_user["user_id"])
        logger.info(f"🔍 Admin query from {user_id}: {request.message[:50]}...")
        
        # Get admin agent
        admin_agent = get_admin_agent()
        
        # Process query
        result = await admin_agent.process_query(
            query=request.message,
            user_id=user_id,
            session_id=request.session_id
        )
        
        return AdminQueryResponse(
            success=result.get("success", False),
            response=result.get("response"),
            tool_calls=result.get("tool_calls"),
            error=result.get("error"),
            query=request.message
        )
        
    except Exception as e:
        logger.error(f"❌ Admin query error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )

