"""
Web Browser - URL fetching and web content extraction agent.

Architecture:
    WebBrowser/
    |-- FetchMethod (HTTP method enumeration)
    |-- FetchResult (response container with metadata)
    |-- DomainPolicy (allowlist/denylist management)
    |-- ExtractionRule (content extraction configuration)
    |-- WebBrowser (unified web interaction orchestration)

Provides controlled URL fetching, content extraction (HTML→text),
domain safety filtering, result caching, and structured web access
for agent operations that require external information retrieval.
"""

from __future__ import annotations

import re
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class FetchMethod(Enum):
    GET = auto()
    HEAD = auto()


@dataclass
class FetchResult:
    url: str
    status_code: int = 0
    content: str = ""
    content_type: str = ""
    size_bytes: int = 0
    fetch_duration_ms: float = 0.0
    cached: bool = False
    error: Optional[str] = None
    extracted_text: str = ""
    title: Optional[str] = None
    links_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "duration_ms": self.fetch_duration_ms,
            "cached": self.cached,
            "error": self.error,
            "text_length": len(self.extracted_text),
            "title": self.title,
            "links_count": self.links_count,
            "text_preview": self.extracted_text[:500] if self.extracted_text else "",
        }


class DomainPolicy:
    """Allowlist/denylist domain safety filter."""

    def __init__(self):
        self._allowlist: Set[str] = set()
        self._denylist: Set[str] = set()
        self._allow_all: bool = False

    def set_allow_all(self, allow: bool) -> None:
        self._allow_all = allow

    def add_allow(self, domain: str) -> None:
        self._allowlist.add(domain.lower())

    def add_deny(self, domain: str) -> None:
        self._denylist.add(domain.lower())

    def is_allowed(self, url: str) -> Tuple[bool, str]:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            base_domain = ".".join(domain.split(".")[-2:]) if domain.count(".") > 1 else domain
        except Exception:
            return False, f"Invalid URL: {url}"

        for denied in self._denylist:
            if denied in base_domain or base_domain == denied:
                return False, f"Domain '{domain}' is denylisted"

        if self._allow_all:
            return True, ""

        for allowed in self._allowlist:
            if allowed in base_domain or base_domain == allowed:
                return True, ""

        return False, f"Domain '{domain}' is not in allowlist"

    def list_allow(self) -> List[str]:
        return sorted(self._allowlist)

    def list_deny(self) -> List[str]:
        return sorted(self._denylist)


HTML_TAGS_PATTERN = re.compile(r'<[^>]+>')
SCRIPT_STYLE_PATTERN = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.DOTALL | re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r'\s+')
TITLE_PATTERN = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE)
LINK_PATTERN = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)


class WebBrowser:
    """Controlled web interaction orchestration for agent use."""

    _instance: Optional["WebBrowser"] = None

    def __init__(self):
        self._policy = DomainPolicy()
        self._cache: Dict[str, FetchResult] = {}
        self._cache_ttl: float = 300.0
        self._max_content_size: int = 5 * 1024 * 1024
        self._default_timeout: float = 30.0
        self._total_fetches = 0
        self._total_cached = 0
        self._total_denied = 0
        self._total_errors = 0

        self._policy.set_allow_all(False)
        self._policy.add_allow("wikipedia.org")
        self._policy.add_allow("github.com")
        self._policy.add_allow("docs.python.org")
        self._policy.add_allow("developer.mozilla.org")
        self._policy.add_allow("stackoverflow.com")

    @classmethod
    def get_instance(cls) -> "WebBrowser":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def policy(self) -> DomainPolicy:
        return self._policy

    def fetch(self, url: str, timeout: Optional[float] = None,
              bypass_cache: bool = False) -> FetchResult:
        self._total_fetches += 1

        allowed, reason = self._policy.is_allowed(url)
        if not allowed:
            self._total_denied += 1
            return FetchResult(url=url, status_code=0, error=reason)

        cache_key = hashlib.md5(url.encode()).hexdigest()
        if not bypass_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            self._total_cached += 1
            return FetchResult(
                url=url, status_code=cached.status_code,
                content=cached.content, content_type=cached.content_type,
                size_bytes=cached.size_bytes, cached=True,
                extracted_text=cached.extracted_text,
                title=cached.title, links_count=cached.links_count,
            )

        fetch_timeout = timeout or self._default_timeout
        start = time.monotonic()

        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(
                url, headers={
                    "User-Agent": "SparkLabs-Agent/2.0",
                    "Accept": "text/html,application/xhtml+xml,*/*",
                }
            )

            with urllib.request.urlopen(req, timeout=fetch_timeout) as response:
                status_code = response.status
                content_type = response.headers.get("Content-Type", "text/html")
                raw = response.read(self._max_content_size)
                content = raw.decode("utf-8", errors="replace")
                size_bytes = len(raw)

            duration = (time.monotonic() - start) * 1000

            extracted = self._extract_text(content)
            title = self._extract_title(content)
            links = len(LINK_PATTERN.findall(content))

            result = FetchResult(
                url=url, status_code=status_code, content=content,
                content_type=content_type, size_bytes=size_bytes,
                fetch_duration_ms=duration, extracted_text=extracted,
                title=title, links_count=links,
            )

            self._cache[cache_key] = result
            return result

        except urllib.error.HTTPError as e:
            self._total_errors += 1
            return FetchResult(url=url, status_code=e.code,
                             error=f"HTTP {e.code}: {e.reason}",
                             fetch_duration_ms=(time.monotonic() - start) * 1000)
        except urllib.error.URLError as e:
            self._total_errors += 1
            return FetchResult(url=url, status_code=0,
                             error=f"URL Error: {e.reason}",
                             fetch_duration_ms=(time.monotonic() - start) * 1000)
        except Exception as e:
            self._total_errors += 1
            return FetchResult(url=url, status_code=0,
                             error=str(e),
                             fetch_duration_ms=(time.monotonic() - start) * 1000)

    def _extract_text(self, html: str) -> str:
        cleaned = SCRIPT_STYLE_PATTERN.sub("", html)
        text_only = HTML_TAGS_PATTERN.sub(" ", cleaned)
        text_only = WHITESPACE_PATTERN.sub(" ", text_only)
        return text_only.strip()

    def _extract_title(self, html: str) -> Optional[str]:
        match = TITLE_PATTERN.search(html)
        if match:
            return match.group(1).strip()[:200]
        return None

    def fetch_text(self, url: str, timeout: Optional[float] = None) -> str:
        result = self.fetch(url, timeout=timeout)
        if result.error:
            return f"[Error fetching {url}: {result.error}]"
        if result.extracted_text:
            return result.extracted_text
        return f"[No text content from {url}]"

    def search_summary(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        results = []
        for url, cached in list(self._cache.items())[:10]:
            decoded_url = cached.url
            if query.lower() in decoded_url.lower() or query.lower() in cached.extracted_text.lower()[:500]:
                results.append({
                    "url": decoded_url,
                    "title": cached.title,
                    "preview": cached.extracted_text[:200] if cached.extracted_text else "",
                })
                if len(results) >= max_results:
                    break
        return results

    def clear_cache(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count

    def set_cache_ttl(self, ttl: float) -> None:
        self._cache_ttl = ttl

    def add_allowed_domain(self, domain: str) -> None:
        self._policy.add_allow(domain)

    def add_denied_domain(self, domain: str) -> None:
        self._policy.add_deny(domain)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_fetches": self._total_fetches,
            "cached_hits": self._total_cached,
            "denied": self._total_denied,
            "errors": self._total_errors,
            "cache_size": len(self._cache),
            "cache_ttl": self._cache_ttl,
            "allowed_domains": len(self._policy._allowlist),
            "denied_domains": len(self._policy._denylist),
            "success_rate": ((self._total_fetches - self._total_errors - self._total_denied)
                           / max(1, self._total_fetches) * 100),
        }

    def reset(self) -> None:
        self._cache.clear()
        self._total_fetches = 0
        self._total_cached = 0
        self._total_denied = 0
        self._total_errors = 0


def get_web_browser() -> WebBrowser:
    return WebBrowser.get_instance()
