"""
Test cases for Booking Service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

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
        "contact_phone": "0123456789",
        "special_requests": "Phòng view đẹp"
    }


@pytest.fixture
def sample_booking_response():
    """Sample booking response from database"""
    booking_id = str(uuid4())
    package_id = str(uuid4())
    user_id = str(uuid4())
    now = datetime.now().isoformat()
    
    return {
        "booking_id": booking_id,
        "package_id": package_id,
        "user_id": user_id,
        "number_of_people": 2,
        "total_amount": 5000000,
        "contact_name": "Nguyen Van A",
        "contact_phone": "0123456789",
        "special_requests": "Phòng view đẹp",
        "status": "pending",
        "created_at": now,
        "updated_at": now
    }


# Test get_all_bookings
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


# Test get_booking_by_id
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


# Test create_booking
@pytest.mark.asyncio
async def test_create_booking_success(booking_service, mock_supabase, sample_booking_data, sample_booking_response):
    """Test creating booking successfully"""
    # Mock package check
    mock_package_result = MagicMock()
    mock_package_result.data = [{
        "available_slots": 10,
        "is_active": True,
        "price": 2500000
    }]
    
    # Mock booking insert
    mock_booking_result = MagicMock()
    # total_amount should be price * number_of_people = 2,500,000 * 2 = 5,000,000
    sample_created = sample_booking_response.copy()
    sample_created["total_amount"] = 2500000 * sample_booking_data["number_of_people"]
    mock_booking_result.data = [sample_created]
    
    # Mock update slots
    mock_update_result = MagicMock()
    mock_update_result.data = [{"available_slots": 8}]
    
    def table_side_effect(table_name):
        if table_name == "tour_packages":
            # Build separate mocks for select and update chains to avoid execute() collision
            tp_root = MagicMock()
            tp_select = MagicMock()
            tp_update = MagicMock()

            # select chain returns tp_select, which executes to package_result
            tp_root.select.return_value = tp_select
            tp_select.eq.return_value = tp_select
            tp_select.execute.return_value = mock_package_result

            # update chain returns tp_update, which executes to update_result
            tp_root.update.return_value = tp_update
            tp_update.eq.return_value = tp_update
            tp_update.execute.return_value = mock_update_result

            return tp_root
        else:  # bookings
            bk = MagicMock()
            bk.insert.return_value = bk
            bk.execute.return_value = mock_booking_result
            return bk
    
    mock_supabase.table.side_effect = table_side_effect
    
    result = await booking_service.create_booking(sample_booking_data)
    
    assert result["EC"] == 0
    assert result["EM"] == "Booking created successfully"
    assert result["data"]["booking_id"] == sample_created["booking_id"]
    assert result["data"]["total_amount"] == 2500000 * sample_booking_data["number_of_people"]


@pytest.mark.asyncio
async def test_create_booking_package_not_found(booking_service, mock_supabase, sample_booking_data):
    """Test creating booking with non-existent package"""
    mock_result = MagicMock()
    mock_result.data = []
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.create_booking(sample_booking_data)
    
    assert result["EC"] == 1
    assert result["EM"] == "Tour package not found"


@pytest.mark.asyncio
async def test_create_booking_package_inactive(booking_service, mock_supabase, sample_booking_data):
    """Test creating booking for inactive package"""
    mock_result = MagicMock()
    mock_result.data = [{
        "available_slots": 10,
        "is_active": False,
        "price": 2500000
    }]
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = mock_result
    
    mock_supabase.table.return_value = mock_query
    
    result = await booking_service.create_booking(sample_booking_data)
    
    assert result["EC"] == 2
    assert result["EM"] == "Tour package is not active"


@pytest.mark.asyncio
async def test_create_booking_not_enough_slots(booking_service, mock_supabase, sample_booking_data):
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
    
    result = await booking_service.create_booking(sample_booking_data)
    
    assert result["EC"] == 3
    assert "Not enough slots available" in result["EM"]


# Test update_booking
@pytest.mark.asyncio
async def test_update_booking_success(booking_service, mock_supabase, sample_booking_response):
    """Test updating booking successfully"""
    # Mock get_booking_by_id
    with patch.object(booking_service, 'get_booking_by_id', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": sample_booking_response
        }
        
        # Mock update result (e.g. status change)
        updated_booking = sample_booking_response.copy()
        updated_booking["status"] = "confirmed"
        
        mock_result = MagicMock()
        mock_result.data = [updated_booking]
        
        mock_query = MagicMock()
        mock_query.update.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_query
        
        update_data = {"status": "confirmed"}
        result = await booking_service.update_booking(sample_booking_response["booking_id"], update_data)
        
        assert result["EC"] == 0
        assert result["EM"] == "Booking updated successfully"
        assert result["data"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_update_booking_recalculate_total(booking_service, mock_supabase, sample_booking_response):
    """Test updating number_of_people recalculates total_amount"""
    # Existing booking
    with patch.object(booking_service, 'get_booking_by_id', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": sample_booking_response
        }

        # Mock tour_packages select to provide price and slots
        mock_pkg_select = MagicMock()
        mock_pkg_result = MagicMock()
        mock_pkg_result.data = [{
            "available_slots": 10,
            "price": 2500000
        }]
        mock_pkg_select.select.return_value = mock_pkg_select
        mock_pkg_select.eq.return_value = mock_pkg_select
        mock_pkg_select.execute.return_value = mock_pkg_result

        # Mock bookings update to return recalculated total_amount
        new_people = 3
        updated_total = 2500000 * new_people
        updated_booking = sample_booking_response.copy()
        updated_booking["number_of_people"] = new_people
        updated_booking["total_amount"] = updated_total

        mock_update_result = MagicMock()
        mock_update_result.data = [updated_booking]

        # Mock tour_packages update (for slots change)
        mock_pkg_update = MagicMock()
        mock_pkg_update.update.return_value = mock_pkg_update
        mock_pkg_update.eq.return_value = mock_pkg_update
        mock_pkg_update.execute.return_value = MagicMock()

        def table_side_effect(table_name):
            if table_name == "tour_packages":
                # Return an object supporting select and update chains
                # Use a simple object that switches behavior based on last called method
                return mock_pkg_select
            elif table_name == "bookings":
                mock_book_update = MagicMock()
                mock_book_update.update.return_value = mock_book_update
                mock_book_update.eq.return_value = mock_book_update
                mock_book_update.execute.return_value = mock_update_result
                return mock_book_update
            return MagicMock()

        mock_supabase.table.side_effect = table_side_effect

        result = await booking_service.update_booking(sample_booking_response["booking_id"], {"number_of_people": new_people})

        assert result["EC"] == 0
        assert result["data"]["number_of_people"] == new_people
        assert result["data"]["total_amount"] == updated_total


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


# Test delete_booking
@pytest.mark.asyncio
async def test_delete_booking_success(booking_service, mock_supabase, sample_booking_response):
    """Test deleting booking successfully"""
    with patch.object(booking_service, 'get_booking_by_id', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "EC": 0,
            "EM": "Success",
            "data": sample_booking_response
        }
        
        # Mock delete
        mock_delete_result = MagicMock()
        mock_delete_result.data = [sample_booking_response]
        
        # Mock get package slots
        mock_package_result = MagicMock()
        mock_package_result.data = [{"available_slots": 8}]
        
        # Mock update slots
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


# Test validation scenarios
@pytest.mark.asyncio
async def test_create_booking_with_special_requests(booking_service, mock_supabase, sample_booking_data):
    """Test creating booking with special requests"""
    sample_booking_data["special_requests"] = "Muốn phòng tầng cao"
    
    mock_package_result = MagicMock()
    mock_package_result.data = [{
        "available_slots": 10,
        "is_active": True,
        "price": 2500000
    }]
    
    mock_booking_result = MagicMock()
    computed_total = 2500000 * sample_booking_data["number_of_people"]
    mock_booking_result.data = [{**sample_booking_data, "booking_id": str(uuid4()), "status": "pending", "total_amount": computed_total}]
    
    mock_update_result = MagicMock()
    mock_update_result.data = [{"available_slots": 8}]
    
    def table_side_effect(table_name):
        if table_name == "tour_packages":
            tp_root = MagicMock()
            tp_select = MagicMock()
            tp_update = MagicMock()

            tp_root.select.return_value = tp_select
            tp_select.eq.return_value = tp_select
            tp_select.execute.return_value = mock_package_result

            tp_root.update.return_value = tp_update
            tp_update.eq.return_value = tp_update
            tp_update.execute.return_value = mock_update_result

            return tp_root
        else:
            bk = MagicMock()
            bk.insert.return_value = bk
            bk.execute.return_value = mock_booking_result
            return bk
    
    mock_supabase.table.side_effect = table_side_effect
    
    result = await booking_service.create_booking(sample_booking_data)
    
    assert result["EC"] == 0
    assert result["data"]["total_amount"] == 2500000 * sample_booking_data["number_of_people"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
