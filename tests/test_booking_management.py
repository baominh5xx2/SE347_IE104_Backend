"""
Test cases for Booking Management Service (UC-USER-03)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from app.v1.services.booking_management_service import BookingManagementService
from app.v1.api.endpoints.booking_management import (
    get_my_bookings,
    get_my_booking_detail,
    get_all_bookings_admin,
    get_user_bookings_admin,
    get_booking_detail_admin
)
from fastapi import HTTPException


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    return MagicMock()


@pytest.fixture
def booking_management_service(mock_supabase):
    """Create BookingManagementService instance with mock client"""
    return BookingManagementService(mock_supabase)


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing"""
    return str(uuid4())


@pytest.fixture
def sample_tour_package():
    """Sample tour package data"""
    return {
        "package_id": str(uuid4()),
        "package_name": "Tour Đà Lạt 3N2Đ",
        "destination": "Đà Lạt",
        "description": "Khám phá thành phố ngàn hoa",
        "duration_days": 3,
        "start_date": "2025-01-15",
        "end_date": "2025-01-17",
        "price": 4500000,
        "image_urls": "url1|url2"
    }


@pytest.fixture
def sample_booking_with_tour():
    """Sample booking data with tour package info"""
    booking_id = str(uuid4())
    package_id = str(uuid4())
    user_id = str(uuid4())
    now = datetime.now().isoformat()
    
    return {
        "booking_id": booking_id,
        "user_id": user_id,
        "package_id": package_id,
        "number_of_people": 2,
        "total_amount": 9000000,
        "contact_name": "Nguyen Van A",
        "contact_phone": "0123456789",
        "special_requests": "Phòng view đẹp",
        "status": "confirmed",
        "created_at": now,
        "updated_at": now,
        "tour_packages": {
            "package_id": package_id,
            "package_name": "Tour Đà Lạt 3N2Đ",
            "destination": "Đà Lạt",
            "description": "Khám phá thành phố ngàn hoa",
            "duration_days": 3,
            "start_date": "2025-01-15",
            "end_date": "2025-01-17",
            "price": 4500000,
            "image_urls": "url1|url2"
        }
    }


@pytest.fixture
def sample_user():
    """Sample user data"""
    return {
        "user_id": str(uuid4()),
        "email": "user@example.com",
        "full_name": "Nguyen Van A",
        "role": "user"
    }


@pytest.fixture
def sample_admin():
    """Sample admin data"""
    return {
        "user_id": str(uuid4()),
        "email": "admin@example.com",
        "full_name": "Admin User",
        "role": "admin"
    }


# ============================================
# Service Tests: get_user_bookings
# ============================================

@pytest.mark.asyncio
async def test_get_user_bookings_success(booking_management_service, mock_supabase, sample_user_id, sample_booking_with_tour):
    """Test getting user bookings successfully"""
    mock_result = MagicMock()
    mock_result.data = [sample_booking_with_tour]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert len(result["data"]) == 1
    assert result["total"] == 1
    assert result["data"][0]["booking_id"] == sample_booking_with_tour["booking_id"]
    assert result["data"][0]["tour_name"] == "Tour Đà Lạt 3N2Đ"
    assert result["data"][0]["destination"] == "Đà Lạt"


@pytest.mark.asyncio
async def test_get_user_bookings_with_status_filter(booking_management_service, mock_supabase, sample_user_id):
    """Test getting user bookings with status filter"""
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings(
        user_id=sample_user_id,
        status="pending"
    )
    
    assert result["EC"] == 0
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_get_user_bookings_empty(booking_management_service, mock_supabase, sample_user_id):
    """Test getting bookings when user has no bookings"""
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["total"] == 0
    assert result["data"] == []


# ============================================
# Service Tests: get_user_booking_detail
# ============================================

@pytest.mark.asyncio
async def test_get_user_booking_detail_success(booking_management_service, mock_supabase, sample_user_id, sample_booking_with_tour):
    """Test getting user booking detail successfully"""
    booking_id = sample_booking_with_tour["booking_id"]
    
    mock_result = MagicMock()
    mock_result.data = [sample_booking_with_tour]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_booking_detail(
        booking_id=booking_id,
        user_id=sample_user_id
    )
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert result["data"]["booking_id"] == booking_id
    assert result["data"]["tour_package"] is not None
    assert result["data"]["tour_package"]["package_name"] == "Tour Đà Lạt 3N2Đ"


@pytest.mark.asyncio
async def test_get_user_booking_detail_not_found(booking_management_service, mock_supabase, sample_user_id):
    """Test getting non-existent booking detail"""
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_booking_detail(
        booking_id=str(uuid4()),
        user_id=sample_user_id
    )
    
    assert result["EC"] == 1
    assert "not found" in result["EM"].lower() or "denied" in result["EM"].lower()


# ============================================
# Service Tests: get_all_bookings_admin
# ============================================

@pytest.mark.asyncio
async def test_get_all_bookings_admin_success(booking_management_service, mock_supabase, sample_booking_with_tour):
    """Test admin getting all bookings successfully"""
    # Mock bookings query
    mock_booking_result = MagicMock()
    mock_booking_result.data = [sample_booking_with_tour]
    mock_booking_result.count = 1
    
    mock_booking_query = MagicMock()
    mock_booking_query.select.return_value = mock_booking_query
    mock_booking_query.eq.return_value = mock_booking_query
    mock_booking_query.order.return_value = mock_booking_query
    mock_booking_query.execute.return_value = mock_booking_result
    
    # Mock users query
    mock_user_result = MagicMock()
    mock_user_result.data = [{
        "email": "user@example.com",
        "full_name": "Nguyen Van A"
    }]
    
    mock_user_query = MagicMock()
    mock_user_query.select.return_value = mock_user_query
    mock_user_query.eq.return_value = mock_user_query
    mock_user_query.execute.return_value = mock_user_result
    
    def table_side_effect(table_name):
        if table_name == "bookings":
            return mock_booking_query
        elif table_name == "users":
            return mock_user_query
        return MagicMock()
    
    mock_supabase.table.side_effect = table_side_effect
    
    result = await booking_management_service.get_all_bookings_admin()
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert len(result["data"]) == 1
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_get_all_bookings_admin_with_status_filter(booking_management_service, mock_supabase):
    """Test admin getting all bookings with status filter"""
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_all_bookings_admin(status="pending")
    
    assert result["EC"] == 0
    assert result["total"] == 0


# ============================================
# Service Tests: get_user_bookings_admin
# ============================================

@pytest.mark.asyncio
async def test_get_user_bookings_admin_success(booking_management_service, mock_supabase, sample_user_id, sample_booking_with_tour):
    """Test admin getting bookings of specific user"""
    mock_result = MagicMock()
    mock_result.data = [sample_booking_with_tour]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings_admin(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert len(result["data"]) == 1
    assert result["data"][0]["tour_name"] == "Tour Đà Lạt 3N2Đ"


# ============================================
# Service Tests: get_booking_detail_admin
# ============================================

@pytest.mark.asyncio
async def test_get_booking_detail_admin_success(booking_management_service, mock_supabase, sample_booking_with_tour):
    """Test admin getting booking detail"""
    booking_id = sample_booking_with_tour["booking_id"]
    
    mock_result = MagicMock()
    mock_result.data = [sample_booking_with_tour]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_booking_detail_admin(booking_id=booking_id)
    
    assert result["EC"] == 0
    assert result["EM"] == "Success"
    assert result["data"]["booking_id"] == booking_id
    assert result["data"]["tour_package"] is not None


@pytest.mark.asyncio
async def test_get_booking_detail_admin_not_found(booking_management_service, mock_supabase):
    """Test admin getting non-existent booking detail"""
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_booking_detail_admin(booking_id=str(uuid4()))
    
    assert result["EC"] == 1
    assert "not found" in result["EM"].lower()


# ============================================
# Endpoint Tests (with authentication)
# ============================================

@pytest.mark.asyncio
async def test_get_my_bookings_endpoint_success(mock_supabase, sample_user, sample_booking_with_tour):
    """Test GET /my-bookings endpoint"""
    from app.v1.services.booking_management_service import BookingManagementService
    
    service = BookingManagementService(mock_supabase)
    
    # Mock service method
    with patch.object(service, 'get_user_bookings', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": [{
                "booking_id": sample_booking_with_tour["booking_id"],
                "tour_name": "Tour Đà Lạt 3N2Đ",
                "destination": "Đà Lạt",
                "start_date": "2025-01-15",
                "end_date": "2025-01-17",
                "number_of_people": 2,
                "total_amount": 9000000,
                "status": "confirmed",
                "created_at": datetime.now().isoformat()
            }],
            "total": 1
        }
        
        # Mock dependency
        with patch('app.v1.api.endpoints.booking_management.get_booking_management_service') as mock_service_dep:
            mock_service_dep.return_value = service
            
            result = await get_my_bookings(
                status=None,
                limit=None,
                offset=None,
                current_user=sample_user,
                service=service
            )
            
            assert result.EC == 0
            assert result.total == 1
            assert len(result.data) == 1


@pytest.mark.asyncio
async def test_get_my_booking_detail_endpoint_success(mock_supabase, sample_user, sample_booking_with_tour):
    """Test GET /my-bookings/{booking_id} endpoint"""
    from app.v1.services.booking_management_service import BookingManagementService
    
    service = BookingManagementService(mock_supabase)
    booking_id = uuid4()
    
    # Mock service method
    with patch.object(service, 'get_user_booking_detail', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": {
                "booking_id": str(booking_id),
                "status": "confirmed",
                "number_of_people": 2,
                "total_amount": 9000000,
                "contact_name": "Nguyen Van A",
                "contact_phone": "0123456789",
                "special_requests": "Phòng view đẹp",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tour_package": {
                    "package_id": str(uuid4()),
                    "package_name": "Tour Đà Lạt 3N2Đ",
                    "destination": "Đà Lạt",
                    "description": "Khám phá thành phố ngàn hoa",
                    "duration_days": 3,
                    "start_date": "2025-01-15",
                    "end_date": "2025-01-17",
                    "price": 4500000,
                    "image_urls": "url1|url2"
                }
            }
        }
        
        result = await get_my_booking_detail(
            booking_id=booking_id,
            current_user=sample_user,
            service=service
        )
        
        assert result.EC == 0
        assert str(result.data.booking_id) == str(booking_id)


@pytest.mark.asyncio
async def test_get_my_booking_detail_endpoint_not_found(mock_supabase, sample_user):
    """Test GET /my-bookings/{booking_id} endpoint with non-existent booking"""
    from app.v1.services.booking_management_service import BookingManagementService
    
    service = BookingManagementService(mock_supabase)
    booking_id = uuid4()
    
    # Mock service method
    with patch.object(service, 'get_user_booking_detail', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 1,
            "EM": "Booking not found or access denied",
            "data": None
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_my_booking_detail(
                booking_id=booking_id,
                current_user=sample_user,
                service=service
            )
        
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_all_bookings_admin_endpoint_success(mock_supabase, sample_admin):
    """Test GET /admin/all endpoint"""
    from app.v1.services.booking_management_service import BookingManagementService
    
    service = BookingManagementService(mock_supabase)
    
    # Mock service method
    with patch.object(service, 'get_all_bookings_admin', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": [{
                "booking_id": str(uuid4()),
                "user_id": str(uuid4()),
                "user_email": "user@example.com",
                "user_full_name": "Nguyen Van A",
                "tour_name": "Tour Đà Lạt 3N2Đ",
                "destination": "Đà Lạt",
                "start_date": "2025-01-15",
                "number_of_people": 2,
                "total_amount": 9000000,
                "status": "confirmed",
                "created_at": datetime.now().isoformat()
            }],
            "total": 1
        }
        
        result = await get_all_bookings_admin(
            status=None,
            limit=None,
            offset=None,
            current_admin=sample_admin,
            service=service
        )
        
        assert result.EC == 0
        assert result.total == 1


@pytest.mark.asyncio
async def test_get_user_bookings_admin_endpoint_success(mock_supabase, sample_admin, sample_user_id):
    """Test GET /admin/user/{user_id} endpoint"""
    from app.v1.services.booking_management_service import BookingManagementService
    
    service = BookingManagementService(mock_supabase)
    
    # Mock service method
    # get_user_bookings_admin returns AdminBookingListItem format with user_id
    test_user_id = uuid4()
    with patch.object(service, 'get_user_bookings_admin', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": [{
                "booking_id": str(uuid4()),
                "user_id": str(test_user_id),
                "tour_name": "Tour Đà Lạt 3N2Đ",
                "destination": "Đà Lạt",
                "start_date": "2025-01-15",
                "number_of_people": 2,
                "total_amount": 9000000,
                "status": "confirmed",
                "created_at": datetime.now().isoformat()
            }],
            "total": 1
        }
        
        result = await get_user_bookings_admin(
            user_id=uuid4(),
            status=None,
            limit=None,
            offset=None,
            current_admin=sample_admin,
            service=service
        )
        
        assert result.EC == 0
        assert result.total == 1


@pytest.mark.asyncio
async def test_get_booking_detail_admin_endpoint_success(mock_supabase, sample_admin, sample_booking_with_tour):
    """Test GET /admin/{booking_id} endpoint"""
    from app.v1.services.booking_management_service import BookingManagementService
    
    service = BookingManagementService(mock_supabase)
    booking_id = uuid4()
    
    # Mock service method
    with patch.object(service, 'get_booking_detail_admin', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": {
                "booking_id": str(booking_id),
                "status": "confirmed",
                "number_of_people": 2,
                "total_amount": 9000000,
                "contact_name": "Nguyen Van A",
                "contact_phone": "0123456789",
                "special_requests": "Phòng view đẹp",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tour_package": {
                    "package_id": str(uuid4()),
                    "package_name": "Tour Đà Lạt 3N2Đ",
                    "destination": "Đà Lạt",
                    "description": "Khám phá thành phố ngàn hoa",
                    "duration_days": 3,
                    "start_date": "2025-01-15",
                    "end_date": "2025-01-17",
                    "price": 4500000,
                    "image_urls": "url1|url2"
                }
            }
        }
        
        result = await get_booking_detail_admin(
            booking_id=booking_id,
            current_admin=sample_admin,
            service=service
        )
        
        assert result.EC == 0
        assert str(result.data.booking_id) == str(booking_id)


@pytest.mark.asyncio
async def test_get_booking_detail_admin_endpoint_not_found(mock_supabase, sample_admin):
    """Test GET /admin/{booking_id} endpoint with non-existent booking"""
    from app.v1.services.booking_management_service import BookingManagementService
    
    service = BookingManagementService(mock_supabase)
    booking_id = uuid4()
    
    # Mock service method
    with patch.object(service, 'get_booking_detail_admin', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 1,
            "EM": "Booking not found",
            "data": None
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_booking_detail_admin(
                booking_id=booking_id,
                current_admin=sample_admin,
                service=service
            )
        
        assert exc_info.value.status_code == 404


# ============================================
# Error Handling Tests
# ============================================

@pytest.mark.asyncio
async def test_get_user_bookings_exception_handling(booking_management_service, mock_supabase, sample_user_id):
    """Test exception handling in get_user_bookings"""
    mock_supabase.table.side_effect = Exception("Database error")
    
    result = await booking_management_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 1
    assert "Error" in result["EM"]


@pytest.mark.asyncio
async def test_get_user_booking_detail_exception_handling(booking_management_service, mock_supabase, sample_user_id):
    """Test exception handling in get_user_booking_detail"""
    mock_supabase.table.side_effect = Exception("Database error")
    
    result = await booking_management_service.get_user_booking_detail(
        booking_id=str(uuid4()),
        user_id=sample_user_id
    )
    
    assert result["EC"] == 2
    assert "Error" in result["EM"]


# ============================================
# Edge Cases Tests
# ============================================

@pytest.mark.asyncio
async def test_get_user_bookings_with_invalid_status(booking_management_service, mock_supabase, sample_user_id):
    """Test getting bookings with invalid status value"""
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    # Invalid status should still work (filter returns empty)
    result = await booking_management_service.get_user_bookings(
        user_id=sample_user_id,
        status="invalid_status_xyz"
    )
    
    assert result["EC"] == 0
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_get_user_bookings_pagination_edge_cases(booking_management_service, mock_supabase, sample_user_id):
    """Test pagination edge cases"""
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
    
    # Test with limit=1
    result = await booking_management_service.get_user_bookings(
        user_id=sample_user_id,
        limit=1
    )
    assert result["EC"] == 0
    
    # Test with large offset
    result = await booking_management_service.get_user_bookings(
        user_id=sample_user_id,
        offset=999999
    )
    assert result["EC"] == 0
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_get_user_bookings_missing_tour_package(booking_management_service, mock_supabase, sample_user_id):
    """Test getting bookings when tour_packages is None or missing"""
    booking_data = {
        "booking_id": str(uuid4()),
        "number_of_people": 2,
        "total_amount": 9000000,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "tour_packages": None  # Missing tour package
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert len(result["data"]) == 1
    assert result["data"][0]["tour_name"] == "Unknown Tour"
    assert result["data"][0]["destination"] == "Unknown"


@pytest.mark.asyncio
async def test_get_user_bookings_tour_package_as_list(booking_management_service, mock_supabase, sample_user_id):
    """Test handling when tour_packages is returned as list"""
    booking_data = {
        "booking_id": str(uuid4()),
        "number_of_people": 2,
        "total_amount": 9000000,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "tour_packages": [{  # List format
            "package_name": "Tour Đà Lạt",
            "destination": "Đà Lạt",
            "start_date": "2025-01-15",
            "end_date": "2025-01-17"
        }]
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["data"][0]["tour_name"] == "Tour Đà Lạt"


@pytest.mark.asyncio
async def test_get_user_bookings_empty_tour_package_list(booking_management_service, mock_supabase, sample_user_id):
    """Test handling when tour_packages is empty list"""
    booking_data = {
        "booking_id": str(uuid4()),
        "number_of_people": 2,
        "total_amount": 9000000,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "tour_packages": []  # Empty list
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["data"][0]["tour_name"] == "Unknown Tour"


@pytest.mark.asyncio
async def test_get_user_booking_detail_wrong_user(booking_management_service, mock_supabase):
    """Test getting booking detail with wrong user_id (should return not found)"""
    booking_id = str(uuid4())
    correct_user_id = str(uuid4())
    wrong_user_id = str(uuid4())
    
    # Mock returns empty because user_id doesn't match
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_booking_detail(
        booking_id=booking_id,
        user_id=wrong_user_id
    )
    
    assert result["EC"] == 1
    assert "not found" in result["EM"].lower() or "denied" in result["EM"].lower()


@pytest.mark.asyncio
async def test_get_user_booking_detail_missing_tour_package(booking_management_service, mock_supabase, sample_user_id):
    """Test getting booking detail when tour_package is None"""
    booking_id = str(uuid4())
    booking_data = {
        "booking_id": booking_id,
        "user_id": sample_user_id,
        "number_of_people": 2,
        "total_amount": 9000000,
        "contact_name": "Nguyen Van A",
        "contact_phone": "0123456789",
        "special_requests": None,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "tour_packages": None
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_booking_detail(
        booking_id=booking_id,
        user_id=sample_user_id
    )
    
    assert result["EC"] == 0
    assert result["data"]["tour_package"] is None


@pytest.mark.asyncio
async def test_get_all_bookings_admin_empty_database(booking_management_service, mock_supabase):
    """Test admin getting all bookings when database is empty"""
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_all_bookings_admin()
    
    assert result["EC"] == 0
    assert result["total"] == 0
    assert result["data"] == []


@pytest.mark.asyncio
async def test_get_all_bookings_admin_missing_user_info(booking_management_service, mock_supabase):
    """Test admin getting bookings when user info is missing"""
    booking_data = {
        "booking_id": str(uuid4()),
        "user_id": str(uuid4()),
        "number_of_people": 2,
        "total_amount": 9000000,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "tour_packages": {
            "package_name": "Tour Đà Lạt",
            "destination": "Đà Lạt",
            "start_date": "2025-01-15"
        }
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    # Mock users query returns empty
    mock_user_result = MagicMock()
    mock_user_result.data = []
    
    mock_user_query = MagicMock()
    mock_user_query.select.return_value = mock_user_query
    mock_user_query.eq.return_value = mock_user_query
    mock_user_query.execute.return_value = mock_user_result
    
    def table_side_effect(table_name):
        if table_name == "bookings":
            return mock_query
        elif table_name == "users":
            return mock_user_query
        return MagicMock()
    
    mock_supabase.table.side_effect = table_side_effect
    
    result = await booking_management_service.get_all_bookings_admin()
    
    assert result["EC"] == 0
    assert result["data"][0]["user_email"] is None
    assert result["data"][0]["user_full_name"] is None


@pytest.mark.asyncio
async def test_get_user_bookings_admin_invalid_user_id(booking_management_service, mock_supabase):
    """Test admin getting bookings for non-existent user"""
    invalid_user_id = str(uuid4())
    
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings_admin(user_id=invalid_user_id)
    
    assert result["EC"] == 0
    assert result["total"] == 0
    assert result["data"] == []


@pytest.mark.asyncio
async def test_get_booking_detail_admin_missing_tour_package(booking_management_service, mock_supabase):
    """Test admin getting booking detail when tour_package is missing"""
    booking_id = str(uuid4())
    booking_data = {
        "booking_id": booking_id,
        "number_of_people": 2,
        "total_amount": 9000000,
        "contact_name": "Nguyen Van A",
        "contact_phone": "0123456789",
        "special_requests": None,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "tour_packages": None
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_booking_detail_admin(booking_id=booking_id)
    
    assert result["EC"] == 0
    assert result["data"]["tour_package"] is None


@pytest.mark.asyncio
async def test_get_user_bookings_special_characters_in_data(booking_management_service, mock_supabase, sample_user_id):
    """Test handling special characters in tour data"""
    booking_data = {
        "booking_id": str(uuid4()),
        "number_of_people": 2,
        "total_amount": 9000000,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "tour_packages": {
            "package_name": "Tour Đà Lạt & Nha Trang <script>alert('xss')</script>",
            "destination": "Đà Lạt / Nha Trang",
            "start_date": "2025-01-15",
            "end_date": "2025-01-17"
        }
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert "<script>" in result["data"][0]["tour_name"]  # Should preserve data as-is


@pytest.mark.asyncio
async def test_get_user_bookings_very_large_total_amount(booking_management_service, mock_supabase, sample_user_id):
    """Test handling very large total_amount values"""
    booking_data = {
        "booking_id": str(uuid4()),
        "number_of_people": 100,
        "total_amount": 999999999999.99,  # Very large amount
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "tour_packages": {
            "package_name": "Tour VIP",
            "destination": "Đà Lạt",
            "start_date": "2025-01-15"
        }
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert result["data"][0]["total_amount"] == 999999999999.99


@pytest.mark.asyncio
async def test_get_user_bookings_all_status_values(booking_management_service, mock_supabase, sample_user_id):
    """Test getting bookings with all possible status values"""
    statuses = ["pending", "confirmed", "cancelled", "completed", "otp_sent"]
    
    for status in statuses:
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_query
        
        result = await booking_management_service.get_user_bookings(
            user_id=sample_user_id,
            status=status
        )
        
        assert result["EC"] == 0


@pytest.mark.asyncio
async def test_get_user_booking_detail_empty_special_requests(booking_management_service, mock_supabase, sample_user_id, sample_booking_with_tour):
    """Test getting booking detail with empty special_requests"""
    booking_id = sample_booking_with_tour["booking_id"]
    booking_data = sample_booking_with_tour.copy()
    booking_data["special_requests"] = ""
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_booking_detail(
        booking_id=booking_id,
        user_id=sample_user_id
    )
    
    assert result["EC"] == 0
    assert result["data"]["special_requests"] == ""


@pytest.mark.asyncio
async def test_get_all_bookings_admin_database_timeout(booking_management_service, mock_supabase):
    """Test handling database timeout error"""
    import asyncio
    
    async def timeout_error():
        await asyncio.sleep(0.01)
        raise TimeoutError("Database connection timeout")
    
    mock_supabase.table.side_effect = timeout_error
    
    result = await booking_management_service.get_all_bookings_admin()
    
    assert result["EC"] == 1
    assert "Error" in result["EM"]


@pytest.mark.asyncio
async def test_get_user_bookings_unicode_characters(booking_management_service, mock_supabase, sample_user_id):
    """Test handling unicode characters in tour names"""
    booking_data = {
        "booking_id": str(uuid4()),
        "number_of_people": 2,
        "total_amount": 9000000,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "tour_packages": {
            "package_name": "Tour Đà Lạt 🏔️ 日本 🇯🇵",
            "destination": "Đà Lạt",
            "start_date": "2025-01-15"
        }
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings(user_id=sample_user_id)
    
    assert result["EC"] == 0
    assert "🏔️" in result["data"][0]["tour_name"]


@pytest.mark.asyncio
async def test_get_user_bookings_max_limit(booking_management_service, mock_supabase, sample_user_id):
    """Test getting bookings with maximum limit"""
    mock_result = MagicMock()
    mock_result.data = []
    mock_result.count = 0
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_bookings(
        user_id=sample_user_id,
        limit=100  # Max limit
    )
    
    assert result["EC"] == 0


@pytest.mark.asyncio
async def test_get_user_booking_detail_malformed_tour_package(booking_management_service, mock_supabase, sample_user_id):
    """Test handling malformed tour_package data"""
    booking_id = str(uuid4())
    booking_data = {
        "booking_id": booking_id,
        "user_id": sample_user_id,
        "number_of_people": 2,
        "total_amount": 9000000,
        "contact_name": "Nguyen Van A",
        "contact_phone": "0123456789",
        "special_requests": None,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "tour_packages": "invalid_string"  # Wrong type
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_management_service.get_user_booking_detail(
        booking_id=booking_id,
        user_id=sample_user_id
    )
    
    # Should handle gracefully
    assert result["EC"] == 0
    assert result["data"]["tour_package"] is None


@pytest.mark.asyncio
async def test_get_all_bookings_admin_partial_user_info(booking_management_service, mock_supabase):
    """Test admin getting bookings when user has partial info"""
    booking_data = {
        "booking_id": str(uuid4()),
        "user_id": str(uuid4()),
        "number_of_people": 2,
        "total_amount": 9000000,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "tour_packages": {
            "package_name": "Tour Đà Lạt",
            "destination": "Đà Lạt",
            "start_date": "2025-01-15"
        }
    }
    
    mock_result = MagicMock()
    mock_result.data = [booking_data]
    mock_result.count = 1
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    # Mock users query returns partial info
    mock_user_result = MagicMock()
    mock_user_result.data = [{
        "email": "user@example.com",
        # full_name is missing
    }]
    
    mock_user_query = MagicMock()
    mock_user_query.select.return_value = mock_user_query
    mock_user_query.eq.return_value = mock_user_query
    mock_user_query.execute.return_value = mock_user_result
    
    def table_side_effect(table_name):
        if table_name == "bookings":
            return mock_query
        elif table_name == "users":
            return mock_user_query
        return MagicMock()
    
    mock_supabase.table.side_effect = table_side_effect
    
    result = await booking_management_service.get_all_bookings_admin()
    
    assert result["EC"] == 0
    assert result["data"][0]["user_email"] == "user@example.com"
    assert result["data"][0]["user_full_name"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

