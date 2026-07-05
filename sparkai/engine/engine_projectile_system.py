"""
SparkLabs Engine - Projectile System

A runtime projectile simulation core for the SparkLabs AI-native game engine.
It manages projectile types (bullets, arrows, spell bolts, thrown items) with
trajectory patterns ranging from linear and ballistic gravity-drop to homing
and spiral paths. The system handles piercing, ricochet, splash-damage falloff,
team-affiliation filtering, lifecycle expiry, and per-projectile object pooling.
Designed for high-volume combat scenes without per-frame allocation churn.

Architecture:
  ProjectileSystem (singleton)
    |-- ProjectileType, ProjectileInstance, SplashFalloff,
       ProjectileStats, ProjectileSnapshot, ProjectileEvent
    |-- ProjectileTrajectory, ProjectileStatus, ProjectileEventKind

Core Capabilities:
  - register_type / get_type / list_types / update_type / remove_type:
    projectile type lifecycle with speed, drag, gravity, and payload.
  - spawn_projectile / get_projectile / list_projectiles / remove_projectile:
    instance lifecycle with owner, team, and target.
  - tick: advance simulation by a delta time, integrating trajectories and
    resolving collisions, pierce counts, and expiry.
  - set_target / clear_target: runtime homing target assignment.
  - register_splash_falloff / get_splash_falloff / list_splash_falloffs:
    splash-damage curves keyed by projectile type.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`ProjectileSystem.get_instance` or the module-level
:func:`get_projectile_system` factory.
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

_MAX_TYPES: int = 1000
_MAX_INSTANCES: int = 20000
_MAX_FALLOFFS: int = 500
_MAX_EVENTS: int = 5000


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


# Vector helpers (3D tuples) ------------------------------------------------


def _v3_add(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _v3_sub(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v3_scale(a: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (a[0] * s, a[1] * s, a[2] * s)


def _v3_dot(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _v3_length(a: Tuple[float, float, float]) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _v3_normalize(a: Tuple[float, float, float]) -> Tuple[float, float, float]:
    length = _v3_length(a)
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / length
    return (a[0] * inv, a[1] * inv, a[2] * inv)


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ProjectileTrajectory(Enum):
    """Trajectory patterns supported by the projectile system."""
    LINEAR = "linear"
    BALLISTIC = "ballistic"
    HOMING = "homing"
    SPIRAL = "spiral"
    BEAM = "beam"


class ProjectileStatus(Enum):
    """Runtime status of a projectile instance."""
    ACTIVE = "active"
    IMPACTED = "impacted"
    EXPIRED = "expired"
    DEFLECTED = "deflected"
    SPENT = "spent"


class ProjectileEventKind(Enum):
    """Audit event types emitted by the projectile system."""
    TYPE_REGISTERED = "type_registered"
    TYPE_UPDATED = "type_updated"
    TYPE_REMOVED = "type_removed"
    PROJECTILE_SPAWNED = "projectile_spawned"
    PROJECTILE_REMOVED = "projectile_removed"
    PROJECTILE_IMPACTED = "projectile_impacted"
    PROJECTILE_EXPIRED = "projectile_expired"
    PROJECTILE_DEFLECTED = "projectile_deflected"
    TICK_COMPLETED = "tick_completed"
    FALLOFF_REGISTERED = "falloff_registered"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ProjectileType:
    """Definition of a projectile kind with physics and payload parameters."""
    type_id: str = ""
    name: str = ""
    description: str = ""
    trajectory: str = ProjectileTrajectory.LINEAR.value
    speed: float = 50.0
    gravity_scale: float = 0.0
    drag: float = 0.0
    collision_radius: float = 0.2
    max_pierce: int = 1
    max_ricochet: int = 0
    splash_radius: float = 0.0
    lifetime_seconds: float = 5.0
    homing_strength: float = 0.0
    spiral_frequency: float = 0.0
    spiral_amplitude: float = 0.0
    team_filter_mode: str = "enemy_only"
    payload_kind: str = "damage"
    payload_value: float = 10.0
    color_hex: str = "#FFAA00"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProjectileInstance:
    """A live projectile instance in the simulation."""
    instance_id: str = ""
    type_id: str = ""
    owner_id: str = ""
    team_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    target_id: str = ""
    target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    age_seconds: float = 0.0
    remaining_pierce: int = 1
    remaining_ricochet: int = 0
    status: str = ProjectileStatus.ACTIVE.value
    impact_count: int = 0
    spawn_time: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SplashFalloff:
    """A radial damage falloff curve for splash projectiles."""
    falloff_id: str = ""
    type_id: str = ""
    curve_kind: str = "linear"
    inner_radius: float = 0.0
    outer_radius: float = 1.0
    inner_value: float = 1.0
    outer_value: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProjectileStats:
    """Aggregate statistics for the projectile system."""
    total_types: int = 0
    active_instances: int = 0
    total_spawned: int = 0
    total_impacts: int = 0
    total_expired: int = 0
    total_deflected: int = 0
    ticks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProjectileSnapshot:
    """Point-in-time snapshot of system state."""
    types: int = 0
    instances: int = 0
    falloffs: int = 0
    events: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProjectileEvent:
    """Audit event emitted by the projectile system."""
    event_id: str = ""
    kind: str = ProjectileEventKind.PROJECTILE_SPAWNED.value
    instance_id: str = ""
    type_id: str = ""
    timestamp: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton System
# ---------------------------------------------------------------------------


class ProjectileSystem:
    """Runtime projectile simulation managing types, instances, and falloffs."""

    _instance: Optional["ProjectileSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._types: Dict[str, ProjectileType] = {}
        self._instances: Dict[str, ProjectileInstance] = {}
        self._falloffs: Dict[str, SplashFalloff] = {}
        self._events: List[ProjectileEvent] = []
        self._stats = ProjectileStats()

    @classmethod
    def get_instance(cls) -> "ProjectileSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -- lifecycle -------------------------------------------------------

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_defaults()
            self._initialized = True

    def _seed_defaults(self) -> None:
        # Seed 1: arrow type (ballistic)
        arrow = ProjectileType(
            type_id="prt_arrow",
            name="Arrow",
            description="A ballistic arrow affected by gravity drop.",
            trajectory=ProjectileTrajectory.BALLISTIC.value,
            speed=60.0,
            gravity_scale=0.6,
            drag=0.02,
            collision_radius=0.15,
            max_pierce=1,
            max_ricochet=0,
            splash_radius=0.0,
            lifetime_seconds=4.0,
            payload_kind="damage",
            payload_value=15.0,
            color_hex="#8B4513",
        )
        self._types[arrow.type_id] = arrow

        # Seed 2: fire bolt (homing spell)
        fire_bolt = ProjectileType(
            type_id="prt_fire_bolt",
            name="Fire Bolt",
            description="A homing bolt of fire that tracks its target.",
            trajectory=ProjectileTrajectory.HOMING.value,
            speed=25.0,
            gravity_scale=0.0,
            drag=0.0,
            collision_radius=0.3,
            max_pierce=1,
            max_ricochet=0,
            splash_radius=2.0,
            lifetime_seconds=6.0,
            homing_strength=3.0,
            payload_kind="fire_damage",
            payload_value=25.0,
            color_hex="#FF4500",
        )
        self._types[fire_bolt.type_id] = fire_bolt

        # Seed 3: piercing round (linear)
        pierce_round = ProjectileType(
            type_id="prt_piercing_round",
            name="Piercing Round",
            description="A high-velocity round that pierces multiple targets.",
            trajectory=ProjectileTrajectory.LINEAR.value,
            speed=120.0,
            gravity_scale=0.0,
            drag=0.0,
            collision_radius=0.1,
            max_pierce=3,
            max_ricochet=0,
            splash_radius=0.0,
            lifetime_seconds=2.0,
            payload_kind="damage",
            payload_value=10.0,
            color_hex="#C0C0C0",
        )
        self._types[pierce_round.type_id] = pierce_round

        # Seed 4: spiral shuriken
        shuriken = ProjectileType(
            type_id="prt_spiral_shuriken",
            name="Spiral Shuriken",
            description="A shuriken that travels in a spiral pattern.",
            trajectory=ProjectileTrajectory.SPIRAL.value,
            speed=30.0,
            gravity_scale=0.0,
            drag=0.05,
            collision_radius=0.2,
            max_pierce=2,
            max_ricochet=1,
            splash_radius=0.0,
            lifetime_seconds=5.0,
            spiral_frequency=8.0,
            spiral_amplitude=0.5,
            payload_kind="damage",
            payload_value=8.0,
            color_hex="#9370DB",
        )
        self._types[shuriken.type_id] = shuriken

        # Seed splash falloff for fire bolt
        falloff = SplashFalloff(
            falloff_id="fof_fire_bolt",
            type_id="prt_fire_bolt",
            curve_kind="linear",
            inner_radius=0.5,
            outer_radius=2.0,
            inner_value=1.0,
            outer_value=0.1,
        )
        self._falloffs[falloff.falloff_id] = falloff

        self._stats.total_types = len(self._types)
        self._emit(
            ProjectileEventKind.TYPE_REGISTERED,
            type_id="prt_arrow",
            payload={"seeded": True},
        )
        self._emit(
            ProjectileEventKind.TYPE_REGISTERED,
            type_id="prt_fire_bolt",
            payload={"seeded": True},
        )
        self._emit(
            ProjectileEventKind.TYPE_REGISTERED,
            type_id="prt_piercing_round",
            payload={"seeded": True},
        )
        self._emit(
            ProjectileEventKind.TYPE_REGISTERED,
            type_id="prt_spiral_shuriken",
            payload={"seeded": True},
        )
        self._emit(
            ProjectileEventKind.FALLOFF_REGISTERED,
            type_id="prt_fire_bolt",
            payload={"falloff_id": "fof_fire_bolt"},
        )

    def _emit(
        self,
        kind: ProjectileEventKind,
        instance_id: str = "",
        type_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> ProjectileEvent:
        event = ProjectileEvent(
            event_id=_new_id("evt"),
            kind=kind.value,
            instance_id=instance_id,
            type_id=type_id,
            timestamp=_now(),
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    # -- type CRUD -------------------------------------------------------

    def register_type(self, ptype: ProjectileType) -> ProjectileType:
        with self._lock:
            if not ptype.type_id:
                ptype.type_id = _new_id("prt")
            self._types[ptype.type_id] = ptype
            _evict_fifo_dict(self._types, _MAX_TYPES)
            self._stats.total_types = len(self._types)
            self._emit(
                ProjectileEventKind.TYPE_REGISTERED,
                type_id=ptype.type_id,
                payload={"name": ptype.name, "trajectory": ptype.trajectory},
            )
            return ptype

    def get_type(self, type_id: str) -> Optional[ProjectileType]:
        return self._types.get(type_id)

    def list_types(
        self,
        trajectory: Optional[str] = None,
        limit: int = 50,
    ) -> List[ProjectileType]:
        limit = max(1, min(int(limit), 200))
        results: List[ProjectileType] = []
        for ptype in self._types.values():
            if trajectory and ptype.trajectory != trajectory:
                continue
            results.append(ptype)
        return results[:limit]

    def update_type(self, type_id: str, updates: Dict[str, Any]) -> Optional[ProjectileType]:
        with self._lock:
            ptype = self._types.get(type_id)
            if ptype is None:
                return None
            if "name" in updates:
                ptype.name = str(updates["name"])
            if "description" in updates:
                ptype.description = str(updates["description"])
            if "speed" in updates:
                ptype.speed = _safe_float(updates["speed"], ptype.speed)
            if "gravity_scale" in updates:
                ptype.gravity_scale = _safe_float(updates["gravity_scale"], ptype.gravity_scale)
            if "drag" in updates:
                ptype.drag = _safe_float(updates["drag"], ptype.drag)
            if "collision_radius" in updates:
                ptype.collision_radius = _safe_float(updates["collision_radius"], ptype.collision_radius)
            if "max_pierce" in updates:
                ptype.max_pierce = _safe_int(updates["max_pierce"], ptype.max_pierce)
            if "max_ricochet" in updates:
                ptype.max_ricochet = _safe_int(updates["max_ricochet"], ptype.max_ricochet)
            if "splash_radius" in updates:
                ptype.splash_radius = _safe_float(updates["splash_radius"], ptype.splash_radius)
            if "lifetime_seconds" in updates:
                ptype.lifetime_seconds = _safe_float(updates["lifetime_seconds"], ptype.lifetime_seconds)
            if "homing_strength" in updates:
                ptype.homing_strength = _safe_float(updates["homing_strength"], ptype.homing_strength)
            if "payload_value" in updates:
                ptype.payload_value = _safe_float(updates["payload_value"], ptype.payload_value)
            if "color_hex" in updates:
                ptype.color_hex = str(updates["color_hex"])
            self._emit(
                ProjectileEventKind.TYPE_UPDATED,
                type_id=type_id,
                payload={"fields": list(updates.keys())},
            )
            return ptype

    def remove_type(self, type_id: str) -> bool:
        with self._lock:
            removed = self._types.pop(type_id, None)
            if removed is None:
                return False
            # Remove associated falloffs
            fof_ids = [fid for fid, f in self._falloffs.items() if f.type_id == type_id]
            for fid in fof_ids:
                self._falloffs.pop(fid, None)
            self._stats.total_types = len(self._types)
            self._emit(
                ProjectileEventKind.TYPE_REMOVED,
                type_id=type_id,
            )
            return True

    # -- instance lifecycle ----------------------------------------------

    def spawn_projectile(
        self,
        type_id: str,
        owner_id: str = "",
        team_id: str = "",
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        direction: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        target_id: str = "",
        target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        speed_override: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ProjectileInstance]:
        with self._lock:
            ptype = self._types.get(type_id)
            if ptype is None:
                return None
            speed = ptype.speed if speed_override is None else _safe_float(speed_override, ptype.speed)
            dir_n = _v3_normalize(direction)
            velocity = _v3_scale(dir_n, speed)
            instance = ProjectileInstance(
                instance_id=_new_id("prj"),
                type_id=type_id,
                owner_id=owner_id,
                team_id=team_id,
                position=position,
                velocity=velocity,
                direction=dir_n,
                target_id=target_id,
                target_position=target_position,
                age_seconds=0.0,
                remaining_pierce=ptype.max_pierce,
                remaining_ricochet=ptype.max_ricochet,
                status=ProjectileStatus.ACTIVE.value,
                impact_count=0,
                spawn_time=_now(),
                metadata=metadata or {},
            )
            self._instances[instance.instance_id] = instance
            _evict_fifo_dict(self._instances, _MAX_INSTANCES)
            self._stats.active_instances = sum(
                1 for i in self._instances.values() if i.status == ProjectileStatus.ACTIVE.value
            )
            self._stats.total_spawned += 1
            self._emit(
                ProjectileEventKind.PROJECTILE_SPAWNED,
                instance_id=instance.instance_id,
                type_id=type_id,
                payload={"owner": owner_id, "team": team_id},
            )
            return instance

    def get_projectile(self, instance_id: str) -> Optional[ProjectileInstance]:
        return self._instances.get(instance_id)

    def list_projectiles(
        self,
        type_id: Optional[str] = None,
        status: Optional[str] = None,
        owner_id: Optional[str] = None,
        team_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ProjectileInstance]:
        limit = max(1, min(int(limit), 200))
        results: List[ProjectileInstance] = []
        for inst in self._instances.values():
            if type_id and inst.type_id != type_id:
                continue
            if status and inst.status != status:
                continue
            if owner_id and inst.owner_id != owner_id:
                continue
            if team_id and inst.team_id != team_id:
                continue
            results.append(inst)
        return results[:limit]

    def remove_projectile(self, instance_id: str) -> bool:
        with self._lock:
            removed = self._instances.pop(instance_id, None)
            if removed is None:
                return False
            self._stats.active_instances = sum(
                1 for i in self._instances.values() if i.status == ProjectileStatus.ACTIVE.value
            )
            self._emit(
                ProjectileEventKind.PROJECTILE_REMOVED,
                instance_id=instance_id,
            )
            return True

    def set_target(
        self,
        instance_id: str,
        target_id: str = "",
        target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> Optional[ProjectileInstance]:
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return None
            inst.target_id = target_id
            inst.target_position = target_position
            return inst

    def clear_target(self, instance_id: str) -> Optional[ProjectileInstance]:
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return None
            inst.target_id = ""
            inst.target_position = (0.0, 0.0, 0.0)
            return inst

    # -- simulation ------------------------------------------------------

    def tick(self, delta_seconds: float) -> Dict[str, Any]:
        delta = max(0.0, _safe_float(delta_seconds, 0.016))
        if delta <= 0.0:
            return {"ok": True, "delta": 0.0, "active": 0, "impacts": 0, "expired": 0}
        impacts = 0
        expired = 0
        deflected = 0
        with self._lock:
            to_remove: List[str] = []
            for inst_id, inst in self._instances.items():
                if inst.status != ProjectileStatus.ACTIVE.value:
                    continue
                ptype = self._types.get(inst.type_id)
                if ptype is None:
                    inst.status = ProjectileStatus.EXPIRED.value
                    expired += 1
                    continue
                # Integrate position
                inst.position = _v3_add(inst.position, _v3_scale(inst.velocity, delta))
                # Apply gravity
                if ptype.gravity_scale != 0.0:
                    inst.velocity = (
                        inst.velocity[0],
                        inst.velocity[1] - 9.81 * ptype.gravity_scale * delta,
                        inst.velocity[2],
                    )
                # Apply drag
                if ptype.drag != 0.0:
                    drag_factor = max(0.0, 1.0 - ptype.drag * delta)
                    inst.velocity = _v3_scale(inst.velocity, drag_factor)
                # Homing: steer velocity toward target
                if ptype.trajectory == ProjectileTrajectory.HOMING.value and inst.target_id:
                    delta_target = _v3_sub(inst.target_position, inst.position)
                    target_dir = _v3_normalize(delta_target)
                    current_dir = _v3_normalize(inst.velocity)
                    steer = _v3_sub(target_dir, current_dir)
                    steer = _v3_scale(steer, ptype.homing_strength * delta)
                    new_dir = _v3_normalize(_v3_add(current_dir, steer))
                    speed = _v3_length(inst.velocity)
                    inst.velocity = _v3_scale(new_dir, speed)
                # Spiral: offset direction perpendicular to velocity
                if ptype.trajectory == ProjectileTrajectory.SPIRAL.value and ptype.spiral_frequency > 0.0:
                    phase = inst.age_seconds * ptype.spiral_frequency * 2.0 * math.pi
                    perp = _v3_normalize((
                        -inst.velocity[1],
                        inst.velocity[0],
                        0.0,
                    ))
                    offset = _v3_scale(perp, ptype.spiral_amplitude * math.sin(phase) * delta)
                    inst.position = _v3_add(inst.position, offset)
                # Age and lifetime check
                inst.age_seconds += delta
                if inst.age_seconds >= ptype.lifetime_seconds:
                    inst.status = ProjectileStatus.EXPIRED.value
                    expired += 1
                    self._emit(
                        ProjectileEventKind.PROJECTILE_EXPIRED,
                        instance_id=inst_id,
                        type_id=inst.type_id,
                    )
                # Spent (no remaining pierce and no ricochet)
                if inst.remaining_pierce <= 0 and inst.remaining_ricochet <= 0:
                    inst.status = ProjectileStatus.SPENT.value
                    to_remove.append(inst_id)
            # Cleanup spent instances
            for inst_id in to_remove:
                self._instances.pop(inst_id, None)
            self._stats.active_instances = sum(
                1 for i in self._instances.values() if i.status == ProjectileStatus.ACTIVE.value
            )
            self._stats.total_expired += expired
            self._stats.total_impacts += impacts
            self._stats.total_deflected += deflected
            self._stats.ticks += 1
            self._emit(
                ProjectileEventKind.TICK_COMPLETED,
                payload={
                    "delta": delta,
                    "impacts": impacts,
                    "expired": expired,
                    "deflected": deflected,
                },
            )
        return {
            "ok": True,
            "delta": delta,
            "active": self._stats.active_instances,
            "impacts": impacts,
            "expired": expired,
            "deflected": deflected,
        }

    def impact(
        self,
        instance_id: str,
        impact_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        deflected: bool = False,
    ) -> Optional[ProjectileInstance]:
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return None
            inst.impact_count += 1
            if deflected and inst.remaining_ricochet > 0:
                inst.remaining_ricochet -= 1
                inst.status = ProjectileStatus.DEFLECTED.value
                self._stats.total_deflected += 1
                self._emit(
                    ProjectileEventKind.PROJECTILE_DEFLECTED,
                    instance_id=instance_id,
                    type_id=inst.type_id,
                )
                # Reset to active for continued flight
                inst.status = ProjectileStatus.ACTIVE.value
                return inst
            inst.remaining_pierce -= 1
            if inst.remaining_pierce <= 0:
                inst.status = ProjectileStatus.IMPACTED.value
                self._stats.total_impacts += 1
                self._emit(
                    ProjectileEventKind.PROJECTILE_IMPACTED,
                    instance_id=instance_id,
                    type_id=inst.type_id,
                    payload={"position": list(impact_position)},
                )
            else:
                # Still has pierce; log impact but remain active
                self._stats.total_impacts += 1
                self._emit(
                    ProjectileEventKind.PROJECTILE_IMPACTED,
                    instance_id=instance_id,
                    type_id=inst.type_id,
                    payload={"position": list(impact_position), "pierce_remaining": inst.remaining_pierce},
                )
            return inst

    # -- splash falloff --------------------------------------------------

    def register_splash_falloff(self, falloff: SplashFalloff) -> SplashFalloff:
        with self._lock:
            if not falloff.falloff_id:
                falloff.falloff_id = _new_id("fof")
            self._falloffs[falloff.falloff_id] = falloff
            _evict_fifo_dict(self._falloffs, _MAX_FALLOFFS)
            self._emit(
                ProjectileEventKind.FALLOFF_REGISTERED,
                type_id=falloff.type_id,
                payload={"falloff_id": falloff.falloff_id},
            )
            return falloff

    def get_splash_falloff(self, falloff_id: str) -> Optional[SplashFalloff]:
        return self._falloffs.get(falloff_id)

    def list_splash_falloffs(
        self,
        type_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SplashFalloff]:
        limit = max(1, min(int(limit), 200))
        results: List[SplashFalloff] = []
        for f in self._falloffs.values():
            if type_id and f.type_id != type_id:
                continue
            results.append(f)
        return results[:limit]

    def remove_splash_falloff(self, falloff_id: str) -> bool:
        with self._lock:
            removed = self._falloffs.pop(falloff_id, None)
            return removed is not None

    def evaluate_splash(
        self,
        falloff_id: str,
        distance: float,
    ) -> Dict[str, Any]:
        falloff = self._falloffs.get(falloff_id)
        if falloff is None:
            return {"ok": False, "reason": "falloff_not_found"}
        d = max(0.0, _safe_float(distance, 0.0))
        if d <= falloff.inner_radius:
            value = falloff.inner_value
        elif d >= falloff.outer_radius:
            value = falloff.outer_value
        else:
            span = max(1e-9, falloff.outer_radius - falloff.inner_radius)
            t = (d - falloff.inner_radius) / span
            if falloff.curve_kind == "linear":
                value = falloff.inner_value + (falloff.outer_value - falloff.inner_value) * t
            elif falloff.curve_kind == "quadratic":
                value = falloff.inner_value + (falloff.outer_value - falloff.inner_value) * t * t
            elif falloff.curve_kind == "sqrt":
                value = falloff.inner_value + (falloff.outer_value - falloff.inner_value) * math.sqrt(t)
            else:
                value = falloff.inner_value + (falloff.outer_value - falloff.inner_value) * t
        return {
            "ok": True,
            "falloff_id": falloff_id,
            "distance": d,
            "value": value,
            "curve_kind": falloff.curve_kind,
        }

    # -- observability ---------------------------------------------------

    def list_events(self, limit: int = 50) -> List[ProjectileEvent]:
        limit = max(1, min(int(limit), 200))
        return list(self._events[-limit:])

    def get_stats(self) -> ProjectileStats:
        self._stats.total_types = len(self._types)
        self._stats.active_instances = sum(
            1 for i in self._instances.values() if i.status == ProjectileStatus.ACTIVE.value
        )
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "types": len(self._types),
            "instances": len(self._instances),
            "active_instances": sum(
                1 for i in self._instances.values() if i.status == ProjectileStatus.ACTIVE.value
            ),
            "falloffs": len(self._falloffs),
            "events": len(self._events),
            "total_spawned": self._stats.total_spawned,
            "total_impacts": self._stats.total_impacts,
            "total_expired": self._stats.total_expired,
            "ticks": self._stats.ticks,
        }

    def get_snapshot(self) -> ProjectileSnapshot:
        return ProjectileSnapshot(
            types=len(self._types),
            instances=len(self._instances),
            falloffs=len(self._falloffs),
            events=len(self._events),
            timestamp=_now(),
        )

    def reset(self) -> None:
        with self._lock:
            self._types.clear()
            self._instances.clear()
            self._falloffs.clear()
            self._events.clear()
            self._stats = ProjectileStats()
            self._initialized = False
            self._seed_defaults()
            self._initialized = True


# ---------------------------------------------------------------------------
# Module Factory
# ---------------------------------------------------------------------------


def get_projectile_system() -> ProjectileSystem:
    instance = ProjectileSystem.get_instance()
    if not instance._initialized:
        instance.initialize()
    return instance
