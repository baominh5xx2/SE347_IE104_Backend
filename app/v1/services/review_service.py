"""
Review Service
Handles review CRUD operations
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from supabase import Client

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for managing tour reviews"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize ReviewService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    async def get_all_reviews(
        self,
        package_id: Optional[str] = None,
        user_id: Optional[str] = None,
        is_approved: Optional[bool] = None,
        rating: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all reviews with optional filters
        
        Args:
            package_id: Filter by package ID
            user_id: Filter by user ID
            is_approved: Filter by approval status
            rating: Filter by rating
            limit: Maximum number of results
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            # Select reviews with tour_packages info via JOIN through bookings and users
            query = self.supabase.table('reviews').select(
                'review_id, booking_id, user_id, package_id, rating, comment, is_approved, created_at, updated_at, '
                'users(full_name, email, profile_picture), '
                'bookings(package_id, tour_packages(package_id, package_name, destination, price))',
                count='exact'
            )
            
            # Apply filters
            if package_id:
                query = query.eq('package_id', package_id)
            if user_id:
                query = query.eq('user_id', user_id)
            if is_approved is not None:
                query = query.eq('is_approved', is_approved)
            if rating:
                query = query.eq('rating', rating)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            # Order by created_at descending
            query = query.order('created_at', desc=True)
            
            result = query.execute()
            
            # Flatten nested bookings.tour_packages and users data
            flattened_data = []
            for review in (result.data or []):
                # Get users data - Supabase returns as object for one-to-one relationship
                user_data = review.get('users', {})
                if isinstance(user_data, list) and user_data:
                    user_data = user_data[0]
                elif not isinstance(user_data, dict):
                    user_data = {}
                
                # Get bookings data
                booking_data = review.get('bookings')
                if isinstance(booking_data, list) and booking_data:
                    booking_data = booking_data[0]
                elif not isinstance(booking_data, dict):
                    booking_data = {}
                
                # Get tour_packages data from bookings
                package_data = booking_data.get('tour_packages', {}) if booking_data else {}
                if isinstance(package_data, list) and package_data:
                    package_data = package_data[0]
                elif not isinstance(package_data, dict):
                    package_data = {}
                
                # Build flattened review with all user and package metadata
                flattened_review = {
                    "review_id": review.get('review_id'),
                    "booking_id": review.get('booking_id'),
                    "user_id": review.get('user_id'),
                    "package_id": review.get('package_id'),
                    "rating": review.get('rating'),
                    "comment": review.get('comment'),
                    "is_approved": review.get('is_approved'),
                    "created_at": review.get('created_at'),
                    "updated_at": review.get('updated_at'),
                    # User metadata - ensure these are always included
                    "user_full_name": user_data.get('full_name') if user_data else None,
                    "user_email": user_data.get('email') if user_data else None,
                    "user_profile_picture": user_data.get('profile_picture') if user_data else None,
                    # Package metadata - extract package name
                    "package_name": package_data.get('package_name') if package_data else None,
                    "package": package_data if package_data else None
                }
                flattened_data.append(flattened_review)
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": flattened_data,
                "total": result.count
            }
            
        except Exception as e:
            logger.error(f"Error getting reviews: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving reviews: {str(e)}",
                "data": None,
                "total": 0
            }
    
    async def get_review_by_id(self, review_id: str) -> Dict[str, Any]:
        """
        Get review by ID
        
        Args:
            review_id: UUID of the review
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            result = self.supabase.table('reviews') \
                .select('*') \
                .eq('review_id', review_id) \
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Review not found",
                    "data": None
                }
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting review {review_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving review: {str(e)}",
                "data": None
            }
    
    async def get_review_detail(self, review_id: str) -> Dict[str, Any]:
        """
        Get review detail with user and package information
        
        Args:
            review_id: UUID of the review
            
        Returns:
            Dict with EC, EM, and data (includes user and package info)
        """
        try:
            # Get review with joined user and package info
            result = self.supabase.table('reviews') \
                .select('review_id, booking_id, user_id, package_id, rating, comment, is_approved, created_at, updated_at, users(full_name, email, profile_picture), tour_packages(package_name, destination)') \
                .eq('review_id', review_id) \
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Review not found",
                    "data": None
                }
            
            review = result.data[0]
            
            # Flatten nested data
            user_data = review.get('users', {})
            if isinstance(user_data, list) and user_data:
                user_data = user_data[0]
            elif not isinstance(user_data, dict):
                user_data = {}
            
            package_data = review.get('tour_packages', {})
            if isinstance(package_data, list) and package_data:
                package_data = package_data[0]
            elif not isinstance(package_data, dict):
                package_data = {}
            
            # Build response
            review_detail = {
                "review_id": review.get('review_id'),
                "booking_id": review.get('booking_id'),
                "user_id": review.get('user_id'),
                "package_id": review.get('package_id'),
                "rating": review.get('rating'),
                "comment": review.get('comment'),
                "is_approved": review.get('is_approved'),
                "created_at": review.get('created_at'),
                "updated_at": review.get('updated_at'),
                "user_full_name": user_data.get('full_name'),
                "user_email": user_data.get('email'),
                "user_profile_picture": user_data.get('profile_picture'),
                "package_name": package_data.get('package_name'),
                "destination": package_data.get('destination')
            }
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": review_detail
            }
            
        except Exception as e:
            logger.error(f"Error getting review detail {review_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving review detail: {str(e)}",
                "data": None
            }
    
    async def create_review(self, review_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Create a new review
        
        Args:
            review_data: Dictionary containing review information
                - booking_id: UUID
                - package_id: UUID
                - rating: int (1-5)
                - comment: Optional[str]
            user_id: UUID of the user creating the review
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            # Verify booking exists and belongs to user
            booking_result = self.supabase.table('bookings') \
                .select('booking_id, user_id, package_id, status') \
                .eq('booking_id', str(review_data['booking_id'])) \
                .execute()
            
            if not booking_result.data:
                return {
                    "EC": 1,
                    "EM": "Booking not found",
                    "data": None
                }
            
            booking = booking_result.data[0]
            
            # Check if booking belongs to user
            if str(booking['user_id']) != str(user_id):
                return {
                    "EC": 2,
                    "EM": "You can only review your own bookings",
                    "data": None
                }
            
            # Check if booking is completed (only completed bookings can be reviewed)
            if booking['status'] != 'completed':
                return {
                    "EC": 3,
                    "EM": f"Only completed bookings can be reviewed. Current status: {booking['status']}",
                    "data": None
                }
            
            # Verify package_id matches booking's package_id
            if str(booking['package_id']) != str(review_data['package_id']):
                return {
                    "EC": 4,
                    "EM": "Package ID does not match the booking's package",
                    "data": None
                }
            
            # Check if review already exists for this booking (unique constraint)
            existing_review = self.supabase.table('reviews') \
                .select('review_id') \
                .eq('booking_id', str(review_data['booking_id'])) \
                .execute()
            
            if existing_review.data:
                return {
                    "EC": 5,
                    "EM": "A review already exists for this booking",
                    "data": None
                }
            
            # Prepare review data
            now = datetime.now(timezone.utc).isoformat()
            review_insert = {
                "booking_id": str(review_data['booking_id']),
                "user_id": str(user_id),
                "package_id": str(review_data['package_id']),
                "rating": review_data['rating'],
                "comment": review_data.get('comment'),
                "is_approved": False,  # Default to False, requires admin approval
                "created_at": now,
                "updated_at": now
            }
            
            # Insert review
            result = self.supabase.table('reviews').insert(review_insert).execute()
            
            if not result.data:
                return {
                    "EC": 6,
                    "EM": "Failed to create review",
                    "data": None
                }
            
            logger.info(f"Created review {result.data[0]['review_id']} for booking {review_data['booking_id']}")
            
            return {
                "EC": 0,
                "EM": "Review created successfully",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error creating review: {str(e)}")
            return {
                "EC": 7,
                "EM": f"Error creating review: {str(e)}",
                "data": None
            }
    
    async def update_review(
        self, 
        review_id: str, 
        update_data: Dict[str, Any],
        user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Update review information
        
        Args:
            review_id: UUID of the review
            update_data: Dictionary containing fields to update
            user_id: UUID of the user (required if not admin)
            is_admin: Whether the user is an admin
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            # Check if review exists
            existing = await self.get_review_by_id(review_id)
            if existing["EC"] != 0:
                return existing
            
            review = existing["data"]
            
            # Check permissions: only owner or admin can update
            if not is_admin:
                if not user_id:
                    return {
                        "EC": 1,
                        "EM": "User ID is required",
                        "data": None
                    }
                
                if str(review['user_id']) != str(user_id):
                    return {
                        "EC": 2,
                        "EM": "You can only update your own reviews",
                        "data": None
                    }
            
            # Only admin can update is_approved
            if 'is_approved' in update_data and not is_admin:
                return {
                    "EC": 3,
                    "EM": "Only admins can change approval status",
                    "data": None
                }
            
            # When user (not admin) updates review content, reset approval status
            # Admin needs to re-approve the modified review
            if not is_admin and ('rating' in update_data or 'comment' in update_data):
                update_data['is_approved'] = False
                logger.info(f"Review {review_id} approval reset due to content change by user")
            
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Update review
            result = self.supabase.table('reviews') \
                .update(update_data) \
                .eq('review_id', review_id) \
                .execute()
            
            if not result.data:
                return {
                    "EC": 4,
                    "EM": "Failed to update review",
                    "data": None
                }
            
            logger.info(f"Updated review {review_id}")
            
            return {
                "EC": 0,
                "EM": "Review updated successfully",
                "data": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error updating review {review_id}: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error updating review: {str(e)}",
                "data": None
            }
    
    async def delete_review(
        self, 
        review_id: str,
        user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a review
        
        Args:
            review_id: UUID of the review
            user_id: UUID of the user (required if not admin)
            is_admin: Whether the user is an admin
            
        Returns:
            Dict with EC and EM
        """
        try:
            # Check if review exists
            existing = await self.get_review_by_id(review_id)
            if existing["EC"] != 0:
                return existing
            
            review = existing["data"]
            
            # Check permissions: only owner or admin can delete
            if not is_admin:
                if not user_id:
                    return {
                        "EC": 1,
                        "EM": "User ID is required",
                        "data": None
                    }
                
                if str(review['user_id']) != str(user_id):
                    return {
                        "EC": 2,
                        "EM": "You can only delete your own reviews",
                        "data": None
                    }
            
            # Delete review
            result = self.supabase.table('reviews') \
                .delete() \
                .eq('review_id', review_id) \
                .execute()
            
            if not result.data:
                return {
                    "EC": 3,
                    "EM": "Failed to delete review"
                }
            
            logger.info(f"Deleted review {review_id}")
            
            return {
                "EC": 0,
                "EM": "Review deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting review {review_id}: {str(e)}")
            return {
                "EC": 4,
                "EM": f"Error deleting review: {str(e)}"
            }
    
    async def get_reviews_by_package(
        self,
        package_id: str,
        is_approved: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all approved reviews for a package
        
        Args:
            package_id: UUID of the package
            is_approved: Only get approved reviews (default: True)
            limit: Maximum number of results
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, data, and total
        """
        return await self.get_all_reviews(
            package_id=package_id,
            is_approved=is_approved,
            limit=limit,
            offset=offset
        )
    
    async def get_review_stats(self, package_id: str) -> Dict[str, Any]:
        """
        Get review statistics for a package
        
        Args:
            package_id: UUID of the package
            
        Returns:
            Dict with EC, EM, and data (stats)
        """
        try:
            # Get all approved reviews for the package
            reviews_result = self.supabase.table('reviews') \
                .select('rating') \
                .eq('package_id', package_id) \
                .eq('is_approved', True) \
                .execute()
            
            if not reviews_result.data:
                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": {
                        "total_reviews": 0,
                        "average_rating": 0.0,
                        "rating_distribution": {
                            "1": 0,
                            "2": 0,
                            "3": 0,
                            "4": 0,
                            "5": 0
                        }
                    }
                }
            
            ratings = [review['rating'] for review in reviews_result.data]
            total_reviews = len(ratings)
            average_rating = sum(ratings) / total_reviews if total_reviews > 0 else 0.0
            
            # Calculate rating distribution
            rating_distribution = {
                "1": ratings.count(1),
                "2": ratings.count(2),
                "3": ratings.count(3),
                "4": ratings.count(4),
                "5": ratings.count(5)
            }
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "total_reviews": total_reviews,
                    "average_rating": round(average_rating, 2),
                    "rating_distribution": rating_distribution
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting review stats for package {package_id}: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving review stats: {str(e)}",
                "data": None
            }
