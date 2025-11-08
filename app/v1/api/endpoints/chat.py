"""
Chat API Endpoints
"""
import logging
import uuid
from fastapi import APIRouter, HTTPException
from typing import Optional
from ...schema.agent_schema import ChatRequest, ChatResponse, ConversationHistory
from ...services.agent_services import supervisor_graph
from ...services.agent_services.memory import conversation_memory
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat message and get AI response
    
    Args:
        request: Chat request with message and optional conversation_id
        
    Returns:
        ChatResponse with assistant's response
    """
    try:
        # Generate conversation_id if not provided
        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        user_id = request.user_id or "anonymous_user"
        
        # Process message through supervisor graph
        result = await supervisor_graph.process_message(
            user_message=request.message,
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        # Extract response
        response_message = result.get("response", "Xin lỗi, không thể xử lý yêu cầu của bạn.")
        
        # Store episode in memory if available
        try:
            await conversation_memory.store_episode(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=request.message,
                assistant_response=response_message,
                metadata=result.get("metadata", {})
            )
        except Exception as e:
            logger.warning(f"Failed to store episode: {str(e)}")
        
        return ChatResponse(
            conversation_id=conversation_id,
            message=response_message,
            metadata={
                "recommendations": result.get("recommendations", []),
                **result.get("metadata", {})
            },
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str):
    """
    Get conversation history by conversation_id
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        ConversationHistory with messages
    """
    try:
        # Get memory for this conversation
        memory = conversation_memory.get_memory(conversation_id)
        
        # Convert messages to schema format
        messages = []
        for msg in memory.messages:
            from ...schema.agent_schema import Message, MessageRole
            role = MessageRole.USER if msg.type == "human" else MessageRole.ASSISTANT
            messages.append(Message(
                role=role,
                content=msg.content,
                timestamp=datetime.now()
            ))
        
        return ConversationHistory(
            conversation_id=conversation_id,
            messages=messages,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation and its history
    
    Args:
        conversation_id: Conversation ID to delete
        
    Returns:
        Success message
    """
    try:
        # Delete from memory storage
        if conversation_id in conversation_memory.memory_storage:
            del conversation_memory.memory_storage[conversation_id]
        
        return {
            "message": f"Conversation {conversation_id} deleted successfully",
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
