"""
Agent Management API Endpoints
"""
import logging
from fastapi import APIRouter
from typing import Dict, Any
from ...services.agent_services import supervisor_graph
from ...services.agent_services.config import agent_config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_agent_status():
    """
    Get agent system status
    
    Returns:
        Agent status information
    """
    try:
        return {
            "status": "running",
            "agent_type": "supervisor_graph",
            "config": {
                "model": agent_config.model,
                "temperature": agent_config.temperature,
                "max_iterations": agent_config.max_iterations,
                "streaming": agent_config.enable_streaming
            }
        }
    except Exception as e:
        logger.error(f"Error getting agent status: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/graph")
async def get_agent_graph():
    """
    Get LangGraph structure information
    
    Returns:
        Graph structure and flow information
    """
    try:
        graph = supervisor_graph.graph
        
        return {
            "graph_type": "StateGraph",
            "nodes": [
                "chat_llm",
                "chat_tools",
                "recommendation_agent"
            ],
            "flow": {
                "start": "chat_llm",
                "edges": [
                    "START -> chat_llm",
                    "chat_llm -> (conditional) -> chat_tools or END",
                    "chat_tools -> (conditional) -> recommendation_agent or chat_llm",
                    "recommendation_agent -> chat_llm",
                    "chat_llm -> END"
                ]
            },
            "description": "Multi-agent system with tool calling loop"
        }
    except Exception as e:
        logger.error(f"Error getting graph info: {str(e)}")
        return {
            "error": str(e)
        }


@router.get("/info")
async def get_agent_info():
    """
    Get detailed agent information
    
    Returns:
        Comprehensive agent information
    """
    try:
        return {
            "name": "Tour Booking AI System",
            "version": "2.1.0",
            "description": "LangGraph dual-agent system with MCP integration and tool calling loop",
            "agents": [
                {
                    "name": "Chat Agent",
                    "description": "Main conversational agent with tool calling loop",
                    "tools": "Multiple tools including recommendation requests"
                },
                {
                    "name": "Recommendation Agent",
                    "description": "Provides tour recommendations",
                    "triggered_by": "Chat Agent via tool call"
                }
            ],
            "features": [
                "Tool calling loop",
                "Conditional routing",
                "Conversation memory",
                "MCP integration"
            ],
            "config": {
                "model": agent_config.model,
                "temperature": agent_config.temperature,
                "max_iterations": agent_config.max_iterations
            }
        }
    except Exception as e:
        logger.error(f"Error getting agent info: {str(e)}")
        return {
            "error": str(e)
        }
