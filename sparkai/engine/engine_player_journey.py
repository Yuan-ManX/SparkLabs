"""
SparkLabs Engine - Player Journey Engine

Tracks and analyzes the journeys that players take through a game. A
"journey" is a chronologically ordered sequence of ``JourneyStage``
visits, ``TouchPoint`` interactions, ``EngagementLevel`` readings,
``EmotionSignal`` snapshots and ``FunnelPhase`` transitions recorded
for a single play session. The engine records everything as
``JourneyEvent`` audit entries, computes aggregate ``JourneyStats``
and supports snapshotting the entire state for offline analysis or
time-travel debugging of the player experience.

Architecture:
  PlayerJourneyEngine (singleton)
    |-- JourneySession, StageTransition, TouchpointEvent,
        EngagementReading, EmotionSnapshot, FunnelState,
        JourneyStats, JourneySnapshot, JourneyEvent
    |-- JourneyStage, TouchPoint, EngagementLevel, FunnelPhase,
        EmotionSignal, DropOffReason, JourneyEventKind

Core Capabilities:
  - start_session / end_session: lifecycle management for play
    sessions, with an optional drop-off stage on end.
  - record_stage_transition / record_touchpoint / record_engagement /
    record_emotion: per-session data capture.
  - create_funnel / advance_funnel / complete_funnel /
    record_drop_off: marketing-style funnels with phase transitions.
  - get_sessions / get_session / get_transitions / get_touchpoints /
    get_engagement_readings / get_emotion_snapshots / get_funnels:
    accessor helpers that return copies of the underlying stores.
  - list_events / get_stats / get_status / get_snapshot:
    observability and serialization.
  - reset: clear all stores and re-seed with default data.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`PlayerJourneyEngine.get_instance` or the module-level
:func:`get_player_journey` factory. All public methods are guarded by
the re-entrant lock.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest
# entry is evicted in FIFO order to keep memory growth predictable
# across long-running sessions and large player populations.
_MAX_SESSIONS: int = 500
_MAX_TRANSITIONS_PER_SESSION: int = 100
_MAX_TOUCHPOINTS_PER_SESSION: int = 200
_MAX_READINGS_PER_SESSION: int = 200
_MAX_EMOTIONS_PER_SESSION: int = 200
_MAX_FUNNELS: int = 500
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix.

    Used as the default factory for timestamp fields on data classes
    and on every audit event the engine emits.
    """
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier
            with an underscore. When omitted, the bare hex id is
            returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict to keep ``len(store) <= max_size``.

    Eviction order follows the dict's iteration order, which for
    Python 3.7+ is insertion order. The store is mutated in place.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep ``len(store) <= max_size``.

    Eviction order is the natural list order (front is oldest). The
    store is mutated in place.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert ``value`` into something safe to drop into a JSON payload.

    Enums are unwrapped to their ``.value`` strings. Dataclasses are
    serialized through :func:`_dataclass_to_dict`. Lists and dicts are
    walked recursively. Anything else is returned as-is.
    """
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
    """Convert a dataclass instance to a plain dictionary.

    Each value is passed through :func:`_to_jsonable` so that nested
    enums or dataclasses are also serialized. The returned dictionary
    is a shallow copy of the dataclass's fields.
    """
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


class JourneyStage(Enum):
    """High-level phase of the player's journey through the game.

    - ``TUTORIAL``: the player is learning the rules and mechanics.
    - ``EXPLORATION``: the player is freely exploring the world.
    - ``DISCOVERY``: the player is uncovering a new mechanic or area.
    - ``CHALLENGE``: the player is facing a difficult encounter.
    - ``CLIMAX``: the player is at a peak dramatic moment.
    - ``RESOLUTION``: the player is wrapping up a storyline.
    - ``REPLAY``: the player is replaying content (new game+ etc).
    """

    TUTORIAL = "tutorial"
    EXPLORATION = "exploration"
    DISCOVERY = "discovery"
    CHALLENGE = "challenge"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    REPLAY = "replay"


class TouchPoint(Enum):
    """A discrete interaction point the player may reach.

    - ``MENU``: a UI menu screen (main menu, pause menu, settings).
    - ``CUTSCENE``: a non-interactive narrative sequence.
    - ``GAMEPLAY``: active gameplay moment.
    - ``DIALOGUE``: an NPC conversation.
    - ``BATTLE``: a combat encounter.
    - ``SHOP``: a vendor / merchant interaction.
    - ``INVENTORY``: the inventory or loadout screen.
    - ``ACHIEVEMENT``: an achievement / trophy notification.
    - ``DEATH``: a death event.
    - ``VICTORY``: a victory / win event.
    - ``PAUSE``: a pause overlay.
    """

    MENU = "menu"
    CUTSCENE = "cutscene"
    GAMEPLAY = "gameplay"
    DIALOGUE = "dialogue"
    BATTLE = "battle"
    SHOP = "shop"
    INVENTORY = "inventory"
    ACHIEVEMENT = "achievement"
    DEATH = "death"
    VICTORY = "victory"
    PAUSE = "pause"


class EngagementLevel(Enum):
    """How engaged the player currently is with the game.

    - ``DISENGAGED``: the player is not paying attention.
    - ``CASUAL``: light, drop-in play.
    - ``INVOLVED``: actively playing but not deeply focused.
    - ``IMMERSED``: deeply focused on the experience.
    - ``FLOW``: the player is in flow state.
    - ``PEAK``: peak / transcendental engagement.
    """

    DISENGAGED = "disengaged"
    CASUAL = "casual"
    INVOLVED = "involved"
    IMMERSED = "immersed"
    FLOW = "flow"
    PEAK = "peak"


class FunnelPhase(Enum):
    """Standard marketing-funnel phase progression.

    - ``AWARENESS``: the player first becomes aware of the game.
    - ``INTEREST``: the player expresses interest (wishlist, trailer).
    - ``TRIAL``: the player tries the game (demo, free weekend).
    - ``ENGAGEMENT``: the player is regularly playing.
    - ``RETENTION``: the player keeps coming back.
    - ``ADVOCACY``: the player recommends the game to others.
    """

    AWARENESS = "awareness"
    INTEREST = "interest"
    TRIAL = "trial"
    ENGAGEMENT = "engagement"
    RETENTION = "retention"
    ADVOCACY = "advocacy"


class EmotionSignal(Enum):
    """Discrete emotional state detected from player behavior.

    - ``JOY``: positive delight.
    - ``FRUSTRATION``: the player is struggling or annoyed.
    - ``CURIOSITY``: the player is exploring / questioning.
    - ``FEAR``: the player is anxious or scared.
    - ``SURPRISE``: the player was caught off-guard.
    - ``SATISFACTION``: a goal was met cleanly.
    - ``BOREDOM``: the player is losing interest.
    - ``ANXIETY``: the player is nervous about an outcome.
    - ``EXCITEMENT``: the player is highly energized.
    """

    JOY = "joy"
    FRUSTRATION = "frustration"
    CURIOSITY = "curiosity"
    FEAR = "fear"
    SURPRISE = "surprise"
    SATISFACTION = "satisfaction"
    BOREDOM = "boredom"
    ANXIETY = "anxiety"
    EXCITEMENT = "excitement"


class DropOffReason(Enum):
    """Reason a player stopped playing or fell out of a funnel.

    - ``DIFFICULTY``: the content was too hard.
    - ``CONFUSION``: the player did not understand the content.
    - ``LENGTH``: the content was too long.
    - ``TECHNICAL``: a crash, bug or performance problem.
    - ``CONTENT``: missing / unsatisfactory content.
    - ``LOST_INTEREST``: the player simply wandered off.
    """

    DIFFICULTY = "difficulty"
    CONFUSION = "confusion"
    LENGTH = "length"
    TECHNICAL = "technical"
    CONTENT = "content"
    LOST_INTEREST = "lost_interest"


class JourneyEventKind(Enum):
    """Kinds of audit events emitted by the player journey engine."""

    STAGE_ENTERED = "stage_entered"
    TOUCHPOINT_REACHED = "touchpoint_reached"
    ENGAGEMENT_CHANGED = "engagement_changed"
    EMOTION_DETECTED = "emotion_detected"
    FUNNEL_TRANSITION = "funnel_transition"
    DROP_OFF_RECORDED = "drop_off_recorded"
    MILESTONE_REACHED = "milestone_reached"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class JourneySession:
    """A single play session for a player.

    The session captures the player's id, the time window during
    which the session was active, the stages visited, touchpoints
    reached, current engagement level, total play duration, the
    funnels completed and the stage at which the player dropped off
    (empty when the session ended cleanly).
    """

    session_id: str = field(default_factory=lambda: _new_id("session"))
    player_id: str = ""
    started_at: str = field(default_factory=_now)
    ended_at: str = ""
    stages_visited: List[str] = field(default_factory=list)
    touchpoints_reached: List[str] = field(default_factory=list)
    current_stage: str = JourneyStage.TUTORIAL.value
    current_engagement: str = EngagementLevel.CASUAL.value
    total_duration: float = 0.0
    funnels_completed: int = 0
    drop_off_stage: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "player_id": self.player_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "stages_visited": list(self.stages_visited),
            "touchpoints_reached": list(self.touchpoints_reached),
            "current_stage": self.current_stage,
            "current_engagement": self.current_engagement,
            "total_duration": self.total_duration,
            "funnels_completed": self.funnels_completed,
            "drop_off_stage": self.drop_off_stage,
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class StageTransition:
    """A single transition between two ``JourneyStage`` values."""

    transition_id: str = field(default_factory=lambda: _new_id("trans"))
    session_id: str = ""
    from_stage: str = JourneyStage.TUTORIAL.value
    to_stage: str = JourneyStage.EXPLORATION.value
    duration_in_previous: float = 0.0
    trigger: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "session_id": self.session_id,
            "from_stage": self.from_stage,
            "to_stage": self.to_stage,
            "duration_in_previous": self.duration_in_previous,
            "trigger": self.trigger,
            "timestamp": self.timestamp,
        }


@dataclass
class TouchpointEvent:
    """A single touchpoint reached during a session."""

    event_id: str = field(default_factory=lambda: _new_id("tpe"))
    session_id: str = ""
    touchpoint: str = TouchPoint.MENU.value
    context: str = ""
    duration: float = 0.0
    outcome: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "touchpoint": self.touchpoint,
            "context": self.context,
            "duration": self.duration,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
        }


@dataclass
class EngagementReading:
    """A reading of the player's engagement at a moment in time.

    Captures the engagement level plus a normalized intensity
    (0..1), the focus of the player's attention, the balance between
    the challenge of the content and the player's perceived skill
    (a positive number means content is harder than skill) and a
    coarse skill level bucket.
    """

    reading_id: str = field(default_factory=lambda: _new_id("eng"))
    session_id: str = ""
    level: str = EngagementLevel.CASUAL.value
    intensity: float = 0.5
    attention_focus: str = ""
    challenge_balance: float = 0.0
    skill_level: str = "novice"
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reading_id": self.reading_id,
            "session_id": self.session_id,
            "level": self.level,
            "intensity": self.intensity,
            "attention_focus": self.attention_focus,
            "challenge_balance": self.challenge_balance,
            "skill_level": self.skill_level,
            "timestamp": self.timestamp,
        }


@dataclass
class EmotionSnapshot:
    """A single emotional reading observed during a session.

    Stores the discrete emotion signal, the intensity of the signal
    (0..1), the trigger that produced it, and the valence (a value
    in [-1, 1] where positive means a positive emotion).
    """

    snapshot_id: str = field(default_factory=lambda: _new_id("emo"))
    session_id: str = ""
    signal: str = EmotionSignal.JOY.value
    intensity: float = 0.5
    trigger: str = ""
    valence: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "session_id": self.session_id,
            "signal": self.signal,
            "intensity": self.intensity,
            "trigger": self.trigger,
            "valence": self.valence,
            "timestamp": self.timestamp,
        }


@dataclass
class FunnelState:
    """A marketing-style funnel for a single player.

    The funnel moves through ``FunnelPhase`` values from AWARENESS
    to ADVOCACY. ``entered_at`` records when the player entered the
    funnel, ``advanced_at`` is the most recent advance time,
    ``completed_at`` is set when the funnel is completed, and
    ``drop_off_reason`` is populated when the player drops off.
    """

    funnel_id: str = field(default_factory=lambda: _new_id("fun"))
    player_id: str = ""
    funnel_name: str = "default"
    current_phase: str = FunnelPhase.AWARENESS.value
    entered_at: str = field(default_factory=_now)
    advanced_at: str = ""
    completed_at: str = ""
    drop_off_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "funnel_id": self.funnel_id,
            "player_id": self.player_id,
            "funnel_name": self.funnel_name,
            "current_phase": self.current_phase,
            "entered_at": self.entered_at,
            "advanced_at": self.advanced_at,
            "completed_at": self.completed_at,
            "drop_off_reason": self.drop_off_reason,
        }


@dataclass
class JourneyStats:
    """Aggregate counters describing the player journey engine state."""

    total_sessions: int = 0
    active_sessions: int = 0
    completed_sessions: int = 0
    total_transitions: int = 0
    total_touchpoints: int = 0
    average_session_length: float = 0.0
    drop_off_rate: float = 0.0
    average_engagement: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "completed_sessions": self.completed_sessions,
            "total_transitions": self.total_transitions,
            "total_touchpoints": self.total_touchpoints,
            "average_session_length": self.average_session_length,
            "drop_off_rate": self.drop_off_rate,
            "average_engagement": self.average_engagement,
        }


@dataclass
class JourneySnapshot:
    """An immutable snapshot of the entire player journey engine."""

    initialized: bool = False
    sessions: List[JourneySession] = field(default_factory=list)
    events: List["JourneyEvent"] = field(default_factory=list)
    stats: JourneyStats = field(default_factory=JourneyStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "sessions": [s.to_dict() for s in self.sessions],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class JourneyEvent:
    """An audit event emitted by the player journey engine."""

    event_id: str = field(default_factory=lambda: _new_id("pevt"))
    kind: JourneyEventKind = JourneyEventKind.STAGE_ENTERED
    session_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "session_id": self.session_id,
            "payload": _to_jsonable(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Player Journey Engine (Singleton)
# ---------------------------------------------------------------------------


class PlayerJourneyEngine:
    """Track and analyze player journeys through the game.

    The engine records play sessions, the stage transitions and
    touchpoints reached during each session, engagement readings and
    emotion snapshots, and marketing-style funnels with phase
    progression and drop-off tracking. Every record is also surfaced
    as a ``JourneyEvent`` audit entry so the journey can be replayed
    end-to-end.

    Implements the singleton pattern with double-checked locking
    using ``threading.RLock`` for thread-safe access. All public
    methods are guarded by the re-entrant lock. Consumers should
    obtain the instance through :meth:`get_instance` or the
    module-level :func:`get_player_journey` factory.

    Usage:
        engine = get_player_journey()
        session = engine.start_session("player_42", "session_1")
        engine.record_stage_transition(
            session.session_id,
            JourneyStage.TUTORIAL,
            JourneyStage.EXPLORATION,
            duration_in_previous=120.0,
            trigger="tutorial_complete",
        )
        engine.end_session(session.session_id, drop_off_stage="")
        print(engine.get_status())
    """

    _instance: Optional["PlayerJourneyEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "PlayerJourneyEngine":
        # Double-checked locking: acquire the lock only when the
        # instance has not yet been created. The freshly allocated
        # instance is marked as not-yet-initialized so that __init__
        # performs the real one-time setup.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "PlayerJourneyEngine":
        """Return the singleton engine instance (constructs on first use)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # One-time initialization guard. The outer check avoids taking
        # the lock on the hot path once initialization is complete; the
        # inner check prevents a race between two threads that both
        # observed _initialized as False.
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Primary stores.
            self._sessions: Dict[str, JourneySession] = {}
            self._transitions: Dict[str, StageTransition] = {}
            self._touchpoints: Dict[str, TouchpointEvent] = {}
            self._readings: Dict[str, EngagementReading] = {}
            self._emotions: Dict[str, EmotionSnapshot] = {}
            self._funnels: Dict[str, FunnelState] = {}
            self._events: List[JourneyEvent] = []

            # Per-session index maps so accessor methods do not have
            # to scan the global stores.
            self._transitions_by_session: Dict[str, List[str]] = {}
            self._touchpoints_by_session: Dict[str, List[str]] = {}
            self._readings_by_session: Dict[str, List[str]] = {}
            self._emotions_by_session: Dict[str, List[str]] = {}

            # Aggregate counters maintained for fast stats retrieval.
            self._session_counter: int = 0
            self._transition_counter: int = 0
            self._touchpoint_counter: int = 0
            self._reading_counter: int = 0
            self._emotion_counter: int = 0
            self._funnel_counter: int = 0
            self._event_counter: int = 0
            self._completed_session_counter: int = 0
            self._drop_off_counter: int = 0

            self._initialized: bool = True

            # Populate the default seed journey data.
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with seed sessions, transitions and events.

        The seed demonstrates a small but representative journey data
        set:

          - 3 sessions (one already ended with a drop-off, one active,
            one completed cleanly).
          - 8 stage transitions across the three sessions.
          - 12 touchpoint events covering menus, gameplay, dialogue
            and combat.
          - 6 engagement readings ranging from CASUAL to FLOW.
          - 5 emotion snapshots including JOY, FRUSTRATION and
            EXCITEMENT.
          - 4 funnel states at varying phases of progression.
          - 10 audit events covering the major event kinds.
        """
        # ------------------------------------------------------------------
        # Session 1: a clean completion.
        # ------------------------------------------------------------------
        s1 = self.start_session(player_id="player_alpha", session_id="seed_session_1")
        s1.metadata = {"seed": True, "platform": "pc", "build": "1.0.0"}
        self.record_stage_transition(
            session_id=s1.session_id,
            from_stage=JourneyStage.TUTORIAL,
            to_stage=JourneyStage.EXPLORATION,
            duration_in_previous=95.0,
            trigger="tutorial_complete",
        )
        self.record_stage_transition(
            session_id=s1.session_id,
            from_stage=JourneyStage.EXPLORATION,
            to_stage=JourneyStage.DISCOVERY,
            duration_in_previous=420.0,
            trigger="new_area_unlocked",
        )
        self.record_stage_transition(
            session_id=s1.session_id,
            from_stage=JourneyStage.DISCOVERY,
            to_stage=JourneyStage.CHALLENGE,
            duration_in_previous=180.0,
            trigger="boss_encounter",
        )
        self.record_stage_transition(
            session_id=s1.session_id,
            from_stage=JourneyStage.CHALLENGE,
            to_stage=JourneyStage.RESOLUTION,
            duration_in_previous=300.0,
            trigger="boss_defeated",
        )
        self.record_touchpoint(
            session_id=s1.session_id,
            touchpoint=TouchPoint.MENU,
            context="main_menu",
            duration=12.0,
            outcome="navigate_to_continue",
        )
        self.record_touchpoint(
            session_id=s1.session_id,
            touchpoint=TouchPoint.GAMEPLAY,
            context="tutorial_island",
            duration=95.0,
            outcome="tutorial_finished",
        )
        self.record_touchpoint(
            session_id=s1.session_id,
            touchpoint=TouchPoint.BATTLE,
            context="tutorial_combat",
            duration=45.0,
            outcome="victory",
        )
        self.record_touchpoint(
            session_id=s1.session_id,
            touchpoint=TouchPoint.ACHIEVEMENT,
            context="first_kill",
            duration=2.0,
            outcome="shown",
        )
        self.record_engagement(
            session_id=s1.session_id,
            level=EngagementLevel.INVOLVED,
            intensity=0.6,
            attention_focus="tutorial",
            challenge_balance=-0.2,
            skill_level="novice",
        )
        self.record_engagement(
            session_id=s1.session_id,
            level=EngagementLevel.IMMERSED,
            intensity=0.8,
            attention_focus="boss",
            challenge_balance=0.3,
            skill_level="intermediate",
        )
        self.record_emotion(
            session_id=s1.session_id,
            signal=EmotionSignal.JOY,
            intensity=0.7,
            trigger="tutorial_complete",
            valence=0.8,
        )
        self.record_emotion(
            session_id=s1.session_id,
            signal=EmotionSignal.EXCITEMENT,
            intensity=0.9,
            trigger="boss_encounter",
            valence=0.7,
        )
        # End the session cleanly.
        self.end_session(session_id=s1.session_id, drop_off_stage="")

        # ------------------------------------------------------------------
        # Session 2: an active session, not yet ended.
        # ------------------------------------------------------------------
        s2 = self.start_session(player_id="player_beta", session_id="seed_session_2")
        s2.metadata = {"seed": True, "platform": "console", "build": "1.0.0"}
        self.record_stage_transition(
            session_id=s2.session_id,
            from_stage=JourneyStage.TUTORIAL,
            to_stage=JourneyStage.EXPLORATION,
            duration_in_previous=110.0,
            trigger="tutorial_complete",
        )
        self.record_stage_transition(
            session_id=s2.session_id,
            from_stage=JourneyStage.EXPLORATION,
            to_stage=JourneyStage.CHALLENGE,
            duration_in_previous=250.0,
            trigger="ambush",
        )
        self.record_touchpoint(
            session_id=s2.session_id,
            touchpoint=TouchPoint.DIALOGUE,
            context="npc_intro",
            duration=35.0,
            outcome="continued",
        )
        self.record_touchpoint(
            session_id=s2.session_id,
            touchpoint=TouchPoint.BATTLE,
            context="ambush",
            duration=60.0,
            outcome="in_progress",
        )
        self.record_touchpoint(
            session_id=s2.session_id,
            touchpoint=TouchPoint.PAUSE,
            context="pause_menu",
            duration=8.0,
            outcome="resumed",
        )
        self.record_touchpoint(
            session_id=s2.session_id,
            touchpoint=TouchPoint.INVENTORY,
            context="loot_review",
            duration=15.0,
            outcome="equipped",
        )
        self.record_engagement(
            session_id=s2.session_id,
            level=EngagementLevel.FLOW,
            intensity=0.95,
            attention_focus="ambush",
            challenge_balance=0.0,
            skill_level="intermediate",
        )
        self.record_engagement(
            session_id=s2.session_id,
            level=EngagementLevel.IMMERSED,
            intensity=0.85,
            attention_focus="npc_intro",
            challenge_balance=-0.1,
            skill_level="intermediate",
        )
        self.record_emotion(
            session_id=s2.session_id,
            signal=EmotionSignal.ANXIETY,
            intensity=0.5,
            trigger="ambush",
            valence=-0.3,
        )
        self.record_emotion(
            session_id=s2.session_id,
            signal=EmotionSignal.SURPRISE,
            intensity=0.7,
            trigger="ambush_trigger",
            valence=0.1,
        )

        # ------------------------------------------------------------------
        # Session 3: a session that ended with a drop-off.
        # ------------------------------------------------------------------
        s3 = self.start_session(player_id="player_gamma", session_id="seed_session_3")
        s3.metadata = {"seed": True, "platform": "mobile", "build": "1.0.0"}
        self.record_stage_transition(
            session_id=s3.session_id,
            from_stage=JourneyStage.TUTORIAL,
            to_stage=JourneyStage.EXPLORATION,
            duration_in_previous=80.0,
            trigger="tutorial_complete",
        )
        self.record_stage_transition(
            session_id=s3.session_id,
            from_stage=JourneyStage.EXPLORATION,
            to_stage=JourneyStage.CHALLENGE,
            duration_in_previous=60.0,
            trigger="tutorial_boss",
        )
        self.record_touchpoint(
            session_id=s3.session_id,
            touchpoint=TouchPoint.MENU,
            context="main_menu",
            duration=5.0,
            outcome="navigate_to_new_game",
        )
        self.record_touchpoint(
            session_id=s3.session_id,
            touchpoint=TouchPoint.GAMEPLAY,
            context="tutorial",
            duration=80.0,
            outcome="tutorial_finished",
        )
        self.record_touchpoint(
            session_id=s3.session_id,
            touchpoint=TouchPoint.BATTLE,
            context="tutorial_boss",
            duration=20.0,
            outcome="died",
        )
        self.record_touchpoint(
            session_id=s3.session_id,
            touchpoint=TouchPoint.DEATH,
            context="tutorial_boss",
            duration=3.0,
            outcome="game_over",
        )
        self.record_engagement(
            session_id=s3.session_id,
            level=EngagementLevel.CASUAL,
            intensity=0.4,
            attention_focus="tutorial",
            challenge_balance=0.5,
            skill_level="novice",
        )
        self.record_engagement(
            session_id=s3.session_id,
            level=EngagementLevel.DISENGAGED,
            intensity=0.2,
            attention_focus="none",
            challenge_balance=0.8,
            skill_level="novice",
        )
        self.record_emotion(
            session_id=s3.session_id,
            signal=EmotionSignal.FRUSTRATION,
            intensity=0.8,
            trigger="tutorial_boss",
            valence=-0.7,
        )
        # End the session with a drop-off.
        self.end_session(
            session_id=s3.session_id,
            drop_off_stage=JourneyStage.CHALLENGE.value,
        )
        # Record a drop-off event for the session.
        # The funnel for player_gamma will be set up below and we
        # drop it off so the audit log has a DROP_OFF_RECORDED event.

        # ------------------------------------------------------------------
        # Funnels: 4 funnel states at varying phases.
        # ------------------------------------------------------------------
        f1 = self.create_funnel(player_id="player_alpha", funnel_name="onboarding")
        self.advance_funnel(
            funnel_id=f1.funnel_id, new_phase=FunnelPhase.INTEREST
        )
        self.advance_funnel(
            funnel_id=f1.funnel_id, new_phase=FunnelPhase.TRIAL
        )
        self.advance_funnel(
            funnel_id=f1.funnel_id, new_phase=FunnelPhase.ENGAGEMENT
        )
        self.advance_funnel(
            funnel_id=f1.funnel_id, new_phase=FunnelPhase.RETENTION
        )
        self.complete_funnel(funnel_id=f1.funnel_id)

        f2 = self.create_funnel(player_id="player_beta", funnel_name="onboarding")
        self.advance_funnel(
            funnel_id=f2.funnel_id, new_phase=FunnelPhase.INTEREST
        )
        self.advance_funnel(
            funnel_id=f2.funnel_id, new_phase=FunnelPhase.TRIAL
        )

        f3 = self.create_funnel(player_id="player_gamma", funnel_name="onboarding")
        self.advance_funnel(
            funnel_id=f3.funnel_id, new_phase=FunnelPhase.INTEREST
        )
        self.advance_funnel(
            funnel_id=f3.funnel_id, new_phase=FunnelPhase.TRIAL
        )
        self.record_drop_off(
            funnel_id=f3.funnel_id, reason=DropOffReason.DIFFICULTY
        )

        f4 = self.create_funnel(player_id="player_delta", funnel_name="season_pass")
        self.advance_funnel(
            funnel_id=f4.funnel_id, new_phase=FunnelPhase.INTEREST
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: JourneyEventKind,
        session_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> JourneyEvent:
        """Record an audit event (caller must hold ``self._lock``).

        Returns the created JourneyEvent. Evicts the oldest event
        when the event store is at capacity.
        """
        event = JourneyEvent(
            kind=kind,
            session_id=session_id,
            payload=dict(payload) if payload else {},
        )
        _evict_fifo_list(self._events, _MAX_EVENTS)
        self._events.append(event)
        self._event_counter += 1
        return event

    def _compute_engagement_average(self) -> float:
        """Return the mean engagement intensity across all readings.

        Returns 0.0 when no readings are present. Caller must hold
        ``self._lock``.
        """
        if not self._readings:
            return 0.0
        total = 0.0
        for r in self._readings.values():
            total += max(0.0, min(1.0, float(r.intensity)))
        return total / float(len(self._readings))

    def _average_session_length(self) -> float:
        """Return the mean session duration in seconds.

        Returns 0.0 when no sessions are present. Caller must hold
        ``self._lock``.
        """
        if not self._sessions:
            return 0.0
        total = 0.0
        for s in self._sessions.values():
            total += max(0.0, float(s.total_duration))
        return total / float(len(self._sessions))

    def _drop_off_rate(self) -> float:
        """Return the fraction of sessions that ended with a drop-off.

        Returns 0.0 when no sessions are present. Caller must hold
        ``self._lock``.
        """
        if not self._sessions:
            return 0.0
        dropped = 0
        for s in self._sessions.values():
            if s.drop_off_stage:
                dropped += 1
        return float(dropped) / float(len(self._sessions))

    def _active_sessions(self) -> int:
        """Return the count of currently active (not ended) sessions.

        Caller must hold ``self._lock``.
        """
        return sum(1 for s in self._sessions.values() if not s.ended_at)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(
        self, player_id: str, session_id: Optional[str] = None
    ) -> JourneySession:
        """Start a new play session for ``player_id``.

        When ``session_id`` is omitted (or empty), a new id is
        generated. The session is registered in the global store and
        a STAGE_ENTERED event is recorded for the initial TUTORIAL
        stage.

        Returns:
            The newly created JourneySession.
        """
        with self._lock:
            if not session_id:
                session_id = _new_id("session")
            session = JourneySession(
                session_id=session_id,
                player_id=player_id,
                current_stage=JourneyStage.TUTORIAL.value,
                current_engagement=EngagementLevel.CASUAL.value,
            )
            # Enforce the bounded session store cap via FIFO eviction.
            _evict_fifo_dict(self._sessions, _MAX_SESSIONS)
            self._sessions[session.session_id] = session
            self._session_counter += 1
            self._transitions_by_session.setdefault(session.session_id, [])
            self._touchpoints_by_session.setdefault(session.session_id, [])
            self._readings_by_session.setdefault(session.session_id, [])
            self._emotions_by_session.setdefault(session.session_id, [])
            self._record_event(
                kind=JourneyEventKind.STAGE_ENTERED,
                session_id=session.session_id,
                payload={
                    "player_id": player_id,
                    "stage": JourneyStage.TUTORIAL.value,
                },
            )
            return session

    def end_session(
        self, session_id: str, drop_off_stage: str = ""
    ) -> Optional[JourneySession]:
        """End a previously started session.

        Sets the session's ``ended_at`` timestamp, the total
        accumulated duration (sum of the durations of the recorded
        touchpoints, falling back to 0) and an optional drop-off
        stage. Records a MILESTONE_REACHED event for the end. When
        a drop-off stage is provided, a DROP_OFF_RECORDED event is
        also recorded.

        Returns:
            The updated JourneySession, or None when no session
            matches ``session_id``.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.ended_at = _now()
            if drop_off_stage:
                # Coerce to a plain string so the value is always JSON-friendly.
                if isinstance(drop_off_stage, JourneyStage):
                    drop_off_stage = drop_off_stage.value
                else:
                    drop_off_stage = str(drop_off_stage)
                session.drop_off_stage = drop_off_stage
                self._drop_off_counter += 1
            else:
                self._completed_session_counter += 1
            total_duration = 0.0
            for tp_id in self._touchpoints_by_session.get(session_id, []):
                tp = self._touchpoints.get(tp_id)
                if tp is not None:
                    total_duration += max(0.0, float(tp.duration))
            if total_duration > 0.0:
                session.total_duration = total_duration
            self._record_event(
                kind=JourneyEventKind.MILESTONE_REACHED,
                session_id=session_id,
                payload={
                    "ended_at": session.ended_at,
                    "total_duration": session.total_duration,
                    "drop_off_stage": session.drop_off_stage,
                },
            )
            if session.drop_off_stage:
                self._record_event(
                    kind=JourneyEventKind.DROP_OFF_RECORDED,
                    session_id=session_id,
                    payload={
                        "drop_off_stage": session.drop_off_stage,
                        "player_id": session.player_id,
                    },
                )
            return session

    # ------------------------------------------------------------------
    # Session data capture
    # ------------------------------------------------------------------

    def record_stage_transition(
        self,
        session_id: str,
        from_stage: JourneyStage,
        to_stage: JourneyStage,
        duration_in_previous: float,
        trigger: str = "",
    ) -> StageTransition:
        """Record a transition between two stages within a session.

        Updates the session's ``current_stage`` and appends the new
        stage to ``stages_visited``. Records a STAGE_ENTERED audit
        event.

        Returns:
            The newly created StageTransition.
        """
        with self._lock:
            from_value = from_stage.value if isinstance(from_stage, JourneyStage) else str(from_stage)
            to_value = to_stage.value if isinstance(to_stage, JourneyStage) else str(to_stage)
            transition = StageTransition(
                session_id=session_id,
                from_stage=from_value,
                to_stage=to_value,
                duration_in_previous=max(0.0, float(duration_in_previous)),
                trigger=trigger or "",
            )
            # Enforce the bounded transition store cap via FIFO eviction.
            _evict_fifo_dict(self._transitions, _MAX_TRANSITIONS_PER_SESSION * 4)
            self._transitions[transition.transition_id] = transition
            self._transition_counter += 1
            ids = self._transitions_by_session.setdefault(session_id, [])
            ids.append(transition.transition_id)
            _evict_fifo_list(ids, _MAX_TRANSITIONS_PER_SESSION)
            session = self._sessions.get(session_id)
            if session is not None:
                session.current_stage = to_value
                if to_value not in session.stages_visited:
                    session.stages_visited.append(to_value)
            self._record_event(
                kind=JourneyEventKind.STAGE_ENTERED,
                session_id=session_id,
                payload={
                    "from_stage": from_value,
                    "to_stage": to_value,
                    "trigger": trigger or "",
                    "duration_in_previous": transition.duration_in_previous,
                },
            )
            return transition

    def record_touchpoint(
        self,
        session_id: str,
        touchpoint: TouchPoint,
        context: str = "",
        duration: float = 0.0,
        outcome: str = "",
    ) -> TouchpointEvent:
        """Record a touchpoint reached during a session.

        Appends the touchpoint id to the session's
        ``touchpoints_reached`` list and emits a TOUCHPOINT_REACHED
        audit event.

        Returns:
            The newly created TouchpointEvent.
        """
        with self._lock:
            tp_value = touchpoint.value if isinstance(touchpoint, TouchPoint) else str(touchpoint)
            event = TouchpointEvent(
                session_id=session_id,
                touchpoint=tp_value,
                context=context or "",
                duration=max(0.0, float(duration)),
                outcome=outcome or "",
            )
            _evict_fifo_dict(self._touchpoints, _MAX_TOUCHPOINTS_PER_SESSION * 4)
            self._touchpoints[event.event_id] = event
            self._touchpoint_counter += 1
            ids = self._touchpoints_by_session.setdefault(session_id, [])
            ids.append(event.event_id)
            _evict_fifo_list(ids, _MAX_TOUCHPOINTS_PER_SESSION)
            session = self._sessions.get(session_id)
            if session is not None:
                if tp_value not in session.touchpoints_reached:
                    session.touchpoints_reached.append(tp_value)
            self._record_event(
                kind=JourneyEventKind.TOUCHPOINT_REACHED,
                session_id=session_id,
                payload={
                    "touchpoint": tp_value,
                    "context": context or "",
                    "duration": event.duration,
                    "outcome": outcome or "",
                },
            )
            return event

    def record_engagement(
        self,
        session_id: str,
        level: EngagementLevel,
        intensity: float,
        attention_focus: str = "",
        challenge_balance: float = 0.0,
        skill_level: str = "novice",
    ) -> EngagementReading:
        """Record an engagement reading for a session.

        Updates the session's ``current_engagement`` and emits an
        ENGAGEMENT_CHANGED audit event.

        Returns:
            The newly created EngagementReading.
        """
        with self._lock:
            level_value = level.value if isinstance(level, EngagementLevel) else str(level)
            reading = EngagementReading(
                session_id=session_id,
                level=level_value,
                intensity=max(0.0, min(1.0, float(intensity))),
                attention_focus=attention_focus or "",
                challenge_balance=float(challenge_balance),
                skill_level=skill_level or "novice",
            )
            _evict_fifo_dict(self._readings, _MAX_READINGS_PER_SESSION * 4)
            self._readings[reading.reading_id] = reading
            self._reading_counter += 1
            ids = self._readings_by_session.setdefault(session_id, [])
            ids.append(reading.reading_id)
            _evict_fifo_list(ids, _MAX_READINGS_PER_SESSION)
            session = self._sessions.get(session_id)
            if session is not None:
                session.current_engagement = level_value
            self._record_event(
                kind=JourneyEventKind.ENGAGEMENT_CHANGED,
                session_id=session_id,
                payload={
                    "level": level_value,
                    "intensity": reading.intensity,
                    "attention_focus": reading.attention_focus,
                    "challenge_balance": reading.challenge_balance,
                    "skill_level": reading.skill_level,
                },
            )
            return reading

    def record_emotion(
        self,
        session_id: str,
        signal: EmotionSignal,
        intensity: float,
        trigger: str = "",
        valence: float = 0.0,
    ) -> EmotionSnapshot:
        """Record an emotion snapshot for a session.

        Emits an EMOTION_DETECTED audit event.

        Returns:
            The newly created EmotionSnapshot.
        """
        with self._lock:
            signal_value = signal.value if isinstance(signal, EmotionSignal) else str(signal)
            snapshot = EmotionSnapshot(
                session_id=session_id,
                signal=signal_value,
                intensity=max(0.0, min(1.0, float(intensity))),
                trigger=trigger or "",
                valence=max(-1.0, min(1.0, float(valence))),
            )
            _evict_fifo_dict(self._emotions, _MAX_EMOTIONS_PER_SESSION * 4)
            self._emotions[snapshot.snapshot_id] = snapshot
            self._emotion_counter += 1
            ids = self._emotions_by_session.setdefault(session_id, [])
            ids.append(snapshot.snapshot_id)
            _evict_fifo_list(ids, _MAX_EMOTIONS_PER_SESSION)
            self._record_event(
                kind=JourneyEventKind.EMOTION_DETECTED,
                session_id=session_id,
                payload={
                    "signal": signal_value,
                    "intensity": snapshot.intensity,
                    "trigger": trigger or "",
                    "valence": snapshot.valence,
                },
            )
            return snapshot

    # ------------------------------------------------------------------
    # Funnels
    # ------------------------------------------------------------------

    def create_funnel(
        self, player_id: str, funnel_name: str = "default"
    ) -> FunnelState:
        """Create a new funnel state for ``player_id``.

        The funnel starts in the AWARENESS phase and is recorded in
        the global funnel store. A FUNNEL_TRANSITION audit event is
        emitted for the initial phase entry.

        Returns:
            The newly created FunnelState.
        """
        with self._lock:
            funnel = FunnelState(
                player_id=player_id,
                funnel_name=funnel_name or "default",
                current_phase=FunnelPhase.AWARENESS.value,
            )
            _evict_fifo_dict(self._funnels, _MAX_FUNNELS)
            self._funnels[funnel.funnel_id] = funnel
            self._funnel_counter += 1
            self._record_event(
                kind=JourneyEventKind.FUNNEL_TRANSITION,
                session_id="",
                payload={
                    "funnel_id": funnel.funnel_id,
                    "player_id": player_id,
                    "funnel_name": funnel.funnel_name,
                    "new_phase": FunnelPhase.AWARENESS.value,
                },
            )
            return funnel

    def advance_funnel(
        self, funnel_id: str, new_phase: FunnelPhase
    ) -> Optional[FunnelState]:
        """Advance a funnel to a new phase.

        Sets the funnel's ``current_phase`` and ``advanced_at``
        timestamp. A FUNNEL_TRANSITION audit event is emitted. When
        the new phase is ADVOCACY, the funnel is also marked as
        completed (mirroring :meth:`complete_funnel`).

        Returns:
            The updated FunnelState, or None when no funnel matches
            ``funnel_id``.
        """
        with self._lock:
            funnel = self._funnels.get(funnel_id)
            if funnel is None:
                return None
            new_value = new_phase.value if isinstance(new_phase, FunnelPhase) else str(new_phase)
            previous = funnel.current_phase
            funnel.current_phase = new_value
            funnel.advanced_at = _now()
            if new_value == FunnelPhase.ADVOCACY.value and not funnel.completed_at:
                funnel.completed_at = funnel.advanced_at
            self._record_event(
                kind=JourneyEventKind.FUNNEL_TRANSITION,
                session_id="",
                payload={
                    "funnel_id": funnel_id,
                    "previous_phase": previous,
                    "new_phase": new_value,
                    "player_id": funnel.player_id,
                },
            )
            return funnel

    def complete_funnel(self, funnel_id: str) -> Optional[FunnelState]:
        """Mark a funnel as completed.

        Sets the funnel's ``completed_at`` timestamp and records a
        MILESTONE_REACHED audit event. The phase is forced to
        ADVOCACY when the funnel is not already past it.

        Returns:
            The updated FunnelState, or None when no funnel matches
            ``funnel_id``.
        """
        with self._lock:
            funnel = self._funnels.get(funnel_id)
            if funnel is None:
                return None
            if not funnel.completed_at:
                funnel.completed_at = _now()
            if funnel.current_phase != FunnelPhase.ADVOCACY.value:
                previous = funnel.current_phase
                funnel.current_phase = FunnelPhase.ADVOCACY.value
                funnel.advanced_at = funnel.completed_at
                self._record_event(
                    kind=JourneyEventKind.FUNNEL_TRANSITION,
                    session_id="",
                    payload={
                        "funnel_id": funnel_id,
                        "previous_phase": previous,
                        "new_phase": FunnelPhase.ADVOCACY.value,
                        "player_id": funnel.player_id,
                        "auto_promoted": True,
                    },
                )
            self._record_event(
                kind=JourneyEventKind.MILESTONE_REACHED,
                session_id="",
                payload={
                    "funnel_id": funnel_id,
                    "player_id": funnel.player_id,
                    "funnel_name": funnel.funnel_name,
                    "completed_at": funnel.completed_at,
                },
            )
            return funnel

    def record_drop_off(
        self, funnel_id: str, reason: DropOffReason
    ) -> Optional[FunnelState]:
        """Record a drop-off on a funnel.

        Sets the funnel's ``drop_off_reason`` and emits a
        DROP_OFF_RECORDED audit event.

        Returns:
            The updated FunnelState, or None when no funnel matches
            ``funnel_id``.
        """
        with self._lock:
            funnel = self._funnels.get(funnel_id)
            if funnel is None:
                return None
            reason_value = reason.value if isinstance(reason, DropOffReason) else str(reason)
            funnel.drop_off_reason = reason_value
            self._record_event(
                kind=JourneyEventKind.DROP_OFF_RECORDED,
                session_id="",
                payload={
                    "funnel_id": funnel_id,
                    "player_id": funnel.player_id,
                    "funnel_name": funnel.funnel_name,
                    "reason": reason_value,
                    "phase": funnel.current_phase,
                },
            )
            return funnel

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_sessions(self) -> List[JourneySession]:
        """Return a copy of all sessions (oldest first)."""
        with self._lock:
            return list(self._sessions.values())

    def get_session(self, session_id: str) -> Optional[JourneySession]:
        """Return a copy of the session matching ``session_id``.

        Returns None when the session is not registered.
        """
        with self._lock:
            return self._sessions.get(session_id)

    def get_transitions(self, session_id: str) -> List[StageTransition]:
        """Return all stage transitions recorded for ``session_id``.

        Returns an empty list when the session is unknown.
        """
        with self._lock:
            ids = self._transitions_by_session.get(session_id, [])
            return [self._transitions[i] for i in ids if i in self._transitions]

    def get_touchpoints(self, session_id: str) -> List[TouchpointEvent]:
        """Return all touchpoint events recorded for ``session_id``."""
        with self._lock:
            ids = self._touchpoints_by_session.get(session_id, [])
            return [self._touchpoints[i] for i in ids if i in self._touchpoints]

    def get_engagement_readings(self, session_id: str) -> List[EngagementReading]:
        """Return all engagement readings for ``session_id``."""
        with self._lock:
            ids = self._readings_by_session.get(session_id, [])
            return [self._readings[i] for i in ids if i in self._readings]

    def get_emotion_snapshots(self, session_id: str) -> List[EmotionSnapshot]:
        """Return all emotion snapshots for ``session_id``."""
        with self._lock:
            ids = self._emotions_by_session.get(session_id, [])
            return [self._emotions[i] for i in ids if i in self._emotions]

    def get_funnels(self) -> List[FunnelState]:
        """Return a copy of all funnels (oldest first)."""
        with self._lock:
            return list(self._funnels.values())

    def list_events(self, limit: int = 100) -> List[JourneyEvent]:
        """Return audit events limited to the most recent ``limit`` entries.

        A non-positive ``limit`` returns an empty list.
        """
        with self._lock:
            events = list(self._events)
        if limit <= 0:
            return []
        return events[-limit:]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_stats(self) -> JourneyStats:
        """Compute aggregate statistics from the current engine state."""
        with self._lock:
            return JourneyStats(
                total_sessions=len(self._sessions),
                active_sessions=self._active_sessions(),
                completed_sessions=self._completed_session_counter,
                total_transitions=len(self._transitions),
                total_touchpoints=len(self._touchpoints),
                average_session_length=self._average_session_length(),
                drop_off_rate=self._drop_off_rate(),
                average_engagement=self._compute_engagement_average(),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current player journey engine state.

        The ``initialized`` flag is always the first key in the
        returned dictionary, followed by store counts, aggregate
        counters and the computed stats block.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "session_count": len(self._sessions),
                "transition_count": len(self._transitions),
                "touchpoint_count": len(self._touchpoints),
                "reading_count": len(self._readings),
                "emotion_count": len(self._emotions),
                "funnel_count": len(self._funnels),
                "event_count": len(self._events),
                "session_counter": self._session_counter,
                "transition_counter": self._transition_counter,
                "touchpoint_counter": self._touchpoint_counter,
                "reading_counter": self._reading_counter,
                "emotion_counter": self._emotion_counter,
                "funnel_counter": self._funnel_counter,
                "event_counter": self._event_counter,
                "completed_session_counter": self._completed_session_counter,
                "drop_off_counter": self._drop_off_counter,
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> JourneySnapshot:
        """Capture an immutable snapshot of the player journey engine."""
        with self._lock:
            stats = self.get_stats()
            return JourneySnapshot(
                initialized=self._initialized,
                sessions=list(self._sessions.values()),
                events=list(self._events),
                stats=stats,
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with default data.

        Restores the engine to its initial state, including the seed
        sessions, transitions, touchpoints, readings, emotions,
        funnels and audit events.
        """
        with self._lock:
            self._sessions.clear()
            self._transitions.clear()
            self._touchpoints.clear()
            self._readings.clear()
            self._emotions.clear()
            self._funnels.clear()
            self._events.clear()
            self._transitions_by_session.clear()
            self._touchpoints_by_session.clear()
            self._readings_by_session.clear()
            self._emotions_by_session.clear()
            self._session_counter = 0
            self._transition_counter = 0
            self._touchpoint_counter = 0
            self._reading_counter = 0
            self._emotion_counter = 0
            self._funnel_counter = 0
            self._event_counter = 0
            self._completed_session_counter = 0
            self._drop_off_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_player_journey() -> PlayerJourneyEngine:
    """Return the singleton PlayerJourneyEngine instance."""
    return PlayerJourneyEngine.get_instance()
