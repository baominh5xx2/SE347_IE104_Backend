"""
Base LLM Provider
Defines interface for creating LangChain-compatible chat models.
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def get_llm(self, **kwargs: Any):
        """
        Return a LangChain-compatible chat model.

        Args:
            **kwargs: Provider-specific keyword arguments (model, api_key, etc.)
        """
        raise NotImplementedError


