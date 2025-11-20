"""
MCP Tools
Tools that call MCP server directly
"""
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import asyncio
import concurrent.futures
import logging
import json
from fastmcp import Client
from app.v1.core.config import settings
from app.v1.schema.shema_tool_mcp import (
    SearchTourPackagesInput,
    CreateBookingInput,
    RequestRecommendationInput,
    SearchFlightsInput,
    GetCurrentTemperatureInput,
    GetWeatherForecastInput,
    SearchEpisodesInput
)
from app.v1.mcp.src.schema import (
    GetUserBookingsInput,
    UpdateBookingInput,
    DeleteBookingInput
)

logger = logging.getLogger(__name__)


# ============================================================================
# MCP CLIENT HELPER
# ============================================================================

async def call_mcp_tool(tool_name: str, params: Dict[str, Any]) -> Any:
    """
    Generic function to call any MCP tool
    
    Args:
        tool_name: Name of the MCP tool
        params: Tool parameters
        
    Returns:
        Tool result (parsed from JSON if possible)
    """
    # Get MCP config
    from app.v1.core.prompts import PromptManager
    mcp_config = PromptManager().get_mcp_config()
    
    base_url = settings.MCP_SERVER_URL or mcp_config.get('server_url', 'http://localhost:8000/mcp/mcp')
    
    async with Client(base_url) as client:
        result = await client.call_tool(tool_name, params)
        
        # Handle CallToolResult object from FastMCP
        if hasattr(result, 'content'):
            content_list = result.content
            text_content = ""
            for item in content_list:
                if hasattr(item, 'text'):
                    text_content += item.text
                elif isinstance(item, dict) and item.get("type") == "text":
                    text_content += item.get("text", "")
            
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                return text_content
        
        # Handle string result
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result
        
        return result


def run_async_in_thread(coro):
    """
    Run async coroutine in a new thread with its own event loop
    
    Args:
        coro: Async coroutine to run
        
    Returns:
        Result from coroutine
    """
    def run_in_thread():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coro)
        finally:
            try:
                new_loop.run_until_complete(asyncio.sleep(0.1))
            except:
                pass
            new_loop.close()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        return future.result(timeout=30)



def create_booking_sync(user_phone: str, package_id: str, number_of_people: int, special_requests: str = "", user_id: Optional[str] = None):
    """
    Sync wrapper for create_booking MCP tool
    
    Args:
        user_phone: User phone number
        package_id: Tour package ID
        number_of_people: Number of people
        special_requests: Special requests
        user_id: Optional user ID
        
    Returns:
        Booking result dict
    """
    try:
        params = {
            "user_phone": user_phone,
            "package_id": package_id,
            "number_of_people": number_of_people
        }
        if special_requests:
            params["special_requests"] = special_requests
        if user_id:
            params["user_id"] = user_id
        
        result = run_async_in_thread(call_mcp_tool("create_booking", params))
    except concurrent.futures.TimeoutError:
        logger.error("create_booking_sync timeout")
        return {"error": "Request timeout"}
    except Exception as e:
        logger.error(f"Error in create_booking_sync: {e}")
        return {"error": f"Failed to create booking: {str(e)}"}
    
    # Check if result is valid (not None and not empty)
    if result is None:
        return {"error": "Failed to create booking: No response from MCP server"}
    
    # If result is a dict with "success" key, return it directly
    if isinstance(result, dict):
        # MCP server returns full booking response with "success" key
        if "success" in result:
            return result
        # If no "success" key but has other keys, return it
        elif len(result) > 0:
            return result
        # Empty dict
        else:
            return {"error": "Failed to create booking: Empty response from MCP server"}
    
    # Non-dict result
    return {"error": f"Failed to create booking: Unexpected response type: {type(result)}"}


def get_user_bookings_sync(user_id: str) -> Dict[str, Any]:
    """
    Sync wrapper for get_user_bookings MCP tool
    
    Args:
        user_id: User ID to fetch bookings for
        
    Returns:
        Dict with 'success' and 'bookings' keys
    """
    try:
        params = {"user_id": user_id}
        result = run_async_in_thread(call_mcp_tool("get_user_bookings", params))
    except concurrent.futures.TimeoutError:
        logger.error("get_user_bookings_sync timeout")
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        logger.error(f"Error in get_user_bookings_sync: {e}")
        return {"success": False, "error": f"Failed to get bookings: {str(e)}"}
    
    if result is None:
        return {"success": False, "error": "No response from MCP server"}
    
    return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}


def update_booking_sync(booking_id: str, number_of_people: Optional[int] = None, special_requests: Optional[str] = None) -> Dict[str, Any]:
    """
    Sync wrapper for update_booking MCP tool
    
    Args:
        booking_id: Booking ID to update
        number_of_people: New number of people (optional)
        special_requests: New special requests (optional)
        
    Returns:
        Dict with success status
    """
    try:
        params = {"booking_id": booking_id}
        if number_of_people is not None:
            params["number_of_people"] = number_of_people
        if special_requests is not None:
            params["special_requests"] = special_requests
        
        result = run_async_in_thread(call_mcp_tool("update_booking", params))
    except concurrent.futures.TimeoutError:
        logger.error("update_booking_sync timeout")
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        logger.error(f"Error in update_booking_sync: {e}")
        return {"success": False, "error": f"Failed to update booking: {str(e)}"}
    
    if result is None:
        return {"success": False, "error": "No response from MCP server"}
    
    return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}


def delete_booking_sync(booking_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Sync wrapper for delete_booking MCP tool
    
    Args:
        booking_id: Booking ID to cancel
        reason: Optional reason for cancellation
        
    Returns:
        Dict with success status
    """
    try:
        params = {"booking_id": booking_id}
        if reason:
            params["reason"] = reason
        
        result = run_async_in_thread(call_mcp_tool("delete_booking", params))
    except concurrent.futures.TimeoutError:
        logger.error("delete_booking_sync timeout")
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        logger.error(f"Error in delete_booking_sync: {e}")
        return {"success": False, "error": f"Failed to delete booking: {str(e)}"}
    
    if result is None:
        return {"success": False, "error": "No response from MCP server"}
    
    return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}


def request_recommendation_sync(user_query: str, destination: Optional[str] = None, budget: Optional[float] = None, duration: Optional[int] = None):
    """
    Chat Agent calls Recommendation Agent to get tour recommendations
    
    This is how Chat Agent communicates with Recommendation Agent.
    When Chat Agent determines user needs tour recommendations, it calls this tool.
    
    Args:
        user_query: User's query
        destination: Optional destination
        budget: Optional budget
        duration: Optional duration
        
    Returns:
        Status dict indicating recommendation was requested
    """
    return {
        "status": "requested",
        "message": "Recommendation Agent will provide tour recommendations",
        "user_query": user_query,
        "destination": destination,
        "budget": budget,
        "duration": duration
    }


def create_booking_tool() -> StructuredTool:
    """Create StructuredTool for create_booking"""
    return StructuredTool.from_function(
        func=create_booking_sync,
        name="create_booking",
        description="Tạo booking mới cho user - YÊU CẦU THU THẬP ĐẦY ĐỦ THÔNG TIN TRƯỚC KHI GỌI (user_phone, package_id, number_of_people)",
        args_schema=CreateBookingInput
    )


def get_user_bookings_tool() -> StructuredTool:
    """Create StructuredTool for get_user_bookings"""
    return StructuredTool.from_function(
        func=get_user_bookings_sync,
        name="get_user_bookings",
        description="Lấy danh sách tất cả các booking của user. Trả về chi tiết tour, ngày khởi hành, số người, tổng tiền và trạng thái booking.",
        args_schema=GetUserBookingsInput
    )


def update_booking_tool() -> StructuredTool:
    """Create StructuredTool for update_booking"""
    return StructuredTool.from_function(
        func=update_booking_sync,
        name="update_booking",
        description="Cập nhật booking hiện tại - có thể thay đổi số người hoặc ghi chú đặc biệt. Nếu tăng số người, hệ thống tự động kiểm tra còn slot và cập nhật giá.",
        args_schema=UpdateBookingInput
    )


def delete_booking_tool() -> StructuredTool:
    """Create StructuredTool for delete_booking"""
    return StructuredTool.from_function(
        func=delete_booking_sync,
        name="delete_booking",
        description="Hủy (cancel) booking và trả lại slot cho tour. Dữ liệu booking được giữ lại với trạng thái 'cancelled' (soft delete).",
        args_schema=DeleteBookingInput
    )


def request_recommendation_tool() -> StructuredTool:
    """Create StructuredTool for request_recommendation"""
    return StructuredTool.from_function(
        func=request_recommendation_sync,
        name="request_recommendation",
        description="Gọi Recommendation Agent để lấy tour recommendations. Sử dụng tool này khi user hỏi về tour, du lịch, địa điểm, hoặc muốn tìm tour packages. Chat Agent tự quyết định khi nào cần gọi tool này.",
        args_schema=RequestRecommendationInput
    )


def search_tour_packages_sync(
    user_message: str,
    max_price: Optional[float] = None,
    duration: Optional[int] = None,
    destination: Optional[str] = None,
    limit: int = 10
):
    """
    Sync wrapper for search_tour_packages MCP tool
    
    Args:
        user_message: User's search query
        max_price: Maximum price filter in VND
        duration: Duration filter in days
        destination: Destination filter
        limit: Maximum number of results
        
    Returns:
        Dict with 'found' and 'packages' keys
    """
    try:
        params = {"user_message": user_message, "limit": limit}
        if max_price is not None:
            params["max_price"] = max_price
        if duration is not None:
            params["duration"] = duration
        if destination:
            params["destination"] = destination
        
        result = run_async_in_thread(call_mcp_tool("search_tour_packages", params))
    except concurrent.futures.TimeoutError:
        logger.error("search_tour_packages_sync timeout")
        return {"found": 0, "packages": [], "error": "Request timeout"}
    except Exception as e:
        logger.error(f"Error in search_tour_packages_sync: {e}")
        return {"found": 0, "packages": [], "error": f"Failed to search: {str(e)}"}
    return result if result else {"found": 0, "packages": []}


def search_tour_packages_tool() -> StructuredTool:
    """Create StructuredTool for search_tour_packages"""
    return StructuredTool.from_function(
        func=search_tour_packages_sync,
        name="search_tour_packages",
        description="Search tour packages using semantic vector search. This tool uses AI embeddings to find tours that semantically match the user's query.",
        args_schema=SearchTourPackagesInput
    )


def search_flights_sync(departure_iata: str, arrival_iata: str, limit: int = 5) -> str:
    """
    Sync wrapper for search_flights MCP tool
    
    Args:
        departure_iata: Departure airport IATA code
        arrival_iata: Arrival airport IATA code
        limit: Maximum number of flights to return
        
    Returns:
        Formatted flight information string
    """
    try:
        params = {
            "departure_iata": departure_iata,
            "arrival_iata": arrival_iata,
            "limit": limit
        }
        result = run_async_in_thread(call_mcp_tool("search_flights", params))
    except concurrent.futures.TimeoutError:
        logger.error("search_flights_sync timeout")
        return "Error: Request timeout"
    except Exception as e:
        logger.error(f"Error in search_flights_sync: {e}")
        return f"Error: Failed to search flights: {str(e)}"
    
    return result if result else "Error: No response from MCP server"


def get_current_temperature_sync(city_name: str) -> str:
    """
    Sync wrapper for get_current_temperature MCP tool
    
    Args:
        city_name: City name
        
    Returns:
        Current weather information string
    """
    try:
        params = {"city_name": city_name}
        result = run_async_in_thread(call_mcp_tool("get_current_temperature_by_city", params))
    except concurrent.futures.TimeoutError:
        logger.error("get_current_temperature_sync timeout")
        return "Error: Request timeout"
    except Exception as e:
        logger.error(f"Error in get_current_temperature_sync: {e}")
        return f"Error: Failed to get weather: {str(e)}"
    
    return result if result else "Error: No response from MCP server"


def get_weather_forecast_sync(city_name: str, days: int = 5) -> str:
    """
    Sync wrapper for get_weather_forecast MCP tool
    
    Args:
        city_name: City name
        days: Number of days to forecast
        
    Returns:
        Weather forecast information string
    """
    try:
        params = {"city_name": city_name, "days": days}
        result = run_async_in_thread(call_mcp_tool("get_weather_forecast_by_city", params))
    except concurrent.futures.TimeoutError:
        logger.error("get_weather_forecast_sync timeout")
        return "Error: Request timeout"
    except Exception as e:
        logger.error(f"Error in get_weather_forecast_sync: {e}")
        return f"Error: Failed to get forecast: {str(e)}"
    
    return result if result else "Error: No response from MCP server"


def search_mem0_episodes_sync(search_query: str, user_id: Optional[str] = None, limit: int = 5) -> Dict:
    """
    Sync wrapper for search_episodes MCP tool via Mem0
    
    Args:
        search_query: Search query text for Mem0
        user_id: Optional user ID for personalized search
        limit: Maximum number of results
        
    Returns:
        Dict with 'found' and 'episodes' keys
    """
    try:
        params = {"query_text": search_query, "limit": limit}
        if user_id:
            params["user_id"] = user_id
        
        result = run_async_in_thread(call_mcp_tool("search_episodes", params))
    except concurrent.futures.TimeoutError:
        logger.error("search_mem0_episodes_sync timeout")
        return {"found": 0, "episodes": [], "error": "Request timeout"}
    except Exception as e:
        logger.error(f"Error in search_mem0_episodes_sync: {e}")
        return {"found": 0, "episodes": [], "error": f"Failed to search: {str(e)}"}
    
    return result if result else {"found": 0, "episodes": []}


def search_flights_tool() -> StructuredTool:
    """Create StructuredTool for search_flights"""
    return StructuredTool.from_function(
        func=search_flights_sync,
        name="search_flights",
        description="Search for flights between two airports. Returns future flights only (not yet departed). Use IATA codes (e.g., HAN=Hanoi, SGN=Ho Chi Minh, DAD=Da Nang).",
        args_schema=SearchFlightsInput
    )


def get_current_temperature_tool() -> StructuredTool:
    """Create StructuredTool for get_current_temperature"""
    return StructuredTool.from_function(
        func=get_current_temperature_sync,
        name="get_current_temperature",
        description="Get current temperature and weather conditions for a city. Use this when user asks about current weather.",
        args_schema=GetCurrentTemperatureInput
    )


def get_weather_forecast_tool() -> StructuredTool:
    """Create StructuredTool for get_weather_forecast"""
    return StructuredTool.from_function(
        func=get_weather_forecast_sync,
        name="get_weather_forecast",
        description="Get weather forecast for a city for the next few days (1-5 days). Use this when user asks about weather forecast or future weather.",
        args_schema=GetWeatherForecastInput
    )


def search_mem0_episodes_tool() -> StructuredTool:
    """Create StructuredTool for search_mem0_episodes"""
    return StructuredTool.from_function(
        func=search_mem0_episodes_sync,
        name="search_episodes",
        description="Search through conversation history and user interactions stored in Mem0 memory system to find relevant episodes. Use this to find past conversations or user preferences related to the query.",
        args_schema=SearchEpisodesInput
    )


def generate_tour_ui_sync(packages: list) -> Dict:
    """Generate interactive UI for tour packages using MCP-UI"""
    try:
        params = {"packages": packages}
        result = run_async_in_thread(call_mcp_tool("generate_tour_ui", params))
    except concurrent.futures.TimeoutError:
        logger.error("generate_tour_ui_sync timeout")
        return {"error": "Request timeout"}
    except Exception as e:
        logger.error(f"Error in generate_tour_ui_sync: {e}")
        return {"error": f"Failed to generate UI: {str(e)}"}
    
    return result if result else {"error": "No response from MCP server"}


def generate_tour_ui_tool() -> StructuredTool:
    """Create StructuredTool for generate_tour_ui"""
    class GenerateTourUIInput(BaseModel):
        packages: list = Field(..., description="List of tour package dictionaries to display in UI grid")
    
    return StructuredTool.from_function(
        func=generate_tour_ui_sync,
        name="generate_tour_ui",
        description="Generate beautiful interactive UI component displaying tour packages in a responsive grid. Use this after getting tour recommendations to show them visually with images, prices, and booking buttons.",
        args_schema=GenerateTourUIInput
    )
