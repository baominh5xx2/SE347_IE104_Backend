"""
Main API Router
"""
from fastapi import APIRouter
from .endpoints import chat, agent, health, auth, tour_packages, bookings

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tour_packages.router, prefix="/tour-packages", tags=["Tour Packages"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])