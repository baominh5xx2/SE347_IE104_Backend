"""
Travel News API Endpoints
"""
import logging
from fastapi import APIRouter, Query, HTTPException, Path
from typing import Optional

from app.v1.services.travel_news_service import get_travel_news_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{k}")
async def get_travel_news(
    k: int = Path(..., ge=1, description="Number of latest news items to fetch for today"),
    source_type: Optional[str] = Query(None, description="Filter by source type: 'news' or 'guide'"),
    destination: Optional[str] = Query(None, description="Filter by destination (partial match)")
):
    """
    Lấy k cái URL tin tức/cẩm nang du lịch của ngày hôm nay, mới nhất trước
    
    Args:
        k: Số lượng items cần lấy của ngày hôm nay
        source_type: Lọc theo loại ('news' hoặc 'guide')
        destination: Lọc theo địa điểm (tìm kiếm partial)
        
    Returns:
        Dict với k items của ngày hôm nay
    """
    try:
        service = get_travel_news_service()
        result = service.get_today_travel_news(
            limit=k,
            source_type=source_type,
            destination=destination
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to fetch travel news")
            )
        
        return {
            "EC": 0,
            "EM": "Success",
            "data": result.get("data", []),
            "count": len(result.get("data", [])),
            "date": result.get("date", ""),
            "source": result.get("source", ""),
            "total": result.get("total", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_travel_news endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/run_agent")
async def run_agent():
    """
    Trigger Perplexity Search Agent ngay lập tức để lấy tin tức/cẩm nang du lịch MỚI & HOT
    với detailed prompt ưu tiên trending topics, recent news (7-30 ngày gần đây)
    và lưu vào DB (bỏ qua lịch chạy cron).
    """
    try:
        service = get_travel_news_service()
        # Use detailed prompt to prioritize trending/new content
        result = await service.search_and_save_travel_news(use_detailed_prompt=True)

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to refresh travel news"),
            )

        return {
            "EC": 0,
            "EM": "Perplexity search executed successfully with trending content preference",
            "saved": result.get("saved", 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in refresh_travel_news endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")