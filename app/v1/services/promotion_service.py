"""
Promotion Service
Handles all promotion-related business logic
"""
import logging
import random
import string
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from supabase import Client

logger = logging.getLogger(__name__)


class PromotionService:
    """Service for managing promotions and tour-promotion relationships"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    def _generate_promotion_code(self) -> str:
        """
        Tạo mã khuyến mãi ngẫu nhiên 8 ký tự (chữ và số)
        
        Returns:
            str: Mã khuyến mãi 8 ký tự
        """
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choice(characters) for _ in range(8))
    
    async def create_promotion(self, promotion_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tạo mới một promotion
        
        Args:
            promotion_data: Dict chứa thông tin promotion
            
        Returns:
            Dict với EC, EM và promotion data
        """
        try:
            # Convert datetime to ISO format strings
            if isinstance(promotion_data.get('start_date'), datetime):
                promotion_data['start_date'] = promotion_data['start_date'].isoformat()
            if isinstance(promotion_data.get('end_date'), datetime):
                promotion_data['end_date'] = promotion_data['end_date'].isoformat()
            
            # Set default values
            if 'used_count' not in promotion_data:
                promotion_data['used_count'] = 0
            
            # Tạo mã khuyến mãi tự động
            if 'code' not in promotion_data or not promotion_data['code']:
                promotion_data['code'] = self._generate_promotion_code()
            
            # Insert into database
            result = self.supabase.table('promotions').insert(promotion_data).execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Failed to create promotion",
                    "promotion": None
                }
            
            logger.info(f"Created promotion: {result.data[0]['promotion_id']}")
            return {
                "EC": 0,
                "EM": "Promotion created successfully",
                "promotion": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error creating promotion: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error creating promotion: {str(e)}",
                "promotion": None
            }
    
    async def get_promotion_by_id(self, promotion_id: str) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết một promotion
        
        Args:
            promotion_id: UUID của promotion
            
        Returns:
            Dict với EC, EM và promotion data
        """
        try:
            result = self.supabase.table('promotions')\
                .select('*')\
                .eq('promotion_id', promotion_id)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": f"Promotion not found: {promotion_id}",
                    "promotion": None
                }
            
            return {
                "EC": 0,
                "EM": "Promotion found",
                "promotion": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting promotion: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error getting promotion: {str(e)}",
                "promotion": None
            }
    
    async def get_promotion_by_code(self, code: str) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết một promotion bằng code
        
        Args:
            code: Mã khuyến mãi (8 ký tự)
            
        Returns:
            Dict với EC, EM và promotion data
        """
        try:
            result = self.supabase.table('promotions')\
                .select('*')\
                .eq('code', code)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": f"Promotion not found with code: {code}",
                    "promotion": None
                }
            
            return {
                "EC": 0,
                "EM": "Promotion found",
                "promotion": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting promotion by code: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error getting promotion: {str(e)}",
                "promotion": None
            }
    
    async def get_all_promotions(
        self,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lấy danh sách tất cả promotions
        
        Args:
            is_active: Lọc theo trạng thái
            limit: Giới hạn số lượng
            offset: Bỏ qua số lượng
            
        Returns:
            Dict với EC, EM, found và danh sách promotions
        """
        try:
            query = self.supabase.table('promotions').select('*')
            
            # Apply filters
            if is_active is not None:
                query = query.eq('is_active', is_active)
            
            # Apply pagination
            if offset is not None:
                query = query.range(offset, offset + (limit or 100) - 1)
            elif limit is not None:
                query = query.limit(limit)
            
            result = query.execute()
            
            return {
                "EC": 0,
                "EM": "Promotions retrieved successfully",
                "found": len(result.data),
                "promotions": result.data
            }
            
        except Exception as e:
            logger.error(f"Error getting promotions: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error getting promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }
    
    async def filter_promotions_by_discount(
        self,
        min_discount_value: Optional[float] = None,
        max_discount_value: Optional[float] = None,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lọc promotions theo khoảng discount_value
        """
        try:
            query = self.supabase.table('promotions').select('*')

            if min_discount_value is not None:
                query = query.gte('discount_value', min_discount_value)
            if max_discount_value is not None:
                query = query.lte('discount_value', max_discount_value)

            if is_active is not None:
                query = query.eq('is_active', is_active)

            if offset is not None:
                query = query.range(offset, offset + (limit or 100) - 1)
            elif limit is not None:
                query = query.limit(limit)

            result = query.execute()

            return {
                "EC": 0,
                "EM": "Promotions filtered by discount_value successfully",
                "found": len(result.data),
                "promotions": result.data
            }

        except Exception as e:
            logger.error(f"Error filtering promotions by discount_value: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error filtering promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }

    async def filter_promotions_by_date_range(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Filter promotions by date, comparing ONLY the calendar date (YYYY-MM-DD),
        ignoring time and timezone, implemented via half-open day ranges:
        - Only start_date: start_date in [start_date 00:00, start_date+1 00:00)
        - Only end_date: end_date in [end_date 00:00, end_date+1 00:00)
        - Both: intersection of both conditions
        """
        try:
            query = self.supabase.table('promotions').select('*')

            # Build day-range boundaries as ISO strings (Postgres will cast to timestamp)
            if start_date is not None:
                start_day = start_date.date()
                start_lower = start_day.isoformat()  # YYYY-MM-DD 00:00 implicit
                # next day for upper bound (exclusive)
                from datetime import timedelta
                start_upper = (start_day + timedelta(days=1)).isoformat()
            else:
                start_lower = start_upper = None

            if end_date is not None:
                end_day = end_date.date()
                end_lower = end_day.isoformat()
                from datetime import timedelta
                end_upper = (end_day + timedelta(days=1)).isoformat()
            else:
                end_lower = end_upper = None

            # Only start_date: match records whose start_date is within that day
            if start_lower is not None and end_lower is None:
                query = query.gte('start_date', start_lower).lt('start_date', start_upper)
            # Only end_date: match records whose end_date is within that day
            elif end_lower is not None and start_lower is None:
                query = query.gte('end_date', end_lower).lt('end_date', end_upper)
            # Both: require both dates to fall on the specified days
            elif start_lower is not None and end_lower is not None:
                query = query.gte('start_date', start_lower).lt('start_date', start_upper)
                query = query.gte('end_date', end_lower).lt('end_date', end_upper)

            if is_active is not None:
                query = query.eq('is_active', is_active)

            if offset is not None:
                query = query.range(offset, offset + (limit or 100) - 1)
            elif limit is not None:
                query = query.limit(limit)

            result = query.execute()

            return {
                "EC": 0,
                "EM": "Promotions filtered by date range successfully",
                "found": len(result.data),
                "promotions": result.data
            }

        except Exception as e:
            logger.error(f"Error filtering promotions by date range: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error filtering promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }

    async def filter_promotions_by_quantity(
        self,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lọc promotions theo khoảng quantity
        """
        try:
            query = self.supabase.table('promotions').select('*')

            if min_quantity is not None:
                query = query.gte('quantity', min_quantity)
            if max_quantity is not None:
                query = query.lte('quantity', max_quantity)

            if is_active is not None:
                query = query.eq('is_active', is_active)

            if offset is not None:
                query = query.range(offset, offset + (limit or 100) - 1)
            elif limit is not None:
                query = query.limit(limit)

            result = query.execute()

            return {
                "EC": 0,
                "EM": "Promotions filtered by quantity successfully",
                "found": len(result.data),
                "promotions": result.data
            }

        except Exception as e:
            logger.error(f"Error filtering promotions by quantity: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error filtering promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }

    async def filter_promotions_by_used_count(
        self,
        min_user_count: Optional[int] = None,
        max_user_count: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lọc promotions theo khoảng used_count (user_count)
        """
        try:
            query = self.supabase.table('promotions').select('*')

            if min_user_count is not None:
                query = query.gte('used_count', min_user_count)
            if max_user_count is not None:
                query = query.lte('used_count', max_user_count)

            if is_active is not None:
                query = query.eq('is_active', is_active)

            if offset is not None:
                query = query.range(offset, offset + (limit or 100) - 1)
            elif limit is not None:
                query = query.limit(limit)

            result = query.execute()

            return {
                "EC": 0,
                "EM": "Promotions filtered by user_count successfully",
                "found": len(result.data),
                "promotions": result.data
            }

        except Exception as e:
            logger.error(f"Error filtering promotions by user_count: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error filtering promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }
    
    async def update_promotion(self, promotion_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cập nhật thông tin promotion
        
        Args:
            promotion_id: UUID của promotion
            update_data: Dict chứa dữ liệu cần update
            
        Returns:
            Dict với EC, EM và promotion data
        """
        try:
            # Convert datetime to ISO format strings
            if isinstance(update_data.get('start_date'), datetime):
                update_data['start_date'] = update_data['start_date'].isoformat()
            if isinstance(update_data.get('end_date'), datetime):
                update_data['end_date'] = update_data['end_date'].isoformat()
            
            # Update database
            result = self.supabase.table('promotions')\
                .update(update_data)\
                .eq('promotion_id', promotion_id)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": f"Promotion not found: {promotion_id}",
                    "promotion": None
                }
            
            logger.info(f"Updated promotion: {promotion_id}")
            return {
                "EC": 0,
                "EM": "Promotion updated successfully",
                "promotion": result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error updating promotion: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error updating promotion: {str(e)}",
                "promotion": None
            }
    
    async def delete_promotion(self, promotion_id: str) -> Dict[str, Any]:
        """
        Xóa một promotion
        
        Args:
            promotion_id: UUID của promotion
            
        Returns:
            Dict với EC và EM
        """
        try:
            result = self.supabase.table('promotions')\
                .delete()\
                .eq('promotion_id', promotion_id)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": f"Promotion not found: {promotion_id}"
                }
            
            logger.info(f"Deleted promotion: {promotion_id}")
            return {
                "EC": 0,
                "EM": "Promotion deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting promotion: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error deleting promotion: {str(e)}"
            }
    
    async def get_available_promotions(self) -> Dict[str, Any]:
        """
        Lấy tất cả mã khuyến mãi còn hạn và còn số lượng
        Áp dụng cho TẤT CẢ tour
        
        Returns:
            Dict với EC, EM, found và danh sách promotions
        """
        try:
            # Get current time
            now = datetime.now()
            
            # Query all promotions
            result = self.supabase.table('promotions')\
                .select('*')\
                .eq('is_active', True)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 0,
                    "EM": "No promotions available",
                    "found": 0,
                    "promotions": []
                }
            
            # Filter promotions: còn hạn, còn số lượng
            valid_promotions = []
            for promo in result.data:
                try:
                    # Parse dates from database (remove timezone info for comparison)
                    start_date = datetime.fromisoformat(promo['start_date'].replace('Z', '+00:00')).replace(tzinfo=None)
                    end_date = datetime.fromisoformat(promo['end_date'].replace('Z', '+00:00')).replace(tzinfo=None)
                    
                    # Check if still valid
                    is_valid_time = start_date <= now <= end_date
                    has_quantity = promo['used_count'] < promo['quantity']
                    
                    if is_valid_time and has_quantity:
                        valid_promotions.append(promo)
                except Exception as date_error:
                    logger.warning(f"Error parsing dates for promotion {promo.get('promotion_id')}: {str(date_error)}")
                    continue
            
            return {
                "EC": 0,
                "EM": "Promotions retrieved successfully",
                "found": len(valid_promotions),
                "promotions": valid_promotions
            }
            
        except Exception as e:
            logger.error(f"Error getting available promotions: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error getting promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }
    
    async def apply_promotion_to_booking(
        self,
        promotion_id: str,
        original_price: float
    ) -> Dict[str, Any]:
        """
        Áp dụng mã khuyến mãi: tính giá sau giảm và tăng used_count
        
        Args:
            promotion_id: UUID của promotion
            original_price: Giá gốc
            
        Returns:
            Dict với EC, EM, final_price và discount_amount
        """
        try:
            # Get promotion details
            promo_result = await self.get_promotion_by_id(promotion_id)
            if promo_result['EC'] != 0:
                return {
                    "EC": 1,
                    "EM": "Promotion not found",
                    "final_price": original_price,
                    "discount_amount": 0
                }
            
            promo = promo_result['promotion']
            
            # Validate promotion
            now = datetime.now()
            # Parse dates and remove timezone for comparison
            start_date = datetime.fromisoformat(promo['start_date'].replace('Z', '+00:00')).replace(tzinfo=None)
            end_date = datetime.fromisoformat(promo['end_date'].replace('Z', '+00:00')).replace(tzinfo=None)
            
            # Check if promotion is still valid
            if not (start_date <= now <= end_date):
                return {
                    "EC": 1,
                    "EM": "Promotion has expired or not started yet",
                    "final_price": original_price,
                    "discount_amount": 0
                }
            
            # Check if promotion is active
            if not promo.get('is_active', False):
                return {
                    "EC": 1,
                    "EM": "Promotion is not active",
                    "final_price": original_price,
                    "discount_amount": 0
                }
            
            # Check if promotion has available quantity
            if promo['used_count'] >= promo['quantity']:
                return {
                    "EC": 1,
                    "EM": "Promotion has reached its usage limit",
                    "final_price": original_price,
                    "discount_amount": 0
                }
            
            # Calculate discount
            discount_amount = 0
            if promo['discount_type'] == 'PERCENTAGE':
                discount_amount = original_price * (promo['discount_value'] / 100)
            elif promo['discount_type'] == 'FIXED_AMOUNT':
                discount_amount = promo['discount_value']
            
            # Ensure discount doesn't exceed original price
            discount_amount = min(discount_amount, original_price)
            final_price = original_price - discount_amount
            
            # Increment used_count
            new_used_count = promo['used_count'] + 1
            update_result = self.supabase.table('promotions')\
                .update({'used_count': new_used_count})\
                .eq('promotion_id', promotion_id)\
                .execute()
            
            if not update_result.data:
                logger.error(f"Failed to increment used_count for promotion {promotion_id}")
            
            logger.info(f"Applied promotion {promotion_id}: {original_price} -> {final_price} (discount: {discount_amount})")
            return {
                "EC": 0,
                "EM": "Promotion applied successfully",
                "final_price": final_price,
                "discount_amount": discount_amount
            }
            
        except Exception as e:
            logger.error(f"Error applying promotion: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error applying promotion: {str(e)}",
                "final_price": original_price,
                "discount_amount": 0
            }
