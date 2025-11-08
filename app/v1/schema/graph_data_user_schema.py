
"""
Simple Graph Data Schema for User Interactions
Using Graphiti's automatic entity extraction - no custom schema needed
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel


class EpisodeData(BaseModel):
    """Simple episode data structure for API responses"""
    episode_id: str
    name: str
    episode_body: str
    source_description: str
    created_at: str
    user_id: Optional[str] = None
    search_method: Optional[str] = None


class PersonalizationContext(BaseModel):
    """Personalization context from user's episodes"""
    user_id: str
    episodes: List[EpisodeData]
    has_data: bool
    
    class Config:
        arbitrary_types_allowed = True

