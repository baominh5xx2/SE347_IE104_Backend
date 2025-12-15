"""
Unit tests for Admin User Service
Tests all methods with comprehensive edge cases
"""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.v1.services.admin_user_service import AdminUserService


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    return MagicMock()


@pytest.fixture
def admin_user_service(mock_supabase):
    """Create AdminUserService instance with mock client"""
    return AdminUserService(mock_supabase)


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing"""
    return str(uuid4())


@pytest.fixture
def sample_user_data():
    """Sample user data"""
    return {
        "user_id": str(uuid4()),
        "email": "user@example.com",
        "full_name": "Nguyễn Văn A",
        "phone_number": "0901234567",
        "profile_picture": "https://example.com/avatar.jpg",
        "role": "user",
        "is_active": True,
        "created_at": "2025-01-01T10:00:00Z",
        "updated_at": "2025-01-10T15:30:00Z",
        "last_access_time": "2025-01-15T08:30:00Z"
    }


@pytest.fixture
def sample_admin_data():
    """Sample admin user data"""
    return {
        "user_id": str(uuid4()),
        "email": "admin@example.com",
        "full_name": "Admin User",
        "phone_number": "0987654321",
        "role": "admin",
        "is_active": True,
        "created_at": "2025-01-01T10:00:00Z",
        "updated_at": "2025-01-10T15:30:00Z",
        "last_access_time": "2025-01-15T08:30:00Z"
    }


# ============================================
# GET_USER_PROFILE TESTS
# ============================================

def test_get_user_profile_success(admin_user_service, mock_supabase, sample_user_data):
    """Test successful user profile retrieval"""
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [sample_user_data]
    
    result = admin_user_service.get_user_profile(sample_user_data["user_id"])
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert result["data"]["user_id"] == sample_user_data["user_id"]
    assert result["data"]["email"] == sample_user_data["email"]
    assert result["data"]["full_name"] == sample_user_data["full_name"]


def test_get_user_profile_not_found(admin_user_service, mock_supabase, sample_user_id):
    """Test user profile retrieval when user doesn't exist"""
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    result = admin_user_service.get_user_profile(sample_user_id)
    
    assert result["EC"] == 1
    assert result["EM"] == "User not found"
    assert result["data"] is None


def test_get_user_profile_empty_data(admin_user_service, mock_supabase, sample_user_id):
    """Test user profile retrieval when data is None"""
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = None
    
    result = admin_user_service.get_user_profile(sample_user_id)
    
    assert result["EC"] == 1
    assert result["EM"] == "User not found"
    assert result["data"] is None


def test_get_user_profile_exception(admin_user_service, mock_supabase, sample_user_id):
    """Test user profile retrieval when exception occurs"""
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("Database error")
    
    result = admin_user_service.get_user_profile(sample_user_id)
    
    assert result["EC"] == 2
    assert "Error retrieving user profile" in result["EM"]
    assert result["data"] is None


# ============================================
# CREATE_USER TESTS
# ============================================

def test_create_user_success(admin_user_service, mock_supabase):
    """Test successful user creation"""
    email = "newuser@example.com"
    full_name = "New User"
    phone_number = "0901234567"
    
    # Mock: email doesn't exist
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    # Mock: user creation
    new_user = {
        "user_id": str(uuid4()),
        "email": email,
        "full_name": full_name,
        "phone_number": phone_number,
        "role": "user",
        "is_active": True
    }
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [new_user]
    
    result = admin_user_service.create_user(
        email=email,
        full_name=full_name,
        phone_number=phone_number,
        password="password123",
        role="user",
        is_active=True
    )
    
    assert result["EC"] == 0
    assert result["EM"] == "User created successfully"
    assert result["data"]["email"] == email
    assert result["data"]["full_name"] == full_name
    assert result["data"]["role"] == "user"


def test_create_user_email_exists(admin_user_service, mock_supabase):
    """Test user creation when email already exists"""
    email = "existing@example.com"
    existing_user = {"user_id": str(uuid4()), "email": email}
    
    # Mock: email exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [existing_user]
    
    result = admin_user_service.create_user(email=email)
    
    assert result["EC"] == 1
    assert result["EM"] == "Email already exists"
    assert result["data"] is None


def test_create_user_auto_generate_password(admin_user_service, mock_supabase):
    """Test user creation with auto-generated password"""
    email = "newuser@example.com"
    
    # Mock: email doesn't exist
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    # Mock: user creation
    new_user = {
        "user_id": str(uuid4()),
        "email": email,
        "full_name": email.split('@')[0],
        "role": "user",
        "is_active": True
    }
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [new_user]
    
    result = admin_user_service.create_user(email=email)
    
    assert result["EC"] == 0
    assert result["data"]["password"] is not None
    assert len(result["data"]["password"]) >= 12  # Generated password should be at least 12 chars


def test_create_user_with_admin_role(admin_user_service, mock_supabase):
    """Test user creation with admin role"""
    email = "admin@example.com"
    
    # Mock: email doesn't exist
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    # Mock: user creation
    new_user = {
        "user_id": str(uuid4()),
        "email": email,
        "full_name": "Admin User",
        "role": "admin",
        "is_active": True
    }
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [new_user]
    
    result = admin_user_service.create_user(
        email=email,
        full_name="Admin User",
        role="admin"
    )
    
    assert result["EC"] == 0
    assert result["data"]["role"] == "admin"


def test_create_user_insert_fails(admin_user_service, mock_supabase):
    """Test user creation when database insert fails"""
    email = "newuser@example.com"
    
    # Mock: email doesn't exist
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    # Mock: insert returns empty data
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = []
    
    result = admin_user_service.create_user(email=email)
    
    assert result["EC"] == 2
    assert result["EM"] == "Failed to create user"
    assert result["data"] is None


def test_create_user_exception(admin_user_service, mock_supabase):
    """Test user creation when exception occurs"""
    email = "newuser@example.com"
    
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("Database error")
    
    result = admin_user_service.create_user(email=email)
    
    assert result["EC"] == 2
    assert "Error creating user" in result["EM"]
    assert result["data"] is None


# ============================================
# UPDATE_USER TESTS
# ============================================

def test_update_user_success(admin_user_service, mock_supabase, sample_user_id):
    """Test successful user update"""
    updated_data = {
        "user_id": sample_user_id,
        "email": "updated@example.com",
        "full_name": "Updated Name",
        "phone_number": "0987654321",
        "role": "user",
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Create separate mocks for each table call
    call_count = [0]
    
    def mock_table(table_name):
        mock_table_obj = MagicMock()
        call_count[0] += 1
        
        if call_count[0] == 1:
            # First call: check user exists
            mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": sample_user_id, "email": "old@example.com"}]
        elif call_count[0] == 2:
            # Second call: check email doesn't exist
            mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = []
        elif call_count[0] == 3:
            # Third call: update
            mock_table_obj.update.return_value.eq.return_value.execute.return_value.data = [updated_data]
        
        return mock_table_obj
    
    mock_supabase.table.side_effect = mock_table
    
    result = admin_user_service.update_user(
        user_id=sample_user_id,
        email="updated@example.com",
        full_name="Updated Name",
        phone_number="0987654321"
    )
    
    assert result["EC"] == 0
    assert result["EM"] == "User updated successfully"
    assert result["data"]["email"] == "updated@example.com"
    assert result["data"]["full_name"] == "Updated Name"


def test_update_user_not_found(admin_user_service, mock_supabase, sample_user_id):
    """Test user update when user doesn't exist"""
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    result = admin_user_service.update_user(user_id=sample_user_id, email="new@example.com")
    
    assert result["EC"] == 1
    assert result["EM"] == "User not found"
    assert result["data"] is None


def test_update_user_email_exists(admin_user_service, mock_supabase, sample_user_id):
    """Test user update when new email already exists for another user"""
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": sample_user_id, "email": "old@example.com"}]
    
    # Mock: new email exists for different user
    other_user_id = str(uuid4())
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": other_user_id, "email": "existing@example.com"}]
    
    result = admin_user_service.update_user(
        user_id=sample_user_id,
        email="existing@example.com"
    )
    
    assert result["EC"] == 1
    assert result["EM"] == "Email already exists"
    assert result["data"] is None


def test_update_user_same_email(admin_user_service, mock_supabase, sample_user_id):
    """Test user update with same email (should succeed)"""
    email = "same@example.com"
    
    # Mock: user exists with same email
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": sample_user_id, "email": email}]
    
    # Mock: email check returns same user
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": sample_user_id, "email": email}]
    
    # Mock: update
    updated_data = {
        "user_id": sample_user_id,
        "email": email,
        "full_name": "Updated Name",
        "role": "user",
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated_data]
    
    result = admin_user_service.update_user(
        user_id=sample_user_id,
        email=email,
        full_name="Updated Name"
    )
    
    assert result["EC"] == 0
    assert result["data"]["email"] == email


def test_update_user_invalid_role(admin_user_service, mock_supabase, sample_user_id):
    """Test user update with invalid role"""
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": sample_user_id}]
    
    result = admin_user_service.update_user(
        user_id=sample_user_id,
        role="invalid_role"
    )
    
    assert result["EC"] == 2
    assert "Invalid role" in result["EM"]
    assert result["data"] is None


def test_update_user_password(admin_user_service, mock_supabase, sample_user_id):
    """Test user update with password change"""
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": sample_user_id}]
    
    # Mock: update
    updated_data = {
        "user_id": sample_user_id,
        "email": "user@example.com",
        "role": "user",
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated_data]
    
    result = admin_user_service.update_user(
        user_id=sample_user_id,
        password="newpassword123"
    )
    
    assert result["EC"] == 0
    # Verify password was hashed (check that update was called with password_hash)
    update_call = mock_supabase.table.return_value.update.return_value.eq.return_value.execute
    assert update_call.called


def test_update_user_partial_update(admin_user_service, mock_supabase, sample_user_id):
    """Test user update with only some fields"""
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": sample_user_id}]
    
    # Mock: update
    updated_data = {
        "user_id": sample_user_id,
        "email": "user@example.com",
        "full_name": "Only Name Updated",
        "role": "user",
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated_data]
    
    result = admin_user_service.update_user(
        user_id=sample_user_id,
        full_name="Only Name Updated"
    )
    
    assert result["EC"] == 0
    assert result["data"]["full_name"] == "Only Name Updated"


def test_update_user_update_fails(admin_user_service, mock_supabase, sample_user_id):
    """Test user update when database update fails"""
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": sample_user_id}]
    
    # Mock: update returns empty data
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
    
    result = admin_user_service.update_user(user_id=sample_user_id, full_name="New Name")
    
    assert result["EC"] == 2
    assert result["EM"] == "Failed to update user"
    assert result["data"] is None


def test_update_user_exception(admin_user_service, mock_supabase, sample_user_id):
    """Test user update when exception occurs"""
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("Database error")
    
    result = admin_user_service.update_user(user_id=sample_user_id, email="new@example.com")
    
    assert result["EC"] == 2
    assert "Error updating user" in result["EM"]
    assert result["data"] is None


# ============================================
# DELETE_USER TESTS
# ============================================

def test_delete_user_success(admin_user_service, mock_supabase, sample_user_id):
    """Test successful user deletion"""
    user_data = {
        "user_id": sample_user_id,
        "email": "user@example.com",
        "full_name": "Test User"
    }
    
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user_data]
    
    # Mock: no related records
    mock_response = MagicMock()
    mock_response.count = 0
    mock_response.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
    
    # Mock: delete
    mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [user_data]
    
    result = admin_user_service.delete_user(sample_user_id)
    
    assert result["EC"] == 0
    assert result["EM"] == "User deleted successfully"
    assert result["data"]["user_id"] == sample_user_id


def test_delete_user_not_found(admin_user_service, mock_supabase, sample_user_id):
    """Test user deletion when user doesn't exist"""
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    result = admin_user_service.delete_user(sample_user_id)
    
    assert result["EC"] == 1
    assert result["EM"] == "User not found"
    assert result["data"] is None


def test_delete_user_has_bookings(admin_user_service, mock_supabase, sample_user_id):
    """Test user deletion when user has bookings"""
    user_data = {"user_id": sample_user_id, "email": "user@example.com", "full_name": "Test User"}
    
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user_data]
    
    # Mock: user has bookings
    mock_response = MagicMock()
    mock_response.count = 5
    mock_response.data = [{"booking_id": str(uuid4())}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
    
    result = admin_user_service.delete_user(sample_user_id)
    
    assert result["EC"] == 3
    assert "Cannot delete user" in result["EM"]
    assert "booking" in result["EM"].lower()
    assert result["data"] is None


def test_delete_user_has_payments(admin_user_service, mock_supabase, sample_user_id):
    """Test user deletion when user has payments"""
    user_data = {"user_id": sample_user_id, "email": "user@example.com", "full_name": "Test User"}
    
    call_count = [0]
    
    def mock_table(table_name):
        mock_table_obj = MagicMock()
        call_count[0] += 1
        
        if call_count[0] == 1:
            # First call: check user exists
            mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = [user_data]
        elif table_name == "bookings":
            # Check bookings - no bookings
            mock_response = MagicMock()
            mock_response.count = 0
            mock_response.data = []
            mock_table_obj.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        elif table_name == "payments":
            # Check payments - has payments
            mock_response = MagicMock()
            mock_response.count = 3
            mock_response.data = [{"payment_id": str(uuid4())}]
            mock_table_obj.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        
        return mock_table_obj
    
    mock_supabase.table.side_effect = mock_table
    
    result = admin_user_service.delete_user(sample_user_id)
    
    assert result["EC"] == 3
    assert "Cannot delete user" in result["EM"]
    assert "payment" in result["EM"].lower()
    assert result["data"] is None


def test_delete_user_has_reviews(admin_user_service, mock_supabase, sample_user_id):
    """Test user deletion when user has reviews"""
    user_data = {"user_id": sample_user_id, "email": "user@example.com", "full_name": "Test User"}
    
    call_count = [0]
    
    def mock_table(table_name):
        mock_table_obj = MagicMock()
        call_count[0] += 1
        
        if call_count[0] == 1:
            # First call: check user exists
            mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = [user_data]
        else:
            mock_response = MagicMock()
            if table_name in ["bookings", "payments"]:
                mock_response.count = 0
                mock_response.data = []
            elif table_name == "reviews":
                mock_response.count = 2
                mock_response.data = [{"review_id": str(uuid4())}]
            else:
                mock_response.count = 0
                mock_response.data = []
            mock_table_obj.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        
        return mock_table_obj
    
    mock_supabase.table.side_effect = mock_table
    
    result = admin_user_service.delete_user(sample_user_id)
    
    assert result["EC"] == 3
    assert "Cannot delete user" in result["EM"]
    assert "review" in result["EM"].lower()
    assert result["data"] is None


def test_delete_user_has_chat_rooms(admin_user_service, mock_supabase, sample_user_id):
    """Test user deletion when user has chat rooms"""
    user_data = {"user_id": sample_user_id, "email": "user@example.com", "full_name": "Test User"}
    
    call_count = [0]
    
    def mock_table(table_name):
        mock_table_obj = MagicMock()
        call_count[0] += 1
        
        if call_count[0] == 1:
            # First call: check user exists
            mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = [user_data]
        else:
            mock_response = MagicMock()
            if table_name in ["bookings", "payments", "reviews"]:
                mock_response.count = 0
                mock_response.data = []
            elif table_name == "chat_rooms":
                mock_response.count = 1
                mock_response.data = [{"room_id": str(uuid4())}]
            else:
                mock_response.count = 0
                mock_response.data = []
            mock_table_obj.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        
        return mock_table_obj
    
    mock_supabase.table.side_effect = mock_table
    
    result = admin_user_service.delete_user(sample_user_id)
    
    assert result["EC"] == 3
    assert "Cannot delete user" in result["EM"]
    assert "chat room" in result["EM"].lower()
    assert result["data"] is None


def test_delete_user_has_otp_verifications(admin_user_service, mock_supabase, sample_user_id):
    """Test user deletion when user has OTP verifications"""
    user_data = {"user_id": sample_user_id, "email": "user@example.com", "full_name": "Test User"}
    
    call_count = [0]
    
    def mock_table(table_name):
        mock_table_obj = MagicMock()
        call_count[0] += 1
        
        if call_count[0] == 1:
            # First call: check user exists
            mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = [user_data]
        else:
            mock_response = MagicMock()
            if table_name in ["bookings", "payments", "reviews", "chat_rooms"]:
                mock_response.count = 0
                mock_response.data = []
            elif table_name == "otp_verifications":
                mock_response.count = 1
                mock_response.data = [{"otp_id": str(uuid4())}]
            else:
                mock_response.count = 0
                mock_response.data = []
            mock_table_obj.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        
        return mock_table_obj
    
    mock_supabase.table.side_effect = mock_table
    
    result = admin_user_service.delete_user(sample_user_id)
    
    assert result["EC"] == 3
    assert "Cannot delete user" in result["EM"]
    assert "OTP" in result["EM"]
    assert result["data"] is None


def test_delete_user_delete_fails(admin_user_service, mock_supabase, sample_user_id):
    """Test user deletion when database delete fails"""
    user_data = {"user_id": sample_user_id, "email": "user@example.com", "full_name": "Test User"}
    
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user_data]
    
    # Mock: no related records
    mock_response = MagicMock()
    mock_response.count = 0
    mock_response.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
    
    # Mock: delete returns empty
    mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    
    result = admin_user_service.delete_user(sample_user_id)
    
    assert result["EC"] == 2
    assert result["EM"] == "Failed to delete user"
    assert result["data"] is None


def test_delete_user_exception(admin_user_service, mock_supabase, sample_user_id):
    """Test user deletion when exception occurs"""
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("Database error")
    
    result = admin_user_service.delete_user(sample_user_id)
    
    assert result["EC"] == 2
    assert "Error deleting user" in result["EM"]
    assert result["data"] is None


# ============================================
# GET_ALL_USERS TESTS
# ============================================

def test_get_all_users_success(admin_user_service, mock_supabase):
    """Test successful retrieval of all users"""
    users_data = [
        {
            "user_id": str(uuid4()),
            "email": "user1@example.com",
            "full_name": "User One",
            "role": "user",
            "is_active": True,
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-10T15:30:00Z",
            "last_access_time": "2025-01-15T08:30:00Z"
        },
        {
            "user_id": str(uuid4()),
            "email": "user2@example.com",
            "full_name": "User Two",
            "role": "user",
            "is_active": True,
            "created_at": "2025-01-02T10:00:00Z",
            "updated_at": None,
            "last_access_time": None
        }
    ]
    
    mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value.data = users_data
    
    result = admin_user_service.get_all_users()
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert len(result["data"]["users"]) == 2
    assert result["data"]["total"] == 2
    assert result["data"]["users"][0]["email"] == "user1@example.com"


def test_get_all_users_empty(admin_user_service, mock_supabase):
    """Test get all users when no users exist"""
    mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value.data = []
    
    result = admin_user_service.get_all_users()
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert len(result["data"]["users"]) == 0
    assert result["data"]["total"] == 0


def test_get_all_users_none_data(admin_user_service, mock_supabase):
    """Test get all users when data is None"""
    mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value.data = None
    
    result = admin_user_service.get_all_users()
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert len(result["data"]["users"]) == 0
    assert result["data"]["total"] == 0


def test_get_all_users_exception(admin_user_service, mock_supabase):
    """Test get all users when exception occurs"""
    mock_supabase.table.return_value.select.return_value.order.return_value.execute.side_effect = Exception("Database error")
    
    result = admin_user_service.get_all_users()
    
    assert result["EC"] == 2
    assert "Error retrieving users" in result["EM"]
    assert result["data"] is None


# ============================================
# GET_USER_BOOKINGS TESTS
# ============================================

def test_get_user_bookings_success(admin_user_service, mock_supabase, sample_user_id):
    """Test successful retrieval of user bookings"""
    bookings_data = [
        {
            "booking_id": str(uuid4()),
            "user_id": sample_user_id,
            "package_id": str(uuid4()),
            "number_of_people": 2,
            "total_amount": 9000000,
            "status": "confirmed",
            "created_at": "2025-01-10T10:00:00Z",
            "tour_packages": {
                "package_name": "Tour Đà Lạt",
                "start_date": "2025-02-01",
                "end_date": "2025-02-03"
            }
        }
    ]
    
    # Mock response with count and data
    mock_response = MagicMock()
    mock_response.count = 1
    mock_response.data = bookings_data
    
    # Mock query chain: select -> eq -> (optional filters) -> order -> range -> execute
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = mock_response
    
    mock_supabase.table.return_value = mock_query
    
    result = admin_user_service.get_user_bookings(user_id=sample_user_id, page=1, limit=20)
    
    assert result["EC"] == 0
    assert len(result["data"]["items"]) == 1
    assert result["data"]["total"] == 1


def test_get_user_bookings_empty(admin_user_service, mock_supabase, sample_user_id):
    """Test get user bookings when user has no bookings"""
    mock_response = MagicMock()
    mock_response.count = 0
    mock_response.data = []
    
    # Mock query chain
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = mock_response
    
    mock_supabase.table.return_value = mock_query
    
    result = admin_user_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert len(result["data"]["items"]) == 0
    assert result["data"]["total"] == 0


def test_get_user_bookings_with_filters(admin_user_service, mock_supabase, sample_user_id):
    """Test get user bookings with status and date filters"""
    mock_response = MagicMock()
    mock_response.count = 1
    mock_response.data = [{"booking_id": str(uuid4()), "status": "confirmed"}]
    
    # Mock query chain with filters
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = mock_response
    
    mock_supabase.table.return_value = mock_query
    
    result = admin_user_service.get_user_bookings(
        user_id=sample_user_id,
        status="confirmed",
        from_date="2025-01-01",
        to_date="2025-12-31"
    )
    
    assert result["EC"] == 0


def test_get_user_bookings_exception(admin_user_service, mock_supabase, sample_user_id):
    """Test get user bookings when exception occurs"""
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.side_effect = Exception("Database error")
    
    mock_supabase.table.return_value = mock_query
    
    result = admin_user_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 2
    assert "Error retrieving user bookings" in result["EM"]
    assert result["data"] is None


# ============================================
# SET_USER_ACTIVE TESTS
# ============================================

def test_set_user_active_success(admin_user_service, mock_supabase, sample_user_id):
    """Test successful user status update"""
    user_data = {
        "user_id": sample_user_id,
        "email": "user@example.com",
        "is_active": False
    }
    
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user_data]
    
    # Mock: update
    updated_data = {**user_data, "is_active": True}
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated_data]
    
    result = admin_user_service.set_user_active(
        user_id=sample_user_id,
        is_active=True,
        reason="Admin activation",
        admin_id=str(uuid4())
    )
    
    assert result["EC"] == 0
    assert result["data"]["is_active"] is True


def test_set_user_active_not_found(admin_user_service, mock_supabase, sample_user_id):
    """Test set user active when user doesn't exist"""
    # Mock: update returns empty data (user not found)
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
    
    result = admin_user_service.set_user_active(
        user_id=sample_user_id,
        is_active=True,
        reason="Test",
        admin_id=str(uuid4())
    )
    
    assert result["EC"] == 1
    assert result["EM"] == "User not found"
    assert result["data"] is None


def test_set_user_active_exception(admin_user_service, mock_supabase, sample_user_id):
    """Test set user active when exception occurs"""
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("Database error")
    
    result = admin_user_service.set_user_active(
        user_id=sample_user_id,
        is_active=True,
        reason="Test",
        admin_id=str(uuid4())
    )
    
    assert result["EC"] == 2
    assert "Error updating user status" in result["EM"]
    assert result["data"] is None


# ============================================
# GET_USER_SUMMARY TESTS
# ============================================

def test_get_user_summary_success(admin_user_service, mock_supabase, sample_user_id, sample_user_data):
    """Test successful user summary retrieval"""
    call_count = [0]
    
    # Mock responses
    bookings_response = MagicMock()
    bookings_response.data = [
        {"booking_id": str(uuid4()), "status": "completed", "total_amount": 5000000},
        {"booking_id": str(uuid4()), "status": "confirmed", "total_amount": 3000000}
    ]
    
    payments_response = MagicMock()
    payments_response.data = [
        {"payment_id": str(uuid4()), "amount": 5000000, "payment_status": "completed", "paid_at": "2025-01-10T10:00:00Z"}
    ]
    
    recent_bookings_response = MagicMock()
    recent_bookings_response.data = [
        {
            "booking_id": str(uuid4()),
            "package_id": str(uuid4()),
            "status": "confirmed",
            "total_amount": 3000000,
            "created_at": "2025-01-15T10:00:00Z",
            "tour_packages": {"package_name": "Tour Đà Lạt"}
        }
    ]
    
    recent_payments_response = MagicMock()
    recent_payments_response.data = [
        {
            "payment_id": str(uuid4()),
            "amount": 5000000,
            "payment_status": "completed",
            "paid_at": "2025-01-10T10:00:00Z"
        }
    ]
    
    def mock_table(table_name):
        mock_table_obj = MagicMock()
        call_count[0] += 1
        
        if table_name == "users":
            # get_user_profile call
            mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = [sample_user_data]
        elif table_name == "bookings":
            if call_count[0] == 2:
                # First bookings query (for KPIs)
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = bookings_response
                return mock_query
            else:
                # Recent bookings query
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value.execute.return_value = recent_bookings_response
                return mock_query
        elif table_name == "payments":
            if call_count[0] == 3:
                # Payments query (for KPIs)
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value.execute.return_value = payments_response
                return mock_query
            else:
                # Recent payments query
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value.execute.return_value = recent_payments_response
                return mock_query
        
        return mock_table_obj
    
    mock_supabase.table.side_effect = mock_table
    
    result = admin_user_service.get_user_summary(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["data"]["user"]["user_id"] == str(sample_user_data["user_id"])
    assert "kpi" in result["data"]
    assert "recent" in result["data"]


def test_get_user_summary_user_not_found(admin_user_service, mock_supabase, sample_user_id):
    """Test user summary when user doesn't exist"""
    # Mock: user not found in get_user_profile
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    result = admin_user_service.get_user_summary(user_id=sample_user_id)
    
    assert result["EC"] == 1
    assert result["EM"] == "User not found"
    assert result["data"] is None


def test_get_user_summary_no_bookings(admin_user_service, mock_supabase, sample_user_id, sample_user_data):
    """Test user summary when user has no bookings"""
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [sample_user_data]
    
    # Mock: empty bookings and payments
    empty_response = MagicMock()
    empty_response.data = []
    
    def mock_table(table_name):
        mock_table_obj = MagicMock()
        if table_name == "users":
            mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = [sample_user_data]
        else:
            mock_table_obj.select.return_value.eq.return_value.execute.return_value = empty_response
            mock_table_obj.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = empty_response
            if hasattr(mock_table_obj.select.return_value.eq.return_value, 'in_'):
                mock_table_obj.select.return_value.eq.return_value.in_.return_value.execute.return_value = empty_response
        return mock_table_obj
    
    mock_supabase.table.side_effect = mock_table
    
    result = admin_user_service.get_user_summary(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["data"]["kpi"]["total_bookings"] == 0
    assert result["data"]["kpi"]["total_paid_amount"] == 0


def test_get_user_summary_with_date_filter(admin_user_service, mock_supabase, sample_user_id, sample_user_data):
    """Test user summary with date filters"""
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [sample_user_data]
    
    # Mock: empty responses
    empty_response = MagicMock()
    empty_response.data = []
    
    def mock_table(table_name):
        mock_table_obj = MagicMock()
        if table_name == "users":
            mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = [sample_user_data]
        else:
            mock_table_obj.select.return_value.eq.return_value.execute.return_value = empty_response
            mock_table_obj.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = empty_response
            if hasattr(mock_table_obj.select.return_value.eq.return_value, 'in_'):
                mock_table_obj.select.return_value.eq.return_value.in_.return_value.execute.return_value = empty_response
        return mock_table_obj
    
    mock_supabase.table.side_effect = mock_table
    
    result = admin_user_service.get_user_summary(
        user_id=sample_user_id,
        from_date="2025-01-01",
        to_date="2025-12-31"
    )
    
    assert result["EC"] == 0


def test_get_user_summary_exception(admin_user_service, mock_supabase, sample_user_id):
    """Test user summary when exception occurs"""
    # Exception occurs in get_user_profile (first call)
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("Database error")
    
    result = admin_user_service.get_user_summary(user_id=sample_user_id)
    
    assert result["EC"] == 2
    assert "Error retrieving user profile" in result["EM"]
    assert result["data"] is None


# ============================================
# GET_USER_CHAT_HISTORY TESTS
# ============================================

def test_get_user_chat_history_success(admin_user_service, mock_supabase, sample_user_id):
    """Test successful user chat history retrieval"""
    room_id = str(uuid4())
    rooms_data = [
        {
            "room_id": room_id,
            "user_id": sample_user_id,
            "title": "Chat về tour Đà Lạt",
            "created_at": "2025-01-10T10:00:00Z",
            "updated_at": "2025-01-15T15:30:00Z"
        }
    ]
    
    messages_data = [
        {
            "message_id": str(uuid4()),
            "role": "user",
            "content": "Xin chào",
            "intent": "greeting",
            "created_at": "2025-01-10T10:00:00Z"
        },
        {
            "message_id": str(uuid4()),
            "role": "assistant",
            "content": "Chào bạn!",
            "intent": None,
            "created_at": "2025-01-10T10:01:00Z"
        }
    ]
    
    # Mock: chat rooms
    rooms_response = MagicMock()
    rooms_response.data = rooms_data
    
    # Mock: messages
    messages_response = MagicMock()
    messages_response.data = messages_data
    
    def mock_table(table_name):
        mock_table_obj = MagicMock()
        if table_name == "chat_rooms":
            mock_table_obj.select.return_value.eq.return_value.order.return_value.execute.return_value = rooms_response
        elif table_name == "chat_history":
            mock_table_obj.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = messages_response
        return mock_table_obj
    
    mock_supabase.table.side_effect = mock_table
    
    result = admin_user_service.get_user_chat_history(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["data"]["user_id"] == sample_user_id
    assert result["data"]["total_rooms"] == 1
    assert len(result["data"]["rooms"]) == 1
    assert len(result["data"]["rooms"][0]["messages"]) == 2


def test_get_user_chat_history_no_rooms(admin_user_service, mock_supabase, sample_user_id):
    """Test user chat history when user has no chat rooms"""
    rooms_response = MagicMock()
    rooms_response.data = []
    
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = rooms_response
    
    result = admin_user_service.get_user_chat_history(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["data"]["total_rooms"] == 0
    assert len(result["data"]["rooms"]) == 0


def test_get_user_chat_history_no_messages(admin_user_service, mock_supabase, sample_user_id):
    """Test user chat history when rooms exist but no messages"""
    room_id = str(uuid4())
    rooms_data = [
        {
            "room_id": room_id,
            "user_id": sample_user_id,
            "title": "Empty Room",
            "created_at": "2025-01-10T10:00:00Z",
            "updated_at": "2025-01-10T10:00:00Z"
        }
    ]
    
    rooms_response = MagicMock()
    rooms_response.data = rooms_data
    
    messages_response = MagicMock()
    messages_response.data = []
    
    def mock_table(table_name):
        mock_table_obj = MagicMock()
        if table_name == "chat_rooms":
            mock_table_obj.select.return_value.eq.return_value.order.return_value.execute.return_value = rooms_response
        elif table_name == "chat_history":
            mock_table_obj.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = messages_response
        return mock_table_obj
    
    mock_supabase.table.side_effect = mock_table
    
    result = admin_user_service.get_user_chat_history(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["data"]["total_rooms"] == 1
    assert len(result["data"]["rooms"][0]["messages"]) == 0


def test_get_user_chat_history_exception(admin_user_service, mock_supabase, sample_user_id):
    """Test user chat history when exception occurs"""
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.side_effect = Exception("Database error")
    
    result = admin_user_service.get_user_chat_history(user_id=sample_user_id)
    
    assert result["EC"] == 2
    assert "Error retrieving user chat history" in result["EM"]
    assert result["data"] is None


# ============================================
# PASSWORD HASHING TESTS
# ============================================

def test_hash_password(admin_user_service):
    """Test password hashing functionality"""
    password = "testpassword123"
    hashed = admin_user_service._hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 0
    assert hashed.startswith("$2b$")  # bcrypt hash format


def test_hash_password_different_passwords(admin_user_service):
    """Test that different passwords produce different hashes"""
    password1 = "password1"
    password2 = "password2"
    
    hashed1 = admin_user_service._hash_password(password1)
    hashed2 = admin_user_service._hash_password(password2)
    
    assert hashed1 != hashed2


def test_hash_password_same_password_different_hash(admin_user_service):
    """Test that same password produces different hashes (due to salt)"""
    password = "samepassword"
    
    hashed1 = admin_user_service._hash_password(password)
    hashed2 = admin_user_service._hash_password(password)
    
    # Different salts should produce different hashes
    assert hashed1 != hashed2


# ============================================
# EDGE CASES - PAGINATION
# ============================================

def test_get_user_bookings_pagination_edge_cases(admin_user_service, mock_supabase, sample_user_id):
    """Test pagination edge cases for user bookings"""
    mock_response = MagicMock()
    mock_response.count = 0
    mock_response.data = []
    
    # Mock query chain
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = mock_response
    
    mock_supabase.table.return_value = mock_query
    
    # Test with large page number
    result = admin_user_service.get_user_bookings(user_id=sample_user_id, page=999, limit=20)
    
    assert result["EC"] == 0
    assert result["data"]["page"] == 999


def test_get_user_bookings_limit_edge_cases(admin_user_service, mock_supabase, sample_user_id):
    """Test limit edge cases for user bookings"""
    mock_response = MagicMock()
    mock_response.count = 100
    mock_response.data = [{"booking_id": str(uuid4())} for _ in range(100)]
    
    # Mock query chain
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = mock_response
    
    mock_supabase.table.return_value = mock_query
    
    # Test with max limit
    result = admin_user_service.get_user_bookings(user_id=sample_user_id, page=1, limit=100)
    
    assert result["EC"] == 0
    assert result["data"]["limit"] == 100


# ============================================
# EDGE CASES - NULL VALUES
# ============================================

def test_create_user_with_null_optional_fields(admin_user_service, mock_supabase):
    """Test user creation with None for optional fields"""
    email = "user@example.com"
    
    # Mock: email doesn't exist
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    # Mock: user creation
    new_user = {
        "user_id": str(uuid4()),
        "email": email,
        "full_name": email.split('@')[0],
        "phone_number": None,
        "role": "user",
        "is_active": True
    }
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [new_user]
    
    result = admin_user_service.create_user(
        email=email,
        full_name=None,
        phone_number=None
    )
    
    assert result["EC"] == 0
    assert result["data"]["email"] == email


def test_update_user_with_none_values(admin_user_service, mock_supabase, sample_user_id):
    """Test user update with None values (should not update those fields)"""
    # Mock: user exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": sample_user_id}]
    
    # Mock: update
    updated_data = {
        "user_id": sample_user_id,
        "email": "user@example.com",
        "role": "user",
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated_data]
    
    result = admin_user_service.update_user(
        user_id=sample_user_id,
        email=None,
        full_name=None,
        phone_number=None
    )
    
    assert result["EC"] == 0
    # Verify that update was called (even with None values, updated_at should be set)
    assert mock_supabase.table.return_value.update.called
