"""
Admin Featured Tours Service
Handles featured tour packages management
"""
import logging
from typing import List, Dict, Any
from uuid import UUID
from supabase import Client

logger = logging.getLogger(__name__)


class AdminFeaturedToursService:
    """Service for managing featured tours"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize AdminFeaturedToursService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    def get_featured_tours(self) -> List[Dict[str, Any]]:
        """
        Get all featured tours (is_featured=TRUE and is_active=TRUE)
        
        Returns:
            List of featured tour packages
        """
        try:
            query = self.supabase.table('tour_packages').select('*')
            query = query.eq('is_featured', True)
            query = query.eq('is_active', True)
            query = query.order('created_at', desc=True)
            
            result = query.execute()
            featured_tours = result.data if result.data else []
            
            logger.info(f"📌 Found {len(featured_tours)} featured tours")
            return featured_tours
            
        except Exception as e:
            logger.error(f"Error fetching featured tours: {str(e)}")
            return []
    
    def update_featured_tours(self, tour_package_ids: List[UUID]) -> Dict[str, Any]:
        """
        Update featured tours: set is_featured=FALSE for all, then TRUE for specified IDs
        
        Args:
            tour_package_ids: List of package IDs to set as featured
            
        Returns:
            Dict with success status and message
        """
        try:
            # Step 1: Validate all IDs exist and are active
            valid_ids = []
            for pkg_id in tour_package_ids:
                result = self.supabase.table('tour_packages').select('package_id, is_active').eq('package_id', str(pkg_id)).execute()
                if result.data and len(result.data) > 0:
                    if result.data[0].get('is_active'):
                        valid_ids.append(str(pkg_id))
                    else:
                        logger.warning(f"Package {pkg_id} is inactive, skipping")
                else:
                    logger.warning(f"Package {pkg_id} not found, skipping")
            
            if not valid_ids:
                return {
                    "success": False,
                    "message": "No valid package IDs provided",
                    "updated": 0
                }
            
            # Step 2: Set is_featured=FALSE for all
            self.supabase.table('tour_packages').update({'is_featured': False}).neq('package_id', '00000000-0000-0000-0000-000000000000').execute()
            
            # Step 3: Set is_featured=TRUE for specified IDs
            for pkg_id in valid_ids:
                self.supabase.table('tour_packages').update({'is_featured': True}).eq('package_id', pkg_id).execute()
            
            logger.info(f"✅ Updated {len(valid_ids)} featured tours")
            
            return {
                "success": True,
                "message": f"Successfully updated {len(valid_ids)} featured tours",
                "updated": len(valid_ids),
                "valid_ids": valid_ids,
                "invalid_ids": [str(pid) for pid in tour_package_ids if str(pid) not in valid_ids]
            }
            
        except Exception as e:
            logger.error(f"Error updating featured tours: {str(e)}")
            return {
                "success": False,
                "message": f"Error updating featured tours: {str(e)}",
                "updated": 0
            }

