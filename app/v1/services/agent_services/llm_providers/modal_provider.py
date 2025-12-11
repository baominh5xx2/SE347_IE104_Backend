"""
Modal LLM Provider
Uses ChatOpenAI-compatible client pointing to Modal endpoint.
Assumes Modal exposes an OpenAI-compatible API.
"""
import logging
from typing import Any
from langchain_openai import ChatOpenAI

from app.v1.services.agent_services.llm_providers.base_provider import BaseLLMProvider
from app.v1.services.agent_services.config import agent_config

logger = logging.getLogger(__name__)


class ModalProvider(BaseLLMProvider):
    """Provider for Modal-hosted models (OpenAI-compatible endpoint)."""

    def get_llm(self, **kwargs: Any):
        # Merge defaults from config if not provided
        model_kwargs = dict(kwargs)
        
        # Normalize base_url: ensure it ends with /v1 for OpenAI-compatible API
        if "base_url" not in model_kwargs and agent_config.modal_api_url:
            base_url = agent_config.modal_api_url.strip()
            # Remove trailing slash
            if base_url.endswith('/'):
                base_url = base_url[:-1]
            # Ensure /v1 is present (ChatOpenAI needs it for OpenAI-compatible endpoints)
            if not base_url.endswith('/v1'):
                # Remove /v1 if it exists somewhere else, then add it at the end
                if '/v1' in base_url:
                    base_url = base_url.split('/v1')[0]
                base_url = base_url.rstrip('/') + '/v1'
            model_kwargs["base_url"] = base_url
            logger.info(f"🔗 Modal base_url: {base_url}")
        
        # Set model name: Modal uses Qwen/Qwen3-8B-FP8, not OpenAI model names
        # Only use model from kwargs if explicitly provided, otherwise use Modal's model
        if "model" not in model_kwargs:
            # Check if agent_config.model is a Modal/HuggingFace model (contains /)
            if agent_config.model and "/" in agent_config.model:
                # Looks like a HuggingFace model name (e.g., Qwen/Qwen3-8B-FP8)
                model_kwargs["model"] = agent_config.model
            else:
                # Default to Modal's model (ignore OpenAI model names like gpt-5-mini)
                model_kwargs["model"] = "Qwen/Qwen3-8B-FP8"
                logger.warning(f"⚠️ Modal provider: Ignoring OpenAI model '{agent_config.model}', using Modal model 'Qwen/Qwen3-8B-FP8'")
            logger.info(f"📌 Using Modal model: {model_kwargs['model']}")
        
        # Set API key if provided
        if "api_key" not in model_kwargs and agent_config.modal_api_key:
            model_kwargs["api_key"] = agent_config.modal_api_key
        
        logger.info(f"🤖 Creating Modal LLM with model: {model_kwargs.get('model')}, base_url: {model_kwargs.get('base_url')}")
        return ChatOpenAI(**model_kwargs)


