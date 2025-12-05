"""
Promotion API Endpoints
"""
import logging
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
