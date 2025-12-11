"""
LLM provider factory
Allows switching between OpenAI and Modal via configuration.
"""
from app.v1.services.agent_services.config import agent_config
from app.v1.services.agent_services.llm_providers.openai_provider import OpenAIProvider
from app.v1.services.agent_services.llm_providers.modal_provider import ModalProvider


def create_llm_provider():
    """
    Factory to create LLM provider instance based on configuration.
    Defaults to OpenAI if provider not recognized.
    """
    provider = (agent_config.provider or "openai").lower()
    if provider == "modal":
        return ModalProvider()
    return OpenAIProvider()


