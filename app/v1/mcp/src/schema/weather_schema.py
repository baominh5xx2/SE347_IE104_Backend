"""
Weather Tools Schema
Input schemas for weather-related MCP tools
"""
from pydantic import BaseModel, Field


class GetCurrentTemperatureInput(BaseModel):
    """Input schema for get_current_temperature_by_city tool"""
    city_name: str = Field(..., description="City name (e.g., 'Hanoi', 'Ho Chi Minh', 'Da Nang')")


class GetWeatherForecastInput(BaseModel):
    """Input schema for get_weather_forecast_by_city tool"""
    city_name: str = Field(..., description="City name for weather forecast")
    days: int = Field(default=5, ge=1, le=14, description="Number of days to forecast (1-14 days)")
