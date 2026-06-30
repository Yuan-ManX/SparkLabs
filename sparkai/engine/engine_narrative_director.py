"""
SparkLabs Engine - Narrative Director

Engine-side narrative runtime subsystem that manages active story arcs,
story beats, branching decision points, and coordinates narrative state
with quest, dialogue, and cutscene subsystems. Provides a structured canvas
for agent narrative decisions to execute at runtime.

The narrative director maintains a forest of story arcs, each composed of
ordered beats with optional branching choices. Beats progress through
PENDING -> ACTIVE -> COMPLETED (or SKIPPED / CANCELLED) states. When a
beat completes, the director evaluates gating conditions to determine
which subsequent beats become available.

This subsystem focuses on runtime state tracking and beat progression.
Creative narrative generation is delegated to agent-side modules; this
module executes the resulting narrative structure within the engine.

Architecture:
  NarrativeDirectorEngine (Singleton)
    |-- StoryArc                   (a named narrative arc of ordered beats)
    |-- NarrativeBeat              (a single beat within an arc)
    |-- NarrativeChoice            (a player-selectable branching option)
    |-- StoryFlag                  (a named narrative state flag)
    |-- NarrativeEvent             (an emitted narrative lifecycle event)
    |-- NarrativeDirectorSnapshot  (immutable snapshot of director state)

Lifecycle:
  1. register_arc(arc) / create_arc(...)        -> StoryArc
  2. add_beat(arc_id, beat) / create_beat(...)  -> NarrativeBeat
  3. start_arc(arc_id)                          -> StoryArc
  4. activate_beat(beat_id)                     -> NarrativeBeat
  5. present_choice(beat_id, choice_id)         -> NarrativeChoice
  6. make_choice(beat_id, choice_id)            -> NarrativeChoice
  7. complete_beat(beat_id, choice_id=None)     -> NarrativeBeat
  8. complete_arc(arc_id) / abandon_arc(arc_id) -> StoryArc
  9. get_snapshot() / get_status() / reset()
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Enumerations
# =============================================================================


class BeatStatus(Enum):
    """Lifecycle states for a single narrative beat."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    FAILED = "failed"
    LOCKED = "locked"


class ArcStatus(Enum):
    """Lifecycle states for a story arc."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FAILED = "failed"


class BeatType(Enum):
    """Thematic classification for a narrative beat."""

    NARRATIVE = "narrative"
    DIALOGUE = "dialogue"
    COMBAT = "combat"
    PUZZLE = "puzzle"
    EXPLORATION = "exploration"
    CINEMATIC = "cinematic"
    CHOICE = "choice"
    CUSTOM = "custom"


class ChoiceImpact(Enum):
    """Severity classification for the consequence of a choice."""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class GateType(Enum):
    """Categories of gating conditions evaluated before a beat activates."""

    STORY_FLAG = "story_flag"
    QUEST_COMPLETE = "quest_complete"
    ENTITY_STATE = "entity_state"
    LEVEL_REACHED = "level_reached"
    CUSTOM = "custom"


class NarrativeEventKind(Enum):
    """Kinds of events emitted by the narrative director."""

    ARC_STARTED = "arc_started"
    ARC_COMPLETED = "arc_completed"
    BEAT_ACTIVATED = "beat_activated"
    BEAT_COMPLETED = "beat_completed"
    CHOICE_PRESENTED = "choice_presented"
    CHOICE_MADE = "choice_made"
    BRANCH_TAKEN = "branch_taken"
    FLAG_SET = "flag_set"
    FLAG_CLEARED = "flag_cleared"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class StoryFlag:
    """A named narrative state flag with an associated value.

    Flags are the primary mechanism for gating beat progression and
    recording narrative decisions. A flag may be scoped to a specific
    domain (e.g. ``"global"``, ``"arc"``) to namespace its effect.

    Attributes:
        name: Unique identifier for the flag.
        value: Arbitrary serializable value held by the flag.
        set_at: Timestamp at which the flag was last written.
        scope: Logical scope grouping for the flag.
    """

    name: str
    value: Any = None
    set_at: Optional[datetime.datetime] = field(default_factory=datetime.datetime.now)
    scope: str = "global"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "set_at": self.set_at.isoformat() if self.set_at else None,
            "scope": self.scope,
        }


@dataclass
class NarrativeChoice:
    """A player-selectable branching option attached to a beat.

    When a choice is made, its ``consequences`` are applied as narrative
    flags and the optional ``next_beat_id`` determines which beat becomes
    the continuation of the arc.

    Attributes:
        id: Unique identifier (auto-generated).
        text: Display text shown to the player.
        consequences: Mapping of flag name to value applied on selection.
        impact: Severity classification of the choice.
        next_beat_id: Identifier of the beat to follow when chosen.
        metadata: Free-form extension data.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    text: str = ""
    consequences: Dict[str, Any] = field(default_factory=dict)
    impact: ChoiceImpact = ChoiceImpact.MINOR
    next_beat_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "consequences": dict(self.consequences),
            "impact": self.impact.value,
            "next_beat_id": self.next_beat_id,
            "metadata": dict(self.metadata),
        }


@dataclass
class NarrativeBeat:
    """A single narrative beat within a story arc.

    Beats are the atomic unit of narrative progression. Each beat carries
    an optional gating condition that must be satisfied before activation,
    a set of flags written on completion, and an optional list of choices
    for branching beats.

    Attributes:
        id: Unique identifier (auto-generated).
        arc_id: Identifier of the owning arc.
        order: Sort order within the arc (ascending).
        beat_type: Thematic classification of the beat.
        title: Human-readable title.
        description: Long-form description of the beat content.
        status: Current lifecycle state.
        choices: Branching options available on this beat.
        gate_condition: Optional gate dict evaluated on activation.
        required_flags: Flag names that must be present to activate.
        set_flags_on_complete: Flag name/value pairs written on completion.
        next_beat_id: Identifier of the default following beat.
        metadata: Free-form extension data.
        started_at: Timestamp when the beat became active.
        completed_at: Timestamp when the beat reached a terminal state.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    arc_id: str = ""
    order: int = 0
    beat_type: BeatType = BeatType.NARRATIVE
    title: str = ""
    description: str = ""
    status: BeatStatus = BeatStatus.PENDING
    choices: List[NarrativeChoice] = field(default_factory=list)
    gate_condition: Optional[Dict[str, Any]] = None
    required_flags: List[str] = field(default_factory=list)
    set_flags_on_complete: Dict[str, Any] = field(default_factory=dict)
    next_beat_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "arc_id": self.arc_id,
            "order": self.order,
            "beat_type": self.beat_type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "choices": [c.to_dict() for c in self.choices],
            "gate_condition": dict(self.gate_condition) if self.gate_condition else None,
            "required_flags": list(self.required_flags),
            "set_flags_on_complete": dict(self.set_flags_on_complete),
            "next_beat_id": self.next_beat_id,
            "metadata": dict(self.metadata),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class StoryArc:
    """A named narrative arc composed of ordered beats.

    An arc owns its beat collection, tracks the currently active beat,
    and maintains a local flag namespace. Arcs progress through the
    ``ArcStatus`` lifecycle from ``DRAFT`` to a terminal state.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name of the arc.
        description: Long-form description of the arc.
        status: Current lifecycle state.
        beats: Ordered list of beats belonging to the arc.
        active_beat_id: Identifier of the currently active beat, if any.
        start_beat_id: Identifier of the entry beat.
        priority: Ordering priority (lower values activate earlier).
        flags: Local flag namespace for the arc.
        metadata: Free-form extension data.
        started_at: Timestamp when the arc became active.
        completed_at: Timestamp when the arc reached a terminal state.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    status: ArcStatus = ArcStatus.DRAFT
    beats: List[NarrativeBeat] = field(default_factory=list)
    active_beat_id: Optional[str] = None
    start_beat_id: Optional[str] = None
    priority: int = 0
    flags: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "beats": [b.to_dict() for b in self.beats],
            "active_beat_id": self.active_beat_id,
            "start_beat_id": self.start_beat_id,
            "priority": self.priority,
            "flags": dict(self.flags),
            "metadata": dict(self.metadata),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class NarrativeEvent:
    """An immutable record of a narrative lifecycle event.

    Attributes:
        id: Unique identifier (auto-generated).
        kind: The ``NarrativeEventKind`` of the event.
        arc_id: Identifier of the associated arc, if any.
        beat_id: Identifier of the associated beat, if any.
        choice_id: Identifier of the associated choice, if any.
        payload: Free-form payload describing the event.
        timestamp: Time at which the event was emitted.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: NarrativeEventKind = NarrativeEventKind.BEAT_ACTIVATED
    arc_id: Optional[str] = None
    beat_id: Optional[str] = None
    choice_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "arc_id": self.arc_id,
            "beat_id": self.beat_id,
            "choice_id": self.choice_id,
            "payload": dict(self.payload),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class NarrativeDirectorSnapshot:
    """An immutable snapshot of the narrative director state.

    Attributes:
        arc_count: Total number of registered arcs.
        active_arc_count: Number of arcs currently active.
        beat_count: Total number of registered beats.
        active_beat_count: Number of beats currently active.
        flag_count: Total number of narrative flags set.
        event_count: Total number of events retained.
        stats: Aggregated statistic counters.
        timestamp: Time at which the snapshot was taken.
    """

    arc_count: int = 0
    active_arc_count: int = 0
    beat_count: int = 0
    active_beat_count: int = 0
    flag_count: int = 0
    event_count: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arc_count": self.arc_count,
            "active_arc_count": self.active_arc_count,
            "beat_count": self.beat_count,
            "active_beat_count": self.active_beat_count,
            "flag_count": self.flag_count,
            "event_count": self.event_count,
            "stats": dict(self.stats),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =============================================================================
# Narrative Director Engine (Singleton)
# =============================================================================


class NarrativeDirectorEngine:
    """Engine-side narrative runtime that executes story arcs and beats.

    Maintains a registry of story arcs, their constituent beats, narrative
    flags, and a rolling event log. Coordinates beat activation through
    gating conditions, applies consequence flags on choice selection, and
    emits lifecycle events to subscribed handlers.

    All public methods are thread-safe. The class implements the singleton
    pattern with double-checked locking; consumers should obtain the
    instance through :meth:`get_instance` or :func:`get_narrative_director`.
    """

    _instance: Optional["NarrativeDirectorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if getattr(self, "_initialized", False):
            return

        # Primary registries.
        self._arcs: Dict[str, StoryArc] = {}
        self._beat_index: Dict[str, NarrativeBeat] = {}
        self._beat_to_arc: Dict[str, str] = {}

        # Narrative flags scoped by name.
        self._flags: Dict[str, StoryFlag] = {}

        # Event log and subscriber registry.
        self._events: List[NarrativeEvent] = []
        self._event_handlers: Dict[str, List[Callable[[NarrativeEvent], None]]] = {}
        self._total_events_emitted: int = 0

        # Custom gate handlers keyed by handler key.
        self._custom_gate_handlers: Dict[str, Callable[[Dict[str, Any]], bool]] = {}

        # Choice bookkeeping.
        self._beat_choices: Dict[str, str] = {}
        self._presented_choices: Dict[str, bool] = {}
        self._total_choices_presented: int = 0
        self._total_choices_made: int = 0

        self._initialized: bool = True

        # Populate the default seed narrative.
        self._seed_default_data()

    @classmethod
    def get_instance(cls) -> "NarrativeDirectorEngine":
        """Return the singleton NarrativeDirectorEngine instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_beat(self, beat_id: str) -> Optional[Tuple[StoryArc, NarrativeBeat]]:
        """Locate the arc and beat for a given beat identifier."""
        arc_id = self._beat_to_arc.get(beat_id)
        if arc_id is None:
            return None
        arc = self._arcs.get(arc_id)
        if arc is None:
            return None
        beat = self._beat_index.get(beat_id)
        if beat is None:
            return None
        return arc, beat

    def _index_beat(self, arc: StoryArc, beat: NarrativeBeat) -> None:
        """Register a beat in the lookup indexes."""
        beat.arc_id = arc.id
        self._beat_index[beat.id] = beat
        self._beat_to_arc[beat.id] = arc.id

    def _unindex_beat(self, beat_id: str) -> None:
        """Remove a beat from the lookup indexes."""
        self._beat_index.pop(beat_id, None)
        self._beat_to_arc.pop(beat_id, None)

    @staticmethod
    def _normalize_kind(kind: Any) -> str:
        """Normalize an event kind argument to its string value."""
        if kind is None:
            return "*"
        if isinstance(kind, NarrativeEventKind):
            return kind.value
        return str(kind)

    @staticmethod
    def _normalize_gate_type(gate_type: Any) -> str:
        """Normalize a gate type argument to its string value."""
        if isinstance(gate_type, GateType):
            return gate_type.value
        return str(gate_type).lower()

    def _compute_stats(self) -> Dict[str, Any]:
        """Compute the aggregate statistic counters from current state."""
        total_arcs = len(self._arcs)
        active_arcs = sum(
            1 for a in self._arcs.values() if a.status == ArcStatus.ACTIVE
        )
        completed_arcs = sum(
            1 for a in self._arcs.values() if a.status == ArcStatus.COMPLETED
        )
        abandoned_arcs = sum(
            1 for a in self._arcs.values() if a.status == ArcStatus.ABANDONED
        )

        total_beats = len(self._beat_index)
        active_beats = sum(
            1 for b in self._beat_index.values() if b.status == BeatStatus.ACTIVE
        )
        completed_beats = sum(
            1 for b in self._beat_index.values() if b.status == BeatStatus.COMPLETED
        )
        skipped_beats = sum(
            1 for b in self._beat_index.values() if b.status == BeatStatus.SKIPPED
        )

        return {
            "total_arcs": total_arcs,
            "active_arcs": active_arcs,
            "completed_arcs": completed_arcs,
            "abandoned_arcs": abandoned_arcs,
            "total_beats": total_beats,
            "active_beats": active_beats,
            "completed_beats": completed_beats,
            "skipped_beats": skipped_beats,
            "total_choices_presented": self._total_choices_presented,
            "total_choices_made": self._total_choices_made,
            "total_events_emitted": self._total_events_emitted,
        }

    def _dispatch_event(self, event: NarrativeEvent) -> None:
        """Deliver an event to all matching registered handlers."""
        kind_value = event.kind.value
        for key in (kind_value, "*"):
            handlers = self._event_handlers.get(key)
            if not handlers:
                continue
            for handler in list(handlers):
                try:
                    handler(event)
                except Exception:
                    # A failing handler must not break event dispatch.
                    pass

    # ------------------------------------------------------------------
    # Arc management
    # ------------------------------------------------------------------

    def register_arc(self, arc: StoryArc) -> StoryArc:
        """Register a fully constructed story arc in the director.

        Args:
            arc: The StoryArc to register. Its beats are indexed for
                lookup. If no ``start_beat_id`` is set and the arc has at
                least one beat, the first beat becomes the start beat.

        Returns:
            The registered StoryArc.

        Raises:
            ValueError: If an arc with the same id is already registered.
        """
        with self._lock:
            if arc.id in self._arcs:
                raise ValueError(f"Arc already registered: {arc.id}")
            self._arcs[arc.id] = arc
            for beat in arc.beats:
                self._index_beat(arc, beat)
            if arc.start_beat_id is None and arc.beats:
                arc.start_beat_id = arc.beats[0].id
            self._emit_event(
                NarrativeEventKind.ARC_STARTED,
                arc_id=arc.id,
                beat_id=None,
                choice_id=None,
                payload={"name": arc.name, "status": arc.status.value},
            )
            return arc

    def create_arc(
        self,
        name: str,
        description: str = "",
        start_beat_title: str = "Start",
        priority: int = 0,
    ) -> StoryArc:
        """Create a new arc with a single initial beat and register it.

        Args:
            name: Human-readable name of the arc.
            description: Long-form description of the arc.
            start_beat_title: Title of the initial beat.
            priority: Ordering priority of the arc.

        Returns:
            The newly created and registered StoryArc.
        """
        with self._lock:
            arc = StoryArc(
                name=name,
                description=description,
                status=ArcStatus.DRAFT,
                priority=priority,
            )
            initial_beat = NarrativeBeat(
                arc_id=arc.id,
                order=1,
                beat_type=BeatType.NARRATIVE,
                title=start_beat_title,
            )
            arc.beats.append(initial_beat)
            arc.start_beat_id = initial_beat.id
            self._index_beat(arc, initial_beat)
            self._arcs[arc.id] = arc
            self._emit_event(
                NarrativeEventKind.ARC_STARTED,
                arc_id=arc.id,
                beat_id=None,
                choice_id=None,
                payload={"name": arc.name, "status": arc.status.value},
            )
            return arc

    def get_arc(self, arc_id: str) -> Optional[StoryArc]:
        """Retrieve a registered arc by its identifier."""
        with self._lock:
            return self._arcs.get(arc_id)

    def list_arcs(self, status: Optional[ArcStatus] = None) -> List[StoryArc]:
        """List registered arcs, optionally filtered by status.

        The returned list is sorted by ascending priority then name.
        """
        with self._lock:
            arcs = list(self._arcs.values())
            if status is not None:
                arcs = [a for a in arcs if a.status == status]
            arcs.sort(key=lambda a: (a.priority, a.name))
            return arcs

    def remove_arc(self, arc_id: str) -> bool:
        """Remove an arc and all of its beats from the director.

        Returns:
            True if the arc was removed, False if it was not found.
        """
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                return False
            for beat in arc.beats:
                self._unindex_beat(beat.id)
                self._beat_choices.pop(beat.id, None)
                self._presented_choices.pop(beat.id, None)
            del self._arcs[arc_id]
            return True

    def start_arc(self, arc_id: str) -> StoryArc:
        """Activate an arc by activating its start beat.

        Sets the arc status to ``ACTIVE``, records the start time, and
        activates the start beat. If the arc is already active, it is
        returned unchanged.

        Args:
            arc_id: Identifier of the arc to start.

        Returns:
            The started StoryArc.

        Raises:
            ValueError: If the arc is not found or has no start beat.
        """
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                raise ValueError(f"Arc not found: {arc_id}")
            if arc.status == ArcStatus.ACTIVE:
                return arc
            if arc.start_beat_id is None:
                raise ValueError(f"Arc has no start beat: {arc_id}")
            arc.status = ArcStatus.ACTIVE
            arc.started_at = datetime.datetime.now()
            arc.completed_at = None
            self.activate_beat(arc.start_beat_id)
            return arc

    def pause_arc(self, arc_id: str) -> StoryArc:
        """Pause an active arc.

        Raises:
            ValueError: If the arc is not found.
        """
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                raise ValueError(f"Arc not found: {arc_id}")
            arc.status = ArcStatus.PAUSED
            return arc

    def resume_arc(self, arc_id: str) -> StoryArc:
        """Resume a paused arc.

        Raises:
            ValueError: If the arc is not found.
        """
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                raise ValueError(f"Arc not found: {arc_id}")
            arc.status = ArcStatus.ACTIVE
            return arc

    def complete_arc(self, arc_id: str) -> StoryArc:
        """Mark an arc as completed.

        Raises:
            ValueError: If the arc is not found.
        """
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                raise ValueError(f"Arc not found: {arc_id}")
            arc.status = ArcStatus.COMPLETED
            arc.completed_at = datetime.datetime.now()
            self._emit_event(
                NarrativeEventKind.ARC_COMPLETED,
                arc_id=arc.id,
                beat_id=None,
                choice_id=None,
                payload={"name": arc.name},
            )
            return arc

    def abandon_arc(self, arc_id: str) -> StoryArc:
        """Mark an arc as abandoned.

        Raises:
            ValueError: If the arc is not found.
        """
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                raise ValueError(f"Arc not found: {arc_id}")
            arc.status = ArcStatus.ABANDONED
            arc.completed_at = datetime.datetime.now()
            return arc

    # ------------------------------------------------------------------
    # Beat management
    # ------------------------------------------------------------------

    def add_beat(self, arc_id: str, beat: NarrativeBeat) -> NarrativeBeat:
        """Add a fully constructed beat to an existing arc.

        Args:
            arc_id: Identifier of the owning arc.
            beat: The NarrativeBeat to add.

        Returns:
            The added NarrativeBeat.

        Raises:
            ValueError: If the arc is not found or the beat id collides.
        """
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                raise ValueError(f"Arc not found: {arc_id}")
            if beat.id in self._beat_index:
                raise ValueError(f"Beat already registered: {beat.id}")
            self._index_beat(arc, beat)
            arc.beats.append(beat)
            arc.beats.sort(key=lambda b: b.order)
            if arc.start_beat_id is None:
                arc.start_beat_id = beat.id
            return beat

    def create_beat(
        self,
        arc_id: str,
        beat_type: BeatType,
        title: str,
        description: str = "",
        order: int = 0,
        gate_condition: Optional[Dict[str, Any]] = None,
    ) -> NarrativeBeat:
        """Create a new beat and add it to an arc.

        Args:
            arc_id: Identifier of the owning arc.
            beat_type: Thematic classification of the beat.
            title: Human-readable title.
            description: Long-form description.
            order: Sort order within the arc.
            gate_condition: Optional gate dict evaluated on activation.

        Returns:
            The newly created NarrativeBeat.

        Raises:
            ValueError: If the arc is not found.
        """
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                raise ValueError(f"Arc not found: {arc_id}")
            beat = NarrativeBeat(
                arc_id=arc.id,
                order=order,
                beat_type=beat_type,
                title=title,
                description=description,
                gate_condition=gate_condition,
            )
            self._index_beat(arc, beat)
            arc.beats.append(beat)
            arc.beats.sort(key=lambda b: b.order)
            if arc.start_beat_id is None:
                arc.start_beat_id = beat.id
            return beat

    def get_beat(self, beat_id: str) -> Optional[NarrativeBeat]:
        """Retrieve a beat by its identifier."""
        with self._lock:
            return self._beat_index.get(beat_id)

    def list_beats(
        self,
        arc_id: Optional[str] = None,
        status: Optional[BeatStatus] = None,
    ) -> List[NarrativeBeat]:
        """List beats, optionally filtered by arc and status.

        Args:
            arc_id: When provided, restricts results to the given arc.
            status: When provided, restricts results to the given status.

        Returns:
            A list of matching beats sorted by ascending order.
        """
        with self._lock:
            if arc_id is not None:
                arc = self._arcs.get(arc_id)
                beats = list(arc.beats) if arc is not None else []
            else:
                beats = list(self._beat_index.values())
            if status is not None:
                beats = [b for b in beats if b.status == status]
            beats.sort(key=lambda b: b.order)
            return beats

    def remove_beat(self, beat_id: str) -> bool:
        """Remove a beat from its arc.

        Returns:
            True if the beat was removed, False if it was not found.
        """
        with self._lock:
            resolved = self._resolve_beat(beat_id)
            if resolved is None:
                return False
            arc, beat = resolved
            arc.beats = [b for b in arc.beats if b.id != beat_id]
            self._unindex_beat(beat_id)
            self._beat_choices.pop(beat_id, None)
            self._presented_choices.pop(beat_id, None)
            if arc.active_beat_id == beat_id:
                arc.active_beat_id = None
            if arc.start_beat_id == beat_id:
                arc.start_beat_id = arc.beats[0].id if arc.beats else None
            return True

    def activate_beat(self, beat_id: str) -> NarrativeBeat:
        """Activate a beat after evaluating its gating conditions.

        Sets the beat status to ``ACTIVE``, records the start time, and
        marks it as the arc's active beat. The gate condition and required
        flags must be satisfied; otherwise a ``ValueError`` is raised.

        Args:
            beat_id: Identifier of the beat to activate.

        Returns:
            The activated NarrativeBeat.

        Raises:
            ValueError: If the beat is not found, is in a terminal state,
                or its gating conditions are not satisfied.
        """
        with self._lock:
            resolved = self._resolve_beat(beat_id)
            if resolved is None:
                raise ValueError(f"Beat not found: {beat_id}")
            arc, beat = resolved

            if beat.status in (
                BeatStatus.COMPLETED,
                BeatStatus.SKIPPED,
                BeatStatus.CANCELLED,
                BeatStatus.FAILED,
            ):
                raise ValueError(
                    f"Cannot activate beat in terminal state {beat.status.value}: {beat_id}"
                )

            for flag_name in beat.required_flags:
                if self._flags.get(flag_name) is None:
                    raise ValueError(
                        f"Required flag not set: {flag_name}"
                    )

            if beat.gate_condition:
                if not self.check_gate(beat.gate_condition):
                    raise ValueError(
                        f"Gate condition not satisfied for beat: {beat_id}"
                    )

            beat.status = BeatStatus.ACTIVE
            beat.started_at = datetime.datetime.now()
            beat.completed_at = None
            arc.active_beat_id = beat.id

            self._emit_event(
                NarrativeEventKind.BEAT_ACTIVATED,
                arc_id=arc.id,
                beat_id=beat.id,
                choice_id=None,
                payload={"title": beat.title, "order": beat.order},
            )
            return beat

    def complete_beat(
        self,
        beat_id: str,
        choice_id: Optional[str] = None,
    ) -> NarrativeBeat:
        """Finalize a beat, applying flags and optionally a choice.

        Sets the beat status to ``COMPLETED``, applies ``set_flags_on_complete``,
        and, when a choice is supplied, records the choice and applies its
        consequences. The arc's active beat is cleared so the next beat can
        be activated explicitly.

        Args:
            beat_id: Identifier of the beat to complete.
            choice_id: Optional choice to record together with completion.

        Returns:
            The completed NarrativeBeat.

        Raises:
            ValueError: If the beat is not found, is in a terminal state,
                or the supplied choice is invalid for the beat.
        """
        with self._lock:
            resolved = self._resolve_beat(beat_id)
            if resolved is None:
                raise ValueError(f"Beat not found: {beat_id}")
            arc, beat = resolved

            if beat.status in (
                BeatStatus.COMPLETED,
                BeatStatus.SKIPPED,
                BeatStatus.CANCELLED,
                BeatStatus.FAILED,
            ):
                raise ValueError(
                    f"Cannot complete beat in terminal state {beat.status.value}: {beat_id}"
                )

            # Process the choice when supplied and not already recorded.
            if choice_id is not None and self._beat_choices.get(beat_id) != choice_id:
                choice = self._find_choice(beat, choice_id)
                if choice is None:
                    raise ValueError(
                        f"Choice {choice_id} not found on beat {beat_id}"
                    )
                self._apply_choice(arc, beat, choice)

            beat.status = BeatStatus.COMPLETED
            beat.completed_at = datetime.datetime.now()

            # Apply completion flags.
            for flag_name, flag_value in beat.set_flags_on_complete.items():
                self._set_flag_internal(flag_name, flag_value, scope="global")

            if arc.active_beat_id == beat.id:
                arc.active_beat_id = None

            self._emit_event(
                NarrativeEventKind.BEAT_COMPLETED,
                arc_id=arc.id,
                beat_id=beat.id,
                choice_id=choice_id,
                payload={"title": beat.title},
            )
            return beat

    def skip_beat(self, beat_id: str) -> NarrativeBeat:
        """Mark a beat as skipped without applying completion flags.

        Raises:
            ValueError: If the beat is not found or is in a terminal state.
        """
        with self._lock:
            resolved = self._resolve_beat(beat_id)
            if resolved is None:
                raise ValueError(f"Beat not found: {beat_id}")
            arc, beat = resolved

            if beat.status in (
                BeatStatus.COMPLETED,
                BeatStatus.SKIPPED,
                BeatStatus.CANCELLED,
                BeatStatus.FAILED,
            ):
                raise ValueError(
                    f"Cannot skip beat in terminal state {beat.status.value}: {beat_id}"
                )
            beat.status = BeatStatus.SKIPPED
            beat.completed_at = datetime.datetime.now()
            if arc.active_beat_id == beat.id:
                arc.active_beat_id = None
            return beat

    def cancel_beat(self, beat_id: str) -> NarrativeBeat:
        """Mark a beat as cancelled.

        Raises:
            ValueError: If the beat is not found or is in a terminal state.
        """
        with self._lock:
            resolved = self._resolve_beat(beat_id)
            if resolved is None:
                raise ValueError(f"Beat not found: {beat_id}")
            arc, beat = resolved

            if beat.status in (
                BeatStatus.COMPLETED,
                BeatStatus.SKIPPED,
                BeatStatus.CANCELLED,
                BeatStatus.FAILED,
            ):
                raise ValueError(
                    f"Cannot cancel beat in terminal state {beat.status.value}: {beat_id}"
                )
            beat.status = BeatStatus.CANCELLED
            beat.completed_at = datetime.datetime.now()
            if arc.active_beat_id == beat.id:
                arc.active_beat_id = None
            return beat

    # ------------------------------------------------------------------
    # Choice management
    # ------------------------------------------------------------------

    @staticmethod
    def _find_choice(beat: NarrativeBeat, choice_id: str) -> Optional[NarrativeChoice]:
        """Locate a choice on a beat by its identifier."""
        for choice in beat.choices:
            if choice.id == choice_id:
                return choice
        return None

    def _apply_choice(
        self,
        arc: StoryArc,
        beat: NarrativeBeat,
        choice: NarrativeChoice,
    ) -> None:
        """Apply a choice's consequence flags and record the selection."""
        self._beat_choices[beat.id] = choice.id
        for flag_name, flag_value in choice.consequences.items():
            self._set_flag_internal(flag_name, flag_value, scope="global")
        self._total_choices_made += 1
        self._emit_event(
            NarrativeEventKind.CHOICE_MADE,
            arc_id=arc.id,
            beat_id=beat.id,
            choice_id=choice.id,
            payload={"text": choice.text, "impact": choice.impact.value},
        )
        self._emit_event(
            NarrativeEventKind.BRANCH_TAKEN,
            arc_id=arc.id,
            beat_id=choice.next_beat_id,
            choice_id=choice.id,
            payload={"next_beat_id": choice.next_beat_id},
        )

    def present_choice(self, beat_id: str, choice_id: str) -> NarrativeChoice:
        """Mark a choice as presented to the player.

        Args:
            beat_id: Identifier of the beat exposing the choice.
            choice_id: Identifier of the choice being presented.

        Returns:
            The presented NarrativeChoice.

        Raises:
            ValueError: If the beat or choice is not found.
        """
        with self._lock:
            resolved = self._resolve_beat(beat_id)
            if resolved is None:
                raise ValueError(f"Beat not found: {beat_id}")
            arc, beat = resolved
            choice = self._find_choice(beat, choice_id)
            if choice is None:
                raise ValueError(
                    f"Choice {choice_id} not found on beat {beat_id}"
                )
            self._presented_choices[f"{beat_id}:{choice_id}"] = True
            self._total_choices_presented += 1
            self._emit_event(
                NarrativeEventKind.CHOICE_PRESENTED,
                arc_id=arc.id,
                beat_id=beat.id,
                choice_id=choice.id,
                payload={"text": choice.text},
            )
            return choice

    def make_choice(self, beat_id: str, choice_id: str) -> NarrativeChoice:
        """Record the player's choice and apply its consequences.

        Applies the choice's consequence flags and records the selection so
        that a subsequent :meth:`complete_beat` call does not reapply them.
        The beat is not finalized by this call.

        Args:
            beat_id: Identifier of the beat exposing the choice.
            choice_id: Identifier of the choice being made.

        Returns:
            The selected NarrativeChoice.

        Raises:
            ValueError: If the beat or choice is not found, or the choice
                was already recorded for the beat.
        """
        with self._lock:
            resolved = self._resolve_beat(beat_id)
            if resolved is None:
                raise ValueError(f"Beat not found: {beat_id}")
            arc, beat = resolved
            choice = self._find_choice(beat, choice_id)
            if choice is None:
                raise ValueError(
                    f"Choice {choice_id} not found on beat {beat_id}"
                )
            existing = self._beat_choices.get(beat_id)
            if existing is not None and existing != choice_id:
                raise ValueError(
                    f"A different choice was already made for beat {beat_id}"
                )
            if existing == choice_id:
                return choice
            self._apply_choice(arc, beat, choice)
            return choice

    # ------------------------------------------------------------------
    # Flag management
    # ------------------------------------------------------------------

    def _set_flag_internal(
        self,
        name: str,
        value: Any,
        scope: str = "global",
    ) -> StoryFlag:
        """Set a flag without acquiring the lock (internal use only)."""
        flag = StoryFlag(name=name, value=value, scope=scope)
        self._flags[name] = flag
        self._emit_event(
            NarrativeEventKind.FLAG_SET,
            arc_id=None,
            beat_id=None,
            choice_id=None,
            payload={"name": name, "value": value, "scope": scope},
        )
        return flag

    def set_flag(self, name: str, value: Any, scope: str = "global") -> StoryFlag:
        """Set a narrative flag, creating or overwriting it.

        Args:
            name: Unique name of the flag.
            value: Value to store on the flag.
            scope: Logical scope grouping for the flag.

        Returns:
            The stored StoryFlag.
        """
        with self._lock:
            return self._set_flag_internal(name, value, scope)

    def get_flag(self, name: str) -> Optional[StoryFlag]:
        """Retrieve a flag by name, or None if not set."""
        with self._lock:
            return self._flags.get(name)

    def clear_flag(self, name: str) -> bool:
        """Remove a flag by name.

        Returns:
            True if the flag was removed, False if it was not set.
        """
        with self._lock:
            if name not in self._flags:
                return False
            del self._flags[name]
            self._emit_event(
                NarrativeEventKind.FLAG_CLEARED,
                arc_id=None,
                beat_id=None,
                choice_id=None,
                payload={"name": name},
            )
            return True

    def list_flags(self) -> List[StoryFlag]:
        """Return a list of all currently set flags."""
        with self._lock:
            return list(self._flags.values())

    # ------------------------------------------------------------------
    # Gate evaluation
    # ------------------------------------------------------------------

    def check_gate(self, gate_condition: Optional[Dict[str, Any]]) -> bool:
        """Evaluate whether a gate condition is satisfied.

        A ``None`` or empty gate always passes. Supported gate types:

            * ``story_flag``    - the named flag exists with the expected value.
            * ``quest_complete``- placeholder; always returns True.
            * ``entity_state`` - placeholder; always returns True.
            * ``level_reached`` - placeholder; always returns True.
            * ``custom``       - invokes a registered handler, else True.

        Args:
            gate_condition: Gate dict containing ``gate_type`` and any
                parameters required by that gate type.

        Returns:
            True if the gate is satisfied (or absent), False otherwise.
        """
        with self._lock:
            if not gate_condition:
                return True

            gate_type = self._normalize_gate_type(gate_condition.get("gate_type", ""))

            if gate_type == GateType.STORY_FLAG.value:
                flag_name = gate_condition.get("flag_name")
                expected = gate_condition.get("expected_value")
                if not flag_name:
                    return True
                flag = self._flags.get(flag_name)
                if flag is None:
                    return False
                return flag.value == expected

            if gate_type == GateType.QUEST_COMPLETE.value:
                # No quest system link is wired here; behave permissively.
                gate_condition.get("quest_id")
                return True

            if gate_type == GateType.ENTITY_STATE.value:
                # No entity state system link is wired here; behave permissively.
                gate_condition.get("entity_id")
                gate_condition.get("required_state")
                return True

            if gate_type == GateType.LEVEL_REACHED.value:
                # No level system link is wired here; behave permissively.
                gate_condition.get("level_id")
                return True

            if gate_type == GateType.CUSTOM.value:
                handler_key = gate_condition.get("handler_key", "")
                handler = self._custom_gate_handlers.get(handler_key)
                if handler is None:
                    return True
                try:
                    return bool(handler(gate_condition))
                except Exception:
                    return False

            # Unknown gate types pass permissively.
            return True

    def register_custom_gate_handler(
        self,
        key: str,
        handler: Callable[[Dict[str, Any]], bool],
    ) -> None:
        """Register a handler invoked by ``custom`` gate conditions.

        Args:
            key: Lookup key matching the ``handler_key`` field of a custom
                gate condition dict.
            handler: Callable that receives the full gate condition dict
                and returns a boolean satisfaction result.
        """
        with self._lock:
            self._custom_gate_handlers[key] = handler

    # ------------------------------------------------------------------
    # Event management
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: Any,
        handler: Callable[[NarrativeEvent], None],
    ) -> None:
        """Subscribe a handler to narrative events.

        Args:
            kind: The ``NarrativeEventKind`` (or its string value) to
                subscribe to. Pass ``None`` to subscribe to all events.
            handler: Callable invoked with each matching NarrativeEvent.

        Raises:
            ValueError: If the handler limit (50) has been reached.
        """
        with self._lock:
            total = sum(len(v) for v in self._event_handlers.values())
            if total >= 50:
                raise ValueError("Event handler limit reached (50)")
            key = self._normalize_kind(kind)
            self._event_handlers.setdefault(key, []).append(handler)

    def _emit_event(
        self,
        kind: NarrativeEventKind,
        arc_id: Optional[str],
        beat_id: Optional[str],
        choice_id: Optional[str],
        payload: Optional[Dict[str, Any]] = None,
    ) -> NarrativeEvent:
        """Create, log, and dispatch a narrative event (internal use)."""
        event = NarrativeEvent(
            kind=kind,
            arc_id=arc_id,
            beat_id=beat_id,
            choice_id=choice_id,
            payload=payload or {},
        )
        self._events.append(event)
        if len(self._events) > 1000:
            # Evict the oldest entries beyond the 1000-event cap.
            del self._events[: len(self._events) - 1000]
        self._total_events_emitted += 1
        self._dispatch_event(event)
        return event

    def emit_event(
        self,
        kind: NarrativeEventKind,
        arc_id: Optional[str] = None,
        beat_id: Optional[str] = None,
        choice_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> NarrativeEvent:
        """Emit a narrative event to the log and subscribed handlers.

        Args:
            kind: The ``NarrativeEventKind`` to emit.
            arc_id: Optional associated arc identifier.
            beat_id: Optional associated beat identifier.
            choice_id: Optional associated choice identifier.
            payload: Optional payload describing the event.

        Returns:
            The created NarrativeEvent.
        """
        with self._lock:
            return self._emit_event(
                kind,
                arc_id=arc_id,
                beat_id=beat_id,
                choice_id=choice_id,
                payload=payload,
            )

    def list_events(self, limit: int = 100) -> List[NarrativeEvent]:
        """Return the most recent events, newest last.

        Args:
            limit: Maximum number of events to return.

        Returns:
            A list of NarrativeEvent records (up to ``limit``).
        """
        with self._lock:
            if limit <= 0:
                return []
            return list(self._events[-limit:])

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current director state."""
        with self._lock:
            stats = self._compute_stats()
            return {
                "total_arcs": stats["total_arcs"],
                "total_beats": stats["total_beats"],
                "total_flags": len(self._flags),
                "total_events": len(self._events),
                "total_handlers": sum(len(v) for v in self._event_handlers.values()),
                "stats": stats,
            }

    def get_snapshot(self) -> NarrativeDirectorSnapshot:
        """Capture an immutable snapshot of the director state."""
        with self._lock:
            stats = self._compute_stats()
            return NarrativeDirectorSnapshot(
                arc_count=stats["total_arcs"],
                active_arc_count=stats["active_arcs"],
                beat_count=stats["total_beats"],
                active_beat_count=stats["active_beats"],
                flag_count=len(self._flags),
                event_count=len(self._events),
                stats=stats,
                timestamp=datetime.datetime.now(),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all arcs, beats, flags, events, and handlers.

        Restores the director to its initial state, including the default
        seed narrative.
        """
        with self._lock:
            self._arcs.clear()
            self._beat_index.clear()
            self._beat_to_arc.clear()
            self._flags.clear()
            self._events.clear()
            self._event_handlers.clear()
            self._custom_gate_handlers.clear()
            self._beat_choices.clear()
            self._presented_choices.clear()
            self._total_events_emitted = 0
            self._total_choices_presented = 0
            self._total_choices_made = 0
            self._seed_default_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Populate the default narrative arc and its beats."""
        arc = StoryArc(
            name="The Awakening",
            description=(
                "The opening arc where the protagonist discovers their "
                "calling, meets a mentor, and chooses a path forward."
            ),
            status=ArcStatus.DRAFT,
            priority=0,
        )

        beat1 = NarrativeBeat(
            arc_id=arc.id,
            order=1,
            beat_type=BeatType.NARRATIVE,
            title="Prologue: The Calling",
            description=(
                "The protagonist receives a mysterious summons that "
                "sets the journey in motion."
            ),
            set_flags_on_complete={"prologue_complete": True},
        )

        beat2 = NarrativeBeat(
            arc_id=arc.id,
            order=2,
            beat_type=BeatType.DIALOGUE,
            title="The Mentor's Tale",
            description=(
                "An aged mentor recounts the history of the land and "
                "the burden the protagonist must carry."
            ),
            gate_condition={
                "gate_type": GateType.STORY_FLAG.value,
                "flag_name": "prologue_complete",
                "expected_value": True,
            },
            set_flags_on_complete={"mentor_spoken": True},
        )

        beat3 = NarrativeBeat(
            arc_id=arc.id,
            order=3,
            beat_type=BeatType.CHOICE,
            title="The Crossroads",
            description=(
                "Two paths stretch outward from the crossroads. The "
                "protagonist must commit to one."
            ),
            gate_condition={
                "gate_type": GateType.STORY_FLAG.value,
                "flag_name": "mentor_spoken",
                "expected_value": True,
            },
            choices=[
                NarrativeChoice(
                    text="Take the mountain path",
                    consequences={"path": "mountain"},
                    impact=ChoiceImpact.MODERATE,
                ),
                NarrativeChoice(
                    text="Take the river path",
                    consequences={"path": "river"},
                    impact=ChoiceImpact.MODERATE,
                ),
            ],
        )

        arc.beats = [beat1, beat2, beat3]
        arc.start_beat_id = beat1.id

        self._arcs[arc.id] = arc
        for beat in arc.beats:
            self._index_beat(arc, beat)


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_narrative_director() -> NarrativeDirectorEngine:
    """Return the singleton NarrativeDirectorEngine instance."""
    return NarrativeDirectorEngine.get_instance()
