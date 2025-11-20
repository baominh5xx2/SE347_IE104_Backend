"""
UI Generation Tools Schema
Input schemas for MCP-UI generation tools
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any


class TourPackageUIModel(BaseModel):
    """Single tour package for UI generation"""
    package_id: str = Field(..., description="UUID of the package")
    package_name: str = Field(..., description="Tour package name")
    destination: str = Field(..., description="Destination location")
    duration_days: int = Field(..., ge=1, description="Tour duration in days")
    price: float = Field(..., ge=0, description="Price in VND")
    image_urls: str = Field(..., description="Pipe-separated image URLs (e.g., 'url1|url2|url3')")
    description: str = Field(..., description="Tour description")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD format)")
    available_slots: int = Field(..., ge=0, description="Number of available slots")


class GenerateTourUIInput(BaseModel):
    """Input schema for generate_tour_ui tool"""
    packages: List[Dict[str, Any]] = Field(..., description="List of tour package dictionaries to display in UI grid. Each package should have: package_id, package_name, destination, duration_days, price, image_urls, description, start_date, available_slots")
