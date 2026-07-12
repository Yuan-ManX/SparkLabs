"""
SparkLabs Agent - Player Sentiment Analyzer

AI-native sentiment analysis engine for the SparkLabs game platform. The
analyzer ingests gameplay telemetry, chat logs, survey responses, and
behavioral signals to model player emotion, frustration, engagement, and
satisfaction in real time. It builds per-player emotion profiles, detects
frustration events, tracks engagement metrics, and produces AI-driven
intervention suggestions to protect retention and well-being.

Architecture:
  PlayerSentimentAnalyzer (singleton)
    |-- SentimentSample, EmotionProfile, FrustrationEvent, EngagementMetric,
        InterventionSuggestion, SentimentTimeline, SentimentEvent,
        SentimentConfig, SentimentStats, SentimentSnapshot
    |-- SentimentType, EmotionCategory, EngagementLevel, FrustrationLevel,
        DataSource, InterventionType, TrendDirection

Core Capabilities:
  - register_sample / get_sample / list_samples / remove_sample: ingest and
    manage discrete sentiment observations from any data source.
  - get_or_create_profile / get_profile / list_profiles / update_profile /
    remove_profile: maintain persistent per-player emotion profiles that
    aggregate raw samples into dominant emotion, volatility, and trends.
  - record_frustration / get_frustration_event / list_frustration_events /
    resolve_frustration: capture frustration spikes with trigger context and
    track their resolution state.
  - record_engagement / get_engagement_metric / list_engagement_metrics:
    record quantitative engagement readings (session duration, APM, social
    interactions, exploration, progression).
  - suggest_intervention / register_intervention / get_intervention /
    list_interventions / remove_intervention: AI-driven recommendations that
    map a player's emotional state to a concrete intervention type.
  - generate_timeline / get_sentiment_summary / detect_churn_risk /
    batch_analyze: analytical views that turn raw signals into actionable
    insight.
  - list_events / get_status / get_stats / get_snapshot / get_config /
    set_config / tick / reset: observability, tuning, and lifecycle control.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PROFILES: int = 5000
_MAX_SAMPLES: int = 50000
_MAX_SAMPLES_PER_PLAYER: int = 500
_MAX_FRUSTRATION_EVENTS: int = 10000
_MAX_ENGAGEMENT_METRICS: int = 20000
_MAX_INTERVENTIONS: int = 8000
_MAX_TIMELINES: int = 5000
_MAX_EVENTS: int = 10000

# Scoring bounds
_SENTIMENT_MIN: float = -1.0
_SENTIMENT_MAX: float = 1.0
_VOLATILITY_FLOOR: float = 0.0
_VOLATILITY_CEIL: float = 1.0

# Churn-risk calibration
_CHURN_ENGAGEMENT_WEIGHT: float = 0.45
_CHURN_SATISFACTION_WEIGHT: float = 0.25
_CHURN_SENTIMENT_WEIGHT: float = 0.20
_CHURN_FRUSTRATION_WEIGHT: float = 0.10

# Frustration-to-score mapping used when deriving a numeric frustration factor
_FRUSTRATION_SCORES: Dict[str, float] = {
    "none": 0.0,
    "low": 0.25,
    "moderate": 0.5,
    "high": 0.75,
    "severe": 1.0,
}

# Engagement-to-risk baseline used by churn detection
_ENGAGEMENT_RISK: Dict[str, float] = {
    "highly_engaged": 0.05,
    "engaged": 0.15,
    "neutral": 0.4,
    "disengaged": 0.7,
    "churn_risk": 0.9,
}


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


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


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


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((v - avg) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        cleaned = ts.rstrip("Z")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class SentimentType(str, Enum):
    """Overall polarity of a sentiment observation."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    VERY_POSITIVE = "very_positive"
    VERY_NEGATIVE = "very_negative"


class EmotionCategory(str, Enum):
    """Discrete emotion labels derived from behavioral and textual signals."""
    JOY = "joy"
    FRUSTRATION = "frustration"
    EXCITEMENT = "excitement"
    BOREDOM = "boredom"
    ANGER = "anger"
    SATISFACTION = "satisfaction"
    ANXIETY = "anxiety"
    CURIOSITY = "curiosity"
    RELIEF = "relief"
    DISAPPOINTMENT = "disappointment"
    PRIDE = "pride"
    CONFUSION = "confusion"
    NEUTRAL = "neutral"


class EngagementLevel(str, Enum):
    """Player engagement states mapped to retention outcomes."""
    HIGHLY_ENGAGED = "highly_engaged"
    ENGAGED = "engaged"
    NEUTRAL = "neutral"
    DISENGAGED = "disengaged"
    CHURN_RISK = "churn_risk"


class FrustrationLevel(str, Enum):
    """Severity of a frustration episode."""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


class DataSource(str, Enum):
    """Origin of a sentiment signal."""
    GAMEPLAY_TELEMETRY = "gameplay_telemetry"
    CHAT_LOG = "chat_log"
    SURVEY = "survey"
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    SESSION_DURATION = "session_duration"
    SOCIAL_INTERACTION = "social_interaction"
    PURCHASE_BEHAVIOR = "purchase_behavior"


class InterventionType(str, Enum):
    """Categories of intervention the analyzer can recommend."""
    DIFFICULTY_ADJUSTMENT = "difficulty_adjustment"
    TUTORIAL_PROMPT = "tutorial_prompt"
    REWARD_GRANT = "reward_grant"
    CONTENT_SUGGESTION = "content_suggestion"
    SOCIAL_NUDGE = "social_nudge"
    BREAK_SUGGESTION = "break_suggestion"
    NONE = "none"


class TrendDirection(str, Enum):
    """Direction of change in a metric over the analysis window."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SentimentSample:
    """A single sentiment observation for a player.

    Captures the polarity, emotion, score, engagement, frustration, source,
    and contextual metadata at a point in time. Samples are the atomic unit
    fed into profile aggregation and timeline generation.
    """
    sample_id: str
    player_id: str
    timestamp: str
    sentiment_type: SentimentType
    emotion_category: EmotionCategory
    sentiment_score: float = 0.0
    engagement_level: EngagementLevel = EngagementLevel.NEUTRAL
    frustration_level: FrustrationLevel = FrustrationLevel.NONE
    data_source: DataSource = DataSource.GAMEPLAY_TELEMETRY
    session_id: str = ""
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EmotionProfile:
    """Aggregated emotional state for a single player.

    Derived from the player's sentiment samples: dominant emotion, average
    sentiment, engagement and frustration trends, emotional volatility, and
    a composite satisfaction score.
    """
    profile_id: str
    player_id: str
    dominant_emotion: EmotionCategory
    average_sentiment: float = 0.0
    engagement_trend: TrendDirection = TrendDirection.STABLE
    frustration_trend: TrendDirection = TrendDirection.STABLE
    emotional_volatility: float = 0.0
    satisfaction_score: float = 0.0
    last_updated: str = ""
    samples_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FrustrationEvent:
    """A recorded frustration spike with trigger context.

    Tracks the severity, trigger type and description, duration, and
    resolution state so the system can correlate frustration causes with
    outcomes and measure mitigation effectiveness.
    """
    event_id: str
    player_id: str
    timestamp: str
    frustration_level: FrustrationLevel
    trigger_type: str = ""
    trigger_description: str = ""
    duration_seconds: float = 0.0
    context: str = ""
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EngagementMetric:
    """A quantitative engagement reading for a player.

    Captures session duration, actions per minute, social interaction count,
    exploration score, and progression rate at a point in time. These
    readings complement the qualitative sentiment samples.
    """
    metric_id: str
    player_id: str
    timestamp: str
    engagement_level: EngagementLevel
    session_duration: float = 0.0
    actions_per_minute: float = 0.0
    social_interactions: int = 0
    exploration_score: float = 0.0
    progression_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InterventionSuggestion:
    """An AI-generated intervention recommendation for a player.

    Maps the player's current emotional and engagement state to a concrete
    intervention type, with a priority, rationale, expected impact, and the
    target metric the intervention is meant to move.
    """
    suggestion_id: str
    player_id: str
    timestamp: str
    intervention_type: InterventionType
    priority: str = "low"
    reason: str = ""
    expected_impact: str = ""
    target_metric: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SentimentTimeline:
    """A time-ordered series of sentiment samples for a player.

    Built by generate_timeline over a bounded period. Includes the trend
    direction, average score, peak and lowest emotions, and the boundary
    timestamps of the window.
    """
    timeline_id: str
    player_id: str
    samples: List[Dict[str, Any]] = field(default_factory=list)
    trend_direction: TrendDirection = TrendDirection.STABLE
    average_score: float = 0.0
    peak_emotion: EmotionCategory = EmotionCategory.JOY
    lowest_emotion: EmotionCategory = EmotionCategory.FRUSTRATION
    period_start: str = ""
    period_end: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SentimentConfig:
    """Tunable configuration for the sentiment analyzer."""
    max_profiles: int = 5000
    max_samples_per_player: int = 500
    max_frustration_events: int = 10000
    analysis_window_minutes: int = 60
    auto_intervention_enabled: bool = True
    frustration_threshold: float = 0.6
    churn_risk_threshold: float = 0.65
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SentimentStats:
    """Roll-up statistics maintained across the analyzer's lifetime."""
    total_profiles: int = 0
    total_samples: int = 0
    total_frustration_events: int = 0
    total_interventions: int = 0
    avg_satisfaction: float = 0.0
    churn_risk_count: int = 0
    highly_engaged_count: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SentimentSnapshot:
    """A point-in-time snapshot of the analyzer's full state."""
    timestamp: str
    profiles: List[Dict[str, Any]] = field(default_factory=list)
    recent_samples: List[Dict[str, Any]] = field(default_factory=list)
    frustration_events: List[Dict[str, Any]] = field(default_factory=list)
    interventions: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SentimentEvent:
    """An internal audit event emitted by the analyzer."""
    event_id: str
    event_type: str
    timestamp: str
    player_id: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Main System - Player Sentiment Analyzer (Singleton)
# ---------------------------------------------------------------------------

class PlayerSentimentAnalyzer:
    """AI-native player sentiment analysis engine.

    The analyzer maintains per-player emotion profiles, frustration events,
    engagement metrics, intervention suggestions, and timelines. It is
    thread-safe and implemented as a singleton with double-checked locking.
    The _init_lock guards seed initialization; _lock guards the singleton
    instance creation. All mutating methods take the _init_lock to keep
    internal dictionaries consistent.
    """

    _instance: Optional["PlayerSentimentAnalyzer"] = None
    _lock = threading.RLock()
    _init_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "PlayerSentimentAnalyzer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "PlayerSentimentAnalyzer":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._samples: Dict[str, SentimentSample] = {}
            self._player_samples: Dict[str, List[str]] = {}
            self._profiles: Dict[str, EmotionProfile] = {}
            self._frustration_events: Dict[str, FrustrationEvent] = {}
            self._engagement_metrics: Dict[str, EngagementMetric] = {}
            self._player_engagement: Dict[str, List[str]] = {}
            self._interventions: Dict[str, InterventionSuggestion] = {}
            self._timelines: Dict[str, SentimentTimeline] = {}
            self._events: List[SentimentEvent] = []
            self._config = SentimentConfig()
            self._stats = SentimentStats()
            self._tick_count: int = 0
            self._seed()
            # _seed() sets self._initialized = True when it finishes.

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, player_id: str = "",
              data: Optional[Dict[str, Any]] = None) -> None:
        event = SentimentEvent(
            event_id=_new_id("evt"),
            event_type=event_type,
            timestamp=_now(),
            player_id=player_id,
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        self._stats.total_profiles = len(self._profiles)
        self._stats.total_samples = len(self._samples)
        self._stats.total_frustration_events = len(self._frustration_events)
        self._stats.total_interventions = len(self._interventions)
        self._stats.tick_count = self._tick_count

        satisfaction_values: List[float] = [
            p.satisfaction_score for p in self._profiles.values()
        ]
        self._stats.avg_satisfaction = round(_mean(satisfaction_values), 4)

        self._stats.churn_risk_count = sum(
            1 for p in self._profiles.values()
            if p.dominant_emotion in (EmotionCategory.FRUSTRATION, EmotionCategory.ANGER,
                                      EmotionCategory.DISAPPOINTMENT)
            or p.satisfaction_score < 0.4
        )
        self._stats.highly_engaged_count = sum(
            1 for p in self._profiles.values()
            if p.satisfaction_score >= 0.75
        )

    def _player_sample_list(self, player_id: str) -> List[SentimentSample]:
        ids = self._player_samples.get(player_id, [])
        out: List[SentimentSample] = []
        for sid in ids:
            s = self._samples.get(sid)
            if s is not None:
                out.append(s)
        return out

    def _player_engagement_list(self, player_id: str) -> List[EngagementMetric]:
        ids = self._player_engagement.get(player_id, [])
        out: List[EngagementMetric] = []
        for mid in ids:
            m = self._engagement_metrics.get(mid)
            if m is not None:
                out.append(m)
        return out

    @staticmethod
    def _sentiment_to_score(st: SentimentType, fallback: float = 0.0) -> float:
        mapping = {
            SentimentType.VERY_POSITIVE: 0.9,
            SentimentType.POSITIVE: 0.6,
            SentimentType.NEUTRAL: 0.0,
            SentimentType.MIXED: 0.1,
            SentimentType.NEGATIVE: -0.6,
            SentimentType.VERY_NEGATIVE: -0.9,
        }
        return mapping.get(st, fallback)

    @staticmethod
    def _frustration_score(level: FrustrationLevel) -> float:
        return _FRUSTRATION_SCORES.get(level.value, 0.0)

    @staticmethod
    def _engagement_risk(level: EngagementLevel) -> float:
        return _ENGAGEMENT_RISK.get(level.value, 0.4)

    # ------------------------------------------------------------------
    # Sentiment Sample Lifecycle
    # ------------------------------------------------------------------

    def register_sample(
        self,
        sample_id: str,
        player_id: str,
        sentiment_type: Any,
        emotion_category: Any,
        sentiment_score: float = 0.0,
        engagement_level: str = "neutral",
        frustration_level: str = "none",
        data_source: str = "gameplay_telemetry",
        session_id: str = "",
        context: str = "",
        timestamp: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[SentimentSample]]:
        """Register a discrete sentiment observation for a player."""
        if not sample_id or not player_id:
            return False, "sample_id and player_id are required", None

        st = _coerce_enum(SentimentType, sentiment_type)
        if st is None:
            return False, f"invalid sentiment_type: {sentiment_type}", None

        ec = _coerce_enum(EmotionCategory, emotion_category)
        if ec is None:
            return False, f"invalid emotion_category: {emotion_category}", None

        el = _coerce_enum(EngagementLevel, engagement_level, EngagementLevel.NEUTRAL)
        fl = _coerce_enum(FrustrationLevel, frustration_level, FrustrationLevel.NONE)
        ds = _coerce_enum(DataSource, data_source, DataSource.GAMEPLAY_TELEMETRY)

        with self._init_lock:
            if sample_id in self._samples:
                return False, f"sample_id already exists: {sample_id}", None

            score = _clamp(_safe_float(sentiment_score, self._sentiment_to_score(st)),
                           _SENTIMENT_MIN, _SENTIMENT_MAX)
            ts = timestamp or _now()

            sample = SentimentSample(
                sample_id=sample_id,
                player_id=player_id,
                timestamp=ts,
                sentiment_type=st,
                emotion_category=ec,
                sentiment_score=round(score, 4),
                engagement_level=el,
                frustration_level=fl,
                data_source=ds,
                session_id=session_id,
                context=context,
                metadata=metadata or {},
            )
            self._samples[sample_id] = sample
            bucket = self._player_samples.setdefault(player_id, [])
            bucket.append(sample_id)
            _evict_fifo_dict(self._samples, _MAX_SAMPLES)
            _evict_fifo_list(bucket, self._config.max_samples_per_player)

            # Update or create the player profile lazily.
            self._recompute_profile(player_id)

            self._emit(
                "sample_registered",
                player_id=player_id,
                data={"sample_id": sample_id, "sentiment_type": st.value,
                      "emotion": ec.value, "score": round(score, 4)},
            )
            return True, "success", sample

    def get_sample(self, sample_id: str) -> Optional[SentimentSample]:
        return self._samples.get(sample_id)

    def list_samples(
        self,
        player_id: str,
        limit: int = 100,
        source_filter: str = "",
    ) -> List[SentimentSample]:
        source_enum = _coerce_enum(DataSource, source_filter) if source_filter else None
        result: List[SentimentSample] = []
        cap = max(1, _safe_int(limit, 100))
        for s in self._player_sample_list(player_id):
            if source_enum is not None and s.data_source != source_enum:
                continue
            result.append(s)
            if len(result) >= cap:
                break
        # Return most-recent-first for readability.
        result.sort(key=lambda x: x.timestamp, reverse=True)
        return result

    def remove_sample(self, sample_id: str) -> Tuple[bool, str]:
        with self._init_lock:
            sample = self._samples.pop(sample_id, None)
            if sample is None:
                return False, "not found"
            bucket = self._player_samples.get(sample.player_id)
            if bucket:
                try:
                    bucket.remove(sample_id)
                except ValueError:
                    pass
            self._recompute_profile(sample.player_id)
            self._emit(
                "sample_removed",
                player_id=sample.player_id,
                data={"sample_id": sample_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Emotion Profile Lifecycle
    # ------------------------------------------------------------------

    def get_or_create_profile(self, player_id: str) -> Optional[EmotionProfile]:
        if not player_id:
            return None
        with self._init_lock:
            existing = self._profiles.get(player_id)
            if existing is not None:
                return existing
            profile = EmotionProfile(
                profile_id=_new_id("profile"),
                player_id=player_id,
                dominant_emotion=EmotionCategory.NEUTRAL,
                average_sentiment=0.0,
                engagement_trend=TrendDirection.STABLE,
                frustration_trend=TrendDirection.STABLE,
                emotional_volatility=0.0,
                satisfaction_score=0.5,
                last_updated=_now(),
                samples_count=0,
                metadata={},
            )
            self._profiles[player_id] = profile
            _evict_fifo_dict(self._profiles, self._config.max_profiles)
            self._emit(
                "profile_created",
                player_id=player_id,
                data={"profile_id": profile.profile_id},
            )
            return profile

    def get_profile(self, player_id: str) -> Optional[EmotionProfile]:
        return self._profiles.get(player_id)

    def list_profiles(self, engagement_filter: str = "") -> List[EmotionProfile]:
        level = _coerce_enum(EngagementLevel, engagement_filter) if engagement_filter else None
        result: List[EmotionProfile] = []
        for p in self._profiles.values():
            if level is not None:
                # Map profile signals to an engagement bucket for filtering.
                bucket = self._profile_engagement_bucket(p)
                if bucket != level:
                    continue
            result.append(p)
        result.sort(key=lambda x: x.satisfaction_score, reverse=True)
        return result

    @staticmethod
    def _profile_engagement_bucket(profile: EmotionProfile) -> EngagementLevel:
        if profile.satisfaction_score >= 0.75 and profile.average_sentiment >= 0.4:
            return EngagementLevel.HIGHLY_ENGAGED
        if profile.satisfaction_score >= 0.55:
            return EngagementLevel.ENGAGED
        if profile.satisfaction_score <= 0.25 or profile.average_sentiment <= -0.4:
            return EngagementLevel.CHURN_RISK
        if profile.satisfaction_score < 0.45:
            return EngagementLevel.DISENGAGED
        return EngagementLevel.NEUTRAL

    def update_profile(self, player_id: str) -> Tuple[bool, str, Optional[EmotionProfile]]:
        """Recalculate a player's profile from its recorded samples."""
        with self._init_lock:
            if player_id not in self._profiles:
                return False, "profile not found", None
            self._recompute_profile(player_id)
            return True, "updated", self._profiles.get(player_id)

    def remove_profile(self, player_id: str) -> Tuple[bool, str]:
        with self._init_lock:
            removed = self._profiles.pop(player_id, None)
            if removed is None:
                return False, "not found"
            self._emit(
                "profile_removed",
                player_id=player_id,
                data={"profile_id": removed.profile_id},
            )
            return True, "removed"

    def _recompute_profile(self, player_id: str) -> None:
        """Recompute the aggregated profile fields from raw samples."""
        profile = self._profiles.get(player_id)
        if profile is None:
            return

        samples = self._player_sample_list(player_id)
        if not samples:
            profile.samples_count = 0
            profile.last_updated = _now()
            return

        scores = [s.sentiment_score for s in samples]
        avg_sentiment = _mean(scores)
        volatility = _clamp(_stddev(scores), _VOLATILITY_FLOOR, _VOLATILITY_CEIL)

        # Dominant emotion is the most frequent category among recent samples.
        emotion_counts: Dict[EmotionCategory, int] = {}
        for s in samples:
            emotion_counts[s.emotion_category] = emotion_counts.get(s.emotion_category, 0) + 1
        dominant = max(emotion_counts, key=lambda k: emotion_counts[k])

        # Trend direction derived from comparing the second half of samples
        # (most recent) against the first half.
        midpoint = len(scores) // 2
        if midpoint == 0:
            engagement_trend = TrendDirection.STABLE
            frustration_trend = TrendDirection.STABLE
        else:
            older = scores[:midpoint]
            newer = scores[midpoint:]
            delta = _mean(newer) - _mean(older)
            if abs(delta) < 0.05:
                engagement_trend = TrendDirection.STABLE
            elif delta > 0:
                engagement_trend = TrendDirection.IMPROVING
            else:
                engagement_trend = TrendDirection.DECLINING

            older_frustration = _mean([
                self._frustration_score(s.frustration_level) for s in samples[:midpoint]
            ])
            newer_frustration = _mean([
                self._frustration_score(s.frustration_level) for s in samples[midpoint:]
            ])
            f_delta = newer_frustration - older_frustration
            if abs(f_delta) < 0.05:
                frustration_trend = TrendDirection.STABLE
            elif f_delta > 0:
                frustration_trend = TrendDirection.DECLINING
            else:
                frustration_trend = TrendDirection.IMPROVING

        if volatility > 0.35:
            engagement_trend = TrendDirection.VOLATILE

        # Satisfaction score blends average sentiment, inverse volatility, and
        # inverse frustration into a 0..1 composite.
        avg_frustration = _mean([
            self._frustration_score(s.frustration_level) for s in samples
        ])
        sentiment_component = (avg_sentiment + 1.0) / 2.0  # map -1..1 to 0..1
        satisfaction = (
            0.5 * sentiment_component
            + 0.3 * (1.0 - volatility)
            + 0.2 * (1.0 - avg_frustration)
        )
        satisfaction = _clamp(satisfaction)

        profile.dominant_emotion = dominant
        profile.average_sentiment = round(avg_sentiment, 4)
        profile.engagement_trend = engagement_trend
        profile.frustration_trend = frustration_trend
        profile.emotional_volatility = round(volatility, 4)
        profile.satisfaction_score = round(satisfaction, 4)
        profile.samples_count = len(samples)
        profile.last_updated = _now()

    # ------------------------------------------------------------------
    # Frustration Event Lifecycle
    # ------------------------------------------------------------------

    def record_frustration(
        self,
        event_id: str,
        player_id: str,
        frustration_level: Any,
        trigger_type: str = "",
        trigger_description: str = "",
        duration_seconds: float = 0.0,
        context: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[FrustrationEvent]]:
        if not event_id or not player_id:
            return False, "event_id and player_id are required", None
        fl = _coerce_enum(FrustrationLevel, frustration_level)
        if fl is None:
            return False, f"invalid frustration_level: {frustration_level}", None

        with self._init_lock:
            if event_id in self._frustration_events:
                return False, f"event_id already exists: {event_id}", None

            event = FrustrationEvent(
                event_id=event_id,
                player_id=player_id,
                timestamp=_now(),
                frustration_level=fl,
                trigger_type=trigger_type,
                trigger_description=trigger_description,
                duration_seconds=_safe_float(duration_seconds, 0.0),
                context=context,
                resolved=False,
                metadata=metadata or {},
            )
            self._frustration_events[event_id] = event
            _evict_fifo_dict(self._frustration_events, self._config.max_frustration_events)
            self._emit(
                "frustration_recorded",
                player_id=player_id,
                data={"event_id": event_id, "level": fl.value,
                      "trigger_type": trigger_type},
            )
            return True, "success", event

    def get_frustration_event(self, event_id: str) -> Optional[FrustrationEvent]:
        return self._frustration_events.get(event_id)

    def list_frustration_events(
        self,
        player_id: str = "",
        resolved_filter: str = "",
    ) -> List[FrustrationEvent]:
        resolved_flag: Optional[bool] = None
        if resolved_filter.lower() == "true":
            resolved_flag = True
        elif resolved_filter.lower() == "false":
            resolved_flag = False

        result: List[FrustrationEvent] = []
        for e in self._frustration_events.values():
            if player_id and e.player_id != player_id:
                continue
            if resolved_flag is not None and e.resolved != resolved_flag:
                continue
            result.append(e)
        result.sort(key=lambda x: x.timestamp, reverse=True)
        return result

    def resolve_frustration(self, event_id: str) -> Tuple[bool, str, Optional[FrustrationEvent]]:
        with self._init_lock:
            event = self._frustration_events.get(event_id)
            if event is None:
                return False, "not found", None
            event.resolved = True
            self._emit(
                "frustration_resolved",
                player_id=event.player_id,
                data={"event_id": event_id},
            )
            return True, "resolved", event

    # ------------------------------------------------------------------
    # Engagement Metric Lifecycle
    # ------------------------------------------------------------------

    def record_engagement(
        self,
        metric_id: str,
        player_id: str,
        engagement_level: Any,
        session_duration: float = 0.0,
        actions_per_minute: float = 0.0,
        social_interactions: int = 0,
        exploration_score: float = 0.0,
        progression_rate: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[EngagementMetric]]:
        if not metric_id or not player_id:
            return False, "metric_id and player_id are required", None
        el = _coerce_enum(EngagementLevel, engagement_level)
        if el is None:
            return False, f"invalid engagement_level: {engagement_level}", None

        with self._init_lock:
            if metric_id in self._engagement_metrics:
                return False, f"metric_id already exists: {metric_id}", None

            metric = EngagementMetric(
                metric_id=metric_id,
                player_id=player_id,
                timestamp=_now(),
                engagement_level=el,
                session_duration=_safe_float(session_duration, 0.0),
                actions_per_minute=_safe_float(actions_per_minute, 0.0),
                social_interactions=_safe_int(social_interactions, 0),
                exploration_score=_clamp(_safe_float(exploration_score, 0.0)),
                progression_rate=_clamp(_safe_float(progression_rate, 0.0)),
                metadata=metadata or {},
            )
            self._engagement_metrics[metric_id] = metric
            bucket = self._player_engagement.setdefault(player_id, [])
            bucket.append(metric_id)
            _evict_fifo_dict(self._engagement_metrics, _MAX_ENGAGEMENT_METRICS)
            self._emit(
                "engagement_recorded",
                player_id=player_id,
                data={"metric_id": metric_id, "level": el.value,
                      "session_duration": metric.session_duration},
            )
            return True, "success", metric

    def get_engagement_metric(self, metric_id: str) -> Optional[EngagementMetric]:
        return self._engagement_metrics.get(metric_id)

    def list_engagement_metrics(
        self,
        player_id: str,
        limit: int = 50,
    ) -> List[EngagementMetric]:
        result = self._player_engagement_list(player_id)
        cap = max(1, _safe_int(limit, 50))
        result.sort(key=lambda x: x.timestamp, reverse=True)
        return result[:cap]

    # ------------------------------------------------------------------
    # Intervention Lifecycle
    # ------------------------------------------------------------------

    def suggest_intervention(
        self,
        player_id: str,
    ) -> Tuple[bool, str, Optional[InterventionSuggestion]]:
        """Generate an AI-driven intervention suggestion for a player.

        The suggestion is derived from the player's emotion profile, churn
        risk, frustration level, and engagement trend. When no profile
        exists the call returns without a suggestion.
        """
        if not player_id:
            return False, "player_id is required", None

        with self._init_lock:
            profile = self._profiles.get(player_id)
            if profile is None:
                return False, "profile not found", None

            risk_ok, _, risk = self._compute_churn_risk(profile)
            if not risk_ok:
                return False, "could not compute churn risk", None

            unresolved = [
                e for e in self._frustration_events.values()
                if e.player_id == player_id and not e.resolved
            ]
            max_frustration = FrustrationLevel.NONE
            for e in unresolved:
                if e.frustration_level.value == "severe":
                    max_frustration = FrustrationLevel.SEVERE
                    break
                if e.frustration_level.value == "high" and max_frustration != FrustrationLevel.SEVERE:
                    max_frustration = FrustrationLevel.HIGH

            intervention_type, priority, reason, target = self._decide_intervention(
                profile, risk, max_frustration
            )

            suggestion = InterventionSuggestion(
                suggestion_id=_new_id("sug"),
                player_id=player_id,
                timestamp=_now(),
                intervention_type=intervention_type,
                priority=priority,
                reason=reason,
                expected_impact=self._expected_impact_for(intervention_type),
                target_metric=target,
                metadata={
                    "churn_risk": round(risk, 4),
                    "satisfaction": profile.satisfaction_score,
                    "auto_generated": True,
                },
            )
            self._interventions[suggestion.suggestion_id] = suggestion
            _evict_fifo_dict(self._interventions, _MAX_INTERVENTIONS)
            self._emit(
                "intervention_suggested",
                player_id=player_id,
                data={"suggestion_id": suggestion.suggestion_id,
                      "type": intervention_type.value, "priority": priority},
            )
            return True, "success", suggestion

    def _decide_intervention(
        self,
        profile: EmotionProfile,
        churn_risk: float,
        max_frustration: FrustrationLevel,
    ) -> Tuple[InterventionType, str, str, str]:
        """Decide an intervention type from the player's current state."""
        if max_frustration in (FrustrationLevel.SEVERE, FrustrationLevel.HIGH):
            return (
                InterventionType.DIFFICULTY_ADJUSTMENT,
                "critical",
                "Player is experiencing severe frustration; reduce difficulty "
                "to restore a sense of progress.",
                "frustration_level",
            )
        if churn_risk >= self._config.churn_risk_threshold:
            return (
                InterventionType.CONTENT_SUGGESTION,
                "high",
                "Elevated churn risk detected; surface fresh content to "
                "rekindle interest.",
                "churn_risk",
            )
        if profile.dominant_emotion == EmotionCategory.BOREDOM:
            return (
                InterventionType.CONTENT_SUGGESTION,
                "medium",
                "Boredom is the dominant emotion; introduce variety or new "
                "objectives.",
                "engagement_level",
            )
        if profile.dominant_emotion == EmotionCategory.CONFUSION:
            return (
                InterventionType.TUTORIAL_PROMPT,
                "medium",
                "Confusion detected; offer a contextual tutorial prompt to "
                "clarify mechanics.",
                "progression_rate",
            )
        if profile.dominant_emotion == EmotionCategory.ANGER:
            return (
                InterventionType.BREAK_SUGGESTION,
                "high",
                "Anger signals building tension; suggest a short break to "
                "cool down.",
                "satisfaction_score",
            )
        if profile.engagement_trend == TrendDirection.DECLINING:
            return (
                InterventionType.REWARD_GRANT,
                "medium",
                "Engagement is declining; grant a small reward to reinforce "
                "continued play.",
                "engagement_level",
            )
        if profile.dominant_emotion in (EmotionCategory.JOY, EmotionCategory.PRIDE,
                                        EmotionCategory.SATISFACTION):
            return (
                InterventionType.SOCIAL_NUDGE,
                "low",
                "Positive emotional state; nudge the player toward social "
                "features to amplify satisfaction.",
                "social_interactions",
            )
        return (
            InterventionType.NONE,
            "low",
            "No intervention required at this time.",
            "none",
        )

    @staticmethod
    def _expected_impact_for(it: InterventionType) -> str:
        mapping = {
            InterventionType.DIFFICULTY_ADJUSTMENT: "Lower frustration and reduce wipe-driven exit.",
            InterventionType.TUTORIAL_PROMPT: "Improve clarity and lift progression rate.",
            InterventionType.REWARD_GRANT: "Reinforce positive feedback loop and raise engagement.",
            InterventionType.CONTENT_SUGGESTION: "Restore novelty and lower churn probability.",
            InterventionType.SOCIAL_NUDGE: "Deepen community ties and extend session duration.",
            InterventionType.BREAK_SUGGESTION: "Defuse anger and protect long-term well-being.",
            InterventionType.NONE: "No measurable impact expected.",
        }
        return mapping.get(it, "")

    def register_intervention(
        self,
        suggestion_id: str,
        player_id: str,
        intervention_type: Any,
        priority: str = "low",
        reason: str = "",
        expected_impact: str = "",
        target_metric: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[InterventionSuggestion]]:
        if not suggestion_id or not player_id:
            return False, "suggestion_id and player_id are required", None
        it = _coerce_enum(InterventionType, intervention_type)
        if it is None:
            return False, f"invalid intervention_type: {intervention_type}", None

        with self._init_lock:
            if suggestion_id in self._interventions:
                return False, f"suggestion_id already exists: {suggestion_id}", None

            suggestion = InterventionSuggestion(
                suggestion_id=suggestion_id,
                player_id=player_id,
                timestamp=_now(),
                intervention_type=it,
                priority=priority,
                reason=reason,
                expected_impact=expected_impact,
                target_metric=target_metric,
                metadata=metadata or {},
            )
            self._interventions[suggestion_id] = suggestion
            _evict_fifo_dict(self._interventions, _MAX_INTERVENTIONS)
            self._emit(
                "intervention_registered",
                player_id=player_id,
                data={"suggestion_id": suggestion_id, "type": it.value},
            )
            return True, "success", suggestion

    def get_intervention(self, suggestion_id: str) -> Optional[InterventionSuggestion]:
        return self._interventions.get(suggestion_id)

    def list_interventions(
        self,
        player_id: str = "",
        type_filter: str = "",
    ) -> List[InterventionSuggestion]:
        type_enum = _coerce_enum(InterventionType, type_filter) if type_filter else None
        result: List[InterventionSuggestion] = []
        for s in self._interventions.values():
            if player_id and s.player_id != player_id:
                continue
            if type_enum is not None and s.intervention_type != type_enum:
                continue
            result.append(s)
        result.sort(key=lambda x: x.timestamp, reverse=True)
        return result

    def remove_intervention(self, suggestion_id: str) -> Tuple[bool, str]:
        with self._init_lock:
            removed = self._interventions.pop(suggestion_id, None)
            if removed is None:
                return False, "not found"
            self._emit(
                "intervention_removed",
                player_id=removed.player_id,
                data={"suggestion_id": suggestion_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Timeline and Analytics
    # ------------------------------------------------------------------

    def generate_timeline(
        self,
        player_id: str,
        period_start: str = "",
        period_end: str = "",
    ) -> Optional[SentimentTimeline]:
        """Build a sentiment timeline for a player over a bounded period."""
        if not player_id:
            return None

        start_dt = _parse_iso(period_start) if period_start else None
        end_dt = _parse_iso(period_end) if period_end else None

        samples = self._player_sample_list(player_id)
        filtered: List[SentimentSample] = []
        for s in samples:
            s_dt = _parse_iso(s.timestamp)
            if s_dt is None:
                continue
            if start_dt is not None and s_dt < start_dt:
                continue
            if end_dt is not None and s_dt > end_dt:
                continue
            filtered.append(s)

        filtered.sort(key=lambda x: x.timestamp)

        if not filtered:
            return None

        scores = [s.sentiment_score for s in filtered]
        emotion_counts: Dict[EmotionCategory, int] = {}
        for s in filtered:
            emotion_counts[s.emotion_category] = emotion_counts.get(s.emotion_category, 0) + 1

        peak_emotion = max(emotion_counts, key=lambda k: emotion_counts[k])
        lowest_emotion = min(emotion_counts, key=lambda k: emotion_counts[k])

        # Trend from first half to second half of the window.
        midpoint = len(scores) // 2
        if midpoint == 0:
            trend = TrendDirection.STABLE
        else:
            delta = _mean(scores[midpoint:]) - _mean(scores[:midpoint])
            if abs(delta) < 0.05:
                trend = TrendDirection.STABLE
            elif delta > 0:
                trend = TrendDirection.IMPROVING
            else:
                trend = TrendDirection.DECLINING
        if _stddev(scores) > 0.35:
            trend = TrendDirection.VOLATILE

        timeline = SentimentTimeline(
            timeline_id=_new_id("tl"),
            player_id=player_id,
            samples=[s.to_dict() for s in filtered],
            trend_direction=trend,
            average_score=round(_mean(scores), 4),
            peak_emotion=peak_emotion,
            lowest_emotion=lowest_emotion,
            period_start=filtered[0].timestamp,
            period_end=filtered[-1].timestamp,
            metadata={"sample_count": len(filtered)},
        )
        with self._init_lock:
            self._timelines[timeline.timeline_id] = timeline
            _evict_fifo_dict(self._timelines, _MAX_TIMELINES)
        self._emit(
            "timeline_generated",
            player_id=player_id,
            data={"timeline_id": timeline.timeline_id,
                  "samples": len(filtered), "trend": trend.value},
        )
        return timeline

    def get_sentiment_summary(self, player_id: str) -> Dict[str, Any]:
        """Return a compact summary of a player's sentiment state."""
        profile = self._profiles.get(player_id)
        if profile is None:
            return {"player_id": player_id, "found": False}

        samples = self._player_sample_list(player_id)
        frustration_events = [
            e for e in self._frustration_events.values() if e.player_id == player_id
        ]
        interventions = [
            i for i in self._interventions.values() if i.player_id == player_id
        ]
        engagement_metrics = self._player_engagement_list(player_id)
        _, _, churn_risk = self._compute_churn_risk(profile)

        return {
            "player_id": player_id,
            "found": True,
            "profile": profile.to_dict(),
            "churn_risk": round(churn_risk, 4),
            "samples_count": len(samples),
            "frustration_events_count": len(frustration_events),
            "unresolved_frustration": sum(1 for e in frustration_events if not e.resolved),
            "interventions_count": len(interventions),
            "engagement_metrics_count": len(engagement_metrics),
            "engagement_bucket": self._profile_engagement_bucket(profile).value,
        }

    def detect_churn_risk(self, player_id: str) -> Tuple[bool, str, float]:
        """Compute a 0..1 churn risk score for a player."""
        if not player_id:
            return False, "player_id is required", 0.0
        profile = self._profiles.get(player_id)
        if profile is None:
            return False, "profile not found", 0.0
        ok, _, risk = self._compute_churn_risk(profile)
        if not ok:
            return False, "could not compute churn risk", 0.0
        return True, "ok", round(risk, 4)

    def _compute_churn_risk(self, profile: EmotionProfile) -> Tuple[bool, str, float]:
        engagement = self._profile_engagement_bucket(profile)
        engagement_risk = self._engagement_risk(engagement)
        satisfaction_risk = 1.0 - _clamp(profile.satisfaction_score)
        sentiment_risk = _clamp((0.0 - profile.average_sentiment) / 2.0 + 0.5)
        frustration_factor = 0.0
        if profile.dominant_emotion in (EmotionCategory.FRUSTRATION, EmotionCategory.ANGER):
            frustration_factor = 0.8
        elif profile.dominant_emotion == EmotionCategory.DISAPPOINTMENT:
            frustration_factor = 0.5

        risk = (
            _CHURN_ENGAGEMENT_WEIGHT * engagement_risk
            + _CHURN_SATISFACTION_WEIGHT * satisfaction_risk
            + _CHURN_SENTIMENT_WEIGHT * sentiment_risk
            + _CHURN_FRUSTRATION_WEIGHT * frustration_factor
        )
        return True, "ok", _clamp(risk)

    def batch_analyze(
        self,
        player_ids: List[str],
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Run sentiment analysis across multiple players at once."""
        if not player_ids:
            return False, "player_ids list is empty", []
        results: List[Dict[str, Any]] = []
        for pid in player_ids:
            summary = self.get_sentiment_summary(pid)
            results.append(summary)
        return True, "success", results

    # ------------------------------------------------------------------
    # Event Log and Observability
    # ------------------------------------------------------------------

    def list_events(
        self,
        player_id: str = "",
        limit: int = 100,
    ) -> List[SentimentEvent]:
        cap = max(1, _safe_int(limit, 100))
        result: List[SentimentEvent] = []
        # Walk newest-first for a readable recent-activity feed.
        for e in reversed(self._events):
            if player_id and e.player_id != player_id:
                continue
            result.append(e)
            if len(result) >= cap:
                break
        return result

    def get_status(self) -> Dict[str, Any]:
        self._refresh_stats()
        return {
            "initialized": self._initialized,
            "profiles": len(self._profiles),
            "samples": len(self._samples),
            "frustration_events": len(self._frustration_events),
            "engagement_metrics": len(self._engagement_metrics),
            "interventions": len(self._interventions),
            "timelines": len(self._timelines),
            "events": len(self._events),
            "tick_count": self._tick_count,
            "config": self._config.to_dict(),
        }

    def get_stats(self) -> SentimentStats:
        self._refresh_stats()
        return self._stats

    def get_snapshot(self) -> SentimentSnapshot:
        self._refresh_stats()
        recent_samples = [
            s.to_dict() for s in list(self._samples.values())[-50:]
        ]
        frustration_events = [
            e.to_dict() for e in list(self._frustration_events.values())[-50:]
        ]
        interventions = [
            i.to_dict() for i in list(self._interventions.values())[-50:]
        ]
        return SentimentSnapshot(
            timestamp=_now(),
            profiles=[p.to_dict() for p in list(self._profiles.values())[-100:]],
            recent_samples=recent_samples,
            frustration_events=frustration_events,
            interventions=interventions,
            stats=self._stats.to_dict(),
        )

    def get_config(self) -> SentimentConfig:
        return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, SentimentConfig]:
        """Update tunable configuration fields.

        Only known fields on SentimentConfig are accepted. Numeric fields are
        coerced and clamped to safe ranges.
        """
        with self._init_lock:
            known = set(self._config.__dataclass_fields__.keys())
            applied: List[str] = []
            for key, value in kwargs.items():
                if key not in known or key == "metadata":
                    continue
                if key == "max_profiles":
                    self._config.max_profiles = max(1, _safe_int(value, 5000))
                elif key == "max_samples_per_player":
                    self._config.max_samples_per_player = max(1, _safe_int(value, 500))
                elif key == "max_frustration_events":
                    self._config.max_frustration_events = max(1, _safe_int(value, 10000))
                elif key == "analysis_window_minutes":
                    self._config.analysis_window_minutes = max(1, _safe_int(value, 60))
                elif key == "auto_intervention_enabled":
                    self._config.auto_intervention_enabled = bool(value)
                elif key == "frustration_threshold":
                    self._config.frustration_threshold = _clamp(_safe_float(value, 0.6))
                elif key == "churn_risk_threshold":
                    self._config.churn_risk_threshold = _clamp(_safe_float(value, 0.65))
                else:
                    continue
                applied.append(key)

            if not applied:
                return False, "no valid config fields supplied", self._config

            self._emit(
                "config_updated",
                player_id="",
                data={"fields": applied},
            )
            return True, "updated", self._config

    # ------------------------------------------------------------------
    # Tick and Lifecycle
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        """Advance the analyzer by one tick.

        Refreshes statistics, and when auto-intervention is enabled, scans
        profiles for high churn risk or frustration and generates suggestions
        for players that need attention.
        """
        with self._init_lock:
            self._tick_count += 1
            self._refresh_stats()

            auto_interventions: List[str] = []
            if self._config.auto_intervention_enabled:
                for player_id, profile in list(self._profiles.items()):
                    _, _, risk = self._compute_churn_risk(profile)
                    if risk >= self._config.churn_risk_threshold:
                        ok, _, suggestion = self.suggest_intervention(player_id)
                        if ok and suggestion is not None:
                            auto_interventions.append(suggestion.suggestion_id)

            self._emit(
                "tick",
                player_id="",
                data={"tick": self._tick_count,
                      "auto_interventions": auto_interventions},
            )
            return {
                "status": "ok",
                "tick": self._tick_count,
                "profiles": len(self._profiles),
                "samples": len(self._samples),
                "auto_interventions": auto_interventions,
                "stats": self._stats.to_dict(),
            }

    def reset(self) -> None:
        """Clear all analyzer state and re-seed the canonical dataset."""
        with self._init_lock:
            self._samples.clear()
            self._player_samples.clear()
            self._profiles.clear()
            self._frustration_events.clear()
            self._engagement_metrics.clear()
            self._player_engagement.clear()
            self._interventions.clear()
            self._timelines.clear()
            self._events.clear()
            self._config = SentimentConfig()
            self._stats = SentimentStats()
            self._tick_count = 0
            self._initialized = False
            self._seed()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the analyzer with a canonical set of sentiment data."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return

            base_time = datetime.utcnow()

            # ----------------------------------------------------------
            # Emotion Profiles (10)
            # ----------------------------------------------------------
            profile_seeds = [
                ("profile_player_001", "player_001", EmotionCategory.JOY,
                 0.72, TrendDirection.IMPROVING, TrendDirection.IMPROVING,
                 0.12, 0.86, {"segment": "whale", "region": "na_east"}),
                ("profile_player_002", "player_002", EmotionCategory.FRUSTRATION,
                 -0.42, TrendDirection.DECLINING, TrendDirection.DECLINING,
                 0.34, 0.33, {"segment": "regular", "region": "eu_west"}),
                ("profile_player_003", "player_003", EmotionCategory.EXCITEMENT,
                 0.61, TrendDirection.STABLE, TrendDirection.STABLE,
                 0.18, 0.74, {"segment": "regular", "region": "na_west"}),
                ("profile_player_004", "player_004", EmotionCategory.BOREDOM,
                 0.08, TrendDirection.DECLINING, TrendDirection.STABLE,
                 0.09, 0.44, {"segment": "casual", "region": "apac"}),
                ("profile_player_005", "player_005", EmotionCategory.ANGER,
                 -0.58, TrendDirection.DECLINING, TrendDirection.DECLINING,
                 0.41, 0.21, {"segment": "regular", "region": "na_east"}),
                ("profile_player_006", "player_006", EmotionCategory.SATISFACTION,
                 0.79, TrendDirection.IMPROVING, TrendDirection.IMPROVING,
                 0.07, 0.91, {"segment": "whale", "region": "eu_west"}),
                ("profile_player_007", "player_007", EmotionCategory.ANXIETY,
                 0.19, TrendDirection.STABLE, TrendDirection.DECLINING,
                 0.26, 0.55, {"segment": "regular", "region": "apac"}),
                ("profile_player_008", "player_008", EmotionCategory.CURIOSITY,
                 0.52, TrendDirection.IMPROVING, TrendDirection.STABLE,
                 0.15, 0.71, {"segment": "regular", "region": "na_west"}),
                ("profile_player_009", "player_009", EmotionCategory.DISAPPOINTMENT,
                 -0.31, TrendDirection.DECLINING, TrendDirection.STABLE,
                 0.22, 0.29, {"segment": "casual", "region": "na_east"}),
                ("profile_player_010", "player_010", EmotionCategory.PRIDE,
                 0.76, TrendDirection.IMPROVING, TrendDirection.IMPROVING,
                 0.11, 0.88, {"segment": "whale", "region": "eu_west"}),
            ]
            for (pid, player_id, dominant, avg_sent, eng_trend, frust_trend,
                 volatility, satisfaction, meta) in profile_seeds:
                profile = EmotionProfile(
                    profile_id=pid,
                    player_id=player_id,
                    dominant_emotion=dominant,
                    average_sentiment=avg_sent,
                    engagement_trend=eng_trend,
                    frustration_trend=frust_trend,
                    emotional_volatility=volatility,
                    satisfaction_score=satisfaction,
                    last_updated=_now(),
                    samples_count=0,
                    metadata=meta,
                )
                self._profiles[player_id] = profile

            # ----------------------------------------------------------
            # Sentiment Samples (22)
            # ----------------------------------------------------------
            sample_seeds = [
                # player_001 - joyful, engaged
                ("sample_001", "player_001", SentimentType.VERY_POSITIVE,
                 EmotionCategory.JOY, 0.85, EngagementLevel.HIGHLY_ENGAGED,
                 FrustrationLevel.NONE, DataSource.GAMEPLAY_TELEMETRY,
                 "sess_001", "Cleared a difficult raid boss on first attempt"),
                ("sample_002", "player_001", SentimentType.POSITIVE,
                 EmotionCategory.PRIDE, 0.72, EngagementLevel.HIGHLY_ENGAGED,
                 FrustrationLevel.NONE, DataSource.CHAT_LOG,
                 "sess_001", "Shared victory screenshot in guild chat"),
                ("sample_003", "player_001", SentimentType.POSITIVE,
                 EmotionCategory.SATISFACTION, 0.68, EngagementLevel.ENGAGED,
                 FrustrationLevel.LOW, DataSource.SURVEY,
                 "sess_002", "Rated the session 9/10 in post-session survey"),
                # player_002 - frustrated, declining
                ("sample_004", "player_002", SentimentType.NEGATIVE,
                 EmotionCategory.FRUSTRATION, -0.45, EngagementLevel.DISENGAGED,
                 FrustrationLevel.HIGH, DataSource.GAMEPLAY_TELEMETRY,
                 "sess_010", "Wiped 8 times on the same encounter"),
                ("sample_005", "player_002", SentimentType.VERY_NEGATIVE,
                 EmotionCategory.ANGER, -0.78, EngagementLevel.CHURN_RISK,
                 FrustrationLevel.SEVERE, DataSource.CHAT_LOG,
                 "sess_010", "Typed aggressive messages after a loss"),
                ("sample_006", "player_002", SentimentType.NEGATIVE,
                 EmotionCategory.DISAPPOINTMENT, -0.38, EngagementLevel.DISENGAGED,
                 FrustrationLevel.MODERATE, DataSource.BEHAVIORAL_PATTERN,
                 "sess_011", "Abandoned the session after 6 minutes"),
                # player_003 - excited, stable
                ("sample_007", "player_003", SentimentType.POSITIVE,
                 EmotionCategory.EXCITEMENT, 0.66, EngagementLevel.ENGAGED,
                 FrustrationLevel.LOW, DataSource.GAMEPLAY_TELEMETRY,
                 "sess_020", "Unlocked a rare cosmetic drop"),
                ("sample_008", "player_003", SentimentType.POSITIVE,
                 EmotionCategory.CURIOSITY, 0.54, EngagementLevel.ENGAGED,
                 FrustrationLevel.NONE, DataSource.SESSION_DURATION,
                 "sess_020", "Explored a new map region for 40 minutes"),
                # player_004 - bored, declining
                ("sample_009", "player_004", SentimentType.NEUTRAL,
                 EmotionCategory.BOREDOM, 0.05, EngagementLevel.NEUTRAL,
                 FrustrationLevel.LOW, DataSource.SESSION_DURATION,
                 "sess_030", "Idle in hub for 25 minutes"),
                ("sample_010", "player_004", SentimentType.MIXED,
                 EmotionCategory.CONFUSION, 0.12, EngagementLevel.NEUTRAL,
                 FrustrationLevel.MODERATE, DataSource.BEHAVIORAL_PATTERN,
                 "sess_031", "Repeatedly failed a tutorial-adjacent puzzle"),
                # player_005 - angry, churn risk
                ("sample_011", "player_005", SentimentType.VERY_NEGATIVE,
                 EmotionCategory.ANGER, -0.72, EngagementLevel.CHURN_RISK,
                 FrustrationLevel.SEVERE, DataSource.CHAT_LOG,
                 "sess_040", "Reported for abusive language"),
                ("sample_012", "player_005", SentimentType.NEGATIVE,
                 EmotionCategory.FRUSTRATION, -0.5, EngagementLevel.DISENGAGED,
                 FrustrationLevel.HIGH, DataSource.GAMEPLAY_TELEMETRY,
                 "sess_040", "Lost 5 ranked matches in a row"),
                ("sample_013", "player_005", SentimentType.NEGATIVE,
                 EmotionCategory.DISAPPOINTMENT, -0.44, EngagementLevel.DISENGAGED,
                 FrustrationLevel.HIGH, DataSource.PURCHASE_BEHAVIOR,
                 "sess_041", "Requested a refund for a recent purchase"),
                # player_006 - satisfied, highly engaged
                ("sample_014", "player_006", SentimentType.VERY_POSITIVE,
                 EmotionCategory.SATISFACTION, 0.88, EngagementLevel.HIGHLY_ENGAGED,
                 FrustrationLevel.NONE, DataSource.SURVEY,
                 "sess_050", "Rated the season 10/10"),
                ("sample_015", "player_006", SentimentType.POSITIVE,
                 EmotionCategory.PRIDE, 0.74, EngagementLevel.HIGHLY_ENGAGED,
                 FrustrationLevel.NONE, DataSource.GAMEPLAY_TELEMETRY,
                 "sess_050", "Reached the top of the weekly leaderboard"),
                # player_007 - anxious
                ("sample_016", "player_007", SentimentType.NEUTRAL,
                 EmotionCategory.ANXIETY, 0.16, EngagementLevel.ENGAGED,
                 FrustrationLevel.MODERATE, DataSource.CHAT_LOG,
                 "sess_060", "Asked teammates whether performance was acceptable"),
                ("sample_017", "player_007", SentimentType.MIXED,
                 EmotionCategory.CURIOSITY, 0.22, EngagementLevel.ENGAGED,
                 FrustrationLevel.LOW, DataSource.SESSION_DURATION,
                 "sess_060", "Tried a new build but hesitated frequently"),
                # player_008 - curious
                ("sample_018", "player_008", SentimentType.POSITIVE,
                 EmotionCategory.CURIOSITY, 0.58, EngagementLevel.ENGAGED,
                 FrustrationLevel.NONE, DataSource.BEHAVIORAL_PATTERN,
                 "sess_070", "Tested multiple weapon combinations"),
                ("sample_019", "player_008", SentimentType.POSITIVE,
                 EmotionCategory.EXCITEMENT, 0.62, EngagementLevel.ENGAGED,
                 FrustrationLevel.LOW, DataSource.GAMEPLAY_TELEMETRY,
                 "sess_070", "Discovered a hidden area"),
                # player_009 - disappointed
                ("sample_020", "player_009", SentimentType.NEGATIVE,
                 EmotionCategory.DISAPPOINTMENT, -0.34, EngagementLevel.DISENGAGED,
                 FrustrationLevel.MODERATE, DataSource.SURVEY,
                 "sess_080", "Felt the reward did not match the effort"),
                # player_010 - pride
                ("sample_021", "player_010", SentimentType.VERY_POSITIVE,
                 EmotionCategory.PRIDE, 0.82, EngagementLevel.HIGHLY_ENGAGED,
                 FrustrationLevel.NONE, DataSource.GAMEPLAY_TELEMETRY,
                 "sess_090", "Completed a prestige achievement"),
                ("sample_022", "player_010", SentimentType.POSITIVE,
                 EmotionCategory.RELIEF, 0.64, EngagementLevel.ENGAGED,
                 FrustrationLevel.LOW, DataSource.SOCIAL_INTERACTION,
                 "sess_090", "Received congratulations from guildmates"),
            ]
            for idx, (sid, pid, st, ec, score, el, fl, ds, sess, ctx) in enumerate(sample_seeds):
                ts = (base_time - timedelta(minutes=len(sample_seeds) - idx)).isoformat() + "Z"
                sample = SentimentSample(
                    sample_id=sid,
                    player_id=pid,
                    timestamp=ts,
                    sentiment_type=st,
                    emotion_category=ec,
                    sentiment_score=score,
                    engagement_level=el,
                    frustration_level=fl,
                    data_source=ds,
                    session_id=sess,
                    context=ctx,
                    metadata={"seed": True},
                )
                self._samples[sid] = sample
                self._player_samples.setdefault(pid, []).append(sid)

            # Recompute every seeded profile so aggregates reflect samples.
            for pid in list(self._profiles.keys()):
                self._recompute_profile(pid)

            # ----------------------------------------------------------
            # Frustration Events (5)
            # ----------------------------------------------------------
            frustration_seeds = [
                ("frust_event_001", "player_002", FrustrationLevel.HIGH,
                 "repeated_wipe", "Wiped 8 times on the same encounter",
                 420.0, "raid_boss_3", False),
                ("frust_event_002", "player_005", FrustrationLevel.SEVERE,
                 "losing_streak", "Lost 5 ranked matches in a row",
                 1800.0, "ranked_pvp", False),
                ("frust_event_003", "player_004", FrustrationLevel.MODERATE,
                 "puzzle_block", "Could not solve a tutorial-adjacent puzzle",
                 300.0, "puzzle_room_2", True),
                ("frust_event_004", "player_007", FrustrationLevel.MODERATE,
                 "social_pressure", "Felt judged by teammates during voice chat",
                 240.0, "team_dungeon", False),
                ("frust_event_005", "player_009", FrustrationLevel.LOW,
                 "reward_mismatch", "Reward felt disproportionate to effort",
                 90.0, "weekly_quest", True),
            ]
            for eid, pid, fl, trig, desc, dur, ctx, resolved in frustration_seeds:
                event = FrustrationEvent(
                    event_id=eid,
                    player_id=pid,
                    timestamp=_now(),
                    frustration_level=fl,
                    trigger_type=trig,
                    trigger_description=desc,
                    duration_seconds=dur,
                    context=ctx,
                    resolved=resolved,
                    metadata={"seed": True},
                )
                self._frustration_events[eid] = event

            # ----------------------------------------------------------
            # Engagement Metrics (5)
            # ----------------------------------------------------------
            engagement_seeds = [
                ("metric_001", "player_001", EngagementLevel.HIGHLY_ENGAGED,
                 92.0, 48.0, 12, 0.78, 0.82),
                ("metric_002", "player_002", EngagementLevel.DISENGAGED,
                 6.0, 8.0, 0, 0.12, 0.05),
                ("metric_003", "player_003", EngagementLevel.ENGAGED,
                 64.0, 35.0, 6, 0.66, 0.58),
                ("metric_004", "player_005", EngagementLevel.CHURN_RISK,
                 18.0, 22.0, 1, 0.08, 0.02),
                ("metric_005", "player_006", EngagementLevel.HIGHLY_ENGAGED,
                 110.0, 52.0, 15, 0.84, 0.88),
            ]
            for mid, pid, el, dur, apm, social, explore, prog in engagement_seeds:
                metric = EngagementMetric(
                    metric_id=mid,
                    player_id=pid,
                    timestamp=_now(),
                    engagement_level=el,
                    session_duration=dur,
                    actions_per_minute=apm,
                    social_interactions=social,
                    exploration_score=explore,
                    progression_rate=prog,
                    metadata={"seed": True},
                )
                self._engagement_metrics[mid] = metric
                self._player_engagement.setdefault(pid, []).append(mid)

            # ----------------------------------------------------------
            # Intervention Suggestions (5)
            # ----------------------------------------------------------
            intervention_seeds = [
                ("sug_001", "player_002", InterventionType.DIFFICULTY_ADJUSTMENT,
                 "critical", "Severe frustration from repeated wipes; lower "
                 "encounter difficulty to restore progress.",
                 "Lower frustration and reduce session abandonment.",
                 "frustration_level"),
                ("sug_002", "player_005", InterventionType.BREAK_SUGGESTION,
                 "high", "Anger and losing streak detected; suggest a short "
                 "break to defuse tension.",
                 "Protect well-being and reduce toxic interactions.",
                 "satisfaction_score"),
                ("sug_003", "player_004", InterventionType.CONTENT_SUGGESTION,
                 "medium", "Boredom is dominant; introduce variety or new "
                 "objectives.",
                 "Restore novelty and lift engagement.",
                 "engagement_level"),
                ("sug_004", "player_007", InterventionType.SOCIAL_NUDGE,
                 "medium", "Anxiety around social judgment; nudge toward "
                 "lower-pressure cooperative content.",
                 "Reduce anxiety and strengthen social ties.",
                 "social_interactions"),
                ("sug_005", "player_001", InterventionType.REWARD_GRANT,
                 "low", "Highly positive state; grant a small reward to "
                 "reinforce continued engagement.",
                 "Reinforce positive feedback loop.",
                 "engagement_level"),
            ]
            for sid, pid, it, priority, reason, impact, target in intervention_seeds:
                suggestion = InterventionSuggestion(
                    suggestion_id=sid,
                    player_id=pid,
                    timestamp=_now(),
                    intervention_type=it,
                    priority=priority,
                    reason=reason,
                    expected_impact=impact,
                    target_metric=target,
                    metadata={"seed": True},
                )
                self._interventions[sid] = suggestion

            # ----------------------------------------------------------
            # Sentiment Timelines (3)
            # ----------------------------------------------------------
            timeline_players = ["player_001", "player_002", "player_005"]
            for idx, pid in enumerate(timeline_players):
                player_samples = self._player_sample_list(pid)
                if not player_samples:
                    continue
                player_samples.sort(key=lambda x: x.timestamp)
                scores = [s.sentiment_score for s in player_samples]
                emotion_counts: Dict[EmotionCategory, int] = {}
                for s in player_samples:
                    emotion_counts[s.emotion_category] = emotion_counts.get(s.emotion_category, 0) + 1
                peak = max(emotion_counts, key=lambda k: emotion_counts[k])
                lowest = min(emotion_counts, key=lambda k: emotion_counts[k])
                timeline = SentimentTimeline(
                    timeline_id=f"timeline_{idx + 1:03d}",
                    player_id=pid,
                    samples=[s.to_dict() for s in player_samples],
                    trend_direction=TrendDirection.STABLE,
                    average_score=round(_mean(scores), 4),
                    peak_emotion=peak,
                    lowest_emotion=lowest,
                    period_start=player_samples[0].timestamp,
                    period_end=player_samples[-1].timestamp,
                    metadata={"seed": True, "sample_count": len(player_samples)},
                )
                self._timelines[timeline.timeline_id] = timeline

            self._refresh_stats()
            self._emit(
                "analyzer_seeded",
                player_id="",
                data={
                    "profiles": len(self._profiles),
                    "samples": len(self._samples),
                    "frustration_events": len(self._frustration_events),
                    "engagement_metrics": len(self._engagement_metrics),
                    "interventions": len(self._interventions),
                    "timelines": len(self._timelines),
                },
            )
            self._initialized = True


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_player_sentiment_analyzer() -> PlayerSentimentAnalyzer:
    """Return the shared PlayerSentimentAnalyzer singleton instance."""
    return PlayerSentimentAnalyzer.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "SentimentType",
    "EmotionCategory",
    "EngagementLevel",
    "FrustrationLevel",
    "DataSource",
    "InterventionType",
    "TrendDirection",
    # Data classes
    "SentimentSample",
    "EmotionProfile",
    "FrustrationEvent",
    "EngagementMetric",
    "InterventionSuggestion",
    "SentimentTimeline",
    "SentimentConfig",
    "SentimentStats",
    "SentimentSnapshot",
    "SentimentEvent",
    # Main system
    "PlayerSentimentAnalyzer",
    "get_player_sentiment_analyzer",
]
