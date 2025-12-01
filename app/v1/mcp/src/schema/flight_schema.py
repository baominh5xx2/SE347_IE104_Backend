"""
Flight Tools Schema
Input schemas for flight-related MCP tools
"""
from pydantic import BaseModel, Field


class SearchFlightsInput(BaseModel):
    """Input schema for search_flights tool"""
    departure_iata: str = Field(..., description="Departure airport IATA code (e.g., 'HAN' for Hanoi, 'SGN' for HCMC, 'DAD' for Da Nang)")
    arrival_iata: str = Field(..., description="Arrival airport IATA code")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of flights to return (1-20)")
