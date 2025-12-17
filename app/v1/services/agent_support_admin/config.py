"""
Admin Agent Configuration
Loads from admin_agent.yaml with env variable substitution
Following LangGraph configuration pattern
"""
import os
import re
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel
from app.v1.core.config import settings

logger = logging.getLogger(__name__)


def _resolve_env_vars(value: Any) -> Any:
    """
    Resolve environment variables in YAML values.
    Supports ${VAR:-default} syntax.
    """
    if isinstance(value, str):
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


def _load_admin_yaml_config() -> Dict[str, Any]:
    """Load admin_agent.yaml and resolve env variables"""
    config_path = Path(__file__).parent.parent.parent.parent.parent / "admin_agent.yaml"
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return _resolve_env_vars(config)
        logger.warning(f"admin_agent.yaml not found at {config_path}")
        return {}
    except Exception as e:
        logger.error(f"Could not load admin_agent.yaml: {e}")
        return {}


class AdminAgentConfig(BaseModel):
    """Configuration for admin agent system"""
    
    # LLM Configuration
    model: str = settings.OPENAI_MODEL
    api_key: str = settings.OPENAI_API_KEY
    provider: str = settings.LLM_PROVIDER
    temperature: float = 0.3
    max_tokens: int = 1024
    streaming: bool = False
    
    # Agent Configuration
    name: str = "admin_agent"
    description: str = "Admin agent with BigQuery tool"
    max_iterations: int = 5
    timeout: int = 60
    
    # Memory Configuration
    max_history: int = 10
    
    class Config:
        """Pydantic config"""
        extra = "allow"
    
    @classmethod
    def from_yaml(cls) -> "AdminAgentConfig":
        """Create config from admin_agent.yaml, fallback to settings"""
        yaml_config = _load_admin_yaml_config()
        llm_config = yaml_config.get('llm', {})
        agent_config = yaml_config.get('agent', {})
        memory_config = yaml_config.get('memory', {})
        
        return cls(
            # LLM config
            provider=llm_config.get('provider', settings.LLM_PROVIDER),
            model=llm_config.get('model', settings.OPENAI_MODEL),
            api_key=llm_config.get('api_key', settings.OPENAI_API_KEY) or settings.OPENAI_API_KEY,
            temperature=llm_config.get('temperature', 0.3),
            max_tokens=llm_config.get('max_tokens', 1024),
            streaming=llm_config.get('streaming', False),
            # Agent config
            name=agent_config.get('name', 'admin_agent'),
            description=agent_config.get('description', 'Admin agent with BigQuery tool'),
            max_iterations=agent_config.get('max_iterations', 5),
            timeout=agent_config.get('timeout', 60),
            # Memory config
            max_history=memory_config.get('max_history', 10),
        )


def get_admin_prompts() -> Dict[str, str]:
    """Get prompts from admin_agent.yaml"""
    yaml_config = _load_admin_yaml_config()
    agent_config = yaml_config.get('agent', {})
    prompts = agent_config.get('prompts', {})
    
    return {
        'system': prompts.get('system', ''),
        'sql_generation': prompts.get('sql_generation', ''),
        'result_formatting': prompts.get('result_formatting', ''),
    }


def get_admin_tools_config() -> list:
    """Get tools configuration from admin_agent.yaml"""
    yaml_config = _load_admin_yaml_config()
    return yaml_config.get('tools', [])


def get_admin_workflow_config() -> Dict[str, Any]:
    """Get workflow configuration from admin_agent.yaml"""
    yaml_config = _load_admin_yaml_config()
    return yaml_config.get('workflow', {})


def get_system_prompt() -> str:
    """Get system prompt from admin_agent.yaml"""
    prompts = get_admin_prompts()
    return prompts.get('system', '')


# Global config instance
admin_agent_config = AdminAgentConfig.from_yaml()
