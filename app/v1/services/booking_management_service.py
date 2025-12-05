"""
Booking Management Service
Service cho UC-USER-03: Quản lý Tour Đã Đăng Ký
"""
import logging
from typing import Optional, Dict, Any
from supabase import Client

logger = logging.getLogger(__name__)


class BookingManagementService:
    """Service for managing user bookings with tour package information"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize BookingManagementService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    async def get_user_bookings(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lấy danh sách bookings của user với thông tin tour package
        
        Args:
            user_id: ID của user
            status: Filter theo trạng thái (pending/confirmed/cancelled/completed)
            limit: Maximum number of results
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            # Join với tour_packages để lấy thông tin tour
            query = self.supabase.table('bookings')\
                .select('booking_id, number_of_people, total_amount, status, created_at, tour_packages(package_name, destination, start_date, end_date)', count='exact')\
                .eq('user_id', user_id)
            
            # Apply status filter
            if status:
                query = query.eq('status', status)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            # Order by created_at descending
            query = query.order('created_at', desc=True)
            
            result = query.execute()
            
            # Format response data
            formatted_data = []
            for booking in result.data:
                tour_pkg = booking.get('tour_packages', {})
                # Handle case where tour_packages might be a list or dict
                if isinstance(tour_pkg, list) and tour_pkg:
                    tour_pkg = tour_pkg[0]
                elif not isinstance(tour_pkg, dict):
                    tour_pkg = {}
                
                formatted_data.append({
                    "booking_id": booking['booking_id'],
                    "tour_name": tour_pkg.get('package_name', 'Unknown Tour'),
                    "destination": tour_pkg.get('destination', 'Unknown'),
                    "start_date": tour_pkg.get('start_date'),
                    "end_date": tour_pkg.get('end_date'),
                    "number_of_people": booking['number_of_people'],
                    "total_amount": float(booking['total_amount']),
                    "status": booking['status'],
                    "created_at": booking['created_at']
                })
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": formatted_data,
                "total": result.count
            }
            
        except Exception as e:
            logger.error(f"Error getting user bookings: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving bookings: {str(e)}",
                "data": None,
                "total": 0
            }
    
    async def get_user_booking_detail(
        self,
        booking_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Lấy chi tiết booking của user với đầy đủ thông tin tour package
        
        Args:
            booking_id: UUID của booking
            user_id: ID của user (để verify ownership)
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            # Join với tour_packages để lấy đầy đủ thông tin tour
            result = self.supabase.table('bookings')\
                .select('*, tour_packages(*)', count='exact')\
                .eq('booking_id', booking_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Booking not found or access denied",
                    "data": None
                }
            
            booking = result.data[0]
            tour_pkg = booking.get('tour_packages', {})
            # Handle case where tour_packages might be a list or dict
            if isinstance(tour_pkg, list) and tour_pkg:
                tour_pkg = tour_pkg[0]
            elif not isinstance(tour_pkg, dict):
                tour_pkg = {}
            
            # Format tour package info
            tour_package_info = None
            if tour_pkg:
                tour_package_info = {
                    "package_id": tour_pkg.get('package_id'),
                    "package_name": tour_pkg.get('package_name'),
                    "destination": tour_pkg.get('destination'),
                    "description": tour_pkg.get('description'),
                    "duration_days": tour_pkg.get('duration_days'),
                    "start_date": tour_pkg.get('start_date'),
                    "end_date": tour_pkg.get('end_date'),
                    "price": float(tour_pkg.get('price', 0)),
                    "image_urls": tour_pkg.get('image_urls')
                }
            
            # Format booking detail
            formatted_data = {
                "booking_id": booking['booking_id'],
                "status": booking['status'],
                "number_of_people": booking['number_of_people'],
                "total_amount": float(booking['total_amount']),
                "contact_name": booking['contact_name'],
                "contact_phone": booking['contact_phone'],
                "special_requests": booking.get('special_requests'),
                "created_at": booking['created_at'],
                "updated_at": booking['updated_at'],
                "tour_package": tour_package_info
            }
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": formatted_data
            }
            
        except Exception as e:
            logger.error(f"Error getting booking detail {booking_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving booking: {str(e)}",
                "data": None
            }
    
    async def get_all_bookings_admin(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Admin: Lấy tất cả bookings trong hệ thống với thông tin user và tour
        
        Args:
            status: Filter theo trạng thái
            limit: Maximum number of results
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            # Join với tour_packages và users để lấy đầy đủ thông tin
            # Note: Supabase join syntax requires foreign key relationship
            query = self.supabase.table('bookings')\
                .select('booking_id, user_id, number_of_people, total_amount, status, created_at, tour_packages(package_name, destination, start_date)', count='exact')
            
            # Apply status filter
            if status:
                query = query.eq('status', status)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            # Order by created_at descending
            query = query.order('created_at', desc=True)
            
            result = query.execute()
            
            # Format response data
            formatted_data = []
            for booking in result.data:
                tour_pkg = booking.get('tour_packages', {})
                if isinstance(tour_pkg, list) and tour_pkg:
                    tour_pkg = tour_pkg[0]
                elif not isinstance(tour_pkg, dict):
                    tour_pkg = {}
                
                # Get user info separately if needed
                user_id = booking.get('user_id')
                user_email = None
                user_full_name = None
                if user_id:
                    try:
                        user_result = self.supabase.table('users')\
                            .select('email, full_name')\
                            .eq('user_id', user_id)\
                            .execute()
                        if user_result.data:
                            user_info = user_result.data[0]
                            user_email = user_info.get('email')
                            user_full_name = user_info.get('full_name')
                    except Exception as e:
                        logger.warning(f"Could not fetch user info for {user_id}: {str(e)}")
                
                formatted_data.append({
                    "booking_id": booking['booking_id'],
                    "user_id": user_id,
                    "user_email": user_email,
                    "user_full_name": user_full_name,
                    "tour_name": tour_pkg.get('package_name', 'Unknown Tour'),
                    "destination": tour_pkg.get('destination', 'Unknown'),
                    "start_date": tour_pkg.get('start_date'),
                    "number_of_people": booking['number_of_people'],
                    "total_amount": float(booking['total_amount']),
                    "status": booking['status'],
                    "created_at": booking['created_at']
                })
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": formatted_data,
                "total": result.count
            }
            
        except Exception as e:
            logger.error(f"Error getting all bookings admin: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving bookings: {str(e)}",
                "data": None,
                "total": 0
            }
    
    async def get_user_bookings_admin(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Admin: Lấy tất cả bookings của 1 user cụ thể
        
        Args:
            user_id: ID của user cần xem
            status: Filter theo trạng thái
            limit: Maximum number of results
            offset: Number of records to skip
            
        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            # Join với tour_packages để lấy thông tin tour
            query = self.supabase.table('bookings')\
                .select('booking_id, number_of_people, total_amount, status, created_at, tour_packages(package_name, destination, start_date)', count='exact')\
                .eq('user_id', user_id)
            
            # Apply status filter
            if status:
                query = query.eq('status', status)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            # Order by created_at descending
            query = query.order('created_at', desc=True)
            
            result = query.execute()
            
            # Format response data
            formatted_data = []
            for booking in result.data:
                tour_pkg = booking.get('tour_packages', {})
                if isinstance(tour_pkg, list) and tour_pkg:
                    tour_pkg = tour_pkg[0]
                elif not isinstance(tour_pkg, dict):
                    tour_pkg = {}
                
                formatted_data.append({
                    "booking_id": booking['booking_id'],
                    "user_id": user_id,  # Include user_id for admin
                    "tour_name": tour_pkg.get('package_name', 'Unknown Tour'),
                    "destination": tour_pkg.get('destination', 'Unknown'),
                    "start_date": tour_pkg.get('start_date'),
                    "number_of_people": booking['number_of_people'],
                    "total_amount": float(booking['total_amount']),
                    "status": booking['status'],
                    "created_at": booking['created_at']
                })
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": formatted_data,
                "total": result.count
            }
            
        except Exception as e:
            logger.error(f"Error getting user bookings admin: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving bookings: {str(e)}",
                "data": None,
                "total": 0
            }
    
    async def get_booking_detail_admin(
        self,
        booking_id: str
    ) -> Dict[str, Any]:
        """
        Admin: Lấy chi tiết bất kỳ booking nào
        
        Args:
            booking_id: UUID của booking
            
        Returns:
            Dict with EC, EM, and data
        """
        try:
            # Join với tour_packages để lấy đầy đủ thông tin tour
            result = self.supabase.table('bookings')\
                .select('*, tour_packages(*)', count='exact')\
                .eq('booking_id', booking_id)\
                .execute()
            
            if not result.data:
                return {
                    "EC": 1,
                    "EM": "Booking not found",
                    "data": None
                }
            
            booking = result.data[0]
            tour_pkg = booking.get('tour_packages', {})
            if isinstance(tour_pkg, list) and tour_pkg:
                tour_pkg = tour_pkg[0]
            elif not isinstance(tour_pkg, dict):
                tour_pkg = {}
            
            # Format tour package info
            tour_package_info = None
            if tour_pkg:
                tour_package_info = {
                    "package_id": tour_pkg.get('package_id'),
                    "package_name": tour_pkg.get('package_name'),
                    "destination": tour_pkg.get('destination'),
                    "description": tour_pkg.get('description'),
                    "duration_days": tour_pkg.get('duration_days'),
                    "start_date": tour_pkg.get('start_date'),
                    "end_date": tour_pkg.get('end_date'),
                    "price": float(tour_pkg.get('price', 0)),
                    "image_urls": tour_pkg.get('image_urls')
                }
            
            # Format booking detail
            formatted_data = {
                "booking_id": booking['booking_id'],
                "status": booking['status'],
                "number_of_people": booking['number_of_people'],
                "total_amount": float(booking['total_amount']),
                "contact_name": booking['contact_name'],
                "contact_phone": booking['contact_phone'],
                "special_requests": booking.get('special_requests'),
                "created_at": booking['created_at'],
                "updated_at": booking['updated_at'],
                "tour_package": tour_package_info
            }
            
            return {
                "EC": 0,
                "EM": "Success",
                "data": formatted_data
            }
            
        except Exception as e:
            logger.error(f"Error getting booking detail admin {booking_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving booking: {str(e)}",
                "data": None
            }

