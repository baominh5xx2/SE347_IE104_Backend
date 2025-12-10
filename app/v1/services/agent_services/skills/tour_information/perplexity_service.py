"""
Perplexity API Service
Service để gọi Perplexity API và lấy thông tin tour mới nhất
Sử dụng official Perplexity SDK
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


class PerplexityService:
    """Service để gọi Perplexity API và lấy thông tin tour du lịch"""
    
    def __init__(self):
        """Initialize Perplexity Service"""
        self.api_key = settings.PERPLEXITY_API_KEY
        self._price_pattern = re.compile(r"(\d[\d\.]{3,})(?:\s?)(vnd|vnđ|đ|usd|$)", re.IGNORECASE)
        self._time_keywords = ["tháng", "mùa", "thời điểm", "thời gian", "tốt nhất", "cao điểm", "thấp điểm"]
        self._tip_keywords = ["lưu ý", "tip", "khuyên", "nên", "tránh", "kinh nghiệm"]
    
    async def search_tour_info(
        self,
        destination: str,
        query_type: str = "latest"
    ) -> Dict[str, Any]:
        """
        Tìm thông tin tour mới nhất cho một địa điểm
        
        Args:
            destination: Tên địa điểm (ví dụ: "Đà Lạt", "Phú Quốc")
            query_type: Loại query ("latest" cho thông tin mới nhất)
            
        Returns:
            Dict với thông tin tour: destination, highlights, typical_prices, best_time, tips, sources
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "PERPLEXITY_API_KEY not configured",
                "destination": destination
            }
        
        try:
            import asyncio
            import concurrent.futures
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # ==== Phase 1: Gọi chat API và yêu cầu JSON chuẩn schema ====
                chat_success = False
                system_prompt = (
                    "Bạn là trợ lý du lịch. Trả về JSON thuần túy, không giải thích thêm. "
                    "Schema: {"
                    '  "destination": string,'
                    '  "highlights": string[],'
                    '  "typical_prices": string,'
                    '  "best_time": string,'
                    '  "tips": string[],'
                    '  "sources": string[]'
                    "}"
                )
                user_prompt = (
                    f"Địa điểm: {destination}. "
                    "Hãy tìm thông tin tour mới nhất (ưu tiên 7-30 ngày), điểm tham quan nổi bật, "
                    "khoảng giá tour phổ biến, thời gian tốt nhất để đi, lưu ý du lịch, và liệt kê nguồn (URL). "
                    "TRẢ VỀ JSON THUẦN TÚY THEO SCHEMA, KHÔNG THÊM VĂN BẢN KHÁC."
                )
                
                try:
                    chat_resp = await loop.run_in_executor(
                        executor,
                        lambda: Perplexity(api_key=self.api_key).chat.completions.create(
                            model="sonar-pro",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.3,
                            max_tokens=400
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
                            parsed.setdefault("destination", destination)
                            parsed.setdefault("highlights", [])
                            parsed.setdefault("typical_prices", "")
                            parsed.setdefault("best_time", "")
                            parsed.setdefault("tips", [])
                            parsed.setdefault("sources", [])
                            
                            return {
                                "success": True,
                                "destination": parsed.get("destination", destination),
                                "highlights": parsed.get("highlights", []),
                                "typical_prices": parsed.get("typical_prices", ""),
                                "best_time": parsed.get("best_time", ""),
                                "tips": parsed.get("tips", []),
                                "sources": parsed.get("sources", []),
                                "raw_response": content
                            }
                        except Exception:
                            pass
                except Exception as chat_error:
                    logger.warning(f"Chat structured query failed, fallback to search. Error: {chat_error}")
                
                # ==== Phase 2: fallback search API + inline format ====
                query = (
                    f"Tìm thông tin mới nhất về tour du lịch tại {destination}, "
                    f"bao gồm: điểm tham quan nổi bật, giá tour phổ biến, "
                    f"thời gian tốt nhất để đi, lưu ý du lịch, và các tour packages phổ biến, các cẩm nang du lịch"
                )
                
                def run_search():
                    client = Perplexity(api_key=self.api_key)
                    return client.search.create(
                        query=query,
                        country="VN",  # Vietnamese results
                        max_results=5
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
                        "error": f"Chưa tìm thấy thông tin cập nhật cho {destination}, vui lòng thử lại sau.",
                        "destination": destination,
                        "results": []
                    }
                
                highlights: List[str] = []
                tips: List[str] = []
                sources: List[str] = []
                typical_prices = ""
                best_time = ""
                
                for item in results:
                    snippet = item.get("snippet") or ""
                    title = item.get("title") or ""
                    url = item.get("url")
                    
                    if url and url not in sources:
                        sources.append(url)
                    
                    candidate = title.strip() or snippet.strip()
                    if candidate:
                        highlights.append(candidate[:240])
                    
                    if not typical_prices:
                        match = self._price_pattern.search(snippet.lower())
                        if match:
                            typical_prices = snippet.strip()
                    
                    if not best_time:
                        lowered = snippet.lower()
                        if any(key in lowered for key in self._time_keywords):
                            best_time = snippet.strip()
                    
                    lowered = snippet.lower()
                    if any(key in lowered for key in self._tip_keywords):
                        tips.append(snippet.strip())
                
                highlights = highlights[:5]
                tips = tips[:5]
                
                return {
                    "success": True,
                    "destination": destination,
                    "highlights": highlights,
                    "typical_prices": typical_prices,
                    "best_time": best_time,
                    "tips": tips,
                    "sources": sources,
                    "raw_results": results
                }
            
        except Exception as e:
            # Handle SDK-specific exceptions if available
            error_msg = str(e)
            logger.error(f"Error calling Perplexity API: {error_msg}", exc_info=True)
            
            # Check for common error types
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                error_msg = "Rate limit exceeded. Please try again later."
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                error_msg = "Invalid API key. Please check PERPLEXITY_API_KEY configuration."
            elif "timeout" in error_msg.lower():
                error_msg = "Request timeout. Please try again."
            
            return {
                "success": False,
                "error": f"Failed to get tour information: {error_msg}",
                "destination": destination
            }

# Singleton instance
_perplexity_service = None

def get_perplexity_service() -> PerplexityService:
    """Get singleton PerplexityService instance"""
    global _perplexity_service
    if _perplexity_service is None:
        _perplexity_service = PerplexityService()
    return _perplexity_service