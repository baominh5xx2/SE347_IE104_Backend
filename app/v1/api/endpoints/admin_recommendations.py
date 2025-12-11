"""
Admin Recommendations API Endpoints
Handles admin control over tour recommendations
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from ...schema.tour_package_schema import (
    AdminRecommendationConfig,
    AdminRecommendationUpdate,
    AdminRecommendationResponse
)
from ...services.tour_package_service import TourPackageService
from ...core.supabase import get_supabase_client
from ...core.dependencies import get_current_user
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def get_tour_package_service():
    """Dependency to get TourPackageService instance"""
    supabase = get_supabase_client()
    return TourPackageService(supabase)


def check_admin_role(current_user: dict = Depends(get_current_user)):
    """
    Dependency to check if user is admin
    Raises HTTPException if not admin
    """
    user_role = current_user.get("role", "user")
    if user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user


@router.get("/admin/recommendations", response_model=AdminRecommendationResponse)
async def get_admin_recommendations(
    service: TourPackageService = Depends(get_tour_package_service),
    current_user: dict = Depends(check_admin_role)
):
    """
    Get admin recommendation configuration and featured tours
    
    Requires: Admin role
    
    Returns:
        - enabled: Admin Mode status (from database, fallback to settings)
        - featured_tours: List of currently featured tours
        - total_featured: Count of featured tours
    """
    try:
        # Get current config from database (fallback to settings if not found)
        admin_mode_enabled = service.get_admin_setting(
            'ADMIN_RECOMMENDATION_ENABLED',
            default_value=settings.ADMIN_RECOMMENDATION_ENABLED
        )
        
        # Get featured tours
        featured_tours = service.get_featured_tours()
        
        config = AdminRecommendationConfig(
            enabled=admin_mode_enabled,
            featured_tours=featured_tours,
            total_featured=len(featured_tours)
        )
        
        return AdminRecommendationResponse(
            EC=0,
            EM="Successfully retrieved admin recommendation config",
            data=config
        )
        
    except Exception as e:
        logger.error(f"Error in get_admin_recommendations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving admin recommendation config: {str(e)}"
        )


@router.put("/admin/recommendations", response_model=AdminRecommendationResponse)
async def update_admin_recommendations(
    update_data: AdminRecommendationUpdate,
    service: TourPackageService = Depends(get_tour_package_service),
    current_user: dict = Depends(check_admin_role)
):
    """
    Update admin recommendation settings
    
    Requires: Admin role
    
    Body:
        - enabled (optional): Toggle Admin/AI mode (persisted to database)
        - tour_package_ids (optional): Set featured tours (will unset others)
    
    Note: 
        - enabled flag is persisted to database (admin_settings table) and also updated in-memory
        - tour_package_ids are validated before updating (must exist and be active)
    """
    try:
        updated_config = {}
        
        # Update enabled flag (persist to database + in-memory)
        if update_data.enabled is not None:
            # Persist to database
            success = service.set_admin_setting(
                'ADMIN_RECOMMENDATION_ENABLED',
                update_data.enabled,
                updated_by=current_user.get('user_id')
            )
            
            if success:
                # Also update in-memory settings for immediate effect
                settings.ADMIN_RECOMMENDATION_ENABLED = update_data.enabled
                updated_config['enabled'] = update_data.enabled
                logger.info(f"✅ Admin Mode {'ENABLED' if update_data.enabled else 'DISABLED'} by admin {current_user.get('user_id')}")
            else:
                logger.warning(f"⚠️ Failed to persist admin setting to database")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save admin recommendation setting"
                )
        
        # Update featured tours
        if update_data.tour_package_ids is not None:
            result = service.update_featured_tours(update_data.tour_package_ids)
            
            if not result.get('success'):
                raise HTTPException(
                    status_code=400,
                    detail=result.get('message', 'Failed to update featured tours')
                )
            
            updated_config['featured_updated'] = result.get('updated', 0)
            updated_config['valid_ids'] = result.get('valid_ids', [])
            updated_config['invalid_ids'] = result.get('invalid_ids', [])
            
            logger.info(f"✅ Featured tours updated: {result.get('updated')} tours by admin {current_user.get('user_id')}")
        
        # Get updated config (from database, fallback to settings)
        admin_mode_enabled = service.get_admin_setting(
            'ADMIN_RECOMMENDATION_ENABLED',
            default_value=settings.ADMIN_RECOMMENDATION_ENABLED
        )
        featured_tours = service.get_featured_tours()
        
        config = AdminRecommendationConfig(
            enabled=admin_mode_enabled,
            featured_tours=featured_tours,
            total_featured=len(featured_tours)
        )
        
        return AdminRecommendationResponse(
            EC=0,
            EM=f"Successfully updated admin recommendations: {', '.join(updated_config.keys())}",
            data=config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_admin_recommendations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating admin recommendations: {str(e)}"
        )

