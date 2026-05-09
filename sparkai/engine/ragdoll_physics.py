"""
SparkLabs Engine - Ragdoll Physics

Physics-based ragdoll simulation for character death, impact
reactions, and dynamic body behaviors. Models character skeletons
as interconnected rigid bodies with configurable joint limits,
damping, and collision response for realistic character motion.

Architecture:
  RagdollSystem
    |-- BoneBody (individual rigid body for a skeleton bone)
    |-- RagdollPose (bone positions defining a ragdoll state)
    |-- JointChain (connected bone bodies forming limbs)
    |-- ImpactSimulator (apply forces and impulses to ragdoll)
    |-- TransitionBlender (smooth animation-to-ragdoll blending)

Ragdoll States:
  - IDLE: inactive, no simulation
  - ACTIVE: fully simulated physics
  - BLENDING: transitioning between animation and physics
  - SETTLING: ragdoll settling after impact
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class RagdollState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    BLENDING = "blending"
    SETTLING = "settling"


class CollisionShape(Enum):
    BOX = "box"
    SPHERE = "sphere"
    CAPSULE = "capsule"
    CYLINDER = "cylinder"


@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vec3":
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> "Vec3":
        length = self.length()
        if length == 0.0:
            return Vec3()
        return Vec3(self.x / length, self.y / length, self.z / length)

    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class BoneBody:
    body_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    bone_name: str = ""
    parent_bone: str = ""
    shape: CollisionShape = CollisionShape.CAPSULE
    position: Vec3 = field(default_factory=Vec3)
    rotation: float = 0.0
    velocity: Vec3 = field(default_factory=Vec3)
    angular_velocity: float = 0.0
    mass: float = 1.0
    radius: float = 0.3
    length: float = 1.0
    damping: float = 0.95
    frozen: bool = False

    def apply_force(self, force: Vec3) -> None:
        if self.frozen or self.mass <= 0:
            return
        acceleration = force * (1.0 / self.mass)
        self.velocity = self.velocity + acceleration

    def step(self, dt: float, gravity: Vec3) -> None:
        if self.frozen:
            return
        grav_accel = gravity * dt
        self.velocity = self.velocity + grav_accel
        self.velocity = self.velocity * (1.0 - (1.0 - self.damping) * dt * 10.0)
        self.position = self.position + self.velocity * dt
        self.rotation += self.angular_velocity * dt
        self.angular_velocity *= max(0.0, 1.0 - (1.0 - self.damping) * dt * 5.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "bone_name": self.bone_name,
            "position": self.position.to_tuple(),
            "velocity": self.velocity.to_tuple(),
            "mass": self.mass,
            "frozen": self.frozen,
        }


@dataclass
class RagdollSkeleton:
    skeleton_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    bone_bodies: Dict[str, BoneBody] = field(default_factory=dict)
    state: RagdollState = RagdollState.IDLE
    gravity: Vec3 = field(default_factory=lambda: Vec3(0.0, -9.81, 0.0))
    total_mass: float = 0.0

    def add_bone(
        self,
        bone_name: str,
        parent_bone: str = "",
        mass: float = 1.0,
        length: float = 1.0,
        radius: float = 0.3,
    ) -> BoneBody:
        body = BoneBody(
            bone_name=bone_name,
            parent_bone=parent_bone,
            mass=mass,
            length=length,
            radius=radius,
        )
        self.bone_bodies[body.body_id] = body
        self.total_mass += mass
        return body

    def activate(self) -> None:
        for body in self.bone_bodies.values():
            body.frozen = False
            impact_force = Vec3(
                (random.random() - 0.5) * 20.0,
                random.random() * 15.0,
                (random.random() - 0.5) * 20.0,
            )
            body.apply_force(impact_force)
        self.state = RagdollState.ACTIVE

    def deactivate(self) -> None:
        for body in self.bone_bodies.values():
            body.frozen = True
            body.velocity = Vec3()
            body.angular_velocity = 0.0
        self.state = RagdollState.IDLE

    def apply_impact(
        self,
        force: Vec3,
        impact_bone: Optional[str] = None,
    ) -> None:
        self.state = RagdollState.ACTIVE
        if impact_bone:
            target = next(
                (b for b in self.bone_bodies.values() if b.bone_name == impact_bone),
                None,
            )
            if target:
                target.apply_force(force)
                return
        distribution = force * (1.0 / max(1, len(self.bone_bodies)))
        for body in self.bone_bodies.values():
            body.apply_force(distribution * (0.5 + random.random()))

    def step(self, dt: float) -> None:
        if self.state not in (RagdollState.ACTIVE, RagdollState.SETTLING):
            return
        for body in self.bone_bodies.values():
            body.step(dt, self.gravity)

        total_kinetic = sum(
            b.velocity.length() * b.mass for b in self.bone_bodies.values()
        )
        if (
            self.state == RagdollState.ACTIVE
            and total_kinetic < 0.5
        ):
            settle_time = sum(
                b.velocity.length() for b in self.bone_bodies.values()
            )
            if settle_time < 0.1:
                self.state = RagdollState.SETTLING

    def enforce_joints(
        self,
        stiffness: float = 0.8,
        rest_distance_margin: float = 0.05,
    ) -> None:
        bodies = list(self.bone_bodies.values())
        for i, body_a in enumerate(bodies):
            if body_a.parent_bone:
                parent = next(
                    (b for b in bodies if b.bone_name == body_a.parent_bone), None
                )
                if parent:
                    direction = body_a.position - parent.position
                    distance = direction.length()
                    rest_length = body_a.length * 0.5 + parent.length * 0.5
                    if abs(distance - rest_length) > rest_distance_margin:
                        correction = direction.normalized() * (rest_length - distance) * stiffness * 0.5
                        parent.position = parent.position - correction
                        body_a.position = body_a.position + correction

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skeleton_id": self.skeleton_id,
            "name": self.name,
            "bone_count": len(self.bone_bodies),
            "state": self.state.value,
            "total_mass": round(self.total_mass, 2),
            "bodies": [b.to_dict() for b in self.bone_bodies.values()],
        }


class RagdollSystem:
    """Physics-based ragdoll simulation for character animation."""

    _instance: Optional["RagdollSystem"] = None
    _lock = threading.Lock()

    MAX_SKELETONS = 100

    def __init__(self):
        self._skeletons: Dict[str, RagdollSkeleton] = {}
        self._joint_stiffness: float = 0.8
        self._default_gravity = Vec3(0.0, -9.81, 0.0)

    @classmethod
    def get_instance(cls) -> "RagdollSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_skeleton(
        self,
        name: str = "",
        gravity: Optional[Vec3] = None,
    ) -> RagdollSkeleton:
        skeleton = RagdollSkeleton(
            name=name,
            gravity=gravity or self._default_gravity,
        )
        self._skeletons[skeleton.skeleton_id] = skeleton
        return skeleton

    def build_humanoid(
        self,
        name: str = "humanoid",
    ) -> RagdollSkeleton:
        skeleton = self.create_skeleton(name=name)

        skeleton.add_bone("head", "neck", mass=3.0, length=0.25, radius=0.15)
        skeleton.add_bone("neck", "torso", mass=1.0, length=0.12, radius=0.08)
        skeleton.add_bone("torso", "", mass=12.0, length=0.6, radius=0.25)

        skeleton.add_bone("upper_arm_l", "torso", mass=2.5, length=0.35, radius=0.1)
        skeleton.add_bone("forearm_l", "upper_arm_l", mass=1.5, length=0.3, radius=0.08)
        skeleton.add_bone("hand_l", "forearm_l", mass=0.5, length=0.15, radius=0.06)

        skeleton.add_bone("upper_arm_r", "torso", mass=2.5, length=0.35, radius=0.1)
        skeleton.add_bone("forearm_r", "upper_arm_r", mass=1.5, length=0.3, radius=0.08)
        skeleton.add_bone("hand_r", "forearm_r", mass=0.5, length=0.15, radius=0.06)

        skeleton.add_bone("upper_leg_l", "torso", mass=5.0, length=0.45, radius=0.15)
        skeleton.add_bone("lower_leg_l", "upper_leg_l", mass=3.0, length=0.4, radius=0.12)
        skeleton.add_bone("foot_l", "lower_leg_l", mass=1.0, length=0.18, radius=0.08)

        skeleton.add_bone("upper_leg_r", "torso", mass=5.0, length=0.45, radius=0.15)
        skeleton.add_bone("lower_leg_r", "upper_leg_r", mass=3.0, length=0.4, radius=0.12)
        skeleton.add_bone("foot_r", "lower_leg_r", mass=1.0, length=0.18, radius=0.08)

        return skeleton

    def get_skeleton(self, skeleton_id: str) -> Optional[RagdollSkeleton]:
        return self._skeletons.get(skeleton_id)

    def activate_skeleton(self, skeleton_id: str) -> bool:
        skeleton = self._skeletons.get(skeleton_id)
        if skeleton:
            skeleton.activate()
            return True
        return False

    def deactivate_skeleton(self, skeleton_id: str) -> bool:
        skeleton = self._skeletons.get(skeleton_id)
        if skeleton:
            skeleton.deactivate()
            return True
        return False

    def apply_impact(
        self,
        skeleton_id: str,
        force: Tuple[float, float, float],
        bone_name: Optional[str] = None,
    ) -> bool:
        skeleton = self._skeletons.get(skeleton_id)
        if not skeleton:
            return False
        skeleton.apply_impact(
            Vec3(*force), impact_bone=bone_name
        )
        return True

    def step(self, dt: float) -> None:
        for skeleton in self._skeletons.values():
            skeleton.step(dt)
            if skeleton.state in (RagdollState.ACTIVE, RagdollState.BLENDING):
                skeleton.enforce_joints(self._joint_stiffness)

    def list_skeletons(self) -> List[RagdollSkeleton]:
        return list(self._skeletons.values())

    def delete_skeleton(self, skeleton_id: str) -> bool:
        if skeleton_id in self._skeletons:
            del self._skeletons[skeleton_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        active = sum(
            1 for s in self._skeletons.values() if s.state == RagdollState.ACTIVE
        )
        total_bones = sum(
            len(s.bone_bodies) for s in self._skeletons.values()
        )
        return {
            "skeletons": len(self._skeletons),
            "active_ragdolls": active,
            "total_bones": total_bones,
            "joint_stiffness": self._joint_stiffness,
            "default_gravity": self._default_gravity.to_tuple(),
        }


def get_ragdoll_system() -> RagdollSystem:
    return RagdollSystem.get_instance()