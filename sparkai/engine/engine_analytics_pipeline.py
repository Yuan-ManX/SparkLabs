"""
SparkLabs Engine - Analytics Pipeline

An AI-driven analytics pipeline for the AI-native game engine that
collects, processes, analyzes, and visualizes game telemetry data to
provide actionable insights. The pipeline supports real-time metric
tracking, statistical anomaly detection, trend forecasting, player
and session summaries, and a live dashboard of key performance indicators.

Architecture:
  AnalyticsPipelineEngine (singleton)
    |-- TelemetryEvent (atomic unit of telemetry data)
    |-- AnalyticsQuery (parameterized metric aggregation request)
    |-- AnalyticsReport (generated report with insights and recommendations)
    |-- PerformanceAlert (threshold-based alert with severity)
    |-- MetricType (20 gameplay and performance metric categories)
    |-- AggregationType (8 aggregation strategies for metric queries)
    |-- SeverityLevel (4 alert severity tiers)

Core Capabilities:
  - track_event: Record a single telemetry event with context
  - track_batch: Ingest a batch of events in a single atomic operation
  - query_metrics: Run parameterized aggregation queries across time ranges
  - generate_report: Auto-generate analytic reports with insights and recommendations
  - set_alert / check_alerts: Configure and evaluate threshold-based alerts
  - get_realtime_dashboard: Snapshot of all current key metrics
  - get_player_summary / get_session_summary: Per-player and per-session breakdowns
  - detect_anomalies: Statistical outlier detection using z-score and IQR methods
  - predict_trends: Simple linear regression forecasting from historical data
"""

from __future__ import annotations

import json
import math
import random
import statistics
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class MetricType(Enum):
    """Gameplay and performance metric categories tracked by the pipeline."""
    FPS = "fps"
    MEMORY = "memory"
    DRAW_CALLS = "draw_calls"
    ENTITY_COUNT = "entity_count"
    PLAYER_DEATHS = "player_deaths"
    PLAYER_ACTIONS = "player_actions"
    SESSION_DURATION = "session_duration"
    LEVEL_COMPLETION = "level_completion"
    ITEM_COLLECTED = "item_collected"
    ENEMY_KILLED = "enemy_killed"
    BOSS_DEFEATED = "boss_defeated"
    CURRENCY_EARNED = "currency_earned"
    CURRENCY_SPENT = "currency_spent"
    QUEST_COMPLETED = "quest_completed"
    UPGRADE_PURCHASED = "upgrade_purchased"
    ABILITY_USED = "ability_used"
    DAMAGE_DEALT = "damage_dealt"
    DAMAGE_TAKEN = "damage_taken"
    HEALING_DONE = "healing_done"
    REVIVES_USED = "revives_used"


class AggregationType(Enum):
    """Aggregation strategies for metric queries."""
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    PERCENTILE = "percentile"
    RATE = "rate"
    DISTRIBUTION = "distribution"


class SeverityLevel(Enum):
    """Alert severity tiers for threshold-based monitoring."""
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class TelemetryEvent:
    """A single atomic unit of telemetry data captured from the game engine."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metric_type: MetricType = MetricType.FPS
    value: float = 0.0
    player_id: str = ""
    session_id: str = ""
    timestamp: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "player_id": self.player_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class AnalyticsQuery:
    """A parameterized request for metric aggregation over a time range."""
    query_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metric_type: MetricType = MetricType.FPS
    aggregation: AggregationType = AggregationType.AVERAGE
    time_range_start: float = 0.0
    time_range_end: float = 0.0
    group_by: Optional[str] = None
    filter_conditions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "metric_type": self.metric_type.value,
            "aggregation": self.aggregation.value,
            "time_range_start": self.time_range_start,
            "time_range_end": self.time_range_end,
            "group_by": self.group_by,
            "filter_conditions": self.filter_conditions,
        }


@dataclass
class AnalyticsReport:
    """A generated report containing metric analysis, insights, and recommendations."""
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    queries: List[AnalyticsQuery] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=_time_module.time)
    data_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "title": self.title,
            "query_count": len(self.queries),
            "queries": [q.to_dict() for q in self.queries],
            "insights": self.insights,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at,
            "data_summary": self.data_summary,
        }


@dataclass
class PerformanceAlert:
    """A threshold-based alert triggered when a metric exceeds its configured limit."""
    alert_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metric_type: MetricType = MetricType.FPS
    current_value: float = 0.0
    threshold: float = 0.0
    severity: SeverityLevel = SeverityLevel.INFO
    message: str = ""
    triggered_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "metric_type": self.metric_type.value,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "message": self.message,
            "triggered_at": self.triggered_at,
        }


# ---------------------------------------------------------------------------
# AnalyticsPipelineEngine — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class AnalyticsPipelineEngine:
    """
    AI-driven analytics pipeline for collecting, processing, analyzing,
    and visualizing game telemetry data.

    The pipeline ingests TelemetryEvent records, supports parameterized
    aggregation queries, generates analytical reports with auto-detected
    insights, performs statistical anomaly detection and trend forecasting,
    and provides a real-time dashboard of all key metrics.

    Thread-safe via a reentrant lock. Use get_analytics_pipeline() or
    AnalyticsPipelineEngine.get_instance() to obtain the singleton.

    Usage:
        pipeline = get_analytics_pipeline()
        pipeline.track_event(MetricType.FPS, 60.0, "player_1", "session_abc")
        dashboard = pipeline.get_realtime_dashboard()
        anomalies = pipeline.detect_anomalies(MetricType.FPS, 0, time.time())
    """

    _instance: Optional["AnalyticsPipelineEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_EVENTS = 10000
    MAX_ALERT_HISTORY = 500
    ANOMALY_ZSCORE_THRESHOLD = 2.5
    ANOMALY_IQR_MULTIPLIER = 1.5
    FORECAST_MIN_DATA_POINTS = 5
    PERCENTILE_DEFAULT = 95.0

    def __new__(cls) -> "AnalyticsPipelineEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._events: deque = deque(maxlen=self.MAX_EVENTS)
        self._events_by_player: Dict[str, List[TelemetryEvent]] = defaultdict(list)
        self._events_by_session: Dict[str, List[TelemetryEvent]] = defaultdict(list)
        self._events_by_metric: Dict[MetricType, List[TelemetryEvent]] = defaultdict(list)

        self._alerts_config: Dict[MetricType, List[Dict[str, Any]]] = defaultdict(list)
        self._triggered_alerts: deque = deque(maxlen=self.MAX_ALERT_HISTORY)

        self._total_events: int = 0
        self._total_batches: int = 0
        self._total_reports: int = 0
        self._total_alerts_triggered: int = 0
        self._total_queries_run: int = 0

    @classmethod
    def get_instance(cls) -> "AnalyticsPipelineEngine":
        return cls()

    # ------------------------------------------------------------------
    # Event Tracking
    # ------------------------------------------------------------------

    def track_event(
        self,
        metric_type: MetricType,
        value: float,
        player_id: str = "",
        session_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TelemetryEvent:
        """Record a single telemetry event and index it for efficient querying."""
        event = TelemetryEvent(
            metric_type=metric_type,
            value=value,
            player_id=player_id,
            session_id=session_id,
            metadata=metadata or {},
        )

        with self._lock:
            self._events.append(event)
            self._total_events += 1

            if player_id:
                self._events_by_player[player_id].append(event)
                if len(self._events_by_player[player_id]) > self.MAX_EVENTS:
                    self._events_by_player[player_id] = self._events_by_player[player_id][-self.MAX_EVENTS // 2:]

            if session_id:
                self._events_by_session[session_id].append(event)
                if len(self._events_by_session[session_id]) > self.MAX_EVENTS:
                    self._events_by_session[session_id] = self._events_by_session[session_id][-self.MAX_EVENTS // 2:]

            self._events_by_metric[metric_type].append(event)
            if len(self._events_by_metric[metric_type]) > self.MAX_EVENTS:
                self._events_by_metric[metric_type] = self._events_by_metric[metric_type][-self.MAX_EVENTS // 2:]

        return event

    def track_batch(self, events: List[TelemetryEvent]) -> List[TelemetryEvent]:
        """Ingest a batch of telemetry events in a single atomic operation."""
        with self._lock:
            for event in events:
                self._events.append(event)
                self._total_events += 1

                if event.player_id:
                    self._events_by_player[event.player_id].append(event)
                if event.session_id:
                    self._events_by_session[event.session_id].append(event)
                self._events_by_metric[event.metric_type].append(event)

            self._total_batches += 1

        return events

    # ------------------------------------------------------------------
    # Metric Querying
    # ------------------------------------------------------------------

    def query_metrics(
        self,
        metric_type: MetricType,
        aggregation: AggregationType = AggregationType.AVERAGE,
        time_range_start: float = 0.0,
        time_range_end: float = 0.0,
        group_by: Optional[str] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a parameterized aggregation query over telemetry events.

        Filters events by metric_type and time range, then applies the
        specified aggregation. Supports grouping by player_id, session_id,
        or any metadata key. Additional filter_conditions narrow the
        event set by matching metadata fields.

        Args:
            metric_type: The metric category to query.
            aggregation: The aggregation strategy to apply.
            time_range_start: Start of the time window (0 = no lower bound).
            time_range_end: End of the time window (0 = no upper bound).
            group_by: Optional grouping key (player_id, session_id, or metadata key).
            filter_conditions: Key-value pairs to match against event metadata.

        Returns:
            A dict with the query results including aggregated values,
            group breakdowns, and query metadata.
        """
        if time_range_end == 0.0:
            time_range_end = _time_module.time()

        matched = self._filter_events(
            metric_type=metric_type,
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            filter_conditions=filter_conditions or {},
        )

        self._total_queries_run += 1

        if group_by:
            return self._compute_grouped_aggregation(
                matched, aggregation, group_by, metric_type,
                time_range_start, time_range_end, filter_conditions or {},
            )

        result = self._apply_aggregation(matched, aggregation)
        return {
            "query_id": uuid.uuid4().hex,
            "metric_type": metric_type.value,
            "aggregation": aggregation.value,
            "time_range_start": time_range_start,
            "time_range_end": time_range_end,
            "event_count": len(matched),
            "result": result,
            "group_by": None,
        }

    def _filter_events(
        self,
        metric_type: MetricType,
        time_range_start: float,
        time_range_end: float,
        filter_conditions: Dict[str, Any],
    ) -> List[TelemetryEvent]:
        """Filter events by metric type, time range, and metadata conditions."""
        with self._lock:
            candidates = list(self._events_by_metric.get(metric_type, []))
            if not candidates:
                candidates = [
                    e for e in self._events if e.metric_type == metric_type
                ]

        filtered: List[TelemetryEvent] = []
        for event in candidates:
            if time_range_start > 0 and event.timestamp < time_range_start:
                continue
            if time_range_end > 0 and event.timestamp > time_range_end:
                continue
            if filter_conditions:
                match = True
                for key, expected in filter_conditions.items():
                    if event.metadata.get(key) != expected:
                        match = False
                        break
                if not match:
                    continue
            filtered.append(event)

        return filtered

    def _compute_grouped_aggregation(
        self,
        events: List[TelemetryEvent],
        aggregation: AggregationType,
        group_by: str,
        metric_type: MetricType,
        time_range_start: float,
        time_range_end: float,
        filter_conditions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Group events by the specified key and compute aggregation per group."""
        groups: Dict[str, List[TelemetryEvent]] = defaultdict(list)

        for event in events:
            if group_by == "player_id":
                key = event.player_id or "unknown"
            elif group_by == "session_id":
                key = event.session_id or "unknown"
            else:
                key = str(event.metadata.get(group_by, "unknown"))
            groups[key].append(event)

        group_results: Dict[str, Any] = {}
        for key, group_events in groups.items():
            group_results[key] = {
                "result": self._apply_aggregation(group_events, aggregation),
                "event_count": len(group_events),
            }

        return {
            "query_id": uuid.uuid4().hex,
            "metric_type": metric_type.value,
            "aggregation": aggregation.value,
            "time_range_start": time_range_start,
            "time_range_end": time_range_end,
            "event_count": len(events),
            "group_by": group_by,
            "group_count": len(groups),
            "groups": group_results,
        }

    def _apply_aggregation(
        self,
        events: List[TelemetryEvent],
        aggregation: AggregationType,
    ) -> Any:
        """Apply the specified aggregation function to a list of events."""
        if not events:
            return None

        values = [e.value for e in events]

        if aggregation == AggregationType.SUM:
            return sum(values)
        elif aggregation == AggregationType.AVERAGE:
            return round(sum(values) / len(values), 4)
        elif aggregation == AggregationType.MIN:
            return min(values)
        elif aggregation == AggregationType.MAX:
            return max(values)
        elif aggregation == AggregationType.COUNT:
            return len(values)
        elif aggregation == AggregationType.PERCENTILE:
            return self._compute_percentile(sorted(values), self.PERCENTILE_DEFAULT)
        elif aggregation == AggregationType.RATE:
            if len(events) < 2:
                return 0.0
            time_span = events[-1].timestamp - events[0].timestamp
            if time_span <= 0:
                return 0.0
            return round(len(events) / time_span, 4)
        elif aggregation == AggregationType.DISTRIBUTION:
            return self._compute_distribution(values)
        else:
            return round(sum(values) / len(values), 4)

    @staticmethod
    def _compute_percentile(sorted_values: List[float], percentile: float) -> float:
        """Compute the given percentile from a sorted list of values."""
        if not sorted_values:
            return 0.0
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        lower = int(math.floor(index))
        upper = int(math.ceil(index))
        if lower == upper:
            return sorted_values[lower]
        weight = index - lower
        return round(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight, 4)

    @staticmethod
    def _compute_distribution(values: List[float]) -> Dict[str, Any]:
        """Compute the statistical distribution of a list of values."""
        if not values:
            return {}
        sorted_vals = sorted(values)
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": round(statistics.mean(values), 4) if len(values) >= 1 else 0.0,
            "median": round(statistics.median(values), 4) if len(values) >= 1 else 0.0,
            "stdev": round(statistics.stdev(values), 4) if len(values) >= 2 else 0.0,
            "p25": AnalyticsPipelineEngine._compute_percentile(sorted_vals, 25.0),
            "p50": AnalyticsPipelineEngine._compute_percentile(sorted_vals, 50.0),
            "p75": AnalyticsPipelineEngine._compute_percentile(sorted_vals, 75.0),
            "p95": AnalyticsPipelineEngine._compute_percentile(sorted_vals, 95.0),
        }

    # ------------------------------------------------------------------
    # Report Generation
    # ------------------------------------------------------------------

    def generate_report(
        self,
        title: str,
        metric_types: List[MetricType],
        time_range_start: float = 0.0,
        time_range_end: float = 0.0,
    ) -> AnalyticsReport:
        """Generate an analytical report with auto-detected insights and recommendations.

        For each requested metric type, the report runs multiple aggregation
        queries (average, sum, distribution, rate) and analyzes the results
        to produce human-readable insights and actionable recommendations.

        Args:
            title: A descriptive title for the report.
            metric_types: List of metric types to include in the report.
            time_range_start: Start of the analysis window.
            time_range_end: End of the analysis window.

        Returns:
            An AnalyticsReport with queries, insights, and recommendations.
        """
        if time_range_end == 0.0:
            time_range_end = _time_module.time()

        queries: List[AnalyticsQuery] = []
        all_aggregations = [
            AggregationType.AVERAGE,
            AggregationType.SUM,
            AggregationType.DISTRIBUTION,
            AggregationType.RATE,
        ]

        for mt in metric_types:
            for agg in all_aggregations:
                query = AnalyticsQuery(
                    metric_type=mt,
                    aggregation=agg,
                    time_range_start=time_range_start,
                    time_range_end=time_range_end,
                )
                queries.append(query)

        insights: List[str] = []
        recommendations: List[str] = []
        data_summary: Dict[str, Any] = {}

        for mt in metric_types:
            events = self._filter_events(mt, time_range_start, time_range_end, {})
            if not events:
                insights.append(f"No events recorded for {mt.value} in the specified time range.")
                data_summary[mt.value] = {"event_count": 0, "average": None}
                continue

            avg_val = self._apply_aggregation(events, AggregationType.AVERAGE)
            total_val = self._apply_aggregation(events, AggregationType.SUM)
            rate_val = self._apply_aggregation(events, AggregationType.RATE)
            dist = self._apply_aggregation(events, AggregationType.DISTRIBUTION)

            data_summary[mt.value] = {
                "event_count": len(events),
                "average": avg_val,
                "total": total_val,
                "rate": rate_val,
                "distribution": dist,
            }

            # Generate insights from the data
            self._generate_metric_insights(
                mt, events, avg_val, rate_val, dist, insights, recommendations,
            )

        # Sort insights for consistent output
        insights.sort()

        report = AnalyticsReport(
            title=title,
            queries=queries,
            insights=insights,
            recommendations=recommendations,
            data_summary=data_summary,
        )

        self._total_reports += 1
        return report

    def _generate_metric_insights(
        self,
        metric_type: MetricType,
        events: List[TelemetryEvent],
        avg_val: Any,
        rate_val: Any,
        dist: Any,
        insights: List[str],
        recommendations: List[str],
    ) -> None:
        """Generate human-readable insights and recommendations for a metric."""
        mt_name = metric_type.value

        if isinstance(avg_val, (int, float)) and dist and isinstance(dist, dict):
            stdev = dist.get("stdev", 0)
            if stdev > 0 and avg_val > 0:
                cv = stdev / abs(avg_val)
                if cv > 1.0:
                    insights.append(
                        f"High variability in {mt_name} (CV={cv:.2f}); "
                        f"values range from {dist.get('min')} to {dist.get('max')}."
                    )
                elif cv < 0.1:
                    insights.append(
                        f"{mt_name} is highly stable (CV={cv:.2f}) with "
                        f"minimal fluctuation around {avg_val}."
                    )

        if isinstance(rate_val, (int, float)) and rate_val > 0:
            insights.append(
                f"{mt_name} event rate: {rate_val:.2f} events per second "
                f"({len(events)} total events)."
            )

        # Metric-specific recommendations
        if metric_type == MetricType.FPS and isinstance(avg_val, (int, float)):
            if avg_val < 30:
                recommendations.append(
                    f"FPS average ({avg_val:.1f}) is below 30; consider reducing "
                    f"draw calls, enabling LOD, or optimizing shaders."
                )
            elif avg_val < 60:
                recommendations.append(
                    f"FPS average ({avg_val:.1f}) is below 60; monitor for dips "
                    f"during heavy scenes."
                )

        if metric_type == MetricType.MEMORY and isinstance(avg_val, (int, float)):
            if avg_val > 1024 * 1024 * 1024:
                recommendations.append(
                    f"Memory usage is high ({avg_val / (1024**3):.2f} GB avg); "
                    f"consider asset streaming or texture compression."
                )

        if metric_type == MetricType.PLAYER_DEATHS and isinstance(rate_val, (int, float)):
            if rate_val > 0.05:
                recommendations.append(
                    f"Player death rate is high ({rate_val:.3f}/s); review difficulty "
                    f"balance and check for unfair encounter designs."
                )

        if metric_type == MetricType.DRAW_CALLS and isinstance(avg_val, (int, float)):
            if avg_val > 500:
                recommendations.append(
                    f"Draw calls average ({avg_val:.0f}) exceeds 500; consider "
                    f"batching, instancing, or atlasing to reduce GPU overhead."
                )

    # ------------------------------------------------------------------
    # Alert Management
    # ------------------------------------------------------------------

    def set_alert(
        self,
        metric_type: MetricType,
        threshold: float,
        severity: SeverityLevel = SeverityLevel.WARNING,
    ) -> PerformanceAlert:
        """Configure a threshold-based alert for a metric type.

        When the metric's latest value exceeds the threshold, the alert
        will be triggered during the next check_alerts() call.

        Args:
            metric_type: The metric to monitor.
            threshold: The value above which the alert triggers.
            severity: The severity level assigned to the alert.

        Returns:
            A PerformanceAlert representing the alert configuration.
        """
        config_entry = {
            "threshold": threshold,
            "severity": severity,
            "configured_at": _time_module.time(),
        }

        with self._lock:
            self._alerts_config[metric_type].append(config_entry)

        return PerformanceAlert(
            metric_type=metric_type,
            current_value=0.0,
            threshold=threshold,
            severity=severity,
            message=f"Alert configured for {metric_type.value}: threshold={threshold}, severity={severity.value}",
        )

    def check_alerts(self) -> List[PerformanceAlert]:
        """Evaluate all configured alerts against the latest metric values.

        For each alert configuration, the most recent event value for the
        metric is compared against the threshold. Alerts that exceed their
        threshold are recorded and returned.

        Returns:
            A list of PerformanceAlert instances that were triggered.
        """
        triggered: List[PerformanceAlert] = []

        with self._lock:
            for metric_type, configs in self._alerts_config.items():
                latest = self._get_latest_event_for_metric(metric_type)
                if latest is None:
                    continue

                for config in configs:
                    threshold = config["threshold"]
                    if latest.value > threshold:
                        severity = config["severity"]
                        message = (
                            f"{metric_type.value} is {latest.value:.2f} which exceeds "
                            f"the threshold of {threshold:.2f}"
                        )
                        alert = PerformanceAlert(
                            metric_type=metric_type,
                            current_value=latest.value,
                            threshold=threshold,
                            severity=severity,
                            message=message,
                        )
                        self._triggered_alerts.append(alert)
                        self._total_alerts_triggered += 1
                        triggered.append(alert)

        return triggered

    def _get_latest_event_for_metric(self, metric_type: MetricType) -> Optional[TelemetryEvent]:
        """Get the most recent event for a given metric type."""
        events = self._events_by_metric.get(metric_type, [])
        if events:
            return events[-1]
        return None

    # ------------------------------------------------------------------
    # Real-Time Dashboard
    # ------------------------------------------------------------------

    def get_realtime_dashboard(self) -> Dict[str, Any]:
        """Return a real-time snapshot of all key metrics and system status.

        The dashboard includes the latest value for each metric type,
        active alert status, recent event counts, session and player
        statistics, and a health summary.

        Returns:
            A dict with the complete dashboard snapshot.
        """
        with self._lock:
            metrics_snapshot: Dict[str, Any] = {}
            for mt in MetricType:
                latest = self._get_latest_event_for_metric(mt)
                metrics_snapshot[mt.value] = {
                    "latest_value": latest.value if latest else None,
                    "latest_timestamp": latest.timestamp if latest else None,
                    "total_events": len(self._events_by_metric.get(mt, [])),
                }

            # Recent events summary (last 60 seconds)
            now = _time_module.time()
            recent_cutoff = now - 60.0
            recent_events = [e for e in self._events if e.timestamp >= recent_cutoff]

            active_alerts = [
                a for a in self._triggered_alerts
                if a.triggered_at >= recent_cutoff
            ]

            alert_status: Dict[str, Any] = {
                "active_alerts": len(active_alerts),
                "total_alerts_configured": sum(len(c) for c in self._alerts_config.values()),
                "total_alerts_triggered": self._total_alerts_triggered,
                "recent_alerts": [
                    {"metric": a.metric_type.value, "severity": a.severity.value, "value": a.current_value}
                    for a in list(self._triggered_alerts)[-10:]
                ],
            }

            player_stats: Dict[str, Any] = {
                "unique_players": len(self._events_by_player),
                "active_sessions": len(self._events_by_session),
            }

            return {
                "timestamp": now,
                "metrics": metrics_snapshot,
                "alert_status": alert_status,
                "player_stats": player_stats,
                "recent_events_per_second": round(len(recent_events) / 60.0, 2),
                "total_events_ingested": self._total_events,
                "total_reports_generated": self._total_reports,
                "system_health": self._compute_health_summary(),
            }

    def _compute_health_summary(self) -> Dict[str, str]:
        """Compute a simple health summary based on key metrics."""
        health = {}

        fps_events = self._events_by_metric.get(MetricType.FPS, [])
        if fps_events:
            latest_fps = fps_events[-1].value
            if latest_fps >= 60:
                health["fps"] = "good"
            elif latest_fps >= 30:
                health["fps"] = "fair"
            else:
                health["fps"] = "poor"
        else:
            health["fps"] = "unknown"

        memory_events = self._events_by_metric.get(MetricType.MEMORY, [])
        if memory_events:
            latest_mem = memory_events[-1].value
            gb = latest_mem / (1024 ** 3)
            if gb < 2:
                health["memory"] = "good"
            elif gb < 4:
                health["memory"] = "fair"
            else:
                health["memory"] = "high"
        else:
            health["memory"] = "unknown"

        alert_count = len(self._triggered_alerts)
        if alert_count == 0:
            health["alerts"] = "clear"
        elif alert_count < 5:
            health["alerts"] = "minor"
        else:
            health["alerts"] = "attention_needed"

        return health

    # ------------------------------------------------------------------
    # Player and Session Summaries
    # ------------------------------------------------------------------

    def get_player_summary(self, player_id: str) -> Dict[str, Any]:
        """Return a summary of all telemetry data for a specific player.

        Includes per-metric breakdowns with average, total, and count,
        session history, and overall engagement metrics.

        Args:
            player_id: The unique identifier of the player.

        Returns:
            A dict with the player's telemetry summary.
        """
        with self._lock:
            events = list(self._events_by_player.get(player_id, []))
            if not events:
                events = [e for e in self._events if e.player_id == player_id]

        if not events:
            return {"player_id": player_id, "event_count": 0, "found": False}

        metric_breakdown: Dict[str, Any] = {}
        by_metric: Dict[MetricType, List[float]] = defaultdict(list)
        sessions: Set[str] = set()

        for event in events:
            by_metric[event.metric_type].append(event.value)
            if event.session_id:
                sessions.add(event.session_id)

        for mt, values in by_metric.items():
            metric_breakdown[mt.value] = {
                "count": len(values),
                "total": round(sum(values), 4),
                "average": round(sum(values) / len(values), 4),
                "min": min(values),
                "max": max(values),
            }

        time_span = events[-1].timestamp - events[0].timestamp if len(events) >= 2 else 0

        return {
            "player_id": player_id,
            "found": True,
            "event_count": len(events),
            "first_seen": events[0].timestamp,
            "last_seen": events[-1].timestamp,
            "active_duration_seconds": round(time_span, 2),
            "session_count": len(sessions),
            "sessions": sorted(sessions),
            "metric_breakdown": metric_breakdown,
        }

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Return a summary of all telemetry data for a specific session.

        Includes per-metric breakdowns, player information, session
        duration, and event timeline density.

        Args:
            session_id: The unique identifier of the session.

        Returns:
            A dict with the session's telemetry summary.
        """
        with self._lock:
            events = list(self._events_by_session.get(session_id, []))
            if not events:
                events = [e for e in self._events if e.session_id == session_id]

        if not events:
            return {"session_id": session_id, "event_count": 0, "found": False}

        metric_breakdown: Dict[str, Any] = {}
        by_metric: Dict[MetricType, List[float]] = defaultdict(list)
        players: Set[str] = set()

        for event in events:
            by_metric[event.metric_type].append(event.value)
            if event.player_id:
                players.add(event.player_id)

        for mt, values in by_metric.items():
            metric_breakdown[mt.value] = {
                "count": len(values),
                "total": round(sum(values), 4),
                "average": round(sum(values) / len(values), 4),
                "min": min(values),
                "max": max(values),
            }

        duration = events[-1].timestamp - events[0].timestamp if len(events) >= 2 else 0
        event_rate = round(len(events) / duration, 4) if duration > 0 else 0.0

        return {
            "session_id": session_id,
            "found": True,
            "event_count": len(events),
            "started_at": events[0].timestamp,
            "ended_at": events[-1].timestamp,
            "duration_seconds": round(duration, 2),
            "event_rate_per_second": event_rate,
            "player_count": len(players),
            "players": sorted(players),
            "metric_breakdown": metric_breakdown,
        }

    # ------------------------------------------------------------------
    # Anomaly Detection
    # ------------------------------------------------------------------

    def detect_anomalies(
        self,
        metric_type: MetricType,
        time_range_start: float = 0.0,
        time_range_end: float = 0.0,
    ) -> Dict[str, Any]:
        """Detect statistical anomalies in metric data using z-score and IQR methods.

        Events with a z-score exceeding ANOMALY_ZSCORE_THRESHOLD or falling
        outside the IQR-based fences are flagged as potential anomalies.

        Args:
            metric_type: The metric type to analyze.
            time_range_start: Start of the analysis window.
            time_range_end: End of the analysis window.

        Returns:
            A dict with anomaly events, summary statistics, and detection metadata.
        """
        if time_range_end == 0.0:
            time_range_end = _time_module.time()

        events = self._filter_events(metric_type, time_range_start, time_range_end, {})

        if len(events) < self.FORECAST_MIN_DATA_POINTS:
            return {
                "metric_type": metric_type.value,
                "event_count": len(events),
                "error": f"Need at least {self.FORECAST_MIN_DATA_POINTS} events for anomaly detection.",
                "anomalies": [],
            }

        values = [e.value for e in events]

        # Z-score method
        mean_val = statistics.mean(values)
        stdev_val = statistics.stdev(values) if len(values) >= 2 else 0.0

        zscore_anomalies: List[Dict[str, Any]] = []
        if stdev_val > 0:
            for event in events:
                zscore = (event.value - mean_val) / stdev_val
                if abs(zscore) > self.ANOMALY_ZSCORE_THRESHOLD:
                    zscore_anomalies.append({
                        "event_id": event.event_id,
                        "value": event.value,
                        "zscore": round(zscore, 4),
                        "method": "zscore",
                        "timestamp": event.timestamp,
                    })

        # IQR method
        sorted_vals = sorted(values)
        q1 = self._compute_percentile(sorted_vals, 25.0)
        q3 = self._compute_percentile(sorted_vals, 75.0)
        iqr = q3 - q1
        lower_fence = q1 - self.ANOMALY_IQR_MULTIPLIER * iqr
        upper_fence = q3 + self.ANOMALY_IQR_MULTIPLIER * iqr

        iqr_anomalies: List[Dict[str, Any]] = []
        if iqr > 0:
            for event in events:
                if event.value < lower_fence or event.value > upper_fence:
                    iqr_anomalies.append({
                        "event_id": event.event_id,
                        "value": event.value,
                        "method": "iqr",
                        "timestamp": event.timestamp,
                    })

        # Merge and deduplicate by event_id
        seen_ids: Set[str] = set()
        all_anomalies: List[Dict[str, Any]] = []
        for anomaly in zscore_anomalies + iqr_anomalies:
            if anomaly["event_id"] not in seen_ids:
                seen_ids.add(anomaly["event_id"])
                all_anomalies.append(anomaly)

        all_anomalies.sort(key=lambda a: a["timestamp"])

        return {
            "metric_type": metric_type.value,
            "event_count": len(events),
            "anomaly_count": len(all_anomalies),
            "anomaly_rate": round(len(all_anomalies) / len(events), 4),
            "statistics": {
                "mean": round(mean_val, 4),
                "stdev": round(stdev_val, 4),
                "q1": round(q1, 4),
                "q3": round(q3, 4),
                "iqr": round(iqr, 4),
                "lower_fence": round(lower_fence, 4),
                "upper_fence": round(upper_fence, 4),
            },
            "zscore_threshold": self.ANOMALY_ZSCORE_THRESHOLD,
            "iqr_multiplier": self.ANOMALY_IQR_MULTIPLIER,
            "anomalies": all_anomalies,
        }

    # ------------------------------------------------------------------
    # Trend Forecasting
    # ------------------------------------------------------------------

    def predict_trends(
        self,
        metric_type: MetricType,
        forecast_hours: float = 1.0,
    ) -> Dict[str, Any]:
        """Forecast future metric values using simple linear regression on historical data.

        Aggregates events into time-bucketed averages, fits a linear model
        using least-squares regression, and projects forward for the specified
        forecast horizon.

        Args:
            metric_type: The metric type to forecast.
            forecast_hours: Number of hours to forecast into the future.

        Returns:
            A dict with predicted values, trend direction, confidence metrics,
            and the regression model parameters.
        """
        with self._lock:
            events = list(self._events_by_metric.get(metric_type, []))
            if not events:
                events = [e for e in self._events if e.metric_type == metric_type]

        if len(events) < self.FORECAST_MIN_DATA_POINTS:
            return {
                "metric_type": metric_type.value,
                "event_count": len(events),
                "error": f"Need at least {self.FORECAST_MIN_DATA_POINTS} events for forecasting.",
                "predictions": [],
            }

        # Bucket events into time windows for stable regression input
        bucket_size = max(60.0, (events[-1].timestamp - events[0].timestamp) / min(len(events), 50))
        buckets: Dict[int, List[float]] = defaultdict(list)
        for event in events:
            bucket_key = int(event.timestamp / bucket_size)
            buckets[bucket_key].append(event.value)

        data_points: List[Tuple[float, float]] = []
        for bucket_key in sorted(buckets.keys()):
            avg = sum(buckets[bucket_key]) / len(buckets[bucket_key])
            center_time = bucket_key * bucket_size + bucket_size / 2.0
            data_points.append((center_time, avg))

        if len(data_points) < 2:
            return {
                "metric_type": metric_type.value,
                "event_count": len(events),
                "error": "Insufficient time-bucketed data points for regression.",
                "predictions": [],
            }

        # Simple linear regression: y = slope * x + intercept
        n = len(data_points)
        sum_x = sum(p[0] for p in data_points)
        sum_y = sum(p[1] for p in data_points)
        sum_xy = sum(p[0] * p[1] for p in data_points)
        sum_x2 = sum(p[0] ** 2 for p in data_points)

        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return {
                "metric_type": metric_type.value,
                "event_count": len(events),
                "error": "Cannot fit regression line (zero variance in time values).",
                "predictions": [],
            }

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n

        # Compute R-squared for confidence assessment
        y_mean = sum_y / n
        ss_res = sum((p[1] - (slope * p[0] + intercept)) ** 2 for p in data_points)
        ss_tot = sum((p[1] - y_mean) ** 2 for p in data_points)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Generate forecast predictions
        forecast_seconds = forecast_hours * 3600.0
        last_time = data_points[-1][0]
        prediction_steps = max(1, int(forecast_seconds / bucket_size))
        predictions: List[Dict[str, Any]] = []

        for step in range(1, prediction_steps + 1):
            future_time = last_time + step * bucket_size
            predicted_value = slope * future_time + intercept
            predictions.append({
                "timestamp": future_time,
                "predicted_value": round(predicted_value, 4),
                "hours_from_now": round((future_time - last_time) / 3600.0, 2),
            })

        # Determine trend direction
        if slope > 0.001:
            trend = "increasing"
        elif slope < -0.001:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "metric_type": metric_type.value,
            "event_count": len(events),
            "data_points": len(data_points),
            "bucket_size_seconds": round(bucket_size, 2),
            "forecast_hours": forecast_hours,
            "trend": trend,
            "slope": round(slope, 6),
            "intercept": round(intercept, 4),
            "r_squared": round(r_squared, 4),
            "confidence": "high" if r_squared > 0.7 else ("moderate" if r_squared > 0.4 else "low"),
            "predictions": predictions,
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive pipeline statistics including event counts,
        index sizes, alert status, and query performance data."""
        with self._lock:
            metric_counts: Dict[str, int] = {}
            for mt, evts in self._events_by_metric.items():
                metric_counts[mt.value] = len(evts)

            player_counts: Dict[str, int] = {}
            for pid, evts in self._events_by_player.items():
                player_counts[pid] = len(evts)

            top_players = sorted(player_counts.items(), key=lambda x: -x[1])[:10]
            top_metrics = sorted(metric_counts.items(), key=lambda x: -x[1])[:10]

            return {
                "total_events_ingested": self._total_events,
                "events_in_memory": len(self._events),
                "max_events_capacity": self.MAX_EVENTS,
                "total_batches": self._total_batches,
                "total_reports": self._total_reports,
                "total_queries_run": self._total_queries_run,
                "total_alerts_triggered": self._total_alerts_triggered,
                "unique_players": len(self._events_by_player),
                "unique_sessions": len(self._events_by_session),
                "unique_metric_types": len(self._events_by_metric),
                "configured_alerts": sum(len(c) for c in self._alerts_config.values()),
                "recent_triggered_alerts": len(self._triggered_alerts),
                "top_players_by_events": [
                    {"player_id": pid, "event_count": count}
                    for pid, count in top_players
                ],
                "top_metrics_by_count": [
                    {"metric_type": mt, "event_count": count}
                    for mt, count in top_metrics
                ],
                "anomaly_zscore_threshold": self.ANOMALY_ZSCORE_THRESHOLD,
                "anomaly_iqr_multiplier": self.ANOMALY_IQR_MULTIPLIER,
                "forecast_min_data_points": self.FORECAST_MIN_DATA_POINTS,
            }


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_analytics_pipeline() -> AnalyticsPipelineEngine:
    """Return the singleton AnalyticsPipelineEngine instance."""
    return AnalyticsPipelineEngine.get_instance()