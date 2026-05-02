"""
Budget Tracker - Token and cost budget management for AI-native game development.

Architecture:
    BudgetTracker/
    |-- BudgetScope (per-session, daily, monthly enumeration)
    |-- BudgetLimit (threshold configuration dataclass)
    |-- BudgetUsage (consumed resources dataclass)
    |-- BudgetAlert (warning/block configuration dataclass)
    |-- BudgetTracker (global budget orchestration)

Tracks LLM token consumption and estimated costs during game development
sessions. Enforces configurable budgets with warning thresholds and hard
caps to prevent runaway spending. Supports per-session, daily, and total
budget scopes.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable


class BudgetScope(Enum):
    PER_SESSION = auto()
    DAILY = auto()
    MONTHLY = auto()
    TOTAL = auto()


class AlertLevel(Enum):
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()
    BLOCKED = auto()


@dataclass
class BudgetLimit:
    scope: BudgetScope = BudgetScope.PER_SESSION
    max_tokens: int = 100000
    max_cost_cents: int = 500
    warn_at_percent: float = 0.8
    block_at_percent: float = 0.95
    reset_period_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope.name,
            "max_tokens": self.max_tokens,
            "max_cost_cents": self.max_cost_cents,
            "warn_at_pct": self.warn_at_percent,
            "block_at_pct": self.block_at_percent,
        }


@dataclass
class BudgetUsage:
    scope: BudgetScope = BudgetScope.PER_SESSION
    session_id: str = ""
    tokens_used: int = 0
    cost_cents: int = 0
    requests: int = 0
    last_updated: float = 0.0
    model_breakdown: Dict[str, int] = field(default_factory=dict)

    def token_usage_percent(self, limit: BudgetLimit) -> float:
        if limit.max_tokens <= 0:
            return 0.0
        return self.tokens_used / limit.max_tokens

    def cost_usage_percent(self, limit: BudgetLimit) -> float:
        if limit.max_cost_cents <= 0:
            return 0.0
        return self.cost_cents / limit.max_cost_cents

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope.name,
            "session_id": self.session_id,
            "tokens_used": self.tokens_used,
            "cost_cents": self.cost_cents,
            "requests": self.requests,
            "models": self.model_breakdown,
        }


@dataclass
class BudgetAlert:
    alert_id: str = ""
    level: AlertLevel = AlertLevel.INFO
    scope: BudgetScope = BudgetScope.PER_SESSION
    message: str = ""
    timestamp: float = 0.0
    tokens_used: int = 0
    tokens_limit: int = 0
    percent_used: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.name,
            "scope": self.scope.name,
            "message": self.message,
            "tokens_used": self.tokens_used,
            "tokens_limit": self.tokens_limit,
            "percent_used": round(self.percent_used * 100, 1),
        }


class BudgetTracker:
    _instance: Optional["BudgetTracker"] = None
    _COST_PER_1K_TOKENS_INPUT = 0.003
    _COST_PER_1K_TOKENS_OUTPUT = 0.015
    _MIN_TOKENS_PER_SECOND = 10

    def __init__(self):
        self._limits: Dict[BudgetScope, BudgetLimit] = {}
        self._usage: Dict[str, BudgetUsage] = {}
        self._alerts: List[BudgetAlert] = []
        self._alert_callbacks: List[Callable[[BudgetAlert], None]] = []
        self._enabled: bool = True
        self._lock = threading.Lock()
        self._register_default_limits()

    def _register_default_limits(self) -> None:
        self._limits[BudgetScope.PER_SESSION] = BudgetLimit(
            scope=BudgetScope.PER_SESSION,
            max_tokens=200000,
            max_cost_cents=500,
            warn_at_percent=0.7,
            block_at_percent=0.9,
        )
        self._limits[BudgetScope.DAILY] = BudgetLimit(
            scope=BudgetScope.DAILY,
            max_tokens=1000000,
            max_cost_cents=3000,
            warn_at_percent=0.8,
            block_at_percent=0.95,
            reset_period_seconds=86400,
        )

    @classmethod
    def get_instance(cls) -> "BudgetTracker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_limit(self, scope: BudgetScope, limit: BudgetLimit) -> None:
        self._limits[scope] = limit

    def get_limit(self, scope: BudgetScope) -> Optional[BudgetLimit]:
        return self._limits.get(scope)

    def can_proceed(self, session_id: str, estimated_tokens: int = 100) -> bool:
        if not self._enabled:
            return True

        for scope in [BudgetScope.PER_SESSION, BudgetScope.DAILY, BudgetScope.TOTAL]:
            limit = self._limits.get(scope)
            if not limit:
                continue

            usage_key = self._usage_key(scope, session_id)
            usage = self._usage.get(usage_key)
            if not usage:
                continue

            if usage.tokens_used >= limit.max_tokens * limit.block_at_percent:
                return False
            if usage.cost_cents >= limit.max_cost_cents * limit.block_at_percent:
                return False

        return True

    def record_usage(self, session_id: str, tokens_input: int = 0, tokens_output: int = 0,
                     model: str = "") -> Dict[BudgetScope, AlertLevel]:
        if not self._enabled:
            return {}

        cost = self._estimate_cost(tokens_input, tokens_output)
        alerts: Dict[BudgetScope, AlertLevel] = {}

        for scope in [BudgetScope.PER_SESSION, BudgetScope.DAILY, BudgetScope.TOTAL]:
            limit = self._limits.get(scope)
            if not limit:
                continue

            usage_key = self._usage_key(scope, session_id)
            with self._lock:
                if usage_key not in self._usage:
                    self._usage[usage_key] = BudgetUsage(
                        scope=scope,
                        session_id=session_id,
                    )
                usage = self._usage[usage_key]
                usage.tokens_used += tokens_input + tokens_output
                usage.cost_cents += cost
                usage.requests += 1
                usage.last_updated = time.time()
                if model:
                    usage.model_breakdown[model] = (
                        usage.model_breakdown.get(model, 0) + tokens_input + tokens_output
                    )

            usage_pct = max(usage.token_usage_percent(limit), usage.cost_usage_percent(limit))
            level = AlertLevel.INFO

            if usage_pct >= limit.block_at_percent:
                level = AlertLevel.BLOCKED
            elif usage_pct >= limit.warn_at_percent:
                level = AlertLevel.WARNING
            elif usage_pct >= 0.9:
                level = AlertLevel.CRITICAL

            if level != AlertLevel.INFO:
                alert = BudgetAlert(
                    alert_id=f"{scope.name}_{int(time.time())}",
                    level=level,
                    scope=scope,
                    message=f"{scope.name} budget at {usage_pct*100:.1f}%",
                    timestamp=time.time(),
                    tokens_used=usage.tokens_used,
                    tokens_limit=limit.max_tokens,
                    percent_used=usage_pct,
                )
                self._alerts.append(alert)
                self._notify_callbacks(alert)

            alerts[scope] = level

        return alerts

    def get_session_usage(self, session_id: str, scope: BudgetScope = BudgetScope.PER_SESSION) -> Optional[BudgetUsage]:
        usage_key = self._usage_key(scope, session_id)
        return self._usage.get(usage_key)

    def get_all_usage(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": key,
                "scope": usage.scope.name,
                "session_id": usage.session_id,
                "tokens_used": usage.tokens_used,
                "cost_cents": usage.cost_cents,
                "requests": usage.requests,
            }
            for key, usage in self._usage.items()
        ]

    def get_recent_alerts(self, limit: int = 20) -> List[BudgetAlert]:
        return self._alerts[-limit:]

    def clear_alerts(self) -> int:
        count = len(self._alerts)
        self._alerts.clear()
        return count

    def on_alert(self, callback: Callable[[BudgetAlert], None]) -> None:
        self._alert_callbacks.append(callback)

    def reset_scope(self, scope: BudgetScope) -> int:
        count = 0
        with self._lock:
            keys_to_remove = []
            for key, usage in self._usage.items():
                if usage.scope == scope:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self._usage[key]
                count += 1
        return count

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def _estimate_cost(self, tokens_input: int, tokens_output: int) -> int:
        input_cost = (tokens_input / 1000) * self._COST_PER_1K_TOKENS_INPUT
        output_cost = (tokens_output / 1000) * self._COST_PER_1K_TOKENS_OUTPUT
        return int((input_cost + output_cost) * 100)

    def _usage_key(self, scope: BudgetScope, session_id: str) -> str:
        if scope == BudgetScope.TOTAL:
            return "total"
        elif scope == BudgetScope.DAILY:
            from datetime import datetime
            day = datetime.now().strftime("%Y-%m-%d")
            return f"daily_{day}"
        return f"session_{session_id}"

    def _notify_callbacks(self, alert: BudgetAlert) -> None:
        for cb in self._alert_callbacks:
            try:
                cb(alert)
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_tokens = sum(u.tokens_used for u in self._usage.values())
            total_cost = sum(u.cost_cents for u in self._usage.values())
            total_requests = sum(u.requests for u in self._usage.values())

        usage_pcts = {}
        for scope in BudgetScope:
            limit = self._limits.get(scope)
            if not limit:
                continue
            scope_tokens = sum(
                u.tokens_used for u in self._usage.values() if u.scope == scope
            )
            usage_pcts[scope.name] = round(
                (scope_tokens / limit.max_tokens * 100) if limit.max_tokens > 0 else 0, 1
            )

        return {
            "enabled": self._enabled,
            "total_tokens": total_tokens,
            "total_cost_cents": total_cost,
            "total_requests": total_requests,
            "alert_count": len(self._alerts),
            "limits": {s.name: l.to_dict() for s, l in self._limits.items()},
            "usage_percentages": usage_pcts,
        }


def get_budget_tracker() -> BudgetTracker:
    return BudgetTracker.get_instance()
