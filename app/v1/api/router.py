"""
Main API Router
"""
from fastapi import APIRouter
from .endpoints import chat, agent, health

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])
