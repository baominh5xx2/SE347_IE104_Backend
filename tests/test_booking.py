"""
Test cases for Booking Service with OTP Flow
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.v1.services.booking_service import BookingService


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    return MagicMock()


@pytest.fixture
def booking_service(mock_supabase):
    """Create BookingService instance with mock client"""
    return BookingService(mock_supabase)


@pytest.fixture
def sample_booking_data():
    """Sample booking data for testing"""
    return {
        "package_id": str(uuid4()),
        "user_id": str(uuid4()),
        "number_of_people": 2,
        "contact_name": "Nguyen Van A",
        "contact_phone": "0901234567",
        "contact_email": "user@example.com",
        "special_requests": "Phòng view đẹp"
    }


@pytest.fixture
def sample_booking_response():
    """Sample booking response from database"""
    booking_id = str(uuid4())
    package_id = str(uuid4())
    user_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    return {
        "booking_id": booking_id,
        "package_id": package_id,
        "user_id": user_id,
        "number_of_people": 2,
        "total_amount": 5000000,
        "contact_name": "Nguyen Van A",
        "contact_phone": "0901234567",
        "contact_email": "user@example.com",
        "special_requests": "Phòng view đẹp",
        "status": "pending",
        "created_at": now,
        "updated_at": now
    }


# ============================================================================
# TEST: get_all_bookings
# ============================================================================

@pytest.mark.asyncio
async def test_get_all_bookings_success(booking_service, mock_supabase, sample_booking_response):
    """Test getting all bookings successfully"""
    mock_result = MagicMock()
    mock_result.data = [sample_booking_response]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.get_all_bookings()
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert len(result["data"]) == 1
    assert result["total"] == 1
    assert result["data"][0]["contact_email"] == "user@example.com"


@pytest.mark.asyncio
async def test_get_all_bookings_with_filters(booking_service, mock_supabase):
    """Test getting bookings with filters"""
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    user_id = str(uuid4())
    result = await booking_service.get_all_bookings(
        user_id=user_id,
        status="pending",
        limit=10,
        offset=0
    )
    
    assert result["EC"] == 0
    assert result["total"] == 0


# ============================================================================
# TEST: get_booking_by_id
# ============================================================================

@pytest.mark.asyncio
async def test_get_booking_by_id_success(booking_service, mock_supabase, sample_booking_response):
    """Test getting booking by ID successfully"""
    mock_result = MagicMock()
    mock_result.data = [sample_booking_response]
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    booking_id = sample_booking_response["booking_id"]
    result = await booking_service.get_booking_by_id(booking_id)
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert result["data"]["booking_id"] == booking_id
    assert result["data"]["contact_email"] == "user@example.com"


@pytest.mark.asyncio
async def test_get_booking_by_id_not_found(booking_service, mock_supabase):
    """Test getting non-existent booking"""
    mock_result = MagicMock()
    mock_result.data = []
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.get_booking_by_id(str(uuid4()))
    
    assert result["EC"] == 1
    assert result["EM"] == "Booking not found"


# ============================================================================
# TEST: create_booking_with_otp (NEW PRIMARY METHOD)
# ============================================================================

@pytest.mark.asyncio
async def test_create_booking_with_otp_success(booking_service, mock_supabase, sample_booking_data):
    """Test creating booking with OTP successfully"""
    # Mock package check - Need both select calls
    mock_package_select_1 = MagicMock()
    mock_package_select_1.data = [{
        "package_id": sample_booking_data["package_id"],
        "package_name": "Tour Hạ Long 3N2Đ",
        "available_slots": 10,
        "is_active": True,
        "price": 2500000
    }]
    
    mock_package_select_2 = MagicMock()
    mock_package_select_2.data = [{
        "available_slots": 10,
        "is_active": True
    }]
    
    # Mock user check
    mock_user_result = MagicMock()
    mock_user_result.data = [{
        "user_id": sample_booking_data["user_id"],
        "full_name": "Nguyen Van A",
        "phone_number": "0901234567",
        "email": "user@example.com"
    }]
    
    # Mock booking insert
    booking_id = str(uuid4())
    mock_booking_result = MagicMock()
    mock_booking_result.data = [{
        "booking_id": booking_id,
        "package_id": sample_booking_data["package_id"],
        "user_id": sample_booking_data["user_id"],
        "number_of_people": 2,
        "total_amount": 5000000,
        "contact_name": "Nguyen Van A",
        "contact_phone": "0901234567",
        "contact_email": "user@example.com",
        "status": "otp_sent",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }]
    
    # Mock OTP insert
    mock_otp_result = MagicMock()
    mock_otp_result.data = [{"booking_id": booking_id, "otp_code": "123456"}]
    
    # Mock OTP service
    mock_otp_service = MagicMock()
    mock_otp_service.send_otp_email.return_value = True
    
    # Mock slots update
    mock_update_result = MagicMock()
    mock_update_result.data = [{"available_slots": 8}]
    
    package_call_count = {'count': 0}
    
    def table_side_effect(table_name):
        mock_query = MagicMock()
        
        if table_name == "tour_packages":
            # First call: select with all fields
            if package_call_count['count'] == 0:
                package_call_count['count'] += 1
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_package_select_1
            # Second call: select for validation
            elif package_call_count['count'] == 1:
                package_call_count['count'] += 1
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_package_select_2
            # Third call: update slots
            else:
                mock_query.update.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_update_result
            
        elif table_name == "users":
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_user_result
            
        elif table_name == "bookings":
            mock_query.insert.return_value = mock_query
            mock_query.execute.return_value = mock_booking_result
            
        elif table_name == "otp_verifications":
            mock_query.insert.return_value = mock_query
            mock_query.execute.return_value = mock_otp_result
            
        return mock_query
    
    mock_supabase.table.side_effect = table_side_effect
    
    with patch('app.v1.services.booking_service.get_otp_service', return_value=mock_otp_service):
        result = await booking_service.create_booking_with_otp(sample_booking_data)
    
    assert result["EC"] == 0
    assert "OTP" in result["EM"]
    assert result["data"]["booking_id"] == booking_id
    assert result["data"]["awaiting_otp"] is True
    assert result["data"]["contact_email"] == "user@example.com"


@pytest.mark.asyncio
async def test_create_booking_with_otp_package_not_found(booking_service, mock_supabase, sample_booking_data):
    """Test creating booking with non-existent package"""
    mock_result = MagicMock()
    mock_result.data = []
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.create_booking_with_otp(sample_booking_data)
    
    assert result["EC"] == 1
    assert "not found" in result["EM"].lower()


@pytest.mark.asyncio
async def test_create_booking_with_otp_insufficient_slots(booking_service, mock_supabase, sample_booking_data):
    """Test creating booking without enough slots"""
    mock_result = MagicMock()
    mock_result.data = [{
        "available_slots": 1,  # Less than requested
        "is_active": True,
        "price": 2500000
    }]
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.create_booking_with_otp(sample_booking_data)
    
    assert result["EC"] == 3
    assert "slots" in result["EM"].lower()


# ============================================================================
# TEST: verify_otp
# ============================================================================

@pytest.mark.asyncio
async def test_verify_otp_success(booking_service, mock_supabase):
    """Test verifying OTP successfully"""
    booking_id = str(uuid4())
    otp_code = "123456"
    
    # Mock OTP record
    from datetime import timedelta
    future_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    mock_otp_result = MagicMock()
    mock_otp_result.data = [{
        "booking_id": booking_id,
        "otp_code": otp_code,
        "phone_number": "0901234567",
        "expires_at": future_time.isoformat(),  # ISO format string
        "attempts": 0,
        "is_verified": False
    }]
    
    # Mock booking
    mock_booking_result = MagicMock()
    mock_booking_result.data = [{
        "booking_id": booking_id,
        "status": "otp_sent",
        "contact_email": "user@example.com",
        "tour_packages": {
            "package_name": "Tour Hạ Long 3N2Đ"
        }
    }]
    
    # Mock OTP update
    mock_otp_update = MagicMock()
    mock_otp_update.data = [{"is_verified": True}]
    
    # Mock booking update
    mock_booking_update = MagicMock()
    mock_booking_update.data = [{
        "booking_id": booking_id,
        "status": "pending"
    }]
    
    # Setup mock query builder
    mock_otp_query = MagicMock()
    mock_otp_query.select = MagicMock(return_value=mock_otp_query)
    mock_otp_query.eq = MagicMock(return_value=mock_otp_query)
    mock_otp_query.update = MagicMock(return_value=mock_otp_query)
    mock_otp_query.execute = MagicMock(side_effect=[
        mock_otp_result,  # First select: check booking has OTP (line 622)
        mock_otp_result,  # Second select: get OTP with correct code (line 631)
        mock_otp_update   # Update: mark verified (line 705)
    ])
    
    mock_booking_query = MagicMock()
    mock_booking_query.select = MagicMock(return_value=mock_booking_query)
    mock_booking_query.eq = MagicMock(return_value=mock_booking_query)
    mock_booking_query.update = MagicMock(return_value=mock_booking_query)
    mock_booking_query.execute = MagicMock(side_effect=[
        mock_booking_update,  # Update status
        mock_booking_result   # Get booking details
    ])
    
    def table_side_effect(table_name):
        if table_name == "otp_verifications":
            return mock_otp_query
        elif table_name == "bookings":
            return mock_booking_query
        return MagicMock()
    
    mock_supabase.table.side_effect = table_side_effect
    
    result = await booking_service.verify_otp(booking_id=booking_id, otp_code=otp_code)
    
    assert result["EC"] == 0
    assert ("confirmed" in result["EM"].lower() or "success" in result["EM"].lower() or 
            "thành công" in result["EM"].lower() or "xác thực" in result["EM"].lower())


@pytest.mark.asyncio
async def test_verify_otp_invalid_code(booking_service, mock_supabase):
    """Test verifying with invalid OTP code"""
    from datetime import timedelta
    booking_id = str(uuid4())
    future_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    # First query: check booking has OTP (returns data)
    mock_otp_check_result = MagicMock()
    mock_otp_check_result.data = [{
        "booking_id": booking_id,
        "otp_code": "123456",
        "expires_at": future_time.isoformat(),
        "attempts": 0,
        "is_verified": False
    }]
    
    # Second query: check with wrong code (returns empty)
    mock_empty_result = MagicMock()
    mock_empty_result.data = []
    
    # Third query: get existing OTP for increment attempts
    mock_existing_otp = MagicMock()
    mock_existing_otp.data = [{
        "booking_id": booking_id,
        "otp_code": "123456",
        "expires_at": future_time.isoformat(),
        "attempts": 0,
        "is_verified": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }]
    
    # Fourth: update attempts
    mock_update_result = MagicMock()
    mock_update_result.data = [{"attempts": 1}]
    
    mock_query = MagicMock()
    mock_query.select = MagicMock(return_value=mock_query)
    mock_query.eq = MagicMock(return_value=mock_query)
    mock_query.update = MagicMock(return_value=mock_query)
    mock_query.execute = MagicMock(side_effect=[
        mock_otp_check_result,  # First select: check OTP exists
        mock_empty_result,      # Second select: wrong code
        mock_existing_otp,      # Third select: get for increment
        mock_update_result      # Update attempts
    ])
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.verify_otp(booking_id=booking_id, otp_code="999999")
    
    assert result["EC"] != 0
    assert ("invalid" in result["EM"].lower() or "incorrect" in result["EM"].lower() or 
            "sai" in result["EM"].lower() or "không đúng" in result["EM"].lower())


@pytest.mark.asyncio
async def test_verify_otp_expired(booking_service, mock_supabase):
    """Test verifying expired OTP"""
    from datetime import timedelta
    booking_id = str(uuid4())
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    mock_otp_result = MagicMock()
    mock_otp_result.data = [{
        "booking_id": booking_id,
        "otp_code": "123456",
        "expires_at": past_time.isoformat(),  # Past time
        "attempts": 0,
        "is_verified": False
    }]
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_otp_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.verify_otp(booking_id=booking_id, otp_code="123456")
    
    assert result["EC"] != 0
    assert ("expired" in result["EM"].lower() or "hết hạn" in result["EM"].lower())


@pytest.mark.asyncio
async def test_verify_otp_max_attempts(booking_service, mock_supabase):
    """Test verifying OTP with max attempts reached"""
    from datetime import timedelta
    booking_id = str(uuid4())
    future_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    mock_otp_result = MagicMock()
    mock_otp_result.data = [{
        "booking_id": booking_id,
        "otp_code": "123456",
        "expires_at": future_time.isoformat(),
        "attempts": 3,  # Max reached
        "is_verified": False
    }]
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_otp_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.verify_otp(booking_id=booking_id, otp_code="123456")
    
    assert result["EC"] != 0
    assert ("attempts" in result["EM"].lower() or "exceeded" in result["EM"].lower() or 
            "vượt quá" in result["EM"].lower() or "cho phép" in result["EM"].lower())


# ============================================================================
# TEST: resend_otp
# ============================================================================

@pytest.mark.asyncio
async def test_resend_otp_success(booking_service, mock_supabase):
    """Test resending OTP successfully"""
    booking_id = str(uuid4())
    
    # Mock booking
    mock_booking_result = MagicMock()
    mock_booking_result.data = [{
        "booking_id": booking_id,
        "status": "otp_sent",
        "contact_email": "user@example.com",
        "contact_phone": "0901234567",
        "tour_packages": {
            "package_name": "Tour Hạ Long 3N2Đ"
        }
    }]
    
    # Mock delete old OTP
    mock_delete_result = MagicMock()
    mock_delete_result.data = []
    
    # Mock insert new OTP
    mock_otp_insert = MagicMock()
    mock_otp_insert.data = [{"booking_id": booking_id, "otp_code": "654321"}]
    
    # Mock OTP service
    mock_otp_service = MagicMock()
    mock_otp_service.send_otp_email.return_value = True
    
    def table_side_effect(table_name):
        mock_query = MagicMock()
        
        if table_name == "bookings":
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_booking_result
            
        elif table_name == "otp_verifications":
            mock_query.delete.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_delete_result
            
            mock_query.insert.return_value = mock_query
            mock_query.execute.return_value = mock_otp_insert
            
        return mock_query
    
    mock_supabase.table.side_effect = table_side_effect
    
    with patch('app.v1.services.booking_service.get_otp_service', return_value=mock_otp_service):
        result = await booking_service.resend_otp(booking_id=booking_id)
    
    assert result["EC"] == 0
    assert "OTP" in result["EM"]
    assert result["data"]["booking_id"] == booking_id
    assert result["data"]["contact_email"] == "user@example.com"


@pytest.mark.asyncio
async def test_resend_otp_booking_not_found(booking_service, mock_supabase):
    """Test resending OTP for non-existent booking"""
    mock_result = MagicMock()
    mock_result.data = []
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.resend_otp(booking_id=str(uuid4()))
    
    assert result["EC"] == 1
    assert "not found" in result["EM"].lower()


@pytest.mark.asyncio
async def test_resend_otp_invalid_status(booking_service, mock_supabase):
    """Test resending OTP for booking not awaiting OTP"""
    booking_id = str(uuid4())
    
    mock_result = MagicMock()
    mock_result.data = [{
        "booking_id": booking_id,
        "status": "confirmed",  # Not otp_sent
        "contact_email": "user@example.com"
    }]
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.resend_otp(booking_id=booking_id)
    
    assert result["EC"] == 2
    assert ("otp_sent" in result["EM"].lower() or "cannot resend" in result["EM"].lower())


# ============================================================================
# TEST: update_booking
# ============================================================================

@pytest.mark.asyncio
async def test_update_booking_contact_email(booking_service, mock_supabase, sample_booking_response):
    """Test updating booking contact_email"""
    with patch.object(booking_service, 'get_booking_by_id', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": sample_booking_response
        }
        
        updated_booking = sample_booking_response.copy()
        updated_booking["contact_email"] = "newemail@example.com"
        
        mock_result = MagicMock()
        mock_result.data = [updated_booking]
        
        mock_query = MagicMock()
        mock_query.update.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_query
        
        result = await booking_service.update_booking(
            sample_booking_response["booking_id"],
            {"contact_email": "newemail@example.com"}
        )
        
        assert result["EC"] == 0
        assert result["data"]["contact_email"] == "newemail@example.com"


@pytest.mark.asyncio
async def test_update_booking_status(booking_service, mock_supabase, sample_booking_response):
    """Test updating booking status"""
    with patch.object(booking_service, 'get_booking_by_id', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": sample_booking_response
        }
        
        updated_booking = sample_booking_response.copy()
        updated_booking["status"] = "confirmed"
        
        mock_result = MagicMock()
        mock_result.data = [updated_booking]
        
        mock_query = MagicMock()
        mock_query.update.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_query
        
        result = await booking_service.update_booking(
            sample_booking_response["booking_id"],
            {"status": "confirmed"}
        )
        
        assert result["EC"] == 0
        assert result["data"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_update_booking_not_found(booking_service, mock_supabase):
    """Test updating non-existent booking"""
    with patch.object(booking_service, 'get_booking_by_id', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 1,
            "EM": "Booking not found",
            "data": None
        }
        
        result = await booking_service.update_booking(str(uuid4()), {"status": "confirmed"})
        
        assert result["EC"] == 1
        assert result["EM"] == "Booking not found"


# ============================================================================
# TEST: delete_booking
# ============================================================================

@pytest.mark.asyncio
async def test_delete_booking_success(booking_service, mock_supabase, sample_booking_response):
    """Test deleting booking successfully"""
    with patch.object(booking_service, 'get_booking_by_id', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": sample_booking_response
        }
        
        mock_delete_result = MagicMock()
        mock_delete_result.data = [sample_booking_response]
        
        mock_package_result = MagicMock()
        mock_package_result.data = [{"available_slots": 8}]
        
        mock_update_result = MagicMock()
        mock_update_result.data = [{"available_slots": 10}]
        
        def table_side_effect(table_name):
            mock_query = MagicMock()
            
            if table_name == "bookings":
                mock_query.delete.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_delete_result
            else:  # tour_packages
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_package_result
                
                mock_query.update.return_value = mock_query
                mock_query.execute.return_value = mock_update_result
                
            return mock_query
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = await booking_service.delete_booking(sample_booking_response["booking_id"])
        
        assert result["EC"] == 0
        assert result["EM"] == "Booking deleted successfully"


@pytest.mark.asyncio
async def test_delete_booking_not_found(booking_service, mock_supabase):
    """Test deleting non-existent booking"""
    with patch.object(booking_service, 'get_booking_by_id', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 1,
            "EM": "Booking not found",
            "data": None
        }
        
        result = await booking_service.delete_booking(str(uuid4()))
        
        assert result["EC"] == 1
        assert result["EM"] == "Booking not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
