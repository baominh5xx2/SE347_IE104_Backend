"""
MCP Tools - Search Personalization
Search conversation memories stored in Mem0 for personalization.
"""
from fastmcp import FastMCP
from typing import Optional, Dict, Any
import logging

from src.mcp_server.core.mem0_client import mem0_client

logger = logging.getLogger(__name__)


def _format_mem0_episode(memory: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Mem0 memory into the legacy episode format expected by agents."""
    metadata = memory.get("metadata", {}) or {}

    return {
        "episode_id": memory.get("id"),
        "name": metadata.get("title") or metadata.get("intent") or "mem0_episode",
        "episode_body": memory.get("memory") or metadata.get("content") or "",
        "source_description": metadata.get("source", "Mem0 conversation memory"),
        "created_at": memory.get("created_at"),
        "user_id": memory.get("user_id"),
        "search_method": "mem0_semantic",
        "score": memory.get("score"),
        "metadata": metadata
    }


def register_search_personalization_tools(mcp: FastMCP):
    """Register search personalization tools using Mem0"""

    @mcp.tool()
    async def search_episodes(
        query_text: str,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Search for relevant conversation memories stored in Mem0.

        This replaces the legacy Graphiti-based episode search. Results are pulled
        from Mem0 using semantic search with Mem0 v2 filters to ensure user isolation.

        Args:
            query_text (str): Search query text. Example: "Đà Lạt tour", "beach destinations"
            user_id (str, optional): User ID for personalized search. Example: "user_123"
            limit (int, optional): Maximum number of results to return. Default: 5. Example: 5

        Returns:
            Dict with:
            - found (int): Number of episodes found
            - episodes (list): List of episode dictionaries compatible with agents
        """
        try:
            filters: Optional[Dict[str, Any]] = None
            if user_id:
                # Use OR so multiple user filters can be merged upstream if needed
                filters = {"OR": [{"user_id": user_id}]}

            memories = mem0_client.search(
                query=query_text,
                user_id=user_id,
                limit=limit,
                filters=filters
            )

            if memories:
                episodes = [_format_mem0_episode(memory) for memory in memories]
                return {
                    "found": len(episodes),
                    "episodes": episodes
                }

            return {
                "found": 0,
                "episodes": [],
                "message": f"No episodes found for query: '{query_text}'"
            }

        except Exception as e:
            logger.error(f"❌ Error in search_episodes tool: {str(e)}")
            return {
                "found": 0,
                "episodes": [],
                "error": str(e),
                "message": f"Error searching episodes: {str(e)}"
            }

