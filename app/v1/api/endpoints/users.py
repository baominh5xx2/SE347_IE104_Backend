"""
User Profile Endpoints
API endpoints for user self-service profile management
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Dict, Any

from ...core.dependencies import get_current_user
from ...services.user_profile_service import get_user_profile_service, UserProfileService
from ...schema.user_profile_schema import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserProfileUpdateResponse,
    ChangePasswordRequest,
    ChangePasswordResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: UserProfileService = Depends(get_user_profile_service)
):
    """
    Get current user's profile
    
    Args:
        current_user: Current user from JWT
        service: UserProfileService instance
        
    Returns:
        User profile data
        
    Raises:
        404: User not found
        403: Account disabled
    """
    user_id = current_user.get("user_id")
    result = service.get_my_profile(user_id)
    
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    
    # Check if account is activated
    if result["data"] and not result["data"].get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    return result


@router.patch("/me", response_model=UserProfileUpdateResponse)
async def update_my_profile(
    request: UserProfileUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: UserProfileService = Depends(get_user_profile_service)
):
    """
    Update current user's profile (allowlist fields only)
    
    Args:
        request: Profile update request body
        current_user: Current user from JWT
        service: UserProfileService instance
        
    Returns:
        Updated user profile data
        
    Raises:
        404: User not found
        403: Account disabled
    """
    user_id = current_user.get("user_id")
    
    result = service.update_my_profile(
        user_id=user_id,
        full_name=request.full_name,
        phone_number=request.phone_number,
        profile_picture=request.profile_picture
    )
    
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    
    # Check if account is active
    if result["data"] and not result["data"].get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    return result


@router.post("/me/avatar", response_model=UserProfileUpdateResponse)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: UserProfileService = Depends(get_user_profile_service)
):
    """Upload a profile picture to Cloudinary and update the profile URL"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    content = await file.read()

    # 5 MB guardrail
    if content and len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is too large (max 5MB)")

    result = service.upload_profile_picture(
        user_id=current_user.get("user_id"),
        file_bytes=content,
        filename=file.filename or "avatar"
    )

    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])

    if result["data"] and not result["data"].get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is disabled")

    return result


@router.post("/me/password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: UserProfileService = Depends(get_user_profile_service)
):
    """Change user password"""
    result = service.change_password(
        user_id=current_user.get("user_id"),
        current_password=request.current_password,
        new_password=request.new_password
    )

    if result["EC"] == 1:
        raise HTTPException(status_code=400, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])

    return result
