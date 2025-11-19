"""
Unit Tests for Booking Tools
Simple tests to verify bookings are saved to database
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

load_dotenv()

from src.mcp_server.tools.booking_tools import _create_booking_impl
from supabase import create_client, Client


@pytest.fixture
def sample_user():
    """Sample user data"""
    return {
        "user_id": "user_123",
        "phone_number": "0912345678",
        "full_name": "Nguyễn Văn A",
        "email": "test@example.com"
    }


@pytest.fixture
def sample_package():
    """Sample tour package data"""
    return {
        "package_id": "package_123",
        "package_name": "Tour Đà Lạt 3 ngày 2 đêm",
        "destination": "Đà Lạt",
        "price": 2500000.0,
        "available_slots": 10,
        "is_active": True,
        "duration_days": 3,
        "start_date": "2024-12-25",
        "end_date": "2024-12-27"
    }


@pytest.fixture
def sample_booking():
    """Sample booking data"""
    return {
        "booking_id": "booking_abc123",
        "user_id": "user_123",
        "package_id": "package_123",
        "number_of_people": 2,
        "total_amount": 5000000.0,
        "travel_date": "2024-12-25",
        "contact_name": "Nguyễn Văn A",
        "contact_phone": "0912345678",
        "special_requests": "Window seat preferred",
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


@patch('src.mcp_server.tools.booking_tools.create_client')
@pytest.mark.asyncio
async def test_create_booking_saves_to_database(
    mock_create_client,
    sample_user,
    sample_package,
    sample_booking
):
    """Test that create_booking tool saves data to bookings table"""
    # Setup mock Supabase client
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    # Mock user lookup - user exists
    user_select = MagicMock()
    user_select.eq.return_value = user_select
    user_response = MagicMock()
    user_response.data = [sample_user]
    user_select.execute.return_value = user_response
    
    # Mock package lookup - package exists
    package_select = MagicMock()
    package_select.eq.return_value = package_select
    package_response = MagicMock()
    package_response.data = [sample_package]
    package_select.execute.return_value = package_response
    
    # Mock booking insert - THIS IS WHAT WE'RE TESTING
    booking_insert = MagicMock()
    booking_response = MagicMock()
    booking_response.data = [sample_booking]
    booking_insert.execute.return_value = booking_response
    
    # Mock slots update
    slots_update = MagicMock()
    slots_update.eq.return_value = slots_update
    update_response = MagicMock()
    update_response.data = [sample_package]
    slots_update.execute.return_value = update_response
    
    # Mock verification query
    verify_select = MagicMock()
    verify_select.eq.return_value = verify_select
    verify_response = MagicMock()
    verify_response.data = [sample_booking]
    verify_select.execute.return_value = verify_response
    
    # Setup table side effect
    def table_side_effect(table_name):
        mock_tbl = MagicMock()
        if table_name == "users":
            mock_tbl.select.return_value = user_select
        elif table_name == "tour_packages":
            mock_tbl.select.return_value = package_select
            mock_tbl.update.return_value = slots_update
        elif table_name == "bookings":
            mock_tbl.select.return_value = verify_select
            mock_tbl.insert.return_value = booking_insert
        return mock_tbl
    
    mock_client.table.side_effect = table_side_effect
    
    # Call the tool
    result = await _create_booking_impl(
        user_phone="0912345678",
        package_id="package_123",
        number_of_people=2,
        special_requests="Window seat preferred"
    )
    
    # Verify booking was inserted (verify insert was called)
    assert booking_insert.execute.called, "Booking insert.execute() should be called to save to database"
    
    # Verify success response
    assert result["success"] is True
    assert "booking_id" in result
    assert result["booking_id"] == "booking_abc123"
    
    # Verify the booking data structure
    assert "confirmation" in result
    assert result["confirmation"]["number_of_people"] == 2
    assert result["confirmation"]["total_amount"] == 5000000.0
    assert result["confirmation"]["special_requests"] == "Window seat preferred"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_booking_saves_to_real_database():
    """Integration test: Verify booking is actually saved to Supabase database"""
    # Check if Supabase credentials are configured
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        pytest.skip("Supabase credentials not configured - skipping integration test")
    
    # Test connection
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test connection by querying tables
        print("🔍 Testing database connection...")
        tour_packages = supabase.table("tour_packages").select("package_id").limit(1).execute()
        print(f"✅ Database connection successful")
        
        # Verify users table exists
        users = supabase.table("users").select("user_id").limit(1).execute()
        print(f"✅ Users table exists and accessible")
        
        # Verify bookings table exists
        bookings = supabase.table("bookings").select("booking_id").limit(1).execute()
        print(f"✅ Bookings table exists and accessible")
        
        # Get a real package_id from database
        packages = supabase.table("tour_packages")\
            .select("package_id, package_name, available_slots")\
            .eq("is_active", True)\
            .gt("available_slots", 0)\
            .limit(1)\
            .execute()
        
        if not packages.data or len(packages.data) == 0:
            pytest.skip("No active packages with available slots found - skipping integration test")
        
        real_package = packages.data[0]
        package_id = str(real_package["package_id"])
        
        print(f"\n📦 Testing with real package: {real_package.get('package_name')} (ID: {package_id})")
        print(f"   Available slots: {real_package.get('available_slots')}")
        
        # Test phone number - use unique timestamp-based phone
        test_phone = f"09{datetime.now().strftime('%m%d%H%M%S')[-8:]}"
        print(f"\n📞 Testing with phone: {test_phone}")
        
        # Get initial booking count
        initial_bookings = supabase.table("bookings")\
            .select("booking_id", count="exact")\
            .eq("contact_phone", test_phone)\
            .execute()
        initial_count = len(initial_bookings.data) if initial_bookings.data else 0
        print(f"📊 Initial bookings for {test_phone}: {initial_count}")
        
        # Test actual booking creation
        result = await _create_booking_impl(
            user_phone=test_phone,
            package_id=package_id,
            number_of_people=1,
            special_requests="Integration test booking"
        )
        
        # Verify result
        assert result["success"] is True, f"Booking creation failed: {result.get('error')}"
        booking_id = result.get("booking_id")
        assert booking_id is not None, "Booking ID should not be None"
        
        print(f"\n✅ Booking created successfully: {booking_id}")
        
        # Wait a bit for database to commit
        import asyncio
        await asyncio.sleep(1)
        
        # Query back from database to verify data is ACTUALLY SAVED
        print(f"\n🔍 Verifying booking exists in database...")
        verify = supabase.table("bookings")\
            .select("*")\
            .eq("booking_id", booking_id)\
            .execute()
        
        if not verify.data or len(verify.data) == 0:
            pytest.fail(f"❌ CRITICAL: Booking {booking_id} NOT FOUND in database after creation!")
        
        saved_booking = verify.data[0]
        print(f"✅ VERIFIED: Booking {booking_id} EXISTS in database!")
        print(f"   📝 Saved data:")
        print(f"      - booking_id: {saved_booking.get('booking_id')}")
        print(f"      - user_id: {saved_booking.get('user_id')}")
        print(f"      - package_id: {saved_booking.get('package_id')}")
        print(f"      - number_of_people: {saved_booking.get('number_of_people')}")
        print(f"      - total_amount: {saved_booking.get('total_amount')}")
        print(f"      - status: {saved_booking.get('status')}")
        print(f"      - special_requests: {saved_booking.get('special_requests')}")
        
        # Verify all data matches
        assert saved_booking.get("booking_id") == booking_id
        assert saved_booking.get("package_id") == package_id
        assert saved_booking.get("number_of_people") == 1
        assert saved_booking.get("special_requests") == "Integration test booking"
        assert saved_booking.get("contact_phone") == test_phone
        
        # Verify user was created
        user_check = supabase.table("users")\
            .select("*")\
            .eq("phone_number", test_phone)\
            .execute()
        
        if user_check.data and len(user_check.data) > 0:
            print(f"✅ User created in database: {user_check.data[0].get('user_id')}")
        
        # Verify package slots were updated
        updated_package = supabase.table("tour_packages")\
            .select("available_slots")\
            .eq("package_id", package_id)\
            .execute()
        
        if updated_package.data:
            new_slots = updated_package.data[0].get("available_slots")
            original_slots = real_package.get("available_slots")
            expected_slots = original_slots - 1
            print(f"✅ Package slots updated: {original_slots} -> {new_slots} (expected: {expected_slots})")
            assert new_slots == expected_slots, f"Slots not updated correctly: {new_slots} != {expected_slots}"
        
        print(f"\n🎉 SUCCESS: All data verified - booking is correctly saved to database!")
        
    except Exception as e:
        import traceback
        print(f"\n❌ Test failed with error:")
        print(traceback.format_exc())
        pytest.fail(f"❌ Database connection or test failed: {str(e)}")
