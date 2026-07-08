"""
SparkLabs Engine - Trigger Volume System

Manages spatial trigger regions that fire events when entities enter,
exit, or remain inside them. Supports box, sphere, cylinder, and
capsule shapes with one-shot, repeat, and conditional trigger modes.

Designed for level transitions, cutscene triggers, pressure plates,
area-based encounters, damage zones, checkpoint activations, and
interactive object proximity detection. Integrates with the scene
query system, event bus, and entity component system.
"""

from __future__ import annotations

import math
import threading
import time
import uuid as _uuid
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


def _length3(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


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

_MAX_VOLUMES = 3000
_MAX_OCCUPANTS = 10000
_MAX_EVENTS = 5000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VolumeShape(str, Enum):
    """Geometric shape of the trigger volume."""
    BOX = "box"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    CAPSULE = "capsule"
    PLANE = "plane"


class TriggerMode(str, Enum):
    """How the trigger fires when entities are inside."""
    ONESHOT = "oneshot"
    REPEAT = "repeat"
    CONTINUOUS = "continuous"
    PULSE = "pulse"


class TriggerState(str, Enum):
    """Operational state of a trigger volume."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    COOLDOWN = "cooldown"


class TriggerEventKind(str, Enum):
    VOLUME_REGISTERED = "volume_registered"
    VOLUME_REMOVED = "volume_removed"
    VOLUME_ENABLED = "volume_enabled"
    VOLUME_DISABLED = "volume_disabled"
    ENTITY_ENTERED = "entity_entered"
    ENTITY_EXITED = "entity_exited"
    TRIGGER_FIRED = "trigger_fired"
    TRIGGER_RESET = "trigger_reset"
    COOLDOWN_STARTED = "cooldown_started"
    COOLDOWN_ENDED = "cooldown_ended"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class VolumeGeometry:
    """Geometric description of the trigger region."""
    shape: str = VolumeShape.BOX.value
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    size: Tuple[float, float, float] = (5.0, 5.0, 5.0)
    radius: float = 5.0
    height: float = 5.0
    rotation_yaw: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TriggerCondition:
    """Optional condition that must be met for the trigger to fire."""
    condition_id: str = ""
    required_tag: str = ""
    required_property: str = ""
    required_value: float = 0.0
    min_entity_count: int = 1
    max_entity_count: int = 9999
    require_all_tags: bool = False
    invert: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TriggerVolume:
    """A single trigger volume definition."""
    volume_id: str
    name: str = ""
    shape: str = VolumeShape.BOX.value
    geometry: VolumeGeometry = field(default_factory=VolumeGeometry)
    mode: str = TriggerMode.REPEAT.value
    state: str = TriggerState.ACTIVE.value
    enabled: bool = True
    cooldown_seconds: float = 0.0
    pulse_interval: float = 1.0
    max_activations: int = 0
    activation_count: int = 0
    last_fire_time: float = 0.0
    last_pulse_time: float = 0.0
    filter_tags: List[str] = field(default_factory=list)
    filter_entity_ids: List[str] = field(default_factory=list)
    exclude_entity_ids: List[str] = field(default_factory=list)
    condition: TriggerCondition = field(default_factory=TriggerCondition)
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OccupantRecord:
    """Tracks an entity currently inside a trigger volume."""
    entity_id: str
    volume_id: str
    entered_at: float
    last_pulse_at: float = 0.0
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TriggerActivation:
    """Record of a single trigger activation."""
    activation_id: str
    volume_id: str
    entity_id: str
    timestamp: float
    event_kind: str = TriggerEventKind.TRIGGER_FIRED.value
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TriggerConfig:
    max_volumes: int = 500
    max_occupants_per_volume: int = 100
    default_cooldown: float = 1.0
    default_pulse_interval: float = 1.0
    auto_expire: bool = True
    expire_after_seconds: float = 0.0
    enable_conditions: bool = True
    tick_rate_hz: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TriggerStats:
    total_volumes: int = 0
    active_volumes: int = 0
    inactive_volumes: int = 0
    expired_volumes: int = 0
    total_activations: int = 0
    total_entered: int = 0
    total_exited: int = 0
    current_occupants: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TriggerSnapshot:
    volumes: List[Dict[str, Any]] = field(default_factory=list)
    occupants: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TriggerEvent:
    event_id: str
    kind: str
    timestamp: float
    volume_id: Optional[str] = None
    entity_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Trigger Volume System
# ---------------------------------------------------------------------------

class TriggerVolumeSystem:
    """Manages spatial trigger volumes and entity occupancy tracking."""

    _instance: Optional["TriggerVolumeSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._volumes: Dict[str, TriggerVolume] = {}
        self._occupants: Dict[str, List[OccupantRecord]] = {}
        self._activations: List[TriggerActivation] = []
        self._events: List[TriggerEvent] = []
        self._stats = TriggerStats()
        self._config = TriggerConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._activation_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "TriggerVolumeSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample trigger volumes for demonstration."""
        checkpoint = TriggerVolume(
            volume_id="trg_checkpoint_start",
            name="Starting Checkpoint",
            shape=VolumeShape.BOX.value,
            geometry=VolumeGeometry(
                shape=VolumeShape.BOX.value,
                center=(0.0, 0.0, 0.0),
                size=(4.0, 4.0, 4.0),
            ),
            mode=TriggerMode.ONESHOT.value,
            state=TriggerState.ACTIVE.value,
            cooldown_seconds=2.0,
            payload={"action": "set_checkpoint", "checkpoint_id": "cp_start"},
        )
        self._volumes[checkpoint.volume_id] = checkpoint
        self._occupants[checkpoint.volume_id] = []

        damage_zone = TriggerVolume(
            volume_id="trg_lava_pool",
            name="Lava Damage Zone",
            shape=VolumeShape.SPHERE.value,
            geometry=VolumeGeometry(
                shape=VolumeShape.SPHERE.value,
                center=(50.0, 0.0, 30.0),
                size=(0.0, 0.0, 0.0),
                radius=6.0,
            ),
            mode=TriggerMode.PULSE.value,
            state=TriggerState.ACTIVE.value,
            pulse_interval=0.5,
            payload={"action": "apply_damage", "damage": 10.0, "damage_type": "fire"},
        )
        self._volumes[damage_zone.volume_id] = damage_zone
        self._occupants[damage_zone.volume_id] = []

        level_transition = TriggerVolume(
            volume_id="trg_level_transition_01",
            name="Dungeon Entrance",
            shape=VolumeShape.CYLINDER.value,
            geometry=VolumeGeometry(
                shape=VolumeShape.CYLINDER.value,
                center=(100.0, 0.0, 0.0),
                size=(0.0, 0.0, 0.0),
                radius=3.0,
                height=5.0,
            ),
            mode=TriggerMode.ONESHOT.value,
            state=TriggerState.ACTIVE.value,
            cooldown_seconds=5.0,
            filter_tags=["player"],
            payload={"action": "load_level", "level_id": "dungeon_01"},
        )
        self._volumes[level_transition.volume_id] = level_transition
        self._occupants[level_transition.volume_id] = []

        self._stats.total_volumes = len(self._volumes)
        self._stats.active_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.ACTIVE.value)
        self._stats.inactive_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.INACTIVE.value)
        self._stats.expired_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.EXPIRED.value)
        self._initialized = True

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"tevt_{self._event_counter:08d}"

    def _next_activation_id(self) -> str:
        self._activation_counter += 1
        return f"tact_{self._activation_counter:08d}"

    def _record_event(self, kind: str, **kwargs: Any) -> TriggerEvent:
        event = TriggerEvent(
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
    # Volume Management
    # ------------------------------------------------------------------

    def register_volume(self, volume: TriggerVolume) -> Dict[str, Any]:
        if len(self._volumes) >= _MAX_VOLUMES and volume.volume_id not in self._volumes:
            oldest_id = next(iter(self._volumes))
            self._volumes.pop(oldest_id, None)
            self._occupants.pop(oldest_id, None)
        was_new = volume.volume_id not in self._volumes
        self._volumes[volume.volume_id] = volume
        if was_new:
            self._occupants[volume.volume_id] = []
        self._stats.total_volumes = len(self._volumes)
        self._stats.active_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.ACTIVE.value)
        self._stats.inactive_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.INACTIVE.value)
        self._stats.expired_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.EXPIRED.value)
        self._record_event(
            TriggerEventKind.VOLUME_REGISTERED if was_new else TriggerEventKind.CONFIG_UPDATED,
            volume_id=volume.volume_id,
            details={"name": volume.name, "shape": volume.shape, "mode": volume.mode},
        )
        return {"volume_id": volume.volume_id, "registered": True}

    def remove_volume(self, volume_id: str) -> Dict[str, Any]:
        if volume_id not in self._volumes:
            return {"volume_id": volume_id, "removed": False, "reason": "not found"}
        self._volumes.pop(volume_id)
        self._occupants.pop(volume_id, None)
        self._stats.total_volumes = len(self._volumes)
        self._stats.active_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.ACTIVE.value)
        self._stats.inactive_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.INACTIVE.value)
        self._stats.expired_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.EXPIRED.value)
        self._stats.current_occupants = sum(len(occ) for occ in self._occupants.values())
        self._record_event(TriggerEventKind.VOLUME_REMOVED, volume_id=volume_id)
        return {"volume_id": volume_id, "removed": True}

    def get_volume(self, volume_id: str) -> Optional[TriggerVolume]:
        return self._volumes.get(volume_id)

    def list_volumes(self, shape: Optional[str] = None, mode: Optional[str] = None, state: Optional[str] = None, enabled: Optional[bool] = None, limit: int = 100) -> List[TriggerVolume]:
        results: List[TriggerVolume] = []
        for v in self._volumes.values():
            if shape is not None and v.shape != shape:
                continue
            if mode is not None and v.mode != mode:
                continue
            if state is not None and v.state != state:
                continue
            if enabled is not None and v.enabled != enabled:
                continue
            results.append(v)
        return results[:max(0, min(limit, len(results)))]

    def enable_volume(self, volume_id: str, enabled: bool) -> Dict[str, Any]:
        v = self._volumes.get(volume_id)
        if v is None:
            return {"volume_id": volume_id, "updated": False, "reason": "not found"}
        v.enabled = enabled
        v.updated_at = _now()
        self._record_event(
            TriggerEventKind.VOLUME_ENABLED if enabled else TriggerEventKind.VOLUME_DISABLED,
            volume_id=volume_id,
        )
        return {"volume_id": volume_id, "enabled": enabled}

    def reset_volume(self, volume_id: str) -> Dict[str, Any]:
        v = self._volumes.get(volume_id)
        if v is None:
            return {"volume_id": volume_id, "reset": False, "reason": "not found"}
        v.activation_count = 0
        v.state = TriggerState.ACTIVE.value
        v.last_fire_time = 0.0
        v.last_pulse_time = 0.0
        v.updated_at = _now()
        self._occupants[volume_id] = []
        self._record_event(TriggerEventKind.TRIGGER_RESET, volume_id=volume_id)
        return {"volume_id": volume_id, "reset": True}

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------

    def _point_in_geometry(self, geom: VolumeGeometry, point: Tuple[float, float, float]) -> bool:
        shape = geom.shape
        if shape == VolumeShape.SPHERE.value:
            d = _length3(_sub3(point, geom.center))
            return d <= geom.radius
        if shape == VolumeShape.BOX.value:
            for i in range(3):
                half = geom.size[i] * 0.5
                if abs(point[i] - geom.center[i]) > half:
                    return False
            return True
        if shape == VolumeShape.CYLINDER.value:
            dx = point[0] - geom.center[0]
            dz = point[2] - geom.center[2]
            radial = math.sqrt(dx * dx + dz * dz)
            if radial > geom.radius:
                return False
            half_h = geom.height * 0.5
            if abs(point[1] - geom.center[1]) > half_h:
                return False
            return True
        if shape == VolumeShape.CAPSULE.value:
            dx = point[0] - geom.center[0]
            dz = point[2] - geom.center[2]
            radial = math.sqrt(dx * dx + dz * dz)
            if radial > geom.radius:
                return False
            half_h = geom.height * 0.5
            y_rel = point[1] - geom.center[1]
            if -half_h <= y_rel <= half_h:
                return True
            cap_offset = half_h if y_rel > 0 else -half_h
            cap_center = (geom.center[0], geom.center[1] + cap_offset, geom.center[2])
            d = _length3(_sub3(point, cap_center))
            return d <= geom.radius
        if shape == VolumeShape.PLANE.value:
            return abs(point[1] - geom.center[1]) <= geom.height * 0.5
        return False

    def _entity_passes_filter(self, volume: TriggerVolume, entity_id: str, tags: List[str]) -> bool:
        if volume.exclude_entity_ids and entity_id in volume.exclude_entity_ids:
            return False
        if volume.filter_entity_ids and entity_id not in volume.filter_entity_ids:
            return False
        if volume.filter_tags:
            if volume.condition.require_all_tags:
                if not all(t in tags for t in volume.filter_tags):
                    return False
            else:
                if not any(t in tags for t in volume.filter_tags):
                    return False
        return True

    def _check_condition(self, volume: TriggerVolume, occupant_count: int) -> bool:
        cond = volume.condition
        if not self._config.enable_conditions or not cond.condition_id:
            return True
        passes = True
        if cond.min_entity_count > 0:
            passes = passes and occupant_count >= cond.min_entity_count
        if cond.max_entity_count < 9999:
            passes = passes and occupant_count <= cond.max_entity_count
        if cond.invert:
            passes = not passes
        return passes

    # ------------------------------------------------------------------
    # Entity update
    # ------------------------------------------------------------------

    def update_entity(self, entity_id: str, position: Tuple[float, float, float], tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Update an entity's position and process trigger enter/exit/pulse events."""
        if tags is None:
            tags = []
        entered: List[str] = []
        exited: List[str] = []
        fired: List[Dict[str, Any]] = []
        now = _now()

        for volume in self._volumes.values():
            if not volume.enabled:
                continue
            in_volume = self._point_in_geometry(volume.geometry, position)
            if not self._entity_passes_filter(volume, entity_id, tags):
                continue

            occupants = self._occupants.get(volume.volume_id, [])
            existing = None
            for occ in occupants:
                if occ.entity_id == entity_id:
                    existing = occ
                    break

            # Process exit even for expired volumes
            if existing is not None and not in_volume:
                occupants.remove(existing)
                self._occupants[volume.volume_id] = occupants
                self._stats.total_exited += 1
                exited.append(volume.volume_id)
                self._record_event(
                    TriggerEventKind.ENTITY_EXITED,
                    volume_id=volume.volume_id,
                    entity_id=entity_id,
                    details={"position": list(position)},
                )
                continue

            # Skip enter/pulse for expired volumes
            if volume.state == TriggerState.EXPIRED.value:
                continue

            if in_volume and existing is None:
                # Entity entered
                if len(occupants) >= self._config.max_occupants_per_volume:
                    occupants.pop(0)
                record = OccupantRecord(
                    entity_id=entity_id,
                    volume_id=volume.volume_id,
                    entered_at=now,
                    last_pulse_at=now,
                    position=position,
                    tags=list(tags),
                )
                occupants.append(record)
                self._occupants[volume.volume_id] = occupants
                self._stats.total_entered += 1
                entered.append(volume.volume_id)
                self._record_event(
                    TriggerEventKind.ENTITY_ENTERED,
                    volume_id=volume.volume_id,
                    entity_id=entity_id,
                    details={"position": list(position)},
                )
                # Fire trigger for enter mode
                if self._can_fire(volume, now):
                    activation = self._fire(volume, entity_id, position, now)
                    fired.append(activation.to_dict())

            elif in_volume and existing is not None:
                existing.position = position
                existing.tags = list(tags)
                # Pulse mode: fire at intervals
                if volume.mode == TriggerMode.PULSE.value:
                    if now - existing.last_pulse_at >= volume.pulse_interval:
                        if self._can_fire(volume, now):
                            existing.last_pulse_at = now
                            activation = self._fire(volume, entity_id, position, now)
                            fired.append(activation.to_dict())
                # Continuous mode: fire every update
                elif volume.mode == TriggerMode.CONTINUOUS.value:
                    if self._can_fire(volume, now):
                        activation = self._fire(volume, entity_id, position, now)
                        fired.append(activation.to_dict())

        self._stats.current_occupants = sum(len(occ) for occ in self._occupants.values())
        return {
            "entity_id": entity_id,
            "entered": entered,
            "exited": exited,
            "fired": fired,
        }

    def _can_fire(self, volume: TriggerVolume, now: float) -> bool:
        if volume.state == TriggerState.EXPIRED.value:
            return False
        if volume.state == TriggerState.COOLDOWN.value:
            if volume.cooldown_seconds > 0 and now - volume.last_fire_time >= volume.cooldown_seconds:
                volume.state = TriggerState.ACTIVE.value
                self._record_event(TriggerEventKind.COOLDOWN_ENDED, volume_id=volume.volume_id)
            else:
                return False
        if volume.max_activations > 0 and volume.activation_count >= volume.max_activations:
            volume.state = TriggerState.EXPIRED.value
            return False
        return True

    def _fire(self, volume: TriggerVolume, entity_id: str, position: Tuple[float, float, float], now: float) -> TriggerActivation:
        volume.activation_count += 1
        volume.last_fire_time = now
        volume.updated_at = now
        self._stats.total_activations += 1
        if volume.mode == TriggerMode.ONESHOT.value and volume.max_activations == 0:
            volume.max_activations = 1
        if volume.max_activations > 0 and volume.activation_count >= volume.max_activations:
            volume.state = TriggerState.EXPIRED.value
        elif volume.cooldown_seconds > 0:
            volume.state = TriggerState.COOLDOWN.value
            self._record_event(TriggerEventKind.COOLDOWN_STARTED, volume_id=volume.volume_id, details={"cooldown": volume.cooldown_seconds})
        activation = TriggerActivation(
            activation_id=self._next_activation_id(),
            volume_id=volume.volume_id,
            entity_id=entity_id,
            timestamp=now,
            event_kind=TriggerEventKind.TRIGGER_FIRED.value,
            position=position,
            payload=dict(volume.payload),
        )
        self._activations.append(activation)
        if len(self._activations) > _MAX_OCCUPANTS:
            self._activations = self._activations[-_MAX_OCCUPANTS:]
        self._record_event(
            TriggerEventKind.TRIGGER_FIRED,
            volume_id=volume.volume_id,
            entity_id=entity_id,
            details={"activation_id": activation.activation_id, "payload": volume.payload},
        )
        return activation

    # ------------------------------------------------------------------
    # Occupant queries
    # ------------------------------------------------------------------

    def list_occupants(self, volume_id: Optional[str] = None, limit: int = 100) -> List[OccupantRecord]:
        results: List[OccupantRecord] = []
        if volume_id is not None:
            results = list(self._occupants.get(volume_id, []))
        else:
            for occ_list in self._occupants.values():
                results.extend(occ_list)
        return results[:max(0, min(limit, len(results)))]

    def get_occupants(self, volume_id: str) -> List[OccupantRecord]:
        return list(self._occupants.get(volume_id, []))

    # ------------------------------------------------------------------
    # Activations
    # ------------------------------------------------------------------

    def list_activations(self, volume_id: Optional[str] = None, entity_id: Optional[str] = None, limit: int = 100) -> List[TriggerActivation]:
        results: List[TriggerActivation] = []
        for a in self._activations:
            if volume_id is not None and a.volume_id != volume_id:
                continue
            if entity_id is not None and a.entity_id != entity_id:
                continue
            results.append(a)
        return list(reversed(results))[:max(0, min(limit, len(results)))]

    # ------------------------------------------------------------------
    # Tick / lifecycle
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        now = _now()
        # Expire volumes past their lifetime
        if self._config.auto_expire and self._config.expire_after_seconds > 0:
            for v in self._volumes.values():
                if v.state == TriggerState.ACTIVE.value and now - v.created_at > self._config.expire_after_seconds:
                    v.state = TriggerState.EXPIRED.value
            self._stats.expired_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.EXPIRED.value)
            self._stats.active_volumes = sum(1 for v in self._volumes.values() if v.state == TriggerState.ACTIVE.value)
        self._record_event(TriggerEventKind.TICK, details={"delta_time": delta_time, "tick": self._tick_count})
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]
        return {"tick": self._tick_count, "delta_time": delta_time}

    def get_config(self) -> TriggerConfig:
        return self._config

    def set_config(self, config: TriggerConfig) -> Dict[str, Any]:
        self._config = config
        self._record_event(TriggerEventKind.CONFIG_UPDATED, details={"max_volumes": config.max_volumes})
        return {"updated": True}

    def list_events(self, volume_id: Optional[str] = None, entity_id: Optional[str] = None, limit: int = 100) -> List[TriggerEvent]:
        results: List[TriggerEvent] = []
        for e in self._events:
            if volume_id is not None and e.volume_id != volume_id:
                continue
            if entity_id is not None and e.entity_id != entity_id:
                continue
            results.append(e)
        return list(reversed(results))[:max(0, min(limit, len(results)))]

    def get_stats(self) -> TriggerStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_volumes": len(self._volumes),
            "active_volumes": sum(1 for v in self._volumes.values() if v.state == TriggerState.ACTIVE.value),
            "current_occupants": sum(len(occ) for occ in self._occupants.values()),
            "total_activations": self._stats.total_activations,
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> TriggerSnapshot:
        return TriggerSnapshot(
            volumes=[v.to_dict() for v in self._volumes.values()],
            occupants=[occ.to_dict() for occ_list in self._occupants.values() for occ in occ_list],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        self._volumes.clear()
        self._occupants.clear()
        self._activations.clear()
        self._events.clear()
        self._stats = TriggerStats()
        self._tick_count = 0
        self._event_counter = 0
        self._activation_counter = 0
        self._initialized = False
        self._seed()
        self._record_event(TriggerEventKind.RESET)
        return {"reset": True, "initialized": self._initialized}


def get_trigger_volume() -> TriggerVolumeSystem:
    return TriggerVolumeSystem.get_instance()
