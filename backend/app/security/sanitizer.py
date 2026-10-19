import re
import ipaddress
from urllib.parse import urlparse, urlunparse

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword"
}

def is_safe_url(url: str) -> bool:
    """
    Checks if a URL is safe to retrieve (protecting against SSRF, loopback, private networks).
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Deny localhost and local domains
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False
        if hostname.lower().endswith((".local", ".internal", ".localhost")):
            return False
            
        # Check IP ranges
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        except ValueError:
            # It is a hostname, not a raw IP
            pass
            
        return True
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """
    Normalizes a URL by removing trailing slashes, fragments, and tracking parameters.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        # Strip trailing slash from path if length > 1
        path = parsed.path.lower().rstrip("/")
        # Filter out tracking query params like utm_*
        query_parts = []
        if parsed.query:
            for param in parsed.query.split("&"):
                if not param.lower().startswith(("utm_", "fbclid=", "gclid=")):
                    query_parts.append(param)
        cleaned_query = "&".join(query_parts)
        
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.params,
            cleaned_query,
            "" # strip fragment
        ))
        return normalized
    except Exception:
        return url.strip()

def sanitize_text(text: str) -> str:
    """Sanitizes text to prevent XSS / control character injections while preserving readability."""
    if not text:
        return ""
    # Strip null bytes and non-printable control characters
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return cleaned.strip()

def validate_github_username(username: str) -> bool:
    """Validates GitHub username format."""
    if not username:
        return False
    # GitHub username: alphanumeric and single hyphens, max 39 chars
    return bool(re.match(r'^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$', username))
