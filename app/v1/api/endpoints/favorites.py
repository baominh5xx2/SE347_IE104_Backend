"""
Favorite Tour API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from ...schema.favorite_schema import (
    FavoriteToggleRequest,
    FavoriteResponse,
    FavoriteCheckResponse,
    FavoriteListResponse
)
from ...services.favorite_service import FavoriteTourService
from ...core.supabase import get_supabase_client
from ...core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def get_favorite_service():
    """Dependency to get FavoriteTourService instance"""
    supabase = get_supabase_client()
    return FavoriteTourService(supabase)


@router.post("/", response_model=FavoriteResponse)
async def add_favorite(
    request: FavoriteToggleRequest,
    current_user: dict = Depends(get_current_user),
    service: FavoriteTourService = Depends(get_favorite_service)
):
    """
    Add a tour package to favorites (create favorite/thêm thích)
    
    Chỉ dùng để thêm favorite. Nếu tour đã được favorite rồi, sẽ trả về lỗi.
    Để xóa favorite, sử dụng DELETE /api/v1/favorites/{package_id}
    
    Requires authentication.
    
    Args:
        request: FavoriteToggleRequest with package_id
        current_user: Current authenticated user (from JWT token)
        service: Favorite service instance
        
    Returns:
        FavoriteResponse with is_favorite=True
        
    Example:
        POST /api/v1/favorites/
        Body:
        {
            "package_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c"
        }
    """
    try:
        user_id = current_user["user_id"]
        result = await service.add_favorite(
            user_id=user_id,
            package_id=str(request.package_id)
        )
        
        # Nếu đã favorite rồi (EC=1), trả về 409 Conflict
        if result["EC"] == 1:
            raise HTTPException(status_code=409, detail=result["EM"])
        # Nếu có lỗi khác (EC != 0), trả về 400
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return FavoriteResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in add_favorite endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my", response_model=FavoriteListResponse)
async def get_my_favorites(
    current_user: dict = Depends(get_current_user),
    service: FavoriteTourService = Depends(get_favorite_service)
):
    """
    Get list of favorite tours for the current user
    
    Returns full tour package details, sorted by most recently favorited first.
    
    Requires authentication.
    
    Args:
        current_user: Current authenticated user (from JWT token)
        service: Favorite service instance
        
    Returns:
        FavoriteListResponse with list of favorite tour packages
        
    Example:
        GET /api/v1/favorites/my
    """
    try:
        user_id = current_user["user_id"]
        result = await service.get_user_favorites(user_id=user_id)
        
        if result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])
        
        return FavoriteListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_my_favorites endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{package_id}", response_model=FavoriteResponse)
async def remove_favorite(
    package_id: UUID,
    current_user: dict = Depends(get_current_user),
    service: FavoriteTourService = Depends(get_favorite_service)
):
    """
    Remove a tour package from favorites (unfavorite/hủy thích)
    
    Requires authentication.
    
    Args:
        package_id: UUID of the tour package to remove from favorites
        current_user: Current authenticated user (from JWT token)
        service: Favorite service instance
        
    Returns:
        FavoriteResponse with is_favorite=False
        
    Example:
        DELETE /api/v1/favorites/07e8c89e-90d4-4ebc-9302-384dc6cb2f0c
    """
    try:
        user_id = current_user["user_id"]
        result = await service.remove_favorite(
            user_id=user_id,
            package_id=str(package_id)
        )
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return FavoriteResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in remove_favorite endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check/{package_id}", response_model=FavoriteCheckResponse)
async def check_favorite(
    package_id: UUID,
    current_user: dict = Depends(get_current_user),
    service: FavoriteTourService = Depends(get_favorite_service)
):
    """
    Check if a specific tour package is favorited by the current user
    
    Requires authentication.
    
    Args:
        package_id: UUID of the tour package to check
        current_user: Current authenticated user (from JWT token)
        service: Favorite service instance
        
    Returns:
        FavoriteCheckResponse with is_favorite status
        
    Example:
        GET /api/v1/favorites/check/07e8c89e-90d4-4ebc-9302-384dc6cb2f0c
    """
    try:
        user_id = current_user["user_id"]
        result = await service.is_favorite(
            user_id=user_id,
            package_id=str(package_id)
        )
        
        if result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])
        
        return FavoriteCheckResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in check_favorite endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

