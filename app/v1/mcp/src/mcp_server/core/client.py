"""
Backend API Client
HTTP client for communicating with the backend API
"""
import httpx
from typing import Any, Dict, Optional
from .config import settings


class BackendClient:
    """
    Async HTTP client for backend API communication
    """
    
    def __init__(self):
        self.base_url = settings.BACKEND_API_URL
        self.timeout = settings.BACKEND_API_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Context manager entry"""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self._client:
            await self._client.aclose()
    
    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat message to the agent
        
        Args:
            message: The message to send
            conversation_id: Optional conversation ID
            user_id: Optional user ID
            
        Returns:
            Agent response
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        response = await self._client.post(
            "/api/v1/chat",
            json={
                "message": message,
                "conversation_id": conversation_id,
                "user_id": user_id
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get conversation history
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Conversation data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        response = await self._client.get(f"/api/v1/conversations/{conversation_id}")
        response.raise_for_status()
        return response.json()
    
    async def delete_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Delete a conversation
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Deletion result
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        response = await self._client.delete(f"/api/v1/conversations/{conversation_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """
        Get agent status
        
        Returns:
            Agent status
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        response = await self._client.get("/api/v1/agent/status")
        response.raise_for_status()
        return response.json()
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """
        Get agent information
        
        Returns:
            Agent info
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        response = await self._client.get("/api/v1/agent/info")
        response.raise_for_status()
        return response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check backend health
        
        Returns:
            Health status
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()

