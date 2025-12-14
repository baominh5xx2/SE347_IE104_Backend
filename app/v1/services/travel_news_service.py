"""
Travel News Service
Tìm kiếm và lưu trữ tin tức/cẩm nang du lịch bằng Perplexity Search API
"""
import logging
import asyncio
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any, Optional

from supabase import Client
from perplexity import Perplexity

from app.v1.core.config import settings
from app.v1.core.supabase import supabase_client

logger = logging.getLogger(__name__)


class TravelNewsService:
    """Service để tìm kiếm và lưu trữ tin tức / cẩm nang du lịch"""

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.perplexity_api_key = settings.PERPLEXITY_API_KEY
        self.search_queries = getattr(
            settings,
            "TRAVEL_NEWS_SEARCH_QUERIES",
            ["tin tức du lịch", "cẩm nang du lịch"],
        )
        
        # Detailed prompt for Perplexity with preference for trending/new content
        self.detailed_search_prompt = """
        Tìm kiếm tin tức và cẩm nang du lịch LATEST và HOT nhất trong 2-4 tuần gần đây.
        
        YÊU CẦU:
        1. ƯU TIÊN TIN TỨC MỚI: Tìm thông tin đã xuất bản trong 7-30 ngày gần đây (avoid tin cũ)
        2. TRENDING TOPICS: Các điểm đến HOT hiện nay, promotions, seasonal events
        3. RELEVANT FOR VIETNAM: Du lịch trong Việt Nam + các điểm đến nước ngoài popular với du khách Việt
        4. PRACTICAL INFO: 
           - Hướng dẫn du lịch (visa, budget, best time to visit)
           - Updates về điều kiện du lịch (an toàn, weather, restrictions)
           - Khám phá điểm mới lạ
           - Festival/sự kiện du lịch sắp tới
           - Flight deals, tour promotions
        5. SOURCE QUALITY: Ưu tiên từ các trang uy tín (tour operators, travel guides, news sites)
        6. RECENCY: Sắp xếp theo mới nhất trước
        
        TRẢ VỀ TOP RESULTS: Kết quả mới nhất, most relevant, được verify từ các nguồn tin tức
        """

    def _run_search_sync(self, query: str, use_detailed_prompt: bool = False):
        """Chạy Perplexity Search (sync)
        Args:
            query: Search query
            use_detailed_prompt: Nếu True, sử dụng detailed prompt cho kết quả tốt hơn
        """
        client = Perplexity(api_key=self.perplexity_api_key)
        
        # Enhance query with detailed prompt if requested
        if use_detailed_prompt:
            enhanced_query = f"{self.detailed_search_prompt}\n\nSearch for: {query}"
        else:
            enhanced_query = query
        
        return client.search.create(
            query=enhanced_query,
            country="VN",  # Ưu tiên kết quả tại Việt Nam
            max_results=20,  # Tăng từ 10 lên 15 để lấy nhiều kết quả hơn
        )

    async def search_and_save_travel_news(self, use_detailed_prompt: bool = True) -> Dict[str, Any]:
        """
        Chạy search cho các query cấu hình và lưu kết quả vào DB.
        Args:
            use_detailed_prompt: Nếu True, sử dụng detailed prompt để ưu tiên tin tức mới/hot
        """
        if not self.perplexity_api_key:
            error_msg = "PERPLEXITY_API_KEY not configured"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "saved": 0}

        saved_count = 0
        results_collected: List[Dict[str, Any]] = []

        try:
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for query in self.search_queries:
                    try:
                        search = await loop.run_in_executor(
                            executor, self._run_search_sync, query, use_detailed_prompt
                        )
                        if not search or not getattr(search, "results", None):
                            logger.warning(f"No results returned for query: {query}")
                            continue

                        source_type = "guide" if "cẩm nang" in query.lower() else "news"

                        for item in search.results:
                            results_collected.append(
                                {
                                    "title": item.title,
                                    "url": item.url,
                                    "snippet": item.snippet,
                                    "date": getattr(item, "date", None),
                                    "last_updated": getattr(item, "last_updated", None),
                                    "source_type": source_type,
                                    "destination": None,
                                    "created_at": datetime.utcnow().isoformat(),
                                    "updated_at": datetime.utcnow().isoformat(),
                                }
                            )
                    except Exception as e:
                        logger.error(f"Error searching query '{query}': {str(e)}")

            if results_collected:
                saved_count = self.save_news_urls(results_collected)

            return {"success": True, "saved": saved_count}

        except Exception as e:
            logger.error(f"Error in search_and_save_travel_news: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e), "saved": saved_count}

    def save_news_urls(self, items: List[Dict[str, Any]]) -> int:
        """
        Lưu batch URLs vào database, skip duplicates bằng upsert theo URL.
        Deduplicate items trước để tránh PostgreSQL error khi ON CONFLICT
        """
        if not items:
            return 0

        try:
            # Deduplicate items by URL - keep first occurrence (newest)
            seen_urls = set()
            deduplicated_items = []
            for item in items:
                url = item.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    deduplicated_items.append(item)
            
            if not deduplicated_items:
                logger.warning("No unique URLs to save after deduplication")
                return 0
            
            logger.info(f"Saving {len(deduplicated_items)} unique URLs (deduplicated from {len(items)})")
            
            result = (
                self.supabase.table("travel_news_urls")
                .upsert(deduplicated_items, on_conflict="url")
                .execute()
            )
            # supabase-py upsert trả về data với rows inserted/updated
            data = getattr(result, "data", []) or []
            return len(data)
        except Exception as e:
            logger.error(f"Error saving travel news URLs: {str(e)}", exc_info=True)
            return 0

    def get_travel_news(
        self,
        page: int = 1,
        limit: int = 20,
        source_type: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lấy danh sách URLs đã lưu với pagination.
        """
        offset = max(page - 1, 0) * limit

        try:
            query = self.supabase.table("travel_news_urls").select("*", count="exact")

            if source_type:
                query = query.eq("source_type", source_type)
            if destination:
                query = query.ilike("destination", f"%{destination}%")

            count_result = query.execute()
            total = count_result.count if hasattr(count_result, "count") else 0

            # Lấy data với order mới nhất
            data_query = self.supabase.table("travel_news_urls").select("*")
            if source_type:
                data_query = data_query.eq("source_type", source_type)
            if destination:
                data_query = data_query.ilike("destination", f"%{destination}%")

            data_result = (
                data_query.order("date", desc=True)
                .order("created_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )

            data = data_result.data or []
            total_pages = (total + limit - 1) // limit if limit > 0 else 0

            return {
                "success": True,
                "data": data,
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
            }

        except Exception as e:
            logger.error(f"Error fetching travel news: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "page": page,
                "limit": limit,
                "total": 0,
            }

    def search_travel_news(
        self,
        keywords: str,
        source_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search travel news theo keywords trong title với pagination.
        
        Args:
            keywords: Keywords để search (sẽ split thành các từ riêng lẻ)
            source_type: Filter theo loại ('news' hoặc 'guide')
            page: Page number (bắt đầu từ 1)
            limit: Số items per page
            
        Returns:
            Dict với search results và pagination info
        """
        offset = max(page - 1, 0) * limit
        
        try:
            # Split keywords thành các từ riêng lẻ và loại bỏ empty strings
            keyword_list = [kw.strip() for kw in keywords.split() if kw.strip()]
            
            if not keyword_list:
                return {
                    "success": False,
                    "error": "Keywords cannot be empty",
                    "data": [],
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "total_pages": 0,
                }
            
            # Build base query
            query = self.supabase.table("travel_news_urls").select("*", count="exact")
            
            # Apply source_type filter nếu có
            if source_type:
                query = query.eq("source_type", source_type)
            
            # Build OR conditions cho mỗi keyword trên field title
            # Supabase Python client hỗ trợ .or() với format: "column.ilike.pattern,column.ilike.pattern"
            or_conditions = []
            for keyword in keyword_list:
                or_conditions.append(f"title.ilike.%{keyword}%")
            
            # Apply OR filter cho title search
            if or_conditions:
                # Supabase .or() method expects a string with comma-separated conditions
                or_filter = ",".join(or_conditions)
                query = query.or_(or_filter)
            
            # Get total count
            count_result = query.execute()
            total = count_result.count if hasattr(count_result, "count") else 0
            total_pages = (total + limit - 1) // limit if limit > 0 else 0
            
            # Build data query với same filters
            data_query = self.supabase.table("travel_news_urls").select("*")
            
            if source_type:
                data_query = data_query.eq("source_type", source_type)
            
            if or_conditions:
                or_filter = ",".join(or_conditions)
                data_query = data_query.or_(or_filter)
            
            # Apply pagination và ordering
            data_result = (
                data_query.order("created_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )
            
            data = data_result.data or []
            
            return {
                "success": True,
                "data": data,
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
            }
            
        except Exception as e:
            logger.error(f"Error searching travel news: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "page": page,
                "limit": limit,
                "total": 0,
                "total_pages": 0,
            }

    def get_today_travel_news(
        self,
        limit: int = 20,
        source_type: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lấy danh sách URLs của ngày hôm nay (created_at trong ngày hôm nay)
        Nếu ngày hôm nay không có dữ liệu, lấy của ngày hôm qua
        Args:
            limit: Số lượng items cần lấy
            source_type: Lọc theo loại ('news' hoặc 'guide')
            destination: Lọc theo địa điểm
        Returns:
            Dict với URLs của ngày hôm nay (hoặc ngày hôm qua nếu hôm nay trống)
        """
        try:
            from datetime import datetime, timezone, timedelta
            
            # Get today's date range (00:00:00 to 23:59:59 UTC)
            today = datetime.now(timezone.utc).date()
            start_of_day = f"{today}T00:00:00Z"
            end_of_day = f"{today}T23:59:59Z"
            
            logger.info(f"Fetching travel news for today: {today}")
            
            # Build query for today
            query = (
                self.supabase.table("travel_news_urls")
                .select("*")
                .gte("created_at", start_of_day)
                .lte("created_at", end_of_day)
            )
            
            if source_type:
                query = query.eq("source_type", source_type)
            if destination:
                query = query.ilike("destination", f"%{destination}%")
            
            # Get count for today
            count_result = query.execute()
            today_data = count_result.data or []
            total = len(today_data)
            
            # If today has data, return it
            if today_data:
                # Fetch today's data ordered by newest first
                data_result = (
                    self.supabase.table("travel_news_urls")
                    .select("*")
                    .gte("created_at", start_of_day)
                    .lte("created_at", end_of_day)
                )
                
                if source_type:
                    data_result = data_result.eq("source_type", source_type)
                if destination:
                    data_result = data_result.ilike("destination", f"%{destination}%")
                
                data_result = (
                    data_result
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                
                data = data_result.data or []
                
                logger.info(f"Found {len(data)} travel news items for today (limited to {limit})")
                
                return {
                    "success": True,
                    "data": data,
                    "limit": limit,
                    "total": total,
                    "date": str(today),
                    "source": "today"
                }
            
            # If today is empty, fetch yesterday's data
            logger.info(f"No data for today ({today}), fetching yesterday's data...")
            yesterday = today - timedelta(days=1)
            yesterday_start = f"{yesterday}T00:00:00Z"
            yesterday_end = f"{yesterday}T23:59:59Z"
            
            data_result = (
                self.supabase.table("travel_news_urls")
                .select("*")
                .gte("created_at", yesterday_start)
                .lte("created_at", yesterday_end)
            )
            
            if source_type:
                data_result = data_result.eq("source_type", source_type)
            if destination:
                data_result = data_result.ilike("destination", f"%{destination}%")
            
            data_result = (
                data_result
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            
            data = data_result.data or []
            total_yesterday = len(data)
            
            logger.info(f"Found {len(data)} travel news items for yesterday ({yesterday}) (limited to {limit})")
            
            return {
                "success": True,
                "data": data,
                "limit": limit,
                "total": total_yesterday,
                "date": str(yesterday),
                "source": "yesterday"
            }
        
        except Exception as e:
            logger.error(f"Error fetching today's travel news: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "limit": limit,
                "total": 0,
            }


# Singleton instance
_travel_news_service: Optional[TravelNewsService] = None


def get_travel_news_service() -> TravelNewsService:
    """Get singleton TravelNewsService"""
    global _travel_news_service
    if _travel_news_service is None:
        _travel_news_service = TravelNewsService(supabase_client)
    return _travel_news_service