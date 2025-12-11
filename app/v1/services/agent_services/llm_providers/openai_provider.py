"""
OpenAI LLM Provider
Wraps ChatOpenAI from langchain_openai.
"""
from typing import Any
from langchain_openai import ChatOpenAI

from app.v1.services.agent_services.llm_providers.base_provider import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """Provider for OpenAI (ChatOpenAI)."""

    def get_llm(self, **kwargs: Any):
        return ChatOpenAI(**kwargs)


