"""
Configuration management for MCP Server
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """MCP Server Settings"""
    
    # Server Info
    MCP_SERVER_NAME: str = "ai-assistant-mcp"
    MCP_SERVER_VERSION: str = "0.1.0"
    MCP_DEBUG: bool = True
    
    # Backend API
    BACKEND_API_URL: str = "http://localhost:8000"
    BACKEND_API_TIMEOUT: int = 30
    
    # OpenAI (optional)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-5-mini"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
