"""
SparkLabs Engine - Vehicle Physics System

Simulates wheeled vehicle dynamics with suspension, engine torque,
steering, drift, surface friction, and collision response. Supports
cars, trucks, motorcycles, and tanks with configurable axle layouts,
drive types, and tire models.

Designed for racing games, open-world driving, vehicular combat, and
simulation experiences. Integrates with the physics dynamics core,
surface profile system, and wind field for aerodynamic effects.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sparkai.engine.engine_physics_dynamics import Vector2


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


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict"):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_VEHICLES = 2000
_MAX_WHEELS = 16000
_MAX_ENGINE_LOG = 5000
_MAX_EVENTS = 5000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VehicleKind(str, Enum):
    CAR = "car"
    TRUCK = "truck"
    MOTORCYCLE = "motorcycle"
    TANK = "tank"
    HOVERCRAFT = "hovercraft"
    AIRCRAFT = "aircraft"
    BOAT = "boat"
    CUSTOM = "custom"


class DriveType(str, Enum):
    FWD = "fwd"
    RWD = "rwd"
    AWD = "awd"
    FOUR_WD = "four_wd"
    SIX_WD = "six_wd"
    EIGHT_WD = "eight_wd"


class WheelPosition(str, Enum):
    FRONT_LEFT = "front_left"
    FRONT_RIGHT = "front_right"
    REAR_LEFT = "rear_left"
    REAR_RIGHT = "rear_right"
    MID_LEFT = "mid_left"
    MID_RIGHT = "mid_right"
    CENTER = "center"
    TRACK_LEFT = "track_left"
    TRACK_RIGHT = "track_right"


class SurfaceGrip(str, Enum):
    ASPHALT = "asphalt"
    CONCRETE = "concrete"
    DIRT = "dirt"
    GRASS = "grass"
    GRAVEL = "gravel"
    ICE = "ice"
    SAND = "sand"
    SNOW = "snow"
    WET = "wet"
    OIL = "oil"
    METAL = "metal"
    WATER = "water"


class VehicleStatus(str, Enum):
    PARKED = "parked"
    DRIVING = "driving"
    SKIDDING = "skidding"
    AIRBORNE = "airborne"
    ROLLED = "rolled"
    DESTROYED = "destroyed"
    UNDERWATER = "underwater"


class DamageZone(str, Enum):
    FRONT = "front"
    REAR = "rear"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    ENGINE = "engine"
    WHEEL = "wheel"
    TRANSMISSION = "transmission"
    FUEL_TANK = "fuel_tank"


class VehicleEventKind(str, Enum):
    REGISTERED = "registered"
    REMOVED = "removed"
    STARTED = "started"
    STOPPED = "stopped"
    COLLISION = "collision"
    SKIDDING = "skidding"
    AIRBORNE = "airborne"
    LANDED = "landed"
    ROLLED = "rolled"
    DAMAGED = "damaged"
    DESTROYED = "destroyed"
    GEAR_SHIFT = "gear_shift"
    SURFACE_CHANGED = "surface_changed"
    FUEL_LOW = "fuel_low"
    FUEL_EMPTY = "fuel_empty"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class WheelSpec:
    wheel_id: str
    position: str = WheelPosition.FRONT_LEFT.value
    radius: float = 0.34
    width: float = 0.25
    mass: float = 25.0
    steer_angle: float = 0.0
    drive: bool = True
    brake: bool = True
    handbrake: bool = False
    suspension_rest_length: float = 0.35
    spring_stiffness: float = 35000.0
    damper_compression: float = 4500.0
    damper_rebound: float = 6000.0
    max_steer: float = 35.0
    lateral_grip: float = 1.0
    longitudinal_grip: float = 1.0
    contact: bool = False
    contact_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    suspension_force: float = 0.0
    slip_ratio: float = 0.0
    slip_angle: float = 0.0
    angular_velocity: float = 0.0
    damage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EngineSpec:
    max_torque: float = 400.0
    max_power: float = 250000.0
    rpm_idle: float = 800.0
    rpm_max: float = 7000.0
    rpm_redline: float = 7500.0
    torque_curve: List[Tuple[float, float]] = field(default_factory=lambda: [
        (800.0, 200.0),
        (2000.0, 320.0),
        (3500.0, 400.0),
        (5000.0, 380.0),
        (6500.0, 300.0),
        (7500.0, 200.0),
    ])
    current_rpm: float = 800.0
    current_torque: float = 0.0
    throttle: float = 0.0
    fuel_consumption_rate: float = 0.08
    current_gear: int = 1
    gear_ratios: List[float] = field(default_factory=lambda: [3.5, 2.1, 1.4, 1.0, 0.8, 0.65])
    reverse_ratio: float = 3.2
    differential_ratio: float = 3.7
    efficiency: float = 0.92

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VehicleConfig:
    max_vehicles: int = 500
    max_wheels_per_vehicle: int = 8
    gravity: float = 9.81
    air_density: float = 1.225
    drag_coefficient: float = 0.32
    frontal_area: float = 2.2
    downforce_coefficient: float = 0.0
    brake_bias: float = 0.55
    abs_enabled: bool = True
    traction_control: bool = True
    stability_control: bool = True
    handbrake_force: float = 8000.0
    roll_resistance: float = 0.015
    fuel_enabled: bool = True
    fuel_capacity: float = 60.0
    damage_enabled: bool = True
    auto_transmission: bool = True
    shift_up_rpm: float = 6000.0
    shift_down_rpm: float = 2500.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VehicleState:
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    acceleration: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_yaw: float = 0.0
    rotation_pitch: float = 0.0
    rotation_roll: float = 0.0
    angular_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    speed: float = 0.0
    speed_kmh: float = 0.0
    steering_input: float = 0.0
    throttle_input: float = 0.0
    brake_input: float = 0.0
    handbrake_input: float = 0.0
    status: str = VehicleStatus.PARKED.value
    surface: str = SurfaceGrip.ASPHALT.value
    fuel: float = 60.0
    engine_on: bool = False
    airborne: bool = False
    wheels_in_contact: int = 0
    drift_angle: float = 0.0
    g_force_lateral: float = 0.0
    g_force_longitudinal: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DamageRecord:
    zone: str
    amount: float
    timestamp: float
    impact_speed: float = 0.0
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VehicleProfile:
    vehicle_id: str
    name: str = ""
    kind: str = VehicleKind.CAR.value
    drive_type: str = DriveType.RWD.value
    mass: float = 1500.0
    center_of_mass: Tuple[float, float, float] = (0.0, -0.4, 0.0)
    wheelbase: float = 2.7
    track_width: float = 1.6
    length: float = 4.5
    width: float = 1.85
    height: float = 1.4
    wheels: List[WheelSpec] = field(default_factory=list)
    engine: EngineSpec = field(default_factory=EngineSpec)
    state: VehicleState = field(default_factory=VehicleState)
    config: VehicleConfig = field(default_factory=VehicleConfig)
    damage: Dict[str, float] = field(default_factory=dict)
    damage_log: List[DamageRecord] = field(default_factory=list)
    total_damage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VehicleStats:
    total_vehicles: int = 0
    active_vehicles: int = 0
    parked_vehicles: int = 0
    destroyed_vehicles: int = 0
    total_collisions: int = 0
    total_skids: int = 0
    total_airborne: int = 0
    total_rolls: int = 0
    max_speed_kmh: float = 0.0
    total_distance_km: float = 0.0
    total_fuel_consumed: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VehicleSnapshot:
    vehicles: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VehicleEvent:
    event_id: str
    kind: str
    vehicle_id: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Vehicle Physics System
# ---------------------------------------------------------------------------

class VehiclePhysicsSystem:
    """Manages wheeled vehicle simulation with suspension, engine, and tire dynamics."""

    _instance: Optional["VehiclePhysicsSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._vehicles: Dict[str, VehicleProfile] = {}
        self._events: List[VehicleEvent] = []
        self._stats = VehicleStats()
        self._config = VehicleConfig()
        self._tick_count: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "VehiclePhysicsSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed sample vehicles for testing and demonstration."""
        # Sports car (RWD)
        sports_car = VehicleProfile(
            vehicle_id="veh_sports_coupe",
            name="Phantom GT",
            kind=VehicleKind.CAR.value,
            drive_type=DriveType.RWD.value,
            mass=1450.0,
            center_of_mass=(0.0, -0.45, 0.0),
            wheelbase=2.6,
            track_width=1.55,
            length=4.3,
            width=1.82,
            height=1.28,
            engine=EngineSpec(
                max_torque=420.0,
                max_power=320000.0,
                rpm_max=7800.0,
                rpm_redline=8200.0,
                fuel_consumption_rate=0.10,
            ),
            config=VehicleConfig(
                drag_coefficient=0.30,
                frontal_area=2.0,
                downforce_coefficient=0.5,
                brake_bias=0.52,
            ),
        )
        sports_car.wheels = self._create_wheels_4(sports_car)
        sports_car.state.fuel = 55.0
        self._vehicles[sports_car.vehicle_id] = sports_car

        # Off-road truck (4WD)
        truck = VehicleProfile(
            vehicle_id="veh_offroad_truck",
            name="Boulder X",
            kind=VehicleKind.TRUCK.value,
            drive_type=DriveType.FOUR_WD.value,
            mass=2200.0,
            center_of_mass=(0.0, -0.5, 0.0),
            wheelbase=3.2,
            track_width=1.75,
            length=5.1,
            width=1.95,
            height=1.85,
            engine=EngineSpec(
                max_torque=550.0,
                max_power=200000.0,
                rpm_max=4500.0,
                rpm_redline=5000.0,
                fuel_consumption_rate=0.14,
            ),
            config=VehicleConfig(
                drag_coefficient=0.45,
                frontal_area=3.0,
                brake_bias=0.58,
                abs_enabled=True,
                traction_control=True,
            ),
        )
        truck.wheels = self._create_wheels_4(truck, radius=0.42, offroad=True)
        truck.state.fuel = 80.0
        self._vehicles[truck.vehicle_id] = truck

        # Racing motorcycle
        moto = VehicleProfile(
            vehicle_id="veh_racing_moto",
            name="Velocity R",
            kind=VehicleKind.MOTORCYCLE.value,
            drive_type=DriveType.RWD.value,
            mass=200.0,
            center_of_mass=(0.0, -0.6, 0.0),
            wheelbase=1.4,
            track_width=0.0,
            length=2.0,
            width=0.7,
            height=1.1,
            engine=EngineSpec(
                max_torque=120.0,
                max_power=160000.0,
                rpm_max=14000.0,
                rpm_redline=15000.0,
                fuel_consumption_rate=0.06,
            ),
            config=VehicleConfig(
                drag_coefficient=0.38,
                frontal_area=0.65,
                brake_bias=0.45,
            ),
        )
        moto.wheels = [
            WheelSpec(
                wheel_id="wheel_front",
                position=WheelPosition.FRONT_LEFT.value,
                radius=0.30,
                width=0.12,
                steer_angle=0.0,
                drive=False,
                max_steer=30.0,
                suspension_rest_length=0.30,
                spring_stiffness=25000.0,
            ),
            WheelSpec(
                wheel_id="wheel_rear",
                position=WheelPosition.REAR_LEFT.value,
                radius=0.30,
                width=0.20,
                drive=True,
                handbrake=True,
                suspension_rest_length=0.30,
                spring_stiffness=30000.0,
            ),
        ]
        moto.state.fuel = 18.0
        self._vehicles[moto.vehicle_id] = moto

        self._stats.total_vehicles = len(self._vehicles)
        self._stats.parked_vehicles = len(self._vehicles)
        self._initialized = True

    def _create_wheels_4(self, vehicle: VehicleProfile, radius: float = 0.34, offroad: bool = False) -> List[WheelSpec]:
        """Create a standard 4-wheel layout."""
        lateral_grip = 0.7 if offroad else 1.0
        spring_k = 28000.0 if offroad else 35000.0
        return [
            WheelSpec(
                wheel_id="wheel_fl",
                position=WheelPosition.FRONT_LEFT.value,
                radius=radius,
                steer_angle=0.0,
                drive=vehicle.drive_type in (DriveType.FWD.value, DriveType.AWD.value, DriveType.FOUR_WD.value),
                max_steer=35.0,
                spring_stiffness=spring_k,
                lateral_grip=lateral_grip,
            ),
            WheelSpec(
                wheel_id="wheel_fr",
                position=WheelPosition.FRONT_RIGHT.value,
                radius=radius,
                steer_angle=0.0,
                drive=vehicle.drive_type in (DriveType.FWD.value, DriveType.AWD.value, DriveType.FOUR_WD.value),
                max_steer=35.0,
                spring_stiffness=spring_k,
                lateral_grip=lateral_grip,
            ),
            WheelSpec(
                wheel_id="wheel_rl",
                position=WheelPosition.REAR_LEFT.value,
                radius=radius,
                drive=vehicle.drive_type in (DriveType.RWD.value, DriveType.AWD.value, DriveType.FOUR_WD.value),
                handbrake=True,
                spring_stiffness=spring_k,
                lateral_grip=lateral_grip,
            ),
            WheelSpec(
                wheel_id="wheel_rr",
                position=WheelPosition.REAR_RIGHT.value,
                radius=radius,
                drive=vehicle.drive_type in (DriveType.RWD.value, DriveType.AWD.value, DriveType.FOUR_WD.value),
                handbrake=True,
                spring_stiffness=spring_k,
                lateral_grip=lateral_grip,
            ),
        ]

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, vehicle_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        event = VehicleEvent(
            event_id=f"evt_{self._tick_count}_{len(self._events)}",
            kind=kind,
            vehicle_id=vehicle_id,
            timestamp=_now(),
            details=details or {},
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]

    def _recompute_stats(self) -> None:
        self._stats.total_vehicles = len(self._vehicles)
        active = 0
        parked = 0
        destroyed = 0
        for v in self._vehicles.values():
            if v.state.status == VehicleStatus.DESTROYED.value:
                destroyed += 1
            elif v.state.status == VehicleStatus.PARKED.value:
                parked += 1
            else:
                active += 1
        self._stats.active_vehicles = active
        self._stats.parked_vehicles = parked
        self._stats.destroyed_vehicles = destroyed

    def _compute_torque_at_rpm(self, engine: EngineSpec, rpm: float) -> float:
        """Interpolate torque from the torque curve."""
        if not engine.torque_curve:
            return engine.max_torque * _clamp(rpm / engine.rpm_max, 0.0, 1.0)
        curve = sorted(engine.torque_curve, key=lambda p: p[0])
        if rpm <= curve[0][0]:
            return curve[0][1]
        if rpm >= curve[-1][0]:
            return curve[-1][1]
        for i in range(len(curve) - 1):
            r0, t0 = curve[i]
            r1, t1 = curve[i + 1]
            if r0 <= rpm <= r1:
                alpha = (rpm - r0) / max(r1 - r0, 0.001)
                return t0 + alpha * (t1 - t0)
        return engine.max_torque

    def _surface_friction_factor(self, surface: str) -> float:
        factors = {
            SurfaceGrip.ASPHALT.value: 1.0,
            SurfaceGrip.CONCRETE.value: 0.95,
            SurfaceGrip.DIRT.value: 0.65,
            SurfaceGrip.GRASS.value: 0.55,
            SurfaceGrip.GRAVEL.value: 0.60,
            SurfaceGrip.ICE.value: 0.20,
            SurfaceGrip.SAND.value: 0.45,
            SurfaceGrip.SNOW.value: 0.40,
            SurfaceGrip.WET.value: 0.70,
            SurfaceGrip.OIL.value: 0.30,
            SurfaceGrip.METAL.value: 0.85,
            SurfaceGrip.WATER.value: 0.35,
        }
        return factors.get(surface, 0.8)

    # ------------------------------------------------------------------
    # Vehicle Lifecycle
    # ------------------------------------------------------------------

    def register_vehicle(self, vehicle: VehicleProfile) -> VehicleProfile:
        with self._init_lock:
            if len(self._vehicles) >= _MAX_VEHICLES:
                oldest_id = next(iter(self._vehicles))
                del self._vehicles[oldest_id]
            self._vehicles[vehicle.vehicle_id] = vehicle
            vehicle.created_at = _now()
            vehicle.updated_at = _now()
            self._recompute_stats()
            self._emit_event(VehicleEventKind.REGISTERED.value, vehicle.vehicle_id, {"name": vehicle.name, "kind": vehicle.kind})
            return vehicle

    def get_vehicle(self, vehicle_id: str) -> Optional[VehicleProfile]:
        return self._vehicles.get(vehicle_id)

    def list_vehicles(self, kind: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> List[VehicleProfile]:
        results = list(self._vehicles.values())
        if kind:
            results = [v for v in results if v.kind == kind]
        if status:
            results = [v for v in results if v.state.status == status]
        return results[:max(0, int(limit))]

    def remove_vehicle(self, vehicle_id: str) -> bool:
        with self._init_lock:
            if vehicle_id not in self._vehicles:
                return False
            del self._vehicles[vehicle_id]
            self._recompute_stats()
            self._emit_event(VehicleEventKind.REMOVED.value, vehicle_id)
            return True

    # ------------------------------------------------------------------
    # Driving Controls
    # ------------------------------------------------------------------

    def set_steering(self, vehicle_id: str, steering_input: float) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        v.state.steering_input = _clamp(steering_input, -1.0, 1.0)
        max_steer = max((w.max_steer for w in v.wheels if w.max_steer > 0), default=35.0)
        for w in v.wheels:
            if w.max_steer > 0:
                w.steer_angle = v.state.steering_input * w.max_steer
        v.updated_at = _now()
        return v

    def set_throttle(self, vehicle_id: str, throttle_input: float) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        v.state.throttle_input = _clamp(throttle_input, 0.0, 1.0)
        v.engine.throttle = v.state.throttle_input
        if v.state.throttle_input > 0.0 and not v.state.engine_on:
            v.state.engine_on = True
            self._emit_event(VehicleEventKind.STARTED.value, vehicle_id)
        v.updated_at = _now()
        return v

    def set_brake(self, vehicle_id: str, brake_input: float) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        v.state.brake_input = _clamp(brake_input, 0.0, 1.0)
        v.updated_at = _now()
        return v

    def set_handbrake(self, vehicle_id: str, handbrake_input: float) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        v.state.handbrake_input = _clamp(handbrake_input, 0.0, 1.0)
        v.updated_at = _now()
        return v

    def start_engine(self, vehicle_id: str) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        if v.state.fuel <= 0.0:
            self._emit_event(VehicleEventKind.FUEL_EMPTY.value, vehicle_id)
            return v
        v.state.engine_on = True
        v.engine.current_rpm = v.engine.rpm_idle
        if v.state.status == VehicleStatus.PARKED.value:
            v.state.status = VehicleStatus.DRIVING.value
        self._emit_event(VehicleEventKind.STARTED.value, vehicle_id)
        v.updated_at = _now()
        return v

    def stop_engine(self, vehicle_id: str) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        v.state.engine_on = False
        v.engine.throttle = 0.0
        v.state.throttle_input = 0.0
        if abs(v.state.speed) < 0.5:
            v.state.status = VehicleStatus.PARKED.value
        self._emit_event(VehicleEventKind.STOPPED.value, vehicle_id)
        v.updated_at = _now()
        return v

    def shift_gear(self, vehicle_id: str, gear: int) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        max_gear = len(v.engine.gear_ratios)
        v.engine.current_gear = _clamp(gear, -1, max_gear)
        self._emit_event(VehicleEventKind.GEAR_SHIFT.value, vehicle_id, {"gear": v.engine.current_gear})
        v.updated_at = _now()
        return v

    def set_surface(self, vehicle_id: str, surface: str) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        old = v.state.surface
        v.state.surface = surface
        if old != surface:
            self._emit_event(VehicleEventKind.SURFACE_CHANGED.value, vehicle_id, {"old": old, "new": surface})
        v.updated_at = _now()
        return v

    # ------------------------------------------------------------------
    # Damage
    # ------------------------------------------------------------------

    def apply_damage(self, vehicle_id: str, zone: str, amount: float, impact_speed: float = 0.0, source: str = "") -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        if not v.config.damage_enabled:
            return v
        amount = max(0.0, float(amount))
        v.damage[zone] = v.damage.get(zone, 0.0) + amount
        v.total_damage += amount
        v.damage_log.append(DamageRecord(
            zone=zone,
            amount=amount,
            timestamp=_now(),
            impact_speed=impact_speed,
            source=source,
        ))
        if len(v.damage_log) > 100:
            v.damage_log = v.damage_log[-100:]
        # Critical zone checks
        if zone == DamageZone.ENGINE.value and v.damage.get(DamageZone.ENGINE.value, 0.0) > 80.0:
            v.state.engine_on = False
        if v.total_damage > 200.0:
            v.state.status = VehicleStatus.DESTROYED.value
            self._emit_event(VehicleEventKind.DESTROYED.value, vehicle_id, {"total_damage": v.total_damage})
        else:
            self._emit_event(VehicleEventKind.DAMAGED.value, vehicle_id, {"zone": zone, "amount": amount})
        self._stats.total_collisions += 1 if source == "collision" else 0
        v.updated_at = _now()
        return v

    def repair(self, vehicle_id: str, amount: float = 100.0) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        amount = max(0.0, float(amount))
        for zone in list(v.damage.keys()):
            v.damage[zone] = max(0.0, v.damage[zone] - amount)
            if v.damage[zone] <= 0.0:
                del v.damage[zone]
        v.total_damage = max(0.0, v.total_damage - amount)
        if v.state.status == VehicleStatus.DESTROYED.value and v.total_damage < 100.0:
            v.state.status = VehicleStatus.PARKED.value
        v.updated_at = _now()
        return v

    def refuel(self, vehicle_id: str, amount: float) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        v.state.fuel = min(v.config.fuel_capacity, v.state.fuel + max(0.0, float(amount)))
        v.updated_at = _now()
        return v

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016, current_time: Optional[float] = None) -> Dict[str, Any]:
        self._tick_count += 1
        events_emitted = 0
        max_speed = 0.0
        total_distance = 0.0
        total_fuel = 0.0

        for v in self._vehicles.values():
            if v.state.status == VehicleStatus.DESTROYED.value:
                continue

            dt = max(0.001, min(delta_time, 0.1))

            # Engine dynamics
            if v.state.engine_on:
                target_rpm = v.engine.rpm_idle + v.state.throttle_input * (v.engine.rpm_redline - v.engine.rpm_idle)
                v.engine.current_rpm += (target_rpm - v.engine.current_rpm) * 3.0 * dt
                v.engine.current_rpm = _clamp(v.engine.current_rpm, v.engine.rpm_idle, v.engine.rpm_redline)
                v.engine.current_torque = self._compute_torque_at_rpm(v.engine, v.engine.current_rpm)

                # Auto transmission
                if v.config.auto_transmission and v.engine.current_gear > 0:
                    if v.engine.current_rpm > v.config.shift_up_rpm and v.engine.current_gear < len(v.engine.gear_ratios):
                        v.engine.current_gear += 1
                        self._emit_event(VehicleEventKind.GEAR_SHIFT.value, v.vehicle_id, {"gear": v.engine.current_gear, "auto": True})
                        events_emitted += 1
                    elif v.engine.current_rpm < v.config.shift_down_rpm and v.engine.current_gear > 1:
                        v.engine.current_gear -= 1
                        self._emit_event(VehicleEventKind.GEAR_SHIFT.value, v.vehicle_id, {"gear": v.engine.current_gear, "auto": True})
                        events_emitted += 1

                # Fuel consumption
                if v.config.fuel_enabled:
                    consumption = v.engine.fuel_consumption_rate * v.state.throttle_input * (v.engine.current_rpm / v.engine.rpm_max) * dt
                    v.state.fuel = max(0.0, v.state.fuel - consumption)
                    total_fuel += consumption
                    if v.state.fuel < 5.0 and v.state.fuel > 0.0:
                        self._emit_event(VehicleEventKind.FUEL_LOW.value, v.vehicle_id, {"fuel": v.state.fuel})
                        events_emitted += 1
                    if v.state.fuel <= 0.0:
                        v.state.engine_on = False
                        v.state.throttle_input = 0.0
                        self._emit_event(VehicleEventKind.FUEL_EMPTY.value, v.vehicle_id)
                        events_emitted += 1

                # Compute wheel drive force
                gear_ratio = v.engine.gear_ratios[v.engine.current_gear - 1] if 1 <= v.engine.current_gear <= len(v.engine.gear_ratios) else 1.0
                if v.engine.current_gear < 0:
                    gear_ratio = -v.engine.reverse_ratio
                wheel_force = v.engine.current_torque * gear_ratio * v.engine.differential_ratio * v.engine.efficiency * v.state.throttle_input

                # Apply to velocity (simplified bicycle model)
                vx, vy, vz = v.state.velocity
                vx += (wheel_force / max(v.mass, 1.0)) * dt
            else:
                wheel_force = 0.0
                vx, vy, vz = v.state.velocity

            # Braking force
            brake_force = v.state.brake_input * v.config.brake_bias * 12000.0
            handbrake_force = v.state.handbrake_input * v.config.handbrake_force
            total_brake = brake_force + handbrake_force
            if abs(vx) > 0.01:
                decel = total_brake / max(v.mass, 1.0)
                if abs(vx) < decel * dt:
                    vx = 0.0
                else:
                    vx -= math.copysign(decel * dt, vx)

            # Rolling resistance
            if abs(vx) > 0.01:
                vx *= (1.0 - v.config.roll_resistance * dt)

            # Aerodynamic drag
            speed = abs(vx)
            drag = 0.5 * v.config.air_density * v.config.drag_coefficient * v.config.frontal_area * speed * speed
            if speed > 0.01:
                vx -= math.copysign((drag / max(v.mass, 1.0)) * dt, vx)

            # Steering effect (bicycle model)
            if abs(vx) > 0.5:
                steer_rad = math.radians(v.state.steering_input * 35.0)
                turn_radius = max(v.wheelbase, 0.5) / math.tan(max(abs(steer_rad), 0.001)) * math.copysign(1.0, steer_rad)
                yaw_rate = vx / turn_radius if abs(turn_radius) > 0.5 else 0.0
                v.state.rotation_yaw += yaw_rate * dt
                # Lateral velocity component
                vy += yaw_rate * v.wheelbase * 0.5 * dt
            else:
                yaw_rate = 0.0

            # Surface friction
            surface_factor = self._surface_friction_factor(v.state.surface)
            vx *= (0.99 + 0.01 * surface_factor)
            vy *= (0.90 + 0.09 * surface_factor)

            # Update state
            v.state.velocity = (vx, vy, vz)
            v.state.speed = math.sqrt(vx * vx + vy * vy + vz * vz)
            v.state.speed_kmh = v.state.speed * 3.6

            # Update position
            px, py, pz = v.state.position
            px += vx * dt
            pz += vz * dt
            v.state.position = (px, py, pz)

            # Wheel contact check (simplified)
            v.state.wheels_in_contact = sum(1 for w in v.wheels if w.contact) or len(v.wheels)

            # Drift detection
            if v.state.speed > 5.0:
                drift = math.degrees(math.atan2(abs(vy), abs(vx))) if abs(vx) > 0.1 else 0.0
                v.state.drift_angle = drift
                if drift > 15.0 and v.state.status != VehicleStatus.SKIDDING.value:
                    v.state.status = VehicleStatus.SKIDDING.value
                    self._emit_event(VehicleEventKind.SKIDDING.value, v.vehicle_id, {"drift_angle": drift})
                    events_emitted += 1
                    self._stats.total_skids += 1
                elif drift <= 10.0 and v.state.status == VehicleStatus.SKIDDING.value:
                    v.state.status = VehicleStatus.DRIVING.value
            else:
                v.state.drift_angle = 0.0
                if v.state.status == VehicleStatus.SKIDDING.value:
                    v.state.status = VehicleStatus.DRIVING.value

            # Airborne check
            if v.state.wheels_in_contact == 0 and not v.state.airborne:
                v.state.airborne = True
                if v.state.status != VehicleStatus.AIRBORNE.value:
                    v.state.status = VehicleStatus.AIRBORNE.value
                    self._emit_event(VehicleEventKind.AIRBORNE.value, v.vehicle_id)
                    events_emitted += 1
                    self._stats.total_airborne += 1
            elif v.state.wheels_in_contact > 0 and v.state.airborne:
                v.state.airborne = False
                if v.state.status == VehicleStatus.AIRBORNE.value:
                    v.state.status = VehicleStatus.DRIVING.value
                    self._emit_event(VehicleEventKind.LANDED.value, v.vehicle_id)
                    events_emitted += 1

            # G-force computation
            v.state.g_force_lateral = abs(yaw_rate * v.state.speed / 9.81) if v.state.speed > 0 else 0.0
            accel_long = (wheel_force - total_brake - drag) / max(v.mass, 1.0)
            v.state.g_force_longitudinal = abs(accel_long / 9.81)

            # Status transitions
            if v.state.speed < 0.5 and v.state.status not in (VehicleStatus.PARKED.value, VehicleStatus.DESTROYED.value, VehicleStatus.AIRBORNE.value):
                if not v.state.engine_on and v.state.throttle_input == 0.0:
                    v.state.status = VehicleStatus.PARKED.value

            max_speed = max(max_speed, v.state.speed_kmh)
            total_distance += v.state.speed * dt / 1000.0

            v.updated_at = _now()

        self._stats.max_speed_kmh = max(self._stats.max_speed_kmh, max_speed)
        self._stats.total_distance_km += total_distance
        self._stats.total_fuel_consumed += total_fuel
        self._stats.tick_count = self._tick_count
        self._recompute_stats()

        return {
            "tick": self._tick_count,
            "vehicles_processed": len(self._vehicles),
            "events_emitted": events_emitted,
            "max_speed_kmh": round(max_speed, 2),
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_wheel(self, vehicle_id: str, wheel_id: str) -> Optional[WheelSpec]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        for w in v.wheels:
            if w.wheel_id == wheel_id:
                return w
        return None

    def update_wheel(self, vehicle_id: str, wheel: WheelSpec) -> Optional[VehicleProfile]:
        v = self._vehicles.get(vehicle_id)
        if v is None:
            return None
        for i, w in enumerate(v.wheels):
            if w.wheel_id == wheel.wheel_id:
                v.wheels[i] = wheel
                v.updated_at = _now()
                return v
        return None

    def get_config(self) -> VehicleConfig:
        return self._config

    def set_config(self, config: VehicleConfig) -> VehicleConfig:
        with self._init_lock:
            self._config = config
            return self._config

    def list_events(self, limit: int = 100, vehicle_id: Optional[str] = None) -> List[VehicleEvent]:
        results = list(self._events)
        if vehicle_id:
            results = [e for e in results if e.vehicle_id == vehicle_id]
        return results[-max(0, int(limit)):]

    def get_stats(self) -> VehicleStats:
        self._recompute_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_vehicles": len(self._vehicles),
            "active_vehicles": sum(1 for v in self._vehicles.values() if v.state.status not in (VehicleStatus.PARKED.value, VehicleStatus.DESTROYED.value)),
            "tick_count": self._tick_count,
            "config": self._config.to_dict(),
        }

    def get_snapshot(self) -> VehicleSnapshot:
        self._recompute_stats()
        return VehicleSnapshot(
            vehicles=[v.to_dict() for v in list(self._vehicles.values())[:20]],
            stats=self._stats.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> None:
        self._vehicles.clear()
        self._events.clear()
        self._stats = VehicleStats()
        self._config = VehicleConfig()
        self._tick_count = 0
        self._seed()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_vehicle_physics() -> VehiclePhysicsSystem:
    """Return the singleton VehiclePhysicsSystem instance."""
    return VehiclePhysicsSystem.get_instance()
