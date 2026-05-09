"""
SparkLabs Engine - Physics Constraints

Physics constraint and joint system for the SparkLabs AI-native
game engine. Provides mechanical constraints (spring, hinge, slider,
distance, pin, weld) that connect physics bodies and restrict their
relative motion. AI agents define constraint configurations to
assemble complex physical structures from simple bodies.

Architecture:
  PhysicsConstraints
    |-- Constraint (base: body_a, body_b, anchor points)
    |-- SpringConstraint (elastic force between two bodies)
    |-- HingeConstraint (rotational pivot around a point)
    |-- SliderConstraint (linear motion along an axis)
    |-- DistanceConstraint (fixed separation distance)
    |-- WeldConstraint (rigidly fused connection)
    |-- ConstraintSolver (resolve forces per constraint type)
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ConstraintType(Enum):
    SPRING = "spring"
    HINGE = "hinge"
    SLIDER = "slider"
    DISTANCE = "distance"
    PIN = "pin"
    WELD = "weld"


class ConstraintState(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BROKEN = "broken"
    SOLVED = "solved"


@dataclass
class Constraint:
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    constraint_type: ConstraintType = ConstraintType.DISTANCE
    body_a_id: str = ""
    body_b_id: str = ""
    anchor_a: Tuple[float, float] = (0.0, 0.0)
    anchor_b: Tuple[float, float] = (0.0, 0.0)
    state: ConstraintState = ConstraintState.ACTIVE
    break_force: float = 0.0
    stiffness: float = 0.5
    damping: float = 0.1
    applied_force: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "constraint_id": self.constraint_id,
            "name": self.name,
            "type": self.constraint_type.value,
            "body_a": self.body_a_id,
            "body_b": self.body_b_id,
            "state": self.state.value,
            "stiffness": self.stiffness,
        }


@dataclass
class SpringConstraint(Constraint):
    rest_length: float = 50.0
    min_length: float = 0.0
    max_length: float = 200.0
    spring_coefficient: float = 100.0
    oscillation_frequency: float = 1.0

    def __post_init__(self):
        self.constraint_type = ConstraintType.SPRING

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "rest_length": self.rest_length,
            "spring_coefficient": self.spring_coefficient,
        })
        return base


@dataclass
class HingeConstraint(Constraint):
    min_angle: float = -math.pi
    max_angle: float = math.pi
    motor_enabled: bool = False
    motor_speed: float = 0.0
    motor_max_torque: float = 100.0

    def __post_init__(self):
        self.constraint_type = ConstraintType.HINGE

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "angle_range": f"{self.min_angle:.2f} to {self.max_angle:.2f}",
            "motor_enabled": self.motor_enabled,
        })
        return base


@dataclass
class SliderConstraint(Constraint):
    axis: Tuple[float, float] = (1.0, 0.0)
    min_translation: float = -100.0
    max_translation: float = 100.0
    motor_enabled: bool = False
    motor_speed: float = 0.0

    def __post_init__(self):
        self.constraint_type = ConstraintType.SLIDER

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "axis": list(self.axis),
            "translation_range": f"{self.min_translation} to {self.max_translation}",
        })
        return base


class PhysicsConstraints:
    """
    Physics constraint and joint management system.

    Provides a library of mechanical constraints that connect physics
    bodies with configurable limits. Supports spring (elastic), hinge
    (rotational pivot), slider (linear motion), distance (fixed
    separation), pin (fixed point), and weld (rigid connection)
    constraint types. Each constraint tracks applied forces and can
    break when exceeding configurable thresholds, enabling dynamic
    destruction of physical structures.
    """

    _instance: Optional["PhysicsConstraints"] = None

    def __init__(self):
        self._constraints: Dict[str, Constraint] = {}
        self._active_count: int = 0
        self._iteration_count: int = 10

    @classmethod
    def get_instance(cls) -> "PhysicsConstraints":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_spring(self, body_a_id: str = "", body_b_id: str = "", rest_length: float = 50.0, **kwargs) -> SpringConstraint:
        constraint = SpringConstraint(body_a_id=body_a_id, body_b_id=body_b_id, rest_length=rest_length, **kwargs)
        self._constraints[constraint.constraint_id] = constraint
        if constraint.state == ConstraintState.ACTIVE:
            self._active_count += 1
        return constraint

    def create_hinge(self, body_a_id: str = "", body_b_id: str = "", anchor: Tuple[float, float] = (0.0, 0.0), **kwargs) -> HingeConstraint:
        constraint = HingeConstraint(body_a_id=body_a_id, body_b_id=body_b_id, anchor_a=anchor, anchor_b=anchor, **kwargs)
        self._constraints[constraint.constraint_id] = constraint
        if constraint.state == ConstraintState.ACTIVE:
            self._active_count += 1
        return constraint

    def create_slider(self, body_a_id: str = "", body_b_id: str = "", axis: Tuple[float, float] = (1.0, 0.0), **kwargs) -> SliderConstraint:
        constraint = SliderConstraint(body_a_id=body_a_id, body_b_id=body_b_id, axis=axis, **kwargs)
        self._constraints[constraint.constraint_id] = constraint
        if constraint.state == ConstraintState.ACTIVE:
            self._active_count += 1
        return constraint

    def create_distance(self, body_a_id: str = "", body_b_id: str = "", distance: float = 100.0, **kwargs) -> Constraint:
        constraint = Constraint(
            constraint_type=ConstraintType.DISTANCE,
            body_a_id=body_a_id,
            body_b_id=body_b_id,
            **kwargs,
        )
        self._constraints[constraint.constraint_id] = constraint
        if constraint.state == ConstraintState.ACTIVE:
            self._active_count += 1
        return constraint

    def create_pin(self, body_a_id: str = "", anchor: Tuple[float, float] = (0.0, 0.0), **kwargs) -> Constraint:
        constraint = Constraint(
            constraint_type=ConstraintType.PIN,
            body_a_id=body_a_id,
            anchor_a=anchor,
            **kwargs,
        )
        self._constraints[constraint.constraint_id] = constraint
        if constraint.state == ConstraintState.ACTIVE:
            self._active_count += 1
        return constraint

    def create_weld(self, body_a_id: str = "", body_b_id: str = "", **kwargs) -> Constraint:
        constraint = Constraint(
            constraint_type=ConstraintType.WELD,
            body_a_id=body_a_id,
            body_b_id=body_b_id,
            stiffness=1.0,
            **kwargs,
        )
        self._constraints[constraint.constraint_id] = constraint
        if constraint.state == ConstraintState.ACTIVE:
            self._active_count += 1
        return constraint

    def get_constraint(self, constraint_id: str) -> Optional[Constraint]:
        return self._constraints.get(constraint_id)

    def remove_constraint(self, constraint_id: str) -> bool:
        constraint = self._constraints.pop(constraint_id, None)
        if constraint and constraint.state == ConstraintState.ACTIVE:
            self._active_count -= 1
        return constraint is not None

    def set_state(self, constraint_id: str, state: ConstraintState) -> bool:
        constraint = self._constraints.get(constraint_id)
        if not constraint:
            return False
        old_active = constraint.state == ConstraintState.ACTIVE
        constraint.state = state
        new_active = state == ConstraintState.ACTIVE
        if old_active and not new_active:
            self._active_count -= 1
        elif not old_active and new_active:
            self._active_count += 1
        return True

    def disable(self, constraint_id: str) -> bool:
        return self.set_state(constraint_id, ConstraintState.INACTIVE)

    def enable(self, constraint_id: str) -> bool:
        return self.set_state(constraint_id, ConstraintState.ACTIVE)

    def step(self, delta_time: float) -> None:
        for constraint in self._constraints.values():
            if constraint.state != ConstraintState.ACTIVE:
                continue
            if constraint.break_force > 0 and constraint.applied_force >= constraint.break_force:
                constraint.state = ConstraintState.BROKEN
                self._active_count -= 1

    def get_constraints_for_body(self, body_id: str) -> List[Constraint]:
        return [
            c for c in self._constraints.values()
            if c.body_a_id == body_id or c.body_b_id == body_id
        ]

    def list_constraints(self, constraint_type: Optional[ConstraintType] = None) -> List[Constraint]:
        if constraint_type:
            return [c for c in self._constraints.values() if c.constraint_type == constraint_type]
        return list(self._constraints.values())

    def get_stats(self) -> dict:
        type_counts = {}
        for c in self._constraints.values():
            type_name = c.constraint_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        return {
            "total_constraints": len(self._constraints),
            "active": self._active_count,
            "by_type": type_counts,
            "iterations": self._iteration_count,
        }

    def reset(self) -> None:
        self._constraints.clear()
        self._active_count = 0


def get_physics_constraints() -> PhysicsConstraints:
    return PhysicsConstraints.get_instance()
