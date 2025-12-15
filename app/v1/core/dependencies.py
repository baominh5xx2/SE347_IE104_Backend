"""
Authentication and Authorization Dependencies
FastAPI dependencies để extract và verify user từ JWT token
"""
import logging
from fastapi import Depends, HTTPException, Header, status
from typing import Optional, Dict, Any
from ..services.auth_service import AuthService
from ..core.supabase import get_supabase_client

logger = logging.getLogger(__name__)


def get_auth_service() -> AuthService:
    """
    Dependency để get AuthService instance
    
    Returns:
        AuthService instance
    """
    supabase = get_supabase_client()
    return AuthService(supabase)


def get_current_user(
    authorization: Optional[str] = Header(None),
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Extract và verify JWT token từ Authorization header
    Query role từ database và return user info với role
    
    Args:
        authorization: Authorization header value (format: "Bearer <token>")
        auth_service: AuthService instance
        
    Returns:
        Dict với user info: {user_id, email, full_name, role}
        
    Raises:
        HTTPException 401: Nếu token missing, invalid, expired hoặc user không tồn tại
    """
    # Extract token từ Authorization header
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required"
        )
    
    # Parse "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
    
    token = parts[1]
    
    # Verify token
    verify_result = auth_service.verify_token(token)
    
    if verify_result["EC"] != 0:
        error_msg = verify_result.get("EM", "Token verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg
        )
    
    token_data = verify_result["data"]
    user_id = token_data.get("user_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    
    # Query role and activation status từ database
    user_status = auth_service.get_user_status(user_id)
    
    if user_status is None:
        logger.warning(f"User {user_id} not found in database")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check if account is active
    if not user_status.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Return user info với role
    return {
        "user_id": user_id,
        "email": token_data.get("email"),
        "full_name": token_data.get("full_name"),
        "role": user_status.get("role", "user")
    }


def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Verify user có role = 'admin'
    
    Args:
        current_user: Current user info từ get_current_user() dependency
        
    Returns:
        Admin user info
        
    Raises:
        HTTPException 403: Nếu user không phải admin
    """
    role = current_user.get("role")
    
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


def get_chat_room_service():
    """
    Dependency để get ChatRoomService instance
    
    Returns:
        ChatRoomService instance
    """
    from ..services.chat_room_service import ChatRoomService
    supabase = get_supabase_client()
    return ChatRoomService(supabase)
