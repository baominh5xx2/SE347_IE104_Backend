"""
Agent State Definitions
Shared state schemas for multi-agent system
"""
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """
    Shared state between all agents
    
    Extends MessagesState from LangGraph for proper message handling.
    All agents can read/write to this shared state.
    """
    # Conversation context
    conversation_id: str
    user_id: str
    
    # Chat Agent outputs
    chat_response: str
    
    # Recommendation Agent outputs
    needs_recommendation: bool
    recommendation_params: Dict[str, Any]
    
    # Shared data
    recommended_package_ids: List[str]
    tour_packages: List[Dict[str, Any]]  # Full tour package objects for API response
    
    # Final output
    final_response: str
