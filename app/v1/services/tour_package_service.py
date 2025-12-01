"""
Tour Package Service
Handles CRUD operations for tour packages
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID
from supabase import Client
import openai
import os

# Import search service from MCP tools
try:
    from ..mcp.src.tools.tour_search_tools import tour_package_search_service
except ImportError:
    tour_package_search_service = None
    logging.warning("TourPackageSearchService not available - search functionality disabled")

# Import mem0 client for user preferences
try:
    from ..core.mem0_client import mem0_client
except ImportError:
    mem0_client = None
    logging.warning("Mem0 client not available - personalization disabled")

logger = logging.getLogger(__name__)


class TourPackageService:
    """Service for tour package management"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize TourPackageService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        # Initialize OpenAI client for embeddings
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            openai.api_key = openai_api_key
        # Use text-embedding-3-small for 1536 dimensions (matches database schema)
        self.embedding_model = "text-embedding-3-small"
    
    async def _generate_embedding(self, package_data: Dict[str, Any]) -> Optional[List[float]]:
        """
        Generate embedding for tour package using OpenAI
        
        Args:
            package_data: Tour package data
            
        Returns:
            List of floats representing the embedding, or None if failed
        """
        try:
            # Combine relevant fields for embedding
            text_parts = [
                package_data.get("package_name", ""),
                package_data.get("destination", ""),
                package_data.get("description", ""),
                package_data.get("cuisine", ""),
                package_data.get("suitable_for", "")
            ]
            
            text_to_embed = " ".join([str(part) for part in text_parts if part])
            
            logger.info(f"Generating embedding for: '{text_to_embed[:100]}...' using model {self.embedding_model}")
            
            # Generate embedding using text-embedding-3-small (1536 dimensions)
            response = openai.embeddings.create(
                model=self.embedding_model,
                input=text_to_embed
            )
            
            embedding = response.data[0].embedding
            logger.info(f"✓ Generated embedding (dimension: {len(embedding)}) for package: {package_data.get('package_name', 'Unknown')}")
            return embedding
            
        except Exception as e:
            logger.error(f"✗ Error generating embedding: {str(e)}", exc_info=True)
            return None
    
    async def _upsert_embedding(self, package_id: str, embedding: List[float]) -> bool:
        """
        Upsert embedding to package_embeddings table
        
        Args:
            package_id: UUID of the package
            embedding: Embedding vector
            
        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            embedding_data = {
                "package_id": package_id,
                "embedding": embedding,
                "created_at": now
            }
            
            logger.info(f"Upserting embedding for package {package_id} (vector dimension: {len(embedding)})")
            
            # Upsert (insert or update)
            result = self.supabase.table('package_embeddings') \
                .upsert(embedding_data) \
                .execute()
            
            if result.data:
                logger.info(f"✓ Successfully upserted embedding for package {package_id}")
                return True
            else:
                logger.warning(f"⚠ Upsert returned no data for package {package_id}")
                return False
            
        except Exception as e:
            logger.error(f"✗ Error upserting embedding for package {package_id}: {str(e)}", exc_info=True)
            return False
    
    async def _delete_embedding(self, package_id: str) -> bool:
        """
        Delete embedding from package_embeddings table
        
        Args:
            package_id: UUID of the package
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.supabase.table('package_embeddings') \
                .delete() \
                .eq('package_id', package_id) \
                .execute()
            
            logger.info(f"Successfully deleted embedding for package {package_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting embedding for package {package_id}: {str(e)}")
            return False
    
    async def get_all_packages(
        self, 
        is_active: Optional[bool] = None,
        destination: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all tour packages with optional filters
        
        Args:
            is_active: Filter by active status
            destination: Filter by destination
            limit: Number of records to return
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, total, and packages list
        """
        try:
            query = self.supabase.table('tour_packages').select('*')
            
            # Apply filters
            if is_active is not None:
                query = query.eq('is_active', is_active)
            
            if destination:
                query = query.ilike('destination', f'%{destination}%')
            
            # Order by created_at descending
            query = query.order('created_at', desc=True)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            result = query.execute()
            
            return {
                "EC": 0,
                "EM": "Successfully retrieved tour packages",
                "total": len(result.data),
                "packages": result.data
            }
            
        except Exception as e:
            logger.error(f"Error getting tour packages: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving tour packages: {str(e)}",
                "total": 0,
                "packages": []
            }
    
    async def get_package_by_id(self, package_id: str) -> Dict[str, Any]:
        """
        Get a single tour package by ID
        
        Args:
            package_id: UUID of the tour package
            
        Returns:
            Dict with EC, EM, and package data
        """
        try:
            result = self.supabase.table('tour_packages') \
                .select('*') \
                .eq('package_id', package_id) \
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Tour package not found",
                    "package": None
                }
            
            return {
                "EC": 0,
                "EM": "Successfully retrieved tour package",
                "package": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting tour package {package_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving tour package: {str(e)}",
                "package": None
            }
    
    async def create_package(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new tour package and generate embedding
        
        Args:
            package_data: Dictionary containing tour package data
            
        Returns:
            Dict with EC, EM, and created package
        """
        try:
            # Add timestamps
            now = datetime.now(timezone.utc).isoformat()
            package_data['created_at'] = now
            package_data['updated_at'] = now
            
            result = self.supabase.table('tour_packages') \
                .insert(package_data) \
                .execute()
            
            if result.data:
                created_package = result.data[0]
                package_id = created_package.get("package_id")
                
                logger.info(f"Tour package created with ID: {package_id}. Starting embedding generation...")
                
                # Generate and store embedding
                try:
                    embedding = await self._generate_embedding(created_package)
                    if embedding:
                        success = await self._upsert_embedding(package_id, embedding)
                        if success:
                            logger.info(f"✓ Embedding successfully created for package {package_id}")
                        else:
                            logger.error(f"✗ Failed to upsert embedding for package {package_id}")
                    else:
                        logger.warning(f"⚠ Failed to generate embedding for package {package_id}")
                except Exception as embed_error:
                    logger.error(f"✗ Exception during embedding process for package {package_id}: {str(embed_error)}")
                
                return {
                    "EC": 0,
                    "EM": "Tour package created successfully",
                    "package": created_package
                }
            else:
                return {
                    "EC": 1,
                    "EM": "Failed to create tour package",
                    "package": None
                }
                
        except Exception as e:
            logger.error(f"Error creating tour package: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error creating tour package: {str(e)}",
                "package": None
            }
    
    async def update_package(
        self, 
        package_id: str, 
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing tour package and regenerate embedding
        
        Args:
            package_id: UUID of the tour package to update
            update_data: Dictionary containing fields to update
            
        Returns:
            Dict with EC, EM, and updated package
        """
        try:
            # Check if package exists
            existing = await self.get_package_by_id(package_id)
            if existing["EC"] != 0:
                return existing
            
            # Remove None values from update_data
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            if not update_data:
                return {
                    "EC": 1,
                    "EM": "No fields to update",
                    "package": None
                }
            
            # Add updated timestamp
            update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            result = self.supabase.table('tour_packages') \
                .update(update_data) \
                .eq('package_id', package_id) \
                .execute()
            
            if result.data:
                updated_package = result.data[0]
                
                # Regenerate embedding if content fields were updated
                content_fields = ['package_name', 'destination', 'description', 'cuisine', 'suitable_for']
                if any(field in update_data for field in content_fields):
                    embedding = await self._generate_embedding(updated_package)
                    if embedding:
                        await self._upsert_embedding(package_id, embedding)
                    else:
                        logger.warning(f"Failed to regenerate embedding for package {package_id}")
                
                return {
                    "EC": 0,
                    "EM": "Tour package updated successfully",
                    "package": updated_package
                }
            else:
                return {
                    "EC": 2,
                    "EM": "Failed to update tour package",
                    "package": None
                }
                
        except Exception as e:
            logger.error(f"Error updating tour package {package_id}: {str(e)}")
            return {
                "EC": 3,
                "EM": f"Error updating tour package: {str(e)}",
                "package": None
            }
    
    async def delete_package(self, package_id: str) -> Dict[str, Any]:
        """
        Delete a tour package and its embedding
        
        Args:
            package_id: UUID of the tour package to delete
            
        Returns:
            Dict with EC and EM
        """
        try:
            # Check if package exists
            existing = await self.get_package_by_id(package_id)
            if existing["EC"] != 0:
                return {
                    "EC": existing["EC"],
                    "EM": existing["EM"]
                }
            
            # Delete embedding first (if exists)
            await self._delete_embedding(package_id)
            
            # Delete tour package
            result = self.supabase.table('tour_packages') \
                .delete() \
                .eq('package_id', package_id) \
                .execute()
            
            return {
                "EC": 0,
                "EM": "Tour package deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting tour package {package_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error deleting tour package: {str(e)}"
            }
    
    async def create_packages_bulk(self, packages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple tour packages from bulk data
        
        Args:
            packages_data: List of dictionaries containing tour package data
            
        Returns:
            Dict with EC, EM, statistics and results
        """
        try:
            created_packages = []
            errors = []
            
            for idx, package_data in enumerate(packages_data, start=1):
                try:
                    # Add timestamps
                    now = datetime.now(timezone.utc).isoformat()
                    package_data['created_at'] = now
                    package_data['updated_at'] = now
                    
                    # Insert package
                    result = self.supabase.table('tour_packages') \
                        .insert(package_data) \
                        .execute()
                    
                    if result.data:
                        created_package = result.data[0]
                        package_id = created_package.get("package_id")
                        
                        # Generate and store embedding
                        try:
                            embedding = await self._generate_embedding(created_package)
                            if embedding:
                                await self._upsert_embedding(package_id, embedding)
                                logger.info(f"✓ Package {idx}: Created with embedding - {created_package.get('package_name')}")
                            else:
                                logger.warning(f"⚠ Package {idx}: Created without embedding - {created_package.get('package_name')}")
                        except Exception as embed_error:
                            logger.error(f"✗ Package {idx}: Embedding error - {str(embed_error)}")
                        
                        created_packages.append(created_package)
                    else:
                        error_msg = f"Package {idx}: Failed to insert - {package_data.get('package_name', 'Unknown')}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                except Exception as e:
                    error_msg = f"Package {idx}: {str(e)} - {package_data.get('package_name', 'Unknown')}"
                    errors.append(error_msg)
                    logger.error(f"Error creating package {idx}: {str(e)}")
            
            total_processed = len(packages_data)
            successful = len(created_packages)
            failed = len(errors)
            
            return {
                "EC": 0 if failed == 0 else 1,
                "EM": f"Processed {total_processed} packages: {successful} successful, {failed} failed",
                "total_processed": total_processed,
                "successful": successful,
                "failed": failed,
                "created_packages": created_packages,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error in bulk package creation: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error in bulk creation: {str(e)}",
                "total_processed": len(packages_data),
                "successful": 0,
                "failed": len(packages_data),
                "created_packages": [],
                "errors": [str(e)]
    async def search_packages(
        self,
        user_message: str,
        max_price: Optional[float] = None,
        duration: Optional[int] = None,
        destination: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search tour packages using hybrid search (semantic + keyword + filters)
        
        Args:
            user_message: User query (e.g., "Tôi muốn đi Đà Lạt")
            max_price: Maximum price filter
            duration: Duration filter in days
            destination: Destination filter
            limit: Number of results
            
        Returns:
            Dict with EC, EM, found, and packages list
        """
        try:
            if not tour_package_search_service:
                return {
                    "EC": 1,
                    "EM": "Search service not available",
                    "found": 0,
                    "packages": []
                }
            
            # Build filters dict
            filters = {}
            if max_price is not None:
                filters["max_price"] = max_price
            if duration is not None:
                filters["duration"] = duration
            if destination:
                filters["destination"] = destination
            
            # Call search service
            packages = await tour_package_search_service.search_tour_packages(
                user_message=user_message,
                filters=filters if filters else None,
                limit=limit
            )
            
            # Filter out description from packages (keep other fields)
            filtered_packages = []
            for pkg in packages:
                pkg_copy = {k: v for k, v in pkg.items() if k != 'description'}
                filtered_packages.append(pkg_copy)
            
            return {
                "EC": 0,
                "EM": "Successfully searched tour packages",
                "found": len(filtered_packages),
                "packages": filtered_packages
            }
            
        except Exception as e:
            logger.error(f"Error searching tour packages: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error searching tour packages: {str(e)}",
                "found": 0,
                "packages": []
            }
    
    async def recommend_packages(
        self,
        user_id: str,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Recommend tour packages dựa trên tour gần hết hạn và đặc điểm user từ Mem0
        
        Logic:
        1. Tìm 10 tour gần hết hạn nhất (end_date gần nhất, is_active=True, available_slots > 0)
        2. Lấy đặc điểm user từ Mem0 (preferences, lịch sử tìm kiếm)
        3. Dùng hybrid search để tìm k tour phù hợp nhất từ 10 tour gần hết hạn
        
        Args:
            user_id: User ID để lấy đặc điểm từ Mem0
            k: Số lượng tour được recommend (1-10)
            
        Returns:
            Dict with EC, EM, found, and packages list
        """
        try:
            from datetime import datetime, timezone
            
            # Step 1: Tìm 10 tour gần hết hạn nhất
            now = datetime.now(timezone.utc).isoformat()
            
            # Query tours: is_active=True, available_slots > 0, end_date >= now, order by end_date ASC
            query = self.supabase.table('tour_packages').select('*')
            query = query.eq('is_active', True)
            query = query.gt('available_slots', 0)
            query = query.gte('end_date', now)  # Chỉ lấy tour chưa hết hạn
            query = query.order('end_date', desc=False)  # Sắp xếp theo end_date tăng dần (gần hết hạn nhất trước)
            query = query.limit(10)
            
            result = query.execute()
            expiring_tours = result.data if result.data else []
            
            if not expiring_tours:
                return {
                    "EC": 0,
                    "EM": "No expiring tours available",
                    "found": 0,
                    "packages": []
                }
            
            # Step 2: Lấy đặc điểm user từ Mem0
            user_preferences = ""
            if mem0_client and mem0_client.is_available:
                try:
                    logger.info(f"📚 Fetching user preferences from Mem0 for user {user_id}")
                    # Search mem0 for user preferences about tours, travel, destinations
                    memories = mem0_client.search(
                        query="tour travel destination preferences budget duration",
                        user_id=user_id,
                        limit=5
                    )
                    
                    if memories:
                        # Extract preferences from memories
                        preference_texts = []
                        for mem in memories:
                            content = mem.get('memory', '') or mem.get('content', '') or mem.get('text', '')
                            if content:
                                preference_texts.append(content)  # Limit length
                        
                        if preference_texts:
                            user_preferences = ". ".join(preference_texts)
                except Exception as e:
                    logger.warning(f"⚠️ Error fetching user preferences from Mem0: {str(e)}")
                    user_preferences = ""
            else:
                logger.info("Mem0 client not available, skipping personalization")
            
            # Step 3: Dùng search tool để tìm k tour phù hợp từ 10 tour gần hết hạn
            if not tour_package_search_service:
                # Fallback: return expiring tours directly
                logger.warning("Search service not available, returning expiring tours directly")
                return {
                    "EC": 0,
                    "EM": "Successfully retrieved expiring tours",
                    "found": min(k, len(expiring_tours)),
                    "packages": expiring_tours[:k]
                }
            
            # Build search query từ user preferences
            if user_preferences:
                search_query = f"Dựa trên sở thích: {user_preferences}. Tìm tour phù hợp"
            else:
                search_query = "Tìm tour du lịch phù hợp"
            
            logger.info(f"🔍 Searching for {k} recommended tours from {len(expiring_tours)} expiring tours")
            
            # Get package IDs from expiring tours
            expiring_package_ids = [str(tour.get('package_id', '')) for tour in expiring_tours if tour.get('package_id')]
            
            # Search với search service - nhưng cần filter để chỉ lấy từ expiring tours
            # Vì search service không hỗ trợ filter by package_ids trực tiếp,
            # ta sẽ search và filter kết quả sau
            all_packages = await tour_package_search_service.search_tour_packages(
                user_message=search_query,
                filters=None,
                limit=20  # Get more to filter
            )
            
            # Filter để chỉ lấy packages trong expiring_tours
            recommended_packages = []
            expiring_ids_set = set(expiring_package_ids)
            
            # Tạo map từ package_id -> tour data để merge scores với tour data
            expiring_tours_map = {str(tour.get('package_id', '')): tour for tour in expiring_tours}
            
            for pkg in all_packages:
                pkg_id = str(pkg.get('package_id', ''))
                if pkg_id in expiring_ids_set:
                    # Merge search result với tour data từ expiring_tours
                    tour_data = expiring_tours_map.get(pkg_id, {})
                    # Keep search scores but ensure all tour fields are present
                    merged_pkg = {**tour_data, **pkg}
                    recommended_packages.append(merged_pkg)
                    if len(recommended_packages) >= k:
                        break
            
            # Nếu không đủ k tour từ search, thêm từ expiring_tours (theo thứ tự gần hết hạn)
            if len(recommended_packages) < k:
                recommended_ids = {str(p.get('package_id', '')) for p in recommended_packages}
                for tour in expiring_tours:
                    tour_id = str(tour.get('package_id', ''))
                    if tour_id not in recommended_ids:
                        # Add default scores
                        tour_copy = tour.copy()
                        tour_copy['final_score'] = 0.5
                        tour_copy['semantic_score'] = 0.5
                        tour_copy['keyword_score'] = 0.0
                        recommended_packages.append(tour_copy)
                        if len(recommended_packages) >= k:
                            break
            
            # Sort by final_score if available, then by end_date
            recommended_packages.sort(
                key=lambda x: (x.get('final_score', 0), x.get('end_date', '')),
                reverse=True
            )
            recommended_packages = recommended_packages[:k]
            
            # Filter out description from packages (keep other fields)
            filtered_packages = []
            for pkg in recommended_packages:
                pkg_copy = {k: v for k, v in pkg.items() if k != 'description'}
                filtered_packages.append(pkg_copy)
            
            logger.info(f"✅ Recommended {len(filtered_packages)} tours for user {user_id}")
            
            return {
                "EC": 0,
                "EM": "Successfully recommended tour packages",
                "found": len(filtered_packages),
                "packages": filtered_packages
            }
            
        except Exception as e:
            logger.error(f"Error recommending tour packages: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "EC": 1,
                "EM": f"Error recommending tour packages: {str(e)}",
                "found": 0,
                "packages": []
            }
