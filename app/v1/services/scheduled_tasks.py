"""
Scheduled Tasks
Background jobs chạy định kỳ
"""
import logging
import asyncio
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from app.v1.core.config import settings
from app.v1.core.supabase import get_supabase_client
from app.v1.services.travel_news_service import get_travel_news_service

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler = None


def get_scheduler() -> AsyncIOScheduler:
    """Get singleton scheduler instance"""
    global _scheduler
    if _scheduler is None:
        # Setup scheduler với timezone Asia/Ho_Chi_Minh
        vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
        _scheduler = AsyncIOScheduler(timezone=vn_tz)
    return _scheduler


async def daily_travel_news_job():
    """
    Job chạy mỗi ngày để search và lưu tin tức/cẩm nang du lịch
    """
    logger.info("Starting daily travel news search job...")
    try:
        service = get_travel_news_service()
        result = await service.search_and_save_travel_news()
        
        if result.get("success"):
            saved_count = result.get("saved", 0)
            logger.info(f"Daily travel news job completed successfully. Saved {saved_count} URLs.")
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"Daily travel news job failed: {error}")
    except Exception as e:
        logger.error(f"Error in daily travel news job: {str(e)}", exc_info=True)


async def auto_complete_bookings_job():
    """
    Job chạy mỗi ngày để tự động chuyển booking status thành 'completed'
    khi tour đã kết thúc (end_date < today)
    
    Logic:
    1. Tìm tất cả bookings có status='confirmed'
    2. JOIN với tour_packages để lấy end_date
    3. Update status='completed' nếu end_date < today
    """
    logger.info("Starting auto-complete bookings job...")
    try:
        supabase = get_supabase_client()
        today = date.today().isoformat()
        
        # Lấy danh sách bookings confirmed cần update
        # Join với tour_packages để check end_date
        bookings_result = supabase.table('bookings') \
            .select('booking_id, package_id, status, tour_packages!inner(end_date)') \
            .eq('status', 'confirmed') \
            .execute()
        
        if not bookings_result.data:
            logger.info("No confirmed bookings to check.")
            return
        
        # Filter bookings có tour đã kết thúc
        completed_count = 0
        for booking in bookings_result.data:
            tour_info = booking.get('tour_packages', {})
            end_date = tour_info.get('end_date')
            
            if end_date and end_date < today:
                # Update status to completed
                update_result = supabase.table('bookings') \
                    .update({'status': 'completed', 'updated_at': 'now()'}) \
                    .eq('booking_id', booking['booking_id']) \
                    .execute()
                
                if update_result.data:
                    completed_count += 1
                    logger.debug(f"Booking {booking['booking_id']} marked as completed")
        
        logger.info(f"Auto-complete bookings job finished. Updated {completed_count} bookings to 'completed'.")
        
    except Exception as e:
        logger.error(f"Error in auto-complete bookings job: {str(e)}", exc_info=True)


def setup_scheduled_jobs():
    """
    Setup tất cả scheduled jobs
    """
    scheduler = get_scheduler()
    
    # Schedule daily travel news job lúc 17:00 giờ VN
    hour = getattr(settings, "TRAVEL_NEWS_SCHEDULE_HOUR", 17)
    minute = getattr(settings, "TRAVEL_NEWS_SCHEDULE_MINUTE", 0)
    
    scheduler.add_job(
        daily_travel_news_job,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=pytz.timezone("Asia/Ho_Chi_Minh")),
        id="daily_travel_news",
        name="Daily Travel News Search",
        replace_existing=True,
    )
    
    logger.info(f"Scheduled daily travel news job at {hour:02d}:{minute:02d} (VN time)")
    
    # Schedule auto-complete bookings job lúc 01:00 giờ VN (chạy ban đêm)
    scheduler.add_job(
        auto_complete_bookings_job,
        trigger=CronTrigger(hour=1, minute=0, timezone=pytz.timezone("Asia/Ho_Chi_Minh")),
        id="auto_complete_bookings",
        name="Auto-Complete Bookings",
        replace_existing=True,
    )
    
    logger.info("Scheduled auto-complete bookings job at 01:00 (VN time)")


def start_scheduler():
    """Start the scheduler"""
    scheduler = get_scheduler()
    if not scheduler.running:
        setup_scheduled_jobs()
        scheduler.start()
        logger.info("Scheduler started successfully")
    else:
        logger.warning("Scheduler is already running")


def shutdown_scheduler():
    """Shutdown the scheduler"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler shut down successfully")
        _scheduler = None