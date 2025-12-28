"""
Tour Package Service
Handles CRUD operations for tour packages
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, date
from uuid import UUID
from supabase import Client
import openai
import os
from fastapi import UploadFile

# Import Cloudinary config
from ..core.cloudinary_config import CloudinaryConfig

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

# Import admin services
from .admin_settings_service import AdminSettingsService
from .admin_featured_tours_service import AdminFeaturedToursService
from .notification_service import NotificationService
from .favorite_service import FavoriteTourService

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
        
        # Initialize admin services
        self.admin_settings = AdminSettingsService(supabase_client)
        self.admin_featured_tours = AdminFeaturedToursService(supabase_client)
        self.notification_service = NotificationService(supabase_client)
        self.favorite_service = FavoriteTourService(supabase_client)
    
    async def _add_favorite_status(
        self,
        packages: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Add is_favorite field to each package in the list
        
        Args:
            packages: List of tour package dictionaries
            user_id: Optional user ID to check favorite status
            
        Returns:
            List of packages with is_favorite field added
        """
        if not packages:
            return packages
        
        # If no user_id, set all to False
        if not user_id:
            for pkg in packages:
                pkg['is_favorite'] = False
            return packages
        
        # Batch check favorites for efficiency
        package_ids = [str(pkg.get('package_id', '')) for pkg in packages if pkg.get('package_id')]
        
        if not package_ids:
            # No valid package IDs, set all to False
            for pkg in packages:
                pkg['is_favorite'] = False
            return packages
        
        # Get all favorites for this user
        try:
            favorites_result = self.supabase.table('favorite_tours') \
                .select('package_id') \
                .eq('user_id', user_id) \
                .in_('package_id', package_ids) \
                .execute()
            
            # Create set of favorited package IDs
            favorited_ids = {str(fav['package_id']) for fav in favorites_result.data}
            
            # Add is_favorite to each package
            for pkg in packages:
                pkg_id = str(pkg.get('package_id', ''))
                pkg['is_favorite'] = pkg_id in favorited_ids
                
        except Exception as e:
            logger.warning(f"Error checking favorite status: {str(e)}, setting all to False")
            for pkg in packages:
                pkg['is_favorite'] = False
        
        return packages
    
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
    
    async def upload_images(self, images: List[UploadFile]) -> List[str]:
        """
        Upload multiple images to Cloudinary
        
        Args:
            images: List of UploadFile objects
            
        Returns:
            List of uploaded image URLs
        """
        try:
            files_data = []
            
            for image in images:
                # Read file content
                content = await image.read()
                # Reset file pointer
                await image.seek(0)
                
                files_data.append((content, image.filename))
            
            # Upload to Cloudinary
            urls = CloudinaryConfig.upload_multiple_images(files_data, folder="tour_packages")
            
            logger.info(f"✓ Uploaded {len(urls)} images to Cloudinary")
            return urls
            
        except Exception as e:
            logger.error(f"✗ Error uploading images: {str(e)}")
            return []
    
    async def delete_images_from_urls(self, image_urls: str) -> int:
        """
        Delete images from Cloudinary using URLs
        
        Args:
            image_urls: Pipe-separated image URLs
            
        Returns:
            Number of successfully deleted images
        """
        try:
            if not image_urls:
                return 0
            
            urls = image_urls.split("|")
            public_ids = []
            
            for url in urls:
                public_id = CloudinaryConfig.extract_public_id_from_url(url.strip())
                if public_id:
                    public_ids.append(public_id)
            
            deleted_count = CloudinaryConfig.delete_multiple_images(public_ids)
            logger.info(f"✓ Deleted {deleted_count}/{len(public_ids)} images from Cloudinary")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"✗ Error deleting images: {str(e)}")
            return 0
    
    async def get_all_packages(
        self, 
        is_active: Optional[bool] = None,
        destination: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all tour packages with optional filters
        
        Args:
            is_active: Filter by active status
            destination: Filter by destination
            limit: Number of records to return
            offset: Number of records to skip
            user_id: Optional user ID to check favorite status
            
        Returns:
            Dict with EC, EM, total, and packages list (with is_favorite field)
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
            
            # Add is_favorite status to packages
            packages_with_favorite = await self._add_favorite_status(result.data, user_id)
            
            return {
                "EC": 0,
                "EM": "Successfully retrieved tour packages",
                "total": len(packages_with_favorite),
                "packages": packages_with_favorite
            }
            
        except Exception as e:
            logger.error(f"Error getting tour packages: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving tour packages: {str(e)}",
                "total": 0,
                "packages": []
            }
    
    async def filter_packages_by_month(
        self,
        month: int,
        year: int,
        date_type: str = "start_date",
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Filter tour packages by month and year
        
        Args:
            month: Month (1-12)
            year: Year
            date_type: Type of date to filter ('start_date' or 'end_date')
            is_active: Filter by active status
            limit: Number of records to return
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, total, and packages list
        """
        try:
            # Build date range for the month
            start_of_month = date(year, month, 1)
            # Get last day of month
            if month == 12:
                end_of_month = date(year + 1, 1, 1)
            else:
                end_of_month = date(year, month + 1, 1)
            
            query = self.supabase.table('tour_packages').select('*')
            
            # Filter by date range
            if date_type == "start_date":
                query = query.gte('start_date', start_of_month.isoformat())
                query = query.lt('start_date', end_of_month.isoformat())
            else:  # end_date
                query = query.gte('end_date', start_of_month.isoformat())
                query = query.lt('end_date', end_of_month.isoformat())
            
            # Apply additional filters
            if is_active is not None:
                query = query.eq('is_active', is_active)
            
            # Order by date
            query = query.order(date_type, desc=False)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            result = query.execute()
            
            # Add is_favorite status to packages
            packages_with_favorite = await self._add_favorite_status(result.data, user_id)
            
            return {
                "EC": 0,
                "EM": f"Successfully retrieved tour packages for {month}/{year}",
                "total": len(packages_with_favorite),
                "packages": packages_with_favorite
            }
            
        except Exception as e:
            logger.error(f"Error filtering packages by month: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error filtering tour packages: {str(e)}",
                "total": 0,
                "packages": []
            }
    
    async def filter_packages_by_year(
        self,
        year: int,
        date_type: str = "start_date",
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Filter tour packages by year
        
        Args:
            year: Year to filter
            date_type: Type of date to filter ('start_date' or 'end_date')
            is_active: Filter by active status
            limit: Number of records to return
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, total, and packages list
        """
        try:
            # Build date range for the year
            start_of_year = date(year, 1, 1)
            end_of_year = date(year + 1, 1, 1)
            
            query = self.supabase.table('tour_packages').select('*')
            
            # Filter by date range
            if date_type == "start_date":
                query = query.gte('start_date', start_of_year.isoformat())
                query = query.lt('start_date', end_of_year.isoformat())
            else:  # end_date
                query = query.gte('end_date', start_of_year.isoformat())
                query = query.lt('end_date', end_of_year.isoformat())
            
            # Apply additional filters
            if is_active is not None:
                query = query.eq('is_active', is_active)
            
            # Order by date
            query = query.order(date_type, desc=False)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            result = query.execute()
            
            # Add is_favorite status to packages
            packages_with_favorite = await self._add_favorite_status(result.data, user_id)
            
            return {
                "EC": 0,
                "EM": f"Successfully retrieved tour packages for year {year}",
                "total": len(packages_with_favorite),
                "packages": packages_with_favorite
            }
            
        except Exception as e:
            logger.error(f"Error filtering packages by year: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error filtering tour packages: {str(e)}",
                "total": 0,
                "packages": []
            }
    
    async def filter_packages_by_date(
        self,
        start_date: date,
        end_date: date,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Filter tour packages by a date range (inclusive).
        
        Args:
            start_date: Range start (YYYY-MM-DD)
            end_date: Range end (YYYY-MM-DD)
            is_active: Filter by active status
            limit: Number of records to return
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, total, and packages list
        """
        try:
            query = self.supabase.table('tour_packages').select('*')
            
            # Filter packages that start on/after start_date and end on/before end_date
            query = query.gte('start_date', start_date.isoformat())
            query = query.lte('end_date', end_date.isoformat())
            
            if is_active is not None:
                query = query.eq('is_active', is_active)
            
            query = query.order('start_date', desc=False)
            
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            result = query.execute()
            
            # Add is_favorite status to packages
            packages_with_favorite = await self._add_favorite_status(result.data, user_id)
            
            return {
                "EC": 0,
                "EM": f"Successfully retrieved tour packages from {start_date.isoformat()} to {end_date.isoformat()}",
                "total": len(packages_with_favorite),
                "packages": packages_with_favorite
            }
            
        except Exception as e:
            logger.error(f"Error filtering packages by date range: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error filtering tour packages: {str(e)}",
                "total": 0,
                "packages": []
            }
    
    async def filter_packages_by_price_range(
        self,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Filter tour packages by price range
        
        Args:
            min_price: Minimum price (VND)
            max_price: Maximum price (VND)
            is_active: Filter by active status
            limit: Number of records to return
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, total, and packages list
        """
        try:
            query = self.supabase.table('tour_packages').select('*')
            
            # Apply price filters
            if min_price is not None:
                query = query.gte('price', min_price)
            if max_price is not None:
                query = query.lte('price', max_price)
            
            # Apply additional filters
            if is_active is not None:
                query = query.eq('is_active', is_active)
            
            # Order by price ascending
            query = query.order('price', desc=False)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            result = query.execute()
            
            # Add is_favorite status to packages
            packages_with_favorite = await self._add_favorite_status(result.data, user_id)
            
            price_range_str = ""
            if min_price is not None and max_price is not None:
                price_range_str = f"from {min_price:,.0f} to {max_price:,.0f} VND"
            elif min_price is not None:
                price_range_str = f">= {min_price:,.0f} VND"
            elif max_price is not None:
                price_range_str = f"<= {max_price:,.0f} VND"
            
            return {
                "EC": 0,
                "EM": f"Successfully retrieved tour packages {price_range_str}",
                "total": len(packages_with_favorite),
                "packages": packages_with_favorite
            }
            
        except Exception as e:
            logger.error(f"Error filtering packages by price range: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error filtering tour packages: {str(e)}",
                "total": 0,
                "packages": []
            }
    
    async def get_package_by_id(self, package_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
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
            
            package = result.data[0]
            # Add is_favorite status
            packages_with_favorite = await self._add_favorite_status([package], user_id)
            
            return {
                "EC": 0,
                "EM": "Successfully retrieved tour package",
                "package": packages_with_favorite[0] if packages_with_favorite else package
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
                # Fetch full updated record to ensure all fields are present
                full_result = self.supabase.table('tour_packages') \
                    .select('*') \
                    .eq('package_id', package_id) \
                    .single() \
                    .execute()
                
                if full_result.data:
                    updated_package = full_result.data
                    
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
                        "EM": "Failed to fetch updated tour package",
                        "package": None
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
        Delete a tour package, its embedding, and images from Cloudinary
        
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
            
            package = existing["package"]
            
            # Delete images from Cloudinary
            if package.get("image_urls"):
                logger.info(f"Deleting images from Cloudinary for package {package_id}")
                deleted_count = await self.delete_images_from_urls(package["image_urls"])
                logger.info(f"Deleted {deleted_count} images from Cloudinary")
            
            # Delete embedding (if exists)
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
            }
    
    async def search_packages(
        self,
        user_message: str,
        max_price: Optional[float] = None,
        duration: Optional[int] = None,
        destination: Optional[str] = None,
        limit: int = 10,
        user_id: Optional[str] = None
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
            
            # Add is_favorite status to packages
            packages_with_favorite = await self._add_favorite_status(filtered_packages, user_id)
            
            return {
                "EC": 0,
                "EM": "Successfully searched tour packages",
                "found": len(packages_with_favorite),
                "packages": packages_with_favorite
            }
            
        except Exception as e:
            logger.error(f"Error searching tour packages: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error searching tour packages: {str(e)}",
                "found": 0,
                "packages": []
            }
    
    # ============================================================================
    # Admin Settings & Featured Tours (delegated to separate services)
    # ============================================================================
    
    def get_admin_setting(self, setting_key: str, default_value: Any = None) -> Any:
        """Delegate to AdminSettingsService"""
        return self.admin_settings.get_admin_setting(setting_key, default_value)
    
    def set_admin_setting(self, setting_key: str, setting_value: Any, updated_by: Optional[str] = None) -> bool:
        """Delegate to AdminSettingsService"""
        return self.admin_settings.set_admin_setting(setting_key, setting_value, updated_by)
    
    def get_featured_tours(self) -> List[Dict[str, Any]]:
        """Delegate to AdminFeaturedToursService"""
        return self.admin_featured_tours.get_featured_tours()
    
    def update_featured_tours(self, tour_package_ids: List[UUID]) -> Dict[str, Any]:
        """Delegate to AdminFeaturedToursService"""
        return self.admin_featured_tours.update_featured_tours(tour_package_ids)
    
    async def recommend_packages(
        self,
        user_id: str,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Recommend tour packages với Admin Mode support
        
        Logic:
        - Nếu ADMIN_RECOMMENDATION_ENABLED = True:
          1. Lấy featured tours (is_featured=TRUE)
          2. Nếu đủ >= k, trả k tours (cắt)
          3. Nếu thiếu, fallback AI để bù đủ (k - len(featured))
        - Nếu ADMIN_RECOMMENDATION_ENABLED = False:
          Standard AI recommendation với expiring tours + Mem0 personalization
        
        Args:
            user_id: User ID để lấy đặc điểm từ Mem0
            k: Số lượng tour được recommend (1-10)
            
        Returns:
            Dict with EC, EM, found, packages, and mode (admin/ai/hybrid)
        """
        try:
            from ..core.config import settings
            
            # Check Admin Mode (from database, fallback to settings)
            admin_mode_enabled = self.get_admin_setting(
                'ADMIN_RECOMMENDATION_ENABLED',
                default_value=settings.ADMIN_RECOMMENDATION_ENABLED
            )
            
            if admin_mode_enabled:
                logger.info("🎯 Admin Mode ENABLED - Using featured tours")
                
                # Get featured tours
                featured_tours = self.get_featured_tours()
                
                if len(featured_tours) >= k:
                    # Đủ featured tours, trả k tours
                    selected_tours = featured_tours[:k]
                    
                    # Remove description from response
                    filtered_packages = [{k: v for k, v in pkg.items() if k != 'description'} for pkg in selected_tours]
                    
                    # Add is_favorite status to packages
                    packages_with_favorite = await self._add_favorite_status(filtered_packages, user_id)
                    
                    logger.info(f"✅ Returned {len(packages_with_favorite)} featured tours (Admin Mode)")
                    
                    return {
                        "EC": 0,
                        "EM": "Successfully recommended featured tours (Admin Mode)",
                        "found": len(packages_with_favorite),
                        "packages": packages_with_favorite,
                        "mode": "admin"
                    }
                else:
                    # Thiếu featured tours, fallback AI
                    needed_count = k - len(featured_tours)
                    logger.info(f"⚠️ Only {len(featured_tours)} featured tours, need {needed_count} more from AI")
                    
                    # Get AI recommendations (exclude featured tours)
                    featured_ids = {str(tour.get('package_id')) for tour in featured_tours}
                    ai_result = await self._ai_recommend_packages(user_id, needed_count, exclude_ids=featured_ids)
                    
                    # Combine: featured first, then AI
                    combined_packages = featured_tours + ai_result.get('packages', [])
                    combined_packages = combined_packages[:k]
                    
                    # Remove description
                    filtered_packages = [{k: v for k, v in pkg.items() if k != 'description'} for pkg in combined_packages]
                    
                    # Add is_favorite status to packages
                    packages_with_favorite = await self._add_favorite_status(filtered_packages, user_id)
                    
                    logger.info(f"✅ Hybrid: {len(featured_tours)} featured + {len(ai_result.get('packages', []))} AI = {len(packages_with_favorite)} total")
                    
                    return {
                        "EC": 0,
                        "EM": f"Hybrid recommendation: {len(featured_tours)} featured + {len(ai_result.get('packages', []))} AI",
                        "found": len(packages_with_favorite),
                        "packages": packages_with_favorite,
                        "mode": "hybrid"
                    }
            else:
                # Admin Mode disabled - use AI recommendation
                logger.info("🤖 Admin Mode DISABLED - Using AI recommendation")
                ai_result = await self._ai_recommend_packages(user_id, k)
                ai_result['mode'] = 'ai'
                return ai_result
                
        except Exception as e:
            logger.error(f"Error in recommend_packages: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "EC": 1,
                "EM": f"Error recommending tour packages: {str(e)}",
                "found": 0,
                "packages": [],
                "mode": "error"
            }
    
    async def _ai_recommend_packages(
        self,
        user_id: str,
        k: int = 5,
        exclude_ids: Optional[set] = None
    ) -> Dict[str, Any]:
        """
        AI recommendation logic (original recommend_packages logic)
        
        Args:
            user_id: User ID
            k: Number of recommendations
            exclude_ids: Set of package IDs to exclude (e.g., already featured)
            
        Returns:
            Dict with packages
        """
        try:
            if exclude_ids is None:
                exclude_ids = set()
            
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
            
            # Filter out excluded IDs
            if exclude_ids:
                expiring_tours = [tour for tour in expiring_tours if str(tour.get('package_id')) not in exclude_ids]
            
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
                                preference_texts.append(content)
                        
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
            
            # Add is_favorite status to packages
            packages_with_favorite = await self._add_favorite_status(filtered_packages, user_id)
            
            logger.info(f"✅ Recommended {len(packages_with_favorite)} tours for user {user_id}")
            
            return {
                "EC": 0,
                "EM": "Successfully recommended tour packages",
                "found": len(packages_with_favorite),
                "packages": packages_with_favorite
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
    
    async def cancel_tour_package(
        self,
        package_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a tour package and all related bookings
        
        When admin cancels a tour:
        1. Set is_active = False
        2. Get all bookings with status 'pending' or 'confirmed'
        3. Cancel each booking (soft delete)
        4. Restore available_slots
        5. Create notification for each affected user
        
        Args:
            package_id: UUID of the tour package
            reason: Reason for cancellation
            
        Returns:
            Dict with EC, EM, and cancelled counts
        """
        try:
            # Import BookingService here to avoid circular import
            from .booking_service import BookingService
            booking_service = BookingService(self.supabase)
            
            # 1. Get tour package details
            package_result = await self.get_package_by_id(package_id)
            if package_result["EC"] != 0:
                return package_result
            
            package = package_result["package"]
            package_name = package.get('package_name', 'Unknown Tour')
            
            # 2. Set is_active = False
            update_result = self.supabase.table('tour_packages') \
                .update({"is_active": False, "updated_at": "now()"}) \
                .eq('package_id', package_id) \
                .execute()
            
            if not update_result.data:
                return {
                    "EC": 1,
                    "EM": "Failed to deactivate tour package"
                }
            
            # 3. Get all related bookings (pending/confirmed)
            bookings_result = self.supabase.table('bookings') \
                .select('booking_id, user_id, status, number_of_people') \
                .eq('package_id', package_id) \
                .in_('status', ['pending', 'confirmed']) \
                .execute()
            
            if not bookings_result.data:
                logger.info(f"Tour {package_id} cancelled, no active bookings to cancel")
                return {
                    "EC": 0,
                    "EM": "Tour cancelled successfully. No active bookings.",
                    "cancelled_bookings": 0
                }
            
            # 4. Cancel each booking and create notification
            cancelled_count = 0
            notification_count = 0
            
            for booking in bookings_result.data:
                # Cancel booking
                cancel_result = await booking_service.cancel_booking(
                    booking_id=booking['booking_id'],
                    reason=f"Tour đã bị hủy bởi admin. {reason or ''}".strip(),
                    cancelled_by="admin"
                )
                
                if cancel_result["EC"] == 0:
                    cancelled_count += 1
                    
                    # Create notification for user
                    notification_result = await self.notification_service.create_notification(
                        user_id=booking['user_id'],
                        type="tour_cancelled",
                        title=f"Tour '{package_name}' đã bị hủy",
                        message=f"Rất tiếc, tour '{package_name}' đã bị hủy bởi admin. " + 
                                f"Lý do: {reason or 'Không rõ lý do'}. " +
                                f"Số slot của bạn ({booking['number_of_people']} người) đã được hoàn lại.",
                        metadata={
                            "package_id": package_id,
                            "package_name": package_name,
                            "booking_id": booking['booking_id'],
                            "reason": reason
                        }
                    )
                    
                    if notification_result["EC"] == 0:
                        notification_count += 1
                else:
                    logger.warning(f"Failed to cancel booking {booking['booking_id']}: {cancel_result['EM']}")
            
            logger.info(f"Cancelled tour {package_id}: {cancelled_count} bookings cancelled, {notification_count} notifications sent")
            
            return {
                "EC": 0,
                "EM": f"Tour cancelled successfully. {cancelled_count} bookings cancelled, {notification_count} users notified.",
                "cancelled_bookings": cancelled_count,
                "notifications_sent": notification_count
            }
            
        except Exception as e:
            logger.error(f"Error cancelling tour {package_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error cancelling tour: {str(e)}",
                "cancelled_bookings": 0
            }

