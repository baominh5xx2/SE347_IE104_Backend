"""
AI Assistant MCP Server
Professional FastMCP implementation with modular architecture
"""
import os
import asyncio
from fastmcp import FastMCP
from src.core.config import settings
from src.tools.weather_tools import register_weather_tools
from src.tools.flight_tools import register_flight_tools
from src.tools.booking_tools import register_booking_tools
from src.tools.search_personalization import register_search_personalization_tools
from src.tools.tour_search_tools import register_tour_search_tools
from src.resources import register_all_resources
from src.prompts import register_all_prompts
from src.utils import setup_logging

# Setup logging
setup_logging(settings.LOG_LEVEL)

# Initialize Main FastMCP server
mcp = FastMCP(
    name=settings.SERVER_NAME,
    version=settings.SERVER_VERSION,
    log_level=settings.LOG_LEVEL
)

# Create Sub-servers for better organization (Composition Pattern)
weather_server = FastMCP(name="Weather")
flight_server = FastMCP(name="Flight")
booking_server = FastMCP(name="Booking")
search_server = FastMCP(name="Search")

# Register tools to sub-servers
register_weather_tools(weather_server)
register_flight_tools(flight_server)
register_booking_tools(booking_server)
register_search_personalization_tools(search_server)
register_tour_search_tools(search_server)

# Import sub-servers into main (static composition, no prefixes to keep original tool names)
async def compose_servers():
    await mcp.import_server(weather_server)
    await mcp.import_server(flight_server)
    await mcp.import_server(booking_server)
    await mcp.import_server(search_server)

# Run composition once at import time
asyncio.run(compose_servers())

# Register resources and prompts to main server (or organize similarly if needed)
register_all_resources(mcp)
register_all_prompts(mcp)

if __name__ == "__main__":
    # Get port from env or default to 8001
    port = int(os.getenv("PORT", 8001))
    # Run with SSE transport
    mcp.run(transport="sse", port=port, host="0.0.0.0")