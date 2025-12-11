"""
Unit tests for LLM providers factory (OpenAI / Modal)
"""
import pytest
from app.v1.services.agent_services import config as agent_services_config
from app.v1.services.agent_services.llm_providers import create_llm_provider
from app.v1.services.agent_services.llm_providers.openai_provider import OpenAIProvider
from app.v1.services.agent_services.llm_providers.modal_provider import ModalProvider


@pytest.fixture(autouse=True)
def reset_provider():
    # Ensure each test starts with default provider = openai
    agent_services_config.agent_config.provider = "openai"
    agent_services_config.agent_config.modal_api_url = ""
    agent_services_config.agent_config.modal_api_key = ""
    yield
    # Reset after test
    agent_services_config.agent_config.provider = "openai"
    agent_services_config.agent_config.modal_api_url = ""
    agent_services_config.agent_config.modal_api_key = ""


def test_factory_returns_openai_by_default():
    provider = create_llm_provider()
    assert isinstance(provider, OpenAIProvider)


def test_factory_returns_modal_when_config_set():
    agent_services_config.agent_config.provider = "modal"
    provider = create_llm_provider()
    assert isinstance(provider, ModalProvider)


def test_modal_provider_injects_modal_api_url(monkeypatch):
    agent_services_config.agent_config.provider = "modal"
    agent_services_config.agent_config.modal_api_url = "https://example.modal.run"
    agent_services_config.agent_config.modal_api_key = "modal-key"

    provider = create_llm_provider()
    llm = provider.get_llm(model="mistral-7b-instruct")  # should not raise

    # The underlying ChatOpenAI stores base_url attribute; ensure it was set
    assert getattr(llm, "client_params", {}).get("base_url") == "https://example.modal.run"
    assert getattr(llm, "api_key") == "modal-key"


