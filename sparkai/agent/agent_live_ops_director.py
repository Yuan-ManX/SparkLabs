"""
SparkLabs Agent - AI Live-Ops Director

A runtime fusion module that closes the loop between live player telemetry
and the running engine. The director segments players into cohorts,
ingests real-time gameplay metrics, reasons over trends to detect churn
risk and engagement drops, proposes retuning actions (difficulty
adjustments, live events, store promotions, balance changes), executes
approved actions against engine subsystems, and measures the impact of
each intervention.

This module embodies the AI-native principle: the engine is not a static
artifact but a living system that an intelligent agent continuously
observes, diagnoses, and retunes while players are in-session.

Architecture:
  LiveOpsDirector (singleton)
    |-- PlayerCohort, TelemetrySnapshot, TrendAnalysis, RetuneAction,
        ActionImpact, LiveOpsCampaign, LiveOpsStats, LiveOpsSnapshot,
        LiveOpsEvent
    |-- CohortType, MetricType, TrendDirection, AlertSeverity,
        ActionType, ActionStatus, ImpactVerdict, LiveOpsEventKind

Core Capabilities:
  - register_cohort / update_cohort / get_cohort / list_cohorts /
    delete_cohort: player segmentation with criteria and size tracking.
  - ingest_telemetry / get_telemetry / list_telemetry: real-time metric
    ingestion per cohort with retention and monetization signals.
  - analyze_trends / get_trend / list_trends: trend detection with
    direction, severity, and AI confidence scoring.
  - propose_action / approve_action / reject_action / execute_action /
    list_actions / get_action: retuning action lifecycle from proposal
    through execution to impact measurement.
  - measure_impact / get_impact / list_impacts: A/B-style impact
    measurement comparing before/after metric snapshots.
  - create_campaign / update_campaign / get_campaign / list_campaigns:
    campaign grouping for coordinated multi-action live-ops events.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_COHORTS: int = 200
_MAX_TELEMETRY_PER_COHORT: int = 1000
_MAX_TRENDS: int = 500
_MAX_ACTIONS: int = 1000
_MAX_IMPACTS: int = 1000
_MAX_CAMPAIGNS: int = 100
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


class CohortType(Enum):
    NEW_PLAYER = "new_player"
    RETURNING_PLAYER = "returning_player"
    VETERAN = "veteran"
    WHALE = "whale"
    FREE_TO_PLAY = "free_to_play"
    CHURNED = "churned"
    REACTIVATED = "reactivated"
    CUSTOM = "custom"


class MetricType(Enum):
    DAUS = "daus"
    MAUS = "maus"
    RETENTION = "retention"
    SESSION_LENGTH = "session_length"
    MONETIZATION = "monetization"
    ENGAGEMENT = "engagement"
    PROGRESSION = "progression"
    CHURN_RISK = "churn_risk"
    COMPLETION_RATE = "completion_rate"
    SOCIAL_ACTIVITY = "social_activity"


class TrendDirection(Enum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ActionType(Enum):
    DIFFICULTY_ADJUST = "difficulty_adjust"
    EVENT_TRIGGER = "event_trigger"
    STORE_PROMOTION = "store_promotion"
    BALANCE_CHANGE = "balance_change"
    REWARD_BOOST = "reward_boost"
    CONTENT_UNLOCK = "content_unlock"
    NOTIFICATION_SEND = "notification_send"
    FEATURE_FLAG_TOGGLE = "feature_flag_toggle"
    ECONOMY_RECALIBRATE = "economy_recalibrate"
    PERSONALIZED_OFFER = "personalized_offer"


class ActionStatus(Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ImpactVerdict(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    INCONCLUSIVE = "inconclusive"


class LiveOpsEventKind(Enum):
    COHORT_REGISTERED = "cohort_registered"
    COHORT_UPDATED = "cohort_updated"
    COHORT_REMOVED = "cohort_removed"
    TELEMETRY_INGESTED = "telemetry_ingested"
    TREND_DETECTED = "trend_detected"
    ACTION_PROPOSED = "action_proposed"
    ACTION_APPROVED = "action_approved"
    ACTION_REJECTED = "action_rejected"
    ACTION_EXECUTED = "action_executed"
    ACTION_COMPLETED = "action_completed"
    IMPACT_MEASURED = "impact_measured"
    CAMPAIGN_CREATED = "campaign_created"
    CAMPAIGN_UPDATED = "campaign_updated"
    CAMPAIGN_LAUNCHED = "campaign_launched"
    CAMPAIGN_COMPLETED = "campaign_completed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PlayerCohort:
    """A player segment defined by criteria for live-ops targeting."""
    cohort_id: str
    name: str
    cohort_type: CohortType = CohortType.CUSTOM
    description: str = ""
    criteria: Dict[str, Any] = field(default_factory=dict)
    player_count: int = 0
    is_active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TelemetrySnapshot:
    """A point-in-time metric snapshot for a cohort."""
    snapshot_id: str
    cohort_id: str
    metric: MetricType
    value: float = 0.0
    previous_value: float = 0.0
    delta: float = 0.0
    sample_size: int = 0
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TrendAnalysis:
    """An AI-analyzed trend over a cohort's metrics."""
    trend_id: str
    cohort_id: str
    metric: MetricType
    direction: TrendDirection = TrendDirection.STABLE
    severity: AlertSeverity = AlertSeverity.INFO
    current_value: float = 0.0
    change_rate: float = 0.0
    confidence: float = 0.0
    description: str = ""
    recommended_actions: List[str] = field(default_factory=list)
    detected_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RetuneAction:
    """A proposed or executed retuning action targeting engine subsystems."""
    action_id: str
    cohort_id: str
    action_type: ActionType
    title: str = ""
    description: str = ""
    target_system: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    status: ActionStatus = ActionStatus.PROPOSED
    proposed_by: str = "ai_director"
    approved_by: str = ""
    executed_at: str = ""
    completed_at: str = ""
    campaign_id: str = ""
    trend_id: str = ""
    expected_impact: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ActionImpact:
    """Measured impact of an executed retuning action."""
    impact_id: str
    action_id: str
    metric: MetricType
    before_value: float = 0.0
    after_value: float = 0.0
    delta: float = 0.0
    delta_percentage: float = 0.0
    verdict: ImpactVerdict = ImpactVerdict.INCONCLUSIVE
    confidence: float = 0.0
    measurement_window: str = ""
    notes: str = ""
    measured_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LiveOpsCampaign:
    """A coordinated live-ops campaign grouping multiple retune actions."""
    campaign_id: str
    name: str
    description: str = ""
    cohort_ids: List[str] = field(default_factory=list)
    action_ids: List[str] = field(default_factory=list)
    status: str = "draft"
    start_time: str = ""
    end_time: str = ""
    target_metric: MetricType = MetricType.ENGAGEMENT
    target_improvement: float = 0.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LiveOpsStats:
    total_cohorts: int = 0
    active_cohorts: int = 0
    total_telemetry_points: int = 0
    total_trends: int = 0
    critical_trends: int = 0
    total_actions: int = 0
    executed_actions: int = 0
    completed_actions: int = 0
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LiveOpsSnapshot:
    cohorts: List[Dict[str, Any]] = field(default_factory=list)
    trends: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    campaigns: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LiveOpsEvent:
    event_id: str
    kind: LiveOpsEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Live-Ops Director Singleton
# ---------------------------------------------------------------------------


class LiveOpsDirector:
    """AI-native fusion module closing the loop between live telemetry and engine state."""

    _instance: Optional["LiveOpsDirector"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "LiveOpsDirector":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "LiveOpsDirector":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._cohorts: Dict[str, PlayerCohort] = {}
            self._telemetry: Dict[str, List[TelemetrySnapshot]] = {}
            self._trends: Dict[str, TrendAnalysis] = {}
            self._actions: Dict[str, RetuneAction] = {}
            self._impacts: Dict[str, ActionImpact] = {}
            self._campaigns: Dict[str, LiveOpsCampaign] = {}
            self._events: List[LiveOpsEvent] = []
            self._seed_data()
            self._initialized = True

    def _emit(self, kind: LiveOpsEventKind, data: Dict[str, Any]) -> None:
        event = LiveOpsEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Cohort Management
    # ------------------------------------------------------------------

    def register_cohort(self, name: str, cohort_type: CohortType = CohortType.CUSTOM,
                        description: str = "", criteria: Dict[str, Any] = None,
                        player_count: int = 0, is_active: bool = True) -> PlayerCohort:
        with self._lock:
            cohort = PlayerCohort(
                cohort_id=_new_id("coh"),
                name=name,
                cohort_type=cohort_type,
                description=description,
                criteria=criteria or {},
                player_count=player_count,
                is_active=is_active,
            )
            self._cohorts[cohort.cohort_id] = cohort
            _evict_fifo_dict(self._cohorts, _MAX_COHORTS)
            self._emit(LiveOpsEventKind.COHORT_REGISTERED, {"cohort_id": cohort.cohort_id})
            return cohort

    def update_cohort(self, cohort_id: str, updates: Dict[str, Any]) -> Optional[PlayerCohort]:
        with self._lock:
            cohort = self._cohorts.get(cohort_id)
            if cohort is None:
                return None
            for k, v in updates.items():
                if k == "cohort_type" and isinstance(v, str):
                    try:
                        v = CohortType(v)
                    except ValueError:
                        continue
                if hasattr(cohort, k) and k not in ("cohort_id", "created_at"):
                    setattr(cohort, k, v)
            cohort.updated_at = _now()
            self._emit(LiveOpsEventKind.COHORT_UPDATED, {"cohort_id": cohort_id})
            return cohort

    def get_cohort(self, cohort_id: str) -> Optional[PlayerCohort]:
        with self._lock:
            return self._cohorts.get(cohort_id)

    def list_cohorts(self, cohort_type: CohortType = None,
                     is_active: bool = None) -> List[PlayerCohort]:
        with self._lock:
            items = list(self._cohorts.values())
            if cohort_type is not None:
                items = [c for c in items if c.cohort_type == cohort_type]
            if is_active is not None:
                items = [c for c in items if c.is_active == is_active]
            return items

    def delete_cohort(self, cohort_id: str) -> bool:
        with self._lock:
            if cohort_id not in self._cohorts:
                return False
            del self._cohorts[cohort_id]
            self._telemetry.pop(cohort_id, None)
            self._emit(LiveOpsEventKind.COHORT_REMOVED, {"cohort_id": cohort_id})
            return True

    # ------------------------------------------------------------------
    # Telemetry Ingestion
    # ------------------------------------------------------------------

    def ingest_telemetry(self, cohort_id: str, metric: MetricType,
                         value: float, previous_value: float = 0.0,
                         sample_size: int = 0,
                         metadata: Dict[str, Any] = None) -> Optional[TelemetrySnapshot]:
        with self._lock:
            if cohort_id not in self._cohorts:
                return None
            delta = value - previous_value
            snapshot = TelemetrySnapshot(
                snapshot_id=_new_id("tel"),
                cohort_id=cohort_id,
                metric=metric,
                value=value,
                previous_value=previous_value,
                delta=delta,
                sample_size=sample_size,
                metadata=metadata or {},
            )
            if cohort_id not in self._telemetry:
                self._telemetry[cohort_id] = []
            self._telemetry[cohort_id].append(snapshot)
            _evict_fifo_list(self._telemetry[cohort_id], _MAX_TELEMETRY_PER_COHORT)
            self._emit(LiveOpsEventKind.TELEMETRY_INGESTED, {
                "cohort_id": cohort_id,
                "metric": metric.value,
                "value": value,
            })
            return snapshot

    def get_telemetry(self, cohort_id: str, metric: MetricType = None,
                      limit: int = 50) -> List[TelemetrySnapshot]:
        with self._lock:
            snapshots = self._telemetry.get(cohort_id, [])
            if metric is not None:
                snapshots = [s for s in snapshots if s.metric == metric]
            return snapshots[-limit:]

    def list_telemetry(self, cohort_id: str = None, limit: int = 100) -> List[TelemetrySnapshot]:
        with self._lock:
            result: List[TelemetrySnapshot] = []
            if cohort_id:
                result = self._telemetry.get(cohort_id, [])[-limit:]
            else:
                for snaps in self._telemetry.values():
                    result.extend(snaps)
                result = result[-limit:]
            return result

    # ------------------------------------------------------------------
    # Trend Analysis
    # ------------------------------------------------------------------

    def analyze_trends(self, cohort_id: str = None,
                       metric: MetricType = None) -> List[TrendAnalysis]:
        with self._lock:
            analyses: List[TrendAnalysis] = []
            cohort_ids = [cohort_id] if cohort_id else list(self._telemetry.keys())
            for cid in cohort_ids:
                snapshots = self._telemetry.get(cid, [])
                if not snapshots:
                    continue
                metrics_to_check = [metric] if metric else list(set(s.metric for s in snapshots))
                for m in metrics_to_check:
                    metric_snaps = [s for s in snapshots if s.metric == m]
                    if len(metric_snaps) < 2:
                        continue
                    latest = metric_snaps[-1]
                    earliest = metric_snaps[0]
                    change_rate = 0.0
                    if earliest.value != 0:
                        change_rate = (latest.value - earliest.value) / abs(earliest.value)
                    direction = TrendDirection.STABLE
                    if abs(change_rate) < 0.05:
                        direction = TrendDirection.STABLE
                    elif change_rate > 0:
                        direction = TrendDirection.RISING
                    elif change_rate < 0:
                        direction = TrendDirection.FALLING
                    if len(metric_snaps) >= 4:
                        deltas = [s.delta for s in metric_snaps[-4:]]
                        sign_changes = sum(1 for i in range(1, len(deltas))
                                           if (deltas[i] > 0) != (deltas[i-1] > 0))
                        if sign_changes >= 2:
                            direction = TrendDirection.VOLATILE

                    severity = AlertSeverity.INFO
                    if m in (MetricType.CHURN_RISK, MetricType.RETENTION):
                        if direction == TrendDirection.RISING and m == MetricType.CHURN_RISK:
                            severity = AlertSeverity.CRITICAL if change_rate > 0.2 else AlertSeverity.WARNING
                        if direction == TrendDirection.FALLING and m == MetricType.RETENTION:
                            severity = AlertSeverity.CRITICAL if change_rate < -0.2 else AlertSeverity.WARNING
                    elif direction == TrendDirection.FALLING and change_rate < -0.3:
                        severity = AlertSeverity.WARNING
                    if direction == TrendDirection.VOLATILE:
                        severity = AlertSeverity.WARNING

                    recommended: List[str] = []
                    if severity in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY):
                        recommended.append(ActionType.DIFFICULTY_ADJUST.value)
                        recommended.append(ActionType.REWARD_BOOST.value)
                    elif severity == AlertSeverity.WARNING:
                        recommended.append(ActionType.EVENT_TRIGGER.value)
                        recommended.append(ActionType.NOTIFICATION_SEND.value)
                    if m == MetricType.MONETIZATION and direction == TrendDirection.FALLING:
                        recommended.append(ActionType.STORE_PROMOTION.value)
                        recommended.append(ActionType.PERSONALIZED_OFFER.value)

                    confidence = min(1.0, len(metric_snaps) / 10.0)
                    description = (
                        f"{m.value} for cohort {cid} is {direction.value} "
                        f"with {change_rate:+.1%} change rate (confidence: {confidence:.0%})"
                    )
                    trend = TrendAnalysis(
                        trend_id=_new_id("trd"),
                        cohort_id=cid,
                        metric=m,
                        direction=direction,
                        severity=severity,
                        current_value=latest.value,
                        change_rate=change_rate,
                        confidence=confidence,
                        description=description,
                        recommended_actions=recommended,
                    )
                    self._trends[trend.trend_id] = trend
                    _evict_fifo_dict(self._trends, _MAX_TRENDS)
                    analyses.append(trend)
                    self._emit(LiveOpsEventKind.TREND_DETECTED, {
                        "trend_id": trend.trend_id,
                        "cohort_id": cid,
                        "metric": m.value,
                        "direction": direction.value,
                        "severity": severity.value,
                    })
            return analyses

    def get_trend(self, trend_id: str) -> Optional[TrendAnalysis]:
        with self._lock:
            return self._trends.get(trend_id)

    def list_trends(self, cohort_id: str = None, severity: AlertSeverity = None,
                    limit: int = 50) -> List[TrendAnalysis]:
        with self._lock:
            items = list(self._trends.values())
            if cohort_id is not None:
                items = [t for t in items if t.cohort_id == cohort_id]
            if severity is not None:
                items = [t for t in items if t.severity == severity]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Retune Action Lifecycle
    # ------------------------------------------------------------------

    def propose_action(self, cohort_id: str, action_type: ActionType,
                       title: str = "", description: str = "",
                       target_system: str = "",
                       parameters: Dict[str, Any] = None,
                       priority: int = 5, trend_id: str = "",
                       expected_impact: str = "",
                       proposed_by: str = "ai_director") -> Optional[RetuneAction]:
        with self._lock:
            if cohort_id not in self._cohorts:
                return None
            action = RetuneAction(
                action_id=_new_id("act"),
                cohort_id=cohort_id,
                action_type=action_type,
                title=title,
                description=description,
                target_system=target_system,
                parameters=parameters or {},
                priority=priority,
                trend_id=trend_id,
                expected_impact=expected_impact,
                proposed_by=proposed_by,
            )
            self._actions[action.action_id] = action
            _evict_fifo_dict(self._actions, _MAX_ACTIONS)
            self._emit(LiveOpsEventKind.ACTION_PROPOSED, {
                "action_id": action.action_id,
                "cohort_id": cohort_id,
                "action_type": action_type.value,
            })
            return action

    def approve_action(self, action_id: str, approved_by: str = "operator") -> Optional[RetuneAction]:
        with self._lock:
            action = self._actions.get(action_id)
            if action is None or action.status != ActionStatus.PROPOSED:
                return None
            action.status = ActionStatus.APPROVED
            action.approved_by = approved_by
            action.updated_at = _now()
            self._emit(LiveOpsEventKind.ACTION_APPROVED, {"action_id": action_id})
            return action

    def reject_action(self, action_id: str) -> Optional[RetuneAction]:
        with self._lock:
            action = self._actions.get(action_id)
            if action is None or action.status != ActionStatus.PROPOSED:
                return None
            action.status = ActionStatus.REJECTED
            action.updated_at = _now()
            self._emit(LiveOpsEventKind.ACTION_REJECTED, {"action_id": action_id})
            return action

    def execute_action(self, action_id: str) -> Optional[RetuneAction]:
        with self._lock:
            action = self._actions.get(action_id)
            if action is None or action.status != ActionStatus.APPROVED:
                return None
            action.status = ActionStatus.EXECUTING
            action.executed_at = _now()
            action.updated_at = _now()
            self._emit(LiveOpsEventKind.ACTION_EXECUTED, {"action_id": action_id})
            action.status = ActionStatus.COMPLETED
            action.completed_at = _now()
            action.updated_at = _now()
            self._emit(LiveOpsEventKind.ACTION_COMPLETED, {"action_id": action_id})
            return action

    def get_action(self, action_id: str) -> Optional[RetuneAction]:
        with self._lock:
            return self._actions.get(action_id)

    def list_actions(self, cohort_id: str = None, status: ActionStatus = None,
                     action_type: ActionType = None,
                     limit: int = 50) -> List[RetuneAction]:
        with self._lock:
            items = list(self._actions.values())
            if cohort_id is not None:
                items = [a for a in items if a.cohort_id == cohort_id]
            if status is not None:
                items = [a for a in items if a.status == status]
            if action_type is not None:
                items = [a for a in items if a.action_type == action_type]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Impact Measurement
    # ------------------------------------------------------------------

    def measure_impact(self, action_id: str, metric: MetricType,
                       before_value: float, after_value: float,
                       measurement_window: str = "24h",
                       confidence: float = 0.8,
                       notes: str = "") -> Optional[ActionImpact]:
        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                return None
            delta = after_value - before_value
            delta_pct = 0.0
            if before_value != 0:
                delta_pct = (delta / abs(before_value)) * 100.0
            verdict = ImpactVerdict.INCONCLUSIVE
            if abs(delta_pct) < 2.0:
                verdict = ImpactVerdict.NEUTRAL
            elif delta > 0:
                verdict = ImpactVerdict.POSITIVE
            elif delta < 0:
                verdict = ImpactVerdict.NEGATIVE
            if metric in (MetricType.CHURN_RISK,) and delta < 0:
                verdict = ImpactVerdict.POSITIVE
            impact = ActionImpact(
                impact_id=_new_id("imp"),
                action_id=action_id,
                metric=metric,
                before_value=before_value,
                after_value=after_value,
                delta=delta,
                delta_percentage=delta_pct,
                verdict=verdict,
                confidence=confidence,
                measurement_window=measurement_window,
                notes=notes,
            )
            self._impacts[impact.impact_id] = impact
            _evict_fifo_dict(self._impacts, _MAX_IMPACTS)
            self._emit(LiveOpsEventKind.IMPACT_MEASURED, {
                "impact_id": impact.impact_id,
                "action_id": action_id,
                "verdict": verdict.value,
            })
            return impact

    def get_impact(self, impact_id: str) -> Optional[ActionImpact]:
        with self._lock:
            return self._impacts.get(impact_id)

    def list_impacts(self, action_id: str = None, metric: MetricType = None,
                     verdict: ImpactVerdict = None,
                     limit: int = 50) -> List[ActionImpact]:
        with self._lock:
            items = list(self._impacts.values())
            if action_id is not None:
                items = [i for i in items if i.action_id == action_id]
            if metric is not None:
                items = [i for i in items if i.metric == metric]
            if verdict is not None:
                items = [i for i in items if i.verdict == verdict]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Campaign Management
    # ------------------------------------------------------------------

    def create_campaign(self, name: str, description: str = "",
                        cohort_ids: List[str] = None,
                        target_metric: MetricType = MetricType.ENGAGEMENT,
                        target_improvement: float = 0.0,
                        start_time: str = "", end_time: str = "") -> LiveOpsCampaign:
        with self._lock:
            campaign = LiveOpsCampaign(
                campaign_id=_new_id("cmp"),
                name=name,
                description=description,
                cohort_ids=cohort_ids or [],
                target_metric=target_metric,
                target_improvement=target_improvement,
                start_time=start_time,
                end_time=end_time,
            )
            self._campaigns[campaign.campaign_id] = campaign
            _evict_fifo_dict(self._campaigns, _MAX_CAMPAIGNS)
            self._emit(LiveOpsEventKind.CAMPAIGN_CREATED, {
                "campaign_id": campaign.campaign_id,
            })
            return campaign

    def update_campaign(self, campaign_id: str, updates: Dict[str, Any]) -> Optional[LiveOpsCampaign]:
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign is None:
                return None
            for k, v in updates.items():
                if k == "target_metric" and isinstance(v, str):
                    try:
                        v = MetricType(v)
                    except ValueError:
                        continue
                if hasattr(campaign, k) and k not in ("campaign_id", "created_at"):
                    setattr(campaign, k, v)
            campaign.updated_at = _now()
            self._emit(LiveOpsEventKind.CAMPAIGN_UPDATED, {"campaign_id": campaign_id})
            return campaign

    def get_campaign(self, campaign_id: str) -> Optional[LiveOpsCampaign]:
        with self._lock:
            return self._campaigns.get(campaign_id)

    def list_campaigns(self, status: str = None, limit: int = 50) -> List[LiveOpsCampaign]:
        with self._lock:
            items = list(self._campaigns.values())
            if status is not None:
                items = [c for c in items if c.status == status]
            return items[-limit:]

    def launch_campaign(self, campaign_id: str) -> Optional[LiveOpsCampaign]:
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign is None:
                return None
            campaign.status = "active"
            campaign.start_time = campaign.start_time or _now()
            campaign.updated_at = _now()
            for action_id in campaign.action_ids:
                action = self._actions.get(action_id)
                if action and action.status == ActionStatus.PROPOSED:
                    action.status = ActionStatus.APPROVED
                    action.approved_by = "campaign_auto"
                    action.updated_at = _now()
            self._emit(LiveOpsEventKind.CAMPAIGN_LAUNCHED, {"campaign_id": campaign_id})
            return campaign

    def complete_campaign(self, campaign_id: str) -> Optional[LiveOpsCampaign]:
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign is None:
                return None
            campaign.status = "completed"
            campaign.end_time = campaign.end_time or _now()
            campaign.updated_at = _now()
            self._emit(LiveOpsEventKind.CAMPAIGN_COMPLETED, {"campaign_id": campaign_id})
            return campaign

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, kind: LiveOpsEventKind = None, limit: int = 100) -> List[LiveOpsEvent]:
        with self._lock:
            items = list(self._events)
            if kind is not None:
                items = [e for e in items if e.kind == kind]
            return items[-limit:]

    def get_stats(self) -> LiveOpsStats:
        with self._lock:
            active_cohorts = sum(1 for c in self._cohorts.values() if c.is_active)
            telemetry_count = sum(len(snaps) for snaps in self._telemetry.values())
            critical_trends = sum(1 for t in self._trends.values()
                                  if t.severity in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY))
            executed = sum(1 for a in self._actions.values()
                           if a.status in (ActionStatus.EXECUTING, ActionStatus.COMPLETED))
            completed = sum(1 for a in self._actions.values()
                            if a.status == ActionStatus.COMPLETED)
            active_campaigns = sum(1 for c in self._campaigns.values()
                                   if c.status == "active")
            return LiveOpsStats(
                total_cohorts=len(self._cohorts),
                active_cohorts=active_cohorts,
                total_telemetry_points=telemetry_count,
                total_trends=len(self._trends),
                critical_trends=critical_trends,
                total_actions=len(self._actions),
                executed_actions=executed,
                completed_actions=completed,
                total_campaigns=len(self._campaigns),
                active_campaigns=active_campaigns,
                total_events=len(self._events),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "cohorts": len(self._cohorts),
                "telemetry_points": sum(len(s) for s in self._telemetry.values()),
                "trends": len(self._trends),
                "actions": len(self._actions),
                "impacts": len(self._impacts),
                "campaigns": len(self._campaigns),
                "events": len(self._events),
            }

    def get_snapshot(self) -> LiveOpsSnapshot:
        with self._lock:
            return LiveOpsSnapshot(
                cohorts=[c.to_dict() for c in list(self._cohorts.values())[:20]],
                trends=[t.to_dict() for t in list(self._trends.values())[:20]],
                actions=[a.to_dict() for a in list(self._actions.values())[:20]],
                campaigns=[c.to_dict() for c in list(self._campaigns.values())[:20]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._cohorts.clear()
            self._telemetry.clear()
            self._trends.clear()
            self._actions.clear()
            self._impacts.clear()
            self._campaigns.clear()
            self._events.clear()
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        new_players = PlayerCohort(
            cohort_id="coh_seed_new",
            name="New Players (Day 1-7)",
            cohort_type=CohortType.NEW_PLAYER,
            description="Players in their first week",
            criteria={"days_played_max": 7},
            player_count=15420,
        )
        self._cohorts[new_players.cohort_id] = new_players

        veterans = PlayerCohort(
            cohort_id="coh_seed_vet",
            name="Veterans (30+ days)",
            cohort_type=CohortType.VETERAN,
            description="Long-term engaged players",
            criteria={"days_played_min": 30},
            player_count=3200,
        )
        self._cohorts[veterans.cohort_id] = veterans

        whales = PlayerCohort(
            cohort_id="coh_seed_whale",
            name="Top Spenders",
            cohort_type=CohortType.WHALE,
            description="Players with high lifetime spend",
            criteria={"lifetime_spend_min": 500},
            player_count=180,
        )
        self._cohorts[whales.cohort_id] = whales

        self._telemetry["coh_seed_new"] = [
            TelemetrySnapshot(
                snapshot_id=_new_id("tel"),
                cohort_id="coh_seed_new",
                metric=MetricType.RETENTION,
                value=0.42,
                previous_value=0.45,
                delta=-0.03,
                sample_size=15420,
            ),
            TelemetrySnapshot(
                snapshot_id=_new_id("tel"),
                cohort_id="coh_seed_new",
                metric=MetricType.CHURN_RISK,
                value=0.38,
                previous_value=0.32,
                delta=0.06,
                sample_size=15420,
            ),
            TelemetrySnapshot(
                snapshot_id=_new_id("tel"),
                cohort_id="coh_seed_new",
                metric=MetricType.ENGAGEMENT,
                value=72.5,
                previous_value=75.0,
                delta=-2.5,
                sample_size=15420,
            ),
        ]

        self._telemetry["coh_seed_vet"] = [
            TelemetrySnapshot(
                snapshot_id=_new_id("tel"),
                cohort_id="coh_seed_vet",
                metric=MetricType.MONETIZATION,
                value=12.50,
                previous_value=14.00,
                delta=-1.50,
                sample_size=3200,
            ),
            TelemetrySnapshot(
                snapshot_id=_new_id("tel"),
                cohort_id="coh_seed_vet",
                metric=MetricType.SESSION_LENGTH,
                value=45.0,
                previous_value=48.0,
                delta=-3.0,
                sample_size=3200,
            ),
        ]

        self._telemetry["coh_seed_whale"] = [
            TelemetrySnapshot(
                snapshot_id=_new_id("tel"),
                cohort_id="coh_seed_whale",
                metric=MetricType.MONETIZATION,
                value=850.0,
                previous_value=800.0,
                delta=50.0,
                sample_size=180,
            ),
        ]

        campaign = LiveOpsCampaign(
            campaign_id="cmp_seed_retention",
            name="New Player Retention Boost",
            description="Coordinated actions to improve Day-7 retention",
            cohort_ids=["coh_seed_new"],
            target_metric=MetricType.RETENTION,
            target_improvement=0.05,
            status="draft",
        )
        self._campaigns[campaign.campaign_id] = campaign


def get_live_ops_director() -> LiveOpsDirector:
    """Factory function returning the singleton LiveOpsDirector instance."""
    return LiveOpsDirector.get_instance()
