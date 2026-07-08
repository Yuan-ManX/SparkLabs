"""
SparkLabs Engine - Gravity Field System

Models spatial gravity regions with custom directions, magnitudes, and
fall-off curves. Supports planetary gravity wells, zero-G pockets,
directional fields for wall-running, and blended overlapping fields
for smooth transitions between gravity zones.

Designed for platformers, space shooters, puzzle games, and any
experience that needs non-uniform gravity. Integrates with the physics
dynamics core, vehicle physics, and character controllers.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> float:
    return time.time()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * _clamp(t, 0.0, 1.0)


def _length3(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _normalize3(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    n = _length3(v)
    if n < 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _scale3(v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _add3(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub3(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
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
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_FIELDS = 2000
_MAX_WELLS = 500
_MAX_PROBES = 5000
_MAX_EVENTS = 5000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FieldKind(str, Enum):
    """Shape of the gravity field region."""
    BOX = "box"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    CAPSULE = "capsule"
    PLANE = "plane"
    GLOBAL = "global"


class FieldMode(str, Enum):
    """How the field affects bodies inside it."""
    ABSOLUTE = "absolute"
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"
    ZERO_G = "zero_g"
    POINT_ATTRACT = "point_attract"
    POINT_REPEL = "point_repel"


class FalloffCurve(str, Enum):
    """Fall-off function used to attenuate field strength with distance."""
    NONE = "none"
    LINEAR = "linear"
    INVERSE = "inverse"
    INVERSE_SQUARE = "inverse_square"
    SMOOTHSTEP = "smoothstep"
    SMOOTHERSTEP = "smootherstep"


class FieldPriority(str, Enum):
    """Priority tier for resolving overlapping fields."""
    BACKGROUND = "background"
    NORMAL = "normal"
    HIGH = "high"
    OVERRIDE = "override"


class GravityEventKind(str, Enum):
    FIELD_REGISTERED = "field_registered"
    FIELD_REMOVED = "field_removed"
    FIELD_ENABLED = "field_enabled"
    FIELD_DISABLED = "field_disabled"
    WELL_REGISTERED = "well_registered"
    WELL_REMOVED = "well_removed"
    PROBE_SAMPLED = "probe_sampled"
    BODY_ENTERED = "body_entered"
    BODY_EXITED = "body_exited"
    MODE_CHANGED = "mode_changed"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FieldShape:
    """Geometric description of the field region."""
    kind: str = FieldKind.BOX.value
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    size: Tuple[float, float, float] = (10.0, 10.0, 10.0)
    radius: float = 5.0
    height: float = 10.0
    rotation_yaw: float = 0.0
    rotation_pitch: float = 0.0
    rotation_roll: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GravityField:
    """A single gravity field region with a custom gravity vector."""
    field_id: str
    name: str = ""
    kind: str = FieldKind.BOX.value
    mode: str = FieldMode.ABSOLUTE.value
    priority: str = FieldPriority.NORMAL.value
    shape: FieldShape = field(default_factory=FieldShape)
    gravity_vector: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    magnitude: float = 9.81
    direction: Tuple[float, float, float] = (0.0, -1.0, 0.0)
    falloff: str = FalloffCurve.LINEAR.value
    falloff_start: float = 0.0
    falloff_end: float = 1.0
    enabled: bool = True
    blend_weight: float = 1.0
    attract_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    attract_strength: float = 9.81
    min_distance: float = 0.1
    max_distance: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GravityWell:
    """A point-source gravity attractor or repulsor."""
    well_id: str
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mass: float = 5.972e24
    gravitational_constant: float = 6.674e-11
    repel: bool = False
    enabled: bool = True
    inner_radius: float = 1.0
    outer_radius: float = 100.0
    falloff: str = FalloffCurve.INVERSE_SQUARE.value
    max_acceleration: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GravitySample:
    """Result of probing gravity at a single point."""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    acceleration: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    magnitude: float = 9.81
    contributing_fields: List[str] = field(default_factory=list)
    in_zero_g: bool = False
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BodyTracking:
    """Tracks a body's gravity state for entered/exited events."""
    body_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    current_field_ids: List[str] = field(default_factory=list)
    last_acceleration: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GravityConfig:
    default_gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    default_magnitude: float = 9.81
    max_fields: int = 500
    max_wells: int = 100
    max_tracked_bodies: int = 1000
    blend_strategy: str = "weighted_average"
    zero_g_threshold: float = 0.05
    enable_wells: bool = True
    enable_field_blending: bool = True
    body_tracking_enabled: bool = True
    global_field_id: str = "fld_global_default"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GravityStats:
    total_fields: int = 0
    enabled_fields: int = 0
    disabled_fields: int = 0
    total_wells: int = 0
    total_probes: int = 0
    zero_g_samples: int = 0
    bodies_entered: int = 0
    bodies_exited: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GravitySnapshot:
    fields: List[Dict[str, Any]] = field(default_factory=list)
    wells: List[Dict[str, Any]] = field(default_factory=list)
    tracked_bodies: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GravityEvent:
    event_id: str
    kind: str
    timestamp: float
    field_id: Optional[str] = None
    well_id: Optional[str] = None
    body_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Gravity Field System
# ---------------------------------------------------------------------------

class GravityFieldSystem:
    """Manages spatial gravity fields and point-source gravity wells."""

    _instance: Optional["GravityFieldSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._fields: Dict[str, GravityField] = {}
        self._wells: Dict[str, GravityWell] = {}
        self._bodies: Dict[str, BodyTracking] = {}
        self._events: List[GravityEvent] = []
        self._stats = GravityStats()
        self._config = GravityConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "GravityFieldSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed default fields and a couple of demonstration wells."""
        global_field = GravityField(
            field_id=self._config.global_field_id,
            name="Global Default Gravity",
            kind=FieldKind.GLOBAL.value,
            mode=FieldMode.ABSOLUTE.value,
            priority=FieldPriority.BACKGROUND.value,
            shape=FieldShape(kind=FieldKind.GLOBAL.value, center=(0.0, 0.0, 0.0), size=(0.0, 0.0, 0.0), radius=0.0, height=0.0),
            gravity_vector=self._config.default_gravity,
            magnitude=self._config.default_magnitude,
            direction=(0.0, -1.0, 0.0),
            falloff=FalloffCurve.NONE.value,
            enabled=True,
            blend_weight=1.0,
        )
        self._fields[global_field.field_id] = global_field

        zero_g_pocket = GravityField(
            field_id="fld_zero_g_pocket",
            name="Zero-G Chamber",
            kind=FieldKind.SPHERE.value,
            mode=FieldMode.ZERO_G.value,
            priority=FieldPriority.HIGH.value,
            shape=FieldShape(
                kind=FieldKind.SPHERE.value,
                center=(50.0, 10.0, 0.0),
                size=(20.0, 20.0, 20.0),
                radius=10.0,
            ),
            gravity_vector=(0.0, 0.0, 0.0),
            magnitude=0.0,
            direction=(0.0, 0.0, 0.0),
            falloff=FalloffCurve.SMOOTHSTEP.value,
            falloff_start=0.8,
            falloff_end=1.0,
            enabled=True,
            blend_weight=1.0,
        )
        self._fields[zero_g_pocket.field_id] = zero_g_pocket

        wall_run_field = GravityField(
            field_id="fld_wall_run_east",
            name="East Wall-Run Field",
            kind=FieldKind.BOX.value,
            mode=FieldMode.ABSOLUTE.value,
            priority=FieldPriority.NORMAL.value,
            shape=FieldShape(
                kind=FieldKind.BOX.value,
                center=(100.0, 5.0, 0.0),
                size=(2.0, 10.0, 20.0),
                radius=0.0,
            ),
            gravity_vector=(-9.81, 0.0, 0.0),
            magnitude=9.81,
            direction=(-1.0, 0.0, 0.0),
            falloff=FalloffCurve.LINEAR.value,
            falloff_start=0.0,
            falloff_end=1.0,
            enabled=True,
            blend_weight=1.0,
        )
        self._fields[wall_run_field.field_id] = wall_run_field

        planet_well = GravityWell(
            well_id="wel_planet_core",
            name="Planet Core Attractor",
            position=(0.0, -500.0, 0.0),
            mass=5.972e24,
            inner_radius=10.0,
            outer_radius=1000.0,
            max_acceleration=25.0,
        )
        self._wells[planet_well.well_id] = planet_well

        repulsor_well = GravityWell(
            well_id="wel_anti_grav_node",
            name="Anti-Gravity Node",
            position=(75.0, 15.0, 0.0),
            mass=1.0e22,
            inner_radius=2.0,
            outer_radius=30.0,
            max_acceleration=15.0,
            repel=True,
        )
        self._wells[repulsor_well.well_id] = repulsor_well

        self._stats.total_fields = len(self._fields)
        self._stats.enabled_fields = sum(1 for f in self._fields.values() if f.enabled)
        self._stats.disabled_fields = self._stats.total_fields - self._stats.enabled_fields
        self._stats.total_wells = len(self._wells)
        self._initialized = True

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"gevt_{self._event_counter:08d}"

    def _record_event(self, kind: str, **kwargs: Any) -> GravityEvent:
        event = GravityEvent(
            event_id=self._next_event_id(),
            kind=kind,
            timestamp=_now(),
            **kwargs,
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]
        return event

    # ------------------------------------------------------------------
    # Field Management
    # ------------------------------------------------------------------

    def register_field(self, field: GravityField) -> Dict[str, Any]:
        """Register a new gravity field. Replaces existing field with same id."""
        if len(self._fields) >= _MAX_FIELDS and field.field_id not in self._fields:
            oldest_id = next(iter(self._fields))
            self._fields.pop(oldest_id, None)
        was_new = field.field_id not in self._fields
        self._fields[field.field_id] = field
        self._stats.total_fields = len(self._fields)
        self._stats.enabled_fields = sum(1 for f in self._fields.values() if f.enabled)
        self._stats.disabled_fields = self._stats.total_fields - self._stats.enabled_fields
        self._record_event(
            GravityEventKind.FIELD_REGISTERED if was_new else GravityEventKind.MODE_CHANGED,
            field_id=field.field_id,
            details={"name": field.name, "kind": field.kind, "mode": field.mode},
        )
        return {"field_id": field.field_id, "registered": True}

    def remove_field(self, field_id: str) -> Dict[str, Any]:
        if field_id == self._config.global_field_id:
            return {"field_id": field_id, "removed": False, "reason": "global field cannot be removed"}
        if field_id not in self._fields:
            return {"field_id": field_id, "removed": False, "reason": "not found"}
        self._fields.pop(field_id)
        self._stats.total_fields = len(self._fields)
        self._stats.enabled_fields = sum(1 for f in self._fields.values() if f.enabled)
        self._stats.disabled_fields = self._stats.total_fields - self._stats.enabled_fields
        self._record_event(GravityEventKind.FIELD_REMOVED, field_id=field_id)
        return {"field_id": field_id, "removed": True}

    def get_field(self, field_id: str) -> Optional[GravityField]:
        return self._fields.get(field_id)

    def list_fields(self, kind: Optional[str] = None, mode: Optional[str] = None, enabled: Optional[bool] = None, limit: int = 100) -> List[GravityField]:
        results: List[GravityField] = []
        for f in self._fields.values():
            if kind is not None and f.kind != kind:
                continue
            if mode is not None and f.mode != mode:
                continue
            if enabled is not None and f.enabled != enabled:
                continue
            results.append(f)
        return results[:max(0, min(limit, len(results)))]

    def enable_field(self, field_id: str, enabled: bool) -> Dict[str, Any]:
        f = self._fields.get(field_id)
        if f is None:
            return {"field_id": field_id, "updated": False, "reason": "not found"}
        f.enabled = enabled
        f.updated_at = _now()
        self._stats.enabled_fields = sum(1 for x in self._fields.values() if x.enabled)
        self._stats.disabled_fields = self._stats.total_fields - self._stats.enabled_fields
        self._record_event(
            GravityEventKind.FIELD_ENABLED if enabled else GravityEventKind.FIELD_DISABLED,
            field_id=field_id,
        )
        return {"field_id": field_id, "enabled": enabled}

    def set_field_mode(self, field_id: str, mode: str) -> Dict[str, Any]:
        f = self._fields.get(field_id)
        if f is None:
            return {"field_id": field_id, "updated": False, "reason": "not found"}
        f.mode = mode
        f.updated_at = _now()
        self._record_event(GravityEventKind.MODE_CHANGED, field_id=field_id, details={"mode": mode})
        return {"field_id": field_id, "mode": mode}

    # ------------------------------------------------------------------
    # Well Management
    # ------------------------------------------------------------------

    def register_well(self, well: GravityWell) -> Dict[str, Any]:
        if len(self._wells) >= _MAX_WELLS and well.well_id not in self._wells:
            oldest_id = next(iter(self._wells))
            self._wells.pop(oldest_id, None)
        was_new = well.well_id not in self._wells
        self._wells[well.well_id] = well
        self._stats.total_wells = len(self._wells)
        self._record_event(
            GravityEventKind.WELL_REGISTERED if was_new else GravityEventKind.MODE_CHANGED,
            well_id=well.well_id,
            details={"name": well.name, "repel": well.repel},
        )
        return {"well_id": well.well_id, "registered": True}

    def remove_well(self, well_id: str) -> Dict[str, Any]:
        if well_id not in self._wells:
            return {"well_id": well_id, "removed": False, "reason": "not found"}
        self._wells.pop(well_id)
        self._stats.total_wells = len(self._wells)
        self._record_event(GravityEventKind.WELL_REMOVED, well_id=well_id)
        return {"well_id": well_id, "removed": True}

    def get_well(self, well_id: str) -> Optional[GravityWell]:
        return self._wells.get(well_id)

    def list_wells(self, limit: int = 100) -> List[GravityWell]:
        return list(self._wells.values())[:max(0, min(limit, len(self._wells)))]

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------

    def _point_in_shape(self, shape: FieldShape, point: Tuple[float, float, float]) -> bool:
        kind = shape.kind
        if kind == FieldKind.GLOBAL.value:
            return True
        if kind == FieldKind.SPHERE.value:
            d = _length3(_sub3(point, shape.center))
            return d <= shape.radius
        if kind == FieldKind.BOX.value:
            for i in range(3):
                half = shape.size[i] * 0.5
                if abs(point[i] - shape.center[i]) > half:
                    return False
            return True
        if kind == FieldKind.CYLINDER.value:
            dx = point[0] - shape.center[0]
            dz = point[2] - shape.center[2]
            radial = math.sqrt(dx * dx + dz * dz)
            if radial > shape.radius:
                return False
            half_h = shape.height * 0.5
            if abs(point[1] - shape.center[1]) > half_h:
                return False
            return True
        if kind == FieldKind.CAPSULE.value:
            dx = point[0] - shape.center[0]
            dz = point[2] - shape.center[2]
            radial = math.sqrt(dx * dx + dz * dz)
            if radial > shape.radius:
                return False
            half_h = shape.height * 0.5
            y_rel = point[1] - shape.center[1]
            if -half_h <= y_rel <= half_h:
                return True
            cap_offset = half_h if y_rel > 0 else -half_h
            cap_center = (shape.center[0], shape.center[1] + cap_offset, shape.center[2])
            d = _length3(_sub3(point, cap_center))
            return d <= shape.radius
        if kind == FieldKind.PLANE.value:
            return abs(point[1] - shape.center[1]) <= shape.height * 0.5
        return False

    def _shape_distance_factor(self, shape: FieldShape, point: Tuple[float, float, float]) -> float:
        """Return normalized distance factor in [0,1] where 0=center, 1=edge."""
        kind = shape.kind
        if kind == FieldKind.GLOBAL.value:
            return 0.0
        if kind == FieldKind.SPHERE.value:
            d = _length3(_sub3(point, shape.center))
            return _clamp(d / max(shape.radius, 1e-6), 0.0, 1.0)
        if kind == FieldKind.BOX.value:
            max_ratio = 0.0
            for i in range(3):
                half = shape.size[i] * 0.5
                if half < 1e-6:
                    continue
                max_ratio = max(max_ratio, abs(point[i] - shape.center[i]) / half)
            return _clamp(max_ratio, 0.0, 1.0)
        if kind == FieldKind.CYLINDER.value:
            dx = point[0] - shape.center[0]
            dz = point[2] - shape.center[2]
            radial = math.sqrt(dx * dx + dz * dz)
            radial_factor = _clamp(radial / max(shape.radius, 1e-6), 0.0, 1.0)
            half_h = max(shape.height * 0.5, 1e-6)
            vertical_factor = _clamp(abs(point[1] - shape.center[1]) / half_h, 0.0, 1.0)
            return max(radial_factor, vertical_factor)
        if kind == FieldKind.CAPSULE.value:
            dx = point[0] - shape.center[0]
            dz = point[2] - shape.center[2]
            radial = math.sqrt(dx * dx + dz * dz)
            radial_factor = _clamp(radial / max(shape.radius, 1e-6), 0.0, 1.0)
            half_h = max(shape.height * 0.5, 1e-6)
            y_rel = point[1] - shape.center[1]
            if -half_h <= y_rel <= half_h:
                return radial_factor
            cap_offset = half_h if y_rel > 0 else -half_h
            cap_center = (shape.center[0], shape.center[1] + cap_offset, shape.center[2])
            d = _length3(_sub3(point, cap_center))
            return _clamp(d / max(shape.radius, 1e-6), 0.0, 1.0)
        if kind == FieldKind.PLANE.value:
            return _clamp(abs(point[1] - shape.center[1]) / max(shape.height * 0.5, 1e-6), 0.0, 1.0)
        return 0.0

    def _falloff_weight(self, curve: str, t: float, start: float, end: float) -> float:
        if curve == FalloffCurve.NONE.value:
            return 1.0
        if t <= start:
            return 1.0
        if t >= end:
            base = 0.0
        else:
            span = max(end - start, 1e-6)
            local_t = (t - start) / span
            if curve == FalloffCurve.LINEAR.value:
                base = 1.0 - local_t
            elif curve == FalloffCurve.INVERSE.value:
                base = 1.0 / (1.0 + local_t * 9.0)
            elif curve == FalloffCurve.INVERSE_SQUARE.value:
                base = 1.0 / (1.0 + local_t * local_t * 99.0)
            elif curve == FalloffCurve.SMOOTHSTEP.value:
                base = 1.0 - (local_t * local_t * (3.0 - 2.0 * local_t))
            elif curve == FalloffCurve.SMOOTHERSTEP.value:
                base = 1.0 - (local_t * local_t * local_t * (local_t * (local_t * 6.0 - 15.0) + 10.0))
            else:
                base = 1.0 - local_t
        return _clamp(base, 0.0, 1.0)

    # ------------------------------------------------------------------
    # Gravity sampling
    # ------------------------------------------------------------------

    def sample_gravity(self, position: Tuple[float, float, float]) -> GravitySample:
        """Compute blended gravity acceleration at the given position."""
        contributing: List[str] = []
        in_zero_g = False
        accumulated = (0.0, 0.0, 0.0)
        total_weight = 0.0

        # Sort fields by priority tier
        priority_order = {
            FieldPriority.BACKGROUND.value: 0,
            FieldPriority.NORMAL.value: 1,
            FieldPriority.HIGH.value: 2,
            FieldPriority.OVERRIDE.value: 3,
        }
        active_fields = [f for f in self._fields.values() if f.enabled]
        active_fields.sort(key=lambda f: priority_order.get(f.priority, 0))

        override_active = False
        for f in active_fields:
            if not self._point_in_shape(f.shape, position):
                continue
            t = self._shape_distance_factor(f.shape, position)
            weight = self._falloff_weight(f.falloff, t, f.falloff_start, f.falloff_end)
            weight *= f.blend_weight
            if weight <= 0.0:
                continue

            if f.mode == FieldMode.ZERO_G.value:
                in_zero_g = True
                contributing.append(f.field_id)
                accumulated = (0.0, 0.0, 0.0)
                total_weight = 0.0
                continue

            if f.priority == FieldPriority.OVERRIDE.value:
                override_active = True
                accumulated = (0.0, 0.0, 0.0)
                total_weight = 0.0

            if f.mode == FieldMode.ABSOLUTE.value:
                vec = _scale3(f.direction, f.magnitude)
                accumulated = _add3(accumulated, _scale3(vec, weight))
                total_weight += weight
            elif f.mode == FieldMode.ADDITIVE.value:
                vec = _scale3(f.direction, f.magnitude)
                accumulated = _add3(accumulated, _scale3(vec, weight))
                total_weight += weight
            elif f.mode == FieldMode.MULTIPLICATIVE.value:
                base = _length3(accumulated) if total_weight > 0 else self._config.default_magnitude
                vec = _scale3(f.direction, base * (f.magnitude / 9.81))
                accumulated = _scale3(accumulated, weight) if total_weight > 0 else vec
                accumulated = _add3(accumulated, _scale3(vec, 1.0 - weight))
                total_weight += weight
            elif f.mode in (FieldMode.POINT_ATTRACT.value, FieldMode.POINT_REPEL.value):
                delta = _sub3(f.attract_point, position)
                dist = _length3(delta)
                if dist < f.min_distance:
                    dist = f.min_distance
                    delta = _scale3(_normalize3(delta), dist)
                if dist > f.max_distance:
                    continue
                direction = _normalize3(delta)
                if f.mode == FieldMode.POINT_REPEL.value:
                    direction = _scale3(direction, -1.0)
                t_norm = _clamp((dist - f.min_distance) / max(f.max_distance - f.min_distance, 1e-6), 0.0, 1.0)
                accel = f.attract_strength * self._falloff_weight(f.falloff, t_norm, 0.0, 1.0)
                vec = _scale3(direction, accel)
                accumulated = _add3(accumulated, _scale3(vec, weight))
                total_weight += weight

            contributing.append(f.field_id)

        if not override_active and total_weight > 0:
            accumulated = _scale3(accumulated, 1.0 / total_weight)

        # Apply wells
        if self._config.enable_wells and not in_zero_g:
            for w in self._wells.values():
                if not w.enabled:
                    continue
                delta = _sub3(w.position, position)
                dist = _length3(delta)
                if dist < w.inner_radius:
                    dist = w.inner_radius
                    delta = _scale3(_normalize3(delta), dist)
                if dist > w.outer_radius:
                    continue
                direction = _normalize3(delta)
                if w.repel:
                    direction = _scale3(direction, -1.0)
                # Newtonian magnitude with cap
                accel = w.gravitational_constant * w.mass / max(dist * dist, 1e-6)
                accel = min(accel, w.max_acceleration)
                # Apply falloff based on normalized distance
                t_norm = _clamp((dist - w.inner_radius) / max(w.outer_radius - w.inner_radius, 1e-6), 0.0, 1.0)
                accel *= self._falloff_weight(w.falloff, t_norm, 0.0, 1.0)
                accumulated = _add3(accumulated, _scale3(direction, accel))

        magnitude = _length3(accumulated)
        if magnitude < self._config.zero_g_threshold:
            in_zero_g = True
            accumulated = (0.0, 0.0, 0.0)
            magnitude = 0.0

        sample = GravitySample(
            position=position,
            acceleration=accumulated,
            magnitude=magnitude,
            contributing_fields=contributing,
            in_zero_g=in_zero_g,
            timestamp=_now(),
        )
        self._stats.total_probes += 1
        if in_zero_g:
            self._stats.zero_g_samples += 1
        self._record_event(
            GravityEventKind.PROBE_SAMPLED,
            details={"position": list(position), "magnitude": magnitude, "in_zero_g": in_zero_g},
        )
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]
        return sample

    # ------------------------------------------------------------------
    # Body tracking
    # ------------------------------------------------------------------

    def update_body(self, body_id: str, position: Tuple[float, float, float]) -> Dict[str, Any]:
        """Update a tracked body's position and emit entered/exited events."""
        if not self._config.body_tracking_enabled:
            return {"body_id": body_id, "tracked": False}
        if len(self._bodies) >= self._config.max_tracked_bodies and body_id not in self._bodies:
            oldest_id = next(iter(self._bodies))
            self._bodies.pop(oldest_id, None)
        body = self._bodies.get(body_id)
        if body is None:
            body = BodyTracking(body_id=body_id, position=position)
            self._bodies[body_id] = body

        previous_fields = set(body.current_field_ids)
        current_fields: List[str] = []
        for f in self._fields.values():
            if not f.enabled:
                continue
            if self._point_in_shape(f.shape, position):
                current_fields.append(f.field_id)
        current_set = set(current_fields)

        entered = current_set - previous_fields
        exited = previous_fields - current_set

        sample = self.sample_gravity(position)
        body.position = position
        body.current_field_ids = current_fields
        body.last_acceleration = sample.acceleration
        body.updated_at = _now()

        for fid in entered:
            self._stats.bodies_entered += 1
            self._record_event(GravityEventKind.BODY_ENTERED, field_id=fid, body_id=body_id)
        for fid in exited:
            self._stats.bodies_exited += 1
            self._record_event(GravityEventKind.BODY_EXITED, field_id=fid, body_id=body_id)

        return {
            "body_id": body_id,
            "tracked": True,
            "current_fields": current_fields,
            "entered": list(entered),
            "exited": list(exited),
            "acceleration": list(sample.acceleration),
            "magnitude": sample.magnitude,
            "in_zero_g": sample.in_zero_g,
        }

    def get_body(self, body_id: str) -> Optional[BodyTracking]:
        return self._bodies.get(body_id)

    def list_bodies(self, limit: int = 100) -> List[BodyTracking]:
        return list(self._bodies.values())[:max(0, min(limit, len(self._bodies)))]

    def remove_body(self, body_id: str) -> Dict[str, Any]:
        if body_id not in self._bodies:
            return {"body_id": body_id, "removed": False}
        self._bodies.pop(body_id)
        return {"body_id": body_id, "removed": True}

    # ------------------------------------------------------------------
    # Tick / lifecycle
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        self._record_event(GravityEventKind.TICK, details={"delta_time": delta_time, "tick": self._tick_count})
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]
        return {"tick": self._tick_count, "delta_time": delta_time}

    def get_config(self) -> GravityConfig:
        return self._config

    def set_config(self, config: GravityConfig) -> Dict[str, Any]:
        self._config = config
        self._record_event(GravityEventKind.CONFIG_UPDATED, details={"max_fields": config.max_fields})
        return {"updated": True}

    def list_events(self, field_id: Optional[str] = None, well_id: Optional[str] = None, body_id: Optional[str] = None, limit: int = 100) -> List[GravityEvent]:
        results: List[GravityEvent] = []
        for e in self._events:
            if field_id is not None and e.field_id != field_id:
                continue
            if well_id is not None and e.well_id != well_id:
                continue
            if body_id is not None and e.body_id != body_id:
                continue
            results.append(e)
        return list(reversed(results))[:max(0, min(limit, len(results)))]

    def get_stats(self) -> GravityStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_fields": len(self._fields),
            "enabled_fields": sum(1 for f in self._fields.values() if f.enabled),
            "total_wells": len(self._wells),
            "tracked_bodies": len(self._bodies),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> GravitySnapshot:
        return GravitySnapshot(
            fields=[f.to_dict() for f in self._fields.values()],
            wells=[w.to_dict() for w in self._wells.values()],
            tracked_bodies=len(self._bodies),
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        self._fields.clear()
        self._wells.clear()
        self._bodies.clear()
        self._events.clear()
        self._stats = GravityStats()
        self._tick_count = 0
        self._event_counter = 0
        self._initialized = False
        self._seed()
        self._record_event(GravityEventKind.RESET)
        return {"reset": True, "initialized": self._initialized}


def get_gravity_field() -> GravityFieldSystem:
    return GravityFieldSystem.get_instance()
