"""
SparkLabs Agent - Learning Analytics Engine

This module implements a formal learning-analytics engine for AI agents
operating inside the SparkLabs AI-native game engine. It is intentionally
distinct from sibling modules:

  - ``agent_meta_learner.py`` is concerned with meta-learning *algorithms*
    (learning-to-learn hyperparameter adaptation).
  - ``agent_interaction_loop.py`` simply persists a flat reward list for
    reinforcement-style bookkeeping.

The engine exposed here provides formal learning analytics that game
designers, curriculum authors, and AI behaviour authors can use to track
*what* an agent knows, *how well* it knows it, and *how fast* it is
acquiring new competence. Concretely, it offers:

  1. Knowledge Tracing
       Each ``KnowledgeUnit`` is a single concept or skill an agent has
       encountered. The unit carries a discrete ``KnowledgeState`` (UNKNOWN
       -> INTRODUCED -> PRACTICED -> FAMILIAR -> PROFICIENT -> MASTERED)
       and a discrete ``MasteryLevel`` (NOVICE -> EXPERT). Practice sessions
       update the unit's state and level automatically.

  2. Learning Curve Analysis
       Per-unit :class:`LearningCurve` records a time series of mastery
       observations. The engine fits a simple linear-regression slope to
       the curve, classifies the trajectory as IMPROVING, STABLE, or
       DECLINING, and detects plateaus (slope magnitude below a small
       epsilon) automatically.

  3. Mastery Tracking and Reporting
       Mastery score is a weighted blend of (a) practice volume, (b)
       historical success rate, and (c) retention. Reports roll up all of
       an agent's units into distribution maps and a list of recommended
       knowledge gaps.

  4. Learning Velocity
       ``compute_learning_velocity`` measures the rate at which an agent
       transitions units into the PROFICIENT or MASTERED state per session.

  5. Spaced-Repetition Style Review Scheduling
       Reviews are scheduled with a simplified SuperMemo/SM-2 style
       ``ease_factor`` and ``repetitions`` counter. ``due_reviews`` returns
       the schedules that are now eligible for review.

  6. Forgetting Detection
       If a unit's last practice is older than a configurable threshold
       and its retention score has dropped below 0.5, the engine flags it
       as forgotten.

Architecture:
  LearningAnalyticsEngine (Singleton, double-checked locking with threading.RLock)
    |-- KnowledgeUnit
    |-- PracticeSession
    |-- LearningCurve / LearningCurvePoint
    |-- KnowledgeReport
    |-- LearningInsight
    |-- ReviewSchedule
    |-- LearningStats
    |-- LearningAnalyticsSnapshot
    |-- LearningAnalyticsEvent

All public mutating methods are protected by a re-entrant lock so the
engine is safe to call from multiple agent threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import math
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_UNITS: int = 5000
_MAX_SESSIONS: int = 10000
_MAX_CURVES: int = 5000
_MAX_REPORTS: int = 1000
_MAX_INSIGHTS: int = 2000
_MAX_SCHEDULES: int = 5000
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Algorithm constants
# ---------------------------------------------------------------------------

# Mastery-score blend weights (must sum to 1.0).
_PRACTICE_WEIGHT: float = 0.30
_SUCCESS_WEIGHT: float = 0.45
_RETENTION_WEIGHT: float = 0.25

# Success-rate smoothing prior: success_count + prior / practice_count + 2*prior
_SUCCESS_RATE_PRIOR: float = 1.0

# A score above this is considered a learning "success" transition.
_MASTERY_THRESHOLD: float = 0.85

# Plateau detection epsilon: |slope| below this is considered flat.
_PLATEAU_SLOPE_EPSILON: float = 0.01

# Forgetting detection thresholds.
_FORGETTING_AGE_HOURS: float = 168.0  # 7 days
_FORGETTING_RETENTION_CUTOFF: float = 0.5

# Default spaced-repetition parameters.
_DEFAULT_INTERVAL_HOURS: float = 24.0
_DEFAULT_EASE_FACTOR: float = 2.5
_MIN_EASE_FACTOR: float = 1.3
_MAX_EASE_FACTOR: float = 4.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Generate a short unique identifier for a record."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _hours_ago_timestamp(hours: float) -> str:
    """Return an ISO-8601 timestamp for the given number of hours in the past."""
    dt = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    return dt.isoformat() + "Z"


def _parse_timestamp(value: str) -> Optional[datetime.datetime]:
    """Parse an ISO-8601 timestamp string into a datetime object.

    Returns ``None`` if the value cannot be parsed.
    """
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "")
        return datetime.datetime.fromisoformat(cleaned)
    except (ValueError, TypeError, AttributeError):
        return None


def _hours_between(start: str, end: str) -> Optional[float]:
    """Return the number of hours between two ISO-8601 timestamp strings.

    Returns ``None`` if either value cannot be parsed.
    """
    start_dt = _parse_timestamp(start)
    end_dt = _parse_timestamp(end)
    if start_dt is None or end_dt is None:
        return None
    delta = (end_dt - start_dt).total_seconds() / 3600.0
    return max(0.0, delta)


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key returned
    by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    while len(store) > max_size:
        store.pop(0)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class KnowledgeState(Enum):
    """Discrete knowledge states along a learner's progress curve.

    The ordering is meaningful: states are intended to advance from UNKNOWN
    through INTRODUCED, PRACTICED, FAMILIAR, PROFICIENT, to MASTERED, but
    the engine permits regressive transitions when retention collapses.
    """
    UNKNOWN = "unknown"
    INTRODUCED = "introduced"
    PRACTICED = "practiced"
    FAMILIAR = "familiar"
    PROFICIENT = "proficient"
    MASTERED = "mastered"


class LearningPhase(Enum):
    """The high-level pedagogical phase an agent is in for a unit."""
    INTAKE = "intake"
    PRACTICE = "practice"
    APPLICATION = "application"
    MASTERY = "mastery"
    RETENTION = "retention"


class MasteryLevel(Enum):
    """Discrete mastery bands derived from a continuous mastery score."""
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class TrendDirection(Enum):
    """Direction of a learning curve's fitted slope."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class MetricType(Enum):
    """Metric categories emitted by the learning analytics engine."""
    LEARNING_VELOCITY = "learning_velocity"
    RETENTION_RATE = "retention_rate"
    MASTERY_SCORE = "mastery_score"
    FORGETTING_RATE = "forgetting_rate"
    TRANSFER_RATE = "transfer_rate"


class LearningEventKind(Enum):
    """Observable lifecycle events emitted by the learning analytics engine."""
    SESSION_STARTED = "session_started"
    CONCEPT_LEARNED = "concept_learned"
    PRACTICE_RECORDED = "practice_recorded"
    MASTERY_UPDATED = "mastery_updated"
    REVIEW_SCHEDULED = "review_scheduled"
    FORGETTING_DETECTED = "forgetting_detected"
    INSIGHT_GENERATED = "insight_generated"
    REPORT_GENERATED = "report_generated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeUnit:
    """A single concept or skill an agent has encountered."""
    unit_id: str
    agent_id: str
    concept: str
    knowledge_state: KnowledgeState
    mastery_level: MasteryLevel
    first_seen: str
    last_practiced: str
    practice_count: int
    success_count: int
    retention_score: float
    mastery_score: float = 0.0
    learning_phase: LearningPhase = LearningPhase.INTAKE
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this knowledge unit to a JSON-friendly dictionary."""
        return {
            "unit_id": self.unit_id,
            "agent_id": self.agent_id,
            "concept": self.concept,
            "knowledge_state": self.knowledge_state.value,
            "mastery_level": self.mastery_level.value,
            "first_seen": self.first_seen,
            "last_practiced": self.last_practiced,
            "practice_count": self.practice_count,
            "success_count": self.success_count,
            "retention_score": self.retention_score,
            "mastery_score": self.mastery_score,
            "learning_phase": self.learning_phase.value,
            "description": self.description,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class PracticeSession:
    """A single recorded practice attempt for a knowledge unit."""
    session_id: str
    agent_id: str
    unit_id: str
    started_at: str
    ended_at: str
    attempts: int
    successes: int
    hints_used: int
    duration_seconds: int
    score: float
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this practice session to a JSON-friendly dictionary."""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "unit_id": self.unit_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "attempts": self.attempts,
            "successes": self.successes,
            "hints_used": self.hints_used,
            "duration_seconds": self.duration_seconds,
            "score": self.score,
            "notes": self.notes,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class LearningCurvePoint:
    """A single time-indexed point on a learning curve."""
    point_id: str
    agent_id: str
    unit_id: str
    session_index: int
    mastery_score: float
    timestamp: str
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this curve point to a JSON-friendly dictionary."""
        return {
            "point_id": self.point_id,
            "agent_id": self.agent_id,
            "unit_id": self.unit_id,
            "session_index": self.session_index,
            "mastery_score": self.mastery_score,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class LearningCurve:
    """A fitted learning curve for a knowledge unit."""
    curve_id: str
    agent_id: str
    unit_id: str
    points: List[LearningCurvePoint]
    trend: TrendDirection
    slope: float
    plateau_detected: bool
    fit_r_squared: float
    concept: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this learning curve to a JSON-friendly dictionary."""
        return {
            "curve_id": self.curve_id,
            "agent_id": self.agent_id,
            "unit_id": self.unit_id,
            "points": [p.to_dict() for p in self.points],
            "trend": self.trend.value,
            "slope": self.slope,
            "plateau_detected": self.plateau_detected,
            "fit_r_squared": self.fit_r_squared,
            "concept": self.concept,
            "updated_at": self.updated_at,
        }


@dataclass
class KnowledgeReport:
    """A roll-up report of an agent's learning analytics."""
    report_id: str
    agent_id: str
    total_units: int
    by_state: Dict[str, int]
    by_level: Dict[str, int]
    average_mastery: float
    knowledge_gaps: List[str]
    recommendations: List[str]
    generated_at: str
    average_velocity: float = 0.0
    average_retention: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this knowledge report to a JSON-friendly dictionary."""
        return {
            "report_id": self.report_id,
            "agent_id": self.agent_id,
            "total_units": self.total_units,
            "by_state": dict(self.by_state),
            "by_level": dict(self.by_level),
            "average_mastery": self.average_mastery,
            "knowledge_gaps": list(self.knowledge_gaps),
            "recommendations": list(self.recommendations),
            "generated_at": self.generated_at,
            "average_velocity": self.average_velocity,
            "average_retention": self.average_retention,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class LearningInsight:
    """A synthesised insight describing a notable learning pattern."""
    insight_id: str
    agent_id: str
    kind: str
    description: str
    related_units: List[str]
    confidence: float
    created_at: str
    metric_type: MetricType = MetricType.MASTERY_SCORE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this learning insight to a JSON-friendly dictionary."""
        return {
            "insight_id": self.insight_id,
            "agent_id": self.agent_id,
            "kind": self.kind,
            "description": self.description,
            "related_units": list(self.related_units),
            "confidence": self.confidence,
            "created_at": self.created_at,
            "metric_type": self.metric_type.value,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class ReviewSchedule:
    """A spaced-repetition review schedule for a knowledge unit."""
    schedule_id: str
    agent_id: str
    unit_id: str
    next_review_at: str
    interval_hours: float
    ease_factor: float
    repetitions: int
    last_reviewed_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this review schedule to a JSON-friendly dictionary."""
        return {
            "schedule_id": self.schedule_id,
            "agent_id": self.agent_id,
            "unit_id": self.unit_id,
            "next_review_at": self.next_review_at,
            "interval_hours": self.interval_hours,
            "ease_factor": self.ease_factor,
            "repetitions": self.repetitions,
            "last_reviewed_at": self.last_reviewed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class LearningStats:
    """Aggregate statistics about the learning analytics engine."""
    total_agents: int
    total_units: int
    total_sessions: int
    total_insights: int
    average_mastery: float
    mastery_distribution: Dict[str, int]
    state_distribution: Dict[str, int] = field(default_factory=dict)
    total_reports: int = 0
    total_schedules: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_agents": self.total_agents,
            "total_units": self.total_units,
            "total_sessions": self.total_sessions,
            "total_insights": self.total_insights,
            "average_mastery": self.average_mastery,
            "mastery_distribution": dict(self.mastery_distribution),
            "state_distribution": dict(self.state_distribution),
            "total_reports": self.total_reports,
            "total_schedules": self.total_schedules,
        }


@dataclass
class LearningAnalyticsSnapshot:
    """A complete snapshot of the learning analytics engine state."""
    initialized: bool
    units: List[KnowledgeUnit]
    sessions: List[PracticeSession]
    curves: List[LearningCurve]
    reports: List[KnowledgeReport]
    insights: List[LearningInsight]
    schedules: List[ReviewSchedule]
    events: List["LearningAnalyticsEvent"]
    stats: LearningStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "units": [u.to_dict() for u in self.units],
            "sessions": [s.to_dict() for s in self.sessions],
            "curves": [c.to_dict() for c in self.curves],
            "reports": [r.to_dict() for r in self.reports],
            "insights": [i.to_dict() for i in self.insights],
            "schedules": [s.to_dict() for s in self.schedules],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class LearningAnalyticsEvent:
    """An observable lifecycle event emitted by the learning analytics engine."""
    event_id: str
    kind: LearningEventKind
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


# ---------------------------------------------------------------------------
# Learning Analytics Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------


class LearningAnalyticsEngine:
    """Formal learning analytics engine for AI game agents.

    The engine tracks per-agent knowledge units, practice sessions, learning
    curves, mastery levels, retention scores, spaced-repetition review
    schedules, and synthesised insights. It is a thread-safe singleton
    accessed via :meth:`get_instance` or the module-level
    :func:`get_learning_analytics` helper.

    Usage:
        engine = get_learning_analytics()
        unit = engine.register_unit("agent_alpha", "combat")
        engine.record_practice("agent_alpha", unit.unit_id,
                               attempts=5, successes=4, hints_used=1)
        engine.record_curve_point("agent_alpha", unit.unit_id, 0.65)
        curve = engine.compute_curve_trend("agent_alpha", unit.unit_id)
        report = engine.generate_report("agent_alpha")
    """

    _instance: Optional["LearningAnalyticsEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # -- Construction (double-checked locking) -----------------------------

    def __new__(cls) -> "LearningAnalyticsEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        # Fast path: already initialized singleton.
        if self._initialized:
            return
        with self._lock:
            # Second check inside the lock to guard against concurrent
            # construction.
            if self._initialized:
                return

            # Primary stores keyed by id where it makes sense; lists where
            # ordering matters.
            self._units: Dict[str, KnowledgeUnit] = {}
            self._sessions: Dict[str, PracticeSession] = {}
            self._curves: Dict[str, LearningCurve] = {}
            self._reports: Dict[str, KnowledgeReport] = {}
            self._insights: Dict[str, LearningInsight] = {}
            self._schedules: Dict[str, ReviewSchedule] = {}
            self._events: List[LearningAnalyticsEvent] = []

            # Auxiliary lookup tables for fast per-agent access.
            self._units_by_agent: Dict[str, List[str]] = {}
            self._sessions_by_agent: Dict[str, List[str]] = {}
            self._curves_by_agent: Dict[str, List[str]] = {}
            self._insights_by_agent: Dict[str, List[str]] = {}
            self._schedules_by_agent: Dict[str, List[str]] = {}
            self._reports_by_agent: Dict[str, List[str]] = {}

            # Track known agents for stats.
            self._known_agents: Set[str] = set()

            # Aggregate counters.
            self._unit_counter: int = 0
            self._session_counter: int = 0
            self._curve_counter: int = 0
            self._point_counter: int = 0
            self._report_counter: int = 0
            self._insight_counter: int = 0
            self._schedule_counter: int = 0

            self._initialized: bool = True

            # Seed baseline learning analytics data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "LearningAnalyticsEngine":
        """Return the singleton LearningAnalyticsEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Knowledge Unit management
    # ------------------------------------------------------------------

    def register_unit(self, agent_id: str, concept: str,
                      description: str = "") -> KnowledgeUnit:
        """Create or re-fetch a knowledge unit for an agent and concept.

        If the (agent_id, concept) pair already has a unit, the existing
        unit is returned unchanged. Otherwise a new unit is created in the
        INTRODUCED state with a fresh identifier, current timestamp, and an
        initial mastery score of zero.

        Args:
            agent_id: Identifier of the agent learning the concept.
            concept: Short, canonical name of the concept or skill.
            description: Optional free-form description of the concept.

        Returns:
            The :class:`KnowledgeUnit` for the (agent, concept) pair.
        """
        with self._lock:
            self._known_agents.add(agent_id)
            for existing in self._units.values():
                if existing.agent_id == agent_id and existing.concept == concept:
                    return existing
            now = _now()
            unit = KnowledgeUnit(
                unit_id=_new_id(),
                agent_id=agent_id,
                concept=concept,
                knowledge_state=KnowledgeState.INTRODUCED,
                mastery_level=MasteryLevel.NOVICE,
                first_seen=now,
                last_practiced=now,
                practice_count=0,
                success_count=0,
                retention_score=1.0,
                mastery_score=0.0,
                learning_phase=LearningPhase.INTAKE,
                description=description or "",
            )
            return self._ingest_unit(unit)

    def _ingest_unit(self, unit: KnowledgeUnit) -> KnowledgeUnit:
        """Store a constructed unit and update derived state.

        Assumes the caller already holds ``self._lock``.
        """
        self._units[unit.unit_id] = unit
        self._unit_counter += 1
        self._units_by_agent.setdefault(unit.agent_id, []).append(unit.unit_id)
        _evict_fifo_dict(self._units, _MAX_UNITS)
        self._record_event(
            LearningEventKind.CONCEPT_LEARNED,
            {
                "agent_id": unit.agent_id,
                "unit_id": unit.unit_id,
                "concept": unit.concept,
                "knowledge_state": unit.knowledge_state.value,
            },
        )
        return unit

    def get_unit(self, agent_id: str, unit_id: str) -> Optional[KnowledgeUnit]:
        """Return a knowledge unit by id, or None if not found."""
        with self._lock:
            unit = self._units.get(unit_id)
            if unit is None or unit.agent_id != agent_id:
                return None
            return unit

    def list_units(
        self,
        agent_id: str,
        knowledge_state: Optional[KnowledgeState] = None,
        mastery_level: Optional[MasteryLevel] = None,
    ) -> List[KnowledgeUnit]:
        """List knowledge units for an agent, optionally filtered."""
        with self._lock:
            results: List[KnowledgeUnit] = []
            for uid in self._units_by_agent.get(agent_id, []):
                unit = self._units.get(uid)
                if unit is None:
                    continue
                if knowledge_state is not None and unit.knowledge_state != knowledge_state:
                    continue
                if mastery_level is not None and unit.mastery_level != mastery_level:
                    continue
                results.append(unit)
            return results

    def update_unit(self, agent_id: str, unit_id: str,
                    **kwargs: Any) -> Optional[KnowledgeUnit]:
        """Update fields on a knowledge unit.

        Supported keyword arguments mirror the dataclass fields (excluding
        ``unit_id`` and ``agent_id``, which are immutable). Unknown keys
        are ignored. After updates, mastery and state/level are recomputed
        automatically.

        Returns:
            The updated :class:`KnowledgeUnit`, or ``None`` if not found.
        """
        with self._lock:
            unit = self._units.get(unit_id)
            if unit is None or unit.agent_id != agent_id:
                return None
            for key, value in kwargs.items():
                if key in ("unit_id", "agent_id"):
                    continue
                if not hasattr(unit, key):
                    continue
                setattr(unit, key, value)
            # Recompute derived fields.
            self._recompute_unit_state(unit)
            self._record_event(
                LearningEventKind.MASTERY_UPDATED,
                {
                    "agent_id": agent_id,
                    "unit_id": unit_id,
                    "knowledge_state": unit.knowledge_state.value,
                    "mastery_level": unit.mastery_level.value,
                    "mastery_score": unit.mastery_score,
                },
            )
            return unit

    # ------------------------------------------------------------------
    # Practice session recording
    # ------------------------------------------------------------------

    def record_practice(
        self,
        agent_id: str,
        unit_id: str,
        attempts: int = 1,
        successes: int = 1,
        hints_used: int = 0,
        duration_seconds: int = 60,
        notes: str = "",
    ) -> Optional[PracticeSession]:
        """Record a practice session and update the underlying knowledge unit.

        Args:
            agent_id: Identifier of the practising agent.
            unit_id: Identifier of the knowledge unit being practised.
            attempts: Number of attempts the agent made during the session.
            successes: Number of successful attempts.
            hints_used: Number of hints surfaced to the agent.
            duration_seconds: Wall-clock duration of the practice session.
            notes: Optional free-form notes about the session.

        Returns:
            The newly created :class:`PracticeSession`, or ``None`` if the
            unit does not exist for this agent.
        """
        with self._lock:
            unit = self._units.get(unit_id)
            if unit is None or unit.agent_id != agent_id:
                return None
            attempts_i = max(0, int(attempts))
            successes_i = max(0, min(int(successes), attempts_i if attempts_i > 0 else int(successes)))
            hints_i = max(0, int(hints_used))
            duration_i = max(0, int(duration_seconds))
            now = _now()
            # Session score is success-rate blended with a hint penalty.
            if attempts_i > 0:
                raw_score = successes_i / attempts_i
            else:
                raw_score = 0.0
            hint_penalty = min(0.5, 0.05 * hints_i)
            score = _clamp(raw_score - hint_penalty, 0.0, 1.0)
            session = PracticeSession(
                session_id=_new_id(),
                agent_id=agent_id,
                unit_id=unit_id,
                started_at=now,
                ended_at=now,
                attempts=attempts_i,
                successes=successes_i,
                hints_used=hints_i,
                duration_seconds=duration_i,
                score=round(score, 4),
                notes=notes or "",
            )
            self._sessions[session.session_id] = session
            self._session_counter += 1
            self._sessions_by_agent.setdefault(agent_id, []).append(session.session_id)
            _evict_fifo_dict(self._sessions, _MAX_SESSIONS)

            # Update the underlying unit.
            unit.practice_count += attempts_i
            unit.success_count += successes_i
            unit.last_practiced = now
            self._recompute_unit_state(unit)

            # If forgetting was previously detected, clear the unit's
            # "forgetting" metadata flag if the new score is high.
            if unit.metadata.get("forgetting_detected") and unit.retention_score >= 0.5:
                unit.metadata.pop("forgetting_detected", None)

            self._record_event(
                LearningEventKind.PRACTICE_RECORDED,
                {
                    "agent_id": agent_id,
                    "unit_id": unit_id,
                    "session_id": session.session_id,
                    "attempts": attempts_i,
                    "successes": successes_i,
                    "score": session.score,
                },
            )
            return session

    def list_sessions(
        self,
        agent_id: str,
        unit_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[PracticeSession]:
        """List practice sessions for an agent, newest first."""
        with self._lock:
            n = max(0, int(limit))
            results: List[PracticeSession] = []
            for sid in reversed(self._sessions_by_agent.get(agent_id, [])):
                session = self._sessions.get(sid)
                if session is None:
                    continue
                if unit_id is not None and session.unit_id != unit_id:
                    continue
                results.append(session)
                if n > 0 and len(results) >= n:
                    break
            return results

    def get_session(self, session_id: str) -> Optional[PracticeSession]:
        """Return a single practice session by id, or None if not found."""
        with self._lock:
            return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Learning curve recording and analysis
    # ------------------------------------------------------------------

    def record_curve_point(
        self,
        agent_id: str,
        unit_id: str,
        mastery_score: float,
    ) -> Optional[LearningCurvePoint]:
        """Append a new point to a unit's learning curve.

        The point's session index is auto-incremented from the existing
        curve for that (agent, unit) pair, or 0 if no curve exists yet.

        Args:
            agent_id: Identifier of the agent.
            unit_id: Identifier of the knowledge unit.
            mastery_score: Mastery score in [0, 1] observed at this step.

        Returns:
            The newly created :class:`LearningCurvePoint`, or ``None`` if
            the unit does not exist for this agent.
        """
        with self._lock:
            unit = self._units.get(unit_id)
            if unit is None or unit.agent_id != agent_id:
                return None
            self._known_agents.add(agent_id)
            clamped = _clamp(float(mastery_score), 0.0, 1.0)
            existing_curve = self._find_curve(agent_id, unit_id)
            session_index = 0
            curve_id = ""
            if existing_curve is not None:
                curve_id = existing_curve.curve_id
                session_index = len(existing_curve.points)
            now = _now()
            point = LearningCurvePoint(
                point_id=_new_id(),
                agent_id=agent_id,
                unit_id=unit_id,
                session_index=session_index,
                mastery_score=round(clamped, 4),
                timestamp=now,
            )
            if existing_curve is None:
                curve = LearningCurve(
                    curve_id=_new_id(),
                    agent_id=agent_id,
                    unit_id=unit_id,
                    points=[point],
                    trend=TrendDirection.STABLE,
                    slope=0.0,
                    plateau_detected=True,
                    fit_r_squared=0.0,
                    concept=unit.concept,
                    updated_at=now,
                )
                self._curves[curve.curve_id] = curve
                self._curve_counter += 1
                self._curves_by_agent.setdefault(agent_id, []).append(curve.curve_id)
            else:
                existing_curve.points.append(point)
                existing_curve.updated_at = now
            self._point_counter += 1
            _evict_fifo_dict(self._curves, _MAX_CURVES)
            self._record_event(
                LearningEventKind.MASTERY_UPDATED,
                {
                    "agent_id": agent_id,
                    "unit_id": unit_id,
                    "curve_id": curve_id or self._find_curve(agent_id, unit_id).curve_id
                    if self._find_curve(agent_id, unit_id) else "",
                    "session_index": session_index,
                    "mastery_score": clamped,
                },
            )
            return point

    def get_learning_curve(
        self, agent_id: str, unit_id: str
    ) -> Optional[LearningCurve]:
        """Return the learning curve for a (agent, unit) pair, or None."""
        with self._lock:
            return self._find_curve(agent_id, unit_id)

    def list_learning_curves(self, agent_id: str) -> List[LearningCurve]:
        """List all learning curves belonging to an agent."""
        with self._lock:
            results: List[LearningCurve] = []
            for cid in self._curves_by_agent.get(agent_id, []):
                curve = self._curves.get(cid)
                if curve is not None:
                    results.append(curve)
            return results

    def compute_curve_trend(
        self, agent_id: str, unit_id: str
    ) -> Optional[LearningCurve]:
        """Recompute the trend, slope, plateau flag, and R^2 of a curve.

        Uses simple ordinary-least-squares linear regression of mastery
        score against session index. A plateau is flagged when the slope's
        magnitude is below ``_PLATEAU_SLOPE_EPSILON``.

        Returns:
            The updated :class:`LearningCurve`, or ``None`` if not found.
        """
        with self._lock:
            curve = self._find_curve(agent_id, unit_id)
            if curve is None:
                return None
            slope, r_squared = self._fit_linear_curve(curve.points)
            curve.slope = round(slope, 6)
            curve.fit_r_squared = round(r_squared, 6)
            if abs(slope) < _PLATEAU_SLOPE_EPSILON:
                curve.trend = TrendDirection.STABLE
                curve.plateau_detected = True
            elif slope > 0:
                curve.trend = TrendDirection.IMPROVING
                curve.plateau_detected = False
            else:
                curve.trend = TrendDirection.DECLINING
                curve.plateau_detected = False
            curve.updated_at = _now()
            self._record_event(
                LearningEventKind.MASTERY_UPDATED,
                {
                    "agent_id": agent_id,
                    "unit_id": unit_id,
                    "curve_id": curve.curve_id,
                    "trend": curve.trend.value,
                    "slope": curve.slope,
                    "r_squared": curve.fit_r_squared,
                    "plateau_detected": curve.plateau_detected,
                },
            )
            return curve

    @staticmethod
    def _fit_linear_curve(
        points: List[LearningCurvePoint],
    ) -> Tuple[float, float]:
        """Fit a linear regression to a curve's points.

        Returns ``(slope, r_squared)``. When there are fewer than two
        points, or all points share the same x-coordinate, both values
        are returned as 0.0.
        """
        if len(points) < 2:
            return 0.0, 0.0
        xs = [float(p.session_index) for p in points]
        ys = [float(p.mastery_score) for p in points]
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        if all(x == mean_x for x in xs):
            return 0.0, 0.0
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den_x = sum((x - mean_x) ** 2 for x in xs)
        den_y = sum((y - mean_y) ** 2 for y in ys)
        if den_x == 0.0 or den_y == 0.0:
            return 0.0, 0.0
        slope = num / den_x
        # R^2 = 1 - SS_res / SS_tot
        predicted = [mean_y + slope * (x - mean_x) for x in xs]
        ss_res = sum((y - p_y) ** 2 for y, p_y in zip(ys, predicted))
        r_squared = 1.0 - (ss_res / den_y)
        return slope, r_squared

    # ------------------------------------------------------------------
    # Forgetting detection
    # ------------------------------------------------------------------

    def detect_forgetting(self, agent_id: str, unit_id: str) -> bool:
        """Detect whether a unit shows signs of forgetting.

        A unit is considered forgotten if BOTH:
          - it has not been practised in more than
            ``_FORGETTING_AGE_HOURS`` hours, AND
          - its retention score is below ``_FORGETTING_RETENTION_CUTOFF``.

        When a previously-flagged unit is no longer forgotten, the flag
        is cleared automatically.

        Returns:
            ``True`` if the unit is currently considered forgotten,
            ``False`` otherwise (including when the unit is missing).
        """
        with self._lock:
            unit = self._units.get(unit_id)
            if unit is None or unit.agent_id != agent_id:
                return False
            hours_since_practice = _hours_between(unit.last_practiced, _now())
            if hours_since_practice is None:
                hours_since_practice = 0.0
            is_forgotten = (
                hours_since_practice > _FORGETTING_AGE_HOURS
                and unit.retention_score < _FORGETTING_RETENTION_CUTOFF
            )
            was_flagged = bool(unit.metadata.get("forgetting_detected"))
            if is_forgotten and not was_flagged:
                unit.metadata["forgetting_detected"] = True
                self._record_event(
                    LearningEventKind.FORGETTING_DETECTED,
                    {
                        "agent_id": agent_id,
                        "unit_id": unit_id,
                        "hours_since_practice": hours_since_practice,
                        "retention_score": unit.retention_score,
                    },
                )
            elif not is_forgotten and was_flagged:
                unit.metadata.pop("forgetting_detected", None)
            return is_forgotten

    # ------------------------------------------------------------------
    # Spaced-repetition review scheduling
    # ------------------------------------------------------------------

    def schedule_review(
        self,
        agent_id: str,
        unit_id: str,
        interval_hours: float = _DEFAULT_INTERVAL_HOURS,
        ease_factor: float = _DEFAULT_EASE_FACTOR,
    ) -> Optional[ReviewSchedule]:
        """Create or refresh a review schedule for a knowledge unit.

        If a schedule already exists for the (agent, unit) pair, its
        ``interval_hours``, ``ease_factor``, ``next_review_at``, and
        ``updated_at`` fields are refreshed. Otherwise a fresh schedule
        is created.

        Args:
            agent_id: Identifier of the agent that owns the unit.
            unit_id: Identifier of the knowledge unit.
            interval_hours: Initial interval until the next review, in
                hours. Clamped to a minimum of 0.0.
            ease_factor: Initial SuperMemo-style ease factor. Clamped to
                ``[_MIN_EASE_FACTOR, _MAX_EASE_FACTOR]``.

        Returns:
            The :class:`ReviewSchedule`, or ``None`` if the unit does
            not exist for this agent.
        """
        with self._lock:
            unit = self._units.get(unit_id)
            if unit is None or unit.agent_id != agent_id:
                return None
            self._known_agents.add(agent_id)
            interval = max(0.0, float(interval_hours))
            ease = _clamp(float(ease_factor), _MIN_EASE_FACTOR, _MAX_EASE_FACTOR)
            now = _now()
            existing = self._find_schedule(agent_id, unit_id)
            if existing is not None:
                existing.interval_hours = round(interval, 4)
                existing.ease_factor = round(ease, 4)
                existing.updated_at = now
                existing.next_review_at = self._compute_next_review(
                    now, interval,
                )
                self._record_event(
                    LearningEventKind.REVIEW_SCHEDULED,
                    {
                        "agent_id": agent_id,
                        "unit_id": unit_id,
                        "schedule_id": existing.schedule_id,
                        "next_review_at": existing.next_review_at,
                    },
                )
                return existing
            schedule = ReviewSchedule(
                schedule_id=_new_id(),
                agent_id=agent_id,
                unit_id=unit_id,
                next_review_at=self._compute_next_review(now, interval),
                interval_hours=round(interval, 4),
                ease_factor=round(ease, 4),
                repetitions=0,
                last_reviewed_at=None,
                created_at=now,
                updated_at=now,
            )
            self._schedules[schedule.schedule_id] = schedule
            self._schedule_counter += 1
            self._schedules_by_agent.setdefault(agent_id, []).append(schedule.schedule_id)
            _evict_fifo_dict(self._schedules, _MAX_SCHEDULES)
            self._record_event(
                LearningEventKind.REVIEW_SCHEDULED,
                {
                    "agent_id": agent_id,
                    "unit_id": unit_id,
                    "schedule_id": schedule.schedule_id,
                    "next_review_at": schedule.next_review_at,
                },
            )
            return schedule

    def get_review_schedule(
        self, agent_id: str, unit_id: str
    ) -> Optional[ReviewSchedule]:
        """Return the review schedule for a (agent, unit) pair, or None."""
        with self._lock:
            return self._find_schedule(agent_id, unit_id)

    def due_reviews(
        self,
        agent_id: str,
        before_timestamp: Optional[str] = None,
    ) -> List[ReviewSchedule]:
        """Return review schedules whose ``next_review_at`` is in the past.

        Args:
            agent_id: Identifier of the agent whose schedules are queried.
            before_timestamp: Optional ISO-8601 cutoff. When ``None`` the
                current wall-clock time is used.

        Returns:
            A list of :class:`ReviewSchedule` objects whose next-review
            timestamp is on or before the cutoff, in chronological order.
        """
        with self._lock:
            cutoff = before_timestamp or _now()
            cutoff_dt = _parse_timestamp(cutoff) or datetime.datetime.utcnow()
            results: List[ReviewSchedule] = []
            for sid in self._schedules_by_agent.get(agent_id, []):
                schedule = self._schedules.get(sid)
                if schedule is None:
                    continue
                next_dt = _parse_timestamp(schedule.next_review_at)
                if next_dt is None:
                    continue
                if next_dt <= cutoff_dt:
                    results.append(schedule)
            results.sort(key=lambda s: s.next_review_at)
            return results

    def record_review(
        self,
        agent_id: str,
        unit_id: str,
        success: bool,
    ) -> Optional[ReviewSchedule]:
        """Mark a review as completed and update its schedule.

        On a successful review, the interval grows by ``ease_factor`` and
        the repetition counter increments. On a failed review, the
        interval resets to a short one-hour value and the ease factor
        drops by 0.2 (floored at ``_MIN_EASE_FACTOR``). The
        ``last_reviewed_at`` and ``next_review_at`` fields are refreshed.

        Returns:
            The updated :class:`ReviewSchedule`, or ``None`` if missing.
        """
        with self._lock:
            schedule = self._find_schedule(agent_id, unit_id)
            if schedule is None:
                return None
            now = _now()
            schedule.last_reviewed_at = now
            schedule.repetitions += 1
            if success:
                new_interval = max(1.0, schedule.interval_hours * schedule.ease_factor)
            else:
                schedule.ease_factor = max(
                    _MIN_EASE_FACTOR,
                    schedule.ease_factor - 0.2,
                )
                new_interval = 1.0
            schedule.interval_hours = round(new_interval, 4)
            schedule.ease_factor = round(schedule.ease_factor, 4)
            schedule.next_review_at = self._compute_next_review(now, new_interval)
            schedule.updated_at = now
            self._record_event(
                LearningEventKind.REVIEW_SCHEDULED,
                {
                    "agent_id": agent_id,
                    "unit_id": unit_id,
                    "schedule_id": schedule.schedule_id,
                    "success": success,
                    "next_review_at": schedule.next_review_at,
                },
            )
            return schedule

    @staticmethod
    def _compute_next_review(now_iso: str, interval_hours: float) -> str:
        """Return an ISO-8601 timestamp ``interval_hours`` from ``now_iso``."""
        now_dt = _parse_timestamp(now_iso) or datetime.datetime.utcnow()
        target = now_dt + datetime.timedelta(hours=max(0.0, float(interval_hours)))
        return target.isoformat() + "Z"

    # ------------------------------------------------------------------
    # Insights and reports
    # ------------------------------------------------------------------

    def generate_insight(
        self,
        agent_id: str,
        kind: str,
        description: str,
        related_unit_ids: Optional[List[str]] = None,
        confidence: float = 0.5,
        metric_type: MetricType = MetricType.MASTERY_SCORE,
    ) -> LearningInsight:
        """Create a synthesised learning insight for an agent.

        Args:
            agent_id: Identifier of the agent that owns the insight.
            kind: Free-form category for the insight, e.g. ``"rapid_improvement"``
                or ``"needs_review"``.
            description: Human-readable description of the insight.
            related_unit_ids: Optional list of knowledge unit ids the
                insight refers to.
            confidence: Confidence in the insight, clamped to [0, 1].
            metric_type: The :class:`MetricType` this insight is keyed to.

        Returns:
            The newly created :class:`LearningInsight`.
        """
        with self._lock:
            self._known_agents.add(agent_id)
            clamped_conf = _clamp(float(confidence), 0.0, 1.0)
            now = _now()
            insight = LearningInsight(
                insight_id=_new_id(),
                agent_id=agent_id,
                kind=kind,
                description=description,
                related_units=list(related_unit_ids) if related_unit_ids else [],
                confidence=round(clamped_conf, 4),
                created_at=now,
                metric_type=metric_type,
            )
            self._insights[insight.insight_id] = insight
            self._insight_counter += 1
            self._insights_by_agent.setdefault(agent_id, []).append(insight.insight_id)
            _evict_fifo_dict(self._insights, _MAX_INSIGHTS)
            self._record_event(
                LearningEventKind.INSIGHT_GENERATED,
                {
                    "agent_id": agent_id,
                    "insight_id": insight.insight_id,
                    "kind": kind,
                    "confidence": insight.confidence,
                },
            )
            return insight

    def list_insights(
        self,
        agent_id: str,
        kind: Optional[str] = None,
    ) -> List[LearningInsight]:
        """List insights for an agent, optionally filtered by ``kind``."""
        with self._lock:
            results: List[LearningInsight] = []
            for iid in self._insights_by_agent.get(agent_id, []):
                insight = self._insights.get(iid)
                if insight is None:
                    continue
                if kind is not None and insight.kind != kind:
                    continue
                results.append(insight)
            return results

    def generate_report(self, agent_id: str) -> KnowledgeReport:
        """Generate a roll-up knowledge report for an agent.

        The report computes the unit distribution by knowledge state and
        mastery level, the average mastery, a list of knowledge gaps (units
        whose mastery is below 0.5) and a list of recommendations
        describing the most relevant next steps for the agent.

        Returns:
            The newly created :class:`KnowledgeReport`.
        """
        with self._lock:
            self._known_agents.add(agent_id)
            units = [
                self._units[uid]
                for uid in self._units_by_agent.get(agent_id, [])
                if uid in self._units
            ]
            by_state: Dict[str, int] = {}
            by_level: Dict[str, int] = {}
            mastery_total = 0.0
            retention_total = 0.0
            gaps: List[str] = []
            for unit in units:
                by_state[unit.knowledge_state.value] = by_state.get(
                    unit.knowledge_state.value, 0,
                ) + 1
                by_level[unit.mastery_level.value] = by_level.get(
                    unit.mastery_level.value, 0,
                ) + 1
                mastery_total += unit.mastery_score
                retention_total += unit.retention_score
                if unit.mastery_score < 0.5:
                    gaps.append(unit.concept)
            n = len(units)
            avg_mastery = (mastery_total / n) if n else 0.0
            avg_retention = (retention_total / n) if n else 0.0
            avg_velocity = self._compute_velocity_locked(agent_id)
            recommendations: List[str] = []
            if gaps:
                recommendations.append(
                    "Schedule focused practice on: " + ", ".join(gaps[:5]),
                )
            if avg_retention < 0.6:
                recommendations.append(
                    "Increase review frequency to combat retention decay",
                )
            if avg_velocity < 0.05 and n > 0:
                recommendations.append(
                    "Consider guided instruction to accelerate mastery",
                )
            if not recommendations:
                recommendations.append("Maintain current learning trajectory")
            now = _now()
            report = KnowledgeReport(
                report_id=_new_id(),
                agent_id=agent_id,
                total_units=n,
                by_state=by_state,
                by_level=by_level,
                average_mastery=round(avg_mastery, 4),
                knowledge_gaps=sorted(gaps),
                recommendations=recommendations,
                generated_at=now,
                average_velocity=round(avg_velocity, 4),
                average_retention=round(avg_retention, 4),
            )
            self._reports[report.report_id] = report
            self._report_counter += 1
            self._reports_by_agent.setdefault(agent_id, []).append(report.report_id)
            _evict_fifo_dict(self._reports, _MAX_REPORTS)
            self._record_event(
                LearningEventKind.REPORT_GENERATED,
                {
                    "agent_id": agent_id,
                    "report_id": report.report_id,
                    "total_units": n,
                    "average_mastery": report.average_mastery,
                },
            )
            return report

    def list_reports(
        self,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[KnowledgeReport]:
        """List knowledge reports, optionally filtered by agent."""
        with self._lock:
            n = max(0, int(limit))
            if agent_id is not None:
                ids = list(reversed(self._reports_by_agent.get(agent_id, [])))
            else:
                ids = list(reversed(list(self._reports.keys())))
            results: List[KnowledgeReport] = []
            for rid in ids:
                report = self._reports.get(rid)
                if report is None:
                    continue
                results.append(report)
                if n > 0 and len(results) >= n:
                    break
            return results

    def get_report(self, report_id: str) -> Optional[KnowledgeReport]:
        """Return a knowledge report by id, or None if not found."""
        with self._lock:
            return self._reports.get(report_id)

    # ------------------------------------------------------------------
    # Aggregate analytics
    # ------------------------------------------------------------------

    def compute_learning_velocity(self, agent_id: str) -> float:
        """Estimate the agent's learning velocity in units-per-session.

        Velocity is defined as the number of knowledge units that have
        reached PROFICIENT or MASTERED divided by the total number of
        practice sessions for the agent. When the agent has no sessions
        yet, the velocity is reported as 0.0.
        """
        with self._lock:
            return round(self._compute_velocity_locked(agent_id), 4)

    def _compute_velocity_locked(self, agent_id: str) -> float:
        """Internal, lock-held helper for compute_learning_velocity."""
        mastered_count = 0
        for uid in self._units_by_agent.get(agent_id, []):
            unit = self._units.get(uid)
            if unit is None:
                continue
            if unit.knowledge_state in (KnowledgeState.PROFICIENT, KnowledgeState.MASTERED):
                mastered_count += 1
        session_count = len(self._sessions_by_agent.get(agent_id, []))
        if session_count == 0:
            return 0.0
        return mastered_count / float(session_count)

    def compute_mastery_distribution(self, agent_id: str) -> Dict[str, int]:
        """Return a count of units per mastery level for an agent."""
        with self._lock:
            distribution: Dict[str, int] = {}
            for uid in self._units_by_agent.get(agent_id, []):
                unit = self._units.get(uid)
                if unit is None:
                    continue
                level = unit.mastery_level.value
                distribution[level] = distribution.get(level, 0) + 1
            return distribution

    def compute_retention_rate(self, agent_id: str) -> float:
        """Return the average retention score across the agent's units."""
        with self._lock:
            total = 0.0
            count = 0
            for uid in self._units_by_agent.get(agent_id, []):
                unit = self._units.get(uid)
                if unit is None:
                    continue
                total += unit.retention_score
                count += 1
            if count == 0:
                return 0.0
            return round(total / float(count), 4)

    def compute_forgetting_rate(self, agent_id: str) -> float:
        """Return the fraction of the agent's units flagged as forgotten."""
        with self._lock:
            total = 0
            forgotten = 0
            for uid in self._units_by_agent.get(agent_id, []):
                unit = self._units.get(uid)
                if unit is None:
                    continue
                total += 1
                if unit.metadata.get("forgetting_detected"):
                    forgotten += 1
            if total == 0:
                return 0.0
            return round(forgotten / float(total), 4)

    def compute_transfer_rate(self, agent_id: str) -> float:
        """Return the fraction of units in the APPLICATION phase or beyond.

        "Transfer" here means the agent has progressed past pure practice
        and is applying the concept in a richer context. Units in
        APPLICATION, MASTERY, or RETENTION phases count toward the rate.
        """
        with self._lock:
            total = 0
            transferred = 0
            transfer_phases = {
                LearningPhase.APPLICATION,
                LearningPhase.MASTERY,
                LearningPhase.RETENTION,
            }
            for uid in self._units_by_agent.get(agent_id, []):
                unit = self._units.get(uid)
                if unit is None:
                    continue
                total += 1
                if unit.learning_phase in transfer_phases:
                    transferred += 1
            if total == 0:
                return 0.0
            return round(transferred / float(total), 4)

    def compute_metric(self, agent_id: str, metric: MetricType) -> float:
        """Dispatch helper that returns a single metric by :class:`MetricType`."""
        with self._lock:
            if metric == MetricType.LEARNING_VELOCITY:
                return self.compute_learning_velocity(agent_id)
            if metric == MetricType.RETENTION_RATE:
                return self.compute_retention_rate(agent_id)
            if metric == MetricType.MASTERY_SCORE:
                total = 0.0
                count = 0
                for uid in self._units_by_agent.get(agent_id, []):
                    unit = self._units.get(uid)
                    if unit is None:
                        continue
                    total += unit.mastery_score
                    count += 1
                if count == 0:
                    return 0.0
                return round(total / float(count), 4)
            if metric == MetricType.FORGETTING_RATE:
                return self.compute_forgetting_rate(agent_id)
            if metric == MetricType.TRANSFER_RATE:
                return self.compute_transfer_rate(agent_id)
            return 0.0

    # ------------------------------------------------------------------
    # Internal recomputation helpers
    # ------------------------------------------------------------------

    def _recompute_unit_state(self, unit: KnowledgeUnit) -> None:
        """Recompute derived fields (mastery, retention, state, level).

        Assumes the caller already holds ``self._lock``.

        Mastery score blends three signals:

          - practice volume via a logarithmic compression of practice_count
          - smoothed historical success rate
          - retention_score (updated by exponential decay since last practice)

        Knowledge state and mastery level are then derived from the
        resulting mastery score and practice count.
        """
        # Update retention using exponential decay since the last practice.
        if unit.practice_count == 0:
            retention = 1.0
        else:
            hours_since = _hours_between(unit.last_practiced, _now()) or 0.0
            # Half-life of 72 hours.
            half_life = 72.0
            retention = math.exp(-hours_since * math.log(2.0) / half_life)
        unit.retention_score = _clamp(retention, 0.0, 1.0)

        # Practice volume signal: log compression in [0, 1] (saturates at ~50).
        practice_volume = _clamp(math.log1p(max(0, unit.practice_count)) / math.log1p(50.0))

        # Smoothed success rate with a Laplace-style prior.
        numerator = unit.success_count + _SUCCESS_RATE_PRIOR
        denominator = unit.practice_count + 2.0 * _SUCCESS_RATE_PRIOR
        success_rate = numerator / denominator if denominator > 0 else 0.0

        mastery = (
            _PRACTICE_WEIGHT * practice_volume
            + _SUCCESS_WEIGHT * success_rate
            + _RETENTION_WEIGHT * unit.retention_score
        )
        unit.mastery_score = round(_clamp(mastery, 0.0, 1.0), 4)

        # Derive knowledge state from mastery.
        if unit.practice_count == 0:
            unit.knowledge_state = KnowledgeState.INTRODUCED
            unit.learning_phase = LearningPhase.INTAKE
        elif unit.mastery_score >= 0.9 and unit.practice_count >= 10:
            unit.knowledge_state = KnowledgeState.MASTERED
            unit.learning_phase = LearningPhase.MASTERY
        elif unit.mastery_score >= 0.75 and unit.practice_count >= 5:
            unit.knowledge_state = KnowledgeState.PROFICIENT
            unit.learning_phase = LearningPhase.APPLICATION
        elif unit.mastery_score >= 0.55:
            unit.knowledge_state = KnowledgeState.FAMILIAR
            unit.learning_phase = LearningPhase.APPLICATION
        elif unit.mastery_score >= 0.3 or unit.practice_count >= 2:
            unit.knowledge_state = KnowledgeState.PRACTICED
            unit.learning_phase = LearningPhase.PRACTICE
        else:
            unit.knowledge_state = KnowledgeState.INTRODUCED
            unit.learning_phase = LearningPhase.INTAKE

        # Derive mastery level from mastery score bands.
        if unit.mastery_score >= 0.9:
            unit.mastery_level = MasteryLevel.EXPERT
        elif unit.mastery_score >= 0.7:
            unit.mastery_level = MasteryLevel.ADVANCED
        elif unit.mastery_score >= 0.5:
            unit.mastery_level = MasteryLevel.INTERMEDIATE
        elif unit.mastery_score >= 0.25:
            unit.mastery_level = MasteryLevel.BEGINNER
        else:
            unit.mastery_level = MasteryLevel.NOVICE

    def _find_curve(self, agent_id: str, unit_id: str) -> Optional[LearningCurve]:
        """Return the curve for a (agent, unit) pair, or None.

        Assumes the caller already holds ``self._lock``.
        """
        for cid in self._curves_by_agent.get(agent_id, []):
            curve = self._curves.get(cid)
            if curve is None:
                continue
            if curve.unit_id == unit_id:
                return curve
        return None

    def _find_schedule(
        self, agent_id: str, unit_id: str
    ) -> Optional[ReviewSchedule]:
        """Return the schedule for a (agent, unit) pair, or None.

        Assumes the caller already holds ``self._lock``.
        """
        for sid in self._schedules_by_agent.get(agent_id, []):
            schedule = self._schedules.get(sid)
            if schedule is None:
                continue
            if schedule.unit_id == unit_id:
                return schedule
        return None

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: LearningEventKind,
        payload: Dict[str, Any],
    ) -> None:
        """Record an observable learning analytics event.

        Assumes the caller already holds ``self._lock``. The event log is
        bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = LearningAnalyticsEvent(
            event_id=_new_id(),
            kind=kind,
            timestamp=_now(),
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, limit: int = 100) -> List[LearningAnalyticsEvent]:
        """Return the most recent learning analytics events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> LearningStats:
        """Return aggregate statistics about the learning analytics engine."""
        with self._lock:
            units = list(self._units.values())
            mastery_distribution: Dict[str, int] = {}
            state_distribution: Dict[str, int] = {}
            total_mastery = 0.0
            for unit in units:
                level = unit.mastery_level.value
                mastery_distribution[level] = mastery_distribution.get(level, 0) + 1
                state = unit.knowledge_state.value
                state_distribution[state] = state_distribution.get(state, 0) + 1
                total_mastery += unit.mastery_score
            avg_mastery = (total_mastery / len(units)) if units else 0.0
            return LearningStats(
                total_agents=len(self._known_agents),
                total_units=len(self._units),
                total_sessions=len(self._sessions),
                total_insights=len(self._insights),
                average_mastery=round(avg_mastery, 4),
                mastery_distribution=mastery_distribution,
                state_distribution=state_distribution,
                total_reports=len(self._reports),
                total_schedules=len(self._schedules),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics."""
        with self._lock:
            stats = self.get_stats()
            status: Dict[str, Any] = {
                "initialized": self._initialized,
                "total_agents": len(self._known_agents),
                "total_units": len(self._units),
                "total_sessions": len(self._sessions),
                "total_curves": len(self._curves),
                "total_reports": len(self._reports),
                "total_insights": len(self._insights),
                "total_schedules": len(self._schedules),
                "total_events": len(self._events),
                "counters": {
                    "unit_counter": self._unit_counter,
                    "session_counter": self._session_counter,
                    "curve_counter": self._curve_counter,
                    "point_counter": self._point_counter,
                    "report_counter": self._report_counter,
                    "insight_counter": self._insight_counter,
                    "schedule_counter": self._schedule_counter,
                },
                "average_mastery": stats.average_mastery,
                "mastery_distribution": dict(stats.mastery_distribution),
                "state_distribution": dict(stats.state_distribution),
                "capacities": {
                    "max_units": _MAX_UNITS,
                    "max_sessions": _MAX_SESSIONS,
                    "max_curves": _MAX_CURVES,
                    "max_reports": _MAX_REPORTS,
                    "max_insights": _MAX_INSIGHTS,
                    "max_schedules": _MAX_SCHEDULES,
                    "max_events": _MAX_EVENTS,
                },
                "algorithm_constants": {
                    "practice_weight": _PRACTICE_WEIGHT,
                    "success_weight": _SUCCESS_WEIGHT,
                    "retention_weight": _RETENTION_WEIGHT,
                    "success_rate_prior": _SUCCESS_RATE_PRIOR,
                    "mastery_threshold": _MASTERY_THRESHOLD,
                    "plateau_slope_epsilon": _PLATEAU_SLOPE_EPSILON,
                    "forgetting_age_hours": _FORGETTING_AGE_HOURS,
                    "forgetting_retention_cutoff": _FORGETTING_RETENTION_CUTOFF,
                    "default_interval_hours": _DEFAULT_INTERVAL_HOURS,
                    "default_ease_factor": _DEFAULT_EASE_FACTOR,
                    "min_ease_factor": _MIN_EASE_FACTOR,
                    "max_ease_factor": _MAX_EASE_FACTOR,
                },
            }
            return status

    def get_snapshot(self) -> LearningAnalyticsSnapshot:
        """Return a complete snapshot of the learning analytics engine state."""
        with self._lock:
            return LearningAnalyticsSnapshot(
                initialized=self._initialized,
                units=list(self._units.values()),
                sessions=list(self._sessions.values()),
                curves=list(self._curves.values()),
                reports=list(self._reports.values()),
                insights=list(self._insights.values()),
                schedules=list(self._schedules.values()),
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state and re-seed baseline data.

        After clearing, the engine re-seeds the baseline learning analytics
        data, restoring a freshly initialized state.
        """
        with self._lock:
            self._units.clear()
            self._sessions.clear()
            self._curves.clear()
            self._reports.clear()
            self._insights.clear()
            self._schedules.clear()
            self._events.clear()
            self._units_by_agent.clear()
            self._sessions_by_agent.clear()
            self._curves_by_agent.clear()
            self._insights_by_agent.clear()
            self._schedules_by_agent.clear()
            self._reports_by_agent.clear()
            self._known_agents.clear()
            self._unit_counter = 0
            self._session_counter = 0
            self._curve_counter = 0
            self._point_counter = 0
            self._report_counter = 0
            self._insight_counter = 0
            self._schedule_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs learning analytics data.

        Seeds two agents (``agent_alpha`` and ``agent_beta``) with different
        learning profiles, practice sessions, a learning curve, two
        insights, two review schedules, and a single roll-up report.
        """
        # --- Agents: agent_alpha is a fast learner, agent_beta is slow
        # but thorough. We seed units with explicit states/levels to give
        # the engine a useful starting point.
        self._known_agents.add("agent_alpha")
        self._known_agents.add("agent_beta")

        # --- agent_alpha: combat, stealth, navigation, healing ----------
        alpha_specs = [
            ("combat", KnowledgeState.PROFICIENT, MasteryLevel.ADVANCED, 0.82, 16, 14),
            ("stealth", KnowledgeState.PRACTICED, MasteryLevel.INTERMEDIATE, 0.48, 5, 3),
            ("navigation", KnowledgeState.FAMILIAR, MasteryLevel.INTERMEDIATE, 0.61, 7, 5),
            ("healing", KnowledgeState.INTRODUCED, MasteryLevel.NOVICE, 0.18, 1, 0),
        ]
        alpha_units: Dict[str, KnowledgeUnit] = {}
        for concept, state, level, mastery, practice, successes in alpha_specs:
            first_seen = _hours_ago_timestamp(96.0)
            last_practiced = _hours_ago_timestamp(6.0)
            unit = KnowledgeUnit(
                unit_id=_new_id(),
                agent_id="agent_alpha",
                concept=concept,
                knowledge_state=state,
                mastery_level=level,
                first_seen=first_seen,
                last_practiced=last_practiced,
                practice_count=practice,
                success_count=successes,
                retention_score=0.85,
                mastery_score=mastery,
                learning_phase=(
                    LearningPhase.APPLICATION
                    if state in (KnowledgeState.PROFICIENT, KnowledgeState.FAMILIAR)
                    else LearningPhase.PRACTICE
                    if state == KnowledgeState.PRACTICED
                    else LearningPhase.INTAKE
                ),
                description=f"Alpha's {concept} knowledge unit",
            )
            self._ingest_unit(unit)
            alpha_units[concept] = unit

        # --- agent_beta: magic, alchemy, enchanting ---------------------
        beta_specs = [
            ("magic", KnowledgeState.FAMILIAR, MasteryLevel.ADVANCED, 0.78, 12, 10),
            ("alchemy", KnowledgeState.PROFICIENT, MasteryLevel.INTERMEDIATE, 0.66, 9, 7),
            ("enchanting", KnowledgeState.PRACTICED, MasteryLevel.BEGINNER, 0.35, 4, 2),
        ]
        beta_units: Dict[str, KnowledgeUnit] = {}
        for concept, state, level, mastery, practice, successes in beta_specs:
            first_seen = _hours_ago_timestamp(120.0)
            last_practiced = _hours_ago_timestamp(12.0)
            unit = KnowledgeUnit(
                unit_id=_new_id(),
                agent_id="agent_beta",
                concept=concept,
                knowledge_state=state,
                mastery_level=level,
                first_seen=first_seen,
                last_practiced=last_practiced,
                practice_count=practice,
                success_count=successes,
                retention_score=0.78,
                mastery_score=mastery,
                learning_phase=(
                    LearningPhase.APPLICATION
                    if state in (KnowledgeState.PROFICIENT, KnowledgeState.FAMILIAR)
                    else LearningPhase.PRACTICE
                ),
                description=f"Beta's {concept} knowledge unit",
            )
            self._ingest_unit(unit)
            beta_units[concept] = unit

        # --- Practice sessions for agent_alpha (5 sessions) ------------
        alpha_sessions = [
            (alpha_units["combat"], 3, 3, 0, 300, 0.95),
            (alpha_units["combat"], 2, 2, 1, 180, 0.85),
            (alpha_units["stealth"], 2, 1, 1, 240, 0.40),
            (alpha_units["navigation"], 3, 2, 0, 200, 0.65),
            (alpha_units["healing"], 1, 0, 0, 90, 0.10),
        ]
        for unit, attempts, successes, hints, duration, _score in alpha_sessions:
            self.record_practice(
                agent_id="agent_alpha",
                unit_id=unit.unit_id,
                attempts=attempts,
                successes=successes,
                hints_used=hints,
                duration_seconds=duration,
                notes="seed session",
            )

        # --- Practice sessions for agent_beta (3 sessions) -------------
        beta_sessions = [
            (beta_units["magic"], 2, 2, 0, 360, 0.90),
            (beta_units["alchemy"], 3, 2, 1, 420, 0.60),
            (beta_units["enchanting"], 2, 1, 2, 300, 0.30),
        ]
        for unit, attempts, successes, hints, duration, _score in beta_sessions:
            self.record_practice(
                agent_id="agent_beta",
                unit_id=unit.unit_id,
                attempts=attempts,
                successes=successes,
                hints_used=hints,
                duration_seconds=duration,
                notes="seed session",
            )

        # --- Learning curve: 8 points for agent_alpha's combat ---------
        combat_unit = alpha_units["combat"]
        curve_scores = [0.32, 0.45, 0.52, 0.61, 0.68, 0.74, 0.79, 0.83]
        for idx, score in enumerate(curve_scores):
            self.record_curve_point(
                agent_id="agent_alpha",
                unit_id=combat_unit.unit_id,
                mastery_score=score,
            )
        # Fit the curve so trend / slope / plateau are populated.
        self.compute_curve_trend("agent_alpha", combat_unit.unit_id)

        # --- Two insights ---------------------------------------------
        self.generate_insight(
            agent_id="agent_alpha",
            kind="rapid_improvement",
            description="agent_alpha is improving rapidly in combat",
            related_unit_ids=[combat_unit.unit_id],
            confidence=0.85,
            metric_type=MetricType.LEARNING_VELOCITY,
        )
        self.generate_insight(
            agent_id="agent_beta",
            kind="needs_review",
            description="agent_beta needs review on enchanting",
            related_unit_ids=[beta_units["enchanting"].unit_id],
            confidence=0.72,
            metric_type=MetricType.RETENTION_RATE,
        )

        # --- Two review schedules -------------------------------------
        self.schedule_review(
            agent_id="agent_alpha",
            unit_id=combat_unit.unit_id,
            interval_hours=12.0,
            ease_factor=2.6,
        )
        self.schedule_review(
            agent_id="agent_beta",
            unit_id=beta_units["enchanting"].unit_id,
            interval_hours=6.0,
            ease_factor=2.2,
        )

        # --- One report ------------------------------------------------
        self.generate_report("agent_alpha")


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_learning_analytics() -> LearningAnalyticsEngine:
    """Return the singleton LearningAnalyticsEngine instance."""
    return LearningAnalyticsEngine.get_instance()
