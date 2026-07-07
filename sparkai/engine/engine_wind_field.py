"""
SparkLabs Engine - Wind Field System

A 3D vector wind field simulation for the SparkLabs AI-native game engine.
It maintains named wind zones (directional, radial, vortex, turbulent),
samples the composite wind vector at any point in space, and computes
aerodynamic forces (drag and lift) on objects that have a cross-section
and aerodynamic coefficient. Unlike the visual weather system, this
module is a physics-grade wind solver: it blends overlapping zones,
applies Perlin-style turbulence, generates time-based gusts, and returns
force vectors that feed into rigid-body, cable, cloth, and particle
integrators.

Architecture:
  WindFieldSystem (singleton)
    |-- WindZone, WindSample, WindFieldStats, WindFieldSnapshot, WindFieldEvent
    |-- WindZoneKind, WindFieldEventKind

Core Capabilities:
  - register_zone / get_zone / list_zones / update_zone / remove_zone:
    wind zone lifecycle with kind, position, radius, direction, strength.
  - sample_point: composite wind vector at a 3D position, blending all
    overlapping zones with falloff, turbulence, and gust modulation.
  - compute_force: aerodynamic drag and lift force on an object given
    its cross-section area, drag coefficient, and lift coefficient.
  - step: advance the wind simulation by dt, updating gust envelopes
    and turbulence phases.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`WindFieldSystem.get_instance` or the module-level
:func:`get_wind_field` factory.
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
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_ZONES: int = 2000
_MAX_SAMPLES: int = 5000
_MAX_EVENTS: int = 5000
_MAX_GUST_QUEUE: int = 200


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _vec_length(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    length = _vec_length(v)
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _vec_dot(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_cross(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec_scale(
    v: Tuple[float, float, float], s: float
) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec_add(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_sub(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


# Air density at sea level (kg/m^3)
_AIR_DENSITY: float = 1.225

# Default zone parameters by kind
_DEFAULT_ZONE_PARAMS: Dict[str, Dict[str, Any]] = {
    "directional": {
        "direction": (1.0, 0.0, 0.0),
        "strength": 5.0,
        "radius": 100.0,
        "falloff": 1.0,
        "turbulence": 0.2,
        "gust_frequency": 0.3,
        "gust_strength": 0.5,
    },
    "radial": {
        "direction": (0.0, 1.0, 0.0),
        "strength": 8.0,
        "radius": 50.0,
        "falloff": 2.0,
        "turbulence": 0.3,
        "gust_frequency": 0.2,
        "gust_strength": 0.4,
    },
    "vortex": {
        "direction": (0.0, 1.0, 0.0),
        "strength": 6.0,
        "radius": 60.0,
        "falloff": 1.5,
        "turbulence": 0.4,
        "gust_frequency": 0.15,
        "gust_strength": 0.6,
    },
    "turbulent": {
        "direction": (1.0, 0.0, 0.0),
        "strength": 4.0,
        "radius": 80.0,
        "falloff": 1.0,
        "turbulence": 0.8,
        "gust_frequency": 0.5,
        "gust_strength": 0.7,
    },
}


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class WindZoneKind(Enum):
    """Functional kinds of wind zones."""
    DIRECTIONAL = "directional"
    RADIAL = "radial"
    VORTEX = "vortex"
    TURBULENT = "turbulent"


class WindFieldEventKind(Enum):
    """Audit event types emitted by the wind field system."""
    ZONE_REGISTERED = "zone_registered"
    ZONE_REMOVED = "zone_removed"
    ZONE_UPDATED = "zone_updated"
    WIND_SAMPLED = "wind_sampled"
    FORCE_COMPUTED = "force_computed"
    STEP_COMPLETED = "step_completed"
    GUST_TRIGGERED = "gust_triggered"
    ZONE_ACTIVATED = "zone_activated"
    ZONE_DEACTIVATED = "zone_deactivated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class WindZone:
    """A named wind zone in 3D space."""
    zone_id: str = ""
    name: str = ""
    kind: str = WindZoneKind.DIRECTIONAL.value
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    strength: float = 5.0
    radius: float = 100.0
    falloff: float = 1.0
    turbulence: float = 0.2
    gust_frequency: float = 0.3
    gust_strength: float = 0.5
    active: bool = True
    phase: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WindSample:
    """A wind vector sample at a point in space."""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    speed: float = 0.0
    contributing_zones: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WindFieldStats:
    """Aggregate statistics for the wind field system."""
    total_zones: int = 0
    active_zones: int = 0
    total_samples: int = 0
    total_forces: int = 0
    total_steps: int = 0
    total_gusts: int = 0
    max_wind_speed: float = 0.0
    avg_wind_speed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WindFieldSnapshot:
    """Point-in-time snapshot of wind field state."""
    total_zones: int = 0
    active_zones: int = 0
    simulation_time: float = 0.0
    max_wind_speed: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WindFieldEvent:
    """An audit event emitted by the wind field system."""
    event_id: str = ""
    kind: str = WindFieldEventKind.ZONE_REGISTERED.value
    timestamp: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Wind Field System Singleton
# ---------------------------------------------------------------------------


class WindFieldSystem:
    """A 3D vector wind field with zones, turbulence, and gusts.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["WindFieldSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._zones: Dict[str, WindZone] = {}
        self._events: List[WindFieldEvent] = []
        self._simulation_time: float = 0.0
        self._max_wind_speed: float = 0.0
        self._speed_accum: float = 0.0
        self._speed_count: int = 0
        self._stats = WindFieldStats()
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "WindFieldSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed initial wind zones."""
        seeded = [
            WindZone(
                zone_id="wnd_global_breeze",
                name="Global Breeze",
                kind=WindZoneKind.DIRECTIONAL.value,
                position=(0.0, 0.0, 0.0),
                direction=(1.0, 0.0, 0.2),
                strength=3.0,
                radius=500.0,
                falloff=0.5,
                turbulence=0.15,
                gust_frequency=0.2,
                gust_strength=0.3,
                active=True,
                phase=0.0,
                metadata={"scene": "global"},
            ),
            WindZone(
                zone_id="wnd_canyon_vortex",
                name="Canyon Vortex",
                kind=WindZoneKind.VORTEX.value,
                position=(50.0, 0.0, 0.0),
                direction=(0.0, 1.0, 0.0),
                strength=7.0,
                radius=80.0,
                falloff=1.5,
                turbulence=0.35,
                gust_frequency=0.25,
                gust_strength=0.5,
                active=True,
                phase=1.2,
                metadata={"scene": "canyon"},
            ),
            WindZone(
                zone_id="wnd_explosion_blast",
                name="Explosion Blast",
                kind=WindZoneKind.RADIAL.value,
                position=(0.0, 5.0, 0.0),
                direction=(0.0, 1.0, 0.0),
                strength=15.0,
                radius=40.0,
                falloff=2.5,
                turbulence=0.5,
                gust_frequency=0.8,
                gust_strength=0.9,
                active=True,
                phase=0.5,
                metadata={"scene": "explosion"},
            ),
            WindZone(
                zone_id="wnd_storm_turbulent",
                name="Storm Turbulent",
                kind=WindZoneKind.TURBULENT.value,
                position=(0.0, 20.0, 0.0),
                direction=(0.8, 0.0, 0.6),
                strength=10.0,
                radius=200.0,
                falloff=1.0,
                turbulence=0.85,
                gust_frequency=0.6,
                gust_strength=0.8,
                active=True,
                phase=2.1,
                metadata={"scene": "storm"},
            ),
        ]
        for z in seeded:
            self._zones[z.zone_id] = z
        self._stats.total_zones = len(self._zones)
        self._stats.active_zones = len([z for z in self._zones.values() if z.active])
        self._initialized = True

    def _emit(self, kind: str, payload: Dict[str, Any]) -> None:
        event = WindFieldEvent(
            event_id=_new_id("wfe"),
            kind=kind,
            timestamp=_now(),
            payload=payload,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Zone Lifecycle
    # ------------------------------------------------------------------

    def register_zone(self, zone: WindZone) -> WindZone:
        if not zone.zone_id:
            zone.zone_id = _new_id("wnd")
        if not zone.name:
            zone.name = zone.zone_id
        if zone.kind not in [k.value for k in WindZoneKind]:
            zone.kind = WindZoneKind.DIRECTIONAL.value
        zone.direction = _vec_normalize(zone.direction)
        self._zones[zone.zone_id] = zone
        _evict_fifo_dict(self._zones, _MAX_ZONES)
        self._stats.total_zones = len(self._zones)
        self._stats.active_zones = len([z for z in self._zones.values() if z.active])
        self._emit(
            WindFieldEventKind.ZONE_REGISTERED.value,
            {"zone_id": zone.zone_id, "kind": zone.kind},
        )
        return zone

    def get_zone(self, zone_id: str) -> Optional[WindZone]:
        return self._zones.get(zone_id)

    def list_zones(
        self,
        kind: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[WindZone]:
        results: List[WindZone] = []
        for z in self._zones.values():
            if kind and z.kind != kind:
                continue
            if active_only and not z.active:
                continue
            results.append(z)
        return results[:max(0, int(limit))]

    def update_zone(self, zone_id: str, updates: Dict[str, Any]) -> Optional[WindZone]:
        zone = self._zones.get(zone_id)
        if zone is None:
            return None
        if "name" in updates:
            zone.name = str(updates["name"])
        if "kind" in updates and updates["kind"] in [k.value for k in WindZoneKind]:
            zone.kind = updates["kind"]
        if "position" in updates:
            pos = updates["position"]
            zone.position = tuple(pos) if isinstance(pos, list) else pos
        if "direction" in updates:
            d = updates["direction"]
            d = tuple(d) if isinstance(d, list) else d
            zone.direction = _vec_normalize(d)
        if "strength" in updates:
            zone.strength = _safe_float(updates["strength"], zone.strength)
        if "radius" in updates:
            zone.radius = _safe_float(updates["radius"], zone.radius)
        if "falloff" in updates:
            zone.falloff = _safe_float(updates["falloff"], zone.falloff)
        if "turbulence" in updates:
            zone.turbulence = _clamp(_safe_float(updates["turbulence"], zone.turbulence))
        if "gust_frequency" in updates:
            zone.gust_frequency = _safe_float(updates["gust_frequency"], zone.gust_frequency)
        if "gust_strength" in updates:
            zone.gust_strength = _safe_float(updates["gust_strength"], zone.gust_strength)
        if "active" in updates:
            zone.active = bool(updates["active"])
            self._stats.active_zones = len([z for z in self._zones.values() if z.active])
        if "phase" in updates:
            zone.phase = _safe_float(updates["phase"], zone.phase)
        if "metadata" in updates:
            zone.metadata = updates["metadata"]
        self._emit(
            WindFieldEventKind.ZONE_UPDATED.value,
            {"zone_id": zone_id},
        )
        return zone

    def remove_zone(self, zone_id: str) -> bool:
        existed = self._zones.pop(zone_id, None) is not None
        if existed:
            self._stats.total_zones = len(self._zones)
            self._stats.active_zones = len([z for z in self._zones.values() if z.active])
            self._emit(
                WindFieldEventKind.ZONE_REMOVED.value,
                {"zone_id": zone_id},
            )
        return existed

    # ------------------------------------------------------------------
    # Wind Sampling
    # ------------------------------------------------------------------

    def _zone_influence(
        self, zone: WindZone, position: Tuple[float, float, float]
    ) -> float:
        """Compute the influence weight of a zone at a position (0..1)."""
        diff = _vec_sub(position, zone.position)
        dist = _vec_length(diff)
        if dist > zone.radius:
            return 0.0
        if zone.radius < 1e-9:
            return 1.0
        t = dist / zone.radius
        falloff = zone.falloff if zone.falloff > 0 else 1.0
        return max(0.0, 1.0 - t) ** falloff

    def _gust_factor(self, zone: WindZone) -> float:
        """Compute the current gust modulation factor for a zone."""
        freq = zone.gust_frequency if zone.gust_frequency > 0 else 0.01
        phase = zone.phase + self._simulation_time * freq * 2.0 * math.pi
        raw = math.sin(phase)
        gust = 1.0 + raw * zone.gust_strength
        return max(0.0, gust)

    def _turbulence_vector(
        self, zone: WindZone, position: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """Compute a pseudo-Perlin turbulence vector."""
        t = zone.turbulence
        if t < 1e-6:
            return (0.0, 0.0, 0.0)
        phase = zone.phase + self._simulation_time * 0.7
        bx = math.sin(position[0] * 0.1 + phase) * math.cos(position[1] * 0.13 + phase * 1.1)
        by = math.sin(position[1] * 0.11 + phase * 1.3) * math.cos(position[2] * 0.12 + phase * 0.9)
        bz = math.sin(position[2] * 0.09 + phase * 0.8) * math.cos(position[0] * 0.14 + phase * 1.2)
        return (bx * t, by * t, bz * t)

    def _zone_wind_vector(
        self, zone: WindZone, position: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """Compute the wind vector from a single zone at a position."""
        influence = self._zone_influence(zone, position)
        if influence < 1e-6:
            return (0.0, 0.0, 0.0)
        gust = self._gust_factor(zone)
        base_strength = zone.strength * influence * gust
        if zone.kind == WindZoneKind.DIRECTIONAL.value:
            v = _vec_scale(zone.direction, base_strength)
        elif zone.kind == WindZoneKind.RADIAL.value:
            diff = _vec_sub(position, zone.position)
            direction = _vec_normalize(diff)
            v = _vec_scale(direction, base_strength)
        elif zone.kind == WindZoneKind.VORTEX.value:
            diff = _vec_sub(position, zone.position)
            cross = _vec_cross(zone.direction, diff)
            direction = _vec_normalize(cross)
            v = _vec_scale(direction, base_strength)
        elif zone.kind == WindZoneKind.TURBULENT.value:
            turb = self._turbulence_vector(zone, position)
            v = _vec_add(_vec_scale(zone.direction, base_strength * 0.5), _vec_scale(turb, base_strength))
        else:
            v = _vec_scale(zone.direction, base_strength)
        turb = self._turbulence_vector(zone, position)
        v = _vec_add(v, _vec_scale(turb, base_strength * 0.3))
        return v

    def sample_point(self, position: Tuple[float, float, float]) -> Dict[str, Any]:
        """Sample the composite wind vector at a 3D position."""
        pos = tuple(position) if isinstance(position, list) else position
        composite = (0.0, 0.0, 0.0)
        contributing: List[str] = []
        for zone in self._zones.values():
            if not zone.active:
                continue
            v = self._zone_wind_vector(zone, pos)
            if _vec_length(v) > 1e-6:
                composite = _vec_add(composite, v)
                contributing.append(zone.zone_id)
        speed = _vec_length(composite)
        self._stats.total_samples += 1
        if speed > self._stats.max_wind_speed:
            self._stats.max_wind_speed = speed
        self._speed_accum += speed
        self._speed_count += 1
        self._stats.avg_wind_speed = self._speed_accum / max(1, self._speed_count)
        sample = WindSample(
            position=pos,
            velocity=composite,
            speed=speed,
            contributing_zones=contributing,
            timestamp=_now(),
        )
        self._emit(
            WindFieldEventKind.WIND_SAMPLED.value,
            {"position": list(pos), "speed": speed, "zones": len(contributing)},
        )
        return sample.to_dict()

    # ------------------------------------------------------------------
    # Aerodynamic Force
    # ------------------------------------------------------------------

    def compute_force(
        self,
        position: Tuple[float, float, float],
        cross_section: float = 1.0,
        drag_coefficient: float = 1.0,
        lift_coefficient: float = 0.0,
        object_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> Dict[str, Any]:
        """Compute aerodynamic drag and lift force on an object."""
        pos = tuple(position) if isinstance(position, list) else position
        vel = tuple(object_velocity) if isinstance(object_velocity, list) else object_velocity
        wind = self.sample_point(pos)
        wind_vel = tuple(wind["velocity"])
        relative_vel = _vec_sub(wind_vel, vel)
        rel_speed = _vec_length(relative_vel)
        if rel_speed < 1e-6:
            return {
                "drag_force": [0.0, 0.0, 0.0],
                "lift_force": [0.0, 0.0, 0.0],
                "total_force": [0.0, 0.0, 0.0],
                "relative_speed": 0.0,
                "wind_speed": wind["speed"],
                "position": list(pos),
            }
        rel_dir = _vec_normalize(relative_vel)
        # Drag force = 0.5 * rho * v^2 * Cd * A * direction
        drag_magnitude = 0.5 * _AIR_DENSITY * rel_speed * rel_speed * drag_coefficient * cross_section
        drag_force = _vec_scale(rel_dir, drag_magnitude)
        # Lift force = 0.5 * rho * v^2 * Cl * A * perpendicular
        lift_magnitude = 0.5 * _AIR_DENSITY * rel_speed * rel_speed * lift_coefficient * cross_section
        # Lift direction is perpendicular to relative velocity, in the vertical plane
        up = (0.0, 1.0, 0.0)
        cross = _vec_cross(rel_dir, up)
        cross_len = _vec_length(cross)
        if cross_len > 1e-6:
            lift_dir = _vec_normalize(cross)
        else:
            lift_dir = (0.0, 1.0, 0.0)
        lift_force = _vec_scale(lift_dir, lift_magnitude)
        total_force = _vec_add(drag_force, lift_force)
        self._stats.total_forces += 1
        self._emit(
            WindFieldEventKind.FORCE_COMPUTED.value,
            {
                "position": list(pos),
                "relative_speed": rel_speed,
                "drag": drag_magnitude,
                "lift": lift_magnitude,
            },
        )
        return {
            "drag_force": list(drag_force),
            "lift_force": list(lift_force),
            "total_force": list(total_force),
            "relative_speed": rel_speed,
            "wind_speed": wind["speed"],
            "position": list(pos),
        }

    # ------------------------------------------------------------------
    # Simulation Step
    # ------------------------------------------------------------------

    def step(self, dt: float) -> Dict[str, Any]:
        """Advance the wind simulation by dt seconds."""
        dt = _safe_float(dt, 0.016)
        self._simulation_time += dt
        self._stats.total_steps += 1
        self._emit(
            WindFieldEventKind.STEP_COMPLETED.value,
            {"dt": dt, "simulation_time": self._simulation_time},
        )
        return {
            "simulation_time": self._simulation_time,
            "dt": dt,
            "active_zones": len([z for z in self._zones.values() if z.active]),
        }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, kind: str = "", limit: int = 50) -> List[WindFieldEvent]:
        results: List[WindFieldEvent] = []
        for e in reversed(self._events):
            if kind and e.kind != kind:
                continue
            results.append(e)
            if len(results) >= max(1, int(limit)):
                break
        return results

    def get_stats(self) -> WindFieldStats:
        self._stats.total_zones = len(self._zones)
        self._stats.active_zones = len([z for z in self._zones.values() if z.active])
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "zones": len(self._zones),
            "active_zones": len([z for z in self._zones.values() if z.active]),
            "simulation_time": self._simulation_time,
            "max_wind_speed": self._stats.max_wind_speed,
            "avg_wind_speed": self._stats.avg_wind_speed,
            "events": len(self._events),
        }

    def get_snapshot(self) -> WindFieldSnapshot:
        return WindFieldSnapshot(
            total_zones=len(self._zones),
            active_zones=len([z for z in self._zones.values() if z.active]),
            simulation_time=self._simulation_time,
            max_wind_speed=self._stats.max_wind_speed,
            timestamp=_now(),
        )

    def reset(self) -> None:
        with self._init_lock:
            self._zones.clear()
            self._events.clear()
            self._simulation_time = 0.0
            self._max_wind_speed = 0.0
            self._speed_accum = 0.0
            self._speed_count = 0
            self._stats = WindFieldStats()
            self._seed()


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------


def get_wind_field() -> WindFieldSystem:
    """Return the singleton WindFieldSystem instance."""
    return WindFieldSystem.get_instance()
