"""
Tour Search Tools Schema
Input schemas for tour search and recommendation MCP tools
"""
from pydantic import BaseModel, Field
from typing import Optional


class SearchTourPackagesInput(BaseModel):
    """Input schema for search_tour_packages tool"""
    user_message: str = Field(..., description="User's search query in Vietnamese or English (e.g., 'Tôi muốn đi Đà Lạt', 'beach tour')")
    max_price: Optional[float] = Field(default=None, ge=0, description="IGNORED - kept for compatibility. Max price filter in VND")
    duration: Optional[int] = Field(default=None, ge=1, le=30, description="IGNORED - kept for compatibility. Duration filter in days")
    destination: Optional[str] = Field(default=None, description="IGNORED - kept for compatibility. Destination filter")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of results (1-50)")


class RequestRecommendationInput(BaseModel):
    """Input schema for request_recommendation tool"""
    user_query: str = Field(..., description="User's search query or travel request")
    destination: Optional[str] = Field(default=None, description="Optional destination preference")
    budget: Optional[float] = Field(default=None, ge=0, description="Optional budget in VND")
    duration: Optional[int] = Field(default=None, ge=1, le=30, description="Optional trip duration in days")
