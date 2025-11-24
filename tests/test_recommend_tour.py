"""
Unit tests for Tour Package Recommend Endpoint
Tests for recommendation functionality based on expiring tours and user preferences from Mem0
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta
import logging

from app.v1.services.tour_package_service import TourPackageService
from app.v1.api.endpoints.tour_packages import recommend_tour_packages
from app.v1.schema.tour_package_schema import TourPackageRecommendRequest, TourPackageSearchResponse

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
def sample_expiring_tours():
    """Sample expiring tours for testing"""
    now = datetime.now(timezone.utc)
    return [
        {
            "package_id": "111e4567-e89b-12d3-a456-426614174000",
            "package_name": "Tour Đà Lạt 3N2Đ",
            "destination": "Đà Lạt",
            "description": "Tour khám phá thành phố ngàn hoa",
            "duration_days": 3,
            "price": 2500000,
            "available_slots": 20,
            "is_active": True,
            "end_date": (now + timedelta(days=5)).isoformat(),
            "start_date": (now + timedelta(days=2)).isoformat()
        },
        {
            "package_id": "222e4567-e89b-12d3-a456-426614174001",
            "package_name": "Tour Đà Nẵng 2N1Đ",
            "destination": "Đà Nẵng",
            "description": "Tour biển đẹp",
            "duration_days": 2,
            "price": 1800000,
            "available_slots": 15,
            "is_active": True,
            "end_date": (now + timedelta(days=7)).isoformat(),
            "start_date": (now + timedelta(days=3)).isoformat()
        },
        {
            "package_id": "333e4567-e89b-12d3-a456-426614174002",
            "package_name": "Tour Hà Nội 4N3Đ",
            "destination": "Hà Nội",
            "description": "Tour thủ đô",
            "duration_days": 4,
            "price": 3200000,
            "available_slots": 10,
            "is_active": True,
            "end_date": (now + timedelta(days=10)).isoformat(),
            "start_date": (now + timedelta(days=5)).isoformat()
        }
    ]


@pytest.fixture
def sample_mem0_memories():
    """Sample Mem0 memories for testing"""
    return [
        {
            "memory": "User thích đi Đà Lạt, thích khí hậu mát mẻ",
            "content": "User thích đi Đà Lạt, thích khí hậu mát mẻ",
            "score": 0.9
        },
        {
            "memory": "User có ngân sách khoảng 2-3 triệu",
            "content": "User có ngân sách khoảng 2-3 triệu",
            "score": 0.8
        },
        {
            "memory": "User thích tour 2-3 ngày",
            "content": "User thích tour 2-3 ngày",
            "score": 0.7
        }
    ]


@pytest.fixture
def sample_search_results():
    """Sample search results from search service"""
    return [
        {
            "package_id": "111e4567-e89b-12d3-a456-426614174000",
            "package_name": "Tour Đà Lạt 3N2Đ",
            "destination": "Đà Lạt",
            "final_score": 0.85,
            "semantic_score": 0.8,
            "keyword_score": 0.7
        },
        {
            "package_id": "222e4567-e89b-12d3-a456-426614174001",
            "package_name": "Tour Đà Nẵng 2N1Đ",
            "destination": "Đà Nẵng",
            "final_score": 0.75,
            "semantic_score": 0.7,
            "keyword_score": 0.6
        }
    ]


# ==================== TourPackageService Recommend Tests ====================

class TestTourPackageServiceRecommend:
    """Test cases for TourPackageService.recommend_packages method"""
    
    @pytest.mark.asyncio
    async def test_recommend_packages_success(
        self, 
        tour_package_service, 
        sample_expiring_tours, 
        sample_mem0_memories,
        sample_search_results
    ):
        """Test successful recommendation with Mem0 and search service"""
        logger.info("🧪 TEST: Recommend Packages - Success Case")
        service, mock_table = tour_package_service
        
        # Mock Supabase query chain
        mock_query = Mock()
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.gt = Mock(return_value=mock_query)
        mock_query.gte = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.execute = Mock(return_value=Mock(data=sample_expiring_tours))
        mock_table.select = Mock(return_value=mock_query)
        
        with patch('app.v1.services.tour_package_service.mem0_client') as mock_mem0, \
             patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            
            # Mock Mem0 client
            mock_mem0.is_available = True
            mock_mem0.search = Mock(return_value=sample_mem0_memories)
            
            # Mock search service
            mock_search.search_tour_packages = AsyncMock(return_value=sample_search_results)
            
            result = await service.recommend_packages(
                user_id="user123",
                k=2
            )
            
            assert result["EC"] == 0
            assert result["EM"] == "Successfully recommended tour packages"
            assert result["found"] == 2
            assert len(result["packages"]) == 2
            # Verify first package has scores from search
            assert result["packages"][0].get("final_score") is not None
            mock_mem0.search.assert_called_once()
            mock_search.search_tour_packages.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_recommend_packages_no_expiring_tours(self, tour_package_service):
        """Test recommendation when no expiring tours available"""
        logger.info("🧪 TEST: Recommend Packages - No Expiring Tours")
        service, mock_table = tour_package_service
        
        # Mock Supabase query returning empty
        mock_query = Mock()
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.gt = Mock(return_value=mock_query)
        mock_query.gte = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.execute = Mock(return_value=Mock(data=[]))
        mock_table.select = Mock(return_value=mock_query)
        
        result = await service.recommend_packages(
            user_id="user123",
            k=5
        )
        
        assert result["EC"] == 0
        assert result["EM"] == "No expiring tours available"
        assert result["found"] == 0
        assert len(result["packages"]) == 0
    
    @pytest.mark.asyncio
    async def test_recommend_packages_mem0_unavailable(
        self, 
        tour_package_service, 
        sample_expiring_tours,
        sample_search_results
    ):
        """Test recommendation when Mem0 is not available"""
        logger.info("🧪 TEST: Recommend Packages - Mem0 Unavailable")
        service, mock_table = tour_package_service
        
        # Mock Supabase query
        mock_query = Mock()
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.gt = Mock(return_value=mock_query)
        mock_query.gte = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.execute = Mock(return_value=Mock(data=sample_expiring_tours))
        mock_table.select = Mock(return_value=mock_query)
        
        with patch('app.v1.services.tour_package_service.mem0_client') as mock_mem0, \
             patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            
            # Mock Mem0 as unavailable
            mock_mem0.is_available = False
            
            # Mock search service
            mock_search.search_tour_packages = AsyncMock(return_value=sample_search_results)
            
            result = await service.recommend_packages(
                user_id="user123",
                k=2
            )
            
            assert result["EC"] == 0
            assert result["found"] == 2
            # Should still work without Mem0, using default search query
            mock_search.search_tour_packages.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_recommend_packages_search_service_unavailable(
        self, 
        tour_package_service, 
        sample_expiring_tours
    ):
        """Test recommendation when search service is not available"""
        logger.info("🧪 TEST: Recommend Packages - Search Service Unavailable")
        service, mock_table = tour_package_service
        
        # Mock Supabase query
        mock_query = Mock()
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.gt = Mock(return_value=mock_query)
        mock_query.gte = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.execute = Mock(return_value=Mock(data=sample_expiring_tours))
        mock_table.select = Mock(return_value=mock_query)
        
        with patch('app.v1.services.tour_package_service.tour_package_search_service', None):
            result = await service.recommend_packages(
                user_id="user123",
                k=2
            )
            
            assert result["EC"] == 0
            assert result["EM"] == "Successfully retrieved expiring tours"
            assert result["found"] == 2
            assert len(result["packages"]) == 2
            # Should return expiring tours directly without scores
            assert result["packages"][0].get("package_id") in [t["package_id"] for t in sample_expiring_tours]
    
    @pytest.mark.asyncio
    async def test_recommend_packages_no_memories(
        self, 
        tour_package_service, 
        sample_expiring_tours,
        sample_search_results
    ):
        """Test recommendation when user has no memories in Mem0"""
        logger.info("🧪 TEST: Recommend Packages - No Memories")
        service, mock_table = tour_package_service
        
        # Mock Supabase query
        mock_query = Mock()
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.gt = Mock(return_value=mock_query)
        mock_query.gte = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.execute = Mock(return_value=Mock(data=sample_expiring_tours))
        mock_table.select = Mock(return_value=mock_query)
        
        with patch('app.v1.services.tour_package_service.mem0_client') as mock_mem0, \
             patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            
            # Mock Mem0 returning empty
            mock_mem0.is_available = True
            mock_mem0.search = Mock(return_value=[])
            
            # Mock search service
            mock_search.search_tour_packages = AsyncMock(return_value=sample_search_results)
            
            result = await service.recommend_packages(
                user_id="user123",
                k=2
            )
            
            assert result["EC"] == 0
            assert result["found"] == 2
            # Should use default search query when no memories
            mock_search.search_tour_packages.assert_called_once()
            call_args = mock_search.search_tour_packages.call_args
            assert "Tìm tour du lịch phù hợp" in call_args[1]["user_message"]
    
    @pytest.mark.asyncio
    async def test_recommend_packages_insufficient_search_results(
        self, 
        tour_package_service, 
        sample_expiring_tours,
        sample_mem0_memories
    ):
        """Test recommendation when search returns fewer results than k"""
        logger.info("🧪 TEST: Recommend Packages - Insufficient Search Results")
        service, mock_table = tour_package_service
        
        # Mock Supabase query
        mock_query = Mock()
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.gt = Mock(return_value=mock_query)
        mock_query.gte = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.execute = Mock(return_value=Mock(data=sample_expiring_tours))
        mock_table.select = Mock(return_value=mock_query)
        
        with patch('app.v1.services.tour_package_service.mem0_client') as mock_mem0, \
             patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            
            # Mock Mem0
            mock_mem0.is_available = True
            mock_mem0.search = Mock(return_value=sample_mem0_memories)
            
            # Mock search service returning only 1 result (less than k=3)
            mock_search.search_tour_packages = AsyncMock(return_value=[
                {
                    "package_id": "111e4567-e89b-12d3-a456-426614174000",
                    "final_score": 0.85
                }
            ])
            
            result = await service.recommend_packages(
                user_id="user123",
                k=3
            )
            
            assert result["EC"] == 0
            assert result["found"] == 3
            # Should fill remaining slots from expiring tours
            assert len(result["packages"]) == 3
    
    @pytest.mark.asyncio
    async def test_recommend_packages_error_handling(self, tour_package_service):
        """Test recommendation error handling"""
        logger.info("🧪 TEST: Recommend Packages - Error Handling")
        service, mock_table = tour_package_service
        
        # Mock Supabase query throwing error
        mock_query = Mock()
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.gt = Mock(return_value=mock_query)
        mock_query.gte = Mock(side_effect=Exception("Database error"))
        mock_table.select = Mock(return_value=mock_query)
        
        result = await service.recommend_packages(
            user_id="user123",
            k=5
        )
        
        assert result["EC"] == 1
        assert "Error recommending tour packages" in result["EM"]
        assert result["found"] == 0
        assert len(result["packages"]) == 0


# ==================== Recommend Endpoint Tests ====================

class TestRecommendTourPackagesEndpoint:
    """Test cases for recommend_tour_packages endpoint"""
    
    @pytest.mark.asyncio
    async def test_endpoint_recommend_success(
        self, 
        tour_package_service, 
        sample_expiring_tours,
        sample_search_results
    ):
        """Test successful recommend endpoint call"""
        logger.info("🧪 TEST: Recommend Endpoint - Success Case")
        service, _ = tour_package_service
        
        mock_recommend = AsyncMock(return_value={
            "EC": 0,
            "EM": "Successfully recommended tour packages",
            "found": 2,
            "packages": sample_search_results
        })
        service.recommend_packages = mock_recommend
        
        request = TourPackageRecommendRequest(user_id="user123", k=2)
        response = await recommend_tour_packages(
            request=request,
            service=service
        )
        
        assert isinstance(response, TourPackageSearchResponse)
        assert response.EC == 0
        assert response.found == 2
        assert len(response.packages) == 2
        mock_recommend.assert_called_once_with(
            user_id="user123",
            k=2
        )
    
    @pytest.mark.asyncio
    async def test_endpoint_recommend_default_k(self, tour_package_service, sample_search_results):
        """Test recommend endpoint with default k value"""
        logger.info("🧪 TEST: Recommend Endpoint - Default K")
        service, _ = tour_package_service
        
        mock_recommend = AsyncMock(return_value={
            "EC": 0,
            "EM": "Successfully recommended tour packages",
            "found": 5,
            "packages": sample_search_results * 3
        })
        service.recommend_packages = mock_recommend
        
        request = TourPackageRecommendRequest(user_id="user123")  # Default k=5
        response = await recommend_tour_packages(
            request=request,
            service=service
        )
        
        assert response.EC == 0
        # Default k is 5
        assert mock_recommend.called
        call_kwargs = mock_recommend.call_args.kwargs
        assert call_kwargs["user_id"] == "user123"
        assert call_kwargs["k"] == 5
    
    @pytest.mark.asyncio
    async def test_endpoint_recommend_no_results(self, tour_package_service):
        """Test recommend endpoint with no results"""
        logger.info("🧪 TEST: Recommend Endpoint - No Results")
        service, _ = tour_package_service
        
        mock_recommend = AsyncMock(return_value={
            "EC": 0,
            "EM": "No expiring tours available",
            "found": 0,
            "packages": []
        })
        service.recommend_packages = mock_recommend
        
        request = TourPackageRecommendRequest(user_id="user123", k=5)
        response = await recommend_tour_packages(
            request=request,
            service=service
        )
        
        assert response.EC == 0
        assert response.found == 0
        assert len(response.packages) == 0
    
    @pytest.mark.asyncio
    async def test_endpoint_recommend_error_handling(self, tour_package_service):
        """Test recommend endpoint error handling"""
        logger.info("🧪 TEST: Recommend Endpoint - Error Handling")
        service, _ = tour_package_service
        
        mock_recommend = AsyncMock(side_effect=Exception("Service error"))
        service.recommend_packages = mock_recommend
        
        request = TourPackageRecommendRequest(user_id="user123", k=5)
        with pytest.raises(HTTPException) as exc_info:
            await recommend_tour_packages(
                request=request,
                service=service
            )
        
        assert exc_info.value.status_code == 500
        assert "Service error" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_endpoint_recommend_parameter_validation(self, tour_package_service):
        """Test recommend endpoint parameter validation"""
        logger.info("🧪 TEST: Recommend Endpoint - Parameter Validation")
        service, _ = tour_package_service
        
        mock_recommend = AsyncMock(return_value={
            "EC": 0,
            "EM": "Successfully recommended tour packages",
            "found": 10,
            "packages": []
        })
        service.recommend_packages = mock_recommend
        
        # Test with max k value (10)
        request = TourPackageRecommendRequest(user_id="user123", k=10)
        response = await recommend_tour_packages(
            request=request,
            service=service
        )
        
        assert response.EC == 0
        assert mock_recommend.called
        call_kwargs = mock_recommend.call_args.kwargs
        assert call_kwargs["user_id"] == "user123"
        assert call_kwargs["k"] == 10


# ==================== Integration Tests ====================

class TestRecommendIntegration:
    """Integration tests for recommend functionality"""
    
    @pytest.mark.asyncio
    async def test_full_recommend_flow(self, tour_package_service):
        """Test full recommend flow from service to response"""
        logger.info("🧪 TEST: Full Recommend Flow Integration")
        service, mock_table = tour_package_service
        
        sample_tours = [
            {
                "package_id": "111e4567-e89b-12d3-a456-426614174000",
                "package_name": "Tour Đà Lạt",
                "destination": "Đà Lạt",
                "price": 2500000,
                "end_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
            }
        ]
        
        # Mock Supabase
        mock_query = Mock()
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.gt = Mock(return_value=mock_query)
        mock_query.gte = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.execute = Mock(return_value=Mock(data=sample_tours))
        mock_table.select = Mock(return_value=mock_query)
        
        with patch('app.v1.services.tour_package_service.mem0_client') as mock_mem0, \
             patch('app.v1.services.tour_package_service.tour_package_search_service') as mock_search:
            
            mock_mem0.is_available = True
            mock_mem0.search = Mock(return_value=[])
            mock_search.search_tour_packages = AsyncMock(return_value=[
                {
                    "package_id": "111e4567-e89b-12d3-a456-426614174000",
                    "final_score": 0.85
                }
            ])
            
            # Test service method
            service_result = await service.recommend_packages(
                user_id="user123",
                k=1
            )
            
            assert service_result["EC"] == 0
            assert service_result["found"] == 1
            
            # Test endpoint with service
            mock_service = AsyncMock(return_value=service_result)
            service.recommend_packages = mock_service
            
            request = TourPackageRecommendRequest(user_id="user123", k=1)
            response = await recommend_tour_packages(
                request=request,
                service=service
            )
            
            assert isinstance(response, TourPackageSearchResponse)
            assert response.EC == 0
            assert response.found == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

