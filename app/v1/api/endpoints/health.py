"""
Health Check Endpoints
"""
from fastapi import APIRouter, status

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Assistant API",
        "version": "1.0.0"
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """Readiness check endpoint"""
    # Add checks for dependencies (database, redis, etc.)
    return {
        "status": "ready",
        "dependencies": {
            "database": "healthy",
            "cache": "healthy",
            "llm": "healthy"
        }
    }
