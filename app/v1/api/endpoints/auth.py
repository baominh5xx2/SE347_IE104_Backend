"""
Authentication API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from ...schema.auth_schema import (
    RegisterRequest,
    LoginRequest,
    VerifyTokenRequest,
    RegisterResponse,
    LoginResponse,
    VerifyTokenResponse
)
from ...services.auth_service import AuthService
from ...core.supabase import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


def get_auth_service():
    """Dependency to get AuthService instance"""
    supabase = get_supabase_client()
    return AuthService(supabase)


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user
    
    Args:
        request: Registration request data
        auth_service: Authentication service instance
        
    Returns:
        RegisterResponse with user data or error message
    """
    try:
        result = await auth_service.register_user(
            full_name=request.full_name,
            email=request.email,
            password=request.password,
            phone_number=request.phone_number
        )
        
        if result["EC"] != 0:
            return RegisterResponse(**result)
        
        return RegisterResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in register endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and return access token
    
    Args:
        request: Login request data
        auth_service: Authentication service instance
        
    Returns:
        LoginResponse with access token and user data or error message
    """
    try:
        result = await auth_service.login_user(
            email=request.email,
            password=request.password
        )
        
        return LoginResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in login endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-token", response_model=VerifyTokenResponse)
async def verify_token(
    request: VerifyTokenRequest = None,
    authorization: Optional[str] = Header(None),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Verify JWT access token
    
    Args:
        request: Optional token in request body
        authorization: Optional token in Authorization header
        auth_service: Authentication service instance
        
    Returns:
        VerifyTokenResponse with decoded token data or error message
    """
    try:
        # Get token from request body or Authorization header
        token = None
        if request and request.token:
            token = request.token
        elif authorization:
            # Extract token from "Bearer <token>" format
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
        
        if not token:
            return VerifyTokenResponse(
                EC=1,
                EM="Token is required"
            )
        
        result = auth_service.verify_token(token)
        return VerifyTokenResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in verify-token endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def auth_info():
    """
    Get authentication API information
    
    Returns:
        API information
    """
    return {
        "message": "Authentication API",
        "version": "1.0",
        "endpoints": {
            "register": "POST /api/v1/auth/register",
            "login": "POST /api/v1/auth/login",
            "verify-token": "POST /api/v1/auth/verify-token"
        }
    }
