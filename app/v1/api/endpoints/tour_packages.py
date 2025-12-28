"""
Tour Package API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from typing import Optional, List
from uuid import UUID
import csv
import io
from datetime import date, datetime

from ...schema.tour_package_schema import (
    TourPackageCreate,
    TourPackageUpdate,
    TourPackageListResponse,
    TourPackageDetailResponse,
    TourPackageCreateResponse,
    TourPackageUpdateResponse,
    TourPackageDeleteResponse,
    TourPackageBulkCreateResponse,
    TourPackageSearchRequest,
    TourPackageRecommendRequest,
    TourPackageSearchResponse
)
from ...services.tour_package_service import TourPackageService
from ...core.supabase import get_supabase_client
from ...core.dependencies import get_current_user, get_optional_current_user
from fastapi import Security
from typing import Optional as Opt
from ...core.config import settings

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
    current_user: Opt[dict] = Depends(get_optional_current_user),  # Optional auth
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
        user_id = current_user.get("user_id") if current_user else None
        result = await service.search_packages(
            user_message=request.q,
            max_price=request.max_price,
            duration=request.duration,
            destination=request.destination,
            limit=request.limit,
            user_id=user_id
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
    current_user: Opt[dict] = Depends(get_optional_current_user),  # Optional auth
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
        user_id = current_user.get("user_id") if current_user else None
        result = await service.get_all_packages(
            is_active=is_active,
            destination=destination,
            limit=limit,
            offset=offset,
            user_id=user_id
        )
        return TourPackageListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_tour_packages endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter/by-month", response_model=TourPackageListResponse)
async def filter_tours_by_month(
    month: int = Query(..., ge=1, le=12, description="Tháng (1-12)"),
    year: int = Query(..., ge=2000, description="Năm (ví dụ: 2024)"),
    date_type: str = Query("start_date", description="Loại ngày để lọc: 'start_date' hoặc 'end_date'"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_user: Opt[dict] = Depends(get_optional_current_user),  # Optional auth
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Lọc tour packages theo tháng
    
    Args:
        month: Tháng cần lọc (1-12)
        year: Năm cần lọc
        date_type: Loại ngày để lọc ('start_date' hoặc 'end_date', mặc định: 'start_date')
        is_active: Lọc theo trạng thái hoạt động
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        service: Tour package service instance
        
    Returns:
        TourPackageListResponse với danh sách tour packages
        
    Example:
        GET /api/v1/tour-packages/filter/by-month?month=12&year=2024
        GET /api/v1/tour-packages/filter/by-month?month=1&year=2025&date_type=end_date
    """
    try:
        if date_type not in ['start_date', 'end_date']:
            raise HTTPException(status_code=400, detail="date_type phải là 'start_date' hoặc 'end_date'")
        
        user_id = current_user.get("user_id") if current_user else None
        result = await service.filter_packages_by_month(
            month=month,
            year=year,
            date_type=date_type,
            is_active=is_active,
            limit=limit,
            offset=offset,
            user_id=user_id
        )
        return TourPackageListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in filter_tours_by_month endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter/by-year", response_model=TourPackageListResponse)
async def filter_tours_by_year(
    year: int = Query(..., ge=2000, description="Năm cần lọc (ví dụ: 2024)"),
    date_type: str = Query("start_date", description="Loại ngày để lọc: 'start_date' hoặc 'end_date'"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_user: Opt[dict] = Depends(get_optional_current_user),  # Optional auth
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Lọc tour packages theo năm
    
    Args:
        year: Năm cần lọc
        date_type: Loại ngày để lọc ('start_date' hoặc 'end_date', mặc định: 'start_date')
        is_active: Lọc theo trạng thái hoạt động
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        service: Tour package service instance
        
    Returns:
        TourPackageListResponse với danh sách tour packages
        
    Example:
        GET /api/v1/tour-packages/filter/by-year?year=2024
        GET /api/v1/tour-packages/filter/by-year?year=2025&date_type=end_date
    """
    try:
        if date_type not in ['start_date', 'end_date']:
            raise HTTPException(status_code=400, detail="date_type phải là 'start_date' hoặc 'end_date'")
        
        user_id = current_user.get("user_id") if current_user else None
        result = await service.filter_packages_by_year(
            year=year,
            date_type=date_type,
            is_active=is_active,
            limit=limit,
            offset=offset,
            user_id=user_id
        )
        return TourPackageListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in filter_tours_by_year endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter/by-date", response_model=TourPackageListResponse)
async def filter_tours_by_date(
    start_date: date = Query(..., description="Ngày bắt đầu khoảng lọc (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Ngày kết thúc khoảng lọc (YYYY-MM-DD)"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_user: Opt[dict] = Depends(get_optional_current_user),  # Optional auth
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Lọc tour packages theo khoảng ngày (start_date -> end_date)
    
    Args:
        start_date: Ngày bắt đầu khoảng lọc (YYYY-MM-DD)
        end_date: Ngày kết thúc khoảng lọc (YYYY-MM-DD)
        is_active: Lọc theo trạng thái hoạt động
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        service: Tour package service instance
        
    Returns:
        TourPackageListResponse với danh sách tour packages
        
    Example:
        GET /api/v1/tour-packages/filter/by-date?start_date=2024-12-20&end_date=2024-12-31
    """
    try:
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date phải nhỏ hơn hoặc bằng end_date")
        
        user_id = current_user.get("user_id") if current_user else None
        result = await service.filter_packages_by_date(
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
            limit=limit,
            offset=offset,
            user_id=user_id
        )
        return TourPackageListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in filter_tours_by_date endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter/by-price-range", response_model=TourPackageListResponse)
async def filter_tours_by_price_range(
    min_price: Optional[float] = Query(None, ge=0, description="Giá tối thiểu (VND)"),
    max_price: Optional[float] = Query(None, ge=0, description="Giá tối đa (VND)"),
    price_segment: Optional[str] = Query(None, description="Phân khúc giá: 'budget' (<5M), 'mid' (5M-15M), 'premium' (>15M)"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_user: Opt[dict] = Depends(get_optional_current_user),  # Optional auth
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Lọc tour packages theo phân khúc giá hoặc khoảng giá
    
    Args:
        min_price: Giá tối thiểu (VND)
        max_price: Giá tối đa (VND)
        price_segment: Phân khúc giá nhanh:
            - 'budget': < 5,000,000 VND
            - 'mid': 5,000,000 - 15,000,000 VND
            - 'premium': > 15,000,000 VND
        is_active: Lọc theo trạng thái hoạt động
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        service: Tour package service instance
        
    Returns:
        TourPackageListResponse với danh sách tour packages
        
    Example:
        GET /api/v1/tour-packages/filter/by-price-range?price_segment=budget
        GET /api/v1/tour-packages/filter/by-price-range?min_price=5000000&max_price=15000000
        GET /api/v1/tour-packages/filter/by-price-range?min_price=1000000
    """
    try:
        # Validate price_segment if provided
        valid_segments = ['budget', 'mid', 'premium']
        if price_segment and price_segment not in valid_segments:
            raise HTTPException(
                status_code=400,
                detail=f"price_segment phải là một trong: {', '.join(valid_segments)}"
            )
        
        # If price_segment is provided, set min_price and max_price accordingly
        if price_segment:
            if price_segment == 'budget':
                min_price = None
                max_price = 5000000
            elif price_segment == 'mid':
                min_price = 5000000
                max_price = 15000000
            elif price_segment == 'premium':
                min_price = 15000000
                max_price = None
        
        # Validate that at least one filter is provided
        if min_price is None and max_price is None:
            raise HTTPException(
                status_code=400,
                detail="Phải cung cấp ít nhất một trong: min_price, max_price, hoặc price_segment"
            )
        
        # Validate min_price <= max_price if both are provided
        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(
                status_code=400,
                detail="min_price phải nhỏ hơn hoặc bằng max_price"
            )
        
        user_id = current_user.get("user_id") if current_user else None
        result = await service.filter_packages_by_price_range(
            min_price=min_price,
            max_price=max_price,
            is_active=is_active,
            limit=limit,
            offset=offset,
            user_id=user_id
        )
        return TourPackageListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in filter_tours_by_price_range endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{package_id}", response_model=TourPackageDetailResponse)
async def get_tour_package(
    package_id: UUID,
    current_user: Opt[dict] = Depends(get_optional_current_user),  # Optional auth
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
        user_id = current_user.get("user_id") if current_user else None
        result = await service.get_package_by_id(str(package_id), user_id=user_id)
        
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
    package_name: str = Form(..., description="Tên tour package", example="Tour Đà Lạt 3N2Đ"),
    destination: str = Form(..., description="Điểm đến", example="Đà Lạt"),
    description: str = Form(..., description="Mô tả chi tiết", example="Tour khám phá thành phố ngàn hoa với nhiều điểm tham quan đẹp"),
    duration_days: int = Form(..., description="Số ngày tour (>0)", example=3, gt=0),
    price: float = Form(..., description="Giá tour VNĐ (>0)", example=2500000, gt=0),
    available_slots: int = Form(..., description="Số chỗ còn trống (≥0)", example=20, ge=0),
    start_date: date = Form(..., description="Ngày bắt đầu (YYYY-MM-DD)", example="2024-12-10"),
    end_date: date = Form(..., description="Ngày kết thúc (YYYY-MM-DD)", example="2024-12-13"),
    cuisine: Optional[str] = Form(None, description="Ẩm thực", example="Ẩm thực miền Trung"),
    suitable_for: Optional[str] = Form(None, description="Phù hợp cho", example="Gia đình, Cặp đôi"),
    is_active: bool = Form(True, description="Trạng thái kích hoạt"),
    images: List[UploadFile] = File(..., description="Tour images (max 10 ảnh, định dạng: JPEG/JPG/PNG/WebP)"),
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Tạo mới tour package với upload ảnh trực tiếp lên Cloudinary
    
    Endpoint này tự động:
    - Upload ảnh lên Cloudinary
    - Tạo tour package với URLs từ Cloudinary
    - Rollback nếu có lỗi
    
    Args:
        package_name: Tên gói tour
        destination: Điểm đến
        description: Mô tả chi tiết
        duration_days: Số ngày tour (>0)
        price: Giá tour VNĐ (>0)
        available_slots: Số chỗ còn trống (≥0)
        start_date: Ngày bắt đầu (YYYY-MM-DD)
        end_date: Ngày kết thúc (YYYY-MM-DD)
        cuisine: Ẩm thực (optional)
        suitable_for: Phù hợp cho (optional)
        is_active: Trạng thái kích hoạt
        images: Danh sách file ảnh (tối đa 10 ảnh, định dạng: JPEG/JPG/PNG/WebP)
        service: Tour package service instance
        
    Returns:
        TourPackageCreateResponse với image_urls từ Cloudinary
        
    Example:
        POST /api/v1/tour-packages
        Content-Type: multipart/form-data
        Form Data:
            - package_name: "Tour Đà Lạt 3N2Đ"
            - destination: "Đà Lạt"
            - description: "Tour khám phá thành phố ngàn hoa"
            - duration_days: 3
            - price: 2500000
            - available_slots: 20
            - start_date: "2024-12-01"
            - end_date: "2024-12-03"
            - cuisine: "Ẩm thực miền Trung"
            - suitable_for: "Gia đình, Cặp đôi"
            - is_active: true
            - images: [file1.jpg, file2.jpg, ...]
    """
    try:
        # Validate max 10 images
        if len(images) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 images allowed")
        
        # Validate image types
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        for image in images:
            if image.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type: {image.content_type}. Allowed: jpeg, jpg, png, webp"
                )
        
        # Upload images to Cloudinary
        logger.info(f"Uploading {len(images)} images to Cloudinary...")
        image_urls = await service.upload_images(images)
        
        if not image_urls:
            raise HTTPException(status_code=500, detail="Failed to upload images")
        
        # Prepare package data
        package_data = {
            "package_name": package_name,
            "destination": destination,
            "description": description,
            "duration_days": duration_days,
            "price": price,
            "available_slots": available_slots,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "image_urls": "|".join(image_urls),  # Pipe-separated URLs
            "cuisine": cuisine,
            "suitable_for": suitable_for,
            "is_active": is_active
        }
        
        # Create tour package
        result = await service.create_package(package_data)
        
        if result["EC"] != 0:
            # Rollback: Delete uploaded images
            await service.delete_images_from_urls(package_data["image_urls"])
            raise HTTPException(status_code=400, detail=result["EM"])
        
        logger.info(f"✓ Created tour package with {len(image_urls)} images")
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
    Cập nhật thông tin tour package (JSON)
    
    Args:
        package_id: UUID của tour package cần cập nhật
        package: Dữ liệu cần cập nhật (các trường optional)
        service: Tour package service instance
        
    Returns:
        TourPackageUpdateResponse với thông tin tour package đã cập nhật
        
    Example:
        PUT /api/v1/tour-packages/123e4567-e89b-12d3-a456-426614174000
        Content-Type: application/json
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
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")
        
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


@router.post("/{package_id}/images")
async def manage_tour_images(
    package_id: UUID,
    images: List[UploadFile] = File(..., description="Tour images (max 10 ảnh, định dạng: JPEG/JPG/PNG/WebP)"),
    replace_existing: bool = Query(False, description="True = thay thế ảnh cũ, False = thêm vào ảnh hiện có"),
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Upload/quản lý ảnh cho tour package
    
    Args:
        package_id: UUID của tour package
        images: Danh sách file ảnh cần upload
        replace_existing: True = thay thế ảnh cũ, False = thêm vào ảnh hiện có
        service: Tour package service instance
        
    Returns:
        Dict với danh sách URL ảnh
        
    Example:
        POST /api/v1/tour-packages/123e4567-e89b-12d3-a456-426614174000/images?replace_existing=false
        Content-Type: multipart/form-data
        Files: [image1.jpg, image2.jpg]
    """
    try:
        # Get existing package
        package_result = await service.get_package_by_id(str(package_id))
        if package_result["EC"] != 0:
            raise HTTPException(status_code=404, detail="Tour package not found")
        
        existing_package = package_result["package"]
        
        # Validate max 10 images total
        existing_image_count = 0
        if not replace_existing and existing_package.get("image_urls"):
            existing_image_count = len(existing_package["image_urls"].split("|"))
        
        total_images = existing_image_count + len(images)
        if total_images > 10:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum 10 images allowed. Current: {existing_image_count}, Uploading: {len(images)}"
            )
        
        # Validate image types
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        for image in images:
            if image.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type: {image.content_type}. Allowed: jpeg, jpg, png, webp"
                )
        
        # Upload new images
        logger.info(f"Uploading {len(images)} images to Cloudinary...")
        new_image_urls = await service.upload_images(images)
        
        if not new_image_urls:
            raise HTTPException(status_code=500, detail="Failed to upload images")
        
        # Prepare final image_urls
        if replace_existing:
            # Delete old images from Cloudinary
            if existing_package.get("image_urls"):
                await service.delete_images_from_urls(existing_package["image_urls"])
            final_image_urls = "|".join(new_image_urls)
        else:
            # Append to existing
            existing_urls = existing_package.get("image_urls", "")
            if existing_urls:
                final_image_urls = existing_urls + "|" + "|".join(new_image_urls)
            else:
                final_image_urls = "|".join(new_image_urls)
        
        # Update package with new image_urls
        update_result = await service.update_package(
            str(package_id),
            {"image_urls": final_image_urls}
        )
        
        if update_result["EC"] != 0:
            # Rollback: Delete newly uploaded images
            await service.delete_images_from_urls("|".join(new_image_urls))
            raise HTTPException(status_code=500, detail="Failed to update package with new images")
        
        return {
            "EC": 0,
            "EM": "Images uploaded successfully",
            "image_urls": final_image_urls.split("|"),
            "total_images": len(final_image_urls.split("|"))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error managing tour images: {str(e)}")
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


@router.post("/{package_id}/cancel")
async def cancel_tour_package(
    package_id: UUID,
    reason: Optional[str] = Query(None, description="Lý do hủy tour"),
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Hủy tour package và tất cả bookings liên quan (Admin only)
    
    Khi admin hủy tour:
    1. Set is_active = False
    2. Tự động hủy tất cả bookings có status 'pending' hoặc 'confirmed'
    3. Hoàn trả available_slots cho mỗi booking
    4. Tạo notification cho tất cả users bị ảnh hưởng
    
    Args:
        package_id: UUID của tour package cần hủy
        reason: Lý do hủy tour
        service: Tour package service instance
        
    Returns:
        Dict với số booking đã hủy và số notification đã gửi
        
    Example:
        POST /api/v1/tour-packages/123e4567-e89b-12d3-a456-426614174000/cancel?reason=Thiên tai
    """
    try:
        result = await service.cancel_tour_package(
            package_id=str(package_id),
            reason=reason
        )
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cancel_tour_package endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/csv", response_model=TourPackageBulkCreateResponse, status_code=201)
async def create_tour_packages_from_csv(
    file: UploadFile = File(..., description="CSV file chứa dữ liệu tour packages"),
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Tạo nhiều tour packages từ file CSV
    
    CSV file phải có các cột sau (header):
    - package_name: Tên gói tour (bắt buộc)
    - destination: Điểm đến (bắt buộc)
    - description: Mô tả chi tiết (bắt buộc)
    - duration_days: Số ngày tour (bắt buộc, số nguyên > 0)
    - price: Giá tour (bắt buộc, số thực > 0)
    - available_slots: Số chỗ còn trống (bắt buộc, số nguyên >= 0)
    - start_date: Ngày bắt đầu (bắt buộc, định dạng: YYYY-MM-DD)
    - end_date: Ngày kết thúc (bắt buộc, định dạng: YYYY-MM-DD)
    - image_urls: URL hình ảnh (tùy chọn, phân cách bằng |)
    - cuisine: Ẩm thực (tùy chọn)
    - suitable_for: Phù hợp cho (tùy chọn)
    - is_active: Trạng thái kích hoạt (tùy chọn, true/false, mặc định: true)
    
    Args:
        file: File CSV upload
        service: Tour package service instance
        
    Returns:
        TourPackageBulkCreateResponse với thống kê kết quả
        
    Example:
        POST /api/v1/tour-packages/bulk/csv
        Content-Type: multipart/form-data
        Body: CSV file
    """
    try:
        # Kiểm tra file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File phải có định dạng CSV")
        
        # Đọc nội dung file (ưu tiên UTF-8, fallback nếu file không hợp lệ)
        contents = await file.read()
        try:
            csv_text = contents.decode('utf-8-sig')  # utf-8-sig để xử lý BOM
        except UnicodeDecodeError as decode_err:
            # Một số file CSV có thể ở encoding khác (VD: Windows-1258) hoặc chứa byte lỗi
            logger.warning(f"CSV decode failed with utf-8-sig: {decode_err}. Falling back to tolerant decode.")
            try:
                csv_text = contents.decode('cp1258')  # Thử Windows-1258 phổ biến cho tiếng Việt
            except Exception:
                csv_text = contents.decode('utf-8', errors='replace')  # Cuối cùng: bỏ/replace byte lỗi
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        # Kiểm tra header
        required_fields = [
            'package_name', 'destination', 'description', 'duration_days',
            'price', 'available_slots', 'start_date', 'end_date'
        ]
        
        if not csv_reader.fieldnames:
            raise HTTPException(status_code=400, detail="File CSV không có header")
        
        missing_fields = [field for field in required_fields if field not in csv_reader.fieldnames]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Thiếu các cột bắt buộc: {', '.join(missing_fields)}"
            )
        
        # Parse và validate từng dòng
        packages_data = []
        errors = []
        row_num = 1  # Bắt đầu từ 1 (sau header)
        
        for row in csv_reader:
            row_num += 1
            try:
                # Parse và validate dữ liệu
                package_data = {
                    'package_name': row['package_name'].strip(),
                    'destination': row['destination'].strip(),
                    'description': row['description'].strip(),
                    'duration_days': int(row['duration_days']),
                    'price': float(row['price']),
                    'available_slots': int(row['available_slots']),
                    'start_date': datetime.strptime(row['start_date'].strip(), '%Y-%m-%d').date().isoformat(),
                    'end_date': datetime.strptime(row['end_date'].strip(), '%Y-%m-%d').date().isoformat(),
                }
                
                # Optional fields
                if row.get('image_urls'):
                    package_data['image_urls'] = row['image_urls'].strip()
                
                if row.get('cuisine'):
                    package_data['cuisine'] = row['cuisine'].strip()
                
                if row.get('suitable_for'):
                    package_data['suitable_for'] = row['suitable_for'].strip()
                
                # Parse is_active
                if row.get('is_active'):
                    is_active_str = row['is_active'].strip().lower()
                    package_data['is_active'] = is_active_str in ['true', '1', 'yes', 'y']
                else:
                    package_data['is_active'] = True
                
                # Validation
                if not package_data['package_name']:
                    raise ValueError("package_name không được để trống")
                if not package_data['destination']:
                    raise ValueError("destination không được để trống")
                if not package_data['description']:
                    raise ValueError("description không được để trống")
                if package_data['duration_days'] <= 0:
                    raise ValueError("duration_days phải lớn hơn 0")
                if package_data['price'] <= 0:
                    raise ValueError("price phải lớn hơn 0")
                if package_data['available_slots'] < 0:
                    raise ValueError("available_slots phải lớn hơn hoặc bằng 0")
                
                packages_data.append(package_data)
                
            except ValueError as e:
                errors.append(f"Dòng {row_num}: {str(e)}")
            except Exception as e:
                errors.append(f"Dòng {row_num}: Lỗi parse dữ liệu - {str(e)}")
        
        if not packages_data:
            raise HTTPException(
                status_code=400,
                detail=f"Không có dữ liệu hợp lệ để tạo. Lỗi: {'; '.join(errors)}"
            )
        
        # Tạo packages qua service
        result = await service.create_packages_bulk(packages_data)
        
        # Thêm parsing errors vào kết quả
        if errors:
            result['parsing_errors'] = errors
        
        return TourPackageBulkCreateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_tour_packages_from_csv endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý file CSV: {str(e)}")


