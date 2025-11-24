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
