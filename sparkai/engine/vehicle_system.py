"""
SparkLabs Engine - Vehicle System

Physics-based vehicle simulation for AI-native game worlds.
Models wheel-driven ground vehicles with configurable engine
power, transmission gearing, suspension dynamics, and tire
friction. Supports multiple vehicle types from compact cars
to heavy trucks with distinct handling characteristics.

Architecture:
  VehicleSystem
    |-- EngineModel (torque curves, RPM limits, power delivery)
    |-- TransmissionModel (gear ratios, shift timing, drive type)
    |-- SuspensionModel (spring rates, damping, ride height)
    |-- WheelCollider (slip detection, friction curves, braking)
    |-- CenterOfMass (stability adjustment, roll prevention)

Vehicle Types:
  - COMPACT: light, quick acceleration, tight turning
  - SEDAN: balanced handling, moderate speed
  - SUV: higher ground clearance, slower turning
  - SPORT: high top speed, stiff suspension
  - TRUCK: heavy cargo, slow acceleration, wide turning
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class VehicleType(Enum):
    COMPACT = "compact"
    SEDAN = "sedan"
    SUV = "suv"
    SPORT = "sport"
    TRUCK = "truck"


class DriveType(Enum):
    FRONT_WHEEL = "front_wheel"
    REAR_WHEEL = "rear_wheel"
    ALL_WHEEL = "all_wheel"


class GearMode(Enum):
    PARK = "park"
    REVERSE = "reverse"
    NEUTRAL = "neutral"
    DRIVE = "drive"


@dataclass
class VehicleConfig:
    vehicle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    vehicle_type: VehicleType = VehicleType.SEDAN
    drive_type: DriveType = DriveType.ALL_WHEEL
    engine_power: float = 200.0
    max_torque: float = 300.0
    max_rpm: float = 7000.0
    idle_rpm: float = 800.0
    gear_ratios: List[float] = field(default_factory=lambda: [-3.5, 3.8, 2.5, 1.5, 1.0, 0.75])
    final_drive_ratio: float = 3.5
    wheel_radius: float = 0.35
    suspension_stiffness: float = 15000.0
    suspension_damping: float = 2000.0
    suspension_travel: float = 0.2
    max_steering_angle: float = 35.0
    mass: float = 1500.0
    drag_coefficient: float = 0.35
    braking_force: float = 8000.0
    handbrake_force: float = 5000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "type": self.vehicle_type.value,
            "drive": self.drive_type.value,
            "engine_power": self.engine_power,
            "mass": self.mass,
            "gears": len(self.gear_ratios),
        }


DEFAULT_VEHICLE_CONFIGS: Dict[VehicleType, Dict[str, Any]] = {
    VehicleType.COMPACT: {"engine_power": 120.0, "mass": 1000.0, "max_steering_angle": 38.0, "drag_coefficient": 0.3},
    VehicleType.SEDAN: {"engine_power": 200.0, "mass": 1500.0, "max_steering_angle": 35.0, "drag_coefficient": 0.35},
    VehicleType.SUV: {"engine_power": 250.0, "mass": 2200.0, "max_steering_angle": 32.0, "drag_coefficient": 0.4},
    VehicleType.SPORT: {"engine_power": 400.0, "mass": 1300.0, "max_steering_angle": 28.0, "drag_coefficient": 0.28},
    VehicleType.TRUCK: {"engine_power": 350.0, "mass": 5000.0, "max_steering_angle": 25.0, "drag_coefficient": 0.5},
}


@dataclass
class VehicleState:
    vehicle_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    forward_speed_ms: float = 0.0
    rpm: float = 800.0
    current_gear: int = 0
    gear_mode: GearMode = GearMode.PARK
    steering_angle: float = 0.0
    throttle: float = 0.0
    brake: float = 0.0
    handbrake: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "position": list(self.position),
            "speed_ms": round(self.forward_speed_ms, 2),
            "speed_kmh": round(self.forward_speed_ms * 3.6, 1),
            "rpm": round(self.rpm, 0),
            "gear": self.current_gear,
            "mode": self.gear_mode.value,
            "steering": round(self.steering_angle, 1),
        }


class VehicleSystem:
    _instance: Optional[VehicleSystem] = None

    @classmethod
    def get_instance(cls) -> VehicleSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._configs: Dict[str, VehicleConfig] = {}
        self._states: Dict[str, VehicleState] = {}
        self._total_vehicles: int = 0

    def create_vehicle(self, vehicle_id: str, vehicle_type: VehicleType = VehicleType.SEDAN,
                       drive_type: Optional[DriveType] = None) -> VehicleState:
        base = DEFAULT_VEHICLE_CONFIGS.get(vehicle_type, {})
        config = VehicleConfig(
            vehicle_id=vehicle_id,
            vehicle_type=vehicle_type,
            drive_type=drive_type or DriveType.ALL_WHEEL,
            **{k: v for k, v in base.items() if k in VehicleConfig.__dataclass_fields__},
        )
        self._configs[vehicle_id] = config
        state = VehicleState(vehicle_id=vehicle_id)
        self._states[vehicle_id] = state
        self._total_vehicles += 1
        return state

    def set_input(self, vehicle_id: str, throttle: float = 0.0, steering: float = 0.0,
                  brake: float = 0.0, handbrake: bool = False) -> Optional[VehicleState]:
        state = self._states.get(vehicle_id)
        if state is None:
            return None
        state.throttle = max(-1.0, min(1.0, throttle))
        state.steering_angle = state.steering_angle = max(-1.0, min(1.0, steering))
        state.brake = max(0.0, min(1.0, brake))
        state.handbrake = handbrake
        return state

    def set_gear_mode(self, vehicle_id: str, mode: GearMode):
        state = self._states.get(vehicle_id)
        if state:
            state.gear_mode = mode

    def update(self, vehicle_id: str, delta_time: float) -> Optional[VehicleState]:
        state = self._states.get(vehicle_id)
        config = self._configs.get(vehicle_id)
        if state is None or config is None:
            return None

        dt = max(0.001, delta_time)

        if state.gear_mode == GearMode.PARK:
            return state

        wheel_angular_velocity = state.forward_speed_ms / config.wheel_radius if config.wheel_radius > 0 else 0
        state.rpm = wheel_angular_velocity * 60 / (2 * math.pi) * config.final_drive_ratio * (
            config.gear_ratios[state.current_gear] if 0 <= state.current_gear < len(config.gear_ratios) else 1.0
        )
        state.rpm = max(config.idle_rpm, min(state.rpm, config.max_rpm))

        if state.brake > 0 or state.handbrake:
            brake_force = config.braking_force if not state.handbrake else config.handbrake_force
            brake_decel = (brake_force / config.mass) * state.brake * dt
            direction = 1.0 if state.forward_speed_ms >= 0 else -1.0
            state.forward_speed_ms -= brake_decel * direction
            if abs(state.forward_speed_ms) < 0.1:
                state.forward_speed_ms = 0.0

        if state.gear_mode == GearMode.DRIVE:
            if abs(state.throttle) > 0.01:
                total_ratio = config.final_drive_ratio * (
                    config.gear_ratios[state.current_gear] if 0 <= state.current_gear < len(config.gear_ratios) else 1.0
                )
                wheel_torque = config.max_torque * state.throttle * total_ratio
                drive_force = wheel_torque / config.wheel_radius if config.wheel_radius > 0 else 0
                acceleration = (drive_force / config.mass) * dt
                state.forward_speed_ms += acceleration

            drag_force = 0.5 * 1.225 * config.drag_coefficient * 2.2 * (state.forward_speed_ms ** 2)
            drag_accel = (drag_force / config.mass) * dt
            if state.forward_speed_ms > 0:
                state.forward_speed_ms = max(0, state.forward_speed_ms - drag_accel)

        auto_shift = state.forward_speed_ms * 3.6 / 15
        state.current_gear = max(1, min(len(config.gear_ratios) - 2, int(auto_shift)))

        if state.steering_angle != 0 and abs(state.forward_speed_ms) > 0.1:
            wheelbase = 2.5
            turn_radius = wheelbase / math.sin(math.radians(abs(state.steering_angle) * config.max_steering_angle))
            angular_velocity = state.forward_speed_ms / turn_radius if turn_radius > 0 else 0
            yaw_change = angular_velocity * dt * (1.0 if state.steering_angle > 0 else -1.0)

        forward = (0.0, 0.0, 1.0)
        state.position = (
            state.position[0] + forward[0] * state.forward_speed_ms * dt,
            state.position[1],
            state.position[2] + forward[2] * state.forward_speed_ms * dt,
        )

        state.timestamp = time.time()
        return state

    def get_state(self, vehicle_id: str) -> Optional[VehicleState]:
        return self._states.get(vehicle_id)

    def remove_vehicle(self, vehicle_id: str):
        self._configs.pop(vehicle_id, None)
        self._states.pop(vehicle_id, None)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_vehicles": self._total_vehicles,
            "active_vehicles": len(self._states),
            "type_distribution": {
                vt.value: sum(1 for c in self._configs.values() if c.vehicle_type == vt)
                for vt in VehicleType
            },
        }


def get_vehicle_system() -> VehicleSystem:
    return VehicleSystem.get_instance()