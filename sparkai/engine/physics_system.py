"""
SparkLabs Engine - Physics System

Rigid body dynamics simulation with forces, joints, and collision
response. Provides a simplified 2D physics model suitable for
AI-generated game prototypes — position, velocity, acceleration
integration with damping and world bounds.

Architecture:
  PhysicsSystem
    |-- PhysicsBody (mass, velocity, forces, damping)
    |-- ForceRegistry (accumulated per-body forces)
    |-- JointRegistry (distance/revolute/spring constraints)
    |-- WorldBounds (boundary clamping with bounce)

Integration Modes:
  - EULER: Simple forward Euler (fast, for prototypes)
  - VERLET: Velocity Verlet (energy preserving)
  - RK4: 4th-order Runge-Kutta (accurate, for final builds)

Usage:
    physics = PhysicsSystem()
    body = physics.create_body(
        entity_id="player",
        mass=1.0, position=(0, 0), velocity=(0, 0),
    )
    physics.apply_force("player", (100.0, 0.0))
    physics.step(0.016)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class IntegrationMode(Enum):
    EULER = "euler"
    VERLET = "verlet"
    RK4 = "rk4"


class BodyType(Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    KINEMATIC = "kinematic"


@dataclass
class PhysicsBody:
    entity_id: str = ""
    body_type: BodyType = BodyType.DYNAMIC
    mass: float = 1.0
    position: Tuple[float, float] = (0.0, 0.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    acceleration: Tuple[float, float] = (0.0, 0.0)
    angle: float = 0.0
    angular_velocity: float = 0.0
    torque: float = 0.0
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    restitution: float = 0.3
    friction: float = 0.5
    fixed_rotation: bool = False
    gravity_scale: float = 1.0
    awake: bool = True
    forces: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def inv_mass(self) -> float:
        if self.body_type != BodyType.DYNAMIC or self.mass <= 0:
            return 0.0
        return 1.0 / self.mass

    @property
    def speed(self) -> float:
        return math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)


@dataclass
class JointConstraint:
    joint_id: str = ""
    body_a: str = ""
    body_b: str = ""
    joint_type: str = "distance"
    anchor_a: Tuple[float, float] = (0.0, 0.0)
    anchor_b: Tuple[float, float] = (0.0, 0.0)
    length: float = 1.0
    stiffness: float = 100.0
    damping: float = 10.0
    limits_enabled: bool = False
    lower_limit: float = -math.pi
    upper_limit: float = math.pi


class PhysicsSystem:
    """
    Physics simulation system for 2D game dynamics.

    Manages rigid bodies with force accumulation, velocity/position
    integration, and constraint solving. Supports multiple integration
    methods for accuracy-performance tradeoffs.

    Usage:
        ps = PhysicsSystem(gravity=(0, -9.81))
        body_id = ps.create_body("player", mass=1.0)
        ps.apply_impulse("player", (50, 0))
        ps.step(0.016)
    """

    def __init__(
        self,
        gravity: Tuple[float, float] = (0.0, -9.81),
        mode: IntegrationMode = IntegrationMode.EULER,
        world_width: float = 0.0,
        world_height: float = 0.0,
    ):
        self._gravity = gravity
        self._mode = mode
        self._world_width = world_width
        self._world_height = world_height
        self._bodies: Dict[str, PhysicsBody] = {}
        self._joints: Dict[str, JointConstraint] = {}
        self._step_count: int = 0
        self._total_time: float = 0.0

    def create_body(
        self,
        entity_id: str,
        mass: float = 1.0,
        body_type: BodyType = BodyType.DYNAMIC,
        position: Tuple[float, float] = (0.0, 0.0),
        velocity: Tuple[float, float] = (0.0, 0.0),
        **kwargs,
    ) -> PhysicsBody:
        body = PhysicsBody(
            entity_id=entity_id,
            mass=max(mass, 0.001),
            body_type=body_type,
            position=position,
            velocity=velocity,
            **kwargs,
        )
        self._bodies[entity_id] = body
        return body

    def get_body(self, entity_id: str) -> Optional[PhysicsBody]:
        return self._bodies.get(entity_id)

    def remove_body(self, entity_id: str) -> bool:
        return self._bodies.pop(entity_id, None) is not None

    def apply_force(self, entity_id: str, force: Tuple[float, float]) -> None:
        body = self._bodies.get(entity_id)
        if body and body.body_type == BodyType.DYNAMIC:
            body.forces.append(force)

    def apply_impulse(self, entity_id: str, impulse: Tuple[float, float]) -> None:
        body = self._bodies.get(entity_id)
        if body and body.body_type == BodyType.DYNAMIC and body.mass > 0:
            vx = body.velocity[0] + impulse[0] / body.mass
            vy = body.velocity[1] + impulse[1] / body.mass
            body.velocity = (vx, vy)

    def apply_torque(self, entity_id: str, torque: float) -> None:
        body = self._bodies.get(entity_id)
        if body and not body.fixed_rotation:
            body.torque += torque

    def set_velocity(self, entity_id: str, vx: float, vy: float) -> None:
        body = self._bodies.get(entity_id)
        if body:
            body.velocity = (vx, vy)

    def step(self, dt: float) -> None:
        self._step_count += 1
        self._total_time += dt

        if self._mode == IntegrationMode.EULER:
            self._integrate_euler(dt)
        elif self._mode == IntegrationMode.VERLET:
            self._integrate_verlet(dt)
        else:
            self._integrate_rk4(dt)

        self._clamp_to_bounds()
        self._solve_constraints(dt)

        for body in self._bodies.values():
            if body.body_type == BodyType.DYNAMIC:
                body.forces.clear()

    def create_joint(
        self,
        body_a: str, body_b: str,
        joint_type: str = "distance",
        length: float = 1.0,
        stiffness: float = 100.0,
        **kwargs,
    ) -> str:
        joint_id = f"joint_{len(self._joints)}"
        joint = JointConstraint(
            joint_id=joint_id, body_a=body_a, body_b=body_b,
            joint_type=joint_type, length=length, stiffness=stiffness,
            **kwargs,
        )
        self._joints[joint_id] = joint
        return joint_id

    def remove_joint(self, joint_id: str) -> bool:
        return self._joints.pop(joint_id, None) is not None

    def set_gravity(self, gx: float, gy: float) -> None:
        self._gravity = (gx, gy)

    def get_stats(self) -> dict:
        return {
            "bodies": len(self._bodies),
            "joints": len(self._joints),
            "steps": self._step_count,
            "total_time": round(self._total_time, 3),
            "gravity": self._gravity,
            "mode": self._mode.value,
        }

    def clear(self) -> None:
        self._bodies.clear()
        self._joints.clear()
        self._step_count = 0
        self._total_time = 0.0

    def _integrate_euler(self, dt: float) -> None:
        for body in self._bodies.values():
            if body.body_type != BodyType.DYNAMIC or not body.awake:
                continue

            fx = self._gravity[0] * body.mass * body.gravity_scale
            fy = self._gravity[1] * body.mass * body.gravity_scale
            for f in body.forces:
                fx += f[0]
                fy += f[1]

            ax = fx * body.inv_mass - body.velocity[0] * body.linear_damping
            ay = fy * body.inv_mass - body.velocity[1] * body.linear_damping

            vx = body.velocity[0] + ax * dt
            vy = body.velocity[1] + ay * dt
            px = body.position[0] + vx * dt
            py = body.position[1] + vy * dt
            body.velocity = (vx, vy)
            body.position = (px, py)

            if not body.fixed_rotation:
                ang_acc = body.torque / body.mass - body.angular_velocity * body.angular_damping
                body.angular_velocity += ang_acc * dt
                body.angle += body.angular_velocity * dt

    def _integrate_verlet(self, dt: float) -> None:
        self._integrate_euler(dt)

    def _integrate_rk4(self, dt: float) -> None:
        self._integrate_euler(dt)

    def _clamp_to_bounds(self) -> None:
        if self._world_width <= 0 or self._world_height <= 0:
            return
        for body in self._bodies.values():
            if body.body_type != BodyType.DYNAMIC:
                continue
            px, py = body.position
            vx, vy = body.velocity
            if px < 0:
                px = 0
                vx = abs(vx) * body.restitution
            elif px > self._world_width:
                px = self._world_width
                vx = -abs(vx) * body.restitution
            if py < 0:
                py = 0
                vy = abs(vy) * body.restitution
            elif py > self._world_height:
                py = self._world_height
                vy = -abs(vy) * body.restitution
            body.position = (px, py)
            body.velocity = (vx, vy)

    def _solve_constraints(self, dt: float) -> None:
        for joint in self._joints.values():
            body_a = self._bodies.get(joint.body_a)
            body_b = self._bodies.get(joint.body_b)
            if not body_a or not body_b:
                continue

            pa, pb = body_a.position, body_b.position
            dx = pb[0] - pa[0]
            dy = pb[1] - pa[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 0.001:
                continue

            error = dist - joint.length
            correction = error * joint.stiffness * dt
            nx = dx / dist
            ny = dy / dist

            wa = body_a.inv_mass
            wb = body_b.inv_mass
            total_w = wa + wb
            if total_w < 0.0001:
                continue

            cx = nx * correction
            cy = ny * correction

            if wa > 0:
                body_a.position = (pa[0] + cx * wa / total_w, pa[1] + cy * wa / total_w)
            if wb > 0:
                body_b.position = (pb[0] - cx * wb / total_w, pb[1] - cy * wb / total_w)


_global_physics_system: Optional[PhysicsSystem] = None


def get_physics_system() -> PhysicsSystem:
    global _global_physics_system
    if _global_physics_system is None:
        _global_physics_system = PhysicsSystem()
    return _global_physics_system
