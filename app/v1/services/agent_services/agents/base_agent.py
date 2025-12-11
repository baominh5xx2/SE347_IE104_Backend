"""
Base Agent Class
Base class for all agents with common functionality
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.v1.services.agent_services.config import agent_config
from app.v1.core.logging_config import agent_callback
from app.v1.services.agent_services.llm_providers import create_llm_provider
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents
    
    Provides common functionality:
    - LLM initialization
    - Logging
    - Error handling
    """
    
    def __init__(
        self,
        name: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        reasoning: Optional[dict] = None,
        **kwargs
    ):
        """
        Initialize base agent
        
        Args:
            name: Agent name for logging
            model: LLM model (defaults to config)
            temperature: LLM temperature (defaults to config)
            reasoning: Reasoning config (defaults to config)
        """
        self.name = name
        self.model = model or agent_config.model
        self.temperature = temperature if temperature is not None else agent_config.temperature
        self.reasoning = reasoning or getattr(agent_config, 'reasoning', None)
        
        # Initialize LLM
        callbacks = [agent_callback] if agent_callback and agent_config.enable_streaming else []
        
        # Build LLM kwargs
        llm_kwargs = {
            "model": self.model,
            "api_key": agent_config.api_key
        }
        
        # if self.temperature is not None:
        #     llm_kwargs["temperature"] = self.temperature
            
        if agent_config.enable_streaming:
            llm_kwargs["streaming"] = agent_config.enable_streaming
            
        if callbacks:
            llm_kwargs["callbacks"] = callbacks
            
        if agent_config.enable_streaming:
            llm_kwargs["verbose"] = agent_config.enable_streaming
        
        if self.reasoning:
            llm_kwargs["reasoning"] = self.reasoning
            
        if agent_config.organization:
            llm_kwargs["organization"] = agent_config.organization
        
        # Use provider factory to create LLM (OpenAI or Modal)
        provider = create_llm_provider()
        self.llm = provider.get_llm(**llm_kwargs)
    
    def get_llm(self):
        """Get LLM instance"""
        return self.llm
