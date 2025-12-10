"""
Main FastAPI Application with LangGraph Integration
"""
import uvicorn
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.v1.core.config import settings
from app.v1.api.router import api_router

# Import MCP server instance
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "app/v1/mcp"))
from app.v1.mcp.server import mcp as mcp_server

# Initialize logging FIRST before any other imports
from app.v1.core.logging_config import setup_logging
setup_logging(
    level=settings.LOG_LEVEL,
    enable_langchain_tracing=settings.LANGCHAIN_TRACING,
    enable_callback=settings.LANGCHAIN_VERBOSE
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Start scheduler on startup
    from app.v1.services.scheduled_tasks import start_scheduler, shutdown_scheduler
    start_scheduler()
    logger.info("Application started, scheduler initialized")
    
    yield
    
    # Shutdown scheduler on shutdown
    shutdown_scheduler()
    logger.info("Application shutting down, scheduler stopped")


# Initialize FastAPI app
app = FastAPI(
    title="AI Assistant API with LangGraph",
    description="Backend API for AI Assistant using LangGraph for agent orchestration",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,  # Disable 307 redirect for trailing slashes
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP Server
mcp_app = mcp_server.http_app(path="")

# Expose MCP endpoints at /mcp via router include (FastAPI will merge lifespans)
app.include_router(mcp_app.router, prefix="/mcp")

# Include API router at /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Assistant API with LangGraph",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
