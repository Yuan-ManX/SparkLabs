"""
SparkLabs Engine - Water System

Fluid body simulation and buoyancy physics for AI-native games.
Manages water body definitions, flow dynamics, wave simulation,
and object buoyancy with configurable physical parameters.

Architecture:
  WaterSystem
    |-- WaterBodyRegistry (water body type and zone catalog)
    |-- FlowSimulator (directional flow and current vectors)
    |-- WaveGenerator (amplitude and frequency wave modeling)
    |-- BuoyancyEngine (floating and submersion physics)

Water Body Types:
  - OCEAN, LAKE, RIVER, POND, SWAMP, WATERFALL, FOUNTAIN
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class WaterBody(Enum):
    OCEAN = "ocean"
    LAKE = "lake"
    RIVER = "river"
    POND = "pond"
    SWAMP = "swamp"
    WATERFALL = "waterfall"
    FOUNTAIN = "fountain"


@dataclass
class WaterPhysics:
    density: float = 1000.0
    viscosity: float = 0.001
    surface_tension: float = 0.0728
    flow_direction: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    flow_speed: float = 0.0
    wave_amplitude: float = 0.0
    wave_frequency: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "density": self.density,
            "viscosity": self.viscosity,
            "surface_tension": self.surface_tension,
            "flow_speed": self.flow_speed,
            "wave_amplitude": self.wave_amplitude,
            "wave_frequency": self.wave_frequency,
        }


@dataclass
class BuoyancyParams:
    object_density: float = 500.0
    drag_coefficient: float = 0.47
    angular_drag: float = 0.5
    submersion_depth: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_density": self.object_density,
            "drag_coefficient": self.drag_coefficient,
            "angular_drag": self.angular_drag,
            "submersion_depth": self.submersion_depth,
        }


DEFAULT_PHYSICS_PRESETS: Dict[WaterBody, WaterPhysics] = {
    WaterBody.OCEAN: WaterPhysics(
        density=1027.0, viscosity=0.00108, surface_tension=0.074,
        flow_direction=(0.5, 0.0, 0.0), flow_speed=0.3,
        wave_amplitude=1.5, wave_frequency=0.12,
    ),
    WaterBody.LAKE: WaterPhysics(
        density=1000.0, viscosity=0.001, surface_tension=0.0728,
        flow_direction=(0.0, 0.0, 0.0), flow_speed=0.02,
        wave_amplitude=0.3, wave_frequency=0.08,
    ),
    WaterBody.RIVER: WaterPhysics(
        density=1000.0, viscosity=0.001, surface_tension=0.072,
        flow_direction=(1.0, 0.0, 0.0), flow_speed=2.5,
        wave_amplitude=0.4, wave_frequency=0.15,
    ),
    WaterBody.POND: WaterPhysics(
        density=1002.0, viscosity=0.0012, surface_tension=0.073,
        flow_direction=(0.0, 0.0, 0.0), flow_speed=0.0,
        wave_amplitude=0.1, wave_frequency=0.05,
    ),
    WaterBody.SWAMP: WaterPhysics(
        density=1050.0, viscosity=0.01, surface_tension=0.05,
        flow_direction=(0.1, 0.0, 0.0), flow_speed=0.08,
        wave_amplitude=0.05, wave_frequency=0.03,
    ),
    WaterBody.WATERFALL: WaterPhysics(
        density=1000.0, viscosity=0.001, surface_tension=0.072,
        flow_direction=(0.0, -1.0, 0.0), flow_speed=9.8,
        wave_amplitude=0.0, wave_frequency=0.0,
    ),
    WaterBody.FOUNTAIN: WaterPhysics(
        density=1000.0, viscosity=0.001, surface_tension=0.072,
        flow_direction=(0.0, 1.0, 0.0), flow_speed=4.0,
        wave_amplitude=0.2, wave_frequency=0.3,
    ),
}


@dataclass
class WaterObject:
    object_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    mass: float = 1.0
    volume: float = 0.01
    buoyancy: BuoyancyParams = field(default_factory=BuoyancyParams)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    water_body_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "name": self.name,
            "mass": self.mass,
            "volume": self.volume,
            "water_body_id": self.water_body_id,
            "position": list(self.position),
        }


@dataclass
class WaterBodyInstance:
    body_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    body_type: WaterBody = WaterBody.LAKE
    physics: WaterPhysics = field(default_factory=WaterPhysics)
    surface_height: float = 0.0
    bounds_min: Tuple[float, float, float] = (-10.0, -10.0, -10.0)
    bounds_max: Tuple[float, float, float] = (10.0, 10.0, 10.0)
    elapsed_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "name": self.name,
            "body_type": self.body_type.value,
            "surface_height": self.surface_height,
        }


class WaterSystem:
    _instance: Optional[WaterSystem] = None

    def __init__(self):
        self._water_bodies: Dict[str, WaterBodyInstance] = {}
        self._water_objects: Dict[str, WaterObject] = {}
        self._total_updates: int = 0

    @classmethod
    def get_instance(cls) -> WaterSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_water_body(
        self,
        name: str,
        body_type: WaterBody,
        surface_height: float = 0.0,
        bounds_min: Optional[Tuple[float, float, float]] = None,
        bounds_max: Optional[Tuple[float, float, float]] = None,
        custom_physics: Optional[WaterPhysics] = None,
    ) -> str:
        physics = custom_physics if custom_physics is not None else DEFAULT_PHYSICS_PRESETS.get(
            body_type, WaterPhysics()
        )
        instance = WaterBodyInstance(
            name=name,
            body_type=body_type,
            physics=physics,
            surface_height=surface_height,
            bounds_min=bounds_min or (-10.0, -10.0, -10.0),
            bounds_max=bounds_max or (10.0, 10.0, 10.0),
        )
        self._water_bodies[instance.body_id] = instance
        return instance.body_id

    def remove_water_body(self, body_id: str) -> bool:
        if body_id not in self._water_bodies:
            return False
        for obj_id, obj in list(self._water_objects.items()):
            if obj.water_body_id == body_id:
                del self._water_objects[obj_id]
        del self._water_bodies[body_id]
        return True

    def update_physics(self, body_id: str, delta_seconds: float):
        if body_id not in self._water_bodies:
            return
        body = self._water_bodies[body_id]
        body.elapsed_time += delta_seconds
        self._total_updates += 1

    def get_buoyancy(self, object_id: str) -> Optional[Dict[str, float]]:
        obj = self._water_objects.get(object_id)
        if obj is None:
            return None
        body = self._water_bodies.get(obj.water_body_id)
        if body is None:
            return None

        fluid_density = body.physics.density
        displaced_volume = obj.volume
        buoyant_force = fluid_density * displaced_volume * 9.81
        submerged_weight = obj.mass * 9.81 - buoyant_force
        buoyancy_factor = buoyant_force / (obj.mass * 9.81) if obj.mass > 0 else 1.0

        return {
            "buoyant_force": round(buoyant_force, 4),
            "submerged_weight": round(submerged_weight, 4),
            "buoyancy_factor": round(buoyancy_factor, 4),
            "submersion_depth": round(obj.buoyancy.submersion_depth, 4),
            "drag_coefficient": obj.buoyancy.drag_coefficient,
        }

    def add_water_object(
        self,
        name: str,
        water_body_id: str,
        mass: float = 1.0,
        volume: float = 0.01,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        buoyancy: Optional[BuoyancyParams] = None,
    ) -> Optional[str]:
        if water_body_id not in self._water_bodies:
            return None
        obj = WaterObject(
            name=name,
            mass=mass,
            volume=volume,
            position=position,
            water_body_id=water_body_id,
            buoyancy=buoyancy or BuoyancyParams(),
        )
        self._water_objects[obj.object_id] = obj
        return obj.object_id

    def remove_water_object(self, object_id: str) -> bool:
        if object_id not in self._water_objects:
            return False
        del self._water_objects[object_id]
        return True

    def get_wave_height(self, body_id: str, position: Tuple[float, float, float]) -> float:
        body = self._water_bodies.get(body_id)
        if body is None:
            return 0.0

        physics = body.physics
        x, y, z = position
        freq = physics.wave_frequency
        amp = physics.wave_amplitude

        if freq == 0.0 or amp == 0.0:
            return body.surface_height

        time_offset = body.elapsed_time
        wave_height = body.surface_height + amp * math.sin(
            x * freq * math.pi + time_offset
        ) * math.cos(z * freq * 0.7 * math.pi + time_offset * 0.5)

        return wave_height

    def get_all_water_bodies(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for body_id, body in self._water_bodies.items():
            result[body_id] = body.to_dict()
        return result

    def get_objects_in_body(self, body_id: str) -> List[Dict[str, Any]]:
        objects = []
        for obj in self._water_objects.values():
            if obj.water_body_id == body_id:
                objects.append(obj.to_dict())
        return objects

    def get_stats(self) -> Dict[str, Any]:
        body_details = {}
        for body_id, body in self._water_bodies.items():
            object_count = sum(
                1 for obj in self._water_objects.values()
                if obj.water_body_id == body_id
            )
            body_details[body_id] = {
                "name": body.name,
                "type": body.body_type.value,
                "surface_height": body.surface_height,
                "object_count": object_count,
            }
        return {
            "total_water_bodies": len(self._water_bodies),
            "total_water_objects": len(self._water_objects),
            "total_updates": self._total_updates,
            "water_bodies": body_details,
        }


def get_water_system() -> WaterSystem:
    return WaterSystem.get_instance()