"""Animation State Machine System for SparkLabs AI-native game engine.

Provides skeletal animation blending, hierarchical state machine
transitions, 2D blend spaces, inverse kinematics solving, and
layered animation playback for expressive character motion.
"""

import hashlib
import math
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest entry is
# evicted in FIFO order so memory growth stays predictable under heavy use.
_MAX_CLIPS: int = 2000
_MAX_BLUEPRINTS: int = 1000
_MAX_EVENTS: int = 10000
_MAX_LIST_LIMIT: int = 500
_DEFAULT_LIST_LIMIT: int = 100

# Numeric bounds for common parameters.
_WEIGHT_MIN: float = 0.0
_WEIGHT_MAX: float = 1.0
_SPEED_MIN: float = 0.0
_SPEED_MAX: float = 10.0
_DURATION_MIN: float = 0.0
_DURATION_MAX: float = 600.0
_FRAME_RATE_MIN: float = 1.0
_FRAME_RATE_MAX: float = 120.0
_BONE_COUNT_MIN: int = 1
_BONE_COUNT_MAX: int = 1024
_PRIORITY_MIN: int = -1000
_PRIORITY_MAX: int = 1000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _gen_id(seed_str: str = "", prefix: str = "") -> str:
    """Generate a short unique identifier using an MD5 digest.

    Combines a caller-supplied seed string with the current monotonic time
    and a random float so collisions are practically impossible. The first
    12 hex characters of the digest are returned, optionally prefixed.

    Args:
        seed_str: Optional seed material mixed into the digest input.
        prefix: Optional prefix joined to the digest with an underscore.

    Returns:
        A 12-character hex id, optionally prefixed.
    """
    raw = f"{seed_str}:{time.time():.9f}:{random.random():.9f}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}" if prefix else digest


def _now_ts() -> float:
    """Return the current wall-clock time in seconds since the epoch."""
    return time.time()


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits ``max_size``.

    Uses insertion-order iteration so the first inserted key is dropped
    first, keeping memory growth bounded for FIFO-style stores.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits ``max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value to the inclusive ``[low, high]`` range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float, returning ``default`` on failure."""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int, returning ``default`` on failure."""
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to ``default``.

    Accepts either an existing enum member or its raw value. Returns
    ``default`` when the value cannot be resolved.
    """
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value into a JSON-serializable form.

    Handles enums (by value), dicts, lists, tuples, sets, and dataclass
    instances via :func:`_dataclass_to_dict`.
    """
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
    """Convert a dataclass instance into a dict of JSON-serializable values.

    Inspects ``__dataclass_fields__`` so nested dataclasses and container
    fields are converted recursively through :func:`_to_jsonable`.
    """
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


# ---------------------------------------------------------------------------
# Vector Helpers (3D)
# ---------------------------------------------------------------------------


def _vec_length(v: Tuple[float, float, float]) -> float:
    """Return the Euclidean length of a 3D vector."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Return the unit-length version of a 3D vector.

    Returns the zero vector when the input length is below epsilon.
    """
    length = _vec_length(v)
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _vec_dot(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    """Return the dot product of two 3D vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_cross(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Return the cross product of two 3D vectors."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec_scale(
    v: Tuple[float, float, float], s: float
) -> Tuple[float, float, float]:
    """Return a 3D vector scaled by a scalar."""
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec_add(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Return the sum of two 3D vectors."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_sub(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Return the difference of two 3D vectors (a - b)."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_lerp(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    t: float,
) -> Tuple[float, float, float]:
    """Linearly interpolate between two 3D vectors by parameter ``t``."""
    t = _clamp(t, 0.0, 1.0)
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _vec_rotate_around_axis(
    v: Tuple[float, float, float],
    axis: Tuple[float, float, float],
    angle: float,
) -> Tuple[float, float, float]:
    """Rotate vector ``v`` around a unit ``axis`` by ``angle`` radians.

    Uses Rodrigues' rotation formula.
    """
    c = math.cos(angle)
    s = math.sin(angle)
    cross = _vec_cross(axis, v)
    dot = _vec_dot(axis, v)
    one_minus_c = 1.0 - c
    return (
        v[0] * c + cross[0] * s + axis[0] * dot * one_minus_c,
        v[1] * c + cross[1] * s + axis[1] * dot * one_minus_c,
        v[2] * c + cross[2] * s + axis[2] * dot * one_minus_c,
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AnimBlendMode(str, Enum):
    """Blend modes for combining animation layers and transitions."""

    OVERRIDE = "override"
    ADDITIVE = "additive"
    SUBTRACTIVE = "subtractive"
    MASK = "mask"


class AnimEventKind(str, Enum):
    """Audit event kinds emitted by the animation state machine."""

    CREATED = "created"
    PLAYED = "played"
    STOPPED = "stopped"
    TRANSITIONED = "transitioned"
    BLENDED = "blended"
    IK_SOLVED = "ik_solved"
    LAYER_ADDED = "layer_added"
    STATE_CHANGED = "state_changed"


class AnimLoopMode(str, Enum):
    """Playback loop behavior for an animation clip or state."""

    ONCE = "once"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    CLAMP = "clamp"


class AnimParameterType(str, Enum):
    """Types accepted by blueprint parameters driving transitions."""

    FLOAT = "float"
    BOOL = "bool"
    INT = "int"
    TRIGGER = "trigger"


class AnimStatus(str, Enum):
    """Runtime status of a blueprint playback session."""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    BLENDING = "blending"
    FINISHED = "finished"


class AnimTransitionCondition(str, Enum):
    """Comparison operators for transition conditions."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER = "greater"
    LESS = "less"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    IN_RANGE = "in_range"


class BoneRole(str, Enum):
    """Semantic role of a bone within a skeleton hierarchy."""

    ROOT = "root"
    SPINE = "spine"
    HEAD = "head"
    ARM_L = "arm_l"
    ARM_R = "arm_r"
    HAND_L = "hand_l"
    HAND_R = "hand_r"
    LEG_L = "leg_l"
    LEG_R = "leg_r"
    FOOT_L = "foot_l"
    FOOT_R = "foot_r"
    CUSTOM = "custom"


class BlendSpaceType(str, Enum):
    """Sampling strategy used by a blend space."""

    NONE = "none"
    DIRECTIONAL_1D = "directional_1d"
    DIRECTIONAL_2D = "directional_2d"
    RADIAL = "radial"


class IKChainType(str, Enum):
    """Solver strategy for an inverse kinematics chain."""

    LIMB_2BONE = "limb_2bone"
    LIMB_3BONE = "limb_3bone"
    SPINE_CHAIN = "spine_chain"
    LOOK_AT = "look_at"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class AnimClip:
    """A named skeletal animation clip with timing and tagging data."""

    clip_id: str = ""
    name: str = ""
    duration: float = 0.0
    frame_rate: float = 30.0
    bone_count: int = 0
    loop_mode: str = AnimLoopMode.LOOP.value
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "duration": round(self.duration, 4),
            "frame_rate": round(self.frame_rate, 2),
            "bone_count": self.bone_count,
            "loop_mode": self.loop_mode,
            "tags": list(self.tags),
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class AnimState:
    """A node in the state machine bound to a single clip."""

    state_id: str = ""
    name: str = ""
    clip_id: str = ""
    speed: float = 1.0
    loop_mode: str = AnimLoopMode.LOOP.value
    default_transition: str = ""
    on_enter: List[str] = field(default_factory=list)
    on_exit: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "name": self.name,
            "clip_id": self.clip_id,
            "speed": round(self.speed, 4),
            "loop_mode": self.loop_mode,
            "default_transition": self.default_transition,
            "on_enter": list(self.on_enter),
            "on_exit": list(self.on_exit),
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class TransitionCondition:
    """A single predicate evaluated against a blueprint parameter."""

    parameter_name: str = ""
    condition_type: str = AnimTransitionCondition.EQUALS.value
    threshold: float = 0.0
    compare_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "condition_type": self.condition_type,
            "threshold": _to_jsonable(self.threshold),
            "compare_value": _to_jsonable(self.compare_value),
        }


@dataclass
class AnimTransition:
    """A directed edge between two states with a timed blend."""

    transition_id: str = ""
    source_state: str = ""
    target_state: str = ""
    duration: float = 0.2
    blend_mode: str = AnimBlendMode.OVERRIDE.value
    conditions: List[TransitionCondition] = field(default_factory=list)
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "source_state": self.source_state,
            "target_state": self.target_state,
            "duration": round(self.duration, 4),
            "blend_mode": self.blend_mode,
            "conditions": [c.to_dict() for c in self.conditions],
            "priority": self.priority,
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class AnimParameter:
    """A typed, bounded value driving transition evaluation."""

    name: str = ""
    param_type: str = AnimParameterType.FLOAT.value
    default_value: Any = 0.0
    min_value: float = 0.0
    max_value: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "param_type": self.param_type,
            "default_value": _to_jsonable(self.default_value),
            "min_value": self.min_value,
            "max_value": self.max_value,
        }


@dataclass
class BlendSpaceNode:
    """A clip sample point within a blend space grid."""

    node_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    clip_id: str = ""
    speed: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "position_x": round(self.position_x, 4),
            "position_y": round(self.position_y, 4),
            "clip_id": self.clip_id,
            "speed": round(self.speed, 4),
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class BlendSpace:
    """A parameterized grid of clip samples interpolated at runtime."""

    space_id: str = ""
    name: str = ""
    space_type: str = BlendSpaceType.DIRECTIONAL_2D.value
    x_parameter: str = ""
    y_parameter: str = ""
    nodes: List[BlendSpaceNode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "space_id": self.space_id,
            "name": self.name,
            "space_type": self.space_type,
            "x_parameter": self.x_parameter,
            "y_parameter": self.y_parameter,
            "nodes": [n.to_dict() for n in self.nodes],
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class AnimLayer:
    """A composited pose layer with a weight and bone mask."""

    layer_id: str = ""
    name: str = ""
    weight: float = 1.0
    mask_bones: List[str] = field(default_factory=list)
    blend_mode: str = AnimBlendMode.OVERRIDE.value
    current_state: str = ""
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "weight": round(self.weight, 4),
            "mask_bones": list(self.mask_bones),
            "blend_mode": self.blend_mode,
            "current_state": self.current_state,
            "active": self.active,
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class IKChain:
    """A bone chain solved toward a target position."""

    chain_id: str = ""
    name: str = ""
    chain_type: str = IKChainType.LIMB_2BONE.value
    root_bone: str = ""
    mid_bones: List[str] = field(default_factory=list)
    tip_bone: str = ""
    target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    pole_vector: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "chain_type": self.chain_type,
            "root_bone": self.root_bone,
            "mid_bones": list(self.mid_bones),
            "tip_bone": self.tip_bone,
            "target_position": list(self.target_position),
            "pole_vector": list(self.pole_vector),
            "weight": round(self.weight, 4),
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class AnimBlueprint:
    """A complete animation graph: layers, states, transitions, and solvers."""

    blueprint_id: str = ""
    name: str = ""
    layers: Dict[str, AnimLayer] = field(default_factory=dict)
    states: Dict[str, AnimState] = field(default_factory=dict)
    transitions: List[AnimTransition] = field(default_factory=list)
    parameters: Dict[str, AnimParameter] = field(default_factory=dict)
    blend_spaces: Dict[str, BlendSpace] = field(default_factory=dict)
    ik_chains: Dict[str, IKChain] = field(default_factory=dict)
    current_state: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blueprint_id": self.blueprint_id,
            "name": self.name,
            "layers": [l.to_dict() for l in self.layers.values()],
            "states": [s.to_dict() for s in self.states.values()],
            "transitions": [t.to_dict() for t in self.transitions],
            "parameters": [p.to_dict() for p in self.parameters.values()],
            "blend_spaces": [b.to_dict() for b in self.blend_spaces.values()],
            "ik_chains": [k.to_dict() for k in self.ik_chains.values()],
            "current_state": self.current_state,
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class AnimConfig:
    """Tunable configuration for the animation state machine."""

    max_blueprints: int = 1000
    max_clips: int = 2000
    max_layers_per_blueprint: int = 32
    max_states_per_blueprint: int = 256
    max_blend_spaces: int = 64
    default_blend_duration: float = 0.2
    enable_ik: bool = True
    enable_root_motion: bool = True
    global_speed: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_blueprints": self.max_blueprints,
            "max_clips": self.max_clips,
            "max_layers_per_blueprint": self.max_layers_per_blueprint,
            "max_states_per_blueprint": self.max_states_per_blueprint,
            "max_blend_spaces": self.max_blend_spaces,
            "default_blend_duration": round(self.default_blend_duration, 4),
            "enable_ik": self.enable_ik,
            "enable_root_motion": self.enable_root_motion,
            "global_speed": round(self.global_speed, 4),
        }


@dataclass
class AnimStats:
    """Aggregate statistics computed across all blueprints."""

    total_clips: int = 0
    total_blueprints: int = 0
    total_states: int = 0
    total_transitions: int = 0
    total_blend_spaces: int = 0
    total_ik_chains: int = 0
    total_layers: int = 0
    active_blueprints: int = 0
    playing_states: int = 0
    total_transitions_triggered: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_clips": self.total_clips,
            "total_blueprints": self.total_blueprints,
            "total_states": self.total_states,
            "total_transitions": self.total_transitions,
            "total_blend_spaces": self.total_blend_spaces,
            "total_ik_chains": self.total_ik_chains,
            "total_layers": self.total_layers,
            "active_blueprints": self.active_blueprints,
            "playing_states": self.playing_states,
            "total_transitions_triggered": self.total_transitions_triggered,
            "tick_count": self.tick_count,
        }


@dataclass
class AnimSnapshot:
    """A point-in-time view of the system state for observability."""

    initialized: bool = False
    tick_count: int = 0
    active_blueprints: int = 0
    playing_states: int = 0
    total_clips: int = 0
    total_layers: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "tick_count": self.tick_count,
            "active_blueprints": self.active_blueprints,
            "playing_states": self.playing_states,
            "total_clips": self.total_clips,
            "total_layers": self.total_layers,
        }


@dataclass
class AnimEvent:
    """An audit entry recording a lifecycle change in the system."""

    event_id: str = ""
    kind: str = AnimEventKind.CREATED.value
    timestamp: float = 0.0
    blueprint_id: str = ""
    description: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "timestamp": round(self.timestamp, 4),
            "blueprint_id": self.blueprint_id,
            "description": self.description,
            "data": _to_jsonable(self.data),
        }


# ---------------------------------------------------------------------------
# Animation State Machine System
# ---------------------------------------------------------------------------


class AnimationStateMachineSystem:
    """Manages clips, blueprints, state machines, blend spaces, IK, and layers.

    The system is a thread-safe singleton. All public methods take the
    instance lock before mutating shared state so concurrent calls from
    gameplay, render, and editor threads remain consistent. Consumers
    should obtain the instance through :meth:`get_instance` or the
    module-level :func:`get_animation_state_machine_system` factory.
    """

    __instance = None
    __lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._init_lock = threading.RLock()
        self._initialized: bool = False
        # Containers are populated inside _initialize so __init__ stays thin.
        self._clips: Dict[str, AnimClip] = {}
        self._blueprints: Dict[str, AnimBlueprint] = {}
        self._runtime: Dict[str, Dict[str, Any]] = {}
        self._events: List[AnimEvent] = []
        self._config: AnimConfig = AnimConfig()
        self._stats: AnimStats = AnimStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialize()

    @classmethod
    def get_instance(cls) -> "AnimationStateMachineSystem":
        """Return the singleton instance using double-checked locking.

        The instance is created exactly once even when multiple threads
        call this concurrently on first use.
        """
        if cls.__instance is None:
            with cls.__lock:
                if cls.__instance is None:
                    cls.__instance = cls()
        return cls.__instance

    def _initialize(self) -> None:
        """Initialize the system with seed data (idempotent).

        Guarded by the init lock so repeated calls are no-ops after the
        first successful seed. Invoked from ``__init__`` and re-run from
        ``reset`` to repopulate the default data set.
        """
        with self._init_lock:
            if self._initialized:
                return
            self._clips = {}
            self._blueprints = {}
            self._runtime = {}
            self._events = []
            self._config = AnimConfig()
            self._stats = AnimStats()
            self._tick_count = 0
            self._event_counter = 0
            self._seed()
            self._initialized = True

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the system with realistic seed data.

        Seeds eight clips covering the canonical locomotion and combat set
        (idle, walk, run, jump, attack, death, fall, crouch), four
        blueprints (humanoid, quadruped, flyer, robot), ten states, twelve
        transitions, five parameters, four blend spaces, six IK chains,
        eight layers, and six audit events.
        """
        # --- Clips (8) ---
        clip_defs = [
            ("clip_idle", "Idle", 2.0, 30.0, 64, AnimLoopMode.LOOP.value,
             ["locomotion", "idle"], {"seed": True}),
            ("clip_walk", "Walk", 1.0, 30.0, 64, AnimLoopMode.LOOP.value,
             ["locomotion", "walk"], {"seed": True}),
            ("clip_run", "Run", 0.8, 30.0, 64, AnimLoopMode.LOOP.value,
             ["locomotion", "run"], {"seed": True}),
            ("clip_jump", "Jump", 1.2, 30.0, 64, AnimLoopMode.ONCE.value,
             ["action", "jump"], {"seed": True}),
            ("clip_attack", "Attack", 0.6, 30.0, 64, AnimLoopMode.ONCE.value,
             ["combat", "attack"], {"seed": True}),
            ("clip_death", "Death", 2.4, 30.0, 64, AnimLoopMode.CLAMP.value,
             ["combat", "death"], {"seed": True}),
            ("clip_fall", "Fall", 1.0, 30.0, 64, AnimLoopMode.LOOP.value,
             ["action", "fall"], {"seed": True}),
            ("clip_crouch", "Crouch", 1.5, 30.0, 64, AnimLoopMode.LOOP.value,
             ["locomotion", "crouch"], {"seed": True}),
        ]
        for cid, name, dur, fr, bc, lm, tags, md in clip_defs:
            self._clips[cid] = AnimClip(
                clip_id=cid, name=name, duration=dur, frame_rate=fr,
                bone_count=bc, loop_mode=lm, tags=list(tags), metadata=dict(md),
            )

        # --- Blueprints (4) ---
        blueprint_defs = [
            ("bp_humanoid", "Humanoid Character"),
            ("bp_quadruped", "Quadruped Character"),
            ("bp_flyer", "Flying Character"),
            ("bp_robot", "Robot Character"),
        ]
        for bid, bname in blueprint_defs:
            bp = AnimBlueprint(blueprint_id=bid, name=bname,
                               metadata={"seed": True})
            self._blueprints[bid] = bp
            self._runtime[bid] = self._fresh_runtime(bp)

        # --- Parameters (5) on the humanoid blueprint ---
        param_defs = [
            ("speed", AnimParameterType.FLOAT.value, 0.0, 0.0, 6.0),
            ("is_grounded", AnimParameterType.BOOL.value, True, 0.0, 1.0),
            ("health", AnimParameterType.FLOAT.value, 100.0, 0.0, 100.0),
            ("input_x", AnimParameterType.FLOAT.value, 0.0, -1.0, 1.0),
            ("input_y", AnimParameterType.FLOAT.value, 0.0, -1.0, 1.0),
        ]
        humanoid = self._blueprints["bp_humanoid"]
        for pname, ptype, pdef, pmin, pmax in param_defs:
            humanoid.parameters[pname] = AnimParameter(
                name=pname, param_type=ptype, default_value=pdef,
                min_value=pmin, max_value=pmax,
            )
        self._runtime["bp_humanoid"]["param_values"] = {
            p.name: p.default_value for p in humanoid.parameters.values()
        }

        # --- States (10) distributed across blueprints ---
        state_defs = [
            ("bp_humanoid", "st_idle", "Idle", "clip_idle", 1.0,
             AnimLoopMode.LOOP.value),
            ("bp_humanoid", "st_walk", "Walk", "clip_walk", 1.0,
             AnimLoopMode.LOOP.value),
            ("bp_humanoid", "st_run", "Run", "clip_run", 1.0,
             AnimLoopMode.LOOP.value),
            ("bp_humanoid", "st_jump", "Jump", "clip_jump", 1.0,
             AnimLoopMode.ONCE.value),
            ("bp_humanoid", "st_attack", "Attack", "clip_attack", 1.0,
             AnimLoopMode.ONCE.value),
            ("bp_humanoid", "st_death", "Death", "clip_death", 1.0,
             AnimLoopMode.CLAMP.value),
            ("bp_quadruped", "st_crouch", "Crouch", "clip_crouch", 1.0,
             AnimLoopMode.LOOP.value),
            ("bp_quadruped", "st_fall", "Fall", "clip_fall", 1.0,
             AnimLoopMode.LOOP.value),
            ("bp_flyer", "st_fly_idle", "Fly Idle", "clip_idle", 0.8,
             AnimLoopMode.LOOP.value),
            ("bp_robot", "st_power_down", "Power Down", "clip_death", 0.7,
             AnimLoopMode.CLAMP.value),
        ]
        for bid, sid, sname, clip, spd, lm in state_defs:
            bp = self._blueprints[bid]
            bp.states[sid] = AnimState(
                state_id=sid, name=sname, clip_id=clip, speed=spd,
                loop_mode=lm, metadata={"seed": True},
            )

        # Set default/current state for each blueprint that has states.
        for bp in self._blueprints.values():
            if bp.states and not bp.current_state:
                bp.current_state = next(iter(bp.states.keys()))

        # --- Transitions (12) on the humanoid blueprint ---
        transition_defs = [
            ("tr_idle_to_walk", "st_idle", "st_walk", 0.2,
             AnimBlendMode.OVERRIDE.value, [("speed", "greater", 0.1, None)], 0),
            ("tr_walk_to_idle", "st_walk", "st_idle", 0.2,
             AnimBlendMode.OVERRIDE.value, [("speed", "less", 0.1, None)], 0),
            ("tr_walk_to_run", "st_walk", "st_run", 0.2,
             AnimBlendMode.OVERRIDE.value, [("speed", "greater", 3.0, None)], 1),
            ("tr_run_to_walk", "st_run", "st_walk", 0.2,
             AnimBlendMode.OVERRIDE.value, [("speed", "less", 3.0, None)], 1),
            ("tr_idle_to_jump", "st_idle", "st_jump", 0.1,
             AnimBlendMode.OVERRIDE.value,
             [("is_grounded", "equals", 0.0, False)], 5),
            ("tr_jump_to_fall", "st_jump", "st_death", 0.2,
             AnimBlendMode.OVERRIDE.value, [], 4),
            ("tr_idle_to_attack", "st_idle", "st_attack", 0.05,
             AnimBlendMode.ADDITIVE.value, [], 6),
            ("tr_attack_to_idle", "st_attack", "st_idle", 0.2,
             AnimBlendMode.OVERRIDE.value, [], 3),
            ("tr_idle_to_death", "st_idle", "st_death", 0.3,
             AnimBlendMode.OVERRIDE.value,
             [("health", "less", 1.0, None)], 10),
            ("tr_walk_to_crouch", "st_walk", "st_idle", 0.15,
             AnimBlendMode.OVERRIDE.value, [("input_y", "less", -0.5, None)], 2),
            ("tr_run_to_fall", "st_run", "st_death", 0.2,
             AnimBlendMode.OVERRIDE.value,
             [("is_grounded", "equals", 0.0, False)], 7),
            ("tr_idle_to_walk_range", "st_idle", "st_walk", 0.2,
             AnimBlendMode.OVERRIDE.value,
             [("speed", "in_range", 0.1, 3.0)], 0),
        ]
        for tid, src, dst, dur, bm, conds, prio in transition_defs:
            cond_objs = [
                TransitionCondition(
                    parameter_name=pn, condition_type=ct,
                    threshold=thr, compare_value=cv,
                )
                for pn, ct, thr, cv in conds
            ]
            humanoid.transitions.append(AnimTransition(
                transition_id=tid, source_state=src, target_state=dst,
                duration=dur, blend_mode=bm, conditions=cond_objs,
                priority=prio, metadata={"seed": True},
            ))

        # Quadruped gets a couple of transitions too.
        quad = self._blueprints["bp_quadruped"]
        quad.transitions.append(AnimTransition(
            transition_id="tr_crouch_to_fall", source_state="st_crouch",
            target_state="st_fall", duration=0.2,
            blend_mode=AnimBlendMode.OVERRIDE.value, conditions=[],
            priority=0, metadata={"seed": True},
        ))
        quad.transitions.append(AnimTransition(
            transition_id="tr_fall_to_crouch", source_state="st_fall",
            target_state="st_crouch", duration=0.2,
            blend_mode=AnimBlendMode.OVERRIDE.value, conditions=[],
            priority=0, metadata={"seed": True},
        ))

        # --- Blend Spaces (4) ---
        locomotion_nodes = [
            BlendSpaceNode("bsn_walk", 0.0, 0.0, "clip_walk", 1.0, {}),
            BlendSpaceNode("bsn_run", 6.0, 0.0, "clip_run", 1.0, {}),
            BlendSpaceNode("bsn_idle", 0.0, 1.0, "clip_idle", 1.0, {}),
        ]
        humanoid.blend_spaces["bs_locomotion"] = BlendSpace(
            space_id="bs_locomotion", name="Locomotion 2D",
            space_type=BlendSpaceType.DIRECTIONAL_2D.value,
            x_parameter="speed", y_parameter="input_y",
            nodes=locomotion_nodes, metadata={"seed": True},
        )

        aim_nodes = [
            BlendSpaceNode("bsn_aim_down", -1.0, 0.0, "clip_idle", 1.0, {}),
            BlendSpaceNode("bsn_aim_up", 1.0, 0.0, "clip_attack", 1.0, {}),
        ]
        humanoid.blend_spaces["bs_aim_1d"] = BlendSpace(
            space_id="bs_aim_1d", name="Aim 1D",
            space_type=BlendSpaceType.DIRECTIONAL_1D.value,
            x_parameter="input_y", y_parameter="",
            nodes=aim_nodes, metadata={"seed": True},
        )

        turn_nodes = [
            BlendSpaceNode("bsn_turn_l", -1.0, 0.0, "clip_walk", 0.8, {}),
            BlendSpaceNode("bsn_turn_r", 1.0, 0.0, "clip_walk", 0.8, {}),
            BlendSpaceNode("bsn_turn_fwd", 0.0, 1.0, "clip_run", 1.0, {}),
        ]
        humanoid.blend_spaces["bs_turn_radial"] = BlendSpace(
            space_id="bs_turn_radial", name="Turn Radial",
            space_type=BlendSpaceType.RADIAL.value,
            x_parameter="input_x", y_parameter="input_y",
            nodes=turn_nodes, metadata={"seed": True},
        )

        speed_nodes = [
            BlendSpaceNode("bsn_s_idle", 0.0, 0.0, "clip_idle", 1.0, {}),
            BlendSpaceNode("bsn_s_walk", 2.0, 0.0, "clip_walk", 1.0, {}),
            BlendSpaceNode("bsn_s_run", 6.0, 0.0, "clip_run", 1.0, {}),
        ]
        humanoid.blend_spaces["bs_speed_1d"] = BlendSpace(
            space_id="bs_speed_1d", name="Speed 1D",
            space_type=BlendSpaceType.DIRECTIONAL_1D.value,
            x_parameter="speed", y_parameter="",
            nodes=speed_nodes, metadata={"seed": True},
        )

        # --- IK Chains (6) ---
        ik_defs = [
            ("ik_left_hand", "Left Hand IK", IKChainType.LIMB_2BONE.value,
             "bone_upper_arm_l", ["bone_lower_arm_l"], "bone_hand_l",
             (0.5, 1.2, 0.2), (1.0, 0.0, 0.0), 1.0),
            ("ik_right_hand", "Right Hand IK", IKChainType.LIMB_2BONE.value,
             "bone_upper_arm_r", ["bone_lower_arm_r"], "bone_hand_r",
             (-0.5, 1.2, 0.2), (-1.0, 0.0, 0.0), 1.0),
            ("ik_left_foot", "Left Foot IK", IKChainType.LIMB_2BONE.value,
             "bone_thigh_l", ["bone_calf_l"], "bone_foot_l",
             (0.2, 0.0, 0.4), (0.0, 1.0, 0.0), 1.0),
            ("ik_right_foot", "Right Foot IK", IKChainType.LIMB_2BONE.value,
             "bone_thigh_r", ["bone_calf_r"], "bone_foot_r",
             (-0.2, 0.0, 0.4), (0.0, 1.0, 0.0), 1.0),
            ("ik_head_look", "Head Look At", IKChainType.LOOK_AT.value,
             "bone_neck", [], "bone_head",
             (0.0, 1.6, 1.0), (0.0, 1.0, 0.0), 0.6),
            ("ik_spine", "Spine Chain", IKChainType.SPINE_CHAIN.value,
             "bone_spine_01", ["bone_spine_02", "bone_spine_03"],
             "bone_neck", (0.0, 1.4, 0.1), (0.0, 1.0, 0.0), 0.4),
        ]
        for cid, cname, ct, root, mids, tip, target, pole, w in ik_defs:
            humanoid.ik_chains[cid] = IKChain(
                chain_id=cid, name=cname, chain_type=ct, root_bone=root,
                mid_bones=list(mids), tip_bone=tip, target_position=target,
                pole_vector=pole, weight=w,
                metadata={"seed": True, "rest_positions": {
                    "root": (0.0, 0.0, 0.0),
                    "mid": (0.0, 0.6, 0.0),
                    "tip": (0.0, 1.2, 0.0),
                }},
            )

        # --- Layers (8) on the humanoid blueprint ---
        layer_defs = [
            ("layer_base", "Base Layer", 1.0, [], AnimBlendMode.OVERRIDE.value),
            ("layer_upper_body", "Upper Body", 0.8,
             ["bone_spine_01", "bone_spine_02", "bone_spine_03",
              "bone_neck", "bone_head"], AnimBlendMode.OVERRIDE.value),
            ("layer_lower_body", "Lower Body", 0.9,
             ["bone_hip", "bone_thigh_l", "bone_calf_l", "bone_foot_l",
              "bone_thigh_r", "bone_calf_r", "bone_foot_r"],
             AnimBlendMode.OVERRIDE.value),
            ("layer_head", "Head", 0.5, ["bone_neck", "bone_head"],
             AnimBlendMode.ADDITIVE.value),
            ("layer_left_arm", "Left Arm", 0.7,
             ["bone_upper_arm_l", "bone_lower_arm_l", "bone_hand_l"],
             AnimBlendMode.OVERRIDE.value),
            ("layer_right_arm", "Right Arm", 0.7,
             ["bone_upper_arm_r", "bone_lower_arm_r", "bone_hand_r"],
             AnimBlendMode.OVERRIDE.value),
            ("layer_legs", "Legs", 0.6,
             ["bone_thigh_l", "bone_calf_l", "bone_foot_l",
              "bone_thigh_r", "bone_calf_r", "bone_foot_r"],
             AnimBlendMode.ADDITIVE.value),
            ("layer_props", "Props", 1.0, [], AnimBlendMode.MASK.value),
        ]
        for lid, lname, w, mask, bm in layer_defs:
            humanoid.layers[lid] = AnimLayer(
                layer_id=lid, name=lname, weight=w, mask_bones=list(mask),
                blend_mode=bm, current_state=humanoid.current_state,
                active=True, metadata={"seed": True},
            )

        # --- Events (6) ---
        self._events = [
            AnimEvent(event_id=_gen_id("evt", "ev"), kind=AnimEventKind.CREATED.value,
                      timestamp=_now_ts(), blueprint_id="bp_humanoid",
                      description="seed blueprint created",
                      data={"seed": True}),
            AnimEvent(event_id=_gen_id("evt", "ev"), kind=AnimEventKind.CREATED.value,
                      timestamp=_now_ts(), blueprint_id="bp_quadruped",
                      description="seed blueprint created",
                      data={"seed": True}),
            AnimEvent(event_id=_gen_id("evt", "ev"), kind=AnimEventKind.CREATED.value,
                      timestamp=_now_ts(), blueprint_id="bp_flyer",
                      description="seed blueprint created",
                      data={"seed": True}),
            AnimEvent(event_id=_gen_id("evt", "ev"), kind=AnimEventKind.CREATED.value,
                      timestamp=_now_ts(), blueprint_id="bp_robot",
                      description="seed blueprint created",
                      data={"seed": True}),
            AnimEvent(event_id=_gen_id("evt", "ev"), kind=AnimEventKind.LAYER_ADDED.value,
                      timestamp=_now_ts(), blueprint_id="bp_humanoid",
                      description="seed layers added",
                      data={"count": 8}),
            AnimEvent(event_id=_gen_id("evt", "ev"), kind=AnimEventKind.BLENDED.value,
                      timestamp=_now_ts(), blueprint_id="bp_humanoid",
                      description="seed blend space created",
                      data={"space_id": "bs_locomotion"}),
        ]
        self._event_counter = len(self._events)

        # Refresh aggregate stats so the seed is reflected immediately.
        self._refresh_stats()

    def _fresh_runtime(self, bp: AnimBlueprint) -> Dict[str, Any]:
        """Build a fresh runtime playback state for a blueprint."""
        return {
            "status": AnimStatus.IDLE.value,
            "playback_time": 0.0,
            "playback_speed": 1.0,
            "blend_remaining": 0.0,
            "blend_duration": 0.0,
            "blend_from_state": "",
            "blend_to_state": "",
            "param_values": {
                p.name: p.default_value for p in bp.parameters.values()
            },
        }

    def _emit(self, kind: str, description: str,
              data: Optional[Dict[str, Any]] = None,
              blueprint_id: str = "") -> None:
        """Append an audit event to the in-memory event log.

        Args:
            kind: One of :class:`AnimEventKind` string values.
            description: Human-readable summary of the event.
            data: Optional payload dict stored with the event.
            blueprint_id: Optional blueprint the event pertains to.
        """
        event = AnimEvent(
            event_id=_gen_id("evt", "ev"),
            kind=kind,
            timestamp=_now_ts(),
            blueprint_id=blueprint_id,
            description=description,
            data=dict(data) if data else {},
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from the current stores."""
        total_states = sum(len(b.states) for b in self._blueprints.values())
        total_trans = sum(len(b.transitions) for b in self._blueprints.values())
        total_bs = sum(len(b.blend_spaces) for b in self._blueprints.values())
        total_ik = sum(len(b.ik_chains) for b in self._blueprints.values())
        total_layers = sum(len(b.layers) for b in self._blueprints.values())
        active = sum(
            1 for bid in self._blueprints
            if self._runtime.get(bid, {}).get("status") == AnimStatus.PLAYING.value
        )
        self._stats.total_clips = len(self._clips)
        self._stats.total_blueprints = len(self._blueprints)
        self._stats.total_states = total_states
        self._stats.total_transitions = total_trans
        self._stats.total_blend_spaces = total_bs
        self._stats.total_ik_chains = total_ik
        self._stats.total_layers = total_layers
        self._stats.active_blueprints = active
        self._stats.playing_states = active
        self._stats.tick_count = self._tick_count

    # ------------------------------------------------------------------
    # Clip Management
    # ------------------------------------------------------------------

    def register_clip(self, clip_id: str = "", name: str = "",
                      duration: float = 1.0, frame_rate: float = 30.0,
                      bone_count: int = 0, loop_mode: str = AnimLoopMode.LOOP.value,
                      tags: Optional[List[str]] = None,
                      metadata: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, str, Optional[AnimClip]]:
        """Register a new animation clip in the clip registry."""
        with self._lock:
            cid = clip_id or _gen_id("clip", "clip")
            if cid in self._clips:
                return (False, f"clip already exists: {cid}", self._clips[cid])
            duration = _clamp(_safe_float(duration, 1.0), _DURATION_MIN, _DURATION_MAX)
            frame_rate = _clamp(_safe_float(frame_rate, 30.0), _FRAME_RATE_MIN, _FRAME_RATE_MAX)
            bone_count = _clamp(_safe_int(bone_count, 0), _BONE_COUNT_MIN, _BONE_COUNT_MAX)
            lm = _coerce_enum(AnimLoopMode, loop_mode, AnimLoopMode.LOOP).value
            clip = AnimClip(
                clip_id=cid, name=name or cid, duration=duration,
                frame_rate=frame_rate, bone_count=bone_count, loop_mode=lm,
                tags=list(tags) if tags else [],
                metadata=dict(metadata) if metadata else {},
            )
            self._clips[cid] = clip
            _evict_fifo_dict(self._clips, self._config.max_clips)
            self._emit(AnimEventKind.CREATED.value, f"clip registered: {cid}",
                       {"clip_id": cid, "name": clip.name, "duration": duration})
            self._refresh_stats()
            return (True, f"clip registered: {cid}", clip)

    def remove_clip(self, clip_id: str) -> Tuple[bool, str]:
        """Remove a clip from the registry by id."""
        with self._lock:
            if clip_id not in self._clips:
                return (False, f"clip not found: {clip_id}")
            del self._clips[clip_id]
            self._emit(AnimEventKind.STOPPED.value, f"clip removed: {clip_id}",
                       {"clip_id": clip_id})
            self._refresh_stats()
            return (True, f"clip removed: {clip_id}")

    def get_clip(self, clip_id: str) -> Optional[AnimClip]:
        """Return a clip by id, or ``None`` when it does not exist."""
        with self._lock:
            return self._clips.get(clip_id)

    def list_clips(self, tag: Optional[str] = None,
                   limit: int = _DEFAULT_LIST_LIMIT) -> List[AnimClip]:
        """List clips, optionally filtered by tag, capped by ``limit``."""
        with self._lock:
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT), 1, _MAX_LIST_LIMIT)
            clips = list(self._clips.values())
            if tag:
                clips = [c for c in clips if tag in c.tags]
            return clips[:cap]

    # ------------------------------------------------------------------
    # Blueprint Management
    # ------------------------------------------------------------------

    def create_blueprint(self, blueprint_id: str = "", name: str = "",
                         parameters: Optional[List[Dict[str, Any]]] = None,
                         metadata: Optional[Dict[str, Any]] = None
                         ) -> Tuple[bool, str, Optional[AnimBlueprint]]:
        """Create a new animation blueprint."""
        with self._lock:
            bid = blueprint_id or _gen_id("bp", "bp")
            if bid in self._blueprints:
                return (False, f"blueprint already exists: {bid}", self._blueprints[bid])
            bp = AnimBlueprint(
                blueprint_id=bid, name=name or bid,
                metadata=dict(metadata) if metadata else {},
            )
            if parameters:
                for p in parameters:
                    pname = str(p.get("name", ""))
                    if not pname:
                        continue
                    ptype = _coerce_enum(AnimParameterType, p.get("param_type"),
                                         AnimParameterType.FLOAT).value
                    pdef = p.get("default_value", 0.0)
                    pmin = _safe_float(p.get("min_value", 0.0), 0.0)
                    pmax = _safe_float(p.get("max_value", 1.0), 1.0)
                    bp.parameters[pname] = AnimParameter(
                        name=pname, param_type=ptype, default_value=pdef,
                        min_value=pmin, max_value=pmax,
                    )
            self._blueprints[bid] = bp
            self._runtime[bid] = self._fresh_runtime(bp)
            _evict_fifo_dict(self._blueprints, self._config.max_blueprints)
            self._emit(AnimEventKind.CREATED.value, f"blueprint created: {bid}",
                       {"blueprint_id": bid, "name": bp.name}, blueprint_id=bid)
            self._refresh_stats()
            return (True, f"blueprint created: {bid}", bp)

    def remove_blueprint(self, blueprint_id: str) -> Tuple[bool, str]:
        """Remove a blueprint and its runtime state by id."""
        with self._lock:
            if blueprint_id not in self._blueprints:
                return (False, f"blueprint not found: {blueprint_id}")
            del self._blueprints[blueprint_id]
            self._runtime.pop(blueprint_id, None)
            self._emit(AnimEventKind.STOPPED.value, f"blueprint removed: {blueprint_id}",
                       {"blueprint_id": blueprint_id})
            self._refresh_stats()
            return (True, f"blueprint removed: {blueprint_id}")

    def get_blueprint(self, blueprint_id: str) -> Optional[AnimBlueprint]:
        """Return a blueprint by id, or ``None`` when it does not exist."""
        with self._lock:
            return self._blueprints.get(blueprint_id)

    def list_blueprints(self, limit: int = _DEFAULT_LIST_LIMIT) -> List[AnimBlueprint]:
        """List blueprints capped by ``limit``."""
        with self._lock:
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT), 1, _MAX_LIST_LIMIT)
            return list(self._blueprints.values())[:cap]

    # ------------------------------------------------------------------
    # State Management
    # ------------------------------------------------------------------

    def add_state(self, blueprint_id: str, state_id: str = "",
                  name: str = "", clip_id: str = "", speed: float = 1.0,
                  loop_mode: str = AnimLoopMode.LOOP.value,
                  metadata: Optional[Dict[str, Any]] = None
                  ) -> Tuple[bool, str, AnimBlueprint]:
        """Add a state to a blueprint bound to a clip."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                empty = AnimBlueprint()
                return (False, f"blueprint not found: {blueprint_id}", empty)
            if len(bp.states) >= self._config.max_states_per_blueprint:
                return (False, "state limit reached for blueprint", bp)
            sid = state_id or _gen_id("st", "st")
            if sid in bp.states:
                return (False, f"state already exists: {sid}", bp)
            if clip_id and clip_id not in self._clips:
                return (False, f"clip not found: {clip_id}", bp)
            spd = _clamp(_safe_float(speed, 1.0), _SPEED_MIN, _SPEED_MAX)
            lm = _coerce_enum(AnimLoopMode, loop_mode, AnimLoopMode.LOOP).value
            state = AnimState(
                state_id=sid, name=name or sid, clip_id=clip_id, speed=spd,
                loop_mode=lm, metadata=dict(metadata) if metadata else {},
            )
            bp.states[sid] = state
            if not bp.current_state:
                bp.current_state = sid
            self._emit(AnimEventKind.STATE_CHANGED.value, f"state added: {sid}",
                       {"blueprint_id": blueprint_id, "state_id": sid},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"state added: {sid}", bp)

    def remove_state(self, blueprint_id: str, state_id: str
                     ) -> Tuple[bool, str, AnimBlueprint]:
        """Remove a state and any transitions that touch it."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            if state_id not in bp.states:
                return (False, f"state not found: {state_id}", bp)
            del bp.states[state_id]
            bp.transitions = [
                t for t in bp.transitions
                if t.source_state != state_id and t.target_state != state_id
            ]
            if bp.current_state == state_id:
                bp.current_state = next(iter(bp.states.keys()), "")
            self._emit(AnimEventKind.STATE_CHANGED.value, f"state removed: {state_id}",
                       {"blueprint_id": blueprint_id, "state_id": state_id},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"state removed: {state_id}", bp)

    def get_state(self, blueprint_id: str, state_id: str) -> Optional[AnimState]:
        """Return a state by id within a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return None
            return bp.states.get(state_id)

    def list_states(self, blueprint_id: str) -> List[AnimState]:
        """List all states in a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return []
            return list(bp.states.values())

    def set_default_state(self, blueprint_id: str, state_id: str
                          ) -> Tuple[bool, str, AnimBlueprint]:
        """Set the current/default state of a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            if state_id not in bp.states:
                return (False, f"state not found: {state_id}", bp)
            previous = bp.current_state
            bp.current_state = state_id
            rt = self._runtime.get(blueprint_id)
            if rt is not None:
                rt["playback_time"] = 0.0
            self._emit(AnimEventKind.STATE_CHANGED.value,
                       f"default state set: {state_id} (was {previous})",
                       {"blueprint_id": blueprint_id, "state_id": state_id,
                        "previous": previous},
                       blueprint_id=blueprint_id)
            return (True, f"default state set: {state_id}", bp)

    # ------------------------------------------------------------------
    # Transition Management
    # ------------------------------------------------------------------

    def add_transition(self, blueprint_id: str, transition_id: str = "",
                       source_state: str = "", target_state: str = "",
                       duration: float = 0.2,
                       blend_mode: str = AnimBlendMode.OVERRIDE.value,
                       conditions: Optional[List[Dict[str, Any]]] = None,
                       priority: int = 0,
                       metadata: Optional[Dict[str, Any]] = None
                       ) -> Tuple[bool, str, AnimBlueprint]:
        """Add a directed transition between two states in a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            if not source_state or not target_state:
                return (False, "source_state and target_state are required", bp)
            if source_state not in bp.states:
                return (False, f"source state not found: {source_state}", bp)
            if target_state not in bp.states:
                return (False, f"target state not found: {target_state}", bp)
            tid = transition_id or _gen_id("tr", "tr")
            if any(t.transition_id == tid for t in bp.transitions):
                return (False, f"transition already exists: {tid}", bp)
            dur = _clamp(_safe_float(duration, self._config.default_blend_duration),
                         _DURATION_MIN, _DURATION_MAX)
            bm = _coerce_enum(AnimBlendMode, blend_mode, AnimBlendMode.OVERRIDE).value
            prio = _clamp(_safe_int(priority, 0), _PRIORITY_MIN, _PRIORITY_MAX)
            cond_objs: List[TransitionCondition] = []
            if conditions:
                for c in conditions:
                    cond_objs.append(TransitionCondition(
                        parameter_name=str(c.get("parameter_name", "")),
                        condition_type=_coerce_enum(
                            AnimTransitionCondition, c.get("condition_type"),
                            AnimTransitionCondition.EQUALS).value,
                        threshold=_safe_float(c.get("threshold", 0.0), 0.0),
                        compare_value=c.get("compare_value"),
                    ))
            trans = AnimTransition(
                transition_id=tid, source_state=source_state,
                target_state=target_state, duration=dur, blend_mode=bm,
                conditions=cond_objs, priority=prio,
                metadata=dict(metadata) if metadata else {},
            )
            bp.transitions.append(trans)
            # Keep transitions sorted by descending priority for evaluation.
            bp.transitions.sort(key=lambda t: -t.priority)
            self._emit(AnimEventKind.TRANSITIONED.value, f"transition added: {tid}",
                       {"blueprint_id": blueprint_id, "transition_id": tid,
                        "source": source_state, "target": target_state},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"transition added: {tid}", bp)

    def remove_transition(self, blueprint_id: str, transition_id: str
                          ) -> Tuple[bool, str, AnimBlueprint]:
        """Remove a transition by id from a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            before = len(bp.transitions)
            bp.transitions = [t for t in bp.transitions if t.transition_id != transition_id]
            if len(bp.transitions) == before:
                return (False, f"transition not found: {transition_id}", bp)
            self._emit(AnimEventKind.TRANSITIONED.value, f"transition removed: {transition_id}",
                       {"blueprint_id": blueprint_id, "transition_id": transition_id},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"transition removed: {transition_id}", bp)

    def list_transitions(self, blueprint_id: str) -> List[AnimTransition]:
        """List all transitions in a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return []
            return list(bp.transitions)

    def trigger_transition(self, blueprint_id: str, target_state: str
                           ) -> Tuple[bool, str, AnimBlueprint]:
        """Manually trigger a transition to ``target_state`` if a path exists."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            if target_state not in bp.states:
                return (False, f"target state not found: {target_state}", bp)
            current = bp.current_state
            # Find a matching transition; fall back to a direct jump.
            match = None
            for t in bp.transitions:
                if t.source_state == current and t.target_state == target_state:
                    match = t
                    break
            duration = match.duration if match else self._config.default_blend_duration
            blend_mode = match.blend_mode if match else AnimBlendMode.OVERRIDE.value
            bp.current_state = target_state
            rt = self._runtime.get(blueprint_id)
            if rt is not None:
                rt["blend_remaining"] = duration
                rt["blend_duration"] = duration
                rt["blend_from_state"] = current
                rt["blend_to_state"] = target_state
                rt["playback_time"] = 0.0
                if rt["status"] == AnimStatus.IDLE.value:
                    rt["status"] = AnimStatus.BLENDING.value
            self._stats.total_transitions_triggered += 1
            self._emit(AnimEventKind.TRANSITIONED.value,
                       f"transition triggered: {current} -> {target_state}",
                       {"blueprint_id": blueprint_id, "from": current,
                        "to": target_state, "duration": duration,
                        "blend_mode": blend_mode},
                       blueprint_id=blueprint_id)
            return (True, f"transition triggered: {current} -> {target_state}", bp)

    # ------------------------------------------------------------------
    # Parameter Management
    # ------------------------------------------------------------------

    def set_parameter(self, blueprint_id: str, name: str, value: Any
                      ) -> Tuple[bool, str, AnimBlueprint]:
        """Set the current value of a blueprint parameter."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            if not name:
                return (False, "parameter name is required", bp)
            param = bp.parameters.get(name)
            rt = self._runtime.get(blueprint_id)
            if rt is None:
                rt = self._fresh_runtime(bp)
                self._runtime[blueprint_id] = rt
            if param is None:
                # Auto-create a float parameter when an unknown name is set.
                ptype = AnimParameterType.FLOAT.value
                if isinstance(value, bool):
                    ptype = AnimParameterType.BOOL.value
                elif isinstance(value, int):
                    ptype = AnimParameterType.INT.value
                param = AnimParameter(name=name, param_type=ptype,
                                      default_value=value, min_value=0.0,
                                      max_value=1.0 if ptype == AnimParameterType.FLOAT.value else 1)
                bp.parameters[name] = param
            # Coerce and clamp the value according to the parameter type.
            coerced = value
            if param.param_type == AnimParameterType.FLOAT.value:
                coerced = _clamp(_safe_float(value, param.default_value),
                                 param.min_value, param.max_value)
            elif param.param_type == AnimParameterType.INT.value:
                coerced = _safe_int(value, param.default_value)
            elif param.param_type == AnimParameterType.BOOL.value:
                coerced = bool(value)
            elif param.param_type == AnimParameterType.TRIGGER.value:
                coerced = bool(value)
            rt["param_values"][name] = coerced
            self._emit(AnimEventKind.STATE_CHANGED.value, f"parameter set: {name}={coerced}",
                       {"blueprint_id": blueprint_id, "name": name,
                        "value": coerced},
                       blueprint_id=blueprint_id)
            return (True, f"parameter set: {name}={coerced}", bp)

    def get_parameter(self, blueprint_id: str, name: str) -> Optional[Any]:
        """Return the current value of a blueprint parameter."""
        with self._lock:
            rt = self._runtime.get(blueprint_id)
            if rt is None:
                return None
            return rt["param_values"].get(name)

    def list_parameters(self, blueprint_id: str) -> List[AnimParameter]:
        """List all parameter definitions in a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return []
            return list(bp.parameters.values())

    # ------------------------------------------------------------------
    # Blend Space Management
    # ------------------------------------------------------------------

    def create_blend_space(self, blueprint_id: str, space_id: str = "",
                           name: str = "",
                           space_type: str = BlendSpaceType.DIRECTIONAL_2D.value,
                           x_parameter: str = "", y_parameter: str = "",
                           nodes: Optional[List[Dict[str, Any]]] = None,
                           metadata: Optional[Dict[str, Any]] = None
                           ) -> Tuple[bool, str, Optional[BlendSpace]]:
        """Create and attach a blend space to a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", None)
            if len(bp.blend_spaces) >= self._config.max_blend_spaces:
                return (False, "blend space limit reached for blueprint", None)
            sid = space_id or _gen_id("bs", "bs")
            if sid in bp.blend_spaces:
                return (False, f"blend space already exists: {sid}", bp.blend_spaces[sid])
            st = _coerce_enum(BlendSpaceType, space_type, BlendSpaceType.DIRECTIONAL_2D).value
            node_objs: List[BlendSpaceNode] = []
            if nodes:
                for n in nodes:
                    clip_id = str(n.get("clip_id", ""))
                    if clip_id and clip_id not in self._clips:
                        return (False, f"clip not found for node: {clip_id}", None)
                    node_objs.append(BlendSpaceNode(
                        node_id=str(n.get("node_id", "")) or _gen_id("bsn", "bsn"),
                        position_x=_safe_float(n.get("position_x", 0.0), 0.0),
                        position_y=_safe_float(n.get("position_y", 0.0), 0.0),
                        clip_id=clip_id,
                        speed=_clamp(_safe_float(n.get("speed", 1.0), 1.0),
                                     _SPEED_MIN, _SPEED_MAX),
                        metadata=dict(n.get("metadata", {})) if n.get("metadata") else {},
                    ))
            space = BlendSpace(
                space_id=sid, name=name or sid, space_type=st,
                x_parameter=x_parameter, y_parameter=y_parameter,
                nodes=node_objs, metadata=dict(metadata) if metadata else {},
            )
            bp.blend_spaces[sid] = space
            self._emit(AnimEventKind.BLENDED.value, f"blend space created: {sid}",
                       {"blueprint_id": blueprint_id, "space_id": sid,
                        "space_type": st, "node_count": len(node_objs)},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"blend space created: {sid}", space)

    def remove_blend_space(self, blueprint_id: str, space_id: str
                           ) -> Tuple[bool, str]:
        """Remove a blend space from a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}")
            if space_id not in bp.blend_spaces:
                return (False, f"blend space not found: {space_id}")
            del bp.blend_spaces[space_id]
            self._emit(AnimEventKind.BLENDED.value, f"blend space removed: {space_id}",
                       {"blueprint_id": blueprint_id, "space_id": space_id},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"blend space removed: {space_id}")

    def get_blend_space(self, blueprint_id: str, space_id: str) -> Optional[BlendSpace]:
        """Return a blend space by id within a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return None
            return bp.blend_spaces.get(space_id)

    def list_blend_spaces(self, blueprint_id: str) -> List[BlendSpace]:
        """List all blend spaces in a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return []
            return list(bp.blend_spaces.values())

    def sample_blend_space(self, blueprint_id: str, space_id: str,
                           x: float, y: float = 0.0
                           ) -> Tuple[bool, str, Dict[str, Any]]:
        """Sample a blend space at ``(x, y)`` and return clip weights.

        For 1D spaces the two nodes bracketing ``x`` are linearly blended.
        For 2D and radial spaces an inverse-distance weighting of the
        nearest nodes is used so the result is always well-defined.
        """
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", {})
            space = bp.blend_spaces.get(space_id)
            if space is None:
                return (False, f"blend space not found: {space_id}", {})
            nodes = space.nodes
            if not nodes:
                return (True, "blend space has no nodes", {
                    "space_id": space_id, "space_type": space.space_type,
                    "x": x, "y": y, "node_count": 0, "clip_weights": [],
                    "primary_clip": "",
                })
            sx = _safe_float(x, 0.0)
            sy = _safe_float(y, 0.0)
            st = space.space_type
            clip_weights: List[Dict[str, Any]] = []

            if st == BlendSpaceType.DIRECTIONAL_1D.value:
                ordered = sorted(nodes, key=lambda n: n.position_x)
                prev_node = None
                next_node = None
                for n in ordered:
                    if n.position_x <= sx:
                        prev_node = n
                    if n.position_x >= sx and next_node is None:
                        next_node = n
                if prev_node is None:
                    prev_node = ordered[0]
                if next_node is None:
                    next_node = ordered[-1]
                if prev_node is next_node:
                    clip_weights.append({"clip_id": prev_node.clip_id,
                                         "weight": 1.0, "speed": prev_node.speed})
                else:
                    span = next_node.position_x - prev_node.position_x
                    t = 0.0 if abs(span) < 1e-9 else (sx - prev_node.position_x) / span
                    t = _clamp(t, 0.0, 1.0)
                    clip_weights.append({"clip_id": prev_node.clip_id,
                                         "weight": round(1.0 - t, 6),
                                         "speed": prev_node.speed})
                    clip_weights.append({"clip_id": next_node.clip_id,
                                         "weight": round(t, 6),
                                         "speed": next_node.speed})

            elif st == BlendSpaceType.RADIAL.value:
                # Treat (x, y) as a direction whose magnitude selects reach.
                radius = math.sqrt(sx * sx + sy * sy)
                angle = math.atan2(sy, sx) if radius > 1e-9 else 0.0
                scored = []
                for n in nodes:
                    nr = math.sqrt(n.position_x ** 2 + n.position_y ** 2)
                    na = math.atan2(n.position_y, n.position_x) if nr > 1e-9 else 0.0
                    # Angular distance wrapped to [-pi, pi].
                    da = math.atan2(math.sin(angle - na), math.cos(angle - na))
                    dr = abs(nr - radius)
                    dist = math.sqrt(da * da + dr * dr)
                    scored.append((n, dist))
                scored.sort(key=lambda t: t[1])
                nearest = scored[:3]
                weights = [(n, 1.0 / (d * d + 1e-6)) for n, d in nearest]
                total = sum(w for _, w in weights)
                agg: Dict[str, Dict[str, Any]] = {}
                for n, w in weights:
                    slot = agg.setdefault(n.clip_id, {"weight": 0.0, "speed": n.speed})
                    slot["weight"] += w / total
                for cid, info in agg.items():
                    clip_weights.append({"clip_id": cid,
                                         "weight": round(info["weight"], 6),
                                         "speed": info["speed"]})

            else:
                # DIRECTIONAL_2D (and NONE fallback) use inverse-distance weighting.
                scored = []
                for n in nodes:
                    dx = n.position_x - sx
                    dy = n.position_y - sy
                    dist = math.sqrt(dx * dx + dy * dy)
                    scored.append((n, dist))
                # Short-circuit when the sample lands exactly on a node.
                exact = next((n for n, d in scored if d < 1e-9), None)
                if exact is not None:
                    clip_weights.append({"clip_id": exact.clip_id,
                                         "weight": 1.0, "speed": exact.speed})
                else:
                    scored.sort(key=lambda t: t[1])
                    nearest = scored[:3]
                    weights = [(n, 1.0 / (d * d + 1e-6)) for n, d in nearest]
                    total = sum(w for _, w in weights)
                    agg2: Dict[str, Dict[str, Any]] = {}
                    for n, w in weights:
                        slot = agg2.setdefault(n.clip_id, {"weight": 0.0, "speed": n.speed})
                        slot["weight"] += w / total
                    for cid, info in agg2.items():
                        clip_weights.append({"clip_id": cid,
                                             "weight": round(info["weight"], 6),
                                             "speed": info["speed"]})

            clip_weights.sort(key=lambda c: -c["weight"])
            primary = clip_weights[0]["clip_id"] if clip_weights else ""
            self._emit(AnimEventKind.BLENDED.value,
                       f"blend space sampled: {space_id} at ({sx:.3f},{sy:.3f})",
                       {"blueprint_id": blueprint_id, "space_id": space_id,
                        "x": sx, "y": sy, "primary_clip": primary},
                       blueprint_id=blueprint_id)
            return (True, f"blend space sampled: {space_id}", {
                "space_id": space_id,
                "space_type": st,
                "x": sx,
                "y": sy,
                "node_count": len(nodes),
                "clip_weights": clip_weights,
                "primary_clip": primary,
            })

    # ------------------------------------------------------------------
    # Layer Management
    # ------------------------------------------------------------------

    def add_layer(self, blueprint_id: str, layer_id: str = "", name: str = "",
                  weight: float = 1.0, mask_bones: Optional[List[str]] = None,
                  blend_mode: str = AnimBlendMode.OVERRIDE.value,
                  metadata: Optional[Dict[str, Any]] = None
                  ) -> Tuple[bool, str, AnimBlueprint]:
        """Add a composited animation layer to a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            if len(bp.layers) >= self._config.max_layers_per_blueprint:
                return (False, "layer limit reached for blueprint", bp)
            lid = layer_id or _gen_id("layer", "layer")
            if lid in bp.layers:
                return (False, f"layer already exists: {lid}", bp)
            w = _clamp(_safe_float(weight, 1.0), _WEIGHT_MIN, _WEIGHT_MAX)
            bm = _coerce_enum(AnimBlendMode, blend_mode, AnimBlendMode.OVERRIDE).value
            layer = AnimLayer(
                layer_id=lid, name=name or lid, weight=w,
                mask_bones=list(mask_bones) if mask_bones else [],
                blend_mode=bm, current_state=bp.current_state, active=True,
                metadata=dict(metadata) if metadata else {},
            )
            bp.layers[lid] = layer
            self._emit(AnimEventKind.LAYER_ADDED.value, f"layer added: {lid}",
                       {"blueprint_id": blueprint_id, "layer_id": lid,
                        "weight": w, "blend_mode": bm},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"layer added: {lid}", bp)

    def remove_layer(self, blueprint_id: str, layer_id: str
                     ) -> Tuple[bool, str, AnimBlueprint]:
        """Remove a layer by id from a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            if layer_id not in bp.layers:
                return (False, f"layer not found: {layer_id}", bp)
            del bp.layers[layer_id]
            self._emit(AnimEventKind.LAYER_ADDED.value, f"layer removed: {layer_id}",
                       {"blueprint_id": blueprint_id, "layer_id": layer_id},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"layer removed: {layer_id}", bp)

    def set_layer_weight(self, blueprint_id: str, layer_id: str,
                         weight: float) -> Tuple[bool, str, AnimBlueprint]:
        """Set the blend weight of an existing layer."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            layer = bp.layers.get(layer_id)
            if layer is None:
                return (False, f"layer not found: {layer_id}", bp)
            layer.weight = _clamp(_safe_float(weight, 1.0), _WEIGHT_MIN, _WEIGHT_MAX)
            self._emit(AnimEventKind.BLENDED.value,
                       f"layer weight set: {layer_id}={layer.weight}",
                       {"blueprint_id": blueprint_id, "layer_id": layer_id,
                        "weight": layer.weight},
                       blueprint_id=blueprint_id)
            return (True, f"layer weight set: {layer_id}={layer.weight}", bp)

    def list_layers(self, blueprint_id: str) -> List[AnimLayer]:
        """List all layers in a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return []
            return list(bp.layers.values())

    # ------------------------------------------------------------------
    # IK Management
    # ------------------------------------------------------------------

    def add_ik_chain(self, blueprint_id: str, chain_id: str = "", name: str = "",
                     chain_type: str = IKChainType.LIMB_2BONE.value,
                     root_bone: str = "", mid_bones: Optional[List[str]] = None,
                     tip_bone: str = "",
                     target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                     pole_vector: Tuple[float, float, float] = (1.0, 0.0, 0.0),
                     weight: float = 1.0,
                     metadata: Optional[Dict[str, Any]] = None
                     ) -> Tuple[bool, str, AnimBlueprint]:
        """Add an inverse kinematics chain to a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            cid = chain_id or _gen_id("ik", "ik")
            if cid in bp.ik_chains:
                return (False, f"ik chain already exists: {cid}", bp)
            ct = _coerce_enum(IKChainType, chain_type, IKChainType.LIMB_2BONE).value
            w = _clamp(_safe_float(weight, 1.0), _WEIGHT_MIN, _WEIGHT_MAX)
            chain = IKChain(
                chain_id=cid, name=name or cid, chain_type=ct,
                root_bone=root_bone, mid_bones=list(mid_bones) if mid_bones else [],
                tip_bone=tip_bone,
                target_position=(float(target_position[0]), float(target_position[1]),
                                 float(target_position[2])),
                pole_vector=(float(pole_vector[0]), float(pole_vector[1]),
                             float(pole_vector[2])),
                weight=w, metadata=dict(metadata) if metadata else {},
            )
            bp.ik_chains[cid] = chain
            self._emit(AnimEventKind.IK_SOLVED.value, f"ik chain added: {cid}",
                       {"blueprint_id": blueprint_id, "chain_id": cid,
                        "chain_type": ct},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"ik chain added: {cid}", bp)

    def remove_ik_chain(self, blueprint_id: str, chain_id: str
                        ) -> Tuple[bool, str, AnimBlueprint]:
        """Remove an IK chain by id from a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            if chain_id not in bp.ik_chains:
                return (False, f"ik chain not found: {chain_id}", bp)
            del bp.ik_chains[chain_id]
            self._emit(AnimEventKind.IK_SOLVED.value, f"ik chain removed: {chain_id}",
                       {"blueprint_id": blueprint_id, "chain_id": chain_id},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"ik chain removed: {chain_id}", bp)

    def set_ik_target(self, blueprint_id: str, chain_id: str,
                      target_position: Tuple[float, float, float]
                      ) -> Tuple[bool, str, AnimBlueprint]:
        """Set the world-space target position for an IK chain."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            chain = bp.ik_chains.get(chain_id)
            if chain is None:
                return (False, f"ik chain not found: {chain_id}", bp)
            chain.target_position = (float(target_position[0]),
                                     float(target_position[1]),
                                     float(target_position[2]))
            self._emit(AnimEventKind.IK_SOLVED.value,
                       f"ik target set: {chain_id}",
                       {"blueprint_id": blueprint_id, "chain_id": chain_id,
                        "target_position": list(chain.target_position)},
                       blueprint_id=blueprint_id)
            return (True, f"ik target set: {chain_id}", bp)

    def set_ik_weight(self, blueprint_id: str, chain_id: str,
                      weight: float) -> Tuple[bool, str, AnimBlueprint]:
        """Set the influence weight of an IK chain."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            chain = bp.ik_chains.get(chain_id)
            if chain is None:
                return (False, f"ik chain not found: {chain_id}", bp)
            chain.weight = _clamp(_safe_float(weight, 1.0), _WEIGHT_MIN, _WEIGHT_MAX)
            self._emit(AnimEventKind.IK_SOLVED.value,
                       f"ik weight set: {chain_id}={chain.weight}",
                       {"blueprint_id": blueprint_id, "chain_id": chain_id,
                        "weight": chain.weight},
                       blueprint_id=blueprint_id)
            return (True, f"ik weight set: {chain_id}={chain.weight}", bp)

    def list_ik_chains(self, blueprint_id: str) -> List[IKChain]:
        """List all IK chains in a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return []
            return list(bp.ik_chains.values())

    def solve_ik(self, blueprint_id: str, chain_id: str
                 ) -> Tuple[bool, str, Dict[str, Any]]:
        """Solve a 2-bone inverse kinematics chain toward its target.

        Implements the classic analytical 2-bone IK solver: the root bone
        is pinned, the tip bone reaches toward the target, and the mid
        joint bends into the plane defined by the pole vector. The
        solution is returned as a dict of joint world positions.

        For 3-bone spine chains and look-at chains the solver falls back
        to a stretched reach with a single bend toward the target.
        """
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", {})
            chain = bp.ik_chains.get(chain_id)
            if chain is None:
                return (False, f"ik chain not found: {chain_id}", {})
            if not self._config.enable_ik:
                return (False, "ik is disabled in config", {})

            rest = chain.metadata.get("rest_positions", {}) if chain.metadata else {}
            root = (
                float(rest.get("root", (0.0, 0.0, 0.0))[0]),
                float(rest.get("root", (0.0, 0.0, 0.0))[1]),
                float(rest.get("root", (0.0, 0.0, 0.0))[2]),
            )
            mid_rest = rest.get("mid", (0.0, 0.6, 0.0))
            tip_rest = rest.get("tip", (0.0, 1.2, 0.0))
            mid = (float(mid_rest[0]), float(mid_rest[1]), float(mid_rest[2]))
            tip = (float(tip_rest[0]), float(tip_rest[1]), float(tip_rest[2]))

            target = (float(chain.target_position[0]),
                      float(chain.target_position[1]),
                      float(chain.target_position[2]))
            pole = (float(chain.pole_vector[0]),
                    float(chain.pole_vector[1]),
                    float(chain.pole_vector[2])) if (
                chain.pole_vector and any(abs(c) > 1e-9 for c in chain.pole_vector)
            ) else (1.0, 0.0, 0.0)

            len1 = _vec_length(_vec_sub(mid, root))
            len2 = _vec_length(_vec_sub(tip, mid))
            if len1 < 1e-6:
                len1 = 1.0
            if len2 < 1e-6:
                len2 = 1.0

            root_to_target = _vec_sub(target, root)
            dist = _vec_length(root_to_target)
            max_reach = len1 + len2 - 1e-4
            min_reach = abs(len1 - len2) + 1e-4
            clamped_dist = _clamp(dist, min_reach, max_reach)

            direction = _vec_normalize(root_to_target)
            if _vec_length(direction) < 1e-9:
                direction = (0.0, 1.0, 0.0)

            # Law of cosines: angle at the root between root->target and root->mid.
            cos_a = (len1 * len1 + clamped_dist * clamped_dist - len2 * len2) / (
                2.0 * len1 * clamped_dist
            )
            cos_a = _clamp(cos_a, -1.0, 1.0)
            angle_a = math.acos(cos_a)

            # Bend axis perpendicular to the target direction and the pole vector.
            pole_dir = _vec_normalize(pole)
            bend_axis = _vec_cross(direction, pole_dir)
            if _vec_length(bend_axis) < 1e-9:
                bend_axis = _vec_cross(direction, (0.0, 0.0, 1.0))
                if _vec_length(bend_axis) < 1e-9:
                    bend_axis = _vec_cross(direction, (1.0, 0.0, 0.0))
            bend_axis = _vec_normalize(bend_axis)

            mid_dir = _vec_rotate_around_axis(direction, bend_axis, angle_a)
            mid_pos = _vec_add(root, _vec_scale(mid_dir, len1))
            # Project the tip onto the target, clamped to the second bone length.
            tip_dir = _vec_normalize(_vec_sub(target, mid_pos))
            tip_pos = _vec_add(mid_pos, _vec_scale(tip_dir, len2))

            weight = _clamp(chain.weight, 0.0, 1.0)
            final_mid = _vec_lerp(mid, mid_pos, weight)
            final_tip = _vec_lerp(tip, tip_pos, weight)

            ct = chain.chain_type
            joint_chain: List[List[float]] = [
                list(root), list(final_mid), list(final_tip),
            ]
            # For spine chains with multiple mid bones, distribute the bend.
            if ct in (IKChainType.SPINE_CHAIN.value, IKChainType.LIMB_3BONE.value) and chain.mid_bones:
                mid_count = len(chain.mid_bones)
                distributed: List[List[float]] = [list(root)]
                for i in range(mid_count):
                    t_frac = (i + 1) / (mid_count + 1)
                    distributed.append(list(_vec_lerp(root, final_mid, t_frac)))
                distributed.append(list(final_tip))
                joint_chain = distributed

            result = {
                "chain_id": chain_id,
                "chain_type": ct,
                "root_bone": chain.root_bone,
                "tip_bone": chain.tip_bone,
                "root": list(root),
                "mid": list(final_mid),
                "tip": list(final_tip),
                "target": list(target),
                "pole_vector": list(pole),
                "bone_lengths": [len1, len2],
                "reach": round(dist, 6),
                "clamped_reach": round(clamped_dist, 6),
                "weight": weight,
                "angle_root": round(angle_a, 6),
                "joint_chain": joint_chain,
                "solved": True,
            }
            self._emit(AnimEventKind.IK_SOLVED.value,
                       f"ik solved: {chain_id}",
                       {"blueprint_id": blueprint_id, "chain_id": chain_id,
                        "reach": dist, "weight": weight},
                       blueprint_id=blueprint_id)
            return (True, f"ik solved: {chain_id}", result)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def play_blueprint(self, blueprint_id: str) -> Tuple[bool, str, AnimBlueprint]:
        """Start playback of a blueprint from its current state."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            rt = self._runtime.get(blueprint_id)
            if rt is None:
                rt = self._fresh_runtime(bp)
                self._runtime[blueprint_id] = rt
            rt["status"] = AnimStatus.PLAYING.value
            self._emit(AnimEventKind.PLAYED.value, f"blueprint played: {blueprint_id}",
                       {"blueprint_id": blueprint_id,
                        "state": bp.current_state},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"blueprint played: {blueprint_id}", bp)

    def pause_blueprint(self, blueprint_id: str) -> Tuple[bool, str, AnimBlueprint]:
        """Pause playback of a blueprint, retaining its playback time."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            rt = self._runtime.get(blueprint_id)
            if rt is None:
                rt = self._fresh_runtime(bp)
                self._runtime[blueprint_id] = rt
            rt["status"] = AnimStatus.PAUSED.value
            self._emit(AnimEventKind.STOPPED.value, f"blueprint paused: {blueprint_id}",
                       {"blueprint_id": blueprint_id},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"blueprint paused: {blueprint_id}", bp)

    def stop_blueprint(self, blueprint_id: str) -> Tuple[bool, str, AnimBlueprint]:
        """Stop playback of a blueprint and reset its playback time."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            rt = self._runtime.get(blueprint_id)
            if rt is None:
                rt = self._fresh_runtime(bp)
                self._runtime[blueprint_id] = rt
            rt["status"] = AnimStatus.IDLE.value
            rt["playback_time"] = 0.0
            rt["blend_remaining"] = 0.0
            rt["blend_duration"] = 0.0
            rt["blend_from_state"] = ""
            rt["blend_to_state"] = ""
            self._emit(AnimEventKind.STOPPED.value, f"blueprint stopped: {blueprint_id}",
                       {"blueprint_id": blueprint_id},
                       blueprint_id=blueprint_id)
            self._refresh_stats()
            return (True, f"blueprint stopped: {blueprint_id}", bp)

    def set_playback_speed(self, blueprint_id: str, speed: float
                           ) -> Tuple[bool, str, AnimBlueprint]:
        """Set the per-blueprint playback speed multiplier."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", AnimBlueprint())
            rt = self._runtime.get(blueprint_id)
            if rt is None:
                rt = self._fresh_runtime(bp)
                self._runtime[blueprint_id] = rt
            rt["playback_speed"] = _clamp(_safe_float(speed, 1.0),
                                          _SPEED_MIN, _SPEED_MAX)
            self._emit(AnimEventKind.PLAYED.value,
                       f"playback speed set: {rt['playback_speed']}",
                       {"blueprint_id": blueprint_id,
                        "speed": rt["playback_speed"]},
                       blueprint_id=blueprint_id)
            return (True, f"playback speed set: {rt['playback_speed']}", bp)

    def get_current_state(self, blueprint_id: str) -> Optional[AnimState]:
        """Return the currently active state of a blueprint."""
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None or not bp.current_state:
                return None
            return bp.states.get(bp.current_state)

    # ------------------------------------------------------------------
    # AI / Procedural
    # ------------------------------------------------------------------

    def auto_generate_transition(self, blueprint_id: str, source_state: str,
                                 context: Optional[Dict[str, Any]] = None
                                 ) -> Tuple[bool, str, Optional[AnimTransition]]:
        """Procedurally generate and register a transition.

        The context dict may carry a ``target_state``, ``trigger`` name,
        ``duration``, ``blend_mode``, and ``priority``. When the target is
        omitted the system picks a plausible destination state by looking
        for a state whose clip tags differ from the source clip.
        """
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", None)
            if source_state and source_state not in bp.states:
                return (False, f"source state not found: {source_state}", None)
            ctx = context or {}
            target = str(ctx.get("target_state", ""))
            if not target:
                # Pick a candidate target that is not the source.
                source_clip = bp.states.get(source_state).clip_id if source_state else ""
                src_tags = set(self._clips.get(source_clip).tags) if (
                    source_clip and source_clip in self._clips
                ) else set()
                candidates = [s for s in bp.states.values() if s.state_id != source_state]

                def _overlap(candidate: AnimState) -> int:
                    """Return the tag overlap count between source and candidate."""
                    if not candidate.clip_id or candidate.clip_id not in self._clips:
                        return 0
                    return len(src_tags & set(self._clips[candidate.clip_id].tags))

                # Prefer states whose clip tags do not overlap the source.
                ranked = sorted(candidates, key=lambda s: -_overlap(s))
                if not ranked:
                    return (False, "no candidate target state available", None)
                target = ranked[0].state_id
            if target not in bp.states:
                return (False, f"target state not found: {target}", None)
            duration = _safe_float(ctx.get("duration", self._config.default_blend_duration),
                                   self._config.default_blend_duration)
            blend_mode = str(ctx.get("blend_mode", AnimBlendMode.OVERRIDE.value))
            priority = _safe_int(ctx.get("priority", 0), 0)
            trigger = str(ctx.get("trigger", ""))
            conditions: List[TransitionCondition] = []
            if trigger:
                conditions.append(TransitionCondition(
                    parameter_name=trigger,
                    condition_type=AnimTransitionCondition.EQUALS.value,
                    threshold=1.0, compare_value=True,
                ))
            ok, msg, _ = self.add_transition(
                blueprint_id, "", source_state, target, duration,
                blend_mode, [c.__dict__ for c in conditions] if False else None,
                priority, {"auto_generated": True, "trigger": trigger},
            )
            if not ok:
                return (False, msg, None)
            # add_transition keeps the list sorted; fetch the newest match.
            for t in bp.transitions:
                if (t.source_state == source_state and t.target_state == target
                        and t.metadata.get("auto_generated")):
                    return (True, f"auto transition generated: {t.transition_id}", t)
            # Fallback: return the last transition.
            if bp.transitions:
                return (True, "auto transition generated", bp.transitions[-1])
            return (False, "auto transition generation failed", None)

    def suggest_state(self, blueprint_id: str,
                      context: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, str, Optional[AnimState]]:
        """Suggest a state for the blueprint based on a context dict.

        The suggestion considers the current parameter values and any
        ``action`` hint in the context, ranking candidate states by how
        well their clip tags match the requested action.
        """
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", None)
            if not bp.states:
                return (False, "blueprint has no states", None)
            ctx = context or {}
            action = str(ctx.get("action", "")).lower()
            rt = self._runtime.get(blueprint_id, {})
            params = rt.get("param_values", {}) if rt else {}
            current = bp.current_state

            best: Optional[AnimState] = None
            best_score = -1.0
            for state in bp.states.values():
                if state.state_id == current:
                    continue
                clip = self._clips.get(state.clip_id)
                score = 0.0
                if clip:
                    tags = [t.lower() for t in clip.tags]
                    if action and action in tags:
                        score += 2.0
                    if action and any(action in t for t in tags):
                        score += 1.0
                    # Locomotion tuning: prefer walk/run when speed is high.
                    if "walk" in tags and _safe_float(params.get("speed"), 0.0) > 0.1:
                        score += 0.5
                    if "run" in tags and _safe_float(params.get("speed"), 0.0) > 3.0:
                        score += 0.8
                    if "fall" in tags and not bool(params.get("is_grounded", True)):
                        score += 1.2
                    if "death" in tags and _safe_float(params.get("health"), 100.0) < 1.0:
                        score += 2.0
                score += random.random() * 0.01  # tie-breaker
                if score > best_score:
                    best_score = score
                    best = state
            if best is None:
                best = next(iter(bp.states.values()))
            self._emit(AnimEventKind.STATE_CHANGED.value,
                       f"state suggested: {best.state_id}",
                       {"blueprint_id": blueprint_id,
                        "state_id": best.state_id,
                        "score": round(best_score, 4)},
                       blueprint_id=blueprint_id)
            return (True, f"state suggested: {best.state_id}", best)

    def optimize_blend_tree(self, blueprint_id: str
                            ) -> Tuple[bool, str, List[str]]:
        """Inspect a blueprint and return optimization suggestions.

        The analysis detects duplicate transitions, unused blend spaces,
        over-weighted layers, and IK chains that may be too influential,
        returning a list of human-readable recommendations.
        """
        with self._lock:
            bp = self._blueprints.get(blueprint_id)
            if bp is None:
                return (False, f"blueprint not found: {blueprint_id}", [])
            suggestions: List[str] = []

            # Duplicate transition detection (same source and target).
            seen_pairs: Dict[Tuple[str, str], int] = {}
            for t in bp.transitions:
                key = (t.source_state, t.target_state)
                seen_pairs[key] = seen_pairs.get(key, 0) + 1
            for (src, dst), count in seen_pairs.items():
                if count > 1:
                    suggestions.append(
                        f"Merge {count} duplicate transitions from '{src}' to '{dst}'."
                    )

            # Orphan states with no inbound or outbound transitions.
            connected: set = set()
            for t in bp.transitions:
                connected.add(t.source_state)
                connected.add(t.target_state)
            for state in bp.states.values():
                if state.state_id not in connected and state.state_id != bp.current_state:
                    suggestions.append(
                        f"State '{state.state_id}' is unreachable; add a transition or remove it."
                    )

            # Blend spaces with too few nodes to interpolate meaningfully.
            for space in bp.blend_spaces.values():
                if len(space.nodes) < 2:
                    suggestions.append(
                        f"Blend space '{space.space_id}' has fewer than 2 nodes; "
                        "add samples for smoother blending."
                    )

            # Layers whose weight dominates the base layer.
            for layer in bp.layers.values():
                if layer.active and layer.weight >= 0.99 and layer.blend_mode == AnimBlendMode.OVERRIDE.value:
                    if layer.layer_id != "layer_base":
                        suggestions.append(
                            f"Layer '{layer.layer_id}' is at full override weight; "
                            "consider lowering it to preserve base motion."
                        )

            # IK chains whose weight may cause popping.
            for chain in bp.ik_chains.values():
                if chain.weight >= 0.99:
                    suggestions.append(
                        f"IK chain '{chain.chain_id}' is at full weight; "
                        "ramp the weight for smoother corrections."
                    )

            # States bound to missing clips.
            for state in bp.states.values():
                if state.clip_id and state.clip_id not in self._clips:
                    suggestions.append(
                        f"State '{state.state_id}' points to missing clip '{state.clip_id}'."
                    )

            if not suggestions:
                suggestions.append("Blend tree is well-formed; no optimizations needed.")
            self._emit(AnimEventKind.BLENDED.value,
                       f"blend tree optimized: {len(suggestions)} suggestion(s)",
                       {"blueprint_id": blueprint_id,
                        "suggestion_count": len(suggestions)},
                       blueprint_id=blueprint_id)
            return (True, f"generated {len(suggestions)} suggestion(s)", suggestions)

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------

    def get_config(self) -> AnimConfig:
        """Return the current system configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, AnimConfig]:
        """Update one or more configuration fields by keyword."""
        with self._lock:
            allowed = set(AnimConfig.__dataclass_fields__.keys())
            updated: List[str] = []
            for key, value in kwargs.items():
                if key not in allowed:
                    continue
                if key in ("enable_ik", "enable_root_motion"):
                    setattr(self._config, key, bool(value))
                elif key in ("max_blueprints", "max_clips", "max_layers_per_blueprint",
                             "max_states_per_blueprint", "max_blend_spaces"):
                    setattr(self._config, key, _safe_int(value, getattr(self._config, key)))
                else:
                    setattr(self._config, key, _safe_float(value, getattr(self._config, key)))
                updated.append(key)
            if not updated:
                return (False, "no valid config keys provided", self._config)
            return (True, f"updated config: {', '.join(updated)}", self._config)

    def get_stats(self) -> AnimStats:
        """Return aggregate statistics as an :class:`AnimStats` dataclass."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> AnimSnapshot:
        """Return a point-in-time snapshot as an :class:`AnimSnapshot` dataclass."""
        with self._lock:
            active = sum(
                1 for bid in self._blueprints
                if self._runtime.get(bid, {}).get("status") == AnimStatus.PLAYING.value
            )
            total_layers = sum(len(b.layers) for b in self._blueprints.values())
            return AnimSnapshot(
                initialized=self._initialized,
                tick_count=self._tick_count,
                active_blueprints=active,
                playing_states=active,
                total_clips=len(self._clips),
                total_layers=total_layers,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a compact status dict for quick observability."""
        with self._lock:
            active = sum(
                1 for bid in self._blueprints
                if self._runtime.get(bid, {}).get("status") == AnimStatus.PLAYING.value
            )
            return {
                "initialized": self._initialized,
                "clips": len(self._clips),
                "blueprints": len(self._blueprints),
                "active_blueprints": active,
                "events": len(self._events),
                "tick_count": self._tick_count,
                "config": self._config.to_dict(),
            }

    def list_events(self, limit: int = _DEFAULT_LIST_LIMIT) -> List[AnimEvent]:
        """Return the most recent events, capped by ``limit``."""
        with self._lock:
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT), 1, _MAX_LIST_LIMIT)
            return list(self._events[-cap:])

    def tick(self, dt: float) -> Dict[str, Any]:
        """Advance animation playback by ``dt`` seconds.

        For each playing blueprint the playback time advances according to
        the state speed, global speed, and per-blueprint playback speed.
        Loop modes are honored, transitions are evaluated against the
        current parameter values, and active blend windows decay over time.
        """
        with self._lock:
            step = _safe_float(dt, 0.0)
            if step < 0.0:
                step = 0.0
            self._tick_count += 1
            global_speed = self._config.global_speed
            transitions_triggered = 0
            playing = 0
            finished = 0

            for bid, bp in self._blueprints.items():
                rt = self._runtime.get(bid)
                if not rt:
                    continue
                if rt["status"] not in (AnimStatus.PLAYING.value,
                                        AnimStatus.BLENDING.value):
                    continue
                playing += 1
                current = bp.current_state
                state = bp.states.get(current) if current else None
                if state is None:
                    continue
                clip = self._clips.get(state.clip_id)
                if clip is None:
                    continue

                spd = (rt["playback_speed"] * state.speed * global_speed)
                if spd < 0.0:
                    spd = 0.0
                rt["playback_time"] += step * spd
                dur = clip.duration
                if dur > 0.0:
                    lm = state.loop_mode
                    if lm == AnimLoopMode.ONCE.value:
                        if rt["playback_time"] >= dur:
                            rt["playback_time"] = dur
                            rt["status"] = AnimStatus.FINISHED.value
                            finished += 1
                    elif lm == AnimLoopMode.LOOP.value:
                        rt["playback_time"] = rt["playback_time"] % dur
                    elif lm == AnimLoopMode.PING_PONG.value:
                        cycle = rt["playback_time"] % (2.0 * dur)
                        if cycle <= dur:
                            rt["playback_time"] = cycle
                        else:
                            rt["playback_time"] = 2.0 * dur - cycle
                    elif lm == AnimLoopMode.CLAMP.value:
                        if rt["playback_time"] > dur:
                            rt["playback_time"] = dur

                # Evaluate outbound transitions against current parameters.
                if rt["status"] in (AnimStatus.PLAYING.value,
                                    AnimStatus.BLENDING.value):
                    if self._evaluate_transitions(bp, rt):
                        transitions_triggered += 1

                # Decay the active blend window.
                if rt["blend_remaining"] > 0.0:
                    rt["blend_remaining"] -= step
                    if rt["blend_remaining"] <= 0.0:
                        rt["blend_remaining"] = 0.0
                        rt["blend_duration"] = 0.0
                        rt["blend_from_state"] = ""
                        rt["blend_to_state"] = ""
                        if rt["status"] == AnimStatus.BLENDING.value:
                            rt["status"] = AnimStatus.PLAYING.value

            self._stats.tick_count = self._tick_count
            self._stats.active_blueprints = playing
            self._stats.playing_states = playing
            self._stats.total_transitions_triggered += transitions_triggered
            return {
                "tick_count": self._tick_count,
                "dt": step,
                "transitions_triggered": transitions_triggered,
                "playing": playing,
                "finished": finished,
                "active_blueprints": playing,
            }

    def reset(self) -> Tuple[bool, str]:
        """Clear all data and re-seed the system with defaults."""
        with self._lock:
            self._clips.clear()
            self._blueprints.clear()
            self._runtime.clear()
            self._events.clear()
            self._config = AnimConfig()
            self._stats = AnimStats()
            self._tick_count = 0
            self._event_counter = 0
            with self._init_lock:
                self._initialized = False
                self._seed()
                self._initialized = True
            return (True, "system reset and re-seeded")

    # ------------------------------------------------------------------
    # Internal: Transition Evaluation
    # ------------------------------------------------------------------

    def _evaluate_transitions(self, bp: AnimBlueprint,
                              rt: Dict[str, Any]) -> bool:
        """Evaluate outbound transitions for the current state.

        Returns ``True`` when a transition was triggered. Transitions are
        evaluated in priority order (highest first); the first whose
        conditions all pass fires immediately.
        """
        current = bp.current_state
        param_values = rt.get("param_values", {})
        for t in bp.transitions:
            if t.source_state != current:
                continue
            if not t.conditions:
                # A transition with no conditions never auto-fires here so
                # that explicit trigger_transition remains the only path.
                continue
            if all(self._check_condition(c, param_values) for c in t.conditions):
                # Trigger the transition in-place.
                bp.current_state = t.target_state
                rt["blend_remaining"] = t.duration
                rt["blend_duration"] = t.duration
                rt["blend_from_state"] = current
                rt["blend_to_state"] = t.target_state
                rt["playback_time"] = 0.0
                if rt["status"] == AnimStatus.PLAYING.value:
                    rt["status"] = AnimStatus.BLENDING.value
                self._stats.total_transitions_triggered += 1
                self._emit(AnimEventKind.TRANSITIONED.value,
                           f"auto transition: {current} -> {t.target_state}",
                           {"blueprint_id": bp.blueprint_id,
                            "transition_id": t.transition_id,
                            "from": current, "to": t.target_state},
                           blueprint_id=bp.blueprint_id)
                return True
        return False

    def _check_condition(self, cond: TransitionCondition,
                         param_values: Dict[str, Any]) -> bool:
        """Evaluate a single transition condition against parameter values."""
        value = param_values.get(cond.parameter_name)
        ct = cond.condition_type
        if isinstance(ct, AnimTransitionCondition):
            ct = ct.value
        if ct == AnimTransitionCondition.EQUALS.value:
            return value == cond.compare_value
        if ct == AnimTransitionCondition.NOT_EQUALS.value:
            return value != cond.compare_value
        if value is None:
            return False
        try:
            if ct == AnimTransitionCondition.GREATER.value:
                return float(value) > float(cond.threshold)
            if ct == AnimTransitionCondition.LESS.value:
                return float(value) < float(cond.threshold)
            if ct == AnimTransitionCondition.GREATER_EQUAL.value:
                return float(value) >= float(cond.threshold)
            if ct == AnimTransitionCondition.LESS_EQUAL.value:
                return float(value) <= float(cond.threshold)
            if ct == AnimTransitionCondition.IN_RANGE.value:
                low = float(cond.threshold)
                high = float(cond.compare_value) if cond.compare_value is not None else low
                return low <= float(value) <= high
        except (TypeError, ValueError):
            return False
        return False


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------


def get_animation_state_machine_system() -> AnimationStateMachineSystem:
    """Return the singleton AnimationStateMachineSystem instance."""
    return AnimationStateMachineSystem.get_instance()
