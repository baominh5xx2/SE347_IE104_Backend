from pydantic import BaseModel, Field
from typing import Optional, Dict

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
    user_email: str = Field(description="User email address - REQUIRED for OTP verification")
    package_id: str = Field(description="Tour package ID from recommendation results")
    number_of_people: int = Field(description="Number of people traveling")
    special_requests: str = Field(default="", description="Special requests or requirements")
    user_id: Optional[str] = Field(default=None, description="User ID if available (for authenticated users)")


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
    """Input schema for search_mem0_episodes tool"""
    query_text: str = Field(description="Search query text to find relevant episodes in Mem0 conversation history")
    user_id: Optional[str] = Field(default=None, description="Optional user ID for personalized search")
    limit: int = Field(default=5, description="Maximum number of results to return (1-20)")