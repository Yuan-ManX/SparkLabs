"""
SparkLabs Agent - AI Natural-Language Analytics Query Engine

A natural-language analytics interface for the SparkLabs AI-native game
engine. Designers ask questions in plain English (e.g. "What is our D7
retention by cohort?" or "Show me the top 10 churn risk players") and the
engine interprets the intent, plans a multi-step query across registered
data sources, executes it, and returns structured result rows.

This module embodies the AI-native principle: analytics is not a static
SQL console but an intelligent agent that classifies intent, reasons about
which data sources and metrics are relevant, decomposes the question into
an executable plan, and produces interpretable mock results that mirror
the shape of real telemetry joins.

Architecture:
  AnalyticsQueryEngine (singleton)
    |-- NLQuery, QueryResult, SavedQuery, DataSource, MetricDefinition,
       QueryPlan, AnalyticsQueryStats, AnalyticsQuerySnapshot,
       AnalyticsQueryEvent
    |-- QueryIntent, QueryStatus, DataSourceType, ResultFormat,
       AnalyticsQueryEventKind

Core Capabilities:
  - submit_query / plan_query / execute_query / get_query / list_queries:
    natural-language query lifecycle from submission to result.
  - save_query / get_saved_query / list_saved_queries / delete_saved_query:
    reusable named query library.
  - register_data_source / get_data_source / list_data_sources: registry of
    queryable data sources (telemetry, analytics_db, live_ops, ...).
  - register_metric / get_metric / list_metrics: catalog of metric
    definitions keyed by intent.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_QUERIES: int = 5000
_MAX_RESULTS: int = 5000
_MAX_PLANS: int = 5000
_MAX_SAVED_QUERIES: int = 1000
_MAX_DATA_SOURCES: int = 200
_MAX_METRICS: int = 500
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class QueryIntent(Enum):
    RETENTION = "retention"
    ENGAGEMENT = "engagement"
    MONETIZATION = "monetization"
    PROGRESSION = "progression"
    COMPARISON = "comparison"
    TREND = "trend"
    FUNNEL = "funnel"
    COHORT = "cohort"
    SUMMARY = "summary"
    CUSTOM = "custom"


class QueryStatus(Enum):
    PENDING = "pending"
    PLANNED = "planned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class DataSourceType(Enum):
    TELEMETRY = "telemetry"
    ANALYTICS_DB = "analytics_db"
    LIVE_OPS = "live_ops"
    PLAYER_PROFILES = "player_profiles"
    ECONOMY = "economy"
    EVENTS = "events"


class ResultFormat(Enum):
    TABLE = "table"
    CHART = "chart"
    NUMBER = "number"
    PERCENTAGE = "percentage"
    LIST = "list"


class AnalyticsQueryEventKind(Enum):
    QUERY_SUBMITTED = "query_submitted"
    QUERY_PLANNED = "query_planned"
    QUERY_EXECUTING = "query_executing"
    QUERY_COMPLETED = "query_completed"
    QUERY_FAILED = "query_failed"
    QUERY_SAVED = "query_saved"
    QUERY_DELETED = "query_deleted"
    DATASOURCE_REGISTERED = "datasource_registered"
    METRIC_REGISTERED = "metric_registered"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class NLQuery:
    """A natural-language analytics question submitted by a designer."""
    query_id: str
    text: str
    intent: QueryIntent = QueryIntent.CUSTOM
    status: QueryStatus = QueryStatus.PENDING
    requested_format: ResultFormat = ResultFormat.TABLE
    requested_by: str = ""
    plan_id: str = ""
    result_id: str = ""
    error: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    completed_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QueryResult:
    """The structured result rows produced by executing a query."""
    result_id: str
    query_id: str
    intent: QueryIntent = QueryIntent.CUSTOM
    format: ResultFormat = ResultFormat.TABLE
    columns: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    row_count: int = 0
    execution_ms: int = 0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SavedQuery:
    """A reusable named query stored in the analytics library."""
    saved_id: str
    name: str
    text: str
    intent: QueryIntent = QueryIntent.CUSTOM
    description: str = ""
    created_by: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DataSource:
    """A queryable data source registered with the engine."""
    source_id: str
    name: str
    source_type: DataSourceType
    connection: str = ""
    description: str = ""
    is_active: bool = True
    schema: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetricDefinition:
    """A named metric definition keyed to a query intent."""
    metric_id: str
    name: str
    intent: QueryIntent = QueryIntent.CUSTOM
    formula: str = ""
    unit: str = ""
    description: str = ""
    data_source_id: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QueryPlan:
    """A decomposed execution plan for a natural-language query."""
    plan_id: str
    query_id: str
    intent: QueryIntent = QueryIntent.CUSTOM
    steps: List[Dict[str, Any]] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnalyticsQueryStats:
    """Aggregate statistics for the analytics query engine."""
    total_queries: int = 0
    pending_queries: int = 0
    planned_queries: int = 0
    executing_queries: int = 0
    completed_queries: int = 0
    failed_queries: int = 0
    total_saved_queries: int = 0
    total_data_sources: int = 0
    total_metrics: int = 0
    total_events: int = 0
    avg_execution_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnalyticsQuerySnapshot:
    """A point-in-time snapshot of engine state."""
    queries: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    saved_queries: List[Dict[str, Any]] = field(default_factory=list)
    data_sources: List[Dict[str, Any]] = field(default_factory=list)
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnalyticsQueryEvent:
    """An audit event emitted by the analytics query engine."""
    event_id: str
    kind: AnalyticsQueryEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Analytics Query Engine Singleton
# ---------------------------------------------------------------------------


class AnalyticsQueryEngine:
    """AI-native natural-language analytics query engine for game data."""

    _instance: Optional["AnalyticsQueryEngine"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "AnalyticsQueryEngine":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AnalyticsQueryEngine":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._queries: Dict[str, NLQuery] = {}
            self._results: Dict[str, QueryResult] = {}
            self._plans: Dict[str, QueryPlan] = {}
            self._saved_queries: Dict[str, SavedQuery] = {}
            self._data_sources: Dict[str, DataSource] = {}
            self._metrics: Dict[str, MetricDefinition] = {}
            self._events: List[AnalyticsQueryEvent] = []
            self._seed_data()
            self._initialized = True

    def _emit(self, kind: AnalyticsQueryEventKind, data: Dict[str, Any]) -> None:
        event = AnalyticsQueryEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Intent Detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_intent(text: str) -> QueryIntent:
        lowered = (text or "").lower()
        if any(k in lowered for k in ("retention", "d1", "d3", "d7", "d14", "d30", "day-7", "day 7")):
            return QueryIntent.RETENTION
        if any(k in lowered for k in ("funnel", "conversion", "step")):
            return QueryIntent.FUNNEL
        if any(k in lowered for k in ("cohort",)) and "retention" not in lowered:
            return QueryIntent.COHORT
        if any(k in lowered for k in ("revenue", "arpu", "arppu", "spend", "monetiz", "ltv", "purchas")):
            return QueryIntent.MONETIZATION
        if any(k in lowered for k in ("progress", "level", "completion", "xp", "unlock")):
            return QueryIntent.PROGRESSION
        if any(k in lowered for k in ("compare", "versus", " vs ", "difference", "delta", "against")):
            return QueryIntent.COMPARISON
        if any(k in lowered for k in ("trend", "over time", "growth", "weekly", "monthly", "trajectory")):
            return QueryIntent.TREND
        if any(k in lowered for k in ("summary", "overview", "snapshot", "kpi", "dashboard")):
            return QueryIntent.SUMMARY
        if any(k in lowered for k in ("churn", "risk", "engagement", "session", "dau", "mau", "active")):
            return QueryIntent.ENGAGEMENT
        return QueryIntent.CUSTOM

    # ------------------------------------------------------------------
    # Query Lifecycle
    # ------------------------------------------------------------------

    def submit_query(self, text: str, requested_by: str = "",
                     requested_format: ResultFormat = ResultFormat.TABLE,
                     intent: Optional[QueryIntent] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> NLQuery:
        with self._lock:
            detected = intent if intent is not None else self._detect_intent(text)
            query = NLQuery(
                query_id=_new_id("q"),
                text=text,
                intent=detected,
                status=QueryStatus.PENDING,
                requested_format=requested_format,
                requested_by=requested_by,
                metadata=metadata or {},
            )
            self._queries[query.query_id] = query
            _evict_fifo_dict(self._queries, _MAX_QUERIES)
            self._emit(AnalyticsQueryEventKind.QUERY_SUBMITTED, {
                "query_id": query.query_id,
                "intent": detected.value,
                "requested_by": requested_by,
            })
            return query

    def plan_query(self, query_id: str) -> Optional[QueryPlan]:
        with self._lock:
            query = self._queries.get(query_id)
            if query is None:
                return None
            steps = self._build_plan_steps(query)
            data_source_ids = [s for s in self._data_sources.keys()]
            estimated = 0.0
            for step in steps:
                estimated += float(step.get("est_ms", 0))
            plan = QueryPlan(
                plan_id=_new_id("plan"),
                query_id=query_id,
                intent=query.intent,
                steps=steps,
                data_sources=data_source_ids,
                estimated_cost=round(estimated / 1000.0, 3),
            )
            self._plans[plan.plan_id] = plan
            _evict_fifo_dict(self._plans, _MAX_PLANS)
            query.plan_id = plan.plan_id
            query.status = QueryStatus.PLANNED
            query.updated_at = _now()
            self._emit(AnalyticsQueryEventKind.QUERY_PLANNED, {
                "query_id": query_id,
                "plan_id": plan.plan_id,
                "step_count": len(steps),
            })
            return plan

    def _build_plan_steps(self, query: NLQuery) -> List[Dict[str, Any]]:
        """Decompose a query into executable steps based on its intent."""
        intent = query.intent
        source = self._pick_source_for_intent(intent)
        steps: List[Dict[str, Any]] = []

        steps.append({
            "step": 1,
            "action": "parse",
            "source": "nl_parser",
            "description": f"Parse natural-language query and resolve intent '{intent.value}'.",
            "est_ms": 5,
        })
        steps.append({
            "step": 2,
            "action": "resolve_metrics",
            "source": "metric_registry",
            "description": "Resolve metric definitions relevant to the intent.",
            "est_ms": 8,
        })
        steps.append({
            "step": 3,
            "action": "scan",
            "source": source,
            "description": f"Scan '{source}' for matching event records within the target window.",
            "est_ms": 45,
        })
        steps.append({
            "step": 4,
            "action": "aggregate",
            "source": "analytics_db",
            "description": "Group, aggregate, and compute the requested measure.",
            "est_ms": 30,
        })
        steps.append({
            "step": 5,
            "action": "format",
            "source": "result_formatter",
            "description": f"Format output as '{query.requested_format.value}' for the caller.",
            "est_ms": 5,
        })
        return steps

    def _pick_source_for_intent(self, intent: QueryIntent) -> str:
        if intent == QueryIntent.MONETIZATION:
            preferred = "ds_economy"
        elif intent == QueryIntent.PROGRESSION:
            preferred = "ds_player_profiles"
        elif intent in (QueryIntent.RETENTION, QueryIntent.COHORT, QueryIntent.FUNNEL):
            preferred = "ds_analytics_db"
        elif intent == QueryIntent.ENGAGEMENT:
            preferred = "ds_telemetry"
        else:
            preferred = "ds_analytics_db"
        if preferred in self._data_sources:
            return preferred
        if self._data_sources:
            return next(iter(self._data_sources.keys()))
        return preferred

    def execute_query(self, query_id: str) -> Optional[QueryResult]:
        with self._lock:
            query = self._queries.get(query_id)
            if query is None:
                return None
            if query.plan_id == "" or query.plan_id not in self._plans:
                self.plan_query(query_id)
                query = self._queries.get(query_id)
                if query is None:
                    return None

            start = time.time()
            query.status = QueryStatus.EXECUTING
            query.updated_at = _now()
            self._emit(AnalyticsQueryEventKind.QUERY_EXECUTING, {
                "query_id": query_id,
            })

            try:
                columns, rows, summary = self._simulate_result(query)
                elapsed_ms = int((time.time() - start) * 1000)
                result = QueryResult(
                    result_id=_new_id("res"),
                    query_id=query_id,
                    intent=query.intent,
                    format=query.requested_format,
                    columns=columns,
                    rows=rows,
                    summary=summary,
                    row_count=len(rows),
                    execution_ms=elapsed_ms,
                )
                self._results[result.result_id] = result
                _evict_fifo_dict(self._results, _MAX_RESULTS)
                query.result_id = result.result_id
                query.status = QueryStatus.COMPLETED
                query.completed_at = _now()
                query.updated_at = _now()
                self._emit(AnalyticsQueryEventKind.QUERY_COMPLETED, {
                    "query_id": query_id,
                    "result_id": result.result_id,
                    "row_count": result.row_count,
                    "execution_ms": elapsed_ms,
                })
                return result
            except Exception as exc:  # pragma: no cover - defensive guard
                query.status = QueryStatus.FAILED
                query.error = str(exc)
                query.updated_at = _now()
                self._emit(AnalyticsQueryEventKind.QUERY_FAILED, {
                    "query_id": query_id,
                    "error": query.error,
                })
                return None

    def _simulate_result(self, query: NLQuery) -> tuple:
        """Produce mock result rows shaped to match the query intent."""
        intent = query.intent
        if intent == QueryIntent.RETENTION:
            columns = ["cohort", "day", "retention_pct"]
            rows = [
                {"cohort": "2025-W22", "day": 1, "retention_pct": 0.42},
                {"cohort": "2025-W22", "day": 3, "retention_pct": 0.28},
                {"cohort": "2025-W22", "day": 7, "retention_pct": 0.18},
                {"cohort": "2025-W22", "day": 14, "retention_pct": 0.11},
                {"cohort": "2025-W22", "day": 30, "retention_pct": 0.06},
            ]
            summary = "D7 retention for cohort 2025-W22 is 18.0%."
        elif intent == QueryIntent.ENGAGEMENT:
            columns = ["date", "dau", "sessions", "avg_session_min"]
            rows = [
                {"date": "2025-06-27", "dau": 12450, "sessions": 31200, "avg_session_min": 18.4},
                {"date": "2025-06-28", "dau": 13180, "sessions": 33450, "avg_session_min": 19.1},
                {"date": "2025-06-29", "dau": 14200, "sessions": 36800, "avg_session_min": 20.3},
                {"date": "2025-06-30", "dau": 13870, "sessions": 35100, "avg_session_min": 19.8},
                {"date": "2025-07-01", "dau": 14520, "sessions": 38200, "avg_session_min": 20.7},
            ]
            summary = "Top 10 churn risk players identified by declining session counts."
        elif intent == QueryIntent.MONETIZATION:
            columns = ["date", "revenue_usd", "arpu", "payers"]
            rows = [
                {"date": "2025-06-27", "revenue_usd": 4200.0, "arpu": 0.34, "payers": 510},
                {"date": "2025-06-28", "revenue_usd": 4580.0, "arpu": 0.35, "payers": 540},
                {"date": "2025-06-29", "revenue_usd": 5100.0, "arpu": 0.36, "payers": 580},
                {"date": "2025-06-30", "revenue_usd": 4870.0, "arpu": 0.35, "payers": 560},
                {"date": "2025-07-01", "revenue_usd": 5320.0, "arpu": 0.37, "payers": 600},
            ]
            summary = "ARPU trending up to $0.37 with 600 payers on 2025-07-01."
        elif intent == QueryIntent.PROGRESSION:
            columns = ["level", "players_reached", "drop_off_pct"]
            rows = [
                {"level": 1, "players_reached": 20000, "drop_off_pct": 0.05},
                {"level": 5, "players_reached": 16800, "drop_off_pct": 0.12},
                {"level": 10, "players_reached": 12100, "drop_off_pct": 0.18},
                {"level": 15, "players_reached": 8400, "drop_off_pct": 0.24},
                {"level": 20, "players_reached": 5600, "drop_off_pct": 0.31},
            ]
            summary = "Largest drop-off occurs between level 10 and level 15."
        elif intent == QueryIntent.COMPARISON:
            columns = ["segment", "metric_a", "metric_b", "delta_pct"]
            rows = [
                {"segment": "organic", "metric_a": 0.19, "metric_b": 0.21, "delta_pct": 0.105},
                {"segment": "paid", "metric_a": 0.14, "metric_b": 0.16, "delta_pct": 0.143},
                {"segment": "invite", "metric_a": 0.23, "metric_b": 0.26, "delta_pct": 0.130},
            ]
            summary = "Invite segment outperforms paid across both metrics."
        elif intent == QueryIntent.TREND:
            columns = ["date", "value", "change_pct"]
            rows = [
                {"date": "2025-W21", "value": 0.16, "change_pct": 0.0},
                {"date": "2025-W22", "value": 0.18, "change_pct": 0.125},
                {"date": "2025-W23", "value": 0.17, "change_pct": -0.056},
                {"date": "2025-W24", "value": 0.19, "change_pct": 0.118},
                {"date": "2025-W25", "value": 0.21, "change_pct": 0.105},
            ]
            summary = "Upward trend over the last 5 weeks, ending at 0.21."
        elif intent == QueryIntent.FUNNEL:
            columns = ["stage", "users", "conversion_pct"]
            rows = [
                {"stage": "install", "users": 20000, "conversion_pct": 1.0},
                {"stage": "tutorial_complete", "users": 15600, "conversion_pct": 0.78},
                {"stage": "first_purchase", "users": 2400, "conversion_pct": 0.12},
                {"stage": "repeat_purchase", "users": 1080, "conversion_pct": 0.054},
            ]
            summary = "Tutorial-to-first-purchase conversion is 12.0%."
        elif intent == QueryIntent.COHORT:
            columns = ["cohort", "week_1", "week_2", "week_3", "week_4"]
            rows = [
                {"cohort": "2025-W22", "week_1": 0.42, "week_2": 0.28, "week_3": 0.21, "week_4": 0.16},
                {"cohort": "2025-W23", "week_1": 0.44, "week_2": 0.30, "week_3": 0.22, "week_4": 0.0},
                {"cohort": "2025-W24", "week_1": 0.41, "week_2": 0.27, "week_3": 0.0, "week_4": 0.0},
            ]
            summary = "Cohort retention matrix across 4 weeks for 3 cohorts."
        elif intent == QueryIntent.SUMMARY:
            columns = ["metric", "value", "change_pct"]
            rows = [
                {"metric": "dau", "value": 14520, "change_pct": 0.047},
                {"metric": "d7_retention", "value": 0.18, "change_pct": 0.020},
                {"metric": "arpu", "value": 0.37, "change_pct": 0.027},
                {"metric": "crash_rate", "value": 0.0021, "change_pct": -0.087},
            ]
            summary = "Overview snapshot: DAU and retention up, crash rate down."
        else:
            columns = ["key", "value"]
            rows = [
                {"key": "query", "value": query.text},
                {"key": "intent", "value": query.intent.value},
                {"key": "status", "value": QueryStatus.COMPLETED.value},
                {"key": "note", "value": "No specific template matched; returning generic summary."},
            ]
            summary = "Custom query executed with generic result shape."
        return columns, rows, summary

    def get_query(self, query_id: str) -> Optional[NLQuery]:
        with self._lock:
            return self._queries.get(query_id)

    def list_queries(self, status: Optional[QueryStatus] = None,
                     intent: Optional[QueryIntent] = None,
                     limit: int = 100) -> List[NLQuery]:
        with self._lock:
            items = list(self._queries.values())
            if status is not None:
                items = [q for q in items if q.status == status]
            if intent is not None:
                items = [q for q in items if q.intent == intent]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Saved Query Library
    # ------------------------------------------------------------------

    def save_query(self, name: str, text: str,
                   intent: QueryIntent = QueryIntent.CUSTOM,
                   description: str = "",
                   created_by: str = "",
                   tags: Optional[List[str]] = None) -> SavedQuery:
        with self._lock:
            resolved_intent = intent if intent != QueryIntent.CUSTOM else self._detect_intent(text)
            saved = SavedQuery(
                saved_id=_new_id("sq"),
                name=name,
                text=text,
                intent=resolved_intent,
                description=description,
                created_by=created_by,
                tags=tags or [],
            )
            self._saved_queries[saved.saved_id] = saved
            _evict_fifo_dict(self._saved_queries, _MAX_SAVED_QUERIES)
            self._emit(AnalyticsQueryEventKind.QUERY_SAVED, {
                "saved_id": saved.saved_id,
                "name": name,
            })
            return saved

    def get_saved_query(self, saved_id: str) -> Optional[SavedQuery]:
        with self._lock:
            return self._saved_queries.get(saved_id)

    def list_saved_queries(self, intent: Optional[QueryIntent] = None,
                           limit: int = 100) -> List[SavedQuery]:
        with self._lock:
            items = list(self._saved_queries.values())
            if intent is not None:
                items = [s for s in items if s.intent == intent]
            return items[-limit:]

    def delete_saved_query(self, saved_id: str) -> bool:
        with self._lock:
            if saved_id not in self._saved_queries:
                return False
            del self._saved_queries[saved_id]
            self._emit(AnalyticsQueryEventKind.QUERY_DELETED, {
                "saved_id": saved_id,
            })
            return True

    # ------------------------------------------------------------------
    # Data Source Registry
    # ------------------------------------------------------------------

    def register_data_source(self, name: str, source_type: DataSourceType,
                             connection: str = "",
                             description: str = "",
                             schema: Optional[Dict[str, str]] = None) -> DataSource:
        with self._lock:
            source = DataSource(
                source_id=_new_id("ds"),
                name=name,
                source_type=source_type,
                connection=connection,
                description=description,
                schema=schema or {},
            )
            self._data_sources[source.source_id] = source
            _evict_fifo_dict(self._data_sources, _MAX_DATA_SOURCES)
            self._emit(AnalyticsQueryEventKind.DATASOURCE_REGISTERED, {
                "source_id": source.source_id,
                "name": name,
                "source_type": source_type.value,
            })
            return source

    def get_data_source(self, source_id: str) -> Optional[DataSource]:
        with self._lock:
            return self._data_sources.get(source_id)

    def list_data_sources(self, source_type: Optional[DataSourceType] = None,
                          limit: int = 100) -> List[DataSource]:
        with self._lock:
            items = list(self._data_sources.values())
            if source_type is not None:
                items = [s for s in items if s.source_type == source_type]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Metric Catalog
    # ------------------------------------------------------------------

    def register_metric(self, name: str, intent: QueryIntent,
                        formula: str = "",
                        unit: str = "",
                        description: str = "",
                        data_source_id: str = "") -> MetricDefinition:
        with self._lock:
            metric = MetricDefinition(
                metric_id=_new_id("met"),
                name=name,
                intent=intent,
                formula=formula,
                unit=unit,
                description=description,
                data_source_id=data_source_id,
            )
            self._metrics[metric.metric_id] = metric
            _evict_fifo_dict(self._metrics, _MAX_METRICS)
            self._emit(AnalyticsQueryEventKind.METRIC_REGISTERED, {
                "metric_id": metric.metric_id,
                "name": name,
                "intent": intent.value,
            })
            return metric

    def get_metric(self, metric_id: str) -> Optional[MetricDefinition]:
        with self._lock:
            return self._metrics.get(metric_id)

    def list_metrics(self, intent: Optional[QueryIntent] = None,
                     limit: int = 100) -> List[MetricDefinition]:
        with self._lock:
            items = list(self._metrics.values())
            if intent is not None:
                items = [m for m in items if m.intent == intent]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, kind: Optional[AnalyticsQueryEventKind] = None,
                    limit: int = 100) -> List[AnalyticsQueryEvent]:
        with self._lock:
            items = list(self._events)
            if kind is not None:
                items = [e for e in items if e.kind == kind]
            return items[-limit:]

    def get_stats(self) -> AnalyticsQueryStats:
        with self._lock:
            queries = list(self._queries.values())
            pending = sum(1 for q in queries if q.status == QueryStatus.PENDING)
            planned = sum(1 for q in queries if q.status == QueryStatus.PLANNED)
            executing = sum(1 for q in queries if q.status == QueryStatus.EXECUTING)
            completed = sum(1 for q in queries if q.status == QueryStatus.COMPLETED)
            failed = sum(1 for q in queries if q.status == QueryStatus.FAILED)
            completed_results = [r for r in self._results.values() if r.execution_ms > 0]
            avg_ms = (
                sum(r.execution_ms for r in completed_results) / len(completed_results)
                if completed_results else 0.0
            )
            return AnalyticsQueryStats(
                total_queries=len(self._queries),
                pending_queries=pending,
                planned_queries=planned,
                executing_queries=executing,
                completed_queries=completed,
                failed_queries=failed,
                total_saved_queries=len(self._saved_queries),
                total_data_sources=len(self._data_sources),
                total_metrics=len(self._metrics),
                total_events=len(self._events),
                avg_execution_ms=round(avg_ms, 2),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "queries": len(self._queries),
                "results": len(self._results),
                "plans": len(self._plans),
                "saved_queries": len(self._saved_queries),
                "data_sources": len(self._data_sources),
                "metrics": len(self._metrics),
                "events": len(self._events),
            }

    def get_snapshot(self) -> AnalyticsQuerySnapshot:
        with self._lock:
            return AnalyticsQuerySnapshot(
                queries=[q.to_dict() for q in list(self._queries.values())[:20]],
                results=[r.to_dict() for r in list(self._results.values())[:20]],
                saved_queries=[s.to_dict() for s in list(self._saved_queries.values())[:20]],
                data_sources=[d.to_dict() for d in list(self._data_sources.values())[:20]],
                metrics=[m.to_dict() for m in list(self._metrics.values())[:20]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._queries.clear()
            self._results.clear()
            self._plans.clear()
            self._saved_queries.clear()
            self._data_sources.clear()
            self._metrics.clear()
            self._events.clear()
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        # Two data sources: telemetry and analytics_db.
        telemetry = DataSource(
            source_id="ds_telemetry",
            name="Live Gameplay Telemetry",
            source_type=DataSourceType.TELEMETRY,
            connection="kafka://telemetry.internal:9092",
            description="Real-time gameplay event stream from game clients.",
            schema={
                "event_id": "string",
                "player_id": "string",
                "session_id": "string",
                "event_type": "string",
                "timestamp": "datetime",
                "value": "float",
            },
        )
        self._data_sources[telemetry.source_id] = telemetry

        analytics_db = DataSource(
            source_id="ds_analytics_db",
            name="Analytics Warehouse",
            source_type=DataSourceType.ANALYTICS_DB,
            connection="postgresql://analytics.internal:5432/warehouse",
            description="Aggregated analytics warehouse with daily and cohort tables.",
            schema={
                "player_id": "string",
                "cohort": "string",
                "date": "date",
                "dau": "int",
                "sessions": "int",
                "revenue_usd": "float",
            },
        )
        self._data_sources[analytics_db.source_id] = analytics_db

        # Three metric definitions: retention_d7, arpu, session_length.
        retention_metric = MetricDefinition(
            metric_id="met_retention_d7",
            name="retention_d7",
            intent=QueryIntent.RETENTION,
            formula="count(distinct player_id where active_day=install_day+7) / count(distinct player_id)",
            unit="percentage",
            description="Share of players still active 7 days after install.",
            data_source_id="ds_analytics_db",
        )
        self._metrics[retention_metric.metric_id] = retention_metric

        arpu_metric = MetricDefinition(
            metric_id="met_arpu",
            name="arpu",
            intent=QueryIntent.MONETIZATION,
            formula="sum(revenue_usd) / count(distinct player_id)",
            unit="usd",
            description="Average revenue per user across the active player base.",
            data_source_id="ds_analytics_db",
        )
        self._metrics[arpu_metric.metric_id] = arpu_metric

        session_metric = MetricDefinition(
            metric_id="met_session_length",
            name="session_length",
            intent=QueryIntent.ENGAGEMENT,
            formula="avg(session_end_ts - session_start_ts)",
            unit="minutes",
            description="Average session length in minutes per player.",
            data_source_id="ds_telemetry",
        )
        self._metrics[session_metric.metric_id] = session_metric

        # Two saved queries: D7 retention by cohort, and top 10 churn risk players.
        saved_retention = SavedQuery(
            saved_id="sq_d7_retention_cohort",
            name="D7 retention by cohort",
            text="What is our D7 retention broken down by cohort?",
            intent=QueryIntent.RETENTION,
            description="Weekly Day-7 retention split by acquisition cohort.",
            created_by="designer_alice",
            tags=["retention", "cohort", "weekly"],
        )
        self._saved_queries[saved_retention.saved_id] = saved_retention

        saved_churn = SavedQuery(
            saved_id="sq_top10_churn_risk",
            name="Top 10 churn risk players",
            text="Show me the top 10 players at highest risk of churning",
            intent=QueryIntent.ENGAGEMENT,
            description="Players with steeply declining session counts in the last 7 days.",
            created_by="designer_bob",
            tags=["engagement", "churn", "risk"],
        )
        self._saved_queries[saved_churn.saved_id] = saved_churn


def get_analytics_query_engine() -> AnalyticsQueryEngine:
    """Factory function returning the singleton AnalyticsQueryEngine instance."""
    return AnalyticsQueryEngine.get_instance()
