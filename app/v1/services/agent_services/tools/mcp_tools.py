"""
MCP Tools
Tools that call MCP server
"""
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, Dict
import asyncio
import concurrent.futures
import logging
from app.v1.services.agent_services.mcp_intergation import mcp_client

logger = logging.getLogger(__name__)


class SearchTourPackagesInput(BaseModel):
    """Input schema for search_tour_packages tool"""
    user_message: str = Field(description="User's search query in Vietnamese or English")
    max_price: Optional[float] = Field(default=None, description="Maximum price filter in VND")
    duration: Optional[int] = Field(default=None, description="Duration filter in days")
    destination: Optional[str] = Field(default=None, description="Destination filter")
    limit: int = Field(default=10, description="Maximum number of results")


class CreateBookingInput(BaseModel):
    """Input schema for create_booking tool"""
    user_phone: str = Field(description="User phone number")
    package_id: str = Field(description="Tour package ID from recommendation results")
    number_of_people: int = Field(description="Number of people traveling")
    special_requests: str = Field(default="", description="Special requests or requirements")


class RequestRecommendationInput(BaseModel):
    """Input schema for request_recommendation tool"""
    user_query: str = Field(description="User's query or request for tour recommendations")
    destination: Optional[str] = Field(default=None, description="Destination if mentioned")
    budget: Optional[float] = Field(default=None, description="Budget if mentioned")
    duration: Optional[int] = Field(default=None, description="Duration in days if mentioned")


class SearchFlightsInput(BaseModel):
    """Input schema for search_flights tool"""
    departure_iata: str = Field(description="Departure airport IATA code (e.g., HAN for Hanoi, SGN for Ho Chi Minh)")
    arrival_iata: str = Field(description="Arrival airport IATA code (e.g., SGN for Ho Chi Minh, HAN for Hanoi)")
    limit: int = Field(default=5, description="Maximum number of flights to return (1-100)")


class GetCurrentTemperatureInput(BaseModel):
    """Input schema for get_current_temperature tool"""
    city_name: str = Field(description="City name to get current weather for")


class GetWeatherForecastInput(BaseModel):
    """Input schema for get_weather_forecast tool"""
    city_name: str = Field(description="City name to get weather forecast for")
    days: int = Field(default=5, description="Number of days to forecast (1-5)")


class SearchEpisodesInput(BaseModel):
    """Input schema for search_episodes tool"""
    query_text: str = Field(description="Search query text to find relevant episodes in conversation history")
    user_id: Optional[str] = Field(default=None, description="Optional user ID for personalized search")
    limit: int = Field(default=5, description="Maximum number of results to return (1-20)")


def create_booking_sync(user_phone: str, package_id: str, number_of_people: int, special_requests: str = ""):
    """
    Sync wrapper for create_booking MCP tool
    
    Args:
        user_phone: User phone number
        package_id: Tour package ID
        number_of_people: Number of people
        special_requests: Special requests
        
    Returns:
        Booking result dict
    """
    def run_in_thread():
        """Run async function in a new thread with its own event loop"""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            # Create a new client for this event loop to avoid connection pool issues
            from app.v1.services.agent_services.mcp_intergation import MCPIntegrationService
            from app.v1.core.config import settings
            
            # Create a temporary client for this thread
            temp_client = MCPIntegrationService(
                retry_count=settings.MCP_RETRY_COUNT,
                retry_backoff=settings.MCP_RETRY_BACKOFF
            )
            
            try:
                result = new_loop.run_until_complete(
                    temp_client.create_booking(
                        user_phone=user_phone,
                        package_id=package_id,
                        number_of_people=number_of_people,
                        special_requests=special_requests
                    )
                )
                return result
            finally:
                # Cleanup client before closing event loop
                try:
                    new_loop.run_until_complete(temp_client.close())
                except Exception as cleanup_error:
                    logger.debug(f"Cleanup error (non-critical): {cleanup_error}")
        finally:
            # Give a moment for cleanup to complete
            try:
                new_loop.run_until_complete(asyncio.sleep(0.1))
            except:
                pass
            new_loop.close()
    
    try:
        # Always use thread pool to avoid event loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            result = future.result(timeout=30)
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
    def run_in_thread():
        """Run async function in a new thread with its own event loop"""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            # Create a new client for this event loop to avoid connection pool issues
            from app.v1.services.agent_services.mcp_intergation import MCPIntegrationService
            from app.v1.core.config import settings
            
            # Create a temporary client for this thread
            temp_client = MCPIntegrationService(
                retry_count=settings.MCP_RETRY_COUNT,
                retry_backoff=settings.MCP_RETRY_BACKOFF
            )
            
            try:
                result = new_loop.run_until_complete(
                    temp_client.search_tour_packages(
                        user_message=user_message,
                        max_price=max_price,
                        duration=duration,
                        destination=destination,
                        limit=limit
                    )
                )
                return result
            finally:
                # Cleanup client before closing event loop
                try:
                    new_loop.run_until_complete(temp_client.close())
                except Exception as cleanup_error:
                    logger.debug(f"Cleanup error (non-critical): {cleanup_error}")
        finally:
            # Give a moment for cleanup to complete
            try:
                new_loop.run_until_complete(asyncio.sleep(0.1))
            except:
                pass
            new_loop.close()
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            result = future.result(timeout=30)
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
    def run_in_thread():
        """Run async function in a new thread with its own event loop"""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            from app.v1.services.agent_services.mcp_intergation import MCPIntegrationService
            from app.v1.core.config import settings
            
            temp_client = MCPIntegrationService(
                retry_count=settings.MCP_RETRY_COUNT,
                retry_backoff=settings.MCP_RETRY_BACKOFF
            )
            
            try:
                result = new_loop.run_until_complete(
                    temp_client.search_flights(
                        departure_iata=departure_iata,
                        arrival_iata=arrival_iata,
                        limit=limit
                    )
                )
                return result
            finally:
                try:
                    new_loop.run_until_complete(temp_client.close())
                except Exception as cleanup_error:
                    logger.debug(f"Cleanup error (non-critical): {cleanup_error}")
        finally:
            try:
                new_loop.run_until_complete(asyncio.sleep(0.1))
            except:
                pass
            new_loop.close()
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            result = future.result(timeout=30)
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
    def run_in_thread():
        """Run async function in a new thread with its own event loop"""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            from app.v1.services.agent_services.mcp_intergation import MCPIntegrationService
            from app.v1.core.config import settings
            
            temp_client = MCPIntegrationService(
                retry_count=settings.MCP_RETRY_COUNT,
                retry_backoff=settings.MCP_RETRY_BACKOFF
            )
            
            try:
                result = new_loop.run_until_complete(
                    temp_client.get_current_temperature(city_name=city_name)
                )
                return result
            finally:
                try:
                    new_loop.run_until_complete(temp_client.close())
                except Exception as cleanup_error:
                    logger.debug(f"Cleanup error (non-critical): {cleanup_error}")
        finally:
            try:
                new_loop.run_until_complete(asyncio.sleep(0.1))
            except:
                pass
            new_loop.close()
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            result = future.result(timeout=15)
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
    def run_in_thread():
        """Run async function in a new thread with its own event loop"""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            from app.v1.services.agent_services.mcp_intergation import MCPIntegrationService
            from app.v1.core.config import settings
            
            temp_client = MCPIntegrationService(
                retry_count=settings.MCP_RETRY_COUNT,
                retry_backoff=settings.MCP_RETRY_BACKOFF
            )
            
            try:
                result = new_loop.run_until_complete(
                    temp_client.get_weather_forecast(city_name=city_name, days=days)
                )
                return result
            finally:
                try:
                    new_loop.run_until_complete(temp_client.close())
                except Exception as cleanup_error:
                    logger.debug(f"Cleanup error (non-critical): {cleanup_error}")
        finally:
            try:
                new_loop.run_until_complete(asyncio.sleep(0.1))
            except:
                pass
            new_loop.close()
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            result = future.result(timeout=15)
    except concurrent.futures.TimeoutError:
        logger.error("get_weather_forecast_sync timeout")
        return "Error: Request timeout"
    except Exception as e:
        logger.error(f"Error in get_weather_forecast_sync: {e}")
        return f"Error: Failed to get forecast: {str(e)}"
    
    return result if result else "Error: No response from MCP server"


def search_episodes_sync(query_text: str, user_id: Optional[str] = None, limit: int = 5) -> Dict:
    """
    Sync wrapper for search_episodes MCP tool
    
    Args:
        query_text: Search query text
        user_id: Optional user ID for personalized search
        limit: Maximum number of results
        
    Returns:
        Dict with 'found' and 'episodes' keys
    """
    def run_in_thread():
        """Run async function in a new thread with its own event loop"""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            from app.v1.services.agent_services.mcp_intergation import MCPIntegrationService
            from app.v1.core.config import settings
            
            temp_client = MCPIntegrationService(
                retry_count=settings.MCP_RETRY_COUNT,
                retry_backoff=settings.MCP_RETRY_BACKOFF
            )
            
            try:
                result = new_loop.run_until_complete(
                    temp_client.search_episodes(
                        query_text=query_text,
                        user_id=user_id,
                        limit=limit
                    )
                )
                return result
            finally:
                try:
                    new_loop.run_until_complete(temp_client.close())
                except Exception as cleanup_error:
                    logger.debug(f"Cleanup error (non-critical): {cleanup_error}")
        finally:
            try:
                new_loop.run_until_complete(asyncio.sleep(0.1))
            except:
                pass
            new_loop.close()
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            result = future.result(timeout=15)
    except concurrent.futures.TimeoutError:
        logger.error("search_episodes_sync timeout")
        return {"found": 0, "episodes": [], "error": "Request timeout"}
    except Exception as e:
        logger.error(f"Error in search_episodes_sync: {e}")
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


def search_episodes_tool() -> StructuredTool:
    """Create StructuredTool for search_episodes"""
    return StructuredTool.from_function(
        func=search_episodes_sync,
        name="search_episodes",
        description="Search through conversation history and user interactions stored in the knowledge graph to find relevant episodes. Use this to find past conversations or user preferences related to the query.",
        args_schema=SearchEpisodesInput
    )

