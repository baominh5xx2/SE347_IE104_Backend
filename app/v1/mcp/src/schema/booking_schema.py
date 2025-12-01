"""
Booking Tools Schema
Input schemas for booking-related MCP tools
"""
from pydantic import BaseModel, Field
from typing import Optional


class CreateBookingInput(BaseModel):
    """Input schema for create_booking tool"""
    user_phone: str = Field(..., description="User phone number (Vietnamese format, e.g., '0901234567')")
    package_id: str = Field(..., description="Tour package UUID (must be exactly as returned from search_tour_packages)")
    number_of_people: int = Field(..., ge=1, le=50, description="Number of people (1-50)")
    special_requests: Optional[str] = Field(default="", description="Special requests or dietary restrictions")
    user_id: Optional[str] = Field(None, description="User ID if available (for authenticated users)")


class UpdateBookingInput(BaseModel):
    """Input schema for update_booking tool"""
    booking_id: str = Field(..., description="The ID of the booking to update")
    number_of_people: Optional[int] = Field(None, ge=1, le=50, description="New number of people (optional)")
    special_requests: Optional[str] = Field(None, description="New special requests (optional)")


class DeleteBookingInput(BaseModel):
    """Input schema for delete_booking tool"""
    booking_id: str = Field(..., description="The ID of the booking to cancel/delete")
    reason: Optional[str] = Field(None, description="Reason for cancellation")


class GetUserBookingsInput(BaseModel):
    """Input schema for get_user_bookings tool"""
    user_id: str = Field(..., description="User ID was retrieved from the agent state. Do not ask user anymore.")
