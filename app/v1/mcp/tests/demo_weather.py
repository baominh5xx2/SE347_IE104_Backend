import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_server.core.config import settings
from src.mcp_server.tools.weather_tools import WeatherService


async def test_current_weather(weather_service: WeatherService):
    """
    Test current weather retrieval for multiple cities.
    
    This function demonstrates the use of WeatherService.get_current_temperature()
    method to retrieve real-time weather data for Vietnamese cities.
    
    Args:
        weather_service (WeatherService): An instance of WeatherService
    """
    print("📍 Testing Current Weather")
    print("-" * 60)
    
    # Define test cities (English name, Vietnamese name)
    cities = [
        ("Ho Chi Minh", "Thành phố Hồ Chí Minh"),
        ("Soc Trang", "Sóc Trăng"),
        ("Hanoi", "Hà Nội"),
        ("Da Nang", "Đà Nẵng"),
    ]
    
    # Test current weather for each city
    for city_en, city_vi in cities:
        print(f"\n🌍 {city_vi} ({city_en}):")
        try:
            # Call the get_current_temperature method
            result = await weather_service.get_current_temperature(city_en)
            
            # Display result with proper formatting
            if result.startswith("Error"):
                print(f"   ❌ {result}")
            else:
                # Parse and display in a formatted way
                print(f"   ✅ {result}")
                
        except Exception as e:
            print(f"   ❌ Unexpected error: {str(e)}")


async def test_weather_forecast(weather_service: WeatherService):
    """
    Test weather forecast retrieval for a specific city.
    
    This function demonstrates the use of WeatherService.get_weather_forecast()
    method to retrieve multi-day weather forecasts.
    
    Args:
        weather_service (WeatherService): An instance of WeatherService
    """

    print("=" * 60)
    print("📅 Testing Weather Forecast")
    print("-" * 60)
    
    # Define test cities and forecast days
    test_cases = [
        ("Ho Chi Minh", "Thành phố Hồ Chí Minh", 3),
        ("Hanoi", "Hà Nội", 3),
    ]
    
    # Test forecast for each city
    for city_en, city_vi, days in test_cases:
        print(f"\n🌍 {days}-day forecast for {city_vi} ({city_en}):")
        print()
        
        try:
            # Call the get_weather_forecast method
            result = await weather_service.get_weather_forecast(city_en, days=days)
            
            # Display result
            if result.startswith("Error"):
                print(f"   ❌ {result}")
            else:
                # Print the formatted forecast
                print(result)
                
        except Exception as e:
            print(f"   ❌ Unexpected error: {str(e)}")


async def test_weather_tools():
    """
    Main test function for Weather Tools.
    
    This function orchestrates all weather tool tests by:
    1. Creating a WeatherService instance
    2. Testing current weather retrieval
    3. Testing weather forecast retrieval
    
    The function demonstrates proper OOP usage with the WeatherService class.
    """
    print("=" * 60)
    print("🌤️  Weather Tools Demo - OOP Version")
    print("=" * 60)
    print()
    
    # Create WeatherService instance
    # This demonstrates proper OOP instantiation
    weather_service = WeatherService()
    
    # Verify API key is configured
    if not weather_service.api_key:
        print("❌ ERROR: WEATHER_API_KEY not configured!")
        print("   Please set your OpenWeatherMap API key in environment variables.")
        return
    
    # Test 1: Current Weather
    try:
        await test_current_weather(weather_service)
    except Exception as e:
        print(f"\n❌ Current weather test failed: {str(e)}")
    
    print()
    
    # Test 2: Weather Forecast
    try:
        await test_weather_forecast(weather_service)
    except Exception as e:
        print(f"\n❌ Forecast test failed: {str(e)}")


def main():
    """
    Main entry point for the demo script.
    
    This function initializes the demo and runs all async tests.
    It displays configuration information and handles the async event loop.
    """
    print()
    print("📋 Configuration:")
    print(f"   • Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run async tests
    try:
        asyncio.run(test_weather_tools())
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")


if __name__ == "__main__":
    main()


