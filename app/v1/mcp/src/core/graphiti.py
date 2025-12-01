"""
Graphiti Service - Graphiti initialization and episode management
Following Graphiti documentation standards
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import uuid

from src.mcp_server.core.config import settings

logger = logging.getLogger(__name__)

# Import Graphiti
try:
    from graphiti_core import Graphiti
    from graphiti_core.driver.falkordb_driver import FalkorDriver
    from graphiti_core.nodes import EpisodeType
    
    GRAPHITI_AVAILABLE = True
    logger.info("✅ Graphiti imports successful")
except ImportError as e:
    GRAPHITI_AVAILABLE = False
    logger.error(f"❌ Graphiti import failed: {str(e)}")


class GraphitiService:
    """
    Graphiti Service for episode management and search
    Following Graphiti standards:
    - Use add_episode() for data ingestion
    - Use search_episodes() for hybrid search of episodes
    - Use get_user_episodes() for user-specific episode search
    - Let Graphiti handle entity extraction automatically
    """
    
    def __init__(self):
        """Initialize Graphiti with configuration from settings"""
        self.graphiti = None
        self.graphiti_enabled = False
        
        if GRAPHITI_AVAILABLE:
            try:
                logger.info("🔄 Initializing Graphiti...")
                
                # Create FalkorDB driver
                falkor_driver = FalkorDriver(
                    host=settings.FALKORDB_HOST,
                    port=settings.FALKORDB_PORT,
                    username=settings.FALKORDB_USERNAME,
                    password=settings.FALKORDB_PASSWORD,
                    database=settings.FALKORDB_DATABASE
                )
                
                # Initialize Graphiti - it handles LLM and embeddings internally
                self.graphiti = Graphiti(graph_driver=falkor_driver)
                
                self.graphiti_enabled = True
                logger.info("✅ Graphiti initialized successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Graphiti: {str(e)}")
                self.graphiti_enabled = False
        else:
            logger.warning("⚠️ Graphiti not available")
    
    async def search_episodes(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search episodes using Graphiti's hybrid search
        
        Args:
            query_text: Search query
            user_id: Optional user ID for focal node search
            limit: Number of results
            
        Returns:
            List of episodes
        """
        if not self.graphiti_enabled or not self.graphiti:
            logger.warning("⚠️ Graphiti not available")
            return []
        
        try:
            # Use Graphiti's standard search
            # This returns edges (facts) by default
            search_results = await self.graphiti.search(query_text)
            
            if not search_results:
                logger.info(f"📊 No results found for query: '{query_text}'")
                return []
            
            logger.info(f"📊 Found {len(search_results)} results from Graphiti")
            
            # Convert results to episode format
            episodes = []
            for item in search_results[:limit]:
                # Check if this is an edge (fact) with episodes
                if hasattr(item, 'episodes') and item.episodes:
                    # Get episode IDs
                    for episode_ref in item.episodes[:1]:  # Take first episode
                        if isinstance(episode_ref, str):
                            # Episode ID - create episode dict from available data
                            episode = {
                                "episode_id": episode_ref,
                                "name": f"episode_{episode_ref[:8]}",
                                "episode_body": getattr(item, 'fact', '') or f"Episode {episode_ref}",
                                "source_description": getattr(item, 'source_description', ''),
                                "created_at": str(getattr(item, 'created_at', '')),
                                "user_id": user_id or "",
                                "search_method": "episode_fetch"
                            }
                            episodes.append(episode)
                
                if len(episodes) >= limit:
                    break
            
            logger.info(f"✅ Retrieved {len(episodes)} episodes")
            return episodes
            
        except Exception as e:
            logger.error(f"❌ Error searching episodes: {str(e)}")
            return []
    
    async def get_user_episodes(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get all episodes for a user using Graphiti's search
        
        Args:
            user_id: User ID
            limit: Number of results
            
        Returns:
            List of user's episodes
        """
        if not self.graphiti_enabled or not self.graphiti:
            logger.warning("⚠️ Graphiti not available")
            return []
        
        try:
            # Search for user-specific content
            search_results = await self.graphiti.search(f"user {user_id}")
            
            if not search_results:
                logger.info(f"📊 No episodes found for user: {user_id}")
                return []
            
            logger.info(f"📊 Found {len(search_results)} results for user {user_id}")
            
            # Convert to episode format
            episodes = []
            for item in search_results[:limit]:
                if hasattr(item, 'episodes') and item.episodes:
                    for episode_ref in item.episodes[:1]:
                        if isinstance(episode_ref, str):
                            # Episode ID - create episode dict from available data
                            episode = {
                                "episode_id": episode_ref,
                                "name": f"episode_{episode_ref[:8]}",
                                "episode_body": getattr(item, 'fact', '') or f"Episode {episode_ref}",
                                "source_description": getattr(item, 'source_description', ''),
                                "created_at": str(getattr(item, 'created_at', '')),
                                "user_id": user_id,
                                "search_method": "user_search"
                            }
                            episodes.append(episode)
                
                if len(episodes) >= limit:
                    break
            
            logger.info(f"✅ Retrieved {len(episodes)} episodes for user {user_id}")
            return episodes
            
        except Exception as e:
            logger.error(f"❌ Error getting user episodes: {str(e)}")
            return []


# Singleton instance
_graphiti_service = None


def get_graphiti_service() -> GraphitiService:
    """Get or create Graphiti service singleton"""
    global _graphiti_service
    if _graphiti_service is None:
        _graphiti_service = GraphitiService()
    return _graphiti_service

