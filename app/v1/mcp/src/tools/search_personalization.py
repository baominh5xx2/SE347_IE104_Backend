"""
MCP Tools - Search Personalization
Search conversation memories stored in Mem0 for personalization.
"""
from fastmcp import FastMCP
from typing import Optional, Dict, Any
import logging

from app.v1.mcp.src.core.mem0_client import mem0_client

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
            # Use MCP Mem0 client to search memories
            if not mem0_client.is_available:
                logger.warning("Mem0 client not available for search_episodes")
                return {"found": 0, "episodes": []}
            
            # Search memories using MCP Mem0 client
            results = mem0_client.search(
                query=validated.search_query,
                user_id=validated.user_id,
                limit=validated.limit
            )
            
            # Format results as episodes
            episodes = []
            for memory in results:
                formatted = _format_mem0_episode(memory)
                episodes.append(formatted)
            
            logger.info(f"✅ Found {len(episodes)} episodes for query: {validated.search_query[:50]}...")
            return {"found": len(episodes), "episodes": episodes}
            
        except ValidationError as e:
            return {"found": 0, "episodes": [], "error": str(e)}
        except Exception as e:
            return {"found": 0, "episodes": [], "error": str(e)}

