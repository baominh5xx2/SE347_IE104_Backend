"""
Chat Room API Endpoints
Endpoints để quản lý chat rooms và messages
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from uuid import UUID
from ...schema.chat_schema import (
    ChatRoomCreate,
    ChatRoomCreateResponse,
    ChatRoomListResponse,
    ChatRoomDetailResponse,
    ChatRoomUpdateRequest,
    ChatMessagesResponse
)
from ...core.dependencies import get_current_user, get_chat_room_service
from ...services.chat_room_service import ChatRoomService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/rooms", response_model=ChatRoomCreateResponse)
async def create_room(
    room_data: ChatRoomCreate,
    current_user: dict = Depends(get_current_user),
    service: ChatRoomService = Depends(get_chat_room_service)
):
    """
    Tạo chat room mới
    
    Args:
        room_data: Room data với optional title
        current_user: Current authenticated user
        service: ChatRoomService instance
        
    Returns:
        ChatRoomCreateResponse với room data
    """
    try:
        user_id = str(current_user["user_id"])
        result = service.create_room(
            user_id=user_id,
            title=room_data.title
        )
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return ChatRoomCreateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_room endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms", response_model=ChatRoomListResponse)
async def get_rooms(
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    limit: int = Query(50, ge=1, le=100, description="Number of rooms per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: dict = Depends(get_current_user),
    service: ChatRoomService = Depends(get_chat_room_service)
):
    """
    Lấy danh sách chat rooms của user
    
    Args:
        archived: Filter theo archived status (None = all, True = archived only, False = not archived)
        limit: Số lượng rooms tối đa
        offset: Offset cho pagination
        current_user: Current authenticated user
        service: ChatRoomService instance
        
    Returns:
        ChatRoomListResponse với list rooms
    """
    try:
        user_id = str(current_user["user_id"])
        result = service.get_user_rooms(
            user_id=user_id,
            archived=archived,
            limit=limit,
            offset=offset
        )
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return ChatRoomListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_rooms endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms/{room_id}", response_model=ChatRoomDetailResponse)
async def get_room(
    room_id: UUID,
    current_user: dict = Depends(get_current_user),
    service: ChatRoomService = Depends(get_chat_room_service)
):
    """
    Lấy thông tin chi tiết một room
    
    Args:
        room_id: ID của room
        current_user: Current authenticated user
        service: ChatRoomService instance
        
    Returns:
        ChatRoomDetailResponse với room data
    """
    try:
        user_id = str(current_user["user_id"])
        result = service.get_room_by_id(
            room_id=str(room_id),
            user_id=user_id
        )
        
        if result["EC"] != 0:
            status_code = 404 if result["EC"] == 404 else 400
            raise HTTPException(status_code=status_code, detail=result["EM"])
        
        return ChatRoomDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_room endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms/{room_id}/messages", response_model=ChatMessagesResponse)
async def get_room_messages(
    room_id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Number of messages per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: dict = Depends(get_current_user),
    service: ChatRoomService = Depends(get_chat_room_service)
):
    """
    Lấy lịch sử messages của một room
    
    Args:
        room_id: ID của room
        limit: Số lượng messages tối đa
        offset: Offset cho pagination
        current_user: Current authenticated user
        service: ChatRoomService instance
        
    Returns:
        ChatMessagesResponse với list messages
    """
    try:
        user_id = str(current_user["user_id"])
        result = service.get_room_messages(
            room_id=str(room_id),
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        if result["EC"] != 0:
            status_code = 404 if result["EC"] == 404 else 400
            raise HTTPException(status_code=status_code, detail=result["EM"])
        
        return ChatMessagesResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_room_messages endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rooms/{room_id}", response_model=ChatRoomDetailResponse)
async def update_room(
    room_id: UUID,
    room_data: ChatRoomUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: ChatRoomService = Depends(get_chat_room_service)
):
    """
    Cập nhật room (title, archive status)
    
    Args:
        room_id: ID của room
        room_data: Update data (title, is_archived)
        current_user: Current authenticated user
        service: ChatRoomService instance
        
    Returns:
        ChatRoomDetailResponse với updated room data
    """
    try:
        user_id = str(current_user["user_id"])
        result = service.update_room(
            room_id=str(room_id),
            user_id=user_id,
            title=room_data.title,
            is_archived=room_data.is_archived
        )
        
        if result["EC"] != 0:
            status_code = 404 if result["EC"] == 404 else 400
            raise HTTPException(status_code=status_code, detail=result["EM"])
        
        return ChatRoomDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_room endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rooms/{room_id}")
async def delete_room(
    room_id: UUID,
    current_user: dict = Depends(get_current_user),
    service: ChatRoomService = Depends(get_chat_room_service)
):
    """
    Xóa room và tất cả messages
    
    Args:
        room_id: ID của room
        current_user: Current authenticated user
        service: ChatRoomService instance
        
    Returns:
        Success message
    """
    try:
        user_id = str(current_user["user_id"])
        result = service.delete_room(
            room_id=str(room_id),
            user_id=user_id
        )
        
        if result["EC"] != 0:
            status_code = 404 if result["EC"] == 404 else 400
            raise HTTPException(status_code=status_code, detail=result["EM"])
        
        return {
            "EC": 0,
            "EM": "Room deleted successfully",
            "data": result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_room endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

