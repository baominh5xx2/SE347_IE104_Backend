"""
Test Report APIs
"""
import pytest
from datetime import date, timedelta
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    client = MagicMock()
    return client


@pytest.fixture
def sample_bookings_data():
    """Sample bookings data for testing"""
    return [
        {
            "booking_id": "booking-1",
            "package_id": "tour-a",
            "number_of_people": 5,
            "total_amount": 12000000,
            "created_at": "2025-12-08T10:00:00",
            "status": "confirmed",
            "tour_packages": {
                "package_id": "tour-a",
                "package_name": "Tour Đà Lạt",
                "destination": "Đà Lạt",
                "price": 3000000
            }
        },
        {
            "booking_id": "booking-2",
            "package_id": "tour-b",
            "number_of_people": 3,
            "total_amount": 24000000,
            "created_at": "2025-12-08T14:00:00",
            "status": "confirmed",
            "tour_packages": {
                "package_id": "tour-b",
                "package_name": "Tour Nha Trang",
                "destination": "Nha Trang",
                "price": 8000000
            }
        },
        {
            "booking_id": "booking-3",
            "package_id": "tour-c",
            "number_of_people": 2,
            "total_amount": 40000000,
            "created_at": "2025-12-08T16:00:00",
            "status": "pending",
            "tour_packages": {
                "package_id": "tour-c",
                "package_name": "Tour Phú Quốc Premium",
                "destination": "Phú Quốc",
                "price": 20000000
            }
        }
    ]


class TestRevenueReport:
    """Test revenue report endpoints"""
    
    @pytest.mark.asyncio
    async def test_revenue_report_by_week(self, mock_supabase_client, sample_bookings_data):
        """Test revenue report by week"""
        from app.v1.services.report_service import ReportService
        
        # Mock response
        mock_response = MagicMock()
        mock_response.data = sample_bookings_data
        mock_supabase_client.table.return_value.select.return_value.gte.return_value.lte.return_value.neq.return_value.execute.return_value = mock_response
        
        service = ReportService(mock_supabase_client)
        result = await service.get_revenue_report(
            period_type="week",
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 8)
        )
        
        assert result["EC"] == 0
        assert result["EM"] == "Success"
        assert result["period_type"] == "week"
        assert "data" in result
        assert result["total_revenue"] > 0
        assert result["total_bookings"] > 0
    
    @pytest.mark.asyncio
    async def test_revenue_report_by_month(self, mock_supabase_client, sample_bookings_data):
        """Test revenue report by month"""
        from app.v1.services.report_service import ReportService
        
        mock_response = MagicMock()
        mock_response.data = sample_bookings_data
        mock_supabase_client.table.return_value.select.return_value.gte.return_value.lte.return_value.neq.return_value.execute.return_value = mock_response
        
        service = ReportService(mock_supabase_client)
        result = await service.get_revenue_report(
            period_type="month",
            num_periods=3
        )
        
        assert result["EC"] == 0
        assert result["period_type"] == "month"
        assert isinstance(result["data"], list)
    
    @pytest.mark.asyncio
    async def test_revenue_report_empty_data(self, mock_supabase_client):
        """Test revenue report with no bookings"""
        from app.v1.services.report_service import ReportService
        
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table.return_value.select.return_value.gte.return_value.lte.return_value.neq.return_value.execute.return_value = mock_response
        
        service = ReportService(mock_supabase_client)
        result = await service.get_revenue_report(
            period_type="week",
            num_periods=1
        )
        
        assert result["EC"] == 0
        assert result["total_revenue"] == 0
        assert result["total_bookings"] == 0
        assert len(result["data"]) == 0


class TestPeopleByPriceRange:
    """Test people by price range statistics endpoints"""
    
    @pytest.mark.asyncio
    async def test_people_stats_by_week(self, mock_supabase_client, sample_bookings_data):
        """Test people statistics by week"""
        from app.v1.services.report_service import ReportService
        
        mock_response = MagicMock()
        mock_response.data = sample_bookings_data
        mock_supabase_client.table.return_value.select.return_value.gte.return_value.lte.return_value.neq.return_value.execute.return_value = mock_response
        
        service = ReportService(mock_supabase_client)
        result = await service.get_people_stats_by_price_range(
            period_type="week",
            target_date=date(2025, 12, 8)
        )
        
        assert result["EC"] == 0
        assert result["EM"] == "Success"
        assert result["period_type"] == "week"
        assert "period_start" in result
        assert "period_end" in result
        assert len(result["data"]) == 3  # budget, medium, premium
        
        # Check all price ranges are present
        price_ranges = [item["price_range"] for item in result["data"]]
        assert "budget" in price_ranges
        assert "medium" in price_ranges
        assert "premium" in price_ranges
        
        # Verify totals
        assert result["total_people_all_ranges"] >= 0
        assert result["total_bookings_all_ranges"] >= 0
    
    @pytest.mark.asyncio
    async def test_people_stats_by_month(self, mock_supabase_client, sample_bookings_data):
        """Test people statistics by month"""
        from app.v1.services.report_service import ReportService
        
        mock_response = MagicMock()
        mock_response.data = sample_bookings_data
        mock_supabase_client.table.return_value.select.return_value.gte.return_value.lte.return_value.neq.return_value.execute.return_value = mock_response
        
        service = ReportService(mock_supabase_client)
        result = await service.get_people_stats_by_price_range(
            period_type="month",
            target_date=date(2025, 12, 1)
        )
        
        assert result["EC"] == 0
        assert result["period_type"] == "month"
        assert len(result["data"]) == 3
    
    @pytest.mark.asyncio
    async def test_price_range_categorization(self, mock_supabase_client, sample_bookings_data):
        """Test that bookings are correctly categorized by price range"""
        from app.v1.services.report_service import ReportService
        
        mock_response = MagicMock()
        mock_response.data = sample_bookings_data
        mock_supabase_client.table.return_value.select.return_value.gte.return_value.lte.return_value.neq.return_value.execute.return_value = mock_response
        
        service = ReportService(mock_supabase_client)
        result = await service.get_people_stats_by_price_range(
            period_type="week",
            target_date=date(2025, 12, 8)
        )
        
        # Find each price range
        budget = next((item for item in result["data"] if item["price_range"] == "budget"), None)
        medium = next((item for item in result["data"] if item["price_range"] == "medium"), None)
        premium = next((item for item in result["data"] if item["price_range"] == "premium"), None)
        
        assert budget is not None
        assert medium is not None
        assert premium is not None
        
        # Budget should have tour-a (3M)
        assert budget["total_people"] == 5
        assert budget["price_min"] == 0
        assert budget["price_max"] == 5000000
        
        # Medium should have tour-b (8M)
        assert medium["total_people"] == 3
        assert medium["price_min"] == 5000000
        assert medium["price_max"] == 15000000
        
        # Premium should have tour-c (20M)
        assert premium["total_people"] == 2
        assert premium["price_min"] == 15000000
        assert premium["price_max"] is None
    
    @pytest.mark.asyncio
    async def test_people_stats_empty_data(self, mock_supabase_client):
        """Test people statistics with no bookings"""
        from app.v1.services.report_service import ReportService
        
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table.return_value.select.return_value.gte.return_value.lte.return_value.neq.return_value.execute.return_value = mock_response
        
        service = ReportService(mock_supabase_client)
        result = await service.get_people_stats_by_price_range(
            period_type="week"
        )
        
        assert result["EC"] == 0
        assert result["total_people_all_ranges"] == 0
        assert result["total_bookings_all_ranges"] == 0
        
        # All price ranges should have zero values
        for item in result["data"]:
            assert item["total_people"] == 0
            assert item["total_bookings"] == 0
            assert item["total_tours"] == 0


class TestReportServiceHelpers:
    """Test helper methods in ReportService"""
    
    def test_get_price_range_category(self, mock_supabase_client):
        """Test price range categorization"""
        from app.v1.services.report_service import ReportService
        
        service = ReportService(mock_supabase_client)
        
        # Budget: < 5M
        assert service._get_price_range_category(1000000) == "budget"
        assert service._get_price_range_category(4999999) == "budget"
        
        # Medium: 5M - 15M
        assert service._get_price_range_category(5000000) == "medium"
        assert service._get_price_range_category(10000000) == "medium"
        assert service._get_price_range_category(14999999) == "medium"
        
        # Premium: > 15M
        assert service._get_price_range_category(15000000) == "premium"
        assert service._get_price_range_category(20000000) == "premium"
        assert service._get_price_range_category(50000000) == "premium"
    
    def test_get_week_boundaries(self, mock_supabase_client):
        """Test week boundary calculation"""
        from app.v1.services.report_service import ReportService
        
        service = ReportService(mock_supabase_client)
        
        # Test Monday
        target = date(2025, 12, 8)  # Monday
        start, end = service._get_week_boundaries(target)
        assert start == date(2025, 12, 8)  # Monday
        assert end == date(2025, 12, 14)  # Sunday
        assert (end - start).days == 6
        
        # Test Sunday
        target = date(2025, 12, 7)  # Sunday
        start, end = service._get_week_boundaries(target)
        assert start == date(2025, 12, 1)  # Monday of that week
        assert end == date(2025, 12, 7)  # Sunday
        
        # Test Wednesday
        target = date(2025, 12, 10)  # Wednesday
        start, end = service._get_week_boundaries(target)
        assert start == date(2025, 12, 8)  # Monday
        assert end == date(2025, 12, 14)  # Sunday
    
    def test_get_month_boundaries(self, mock_supabase_client):
        """Test month boundary calculation"""
        from app.v1.services.report_service import ReportService
        
        service = ReportService(mock_supabase_client)
        
        # Test December 2025
        target = date(2025, 12, 15)
        start, end = service._get_month_boundaries(target)
        assert start == date(2025, 12, 1)
        assert end == date(2025, 12, 31)
        
        # Test February 2024 (leap year)
        target = date(2024, 2, 15)
        start, end = service._get_month_boundaries(target)
        assert start == date(2024, 2, 1)
        assert end == date(2024, 2, 29)
        
        # Test February 2025 (non-leap year)
        target = date(2025, 2, 15)
        start, end = service._get_month_boundaries(target)
        assert start == date(2025, 2, 1)
        assert end == date(2025, 2, 28)
        
        # Test November (30 days)
        target = date(2025, 11, 15)
        start, end = service._get_month_boundaries(target)
        assert start == date(2025, 11, 1)
        assert end == date(2025, 11, 30)


class TestReportEndpoints:
    """Test report API endpoints"""
    
    @pytest.mark.asyncio
    async def test_revenue_endpoint_validation(self):
        """Test revenue endpoint parameter validation"""
        # This would be an integration test with actual FastAPI app
        # Testing that invalid dates are rejected
        pass
    
    @pytest.mark.asyncio
    async def test_people_stats_endpoint_validation(self):
        """Test people stats endpoint parameter validation"""
        # This would be an integration test with actual FastAPI app
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
