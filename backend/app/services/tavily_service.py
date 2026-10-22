import os
import time
import asyncio
import hashlib
from typing import Dict, Any, List, Optional
import httpx

from app.config import settings
from app.security.sanitizer import is_safe_url, normalize_url


class TavilyConfigurationError(RuntimeError):
    """Raised when live scholarship discovery is requested without a configured TAVILY_API_KEY."""
    def __init__(
        self,
        message: str = (
            "TAVILY_API_KEY is not configured. Live scholarship discovery requires a valid Tavily API key. "
            "Please configure TAVILY_API_KEY in the environment or .env file."
        )
    ):
        super().__init__(message)
        self.message = message


class TavilyService:
    """
    Live scholarship discovery service using Tavily Search API.
    Provides profile-targeted searches, caching to prevent redundant API usage,
    and exponential backoff retry for transient failures.
    """
    TAVILY_SEARCH_URL = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: Optional[str] = None,
        search_depth: Optional[str] = None,
        max_results: Optional[int] = None,
        cache_ttl_seconds: int = 3600
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "TAVILY_API_KEY", "")
        self.search_depth = search_depth or getattr(settings, "TAVILY_SEARCH_DEPTH", "basic")
        self.max_results = max_results or getattr(settings, "TAVILY_MAX_RESULTS", 5)
        self.cache_ttl_seconds = cache_ttl_seconds
        self._is_quota_exhausted = False
        self._cache: Dict[str, Dict[str, Any]] = {}

    def reload_credentials(self, new_key: Optional[str] = None) -> None:
        """Reloads TAVILY_API_KEY from environment or settings."""
        from app.config import reload_settings
        reload_settings()
        self.api_key = new_key or getattr(settings, "TAVILY_API_KEY", "")
        self.search_depth = getattr(settings, "TAVILY_SEARCH_DEPTH", "basic")
        self.max_results = getattr(settings, "TAVILY_MAX_RESULTS", 5)
        self._is_quota_exhausted = False

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def ensure_available(self) -> None:
        """Validates that Tavily API key is configured; raises TavilyConfigurationError otherwise."""
        if not self.is_available:
            raise TavilyConfigurationError()

    def _cache_key(self, query: str, search_depth: str, max_results: int) -> str:
        raw = f"{query.strip().lower()}|{search_depth}|{max_results}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_from_cache(self, query: str, search_depth: str, max_results: int) -> Optional[Dict[str, Any]]:
        key = self._cache_key(query, search_depth, max_results)
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() - entry["timestamp"] > self.cache_ttl_seconds:
            del self._cache[key]
            return None
        return entry["data"]

    def put_in_cache(self, query: str, search_depth: str, max_results: int, data: Dict[str, Any]) -> None:
        key = self._cache_key(query, search_depth, max_results)
        self._cache[key] = {
            "timestamp": time.time(),
            "data": data
        }

    def clear_cache(self) -> None:
        self._cache.clear()

    async def search(
        self,
        query: str,
        search_depth: Optional[str] = None,
        max_results: Optional[int] = None,
        include_raw_content: bool = False,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a targeted search using Tavily API.
        Applies in-memory query caching and exponential backoff retry for transient errors.
        """
        if not self.is_available:
            return {
                "success": False,
                "status": "NOT_CONFIGURED",
                "error": "TAVILY_API_KEY is not configured.",
                "results": [],
                "query": query,
                "country": country
            }

        depth = search_depth or self.search_depth
        limit = max_results or self.max_results

        # 1. Check Cache (Requirement 6: Cache search results to reduce repeated API usage)
        cached = self.get_from_cache(query, depth, limit)
        if cached:
            cached_copy = dict(cached)
            cached_copy["cached"] = True
            return cached_copy

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": depth,
            "max_results": limit,
            "include_raw_content": include_raw_content,
            "include_answer": False
        }

        # 2. Retry loop with exponential backoff for transient failures (Requirement 6)
        max_retries = 3
        backoff_delays = [0.5, 1.5, 3.0]
        last_error = ""

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        self.TAVILY_SEARCH_URL,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    raw_results = data.get("results", [])
                    filtered_results = []

                    for r in raw_results:
                        raw_url = r.get("url", "")
                        if raw_url and is_safe_url(raw_url):
                            filtered_results.append({
                                "title": r.get("title", "Official Degree / Scholarship Portal"),
                                "url": normalize_url(raw_url),
                                "content": r.get("content", ""),
                                "raw_content": r.get("raw_content"),
                                "score": r.get("score", 0.0)
                            })

                    response_data = {
                        "success": True,
                        "status": "SUCCESS",
                        "results": filtered_results,
                        "query": query,
                        "country": country,
                        "cached": False
                    }
                    self.put_in_cache(query, depth, limit, response_data)
                    return response_data

                # Quota / Rate limit exhausted
                if resp.status_code in (429, 432):
                    self._is_quota_exhausted = True
                    error_msg = f"Tavily API quota or rate limit exhausted (HTTP {resp.status_code})."
                    return {
                        "success": False,
                        "status": "QUOTA_EXHAUSTED",
                        "error": error_msg,
                        "results": [],
                        "query": query,
                        "country": country
                    }

                # Retryable server errors (500, 502, 503, 504)
                if resp.status_code in (500, 502, 503, 504):
                    last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
                    if attempt < max_retries - 1:
                        await asyncio.sleep(backoff_delays[attempt])
                        continue
                    break

                # Non-retryable client error (400, 401, 403, etc.)
                last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
                break

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = f"Network transport error: {str(exc)}"
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff_delays[attempt])
                    continue
                break
            except Exception as e:
                last_error = f"Unexpected Tavily search error: {str(e)}"
                break

        return {
            "success": False,
            "status": "ERROR",
            "error": last_error or "Tavily search request failed.",
            "results": [],
            "query": query,
            "country": country
        }


tavily_service = TavilyService()
