"""
Application Configuration
"""
import os
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
    # LLM Provider Switch
    LLM_PROVIDER: str = "openai"  # Options: openai | modal
    MODAL_API_URL: str = ""  # Modal endpoint (OpenAI-compatible)
    MODAL_API_KEY: str = ""  # Modal auth token if required
    # Perplexity Configuration
    PERPLEXITY_API_KEY: str = ""
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
    # NOTE: Nếu dùng ngrok, cập nhật GOOGLE_REDIRECT_URI trong .env thành ngrok URL
    # và thêm URL đó vào Google Cloud Console > Credentials > OAuth 2.0 Client > Authorized redirect URIs
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    
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
    FRONTEND_BASE_URL: str = "http://localhost:3000"  # Frontend URL to redirect after payment
    
    # OTP & Email Configuration
    OTP_EXPIRE_MINUTES: int = 5  # OTP hết hạn sau 5 phút
    SENDGRID_API_KEY: str = ""  # SendGrid API key
    SENDGRID_FROM_EMAIL: str = "noreply@yourdomain.com"  # Email gửi đi
    
    # Travel News Configuration
    TRAVEL_NEWS_SEARCH_QUERIES: List[str] = [
        "tin tức du lịch mới nhất 2024",
        "cẩm nang du lịch Việt Nam",
        "destination hot trending",
        "tour promotions deals",
    ]  # Queries để search - sẽ search với detailed prompt ưu tiên trending & recent content
    TRAVEL_NEWS_SCHEDULE_HOUR: int = 17  # Hour để chạy scheduled job (17 = 5 PM)
    TRAVEL_NEWS_SCHEDULE_MINUTE: int = 0  # Minute để chạy scheduled job
    
    # Admin Recommendation Configuration
    ADMIN_RECOMMENDATION_ENABLED: bool = False  # Enable Admin Mode for tour recommendations (override AI with featured tours)
    
    @field_validator('OPENAI_API_KEY', mode='before')
    @classmethod
    def prefer_exported_openai_key(cls, v):
        """
        Allow overriding OpenAI key via exported env (e.g., OPENAI_API_KEY or OPENAI_API_KEY_EXPORT).
        Falls back to value provided (e.g., from .env) if no exported key is present.
        """
        if v:
            return v
        alt = os.getenv("OPENAI_API_KEY_EXPORT") or os.getenv("OPENAI_API_KEY")
        if alt:
            return alt
        raise ValueError("OPENAI_API_KEY is required (set OPENAI_API_KEY or OPENAI_API_KEY_EXPORT)")
    
    @field_validator('PERPLEXITY_API_KEY', mode='before')
    @classmethod
    def prefer_perplexity_key(cls, v):
        """Allow PERPLEXITY_API_KEY from env, return empty if not set"""
        if v:
            return v
        alt = os.getenv("PERPLEXITY_API_KEY")
        return alt if alt else ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env that are not in Settings


settings = Settings()
