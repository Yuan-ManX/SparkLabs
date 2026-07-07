"""
Agent Retention Predictor

AI-driven churn prediction and retention strategy engine. Fills the player
retention gap by combining engagement signals (recency, frequency, duration,
progression, social, monetary) into a unified churn risk score and recommending
personalized retention actions.

Distinct from agent_player_modeler (which models playstyle and skill) and
agent_liveops_director (which schedules live events): this module focuses
specifically on predicting churn and prescribing targeted interventions.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity constants
# ---------------------------------------------------------------------------
_MAX_PLAYERS = 20000
_MAX_SESSIONS = 100000
_MAX_ACTIONS = 5000
_MAX_CAMPAIGNS = 500
_MAX_SEGMENTS = 200
_MAX_EVENTS = 5000

# Scoring weights (must sum to 1.0)
_RECENCY_WEIGHT = 0.30
_FREQUENCY_WEIGHT = 0.20
_DURATION_WEIGHT = 0.15
_PROGRESSION_WEIGHT = 0.15
_SOCIAL_WEIGHT = 0.10
_MONETARY_WEIGHT = 0.10

# Thresholds
_RECENCY_HALF_LIFE_DAYS = 7.0      # recency factor halves every 7 days
_FREQUENCY_NORMALIZER = 7.0        # 7 sessions/week = max frequency factor
_DURATION_NORMALIZER = 120.0       # 120 min sessions = max duration factor
_CHURN_RISK_HIGH = 0.65
_CHURN_RISK_MEDIUM = 0.40
_CHURN_RISK_LOW = 0.20

# Session window for churn evaluation
_SESSION_WINDOW_DAYS = 30


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _now_seconds() -> float:
    return time.time()


def _days_between(t1: float, t2: float) -> float:
    return abs(t1 - t2) / 86400.0


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    if len(store) <= max_size:
        return
    overflow = len(store) - max_size
    keys = list(store.keys())[:overflow]
    for k in keys:
        store.pop(k, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    if len(store) <= max_size:
        return
    overflow = len(store) - max_size
    del store[:overflow]


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_dataclass_to_dict(v) for v in obj]
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class RiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SegmentKind:
    NEW = "new"
    ACTIVE = "active"
    DORMANT = "dormant"
    CHURNED = "churned"
    RETURNED = "returned"
    WHALE = "whale"
    DOLPHIN = "dolphin"
    MINNOW = "minnow"


class ActionKind:
    PUSH_NOTIFICATION = "push_notification"
    EMAIL = "email"
    IN_GAME_REWARD = "in_game_reward"
    DISCOUNT = "discount"
    PERSONAL_OFFER = "personal_offer"
    TUTORIAL_HINT = "tutorial_hint"
    SOCIAL_NUDGE = "social_nudge"
    CONTENT_UNLOCK = "content_unlock"


class CampaignStatus:
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RetentionEventKind:
    PLAYER_REGISTERED = "player_registered"
    PLAYER_REMOVED = "player_removed"
    SESSION_RECORDED = "session_recorded"
    CHURN_PREDICTED = "churn_predicted"
    PLAYER_SEGMENTED = "player_segmented"
    ACTION_RECOMMENDED = "action_recommended"
    CAMPAIGN_CREATED = "campaign_created"
    CAMPAIGN_ACTIVATED = "campaign_activated"
    CAMPAIGN_PAUSED = "campaign_paused"
    CAMPAIGN_COMPLETED = "campaign_completed"
    CAMPAIGN_REMOVED = "campaign_removed"
    TICK_PROCESSED = "tick_processed"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class SessionRecord:
    session_id: str
    player_id: str
    started_at: float
    duration_minutes: float
    events_count: int = 0
    progress_delta: float = 0.0
    social_interactions: int = 0
    monetization_cents: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "player_id": self.player_id,
            "started_at": self.started_at,
            "duration_minutes": self.duration_minutes,
            "events_count": self.events_count,
            "progress_delta": self.progress_delta,
            "social_interactions": self.social_interactions,
            "monetization_cents": self.monetization_cents,
        }


@dataclass
class PlayerEngagementProfile:
    player_id: str
    display_name: str
    region: str = "global"
    registered_at: float = field(default_factory=_now_seconds)
    last_active_at: float = field(default_factory=_now_seconds)
    total_sessions: int = 0
    total_playtime_minutes: float = 0.0
    total_events: int = 0
    total_social_interactions: int = 0
    total_monetization_cents: int = 0
    progression_level: float = 0.0     # 0..1
    days_since_register: float = 0.0
    is_veteran: bool = False
    sessions: List[str] = field(default_factory=list)   # session ids, most recent last

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "region": self.region,
            "registered_at": self.registered_at,
            "last_active_at": self.last_active_at,
            "total_sessions": self.total_sessions,
            "total_playtime_minutes": self.total_playtime_minutes,
            "total_events": self.total_events,
            "total_social_interactions": self.total_social_interactions,
            "total_monetization_cents": self.total_monetization_cents,
            "progression_level": self.progression_level,
            "days_since_register": self.days_since_register,
            "is_veteran": self.is_veteran,
            "sessions": list(self.sessions),
        }


@dataclass
class ChurnRiskScore:
    player_id: str
    risk_score: float                   # 0..1, higher = more likely to churn
    risk_level: str                     # RiskLevel value
    recency_factor: float
    frequency_factor: float
    duration_factor: float
    progression_factor: float
    social_factor: float
    monetary_factor: float
    predicted_at: float
    contributing_factors: List[str] = field(default_factory=list)
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "risk_score": round(self.risk_score, 4),
            "risk_level": self.risk_level,
            "recency_factor": round(self.recency_factor, 4),
            "frequency_factor": round(self.frequency_factor, 4),
            "duration_factor": round(self.duration_factor, 4),
            "progression_factor": round(self.progression_factor, 4),
            "social_factor": round(self.social_factor, 4),
            "monetary_factor": round(self.monetary_factor, 4),
            "predicted_at": self.predicted_at,
            "contributing_factors": list(self.contributing_factors),
            "confidence": round(self.confidence, 4),
        }


@dataclass
class RetentionAction:
    action_id: str
    player_id: str
    action_kind: str                    # ActionKind value
    title: str
    description: str
    priority: float                     # 0..1
    estimated_uplift: float             # 0..1
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now_seconds)
    expires_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "player_id": self.player_id,
            "action_kind": self.action_kind,
            "title": self.title,
            "description": self.description,
            "priority": round(self.priority, 4),
            "estimated_uplift": round(self.estimated_uplift, 4),
            "payload": dict(self.payload),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


@dataclass
class RetentionCampaign:
    campaign_id: str
    name: str
    description: str
    status: str                         # CampaignStatus value
    target_segment: str                 # SegmentKind value
    action_kind: str                    # ActionKind value
    target_player_ids: List[str] = field(default_factory=list)
    started_at: float = 0.0
    ends_at: float = 0.0
    budget_cents: int = 0
    spent_cents: int = 0
    reach_count: int = 0
    conversion_count: int = 0
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "target_segment": self.target_segment,
            "action_kind": self.action_kind,
            "target_player_ids": list(self.target_player_ids),
            "started_at": self.started_at,
            "ends_at": self.ends_at,
            "budget_cents": self.budget_cents,
            "spent_cents": self.spent_cents,
            "reach_count": self.reach_count,
            "conversion_count": self.conversion_count,
            "payload": dict(self.payload),
        }


@dataclass
class RetentionConfig:
    churn_high_threshold: float = _CHURN_RISK_HIGH
    churn_medium_threshold: float = _CHURN_RISK_MEDIUM
    churn_low_threshold: float = _CHURN_RISK_LOW
    recency_half_life_days: float = _RECENCY_HALF_LIFE_DAYS
    session_window_days: int = _SESSION_WINDOW_DAYS
    auto_segment: bool = True
    auto_recommend: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "churn_high_threshold": self.churn_high_threshold,
            "churn_medium_threshold": self.churn_medium_threshold,
            "churn_low_threshold": self.churn_low_threshold,
            "recency_half_life_days": self.recency_half_life_days,
            "session_window_days": self.session_window_days,
            "auto_segment": self.auto_segment,
            "auto_recommend": self.auto_recommend,
        }


@dataclass
class RetentionStats:
    total_players: int = 0
    total_sessions: int = 0
    total_campaigns: int = 0
    active_campaigns: int = 0
    predictions_made: int = 0
    actions_recommended: int = 0
    avg_risk_score: float = 0.0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    critical_risk_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_players": self.total_players,
            "total_sessions": self.total_sessions,
            "total_campaigns": self.total_campaigns,
            "active_campaigns": self.active_campaigns,
            "predictions_made": self.predictions_made,
            "actions_recommended": self.actions_recommended,
            "avg_risk_score": round(self.avg_risk_score, 4),
            "high_risk_count": self.high_risk_count,
            "medium_risk_count": self.medium_risk_count,
            "low_risk_count": self.low_risk_count,
            "critical_risk_count": self.critical_risk_count,
        }


@dataclass
class RetentionSnapshot:
    captured_at: float
    players: int
    sessions: int
    campaigns: int
    active_campaigns: int
    avg_risk: float
    segment_distribution: Dict[str, int]
    top_actions: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "captured_at": self.captured_at,
            "players": self.players,
            "sessions": self.sessions,
            "campaigns": self.campaigns,
            "active_campaigns": self.active_campaigns,
            "avg_risk": round(self.avg_risk, 4),
            "segment_distribution": dict(self.segment_distribution),
            "top_actions": list(self.top_actions),
        }


@dataclass
class RetentionEvent:
    event_id: str
    kind: str                           # RetentionEventKind value
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }


# ---------------------------------------------------------------------------
# Singleton engine
# ---------------------------------------------------------------------------
class RetentionPredictor:
    """AI-driven churn prediction and retention strategy engine."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        self._players: Dict[str, PlayerEngagementProfile] = {}
        self._sessions: Dict[str, SessionRecord] = {}
        self._player_sessions: Dict[str, List[str]] = {}     # player_id -> [session_id]
        self._predictions: Dict[str, ChurnRiskScore] = {}    # player_id -> latest
        self._segments: Dict[str, str] = {}                  # player_id -> SegmentKind
        self._actions: Dict[str, RetentionAction] = {}
        self._player_actions: Dict[str, List[str]] = {}      # player_id -> [action_id]
        self._campaigns: Dict[str, RetentionCampaign] = {}
        self._config = RetentionConfig()
        self._events: List[RetentionEvent] = []
        self._stats = RetentionStats()
        self._tick_count: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed()
            self._initialized = True

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._players.clear()
            self._sessions.clear()
            self._player_sessions.clear()
            self._predictions.clear()
            self._segments.clear()
            self._actions.clear()
            self._player_actions.clear()
            self._campaigns.clear()
            self._events.clear()
            self._stats = RetentionStats()
            self._tick_count = 0
            self._config = RetentionConfig()
            self._initialized = False
            self.initialize()
            return {"status": "ok", "reset": True, "players": len(self._players)}

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "players": len(self._players),
                "sessions": len(self._sessions),
                "predictions": len(self._predictions),
                "actions": len(self._actions),
                "campaigns": len(self._campaigns),
                "active_campaigns": sum(
                    1 for c in self._campaigns.values() if c.status == CampaignStatus.ACTIVE
                ),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            segment_dist: Dict[str, int] = {}
            for seg in self._segments.values():
                segment_dist[seg] = segment_dist.get(seg, 0) + 1
            top_actions = [
                a.to_dict() for a in list(self._actions.values())[:5]
            ]
            avg_risk = 0.0
            if self._predictions:
                avg_risk = sum(p.risk_score for p in self._predictions.values()) / len(self._predictions)
            snap = RetentionSnapshot(
                captured_at=_now_seconds(),
                players=len(self._players),
                sessions=len(self._sessions),
                campaigns=len(self._campaigns),
                active_campaigns=sum(
                    1 for c in self._campaigns.values() if c.status == CampaignStatus.ACTIVE
                ),
                avg_risk=avg_risk,
                segment_distribution=segment_dist,
                top_actions=top_actions,
            )
            return snap.to_dict()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._stats.total_players = len(self._players)
            self._stats.total_sessions = len(self._sessions)
            self._stats.total_campaigns = len(self._campaigns)
            self._stats.active_campaigns = sum(
                1 for c in self._campaigns.values() if c.status == CampaignStatus.ACTIVE
            )
            self._stats.predictions_made = len(self._predictions)
            self._stats.actions_recommended = len(self._actions)
            if self._predictions:
                self._stats.avg_risk_score = sum(
                    p.risk_score for p in self._predictions.values()
                ) / len(self._predictions)
                self._stats.high_risk_count = sum(
                    1 for p in self._predictions.values() if p.risk_level == RiskLevel.HIGH
                )
                self._stats.medium_risk_count = sum(
                    1 for p in self._predictions.values() if p.risk_level == RiskLevel.MEDIUM
                )
                self._stats.low_risk_count = sum(
                    1 for p in self._predictions.values() if p.risk_level == RiskLevel.LOW
                )
                self._stats.critical_risk_count = sum(
                    1 for p in self._predictions.values() if p.risk_level == RiskLevel.CRITICAL
                )
            return self._stats.to_dict()

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------
    def _log_event(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> None:
        evt = RetentionEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            kind=kind,
            timestamp=_now_seconds(),
            payload=payload or {},
        )
        self._events.append(evt)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, limit: int = 50, kind: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            limit = max(1, min(_safe_int(limit, 50), 500))
            events = self._events
            if kind:
                events = [e for e in events if e.kind == kind]
            sliced = events[-limit:]
            return {
                "events": [e.to_dict() for e in sliced],
                "total": len(self._events),
                "returned": len(sliced),
            }

    # ------------------------------------------------------------------
    # Player management
    # ------------------------------------------------------------------
    def register_player(
        self,
        player_id: str,
        display_name: str,
        region: str = "global",
        registered_at: Optional[float] = None,
        progression_level: float = 0.0,
    ) -> Dict[str, Any]:
        with self._lock:
            if not player_id:
                return {"status": "error", "error": "player_id required"}
            if player_id in self._players:
                return {"status": "error", "error": "player already exists"}
            now = _now_seconds()
            profile = PlayerEngagementProfile(
                player_id=player_id,
                display_name=display_name or player_id,
                region=region or "global",
                registered_at=registered_at if registered_at else now,
                last_active_at=now,
                progression_level=_clamp(_safe_float(progression_level, 0.0)),
            )
            profile.days_since_register = _days_between(now, profile.registered_at)
            self._players[player_id] = profile
            self._player_sessions[player_id] = []
            self._player_actions[player_id] = []
            _evict_fifo_dict(self._players, _MAX_PLAYERS)
            self._log_event(RetentionEventKind.PLAYER_REGISTERED, {"player_id": player_id})
            return {"status": "ok", "player": profile.to_dict()}

    def get_player(self, player_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            p = self._players.get(player_id)
            if not p:
                return None
            return p.to_dict()

    def list_players(
        self,
        segment: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        with self._lock:
            limit = max(1, min(_safe_int(limit, 50), 500))
            offset = max(0, _safe_int(offset, 0))
            items = list(self._players.values())
            if segment:
                items = [p for p in items if self._segments.get(p.player_id) == segment]
            if region:
                items = [p for p in items if p.region == region]
            total = len(items)
            sliced = items[offset:offset + limit]
            return {
                "players": [p.to_dict() for p in sliced],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

    def remove_player(self, player_id: str) -> Dict[str, Any]:
        with self._lock:
            if player_id not in self._players:
                return {"status": "error", "error": "player not found", "found": False}
            self._players.pop(player_id, None)
            self._predictions.pop(player_id, None)
            self._segments.pop(player_id, None)
            session_ids = self._player_sessions.pop(player_id, [])
            for sid in session_ids:
                self._sessions.pop(sid, None)
            action_ids = self._player_actions.pop(player_id, [])
            for aid in action_ids:
                self._actions.pop(aid, None)
            self._log_event(RetentionEventKind.PLAYER_REMOVED, {"player_id": player_id})
            return {"status": "ok", "removed": True, "player_id": player_id}

    # ------------------------------------------------------------------
    # Session recording
    # ------------------------------------------------------------------
    def record_session(
        self,
        player_id: str,
        duration_minutes: float,
        events_count: int = 0,
        progress_delta: float = 0.0,
        social_interactions: int = 0,
        monetization_cents: int = 0,
        started_at: Optional[float] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            p = self._players.get(player_id)
            if not p:
                return {"status": "error", "error": "player not found", "found": False}
            now = _now_seconds()
            session = SessionRecord(
                session_id=f"ses_{uuid.uuid4().hex[:12]}",
                player_id=player_id,
                started_at=started_at if started_at else now,
                duration_minutes=max(0.0, _safe_float(duration_minutes, 0.0)),
                events_count=max(0, _safe_int(events_count, 0)),
                progress_delta=_safe_float(progress_delta, 0.0),
                social_interactions=max(0, _safe_int(social_interactions, 0)),
                monetization_cents=max(0, _safe_int(monetization_cents, 0)),
            )
            self._sessions[session.session_id] = session
            _evict_fifo_dict(self._sessions, _MAX_SESSIONS)
            self._player_sessions.setdefault(player_id, []).append(session.session_id)
            _evict_fifo_list(self._player_sessions[player_id], _SESSION_WINDOW_DAYS * 4)

            # Update player profile aggregates
            p.total_sessions += 1
            p.total_playtime_minutes += session.duration_minutes
            p.total_events += session.events_count
            p.total_social_interactions += session.social_interactions
            p.total_monetization_cents += session.monetization_cents
            p.last_active_at = session.started_at
            p.progression_level = _clamp(p.progression_level + session.progress_delta)
            p.days_since_register = _days_between(now, p.registered_at)
            p.is_veteran = p.days_since_register >= 30.0
            p.sessions.append(session.session_id)
            _evict_fifo_list(p.sessions, 100)

            self._log_event(
                RetentionEventKind.SESSION_RECORDED,
                {"player_id": player_id, "session_id": session.session_id},
            )
            return {"status": "ok", "session": session.to_dict()}

    def get_session_history(self, player_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._lock:
            if player_id not in self._players:
                return {"status": "error", "error": "player not found", "found": False}
            limit = max(1, min(_safe_int(limit, 20), 200))
            ids = self._player_sessions.get(player_id, [])[-limit:]
            sessions = [self._sessions[sid].to_dict() for sid in ids if sid in self._sessions]
            return {
                "player_id": player_id,
                "sessions": sessions,
                "count": len(sessions),
            }

    # ------------------------------------------------------------------
    # Churn prediction
    # ------------------------------------------------------------------
    def _compute_factors(self, profile: PlayerEngagementProfile) -> Tuple[
        float, float, float, float, float, float, List[str]
    ]:
        now = _now_seconds()
        # Recency: exponential decay with half-life
        days_inactive = _days_between(now, profile.last_active_at)
        if days_inactive <= 0:
            recency = 1.0
        else:
            recency = 0.5 ** (days_inactive / max(0.1, self._config.recency_half_life_days))
        recency = _clamp(recency)

        # Frequency: sessions per week over the session window
        window_seconds = self._config.session_window_days * 86400.0
        recent_session_count = 0
        for sid in profile.sessions:
            s = self._sessions.get(sid)
            if s and (now - s.started_at) <= window_seconds:
                recent_session_count += 1
        frequency = _clamp(recent_session_count / _FREQUENCY_NORMALIZER)

        # Duration: average session length over recent window
        recent_durations: List[float] = []
        for sid in profile.sessions:
            s = self._sessions.get(sid)
            if s and (now - s.started_at) <= window_seconds:
                recent_durations.append(s.duration_minutes)
        avg_duration = (
            sum(recent_durations) / len(recent_durations)
            if recent_durations
            else 0.0
        )
        duration = _clamp(avg_duration / _DURATION_NORMALIZER)

        # Progression: stored level
        progression = _clamp(profile.progression_level)

        # Social: social interactions per session
        social_per_session = (
            profile.total_social_interactions / max(1, profile.total_sessions)
        )
        social = _clamp(social_per_session / 10.0)

        # Monetary: spending level
        monetary = _clamp(profile.total_monetization_cents / 10000.0)

        # Contributing factors (top decline drivers)
        contributing: List[str] = []
        factor_map = [
            ("recency", recency),
            ("frequency", frequency),
            ("duration", duration),
            ("progression", progression),
            ("social", social),
            ("monetary", monetary),
        ]
        sorted_factors = sorted(factor_map, key=lambda x: x[1])
        for name, val in sorted_factors[:3]:
            if val < 0.4:
                contributing.append(name)

        return recency, frequency, duration, progression, social, monetary, contributing

    def predict_churn(self, player_id: str) -> Dict[str, Any]:
        with self._lock:
            p = self._players.get(player_id)
            if not p:
                return {"status": "error", "error": "player not found", "found": False}
            recency, frequency, duration, progression, social, monetary, contributing = (
                self._compute_factors(p)
            )
            engagement = (
                recency * _RECENCY_WEIGHT
                + frequency * _FREQUENCY_WEIGHT
                + duration * _DURATION_WEIGHT
                + progression * _PROGRESSION_WEIGHT
                + social * _SOCIAL_WEIGHT
                + monetary * _MONETARY_WEIGHT
            )
            risk_score = _clamp(1.0 - engagement)

            # Determine risk level
            if risk_score >= self._config.churn_high_threshold:
                risk_level = RiskLevel.HIGH
            elif risk_score >= self._config.churn_medium_threshold:
                risk_level = RiskLevel.MEDIUM
            elif risk_score >= self._config.churn_low_threshold:
                risk_level = RiskLevel.LOW
            else:
                risk_level = RiskLevel.LOW

            # Critical if very high or veteran with rising risk
            if risk_score >= 0.85:
                risk_level = RiskLevel.CRITICAL

            confidence = _clamp(
                0.5
                + min(0.3, p.total_sessions / 50.0)
                + min(0.2, p.days_since_register / 60.0)
            )

            score = ChurnRiskScore(
                player_id=player_id,
                risk_score=risk_score,
                risk_level=risk_level,
                recency_factor=recency,
                frequency_factor=frequency,
                duration_factor=duration,
                progression_factor=progression,
                social_factor=social,
                monetary_factor=monetary,
                predicted_at=_now_seconds(),
                contributing_factors=contributing,
                confidence=confidence,
            )
            self._predictions[player_id] = score

            # Auto-segment if enabled
            if self._config.auto_segment:
                self._segment_player_internal(p, score)

            self._log_event(
                RetentionEventKind.CHURN_PREDICTED,
                {"player_id": player_id, "risk_score": round(risk_score, 4), "risk_level": risk_level},
            )
            return {"status": "ok", "prediction": score.to_dict()}

    def _segment_player_internal(
        self, profile: PlayerEngagementProfile, score: ChurnRiskScore
    ) -> str:
        # Whale/Dolphin/Minnow by monetization
        spend_cents = profile.total_monetization_cents
        if spend_cents >= 5000:        # $50+
            seg = SegmentKind.WHALE
        elif spend_cents >= 1000:      # $10-$50
            seg = SegmentKind.DOLPHIN
        elif spend_cents > 0:
            seg = SegmentKind.MINNOW
        else:
            # No spend - segment by activity
            now = _now_seconds()
            days_inactive = _days_between(now, profile.last_active_at)
            if profile.days_since_register < 7.0:
                seg = SegmentKind.NEW
            elif days_inactive > 14.0:
                if score.risk_score >= 0.8:
                    seg = SegmentKind.CHURNED
                else:
                    seg = SegmentKind.DORMANT
            elif days_inactive > 7.0 and score.risk_score < 0.4:
                seg = SegmentKind.RETURNED
            else:
                seg = SegmentKind.ACTIVE
        self._segments[profile.player_id] = seg
        return seg

    def segment_players(self, segment: Optional[str] = None) -> Dict[str, Any]:
        """Segment all players and return distribution."""
        with self._lock:
            distribution: Dict[str, int] = {}
            for pid, p in self._players.items():
                score = self._predictions.get(pid)
                if not score:
                    # Compute on the fly without storing
                    recency, frequency, duration, progression, social, monetary, _ = (
                        self._compute_factors(p)
                    )
                    engagement = (
                        recency * _RECENCY_WEIGHT
                        + frequency * _FREQUENCY_WEIGHT
                        + duration * _DURATION_WEIGHT
                        + progression * _PROGRESSION_WEIGHT
                        + social * _SOCIAL_WEIGHT
                        + monetary * _MONETARY_WEIGHT
                    )
                    risk_score = _clamp(1.0 - engagement)
                    score = ChurnRiskScore(
                        player_id=pid,
                        risk_score=risk_score,
                        risk_level=RiskLevel.LOW,
                        recency_factor=recency,
                        frequency_factor=frequency,
                        duration_factor=duration,
                        progression_factor=progression,
                        social_factor=social,
                        monetary_factor=monetary,
                        predicted_at=_now_seconds(),
                    )
                seg = self._segment_player_internal(p, score)
                distribution[seg] = distribution.get(seg, 0) + 1
            self._log_event(
                RetentionEventKind.PLAYER_SEGMENTED,
                {"distribution": distribution},
            )
            if segment:
                players_in_segment = [
                    pid for pid, s in self._segments.items() if s == segment
                ]
                return {
                    "status": "ok",
                    "distribution": distribution,
                    "segment": segment,
                    "player_ids": players_in_segment,
                    "count": len(players_in_segment),
                }
            return {"status": "ok", "distribution": distribution}

    # ------------------------------------------------------------------
    # Action recommendation
    # ------------------------------------------------------------------
    def recommend_action(self, player_id: str) -> Dict[str, Any]:
        with self._lock:
            p = self._players.get(player_id)
            if not p:
                return {"status": "error", "error": "player not found", "found": False}
            score = self._predictions.get(player_id)
            if not score:
                result = self.predict_churn(player_id)
                if result.get("status") != "ok":
                    return result
                score = self._predictions[player_id]

            seg = self._segments.get(player_id, SegmentKind.ACTIVE)
            action_kind, title, description, uplift, priority, payload = (
                self._choose_action(p, score, seg)
            )
            action = RetentionAction(
                action_id=f"act_{uuid.uuid4().hex[:12]}",
                player_id=player_id,
                action_kind=action_kind,
                title=title,
                description=description,
                priority=priority,
                estimated_uplift=uplift,
                payload=payload,
                expires_at=_now_seconds() + 86400.0,   # 24h validity
            )
            self._actions[action.action_id] = action
            self._player_actions.setdefault(player_id, []).append(action.action_id)
            _evict_fifo_dict(self._actions, _MAX_ACTIONS)
            _evict_fifo_list(self._player_actions[player_id], 50)

            self._log_event(
                RetentionEventKind.ACTION_RECOMMENDED,
                {"player_id": player_id, "action_id": action.action_id, "action_kind": action_kind},
            )
            return {"status": "ok", "action": action.to_dict()}

    def _choose_action(
        self,
        profile: PlayerEngagementProfile,
        score: ChurnRiskScore,
        segment: str,
    ) -> Tuple[str, str, str, float, float, Dict[str, Any]]:
        """Heuristic policy mapping risk + segment to action."""
        risk = score.risk_score
        contributing = set(score.contributing_factors)

        if segment == SegmentKind.WHALE and risk >= 0.5:
            return (
                ActionKind.PERSONAL_OFFER,
                "Personal VIP Offer",
                "Exclusive personalized offer for high-value player at risk of churning.",
                0.78,
                0.95,
                {"discount_pct": 25, "exclusive_item": "vip_skin_pack"},
            )
        if segment in (SegmentKind.WHALE, SegmentKind.DOLPHIN) and risk >= 0.4:
            return (
                ActionKind.DISCOUNT,
                "Targeted Discount",
                "Time-limited discount on premium content.",
                0.62,
                0.8,
                {"discount_pct": 15, "duration_hours": 48},
            )
        if "recency" in contributing and risk >= 0.6:
            return (
                ActionKind.PUSH_NOTIFICATION,
                "We Miss You Notification",
                "Push notification highlighting new content since last visit.",
                0.55,
                0.85,
                {"channel": "push", "message": "new_season_live"},
            )
        if "frequency" in contributing and risk >= 0.5:
            return (
                ActionKind.IN_GAME_REWARD,
                "Daily Login Bonus",
                "Boost daily login rewards to increase session frequency.",
                0.6,
                0.8,
                {"reward_type": "currency", "amount": 500},
            )
        if "duration" in contributing:
            return (
                ActionKind.CONTENT_UNLOCK,
                "Early Content Unlock",
                "Unlock content early to extend session duration.",
                0.5,
                0.7,
                {"content_id": "expansion_prologue"},
            )
        if "social" in contributing:
            return (
                ActionKind.SOCIAL_NUDGE,
                "Friend Activity Nudge",
                "Notify player about friend activity and squad opportunities.",
                0.52,
                0.65,
                {"channel": "social", "template": "friend_online"},
            )
        if "progression" in contributing:
            return (
                ActionKind.TUTORIAL_HINT,
                "Progression Hint",
                "Surface next-step hint to overcome progression stall.",
                0.48,
                0.6,
                {"hint_id": "next_objective"},
            )
        if segment == SegmentKind.NEW and risk >= 0.4:
            return (
                ActionKind.TUTORIAL_HINT,
                "Onboarding Tip",
                "Provide onboarding tip for new player showing churn signals.",
                0.55,
                0.7,
                {"hint_id": "first_victory"},
            )
        if segment == SegmentKind.CHURNED:
            return (
                ActionKind.EMAIL,
                "Win-Back Email",
                "Email campaign with return incentives for churned player.",
                0.4,
                0.6,
                {"channel": "email", "template": "winback_v1"},
            )
        # Default low-risk engagement
        return (
            ActionKind.IN_GAME_REWARD,
            "Engagement Booster",
            "Small reward to maintain engagement for low-risk player.",
            0.35,
            0.4,
            {"reward_type": "cosmetic", "amount": 1},
        )

    def list_actions(
        self, player_id: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        with self._lock:
            limit = max(1, min(_safe_int(limit, 50), 500))
            if player_id:
                ids = self._player_actions.get(player_id, [])[-limit:]
                actions = [self._actions[aid].to_dict() for aid in ids if aid in self._actions]
            else:
                actions = [a.to_dict() for a in list(self._actions.values())[-limit:]]
            return {"actions": actions, "count": len(actions)}

    # ------------------------------------------------------------------
    # Campaign management
    # ------------------------------------------------------------------
    def create_campaign(
        self,
        campaign_id: str,
        name: str,
        description: str,
        target_segment: str,
        action_kind: str,
        target_player_ids: Optional[List[str]] = None,
        budget_cents: int = 0,
        duration_hours: float = 24.0,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            if not campaign_id:
                return {"status": "error", "error": "campaign_id required"}
            if campaign_id in self._campaigns:
                return {"status": "error", "error": "campaign already exists"}
            now = _now_seconds()
            campaign = RetentionCampaign(
                campaign_id=campaign_id,
                name=name or campaign_id,
                description=description or "",
                status=CampaignStatus.DRAFT,
                target_segment=target_segment or SegmentKind.ACTIVE,
                action_kind=action_kind or ActionKind.IN_GAME_REWARD,
                target_player_ids=list(target_player_ids or []),
                started_at=0.0,
                ends_at=0.0,
                budget_cents=max(0, _safe_int(budget_cents, 0)),
                payload=payload or {},
            )
            # Resolve target players if not explicitly provided
            if not campaign.target_player_ids:
                campaign.target_player_ids = [
                    pid for pid, seg in self._segments.items()
                    if seg == campaign.target_segment
                ]
            self._campaigns[campaign_id] = campaign
            _evict_fifo_dict(self._campaigns, _MAX_CAMPAIGNS)
            self._log_event(
                RetentionEventKind.CAMPAIGN_CREATED,
                {"campaign_id": campaign_id, "target_segment": target_segment},
            )
            return {"status": "ok", "campaign": campaign.to_dict()}

    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            c = self._campaigns.get(campaign_id)
            if not c:
                return None
            return c.to_dict()

    def list_campaigns(
        self, status: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        with self._lock:
            limit = max(1, min(_safe_int(limit, 50), 500))
            items = list(self._campaigns.values())
            if status:
                items = [c for c in items if c.status == status]
            sliced = items[-limit:]
            return {
                "campaigns": [c.to_dict() for c in sliced],
                "count": len(sliced),
            }

    def update_campaign(
        self, campaign_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        with self._lock:
            c = self._campaigns.get(campaign_id)
            if not c:
                return {"status": "error", "error": "campaign not found", "found": False}
            if "name" in updates:
                c.name = str(updates["name"])
            if "description" in updates:
                c.description = str(updates["description"])
            if "budget_cents" in updates:
                c.budget_cents = max(0, _safe_int(updates["budget_cents"], 0))
            if "target_player_ids" in updates and isinstance(updates["target_player_ids"], list):
                c.target_player_ids = [str(x) for x in updates["target_player_ids"]]
            if "payload" in updates and isinstance(updates["payload"], dict):
                c.payload = dict(updates["payload"])
            return {"status": "ok", "campaign": c.to_dict()}

    def remove_campaign(self, campaign_id: str) -> Dict[str, Any]:
        with self._lock:
            if campaign_id not in self._campaigns:
                return {"status": "error", "error": "campaign not found", "found": False}
            self._campaigns.pop(campaign_id, None)
            self._log_event(
                RetentionEventKind.CAMPAIGN_REMOVED,
                {"campaign_id": campaign_id},
            )
            return {"status": "ok", "removed": True, "campaign_id": campaign_id}

    def activate_campaign(self, campaign_id: str) -> Dict[str, Any]:
        with self._lock:
            c = self._campaigns.get(campaign_id)
            if not c:
                return {"status": "error", "error": "campaign not found", "found": False}
            now = _now_seconds()
            c.status = CampaignStatus.ACTIVE
            c.started_at = now
            c.reach_count = len(c.target_player_ids)
            self._log_event(
                RetentionEventKind.CAMPAIGN_ACTIVATED,
                {"campaign_id": campaign_id, "reach": c.reach_count},
            )
            return {"status": "ok", "campaign": c.to_dict()}

    def pause_campaign(self, campaign_id: str) -> Dict[str, Any]:
        with self._lock:
            c = self._campaigns.get(campaign_id)
            if not c:
                return {"status": "error", "error": "campaign not found", "found": False}
            c.status = CampaignStatus.PAUSED
            self._log_event(
                RetentionEventKind.CAMPAIGN_PAUSED,
                {"campaign_id": campaign_id},
            )
            return {"status": "ok", "campaign": c.to_dict()}

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------
    def set_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if "churn_high_threshold" in config:
                self._config.churn_high_threshold = _clamp(_safe_float(config["churn_high_threshold"], _CHURN_RISK_HIGH))
            if "churn_medium_threshold" in config:
                self._config.churn_medium_threshold = _clamp(_safe_float(config["churn_medium_threshold"], _CHURN_RISK_MEDIUM))
            if "churn_low_threshold" in config:
                self._config.churn_low_threshold = _clamp(_safe_float(config["churn_low_threshold"], _CHURN_RISK_LOW))
            if "recency_half_life_days" in config:
                self._config.recency_half_life_days = max(0.1, _safe_float(config["recency_half_life_days"], _RECENCY_HALF_LIFE_DAYS))
            if "session_window_days" in config:
                self._config.session_window_days = max(1, _safe_int(config["session_window_days"], _SESSION_WINDOW_DAYS))
            if "auto_segment" in config:
                self._config.auto_segment = bool(config["auto_segment"])
            if "auto_recommend" in config:
                self._config.auto_recommend = bool(config["auto_recommend"])
            return {"status": "ok", "config": self._config.to_dict()}

    def get_config(self) -> Dict[str, Any]:
        with self._lock:
            return {"status": "ok", "config": self._config.to_dict()}

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------
    def tick(self) -> Dict[str, Any]:
        with self._lock:
            self._tick_count += 1
            now = _now_seconds()
            # Auto-predict for all players if auto_recommend is on
            predicted = 0
            actions_created = 0
            if self._config.auto_recommend:
                for pid in list(self._players.keys()):
                    self.predict_churn(pid)
                    predicted += 1
                    # Auto-recommend for high-risk players
                    score = self._predictions.get(pid)
                    if score and score.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                        existing = self._player_actions.get(pid, [])
                        if not existing or (
                            self._actions[existing[-1]].expires_at < now
                        ):
                            self.recommend_action(pid)
                            actions_created += 1

            # Auto-complete campaigns past their end time
            completed = 0
            for c in self._campaigns.values():
                if c.status == CampaignStatus.ACTIVE and c.ends_at > 0 and now >= c.ends_at:
                    c.status = CampaignStatus.COMPLETED
                    completed += 1
                    self._log_event(
                        RetentionEventKind.CAMPAIGN_COMPLETED,
                        {"campaign_id": c.campaign_id},
                    )

            self._log_event(
                RetentionEventKind.TICK_PROCESSED,
                {
                    "tick": self._tick_count,
                    "predicted": predicted,
                    "actions_created": actions_created,
                    "completed": completed,
                },
            )
            return {
                "status": "ok",
                "tick": self._tick_count,
                "predicted": predicted,
                "actions_created": actions_created,
                "campaigns_completed": completed,
            }

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------
    def _seed(self) -> None:
        now = _now_seconds()
        # 6 seeded players with varied engagement profiles
        seeds = [
            {
                "player_id": "plr_acolyte_fresh",
                "display_name": "Acolyte Fresh",
                "region": "na",
                "registered_at": now - 86400 * 2,    # 2 days ago
                "progression_level": 0.15,
                "sessions": [
                    {"duration": 25.0, "events": 40, "progress": 0.05, "social": 1, "spend": 0, "age_days": 2},
                    {"duration": 35.0, "events": 55, "progress": 0.05, "social": 2, "spend": 0, "age_days": 1},
                ],
            },
            {
                "player_id": "plr_veteran_steady",
                "display_name": "Veteran Steady",
                "region": "eu",
                "registered_at": now - 86400 * 90,  # 90 days ago
                "progression_level": 0.78,
                "sessions": [
                    {"duration": 75.0, "events": 180, "progress": 0.02, "social": 8, "spend": 200, "age_days": 6},
                    {"duration": 80.0, "events": 190, "progress": 0.02, "social": 7, "spend": 100, "age_days": 4},
                    {"duration": 65.0, "events": 150, "progress": 0.01, "social": 5, "spend": 0, "age_days": 2},
                    {"duration": 70.0, "events": 160, "progress": 0.01, "social": 6, "spend": 50, "age_days": 1},
                ],
            },
            {
                "player_id": "plr_whale_engaged",
                "display_name": "Whale Engaged",
                "region": "apac",
                "registered_at": now - 86400 * 120,
                "progression_level": 0.92,
                "sessions": [
                    {"duration": 110.0, "events": 280, "progress": 0.01, "social": 12, "spend": 2500, "age_days": 5},
                    {"duration": 95.0, "events": 230, "progress": 0.01, "social": 10, "spend": 1500, "age_days": 3},
                    {"duration": 120.0, "events": 300, "progress": 0.01, "social": 14, "spend": 3000, "age_days": 1},
                ],
            },
            {
                "player_id": "plr_dormant_returner",
                "display_name": "Dormant Returner",
                "region": "na",
                "registered_at": now - 86400 * 60,
                "progression_level": 0.55,
                "sessions": [
                    {"duration": 50.0, "events": 100, "progress": 0.03, "social": 3, "spend": 100, "age_days": 30},
                    {"duration": 40.0, "events": 80, "progress": 0.02, "social": 2, "spend": 0, "age_days": 25},
                    {"duration": 45.0, "events": 90, "progress": 0.02, "social": 2, "spend": 50, "age_days": 1},
                ],
            },
            {
                "player_id": "plr_churned_lapsed",
                "display_name": "Churned Lapsed",
                "region": "eu",
                "registered_at": now - 86400 * 75,
                "progression_level": 0.42,
                "sessions": [
                    {"duration": 30.0, "events": 50, "progress": 0.04, "social": 1, "spend": 0, "age_days": 45},
                    {"duration": 25.0, "events": 40, "progress": 0.03, "social": 0, "spend": 0, "age_days": 40},
                ],
            },
            {
                "player_id": "plr_at_risk_mid",
                "display_name": "At Risk Mid",
                "region": "sa",
                "registered_at": now - 86400 * 35,
                "progression_level": 0.38,
                "sessions": [
                    {"duration": 45.0, "events": 90, "progress": 0.03, "social": 2, "spend": 50, "age_days": 12},
                    {"duration": 35.0, "events": 70, "progress": 0.02, "social": 1, "spend": 0, "age_days": 8},
                ],
            },
        ]

        for seed in seeds:
            profile = PlayerEngagementProfile(
                player_id=seed["player_id"],
                display_name=seed["display_name"],
                region=seed["region"],
                registered_at=seed["registered_at"],
                last_active_at=seed["registered_at"],
                progression_level=seed["progression_level"],
            )
            self._players[profile.player_id] = profile
            self._player_sessions[profile.player_id] = []
            self._player_actions[profile.player_id] = []
            for s in seed["sessions"]:
                started = now - s["age_days"] * 86400
                session = SessionRecord(
                    session_id=f"ses_{uuid.uuid4().hex[:10]}",
                    player_id=profile.player_id,
                    started_at=started,
                    duration_minutes=s["duration"],
                    events_count=s["events"],
                    progress_delta=s["progress"],
                    social_interactions=s["social"],
                    monetization_cents=s["spend"],
                )
                self._sessions[session.session_id] = session
                self._player_sessions[profile.player_id].append(session.session_id)
                profile.total_sessions += 1
                profile.total_playtime_minutes += session.duration_minutes
                profile.total_events += session.events_count
                profile.total_social_interactions += session.social_interactions
                profile.total_monetization_cents += session.monetization_cents
                profile.last_active_at = max(profile.last_active_at, started)
                profile.progression_level = _clamp(
                    profile.progression_level + session.progress_delta
                )
                profile.sessions.append(session.session_id)
            profile.days_since_register = _days_between(now, profile.registered_at)
            profile.is_veteran = profile.days_since_register >= 30.0

        # Initial predictions for all seeded players
        for pid in list(self._players.keys()):
            self.predict_churn(pid)

        # One seeded campaign
        campaign = RetentionCampaign(
            campaign_id="cmp_winback_dormant",
            name="Dormant Win-Back",
            description="Win-back campaign targeting dormant players with personal offers.",
            status=CampaignStatus.DRAFT,
            target_segment=SegmentKind.DORMANT,
            action_kind=ActionKind.PERSONAL_OFFER,
            budget_cents=50000,
            payload={"discount_pct": 20, "duration_hours": 72},
        )
        campaign.target_player_ids = [
            pid for pid, seg in self._segments.items() if seg == SegmentKind.DORMANT
        ]
        self._campaigns[campaign.campaign_id] = campaign


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------
_singleton: Optional[RetentionPredictor] = None
_singleton_lock = threading.Lock()


def get_retention_predictor() -> RetentionPredictor:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = RetentionPredictor()
                _singleton.initialize()
    return _singleton
