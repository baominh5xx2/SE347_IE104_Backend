"""
Report Service
Handles analytics and reporting for bookings and tours
"""
import logging
from datetime import datetime, timedelta, date, timezone
from typing import Optional, Dict, Any, List
from supabase import Client

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating reports and analytics"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize ReportService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    def _get_price_range_category(self, price: float) -> str:
        """
        Categorize tour price into price range
        
        Args:
            price: Tour price
            
        Returns:
            Price range category: budget, medium, premium
        """
        if price < 5_000_000:
            return "budget"
        elif price < 15_000_000:
            return "medium"
        else:
            return "premium"
    
    def _get_price_range_filter(self, price_range: Optional[str]) -> tuple:
        """
        Get min and max price for a price range
        
        Args:
            price_range: Price range category
            
        Returns:
            Tuple of (min_price, max_price)
        """
        if not price_range:
            return (0, float('inf'))
        
        price_ranges = {
            "budget": (0, 5_000_000),
            "medium": (5_000_000, 15_000_000),
            "premium": (15_000_000, float('inf'))
        }
        return price_ranges.get(price_range, (0, float('inf')))
    
    def _get_week_boundaries(self, target_date: date) -> tuple:
        """
        Get start and end date of the week containing target_date
        Week starts on Monday and ends on Sunday
        
        Args:
            target_date: Date to find week boundaries for
            
        Returns:
            Tuple of (week_start, week_end)
        """
        # Get Monday of the current week (weekday: 0=Mon, 1=Tue, ..., 6=Sun)
        days_since_monday = target_date.weekday()
        week_start = target_date - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)  # Sunday
        return (week_start, week_end)
    
    def _get_month_boundaries(self, target_date: date) -> tuple:
        """
        Get start and end date of the month containing target_date
        
        Args:
            target_date: Date to find month boundaries for
            
        Returns:
            Tuple of (month_start, month_end)
        """
        month_start = target_date.replace(day=1)
        
        # Get last day of month
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        month_end = next_month - timedelta(days=1)
        
        return (month_start, month_end)
    
    async def get_revenue_report(
        self,
        period_type: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        num_periods: int = 12
    ) -> Dict[str, Any]:
        """
        Get revenue report by week or month
        
        Args:
            period_type: "week" or "month"
            start_date: Start date for report (default: num_periods ago)
            end_date: End date for report (default: today)
            num_periods: Number of periods to show if start_date not provided
            
        Returns:
            Dict with EC, EM, period_type, data, total_revenue, total_bookings
        """
        try:
            # Set default dates
            if not end_date:
                end_date = date.today()
            
            if not start_date:
                if period_type == "week":
                    start_date = end_date - timedelta(weeks=num_periods)
                else:  # month
                    # Go back num_periods months
                    year = end_date.year
                    month = end_date.month - num_periods
                    while month <= 0:
                        month += 12
                        year -= 1
                    start_date = date(year, month, 1)
            
            # Fetch all bookings in the date range (exclude cancelled only)
            response = self.supabase.table('bookings')\
                .select('booking_id, total_amount, created_at, status')\
                .gte('created_at', start_date.isoformat())\
                .lte('created_at', end_date.isoformat())\
                .neq('status', 'cancelled')\
                .execute()
            
            bookings = response.data if response.data else []
            
            # Group by period
            periods = {}
            for booking in bookings:
                created_at = datetime.fromisoformat(booking['created_at'].replace('Z', '+00:00')).date()
                
                if period_type == "week":
                    period_start, period_end = self._get_week_boundaries(created_at)
                else:  # month
                    period_start, period_end = self._get_month_boundaries(created_at)
                
                period_key = (period_start, period_end)
                
                if period_key not in periods:
                    periods[period_key] = {
                        'period_start': period_start,
                        'period_end': period_end,
                        'total_revenue': 0.0,
                        'total_bookings': 0
                    }
                
                periods[period_key]['total_revenue'] += float(booking['total_amount'])
                periods[period_key]['total_bookings'] += 1
            
            # Convert to list and sort
            data = sorted(periods.values(), key=lambda x: x['period_start'])
            
            # Calculate totals
            total_revenue = sum(p['total_revenue'] for p in data)
            total_bookings = sum(p['total_bookings'] for p in data)
            
            return {
                "EC": 0,
                "EM": "Success",
                "period_type": period_type,
                "data": data,
                "total_revenue": total_revenue,
                "total_bookings": total_bookings
            }
            
        except Exception as e:
            logger.error(f"Error generating revenue report: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error generating revenue report: {str(e)}",
                "period_type": period_type,
                "data": [],
                "total_revenue": 0.0,
                "total_bookings": 0
            }
    
    async def get_people_stats_by_price_range(
        self,
        period_type: str,
        target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get statistics of people traveling by price range for a specific week or month
        
        Args:
            period_type: "week" or "month"
            target_date: Date to determine the period (default: today)
            
        Returns:
            Dict with EC, EM, period_type, period_start, period_end, data, totals
        """
        try:
            # Set default date
            if not target_date:
                target_date = date.today()
            
            # Get period boundaries
            if period_type == "week":
                period_start, period_end = self._get_week_boundaries(target_date)
            else:  # month
                period_start, period_end = self._get_month_boundaries(target_date)
            
            # Fetch bookings with tour package info
            # Note: period_end needs to include the entire day (23:59:59)
            period_end_inclusive = f"{period_end.isoformat()}T23:59:59.999999"
            
            logger.info(f"Querying bookings from {period_start.isoformat()} to {period_end_inclusive}")
            
            response = self.supabase.table('bookings')\
                .select('booking_id, package_id, number_of_people, total_amount, created_at, status, tour_packages(package_id, package_name, destination, price)')\
                .gte('created_at', period_start.isoformat())\
                .lte('created_at', period_end_inclusive)\
                .neq('status', 'cancelled')\
                .execute()
            
            bookings = response.data if response.data else []
            logger.info(f"Found {len(bookings)} bookings in period")
            
            # Initialize stats for each price range
            price_ranges_config = {
                "budget": {"min": 0, "max": 5_000_000},
                "medium": {"min": 5_000_000, "max": 15_000_000},
                "premium": {"min": 15_000_000, "max": None}
            }
            
            stats_by_range = {
                range_name: {
                    "price_range": range_name,
                    "price_min": config["min"],
                    "price_max": config["max"],
                    "total_people": 0,
                    "total_bookings": 0,
                    "tour_ids": set()
                }
                for range_name, config in price_ranges_config.items()
            }
            
            # Process bookings
            for booking in bookings:
                if not booking.get('tour_packages'):
                    logger.warning(f"Booking {booking.get('booking_id')} has no tour_packages data")
                    continue
                
                package = booking['tour_packages']
                price = float(package['price'])
                package_id = str(package['package_id'])
                
                # Determine price range
                price_range = self._get_price_range_category(price)
                
                logger.debug(f"Booking {booking['booking_id']}: {booking['number_of_people']} people, "
                           f"tour {package_id} (price {price:,.0f} VND) -> {price_range}, "
                           f"status={booking.get('status')}")
                
                if price_range in stats_by_range:
                    stats_by_range[price_range]['total_people'] += booking['number_of_people']
                    stats_by_range[price_range]['total_bookings'] += 1
                    stats_by_range[price_range]['tour_ids'].add(package_id)
            
            # Convert to list and add tour count
            data = []
            for range_name in ["budget", "medium", "premium"]:
                stat = stats_by_range[range_name]
                data.append({
                    "price_range": stat["price_range"],
                    "price_min": stat["price_min"],
                    "price_max": stat["price_max"],
                    "total_people": stat["total_people"],
                    "total_bookings": stat["total_bookings"],
                    "total_tours": len(stat["tour_ids"])
                })
            
            # Calculate totals
            total_people_all_ranges = sum(d["total_people"] for d in data)
            total_bookings_all_ranges = sum(d["total_bookings"] for d in data)
            
            return {
                "EC": 0,
                "EM": "Success",
                "period_type": period_type,
                "period_start": period_start,
                "period_end": period_end,
                "data": data,
                "total_people_all_ranges": total_people_all_ranges,
                "total_bookings_all_ranges": total_bookings_all_ranges
            }
            
        except Exception as e:
            logger.error(f"Error getting price range statistics: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error getting price range statistics: {str(e)}",
                "period_type": period_type,
                "period_start": target_date,
                "period_end": target_date,
                "data": [],
                "total_people_all_ranges": 0,
                "total_bookings_all_ranges": 0
            }
