"""
MCP Tools
Tools that call MCP server directly - OOP Architecture
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
from app.v1.services.agent_services.skills.skill_loader import get_skill_loader
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
    DeleteBookingInput,
    VerifyOTPInput,
    CreatePaymentInput
)

logger = logging.getLogger(__name__)


# ============================================================================
# MCP CLIENT - Core MCP Communication
# ============================================================================

class MCPClient:
    """Core MCP client for calling MCP server tools"""
    
    def __init__(self):
        """Initialize MCP client"""
        self._base_url = None
    
    def _get_base_url(self) -> str:
        """Get MCP server base URL"""
        if self._base_url is None:
            from app.v1.core.prompts import PromptManager
            mcp_config = PromptManager().get_mcp_config()
            self._base_url = settings.MCP_SERVER_URL or mcp_config.get(
                'server_url', 
                'http://localhost:8000/mcp/mcp'
            )
        return self._base_url
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Generic method to call any MCP tool
        
        Args:
            tool_name: Name of the MCP tool
            params: Tool parameters
            
        Returns:
            Tool result (parsed from JSON if possible)
        """
        base_url = self._get_base_url()
        
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
    
    def call_tool_sync(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Synchronous wrapper for calling MCP tool
        
        Args:
            tool_name: Name of the MCP tool
            params: Tool parameters
            
        Returns:
            Tool result
        """
        return self._run_async_in_thread(self.call_tool(tool_name, params))
    
    @staticmethod
    def _run_async_in_thread(coro):
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


# ============================================================================
# MCP TOOL HANDLERS - Business Logic for Each Tool Category
# ============================================================================

class BookingToolHandler:
    """Handler for booking-related MCP tools"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    def create_booking(
        self, 
        user_phone: str,
        user_email: str,
        package_id: str, 
        number_of_people: int, 
        special_requests: str = "", 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new booking"""
        try:
            params = {
                "user_phone": user_phone,
                "user_email": user_email,
                "package_id": package_id,
                "number_of_people": number_of_people
            }
            if special_requests:
                params["special_requests"] = special_requests
            if user_id:
                params["user_id"] = user_id
            
            result = self.mcp_client.call_tool_sync("create_booking", params)
        except concurrent.futures.TimeoutError:
            logger.error("create_booking timeout")
            return {"error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in create_booking: {e}")
            return {"error": f"Failed to create booking: {str(e)}"}
        
        if result is None:
            return {"error": "Failed to create booking: No response from MCP server"}
        
        if isinstance(result, dict):
            if "success" in result:
                return result
            elif len(result) > 0:
                return result
            else:
                return {"error": "Failed to create booking: Empty response from MCP server"}
        
        return {"error": f"Failed to create booking: Unexpected response type: {type(result)}"}
    
    def get_user_bookings(self, user_id: str) -> Dict[str, Any]:
        """Get all bookings for a user"""
        try:
            params = {"user_id": user_id}
            result = self.mcp_client.call_tool_sync("get_user_bookings", params)
        except concurrent.futures.TimeoutError:
            logger.error("get_user_bookings timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in get_user_bookings: {e}")
            return {"success": False, "error": f"Failed to get bookings: {str(e)}"}
        
        if result is None:
            return {"success": False, "error": "No response from MCP server"}
        
        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}
    
    def update_booking(
        self, 
        booking_id: str, 
        number_of_people: Optional[int] = None, 
        special_requests: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing booking"""
        try:
            params = {"booking_id": booking_id}
            if number_of_people is not None:
                params["number_of_people"] = number_of_people
            if special_requests is not None:
                params["special_requests"] = special_requests
            
            result = self.mcp_client.call_tool_sync("update_booking", params)
        except concurrent.futures.TimeoutError:
            logger.error("update_booking timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in update_booking: {e}")
            return {"success": False, "error": f"Failed to update booking: {str(e)}"}
        
        if result is None:
            return {"success": False, "error": "No response from MCP server"}
        
        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}
    
    def delete_booking(self, booking_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Delete (cancel) a booking"""
        try:
            params = {"booking_id": booking_id}
            if reason:
                params["reason"] = reason
            
            result = self.mcp_client.call_tool_sync("delete_booking", params)
        except concurrent.futures.TimeoutError:
            logger.error("delete_booking timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in delete_booking: {e}")
            return {"success": False, "error": f"Failed to delete booking: {str(e)}"}
        
        if result is None:
            return {"success": False, "error": "No response from MCP server"}
        
        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}
    
    def verify_otp_and_confirm_booking(self, booking_id: str, otp_code: str) -> Dict[str, Any]:
        """Verify OTP code and confirm booking"""
        try:
            params = {
                "booking_id": booking_id,
                "otp_code": otp_code
            }
            
            result = self.mcp_client.call_tool_sync("verify_otp_and_confirm_booking", params)
        except concurrent.futures.TimeoutError:
            logger.error("verify_otp_and_confirm_booking timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in verify_otp_and_confirm_booking: {e}")
            return {"success": False, "error": f"Failed to verify OTP: {str(e)}"}
        
        if result is None:
            return {"success": False, "error": "No response from MCP server"}
        
        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}
    
    def create_payment(self, booking_id: str, payment_method: str = "vnpay") -> Dict[str, Any]:
        """Create payment và generate VNPay URL"""
        try:
            params = {
                "booking_id": booking_id,
                "payment_method": payment_method
            }
            
            result = self.mcp_client.call_tool_sync("create_payment", params)
        except concurrent.futures.TimeoutError:
            logger.error("create_payment timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in create_payment: {e}")
            return {"success": False, "error": f"Failed to create payment: {str(e)}"}
        
        if result is None:
            return {"success": False, "error": "No response from MCP server"}
        
        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}


class SearchToolHandler:
    """Handler for search-related MCP tools"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    def search_tour_packages(
        self,
        user_message: str,
        max_price: Optional[float] = None,
        duration: Optional[int] = None,
        destination: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search tour packages using semantic vector search"""
        try:
            params = {"user_message": user_message, "limit": limit}
            if max_price is not None:
                params["max_price"] = max_price
            if duration is not None:
                params["duration"] = duration
            if destination:
                params["destination"] = destination
            
            result = self.mcp_client.call_tool_sync("search_tour_packages", params)
        except concurrent.futures.TimeoutError:
            logger.error("search_tour_packages timeout")
            return {"found": 0, "packages": [], "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in search_tour_packages: {e}")
            return {"found": 0, "packages": [], "error": f"Failed to search: {str(e)}"}
        
        return result if result else {"found": 0, "packages": []}
    
    def search_mem0_episodes(
        self, 
        search_query: str, 
        user_id: Optional[str] = None, 
        limit: int = 5
    ) -> Dict[str, Any]:
        """Search conversation memories stored in Mem0"""
        try:
            params = {"query_text": search_query, "limit": limit}
            if user_id:
                params["user_id"] = user_id
            
            result = self.mcp_client.call_tool_sync("search_episodes", params)
        except concurrent.futures.TimeoutError:
            logger.error("search_mem0_episodes timeout")
            return {"found": 0, "episodes": [], "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in search_mem0_episodes: {e}")
            return {"found": 0, "episodes": [], "error": f"Failed to search: {str(e)}"}
        
        return result if result else {"found": 0, "episodes": []}


class FlightToolHandler:
    """Handler for flight-related MCP tools"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    def search_flights(self, departure_iata: str, arrival_iata: str, limit: int = 5) -> str:
        """Search for flights between two airports"""
        try:
            params = {
                "departure_iata": departure_iata,
                "arrival_iata": arrival_iata,
                "limit": limit
            }
            result = self.mcp_client.call_tool_sync("search_flights", params)
        except concurrent.futures.TimeoutError:
            logger.error("search_flights timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in search_flights: {e}")
            return f"Error: Failed to search flights: {str(e)}"
        
        return result if result else "Error: No response from MCP server"


class WeatherToolHandler:
    """Handler for weather-related MCP tools"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    def get_current_temperature(self, city_name: str) -> str:
        """Get current temperature and weather conditions"""
        try:
            params = {"city_name": city_name}
            result = self.mcp_client.call_tool_sync("get_current_temperature_by_city", params)
        except concurrent.futures.TimeoutError:
            logger.error("get_current_temperature timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in get_current_temperature: {e}")
            return f"Error: Failed to get weather: {str(e)}"
        
        return result if result else "Error: No response from MCP server"
    
    def get_weather_forecast(self, city_name: str, days: int = 5) -> str:
        """Get weather forecast for a city"""
        try:
            params = {"city_name": city_name, "days": days}
            result = self.mcp_client.call_tool_sync("get_weather_forecast_by_city", params)
        except concurrent.futures.TimeoutError:
            logger.error("get_weather_forecast timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in get_weather_forecast: {e}")
            return f"Error: Failed to get forecast: {str(e)}"
        
        return result if result else "Error: No response from MCP server"


class UIToolHandler:
    """Handler for UI-related MCP tools"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    def generate_tour_ui(self, packages: list) -> Dict[str, Any]:
        """Generate interactive UI for tour packages"""
        try:
            params = {"packages": packages}
            result = self.mcp_client.call_tool_sync("generate_tour_ui", params)
        except concurrent.futures.TimeoutError:
            logger.error("generate_tour_ui timeout")
            return {"error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in generate_tour_ui: {e}")
            return {"error": f"Failed to generate UI: {str(e)}"}
        
        return result if result else {"error": "No response from MCP server"}
    
    def generate_payment_ui(
        self,
        payment_url: str,
        booking_id: str,
        total_amount: float,
        tour_name: str,
        payment_method: str = "vnpay"
    ) -> Dict[str, Any]:
        """Generate payment button UI component"""
        try:
            params = {
                "payment_url": payment_url,
                "booking_id": booking_id,
                "total_amount": total_amount,
                "tour_name": tour_name,
                "payment_method": payment_method
            }
            result = self.mcp_client.call_tool_sync("generate_payment_ui", params)
        except concurrent.futures.TimeoutError:
            logger.error("generate_payment_ui timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in generate_payment_ui: {e}")
            return {"success": False, "error": f"Failed to generate payment UI: {str(e)}"}
        
        return result if result else {"success": False, "error": "No response from MCP server"}


class RecommendationToolHandler:
    """Handler for recommendation-related tools (internal, not MCP)"""
    
    @staticmethod
    def request_recommendation(
        user_query: str,
        destination: Optional[str] = None,
        budget: Optional[float] = None,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Chat Agent calls Recommendation Agent to get tour recommendations
        
        This is how Chat Agent communicates with Recommendation Agent.
        When Chat Agent determines user needs tour recommendations, it calls this tool.
        """
        return {
            "status": "requested",
            "message": "Recommendation Agent will provide tour recommendations",
            "user_query": user_query,
            "destination": destination,
            "budget": budget,
            "duration": duration
        }


class PerplexityToolHandler:
    """Handler for Perplexity API tools (Tour Information Skill)"""
    
    def __init__(self):
        """Initialize Perplexity Tool Handler"""
        from app.v1.services.agent_services.skills.tour_information.perplexity_service import get_perplexity_service
        self.perplexity_service = get_perplexity_service()
        self.skill_loader = get_skill_loader()
        self.skill_guidelines = self._get_skill_guidelines()
    
    def _get_skill_guidelines(self) -> Optional[str]:
        """
        Load full SKILL.md content for progressive disclosure (Level 2)
        """
        try:
            content = self.skill_loader.load_skill_content("Tour Information Collector")
            return content
        except Exception as e:
            logger.warning(f"Could not load skill guidelines: {e}")
            return None
    
    async def search_latest_tour_info(self, destination: str) -> Dict[str, Any]:
        """
        Tìm thông tin tour mới nhất cho một địa điểm bằng Perplexity API
        
        Args:
            destination: Tên địa điểm (ví dụ: "Đà Lạt", "Phú Quốc", "Hà Nội")
            
        Returns:
            Dict với thông tin tour: destination, highlights, typical_prices, best_time, tips, sources
        """
        result = await self.perplexity_service.search_tour_info(destination)
        if self.skill_guidelines:
            result["skill_guidelines"] = self.skill_guidelines
        return result
    
    def search_latest_tour_info_sync(self, destination: str) -> Dict[str, Any]:
        """Synchronous wrapper for search_latest_tour_info"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, use run_until_complete in a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self.perplexity_service.search_tour_info(destination))
                    )
                    result = future.result(timeout=30)
            else:
                result = loop.run_until_complete(self.perplexity_service.search_tour_info(destination))
        except RuntimeError:
            # No event loop, create one
            result = asyncio.run(self.perplexity_service.search_tour_info(destination))
        
        if self.skill_guidelines:
            result["skill_guidelines"] = self.skill_guidelines
        return result


# ============================================================================
# MCP TOOL FACTORY - Creates LangChain StructuredTools
# ============================================================================

class MCPToolFactory:
    """Factory for creating LangChain StructuredTools from MCP handlers"""
    
    def __init__(self):
        """Initialize factory with MCP client and handlers"""
        self.mcp_client = MCPClient()
        self.booking_handler = BookingToolHandler(self.mcp_client)
        self.search_handler = SearchToolHandler(self.mcp_client)
        self.flight_handler = FlightToolHandler(self.mcp_client)
        self.weather_handler = WeatherToolHandler(self.mcp_client)
        self.ui_handler = UIToolHandler(self.mcp_client)
        self.recommendation_handler = RecommendationToolHandler()
        self.perplexity_handler = PerplexityToolHandler()
    
    # Booking Tools
    def create_booking_tool(self) -> StructuredTool:
        """Create StructuredTool for create_booking"""
        return StructuredTool.from_function(
            func=self.booking_handler.create_booking,
            name="create_booking",
            description="Tạo booking mới cho user - YÊU CẦU THU THẬP ĐẦY ĐỦ THÔNG TIN TRƯỚC KHI GỌI (user_phone, user_email, package_id, number_of_people). Hệ thống sẽ gửi mã OTP về email để xác nhận.",
            args_schema=CreateBookingInput
        )
    
    def get_user_bookings_tool(self) -> StructuredTool:
        """Create StructuredTool for get_user_bookings"""
        return StructuredTool.from_function(
            func=self.booking_handler.get_user_bookings,
            name="get_user_bookings",
            description="Lấy danh sách tất cả các booking của user. Trả về chi tiết tour, ngày khởi hành, số người, tổng tiền và trạng thái booking.",
            args_schema=GetUserBookingsInput
        )
    
    def update_booking_tool(self) -> StructuredTool:
        """Create StructuredTool for update_booking"""
        return StructuredTool.from_function(
            func=self.booking_handler.update_booking,
            name="update_booking",
            description="Cập nhật booking hiện tại - có thể thay đổi số người hoặc ghi chú đặc biệt. Nếu tăng số người, hệ thống tự động kiểm tra còn slot và cập nhật giá.",
            args_schema=UpdateBookingInput
        )
    
    def delete_booking_tool(self) -> StructuredTool:
        """Create StructuredTool for delete_booking"""
        return StructuredTool.from_function(
            func=self.booking_handler.delete_booking,
            name="delete_booking",
            description="Hủy (cancel) booking và trả lại slot cho tour. Dữ liệu booking được giữ lại với trạng thái 'cancelled' (soft delete).",
            args_schema=DeleteBookingInput
        )
    
    def verify_otp_and_confirm_booking_tool(self) -> StructuredTool:
        """Create StructuredTool for verify_otp_and_confirm_booking"""
        return StructuredTool.from_function(
            func=self.booking_handler.verify_otp_and_confirm_booking,
            name="verify_otp_and_confirm_booking",
            description="Xác thực mã OTP và xác nhận booking. Gọi tool này khi user cung cấp mã OTP 6 số từ email. Sau khi verify thành công, booking sẽ được chuyển sang trạng thái 'confirmed'.",
            args_schema=VerifyOTPInput
        )
    
    def create_payment_tool(self) -> StructuredTool:
        """Create StructuredTool for create_payment"""
        return StructuredTool.from_function(
            func=self.booking_handler.create_payment,
            name="create_payment",
            description="Tạo payment request và generate VNPay URL cho booking đã được xác nhận. Gọi tool này sau khi verify OTP thành công để tạo link thanh toán. Tool sẽ trả về payment_url để user có thể thanh toán.",
            args_schema=CreatePaymentInput
        )
    
    # Search Tools
    def search_tour_packages_tool(self) -> StructuredTool:
        """Create StructuredTool for search_tour_packages"""
        return StructuredTool.from_function(
            func=self.search_handler.search_tour_packages,
            name="search_tour_packages",
            description="Search tour packages using semantic vector search. This tool uses AI embeddings to find tours that semantically match the user's query.",
            args_schema=SearchTourPackagesInput
        )
    
    def search_mem0_episodes_tool(self) -> StructuredTool:
        """Create StructuredTool for search_mem0_episodes"""
        return StructuredTool.from_function(
            func=self.search_handler.search_mem0_episodes,
            name="search_episodes",
            description="Search through conversation history and user interactions stored in Mem0 memory system to find relevant episodes. Use this to find past conversations or user preferences related to the query.",
            args_schema=SearchEpisodesInput
        )
    
    # Flight Tools
    def search_flights_tool(self) -> StructuredTool:
        """Create StructuredTool for search_flights"""
        return StructuredTool.from_function(
            func=self.flight_handler.search_flights,
            name="search_flights",
            description="Search for flights between two airports. Returns future flights only (not yet departed). Use IATA codes (e.g., HAN=Hanoi, SGN=Ho Chi Minh, DAD=Da Nang).",
            args_schema=SearchFlightsInput
        )
    
    # Weather Tools
    def get_current_temperature_tool(self) -> StructuredTool:
        """Create StructuredTool for get_current_temperature"""
        return StructuredTool.from_function(
            func=self.weather_handler.get_current_temperature,
            name="get_current_temperature",
            description="Get current temperature and weather conditions for a city. Use this when user asks about current weather.",
            args_schema=GetCurrentTemperatureInput
        )
    
    def get_weather_forecast_tool(self) -> StructuredTool:
        """Create StructuredTool for get_weather_forecast"""
        return StructuredTool.from_function(
            func=self.weather_handler.get_weather_forecast,
            name="get_weather_forecast",
            description="Get weather forecast for a city for the next few days (1-5 days). Use this when user asks about weather forecast or future weather.",
            args_schema=GetWeatherForecastInput
        )
    
    # UI Tools
    def generate_tour_ui_tool(self) -> StructuredTool:
        """Create StructuredTool for generate_tour_ui"""
        class GenerateTourUIInput(BaseModel):
            packages: list = Field(..., description="List of tour package dictionaries to display in UI grid")
        
        return StructuredTool.from_function(
            func=self.ui_handler.generate_tour_ui,
            name="generate_tour_ui",
            description="Generate beautiful interactive UI component displaying tour packages in a responsive grid. Use this after getting tour recommendations to show them visually with images, prices, and booking buttons.",
            args_schema=GenerateTourUIInput
        )
    
    def generate_payment_ui_tool(self) -> StructuredTool:
        """Create StructuredTool for generate_payment_ui"""
        class GeneratePaymentUIInput(BaseModel):
            payment_url: str = Field(..., description="VNPay payment URL to redirect user")
            booking_id: str = Field(..., description="Booking ID for this payment")
            total_amount: float = Field(..., ge=0, description="Total amount to pay in VND")
            tour_name: str = Field(..., description="Tour package name")
            payment_method: str = Field(default="vnpay", description="Payment method")
        
        return StructuredTool.from_function(
            func=self.ui_handler.generate_payment_ui,
            name="generate_payment_ui",
            description="Generate payment button UI component for user to click and pay. Call this tool after create_payment succeeds to show payment button to user. The button will redirect user to VNPay payment page.",
            args_schema=GeneratePaymentUIInput
        )
    
    # Recommendation Tools
    def request_recommendation_tool(self) -> StructuredTool:
        """Create StructuredTool for request_recommendation"""
        return StructuredTool.from_function(
            func=self.recommendation_handler.request_recommendation,
            name="request_recommendation",
            description="Gọi Recommendation Agent để lấy tour recommendations. Sử dụng tool này khi user hỏi về tour, du lịch, địa điểm, hoặc muốn tìm tour packages. Chat Agent tự quyết định khi nào cần gọi tool này.",
            args_schema=RequestRecommendationInput
        )
    
    # Perplexity Tools (Tour Information Skill)
    def search_latest_tour_info_tool(self) -> StructuredTool:
        """Create StructuredTool for search_latest_tour_info"""
        class SearchLatestTourInfoInput(BaseModel):
            destination: str = Field(..., description="Tên địa điểm cần tìm thông tin tour (ví dụ: 'Đà Lạt', 'Phú Quốc', 'Hà Nội')")
        
        return StructuredTool.from_function(
            func=self.perplexity_handler.search_latest_tour_info_sync,
            name="search_latest_tour_info",
            description=(
                "Tìm thông tin tour mới nhất và cập nhật cho một địa điểm cụ thể bằng Perplexity API. "
                "Sử dụng khi user hỏi về: thông tin tour mới nhất, xu hướng du lịch, điểm tham quan, giá cả, lưu ý du lịch cho địa điểm. "
                "Output format (tuân theo SKILL.md): destination, highlights (list), typical_prices (string), best_time (string), tips (list), sources (list URLs). "
                "Tool này trả về thông tin real-time từ internet, khác với request_recommendation (tìm trong database)."
            ),
            args_schema=SearchLatestTourInfoInput
        )


# ============================================================================
# SINGLETON INSTANCE & BACKWARD COMPATIBILITY
# ============================================================================

# Create singleton factory instance
_tool_factory = MCPToolFactory()

# Backward compatibility: Export functions that match old API
def create_booking_sync(*args, **kwargs):
    return _tool_factory.booking_handler.create_booking(*args, **kwargs)

def get_user_bookings_sync(*args, **kwargs):
    return _tool_factory.booking_handler.get_user_bookings(*args, **kwargs)

def update_booking_sync(*args, **kwargs):
    return _tool_factory.booking_handler.update_booking(*args, **kwargs)

def delete_booking_sync(*args, **kwargs):
    return _tool_factory.booking_handler.delete_booking(*args, **kwargs)

def search_tour_packages_sync(*args, **kwargs):
    return _tool_factory.search_handler.search_tour_packages(*args, **kwargs)

def search_mem0_episodes_sync(*args, **kwargs):
    return _tool_factory.search_handler.search_mem0_episodes(*args, **kwargs)

def search_flights_sync(*args, **kwargs):
    return _tool_factory.flight_handler.search_flights(*args, **kwargs)

def get_current_temperature_sync(*args, **kwargs):
    return _tool_factory.weather_handler.get_current_temperature(*args, **kwargs)

def get_weather_forecast_sync(*args, **kwargs):
    return _tool_factory.weather_handler.get_weather_forecast(*args, **kwargs)

def generate_tour_ui_sync(*args, **kwargs):
    return _tool_factory.ui_handler.generate_tour_ui(*args, **kwargs)

def request_recommendation_sync(*args, **kwargs):
    return _tool_factory.recommendation_handler.request_recommendation(*args, **kwargs)

# Backward compatibility: Export tool creators
def create_booking_tool() -> StructuredTool:
    return _tool_factory.create_booking_tool()

def get_user_bookings_tool() -> StructuredTool:
    return _tool_factory.get_user_bookings_tool()

def update_booking_tool() -> StructuredTool:
    return _tool_factory.update_booking_tool()

def delete_booking_tool() -> StructuredTool:
    return _tool_factory.delete_booking_tool()

def verify_otp_and_confirm_booking_tool() -> StructuredTool:
    return _tool_factory.verify_otp_and_confirm_booking_tool()

def create_payment_tool() -> StructuredTool:
    return _tool_factory.create_payment_tool()

def search_tour_packages_tool() -> StructuredTool:
    return _tool_factory.search_tour_packages_tool()

def search_mem0_episodes_tool() -> StructuredTool:
    return _tool_factory.search_mem0_episodes_tool()

def search_flights_tool() -> StructuredTool:
    return _tool_factory.search_flights_tool()

def get_current_temperature_tool() -> StructuredTool:
    return _tool_factory.get_current_temperature_tool()

def get_weather_forecast_tool() -> StructuredTool:
    return _tool_factory.get_weather_forecast_tool()

def generate_tour_ui_tool() -> StructuredTool:
    return _tool_factory.generate_tour_ui_tool()

def generate_payment_ui_tool() -> StructuredTool:
    return _tool_factory.generate_payment_ui_tool()

def request_recommendation_tool() -> StructuredTool:
    return _tool_factory.request_recommendation_tool()

def search_latest_tour_info_tool() -> StructuredTool:
    return _tool_factory.search_latest_tour_info_tool()

# Legacy compatibility: Keep old call_mcp_tool function
async def call_mcp_tool(tool_name: str, params: Dict[str, Any]) -> Any:
    """Legacy function for backward compatibility"""
    client = MCPClient()
    return await client.call_tool(tool_name, params)
