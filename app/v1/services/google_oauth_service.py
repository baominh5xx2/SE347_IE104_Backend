"""
Google OAuth Service
Handles Google OAuth2 authentication flow
"""
import logging
import httpx
from typing import Dict, Any, Optional
from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
from supabase import Client
from datetime import datetime, timezone

from ..core.config import settings

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Service for Google OAuth authentication"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize GoogleOAuthService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
    def get_google_auth_url(self) -> str:
        """
        Generate Google OAuth authorization URL
        
        Returns:
            str: Authorization URL for Google OAuth
        """
        try:
            # Create OAuth2 flow
            flow = Flow.from_client_config(
                client_config={
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=[
                    'openid',
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile'
                ]
            )
            
            flow.redirect_uri = self.redirect_uri
            
            # Generate authorization URL
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            return authorization_url
            
        except Exception as e:
            logger.error(f"Error generating Google auth URL: {str(e)}")
            raise
    
    def verify_google_token(self, id_token_str: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google ID token and extract user info
        
        Args:
            id_token_str: Google ID token string
            
        Returns:
            Dict containing user info if valid, None otherwise
        """
        try:
            logger.info(f"Attempting to verify Google token...")
            logger.debug(f"Token (first 50 chars): {id_token_str[:50]}...")
            logger.debug(f"Client ID: {self.client_id[:20]}...")
            
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                id_token_str, 
                requests.Request(), 
                self.client_id
            )
            
            logger.info(f"Token verified successfully. Issuer: {idinfo.get('iss')}")
            
            # Check if token is from Google
            if idinfo.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
                logger.error(f"Invalid issuer: {idinfo.get('iss')}")
                return None
            
            # Token is valid, extract user info
            user_info = {
                "google_id": idinfo['sub'],
                "email": idinfo.get('email'),
                "email_verified": idinfo.get('email_verified', False),
                "full_name": idinfo.get('name'),
                "given_name": idinfo.get('given_name'),
                "family_name": idinfo.get('family_name'),
                "picture": idinfo.get('picture'),
                "locale": idinfo.get('locale')
            }
            
            logger.info(f"Successfully verified Google token for user: {user_info['email']}")
            return user_info
            
        except ValueError as e:
            logger.error(f"Invalid Google token (ValueError): {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verifying Google token: {str(e)}")
            return None
    
    async def google_login(self, id_token_str: str) -> Dict[str, Any]:
        """
        Authenticate user with Google ID token
        
        Args:
            id_token_str: Google ID token from client
            
        Returns:
            Dict containing login result with access token
        """
        try:
            # Verify Google token
            google_user = self.verify_google_token(id_token_str)
            
            if not google_user:
                return {
                    "EC": 1,
                    "EM": "Invalid Google token"
                }
            
            if not google_user.get('email_verified'):
                return {
                    "EC": 2,
                    "EM": "Email not verified by Google"
                }
            
            email = google_user['email']
            
            # Check if user exists
            result = self.supabase.table('users') \
                .select("*") \
                .eq('email', email) \
                .execute()
            
            from ..services.auth_service import AuthService
            auth_service = AuthService(self.supabase)
            
            if result.data:
                # User exists - update info and login
                user = result.data[0]
                
                # Update user info from Google
                update_data = {
                    "full_name": google_user.get('full_name') or user.get('full_name'),
                    "google_id": google_user.get('google_id'),
                    "profile_picture": google_user.get('picture'),
                    "login_type": "GOOGLE",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                self.supabase.table('users').update(update_data).eq('user_id', user['user_id']).execute()
                
                # Check if account is activated
                if not user.get('is_activate', True):
                    return {
                        "EC": 3,
                        "EM": "Account is not activated"
                    }
                
                # Generate access token
                access_token = auth_service._generate_access_token({
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "user_id": user["user_id"]
                })
                
                return {
                    "EC": 0,
                    "EM": "Login successful",
                    "access_token": access_token,
                    "user": {
                        "user_id": user["user_id"],
                        "email": user["email"],
                        "full_name": user["full_name"],
                        "phone_number": user.get("phone_number"),
                        "profile_picture": user.get("profile_picture")
                    }
                }
            else:
                # User doesn't exist - create new account
                new_user = {
                    "full_name": google_user.get('full_name') or google_user.get('email').split('@')[0],
                    "email": email,
                    "google_id": google_user.get('google_id'),
                    "profile_picture": google_user.get('picture'),
                    "is_activate": True,
                    "login_type": "GOOGLE",
                    "security_2fa_enabled": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                create_result = self.supabase.table('users').insert(new_user).execute()
                
                if create_result.data:
                    user = create_result.data[0]
                    
                    # Generate access token
                    access_token = auth_service._generate_access_token({
                        "email": user["email"],
                        "full_name": user["full_name"],
                        "user_id": user["user_id"]
                    })
                    
                    return {
                        "EC": 0,
                        "EM": "Account created and login successful",
                        "access_token": access_token,
                        "user": {
                            "user_id": user["user_id"],
                            "email": user["email"],
                            "full_name": user["full_name"],
                            "phone_number": user.get("phone_number"),
                            "profile_picture": user.get("profile_picture")
                        }
                    }
                else:
                    return {
                        "EC": 4,
                        "EM": "Failed to create user account"
                    }
                    
        except Exception as e:
            logger.error(f"Error during Google login: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Google login error: {str(e)}"
            }
    
    async def handle_google_callback(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle Google OAuth callback
        
        Args:
            code: Authorization code from Google (will be URL-decoded automatically)
            state: State parameter from OAuth flow (optional)
            
        Returns:
            Dict containing login result
        """
        try:
            # URL decode the code in case it's passed with %2F instead of /
            from urllib.parse import unquote
            decoded_code = unquote(code)
            
            logger.info(f"Handling Google callback with code...")
            logger.debug(f"Original code: {code[:30]}...")
            logger.debug(f"Decoded code: {decoded_code[:30]}...")
            
            # Exchange authorization code for tokens using direct HTTP request
            # This is more reliable than using Flow which requires state management
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "code": decoded_code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data)
                
                if response.status_code != 200:
                    logger.error(f"Token exchange failed: {response.text}")
                    return {
                        "EC": 6,
                        "EM": f"Failed to exchange code for token: {response.text}"
                    }
                
                token_data = response.json()
                id_token_str = token_data.get("id_token")
                
                if not id_token_str:
                    logger.error("No id_token in response")
                    return {
                        "EC": 6,
                        "EM": "No ID token received from Google"
                    }
                
                logger.info("Successfully exchanged code for token")
                
                # Login with ID token
                return await self.google_login(id_token_str)
            
            # Login with ID token
            return await self.google_login(id_token_str)
            
        except Exception as e:
            logger.error(f"Error handling Google callback: {str(e)}")
            return {
                "EC": 6,
                "EM": f"Google callback error: {str(e)}"
            }
