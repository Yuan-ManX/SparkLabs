"""
SparkLabs Agent - Circuit Breaker

API resilience system with circuit breaking, rate limiting, and
adaptive backoff for external service calls. Protects agent
operations from cascading failures when downstream APIs degrade.

Architecture:
  CircuitBreaker
    |-- BreakerState (CLOSED, OPEN, HALF_OPEN)
    |-- FailureTracker (sliding window failure counting)
    |-- BackoffStrategy (exponential/jittered retry delay)
    |-- RateLimiter (token bucket per service endpoint)

States:
  - CLOSED: Normal operation — requests pass through
  - OPEN: Circuit tripped — requests fail fast
  - HALF_OPEN: Probing — limited requests test recovery

Usage:
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    
    # Wrap an API call
    result = cb.call(
        service="openai",
        func=lambda: client.chat.completions.create(...),
    )
    if result is None:
        print(f"Circuit open for openai: {cb.get_status('openai')}")
"""

from __future__ import annotations

import random
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple


class BreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ServiceStats:
    name: str = ""
    state: BreakerState = BreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    opened_at: float = 0.0
    total_requests: int = 0
    total_failures: int = 0
    avg_response_time_ms: float = 0.0


class RateLimiter:
    """Token bucket rate limiter for API call throttling."""

    def __init__(self, max_tokens: int = 100, refill_rate: float = 10.0):
        self._max_tokens = max_tokens
        self._tokens = float(max_tokens)
        self._refill_rate = refill_rate
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def try_acquire(self, tokens: float = 1.0) -> bool:
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    def available(self) -> float:
        self._refill()
        return self._tokens


class CircuitBreaker:
    """
    Circuit breaker with adaptive backoff for API resilience.

    Monitors service health across a sliding window, tripping
    the circuit on repeated failures. Supports automatic
    recovery probing with half-open state.

    Usage:
        cb = CircuitBreaker()
        
        def call_openai():
            return client.create(prompt)
        
        result = cb.call("openai", call_openai)
        if result is None:
            # Circuit is open — use fallback or retry later
            pass
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        recovery_timeout: float = 30.0,
        half_open_max_requests: int = 1,
        max_backoff: float = 120.0,
        base_delay: float = 1.0,
        jitter: float = 0.1,
        window_size: int = 60,
    ):
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max = half_open_max_requests
        self._max_backoff = max_backoff
        self._base_delay = base_delay
        self._jitter = jitter

        self._services: Dict[str, ServiceStats] = {}
        self._failure_windows: Dict[str, Deque[float]] = {}
        self._window_size = window_size
        self._rate_limiters: Dict[str, RateLimiter] = {}
        self._half_open_counters: Dict[str, int] = {}

        self._total_calls: int = 0
        self._total_failures: int = 0
        self._total_rejected: int = 0

    def register_service(
        self,
        name: str,
        max_rps: float = 10.0,
    ) -> None:
        self._services[name] = ServiceStats(name=name)
        self._failure_windows[name] = deque()
        self._rate_limiters[name] = RateLimiter(
            max_tokens=int(max_rps * 2),
            refill_rate=max_rps,
        )

    def call(
        self,
        service: str,
        func: Callable[[], Any],
        timeout: float = 30.0,
        fallback: Optional[Callable[[], Any]] = None,
    ) -> Any:
        self._total_calls += 1

        if service not in self._services:
            self.register_service(service)

        stats = self._services[service]
        limiter = self._rate_limiters.get(service)

        if limiter and not limiter.try_acquire():
            self._total_rejected += 1
            if fallback:
                return fallback()
            raise RateLimitError(f"Rate limit exceeded for {service}")

        if stats.state == BreakerState.OPEN:
            if time.time() - stats.opened_at < self._recovery_timeout:
                self._total_rejected += 1
                if fallback:
                    return fallback()
                raise CircuitOpenError(f"Circuit open for {service}")
            stats.state = BreakerState.HALF_OPEN
            self._half_open_counters[service] = 0

        if stats.state == BreakerState.HALF_OPEN:
            counter = self._half_open_counters.get(service, 0)
            if counter >= self._half_open_max:
                self._total_rejected += 1
                if fallback:
                    return fallback()
                raise CircuitOpenError(f"Half-open limit for {service}")
            self._half_open_counters[service] = counter + 1

        start = time.monotonic()
        try:
            result = func()
            elapsed = (time.monotonic() - start) * 1000.0
            self._on_success(service, elapsed)
            return result
        except Exception as e:
            self._on_failure(service)
            if fallback:
                return fallback()
            raise e

    def call_async(
        self,
        service: str,
        coro_func: Callable[[], Any],
        fallback: Optional[Callable[[], Any]] = None,
    ) -> Any:
        return self.call(service, coro_func, fallback=fallback)

    def get_status(self, service: str) -> dict:
        stats = self._services.get(service)
        if not stats:
            return {"error": "Unknown service"}
        limiter = self._rate_limiters.get(service)
        return {
            "service": service,
            "state": stats.state.value,
            "failures_current": self._count_window_failures(service),
            "consecutive_failures": stats.consecutive_failures,
            "consecutive_successes": stats.consecutive_successes,
            "total_requests": stats.total_requests,
            "total_failures": stats.total_failures,
            "avg_response_ms": round(stats.avg_response_time_ms, 2),
            "tokens_available": round(limiter.available(), 1) if limiter else 0,
        }

    def get_all_status(self) -> dict:
        return {
            "services": {s: self.get_status(s) for s in self._services},
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_rejected": self._total_rejected,
        }

    def force_open(self, service: str) -> None:
        self._ensure_service(service)
        self._services[service].state = BreakerState.OPEN
        self._services[service].opened_at = time.time()

    def force_close(self, service: str) -> None:
        self._ensure_service(service)
        self._services[service].state = BreakerState.CLOSED
        self._services[service].consecutive_failures = 0
        self._failure_windows[service].clear()

    def get_retry_delay(self, service: str, attempt: int) -> float:
        delay = min(
            self._base_delay * (2 ** attempt),
            self._max_backoff,
        )
        jitter_amount = delay * self._jitter * random.uniform(-1, 1)
        return max(0.0, delay + jitter_amount)

    def reset(self, service: str) -> None:
        self._ensure_service(service)
        stats = ServiceStats(name=service)
        self._services[service] = stats
        self._failure_windows[service] = deque()
        self._half_open_counters.pop(service, None)

    def clear(self) -> None:
        self._services.clear()
        self._failure_windows.clear()
        self._rate_limiters.clear()
        self._half_open_counters.clear()
        self._total_calls = 0
        self._total_failures = 0
        self._total_rejected = 0

    def get_stats(self) -> dict:
        return self.get_all_status()

    def get_state(self) -> BreakerState:
        for svc in self._services.values():
            return svc.state
        return BreakerState.CLOSED

    def _ensure_service(self, service: str) -> None:
        if service not in self._services:
            self.register_service(service)

    def _on_success(self, service: str, elapsed_ms: float) -> None:
        stats = self._services[service]
        stats.success_count += 1
        stats.total_requests += 1
        stats.consecutive_successes += 1
        stats.consecutive_failures = 0
        stats.last_success_time = time.time()

        if stats.state == BreakerState.HALF_OPEN:
            if stats.consecutive_successes >= self._success_threshold:
                stats.state = BreakerState.CLOSED
                self._failure_windows[service].clear()
                self._half_open_counters.pop(service, None)

        stats.avg_response_time_ms = (
            stats.avg_response_time_ms * (stats.total_requests - 1) + elapsed_ms
        ) / stats.total_requests

    def _on_failure(self, service: str) -> None:
        stats = self._services[service]
        stats.failure_count += 1
        stats.total_failures += 1
        stats.total_requests += 1
        stats.consecutive_failures += 1
        stats.consecutive_successes = 0
        stats.last_failure_time = time.time()
        self._total_failures += 1

        now = time.time()
        self._failure_windows[service].append(now)
        self._trim_window(service)

        if stats.state == BreakerState.CLOSED:
            recent = self._count_window_failures(service)
            if recent >= self._failure_threshold:
                stats.state = BreakerState.OPEN
                stats.opened_at = now

        elif stats.state == BreakerState.HALF_OPEN:
            stats.state = BreakerState.OPEN
            stats.opened_at = now
            self._half_open_counters.pop(service, None)

    def _count_window_failures(self, service: str) -> int:
        now = time.time()
        cutoff = now - self._window_size
        window = self._failure_windows.get(service, deque())
        return sum(1 for ts in window if ts >= cutoff)

    def _trim_window(self, service: str) -> None:
        now = time.time()
        cutoff = now - self._window_size * 2
        window = self._failure_windows.get(service, deque())
        while window and window[0] < cutoff:
            window.popleft()


class CircuitOpenError(Exception):
    pass


class RateLimitError(Exception):
    pass


_global_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    global _global_circuit_breaker
    if _global_circuit_breaker is None:
        _global_circuit_breaker = CircuitBreaker()
    return _global_circuit_breaker
