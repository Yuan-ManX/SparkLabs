"""
SparkLabs Agent - Session Insights Engine

Analyzes game development session history to produce comprehensive
usage insights — token consumption, cost estimates, task completion
patterns, tool usage trends, and development productivity metrics.

Architecture:
  InsightsEngine
    |-- SessionCollector (gathers session data from trajectory records)
    |-- TokenAnalyzer (token input/output breakdown by model)
    |-- CostEstimator (USD cost estimates with pricing tiers)
    |-- ToolAnalyzer (tool call frequency and latency patterns)
    |-- TaskAnalyzer (task completion rates and iteration counts)
    |-- TrendBuilder (daily/weekly activity visualization)
    |-- ReportFormatter (JSON + terminal-friendly summary output)

Usage:
    engine = InsightsEngine()
    engine.feed_session(session_id, trajectory_events)
    report = engine.generate(days=30)
    print(engine.format_summary(report))
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class InsightPeriod(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALL_TIME = "all_time"


@dataclass
class TokenBreakdown:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hit_tokens: int = 0
    total_requests: int = 0
    estimated_cost_cents: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ModelStats:
    model_name: str = ""
    provider: str = ""
    tokens: TokenBreakdown = field(default_factory=TokenBreakdown)
    first_seen: float = 0.0
    last_seen: float = 0.0


@dataclass
class ToolStats:
    tool_name: str = ""
    call_count: int = 0
    total_duration_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0

    @property
    def avg_duration_ms(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.total_duration_ms / self.call_count

    @property
    def success_rate(self) -> float:
        if self.call_count == 0:
            return 1.0
        return self.success_count / self.call_count


@dataclass
class TaskStats:
    tasks_started: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_iterations: int = 0
    total_retries: int = 0

    @property
    def completion_rate(self) -> float:
        if self.tasks_started == 0:
            return 0.0
        return self.tasks_completed / self.tasks_started

    @property
    def avg_iterations(self) -> float:
        if self.tasks_started == 0:
            return 0.0
        return self.total_iterations / self.tasks_started


@dataclass
class DailyActivity:
    date: str = ""
    token_count: int = 0
    tool_calls: int = 0
    tasks_completed: int = 0
    session_count: int = 0


@dataclass
class InsightsReport:
    period: InsightPeriod = InsightPeriod.WEEKLY
    days_covered: int = 7
    generated_at: float = 0.0
    total_sessions: int = 0
    models: List[ModelStats] = field(default_factory=list)
    tools: List[ToolStats] = field(default_factory=list)
    tasks: TaskStats = field(default_factory=TaskStats)
    activity: List[DailyActivity] = field(default_factory=list)
    total_tokens: TokenBreakdown = field(default_factory=TokenBreakdown)
    top_cost_model: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period.value,
            "days_covered": self.days_covered,
            "generated_at": self.generated_at,
            "total_sessions": self.total_sessions,
            "total_tokens": {
                "input": self.total_tokens.input_tokens,
                "output": self.total_tokens.output_tokens,
                "cache_hit": self.total_tokens.cache_hit_tokens,
                "total": self.total_tokens.total_tokens,
                "requests": self.total_tokens.total_requests,
                "estimated_cost_cents": self.total_tokens.estimated_cost_cents,
            },
            "models": [
                {
                    "model": m.model_name,
                    "provider": m.provider,
                    "input_tokens": m.tokens.input_tokens,
                    "output_tokens": m.tokens.output_tokens,
                    "cost_cents": m.tokens.estimated_cost_cents,
                }
                for m in sorted(self.models, key=lambda x: x.tokens.total_tokens, reverse=True)
            ],
            "tools": [
                {
                    "name": t.tool_name,
                    "calls": t.call_count,
                    "avg_ms": round(t.avg_duration_ms, 1),
                    "success_rate": round(t.success_rate, 2),
                }
                for t in sorted(self.tools, key=lambda x: x.call_count, reverse=True)
            ],
            "tasks": {
                "started": self.tasks.tasks_started,
                "completed": self.tasks.tasks_completed,
                "failed": self.tasks.tasks_failed,
                "completion_rate": round(self.tasks.completion_rate, 2),
                "avg_iterations": round(self.tasks.avg_iterations, 1),
            },
            "activity": [
                {"date": a.date, "tokens": a.token_count, "tool_calls": a.tool_calls}
                for a in self.activity
            ],
            "top_cost_model": self.top_cost_model,
        }


class InsightsEngine:
    """Analyzes game development session data and produces insights reports."""

    _instance: Optional["InsightsEngine"] = None

    def __init__(self):
        self._models: Dict[str, ModelStats] = {}
        self._tools: Dict[str, ToolStats] = {}
        self._tasks: TaskStats = TaskStats()
        self._activity: Dict[str, DailyActivity] = {}
        self._total_tokens: TokenBreakdown = TokenBreakdown()
        self._total_sessions: int = 0
        self._last_cleanup: float = 0.0
        self._enabled: bool = True
        self._pricing_callbacks: List[Callable[[str, int, int], int]] = []

    @classmethod
    def get_instance(cls) -> "InsightsEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_pricing(self, callback: Callable[[str, int, int], int]) -> None:
        self._pricing_callbacks.append(callback)

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> int:
        for cb in self._pricing_callbacks:
            result = cb(model, input_tokens, output_tokens)
            if result > 0:
                return result
        return input_tokens // 500 + output_tokens // 100

    def feed_session(self, session_id: str, events: List[Any]) -> None:
        if not self._enabled:
            return

        self._total_sessions += 1
        session_date = time.strftime("%Y-%m-%d")

        if session_date not in self._activity:
            self._activity[session_date] = DailyActivity(date=session_date)
        day = self._activity[session_date]
        day.session_count += 1

        for event in events:
            evt_data = getattr(event, "data", {}) if hasattr(event, "data") else {}
            evt_type = getattr(event, "event_type", None)

            if evt_type and hasattr(evt_type, "name"):
                type_name = evt_type.name
            elif isinstance(evt_type, str):
                type_name = evt_type
            else:
                type_name = str(evt_type)

            if type_name in ("LLM_REQUEST", "LLM_RESPONSE"):
                model = evt_data.get("model", "unknown") if isinstance(evt_data, dict) else "unknown"
                tokens_in = evt_data.get("tokens", evt_data.get("prompt_tokens", 0)) if isinstance(evt_data, dict) else 0
                tokens_out = evt_data.get("completion_tokens", evt_data.get("response", "")) if isinstance(evt_data, dict) else 0
                if isinstance(tokens_out, str):
                    tokens_out = len(tokens_out) // 4
                tokens_in = int(tokens_in or 0)
                tokens_out = int(tokens_out or 0)

                if model not in self._models:
                    self._models[model] = ModelStats(model_name=model, first_seen=time.time())
                ms = self._models[model]
                ms.last_seen = time.time()
                ms.tokens.input_tokens += tokens_in
                ms.tokens.output_tokens += tokens_out
                ms.tokens.total_requests += 1
                cost = self._estimate_cost(model, tokens_in, tokens_out)
                ms.tokens.estimated_cost_cents += cost

                self._total_tokens.input_tokens += tokens_in
                self._total_tokens.output_tokens += tokens_out
                self._total_tokens.total_requests += 1
                self._total_tokens.estimated_cost_cents += cost

                day.token_count += tokens_in + tokens_out

            if type_name == "TOOL_CALL":
                tool_name = evt_data.get("name", evt_data.get("tool", "")) if isinstance(evt_data, dict) else ""
                duration = float(evt_data.get("duration_ms", 0) or 0) if isinstance(evt_data, dict) else 0.0
                success = bool(evt_data.get("success", True)) if isinstance(evt_data, dict) else True

                if tool_name not in self._tools:
                    self._tools[tool_name] = ToolStats(tool_name=tool_name)
                ts = self._tools[tool_name]
                ts.call_count += 1
                ts.total_duration_ms += duration
                if success:
                    ts.success_count += 1
                else:
                    ts.failure_count += 1

                day.tool_calls += 1

    def track_task(self, started: bool = False, completed: bool = False,
                   failed: bool = False, iterations: int = 0, retries: int = 0) -> None:
        if not self._enabled:
            return
        if started:
            self._tasks.tasks_started += 1
        if completed:
            self._tasks.tasks_completed += 1
        if failed:
            self._tasks.tasks_failed += 1
        self._tasks.total_iterations += iterations
        self._tasks.total_retries += retries

    def generate(self, days: int = 30) -> InsightsReport:
        cutoff_time = time.time() - (days * 86400)
        cutoff_date = time.strftime("%Y-%m-%d", time.localtime(cutoff_time))

        period = InsightPeriod.DAILY if days <= 1 else InsightPeriod.WEEKLY if days <= 7 else InsightPeriod.MONTHLY

        recent_activity = [
            a for d, a in sorted(self._activity.items())
            if d >= cutoff_date
        ]

        top_model = ""
        top_cost = 0
        for name, ms in self._models.items():
            if ms.tokens.estimated_cost_cents > top_cost:
                top_cost = ms.tokens.estimated_cost_cents
                top_model = name

        return InsightsReport(
            period=period,
            days_covered=days,
            generated_at=time.time(),
            total_sessions=self._total_sessions,
            models=list(self._models.values()),
            tools=list(self._tools.values()),
            tasks=self._tasks,
            activity=recent_activity,
            total_tokens=self._total_tokens,
            top_cost_model=top_model,
        )

    def format_summary(self, report: InsightsReport) -> str:
        lines = [
            f"SparkLabs Insights Report ({report.period.value})",
            f"Period: last {report.days_covered} days | Sessions: {report.total_sessions}",
            f"Tokens: {report.total_tokens.total_tokens:,} total | "
            f"Cost: ${report.total_tokens.estimated_cost_cents / 100:.2f} est.",
            f"Tasks: {report.tasks.tasks_completed}/{report.tasks.tasks_started} completed "
            f"({report.tasks.completion_rate:.0%}) | Avg {report.tasks.avg_iterations:.1f} iterations",
        ]
        if report.top_cost_model:
            lines.append(f"Top model by cost: {report.top_cost_model}")
        if report.tools:
            top_tools = sorted(report.tools, key=lambda t: t.call_count, reverse=True)[:5]
            lines.append(f"Top tools: {', '.join(f'{t.tool_name}({t.call_count})' for t in top_tools)}")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_sessions": self._total_sessions,
            "models_tracked": len(self._models),
            "tools_tracked": len(self._tools),
            "tasks_tracked": self._tasks.tasks_started,
            "total_tokens": self._total_tokens.total_tokens,
            "total_cost_cents": self._total_tokens.estimated_cost_cents,
            "enabled": self._enabled,
        }

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def reset(self) -> None:
        self._models.clear()
        self._tools.clear()
        self._tasks = TaskStats()
        self._activity.clear()
        self._total_tokens = TokenBreakdown()
        self._total_sessions = 0


def get_insights_engine() -> InsightsEngine:
    return InsightsEngine.get_instance()
