"""
SparkAI Agent - Error Classification Engine

A centralized error classification pipeline that produces structured
recovery hints for every error encountered in the agent runtime.
The classifier determines the correct recovery action based on
error patterns, HTTP status codes, and context-aware heuristics.
"""

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorCategory(Enum):
    AUTH = "auth"
    AUTH_PERMANENT = "auth_permanent"
    BILLING = "billing"
    RATE_LIMIT = "rate_limit"
    OVERLOADED = "overloaded"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    CONTEXT_OVERFLOW = "context_overflow"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    MODEL_NOT_FOUND = "model_not_found"
    PROVIDER_BLOCKED = "provider_blocked"
    FORMAT_ERROR = "format_error"
    NETWORK_ERROR = "network_error"
    TOOL_EXECUTION = "tool_execution"
    VALIDATION_ERROR = "validation_error"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    RETRY = "retry"
    RETRY_WITH_JITTER = "retry_with_jitter"
    COMPRESS_CONTEXT = "compress_context"
    ROTATE_CREDENTIAL = "rotate_credential"
    FALLBACK_PROVIDER = "fallback_provider"
    REBUILD_CLIENT = "rebuild_client"
    REDUCE_PAYLOAD = "reduce_payload"
    ABORT = "abort"
    ESCALATE = "escalate"
    WAIT_AND_RETRY = "wait_and_retry"
    SKIP = "skip"
    RESTART = "restart"


@dataclass
class RecoveryHints:
    should_retry: bool = False
    should_compress: bool = False
    should_rotate_credential: bool = False
    should_fallback: bool = False
    should_rebuild: bool = False
    should_reduce_payload: bool = False
    should_abort: bool = False
    should_escalate: bool = False
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    recovery_action: RecoveryAction = RecoveryAction.RETRY
    cooldown_seconds: float = 0.0
    diagnostic_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_retry": self.should_retry,
            "should_compress": self.should_compress,
            "should_rotate_credential": self.should_rotate_credential,
            "should_fallback": self.should_fallback,
            "should_rebuild": self.should_rebuild,
            "should_reduce_payload": self.should_reduce_payload,
            "should_abort": self.should_abort,
            "should_escalate": self.should_escalate,
            "max_retries": self.max_retries,
            "base_delay_seconds": self.base_delay_seconds,
            "max_delay_seconds": self.max_delay_seconds,
            "recovery_action": self.recovery_action.value,
            "cooldown_seconds": self.cooldown_seconds,
            "diagnostic_message": self.diagnostic_message,
        }


@dataclass
class ClassifiedError:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    category: ErrorCategory = ErrorCategory.UNKNOWN
    hints: RecoveryHints = field(default_factory=RecoveryHints)
    original_error: str = ""
    context_tokens: int = 0
    context_messages: int = 0
    provider: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "hints": self.hints.to_dict(),
            "original_error": self.original_error[:200],
            "context_tokens": self.context_tokens,
            "context_messages": self.context_messages,
            "provider": self.provider,
            "timestamp": self.timestamp,
        }


_RATE_LIMIT_PATTERNS = [
    r"rate.?limit",
    r"too many requests",
    r"request limit",
    r"throttl",
    r"quota exceeded",
    r"try again in \d+",
    r"resets at",
    r"retry.?after",
    r"RPM limit",
    r"TPM limit",
]

_BILLING_PATTERNS = [
    r"billing",
    r"payment",
    r"credit",
    r"subscription",
    r"plan limit",
    r"insufficient funds",
    r"invoice",
]

_AUTH_PATTERNS = [
    r"invalid api key",
    r"unauthorized",
    r"authentication failed",
    r"invalid token",
    r"token expired",
    r"access denied",
    r"forbidden",
    r"permission denied",
    r"invalid credentials",
]

_CONTEXT_OVERFLOW_PATTERNS = [
    r"context.?length",
    r"max.?tokens",
    r"token.?limit",
    r"context.?window",
    r"too many tokens",
    r"prompt.?too.?long",
    r"input.?too.?long",
    r"maximum context",
    r"content too large",
]

_OVERLOADED_PATTERNS = [
    r"overloaded",
    r"capacity",
    r"server is busy",
    r"service unavailable",
    r"temporarily unavailable",
    r"please try again later",
    r"high demand",
]

_NETWORK_PATTERNS = [
    r"connection.?reset",
    r"connection.?refused",
    r"connection.?timeout",
    r"ssl.?error",
    r"tls.?error",
    r"dns.?error",
    r"socket.?error",
    r"network.?error",
    r"eof occurred",
]


class ErrorClassifier:
    """
    Priority-ordered classification pipeline that determines
    the correct recovery action for every error.
    """

    def __init__(self):
        self._classification_count = 0
        self._by_category: Dict[str, int] = {}

    def classify(
        self,
        error: Exception,
        context_tokens: int = 0,
        context_messages: int = 0,
        provider: str = "",
        http_status: Optional[int] = None,
    ) -> ClassifiedError:
        error_str = str(error)
        error_lower = error_str.lower()

        classified = ClassifiedError(
            original_error=error_str,
            context_tokens=context_tokens,
            context_messages=context_messages,
            provider=provider,
        )

        if http_status:
            self._classify_by_status(classified, http_status, error_lower)
        else:
            self._classify_by_patterns(classified, error_lower, context_tokens, context_messages)

        self._classification_count += 1
        cat = classified.category.value
        self._by_category[cat] = self._by_category.get(cat, 0) + 1

        return classified

    def _classify_by_status(
        self,
        classified: ClassifiedError,
        status: int,
        error_lower: str,
    ) -> None:
        if status == 401:
            self._apply_auth(classified, permanent=False)
        elif status == 403:
            if any(p.search(error_lower) for p in [re.compile(r"billing|payment|credit", re.I)]):
                self._apply_billing(classified)
            else:
                self._apply_auth(classified, permanent=True)
        elif status == 402:
            if any(p.search(error_lower) for p in [re.compile(r"try again|resets at|retry", re.I)]):
                self._apply_rate_limit(classified, error_lower)
            else:
                self._apply_billing(classified)
        elif status == 429:
            self._apply_rate_limit(classified, error_lower)
        elif status == 400:
            if classified.context_tokens > 40000 or classified.context_messages > 80:
                self._apply_context_overflow(classified)
            else:
                self._apply_format_error(classified)
        elif status == 404:
            self._apply_model_not_found(classified)
        elif status == 413:
            self._apply_payload_too_large(classified)
        elif status == 500:
            self._apply_server_error(classified)
        elif status == 502 or status == 503:
            self._apply_overloaded(classified)
        elif status == 504:
            self._apply_timeout(classified)
        else:
            self._apply_unknown(classified)

    def _classify_by_patterns(
        self,
        classified: ClassifiedError,
        error_lower: str,
        context_tokens: int,
        context_messages: int,
    ) -> None:
        if self._matches(error_lower, _AUTH_PATTERNS):
            self._apply_auth(classified, "permanent" in error_lower or "invalid" in error_lower)
        elif self._matches(error_lower, _RATE_LIMIT_PATTERNS):
            self._apply_rate_limit(classified, error_lower)
        elif self._matches(error_lower, _BILLING_PATTERNS):
            self._apply_billing(classified)
        elif self._matches(error_lower, _CONTEXT_OVERFLOW_PATTERNS):
            self._apply_context_overflow(classified)
        elif self._matches(error_lower, _OVERLOADED_PATTERNS):
            self._apply_overloaded(classified)
        elif self._matches(error_lower, _NETWORK_PATTERNS):
            self._apply_network_error(classified)
        elif "timeout" in error_lower or "timed out" in error_lower:
            self._apply_timeout(classified)
        elif context_tokens > 40000 or context_messages > 80:
            self._apply_context_overflow(classified)
        elif "tool" in error_lower and ("execute" in error_lower or "fail" in error_lower):
            self._apply_tool_execution(classified)
        elif "validation" in error_lower or "invalid" in error_lower:
            self._apply_validation_error(classified)
        else:
            self._apply_unknown(classified)

    def _matches(self, text: str, patterns: List[str]) -> bool:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _apply_auth(self, classified: ClassifiedError, permanent: bool = False) -> None:
        classified.category = ErrorCategory.AUTH_PERMANENT if permanent else ErrorCategory.AUTH
        classified.hints = RecoveryHints(
            should_rotate_credential=True,
            should_retry=not permanent,
            should_abort=permanent,
            max_retries=1 if not permanent else 0,
            recovery_action=RecoveryAction.ROTATE_CREDENTIAL if not permanent else RecoveryAction.ABORT,
            diagnostic_message="Auth failure: rotate credential" if not permanent else "Permanent auth failure: abort",
        )

    def _apply_billing(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.BILLING
        classified.hints = RecoveryHints(
            should_rotate_credential=True,
            should_fallback=True,
            should_retry=True,
            max_retries=1,
            recovery_action=RecoveryAction.ROTATE_CREDENTIAL,
            diagnostic_message="Billing error: rotate to different credential",
        )

    def _apply_rate_limit(self, classified: ClassifiedError, error_lower: str) -> None:
        classified.category = ErrorCategory.RATE_LIMIT
        cooldown = self._extract_cooldown(error_lower)
        classified.hints = RecoveryHints(
            should_retry=True,
            should_rotate_credential=True,
            max_retries=3,
            base_delay_seconds=2.0,
            max_delay_seconds=60.0,
            cooldown_seconds=cooldown,
            recovery_action=RecoveryAction.WAIT_AND_RETRY,
            diagnostic_message=f"Rate limited: wait {cooldown}s or rotate credential",
        )

    def _apply_context_overflow(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.CONTEXT_OVERFLOW
        classified.hints = RecoveryHints(
            should_compress=True,
            should_retry=True,
            should_reduce_payload=True,
            max_retries=2,
            base_delay_seconds=0.5,
            recovery_action=RecoveryAction.COMPRESS_CONTEXT,
            diagnostic_message="Context overflow: compress before retry",
        )

    def _apply_overloaded(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.OVERLOADED
        classified.hints = RecoveryHints(
            should_retry=True,
            should_fallback=True,
            max_retries=3,
            base_delay_seconds=5.0,
            max_delay_seconds=120.0,
            recovery_action=RecoveryAction.RETRY_WITH_JITTER,
            diagnostic_message="Provider overloaded: retry with backoff or fallback",
        )

    def _apply_server_error(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.SERVER_ERROR
        classified.hints = RecoveryHints(
            should_retry=True,
            should_fallback=True,
            max_retries=2,
            base_delay_seconds=3.0,
            recovery_action=RecoveryAction.RETRY_WITH_JITTER,
            diagnostic_message="Server error: retry with backoff",
        )

    def _apply_timeout(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.TIMEOUT
        classified.hints = RecoveryHints(
            should_retry=True,
            should_rebuild=True,
            max_retries=2,
            base_delay_seconds=2.0,
            recovery_action=RecoveryAction.REBUILD_CLIENT,
            diagnostic_message="Timeout: rebuild client and retry",
        )

    def _apply_model_not_found(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.MODEL_NOT_FOUND
        classified.hints = RecoveryHints(
            should_fallback=True,
            should_retry=True,
            max_retries=1,
            recovery_action=RecoveryAction.FALLBACK_PROVIDER,
            diagnostic_message="Model not found: fallback to different model",
        )

    def _apply_payload_too_large(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.PAYLOAD_TOO_LARGE
        classified.hints = RecoveryHints(
            should_compress=True,
            should_reduce_payload=True,
            should_retry=True,
            max_retries=2,
            recovery_action=RecoveryAction.REDUCE_PAYLOAD,
            diagnostic_message="Payload too large: compress and reduce before retry",
        )

    def _apply_format_error(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.FORMAT_ERROR
        classified.hints = RecoveryHints(
            should_retry=True,
            max_retries=1,
            recovery_action=RecoveryAction.RETRY,
            diagnostic_message="Format error: retry with stripped payload",
        )

    def _apply_network_error(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.NETWORK_ERROR
        classified.hints = RecoveryHints(
            should_retry=True,
            should_rebuild=True,
            max_retries=3,
            base_delay_seconds=1.0,
            recovery_action=RecoveryAction.REBUILD_CLIENT,
            diagnostic_message="Network error: rebuild client and retry",
        )

    def _apply_tool_execution(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.TOOL_EXECUTION
        classified.hints = RecoveryHints(
            should_retry=True,
            max_retries=2,
            base_delay_seconds=1.0,
            recovery_action=RecoveryAction.RETRY_WITH_JITTER,
            diagnostic_message="Tool execution error: retry with backoff",
        )

    def _apply_validation_error(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.VALIDATION_ERROR
        classified.hints = RecoveryHints(
            should_abort=True,
            should_escalate=True,
            recovery_action=RecoveryAction.ESCALATE,
            diagnostic_message="Validation error: escalate for review",
        )

    def _apply_resource_exhausted(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.RESOURCE_EXHAUSTED
        classified.hints = RecoveryHints(
            should_retry=True,
            max_retries=3,
            base_delay_seconds=5.0,
            max_delay_seconds=120.0,
            recovery_action=RecoveryAction.WAIT_AND_RETRY,
            diagnostic_message="Resource exhausted: wait and retry",
        )

    def _apply_provider_blocked(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.PROVIDER_BLOCKED
        classified.hints = RecoveryHints(
            should_abort=True,
            should_escalate=True,
            recovery_action=RecoveryAction.ESCALATE,
            diagnostic_message="Provider policy blocked: escalate to user",
        )

    def _apply_unknown(self, classified: ClassifiedError) -> None:
        classified.category = ErrorCategory.UNKNOWN
        classified.hints = RecoveryHints(
            should_retry=True,
            max_retries=2,
            base_delay_seconds=2.0,
            recovery_action=RecoveryAction.RETRY_WITH_JITTER,
            diagnostic_message="Unknown error: retry with jittered backoff",
        )

    def _extract_cooldown(self, error_lower: str) -> float:
        match = re.search(r"try again in (\d+(?:\.\d+)?)\s*(s|sec|second|min|minute|m|h|hour)?", error_lower)
        if match:
            value = float(match.group(1))
            unit = (match.group(2) or "s").lower()
            if unit.startswith("m") and not unit.startswith("mi"):
                value *= 60.0
            elif unit.startswith("min"):
                value *= 60.0
            elif unit.startswith("h"):
                value *= 3600.0
            return value

        match = re.search(r"resets? at (\d+)", error_lower)
        if match:
            reset_at = float(match.group(1))
            now = time.time()
            if reset_at > now:
                return min(reset_at - now, 3600.0)

        match = re.search(r"retry.?after[:\s]*(\d+(?:\.\d+)?)", error_lower)
        if match:
            return float(match.group(1))

        return 30.0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_classifications": self._classification_count,
            "by_category": dict(self._by_category),
        }


_global_classifier: Optional[ErrorClassifier] = None


def get_error_classifier() -> ErrorClassifier:
    global _global_classifier
    if _global_classifier is None:
        _global_classifier = ErrorClassifier()
    return _global_classifier


def reset_error_classifier() -> None:
    global _global_classifier
    _global_classifier = None
