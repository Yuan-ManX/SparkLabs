"""
SparkLabs Agent - Narrative Memory Engine
=========================================

Episodic narrative memory and character-arc tracking for AI agents operating
inside the SparkLabs AI-native game engine.

This module implements a narrative memory engine that stores episodic
memories of story events -- plot points, character interactions, world
changes, twists, revelations -- and tracks how characters evolve across the
course of a narrative. It provides rich retrieval by story arc, character,
chronology, and dramatic significance so that downstream storytelling agents
can recall what has happened, to whom, and why it mattered.

Core concepts
-------------

1. **Story Events** -- ``StoryEvent`` records are the atomic unit of
   narrative memory. Each event captures a title, description, type
   (PLOT_POINT, CONFLICT, TWIST, ...), the story arc it belongs to, the
   characters that participated, a narrative timestamp, a dramatic weight
   in [0, 1], an emotional tone, and arbitrary tags. Events are the raw
   material from which timelines and character journeys are constructed.

2. **Character Arcs** -- ``CharacterArc`` tracks how a single character
   evolves through the narrative. Each arc records the character's role
   (PROTAGONIST, ANTAGONIST, ...), current stage (SETUP -> RISING_ACTION
   -> CLIMAX -> FALLING_ACTION -> RESOLUTION -> EPILOGUE), status
   (DORMANT, ACTIVE, PAUSED, COMPLETED, ABANDONED), a prose summary, the
   key events that shaped the arc, a full stage-transition history, and a
   relationship map linking to other characters.

3. **Plot Threads** -- ``PlotThread`` represents an open narrative
   question or ongoing storyline (e.g. "The Ancient Prophecy"). Threads
   link related events across arcs, carry a priority, and move through
   OPEN -> RESOLVED / DROPPED states.

4. **Timelines** -- ``NarrativeTimeline`` orders the events of a story
   arc chronologically by narrative time, providing the backbone for
   chronological retrieval and narrative-density analysis.

5. **Narrative Density** -- ``compute_narrative_density`` aggregates
   events per arc stage, dramatic-weight distribution, and emotional-tone
   distribution so callers can understand the shape and pacing of a
   story.

Architecture
------------

NarrativeMemoryEngine (Singleton, double-checked locking with threading.RLock)
  |-- StoryEvent                -- a single recorded narrative story event
  |-- CharacterArc              -- a character's evolving arc through the story
  |-- PlotThread                -- an open or resolved narrative storyline
  |-- NarrativeTimeline         -- a chronologically ordered event sequence
  |-- NarrativeMemoryStats      -- aggregate engine statistics
  |-- NarrativeMemorySnapshot   -- complete engine state snapshot
  |-- NarrativeMemoryEvent      -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the engine
is safe to call from multiple agent threads. Bounded in-memory stores use
FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_STORY_EVENTS: int = 5000
_MAX_CHARACTERS: int = 1000
_MAX_PLOT_THREADS: int = 500
_MAX_TIMELINES: int = 500
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Return a 16-character hexadecimal identifier."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive range [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key
    returned by iteration is the oldest. This implements FIFO eviction.
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

class StoryEventType(Enum):
    """Classification of a story event by its narrative function."""
    PLOT_POINT = "plot_point"
    CHARACTER_INTRODUCTION = "character_introduction"
    CONFLICT = "conflict"
    RESOLUTION = "resolution"
    TWIST = "twist"
    REVELATION = "revelation"
    INTERACTION = "interaction"
    WORLD_EVENT = "world_event"
    FLASHBACK = "flashback"
    FORESHADOW = "foreshadow"


class ArcStage(Enum):
    """Stage of a character's arc within the classic dramatic structure."""
    SETUP = "setup"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"
    EPILOGUE = "epilogue"


class ArcStatus(Enum):
    """Lifecycle status of a character arc."""
    DORMANT = "dormant"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class CharacterRole(Enum):
    """Dramatic role a character plays in the narrative."""
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MENTOR = "mentor"
    FOIL = "foil"
    CATALYST = "catalyst"


class NarrativeTense(Enum):
    """Temporal perspective from which a story event is recounted."""
    PAST = "past"
    PRESENT = "present"
    FUTURE_CONDITIONAL = "future_conditional"


class PlotThreadStatus(Enum):
    """Lifecycle status of a plot thread."""
    OPEN = "open"
    RESOLVED = "resolved"
    DROPPED = "dropped"


class NarrativeEventKind(Enum):
    """Observable lifecycle events emitted by the narrative memory engine."""
    STORY_EVENT_RECORDED = "story_event_recorded"
    STORY_EVENT_RECALLED = "story_event_recalled"
    ARC_CREATED = "arc_created"
    ARC_UPDATED = "arc_updated"
    ARC_STAGE_CHANGED = "arc_stage_changed"
    CHARACTER_ADDED = "character_added"
    CHARACTER_REMOVED = "character_removed"
    PLOT_THREAD_LINKED = "plot_thread_linked"
    TIMELINE_REORDERED = "timeline_reordered"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class StoryEvent:
    """A single recorded narrative story event.

    Story events are the atomic unit of narrative memory. Each event
    captures what happened, what kind of narrative beat it represents,
    which characters participated, where and when it occurred in
    narrative time, how dramatically significant it is, and its
    emotional tone.
    """

    event_id: str
    title: str
    description: str
    event_type: StoryEventType
    story_arc_id: str = ""
    participant_ids: List[str] = field(default_factory=list)
    location: str = ""
    timestamp: str = ""
    dramatic_weight: float = 0.5
    emotional_tone: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this story event to a JSON-friendly dictionary.

        Enum fields are serialized via ``.value`` and nested lists/dicts
        are copied so the returned dict is safe to mutate.
        """
        return {
            "event_id": self.event_id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type.value,
            "story_arc_id": self.story_arc_id,
            "participant_ids": list(self.participant_ids),
            "location": self.location,
            "timestamp": self.timestamp,
            "dramatic_weight": self.dramatic_weight,
            "emotional_tone": self.emotional_tone,
            "tags": list(self.tags),
            "metadata": dict(self.metadata) if self.metadata else {},
            "created_at": self.created_at,
        }


@dataclass
class CharacterArc:
    """A character's evolving arc through the narrative.

    Each arc tracks a character's role, current dramatic stage, status,
    a prose summary of their journey, the key events that shaped them,
    a full stage-transition history, and a relationship map to other
    characters in the story.
    """

    arc_id: str
    character_id: str
    character_name: str
    role: CharacterRole
    current_stage: ArcStage
    status: ArcStatus
    arc_summary: str = ""
    key_events: List[str] = field(default_factory=list)
    stage_history: List[Dict[str, Any]] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)
    started_at: str = field(default_factory=_now)
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this character arc to a JSON-friendly dictionary.

        Enum fields are serialized via ``.value``. Nested lists and dicts
        are deep-copied so the returned dict is safe to mutate.
        """
        return {
            "arc_id": self.arc_id,
            "character_id": self.character_id,
            "character_name": self.character_name,
            "role": self.role.value,
            "current_stage": self.current_stage.value,
            "status": self.status.value,
            "arc_summary": self.arc_summary,
            "key_events": list(self.key_events),
            "stage_history": [dict(entry) for entry in self.stage_history],
            "relationships": dict(self.relationships),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class PlotThread:
    """An open or resolved narrative storyline spanning multiple events.

    A plot thread represents an ongoing narrative question or subplot
    (e.g. "The Ancient Prophecy") that links related events across one
    or more character arcs. Threads carry a priority and move through
    OPEN -> RESOLVED / DROPPED states.
    """

    thread_id: str
    name: str
    description: str = ""
    related_arcs: List[str] = field(default_factory=list)
    status: PlotThreadStatus = PlotThreadStatus.OPEN
    priority: int = 3
    linked_events: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    resolved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plot thread to a JSON-friendly dictionary."""
        return {
            "thread_id": self.thread_id,
            "name": self.name,
            "description": self.description,
            "related_arcs": list(self.related_arcs),
            "status": self.status.value,
            "priority": self.priority,
            "linked_events": list(self.linked_events),
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }


@dataclass
class NarrativeTimeline:
    """A chronologically ordered sequence of events for a story arc.

    The timeline orders the events of a story arc by their narrative
    timestamp, providing the backbone for chronological retrieval and
    narrative-density analysis.
    """

    timeline_id: str
    arc_id: str
    ordered_events: List[str] = field(default_factory=list)
    time_range_start: str = ""
    time_range_end: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this timeline to a JSON-friendly dictionary."""
        return {
            "timeline_id": self.timeline_id,
            "arc_id": self.arc_id,
            "ordered_events": list(self.ordered_events),
            "time_range_start": self.time_range_start,
            "time_range_end": self.time_range_end,
        }


@dataclass
class NarrativeMemoryStats:
    """Aggregate statistics about the narrative memory engine."""

    total_events: int = 0
    total_arcs: int = 0
    total_threads: int = 0
    total_characters: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    arcs_by_status: Dict[str, int] = field(default_factory=dict)
    avg_dramatic_weight: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_events": self.total_events,
            "total_arcs": self.total_arcs,
            "total_threads": self.total_threads,
            "total_characters": self.total_characters,
            "events_by_type": dict(self.events_by_type),
            "arcs_by_status": dict(self.arcs_by_status),
            "avg_dramatic_weight": self.avg_dramatic_weight,
        }


@dataclass
class NarrativeMemorySnapshot:
    """A point-in-time snapshot of the entire narrative memory engine state."""

    initialized: bool = False
    events: List[StoryEvent] = field(default_factory=list)
    arcs: List[CharacterArc] = field(default_factory=list)
    threads: List[PlotThread] = field(default_factory=list)
    characters: List[CharacterArc] = field(default_factory=list)
    timelines: List[NarrativeTimeline] = field(default_factory=list)
    stats: NarrativeMemoryStats = field(default_factory=NarrativeMemoryStats)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "events": [e.to_dict() for e in self.events],
            "arcs": [a.to_dict() for a in self.arcs],
            "threads": [t.to_dict() for t in self.threads],
            "characters": [c.to_dict() for c in self.characters],
            "timelines": [tl.to_dict() for tl in self.timelines],
            "stats": self.stats.to_dict(),
        }


@dataclass
class NarrativeMemoryEvent:
    """An observable lifecycle event emitted by the narrative memory engine."""

    event_id: str = field(default_factory=_new_id)
    kind: NarrativeEventKind = NarrativeEventKind.STORY_EVENT_RECORDED
    timestamp: str = field(default_factory=_now)
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
# Narrative Memory Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------

class NarrativeMemoryEngine:
    """Singleton engine that stores episodic narrative memories and tracks
    character arcs.

    The engine records story events (plot points, interactions, twists),
    maintains character arcs that track how each character evolves through
    the narrative, manages plot threads that link related events across
    arcs, and builds chronological timelines for story arcs. It provides
    rich retrieval by character, arc, emotion, and dramatic significance.

    The engine is a process-wide singleton accessed via
    :meth:`get_instance` or the module-level :func:`get_narrative_memory`
    helper. All public methods are thread-safe, guarded by a reentrant
    lock. In-memory stores are bounded by capacity constants and use FIFO
    eviction so the engine never grows without limit.

    Usage::

        engine = get_narrative_memory()
        engine.register_character("hero", "Lyra", CharacterRole.PROTAGONIST,
                                  arc_summary="A young warrior discovering her powers")
        event = engine.record_event(
            title="The Calling",
            description="Lyra discovers her hidden powers.",
            event_type=StoryEventType.CHARACTER_INTRODUCTION,
            story_arc_id="main_arc",
            participant_ids=["hero"],
            dramatic_weight=0.7,
            emotional_tone="hopeful",
        )
        engine.link_event_to_character(event.event_id, "hero")
        journey = engine.get_character_journey("hero")
    """

    _instance: Optional["NarrativeMemoryEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton construction (double-checked locking)
    # ------------------------------------------------------------------

    def __new__(cls) -> "NarrativeMemoryEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "NarrativeMemoryEngine":
        """Return the singleton NarrativeMemoryEngine instance.

        Uses double-checked locking so that calls after initialization
        take the fast path without acquiring the lock. Does NOT reset
        ``_initialized``; only constructs the singleton if it is absent.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if self._initialized:
            return
        with self._lock:
            # Second check inside the lock to guard against concurrent
            # construction.
            if self._initialized:
                return

            # Core storage keyed by entity id.
            self._events_store: Dict[str, StoryEvent] = {}
            self._characters: Dict[str, CharacterArc] = {}
            self._plot_threads: Dict[str, PlotThread] = {}
            self._timelines: Dict[str, NarrativeTimeline] = {}

            # Observable event log (chronological append-only list).
            self._events: List[NarrativeMemoryEvent] = []

            # Monotonic counters for diagnostics.
            self._event_counter: int = 0
            self._character_counter: int = 0
            self._thread_counter: int = 0
            self._timeline_counter: int = 0
            self._audit_event_counter: int = 0

            # Mark initialization complete, then seed baseline data.
            # _seed_data is called at the END of init as required.
            self._initialized: bool = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline narrative content.

        Seeds three characters (hero Lyra, villain Malachar, mentor
        Eldwin), five story events spanning the opening of the narrative,
        one plot thread ("The Ancient Prophecy") linked to key events,
        and one timeline for the main story arc.
        """
        now = _now()

        # --- Characters ------------------------------------------------
        # Three archetypal characters at different stages of their arcs.
        character_specs = [
            (
                "hero",
                "Lyra",
                CharacterRole.PROTAGONIST,
                ArcStage.RISING_ACTION,
                ArcStatus.ACTIVE,
                "A young warrior discovering her powers",
            ),
            (
                "villain",
                "Malachar",
                CharacterRole.ANTAGONIST,
                ArcStage.SETUP,
                ArcStatus.ACTIVE,
                "An ancient sorcerer seeking revenge",
            ),
            (
                "mentor",
                "Eldwin",
                CharacterRole.MENTOR,
                ArcStage.SETUP,
                ArcStatus.ACTIVE,
                "An old sage guiding Lyra",
            ),
        ]
        for (char_id, name, role, stage, status, summary) in character_specs:
            arc = CharacterArc(
                arc_id=_new_id(),
                character_id=char_id,
                character_name=name,
                role=role,
                current_stage=stage,
                status=status,
                arc_summary=summary,
                started_at=now,
                metadata={"seed": True},
            )
            # Record the initial stage in the stage history.
            arc.stage_history.append({
                "stage": stage.value,
                "event_id": None,
                "timestamp": now,
            })
            self._characters[char_id] = arc
            self._character_counter += 1
            self._record_event(
                NarrativeEventKind.CHARACTER_ADDED,
                {
                    "character_id": char_id,
                    "character_name": name,
                    "role": role.value,
                    "stage": stage.value,
                },
            )
            self._record_event(
                NarrativeEventKind.ARC_CREATED,
                {
                    "arc_id": arc.arc_id,
                    "character_id": char_id,
                    "character_name": name,
                    "role": role.value,
                },
            )

        # Establish initial relationships between seeded characters.
        hero_arc = self._characters.get("hero")
        villain_arc = self._characters.get("villain")
        mentor_arc = self._characters.get("mentor")
        if hero_arc is not None:
            hero_arc.relationships["villain"] = "Adversary seeking to destroy her"
            hero_arc.relationships["mentor"] = "Trusted guide and father figure"
        if villain_arc is not None:
            villain_arc.relationships["hero"] = "The prophesied one who must fall"
            villain_arc.relationships["mentor"] = "Former apprentice turned enemy"
        if mentor_arc is not None:
            mentor_arc.relationships["hero"] = "Protégé carrying the hope of the realm"
            mentor_arc.relationships["villain"] = "A former student lost to darkness"

        # --- Story Events ----------------------------------------------
        # Five events spanning the opening of the narrative. Each carries
        # a narrative timestamp for chronological ordering, a dramatic
        # weight, and an emotional tone.
        main_arc_id = "arc_main"

        event_specs = [
            (
                "The Calling",
                "Lyra hears a mysterious voice calling her toward the "
                "ancient ruins, where she discovers a glowing artifact "
                "that resonates with her hidden lineage.",
                StoryEventType.CHARACTER_INTRODUCTION,
                main_arc_id,
                ["hero"],
                "Ancient Ruins",
                "0001-01-01T08:00",
                0.7,
                "hopeful",
                ["calling", "lineage", "artifact"],
            ),
            (
                "First Encounter",
                "Lyra and Malachar meet for the first time at the "
                "crossroads. Words are exchanged and a dark threat is "
                "made, setting the stage for their enduring conflict.",
                StoryEventType.INTERACTION,
                main_arc_id,
                ["hero", "villain"],
                "Crossroads",
                "0001-01-02T14:00",
                0.6,
                "tense",
                ["encounter", "threat", "conflict"],
            ),
            (
                "Mentor's Guidance",
                "Eldwin finds Lyra struggling to control her awakening "
                "powers and offers to train her, revealing fragments of "
                "the ancient prophecy that binds them all.",
                StoryEventType.INTERACTION,
                main_arc_id,
                ["hero", "mentor"],
                "Hidden Grove",
                "0001-01-03T10:00",
                0.5,
                "wise",
                ["training", "prophecy", "guidance"],
            ),
            (
                "The Betrayal",
                "Malachar reveals that Eldwin was once his mentor and that "
                "the sage has been concealing the true cost of the prophecy. "
                "Trust shatters as long-held secrets come to light.",
                StoryEventType.TWIST,
                main_arc_id,
                ["villain", "mentor"],
                "Sanctum",
                "0001-01-05T19:00",
                0.9,
                "shocking",
                ["betrayal", "secret", "revelation"],
            ),
            (
                "Awakening Power",
                "Driven by the revelations, Lyra unleashes a surge of "
                "power she did not know she possessed, turning the tide "
                "of battle and embracing her role as the prophesied one.",
                StoryEventType.REVELATION,
                main_arc_id,
                ["hero"],
                "Battlefield",
                "0001-01-07T12:00",
                0.8,
                "triumphant",
                ["power", "awakening", "destiny"],
            ),
        ]

        seeded_event_ids: List[str] = []
        for (title, desc, etype, arc_id, participants, location,
             narrative_ts, weight, tone, tags) in event_specs:
            event = StoryEvent(
                event_id=_new_id(),
                title=title,
                description=desc,
                event_type=etype,
                story_arc_id=arc_id,
                participant_ids=list(participants),
                location=location,
                timestamp=narrative_ts,
                dramatic_weight=_clamp(weight, 0.0, 1.0),
                emotional_tone=tone,
                tags=list(tags),
                created_at=now,
                metadata={"seed": True},
            )
            self._events_store[event.event_id] = event
            self._event_counter += 1
            seeded_event_ids.append(event.event_id)

            # Link the event to each participating character's key events.
            for pid in participants:
                char_arc = self._characters.get(pid)
                if char_arc is not None and event.event_id not in char_arc.key_events:
                    char_arc.key_events.append(event.event_id)

            self._record_event(
                NarrativeEventKind.STORY_EVENT_RECORDED,
                {
                    "event_id": event.event_id,
                    "title": event.title,
                    "event_type": event.event_type.value,
                    "story_arc_id": event.story_arc_id,
                    "dramatic_weight": event.dramatic_weight,
                    "emotional_tone": event.emotional_tone,
                },
            )

        _evict_fifo_dict(self._events_store, _MAX_STORY_EVENTS)

        # --- Plot Thread: The Ancient Prophecy -------------------------
        # Linked to events 1 (The Calling), 4 (The Betrayal), and
        # 5 (Awakening Power) -- the three beats most tied to the prophecy.
        prophecy_thread = PlotThread(
            thread_id=_new_id(),
            name="The Ancient Prophecy",
            description=(
                "An ancient prophecy foretells the rise of a warrior "
                "who will either save or destroy the realm. The true "
                "cost of fulfilling it has been hidden for generations."
            ),
            related_arcs=[main_arc_id],
            status=PlotThreadStatus.OPEN,
            priority=5,
            linked_events=[
                seeded_event_ids[0],
                seeded_event_ids[3],
                seeded_event_ids[4],
            ],
            created_at=now,
        )
        prophecy_thread.metadata = {"seed": True}
        self._plot_threads[prophecy_thread.thread_id] = prophecy_thread
        self._thread_counter += 1
        self._record_event(
            NarrativeEventKind.PLOT_THREAD_LINKED,
            {
                "thread_id": prophecy_thread.thread_id,
                "name": prophecy_thread.name,
                "linked_event_count": len(prophecy_thread.linked_events),
                "priority": prophecy_thread.priority,
            },
        )
        _evict_fifo_dict(self._plot_threads, _MAX_PLOT_THREADS)

        # --- Timeline for the main arc ---------------------------------
        # Order all main-arc events chronologically by narrative timestamp.
        timeline = self._build_timeline_internal(main_arc_id)
        self._timelines[main_arc_id] = timeline
        self._timeline_counter += 1
        _evict_fifo_dict(self._timelines, _MAX_TIMELINES)

        # Enforce audit event capacity after seeding.
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_event(
        self, kind: NarrativeEventKind, payload: Dict[str, Any]
    ) -> None:
        """Record an observable narrative memory event.

        Assumes the caller already holds ``self._lock``. The event log
        is bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = NarrativeMemoryEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        self._audit_event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _build_timeline_internal(
        self, story_arc_id: str
    ) -> NarrativeTimeline:
        """Construct a chronological timeline for a story arc.

        Filters all events belonging to ``story_arc_id`` and orders them
        by their narrative ``timestamp`` field (ascending). Events with
        an empty timestamp are sorted to the end. Assumes the caller
        already holds ``self._lock``.
        """
        arc_events: List[StoryEvent] = [
            e for e in self._events_store.values()
            if e.story_arc_id == story_arc_id
        ]
        # Sort by narrative timestamp; empty timestamps go last.
        arc_events.sort(
            key=lambda e: (e.timestamp == "", e.timestamp)
        )
        ordered_ids = [e.event_id for e in arc_events]
        if arc_events:
            time_start = arc_events[0].timestamp
            time_end = arc_events[-1].timestamp
        else:
            time_start = ""
            time_end = ""
        return NarrativeTimeline(
            timeline_id=_new_id(),
            arc_id=story_arc_id,
            ordered_events=ordered_ids,
            time_range_start=time_start,
            time_range_end=time_end,
        )

    # ------------------------------------------------------------------
    # Character arc management
    # ------------------------------------------------------------------

    def register_character(
        self,
        character_id: str,
        character_name: str,
        role: CharacterRole,
        arc_summary: str = "",
    ) -> CharacterArc:
        """Register a new character and create their character arc.

        If a character with the given ``character_id`` already exists,
        the existing arc is returned unchanged. New characters start in
        the SETUP stage with an ACTIVE status.

        Args:
            character_id: Unique identifier for the character.
            character_name: Display name of the character.
            role: The :class:`CharacterRole` the character plays.
            arc_summary: Optional prose summary of the character's arc.

        Returns:
            The :class:`CharacterArc` for the character.
        """
        with self._lock:
            existing = self._characters.get(character_id)
            if existing is not None:
                return existing

            now = _now()
            arc = CharacterArc(
                arc_id=_new_id(),
                character_id=character_id,
                character_name=character_name,
                role=role,
                current_stage=ArcStage.SETUP,
                status=ArcStatus.ACTIVE,
                arc_summary=arc_summary,
                started_at=now,
            )
            # Record the initial stage in the stage history.
            arc.stage_history.append({
                "stage": ArcStage.SETUP.value,
                "event_id": None,
                "timestamp": now,
            })
            self._characters[character_id] = arc
            self._character_counter += 1
            _evict_fifo_dict(self._characters, _MAX_CHARACTERS)

            self._record_event(
                NarrativeEventKind.CHARACTER_ADDED,
                {
                    "character_id": character_id,
                    "character_name": character_name,
                    "role": role.value,
                },
            )
            self._record_event(
                NarrativeEventKind.ARC_CREATED,
                {
                    "arc_id": arc.arc_id,
                    "character_id": character_id,
                    "character_name": character_name,
                    "role": role.value,
                },
            )
            return arc

    def get_character(self, character_id: str) -> Optional[CharacterArc]:
        """Return the character arc for ``character_id``, or None if absent."""
        with self._lock:
            return self._characters.get(character_id)

    def list_characters(
        self,
        role: Optional[CharacterRole] = None,
        status: Optional[ArcStatus] = None,
    ) -> List[CharacterArc]:
        """Return character arcs, optionally filtered by role and/or status.

        Args:
            role: When provided, only characters with this role are returned.
            status: When provided, only characters with this status are
                returned.

        Returns:
            A list of matching :class:`CharacterArc` objects in insertion
            order.
        """
        with self._lock:
            results: List[CharacterArc] = []
            for arc in self._characters.values():
                if role is not None and arc.role != role:
                    continue
                if status is not None and arc.status != status:
                    continue
                results.append(arc)
            return results

    def update_character(
        self, character_id: str, **kwargs: Any
    ) -> Optional[CharacterArc]:
        """Update one or more fields of a character arc.

        Only known ``CharacterArc`` fields are applied; unknown keys are
        ignored. Enum-valued fields accept either an enum member or a
        string value. If ``current_stage`` is updated, a stage-history
        entry is recorded automatically.

        Args:
            character_id: Identifier of the character to update.
            **kwargs: Field names and values to set on the arc.

        Returns:
            The updated :class:`CharacterArc`, or ``None`` if the
            character was not found.
        """
        with self._lock:
            arc = self._characters.get(character_id)
            if arc is None:
                return None

            known_fields = {
                "character_name", "role", "current_stage", "status",
                "arc_summary", "key_events", "stage_history",
                "relationships", "completed_at", "metadata",
            }
            stage_changed = False
            new_stage: Optional[ArcStage] = None
            for key, value in kwargs.items():
                if key not in known_fields:
                    continue
                if key == "role" and isinstance(value, str):
                    value = CharacterRole(value)
                if key == "current_stage" and isinstance(value, str):
                    value = ArcStage(value)
                if key == "status" and isinstance(value, str):
                    value = ArcStatus(value)
                if key in ("key_events",) and value is not None:
                    value = list(value)
                if key == "stage_history" and value is not None:
                    value = [dict(e) for e in value]
                if key == "relationships" and value is not None:
                    value = dict(value)
                if key == "metadata" and value is not None:
                    value = dict(value)
                if key == "current_stage":
                    stage_changed = True
                    new_stage = value  # type: ignore[assignment]
                setattr(arc, key, value)

            # If the stage was changed, append a stage-history entry so
            # the transition is preserved.
            if stage_changed and new_stage is not None:
                arc.stage_history.append({
                    "stage": new_stage.value,
                    "event_id": None,
                    "timestamp": _now(),
                })

            self._record_event(
                NarrativeEventKind.ARC_UPDATED,
                {
                    "character_id": character_id,
                    "arc_id": arc.arc_id,
                    "stage_changed": stage_changed,
                },
            )
            return arc

    def advance_arc_stage(
        self,
        character_id: str,
        new_stage: ArcStage,
        triggering_event_id: Optional[str] = None,
    ) -> Optional[CharacterArc]:
        """Advance a character to a new arc stage, recording the transition.

        The character's ``current_stage`` is updated and a new entry is
        appended to ``stage_history`` capturing the new stage, the
        triggering event (if any), and the transition timestamp. If the
        new stage is RESOLUTION or EPILOGUE, the arc status is
        automatically set to COMPLETED and ``completed_at`` is recorded.

        Args:
            character_id: Identifier of the character whose stage to advance.
            new_stage: The :class:`ArcStage` to move the character to.
            triggering_event_id: Optional event id that triggered the
                stage transition.

        Returns:
            The updated :class:`CharacterArc`, or ``None`` if the
            character was not found.
        """
        with self._lock:
            arc = self._characters.get(character_id)
            if arc is None:
                return None

            old_stage = arc.current_stage
            now = _now()
            arc.current_stage = new_stage
            arc.stage_history.append({
                "stage": new_stage.value,
                "event_id": triggering_event_id,
                "timestamp": now,
            })

            # Automatically complete the arc when the character reaches
            # the resolution or epilogue stage.
            if new_stage in (ArcStage.RESOLUTION, ArcStage.EPILOGUE):
                arc.status = ArcStatus.COMPLETED
                arc.completed_at = now

            self._record_event(
                NarrativeEventKind.ARC_STAGE_CHANGED,
                {
                    "character_id": character_id,
                    "arc_id": arc.arc_id,
                    "old_stage": old_stage.value,
                    "new_stage": new_stage.value,
                    "triggering_event_id": triggering_event_id,
                },
            )
            return arc

    # ------------------------------------------------------------------
    # Story event recording and lookup
    # ------------------------------------------------------------------

    def record_event(
        self,
        title: str,
        description: str,
        event_type: StoryEventType,
        story_arc_id: str = "",
        participant_ids: Optional[List[str]] = None,
        location: str = "",
        timestamp: Optional[str] = None,
        dramatic_weight: float = 0.5,
        emotional_tone: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoryEvent:
        """Record a narrative story event.

        The event is stored in the engine and automatically linked to
        each participating character's ``key_events`` list. If
        ``timestamp`` is omitted, the wall-clock creation time is used
        as the narrative timestamp.

        Args:
            title: Short title of the story event.
            description: Free-form description of what happened.
            event_type: The :class:`StoryEventType` categorisation.
            story_arc_id: Identifier of the story arc this event belongs to.
            participant_ids: Character ids involved in the event.
            location: Where the event occurred in the narrative world.
            timestamp: Narrative-world timestamp string. When omitted,
                the wall-clock creation time is used.
            dramatic_weight: Dramatic significance in [0.0, 1.0] (clamped).
                Higher values indicate more impactful events.
            emotional_tone: Emotional flavour of the event (e.g. "tense").
            tags: Optional list of free-form tags for retrieval.
            metadata: Optional arbitrary metadata to attach.

        Returns:
            The newly created :class:`StoryEvent`.
        """
        with self._lock:
            now = _now()
            event = StoryEvent(
                event_id=_new_id(),
                title=title,
                description=description,
                event_type=event_type,
                story_arc_id=story_arc_id,
                participant_ids=list(participant_ids) if participant_ids else [],
                location=location,
                timestamp=timestamp or now,
                dramatic_weight=_clamp(float(dramatic_weight), 0.0, 1.0),
                emotional_tone=emotional_tone,
                tags=list(tags) if tags else [],
                created_at=now,
                metadata=dict(metadata) if metadata else {},
            )
            self._events_store[event.event_id] = event
            self._event_counter += 1
            _evict_fifo_dict(self._events_store, _MAX_STORY_EVENTS)

            # Link the event to each participating character's key events.
            for pid in event.participant_ids:
                char_arc = self._characters.get(pid)
                if char_arc is not None and event.event_id not in char_arc.key_events:
                    char_arc.key_events.append(event.event_id)

            self._record_event(
                NarrativeEventKind.STORY_EVENT_RECORDED,
                {
                    "event_id": event.event_id,
                    "title": event.title,
                    "event_type": event.event_type.value,
                    "story_arc_id": event.story_arc_id,
                    "dramatic_weight": event.dramatic_weight,
                    "emotional_tone": event.emotional_tone,
                },
            )
            return event

    def get_event(self, event_id: str) -> Optional[StoryEvent]:
        """Return a single story event by id, or None if not found."""
        with self._lock:
            return self._events_store.get(event_id)

    def list_story_events(
        self,
        story_arc_id: Optional[str] = None,
        event_type: Optional[StoryEventType] = None,
        character_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[StoryEvent]:
        """List story events, optionally filtered by arc, type, and character.

        Args:
            story_arc_id: When provided, only events belonging to this
                story arc are returned.
            event_type: When provided, only events of this type are
                returned.
            character_id: When provided, only events in which this
                character participated are returned.
            limit: Maximum number of events to return. ``0`` returns an
                empty list.

        Returns:
            A list of matching :class:`StoryEvent` objects in insertion
            order, truncated to ``limit``.
        """
        with self._lock:
            n = max(0, int(limit))
            results: List[StoryEvent] = []
            for event in self._events_store.values():
                if story_arc_id is not None and event.story_arc_id != story_arc_id:
                    continue
                if event_type is not None and event.event_type != event_type:
                    continue
                if character_id is not None and character_id not in event.participant_ids:
                    continue
                results.append(event)
                if n > 0 and len(results) >= n:
                    break
            return results

    def recall_narrative(
        self,
        character_id: Optional[str] = None,
        story_arc_id: Optional[str] = None,
        emotion: Optional[str] = None,
        limit: int = 10,
    ) -> List[StoryEvent]:
        """Retrieve story events by narrative relevance.

        Events are matched if they involve the given character, belong to
        the given story arc, or carry the given emotional tone. When
        multiple filters are provided, an event matching ANY filter is
        included (union semantics). Results are ranked by dramatic weight
        (descending) so the most narratively significant events surface
        first.

        Args:
            character_id: When provided, match events where this character
                participated.
            story_arc_id: When provided, match events in this story arc.
            emotion: When provided, match events whose ``emotional_tone``
                equals this value (case-insensitive).
            limit: Maximum number of results to return. ``0`` returns an
                empty list.

        Returns:
            A list of matching :class:`StoryEvent` objects ranked by
            dramatic weight, descending.
        """
        with self._lock:
            n = max(0, int(limit))
            emotion_lower = emotion.lower().strip() if emotion else None
            matched: List[StoryEvent] = []
            seen_ids: set = set()
            for event in self._events_store.values():
                match = False
                if character_id is not None and character_id in event.participant_ids:
                    match = True
                if story_arc_id is not None and event.story_arc_id == story_arc_id:
                    match = True
                if emotion_lower is not None and event.emotional_tone.lower().strip() == emotion_lower:
                    match = True
                if match and event.event_id not in seen_ids:
                    matched.append(event)
                    seen_ids.add(event.event_id)

            # Rank by dramatic weight, descending. Ties are broken by
            # narrative timestamp so earlier events come first among
            # equally-weighted ones.
            matched.sort(
                key=lambda e: (-e.dramatic_weight, e.timestamp)
            )
            if n > 0:
                matched = matched[:n]

            self._record_event(
                NarrativeEventKind.STORY_EVENT_RECALLED,
                {
                    "character_id": character_id,
                    "story_arc_id": story_arc_id,
                    "emotion": emotion,
                    "returned": len(matched),
                },
            )
            return matched

    def link_event_to_character(
        self, event_id: str, character_id: str
    ) -> bool:
        """Add an event to a character's ``key_events`` list.

        Also adds the character to the event's ``participant_ids`` if not
        already present, so the linkage is bidirectional.

        Args:
            event_id: Identifier of the story event to link.
            character_id: Identifier of the character to link the event to.

        Returns:
            ``True`` if both the event and character were found and the
            link was applied, ``False`` otherwise.
        """
        with self._lock:
            event = self._events_store.get(event_id)
            arc = self._characters.get(character_id)
            if event is None or arc is None:
                return False

            if event_id not in arc.key_events:
                arc.key_events.append(event_id)
            if character_id not in event.participant_ids:
                event.participant_ids.append(character_id)

            self._record_event(
                NarrativeEventKind.ARC_UPDATED,
                {
                    "character_id": character_id,
                    "arc_id": arc.arc_id,
                    "linked_event_id": event_id,
                },
            )
            return True

    # ------------------------------------------------------------------
    # Plot thread management
    # ------------------------------------------------------------------

    def create_plot_thread(
        self,
        name: str,
        description: str = "",
        related_arcs: Optional[List[str]] = None,
        priority: int = 3,
    ) -> PlotThread:
        """Create and store a new plot thread.

        Plot threads represent ongoing narrative storylines that link
        related events across one or more character arcs. New threads
        start in the OPEN status.

        Args:
            name: Human-readable name of the plot thread.
            description: Optional description of the storyline.
            related_arcs: Optional list of story arc ids the thread spans.
            priority: Priority in [1, 5] (clamped). Higher values indicate
                more central threads.

        Returns:
            The newly created :class:`PlotThread`.
        """
        with self._lock:
            thread = PlotThread(
                thread_id=_new_id(),
                name=name,
                description=description,
                related_arcs=list(related_arcs) if related_arcs else [],
                status=PlotThreadStatus.OPEN,
                priority=int(_clamp(priority, 1, 5)),
                created_at=_now(),
            )
            self._plot_threads[thread.thread_id] = thread
            self._thread_counter += 1
            _evict_fifo_dict(self._plot_threads, _MAX_PLOT_THREADS)

            self._record_event(
                NarrativeEventKind.PLOT_THREAD_LINKED,
                {
                    "thread_id": thread.thread_id,
                    "name": thread.name,
                    "priority": thread.priority,
                    "related_arc_count": len(thread.related_arcs),
                },
            )
            return thread

    def get_plot_thread(self, thread_id: str) -> Optional[PlotThread]:
        """Return the plot thread with the given id, or None if absent."""
        with self._lock:
            return self._plot_threads.get(thread_id)

    def list_plot_threads(
        self, status: Optional[PlotThreadStatus] = None
    ) -> List[PlotThread]:
        """Return plot threads, optionally filtered by status.

        Args:
            status: When provided, only threads with this status are
                returned.

        Returns:
            A list of matching :class:`PlotThread` objects in insertion
            order.
        """
        with self._lock:
            results: List[PlotThread] = []
            for thread in self._plot_threads.values():
                if status is not None and thread.status != status:
                    continue
                results.append(thread)
            return results

    def resolve_plot_thread(
        self,
        thread_id: str,
        resolution_event_id: Optional[str] = None,
    ) -> Optional[PlotThread]:
        """Mark a plot thread as RESOLVED.

        If ``resolution_event_id`` is provided, it is appended to the
        thread's ``linked_events`` list. The thread's ``resolved_at``
        timestamp is recorded.

        Args:
            thread_id: Identifier of the plot thread to resolve.
            resolution_event_id: Optional event id that resolved the thread.

        Returns:
            The updated :class:`PlotThread`, or ``None`` if not found or
            already resolved/dropped.
        """
        with self._lock:
            thread = self._plot_threads.get(thread_id)
            if thread is None:
                return None
            if thread.status != PlotThreadStatus.OPEN:
                return None

            thread.status = PlotThreadStatus.RESOLVED
            thread.resolved_at = _now()
            if resolution_event_id is not None:
                if resolution_event_id not in thread.linked_events:
                    thread.linked_events.append(resolution_event_id)

            self._record_event(
                NarrativeEventKind.PLOT_THREAD_LINKED,
                {
                    "thread_id": thread.thread_id,
                    "name": thread.name,
                    "new_status": thread.status.value,
                    "resolution_event_id": resolution_event_id,
                },
            )
            return thread

    def link_event_to_thread(
        self, thread_id: str, event_id: str
    ) -> bool:
        """Link a story event to a plot thread.

        Adds ``event_id`` to the thread's ``linked_events`` list if not
        already present.

        Args:
            thread_id: Identifier of the plot thread.
            event_id: Identifier of the story event to link.

        Returns:
            ``True`` if both the thread and event were found and the link
            was applied, ``False`` otherwise.
        """
        with self._lock:
            thread = self._plot_threads.get(thread_id)
            event = self._events_store.get(event_id)
            if thread is None or event is None:
                return False

            if event_id not in thread.linked_events:
                thread.linked_events.append(event_id)

            self._record_event(
                NarrativeEventKind.PLOT_THREAD_LINKED,
                {
                    "thread_id": thread.thread_id,
                    "name": thread.name,
                    "linked_event_id": event_id,
                },
            )
            return True

    # ------------------------------------------------------------------
    # Timelines and character journeys
    # ------------------------------------------------------------------

    def build_timeline(self, story_arc_id: str) -> NarrativeTimeline:
        """Construct (and store) a chronological timeline for a story arc.

        Filters all events belonging to ``story_arc_id`` and orders them
        by their narrative ``timestamp`` field (ascending). The resulting
        :class:`NarrativeTimeline` replaces any previously stored timeline
        for the same arc.

        Args:
            story_arc_id: Identifier of the story arc to build a timeline for.

        Returns:
            A :class:`NarrativeTimeline` with the chronologically ordered
            event ids. If no events exist for the arc, an empty timeline
            is returned.
        """
        with self._lock:
            timeline = self._build_timeline_internal(story_arc_id)
            self._timelines[story_arc_id] = timeline
            self._timeline_counter += 1
            _evict_fifo_dict(self._timelines, _MAX_TIMELINES)

            self._record_event(
                NarrativeEventKind.TIMELINE_REORDERED,
                {
                    "story_arc_id": story_arc_id,
                    "timeline_id": timeline.timeline_id,
                    "event_count": len(timeline.ordered_events),
                },
            )
            return timeline

    def get_timeline(self, story_arc_id: str) -> Optional[NarrativeTimeline]:
        """Return the stored timeline for a story arc, or None if absent.

        Unlike :meth:`build_timeline`, this method does not reconstruct the
        timeline; it returns the most recently stored timeline for the arc.
        """
        with self._lock:
            return self._timelines.get(story_arc_id)

    def get_character_journey(
        self, character_id: str
    ) -> List[StoryEvent]:
        """Return all events involving a character in chronological order.

        An event involves a character if the character's id appears in the
        event's ``participant_ids`` list, or if the event id appears in the
        character's ``key_events`` list. Results are sorted by narrative
        timestamp (ascending).

        Args:
            character_id: Identifier of the character whose journey to retrieve.

        Returns:
            A chronologically ordered list of :class:`StoryEvent` objects
            involving the character. Returns an empty list if the character
            is unknown or has no events.
        """
        with self._lock:
            arc = self._characters.get(character_id)
            if arc is None:
                return []

            # Collect event ids from both the character's key_events list
            # and any event whose participant_ids include the character.
            journey_ids: set = set()
            for eid in arc.key_events:
                journey_ids.add(eid)
            for event in self._events_store.values():
                if character_id in event.participant_ids:
                    journey_ids.add(event.event_id)

            journey: List[StoryEvent] = []
            for eid in journey_ids:
                event = self._events_store.get(eid)
                if event is not None:
                    journey.append(event)

            # Sort by narrative timestamp; empty timestamps go last.
            journey.sort(key=lambda e: (e.timestamp == "", e.timestamp))
            return journey

    # ------------------------------------------------------------------
    # Narrative density analysis
    # ------------------------------------------------------------------

    def compute_narrative_density(
        self, story_arc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute narrative density metrics for the engine or a single arc.

        When ``story_arc_id`` is provided, metrics are computed only over
        events belonging to that arc; otherwise all events are considered.

        The returned dictionary contains:

        - ``total_events``: count of events in scope.
        - ``events_by_type``: mapping of event-type value -> count.
        - ``dramatic_weight_distribution``: mapping of weight bucket
          ("low", "medium", "high") -> count, where low < 0.4,
          0.4 <= medium <= 0.7, and high > 0.7.
        - ``avg_dramatic_weight``: mean dramatic weight across events.
        - ``events_per_stage``: mapping of :class:`ArcStage` value ->
          count of events attributed to that stage. An event is attributed
          to a stage if any participating character is currently at that
          stage.
        - ``emotional_tone_distribution``: mapping of emotional tone ->
          count.

        Args:
            story_arc_id: Optional story arc to scope the computation.

        Returns:
            A dictionary of narrative density metrics.
        """
        with self._lock:
            events: List[StoryEvent] = []
            for event in self._events_store.values():
                if story_arc_id is not None and event.story_arc_id != story_arc_id:
                    continue
                events.append(event)

            total_events = len(events)
            events_by_type: Dict[str, int] = {}
            weight_distribution: Dict[str, int] = {"low": 0, "medium": 0, "high": 0}
            tone_distribution: Dict[str, int] = {}
            events_per_stage: Dict[str, int] = {}
            total_weight = 0.0

            for event in events:
                # Events by type.
                etype_key = event.event_type.value
                events_by_type[etype_key] = events_by_type.get(etype_key, 0) + 1

                # Dramatic weight distribution.
                weight = event.dramatic_weight
                total_weight += weight
                if weight < 0.4:
                    weight_distribution["low"] += 1
                elif weight <= 0.7:
                    weight_distribution["medium"] += 1
                else:
                    weight_distribution["high"] += 1

                # Emotional tone distribution.
                tone = event.emotional_tone.strip()
                if tone:
                    tone_distribution[tone] = tone_distribution.get(tone, 0) + 1

                # Events per stage: attribute the event to the current
                # stage of each participating character.
                attributed_stages: set = set()
                for pid in event.participant_ids:
                    char_arc = self._characters.get(pid)
                    if char_arc is not None:
                        attributed_stages.add(char_arc.current_stage.value)
                for stage_val in attributed_stages:
                    events_per_stage[stage_val] = (
                        events_per_stage.get(stage_val, 0) + 1
                    )

            avg_weight = (
                round(total_weight / total_events, 4) if total_events > 0 else 0.0
            )

            return {
                "total_events": total_events,
                "events_by_type": events_by_type,
                "dramatic_weight_distribution": weight_distribution,
                "avg_dramatic_weight": avg_weight,
                "events_per_stage": events_per_stage,
                "emotional_tone_distribution": tone_distribution,
            }

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[NarrativeMemoryEvent]:
        """Return the most recent narrative memory audit events, newest first.

        These are engine lifecycle events (recorded, recalled, arc changes,
        etc.), not story events. To list story events, use
        :meth:`list_story_events`.
        """
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> NarrativeMemoryStats:
        """Compute aggregate statistics over the narrative memory engine."""
        with self._lock:
            events = list(self._events_store.values())
            arcs = list(self._characters.values())
            threads = list(self._plot_threads.values())

            by_type: Dict[str, int] = {}
            arcs_by_status: Dict[str, int] = {}
            total_weight = 0.0
            for event in events:
                key = event.event_type.value
                by_type[key] = by_type.get(key, 0) + 1
                total_weight += event.dramatic_weight
            for arc in arcs:
                key = arc.status.value
                arcs_by_status[key] = arcs_by_status.get(key, 0) + 1

            avg_weight = (
                round(total_weight / len(events), 4) if events else 0.0
            )

            return NarrativeMemoryStats(
                total_events=len(events),
                total_arcs=len(arcs),
                total_threads=len(threads),
                total_characters=len(arcs),
                events_by_type=by_type,
                arcs_by_status=arcs_by_status,
                avg_dramatic_weight=avg_weight,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the engine.

        The ``initialized`` flag is always the first key so callers can
        cheaply verify the engine is ready before inspecting counts.
        """
        with self._lock:
            stats = self.get_stats()
            status: Dict[str, Any] = {
                "initialized": self._initialized,
                "engine_id": id(self),
                "total_events": len(self._events_store),
                "total_characters": len(self._characters),
                "total_threads": len(self._plot_threads),
                "total_timelines": len(self._timelines),
                "total_audit_events": len(self._events),
                "event_counter": self._event_counter,
                "character_counter": self._character_counter,
                "thread_counter": self._thread_counter,
                "timeline_counter": self._timeline_counter,
                "audit_event_counter": self._audit_event_counter,
                "avg_dramatic_weight": stats.avg_dramatic_weight,
                "events_by_type": dict(stats.events_by_type),
                "arcs_by_status": dict(stats.arcs_by_status),
                "capacities": {
                    "max_story_events": _MAX_STORY_EVENTS,
                    "max_characters": _MAX_CHARACTERS,
                    "max_plot_threads": _MAX_PLOT_THREADS,
                    "max_timelines": _MAX_TIMELINES,
                    "max_events": _MAX_EVENTS,
                },
            }
            return status

    def get_snapshot(self) -> NarrativeMemorySnapshot:
        """Capture a point-in-time snapshot of the engine state."""
        with self._lock:
            return NarrativeMemorySnapshot(
                initialized=self._initialized,
                events=list(self._events_store.values()),
                arcs=list(self._characters.values()),
                threads=list(self._plot_threads.values()),
                characters=list(self._characters.values()),
                timelines=list(self._timelines.values()),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the engine to its initial seeded state.

        Clears all tracked state and re-seeds the baseline narrative
        content, restoring the engine to a freshly initialized state.
        """
        with self._lock:
            self._events_store.clear()
            self._characters.clear()
            self._plot_threads.clear()
            self._timelines.clear()
            self._events.clear()
            self._event_counter = 0
            self._character_counter = 0
            self._thread_counter = 0
            self._timeline_counter = 0
            self._audit_event_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_narrative_memory() -> NarrativeMemoryEngine:
    """Return the singleton NarrativeMemoryEngine instance."""
    return NarrativeMemoryEngine.get_instance()
