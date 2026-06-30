"""
SparkLabs Engine - Camera Director

A cinematic camera director that orchestrates camera shots, transitions,
and sequences for the game engine. It provides director-level camera
control including shot composition, camera rigs, focus pulls, and
cutscene sequencing - similar to a film director's camera department but
for real-time interactive game scenes.

The camera director maintains a registry of camera shots, transitions
between them, ordered sequences of shots, and focus pulls. Shots
progress through the ``CameraState`` lifecycle (IDLE -> PREPARING ->
ACTIVE -> TRANSITIONING -> COMPLETED). When a shot is activated it
becomes part of the active shot set; transitions move the active
camera from one shot to another; sequences chain shots together for
hands-off cinematic playback.

This subsystem focuses on director-level orchestration and composition
evaluation. Low-level camera transform integration is delegated to the
engine's camera controller; this module decides which shot is active,
how it is composed, and how the cut moves between shots.

Architecture:
  CameraDirectorEngine (Singleton)
    |-- CameraShot                  (a single directed camera shot)
    |-- CameraTransition            (a cut/dissolve/fade between shots)
    |-- CameraSequence              (an ordered playlist of shots)
    |-- FocusPull                   (a depth-of-field focus change)
    |-- CameraEvent                 (an emitted director lifecycle event)
    |-- CameraStats                 (aggregate statistic counters)
    |-- CameraSnapshot              (immutable snapshot of director state)

Lifecycle:
  1. create_shot(...)                       -> CameraShot
  2. activate_shot(shot_id)                 -> CameraShot
  3. create_transition(from, to, type, ...) -> CameraTransition
  4. execute_transition(transition_id)      -> CameraTransition
  5. create_sequence(name, shot_ids, ...)   -> CameraSequence
  6. start_sequence(sequence_id)            -> CameraSequence
  7. advance_sequence(sequence_id)          -> CameraSequence
  8. complete_sequence(sequence_id)         -> CameraSequence
  9. create_focus_pull(...) / execute_focus_pull(...)
 10. compute_composition(shot_id)          -> Dict[str, Any]
 11. get_active_shots() / get_snapshot() / get_status() / reset()
"""

from __future__ import annotations

import datetime
import math
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Enumerations
# =============================================================================


class ShotType(Enum):
    """Cinematic classification of a camera shot by framing."""

    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    OVER_SHOULDER = "over_shoulder"
    AERIAL = "aerial"
    FIRST_PERSON = "first_person"
    TRACKING = "tracking"
    ESTABLISHING = "establishing"


class CameraRig(Enum):
    """The physical camera rig or movement apparatus used for a shot."""

    STATIC = "static"
    DOLLY = "dolly"
    CRANE = "crane"
    HANDHELD = "handheld"
    STEADYCAM = "steadycam"
    TRACK = "track"
    ORBIT = "orbit"


class TransitionType(Enum):
    """The style of cut or blend used to move between two shots."""

    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    DOLLY = "dolly"
    WIPE = "wipe"
    ZOOM = "zoom"


class CameraState(Enum):
    """Lifecycle states for a camera shot or sequence."""

    IDLE = "idle"
    PREPARING = "preparing"
    ACTIVE = "active"
    TRANSITIONING = "transitioning"
    COMPLETED = "completed"


class CompositionRule(Enum):
    """Cinematic composition guidelines used to evaluate a shot."""

    RULE_OF_THIRDS = "rule_of_thirds"
    GOLDEN_RATIO = "golden_ratio"
    CENTER = "center"
    LEADING_LINES = "leading_lines"
    SYMMETRY = "symmetry"
    DIAGONAL = "diagonal"


class CameraEventKind(Enum):
    """Kinds of events emitted by the camera director."""

    SHOT_CREATED = "shot_created"
    SHOT_ACTIVATED = "shot_activated"
    SHOT_COMPLETED = "shot_completed"
    TRANSITION_STARTED = "transition_started"
    TRANSITION_COMPLETED = "transition_completed"
    SEQUENCE_STARTED = "sequence_started"
    SEQUENCE_COMPLETED = "sequence_completed"
    FOCUS_PULL = "focus_pull"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class CameraShot:
    """A single directed camera shot.

    A shot describes a camera placement (position), the point it is aimed
    at (look_at), the field of view, the duration the shot should hold,
    the rig used to capture it, and the composition rule it should be
    evaluated against. Shots progress through the ``CameraState``
    lifecycle as the director activates, transitions between, and
    completes them.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name of the shot.
        shot_type: Cinematic framing classification.
        rig: The camera rig used to capture the shot.
        position: Camera world position as ``(x, y, z)``.
        look_at: World position the camera is aimed at as ``(x, y, z)``.
        fov: Horizontal field of view in degrees.
        duration: Intended hold duration in seconds.
        composition_rule: Composition guideline the shot targets.
        priority: Ordering priority (lower values activate earlier).
        state: Current lifecycle state.
        metadata: Free-form extension data.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    shot_type: ShotType = ShotType.WIDE
    rig: CameraRig = CameraRig.STATIC
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    look_at: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    fov: float = 60.0
    duration: float = 0.0
    composition_rule: CompositionRule = CompositionRule.RULE_OF_THIRDS
    priority: int = 0
    state: CameraState = CameraState.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "shot_type": self.shot_type.value,
            "rig": self.rig.value,
            "position": list(self.position),
            "look_at": list(self.look_at),
            "fov": self.fov,
            "duration": self.duration,
            "composition_rule": self.composition_rule.value,
            "priority": self.priority,
            "state": self.state.value,
            "metadata": dict(self.metadata),
        }


@dataclass
class CameraTransition:
    """A transition that moves the active camera from one shot to another.

    Transitions are created between two existing shots and are executed
    on demand. Executing a transition marks the source shot as
    ``COMPLETED``, the destination shot as ``ACTIVE``, and records the
    start and completion timestamps.

    Attributes:
        id: Unique identifier (auto-generated).
        from_shot_id: Identifier of the source shot.
        to_shot_id: Identifier of the destination shot.
        transition_type: The style of cut or blend.
        duration: Transition length in seconds.
        easing: Easing function name applied to the blend.
        started_at: Timestamp when execution began.
        completed_at: Timestamp when execution finished.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_shot_id: str = ""
    to_shot_id: str = ""
    transition_type: TransitionType = TransitionType.CUT
    duration: float = 0.0
    easing: str = "linear"
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_shot_id": self.from_shot_id,
            "to_shot_id": self.to_shot_id,
            "transition_type": self.transition_type.value,
            "duration": self.duration,
            "easing": self.easing,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class CameraSequence:
    """An ordered playlist of camera shots for hands-off cinematic playback.

    A sequence chains shots together so that advancing the sequence
    moves the active camera from one shot to the next. Sequences
    progress through the ``CameraState`` lifecycle and may optionally
    loop back to the first shot after the last.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name of the sequence.
        description: Long-form description of the sequence.
        shot_ids: Ordered list of shot identifiers in the sequence.
        current_index: Index of the currently active shot, or -1 when
            the sequence has not started or has been completed.
        state: Current lifecycle state.
        started_at: Timestamp when the sequence started.
        completed_at: Timestamp when the sequence completed.
        loop: Whether the sequence loops after the last shot.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    shot_ids: List[str] = field(default_factory=list)
    current_index: int = -1
    state: CameraState = CameraState.IDLE
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    loop: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "shot_ids": list(self.shot_ids),
            "current_index": self.current_index,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "loop": self.loop,
        }


@dataclass
class FocusPull:
    """A depth-of-field focus change performed on a shot.

    A focus pull moves the focal plane from one depth to another over a
    duration. Executing a focus pull records the start time and emits a
    ``FOCUS_PULL`` event; the pull is considered complete once its
    duration has elapsed.

    Attributes:
        id: Unique identifier (auto-generated).
        shot_id: Identifier of the shot the pull is performed on.
        from_focus_depth: Starting focal depth in world units.
        to_focus_depth: Target focal depth in world units.
        duration: Pull length in seconds.
        started_at: Timestamp when execution began.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    shot_id: str = ""
    from_focus_depth: float = 0.0
    to_focus_depth: float = 0.0
    duration: float = 0.0
    started_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "shot_id": self.shot_id,
            "from_focus_depth": self.from_focus_depth,
            "to_focus_depth": self.to_focus_depth,
            "duration": self.duration,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }


@dataclass
class CameraStats:
    """Aggregate statistic counters for the camera director.

    Attributes:
        total_shots_created: Lifetime count of shots created.
        total_shots_activated: Lifetime count of shot activations.
        total_transitions: Lifetime count of transitions executed.
        total_sequences: Lifetime count of sequences started.
        total_focus_pulls: Lifetime count of focus pulls executed.
        last_updated_at: Timestamp of the most recent counter update.
    """

    total_shots_created: int = 0
    total_shots_activated: int = 0
    total_transitions: int = 0
    total_sequences: int = 0
    total_focus_pulls: int = 0
    last_updated_at: Optional[datetime.datetime] = field(
        default_factory=datetime.datetime.now
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_shots_created": self.total_shots_created,
            "total_shots_activated": self.total_shots_activated,
            "total_transitions": self.total_transitions,
            "total_sequences": self.total_sequences,
            "total_focus_pulls": self.total_focus_pulls,
            "last_updated_at": self.last_updated_at.isoformat()
            if self.last_updated_at
            else None,
        }


@dataclass
class CameraSnapshot:
    """An immutable snapshot of the camera director state.

    Attributes:
        active_shot_count: Number of shots currently active.
        sequence_count: Total number of registered sequences.
        total_shots: Total number of registered shots.
        stats: Aggregated statistic counters.
        timestamp: Time at which the snapshot was taken.
    """

    active_shot_count: int = 0
    sequence_count: int = 0
    total_shots: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_shot_count": self.active_shot_count,
            "sequence_count": self.sequence_count,
            "total_shots": self.total_shots,
            "stats": dict(self.stats),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class CameraEvent:
    """An immutable record of a camera director lifecycle event.

    Attributes:
        id: Unique identifier (auto-generated).
        kind: The ``CameraEventKind`` of the event.
        payload: Free-form payload describing the event.
        timestamp: Time at which the event was emitted.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: CameraEventKind = CameraEventKind.SHOT_CREATED
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "payload": dict(self.payload),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =============================================================================
# Camera Director Engine (Singleton)
# =============================================================================


class CameraDirectorEngine:
    """Engine-side cinematic camera director.

    Maintains a registry of camera shots, transitions, sequences, and
    focus pulls. Coordinates shot activation through the ``CameraState``
    lifecycle, evaluates shot composition against cinematic rules, and
    emits lifecycle events to subscribed handlers.

    All public methods are thread-safe. The class implements the
    singleton pattern with double-checked locking; consumers should
    obtain the instance through :meth:`get_instance` or
    :func:`get_camera_director`.
    """

    _instance: Optional["CameraDirectorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if getattr(self, "_initialized", False):
            return

        # Primary registries.
        self._shots: Dict[str, CameraShot] = {}
        self._transitions: Dict[str, CameraTransition] = {}
        self._sequences: Dict[str, CameraSequence] = {}
        self._focus_pulls: Dict[str, FocusPull] = {}

        # Event log and subscriber registry.
        self._events: List[CameraEvent] = []
        self._event_handlers: Dict[str, List[Callable[[CameraEvent], None]]] = {}
        self._total_events_emitted: int = 0

        # Aggregate statistic counters.
        self._total_shots_created: int = 0
        self._total_shots_activated: int = 0
        self._total_transitions: int = 0
        self._total_sequences: int = 0
        self._total_focus_pulls: int = 0

        self._initialized: bool = True

        # Populate the default seed cinematic data.
        self._seed_default_data()

    @classmethod
    def get_instance(cls) -> "CameraDirectorEngine":
        """Return the singleton CameraDirectorEngine instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_kind(kind: Any) -> str:
        """Normalize an event kind argument to its string value."""
        if kind is None:
            return "*"
        if isinstance(kind, CameraEventKind):
            return kind.value
        return str(kind)

    def _dispatch_event(self, event: CameraEvent) -> None:
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

    def _emit_event(
        self,
        kind: CameraEventKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> CameraEvent:
        """Create, log, and dispatch a camera event (internal use only)."""
        event = CameraEvent(
            kind=kind,
            payload=payload or {},
        )
        self._events.append(event)
        if len(self._events) > 1000:
            # Evict the oldest entries beyond the 1000-event cap.
            del self._events[: len(self._events) - 1000]
        self._total_events_emitted += 1
        self._dispatch_event(event)
        return event

    def _compute_stats(self) -> Dict[str, Any]:
        """Compute the aggregate statistic counters from current state."""
        return {
            "total_shots_created": self._total_shots_created,
            "total_shots_activated": self._total_shots_activated,
            "total_transitions": self._total_transitions,
            "total_sequences": self._total_sequences,
            "total_focus_pulls": self._total_focus_pulls,
            "last_updated_at": datetime.datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Shot management
    # ------------------------------------------------------------------

    def create_shot(
        self,
        name: str,
        shot_type: ShotType,
        rig: CameraRig,
        position: Tuple[float, float, float],
        look_at: Tuple[float, float, float],
        fov: float = 60.0,
        duration: float = 0.0,
        composition_rule: CompositionRule = CompositionRule.RULE_OF_THIRDS,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CameraShot:
        """Create and register a new camera shot.

        Args:
            name: Human-readable name of the shot.
            shot_type: Cinematic framing classification.
            rig: The camera rig used to capture the shot.
            position: Camera world position as ``(x, y, z)``.
            look_at: World position the camera is aimed at as ``(x, y, z)``.
            fov: Horizontal field of view in degrees.
            duration: Intended hold duration in seconds.
            composition_rule: Composition guideline the shot targets.
            priority: Ordering priority (lower values activate earlier).
            metadata: Free-form extension data.

        Returns:
            The newly created CameraShot.
        """
        with self._lock:
            shot = CameraShot(
                name=name,
                shot_type=shot_type,
                rig=rig,
                position=tuple(position),
                look_at=tuple(look_at),
                fov=fov,
                duration=duration,
                composition_rule=composition_rule,
                priority=priority,
                state=CameraState.IDLE,
                metadata=dict(metadata) if metadata else {},
            )
            self._shots[shot.id] = shot
            self._total_shots_created += 1
            self._emit_event(
                CameraEventKind.SHOT_CREATED,
                payload={
                    "shot_id": shot.id,
                    "name": shot.name,
                    "shot_type": shot.shot_type.value,
                    "rig": shot.rig.value,
                },
            )
            return shot

    def get_shot(self, shot_id: str) -> Optional[CameraShot]:
        """Retrieve a shot by its identifier."""
        with self._lock:
            return self._shots.get(shot_id)

    def list_shots(
        self,
        shot_type: Optional[ShotType] = None,
        rig: Optional[CameraRig] = None,
    ) -> List[CameraShot]:
        """List shots, optionally filtered by shot type and rig.

        The returned list is sorted by ascending priority then name.
        """
        with self._lock:
            shots = list(self._shots.values())
            if shot_type is not None:
                shots = [s for s in shots if s.shot_type == shot_type]
            if rig is not None:
                shots = [s for s in shots if s.rig == rig]
            shots.sort(key=lambda s: (s.priority, s.name))
            return shots

    def remove_shot(self, shot_id: str) -> bool:
        """Remove a shot from the director.

        Returns:
            True if the shot was removed, False if it was not found.
        """
        with self._lock:
            if shot_id not in self._shots:
                return False
            del self._shots[shot_id]
            # Detach the shot from any sequences that reference it.
            for sequence in self._sequences.values():
                if shot_id in sequence.shot_ids:
                    sequence.shot_ids = [
                        sid for sid in sequence.shot_ids if sid != shot_id
                    ]
            return True

    def activate_shot(self, shot_id: str) -> CameraShot:
        """Activate a shot, marking it as the active camera source.

        Sets the shot state to ``ACTIVE``. A shot in a terminal state
        cannot be reactivated unless it has been reset.

        Args:
            shot_id: Identifier of the shot to activate.

        Returns:
            The activated CameraShot.

        Raises:
            ValueError: If the shot is not found.
        """
        with self._lock:
            shot = self._shots.get(shot_id)
            if shot is None:
                raise ValueError(f"Shot not found: {shot_id}")
            shot.state = CameraState.ACTIVE
            self._total_shots_activated += 1
            self._emit_event(
                CameraEventKind.SHOT_ACTIVATED,
                payload={
                    "shot_id": shot.id,
                    "name": shot.name,
                    "shot_type": shot.shot_type.value,
                },
            )
            return shot

    def complete_shot(self, shot_id: str) -> CameraShot:
        """Mark a shot as completed.

        Sets the shot state to ``COMPLETED``. A shot that is not
        currently active is still marked completed; this is useful when
        a transition finalizes a source shot.

        Args:
            shot_id: Identifier of the shot to complete.

        Returns:
            The completed CameraShot.

        Raises:
            ValueError: If the shot is not found or is already completed.
        """
        with self._lock:
            shot = self._shots.get(shot_id)
            if shot is None:
                raise ValueError(f"Shot not found: {shot_id}")
            if shot.state == CameraState.COMPLETED:
                raise ValueError(
                    f"Shot already completed: {shot_id}"
                )
            shot.state = CameraState.COMPLETED
            self._emit_event(
                CameraEventKind.SHOT_COMPLETED,
                payload={"shot_id": shot.id, "name": shot.name},
            )
            return shot

    # ------------------------------------------------------------------
    # Transition management
    # ------------------------------------------------------------------

    def create_transition(
        self,
        from_shot_id: str,
        to_shot_id: str,
        transition_type: TransitionType = TransitionType.CUT,
        duration: float = 0.0,
        easing: str = "linear",
    ) -> CameraTransition:
        """Create a transition between two existing shots.

        Args:
            from_shot_id: Identifier of the source shot.
            to_shot_id: Identifier of the destination shot.
            transition_type: The style of cut or blend.
            duration: Transition length in seconds.
            easing: Easing function name applied to the blend.

        Returns:
            The newly created CameraTransition.

        Raises:
            ValueError: If either shot is not found or the two shots are
                the same.
        """
        with self._lock:
            if from_shot_id not in self._shots:
                raise ValueError(f"Source shot not found: {from_shot_id}")
            if to_shot_id not in self._shots:
                raise ValueError(f"Destination shot not found: {to_shot_id}")
            if from_shot_id == to_shot_id:
                raise ValueError(
                    "Cannot transition a shot to itself: "
                    f"{from_shot_id}"
                )
            transition = CameraTransition(
                from_shot_id=from_shot_id,
                to_shot_id=to_shot_id,
                transition_type=transition_type,
                duration=duration,
                easing=easing,
            )
            self._transitions[transition.id] = transition
            return transition

    def execute_transition(self, transition_id: str) -> CameraTransition:
        """Execute a previously created transition.

        Marks the source shot as ``COMPLETED`` and the destination shot
        as ``ACTIVE``, then records the transition start and completion
        timestamps.

        Args:
            transition_id: Identifier of the transition to execute.

        Returns:
            The executed CameraTransition.

        Raises:
            ValueError: If the transition is not found or has already
                been executed.
        """
        with self._lock:
            transition = self._transitions.get(transition_id)
            if transition is None:
                raise ValueError(f"Transition not found: {transition_id}")
            if transition.completed_at is not None:
                raise ValueError(
                    f"Transition already executed: {transition_id}"
                )

            from_shot = self._shots.get(transition.from_shot_id)
            to_shot = self._shots.get(transition.to_shot_id)
            if from_shot is None or to_shot is None:
                raise ValueError(
                    "Transition references a missing shot: "
                    f"{transition.from_shot_id} -> {transition.to_shot_id}"
                )

            transition.started_at = datetime.datetime.now()
            if from_shot.state != CameraState.COMPLETED:
                from_shot.state = CameraState.TRANSITIONING
            self._emit_event(
                CameraEventKind.TRANSITION_STARTED,
                payload={
                    "transition_id": transition.id,
                    "from_shot_id": transition.from_shot_id,
                    "to_shot_id": transition.to_shot_id,
                    "transition_type": transition.transition_type.value,
                },
            )

            # Finalize the source shot and activate the destination.
            from_shot.state = CameraState.COMPLETED
            to_shot.state = CameraState.ACTIVE
            self._total_shots_activated += 1
            self._total_transitions += 1
            transition.completed_at = datetime.datetime.now()
            self._emit_event(
                CameraEventKind.TRANSITION_COMPLETED,
                payload={
                    "transition_id": transition.id,
                    "from_shot_id": transition.from_shot_id,
                    "to_shot_id": transition.to_shot_id,
                },
            )
            return transition

    # ------------------------------------------------------------------
    # Sequence management
    # ------------------------------------------------------------------

    def create_sequence(
        self,
        name: str,
        description: str = "",
        shot_ids: Optional[List[str]] = None,
        loop: bool = False,
    ) -> CameraSequence:
        """Create and register a sequence of shots.

        Args:
            name: Human-readable name of the sequence.
            description: Long-form description of the sequence.
            shot_ids: Ordered list of shot identifiers in the sequence.
            loop: Whether the sequence loops after the last shot.

        Returns:
            The newly created CameraSequence.
        """
        with self._lock:
            sequence = CameraSequence(
                name=name,
                description=description,
                shot_ids=list(shot_ids) if shot_ids else [],
                current_index=-1,
                state=CameraState.IDLE,
                loop=loop,
            )
            self._sequences[sequence.id] = sequence
            return sequence

    def start_sequence(self, sequence_id: str) -> CameraSequence:
        """Start playing a sequence by activating its first shot.

        Sets the sequence state to ``ACTIVE`` and activates the first
        shot in the playlist.

        Args:
            sequence_id: Identifier of the sequence to start.

        Returns:
            The started CameraSequence.

        Raises:
            ValueError: If the sequence is not found, is already
                active, or contains no shots.
        """
        with self._lock:
            sequence = self._sequences.get(sequence_id)
            if sequence is None:
                raise ValueError(f"Sequence not found: {sequence_id}")
            if sequence.state == CameraState.ACTIVE:
                raise ValueError(
                    f"Sequence already active: {sequence_id}"
                )
            if not sequence.shot_ids:
                raise ValueError(
                    f"Sequence has no shots: {sequence_id}"
                )
            sequence.state = CameraState.ACTIVE
            sequence.started_at = datetime.datetime.now()
            sequence.completed_at = None
            sequence.current_index = 0
            first_shot_id = sequence.shot_ids[0]
            first_shot = self._shots.get(first_shot_id)
            if first_shot is not None:
                first_shot.state = CameraState.ACTIVE
                self._total_shots_activated += 1
            self._total_sequences += 1
            self._emit_event(
                CameraEventKind.SEQUENCE_STARTED,
                payload={
                    "sequence_id": sequence.id,
                    "name": sequence.name,
                    "shot_count": len(sequence.shot_ids),
                },
            )
            return sequence

    def advance_sequence(self, sequence_id: str) -> CameraSequence:
        """Advance a sequence to its next shot.

        Completes the current shot, advances the index, and activates
        the next shot. When the end of the playlist is reached the
        sequence is either completed (non-looping) or wraps back to the
        first shot (looping).

        Args:
            sequence_id: Identifier of the sequence to advance.

        Returns:
            The advanced CameraSequence.

        Raises:
            ValueError: If the sequence is not found or is not active.
        """
        with self._lock:
            sequence = self._sequences.get(sequence_id)
            if sequence is None:
                raise ValueError(f"Sequence not found: {sequence_id}")
            if sequence.state != CameraState.ACTIVE:
                raise ValueError(
                    f"Sequence is not active: {sequence_id}"
                )

            current_shot_id = sequence.shot_ids[sequence.current_index]
            current_shot = self._shots.get(current_shot_id)
            if current_shot is not None and current_shot.state != CameraState.COMPLETED:
                current_shot.state = CameraState.COMPLETED

            next_index = sequence.current_index + 1
            if next_index >= len(sequence.shot_ids):
                if sequence.loop:
                    next_index = 0
                else:
                    sequence.state = CameraState.COMPLETED
                    sequence.completed_at = datetime.datetime.now()
                    sequence.current_index = -1
                    self._emit_event(
                        CameraEventKind.SEQUENCE_COMPLETED,
                        payload={
                            "sequence_id": sequence.id,
                            "name": sequence.name,
                        },
                    )
                    return sequence

            sequence.current_index = next_index
            next_shot_id = sequence.shot_ids[next_index]
            next_shot = self._shots.get(next_shot_id)
            if next_shot is not None:
                next_shot.state = CameraState.ACTIVE
                self._total_shots_activated += 1
            return sequence

    def complete_sequence(self, sequence_id: str) -> CameraSequence:
        """Mark a sequence as completed regardless of playback position.

        Args:
            sequence_id: Identifier of the sequence to complete.

        Returns:
            The completed CameraSequence.

        Raises:
            ValueError: If the sequence is not found.
        """
        with self._lock:
            sequence = self._sequences.get(sequence_id)
            if sequence is None:
                raise ValueError(f"Sequence not found: {sequence_id}")
            sequence.state = CameraState.COMPLETED
            sequence.completed_at = datetime.datetime.now()
            self._emit_event(
                CameraEventKind.SEQUENCE_COMPLETED,
                payload={
                    "sequence_id": sequence.id,
                    "name": sequence.name,
                },
            )
            return sequence

    # ------------------------------------------------------------------
    # Focus pull management
    # ------------------------------------------------------------------

    def create_focus_pull(
        self,
        shot_id: str,
        from_depth: float,
        to_depth: float,
        duration: float,
    ) -> FocusPull:
        """Create a focus pull on a shot.

        Args:
            shot_id: Identifier of the shot the pull is performed on.
            from_depth: Starting focal depth in world units.
            to_depth: Target focal depth in world units.
            duration: Pull length in seconds.

        Returns:
            The newly created FocusPull.

        Raises:
            ValueError: If the shot is not found or the duration is
                negative.
        """
        with self._lock:
            if shot_id not in self._shots:
                raise ValueError(f"Shot not found: {shot_id}")
            if duration < 0:
                raise ValueError(
                    f"Focus pull duration must be non-negative: {duration}"
                )
            pull = FocusPull(
                shot_id=shot_id,
                from_focus_depth=from_depth,
                to_focus_depth=to_depth,
                duration=duration,
            )
            self._focus_pulls[pull.id] = pull
            return pull

    def execute_focus_pull(self, focus_pull_id: str) -> FocusPull:
        """Execute a previously created focus pull.

        Records the start time, increments the focus pull counter, and
        emits a ``FOCUS_PULL`` event.

        Args:
            focus_pull_id: Identifier of the focus pull to execute.

        Returns:
            The executed FocusPull.

        Raises:
            ValueError: If the focus pull is not found, has already been
                executed, or its shot no longer exists.
        """
        with self._lock:
            pull = self._focus_pulls.get(focus_pull_id)
            if pull is None:
                raise ValueError(f"Focus pull not found: {focus_pull_id}")
            if pull.started_at is not None:
                raise ValueError(
                    f"Focus pull already executed: {focus_pull_id}"
                )
            if pull.shot_id not in self._shots:
                raise ValueError(
                    "Focus pull references a missing shot: "
                    f"{pull.shot_id}"
                )
            pull.started_at = datetime.datetime.now()
            self._total_focus_pulls += 1
            self._emit_event(
                CameraEventKind.FOCUS_PULL,
                payload={
                    "focus_pull_id": pull.id,
                    "shot_id": pull.shot_id,
                    "from_focus_depth": pull.from_focus_depth,
                    "to_focus_depth": pull.to_focus_depth,
                    "duration": pull.duration,
                },
            )
            return pull

    # ------------------------------------------------------------------
    # Composition evaluation
    # ------------------------------------------------------------------

    def compute_composition(self, shot_id: str) -> Dict[str, Any]:
        """Evaluate a shot's composition against the cinematic rules.

        Each composition rule is scored on a 0.0-1.0 scale based on the
        geometric relationship between the shot's camera position and
        its look-at target. The shot's targeted ``composition_rule`` is
        reported as ``rule`` and the matching score is reported as
        ``score``.

        Args:
            shot_id: Identifier of the shot to evaluate.

        Returns:
            A dict containing the evaluated ``rule``, the ``score``
            against that rule, the ``fov``, and the per-rule
            ``evaluations`` mapping.

        Raises:
            ValueError: If the shot is not found.
        """
        with self._lock:
            shot = self._shots.get(shot_id)
            if shot is None:
                raise ValueError(f"Shot not found: {shot_id}")

            evaluations = self._evaluate_all_rules(shot)
            target_value = shot.composition_rule.value
            score = evaluations.get(target_value, 0.0)
            return {
                "shot_id": shot.id,
                "name": shot.name,
                "rule": shot.composition_rule.value,
                "score": round(score, 4),
                "fov": shot.fov,
                "evaluations": {k: round(v, 4) for k, v in evaluations.items()},
            }

    def _evaluate_all_rules(self, shot: CameraShot) -> Dict[str, float]:
        """Compute a 0.0-1.0 score for each composition rule for a shot."""
        px, py, pz = shot.position
        lx, ly, lz = shot.look_at

        # Distance from the camera to the look-at target.
        dx = lx - px
        dy = ly - py
        dz = lz - pz
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        # Avoid division by zero in normalization below.
        safe_distance = distance if distance > 1e-6 else 1e-6

        # Horizontal and vertical offsets of the target relative to the
        # camera, normalized to the view distance so the scores are
        # scale-invariant.
        horizontal = math.sqrt(dx * dx + dz * dz) / safe_distance
        vertical = abs(dy) / safe_distance

        # Normalized field of view in 0..1 (60deg maps to ~0.5).
        fov_factor = max(0.0, min(1.0, shot.fov / 120.0))

        # Rule of thirds: target should sit near a third-line offset.
        thirds_target = 1.0 / 3.0
        thirds_score = 1.0 - min(
            1.0, abs(horizontal - thirds_target) + abs(vertical - thirds_target * 0.5)
        )

        # Golden ratio: target offset near 1/phi.
        phi = (1.0 + math.sqrt(5.0)) / 2.0
        golden_target = 1.0 / phi
        golden_score = 1.0 - min(
            1.0, abs(horizontal - golden_target) + abs(vertical - golden_target * 0.5)
        )

        # Center: target should be near the camera's forward axis.
        center_score = 1.0 - min(1.0, horizontal + vertical)

        # Leading lines: stronger when the camera is low and the target
        # is far (a receding perspective).
        leading_score = min(1.0, (1.0 - vertical) * (distance / 50.0))

        # Symmetry: strongest when the target is centered and balanced.
        symmetry_score = center_score * (1.0 - fov_factor * 0.3)

        # Diagonal: target offset near 45 degrees (equal horizontal and
        # vertical contribution).
        diagonal_score = 1.0 - min(1.0, abs(horizontal - vertical))

        return {
            CompositionRule.RULE_OF_THIRDS.value: max(0.0, min(1.0, thirds_score)),
            CompositionRule.GOLDEN_RATIO.value: max(0.0, min(1.0, golden_score)),
            CompositionRule.CENTER.value: max(0.0, min(1.0, center_score)),
            CompositionRule.LEADING_LINES.value: max(0.0, min(1.0, leading_score)),
            CompositionRule.SYMMETRY.value: max(0.0, min(1.0, symmetry_score)),
            CompositionRule.DIAGONAL.value: max(0.0, min(1.0, diagonal_score)),
        }

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_active_shots(self) -> List[CameraShot]:
        """Return all shots currently in the ``ACTIVE`` state.

        The returned list is sorted by ascending priority then name.
        """
        with self._lock:
            active = [
                s for s in self._shots.values() if s.state == CameraState.ACTIVE
            ]
            active.sort(key=lambda s: (s.priority, s.name))
            return active

    def get_transition(self, transition_id: str) -> Optional[CameraTransition]:
        """Retrieve a transition by its identifier."""
        with self._lock:
            return self._transitions.get(transition_id)

    def get_sequence(self, sequence_id: str) -> Optional[CameraSequence]:
        """Retrieve a sequence by its identifier."""
        with self._lock:
            return self._sequences.get(sequence_id)

    def get_focus_pull(self, focus_pull_id: str) -> Optional[FocusPull]:
        """Retrieve a focus pull by its identifier."""
        with self._lock:
            return self._focus_pulls.get(focus_pull_id)

    def list_transitions(self) -> List[CameraTransition]:
        """Return all registered transitions in creation order."""
        with self._lock:
            return list(self._transitions.values())

    def list_sequences(self) -> List[CameraSequence]:
        """Return all registered sequences sorted by name."""
        with self._lock:
            sequences = list(self._sequences.values())
            sequences.sort(key=lambda s: s.name)
            return sequences

    def list_focus_pulls(self) -> List[FocusPull]:
        """Return all registered focus pulls."""
        with self._lock:
            return list(self._focus_pulls.values())

    # ------------------------------------------------------------------
    # Event management
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: Any,
        handler: Callable[[CameraEvent], None],
    ) -> None:
        """Subscribe a handler to camera director events.

        Args:
            kind: The ``CameraEventKind`` (or its string value) to
                subscribe to. Pass ``None`` to subscribe to all events.
            handler: Callable invoked with each matching CameraEvent.

        Raises:
            ValueError: If the handler limit (50) has been reached.
        """
        with self._lock:
            total = sum(len(v) for v in self._event_handlers.values())
            if total >= 50:
                raise ValueError("Event handler limit reached (50)")
            key = self._normalize_kind(kind)
            self._event_handlers.setdefault(key, []).append(handler)

    def emit_event(
        self,
        kind: CameraEventKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> CameraEvent:
        """Emit a camera director event to the log and subscribed handlers.

        Args:
            kind: The ``CameraEventKind`` to emit.
            payload: Optional payload describing the event.

        Returns:
            The created CameraEvent.
        """
        with self._lock:
            return self._emit_event(kind, payload=payload)

    def list_events(self, limit: int = 100) -> List[CameraEvent]:
        """Return the most recent events, newest last.

        Args:
            limit: Maximum number of events to return.

        Returns:
            A list of CameraEvent records (up to ``limit``).
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
                "total_shots": len(self._shots),
                "active_shots": sum(
                    1
                    for s in self._shots.values()
                    if s.state == CameraState.ACTIVE
                ),
                "total_transitions": len(self._transitions),
                "total_sequences": len(self._sequences),
                "total_focus_pulls": len(self._focus_pulls),
                "total_events": len(self._events),
                "total_handlers": sum(
                    len(v) for v in self._event_handlers.values()
                ),
                "stats": stats,
            }

    def get_snapshot(self) -> CameraSnapshot:
        """Capture an immutable snapshot of the director state."""
        with self._lock:
            stats = self._compute_stats()
            return CameraSnapshot(
                active_shot_count=sum(
                    1
                    for s in self._shots.values()
                    if s.state == CameraState.ACTIVE
                ),
                sequence_count=len(self._sequences),
                total_shots=len(self._shots),
                stats=stats,
                timestamp=datetime.datetime.now(),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all shots, transitions, sequences, focus pulls, events,
        and handlers.

        Restores the director to its initial state, including the
        default seed cinematic data.
        """
        with self._lock:
            self._shots.clear()
            self._transitions.clear()
            self._sequences.clear()
            self._focus_pulls.clear()
            self._events.clear()
            self._event_handlers.clear()
            self._total_events_emitted = 0
            self._total_shots_created = 0
            self._total_shots_activated = 0
            self._total_transitions = 0
            self._total_sequences = 0
            self._total_focus_pulls = 0
            self._seed_default_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Populate the default cinematic shots, transitions, and sequence.

        Creates a small opening cinematic: an establishing wide shot, a
        medium dialogue shot, a close-up reaction shot, an over-shoulder
        shot, and an aerial shot. Two transitions (a hard cut and a
        dissolve) are wired between adjacent shots, and a single
        sequence chains the first three shots together for hands-off
        playback.
        """
        # 1. Establishing wide shot - high crane over the scene.
        establishing = CameraShot(
            name="Establishing Wide",
            shot_type=ShotType.ESTABLISHING,
            rig=CameraRig.CRANE,
            position=(0.0, 25.0, -40.0),
            look_at=(0.0, 5.0, 0.0),
            fov=75.0,
            duration=8.0,
            composition_rule=CompositionRule.RULE_OF_THIRDS,
            priority=0,
            state=CameraState.IDLE,
            metadata={"scene": "opening", "lens": "wide"},
        )
        self._shots[establishing.id] = establishing
        self._total_shots_created += 1
        self._emit_event(
            CameraEventKind.SHOT_CREATED,
            payload={
                "shot_id": establishing.id,
                "name": establishing.name,
                "shot_type": establishing.shot_type.value,
                "rig": establishing.rig.value,
            },
        )

        # 2. Medium dialogue shot - static framing of the conversation.
        medium = CameraShot(
            name="Medium Dialogue",
            shot_type=ShotType.MEDIUM,
            rig=CameraRig.STATIC,
            position=(6.0, 4.0, -10.0),
            look_at=(0.0, 3.0, 0.0),
            fov=50.0,
            duration=4.0,
            composition_rule=CompositionRule.CENTER,
            priority=1,
            state=CameraState.IDLE,
            metadata={"scene": "dialogue", "subject": "protagonist"},
        )
        self._shots[medium.id] = medium
        self._total_shots_created += 1
        self._emit_event(
            CameraEventKind.SHOT_CREATED,
            payload={
                "shot_id": medium.id,
                "name": medium.name,
                "shot_type": medium.shot_type.value,
                "rig": medium.rig.value,
            },
        )

        # 3. Close-up reaction shot - steadycam push on the face.
        close_up = CameraShot(
            name="Close-Up Reaction",
            shot_type=ShotType.CLOSE_UP,
            rig=CameraRig.STEADYCAM,
            position=(2.0, 3.5, -4.0),
            look_at=(0.0, 3.5, 0.0),
            fov=35.0,
            duration=2.5,
            composition_rule=CompositionRule.RULE_OF_THIRDS,
            priority=2,
            state=CameraState.IDLE,
            metadata={"scene": "dialogue", "subject": "face", "emotion": "shock"},
        )
        self._shots[close_up.id] = close_up
        self._total_shots_created += 1
        self._emit_event(
            CameraEventKind.SHOT_CREATED,
            payload={
                "shot_id": close_up.id,
                "name": close_up.name,
                "shot_type": close_up.shot_type.value,
                "rig": close_up.rig.value,
            },
        )

        # 4. Over-shoulder shot - dolly behind the second speaker.
        over_shoulder = CameraShot(
            name="Over-Shoulder",
            shot_type=ShotType.OVER_SHOULDER,
            rig=CameraRig.DOLLY,
            position=(-3.0, 4.0, -6.0),
            look_at=(2.0, 3.2, 0.0),
            fov=45.0,
            duration=5.0,
            composition_rule=CompositionRule.LEADING_LINES,
            priority=3,
            state=CameraState.IDLE,
            metadata={"scene": "dialogue", "subject": "companion"},
        )
        self._shots[over_shoulder.id] = over_shoulder
        self._total_shots_created += 1
        self._emit_event(
            CameraEventKind.SHOT_CREATED,
            payload={
                "shot_id": over_shoulder.id,
                "name": over_shoulder.name,
                "shot_type": over_shoulder.shot_type.value,
                "rig": over_shoulder.rig.value,
            },
        )

        # 5. Aerial shot - crane rise over the full scene.
        aerial = CameraShot(
            name="Aerial Reveal",
            shot_type=ShotType.AERIAL,
            rig=CameraRig.CRANE,
            position=(0.0, 60.0, -20.0),
            look_at=(0.0, 0.0, 0.0),
            fov=90.0,
            duration=6.0,
            composition_rule=CompositionRule.SYMMETRY,
            priority=4,
            state=CameraState.IDLE,
            metadata={"scene": "establishing", "lens": "ultra_wide"},
        )
        self._shots[aerial.id] = aerial
        self._total_shots_created += 1
        self._emit_event(
            CameraEventKind.SHOT_CREATED,
            payload={
                "shot_id": aerial.id,
                "name": aerial.name,
                "shot_type": aerial.shot_type.value,
                "rig": aerial.rig.value,
            },
        )

        # Transition 1: a hard cut from the establishing shot to the
        # medium dialogue shot.
        cut_transition = CameraTransition(
            from_shot_id=establishing.id,
            to_shot_id=medium.id,
            transition_type=TransitionType.CUT,
            duration=0.0,
            easing="linear",
        )
        self._transitions[cut_transition.id] = cut_transition

        # Transition 2: a dissolve from the medium dialogue shot to the
        # close-up reaction shot.
        dissolve_transition = CameraTransition(
            from_shot_id=medium.id,
            to_shot_id=close_up.id,
            transition_type=TransitionType.DISSOLVE,
            duration=1.5,
            easing="ease_in_out",
        )
        self._transitions[dissolve_transition.id] = dissolve_transition

        # Sequence: the opening cinematic chaining the establishing,
        # medium, and close-up shots together.
        opening_sequence = CameraSequence(
            name="Opening Sequence",
            description=(
                "The opening cinematic of the game: an establishing "
                "wide that pulls into a medium dialogue, resolving on "
                "a close-up reaction of the protagonist."
            ),
            shot_ids=[establishing.id, medium.id, close_up.id],
            current_index=-1,
            state=CameraState.IDLE,
            loop=False,
        )
        self._sequences[opening_sequence.id] = opening_sequence


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_camera_director() -> CameraDirectorEngine:
    """Return the singleton CameraDirectorEngine instance."""
    return CameraDirectorEngine.get_instance()
