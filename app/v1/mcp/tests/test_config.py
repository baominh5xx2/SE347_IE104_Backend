"""
Test Configuration
"""
import pytest
from src.mcp_server.core.config import Settings


def test_settings_defaults():
    """Test default settings values"""
    settings = Settings()
    
    assert settings.SERVER_NAME == "AI Assistant MCP Server"
    assert settings.SERVER_VERSION == "1.0.0"
    assert settings.BACKEND_API_URL == "http://localhost:8000"
    assert settings.BACKEND_API_TIMEOUT == 30
    assert settings.MAX_ITERATIONS == 10
    assert settings.TIMEOUT == 300
    assert settings.LOG_LEVEL == "INFO"


def test_settings_custom_values():
    """Test custom settings values"""
    settings = Settings(
        SERVER_NAME="Custom Server",
        BACKEND_API_URL="http://example.com",
        MAX_ITERATIONS=20
    )
    
    assert settings.SERVER_NAME == "Custom Server"
    assert settings.BACKEND_API_URL == "http://example.com"
    assert settings.MAX_ITERATIONS == 20
