"""
Search Tools Schema
Input schemas for search-related MCP tools (Mem0)
"""
from pydantic import BaseModel, Field
from typing import Optional


class SearchEpisodesInput(BaseModel):
    """Input schema for search_episodes tool (Mem0)"""
    search_query: str = Field(..., description="Search query to find relevant conversation history")
    user_id: Optional[str] = Field(default=None, description="Optional user ID for personalized search")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of episodes to return (1-20)")
