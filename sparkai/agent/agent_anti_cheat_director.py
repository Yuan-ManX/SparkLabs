"""
SparkLabs Agent - AI Anti-Cheat Director

A runtime fusion module that protects game integrity by fusing anomaly
reasoning over live gameplay telemetry with dynamic enforcement actions.
The director ingests player behavior signals, detects suspicious patterns
through statistical anomaly detection, investigates flagged players with
multi-signal correlation, and applies graduated enforcement actions
ranging from silent observation to permanent bans.

This module embodies the AI-native principle: anti-cheat is not a static
rule engine but an intelligent agent that learns normal behavior
distributions, adapts to new exploit techniques, and reasons about
false-positive risk before acting.

Architecture:
  AntiCheatDirector (singleton)
    |-- PlayerProfile, BehaviorSample, AnomalyAlert, Investigation,
        EnforcementAction, AppealCase, AntiCheatStats, AntiCheatSnapshot,
        AntiCheatEvent
    |-- RiskLevel, BehaviorCategory, AnomalyType, AlertStatus,
        EnforcementType, InvestigationStatus, AppealStatus,
        AntiCheatEventKind

Core Capabilities:
  - register_player / update_player / get_player / list_players /
    delete_player: player profile management with risk scoring.
  - ingest_behavior / get_behavior / list_behavior: real-time behavior
    signal ingestion across movement, combat, economy, and social.
  - detect_anomalies / get_anomaly / list_anomalies: statistical anomaly
    detection with confidence scoring and multi-signal correlation.
  - open_investigation / update_investigation / close_investigation /
    list_investigations: multi-signal investigation workflow.
  - apply_enforcement / revoke_enforcement / list_enforcements:
    graduated enforcement from warning to ban with revocation support.
  - file_appeal / review_appeal / resolve_appeal / list_appeals:
    player appeal workflow with human-in-the-loop review.
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

_MAX_PLAYERS: int = 10000
_MAX_BEHAVIOR_PER_PLAYER: int = 500
_MAX_ANOMALIES: int = 5000
_MAX_INVESTIGATIONS: int = 1000
_MAX_ENFORCEMENTS: int = 2000
_MAX_APPEALS: int = 500
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


class RiskLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BehaviorCategory(Enum):
    MOVEMENT = "movement"
    COMBAT = "combat"
    ECONOMY = "economy"
    SOCIAL = "social"
    PROGRESSION = "progression"
    CUSTOM = "custom"


class AnomalyType(Enum):
    IMPOSSIBLE_SPEED = "impossible_speed"
    AIMBOT_PATTERN = "aimbot_pattern"
    WALLHACK_SIGNAL = "wallhack_signal"
    RESOURCE_DUPLICATION = "resource_duplication"
    IMPOSSIBLE_PROGRESS = "impossible_progress"
    BOT_BEHAVIOR = "bot_behavior"
    ACCOUNT_SHARING = "account_sharing"
    PAYMENT_FRAUD = "payment_fraud"
    STAT_PADDING = "stat_padding"
    CUSTOM = "custom"


class AlertStatus(Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    DISMISSED = "dismissed"


class InvestigationStatus(Enum):
    OPEN = "open"
    EVIDENCE_GATHERING = "evidence_gathering"
    PENDING_REVIEW = "pending_review"
    CONCLUDED = "concluded"
    CANCELLED = "cancelled"


class EnforcementType(Enum):
    SILENT_FLAG = "silent_flag"
    SOFT_SHADOWBAN = "soft_shadowban"
    RATE_LIMIT = "rate_limit"
    TEMPORARY_SUSPENSION = "temporary_suspension"
    PERMANENT_BAN = "permanent_ban"
    ACCOUNT_RESET = "account_reset"
    WARNING = "warning"


class AppealStatus(Enum):
    FILED = "filed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"


class AntiCheatEventKind(Enum):
    PLAYER_REGISTERED = "player_registered"
    PLAYER_UPDATED = "player_updated"
    PLAYER_REMOVED = "player_removed"
    BEHAVIOR_INGESTED = "behavior_ingested"
    ANOMALY_DETECTED = "anomaly_detected"
    ANOMALY_CONFIRMED = "anomaly_confirmed"
    ANOMALY_DISMISSED = "anomaly_dismissed"
    INVESTIGATION_OPENED = "investigation_opened"
    INVESTIGATION_UPDATED = "investigation_updated"
    INVESTIGATION_CONCLUDED = "investigation_concluded"
    ENFORCEMENT_APPLIED = "enforcement_applied"
    ENFORCEMENT_REVOKED = "enforcement_revoked"
    APPEAL_FILED = "appeal_filed"
    APPEAL_REVIEWED = "appeal_reviewed"
    APPEAL_RESOLVED = "appeal_resolved"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PlayerProfile:
    """A player's anti-cheat profile with risk scoring."""
    player_id: str
    display_name: str = ""
    account_created: str = ""
    risk_level: RiskLevel = RiskLevel.NONE
    risk_score: float = 0.0
    total_anomalies: int = 0
    confirmed_violations: int = 0
    active_enforcements: int = 0
    last_anomaly_at: str = ""
    last_enforcement_at: str = ""
    is_shadowbanned: bool = False
    is_banned: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BehaviorSample:
    """A single behavior telemetry sample from a player."""
    sample_id: str
    player_id: str
    category: BehaviorCategory
    metric: str = ""
    value: float = 0.0
    baseline_value: float = 0.0
    deviation: float = 0.0
    session_id: str = ""
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnomalyAlert:
    """A detected anomaly requiring investigation."""
    alert_id: str
    player_id: str
    anomaly_type: AnomalyType
    category: BehaviorCategory = BehaviorCategory.CUSTOM
    severity: RiskLevel = RiskLevel.MEDIUM
    confidence: float = 0.0
    description: str = ""
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    status: AlertStatus = AlertStatus.OPEN
    investigation_id: str = ""
    detected_at: str = field(default_factory=_now)
    resolved_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Investigation:
    """A multi-signal investigation into suspicious behavior."""
    investigation_id: str
    player_id: str
    alert_ids: List[str] = field(default_factory=list)
    status: InvestigationStatus = InvestigationStatus.OPEN
    assigned_to: str = "ai_director"
    evidence_summary: str = ""
    conclusion: str = ""
    verdict: AlertStatus = AlertStatus.OPEN
    opened_at: str = field(default_factory=_now)
    concluded_at: str = ""
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EnforcementAction:
    """A graduated enforcement action applied to a player."""
    enforcement_id: str
    player_id: str
    enforcement_type: EnforcementType
    reason: str = ""
    investigation_id: str = ""
    alert_id: str = ""
    duration_hours: int = 0
    is_active: bool = True
    applied_at: str = field(default_factory=_now)
    expires_at: str = ""
    revoked_at: str = ""
    revoked_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AppealCase:
    """A player appeal against an enforcement action."""
    appeal_id: str
    player_id: str
    enforcement_id: str
    reason: str = ""
    player_statement: str = ""
    status: AppealStatus = AppealStatus.FILED
    reviewer: str = ""
    review_notes: str = ""
    resolution: str = ""
    filed_at: str = field(default_factory=_now)
    reviewed_at: str = ""
    resolved_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AntiCheatStats:
    total_players: int = 0
    flagged_players: int = 0
    banned_players: int = 0
    total_behavior_samples: int = 0
    total_anomalies: int = 0
    open_anomalies: int = 0
    confirmed_anomalies: int = 0
    total_investigations: int = 0
    open_investigations: int = 0
    total_enforcements: int = 0
    active_enforcements: int = 0
    total_appeals: int = 0
    pending_appeals: int = 0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AntiCheatSnapshot:
    players: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    investigations: List[Dict[str, Any]] = field(default_factory=list)
    enforcements: List[Dict[str, Any]] = field(default_factory=list)
    appeals: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AntiCheatEvent:
    event_id: str
    kind: AntiCheatEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Anti-Cheat Director Singleton
# ---------------------------------------------------------------------------


class AntiCheatDirector:
    """AI-native fusion module protecting game integrity through anomaly reasoning."""

    _instance: Optional["AntiCheatDirector"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "AntiCheatDirector":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AntiCheatDirector":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._players: Dict[str, PlayerProfile] = {}
            self._behavior: Dict[str, List[BehaviorSample]] = {}
            self._anomalies: Dict[str, AnomalyAlert] = {}
            self._investigations: Dict[str, Investigation] = {}
            self._enforcements: Dict[str, EnforcementAction] = {}
            self._appeals: Dict[str, AppealCase] = {}
            self._events: List[AntiCheatEvent] = []
            self._seed_data()
            self._initialized = True

    def _emit(self, kind: AntiCheatEventKind, data: Dict[str, Any]) -> None:
        event = AntiCheatEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _recalc_risk(self, player: PlayerProfile) -> None:
        confirmed = player.confirmed_violations
        active = player.active_enforcements
        if player.is_banned or confirmed >= 3 or active >= 2:
            player.risk_level = RiskLevel.CRITICAL
            player.risk_score = 1.0
        elif confirmed >= 2 or active >= 1:
            player.risk_level = RiskLevel.HIGH
            player.risk_score = 0.75
        elif confirmed >= 1 or player.total_anomalies >= 3:
            player.risk_level = RiskLevel.MEDIUM
            player.risk_score = 0.5
        elif player.total_anomalies >= 1:
            player.risk_level = RiskLevel.LOW
            player.risk_score = 0.25
        else:
            player.risk_level = RiskLevel.NONE
            player.risk_score = 0.0
        player.updated_at = _now()

    # ------------------------------------------------------------------
    # Player Profile Management
    # ------------------------------------------------------------------

    def register_player(self, player_id: str, display_name: str = "",
                        account_created: str = "",
                        metadata: Dict[str, Any] = None) -> PlayerProfile:
        with self._lock:
            player = PlayerProfile(
                player_id=player_id,
                display_name=display_name,
                account_created=account_created,
                metadata=metadata or {},
            )
            self._players[player.player_id] = player
            _evict_fifo_dict(self._players, _MAX_PLAYERS)
            self._emit(AntiCheatEventKind.PLAYER_REGISTERED, {"player_id": player_id})
            return player

    def update_player(self, player_id: str, updates: Dict[str, Any]) -> Optional[PlayerProfile]:
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                return None
            for k, v in updates.items():
                if k == "risk_level" and isinstance(v, str):
                    try:
                        v = RiskLevel(v)
                    except ValueError:
                        continue
                if hasattr(player, k) and k not in ("player_id", "created_at"):
                    setattr(player, k, v)
            self._recalc_risk(player)
            self._emit(AntiCheatEventKind.PLAYER_UPDATED, {"player_id": player_id})
            return player

    def get_player(self, player_id: str) -> Optional[PlayerProfile]:
        with self._lock:
            return self._players.get(player_id)

    def list_players(self, risk_level: RiskLevel = None,
                     is_banned: bool = None, limit: int = 100) -> List[PlayerProfile]:
        with self._lock:
            items = list(self._players.values())
            if risk_level is not None:
                items = [p for p in items if p.risk_level == risk_level]
            if is_banned is not None:
                items = [p for p in items if p.is_banned == is_banned]
            return items[-limit:]

    def delete_player(self, player_id: str) -> bool:
        with self._lock:
            if player_id not in self._players:
                return False
            del self._players[player_id]
            self._behavior.pop(player_id, None)
            self._emit(AntiCheatEventKind.PLAYER_REMOVED, {"player_id": player_id})
            return True

    # ------------------------------------------------------------------
    # Behavior Ingestion
    # ------------------------------------------------------------------

    def ingest_behavior(self, player_id: str, category: BehaviorCategory,
                        metric: str, value: float, baseline_value: float = 0.0,
                        session_id: str = "",
                        metadata: Dict[str, Any] = None) -> Optional[BehaviorSample]:
        with self._lock:
            if player_id not in self._players:
                return None
            deviation = 0.0
            if baseline_value != 0:
                deviation = (value - baseline_value) / abs(baseline_value)
            sample = BehaviorSample(
                sample_id=_new_id("beh"),
                player_id=player_id,
                category=category,
                metric=metric,
                value=value,
                baseline_value=baseline_value,
                deviation=deviation,
                session_id=session_id,
                metadata=metadata or {},
            )
            if player_id not in self._behavior:
                self._behavior[player_id] = []
            self._behavior[player_id].append(sample)
            _evict_fifo_list(self._behavior[player_id], _MAX_BEHAVIOR_PER_PLAYER)
            self._emit(AntiCheatEventKind.BEHAVIOR_INGESTED, {
                "player_id": player_id,
                "category": category.value,
                "metric": metric,
            })
            return sample

    def get_behavior(self, player_id: str, category: BehaviorCategory = None,
                     limit: int = 50) -> List[BehaviorSample]:
        with self._lock:
            samples = self._behavior.get(player_id, [])
            if category is not None:
                samples = [s for s in samples if s.category == category]
            return samples[-limit:]

    def list_behavior(self, player_id: str = None, limit: int = 100) -> List[BehaviorSample]:
        with self._lock:
            result: List[BehaviorSample] = []
            if player_id:
                result = self._behavior.get(player_id, [])[-limit:]
            else:
                for samples in self._behavior.values():
                    result.extend(samples)
                result = result[-limit:]
            return result

    # ------------------------------------------------------------------
    # Anomaly Detection
    # ------------------------------------------------------------------

    def detect_anomalies(self, player_id: str = None) -> List[AnomalyAlert]:
        with self._lock:
            alerts: List[AnomalyAlert] = []
            player_ids = [player_id] if player_id else list(self._behavior.keys())
            for pid in player_ids:
                samples = self._behavior.get(pid, [])
                if not samples:
                    continue
                player = self._players.get(pid)
                if player is None:
                    continue
                by_metric: Dict[Tuple[str, str], List[BehaviorSample]] = {}
                for s in samples:
                    key = (s.category.value, s.metric)
                    by_metric.setdefault(key, []).append(s)

                for (cat, metric), metric_samples in by_metric.items():
                    deviations = [s.deviation for s in metric_samples[-10:]]
                    if len(deviations) < 2:
                        continue
                    avg_dev = sum(deviations) / len(deviations)
                    max_dev = max(abs(d) for d in deviations)
                    if max_dev < 0.5 and avg_dev < 0.3:
                        continue

                    anomaly_type = AnomalyType.CUSTOM
                    category = BehaviorCategory(cat)
                    severity = RiskLevel.LOW
                    confidence = min(1.0, len(deviations) / 5.0)

                    if metric in ("move_speed", "movement_speed", "velocity"):
                        anomaly_type = AnomalyType.IMPOSSIBLE_SPEED
                        category = BehaviorCategory.MOVEMENT
                        severity = RiskLevel.HIGH if max_dev > 1.0 else RiskLevel.MEDIUM
                    elif metric in ("aim_accuracy", "headshot_rate", "tracking_precision"):
                        anomaly_type = AnomalyType.AIMBOT_PATTERN
                        category = BehaviorCategory.COMBAT
                        severity = RiskLevel.CRITICAL if max_dev > 1.5 else RiskLevel.HIGH
                    elif metric in ("wall_bang_rate", "tracking_through_walls"):
                        anomaly_type = AnomalyType.WALLHACK_SIGNAL
                        category = BehaviorCategory.COMBAT
                        severity = RiskLevel.HIGH
                    elif metric in ("gold_earned", "resource_generated", "item_crafted"):
                        anomaly_type = AnomalyType.RESOURCE_DUPLICATION
                        category = BehaviorCategory.ECONOMY
                        severity = RiskLevel.HIGH
                    elif metric in ("xp_gained", "level_progress", "quest_completion_rate"):
                        anomaly_type = AnomalyType.IMPOSSIBLE_PROGRESS
                        category = BehaviorCategory.PROGRESSION
                        severity = RiskLevel.HIGH if max_dev > 1.0 else RiskLevel.MEDIUM
                    elif metric in ("action_regularity", "input_entropy", "response_variance"):
                        anomaly_type = AnomalyType.BOT_BEHAVIOR
                        category = BehaviorCategory.MOVEMENT
                        severity = RiskLevel.MEDIUM

                    description = (
                        f"Detected {anomaly_type.value} for player {pid}: "
                        f"{metric} deviates {avg_dev:+.1%} from baseline "
                        f"(max: {max_dev:+.1%}, confidence: {confidence:.0%})"
                    )
                    evidence = [
                        {"metric": s.metric, "value": s.value,
                         "baseline": s.baseline_value, "deviation": s.deviation,
                         "timestamp": s.timestamp}
                        for s in metric_samples[-5:]
                    ]
                    alert = AnomalyAlert(
                        alert_id=_new_id("anm"),
                        player_id=pid,
                        anomaly_type=anomaly_type,
                        category=category,
                        severity=severity,
                        confidence=confidence,
                        description=description,
                        evidence=evidence,
                    )
                    self._anomalies[alert.alert_id] = alert
                    _evict_fifo_dict(self._anomalies, _MAX_ANOMALIES)
                    player.total_anomalies += 1
                    player.last_anomaly_at = _now()
                    self._recalc_risk(player)
                    alerts.append(alert)
                    self._emit(AntiCheatEventKind.ANOMALY_DETECTED, {
                        "alert_id": alert.alert_id,
                        "player_id": pid,
                        "anomaly_type": anomaly_type.value,
                        "severity": severity.value,
                    })
            return alerts

    def get_anomaly(self, alert_id: str) -> Optional[AnomalyAlert]:
        with self._lock:
            return self._anomalies.get(alert_id)

    def list_anomalies(self, player_id: str = None, status: AlertStatus = None,
                       severity: RiskLevel = None,
                       limit: int = 50) -> List[AnomalyAlert]:
        with self._lock:
            items = list(self._anomalies.values())
            if player_id is not None:
                items = [a for a in items if a.player_id == player_id]
            if status is not None:
                items = [a for a in items if a.status == status]
            if severity is not None:
                items = [a for a in items if a.severity == severity]
            return items[-limit:]

    def confirm_anomaly(self, alert_id: str) -> Optional[AnomalyAlert]:
        with self._lock:
            alert = self._anomalies.get(alert_id)
            if alert is None or alert.status != AlertStatus.OPEN:
                return None
            alert.status = AlertStatus.CONFIRMED
            alert.resolved_at = _now()
            player = self._players.get(alert.player_id)
            if player:
                player.confirmed_violations += 1
                self._recalc_risk(player)
            self._emit(AntiCheatEventKind.ANOMALY_CONFIRMED, {"alert_id": alert_id})
            return alert

    def dismiss_anomaly(self, alert_id: str) -> Optional[AnomalyAlert]:
        with self._lock:
            alert = self._anomalies.get(alert_id)
            if alert is None or alert.status != AlertStatus.OPEN:
                return None
            alert.status = AlertStatus.FALSE_POSITIVE
            alert.resolved_at = _now()
            self._emit(AntiCheatEventKind.ANOMALY_DISMISSED, {"alert_id": alert_id})
            return alert

    # ------------------------------------------------------------------
    # Investigation Workflow
    # ------------------------------------------------------------------

    def open_investigation(self, player_id: str, alert_ids: List[str] = None,
                           assigned_to: str = "ai_director") -> Optional[Investigation]:
        with self._lock:
            if player_id not in self._players:
                return None
            investigation = Investigation(
                investigation_id=_new_id("inv"),
                player_id=player_id,
                alert_ids=alert_ids or [],
                assigned_to=assigned_to,
            )
            self._investigations[investigation.investigation_id] = investigation
            _evict_fifo_dict(self._investigations, _MAX_INVESTIGATIONS)
            for aid in (alert_ids or []):
                alert = self._anomalies.get(aid)
                if alert:
                    alert.status = AlertStatus.INVESTIGATING
                    alert.investigation_id = investigation.investigation_id
            self._emit(AntiCheatEventKind.INVESTIGATION_OPENED, {
                "investigation_id": investigation.investigation_id,
                "player_id": player_id,
            })
            return investigation

    def update_investigation(self, investigation_id: str, updates: Dict[str, Any]) -> Optional[Investigation]:
        with self._lock:
            inv = self._investigations.get(investigation_id)
            if inv is None:
                return None
            for k, v in updates.items():
                if k == "status" and isinstance(v, str):
                    try:
                        v = InvestigationStatus(v)
                    except ValueError:
                        continue
                if k == "verdict" and isinstance(v, str):
                    try:
                        v = AlertStatus(v)
                    except ValueError:
                        continue
                if hasattr(inv, k) and k not in ("investigation_id", "player_id", "opened_at"):
                    setattr(inv, k, v)
            inv.updated_at = _now()
            self._emit(AntiCheatEventKind.INVESTIGATION_UPDATED, {
                "investigation_id": investigation_id,
            })
            return inv

    def close_investigation(self, investigation_id: str, conclusion: str = "",
                            verdict: AlertStatus = AlertStatus.CONFIRMED) -> Optional[Investigation]:
        with self._lock:
            inv = self._investigations.get(investigation_id)
            if inv is None:
                return None
            inv.status = InvestigationStatus.CONCLUDED
            inv.conclusion = conclusion
            inv.verdict = verdict
            inv.concluded_at = _now()
            inv.updated_at = _now()
            for aid in inv.alert_ids:
                alert = self._anomalies.get(aid)
                if alert and alert.status == AlertStatus.INVESTIGATING:
                    alert.status = verdict
                    alert.resolved_at = _now()
            self._emit(AntiCheatEventKind.INVESTIGATION_CONCLUDED, {
                "investigation_id": investigation_id,
                "verdict": verdict.value,
            })
            return inv

    def list_investigations(self, player_id: str = None,
                            status: InvestigationStatus = None,
                            limit: int = 50) -> List[Investigation]:
        with self._lock:
            items = list(self._investigations.values())
            if player_id is not None:
                items = [i for i in items if i.player_id == player_id]
            if status is not None:
                items = [i for i in items if i.status == status]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Enforcement Actions
    # ------------------------------------------------------------------

    def apply_enforcement(self, player_id: str, enforcement_type: EnforcementType,
                          reason: str = "", investigation_id: str = "",
                          alert_id: str = "", duration_hours: int = 0,
                          metadata: Dict[str, Any] = None) -> Optional[EnforcementAction]:
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                return None
            enforcement = EnforcementAction(
                enforcement_id=_new_id("enf"),
                player_id=player_id,
                enforcement_type=enforcement_type,
                reason=reason,
                investigation_id=investigation_id,
                alert_id=alert_id,
                duration_hours=duration_hours,
                metadata=metadata or {},
            )
            self._enforcements[enforcement.enforcement_id] = enforcement
            _evict_fifo_dict(self._enforcements, _MAX_ENFORCEMENTS)
            player.active_enforcements += 1
            player.last_enforcement_at = _now()
            if enforcement_type == EnforcementType.SOFT_SHADOWBAN:
                player.is_shadowbanned = True
            elif enforcement_type == EnforcementType.PERMANENT_BAN:
                player.is_banned = True
            self._recalc_risk(player)
            self._emit(AntiCheatEventKind.ENFORCEMENT_APPLIED, {
                "enforcement_id": enforcement.enforcement_id,
                "player_id": player_id,
                "enforcement_type": enforcement_type.value,
            })
            return enforcement

    def revoke_enforcement(self, enforcement_id: str, revoked_reason: str = "") -> Optional[EnforcementAction]:
        with self._lock:
            enforcement = self._enforcements.get(enforcement_id)
            if enforcement is None or not enforcement.is_active:
                return None
            enforcement.is_active = False
            enforcement.revoked_at = _now()
            enforcement.revoked_reason = revoked_reason
            player = self._players.get(enforcement.player_id)
            if player:
                player.active_enforcements = max(0, player.active_enforcements - 1)
                if enforcement.enforcement_type == EnforcementType.SOFT_SHADOWBAN:
                    player.is_shadowbanned = False
                elif enforcement.enforcement_type == EnforcementType.PERMANENT_BAN:
                    player.is_banned = False
                self._recalc_risk(player)
            self._emit(AntiCheatEventKind.ENFORCEMENT_REVOKED, {
                "enforcement_id": enforcement_id,
            })
            return enforcement

    def list_enforcements(self, player_id: str = None,
                          enforcement_type: EnforcementType = None,
                          is_active: bool = None,
                          limit: int = 50) -> List[EnforcementAction]:
        with self._lock:
            items = list(self._enforcements.values())
            if player_id is not None:
                items = [e for e in items if e.player_id == player_id]
            if enforcement_type is not None:
                items = [e for e in items if e.enforcement_type == enforcement_type]
            if is_active is not None:
                items = [e for e in items if e.is_active == is_active]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Appeal Workflow
    # ------------------------------------------------------------------

    def file_appeal(self, player_id: str, enforcement_id: str,
                    reason: str = "", player_statement: str = "") -> Optional[AppealCase]:
        with self._lock:
            enforcement = self._enforcements.get(enforcement_id)
            if enforcement is None or enforcement.player_id != player_id:
                return None
            appeal = AppealCase(
                appeal_id=_new_id("apl"),
                player_id=player_id,
                enforcement_id=enforcement_id,
                reason=reason,
                player_statement=player_statement,
            )
            self._appeals[appeal.appeal_id] = appeal
            _evict_fifo_dict(self._appeals, _MAX_APPEALS)
            self._emit(AntiCheatEventKind.APPEAL_FILED, {
                "appeal_id": appeal.appeal_id,
                "player_id": player_id,
            })
            return appeal

    def review_appeal(self, appeal_id: str, reviewer: str = "",
                      review_notes: str = "") -> Optional[AppealCase]:
        with self._lock:
            appeal = self._appeals.get(appeal_id)
            if appeal is None or appeal.status != AppealStatus.FILED:
                return None
            appeal.status = AppealStatus.UNDER_REVIEW
            appeal.reviewer = reviewer
            appeal.review_notes = review_notes
            appeal.reviewed_at = _now()
            self._emit(AntiCheatEventKind.APPEAL_REVIEWED, {"appeal_id": appeal_id})
            return appeal

    def resolve_appeal(self, appeal_id: str, approved: bool,
                       resolution: str = "") -> Optional[AppealCase]:
        with self._lock:
            appeal = self._appeals.get(appeal_id)
            if appeal is None or appeal.status != AppealStatus.UNDER_REVIEW:
                return None
            appeal.status = AppealStatus.APPROVED if approved else AppealStatus.DENIED
            appeal.resolution = resolution
            appeal.resolved_at = _now()
            if approved:
                self.revoke_enforcement(appeal.enforcement_id, "Appeal approved")
            self._emit(AntiCheatEventKind.APPEAL_RESOLVED, {
                "appeal_id": appeal_id,
                "approved": approved,
            })
            return appeal

    def list_appeals(self, player_id: str = None, status: AppealStatus = None,
                     limit: int = 50) -> List[AppealCase]:
        with self._lock:
            items = list(self._appeals.values())
            if player_id is not None:
                items = [a for a in items if a.player_id == player_id]
            if status is not None:
                items = [a for a in items if a.status == status]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, kind: AntiCheatEventKind = None, limit: int = 100) -> List[AntiCheatEvent]:
        with self._lock:
            items = list(self._events)
            if kind is not None:
                items = [e for e in items if e.kind == kind]
            return items[-limit:]

    def get_stats(self) -> AntiCheatStats:
        with self._lock:
            flagged = sum(1 for p in self._players.values()
                          if p.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL))
            banned = sum(1 for p in self._players.values() if p.is_banned)
            behavior_count = sum(len(s) for s in self._behavior.values())
            open_anom = sum(1 for a in self._anomalies.values() if a.status == AlertStatus.OPEN)
            confirmed = sum(1 for a in self._anomalies.values() if a.status == AlertStatus.CONFIRMED)
            open_inv = sum(1 for i in self._investigations.values()
                           if i.status in (InvestigationStatus.OPEN, InvestigationStatus.EVIDENCE_GATHERING,
                                           InvestigationStatus.PENDING_REVIEW))
            active_enf = sum(1 for e in self._enforcements.values() if e.is_active)
            pending_appeals = sum(1 for a in self._appeals.values()
                                  if a.status in (AppealStatus.FILED, AppealStatus.UNDER_REVIEW))
            return AntiCheatStats(
                total_players=len(self._players),
                flagged_players=flagged,
                banned_players=banned,
                total_behavior_samples=behavior_count,
                total_anomalies=len(self._anomalies),
                open_anomalies=open_anom,
                confirmed_anomalies=confirmed,
                total_investigations=len(self._investigations),
                open_investigations=open_inv,
                total_enforcements=len(self._enforcements),
                active_enforcements=active_enf,
                total_appeals=len(self._appeals),
                pending_appeals=pending_appeals,
                total_events=len(self._events),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "players": len(self._players),
                "behavior_samples": sum(len(s) for s in self._behavior.values()),
                "anomalies": len(self._anomalies),
                "investigations": len(self._investigations),
                "enforcements": len(self._enforcements),
                "appeals": len(self._appeals),
                "events": len(self._events),
            }

    def get_snapshot(self) -> AntiCheatSnapshot:
        with self._lock:
            return AntiCheatSnapshot(
                players=[p.to_dict() for p in list(self._players.values())[:20]],
                anomalies=[a.to_dict() for a in list(self._anomalies.values())[:20]],
                investigations=[i.to_dict() for i in list(self._investigations.values())[:20]],
                enforcements=[e.to_dict() for e in list(self._enforcements.values())[:20]],
                appeals=[a.to_dict() for a in list(self._appeals.values())[:20]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._players.clear()
            self._behavior.clear()
            self._anomalies.clear()
            self._investigations.clear()
            self._enforcements.clear()
            self._appeals.clear()
            self._events.clear()
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        legit = PlayerProfile(
            player_id="player_clean_1",
            display_name="FairPlayer",
            account_created="2025-01-15T00:00:00Z",
        )
        self._players[legit.player_id] = legit

        suspicious = PlayerProfile(
            player_id="player_suspicious_1",
            display_name="SpeedDemon",
            account_created="2025-06-01T00:00:00Z",
            risk_level=RiskLevel.LOW,
            risk_score=0.25,
            total_anomalies=1,
        )
        self._players[suspicious.player_id] = suspicious

        banned = PlayerProfile(
            player_id="player_banned_1",
            display_name="AimBotKing",
            account_created="2025-03-01T00:00:00Z",
            risk_level=RiskLevel.CRITICAL,
            risk_score=1.0,
            total_anomalies=5,
            confirmed_violations=3,
            active_enforcements=1,
            is_banned=True,
        )
        self._players[banned.player_id] = banned

        self._behavior["player_suspicious_1"] = [
            BehaviorSample(
                sample_id=_new_id("beh"),
                player_id="player_suspicious_1",
                category=BehaviorCategory.MOVEMENT,
                metric="move_speed",
                value=15.0,
                baseline_value=8.0,
                deviation=0.875,
                session_id="sess_001",
            ),
            BehaviorSample(
                sample_id=_new_id("beh"),
                player_id="player_suspicious_1",
                category=BehaviorCategory.COMBAT,
                metric="aim_accuracy",
                value=0.98,
                baseline_value=0.45,
                deviation=1.178,
                session_id="sess_001",
            ),
        ]

        self._enforcements["enf_seed_ban"] = EnforcementAction(
            enforcement_id="enf_seed_ban",
            player_id="player_banned_1",
            enforcement_type=EnforcementType.PERMANENT_BAN,
            reason="Confirmed aimbot usage across multiple sessions",
            is_active=True,
        )
        self._players["player_banned_1"].active_enforcements = 1


def get_anti_cheat_director() -> AntiCheatDirector:
    """Factory function returning the singleton AntiCheatDirector instance."""
    return AntiCheatDirector.get_instance()
