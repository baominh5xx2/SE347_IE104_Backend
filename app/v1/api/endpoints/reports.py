"""
Reports Endpoints
API endpoints for analytics and reporting
"""
import logging
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import date

from app.v1.core.dependencies import get_supabase_client
from app.v1.services.report_service import ReportService
from app.v1.schema.report_schema import (
    RevenueReportResponse,
    PriceRangeStatsResponse,
    ReportPeriod
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/revenue",
    response_model=RevenueReportResponse,
    summary="Báo cáo doanh thu theo tuần hoặc tháng",
    description="""
    Lấy báo cáo doanh thu dựa trên total_amount và created_at của bookings.
    
    - **period_type**: Loại chu kỳ báo cáo (week hoặc month)
    - **start_date**: Ngày bắt đầu báo cáo (format: YYYY-MM-DD)
    - **end_date**: Ngày kết thúc báo cáo (format: YYYY-MM-DD, mặc định là hôm nay)
    - **num_periods**: Số chu kỳ hiển thị nếu không có start_date (mặc định 12)
    
    Tính tất cả các booking trừ status 'cancelled'.
    """
)
async def get_revenue_report(
    period_type: ReportPeriod = Query(..., description="Loại chu kỳ: week hoặc month"),
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc (YYYY-MM-DD)"),
    num_periods: int = Query(12, ge=1, le=52, description="Số chu kỳ hiển thị"),
    supabase_client = Depends(get_supabase_client)
):
    """
    Get revenue report by week or month
    
    Example:
    - GET /api/v1/reports/revenue?period_type=week&num_periods=8
    - GET /api/v1/reports/revenue?period_type=month&start_date=2024-01-01&end_date=2024-12-31
    """
    logger.info(f"Getting revenue report: period_type={period_type}, start_date={start_date}, end_date={end_date}")
    
    service = ReportService(supabase_client)
    result = await service.get_revenue_report(
        period_type=period_type.value,
        start_date=start_date,
        end_date=end_date,
        num_periods=num_periods
    )
    
    return result


@router.get(
    "/people-by-price-range/week",
    response_model=PriceRangeStatsResponse,
    summary="Thống kê số lượng người đi tour theo phân khúc giá (Tuần)",
    description="""
    Lấy thống kê tổng số người đi tour trong tuần, phân chia theo các phân khúc giá.
    
    - **target_date**: Ngày để xác định tuần (format: YYYY-MM-DD, mặc định là hôm nay)
    
    Phân khúc giá:
    - budget: < 5,000,000 VND
    - medium: 5,000,000 - 15,000,000 VND
    - premium: > 15,000,000 VND
    
    Tuần bắt đầu từ thứ Hai. Tính tất cả các booking trừ status 'cancelled'.
    Trả về tổng số người (sum of number_of_people) cho mỗi phân khúc giá.
    """
)
async def get_people_stats_by_week(
    target_date: Optional[date] = Query(None, description="Ngày xác định tuần (YYYY-MM-DD)"),
    supabase_client = Depends(get_supabase_client)
):
    """
    Get statistics of people traveling by price range for a specific week
    
    Example:
    - GET /api/v1/reports/people-by-price-range/week
    - GET /api/v1/reports/people-by-price-range/week?target_date=2024-12-01
    """
    logger.info(f"Getting people stats by week: target_date={target_date}")
    
    service = ReportService(supabase_client)
    result = await service.get_people_stats_by_price_range(
        period_type="week",
        target_date=target_date
    )
    
    return result


@router.get(
    "/people-by-price-range/month",
    response_model=PriceRangeStatsResponse,
    summary="Thống kê số lượng người đi tour theo phân khúc giá (Tháng)",
    description="""
    Lấy thống kê tổng số người đi tour trong tháng, phân chia theo các phân khúc giá.
    
    - **target_date**: Ngày để xác định tháng (format: YYYY-MM-DD, mặc định là hôm nay)
    
    Phân khúc giá:
    - budget: < 5,000,000 VND
    - medium: 5,000,000 - 15,000,000 VND
    - premium: > 15,000,000 VND
    
    Tính tất cả các booking trừ status 'cancelled'.
    Trả về tổng số người (sum of number_of_people) cho mỗi phân khúc giá.
    """
)
async def get_people_stats_by_month(
    target_date: Optional[date] = Query(None, description="Ngày xác định tháng (YYYY-MM-DD)"),
    supabase_client = Depends(get_supabase_client)
):
    """
    Get statistics of people traveling by price range for a specific month
    
    Example:
    - GET /api/v1/reports/people-by-price-range/month
    - GET /api/v1/reports/people-by-price-range/month?target_date=2024-12-01
    """
    logger.info(f"Getting people stats by month: target_date={target_date}")
    
    service = ReportService(supabase_client)
    result = await service.get_people_stats_by_price_range(
        period_type="month",
        target_date=target_date
    )
    
    return result


@router.get(
    "/people-by-price-range",
    response_model=PriceRangeStatsResponse,
    summary="Thống kê số lượng người đi tour theo phân khúc giá (Tuần hoặc Tháng)",
    description="""
    API tổng hợp - Lấy thống kê tổng số người đi tour theo tuần hoặc tháng, phân chia theo các phân khúc giá.
    
    - **period_type**: Loại chu kỳ (week hoặc month)
    - **target_date**: Ngày để xác định chu kỳ (format: YYYY-MM-DD, mặc định là hôm nay)
    
    Phân khúc giá:
    - budget: < 5,000,000 VND
    - medium: 5,000,000 - 15,000,000 VND  
    - premium: > 15,000,000 VND
    
    Trả về thống kê cho tất cả 3 phân khúc giá với tổng số người (sum of number_of_people) trong mỗi phân khúc.
    """
)
async def get_people_stats(
    period_type: ReportPeriod = Query(..., description="Loại chu kỳ: week hoặc month"),
    target_date: Optional[date] = Query(None, description="Ngày xác định chu kỳ (YYYY-MM-DD)"),
    supabase_client = Depends(get_supabase_client)
):
    """
    Get statistics of people traveling by price range for a specific period
    
    Example:
    - GET /api/v1/reports/people-by-price-range?period_type=week
    - GET /api/v1/reports/people-by-price-range?period_type=month&target_date=2024-12-01
    """
    logger.info(f"Getting people stats: period_type={period_type}, target_date={target_date}")
    
    service = ReportService(supabase_client)
    result = await service.get_people_stats_by_price_range(
        period_type=period_type.value,
        target_date=target_date
    )
    
    return result
