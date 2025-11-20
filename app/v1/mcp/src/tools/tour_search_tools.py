"""
MCP Tools - Tour Package Search
Search tour packages using semantic vector search with embeddings
"""
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
import logging
import numpy as np
import os
from langchain_openai import OpenAIEmbeddings
from supabase import create_client, Client
from src.core.config import settings
from app.v1.mcp.src.schema import SearchTourPackagesInput
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Supabase connection - use settings or env vars
SUPABASE_URL = os.getenv("SUPABASE_URL") or settings.SUPABASE_URL
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or settings.SUPABASE_KEY


class TourPackageSearchService:
    """
    Service for vector-based semantic search of tour packages
    
    Features:
    - OpenAI embeddings (text-embedding-3-small)
    - Cosine similarity search
    - Price, duration, destination filters
    - Error handling and logging
    """
    
    def __init__(self):
        """Initialize tour package search service"""
        try:
            self.embeddings = OpenAIEmbeddings(
                api_key=settings.OPENAI_API_KEY,
                model="text-embedding-3-small"
            )
            logger.info("✅ OpenAI embeddings initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize embeddings: {e}")
            self.embeddings = None
        
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("✅ Supabase client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Supabase: {e}")
                self.supabase = None
        else:
            self.supabase = None
            logger.warning("⚠️ Supabase credentials not configured")
        
        logger.info("✅ TourPackageSearchService initialized")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector from text"""
        if not self.embeddings:
            raise ValueError("Embeddings not initialized")
        
        try:
            embedding = self.embeddings.embed_query(text)
            logger.debug(f"Generated embedding for query: {text[:50]}...")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def _search_tours_by_vector(
        self,
        query_embedding: List[float],
        filters: Optional[Dict] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Search tours using vector similarity (cosine similarity)"""
        if not self.supabase:
            logger.error("❌ Supabase not configured")
            return []
        
        try:
            logger.info(f"🔍 Starting vector search (limit: {limit})")
            
            # Get all embeddings from database
            all_embeddings = self.supabase.table("package_embeddings").select("package_id, embedding").execute()
            
            if not all_embeddings.data:
                logger.warning("No embeddings found in database")
                return []
            
            logger.info(f"📊 Found {len(all_embeddings.data)} package embeddings in database")
            
            # Calculate cosine similarity for each package
            results = []
            query_vec = np.array(query_embedding)
            
            for emb_data in all_embeddings.data:
                pkg_id = emb_data['package_id']
                pkg_emb_raw = emb_data['embedding']
                
                # Parse embedding
                try:
                    if isinstance(pkg_emb_raw, str):
                        pkg_emb = [float(x) for x in pkg_emb_raw.strip('[]').split(',')]
                    else:
                        pkg_emb = pkg_emb_raw
                    
                    # Calculate cosine similarity
                    pkg_vec = np.array(pkg_emb)
                    similarity = np.dot(query_vec, pkg_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(pkg_vec)
                    )
                    
                    # Only include if similarity > threshold
                    if similarity > 0.3:
                        # Get package details
                        pkg_result = self.supabase.table("tour_packages").select("*").eq("package_id", pkg_id).single().execute()
                        if pkg_result.data:
                            package = pkg_result.data.copy()
                            package['similarity_score'] = float(similarity)
                            results.append(package)
                except Exception as e:
                    logger.warning(f"⚠️ Error processing package {pkg_id}: {e}")
                    continue
            
            # Sort by similarity
            results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            results = results[:limit]
            
            logger.info(f"✅ Vector search found {len(results)} packages")
            
            # Note: Filters removed - return all semantic search results
            # Let the agent decide which packages are most relevant
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Vector search error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _apply_filters(self, tours: List[Dict], filters: Dict) -> List[Dict]:
        """Apply additional filters to search results"""
        filtered = tours.copy()
        
        if filters.get("max_price"):
            max_price = float(filters["max_price"])
            before = len(filtered)
            filtered = [t for t in filtered if t.get("price", 0) <= max_price]
            logger.debug(f"Price filter ({max_price}): {before} -> {len(filtered)}")
        
        if filters.get("duration"):
            duration = int(filters["duration"])
            before = len(filtered)
            filtered = [t for t in filtered if t.get("duration_days") == duration]
            logger.debug(f"Duration filter ({duration}): {before} -> {len(filtered)}")
        
        if filters.get("destination"):
            destination = filters["destination"].lower()
            before = len(filtered)
            filtered = [t for t in filtered if destination in t.get("destination", "").lower()]
            logger.debug(f"Destination filter ({destination}): {before} -> {len(filtered)}")
        
        return filtered
    
    async def search_tour_packages(
        self,
        user_message: str,
        filters: Optional[Dict] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search tour packages using semantic vector search
        
        Args:
            user_message: User query (e.g., "Tôi muốn đi Đà Lạt")
            filters: Optional filters (IGNORED - returns all semantic matches)
            limit: Number of results
            
        Returns:
            List of tour packages with similarity scores
        """
        try:
            logger.info(f"🔍 Search request: '{user_message[:100]}...' (limit: {limit})")
            
            # Generate embedding
            embedding = self._generate_embedding(user_message)
            
            # Vector search (filters ignored, return pure semantic results)
            results = self._search_tours_by_vector(embedding, filters=None, limit=limit)
            
            logger.info(f"✅ Search completed: {len(results)} packages found")
            return results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []


# Singleton instance
tour_package_search_service = TourPackageSearchService()


from pydantic import ValidationError

def register_tour_search_tools(mcp: FastMCP):
    """Register tour package search tools for multi-agent system"""
    
    @mcp.tool()
    async def search_tour_packages(
        user_message: str,
        max_price: Optional[float] = None,
        duration: Optional[int] = None,
        destination: Optional[str] = None,
        limit: int = 2
    ) -> Dict[str, Any]:
        """
        Search for tour packages using semantic vector search.
        
        Uses OpenAI embeddings (text-embedding-3-small) with cosine similarity.
        NO FILTERS APPLIED - returns pure semantic matches for agent to decide.
        
        Returns:
            Dict with found count and list of tour packages with:
            - found (int): Number of packages found
            - packages (list): Tour dictionaries with package_id, package_name, destination,
              price, duration_days, similarity_score, available_slots, start_date, image_urls
        """
        try:
            # Validate inputs
            validated = SearchTourPackagesInput(
                user_message=user_message,
                max_price=max_price,
                duration=duration,
                destination=destination,
                limit=limit
            )
            
            logger.info(f"📞 MCP Tool Call: search_tour_packages")
            logger.info(f"   Query: {validated.user_message[:100]}")
            logger.info(f"   Filters: IGNORED (semantic search only)")
            logger.info(f"   Limit: {validated.limit}")
            
            # Search packages (no filters applied)
            packages = await tour_package_search_service.search_tour_packages(
                user_message=validated.user_message,
                filters=None,
                limit=validated.limit
            )
            
            result = {
                "found": len(packages),
                "packages": packages
            }
            
            logger.info(f"✅ search_tour_packages completed: {len(packages)} packages found")
            return result
            
        except ValidationError as e:
            return {
                "found": 0,
                "packages": [],
                "error": f"Input Validation Error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"❌ Error in search_tour_packages tool: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "found": 0,
                "packages": [],
                "error": str(e),
                "message": f"Error searching tour packages: {str(e)}"
            }
    
    logger.info("✅ Tour search tools registered")


