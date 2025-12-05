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
    OPENAI_MODEL: str = "gpt-5-mini"
    OPENAI_ORGANIZATION: str = ""  # Optional: OpenAI organization ID for organization-level API access

    
    # Graphiti OpenAI Configuration
    GRAPHITI_SMALL_MODEL: str = "gpt-5-mini"  # For fast operations
    GRAPHITI_MAIN_MODEL: str = "gpt-5-mini"  # For main operations
    GRAPHITI_EMBEDDING_MODEL: str = "text-embedding-3-large"  # Embedding model
    
    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/aiassistant"
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # JWT Configuration
    JWT_SECRET: str
    JWT_EXPIRE: int = 7  # Token expiration in days
    # Token encryption (Fernet URL-safe base64 key). If empty, tokens stored plaintext (not recommended).
    TOKEN_ENCRYPTION_KEY: str = ""
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    
    # Admin Configuration
    ADMIN_SECRET_KEY: str = ""  # Secret key để tạo admin mới (optional, để trống nếu không cần)
    
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
    MCP_SERVER_URL: str = "http://localhost:8001"
    MCP_TIMEOUT: int = 30
    MCP_RETRY_COUNT: int = 3  # Number of retry attempts
    MCP_RETRY_BACKOFF: float = 2.0  # Exponential backoff multiplier
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    LANGCHAIN_VERBOSE: bool = True  # Enable verbose logging for LangChain
    LANGCHAIN_TRACING: bool = False  # Enable LangSmith tracing
    LANGCHAIN_API_KEY: str = ""  # LangSmith API key (optional)
    LANGCHAIN_PROJECT: str = "ai-assistant-backend"  # LangSmith project name
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"  # LangSmith API endpoint
    
    # VNPay Configuration
    VNPAY_TMN_CODE: str = ""  # Merchant code from VNPay
    VNPAY_HASH_SECRET: str = ""  # Secret key from VNPay
    VNPAY_URL: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"  # VNPay payment URL
    VNPAY_RETURN_URL: str = "http://localhost:8000/api/v1/payments/vnpay/return"  # Return URL after payment
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env that are not in Settings


settings = Settings()
