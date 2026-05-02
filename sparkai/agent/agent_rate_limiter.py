"""
Rate Limiter - Token bucket and sliding window rate limiting.

Architecture:
    RateLimiter/
    |-- LimitStrategy (rate limiting algorithm selection)
    |-- RateLimitConfig (per-endpoint limit configuration)
    |-- TokenBucket (token bucket algorithm implementation)
    |-- SlidingWindow (sliding window counter implementation)
    |-- RateLimiter (unified rate limiting orchestrator)

Provides multi-strategy rate limiting for API calls with burst support,
concurrent call capping, and wait queue management for agent operations.
"""

from __future__ import annotations

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class LimitStrategy(Enum):
    TOKEN_BUCKET = auto()
    SLIDING_WINDOW = auto()
    CONCURRENT_CAP = auto()
    LEAKY_BUCKET = auto()


@dataclass
class RateLimitConfig:
    endpoint: str
    strategy: LimitStrategy = LimitStrategy.TOKEN_BUCKET
    max_requests: int = 60
    window_seconds: float = 60.0
    burst_size: int = 10
    max_concurrent: int = 5
    enabled: bool = True


class TokenBucket:
    """Token bucket rate limiting algorithm."""

    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    @property
    def available_tokens(self) -> float:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            return min(self.burst, self.tokens + elapsed * self.rate)


class SlidingWindow:
    """Sliding window counter implementation."""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: List[float] = []
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            self._timestamps = [t for t in self._timestamps if t > cutoff]

            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(now)
                return True
            return False

    @property
    def current_count(self) -> int:
        with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            self._timestamps = [t for t in self._timestamps if t > cutoff]
            return len(self._timestamps)

    @property
    def remaining(self) -> int:
        return max(0, self.max_requests - self.current_count)


class ConcurrentCap:
    """Concurrent request capping."""

    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self._active: Set[str] = set()
        self._lock = threading.Lock()

    def acquire(self, request_id: str) -> bool:
        with self._lock:
            if len(self._active) < self.max_concurrent:
                self._active.add(request_id)
                return True
            return False

    def release(self, request_id: str) -> None:
        with self._lock:
            self._active.discard(request_id)

    @property
    def active_count(self) -> int:
        return len(self._active)


class RateLimiter:
    """Unified rate limiting orchestrator with multiple strategies."""

    _instance: Optional["RateLimiter"] = None

    def __init__(self):
        self._configs: Dict[str, RateLimitConfig] = {}
        self._buckets: Dict[str, TokenBucket] = {}
        self._windows: Dict[str, SlidingWindow] = {}
        self._caps: Dict[str, ConcurrentCap] = {}
        self._total_allowed = 0
        self._total_denied = 0
        self._wait_queue: List[Any] = []

    @classmethod
    def get_instance(cls) -> "RateLimiter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_endpoint(self, config: RateLimitConfig) -> None:
        self._configs[config.endpoint] = config
        if config.strategy == LimitStrategy.TOKEN_BUCKET:
            rate = config.max_requests / config.window_seconds
            self._buckets[config.endpoint] = TokenBucket(rate, config.burst_size)
        elif config.strategy == LimitStrategy.SLIDING_WINDOW:
            self._windows[config.endpoint] = SlidingWindow(
                config.max_requests, config.window_seconds)
        elif config.strategy == LimitStrategy.CONCURRENT_CAP:
            self._caps[config.endpoint] = ConcurrentCap(config.max_concurrent)

    def register_defaults(self) -> None:
        defaults = [
            RateLimitConfig("llm_completion", LimitStrategy.TOKEN_BUCKET, 60, 60, 10, 5),
            RateLimitConfig("llm_embedding", LimitStrategy.TOKEN_BUCKET, 120, 60, 20, 10),
            RateLimitConfig("tool_execution", LimitStrategy.SLIDING_WINDOW, 100, 60, 20, 10),
            RateLimitConfig("web_fetch", LimitStrategy.SLIDING_WINDOW, 30, 60, 5, 3),
            RateLimitConfig("file_operation", LimitStrategy.SLIDING_WINDOW, 200, 60, 50, 10),
            RateLimitConfig("session_create", LimitStrategy.TOKEN_BUCKET, 10, 60, 3, 5),
            RateLimitConfig("concurrent_tasks", LimitStrategy.CONCURRENT_CAP, 0, 0, 0, 20),
        ]
        for d in defaults:
            self.register_endpoint(d)

    def allow(self, endpoint: str, request_id: str = "", tokens: int = 1) -> Tuple[bool, str]:
        config = self._configs.get(endpoint)
        if not config or not config.enabled:
            self._total_allowed += 1
            return True, ""

        if config.strategy == LimitStrategy.TOKEN_BUCKET:
            bucket = self._buckets.get(endpoint)
            if bucket and bucket.consume(tokens):
                self._total_allowed += 1
                return True, ""
            self._total_denied += 1
            return False, f"Token bucket exhausted for '{endpoint}'"

        elif config.strategy == LimitStrategy.SLIDING_WINDOW:
            window = self._windows.get(endpoint)
            if window and window.allow():
                self._total_allowed += 1
                return True, ""
            self._total_denied += 1
            return False, f"Sliding window limit reached for '{endpoint}'"

        elif config.strategy == LimitStrategy.CONCURRENT_CAP:
            cap = self._caps.get(endpoint)
            if cap and cap.acquire(request_id):
                self._total_allowed += 1
                return True, ""
            self._total_denied += 1
            return False, f"Concurrent cap reached for '{endpoint}'"

        self._total_allowed += 1
        return True, ""

    def release(self, endpoint: str, request_id: str) -> None:
        config = self._configs.get(endpoint)
        if config and config.strategy == LimitStrategy.CONCURRENT_CAP:
            cap = self._caps.get(endpoint)
            if cap:
                cap.release(request_id)

    def get_remaining(self, endpoint: str) -> Optional[int]:
        config = self._configs.get(endpoint)
        if not config:
            return None
        if config.strategy == LimitStrategy.TOKEN_BUCKET:
            bucket = self._buckets.get(endpoint)
            return int(bucket.available_tokens) if bucket else None
        elif config.strategy == LimitStrategy.SLIDING_WINDOW:
            window = self._windows.get(endpoint)
            return window.remaining if window else None
        elif config.strategy == LimitStrategy.CONCURRENT_CAP:
            cap = self._caps.get(endpoint)
            return cap.max_concurrent - cap.active_count if cap else None
        return None

    def get_active_count(self, endpoint: str) -> int:
        cap = self._caps.get(endpoint)
        return cap.active_count if cap else 0

    def list_endpoints(self) -> List[Dict[str, Any]]:
        return [{
            "endpoint": c.endpoint,
            "strategy": c.strategy.name.lower(),
            "max_requests": c.max_requests,
            "window_seconds": c.window_seconds,
            "remaining": self.get_remaining(c.endpoint),
            "enabled": c.enabled,
        } for c in self._configs.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_allowed": self._total_allowed,
            "total_denied": self._total_denied,
            "endpoints": len(self._configs),
            "deny_rate": (self._total_denied / max(1, self._total_allowed + self._total_denied) * 100),
            "active_concurrent": sum(c.active_count for c in self._caps.values()),
        }

    def reset(self) -> None:
        self._buckets.clear()
        self._windows.clear()
        self._caps.clear()
        self._total_allowed = 0
        self._total_denied = 0


def get_rate_limiter() -> RateLimiter:
    return RateLimiter.get_instance()
