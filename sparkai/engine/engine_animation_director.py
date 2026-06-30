"""
SparkLabs Engine - Animation Director

Engine-side animation state machine director that orchestrates skeletal
animations, blend trees, state transitions, and animation layers for game
entities. It provides director-level animation control similar to Unity's
Animator and Godot's AnimationTree - managing animation states, transitions
between them with gating conditions, parametric blend trees for procedural
movement, and layered animation for combining upper/lower body clips.

The animation director maintains a registry of animation clips, nodes (state
instances bound to a clip and layer), transitions between nodes, blend trees
that interpolate between child nodes based on a parameter, and layers that
combine animations additively or via override masks. Nodes progress through
the ``AnimationState`` lifecycle (IDLE -> PLAYING -> PAUSED / BLENDING ->
TRANSITIONING -> COMPLETED). When an entity enters a node, the director marks
the node active for that entity; transitions move an entity from one node to
another after evaluating gating conditions; blend trees recompute child
weights whenever their driving parameter changes.

This subsystem focuses on director-level state orchestration and blend
evaluation. Low-level skeletal pose integration and skinning is delegated to
the engine's animation controller; this module decides which clip is active
on which layer, how nodes transition, and how blend trees resolve their
children into weighted contributions.

Architecture:
  AnimationDirectorEngine (Singleton)
    |-- AnimationClip        (a skeletal animation clip with frame data)
    |-- AnimationNode        (a state node bound to a clip and a layer)
    |-- AnimationTransition  (a conditional blend between two nodes)
    |-- AnimationLayer       (a layered animation mask with a blend mode)
    |-- BlendTree            (a parametric blend of child nodes)
    |-- AnimationStats       (aggregate statistic counters)
    |-- AnimationSnapshot    (immutable snapshot of director state)
    |-- AnimationEvent       (an emitted director lifecycle event)

Lifecycle:
  1. create_clip(...)                          -> AnimationClip
  2. create_layer(...)                         -> AnimationLayer
  3. create_node(name, clip_id, layer_id, ...) -> AnimationNode
  4. create_transition(from, to, ...)          -> AnimationTransition
  5. create_blend_tree(name, parameter, ...)   -> BlendTree
  6. enter_state(entity_id, node_id)           -> AnimationNode
  7. trigger_transition(entity_id, transition_id) -> AnimationTransition
  8. evaluate_conditions(transition_id, params) -> bool
  9. update_blend(blend_tree_id, value)        -> Dict
 10. get_active_nodes(entity_id) / get_snapshot() / get_status() / reset()
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Capacity Constants
# =============================================================================

# Maximum number of registered entities of each kind before creation is
# refused. These bounds keep the director's memory footprint predictable
# even when driven by an agent generating large volumes of animation data.
_MAX_CLIPS: int = 2000
_MAX_NODES: int = 5000
_MAX_TRANSITIONS: int = 3000
_MAX_LAYERS: int = 500
_MAX_BLEND_TREES: int = 1000
_MAX_EVENTS: int = 2000

# Maximum number of concurrently registered event handlers across all
# event kinds. Keeps dispatch cost bounded.
_MAX_EVENT_HANDLERS: int = 64


# =============================================================================
# Enumerations
# =============================================================================


class AnimationState(Enum):
    """Lifecycle states for an animation node.

    Nodes begin in the ``IDLE`` state and progress to ``PLAYING`` once an
    entity enters them. A node may be ``PAUSED`` (frozen but resumable),
    ``BLENDING`` (contributing to a blend tree), ``TRANSITIONING`` (a
    transition is currently moving an entity away from the node), or
    ``COMPLETED`` (the clip has finished its playback window).
    """

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    BLENDING = "blending"
    TRANSITIONING = "transitioning"
    COMPLETED = "completed"


class BlendType(Enum):
    """The interpolation strategy used when blending between animations.

    ``NONE`` performs an instantaneous swap, ``LINEAR`` crossfades evenly,
    ``DIRECTIONAL`` selects a child based on a 2D direction (e.g. movement
    angle), ``MOTION`` interpolates along a 1D motion parameter (e.g.
    speed), and ``OVERRIDE`` lets the destination fully replace the source.
    """

    NONE = "none"
    LINEAR = "linear"
    DIRECTIONAL = "directional"
    MOTION = "motion"
    OVERRIDE = "override"


class LayerMode(Enum):
    """How an animation layer combines with the layers beneath it.

    ``BASE`` is the foundational full-body layer, ``ADDITIVE`` adds its
    pose on top of the accumulated pose (typically masked to a subset of
    bones), and ``OVERRIDE`` fully replaces the masked bones' poses.
    """

    BASE = "base"
    ADDITIVE = "additive"
    OVERRIDE = "override"


class LoopMode(Enum):
    """Playback looping behaviour for an animation clip.

    ``ONCE`` plays the clip a single time and then completes, ``LOOP``
    repeats it from the beginning indefinitely, and ``PINGPONG`` plays
    it forward then backward alternately.
    """

    ONCE = "once"
    LOOP = "loop"
    PINGPONG = "pingpong"


class AnimationEventKind(Enum):
    """Kinds of events emitted by the animation director."""

    CLIP_CREATED = "clip_created"
    STATE_CREATED = "state_created"
    TRANSITION_CREATED = "transition_created"
    STATE_ENTERED = "state_entered"
    STATE_EXITED = "state_exited"
    BLEND_UPDATED = "blend_updated"
    LAYER_CREATED = "layer_created"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class AnimationClip:
    """A skeletal animation clip with sampled frame data.

    A clip describes a piece of authored animation - its duration, the
    frame rate it was sampled at, the total number of frames, the looping
    behaviour, and the per-frame skeletal data (bone transforms). Clips are
    referenced by animation nodes; a single clip may be shared across many
    nodes and layers.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name of the clip.
        duration: Total length of the clip in seconds.
        fps: Sample rate the clip was authored at (frames per second).
        loop_mode: Looping behaviour when the clip plays.
        frame_count: Total number of sampled frames in the clip.
        skeletal_data: Per-frame bone transform data (free-form).
        metadata: Free-form extension data.
        timestamp: Time at which the clip was created.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    duration: float = 0.0
    fps: float = 30.0
    loop_mode: LoopMode = LoopMode.ONCE
    frame_count: int = 0
    skeletal_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "duration": self.duration,
            "fps": self.fps,
            "loop_mode": self.loop_mode.value,
            "frame_count": self.frame_count,
            "skeletal_data": dict(self.skeletal_data),
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class AnimationNode:
    """A state node bound to an animation clip and a layer.

    A node is an instance of an animation clip within the state machine.
    It carries a playback speed multiplier, a blend weight (0.0-1.0), the
    blend type to use when transitioning into it, a 2D position used by
    directional blend trees, and the identifier of the layer it belongs
    to. Nodes progress through the ``AnimationState`` lifecycle as the
    director enters, transitions between, and exits them.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name of the node.
        clip_id: Identifier of the clip this node plays.
        state: Current lifecycle state.
        speed: Playback speed multiplier (1.0 = authored speed).
        weight: Blend weight in the range 0.0 to 1.0.
        blend_type: Blend strategy used when entering this node.
        position: 2D position ``(x, y)`` for directional blend trees.
        layer_id: Identifier of the layer this node belongs to.
        metadata: Free-form extension data.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    clip_id: str = ""
    state: AnimationState = AnimationState.IDLE
    speed: float = 1.0
    weight: float = 1.0
    blend_type: BlendType = BlendType.NONE
    position: Tuple[float, float] = (0.0, 0.0)
    layer_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "clip_id": self.clip_id,
            "state": self.state.value,
            "speed": self.speed,
            "weight": self.weight,
            "blend_type": self.blend_type.value,
            "position": list(self.position),
            "layer_id": self.layer_id,
            "metadata": dict(self.metadata),
        }


@dataclass
class AnimationTransition:
    """A conditional blend that moves an entity between two nodes.

    Transitions are created between two existing nodes and are executed on
    demand for a specific entity. Executing a transition exits the source
    node, enters the destination node, and records the start and completion
    timestamps. A transition only fires when all of its gating conditions
    evaluate to true against the supplied parameters.

    Attributes:
        id: Unique identifier (auto-generated).
        from_node_id: Identifier of the source node.
        to_node_id: Identifier of the destination node.
        duration: Blend length in seconds.
        blend_type: Blend strategy used for the crossfade.
        conditions: List of condition dicts (``param``, ``op``, ``value``).
        priority: Ordering priority (lower values fire earlier).
        started_at: Timestamp when execution began.
        completed_at: Timestamp when execution finished.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_node_id: str = ""
    to_node_id: str = ""
    duration: float = 0.0
    blend_type: BlendType = BlendType.LINEAR
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    priority: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "duration": self.duration,
            "blend_type": self.blend_type.value,
            "conditions": [dict(c) for c in self.conditions],
            "priority": self.priority,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class AnimationLayer:
    """A layered animation mask with a blend mode.

    Layers allow multiple animations to contribute to the final pose at
    once. The ``BASE`` layer carries the full-body animation, while
    ``ADDITIVE`` and ``OVERRIDE`` layers affect only the bones listed in
    their mask. Layers have an independent weight (0.0-1.0) and track the
    currently active node for the layer.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name of the layer.
        mode: How the layer combines with layers beneath it.
        weight: Layer weight in the range 0.0 to 1.0.
        mask: List of bone names the layer is allowed to affect.
        active_node_id: Identifier of the layer's currently active node.
        enabled: Whether the layer contributes to the pose.
        metadata: Free-form extension data.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    mode: LayerMode = LayerMode.BASE
    weight: float = 1.0
    mask: List[str] = field(default_factory=list)
    active_node_id: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode.value,
            "weight": self.weight,
            "mask": list(self.mask),
            "active_node_id": self.active_node_id,
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


@dataclass
class BlendTree:
    """A parametric blend of child nodes driven by a single parameter.

    A blend tree interpolates between its child nodes based on the value
    of a named parameter. Each child carries a threshold (the parameter
    value at which the child is fully weighted) and a 2D position used by
    directional blends. Updating the blend tree with a new parameter value
    recomputes the per-child weights.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name of the blend tree.
        parameter: Name of the driving parameter.
        children: List of child descriptors (``node_id``, ``threshold``,
            ``position``).
        min_threshold: Lower bound of the parameter range.
        max_threshold: Upper bound of the parameter range.
        blend_type: Blend strategy used to combine children.
        current_value: Most recently applied parameter value.
        child_weights: Last computed weight per child node id.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    parameter: str = ""
    children: List[Dict[str, Any]] = field(default_factory=list)
    min_threshold: float = 0.0
    max_threshold: float = 1.0
    blend_type: BlendType = BlendType.MOTION
    current_value: float = 0.0
    child_weights: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parameter": self.parameter,
            "children": [dict(c) for c in self.children],
            "min_threshold": self.min_threshold,
            "max_threshold": self.max_threshold,
            "blend_type": self.blend_type.value,
            "current_value": self.current_value,
            "child_weights": dict(self.child_weights),
        }


@dataclass
class AnimationStats:
    """Aggregate statistic counters for the animation director.

    Attributes:
        total_clips: Lifetime count of clips created.
        total_nodes: Lifetime count of nodes created.
        total_transitions: Lifetime count of transitions created.
        total_layers: Lifetime count of layers created.
        total_blend_trees: Lifetime count of blend trees created.
        active_animations: Number of nodes currently in the PLAYING state.
        last_updated: Timestamp of the most recent counter update.
    """

    total_clips: int = 0
    total_nodes: int = 0
    total_transitions: int = 0
    total_layers: int = 0
    total_blend_trees: int = 0
    active_animations: int = 0
    last_updated: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_clips": self.total_clips,
            "total_nodes": self.total_nodes,
            "total_transitions": self.total_transitions,
            "total_layers": self.total_layers,
            "total_blend_trees": self.total_blend_trees,
            "active_animations": self.active_animations,
            "last_updated": self.last_updated,
        }


@dataclass
class AnimationSnapshot:
    """An immutable snapshot of the animation director state.

    Attributes:
        active_node_count: Number of nodes currently in the PLAYING state.
        layer_count: Total number of registered layers.
        total_clips: Total number of registered clips.
        total_nodes: Total number of registered nodes.
        stats: Aggregated statistic counters.
        timestamp: Time at which the snapshot was taken.
    """

    active_node_count: int = 0
    layer_count: int = 0
    total_clips: int = 0
    total_nodes: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_node_count": self.active_node_count,
            "layer_count": self.layer_count,
            "total_clips": self.total_clips,
            "total_nodes": self.total_nodes,
            "stats": dict(self.stats),
            "timestamp": self.timestamp,
        }


@dataclass
class AnimationEvent:
    """An immutable record of an animation director lifecycle event.

    Attributes:
        id: Unique identifier (auto-generated).
        kind: The ``AnimationEventKind`` of the event.
        entity_id: Identifier of the entity the event concerns, if any.
        payload: Free-form payload describing the event.
        timestamp: Time at which the event was emitted.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: AnimationEventKind = AnimationEventKind.CLIP_CREATED
    entity_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "entity_id": self.entity_id,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


# =============================================================================
# Animation Director Engine (Singleton)
# =============================================================================


class AnimationDirectorEngine:
    """Engine-side animation state machine director.

    Maintains a registry of animation clips, nodes, transitions, layers,
    and blend trees. Coordinates node activation through the
    ``AnimationState`` lifecycle, evaluates transition conditions against
    supplied parameters, recomputes blend tree weights when their driving
    parameter changes, and emits lifecycle events to subscribed handlers.

    All public methods are thread-safe. The class implements the singleton
    pattern with double-checked locking; consumers should obtain the
    instance through :meth:`get_instance` or :func:`get_animation_director`.
    """

    _instance: Optional["AnimationDirectorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "AnimationDirectorEngine":
        # Double-checked locking singleton. ``__new__`` allocates the
        # instance and marks it uninitialized; ``__init__`` performs the
        # one-time setup guarded by that flag.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AnimationDirectorEngine":
        """Return the singleton AnimationDirectorEngine instance (thread-safe).

        This does not reset ``_initialized``; the one-time setup performed
        by ``__init__`` is therefore idempotent across repeated calls.
        """
        return cls()

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton. The flag is
        # set to True at the very start so a recursive call into __init__
        # during seeding cannot re-enter setup.
        if self._initialized:
            return
        self._initialized: bool = True

        # Primary registries.
        self._clips: Dict[str, AnimationClip] = {}
        self._nodes: Dict[str, AnimationNode] = {}
        self._transitions: Dict[str, AnimationTransition] = {}
        self._layers: Dict[str, AnimationLayer] = {}
        self._blend_trees: Dict[str, BlendTree] = {}

        # Per-entity active node tracking. Maps an entity id to the list
        # of node ids currently active (PLAYING) for that entity.
        self._entity_active_nodes: Dict[str, List[str]] = {}

        # Event log and subscriber registry. Handlers are stored both in
        # a kind-keyed dispatch map and in a handler-id registry so that
        # individual handlers can be unregistered by id.
        self._events: List[AnimationEvent] = []
        self._event_handlers: Dict[str, List[Callable[[AnimationEvent], None]]] = {}
        self._handler_registry: Dict[
            str, Tuple[str, Callable[[AnimationEvent], None]]
        ] = {}
        self._total_events_emitted: int = 0

        # Aggregate statistic counters (lifetime totals).
        self._total_clips: int = 0
        self._total_nodes: int = 0
        self._total_transitions: int = 0
        self._total_layers: int = 0
        self._total_blend_trees: int = 0

        # Populate the default seed animation data.
        self._seed_default_data()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_kind(kind: Any) -> str:
        """Normalize an event kind argument to its string value.

        ``None`` maps to the wildcard ``"*"`` so a handler subscribed with
        ``None`` receives every event kind.
        """
        if kind is None:
            return "*"
        if isinstance(kind, AnimationEventKind):
            return kind.value
        return str(kind)

    def _dispatch_event(self, event: AnimationEvent) -> None:
        """Deliver an event to all matching registered handlers.

        Handlers subscribed to the event's kind and handlers subscribed
        to the wildcard ``"*"`` are both invoked. A failing handler is
        silently skipped so a single bad handler cannot break dispatch.
        """
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
        kind: AnimationEventKind,
        entity_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> AnimationEvent:
        """Create, log, and dispatch an animation event (internal use only).

        The event log is capped at ``_MAX_EVENTS`` entries; the oldest
        entries are evicted when the cap is exceeded.
        """
        event = AnimationEvent(
            kind=kind,
            entity_id=entity_id,
            payload=payload or {},
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            del self._events[: len(self._events) - _MAX_EVENTS]
        self._total_events_emitted += 1
        self._dispatch_event(event)
        return event

    def _count_active_nodes(self) -> int:
        """Return the number of nodes currently in the PLAYING state."""
        return sum(
            1 for n in self._nodes.values() if n.state == AnimationState.PLAYING
        )

    def _compute_stats(self) -> Dict[str, Any]:
        """Compute the aggregate statistic counters from current state."""
        return {
            "total_clips": self._total_clips,
            "total_nodes": self._total_nodes,
            "total_transitions": self._total_transitions,
            "total_layers": self._total_layers,
            "total_blend_trees": self._total_blend_trees,
            "active_animations": self._count_active_nodes(),
            "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        }

    # ------------------------------------------------------------------
    # Clip management
    # ------------------------------------------------------------------

    def create_clip(
        self,
        name: str,
        duration: float,
        fps: float = 30.0,
        loop_mode: LoopMode = LoopMode.ONCE,
        frame_count: int = 0,
        skeletal_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AnimationClip:
        """Create and register a new animation clip.

        Args:
            name: Human-readable name of the clip.
            duration: Total length of the clip in seconds.
            fps: Sample rate the clip was authored at (frames per second).
            loop_mode: Looping behaviour when the clip plays.
            frame_count: Total number of sampled frames in the clip.
            skeletal_data: Per-frame bone transform data (free-form).
            metadata: Free-form extension data.

        Returns:
            The newly created AnimationClip.

        Raises:
            ValueError: If the clip capacity (``_MAX_CLIPS``) has been
                reached or the duration is negative.
        """
        with self._lock:
            if len(self._clips) >= _MAX_CLIPS:
                raise ValueError(
                    f"Clip capacity reached ({_MAX_CLIPS})"
                )
            if duration < 0:
                raise ValueError(
                    f"Clip duration must be non-negative: {duration}"
                )
            clip = AnimationClip(
                name=name,
                duration=duration,
                fps=fps,
                loop_mode=loop_mode,
                frame_count=frame_count,
                skeletal_data=dict(skeletal_data) if skeletal_data else {},
                metadata=dict(metadata) if metadata else {},
            )
            self._clips[clip.id] = clip
            self._total_clips += 1
            self._emit_event(
                AnimationEventKind.CLIP_CREATED,
                payload={
                    "clip_id": clip.id,
                    "name": clip.name,
                    "duration": clip.duration,
                    "loop_mode": clip.loop_mode.value,
                },
            )
            return clip

    def get_clip(self, clip_id: str) -> Optional[AnimationClip]:
        """Retrieve a clip by its identifier."""
        with self._lock:
            return self._clips.get(clip_id)

    def list_clips(self) -> List[AnimationClip]:
        """Return all registered clips sorted by name then id."""
        with self._lock:
            clips = list(self._clips.values())
            clips.sort(key=lambda c: (c.name, c.id))
            return clips

    def remove_clip(self, clip_id: str) -> bool:
        """Remove a clip from the director.

        Nodes that reference the removed clip are left in place; callers
        should rebind or remove such nodes explicitly.

        Returns:
            True if the clip was removed, False if it was not found.
        """
        with self._lock:
            if clip_id not in self._clips:
                return False
            del self._clips[clip_id]
            return True

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    def create_layer(
        self,
        name: str,
        mode: LayerMode = LayerMode.BASE,
        weight: float = 1.0,
        mask: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AnimationLayer:
        """Create and register a new animation layer.

        Args:
            name: Human-readable name of the layer.
            mode: How the layer combines with layers beneath it.
            weight: Layer weight in the range 0.0 to 1.0.
            mask: List of bone names the layer is allowed to affect.
            metadata: Free-form extension data.

        Returns:
            The newly created AnimationLayer.

        Raises:
            ValueError: If the layer capacity (``_MAX_LAYERS``) has been
                reached.
        """
        with self._lock:
            if len(self._layers) >= _MAX_LAYERS:
                raise ValueError(
                    f"Layer capacity reached ({_MAX_LAYERS})"
                )
            layer = AnimationLayer(
                name=name,
                mode=mode,
                weight=max(0.0, min(1.0, weight)),
                mask=list(mask) if mask else [],
                metadata=dict(metadata) if metadata else {},
            )
            self._layers[layer.id] = layer
            self._total_layers += 1
            self._emit_event(
                AnimationEventKind.LAYER_CREATED,
                payload={
                    "layer_id": layer.id,
                    "name": layer.name,
                    "mode": layer.mode.value,
                    "weight": layer.weight,
                },
            )
            return layer

    def get_layer(self, layer_id: str) -> Optional[AnimationLayer]:
        """Retrieve a layer by its identifier."""
        with self._lock:
            return self._layers.get(layer_id)

    def list_layers(self) -> List[AnimationLayer]:
        """Return all registered layers sorted by name then id."""
        with self._lock:
            layers = list(self._layers.values())
            layers.sort(key=lambda l: (l.name, l.id))
            return layers

    def remove_layer(self, layer_id: str) -> bool:
        """Remove a layer from the director.

        Nodes that reference the removed layer are left in place; callers
        should rebind or remove such nodes explicitly.

        Returns:
            True if the layer was removed, False if it was not found.
        """
        with self._lock:
            if layer_id not in self._layers:
                return False
            del self._layers[layer_id]
            return True

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def create_node(
        self,
        name: str,
        clip_id: str,
        layer_id: str,
        speed: float = 1.0,
        weight: float = 1.0,
        blend_type: BlendType = BlendType.NONE,
        position: Tuple[float, float] = (0.0, 0.0),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AnimationNode:
        """Create and register a new animation node.

        Args:
            name: Human-readable name of the node.
            clip_id: Identifier of the clip this node plays.
            layer_id: Identifier of the layer this node belongs to.
            speed: Playback speed multiplier (1.0 = authored speed).
            weight: Blend weight in the range 0.0 to 1.0.
            blend_type: Blend strategy used when entering this node.
            position: 2D position ``(x, y)`` for directional blend trees.
            metadata: Free-form extension data.

        Returns:
            The newly created AnimationNode.

        Raises:
            ValueError: If the node capacity (``_MAX_NODES``) has been
                reached, or the referenced clip or layer does not exist.
        """
        with self._lock:
            if len(self._nodes) >= _MAX_NODES:
                raise ValueError(
                    f"Node capacity reached ({_MAX_NODES})"
                )
            if clip_id not in self._clips:
                raise ValueError(f"Clip not found: {clip_id}")
            if layer_id not in self._layers:
                raise ValueError(f"Layer not found: {layer_id}")
            node = AnimationNode(
                name=name,
                clip_id=clip_id,
                layer_id=layer_id,
                state=AnimationState.IDLE,
                speed=speed,
                weight=max(0.0, min(1.0, weight)),
                blend_type=blend_type,
                position=tuple(position),
                metadata=dict(metadata) if metadata else {},
            )
            self._nodes[node.id] = node
            self._total_nodes += 1
            self._emit_event(
                AnimationEventKind.STATE_CREATED,
                payload={
                    "node_id": node.id,
                    "name": node.name,
                    "clip_id": node.clip_id,
                    "layer_id": node.layer_id,
                },
            )
            return node

    def get_node(self, node_id: str) -> Optional[AnimationNode]:
        """Retrieve a node by its identifier."""
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self, layer_id: Optional[str] = None) -> List[AnimationNode]:
        """List nodes, optionally filtered by layer.

        The returned list is sorted by name then id.

        Args:
            layer_id: When provided, restrict the result to nodes that
                belong to the given layer.
        """
        with self._lock:
            nodes = list(self._nodes.values())
            if layer_id is not None:
                nodes = [n for n in nodes if n.layer_id == layer_id]
            nodes.sort(key=lambda n: (n.name, n.id))
            return nodes

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the director.

        The node is also detached from any entity's active node list and
        cleared from the active slot of any layer that held it.

        Returns:
            True if the node was removed, False if it was not found.
        """
        with self._lock:
            if node_id not in self._nodes:
                return False
            del self._nodes[node_id]
            for active in self._entity_active_nodes.values():
                if node_id in active:
                    active[:] = [n for n in active if n != node_id]
            for layer in self._layers.values():
                if layer.active_node_id == node_id:
                    layer.active_node_id = None
            return True

    # ------------------------------------------------------------------
    # Transition management
    # ------------------------------------------------------------------

    def create_transition(
        self,
        from_node_id: str,
        to_node_id: str,
        duration: float = 0.0,
        blend_type: BlendType = BlendType.LINEAR,
        conditions: Optional[List[Dict[str, Any]]] = None,
        priority: int = 0,
    ) -> AnimationTransition:
        """Create a transition between two existing nodes.

        Args:
            from_node_id: Identifier of the source node.
            to_node_id: Identifier of the destination node.
            duration: Blend length in seconds.
            blend_type: Blend strategy used for the crossfade.
            conditions: List of condition dicts (``param``, ``op``,
                ``value``). All conditions must hold for the transition
                to fire.
            priority: Ordering priority (lower values fire earlier).

        Returns:
            The newly created AnimationTransition.

        Raises:
            ValueError: If the transition capacity (``_MAX_TRANSITIONS``)
                has been reached, either node does not exist, the two
                nodes are the same, or the duration is negative.
        """
        with self._lock:
            if len(self._transitions) >= _MAX_TRANSITIONS:
                raise ValueError(
                    f"Transition capacity reached ({_MAX_TRANSITIONS})"
                )
            if from_node_id not in self._nodes:
                raise ValueError(f"Source node not found: {from_node_id}")
            if to_node_id not in self._nodes:
                raise ValueError(f"Destination node not found: {to_node_id}")
            if from_node_id == to_node_id:
                raise ValueError(
                    "Cannot transition a node to itself: "
                    f"{from_node_id}"
                )
            if duration < 0:
                raise ValueError(
                    f"Transition duration must be non-negative: {duration}"
                )
            transition = AnimationTransition(
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                duration=duration,
                blend_type=blend_type,
                conditions=[dict(c) for c in conditions] if conditions else [],
                priority=priority,
            )
            self._transitions[transition.id] = transition
            self._total_transitions += 1
            self._emit_event(
                AnimationEventKind.TRANSITION_CREATED,
                payload={
                    "transition_id": transition.id,
                    "from_node_id": transition.from_node_id,
                    "to_node_id": transition.to_node_id,
                    "blend_type": transition.blend_type.value,
                },
            )
            return transition

    def get_transition(self, transition_id: str) -> Optional[AnimationTransition]:
        """Retrieve a transition by its identifier."""
        with self._lock:
            return self._transitions.get(transition_id)

    def list_transitions(
        self,
        from_node_id: Optional[str] = None,
        to_node_id: Optional[str] = None,
    ) -> List[AnimationTransition]:
        """List transitions, optionally filtered by endpoint.

        When both ``from_node_id`` and ``to_node_id`` are provided the
        result is restricted to transitions matching both endpoints. The
        returned list is sorted by ascending priority then id.

        Args:
            from_node_id: When provided, restrict to transitions whose
                source node matches.
            to_node_id: When provided, restrict to transitions whose
                destination node matches.
        """
        with self._lock:
            transitions = list(self._transitions.values())
            if from_node_id is not None:
                transitions = [
                    t for t in transitions if t.from_node_id == from_node_id
                ]
            if to_node_id is not None:
                transitions = [
                    t for t in transitions if t.to_node_id == to_node_id
                ]
            transitions.sort(key=lambda t: (t.priority, t.id))
            return transitions

    def remove_transition(self, transition_id: str) -> bool:
        """Remove a transition from the director.

        Returns:
            True if the transition was removed, False if it was not found.
        """
        with self._lock:
            if transition_id not in self._transitions:
                return False
            del self._transitions[transition_id]
            return True

    # ------------------------------------------------------------------
    # Blend tree management
    # ------------------------------------------------------------------

    def create_blend_tree(
        self,
        name: str,
        parameter: str,
        children: Optional[List[Dict[str, Any]]] = None,
        min_threshold: float = 0.0,
        max_threshold: float = 1.0,
        blend_type: BlendType = BlendType.MOTION,
    ) -> BlendTree:
        """Create and register a new blend tree.

        Each child descriptor should carry a ``node_id`` (referencing a
        registered node), a ``threshold`` (the parameter value at which
        the child is fully weighted), and an optional ``position``
        (a 2D ``(x, y)`` used by directional blends).

        Args:
            name: Human-readable name of the blend tree.
            parameter: Name of the driving parameter.
            children: List of child descriptors.
            min_threshold: Lower bound of the parameter range.
            max_threshold: Upper bound of the parameter range.
            blend_type: Blend strategy used to combine children.

        Returns:
            The newly created BlendTree.

        Raises:
            ValueError: If the blend tree capacity (``_MAX_BLEND_TREES``)
                has been reached or the threshold range is inverted.
        """
        with self._lock:
            if len(self._blend_trees) >= _MAX_BLEND_TREES:
                raise ValueError(
                    f"Blend tree capacity reached ({_MAX_BLEND_TREES})"
                )
            if max_threshold < min_threshold:
                raise ValueError(
                    "max_threshold must be >= min_threshold: "
                    f"{min_threshold} > {max_threshold}"
                )
            tree = BlendTree(
                name=name,
                parameter=parameter,
                children=[dict(c) for c in children] if children else [],
                min_threshold=min_threshold,
                max_threshold=max_threshold,
                blend_type=blend_type,
            )
            self._blend_trees[tree.id] = tree
            self._total_blend_trees += 1
            return tree

    def get_blend_tree(self, blend_tree_id: str) -> Optional[BlendTree]:
        """Retrieve a blend tree by its identifier."""
        with self._lock:
            return self._blend_trees.get(blend_tree_id)

    def list_blend_trees(self) -> List[BlendTree]:
        """Return all registered blend trees sorted by name then id."""
        with self._lock:
            trees = list(self._blend_trees.values())
            trees.sort(key=lambda t: (t.name, t.id))
            return trees

    def remove_blend_tree(self, blend_tree_id: str) -> bool:
        """Remove a blend tree from the director.

        Returns:
            True if the blend tree was removed, False if it was not found.
        """
        with self._lock:
            if blend_tree_id not in self._blend_trees:
                return False
            del self._blend_trees[blend_tree_id]
            return True

    # ------------------------------------------------------------------
    # State machine operations
    # ------------------------------------------------------------------

    def enter_state(
        self,
        entity_id: str,
        node_id: str,
    ) -> Optional[AnimationNode]:
        """Enter a state node for the given entity.

        Marks the node as ``PLAYING``, records it in the entity's active
        node list, and updates the node's layer's active node slot. A node
        already in the ``PLAYING`` state for this entity is a no-op.

        Args:
            entity_id: Identifier of the entity entering the state.
            node_id: Identifier of the node to enter.

        Returns:
            The entered AnimationNode, or None if the node was not found.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return None
            active = self._entity_active_nodes.setdefault(entity_id, [])
            if node_id not in active:
                active.append(node_id)
            node.state = AnimationState.PLAYING
            layer = self._layers.get(node.layer_id)
            if layer is not None:
                layer.active_node_id = node_id
            self._emit_event(
                AnimationEventKind.STATE_ENTERED,
                entity_id=entity_id,
                payload={
                    "node_id": node.id,
                    "name": node.name,
                    "clip_id": node.clip_id,
                    "layer_id": node.layer_id,
                },
            )
            return node

    def exit_state(
        self,
        entity_id: str,
        node_id: str,
    ) -> Optional[AnimationNode]:
        """Exit a state node for the given entity.

        Removes the node from the entity's active node list and resets
        the node to the ``IDLE`` state so it can be re-entered later.

        Args:
            entity_id: Identifier of the entity exiting the state.
            node_id: Identifier of the node to exit.

        Returns:
            The exited AnimationNode, or None if the node was not found.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return None
            active = self._entity_active_nodes.get(entity_id)
            if active and node_id in active:
                active[:] = [n for n in active if n != node_id]
            node.state = AnimationState.IDLE
            layer = self._layers.get(node.layer_id)
            if layer is not None and layer.active_node_id == node_id:
                layer.active_node_id = None
            self._emit_event(
                AnimationEventKind.STATE_EXITED,
                entity_id=entity_id,
                payload={
                    "node_id": node.id,
                    "name": node.name,
                    "clip_id": node.clip_id,
                    "layer_id": node.layer_id,
                },
            )
            return node

    def trigger_transition(
        self,
        entity_id: str,
        transition_id: str,
    ) -> Optional[AnimationTransition]:
        """Execute a previously created transition for an entity.

        Marks the source node as ``TRANSITIONING`` then ``IDLE``, marks
        the destination node as ``PLAYING``, updates the entity's active
        node list and the destination layer's active slot, and records
        the transition start and completion timestamps.

        Args:
            entity_id: Identifier of the entity performing the transition.
            transition_id: Identifier of the transition to execute.

        Returns:
            The executed AnimationTransition, or None if it was not found
            or references a missing node.
        """
        with self._lock:
            transition = self._transitions.get(transition_id)
            if transition is None:
                return None
            from_node = self._nodes.get(transition.from_node_id)
            to_node = self._nodes.get(transition.to_node_id)
            if from_node is None or to_node is None:
                return None

            transition.started_at = datetime.datetime.utcnow().isoformat() + "Z"

            # Mark the source node as transitioning and remove it from
            # the entity's active set.
            from_node.state = AnimationState.TRANSITIONING
            active = self._entity_active_nodes.setdefault(entity_id, [])
            if transition.from_node_id in active:
                active[:] = [n for n in active if n != transition.from_node_id]

            # Activate the destination node for the entity.
            if transition.to_node_id not in active:
                active.append(transition.to_node_id)
            to_node.state = AnimationState.PLAYING
            dest_layer = self._layers.get(to_node.layer_id)
            if dest_layer is not None:
                dest_layer.active_node_id = transition.to_node_id

            # Reset the source node to idle so it can be re-entered, and
            # clear its layer's active slot if it held it.
            from_node.state = AnimationState.IDLE
            src_layer = self._layers.get(from_node.layer_id)
            if src_layer is not None and src_layer.active_node_id == transition.from_node_id:
                src_layer.active_node_id = None

            transition.completed_at = (
                datetime.datetime.utcnow().isoformat() + "Z"
            )
            self._emit_event(
                AnimationEventKind.STATE_EXITED,
                entity_id=entity_id,
                payload={
                    "node_id": from_node.id,
                    "transition_id": transition.id,
                    "layer_id": from_node.layer_id,
                },
            )
            self._emit_event(
                AnimationEventKind.STATE_ENTERED,
                entity_id=entity_id,
                payload={
                    "node_id": to_node.id,
                    "transition_id": transition.id,
                    "layer_id": to_node.layer_id,
                },
            )
            return transition

    def evaluate_conditions(
        self,
        transition_id: str,
        parameters: Dict[str, Any],
    ) -> bool:
        """Evaluate a transition's conditions against supplied parameters.

        Each condition is a dict with keys ``param``, ``op``, and
        ``value``. Supported operators are ``>``, ``<``, ``>=``, ``<=``,
        ``==``, and ``!=``. A transition with no conditions evaluates to
        true. A missing parameter causes the condition (and thus the
        evaluation) to fail.

        Args:
            transition_id: Identifier of the transition to evaluate.
            parameters: Mapping of parameter names to their current values.

        Returns:
            True if all conditions hold (or there are none), False if the
            transition was not found or any condition fails.
        """
        with self._lock:
            transition = self._transitions.get(transition_id)
            if transition is None:
                return False
            if not transition.conditions:
                return True
            params = parameters or {}
            for condition in transition.conditions:
                param = condition.get("param")
                op = condition.get("op")
                threshold = condition.get("value")
                if param is None or op is None or threshold is None:
                    return False
                actual = params.get(param)
                if actual is None:
                    return False
                try:
                    if op == ">":
                        ok = actual > threshold
                    elif op == "<":
                        ok = actual < threshold
                    elif op == ">=":
                        ok = actual >= threshold
                    elif op == "<=":
                        ok = actual <= threshold
                    elif op == "==":
                        ok = actual == threshold
                    elif op == "!=":
                        ok = actual != threshold
                    else:
                        # Unknown operator fails the evaluation safely.
                        return False
                except TypeError:
                    return False
                if not ok:
                    return False
            return True

    def update_blend(self, blend_tree_id: str, value: float) -> Dict[str, Any]:
        """Update a blend tree's driving parameter and recompute child weights.

        For a 1D (``MOTION`` / ``LINEAR``) blend tree the children's
        thresholds define a piecewise-linear weight curve: the two
        children whose thresholds bracket ``value`` receive complementary
        weights and all other children receive zero. For ``DIRECTIONAL``
        blends the 2D child positions are used and each child receives an
        inverse-distance weight. ``NONE`` assigns full weight to the
        nearest child. ``OVERRIDE`` assigns full weight to the last child
        whose threshold is <= ``value``.

        Args:
            blend_tree_id: Identifier of the blend tree to update.
            value: New value of the driving parameter.

        Returns:
            A dict describing the result, including ``blend_tree_id``,
            ``parameter``, ``value``, and ``child_weights`` (a mapping of
            node id to weight). Returns an empty dict if the blend tree
            was not found.
        """
        with self._lock:
            tree = self._blend_trees.get(blend_tree_id)
            if tree is None:
                return {}
            # Clamp the value to the tree's declared range.
            clamped = max(tree.min_threshold, min(tree.max_threshold, value))
            tree.current_value = clamped
            weights: Dict[str, float] = {}
            children = list(tree.children)
            if not children:
                tree.child_weights = weights
                self._emit_event(
                    AnimationEventKind.BLEND_UPDATED,
                    payload={
                        "blend_tree_id": tree.id,
                        "parameter": tree.parameter,
                        "value": clamped,
                        "child_weights": dict(weights),
                    },
                )
                return {
                    "blend_tree_id": tree.id,
                    "parameter": tree.parameter,
                    "value": clamped,
                    "child_weights": dict(weights),
                }

            if tree.blend_type in (BlendType.MOTION, BlendType.LINEAR):
                # Sort children by threshold for the piecewise lookup.
                ordered = sorted(
                    children, key=lambda c: float(c.get("threshold", 0.0))
                )
                # Find the bracketing pair.
                lower = ordered[0]
                upper = ordered[-1]
                for i in range(len(ordered) - 1):
                    lo_t = float(ordered[i].get("threshold", 0.0))
                    hi_t = float(ordered[i + 1].get("threshold", 0.0))
                    if lo_t <= clamped <= hi_t:
                        lower = ordered[i]
                        upper = ordered[i + 1]
                        break
                lo_t = float(lower.get("threshold", 0.0))
                hi_t = float(upper.get("threshold", 0.0))
                lo_id = lower.get("node_id")
                hi_id = upper.get("node_id")
                if hi_t == lo_t:
                    # Degenerate bracket: give full weight to the lower.
                    for c in ordered:
                        weights[c.get("node_id")] = 0.0
                    weights[lo_id] = 1.0
                else:
                    t = (clamped - lo_t) / (hi_t - lo_t)
                    for c in ordered:
                        weights[c.get("node_id")] = 0.0
                    weights[lo_id] = max(0.0, 1.0 - t)
                    weights[hi_id] = max(0.0, t)
            elif tree.blend_type == BlendType.DIRECTIONAL:
                # Inverse-distance weighting against 2D child positions.
                vx, vy = clamped, 0.0
                inv_dists: List[Tuple[str, float]] = []
                for c in children:
                    pos = c.get("position", (0.0, 0.0))
                    try:
                        cx = float(pos[0])
                        cy = float(pos[1]) if len(pos) > 1 else 0.0
                    except (TypeError, IndexError):
                        cx, cy = 0.0, 0.0
                    dx = vx - cx
                    dy = vy - cy
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist < 1e-6:
                        inv_dists.append((c.get("node_id"), float("inf")))
                    else:
                        inv_dists.append((c.get("node_id"), 1.0 / dist))
                total = sum(
                    w for _, w in inv_dists if w != float("inf")
                )
                has_exact = any(w == float("inf") for _, w in inv_dists)
                if has_exact:
                    for nid, w in inv_dists:
                        weights[nid] = 1.0 if w == float("inf") else 0.0
                elif total > 0:
                    for nid, w in inv_dists:
                        weights[nid] = w / total
                else:
                    share = 1.0 / len(inv_dists)
                    for nid, _ in inv_dists:
                        weights[nid] = share
            elif tree.blend_type == BlendType.OVERRIDE:
                # Full weight to the last child whose threshold <= value.
                ordered = sorted(
                    children, key=lambda c: float(c.get("threshold", 0.0))
                )
                winner = ordered[0]
                for c in ordered:
                    if float(c.get("threshold", 0.0)) <= clamped:
                        winner = c
                for c in ordered:
                    weights[c.get("node_id")] = (
                        1.0 if c is winner else 0.0
                    )
            else:  # BlendType.NONE or unknown - nearest child wins.
                ordered = sorted(
                    children, key=lambda c: float(c.get("threshold", 0.0))
                )
                nearest = ordered[0]
                best_delta = abs(
                    float(nearest.get("threshold", 0.0)) - clamped
                )
                for c in ordered[1:]:
                    delta = abs(float(c.get("threshold", 0.0)) - clamped)
                    if delta < best_delta:
                        best_delta = delta
                        nearest = c
                for c in ordered:
                    weights[c.get("node_id")] = (
                        1.0 if c is nearest else 0.0
                    )

            tree.child_weights = weights
            self._emit_event(
                AnimationEventKind.BLEND_UPDATED,
                payload={
                    "blend_tree_id": tree.id,
                    "parameter": tree.parameter,
                    "value": clamped,
                    "child_weights": dict(weights),
                },
            )
            return {
                "blend_tree_id": tree.id,
                "parameter": tree.parameter,
                "value": clamped,
                "child_weights": dict(weights),
            }

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_active_nodes(self, entity_id: str) -> List[AnimationNode]:
        """Return all nodes currently active for the given entity.

        The returned list is sorted by node name then id.

        Args:
            entity_id: Identifier of the entity to query.
        """
        with self._lock:
            active_ids = self._entity_active_nodes.get(entity_id, [])
            nodes = [self._nodes[nid] for nid in active_ids if nid in self._nodes]
            nodes.sort(key=lambda n: (n.name, n.id))
            return nodes

    def get_node_state(self, node_id: str) -> Optional[str]:
        """Return the lifecycle state value of a node.

        Args:
            node_id: Identifier of the node to query.

        Returns:
            The node's state as a string (the ``AnimationState`` value),
            or None if the node was not found.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return None
            return node.state.value

    # ------------------------------------------------------------------
    # Event management
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: Any,
        handler: Callable[[AnimationEvent], None],
    ) -> str:
        """Subscribe a handler to animation director events.

        Args:
            kind: The ``AnimationEventKind`` (or its string value) to
                subscribe to. Pass ``None`` to subscribe to all events.
            handler: Callable invoked with each matching AnimationEvent.

        Returns:
            A handler identifier that can be passed to
            :meth:`unregister_event_handler` to remove the subscription.

        Raises:
            ValueError: If the handler capacity (``_MAX_EVENT_HANDLERS``)
                has been reached.
        """
        with self._lock:
            if len(self._handler_registry) >= _MAX_EVENT_HANDLERS:
                raise ValueError(
                    f"Event handler limit reached ({_MAX_EVENT_HANDLERS})"
                )
            key = self._normalize_kind(kind)
            self._event_handlers.setdefault(key, []).append(handler)
            handler_id = uuid.uuid4().hex
            self._handler_registry[handler_id] = (key, handler)
            return handler_id

    def unregister_event_handler(self, handler_id: str) -> bool:
        """Remove a previously registered event handler.

        Args:
            handler_id: The identifier returned by
                :meth:`register_event_handler`.

        Returns:
            True if the handler was removed, False if no handler is
            registered under that id.
        """
        with self._lock:
            entry = self._handler_registry.pop(handler_id, None)
            if entry is None:
                return False
            key, handler = entry
            handlers = self._event_handlers.get(key)
            if handlers is not None:
                try:
                    handlers.remove(handler)
                except ValueError:
                    pass
                if not handlers:
                    self._event_handlers.pop(key, None)
            return True

    def list_events(
        self,
        event_kind: Optional[Any] = None,
        limit: int = 100,
    ) -> List[AnimationEvent]:
        """Return the most recent events, newest last.

        Args:
            event_kind: When provided (as an ``AnimationEventKind`` or its
                string value), restrict the result to events of that kind.
            limit: Maximum number of events to return.

        Returns:
            A list of AnimationEvent records (up to ``limit``).
        """
        with self._lock:
            if limit <= 0:
                return []
            events = list(self._events)
            if event_kind is not None:
                target = self._normalize_kind(event_kind)
                events = [e for e in events if e.kind.value == target]
            return events[-limit:]

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def get_stats(self) -> AnimationStats:
        """Return aggregate statistic counters as an AnimationStats object."""
        with self._lock:
            return AnimationStats(
                total_clips=self._total_clips,
                total_nodes=self._total_nodes,
                total_transitions=self._total_transitions,
                total_layers=self._total_layers,
                total_blend_trees=self._total_blend_trees,
                active_animations=self._count_active_nodes(),
                last_updated=datetime.datetime.utcnow().isoformat() + "Z",
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current director state."""
        with self._lock:
            stats = self._compute_stats()
            return {
                "initialized": self._initialized,
                "total_clips": len(self._clips),
                "total_nodes": len(self._nodes),
                "total_transitions": len(self._transitions),
                "total_layers": len(self._layers),
                "total_blend_trees": len(self._blend_trees),
                "active_animations": self._count_active_nodes(),
                "tracked_entities": len(self._entity_active_nodes),
                "total_events": len(self._events),
                "total_handlers": len(self._handler_registry),
                "stats": stats,
            }

    def get_snapshot(self) -> AnimationSnapshot:
        """Capture an immutable snapshot of the director state."""
        with self._lock:
            stats = self._compute_stats()
            return AnimationSnapshot(
                active_node_count=self._count_active_nodes(),
                layer_count=len(self._layers),
                total_clips=len(self._clips),
                total_nodes=len(self._nodes),
                stats=stats,
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all clips, nodes, transitions, layers, blend trees, events,
        and handlers.

        Restores the director to its initial state, including the default
        seed animation data.
        """
        with self._lock:
            self._clips.clear()
            self._nodes.clear()
            self._transitions.clear()
            self._layers.clear()
            self._blend_trees.clear()
            self._entity_active_nodes.clear()
            self._events.clear()
            self._event_handlers.clear()
            self._handler_registry.clear()
            self._total_events_emitted = 0
            self._total_clips = 0
            self._total_nodes = 0
            self._total_transitions = 0
            self._total_layers = 0
            self._total_blend_trees = 0
            self._seed_default_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Populate the default clips, layers, nodes, transitions, and blend tree.

        Creates a small locomotion setup: three looping clips (idle, walk,
        run), two layers (a full-body base layer and an additive upper
        body layer masked to the spine and shoulders), three nodes bound
        to the clips on the base layer, two conditional transitions
        (idle->walk and walk->run gated by a ``speed`` parameter), and a
        single 1D motion blend tree that interpolates between the walk and
        run nodes based on speed.
        """
        # 1. Clips - the foundational looping locomotion set.
        idle_clip = AnimationClip(
            name="idle",
            duration=2.0,
            fps=30.0,
            loop_mode=LoopMode.LOOP,
            frame_count=60,
            skeletal_data={"bones": ["root", "spine", "arms", "legs"]},
            metadata={"category": "locomotion", "stance": "idle"},
        )
        self._clips[idle_clip.id] = idle_clip
        self._total_clips += 1
        self._emit_event(
            AnimationEventKind.CLIP_CREATED,
            payload={
                "clip_id": idle_clip.id,
                "name": idle_clip.name,
                "duration": idle_clip.duration,
                "loop_mode": idle_clip.loop_mode.value,
            },
        )

        walk_clip = AnimationClip(
            name="walk",
            duration=0.8,
            fps=30.0,
            loop_mode=LoopMode.LOOP,
            frame_count=24,
            skeletal_data={"bones": ["root", "spine", "arms", "legs"]},
            metadata={"category": "locomotion", "stance": "walk"},
        )
        self._clips[walk_clip.id] = walk_clip
        self._total_clips += 1
        self._emit_event(
            AnimationEventKind.CLIP_CREATED,
            payload={
                "clip_id": walk_clip.id,
                "name": walk_clip.name,
                "duration": walk_clip.duration,
                "loop_mode": walk_clip.loop_mode.value,
            },
        )

        run_clip = AnimationClip(
            name="run",
            duration=0.5,
            fps=30.0,
            loop_mode=LoopMode.LOOP,
            frame_count=15,
            skeletal_data={"bones": ["root", "spine", "arms", "legs"]},
            metadata={"category": "locomotion", "stance": "run"},
        )
        self._clips[run_clip.id] = run_clip
        self._total_clips += 1
        self._emit_event(
            AnimationEventKind.CLIP_CREATED,
            payload={
                "clip_id": run_clip.id,
                "name": run_clip.name,
                "duration": run_clip.duration,
                "loop_mode": run_clip.loop_mode.value,
            },
        )

        # 2. Layers - a full-body base and an additive upper body mask.
        base_layer = AnimationLayer(
            name="Base",
            mode=LayerMode.BASE,
            weight=1.0,
            mask=[],
            enabled=True,
            metadata={"description": "Full-body locomotion layer"},
        )
        self._layers[base_layer.id] = base_layer
        self._total_layers += 1
        self._emit_event(
            AnimationEventKind.LAYER_CREATED,
            payload={
                "layer_id": base_layer.id,
                "name": base_layer.name,
                "mode": base_layer.mode.value,
                "weight": base_layer.weight,
            },
        )

        upper_body_layer = AnimationLayer(
            name="UpperBody",
            mode=LayerMode.ADDITIVE,
            weight=0.5,
            mask=["spine", "shoulder_l", "shoulder_r"],
            enabled=True,
            metadata={"description": "Additive upper body pose layer"},
        )
        self._layers[upper_body_layer.id] = upper_body_layer
        self._total_layers += 1
        self._emit_event(
            AnimationEventKind.LAYER_CREATED,
            payload={
                "layer_id": upper_body_layer.id,
                "name": upper_body_layer.name,
                "mode": upper_body_layer.mode.value,
                "weight": upper_body_layer.weight,
            },
        )

        # 3. Nodes - one state per clip on the base layer.
        idle_node = AnimationNode(
            name="IdleNode",
            clip_id=idle_clip.id,
            layer_id=base_layer.id,
            state=AnimationState.IDLE,
            speed=1.0,
            weight=1.0,
            blend_type=BlendType.LINEAR,
            position=(0.0, 0.0),
            metadata={"stance": "idle"},
        )
        self._nodes[idle_node.id] = idle_node
        self._total_nodes += 1
        self._emit_event(
            AnimationEventKind.STATE_CREATED,
            payload={
                "node_id": idle_node.id,
                "name": idle_node.name,
                "clip_id": idle_node.clip_id,
                "layer_id": idle_node.layer_id,
            },
        )

        walk_node = AnimationNode(
            name="WalkNode",
            clip_id=walk_clip.id,
            layer_id=base_layer.id,
            state=AnimationState.IDLE,
            speed=1.0,
            weight=1.0,
            blend_type=BlendType.LINEAR,
            position=(0.0, 0.0),
            metadata={"stance": "walk"},
        )
        self._nodes[walk_node.id] = walk_node
        self._total_nodes += 1
        self._emit_event(
            AnimationEventKind.STATE_CREATED,
            payload={
                "node_id": walk_node.id,
                "name": walk_node.name,
                "clip_id": walk_node.clip_id,
                "layer_id": walk_node.layer_id,
            },
        )

        run_node = AnimationNode(
            name="RunNode",
            clip_id=run_clip.id,
            layer_id=base_layer.id,
            state=AnimationState.IDLE,
            speed=1.0,
            weight=1.0,
            blend_type=BlendType.LINEAR,
            position=(1.0, 0.0),
            metadata={"stance": "run"},
        )
        self._nodes[run_node.id] = run_node
        self._total_nodes += 1
        self._emit_event(
            AnimationEventKind.STATE_CREATED,
            payload={
                "node_id": run_node.id,
                "name": run_node.name,
                "clip_id": run_node.clip_id,
                "layer_id": run_node.layer_id,
            },
        )

        # 4. Transitions - speed-gated progression along the locomotion set.
        idle_to_walk = AnimationTransition(
            from_node_id=idle_node.id,
            to_node_id=walk_node.id,
            duration=0.3,
            blend_type=BlendType.LINEAR,
            conditions=[{"param": "speed", "op": ">", "value": 0.5}],
            priority=0,
        )
        self._transitions[idle_to_walk.id] = idle_to_walk
        self._total_transitions += 1
        self._emit_event(
            AnimationEventKind.TRANSITION_CREATED,
            payload={
                "transition_id": idle_to_walk.id,
                "from_node_id": idle_to_walk.from_node_id,
                "to_node_id": idle_to_walk.to_node_id,
                "blend_type": idle_to_walk.blend_type.value,
            },
        )

        walk_to_run = AnimationTransition(
            from_node_id=walk_node.id,
            to_node_id=run_node.id,
            duration=0.2,
            blend_type=BlendType.LINEAR,
            conditions=[{"param": "speed", "op": ">", "value": 5.0}],
            priority=1,
        )
        self._transitions[walk_to_run.id] = walk_to_run
        self._total_transitions += 1
        self._emit_event(
            AnimationEventKind.TRANSITION_CREATED,
            payload={
                "transition_id": walk_to_run.id,
                "from_node_id": walk_to_run.from_node_id,
                "to_node_id": walk_to_run.to_node_id,
                "blend_type": walk_to_run.blend_type.value,
            },
        )

        # 5. Blend tree - a 1D motion blend between walk and run on speed.
        motion_blend = BlendTree(
            name="MotionBlend",
            parameter="speed",
            children=[
                {
                    "node_id": walk_node.id,
                    "threshold": 0.0,
                    "position": (0.0, 0.0),
                },
                {
                    "node_id": run_node.id,
                    "threshold": 5.0,
                    "position": (1.0, 0.0),
                },
            ],
            min_threshold=0.0,
            max_threshold=5.0,
            blend_type=BlendType.MOTION,
        )
        self._blend_trees[motion_blend.id] = motion_blend
        self._total_blend_trees += 1


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_animation_director() -> AnimationDirectorEngine:
    """Return the singleton AnimationDirectorEngine instance."""
    return AnimationDirectorEngine.get_instance()
