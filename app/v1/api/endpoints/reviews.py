"""
Review API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID

from ...schema.review_schema import (
    ReviewCreate,
    ReviewUpdate,
    ReviewListResponse,
    ReviewDetailResponseWrapper,
    ReviewCreateResponse,
    ReviewUpdateResponse,
    ReviewDeleteResponse,
    ReviewStatsResponse,
    ReviewApproveRequest,
    ReviewApproveResponse
)
from ...services.review_service import ReviewService
from ...services.booking_management_service import BookingManagementService
from ...core.supabase import get_supabase_client
from ...core.dependencies import get_current_user, get_current_admin
from ...schema.booking_schema import MyBookingListResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_review_service():
    """Dependency to get ReviewService instance"""
    supabase = get_supabase_client()
    return ReviewService(supabase)


def get_booking_management_service():
    """Dependency to get BookingManagementService instance"""
    supabase = get_supabase_client()
    return BookingManagementService(supabase)


@router.get("", response_model=ReviewListResponse)
@router.get("/", response_model=ReviewListResponse)
async def get_reviews(
    package_id: Optional[str] = Query(None, description="Lọc theo package ID"),
    user_id: Optional[str] = Query(None, description="Lọc theo user ID"),
    is_approved: Optional[bool] = Query(None, description="Lọc theo trạng thái phê duyệt"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Lọc theo rating (1-5)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    service: ReviewService = Depends(get_review_service)
):
    """
    Lấy danh sách reviews
    
    Args:
        package_id: Lọc theo package ID
        user_id: Lọc theo user ID
        is_approved: Lọc theo trạng thái phê duyệt
        rating: Lọc theo rating (1-5)
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        service: Review service instance
        
    Returns:
        ReviewListResponse với danh sách reviews
        
    Example:
        GET /api/v1/reviews?package_id=07e8c89e-90d4-4ebc-9302-384dc6cb2f0c
        GET /api/v1/reviews?user_id=bcde5ff1-5fd7-49e0-8790-05463092d54e&is_approved=true
    """
    try:
        result = await service.get_all_reviews(
            package_id=package_id,
            user_id=user_id,
            is_approved=is_approved,
            rating=rating,
            limit=limit,
            offset=offset
        )
        return ReviewListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_reviews endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-reviews", response_model=ReviewListResponse)
async def get_my_reviews(
    current_user: dict = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Lấy danh sách reviews của user hiện tại (yêu cầu authentication)
    
    Args:
        current_user: User hiện tại (từ authentication)
        service: Review service instance
        
    Returns:
        ReviewListResponse với danh sách reviews của user
        
    Example:
        GET /api/v1/reviews/my-reviews
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        result = await service.get_all_reviews(user_id=str(user_id))
        return ReviewListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_my_reviews endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-reviewable-bookings", response_model=MyBookingListResponse)
async def get_my_reviewable_bookings(
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_user: dict = Depends(get_current_user),
    service: BookingManagementService = Depends(get_booking_management_service),
):
    """Lấy danh sách bookings của user hiện tại có status='completed' để có thể review."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        result = await service.get_user_bookings(
            user_id=str(user_id),
            status="completed",
            limit=limit,
            offset=offset,
        )
        return MyBookingListResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_my_reviewable_bookings endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/package/{package_id}", response_model=ReviewListResponse)
async def get_reviews_by_package(
    package_id: UUID,
    is_approved: bool = Query(True, description="Chỉ lấy reviews đã được phê duyệt"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    service: ReviewService = Depends(get_review_service)
):
    """
    Lấy danh sách reviews cho một package cụ thể
    
    Args:
        package_id: UUID của package
        is_approved: Chỉ lấy reviews đã được phê duyệt (mặc định: True)
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        service: Review service instance
        
    Returns:
        ReviewListResponse với danh sách reviews
        
    Example:
        GET /api/v1/reviews/package/07e8c89e-90d4-4ebc-9302-384dc6cb2f0c
    """
    try:
        result = await service.get_reviews_by_package(
            package_id=str(package_id),
            is_approved=is_approved,
            limit=limit,
            offset=offset
        )
        return ReviewListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_reviews_by_package endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/package/{package_id}/stats", response_model=ReviewStatsResponse)
async def get_review_stats(
    package_id: UUID,
    service: ReviewService = Depends(get_review_service)
):
    """
    Lấy thống kê reviews cho một package
    
    Args:
        package_id: UUID của package
        service: Review service instance
        
    Returns:
        ReviewStatsResponse với thống kê (tổng số reviews, rating trung bình, phân bố rating)
        
    Example:
        GET /api/v1/reviews/package/07e8c89e-90d4-4ebc-9302-384dc6cb2f0c/stats
    """
    try:
        result = await service.get_review_stats(str(package_id))
        return ReviewStatsResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_review_stats endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{review_id}", response_model=ReviewDetailResponseWrapper)
async def get_review(
    review_id: UUID,
    service: ReviewService = Depends(get_review_service)
):
    """
    Lấy thông tin chi tiết một review (bao gồm thông tin user và package)
    
    Args:
        review_id: UUID của review
        service: Review service instance
        
    Returns:
        ReviewDetailResponseWrapper với thông tin chi tiết review
        
    Example:
        GET /api/v1/reviews/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.get_review_detail(str(review_id))
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        
        return ReviewDetailResponseWrapper(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_review endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ReviewCreateResponse, status_code=201)
async def create_review(
    review: ReviewCreate,
    current_user: dict = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Tạo review mới (yêu cầu authentication)
    
    Args:
        review: Dữ liệu review (booking_id, package_id, rating, comment)
        current_user: User hiện tại (từ authentication)
        service: Review service instance
        
    Returns:
        ReviewCreateResponse với thông tin review vừa tạo
        
    Example:
        POST /api/v1/reviews
        Body: {
            "booking_id": "uuid",
            "package_id": "uuid",
            "rating": 5,
            "comment": "Tour rất tuyệt vời!"
        }
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        review_data = review.model_dump()
        result = await service.create_review(review_data, str(user_id))
        
        if result["EC"] != 0:
            status_code = 400
            if result["EC"] == 1:
                status_code = 404
            elif result["EC"] == 2 or result["EC"] == 3:
                status_code = 403
            raise HTTPException(status_code=status_code, detail=result["EM"])
        
        return ReviewCreateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_review endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{review_id}", response_model=ReviewUpdateResponse)
async def update_review(
    review_id: UUID,
    review: ReviewUpdate,
    current_user: dict = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Cập nhật review (chỉ owner hoặc admin)
    
    Args:
        review_id: UUID của review cần cập nhật
        review: Dữ liệu cập nhật (rating, comment, is_approved)
        current_user: User hiện tại (từ authentication)
        service: Review service instance
        
    Returns:
        ReviewUpdateResponse với thông tin review sau khi cập nhật
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        # Check if user is admin
        user_role = current_user.get("role", "user")
        is_admin = user_role == "admin"
        
        update_data = review.model_dump(exclude_unset=True)
        result = await service.update_review(
            str(review_id), 
            update_data, 
            str(user_id),
            is_admin=is_admin
        )
        
        if result["EC"] != 0:
            status_code = 400
            if result["EC"] == 1 or result["EC"] == 2:
                status_code = 403
            raise HTTPException(status_code=status_code, detail=result["EM"])
        
        return ReviewUpdateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_review endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{review_id}", response_model=ReviewDeleteResponse)
async def delete_review(
    review_id: UUID,
    current_user: dict = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Xóa một review (chỉ owner hoặc admin)
    
    Args:
        review_id: UUID của review cần xóa
        current_user: User hiện tại (từ authentication)
        service: Review service instance
        
    Returns:
        ReviewDeleteResponse với kết quả xóa
        
    Example:
        DELETE /api/v1/reviews/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        # Check if user is admin
        user_role = current_user.get("role", "user")
        is_admin = user_role == "admin"
        
        result = await service.delete_review(
            str(review_id),
            str(user_id),
            is_admin=is_admin
        )
        
        if result["EC"] != 0:
            status_code = 400
            if result["EC"] == 1 or result["EC"] == 2:
                status_code = 403
            raise HTTPException(status_code=status_code, detail=result["EM"])
        
        return ReviewDeleteResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_review endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Admin Endpoints
# ============================================

@router.get("/admin/pending", response_model=ReviewListResponse)
async def get_pending_reviews(
    package_id: Optional[str] = Query(None, description="Lọc theo package ID"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_admin: dict = Depends(get_current_admin),
    service: ReviewService = Depends(get_review_service)
):
    """
    Admin: Lấy danh sách reviews chờ phê duyệt (is_approved = False)
    
    Args:
        package_id: Lọc theo package ID
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        current_admin: Current authenticated admin (từ token)
        service: Review service instance
        
    Returns:
        ReviewListResponse với danh sách reviews chờ phê duyệt
        
    Example:
        GET /api/v1/reviews/admin/pending
        GET /api/v1/reviews/admin/pending?package_id=07e8c89e-90d4-4ebc-9302-384dc6cb2f0c
    """
    try:
        result = await service.get_all_reviews(
            package_id=package_id,
            is_approved=False,  # Only pending reviews
            limit=limit,
            offset=offset
        )
        return ReviewListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_pending_reviews endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/{review_id}/approve", response_model=ReviewApproveResponse)
async def approve_review(
    review_id: UUID,
    request: ReviewApproveRequest,
    current_admin: dict = Depends(get_current_admin),
    service: ReviewService = Depends(get_review_service)
):
    """
    Admin: Phê duyệt hoặc từ chối một review
    
    Args:
        review_id: UUID của review cần phê duyệt
        request: ReviewApproveRequest với is_approved (True = approve, False = reject)
        current_admin: Current authenticated admin (từ token)
        service: Review service instance
        
    Returns:
        ReviewApproveResponse với thông tin review sau khi cập nhật
        
    Example:
        PUT /api/v1/reviews/admin/123e4567-e89b-12d3-a456-426614174000/approve
        Body: {
            "is_approved": true
        }
    """
    try:
        update_data = {"is_approved": request.is_approved}
        result = await service.update_review(
            str(review_id),
            update_data,
            user_id=None,  # Admin can update any review
            is_admin=True
        )
        
        if result["EC"] != 0:
            status_code = 400
            if result["EC"] == 1:
                status_code = 404
            raise HTTPException(status_code=status_code, detail=result["EM"])
        
        return ReviewApproveResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in approve_review endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/all", response_model=ReviewListResponse)
async def get_all_reviews_admin(
    package_id: Optional[str] = Query(None, description="Lọc theo package ID"),
    user_id: Optional[str] = Query(None, description="Lọc theo user ID"),
    is_approved: Optional[bool] = Query(None, description="Lọc theo trạng thái phê duyệt"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Lọc theo rating (1-5)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    current_admin: dict = Depends(get_current_admin),
    service: ReviewService = Depends(get_review_service)
):
    """
    Admin: Lấy tất cả reviews trong hệ thống (bao gồm cả chưa phê duyệt)
    
    Args:
        package_id: Lọc theo package ID
        user_id: Lọc theo user ID
        is_approved: Lọc theo trạng thái phê duyệt
        rating: Lọc theo rating (1-5)
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        current_admin: Current authenticated admin (từ token)
        service: Review service instance
        
    Returns:
        ReviewListResponse với danh sách reviews
        
    Example:
        GET /api/v1/reviews/admin/all
        GET /api/v1/reviews/admin/all?is_approved=false
    """
    try:
        result = await service.get_all_reviews(
            package_id=package_id,
            user_id=user_id,
            is_approved=is_approved,
            rating=rating,
            limit=limit,
            offset=offset
        )
        return ReviewListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_all_reviews_admin endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
