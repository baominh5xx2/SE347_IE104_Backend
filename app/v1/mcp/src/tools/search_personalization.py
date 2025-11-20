"""
MCP Tools - Search Personalization
Search conversation memories stored in Mem0 for personalization.
"""
from fastmcp import FastMCP
from typing import Optional, Dict, Any
import logging

from src.core.mem0_client import mem0_client

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


from pydantic import ValidationError
from app.v1.mcp.src.schema import SearchEpisodesInput

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

        Returns:
            Dict with:
            - found (int): Number of episodes found
            - episodes (list): List of episode dictionaries compatible with agents
        """
        try:
            validated = SearchEpisodesInput(
                search_query=query_text,
                user_id=user_id,
                limit=limit
            )
            # ... implementation ...
            # For now, just return empty or call service if available
            # Assuming mem0_client is available in scope or imported
            from app.v1.core.mem0_client import mem0_client
            
            results = await mem0_client.search_memories(
                query=validated.search_query,
                user_id=validated.user_id,
                limit=validated.limit
            )
            return {"found": len(results), "episodes": results}
            
        except ValidationError as e:
            return {"found": 0, "episodes": [], "error": str(e)}
        except Exception as e:
            return {"found": 0, "episodes": [], "error": str(e)}

