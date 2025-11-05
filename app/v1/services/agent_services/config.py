"""
Multi-Agent System Configuration
Centralized configuration for all agents
"""
from pydantic import BaseModel
from app.v1.core.config import settings

logger = None  # Will be initialized in setup


class AgentConfig(BaseModel):
    """Configuration for agent system"""
    
    # LLM Configuration
    model: str = settings.OPENAI_MODEL
    api_key: str = settings.OPENAI_API_KEY
    organization: str = settings.OPENAI_ORGANIZATION  # Optional OpenAI organization ID
    temperature: float = 0.7
    
    # Agent Configuration
    max_iterations: int = 10
    timeout: int = 300
    
    # Streaming
    enable_streaming: bool = True
    
    # Tracking
    enable_falkor_tracking: bool = False
    
    # MCP Configuration
    mcp_server_url: str = settings.MCP_SERVER_URL
    mcp_timeout: int = settings.MCP_TIMEOUT
    mcp_retry_count: int = settings.MCP_RETRY_COUNT
    mcp_retry_backoff: float = settings.MCP_RETRY_BACKOFF


# Global config instance
agent_config = AgentConfig()

