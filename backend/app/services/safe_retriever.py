import re
import html
import time
from typing import Dict, Any, Optional
import httpx

from app.security.sanitizer import is_safe_url, normalize_url


class SafePageRetriever:
    """
    Safely retrieves and cleans HTML content from official university and scholarship pages.
    Enforces SSRF prevention via is_safe_url, handles redirects safely, caches page text,
    and maps HTTP status codes to standardized retrieval statuses (SUCCESS, PAYWALL, UNSAFE, ERROR).
    """
    def __init__(self, cache_ttl_seconds: int = 3600, timeout_seconds: float = 5.0):
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _get_cached(self, url: str) -> Optional[Dict[str, Any]]:
        entry = self._cache.get(url)
        if not entry:
            return None
        if time.time() - entry["timestamp"] > self.cache_ttl_seconds:
            del self._cache[url]
            return None
        return entry["data"]

    def _put_cached(self, url: str, data: Dict[str, Any]) -> None:
        self._cache[url] = {
            "timestamp": time.time(),
            "data": data
        }

    def clear_cache(self) -> None:
        self._cache.clear()

    @staticmethod
    def clean_html_to_text(raw_html: str, max_chars: int = 15000) -> str:
        """
        Converts raw HTML document into clean plain text for LLM consumption.
        Strips scripts, styles, navigational chrome, and collapses whitespace.
        """
        if not raw_html:
            return ""

        # Strip script, style, noscript, svg, nav, footer, header tags and their contents
        cleaned = re.sub(r'<(script|style|noscript|svg|nav|footer|header)\b[^>]*>.*?</\1>', ' ', raw_html, flags=re.DOTALL | re.I)
        # Strip comments
        cleaned = re.sub(r'<!--.*?-->', ' ', cleaned, flags=re.DOTALL)
        # Convert break and paragraph tags to newlines
        cleaned = re.sub(r'<(?:br|/p|/div|/h\d|/li|/tr)\b[^>]*>', '\n', cleaned, flags=re.I)
        # Strip all remaining HTML tags
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        # Unescape HTML entities
        cleaned = html.unescape(cleaned)
        # Collapse multiple spaces and blank lines
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in cleaned.splitlines()]
        text = "\n".join([line for line in lines if line])
        return text[:max_chars].strip()

    async def retrieve_page(self, url: str, max_chars: int = 15000) -> Dict[str, Any]:
        """
        Safely retrieves a webpage while verifying SSRF boundaries at each step.
        Returns standardized dictionary with:
        - success: bool
        - status: URL_RETRIEVAL_STATUS_SUCCESS | URL_RETRIEVAL_STATUS_PAYWALL | URL_RETRIEVAL_STATUS_UNSAFE | URL_RETRIEVAL_STATUS_ERROR
        - text: cleaned text
        - url: final verified URL
        - error: error message if unsuccessful
        """
        if not url:
            return {
                "success": False,
                "status": "URL_RETRIEVAL_STATUS_ERROR",
                "error": "URL cannot be empty.",
                "text": "",
                "url": url
            }

        # 1. Enforce SSRF & safe URL boundary (Requirement 3)
        if not is_safe_url(url):
            return {
                "success": False,
                "status": "URL_RETRIEVAL_STATUS_UNSAFE",
                "error": f"URL '{url}' blocked by SSRF policy or is an unsafe address.",
                "text": "",
                "url": url
            }

        norm_url = normalize_url(url)

        # 2. Check Cache (Requirement 6)
        cached = self._get_cached(norm_url)
        if cached:
            return dict(cached)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36 ScholarSwarm/1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            client_timeout = httpx.Timeout(self.timeout_seconds, connect=2.5, read=4.0)
            async with httpx.AsyncClient(timeout=client_timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)

            final_url = str(resp.url)
            # Re-verify final redirected target against SSRF policy
            if not is_safe_url(final_url):
                res = {
                    "success": False,
                    "status": "URL_RETRIEVAL_STATUS_UNSAFE",
                    "error": f"Redirect target '{final_url}' blocked by SSRF policy.",
                    "text": "",
                    "url": final_url
                }
                self._put_cached(norm_url, res)
                return res

            # Handle Paywall / Access Denied
            if resp.status_code in (401, 403):
                res = {
                    "success": False,
                    "status": "URL_RETRIEVAL_STATUS_PAYWALL",
                    "error": f"HTTP {resp.status_code} Access Denied / Institutional Login Required",
                    "text": "",
                    "url": final_url
                }
                self._put_cached(norm_url, res)
                return res

            # Handle Success
            if resp.status_code == 200:
                raw_html = resp.text
                clean_text = self.clean_html_to_text(raw_html, max_chars=max_chars)
                res = {
                    "success": True,
                    "status": "URL_RETRIEVAL_STATUS_SUCCESS",
                    "error": None,
                    "text": clean_text,
                    "url": final_url
                }
                self._put_cached(norm_url, res)
                return res

            # Any other HTTP error (404, 500, etc.)
            res = {
                "success": False,
                "status": "URL_RETRIEVAL_STATUS_ERROR",
                "error": f"HTTP {resp.status_code} error retrieving webpage",
                "text": "",
                "url": final_url
            }
            self._put_cached(norm_url, res)
            return res

        except httpx.TimeoutException:
            return {
                "success": False,
                "status": "URL_RETRIEVAL_STATUS_ERROR",
                "error": f"Connection timed out after {self.timeout_seconds}s.",
                "text": "",
                "url": url
            }
        except httpx.RequestError as exc:
            return {
                "success": False,
                "status": "URL_RETRIEVAL_STATUS_ERROR",
                "error": f"HTTP transport error: {str(exc)}",
                "text": "",
                "url": url
            }
        except Exception as exc:
            return {
                "success": False,
                "status": "URL_RETRIEVAL_STATUS_ERROR",
                "error": f"Unexpected retrieval failure: {str(exc)}",
                "text": "",
                "url": url
            }


safe_page_retriever = SafePageRetriever()
