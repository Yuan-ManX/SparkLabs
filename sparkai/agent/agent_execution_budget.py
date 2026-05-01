"""
SparkAI Agent - Execution Budget Engine

Token and cost budget tracking system. Monitors resource consumption
across agent sessions, enforces budget limits, and provides detailed
usage statistics. Supports multiple budget tiers with warnings,
soft limits, and hard caps to prevent runaway spending.

Architecture:
  ExecutionBudget
    |-- TokenTracker (token usage per session/provider)
    |-- CostTracker (cost estimation from token usage)
    |-- BudgetEnforcer (limit enforcement with warnings)
    |-- UsageReporter (detailed usage statistics)
    |-- SessionLimiter (per-session iteration/step limits)

Budget Tiers:
  - Warning: notification sent, execution continues
  - Soft Limit: agent is asked to wrap up current task
  - Hard Cap: execution is terminated immediately
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BudgetTier(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    SOFT_LIMIT = "soft_limit"
    HARD_CAP = "hard_cap"


class BudgetScope(Enum):
    PER_REQUEST = "per_request"
    PER_SESSION = "per_session"
    PER_DAY = "per_day"
    PER_MONTH = "per_month"
    UNLIMITED = "unlimited"


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class CostEstimate:
    total_cost_usd: float = 0.0
    currency: str = "USD"
    breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cost_usd": round(self.total_cost_usd, 6),
            "currency": self.currency,
            "breakdown": {k: round(v, 6) for k, v in self.breakdown.items()},
        }


@dataclass
class BudgetConfig:
    max_tokens_per_request: int = 100000
    max_tokens_per_session: int = 500000
    max_tokens_per_day: int = 2000000
    max_tokens_per_month: int = 50000000

    max_cost_per_day_usd: float = 10.0
    max_cost_per_month_usd: float = 100.0

    max_iterations_per_session: int = 90
    max_subagent_iterations: int = 50

    warn_at_fraction: float = 0.8
    soft_limit_fraction: float = 0.95
    hard_cap_fraction: float = 1.0

    pricing_per_1k: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "gpt-4": (0.03, 0.06),
        "gpt-4o": (0.0025, 0.01),
        "claude-3-opus": (0.015, 0.075),
        "claude-3-sonnet": (0.003, 0.015),
        "minimax-m2": (0.001, 0.002),
        "default": (0.001, 0.002),
    })


@dataclass
class SessionBudget:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tokens: TokenUsage = field(default_factory=TokenUsage)
    cost: CostEstimate = field(default_factory=CostEstimate)
    iterations: int = 0
    subagent_iterations: int = 0
    tier: BudgetTier = BudgetTier.NORMAL
    created_at: float = field(default_factory=time.time)
    last_updated_at: float = field(default_factory=time.time)
    model: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tokens": self.tokens.to_dict(),
            "cost": self.cost.to_dict(),
            "iterations": self.iterations,
            "subagent_iterations": self.subagent_iterations,
            "tier": self.tier.value,
            "created_at": self.created_at,
            "last_updated_at": self.last_updated_at,
            "model": self.model,
        }


class ExecutionBudget:
    """
    Token and cost budget tracking engine.

    Enforces resource limits across sessions to prevent excessive
    API costs and runaway agent behavior. Provides tiered warnings
    that allow agents to gracefully wind down before reaching
    hard caps.

    Usage:
        budget = ExecutionBudget()
        budget.start_session("gen_001", model="gpt-4o")
        budget.record_usage("gen_001", TokenUsage(prompt=1000, completion=500))
        if budget.check_tier("gen_001") == BudgetTier.WARNING:
            print("Approaching budget limit")
    """

    def __init__(self, config: Optional[BudgetConfig] = None):
        self._config = config or BudgetConfig()
        self._sessions: Dict[str, SessionBudget] = {}
        self._daily_tokens = TokenUsage()
        self._monthly_tokens = TokenUsage()
        self._daily_cost = 0.0
        self._monthly_cost = 0.0
        self._day_start = time.time()
        self._month_start = time.time()
        self._usage_history: List[Dict[str, Any]] = []

    def _rotate_daily(self) -> None:
        now = time.time()
        if now - self._day_start >= 86400.0:
            self._daily_tokens = TokenUsage()
            self._daily_cost = 0.0
            self._day_start = now

    def _rotate_monthly(self) -> None:
        now = time.time()
        if now - self._month_start >= 2592000.0:
            self._monthly_tokens = TokenUsage()
            self._monthly_cost = 0.0
            self._month_start = now

    def start_session(self, session_id: str, model: str = "unknown") -> SessionBudget:
        budget = SessionBudget(session_id=session_id, model=model)
        self._sessions[session_id] = budget
        return budget

    def end_session(self, session_id: str) -> Optional[SessionBudget]:
        budget = self._sessions.pop(session_id, None)
        if budget:
            self._usage_history.append(budget.to_dict())
        return budget

    def record_usage(self, session_id: str, tokens: TokenUsage) -> None:
        self._rotate_daily()
        self._rotate_monthly()

        budget = self._sessions.get(session_id)
        if budget is None:
            budget = self.start_session(session_id)

        budget.tokens += tokens
        budget.iterations += 1
        budget.last_updated_at = time.time()

        self._daily_tokens += tokens
        self._monthly_tokens += tokens

        cost = self._estimate_cost(tokens, budget.model)
        budget.cost.total_cost_usd += cost.total_cost_usd
        self._daily_cost += cost.total_cost_usd
        self._monthly_cost += cost.total_cost_usd

    def record_subagent_iteration(self, session_id: str) -> None:
        budget = self._sessions.get(session_id)
        if budget:
            budget.subagent_iterations += 1

    def _estimate_cost(self, tokens: TokenUsage, model: str) -> CostEstimate:
        pricing = self._config.pricing_per_1k
        match = None
        for key, rates in pricing.items():
            if key in model.lower():
                match = rates
                break
        if match is None:
            match = pricing["default"]

        prompt_rate, completion_rate = match
        prompt_cost = (tokens.prompt_tokens / 1000.0) * prompt_rate
        completion_cost = (tokens.completion_tokens / 1000.0) * completion_rate

        return CostEstimate(
            total_cost_usd=prompt_cost + completion_cost,
            breakdown={
                "prompt_cost": prompt_cost,
                "completion_cost": completion_cost,
            },
        )

    def check_tier(self, session_id: str) -> BudgetTier:
        budget = self._sessions.get(session_id)
        if budget is None:
            return BudgetTier.NORMAL

        self._rotate_daily()
        self._rotate_monthly()

        session_fraction = budget.tokens.total_tokens / max(self._config.max_tokens_per_session, 1)
        daily_fraction = self._daily_tokens.total_tokens / max(self._config.max_tokens_per_day, 1)
        cost_fraction = self._daily_cost / max(self._config.max_cost_per_day_usd, 0.001)
        iter_fraction = budget.iterations / max(self._config.max_iterations_per_session, 1)

        max_fraction = max(session_fraction, daily_fraction, cost_fraction, iter_fraction)

        if max_fraction >= self._config.hard_cap_fraction:
            return BudgetTier.HARD_CAP
        if max_fraction >= self._config.soft_limit_fraction:
            return BudgetTier.SOFT_LIMIT
        if max_fraction >= self._config.warn_at_fraction:
            return BudgetTier.WARNING
        return BudgetTier.NORMAL

    def can_continue(self, session_id: str) -> bool:
        tier = self.check_tier(session_id)
        return tier != BudgetTier.HARD_CAP

    def should_wrap_up(self, session_id: str) -> bool:
        tier = self.check_tier(session_id)
        return tier in (BudgetTier.SOFT_LIMIT, BudgetTier.HARD_CAP)

    def get_session(self, session_id: str) -> Optional[SessionBudget]:
        return self._sessions.get(session_id)

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        budget = self._sessions.get(session_id)
        if not budget:
            return {"error": "Session not found"}

        return {
            **budget.to_dict(),
            "current_tier": self.check_tier(session_id).value,
            "session_token_fraction": round(budget.tokens.total_tokens / max(self._config.max_tokens_per_session, 1), 3),
            "iteration_fraction": round(budget.iterations / max(self._config.max_iterations_per_session, 1), 3),
        }

    def get_daily_stats(self) -> Dict[str, Any]:
        self._rotate_daily()
        return {
            "tokens": self._daily_tokens.to_dict(),
            "cost_usd": round(self._daily_cost, 6),
            "token_fraction": round(self._daily_tokens.total_tokens / max(self._config.max_tokens_per_day, 1), 3),
            "cost_fraction": round(self._daily_cost / max(self._config.max_cost_per_day_usd, 0.001), 3),
        }

    def get_overall_stats(self) -> Dict[str, Any]:
        return {
            "active_sessions": len(self._sessions),
            "completed_sessions": len(self._usage_history),
            "total_tokens_all_time": sum(
                h.get("tokens", {}).get("total_tokens", 0) for h in self._usage_history
            ) + sum(s.tokens.total_tokens for s in self._sessions.values()),
            "total_cost_all_time": round(sum(
                h.get("cost", {}).get("total_cost_usd", 0) for h in self._usage_history
            ) + sum(s.cost.total_cost_usd for s in self._sessions.values()), 6),
            "daily": self.get_daily_stats(),
            "config": {
                "max_tokens_per_request": self._config.max_tokens_per_request,
                "max_tokens_per_session": self._config.max_tokens_per_session,
                "max_tokens_per_day": self._config.max_tokens_per_day,
                "max_cost_per_day_usd": self._config.max_cost_per_day_usd,
                "max_iterations_per_session": self._config.max_iterations_per_session,
            },
        }

    def get_usage_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self._usage_history[-limit:]))

    def reset(self) -> None:
        self._sessions.clear()
        self._daily_tokens = TokenUsage()
        self._monthly_tokens = TokenUsage()
        self._daily_cost = 0.0
        self._monthly_cost = 0.0
        self._usage_history.clear()


_global_execution_budget: Optional[ExecutionBudget] = None


def get_execution_budget() -> ExecutionBudget:
    global _global_execution_budget
    if _global_execution_budget is None:
        _global_execution_budget = ExecutionBudget()
    return _global_execution_budget
