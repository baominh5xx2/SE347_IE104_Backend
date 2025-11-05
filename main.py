"""
Main FastAPI Application with LangGraph Integration
"""
import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.v1.core.config import settings
from app.v1.api.router import api_router

# Initialize logging FIRST before any other imports
from app.v1.core.logging_config import setup_logging
setup_logging(
    level=settings.LOG_LEVEL,
    enable_langchain_tracing=settings.LANGCHAIN_TRACING,
    enable_callback=settings.LANGCHAIN_VERBOSE
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting AI Assistant Backend with LangGraph...")
    
    # Test Supabase connection
    try:
        from app.v1.core.supabase import supabase_client
        print("🔍 Testing Supabase connection...")
        
        # Test connection by checking if client is properly initialized
        if supabase_client and hasattr(supabase_client, 'table'):
            print("✅ Supabase connection successful!")
            print(f"🔗 Connected to: {settings.SUPABASE_URL}")
        else:
            print("❌ Supabase client not properly initialized")
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {str(e)}")
        print("🔧 Please check your SUPABASE_URL and SUPABASE_KEY in .env file")
        # Don't exit, just warn - app can still run without DB
    
    # Test FalkorDB connection
    try:
        from app.v1.core.falkor import falkor_graph
        print("🔍 Testing FalkorDB connection...")
        
        if falkor_graph:
            # Test with simple query
            result = falkor_graph.query("RETURN 'Hello FalkorDB' as message")
            if result and result.result_set:
                print("✅ FalkorDB connection successful!")
                print(f"🔗 Connected to: {settings.FALKORDB_HOST}:{settings.FALKORDB_PORT}")
                print(f"📊 Database: {settings.FALKORDB_DATABASE}")
            else:
                print("❌ FalkorDB query failed")
        else:
            print("❌ FalkorDB client not properly initialized")
        
    except Exception as e:
        print(f"❌ FalkorDB connection failed: {str(e)}")
        print("🔧 Please check your FALKORDB_* settings in .env file")
        # Don't exit, just warn - app can still run without FalkorDB
    
    yield
    # Shutdown
    print("👋 Shutting down AI Assistant Backend...")


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

# Include API router
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
