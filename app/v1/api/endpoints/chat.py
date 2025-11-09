"""
Chat API Endpoints
"""
import logging
import uuid
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from ...schema.agent_schema import ChatRequest, ChatResponse, ConversationHistory
from ...services.agent_services import supervisor_graph
from ...services.agent_services.memory import conversation_memory
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Send a chat message and get AI response via streaming
    """
    try:
        # Generate conversation_id if not provided
        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        user_id = request.user_id or "anonymous_user"
        
        async def event_generator():
            try:
                # Send start event
                start_event = {
                    "type": "start",
                    "conversation_id": conversation_id,
                    "user_id": user_id
                }
                yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"
                
                # Track response for storage
                full_response = ""
                recommendations = []
                metadata = {}
                
                # Stream from LangGraph
                async for event in supervisor_graph.process_message_stream(
                    user_message=request.message,
                    conversation_id=conversation_id,
                    user_id=user_id
                ):
                    event_type = event.get("event", "")
                    
                    # Stream LLM tokens
                    if event_type == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk", {})
                        if hasattr(chunk, "content") and chunk.content:
                            token_event = {
                                "type": "token",
                                "content": chunk.content
                            }
                            yield f"data: {json.dumps(token_event, ensure_ascii=False)}\n\n"
                            full_response += chunk.content
                    
                    # Track final state
                    elif event_type == "on_chain_end":
                        chain_output = event.get("data", {}).get("output", {})
                        if isinstance(chain_output, dict):
                            if "final_response" in chain_output:
                                full_response = chain_output.get("final_response", full_response)
                            if "recommended_package_ids" in chain_output:
                                recommendations = chain_output.get("recommended_package_ids", [])
                            if "metadata" in chain_output:
                                metadata = chain_output.get("metadata", {})
                
                # Send recommendations if available
                if recommendations:
                    rec_event = {
                        "type": "recommendations",
                        "data": recommendations
                    }
                    yield f"data: {json.dumps(rec_event, ensure_ascii=False)}\n\n"
                
                # Send metadata
                metadata_event = {
                    "type": "metadata",
                    "conversation_id": conversation_id,
                    "metadata": metadata
                }
                yield f"data: {json.dumps(metadata_event, ensure_ascii=False)}\n\n"
                
                # Send done
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
                # Store episode in memory
                try:
                    await conversation_memory.store_episode(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        user_message=request.message,
                        assistant_response=full_response,
                        metadata=metadata
                    )
                except Exception as e:
                    logger.warning(f"Failed to store episode: {str(e)}")
                    
            except Exception as e:
                logger.error(f"Error in stream generator: {str(e)}")
                error_event = {"type": "error", "error": str(e)}
                yield f"data: {json.dumps(error_event)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in chat_stream endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
