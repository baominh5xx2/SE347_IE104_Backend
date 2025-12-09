"""
Report Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from enum import Enum


class ReportPeriod(str, Enum):
    """Enum for report period types"""
    WEEK = "week"
    MONTH = "month"


class PriceRange(str, Enum):
    """Enum for tour price ranges"""
    BUDGET = "budget"  # < 5,000,000 VND
    MEDIUM = "medium"  # 5,000,000 - 15,000,000 VND
    PREMIUM = "premium"  # > 15,000,000 VND


class RevenueReportItem(BaseModel):
    """Single revenue report item for a time period"""
    period_start: date = Field(..., description="Ngày bắt đầu chu kỳ")
    period_end: date = Field(..., description="Ngày kết thúc chu kỳ")
    total_revenue: float = Field(..., description="Tổng doanh thu trong chu kỳ")
    total_bookings: int = Field(..., description="Tổng số booking trong chu kỳ")
    
    model_config = {"from_attributes": True}


class RevenueReportResponse(BaseModel):
    """Response schema for revenue report"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    period_type: str = Field(..., description="Loại chu kỳ: week hoặc month")
    data: List[RevenueReportItem] = Field(default=[], description="Danh sách doanh thu theo chu kỳ")
    total_revenue: float = Field(..., description="Tổng doanh thu toàn bộ khoảng thời gian")
    total_bookings: int = Field(..., description="Tổng số booking toàn bộ khoảng thời gian")


class PriceRangeStatItem(BaseModel):
    """Statistics for a single price range"""
    price_range: str = Field(..., description="Phân khúc giá: budget/medium/premium")
    price_min: float = Field(..., description="Giá tối thiểu của phân khúc")
    price_max: Optional[float] = Field(None, description="Giá tối đa của phân khúc (None = không giới hạn)")
    total_people: int = Field(..., description="Tổng số người đi tour trong phân khúc này")
    total_bookings: int = Field(..., description="Tổng số booking trong phân khúc này")
    total_tours: int = Field(..., description="Số lượng tour khác nhau trong phân khúc")
    
    model_config = {"from_attributes": True}


class PriceRangeStatsResponse(BaseModel):
    """Response schema for price range statistics report"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    period_type: str = Field(..., description="Loại chu kỳ: week hoặc month")
    period_start: date = Field(..., description="Ngày bắt đầu chu kỳ")
    period_end: date = Field(..., description="Ngày kết thúc chu kỳ")
    data: List[PriceRangeStatItem] = Field(default=[], description="Thống kê theo từng phân khúc giá")
    total_people_all_ranges: int = Field(..., description="Tổng số người đi tour tất cả phân khúc")
    total_bookings_all_ranges: int = Field(..., description="Tổng số booking tất cả phân khúc")
