"""
Travel News API Endpoints
"""
import logging
from fastapi import APIRouter, Query, HTTPException, Path
from typing import Optional
from pydantic import BaseModel, Field

from app.v1.services.travel_news_service import get_travel_news_service

logger = logging.getLogger(__name__)

router = APIRouter()


class TravelNewsSearchRequest(BaseModel):
    keywords: str = Field(..., min_length=1, description="Search keywords")
    source_type: Optional[str] = Field(None, description="Filter by source type: 'news' or 'guide'")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")


# IMPORTANT: Specific routes must be defined BEFORE dynamic routes like /{k}
# Otherwise FastAPI will match /list with /{k} and try to parse "list" as integer

@router.get("/all")
async def get_paginated_travel_news_list(
    source_type: Optional[str] = Query(None, description="Filter by source type: 'news' or 'guide'"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Lấy danh sách paginated tin tức/cẩm nang du lịch (không cần keywords).
    Dùng để hiển thị danh sách ban đầu khi user chưa search.
    
    Args:
        source_type: Lọc theo loại ('news' hoặc 'guide')
        page: Page number (bắt đầu từ 1)
        limit: Số items per page
        
    Returns:
        Dict với paginated results
    """
    try:
        service = get_travel_news_service()
        result = service.get_travel_news(
            page=page,
            limit=limit,
            source_type=source_type
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to fetch travel news list")
            )
        
        return {
            "EC": 0,
            "EM": "Success",
            "data": result.get("data", []),
            "page": result.get("page", page),
            "limit": result.get("limit", limit),
            "total": result.get("total", 0),
            "total_pages": result.get("total_pages", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_paginated_travel_news_list endpoint: {str(e)}", exc_info=True)
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


@router.post("/search")
async def search_travel_news(request: TravelNewsSearchRequest):
    """
    Search travel news theo keywords trong title với pagination và filters.
    
    Args:
        request: TravelNewsSearchRequest với keywords, source_type, page, limit
        
    Returns:
        Dict với search results và pagination info
    """
    try:
        service = get_travel_news_service()
        result = service.search_travel_news(
            keywords=request.keywords,
            source_type=request.source_type,
            page=request.page,
            limit=request.limit
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to search travel news")
            )
        
        return {
            "EC": 0,
            "EM": "Success",
            "data": result.get("data", []),
            "page": result.get("page", 1),
            "limit": result.get("limit", 20),
            "total": result.get("total", 0),
            "total_pages": result.get("total_pages", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search_travel_news endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{k}")
async def get_travel_news(
    k: int = Path(..., ge=1, description="Number of latest news items to fetch for today"),
    source_type: Optional[str] = Query(None, description="Filter by source type: 'news' or 'guide'"),
    destination: Optional[str] = Query(None, description="Filter by destination (partial match)")
):
    """
    Lấy k cái URL tin tức/cẩm nang du lịch của ngày hôm nay, mới nhất trước
    Nếu không có tin tức nào, tự động trigger agent search để lấy tin tức mới
    
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
        
        data = result.get("data", [])
        
        # Nếu không có tin tức nào, tự động trigger agent search
        if not data or len(data) == 0:
            logger.info("No travel news found, triggering agent search...")
            try:
                # Trigger agent search với detailed prompt để lấy tin tức trending
                agent_result = await service.search_and_save_travel_news(use_detailed_prompt=True)
                
                if agent_result.get("success"):
                    saved_count = agent_result.get("saved", 0)
                    logger.info(f"Agent search completed, saved {saved_count} news items")
                    
                    # Query lại để lấy data mới sau khi agent search
                    result = service.get_today_travel_news(
                        limit=k,
                        source_type=source_type,
                        destination=destination
                    )
                    
                    if result.get("success"):
                        data = result.get("data", [])
                        logger.info(f"Retrieved {len(data)} news items after agent search")
                else:
                    logger.warning(f"Agent search failed: {agent_result.get('error', 'Unknown error')}")
            except Exception as agent_error:
                logger.error(f"Error triggering agent search: {str(agent_error)}", exc_info=True)
                # Continue với empty data nếu agent search fail
        
        return {
            "EC": 0,
            "EM": "Success",
            "data": data,
            "count": len(data),
            "date": result.get("date", ""),
            "source": result.get("source", ""),
            "total": result.get("total", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_travel_news endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")