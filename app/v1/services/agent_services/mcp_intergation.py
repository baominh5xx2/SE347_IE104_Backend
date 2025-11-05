"""
MCP Integration Service
Wrapper for calling MCP tools safely with error handling

Following MCP best practices:
- Structured logging with context
- Retry logic with exponential backoff
- Input/output validation
- Resource management
- Error handling with proper error types
"""
import httpx
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from app.v1.core.config import settings

logger = logging.getLogger(__name__)


class MCPErrorType(str, Enum):
    """MCP error types"""
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"


class MCPError(Exception):
    """Custom MCP error with context"""
    
    def __init__(
        self,
        message: str,
        error_type: MCPErrorType = MCPErrorType.UNKNOWN_ERROR,
        status_code: Optional[int] = None,
        tool_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.tool_name = tool_name
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            "error": self.error_type.value,
            "message": self.message,
            "status_code": self.status_code,
            "tool_name": self.tool_name,
            "details": self.details
        }


class MCPIntegrationService:
    """
    Service for integrating with MCP server
    
    Features:
    - Retry logic with exponential backoff
    - Structured logging with context
    - Input/output validation
    - Connection pooling
    - Error handling with proper error types
    
    Configuration is read from .env file via config.py (settings)
    - MCP_SERVER_URL: MCP server URL
    - MCP_TIMEOUT: Request timeout in seconds
    - MCP_RETRY_COUNT: Number of retry attempts (default: 3)
    - MCP_RETRY_BACKOFF: Base backoff multiplier (default: 2.0)
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        retry_count: int = 3,
        retry_backoff: float = 2.0
    ):
        """
        Initialize MCP integration
        
        Args:
            base_url: MCP server URL (defaults to settings.MCP_SERVER_URL)
            timeout: Request timeout in seconds (defaults to settings.MCP_TIMEOUT)
            retry_count: Number of retry attempts
            retry_backoff: Exponential backoff multiplier
        """
        # Read from .env via config.py (settings)
        self.base_url = base_url or settings.MCP_SERVER_URL
        self.timeout = timeout or settings.MCP_TIMEOUT
        self.retry_count = retry_count
        self.retry_backoff = retry_backoff
        
        # Validate configuration
        if not self.base_url:
            raise ValueError("MCP_SERVER_URL must be configured")
        
        # Create HTTP client with connection pooling
        # Use longer keepalive and disable connection reuse cleanup to avoid event loop issues
        limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
            keepalive_expiry=300.0  # Increased to 5 minutes to avoid premature cleanup
        )
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
            limits=limits,
            follow_redirects=True,
            # Don't close connections immediately - let them timeout naturally
            http2=False  # Use HTTP/1.1 for more predictable behavior
        )
        
        # Log initialization (minimal)
        logger.debug(f"MCP Integration initialized: {self.base_url}")
    
    async def _call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        retry_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        Generic method to call any MCP tool with retry logic
        
        Args:
            tool_name: Name of the tool
            params: Tool parameters (must be JSON-serializable)
            retry_on_error: Whether to retry on transient errors
            
        Returns:
            Tool response dictionary
            
        Raises:
            MCPError: If tool call fails after retries
        """
        # Validate input
        if not tool_name:
            raise MCPError(
                "Tool name is required",
                error_type=MCPErrorType.VALIDATION_ERROR,
                tool_name=tool_name
            )
        
        if not isinstance(params, dict):
            raise MCPError(
                "Parameters must be a dictionary",
                error_type=MCPErrorType.VALIDATION_ERROR,
                tool_name=tool_name
            )
        
        # Generate request ID for tracking
        request_id = f"{tool_name}_{datetime.now().timestamp()}"
        
        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(self.retry_count):
            try:
                # Make HTTP request
                start_time = datetime.now()
                response = await self.client.post(
                    f"/tools/{tool_name}",
                    json=params
                )
                duration = (datetime.now() - start_time).total_seconds()
                
                # Check status code
                if response.status_code >= 500:
                    # Server error - retryable
                    error_msg = f"Server error {response.status_code}"
                    if retry_on_error and attempt < self.retry_count - 1:
                        wait_time = self.retry_backoff ** attempt
                        logger.warning(
                            f"MCP tool {tool_name} server error, retrying...",
                            extra={
                                "tool_name": tool_name,
                                "request_id": request_id,
                                "status_code": response.status_code,
                                "attempt": attempt + 1,
                                "wait_time": wait_time
                            }
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    
                    raise MCPError(
                        error_msg,
                        error_type=MCPErrorType.HTTP_ERROR,
                        status_code=response.status_code,
                        tool_name=tool_name,
                        details={"response": response.text[:500]}
                    )
                
                response.raise_for_status()
                
                # Parse response
                try:
                    result = response.json()
                except Exception as e:
                    raise MCPError(
                        f"Invalid JSON response: {str(e)}",
                        error_type=MCPErrorType.UNKNOWN_ERROR,
                        tool_name=tool_name,
                        details={"response_text": response.text[:500]}
                    )
                
                # Log success (minimal - tool output logged by callback handler)
                logger.debug(f"MCP tool {tool_name} succeeded ({duration:.2f}s)")
                
                return result
                
            except httpx.TimeoutException as e:
                last_error = e
                if retry_on_error and attempt < self.retry_count - 1:
                    wait_time = self.retry_backoff ** attempt
                    logger.warning(
                        f"MCP tool {tool_name} timeout, retrying...",
                        extra={
                            "tool_name": tool_name,
                            "request_id": request_id,
                            "attempt": attempt + 1,
                            "wait_time": wait_time,
                            "timeout": self.timeout
                        }
                    )
                    try:
                        await asyncio.sleep(wait_time)
                    except RuntimeError as loop_error:
                        if "Event loop is closed" in str(loop_error):
                            # Event loop closed during retry - can't continue
                            raise MCPError(
                                f"Event loop closed during retry: {str(e)}",
                                error_type=MCPErrorType.UNKNOWN_ERROR,
                                tool_name=tool_name
                            )
                        raise
                    continue
                
                raise MCPError(
                    f"Request timeout after {self.timeout}s",
                    error_type=MCPErrorType.TIMEOUT,
                    tool_name=tool_name,
                    details={"timeout": self.timeout}
                )
                
            except httpx.NetworkError as e:
                last_error = e
                # Check if it's an event loop closed error
                if "Event loop is closed" in str(e):
                    raise MCPError(
                        f"Event loop closed during request: {str(e)}",
                        error_type=MCPErrorType.NETWORK_ERROR,
                        tool_name=tool_name,
                        details={"error": str(e)}
                    )
                
                if retry_on_error and attempt < self.retry_count - 1:
                    wait_time = self.retry_backoff ** attempt
                    logger.warning(
                        f"MCP tool {tool_name} network error, retrying...",
                        extra={
                            "tool_name": tool_name,
                            "request_id": request_id,
                            "attempt": attempt + 1,
                            "wait_time": wait_time,
                            "error": str(e)
                        }
                    )
                    try:
                        await asyncio.sleep(wait_time)
                    except RuntimeError as loop_error:
                        if "Event loop is closed" in str(loop_error):
                            raise MCPError(
                                f"Event loop closed during retry: {str(e)}",
                                error_type=MCPErrorType.UNKNOWN_ERROR,
                                tool_name=tool_name
                            )
                        raise
                    continue
                
                raise MCPError(
                    f"Network error: {str(e)}",
                    error_type=MCPErrorType.NETWORK_ERROR,
                    tool_name=tool_name,
                    details={"error": str(e)}
                )
                
            except httpx.HTTPStatusError as e:
                # Client errors (4xx) - don't retry
                if 400 <= e.response.status_code < 500:
                    raise MCPError(
                        f"Client error {e.response.status_code}: {e.response.text[:200]}",
                        error_type=MCPErrorType.HTTP_ERROR,
                        status_code=e.response.status_code,
                        tool_name=tool_name,
                        details={"response": e.response.text[:500]}
                    )
                # Server errors (5xx) - retry handled above
                last_error = e
                if retry_on_error and attempt < self.retry_count - 1:
                    wait_time = self.retry_backoff ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise MCPError(
                    f"HTTP error {e.response.status_code}",
                    error_type=MCPErrorType.HTTP_ERROR,
                    status_code=e.response.status_code,
                    tool_name=tool_name
                )
                
            except MCPError:
                # Re-raise our custom errors
                raise
                
            except RuntimeError as e:
                # Check if it's an event loop closed error
                if "Event loop is closed" in str(e):
                    # Don't retry - event loop is closed, can't continue
                    raise MCPError(
                        f"Event loop closed: {str(e)}",
                        error_type=MCPErrorType.UNKNOWN_ERROR,
                        tool_name=tool_name,
                        details={"error_type": type(e).__name__, "error": str(e)}
                    )
                # Re-raise other RuntimeErrors
                last_error = e
                logger.error(
                    f"MCP tool {tool_name} runtime error",
                    extra={
                        "tool_name": tool_name,
                        "request_id": request_id,
                        "error_type": type(e).__name__,
                        "error": str(e)
                    },
                    exc_info=True
                )
                
                if not retry_on_error or attempt >= self.retry_count - 1:
                    raise MCPError(
                        f"Runtime error: {str(e)}",
                        error_type=MCPErrorType.UNKNOWN_ERROR,
                        tool_name=tool_name,
                        details={"error_type": type(e).__name__, "error": str(e)}
                    )
                
            except Exception as e:
                last_error = e
                logger.error(
                    f"MCP tool {tool_name} unexpected error",
                    extra={
                        "tool_name": tool_name,
                        "request_id": request_id,
                        "error_type": type(e).__name__,
                        "error": str(e)
                    },
                    exc_info=True
                )
                
                if not retry_on_error or attempt >= self.retry_count - 1:
                    raise MCPError(
                        f"Unexpected error: {str(e)}",
                        error_type=MCPErrorType.UNKNOWN_ERROR,
                        tool_name=tool_name,
                        details={"error_type": type(e).__name__, "error": str(e)}
                    )
        
        # If we get here, all retries failed
        raise MCPError(
            f"Failed after {self.retry_count} attempts: {str(last_error)}",
            error_type=MCPErrorType.UNKNOWN_ERROR,
            tool_name=tool_name,
            details={"last_error": str(last_error)}
        )
    
    # ============================================================================
    # BOOKING TOOLS
    # ============================================================================
    
    async def search_tours(
        self,
        destination: Optional[str] = None,
        budget: Optional[float] = None,
        duration: Optional[int] = None,
        people: Optional[int] = None
    ) -> List[Dict]:
        """
        Search tour packages via MCP
        
        Args:
            destination: Destination name
            budget: Maximum budget
            duration: Duration in days
            people: Number of people
            
        Returns:
            List of tour packages or empty list on error
        """
        params = {}
        if destination:
            params["destination"] = str(destination).strip()
        if budget is not None:
            params["budget"] = float(budget)
        if duration is not None:
            params["duration"] = int(duration)
        if people is not None:
            params["people"] = int(people)
        
        try:
            result = await self._call_tool("search_tours", params)
            return result.get("tours", [])
        except MCPError as e:
            logger.error(f"search_tours failed: {e.message}", extra=e.to_dict())
            return []
    
    async def get_tour_details(self, package_id: str) -> Optional[Dict]:
        """
        Get tour package details via MCP
        
        Args:
            package_id: Tour package ID
            
        Returns:
            Tour details or None on error
        """
        if not package_id or not str(package_id).strip():
            logger.error("package_id is required")
            return None
        
        try:
            result = await self._call_tool("get_tour_details", {"package_id": str(package_id).strip()})
            return result.get("tour")
        except MCPError as e:
            logger.error(f"get_tour_details failed: {e.message}", extra=e.to_dict())
            return None
    
    async def search_tour_packages(
        self,
        user_message: str,
        max_price: Optional[float] = None,
        duration: Optional[int] = None,
        destination: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search tour packages using semantic vector search via MCP
        
        Args:
            user_message: User's search query
            max_price: Maximum price filter in VND
            duration: Duration filter in days
            destination: Destination filter
            limit: Maximum number of results
            
        Returns:
            Dict with 'found' and 'packages' keys
        """
        params = {
            "user_message": str(user_message).strip(),
            "limit": int(limit)
        }
        if max_price is not None:
            params["max_price"] = float(max_price)
        if duration is not None:
            params["duration"] = int(duration)
        if destination:
            params["destination"] = str(destination).strip()
        
        try:
            result = await self._call_tool("search_tour_packages", params)
            
            # Ensure result has correct structure
            if isinstance(result, dict):
                if "packages" in result:
                    return result
                elif "found" in result:
                    packages = result.get("packages", [])
                    if packages:
                        return result
                    else:
                        logger.warning(f"⚠️ Result has 'found'={result.get('found')} but packages array is empty")
                        return result
                elif "content" in result:
                    # Result might be wrapped in 'content' key (from FastMCP tuple conversion)
                    content_value = result.get("content")
                    
                    # Check if content is a JSON string
                    if isinstance(content_value, str):
                        try:
                            import json
                            parsed = json.loads(content_value)
                            if isinstance(parsed, dict) and ("packages" in parsed or "found" in parsed):
                                return parsed
                        except (json.JSONDecodeError, TypeError):
                            pass
                        
                        # Try to extract JSON from tuple string representation
                        if "packages" in content_value.lower():
                            try:
                                import json
                                import re
                                json_match = re.search(r'\{.*?"packages".*?\}', content_value, re.DOTALL)
                                if json_match:
                                    return json.loads(json_match.group())
                            except (json.JSONDecodeError, AttributeError):
                                pass
                    
                    # If content is a dict, check it
                    if isinstance(content_value, dict) and "packages" in content_value:
                        return content_value
                
                # Try to find packages in nested structure
                for key, value in result.items():
                    if isinstance(value, dict) and "packages" in value:
                        return value
                    elif isinstance(value, list):
                        return {
                            "found": len(value),
                            "packages": value
                        }
                return result
            else:
                logger.error(f"❌ Result is not a dict: {type(result)}, value: {result}")
                return {
                    "found": 0,
                    "packages": [],
                    "error": f"Unexpected result type: {type(result)}"
                }
        except MCPError as e:
            logger.error(f"search_tour_packages failed: {e.message}", extra=e.to_dict())
            return {
                "found": 0,
                "packages": [],
                "error": e.message
            }
    
    async def create_booking(
        self,
        user_phone: str,
        package_id: str,
        number_of_people: int,
        special_requests: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create tour booking via MCP
        
        Args:
            user_phone: User phone number
            package_id: Tour package ID
            number_of_people: Number of people
            special_requests: Special requests
            
        Returns:
            Booking info or None on error
        """
        # Input validation
        if not user_phone or not str(user_phone).strip():
            logger.error("user_phone is required")
            return None
        
        if not package_id or not str(package_id).strip():
            logger.error("package_id is required")
            return None
        
        if not isinstance(number_of_people, int) or number_of_people <= 0:
            logger.error(f"Invalid number_of_people: {number_of_people}")
            return None
        
        params = {
            "user_phone": str(user_phone).strip(),
            "package_id": str(package_id).strip(),
            "number_of_people": number_of_people
        }
        
        if special_requests:
            params["special_requests"] = str(special_requests).strip()
        
        try:
            result = await self._call_tool("create_booking", params)
            # MCP server returns the full booking result directly (not wrapped in "booking" key)
            # Check if result has success key to determine if it's a valid booking response
            if isinstance(result, dict):
                # If result has "success" key, it's the full booking response from MCP
                if "success" in result:
                    return result
                # Otherwise try to get "booking" key (backward compatibility)
                elif "booking" in result:
                    return result.get("booking")
                # If neither, return the whole result
                else:
                    return result
            return result
        except MCPError as e:
            logger.error(f"create_booking failed: {e.message}", extra=e.to_dict())
            return None
    
    # ============================================================================
    # FLIGHT TOOLS
    # ============================================================================
    
    async def search_flights(
        self,
        departure_iata: str,
        arrival_iata: str,
        limit: int = 5
    ) -> str:
        """
        Search flights via MCP
        
        Args:
            departure_iata: Departure airport IATA code (e.g., HAN for Hanoi)
            arrival_iata: Arrival airport IATA code (e.g., SGN for Ho Chi Minh)
            limit: Maximum number of flights to return
            
        Returns:
            Formatted flight information string
        """
        if not departure_iata or not arrival_iata:
            logger.error("departure_iata and arrival_iata are required")
            return "Error: departure_iata and arrival_iata are required"
        
        params = {
            "departure_iata": str(departure_iata).strip().upper(),
            "arrival_iata": str(arrival_iata).strip().upper(),
            "limit": max(1, min(int(limit), 100))
        }
        
        try:
            result = await self._call_tool("search_flights", params)
            # MCP tool returns string directly
            if isinstance(result, str):
                return result
            elif isinstance(result, dict) and "content" in result:
                return result["content"]
            else:
                return str(result)
        except MCPError as e:
            logger.error(f"search_flights failed: {e.message}", extra=e.to_dict())
            return f"Error searching flights: {e.message}"
    
    # ============================================================================
    # WEATHER TOOLS
    # ============================================================================
    
    async def get_weather(
        self,
        location: str,
        days: int = 7
    ) -> Optional[Dict]:
        """
        Get weather forecast via MCP
        
        Args:
            location: Location name
            days: Number of days forecast (1-14)
            
        Returns:
            Weather data or None on error
        """
        if not location:
            logger.error("location is required")
            return None
        
        params = {
            "location": str(location).strip(),
            "days": min(max(1, int(days)), 14)  # Clamp between 1-14
        }
        
        try:
            result = await self._call_tool("get_weather", params)
            return result.get("weather")
        except MCPError as e:
            logger.error(f"get_weather failed: {e.message}", extra=e.to_dict())
            return None
    
    async def get_current_temperature(self, city_name: str) -> str:
        """
        Get current temperature via MCP
        
        Args:
            city_name: City name
            
        Returns:
            Weather information string
        """
        if not city_name:
            return "Error: city_name is required"
        
        params = {
            "city_name": str(city_name).strip()
        }
        
        try:
            result = await self._call_tool("get_current_temperature_by_city", params)
            # MCP tool returns string directly
            if isinstance(result, str):
                return result
            elif isinstance(result, dict) and "content" in result:
                return result["content"]
            else:
                return str(result)
        except MCPError as e:
            logger.error(f"get_current_temperature failed: {e.message}", extra=e.to_dict())
            return f"Error getting weather: {e.message}"
    
    async def get_weather_forecast(self, city_name: str, days: int = 5) -> str:
        """
        Get weather forecast via MCP
        
        Args:
            city_name: City name
            days: Number of days to forecast (1-5)
            
        Returns:
            Forecast information string
        """
        if not city_name:
            return "Error: city_name is required"
        
        params = {
            "city_name": str(city_name).strip(),
            "days": max(1, min(int(days), 5))
        }
        
        try:
            result = await self._call_tool("get_weather_forecast_by_city", params)
            # MCP tool returns string directly
            if isinstance(result, str):
                return result
            elif isinstance(result, dict) and "content" in result:
                return result["content"]
            else:
                return str(result)
        except MCPError as e:
            logger.error(f"get_weather_forecast failed: {e.message}", extra=e.to_dict())
            return f"Error getting forecast: {e.message}"
    
    # ============================================================================
    # SEARCH PERSONALIZATION TOOLS
    # ============================================================================
    
    async def search_episodes(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Search episodes via MCP
        
        Args:
            query_text: Search query text
            user_id: Optional user ID for personalized search
            limit: Maximum number of results
            
        Returns:
            Dict with 'found' and 'episodes' keys
        """
        if not query_text:
            logger.error("query_text is required")
            return {"found": 0, "episodes": [], "error": "query_text is required"}
        
        params = {
            "query_text": str(query_text).strip(),
            "limit": max(1, min(int(limit), 20))
        }
        
        if user_id:
            params["user_id"] = str(user_id).strip()
        
        try:
            result = await self._call_tool("search_episodes", params)
            # Ensure result has correct structure
            if isinstance(result, dict):
                if "episodes" in result:
                    return result
                elif "found" in result:
                    return result
                elif "content" in result:
                    content = result["content"]
                    if isinstance(content, str):
                        try:
                            import json
                            return json.loads(content)
                        except:
                            pass
                return result
            else:
                return {"found": 0, "episodes": [], "error": f"Unexpected result type: {type(result)}"}
        except MCPError as e:
            logger.error(f"search_episodes failed: {e.message}", extra=e.to_dict())
            return {"found": 0, "episodes": [], "error": e.message}
    
    # ============================================================================
    # ADDITIONAL BOOKING TOOLS
    # ============================================================================
    
    async def search_available_tours(
        self,
        destination: Optional[str] = None,
        max_price: Optional[float] = None,
        duration_days: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Search available tours via MCP
        
        Args:
            destination: Destination filter
            max_price: Maximum price filter
            duration_days: Duration filter
            
        Returns:
            Tours data or None on error
        """
        params = {}
        if destination:
            params["destination"] = str(destination).strip()
        if max_price is not None:
            params["max_price"] = float(max_price)
        if duration_days is not None:
            params["duration_days"] = int(duration_days)
        
        try:
            return await self._call_tool("search_available_tours", params)
        except MCPError as e:
            logger.error(f"search_available_tours failed: {e.message}", extra=e.to_dict())
            return None
    
    async def get_booking_details(self, booking_id: str) -> Optional[Dict]:
        """
        Get booking details via MCP
        
        Args:
            booking_id: Booking ID
            
        Returns:
            Booking details or None on error
        """
        if not booking_id or not str(booking_id).strip():
            logger.error("booking_id is required")
            return None
        
        try:
            return await self._call_tool("get_booking_details", {"booking_id": str(booking_id).strip()})
        except MCPError as e:
            logger.error(f"get_booking_details failed: {e.message}", extra=e.to_dict())
            return None
    
    async def close(self):
        """Close HTTP client and cleanup resources"""
        try:
            # Check if client is still open before closing
            if hasattr(self.client, '_transport') and self.client._transport:
                # Try to close gracefully, but don't fail if event loop is closed
                try:
                    await self.client.aclose()
                    logger.info("MCP client closed successfully")
                except RuntimeError as e:
                    if "Event loop is closed" in str(e):
                        # Event loop already closed - just log and continue
                        logger.debug("Event loop already closed, skipping client cleanup")
                    else:
                        raise
        except Exception as e:
            # Don't fail if we can't close - might be during shutdown
            logger.debug(f"Error closing MCP client (non-critical): {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Singleton instance with settings from config
mcp_client = MCPIntegrationService(
    retry_count=settings.MCP_RETRY_COUNT,
    retry_backoff=settings.MCP_RETRY_BACKOFF
)
