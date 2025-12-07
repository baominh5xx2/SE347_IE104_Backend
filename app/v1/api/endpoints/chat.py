"""
Chat API Endpoints
"""
import logging
import uuid
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
from ...schema.agent_schema import ChatRequest, ChatResponse, ConversationHistory
from ...services.agent_services import supervisor_graph
from ...services.agent_services.memory import conversation_memory
from ...core.dependencies import get_current_user, get_chat_room_service
from ...services.chat_room_service import ChatRoomService
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    chat_room_service: ChatRoomService = Depends(get_chat_room_service)
):
    """
    Send a chat message and get AI response via streaming
    Tự động tạo room nếu chưa có và lưu messages vào database
    """
    try:
        user_id = str(current_user["user_id"])
        
        # Nếu có conversation_id, dùng làm room_id
        # Nếu không có, tạo room mới
        room_id = None
        if request.conversation_id:
            # Check room exists
            room_result = chat_room_service.get_room_by_id(request.conversation_id, user_id)
            if room_result["EC"] == 0:
                room_id = request.conversation_id
            else:
                # Room không tồn tại hoặc không thuộc user, tạo mới
                room_result = chat_room_service.create_room(user_id)
                if room_result["EC"] == 0:
                    room_id = str(room_result["data"]["room_id"])
        else:
            # Tạo room mới
            room_result = chat_room_service.create_room(user_id)
            if room_result["EC"] == 0:
                room_id = str(room_result["data"]["room_id"])
        
        if not room_id:
            raise HTTPException(status_code=500, detail="Failed to create or get chat room")
        
        conversation_id = room_id  # Use room_id as conversation_id
        
        # Lưu user message vào database
        try:
            chat_room_service.save_message(
                room_id=room_id,
                user_id=user_id,
                role="user",
                content=request.message
            )
        except Exception as e:
            logger.warning(f"Failed to save user message: {str(e)}")
        
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
                tour_packages = []
                metadata = {}
                
                # Track MCP UI data and whether tokens have been streamed
                pending_mcp_ui_resource = None
                pending_mcp_ui_html = None
                pending_tour_packages = None
                has_streamed_tokens = False
                
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
                            has_streamed_tokens = True
                            
                            # If we have pending MCP UI and now have tokens, send it
                            if pending_mcp_ui_resource or pending_mcp_ui_html or pending_tour_packages:
                                if pending_mcp_ui_resource and isinstance(pending_mcp_ui_resource, dict):
                                    if 'uri' in pending_mcp_ui_resource:
                                        pending_mcp_ui_resource['uri'] = str(pending_mcp_ui_resource['uri'])
                                
                                ui_event = {
                                    "type": "mcp_ui",
                                    "ui_resource": pending_mcp_ui_resource,
                                    "html": pending_mcp_ui_html,  # Keep for backward compatibility
                                    "tourPackages": pending_tour_packages  # New: Send tour packages data
                                }
                                logger.info(f"📤 Streaming MCP UI event (after tokens): {len(pending_tour_packages) if pending_tour_packages else 0} tour packages")
                                yield f"data: {json.dumps(ui_event, ensure_ascii=False)}\n\n"
                                
                                # Clear pending
                                pending_mcp_ui_resource = None
                                pending_mcp_ui_html = None
                                pending_tour_packages = None
                    
                    # Track final state
                    elif event_type == "on_chain_end":
                        chain_output = event.get("data", {}).get("output", {})
                        if isinstance(chain_output, dict):
                            if "final_response" in chain_output:
                                full_response = chain_output.get("final_response", full_response)
                            if "recommended_package_ids" in chain_output:
                                recommendations = chain_output.get("recommended_package_ids", [])
                            if "tour_packages" in chain_output:
                                tour_packages = chain_output.get("tour_packages", [])
                            if "metadata" in chain_output:
                                metadata = chain_output.get("metadata", {})
                            
                            # Check for MCP UI Resource updates
                            mcp_ui_resource = chain_output.get("mcp_ui_resource")
                            mcp_ui_html = chain_output.get("mcp_ui_html")
                            tour_packages_for_ui = chain_output.get("tour_packages", [])
                            
                            # Only send tour packages if this is a recommendation response (check URI)
                            is_recommendation_response = False
                            if mcp_ui_resource and isinstance(mcp_ui_resource, dict):
                                uri = str(mcp_ui_resource.get('uri', ''))
                                if 'tour-recommendations' in uri:
                                    is_recommendation_response = True
                            
                            # Only include tour packages if this is a recommendation response
                            if mcp_ui_resource or mcp_ui_html or (tour_packages_for_ui and is_recommendation_response):
                                # Convert AnyUrl objects to strings if present in mcp_ui_resource
                                if mcp_ui_resource and isinstance(mcp_ui_resource, dict):
                                    if 'uri' in mcp_ui_resource:
                                        mcp_ui_resource['uri'] = str(mcp_ui_resource['uri'])
                                
                                # If tokens have already been streamed, send UI immediately
                                if has_streamed_tokens:
                                    ui_event = {
                                        "type": "mcp_ui",
                                        "ui_resource": mcp_ui_resource,
                                        "html": mcp_ui_html,  # Keep for backward compatibility
                                        "tourPackages": tour_packages_for_ui[:5] if (tour_packages_for_ui and is_recommendation_response) else None  # Only send if recommendation
                                    }
                                    logger.info(f"📤 Streaming MCP UI event (tokens already streamed): {len(tour_packages_for_ui) if (tour_packages_for_ui and is_recommendation_response) else 0} tour packages")
                                    yield f"data: {json.dumps(ui_event, ensure_ascii=False)}\n\n"
                                else:
                                    # Store for later (will be sent when first token arrives)
                                    pending_mcp_ui_resource = mcp_ui_resource
                                    pending_mcp_ui_html = mcp_ui_html
                                    pending_tour_packages = tour_packages_for_ui[:5] if (tour_packages_for_ui and is_recommendation_response) else None
                                    logger.info(f"⏳ MCP UI pending (waiting for tokens): {len(tour_packages_for_ui) if (tour_packages_for_ui and is_recommendation_response) else 0} tour packages")
                
                # If we still have pending MCP UI but no tokens were streamed (edge case), send it at the end
                if (pending_mcp_ui_resource or pending_mcp_ui_html or pending_tour_packages) and not has_streamed_tokens:
                    if pending_mcp_ui_resource and isinstance(pending_mcp_ui_resource, dict):
                        if 'uri' in pending_mcp_ui_resource:
                            pending_mcp_ui_resource['uri'] = str(pending_mcp_ui_resource['uri'])
                    
                    ui_event = {
                        "type": "mcp_ui",
                        "ui_resource": pending_mcp_ui_resource,
                        "html": pending_mcp_ui_html,  # Keep for backward compatibility
                        "tourPackages": pending_tour_packages  # Only set if recommendation response
                    }
                    logger.info(f"📤 Streaming MCP UI event (no tokens, sending at end): {len(pending_tour_packages) if pending_tour_packages else 0} tour packages")
                    yield f"data: {json.dumps(ui_event, ensure_ascii=False)}\n\n"
                
                # Send recommendations (full tour packages) if available
                if recommendations or tour_packages:
                    # Use tour_packages if available (has full details), otherwise use IDs
                    rec_data = tour_packages if tour_packages else recommendations
                    rec_event = {
                        "type": "recommendations",
                        "data": rec_data
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
                
                # Lưu assistant response vào database
                try:
                    chat_room_service.save_message(
                        room_id=room_id,
                        user_id=user_id,
                        role="assistant",
                        content=full_response,
                        intent=metadata.get("intent") if metadata else None,
                        entities=metadata.get("entities") if metadata else None
                    )
                    
                    # Update room title từ message đầu tiên nếu chưa có title tùy chỉnh
                    if full_response:
                        # Check if this is first message in room
                        msg_count_result = chat_room_service.supabase.table('chat_history')\
                            .select("*", count="exact")\
                            .eq('room_id', room_id)\
                            .execute()
                        msg_count = msg_count_result.count if hasattr(msg_count_result, 'count') else 0
                        
                        # Nếu chỉ có 2 messages (user + assistant), update title
                        if msg_count == 2:
                            title = chat_room_service.auto_generate_title(request.message)
                            chat_room_service.update_room(room_id, user_id, title=title)
                except Exception as e:
                    logger.warning(f"Failed to save assistant message: {str(e)}")
                
                # Store episode in memory (without large tour_packages data to avoid metadata limit)
                try:
                    # Only store lightweight metadata to avoid Mem0 2000 char limit
                    storage_metadata = metadata.copy() if metadata else {}
                    
                    # Remove large data that would exceed Mem0 limit
                    storage_metadata.pop('tour_packages', None)
                    storage_metadata.pop('recommended_package_ids', None)
                    
                    await conversation_memory.store_episode(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        user_message=request.message,
                        assistant_response=full_response,
                        metadata=storage_metadata
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
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    chat_room_service: ChatRoomService = Depends(get_chat_room_service)
):
    """
    Send a chat message and get AI response
    
    Args:
        request: Chat request with message and optional conversation_id
        current_user: Current authenticated user
        chat_room_service: ChatRoomService instance
        
    Returns:
        ChatResponse with assistant's response
    """
    try:
        user_id = str(current_user["user_id"])
        
        # Nếu có conversation_id, dùng làm room_id
        # Nếu không có, tạo room mới
        room_id = None
        if request.conversation_id:
            # Check room exists
            room_result = chat_room_service.get_room_by_id(request.conversation_id, user_id)
            if room_result["EC"] == 0:
                room_id = request.conversation_id
            else:
                # Room không tồn tại hoặc không thuộc user, tạo mới
                room_result = chat_room_service.create_room(user_id)
                if room_result["EC"] == 0:
                    room_id = str(room_result["data"]["room_id"])
        else:
            # Tạo room mới
            room_result = chat_room_service.create_room(user_id)
            if room_result["EC"] == 0:
                room_id = str(room_result["data"]["room_id"])
        
        if not room_id:
            raise HTTPException(status_code=500, detail="Failed to create or get chat room")
        
        conversation_id = room_id  # Use room_id as conversation_id
        
        # Lưu user message vào database
        try:
            chat_room_service.save_message(
                room_id=room_id,
                user_id=user_id,
                role="user",
                content=request.message
            )
        except Exception as e:
            logger.warning(f"Failed to save user message: {str(e)}")
        
        # Process message through supervisor graph
        result = await supervisor_graph.process_message(
            user_message=request.message,
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        # Extract response
        response_message = result.get("response", "Xin lỗi, không thể xử lý yêu cầu của bạn.")
        
        # Lưu assistant response vào database
        try:
            metadata = result.get("metadata", {})
            chat_room_service.save_message(
                room_id=room_id,
                user_id=user_id,
                role="assistant",
                content=response_message,
                intent=metadata.get("intent") if metadata else None,
                entities=metadata.get("entities") if metadata else None
            )
            
            # Update room title từ message đầu tiên nếu chưa có title tùy chỉnh
            # Check if this is first message in room
            msg_count_result = chat_room_service.supabase.table('chat_history')\
                .select("*", count="exact")\
                .eq('room_id', room_id)\
                .execute()
            msg_count = msg_count_result.count if hasattr(msg_count_result, 'count') else 0
            
            # Nếu chỉ có 2 messages (user + assistant), update title
            if msg_count == 2:
                title = chat_room_service.auto_generate_title(request.message)
                chat_room_service.update_room(room_id, user_id, title=title)
        except Exception as e:
            logger.warning(f"Failed to save assistant message: {str(e)}")
        
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
