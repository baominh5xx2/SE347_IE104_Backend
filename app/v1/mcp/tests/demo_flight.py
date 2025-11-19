"""
Demo script for searching flights between airports
Demonstrates the FlightService functionality
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_server.tools.flight_tools import FlightService


async def search_vietnam_flights():
    """
    Demo function to search for flights on various routes
    """
    # Create flight service instance
    flight_service = FlightService()
    
    # Demo 1: Hanoi to Ho Chi Minh City
    print("\n" + "=" * 70)
    print("🔎 Demo 1: Tìm chuyến bay Sài Gòn → Hà Nội")
    print("=" * 70)
    result = await flight_service.search_flights(
        departure_iata="SGN",  # Hanoi
        arrival_iata="HAN",    # Ho Chi Minh City
        limit=5,               # Show 5 flights
        future_only=True       # Only show future flights
    )
    print(result)
    
    # Demo 2: Ho Chi Minh City to Da Nang
    print("\n\n" + "=" * 70)
    print("🔎 Demo 2: Tìm chuyến bay Sài Gòn → Đà Nẵng")
    print("=" * 70)
    result = await flight_service.search_flights(
        departure_iata="SGN",  # Ho Chi Minh City
        arrival_iata="DAD",    # Da Nang
        limit=5,               # Show 5 flights
        future_only=True       # Only show future flights
    )
    print(result)
    
    # Demo 3: Ho Chi Minh City to Tokyo (Narita)
    print("\n\n" + "=" * 70)
    print("🔎 Demo 3: Tìm chuyến bay Sài Gòn → Tokyo (Narita)")
    print("=" * 70)
    result = await flight_service.search_flights(
        departure_iata="SGN",  # Ho Chi Minh City
        arrival_iata="NRT",    # Tokyo Narita
        limit=5,               # Show 5 flights
        future_only=True       # Only show future flights
    )
    print(result)
    
    # Demo 4: Ho Chi Minh City to Osaka
    print("\n\n" + "=" * 70)
    print("🔎 Demo 4: Tìm chuyến bay Sài Gòn → Osaka")
    print("=" * 70)
    result = await flight_service.search_flights(
        departure_iata="SGN",  # Ho Chi Minh City
        arrival_iata="KIX",    # Osaka Kansai
        limit=5,               # Show 5 flights
        future_only=True       # Only show future flights
    )
    print(result)


if __name__ == "__main__":
    print("\n" + "🛫" * 35)
    print("   FLIGHT SEARCH DEMO - AviationStack API")
    print("🛫" * 35)
    asyncio.run(search_vietnam_flights())
    print("\n" + "=" * 70)
    print("✅ Demo completed!")
    print("=" * 70 + "\n")

