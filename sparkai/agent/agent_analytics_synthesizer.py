"""
SparkLabs Agent - Game Analytics Synthesizer

Transforms raw game telemetry into actionable narrative insights for the
SparkLabs AI-native game engine. The synthesizer ingests gameplay events,
computes metrics across multiple categories, detects anomalies through
statistical deviation analysis, discovers recurring gameplay patterns,
tracks player journeys from onboarding to endgame, and produces natural
language recommendations that designers can act on.

The agent treats analytics as a first-class AI capability: events are not
merely stored, they are continuously synthesized into insights, each
carrying evidence, affected player segments, confidence scores, and
concrete next steps. Anomaly detection uses z-score based statistical
deviation. Pattern matching looks for recurring event sequences across
the player base. Churn risk combines recency, frequency, and duration
signals. Engagement scoring fuses session frequency, playtime, social
interactions, and progression momentum.

Architecture:
  AnalyticsSynthesizer (singleton)
    |-- GameEvent, MetricDefinition, MetricValue, Insight, AnomalyAlert,
        PlayerJourney, PatternMatch, Recommendation, AnalyticsReport,
        AnalyticsStats, AnalyticsConfig, AnalyticsSnapshot, AnalyticsEvent
    |-- EventCategory, InsightType, InsightSeverity, InsightStatus,
        JourneyStage, MetricAggregation, AnalyticsEventKind, TimeWindow

Core Capabilities:
  - register_metric / remove_metric / get_metric / list_metrics: catalog
    of metric definitions with aggregation rules and thresholds.
  - ingest_event / ingest_batch / get_event / list_events: telemetry
    ingestion with per-player indexing and category filtering.
  - compute_metric / compute_all_metrics: statistical aggregation of event
    values using sum, avg, min, max, count, median, percentile_95, std_dev.
  - detect_insight / analyze_trend: AI-driven insight detection across
    trend, anomaly, correlation, pattern, prediction, and summary types.
  - detect_anomaly / scan_anomalies / resolve_anomaly: z-score based
    anomaly detection with configurable sensitivity and alert lifecycle.
  - find_pattern / discover_patterns: recurring event sequence discovery
    across gameplay, social, economic, combat, and exploration categories.
  - track_player_journey / update_journey_stage / assess_churn_risk /
    compute_engagement: player lifecycle tracking from onboarding to
    endgame with churn prediction and engagement scoring.
  - generate_recommendation / auto_generate_recommendations /
    apply_recommendation / dismiss_recommendation: actionable next-step
    generation tied to detected insights.
  - compile_report / get_player_summary / get_segment_summary: narrative
    report compilation and per-player / per-segment deep dives.
  - get_stats / get_snapshot / get_status / get_config / set_config /
    list_events_log / tick: observability, tuning, and lifecycle control.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`AnalyticsSynthesizer.get_instance` or the module-level
:func:`get_analytics_synthesizer` factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_EVENTS: int = 50000
_MAX_METRICS: int = 500
_MAX_INSIGHTS: int = 5000
_MAX_ANOMALIES: int = 5000
_MAX_JOURNEYS: int = 10000
_MAX_PATTERNS: int = 2000
_MAX_RECOMMENDATIONS: int = 5000
_MAX_REPORTS: int = 1000
_MAX_METRIC_VALUES: int = 50000
_MAX_EVENTS_LOG: int = 10000

# Priority ordering used when ranking recommendations.
_PRIORITY_ORDER: Dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# Time window durations in seconds.
_TIME_WINDOW_SECONDS: Dict[str, float] = {
    "last_hour": 3600.0,
    "last_24_hours": 86400.0,
    "last_7_days": 604800.0,
    "last_30_days": 2592000.0,
    "all_time": float("inf"),
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    """Return the current Unix timestamp."""
    return time.time()


def _new_id(prefix: str = "") -> str:
    """Generate a short unique ID with an optional prefix."""
    base = uuid.uuid4().hex[:10]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits within max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits within max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value to a JSON-serializable form."""
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
    """Convert a dataclass instance to a dict, serializing nested enums."""
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


def _mean(values: List[float]) -> float:
    """Compute the arithmetic mean of a list of floats."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std_dev(values: List[float]) -> float:
    """Compute the population standard deviation of a list of floats."""
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((v - avg) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _median(values: List[float]) -> float:
    """Compute the median of a list of floats."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
    return sorted_vals[mid]


def _percentile(values: List[float], p: float) -> float:
    """Compute the p-th percentile of a list of floats using linear interpolation."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = k - f
    if f + 1 < len(sorted_vals):
        return sorted_vals[f] + c * (sorted_vals[f + 1] - sorted_vals[f])
    return sorted_vals[f]


def _linear_slope(values: List[float]) -> float:
    """Compute the slope of a simple least-squares linear fit over the values."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Convert a string or enum member to an enum member, returning default on failure."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _time_window_seconds(time_window: str) -> float:
    """Return the duration in seconds for a named time window."""
    return _TIME_WINDOW_SECONDS.get(time_window, float("inf"))


def _compute_aggregation(values: List[float], aggregation: str) -> float:
    """Apply the named aggregation to a list of float values."""
    if not values:
        return 0.0
    if aggregation == "sum":
        return float(sum(values))
    if aggregation == "avg":
        return _mean(values)
    if aggregation == "min":
        return float(min(values))
    if aggregation == "max":
        return float(max(values))
    if aggregation == "count":
        return float(len(values))
    if aggregation == "median":
        return _median(values)
    if aggregation == "percentile_95":
        return _percentile(values, 95.0)
    if aggregation == "std_dev":
        return _std_dev(values)
    return float(sum(values))


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class EventCategory(str, Enum):
    """Top-level classification for game telemetry events."""

    GAMEPLAY = "gameplay"
    SOCIAL = "social"
    ECONOMIC = "economic"
    COMBAT = "combat"
    EXPLORATION = "exploration"
    PROGRESSION = "progression"
    RETENTION = "retention"
    MONETIZATION = "monetization"
    TECHNICAL = "technical"
    CUSTOM = "custom"


class InsightType(str, Enum):
    """The analytical nature of a detected insight."""

    TREND = "trend"
    ANOMALY = "anomaly"
    CORRELATION = "correlation"
    PATTERN = "pattern"
    PREDICTION = "prediction"
    RECOMMENDATION = "recommendation"
    ALERT = "alert"
    SUMMARY = "summary"


class InsightSeverity(str, Enum):
    """How urgent or impactful a detected insight is."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InsightStatus(str, Enum):
    """The lifecycle state of a detected insight."""

    DETECTED = "detected"
    ANALYZING = "analyzing"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    ACTED_UPON = "acted_upon"
    RESOLVED = "resolved"


class JourneyStage(str, Enum):
    """A player's current position in the game lifecycle."""

    ONBOARDING = "onboarding"
    TUTORIAL = "tutorial"
    EARLY_GAME = "early_game"
    MID_GAME = "mid_game"
    LATE_GAME = "late_game"
    ENDGAME = "endgame"
    CHURNED = "churned"
    RETURNED = "returned"


class MetricAggregation(str, Enum):
    """The statistical aggregation applied when computing a metric."""

    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    MEDIAN = "median"
    PERCENTILE_95 = "percentile_95"
    STD_DEV = "std_dev"


class AnalyticsEventKind(str, Enum):
    """The kind of audit event emitted by the synthesizer."""

    EVENT_INGESTED = "event_ingested"
    INSIGHT_DETECTED = "insight_detected"
    ANOMALY_ALERTED = "anomaly_alerted"
    JOURNEY_UPDATED = "journey_updated"
    PATTERN_FOUND = "pattern_found"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    METRIC_COMPUTED = "metric_computed"
    REPORT_COMPILED = "report_compiled"
    THRESHOLD_BREACHED = "threshold_breached"


class TimeWindow(str, Enum):
    """A named time range for filtering events and computing metrics."""

    LAST_HOUR = "last_hour"
    LAST_24_HOURS = "last_24_hours"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    ALL_TIME = "all_time"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class GameEvent:
    """A single raw telemetry event from a game client."""

    event_id: str
    player_id: str
    session_id: str
    category: EventCategory
    event_name: str
    value: float
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)
    tick: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetricDefinition:
    """A named metric with its aggregation rule and alert thresholds."""

    metric_id: str
    name: str
    category: EventCategory
    aggregation: MetricAggregation
    description: str = ""
    formula: str = ""
    unit: str = ""
    threshold_warning: float = 0.0
    threshold_critical: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetricValue:
    """A computed metric value for a player or globally."""

    metric_id: str
    value: float
    timestamp: float = field(default_factory=_now)
    player_id: str = ""
    sample_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Insight:
    """A narrative finding derived from telemetry analysis."""

    insight_id: str
    type: InsightType
    severity: InsightSeverity
    status: InsightStatus
    category: EventCategory
    title: str
    description: str
    evidence: List[str] = field(default_factory=list)
    affected_players: List[str] = field(default_factory=list)
    confidence: float = 0.0
    detected_at: float = field(default_factory=_now)
    recommendations: List[str] = field(default_factory=list)
    impact_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnomalyAlert:
    """An alert raised when a metric deviates beyond expected bounds."""

    alert_id: str
    metric_id: str
    expected_value: float
    actual_value: float
    deviation_percent: float
    severity: InsightSeverity
    player_id: str
    timestamp: float = field(default_factory=_now)
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerJourney:
    """A player's lifecycle from first session to current state."""

    player_id: str
    current_stage: JourneyStage
    stage_transitions: List[Dict[str, Any]] = field(default_factory=list)
    total_sessions: int = 0
    total_playtime: float = 0.0
    key_moments: List[str] = field(default_factory=list)
    churn_risk: float = 0.0
    engagement_score: float = 0.0
    last_active: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PatternMatch:
    """A recurring event sequence discovered across the player base."""

    pattern_id: str
    name: str
    description: str
    category: EventCategory
    occurrences: int = 0
    first_seen: float = field(default_factory=_now)
    last_seen: float = field(default_factory=_now)
    confidence: float = 0.0
    affected_count: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Recommendation:
    """An actionable next step tied to a detected insight."""

    recommendation_id: str
    insight_id: str
    title: str
    description: str
    priority: str = "medium"
    action_type: str = "investigate"
    expected_impact: float = 0.0
    target_segment: str = "all"
    steps: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnalyticsReport:
    """A compiled analytics report for a time window."""

    report_id: str
    title: str
    time_window: str
    summary: str
    key_metrics: Dict[str, float] = field(default_factory=dict)
    top_insights: List[str] = field(default_factory=list)
    top_recommendations: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnalyticsStats:
    """Aggregate statistics for the analytics synthesizer."""

    total_events_ingested: int = 0
    total_insights_detected: int = 0
    total_anomalies_alerted: int = 0
    total_recommendations_generated: int = 0
    total_reports_compiled: int = 0
    total_patterns_found: int = 0
    active_alerts: int = 0
    players_tracked: int = 0
    average_insight_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnalyticsConfig:
    """Tunable configuration for the analytics synthesizer."""

    max_events_retained: int = 50000
    max_insights: int = 5000
    enable_anomaly_detection: bool = True
    enable_pattern_matching: bool = True
    enable_journey_tracking: bool = True
    anomaly_sensitivity: float = 0.5
    insight_confidence_threshold: float = 0.6
    max_recommendations: int = 5000
    report_generation_interval: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnalyticsSnapshot:
    """A point-in-time snapshot of synthesizer state."""

    tick_count: int = 0
    events_buffered: int = 0
    insights_active: int = 0
    anomalies_active: int = 0
    journeys_tracked: int = 0
    patterns_active: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnalyticsEvent:
    """An audit event emitted by the analytics synthesizer."""

    event_id: str
    kind: AnalyticsEventKind
    tick: int
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Recommendation Templates
# ---------------------------------------------------------------------------

# Templates used by auto_generate_recommendations. Each entry maps an
# insight type to a list of (action_type, title, description, priority,
# expected_impact) tuples.
_RECOMMENDATION_TEMPLATES: Dict[str, List[Tuple[str, str, str, str, float]]] = {
    "trend": [
        ("tune_pacing", "Adjust Content Pacing",
         "The detected trend indicates a shift in player behavior. Review and "
         "adjust content release pacing to align with the observed trajectory.",
         "medium", 0.4),
        ("balance_difficulty", "Rebalance Difficulty Curve",
         "Trend analysis suggests players may be hitting a difficulty wall. "
         "Consider smoothing the difficulty progression for the affected segment.",
         "high", 0.6),
    ],
    "anomaly": [
        ("investigate", "Investigate Root Cause",
         "An anomalous metric deviation was detected. Initiate a root-cause "
         "investigation to determine whether this is a bug, a design issue, "
         "or an expected outlier.",
         "high", 0.7),
        ("alert_liveops", "Alert Live-Ops Team",
         "Notify the live-ops team about the anomaly for manual review and "
         "potential intervention.",
         "medium", 0.3),
    ],
    "correlation": [
        ("cross_system_tuning", "Cross-System Tuning",
         "A correlation between two systems was detected. Consider jointly "
         "tuning the correlated systems to optimize the overall experience.",
         "medium", 0.5),
    ],
    "pattern": [
        ("content_optimization", "Optimize Content Flow",
         "A recurring gameplay pattern was identified. Use this insight to "
         "optimize the content flow and reduce friction along the detected path.",
         "medium", 0.4),
    ],
    "prediction": [
        ("proactive_intervention", "Proactive Intervention",
         "Predictive analysis indicates a likely future outcome. Consider "
         "proactive intervention to steer the outcome toward a positive direction.",
         "high", 0.6),
    ],
    "alert": [
        ("immediate_action", "Take Immediate Action",
         "A critical alert was triggered. Review and take immediate action to "
         "mitigate the identified risk.",
         "critical", 0.8),
    ],
    "summary": [
        ("review_summary", "Review Analytics Summary",
         "A periodic analytics summary is available. Review the summary for "
         "overall health and identify areas for improvement.",
         "low", 0.2),
    ],
    "recommendation": [
        ("follow_up", "Follow Up on Pending Actions",
         "Prior recommendations are pending action. Follow up with the "
         "responsible teams to ensure timely execution.",
         "low", 0.2),
    ],
}


# ---------------------------------------------------------------------------
# Analytics Synthesizer Singleton
# ---------------------------------------------------------------------------


class AnalyticsSynthesizer:
    """Singleton agent that synthesizes game telemetry into narrative insights.

    The synthesizer maintains game events, metric definitions, computed metric
    values, detected insights, anomaly alerts, player journeys, discovered
    patterns, generated recommendations, and compiled reports. It applies
    statistical analysis to detect anomalies, sequence analysis to discover
    patterns, and lifecycle tracking to assess churn risk and engagement.

    All mutations are guarded by a reentrant lock so the synthesizer is safe
    to call from multiple threads. The AI capabilities center on four original
    algorithms:

      - Statistical anomaly detection using z-score deviation with configurable
        sensitivity mapping to the z-score threshold.
      - Sequence pattern matching that extracts recurring event bigrams and
        trigrams across the player base.
      - Churn risk scoring that combines recency, frequency, and duration into
        a normalized 0-1 risk score.
      - Engagement scoring that fuses session frequency, playtime, social
        interactions, and progression momentum into a 0-1 score.
    """

    _instance: Optional["AnalyticsSynthesizer"] = None
    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction and Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._seeded: bool = False

        # Core registries
        self._metrics: Dict[str, MetricDefinition] = {}
        self._events_store: Dict[str, GameEvent] = {}
        self._events_by_player: Dict[str, List[str]] = {}
        self._metric_values: Dict[str, MetricValue] = {}
        self._insights: Dict[str, Insight] = {}
        self._anomalies: Dict[str, AnomalyAlert] = {}
        self._journeys: Dict[str, PlayerJourney] = {}
        self._patterns: Dict[str, PatternMatch] = {}
        self._recommendations: Dict[str, Recommendation] = {}
        self._reports: Dict[str, AnalyticsReport] = {}

        # Audit log
        self._events_log: List[AnalyticsEvent] = []

        # Bookkeeping
        self._config = AnalyticsConfig()
        self._stats = AnalyticsStats()
        self._tick_count: int = 0

        # Cumulative counters (never reset by expiry)
        self._total_events_ingested: int = 0
        self._total_insights_detected: int = 0
        self._total_anomalies_alerted: int = 0
        self._total_recommendations_generated: int = 0
        self._total_reports_compiled: int = 0
        self._total_patterns_found: int = 0

    @classmethod
    def get_instance(cls) -> "AnalyticsSynthesizer":
        """Return the singleton instance, creating it on first call."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Load seed data exactly once. Safe to call repeatedly."""
        with self._init_lock:
            if self._seeded:
                return
            self._seed_data()
            self._seeded = True
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(
        self, kind: AnalyticsEventKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event to the log."""
        event = AnalyticsEvent(
            event_id=_new_id("aevt"),
            kind=kind,
            tick=self._tick_count,
            payload=payload or {},
        )
        self._events_log.append(event)
        _evict_fifo_list(self._events_log, _MAX_EVENTS_LOG)

    def _refresh_stats(self) -> None:
        """Recompute derived statistics from current state."""
        self._stats.total_events_ingested = self._total_events_ingested
        self._stats.total_insights_detected = self._total_insights_detected
        self._stats.total_anomalies_alerted = self._total_anomalies_alerted
        self._stats.total_recommendations_generated = (
            self._total_recommendations_generated
        )
        self._stats.total_reports_compiled = self._total_reports_compiled
        self._stats.total_patterns_found = self._total_patterns_found
        self._stats.active_alerts = sum(
            1 for a in self._anomalies.values() if a.status == "active"
        )
        self._stats.players_tracked = len(self._events_by_player)
        active_insights = [
            i for i in self._insights.values()
            if i.status in (
                InsightStatus.DETECTED.value,
                InsightStatus.ANALYZING.value,
                InsightStatus.CONFIRMED.value,
            )
        ]
        if active_insights:
            self._stats.average_insight_confidence = round(
                sum(i.confidence for i in active_insights) / len(active_insights),
                4,
            )
        else:
            self._stats.average_insight_confidence = 0.0

    def _filter_events(
        self,
        category: Optional[str] = None,
        player_id: Optional[str] = None,
        time_window: str = "all_time",
    ) -> List[GameEvent]:
        """Return events matching the given filters, sorted by timestamp."""
        if player_id is not None:
            event_ids = self._events_by_player.get(player_id, [])
            events = [self._events_store[eid] for eid in event_ids
                      if eid in self._events_store]
        else:
            events = list(self._events_store.values())

        if category is not None:
            events = [e for e in events if e.category == category]

        window_seconds = _time_window_seconds(time_window)
        if window_seconds != float("inf"):
            cutoff = _now() - window_seconds
            events = [e for e in events if e.timestamp >= cutoff]

        events.sort(key=lambda e: e.timestamp)
        return events

    def _unique_player_ids(self) -> List[str]:
        """Return all unique player IDs that have ingested events."""
        return list(self._events_by_player.keys())

    def _events_for_player(self, player_id: str) -> List[GameEvent]:
        """Return all events for a player, sorted by timestamp."""
        event_ids = self._events_by_player.get(player_id, [])
        return [self._events_store[eid] for eid in event_ids
                if eid in self._events_store]

    def _determine_stage(self, player_id: str) -> str:
        """Determine the journey stage for a player based on their events."""
        events = self._events_for_player(player_id)
        if not events:
            return JourneyStage.ONBOARDING.value

        latest_event = max(events, key=lambda e: e.timestamp)
        days_since_last = (_now() - latest_event.timestamp) / 86400.0

        journey = self._journeys.get(player_id)
        if days_since_last > 7.0:
            if journey and journey.current_stage == JourneyStage.CHURNED.value:
                return JourneyStage.RETURNED.value
            return JourneyStage.CHURNED.value

        # Check for tutorial events
        has_tutorial = any(
            "tutorial" in e.event_name.lower() for e in events
        )
        if has_tutorial and len(events) < 5:
            return JourneyStage.TUTORIAL.value

        sessions = set(e.session_id for e in events)
        session_count = len(sessions)
        if session_count < 3:
            return JourneyStage.EARLY_GAME.value
        if session_count < 10:
            return JourneyStage.MID_GAME.value
        if session_count < 30:
            return JourneyStage.LATE_GAME.value
        return JourneyStage.ENDGAME.value

    def _z_threshold(self) -> float:
        """Map the configured anomaly sensitivity to a z-score threshold.

        Higher sensitivity means a lower threshold (more anomalies detected).
        Sensitivity 0.0 maps to z=3.0, sensitivity 1.0 maps to z=1.0.
        """
        sensitivity = max(0.0, min(1.0, self._config.anomaly_sensitivity))
        return 3.0 - 2.0 * sensitivity

    def _severity_from_deviation(
        self, deviation_percent: float,
    ) -> InsightSeverity:
        """Map a deviation percentage to an insight severity."""
        abs_dev = abs(deviation_percent)
        if abs_dev >= 100.0:
            return InsightSeverity.CRITICAL
        if abs_dev >= 50.0:
            return InsightSeverity.HIGH
        if abs_dev >= 25.0:
            return InsightSeverity.MEDIUM
        if abs_dev >= 10.0:
            return InsightSeverity.LOW
        return InsightSeverity.INFO

    def _severity_from_threshold(
        self, value: float, warning: float, critical: float,
    ) -> Optional[InsightSeverity]:
        """Return a severity if the value crosses a threshold, else None."""
        if critical != 0.0 and value >= critical:
            return InsightSeverity.CRITICAL
        if warning != 0.0 and value >= warning:
            return InsightSeverity.HIGH
        return None

    def _expire_old_data(self) -> int:
        """Evict data that exceeds configured capacity limits. Returns count."""
        expired = 0
        while len(self._events_store) > self._config.max_events_retained:
            oldest_key = next(iter(self._events_store), None)
            if oldest_key is None:
                break
            event = self._events_store.pop(oldest_key)
            expired += 1
            player_events = self._events_by_player.get(event.player_id)
            if player_events:
                try:
                    player_events.remove(oldest_key)
                except ValueError:
                    pass
                if not player_events:
                    self._events_by_player.pop(event.player_id, None)

        while len(self._insights) > self._config.max_insights:
            oldest_key = next(iter(self._insights), None)
            if oldest_key is None:
                break
            del self._insights[oldest_key]
            expired += 1

        while len(self._recommendations) > self._config.max_recommendations:
            oldest_key = next(iter(self._recommendations), None)
            if oldest_key is None:
                break
            del self._recommendations[oldest_key]
            expired += 1

        _evict_fifo_dict(self._metric_values, _MAX_METRIC_VALUES)
        _evict_fifo_dict(self._anomalies, _MAX_ANOMALIES)
        _evict_fifo_dict(self._patterns, _MAX_PATTERNS)
        _evict_fifo_dict(self._reports, _MAX_REPORTS)
        return expired

    # ------------------------------------------------------------------
    # Metric Management
    # ------------------------------------------------------------------

    def register_metric(
        self,
        metric_id: str,
        name: str,
        category: str,
        aggregation: str,
        description: str = "",
        threshold_warning: float = 0.0,
        threshold_critical: float = 0.0,
    ) -> Tuple[bool, str, Optional[MetricDefinition]]:
        """Register a new metric definition with aggregation and thresholds."""
        with self._lock:
            if not metric_id or not name:
                return (False, "metric_id and name are required", None)
            if metric_id in self._metrics:
                return (False, f"Metric already exists: {metric_id}", None)

            cat = _coerce_enum(EventCategory, category)
            if cat is None:
                return (False, f"Invalid category: {category}", None)

            agg = _coerce_enum(MetricAggregation, aggregation)
            if agg is None:
                return (False, f"Invalid aggregation: {aggregation}", None)

            metric = MetricDefinition(
                metric_id=metric_id,
                name=name,
                category=cat,
                aggregation=agg,
                description=description,
                formula="",
                unit="",
                threshold_warning=float(threshold_warning),
                threshold_critical=float(threshold_critical),
            )
            self._metrics[metric_id] = metric
            _evict_fifo_dict(self._metrics, _MAX_METRICS)
            self._emit(AnalyticsEventKind.METRIC_COMPUTED, {
                "action": "metric_registered",
                "metric_id": metric_id,
                "name": name,
                "category": cat.value,
                "aggregation": agg.value,
            })
            return (True, f"Metric registered: {metric_id}", metric)

    def remove_metric(self, metric_id: str) -> Tuple[bool, str]:
        """Remove a metric definition by ID."""
        with self._lock:
            if metric_id not in self._metrics:
                return (False, f"Metric not found: {metric_id}")
            del self._metrics[metric_id]
            self._emit(AnalyticsEventKind.METRIC_COMPUTED, {
                "action": "metric_removed",
                "metric_id": metric_id,
            })
            return (True, f"Metric removed: {metric_id}")

    def get_metric(self, metric_id: str) -> Optional[MetricDefinition]:
        """Return a metric definition by ID."""
        with self._lock:
            return self._metrics.get(metric_id)

    def list_metrics(
        self, category: Optional[str] = None,
    ) -> List[MetricDefinition]:
        """List metric definitions, optionally filtered by category."""
        with self._lock:
            items = list(self._metrics.values())
            if category is not None:
                items = [m for m in items if m.category == category]
            return items

    # ------------------------------------------------------------------
    # Event Ingestion
    # ------------------------------------------------------------------

    def ingest_event(
        self,
        player_id: str,
        session_id: str,
        category: str,
        event_name: str,
        value: float = 0.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[GameEvent]]:
        """Ingest a single game telemetry event."""
        with self._lock:
            if not player_id or not event_name:
                return (False, "player_id and event_name are required", None)

            cat = _coerce_enum(EventCategory, category, EventCategory.CUSTOM)
            if cat is None:
                cat = EventCategory.CUSTOM

            event = GameEvent(
                event_id=_new_id("ge"),
                player_id=player_id,
                session_id=session_id,
                category=cat,
                event_name=event_name,
                value=float(value),
                properties=properties or {},
                timestamp=_now(),
                tick=self._tick_count,
            )
            self._events_store[event.event_id] = event
            _evict_fifo_dict(self._events_store, self._config.max_events_retained)

            if player_id not in self._events_by_player:
                self._events_by_player[player_id] = []
            self._events_by_player[player_id].append(event.event_id)

            self._total_events_ingested += 1
            self._emit(AnalyticsEventKind.EVENT_INGESTED, {
                "event_id": event.event_id,
                "player_id": player_id,
                "category": cat.value,
                "event_name": event_name,
            })
            return (True, f"Event ingested: {event.event_id}", event)

    def ingest_batch(
        self, events: List[Dict[str, Any]],
    ) -> Tuple[bool, str, int]:
        """Ingest a batch of events from a list of dicts. Returns count."""
        with self._lock:
            if not events:
                return (False, "No events provided", 0)
            count = 0
            for evt_dict in events:
                ok, _, _ = self.ingest_event(
                    player_id=evt_dict.get("player_id", ""),
                    session_id=evt_dict.get("session_id", ""),
                    category=evt_dict.get("category", "custom"),
                    event_name=evt_dict.get("event_name", ""),
                    value=evt_dict.get("value", 0.0),
                    properties=evt_dict.get("properties"),
                )
                if ok:
                    count += 1
            return (True, f"Ingested {count} events", count)

    def get_event(self, event_id: str) -> Optional[GameEvent]:
        """Return a game event by ID."""
        with self._lock:
            return self._events_store.get(event_id)

    def list_events(
        self,
        category: Optional[str] = None,
        player_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[GameEvent]:
        """List game events with optional category and player filters."""
        with self._lock:
            events = self._filter_events(
                category=category, player_id=player_id,
                time_window="all_time",
            )
            return events[-limit:]

    # ------------------------------------------------------------------
    # Metric Computation
    # ------------------------------------------------------------------

    def compute_metric(
        self,
        metric_id: str,
        player_id: str = "",
        time_window: str = "all_time",
    ) -> Tuple[bool, str, Optional[MetricValue]]:
        """Compute a metric value for a player or globally over a time window."""
        with self._lock:
            metric = self._metrics.get(metric_id)
            if metric is None:
                return (False, f"Metric not found: {metric_id}", None)

            events = self._filter_events(
                category=metric.category.value,
                player_id=player_id if player_id else None,
                time_window=time_window,
            )
            values = [e.value for e in events]
            computed = _compute_aggregation(values, metric.aggregation.value)
            sample_count = len(values)

            mv = MetricValue(
                metric_id=metric_id,
                value=round(computed, 6),
                timestamp=_now(),
                player_id=player_id,
                sample_count=sample_count,
            )
            cache_key = f"{metric_id}:{player_id}" if player_id else f"{metric_id}:global"
            self._metric_values[cache_key] = mv
            _evict_fifo_dict(self._metric_values, _MAX_METRIC_VALUES)

            # Check thresholds and emit breach events
            severity = self._severity_from_threshold(
                computed, metric.threshold_warning, metric.threshold_critical,
            )
            if severity is not None:
                self._emit(AnalyticsEventKind.THRESHOLD_BREACHED, {
                    "metric_id": metric_id,
                    "value": computed,
                    "threshold_warning": metric.threshold_warning,
                    "threshold_critical": metric.threshold_critical,
                    "severity": severity.value,
                    "player_id": player_id,
                })

            self._emit(AnalyticsEventKind.METRIC_COMPUTED, {
                "action": "metric_computed",
                "metric_id": metric_id,
                "player_id": player_id,
                "value": computed,
                "sample_count": sample_count,
                "time_window": time_window,
            })
            msg = f"Metric computed: {metric_id}={computed:.4f} ({sample_count} samples)"
            return (True, msg, mv)

    def compute_all_metrics(
        self, time_window: str = "all_time",
    ) -> Tuple[bool, str, List[MetricValue]]:
        """Compute all registered metrics globally over a time window."""
        with self._lock:
            results: List[MetricValue] = []
            for metric_id in list(self._metrics.keys()):
                ok, _, mv = self.compute_metric(metric_id, "", time_window)
                if ok and mv is not None:
                    results.append(mv)
            return (True, f"Computed {len(results)} metrics", results)

    # ------------------------------------------------------------------
    # Insight Detection and Management
    # ------------------------------------------------------------------

    def detect_insight(
        self,
        category: str,
        type: str,
    ) -> Tuple[bool, str, Optional[Insight]]:
        """Detect a new insight of the given type for the given category."""
        with self._lock:
            cat = _coerce_enum(EventCategory, category)
            if cat is None:
                return (False, f"Invalid category: {category}", None)

            insight_type = _coerce_enum(InsightType, type)
            if insight_type is None:
                return (False, f"Invalid insight type: {type}", None)

            events = self._filter_events(category=cat.value, time_window="all_time")
            if not events:
                return (True, "No events found for category", None)

            if insight_type == InsightType.TREND:
                return self._detect_trend_insight(cat, events)
            if insight_type == InsightType.ANOMALY:
                return self._detect_anomaly_insight(cat, events)
            if insight_type == InsightType.CORRELATION:
                return self._detect_correlation_insight(cat, events)
            if insight_type == InsightType.PATTERN:
                return self._detect_pattern_insight(cat, events)
            if insight_type == InsightType.PREDICTION:
                return self._detect_prediction_insight(cat, events)
            if insight_type == InsightType.SUMMARY:
                return self._detect_summary_insight(cat, events)
            if insight_type == InsightType.ALERT:
                return self._detect_alert_insight(cat, events)
            if insight_type == InsightType.RECOMMENDATION:
                return self._detect_recommendation_insight(cat, events)
            return (False, f"Unsupported insight type: {type}", None)

    def _detect_trend_insight(
        self, cat: EventCategory, events: List[GameEvent],
    ) -> Tuple[bool, str, Optional[Insight]]:
        """Detect a trend insight by analyzing value trajectory over time."""
        if len(events) < 3:
            return (True, "Insufficient events for trend analysis", None)

        # Sort events into time buckets and compute average value per bucket
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        bucket_count = min(5, len(sorted_events))
        bucket_size = max(1, len(sorted_events) // bucket_count)
        bucket_avgs: List[float] = []
        for i in range(0, len(sorted_events), bucket_size):
            chunk = sorted_events[i:i + bucket_size]
            bucket_avgs.append(_mean([e.value for e in chunk]))

        slope = _linear_slope(bucket_avgs)
        avg_value = _mean([e.value for e in events])
        if avg_value == 0:
            avg_value = 1.0
        relative_slope = slope / abs(avg_value)

        if relative_slope > 0.05:
            direction = "upward"
            severity = InsightSeverity.MEDIUM
        elif relative_slope < -0.05:
            direction = "downward"
            severity = InsightSeverity.HIGH
        else:
            direction = "stable"
            severity = InsightSeverity.INFO

        affected = list({e.player_id for e in events})
        confidence = min(1.0, len(events) / 50.0)
        insight = Insight(
            insight_id=_new_id("ins"),
            type=InsightType.TREND,
            severity=severity,
            status=InsightStatus.DETECTED,
            category=cat,
            title=f"{cat.value.capitalize()} metric trending {direction}",
            description=(
                f"Over {len(events)} events in the {cat.value} category, "
                f"the average value shows a {direction} trend "
                f"(slope={slope:.4f}, avg={avg_value:.4f})."
            ),
            evidence=[
                f"Bucket averages: {[round(v, 4) for v in bucket_avgs]}",
                f"Relative slope: {relative_slope:.4f}",
                f"Total events analyzed: {len(events)}",
            ],
            affected_players=affected[:20],
            confidence=round(confidence, 4),
            impact_score=round(abs(relative_slope), 4),
        )
        self._insights[insight.insight_id] = insight
        _evict_fifo_dict(self._insights, self._config.max_insights)
        self._total_insights_detected += 1
        self._emit(AnalyticsEventKind.INSIGHT_DETECTED, {
            "insight_id": insight.insight_id,
            "type": InsightType.TREND.value,
            "category": cat.value,
            "severity": severity.value,
        })
        return (True, f"Trend insight detected: {insight.insight_id}", insight)

    def _detect_anomaly_insight(
        self, cat: EventCategory, events: List[GameEvent],
    ) -> Tuple[bool, str, Optional[Insight]]:
        """Detect an anomaly insight by looking for value outliers."""
        if len(events) < 5:
            return (True, "Insufficient events for anomaly analysis", None)

        values = [e.value for e in events]
        avg = _mean(values)
        std = _std_dev(values)
        if std == 0:
            return (True, "No variance in values; no anomaly detected", None)

        z_threshold = self._z_threshold()
        outliers = []
        for e in events:
            z = abs(e.value - avg) / std
            if z > z_threshold:
                outliers.append((e, z))

        if not outliers:
            return (True, "No anomalies detected in category", None)

        affected = list({e.player_id for e, _ in outliers})
        max_z = max(z for _, z in outliers)
        severity = self._severity_from_deviation(max_z * 25.0)
        confidence = min(1.0, len(outliers) / 10.0)

        insight = Insight(
            insight_id=_new_id("ins"),
            type=InsightType.ANOMALY,
            severity=severity,
            status=InsightStatus.DETECTED,
            category=cat,
            title=f"Anomalous {cat.value} values detected in {len(outliers)} events",
            description=(
                f"{len(outliers)} out of {len(events)} events in the {cat.value} "
                f"category deviate significantly from the mean (avg={avg:.4f}, "
                f"std={std:.4f}, max z-score={max_z:.2f})."
            ),
            evidence=[
                f"Mean: {avg:.4f}, Std Dev: {std:.4f}",
                f"Z-score threshold: {z_threshold:.2f}",
                f"Outlier count: {len(outliers)}",
            ],
            affected_players=affected[:20],
            confidence=round(confidence, 4),
            impact_score=round(min(1.0, max_z / 5.0), 4),
        )
        self._insights[insight.insight_id] = insight
        _evict_fifo_dict(self._insights, self._config.max_insights)
        self._total_insights_detected += 1
        self._emit(AnalyticsEventKind.INSIGHT_DETECTED, {
            "insight_id": insight.insight_id,
            "type": InsightType.ANOMALY.value,
            "category": cat.value,
            "severity": severity.value,
        })
        return (True, f"Anomaly insight detected: {insight.insight_id}", insight)

    def _detect_correlation_insight(
        self, cat: EventCategory, events: List[GameEvent],
    ) -> Tuple[bool, str, Optional[Insight]]:
        """Detect a correlation insight by looking for co-occurring event types."""
        if len(events) < 10:
            return (True, "Insufficient events for correlation analysis", None)

        # Group events by session and count event name pairs
        session_events: Dict[str, List[str]] = {}
        for e in events:
            if e.session_id not in session_events:
                session_events[e.session_id] = []
            session_events[e.session_id].append(e.event_name)

        pair_counts: Dict[Tuple[str, str], int] = {}
        for session_id, names in session_events.items():
            unique_names = sorted(set(names))
            for i in range(len(unique_names)):
                for j in range(i + 1, len(unique_names)):
                    pair = (unique_names[i], unique_names[j])
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1

        if not pair_counts:
            return (True, "No event pairs found for correlation", None)

        best_pair = max(pair_counts, key=pair_counts.get)
        best_count = pair_counts[best_pair]
        total_sessions = len(session_events)
        correlation_strength = best_count / total_sessions if total_sessions else 0

        if correlation_strength < 0.3:
            return (True, "No strong correlations found", None)

        affected = list({e.player_id for e in events
                         if e.event_name in best_pair})[:20]
        confidence = min(1.0, correlation_strength)
        severity = InsightSeverity.MEDIUM if correlation_strength > 0.5 else InsightSeverity.LOW

        insight = Insight(
            insight_id=_new_id("ins"),
            type=InsightType.CORRELATION,
            severity=severity,
            status=InsightStatus.DETECTED,
            category=cat,
            title=f"Correlation between '{best_pair[0]}' and '{best_pair[1]}'",
            description=(
                f"Events '{best_pair[0]}' and '{best_pair[1]}' co-occur in "
                f"{best_count} out of {total_sessions} sessions "
                f"(strength={correlation_strength:.2f})."
            ),
            evidence=[
                f"Co-occurrence rate: {correlation_strength:.4f}",
                f"Sessions analyzed: {total_sessions}",
                f"Pair: {best_pair[0]} <-> {best_pair[1]}",
            ],
            affected_players=affected,
            confidence=round(confidence, 4),
            impact_score=round(correlation_strength, 4),
        )
        self._insights[insight.insight_id] = insight
        _evict_fifo_dict(self._insights, self._config.max_insights)
        self._total_insights_detected += 1
        self._emit(AnalyticsEventKind.INSIGHT_DETECTED, {
            "insight_id": insight.insight_id,
            "type": InsightType.CORRELATION.value,
            "category": cat.value,
        })
        return (True, f"Correlation insight detected: {insight.insight_id}", insight)

    def _detect_pattern_insight(
        self, cat: EventCategory, events: List[GameEvent],
    ) -> Tuple[bool, str, Optional[Insight]]:
        """Detect a pattern insight by finding recurring event sequences."""
        if len(events) < 6:
            return (True, "Insufficient events for pattern analysis", None)

        # Group by player and extract event name sequences
        player_sequences: Dict[str, List[str]] = {}
        for e in events:
            if e.player_id not in player_sequences:
                player_sequences[e.player_id] = []
            player_sequences[e.player_id].append(e.event_name)

        # Find recurring bigrams
        bigram_counts: Dict[Tuple[str, str], int] = {}
        bigram_players: Dict[Tuple[str, str], set] = {}
        for pid, names in player_sequences.items():
            seen = set()
            for i in range(len(names) - 1):
                bigram = (names[i], names[i + 1])
                bigram_counts[bigram] = bigram_counts.get(bigram, 0) + 1
                seen.add(bigram)
            for bg in seen:
                if bg not in bigram_players:
                    bigram_players[bg] = set()
                bigram_players[bg].add(pid)

        if not bigram_counts:
            return (True, "No event sequences found", None)

        best_bigram = max(bigram_counts, key=bigram_counts.get)
        best_count = bigram_counts[best_bigram]
        affected_count = len(bigram_players.get(best_bigram, set()))

        if best_count < 2:
            return (True, "No recurring patterns found", None)

        confidence = min(1.0, best_count / 10.0)
        insight = Insight(
            insight_id=_new_id("ins"),
            type=InsightType.PATTERN,
            severity=InsightSeverity.LOW,
            status=InsightStatus.DETECTED,
            category=cat,
            title=f"Recurring pattern: {best_bigram[0]} -> {best_bigram[1]}",
            description=(
                f"The event sequence '{best_bigram[0]}' followed by "
                f"'{best_bigram[1]}' recurs {best_count} times across "
                f"{affected_count} players in the {cat.value} category."
            ),
            evidence=[
                f"Bigram: {best_bigram[0]} -> {best_bigram[1]}",
                f"Occurrences: {best_count}",
                f"Affected players: {affected_count}",
            ],
            affected_players=list(bigram_players.get(best_bigram, set()))[:20],
            confidence=round(confidence, 4),
            impact_score=round(min(1.0, best_count / 20.0), 4),
        )
        self._insights[insight.insight_id] = insight
        _evict_fifo_dict(self._insights, self._config.max_insights)
        self._total_insights_detected += 1
        self._emit(AnalyticsEventKind.PATTERN_FOUND, {
            "insight_id": insight.insight_id,
            "type": InsightType.PATTERN.value,
            "category": cat.value,
            "pattern": f"{best_bigram[0]} -> {best_bigram[1]}",
        })
        return (True, f"Pattern insight detected: {insight.insight_id}", insight)

    def _detect_prediction_insight(
        self, cat: EventCategory, events: List[GameEvent],
    ) -> Tuple[bool, str, Optional[Insight]]:
        """Predict future outcomes based on current trajectory."""
        if len(events) < 5:
            return (True, "Insufficient events for prediction", None)

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        values = [e.value for e in sorted_events]
        slope = _linear_slope(values)
        current_value = values[-1] if values else 0.0
        projected = current_value + slope * len(values)

        if slope > 0:
            prediction = f"Values are projected to increase to ~{projected:.4f}"
            severity = InsightSeverity.MEDIUM
        elif slope < 0:
            prediction = f"Values are projected to decrease to ~{projected:.4f}"
            severity = InsightSeverity.HIGH
        else:
            prediction = "Values are projected to remain stable"
            severity = InsightSeverity.INFO

        affected = list({e.player_id for e in events})[:20]
        confidence = min(1.0, len(events) / 30.0)
        insight = Insight(
            insight_id=_new_id("ins"),
            type=InsightType.PREDICTION,
            severity=severity,
            status=InsightStatus.DETECTED,
            category=cat,
            title=f"Prediction for {cat.value}: {prediction}",
            description=(
                f"Based on {len(events)} events, the {cat.value} metric "
                f"is projected to reach {projected:.4f} if the current "
                f"trajectory (slope={slope:.4f}) continues."
            ),
            evidence=[
                f"Current value: {current_value:.4f}",
                f"Slope: {slope:.4f}",
                f"Projected value: {projected:.4f}",
            ],
            affected_players=affected,
            confidence=round(confidence, 4),
            impact_score=round(min(1.0, abs(slope)), 4),
        )
        self._insights[insight.insight_id] = insight
        _evict_fifo_dict(self._insights, self._config.max_insights)
        self._total_insights_detected += 1
        self._emit(AnalyticsEventKind.INSIGHT_DETECTED, {
            "insight_id": insight.insight_id,
            "type": InsightType.PREDICTION.value,
            "category": cat.value,
        })
        return (True, f"Prediction insight detected: {insight.insight_id}", insight)

    def _detect_summary_insight(
        self, cat: EventCategory, events: List[GameEvent],
    ) -> Tuple[bool, str, Optional[Insight]]:
        """Generate a summary insight for the category."""
        values = [e.value for e in events]
        avg = _mean(values)
        total = sum(values)
        affected = list({e.player_id for e in events})
        unique_sessions = len({e.session_id for e in events})

        insight = Insight(
            insight_id=_new_id("ins"),
            type=InsightType.SUMMARY,
            severity=InsightSeverity.INFO,
            status=InsightStatus.DETECTED,
            category=cat,
            title=f"Summary: {len(events)} {cat.value} events across {len(affected)} players",
            description=(
                f"The {cat.value} category contains {len(events)} events "
                f"from {len(affected)} players across {unique_sessions} sessions. "
                f"Total value: {total:.4f}, Average: {avg:.4f}."
            ),
            evidence=[
                f"Event count: {len(events)}",
                f"Player count: {len(affected)}",
                f"Session count: {unique_sessions}",
                f"Total value: {total:.4f}",
                f"Average value: {avg:.4f}",
            ],
            affected_players=affected[:20],
            confidence=1.0,
            impact_score=0.1,
        )
        self._insights[insight.insight_id] = insight
        _evict_fifo_dict(self._insights, self._config.max_insights)
        self._total_insights_detected += 1
        self._emit(AnalyticsEventKind.INSIGHT_DETECTED, {
            "insight_id": insight.insight_id,
            "type": InsightType.SUMMARY.value,
            "category": cat.value,
        })
        return (True, f"Summary insight detected: {insight.insight_id}", insight)

    def _detect_alert_insight(
        self, cat: EventCategory, events: List[GameEvent],
    ) -> Tuple[bool, str, Optional[Insight]]:
        """Generate an alert insight if threshold breaches are found."""
        metrics = [m for m in self._metrics.values() if m.category == cat]
        if not metrics:
            return (True, "No metrics registered for category", None)

        breached_metrics: List[str] = []
        max_severity = InsightSeverity.INFO
        for metric in metrics:
            ok, _, mv = self.compute_metric(metric.metric_id, "", "all_time")
            if not ok or mv is None:
                continue
            severity = self._severity_from_threshold(
                mv.value, metric.threshold_warning, metric.threshold_critical,
            )
            if severity is not None:
                breached_metrics.append(metric.metric_id)
                if severity.value > max_severity.value:
                    max_severity = severity

        if not breached_metrics:
            return (True, "No threshold breaches detected", None)

        affected = list({e.player_id for e in events})[:20]
        insight = Insight(
            insight_id=_new_id("ins"),
            type=InsightType.ALERT,
            severity=max_severity,
            status=InsightStatus.DETECTED,
            category=cat,
            title=f"Alert: {len(breached_metrics)} metrics breached thresholds in {cat.value}",
            description=(
                f"{len(breached_metrics)} metrics in the {cat.value} category "
                f"have crossed their warning or critical thresholds: "
                f"{', '.join(breached_metrics)}."
            ),
            evidence=[f"Breached metrics: {breached_metrics}"],
            affected_players=affected,
            confidence=0.9,
            impact_score=0.8 if max_severity == InsightSeverity.CRITICAL else 0.5,
        )
        self._insights[insight.insight_id] = insight
        _evict_fifo_dict(self._insights, self._config.max_insights)
        self._total_insights_detected += 1
        self._emit(AnalyticsEventKind.THRESHOLD_BREACHED, {
            "insight_id": insight.insight_id,
            "type": InsightType.ALERT.value,
            "category": cat.value,
            "breached_metrics": breached_metrics,
        })
        return (True, f"Alert insight detected: {insight.insight_id}", insight)

    def _detect_recommendation_insight(
        self, cat: EventCategory, events: List[GameEvent],
    ) -> Tuple[bool, str, Optional[Insight]]:
        """Generate a recommendation insight suggesting next actions."""
        affected = list({e.player_id for e in events})[:20]
        values = [e.value for e in events]
        avg = _mean(values)

        insight = Insight(
            insight_id=_new_id("ins"),
            type=InsightType.RECOMMENDATION,
            severity=InsightSeverity.MEDIUM,
            status=InsightStatus.DETECTED,
            category=cat,
            title=f"Recommendation: Review {cat.value} category performance",
            description=(
                f"The {cat.value} category has {len(events)} events with an "
                f"average value of {avg:.4f}. Consider reviewing the category "
                f"performance and identifying optimization opportunities."
            ),
            evidence=[
                f"Event count: {len(events)}",
                f"Average value: {avg:.4f}",
                f"Player count: {len(affected)}",
            ],
            affected_players=affected,
            confidence=0.7,
            impact_score=0.3,
        )
        self._insights[insight.insight_id] = insight
        _evict_fifo_dict(self._insights, self._config.max_insights)
        self._total_insights_detected += 1
        self._emit(AnalyticsEventKind.RECOMMENDATION_GENERATED, {
            "insight_id": insight.insight_id,
            "type": InsightType.RECOMMENDATION.value,
            "category": cat.value,
        })
        return (True, f"Recommendation insight detected: {insight.insight_id}", insight)

    def analyze_trend(
        self,
        metric_id: str,
        time_window: str = "last_7_days",
    ) -> Tuple[bool, str, Optional[Insight]]:
        """Analyze the trend of a specific metric over a time window."""
        with self._lock:
            metric = self._metrics.get(metric_id)
            if metric is None:
                return (False, f"Metric not found: {metric_id}", None)

            events = self._filter_events(
                category=metric.category.value, time_window=time_window,
            )
            if len(events) < 3:
                return (True, "Insufficient data for trend analysis", None)

            sorted_events = sorted(events, key=lambda e: e.timestamp)
            bucket_count = min(5, len(sorted_events))
            bucket_size = max(1, len(sorted_events) // bucket_count)
            bucket_avgs: List[float] = []
            for i in range(0, len(sorted_events), bucket_size):
                chunk = sorted_events[i:i + bucket_size]
                bucket_avgs.append(_mean([e.value for e in chunk]))

            slope = _linear_slope(bucket_avgs)
            current = bucket_avgs[-1] if bucket_avgs else 0.0
            previous = bucket_avgs[0] if bucket_avgs else 0.0
            if previous == 0:
                previous = 1.0
            change_pct = ((current - previous) / abs(previous)) * 100.0

            if change_pct > 5.0:
                direction = "increasing"
                severity = InsightSeverity.MEDIUM
            elif change_pct < -5.0:
                direction = "decreasing"
                severity = InsightSeverity.HIGH
            else:
                direction = "stable"
                severity = InsightSeverity.INFO

            affected = list({e.player_id for e in events})[:20]
            confidence = min(1.0, len(events) / 50.0)
            insight = Insight(
                insight_id=_new_id("ins"),
                type=InsightType.TREND,
                severity=severity,
                status=InsightStatus.DETECTED,
                category=metric.category,
                title=f"Trend: {metric.name} is {direction} ({change_pct:+.1f}%)",
                description=(
                    f"Metric '{metric.name}' over {time_window} shows a {direction} "
                    f"trend. Change: {change_pct:+.1f}%, slope: {slope:.4f}. "
                    f"Current bucket avg: {current:.4f}, first bucket avg: {previous:.4f}."
                ),
                evidence=[
                    f"Bucket averages: {[round(v, 4) for v in bucket_avgs]}",
                    f"Change percentage: {change_pct:.2f}%",
                    f"Linear slope: {slope:.6f}",
                ],
                affected_players=affected,
                confidence=round(confidence, 4),
                impact_score=round(min(1.0, abs(change_pct) / 100.0), 4),
            )
            self._insights[insight.insight_id] = insight
            _evict_fifo_dict(self._insights, self._config.max_insights)
            self._total_insights_detected += 1
            self._emit(AnalyticsEventKind.INSIGHT_DETECTED, {
                "insight_id": insight.insight_id,
                "type": InsightType.TREND.value,
                "metric_id": metric_id,
                "change_pct": round(change_pct, 4),
            })
            return (True, f"Trend analyzed: {insight.insight_id}", insight)

    def get_insight(self, insight_id: str) -> Optional[Insight]:
        """Return an insight by ID."""
        with self._lock:
            return self._insights.get(insight_id)

    def list_insights(
        self,
        type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Insight]:
        """List insights with optional type, severity, and status filters."""
        with self._lock:
            items = list(self._insights.values())
            if type is not None:
                items = [i for i in items if i.type == type]
            if severity is not None:
                items = [i for i in items if i.severity == severity]
            if status is not None:
                items = [i for i in items if i.status == status]
            return items

    def confirm_insight(self, insight_id: str) -> Tuple[bool, str]:
        """Mark an insight as confirmed."""
        with self._lock:
            insight = self._insights.get(insight_id)
            if insight is None:
                return (False, f"Insight not found: {insight_id}")
            insight.status = InsightStatus.CONFIRMED
            self._emit(AnalyticsEventKind.INSIGHT_DETECTED, {
                "action": "insight_confirmed",
                "insight_id": insight_id,
            })
            return (True, f"Insight confirmed: {insight_id}")

    def dismiss_insight(
        self, insight_id: str, reason: str = "",
    ) -> Tuple[bool, str]:
        """Dismiss an insight with a reason."""
        with self._lock:
            insight = self._insights.get(insight_id)
            if insight is None:
                return (False, f"Insight not found: {insight_id}")
            insight.status = InsightStatus.DISMISSED
            self._emit(AnalyticsEventKind.INSIGHT_DETECTED, {
                "action": "insight_dismissed",
                "insight_id": insight_id,
                "reason": reason,
            })
            return (True, f"Insight dismissed: {insight_id}")

    # ------------------------------------------------------------------
    # Anomaly Detection
    # ------------------------------------------------------------------

    def detect_anomaly(
        self,
        metric_id: str,
        player_id: str = "",
    ) -> Tuple[bool, str, Optional[AnomalyAlert]]:
        """Detect an anomaly for a specific metric and player using z-score."""
        with self._lock:
            metric = self._metrics.get(metric_id)
            if metric is None:
                return (False, f"Metric not found: {metric_id}", None)

            # Compute the per-player values to establish a baseline
            all_players = self._unique_player_ids()
            if not all_players:
                return (True, "No players tracked; cannot detect anomalies", None)

            player_values: List[float] = []
            for pid in all_players:
                events = self._filter_events(
                    category=metric.category.value,
                    player_id=pid,
                    time_window="all_time",
                )
                if events:
                    vals = [e.value for e in events]
                    player_values.append(_compute_aggregation(
                        vals, metric.aggregation.value,
                    ))

            if len(player_values) < 2:
                return (True, "Insufficient baseline data for anomaly detection", None)

            expected = _mean(player_values)
            std = _std_dev(player_values)
            if std == 0:
                return (True, "No variance in baseline; cannot detect anomalies", None)

            # Compute the actual value for the target player
            if player_id:
                events = self._filter_events(
                    category=metric.category.value,
                    player_id=player_id,
                    time_window="all_time",
                )
                if not events:
                    return (True, f"No events for player: {player_id}", None)
                vals = [e.value for e in events]
                actual = _compute_aggregation(vals, metric.aggregation.value)
            else:
                events = self._filter_events(
                    category=metric.category.value,
                    time_window="all_time",
                )
                vals = [e.value for e in events]
                actual = _compute_aggregation(vals, metric.aggregation.value)

            z_score = abs(actual - expected) / std
            z_threshold = self._z_threshold()

            if z_score <= z_threshold:
                return (True, "No anomaly detected (within expected range)", None)

            if expected == 0:
                deviation_pct = 100.0 if actual != 0 else 0.0
            else:
                deviation_pct = ((actual - expected) / abs(expected)) * 100.0

            severity = self._severity_from_deviation(deviation_pct)
            alert = AnomalyAlert(
                alert_id=_new_id("al"),
                metric_id=metric_id,
                expected_value=round(expected, 6),
                actual_value=round(actual, 6),
                deviation_percent=round(deviation_pct, 4),
                severity=severity,
                player_id=player_id,
                timestamp=_now(),
                context={
                    "z_score": round(z_score, 4),
                    "z_threshold": round(z_threshold, 4),
                    "std_dev": round(std, 6),
                    "sample_size": len(player_values),
                    "metric_name": metric.name,
                    "category": metric.category.value,
                },
            )
            self._anomalies[alert.alert_id] = alert
            _evict_fifo_dict(self._anomalies, _MAX_ANOMALIES)
            self._total_anomalies_alerted += 1
            self._emit(AnalyticsEventKind.ANOMALY_ALERTED, {
                "alert_id": alert.alert_id,
                "metric_id": metric_id,
                "player_id": player_id,
                "deviation_percent": deviation_pct,
                "severity": severity.value,
            })
            msg = (
                f"Anomaly detected: {metric_id} for {player_id or 'global'} "
                f"deviated {deviation_pct:.1f}% (z={z_score:.2f})"
            )
            return (True, msg, alert)

    def scan_anomalies(self) -> Tuple[bool, str, List[AnomalyAlert]]:
        """Scan all metrics for anomalies across all players."""
        with self._lock:
            if not self._config.enable_anomaly_detection:
                return (False, "Anomaly detection is disabled", [])

            alerts: List[AnomalyAlert] = []
            for metric_id in list(self._metrics.keys()):
                # Check global anomaly
                ok, _, alert = self.detect_anomaly(metric_id, "")
                if ok and alert is not None:
                    alerts.append(alert)

                # Check per-player anomalies
                for player_id in self._unique_player_ids():
                    ok, _, alert = self.detect_anomaly(metric_id, player_id)
                    if ok and alert is not None:
                        alerts.append(alert)

            return (True, f"Scanned {len(self._metrics)} metrics; "
                    f"{len(alerts)} anomalies found", alerts)

    def get_anomaly(self, alert_id: str) -> Optional[AnomalyAlert]:
        """Return an anomaly alert by ID."""
        with self._lock:
            return self._anomalies.get(alert_id)

    def list_anomalies(
        self,
        severity: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[AnomalyAlert]:
        """List anomaly alerts with optional severity and status filters."""
        with self._lock:
            items = list(self._anomalies.values())
            if severity is not None:
                items = [a for a in items if a.severity == severity]
            if status is not None:
                items = [a for a in items if a.status == status]
            return items

    def resolve_anomaly(
        self, alert_id: str, resolution: str = "",
    ) -> Tuple[bool, str]:
        """Resolve an anomaly alert with a resolution note."""
        with self._lock:
            alert = self._anomalies.get(alert_id)
            if alert is None:
                return (False, f"Anomaly not found: {alert_id}")
            alert.status = "resolved"
            alert.context["resolution"] = resolution
            alert.context["resolved_at"] = _now()
            self._emit(AnalyticsEventKind.ANOMALY_ALERTED, {
                "action": "anomaly_resolved",
                "alert_id": alert_id,
                "resolution": resolution,
            })
            return (True, f"Anomaly resolved: {alert_id}")

    # ------------------------------------------------------------------
    # Pattern Matching
    # ------------------------------------------------------------------

    def find_pattern(
        self,
        category: str,
        min_occurrences: int = 2,
    ) -> Tuple[bool, str, Optional[PatternMatch]]:
        """Find the most common recurring event sequence in a category."""
        with self._lock:
            cat = _coerce_enum(EventCategory, category)
            if cat is None:
                return (False, f"Invalid category: {category}", None)

            events = self._filter_events(category=cat.value, time_window="all_time")
            if len(events) < min_occurrences * 2:
                return (True, "Insufficient events for pattern detection", None)

            # Group by player and extract event name sequences
            player_sequences: Dict[str, List[str]] = {}
            for e in events:
                if e.player_id not in player_sequences:
                    player_sequences[e.player_id] = []
                player_sequences[e.player_id].append(e.event_name)

            # Find recurring bigrams
            bigram_data: Dict[Tuple[str, str], Dict[str, Any]] = {}
            for pid, names in player_sequences.items():
                for i in range(len(names) - 1):
                    bigram = (names[i], names[i + 1])
                    if bigram not in bigram_data:
                        bigram_data[bigram] = {
                            "count": 0, "players": set(),
                            "first_seen": float("inf"), "last_seen": 0.0,
                        }
                    bigram_data[bigram]["count"] += 1
                    bigram_data[bigram]["players"].add(pid)

            # Add timestamps
            for e in events:
                for i in range(len(player_sequences.get(e.player_id, [])) - 1):
                    pass  # Timestamps tracked below

            if not bigram_data:
                return (True, "No event sequences found", None)

            # Find the most common bigram meeting the threshold
            best_bigram = None
            best_count = 0
            for bigram, data in bigram_data.items():
                if data["count"] >= min_occurrences and data["count"] > best_count:
                    best_bigram = bigram
                    best_count = data["count"]

            if best_bigram is None:
                return (True, "No patterns meeting minimum occurrence threshold", None)

            data = bigram_data[best_bigram]
            affected_count = len(data["players"])
            confidence = min(1.0, best_count / 20.0)

            # Find first and last seen timestamps
            first_ts = min(e.timestamp for e in events)
            last_ts = max(e.timestamp for e in events)

            pattern = PatternMatch(
                pattern_id=_new_id("pat"),
                name=f"{best_bigram[0]} -> {best_bigram[1]}",
                description=(
                    f"Recurring event sequence '{best_bigram[0]}' followed by "
                    f"'{best_bigram[1]}' in the {cat.value} category, observed "
                    f"{best_count} times across {affected_count} players."
                ),
                category=cat,
                occurrences=best_count,
                first_seen=first_ts,
                last_seen=last_ts,
                confidence=round(confidence, 4),
                affected_count=affected_count,
                properties={
                    "sequence": [best_bigram[0], best_bigram[1]],
                    "min_occurrences": min_occurrences,
                },
            )
            self._patterns[pattern.pattern_id] = pattern
            _evict_fifo_dict(self._patterns, _MAX_PATTERNS)
            self._total_patterns_found += 1
            self._emit(AnalyticsEventKind.PATTERN_FOUND, {
                "pattern_id": pattern.pattern_id,
                "category": cat.value,
                "sequence": pattern.name,
                "occurrences": best_count,
            })
            return (True, f"Pattern found: {pattern.pattern_id}", pattern)

    def discover_patterns(self) -> Tuple[bool, str, List[PatternMatch]]:
        """Discover patterns across all event categories."""
        with self._lock:
            if not self._config.enable_pattern_matching:
                return (False, "Pattern matching is disabled", [])

            patterns: List[PatternMatch] = []
            for cat in EventCategory:
                if cat == EventCategory.CUSTOM:
                    continue
                ok, _, pattern = self.find_pattern(cat.value, min_occurrences=2)
                if ok and pattern is not None:
                    patterns.append(pattern)
            return (True, f"Discovered {len(patterns)} patterns", patterns)

    def get_pattern(self, pattern_id: str) -> Optional[PatternMatch]:
        """Return a pattern match by ID."""
        with self._lock:
            return self._patterns.get(pattern_id)

    def list_patterns(
        self, category: Optional[str] = None,
    ) -> List[PatternMatch]:
        """List pattern matches, optionally filtered by category."""
        with self._lock:
            items = list(self._patterns.values())
            if category is not None:
                items = [p for p in items if p.category == category]
            return items

    # ------------------------------------------------------------------
    # Player Journey Tracking
    # ------------------------------------------------------------------

    def track_player_journey(
        self, player_id: str,
    ) -> Tuple[bool, str, Optional[PlayerJourney]]:
        """Create or update a player journey based on their events."""
        with self._lock:
            if not player_id:
                return (False, "player_id is required", None)

            events = self._events_for_player(player_id)
            if not events and player_id not in self._journeys:
                return (True, "No events found for player", None)

            new_stage = self._determine_stage(player_id)
            existing = self._journeys.get(player_id)

            if existing is None:
                # Create a new journey
                if events:
                    sessions = set(e.session_id for e in events)
                    total_playtime = sum(
                        e.value for e in events
                        if e.category == EventCategory.GAMEPLAY
                    )
                    key_moments = [
                        f"{e.event_name} at tick {e.tick}"
                        for e in events
                        if e.category in (
                            EventCategory.PROGRESSION,
                            EventCategory.COMBAT,
                        )
                    ][:10]
                    last_active = max(e.timestamp for e in events)
                else:
                    sessions = set()
                    total_playtime = 0.0
                    key_moments = []
                    last_active = _now()

                journey = PlayerJourney(
                    player_id=player_id,
                    current_stage=JourneyStage(new_stage),
                    stage_transitions=[{
                        "from": "none",
                        "to": new_stage,
                        "trigger": "initial_tracking",
                        "timestamp": _now(),
                    }],
                    total_sessions=len(sessions),
                    total_playtime=total_playtime,
                    key_moments=key_moments,
                    last_active=last_active,
                )
                self._journeys[player_id] = journey
                _evict_fifo_dict(self._journeys, _MAX_JOURNEYS)

                # Compute churn risk and engagement
                ok_risk, _, churn = self.assess_churn_risk(player_id)
                if ok_risk:
                    journey.churn_risk = churn
                ok_eng, _, eng = self.compute_engagement(player_id)
                if ok_eng:
                    journey.engagement_score = eng

                self._emit(AnalyticsEventKind.JOURNEY_UPDATED, {
                    "player_id": player_id,
                    "stage": new_stage,
                    "action": "journey_created",
                })
                return (True, f"Journey created for {player_id}", journey)
            else:
                # Update existing journey
                old_stage = existing.current_stage.value
                if events:
                    sessions = set(e.session_id for e in events)
                    existing.total_sessions = len(sessions)
                    existing.total_playtime = sum(
                        e.value for e in events
                        if e.category == EventCategory.GAMEPLAY
                    )
                    existing.last_active = max(e.timestamp for e in events)
                    existing.key_moments = [
                        f"{e.event_name} at tick {e.tick}"
                        for e in events
                        if e.category in (
                            EventCategory.PROGRESSION,
                            EventCategory.COMBAT,
                        )
                    ][:10]

                if new_stage != old_stage:
                    existing.stage_transitions.append({
                        "from": old_stage,
                        "to": new_stage,
                        "trigger": "auto_detection",
                        "timestamp": _now(),
                    })
                    existing.current_stage = JourneyStage(new_stage)

                # Recompute churn risk and engagement
                ok_risk, _, churn = self.assess_churn_risk(player_id)
                if ok_risk:
                    existing.churn_risk = churn
                ok_eng, _, eng = self.compute_engagement(player_id)
                if ok_eng:
                    existing.engagement_score = eng

                self._emit(AnalyticsEventKind.JOURNEY_UPDATED, {
                    "player_id": player_id,
                    "stage": new_stage,
                    "action": "journey_updated",
                })
                return (True, f"Journey updated for {player_id}", existing)

    def update_journey_stage(
        self,
        player_id: str,
        new_stage: str,
        trigger: str = "manual",
    ) -> Tuple[bool, str]:
        """Manually update a player's journey stage."""
        with self._lock:
            journey = self._journeys.get(player_id)
            if journey is None:
                return (False, f"Journey not found for player: {player_id}")

            stage = _coerce_enum(JourneyStage, new_stage)
            if stage is None:
                return (False, f"Invalid stage: {new_stage}")

            old_stage = journey.current_stage.value
            journey.stage_transitions.append({
                "from": old_stage,
                "to": stage.value,
                "trigger": trigger,
                "timestamp": _now(),
            })
            journey.current_stage = stage
            self._emit(AnalyticsEventKind.JOURNEY_UPDATED, {
                "player_id": player_id,
                "old_stage": old_stage,
                "new_stage": stage.value,
                "trigger": trigger,
            })
            return (True, f"Stage updated to {stage.value} for {player_id}")

    def get_journey(self, player_id: str) -> Optional[PlayerJourney]:
        """Return a player journey by player ID."""
        with self._lock:
            return self._journeys.get(player_id)

    def list_journeys(
        self, stage: Optional[str] = None,
    ) -> List[PlayerJourney]:
        """List player journeys, optionally filtered by stage."""
        with self._lock:
            items = list(self._journeys.values())
            if stage is not None:
                items = [j for j in items if j.current_stage == stage]
            return items

    def assess_churn_risk(self, player_id: str) -> Tuple[bool, str, float]:
        """Assess churn risk for a player based on recency, frequency, duration."""
        with self._lock:
            events = self._events_for_player(player_id)
            if not events:
                return (True, "No events; churn risk is maximum", 1.0)

            latest_event = max(events, key=lambda e: e.timestamp)
            days_since_last = (_now() - latest_event.timestamp) / 86400.0
            recency_factor = min(1.0, days_since_last / 14.0)

            # Frequency: sessions in the last 7 days
            cutoff_7d = _now() - 604800.0
            recent_events = [e for e in events if e.timestamp >= cutoff_7d]
            recent_sessions = set(e.session_id for e in recent_events)
            sessions_per_week = len(recent_sessions)
            frequency_factor = 1.0 - min(1.0, sessions_per_week / 7.0)

            # Duration: average session length proxy from gameplay event values
            gameplay_events = [e for e in events
                               if e.category == EventCategory.GAMEPLAY]
            if gameplay_events:
                avg_duration = _mean([e.value for e in gameplay_events])
                duration_factor = 1.0 - min(1.0, avg_duration / 60.0)
            else:
                duration_factor = 0.5

            churn_risk = (
                0.40 * recency_factor
                + 0.35 * frequency_factor
                + 0.25 * duration_factor
            )
            churn_risk = max(0.0, min(1.0, churn_risk))

            # Update journey if it exists
            journey = self._journeys.get(player_id)
            if journey is not None:
                journey.churn_risk = round(churn_risk, 4)

            return (True, f"Churn risk: {churn_risk:.4f}", round(churn_risk, 4))

    def compute_engagement(self, player_id: str) -> Tuple[bool, str, float]:
        """Compute engagement score from frequency, playtime, social, progression."""
        with self._lock:
            events = self._events_for_player(player_id)
            if not events:
                return (True, "No events; engagement is zero", 0.0)

            # Session frequency: sessions per week normalized to 0-1
            cutoff_7d = _now() - 604800.0
            recent_events = [e for e in events if e.timestamp >= cutoff_7d]
            recent_sessions = set(e.session_id for e in recent_events)
            session_frequency = min(1.0, len(recent_sessions) / 7.0)

            # Playtime score: total playtime normalized
            gameplay_events = [e for e in events
                               if e.category == EventCategory.GAMEPLAY]
            total_playtime = sum(e.value for e in gameplay_events)
            playtime_score = min(1.0, total_playtime / 600.0)

            # Social score: social interactions normalized
            social_events = [e for e in events
                             if e.category == EventCategory.SOCIAL]
            social_score = min(1.0, len(social_events) / 50.0)

            # Progression score: progression events normalized
            progression_events = [e for e in events
                                  if e.category == EventCategory.PROGRESSION]
            progression_score = min(1.0, len(progression_events) / 30.0)

            engagement = (
                0.30 * session_frequency
                + 0.30 * playtime_score
                + 0.20 * social_score
                + 0.20 * progression_score
            )
            engagement = max(0.0, min(1.0, engagement))

            # Update journey if it exists
            journey = self._journeys.get(player_id)
            if journey is not None:
                journey.engagement_score = round(engagement, 4)

            return (True, f"Engagement: {engagement:.4f}", round(engagement, 4))

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    def generate_recommendation(
        self,
        insight_id: str,
        title: str,
        description: str,
        priority: str = "medium",
        action_type: str = "investigate",
        expected_impact: float = 0.0,
        target_segment: str = "all",
        steps: Optional[List[str]] = None,
    ) -> Tuple[bool, str, Optional[Recommendation]]:
        """Generate a recommendation tied to a specific insight."""
        with self._lock:
            if not title or not description:
                return (False, "title and description are required", None)

            insight = self._insights.get(insight_id)
            if insight is None:
                return (False, f"Insight not found: {insight_id}", None)

            rec = Recommendation(
                recommendation_id=_new_id("rec"),
                insight_id=insight_id,
                title=title,
                description=description,
                priority=priority,
                action_type=action_type,
                expected_impact=float(expected_impact),
                target_segment=target_segment,
                steps=steps or [],
            )
            self._recommendations[rec.recommendation_id] = rec
            _evict_fifo_dict(self._recommendations, self._config.max_recommendations)

            if rec.recommendation_id not in insight.recommendations:
                insight.recommendations.append(rec.recommendation_id)

            self._total_recommendations_generated += 1
            self._emit(AnalyticsEventKind.RECOMMENDATION_GENERATED, {
                "recommendation_id": rec.recommendation_id,
                "insight_id": insight_id,
                "priority": priority,
                "action_type": action_type,
            })
            return (True, f"Recommendation generated: {rec.recommendation_id}", rec)

    def auto_generate_recommendations(self) -> Tuple[bool, str, int]:
        """Auto-generate recommendations from all active insights."""
        with self._lock:
            active_insights = [
                i for i in self._insights.values()
                if i.status in (
                    InsightStatus.DETECTED.value,
                    InsightStatus.CONFIRMED.value,
                )
            ]
            count = 0
            for insight in active_insights:
                templates = _RECOMMENDATION_TEMPLATES.get(insight.type.value, [])
                for action_type, title, desc, priority, impact in templates:
                    ok, _, _ = self.generate_recommendation(
                        insight_id=insight.insight_id,
                        title=title,
                        description=desc,
                        priority=priority,
                        action_type=action_type,
                        expected_impact=impact,
                        target_segment=",".join(insight.affected_players[:5]) or "all",
                        steps=[
                            f"Review insight: {insight.title}",
                            f"Analyze evidence: {'; '.join(insight.evidence[:2])}",
                            "Implement the recommended action",
                            "Monitor the affected metrics for improvement",
                        ],
                    )
                    if ok:
                        count += 1
            return (True, f"Auto-generated {count} recommendations", count)

    def get_recommendation(
        self, recommendation_id: str,
    ) -> Optional[Recommendation]:
        """Return a recommendation by ID."""
        with self._lock:
            return self._recommendations.get(recommendation_id)

    def list_recommendations(
        self, priority: Optional[str] = None,
    ) -> List[Recommendation]:
        """List recommendations, optionally filtered by priority."""
        with self._lock:
            items = list(self._recommendations.values())
            if priority is not None:
                items = [r for r in items if r.priority == priority]
            return items

    def apply_recommendation(
        self, recommendation_id: str,
    ) -> Tuple[bool, str]:
        """Mark a recommendation as applied and update its insight."""
        with self._lock:
            rec = self._recommendations.get(recommendation_id)
            if rec is None:
                return (False, f"Recommendation not found: {recommendation_id}")
            rec.status = "applied"

            insight = self._insights.get(rec.insight_id)
            if insight is not None:
                insight.status = InsightStatus.ACTED_UPON

            self._emit(AnalyticsEventKind.RECOMMENDATION_GENERATED, {
                "action": "recommendation_applied",
                "recommendation_id": recommendation_id,
                "insight_id": rec.insight_id,
            })
            return (True, f"Recommendation applied: {recommendation_id}")

    def dismiss_recommendation(
        self, recommendation_id: str, reason: str = "",
    ) -> Tuple[bool, str]:
        """Dismiss a recommendation with a reason."""
        with self._lock:
            rec = self._recommendations.get(recommendation_id)
            if rec is None:
                return (False, f"Recommendation not found: {recommendation_id}")
            rec.status = "dismissed"
            rec.target_segment = f"{rec.target_segment} (dismissed: {reason})"

            self._emit(AnalyticsEventKind.RECOMMENDATION_GENERATED, {
                "action": "recommendation_dismissed",
                "recommendation_id": recommendation_id,
                "reason": reason,
            })
            return (True, f"Recommendation dismissed: {recommendation_id}")

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def compile_report(
        self,
        title: str,
        time_window: str = "last_24_hours",
    ) -> Tuple[bool, str, Optional[AnalyticsReport]]:
        """Compile an analytics report for a time window."""
        with self._lock:
            if not title:
                return (False, "title is required", None)

            # Compute key metrics
            ok, _, metric_values = self.compute_all_metrics(time_window)
            key_metrics: Dict[str, float] = {}
            if ok:
                for mv in metric_values:
                    key_metrics[mv.metric_id] = mv.value

            # Get top insights by impact score
            insights = sorted(
                self._insights.values(),
                key=lambda i: i.impact_score,
                reverse=True,
            )
            top_insight_ids = [i.insight_id for i in insights[:10]]

            # Get top recommendations by priority
            recs = sorted(
                self._recommendations.values(),
                key=lambda r: _PRIORITY_ORDER.get(r.priority, 0),
                reverse=True,
            )
            top_rec_ids = [r.recommendation_id for r in recs[:10]]

            # Generate summary
            stats = self.get_stats()
            summary_parts = [
                f"Analytics report for {time_window}.",
                f"Total events ingested: {stats.total_events_ingested}.",
                f"Players tracked: {stats.players_tracked}.",
                f"Active alerts: {stats.active_alerts}.",
                f"Insights detected: {stats.total_insights_detected}.",
                f"Average insight confidence: {stats.average_insight_confidence:.2f}.",
            ]
            if insights:
                summary_parts.append(f"Top insight: {insights[0].title}.")
            if recs:
                summary_parts.append(f"Top recommendation: {recs[0].title}.")

            report = AnalyticsReport(
                report_id=_new_id("rep"),
                title=title,
                time_window=time_window,
                summary=" ".join(summary_parts),
                key_metrics=key_metrics,
                top_insights=top_insight_ids,
                top_recommendations=top_rec_ids,
                generated_at=_now(),
            )
            self._reports[report.report_id] = report
            _evict_fifo_dict(self._reports, _MAX_REPORTS)
            self._total_reports_compiled += 1
            self._emit(AnalyticsEventKind.REPORT_COMPILED, {
                "report_id": report.report_id,
                "title": title,
                "time_window": time_window,
            })
            return (True, f"Report compiled: {report.report_id}", report)

    def get_report(self, report_id: str) -> Optional[AnalyticsReport]:
        """Return an analytics report by ID."""
        with self._lock:
            return self._reports.get(report_id)

    def list_reports(self) -> List[AnalyticsReport]:
        """List all compiled analytics reports."""
        with self._lock:
            return list(self._reports.values())

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------

    def get_player_summary(
        self, player_id: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Return a comprehensive summary for a specific player."""
        with self._lock:
            events = self._events_for_player(player_id)
            if not events and player_id not in self._journeys:
                return (False, f"No data found for player: {player_id}", {})

            journey = self._journeys.get(player_id)
            insights = [
                i for i in self._insights.values()
                if player_id in i.affected_players
            ]
            anomalies = [
                a for a in self._anomalies.values()
                if a.player_id == player_id
            ]
            recs = [
                r for r in self._recommendations.values()
                if player_id in r.target_segment
            ]

            categories = {}
            for e in events:
                cat = e.category.value
                if cat not in categories:
                    categories[cat] = 0
                categories[cat] += 1

            ok_risk, _, churn = self.assess_churn_risk(player_id)
            ok_eng, _, eng = self.compute_engagement(player_id)

            summary = {
                "player_id": player_id,
                "journey": journey.to_dict() if journey else None,
                "event_count": len(events),
                "category_breakdown": categories,
                "insight_count": len(insights),
                "insights": [i.to_dict() for i in insights[:10]],
                "anomaly_count": len(anomalies),
                "anomalies": [a.to_dict() for a in anomalies[:10]],
                "recommendation_count": len(recs),
                "recommendations": [r.to_dict() for r in recs[:10]],
                "churn_risk": churn,
                "engagement_score": eng,
                "last_active": max(e.timestamp for e in events) if events else 0,
            }
            return (True, f"Summary for {player_id}", summary)

    def get_segment_summary(
        self, segment_criteria: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Return aggregate stats for players matching segment criteria."""
        with self._lock:
            if not segment_criteria:
                return (False, "No segment criteria provided", {})

            matching_players: List[str] = []
            for player_id in self._unique_player_ids():
                journey = self._journeys.get(player_id)
                matches = True

                stage = segment_criteria.get("stage")
                if stage is not None:
                    if journey is None or journey.current_stage != stage:
                        matches = False

                min_engagement = segment_criteria.get("min_engagement")
                if min_engagement is not None and matches:
                    eng = journey.engagement_score if journey else 0.0
                    if eng < float(min_engagement):
                        matches = False

                max_churn = segment_criteria.get("max_churn_risk")
                if max_churn is not None and matches:
                    risk = journey.churn_risk if journey else 1.0
                    if risk > float(max_churn):
                        matches = False

                if matches:
                    matching_players.append(player_id)

            total_events = sum(
                len(self._events_by_player.get(pid, []))
                for pid in matching_players
            )
            active_anomalies = sum(
                1 for a in self._anomalies.values()
                if a.status == "active"
                and a.player_id in matching_players
            )

            eng_values: List[float] = []
            risk_values: List[float] = []
            for pid in matching_players:
                journey = self._journeys.get(pid)
                if journey:
                    eng_values.append(journey.engagement_score)
                    risk_values.append(journey.churn_risk)

            summary = {
                "criteria": segment_criteria,
                "player_count": len(matching_players),
                "matching_players": matching_players[:50],
                "total_events": total_events,
                "active_anomalies": active_anomalies,
                "avg_engagement": round(_mean(eng_values), 4) if eng_values else 0.0,
                "avg_churn_risk": round(_mean(risk_values), 4) if risk_values else 0.0,
            }
            return (True, f"Segment summary: {len(matching_players)} players", summary)

    # ------------------------------------------------------------------
    # Observability and Lifecycle
    # ------------------------------------------------------------------

    def get_stats(self) -> AnalyticsStats:
        """Return aggregate statistics for the synthesizer."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> AnalyticsSnapshot:
        """Return a point-in-time snapshot of synthesizer state."""
        with self._lock:
            self._refresh_stats()
            return AnalyticsSnapshot(
                tick_count=self._tick_count,
                events_buffered=len(self._events_store),
                insights_active=sum(
                    1 for i in self._insights.values()
                    if i.status in (
                        InsightStatus.DETECTED.value,
                        InsightStatus.ANALYZING.value,
                        InsightStatus.CONFIRMED.value,
                    )
                ),
                anomalies_active=sum(
                    1 for a in self._anomalies.values()
                    if a.status == "active"
                ),
                journeys_tracked=len(self._journeys),
                patterns_active=len(self._patterns),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the synthesizer."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "seeded": self._seeded,
                "tick_count": self._tick_count,
                "metrics": len(self._metrics),
                "events": len(self._events_store),
                "insights": len(self._insights),
                "anomalies": len(self._anomalies),
                "journeys": len(self._journeys),
                "patterns": len(self._patterns),
                "recommendations": len(self._recommendations),
                "reports": len(self._reports),
                "events_log": len(self._events_log),
                "metric_values": len(self._metric_values),
            }

    def get_config(self) -> AnalyticsConfig:
        """Return the current configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, AnalyticsConfig]:
        """Update configuration fields. Returns the updated config."""
        with self._lock:
            valid_fields = {
                "max_events_retained", "max_insights",
                "enable_anomaly_detection", "enable_pattern_matching",
                "enable_journey_tracking", "anomaly_sensitivity",
                "insight_confidence_threshold", "max_recommendations",
                "report_generation_interval",
            }
            updated: List[str] = []
            for key, value in kwargs.items():
                if key in valid_fields:
                    setattr(self._config, key, value)
                    updated.append(key)
                else:
                    return (False, f"Unknown config field: {key}", self._config)
            return (True, f"Updated config: {', '.join(updated)}", self._config)

    def list_events_log(
        self,
        kind: Optional[str] = None,
        limit: int = 100,
    ) -> List[AnalyticsEvent]:
        """List audit events from the synthesizer log."""
        with self._lock:
            items = list(self._events_log)
            if kind is not None:
                items = [e for e in items if e.kind == kind]
            return items[-limit:]

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the synthesizer by one tick.

        Processes the event buffer, computes metrics, scans for anomalies,
        updates player journeys, auto-generates recommendations periodically,
        and expires data that exceeds configured capacity limits.
        """
        dt_seconds = max(0.0, _safe_float(dt, 1.0))
        with self._lock:
            self._tick_count += 1

            # Process event buffer: compute all metrics
            ok, _, metric_values = self.compute_all_metrics("last_24_hours")
            metrics_computed = len(metric_values) if ok else 0

            # Detect anomalies
            anomalies_detected = 0
            if self._config.enable_anomaly_detection:
                ok, _, alerts = self.scan_anomalies()
                if ok:
                    anomalies_detected = len(alerts)

            # Update player journeys
            journeys_updated = 0
            if self._config.enable_journey_tracking:
                for player_id in list(self._journeys.keys()):
                    ok, _, _ = self.track_player_journey(player_id)
                    if ok:
                        journeys_updated += 1

            # Auto-generate recommendations at the configured interval
            insights_generated = 0
            if (self._config.report_generation_interval > 0
                    and self._tick_count % self._config.report_generation_interval == 0):
                ok, _, count = self.auto_generate_recommendations()
                if ok:
                    insights_generated = count

            # Expire old data
            data_expired = self._expire_old_data()

            self._refresh_stats()

            self._emit(AnalyticsEventKind.METRIC_COMPUTED, {
                "action": "tick",
                "tick": self._tick_count,
                "dt": dt_seconds,
                "metrics_computed": metrics_computed,
                "anomalies_detected": anomalies_detected,
                "journeys_updated": journeys_updated,
                "insights_generated": insights_generated,
                "data_expired": data_expired,
            })

            return {
                "status": "ok",
                "tick": self._tick_count,
                "dt": dt_seconds,
                "metrics_computed": metrics_computed,
                "anomalies_detected": anomalies_detected,
                "journeys_updated": journeys_updated,
                "insights_generated": insights_generated,
                "data_expired": data_expired,
                "events_buffered": len(self._events_store),
                "insights_active": sum(
                    1 for i in self._insights.values()
                    if i.status in (
                        InsightStatus.DETECTED.value,
                        InsightStatus.ANALYZING.value,
                        InsightStatus.CONFIRMED.value,
                    )
                ),
                "anomalies_active": sum(
                    1 for a in self._anomalies.values()
                    if a.status == "active"
                ),
            }

    def reset(self) -> Tuple[bool, str]:
        """Clear all state and re-seed the synthesizer.

        Wipes every registry, resets cumulative counters and bookkeeping
        fields, then reloads the canonical seed data so the synthesizer
        returns to a known-good state. Useful for tests and for restoring
        a clean slate without restarting the host process.
        """
        with self._lock:
            self._metrics.clear()
            self._events_store.clear()
            self._events_by_player.clear()
            self._metric_values.clear()
            self._insights.clear()
            self._anomalies.clear()
            self._journeys.clear()
            self._patterns.clear()
            self._recommendations.clear()
            self._reports.clear()
            self._events_log.clear()

            self._config = AnalyticsConfig()
            self._stats = AnalyticsStats()
            self._tick_count = 0

            # Reset cumulative counters so totals reflect only the new seed.
            self._total_events_ingested = 0
            self._total_insights_detected = 0
            self._total_anomalies_alerted = 0
            self._total_recommendations_generated = 0
            self._total_reports_compiled = 0
            self._total_patterns_found = 0

            self._seeded = False
            self._initialized = False
            self._seed_data()
            self._seeded = True
            self._initialized = True

            self._emit(AnalyticsEventKind.REPORT_COMPILED, {
                "action": "reset",
                "description": "Analytics synthesizer reset and re-seeded.",
            })
            return (True, "Analytics synthesizer reset and re-seeded.")

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the synthesizer with a canonical set of analytics data."""
        now = _now()

        # --- 8 Metric Definitions covering different categories ---
        seed_metrics = [
            ("met_session_count", "Session Count", EventCategory.GAMEPLAY,
             MetricAggregation.COUNT, "Total gameplay sessions per player.",
             "count(session_id)", "sessions", 0.0, 0.0),
            ("met_social_interactions", "Social Interactions", EventCategory.SOCIAL,
             MetricAggregation.SUM, "Total social interaction events.",
             "sum(value where category=social)", "events", 50.0, 100.0),
            ("met_revenue_total", "Total Revenue", EventCategory.ECONOMIC,
             MetricAggregation.SUM, "Total revenue from economic events.",
             "sum(value where category=economic)", "usd", 100.0, 500.0),
            ("met_combat_wins", "Combat Wins", EventCategory.COMBAT,
             MetricAggregation.COUNT, "Total combat victory events.",
             "count(event_name=combat_win)", "wins", 20.0, 50.0),
            ("met_areas_discovered", "Areas Discovered", EventCategory.EXPLORATION,
             MetricAggregation.COUNT, "Total unique areas discovered.",
             "count(event_name=area_discovered)", "areas", 10.0, 25.0),
            ("met_levels_completed", "Levels Completed", EventCategory.PROGRESSION,
             MetricAggregation.COUNT, "Total levels completed by a player.",
             "count(event_name=level_complete)", "levels", 15.0, 30.0),
            ("met_retention_d7", "D7 Retention", EventCategory.RETENTION,
             MetricAggregation.AVG, "Average 7-day retention rate.",
             "avg(active_day_7 / install_day)", "percentage", 0.15, 0.10),
            ("met_arpu", "ARPU", EventCategory.MONETIZATION,
             MetricAggregation.AVG, "Average revenue per user.",
             "avg(revenue_per_player)", "usd", 0.30, 0.50),
        ]
        for metric_id, name, cat, agg, desc, formula, unit, warn, crit in seed_metrics:
            self._metrics[metric_id] = MetricDefinition(
                metric_id=metric_id,
                name=name,
                category=cat,
                aggregation=agg,
                description=desc,
                formula=formula,
                unit=unit,
                threshold_warning=warn,
                threshold_critical=crit,
            )

        # --- 20 Game Events from 5 players ---
        seed_players = ["player_001", "player_002", "player_003",
                        "player_004", "player_005"]
        seed_sessions = ["sess_a001", "sess_a002", "sess_b001", "sess_b002",
                         "sess_c001", "sess_c002", "sess_d001", "sess_d002",
                         "sess_e001", "sess_e002"]

        event_templates = [
            ("player_001", "sess_a001", EventCategory.GAMEPLAY, "session_start", 1.0),
            ("player_001", "sess_a001", EventCategory.PROGRESSION, "level_complete", 5.0),
            ("player_001", "sess_a001", EventCategory.COMBAT, "combat_win", 1.0),
            ("player_001", "sess_a002", EventCategory.EXPLORATION, "area_discovered", 1.0),
            ("player_002", "sess_b001", EventCategory.GAMEPLAY, "session_start", 1.0),
            ("player_002", "sess_b001", EventCategory.SOCIAL, "friend_added", 1.0),
            ("player_002", "sess_b001", EventCategory.ECONOMIC, "purchase_made", 4.99),
            ("player_002", "sess_b002", EventCategory.PROGRESSION, "level_complete", 8.0),
            ("player_003", "sess_c001", EventCategory.GAMEPLAY, "session_start", 1.0),
            ("player_003", "sess_c001", EventCategory.COMBAT, "combat_win", 1.0),
            ("player_003", "sess_c001", EventCategory.COMBAT, "combat_loss", 1.0),
            ("player_003", "sess_c002", EventCategory.MONETIZATION, "iap_purchase", 9.99),
            ("player_004", "sess_d001", EventCategory.GAMEPLAY, "session_start", 1.0),
            ("player_004", "sess_d001", EventCategory.EXPLORATION, "area_discovered", 1.0),
            ("player_004", "sess_d001", EventCategory.PROGRESSION, "level_complete", 3.0),
            ("player_004", "sess_d002", EventCategory.SOCIAL, "guild_joined", 1.0),
            ("player_005", "sess_e001", EventCategory.GAMEPLAY, "session_start", 1.0),
            ("player_005", "sess_e001", EventCategory.ECONOMIC, "purchase_made", 2.99),
            ("player_005", "sess_e001", EventCategory.RETENTION, "day_7_active", 1.0),
            ("player_005", "sess_e002", EventCategory.COMBAT, "combat_win", 1.0),
        ]

        for idx, (pid, sid, cat, name, val) in enumerate(event_templates):
            event_id = f"ge_seed_{idx + 1:04d}"
            # Spread events across the last 10 days
            ts = now - (idx * 36000.0)
            event = GameEvent(
                event_id=event_id,
                player_id=pid,
                session_id=sid,
                category=cat,
                event_name=name,
                value=val,
                properties={"seed": True, "index": idx},
                timestamp=ts,
                tick=0,
            )
            self._events_store[event_id] = event
            if pid not in self._events_by_player:
                self._events_by_player[pid] = []
            self._events_by_player[pid].append(event_id)

        self._total_events_ingested = len(event_templates)

        # --- 5 Insights with different types and severities ---
        seed_insights = [
            ("ins_seed_001", InsightType.TREND, InsightSeverity.MEDIUM,
             InsightStatus.CONFIRMED, EventCategory.GAMEPLAY,
             "Gameplay sessions trending upward",
             "Over the last 7 days, gameplay session counts show an upward trend of +12.5%.",
             ["Slope: 0.045", "Change: +12.5%", "Samples: 20"],
             ["player_001", "player_002"], 0.85, 0.6),
            ("ins_seed_002", InsightType.ANOMALY, InsightSeverity.HIGH,
             InsightStatus.DETECTED, EventCategory.ECONOMIC,
             "Anomalous revenue spike detected",
             "Revenue for player_002 deviates 150% from the mean, suggesting a whale purchase.",
             ["Z-score: 2.85", "Expected: 4.99", "Actual: 14.98"],
             ["player_002"], 0.92, 0.8),
            ("ins_seed_003", InsightType.CORRELATION, InsightSeverity.LOW,
             InsightStatus.DETECTED, EventCategory.COMBAT,
             "Correlation between combat_wins and level_complete",
             "Players who win combat are more likely to complete levels in the same session.",
             ["Co-occurrence: 0.72", "Sessions: 8"],
             ["player_001", "player_003"], 0.65, 0.4),
            ("ins_seed_004", InsightType.PATTERN, InsightSeverity.INFO,
             InsightStatus.DETECTED, EventCategory.PROGRESSION,
             "Recurring pattern: session_start -> level_complete",
             "The sequence session_start followed by level_complete recurs across 4 players.",
             ["Occurrences: 5", "Players: 4"],
             ["player_001", "player_002", "player_004"], 0.70, 0.3),
            ("ins_seed_005", InsightType.PREDICTION, InsightSeverity.MEDIUM,
             InsightStatus.CONFIRMED, EventCategory.RETENTION,
             "D7 retention projected to decline",
             "Based on current trajectory, D7 retention is projected to drop to 0.14 within 2 weeks.",
             ["Current: 0.18", "Slope: -0.003", "Projected: 0.14"],
             ["player_005"], 0.78, 0.5),
        ]
        for (iid, itype, isev, istat, icat, title, desc, evidence,
             affected, conf, impact) in seed_insights:
            self._insights[iid] = Insight(
                insight_id=iid,
                type=itype,
                severity=isev,
                status=istat,
                category=icat,
                title=title,
                description=desc,
                evidence=evidence,
                affected_players=affected,
                confidence=conf,
                detected_at=now - 3600.0,
                recommendations=[],
                impact_score=impact,
            )
        self._total_insights_detected = len(seed_insights)

        # --- 3 Anomaly Alerts ---
        seed_anomalies = [
            ("al_seed_001", "met_revenue_total", 4.99, 14.98, 200.0,
             InsightSeverity.HIGH, "player_002"),
            ("al_seed_002", "met_combat_wins", 0.5, 2.0, 300.0,
             InsightSeverity.CRITICAL, "player_001"),
            ("al_seed_003", "met_arpu", 0.35, 0.85, 142.0,
             InsightSeverity.MEDIUM, "player_005"),
        ]
        for (aid, mid, expected, actual, dev, sev, pid) in seed_anomalies:
            self._anomalies[aid] = AnomalyAlert(
                alert_id=aid,
                metric_id=mid,
                expected_value=expected,
                actual_value=actual,
                deviation_percent=dev,
                severity=sev,
                player_id=pid,
                timestamp=now - 1800.0,
                context={
                    "z_score": round(abs(actual - expected) / max(0.01, expected), 4),
                    "metric_name": self._metrics.get(mid, MetricDefinition(
                        mid, mid, EventCategory.CUSTOM, MetricAggregation.COUNT
                    )).name,
                    "seed": True,
                },
                status="active",
            )
        self._total_anomalies_alerted = len(seed_anomalies)

        # --- 5 Player Journeys at different stages ---
        seed_journeys = [
            ("player_001", JourneyStage.MID_GAME, 2, 120.0, 0.15, 0.75, now - 3600.0),
            ("player_002", JourneyStage.LATE_GAME, 2, 340.0, 0.08, 0.82, now - 7200.0),
            ("player_003", JourneyStage.EARLY_GAME, 2, 45.0, 0.45, 0.50, now - 10800.0),
            ("player_004", JourneyStage.ENDGAME, 2, 580.0, 0.05, 0.90, now - 14400.0),
            ("player_005", JourneyStage.CHURNED, 2, 90.0, 0.85, 0.30, now - 86400.0 * 8),
        ]
        for (pid, stage, sessions, playtime, churn, eng, last_active) in seed_journeys:
            self._journeys[pid] = PlayerJourney(
                player_id=pid,
                current_stage=stage,
                stage_transitions=[{
                    "from": "onboarding",
                    "to": stage.value,
                    "trigger": "seed_data",
                    "timestamp": last_active,
                }],
                total_sessions=sessions,
                total_playtime=playtime,
                key_moments=[
                    "First level complete",
                    "First combat win",
                    "First area discovered",
                ],
                churn_risk=churn,
                engagement_score=eng,
                last_active=last_active,
            )

        # --- 4 Pattern Matches ---
        seed_patterns = [
            ("pat_seed_001", "session_start -> level_complete",
             "Players commonly complete a level right after starting a session.",
             EventCategory.GAMEPLAY, 5, now - 86400.0 * 3, now - 3600.0, 0.80, 4),
            ("pat_seed_002", "combat_win -> level_complete",
             "Winning combat frequently precedes level completion.",
             EventCategory.COMBAT, 3, now - 86400.0 * 2, now - 7200.0, 0.70, 3),
            ("pat_seed_003", "area_discovered -> combat_win",
             "Discovering a new area often leads to a combat encounter.",
             EventCategory.EXPLORATION, 2, now - 86400.0 * 4, now - 14400.0, 0.60, 2),
            ("pat_seed_004", "purchase_made -> level_complete",
             "Players who make a purchase tend to complete a level shortly after.",
             EventCategory.ECONOMIC, 2, now - 86400.0 * 2, now - 10800.0, 0.65, 2),
        ]
        for (pat_id, name, desc, cat, occ, first, last, conf, affected) in seed_patterns:
            self._patterns[pat_id] = PatternMatch(
                pattern_id=pat_id,
                name=name,
                description=desc,
                category=cat,
                occurrences=occ,
                first_seen=first,
                last_seen=last,
                confidence=conf,
                affected_count=affected,
                properties={"seed": True},
            )
        self._total_patterns_found = len(seed_patterns)

        # --- 5 Recommendations ---
        seed_recs = [
            ("rec_seed_001", "ins_seed_001", "Adjust Content Pacing",
             "The upward gameplay trend suggests players are ready for new content. "
             "Consider accelerating the content release schedule.",
             "medium", "tune_pacing", 0.4, "player_001,player_002",
             ["Review the trend data", "Plan next content release", "Monitor engagement"]),
            ("rec_seed_002", "ins_seed_002", "Investigate Revenue Anomaly",
             "The revenue spike for player_002 may indicate a whale. Investigate "
             "whether this is a one-time purchase or a new spending pattern.",
             "high", "investigate", 0.7, "player_002",
             ["Pull player_002 purchase history", "Check for promotions", "Alert live-ops"]),
            ("rec_seed_003", "ins_seed_003", "Cross-System Tuning",
             "The combat-level correlation suggests jointly tuning combat difficulty "
             "and level progression for a smoother experience.",
             "medium", "balance_difficulty", 0.5, "player_001,player_003",
             ["Analyze combat-win-to-level ratios", "Tune difficulty curve", "A/B test changes"]),
            ("rec_seed_004", "ins_seed_005", "Proactive Retention Intervention",
             "D7 retention is projected to decline. Launch a targeted re-engagement "
             "campaign for at-risk players before the drop occurs.",
             "high", "proactive_intervention", 0.6, "player_005",
             ["Identify at-risk cohort", "Design re-engagement offer", "Deploy campaign"]),
            ("rec_seed_005", "ins_seed_004", "Optimize Content Flow",
             "The session_start -> level_complete pattern indicates players want "
             "quick wins early in a session. Optimize the content flow accordingly.",
             "low", "content_optimization", 0.3, "all",
             ["Review level placement", "Ensure early-session wins", "Monitor completion rates"]),
        ]
        for (rid, iid, title, desc, priority, action, impact, segment, steps) in seed_recs:
            self._recommendations[rid] = Recommendation(
                recommendation_id=rid,
                insight_id=iid,
                title=title,
                description=desc,
                priority=priority,
                action_type=action,
                expected_impact=impact,
                target_segment=segment,
                steps=steps,
                created_at=now - 1800.0,
                status="pending",
            )
            insight = self._insights.get(iid)
            if insight is not None and rid not in insight.recommendations:
                insight.recommendations.append(rid)
        self._total_recommendations_generated = len(seed_recs)

        # --- 2 Analytics Reports ---
        self._reports["rep_seed_001"] = AnalyticsReport(
            report_id="rep_seed_001",
            title="Weekly Analytics Summary",
            time_window=TimeWindow.LAST_7_DAYS.value,
            summary=(
                "Weekly analytics summary: 20 events ingested across 5 players. "
                "3 active anomalies detected. 5 insights identified with average "
                "confidence of 0.78. Top insight: Anomalous revenue spike detected."
            ),
            key_metrics={
                "met_session_count": 10.0,
                "met_revenue_total": 17.97,
                "met_combat_wins": 3.0,
                "met_levels_completed": 3.0,
                "met_arpu": 3.59,
            },
            top_insights=["ins_seed_002", "ins_seed_001", "ins_seed_005"],
            top_recommendations=["rec_seed_002", "rec_seed_004", "rec_seed_001"],
            generated_at=now - 3600.0,
        )
        self._reports["rep_seed_002"] = AnalyticsReport(
            report_id="rep_seed_002",
            title="Daily Engagement Report",
            time_window=TimeWindow.LAST_24_HOURS.value,
            summary=(
                "Daily engagement report: 5 active players in the last 24 hours. "
                "Average engagement score: 0.65. Average churn risk: 0.32. "
                "1 player at high churn risk. Top recommendation: Proactive "
                "Retention Intervention."
            ),
            key_metrics={
                "met_session_count": 5.0,
                "met_social_interactions": 2.0,
                "met_areas_discovered": 2.0,
            },
            top_insights=["ins_seed_005", "ins_seed_001"],
            top_recommendations=["rec_seed_004", "rec_seed_001"],
            generated_at=now - 7200.0,
        )
        self._total_reports_compiled = 2

        # Refresh stats after seeding
        self._refresh_stats()

        # Emit seed event
        self._emit(AnalyticsEventKind.REPORT_COMPILED, {
            "action": "seed_data_loaded",
            "metrics": len(self._metrics),
            "events": len(self._events_store),
            "insights": len(self._insights),
            "anomalies": len(self._anomalies),
            "journeys": len(self._journeys),
            "patterns": len(self._patterns),
            "recommendations": len(self._recommendations),
            "reports": len(self._reports),
        })


# ---------------------------------------------------------------------------
# Module-Level Factory Function
# ---------------------------------------------------------------------------


def get_analytics_synthesizer() -> AnalyticsSynthesizer:
    """Return the singleton AnalyticsSynthesizer, initializing seed data on first use."""
    inst = AnalyticsSynthesizer.get_instance()
    if not getattr(inst, "_seeded", False):
        inst.initialize()
    return inst
