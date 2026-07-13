"""
SparkLabs Engine - Acoustic Wave Propagation System

A physics-grade acoustic simulation for the SparkLabs AI-native game
engine. It models sound sources, listeners, occluding barriers, and
reverberant echo zones, then propagates spherical wavefronts through
the scene to support stealth mechanics, AI hearing, sonar, echolocation,
and acoustic puzzles.

The system implements the canonical acoustic formulas:
  - Sound speed in air: c = 343 m/s (at 20 degrees Celsius).
  - Inverse square law: I = I0 / (4 * pi * r^2).
  - Geometric spreading attenuation: dL = 20 * log10(r1 / r2).
  - Doppler shift: f' = f * (c +/- v_listener) / (c +/- v_source).
  - Barrier transmission loss: L_tx = L_src - transmission_loss_db.
  - Absorption: A = absorption_coefficient * incident_intensity.
  - Sabine reverberation: T60 = 0.161 * V / (sum(Si * alpha_i)).
  - Sound pressure level: SPL = 20 * log10(p / p_ref), p_ref = 20 uPa.

Architecture:
  _AcousticWaveSystem (Singleton)
    |-- AcousticSource, AcousticListener, SoundBarrier, EchoZone
    |-- Wavefront, PropagationPath, DopplerShift, AcousticStats
    |-- AcousticConfig, AcousticSnapshot, AcousticEvent
    |-- SourceType, WaveStatus, BarrierMaterial, AcousticEventKind

Core Capabilities:
  - register_source / remove_source / get_source / list_sources
  - register_listener / remove_listener / get_listener / list_listeners
  - register_barrier / remove_barrier / get_barrier / list_barriers
  - register_echo_zone / remove_echo_zone / get_echo_zone / list_echo_zones
  - emit_wave / get_wavefront / list_wavefronts
  - compute_propagation / compute_attenuation / compute_doppler
  - check_hearing / get_audible_sources / compute_sound_level
  - check_occlusion / find_reflection_path
  - ai_predict_detection / ai_optimize_barrier_placement / ai_assess_stealth
  - get_sound_map / get_visualization_data
  - reset_sources / list_events / tick
  - get_stats / get_snapshot / get_status / get_config / set_config

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`_AcousticWaveSystem.get_instance` or the module-level
:func:`get_acoustic_wave_system` factory.

Usage:
    aw = get_acoustic_wave_system()
    ok, msg, source = aw.register_source("src_footstep", (10.0, 5.0, 0.0), 60.0, "footstep")
    ok, msg, audible = aw.check_hearing("listener_guard_01", "src_footstep")
    ok, msg, doppler = aw.compute_doppler("src_vehicle", "listener_player")
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Physical Constants
# ---------------------------------------------------------------------------

# Speed of sound in air at 20 degrees Celsius, in meters per second.
_SPEED_OF_SOUND: float = 343.0

# Reference sound pressure of 20 micro-pascals, the threshold of human
# hearing. Used when converting pressure to decibels.
_REF_PRESSURE: float = 20e-6

# Air density in kilograms per cubic meter at sea level.
_AIR_DENSITY: float = 1.225

# Tiny epsilon used to avoid division by zero in distance and vector ops.
_EPSILON: float = 1e-9

# Default ambient sound floor in decibels. A quiet room is around 30 dB.
_AMBIENT_DB: float = 30.0


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Each bounded store uses FIFO eviction once its capacity is exceeded.
# The numbers are intentionally generous so that gameplay-heavy scenes
# can keep a long history of wavefronts and propagation paths without
# silently dropping data that AI analysis might still need.

_MAX_SOURCES: int = 500
_MAX_LISTENERS: int = 300
_MAX_BARRIERS: int = 400
_MAX_ECHO_ZONES: int = 200
_MAX_WAVEFRONTS: int = 2000
_MAX_PROPAGATION_PATHS: int = 4000
_MAX_DOPPLER_RECORDS: int = 2000
_MAX_EVENTS: int = 10000
_MAX_SOUND_MAP_CELLS: int = 4096


# ---------------------------------------------------------------------------
# Module-level Lock
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a Z suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, falling back to default on failure."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Coerce a value to int, falling back to default on failure."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Drop the oldest entries from a dict until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Drop the oldest entries from a list until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value into JSON-serializable primitives."""
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
    """Serialize a dataclass instance into a plain dict.

    The dataclass field set is inspected first so that nested dataclasses
    and Enum-typed fields are normalized into JSON-friendly values via
    :func:`_to_jsonable`. Tuples become lists, Enums become their values,
    and nested dataclasses are recursively expanded.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        return instance
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to default."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


# ---------------------------------------------------------------------------
# Vector Helpers (3D)
# ---------------------------------------------------------------------------


def _vec_add(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_sub(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_scale(
    v: Tuple[float, float, float], s: float
) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec_dot(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_cross(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec_length(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    length = _vec_length(v)
    if length < _EPSILON:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _vec_distance(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    return _vec_length(_vec_sub(a, b))


def _to_vec3(value: Any, default: Tuple[float, float, float] = (0.0, 0.0, 0.0)
             ) -> Tuple[float, float, float]:
    """Coerce a list/tuple/None into a 3-float tuple."""
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        try:
            return (float(value[0]), float(value[1]), float(value[2]))
        except (IndexError, TypeError, ValueError):
            return default
    return default


def _to_vec4(value: Any,
             default: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
             ) -> Tuple[float, float, float, float]:
    """Coerce a list/tuple/None into a 4-float tuple."""
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        try:
            return (float(value[0]), float(value[1]),
                    float(value[2]), float(value[3]))
        except (IndexError, TypeError, ValueError):
            return default
    return default


# ---------------------------------------------------------------------------
# Acoustic Helpers
# ---------------------------------------------------------------------------


def _db_to_linear(db: float) -> float:
    """Convert a decibel value to linear intensity."""
    return 10.0 ** (_safe_float(db, 0.0) / 10.0)


def _linear_to_db(linear: float) -> float:
    """Convert a linear intensity value to decibels."""
    linear = _safe_float(linear, 0.0)
    if linear <= _EPSILON:
        return -math.inf
    return 10.0 * math.log10(linear)


def _pressure_to_spl(pressure: float) -> float:
    """Convert sound pressure in pascals to SPL in decibels."""
    p = _safe_float(pressure, 0.0)
    if abs(p) < _EPSILON:
        return -math.inf
    return 20.0 * math.log10(abs(p) / _REF_PRESSURE)


def _spl_to_pressure(spl_db: float) -> float:
    """Convert SPL in decibels to sound pressure in pascals."""
    return _REF_PRESSURE * (10.0 ** (_safe_float(spl_db, 0.0) / 20.0))


def _spreading_attenuation(distance_m: float, reference_m: float = 1.0) -> float:
    """Geometric spreading attenuation in dB using 20*log10(r/r0)."""
    r = max(_EPSILON, _safe_float(distance_m, 0.0))
    r0 = max(_EPSILON, _safe_float(reference_m, 1.0))
    return 20.0 * math.log10(r / r0)


def _air_absorption_db(distance_m: float, frequency_hz: float) -> float:
    """Approximate frequency-dependent air absorption over distance.

    Uses a coarse model: alpha ~= 0.0001 * (f/1000)^2 dB/m. This is not a
    full ANSI absorption curve but is stable, monotonic, and good enough
    for gameplay. Real atmospheric absorption depends on temperature and
    humidity; gameplay code can override via configuration if needed.
    """
    d = max(0.0, _safe_float(distance_m, 0.0))
    f = max(0.0, _safe_float(frequency_hz, 0.0))
    alpha = 0.0001 * (f / 1000.0) ** 2
    return alpha * d


def _inverse_square_intensity(intensity_0: float, distance_m: float) -> float:
    """Inverse square law: I = I0 / (4 * pi * r^2)."""
    r = max(_EPSILON, _safe_float(distance_m, 0.0))
    return _safe_float(intensity_0, 0.0) / (4.0 * math.pi * r * r)


def _doppler_shift(
    source_velocity: Tuple[float, float, float],
    listener_velocity: Tuple[float, float, float],
    source_pos: Tuple[float, float, float],
    listener_pos: Tuple[float, float, float],
    frequency_hz: float,
) -> Tuple[float, float]:
    """Compute the Doppler-shifted frequency and relative radial velocity.

    Returns (shifted_frequency_hz, relative_velocity_ms) where positive
    relative velocity means source and listener are approaching.
    """
    f = _safe_float(frequency_hz, 0.0)
    if f <= 0.0:
        return (0.0, 0.0)
    direction = _vec_sub(listener_pos, source_pos)
    distance = _vec_length(direction)
    if distance < _EPSILON:
        return (f, 0.0)
    unit = _vec_normalize(direction)
    # Radial velocity component along the source->listener axis.
    v_source_radial = _vec_dot(source_velocity, unit)
    v_listener_radial = _vec_dot(listener_velocity, unit)
    # Approaching means the gap is closing: source moves toward listener
    # (positive radial) and listener moves toward source (negative radial
    # along the axis). Compute closing speed.
    closing = v_source_radial - v_listener_radial
    c = _SPEED_OF_SOUND
    # Clamp so we never divide by zero or go negative.
    denom = max(_EPSILON, c - closing)
    shifted = f * c / denom
    return (shifted, closing)


def _point_in_bounds_2d(
    position: Tuple[float, float, float],
    bounds: Tuple[float, float, float, float],
) -> bool:
    """Test whether a 3D point lies inside the 2D (x, z) bounds."""
    x, _, z = position
    min_x, min_z, max_x, max_z = bounds
    return (min_x <= x <= max_x) and (min_z <= z <= max_z)


def _barrier_aabb(
    barrier_pos: Tuple[float, float, float],
    dimensions: Tuple[float, float, float],
) -> Tuple[float, float, float, float, float, float]:
    """Return the axis-aligned bounding box (min_x, min_y, min_z, max_x, max_y, max_z)."""
    w, h, d = dimensions
    px, py, pz = barrier_pos
    return (px - w / 2.0, py - h / 2.0, pz - d / 2.0,
            px + w / 2.0, py + h / 2.0, pz + d / 2.0)


def _segment_hits_aabb(
    start: Tuple[float, float, float],
    end: Tuple[float, float, float],
    aabb: Tuple[float, float, float, float, float, float],
) -> bool:
    """Slab-based ray/AABB intersection test for a line segment."""
    min_x, min_y, min_z, max_x, max_y, max_z = aabb
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    t_min = 0.0
    t_max = 1.0
    for axis_idx, (delta, lo, hi, s) in enumerate(
        (
            (dx, min_x, max_x, start[0]),
            (dy, min_y, max_y, start[1]),
            (dz, min_z, max_z, start[2]),
        )
    ):
        if abs(delta) < _EPSILON:
            if s < lo or s > hi:
                return False
            continue
        inv = 1.0 / delta
        t1 = (lo - s) * inv
        t2 = (hi - s) * inv
        if t1 > t2:
            t1, t2 = t2, t1
        t_min = max(t_min, t1)
        t_max = min(t_max, t2)
        if t_min > t_max:
            return False
    return t_max >= 0.0


def _material_defaults(material: str) -> Tuple[float, float]:
    """Return (absorption_coefficient, transmission_loss_db) for a material."""
    table = {
        BarrierMaterial.WOOD.value: (0.20, 25.0),
        BarrierMaterial.STONE.value: (0.05, 50.0),
        BarrierMaterial.METAL.value: (0.04, 45.0),
        BarrierMaterial.GLASS.value: (0.12, 30.0),
        BarrierMaterial.CONCRETE.value: (0.03, 60.0),
        BarrierMaterial.FABRIC.value: (0.45, 8.0),
        BarrierMaterial.WATER.value: (0.01, 70.0),
        BarrierMaterial.AIR.value: (0.0, 0.0),
    }
    return table.get(str(material).lower(),
                     (0.10, 20.0))


def _stealth_label(score: float) -> str:
    """Map a stealth score in [0, 1] to a qualitative label."""
    s = _clamp(_safe_float(score, 0.0), 0.0, 1.0)
    if s >= 0.85:
        return "exposed"
    if s >= 0.6:
        return "risky"
    if s >= 0.35:
        return "moderate"
    if s >= 0.1:
        return "safe"
    return "silent"


def _detection_label(probability: float) -> str:
    """Map a detection probability in [0, 1] to a label."""
    p = _clamp(_safe_float(probability, 0.0), 0.0, 1.0)
    if p >= 0.85:
        return "certain"
    if p >= 0.6:
        return "likely"
    if p >= 0.35:
        return "possible"
    if p >= 0.1:
        return "unlikely"
    return "negligible"


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class SourceType(Enum):
    """Classification of an acoustic source by its gameplay role."""
    FOOTSTEP = "footstep"
    VOICE = "voice"
    EXPLOSION = "explosion"
    VEHICLE = "vehicle"
    WEAPON = "weapon"
    ANIMAL = "animal"
    MACHINERY = "machinery"
    AMBIENT = "ambient"


class WaveStatus(Enum):
    """Lifecycle status of a propagating wavefront."""
    EMITTED = "emitted"
    PROPAGATING = "propagating"
    REFLECTED = "reflected"
    ABSORBED = "absorbed"
    FADED = "faded"


class BarrierMaterial(Enum):
    """Material classification of a sound barrier."""
    WOOD = "wood"
    STONE = "stone"
    METAL = "metal"
    GLASS = "glass"
    CONCRETE = "concrete"
    FABRIC = "fabric"
    WATER = "water"
    AIR = "air"


class PathType(Enum):
    """Classification of a propagation path from source to listener."""
    DIRECT = "direct"
    REFLECTED = "reflected"
    DIFFRACTED = "diffracted"
    TRANSMITTED = "transmitted"


class AcousticEventKind(Enum):
    """Audit event types emitted by the acoustic wave system."""
    SOURCE_REGISTERED = "source_registered"
    SOURCE_REMOVED = "source_removed"
    SOURCE_UPDATED = "source_updated"
    LISTENER_REGISTERED = "listener_registered"
    LISTENER_REMOVED = "listener_removed"
    LISTENER_UPDATED = "listener_updated"
    BARRIER_REGISTERED = "barrier_registered"
    BARRIER_REMOVED = "barrier_removed"
    BARRIER_UPDATED = "barrier_updated"
    ECHO_ZONE_REGISTERED = "echo_zone_registered"
    ECHO_ZONE_REMOVED = "echo_zone_removed"
    ECHO_ZONE_UPDATED = "echo_zone_updated"
    WAVE_EMITTED = "wave_emitted"
    WAVE_FADED = "wave_faded"
    WAVE_ABSORBED = "wave_absorbed"
    PROPAGATION_COMPUTED = "propagation_computed"
    DOPPLER_COMPUTED = "doppler_computed"
    HEARING_CHECK = "hearing_check"
    OCCLUSION_CHECK = "occlusion_check"
    REFLECTION_FOUND = "reflection_found"
    SOUND_MAP_GENERATED = "sound_map_generated"
    AI_ASSESSMENT = "ai_assessment"
    CONFIG_UPDATED = "config_updated"
    SOURCES_RESET = "sources_reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class AcousticSource:
    """A sound-emitting entity in 3D space.

    Each source carries an intensity in decibels at 1 meter, a center
    frequency, an optional velocity vector for Doppler calculations, and
    directional parameters that shape the emitted wave. Active sources
    can be queried by listeners via :meth:`check_hearing`.
    """
    source_id: str = ""
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    intensity_db: float = 60.0
    frequency_hz: float = 440.0
    source_type: str = SourceType.AMBIENT.value
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    active: bool = True
    directional: bool = False
    direction: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    spread_angle: float = 360.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AcousticListener:
    """A hearing-capable entity that can detect acoustic sources.

    The listener has a hearing threshold in decibels, a maximum hearing
    range in meters, and a frequency-sensitivity table mapping frequency
    ranges (in Hz) to multipliers. A velocity vector supports Doppler
    calculations, and detected_sources records the IDs of sources the
    listener is currently aware of.
    """
    listener_id: str = ""
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    hearing_threshold_db: float = 30.0
    hearing_range_m: float = 100.0
    frequency_sensitivity: Dict[str, float] = field(
        default_factory=lambda: {
            "0-250": 0.6,
            "250-2000": 1.0,
            "2000-8000": 0.9,
            "8000-20000": 0.5,
        }
    )
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    active: bool = True
    detected_sources: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SoundBarrier:
    """An axis-aligned occluder that absorbs and blocks sound.

    Barriers are axis-aligned boxes described by a center position and
    dimensions (width, height, depth). Each material has an absorption
    coefficient in [0, 1] and a transmission loss in decibels that is
    subtracted from any wave passing through the barrier.
    """
    barrier_id: str = ""
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    dimensions: Tuple[float, float, float] = (1.0, 2.0, 1.0)
    material: str = BarrierMaterial.WOOD.value
    absorption_coefficient: float = 0.2
    transmission_loss_db: float = 25.0
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EchoZone:
    """A rectangular region that reflects and reverberates sound.

    Echo zones are 2D rectangles in the (x, z) plane with a reflection
    coefficient in [0, 1] and a reverberation time T60 in seconds. They
    model indoor spaces, canyons, and caves where reflections dominate.
    """
    zone_id: str = ""
    name: str = ""
    bounds: Tuple[float, float, float, float] = (0.0, 0.0, 10.0, 10.0)
    reflection_coefficient: float = 0.5
    reverb_time_s: float = 0.8
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Wavefront:
    """An expanding spherical wavefront emitted by a source.

    A wavefront starts at an origin with an intensity in decibels and a
    center frequency, then expands at the speed of sound. Its status
    transitions EMITTED -> PROPAGATING -> (REFLECTED | ABSORBED | FADED)
    as it travels through the scene.
    """
    wavefront_id: str = ""
    source_id: str = ""
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius_m: float = 0.0
    intensity_db: float = 60.0
    frequency_hz: float = 440.0
    status: str = WaveStatus.EMITTED.value
    emitted_at: float = 0.0
    velocity_mps: float = _SPEED_OF_SOUND
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PropagationPath:
    """A computed path from a source to a listener.

    The path is a list of segments, each a tuple of (start, end, medium).
    Medium is one of "air", "barrier:<material>", or "echo:<zone_id>".
    The path records total distance, total attenuation, the number of
    reflections, whether it is occluded, and a path type classification.
    """
    path_id: str = ""
    source_id: str = ""
    listener_id: str = ""
    segments: List[Tuple[Tuple[float, float, float],
                         Tuple[float, float, float], str]] = field(
        default_factory=list
    )
    total_distance_m: float = 0.0
    total_attenuation_db: float = 0.0
    reflection_count: int = 0
    occluded: bool = False
    path_type: str = PathType.DIRECT.value
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DopplerShift:
    """The Doppler frequency shift between a source and a listener."""
    doppler_id: str = ""
    source_id: str = ""
    listener_id: str = ""
    original_frequency_hz: float = 440.0
    shifted_frequency_hz: float = 440.0
    relative_velocity_ms: float = 0.0
    shift_factor: float = 1.0
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AcousticConfig:
    """Tunable runtime configuration for the acoustic wave system."""
    max_sources: int = _MAX_SOURCES
    max_listeners: int = _MAX_LISTENERS
    max_barriers: int = _MAX_BARRIERS
    max_echo_zones: int = _MAX_ECHO_ZONES
    max_wavefronts: int = _MAX_WAVEFRONTS
    max_propagation_paths: int = _MAX_PROPAGATION_PATHS
    max_doppler_records: int = _MAX_DOPPLER_RECORDS
    max_events: int = _MAX_EVENTS
    speed_of_sound: float = _SPEED_OF_SOUND
    ambient_db: float = _AMBIENT_DB
    reference_distance_m: float = 1.0
    sound_map_resolution: int = 16
    enable_air_absorption: bool = True
    enable_doppler: bool = True
    enable_reflections: bool = True
    enable_diffraction: bool = True
    wavefront_fade_db: float = 0.0
    max_wavefront_radius_m: float = 1000.0
    ai_analysis_frequency: int = 50
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AcousticStats:
    """Roll-up statistics maintained across the system lifetime."""
    total_sources: int = 0
    active_sources: int = 0
    total_listeners: int = 0
    active_listeners: int = 0
    total_barriers: int = 0
    active_barriers: int = 0
    total_echo_zones: int = 0
    active_echo_zones: int = 0
    total_wavefronts_emitted: int = 0
    active_wavefronts: int = 0
    total_propagation_paths: int = 0
    total_doppler_records: int = 0
    total_hearing_checks: int = 0
    total_occlusion_checks: int = 0
    total_reflections_found: int = 0
    total_sound_maps: int = 0
    total_ai_assessments: int = 0
    tick_count: int = 0
    peak_intensity_db: float = 0.0
    avg_propagation_distance_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AcousticSnapshot:
    """A point-in-time snapshot of the full system state."""
    timestamp: str = field(default_factory=_now)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    listeners: List[Dict[str, Any]] = field(default_factory=list)
    barriers: List[Dict[str, Any]] = field(default_factory=list)
    echo_zones: List[Dict[str, Any]] = field(default_factory=list)
    wavefronts: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AcousticEvent:
    """An internal audit event emitted by the acoustic wave system."""
    event_id: str = ""
    timestamp: str = field(default_factory=_now)
    event_type: str = AcousticEventKind.SOURCE_REGISTERED.value
    description: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Acoustic Wave System (Singleton)
# ---------------------------------------------------------------------------


class _AcousticWaveSystem:
    """A physical acoustic wave propagation simulator.

    The system is thread-safe and implemented as a singleton with
    double-checked locking. ``_init_lock`` guards singleton creation and
    seeding; ``_lock`` guards all mutating operations so the internal
    dictionaries stay consistent across concurrent callers.

    The simulation model intentionally stays lightweight so it can run
    every frame: each wavefront is a sphere expanding at the speed of
    sound, listeners hear a source when the attenuated intensity at
    their position exceeds their threshold, and barriers occlude the
    line of sight between source and listener. Reflections route sound
    through echo zones using simple mirror-image geometry, while
    Doppler shifts use the classic moving-source/moving-listener
    formula.
    """

    _instance: Optional["_AcousticWaveSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._seeded: bool = False
        self._sources: Dict[str, AcousticSource] = {}
        self._listeners: Dict[str, AcousticListener] = {}
        self._barriers: Dict[str, SoundBarrier] = {}
        self._echo_zones: Dict[str, EchoZone] = {}
        self._wavefronts: Dict[str, Wavefront] = {}
        self._propagation_paths: Dict[str, PropagationPath] = {}
        self._doppler_records: Dict[str, DopplerShift] = {}
        self._events: List[AcousticEvent] = []
        self._config = AcousticConfig()
        self._stats = AcousticStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._wavefront_counter: int = 0
        self._path_counter: int = 0
        self._doppler_counter: int = 0
        self._simulation_time: float = 0.0
        self._propagation_distance_accum: float = 0.0
        self._propagation_distance_count: int = 0

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "_AcousticWaveSystem":
        """Return the shared singleton, creating it if needed."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Explicitly seed the system if it has not been seeded yet."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed_data()
            self._initialized = True

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the system with a canonical set of acoustic data.

        Called once during :meth:`initialize`. The seed includes five
        acoustic sources, four listeners, three barriers, three echo
        zones, four wavefronts, and a handful of audit events so that
        the system is immediately usable for gameplay and demos.
        """
        with self._lock:
            if self._seeded:
                return

            # ----------------------------------------------------------
            # Acoustic Sources (5)
            # ----------------------------------------------------------
            source_seeds: List[AcousticSource] = [
                AcousticSource(
                    source_id="src_footstep_alpha",
                    name="Player Footsteps",
                    position=(10.0, 0.0, 5.0),
                    intensity_db=58.0,
                    frequency_hz=180.0,
                    source_type=SourceType.FOOTSTEP.value,
                    velocity=(0.0, 0.0, 0.0),
                    active=True,
                    directional=False,
                    direction=(1.0, 0.0, 0.0),
                    spread_angle=360.0,
                    metadata={"scene": "demo", "owner": "player"},
                ),
                AcousticSource(
                    source_id="src_guard_voice",
                    name="Guard Shout",
                    position=(40.0, 0.0, 20.0),
                    intensity_db=72.0,
                    frequency_hz=850.0,
                    source_type=SourceType.VOICE.value,
                    velocity=(0.0, 0.0, 0.0),
                    active=True,
                    directional=True,
                    direction=(-1.0, 0.0, 0.0),
                    spread_angle=120.0,
                    metadata={"scene": "demo", "owner": "guard"},
                ),
                AcousticSource(
                    source_id="src_explosion_warehouse",
                    name="Warehouse Explosion",
                    position=(-25.0, 0.0, -15.0),
                    intensity_db=140.0,
                    frequency_hz=60.0,
                    source_type=SourceType.EXPLOSION.value,
                    velocity=(0.0, 0.0, 0.0),
                    active=True,
                    directional=False,
                    direction=(0.0, 1.0, 0.0),
                    spread_angle=360.0,
                    metadata={"scene": "demo", "one_shot": True},
                ),
                AcousticSource(
                    source_id="src_vehicle_engine",
                    name="Patrol Truck Engine",
                    position=(80.0, 0.0, 40.0),
                    intensity_db=95.0,
                    frequency_hz=120.0,
                    source_type=SourceType.VEHICLE.value,
                    velocity=(6.0, 0.0, 0.0),
                    active=True,
                    directional=True,
                    direction=(1.0, 0.0, 0.0),
                    spread_angle=180.0,
                    metadata={"scene": "demo", "moving": True},
                ),
                AcousticSource(
                    source_id="src_machinery_hum",
                    name="Generator Hum",
                    position=(15.0, 0.0, -30.0),
                    intensity_db=68.0,
                    frequency_hz=220.0,
                    source_type=SourceType.MACHINERY.value,
                    velocity=(0.0, 0.0, 0.0),
                    active=True,
                    directional=False,
                    direction=(0.0, 1.0, 0.0),
                    spread_angle=360.0,
                    metadata={"scene": "demo", "looping": True},
                ),
            ]
            for src in source_seeds:
                self._sources[src.source_id] = src

            # ----------------------------------------------------------
            # Listeners (4)
            # ----------------------------------------------------------
            listener_seeds: List[AcousticListener] = [
                AcousticListener(
                    listener_id="listener_guard_01",
                    name="Tower Guard Alpha",
                    position=(35.0, 5.0, 18.0),
                    hearing_threshold_db=32.0,
                    hearing_range_m=120.0,
                    velocity=(0.0, 0.0, 0.0),
                    active=True,
                    detected_sources=[],
                    metadata={"scene": "demo", "alertness": "normal"},
                ),
                AcousticListener(
                    listener_id="listener_guard_02",
                    name="Tower Guard Bravo",
                    position=(-20.0, 5.0, -10.0),
                    hearing_threshold_db=35.0,
                    hearing_range_m=100.0,
                    velocity=(0.0, 0.0, 0.0),
                    active=True,
                    detected_sources=[],
                    metadata={"scene": "demo", "alertness": "tired"},
                ),
                AcousticListener(
                    listener_id="listener_player",
                    name="Player Character",
                    position=(10.0, 0.0, 5.0),
                    hearing_threshold_db=25.0,
                    hearing_range_m=80.0,
                    velocity=(0.0, 0.0, 0.0),
                    active=True,
                    detected_sources=[],
                    metadata={"scene": "demo", "alertness": "focused"},
                ),
                AcousticListener(
                    listener_id="listener_drone_recon",
                    name="Recon Drone",
                    position=(60.0, 15.0, 30.0),
                    hearing_threshold_db=40.0,
                    hearing_range_m=150.0,
                    velocity=(2.0, 0.0, -1.0),
                    active=True,
                    detected_sources=[],
                    metadata={"scene": "demo", "alertness": "scanning"},
                ),
            ]
            for lst in listener_seeds:
                self._listeners[lst.listener_id] = lst

            # ----------------------------------------------------------
            # Sound Barriers (3)
            # ----------------------------------------------------------
            barrier_seeds: List[SoundBarrier] = [
                SoundBarrier(
                    barrier_id="barrier_concrete_wall",
                    name="Perimeter Concrete Wall",
                    position=(25.0, 1.5, 12.0),
                    dimensions=(12.0, 3.0, 0.4),
                    material=BarrierMaterial.CONCRETE.value,
                    absorption_coefficient=0.03,
                    transmission_loss_db=60.0,
                    active=True,
                    metadata={"scene": "demo"},
                ),
                SoundBarrier(
                    barrier_id="barrier_wooden_fence",
                    name="Warehouse Wooden Fence",
                    position=(-10.0, 1.0, -8.0),
                    dimensions=(8.0, 2.0, 0.2),
                    material=BarrierMaterial.WOOD.value,
                    absorption_coefficient=0.20,
                    transmission_loss_db=25.0,
                    active=True,
                    metadata={"scene": "demo"},
                ),
                SoundBarrier(
                    barrier_id="barrier_metal_container",
                    name="Shipping Container",
                    position=(50.0, 1.5, 22.0),
                    dimensions=(6.0, 2.6, 2.4),
                    material=BarrierMaterial.METAL.value,
                    absorption_coefficient=0.04,
                    transmission_loss_db=45.0,
                    active=True,
                    metadata={"scene": "demo"},
                ),
            ]
            for bar in barrier_seeds:
                self._barriers[bar.barrier_id] = bar

            # ----------------------------------------------------------
            # Echo Zones (3)
            # ----------------------------------------------------------
            echo_zone_seeds: List[EchoZone] = [
                EchoZone(
                    zone_id="echo_warehouse_interior",
                    name="Warehouse Interior",
                    bounds=(-30.0, -20.0, -5.0, 5.0),
                    reflection_coefficient=0.7,
                    reverb_time_s=1.4,
                    active=True,
                    metadata={"scene": "demo"},
                ),
                EchoZone(
                    zone_id="echo_canyon_pass",
                    name="Canyon Pass",
                    bounds=(60.0, 30.0, 120.0, 90.0),
                    reflection_coefficient=0.85,
                    reverb_time_s=2.1,
                    active=True,
                    metadata={"scene": "demo"},
                ),
                EchoZone(
                    zone_id="echo_courtyard",
                    name="Open Courtyard",
                    bounds=(5.0, 5.0, 30.0, 30.0),
                    reflection_coefficient=0.35,
                    reverb_time_s=0.5,
                    active=True,
                    metadata={"scene": "demo"},
                ),
            ]
            for ez in echo_zone_seeds:
                self._echo_zones[ez.zone_id] = ez

            # ----------------------------------------------------------
            # Wavefronts (4)
            # ----------------------------------------------------------
            wavefront_seeds: List[Tuple[str, str, Tuple[float, float, float],
                                         float, float, float, str]] = [
                ("wf_demo_001", "src_footstep_alpha", (10.0, 0.0, 5.0),
                 4.0, 56.0, 180.0, WaveStatus.PROPAGATING.value),
                ("wf_demo_002", "src_guard_voice", (40.0, 0.0, 20.0),
                 12.0, 65.0, 850.0, WaveStatus.PROPAGATING.value),
                ("wf_demo_003", "src_explosion_warehouse", (-25.0, 0.0, -15.0),
                 30.0, 110.0, 60.0, WaveStatus.PROPAGATING.value),
                ("wf_demo_004", "src_machinery_hum", (15.0, 0.0, -30.0),
                 6.0, 62.0, 220.0, WaveStatus.EMITTED.value),
            ]
            for wf_id, src_id, origin, radius, intensity, freq, status in wavefront_seeds:
                self._wavefront_counter += 1
                wf = Wavefront(
                    wavefront_id=wf_id,
                    source_id=src_id,
                    origin=origin,
                    radius_m=radius,
                    intensity_db=intensity,
                    frequency_hz=freq,
                    status=status,
                    emitted_at=self._simulation_time,
                    velocity_mps=self._config.speed_of_sound,
                )
                self._wavefronts[wf_id] = wf

            # ----------------------------------------------------------
            # Events (6)
            # ----------------------------------------------------------
            event_seeds: List[Tuple[str, str, Dict[str, Any]]] = [
                (AcousticEventKind.SOURCE_REGISTERED.value,
                 "Seeded five acoustic sources for the demo scene.",
                 {"count": 5}),
                (AcousticEventKind.LISTENER_REGISTERED.value,
                 "Seeded four acoustic listeners for the demo scene.",
                 {"count": 4}),
                (AcousticEventKind.BARRIER_REGISTERED.value,
                 "Seeded three sound barriers for the demo scene.",
                 {"count": 3}),
                (AcousticEventKind.ECHO_ZONE_REGISTERED.value,
                 "Seeded three echo zones for the demo scene.",
                 {"count": 3}),
                (AcousticEventKind.WAVE_EMITTED.value,
                 "Seeded four initial wavefronts.",
                 {"count": 4}),
                (AcousticEventKind.TICK.value,
                 "Initial acoustic state seeded.",
                 {"simulation_time": 0.0}),
            ]
            for kind, desc, payload in event_seeds:
                self._event_counter += 1
                self._events.append(AcousticEvent(
                    event_id=f"awevt_{self._event_counter:08d}",
                    timestamp=_now(),
                    event_type=kind,
                    description=desc,
                    payload=payload,
                ))
            _evict_fifo_list(self._events, self._config.max_events)

            self._refresh_stats()
            self._seeded = True

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        description: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event to the rolling event log."""
        self._event_counter += 1
        event = AcousticEvent(
            event_id=f"awevt_{self._event_counter:08d}",
            timestamp=_now(),
            event_type=event_type,
            description=description,
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)

    def _refresh_stats(self) -> None:
        """Recompute the cached AcousticStats roll-up from current state."""
        self._stats.total_sources = len(self._sources)
        self._stats.active_sources = sum(
            1 for s in self._sources.values() if s.active
        )
        self._stats.total_listeners = len(self._listeners)
        self._stats.active_listeners = sum(
            1 for l in self._listeners.values() if l.active
        )
        self._stats.total_barriers = len(self._barriers)
        self._stats.active_barriers = sum(
            1 for b in self._barriers.values() if b.active
        )
        self._stats.total_echo_zones = len(self._echo_zones)
        self._stats.active_echo_zones = sum(
            1 for z in self._echo_zones.values() if z.active
        )
        self._stats.active_wavefronts = sum(
            1 for w in self._wavefronts.values()
            if w.status in (
                WaveStatus.EMITTED.value,
                WaveStatus.PROPAGATING.value,
                WaveStatus.REFLECTED.value,
            )
        )
        self._stats.total_propagation_paths = len(self._propagation_paths)
        self._stats.total_doppler_records = len(self._doppler_records)
        self._stats.tick_count = self._tick_count
        peak = 0.0
        for src in self._sources.values():
            if src.active and src.intensity_db > peak:
                peak = src.intensity_db
        for wf in self._wavefronts.values():
            if wf.intensity_db > peak:
                peak = wf.intensity_db
        self._stats.peak_intensity_db = peak
        if self._propagation_distance_count > 0:
            self._stats.avg_propagation_distance_m = (
                self._propagation_distance_accum
                / self._propagation_distance_count
            )

    def _frequency_sensitivity(
        self, listener: AcousticListener, frequency_hz: float
    ) -> float:
        """Look up the listener sensitivity multiplier for a frequency."""
        f = _safe_float(frequency_hz, 0.0)
        for key, mult in listener.frequency_sensitivity.items():
            try:
                low_s, high_s = key.split("-")
                low = float(low_s)
                high = float(high_s)
                if low <= f <= high:
                    return _safe_float(mult, 1.0)
            except (ValueError, AttributeError):
                continue
        return 1.0

    def _directional_attenuation(
        self, source: AcousticSource, listener_position: Tuple[float, float, float]
    ) -> float:
        """Compute the dB attenuation of a directional source toward a point.

        Directional sources emit at full intensity within their spread
        angle and fall off linearly to -20 dB outside it. Omnidirectional
        sources (spread_angle >= 360) suffer no directional loss.
        """
        if not source.directional:
            return 0.0
        if source.spread_angle >= 360.0:
            return 0.0
        to_listener = _vec_sub(listener_position, source.position)
        if _vec_length(to_listener) < _EPSILON:
            return 0.0
        to_listener_n = _vec_normalize(to_listener)
        direction_n = _vec_normalize(source.direction)
        cos_angle = _clamp(_vec_dot(direction_n, to_listener_n), -1.0, 1.0)
        angle_deg = math.degrees(math.acos(cos_angle))
        half_spread = source.spread_angle / 2.0
        if angle_deg <= half_spread:
            return 0.0
        # Linear falloff over 90 degrees past the spread edge, capped at 20 dB.
        excess = angle_deg - half_spread
        falloff = _clamp(excess / 90.0, 0.0, 1.0)
        return -(falloff * 20.0)

    def _barriers_occluding(
        self,
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
    ) -> List[SoundBarrier]:
        """Return all active barriers whose AABB the segment intersects."""
        out: List[SoundBarrier] = []
        for barrier in self._barriers.values():
            if not barrier.active:
                continue
            aabb = _barrier_aabb(barrier.position, barrier.dimensions)
            if _segment_hits_aabb(start, end, aabb):
                out.append(barrier)
        return out

    def _echo_zone_at(
        self, position: Tuple[float, float, float]
    ) -> Optional[EchoZone]:
        """Return the first active echo zone containing a position."""
        for zone in self._echo_zones.values():
            if not zone.active:
                continue
            if _point_in_bounds_2d(position, zone.bounds):
                return zone
        return None

    def _record_propagation_distance(self, distance_m: float) -> None:
        """Accumulate a propagation distance into the rolling average."""
        d = _safe_float(distance_m, 0.0)
        self._propagation_distance_accum += d
        self._propagation_distance_count += 1

    # ------------------------------------------------------------------
    # Source Lifecycle
    # ------------------------------------------------------------------

    def register_source(
        self,
        source_id: str,
        name: str,
        position: Tuple[float, float, float],
        intensity_db: float,
        source_type: str = SourceType.AMBIENT.value,
        frequency_hz: float = 440.0,
        velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        directional: bool = False,
        direction: Tuple[float, float, float] = (1.0, 0.0, 0.0),
        spread_angle: float = 360.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[AcousticSource]]:
        """Register a new acoustic source in the system."""
        with self._lock:
            sid = str(source_id or "").strip()
            if not sid:
                sid = _new_id("src")
            if sid in self._sources:
                return (False, f"Source '{sid}' already exists.",
                        self._sources[sid])
            if len(self._sources) >= self._config.max_sources:
                _evict_fifo_dict(self._sources, self._config.max_sources)
            stype = _coerce_enum(SourceType, source_type, SourceType.AMBIENT)
            stype_val = stype.value if isinstance(stype, SourceType) else SourceType.AMBIENT.value
            source = AcousticSource(
                source_id=sid,
                name=str(name) if name else sid,
                position=_to_vec3(position),
                intensity_db=_safe_float(intensity_db, 60.0),
                frequency_hz=_safe_float(frequency_hz, 440.0),
                source_type=stype_val,
                velocity=_to_vec3(velocity),
                active=True,
                directional=bool(directional),
                direction=_vec_normalize(_to_vec3(direction, (1.0, 0.0, 0.0))),
                spread_angle=_clamp(_safe_float(spread_angle, 360.0), 0.0, 360.0),
                metadata=metadata or {},
            )
            self._sources[sid] = source
            self._emit(
                AcousticEventKind.SOURCE_REGISTERED.value,
                f"Acoustic source '{sid}' registered.",
                {"source_id": sid, "source_type": stype_val,
                 "intensity_db": source.intensity_db},
            )
            self._refresh_stats()
            return (True, f"Source '{sid}' registered.", source)

    def get_source(self, source_id: str) -> Optional[AcousticSource]:
        """Return the source with the given ID, or None."""
        with self._lock:
            return self._sources.get(source_id)

    def remove_source(
        self, source_id: str
    ) -> Tuple[bool, str, Optional[AcousticSource]]:
        """Remove a source from the system."""
        with self._lock:
            sid = str(source_id or "").strip()
            source = self._sources.pop(sid, None)
            if source is None:
                return (False, f"Source '{sid}' not found.", None)
            self._emit(
                AcousticEventKind.SOURCE_REMOVED.value,
                f"Acoustic source '{sid}' removed.",
                {"source_id": sid},
            )
            self._refresh_stats()
            return (True, f"Source '{sid}' removed.", source)

    def list_sources(
        self,
        source_type: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[AcousticSource]:
        """List sources, optionally filtered by type and active state."""
        with self._lock:
            stype = None
            if source_type:
                stype = _coerce_enum(SourceType, source_type, None)
                stype_val = stype.value if isinstance(stype, SourceType) else str(source_type)
            else:
                stype_val = ""
            results: List[AcousticSource] = []
            for src in self._sources.values():
                if stype_val and src.source_type != stype_val:
                    continue
                if active_only and not src.active:
                    continue
                results.append(src)
            return results[:max(0, int(limit))]

    def update_source(
        self,
        source_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[AcousticSource]]:
        """Apply partial updates to an existing source."""
        with self._lock:
            sid = str(source_id or "").strip()
            src = self._sources.get(sid)
            if src is None:
                return (False, f"Source '{sid}' not found.", None)
            if "name" in updates:
                src.name = str(updates["name"])
            if "position" in updates:
                src.position = _to_vec3(updates["position"], src.position)
            if "intensity_db" in updates:
                src.intensity_db = _safe_float(updates["intensity_db"], src.intensity_db)
            if "frequency_hz" in updates:
                src.frequency_hz = _safe_float(updates["frequency_hz"], src.frequency_hz)
            if "source_type" in updates:
                st = _coerce_enum(SourceType, updates["source_type"], None)
                if isinstance(st, SourceType):
                    src.source_type = st.value
            if "velocity" in updates:
                src.velocity = _to_vec3(updates["velocity"], src.velocity)
            if "active" in updates:
                src.active = bool(updates["active"])
            if "directional" in updates:
                src.directional = bool(updates["directional"])
            if "direction" in updates:
                src.direction = _vec_normalize(_to_vec3(updates["direction"], src.direction))
            if "spread_angle" in updates:
                src.spread_angle = _clamp(_safe_float(updates["spread_angle"], src.spread_angle), 0.0, 360.0)
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                src.metadata = dict(updates["metadata"])
            src.updated_at = _now()
            self._emit(
                AcousticEventKind.SOURCE_UPDATED.value,
                f"Acoustic source '{sid}' updated.",
                {"source_id": sid},
            )
            self._refresh_stats()
            return (True, f"Source '{sid}' updated.", src)

    # ------------------------------------------------------------------
    # Listener Lifecycle
    # ------------------------------------------------------------------

    def register_listener(
        self,
        listener_id: str,
        name: str,
        position: Tuple[float, float, float],
        hearing_threshold_db: float = 30.0,
        hearing_range_m: float = 100.0,
        velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        frequency_sensitivity: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[AcousticListener]]:
        """Register a new acoustic listener in the system."""
        with self._lock:
            lid = str(listener_id or "").strip()
            if not lid:
                lid = _new_id("lst")
            if lid in self._listeners:
                return (False, f"Listener '{lid}' already exists.",
                        self._listeners[lid])
            if len(self._listeners) >= self._config.max_listeners:
                _evict_fifo_dict(self._listeners, self._config.max_listeners)
            listener = AcousticListener(
                listener_id=lid,
                name=str(name) if name else lid,
                position=_to_vec3(position),
                hearing_threshold_db=_safe_float(hearing_threshold_db, 30.0),
                hearing_range_m=_safe_float(hearing_range_m, 100.0),
                frequency_sensitivity=frequency_sensitivity or {
                    "0-250": 0.6,
                    "250-2000": 1.0,
                    "2000-8000": 0.9,
                    "8000-20000": 0.5,
                },
                velocity=_to_vec3(velocity),
                active=True,
                detected_sources=[],
                metadata=metadata or {},
            )
            self._listeners[lid] = listener
            self._emit(
                AcousticEventKind.LISTENER_REGISTERED.value,
                f"Acoustic listener '{lid}' registered.",
                {"listener_id": lid,
                 "hearing_range_m": listener.hearing_range_m},
            )
            self._refresh_stats()
            return (True, f"Listener '{lid}' registered.", listener)

    def get_listener(self, listener_id: str) -> Optional[AcousticListener]:
        """Return the listener with the given ID, or None."""
        with self._lock:
            return self._listeners.get(listener_id)

    def remove_listener(
        self, listener_id: str
    ) -> Tuple[bool, str, Optional[AcousticListener]]:
        """Remove a listener from the system."""
        with self._lock:
            lid = str(listener_id or "").strip()
            listener = self._listeners.pop(lid, None)
            if listener is None:
                return (False, f"Listener '{lid}' not found.", None)
            self._emit(
                AcousticEventKind.LISTENER_REMOVED.value,
                f"Acoustic listener '{lid}' removed.",
                {"listener_id": lid},
            )
            self._refresh_stats()
            return (True, f"Listener '{lid}' removed.", listener)

    def list_listeners(
        self,
        active_only: bool = False,
        limit: int = 100,
    ) -> List[AcousticListener]:
        """List listeners, optionally filtered by active state."""
        with self._lock:
            results: List[AcousticListener] = []
            for lst in self._listeners.values():
                if active_only and not lst.active:
                    continue
                results.append(lst)
            return results[:max(0, int(limit))]

    def update_listener(
        self,
        listener_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[AcousticListener]]:
        """Apply partial updates to an existing listener."""
        with self._lock:
            lid = str(listener_id or "").strip()
            lst = self._listeners.get(lid)
            if lst is None:
                return (False, f"Listener '{lid}' not found.", None)
            if "name" in updates:
                lst.name = str(updates["name"])
            if "position" in updates:
                lst.position = _to_vec3(updates["position"], lst.position)
            if "hearing_threshold_db" in updates:
                lst.hearing_threshold_db = _safe_float(
                    updates["hearing_threshold_db"], lst.hearing_threshold_db)
            if "hearing_range_m" in updates:
                lst.hearing_range_m = _safe_float(
                    updates["hearing_range_m"], lst.hearing_range_m)
            if "velocity" in updates:
                lst.velocity = _to_vec3(updates["velocity"], lst.velocity)
            if "active" in updates:
                lst.active = bool(updates["active"])
            if "frequency_sensitivity" in updates and isinstance(
                updates["frequency_sensitivity"], dict
            ):
                lst.frequency_sensitivity = dict(updates["frequency_sensitivity"])
            if "detected_sources" in updates and isinstance(
                updates["detected_sources"], list
            ):
                lst.detected_sources = [str(s) for s in updates["detected_sources"]]
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                lst.metadata = dict(updates["metadata"])
            lst.updated_at = _now()
            self._emit(
                AcousticEventKind.LISTENER_UPDATED.value,
                f"Acoustic listener '{lid}' updated.",
                {"listener_id": lid},
            )
            self._refresh_stats()
            return (True, f"Listener '{lid}' updated.", lst)

    # ------------------------------------------------------------------
    # Barrier Lifecycle
    # ------------------------------------------------------------------

    def register_barrier(
        self,
        barrier_id: str,
        name: str,
        position: Tuple[float, float, float],
        dimensions: Tuple[float, float, float],
        material: str = BarrierMaterial.WOOD.value,
        absorption_coefficient: Optional[float] = None,
        transmission_loss_db: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[SoundBarrier]]:
        """Register a new sound barrier in the system."""
        with self._lock:
            bid = str(barrier_id or "").strip()
            if not bid:
                bid = _new_id("bar")
            if bid in self._barriers:
                return (False, f"Barrier '{bid}' already exists.",
                        self._barriers[bid])
            if len(self._barriers) >= self._config.max_barriers:
                _evict_fifo_dict(self._barriers, self._config.max_barriers)
            mat = _coerce_enum(BarrierMaterial, material, BarrierMaterial.WOOD)
            mat_val = mat.value if isinstance(mat, BarrierMaterial) else BarrierMaterial.WOOD.value
            default_abs, default_tl = _material_defaults(mat_val)
            if absorption_coefficient is None:
                abs_coeff = default_abs
            else:
                abs_coeff = _clamp(_safe_float(absorption_coefficient, default_abs), 0.0, 1.0)
            if transmission_loss_db is None:
                tl = default_tl
            else:
                tl = max(0.0, _safe_float(transmission_loss_db, default_tl))
            barrier = SoundBarrier(
                barrier_id=bid,
                name=str(name) if name else bid,
                position=_to_vec3(position),
                dimensions=_to_vec3(dimensions, (1.0, 2.0, 1.0)),
                material=mat_val,
                absorption_coefficient=abs_coeff,
                transmission_loss_db=tl,
                active=True,
                metadata=metadata or {},
            )
            self._barriers[bid] = barrier
            self._emit(
                AcousticEventKind.BARRIER_REGISTERED.value,
                f"Sound barrier '{bid}' registered.",
                {"barrier_id": bid, "material": mat_val,
                 "transmission_loss_db": tl},
            )
            self._refresh_stats()
            return (True, f"Barrier '{bid}' registered.", barrier)

    def get_barrier(self, barrier_id: str) -> Optional[SoundBarrier]:
        """Return the barrier with the given ID, or None."""
        with self._lock:
            return self._barriers.get(barrier_id)

    def remove_barrier(
        self, barrier_id: str
    ) -> Tuple[bool, str, Optional[SoundBarrier]]:
        """Remove a barrier from the system."""
        with self._lock:
            bid = str(barrier_id or "").strip()
            barrier = self._barriers.pop(bid, None)
            if barrier is None:
                return (False, f"Barrier '{bid}' not found.", None)
            self._emit(
                AcousticEventKind.BARRIER_REMOVED.value,
                f"Sound barrier '{bid}' removed.",
                {"barrier_id": bid},
            )
            self._refresh_stats()
            return (True, f"Barrier '{bid}' removed.", barrier)

    def list_barriers(
        self,
        material: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[SoundBarrier]:
        """List barriers, optionally filtered by material and active state."""
        with self._lock:
            mat_val = ""
            if material:
                mat = _coerce_enum(BarrierMaterial, material, None)
                mat_val = mat.value if isinstance(mat, BarrierMaterial) else str(material)
            results: List[SoundBarrier] = []
            for bar in self._barriers.values():
                if mat_val and bar.material != mat_val:
                    continue
                if active_only and not bar.active:
                    continue
                results.append(bar)
            return results[:max(0, int(limit))]

    def update_barrier(
        self,
        barrier_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[SoundBarrier]]:
        """Apply partial updates to an existing barrier."""
        with self._lock:
            bid = str(barrier_id or "").strip()
            bar = self._barriers.get(bid)
            if bar is None:
                return (False, f"Barrier '{bid}' not found.", None)
            if "name" in updates:
                bar.name = str(updates["name"])
            if "position" in updates:
                bar.position = _to_vec3(updates["position"], bar.position)
            if "dimensions" in updates:
                bar.dimensions = _to_vec3(updates["dimensions"], bar.dimensions)
            if "material" in updates:
                mat = _coerce_enum(BarrierMaterial, updates["material"], None)
                if isinstance(mat, BarrierMaterial):
                    bar.material = mat.value
            if "absorption_coefficient" in updates:
                bar.absorption_coefficient = _clamp(
                    _safe_float(updates["absorption_coefficient"],
                                bar.absorption_coefficient), 0.0, 1.0)
            if "transmission_loss_db" in updates:
                bar.transmission_loss_db = max(
                    0.0, _safe_float(updates["transmission_loss_db"],
                                     bar.transmission_loss_db))
            if "active" in updates:
                bar.active = bool(updates["active"])
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                bar.metadata = dict(updates["metadata"])
            bar.updated_at = _now()
            self._emit(
                AcousticEventKind.BARRIER_UPDATED.value,
                f"Sound barrier '{bid}' updated.",
                {"barrier_id": bid},
            )
            self._refresh_stats()
            return (True, f"Barrier '{bid}' updated.", bar)

    # ------------------------------------------------------------------
    # Echo Zone Lifecycle
    # ------------------------------------------------------------------

    def register_echo_zone(
        self,
        zone_id: str,
        name: str,
        bounds: Tuple[float, float, float, float],
        reflection_coefficient: float = 0.5,
        reverb_time_s: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[EchoZone]]:
        """Register a new echo zone in the system."""
        with self._lock:
            zid = str(zone_id or "").strip()
            if not zid:
                zid = _new_id("echo")
            if zid in self._echo_zones:
                return (False, f"Echo zone '{zid}' already exists.",
                        self._echo_zones[zid])
            if len(self._echo_zones) >= self._config.max_echo_zones:
                _evict_fifo_dict(self._echo_zones, self._config.max_echo_zones)
            b = _to_vec4(bounds, (0.0, 0.0, 10.0, 10.0))
            # Normalize bounds so min < max.
            if b[0] > b[2]:
                b = (b[2], b[1], b[0], b[3])
            if b[1] > b[3]:
                b = (b[0], b[3], b[2], b[1])
            zone = EchoZone(
                zone_id=zid,
                name=str(name) if name else zid,
                bounds=b,
                reflection_coefficient=_clamp(
                    _safe_float(reflection_coefficient, 0.5), 0.0, 1.0),
                reverb_time_s=max(0.0, _safe_float(reverb_time_s, 0.8)),
                active=True,
                metadata=metadata or {},
            )
            self._echo_zones[zid] = zone
            self._emit(
                AcousticEventKind.ECHO_ZONE_REGISTERED.value,
                f"Echo zone '{zid}' registered.",
                {"zone_id": zid,
                 "reverb_time_s": zone.reverb_time_s},
            )
            self._refresh_stats()
            return (True, f"Echo zone '{zid}' registered.", zone)

    def get_echo_zone(self, zone_id: str) -> Optional[EchoZone]:
        """Return the echo zone with the given ID, or None."""
        with self._lock:
            return self._echo_zones.get(zone_id)

    def remove_echo_zone(
        self, zone_id: str
    ) -> Tuple[bool, str, Optional[EchoZone]]:
        """Remove an echo zone from the system."""
        with self._lock:
            zid = str(zone_id or "").strip()
            zone = self._echo_zones.pop(zid, None)
            if zone is None:
                return (False, f"Echo zone '{zid}' not found.", None)
            self._emit(
                AcousticEventKind.ECHO_ZONE_REMOVED.value,
                f"Echo zone '{zid}' removed.",
                {"zone_id": zid},
            )
            self._refresh_stats()
            return (True, f"Echo zone '{zid}' removed.", zone)

    def list_echo_zones(
        self,
        active_only: bool = False,
        limit: int = 100,
    ) -> List[EchoZone]:
        """List echo zones, optionally filtered by active state."""
        with self._lock:
            results: List[EchoZone] = []
            for z in self._echo_zones.values():
                if active_only and not z.active:
                    continue
                results.append(z)
            return results[:max(0, int(limit))]

    def update_echo_zone(
        self,
        zone_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[EchoZone]]:
        """Apply partial updates to an existing echo zone."""
        with self._lock:
            zid = str(zone_id or "").strip()
            zone = self._echo_zones.get(zid)
            if zone is None:
                return (False, f"Echo zone '{zid}' not found.", None)
            if "name" in updates:
                zone.name = str(updates["name"])
            if "bounds" in updates:
                b = _to_vec4(updates["bounds"], zone.bounds)
                if b[0] > b[2]:
                    b = (b[2], b[1], b[0], b[3])
                if b[1] > b[3]:
                    b = (b[0], b[3], b[2], b[1])
                zone.bounds = b
            if "reflection_coefficient" in updates:
                zone.reflection_coefficient = _clamp(
                    _safe_float(updates["reflection_coefficient"],
                                zone.reflection_coefficient), 0.0, 1.0)
            if "reverb_time_s" in updates:
                zone.reverb_time_s = max(
                    0.0, _safe_float(updates["reverb_time_s"],
                                     zone.reverb_time_s))
            if "active" in updates:
                zone.active = bool(updates["active"])
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                zone.metadata = dict(updates["metadata"])
            zone.updated_at = _now()
            self._emit(
                AcousticEventKind.ECHO_ZONE_UPDATED.value,
                f"Echo zone '{zid}' updated.",
                {"zone_id": zid},
            )
            self._refresh_stats()
            return (True, f"Echo zone '{zid}' updated.", zone)

    # ------------------------------------------------------------------
    # Wavefront Lifecycle
    # ------------------------------------------------------------------

    def emit_wave(
        self,
        source_id: str,
        intensity_db: Optional[float] = None,
        frequency_hz: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[Wavefront]]:
        """Emit a new spherical wavefront from a registered source."""
        with self._lock:
            sid = str(source_id or "").strip()
            src = self._sources.get(sid)
            if src is None:
                return (False, f"Source '{sid}' not found.", None)
            if not src.active:
                return (False, f"Source '{sid}' is inactive.", None)
            if len(self._wavefronts) >= self._config.max_wavefronts:
                _evict_fifo_dict(self._wavefronts, self._config.max_wavefronts)
            self._wavefront_counter += 1
            wf_id = f"wf_{self._wavefront_counter:08d}"
            intensity = src.intensity_db if intensity_db is None else _safe_float(intensity_db, src.intensity_db)
            freq = src.frequency_hz if frequency_hz is None else _safe_float(frequency_hz, src.frequency_hz)
            wf = Wavefront(
                wavefront_id=wf_id,
                source_id=sid,
                origin=src.position,
                radius_m=0.0,
                intensity_db=intensity,
                frequency_hz=freq,
                status=WaveStatus.EMITTED.value,
                emitted_at=self._simulation_time,
                velocity_mps=self._config.speed_of_sound,
                metadata={"source_type": src.source_type},
            )
            self._wavefronts[wf_id] = wf
            self._stats.total_wavefronts_emitted += 1
            self._emit(
                AcousticEventKind.WAVE_EMITTED.value,
                f"Wavefront '{wf_id}' emitted from source '{sid}'.",
                {"wavefront_id": wf_id, "source_id": sid,
                 "intensity_db": intensity},
            )
            self._refresh_stats()
            return (True, f"Wavefront '{wf_id}' emitted.", wf)

    def get_wavefront(self, wavefront_id: str) -> Optional[Wavefront]:
        """Return the wavefront with the given ID, or None."""
        with self._lock:
            return self._wavefronts.get(wavefront_id)

    def list_wavefronts(
        self,
        status: str = "",
        limit: int = 100,
    ) -> List[Wavefront]:
        """List wavefronts, optionally filtered by status."""
        with self._lock:
            status_val = ""
            if status:
                st = _coerce_enum(WaveStatus, status, None)
                status_val = st.value if isinstance(st, WaveStatus) else str(status)
            results: List[Wavefront] = []
            for wf in self._wavefronts.values():
                if status_val and wf.status != status_val:
                    continue
                results.append(wf)
            return results[:max(0, int(limit))]

    def clear_wavefronts(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Remove all wavefronts from the system."""
        with self._lock:
            count = len(self._wavefronts)
            self._wavefronts.clear()
            self._emit(
                AcousticEventKind.WAVE_FADED.value,
                f"Cleared {count} wavefronts.",
                {"cleared": count},
            )
            self._refresh_stats()
            return (True, f"Cleared {count} wavefronts.",
                    {"cleared": count})

    # ------------------------------------------------------------------
    # Propagation, Attenuation, Doppler
    # ------------------------------------------------------------------

    def compute_propagation(
        self,
        source_id: str,
        listener_id: str,
    ) -> Tuple[bool, str, Optional[PropagationPath]]:
        """Compute the propagation path from a source to a listener.

        The path follows the direct line of sight and accounts for
        geometric spreading, air absorption, directional source shaping,
        barrier transmission loss, and echo-zone reverberation. Returns
        a :class:`PropagationPath` describing the segments traveled and
        the total attenuation in decibels.
        """
        with self._lock:
            sid = str(source_id or "").strip()
            lid = str(listener_id or "").strip()
            src = self._sources.get(sid)
            lst = self._listeners.get(lid)
            if src is None:
                return (False, f"Source '{sid}' not found.", None)
            if lst is None:
                return (False, f"Listener '{lid}' not found.", None)
            if not src.active:
                return (False, f"Source '{sid}' is inactive.", None)
            if not lst.active:
                return (False, f"Listener '{lid}' is inactive.", None)

            distance = _vec_distance(src.position, lst.position)
            if distance < _EPSILON:
                distance = _EPSILON
            # Geometric spreading attenuation from 1 m reference.
            spread_db = _spreading_attenuation(distance, self._config.reference_distance_m)
            # Directional shaping.
            dir_db = self._directional_attenuation(src, lst.position)
            # Air absorption.
            air_db = 0.0
            if self._config.enable_air_absorption:
                air_db = _air_absorption_db(distance, src.frequency_hz)
            # Barrier transmission loss along the line of sight.
            barriers_hit = self._barriers_occluding(src.position, lst.position)
            barrier_loss_db = sum(b.transmission_loss_db for b in barriers_hit)
            # Frequency sensitivity of the listener.
            sensitivity = self._frequency_sensitivity(lst, src.frequency_hz)
            # Sensitivity > 1 boosts; < 1 attenuates. Convert to dB.
            sensitivity_db = 0.0
            if sensitivity > 0.0:
                sensitivity_db = 10.0 * math.log10(sensitivity)
            total_attenuation = (spread_db + air_db + abs(dir_db) * -1.0
                                 + barrier_loss_db - sensitivity_db)
            if dir_db < 0.0:
                total_attenuation = spread_db + air_db + (-dir_db) + barrier_loss_db - sensitivity_db
            else:
                total_attenuation = spread_db + air_db + barrier_loss_db - sensitivity_db

            segments: List[Tuple[Tuple[float, float, float],
                                 Tuple[float, float, float], str]] = []
            cursor = src.position
            # If barriers are present, split the path into per-barrier legs.
            if barriers_hit:
                for b in barriers_hit:
                    aabb = _barrier_aabb(b.position, b.dimensions)
                    # Approximate exit point as the midpoint of the AABB.
                    mid = ((aabb[0] + aabb[3]) / 2.0,
                           (aabb[1] + aabb[4]) / 2.0,
                           (aabb[2] + aabb[5]) / 2.0)
                    segments.append((cursor, mid, f"air"))
                    segments.append((mid, mid, f"barrier:{b.material}"))
                    cursor = mid
                segments.append((cursor, lst.position, "air"))
            else:
                segments.append((cursor, lst.position, "air"))

            # Echo zone overlay: if either endpoint sits inside an echo
            # zone, mark the path as reflected and add reverb.
            zone = self._echo_zone_at(lst.position) or self._echo_zone_at(src.position)
            reflection_count = 0
            path_type = PathType.DIRECT.value
            if zone is not None and self._config.enable_reflections:
                reflection_count = 1
                path_type = PathType.REFLECTED.value
                # Add a small reflection leg.
                segments.append((lst.position, lst.position, f"echo:{zone.zone_id}"))
                # Reverberation adds a fixed energy cost derived from T60.
                reverb_penalty = _clamp(zone.reverb_time_s * 3.0, 0.0, 30.0)
                total_attenuation += reverb_penalty

            occluded = bool(barriers_hit) and barrier_loss_db > 0.0
            if occluded:
                path_type = PathType.TRANSMITTED.value

            self._path_counter += 1
            path_id = f"path_{self._path_counter:08d}"
            path = PropagationPath(
                path_id=path_id,
                source_id=sid,
                listener_id=lid,
                segments=segments,
                total_distance_m=distance,
                total_attenuation_db=total_attenuation,
                reflection_count=reflection_count,
                occluded=occluded,
                path_type=path_type,
                metadata={
                    "spread_db": spread_db,
                    "air_db": air_db,
                    "directional_db": dir_db,
                    "barrier_loss_db": barrier_loss_db,
                    "sensitivity_db": sensitivity_db,
                    "barriers_hit": [b.barrier_id for b in barriers_hit],
                    "echo_zone": zone.zone_id if zone else "",
                },
            )
            if len(self._propagation_paths) >= self._config.max_propagation_paths:
                _evict_fifo_dict(self._propagation_paths, self._config.max_propagation_paths)
            self._propagation_paths[path_id] = path
            self._record_propagation_distance(distance)
            self._emit(
                AcousticEventKind.PROPAGATION_COMPUTED.value,
                f"Propagation path '{path_id}' computed.",
                {"path_id": path_id, "source_id": sid, "listener_id": lid,
                 "distance_m": distance, "attenuation_db": total_attenuation,
                 "occluded": occluded},
            )
            self._refresh_stats()
            return (True, f"Path '{path_id}' computed.", path)

    def compute_attenuation(
        self,
        distance_m: float,
        frequency_hz: float,
        medium: str = "air",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the attenuation of a sound over a distance.

        Returns a dictionary with the geometric spreading loss, the air
        (or barrier) absorption, and the total attenuation in decibels.
        The ``medium`` argument selects between "air" and barrier
        materials such as "wood", "stone", or "concrete".
        """
        with self._lock:
            d = max(0.0, _safe_float(distance_m, 0.0))
            f = _safe_float(frequency_hz, 0.0)
            medium_key = str(medium or "air").strip().lower()
            spread_db = _spreading_attenuation(d, self._config.reference_distance_m)
            if medium_key == "air" or medium_key == "":
                abs_db = _air_absorption_db(d, f) if self._config.enable_air_absorption else 0.0
                transmission_loss = 0.0
            else:
                mat = _coerce_enum(BarrierMaterial, medium_key, None)
                mat_val = mat.value if isinstance(mat, BarrierMaterial) else medium_key
                default_abs, default_tl = _material_defaults(mat_val)
                abs_db = default_abs * d * 10.0  # rough scaling for gameplay
                transmission_loss = default_tl
            total_db = spread_db + abs_db + transmission_loss
            result = {
                "distance_m": d,
                "frequency_hz": f,
                "medium": medium_key,
                "spreading_db": spread_db,
                "absorption_db": abs_db,
                "transmission_loss_db": transmission_loss,
                "total_attenuation_db": total_db,
                "remaining_intensity_factor": 10.0 ** (-total_db / 20.0),
            }
            return (True, "Attenuation computed.", result)

    def compute_doppler(
        self,
        source_id: str,
        listener_id: str,
    ) -> Tuple[bool, str, Optional[DopplerShift]]:
        """Compute the Doppler frequency shift between source and listener."""
        with self._lock:
            sid = str(source_id or "").strip()
            lid = str(listener_id or "").strip()
            src = self._sources.get(sid)
            lst = self._listeners.get(lid)
            if src is None:
                return (False, f"Source '{sid}' not found.", None)
            if lst is None:
                return (False, f"Listener '{lid}' not found.", None)
            if src.frequency_hz <= 0.0:
                return (False, "Source frequency is zero.", None)
            shifted, closing = _doppler_shift(
                src.velocity, lst.velocity, src.position, lst.position,
                src.frequency_hz,
            )
            shift_factor = shifted / src.frequency_hz if src.frequency_hz > 0 else 1.0
            self._doppler_counter += 1
            did = f"dop_{self._doppler_counter:08d}"
            record = DopplerShift(
                doppler_id=did,
                source_id=sid,
                listener_id=lid,
                original_frequency_hz=src.frequency_hz,
                shifted_frequency_hz=shifted,
                relative_velocity_ms=closing,
                shift_factor=shift_factor,
                metadata={
                    "source_velocity": list(src.velocity),
                    "listener_velocity": list(lst.velocity),
                    "approaching": closing > 0.0,
                },
            )
            if len(self._doppler_records) >= self._config.max_doppler_records:
                _evict_fifo_dict(self._doppler_records, self._config.max_doppler_records)
            self._doppler_records[did] = record
            self._emit(
                AcousticEventKind.DOPPLER_COMPUTED.value,
                f"Doppler shift '{did}' computed.",
                {"doppler_id": did, "source_id": sid, "listener_id": lid,
                 "original_hz": src.frequency_hz, "shifted_hz": shifted,
                 "closing_ms": closing},
            )
            self._refresh_stats()
            return (True, f"Doppler shift '{did}' computed.", record)

    # ------------------------------------------------------------------
    # Hearing, Occlusion, Reflections
    # ------------------------------------------------------------------

    def check_hearing(
        self,
        listener_id: str,
        source_id: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Determine whether a listener can hear a source.

        Returns a dictionary with the perceived intensity at the
        listener's position, the listener threshold, the distance, and a
        boolean ``heard`` flag. The perceived intensity is the source
        intensity minus the computed propagation attenuation, plus the
        ambient floor.
        """
        with self._lock:
            lid = str(listener_id or "").strip()
            sid = str(source_id or "").strip()
            lst = self._listeners.get(lid)
            src = self._sources.get(sid)
            if lst is None:
                return (False, f"Listener '{lid}' not found.", {})
            if src is None:
                return (False, f"Source '{sid}' not found.", {})
            if not lst.active or not src.active:
                return (True, "Inactive participant.", {
                    "heard": False, "reason": "inactive",
                    "listener_id": lid, "source_id": sid,
                    "perceived_db": 0.0,
                    "threshold_db": lst.hearing_threshold_db,
                })
            distance = _vec_distance(lst.position, src.position)
            if distance > lst.hearing_range_m:
                # Out of range: not heard.
                perceived = self._config.ambient_db
                heard = False
                reason = "out_of_range"
            else:
                ok, _, path = self.compute_propagation(sid, lid)
                if not ok or path is None:
                    return (False, "Propagation computation failed.", {})
                perceived = src.intensity_db - path.total_attenuation_db
                # Apply directional loss explicitly (already in path).
                heard = perceived >= lst.hearing_threshold_db
                reason = "heard" if heard else "below_threshold"
            # Update detected_sources list if heard.
            if heard and sid not in lst.detected_sources:
                lst.detected_sources.append(sid)
            elif not heard and sid in lst.detected_sources:
                lst.detected_sources.remove(sid)
            self._stats.total_hearing_checks += 1
            self._emit(
                AcousticEventKind.HEARING_CHECK.value,
                f"Hearing check: listener '{lid}' vs source '{sid}'.",
                {"listener_id": lid, "source_id": sid,
                 "heard": heard, "perceived_db": perceived,
                 "threshold_db": lst.hearing_threshold_db,
                 "distance_m": distance},
            )
            return (True, reason, {
                "heard": heard,
                "reason": reason,
                "listener_id": lid,
                "source_id": sid,
                "distance_m": distance,
                "perceived_db": perceived,
                "threshold_db": lst.hearing_threshold_db,
                "source_intensity_db": src.intensity_db,
            })

    def get_audible_sources(
        self,
        listener_id: str,
    ) -> List[Dict[str, Any]]:
        """Return all sources the listener can currently hear."""
        with self._lock:
            lid = str(listener_id or "").strip()
            lst = self._listeners.get(lid)
            if lst is None:
                return []
            audible: List[Dict[str, Any]] = []
            for src in list(self._sources.values()):
                if not src.active:
                    continue
                ok, _, info = self.check_hearing(lid, src.source_id)
                if ok and info.get("heard"):
                    audible.append(info)
            # Sort by perceived intensity, loudest first.
            audible.sort(key=lambda d: _safe_float(d.get("perceived_db"), 0.0),
                         reverse=True)
            return audible

    def compute_sound_level(
        self,
        position: Tuple[float, float, float],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the total sound level at a point in space.

        Sums the linear intensities of all active sources (after
        attenuation) and converts back to decibels. Includes the
        ambient floor so that quiet positions are not negative.
        """
        with self._lock:
            pos = _to_vec3(position)
            total_linear = _db_to_linear(self._config.ambient_db)
            contributing: List[Dict[str, Any]] = []
            for src in self._sources.values():
                if not src.active:
                    continue
                distance = _vec_distance(pos, src.position)
                if distance < _EPSILON:
                    distance = self._config.reference_distance_m
                spread_db = _spreading_attenuation(distance, self._config.reference_distance_m)
                air_db = 0.0
                if self._config.enable_air_absorption:
                    air_db = _air_absorption_db(distance, src.frequency_hz)
                dir_db = self._directional_attenuation(src, pos)
                perceived_db = src.intensity_db - spread_db - air_db + dir_db
                # Add barrier loss for the line of sight.
                barriers_hit = self._barriers_occluding(src.position, pos)
                barrier_loss = sum(b.transmission_loss_db for b in barriers_hit)
                perceived_db -= barrier_loss
                if perceived_db > self._config.ambient_db:
                    total_linear += _db_to_linear(perceived_db)
                    contributing.append({
                        "source_id": src.source_id,
                        "perceived_db": perceived_db,
                        "distance_m": distance,
                    })
            total_db = _linear_to_db(total_linear)
            # Sound pressure estimate from the SPL.
            pressure = _spl_to_pressure(total_db)
            return (True, "Sound level computed.", {
                "position": list(pos),
                "total_db": total_db,
                "ambient_db": self._config.ambient_db,
                "pressure_pa": pressure,
                "contributing_sources": contributing,
                "source_count": len(contributing),
            })

    def check_occlusion(
        self,
        source_id: str,
        listener_id: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Check whether the line of sight between source and listener
        is occluded by any active barriers."""
        with self._lock:
            sid = str(source_id or "").strip()
            lid = str(listener_id or "").strip()
            src = self._sources.get(sid)
            lst = self._listeners.get(lid)
            if src is None:
                return (False, f"Source '{sid}' not found.", {})
            if lst is None:
                return (False, f"Listener '{lid}' not found.", {})
            barriers_hit = self._barriers_occluding(src.position, lst.position)
            total_loss = sum(b.transmission_loss_db for b in barriers_hit)
            occluded = len(barriers_hit) > 0 and total_loss > 0.0
            self._stats.total_occlusion_checks += 1
            self._emit(
                AcousticEventKind.OCCLUSION_CHECK.value,
                f"Occlusion check: source '{sid}' vs listener '{lid}'.",
                {"source_id": sid, "listener_id": lid,
                 "occluded": occluded,
                 "barrier_count": len(barriers_hit),
                 "total_loss_db": total_loss},
            )
            return (True, "occluded" if occluded else "clear", {
                "source_id": sid,
                "listener_id": lid,
                "occluded": occluded,
                "barriers": [
                    {"barrier_id": b.barrier_id,
                     "material": b.material,
                     "transmission_loss_db": b.transmission_loss_db}
                    for b in barriers_hit
                ],
                "total_loss_db": total_loss,
            })

    def find_reflection_path(
        self,
        source_id: str,
        listener_id: str,
    ) -> Tuple[bool, str, Optional[PropagationPath]]:
        """Find a reflection path via an echo zone, if one exists.

        Uses a simple mirror-image model: if the listener sits inside an
        echo zone, the path is treated as reflected with the zone's
        reflection coefficient applied. Returns a :class:`PropagationPath`
        with path_type REFLECTED, or None if no echo zone is reachable.
        """
        with self._lock:
            sid = str(source_id or "").strip()
            lid = str(listener_id or "").strip()
            src = self._sources.get(sid)
            lst = self._listeners.get(lid)
            if src is None:
                return (False, f"Source '{sid}' not found.", None)
            if lst is None:
                return (False, f"Listener '{lid}' not found.", None)
            if not self._config.enable_reflections:
                return (False, "Reflections are disabled in config.", None)
            zone = self._echo_zone_at(lst.position) or self._echo_zone_at(src.position)
            if zone is None:
                # No echo zone overlay: no reflection path.
                return (True, "No echo zone available.", None)
            distance = _vec_distance(src.position, lst.position)
            spread_db = _spreading_attenuation(distance, self._config.reference_distance_m)
            reflection_db = -10.0 * math.log10(max(_EPSILON, zone.reflection_coefficient))
            reverb_penalty = _clamp(zone.reverb_time_s * 3.0, 0.0, 30.0)
            total_attenuation = spread_db + reflection_db + reverb_penalty
            self._path_counter += 1
            pid = f"refl_{self._path_counter:08d}"
            path = PropagationPath(
                path_id=pid,
                source_id=sid,
                listener_id=lid,
                segments=[
                    (src.position, lst.position, "air"),
                    (lst.position, lst.position, f"echo:{zone.zone_id}"),
                ],
                total_distance_m=distance,
                total_attenuation_db=total_attenuation,
                reflection_count=1,
                occluded=False,
                path_type=PathType.REFLECTED.value,
                metadata={
                    "echo_zone": zone.zone_id,
                    "reflection_coefficient": zone.reflection_coefficient,
                    "reflection_db": reflection_db,
                    "reverb_time_s": zone.reverb_time_s,
                },
            )
            if len(self._propagation_paths) >= self._config.max_propagation_paths:
                _evict_fifo_dict(self._propagation_paths, self._config.max_propagation_paths)
            self._propagation_paths[pid] = path
            self._stats.total_reflections_found += 1
            self._emit(
                AcousticEventKind.REFLECTION_FOUND.value,
                f"Reflection path '{pid}' found via zone '{zone.zone_id}'.",
                {"path_id": pid, "source_id": sid, "listener_id": lid,
                 "echo_zone": zone.zone_id},
            )
            self._refresh_stats()
            return (True, f"Reflection path '{pid}' found.", path)

    def list_propagation_paths(
        self,
        source_id: str = "",
        listener_id: str = "",
        path_type: str = "",
        limit: int = 100,
    ) -> List[PropagationPath]:
        """Return stored propagation paths, optionally filtered.

        Filters by source ID, listener ID, and/or path type. The most
        recently computed paths are returned first.
        """
        with self._lock:
            ptype_val = ""
            if path_type:
                pt = _coerce_enum(PathType, path_type, None)
                ptype_val = pt.value if isinstance(pt, PathType) else str(path_type)
            sid = str(source_id or "").strip()
            lid = str(listener_id or "").strip()
            results: List[PropagationPath] = []
            for path in reversed(list(self._propagation_paths.values())):
                if sid and path.source_id != sid:
                    continue
                if lid and path.listener_id != lid:
                    continue
                if ptype_val and path.path_type != ptype_val:
                    continue
                results.append(path)
                if len(results) >= max(0, int(limit)):
                    break
            return results

    # ------------------------------------------------------------------
    # Sound Map and Visualization
    # ------------------------------------------------------------------

    def get_sound_map(
        self,
        resolution: int = 16,
    ) -> Dict[str, Any]:
        """Build a 2D grid of sound levels over the scene bounds.

        The grid spans the bounding box of all registered sources. Each
        cell holds the total sound level in decibels at its center. The
        resolution is clamped to keep the cell count under
        _MAX_SOUND_MAP_CELLS.
        """
        with self._lock:
            n = max(4, _safe_int(resolution, self._config.sound_map_resolution))
            n = min(n, int(math.sqrt(_MAX_SOUND_MAP_CELLS)))
            if not self._sources:
                return {
                    "resolution": n,
                    "bounds": [0.0, 0.0, 10.0, 10.0],
                    "grid": [[self._config.ambient_db for _ in range(n)]
                             for _ in range(n)],
                    "max_db": self._config.ambient_db,
                    "min_db": self._config.ambient_db,
                }
            xs = [s.position[0] for s in self._sources.values()]
            zs = [s.position[2] for s in self._sources.values()]
            min_x = min(xs) - 5.0
            max_x = max(xs) + 5.0
            min_z = min(zs) - 5.0
            max_z = max(zs) + 5.0
            if max_x - min_x < _EPSILON:
                max_x = min_x + 10.0
            if max_z - min_z < _EPSILON:
                max_z = min_z + 10.0
            span_x = max_x - min_x
            span_z = max_z - min_z
            grid: List[List[float]] = []
            cell_db_max = self._config.ambient_db
            cell_db_min = self._config.ambient_db
            for rz in range(n):
                row: List[float] = []
                z = min_z + (rz + 0.5) / n * span_z
                for rx in range(n):
                    x = min_x + (rx + 0.5) / n * span_x
                    ok, _, info = self.compute_sound_level((x, 0.0, z))
                    if ok:
                        db = _safe_float(info.get("total_db"), self._config.ambient_db)
                    else:
                        db = self._config.ambient_db
                    row.append(db)
                    if db > cell_db_max:
                        cell_db_max = db
                    if db < cell_db_min:
                        cell_db_min = db
                grid.append(row)
            self._stats.total_sound_maps += 1
            self._emit(
                AcousticEventKind.SOUND_MAP_GENERATED.value,
                f"Sound map generated at resolution {n}.",
                {"resolution": n, "bounds": [min_x, min_z, max_x, max_z]},
            )
            return {
                "resolution": n,
                "bounds": [min_x, min_z, max_x, max_z],
                "grid": grid,
                "max_db": cell_db_max,
                "min_db": cell_db_min,
            }

    def get_visualization_data(
        self,
        zone_id: str = "",
    ) -> Dict[str, Any]:
        """Return a compact visualization payload for the acoustic scene.

        Includes active sources, listeners, barriers, echo zones, and
        propagating wavefronts. When ``zone_id`` is provided, the
        payload is filtered to entities inside that echo zone.
        """
        with self._lock:
            zone: Optional[EchoZone] = None
            if zone_id:
                zone = self._echo_zones.get(str(zone_id).strip())
            sources: List[Dict[str, Any]] = []
            for src in self._sources.values():
                if zone is not None and not _point_in_bounds_2d(src.position, zone.bounds):
                    continue
                sources.append(src.to_dict())
            listeners: List[Dict[str, Any]] = []
            for lst in self._listeners.values():
                if zone is not None and not _point_in_bounds_2d(lst.position, zone.bounds):
                    continue
                listeners.append(lst.to_dict())
            barriers: List[Dict[str, Any]] = []
            for b in self._barriers.values():
                if zone is not None and not _point_in_bounds_2d(b.position, zone.bounds):
                    continue
                barriers.append(b.to_dict())
            echo_zones: List[Dict[str, Any]] = [z.to_dict() for z in self._echo_zones.values()]
            wavefronts: List[Dict[str, Any]] = []
            for wf in self._wavefronts.values():
                if zone is not None and not _point_in_bounds_2d(wf.origin, zone.bounds):
                    continue
                wavefronts.append(wf.to_dict())
            return {
                "zone_id": zone.zone_id if zone else "",
                "sources": sources,
                "listeners": listeners,
                "barriers": barriers,
                "echo_zones": echo_zones,
                "wavefronts": wavefronts,
                "timestamp": _now(),
            }

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def ai_predict_detection(
        self,
        source_id: str,
        listener_id: str,
        time_horizon: float = 1.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Predict the probability that a listener detects a source.

        Combines the current perceived intensity, the listener threshold,
        and a time-horizon factor: longer horizons raise detection odds
        because the listener has more chances to notice the source. The
        model is intentionally simple so it runs every frame.
        """
        with self._lock:
            sid = str(source_id or "").strip()
            lid = str(listener_id or "").strip()
            ok, _, hearing = self.check_hearing(lid, sid)
            if not ok:
                return (False, "Hearing check failed.", {})
            horizon = _clamp(_safe_float(time_horizon, 1.0), 0.0, 60.0)
            perceived = _safe_float(hearing.get("perceived_db"), 0.0)
            threshold = _safe_float(hearing.get("threshold_db"), 30.0)
            distance = _safe_float(hearing.get("distance_m"), 0.0)
            heard_now = bool(hearing.get("heard", False))
            # Probability grows with the dB margin above threshold and
            # with the time horizon. Use a logistic curve.
            margin = perceived - threshold
            time_factor = 1.0 - math.exp(-horizon)
            if margin <= 0.0:
                # Below threshold: detection only via cumulative exposure.
                probability = 0.05 * time_factor * max(0.0, 1.0 + margin / 20.0)
            else:
                probability = 1.0 / (1.0 + math.exp(-0.3 * margin)) * time_factor
            probability = _clamp(probability, 0.0, 1.0)
            label = _detection_label(probability)
            self._stats.total_ai_assessments += 1
            self._emit(
                AcousticEventKind.AI_ASSESSMENT.value,
                f"AI detection prediction: {label} ({probability:.2f}).",
                {"source_id": sid, "listener_id": lid,
                 "probability": probability, "label": label,
                 "time_horizon_s": horizon, "heard_now": heard_now},
            )
            return (True, label, {
                "source_id": sid,
                "listener_id": lid,
                "heard_now": heard_now,
                "perceived_db": perceived,
                "threshold_db": threshold,
                "distance_m": distance,
                "time_horizon_s": horizon,
                "probability": probability,
                "label": label,
            })

    def ai_optimize_barrier_placement(
        self,
        listener_id: str,
        threat_source_ids: List[str],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Suggest barrier placements to shield a listener from threats.

        For each threat, the helper computes the midpoint along the line
        of sight and recommends a barrier there. Returns one suggestion
        per threat with the proposed position, material, and the
        estimated reduction in perceived intensity.
        """
        with self._lock:
            lid = str(listener_id or "").strip()
            lst = self._listeners.get(lid)
            if lst is None:
                return (False, f"Listener '{lid}' not found.", {})
            suggestions: List[Dict[str, Any]] = []
            for sid in threat_source_ids or []:
                src = self._sources.get(str(sid).strip())
                if src is None:
                    continue
                midpoint = (
                    (src.position[0] + lst.position[0]) / 2.0,
                    (src.position[1] + lst.position[1]) / 2.0,
                    (src.position[2] + lst.position[2]) / 2.0,
                )
                # Before placement: current perceived intensity.
                ok_before, _, before = self.check_hearing(lid, src.source_id)
                perceived_before = _safe_float(before.get("perceived_db"), 0.0) if ok_before else 0.0
                # Estimate the reduction using a concrete barrier.
                _, default_tl = _material_defaults(BarrierMaterial.CONCRETE.value)
                estimated_after = perceived_before - default_tl
                # Re-evaluate with a hypothetical barrier in place.
                temp_id = f"barrier_opt_{src.source_id}"
                existed = self._barriers.get(temp_id)
                self._barriers[temp_id] = SoundBarrier(
                    barrier_id=temp_id,
                    name="Optimization Barrier",
                    position=midpoint,
                    dimensions=(2.0, 3.0, 0.5),
                    material=BarrierMaterial.CONCRETE.value,
                    absorption_coefficient=0.03,
                    transmission_loss_db=default_tl,
                    active=True,
                )
                try:
                    ok_after, _, after = self.check_hearing(lid, src.source_id)
                    perceived_after = _safe_float(after.get("perceived_db"), 0.0) if ok_after else 0.0
                    heard_after = bool(after.get("heard", False)) if ok_after else False
                finally:
                    # Restore previous barrier state.
                    if existed is None:
                        self._barriers.pop(temp_id, None)
                    else:
                        self._barriers[temp_id] = existed
                reduction = perceived_before - perceived_after
                suggestions.append({
                    "source_id": src.source_id,
                    "listener_id": lid,
                    "proposed_position": list(midpoint),
                    "recommended_material": BarrierMaterial.CONCRETE.value,
                    "estimated_transmission_loss_db": default_tl,
                    "perceived_before_db": perceived_before,
                    "perceived_after_db": perceived_after,
                    "reduction_db": reduction,
                    "still_heard": heard_after,
                })
            self._stats.total_ai_assessments += 1
            self._emit(
                AcousticEventKind.AI_ASSESSMENT.value,
                f"AI barrier optimization: {len(suggestions)} suggestions.",
                {"listener_id": lid, "suggestion_count": len(suggestions)},
            )
            return (True, f"{len(suggestions)} suggestions.", {
                "listener_id": lid,
                "suggestions": suggestions,
                "suggestion_count": len(suggestions),
            })

    def ai_assess_stealth(
        self,
        listener_id: str,
        source_ids: List[str],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Assess the stealth exposure of a listener against a set of
        sources. Returns a stealth score in [0, 1] where higher means
        more exposed, plus per-source details."""
        with self._lock:
            lid = str(listener_id or "").strip()
            lst = self._listeners.get(lid)
            if lst is None:
                return (False, f"Listener '{lid}' not found.", {})
            details: List[Dict[str, Any]] = []
            worst_score = 0.0
            for sid in source_ids or []:
                src = self._sources.get(str(sid).strip())
                if src is None:
                    continue
                ok, _, info = self.check_hearing(lid, src.source_id)
                if not ok:
                    continue
                perceived = _safe_float(info.get("perceived_db"), 0.0)
                threshold = _safe_float(info.get("threshold_db"), 30.0)
                heard = bool(info.get("heard", False))
                # Score: how far above threshold, normalized to [0, 1].
                margin = perceived - threshold
                score = 1.0 / (1.0 + math.exp(-0.2 * margin))
                score = _clamp(score, 0.0, 1.0)
                if heard:
                    score = max(score, 0.5)
                if score > worst_score:
                    worst_score = score
                details.append({
                    "source_id": src.source_id,
                    "heard": heard,
                    "perceived_db": perceived,
                    "threshold_db": threshold,
                    "margin_db": margin,
                    "score": score,
                })
            label = _stealth_label(worst_score)
            self._stats.total_ai_assessments += 1
            self._emit(
                AcousticEventKind.AI_ASSESSMENT.value,
                f"AI stealth assessment: {label} ({worst_score:.2f}).",
                {"listener_id": lid, "stealth_score": worst_score,
                 "label": label, "source_count": len(details)},
            )
            return (True, label, {
                "listener_id": lid,
                "stealth_score": worst_score,
                "label": label,
                "details": details,
                "exposed_count": sum(1 for d in details if d["heard"]),
            })

    # ------------------------------------------------------------------
    # Reset, Events, Tick
    # ------------------------------------------------------------------

    def reset_sources(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Reset all sources: deactivate every registered source and
        clear detected-source lists on listeners."""
        with self._lock:
            count = 0
            for src in self._sources.values():
                src.active = False
                src.updated_at = _now()
                count += 1
            for lst in self._listeners.values():
                lst.detected_sources = []
                lst.updated_at = _now()
            self._emit(
                AcousticEventKind.SOURCES_RESET.value,
                f"Reset {count} sources.",
                {"count": count},
            )
            self._refresh_stats()
            return (True, f"Reset {count} sources.", {"count": count})

    def list_events(
        self,
        kind: str = "",
        limit: int = 50,
    ) -> List[AcousticEvent]:
        """Return recent audit events, optionally filtered by kind."""
        with self._lock:
            kind_val = ""
            if kind:
                ke = _coerce_enum(AcousticEventKind, kind, None)
                kind_val = ke.value if isinstance(ke, AcousticEventKind) else str(kind)
            results: List[AcousticEvent] = []
            for e in reversed(self._events):
                if kind_val and e.event_type != kind_val:
                    continue
                results.append(e)
                if len(results) >= max(1, int(limit)):
                    break
            return results

    def tick(self, dt: float = 0.016) -> Tuple[bool, str, Dict[str, Any]]:
        """Advance the simulation by dt seconds.

        Expands each propagating wavefront by ``speed_of_sound * dt``,
        fades wavefronts whose intensity drops below the configured
        floor, and updates wavefront statuses. Also records a TICK event
        for observability.
        """
        with self._lock:
            delta = max(0.0, _safe_float(dt, 0.016))
            self._simulation_time += delta
            self._tick_count += 1
            faded_count = 0
            absorbed_count = 0
            for wf in self._wavefronts.values():
                if wf.status in (WaveStatus.FADED.value, WaveStatus.ABSORBED.value):
                    continue
                wf.radius_m += wf.velocity_mps * delta
                # Spreading attenuation reduces intensity as the sphere grows.
                if wf.radius_m > self._config.reference_distance_m:
                    spread_db = _spreading_attenuation(wf.radius_m, self._config.reference_distance_m)
                    perceived = wf.intensity_db - spread_db
                    if perceived <= self._config.wavefront_fade_db:
                        wf.status = WaveStatus.FADED.value
                        faded_count += 1
                    elif wf.radius_m >= self._config.max_wavefront_radius_m:
                        wf.status = WaveStatus.FADED.value
                        faded_count += 1
                    else:
                        wf.status = WaveStatus.PROPAGATING.value
                else:
                    wf.status = WaveStatus.PROPAGATING.value
                # Check absorption by active barriers.
                for b in self._barriers.values():
                    if not b.active:
                        continue
                    aabb = _barrier_aabb(b.position, b.dimensions)
                    # If the wavefront origin is far enough away that the
                    # sphere touches the barrier AABB, count as absorbed.
                    # Use a cheap point-vs-AABB distance check.
                    cx = _clamp(wf.origin[0], aabb[0], aabb[3])
                    cy = _clamp(wf.origin[1], aabb[1], aabb[4])
                    cz = _clamp(wf.origin[2], aabb[2], aabb[5])
                    dist = math.sqrt(
                        (wf.origin[0] - cx) ** 2
                        + (wf.origin[1] - cy) ** 2
                        + (wf.origin[2] - cz) ** 2
                    )
                    if dist <= wf.radius_m and b.absorption_coefficient > 0.9:
                        wf.status = WaveStatus.ABSORBED.value
                        absorbed_count += 1
                        break
            self._stats.tick_count = self._tick_count
            self._emit(
                AcousticEventKind.TICK.value,
                f"Tick {self._tick_count}: dt={delta:.4f}s.",
                {"dt": delta, "simulation_time": self._simulation_time,
                 "faded": faded_count, "absorbed": absorbed_count},
            )
            self._refresh_stats()
            return (True, f"Tick {self._tick_count}.", {
                "dt": delta,
                "simulation_time": self._simulation_time,
                "tick_count": self._tick_count,
                "faded_wavefronts": faded_count,
                "absorbed_wavefronts": absorbed_count,
                "active_wavefronts": sum(
                    1 for w in self._wavefronts.values()
                    if w.status in (
                        WaveStatus.EMITTED.value,
                        WaveStatus.PROPAGATING.value,
                        WaveStatus.REFLECTED.value,
                    )
                ),
            })

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_stats(self) -> AcousticStats:
        """Return the cached AcousticStats roll-up."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> AcousticSnapshot:
        """Return a full snapshot of the system state."""
        with self._lock:
            self._refresh_stats()
            return AcousticSnapshot(
                sources=[s.to_dict() for s in self._sources.values()],
                listeners=[l.to_dict() for l in self._listeners.values()],
                barriers=[b.to_dict() for b in self._barriers.values()],
                echo_zones=[z.to_dict() for z in self._echo_zones.values()],
                wavefronts=[w.to_dict() for w in self._wavefronts.values()],
                events=[e.to_dict() for e in self._events[-50:]],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a compact status summary."""
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "seeded": self._seeded,
                "sources": len(self._sources),
                "listeners": len(self._listeners),
                "barriers": len(self._barriers),
                "echo_zones": len(self._echo_zones),
                "wavefronts": len(self._wavefronts),
                "propagation_paths": len(self._propagation_paths),
                "doppler_records": len(self._doppler_records),
                "events": len(self._events),
                "simulation_time": self._simulation_time,
                "tick_count": self._tick_count,
                "active_wavefronts": self._stats.active_wavefronts,
                "peak_intensity_db": self._stats.peak_intensity_db,
            }

    def get_config(self) -> AcousticConfig:
        """Return the current AcousticConfig."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, AcousticConfig]:
        """Update tunable configuration values.

        Accepts the same keys as :class:`AcousticConfig`. Unknown keys
        are ignored and reported in the returned message.
        """
        with self._lock:
            known = set(self._config.__dataclass_fields__.keys())
            ignored: List[str] = []
            updated: List[str] = []
            for key, value in kwargs.items():
                if key == "metadata":
                    if isinstance(value, dict):
                        self._config.metadata = dict(value)
                        updated.append(key)
                    else:
                        ignored.append(key)
                    continue
                if key not in known:
                    ignored.append(key)
                    continue
                if key.startswith("enable_"):
                    setattr(self._config, key, bool(value))
                elif key in (
                    "max_sources", "max_listeners", "max_barriers",
                    "max_echo_zones", "max_wavefronts", "max_propagation_paths",
                    "max_doppler_records", "max_events", "sound_map_resolution",
                    "ai_analysis_frequency",
                ):
                    setattr(self._config, key, max(1, _safe_int(value, getattr(self._config, key))))
                else:
                    setattr(self._config, key, _safe_float(value, getattr(self._config, key)))
                updated.append(key)
            self._emit(
                AcousticEventKind.CONFIG_UPDATED.value,
                f"Config updated: {', '.join(updated) or 'no keys'}.",
                {"updated": updated, "ignored": ignored},
            )
            msg = f"Updated {len(updated)} keys."
            if ignored:
                msg += f" Ignored: {', '.join(ignored)}."
            return (True, msg, self._config)

    def reset(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Reset the entire system back to the seeded initial state."""
        with self._lock:
            self._sources.clear()
            self._listeners.clear()
            self._barriers.clear()
            self._echo_zones.clear()
            self._wavefronts.clear()
            self._propagation_paths.clear()
            self._doppler_records.clear()
            self._events.clear()
            self._stats = AcousticStats()
            self._tick_count = 0
            self._event_counter = 0
            self._wavefront_counter = 0
            self._path_counter = 0
            self._doppler_counter = 0
            self._simulation_time = 0.0
            self._propagation_distance_accum = 0.0
            self._propagation_distance_count = 0
            self._seeded = False
            self._initialized = False
            self._seed_data()
            self._initialized = True
            return (True, "System reset and reseeded.", {
                "sources": len(self._sources),
                "listeners": len(self._listeners),
                "barriers": len(self._barriers),
                "echo_zones": len(self._echo_zones),
            })


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------


def get_acoustic_wave_system() -> _AcousticWaveSystem:
    """Return the singleton _AcousticWaveSystem instance.

    Calls :meth:`_AcousticWaveSystem.get_instance` and then
    :meth:`_AcousticWaveSystem.initialize` if the instance has not yet
    been seeded, so callers always receive a ready-to-use system.
    """
    inst = _AcousticWaveSystem.get_instance()
    if not inst._initialized:
        inst.initialize()
    return inst
