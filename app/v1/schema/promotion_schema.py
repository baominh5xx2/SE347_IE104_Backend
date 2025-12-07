"""
Promotion Schema Definitions
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime


class PromotionCreate(BaseModel):
    """Schema for creating a new promotion"""
    name: str = Field(..., description="Tên khuyến mãi (VD: Sale hè 2024)")
    description: Optional[str] = Field(None, description="Mô tả chi tiết khuyến mãi")
    discount_type: Literal["PERCENTAGE", "FIXED_AMOUNT"] = Field(..., description="Loại giảm giá: PERCENTAGE (%) hoặc FIXED_AMOUNT (tiền)")
    discount_value: float = Field(..., gt=0, description="Giá trị giảm (VD: 10 nếu %, 500000 nếu tiền)")
    start_date: datetime = Field(..., description="Ngày bắt đầu áp dụng")
    end_date: datetime = Field(..., description="Ngày hết hạn")
    quantity: int = Field(default=5, ge=1, description="Số lượng mã ban đầu")
    is_active: bool = Field(default=True, description="Trạng thái kích hoạt")
    # code sẽ được tự động tạo bởi service, không cần truyền vào


class PromotionUpdate(BaseModel):
    """Schema for updating a promotion"""
    name: Optional[str] = Field(None, description="Tên khuyến mãi")
    description: Optional[str] = Field(None, description="Mô tả chi tiết")
    discount_type: Optional[Literal["PERCENTAGE", "FIXED_AMOUNT"]] = Field(None, description="Loại giảm giá")
    discount_value: Optional[float] = Field(None, gt=0, description="Giá trị giảm")
    start_date: Optional[datetime] = Field(None, description="Ngày bắt đầu")
    end_date: Optional[datetime] = Field(None, description="Ngày hết hạn")
    quantity: Optional[int] = Field(None, ge=1, description="Số lượng mã")
    is_active: Optional[bool] = Field(None, description="Trạng thái kích hoạt")
    code: Optional[str] = Field(None, description="Mã khuyến mãi (8 ký tự)")


class PromotionResponse(BaseModel):
    """Schema for promotion response"""
    promotion_id: UUID
    name: str
    description: Optional[str]
    discount_type: str
    discount_value: float
    start_date: datetime
    end_date: datetime
    quantity: int
    used_count: int
    is_active: bool
    code: str
    
    class Config:
        from_attributes = True


class PromotionListResponse(BaseModel):
    """Schema for list of promotions"""
    EC: int
    EM: str
    found: int
    promotions: List[PromotionResponse]


class PromotionDetailResponse(BaseModel):
    """Schema for single promotion detail"""
    EC: int
    EM: str
    promotion: Optional[PromotionResponse]


class PromotionCreateResponse(BaseModel):
    """Schema for promotion creation response"""
    EC: int
    EM: str
    promotion: Optional[PromotionResponse]


class PromotionUpdateResponse(BaseModel):
    """Schema for promotion update response"""
    EC: int
    EM: str
    promotion: Optional[PromotionResponse]


class PromotionDeleteResponse(BaseModel):
    """Schema for promotion deletion response"""
    EC: int
    EM: str


class TourPromotionLinkRequest(BaseModel):
    """Schema for linking promotion to tour"""
    package_id: UUID = Field(..., description="ID của tour package")
    promotion_id: UUID = Field(..., description="ID của promotion")


class TourPromotionUnlinkRequest(BaseModel):
    """Schema for unlinking promotion from tour"""
    package_id: UUID = Field(..., description="ID của tour package")
    promotion_id: UUID = Field(..., description="ID của promotion")


class TourPromotionLinkResponse(BaseModel):
    """Schema for tour-promotion link response"""
    EC: int
    EM: str
    link_id: Optional[UUID]


class TourPromotionUnlinkResponse(BaseModel):
    """Schema for tour-promotion unlink response"""
    EC: int
    EM: str


class TourPromotionsResponse(BaseModel):
    """Schema for getting promotions of a tour"""
    EC: int
    EM: str
    found: int
    promotions: List[PromotionResponse]
