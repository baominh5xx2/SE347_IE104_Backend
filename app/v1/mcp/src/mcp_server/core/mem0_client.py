"""Mem0 client wrapper for MCP tools."""
from __future__ import annotations

import logging
import os
from threading import RLock
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mem0 import MemoryClient

from .config import settings

load_dotenv()

logger = logging.getLogger(__name__)


class MCPMem0Client:
    """Thread-safe singleton Mem0 client for MCP server."""

    _instance: Optional["MCPMem0Client"] = None
    _lock = RLock()

    def __new__(cls) -> "MCPMem0Client":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self) -> None:
        api_key = settings.MEM0_API_KEY or os.getenv("MEM0_API_KEY")
        if not api_key:
            self.is_available = False
            logger.error("❌ MEM0_API_KEY is not configured for MCP server")
            return

        self._client = MemoryClient(api_key=api_key)
        self.is_available = True
        logger.info("✅ MCP Mem0 client initialized")

    def _merge_filters(
        self,
        user_filter: Optional[Dict[str, Any]],
        extra_filters: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Merge user filter with caller-provided filters using Mem0 v2 syntax."""
        if not user_filter and not extra_filters:
            return None

        # If caller already provided logical operators (AND/OR/NOT), respect structure
        if extra_filters and any(key in {"AND", "OR", "NOT"} for key in extra_filters.keys()):
            merged_filters = extra_filters.copy()
            if user_filter:
                # Inject user filter via AND to ensure isolation
                if "AND" in merged_filters:
                    merged_filters["AND"].append(user_filter)
                else:
                    merged_filters = {"AND": [user_filter, merged_filters]}
            return merged_filters

        merged_filters: Dict[str, Any] = {"AND": []}

        if user_filter:
            merged_filters["AND"].append(user_filter)

        if extra_filters:
            for key, value in extra_filters.items():
                merged_filters["AND"].append({key: value})

        if not merged_filters["AND"]:
            return None

        return merged_filters

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search memories in Mem0 using v2 filters."""
        if not self.is_available:
            logger.warning("Mem0 client not available, returning empty results")
            return []

        user_filter = {"user_id": user_id} if user_id else None
        query_filters = self._merge_filters(user_filter, filters)

        results = self._client.search(
            query=query,
            user_id=user_id,
            limit=limit,
            version="v2",
            filters=query_filters
        )

        # Mem0 v2 can return {"results": [...]}
        if isinstance(results, dict):
            return results.get("results", [])

        return results


mem0_client = MCPMem0Client()
