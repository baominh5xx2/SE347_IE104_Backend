"""
Authentication Service
Handles user registration, login, and token verification
"""
import logging
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from supabase import Client
from ..core.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user management"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize AuthService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        self.jwt_secret = settings.JWT_SECRET
        self.jwt_expire = settings.JWT_EXPIRE
        self.salt_rounds = 10
    
    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        salt = bcrypt.gensalt(rounds=self.salt_rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify password against hashed password
        
        Args:
            password: Plain text password
            hashed_password: Hashed password from database
            
        Returns:
            bool: True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False
    
    def _generate_access_token(self, user_data: Dict[str, Any]) -> str:
        """
        Generate JWT access token
        
        Args:
            user_data: User data to include in token payload (must include email, full_name, user_id, role)
            
        Returns:
            str: JWT access token
        """
        payload = {
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "user_id": user_data["user_id"],
            "role": user_data.get("role", "user"),  # Include role in JWT
            "exp": datetime.now(timezone.utc) + timedelta(days=self.jwt_expire)
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token
    
    async def register_user(
        self,
        full_name: str,
        email: str,
        password: str,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new user
        
        Args:
            full_name: User's full name
            email: User's email address
            password: User's password
            phone_number: Optional phone number
            
        Returns:
            Dict containing registration result
        """
        try:
            # Check if user already exists
            existing_user = self.supabase.table('users') \
                .select("*") \
                .eq('email', email) \
                .execute()
            
            if existing_user.data:
                return {
                    "EC": 1,
                    "EM": "Email already exists"
                }
            
            # Hash password
            hashed_password = self._hash_password(password)
            
            # Create user in database
            user_data = {
                "full_name": full_name,
                "email": email,
                "password_hash": hashed_password,
                "phone_number": phone_number,
                "is_activate": True,
                "login_type": "TRADITIONAL",
                "security_2fa_enabled": False,
                "role": "user",  # Default role for new users
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table('users').insert(user_data).execute()
            
            if result.data:
                user = result.data[0]
                return {
                    "EC": 0,
                    "EM": "User registered successfully",
                    "user": {
                        "user_id": user["user_id"],
                        "email": user["email"],
                        "full_name": user["full_name"],
                        "phone_number": user.get("phone_number")
                    }
                }
            else:
                return {
                    "EC": 2,
                    "EM": "Failed to create user"
                }
                
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            return {
                "EC": 3,
                "EM": f"Registration error: {str(e)}"
            }
    
    async def login_user(
        self, 
        password: str,
        email: Optional[str] = None, 
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user and generate access token
        Can login with either email or phone_number
        
        Args:
            password: User's password
            email: User's email address (optional)
            phone_number: User's phone number (optional)
            
        Returns:
            Dict containing login result with access token
        """
        try:
            # Validate that at least one identifier is provided
            if not email and not phone_number:
                return {
                    "EC": 1,
                    "EM": "Either email or phone_number must be provided"
                }
            
            # Fetch user by email or phone_number
            query = self.supabase.table('users').select("*")
            
            if email:
                query = query.eq('email', email)
            else:
                query = query.eq('phone_number', phone_number)
            
            result = query.execute()
            
            if not result.data:
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }
            
            user = result.data[0]
            
            # Check if user has password (TRADITIONAL login)
            if not user.get('password_hash'):
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }
            
            # Verify password
            if not self._verify_password(password, user['password_hash']):
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }
            
            # Check if account is activated
            if not user.get('is_activate', True):
                return {
                    "EC": 3,
                    "EM": "Account is not activated"
                }
            
            # Get user role (default to 'user' if not set)
            role = user.get('role', 'user')
            
            # Generate access token
            access_token = self._generate_access_token({
                "email": user["email"],
                "full_name": user["full_name"],
                "user_id": user["user_id"],
                "role": role
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
                    "role": role
                }
            }
            
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return {
                "EC": 4,
                "EM": f"Login error: {str(e)}"
            }
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT access token
        
        Args:
            token: JWT access token
            
        Returns:
            Dict containing verification result
        """
        try:
            decoded = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return {
                "EC": 0,
                "EM": "Token is valid",
                "data": {
                    "email": decoded.get("email"),
                    "full_name": decoded.get("full_name"),
                    "user_id": decoded.get("user_id"),
                    "role": decoded.get("role", "user"),  # Include role from JWT
                    "exp": decoded.get("exp")
                }
            }
        except jwt.ExpiredSignatureError:
            return {
                "EC": 1,
                "EM": "Token has expired"
            }
        except jwt.InvalidTokenError as e:
            return {
                "EC": 2,
                "EM": f"Token is invalid: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            return {
                "EC": 3,
                "EM": f"Token verification error: {str(e)}"
            }
    
    def get_user_role(self, user_id: str) -> Optional[str]:
        """
        Get user role from database
        
        Args:
            user_id: UUID of the user
            
        Returns:
            User role ('user' or 'admin') or None if user doesn't exist
        """
        try:
            result = self.supabase.table('users') \
                .select('role') \
                .eq('user_id', user_id) \
                .execute()
            
            if not result.data:
                logger.warning(f"User {user_id} not found")
                return None
            
            role = result.data[0].get('role', 'user')
            return role
            
        except Exception as e:
            logger.error(f"Error getting user role for {user_id}: {str(e)}")
            return None
    
    def get_user_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user role and active status from database
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dict with role and is_active, or None if user doesn't exist
        """
        try:
            result = self.supabase.table('users') \
                .select('role, is_active') \
                .eq('user_id', user_id) \
                .execute()
            
            if not result.data:
                logger.warning(f"User {user_id} not found")
                return None
            
            user = result.data[0]
            return {
                'role': user.get('role', 'user'),
                'is_active': user.get('is_active', True)
            }
            
        except Exception as e:
            logger.error(f"Error getting user status for {user_id}: {str(e)}")
            return None
    
    async def register_admin(
        self,
        full_name: str,
        email: str,
        password: str,
        phone_number: Optional[str] = None,
        admin_secret_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new admin user
        
        Args:
            full_name: Admin's full name
            email: Admin's email address
            password: Admin's password
            phone_number: Optional phone number
            admin_secret_key: Secret key để verify quyền tạo admin (optional, có thể check từ config)
            
        Returns:
            Dict containing registration result
        """
        try:
            # Check if admin secret key is required and valid
            # Có thể check từ config hoặc environment variable
            from ..core.config import settings
            required_secret = getattr(settings, 'ADMIN_SECRET_KEY', None)
            
            if required_secret and admin_secret_key != required_secret:
                return {
                    "EC": 1,
                    "EM": "Invalid admin secret key"
                }
            
            # Check if user already exists
            existing_user = self.supabase.table('users') \
                .select("*") \
                .eq('email', email) \
                .execute()
            
            if existing_user.data:
                return {
                    "EC": 2,
                    "EM": "Email already exists"
                }
            
            # Hash password
            hashed_password = self._hash_password(password)
            
            # Create admin user in database
            user_data = {
                "full_name": full_name,
                "email": email,
                "password_hash": hashed_password,
                "phone_number": phone_number,
                "is_activate": True,
                "login_type": "TRADITIONAL",
                "security_2fa_enabled": False,
                "role": "admin",  # Set role as admin
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table('users').insert(user_data).execute()
            
            if result.data:
                user = result.data[0]
                return {
                    "EC": 0,
                    "EM": "Admin registered successfully",
                    "user": {
                        "user_id": user["user_id"],
                        "email": user["email"],
                        "full_name": user["full_name"],
                        "phone_number": user.get("phone_number"),
                        "role": user.get("role", "admin")
                    }
                }
            else:
                return {
                    "EC": 3,
                    "EM": "Failed to create admin user"
                }
                
        except Exception as e:
            logger.error(f"Error registering admin: {str(e)}")
            return {
                "EC": 4,
                "EM": f"Admin registration error: {str(e)}"
            }
    
    async def login_admin(
        self,
        password: str,
        email: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate admin user and generate access token
        Verify user có role = 'admin' sau khi login thành công
        
        Args:
            password: Admin's password
            email: Admin's email address (optional)
            phone_number: Admin's phone number (optional)
            
        Returns:
            Dict containing login result with access token
        """
        try:
            # Validate that at least one identifier is provided
            if not email and not phone_number:
                return {
                    "EC": 1,
                    "EM": "Either email or phone_number must be provided"
                }
            
            # Fetch user by email or phone_number
            query = self.supabase.table('users').select("*")
            
            if email:
                query = query.eq('email', email)
            else:
                query = query.eq('phone_number', phone_number)
            
            result = query.execute()
            
            if not result.data:
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }
            
            user = result.data[0]
            
            # Check if user has password (TRADITIONAL login)
            if not user.get('password_hash'):
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }
            
            # Verify password
            if not self._verify_password(password, user['password_hash']):
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }
            
            # Check if account is activated
            if not user.get('is_activate', True):
                return {
                    "EC": 3,
                    "EM": "Account is not activated"
                }
            
            # Verify user is admin
            role = user.get('role', 'user')
            if role != 'admin':
                return {
                    "EC": 4,
                    "EM": "Access denied. Admin privileges required."
                }
            
            # Generate access token
            access_token = self._generate_access_token({
                "email": user["email"],
                "full_name": user["full_name"],
                "user_id": user["user_id"],
                "role": role
            })
            
            return {
                "EC": 0,
                "EM": "Admin login successful",
                "access_token": access_token,
                "user": {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "phone_number": user.get("phone_number"),
                    "role": role
                }
            }
            
        except Exception as e:
            logger.error(f"Error during admin login: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Admin login error: {str(e)}"
            }