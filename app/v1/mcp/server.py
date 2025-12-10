"""
AI Assistant MCP Server
Professional FastMCP implementation with modular architecture
"""
import os
import asyncio
import threading
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

# Lazy initialization flag with thread lock
_servers_composed = False
_composition_lock = threading.Lock()

def ensure_servers_composed():
    """Ensure servers are composed, using thread-safe approach"""
    global _servers_composed
    if _servers_composed:
        return
    
    with _composition_lock:
        # Double-check after acquiring lock
        if _servers_composed:
            return
        
        import threading
        
        # Use a separate thread to run the async composition
        # This avoids conflicts with uvicorn's event loop
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(compose_servers())
            finally:
                new_loop.close()
        
        thread = threading.Thread(target=run_in_thread, daemon=False)
        thread.start()
        thread.join(timeout=10.0)  # Wait max 10 seconds
        
        if thread.is_alive():
            raise RuntimeError("Server composition timed out")
        
        _servers_composed = True

# Compose servers lazily - only when needed
# This will be called when mcp.http_app() is accessed or when server is used
try:
    # Try to compose immediately if no event loop is running
    loop = asyncio.get_event_loop()
    if not loop.is_running():
        loop.run_until_complete(compose_servers())
        _servers_composed = True
    else:
        # Event loop is running, defer to lazy initialization
        pass
except RuntimeError:
    # No event loop exists, create one
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(compose_servers())
        _servers_composed = True
    finally:
        loop.close()
except Exception:
    # If anything fails, defer to lazy initialization
    pass

# Register resources and prompts to main server (or organize similarly if needed)
register_all_resources(mcp)
register_all_prompts(mcp)

# Wrap http_app to ensure composition before use
_original_http_app = mcp.http_app

def http_app(path: str = ""):
    """Wrapper to ensure servers are composed before creating http app"""
    ensure_servers_composed()
    return _original_http_app(path)

# Monkey patch to use our wrapper
mcp.http_app = http_app

if __name__ == "__main__":
    # Get port from env or default to 8001
    port = int(os.getenv("PORT", 8001))
    # Run with SSE transport
    mcp.run(transport="sse", port=port, host="0.0.0.0")