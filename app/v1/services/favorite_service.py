"""
Favorite Tour Service
Handles favorite tour operations (like/heart feature)
"""
import logging
from typing import Dict, Any
from datetime import datetime, timezone
from supabase import Client

logger = logging.getLogger(__name__)


class FavoriteTourService:
    """Service for managing favorite tours"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize FavoriteTourService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    async def add_favorite(self, user_id: str, package_id: str) -> Dict[str, Any]:
        """
        Add a tour package to user's favorites (create favorite)
        
        Args:
            user_id: UUID of the user
            package_id: UUID of the tour package
            
        Returns:
            Dict with EC, EM, and is_favorite status (always True if successful)
        """
        try:
            # Check if already favorited
            existing = self.supabase.table('favorite_tours') \
                .select('favorite_id') \
                .eq('user_id', user_id) \
                .eq('package_id', package_id) \
                .execute()
            
            if existing.data:
                # Already favorited
                return {
                    "EC": 1,
                    "EM": "Tour is already in favorites",
                    "is_favorite": True
                }
            
            # Add to favorites
            favorite_data = {
                "user_id": user_id,
                "package_id": package_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table('favorite_tours') \
                .insert(favorite_data) \
                .execute()
            
            if result.data:
                logger.info(f"Added favorite: user={user_id}, package={package_id}")
                return {
                    "EC": 0,
                    "EM": "Tour added to favorites",
                    "is_favorite": True
                }
            else:
                return {
                    "EC": 2,
                    "EM": "Failed to add favorite",
                    "is_favorite": False
                }
                    
        except Exception as e:
            logger.error(f"Error adding favorite: {str(e)}")
            return {
                "EC": 3,
                "EM": f"Error adding favorite: {str(e)}",
                "is_favorite": False
            }
    
    async def remove_favorite(self, user_id: str, package_id: str) -> Dict[str, Any]:
        """
        Remove a tour package from user's favorites (unfavorite)
        
        Args:
            user_id: UUID of the user
            package_id: UUID of the tour package
            
        Returns:
            Dict with EC, EM, and is_favorite status (always False after removal)
        """
        try:
            # Check if favorited
            existing = self.supabase.table('favorite_tours') \
                .select('favorite_id') \
                .eq('user_id', user_id) \
                .eq('package_id', package_id) \
                .execute()
            
            if not existing.data:
                # Not favorited, nothing to remove
                return {
                    "EC": 0,
                    "EM": "Tour is not in favorites",
                    "is_favorite": False
                }
            
            # Remove from favorites
            result = self.supabase.table('favorite_tours') \
                .delete() \
                .eq('user_id', user_id) \
                .eq('package_id', package_id) \
                .execute()
            
            logger.info(f"Removed favorite: user={user_id}, package={package_id}")
            
            return {
                "EC": 0,
                "EM": "Tour removed from favorites",
                "is_favorite": False
            }
                    
        except Exception as e:
            logger.error(f"Error removing favorite: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error removing favorite: {str(e)}",
                "is_favorite": False
            }
    
    async def is_favorite(self, user_id: str, package_id: str) -> Dict[str, Any]:
        """
        Check if a tour package is favorited by the user
        
        Args:
            user_id: UUID of the user
            package_id: UUID of the tour package
            
        Returns:
            Dict with EC, EM, and is_favorite status
        """
        try:
            result = self.supabase.table('favorite_tours') \
                .select('favorite_id') \
                .eq('user_id', user_id) \
                .eq('package_id', package_id) \
                .execute()
            
            is_favorite = len(result.data) > 0
            
            return {
                "EC": 0,
                "EM": "Success",
                "is_favorite": is_favorite
            }
            
        except Exception as e:
            logger.error(f"Error checking favorite status: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error checking favorite status: {str(e)}",
                "is_favorite": False
            }
    
    async def get_user_favorites(self, user_id: str) -> Dict[str, Any]:
        """
        Get all favorite tours for a user with full tour package details
        Sorted by created_at DESC (most recently favorited first)
        Tour mới được tym (favorite) mới nhất sẽ lên đầu
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dict with EC, EM, total, and packages list (sorted by favorited_at DESC)
        """
        try:
            # Get favorite records với thứ tự sắp xếp theo created_at DESC (mới nhất lên đầu)
            # Supabase doesn't support direct JOIN, so we'll do it in two steps
            # First get favorite IDs sorted by created_at, then get packages
            
            # Get favorite records - sắp xếp theo ngày tym (created_at DESC)
            favorites_result = self.supabase.table('favorite_tours') \
                .select('package_id, created_at') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .execute()
            
            if not favorites_result.data:
                return {
                    "EC": 0,
                    "EM": "No favorite tours found",
                    "total": 0,
                    "packages": []
                }
            
            # Extract package IDs (giữ nguyên thứ tự đã sort)
            package_ids = [fav['package_id'] for fav in favorites_result.data]
            
            # Get tour packages (thứ tự từ .in_() có thể không giữ nguyên, nên cần sort lại)
            packages_result = self.supabase.table('tour_packages') \
                .select('*') \
                .in_('package_id', package_ids) \
                .execute()
            
            # Create a map of package_id -> package data
            packages_map = {str(pkg['package_id']): pkg for pkg in packages_result.data}
            
            # Build sorted packages list theo thứ tự favorites_result.data (đã sort theo created_at DESC)
            # Đảm bảo tour mới tym mới nhất lên đầu
            sorted_packages = []
            for fav in favorites_result.data:
                package_id = str(fav['package_id'])
                if package_id in packages_map:
                    package = packages_map[package_id].copy()
                    # Add favorite timestamp để frontend có thể hiển thị
                    package['favorited_at'] = fav['created_at']
                    sorted_packages.append(package)
            
            # Đảm bảo sort lại một lần nữa theo favorited_at DESC (phòng trường hợp có vấn đề)
            # Convert created_at string to datetime for proper sorting
            def get_sort_key(pkg):
                favorited_at = pkg.get('favorited_at', '')
                try:
                    # Try to parse ISO format datetime string
                    if isinstance(favorited_at, str):
                        return datetime.fromisoformat(favorited_at.replace('Z', '+00:00'))
                    return favorited_at
                except:
                    # Fallback to string comparison
                    return favorited_at
            
            sorted_packages.sort(key=get_sort_key, reverse=True)
            
            logger.info(f"Retrieved {len(sorted_packages)} favorite tours for user {user_id}, sorted by favorited_at DESC")
            
            return {
                "EC": 0,
                "EM": "Successfully retrieved favorite tours",
                "total": len(sorted_packages),
                "packages": sorted_packages
            }
            
        except Exception as e:
            logger.error(f"Error getting user favorites: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving favorite tours: {str(e)}",
                "total": 0,
                "packages": []
            }

