"""
Tour Package Service
Handles CRUD operations for tour packages
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID
from supabase import Client

# Import search service from MCP tools
try:
    from ...mcp.src.tools.tour_search_tools import tour_package_search_service
except ImportError:
    tour_package_search_service = None
    logging.warning("TourPackageSearchService not available - search functionality disabled")

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
        Create a new tour package
        
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
                return {
                    "EC": 0,
                    "EM": "Tour package created successfully",
                    "package": result.data[0]
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
        Update an existing tour package
        
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
                return {
                    "EC": 0,
                    "EM": "Tour package updated successfully",
                    "package": result.data[0]
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
        Delete a tour package
        
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
            
            return {
                "EC": 0,
                "EM": "Successfully searched tour packages",
                "found": len(packages),
                "packages": packages
            }
            
        except Exception as e:
            logger.error(f"Error searching tour packages: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error searching tour packages: {str(e)}",
                "found": 0,
                "packages": []
            }
