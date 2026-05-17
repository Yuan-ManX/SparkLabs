"""
SparkLabs Agent - Physics Parameter Tuner

AI-assisted physics parameter tuning engine for the SparkLabs AI-native
game engine. Provides automated analysis and optimization of physics
parameters across multiple domains including gravity, collision, joints,
ragdoll, vehicle, cloth, fluid, and soft-body physics. Generates
domain-specific presets, records tuning sessions for traceability, and
supports AI-driven parameter suggestions based on entity characteristics.

Architecture:
  PhysicsTuner
    |-- PhysicsParameter (individual tunable physics value)
    |-- TunerPreset (named collection of parameter values)
    |-- TuningSession (recorded before/after tuning snapshots)
    |-- PresetComparison (structured comparison between presets)
"""

from __future__ import annotations

import copy
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PhysicsDomain(Enum):
    GRAVITY = "gravity"
    COLLISION = "collision"
    JOINTS = "joints"
    RAGDOLL = "ragdoll"
    VEHICLE = "vehicle"
    CLOTH = "cloth"
    FLUID = "fluid"
    SOFT_BODY = "soft_body"


class TunerPresetType(Enum):
    REALISTIC = "realistic"
    ARCADE = "arcade"
    CINEMATIC = "cinematic"
    PLATFORMER = "platformer"
    TOP_DOWN = "top_down"
    ZERO_G = "zero_g"


class ParameterSource(Enum):
    AI_GENERATED = "ai_generated"
    PLAYTEST_FEEDBACK = "playtest_feedback"
    MANUAL = "manual"
    TEMPLATE = "template"


@dataclass
class PhysicsParameter:
    param_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    domain: PhysicsDomain = PhysicsDomain.GRAVITY
    current_value: float = 0.0
    default_value: float = 0.0
    min_value: float = 0.0
    max_value: float = 1.0
    sensitivity: float = 0.5
    description: str = ""
    unit: str = ""

    def __post_init__(self):
        self.current_value = max(self.min_value, min(self.max_value, self.current_value))
        self.default_value = max(self.min_value, min(self.max_value, self.default_value))

    def clamp(self, value: float) -> float:
        return max(self.min_value, min(self.max_value, value))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "param_id": self.param_id,
            "name": self.name,
            "domain": self.domain.value,
            "current_value": self.current_value,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "sensitivity": self.sensitivity,
            "description": self.description,
            "unit": self.unit,
        }


@dataclass
class TunerPreset:
    preset_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    preset_type: TunerPresetType = TunerPresetType.REALISTIC
    parameters: Dict[str, float] = field(default_factory=dict)
    source: ParameterSource = ParameterSource.TEMPLATE
    quality_score: float = 0.5
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        self.quality_score = max(0.0, min(1.0, self.quality_score))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "name": self.name,
            "preset_type": self.preset_type.value,
            "parameter_count": len(self.parameters),
            "source": self.source.value,
            "quality_score": self.quality_score,
            "created_at": self.created_at,
        }


@dataclass
class TuningSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    target_entity: str = ""
    entity_type: str = ""
    applied_preset_id: str = ""
    parameters_before: Dict[str, float] = field(default_factory=dict)
    parameters_after: Dict[str, float] = field(default_factory=dict)
    feedback: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        changed = {
            k: {"before": self.parameters_before.get(k), "after": v}
            for k, v in self.parameters_after.items()
            if self.parameters_before.get(k) != v
        }
        return {
            "session_id": self.session_id,
            "target_entity": self.target_entity,
            "entity_type": self.entity_type,
            "applied_preset_id": self.applied_preset_id,
            "parameters_changed": len(changed),
            "changes": changed,
            "feedback": self.feedback[:200] if self.feedback else "",
            "created_at": self.created_at,
        }


class PhysicsTuner:
    _instance: Optional["PhysicsTuner"] = None
    _lock: threading.RLock = threading.RLock()

    # Gravity presets in m/s^2
    EARTH_GRAVITY = -9.81
    MOON_GRAVITY = -1.62
    MARS_GRAVITY = -3.71
    ARCADE_GRAVITY = -15.0
    PLATFORMER_GRAVITY = -25.0
    LOW_GRAVITY = -3.0

    def __init__(self):
        self._parameters: Dict[str, PhysicsParameter] = {}
        self._presets: Dict[str, TunerPreset] = {}
        self._sessions: List[TuningSession] = []
        self._session_count: int = 0
        self._lock = threading.RLock()
        self._initialize_parameters()

    @classmethod
    def get_instance(cls) -> "PhysicsTuner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _initialize_parameters(self):
        gravity_params = [
            ("gravity_scale", "Gravity Scale", 1.0, 0.0, 5.0, 0.8, "Multiplier applied to world gravity vector", "x"),
            ("gravity_x", "Gravity X", 0.0, -50.0, 50.0, 0.3, "Horizontal gravity component", "m/s^2"),
            ("gravity_y", "Gravity Y", -9.81, -50.0, 50.0, 0.9, "Vertical gravity component", "m/s^2"),
            ("gravity_z", "Gravity Z", 0.0, -50.0, 50.0, 0.3, "Depth gravity component", "m/s^2"),
        ]
        collision_params = [
            ("bounce_threshold", "Bounce Threshold", 2.0, 0.0, 20.0, 0.6, "Minimum velocity to trigger bounce", "m/s"),
            ("bounciness", "Bounciness", 0.3, 0.0, 1.0, 0.7, "Coefficient of restitution", ""),
            ("friction_static", "Static Friction", 0.6, 0.0, 1.0, 0.5, "Static friction coefficient", ""),
            ("friction_dynamic", "Dynamic Friction", 0.4, 0.0, 1.0, 0.5, "Dynamic friction coefficient", ""),
            ("collision_margin", "Collision Margin", 0.01, 0.001, 0.5, 0.4, "Collision detection margin", "m"),
            ("penetration_recovery", "Penetration Recovery", 0.8, 0.0, 1.0, 0.5, "Penetration resolution speed factor", ""),
        ]
        joints_params = [
            ("joint_damping", "Joint Damping", 0.2, 0.0, 1.0, 0.5, "Joint movement damping", ""),
            ("joint_stiffness", "Joint Stiffness", 100.0, 1.0, 10000.0, 0.7, "Joint spring stiffness", "N/m"),
            ("max_joint_force", "Max Joint Force", 1000.0, 0.0, 100000.0, 0.4, "Maximum force before joint breaks", "N"),
            ("joint_break_torque", "Joint Break Torque", 500.0, 0.0, 50000.0, 0.4, "Maximum torque before joint breaks", "Nm"),
        ]
        ragdoll_params = [
            ("ragdoll_mass_scale", "Ragdoll Mass Scale", 1.0, 0.1, 5.0, 0.6, "Mass multiplier for ragdoll bodies", "x"),
            ("ragdoll_damping", "Ragdoll Damping", 0.1, 0.0, 1.0, 0.5, "Linear damping applied to ragdoll limbs", ""),
            ("ragdoll_angular_damping", "Ragdoll Angular Damping", 0.2, 0.0, 1.0, 0.5, "Angular damping applied to ragdoll limbs", ""),
            ("ragdoll_blend_time", "Ragdoll Blend Time", 0.2, 0.0, 2.0, 0.6, "Animation-to-ragdoll blend duration", "s"),
            ("ragdoll_sleep_threshold", "Ragdoll Sleep Threshold", 0.05, 0.0, 1.0, 0.3, "Velocity threshold for ragdoll sleep", "m/s"),
        ]
        vehicle_params = [
            ("suspension_stiffness", "Suspension Stiffness", 5000.0, 100.0, 50000.0, 0.8, "Suspension spring stiffness", "N/m"),
            ("suspension_damping", "Suspension Damping", 500.0, 10.0, 5000.0, 0.7, "Suspension damping coefficient", "Ns/m"),
            ("suspension_length", "Suspension Length", 0.3, 0.05, 1.0, 0.6, "Maximum suspension travel", "m"),
            ("tire_friction", "Tire Friction", 1.0, 0.1, 5.0, 0.8, "Tire grip coefficient", ""),
            ("engine_power", "Engine Power", 5000.0, 100.0, 50000.0, 0.9, "Maximum engine output", "W"),
            ("brake_torque", "Brake Torque", 3000.0, 100.0, 20000.0, 0.7, "Maximum braking torque", "Nm"),
            ("mass_center_height", "Mass Center Height", 0.5, 0.1, 2.0, 0.6, "Center of mass height above ground", "m"),
        ]
        cloth_params = [
            ("cloth_stiffness", "Cloth Stiffness", 100.0, 1.0, 10000.0, 0.7, "Cloth stretching resistance", "N/m"),
            ("cloth_bending", "Cloth Bending", 10.0, 0.0, 1000.0, 0.6, "Cloth bending resistance", ""),
            ("cloth_damping", "Cloth Damping", 0.5, 0.0, 1.0, 0.5, "Cloth movement damping", ""),
            ("cloth_air_density", "Cloth Air Density", 1.2, 0.0, 5.0, 0.4, "Air density for cloth drag calculation", "kg/m^3"),
        ]
        fluid_params = [
            ("fluid_density", "Fluid Density", 1000.0, 100.0, 10000.0, 0.7, "Base fluid density", "kg/m^3"),
            ("fluid_viscosity", "Fluid Viscosity", 1.0, 0.0, 100.0, 0.6, "Fluid viscosity coefficient", "Pa*s"),
            ("fluid_drag", "Fluid Drag", 0.8, 0.0, 5.0, 0.6, "Drag force multiplier in fluid", ""),
            ("buoyancy_scale", "Buoyancy Scale", 1.0, 0.0, 5.0, 0.7, "Buoyancy force multiplier", "x"),
        ]
        soft_body_params = [
            ("soft_body_stiffness", "Soft Body Stiffness", 100.0, 1.0, 10000.0, 0.8, "Soft body spring stiffness", "N/m"),
            ("soft_body_volume", "Volume Conservation", 1.0, 0.0, 1.0, 0.6, "Volume conservation strength", ""),
            ("soft_body_damping", "Soft Body Damping", 0.3, 0.0, 1.0, 0.5, "Soft body deformation damping", ""),
        ]

        all_params = [
            (PhysicsDomain.GRAVITY, gravity_params),
            (PhysicsDomain.COLLISION, collision_params),
            (PhysicsDomain.JOINTS, joints_params),
            (PhysicsDomain.RAGDOLL, ragdoll_params),
            (PhysicsDomain.VEHICLE, vehicle_params),
            (PhysicsDomain.CLOTH, cloth_params),
            (PhysicsDomain.FLUID, fluid_params),
            (PhysicsDomain.SOFT_BODY, soft_body_params),
        ]

        for domain, params in all_params:
            for key, display_name, default, min_v, max_v, sensitivity, desc, unit in params:
                param = PhysicsParameter(
                    name=key,
                    domain=domain,
                    current_value=default,
                    default_value=default,
                    min_value=min_v,
                    max_value=max_v,
                    sensitivity=sensitivity,
                    description=desc,
                    unit=unit,
                )
                self._parameters[param.param_id] = param

    def create_preset(
        self,
        name: str,
        preset_type: TunerPresetType = TunerPresetType.REALISTIC,
        parameters: Optional[Dict[str, float]] = None,
        source: ParameterSource = ParameterSource.AI_GENERATED,
        quality_score: float = 0.5,
    ) -> TunerPreset:
        preset = TunerPreset(
            name=name,
            preset_type=preset_type,
            parameters=parameters or {},
            source=source,
            quality_score=quality_score,
        )
        with self._lock:
            self._presets[preset.preset_id] = preset
        return preset

    def get_preset(self, preset_id: str) -> Optional[TunerPreset]:
        with self._lock:
            return self._presets.get(preset_id)

    def apply_preset(self, preset_id: str, target_entity: str, entity_type: str = "",
                     feedback: str = "") -> Optional[TuningSession]:
        preset = self.get_preset(preset_id)
        if preset is None:
            return None

        before_snapshot: Dict[str, float] = {}
        for param in self._parameters.values():
            before_snapshot[param.name] = param.current_value

        applied_count = 0
        for param in self._parameters.values():
            if param.name in preset.parameters:
                new_value = param.clamp(preset.parameters[param.name])
                param.current_value = new_value
                applied_count += 1

        after_snapshot: Dict[str, float] = {}
        for param in self._parameters.values():
            after_snapshot[param.name] = param.current_value

        session = TuningSession(
            target_entity=target_entity,
            entity_type=entity_type,
            applied_preset_id=preset_id,
            parameters_before=before_snapshot,
            parameters_after=after_snapshot,
            feedback=feedback,
        )

        with self._lock:
            self._sessions.append(session)
            self._session_count += 1

        return session

    def analyze_entity(self, entity_type: str, mass: float = 1.0, size: float = 1.0,
                       speed: float = 1.0, environment: str = "default") -> Dict[str, Any]:
        suggestions: Dict[str, float] = {}
        reasoning: List[str] = []

        for param in self._parameters.values():
            suggested = param.default_value

            if param.domain == PhysicsDomain.GRAVITY:
                if entity_type in ("character", "player"):
                    if environment == "platformer":
                        suggested = -25.0
                        reasoning.append(f"{param.name}: platformer gravity for character")
                    elif environment == "space":
                        suggested = -1.62
                        reasoning.append(f"{param.name}: lunar-scale gravity for space environment")
                    else:
                        suggested = -9.81
                if entity_type == "projectile":
                    suggested = -9.81 * 0.5
                    reasoning.append(f"{param.name}: reduced gravity for projectile arc")

            elif param.domain == PhysicsDomain.COLLISION:
                if entity_type in ("character", "player"):
                    if param.name == "bounciness":
                        suggested = 0.1
                    elif param.name == "friction_static":
                        suggested = 0.8
                    elif param.name == "friction_dynamic":
                        suggested = 0.6
                    reasoning.append(f"{param.name}: character-appropriate collision")

                elif entity_type == "bouncy_object":
                    if param.name == "bounciness":
                        suggested = 0.9
                    elif param.name == "friction_static":
                        suggested = 0.2
                    reasoning.append(f"{param.name}: high bounciness for elastic object")

                elif entity_type == "vehicle":
                    if param.name == "bounciness":
                        suggested = 0.05
                    elif param.name == "friction_dynamic":
                        suggested = 0.9
                    reasoning.append(f"{param.name}: vehicle collision properties")

            elif param.domain == PhysicsDomain.VEHICLE:
                mass_factor = mass / 1500.0
                if param.name == "suspension_stiffness":
                    suggested = 5000.0 * mass_factor
                elif param.name == "suspension_damping":
                    suggested = 500.0 * mass_factor
                elif param.name == "engine_power":
                    suggested = 10000.0 * mass_factor
                reasoning.append(f"{param.name}: vehicle tuned for mass={mass}kg")

            elif param.domain == PhysicsDomain.RAGDOLL:
                if entity_type == "heavy_character":
                    if param.name == "ragdoll_mass_scale":
                        suggested = 2.0
                    elif param.name == "ragdoll_damping":
                        suggested = 0.3
                    reasoning.append(f"{param.name}: heavy ragdoll tuning")

            elif param.domain == PhysicsDomain.CLOTH:
                if entity_type == "light_fabric":
                    if param.name == "cloth_stiffness":
                        suggested = 50.0
                    elif param.name == "cloth_damping":
                        suggested = 0.3
                    reasoning.append(f"{param.name}: lightweight fabric tuning")
                elif entity_type == "heavy_fabric":
                    if param.name == "cloth_stiffness":
                        suggested = 500.0
                    reasoning.append(f"{param.name}: heavy fabric tuning")

            elif param.domain == PhysicsDomain.FLUID:
                if environment == "water":
                    if param.name == "fluid_density":
                        suggested = 1000.0
                    elif param.name == "buoyancy_scale":
                        suggested = 1.0
                    reasoning.append(f"{param.name}: water environment tuning")
                elif environment == "lava":
                    if param.name == "fluid_density":
                        suggested = 3000.0
                    elif param.name == "fluid_viscosity":
                        suggested = 50.0
                    reasoning.append(f"{param.name}: lava environment tuning")

            suggestions[param.name] = round(suggested, 4)

        return {
            "entity_type": entity_type,
            "mass": mass,
            "size": size,
            "speed": speed,
            "environment": environment,
            "suggestions": suggestions,
            "reasoning": reasoning,
            "suggestion_count": len(suggestions),
        }

    def tune_gravity(self, target_gravity_y: float, gravity_scale: float = 1.0) -> Dict[str, float]:
        changes: Dict[str, float] = {}
        for param in self._parameters.values():
            if param.domain == PhysicsDomain.GRAVITY:
                if param.name == "gravity_y":
                    new_val = param.clamp(target_gravity_y)
                    param.current_value = new_val
                    changes[param.name] = new_val
                elif param.name == "gravity_scale":
                    new_val = param.clamp(gravity_scale)
                    param.current_value = new_val
                    changes[param.name] = new_val
                else:
                    changes[param.name] = param.current_value
        return changes

    def tune_movement_feel(
        self,
        gravity_scale: Optional[float] = None,
        friction: Optional[float] = None,
        damping: Optional[float] = None,
        responsiveness: float = 0.5,
    ) -> Dict[str, float]:
        changes: Dict[str, float] = {}
        for param in self._parameters.values():
            if gravity_scale is not None and param.name == "gravity_scale":
                new_val = param.clamp(gravity_scale)
                param.current_value = new_val
                changes[param.name] = new_val
            if friction is not None and param.name in ("friction_static", "friction_dynamic"):
                new_val = param.clamp(friction)
                param.current_value = new_val
                changes[param.name] = new_val
            if damping is not None and param.name in ("ragdoll_damping", "ragdoll_angular_damping",
                                                       "cloth_damping", "joint_damping"):
                new_val = param.clamp(damping)
                param.current_value = new_val
                changes[param.name] = new_val
        if gravity_scale is not None:
            gravity_ease = 1.0 - responsiveness
            for param in self._parameters.values():
                if param.domain == PhysicsDomain.GRAVITY and param.name not in changes:
                    adjusted = param.default_value * (1.0 + gravity_ease * 0.5)
                    new_val = param.clamp(adjusted)
                    param.current_value = new_val
                    changes[param.name] = new_val
        return changes

    def tune_collision_response(
        self,
        bounciness: Optional[float] = None,
        friction_static: Optional[float] = None,
        friction_dynamic: Optional[float] = None,
        penetration_recovery: Optional[float] = None,
    ) -> Dict[str, float]:
        changes: Dict[str, float] = {}
        target_map = {
            "bounciness": bounciness,
            "friction_static": friction_static,
            "friction_dynamic": friction_dynamic,
            "penetration_recovery": penetration_recovery,
        }
        for param in self._parameters.values():
            if param.name in target_map and target_map[param.name] is not None:
                new_val = param.clamp(target_map[param.name])
                param.current_value = new_val
                changes[param.name] = new_val
        return changes

    def generate_default_presets(self) -> List[TunerPreset]:
        presets: List[TunerPreset] = []

        realistic_params = {}
        for param in self._parameters.values():
            if param.domain == PhysicsDomain.GRAVITY:
                if param.name == "gravity_y":
                    realistic_params[param.name] = self.EARTH_GRAVITY
                elif param.name == "gravity_scale":
                    realistic_params[param.name] = 1.0
            elif param.domain == PhysicsDomain.COLLISION:
                if param.name == "bounciness":
                    realistic_params[param.name] = 0.2
                elif param.name == "friction_static":
                    realistic_params[param.name] = 0.6
                elif param.name == "friction_dynamic":
                    realistic_params[param.name] = 0.4
            elif param.domain == PhysicsDomain.VEHICLE:
                if param.name == "suspension_stiffness":
                    realistic_params[param.name] = 5000.0
                elif param.name == "tire_friction":
                    realistic_params[param.name] = 1.2
                elif param.name == "engine_power":
                    realistic_params[param.name] = 10000.0
            else:
                realistic_params[param.name] = param.default_value
        presets.append(self.create_preset(
            "Realistic Physics", TunerPresetType.REALISTIC, realistic_params,
            ParameterSource.TEMPLATE, 0.85,
        ))

        arcade_params = {}
        for param in self._parameters.values():
            if param.domain == PhysicsDomain.GRAVITY:
                if param.name == "gravity_y":
                    arcade_params[param.name] = self.ARCADE_GRAVITY
                elif param.name == "gravity_scale":
                    arcade_params[param.name] = 1.5
            elif param.domain == PhysicsDomain.COLLISION:
                if param.name == "bounciness":
                    arcade_params[param.name] = 0.5
                elif param.name == "friction_static":
                    arcade_params[param.name] = 0.3
                elif param.name == "friction_dynamic":
                    arcade_params[param.name] = 0.2
            elif param.domain == PhysicsDomain.VEHICLE:
                if param.name == "suspension_stiffness":
                    arcade_params[param.name] = 3000.0
                elif param.name == "tire_friction":
                    arcade_params[param.name] = 2.0
                elif param.name == "engine_power":
                    arcade_params[param.name] = 20000.0
            else:
                arcade_params[param.name] = param.default_value
        presets.append(self.create_preset(
            "Arcade Physics", TunerPresetType.ARCADE, arcade_params,
            ParameterSource.TEMPLATE, 0.80,
        ))

        cinematic_params = {}
        for param in self._parameters.values():
            if param.domain == PhysicsDomain.GRAVITY:
                if param.name == "gravity_y":
                    cinematic_params[param.name] = -5.0
                elif param.name == "gravity_scale":
                    cinematic_params[param.name] = 0.6
            elif param.domain == PhysicsDomain.COLLISION:
                if param.name == "bounciness":
                    cinematic_params[param.name] = 0.1
                elif param.name == "penetration_recovery":
                    cinematic_params[param.name] = 0.9
            elif param.domain == PhysicsDomain.RAGDOLL:
                if param.name == "ragdoll_blend_time":
                    cinematic_params[param.name] = 0.5
                elif param.name == "ragdoll_damping":
                    cinematic_params[param.name] = 0.3
            elif param.domain == PhysicsDomain.CLOTH:
                if param.name == "cloth_bending":
                    cinematic_params[param.name] = 5.0
            else:
                cinematic_params[param.name] = param.default_value
        presets.append(self.create_preset(
            "Cinematic Physics", TunerPresetType.CINEMATIC, cinematic_params,
            ParameterSource.TEMPLATE, 0.75,
        ))

        platformer_params = {}
        for param in self._parameters.values():
            if param.domain == PhysicsDomain.GRAVITY:
                if param.name == "gravity_y":
                    platformer_params[param.name] = self.PLATFORMER_GRAVITY
                elif param.name == "gravity_scale":
                    platformer_params[param.name] = 2.5
            elif param.domain == PhysicsDomain.COLLISION:
                if param.name == "bounciness":
                    platformer_params[param.name] = 0.15
                elif param.name == "friction_static":
                    platformer_params[param.name] = 1.0
                elif param.name == "friction_dynamic":
                    platformer_params[param.name] = 0.8
            else:
                platformer_params[param.name] = param.default_value
        presets.append(self.create_preset(
            "Platformer Physics", TunerPresetType.PLATFORMER, platformer_params,
            ParameterSource.TEMPLATE, 0.82,
        ))

        topdown_params = {}
        for param in self._parameters.values():
            if param.domain == PhysicsDomain.GRAVITY:
                if param.name == "gravity_y":
                    topdown_params[param.name] = 0.0
                elif param.name == "gravity_scale":
                    topdown_params[param.name] = 0.0
            elif param.domain == PhysicsDomain.COLLISION:
                if param.name == "friction_dynamic":
                    topdown_params[param.name] = 0.9
                elif param.name == "bounciness":
                    topdown_params[param.name] = 0.0
            else:
                topdown_params[param.name] = param.default_value
        presets.append(self.create_preset(
            "Top-Down Physics", TunerPresetType.TOP_DOWN, topdown_params,
            ParameterSource.TEMPLATE, 0.78,
        ))

        zerog_params = {}
        for param in self._parameters.values():
            if param.domain == PhysicsDomain.GRAVITY:
                zerog_params[param.name] = 0.0
            elif param.domain == PhysicsDomain.COLLISION:
                if param.name == "bounciness":
                    zerog_params[param.name] = 0.8
                elif param.name == "penetration_recovery":
                    zerog_params[param.name] = 0.5
            elif param.domain == PhysicsDomain.RAGDOLL:
                if param.name == "ragdoll_damping":
                    zerog_params[param.name] = 0.0
                elif param.name == "ragdoll_angular_damping":
                    zerog_params[param.name] = 0.0
                elif param.name == "ragdoll_blend_time":
                    zerog_params[param.name] = 1.0
            else:
                zerog_params[param.name] = param.default_value
        presets.append(self.create_preset(
            "Zero-G Physics", TunerPresetType.ZERO_G, zerog_params,
            ParameterSource.TEMPLATE, 0.70,
        ))

        return presets

    def record_tuning_session(
        self,
        target_entity: str,
        entity_type: str,
        applied_preset_id: str,
        parameters_before: Dict[str, float],
        parameters_after: Dict[str, float],
        feedback: str = "",
    ) -> TuningSession:
        session = TuningSession(
            target_entity=target_entity,
            entity_type=entity_type,
            applied_preset_id=applied_preset_id,
            parameters_before=parameters_before,
            parameters_after=parameters_after,
            feedback=feedback,
        )
        with self._lock:
            self._sessions.append(session)
            self._session_count += 1
        return session

    def get_tuning_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self._sessions[-limit:]]

    def compare_presets(self, preset_id_a: str, preset_id_b: str) -> Optional[Dict[str, Any]]:
        preset_a = self.get_preset(preset_id_a)
        preset_b = self.get_preset(preset_id_b)
        if preset_a is None or preset_b is None:
            return None

        all_keys = set(preset_a.parameters.keys()) | set(preset_b.parameters.keys())
        differences: List[Dict[str, Any]] = []
        for key in sorted(all_keys):
            val_a = preset_a.parameters.get(key)
            val_b = preset_b.parameters.get(key)
            if val_a != val_b:
                differences.append({
                    "parameter": key,
                    "preset_a_value": val_a,
                    "preset_b_value": val_b,
                    "delta": round((val_b or 0) - (val_a or 0), 4),
                })

        return {
            "preset_a": {"id": preset_a.preset_id, "name": preset_a.name, "type": preset_a.preset_type.value},
            "preset_b": {"id": preset_b.preset_id, "name": preset_b.name, "type": preset_b.preset_type.value},
            "differences": differences,
            "difference_count": len(differences),
            "similarity": round(
                1.0 - len(differences) / max(1, len(all_keys)), 4
            ),
        }

    def export_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        preset = self.get_preset(preset_id)
        if preset is None:
            return None

        parameter_details: List[Dict[str, Any]] = []
        for param in self._parameters.values():
            if param.name in preset.parameters:
                parameter_details.append({
                    "name": param.name,
                    "domain": param.domain.value,
                    "value": preset.parameters[param.name],
                    "default": param.default_value,
                    "unit": param.unit,
                    "description": param.description,
                })

        return {
            "preset": preset.to_dict(),
            "parameters": parameter_details,
            "exported_at": time.time(),
        }

    def get_stats(self) -> Dict[str, Any]:
        domain_counts: Dict[str, int] = {}
        for param in self._parameters.values():
            key = param.domain.value
            domain_counts[key] = domain_counts.get(key, 0) + 1

        return {
            "total_parameters": len(self._parameters),
            "total_presets": len(self._presets),
            "total_sessions": self._session_count,
            "parameters_by_domain": domain_counts,
            "domains": [d.value for d in PhysicsDomain],
            "preset_types": [p.value for p in TunerPresetType],
            "parameter_sources": [s.value for s in ParameterSource],
        }


def get_physics_tuner() -> PhysicsTuner:
    return PhysicsTuner.get_instance()