"""
Scheduled Tasks
Background jobs chạy định kỳ
"""
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from app.v1.core.config import settings
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