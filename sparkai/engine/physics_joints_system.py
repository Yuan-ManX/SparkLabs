"""
SparkLabs Engine - Physics Joints System

Constraint-based physics connections between game objects for
AI-native game worlds. Manages joint creation with configurable
motor drives, spring/damper dynamics, joint limits, break force
thresholds, and soft constraint parameters for flexible connections.

Architecture:
  PhysicsJointsSystem
    |-- JointAnchor (3D attachment point per body)
    |-- JointConfig (joint type, bodies, limits, motor, spring)
    |-- JointInstance (runtime joint state, forces, broken status)
    |-- MotorController (velocity/position drive for motors)
    |-- LimitSolver (angular/linear constraint enforcement)
    |-- BreakDetector (force/torque threshold monitoring)

Joint Types:
  - PIN: single point rotation constraint
  - HINGE: single-axis rotation (like a door)
  - SLIDER: single-axis translation
  - SPRING: elastic distance constraint
  - DISTANCE: fixed-length rod constraint
  - WELD: rigid attachment (0 DOF)
  - ROPE: maximum-distance tether
  - PULLEY: coupled distance constraint
  - PRISMATIC: slider with no rotation
  - REVOLUTE: hinge with no translation
  - DOF6: configurable 6-DOF constraint
  - CONE_TWIST: angular swing + twist limit

Motor Modes:
  - DISABLED: motor inactive
  - VELOCITY: target angular/linear velocity
  - POSITION: target angular/linear position
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class JointType(Enum):
    PIN = "pin"
    HINGE = "hinge"
    SLIDER = "slider"
    SPRING = "spring"
    DISTANCE = "distance"
    WELD = "weld"
    ROPE = "rope"
    PULLEY = "pulley"
    PRISMATIC = "prismatic"
    REVOLUTE = "revolute"
    DOF6 = "dof6"
    CONE_TWIST = "cone_twist"


class JointMotorMode(Enum):
    DISABLED = "disabled"
    VELOCITY = "velocity"
    POSITION = "position"


@dataclass
class JointAnchor:
    anchor_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0

    def to_tuple(self) -> tuple:
        return (self.position_x, self.position_y, self.position_z)

    def set_position(self, x: float, y: float, z: float) -> None:
        self.position_x = x
        self.position_y = y
        self.position_z = z


@dataclass
class JointConfig:
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    joint_type: JointType = JointType.WELD
    body_a_id: str = ""
    body_b_id: str = ""
    anchor_a: JointAnchor = field(default_factory=JointAnchor)
    anchor_b: JointAnchor = field(default_factory=JointAnchor)
    break_force: float = float("inf")
    break_torque: float = float("inf")
    collide_connected: bool = False
    motor_enabled: bool = False
    motor_mode: JointMotorMode = JointMotorMode.DISABLED
    motor_target: float = 0.0
    motor_max_force: float = 1000.0
    spring_frequency: float = 0.0
    spring_damping: float = 0.0
    limits_enabled: bool = False
    lower_limit: float = -math.pi
    upper_limit: float = math.pi

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "joint_type": self.joint_type.value,
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "anchor_a": self.anchor_a.to_tuple(),
            "anchor_b": self.anchor_b.to_tuple(),
            "break_force": self.break_force,
            "break_torque": self.break_torque,
            "collide_connected": self.collide_connected,
            "motor_enabled": self.motor_enabled,
            "motor_mode": self.motor_mode.value,
            "motor_target": self.motor_target,
            "motor_max_force": self.motor_max_force,
            "spring_frequency": self.spring_frequency,
            "spring_damping": self.spring_damping,
            "limits_enabled": self.limits_enabled,
            "lower_limit": self.lower_limit,
            "upper_limit": self.upper_limit,
        }


@dataclass
class JointInstance:
    joint_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config_id: str = ""
    is_broken: bool = False
    current_force: float = 0.0
    current_torque: float = 0.0
    created: float = field(default_factory=time.time)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created

    def to_dict(self) -> Dict[str, Any]:
        return {
            "joint_id": self.joint_id,
            "config_id": self.config_id,
            "is_broken": self.is_broken,
            "current_force": round(self.current_force, 4),
            "current_torque": round(self.current_torque, 4),
            "age_seconds": round(self.age_seconds, 2),
            "created": self.created,
        }


JOINT_DOF_MAP: Dict[JointType, int] = {
    JointType.PIN: 2,
    JointType.HINGE: 1,
    JointType.SLIDER: 1,
    JointType.SPRING: 3,
    JointType.DISTANCE: 1,
    JointType.WELD: 0,
    JointType.ROPE: 2,
    JointType.PULLEY: 1,
    JointType.PRISMATIC: 1,
    JointType.REVOLUTE: 1,
    JointType.DOF6: 6,
    JointType.CONE_TWIST: 3,
}


class PhysicsJointsSystem:
    """
    Physics joints engine for constraint-based object coupling.

    Manages joint lifecycle from creation through runtime simulation
    to breaking and removal. Supports motor-driven joints, spring-damper
    elasticity, angular/linear limits, and break force thresholds.

    Usage:
        system = get_physics_joints_system()
        cfg = JointConfig(
            joint_type=JointType.HINGE,
            body_a_id="door", body_b_id="frame",
            anchor_a=JointAnchor(position_y=1.0),
        )
        joint = system.create_joint(cfg)
        system.enable_motor(joint.joint_id, JointMotorMode.VELOCITY, target=2.0)
    """

    _instance: Optional["PhysicsJointsSystem"] = None

    MAX_JOINTS = 1000
    DEFAULT_SPRING_FREQUENCY = 10.0
    DEFAULT_SPRING_DAMPING = 0.7

    @classmethod
    def get_instance(cls) -> "PhysicsJointsSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._configs: Dict[str, JointConfig] = {}
        self._instances: Dict[str, JointInstance] = {}
        self._body_index: Dict[str, List[str]] = {}
        self._total_created: int = 0
        self._total_broken: int = 0

    # ------------------------------------------------------------------
    # Joint lifecycle
    # ------------------------------------------------------------------

    def create_joint(self, config: JointConfig) -> JointInstance:
        """
        Register a new physics joint from configuration.

        Creates a runtime JointInstance bound to the JointConfig.
        If the config_id already exists, returns the existing instance
        without creating a duplicate.
        """
        if config.config_id in self._instances:
            return self._instances[config.config_id]

        instance = JointInstance(
            joint_id=uuid.uuid4().hex,
            config_id=config.config_id,
        )

        self._configs[config.config_id] = config
        self._instances[config.config_id] = instance
        self._total_created += 1

        self._index_body(config.body_a_id, config.config_id)
        self._index_body(config.body_b_id, config.config_id)

        return instance

    def configure_joint(self, joint_id: str, config_updates: Dict[str, Any]) -> None:
        """
        Update config fields for an existing joint.

        Accepted keys match JointConfig field names: joint_type,
        break_force, break_torque, collide_connected, motor_enabled,
        motor_mode, motor_target, motor_max_force, spring_frequency,
        spring_damping, limits_enabled, lower_limit, upper_limit.
        """
        config = self._configs.get(joint_id)
        if config is None:
            return

        allowed = {
            "joint_type", "break_force", "break_torque",
            "collide_connected", "motor_enabled", "motor_mode",
            "motor_target", "motor_max_force", "spring_frequency",
            "spring_damping", "limits_enabled", "lower_limit",
            "upper_limit",
        }

        for key, value in config_updates.items():
            if key not in allowed:
                continue
            if key == "joint_type" and isinstance(value, str):
                value = JointType(value)
            if key == "motor_mode" and isinstance(value, str):
                value = JointMotorMode(value)
            setattr(config, key, value)

    def remove_joint(self, joint_id: str) -> None:
        """Remove a joint and its config, cleaning up body indices."""
        config = self._configs.pop(joint_id, None)
        instance = self._instances.pop(joint_id, None)

        if instance and instance.is_broken:
            self._total_broken = max(0, self._total_broken - 1)

        if config is not None:
            self._unindex_body(config.body_a_id, joint_id)
            self._unindex_body(config.body_b_id, joint_id)

    # ------------------------------------------------------------------
    # Breaking and repair
    # ------------------------------------------------------------------

    def break_joint(self, joint_id: str) -> None:
        """
        Force-break a joint regardless of force thresholds.

        Records the break as if it exceeded structural limits and
        increments the broken count.
        """
        instance = self._instances.get(joint_id)
        if instance is None or instance.is_broken:
            return
        instance.is_broken = True
        self._total_broken += 1

    def repair_joint(self, joint_id: str) -> None:
        """
        Restore a previously broken joint to active state.

        Resets current force and torque readings to zero.
        """
        instance = self._instances.get(joint_id)
        if instance is None or not instance.is_broken:
            return
        instance.is_broken = False
        instance.current_force = 0.0
        instance.current_torque = 0.0
        self._total_broken = max(0, self._total_broken - 1)

    # ------------------------------------------------------------------
    # Motor control
    # ------------------------------------------------------------------

    def enable_motor(
        self,
        joint_id: str,
        mode: JointMotorMode,
        target: float = 0.0,
        max_force: float = 1000.0,
    ) -> None:
        """
        Activate motor drive on a joint.

        Args:
            joint_id: target joint config id
            mode: VELOCITY drives at constant speed, POSITION drives to angle
            target: desired velocity (rad/s, m/s) or position (rad, m)
            max_force: maximum force the motor can apply
        """
        config = self._configs.get(joint_id)
        if config is None:
            return
        config.motor_enabled = True
        config.motor_mode = mode
        config.motor_target = target
        config.motor_max_force = max_force

    def disable_motor(self, joint_id: str) -> None:
        """Deactivate motor drive on a joint."""
        config = self._configs.get(joint_id)
        if config is None:
            return
        config.motor_enabled = False
        config.motor_mode = JointMotorMode.DISABLED
        config.motor_target = 0.0

    # ------------------------------------------------------------------
    # Joint limits
    # ------------------------------------------------------------------

    def set_limits(self, joint_id: str, lower: float, upper: float) -> None:
        """
        Configure angular or linear displacement limits.

        For angular joints (HINGE, REVOLUTE, CONE_TWIST) values
        are in radians. For linear joints (SLIDER, PRISMATIC)
        values are in world units. Lower must be <= upper.
        """
        config = self._configs.get(joint_id)
        if config is None:
            return
        config.lower_limit = lower
        config.upper_limit = max(lower, upper)

    def enable_limits(self, joint_id: str) -> None:
        """Activate limit enforcement for a joint."""
        config = self._configs.get(joint_id)
        if config is None:
            return
        config.limits_enabled = True

    def disable_limits(self, joint_id: str) -> None:
        """Deactivate limit enforcement for a joint."""
        config = self._configs.get(joint_id)
        if config is None:
            return
        config.limits_enabled = False

    # ------------------------------------------------------------------
    # Spring configuration
    # ------------------------------------------------------------------

    def set_spring(self, joint_id: str, frequency: float, damping: float) -> None:
        """
        Configure soft constraint spring parameters.

        Frequency controls stiffness (Hz, higher = stiffer).
        Damping controls energy dissipation (0 = undamped, 1 = critically damped).
        Set frequency to 0 to disable spring behavior.
        """
        config = self._configs.get(joint_id)
        if config is None:
            return
        config.spring_frequency = max(0.0, frequency)
        config.spring_damping = max(0.0, min(1.0, damping))

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_joints_for_body(self, body_id: str) -> List[JointInstance]:
        """
        Return all joint instances connected to a given body.

        Returns an empty list if the body has no joints attached.
        """
        config_ids = self._body_index.get(body_id, [])
        return [
            self._instances[cid]
            for cid in config_ids
            if cid in self._instances
        ]

    def get_config(self, joint_id: str) -> Optional[JointConfig]:
        """Retrieve the configuration for a joint by id."""
        return self._configs.get(joint_id)

    def get_joint_instance(self, joint_id: str) -> Optional[JointInstance]:
        """Retrieve the runtime instance for a joint by id."""
        return self._instances.get(joint_id)

    def get_all_joints(self) -> List[JointInstance]:
        """Return all active joint instances."""
        return list(self._instances.values())

    def get_all_configs(self) -> List[JointConfig]:
        """Return all joint configurations."""
        return list(self._configs.values())

    # ------------------------------------------------------------------
    # Simulation helpers
    # ------------------------------------------------------------------

    def check_break_force(
        self, joint_id: str, applied_force: float, applied_torque: float
    ) -> bool:
        """
        Evaluate whether external forces exceed joint break thresholds.

        Returns True if the joint broke during this evaluation.
        If the joint was already broken, always returns True.
        """
        instance = self._instances.get(joint_id)
        config = self._configs.get(joint_id)
        if instance is None or config is None:
            return True
        if instance.is_broken:
            return True

        instance.current_force = applied_force
        instance.current_torque = applied_torque

        if applied_force >= config.break_force or applied_torque >= config.break_torque:
            self.break_joint(joint_id)
            return True

        return False

    def compute_spring_force(
        self, joint_id: str, displacement: float, velocity: float
    ) -> float:
        """
        Calculate spring-damper restoring force.

        Uses Hooke's law with configurable damping term:
          F = -k * x - c * v
        where k = frequency^2 * mass (approximate), c = 2 * damping * sqrt(k)

        Returns zero if spring parameters are not configured.
        """
        config = self._configs.get(joint_id)
        if config is None or config.spring_frequency <= 0:
            return 0.0

        stiffness = config.spring_frequency ** 2
        critical_damping = 2.0 * config.spring_damping * math.sqrt(stiffness)
        return -stiffness * displacement - critical_damping * velocity

    def apply_limit_constraint(self, joint_id: str, current_value: float) -> float:
        """
        Clamp a position/angle value to joint limits.

        Returns the corrected value if limits are enabled and the
        current value exceeds bounds; otherwise returns the input unchanged.
        """
        config = self._configs.get(joint_id)
        if config is None or not config.limits_enabled:
            return current_value
        return max(config.lower_limit, min(config.upper_limit, current_value))

    def compute_motor_drive(
        self, joint_id: str, current_value: float, current_velocity: float
    ) -> float:
        """
        Compute motor force/torque to drive toward a target.

        For VELOCITY mode: applies force proportional to velocity error.
        For POSITION mode: applies force proportional to position error.
        Returns 0 if the motor is disabled or force would exceed max.
        """
        config = self._configs.get(joint_id)
        if config is None or not config.motor_enabled:
            return 0.0

        if config.motor_mode == JointMotorMode.VELOCITY:
            error = config.motor_target - current_velocity
        elif config.motor_mode == JointMotorMode.POSITION:
            error = config.motor_target - current_value
        else:
            return 0.0

        drive = error * 50.0
        return max(-config.motor_max_force, min(config.motor_max_force, drive))

    # ------------------------------------------------------------------
    # Stats and diagnostics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Return aggregate statistics for the joint system.

        Includes total joint count, type distribution, broken count,
        active motor count, and soft constraint summary.
        """
        by_type: Dict[str, int] = {jt.value: 0 for jt in JointType}
        active_motors = 0
        spring_joints = 0
        limited_joints = 0

        for config in self._configs.values():
            by_type[config.joint_type.value] += 1
            if config.motor_enabled:
                active_motors += 1
            if config.spring_frequency > 0:
                spring_joints += 1
            if config.limits_enabled:
                limited_joints += 1

        broken_count = self._total_broken

        return {
            "total_joints": len(self._instances),
            "by_type": {k: v for k, v in by_type.items() if v > 0},
            "broken_count": broken_count,
            "active_motors": active_motors,
            "spring_joints": spring_joints,
            "limited_joints": limited_joints,
            "total_created": self._total_created,
        }

    def clear(self) -> None:
        """Remove all joints, configs, and indices from the system."""
        self._configs.clear()
        self._instances.clear()
        self._body_index.clear()
        self._total_created = 0
        self._total_broken = 0

    # ------------------------------------------------------------------
    # Internal indexing
    # ------------------------------------------------------------------

    def _index_body(self, body_id: str, config_id: str) -> None:
        if not body_id:
            return
        if body_id not in self._body_index:
            self._body_index[body_id] = []
        if config_id not in self._body_index[body_id]:
            self._body_index[body_id].append(config_id)

    def _unindex_body(self, body_id: str, config_id: str) -> None:
        if body_id in self._body_index:
            try:
                self._body_index[body_id].remove(config_id)
            except ValueError:
                pass
            if not self._body_index[body_id]:
                del self._body_index[body_id]


# ------------------------------------------------------------------
# Module-level accessor
# ------------------------------------------------------------------

def get_physics_joints_system() -> PhysicsJointsSystem:
    return PhysicsJointsSystem.get_instance()