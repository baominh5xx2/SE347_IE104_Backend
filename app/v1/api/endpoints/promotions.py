"""
Promotion API Endpoints
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID

from ...schema.promotion_schema import (
    PromotionCreate,
    PromotionUpdate,
    PromotionListResponse,
    PromotionDetailResponse,
    PromotionCreateResponse,
    PromotionUpdateResponse,
    PromotionDeleteResponse,
    TourPromotionsResponse
)
from ...services.promotion_service import PromotionService
from ...core.supabase import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


def get_promotion_service():
    """Dependency to get PromotionService instance"""
    supabase = get_supabase_client()
    return PromotionService(supabase)


@router.post("/", response_model=PromotionCreateResponse, status_code=201)
async def create_promotion(
    promotion: PromotionCreate,
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Tạo mới một mã khuyến mãi
    
    Mã khuyến mãi (code) sẽ được tự động tạo gồm 8 ký tự ngẫu nhiên (chữ hoa và số)
    
    Example:
        POST /api/v1/promotions
        Body:
        {
            "name": "Sale hè 2024",
            "description": "Giảm giá mùa hè",
            "discount_type": "PERCENTAGE",
            "discount_value": 15,
            "start_date": "2024-06-01T00:00:00",
            "end_date": "2024-08-31T23:59:59",
            "quantity": 100,
            "is_active": true
        }
        
        Response sẽ có thêm trường "code" (VD: "ABC12345")
    """
    try:
        promotion_data = promotion.model_dump()
        result = await service.create_promotion(promotion_data)
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return PromotionCreateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_promotion endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PromotionListResponse)
async def get_promotions(
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Lấy danh sách tất cả mã khuyến mãi
    
    Example:
        GET /api/v1/promotions?is_active=true&limit=10
    """
    try:
        result = await service.get_all_promotions(
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        return PromotionListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_promotions endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter/by-discount", response_model=PromotionListResponse)
async def filter_promotions_by_discount(
    min_discount_value: Optional[float] = Query(None, gt=0, description="Giá trị giảm tối thiểu"),
    max_discount_value: Optional[float] = Query(None, gt=0, description="Giá trị giảm tối đa"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Lọc promotions theo khoảng discount_value.
    Có thể truyền min_discount_value, max_discount_value hoặc cả hai.
    """
    try:
        if min_discount_value is None and max_discount_value is None:
            raise HTTPException(status_code=400, detail="Cần ít nhất một trong min_discount_value hoặc max_discount_value")

        result = await service.filter_promotions_by_discount(
            min_discount_value=min_discount_value,
            max_discount_value=max_discount_value,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        return PromotionListResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in filter_promotions_by_discount endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter/by-date-range", response_model=PromotionListResponse)
async def filter_promotions_by_date_range(
    start_date: Optional[datetime] = Query(None, description="Ngày bắt đầu khoảng lọc (tùy chọn)"),
    end_date: Optional[datetime] = Query(None, description="Ngày kết thúc khoảng lọc (tùy chọn)"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Lọc promotions theo thời gian:
    - Chỉ start_date: lấy những promotion có start_date đúng ngày/giờ đó
    - Chỉ end_date: lấy những promotion có end_date đúng ngày/giờ đó
    - Cả hai: chỉ lấy những promotion có cả start_date VÀ end_date đều đúng ngày/giờ đã truyền
    """
    try:
        if start_date is None and end_date is None:
            raise HTTPException(status_code=400, detail="Cần start_date hoặc end_date")
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date phải nhỏ hơn hoặc bằng end_date")

        result = await service.filter_promotions_by_date_range(
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        return PromotionListResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in filter_promotions_by_date_range endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter/by-quantity", response_model=PromotionListResponse)
async def filter_promotions_by_quantity(
    min_quantity: Optional[int] = Query(None, ge=0, description="Số lượng tối thiểu"),
    max_quantity: Optional[int] = Query(None, ge=0, description="Số lượng tối đa"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Lọc promotions theo khoảng quantity (min-max).
    """
    try:
        if min_quantity is None and max_quantity is None:
            raise HTTPException(status_code=400, detail="Cần ít nhất một trong min_quantity hoặc max_quantity")

        result = await service.filter_promotions_by_quantity(
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        return PromotionListResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in filter_promotions_by_quantity endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter/by-user-count", response_model=PromotionListResponse)
async def filter_promotions_by_user_count(
    min_user_count: Optional[int] = Query(None, ge=0, description="Số lượt sử dụng tối thiểu"),
    max_user_count: Optional[int] = Query(None, ge=0, description="Số lượt sử dụng tối đa"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Lọc promotions theo khoảng user_count (thực tế là trường used_count trong DB).
    """
    try:
        if min_user_count is None and max_user_count is None:
            raise HTTPException(status_code=400, detail="Cần ít nhất một trong min_user_count hoặc max_user_count")

        result = await service.filter_promotions_by_used_count(
            min_user_count=min_user_count,
            max_user_count=max_user_count,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        return PromotionListResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in filter_promotions_by_user_count endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available", response_model=TourPromotionsResponse)
async def get_available_promotions(
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Lấy danh sách tất cả mã khuyến mãi có thể dùng
    Áp dụng cho TẤT CẢ tour
    Chỉ hiện mã còn hạn và còn số lượng (used_count < quantity)
    
    Example:
        GET /api/v1/promotions/available
    """
    try:
        result = await service.get_available_promotions()
        return TourPromotionsResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_available_promotions endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{promotion_id}", response_model=PromotionDetailResponse)
async def get_promotion(
    promotion_id: UUID,
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Lấy thông tin chi tiết một mã khuyến mãi
    
    Example:
        GET /api/v1/promotions/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.get_promotion_by_id(str(promotion_id))
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        
        return PromotionDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_promotion endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code/{code}", response_model=PromotionDetailResponse)
async def get_promotion_by_code(
    code: str,
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Lấy thông tin chi tiết một mã khuyến mãi bằng code
    
    Example:
        GET /api/v1/promotions/code/ABC12345
    """
    try:
        result = await service.get_promotion_by_code(code)
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        
        return PromotionDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_promotion_by_code endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{promotion_id}", response_model=PromotionUpdateResponse)
async def update_promotion(
    promotion_id: UUID,
    promotion: PromotionUpdate,
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Cập nhật thông tin mã khuyến mãi
    
    Example:
        PUT /api/v1/promotions/123e4567-e89b-12d3-a456-426614174000
        Body:
        {
            "discount_value": 20,
            "is_active": false
        }
    """
    try:
        update_data = promotion.model_dump(exclude_unset=True)
        result = await service.update_promotion(str(promotion_id), update_data)
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return PromotionUpdateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_promotion endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{promotion_id}", response_model=PromotionDeleteResponse)
async def delete_promotion(
    promotion_id: UUID,
    service: PromotionService = Depends(get_promotion_service)
):
    """
    Xóa một mã khuyến mãi
    
    Example:
        DELETE /api/v1/promotions/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.delete_promotion(str(promotion_id))
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return PromotionDeleteResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_promotion endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
