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
    Service for hybrid search of tour packages
    
    Features:
    - Hybrid search: Semantic (pgvector) + Keyword (full-text) + Filters
    - OpenAI embeddings (text-embedding-3-small)
    - Supabase native pgvector search (uses ivfflat index)
    - PostgreSQL full-text search on package_name, destination, description
    - Database-level filters for performance
    - Weighted scoring: 0.7 semantic + 0.3 keyword
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
    
    def _search_tours_by_vector_native(
        self,
        query_embedding: List[float],
        filters: Optional[Dict] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search tours using Supabase native pgvector search (uses ivfflat index)
        
        Uses pgvector <=> operator for cosine distance, much faster than Python loop
        """
        if not self.supabase:
            logger.error("❌ Supabase not configured")
            return []
        
        try:
            logger.info(f"🔍 Starting native vector search (limit: {limit})")
            
            # Build base query with filters applied at database level
            base_query = self.supabase.table("tour_packages").select("*")
            
            # Apply filters at database level
            if filters:
                base_query = self._apply_database_filters(base_query, filters)
            
            # Use RPC call to match_packages function (uses pgvector <=> operator)
            # This is much faster than loading all embeddings into Python
            try:
                # Convert embedding to PostgreSQL vector format: '[1,2,3]' as string
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                
                # Call the match_packages function via RPC
                # Note: Supabase RPC expects vector as string representation
                rpc_result = self.supabase.rpc(
                    'match_packages',
                    {
                        'query_embedding': embedding_str,
                        'match_threshold': 0.3,
                        'match_count': limit * 3  # Get more to account for filters
                    }
                ).execute()
                
                if rpc_result.data:
                    # Get package_ids from RPC result
                    matched_package_ids = [item['package_id'] for item in rpc_result.data]
                    
                    # Fetch full package details for matched IDs
                    # Apply filters again if needed (some filters might not be in RPC)
                    query = base_query.in_('package_id', matched_package_ids)
                    result = query.execute()
                    
                    if result.data:
                        # Map similarity scores from RPC result
                        similarity_map = {item['package_id']: item.get('similarity', 0.0) 
                                       for item in rpc_result.data}
                        
                        packages = []
                        for pkg in result.data:
                            pkg_id = pkg.get('package_id')
                            if pkg_id in similarity_map:
                                pkg['similarity_score'] = similarity_map[pkg_id]
                                packages.append(pkg)
                        
                        # Sort by similarity and limit
                        packages.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
                        packages = packages[:limit]
                        
                        logger.info(f"✅ Native vector search found {len(packages)} packages")
                        return packages
            except Exception as rpc_error:
                logger.warning(f"⚠️ RPC match_packages failed, falling back to direct query: {rpc_error}")
                # Fallback: Use direct SQL query if RPC not available
                # This requires raw SQL execution which Supabase Python client doesn't support well
                # So we'll use a workaround: get filtered packages first, then calculate similarity
                pass
            
            # Fallback: Get filtered packages and calculate similarity in Python (slower but works)
            logger.info("⚠️ Using fallback vector search (slower)")
            filtered_result = base_query.execute()
            
            if not filtered_result.data:
                logger.info("No packages match filters")
                return []
            
            # Get embeddings for filtered packages
            package_ids = [pkg['package_id'] for pkg in filtered_result.data]
            embeddings_result = self.supabase.table("package_embeddings").select("package_id, embedding").in_("package_id", package_ids).execute()
            
            if not embeddings_result.data:
                logger.warning("No embeddings found for filtered packages")
                return []
            
            # Calculate similarity for filtered packages
            results = []
            query_vec = np.array(query_embedding)
            
            embedding_map = {}
            for emb_data in embeddings_result.data:
                pkg_id = emb_data['package_id']
                pkg_emb_raw = emb_data['embedding']
                try:
                    if isinstance(pkg_emb_raw, str):
                        pkg_emb = [float(x) for x in pkg_emb_raw.strip('[]').split(',')]
                    else:
                        pkg_emb = pkg_emb_raw
                    embedding_map[pkg_id] = np.array(pkg_emb)
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing embedding for {pkg_id}: {e}")
                    continue
            
            # Calculate similarity and combine with package data
            for pkg in filtered_result.data:
                pkg_id = pkg.get('package_id')
                if pkg_id in embedding_map:
                    pkg_vec = embedding_map[pkg_id]
                    similarity = np.dot(query_vec, pkg_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(pkg_vec)
                    )
                    if similarity > 0.3:
                        pkg_copy = pkg.copy()
                        pkg_copy['similarity_score'] = float(similarity)
                        results.append(pkg_copy)
            
            # Sort by similarity
            results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            results = results[:limit]
            
            logger.info(f"✅ Fallback vector search found {len(results)} packages")
            return results
            
        except Exception as e:
            logger.error(f"❌ Vector search error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _search_tours_by_keyword(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search tours using PostgreSQL full-text search on package_name, destination, description
        
        Uses tsvector and tsquery for efficient keyword matching
        """
        if not self.supabase:
            logger.error("❌ Supabase not configured")
            return []
        
        try:
            logger.info(f"🔍 Starting keyword search: '{query[:50]}...' (limit: {limit})")
            
            # Build base query
            base_query = self.supabase.table("tour_packages").select("*")
            
            # Apply filters at database level
            if filters:
                base_query = self._apply_database_filters(base_query, filters)
            
            # Add active filter
            base_query = base_query.eq("is_active", True)
            
            # Try to use full-text search if search_vector column exists
            # Otherwise, use LIKE queries as fallback
            try:
                query_lower = query.lower()
                
                # Search in package_name, destination, description using multiple queries
                # Supabase doesn't support complex OR in single query, so we'll search each field
                results_by_field = []
                
                # Search package_name (highest priority)
                try:
                    name_results = base_query.ilike('package_name', f'%{query}%').limit(limit * 2).execute()
                    if name_results.data:
                        results_by_field.extend(name_results.data)
                except:
                    pass
                
                # Search destination
                try:
                    dest_results = base_query.ilike('destination', f'%{query}%').limit(limit * 2).execute()
                    if dest_results.data:
                        results_by_field.extend(dest_results.data)
                except:
                    pass
                
                # Search description
                try:
                    desc_results = base_query.ilike('description', f'%{query}%').limit(limit * 2).execute()
                    if desc_results.data:
                        results_by_field.extend(desc_results.data)
                except:
                    pass
                
                # Deduplicate by package_id
                seen_ids = set()
                unique_results = []
                for pkg in results_by_field:
                    pkg_id = pkg.get('package_id')
                    if pkg_id and pkg_id not in seen_ids:
                        seen_ids.add(pkg_id)
                        unique_results.append(pkg)
                
                if unique_results:
                    # Calculate keyword scores based on match position and field
                    scored_packages = []
                    for pkg in unique_results:
                        score = 0.0
                        pkg_name = (pkg.get('package_name') or '').lower()
                        destination = (pkg.get('destination') or '').lower()
                        description = (pkg.get('description') or '').lower()
                        
                        # Higher weight for exact matches and name matches
                        if query_lower in pkg_name:
                            if pkg_name.startswith(query_lower):
                                score += 1.0  # Starts with query
                            else:
                                score += 0.8  # Contains query
                        
                        if query_lower in destination:
                            if destination.startswith(query_lower):
                                score += 0.6
                            else:
                                score += 0.4
                        
                        if query_lower in description:
                            score += 0.2
                        
                        if score > 0:
                            pkg_copy = pkg.copy()
                            pkg_copy['keyword_score'] = score
                            scored_packages.append(pkg_copy)
                    
                    # Sort by keyword score
                    scored_packages.sort(key=lambda x: x.get('keyword_score', 0), reverse=True)
                    scored_packages = scored_packages[:limit]
                    
                    logger.info(f"✅ Keyword search found {len(scored_packages)} packages")
                    return scored_packages
                else:
                    logger.info("No packages found in keyword search")
                    return []
                    
            except Exception as e:
                logger.warning(f"⚠️ Keyword search error: {e}")
                # Fallback: simple LIKE search
                try:
                    result = (
                        base_query
                        .ilike('package_name', f'%{query}%')
                        .limit(limit)
                        .execute()
                    )
                    if result.data:
                        for pkg in result.data:
                            pkg['keyword_score'] = 0.5  # Default score
                        logger.info(f"✅ Fallback keyword search found {len(result.data)} packages")
                        return result.data
                except:
                    pass
                return []
            
        except Exception as e:
            logger.error(f"❌ Keyword search error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _apply_database_filters(self, query, filters: Dict):
        """
        Apply filters at database level for better performance
        
        Returns modified query builder
        """
        if not filters:
            return query
        
        if filters.get("max_price"):
            max_price = float(filters["max_price"])
            query = query.lte("price", max_price)
        
        if filters.get("min_price"):
            min_price = float(filters["min_price"])
            query = query.gte("price", min_price)
        
        if filters.get("duration"):
            duration = int(filters["duration"])
            query = query.eq("duration_days", duration)
        
        if filters.get("destination"):
            destination = filters["destination"]
            # Use ILIKE for case-insensitive partial match
            query = query.ilike("destination", f"%{destination}%")
        
        # Always filter active packages
        query = query.eq("is_active", True)
        
        # Filter available slots > 0
        query = query.gt("available_slots", 0)
        
        return query
    
    def _combine_search_results(
        self,
        semantic_results: List[Dict],
        keyword_results: List[Dict],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        limit: int = 10
    ) -> List[Dict]:
        """
        Combine semantic and keyword search results with weighted scoring
        
        Args:
            semantic_results: Results from vector search with similarity_score
            keyword_results: Results from keyword search with keyword_score
            semantic_weight: Weight for semantic score (default 0.7)
            keyword_weight: Weight for keyword score (default 0.3)
            limit: Maximum number of results to return
            
        Returns:
            Combined and deduplicated results sorted by final_score
        """
        # Normalize scores to 0-1 range if needed
        def normalize_score(score: float, max_score: float) -> float:
            if max_score == 0:
                return 0.0
            return min(1.0, score / max_score)
        
        # Find max scores for normalization
        max_semantic = max([r.get('similarity_score', 0) for r in semantic_results], default=1.0)
        max_keyword = max([r.get('keyword_score', 0) for r in keyword_results], default=1.0)
        
        # Create a map of package_id -> best result
        combined_map = {}
        
        # Add semantic results
        for pkg in semantic_results:
            pkg_id = pkg.get('package_id')
            if not pkg_id:
                continue
            
            normalized_semantic = normalize_score(pkg.get('similarity_score', 0), max_semantic)
            final_score = normalized_semantic * semantic_weight
            
            if pkg_id not in combined_map:
                pkg_copy = pkg.copy()
                pkg_copy['final_score'] = final_score
                pkg_copy['semantic_score'] = normalized_semantic
                pkg_copy['keyword_score'] = 0.0
                combined_map[pkg_id] = pkg_copy
            else:
                # Update if this semantic score is better
                existing = combined_map[pkg_id]
                if normalized_semantic > existing.get('semantic_score', 0):
                    existing['semantic_score'] = normalized_semantic
                    existing['final_score'] = normalized_semantic * semantic_weight + existing.get('keyword_score', 0) * keyword_weight
        
        # Add keyword results
        for pkg in keyword_results:
            pkg_id = pkg.get('package_id')
            if not pkg_id:
                continue
            
            normalized_keyword = normalize_score(pkg.get('keyword_score', 0), max_keyword)
            
            if pkg_id not in combined_map:
                pkg_copy = pkg.copy()
                pkg_copy['final_score'] = normalized_keyword * keyword_weight
                pkg_copy['semantic_score'] = 0.0
                pkg_copy['keyword_score'] = normalized_keyword
                combined_map[pkg_id] = pkg_copy
            else:
                # Add keyword score to existing result
                existing = combined_map[pkg_id]
                existing['keyword_score'] = normalized_keyword
                existing['final_score'] = (
                    existing.get('semantic_score', 0) * semantic_weight +
                    normalized_keyword * keyword_weight
                )
        
        # Convert to list and sort by final_score
        combined_results = list(combined_map.values())
        combined_results.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        # Limit results
        combined_results = combined_results[:limit]
        
        logger.info(f"✅ Combined {len(semantic_results)} semantic + {len(keyword_results)} keyword = {len(combined_results)} unique results")
        
        return combined_results
    
    def _apply_filters(self, tours: List[Dict], filters: Dict) -> List[Dict]:
        """
        Apply additional filters to search results (fallback for post-processing)
        
        Note: Prefer _apply_database_filters() for better performance
        """
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
        Hybrid search: Combines semantic vector search + keyword search + filters
        
        Args:
            user_message: User query (e.g., "Tôi muốn đi Đà Lạt")
            filters: Optional filters (price, duration, destination) - applied at DB level
            limit: Number of results
            
        Returns:
            List of tour packages with final_score (weighted combination of semantic + keyword)
        """
        try:
            logger.info(f"🔍 Hybrid search request: '{user_message[:100]}...' (limit: {limit})")
            
            # Step 1: Generate embedding for semantic search
            embedding = self._generate_embedding(user_message)
            
            # Step 2: Run semantic search (native pgvector)
            semantic_results = self._search_tours_by_vector_native(
                query_embedding=embedding,
                filters=filters,
                limit=limit * 2  # Get more for combination
            )
            
            # Step 3: Run keyword search (full-text)
            keyword_results = self._search_tours_by_keyword(
                query=user_message,
                filters=filters,
                limit=limit * 2  # Get more for combination
            )
            
            # Step 4: Combine results with weighted scoring
            # Weight: 0.7 semantic + 0.3 keyword
            combined_results = self._combine_search_results(
                semantic_results=semantic_results,
                keyword_results=keyword_results,
                semantic_weight=0.7,
                keyword_weight=0.3,
                limit=limit
            )
            
            # Step 5: Ensure filters are applied (double-check, though they should be applied at DB level)
            if filters and combined_results:
                # This is a safety check - filters should already be applied at DB level
                filtered_results = self._apply_filters(combined_results, filters)
                if len(filtered_results) < len(combined_results):
                    logger.debug(f"Post-filtering: {len(combined_results)} -> {len(filtered_results)}")
                combined_results = filtered_results
            
            logger.info(f"✅ Hybrid search completed: {len(combined_results)} packages found")
            logger.info(f"   - Semantic: {len(semantic_results)}, Keyword: {len(keyword_results)}, Combined: {len(combined_results)}")
            
            return combined_results
            
        except Exception as e:
            logger.error(f"❌ Hybrid search failed: {str(e)}")
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
        Search for tour packages using hybrid search (semantic + keyword + filters).
        
        Uses:
        - Semantic search: Supabase native pgvector search (text-embedding-3-small)
        - Keyword search: PostgreSQL full-text search on package_name, destination, description
        - Filters: Database-level filters for price, duration, destination
        - Scoring: Weighted combination (0.7 semantic + 0.3 keyword)
        
        Returns:
            Dict with found count and list of tour packages with:
            - found (int): Number of packages found
            - packages (list): Tour dictionaries with package_id, package_name, destination,
              price, duration_days, final_score, semantic_score, keyword_score, 
              available_slots, start_date, image_urls
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
            
            # Build filters dict
            search_filters = {}
            if validated.max_price:
                search_filters["max_price"] = validated.max_price
            if validated.duration:
                search_filters["duration"] = validated.duration
            if validated.destination:
                search_filters["destination"] = validated.destination
            
            logger.info(f"   Filters: {search_filters if search_filters else 'None'}")
            logger.info(f"   Limit: {validated.limit}")
            
            # Hybrid search: semantic + keyword + filters
            packages = await tour_package_search_service.search_tour_packages(
                user_message=validated.user_message,
                filters=search_filters if search_filters else None,
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


