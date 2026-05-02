"""
Retry System - Intelligent retry with circuit breaker pattern.

Architecture:
    RetrySystem/
    |-- RetryStrategy (backoff algorithm selection)
    |-- RetryConfig (per-operation retry configuration)
    |-- CircuitBreaker (failure-tracking circuit breaker)
    |-- RetryContext (execution context for retry tracking)
    |-- RetrySystem (unified retry orchestration)

Provides intelligent retry with exponential backoff, jitter,
circuit breaker protection, and error classification for agent operations.
"""

from __future__ import annotations

import random
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type


class RetryStrategy(Enum):
    EXPONENTIAL = auto()
    LINEAR = auto()
    CONSTANT = auto()
    EXPONENTIAL_JITTER = auto()
    DECORRELATED_JITTER = auto()


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


@dataclass
class RetryConfig:
    operation: str
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    jitter_factor: float = 0.1
    retryable_errors: Set[str] = field(default_factory=lambda: {
        "rate_limit", "timeout", "connection_error", "server_error",
        "service_unavailable", "temporary_failure"
    })
    non_retryable_errors: Set[str] = field(default_factory=lambda: {
        "auth_error", "invalid_request", "not_found", "permission_denied",
        "quota_exceeded", "content_filter"
    })
    circuit_breaker_enabled: bool = True
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout: float = 30.0


class CircuitBreaker:
    """Failure-tracking circuit breaker for operation protection."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.state = CircuitState.CLOSED
        self._lock = threading.Lock()

    def on_success(self) -> None:
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= 2:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def on_failure(self) -> None:
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    def allow_request(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                elapsed = time.monotonic() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    return True
                return False
            return True

    def reset(self) -> None:
        with self._lock:
            self.failure_count = 0
            self.success_count = 0
            self.state = CircuitState.CLOSED


@dataclass
class RetryContext:
    operation: str
    attempt: int = 0
    total_elapsed: float = 0.0
    last_error: Optional[str] = None
    last_error_type: Optional[str] = None
    next_delay: float = 0.0


class RetrySystem:
    """Intelligent retry orchestration with circuit breaker protection."""

    _instance: Optional["RetrySystem"] = None

    def __init__(self):
        self._configs: Dict[str, RetryConfig] = {}
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._retry_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self._total_retries = 0
        self._total_failures = 0
        self._total_successes = 0

    @classmethod
    def get_instance(cls) -> "RetrySystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_operation(self, config: RetryConfig) -> None:
        self._configs[config.operation] = config
        self._breakers[config.operation] = CircuitBreaker(
            config.circuit_failure_threshold,
            config.circuit_recovery_timeout,
        )

    def register_defaults(self) -> None:
        defaults = [
            RetryConfig("llm_call", max_retries=5, base_delay=2.0, max_delay=120.0,
                        strategy=RetryStrategy.EXPONENTIAL_JITTER),
            RetryConfig("tool_call", max_retries=3, base_delay=1.0, max_delay=30.0),
            RetryConfig("web_fetch", max_retries=3, base_delay=1.0, max_delay=30.0),
            RetryConfig("file_read", max_retries=3, base_delay=0.5, max_delay=10.0),
            RetryConfig("file_write", max_retries=2, base_delay=1.0, max_delay=15.0),
            RetryConfig("skill_execute", max_retries=2, base_delay=1.0, max_delay=15.0),
        ]
        for d in defaults:
            self.register_operation(d)

    def compute_delay(self, config: RetryConfig, attempt: int) -> float:
        if config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.base_delay * (2 ** (attempt - 1))
        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.base_delay * attempt
        elif config.strategy == RetryStrategy.CONSTANT:
            delay = config.base_delay
        elif config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            delay = config.base_delay * (2 ** (attempt - 1))
            jitter = random.uniform(0, config.jitter_factor * delay)
            delay = delay + jitter
        elif config.strategy == RetryStrategy.DECORRELATED_JITTER:
            delay = random.uniform(config.base_delay,
                                   config.base_delay * 3 * (2 ** (attempt - 1)))
        else:
            delay = config.base_delay

        return min(delay, config.max_delay)

    def should_retry(self, operation: str, error_type: str) -> Tuple[bool, str]:
        config = self._configs.get(operation)
        if not config:
            return False, "No config for operation"

        if error_type in config.non_retryable_errors:
            return False, f"Non-retryable error: {error_type}"

        if error_type not in config.retryable_errors:
            return True, ""

        return True, ""

    def execute(self, operation: str, fn: Callable, *args, **kwargs) -> Any:
        config = self._configs.get(operation)
        breaker = self._breakers.get(operation)

        if not config:
            return fn(*args, **kwargs)

        if breaker and not breaker.allow_request():
            self._total_failures += 1
            raise RuntimeError(f"Circuit breaker open for operation '{operation}'")

        start_time = time.monotonic()

        for attempt in range(1, config.max_retries + 2):
            try:
                result = fn(*args, **kwargs)
                if breaker:
                    breaker.on_success()
                self._total_successes += 1
                return result

            except Exception as e:
                error_type = self._classify_error(e)
                elapsed = time.monotonic() - start_time

                if breaker:
                    breaker.on_failure()

                self._retry_counts[operation][attempt] += 1

                if attempt > config.max_retries:
                    self._total_failures += 1
                    raise

                should_retry, reason = self.should_retry(operation, error_type)
                if not should_retry:
                    self._total_failures += 1
                    raise

                delay = self.compute_delay(config, attempt)
                self._total_retries += 1
                time.sleep(delay)

        self._total_failures += 1
        raise RuntimeError(f"All retries exhausted for '{operation}'")

    def _classify_error(self, error: Exception) -> str:
        error_str = str(error).lower()
        type_name = type(error).__name__

        if "rate" in error_str or "limit" in error_str or "429" in error_str:
            return "rate_limit"
        if "timeout" in error_str or "timed out" in error_str:
            return "timeout"
        if "auth" in error_str or "unauthorized" in error_str:
            return "auth_error"
        if "invalid" in error_str or "bad request" in error_str:
            return "invalid_request"
        if "not found" in error_str or "404" in error_str:
            return "not_found"
        if "permission" in error_str or "forbidden" in error_str:
            return "permission_denied"
        if "connection" in error_str or "refused" in error_str:
            return "connection_error"
        if "500" in error_str or "internal" in error_str:
            return "server_error"
        if "unavailable" in error_str or "503" in error_str:
            return "service_unavailable"
        if "quota" in error_str:
            return "quota_exceeded"

        return "temporary_failure"

    def get_circuit_state(self, operation: str) -> Optional[str]:
        breaker = self._breakers.get(operation)
        return breaker.state.name.lower() if breaker else None

    def list_operations(self) -> List[Dict[str, Any]]:
        return [{
            "operation": c.operation,
            "max_retries": c.max_retries,
            "strategy": c.strategy.name.lower(),
            "retryable_count": len(c.retryable_errors),
            "non_retryable_count": len(c.non_retryable_errors),
            "circuit_state": self.get_circuit_state(c.operation),
        } for c in self._configs.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_retries": self._total_retries,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "operations_count": len(self._configs),
            "success_rate": (self._total_successes / max(1, self._total_successes + self._total_failures) * 100),
            "retry_rate": (self._total_retries / max(1, self._total_successes) * 100),
            "open_circuits": sum(1 for b in self._breakers.values()
                               if b.state == CircuitState.OPEN),
        }

    def reset(self) -> None:
        for breaker in self._breakers.values():
            breaker.reset()
        self._retry_counts.clear()
        self._total_retries = 0
        self._total_failures = 0
        self._total_successes = 0


def get_retry_system() -> RetrySystem:
    return RetrySystem.get_instance()
