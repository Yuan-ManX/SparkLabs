"""
SparkLabs Engine - Particle & VFX System

Manages real-time particle effects and visual effects (VFX) for the
game engine. The system owns a registry of particle emitters (each a
bundle of typed parameters such as emitter type, shape, emission rate,
burst count, particle lifetime, start size, start speed, start color,
gravity, drag, and blend mode), particle effects that compose multiple
emitters into a complete VFX sequence, active particle batches that
represent running simulations of an effect or burst, animation curves
for scalar property animation, color gradients for color property
animation, and an audit trail of every lifecycle event.

An integrated AI layer can generate a complete particle effect from a
natural-language description ("roaring campfire", "grenade explosion",
"magic spell impact", "rain splash"), suggest which parameters a
designer should adjust next for a given emitter, and optimize an
existing effect for a target frame rate by reducing particle counts,
emission rates, and disabling expensive modules.

Architecture:
  ParticleVFXSystem (singleton)
    |-- ParticleEmitterType, ParticleBlendMode, ParticleShape,
       ParticleSimulationSpace, ParticleStatus, VFXCategory, SortMode,
       EmitterShape, ParticleEventKind
    |-- ParticleModule, ParticleEmitter, ParticleEffect, ParticleBatch,
       ParticleKeyframe, ParticleCurve, VFXGradient, ParticleVFXConfig,
       ParticleVFXStats, ParticleVFXSnapshot, ParticleVFXEvent
    |-- get_particle_vfx_system

Core Capabilities:
  - register_emitter / get_emitter / list_emitters / remove_emitter /
    update_emitter: emitter registry management with FIFO eviction.
  - create_effect / get_effect / list_effects / remove_effect /
    update_effect / add_emitter_to_effect / remove_emitter_from_effect:
    compose ordered emitter lists into named effects.
  - play_effect / stop_effect / pause_effect / resume_effect: drive the
    lifecycle of a running effect instance (a ParticleBatch).
  - get_batch / list_batches / remove_batch / burst: inspect, list,
    remove, and one-shot emit a burst of particles from an emitter.
  - create_curve / get_curve / list_curves / remove_curve /
    sample_curve: scalar animation curves with keyframe interpolation.
  - create_gradient / get_gradient / list_gradients / remove_gradient /
    sample_gradient: color gradients with stop interpolation.
  - export_effect / import_effect: JSON serialization round-trip that
    carries the effect and all of its emitters.
  - auto_generate_effect: AI-driven effect generation from a
    natural-language description (fire, smoke, explosion, spark, magic,
    blood, dust, water, and combinations thereof).
  - suggest_parameters: AI-driven parameter suggestion that inspects an
    emitter and proposes the next parameters a designer should tune.
  - optimize_effect: AI-driven optimization that reduces particle
    counts, emission rates, and disables expensive modules so the
    effect meets a target frame rate.
  - get_status / get_stats / get_snapshot / get_config / set_config /
    tick / reset / list_events: observability, tuning, and lifecycle.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`ParticleVFXSystem.get_instance` or the module-level
:func:`get_particle_vfx_system` factory. All public methods are guarded
by the re-entrant lock.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest entry
# is evicted in FIFO order to keep memory growth predictable under heavy
# dynamic use (for example a game that spawns dozens of burst effects
# during a large battle or registers a fresh batch for every projectile).
_MAX_EMITTERS: int = 1000
_MAX_EFFECTS: int = 1000
_MAX_BATCHES: int = 2000
_MAX_CURVES: int = 500
_MAX_GRADIENTS: int = 500
_MAX_EVENTS: int = 10000

# Numeric bounds for common parameters.
_RATE_MIN: float = 0.0
_RATE_MAX: float = 10000.0
_LIFETIME_MIN: float = 0.0
_LIFETIME_MAX: float = 600.0
_MAX_PARTICLES_MIN: int = 1
_MAX_PARTICLES_MAX: int = 100000
_SPEED_MIN: float = 0.0
_SPEED_MAX: float = 1000.0
_SIZE_MIN: float = 0.0
_SIZE_MAX: float = 1000.0
_DRAG_MIN: float = 0.0
_DRAG_MAX: float = 10.0
_INTENSITY_MIN: float = 0.0
_INTENSITY_MAX: float = 10.0
_SORT_PRIORITY_MIN: float = -1000.0
_SORT_PRIORITY_MAX: float = 1000.0
_BURST_COUNT_MIN: int = 0
_BURST_COUNT_MAX: int = 50000
_BATCH_SPEED_MIN: float = 0.0
_BATCH_SPEED_MAX: float = 10.0

# List limits.
_DEFAULT_LIST_LIMIT: int = 100
_MAX_LIST_LIMIT: int = 500


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix.

    Used as the default factory for ``created_at`` / ``updated_at`` fields
    and for event timestamps throughout the module.
    """
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier with an
            underscore. When omitted the bare hexadecimal id is returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits ``max_size``.

    Uses insertion-order iteration so the first inserted key is dropped
    first. This keeps memory growth bounded for FIFO-style stores.
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

    Handles enums (by value), dicts, lists, tuples, sets, dataclasses
    (via ``__dataclass_fields__``), and objects exposing ``to_dict``.
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

    Checks ``__dataclass_fields__`` BEFORE ``to_dict`` to avoid recursion
    when a dataclass also defines a ``to_dict`` method that delegates back
    to this helper.
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


def _normalize_keyframes(
    keyframes: Optional[List[Any]],
) -> List["ParticleKeyframe"]:
    """Normalize a list of keyframe inputs into ParticleKeyframe objects.

    Accepts existing ParticleKeyframe objects, dicts with ``time`` and
    ``value`` keys, or two-element ``(time, value)`` tuples/lists.
    """
    if not keyframes:
        return []
    result: List[ParticleKeyframe] = []
    for kf in keyframes:
        if isinstance(kf, ParticleKeyframe):
            result.append(kf)
        elif isinstance(kf, dict):
            result.append(
                ParticleKeyframe(
                    keyframe_id=str(kf.get("keyframe_id", "")) or _new_id("kf"),
                    time=_clamp(_safe_float(kf.get("time", 0.0), 0.0), 0.0, 1.0),
                    value=_safe_float(kf.get("value", 0.0), 0.0),
                    in_tangent=_safe_float(kf.get("in_tangent", 0.0), 0.0),
                    out_tangent=_safe_float(kf.get("out_tangent", 0.0), 0.0),
                    interpolation=str(kf.get("interpolation", "linear")),
                    metadata=dict(kf.get("metadata", {})),
                )
            )
        elif isinstance(kf, (list, tuple)) and len(kf) >= 2:
            result.append(
                ParticleKeyframe(
                    keyframe_id=_new_id("kf"),
                    time=_clamp(_safe_float(kf[0], 0.0), 0.0, 1.0),
                    value=_safe_float(kf[1], 0.0),
                )
            )
    return result


def _normalize_stops(
    stops: Optional[List[Any]],
) -> List[Tuple[float, float, float, float, float]]:
    """Normalize a list of gradient stop inputs into ``(time, r, g, b, a)`` tuples.

    Accepts five-element ``(time, r, g, b, a)`` tuples/lists or dicts
    with ``time`` and ``color`` or individual ``r``/``g``/``b``/``a``
    keys. Color channels are clamped to ``[0.0, 1.0]`` and time is
    clamped to ``[0.0, 1.0]``.
    """
    if not stops:
        return []
    result: List[Tuple[float, float, float, float, float]] = []
    for stop in stops:
        if isinstance(stop, (list, tuple)) and len(stop) >= 5:
            result.append(
                (
                    _clamp(_safe_float(stop[0], 0.0), 0.0, 1.0),
                    _clamp(_safe_float(stop[1], 0.0), 0.0, 1.0),
                    _clamp(_safe_float(stop[2], 0.0), 0.0, 1.0),
                    _clamp(_safe_float(stop[3], 0.0), 0.0, 1.0),
                    _clamp(_safe_float(stop[4], 1.0), 0.0, 1.0),
                )
            )
        elif isinstance(stop, dict):
            time = _clamp(_safe_float(stop.get("time", 0.0), 0.0), 0.0, 1.0)
            color = stop.get("color")
            if isinstance(color, (list, tuple)) and len(color) >= 4:
                r = _clamp(_safe_float(color[0], 0.0), 0.0, 1.0)
                g = _clamp(_safe_float(color[1], 0.0), 0.0, 1.0)
                b = _clamp(_safe_float(color[2], 0.0), 0.0, 1.0)
                a = _clamp(_safe_float(color[3], 1.0), 0.0, 1.0)
            else:
                r = _clamp(_safe_float(stop.get("r", 1.0), 1.0), 0.0, 1.0)
                g = _clamp(_safe_float(stop.get("g", 1.0), 1.0), 0.0, 1.0)
                b = _clamp(_safe_float(stop.get("b", 1.0), 1.0), 0.0, 1.0)
                a = _clamp(_safe_float(stop.get("a", 1.0), 1.0), 0.0, 1.0)
            result.append((time, r, g, b, a))
    return result


def _make_keyframe(
    time: float, value: float, interpolation: str = "linear"
) -> "ParticleKeyframe":
    """Build a ParticleKeyframe with a generated id."""
    return ParticleKeyframe(
        keyframe_id=_new_id("kf"),
        time=_clamp(_safe_float(time, 0.0), 0.0, 1.0),
        value=_safe_float(value, 0.0),
        interpolation=interpolation,
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ParticleEmitterType(str, Enum):
    """Classification of a particle emitter by its volume shape.

    Each value names a canonical emitter volume that determines how
    particles are distributed at spawn time. MESH uses a custom mesh
    surface as the emission volume.
    """

    POINT = "point"
    BOX = "box"
    SPHERE = "sphere"
    CONE = "cone"
    CYLINDER = "cylinder"
    MESH = "mesh"
    LINE = "line"
    CIRCLE = "circle"


class ParticleBlendMode(str, Enum):
    """Blend mode used when compositing particles onto the framebuffer."""

    ADDITIVE = "additive"
    ALPHA = "alpha"
    MULTIPLY = "multiply"
    SUBTRACT = "subtract"
    SCREEN = "screen"


class ParticleShape(str, Enum):
    """Render primitive used to draw each particle.

    POINT renders a single pixel or small point sprite. QUAD renders a
    camera-facing quad. SPRITE renders a textured camera-facing quad.
    TRAIL and STRIP render connected line strips. MESH renders a small
    mesh instance per particle.
    """

    POINT = "point"
    QUAD = "quad"
    CUBE = "cube"
    SPHERE = "sphere"
    SPRITE = "sprite"
    TRAIL = "trail"
    STRIP = "strip"
    MESH = "mesh"


class ParticleSimulationSpace(str, Enum):
    """Coordinate space in which particles simulate after emission.

    LOCAL simulates in the emitter's local space so particles follow the
    emitter. WORLD simulates in world space so particles are left behind
    when the emitter moves. LOCAL_WITH_SCALE is like LOCAL but also
    inherits the emitter's scale.
    """

    LOCAL = "local"
    WORLD = "world"
    LOCAL_WITH_SCALE = "local_with_scale"


class ParticleStatus(str, Enum):
    """Lifecycle state of a particle effect or batch."""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    FINISHED = "finished"


class VFXCategory(str, Enum):
    """Functional grouping of a particle effect.

    Used by the effect browser to group effects into combat,
    environment, magic, weather, destruction, celebration, and UI
    buckets. CUSTOM is used for effects that do not fit any named
    family.
    """

    COMBAT = "combat"
    ENVIRONMENT = "environment"
    MAGIC = "magic"
    WEATHER = "weather"
    DESTRUCTION = "destruction"
    CELEBRATION = "celebration"
    UI = "ui"
    CUSTOM = "custom"


class SortMode(str, Enum):
    """Particle sorting mode within a batch.

    NONE renders particles in emission order. BY_DISTANCE sorts by
    distance to the camera. BY_AGE sorts by particle age. BY_DEPTH sorts
    by view-space depth.
    """

    NONE = "none"
    BY_DISTANCE = "by_distance"
    BY_AGE = "by_age"
    BY_DEPTH = "by_depth"


class EmitterShape(str, Enum):
    """Emission volume shape for the emitter.

    This is distinct from ParticleEmitterType in that it describes the
    exact geometric shape used to sample spawn positions, while
    ParticleEmitterType is the high-level classification. For example an
    emitter of type CONE may use a DISK or ARC shape at its base.
    """

    POINT = "point"
    LINE = "line"
    CIRCLE = "circle"
    BOX = "box"
    SPHERE = "sphere"
    CONE = "cone"
    CYLINDER = "cylinder"
    DISK = "disk"
    ARC = "arc"


class ParticleEventKind(str, Enum):
    """Audit event kinds emitted by the particle VFX system."""

    EMITTER_CREATED = "emitter_created"
    EMITTER_REMOVED = "emitter_removed"
    EFFECT_PLAYED = "effect_played"
    EFFECT_STOPPED = "effect_stopped"
    PARTICLE_BURST = "particle_burst"
    CONFIG_CHANGED = "config_changed"
    SYSTEM_RESET = "system_reset"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Default Parameter Table
# ---------------------------------------------------------------------------

# Default values for new emitters by category. Centralizing the defaults
# here keeps the seed data and the register_emitter method consistent
# and avoids magic numbers scattered through the code.
_DEFAULT_EMITTER_PARAMS: Dict[str, Dict[str, Any]] = {
    "rate": 10.0,
    "burst_count": 0,
    "burst_interval": 0.0,
    "lifetime": 5.0,
    "particle_lifetime": (1.0, 2.0),
    "particle_shape": ParticleShape.QUAD.value,
    "blend_mode": ParticleBlendMode.ALPHA.value,
    "simulation_space": ParticleSimulationSpace.WORLD.value,
    "max_particles": 1000,
    "start_size": (0.1, 0.2),
    "start_speed": (1.0, 3.0),
    "start_color": (1.0, 1.0, 1.0, 1.0),
    "gravity": (0.0, -9.8, 0.0),
    "drag": 0.0,
    "sort_mode": SortMode.NONE.value,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ParticleModule:
    """A typed behavior module that modifies particle simulation over time.

    Modules are the building blocks of an emitter. Each module controls
    one aspect of particle behavior such as lifetime, velocity over life,
    color over life, size over life, force, collision, noise, or
    sub-emission. Modules can link to a ParticleCurve for animated scalar
    properties and to a VFXGradient for animated color properties.

    Attributes:
        module_id: Unique module identifier.
        name: Display name.
        module_type: The module family (e.g. "lifetime",
            "velocity_over_life", "color_over_life", "size_over_life",
            "force", "collision", "noise", "sub_emitter").
        enabled: Whether the module contributes to the simulation.
        parameters: Module-specific parameters as a free-form mapping.
        curve_id: Optional ParticleCurve id for animated scalar properties.
        gradient_id: Optional VFXGradient id for animated color properties.
        sort_order: Ordering hint for module evaluation.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    module_id: str
    name: str
    module_type: str = "lifetime"
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    curve_id: str = ""
    gradient_id: str = ""
    sort_order: float = 0.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleEmitter:
    """A named particle emitter configuration.

    An emitter bundles an emitter type, emission shape, emission rate,
    burst settings, particle lifetime range, particle shape, blend mode,
    simulation space, max particle count, start size/speed/color ranges,
    gravity, drag, sort mode, and a set of behavior modules. Emitters are
    the primary unit of particle configuration.

    Attributes:
        emitter_id: Unique emitter identifier.
        name: Display name.
        description: Human-readable description.
        emitter_type: The ParticleEmitterType value name.
        shape: The EmitterShape value name.
        rate: Continuous emission rate in particles per second.
        burst_count: Number of particles emitted per burst.
        burst_interval: Seconds between bursts (0 = single burst).
        lifetime: Emitter duration in seconds (0 = infinite).
        particle_lifetime: ``(min, max)`` lifetime of each particle.
        particle_shape: The ParticleShape value name.
        blend_mode: The ParticleBlendMode value name.
        simulation_space: The ParticleSimulationSpace value name.
        max_particles: Hard cap on simultaneously active particles.
        start_size: ``(min, max)`` start size of each particle.
        start_speed: ``(min, max)`` start speed of each particle.
        start_color: ``(r, g, b, a)`` start color of each particle.
        gravity: ``(x, y, z)`` gravity applied to each particle.
        drag: Linear drag coefficient applied to particle velocity.
        modules: Behavior modules keyed by module id.
        sort_mode: The SortMode value name.
        enabled: Whether the emitter is eligible for simulation.
        tags: Searchable tags for filtering.
        thumbnail_url: Optional thumbnail asset URL.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    emitter_id: str
    name: str
    description: str = ""
    emitter_type: str = ParticleEmitterType.POINT.value
    shape: str = EmitterShape.POINT.value
    rate: float = 10.0
    burst_count: int = 0
    burst_interval: float = 0.0
    lifetime: float = 5.0
    particle_lifetime: Tuple[float, float] = (1.0, 2.0)
    particle_shape: str = ParticleShape.QUAD.value
    blend_mode: str = ParticleBlendMode.ALPHA.value
    simulation_space: str = ParticleSimulationSpace.WORLD.value
    max_particles: int = 1000
    start_size: Tuple[float, float] = (0.1, 0.2)
    start_speed: Tuple[float, float] = (1.0, 3.0)
    start_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    gravity: Tuple[float, float, float] = (0.0, -9.8, 0.0)
    drag: float = 0.0
    modules: Dict[str, ParticleModule] = field(default_factory=dict)
    sort_mode: str = SortMode.NONE.value
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    thumbnail_url: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleEffect:
    """A complete VFX effect composed of multiple emitters.

    An effect bundles an ordered list of emitter ids, a duration, loop
    behavior, prewarm, delay, sort priority, and tags. Effects are the
    primary unit of VFX playback: calling ``play_effect`` spawns a
    ParticleBatch that simulates all of the effect's emitters together.

    Attributes:
        effect_id: Unique effect identifier.
        name: Display name.
        description: Human-readable description.
        category: The VFXCategory value name.
        emitter_ids: Ordered list of emitter ids in the effect.
        duration: Effect duration in seconds (0 = looping indefinitely).
        looping: Whether the effect loops when it reaches its duration.
        prewarm: Whether to pre-simulate the effect on play so it starts
            in a steady state.
        delay: Seconds to wait before the effect starts emitting.
        status: The ParticleStatus value name.
        sort_priority: Ordering hint for effect playback.
        tags: Searchable tags for filtering.
        thumbnail_url: Optional thumbnail asset URL.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    effect_id: str
    name: str
    description: str = ""
    category: str = VFXCategory.CUSTOM.value
    emitter_ids: List[str] = field(default_factory=list)
    duration: float = 0.0
    looping: bool = True
    prewarm: bool = False
    delay: float = 0.0
    status: str = ParticleStatus.IDLE.value
    sort_priority: float = 0.0
    tags: List[str] = field(default_factory=list)
    thumbnail_url: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleBatch:
    """A batch of active particle simulations.

    A batch represents a running instance of an effect or a one-shot
    burst. It tracks the world position, rotation, and scale of the
    emission origin, the simulation age, the number of active and
    emitted particles, the playback speed, and the lifecycle status.

    Attributes:
        batch_id: Unique batch identifier.
        effect_id: The effect id this batch was spawned from (when
            applicable).
        emitter_ids: The list of emitter ids this batch simulates.
        name: Display name.
        position: ``(x, y, z)`` world position of the emission origin.
        rotation: ``(x, y, z)`` euler rotation in degrees.
        scale: ``(x, y, z)`` scale of the emission origin.
        status: The ParticleStatus value name.
        age: Seconds since the batch started playing.
        duration: Batch duration in seconds (0 = looping).
        active_particles: Estimated count of currently alive particles.
        max_particles: Hard cap on simultaneously active particles.
        emitted_total: Cumulative count of particles emitted.
        looping: Whether the batch loops when it reaches its duration.
        speed: Playback speed multiplier.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    batch_id: str
    effect_id: str = ""
    emitter_ids: List[str] = field(default_factory=list)
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    status: str = ParticleStatus.PLAYING.value
    age: float = 0.0
    duration: float = 0.0
    active_particles: int = 0
    max_particles: int = 1000
    emitted_total: int = 0
    looping: bool = False
    speed: float = 1.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleKeyframe:
    """A single keyframe in an animation curve.

    Attributes:
        keyframe_id: Unique keyframe identifier.
        time: Normalized time in the range ``[0.0, 1.0]``.
        value: The scalar value at this keyframe.
        in_tangent: Tangent controlling the interpolation slope
            approaching this keyframe from the left.
        out_tangent: Tangent controlling the interpolation slope leaving
            this keyframe to the right.
        interpolation: Interpolation mode ("linear", "constant",
            "bezier").
        metadata: Free-form extension data.
    """

    keyframe_id: str
    time: float = 0.0
    value: float = 0.0
    in_tangent: float = 0.0
    out_tangent: float = 0.0
    interpolation: str = "linear"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleCurve:
    """An animation curve composed of ordered keyframes.

    Curves are sampled at a normalized time ``t`` in ``[0.0, 1.0]`` to
    produce a scalar value. When ``loop`` is True the input time wraps
    around the ``[0.0, 1.0]`` range. ``pre_value`` and ``post_value``
    define the value returned before the first and after the last
    keyframe respectively.

    Attributes:
        curve_id: Unique curve identifier.
        name: Display name.
        keyframes: Ordered list of ParticleKeyframe objects.
        loop: Whether the curve loops its input time.
        pre_value: Value returned when sampling before the first keyframe.
        post_value: Value returned when sampling after the last keyframe.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    curve_id: str
    name: str
    keyframes: List[ParticleKeyframe] = field(default_factory=list)
    loop: bool = False
    pre_value: float = 0.0
    post_value: float = 1.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VFXGradient:
    """A color gradient composed of ordered color stops.

    Gradients are sampled at a normalized time ``t`` in ``[0.0, 1.0]`` to
    produce an ``(r, g, b, a)`` color tuple. When ``loop`` is True the
    input time wraps around the ``[0.0, 1.0]`` range. Each stop is a
    ``(time, r, g, b, a)`` tuple with all channels in ``[0.0, 1.0]``.

    Attributes:
        gradient_id: Unique gradient identifier.
        name: Display name.
        stops: Ordered list of ``(time, r, g, b, a)`` tuples.
        loop: Whether the gradient loops its input time.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    gradient_id: str
    name: str
    stops: List[Tuple[float, float, float, float, float]] = field(
        default_factory=list
    )
    loop: bool = False
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleVFXConfig:
    """Global tuning parameters for the particle VFX system.

    Attributes:
        max_emitters: Maximum number of emitters retained before FIFO
            eviction.
        max_effects: Maximum number of effects retained.
        max_batches: Maximum number of active batches retained.
        max_curves: Maximum number of curves retained.
        max_gradients: Maximum number of gradients retained.
        max_events: Maximum number of audit events retained.
        max_particles_per_batch: Hard cap on particles per batch.
        default_simulation_space: Default simulation space for new
            emitters.
        default_blend_mode: Default blend mode for new emitters.
        default_shape: Default particle shape for new emitters.
        enable_sorting: Whether particle sorting is globally enabled.
        enable_gpu: Whether GPU simulation is enabled.
        metadata: Free-form extension data.
    """

    max_emitters: int = _MAX_EMITTERS
    max_effects: int = _MAX_EFFECTS
    max_batches: int = _MAX_BATCHES
    max_curves: int = _MAX_CURVES
    max_gradients: int = _MAX_GRADIENTS
    max_events: int = _MAX_EVENTS
    max_particles_per_batch: int = 5000
    default_simulation_space: str = ParticleSimulationSpace.WORLD.value
    default_blend_mode: str = ParticleBlendMode.ALPHA.value
    default_shape: str = ParticleShape.QUAD.value
    enable_sorting: bool = True
    enable_gpu: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleVFXStats:
    """Aggregate statistics for the particle VFX system.

    Attributes:
        total_emitters: Total number of registered emitters.
        total_effects: Total number of registered effects.
        total_batches: Total number of batches (active and finished).
        total_curves: Total number of registered curves.
        total_gradients: Total number of registered gradients.
        active_batches: Number of batches currently playing.
        active_particles: Estimated total alive particles across all
            playing batches.
        total_bursts: Cumulative count of burst calls.
        total_emitted: Cumulative count of particles emitted.
        tick_count: Number of ticks processed.
    """

    total_emitters: int = 0
    total_effects: int = 0
    total_batches: int = 0
    total_curves: int = 0
    total_gradients: int = 0
    active_batches: int = 0
    active_particles: int = 0
    total_bursts: int = 0
    total_emitted: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleVFXSnapshot:
    """Full state snapshot of the particle VFX system.

    Attributes:
        timestamp: Snapshot timestamp.
        emitters: Serialized emitter list (bounded for size).
        effects: Serialized effect list.
        batches: Serialized batch list (bounded for size).
        curves: Serialized curve list.
        gradients: Serialized gradient list.
        events: Serialized event list (bounded for size).
        stats: Serialized statistics.
    """

    timestamp: str = field(default_factory=_now)
    emitters: List[Dict[str, Any]] = field(default_factory=list)
    effects: List[Dict[str, Any]] = field(default_factory=list)
    batches: List[Dict[str, Any]] = field(default_factory=list)
    curves: List[Dict[str, Any]] = field(default_factory=list)
    gradients: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleVFXEvent:
    """An audit event emitted by the particle VFX system.

    Attributes:
        event_id: Unique event identifier.
        timestamp: Event timestamp.
        event_type: The ParticleEventKind value name.
        target_id: The id of the emitter, effect, or batch the event
            concerns (when applicable).
        description: Human-readable summary of the event.
        metadata: Free-form extension data.
    """

    event_id: str
    timestamp: str = field(default_factory=_now)
    event_type: str = ""
    target_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Particle VFX System
# ---------------------------------------------------------------------------


class ParticleVFXSystem:
    """Manages particle emitters, effects, batches, curves, gradients,
    and the AI VFX generation pipeline.

    The system is a thread-safe singleton. All public methods take the
    instance lock before mutating shared state so that concurrent calls
    from render, gameplay, and editor threads remain consistent.
    """

    _instance: Optional["ParticleVFXSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        # Primary stores
        self._emitters: Dict[str, ParticleEmitter] = {}
        self._effects: Dict[str, ParticleEffect] = {}
        self._batches: Dict[str, ParticleBatch] = {}
        self._curves: Dict[str, ParticleCurve] = {}
        self._gradients: Dict[str, VFXGradient] = {}
        self._events: List[ParticleVFXEvent] = []
        # Config and stats
        self._config = ParticleVFXConfig()
        self._stats = ParticleVFXStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._batch_counter: int = 0
        self.initialize()

    @classmethod
    def get_instance(cls) -> "ParticleVFXSystem":
        """Return the singleton ParticleVFXSystem instance.

        Uses double-checked locking so the instance is created exactly
        once even when multiple threads call this concurrently on first
        use.
        """
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the system with seed data (idempotent).

        Guarded by the init lock so repeated calls are no-ops after the
        first successful seed. This is invoked from ``__init__`` and from
        ``reset`` to repopulate the default data set.
        """
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed()
            self._initialized = True

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the system with seed data.

        Seeds eight preset emitter types covering the canonical VFX
        families (fire, smoke, explosion, spark, magic aura, blood
        spray, dust, water splash), five particle effects combining
        those emitters, four animation curves, three color gradients,
        and six audit events.
        """
        now = _now()

        # --- Particle Emitters (8) ---
        # Each emitter is configured with parameters chosen to evoke its
        # named effect. Fire rises with additive blending, smoke drifts
        # upward with alpha blending, explosions burst radially, sparks
        # fall with gravity, magic auras orbit gently, blood sprays arc
        # downward, dust settles slowly, and water splashes in a sphere.

        fire_emitter = ParticleEmitter(
            emitter_id="emitter_fire",
            name="Fire",
            description="Rising flame particles with additive blending.",
            emitter_type=ParticleEmitterType.POINT.value,
            shape=EmitterShape.CONE.value,
            rate=60.0,
            burst_count=0,
            burst_interval=0.0,
            lifetime=0.0,
            particle_lifetime=(0.5, 1.0),
            particle_shape=ParticleShape.QUAD.value,
            blend_mode=ParticleBlendMode.ADDITIVE.value,
            simulation_space=ParticleSimulationSpace.WORLD.value,
            max_particles=500,
            start_size=(0.2, 0.4),
            start_speed=(1.0, 3.0),
            start_color=(1.0, 0.6, 0.1, 1.0),
            gravity=(0.0, 2.0, 0.0),
            drag=0.5,
            sort_mode=SortMode.BY_AGE.value,
            enabled=True,
            tags=["fire", "heat", "combustion"],
            thumbnail_url="assets://vfx/emitter_fire.png",
            created_at=now,
            updated_at=now,
            metadata={"seed": True, "gradient": "gradient_fire"},
        )
        fire_emitter.modules["mod_color_over_life"] = ParticleModule(
            module_id="mod_color_over_life",
            name="Color Over Life",
            module_type="color_over_life",
            enabled=True,
            parameters={"opacity_curve": "fade_out"},
            gradient_id="gradient_fire",
            sort_order=0.0,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        fire_emitter.modules["mod_size_over_life"] = ParticleModule(
            module_id="mod_size_over_life",
            name="Size Over Life",
            module_type="size_over_life",
            enabled=True,
            parameters={"scale_curve": "fade_out"},
            curve_id="curve_fade_out",
            sort_order=1.0,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._emitters["emitter_fire"] = fire_emitter

        smoke_emitter = ParticleEmitter(
            emitter_id="emitter_smoke",
            name="Smoke",
            description="Drifting smoke clouds with alpha blending.",
            emitter_type=ParticleEmitterType.POINT.value,
            shape=EmitterShape.CONE.value,
            rate=25.0,
            burst_count=0,
            burst_interval=0.0,
            lifetime=0.0,
            particle_lifetime=(2.0, 4.0),
            particle_shape=ParticleShape.QUAD.value,
            blend_mode=ParticleBlendMode.ALPHA.value,
            simulation_space=ParticleSimulationSpace.WORLD.value,
            max_particles=300,
            start_size=(0.5, 1.0),
            start_speed=(0.5, 1.5),
            start_color=(0.3, 0.3, 0.3, 0.6),
            gravity=(0.0, 1.0, 0.0),
            drag=0.8,
            sort_mode=SortMode.BY_AGE.value,
            enabled=True,
            tags=["smoke", "fog", "vapor"],
            thumbnail_url="assets://vfx/emitter_smoke.png",
            created_at=now,
            updated_at=now,
            metadata={"seed": True, "gradient": "gradient_smoke"},
        )
        smoke_emitter.modules["mod_color_over_life"] = ParticleModule(
            module_id="mod_color_over_life",
            name="Color Over Life",
            module_type="color_over_life",
            enabled=True,
            parameters={"opacity_curve": "fade_out"},
            gradient_id="gradient_smoke",
            sort_order=0.0,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        smoke_emitter.modules["mod_size_over_life"] = ParticleModule(
            module_id="mod_size_over_life",
            name="Size Over Life",
            module_type="size_over_life",
            enabled=True,
            parameters={"scale_curve": "fade_in"},
            curve_id="curve_fade_in",
            sort_order=1.0,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._emitters["emitter_smoke"] = smoke_emitter

        explosion_emitter = ParticleEmitter(
            emitter_id="emitter_explosion",
            name="Explosion",
            description="Radial burst of fiery debris.",
            emitter_type=ParticleEmitterType.SPHERE.value,
            shape=EmitterShape.SPHERE.value,
            rate=0.0,
            burst_count=200,
            burst_interval=0.0,
            lifetime=0.0,
            particle_lifetime=(0.5, 1.5),
            particle_shape=ParticleShape.QUAD.value,
            blend_mode=ParticleBlendMode.ADDITIVE.value,
            simulation_space=ParticleSimulationSpace.WORLD.value,
            max_particles=500,
            start_size=(0.3, 0.6),
            start_speed=(5.0, 15.0),
            start_color=(1.0, 0.8, 0.2, 1.0),
            gravity=(0.0, -3.0, 0.0),
            drag=0.3,
            sort_mode=SortMode.NONE.value,
            enabled=True,
            tags=["explosion", "combat", "destruction"],
            thumbnail_url="assets://vfx/emitter_explosion.png",
            created_at=now,
            updated_at=now,
            metadata={"seed": True, "gradient": "gradient_fire"},
        )
        explosion_emitter.modules["mod_color_over_life"] = ParticleModule(
            module_id="mod_color_over_life",
            name="Color Over Life",
            module_type="color_over_life",
            enabled=True,
            parameters={"opacity_curve": "fade_out"},
            gradient_id="gradient_fire",
            sort_order=0.0,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._emitters["emitter_explosion"] = explosion_emitter

        spark_emitter = ParticleEmitter(
            emitter_id="emitter_spark",
            name="Spark",
            description="Bright electric sparks falling with gravity.",
            emitter_type=ParticleEmitterType.POINT.value,
            shape=EmitterShape.CONE.value,
            rate=120.0,
            burst_count=0,
            burst_interval=0.0,
            lifetime=0.0,
            particle_lifetime=(0.2, 0.5),
            particle_shape=ParticleShape.POINT.value,
            blend_mode=ParticleBlendMode.ADDITIVE.value,
            simulation_space=ParticleSimulationSpace.WORLD.value,
            max_particles=800,
            start_size=(0.02, 0.05),
            start_speed=(3.0, 8.0),
            start_color=(1.0, 0.9, 0.5, 1.0),
            gravity=(0.0, -9.8, 0.0),
            drag=0.1,
            sort_mode=SortMode.NONE.value,
            enabled=True,
            tags=["spark", "electric", "energy"],
            thumbnail_url="assets://vfx/emitter_spark.png",
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._emitters["emitter_spark"] = spark_emitter

        magic_aura_emitter = ParticleEmitter(
            emitter_id="emitter_magic_aura",
            name="Magic Aura",
            description="Glowing arcane particles orbiting gently.",
            emitter_type=ParticleEmitterType.SPHERE.value,
            shape=EmitterShape.SPHERE.value,
            rate=40.0,
            burst_count=0,
            burst_interval=0.0,
            lifetime=0.0,
            particle_lifetime=(1.0, 2.0),
            particle_shape=ParticleShape.SPRITE.value,
            blend_mode=ParticleBlendMode.ADDITIVE.value,
            simulation_space=ParticleSimulationSpace.WORLD.value,
            max_particles=400,
            start_size=(0.3, 0.5),
            start_speed=(0.5, 2.0),
            start_color=(0.5, 0.2, 1.0, 1.0),
            gravity=(0.0, 0.5, 0.0),
            drag=0.6,
            sort_mode=SortMode.BY_DISTANCE.value,
            enabled=True,
            tags=["magic", "aura", "arcane"],
            thumbnail_url="assets://vfx/emitter_magic_aura.png",
            created_at=now,
            updated_at=now,
            metadata={"seed": True, "gradient": "gradient_magic"},
        )
        magic_aura_emitter.modules["mod_color_over_life"] = ParticleModule(
            module_id="mod_color_over_life",
            name="Color Over Life",
            module_type="color_over_life",
            enabled=True,
            parameters={"opacity_curve": "pulse"},
            gradient_id="gradient_magic",
            curve_id="curve_pulse",
            sort_order=0.0,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._emitters["emitter_magic_aura"] = magic_aura_emitter

        blood_spray_emitter = ParticleEmitter(
            emitter_id="emitter_blood_spray",
            name="Blood Spray",
            description="Crimson blood spray arcing downward.",
            emitter_type=ParticleEmitterType.POINT.value,
            shape=EmitterShape.CONE.value,
            rate=100.0,
            burst_count=0,
            burst_interval=0.0,
            lifetime=0.0,
            particle_lifetime=(0.3, 0.8),
            particle_shape=ParticleShape.QUAD.value,
            blend_mode=ParticleBlendMode.ALPHA.value,
            simulation_space=ParticleSimulationSpace.WORLD.value,
            max_particles=600,
            start_size=(0.05, 0.15),
            start_speed=(4.0, 10.0),
            start_color=(0.8, 0.0, 0.0, 1.0),
            gravity=(0.0, -9.8, 0.0),
            drag=0.3,
            sort_mode=SortMode.NONE.value,
            enabled=True,
            tags=["blood", "combat", "gore"],
            thumbnail_url="assets://vfx/emitter_blood_spray.png",
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._emitters["emitter_blood_spray"] = blood_spray_emitter

        dust_emitter = ParticleEmitter(
            emitter_id="emitter_dust",
            name="Dust",
            description="Settling dust clouds from a box volume.",
            emitter_type=ParticleEmitterType.BOX.value,
            shape=EmitterShape.BOX.value,
            rate=20.0,
            burst_count=0,
            burst_interval=0.0,
            lifetime=0.0,
            particle_lifetime=(1.0, 3.0),
            particle_shape=ParticleShape.QUAD.value,
            blend_mode=ParticleBlendMode.ALPHA.value,
            simulation_space=ParticleSimulationSpace.WORLD.value,
            max_particles=300,
            start_size=(0.2, 0.5),
            start_speed=(0.5, 2.0),
            start_color=(0.7, 0.6, 0.4, 0.4),
            gravity=(0.0, -1.0, 0.0),
            drag=1.5,
            sort_mode=SortMode.BY_AGE.value,
            enabled=True,
            tags=["dust", "debris", "environment"],
            thumbnail_url="assets://vfx/emitter_dust.png",
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._emitters["emitter_dust"] = dust_emitter

        water_splash_emitter = ParticleEmitter(
            emitter_id="emitter_water_splash",
            name="Water Splash",
            description="Blue water droplets splashing outward.",
            emitter_type=ParticleEmitterType.SPHERE.value,
            shape=EmitterShape.SPHERE.value,
            rate=80.0,
            burst_count=0,
            burst_interval=0.0,
            lifetime=0.0,
            particle_lifetime=(0.4, 1.0),
            particle_shape=ParticleShape.QUAD.value,
            blend_mode=ParticleBlendMode.ALPHA.value,
            simulation_space=ParticleSimulationSpace.WORLD.value,
            max_particles=500,
            start_size=(0.05, 0.15),
            start_speed=(3.0, 8.0),
            start_color=(0.3, 0.6, 1.0, 0.8),
            gravity=(0.0, -9.8, 0.0),
            drag=0.2,
            sort_mode=SortMode.NONE.value,
            enabled=True,
            tags=["water", "splash", "liquid"],
            thumbnail_url="assets://vfx/emitter_water_splash.png",
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._emitters["emitter_water_splash"] = water_splash_emitter

        # --- Particle Effects (5) ---
        effect_seeds: List[Tuple[str, str, str, str, List[str], float, bool, bool, float, float, List[str]]] = [
            (
                "effect_campfire", "Campfire", "A roaring campfire with flames, smoke, and sparks.",
                VFXCategory.ENVIRONMENT.value,
                ["emitter_fire", "emitter_smoke", "emitter_spark"],
                0.0, True, False, 0.0, 0.0,
                ["campfire", "fire", "ambient"],
            ),
            (
                "effect_grenade", "Grenade Explosion", "A grenade detonation with explosion, smoke, and dust.",
                VFXCategory.COMBAT.value,
                ["emitter_explosion", "emitter_smoke", "emitter_dust"],
                3.0, False, False, 0.0, 10.0,
                ["grenade", "explosion", "combat"],
            ),
            (
                "effect_magic_blast", "Magic Blast", "An arcane magic blast with aura and sparks.",
                VFXCategory.MAGIC.value,
                ["emitter_magic_aura", "emitter_spark"],
                2.0, False, False, 0.0, 5.0,
                ["magic", "blast", "arcane"],
            ),
            (
                "effect_blood_impact", "Blood Impact", "A blood spray impact with sparks.",
                VFXCategory.COMBAT.value,
                ["emitter_blood_spray", "emitter_spark"],
                1.0, False, False, 0.0, 8.0,
                ["blood", "impact", "combat"],
            ),
            (
                "effect_rain_splash", "Rain Puddle Splash", "Rain hitting a puddle with splashes and dust.",
                VFXCategory.WEATHER.value,
                ["emitter_water_splash", "emitter_dust"],
                0.0, True, False, 0.0, 0.0,
                ["rain", "splash", "weather"],
            ),
        ]
        for (
            eid, name, desc, category, emitter_ids, duration, looping,
            prewarm, delay, priority, tags,
        ) in effect_seeds:
            effect = ParticleEffect(
                effect_id=eid,
                name=name,
                description=desc,
                category=category,
                emitter_ids=list(emitter_ids),
                duration=duration,
                looping=looping,
                prewarm=prewarm,
                delay=delay,
                status=ParticleStatus.IDLE.value,
                sort_priority=priority,
                tags=list(tags),
                thumbnail_url=f"assets://vfx/{eid}.png",
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
            )
            self._effects[eid] = effect

        # --- Animation Curves (4) ---
        curve_fade_in = ParticleCurve(
            curve_id="curve_fade_in",
            name="Fade In",
            keyframes=[
                ParticleKeyframe(
                    keyframe_id="kf_fade_in_0",
                    time=0.0, value=0.0, interpolation="linear",
                ),
                ParticleKeyframe(
                    keyframe_id="kf_fade_in_1",
                    time=1.0, value=1.0, interpolation="linear",
                ),
            ],
            loop=False,
            pre_value=0.0,
            post_value=1.0,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._curves["curve_fade_in"] = curve_fade_in

        curve_fade_out = ParticleCurve(
            curve_id="curve_fade_out",
            name="Fade Out",
            keyframes=[
                ParticleKeyframe(
                    keyframe_id="kf_fade_out_0",
                    time=0.0, value=1.0, interpolation="linear",
                ),
                ParticleKeyframe(
                    keyframe_id="kf_fade_out_1",
                    time=1.0, value=0.0, interpolation="linear",
                ),
            ],
            loop=False,
            pre_value=1.0,
            post_value=0.0,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._curves["curve_fade_out"] = curve_fade_out

        curve_pulse = ParticleCurve(
            curve_id="curve_pulse",
            name="Pulse",
            keyframes=[
                ParticleKeyframe(
                    keyframe_id="kf_pulse_0",
                    time=0.0, value=0.0, interpolation="linear",
                ),
                ParticleKeyframe(
                    keyframe_id="kf_pulse_1",
                    time=0.5, value=1.0, interpolation="linear",
                ),
                ParticleKeyframe(
                    keyframe_id="kf_pulse_2",
                    time=1.0, value=0.0, interpolation="linear",
                ),
            ],
            loop=True,
            pre_value=0.0,
            post_value=0.0,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._curves["curve_pulse"] = curve_pulse

        curve_sine_wave = ParticleCurve(
            curve_id="curve_sine_wave",
            name="Sine Wave",
            keyframes=[
                ParticleKeyframe(
                    keyframe_id="kf_sine_0",
                    time=0.0, value=0.0, interpolation="linear",
                ),
                ParticleKeyframe(
                    keyframe_id="kf_sine_1",
                    time=0.25, value=1.0, interpolation="linear",
                ),
                ParticleKeyframe(
                    keyframe_id="kf_sine_2",
                    time=0.5, value=0.0, interpolation="linear",
                ),
                ParticleKeyframe(
                    keyframe_id="kf_sine_3",
                    time=0.75, value=-1.0, interpolation="linear",
                ),
                ParticleKeyframe(
                    keyframe_id="kf_sine_4",
                    time=1.0, value=0.0, interpolation="linear",
                ),
            ],
            loop=True,
            pre_value=0.0,
            post_value=0.0,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._curves["curve_sine_wave"] = curve_sine_wave

        # --- Color Gradients (3) ---
        gradient_fire = VFXGradient(
            gradient_id="gradient_fire",
            name="Fire Gradient",
            stops=[
                (0.0, 1.0, 1.0, 0.8, 1.0),
                (0.25, 1.0, 0.6, 0.1, 1.0),
                (0.6, 0.9, 0.2, 0.0, 0.8),
                (1.0, 0.3, 0.0, 0.0, 0.0),
            ],
            loop=False,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._gradients["gradient_fire"] = gradient_fire

        gradient_smoke = VFXGradient(
            gradient_id="gradient_smoke",
            name="Smoke Gradient",
            stops=[
                (0.0, 0.6, 0.6, 0.6, 0.8),
                (0.5, 0.4, 0.4, 0.4, 0.5),
                (1.0, 0.2, 0.2, 0.2, 0.0),
            ],
            loop=False,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._gradients["gradient_smoke"] = gradient_smoke

        gradient_magic = VFXGradient(
            gradient_id="gradient_magic",
            name="Magic Gradient",
            stops=[
                (0.0, 0.3, 0.8, 1.0, 1.0),
                (0.5, 0.6, 0.2, 1.0, 0.8),
                (1.0, 1.0, 0.2, 0.8, 0.0),
            ],
            loop=False,
            created_at=now,
            updated_at=now,
            metadata={"seed": True},
        )
        self._gradients["gradient_magic"] = gradient_magic

        # --- Events (6) ---
        event_seeds: List[Tuple[str, str, str]] = [
            (
                ParticleEventKind.EMITTER_CREATED.value,
                "emitter_fire",
                "Seeded emitter 'Fire'",
            ),
            (
                ParticleEventKind.EMITTER_CREATED.value,
                "emitter_explosion",
                "Seeded emitter 'Explosion'",
            ),
            (
                ParticleEventKind.EFFECT_PLAYED.value,
                "effect_campfire",
                "Seeded effect 'Campfire' (idle)",
            ),
            (
                ParticleEventKind.EFFECT_STOPPED.value,
                "effect_grenade",
                "Seeded effect 'Grenade Explosion' (idle)",
            ),
            (
                ParticleEventKind.PARTICLE_BURST.value,
                "emitter_explosion",
                "Burst preset configured for 'Explosion'",
            ),
            (
                ParticleEventKind.CONFIG_CHANGED.value,
                "",
                "Default configuration applied",
            ),
        ]
        for (etype, target_id, desc) in event_seeds:
            self._event_counter += 1
            self._events.append(
                ParticleVFXEvent(
                    event_id=f"pvfx_evt_{self._event_counter:08d}",
                    timestamp=now,
                    event_type=etype,
                    target_id=target_id,
                    description=desc,
                    metadata={"seed": True},
                )
            )

        # --- Stats ---
        self._refresh_stats()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        target_id: str = "",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event and trim the event log to capacity."""
        self._event_counter += 1
        event = ParticleVFXEvent(
            event_id=f"pvfx_evt_{self._event_counter:08d}",
            timestamp=_now(),
            event_type=event_type,
            target_id=target_id,
            description=description,
            metadata=metadata or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from the current stores."""
        self._stats.total_emitters = len(self._emitters)
        self._stats.total_effects = len(self._effects)
        self._stats.total_batches = len(self._batches)
        self._stats.total_curves = len(self._curves)
        self._stats.total_gradients = len(self._gradients)
        self._stats.active_batches = sum(
            1 for b in self._batches.values()
            if b.status == ParticleStatus.PLAYING.value
        )
        self._stats.active_particles = sum(
            b.active_particles for b in self._batches.values()
        )
        self._stats.tick_count = self._tick_count

    def _resolve_emitter(self, emitter_id: str) -> Optional[ParticleEmitter]:
        return self._emitters.get(emitter_id)

    def _resolve_effect(self, effect_id: str) -> Optional[ParticleEffect]:
        return self._effects.get(effect_id)

    def _resolve_batch(self, batch_id: str) -> Optional[ParticleBatch]:
        return self._batches.get(batch_id)

    def _new_batch_id(self) -> str:
        self._batch_counter += 1
        return f"pbatch_{self._batch_counter:08d}"

    def _compute_batch_max_particles(
        self, emitter_ids: List[str]
    ) -> int:
        """Sum the max_particles across all linked emitters."""
        total = 0
        for eid in emitter_ids:
            emitter = self._emitters.get(eid)
            if emitter is not None:
                total += emitter.max_particles
        if total <= 0:
            total = self._config.max_particles_per_batch
        return min(total, self._config.max_particles_per_batch)

    # ------------------------------------------------------------------
    # Emitter Management
    # ------------------------------------------------------------------

    def register_emitter(
        self,
        emitter_id: str,
        name: str,
        emitter_type: str,
        shape: str = EmitterShape.POINT.value,
        description: str = "",
        rate: float = 10.0,
        burst_count: int = 0,
        burst_interval: float = 0.0,
        lifetime: float = 5.0,
        particle_lifetime: Tuple[float, float] = (1.0, 2.0),
        particle_shape: str = ParticleShape.QUAD.value,
        blend_mode: str = ParticleBlendMode.ALPHA.value,
        simulation_space: str = ParticleSimulationSpace.WORLD.value,
        max_particles: int = 1000,
        start_size: Tuple[float, float] = (0.1, 0.2),
        start_speed: Tuple[float, float] = (1.0, 3.0),
        start_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        gravity: Tuple[float, float, float] = (0.0, -9.8, 0.0),
        drag: float = 0.0,
        sort_mode: str = SortMode.NONE.value,
        enabled: bool = True,
        tags: Optional[List[str]] = None,
        thumbnail_url: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ParticleEmitter]]:
        """Register a new particle emitter.

        Args:
            emitter_id: Unique emitter identifier.
            name: Display name.
            emitter_type: The ParticleEmitterType value name.
            shape: The EmitterShape value name.
            description: Human-readable description.
            rate: Continuous emission rate in particles per second.
            burst_count: Number of particles emitted per burst.
            burst_interval: Seconds between bursts.
            lifetime: Emitter duration in seconds.
            particle_lifetime: ``(min, max)`` lifetime of each particle.
            particle_shape: The ParticleShape value name.
            blend_mode: The ParticleBlendMode value name.
            simulation_space: The ParticleSimulationSpace value name.
            max_particles: Hard cap on active particles.
            start_size: ``(min, max)`` start size.
            start_speed: ``(min, max)`` start speed.
            start_color: ``(r, g, b, a)`` start color.
            gravity: ``(x, y, z)`` gravity.
            drag: Linear drag coefficient.
            sort_mode: The SortMode value name.
            enabled: Whether the emitter is eligible for simulation.
            tags: Searchable tags.
            thumbnail_url: Optional thumbnail asset URL.
            metadata: Free-form extension data.

        Returns:
            A ``(ok, message, emitter)`` tuple. ``ok`` is False when the
            id already exists or the id is empty.
        """
        if not emitter_id:
            return False, "emitter_id is required", None
        with self._lock:
            if emitter_id in self._emitters:
                return False, "emitter_id already exists", None
            if len(self._emitters) >= self._config.max_emitters:
                _evict_fifo_dict(self._emitters, self._config.max_emitters)

            type_enum = _coerce_enum(
                ParticleEmitterType, emitter_type, ParticleEmitterType.POINT
            )
            shape_enum = _coerce_enum(
                EmitterShape, shape, EmitterShape.POINT
            )
            pshape_enum = _coerce_enum(
                ParticleShape, particle_shape, ParticleShape.QUAD
            )
            blend_enum = _coerce_enum(
                ParticleBlendMode, blend_mode, ParticleBlendMode.ALPHA
            )
            space_enum = _coerce_enum(
                ParticleSimulationSpace, simulation_space,
                ParticleSimulationSpace.WORLD,
            )
            sort_enum = _coerce_enum(SortMode, sort_mode, SortMode.NONE)

            now = _now()
            emitter = ParticleEmitter(
                emitter_id=emitter_id,
                name=name or emitter_id,
                description=description,
                emitter_type=type_enum.value,
                shape=shape_enum.value,
                rate=_clamp(_safe_float(rate, 10.0), _RATE_MIN, _RATE_MAX),
                burst_count=_safe_int(
                    _clamp(burst_count, _BURST_COUNT_MIN, _BURST_COUNT_MAX), 0
                ),
                burst_interval=max(0.0, _safe_float(burst_interval, 0.0)),
                lifetime=_clamp(
                    _safe_float(lifetime, 5.0), _LIFETIME_MIN, _LIFETIME_MAX
                ),
                particle_lifetime=(
                    max(0.0, _safe_float(particle_lifetime[0], 1.0)),
                    max(0.0, _safe_float(particle_lifetime[1], 2.0)),
                ),
                particle_shape=pshape_enum.value,
                blend_mode=blend_enum.value,
                simulation_space=space_enum.value,
                max_particles=max(
                    _MAX_PARTICLES_MIN,
                    min(_safe_int(max_particles, 1000), _MAX_PARTICLES_MAX),
                ),
                start_size=(
                    max(0.0, _safe_float(start_size[0], 0.1)),
                    max(0.0, _safe_float(start_size[1], 0.2)),
                ),
                start_speed=(
                    max(0.0, _safe_float(start_speed[0], 1.0)),
                    max(0.0, _safe_float(start_speed[1], 3.0)),
                ),
                start_color=tuple(
                    _clamp(_safe_float(c, 1.0), 0.0, 1.0)
                    for c in start_color
                ),
                gravity=tuple(_safe_float(g, 0.0) for g in gravity),
                drag=_clamp(_safe_float(drag, 0.0), _DRAG_MIN, _DRAG_MAX),
                sort_mode=sort_enum.value,
                enabled=bool(enabled),
                tags=list(tags or []),
                thumbnail_url=thumbnail_url,
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._emitters[emitter_id] = emitter
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                emitter_id,
                f"Registered emitter '{emitter.name}'",
                {"emitter_type": emitter.emitter_type, "shape": emitter.shape},
            )
            return True, "registered", emitter

    def get_emitter(self, emitter_id: str) -> Optional[ParticleEmitter]:
        """Retrieve an emitter by its identifier."""
        with self._lock:
            return self._resolve_emitter(emitter_id)

    def list_emitters(
        self,
        emitter_type: Optional[str] = None,
        shape: Optional[str] = None,
        blend_mode: Optional[str] = None,
        enabled: Optional[bool] = None,
        tag: Optional[str] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[ParticleEmitter]:
        """List emitters with optional filters.

        Args:
            emitter_type: Filter by ParticleEmitterType value name.
            shape: Filter by EmitterShape value name.
            blend_mode: Filter by ParticleBlendMode value name.
            enabled: Filter by enabled state.
            tag: Filter by tag membership.
            limit: Maximum number of emitters to return.

        Returns:
            A list of matching ParticleEmitter objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            type_value = None
            if emitter_type is not None:
                e = _coerce_enum(ParticleEmitterType, emitter_type, None)
                type_value = e.value if e else emitter_type
            shape_value = None
            if shape is not None:
                e = _coerce_enum(EmitterShape, shape, None)
                shape_value = e.value if e else shape
            blend_value = None
            if blend_mode is not None:
                e = _coerce_enum(ParticleBlendMode, blend_mode, None)
                blend_value = e.value if e else blend_mode
            results: List[ParticleEmitter] = []
            for emitter in self._emitters.values():
                if type_value is not None and emitter.emitter_type != type_value:
                    continue
                if shape_value is not None and emitter.shape != shape_value:
                    continue
                if blend_value is not None and emitter.blend_mode != blend_value:
                    continue
                if enabled is not None and emitter.enabled != enabled:
                    continue
                if tag is not None and tag not in emitter.tags:
                    continue
                results.append(emitter)
                if len(results) >= cap:
                    break
            return results

    def remove_emitter(self, emitter_id: str) -> Tuple[bool, str]:
        """Remove an emitter by its identifier.

        Also detaches the emitter from any effects that hold it.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            emitter = self._emitters.get(emitter_id)
            if emitter is None:
                return False, "not found"
            del self._emitters[emitter_id]
            for effect in self._effects.values():
                if emitter_id in effect.emitter_ids:
                    effect.emitter_ids.remove(emitter_id)
                    effect.updated_at = _now()
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EMITTER_REMOVED.value,
                emitter_id,
                f"Removed emitter '{emitter.name}'",
            )
            return True, "removed"

    def update_emitter(
        self, emitter_id: str, **kwargs: Any
    ) -> Tuple[bool, str, Optional[ParticleEmitter]]:
        """Update mutable fields on an existing emitter.

        Accepts any subset of ParticleEmitter fields. Enum-typed fields
        are coerced via their respective enums. Tuple fields
        (``particle_lifetime``, ``start_size``, ``start_speed``,
        ``start_color``, ``gravity``) accept lists or tuples. The
        ``modules`` field, when provided as a dict, is merged into the
        existing modules. The ``updated_at`` timestamp is refreshed.

        Returns:
            A ``(ok, message, emitter)`` tuple.
        """
        with self._lock:
            emitter = self._resolve_emitter(emitter_id)
            if emitter is None:
                return False, "not found", None
            for key in ("name", "description", "thumbnail_url"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(emitter, key, kwargs[key])
            if "enabled" in kwargs and kwargs["enabled"] is not None:
                emitter.enabled = bool(kwargs["enabled"])
            if "rate" in kwargs and kwargs["rate"] is not None:
                emitter.rate = _clamp(
                    _safe_float(kwargs["rate"], emitter.rate),
                    _RATE_MIN, _RATE_MAX,
                )
            if "burst_count" in kwargs and kwargs["burst_count"] is not None:
                emitter.burst_count = _safe_int(
                    _clamp(kwargs["burst_count"], _BURST_COUNT_MIN, _BURST_COUNT_MAX),
                    emitter.burst_count,
                )
            if "burst_interval" in kwargs and kwargs["burst_interval"] is not None:
                emitter.burst_interval = max(0.0, _safe_float(kwargs["burst_interval"], 0.0))
            if "lifetime" in kwargs and kwargs["lifetime"] is not None:
                emitter.lifetime = _clamp(
                    _safe_float(kwargs["lifetime"], emitter.lifetime),
                    _LIFETIME_MIN, _LIFETIME_MAX,
                )
            if "max_particles" in kwargs and kwargs["max_particles"] is not None:
                emitter.max_particles = max(
                    _MAX_PARTICLES_MIN,
                    min(_safe_int(kwargs["max_particles"], emitter.max_particles), _MAX_PARTICLES_MAX),
                )
            if "drag" in kwargs and kwargs["drag"] is not None:
                emitter.drag = _clamp(
                    _safe_float(kwargs["drag"], emitter.drag),
                    _DRAG_MIN, _DRAG_MAX,
                )
            if "tags" in kwargs and kwargs["tags"] is not None:
                emitter.tags = list(kwargs["tags"])
            if "metadata" in kwargs and kwargs["metadata"] is not None:
                if isinstance(kwargs["metadata"], dict):
                    emitter.metadata.update(kwargs["metadata"])
            if "emitter_type" in kwargs and kwargs["emitter_type"] is not None:
                e = _coerce_enum(ParticleEmitterType, kwargs["emitter_type"], None)
                if e is not None:
                    emitter.emitter_type = e.value
            if "shape" in kwargs and kwargs["shape"] is not None:
                e = _coerce_enum(EmitterShape, kwargs["shape"], None)
                if e is not None:
                    emitter.shape = e.value
            if "particle_shape" in kwargs and kwargs["particle_shape"] is not None:
                e = _coerce_enum(ParticleShape, kwargs["particle_shape"], None)
                if e is not None:
                    emitter.particle_shape = e.value
            if "blend_mode" in kwargs and kwargs["blend_mode"] is not None:
                e = _coerce_enum(ParticleBlendMode, kwargs["blend_mode"], None)
                if e is not None:
                    emitter.blend_mode = e.value
            if "simulation_space" in kwargs and kwargs["simulation_space"] is not None:
                e = _coerce_enum(ParticleSimulationSpace, kwargs["simulation_space"], None)
                if e is not None:
                    emitter.simulation_space = e.value
            if "sort_mode" in kwargs and kwargs["sort_mode"] is not None:
                e = _coerce_enum(SortMode, kwargs["sort_mode"], None)
                if e is not None:
                    emitter.sort_mode = e.value
            for tkey in ("particle_lifetime", "start_size", "start_speed"):
                if tkey in kwargs and kwargs[tkey] is not None:
                    val = kwargs[tkey]
                    if isinstance(val, (list, tuple)) and len(val) >= 2:
                        setattr(emitter, tkey, (
                            _safe_float(val[0], 0.0),
                            _safe_float(val[1], 0.0),
                        ))
            if "start_color" in kwargs and kwargs["start_color"] is not None:
                val = kwargs["start_color"]
                if isinstance(val, (list, tuple)) and len(val) >= 4:
                    emitter.start_color = tuple(
                        _clamp(_safe_float(c, 1.0), 0.0, 1.0) for c in val[:4]
                    )
            if "gravity" in kwargs and kwargs["gravity"] is not None:
                val = kwargs["gravity"]
                if isinstance(val, (list, tuple)) and len(val) >= 3:
                    emitter.gravity = tuple(_safe_float(g, 0.0) for g in val[:3])
            if "modules" in kwargs and kwargs["modules"] is not None:
                if isinstance(kwargs["modules"], dict):
                    for mid, mod in kwargs["modules"].items():
                        if isinstance(mod, ParticleModule):
                            emitter.modules[mid] = mod
                        elif isinstance(mod, dict):
                            emitter.modules[mid] = ParticleModule(
                                module_id=str(mod.get("module_id", mid)),
                                name=str(mod.get("name", mid)),
                                module_type=str(mod.get("module_type", "lifetime")),
                                enabled=bool(mod.get("enabled", True)),
                                parameters=dict(mod.get("parameters", {})),
                                curve_id=str(mod.get("curve_id", "")),
                                gradient_id=str(mod.get("gradient_id", "")),
                                sort_order=_safe_float(mod.get("sort_order", 0.0), 0.0),
                                metadata=dict(mod.get("metadata", {})),
                            )
            emitter.updated_at = _now()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                emitter_id,
                f"Updated emitter '{emitter.name}'",
            )
            return True, "updated", emitter

    # ------------------------------------------------------------------
    # Effect Management
    # ------------------------------------------------------------------

    def create_effect(
        self,
        effect_id: str,
        name: str,
        emitter_ids: Optional[List[str]] = None,
        description: str = "",
        category: str = VFXCategory.CUSTOM.value,
        duration: float = 0.0,
        looping: bool = True,
        prewarm: bool = False,
        delay: float = 0.0,
        sort_priority: float = 0.0,
        tags: Optional[List[str]] = None,
        thumbnail_url: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ParticleEffect]]:
        """Create a new particle effect from a list of emitter ids.

        Args:
            effect_id: Unique effect identifier.
            name: Display name.
            emitter_ids: Ordered list of emitter ids in the effect.
            description: Human-readable description.
            category: The VFXCategory value name.
            duration: Effect duration in seconds (0 = looping).
            looping: Whether the effect loops.
            prewarm: Whether to pre-simulate on play.
            delay: Seconds to wait before emitting.
            sort_priority: Ordering hint for playback.
            tags: Searchable tags.
            thumbnail_url: Optional thumbnail asset URL.
            metadata: Free-form extension data.

        Returns:
            A ``(ok, message, effect)`` tuple.
        """
        if not effect_id:
            return False, "effect_id is required", None
        with self._lock:
            if effect_id in self._effects:
                return False, "effect_id already exists", None
            if len(self._effects) >= self._config.max_effects:
                _evict_fifo_dict(self._effects, self._config.max_effects)
            cat_enum = _coerce_enum(VFXCategory, category, VFXCategory.CUSTOM)
            now = _now()
            effect = ParticleEffect(
                effect_id=effect_id,
                name=name or effect_id,
                description=description,
                category=cat_enum.value,
                emitter_ids=list(emitter_ids or []),
                duration=max(0.0, _safe_float(duration, 0.0)),
                looping=bool(looping),
                prewarm=bool(prewarm),
                delay=max(0.0, _safe_float(delay, 0.0)),
                status=ParticleStatus.IDLE.value,
                sort_priority=_clamp(
                    _safe_float(sort_priority, 0.0),
                    _SORT_PRIORITY_MIN, _SORT_PRIORITY_MAX,
                ),
                tags=list(tags or []),
                thumbnail_url=thumbnail_url,
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._effects[effect_id] = effect
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                effect_id,
                f"Created effect '{effect.name}'",
                {"category": effect.category, "emitter_count": len(effect.emitter_ids)},
            )
            return True, "created", effect

    def get_effect(self, effect_id: str) -> Optional[ParticleEffect]:
        """Retrieve an effect by its identifier."""
        with self._lock:
            return self._resolve_effect(effect_id)

    def list_effects(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[ParticleEffect]:
        """List effects with optional filters.

        Args:
            category: Filter by VFXCategory value name.
            status: Filter by ParticleStatus value name.
            tag: Filter by tag membership.
            limit: Maximum number of effects to return.

        Returns:
            A list of matching ParticleEffect objects sorted by
            sort_priority.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            cat_value = None
            if category is not None:
                e = _coerce_enum(VFXCategory, category, None)
                cat_value = e.value if e else category
            status_value = None
            if status is not None:
                e = _coerce_enum(ParticleStatus, status, None)
                status_value = e.value if e else status
            effects = list(self._effects.values())
            effects.sort(key=lambda ef: ef.sort_priority)
            results: List[ParticleEffect] = []
            for effect in effects:
                if cat_value is not None and effect.category != cat_value:
                    continue
                if status_value is not None and effect.status != status_value:
                    continue
                if tag is not None and tag not in effect.tags:
                    continue
                results.append(effect)
                if len(results) >= cap:
                    break
            return results

    def remove_effect(self, effect_id: str) -> Tuple[bool, str]:
        """Remove an effect by its identifier.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False, "not found"
            del self._effects[effect_id]
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EMITTER_REMOVED.value,
                effect_id,
                f"Removed effect '{effect.name}'",
            )
            return True, "removed"

    def update_effect(
        self, effect_id: str, **kwargs: Any
    ) -> Tuple[bool, str, Optional[ParticleEffect]]:
        """Update mutable fields on an existing effect.

        Accepts any subset of ParticleEffect fields. The ``updated_at``
        timestamp is refreshed.

        Returns:
            A ``(ok, message, effect)`` tuple.
        """
        with self._lock:
            effect = self._resolve_effect(effect_id)
            if effect is None:
                return False, "not found", None
            for key in ("name", "description", "thumbnail_url"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(effect, key, kwargs[key])
            for key in ("looping", "prewarm"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(effect, key, bool(kwargs[key]))
            if "duration" in kwargs and kwargs["duration"] is not None:
                effect.duration = max(0.0, _safe_float(kwargs["duration"], 0.0))
            if "delay" in kwargs and kwargs["delay"] is not None:
                effect.delay = max(0.0, _safe_float(kwargs["delay"], 0.0))
            if "sort_priority" in kwargs and kwargs["sort_priority"] is not None:
                effect.sort_priority = _clamp(
                    _safe_float(kwargs["sort_priority"], 0.0),
                    _SORT_PRIORITY_MIN, _SORT_PRIORITY_MAX,
                )
            if "emitter_ids" in kwargs and kwargs["emitter_ids"] is not None:
                effect.emitter_ids = list(kwargs["emitter_ids"])
            if "tags" in kwargs and kwargs["tags"] is not None:
                effect.tags = list(kwargs["tags"])
            if "metadata" in kwargs and kwargs["metadata"] is not None:
                if isinstance(kwargs["metadata"], dict):
                    effect.metadata.update(kwargs["metadata"])
            if "category" in kwargs and kwargs["category"] is not None:
                e = _coerce_enum(VFXCategory, kwargs["category"], None)
                if e is not None:
                    effect.category = e.value
            if "status" in kwargs and kwargs["status"] is not None:
                e = _coerce_enum(ParticleStatus, kwargs["status"], None)
                if e is not None:
                    effect.status = e.value
            effect.updated_at = _now()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                effect_id,
                f"Updated effect '{effect.name}'",
            )
            return True, "updated", effect

    def add_emitter_to_effect(
        self, effect_id: str, emitter_id: str
    ) -> Tuple[bool, str, Optional[ParticleEffect]]:
        """Append an emitter to an effect.

        Returns:
            A ``(ok, message, effect)`` tuple. Fails when the effect or
            emitter is missing, or the emitter is already in the effect.
        """
        with self._lock:
            effect = self._resolve_effect(effect_id)
            if effect is None:
                return False, "effect not found", None
            if emitter_id not in self._emitters:
                return False, "emitter not found", effect
            if emitter_id in effect.emitter_ids:
                return False, "emitter already in effect", effect
            effect.emitter_ids.append(emitter_id)
            effect.updated_at = _now()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                effect_id,
                f"Added emitter '{emitter_id}' to effect '{effect.name}'",
                {"emitter_id": emitter_id},
            )
            return True, "added", effect

    def remove_emitter_from_effect(
        self, effect_id: str, emitter_id: str
    ) -> Tuple[bool, str, Optional[ParticleEffect]]:
        """Remove an emitter from an effect.

        Returns:
            A ``(ok, message, effect)`` tuple.
        """
        with self._lock:
            effect = self._resolve_effect(effect_id)
            if effect is None:
                return False, "effect not found", None
            if emitter_id not in effect.emitter_ids:
                return False, "emitter not in effect", effect
            effect.emitter_ids.remove(emitter_id)
            effect.updated_at = _now()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                effect_id,
                f"Removed emitter '{emitter_id}' from effect '{effect.name}'",
                {"emitter_id": emitter_id},
            )
            return True, "removed", effect

    # ------------------------------------------------------------------
    # Effect Playback
    # ------------------------------------------------------------------

    def play_effect(
        self,
        effect_id: str,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        speed: float = 1.0,
        rotation: Optional[Tuple[float, float, float]] = None,
        scale: Optional[Tuple[float, float, float]] = None,
    ) -> Tuple[bool, str, Optional[ParticleBatch]]:
        """Play a particle effect at a world position.

        Creates a ParticleBatch that simulates all of the effect's
        emitters. The effect status is set to PLAYING.

        Args:
            effect_id: The effect to play.
            x, y, z: World position of the emission origin.
            speed: Playback speed multiplier.
            rotation: Optional ``(x, y, z)`` euler rotation in degrees.
            scale: Optional ``(x, y, z)`` scale of the emission origin.

        Returns:
            A ``(ok, message, batch)`` tuple.
        """
        with self._lock:
            effect = self._resolve_effect(effect_id)
            if effect is None:
                return False, "effect not found", None
            if not effect.emitter_ids:
                return False, "effect has no emitters", None
            batch_id = self._new_batch_id()
            max_p = self._compute_batch_max_particles(effect.emitter_ids)
            now = _now()
            batch = ParticleBatch(
                batch_id=batch_id,
                effect_id=effect_id,
                emitter_ids=list(effect.emitter_ids),
                name=effect.name,
                position=(
                    _safe_float(x, 0.0),
                    _safe_float(y, 0.0),
                    _safe_float(z, 0.0),
                ),
                rotation=tuple(rotation) if rotation else (0.0, 0.0, 0.0),
                scale=tuple(scale) if scale else (1.0, 1.0, 1.0),
                status=ParticleStatus.PLAYING.value,
                age=0.0,
                duration=effect.duration,
                active_particles=0,
                max_particles=max_p,
                emitted_total=0,
                looping=effect.looping,
                speed=_clamp(
                    _safe_float(speed, 1.0), _BATCH_SPEED_MIN, _BATCH_SPEED_MAX
                ),
                created_at=now,
                updated_at=now,
                metadata={"effect_category": effect.category},
            )
            self._batches[batch_id] = batch
            _evict_fifo_dict(self._batches, self._config.max_batches)
            effect.status = ParticleStatus.PLAYING.value
            effect.updated_at = now
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EFFECT_PLAYED.value,
                effect_id,
                f"Played effect '{effect.name}' at ({x:.1f}, {y:.1f}, {z:.1f})",
                {"batch_id": batch_id, "speed": batch.speed},
            )
            return True, "playing", batch

    def stop_effect(self, effect_id: str) -> Tuple[bool, str]:
        """Stop all playing batches for an effect.

        Sets the effect status to STOPPED and marks all its playing
        batches as STOPPED.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            effect = self._resolve_effect(effect_id)
            if effect is None:
                return False, "effect not found"
            stopped_count = 0
            for batch in self._batches.values():
                if batch.effect_id == effect_id and \
                        batch.status in (
                            ParticleStatus.PLAYING.value,
                            ParticleStatus.PAUSED.value,
                        ):
                    batch.status = ParticleStatus.STOPPED.value
                    batch.active_particles = 0
                    batch.updated_at = _now()
                    stopped_count += 1
            effect.status = ParticleStatus.STOPPED.value
            effect.updated_at = _now()
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EFFECT_STOPPED.value,
                effect_id,
                f"Stopped effect '{effect.name}' ({stopped_count} batches)",
                {"stopped_batches": stopped_count},
            )
            return True, "stopped"

    def pause_effect(self, effect_id: str) -> Tuple[bool, str]:
        """Pause all playing batches for an effect.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            effect = self._resolve_effect(effect_id)
            if effect is None:
                return False, "effect not found"
            paused_count = 0
            for batch in self._batches.values():
                if batch.effect_id == effect_id and \
                        batch.status == ParticleStatus.PLAYING.value:
                    batch.status = ParticleStatus.PAUSED.value
                    batch.updated_at = _now()
                    paused_count += 1
            effect.status = ParticleStatus.PAUSED.value
            effect.updated_at = _now()
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EFFECT_STOPPED.value,
                effect_id,
                f"Paused effect '{effect.name}' ({paused_count} batches)",
                {"paused_batches": paused_count},
            )
            return True, "paused"

    def resume_effect(self, effect_id: str) -> Tuple[bool, str]:
        """Resume all paused batches for an effect.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            effect = self._resolve_effect(effect_id)
            if effect is None:
                return False, "effect not found"
            resumed_count = 0
            for batch in self._batches.values():
                if batch.effect_id == effect_id and \
                        batch.status == ParticleStatus.PAUSED.value:
                    batch.status = ParticleStatus.PLAYING.value
                    batch.updated_at = _now()
                    resumed_count += 1
            effect.status = ParticleStatus.PLAYING.value
            effect.updated_at = _now()
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EFFECT_PLAYED.value,
                effect_id,
                f"Resumed effect '{effect.name}' ({resumed_count} batches)",
                {"resumed_batches": resumed_count},
            )
            return True, "resumed"

    # ------------------------------------------------------------------
    # Batch Management
    # ------------------------------------------------------------------

    def get_batch(self, batch_id: str) -> Optional[ParticleBatch]:
        """Retrieve a batch by its identifier."""
        with self._lock:
            return self._resolve_batch(batch_id)

    def list_batches(
        self,
        status: Optional[str] = None,
        effect_id: Optional[str] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[ParticleBatch]:
        """List batches with optional filters.

        Args:
            status: Filter by ParticleStatus value name.
            effect_id: Filter by parent effect id.
            limit: Maximum number of batches to return.

        Returns:
            A list of matching ParticleBatch objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            status_value = None
            if status is not None:
                e = _coerce_enum(ParticleStatus, status, None)
                status_value = e.value if e else status
            results: List[ParticleBatch] = []
            for batch in self._batches.values():
                if status_value is not None and batch.status != status_value:
                    continue
                if effect_id is not None and batch.effect_id != effect_id:
                    continue
                results.append(batch)
                if len(results) >= cap:
                    break
            return results

    def remove_batch(self, batch_id: str) -> Tuple[bool, str]:
        """Remove a batch by its identifier.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch is None:
                return False, "not found"
            del self._batches[batch_id]
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EFFECT_STOPPED.value,
                batch_id,
                f"Removed batch '{batch.name or batch_id}'",
                {"batch_id": batch_id},
            )
            return True, "removed"

    def burst(
        self,
        emitter_id: str,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        count: int = 0,
        speed: float = 1.0,
    ) -> Tuple[bool, str, Optional[ParticleBatch]]:
        """Emit a one-shot burst of particles from an emitter.

        Creates a ParticleBatch that simulates a single burst of the
        given emitter. When ``count`` is zero the emitter's
        ``burst_count`` is used.

        Args:
            emitter_id: The emitter to burst from.
            x, y, z: World position of the burst origin.
            count: Number of particles to emit (0 = use emitter default).
            speed: Playback speed multiplier.

        Returns:
            A ``(ok, message, batch)`` tuple.
        """
        with self._lock:
            emitter = self._resolve_emitter(emitter_id)
            if emitter is None:
                return False, "emitter not found", None
            burst_count = _safe_int(count, emitter.burst_count)
            if burst_count <= 0:
                burst_count = emitter.burst_count
            burst_count = max(1, min(burst_count, _BURST_COUNT_MAX))
            batch_id = self._new_batch_id()
            avg_life = (
                emitter.particle_lifetime[0] + emitter.particle_lifetime[1]
            ) / 2.0
            now = _now()
            batch = ParticleBatch(
                batch_id=batch_id,
                effect_id="",
                emitter_ids=[emitter_id],
                name=f"{emitter.name} Burst",
                position=(
                    _safe_float(x, 0.0),
                    _safe_float(y, 0.0),
                    _safe_float(z, 0.0),
                ),
                rotation=(0.0, 0.0, 0.0),
                scale=(1.0, 1.0, 1.0),
                status=ParticleStatus.PLAYING.value,
                age=0.0,
                duration=avg_life,
                active_particles=burst_count,
                max_particles=emitter.max_particles,
                emitted_total=burst_count,
                looping=False,
                speed=_clamp(
                    _safe_float(speed, 1.0), _BATCH_SPEED_MIN, _BATCH_SPEED_MAX
                ),
                created_at=now,
                updated_at=now,
                metadata={"burst": True, "burst_count": burst_count},
            )
            self._batches[batch_id] = batch
            _evict_fifo_dict(self._batches, self._config.max_batches)
            self._stats.total_bursts += 1
            self._stats.total_emitted += burst_count
            self._refresh_stats()
            self._emit(
                ParticleEventKind.PARTICLE_BURST.value,
                emitter_id,
                f"Burst {burst_count} particles from '{emitter.name}'",
                {"batch_id": batch_id, "count": burst_count},
            )
            return True, "burst", batch

    # ------------------------------------------------------------------
    # Curve Management
    # ------------------------------------------------------------------

    def create_curve(
        self,
        curve_id: str,
        keyframes: Optional[List[Any]] = None,
        name: str = "",
        loop: bool = False,
        pre_value: float = 0.0,
        post_value: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ParticleCurve]]:
        """Create a new animation curve.

        Args:
            curve_id: Unique curve identifier.
            keyframes: List of ParticleKeyframe objects, dicts, or
                ``(time, value)`` tuples.
            name: Display name.
            loop: Whether the curve loops its input time.
            pre_value: Value returned before the first keyframe.
            post_value: Value returned after the last keyframe.
            metadata: Free-form extension data.

        Returns:
            A ``(ok, message, curve)`` tuple.
        """
        if not curve_id:
            return False, "curve_id is required", None
        with self._lock:
            if curve_id in self._curves:
                return False, "curve_id already exists", None
            if len(self._curves) >= self._config.max_curves:
                _evict_fifo_dict(self._curves, self._config.max_curves)
            now = _now()
            curve = ParticleCurve(
                curve_id=curve_id,
                name=name or curve_id,
                keyframes=_normalize_keyframes(keyframes),
                loop=bool(loop),
                pre_value=_safe_float(pre_value, 0.0),
                post_value=_safe_float(post_value, 1.0),
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._curves[curve_id] = curve
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                curve_id,
                f"Created curve '{curve.name}'",
                {"keyframe_count": len(curve.keyframes)},
            )
            return True, "created", curve

    def get_curve(self, curve_id: str) -> Optional[ParticleCurve]:
        """Retrieve a curve by its identifier."""
        with self._lock:
            return self._curves.get(curve_id)

    def list_curves(
        self, limit: int = _DEFAULT_LIST_LIMIT
    ) -> List[ParticleCurve]:
        """List curves.

        Args:
            limit: Maximum number of curves to return.

        Returns:
            A list of ParticleCurve objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            return list(self._curves.values())[:cap]

    def remove_curve(self, curve_id: str) -> Tuple[bool, str]:
        """Remove a curve by its identifier.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            curve = self._curves.get(curve_id)
            if curve is None:
                return False, "not found"
            del self._curves[curve_id]
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EMITTER_REMOVED.value,
                curve_id,
                f"Removed curve '{curve.name}'",
            )
            return True, "removed"

    def sample_curve(
        self, curve_id: str, t: float
    ) -> Tuple[bool, str, float]:
        """Sample a curve at a normalized time.

        Linearly interpolates between the two keyframes surrounding
        ``t``. When the curve loops the input time wraps around
        ``[0.0, 1.0]``. Returns ``pre_value`` before the first keyframe
        and ``post_value`` after the last keyframe (unless looping).

        Args:
            curve_id: The curve to sample.
            t: Normalized time in ``[0.0, 1.0]``.

        Returns:
            A ``(ok, message, value)`` tuple.
        """
        with self._lock:
            curve = self._curves.get(curve_id)
            if curve is None:
                return False, "curve not found", 0.0
            if not curve.keyframes:
                return True, "empty", 0.0
            t_value = _safe_float(t, 0.0)
            if curve.loop:
                t_value = t_value % 1.0
            else:
                t_value = _clamp(t_value, 0.0, 1.0)
            sorted_kfs = sorted(curve.keyframes, key=lambda k: k.time)
            if t_value <= sorted_kfs[0].time:
                if curve.loop and sorted_kfs[0].time > 0.0:
                    pass
                else:
                    return True, "sampled", sorted_kfs[0].value
            if t_value >= sorted_kfs[-1].time:
                return True, "sampled", sorted_kfs[-1].value
            for i in range(len(sorted_kfs) - 1):
                k0 = sorted_kfs[i]
                k1 = sorted_kfs[i + 1]
                if k0.time <= t_value <= k1.time:
                    if k1.time == k0.time:
                        return True, "sampled", k1.value
                    alpha = (t_value - k0.time) / (k1.time - k0.time)
                    value = k0.value + (k1.value - k0.value) * alpha
                    return True, "sampled", value
            return True, "sampled", sorted_kfs[-1].value

    # ------------------------------------------------------------------
    # Gradient Management
    # ------------------------------------------------------------------

    def create_gradient(
        self,
        gradient_id: str,
        stops: Optional[List[Any]] = None,
        name: str = "",
        loop: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[VFXGradient]]:
        """Create a new color gradient.

        Args:
            gradient_id: Unique gradient identifier.
            stops: List of ``(time, r, g, b, a)`` tuples or dicts.
            name: Display name.
            loop: Whether the gradient loops its input time.
            metadata: Free-form extension data.

        Returns:
            A ``(ok, message, gradient)`` tuple.
        """
        if not gradient_id:
            return False, "gradient_id is required", None
        with self._lock:
            if gradient_id in self._gradients:
                return False, "gradient_id already exists", None
            if len(self._gradients) >= self._config.max_gradients:
                _evict_fifo_dict(self._gradients, self._config.max_gradients)
            now = _now()
            gradient = VFXGradient(
                gradient_id=gradient_id,
                name=name or gradient_id,
                stops=_normalize_stops(stops),
                loop=bool(loop),
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._gradients[gradient_id] = gradient
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                gradient_id,
                f"Created gradient '{gradient.name}'",
                {"stop_count": len(gradient.stops)},
            )
            return True, "created", gradient

    def get_gradient(self, gradient_id: str) -> Optional[VFXGradient]:
        """Retrieve a gradient by its identifier."""
        with self._lock:
            return self._gradients.get(gradient_id)

    def list_gradients(
        self, limit: int = _DEFAULT_LIST_LIMIT
    ) -> List[VFXGradient]:
        """List gradients.

        Args:
            limit: Maximum number of gradients to return.

        Returns:
            A list of VFXGradient objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            return list(self._gradients.values())[:cap]

    def remove_gradient(self, gradient_id: str) -> Tuple[bool, str]:
        """Remove a gradient by its identifier.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            gradient = self._gradients.get(gradient_id)
            if gradient is None:
                return False, "not found"
            del self._gradients[gradient_id]
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EMITTER_REMOVED.value,
                gradient_id,
                f"Removed gradient '{gradient.name}'",
            )
            return True, "removed"

    def sample_gradient(
        self, gradient_id: str, t: float
    ) -> Tuple[bool, str, Tuple[float, float, float, float]]:
        """Sample a gradient at a normalized time.

        Linearly interpolates between the two stops surrounding ``t``.
        When the gradient loops the input time wraps around
        ``[0.0, 1.0]``. Returns the first or last stop color when
        sampling outside the stop range (unless looping).

        Args:
            gradient_id: The gradient to sample.
            t: Normalized time in ``[0.0, 1.0]``.

        Returns:
            A ``(ok, message, color)`` tuple where ``color`` is
            ``(r, g, b, a)`` with all channels in ``[0.0, 1.0]``.
        """
        with self._lock:
            gradient = self._gradients.get(gradient_id)
            if gradient is None:
                return False, "gradient not found", (0.0, 0.0, 0.0, 0.0)
            if not gradient.stops:
                return True, "empty", (1.0, 1.0, 1.0, 1.0)
            t_value = _safe_float(t, 0.0)
            if gradient.loop:
                t_value = t_value % 1.0
            else:
                t_value = _clamp(t_value, 0.0, 1.0)
            sorted_stops = sorted(gradient.stops, key=lambda s: s[0])
            if t_value <= sorted_stops[0][0]:
                s0 = sorted_stops[0]
                return True, "sampled", (s0[1], s0[2], s0[3], s0[4])
            if t_value >= sorted_stops[-1][0]:
                s0 = sorted_stops[-1]
                return True, "sampled", (s0[1], s0[2], s0[3], s0[4])
            for i in range(len(sorted_stops) - 1):
                s0 = sorted_stops[i]
                s1 = sorted_stops[i + 1]
                if s0[0] <= t_value <= s1[0]:
                    if s1[0] == s0[0]:
                        return True, "sampled", (s1[1], s1[2], s1[3], s1[4])
                    alpha = (t_value - s0[0]) / (s1[0] - s0[0])
                    r = s0[1] + (s1[1] - s0[1]) * alpha
                    g = s0[2] + (s1[2] - s0[2]) * alpha
                    b = s0[3] + (s1[3] - s0[3]) * alpha
                    a = s0[4] + (s1[4] - s0[4]) * alpha
                    return True, "sampled", (r, g, b, a)
            s0 = sorted_stops[-1]
            return True, "sampled", (s0[1], s0[2], s0[3], s0[4])

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def auto_generate_effect(
        self,
        description: str,
        name: str = "",
        category: str = VFXCategory.CUSTOM.value,
    ) -> Tuple[bool, str, Optional[ParticleEffect]]:
        """AI-generate a particle effect from a natural-language description.

        The generator inspects the description for keywords (fire, smoke,
        explosion, spark, magic, blood, dust, water) and assembles an
        effect with emitters appropriate to the detected themes. When no
        theme is recognized a generic point emitter effect is produced.

        Args:
            description: A natural-language description of the desired
                effect (e.g. "roaring campfire", "grenade explosion",
                "magic spell impact").
            name: Optional display name. When empty a name is derived
                from the description.
            category: The VFXCategory value name for the new effect.

        Returns:
            A ``(ok, message, effect)`` tuple.
        """
        with self._lock:
            if not description or not description.strip():
                return False, "description must not be empty", None
            desc_lower = description.lower()
            effect_id = _new_id("ai_effect")
            derived_name = name or f"AI Effect {effect_id[:8]}"
            now = _now()
            theme_parts: List[str] = []
            emitter_ids: List[str] = []

            # Fire / flame / burning
            if any(kw in desc_lower for kw in ("fire", "flame", "burn", "ember", "blaze")):
                theme_parts.append("fire")
                eid = f"{effect_id}_fire"
                ok, _, emitter = self.register_emitter(
                    emitter_id=eid,
                    name=f"{derived_name} Fire",
                    emitter_type=ParticleEmitterType.POINT.value,
                    shape=EmitterShape.CONE.value,
                    description=f"AI-generated fire: {description[:100]}",
                    rate=60.0,
                    particle_lifetime=(0.5, 1.0),
                    particle_shape=ParticleShape.QUAD.value,
                    blend_mode=ParticleBlendMode.ADDITIVE.value,
                    max_particles=500,
                    start_size=(0.2, 0.4),
                    start_speed=(1.0, 3.0),
                    start_color=(1.0, 0.6, 0.1, 1.0),
                    gravity=(0.0, 2.0, 0.0),
                    drag=0.5,
                    sort_mode=SortMode.BY_AGE.value,
                    tags=["ai_generated", "fire"],
                    metadata={"ai_generated": True, "ai_theme": "fire"},
                )
                if ok and emitter:
                    emitter_ids.append(eid)

            # Smoke / fog / mist
            if any(kw in desc_lower for kw in ("smoke", "fog", "mist", "vapor")):
                theme_parts.append("smoke")
                eid = f"{effect_id}_smoke"
                ok, _, emitter = self.register_emitter(
                    emitter_id=eid,
                    name=f"{derived_name} Smoke",
                    emitter_type=ParticleEmitterType.POINT.value,
                    shape=EmitterShape.CONE.value,
                    description=f"AI-generated smoke: {description[:100]}",
                    rate=25.0,
                    particle_lifetime=(2.0, 4.0),
                    particle_shape=ParticleShape.QUAD.value,
                    blend_mode=ParticleBlendMode.ALPHA.value,
                    max_particles=300,
                    start_size=(0.5, 1.0),
                    start_speed=(0.5, 1.5),
                    start_color=(0.3, 0.3, 0.3, 0.6),
                    gravity=(0.0, 1.0, 0.0),
                    drag=0.8,
                    sort_mode=SortMode.BY_AGE.value,
                    tags=["ai_generated", "smoke"],
                    metadata={"ai_generated": True, "ai_theme": "smoke"},
                )
                if ok and emitter:
                    emitter_ids.append(eid)

            # Explosion / blast / detonation
            if any(kw in desc_lower for kw in ("explosion", "blast", "detonat", "boom")):
                theme_parts.append("explosion")
                eid = f"{effect_id}_explosion"
                ok, _, emitter = self.register_emitter(
                    emitter_id=eid,
                    name=f"{derived_name} Explosion",
                    emitter_type=ParticleEmitterType.SPHERE.value,
                    shape=EmitterShape.SPHERE.value,
                    description=f"AI-generated explosion: {description[:100]}",
                    rate=0.0,
                    burst_count=200,
                    particle_lifetime=(0.5, 1.5),
                    particle_shape=ParticleShape.QUAD.value,
                    blend_mode=ParticleBlendMode.ADDITIVE.value,
                    max_particles=500,
                    start_size=(0.3, 0.6),
                    start_speed=(5.0, 15.0),
                    start_color=(1.0, 0.8, 0.2, 1.0),
                    gravity=(0.0, -3.0, 0.0),
                    drag=0.3,
                    sort_mode=SortMode.NONE.value,
                    tags=["ai_generated", "explosion"],
                    metadata={"ai_generated": True, "ai_theme": "explosion"},
                )
                if ok and emitter:
                    emitter_ids.append(eid)

            # Spark / electric / lightning
            if any(kw in desc_lower for kw in ("spark", "electric", "lightning", "static")):
                theme_parts.append("spark")
                eid = f"{effect_id}_spark"
                ok, _, emitter = self.register_emitter(
                    emitter_id=eid,
                    name=f"{derived_name} Spark",
                    emitter_type=ParticleEmitterType.POINT.value,
                    shape=EmitterShape.CONE.value,
                    description=f"AI-generated sparks: {description[:100]}",
                    rate=120.0,
                    particle_lifetime=(0.2, 0.5),
                    particle_shape=ParticleShape.POINT.value,
                    blend_mode=ParticleBlendMode.ADDITIVE.value,
                    max_particles=800,
                    start_size=(0.02, 0.05),
                    start_speed=(3.0, 8.0),
                    start_color=(1.0, 0.9, 0.5, 1.0),
                    gravity=(0.0, -9.8, 0.0),
                    drag=0.1,
                    tags=["ai_generated", "spark"],
                    metadata={"ai_generated": True, "ai_theme": "spark"},
                )
                if ok and emitter:
                    emitter_ids.append(eid)

            # Magic / arcane / spell / aura
            if any(kw in desc_lower for kw in ("magic", "arcane", "spell", "aura", "enchant")):
                theme_parts.append("magic")
                eid = f"{effect_id}_magic"
                ok, _, emitter = self.register_emitter(
                    emitter_id=eid,
                    name=f"{derived_name} Magic",
                    emitter_type=ParticleEmitterType.SPHERE.value,
                    shape=EmitterShape.SPHERE.value,
                    description=f"AI-generated magic aura: {description[:100]}",
                    rate=40.0,
                    particle_lifetime=(1.0, 2.0),
                    particle_shape=ParticleShape.SPRITE.value,
                    blend_mode=ParticleBlendMode.ADDITIVE.value,
                    max_particles=400,
                    start_size=(0.3, 0.5),
                    start_speed=(0.5, 2.0),
                    start_color=(0.5, 0.2, 1.0, 1.0),
                    gravity=(0.0, 0.5, 0.0),
                    drag=0.6,
                    sort_mode=SortMode.BY_DISTANCE.value,
                    tags=["ai_generated", "magic"],
                    metadata={"ai_generated": True, "ai_theme": "magic"},
                )
                if ok and emitter:
                    emitter_ids.append(eid)

            # Blood / gore / wound
            if any(kw in desc_lower for kw in ("blood", "gore", "wound", "bleed")):
                theme_parts.append("blood")
                eid = f"{effect_id}_blood"
                ok, _, emitter = self.register_emitter(
                    emitter_id=eid,
                    name=f"{derived_name} Blood",
                    emitter_type=ParticleEmitterType.POINT.value,
                    shape=EmitterShape.CONE.value,
                    description=f"AI-generated blood spray: {description[:100]}",
                    rate=100.0,
                    particle_lifetime=(0.3, 0.8),
                    particle_shape=ParticleShape.QUAD.value,
                    blend_mode=ParticleBlendMode.ALPHA.value,
                    max_particles=600,
                    start_size=(0.05, 0.15),
                    start_speed=(4.0, 10.0),
                    start_color=(0.8, 0.0, 0.0, 1.0),
                    gravity=(0.0, -9.8, 0.0),
                    drag=0.3,
                    tags=["ai_generated", "blood"],
                    metadata={"ai_generated": True, "ai_theme": "blood"},
                )
                if ok and emitter:
                    emitter_ids.append(eid)

            # Dust / dirt / sand / debris
            if any(kw in desc_lower for kw in ("dust", "dirt", "sand", "debris")):
                theme_parts.append("dust")
                eid = f"{effect_id}_dust"
                ok, _, emitter = self.register_emitter(
                    emitter_id=eid,
                    name=f"{derived_name} Dust",
                    emitter_type=ParticleEmitterType.BOX.value,
                    shape=EmitterShape.BOX.value,
                    description=f"AI-generated dust: {description[:100]}",
                    rate=20.0,
                    particle_lifetime=(1.0, 3.0),
                    particle_shape=ParticleShape.QUAD.value,
                    blend_mode=ParticleBlendMode.ALPHA.value,
                    max_particles=300,
                    start_size=(0.2, 0.5),
                    start_speed=(0.5, 2.0),
                    start_color=(0.7, 0.6, 0.4, 0.4),
                    gravity=(0.0, -1.0, 0.0),
                    drag=1.5,
                    sort_mode=SortMode.BY_AGE.value,
                    tags=["ai_generated", "dust"],
                    metadata={"ai_generated": True, "ai_theme": "dust"},
                )
                if ok and emitter:
                    emitter_ids.append(eid)

            # Water / rain / splash
            if any(kw in desc_lower for kw in ("water", "rain", "splash", "fluid")):
                theme_parts.append("water")
                eid = f"{effect_id}_water"
                ok, _, emitter = self.register_emitter(
                    emitter_id=eid,
                    name=f"{derived_name} Water",
                    emitter_type=ParticleEmitterType.SPHERE.value,
                    shape=EmitterShape.SPHERE.value,
                    description=f"AI-generated water splash: {description[:100]}",
                    rate=80.0,
                    particle_lifetime=(0.4, 1.0),
                    particle_shape=ParticleShape.QUAD.value,
                    blend_mode=ParticleBlendMode.ALPHA.value,
                    max_particles=500,
                    start_size=(0.05, 0.15),
                    start_speed=(3.0, 8.0),
                    start_color=(0.3, 0.6, 1.0, 0.8),
                    gravity=(0.0, -9.8, 0.0),
                    drag=0.2,
                    tags=["ai_generated", "water"],
                    metadata={"ai_generated": True, "ai_theme": "water"},
                )
                if ok and emitter:
                    emitter_ids.append(eid)

            if not theme_parts:
                # Neutral fallback: a simple point emitter with mild defaults.
                theme_parts.append("generic")
                eid = f"{effect_id}_generic"
                ok, _, emitter = self.register_emitter(
                    emitter_id=eid,
                    name=f"{derived_name} Particles",
                    emitter_type=ParticleEmitterType.POINT.value,
                    shape=EmitterShape.POINT.value,
                    description=f"AI-generated generic particles: {description[:100]}",
                    rate=30.0,
                    particle_lifetime=(0.5, 1.5),
                    particle_shape=ParticleShape.QUAD.value,
                    blend_mode=ParticleBlendMode.ALPHA.value,
                    max_particles=500,
                    start_size=(0.1, 0.2),
                    start_speed=(1.0, 3.0),
                    start_color=(1.0, 1.0, 1.0, 1.0),
                    gravity=(0.0, -5.0, 0.0),
                    drag=0.2,
                    tags=["ai_generated", "generic"],
                    metadata={"ai_generated": True, "ai_theme": "generic"},
                )
                if ok and emitter:
                    emitter_ids.append(eid)

            theme = "-".join(theme_parts)
            # Determine duration and looping from the description.
            looping = True
            duration = 0.0
            if any(kw in desc_lower for kw in ("explosion", "blast", "impact", "burst", "detonat")):
                looping = False
                duration = 3.0
            elif any(kw in desc_lower for kw in ("splash", "impact", "hit")):
                looping = False
                duration = 1.5
            cat_enum = _coerce_enum(VFXCategory, category, VFXCategory.CUSTOM)
            # Override category from themes when not explicitly set.
            if category == VFXCategory.CUSTOM.value:
                if any(t in theme_parts for t in ("fire", "smoke", "dust")):
                    cat_enum = VFXCategory.ENVIRONMENT
                elif any(t in theme_parts for t in ("explosion", "blood")):
                    cat_enum = VFXCategory.COMBAT
                elif "magic" in theme_parts:
                    cat_enum = VFXCategory.MAGIC
                elif "water" in theme_parts:
                    cat_enum = VFXCategory.WEATHER
            effect = ParticleEffect(
                effect_id=effect_id,
                name=derived_name,
                description=f"AI-generated {theme} effect: {description[:140]}",
                category=cat_enum.value,
                emitter_ids=emitter_ids,
                duration=duration,
                looping=looping,
                prewarm=False,
                delay=0.0,
                status=ParticleStatus.IDLE.value,
                sort_priority=0.0,
                tags=["ai_generated"] + theme_parts,
                thumbnail_url="",
                created_at=now,
                updated_at=now,
                metadata={
                    "ai_generated": True,
                    "ai_theme": theme,
                    "ai_description": description[:200],
                },
            )
            self._effects[effect_id] = effect
            _evict_fifo_dict(self._effects, self._config.max_effects)
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                effect_id,
                f"AI generated {theme} effect '{derived_name}'",
                {"theme": theme, "emitter_count": len(emitter_ids)},
            )
            return True, "generated", effect

    def suggest_parameters(
        self, emitter_id: str
    ) -> Tuple[bool, str, List[str]]:
        """AI-suggest which parameters a designer should adjust next.

        Inspects the current configuration of an emitter and proposes the
        next parameters to tune. The heuristic considers the emitter
        type, blend mode, emission mode (rate vs burst), gravity
        direction, particle count, and module coverage.

        Args:
            emitter_id: The emitter to inspect.

        Returns:
            A ``(ok, message, parameters)`` tuple where ``parameters``
            is a list of parameter names ordered by suggestion priority.
        """
        with self._lock:
            emitter = self._resolve_emitter(emitter_id)
            if emitter is None:
                return False, "emitter not found", []
            reasons: Dict[str, int] = {}
            # 1. Burst-only emitters: suggest burst_count and burst_interval.
            if emitter.rate <= 0.0 and emitter.burst_count > 0:
                reasons["burst_count"] = reasons.get("burst_count", 0) + 3
                reasons["burst_interval"] = reasons.get("burst_interval", 0) + 2
            else:
                # 2. Rate-based emitters: suggest rate and particle_lifetime.
                reasons["rate"] = reasons.get("rate", 0) + 3
                reasons["particle_lifetime"] = reasons.get("particle_lifetime", 0) + 2
            # 3. Suggest start_speed for sphere and cone emitters.
            if emitter.emitter_type in (
                ParticleEmitterType.SPHERE.value,
                ParticleEmitterType.CONE.value,
            ):
                reasons["start_speed"] = reasons.get("start_speed", 0) + 2
            # 4. Suggest start_color for additive blending.
            if emitter.blend_mode == ParticleBlendMode.ADDITIVE.value:
                reasons["start_color"] = reasons.get("start_color", 0) + 2
            # 5. Suggest gravity tuning.
            if emitter.gravity[1] != 0.0:
                reasons["gravity"] = reasons.get("gravity", 0) + 2
            # 6. Suggest drag when gravity is strong.
            if abs(emitter.gravity[1]) > 5.0:
                reasons["drag"] = reasons.get("drag", 0) + 1
            # 7. Suggest max_particles when the cap is high.
            if emitter.max_particles > 500:
                reasons["max_particles"] = reasons.get("max_particles", 0) + 1
            # 8. Suggest start_size for quad and sprite shapes.
            if emitter.particle_shape in (
                ParticleShape.QUAD.value,
                ParticleShape.SPRITE.value,
            ):
                reasons["start_size"] = reasons.get("start_size", 0) + 1
            # 9. Suggest adding modules when none are present.
            if not emitter.modules:
                reasons["modules"] = reasons.get("modules", 0) + 3
            # 10. Suggest sort_mode when sorting is enabled.
            if self._config.enable_sorting and \
                    emitter.sort_mode == SortMode.NONE.value:
                reasons["sort_mode"] = reasons.get("sort_mode", 0) + 1
            ordered = sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))
            suggestions = [pname for pname, _ in ordered]
            if not suggestions:
                suggestions = ["rate"]
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                emitter_id,
                f"Suggested {len(suggestions)} parameters for '{emitter.name}'",
                {"suggestions": suggestions[:8]},
            )
            return True, "suggested", suggestions

    def optimize_effect(
        self, effect_id: str, target_fps: int = 60
    ) -> Tuple[bool, str, Optional[ParticleEffect]]:
        """AI-optimize an effect for performance at a target frame rate.

        Reduces max_particles and rate on all linked emitters and
        disables expensive modules (noise, collision, sub_emitter, trail)
        so the effect is likely to hit the target frame rate. Higher
        target frame rates trigger more aggressive reductions.

        Args:
            effect_id: The effect to optimize.
            target_fps: The frame rate the effect should be optimized for.

        Returns:
            A ``(ok, message, effect)`` tuple.
        """
        with self._lock:
            effect = self._resolve_effect(effect_id)
            if effect is None:
                return False, "effect not found", None
            fps = max(1, _safe_int(target_fps, 60))
            if fps >= 120:
                factor = 0.3
            elif fps >= 90:
                factor = 0.5
            elif fps >= 60:
                factor = 0.7
            else:
                factor = 0.9
            expensive_module_types = (
                "noise", "collision", "sub_emitter", "trail",
            )
            changes: List[str] = []
            for eid in effect.emitter_ids:
                emitter = self._emitters.get(eid)
                if emitter is None:
                    continue
                old_max = emitter.max_particles
                emitter.max_particles = max(
                    _MAX_PARTICLES_MIN, int(old_max * factor)
                )
                changes.append(
                    f"{eid}.max_particles: {old_max}->{emitter.max_particles}"
                )
                old_rate = emitter.rate
                if old_rate > 0.0:
                    emitter.rate = round(old_rate * factor, 2)
                    changes.append(
                        f"{eid}.rate: {old_rate}->{emitter.rate}"
                    )
                old_burst = emitter.burst_count
                if old_burst > 0:
                    emitter.burst_count = max(1, int(old_burst * factor))
                    changes.append(
                        f"{eid}.burst_count: {old_burst}->{emitter.burst_count}"
                    )
                for module in emitter.modules.values():
                    if module.module_type in expensive_module_types:
                        if module.enabled:
                            module.enabled = False
                            changes.append(
                                f"{eid}.{module.module_type}: disabled"
                            )
                emitter.updated_at = _now()
            effect.metadata["ai_optimized"] = True
            effect.metadata["ai_target_fps"] = fps
            effect.metadata["ai_changes"] = changes
            effect.updated_at = _now()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                effect_id,
                f"AI optimized '{effect.name}' for {fps} fps",
                {"target_fps": fps, "changes": changes},
            )
            return True, "optimized", effect

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_effect(
        self, effect_id: str, fmt: str = "json"
    ) -> Optional[Dict[str, Any]]:
        """Export an effect and all of its emitters to a serializable dict.

        The exported payload carries the effect definition, every linked
        emitter (including its behavior modules), and any curves and
        gradients linked by those emitters so the effect can be fully
        reconstructed by ``import_effect``.

        Args:
            effect_id: The effect to export.
            fmt: Serialization format. Only "json" is supported.

        Returns:
            A dict representation of the effect bundle, or None when the
            effect is missing or the format is unsupported.
        """
        with self._lock:
            effect = self._resolve_effect(effect_id)
            if effect is None:
                return None
            if fmt.lower() != "json":
                return None
            emitters_payload: List[Dict[str, Any]] = []
            linked_curve_ids: set = set()
            linked_gradient_ids: set = set()
            for eid in effect.emitter_ids:
                emitter = self._emitters.get(eid)
                if emitter is None:
                    continue
                emitter_data = emitter.to_dict()
                # Serialize modules into a list so import can rebuild them.
                emitter_data["modules"] = [
                    m.to_dict() for m in emitter.modules.values()
                ]
                emitters_payload.append(emitter_data)
                for module in emitter.modules.values():
                    if module.curve_id:
                        linked_curve_ids.add(module.curve_id)
                    if module.gradient_id:
                        linked_gradient_ids.add(module.gradient_id)
            curves_payload: List[Dict[str, Any]] = []
            for cid in sorted(linked_curve_ids):
                curve = self._curves.get(cid)
                if curve is not None:
                    curves_payload.append(curve.to_dict())
            gradients_payload: List[Dict[str, Any]] = []
            for gid in sorted(linked_gradient_ids):
                gradient = self._gradients.get(gid)
                if gradient is not None:
                    gradients_payload.append(gradient.to_dict())
            payload = {
                "effect": effect.to_dict(),
                "emitters": emitters_payload,
                "curves": curves_payload,
                "gradients": gradients_payload,
                "_export_format": "json",
                "_export_version": "1.0.0",
                "_exported_at": _now(),
            }
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                effect_id,
                f"Exported effect '{effect.name}' as {fmt}",
                {
                    "format": fmt,
                    "emitter_count": len(emitters_payload),
                    "curve_count": len(curves_payload),
                    "gradient_count": len(gradients_payload),
                },
            )
            return payload

    def import_effect(
        self, data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[ParticleEffect]]:
        """Import an effect bundle from a serialized dict.

        The dict must contain an ``effect`` mapping with at least
        ``effect_id`` and ``name``. Optional ``emitters``, ``curves``, and
        ``gradients`` lists are reconstructed and registered. New ids are
        generated when an incoming id already exists to avoid clobbering.

        Args:
            data: The serialized effect bundle.

        Returns:
            A ``(ok, message, effect)`` tuple.
        """
        if not isinstance(data, dict):
            return False, "data must be a dict", None
        with self._lock:
            effect_data = data.get("effect")
            if not isinstance(effect_data, dict):
                return False, "missing 'effect' mapping", None
            effect_id = str(effect_data.get("effect_id", "")).strip()
            if not effect_id:
                effect_id = _new_id("effect")
            # Avoid clobbering an existing effect.
            if effect_id in self._effects:
                effect_id = f"{effect_id}_{_new_id()}"
            # Reconstruct and register emitters first so the effect can
            # refer to them by id.
            id_remap: Dict[str, str] = {}
            for emitter_data in data.get("emitters", []) or []:
                if not isinstance(emitter_data, dict):
                    continue
                original_id = str(emitter_data.get("emitter_id", "")).strip()
                new_emitter_id = original_id or _new_id("emitter")
                if new_emitter_id in self._emitters:
                    new_emitter_id = f"{new_emitter_id}_{_new_id()}"
                if original_id:
                    id_remap[original_id] = new_emitter_id
                now = _now()
                modules_data = emitter_data.get("modules", []) or []
                modules: Dict[str, ParticleModule] = {}
                for mod_data in modules_data:
                    if not isinstance(mod_data, dict):
                        continue
                    mod_id = str(mod_data.get("module_id", "")) or _new_id("mod")
                    if mod_id in modules:
                        mod_id = f"{mod_id}_{_new_id()}"
                    module = ParticleModule(
                        module_id=mod_id,
                        name=str(mod_data.get("name", mod_id)),
                        module_type=str(
                            mod_data.get("module_type", "lifetime")
                        ),
                        enabled=bool(mod_data.get("enabled", True)),
                        parameters=dict(mod_data.get("parameters", {})),
                        curve_id=str(mod_data.get("curve_id", "")),
                        gradient_id=str(mod_data.get("gradient_id", "")),
                        sort_order=_safe_float(
                            mod_data.get("sort_order", 0.0), 0.0
                        ),
                        created_at=str(mod_data.get("created_at", now)),
                        updated_at=str(mod_data.get("updated_at", now)),
                        metadata=dict(mod_data.get("metadata", {})),
                    )
                    modules[mod_id] = module
                particle_lifetime = emitter_data.get(
                    "particle_lifetime", (1.0, 2.0)
                )
                if not (isinstance(particle_lifetime, (list, tuple))
                        and len(particle_lifetime) == 2):
                    particle_lifetime = (1.0, 2.0)
                start_size = emitter_data.get("start_size", (0.1, 0.2))
                if not (isinstance(start_size, (list, tuple))
                        and len(start_size) == 2):
                    start_size = (0.1, 0.2)
                start_speed = emitter_data.get("start_speed", (1.0, 3.0))
                if not (isinstance(start_speed, (list, tuple))
                        and len(start_speed) == 2):
                    start_speed = (1.0, 3.0)
                start_color = emitter_data.get(
                    "start_color", (1.0, 1.0, 1.0, 1.0)
                )
                if not (isinstance(start_color, (list, tuple))
                        and len(start_color) == 4):
                    start_color = (1.0, 1.0, 1.0, 1.0)
                gravity = emitter_data.get("gravity", (0.0, -9.8, 0.0))
                if not (isinstance(gravity, (list, tuple))
                        and len(gravity) == 3):
                    gravity = (0.0, -9.8, 0.0)
                emitter = ParticleEmitter(
                    emitter_id=new_emitter_id,
                    name=str(emitter_data.get("name", new_emitter_id)),
                    description=str(emitter_data.get("description", "")),
                    emitter_type=_coerce_enum(
                        ParticleEmitterType,
                        emitter_data.get(
                            "emitter_type",
                            ParticleEmitterType.POINT.value,
                        ),
                        ParticleEmitterType.POINT,
                    ).value,
                    shape=_coerce_enum(
                        EmitterShape,
                        emitter_data.get("shape", EmitterShape.POINT.value),
                        EmitterShape.POINT,
                    ).value,
                    rate=_clamp(
                        _safe_float(emitter_data.get("rate", 10.0), 10.0),
                        _RATE_MIN, _RATE_MAX,
                    ),
                    burst_count=max(
                        _BURST_COUNT_MIN,
                        min(
                            _safe_int(
                                emitter_data.get("burst_count", 0), 0
                            ),
                            _BURST_COUNT_MAX,
                        ),
                    ),
                    burst_interval=_safe_float(
                        emitter_data.get("burst_interval", 0.0), 0.0
                    ),
                    lifetime=_clamp(
                        _safe_float(emitter_data.get("lifetime", 5.0), 5.0),
                        _LIFETIME_MIN, _LIFETIME_MAX,
                    ),
                    particle_lifetime=(
                        _safe_float(particle_lifetime[0], 1.0),
                        _safe_float(particle_lifetime[1], 2.0),
                    ),
                    particle_shape=_coerce_enum(
                        ParticleShape,
                        emitter_data.get(
                            "particle_shape", ParticleShape.QUAD.value
                        ),
                        ParticleShape.QUAD,
                    ).value,
                    blend_mode=_coerce_enum(
                        ParticleBlendMode,
                        emitter_data.get(
                            "blend_mode", ParticleBlendMode.ALPHA.value
                        ),
                        ParticleBlendMode.ALPHA,
                    ).value,
                    simulation_space=_coerce_enum(
                        ParticleSimulationSpace,
                        emitter_data.get(
                            "simulation_space",
                            ParticleSimulationSpace.WORLD.value,
                        ),
                        ParticleSimulationSpace.WORLD,
                    ).value,
                    max_particles=max(
                        _MAX_PARTICLES_MIN,
                        min(
                            _safe_int(
                                emitter_data.get("max_particles", 1000), 1000
                            ),
                            _MAX_PARTICLES_MAX,
                        ),
                    ),
                    start_size=(
                        _clamp(
                            _safe_float(start_size[0], 0.1),
                            _SIZE_MIN, _SIZE_MAX,
                        ),
                        _clamp(
                            _safe_float(start_size[1], 0.2),
                            _SIZE_MIN, _SIZE_MAX,
                        ),
                    ),
                    start_speed=(
                        _clamp(
                            _safe_float(start_speed[0], 1.0),
                            _SPEED_MIN, _SPEED_MAX,
                        ),
                        _clamp(
                            _safe_float(start_speed[1], 3.0),
                            _SPEED_MIN, _SPEED_MAX,
                        ),
                    ),
                    start_color=(
                        _safe_float(start_color[0], 1.0),
                        _safe_float(start_color[1], 1.0),
                        _safe_float(start_color[2], 1.0),
                        _safe_float(start_color[3], 1.0),
                    ),
                    gravity=(
                        _safe_float(gravity[0], 0.0),
                        _safe_float(gravity[1], -9.8),
                        _safe_float(gravity[2], 0.0),
                    ),
                    drag=_clamp(
                        _safe_float(emitter_data.get("drag", 0.0), 0.0),
                        _DRAG_MIN, _DRAG_MAX,
                    ),
                    modules=modules,
                    sort_mode=_coerce_enum(
                        SortMode,
                        emitter_data.get("sort_mode", SortMode.NONE.value),
                        SortMode.NONE,
                    ).value,
                    enabled=bool(emitter_data.get("enabled", True)),
                    tags=list(emitter_data.get("tags", [])),
                    thumbnail_url=str(emitter_data.get("thumbnail_url", "")),
                    created_at=str(emitter_data.get("created_at", now)),
                    updated_at=now,
                    metadata=dict(emitter_data.get("metadata", {})),
                )
                emitter.metadata["imported"] = True
                self._emitters[new_emitter_id] = emitter
                _evict_fifo_dict(self._emitters, self._config.max_emitters)
            # Reconstruct linked curves and gradients.
            for curve_data in data.get("curves", []) or []:
                if not isinstance(curve_data, dict):
                    continue
                ok_c, _msg_c, _c = self._import_curve(curve_data)
            for gradient_data in data.get("gradients", []) or []:
                if not isinstance(gradient_data, dict):
                    continue
                ok_g, _msg_g, _g = self._import_gradient(gradient_data)
            # Reconstruct the effect, remapping emitter ids.
            raw_emitter_ids = effect_data.get("emitter_ids", []) or []
            remapped_ids: List[str] = []
            for raw_id in raw_emitter_ids:
                key = str(raw_id)
                remapped_ids.append(id_remap.get(key, key))
            now = _now()
            effect = ParticleEffect(
                effect_id=effect_id,
                name=str(effect_data.get("name", effect_id)),
                description=str(effect_data.get("description", "")),
                category=_coerce_enum(
                    VFXCategory,
                    effect_data.get("category", VFXCategory.CUSTOM.value),
                    VFXCategory.CUSTOM,
                ).value,
                emitter_ids=remapped_ids,
                duration=_clamp(
                    _safe_float(effect_data.get("duration", 0.0), 0.0),
                    _LIFETIME_MIN, _LIFETIME_MAX,
                ),
                looping=bool(effect_data.get("looping", True)),
                prewarm=bool(effect_data.get("prewarm", False)),
                delay=_clamp(
                    _safe_float(effect_data.get("delay", 0.0), 0.0),
                    _LIFETIME_MIN, _LIFETIME_MAX,
                ),
                status=ParticleStatus.IDLE.value,
                sort_priority=_clamp(
                    _safe_float(
                        effect_data.get("sort_priority", 0.0), 0.0
                    ),
                    _SORT_PRIORITY_MIN, _SORT_PRIORITY_MAX,
                ),
                tags=list(effect_data.get("tags", [])),
                thumbnail_url=str(effect_data.get("thumbnail_url", "")),
                created_at=str(effect_data.get("created_at", now)),
                updated_at=now,
                metadata=dict(effect_data.get("metadata", {})),
            )
            effect.metadata["imported"] = True
            self._effects[effect_id] = effect
            _evict_fifo_dict(self._effects, self._config.max_effects)
            self._refresh_stats()
            self._emit(
                ParticleEventKind.EMITTER_CREATED.value,
                effect_id,
                f"Imported effect '{effect.name}'",
                {
                    "emitter_count": len(remapped_ids),
                    "imported_at": now,
                },
            )
            return True, "imported", effect

    def _import_curve(
        self, curve_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[ParticleCurve]]:
        """Reconstruct and register a single curve from a serialized dict."""
        curve_id = str(curve_data.get("curve_id", "")).strip()
        if not curve_id:
            curve_id = _new_id("curve")
        if curve_id in self._curves:
            curve_id = f"{curve_id}_{_new_id()}"
        now = _now()
        keyframes: List[ParticleKeyframe] = []
        for kf_data in curve_data.get("keyframes", []) or []:
            if not isinstance(kf_data, dict):
                continue
            kf_id = str(kf_data.get("keyframe_id", "")) or _new_id("kf")
            keyframes.append(
                ParticleKeyframe(
                    keyframe_id=kf_id,
                    time=_clamp(
                        _safe_float(kf_data.get("time", 0.0), 0.0), 0.0, 1.0
                    ),
                    value=_safe_float(kf_data.get("value", 0.0), 0.0),
                    in_tangent=_safe_float(
                        kf_data.get("in_tangent", 0.0), 0.0
                    ),
                    out_tangent=_safe_float(
                        kf_data.get("out_tangent", 0.0), 0.0
                    ),
                    interpolation=str(
                        kf_data.get("interpolation", "linear")
                    ),
                    metadata=dict(kf_data.get("metadata", {})),
                )
            )
        if not keyframes:
            keyframes = [_make_keyframe(0.0, 0.0)]
        curve = ParticleCurve(
            curve_id=curve_id,
            name=str(curve_data.get("name", curve_id)),
            keyframes=keyframes,
            loop=bool(curve_data.get("loop", curve_data.get("looping", False))),
            pre_value=_safe_float(curve_data.get("pre_value", 0.0), 0.0),
            post_value=_safe_float(curve_data.get("post_value", 1.0), 1.0),
            created_at=str(curve_data.get("created_at", now)),
            updated_at=now,
            metadata=dict(curve_data.get("metadata", {})),
        )
        curve.metadata["imported"] = True
        self._curves[curve_id] = curve
        _evict_fifo_dict(self._curves, self._config.max_curves)
        return True, "imported", curve

    def _import_gradient(
        self, gradient_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[VFXGradient]]:
        """Reconstruct and register a single gradient from a serialized dict."""
        gradient_id = str(gradient_data.get("gradient_id", "")).strip()
        if not gradient_id:
            gradient_id = _new_id("gradient")
        if gradient_id in self._gradients:
            gradient_id = f"{gradient_id}_{_new_id()}"
        now = _now()
        stops: List[Tuple[float, float, float, float, float]] = []
        for stop_data in gradient_data.get("stops", []) or []:
            if not isinstance(stop_data, (list, tuple)):
                continue
            if len(stop_data) < 5:
                continue
            stops.append((
                _clamp(_safe_float(stop_data[0], 0.0), 0.0, 1.0),
                _clamp(_safe_float(stop_data[1], 0.0), 0.0, 1.0),
                _clamp(_safe_float(stop_data[2], 0.0), 0.0, 1.0),
                _clamp(_safe_float(stop_data[3], 0.0), 0.0, 1.0),
                _clamp(_safe_float(stop_data[4], 1.0), 0.0, 1.0),
            ))
        if not stops:
            stops = [(0.0, 1.0, 1.0, 1.0, 1.0), (1.0, 0.0, 0.0, 0.0, 1.0)]
        gradient = VFXGradient(
            gradient_id=gradient_id,
            name=str(gradient_data.get("name", gradient_id)),
            stops=stops,
            loop=bool(
                gradient_data.get("loop", gradient_data.get("looping", False))
            ),
            created_at=str(gradient_data.get("created_at", now)),
            updated_at=now,
            metadata=dict(gradient_data.get("metadata", {})),
        )
        gradient.metadata["imported"] = True
        self._gradients[gradient_id] = gradient
        _evict_fifo_dict(self._gradients, self._config.max_gradients)
        return True, "imported", gradient

    # ------------------------------------------------------------------
    # System Lifecycle
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_emitters": len(self._emitters),
                "total_effects": len(self._effects),
                "total_batches": len(self._batches),
                "total_curves": len(self._curves),
                "total_gradients": len(self._gradients),
                "total_events": len(self._events),
                "active_batches": sum(
                    1 for b in self._batches.values()
                    if b.status == ParticleStatus.PLAYING.value
                ),
                "tick_count": self._tick_count,
            }

    def get_stats(self) -> ParticleVFXStats:
        """Return aggregate statistics (refreshed before return)."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_config(self) -> ParticleVFXConfig:
        """Return the current runtime configuration."""
        with self._lock:
            return self._config

    def set_config(
        self, **kwargs: Any
    ) -> Tuple[bool, str, ParticleVFXConfig]:
        """Update runtime configuration fields.

        Accepts any subset of ParticleVFXConfig fields. Numeric fields are
        coerced and clamped; boolean fields are coerced; enum-typed fields
        (``default_simulation_space``, ``default_blend_mode``,
        ``default_shape``) are coerced via their respective enums.
        """
        with self._lock:
            for key in (
                "max_emitters", "max_effects", "max_batches",
                "max_curves", "max_gradients", "max_events",
                "max_particles_per_batch",
            ):
                if key in kwargs and kwargs[key] is not None:
                    setattr(
                        self._config, key,
                        max(
                            1,
                            _safe_int(
                                kwargs[key], getattr(self._config, key)
                            ),
                        ),
                    )
            for key in ("enable_sorting", "enable_gpu"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(self._config, key, bool(kwargs[key]))
            if "default_simulation_space" in kwargs and \
                    kwargs["default_simulation_space"] is not None:
                enum_val = _coerce_enum(
                    ParticleSimulationSpace,
                    kwargs["default_simulation_space"], None,
                )
                if enum_val is not None:
                    self._config.default_simulation_space = enum_val.value
            if "default_blend_mode" in kwargs and \
                    kwargs["default_blend_mode"] is not None:
                enum_val = _coerce_enum(
                    ParticleBlendMode, kwargs["default_blend_mode"], None
                )
                if enum_val is not None:
                    self._config.default_blend_mode = enum_val.value
            if "default_shape" in kwargs and \
                    kwargs["default_shape"] is not None:
                enum_val = _coerce_enum(
                    ParticleShape, kwargs["default_shape"], None
                )
                if enum_val is not None:
                    self._config.default_shape = enum_val.value
            if "metadata" in kwargs and kwargs["metadata"] is not None:
                if isinstance(kwargs["metadata"], dict):
                    self._config.metadata.update(kwargs["metadata"])
            self._emit(
                ParticleEventKind.CONFIG_CHANGED.value,
                "",
                "Configuration updated",
                {"keys": list(kwargs.keys())},
            )
            return True, "updated", self._config

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance the system by one frame.

        Performs housekeeping: refreshes statistics, trims the event log
        and batch store to capacity, advances every playing batch by the
        elapsed delta time (aging particles, emitting new ones according
        to each emitter rate, and finishing batches that exceed their
        duration), and reports the current frame state.

        Args:
            dt: Delta time in seconds since the last tick.

        Returns:
            A dict describing the post-tick system state.
        """
        with self._lock:
            self._tick_count += 1
            _evict_fifo_list(self._events, self._config.max_events)
            _evict_fifo_dict(self._batches, self._config.max_batches)
            dt_value = _safe_float(dt, 0.016)
            if dt_value < 0.0:
                dt_value = 0.0
            finished_batches = 0
            emitted_this_tick = 0
            for batch in self._batches.values():
                if batch.status != ParticleStatus.PLAYING.value:
                    continue
                batch.age += dt_value * batch.speed
                # Estimate particles emitted this tick from linked emitters.
                emit_count = 0
                for eid in batch.emitter_ids:
                    emitter = self._emitters.get(eid)
                    if emitter is None or not emitter.enabled:
                        continue
                    emit_count += int(
                        emitter.rate * dt_value * batch.speed
                    )
                batch.emitted_total += emit_count
                emitted_this_tick += emit_count
                # Decay active particles by lifetime and add new emissions.
                avg_life = 1.0
                for eid in batch.emitter_ids:
                    emitter = self._emitters.get(eid)
                    if emitter is None:
                        continue
                    avg_life = max(
                        avg_life,
                        (emitter.particle_lifetime[0]
                         + emitter.particle_lifetime[1]) / 2.0,
                    )
                if avg_life > 0.0:
                    decay = max(0.0, 1.0 - (dt_value / avg_life))
                else:
                    decay = 1.0
                batch.active_particles = int(
                    batch.active_particles * decay + emit_count
                )
                batch.active_particles = min(
                    batch.active_particles, batch.max_particles
                )
                batch.updated_at = _now()
                # Finish non-looping batches that exceed their duration.
                if batch.duration > 0.0 and not batch.looping:
                    if batch.age >= batch.duration:
                        batch.status = ParticleStatus.FINISHED.value
                        batch.active_particles = 0
                        finished_batches += 1
            self._stats.total_emitted += emitted_this_tick
            self._stats.tick_count = self._tick_count
            self._refresh_stats()
            result = {
                "tick": self._tick_count,
                "dt": dt_value,
                "total_emitters": len(self._emitters),
                "total_effects": len(self._effects),
                "total_batches": len(self._batches),
                "active_batches": self._stats.active_batches,
                "active_particles": self._stats.active_particles,
                "finished_batches": finished_batches,
                "emitted_this_tick": emitted_this_tick,
                "total_emitted": self._stats.total_emitted,
                "total_bursts": self._stats.total_bursts,
            }
            self._emit(
                ParticleEventKind.EFFECT_PLAYED.value,
                "",
                f"Tick {self._tick_count}",
                result,
            )
            return result

    def list_events(
        self, limit: int = 100
    ) -> List[ParticleVFXEvent]:
        """Return the most recent audit events (newest last)."""
        with self._lock:
            cap = min(
                _safe_int(limit, _DEFAULT_LIST_LIMIT), self._config.max_events
            )
            cap = max(1, cap)
            return list(self._events[-cap:])

    def get_snapshot(self) -> ParticleVFXSnapshot:
        """Return an immutable snapshot of the whole system.

        The emitter, batch, and event lists are bounded so the snapshot
        stays reasonably sized for transmission and logging.
        """
        with self._lock:
            self._refresh_stats()
            return ParticleVFXSnapshot(
                timestamp=_now(),
                emitters=[
                    e.to_dict() for e in list(self._emitters.values())[:50]
                ],
                effects=[
                    f.to_dict() for f in list(self._effects.values())[:50]
                ],
                batches=[
                    b.to_dict() for b in list(self._batches.values())[:50]
                ],
                curves=[
                    c.to_dict() for c in list(self._curves.values())[:50]
                ],
                gradients=[
                    g.to_dict() for g in list(self._gradients.values())[:50]
                ],
                events=[
                    e.to_dict() for e in list(self._events)[-50:]
                ],
                stats=self._stats.to_dict(),
            )

    def reset(self) -> None:
        """Clear all stores and re-seed with default data."""
        with self._lock:
            self._emitters.clear()
            self._effects.clear()
            self._batches.clear()
            self._curves.clear()
            self._gradients.clear()
            self._events.clear()
            self._config = ParticleVFXConfig()
            self._stats = ParticleVFXStats()
            self._tick_count = 0
            self._event_counter = 0
            self._batch_counter = 0
            self._initialized = False
            self._emit(
                ParticleEventKind.SYSTEM_RESET.value,
                "",
                "System reset",
            )
            self._seed()
            self._initialized = True


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_particle_vfx_system() -> ParticleVFXSystem:
    """Return the shared ParticleVFXSystem singleton instance."""
    return ParticleVFXSystem.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "ParticleEmitterType",
    "ParticleBlendMode",
    "ParticleShape",
    "ParticleSimulationSpace",
    "ParticleStatus",
    "VFXCategory",
    "SortMode",
    "EmitterShape",
    "ParticleEventKind",
    # Data classes
    "ParticleModule",
    "ParticleEmitter",
    "ParticleEffect",
    "ParticleBatch",
    "ParticleKeyframe",
    "ParticleCurve",
    "VFXGradient",
    "ParticleVFXConfig",
    "ParticleVFXStats",
    "ParticleVFXSnapshot",
    "ParticleVFXEvent",
    # Main system
    "ParticleVFXSystem",
    "get_particle_vfx_system",
]