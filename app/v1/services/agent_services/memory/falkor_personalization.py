"""
FalkorDB Personalization Service - Simple implementation using Graphiti
Following Graphiti documentation standards
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import uuid

from app.v1.core.config import settings

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


class FalkorPersonalizationService:
    """
    Simple Personalization Service using Graphiti
    
    Following Graphiti standards:
    - Use add_episode() for data ingestion
    - Use search() for hybrid search
    - Use search(query, focal_node_uuid) for user-specific search
    - Let Graphiti handle entity extraction automatically
    """
    
    def __init__(self):
        """Initialize Graphiti with minimal configuration"""
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
    
    async def add_episode(
        self,
        conversation_id: str,
        user_message: str,
        assistant_response: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add episode using Graphiti's standard format
        
        Args:
            conversation_id: Conversation ID
            user_message: User's message
            assistant_response: Assistant's response
            user_id: Optional user ID
            metadata: Optional metadata (intent, destinations, etc.)
            
        Returns:
            episode_id: UUID from Graphiti
        """
        if not self.graphiti_enabled or not self.graphiti:
            logger.warning("⚠️ Graphiti not available")
            return f"ep_{uuid.uuid4().hex[:12]}"
        
        try:
            # Build episode body - Graphiti will extract entities automatically
            episode_body = f"""User: {user_message}
Assistant: {assistant_response}"""
            
            # Add metadata context if provided
            if metadata:
                if metadata.get("intent"):
                    episode_body += f"\nIntent: {metadata['intent']}"
                if metadata.get("destinations"):
                    episode_body += f"\nDestinations: {', '.join(metadata['destinations'])}"
                if metadata.get("price_range"):
                    episode_body += f"\nPrice Range: {metadata['price_range']}"
                if metadata.get("duration"):
                    episode_body += f"\nDuration: {metadata['duration']} days"
            
            # Generate episode name
            episode_name = f"conversation_{conversation_id}_{uuid.uuid4().hex[:8]}"
            
            # Add episode using Graphiti standard format
            result = await self.graphiti.add_episode(
                name=episode_name,
                episode_body=episode_body,
                source=EpisodeType.message,
                source_description=f"Chat conversation for user {user_id}" if user_id else "Chat conversation",
                reference_time=datetime.now()
            )
            
            # Get episode_id from result
            episode_id = getattr(result, 'episode_id', None) or episode_name
            logger.info(f"✅ Episode {episode_id} added successfully")
            
            return episode_id
            
        except Exception as e:
            logger.error(f"❌ Error adding episode: {str(e)}")
            return f"ep_{uuid.uuid4().hex[:12]}"
    
    async def search_episodes(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        limit: int = 5
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
    
    async def generate_personalization_context(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate personalization context for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with user's episodes and context
        """
        try:
            logger.info(f"🔍 Generating personalization context for user: {user_id}")
            
            # Get user's episodes
            episodes = await self.get_user_episodes(user_id, limit=10)
            
            context = {
                "user_id": user_id,
                "episodes": episodes,
                "has_data": len(episodes) > 0
            }
            
            logger.info(f"✅ Personalization context generated (has_data: {context['has_data']})")
            return context
            
        except Exception as e:
            logger.error(f"❌ Error generating personalization context: {str(e)}")
            return {
                "user_id": user_id,
                "episodes": [],
                "has_data": False
            }


# Singleton instance
falkor_personalization_service = FalkorPersonalizationService()

