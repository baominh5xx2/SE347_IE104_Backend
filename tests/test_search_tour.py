"""
Unit tests for Tour Package Search Endpoint
Tests for hybrid search functionality (semantic + keyword + filters)
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
import logging

from app.v1.services.tour_package_service import TourPackageService
from app.v1.api.endpoints.tour_packages import search_tour_packages
from app.v1.schema.tour_package_schema import TourPackageSearchResponse

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
def tour_package_service(mock_supabase_client):
    """Create TourPackageService instance with mocked Supabase client"""
    client, _ = mock_supabase_client
    service = TourPackageService(client)
    return service, mock_supabase_client[1]


@pytest.fixture
def mock_search_service():
    """Mock TourPackageSearchService"""
    mock_service = AsyncMock()
    return mock_service


@pytest.fixture
def sample_search_results():
    """Sample search results for testing"""
    return [
        {
            "package_id": "123e4567-e89b-12d3-a456-426614174000",
            "package_name": "Tour Đà Lạt 3N2Đ",
            "destination": "Đà Lạt",
            "description": "Tour khám phá thành phố ngàn hoa",
            "duration_days": 3,
            "price": 2500000,
            "available_slots": 20,
            "final_score": 0.85,
            "semantic_score": 0.8,
            "keyword_score": 0.7
        },
        {
            "package_id": "223e4567-e89b-12d3-a456-426614174001",
            "package_name": "Tour Đà Lạt 2N1Đ",
            "destination": "Đà Lạt",
            "description": "Tour ngắn ngày Đà Lạt",
            "duration_days": 2,
            "price": 1800000,
            "available_slots": 15,
            "final_score": 0.75,
            "semantic_score": 0.7,
            "keyword_score": 0.6
        }
    ]


# ==================== TourPackageService Search Tests ====================

class TestTourPackageServiceSearch:
    """Test cases for TourPackageService.search_packages method"""
    
    @pytest.mark.asyncio
    async def test_search_packages_success(self, tour_package_service, sample_search_results):
        """Test successful search with results"""
        logger.info("🧪 TEST: Search Packages - Success Case")
        service, _ = tour_package_service
        
        with patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            mock_search.search_tour_packages = AsyncMock(return_value=sample_search_results)
            
            result = await service.search_packages(
                user_message="Tôi muốn đi Đà Lạt",
                limit=10
            )
            
            assert result["EC"] == 0
            assert result["EM"] == "Successfully searched tour packages"
            assert result["found"] == 2
            assert len(result["packages"]) == 2
            assert result["packages"][0]["package_id"] == "123e4567-e89b-12d3-a456-426614174000"
            mock_search.search_tour_packages.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_packages_with_filters(self, tour_package_service, sample_search_results):
        """Test search with filters (max_price, duration, destination)"""
        logger.info("🧪 TEST: Search Packages - With Filters")
        service, _ = tour_package_service
        
        with patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            mock_search.search_tour_packages = AsyncMock(return_value=sample_search_results[:1])
            
            result = await service.search_packages(
                user_message="Tour Đà Lạt",
                max_price=3000000,
                duration=3,
                destination="Đà Lạt",
                limit=5
            )
            
            assert result["EC"] == 0
            assert result["found"] == 1
            # Verify filters were passed correctly
            call_args = mock_search.search_tour_packages.call_args
            assert call_args[1]["filters"]["max_price"] == 3000000
            assert call_args[1]["filters"]["duration"] == 3
            assert call_args[1]["filters"]["destination"] == "Đà Lạt"
            assert call_args[1]["limit"] == 5
    
    @pytest.mark.asyncio
    async def test_search_packages_no_results(self, tour_package_service):
        """Test search with no results"""
        logger.info("🧪 TEST: Search Packages - No Results")
        service, _ = tour_package_service
        
        with patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            mock_search.search_tour_packages = AsyncMock(return_value=[])
            
            result = await service.search_packages(
                user_message="Tour không tồn tại",
                limit=10
            )
            
            assert result["EC"] == 0
            assert result["found"] == 0
            assert len(result["packages"]) == 0
    
    @pytest.mark.asyncio
    async def test_search_packages_service_unavailable(self, tour_package_service):
        """Test search when search service is not available"""
        logger.info("🧪 TEST: Search Packages - Service Unavailable")
        service, _ = tour_package_service
        
        with patch('app.v1.services.tour_package_service.tour_package_search_service', None):
            result = await service.search_packages(
                user_message="Tôi muốn đi Đà Lạt",
                limit=10
            )
            
            assert result["EC"] == 1
            assert "not available" in result["EM"]
            assert result["found"] == 0
            assert len(result["packages"]) == 0
    
    @pytest.mark.asyncio
    async def test_search_packages_error_handling(self, tour_package_service):
        """Test search error handling"""
        logger.info("🧪 TEST: Search Packages - Error Handling")
        service, _ = tour_package_service
        
        with patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            mock_search.search_tour_packages = AsyncMock(side_effect=Exception("Database error"))
            
            result = await service.search_packages(
                user_message="Tôi muốn đi Đà Lạt",
                limit=10
            )
            
            assert result["EC"] == 1
            assert "Error searching tour packages" in result["EM"]
            assert result["found"] == 0
            assert len(result["packages"]) == 0
    
    @pytest.mark.asyncio
    async def test_search_packages_partial_filters(self, tour_package_service, sample_search_results):
        """Test search with partial filters (only max_price)"""
        logger.info("🧪 TEST: Search Packages - Partial Filters")
        service, _ = tour_package_service
        
        with patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            mock_search.search_tour_packages = AsyncMock(return_value=sample_search_results)
            
            result = await service.search_packages(
                user_message="Tour Đà Lạt",
                max_price=3000000,
                limit=10
            )
            
            assert result["EC"] == 0
            assert result["found"] == 2
            # Verify only max_price filter was passed
            call_args = mock_search.search_tour_packages.call_args
            assert "max_price" in call_args[1]["filters"]
            assert "duration" not in call_args[1]["filters"]
            assert "destination" not in call_args[1]["filters"]


# ==================== Search Endpoint Tests ====================

class TestSearchTourPackagesEndpoint:
    """Test cases for search_tour_packages endpoint"""
    
    @pytest.mark.asyncio
    async def test_endpoint_search_success(self, tour_package_service, sample_search_results):
        """Test successful search endpoint call"""
        logger.info("🧪 TEST: Search Endpoint - Success Case")
        service, _ = tour_package_service
        
        mock_search = AsyncMock(return_value={
            "EC": 0,
            "EM": "Successfully searched tour packages",
            "found": 2,
            "packages": sample_search_results
        })
        service.search_packages = mock_search
        
        response = await search_tour_packages(
            q="Tôi muốn đi Đà Lạt",
            limit=10,
            service=service
        )
        
        assert isinstance(response, TourPackageSearchResponse)
        assert response.EC == 0
        assert response.found == 2
        assert len(response.packages) == 2
        # Verify method was called - check call count and key parameters
        assert mock_search.called
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["user_message"] == "Tôi muốn đi Đà Lạt"
        assert call_kwargs["limit"] == 10
        # Optional params may be None or Query(None) - both are acceptable
    
    @pytest.mark.asyncio
    async def test_endpoint_search_with_filters(self, tour_package_service, sample_search_results):
        """Test search endpoint with all filters"""
        logger.info("🧪 TEST: Search Endpoint - With Filters")
        service, _ = tour_package_service
        
        mock_search = AsyncMock(return_value={
            "EC": 0,
            "EM": "Successfully searched tour packages",
            "found": 1,
            "packages": sample_search_results[:1]
        })
        service.search_packages = mock_search
        
        response = await search_tour_packages(
            q="Tour Đà Lạt",
            max_price=3000000.0,
            duration=3,
            destination="Đà Lạt",
            limit=5,
            service=service
        )
        
        assert response.EC == 0
        assert response.found == 1
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args[1]["user_message"] == "Tour Đà Lạt"
        assert call_args[1]["max_price"] == 3000000.0
        assert call_args[1]["duration"] == 3
        assert call_args[1]["destination"] == "Đà Lạt"
        assert call_args[1]["limit"] == 5
    
    @pytest.mark.asyncio
    async def test_endpoint_search_no_results(self, tour_package_service):
        """Test search endpoint with no results"""
        logger.info("🧪 TEST: Search Endpoint - No Results")
        service, _ = tour_package_service
        
        mock_search = AsyncMock(return_value={
            "EC": 0,
            "EM": "Successfully searched tour packages",
            "found": 0,
            "packages": []
        })
        service.search_packages = mock_search
        
        response = await search_tour_packages(
            q="Tour không tồn tại",
            limit=10,
            service=service
        )
        
        assert response.EC == 0
        assert response.found == 0
        assert len(response.packages) == 0
    
    @pytest.mark.asyncio
    async def test_endpoint_search_error_handling(self, tour_package_service):
        """Test search endpoint error handling"""
        logger.info("🧪 TEST: Search Endpoint - Error Handling")
        service, _ = tour_package_service
        
        mock_search = AsyncMock(side_effect=Exception("Database connection error"))
        service.search_packages = mock_search
        
        with pytest.raises(HTTPException) as exc_info:
            await search_tour_packages(
                q="Tôi muốn đi Đà Lạt",
                limit=10,
                service=service
            )
        
        assert exc_info.value.status_code == 500
        assert "Database connection error" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_endpoint_search_validation(self, tour_package_service):
        """Test search endpoint parameter validation"""
        logger.info("🧪 TEST: Search Endpoint - Parameter Validation")
        service, _ = tour_package_service
        
        # Test with valid parameters
        mock_search = AsyncMock(return_value={
            "EC": 0,
            "EM": "Successfully searched tour packages",
            "found": 0,
            "packages": []
        })
        service.search_packages = mock_search
        
        # Test limit bounds (should be validated by FastAPI)
        response = await search_tour_packages(
            q="Test query",
            limit=50,  # Max allowed
            service=service
        )
        
        assert response.EC == 0
        mock_search.assert_called_once()


# ==================== Integration Tests ====================

class TestSearchIntegration:
    """Integration tests for search functionality"""
    
    @pytest.mark.asyncio
    async def test_full_search_flow(self, tour_package_service):
        """Test full search flow from service to response"""
        logger.info("🧪 TEST: Full Search Flow Integration")
        service, _ = tour_package_service
        
        sample_results = [
            {
                "package_id": "123e4567-e89b-12d3-a456-426614174000",
                "package_name": "Tour Đà Lạt 3N2Đ",
                "destination": "Đà Lạt",
                "price": 2500000,
                "final_score": 0.85
            }
        ]
        
        with patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            mock_search.search_tour_packages = AsyncMock(return_value=sample_results)
            
            # Test service method
            service_result = await service.search_packages(
                user_message="Đà Lạt",
                max_price=3000000,
                limit=10
            )
            
            assert service_result["EC"] == 0
            assert service_result["found"] == 1
            
            # Test endpoint with service
            mock_service = AsyncMock(return_value=service_result)
            service.search_packages = mock_service
            
            response = await search_tour_packages(
                q="Đà Lạt",
                max_price=3000000.0,
                limit=10,
                service=service
            )
            
            assert isinstance(response, TourPackageSearchResponse)
            assert response.EC == 0
            assert response.found == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

