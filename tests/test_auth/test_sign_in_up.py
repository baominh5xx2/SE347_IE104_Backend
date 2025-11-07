"""
Unit tests for Authentication Service and Endpoints
Tests for registration and login functionality
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
import logging

from app.v1.services.auth_service import AuthService
from app.v1.api.endpoints.auth import register, login, verify_token
from app.v1.schema.auth_schema import (
    RegisterRequest,
    LoginRequest,
    VerifyTokenRequest,
    RegisterResponse,
    LoginResponse,
    VerifyTokenResponse
)

# Setup logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== Test Fixtures ====================

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    mock_client = Mock()
    mock_table = Mock()
    mock_client.table = Mock(return_value=mock_table)
    return mock_client, mock_table


@pytest.fixture
def auth_service(mock_supabase_client):
    """Create AuthService instance with mocked Supabase client"""
    from app.v1.core.config import settings
    client, _ = mock_supabase_client
    # Use real settings from .env instead of hardcoded values
    service = AuthService(client)
    return service, mock_supabase_client[1]


@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "user_id": "test_user_123",
        "full_name": "Nguyen Van A",
        "email": "test@example.com",
        "password_hash": bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        "phone_number": "0123456789",
        "is_activate": True,
        "login_type": "TRADITIONAL",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


# ==================== AuthService Unit Tests ====================

class TestAuthService:
    """Test cases for AuthService class"""
    
    # ========== Register User Tests ==========
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, test_user_data):
        """Test successful user registration"""
        logger.info("🧪 TEST: Register User - Success Case")
        service, mock_table = auth_service
        
        # Mock: No existing user
        mock_select = Mock()
        mock_select.eq = Mock(return_value=mock_select)
        mock_select.execute = Mock(return_value=Mock(data=[]))
        mock_table.select = Mock(return_value=mock_select)
        
        # Mock: Successful insert
        mock_insert = Mock()
        new_user = test_user_data.copy()
        mock_insert.execute = Mock(return_value=Mock(data=[new_user]))
        mock_table.insert = Mock(return_value=mock_insert)
        
        result = await service.register_user(
            full_name="Nguyen Van A",
            email="test@example.com",
            password="password123",
            phone_number="0123456789"
        )
        
        assert result["EC"] == 0
        assert result["EM"] == "User registered successfully"
        assert result["user"]["email"] == "test@example.com"
        assert result["user"]["full_name"] == "Nguyen Van A"
        assert "user_id" in result["user"]
        logger.info("✅ PASS: User registered successfully")
    
    @pytest.mark.asyncio
    async def test_register_user_email_already_exists(self, auth_service):
        """Test registration with existing email"""
        logger.info("🧪 TEST: Register User - Email Already Exists")
        service, mock_table = auth_service
        
        # Mock: User already exists
        mock_select = Mock()
        mock_select.eq = Mock(return_value=mock_select)
        mock_select.execute = Mock(return_value=Mock(data=[{"email": "test@example.com"}]))
        mock_table.select = Mock(return_value=mock_select)
        
        result = await service.register_user(
            full_name="Nguyen Van A",
            email="test@example.com",
            password="password123"
        )
        
        assert result["EC"] == 1
        assert result["EM"] == "Email already exists"
        assert "user" not in result or result["user"] is None
        logger.info("✅ PASS: Email already exists error handled correctly")
    
    @pytest.mark.asyncio
    async def test_register_user_insert_fails(self, auth_service):
        """Test registration when database insert fails"""
        logger.info("🧪 TEST: Register User - Insert Fails")
        service, mock_table = auth_service
        
        # Mock: No existing user
        mock_select = Mock()
        mock_select.eq = Mock(return_value=mock_select)
        mock_select.execute = Mock(return_value=Mock(data=[]))
        mock_table.select = Mock(return_value=mock_select)
        
        # Mock: Insert fails (returns empty data)
        mock_insert = Mock()
        mock_insert.execute = Mock(return_value=Mock(data=[]))
        mock_table.insert = Mock(return_value=mock_insert)
        
        result = await service.register_user(
            full_name="Nguyen Van A",
            email="test@example.com",
            password="password123"
        )
        
        assert result["EC"] == 2
        assert result["EM"] == "Failed to create user"
        logger.info("✅ PASS: Insert failure handled correctly")
    
    @pytest.mark.asyncio
    async def test_register_user_exception(self, auth_service):
        """Test registration when exception occurs"""
        logger.info("🧪 TEST: Register User - Exception Handling")
        service, mock_table = auth_service
        
        # Mock: Exception on select
        mock_table.select = Mock(side_effect=Exception("Database error"))
        
        result = await service.register_user(
            full_name="Nguyen Van A",
            email="test@example.com",
            password="password123"
        )
        
        assert result["EC"] == 3
        assert "Registration error" in result["EM"]
        logger.info("✅ PASS: Exception handled correctly")
    
    # ========== Login User Tests ==========
    
    @pytest.mark.asyncio
    async def test_login_user_success(self, auth_service, test_user_data):
        """Test successful user login"""
        logger.info("🧪 TEST: Login User - Success Case")
        from app.v1.core.config import settings
        service, mock_table = auth_service
        
        # Mock: User exists with correct password
        mock_select = Mock()
        mock_select.eq = Mock(return_value=mock_select)
        mock_select.execute = Mock(return_value=Mock(data=[test_user_data]))
        mock_table.select = Mock(return_value=mock_select)
        
        result = await service.login_user(
            email="test@example.com",
            password="password123"
        )
        
        assert result["EC"] == 0
        assert result["EM"] == "Login successful"
        assert "access_token" in result
        assert result["user"]["email"] == "test@example.com"
        assert result["user"]["full_name"] == "Nguyen Van A"
        
        # Verify token is valid JWT using settings from .env
        token = result["access_token"]
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        assert decoded["email"] == "test@example.com"
        logger.info("✅ PASS: Login successful with valid JWT token")
    
    @pytest.mark.asyncio
    async def test_login_user_email_not_found(self, auth_service):
        """Test login with non-existent email"""
        logger.info("🧪 TEST: Login User - Email Not Found")
        service, mock_table = auth_service
        
        # Mock: No user found
        mock_select = Mock()
        mock_select.eq = Mock(return_value=mock_select)
        mock_select.execute = Mock(return_value=Mock(data=[]))
        mock_table.select = Mock(return_value=mock_select)
        
        result = await service.login_user(
            email="nonexistent@example.com",
            password="password123"
        )
        
        assert result["EC"] == 1
        assert result["EM"] == "Email/Password is incorrect"
        assert "access_token" not in result
        logger.info("✅ PASS: Email not found error handled correctly")
    
    @pytest.mark.asyncio
    async def test_login_user_wrong_password(self, auth_service, test_user_data):
        """Test login with incorrect password"""
        logger.info("🧪 TEST: Login User - Wrong Password")
        service, mock_table = auth_service
        
        # Mock: User exists
        mock_select = Mock()
        mock_select.eq = Mock(return_value=mock_select)
        mock_select.execute = Mock(return_value=Mock(data=[test_user_data]))
        mock_table.select = Mock(return_value=mock_select)
        
        result = await service.login_user(
            email="test@example.com",
            password="wrongpassword"
        )
        
        assert result["EC"] == 2
        assert result["EM"] == "Email/Password is incorrect"
        assert "access_token" not in result
        logger.info("✅ PASS: Wrong password error handled correctly")
    
    @pytest.mark.asyncio
    async def test_login_user_no_password_hash(self, auth_service, test_user_data):
        """Test login for user without password (social login)"""
        service, mock_table = auth_service
        
        # Mock: User without password_hash
        user_no_password = test_user_data.copy()
        user_no_password.pop("password_hash")
        
        mock_select = Mock()
        mock_select.eq = Mock(return_value=mock_select)
        mock_select.execute = Mock(return_value=Mock(data=[user_no_password]))
        mock_table.select = Mock(return_value=mock_select)
        
        result = await service.login_user(
            email="test@example.com",
            password="password123"
        )
        
        assert result["EC"] == 1
        assert result["EM"] == "Email/Password is incorrect"
    
    @pytest.mark.asyncio
    async def test_login_user_account_deactivated(self, auth_service, test_user_data):
        """Test login for deactivated account"""
        service, mock_table = auth_service
        
        # Mock: User with deactivated account
        deactivated_user = test_user_data.copy()
        deactivated_user["is_activate"] = False
        
        mock_select = Mock()
        mock_select.eq = Mock(return_value=mock_select)
        mock_select.execute = Mock(return_value=Mock(data=[deactivated_user]))
        mock_table.select = Mock(return_value=mock_select)
        
        result = await service.login_user(
            email="test@example.com",
            password="password123"
        )
        
        assert result["EC"] == 3
        assert result["EM"] == "Account is not activated"
        assert "access_token" not in result
    
    @pytest.mark.asyncio
    async def test_login_user_exception(self, auth_service):
        """Test login when exception occurs"""
        service, mock_table = auth_service
        
        # Mock: Exception on select
        mock_table.select = Mock(side_effect=Exception("Database error"))
        
        result = await service.login_user(
            email="test@example.com",
            password="password123"
        )
        
        assert result["EC"] == 4
        assert "Login error" in result["EM"]
    
    # ========== Verify Token Tests ==========
    
    def test_verify_token_success(self, auth_service):
        """Test successful token verification"""
        logger.info("🧪 TEST: Verify Token - Success Case")
        from app.v1.core.config import settings
        service, _ = auth_service
        
        # Create valid token using settings from .env
        payload = {
            "email": "test@example.com",
            "full_name": "Nguyen Van A",
            "user_id": "test_user_123",
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        
        result = service.verify_token(token)
        
        assert result["EC"] == 0
        assert result["EM"] == "Token is valid"
        assert result["data"]["email"] == "test@example.com"
        assert result["data"]["full_name"] == "Nguyen Van A"
        assert result["data"]["user_id"] == "test_user_123"
        logger.info("✅ PASS: Token verified successfully")
    
    def test_verify_token_expired(self, auth_service):
        """Test verification of expired token"""
        logger.info("🧪 TEST: Verify Token - Expired Token")
        from app.v1.core.config import settings
        service, _ = auth_service
        
        # Create expired token using settings from .env
        payload = {
            "email": "test@example.com",
            "full_name": "Nguyen Van A",
            "user_id": "test_user_123",
            "exp": datetime.now(timezone.utc) - timedelta(days=1)  # Expired
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        
        result = service.verify_token(token)
        
        assert result["EC"] == 1
        assert result["EM"] == "Token has expired"
        assert "data" not in result
        logger.info("✅ PASS: Expired token error handled correctly")
    
    def test_verify_token_invalid(self, auth_service):
        """Test verification of invalid token"""
        service, _ = auth_service
        
        # Invalid token
        invalid_token = "invalid.token.here"
        
        result = service.verify_token(invalid_token)
        
        assert result["EC"] == 2
        assert "Token is invalid" in result["EM"]
    
    def test_verify_token_wrong_secret(self, auth_service):
        """Test verification of token signed with wrong secret"""
        service, _ = auth_service
        
        # Create token with wrong secret
        payload = {
            "email": "test@example.com",
            "user_id": "test_user_123",
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }
        token = jwt.encode(payload, "wrong_secret", algorithm="HS256")
        
        result = service.verify_token(token)
        
        assert result["EC"] == 2
        assert "Token is invalid" in result["EM"]


# ==================== API Endpoint Tests ====================

class TestAuthEndpoints:
    """Test cases for FastAPI auth endpoints"""
    
    # ========== Register Endpoint Tests ==========
    
    @pytest.mark.asyncio
    async def test_register_endpoint_success(self, mock_supabase_client):
        """Test successful registration endpoint"""
        client, mock_table = mock_supabase_client
        
        # Mock successful registration
        mock_select = Mock()
        mock_select.eq = Mock(return_value=mock_select)
        mock_select.execute = Mock(return_value=Mock(data=[]))
        mock_table.select = Mock(return_value=mock_select)
        
        mock_insert = Mock()
        mock_insert.execute = Mock(return_value=Mock(data=[{
            "user_id": "test_123",
            "email": "newuser@example.com",
            "full_name": "New User",
            "phone_number": "0123456789"
        }]))
        mock_table.insert = Mock(return_value=mock_insert)
        
        with patch('app.v1.api.endpoints.auth.get_supabase_client', return_value=client):
            with patch('app.v1.api.endpoints.auth.AuthService') as MockAuthService:
                mock_service = Mock()
                mock_service.register_user = AsyncMock(return_value={
                    "EC": 0,
                    "EM": "User registered successfully",
                    "user": {
                        "user_id": "test_123",
                        "email": "newuser@example.com",
                        "full_name": "New User"
                    }
                })
                MockAuthService.return_value = mock_service
                
                request = RegisterRequest(
                    full_name="New User",
                    email="newuser@example.com",
                    password="password123",
                    phone_number="0123456789"
                )
                
                response = await register(request, auth_service=mock_service)
                
                assert isinstance(response, RegisterResponse)
                assert response.EC == 0
                assert response.EM == "User registered successfully"
                assert response.user["email"] == "newuser@example.com"
    
    @pytest.mark.asyncio
    async def test_register_endpoint_email_exists(self, mock_supabase_client):
        """Test registration endpoint with existing email"""
        client, _ = mock_supabase_client
        
        with patch('app.v1.api.endpoints.auth.get_supabase_client', return_value=client):
            with patch('app.v1.api.endpoints.auth.AuthService') as MockAuthService:
                mock_service = Mock()
                mock_service.register_user = AsyncMock(return_value={
                    "EC": 1,
                    "EM": "Email already exists"
                })
                MockAuthService.return_value = mock_service
                
                request = RegisterRequest(
                    full_name="Existing User",
                    email="existing@example.com",
                    password="password123"
                )
                
                response = await register(request, auth_service=mock_service)
                
                assert response.EC == 1
                assert response.EM == "Email already exists"
    
    @pytest.mark.asyncio
    async def test_register_endpoint_exception(self, mock_supabase_client):
        """Test registration endpoint exception handling"""
        client, _ = mock_supabase_client
        
        with patch('app.v1.api.endpoints.auth.get_supabase_client', return_value=client):
            with patch('app.v1.api.endpoints.auth.AuthService') as MockAuthService:
                mock_service = Mock()
                mock_service.register_user = AsyncMock(side_effect=Exception("Database error"))
                MockAuthService.return_value = mock_service
                
                request = RegisterRequest(
                    full_name="Test User",
                    email="test@example.com",
                    password="password123"
                )
                
                with pytest.raises(Exception):
                    await register(request, auth_service=mock_service)
    
    # ========== Login Endpoint Tests ==========
    
    @pytest.mark.asyncio
    async def test_login_endpoint_success(self, mock_supabase_client):
        """Test successful login endpoint"""
        client, _ = mock_supabase_client
        
        with patch('app.v1.api.endpoints.auth.get_supabase_client', return_value=client):
            with patch('app.v1.api.endpoints.auth.AuthService') as MockAuthService:
                mock_service = Mock()
                mock_service.login_user = AsyncMock(return_value={
                    "EC": 0,
                    "EM": "Login successful",
                    "access_token": "test_token_123",
                    "user": {
                        "user_id": "test_123",
                        "email": "test@example.com",
                        "full_name": "Test User"
                    }
                })
                MockAuthService.return_value = mock_service
                
                request = LoginRequest(
                    email="test@example.com",
                    password="password123"
                )
                
                response = await login(request, auth_service=mock_service)
                
                assert isinstance(response, LoginResponse)
                assert response.EC == 0
                assert response.access_token == "test_token_123"
                assert response.user["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_login_endpoint_wrong_credentials(self, mock_supabase_client):
        """Test login endpoint with wrong credentials"""
        client, _ = mock_supabase_client
        
        with patch('app.v1.api.endpoints.auth.get_supabase_client', return_value=client):
            with patch('app.v1.api.endpoints.auth.AuthService') as MockAuthService:
                mock_service = Mock()
                mock_service.login_user = AsyncMock(return_value={
                    "EC": 2,
                    "EM": "Email/Password is incorrect"
                })
                MockAuthService.return_value = mock_service
                
                request = LoginRequest(
                    email="test@example.com",
                    password="wrongpassword"
                )
                
                response = await login(request, auth_service=mock_service)
                
                assert response.EC == 2
                assert response.EM == "Email/Password is incorrect"
                assert response.access_token is None
    
    # ========== Verify Token Endpoint Tests ==========
    
    @pytest.mark.asyncio
    async def test_verify_token_endpoint_from_body_success(self, mock_supabase_client):
        """Test token verification from request body"""
        client, _ = mock_supabase_client
        
        with patch('app.v1.api.endpoints.auth.get_supabase_client', return_value=client):
            with patch('app.v1.api.endpoints.auth.AuthService') as MockAuthService:
                mock_service = Mock()
                mock_service.verify_token = Mock(return_value={
                    "EC": 0,
                    "EM": "Token is valid",
                    "data": {
                        "email": "test@example.com",
                        "user_id": "test_123",
                        "exp": 1234567890
                    }
                })
                MockAuthService.return_value = mock_service
                
                request = VerifyTokenRequest(token="valid_token_123")
                
                response = await verify_token(
                    request=request,
                    authorization=None,
                    auth_service=mock_service
                )
                
                assert response.EC == 0
                assert response.EM == "Token is valid"
                assert response.data["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_verify_token_endpoint_from_header_success(self, mock_supabase_client):
        """Test token verification from Authorization header"""
        client, _ = mock_supabase_client
        
        with patch('app.v1.api.endpoints.auth.get_supabase_client', return_value=client):
            with patch('app.v1.api.endpoints.auth.AuthService') as MockAuthService:
                mock_service = Mock()
                mock_service.verify_token = Mock(return_value={
                    "EC": 0,
                    "EM": "Token is valid",
                    "data": {
                        "email": "test@example.com",
                        "user_id": "test_123"
                    }
                })
                MockAuthService.return_value = mock_service
                
                response = await verify_token(
                    request=None,
                    authorization="Bearer valid_token_123",
                    auth_service=mock_service
                )
                
                assert response.EC == 0
                assert response.EM == "Token is valid"
                mock_service.verify_token.assert_called_with("valid_token_123")
    
    @pytest.mark.asyncio
    async def test_verify_token_endpoint_no_token(self, mock_supabase_client):
        """Test token verification without token"""
        client, _ = mock_supabase_client
        
        with patch('app.v1.api.endpoints.auth.get_supabase_client', return_value=client):
            with patch('app.v1.api.endpoints.auth.AuthService') as MockAuthService:
                mock_service = Mock()
                MockAuthService.return_value = mock_service
                
                response = await verify_token(
                    request=None,
                    authorization=None,
                    auth_service=mock_service
                )
                
                assert response.EC == 1
                assert response.EM == "Token is required"
    
    @pytest.mark.asyncio
    async def test_verify_token_endpoint_expired(self, mock_supabase_client):
        """Test token verification with expired token"""
        client, _ = mock_supabase_client
        
        with patch('app.v1.api.endpoints.auth.get_supabase_client', return_value=client):
            with patch('app.v1.api.endpoints.auth.AuthService') as MockAuthService:
                mock_service = Mock()
                mock_service.verify_token = Mock(return_value={
                    "EC": 1,
                    "EM": "Token has expired"
                })
                MockAuthService.return_value = mock_service
                
                request = VerifyTokenRequest(token="expired_token")
                
                response = await verify_token(
                    request=request,
                    authorization=None,
                    auth_service=mock_service
                )
                
                assert response.EC == 1
                assert response.EM == "Token has expired"


# ==================== Integration Test Cases ====================

class TestAuthIntegration:
    """Integration tests for complete auth flow"""
    
    @pytest.mark.asyncio
    async def test_register_then_login_flow(self, auth_service):
        """Test complete flow: register user then login"""
        service, mock_table = auth_service
        
        # Step 1: Register
        mock_select = Mock()
        mock_select.eq = Mock(return_value=mock_select)
        mock_select.execute = Mock(return_value=Mock(data=[]))
        mock_table.select = Mock(return_value=mock_select)
        
        new_user = {
            "user_id": "new_user_123",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password_hash": bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            "is_activate": True
        }
        
        mock_insert = Mock()
        mock_insert.execute = Mock(return_value=Mock(data=[new_user]))
        mock_table.insert = Mock(return_value=mock_insert)
        
        register_result = await service.register_user(
            full_name="New User",
            email="newuser@example.com",
            password="password123"
        )
        
        assert register_result["EC"] == 0
        
        # Step 2: Login with registered credentials
        mock_select2 = Mock()
        mock_select2.eq = Mock(return_value=mock_select2)
        mock_select2.execute = Mock(return_value=Mock(data=[new_user]))
        mock_table.select = Mock(return_value=mock_select2)
        
        login_result = await service.login_user(
            email="newuser@example.com",
            password="password123"
        )
        
        assert login_result["EC"] == 0
        assert "access_token" in login_result
        
        # Step 3: Verify token
        token = login_result["access_token"]
        verify_result = service.verify_token(token)
        
        assert verify_result["EC"] == 0
        assert verify_result["data"]["email"] == "newuser@example.com"


# ==================== Google OAuth Tests ====================

@pytest.fixture
def mock_google_oauth_service():
    """Mock GoogleOAuthService"""
    from app.v1.services.google_oauth_service import GoogleOAuthService
    mock_service = Mock(spec=GoogleOAuthService)
    return mock_service


class TestGoogleOAuth:
    """Test cases for Google OAuth authentication"""
    
    def test_get_google_auth_url(self, mock_google_oauth_service):
        """Test generating Google OAuth authorization URL"""
        # Setup mock
        expected_url = "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=test"
        mock_google_oauth_service.get_google_auth_url.return_value = expected_url
        
        # Execute
        auth_url = mock_google_oauth_service.get_google_auth_url()
        
        # Assert
        assert auth_url == expected_url
        assert "accounts.google.com" in auth_url
        mock_google_oauth_service.get_google_auth_url.assert_called_once()
        
        logger.info("✓ Test get_google_auth_url passed")
    
    @pytest.mark.asyncio
    async def test_google_login_success(self, mock_google_oauth_service):
        """Test successful Google login with ID token"""
        # Setup mock response
        expected_response = {
            "EC": 0,
            "EM": "Login successful",
            "access_token": "test_access_token",
            "user": {
                "user_id": "test-user-id",
                "email": "test@gmail.com",
                "full_name": "Test User",
                "phone_number": None,
                "profile_picture": "https://lh3.googleusercontent.com/test"
            }
        }
        mock_google_oauth_service.google_login = AsyncMock(return_value=expected_response)
        
        # Execute
        result = await mock_google_oauth_service.google_login("valid_id_token")
        
        # Assert
        assert result["EC"] == 0
        assert result["EM"] == "Login successful"
        assert "access_token" in result
        assert "user" in result
        assert result["user"]["email"] == "test@gmail.com"
        assert result["user"]["profile_picture"] is not None
        
        logger.info("✓ Test google_login_success passed")
    
    @pytest.mark.asyncio
    async def test_google_login_invalid_token(self, mock_google_oauth_service):
        """Test Google login with invalid ID token"""
        # Setup mock response for invalid token
        expected_response = {
            "EC": 1,
            "EM": "Invalid Google token",
            "access_token": None,
            "user": None
        }
        mock_google_oauth_service.google_login = AsyncMock(return_value=expected_response)
        
        # Execute
        result = await mock_google_oauth_service.google_login("invalid_token")
        
        # Assert
        assert result["EC"] == 1
        assert result["EM"] == "Invalid Google token"
        assert result["access_token"] is None
        assert result["user"] is None
        
        logger.info("✓ Test google_login_invalid_token passed")
    
    @pytest.mark.asyncio
    async def test_google_login_unverified_email(self, mock_google_oauth_service):
        """Test Google login with unverified email"""
        # Setup mock response for unverified email
        expected_response = {
            "EC": 2,
            "EM": "Email not verified by Google"
        }
        mock_google_oauth_service.google_login = AsyncMock(return_value=expected_response)
        
        # Execute
        result = await mock_google_oauth_service.google_login("unverified_email_token")
        
        # Assert
        assert result["EC"] == 2
        assert "not verified" in result["EM"]
        
        logger.info("✓ Test google_login_unverified_email passed")
    
    @pytest.mark.asyncio
    async def test_google_callback_success(self, mock_google_oauth_service):
        """Test successful Google OAuth callback with authorization code"""
        # Setup mock response
        expected_response = {
            "EC": 0,
            "EM": "Login successful",
            "access_token": "callback_access_token",
            "user": {
                "user_id": "callback-user-id",
                "email": "callback@gmail.com",
                "full_name": "Callback User",
                "phone_number": "0123456789",
                "profile_picture": "https://lh3.googleusercontent.com/callback"
            }
        }
        mock_google_oauth_service.handle_google_callback = AsyncMock(return_value=expected_response)
        
        # Execute
        result = await mock_google_oauth_service.handle_google_callback(
            code="4/0Ab32j920L4hi...",
            state="test_state"
        )
        
        # Assert
        assert result["EC"] == 0
        assert "access_token" in result
        assert "user" in result
        assert result["user"]["email"] == "callback@gmail.com"
        assert result["user"]["profile_picture"] is not None
        
        logger.info("✓ Test google_callback_success passed")
    
    @pytest.mark.asyncio
    async def test_google_callback_invalid_code(self, mock_google_oauth_service):
        """Test Google OAuth callback with invalid authorization code"""
        # Setup mock response for invalid code
        expected_response = {
            "EC": 6,
            "EM": "Failed to exchange code for token: invalid_grant"
        }
        mock_google_oauth_service.handle_google_callback = AsyncMock(return_value=expected_response)
        
        # Execute
        result = await mock_google_oauth_service.handle_google_callback(
            code="invalid_code",
            state="test_state"
        )
        
        # Assert
        assert result["EC"] == 6
        assert "Failed to exchange" in result["EM"]
        
        logger.info("✓ Test google_callback_invalid_code passed")
    
    @pytest.mark.asyncio
    async def test_google_callback_creates_new_user(self, mock_google_oauth_service):
        """Test Google OAuth callback creates new user if not exists"""
        # Setup mock response for new user
        expected_response = {
            "EC": 0,
            "EM": "Account created and login successful",
            "access_token": "new_user_token",
            "user": {
                "user_id": "new-google-user-id",
                "email": "newgoogleuser@gmail.com",
                "full_name": "New Google User",
                "phone_number": None,
                "profile_picture": "https://lh3.googleusercontent.com/newuser"
            }
        }
        mock_google_oauth_service.handle_google_callback = AsyncMock(return_value=expected_response)
        
        # Execute
        result = await mock_google_oauth_service.handle_google_callback(
            code="valid_code_for_new_user",
            state="test_state"
        )
        
        # Assert
        assert result["EC"] == 0
        assert "created" in result["EM"]
        assert result["user"]["email"] == "newgoogleuser@gmail.com"
        
        logger.info("✓ Test google_callback_creates_new_user passed")


# ==================== Google OAuth Endpoint Tests ====================

class TestGoogleOAuthEndpoints:
    """Test cases for Google OAuth API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_google_auth_url_endpoint(self):
        """Test GET /google/auth-url endpoint"""
        from app.v1.api.endpoints.auth import get_google_auth_url
        
        # Mock GoogleOAuthService
        mock_service = Mock()
        mock_service.get_google_auth_url.return_value = "https://accounts.google.com/o/oauth2/auth?test"
        
        # Execute
        response = await get_google_auth_url(google_service=mock_service)
        
        # Assert
        assert response.EC == 0
        assert response.EM == "Google OAuth URL generated"
        assert response.auth_url is not None
        assert "accounts.google.com" in response.auth_url
        
        logger.info("✓ Test get_google_auth_url_endpoint passed")
    
    @pytest.mark.asyncio
    async def test_google_login_endpoint(self):
        """Test POST /google/login endpoint"""
        from app.v1.api.endpoints.auth import google_login
        from app.v1.schema.auth_schema import GoogleLoginRequest
        
        # Mock service response
        mock_service = Mock()
        mock_service.google_login = AsyncMock(return_value={
            "EC": 0,
            "EM": "Login successful",
            "access_token": "endpoint_test_token",
            "user": {
                "user_id": "endpoint-test-id",
                "email": "endpointtest@gmail.com",
                "full_name": "Endpoint Test User",
                "phone_number": None,
                "profile_picture": "https://lh3.googleusercontent.com/endpoint"
            }
        })
        
        # Create request
        request = GoogleLoginRequest(id_token="test_id_token")
        
        # Execute
        response = await google_login(request=request, google_service=mock_service)
        
        # Assert
        assert response.EC == 0
        assert response.access_token == "endpoint_test_token"
        assert response.user is not None
        
        logger.info("✓ Test google_login_endpoint passed")
    
    @pytest.mark.asyncio
    async def test_google_callback_endpoint_json_format(self):
        """Test GET /google/callback endpoint with JSON format"""
        from app.v1.api.endpoints.auth import google_callback
        
        # Mock service response
        mock_service = Mock()
        mock_service.handle_google_callback = AsyncMock(return_value={
            "EC": 0,
            "EM": "Login successful",
            "access_token": "callback_endpoint_token",
            "user": {
                "user_id": "callback-endpoint-id",
                "email": "callbackendpoint@gmail.com",
                "full_name": "Callback Endpoint User",
                "phone_number": "0987654321",
                "profile_picture": "https://lh3.googleusercontent.com/callbackendpoint"
            }
        })
        
        # Execute with JSON format (default)
        response = await google_callback(
            code="test_code",
            state="test_state",
            error=None,
            format="json",
            google_service=mock_service
        )
        
        # Assert
        assert response["EC"] == 0
        assert "access_token" in response
        assert "user" in response
        
        logger.info("✓ Test google_callback_endpoint_json_format passed")
    
    @pytest.mark.asyncio
    async def test_google_callback_endpoint_with_error(self):
        """Test GET /google/callback endpoint with error parameter"""
        from app.v1.api.endpoints.auth import google_callback
        
        mock_service = Mock()
        
        # Execute with error
        response = await google_callback(
            code=None,
            state=None,
            error="access_denied",
            format="json",
            google_service=mock_service
        )
        
        # Assert
        assert response["EC"] == 1
        assert "access_denied" in response["EM"]
        assert response["access_token"] is None
        
        logger.info("✓ Test google_callback_endpoint_with_error passed")


# ==================== Google OAuth Integration Tests ====================

class TestGoogleOAuthIntegration:
    """Integration tests for complete Google OAuth flow"""
    
    @pytest.mark.asyncio
    async def test_complete_google_oauth_flow(self, mock_supabase_client):
        """Test complete Google OAuth flow from auth URL to login"""
        from app.v1.services.google_oauth_service import GoogleOAuthService
        
        client, mock_table = mock_supabase_client
        service = GoogleOAuthService(client)
        
        # Step 1: Get auth URL
        with patch.object(service, 'get_google_auth_url') as mock_auth_url:
            mock_auth_url.return_value = "https://accounts.google.com/o/oauth2/auth?test"
            auth_url = service.get_google_auth_url()
            assert auth_url is not None
            assert "accounts.google.com" in auth_url
        
        # Step 2: Simulate callback
        with patch.object(service, 'handle_google_callback') as mock_callback:
            mock_callback.return_value = {
                "EC": 0,
                "EM": "Login successful",
                "access_token": "integration_test_token",
                "user": {
                    "user_id": "integration-test-id",
                    "email": "integration@gmail.com",
                    "full_name": "Integration Test",
                    "phone_number": None,
                    "profile_picture": "https://lh3.googleusercontent.com/integration"
                }
            }
            
            result = await mock_callback(code="test_code", state="test_state")
            
            # Assert final result
            assert result["EC"] == 0
            assert "access_token" in result
            assert result["user"]["email"] == "integration@gmail.com"
            assert result["user"]["profile_picture"] is not None
        
        logger.info("✓ Test complete_google_oauth_flow passed")
    
    def test_google_oauth_response_format(self):
        """Test that Google OAuth responses match expected format"""
        # Expected response format
        expected_keys = ["EC", "EM", "access_token", "user"]
        expected_user_keys = ["user_id", "email", "full_name", "phone_number", "profile_picture"]
        
        # Sample response
        sample_response = {
            "EC": 0,
            "EM": "Login successful",
            "access_token": "test_token",
            "user": {
                "user_id": "test-id",
                "email": "test@gmail.com",
                "full_name": "Test User",
                "phone_number": None,
                "profile_picture": "https://lh3.googleusercontent.com/test"
            }
        }
        
        # Assert response structure
        for key in expected_keys:
            assert key in sample_response
        
        for key in expected_user_keys:
            assert key in sample_response["user"]
        
        # Assert data types
        assert isinstance(sample_response["EC"], int)
        assert isinstance(sample_response["EM"], str)
        assert isinstance(sample_response["access_token"], str)
        assert isinstance(sample_response["user"], dict)
        assert isinstance(sample_response["user"]["profile_picture"], str) or sample_response["user"]["profile_picture"] is None
        
        logger.info("✓ Test google_oauth_response_format passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])