"""
Perplexity API Service cho News Search Agent
Service để gọi Perplexity API và lấy tin tức/cẩm nang du lịch mới nhất
Sử dụng official Perplexity SDK với prompt tối ưu cho news/guides
"""
import logging
import os
import re
import json
from typing import Dict, Any, Optional, List
from app.v1.core.config import settings

logger = logging.getLogger(__name__)

# Import official Perplexity SDK
from perplexity import Perplexity


class NewsPerplexityService:
    """Service để gọi Perplexity API và lấy tin tức/cẩm nang du lịch"""
    
    def __init__(self):
        """Initialize News Perplexity Service"""
        self.api_key = settings.PERPLEXITY_API_KEY
    
    async def search_news_info(
        self,
        query: str,
        query_type: str = "latest"
    ) -> Dict[str, Any]:
        """
        Tìm tin tức/cẩm nang du lịch mới nhất dựa trên query của user
        
        Args:
            query: Câu hỏi/từ khóa từ user (ví dụ: "đà lạt có gì hot", "cẩm nang phú quốc")
            query_type: Loại query ("latest" cho thông tin mới nhất)
            
        Returns:
            Dict với thông tin: highlights, tips, sources, raw_results
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "PERPLEXITY_API_KEY not configured",
                "query": query
            }
        
        try:
            import asyncio
            import concurrent.futures
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # ==== Phase 1: Gọi chat API với prompt tối ưu cho news/guides ====
                system_prompt = (
                    "Bạn là chuyên gia tìm kiếm và tổng hợp tin tức du lịch và cẩm nang du lịch. "
                    "Nhiệm vụ của bạn là tìm kiếm thông tin mới nhất, hot nhất về du lịch từ internet và trả về dưới dạng JSON. "
                    "CHỈ TRẢ VỀ JSON THUẦN TÚY, KHÔNG CÓ VĂN BẢN GIẢI THÍCH NÀO KHÁC. "
                    "Schema JSON bắt buộc: {"
                    '  "highlights": ["tin tức 1", "tin tức 2", ...],  // Danh sách tin tức hot, xu hướng du lịch mới nhất, điểm đến nổi bật'
                    '  "tips": ["lưu ý 1", "lưu ý 2", ...],  // Cẩm nang du lịch, kinh nghiệm, lưu ý quan trọng, mẹo du lịch'
                    '  "sources": ["url1", "url2", ...]  // Danh sách URL nguồn tham khảo từ các trang tin tức du lịch'
                    "}"
                )
                user_prompt = (
                    f"Tìm kiếm và tổng hợp tin tức du lịch và cẩm nang du lịch mới nhất về: '{query}'. "
                    "YÊU CẦU: "
                    "- Ưu tiên tuyệt đối thông tin trong 7-30 ngày gần đây, tin tức hot nhất hiện tại. "
                    "- Tập trung vào: tin tức du lịch mới, xu hướng du lịch đang hot, điểm đến nổi bật, sự kiện du lịch, "
                    "cẩm nang du lịch chi tiết, kinh nghiệm thực tế, lưu ý quan trọng cho du khách, mẹo du lịch hữu ích. "
                    "- Lấy thông tin từ các trang tin tức du lịch uy tín, blog du lịch, trang cẩm nang du lịch. "
                    "- Mỗi highlight phải là một tin tức hoặc thông tin cụ thể, rõ ràng. "
                    "- Mỗi tip phải là một lưu ý, kinh nghiệm hoặc cẩm nang thực tế và hữu ích. "
                    "- Sources phải là URL đầy đủ của các trang web nguồn. "
                    "TRẢ VỀ JSON THUẦN TÚY THEO ĐÚNG SCHEMA TRÊN, KHÔNG CÓ VĂN BẢN NÀO KHÁC NGOÀI JSON."
                )
                
                try:
                    chat_resp = await loop.run_in_executor(
                        executor,
                        lambda: Perplexity(api_key=self.api_key).chat.completions.create(
                            model="sonar",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.3,
                            max_tokens=2000  # Tăng max_tokens để lấy nhiều thông tin hơn
                        )
                    )
                    
                    content = ""
                    try:
                        choices = getattr(chat_resp, "choices", [])
                        if choices:
                            message = choices[0].message
                            content = getattr(message, "content", "") or ""
                        else:
                            content = getattr(chat_resp, "content", "") or ""
                    except Exception:
                        content = ""
                    
                    if content:
                        cleaned = content.strip()
                        if cleaned.startswith("```"):
                            cleaned = cleaned.strip("`").strip()
                            if cleaned.lower().startswith("json"):
                                cleaned = cleaned[4:].strip()
                        try:
                            parsed = json.loads(cleaned)
                            parsed.setdefault("highlights", [])
                            parsed.setdefault("tips", [])
                            parsed.setdefault("sources", [])
                            
                            return {
                                "success": True,
                                "highlights": parsed.get("highlights", [])[:10],  # Lấy nhiều hơn cho news
                                "tips": parsed.get("tips", [])[:10],
                                "sources": parsed.get("sources", []),
                                "raw_response": content
                            }
                        except Exception as parse_error:
                            logger.warning(f"Failed to parse JSON response: {parse_error}")
                            # Fall through to search API
                except Exception as chat_error:
                    logger.warning(f"Chat structured query failed, fallback to search. Error: {chat_error}")
                
                # ==== Phase 2: fallback search API với query tối ưu cho news ====
                search_query = (
                    f"Tin tức và cẩm nang du lịch mới nhất về {query}. "
                    f"Tìm các bài viết, tin tức du lịch hot, xu hướng mới, cẩm nang du lịch chi tiết, "
                    f"kinh nghiệm du lịch, lưu ý quan trọng trong 30 ngày gần đây"
                )
                
                def run_search():
                    client = Perplexity(api_key=self.api_key)
                    return client.search.create(
                        query=search_query,
                        country="VN",  # Vietnamese results
                        max_results=5  # Lấy nhiều kết quả hơn cho news
                    )
                
                search = await loop.run_in_executor(executor, run_search)
                
                results: List[Dict[str, Any]] = []
                
                for result in search.results:
                    result_data = {
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet,
                        "date": getattr(result, 'date', None),
                        "last_updated": getattr(result, 'last_updated', None)
                    }
                    results.append(result_data)
                
                if not results:
                    return {
                        "success": False,
                        "error": f"Chưa tìm thấy tin tức/cẩm nang về '{query}', vui lòng thử lại sau.",
                        "query": query,
                        "results": []
                    }
                
                # Extract highlights và tips từ results
                highlights: List[str] = []
                tips: List[str] = []
                sources: List[str] = []
                
                for item in results:
                    snippet = item.get("snippet") or ""
                    title = item.get("title") or ""
                    url = item.get("url")
                    
                    if url and url not in sources:
                        sources.append(url)
                    
                    # Highlights từ title và snippet
                    if title:
                        highlights.append(title.strip())
                    elif snippet:
                        # Lấy phần đầu của snippet làm highlight
                        highlight = snippet.strip()[:200]
                        if highlight not in highlights:
                            highlights.append(highlight)
                    
                    # Tips từ snippet nếu có từ khóa liên quan
                    tip_keywords = ["lưu ý", "tip", "khuyên", "nên", "tránh", "kinh nghiệm", "cẩm nang"]
                    if any(keyword in snippet.lower() for keyword in tip_keywords):
                        tip = snippet.strip()[:300]
                        if tip not in tips:
                            tips.append(tip)
                
                # Nếu không có tips, lấy một số snippet làm tips
                if not tips and results:
                    for item in results[:3]:
                        snippet = item.get("snippet", "")
                        if snippet:
                            tips.append(snippet.strip()[:300])
                
                highlights = highlights[:10]
                tips = tips[:10]
                
                return {
                    "success": True,
                    "highlights": highlights,
                    "tips": tips,
                    "sources": sources,
                    "raw_results": results
                }
            
        except Exception as e:
            # Handle SDK-specific exceptions if available
            error_msg = str(e)
            logger.error(f"Error calling Perplexity API for news search: {error_msg}", exc_info=True)
            
            # Check for common error types
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                error_msg = "Rate limit exceeded. Please try again later."
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                error_msg = "Invalid API key. Please check PERPLEXITY_API_KEY configuration."
            elif "timeout" in error_msg.lower():
                error_msg = "Request timeout. Please try again."
            
            return {
                "success": False,
                "error": f"Failed to get news information: {error_msg}",
                "query": query
            }


# Singleton instance
_news_perplexity_service = None

def get_news_perplexity_service() -> NewsPerplexityService:
    """Get singleton NewsPerplexityService instance"""
    global _news_perplexity_service
    if _news_perplexity_service is None:
        _news_perplexity_service = NewsPerplexityService()
    return _news_perplexity_service
