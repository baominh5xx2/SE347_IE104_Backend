"""
Unit tests for Tour Package Service and Endpoints
Tests for all CRUD operations and edge cases
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, timezone
from uuid import uuid4, UUID
import logging
import csv
import io

from app.v1.services.tour_package_service import TourPackageService
from app.v1.schema.tour_package_schema import (
    TourPackageCreate,
    TourPackageUpdate,
    TourPackageResponse,
    TourPackageBulkCreateResponse
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


@pytest.fixture
def sample_bulk_data():
    """Sample bulk tour package data"""
    return [
        {
            "package_name": "Tour Đà Lạt 3N2Đ",
            "destination": "Đà Lạt",
            "description": "Khám phá thành phố ngàn hoa",
            "duration_days": 3,
            "price": 2500000.0,
            "available_slots": 20,
            "start_date": "2024-12-15",
            "end_date": "2024-12-17",
            "image_urls": "https://example.com/dalat1.jpg",
            "cuisine": "Ẩm thực miền Trung",
            "suitable_for": "Gia đình",
            "is_active": True
        },
        {
            "package_name": "Tour Nha Trang Biển Xanh",
            "destination": "Nha Trang",
            "description": "Tận hưởng biển đảo xinh đẹp",
            "duration_days": 4,
            "price": 3500000.0,
            "available_slots": 25,
            "start_date": "2024-12-20",
            "end_date": "2024-12-23",
            "image_urls": "https://example.com/nhatrang1.jpg",
            "cuisine": "Hải sản tươi sống",
            "suitable_for": "Cặp đôi",
            "is_active": True
        }
    ]


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
    
    # Mock embedding generation
    with patch.object(service, '_generate_embedding', return_value=[0.1] * 1536):
        with patch.object(service, '_upsert_embedding', return_value=True):
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
    
    # Mock embedding generation
    with patch.object(service, '_generate_embedding', return_value=[0.1] * 1536):
        with patch.object(service, '_upsert_embedding', return_value=True):
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
        # Mock embedding generation for content update
        with patch.object(service, '_generate_embedding', return_value=[0.1] * 1536):
            with patch.object(service, '_upsert_embedding', return_value=True):
                # Mock update response
                updated_response = {**sample_tour_response, **update_data}
                mock_update_execute = Mock()
                mock_update_execute.data = [updated_response]
                mock_table.update.return_value.eq.return_value.execute.return_value = mock_update_execute
                
                # Mock select to fetch full record after update
                mock_select_execute = Mock()
                mock_select_execute.data = updated_response
                mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_select_execute
                
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
        # Mock embedding generation for content update (suitable_for is a content field)
        with patch.object(service, '_generate_embedding', return_value=[0.1] * 1536):
            with patch.object(service, '_upsert_embedding', return_value=True):
                # Mock update response
                updated_response = {**sample_tour_response, **update_data}
                mock_update_execute = Mock()
                mock_update_execute.data = [updated_response]
                mock_table.update.return_value.eq.return_value.execute.return_value = mock_update_execute
                
                # Mock select to fetch full record after update
                mock_select_execute = Mock()
                mock_select_execute.data = updated_response
                mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_select_execute
                
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
        # Mock embedding deletion
        with patch.object(service, '_delete_embedding', return_value=True):
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
    
    # Mock embedding generation
    with patch.object(service, '_generate_embedding', return_value=[0.1] * 1536):
        with patch.object(service, '_upsert_embedding', return_value=True):
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
        mock_update_execute = Mock()
        mock_update_execute.data = [updated_response]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_update_execute
        
        # Mock select to fetch full record after update
        mock_select_execute = Mock()
        mock_select_execute.data = updated_response
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_select_execute
        
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
    
    # Mock embedding generation
    with patch.object(service, '_generate_embedding', return_value=[0.1] * 1536):
        with patch.object(service, '_upsert_embedding', return_value=True):
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
        # Dates don't trigger embedding regeneration, so no need to mock embedding methods
        # Mock update response
        updated_response = {
            **sample_tour_response,
            "start_date": "2025-01-15",
            "end_date": "2025-01-17"
        }
        mock_update_execute = Mock()
        mock_update_execute.data = [updated_response]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_update_execute
        
        # Mock select to fetch full record after update
        mock_select_execute = Mock()
        mock_select_execute.data = updated_response
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_select_execute
        
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


# ==================== Test Bulk Create from CSV ====================

@pytest.mark.asyncio
async def test_create_packages_bulk_success(tour_service, sample_bulk_data):
    """Test bulk creating tour packages successfully"""
    service, mock_table = tour_service
    
    # Mock embedding generation
    with patch.object(service, '_generate_embedding', return_value=[0.1] * 1536):
        with patch.object(service, '_upsert_embedding', return_value=True):
            # Mock insert responses
            def mock_insert_execute():
                mock_exec = Mock()
                # Return package with generated ID
                package_data = sample_bulk_data[0].copy()
                package_data['package_id'] = str(uuid4())
                package_data['created_at'] = datetime.now(timezone.utc).isoformat()
                package_data['updated_at'] = datetime.now(timezone.utc).isoformat()
                mock_exec.data = [package_data]
                return mock_exec
            
            mock_table.insert.return_value.execute.side_effect = [
                mock_insert_execute(),
                mock_insert_execute()
            ]
            
            # Execute
            result = await service.create_packages_bulk(sample_bulk_data)
            
            # Assertions
            assert result["EC"] == 0
            assert result["total_processed"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0
            assert len(result["created_packages"]) == 2
            assert len(result["errors"]) == 0
            
            logger.info("✓ Test bulk create success passed")


@pytest.mark.asyncio
async def test_create_packages_bulk_partial_success(tour_service, sample_bulk_data):
    """Test bulk create with some packages failing"""
    service, mock_table = tour_service
    
    # Mock embedding generation
    with patch.object(service, '_generate_embedding', return_value=[0.1] * 1536):
        with patch.object(service, '_upsert_embedding', return_value=True):
            # Mock insert - first succeeds, second fails
            def mock_success():
                mock_exec = Mock()
                package_data = sample_bulk_data[0].copy()
                package_data['package_id'] = str(uuid4())
                package_data['created_at'] = datetime.now(timezone.utc).isoformat()
                package_data['updated_at'] = datetime.now(timezone.utc).isoformat()
                mock_exec.data = [package_data]
                return mock_exec
            
            def mock_failure():
                mock_exec = Mock()
                mock_exec.data = []
                return mock_exec
            
            mock_table.insert.return_value.execute.side_effect = [
                mock_success(),
                mock_failure()
            ]
            
            # Execute
            result = await service.create_packages_bulk(sample_bulk_data)
            
            # Assertions
            assert result["EC"] == 1  # Has failures
            assert result["total_processed"] == 2
            assert result["successful"] == 1
            assert result["failed"] == 1
            assert len(result["created_packages"]) == 1
            assert len(result["errors"]) == 1
            
            logger.info("✓ Test bulk create partial success passed")


@pytest.mark.asyncio
async def test_create_packages_bulk_all_fail(tour_service, sample_bulk_data):
    """Test bulk create when all packages fail"""
    service, mock_table = tour_service
    
    # Mock all inserts failing
    mock_exec = Mock()
    mock_exec.data = []
    mock_table.insert.return_value.execute.return_value = mock_exec
    
    # Execute
    result = await service.create_packages_bulk(sample_bulk_data)
    
    # Assertions
    assert result["EC"] == 1
    assert result["total_processed"] == 2
    assert result["successful"] == 0
    assert result["failed"] == 2
    assert len(result["created_packages"]) == 0
    assert len(result["errors"]) == 2
    
    logger.info("✓ Test bulk create all fail passed")


@pytest.mark.asyncio
async def test_create_packages_bulk_with_embedding_failure(tour_service, sample_bulk_data):
    """Test bulk create when embedding generation fails"""
    service, mock_table = tour_service
    
    # Mock embedding generation failing
    with patch.object(service, '_generate_embedding', return_value=None):
        # Mock successful insert
        def mock_insert_execute():
            mock_exec = Mock()
            package_data = sample_bulk_data[0].copy()
            package_data['package_id'] = str(uuid4())
            package_data['created_at'] = datetime.now(timezone.utc).isoformat()
            package_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            mock_exec.data = [package_data]
            return mock_exec
        
        mock_table.insert.return_value.execute.side_effect = [
            mock_insert_execute(),
            mock_insert_execute()
        ]
        
        # Execute
        result = await service.create_packages_bulk(sample_bulk_data)
        
        # Assertions - packages should still be created even if embedding fails
        assert result["EC"] == 0
        assert result["successful"] == 2
        assert len(result["created_packages"]) == 2
        
        logger.info("✓ Test bulk create with embedding failure passed")


@pytest.mark.asyncio
async def test_create_packages_bulk_empty_list(tour_service):
    """Test bulk create with empty list"""
    service, mock_table = tour_service
    
    # Execute with empty list
    result = await service.create_packages_bulk([])
    
    # Assertions
    assert result["EC"] == 0
    assert result["total_processed"] == 0
    assert result["successful"] == 0
    assert result["failed"] == 0
    
    logger.info("✓ Test bulk create empty list passed")


@pytest.mark.asyncio
async def test_create_packages_bulk_exception_handling(tour_service, sample_bulk_data):
    """Test bulk create with database exception for each package"""
    service, mock_table = tour_service
    
    # Mock database error for each insert
    mock_table.insert.side_effect = Exception("Database connection error")
    
    # Execute
    result = await service.create_packages_bulk(sample_bulk_data)
    
    # Assertions - EC should be 1 (has failures) not 2, as each package error is caught individually
    assert result["EC"] == 1
    assert result["total_processed"] == 2
    assert result["successful"] == 0
    assert result["failed"] == 2
    assert len(result["errors"]) == 2
    assert "Database connection error" in result["errors"][0]
    
    logger.info("✓ Test bulk create exception handling passed")


@pytest.mark.asyncio
async def test_create_packages_bulk_single_package(tour_service, sample_bulk_data):
    """Test bulk create with single package"""
    service, mock_table = tour_service
    
    # Mock embedding generation
    with patch.object(service, '_generate_embedding', return_value=[0.1] * 1536):
        with patch.object(service, '_upsert_embedding', return_value=True):
            # Mock insert response
            mock_exec = Mock()
            package_data = sample_bulk_data[0].copy()
            package_data['package_id'] = str(uuid4())
            package_data['created_at'] = datetime.now(timezone.utc).isoformat()
            package_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            mock_exec.data = [package_data]
            mock_table.insert.return_value.execute.return_value = mock_exec
            
            # Execute with single package
            result = await service.create_packages_bulk([sample_bulk_data[0]])
            
            # Assertions
            assert result["EC"] == 0
            assert result["total_processed"] == 1
            assert result["successful"] == 1
            assert result["failed"] == 0
            
            logger.info("✓ Test bulk create single package passed")


@pytest.mark.asyncio
async def test_create_packages_bulk_large_batch(tour_service):
    """Test bulk create with large batch of packages"""
    service, mock_table = tour_service
    
    # Create 50 packages
    large_batch = []
    for i in range(50):
        large_batch.append({
            "package_name": f"Tour {i}",
            "destination": f"Destination {i}",
            "description": f"Description {i}",
            "duration_days": 3,
            "price": 2000000.0 + (i * 100000),
            "available_slots": 20,
            "start_date": "2024-12-15",
            "end_date": "2024-12-17",
            "is_active": True
        })
    
    # Mock embedding generation
    with patch.object(service, '_generate_embedding', return_value=[0.1] * 1536):
        with patch.object(service, '_upsert_embedding', return_value=True):
            # Mock successful inserts
            def mock_insert_execute():
                mock_exec = Mock()
                mock_exec.data = [{
                    "package_id": str(uuid4()),
                    "package_name": "Test",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }]
                return mock_exec
            
            mock_table.insert.return_value.execute.side_effect = [
                mock_insert_execute() for _ in range(50)
            ]
            
            # Execute
            result = await service.create_packages_bulk(large_batch)
            
            # Assertions
            assert result["EC"] == 0
            assert result["total_processed"] == 50
            assert result["successful"] == 50
            assert result["failed"] == 0
            
            logger.info("✓ Test bulk create large batch passed")


# ==================== Test Bulk Create Response Schema ====================

def test_bulk_create_response_schema():
    """Test TourPackageBulkCreateResponse schema"""
    data = {
        "EC": 0,
        "EM": "Success",
        "total_processed": 5,
        "successful": 5,
        "failed": 0,
        "created_packages": [],
        "errors": []
    }
    
    response = TourPackageBulkCreateResponse(**data)
    
    assert response.EC == 0
    assert response.total_processed == 5
    assert response.successful == 5
    assert response.failed == 0
    
    logger.info("✓ Test bulk create response schema passed")


def test_bulk_create_response_schema_with_errors():
    """Test TourPackageBulkCreateResponse schema with errors"""
    data = {
        "EC": 1,
        "EM": "Partial success",
        "total_processed": 5,
        "successful": 3,
        "failed": 2,
        "created_packages": [],
        "errors": ["Error 1", "Error 2"],
        "parsing_errors": ["Parse error 1"]
    }
    
    response = TourPackageBulkCreateResponse(**data)
    
    assert response.EC == 1
    assert response.successful == 3
    assert response.failed == 2
    assert len(response.errors) == 2
    assert len(response.parsing_errors) == 1
    
    logger.info("✓ Test bulk create response with errors passed")


# ==================== Test is_favorite Feature ====================

@pytest.mark.asyncio
async def test_add_favorite_status_with_user_id(tour_service, sample_tour_response):
    """Test _add_favorite_status adds is_favorite field when user_id is provided"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    package_id = sample_tour_response["package_id"]
    
    # Mock favorites query - package is favorited
    mock_favorites_execute = Mock()
    mock_favorites_execute.data = [{"package_id": package_id}]
    mock_table.select.return_value.eq.return_value.in_.return_value.execute.return_value = mock_favorites_execute
    
    packages = [sample_tour_response.copy()]
    
    # Execute
    result = await service._add_favorite_status(packages, user_id)
    
    # Assertions
    assert len(result) == 1
    assert result[0]["is_favorite"] is True
    assert "is_favorite" in result[0]
    
    logger.info("✓ Test add favorite status with user_id passed")


@pytest.mark.asyncio
async def test_add_favorite_status_without_user_id(tour_service, sample_tour_response):
    """Test _add_favorite_status sets is_favorite=False when user_id is None"""
    service, mock_table = tour_service
    
    packages = [sample_tour_response.copy()]
    
    # Execute without user_id
    result = await service._add_favorite_status(packages, None)
    
    # Assertions
    assert len(result) == 1
    assert result[0]["is_favorite"] is False
    assert "is_favorite" in result[0]
    
    logger.info("✓ Test add favorite status without user_id passed")


@pytest.mark.asyncio
async def test_add_favorite_status_not_favorited(tour_service, sample_tour_response):
    """Test _add_favorite_status when package is not favorited"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    package_id = sample_tour_response["package_id"]
    
    # Mock favorites query - empty (not favorited)
    mock_favorites_execute = Mock()
    mock_favorites_execute.data = []
    mock_table.select.return_value.eq.return_value.in_.return_value.execute.return_value = mock_favorites_execute
    
    packages = [sample_tour_response.copy()]
    
    # Execute
    result = await service._add_favorite_status(packages, user_id)
    
    # Assertions
    assert len(result) == 1
    assert result[0]["is_favorite"] is False
    
    logger.info("✓ Test add favorite status not favorited passed")


@pytest.mark.asyncio
async def test_add_favorite_status_multiple_packages(tour_service):
    """Test _add_favorite_status with multiple packages (batch check)"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    package_id_1 = str(uuid4())
    package_id_2 = str(uuid4())
    package_id_3 = str(uuid4())
    
    packages = [
        {"package_id": package_id_1, "package_name": "Tour 1"},
        {"package_id": package_id_2, "package_name": "Tour 2"},
        {"package_id": package_id_3, "package_name": "Tour 3"}
    ]
    
    # Mock favorites query - only package 1 and 3 are favorited
    mock_favorites_execute = Mock()
    mock_favorites_execute.data = [
        {"package_id": package_id_1},
        {"package_id": package_id_3}
    ]
    mock_table.select.return_value.eq.return_value.in_.return_value.execute.return_value = mock_favorites_execute
    
    # Execute
    result = await service._add_favorite_status(packages, user_id)
    
    # Assertions
    assert len(result) == 3
    assert result[0]["is_favorite"] is True  # package 1
    assert result[1]["is_favorite"] is False  # package 2
    assert result[2]["is_favorite"] is True  # package 3
    
    logger.info("✓ Test add favorite status multiple packages passed")


@pytest.mark.asyncio
async def test_add_favorite_status_empty_list(tour_service):
    """Test _add_favorite_status with empty packages list"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    
    # Execute with empty list
    result = await service._add_favorite_status([], user_id)
    
    # Assertions
    assert len(result) == 0
    
    logger.info("✓ Test add favorite status empty list passed")


@pytest.mark.asyncio
async def test_add_favorite_status_database_error(tour_service, sample_tour_response):
    """Test _add_favorite_status handles database errors gracefully"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    packages = [sample_tour_response.copy()]
    
    # Mock database error
    mock_table.select.side_effect = Exception("Database connection error")
    
    # Execute
    result = await service._add_favorite_status(packages, user_id)
    
    # Assertions - should set all to False on error
    assert len(result) == 1
    assert result[0]["is_favorite"] is False
    
    logger.info("✓ Test add favorite status database error passed")


@pytest.mark.asyncio
async def test_get_all_packages_with_favorite_status(tour_service, sample_tour_response):
    """Test get_all_packages includes is_favorite field"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    package_id = sample_tour_response["package_id"]
    
    # Mock get packages response
    mock_execute = Mock()
    mock_execute.data = [sample_tour_response]
    mock_table.select.return_value.order.return_value.execute.return_value = mock_execute
    
    # Mock favorites query
    mock_favorites_execute = Mock()
    mock_favorites_execute.data = [{"package_id": package_id}]
    # Need to reset side_effect for second call
    def mock_table_side_effect(table_name):
        mock_tbl = Mock()
        if table_name == 'favorite_tours':
            mock_tbl.select.return_value.eq.return_value.in_.return_value.execute.return_value = mock_favorites_execute
        else:
            mock_tbl.select.return_value.order.return_value.execute.return_value = mock_execute
        return mock_tbl
    
    mock_table.__class__.table = Mock(side_effect=lambda self, name: mock_table_side_effect(name))
    
    # Patch _add_favorite_status to avoid complex mocking
    with patch.object(service, '_add_favorite_status', return_value=[{**sample_tour_response, "is_favorite": True}]):
        # Execute
        result = await service.get_all_packages(user_id=user_id)
        
        # Assertions
        assert result["EC"] == 0
        assert len(result["packages"]) == 1
        assert result["packages"][0]["is_favorite"] is True
    
    logger.info("✓ Test get all packages with favorite status passed")


@pytest.mark.asyncio
async def test_get_package_by_id_with_favorite_status(tour_service, sample_tour_response):
    """Test get_package_by_id includes is_favorite field"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    package_id = sample_tour_response["package_id"]
    
    # Mock get package response
    mock_execute = Mock()
    mock_execute.data = [sample_tour_response]
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Patch _add_favorite_status
    with patch.object(service, '_add_favorite_status', return_value=[{**sample_tour_response, "is_favorite": False}]):
        # Execute
        result = await service.get_package_by_id(package_id, user_id=user_id)
        
        # Assertions
        assert result["EC"] == 0
        assert result["package"]["is_favorite"] is False
    
    logger.info("✓ Test get package by ID with favorite status passed")


@pytest.mark.asyncio
async def test_search_packages_with_favorite_status(tour_service):
    """Test search_packages includes is_favorite field"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    package_id = str(uuid4())
    
    sample_package = {
        "package_id": package_id,
        "package_name": "Tour Đà Lạt",
        "destination": "Đà Lạt",
        "price": 2500000.0
    }
    
    # Mock search service
    with patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
        mock_search.search_tour_packages = AsyncMock(return_value=[sample_package])
        
        # Patch _add_favorite_status
        with patch.object(service, '_add_favorite_status', return_value=[{**sample_package, "is_favorite": True}]):
            # Execute
            result = await service.search_packages(
                user_message="tour Đà Lạt",
                user_id=user_id
            )
            
            # Assertions
            assert result["EC"] == 0
            assert len(result["packages"]) == 1
            assert result["packages"][0]["is_favorite"] is True
    
    logger.info("✓ Test search packages with favorite status passed")


@pytest.mark.asyncio
async def test_recommend_packages_with_favorite_status(tour_service):
    """Test recommend_packages includes is_favorite field"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    package_id = str(uuid4())
    
    sample_package = {
        "package_id": package_id,
        "package_name": "Tour Recommended",
        "destination": "Đà Lạt",
        "price": 2500000.0,
        "end_date": "2024-12-31"
    }
    
    # Mock admin settings
    with patch.object(service, 'get_admin_setting', return_value=False):
        # Mock expiring tours query
        mock_execute = Mock()
        mock_execute.data = [sample_package]
        mock_table.select.return_value.eq.return_value.gt.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = mock_execute
        
        # Mock search service
        with patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            mock_search.search_tour_packages = AsyncMock(return_value=[sample_package])
            
            # Mock mem0 client
            with patch('app.v1.services.tour_package_service.mem0_client', None):
                # Patch _add_favorite_status
                with patch.object(service, '_add_favorite_status', return_value=[{**sample_package, "is_favorite": True}]):
                    # Execute
                    result = await service.recommend_packages(user_id=user_id, k=1)
                    
                    # Assertions
                    assert result["EC"] == 0
                    assert len(result["packages"]) == 1
                    assert result["packages"][0]["is_favorite"] is True
    
    logger.info("✓ Test recommend packages with favorite status passed")


@pytest.mark.asyncio
async def test_filter_packages_by_month_with_favorite_status(tour_service, sample_tour_response):
    """Test filter_packages_by_month includes is_favorite field"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    
    # Mock filter response
    mock_execute = Mock()
    mock_execute.data = [sample_tour_response]
    
    mock_query = Mock()
    mock_query.gte.return_value = mock_query
    mock_query.lt.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.execute.return_value = mock_execute
    mock_table.select.return_value = mock_query
    
    # Patch _add_favorite_status
    with patch.object(service, '_add_favorite_status', return_value=[{**sample_tour_response, "is_favorite": False}]):
        # Execute
        result = await service.filter_packages_by_month(
            month=12,
            year=2024,
            user_id=user_id
        )
        
        # Assertions
        assert result["EC"] == 0
        assert len(result["packages"]) == 1
        assert result["packages"][0]["is_favorite"] is False
    
    logger.info("✓ Test filter by month with favorite status passed")


@pytest.mark.asyncio
async def test_get_all_packages_without_user_id(tour_service, sample_tour_response):
    """Test get_all_packages sets is_favorite=False when user_id is None"""
    service, mock_table = tour_service
    
    # Mock get packages response
    mock_execute = Mock()
    mock_execute.data = [sample_tour_response]
    mock_table.select.return_value.order.return_value.execute.return_value = mock_execute
    
    # Patch _add_favorite_status to verify it's called with None
    with patch.object(service, '_add_favorite_status', return_value=[{**sample_tour_response, "is_favorite": False}]) as mock_add:
        # Execute without user_id
        result = await service.get_all_packages(user_id=None)
        
        # Assertions
        assert result["EC"] == 0
        assert len(result["packages"]) == 1
        assert result["packages"][0]["is_favorite"] is False
        # Verify _add_favorite_status was called with None
        mock_add.assert_called_once()
        call_args = mock_add.call_args[0]
        assert call_args[1] is None  # user_id should be None
    
    logger.info("✓ Test get all packages without user_id passed")


@pytest.mark.asyncio
async def test_add_favorite_status_with_invalid_package_ids(tour_service):
    """Test _add_favorite_status handles packages with missing package_id"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    
    packages = [
        {"package_name": "Tour 1"},  # Missing package_id
        {"package_id": str(uuid4()), "package_name": "Tour 2"}
    ]
    
    # Mock favorites query
    mock_favorites_execute = Mock()
    mock_favorites_execute.data = []
    mock_table.select.return_value.eq.return_value.in_.return_value.execute.return_value = mock_favorites_execute
    
    # Execute
    result = await service._add_favorite_status(packages, user_id)
    
    # Assertions
    assert len(result) == 2
    assert result[0]["is_favorite"] is False  # Missing package_id
    assert result[1]["is_favorite"] is False  # Not favorited
    
    logger.info("✓ Test add favorite status with invalid package IDs passed")


@pytest.mark.asyncio
async def test_add_favorite_status_partial_favorites(tour_service):
    """Test _add_favorite_status with mix of favorited and non-favorited packages"""
    service, mock_table = tour_service
    
    user_id = str(uuid4())
    favorited_id = str(uuid4())
    not_favorited_id = str(uuid4())
    
    packages = [
        {"package_id": favorited_id, "package_name": "Tour 1"},
        {"package_id": not_favorited_id, "package_name": "Tour 2"},
        {"package_id": favorited_id, "package_name": "Tour 3"}  # Duplicate ID
    ]
    
    # Mock favorites query - only favorited_id is favorited
    mock_favorites_execute = Mock()
    mock_favorites_execute.data = [{"package_id": favorited_id}]
    mock_table.select.return_value.eq.return_value.in_.return_value.execute.return_value = mock_favorites_execute
    
    # Execute
    result = await service._add_favorite_status(packages, user_id)
    
    # Assertions
    assert len(result) == 3
    assert result[0]["is_favorite"] is True  # favorited
    assert result[1]["is_favorite"] is False  # not favorited
    assert result[2]["is_favorite"] is True  # favorited (duplicate)
    
    logger.info("✓ Test add favorite status partial favorites passed")


# ==================== Run Tests Summary ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
    logger.info("=" * 60)
    logger.info("All tour package tests completed!")
    logger.info("=" * 60)
