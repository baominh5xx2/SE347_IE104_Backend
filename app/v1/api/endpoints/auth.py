"""
Authentication API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import RedirectResponse
from typing import Optional
from ...schema.auth_schema import (
    RegisterRequest,
    LoginRequest,
    VerifyTokenRequest,
    RegisterResponse,
    LoginResponse,
    VerifyTokenResponse,
    GoogleLoginRequest,
    GoogleCallbackRequest,
    GoogleAuthURLResponse,
    AdminRegisterRequest,
    AdminLoginRequest
)
from ...services.auth_service import AuthService
from ...services.google_oauth_service import GoogleOAuthService
from ...core.supabase import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


def get_auth_service():
    """Dependency to get AuthService instance"""
    supabase = get_supabase_client()
    return AuthService(supabase)


def get_google_oauth_service():
    """Dependency to get GoogleOAuthService instance"""
    supabase = get_supabase_client()
    return GoogleOAuthService(supabase)


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
    Can login with either email or phone_number
    
    Args:
        request: Login request data (must provide either email or phone_number with password)
        auth_service: Authentication service instance
        
    Returns:
        LoginResponse with access token and user data or error message
    """
    try:
        result = await auth_service.login_user(
            password=request.password,
            email=request.email,
            phone_number=request.phone_number
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


@router.post("/admin/register", response_model=RegisterResponse)
async def register_admin(
    request: AdminRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new admin user
    
    Requires admin_secret_key nếu ADMIN_SECRET_KEY được config trong .env
    
    Args:
        request: Admin registration request data
        auth_service: Authentication service instance
        
    Returns:
        RegisterResponse with admin user data or error message
    """
    try:
        result = await auth_service.register_admin(
            full_name=request.full_name,
            email=request.email,
            password=request.password,
            phone_number=request.phone_number,
            admin_secret_key=request.admin_secret_key
        )
        
        return RegisterResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in admin register endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/login", response_model=LoginResponse)
async def login_admin(
    request: AdminLoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate admin user and return access token
    Verify user có role = 'admin' sau khi login thành công
    
    Args:
        request: Admin login request data (must provide either email or phone_number with password)
        auth_service: Authentication service instance
        
    Returns:
        LoginResponse with access token and admin user data or error message
    """
    try:
        result = await auth_service.login_admin(
            password=request.password,
            email=request.email,
            phone_number=request.phone_number
        )
        
        return LoginResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in admin login endpoint: {str(e)}")
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
            "verify-token": "POST /api/v1/auth/verify-token",
            "admin-register": "POST /api/v1/auth/admin/register",
            "admin-login": "POST /api/v1/auth/admin/login",
            "google-auth-url": "GET /api/v1/auth/google/auth-url",
            "google-login": "POST /api/v1/auth/google/login",
            "google-callback": "GET /api/v1/auth/google/callback"
        }
    }


@router.get("/google/auth-url", response_model=GoogleAuthURLResponse)
async def get_google_auth_url(
    google_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """
    Get Google OAuth authorization URL
    
    This endpoint generates a URL that redirects users to Google's consent page.
    Users can use this URL to authenticate with their Google account.
    
    Returns:
        GoogleAuthURLResponse with authorization URL
    """
    try:
        auth_url = google_service.get_google_auth_url()
        return GoogleAuthURLResponse(
            EC=0,
            EM="Google OAuth URL generated",
            auth_url=auth_url
        )
    except Exception as e:
        logger.error(f"Error generating Google auth URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google/login", response_model=LoginResponse)
async def google_login(
    request: GoogleLoginRequest,
    google_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """
    Login with Google ID token
    
    This endpoint accepts a Google ID token from the client and authenticates the user.
    If the user doesn't exist, a new account is automatically created.
    
    Args:
        request: Google login request with ID token
        google_service: Google OAuth service instance
        
    Returns:
        LoginResponse with access token and user data
        
    Example:
        ```json
        {
            "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjU5N..."
        }
        ```
    """
    try:
        result = await google_service.google_login(request.id_token)
        return LoginResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in Google login endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




async def _handle_google_callback_logic(
    code: Optional[str],
    state: Optional[str],
    error: Optional[str],
    format: Optional[str],
    google_service: GoogleOAuthService
):
    """Shared logic for Google OAuth callback"""
    try:
        if error:
            logger.error(f"Google OAuth error: {error}")
            if format == "json":
                return {"EC": 1, "EM": f"Google OAuth error: {error}", "access_token": None, "user": None}
            return RedirectResponse(url=f"http://localhost:3000/login?error={error}", status_code=303)
        
        if not code:
            if format == "json":
                return {"EC": 1, "EM": "No authorization code provided", "access_token": None, "user": None}
            return RedirectResponse(url="http://localhost:3000/login?error=no_code", status_code=303)
        
        # Handle callback and get login result
        logger.info("Starting handle_google_callback...")
        result = await google_service.handle_google_callback(code, state)
        logger.info(f"handle_google_callback completed: EC={result.get('EC')}, has_token={bool(result.get('access_token'))}")
        
        # Return JSON format for testing
        if format == "json":
            return result
        
        # Default: Redirect to frontend
        if result["EC"] == 0:
            # Success - redirect to frontend home page with token
            token = result.get("access_token")
            if not token:
                logger.error("No access_token in result!")
                return RedirectResponse(url=f"http://localhost:3000/login?error=no_token", status_code=303)
            logger.info(f"Redirecting to frontend with token (length: {len(token)})")
            return RedirectResponse(url=f"http://localhost:3000/home?token={token}", status_code=303)
        else:
            # Error - redirect with error message
            error_msg = result.get("EM", "Login failed")
            return RedirectResponse(url=f"http://localhost:3000/login?error={error_msg}", status_code=303)
            
    except Exception as e:
        logger.error(f"Error in Google callback endpoint: {str(e)}")
        return RedirectResponse(url=f"http://localhost:3000/login?error={str(e)}", status_code=303)


@router.get("/google/callback")
async def google_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    format: Optional[str] = Query(None, description="Response format: 'redirect' (default) or 'json'"),
    google_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """
    Handle Google OAuth callback
    
    This endpoint handles the callback from Google after user authorization.
    It exchanges the authorization code for tokens and logs the user in.
    
    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection (optional)
        error: Error message if authorization failed
        format: Response format - 'redirect' (default) or 'json'
        google_service: Google OAuth service instance
        
    Returns:
        Redirect to frontend with token or error (default)
        OR JSON response if format=json
    """
    return await _handle_google_callback_logic(code, state, error, format, google_service)