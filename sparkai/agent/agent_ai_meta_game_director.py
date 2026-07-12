"""
SparkLabs Agent - AI Meta Game Director

A novel AI-native agent that manages cross-session meta-narrative, tracking
long-term player progression patterns and adjusting the game world's meta-state
across multiple play sessions. Where most directors operate within a single
session, this director builds a persistent memory layer that spans the entire
lifetime of a player's relationship with the game world.

The director treats each play session as one chapter in a much longer story.
It remembers what the player did last week, weaves those memories into the
current session, and quietly reshapes the world so that past choices keep
echoing forward. This is the layer that makes a game world feel like it has a
memory of its own.

Core design principles:
  - Sessions are chapters, not islands. Every session feeds a persistent
    meta-narrative that grows across play sessions.
  - The world remembers. Player actions leave durable marks on the world
    meta-state that surface in later sessions.
  - Arcs span sessions. Story arcs unfold over many sessions, with each
    session advancing the arc by one beat.
  - Players reveal archetypes over time. Behavior across many sessions is
    more diagnostic than behavior within a single session.
  - Threads weave together. Narrative threads planted in one session can
    resurface and connect to events in a distant future session.
  - Decisions compound. World-level decisions accumulate and shift the world
    meta-state in ways that no single session could.
  - Milestones persist. Significant achievements are tracked across the full
    player history, not just the current session.
  - Meta events call back. Generated events can tie back to specific past
    sessions, creating a sense of continuity.

Architecture:
  AIMetaGameDirector (thread-safe singleton)
    |-- Enums: MetaPhase, MetaArcType, MetaStatus, ProgressionPattern,
    |   WorldMetaState, MetaEventKind, PlayerArchetype, SessionType
    |-- Data: PlayerSession, MetaArc, MetaThread, WorldMetaSnapshot,
    |   ProgressionMilestone, PlayerArchetypeProfile, MetaDecision,
    |   MetaConfig, MetaStats, MetaSnapshot, MetaEvent, CrossSessionLink
    |-- Factory: get_ai_meta_game_director (auto-initializes on first call)

Core Capabilities:
  - register_player / remove_player / get_player / list_players
  - record_session / analyze_session / get_session_history
  - register_meta_arc / start_meta_arc / advance_meta_arc / complete_meta_arc
    / get_meta_arc / list_meta_arcs
  - register_meta_thread / weave_thread / get_meta_thread / list_meta_threads
  - detect_player_archetype / get_player_archetype / list_archetypes
  - create_meta_decision / apply_meta_decision / list_meta_decisions
  - register_milestone / check_milestone / list_milestones
  - capture_world_snapshot / get_world_snapshot / list_world_snapshots
  - find_cross_session_links / get_cross_session_links
  - generate_meta_event / list_meta_events
  - get_stats / get_snapshot / get_status / get_config / set_config
  - tick / list_events / reset
"""

from __future__ import annotations

import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PLAYERS: int = 5000
_MAX_SESSIONS: int = 50000
_MAX_META_ARCS: int = 1000
_MAX_META_THREADS: int = 4000
_MAX_MILESTONES: int = 20000
_MAX_DECISIONS: int = 5000
_MAX_WORLD_SNAPSHOTS: int = 2000
_MAX_META_EVENTS: int = 30000
_MAX_CROSS_SESSION_LINKS: int = 20000
_MAX_EVENTS: int = 20000
_SNAPSHOT_INTERVAL_TICKS: int = 50


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MetaPhase(str, Enum):
    """Lifecycle phase of a meta-arc as it unfolds across sessions."""
    DORMANT = "dormant"
    EMERGING = "emerging"
    DEVELOPING = "developing"
    CULMINATING = "culminating"
    CLIMAX = "climax"
    RESOLVING = "resolving"
    CONCLUDED = "concluded"
    ABANDONED = "abandoned"


class MetaArcType(str, Enum):
    """The narrative shape a cross-session meta-arc can take."""
    CHARACTER_GROWTH = "character_growth"
    WORLD_EVOLUTION = "world_evolution"
    MYSTERY_UNFOLDING = "mystery_unfolding"
    CONFLICT_ESCALATION = "conflict_escalation"
    RELATIONSHIP_DEEPENING = "relationship_deepening"
    DISCOVERY = "discovery"
    REDEMPTION = "redemption"
    DOWNFALL = "downfall"
    LEGACY_BUILDING = "legacy_building"
    PROPHECY_FULFILLMENT = "prophecy_fulfillment"


class MetaStatus(str, Enum):
    """Operational status for meta-level entities."""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class ProgressionPattern(str, Enum):
    """How a player's progression is distributed over time."""
    LINEAR = "linear"
    BURSTY = "bursty"
    STEADY = "steady"
    ERRATIC = "erratic"
    DEEP_DIVE = "deep_dive"
    COMPLETIONIST = "completionist"
    EXPLORATORY = "exploratory"
    SPEEDRUN = "speedrun"
    MASTERY = "mastery"
    SOCIAL = "social"


class WorldMetaState(str, Enum):
    """Macro-level state of the game world across sessions."""
    STABLE = "stable"
    TURBULENT = "turbulent"
    CRISIS = "crisis"
    FLOURISHING = "flourishing"
    DECAYING = "decaying"
    TRANSFORMING = "transforming"
    BALANCED = "balanced"
    VOLATILE = "volatile"


class MetaEventKind(str, Enum):
    """Kinds of events emitted by the meta-narrative layer."""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ARC_ADVANCE = "arc_advance"
    ARC_COMPLETE = "arc_complete"
    THREAD_WEAVE = "thread_weave"
    MILESTONE_REACHED = "milestone_reached"
    ARCHETYPE_SHIFT = "archetype_shift"
    WORLD_SHIFT = "world_shift"
    DECISION_APPLIED = "decision_applied"
    CROSS_SESSION_CALLBACK = "cross_session_callback"
    SNAPSHOT_CAPTURED = "snapshot_captured"
    META_REVEAL = "meta_reveal"


class PlayerArchetype(str, Enum):
    """Long-term player behavior archetypes detected across sessions."""
    EXPLORER = "explorer"
    ACHIEVER = "achiever"
    SOCIALITE = "socialite"
    COMPLETIONIST = "completionist"
    SPEEDRUNNER = "speedrunner"
    STORY_SEEKER = "story_seeker"
    BUILDER = "builder"
    COMBATANT = "combatant"
    TACTICIAN = "tactician"
    WANDERER = "wanderer"


class SessionType(str, Enum):
    """Categorical type of a single play session."""
    STORY = "story"
    COMBAT = "combat"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    CRAFTING = "crafting"
    BOSS_RUSH = "boss_rush"
    SIDE_QUEST = "side_quest"
    SANDBOX = "sandbox"
    COOP = "coop"
    COMPETITIVE = "competitive"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PlayerSession:
    """A single play session recorded against the meta-narrative."""
    session_id: str
    player_id: str
    session_type: str = SessionType.STORY.value
    started_at: float = field(default_factory=_now)
    ended_at: float = 0.0
    duration: float = 0.0
    arc_ids_touched: List[str] = field(default_factory=list)
    thread_ids_touched: List[str] = field(default_factory=list)
    milestones_reached: List[str] = field(default_factory=list)
    decisions_made: List[str] = field(default_factory=list)
    engagement_score: float = 0.0
    narrative_significance: float = 0.0
    world_impact: float = 0.0
    summary: str = ""
    analyzed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetaArc:
    """A story arc that unfolds across many play sessions."""
    arc_id: str
    title: str
    description: str = ""
    arc_type: str = MetaArcType.CHARACTER_GROWTH.value
    phase: str = MetaPhase.DORMANT.value
    status: str = MetaStatus.PENDING.value
    theme: str = ""
    central_question: str = ""
    involved_player_ids: List[str] = field(default_factory=list)
    thread_ids: List[str] = field(default_factory=list)
    milestone_ids: List[str] = field(default_factory=list)
    decision_ids: List[str] = field(default_factory=list)
    session_ids: List[str] = field(default_factory=list)
    current_chapter: int = 0
    total_chapters: int = 5
    tension_level: float = 0.2
    stakes_level: float = 0.2
    player_investment: float = 0.0
    resolution: str = ""
    started_at: float = 0.0
    concluded_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetaThread:
    """A narrative thread that can be woven across arcs and sessions."""
    thread_id: str
    title: str
    description: str = ""
    status: str = MetaStatus.PENDING.value
    thread_type: str = ""
    origin_arc_id: str = ""
    woven_arc_ids: List[str] = field(default_factory=list)
    involved_player_ids: List[str] = field(default_factory=list)
    key_moments: List[str] = field(default_factory=list)
    tension_contribution: float = 0.2
    priority: int = 1
    introduced_in_session: str = ""
    resolved_in_session: str = ""
    connections: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WorldMetaSnapshot:
    """A point-in-time capture of the world meta-state."""
    snapshot_id: str
    label: str = ""
    world_state: str = WorldMetaState.STABLE.value
    stability_index: float = 0.7
    faction_balance: float = 0.5
    threat_level: float = 0.3
    prosperity: float = 0.5
    ley_activity: float = 0.4
    void_pressure: float = 0.2
    active_crisis_ids: List[str] = field(default_factory=list)
    resolved_crisis_ids: List[str] = field(default_factory=list)
    notable_changes: List[str] = field(default_factory=list)
    player_driven_changes: List[str] = field(default_factory=list)
    session_count: int = 0
    captured_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProgressionMilestone:
    """A significant player achievement tracked across sessions."""
    milestone_id: str
    player_id: str
    title: str
    description: str = ""
    milestone_type: str = ""
    arc_id: str = ""
    significance: float = 0.5
    achieved_in_session: str = ""
    achieved_at: float = 0.0
    acknowledged: bool = False
    rewards: List[str] = field(default_factory=list)
    related_milestone_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerArchetypeProfile:
    """Long-term behavior profile for a single player."""
    player_id: str
    name: str = ""
    archetype: str = PlayerArchetype.WANDERER.value
    confidence: float = 0.0
    session_count: int = 0
    total_playtime: float = 0.0
    progression_pattern: str = ProgressionPattern.LINEAR.value
    dominant_session_type: str = SessionType.STORY.value
    engagement_trend: float = 0.0
    milestone_count: int = 0
    arc_participation: int = 0
    thread_involvement: int = 0
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    session_type_counts: Dict[str, int] = field(default_factory=dict)
    last_active: float = 0.0
    first_seen: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetaDecision:
    """A world-level decision derived from accumulated player data."""
    decision_id: str
    title: str
    description: str = ""
    rationale: str = ""
    decision_type: str = ""
    scope: str = "world"
    affected_arc_ids: List[str] = field(default_factory=list)
    affected_thread_ids: List[str] = field(default_factory=list)
    affected_player_ids: List[str] = field(default_factory=list)
    world_impact: float = 0.3
    status: str = MetaStatus.PENDING.value
    priority: int = 1
    confidence: float = 0.5
    expected_outcome: str = ""
    actual_outcome: str = ""
    applied_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetaConfig:
    """Tunable configuration for the meta game director."""
    max_players: int = _MAX_PLAYERS
    max_sessions: int = _MAX_SESSIONS
    max_meta_arcs: int = _MAX_META_ARCS
    max_meta_threads: int = _MAX_META_THREADS
    max_milestones: int = _MAX_MILESTONES
    max_decisions: int = _MAX_DECISIONS
    max_world_snapshots: int = _MAX_WORLD_SNAPSHOTS
    max_meta_events: int = _MAX_META_EVENTS
    max_cross_session_links: int = _MAX_CROSS_SESSION_LINKS
    max_events: int = _MAX_EVENTS
    auto_detect_archetypes: bool = True
    auto_advance_arcs: bool = True
    auto_capture_snapshots: bool = True
    snapshot_interval_ticks: int = _SNAPSHOT_INTERVAL_TICKS
    arc_tension_decay_rate: float = 0.02
    archetype_confidence_threshold: float = 0.35
    world_volatility: float = 0.5
    enable_meta_threads: bool = True
    enable_cross_session_links: bool = True
    meta_tick_interval: float = 60.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetaStats:
    """Aggregate statistics for the meta game director."""
    tick_count: int = 0
    total_players: int = 0
    total_sessions: int = 0
    total_meta_arcs: int = 0
    active_meta_arcs: int = 0
    completed_meta_arcs: int = 0
    total_meta_threads: int = 0
    total_milestones: int = 0
    total_decisions: int = 0
    applied_decisions: int = 0
    total_world_snapshots: int = 0
    total_meta_events: int = 0
    total_cross_session_links: int = 0
    archetype_distribution: Dict[str, int] = field(default_factory=dict)
    archetype_shifts: int = 0
    arc_completions: int = 0
    thread_weaves: int = 0
    avg_sessions_per_player: float = 0.0
    avg_arc_length: float = 0.0
    avg_engagement: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetaSnapshot:
    """A full snapshot of the director's state for inspection."""
    players: List[Dict[str, Any]] = field(default_factory=list)
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    meta_arcs: List[Dict[str, Any]] = field(default_factory=list)
    meta_threads: List[Dict[str, Any]] = field(default_factory=list)
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    world_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    meta_events: List[Dict[str, Any]] = field(default_factory=list)
    cross_session_links: List[Dict[str, Any]] = field(default_factory=list)
    world_state: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetaEvent:
    """An event emitted by the meta-narrative layer."""
    event_id: str
    kind: str = MetaEventKind.META_REVEAL.value
    title: str = ""
    description: str = ""
    related_arc_id: str = ""
    related_thread_id: str = ""
    related_player_id: str = ""
    related_session_id: str = ""
    related_milestone_id: str = ""
    related_decision_id: str = ""
    severity: str = "info"
    scope: str = "meta"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrossSessionLink:
    """A discovered connection between two play sessions."""
    link_id: str
    player_id: str
    link_type: str = "shared_arc"
    source_session_id: str = ""
    target_session_id: str = ""
    strength: float = 0.5
    description: str = ""
    related_arc_id: str = ""
    related_thread_id: str = ""
    discovered_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Meta Game Director
# ---------------------------------------------------------------------------

# Ordered phase progression used when advancing arcs.
_PHASE_ORDER: List[str] = [
    MetaPhase.DORMANT.value,
    MetaPhase.EMERGING.value,
    MetaPhase.DEVELOPING.value,
    MetaPhase.CULMINATING.value,
    MetaPhase.CLIMAX.value,
    MetaPhase.RESOLVING.value,
    MetaPhase.CONCLUDED.value,
]


class AIMetaGameDirector:
    """Thread-safe singleton directing cross-session meta-narrative."""

    _instance: Optional["AIMetaGameDirector"] = None
    _lock = threading.RLock()
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._seeded: bool = False

        # Core registries
        self._players: Dict[str, PlayerArchetypeProfile] = {}
        self._sessions: Dict[str, PlayerSession] = {}
        self._player_sessions: Dict[str, List[str]] = {}
        self._meta_arcs: Dict[str, MetaArc] = {}
        self._meta_threads: Dict[str, MetaThread] = {}
        self._milestones: Dict[str, ProgressionMilestone] = {}
        self._decisions: Dict[str, MetaDecision] = {}
        self._world_snapshots: Dict[str, WorldMetaSnapshot] = {}
        self._meta_events: Dict[str, MetaEvent] = {}
        self._cross_session_links: Dict[str, CrossSessionLink] = {}

        # Live world meta-state (mutated by decisions and ticks)
        self._world_state: Dict[str, Any] = {
            "world_state": WorldMetaState.STABLE.value,
            "stability_index": 0.7,
            "faction_balance": 0.5,
            "threat_level": 0.3,
            "prosperity": 0.5,
            "ley_activity": 0.4,
            "void_pressure": 0.2,
            "active_crisis_ids": [],
        }

        # Bookkeeping
        self._events: List[MetaEvent] = []
        self._stats = MetaStats()
        self._config = MetaConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._snap_counter: int = 0
        self._ticks_since_snapshot: int = 0

    @classmethod
    def get_instance(cls) -> "AIMetaGameDirector":
        if cls._instance is None:
            with cls._lock:
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
        self, kind: str, title: str = "", description: str = "",
        severity: str = "info", scope: str = "meta", **links: Any,
    ) -> MetaEvent:
        self._event_counter += 1
        event = MetaEvent(
            event_id=f"mevt_{self._event_counter:08d}",
            kind=kind, title=title, description=description,
            severity=severity, scope=scope, timestamp=_now(),
        )
        for key, value in links.items():
            if value and hasattr(event, key):
                setattr(event, key, value)
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)
        return event

    def _refresh_stats(self) -> None:
        s = self._stats
        s.tick_count = self._tick_count
        s.total_players = len(self._players)
        s.total_sessions = len(self._sessions)
        s.total_meta_arcs = len(self._meta_arcs)
        s.active_meta_arcs = sum(1 for a in self._meta_arcs.values()
                                 if a.status == MetaStatus.ACTIVE.value)
        s.completed_meta_arcs = sum(1 for a in self._meta_arcs.values()
                                    if a.phase == MetaPhase.CONCLUDED.value)
        s.total_meta_threads = len(self._meta_threads)
        s.total_milestones = len(self._milestones)
        s.total_decisions = len(self._decisions)
        s.applied_decisions = sum(1 for d in self._decisions.values()
                                  if d.status == MetaStatus.COMPLETED.value)
        s.total_world_snapshots = len(self._world_snapshots)
        s.total_meta_events = len(self._meta_events)
        s.total_cross_session_links = len(self._cross_session_links)

        # Archetype distribution across registered players
        dist: Dict[str, int] = {}
        for p in self._players.values():
            dist[p.archetype] = dist.get(p.archetype, 0) + 1
        s.archetype_distribution = dist

        s.avg_sessions_per_player = (
            sum(len(v) for v in self._player_sessions.values()) / len(self._players)
            if self._players else 0.0)

        concluded = [a for a in self._meta_arcs.values()
                     if a.phase == MetaPhase.CONCLUDED.value and a.concluded_at > 0]
        s.avg_arc_length = (sum(a.current_chapter for a in concluded) / len(concluded)
                            if concluded else 0.0)

        analyzed = [s2 for s2 in self._sessions.values() if s2.analyzed]
        s.avg_engagement = (sum(e.engagement_score for e in analyzed) / len(analyzed)
                            if analyzed else 0.0)

    def _next_phase(self, current: str) -> str:
        try:
            idx = _PHASE_ORDER.index(current)
        except ValueError:
            return MetaPhase.EMERGING.value
        if idx + 1 < len(_PHASE_ORDER):
            return _PHASE_ORDER[idx + 1]
        return current

    def _world_state_to_snapshot_dict(self) -> Dict[str, Any]:
        return {k: (list(v) if isinstance(v, list) else v)
                for k, v in self._world_state.items()}

    def _derive_world_state_label(self) -> str:
        threat = _safe_float(self._world_state.get("threat_level", 0.3))
        stability = _safe_float(self._world_state.get("stability_index", 0.7))
        void = _safe_float(self._world_state.get("void_pressure", 0.2))
        if void > 0.7 or threat > 0.8:
            return WorldMetaState.CRISIS.value
        if threat > 0.6:
            return WorldMetaState.TURBULENT.value
        if stability < 0.3:
            return WorldMetaState.DECAYING.value
        if stability > 0.8 and threat < 0.3:
            return WorldMetaState.FLOURISHING.value
        if void > 0.4:
            return WorldMetaState.TRANSFORMING.value
        if threat > 0.45:
            return WorldMetaState.VOLATILE.value
        return WorldMetaState.STABLE.value

    # ------------------------------------------------------------------
    # Player Management
    # ------------------------------------------------------------------

    def register_player(
        self, player_id: str, name: str = "",
        archetype: str = PlayerArchetype.WANDERER.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[PlayerArchetypeProfile]]:
        with _LOCK:
            if not player_id:
                return False, "player_id_required", None
            if len(self._players) >= self._config.max_players and \
                    player_id not in self._players:
                return False, "capacity_reached", None
            profile = self._players.get(player_id)
            if profile is None:
                profile = PlayerArchetypeProfile(
                    player_id=player_id, name=name or player_id,
                    archetype=archetype, first_seen=_now(),
                    metadata=metadata or {},
                )
                self._players[player_id] = profile
                self._player_sessions[player_id] = []
                self._emit(
                    MetaEventKind.SESSION_START, title="player_registered",
                    description=f"Player {player_id} entered the meta layer.",
                    related_player_id=player_id)
            else:
                if name:
                    profile.name = name
                if metadata:
                    profile.metadata.update(metadata)
                profile.updated_at = _now()
            self._refresh_stats()
            return True, "registered", profile

    def remove_player(self, player_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if player_id not in self._players:
                return False, "not_found"
            del self._players[player_id]
            self._player_sessions.pop(player_id, None)
            self._emit(
                MetaEventKind.SESSION_END, title="player_removed",
                description=f"Player {player_id} removed from the meta layer.",
                related_player_id=player_id)
            self._refresh_stats()
            return True, "removed"

    def get_player(self, player_id: str) -> Optional[PlayerArchetypeProfile]:
        with _LOCK:
            return self._players.get(player_id)

    def list_players(self, limit: int = 100) -> List[PlayerArchetypeProfile]:
        with _LOCK:
            return list(self._players.values())[:max(0, limit)]

    # ------------------------------------------------------------------
    # Session Tracking
    # ------------------------------------------------------------------

    def record_session(
        self, player_id: str, session_type: str = SessionType.STORY.value,
        duration: float = 0.0, arc_ids: Optional[List[str]] = None,
        thread_ids: Optional[List[str]] = None, milestones: Optional[List[str]] = None,
        decisions: Optional[List[str]] = None, summary: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[PlayerSession]]:
        with _LOCK:
            if player_id not in self._players:
                return False, "player_not_found", None
            if len(self._sessions) >= self._config.max_sessions:
                return False, "capacity_reached", None
            session_id = _new_id("sess")
            session = PlayerSession(
                session_id=session_id, player_id=player_id,
                session_type=session_type,
                started_at=_now() - max(0.0, duration),
                ended_at=_now(), duration=max(0.0, duration),
                arc_ids_touched=list(arc_ids or []),
                thread_ids_touched=list(thread_ids or []),
                milestones_reached=list(milestones or []),
                decisions_made=list(decisions or []),
                summary=summary, metadata=metadata or {},
            )
            self._sessions[session_id] = session
            self._player_sessions.setdefault(player_id, []).append(session_id)

            # Link session to touched arcs
            for arc_id in session.arc_ids_touched:
                arc = self._meta_arcs.get(arc_id)
                if arc and session_id not in arc.session_ids:
                    arc.session_ids.append(session_id)
                    arc.updated_at = _now()
                    if player_id not in arc.involved_player_ids:
                        arc.involved_player_ids.append(player_id)

            # Link session to touched threads
            for tid in session.thread_ids_touched:
                thread = self._meta_threads.get(tid)
                if thread:
                    if player_id not in thread.involved_player_ids:
                        thread.involved_player_ids.append(player_id)
                    thread.updated_at = _now()

            # Update player aggregate counters
            profile = self._players[player_id]
            profile.session_count += 1
            profile.total_playtime += max(0.0, duration)
            profile.last_active = _now()
            cnt = profile.session_type_counts.get(session_type, 0)
            profile.session_type_counts[session_type] = cnt + 1

            self._emit(
                MetaEventKind.SESSION_START, title="session_recorded",
                description=f"Session {session_id} recorded for {player_id}.",
                related_player_id=player_id, related_session_id=session_id)

            # Auto-analyze when the session lands
            if self._config.auto_detect_archetypes:
                self._analyze_session_internal(session_id)

            self._refresh_stats()
            return True, "recorded", session

    def analyze_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with _LOCK:
            return self._analyze_session_internal(session_id)

    def _analyze_session_internal(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        profile = self._players.get(session.player_id)

        # Engagement: a blend of duration, breadth of arcs/threads, and decisions
        duration_factor = _clamp(session.duration / 3600.0, 0.0, 1.0)
        breadth = _clamp((len(session.arc_ids_touched) + len(session.thread_ids_touched)) / 10.0, 0.0, 1.0)
        decision_factor = _clamp(len(session.decisions_made) / 5.0, 0.0, 1.0)
        engagement = _clamp(0.4 * duration_factor + 0.3 * breadth + 0.3 * decision_factor, 0.0, 1.0)

        # Narrative significance: based on arc phases touched and milestones
        arc_significance = 0.0
        high_phases = (MetaPhase.CULMINATING.value, MetaPhase.CLIMAX.value, MetaPhase.RESOLVING.value)
        for arc_id in session.arc_ids_touched:
            arc = self._meta_arcs.get(arc_id)
            if arc:
                if arc.phase in high_phases:
                    arc_significance += 0.25
                elif arc.phase == MetaPhase.DEVELOPING.value:
                    arc_significance += 0.1
        milestone_factor = _clamp(len(session.milestones_reached) / 3.0, 0.0, 1.0)
        significance = _clamp(arc_significance + 0.5 * milestone_factor, 0.0, 1.0)
        world_impact = _clamp(0.2 * len(session.decisions_made), 0.0, 1.0)

        session.engagement_score = round(engagement, 4)
        session.narrative_significance = round(significance, 4)
        session.world_impact = round(world_impact, 4)
        session.analyzed = True

        if profile is not None:
            # Update engagement trend as a moving blend and recompute aggregates
            profile.engagement_trend = round(0.6 * profile.engagement_trend + 0.4 * engagement, 4)
            profile.milestone_count += len(session.milestones_reached)
            touched_arcs: set = set()
            touched_threads: set = set()
            for sid in self._player_sessions.get(profile.player_id, []):
                s = self._sessions.get(sid)
                if s:
                    touched_arcs.update(s.arc_ids_touched)
                    touched_threads.update(s.thread_ids_touched)
            profile.arc_participation = len(touched_arcs)
            profile.thread_involvement = len(touched_threads)
            if profile.session_type_counts:
                profile.dominant_session_type = max(
                    profile.session_type_counts.items(), key=lambda kv: kv[1])[0]
            profile.progression_pattern = self._infer_progression_pattern(profile)

            if self._config.auto_detect_archetypes:
                self._detect_archetype_internal(profile.player_id)

        # Acknowledge milestones reached this session
        for mid in session.milestones_reached:
            milestone = self._milestones.get(mid)
            if milestone and not milestone.acknowledged:
                milestone.acknowledged = True
                milestone.achieved_in_session = session_id
                milestone.achieved_at = _now()
                self._emit(
                    MetaEventKind.MILESTONE_REACHED,
                    title="milestone_reached",
                    description=f"Milestone {mid} acknowledged for "
                                f"{session.player_id}.",
                    related_player_id=session.player_id,
                    related_session_id=session_id,
                    related_milestone_id=mid)

        # Discover cross-session links for this player
        if self._config.enable_cross_session_links:
            self._discover_cross_session_links(session.player_id)

        self._emit(
            MetaEventKind.SESSION_END, title="session_analyzed",
            description=f"Session {session_id} analyzed: engagement="
                        f"{engagement:.2f}, significance={significance:.2f}.",
            related_session_id=session_id,
            related_player_id=session.player_id)

        return {
            "session_id": session_id,
            "player_id": session.player_id,
            "engagement_score": session.engagement_score,
            "narrative_significance": session.narrative_significance,
            "world_impact": session.world_impact,
            "analyzed": True,
        }

    def _infer_progression_pattern(self, profile: PlayerArchetypeProfile) -> str:
        session_ids = self._player_sessions.get(profile.player_id, [])
        if len(session_ids) < 2:
            return ProgressionPattern.LINEAR.value
        durations: List[float] = []
        types: List[str] = []
        for sid in session_ids:
            s = self._sessions.get(sid)
            if s:
                durations.append(s.duration)
                types.append(s.session_type)
        if not durations:
            return ProgressionPattern.LINEAR.value

        avg_dur = sum(durations) / len(durations)
        unique_types = len(set(types))
        eng = profile.engagement_trend

        # Bursty: high variance in duration relative to the mean
        if len(durations) > 2 and avg_dur > 0:
            variance = sum((d - avg_dur) ** 2 for d in durations) / len(durations)
            if (variance ** 0.5) / avg_dur > 0.8:
                return ProgressionPattern.BURSTY.value
        if avg_dur < 900 and len(durations) >= 3:
            return ProgressionPattern.SPEEDRUN.value
        if avg_dur > 7200:
            return ProgressionPattern.DEEP_DIVE.value
        if profile.milestone_count >= len(session_ids):
            return ProgressionPattern.COMPLETIONIST.value
        if unique_types >= 4:
            return ProgressionPattern.EXPLORATORY.value
        if unique_types <= 2 and eng > 0.6:
            return ProgressionPattern.MASTERY.value
        if profile.dominant_session_type in (SessionType.SOCIAL.value, SessionType.COOP.value):
            return ProgressionPattern.SOCIAL.value
        if unique_types >= 3 and eng < 0.4:
            return ProgressionPattern.ERRATIC.value
        if eng > 0.5:
            return ProgressionPattern.STEADY.value

        return ProgressionPattern.LINEAR.value

    def get_session_history(
        self, player_id: str, limit: int = 50,
    ) -> List[PlayerSession]:
        with _LOCK:
            ids = self._player_sessions.get(player_id, [])
            sessions = [self._sessions[sid] for sid in ids
                        if sid in self._sessions]
            sessions.sort(key=lambda s: s.started_at, reverse=True)
            return sessions[:max(0, limit)]

    # ------------------------------------------------------------------
    # Meta-Arc Management
    # ------------------------------------------------------------------

    def register_meta_arc(
        self, arc_id: str, title: str, description: str = "",
        arc_type: str = MetaArcType.CHARACTER_GROWTH.value,
        theme: str = "", central_question: str = "",
        total_chapters: int = 5, involved_player_ids: Optional[List[str]] = None,
        thread_ids: Optional[List[str]] = None, tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[MetaArc]]:
        with _LOCK:
            if not arc_id or not title:
                return False, "arc_id_and_title_required", None
            if arc_id in self._meta_arcs:
                return False, "already_exists", None
            if len(self._meta_arcs) >= self._config.max_meta_arcs:
                return False, "capacity_reached", None
            meta = metadata or {}
            if tags:
                meta["tags"] = list(tags)
            arc = MetaArc(
                arc_id=arc_id, title=title, description=description,
                arc_type=arc_type, theme=theme, central_question=central_question,
                total_chapters=max(1, int(total_chapters)),
                involved_player_ids=list(involved_player_ids or []),
                thread_ids=list(thread_ids or []),
                metadata=meta,
            )
            self._meta_arcs[arc_id] = arc
            self._emit(
                MetaEventKind.ARC_ADVANCE, title="arc_registered",
                description=f"Meta-arc '{title}' registered.",
                related_arc_id=arc_id)
            self._refresh_stats()
            return True, "registered", arc

    def start_meta_arc(self, arc_id: str) -> Tuple[bool, str, Optional[MetaArc]]:
        with _LOCK:
            arc = self._meta_arcs.get(arc_id)
            if arc is None:
                return False, "not_found", None
            if arc.status == MetaStatus.ACTIVE.value:
                return False, "already_active", arc
            arc.status = MetaStatus.ACTIVE.value
            arc.phase = MetaPhase.EMERGING.value
            arc.current_chapter = max(1, arc.current_chapter)
            arc.started_at = _now()
            arc.updated_at = _now()
            self._emit(
                MetaEventKind.ARC_ADVANCE, title="arc_started",
                description=f"Meta-arc '{arc.title}' is now active.",
                related_arc_id=arc_id)
            self._refresh_stats()
            return True, "started", arc

    def advance_meta_arc(
        self, arc_id: str, phase: str = "",
    ) -> Tuple[bool, str, Optional[MetaArc]]:
        with _LOCK:
            arc = self._meta_arcs.get(arc_id)
            if arc is None:
                return False, "not_found", None
            if arc.status != MetaStatus.ACTIVE.value:
                return False, "not_active", arc
            if arc.phase == MetaPhase.CONCLUDED.value:
                return False, "already_concluded", arc

            next_phase = phase if phase else self._next_phase(arc.phase)
            arc.phase = next_phase
            arc.current_chapter = min(arc.total_chapters, arc.current_chapter + 1)

            # Tension escalates toward the climax, then falls during resolution
            if next_phase in (MetaPhase.CULMINATING.value, MetaPhase.CLIMAX.value):
                arc.tension_level = _clamp(arc.tension_level + 0.2, 0.0, 1.0)
                arc.stakes_level = _clamp(arc.stakes_level + 0.15, 0.0, 1.0)
            elif next_phase == MetaPhase.RESOLVING.value:
                arc.tension_level = _clamp(arc.tension_level - 0.25, 0.0, 1.0)

            # Grow player investment from participating players
            if arc.involved_player_ids:
                avg_eng = 0.0
                count = 0
                for pid in arc.involved_player_ids:
                    prof = self._players.get(pid)
                    if prof:
                        avg_eng += prof.engagement_trend
                        count += 1
                if count > 0:
                    arc.player_investment = _clamp(
                        0.5 * arc.player_investment +
                        0.5 * (avg_eng / count), 0.0, 1.0)

            arc.updated_at = _now()
            self._emit(
                MetaEventKind.ARC_ADVANCE, title="arc_advanced",
                description=f"Meta-arc '{arc.title}' advanced to {next_phase}.",
                related_arc_id=arc_id)
            self._refresh_stats()
            return True, "advanced", arc

    def complete_meta_arc(
        self, arc_id: str, resolution: str = "",
    ) -> Tuple[bool, str, Optional[MetaArc]]:
        with _LOCK:
            arc = self._meta_arcs.get(arc_id)
            if arc is None:
                return False, "not_found", None
            arc.phase = MetaPhase.CONCLUDED.value
            arc.status = MetaStatus.COMPLETED.value
            arc.resolution = resolution or arc.resolution or "Resolved."
            arc.concluded_at = _now()
            arc.tension_level = 0.0
            arc.updated_at = _now()
            self._stats.arc_completions += 1
            self._emit(
                MetaEventKind.ARC_COMPLETE, title="arc_completed",
                description=f"Meta-arc '{arc.title}' concluded.",
                related_arc_id=arc_id)
            self._refresh_stats()
            return True, "completed", arc

    def get_meta_arc(self, arc_id: str) -> Optional[MetaArc]:
        with _LOCK:
            return self._meta_arcs.get(arc_id)

    def list_meta_arcs(self, limit: int = 100) -> List[MetaArc]:
        with _LOCK:
            return list(self._meta_arcs.values())[:max(0, limit)]

    # ------------------------------------------------------------------
    # Meta-Thread Weaving
    # ------------------------------------------------------------------

    def register_meta_thread(
        self, thread_id: str, title: str, description: str = "",
        origin_arc_id: str = "", thread_type: str = "",
        involved_player_ids: Optional[List[str]] = None,
        priority: int = 1, tension_contribution: float = 0.2,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[MetaThread]]:
        with _LOCK:
            if not thread_id or not title:
                return False, "thread_id_and_title_required", None
            if thread_id in self._meta_threads:
                return False, "already_exists", None
            if len(self._meta_threads) >= self._config.max_meta_threads:
                return False, "capacity_reached", None
            thread = MetaThread(
                thread_id=thread_id, title=title, description=description,
                origin_arc_id=origin_arc_id, thread_type=thread_type,
                involved_player_ids=list(involved_player_ids or []),
                priority=max(1, int(priority)),
                tension_contribution=_clamp(tension_contribution, 0.0, 1.0),
                metadata=metadata or {},
            )
            self._meta_threads[thread_id] = thread

            # Attach thread to its origin arc
            if origin_arc_id and origin_arc_id in self._meta_arcs:
                arc = self._meta_arcs[origin_arc_id]
                if thread_id not in arc.thread_ids:
                    arc.thread_ids.append(thread_id)
                    arc.updated_at = _now()

            self._emit(
                MetaEventKind.THREAD_WEAVE, title="thread_registered",
                description=f"Meta-thread '{title}' registered.",
                related_thread_id=thread_id, related_arc_id=origin_arc_id)
            self._refresh_stats()
            return True, "registered", thread

    def weave_thread(
        self, thread_id: str, target_arc_id: str,
        description: str = "",
    ) -> Tuple[bool, str, Optional[MetaThread]]:
        with _LOCK:
            thread = self._meta_threads.get(thread_id)
            if thread is None:
                return False, "thread_not_found", None
            target = self._meta_arcs.get(target_arc_id)
            if target is None:
                return False, "target_arc_not_found", None
            if not self._config.enable_meta_threads:
                return False, "meta_threads_disabled", thread

            if target_arc_id not in thread.woven_arc_ids:
                thread.woven_arc_ids.append(target_arc_id)
            if thread_id not in target.thread_ids:
                target.thread_ids.append(thread_id)
                target.updated_at = _now()
            if description:
                thread.key_moments.append(
                    f"Woven into {target_arc_id}: {description}")
            thread.status = MetaStatus.ACTIVE.value
            thread.updated_at = _now()

            # Weaving boosts the target arc's tension
            target.tension_level = _clamp(
                target.tension_level + thread.tension_contribution * 0.3,
                0.0, 1.0)

            self._stats.thread_weaves += 1
            self._emit(
                MetaEventKind.THREAD_WEAVE, title="thread_woven",
                description=f"Thread '{thread.title}' woven into "
                            f"'{target.title}'.",
                related_thread_id=thread_id, related_arc_id=target_arc_id)
            self._refresh_stats()
            return True, "woven", thread

    def get_meta_thread(self, thread_id: str) -> Optional[MetaThread]:
        with _LOCK:
            return self._meta_threads.get(thread_id)

    def list_meta_threads(self, limit: int = 100) -> List[MetaThread]:
        with _LOCK:
            return list(self._meta_threads.values())[:max(0, limit)]

    # ------------------------------------------------------------------
    # Player Archetype Detection
    # ------------------------------------------------------------------

    def detect_player_archetype(
        self, player_id: str,
    ) -> Tuple[bool, str, Optional[PlayerArchetypeProfile]]:
        with _LOCK:
            if player_id not in self._players:
                return False, "player_not_found", None
            profile = self._detect_archetype_internal(player_id)
            if profile is None:
                return False, "no_sessions", None
            return True, "detected", profile

    def _detect_archetype_internal(
        self, player_id: str,
    ) -> Optional[PlayerArchetypeProfile]:
        profile = self._players.get(player_id)
        if profile is None:
            return None
        session_ids = self._player_sessions.get(player_id, [])
        if not session_ids:
            return profile

        # Tally session types and gather metrics
        type_counts: Dict[str, int] = dict(profile.session_type_counts)
        total = sum(type_counts.values()) or 1
        milestone_density = profile.milestone_count / max(1, profile.session_count)
        avg_dur = (profile.total_playtime / profile.session_count
                   if profile.session_count else 0.0)
        arc_ratio = profile.arc_participation / max(1, profile.session_count)
        thread_ratio = profile.thread_involvement / max(1, profile.session_count)

        story_share = type_counts.get(SessionType.STORY.value, 0) / total
        combat_share = (type_counts.get(SessionType.COMBAT.value, 0) +
                        type_counts.get(SessionType.BOSS_RUSH.value, 0)) / total
        expl_share = (type_counts.get(SessionType.EXPLORATION.value, 0) +
                      type_counts.get(SessionType.SIDE_QUEST.value, 0)) / total
        social_share = (type_counts.get(SessionType.SOCIAL.value, 0) +
                        type_counts.get(SessionType.COOP.value, 0)) / total
        build_share = (type_counts.get(SessionType.CRAFTING.value, 0) +
                       type_counts.get(SessionType.SANDBOX.value, 0)) / total
        speed_share = 1.0 if (avg_dur < 900 and profile.session_count >= 3) else 0.2
        eng = profile.engagement_trend

        scores: Dict[str, float] = {
            PlayerArchetype.EXPLORER.value: _clamp(expl_share + 0.3 * thread_ratio, 0.0, 1.0),
            PlayerArchetype.ACHIEVER.value: _clamp(0.5 * milestone_density + 0.3 * eng, 0.0, 1.0),
            PlayerArchetype.SOCIALITE.value: _clamp(social_share + 0.2 * eng, 0.0, 1.0),
            PlayerArchetype.COMPLETIONIST.value: _clamp(0.4 * milestone_density + 0.4 * arc_ratio, 0.0, 1.0),
            PlayerArchetype.SPEEDRUNNER.value: _clamp(0.6 * speed_share + 0.2 * combat_share, 0.0, 1.0),
            PlayerArchetype.STORY_SEEKER.value: _clamp(story_share + 0.2 * thread_ratio, 0.0, 1.0),
            PlayerArchetype.BUILDER.value: _clamp(build_share + 0.2 * eng, 0.0, 1.0),
            PlayerArchetype.COMBATANT.value: _clamp(combat_share + 0.2 * eng, 0.0, 1.0),
            PlayerArchetype.TACTICIAN.value: _clamp(0.4 * combat_share + 0.4 * eng, 0.0, 1.0),
            PlayerArchetype.WANDERER.value: _clamp(0.3 * (1.0 - eng) + 0.3 * (len(type_counts) / 6.0), 0.0, 1.0),
        }

        best_archetype = max(scores.items(), key=lambda kv: kv[1])[0]
        best_score = scores[best_archetype]
        total_score = sum(scores.values()) or 1.0
        confidence = round(best_score / total_score, 4)

        profile.archetype_scores = {k: round(v, 4) for k, v in scores.items()}

        previous = profile.archetype
        if confidence >= self._config.archetype_confidence_threshold:
            profile.archetype = best_archetype
        profile.confidence = confidence
        profile.updated_at = _now()

        if previous != profile.archetype and previous:
            self._stats.archetype_shifts += 1
            self._emit(
                MetaEventKind.ARCHETYPE_SHIFT, title="archetype_shift",
                description=f"Player {player_id} shifted from {previous} "
                            f"to {profile.archetype}.",
                related_player_id=player_id, severity="notable")

        return profile

    def get_player_archetype(self, player_id: str) -> Optional[str]:
        with _LOCK:
            profile = self._players.get(player_id)
            if profile is None:
                return None
            return profile.archetype

    def list_archetypes(self, limit: int = 100) -> List[Dict[str, Any]]:
        with _LOCK:
            summary: Dict[str, Dict[str, Any]] = {}
            for p in self._players.values():
                entry = summary.setdefault(p.archetype, {
                    "archetype": p.archetype,
                    "player_count": 0,
                    "avg_confidence": 0.0,
                    "players": [],
                })
                entry["player_count"] += 1
                entry["avg_confidence"] += p.confidence
                if len(entry["players"]) < limit:
                    entry["players"].append(p.player_id)
            for entry in summary.values():
                if entry["player_count"]:
                    entry["avg_confidence"] = round(
                        entry["avg_confidence"] / entry["player_count"], 4)
            return list(summary.values())[:max(0, limit)]

    # ------------------------------------------------------------------
    # Meta-Decision Engine
    # ------------------------------------------------------------------

    def create_meta_decision(
        self, decision_id: str, title: str, description: str = "",
        rationale: str = "", decision_type: str = "",
        scope: str = "world",
        affected_arc_ids: Optional[List[str]] = None,
        affected_thread_ids: Optional[List[str]] = None,
        affected_player_ids: Optional[List[str]] = None,
        world_impact: float = 0.3, priority: int = 1,
        confidence: float = 0.5, expected_outcome: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[MetaDecision]]:
        with _LOCK:
            if not decision_id or not title:
                return False, "decision_id_and_title_required", None
            if decision_id in self._decisions:
                return False, "already_exists", None
            if len(self._decisions) >= self._config.max_decisions:
                return False, "capacity_reached", None
            decision = MetaDecision(
                decision_id=decision_id, title=title, description=description,
                rationale=rationale, decision_type=decision_type, scope=scope,
                affected_arc_ids=list(affected_arc_ids or []),
                affected_thread_ids=list(affected_thread_ids or []),
                affected_player_ids=list(affected_player_ids or []),
                world_impact=_clamp(world_impact, 0.0, 1.0),
                priority=max(1, int(priority)),
                confidence=_clamp(confidence, 0.0, 1.0),
                expected_outcome=expected_outcome,
                metadata=metadata or {},
            )
            self._decisions[decision_id] = decision
            self._emit(
                MetaEventKind.DECISION_APPLIED, title="decision_created",
                description=f"Meta-decision '{title}' created.",
                related_decision_id=decision_id)
            self._refresh_stats()
            return True, "created", decision

    def apply_meta_decision(
        self, decision_id: str,
    ) -> Tuple[bool, str, Optional[MetaDecision]]:
        with _LOCK:
            decision = self._decisions.get(decision_id)
            if decision is None:
                return False, "not_found", None
            if decision.status == MetaStatus.COMPLETED.value:
                return False, "already_applied", decision

            impact = decision.world_impact * decision.confidence

            # Shift the live world state based on the decision
            volatility = self._config.world_volatility
            self._world_state["threat_level"] = _clamp(
                _safe_float(self._world_state.get("threat_level")) +
                impact * volatility * 0.5, 0.0, 1.0)
            self._world_state["stability_index"] = _clamp(
                _safe_float(self._world_state.get("stability_index")) -
                impact * volatility * 0.4, 0.0, 1.0)
            self._world_state["void_pressure"] = _clamp(
                _safe_float(self._world_state.get("void_pressure")) +
                impact * volatility * 0.3, 0.0, 1.0)
            self._world_state["ley_activity"] = _clamp(
                _safe_float(self._world_state.get("ley_activity")) +
                impact * volatility * 0.2, 0.0, 1.0)
            self._world_state["world_state"] = self._derive_world_state_label()

            # Advance affected arcs by one beat
            for arc_id in decision.affected_arc_ids:
                arc = self._meta_arcs.get(arc_id)
                if arc and arc.status == MetaStatus.ACTIVE.value:
                    self.advance_meta_arc(arc.arc_id)
                    if decision_id not in arc.decision_ids:
                        arc.decision_ids.append(decision_id)

            # Activate affected threads
            for tid in decision.affected_thread_ids:
                thread = self._meta_threads.get(tid)
                if thread and thread.status != MetaStatus.ACTIVE.value:
                    thread.status = MetaStatus.ACTIVE.value
                    thread.updated_at = _now()

            decision.status = MetaStatus.COMPLETED.value
            decision.applied_at = _now()
            decision.actual_outcome = (
                f"World shifted to {self._world_state['world_state']} "
                f"(impact={impact:.2f}).")
            decision.updated_at = _now()

            self._emit(
                MetaEventKind.DECISION_APPLIED, title="decision_applied",
                description=f"Decision '{decision.title}' applied; "
                            f"{decision.actual_outcome}",
                related_decision_id=decision_id,
                severity="notable")
            self._refresh_stats()
            return True, "applied", decision

    def list_meta_decisions(self, limit: int = 100) -> List[MetaDecision]:
        with _LOCK:
            return list(self._decisions.values())[:max(0, limit)]

    # ------------------------------------------------------------------
    # Progression Milestones
    # ------------------------------------------------------------------

    def register_milestone(
        self, milestone_id: str, player_id: str, title: str,
        description: str = "", milestone_type: str = "",
        arc_id: str = "", significance: float = 0.5,
        rewards: Optional[List[str]] = None,
        related_milestone_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ProgressionMilestone]]:
        with _LOCK:
            if not milestone_id or not player_id or not title:
                return False, "required_fields_missing", None
            if milestone_id in self._milestones:
                return False, "already_exists", None
            if len(self._milestones) >= self._config.max_milestones:
                return False, "capacity_reached", None
            milestone = ProgressionMilestone(
                milestone_id=milestone_id, player_id=player_id, title=title,
                description=description, milestone_type=milestone_type,
                arc_id=arc_id, significance=_clamp(significance, 0.0, 1.0),
                rewards=list(rewards or []),
                related_milestone_ids=list(related_milestone_ids or []),
                metadata=metadata or {},
            )
            self._milestones[milestone_id] = milestone

            # Attach milestone to its arc and player profile
            if arc_id and arc_id in self._meta_arcs:
                arc = self._meta_arcs[arc_id]
                if milestone_id not in arc.milestone_ids:
                    arc.milestone_ids.append(milestone_id)
                    arc.updated_at = _now()
            profile = self._players.get(player_id)
            if profile:
                profile.milestone_count += 1

            self._emit(
                MetaEventKind.MILESTONE_REACHED, title="milestone_registered",
                description=f"Milestone '{title}' registered for {player_id}.",
                related_player_id=player_id, related_milestone_id=milestone_id)
            self._refresh_stats()
            return True, "registered", milestone

    def check_milestone(self, milestone_id: str) -> Optional[ProgressionMilestone]:
        with _LOCK:
            milestone = self._milestones.get(milestone_id)
            if milestone is None:
                return None
            # Acknowledge the milestone if it has been achieved in a session
            if not milestone.acknowledged and milestone.achieved_in_session:
                milestone.acknowledged = True
                milestone.achieved_at = milestone.achieved_at or _now()
                self._emit(
                    MetaEventKind.MILESTONE_REACHED,
                    title="milestone_acknowledged",
                    description=f"Milestone '{milestone.title}' acknowledged.",
                    related_milestone_id=milestone_id,
                    related_player_id=milestone.player_id)
            return milestone

    def list_milestones(
        self, player_id: str = "", limit: int = 100,
    ) -> List[ProgressionMilestone]:
        with _LOCK:
            items = list(self._milestones.values())
            if player_id:
                items = [m for m in items if m.player_id == player_id]
            return items[:max(0, limit)]

    # ------------------------------------------------------------------
    # World Meta-State Snapshots
    # ------------------------------------------------------------------

    def capture_world_snapshot(
        self, label: str = "", notable_changes: Optional[List[str]] = None,
        player_driven_changes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[WorldMetaSnapshot]]:
        with _LOCK:
            if len(self._world_snapshots) >= self._config.max_world_snapshots:
                return False, "capacity_reached", None
            self._snap_counter += 1
            snap_id = f"snap_{self._snap_counter:06d}"
            state_copy = self._world_state_to_snapshot_dict()
            snapshot = WorldMetaSnapshot(
                snapshot_id=snap_id,
                label=label or f"snapshot_{self._snap_counter}",
                world_state=state_copy.get("world_state",
                                           WorldMetaState.STABLE.value),
                stability_index=_safe_float(state_copy.get("stability_index"), 0.7),
                faction_balance=_safe_float(state_copy.get("faction_balance"), 0.5),
                threat_level=_safe_float(state_copy.get("threat_level"), 0.3),
                prosperity=_safe_float(state_copy.get("prosperity"), 0.5),
                ley_activity=_safe_float(state_copy.get("ley_activity"), 0.4),
                void_pressure=_safe_float(state_copy.get("void_pressure"), 0.2),
                active_crisis_ids=list(state_copy.get("active_crisis_ids", [])),
                notable_changes=list(notable_changes or []),
                player_driven_changes=list(player_driven_changes or []),
                session_count=len(self._sessions),
                captured_at=_now(),
                metadata=metadata or {},
            )
            self._world_snapshots[snap_id] = snapshot
            self._emit(
                MetaEventKind.SNAPSHOT_CAPTURED, title="snapshot_captured",
                description=f"World snapshot '{snapshot.label}' captured "
                            f"(state={snapshot.world_state}).",
                severity="info")
            self._refresh_stats()
            return True, "captured", snapshot

    def get_world_snapshot(self, snapshot_id: str) -> Optional[WorldMetaSnapshot]:
        with _LOCK:
            return self._world_snapshots.get(snapshot_id)

    def list_world_snapshots(self, limit: int = 100) -> List[WorldMetaSnapshot]:
        with _LOCK:
            return list(self._world_snapshots.values())[:max(0, limit)]

    # ------------------------------------------------------------------
    # Cross-Session Links
    # ------------------------------------------------------------------

    def find_cross_session_links(
        self, player_id: str,
    ) -> List[CrossSessionLink]:
        with _LOCK:
            return self._discover_cross_session_links(player_id)

    def _discover_cross_session_links(
        self, player_id: str,
    ) -> List[CrossSessionLink]:
        session_ids = self._player_sessions.get(player_id, [])
        if len(session_ids) < 2:
            return []
        discovered: List[CrossSessionLink] = []

        def _add(ltype: str, src: PlayerSession, tgt: PlayerSession,
                 strength: float, desc: str, arc_id: str = "",
                 tid: str = "") -> None:
            lid = _new_id("csl")
            link = CrossSessionLink(
                link_id=lid, player_id=player_id, link_type=ltype,
                source_session_id=src.session_id,
                target_session_id=tgt.session_id, strength=strength,
                description=desc, related_arc_id=arc_id,
                related_thread_id=tid)
            self._cross_session_links[lid] = link
            discovered.append(link)

        sessions = [self._sessions[sid] for sid in session_ids
                    if sid in self._sessions]
        # Compare each pair for shared arcs, threads, or milestone callbacks
        for i in range(len(sessions)):
            for j in range(i + 1, len(sessions)):
                src, tgt = sessions[i], sessions[j]
                for arc_id in set(src.arc_ids_touched) & set(tgt.arc_ids_touched):
                    _add("shared_arc", src, tgt, 0.7,
                         f"Both sessions advanced arc {arc_id}.", arc_id=arc_id)
                for tid in set(src.thread_ids_touched) & set(tgt.thread_ids_touched):
                    _add("shared_thread", src, tgt, 0.6,
                         f"Both sessions touched thread {tid}.", tid=tid)
                if src.milestones_reached and \
                        set(src.milestones_reached) & set(tgt.decisions_made):
                    _add("milestone_callback", src, tgt, 0.8,
                         "A later session built on an earlier milestone.")

        # Evict oldest links if the store exceeds its capacity
        cap = max(1, int(self._config.max_cross_session_links))
        while len(self._cross_session_links) > cap:
            self._cross_session_links.pop(next(iter(self._cross_session_links)), None)
        if discovered:
            self._emit(
                MetaEventKind.CROSS_SESSION_CALLBACK,
                title="cross_session_links_found",
                description=f"Found {len(discovered)} cross-session links "
                            f"for {player_id}.",
                related_player_id=player_id)
            self._refresh_stats()
        return discovered

    def get_cross_session_links(
        self, player_id: str = "", limit: int = 100,
    ) -> List[CrossSessionLink]:
        with _LOCK:
            items = list(self._cross_session_links.values())
            if player_id:
                items = [l for l in items if l.player_id == player_id]
            return items[:max(0, limit)]

    # ------------------------------------------------------------------
    # Meta-Event Generation
    # ------------------------------------------------------------------

    def generate_meta_event(
        self, kind: str = MetaEventKind.META_REVEAL.value,
        title: str = "", description: str = "",
        related_arc_id: str = "", related_thread_id: str = "",
        related_player_id: str = "", related_session_id: str = "",
        related_milestone_id: str = "", related_decision_id: str = "",
        severity: str = "info", scope: str = "meta",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[MetaEvent]]:
        with _LOCK:
            if len(self._meta_events) >= self._config.max_meta_events:
                return False, "capacity_reached", None
            event_id = _new_id("mevt")
            event = MetaEvent(
                event_id=event_id, kind=kind, title=title,
                description=description, related_arc_id=related_arc_id,
                related_thread_id=related_thread_id,
                related_player_id=related_player_id,
                related_session_id=related_session_id,
                related_milestone_id=related_milestone_id,
                related_decision_id=related_decision_id,
                severity=severity, scope=scope,
                metadata=metadata or {},
            )
            self._meta_events[event_id] = event
            # If this event ties back to a past session, record a cross-session
            # callback link so the connection is durable.
            if related_session_id and related_player_id and \
                    self._config.enable_cross_session_links:
                cb_id = _new_id("csl")
                cb = CrossSessionLink(
                    link_id=cb_id, player_id=related_player_id,
                    link_type="meta_event_callback",
                    source_session_id=related_session_id,
                    strength=0.9,
                    description=f"Meta event '{title or kind}' calls back "
                                f"to session {related_session_id}.",
                )
                self._cross_session_links[cb_id] = cb

            self._emit(
                MetaEventKind.META_REVEAL, title="meta_event_generated",
                description=f"Meta event '{title or kind}' generated.",
                severity=severity)
            self._refresh_stats()
            return True, "generated", event

    def list_meta_events(self, limit: int = 100) -> List[MetaEvent]:
        with _LOCK:
            return list(self._meta_events.values())[:max(0, limit)]

    # ------------------------------------------------------------------
    # System State and Control
    # ------------------------------------------------------------------

    def get_stats(self) -> MetaStats:
        with _LOCK:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> MetaSnapshot:
        with _LOCK:
            self._refresh_stats()
            return MetaSnapshot(
                players=[p.to_dict() for p in list(self._players.values())[:20]],
                sessions=[s.to_dict() for s in list(self._sessions.values())[:30]],
                meta_arcs=[a.to_dict() for a in list(self._meta_arcs.values())[:20]],
                meta_threads=[t.to_dict() for t in list(self._meta_threads.values())[:30]],
                milestones=[m.to_dict() for m in list(self._milestones.values())[:30]],
                decisions=[d.to_dict() for d in list(self._decisions.values())[:20]],
                world_snapshots=[w.to_dict() for w in list(self._world_snapshots.values())[:10]],
                meta_events=[e.to_dict() for e in list(self._meta_events.values())[:30]],
                cross_session_links=[l.to_dict() for l in list(self._cross_session_links.values())[:30]],
                world_state=dict(self._world_state),
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            self._refresh_stats()
            arcs = list(self._meta_arcs.values())
            threads = list(self._meta_threads.values())
            milestones = list(self._milestones.values())
            decisions = list(self._decisions.values())
            return {
                "initialized": self._initialized,
                "seeded": self._seeded,
                "total_players": len(self._players),
                "total_sessions": len(self._sessions),
                "total_meta_arcs": len(arcs),
                "active_meta_arcs": sum(1 for a in arcs if a.status == MetaStatus.ACTIVE.value),
                "concluded_meta_arcs": sum(1 for a in arcs if a.phase == MetaPhase.CONCLUDED.value),
                "total_meta_threads": len(threads),
                "woven_threads": sum(1 for t in threads if t.woven_arc_ids),
                "total_milestones": len(milestones),
                "acknowledged_milestones": sum(1 for m in milestones if m.acknowledged),
                "total_decisions": len(decisions),
                "applied_decisions": sum(1 for d in decisions if d.status == MetaStatus.COMPLETED.value),
                "total_world_snapshots": len(self._world_snapshots),
                "total_meta_events": len(self._meta_events),
                "total_cross_session_links": len(self._cross_session_links),
                "world_state": self._world_state.get("world_state"),
                "tick_count": self._tick_count,
            }

    def get_config(self) -> MetaConfig:
        with _LOCK:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, MetaConfig]:
        with _LOCK:
            if not kwargs:
                return False, "no_kwargs", self._config
            cfg = self._config
            # Integer capacity fields
            int_fields = {
                "max_players": _MAX_PLAYERS, "max_sessions": _MAX_SESSIONS,
                "max_meta_arcs": _MAX_META_ARCS, "max_meta_threads": _MAX_META_THREADS,
                "max_milestones": _MAX_MILESTONES, "max_decisions": _MAX_DECISIONS,
                "max_world_snapshots": _MAX_WORLD_SNAPSHOTS,
                "max_meta_events": _MAX_META_EVENTS,
                "max_cross_session_links": _MAX_CROSS_SESSION_LINKS,
                "max_events": _MAX_EVENTS,
            }
            for fname, default in int_fields.items():
                if fname in kwargs:
                    setattr(cfg, fname, _safe_int(kwargs[fname], default))
            # Boolean toggle fields
            for fname in ("auto_detect_archetypes", "auto_advance_arcs",
                          "auto_capture_snapshots", "enable_meta_threads",
                          "enable_cross_session_links"):
                if fname in kwargs:
                    setattr(cfg, fname, bool(kwargs[fname]))
            # Clamped float fields in [0, 1]
            for fname, default in (("arc_tension_decay_rate", 0.02),
                                   ("archetype_confidence_threshold", 0.35),
                                   ("world_volatility", 0.5)):
                if fname in kwargs:
                    setattr(cfg, fname, _clamp(_safe_float(kwargs[fname], default), 0.0, 1.0))
            # Bounded integer / float fields
            if "snapshot_interval_ticks" in kwargs:
                cfg.snapshot_interval_ticks = max(
                    1, _safe_int(kwargs["snapshot_interval_ticks"], _SNAPSHOT_INTERVAL_TICKS))
            if "meta_tick_interval" in kwargs:
                cfg.meta_tick_interval = max(0.0, _safe_float(kwargs["meta_tick_interval"], 60.0))
            self._emit(MetaEventKind.META_REVEAL, title="config_updated",
                       description="Meta configuration updated.")
            return True, "updated", cfg

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            self._ticks_since_snapshot += 1
            dt_scaled = max(0.0, _safe_float(dt, 1.0))
            results: Dict[str, Any] = {
                "tick_count": self._tick_count, "arcs_advanced": 0,
                "threads_weaved": 0, "archetypes_detected": 0,
                "snapshots_captured": 0, "events_generated": 0,
                "world_shifts": 0, "dt": dt_scaled,
            }
            decay = self._config.arc_tension_decay_rate * dt_scaled

            # Advance active arcs whose investment has crossed the threshold
            if self._config.auto_advance_arcs:
                for arc in self._meta_arcs.values():
                    if arc.status != MetaStatus.ACTIVE.value:
                        continue
                    if arc.tension_level > 0.1:
                        arc.tension_level = _clamp(arc.tension_level - decay, 0.0, 1.0)
                    # Auto-advance when enough sessions have touched the arc
                    if len(arc.session_ids) >= arc.current_chapter + 1 and \
                            arc.player_investment > 0.35:
                        prev_phase = arc.phase
                        self.advance_meta_arc(arc.arc_id)
                        if arc.phase != prev_phase:
                            results["arcs_advanced"] += 1
                    # Auto-complete arcs that reach the resolved phase
                    if arc.phase == MetaPhase.RESOLVING.value and \
                            arc.current_chapter >= arc.total_chapters:
                        self.complete_meta_arc(arc.arc_id)

            # Auto-detect archetypes for active players
            if self._config.auto_detect_archetypes:
                for pid, profile in self._players.items():
                    if profile.session_count > 0:
                        before = profile.archetype
                        self._detect_archetype_internal(pid)
                        if self._players[pid].archetype != before:
                            results["archetypes_detected"] += 1

            # Auto-weave dormant threads into active arcs with sufficient investment
            if self._config.enable_meta_threads:
                for thread in self._meta_threads.values():
                    if thread.status != MetaStatus.PENDING.value or not thread.origin_arc_id:
                        continue
                    origin = self._meta_arcs.get(thread.origin_arc_id)
                    if not origin or origin.status != MetaStatus.ACTIVE.value:
                        continue
                    for arc in self._meta_arcs.values():
                        if (arc.status == MetaStatus.ACTIVE.value and
                                arc.arc_id != thread.origin_arc_id and
                                arc.arc_id not in thread.woven_arc_ids and
                                (thread.priority >= 2 or arc.player_investment > 0.4)):
                            self.weave_thread(thread.thread_id, arc.arc_id)
                            results["threads_weaved"] += 1
                            break

            # Periodically capture a world snapshot
            if self._config.auto_capture_snapshots and \
                    self._ticks_since_snapshot >= self._config.snapshot_interval_ticks:
                snap_res, _, _ = self.capture_world_snapshot(label=f"auto_tick_{self._tick_count}")
                if snap_res:
                    results["snapshots_captured"] += 1
                self._ticks_since_snapshot = 0

            # Generate a callback meta event occasionally to keep the world
            # feeling alive across sessions
            if self._tick_count % 10 == 0 and self._sessions:
                sample_session_id = random.choice(list(self._sessions.keys()))
                sample = self._sessions[sample_session_id]
                kind = (MetaEventKind.CROSS_SESSION_CALLBACK.value
                        if sample.arc_ids_touched else MetaEventKind.META_REVEAL.value)
                ok, _, _ = self.generate_meta_event(
                    kind=kind, title="periodic_callback",
                    description=f"The world remembers session {sample_session_id}.",
                    related_player_id=sample.player_id,
                    related_session_id=sample_session_id, severity="info")
                if ok:
                    results["events_generated"] += 1

            # Drift the world state slightly each tick toward equilibrium
            prev_state = self._world_state.get("world_state")
            self._world_state["threat_level"] = _clamp(
                _safe_float(self._world_state.get("threat_level")) - 0.01 * dt_scaled, 0.0, 1.0)
            self._world_state["stability_index"] = _clamp(
                _safe_float(self._world_state.get("stability_index")) + 0.01 * dt_scaled, 0.0, 1.0)
            new_state = self._derive_world_state_label()
            self._world_state["world_state"] = new_state
            if new_state != prev_state:
                results["world_shifts"] += 1
                self._emit(MetaEventKind.WORLD_SHIFT, title="world_shift",
                           description=f"World state drifted to {new_state}.", severity="notable")

            self._emit(MetaEventKind.META_REVEAL, title="tick",
                       description=f"tick_{self._tick_count} processed.")
            self._refresh_stats()
            return results

    def list_events(self, limit: int = 100) -> List[MetaEvent]:
        with _LOCK:
            return list(reversed(self._events[-max(0, limit):]))

    def reset(self) -> Tuple[bool, str]:
        with _LOCK:
            self._players.clear()
            self._sessions.clear()
            self._player_sessions.clear()
            self._meta_arcs.clear()
            self._meta_threads.clear()
            self._milestones.clear()
            self._decisions.clear()
            self._world_snapshots.clear()
            self._meta_events.clear()
            self._cross_session_links.clear()
            self._events.clear()
            self._stats = MetaStats()
            self._config = MetaConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._snap_counter = 0
            self._ticks_since_snapshot = 0
            self._world_state = {
                "world_state": WorldMetaState.STABLE.value,
                "stability_index": 0.7,
                "faction_balance": 0.5,
                "threat_level": 0.3,
                "prosperity": 0.5,
                "ley_activity": 0.4,
                "void_pressure": 0.2,
                "active_crisis_ids": [],
            }
            self._seeded = False
            self._initialized = False
            self._seed_data()
            self._seeded = True
            self._initialized = True
            self._emit(MetaEventKind.META_REVEAL, title="reset",
                       description="Meta game director reset and re-seeded.")
            return True, "reset"

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the director with demonstration data so it works on first use."""
        # --- Seed 5 player archetype profiles ---
        # Tuple: (id, name, archetype, dominant_type, pattern, session_count,
        #         playtime, engagement, milestones, arcs, threads, type_counts)
        seed_players = [
            ("player_lyra", "Lyra Ashbound", PlayerArchetype.STORY_SEEKER.value,
             SessionType.STORY.value, ProgressionPattern.DEEP_DIVE.value, 12, 54000.0, 0.82, 8, 3, 4,
             {SessionType.STORY.value: 7, SessionType.EXPLORATION.value: 3, SessionType.SOCIAL.value: 2}),
            ("player_kael", "Kael Stormrider", PlayerArchetype.COMBATANT.value,
             SessionType.COMBAT.value, ProgressionPattern.BURSTY.value, 9, 18000.0, 0.61, 5, 2, 2,
             {SessionType.COMBAT.value: 5, SessionType.BOSS_RUSH.value: 2, SessionType.STORY.value: 2}),
            ("player_seren", "Seren Brightforge", PlayerArchetype.BUILDER.value,
             SessionType.CRAFTING.value, ProgressionPattern.STEADY.value, 15, 72000.0, 0.74, 6, 1, 5,
             {SessionType.CRAFTING.value: 8, SessionType.SANDBOX.value: 4, SessionType.SOCIAL.value: 3}),
            ("player_orin", "Orin Vale", PlayerArchetype.COMPLETIONIST.value,
             SessionType.SIDE_QUEST.value, ProgressionPattern.COMPLETIONIST.value, 20, 90000.0, 0.88, 14, 5, 3,
             {SessionType.SIDE_QUEST.value: 10, SessionType.EXPLORATION.value: 6, SessionType.STORY.value: 4}),
            ("player_ves", "Ves Nightwhisper", PlayerArchetype.TACTICIAN.value,
             SessionType.COMBAT.value, ProgressionPattern.MASTERY.value, 11, 45000.0, 0.79, 7, 4, 2,
             {SessionType.COMBAT.value: 6, SessionType.COMPETITIVE.value: 3, SessionType.STORY.value: 2}),
        ]
        for (pid, name, arch, dom_type, pattern, sc, playtime, eng,
             miles, arcs, threads, type_counts) in seed_players:
            self._players[pid] = PlayerArchetypeProfile(
                player_id=pid, name=name, archetype=arch, confidence=0.65,
                session_count=sc, total_playtime=playtime, progression_pattern=pattern,
                dominant_session_type=dom_type, engagement_trend=eng, milestone_count=miles,
                arc_participation=arcs, thread_involvement=threads, session_type_counts=dict(type_counts),
                last_active=_now() - 3600, first_seen=_now() - 86400 * 30)
            self._player_sessions[pid] = []

        # --- Seed 5 meta arcs ---
        # Tuple: (id, title, desc, type, phase, status, theme, question,
        #         players, chapter, chapters, tension, stakes, investment)
        seed_arcs = [
            ("arc_void_resurgence", "The Void Resurgence",
             "Maltheris and his cult work across many sessions to tear the Veil, letting Void entities seep back into the material world.",
             MetaArcType.MYSTERY_UNFOLDING.value, MetaPhase.DEVELOPING.value, MetaStatus.ACTIVE.value,
             "Corruption from beyond", "Will the Veil hold against the growing Void pressure?",
             ["player_lyra", "player_ves"], 3, 6, 0.55, 0.6, 0.7),
            ("arc_star_forge_awakening", "Star Forge Awakening",
             "The ancient precursor device beneath Nexus stirs to life, drawing every kingdom into a race to control its power.",
             MetaArcType.DISCOVERY.value, MetaPhase.EMERGING.value, MetaStatus.ACTIVE.value,
             "Awakening power", "What is the true purpose of the Star Forge?",
             ["player_orin", "player_lyra"], 2, 5, 0.4, 0.5, 0.55),
            ("arc_skylands_war", "The Skylands War",
             "Aethelgard and the sky-nomads clash over control of the floating islands, escalating across sessions into open conflict.",
             MetaArcType.CONFLICT_ESCALATION.value, MetaPhase.CULMINATING.value, MetaStatus.ACTIVE.value,
             "Escalating conflict", "Can the Skylands War be stopped before it consumes the skies?",
             ["player_kael", "player_ves"], 4, 5, 0.7, 0.75, 0.6),
            ("arc_lyra_growth", "Lyra's Ascension",
             "Lyra masters her rare sight of the Ley Lines, growing from apprentice to a force that can shape the world's fate.",
             MetaArcType.CHARACTER_GROWTH.value, MetaPhase.DEVELOPING.value, MetaStatus.ACTIVE.value,
             "Personal growth", "Will Lyra accept the burden her gift places on her?",
             ["player_lyra"], 3, 5, 0.5, 0.55, 0.8),
            ("arc_compact_schism", "The Compact Schism",
             "The Veilwright Compact fractures over whether to maintain or tear down the Veil, deepening a rift across many sessions.",
             MetaArcType.RELATIONSHIP_DEEPENING.value, MetaPhase.DORMANT.value, MetaStatus.PENDING.value,
             "Institutional fracture", "Can the Compact survive its own internal war?",
             ["player_seren", "player_orin"], 0, 5, 0.2, 0.3, 0.4),
        ]
        for (aid, title, desc, atype, phase, status, theme, question,
             players, chapter, chapters, tension, stakes, invest) in seed_arcs:
            self._meta_arcs[aid] = MetaArc(
                arc_id=aid, title=title, description=desc, arc_type=atype, phase=phase,
                status=status, theme=theme, central_question=question,
                involved_player_ids=list(players), current_chapter=chapter, total_chapters=chapters,
                tension_level=tension, stakes_level=stakes, player_investment=invest,
                started_at=_now() - 86400 * 14)

        # --- Seed 8 meta threads ---
        # Tuple: (id, title, desc, origin_arc, type, players, priority, tension)
        seed_threads = [
            ("thread_missing_mentor", "The Missing Mentor",
             "Master Corwin vanished while investigating the Star Forge; clues surface across sessions.",
             "arc_lyra_growth", "mystery", ["player_lyra"], 3, 0.5),
            ("thread_void_whispers", "Void Whispers",
             "Faint whispers from beyond the Veil reach those sensitive to ley energy, hinting at what lies beyond.",
             "arc_void_resurgence", "omen", ["player_lyra", "player_ves"], 2, 0.6),
            ("thread_ley_convergence", "The Ley Convergence Prophecy",
             "An ancient prophecy speaks of a day when all ley lines align, either renewing or unmaking the world.",
             "arc_star_forge_awakening", "prophecy", ["player_orin"], 2, 0.7),
            ("thread_star_forge_purpose", "True Purpose of the Star Forge",
             "The Forge was not built to shape constructs but to hold something far older in check.",
             "arc_star_forge_awakening", "secret", ["player_orin", "player_lyra"], 3, 0.65),
            ("thread_sky_nomad_exodus", "The Sky Nomad Exodus",
             "The sky-nomads flee their ancestral islands as war engulfs the Skylands, seeking refuge below.",
             "arc_skylands_war", "displacement", ["player_kael"], 2, 0.5),
            ("thread_dreamweave_breach", "The Dreamweave Thinning",
             "The boundary between dream and waking reality grows thin, letting dream-spirits cross over.",
             "arc_void_resurgence", "incursion", ["player_seren"], 1, 0.55),
            ("thread_maltheris_doubt", "Maltheris's Hidden Doubt",
             "Beneath his conviction, Maltheris harbors a seed of doubt planted by a memory he cannot explain.",
             "arc_void_resurgence", "character", ["player_ves"], 2, 0.6),
            ("thread_fifth_kingdom", "The Lost Fifth Kingdom",
             "Legends speak of a sixth kingdom that vanished at the Sundering, its fate tied to the Star Forge.",
             "arc_compact_schism", "legend", ["player_orin", "player_seren"], 1, 0.45),
        ]
        for (tid, title, desc, origin, ttype, players, prio, tension) in seed_threads:
            origin_arc = self._meta_arcs.get(origin)
            status = (MetaStatus.ACTIVE.value if origin_arc and
                      origin_arc.status == MetaStatus.ACTIVE.value
                      else MetaStatus.PENDING.value)
            self._meta_threads[tid] = MetaThread(
                thread_id=tid, title=title, description=desc, origin_arc_id=origin,
                thread_type=ttype, status=status, involved_player_ids=list(players),
                priority=prio, tension_contribution=tension, created_at=_now() - 86400 * 10)
            if origin_arc and tid not in origin_arc.thread_ids:
                origin_arc.thread_ids.append(tid)

        # Weave a couple of threads across arcs to demonstrate cross-arc weaving
        self._weave_seed("thread_void_whispers", "arc_lyra_growth",
                         "Void whispers reach Lyra through her ley sight.")
        self._weave_seed("thread_star_forge_purpose", "arc_void_resurgence",
                         "The Forge's true purpose ties into the Void's return.")

        # --- Seed 5 milestones ---
        # Tuple: (id, player, title, desc, type, arc_id, significance, acknowledged)
        seed_milestones = [
            ("mile_first_sight", "player_lyra", "First Ley Sight",
             "Lyra first saw the ley lines with her naked eye.", "ability", "arc_lyra_growth", 0.8, True),
            ("mile_void_witness", "player_ves", "Witnessed the Void",
             "Ves survived a direct encounter with a Void entity.", "survival", "arc_void_resurgence", 0.85, True),
            ("mile_sky_champion", "player_kael", "Skylands Champion",
             "Kael won a decisive aerial duel over the Skylands.", "combat", "arc_skylands_war", 0.7, True),
            ("mile_forge_touched", "player_orin", "Touched the Star Forge",
             "Orin made first contact with the awakening Star Forge.", "discovery", "arc_star_forge_awakening", 0.9, False),
            ("mile_compact_oath", "player_seren", "Swore the Compact Oath",
             "Seren formally joined the Veilwright Compact.", "social", "arc_compact_schism", 0.5, True),
        ]
        for (mid, pid, title, desc, mtype, arc_id, sig, ack) in seed_milestones:
            self._milestones[mid] = ProgressionMilestone(
                milestone_id=mid, player_id=pid, title=title, description=desc,
                milestone_type=mtype, arc_id=arc_id, significance=sig, acknowledged=ack,
                achieved_at=_now() - 86400 * 7 if ack else 0.0)
            arc = self._meta_arcs.get(arc_id)
            if arc and mid not in arc.milestone_ids:
                arc.milestone_ids.append(mid)

        # --- Seed 3 world meta snapshots ---
        # Tuple: (id, label, state, stability, faction, threat, prosperity, ley,
        #         void, crises, changes, player_changes, session_count)
        seed_snapshots = [
            ("snap_000001", "Post-Sundering Equilibrium", WorldMetaState.STABLE.value,
             0.75, 0.5, 0.25, 0.6, 0.35, 0.15, [],
             ["The world settled into a fragile peace after the Sundering."], [], 0),
            ("snap_000002", "The Veil Begins to Thin", WorldMetaState.TURBULENT.value,
             0.55, 0.45, 0.5, 0.5, 0.5, 0.4, ["crisis_veil_thinning"],
             ["Void pressure rose as Maltheris's cult gained followers."],
             ["player_ves witnessed the Void", "player_lyra saw ley surges"], 5),
            ("snap_000003", "Star Forge Stirs", WorldMetaState.TRANSFORMING.value,
             0.4, 0.35, 0.65, 0.45, 0.7, 0.5,
             ["crisis_veil_thinning", "crisis_forge_awakening"],
             ["The Star Forge reactivated, sending ley activity soaring."],
             ["player_orin touched the Star Forge", "player_kael contested the Skylands"], 9),
        ]
        for (sid, label, state, stab, fac, threat, pros, ley, void,
             crises, changes, player_changes, sess) in seed_snapshots:
            self._world_snapshots[sid] = WorldMetaSnapshot(
                snapshot_id=sid, label=label, world_state=state, stability_index=stab,
                faction_balance=fac, threat_level=threat, prosperity=pros, ley_activity=ley,
                void_pressure=void, active_crisis_ids=list(crises), notable_changes=list(changes),
                player_driven_changes=list(player_changes), session_count=sess,
                captured_at=_now() - 86400 * (3 - int(sid[-1])))

        # Set the live world state to match the most recent snapshot
        latest = self._world_snapshots.get("snap_000003")
        if latest:
            self._world_state = {
                "world_state": latest.world_state, "stability_index": latest.stability_index,
                "faction_balance": latest.faction_balance, "threat_level": latest.threat_level,
                "prosperity": latest.prosperity, "ley_activity": latest.ley_activity,
                "void_pressure": latest.void_pressure,
                "active_crisis_ids": list(latest.active_crisis_ids),
            }

        # --- Seed 2 cross-session links for demonstration ---
        # Tuple: (id, player, type, source_sess, target_sess, strength, desc, arc_id, thread_id)
        seed_links = [
            ("csl_seed_1", "player_lyra", "shared_arc", "sess_seed_lyra_1",
             "sess_seed_lyra_2", 0.7, "Two sessions both advanced the Void Resurgence arc.",
             "arc_void_resurgence", ""),
            ("csl_seed_2", "player_orin", "shared_thread", "sess_seed_orin_1",
             "sess_seed_orin_2", 0.6, "Two sessions both touched the Star Forge Purpose thread.",
             "", "thread_star_forge_purpose"),
        ]
        for (lid, pid, ltype, src, tgt, strength, desc, arc_id, tid) in seed_links:
            self._cross_session_links[lid] = CrossSessionLink(
                link_id=lid, player_id=pid, link_type=ltype, source_session_id=src,
                target_session_id=tgt, strength=strength, description=desc,
                related_arc_id=arc_id, related_thread_id=tid, discovered_at=_now() - 86400 * 2)

        # --- Seed a meta decision pending application ---
        self._decisions["dec_void_containment"] = MetaDecision(
            decision_id="dec_void_containment", title="Reinforce the Veil",
            description="Divert ley energy to thicken the Veil at its thinnest points, slowing the Void incursion.",
            rationale="Accumulated player actions show the Void pressure rising across multiple sessions. Reinforcing the Veil buys time for a lasting solution.",
            decision_type="defensive", scope="world",
            affected_arc_ids=["arc_void_resurgence"],
            affected_thread_ids=["thread_void_whispers", "thread_dreamweave_breach"],
            affected_player_ids=["player_lyra", "player_ves"],
            world_impact=0.6, priority=3, confidence=0.7,
            expected_outcome="Void pressure drops and stability rises.")

        # --- Seed 2 meta events that call back to past sessions ---
        # Tuple: (id, kind, title, desc, arc_id, thread_id, player_id, session_id,
        #         milestone_id, decision_id, severity, scope)
        seed_meta_events = [
            ("mevt_seed_callback_1", MetaEventKind.CROSS_SESSION_CALLBACK.value,
             "Echo of the First Breach",
             "The world still hums where the Void first broke through in an early session, a scar that shapes current events.",
             "arc_void_resurgence", "thread_void_whispers", "player_lyra",
             "sess_seed_lyra_1", "", "", "notable", "meta"),
            ("mevt_seed_reveal_1", MetaEventKind.META_REVEAL.value, "The Forge Responds",
             "The Star Forge pulsed in response to Orin's earlier contact, a sign that past actions ripple forward.",
             "arc_star_forge_awakening", "thread_star_forge_purpose",
             "player_orin", "sess_seed_orin_1", "mile_forge_touched", "", "notable", "meta"),
        ]
        for (eid, kind, title, desc, arc_id, tid, pid, sid, mid, did,
             sev, scope) in seed_meta_events:
            self._meta_events[eid] = MetaEvent(
                event_id=eid, kind=kind, title=title, description=desc,
                related_arc_id=arc_id, related_thread_id=tid, related_player_id=pid,
                related_session_id=sid, related_milestone_id=mid, related_decision_id=did,
                severity=sev, scope=scope, timestamp=_now() - 86400)

        self._refresh_stats()
        self._emit(
            MetaEventKind.META_REVEAL, title="seeded",
            description="Meta game director seeded with demonstration data: 5 players, "
                        "5 arcs, 8 threads, 5 milestones, 3 world snapshots, "
                        "2 cross-session links, 1 decision, 2 meta events.",
            severity="info")

    def _weave_seed(self, thread_id: str, target_arc_id: str, description: str) -> None:
        """Internal seed helper to weave a thread without emitting events."""
        thread = self._meta_threads.get(thread_id)
        target = self._meta_arcs.get(target_arc_id)
        if not thread or not target:
            return
        if target_arc_id not in thread.woven_arc_ids:
            thread.woven_arc_ids.append(target_arc_id)
        if thread_id not in target.thread_ids:
            target.thread_ids.append(thread_id)
            target.tension_level = _clamp(
                target.tension_level + thread.tension_contribution * 0.3, 0.0, 1.0)
        thread.status = MetaStatus.ACTIVE.value
        thread.key_moments.append(f"Woven into {target_arc_id}: {description}")


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_ai_meta_game_director() -> AIMetaGameDirector:
    """Return the singleton AIMetaGameDirector, initializing seed data on first use."""
    inst = AIMetaGameDirector.get_instance()
    if not getattr(inst, "_seeded", False):
        inst.initialize()
    return inst
