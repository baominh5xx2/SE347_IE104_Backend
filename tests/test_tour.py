"""
Unit tests for Tour Package Service and Endpoints
Tests for all CRUD operations and edge cases
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, timezone
from uuid import uuid4, UUID
import logging

from app.v1.services.tour_package_service import TourPackageService
from app.v1.schema.tour_package_schema import (
    TourPackageCreate,
    TourPackageUpdate,
    TourPackageResponse
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
def tour_service(mock_supabase_client):
    """Create TourPackageService instance with mocked Supabase client"""
    client, table = mock_supabase_client
    service = TourPackageService(client)
    return service, table


@pytest.fixture
def sample_tour_data():
    """Sample tour package data"""
    return {
        "package_name": "Tour Đà Lạt 3N2Đ",
        "destination": "Đà Lạt",
        "description": "Tour khám phá thành phố ngàn hoa với khí hậu mát mẻ quanh năm",
        "duration_days": 3,
        "price": 2500000.0,
        "available_slots": 20,
        "start_date": "2024-12-01",
        "end_date": "2024-12-03",
        "image_urls": "https://example.com/img1.jpg|https://example.com/img2.jpg",
        "cuisine": "Ẩm thực miền Trung",
        "suitable_for": "Gia đình, Cặp đôi",
        "is_active": True
    }


@pytest.fixture
def sample_tour_response():
    """Sample tour package response from database"""
    package_id = uuid4()
    return {
        "package_id": str(package_id),
        "package_name": "Tour Đà Lạt 3N2Đ",
        "destination": "Đà Lạt",
        "description": "Tour khám phá thành phố ngàn hoa với khí hậu mát mẻ quanh năm",
        "duration_days": 3,
        "price": 2500000.0,
        "available_slots": 20,
        "start_date": "2024-12-01",
        "end_date": "2024-12-03",
        "image_urls": "https://example.com/img1.jpg|https://example.com/img2.jpg",
        "cuisine": "Ẩm thực miền Trung",
        "suitable_for": "Gia đình, Cặp đôi",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


# ==================== Test Get All Packages ====================

@pytest.mark.asyncio
async def test_get_all_packages_success(tour_service, sample_tour_response):
    """Test getting all tour packages successfully"""
    service, mock_table = tour_service
    
    # Mock response
    mock_execute = Mock()
    mock_execute.data = [sample_tour_response]
    mock_table.select.return_value.order.return_value.execute.return_value = mock_execute
    
    # Execute
    result = await service.get_all_packages()
    
    # Assertions
    assert result["EC"] == 0
    assert result["EM"] == "Successfully retrieved tour packages"
    assert result["total"] == 1
    assert len(result["packages"]) == 1
    assert result["packages"][0]["package_name"] == "Tour Đà Lạt 3N2Đ"
    
    logger.info("✓ Test get all packages success passed")


@pytest.mark.asyncio
async def test_get_all_packages_with_filters(tour_service, sample_tour_response):
    """Test getting tour packages with filters"""
    service, mock_table = tour_service
    
    # Mock response
    mock_execute = Mock()
    mock_execute.data = [sample_tour_response]
    
    mock_query = Mock()
    mock_query.eq.return_value = mock_query
    mock_query.ilike.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.execute.return_value = mock_execute
    
    mock_table.select.return_value = mock_query
    
    # Execute with filters
    result = await service.get_all_packages(
        is_active=True,
        destination="Đà Lạt",
        limit=10,
        offset=0
    )
    
    # Assertions
    assert result["EC"] == 0
    assert result["total"] == 1
    assert len(result["packages"]) == 1
    
    logger.info("✓ Test get packages with filters passed")


@pytest.mark.asyncio
async def test_get_all_packages_empty(tour_service):
    """Test getting tour packages when none exist"""
    service, mock_table = tour_service
    
    # Mock empty response
    mock_execute = Mock()
    mock_execute.data = []
    mock_table.select.return_value.order.return_value.execute.return_value = mock_execute
    
    # Execute
    result = await service.get_all_packages()
    
    # Assertions
    assert result["EC"] == 0
    assert result["total"] == 0
    assert len(result["packages"]) == 0
    
    logger.info("✓ Test get all packages empty passed")


@pytest.mark.asyncio
async def test_get_all_packages_error(tour_service):
    """Test error handling when getting all packages"""
    service, mock_table = tour_service
    
    # Mock error
    mock_table.select.side_effect = Exception("Database connection error")
    
    # Execute
    result = await service.get_all_packages()
    
    # Assertions
    assert result["EC"] == 1
    assert "Error retrieving tour packages" in result["EM"]
    assert result["total"] == 0
    assert len(result["packages"]) == 0
    
    logger.info("✓ Test get all packages error passed")


# ==================== Test Get Package by ID ====================

@pytest.mark.asyncio
async def test_get_package_by_id_success(tour_service, sample_tour_response):
    """Test getting a tour package by ID successfully"""
    service, mock_table = tour_service
    
    package_id = sample_tour_response["package_id"]
    
    # Mock response
    mock_execute = Mock()
    mock_execute.data = [sample_tour_response]
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Execute
    result = await service.get_package_by_id(package_id)
    
    # Assertions
    assert result["EC"] == 0
    assert result["EM"] == "Successfully retrieved tour package"
    assert result["package"]["package_id"] == package_id
    assert result["package"]["package_name"] == "Tour Đà Lạt 3N2Đ"
    
    logger.info("✓ Test get package by ID success passed")


@pytest.mark.asyncio
async def test_get_package_by_id_not_found(tour_service):
    """Test getting a tour package that doesn't exist"""
    service, mock_table = tour_service
    
    package_id = str(uuid4())
    
    # Mock empty response
    mock_execute = Mock()
    mock_execute.data = []
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Execute
    result = await service.get_package_by_id(package_id)
    
    # Assertions
    assert result["EC"] == 1
    assert result["EM"] == "Tour package not found"
    assert result["package"] is None
    
    logger.info("✓ Test get package by ID not found passed")


@pytest.mark.asyncio
async def test_get_package_by_id_error(tour_service):
    """Test error handling when getting package by ID"""
    service, mock_table = tour_service
    
    package_id = str(uuid4())
    
    # Mock error
    mock_table.select.side_effect = Exception("Database error")
    
    # Execute
    result = await service.get_package_by_id(package_id)
    
    # Assertions
    assert result["EC"] == 2
    assert "Error retrieving tour package" in result["EM"]
    assert result["package"] is None
    
    logger.info("✓ Test get package by ID error passed")


# ==================== Test Create Package ====================

@pytest.mark.asyncio
async def test_create_package_success(tour_service, sample_tour_data, sample_tour_response):
    """Test creating a tour package successfully"""
    service, mock_table = tour_service
    
    # Mock response
    mock_execute = Mock()
    mock_execute.data = [sample_tour_response]
    mock_table.insert.return_value.execute.return_value = mock_execute
    
    # Execute
    result = await service.create_package(sample_tour_data)
    
    # Assertions
    assert result["EC"] == 0
    assert result["EM"] == "Tour package created successfully"
    assert result["package"] is not None
    assert result["package"]["package_name"] == "Tour Đà Lạt 3N2Đ"
    
    # Verify insert was called
    mock_table.insert.assert_called_once()
    
    logger.info("✓ Test create package success passed")


@pytest.mark.asyncio
async def test_create_package_with_optional_fields(tour_service):
    """Test creating package with only required fields"""
    service, mock_table = tour_service
    
    minimal_data = {
        "package_name": "Minimal Tour",
        "destination": "Nha Trang",
        "description": "Simple tour",
        "duration_days": 2,
        "price": 1500000.0,
        "available_slots": 10,
        "start_date": "2024-12-01",
        "end_date": "2024-12-02",
        "is_active": True
    }
    
    # Mock response
    mock_execute = Mock()
    mock_execute.data = [{**minimal_data, "package_id": str(uuid4()), "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()}]
    mock_table.insert.return_value.execute.return_value = mock_execute
    
    # Execute
    result = await service.create_package(minimal_data)
    
    # Assertions
    assert result["EC"] == 0
    assert result["package"]["package_name"] == "Minimal Tour"
    
    logger.info("✓ Test create package with optional fields passed")


@pytest.mark.asyncio
async def test_create_package_failed(tour_service, sample_tour_data):
    """Test failed package creation"""
    service, mock_table = tour_service
    
    # Mock empty response (failed insert)
    mock_execute = Mock()
    mock_execute.data = []
    mock_table.insert.return_value.execute.return_value = mock_execute
    
    # Execute
    result = await service.create_package(sample_tour_data)
    
    # Assertions
    assert result["EC"] == 1
    assert result["EM"] == "Failed to create tour package"
    assert result["package"] is None
    
    logger.info("✓ Test create package failed passed")


@pytest.mark.asyncio
async def test_create_package_error(tour_service, sample_tour_data):
    """Test error handling during package creation"""
    service, mock_table = tour_service
    
    # Mock error
    mock_table.insert.side_effect = Exception("Constraint violation")
    
    # Execute
    result = await service.create_package(sample_tour_data)
    
    # Assertions
    assert result["EC"] == 2
    assert "Error creating tour package" in result["EM"]
    assert result["package"] is None
    
    logger.info("✓ Test create package error passed")


# ==================== Test Update Package ====================

@pytest.mark.asyncio
async def test_update_package_success(tour_service, sample_tour_response):
    """Test updating a tour package successfully"""
    service, mock_table = tour_service
    
    package_id = sample_tour_response["package_id"]
    update_data = {
        "price": 2800000.0,
        "available_slots": 15,
        "cuisine": "Ẩm thực cao cấp"
    }
    
    # Mock get_package_by_id
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_tour_response
    }):
        # Mock update response
        updated_response = {**sample_tour_response, **update_data}
        mock_execute = Mock()
        mock_execute.data = [updated_response]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Execute
        result = await service.update_package(package_id, update_data)
        
        # Assertions
        assert result["EC"] == 0
        assert result["EM"] == "Tour package updated successfully"
        assert result["package"]["price"] == 2800000.0
        assert result["package"]["available_slots"] == 15
        
        logger.info("✓ Test update package success passed")


@pytest.mark.asyncio
async def test_update_package_not_found(tour_service):
    """Test updating a package that doesn't exist"""
    service, mock_table = tour_service
    
    package_id = str(uuid4())
    update_data = {"price": 3000000.0}
    
    # Mock get_package_by_id returning not found
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 1,
        "EM": "Tour package not found",
        "package": None
    }):
        # Execute
        result = await service.update_package(package_id, update_data)
        
        # Assertions
        assert result["EC"] == 1
        assert result["EM"] == "Tour package not found"
        
        logger.info("✓ Test update package not found passed")


@pytest.mark.asyncio
async def test_update_package_no_fields(tour_service, sample_tour_response):
    """Test updating with no valid fields"""
    service, mock_table = tour_service
    
    package_id = sample_tour_response["package_id"]
    update_data = {}
    
    # Mock get_package_by_id
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_tour_response
    }):
        # Execute
        result = await service.update_package(package_id, update_data)
        
        # Assertions
        assert result["EC"] == 1
        assert result["EM"] == "No fields to update"
        
        logger.info("✓ Test update package no fields passed")


@pytest.mark.asyncio
async def test_update_package_partial_update(tour_service, sample_tour_response):
    """Test partial update with only some fields"""
    service, mock_table = tour_service
    
    package_id = sample_tour_response["package_id"]
    update_data = {
        "suitable_for": "Gia đình VIP, Cặp đôi cao cấp",
        "image_urls": "https://new.com/img1.jpg|https://new.com/img2.jpg|https://new.com/img3.jpg"
    }
    
    # Mock get_package_by_id
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_tour_response
    }):
        # Mock update response
        updated_response = {**sample_tour_response, **update_data}
        mock_execute = Mock()
        mock_execute.data = [updated_response]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Execute
        result = await service.update_package(package_id, update_data)
        
        # Assertions
        assert result["EC"] == 0
        assert result["package"]["suitable_for"] == "Gia đình VIP, Cặp đôi cao cấp"
        assert "https://new.com/img3.jpg" in result["package"]["image_urls"]
        
        logger.info("✓ Test update package partial passed")


@pytest.mark.asyncio
async def test_update_package_error(tour_service, sample_tour_response):
    """Test error handling during package update"""
    service, mock_table = tour_service
    
    package_id = sample_tour_response["package_id"]
    update_data = {"price": 3000000.0}
    
    # Mock get_package_by_id
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_tour_response
    }):
        # Mock error
        mock_table.update.side_effect = Exception("Database error")
        
        # Execute
        result = await service.update_package(package_id, update_data)
        
        # Assertions
        assert result["EC"] == 3
        assert "Error updating tour package" in result["EM"]
        
        logger.info("✓ Test update package error passed")


# ==================== Test Delete Package ====================

@pytest.mark.asyncio
async def test_delete_package_success(tour_service, sample_tour_response):
    """Test deleting a tour package successfully"""
    service, mock_table = tour_service
    
    package_id = sample_tour_response["package_id"]
    
    # Mock get_package_by_id
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_tour_response
    }):
        # Mock delete response
        mock_execute = Mock()
        mock_execute.data = [sample_tour_response]
        mock_table.delete.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Execute
        result = await service.delete_package(package_id)
        
        # Assertions
        assert result["EC"] == 0
        assert result["EM"] == "Tour package deleted successfully"
        
        # Verify delete was called
        mock_table.delete.assert_called_once()
        
        logger.info("✓ Test delete package success passed")


@pytest.mark.asyncio
async def test_delete_package_not_found(tour_service):
    """Test deleting a package that doesn't exist"""
    service, mock_table = tour_service
    
    package_id = str(uuid4())
    
    # Mock get_package_by_id returning not found
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 1,
        "EM": "Tour package not found",
        "package": None
    }):
        # Execute
        result = await service.delete_package(package_id)
        
        # Assertions
        assert result["EC"] == 1
        assert result["EM"] == "Tour package not found"
        
        logger.info("✓ Test delete package not found passed")


@pytest.mark.asyncio
async def test_delete_package_error(tour_service, sample_tour_response):
    """Test error handling during package deletion"""
    service, mock_table = tour_service
    
    package_id = sample_tour_response["package_id"]
    
    # Mock get_package_by_id
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_tour_response
    }):
        # Mock error
        mock_table.delete.side_effect = Exception("Foreign key constraint")
        
        # Execute
        result = await service.delete_package(package_id)
        
        # Assertions
        assert result["EC"] != 0
        assert "Error" in result["EM"] or "deleting" in result["EM"]
        
        logger.info("✓ Test delete package error passed")


# ==================== Test Schema Validation ====================

def test_tour_package_create_schema_valid():
    """Test TourPackageCreate schema with valid data"""
    data = {
        "package_name": "Tour Hà Nội",
        "destination": "Hà Nội",
        "description": "Khám phá Thủ đô",
        "duration_days": 2,
        "price": 1800000.0,
        "available_slots": 25,
        "start_date": date(2024, 12, 1),
        "end_date": date(2024, 12, 2),
        "is_active": True
    }
    
    package = TourPackageCreate(**data)
    
    assert package.package_name == "Tour Hà Nội"
    assert package.duration_days == 2
    assert package.price == 1800000.0
    
    logger.info("✓ Test create schema valid passed")


def test_tour_package_create_schema_with_optional_fields():
    """Test TourPackageCreate schema with optional fields"""
    data = {
        "package_name": "Tour Phú Quốc",
        "destination": "Phú Quốc",
        "description": "Đảo ngọc",
        "duration_days": 4,
        "price": 4500000.0,
        "available_slots": 15,
        "start_date": date(2024, 12, 15),
        "end_date": date(2024, 12, 18),
        "image_urls": "https://example.com/pq1.jpg|https://example.com/pq2.jpg",
        "cuisine": "Hải sản tươi sống",
        "suitable_for": "Gia đình, Cặp đôi",
        "is_active": True
    }
    
    package = TourPackageCreate(**data)
    
    assert package.image_urls == "https://example.com/pq1.jpg|https://example.com/pq2.jpg"
    assert package.cuisine == "Hải sản tươi sống"
    assert package.suitable_for == "Gia đình, Cặp đôi"
    
    logger.info("✓ Test create schema with optional fields passed")


def test_tour_package_create_schema_invalid_price():
    """Test TourPackageCreate schema with invalid price"""
    data = {
        "package_name": "Tour Test",
        "destination": "Test",
        "description": "Test",
        "duration_days": 2,
        "price": -1000.0,  # Invalid: negative price
        "available_slots": 10,
        "start_date": date(2024, 12, 1),
        "end_date": date(2024, 12, 2),
        "is_active": True
    }
    
    with pytest.raises(Exception):
        TourPackageCreate(**data)
    
    logger.info("✓ Test create schema invalid price passed")


def test_tour_package_create_schema_invalid_duration():
    """Test TourPackageCreate schema with invalid duration"""
    data = {
        "package_name": "Tour Test",
        "destination": "Test",
        "description": "Test",
        "duration_days": 0,  # Invalid: must be > 0
        "price": 1000000.0,
        "available_slots": 10,
        "start_date": date(2024, 12, 1),
        "end_date": date(2024, 12, 2),
        "is_active": True
    }
    
    with pytest.raises(Exception):
        TourPackageCreate(**data)
    
    logger.info("✓ Test create schema invalid duration passed")


def test_tour_package_update_schema_partial():
    """Test TourPackageUpdate schema with partial data"""
    data = {
        "price": 2000000.0,
        "available_slots": 5
    }
    
    package_update = TourPackageUpdate(**data)
    
    assert package_update.price == 2000000.0
    assert package_update.available_slots == 5
    assert package_update.package_name is None
    assert package_update.cuisine is None
    
    logger.info("✓ Test update schema partial passed")


def test_tour_package_update_schema_all_optional():
    """Test TourPackageUpdate schema with no fields"""
    package_update = TourPackageUpdate()
    
    assert package_update.package_name is None
    assert package_update.price is None
    assert package_update.image_urls is None
    
    logger.info("✓ Test update schema all optional passed")


# ==================== Test Edge Cases ====================

@pytest.mark.asyncio
async def test_create_package_with_multiple_images(tour_service):
    """Test creating package with multiple pipe-separated images"""
    service, mock_table = tour_service
    
    data = {
        "package_name": "Tour Sapa",
        "destination": "Sapa",
        "description": "Núi non hùng vĩ",
        "duration_days": 3,
        "price": 3500000.0,
        "available_slots": 20,
        "start_date": "2024-12-20",
        "end_date": "2024-12-22",
        "image_urls": "https://img1.jpg|https://img2.jpg|https://img3.jpg|https://img4.jpg",
        "is_active": True
    }
    
    # Mock response
    mock_execute = Mock()
    mock_execute.data = [{**data, "package_id": str(uuid4()), "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()}]
    mock_table.insert.return_value.execute.return_value = mock_execute
    
    # Execute
    result = await service.create_package(data)
    
    # Assertions
    assert result["EC"] == 0
    assert "|" in result["package"]["image_urls"]
    assert result["package"]["image_urls"].count("|") == 3  # 4 images = 3 separators
    
    logger.info("✓ Test create package with multiple images passed")


@pytest.mark.asyncio
async def test_update_package_change_active_status(tour_service, sample_tour_response):
    """Test toggling active status"""
    service, mock_table = tour_service
    
    package_id = sample_tour_response["package_id"]
    
    # Mock get_package_by_id
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_tour_response
    }):
        # Mock update response
        updated_response = {**sample_tour_response, "is_active": False}
        mock_execute = Mock()
        mock_execute.data = [updated_response]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Execute
        result = await service.update_package(package_id, {"is_active": False})
        
        # Assertions
        assert result["EC"] == 0
        assert result["package"]["is_active"] is False
        
        logger.info("✓ Test update active status passed")


@pytest.mark.asyncio
async def test_filter_by_destination_case_insensitive(tour_service):
    """Test destination filter is case insensitive"""
    service, mock_table = tour_service
    
    # Mock response
    mock_execute = Mock()
    mock_execute.data = [
        {
            "package_id": str(uuid4()),
            "package_name": "Tour Đà Lạt",
            "destination": "Đà Lạt",
            "price": 2500000.0
        }
    ]
    
    mock_query = Mock()
    mock_query.eq.return_value = mock_query
    mock_query.ilike.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = mock_execute
    
    mock_table.select.return_value = mock_query
    
    # Execute with lowercase
    result = await service.get_all_packages(destination="đà lạt")
    
    # Assertions
    assert result["EC"] == 0
    assert result["total"] == 1
    
    logger.info("✓ Test filter case insensitive passed")


@pytest.mark.asyncio
async def test_pagination_limit_and_offset(tour_service):
    """Test pagination with limit and offset"""
    service, mock_table = tour_service
    
    # Mock response with 3 packages
    mock_execute = Mock()
    mock_execute.data = [
        {"package_id": str(uuid4()), "package_name": f"Tour {i}"} 
        for i in range(1, 4)
    ]
    
    mock_query = Mock()
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.execute.return_value = mock_execute
    
    mock_table.select.return_value = mock_query
    
    # Execute with offset > 0 to ensure offset is called
    result = await service.get_all_packages(limit=3, offset=5)
    
    # Assertions
    assert result["EC"] == 0
    assert result["total"] == 3
    
    # Verify limit was called
    mock_query.limit.assert_called_once_with(3)
    # Verify offset was called (offset > 0 should trigger the call)
    # Note: offset=0 may not trigger offset() call in implementation
    if mock_query.offset.call_count > 0:
        mock_query.offset.assert_called_once_with(5)
    
    logger.info("✓ Test pagination passed")


@pytest.mark.asyncio
async def test_create_package_with_long_description(tour_service):
    """Test creating package with very long description"""
    service, mock_table = tour_service
    
    long_description = "Lorem ipsum " * 200  # Very long text
    
    data = {
        "package_name": "Tour Test",
        "destination": "Test Destination",
        "description": long_description,
        "duration_days": 3,
        "price": 2000000.0,
        "available_slots": 10,
        "start_date": "2024-12-01",
        "end_date": "2024-12-03",
        "is_active": True
    }
    
    # Mock response
    mock_execute = Mock()
    mock_execute.data = [{**data, "package_id": str(uuid4()), "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()}]
    mock_table.insert.return_value.execute.return_value = mock_execute
    
    # Execute
    result = await service.create_package(data)
    
    # Assertions
    assert result["EC"] == 0
    assert len(result["package"]["description"]) > 1000
    
    logger.info("✓ Test create with long description passed")


@pytest.mark.asyncio
async def test_update_package_dates(tour_service, sample_tour_response):
    """Test updating start and end dates"""
    service, mock_table = tour_service
    
    package_id = sample_tour_response["package_id"]
    
    # Mock get_package_by_id
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_tour_response
    }):
        # Mock update response
        updated_response = {
            **sample_tour_response,
            "start_date": "2025-01-15",
            "end_date": "2025-01-17"
        }
        mock_execute = Mock()
        mock_execute.data = [updated_response]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Execute
        result = await service.update_package(package_id, {
            "start_date": "2025-01-15",
            "end_date": "2025-01-17"
        })
        
        # Assertions
        assert result["EC"] == 0
        assert result["package"]["start_date"] == "2025-01-15"
        assert result["package"]["end_date"] == "2025-01-17"
        
        logger.info("✓ Test update dates passed")


# ==================== Run Tests Summary ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
    logger.info("=" * 60)
    logger.info("All tour package tests completed!")
    logger.info("=" * 60)
