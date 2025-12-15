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
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
import asyncio

from ..core.config import settings

logger = logging.getLogger(__name__)

# Optional Fernet import for encrypting refresh tokens
try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:
    Fernet = None  # type: ignore
    InvalidToken = Exception  # type: ignore


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
        # Prepare Fernet if encryption key provided
        self._fernet = None
        enc_key = getattr(settings, 'TOKEN_ENCRYPTION_KEY', '')
        if enc_key and Fernet is not None:
            try:
                # Expecting URL-safe base64-encoded key
                self._fernet = Fernet(enc_key.encode('utf-8'))
            except Exception:
                logger.warning("Invalid TOKEN_ENCRYPTION_KEY provided; refresh tokens will be stored plaintext")
        
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
    
    def _verify_google_token_sync(self, id_token_str: str, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous helper to verify Google token (runs in thread pool)
        Uses official Google API verification: google.oauth2.id_token.verify_oauth2_token
        """
        try:
            logger.info(f"Verifying Google token in thread using official Google API...")
            logger.debug(f"Token (first 50 chars): {id_token_str[:50]}...")
            logger.debug(f"Client ID: {client_id[:20]}...")
            
            # Verify the token using official Google API
            # This is the proper way to verify Google ID tokens
            idinfo = id_token.verify_oauth2_token(
                id_token_str, 
                requests.Request(), 
                client_id
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
            logger.error(f"Error verifying Google token: {str(e)}", exc_info=True)
            return None
    
    def _decode_token_fallback(self, id_token_str: str) -> Optional[Dict[str, Any]]:
        """
        Fallback: Decode JWT token locally without verification (less secure but works)
        Only use when Google API verification fails
        """
        try:
            import base64
            import json
            
            logger.warning("Using fallback: Decoding token locally without verification")
            
            # JWT has 3 parts: header.payload.signature
            parts = id_token_str.split('.')
            if len(parts) != 3:
                logger.error("Invalid JWT format")
                return None
            
            # Decode payload (second part)
            payload = parts[1]
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded = base64.urlsafe_b64decode(payload)
            idinfo = json.loads(decoded)
            
            # Basic validation
            if not idinfo.get('email'):
                logger.error("No email in token")
                return None
            
            logger.info(f"Token decoded locally. Email: {idinfo.get('email')}")
            
            user_info = {
                "google_id": idinfo.get('sub'),
                "email": idinfo.get('email'),
                "email_verified": idinfo.get('email_verified', True),  # Assume verified
                "full_name": idinfo.get('name'),
                "given_name": idinfo.get('given_name'),
                "family_name": idinfo.get('family_name'),
                "picture": idinfo.get('picture'),
                "locale": idinfo.get('locale')
            }
            
            return user_info
            
        except Exception as e:
            logger.error(f"Fallback token decode also failed: {str(e)}")
            return None

    async def verify_google_token(self, id_token_str: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google ID token and extract user info (async version)
        
        Args:
            id_token_str: Google ID token string
            
        Returns:
            Dict containing user info if valid, None otherwise
        """
        try:
            logger.info(f"Attempting to verify Google token...")
            logger.debug(f"Token (first 50 chars): {id_token_str[:50]}...")
            logger.debug(f"Client ID: {self.client_id[:20]}...")
            
            # Run blocking I/O in thread pool with timeout to avoid blocking event loop
            # This allows the event loop to handle other requests while waiting for Google API
            loop = asyncio.get_event_loop()
            try:
                # Set timeout to 30 seconds for Google API verification
                # Google API can sometimes be slow, so we give it enough time
                idinfo = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,  # Use default executor
                        self._verify_google_token_sync,
                        id_token_str,
                        self.client_id
                    ),
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                logger.error("Token verification timed out after 30 seconds - Google API may be slow")
                return None
            
            return idinfo
            
        except Exception as e:
            logger.error(f"Error in async verify_google_token: {str(e)}", exc_info=True)
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
            # Verify Google token (now async)
            logger.info("Verifying Google ID token...")
            google_user = await self.verify_google_token(id_token_str)
            logger.info(f"Google token verified. Email: {google_user.get('email') if google_user else 'None'}")
            
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
            logger.info(f"Checking if user exists with email: {email}")
            result = self.supabase.table('users') \
                .select("*") \
                .eq('email', email) \
                .execute()
            logger.info(f"User check result: {len(result.data) if result.data else 0} user(s) found")
            
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
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "last_access_time": datetime.now(timezone.utc).isoformat()
                }
                
                self.supabase.table('users').update(update_data).eq('user_id', user['user_id']).execute()
                
                # Check if account is activated
                if not user.get('is_activate', True):
                    return {
                        "EC": 3,
                        "EM": "Account is not activated"
                    }
                
                # Get user role (default to 'user' if not set)
                role = user.get('role', 'user')
                
                # Generate access token
                logger.info("Generating access token for existing user...")
                access_token = auth_service._generate_access_token({
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "user_id": user["user_id"],
                    "role": role
                })
                logger.info("Access token generated successfully")
                
                return {
                    "EC": 0,
                    "EM": "Login successful",
                    "access_token": access_token,
                    "user": {
                        "user_id": user["user_id"],
                        "email": user["email"],
                        "full_name": user["full_name"],
                        "phone_number": user.get("phone_number"),
                        "profile_picture": user.get("profile_picture"),
                        "role": role
                    }
                }
            else:
                # User doesn't exist - create new account
                current_time = datetime.now(timezone.utc).isoformat()
                new_user = {
                    "full_name": google_user.get('full_name') or google_user.get('email').split('@')[0],
                    "email": email,
                    "google_id": google_user.get('google_id'),
                    "profile_picture": google_user.get('picture'),
                    "is_activate": True,
                    "login_type": "GOOGLE",
                    "security_2fa_enabled": False,
                    "role": "user",  # Default role for new users
                    "created_at": current_time,
                    "updated_at": current_time,
                    "last_access_time": current_time
                }
                
                logger.info("Creating new user account...")
                create_result = self.supabase.table('users').insert(new_user).execute()
                logger.info(f"New user created: {create_result.data[0]['user_id'] if create_result.data else 'Failed'}")
                
                if create_result.data:
                    user = create_result.data[0]
                    
                    # Get user role (default to 'user' if not set)
                    role = user.get('role', 'user')
                    
                    # Generate access token
                    access_token = auth_service._generate_access_token({
                        "email": user["email"],
                        "full_name": user["full_name"],
                        "user_id": user["user_id"],
                        "role": role
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
                            "profile_picture": user.get("profile_picture"),
                            "role": role
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

    def _encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using Fernet if available, otherwise return plaintext."""
        if not plaintext:
            return plaintext
        if self._fernet is None:
            return plaintext
        try:
            token = self._fernet.encrypt(plaintext.encode('utf-8'))
            return token.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt token: {str(e)}")
            return plaintext

    def _decrypt(self, token_text: str) -> str:
        """Decrypt token_text using Fernet if available, otherwise return token_text."""
        if not token_text:
            return token_text
        if self._fernet is None:
            return token_text
        try:
            data = self._fernet.decrypt(token_text.encode('utf-8'))
            return data.decode('utf-8')
        except InvalidToken:
            logger.error("Invalid encryption token when trying to decrypt refresh token")
            return token_text
        except Exception as e:
            logger.error(f"Failed to decrypt token: {str(e)}")
            return token_text

    async def refresh_access_token(self, user_id: str) -> Dict[str, Any]:
        """Refresh access token using stored refresh_token for given user_id.

        Returns a dict with EC/EM and optionally new access_token and expires_at.
        """
        try:
            # Read stored credentials
            res = self.supabase.table('google_drive_credentials').select('*').eq('user_id', user_id).execute()
            if not res.data:
                return {"EC": 1, "EM": "No google_drive_credentials for user"}

            creds = res.data[0]
            stored_refresh = creds.get('refresh_token')
            if not stored_refresh:
                return {"EC": 2, "EM": "No refresh_token available"}

            refresh_token = self._decrypt(stored_refresh)

            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data)

            if response.status_code != 200:
                logger.error(f"Refresh token failed: {response.text}")
                return {"EC": 3, "EM": f"Refresh failed: {response.text}"}

            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in')
            scope = token_data.get('scope')

            expires_at = None
            if expires_in:
                try:
                    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()
                except Exception:
                    expires_at = None

            update = {"updated_at": datetime.now(timezone.utc).isoformat()}
            if access_token:
                update['access_token'] = access_token
            if expires_at:
                update['expires_at'] = expires_at
            if scope:
                update['scope'] = scope

            try:
                self.supabase.table('google_drive_credentials').update(update).eq('user_id', user_id).execute()
            except Exception as e:
                logger.error(f"Failed to update google_drive_credentials after refresh: {str(e)}")

            return {"EC": 0, "EM": "Refreshed", "access_token": access_token, "expires_at": expires_at}

        except Exception as e:
            logger.error(f"Error refreshing access token: {str(e)}")
            return {"EC": 4, "EM": f"Error: {str(e)}"}
    
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

                # Login / create user with ID token
                logger.info("Calling google_login...")
                login_result = await self.google_login(id_token_str)
                logger.info(f"google_login completed: EC={login_result.get('EC')}, EM={login_result.get('EM')}")

                # If login succeeded, persist Google Drive OAuth2 credentials
                try:
                    if login_result.get("EC") == 0 and login_result.get("user"):
                        logger.info("Saving Google Drive credentials...")
                        user = login_result["user"]
                        user_id = user.get("user_id")

                        # Extract token details (note: refresh_token is only returned on first consent)
                        refresh_token = token_data.get("refresh_token")
                        access_token = token_data.get("access_token")
                        expires_in = token_data.get("expires_in")
                        scope = token_data.get("scope")

                        expires_at = None
                        if expires_in:
                            try:
                                expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()
                            except Exception:
                                expires_at = None

                        now_iso = datetime.now(timezone.utc).isoformat()

                        creds_data = {
                            "user_id": user_id,
                            "scope": scope or "",
                            "updated_at": now_iso
                        }

                        if refresh_token:
                            creds_data["refresh_token"] = self._encrypt(refresh_token)
                        if access_token:
                            creds_data["access_token"] = access_token
                        if expires_at:
                            creds_data["expires_at"] = expires_at

                        # Upsert logic: update if exists, otherwise insert
                        try:
                            logger.info(f"Checking for existing Google Drive credentials for user: {user_id}")
                            existing = self.supabase.table('google_drive_credentials') \
                                .select('*') \
                                .eq('user_id', user_id) \
                                .execute()
                            logger.info(f"Existing credentials check completed: {len(existing.data) if existing.data else 0} found")

                            if existing.data:
                                logger.info("Updating existing Google Drive credentials...")
                                self.supabase.table('google_drive_credentials').update(creds_data).eq('user_id', user_id).execute()
                                logger.info("Google Drive credentials updated successfully")
                            else:
                                logger.info("Inserting new Google Drive credentials...")
                                creds_data["created_at"] = now_iso
                                self.supabase.table('google_drive_credentials').insert(creds_data).execute()
                                logger.info("Google Drive credentials inserted successfully")

                            # mark saved
                            login_result["ggdrive_saved"] = True
                            logger.info("Google Drive credentials saved successfully")
                        except Exception as e:
                            logger.error(f"Failed to persist google_drive_credentials: {str(e)}", exc_info=True)
                            login_result["ggdrive_saved"] = False

                except Exception as e:
                    logger.error(f"Error while saving Google Drive credentials: {str(e)}")

                logger.info("Returning login_result from handle_google_callback")
                return login_result
            
        except Exception as e:
            logger.error(f"Error handling Google callback: {str(e)}")
            return {
                "EC": 6,
                "EM": f"Google callback error: {str(e)}"
            }
