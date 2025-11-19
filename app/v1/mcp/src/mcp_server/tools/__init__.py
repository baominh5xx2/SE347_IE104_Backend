"""Tools package - Register all MCP tools"""
from fastmcp import FastMCP
from .weather_tools import register_weather_tools
from .flight_tools import register_flight_tools
from .booking_tools import register_booking_tools
from .search_personalization import register_search_personalization_tools
from .tour_search_tools import register_tour_search_tools


def register_all_tools(mcp: FastMCP):
    """
    Register all MCP tools
    
    Args:
        mcp: FastMCP server instance
    """
    register_weather_tools(mcp)
    register_flight_tools(mcp)
    register_booking_tools(mcp)
    register_search_personalization_tools(mcp)
    register_tour_search_tools(mcp)

__all__ = [
    "register_all_tools",
    "register_weather_tools",
    "register_flight_tools",
    "register_booking_tools",
    "register_search_personalization_tools",
    "register_tour_search_tools"
]
