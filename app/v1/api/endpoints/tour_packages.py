"""
Tour Package API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID

from ...schema.tour_package_schema import (
    TourPackageCreate,
    TourPackageUpdate,
    TourPackageListResponse,
    TourPackageDetailResponse,
    TourPackageCreateResponse,
    TourPackageUpdateResponse,
    TourPackageDeleteResponse,
    TourPackageSearchRequest,
    TourPackageRecommendRequest,
    TourPackageSearchResponse
)
from ...services.tour_package_service import TourPackageService
from ...core.supabase import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


def get_tour_package_service():
    """Dependency to get TourPackageService instance"""
    supabase = get_supabase_client()
    return TourPackageService(supabase)


@router.post("/recommend", response_model=TourPackageSearchResponse)
async def recommend_tour_packages(
    request: TourPackageRecommendRequest,
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Recommend tour packages dựa trên tour gần hết hạn và đặc điểm user từ Mem0
    
    Logic:
    1. Tìm 10 tour gần hết hạn nhất (dựa vào end_date)
    2. Lấy đặc điểm user từ Mem0 (preferences, lịch sử tìm kiếm)
    3. Dùng hybrid search để tìm k tour phù hợp nhất từ 10 tour gần hết hạn
    
    Args:
        request: TourPackageRecommendRequest với user_id và k
        service: Tour package service instance
        
    Returns:
        TourPackageSearchResponse với danh sách k tour được recommend
        
    Example:
        POST /api/v1/tour-packages/recommend
        Body:
        {
            "user_id": "user123",
            "k": 5
        }
    """
    try:
        result = await service.recommend_packages(
            user_id=request.user_id,
            k=request.k
        )
        return TourPackageSearchResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in recommend_tour_packages endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=TourPackageSearchResponse)
async def search_tour_packages(
    request: TourPackageSearchRequest,
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Tìm kiếm tour packages sử dụng hybrid search (semantic + keyword + filters)
    
    Sử dụng:
    - Semantic search: Supabase native pgvector search (text-embedding-3-small)
    - Keyword search: PostgreSQL full-text search trên package_name, destination, description
    - Filters: Database-level filters cho price, duration, destination
    - Scoring: Weighted combination (0.7 semantic + 0.3 keyword)
    
    Args:
        request: TourPackageSearchRequest với query và filters
        service: Tour package service instance
        
    Returns:
        TourPackageSearchResponse với danh sách tour packages và scores
        
    Example:
        POST /api/v1/tour-packages/search
        Body:
        {
            "q": "Tôi muốn đi Đà Lạt",
            "max_price": 3000000,
            "limit": 10
        }
    """
    try:
        result = await service.search_packages(
            user_message=request.q,
            max_price=request.max_price,
            duration=request.duration,
            destination=request.destination,
            limit=request.limit
        )
        return TourPackageSearchResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in search_tour_packages endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=TourPackageListResponse)
async def get_tour_packages(
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    destination: Optional[str] = Query(None, description="Lọc theo điểm đến"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Lấy danh sách tất cả tour packages
    
    Args:
        is_active: Lọc theo trạng thái hoạt động (True/False)
        destination: Lọc theo điểm đến (tìm kiếm gần đúng)
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        service: Tour package service instance
        
    Returns:
        TourPackageListResponse với danh sách tour packages
        
    Example:
        GET /api/v1/tour-packages?is_active=true&limit=10
        GET /api/v1/tour-packages?destination=Đà Lạt
    """
    try:
        result = await service.get_all_packages(
            is_active=is_active,
            destination=destination,
            limit=limit,
            offset=offset
        )
        return TourPackageListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_tour_packages endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{package_id}", response_model=TourPackageDetailResponse)
async def get_tour_package(
    package_id: UUID,
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Lấy thông tin chi tiết một tour package
    
    Args:
        package_id: UUID của tour package
        service: Tour package service instance
        
    Returns:
        TourPackageDetailResponse với thông tin chi tiết tour package
        
    Example:
        GET /api/v1/tour-packages/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.get_package_by_id(str(package_id))
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        
        return TourPackageDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_tour_package endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TourPackageCreateResponse, status_code=201)
async def create_tour_package(
    package: TourPackageCreate,
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Tạo mới một tour package
    
    Args:
        package: Dữ liệu tour package cần tạo
        service: Tour package service instance
        
    Returns:
        TourPackageCreateResponse với thông tin tour package đã tạo
        
    Example:
        POST /api/v1/tour-packages
        Body:
        {
            "package_name": "Tour Đà Lạt 3N2Đ",
            "destination": "Đà Lạt",
            "description": "Tour khám phá thành phố ngàn hoa",
            "duration_days": 3,
            "price": 2500000,
            "available_slots": 20,
            "departure_location": "TP.HCM",
            "start_date": "2024-12-01",
            "end_date": "2024-12-03",
            "includes": ["Khách sạn 4*", "Ăn 3 bữa", "Hướng dẫn viên"],
            "excludes": ["Vé máy bay"],
            "itinerary": {"day1": "Khởi hành", "day2": "Tham quan", "day3": "Về"},
            "image_url": "https://example.com/image.jpg",
            "is_active": true
        }
    """
    try:
        # Convert to dict and handle date serialization
        package_data = package.model_dump()
        
        # Convert dates to ISO format strings
        if package_data.get('start_date'):
            package_data['start_date'] = package_data['start_date'].isoformat()
        if package_data.get('end_date'):
            package_data['end_date'] = package_data['end_date'].isoformat()
        
        result = await service.create_package(package_data)
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return TourPackageCreateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_tour_package endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{package_id}", response_model=TourPackageUpdateResponse)
async def update_tour_package(
    package_id: UUID,
    package: TourPackageUpdate,
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Cập nhật thông tin tour package
    
    Args:
        package_id: UUID của tour package cần cập nhật
        package: Dữ liệu cần cập nhật (các trường optional)
        service: Tour package service instance
        
    Returns:
        TourPackageUpdateResponse với thông tin tour package đã cập nhật
        
    Example:
        PUT /api/v1/tour-packages/123e4567-e89b-12d3-a456-426614174000
        Body:
        {
            "price": 2800000,
            "available_slots": 15,
            "is_active": true
        }
    """
    try:
        # Convert to dict and remove None values
        update_data = package.model_dump(exclude_unset=True)
        
        # Convert dates to ISO format strings if present
        if 'start_date' in update_data and update_data['start_date']:
            update_data['start_date'] = update_data['start_date'].isoformat()
        if 'end_date' in update_data and update_data['end_date']:
            update_data['end_date'] = update_data['end_date'].isoformat()
        
        result = await service.update_package(str(package_id), update_data)
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return TourPackageUpdateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_tour_package endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{package_id}", response_model=TourPackageDeleteResponse)
async def delete_tour_package(
    package_id: UUID,
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Xóa một tour package
    
    Args:
        package_id: UUID của tour package cần xóa
        service: Tour package service instance
        
    Returns:
        TourPackageDeleteResponse với kết quả xóa
        
    Example:
        DELETE /api/v1/tour-packages/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.delete_package(str(package_id))
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return TourPackageDeleteResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_tour_package endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
