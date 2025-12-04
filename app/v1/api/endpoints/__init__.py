"""API endpoints package initialization"""
from . import chat, agent, health, auth, tour_packages, bookings, promotions

__all__ = ["chat", "agent", "health", "auth", "tour_packages", "bookings", "promotions"]