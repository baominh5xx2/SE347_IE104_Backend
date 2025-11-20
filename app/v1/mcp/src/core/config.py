"""
Core Configuration Module
"""
import os
from typing import Optional
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root() -> Path:
    """
    Find the project root directory by looking for pyproject.toml or .git
    This ensures .env is always found regardless of where the script is run from
    """
    current = Path(__file__).resolve()
    
    # Try to find project root by looking for marker files
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    
    # Fallback: go 3 levels up from this file
    return Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Server Configuration
    SERVER_NAME: str = Field(default="AI Assistant MCP Server", description="MCP server name")
    SERVER_VERSION: str = Field(default="1.0.0", description="Server version")
    
    # Backend API Configuration
    BACKEND_API_URL: str = Field(
        default="http://localhost:8000",
        description="Backend API base URL"
    )
    BACKEND_API_TIMEOUT: int = Field(default=30, description="API timeout in seconds")
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-5-mini", description="OpenAI model")
    
    # Supabase Configuration (for tour search and booking)
    SUPABASE_URL: Optional[str] = Field(default=None, description="Supabase project URL")
    SUPABASE_KEY: Optional[str] = Field(default=None, description="Supabase API key")

    # Mem0 Configuration
    MEM0_API_KEY: Optional[str] = Field(default=None, description="Mem0 API key")
    
    # Weather API Configuration
    WEATHER_API_KEY: Optional[str] = Field(default=None, description="OpenWeatherMap API key")
    
    # Flight API Configuration
    FLIGHT_API_KEY: Optional[str] = Field(default=None, description="AviationStack API key")
    
    # Google Drive Configuration
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = Field(default=None, description="Google Drive Folder ID")
    GOOGLE_CREDENTIALS_PATH: Optional[str] = Field(default=None, description="Path to Google credentials JSON")
    
    # Agent Configuration
    MAX_ITERATIONS: int = Field(default=10, description="Max agent iterations")
    TIMEOUT: int = Field(default=300, description="Agent timeout in seconds")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    model_config = SettingsConfigDict(
        env_file=str(find_project_root() / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Weather API Configuration
    WEATHER_API_KEY: str = Field(
        default="",
        description="OpenWeatherMap API key (get free key at https://openweathermap.org/api)"
    )
    
    # Flight API Configuration
    FLIGHT_API_KEY: str = Field(
        default="",
        description="AviationStack API key (get free key at https://aviationstack.com/)"
    )
    
    # Google Drive Configuration (for document resources)
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = Field(
        default=None,
        description="Google Drive folder ID for documents"
    )
    GOOGLE_CREDENTIALS_PATH: Optional[str] = Field(
        default=None,
        description="Path to Google credentials JSON"
    )
    
    # Agent Configuration
    MAX_ITERATIONS: int = Field(default=10, description="Max agent iterations")
    TIMEOUT: int = Field(default=300, description="Agent timeout in seconds")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # FalkorDB Configuration
    FALKORDB_HOST: str = Field(default="localhost", description="FalkorDB host")
    FALKORDB_PORT: int = Field(default=6379, description="FalkorDB port")
    FALKORDB_USERNAME: Optional[str] = Field(default=None, description="FalkorDB username")
    FALKORDB_PASSWORD: Optional[str] = Field(default=None, description="FalkorDB password")
    FALKORDB_DATABASE: str = Field(default="TravelBooking", description="FalkorDB graph database name")
    FALKORDB_SSL: bool = Field(default=False, description="FalkorDB SSL connection")
    FALKORDB_SAVE_BOOKINGS: bool = Field(default=False, description="Enable saving bookings to FalkorDB")
    
    model_config = SettingsConfigDict(
        # Dynamically find .env in project root
        env_file=str(find_project_root() / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )


# Global settings instance
settings = Settings()
