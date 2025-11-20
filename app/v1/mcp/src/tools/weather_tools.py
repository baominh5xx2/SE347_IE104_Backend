"""
MCP Tools - Weather Tools
Get current weather and forecasts using OpenWeatherMap API
"""
from fastmcp import FastMCP
from typing import Dict, Any, Optional
import httpx
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from ..core.config import settings
from app.v1.mcp.src.schema import GetCurrentTemperatureInput, GetWeatherForecastInput


class WeatherService:
    """
    Weather Service class for retrieving weather information.
    
    This class provides methods to get current temperature and weather forecasts
    for cities using the OpenWeatherMap API. All times are converted to Vietnam
    timezone (UTC+7).
    
    Attributes:
        api_key (str): OpenWeatherMap API key
        base_url (str): Base URL for OpenWeatherMap API
        vietnam_tz (timezone): Vietnam timezone (UTC+7)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize WeatherService with API key.
        
        Args:
            api_key (Optional[str]): OpenWeatherMap API key. 
                                    If not provided, uses settings.WEATHER_API_KEY
        """
        self.api_key = api_key or settings.WEATHER_API_KEY
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.vietnam_tz = timezone(timedelta(hours=7))
    
    async def get_current_temperature(self, city_name: str) -> str:
        """
        Get current temperature and weather conditions for a city.
        
        This method retrieves real-time weather data including temperature,
        feels-like temperature, humidity, and weather description.
        Time is displayed in Vietnam timezone (UTC+7).
        
        Args:
            city_name (str): Name of the city to get weather for
            
        Returns:
            str: Formatted weather information string including:
                - City name
                - Local time (Vietnam timezone UTC+7)
                - Current temperature in Celsius
                - Feels-like temperature
                - Weather description
                - Humidity percentage
                
        Raises:
            Returns error message string if API call fails
            
        Example:
            >>> weather_service = WeatherService()
            >>> result = await weather_service.get_current_temperature("Hanoi")
            >>> print(result)
            Weather in Hanoi at 2025-10-16 14:30:00 (Vietnam time UTC+7): 
            28.5°C (feels like 30.2°C), clear sky, humidity: 65%
        """
        # Validate API key
        if not self.api_key:
            return "Error: WEATHER_API_KEY not found in environment variables"
        
        try:
            # Prepare API request
            url = f"{self.base_url}/weather"
            params = {
                "q": city_name,
                "appid": self.api_key,
                "units": "metric"  # Use Celsius
            }
            
            # Make async HTTP request
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
            
            # Extract weather data
            temperature = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            description = data["weather"][0]["description"]
            
            # Convert timestamp to Vietnam timezone
            obs_timestamp = data.get("dt")
            
            if obs_timestamp is None:
                # Fallback to current UTC time if API doesn't provide timestamp
                obs_dt_utc = datetime.now(timezone.utc)
            else:
                obs_dt_utc = datetime.fromtimestamp(obs_timestamp, tz=timezone.utc)
            
            # Convert to Vietnam timezone (UTC+7)
            local_dt = obs_dt_utc.astimezone(self.vietnam_tz)
            time_str = local_dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Format and return result
            return (
                f"Weather in {city_name} at {time_str} (Vietnam time UTC+7): "
                f"{temperature:.1f}°C (feels like {feels_like:.1f}°C), "
                f"{description}, humidity: {humidity}%"
            )
        
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors
            if e.response.status_code == 404:
                return f"Error: City '{city_name}' not found."
            if e.response.status_code == 401:
                return "Error: Invalid API key."
            return f"Error: HTTP {e.response.status_code}"
        except Exception as e:
            # Handle unexpected errors
            return f"Unexpected error: {e}"
    
    async def get_weather_forecast(self, city_name: str, days: int = 5) -> str:
        """
        Get weather forecast for a city for the next few days.
        
        This method retrieves weather forecast data and aggregates it by day,
        providing temperature ranges, weather conditions, humidity, and rain probability.
        All times are displayed in Vietnam timezone (UTC+7).
        
        Args:
            city_name (str): Name of the city to get forecast for
            days (int, optional): Number of days to forecast (1-5). Defaults to 5.
            
        Returns:
            str: Formatted forecast string with daily weather information including:
                - Date
                - Temperature range (min-max) and average
                - Most common weather condition
                - Average humidity
                - Average rain probability
                
        Raises:
            Returns error message string if API call fails
        """
        
        # Validate API key
        if not self.api_key:
            return "Error: WEATHER_API_KEY not found in environment variables"
        
        # Limit days between 1 and 5
        days = max(1, min(days, 5))
        
        try:
            # Prepare API request
            url = f"{self.base_url}/forecast"
            params = {
                "q": city_name,
                "appid": self.api_key,
                "units": "metric",  # Use Celsius
                "cnt": days * 8  # API returns data every 3 hours, so 8 entries per day
            }
            
            # Make async HTTP request
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
            
            forecast_list = data.get("list", [])
            
            # Aggregate forecast data by day
            daily_data: Dict[str, Dict[str, list]] = {}
            
            for item in forecast_list:
                # Convert timestamp to Vietnam timezone
                utc_dt = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
                local_dt = utc_dt.astimezone(self.vietnam_tz)
                date_key = local_dt.strftime("%Y-%m-%d")
                
                # Initialize date entry if not exists
                if date_key not in daily_data:
                    daily_data[date_key] = {
                        "temps": [],
                        "humidity": [],
                        "weather": [],
                        "rain_prob": []
                    }
                
                # Collect data for this date
                daily_data[date_key]["temps"].append(item["main"]["temp"])
                daily_data[date_key]["humidity"].append(item["main"]["humidity"])
                daily_data[date_key]["weather"].append(item["weather"][0]["description"])
                
                # Add rain probability if available
                if "pop" in item:
                    daily_data[date_key]["rain_prob"].append(item["pop"] * 100)
            
            # Format result string
            result = f"Weather forecast for {city_name} (Vietnam time UTC+7):\n\n"
            
            for date, day_info in list(daily_data.items())[:days]:
                # Calculate statistics for the day
                avg_temp = sum(day_info["temps"]) / len(day_info["temps"])
                min_temp = min(day_info["temps"])
                max_temp = max(day_info["temps"])
                avg_humidity = sum(day_info["humidity"]) / len(day_info["humidity"])
                
                # Get most common weather description
                most_common_weather = max(
                    set(day_info["weather"]),
                    key=day_info["weather"].count
                )
                
                # Calculate average rain probability
                avg_rain = (
                    sum(day_info["rain_prob"]) / len(day_info["rain_prob"])
                    if day_info["rain_prob"] else 0
                )
                
                # Format day information
                result += (
                    f"📅 {date}:\n"
                    f"   🌡️  Temp: {min_temp:.1f}°C - {max_temp:.1f}°C "
                    f"(avg: {avg_temp:.1f}°C)\n"
                    f"   ☁️  Weather: {most_common_weather}\n"
                    f"   💧 Humidity: {avg_humidity:.0f}%\n"
                    f"   🌧️  Rain chance: {avg_rain:.0f}%\n\n"
                )
            
            return result.strip()
        
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors
            if e.response.status_code == 404:
                return f"Error: City '{city_name}' not found."
            if e.response.status_code == 401:
                return "Error: Invalid API key."
            return f"Error: HTTP {e.response.status_code}"
        except Exception as e:
            # Handle unexpected errors
            return f"Unexpected error: {e}"


def register_weather_tools(mcp: FastMCP):
    """
    Register weather tools with FastMCP server.
    
    This function creates a WeatherService instance and registers its methods
    as MCP tools, allowing them to be called through the MCP protocol.
    
    Args:
        mcp (FastMCP): FastMCP instance to register tools with
        
    Example:
        >>> from fastmcp import FastMCP
        >>> mcp = FastMCP(name="weather-server")
        >>> register_weather_tools(mcp)
    """
    # Create WeatherService instance
    weather_service = WeatherService()
    
    @mcp.tool()
    async def get_current_temperature_by_city(city_name: str) -> str:
        """
        Get current temperature and weather conditions for a city.
        
        Returns:
            str: Temperature, feels-like temperature, humidity, and weather description
                 in Vietnam timezone (UTC+7)
        """
        try:
            validated = GetCurrentTemperatureInput(city_name=city_name)
            return await weather_service.get_current_temperature(validated.city_name)
        except ValidationError as e:
            return f"❌ Input Validation Error: {str(e)}"
    
    @mcp.tool()
    async def get_weather_forecast_by_city(city_name: str, days: int = 5) -> str:
        """
        Get weather forecast for a city for the next few days.
        
        Returns:
            str: Daily forecast including temperature, humidity, and weather conditions
        """
        try:
            validated = GetWeatherForecastInput(city_name=city_name, days=days)
            return await weather_service.get_weather_forecast(validated.city_name, validated.days)
        except ValidationError as e:
            return f"❌ Input Validation Error: {str(e)}"

