"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5-nano"
    
    # Graphiti OpenAI Configuration
    GRAPHITI_SMALL_MODEL: str = "gpt-5-nano"  # For fast operations
    GRAPHITI_MAIN_MODEL: str = "gpt-5-nano"  # For main operations
    GRAPHITI_EMBEDDING_MODEL: str = "text-embedding-3-large"  # Embedding model
    
    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/aiassistant"
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # JWT Configuration
    JWT_SECRET: str
    JWT_EXPIRE: int = 7  # Token expiration in days
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000"]
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    # Agent Configuration
    MAX_ITERATIONS: int = 10
    TIMEOUT: int = 300
    
    # FalkorDB Configuration
    FALKORDB_HOST: str = ""
    FALKORDB_PORT: int = 49560
    FALKORDB_USERNAME: str = ""
    FALKORDB_PASSWORD: str = ""
    FALKORDB_DATABASE: str = "db1"
    FALKORDB_SSL: bool = False
    
    # MCP Server Configuration
    MCP_SERVER_URL: str = "http://localhost:3000"
    MCP_TIMEOUT: int = 30
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    LANGCHAIN_VERBOSE: bool = True  # Enable verbose logging for LangChain
    LANGCHAIN_TRACING: bool = False  # Enable LangSmith tracing
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env that are not in Settings


settings = Settings()
