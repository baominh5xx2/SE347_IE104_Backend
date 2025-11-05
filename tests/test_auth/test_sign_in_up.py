"""
Unit tests for Authentication Service and Endpoints
Tests for registration and login functionality
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt

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
    client, _ = mock_supabase_client
    with patch('app.v1.services.auth_service.settings') as mock_settings:
        mock_settings.JWT_SECRET = "test_secret_key"
        mock_settings.JWT_EXPIRE = 7
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
    
    @pytest.mark.asyncio
    async def test_register_user_email_already_exists(self, auth_service):
        """Test registration with existing email"""
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
    
    @pytest.mark.asyncio
    async def test_register_user_insert_fails(self, auth_service):
        """Test registration when database insert fails"""
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
    
    @pytest.mark.asyncio
    async def test_register_user_exception(self, auth_service):
        """Test registration when exception occurs"""
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
    
    # ========== Login User Tests ==========
    
    @pytest.mark.asyncio
    async def test_login_user_success(self, auth_service, test_user_data):
        """Test successful user login"""
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
        
        # Verify token is valid JWT
        token = result["access_token"]
        decoded = jwt.decode(token, "test_secret_key", algorithms=["HS256"])
        assert decoded["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_login_user_email_not_found(self, auth_service):
        """Test login with non-existent email"""
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
    
    @pytest.mark.asyncio
    async def test_login_user_wrong_password(self, auth_service, test_user_data):
        """Test login with incorrect password"""
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
        service, _ = auth_service
        
        # Create valid token
        payload = {
            "email": "test@example.com",
            "full_name": "Nguyen Van A",
            "user_id": "test_user_123",
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }
        token = jwt.encode(payload, "test_secret_key", algorithm="HS256")
        
        result = service.verify_token(token)
        
        assert result["EC"] == 0
        assert result["EM"] == "Token is valid"
        assert result["data"]["email"] == "test@example.com"
        assert result["data"]["full_name"] == "Nguyen Van A"
        assert result["data"]["user_id"] == "test_user_123"
    
    def test_verify_token_expired(self, auth_service):
        """Test verification of expired token"""
        service, _ = auth_service
        
        # Create expired token
        payload = {
            "email": "test@example.com",
            "full_name": "Nguyen Van A",
            "user_id": "test_user_123",
            "exp": datetime.now(timezone.utc) - timedelta(days=1)  # Expired
        }
        token = jwt.encode(payload, "test_secret_key", algorithm="HS256")
        
        result = service.verify_token(token)
        
        assert result["EC"] == 1
        assert result["EM"] == "Token has expired"
        assert "data" not in result
    
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

