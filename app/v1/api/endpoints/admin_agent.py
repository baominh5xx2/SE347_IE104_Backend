"""
Admin Agent API Endpoints
Natural language database queries for admin
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from datetime import datetime
from ...core.dependencies import get_current_user, get_current_admin, get_chat_room_service
from ...services.agent_support_admin import get_admin_agent
from ...services.chat_room_service import ChatRoomService
from ...schema.agent_schema import ConversationHistory, Message, MessageRole

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
        description="Session ID for conversation memory (Chat Room ID)"
    )


class AdminQueryResponse(BaseModel):
    """Response schema for admin query"""
    success: bool
    response: Optional[str] = None
    tool_calls: Optional[list] = None
    error: Optional[str] = None
    query: str
    session_id: Optional[str] = None


@router.post("/query", response_model=AdminQueryResponse)
async def admin_query(
    request: AdminQueryRequest,
    current_user: dict = Depends(get_current_admin),
    chat_room_service: ChatRoomService = Depends(get_chat_room_service)
):
    """
    Process natural language query for admin.
    AUTO-SAVES chat history to database.
    """
    try:
        user_id = str(current_user["user_id"])
        logger.info(f"🔍 Admin query from {user_id}: {request.message[:50]}...")
        
        # 1. Handle Chat Room (Session)
        room_id = request.session_id
        if room_id:
            # Verify room exists and belongs to admin
            check = chat_room_service.get_room_by_id(room_id, user_id)
            if check["EC"] != 0:
                # Room invalid, create new
                room_id = None
        
        if not room_id:
            # Create new room
            title = request.message[:50] + "..." if len(request.message) > 50 else request.message
            room_res = chat_room_service.create_room(user_id, title)
            if room_res["EC"] == 0:
                room_id = str(room_res["data"]["room_id"])
            else:
                raise HTTPException(status_code=500, detail="Failed to create chat room")

        # 2. Save User Message
        chat_room_service.save_message(
            room_id=room_id,
            user_id=user_id,
            role="admin",
            content=request.message
        )

        # 3. Process Query with Admin Agent
        admin_agent = get_admin_agent()
        result = await admin_agent.process_query(
            query=request.message,
            user_id=user_id,
            session_id=room_id
        )
        
        # 4. Save Agent Response
        agent_response = result.get("response")
        if agent_response:
             chat_room_service.save_message(
                room_id=room_id,
                user_id=user_id,
                role="assistant",
                content=agent_response,
                intent="admin_query"
            )

        return AdminQueryResponse(
            success=result.get("success", False),
            response=agent_response,
            tool_calls=result.get("tool_calls"),
            error=result.get("error"),
            query=request.message,
            session_id=room_id
        )
        
    except Exception as e:
        logger.error(f"❌ Admin query error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


@router.get("/conversations", response_model=list)
async def get_admin_conversations(
    current_user: dict = Depends(get_current_admin),
    chat_room_service: ChatRoomService = Depends(get_chat_room_service),
    limit: int = 20,
    offset: int = 0
):
    """Get list of admin conversations"""
    user_id = str(current_user["user_id"])
    result = chat_room_service.get_user_rooms(user_id, limit=limit, offset=offset)
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result["data"]


@router.get("/conversations/{conversation_id}/messages", response_model=list)
async def get_conversation_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_admin),
    chat_room_service: ChatRoomService = Depends(get_chat_room_service),
    limit: int = 50
):
    """Get messages for a specific conversation"""
    user_id = str(current_user["user_id"])
    result = chat_room_service.get_room_messages(conversation_id, user_id, limit=limit)
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result["data"]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_admin),
    chat_room_service: ChatRoomService = Depends(get_chat_room_service)
):
    """Delete a conversation"""
    user_id = str(current_user["user_id"])
    result = chat_room_service.delete_room(conversation_id, user_id)
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return {"success": True, "message": "Deleted successfully"}

