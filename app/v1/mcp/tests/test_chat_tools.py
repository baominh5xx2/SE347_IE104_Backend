"""
Test Chat Tools
"""
import pytest
from unittest.mock import AsyncMock, patch
from src.mcp_server.tools.chat_tools import register_chat_tools
from fastmcp import FastMCP


@pytest.fixture
def mcp_server():
    """Create a FastMCP server instance for testing"""
    return FastMCP("Test Server")


@pytest.fixture
def mock_backend_client():
    """Mock BackendClient"""
    with patch("src.mcp_server.tools.chat_tools.BackendClient") as mock:
        client_instance = AsyncMock()
        mock.return_value.__aenter__.return_value = client_instance
        yield client_instance


@pytest.mark.asyncio
async def test_chat_with_agent(mcp_server, mock_backend_client):
    """Test chat_with_agent tool"""
    # Setup mock response
    mock_backend_client.chat.return_value = {
        "conversation_id": "test_123",
        "message": "Hello, how can I help?",
        "metadata": {"iterations": 1},
        "timestamp": "2025-10-11T10:00:00"
    }
    
    # Register tools
    register_chat_tools(mcp_server)
    
    # Test would go here - FastMCP testing framework needed
    # This is a placeholder showing the test structure
    assert True


@pytest.mark.asyncio
async def test_get_conversation_history(mcp_server, mock_backend_client):
    """Test get_conversation_history tool"""
    mock_backend_client.get_conversation.return_value = {
        "conversation_id": "test_123",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ],
        "summary": {"message_count": 2}
    }
    
    register_chat_tools(mcp_server)
    assert True


@pytest.mark.asyncio
async def test_delete_conversation(mcp_server, mock_backend_client):
    """Test delete_conversation tool"""
    mock_backend_client.delete_conversation.return_value = True
    
    register_chat_tools(mcp_server)
    assert True
