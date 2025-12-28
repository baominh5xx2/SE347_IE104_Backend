"""
Multi-Agent System Configuration
Centralized configuration for all agents
Loads from agent.yaml with env variable substitution
"""
import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel
from app.v1.core.config import settings

logger = None  # Will be initialized in setup


def _resolve_env_vars(value: Any) -> Any:
    """
    Resolve environment variables in YAML values.
    Supports ${VAR:-default} syntax.
    """
    if isinstance(value, str):
        # Match ${VAR:-default} or ${VAR}
        pattern = r'\$\{([^}]+)\}'
        
        def replace_env(match):
            expr = match.group(1)
            if ':-' in expr:
                var_name, default = expr.split(':-', 1)
                return os.getenv(var_name.strip(), default.strip())
            else:
                return os.getenv(expr.strip(), '')
        
        return re.sub(pattern, replace_env, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def _load_yaml_config() -> Dict[str, Any]:
    """Load agent.yaml and resolve env variables"""
    config_path = Path(__file__).parent.parent.parent.parent.parent / "agent.yaml"
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return _resolve_env_vars(config)
        return {}
    except Exception as e:
        print(f"Warning: Could not load agent.yaml: {e}")
        return {}


class AgentConfig(BaseModel):
    """Configuration for agent system"""
    
    # LLM Configuration
    model: str = settings.OPENAI_MODEL
    api_key: str = settings.OPENAI_API_KEY
    organization: str = ""  # Optional OpenAI organization ID
    provider: str = settings.LLM_PROVIDER
    modal_api_url: str = settings.MODAL_API_URL
    modal_api_key: str = settings.MODAL_API_KEY
    temperature: float = 0.7
    reasoning: Optional[Dict[str, Any]] = None  # Reasoning config for OpenAI o1/o3 models
    
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

    @classmethod
    def from_yaml(cls) -> "AgentConfig":
        """Create config from agent.yaml, fallback to settings"""
        yaml_config = _load_yaml_config()
        llm_config = yaml_config.get('llm', {})
        
        # Merge YAML config with defaults (YAML has priority)
        return cls(
            # LLM config from YAML or settings
            provider=llm_config.get('provider', settings.LLM_PROVIDER),
            model=llm_config.get('model', settings.OPENAI_MODEL),
            modal_api_url=llm_config.get('modal_api_url', settings.MODAL_API_URL) or settings.MODAL_API_URL,
            modal_api_key=llm_config.get('modal_api_key', settings.MODAL_API_KEY) or settings.MODAL_API_KEY,
            temperature=llm_config.get('temperature', 0.7),
            reasoning=llm_config.get('reasoning'),  # Load reasoning config from YAML (only for o1/o3 models)
            # Keep other defaults from settings
            api_key=settings.OPENAI_API_KEY,
            organization="",
            max_iterations=10,
            timeout=300,
            enable_streaming=True,
            enable_falkor_tracking=False,
            mcp_server_url=settings.MCP_SERVER_URL,
            mcp_timeout=settings.MCP_TIMEOUT,
            mcp_retry_count=settings.MCP_RETRY_COUNT,
            mcp_retry_backoff=settings.MCP_RETRY_BACKOFF,
        )


# Global config instance - loads from YAML if available
agent_config = AgentConfig.from_yaml()
