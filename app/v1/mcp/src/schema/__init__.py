"""
MCP Tools Schema Definitions
Organized schemas for each tool in separate files
"""

from .weather_schema import GetCurrentTemperatureInput, GetWeatherForecastInput
from .flight_schema import SearchFlightsInput
from .booking_schema import (
    CreateBookingInput,
    UpdateBookingInput,
    DeleteBookingInput,
    GetUserBookingsInput,
    VerifyOTPInput,
    CreatePaymentInput
)
from .tour_search_schema import SearchTourPackagesInput, RequestRecommendationInput
from .ui_schema import GenerateTourUIInput, TourPackageUIModel
from .search_schema import SearchEpisodesInput

__all__ = [
    # Weather
    "GetCurrentTemperatureInput",
    "GetWeatherForecastInput",
    # Flight
    "SearchFlightsInput",
    # Booking
    "CreateBookingInput",
    "UpdateBookingInput",
    "DeleteBookingInput",
    "GetUserBookingsInput",
    "VerifyOTPInput",
    "CreatePaymentInput",
    # Tour Search
    "SearchTourPackagesInput",
    "RequestRecommendationInput",
    # UI
    "GenerateTourUIInput",
    "TourPackageUIModel",
    # Search
    "SearchEpisodesInput",
]
