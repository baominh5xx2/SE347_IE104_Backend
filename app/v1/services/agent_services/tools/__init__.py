
"""
Agent Tools Module
Tools for agents to use
"""
from typing import List
from langchain_core.tools import StructuredTool
from .mcp_tools import (
    create_booking_tool,
    request_recommendation_tool,
    search_flights_tool,
    get_current_temperature_tool,
    get_weather_forecast_tool,
    search_episodes_tool
)

__all__ = ["get_chat_tools"]


def get_chat_tools() -> List[StructuredTool]:
    """
    Get all tools available to Chat Agent
    
    Returns:
        List of StructuredTool instances
    """
    return [
        create_booking_tool(),
        request_recommendation_tool(),
        search_flights_tool(),
        get_current_temperature_tool(),
        get_weather_forecast_tool(),
        search_episodes_tool()
    ]

