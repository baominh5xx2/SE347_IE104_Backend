"""
Chat Endpoints - Using LangGraph Dual Agent System
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from app.v1.schema import ChatRequest, ChatResponse
from app.v1.services.agent_services import dual_agent_system
from app.v1.core.supabase import supabase_client
from datetime import datetime
import json

router = APIRouter()


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest):
    """
    Process a chat message using LangGraph dual-agent system
    
    Flow:
    1. Chat Agent analyzes intent and extracts entities
    2. If needs recommendation → Recommendation Agent finds tours
    3. Final response generated
    
    Args:
        request: Chat request with message
        
    Returns:
        ChatResponse with agent's response and recommendations
    """
    try:
        # Get conversation history for this specific conversation
        history = []
        try:
            # If conversation_id is provided, get history for that conversation
            if request.conversation_id:
                response = supabase_client.table("chat_history")\
                    .select("*")\
                    .eq("conversation_id", request.conversation_id)\
                    .order("created_at", desc=True)\
                    .limit(10)\
                    .execute()
            else:
                # For new conversations, get recent history (fallback)
                response = supabase_client.table("chat_history")\
                    .select("*")\
                    .order("created_at", desc=True)\
                    .limit(10)\
                    .execute()
            
            if response.data:
                history = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in reversed(response.data)
                ]
        except:
            pass
        
        # Generate unique IDs if not provided
        import uuid
        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        user_id = request.user_id or f"user_{uuid.uuid4().hex[:12]}"
        
        # Process through LangGraph dual agent system
        result = await dual_agent_system.process_message(
            user_message=request.message,
            conversation_history=history,
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        # Save conversation to database
        try:
            # Save user message
            supabase_client.table("chat_history").insert({
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": "user",
                "content": request.message,
                "intent": None,
                "entities": None
            }).execute()
            
            # Save assistant response
            supabase_client.table("chat_history").insert({
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": "assistant",
                "content": result["response"],
                "intent": None,
                "entities": None
            }).execute()
        except Exception as e:
            print(f"Warning: Could not save to database: {e}")
        
        return ChatResponse(
            conversation_id=conversation_id,
            message=result["response"],
            metadata={
                "user_id": user_id
            },
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}"
        )


@router.post("/stream", include_in_schema=True)
@router.post("/stream/", include_in_schema=False)
async def chat_stream(request: ChatRequest):
    """
    Stream chat response token by token using LangGraph
    
    Args:
        request: Chat request with message
        
    Returns:
        StreamingResponse with tokens
    """
    async def generate():
        try:
            # Get conversation history for this specific conversation
            history = []
            try:
                # If conversation_id is provided, get history for that conversation
                if request.conversation_id:
                    response = supabase_client.table("chat_history")\
                        .select("*")\
                        .eq("conversation_id", request.conversation_id)\
                        .order("created_at", desc=True)\
                        .limit(10)\
                        .execute()
                else:
                    # For new conversations, get recent history (fallback)
                    response = supabase_client.table("chat_history")\
                        .select("*")\
                        .order("created_at", desc=True)\
                        .limit(10)\
                        .execute()
                
                if response.data:
                    history = [
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in reversed(response.data)
                    ]
            except:
                pass
            
            # Generate unique IDs if not provided
            import uuid
            conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
            user_id = request.user_id or f"user_{uuid.uuid4().hex[:12]}"
            
            # Stream through agents
            async for event in dual_agent_system.stream_message(
                user_message=request.message,
                conversation_history=history,
                conversation_id=conversation_id,
                user_id=user_id
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


@router.get("/history", include_in_schema=True)
@router.get("/history/", include_in_schema=False)
async def get_conversation_history(conversation_id: str = None, limit: int = 20):
    """
    Get conversation history
    
    Args:
        conversation_id: Optional conversation ID to filter by
        limit: Number of recent messages to retrieve
        
    Returns:
        List of conversation messages
    """
    try:
        query = supabase_client.table("chat_history").select("*")
        
        # Filter by conversation_id if provided
        if conversation_id:
            query = query.eq("conversation_id", conversation_id)
        
        response = query.order("created_at", desc=True).limit(limit).execute()
        
        if response.data:
            history = [
                {
                    "message_id": msg["message_id"],
                    "conversation_id": msg["conversation_id"],
                    "user_id": msg["user_id"],
                    "role": msg["role"],
                    "content": msg["content"],
                    "intent": msg["intent"],
                    "entities": msg["entities"],
                    "created_at": msg.get("created_at")
                }
                for msg in reversed(response.data)
            ]
        else:
            history = []
        
        return {
            "conversation_id": conversation_id,
            "messages": history,
            "total": len(history)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving conversation history: {str(e)}"
        )
