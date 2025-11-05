"""
Agent Management Endpoints
"""
from fastapi import APIRouter, HTTPException, status
from app.v1.services.agent_services import supervisor_graph

router = APIRouter()


@router.get("/status")
async def get_agent_status():
    """
    Get agent status and information
    
    Returns:
        Agent status information
    """
    try:
        return {
            "status": "active",
            "agent_type": "LangGraph",
            "model": "gpt-5-mini",
            "capabilities": [
                "conversational_ai",
                "context_awareness",
                "multi_step_reasoning",
                "tour_recommendations",
                "booking_management"
            ],
            "agents": [
                "Chat Agent",
                "Recommendation Agent"
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent status: {str(e)}"
        )


@router.get("/graph")
async def get_graph_structure():
    """
    Get the LangGraph workflow structure
    
    Returns:
        Graph structure visualization
    """
    try:
        return {
            "graph_structure": "Supervisor Graph - Multi-Agent System",
            "nodes": [
                "chat_llm",
                "chat_tools",
                "recommendation_agent"
            ],
            "edges": [
                {"from": "START", "to": "chat_llm"},
                {"from": "chat_llm", "to": "chat_tools", "condition": "has_tool_calls"},
                {"from": "chat_llm", "to": "END", "condition": "no_tool_calls"},
                {"from": "chat_tools", "to": "recommendation_agent", "condition": "recommendation_requested"},
                {"from": "chat_tools", "to": "chat_llm", "condition": "no_recommendation"},
                {"from": "recommendation_agent", "to": "END"}
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting graph structure: {str(e)}"
        )


@router.get("/info")
async def get_agent_info():
    """
    Get detailed agent information
    
    Returns:
        Detailed agent information
    """
    try:
        return {
            "name": "LangGraph AI Assistant",
            "version": "1.0.0",
            "description": "AI assistant powered by LangGraph for multi-step reasoning and conversation",
            "features": [
                "Multi-turn conversations",
                "Context-aware responses",
                "State management",
                "Iterative reasoning",
                "Response validation"
            ],
            "workflow_steps": [
                {
                    "step": "process_input",
                    "description": "Process and prepare user input with context"
                },
                {
                    "step": "generate_response",
                    "description": "Generate AI response using LLM"
                },
                {
                    "step": "validate_response",
                    "description": "Validate response quality and completeness"
                }
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent info: {str(e)}"
        )
