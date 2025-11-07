"""
Base Agent Class
Base class for all agents with common functionality
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from app.v1.services.agent_services.config import agent_config
from app.v1.core.logging_config import agent_callback
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
        **kwargs
    ):
        """
        Initialize base agent
        
        Args:
            name: Agent name for logging
            model: LLM model (defaults to config)
            temperature: LLM temperature (defaults to config)
        """
        self.name = name
        self.model = model or agent_config.model
        self.temperature = temperature if temperature is not None else agent_config.temperature
        
        # Initialize LLM
        callbacks = [agent_callback] if agent_callback and agent_config.enable_streaming else []
        
        # Build LLM kwargs
        llm_kwargs = {
            "model": self.model,
            "api_key": agent_config.api_key,
            "temperature": self.temperature,
            "streaming": agent_config.enable_streaming,
            "callbacks": callbacks,
            "verbose": agent_config.enable_streaming
        }
        
        # Add organization if provided
        if agent_config.organization:
            llm_kwargs["organization"] = agent_config.organization
        
        self.llm = ChatOpenAI(**llm_kwargs)
        
        logger.info(f"✅ {self.name} initialized (model: {self.model}, temp: {self.temperature})")
    
    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process agent logic
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state
        """
        pass
    
    def get_llm(self) -> ChatOpenAI:
        """Get LLM instance"""
        return self.llm
