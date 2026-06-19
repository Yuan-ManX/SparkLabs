"""
SparkLabs Engine Physics

A complete physics simulation engine for the AI-native game engine.
Provides rigid body dynamics, collision detection, constraint solving,
force application, spatial partitioning, and raycasting.

Architecture:
  PhysicsEngine (Singleton)
    |-- PhysicsBody         — rigid body with position, rotation, velocity, mass
    |-- PhysicsConstraint   — joint/constraint between two bodies
    |-- CollisionEvent      — recorded collision data per event

Collision Pipeline:
  1. Broad Phase  — grid-based spatial hash culling
  2. Narrow Phase — shape-specific intersection tests (AABB, circle, polygon)
  3. Resolution   — impulse-based contact resolution
  4. Constraints  — solved after collision response
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BodyType(Enum):
    """Classification of a physics body controlling its simulation behavior."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    KINEMATIC = "kinematic"


class CollisionShape(Enum):
    """Geometric shape used for collision detection on a physics body."""
    CIRCLE = "circle"
    AABB = "aabb"
    POLYGON = "polygon"
    CAPSULE = "capsule"


class ConstraintType(Enum):
    """Type of joint or constraint connecting two physics bodies."""
    SPRING = "spring"
    DISTANCE = "distance"
    HINGE = "hinge"
    SLIDER = "slider"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Vector2D:
    """2D vector for physics calculations."""

    x: float = 0.0
    y: float = 0.0

    def add(self, other: Vector2D) -> Vector2D:
        return Vector2D(self.x + other.x, self.y + other.y)

    def subtract(self, other: Vector2D) -> Vector2D:
        return Vector2D(self.x - other.x, self.y - other.y)

    def multiply(self, scalar: float) -> Vector2D:
        return Vector2D(self.x * scalar, self.y * scalar)

    def dot(self, other: Vector2D) -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vector2D) -> float:
        return self.x * other.y - self.y * other.x

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalize(self) -> Vector2D:
        length_val = self.length()
        if length_val > 0.0001:
            inv = 1.0 / length_val
            return Vector2D(self.x * inv, self.y * inv)
        return Vector2D()

    def perpendicular(self) -> Vector2D:
        return Vector2D(-self.y, self.x)

    def rotate(self, angle: float) -> Vector2D:
        c = math.cos(angle)
        s = math.sin(angle)
        return Vector2D(self.x * c - self.y * s, self.x * s + self.y * c)

    def distance_to(self, other: Vector2D) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_tuple(cls, t: Tuple[float, float]) -> Vector2D:
        return cls(t[0], t[1])


@dataclass
class PhysicsBody:
    """Rigid body with position, velocity, rotation, and collision shape."""

    body_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    body_type: BodyType = BodyType.DYNAMIC
    position: Vector2D = field(default_factory=Vector2D)
    velocity: Vector2D = field(default_factory=Vector2D)
    acceleration: Vector2D = field(default_factory=Vector2D)
    mass: float = 1.0
    rotation: float = 0.0
    angular_velocity: float = 0.0
    shape: CollisionShape = CollisionShape.AABB
    shape_data: Dict[str, Any] = field(default_factory=dict)
    restitution: float = 0.3
    friction: float = 0.5
    is_sleeping: bool = False
    layer: int = 0
    mask: int = 0xFFFFFFFF
    user_data: Optional[Dict[str, Any]] = None

    # Internal tracking
    _force_accumulator: Vector2D = field(default_factory=Vector2D, repr=False)
    _torque_accumulator: float = field(default=0.0, repr=False)
    _inverse_mass: float = field(default=1.0, repr=False)
    _inverse_inertia: float = field(default=1.0, repr=False)

    def __post_init__(self) -> None:
        self._update_mass_properties()

    def _update_mass_properties(self) -> None:
        if self.body_type == BodyType.DYNAMIC and self.mass > 0.0:
            self._inverse_mass = 1.0 / self.mass
        else:
            self._inverse_mass = 0.0
            self._torque_accumulator = 0.0

    def get_inverse_mass(self) -> float:
        if self.body_type != BodyType.DYNAMIC or self.mass <= 0.0:
            return 0.0
        return self._inverse_mass

    def get_aabb(self) -> Tuple[float, float, float, float]:
        """Return (min_x, min_y, max_x, max_y) for broad-phase."""
        if self.shape == CollisionShape.CIRCLE:
            r = float(self.shape_data.get("radius", 1.0))
            return (self.position.x - r, self.position.y - r,
                    self.position.x + r, self.position.y + r)
        elif self.shape == CollisionShape.AABB:
            hw = float(self.shape_data.get("half_width", 0.5))
            hh = float(self.shape_data.get("half_height", 0.5))
            return (self.position.x - hw, self.position.y - hh,
                    self.position.x + hw, self.position.y + hh)
        elif self.shape == CollisionShape.POLYGON:
            vertices = self.shape_data.get("vertices", [])
            if not vertices:
                return (self.position.x, self.position.y, self.position.x, self.position.y)
            min_x = float("inf")
            min_y = float("inf")
            max_x = float("-inf")
            max_y = float("-inf")
            for v in vertices:
                vx = v[0] if isinstance(v, (list, tuple)) else v.x
                vy = v[1] if isinstance(v, (list, tuple)) else v.y
                c = math.cos(self.rotation)
                s = math.sin(self.rotation)
                rx = vx * c - vy * s + self.position.x
                ry = vx * s + vy * c + self.position.y
                min_x = min(min_x, rx)
                min_y = min(min_y, ry)
                max_x = max(max_x, rx)
                max_y = max(max_y, ry)
            return (min_x, min_y, max_x, max_y)
        return (self.position.x - 0.5, self.position.y - 0.5,
                self.position.x + 0.5, self.position.y + 0.5)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "body_type": self.body_type.value,
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict(),
            "acceleration": self.acceleration.to_dict(),
            "mass": self.mass,
            "rotation": self.rotation,
            "angular_velocity": self.angular_velocity,
            "shape": self.shape.value,
            "shape_data": self.shape_data,
            "restitution": self.restitution,
            "friction": self.friction,
            "is_sleeping": self.is_sleeping,
            "layer": self.layer,
            "mask": self.mask,
            "user_data": self.user_data,
        }


@dataclass
class CollisionEvent:
    """Recorded collision data between two bodies."""

    body_a_id: str
    body_b_id: str
    contact_point: Vector2D
    normal: Vector2D
    penetration_depth: float
    relative_velocity: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "contact_point": self.contact_point.to_dict(),
            "normal": self.normal.to_dict(),
            "penetration_depth": self.penetration_depth,
            "relative_velocity": self.relative_velocity,
        }


@dataclass
class PhysicsConstraint:
    """Joint or constraint connecting two physics bodies."""

    constraint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    constraint_type: ConstraintType = ConstraintType.DISTANCE
    body_a_id: str = ""
    body_b_id: str = ""
    anchor_a: Vector2D = field(default_factory=Vector2D)
    anchor_b: Vector2D = field(default_factory=Vector2D)
    stiffness: float = 100.0
    damping: float = 10.0
    rest_length: float = 0.0
    min_limit: Optional[float] = None
    max_limit: Optional[float] = None
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type.value,
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "anchor_a": self.anchor_a.to_dict(),
            "anchor_b": self.anchor_b.to_dict(),
            "stiffness": self.stiffness,
            "damping": self.damping,
            "rest_length": self.rest_length,
            "min_limit": self.min_limit,
            "max_limit": self.max_limit,
            "is_active": self.is_active,
        }


# ---------------------------------------------------------------------------
# Physics Engine
# ---------------------------------------------------------------------------

class PhysicsEngine:
    """
    2D physics simulation engine with rigid body dynamics, collision
    detection, constraint solving, and force application.

    Uses semi-implicit Euler integration and a grid-based spatial hash
    for broad-phase collision detection. Supports AABB, circle, and
    polygon collision shapes.
    """

    _instance: Optional["PhysicsEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "PhysicsEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "PhysicsEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._bodies: Dict[str, PhysicsBody] = {}
        self._constraints: Dict[str, PhysicsConstraint] = {}
        self._collision_callbacks: Dict[str, Callable[[CollisionEvent], None]] = {}
        self._gravity: Vector2D = Vector2D(0.0, -9.81)
        self._spatial_grid: Dict[Tuple[int, int], List[str]] = {}
        self._cell_size: float = 4.0
        self._damping: float = 0.995
        self._angular_damping: float = 0.98
        self._max_velocity: float = 100.0
        self._sleep_threshold: float = 0.01
        self._step_count: int = 0
        self._total_collision_checks: int = 0
        self._total_collisions: int = 0

    # ------------------------------------------------------------------
    # Body Management
    # ------------------------------------------------------------------

    def create_body(
        self,
        body_type: BodyType,
        position: Tuple[float, float],
        shape: CollisionShape,
        shape_data: Dict[str, Any],
        mass: float = 1.0,
        rotation: float = 0.0,
        restitution: float = 0.3,
        friction: float = 0.5,
        layer: int = 0,
        mask: int = 0xFFFFFFFF,
    ) -> PhysicsBody:
        """Create a new physics body and add it to the simulation."""
        with self._lock:
            body = PhysicsBody(
                body_type=body_type,
                position=Vector2D(position[0], position[1]),
                mass=mass,
                rotation=rotation,
                shape=shape,
                shape_data=shape_data,
                restitution=restitution,
                friction=friction,
                layer=layer,
                mask=mask,
            )
            self._bodies[body.body_id] = body
            return body

    def remove_body(self, body_id: str) -> bool:
        """Remove a physics body from the simulation."""
        with self._lock:
            if body_id in self._bodies:
                del self._bodies[body_id]
                # Remove constraints referencing this body
                to_remove = [
                    cid for cid, c in self._constraints.items()
                    if c.body_a_id == body_id or c.body_b_id == body_id
                ]
                for cid in to_remove:
                    del self._constraints[cid]
                return True
            return False

    def get_body(self, body_id: str) -> Optional[PhysicsBody]:
        """Get a body by ID."""
        return self._bodies.get(body_id)

    # ------------------------------------------------------------------
    # Force Application
    # ------------------------------------------------------------------

    def apply_force(self, body_id: str, force_x: float, force_y: float) -> bool:
        """Apply a continuous force to a body (accumulated over the step)."""
        body = self._bodies.get(body_id)
        if body is None or body.body_type != BodyType.DYNAMIC:
            return False
        body._force_accumulator = body._force_accumulator.add(
            Vector2D(force_x, force_y)
        )
        return True

    def apply_impulse(self, body_id: str, impulse_x: float, impulse_y: float) -> bool:
        """Apply an instantaneous impulse to a body."""
        body = self._bodies.get(body_id)
        if body is None or body.body_type != BodyType.DYNAMIC:
            return False
        inv_mass = body.get_inverse_mass()
        if inv_mass <= 0.0:
            return False
        body.velocity = body.velocity.add(
            Vector2D(impulse_x * inv_mass, impulse_y * inv_mass)
        )
        body.is_sleeping = False
        return True

    def apply_torque(self, body_id: str, torque: float) -> bool:
        """Apply a torque to a body (accumulated over the step)."""
        body = self._bodies.get(body_id)
        if body is None or body.body_type != BodyType.DYNAMIC:
            return False
        body._torque_accumulator += torque
        return True

    def set_velocity(self, body_id: str, vx: float, vy: float) -> bool:
        """Set the linear velocity of a body."""
        body = self._bodies.get(body_id)
        if body is None:
            return False
        body.velocity = Vector2D(vx, vy)
        if abs(vx) > 0.001 or abs(vy) > 0.001:
            body.is_sleeping = False
        return True

    def set_position(self, body_id: str, x: float, y: float) -> bool:
        """Set the position of a body."""
        body = self._bodies.get(body_id)
        if body is None:
            return False
        body.position = Vector2D(x, y)
        return True

    # ------------------------------------------------------------------
    # Constraint Management
    # ------------------------------------------------------------------

    def create_constraint(
        self,
        constraint_type: ConstraintType,
        body_a_id: str,
        body_b_id: str,
        anchor_a: Tuple[float, float],
        anchor_b: Tuple[float, float],
        stiffness: float = 100.0,
        damping: float = 10.0,
        rest_length: float = 0.0,
    ) -> PhysicsConstraint:
        """Create a constraint between two bodies."""
        with self._lock:
            constraint = PhysicsConstraint(
                constraint_type=constraint_type,
                body_a_id=body_a_id,
                body_b_id=body_b_id,
                anchor_a=Vector2D(anchor_a[0], anchor_a[1]),
                anchor_b=Vector2D(anchor_b[0], anchor_b[1]),
                stiffness=stiffness,
                damping=damping,
                rest_length=rest_length,
            )
            self._constraints[constraint.constraint_id] = constraint
            return constraint

    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove a constraint from the simulation."""
        with self._lock:
            if constraint_id in self._constraints:
                del self._constraints[constraint_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Spatial Grid (Broad Phase)
    # ------------------------------------------------------------------

    def _rebuild_spatial_grid(self) -> None:
        """Rebuild the spatial hash grid for broad-phase collision detection."""
        self._spatial_grid.clear()
        for body in self._bodies.values():
            if body.is_sleeping:
                continue
            min_x, min_y, max_x, max_y = body.get_aabb()
            min_cx = int(math.floor(min_x / self._cell_size))
            min_cy = int(math.floor(min_y / self._cell_size))
            max_cx = int(math.floor(max_x / self._cell_size))
            max_cy = int(math.floor(max_y / self._cell_size))
            for cx in range(min_cx, max_cx + 1):
                for cy in range(min_cy, max_cy + 1):
                    key = (cx, cy)
                    if key not in self._spatial_grid:
                        self._spatial_grid[key] = []
                    self._spatial_grid[key].append(body.body_id)

    def _get_potential_pairs(self) -> List[Tuple[str, str]]:
        """Get potential collision pairs from the spatial grid."""
        pairs: Dict[Tuple[str, str], bool] = {}
        for cell_ids in self._spatial_grid.values():
            if len(cell_ids) < 2:
                continue
            for i in range(len(cell_ids)):
                for j in range(i + 1, len(cell_ids)):
                    a_id = cell_ids[i]
                    b_id = cell_ids[j]
                    if a_id == b_id:
                        continue
                    key = (a_id, b_id) if a_id < b_id else (b_id, a_id)
                    pairs[key] = True
        return list(pairs.keys())

    # ------------------------------------------------------------------
    # Collision Detection (Narrow Phase)
    # ------------------------------------------------------------------

    def _check_aabb_overlap(
        self, a_min: float, a_max: float, b_min: float, b_max: float
    ) -> bool:
        return a_max > b_min and a_min < b_max

    def _aabb_vs_aabb(
        self, body_a: PhysicsBody, body_b: PhysicsBody
    ) -> Optional[CollisionEvent]:
        """Narrow-phase AABB vs AABB collision test."""
        a_min_x, a_min_y, a_max_x, a_max_y = body_a.get_aabb()
        b_min_x, b_min_y, b_max_x, b_max_y = body_b.get_aabb()

        if not self._check_aabb_overlap(a_min_x, a_max_x, b_min_x, b_max_x):
            return None
        if not self._check_aabb_overlap(a_min_y, a_max_y, b_min_y, b_max_y):
            return None

        # Compute penetration on each axis
        overlap_x = min(a_max_x - b_min_x, b_max_x - a_min_x)
        overlap_y = min(a_max_y - b_min_y, b_max_y - a_min_y)

        if overlap_x < overlap_y:
            penetration = overlap_x
            if a_max_x > b_max_x:
                normal = Vector2D(1.0, 0.0)
            else:
                normal = Vector2D(-1.0, 0.0)
        else:
            penetration = overlap_y
            if a_max_y > b_max_y:
                normal = Vector2D(0.0, 1.0)
            else:
                normal = Vector2D(0.0, -1.0)

        contact_x = (max(a_min_x, b_min_x) + min(a_max_x, b_max_x)) * 0.5
        contact_y = (max(a_min_y, b_min_y) + min(a_max_y, b_max_y)) * 0.5

        rel_vel = body_b.velocity.subtract(body_a.velocity)
        rel_vel_normal = rel_vel.dot(normal)

        return CollisionEvent(
            body_a_id=body_a.body_id,
            body_b_id=body_b.body_id,
            contact_point=Vector2D(contact_x, contact_y),
            normal=normal,
            penetration_depth=penetration,
            relative_velocity=rel_vel_normal,
        )

    def _circle_vs_circle(
        self, body_a: PhysicsBody, body_b: PhysicsBody
    ) -> Optional[CollisionEvent]:
        """Narrow-phase circle vs circle collision test."""
        r_a = float(body_a.shape_data.get("radius", 1.0))
        r_b = float(body_b.shape_data.get("radius", 1.0))
        sum_radii = r_a + r_b

        delta = body_b.position.subtract(body_a.position)
        dist_sq = delta.length_sq()

        if dist_sq >= sum_radii * sum_radii:
            return None

        dist = math.sqrt(dist_sq) if dist_sq > 0.0 else 0.0
        if dist < 0.0001:
            normal = Vector2D(1.0, 0.0)
        else:
            normal = delta.multiply(1.0 / dist)

        penetration = sum_radii - dist
        contact_point = body_a.position.add(
            normal.multiply(r_a - penetration * 0.5)
        )

        rel_vel = body_b.velocity.subtract(body_a.velocity)
        rel_vel_normal = rel_vel.dot(normal)

        return CollisionEvent(
            body_a_id=body_a.body_id,
            body_b_id=body_b.body_id,
            contact_point=contact_point,
            normal=normal,
            penetration_depth=penetration,
            relative_velocity=rel_vel_normal,
        )

    def _aabb_vs_circle(
        self, body_a: PhysicsBody, body_b: PhysicsBody
    ) -> Optional[CollisionEvent]:
        """
        Narrow-phase AABB vs circle collision test.
        body_a is AABB, body_b is circle.
        """
        a_min_x, a_min_y, a_max_x, a_max_y = body_a.get_aabb()
        r_b = float(body_b.shape_data.get("radius", 1.0))

        # Closest point on AABB to circle center
        closest_x = max(a_min_x, min(body_b.position.x, a_max_x))
        closest_y = max(a_min_y, min(body_b.position.y, a_max_y))

        dx = body_b.position.x - closest_x
        dy = body_b.position.y - closest_y
        dist_sq = dx * dx + dy * dy

        if dist_sq >= r_b * r_b:
            return None

        dist = math.sqrt(dist_sq) if dist_sq > 0.0 else 0.0
        if dist < 0.0001:
            # Circle center is inside the AABB, push out along shortest axis
            dist_left = body_b.position.x - a_min_x
            dist_right = a_max_x - body_b.position.x
            dist_bottom = body_b.position.y - a_min_y
            dist_top = a_max_y - body_b.position.y

            if dist_left < dist_right and dist_left < dist_bottom and dist_left < dist_top:
                normal = Vector2D(-1.0, 0.0)
            elif dist_right < dist_bottom and dist_right < dist_top:
                normal = Vector2D(1.0, 0.0)
            elif dist_bottom < dist_top:
                normal = Vector2D(0.0, -1.0)
            else:
                normal = Vector2D(0.0, 1.0)
        else:
            normal = Vector2D(dx / dist, dy / dist)

        penetration = r_b - dist
        contact_point = Vector2D(closest_x, closest_y)

        rel_vel = body_b.velocity.subtract(body_a.velocity)
        rel_vel_normal = rel_vel.dot(normal)

        return CollisionEvent(
            body_a_id=body_a.body_id,
            body_b_id=body_b.body_id,
            contact_point=contact_point,
            normal=normal,
            penetration_depth=penetration,
            relative_velocity=rel_vel_normal,
        )

    def _check_collision(
        self, body_a: PhysicsBody, body_b: PhysicsBody
    ) -> Optional[CollisionEvent]:
        """Dispatch to the correct narrow-phase collision test."""
        shapes = (body_a.shape, body_b.shape)

        if shapes == (CollisionShape.AABB, CollisionShape.AABB):
            return self._aabb_vs_aabb(body_a, body_b)
        elif shapes == (CollisionShape.CIRCLE, CollisionShape.CIRCLE):
            return self._circle_vs_circle(body_a, body_b)
        elif shapes == (CollisionShape.AABB, CollisionShape.CIRCLE):
            return self._aabb_vs_circle(body_a, body_b)
        elif shapes == (CollisionShape.CIRCLE, CollisionShape.AABB):
            event = self._aabb_vs_circle(body_b, body_a)
            if event is not None:
                event.normal = event.normal.multiply(-1.0)
                rel_vel = body_a.velocity.subtract(body_b.velocity)
                event.relative_velocity = rel_vel.dot(event.normal)
            return event

        return None

    # ------------------------------------------------------------------
    # Collision Response
    # ------------------------------------------------------------------

    def _resolve_collision(self, event: CollisionEvent) -> None:
        """Resolve a collision between two bodies using impulse-based response."""
        body_a = self._bodies.get(event.body_a_id)
        body_b = self._bodies.get(event.body_b_id)
        if body_a is None or body_b is None:
            return

        inv_mass_a = body_a.get_inverse_mass()
        inv_mass_b = body_b.get_inverse_mass()
        total_inv_mass = inv_mass_a + inv_mass_b

        if total_inv_mass <= 0.0:
            return

        # Positional correction
        slop = 0.01
        correction_factor = 0.8
        correction_magnitude = max(event.penetration_depth - slop, 0.0) * correction_factor / total_inv_mass
        correction = event.normal.multiply(correction_magnitude)

        if body_a.body_type == BodyType.DYNAMIC:
            body_a.position = body_a.position.subtract(correction.multiply(inv_mass_a))
        if body_b.body_type == BodyType.DYNAMIC:
            body_b.position = body_b.position.add(correction.multiply(inv_mass_b))

        # Velocity resolution
        if event.relative_velocity > 0.0:
            return

        restitution = (body_a.restitution + body_b.restitution) * 0.5
        jn = -(1.0 + restitution) * event.relative_velocity / total_inv_mass
        impulse = event.normal.multiply(jn)

        if body_a.body_type == BodyType.DYNAMIC:
            body_a.velocity = body_a.velocity.subtract(impulse.multiply(inv_mass_a))
        if body_b.body_type == BodyType.DYNAMIC:
            body_b.velocity = body_b.velocity.add(impulse.multiply(inv_mass_b))

        # Friction
        rel_vel = body_b.velocity.subtract(body_a.velocity)
        tangent = rel_vel.subtract(
            event.normal.multiply(rel_vel.dot(event.normal))
        )
        tangent_len = tangent.length()
        if tangent_len > 0.0001:
            tangent = tangent.multiply(1.0 / tangent_len)
            friction_coeff = (body_a.friction + body_b.friction) * 0.5
            jt = -rel_vel.dot(tangent) / total_inv_mass
            jt = max(-jn * friction_coeff, min(jt, jn * friction_coeff))
            friction_impulse = tangent.multiply(jt)

            if body_a.body_type == BodyType.DYNAMIC:
                body_a.velocity = body_a.velocity.subtract(
                    friction_impulse.multiply(inv_mass_a)
                )
            if body_b.body_type == BodyType.DYNAMIC:
                body_b.velocity = body_b.velocity.add(
                    friction_impulse.multiply(inv_mass_b)
                )

        # Wake bodies
        body_a.is_sleeping = False
        body_b.is_sleeping = False

    # ------------------------------------------------------------------
    # Constraint Solving
    # ------------------------------------------------------------------

    def _solve_constraint(self, constraint: PhysicsConstraint) -> None:
        """Solve a single constraint."""
        if not constraint.is_active:
            return

        body_a = self._bodies.get(constraint.body_a_id)
        body_b = self._bodies.get(constraint.body_b_id)
        if body_a is None or body_b is None:
            return

        if constraint.constraint_type == ConstraintType.DISTANCE:
            self._solve_distance_constraint(constraint, body_a, body_b)
        elif constraint.constraint_type == ConstraintType.SPRING:
            self._solve_spring_constraint(constraint, body_a, body_b)
        elif constraint.constraint_type == ConstraintType.HINGE:
            self._solve_hinge_constraint(constraint, body_a, body_b)

    def _solve_distance_constraint(
        self,
        constraint: PhysicsConstraint,
        body_a: PhysicsBody,
        body_b: PhysicsBody,
    ) -> None:
        """Solve a distance constraint between two bodies."""
        # World-space anchor positions
        anchor_a_world = body_a.position.add(
            constraint.anchor_a.rotate(body_a.rotation)
        )
        anchor_b_world = body_b.position.add(
            constraint.anchor_b.rotate(body_b.rotation)
        )

        delta = anchor_b_world.subtract(anchor_a_world)
        dist = delta.length()

        if dist < 0.0001:
            return

        inv_mass_a = body_a.get_inverse_mass()
        inv_mass_b = body_b.get_inverse_mass()
        total_inv_mass = inv_mass_a + inv_mass_b

        if total_inv_mass <= 0.0:
            return

        # Apply limit constraints
        target_length = constraint.rest_length
        if constraint.min_limit is not None and dist < constraint.min_limit:
            target_length = constraint.min_limit
        elif constraint.max_limit is not None and dist > constraint.max_limit:
            target_length = constraint.max_limit
        elif constraint.min_limit is not None or constraint.max_limit is not None:
            return

        normal = delta.multiply(1.0 / dist)
        correction = (dist - target_length) / total_inv_mass * constraint.stiffness * 0.01

        if body_a.body_type == BodyType.DYNAMIC:
            body_a.position = body_a.position.add(
                normal.multiply(correction * inv_mass_a)
            )
        if body_b.body_type == BodyType.DYNAMIC:
            body_b.position = body_b.position.subtract(
                normal.multiply(correction * inv_mass_b)
            )

    def _solve_spring_constraint(
        self,
        constraint: PhysicsConstraint,
        body_a: PhysicsBody,
        body_b: PhysicsBody,
    ) -> None:
        """Solve a spring constraint between two bodies."""
        anchor_a_world = body_a.position.add(
            constraint.anchor_a.rotate(body_a.rotation)
        )
        anchor_b_world = body_b.position.add(
            constraint.anchor_b.rotate(body_b.rotation)
        )

        delta = anchor_b_world.subtract(anchor_a_world)
        dist = delta.length()

        if dist < 0.0001:
            return

        normal = delta.multiply(1.0 / dist)
        displacement = dist - constraint.rest_length

        # Hooke's law: F = -k * x
        force_magnitude = -constraint.stiffness * displacement

        # Damping
        rel_vel = body_b.velocity.subtract(body_a.velocity)
        vel_along_normal = rel_vel.dot(normal)
        force_magnitude -= constraint.damping * vel_along_normal

        inv_mass_a = body_a.get_inverse_mass()
        inv_mass_b = body_b.get_inverse_mass()

        if body_a.body_type == BodyType.DYNAMIC and inv_mass_a > 0.0:
            body_a.velocity = body_a.velocity.subtract(
                normal.multiply(force_magnitude * inv_mass_a * 0.016)
            )
        if body_b.body_type == BodyType.DYNAMIC and inv_mass_b > 0.0:
            body_b.velocity = body_b.velocity.add(
                normal.multiply(force_magnitude * inv_mass_b * 0.016)
            )

    def _solve_hinge_constraint(
        self,
        constraint: PhysicsConstraint,
        body_a: PhysicsBody,
        body_b: PhysicsBody,
    ) -> None:
        """Solve a hinge constraint by aligning the anchor points."""
        anchor_a_world = body_a.position.add(
            constraint.anchor_a.rotate(body_a.rotation)
        )
        anchor_b_world = body_b.position.add(
            constraint.anchor_b.rotate(body_b.rotation)
        )

        delta = anchor_b_world.subtract(anchor_a_world)
        inv_mass_a = body_a.get_inverse_mass()
        inv_mass_b = body_b.get_inverse_mass()
        total_inv_mass = inv_mass_a + inv_mass_b

        if total_inv_mass <= 0.0:
            return

        if body_a.body_type == BodyType.DYNAMIC:
            body_a.position = body_a.position.add(
                delta.multiply(inv_mass_a / total_inv_mass)
            )
        if body_b.body_type == BodyType.DYNAMIC:
            body_b.position = body_b.position.subtract(
                delta.multiply(inv_mass_b / total_inv_mass)
            )

    # ------------------------------------------------------------------
    # Integration (Semi-Implicit Euler)
    # ------------------------------------------------------------------

    def _integrate(self, delta_time: float) -> None:
        """Integrate body positions and velocities using semi-implicit Euler."""
        for body in self._bodies.values():
            if body.body_type != BodyType.DYNAMIC:
                continue
            if body.is_sleeping:
                continue

            # Apply gravity
            body._force_accumulator = body._force_accumulator.add(
                self._gravity.multiply(body.mass)
            )

            # Semi-implicit Euler: v(t+dt) = v(t) + a(t)*dt, x(t+dt) = x(t) + v(t+dt)*dt
            acceleration = body._force_accumulator.multiply(body.get_inverse_mass())
            body.velocity = body.velocity.add(acceleration.multiply(delta_time))

            # Damping
            body.velocity = body.velocity.multiply(self._damping)

            # Clamp velocity
            speed_sq = body.velocity.length_sq()
            max_vel_sq = self._max_velocity * self._max_velocity
            if speed_sq > max_vel_sq:
                scale = self._max_velocity / math.sqrt(speed_sq)
                body.velocity = body.velocity.multiply(scale)

            # Update position
            body.position = body.position.add(body.velocity.multiply(delta_time))

            # Update rotation
            body.angular_velocity += body._torque_accumulator * body.get_inverse_mass() * delta_time
            body.angular_velocity *= self._angular_damping
            body.rotation += body.angular_velocity * delta_time

            # Sleep check
            if speed_sq < self._sleep_threshold * self._sleep_threshold and abs(body.angular_velocity) < self._sleep_threshold:
                body.is_sleeping = True

            # Clear accumulators
            body._force_accumulator = Vector2D()
            body._torque_accumulator = 0.0

    # ------------------------------------------------------------------
    # Raycasting
    # ------------------------------------------------------------------

    def raycast(
        self,
        origin_x: float,
        origin_y: float,
        direction_x: float,
        direction_y: float,
        max_distance: float = 1000.0,
        layer_mask: int = 0xFFFFFFFF,
    ) -> Optional[Dict[str, Any]]:
        """Cast a ray through the physics world and return the closest hit."""
        origin = Vector2D(origin_x, origin_y)
        direction = Vector2D(direction_x, direction_y).normalize()
        closest_hit: Optional[Dict[str, Any]] = None
        closest_dist = max_distance

        for body in self._bodies.values():
            if not (body.layer & layer_mask):
                continue

            hit = self._raycast_body(origin, direction, body, closest_dist)
            if hit is not None and hit["distance"] < closest_dist:
                closest_dist = hit["distance"]
                closest_hit = hit

        return closest_hit

    def _raycast_body(
        self,
        origin: Vector2D,
        direction: Vector2D,
        body: PhysicsBody,
        max_dist: float,
    ) -> Optional[Dict[str, Any]]:
        """Raycast against a single body."""
        if body.shape == CollisionShape.AABB:
            return self._raycast_aabb(origin, direction, body, max_dist)
        elif body.shape == CollisionShape.CIRCLE:
            return self._raycast_circle(origin, direction, body, max_dist)
        return None

    def _raycast_aabb(
        self,
        origin: Vector2D,
        direction: Vector2D,
        body: PhysicsBody,
        max_dist: float,
    ) -> Optional[Dict[str, Any]]:
        """Ray vs AABB intersection test using slab method."""
        min_x, min_y, max_x, max_y = body.get_aabb()

        t_min = 0.0
        t_max = max_dist

        # X slab
        if abs(direction.x) < 0.0000001:
            if origin.x < min_x or origin.x > max_x:
                return None
        else:
            inv_d = 1.0 / direction.x
            t1 = (min_x - origin.x) * inv_d
            t2 = (max_x - origin.x) * inv_d
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)

        if t_min > t_max:
            return None

        # Y slab
        if abs(direction.y) < 0.0000001:
            if origin.y < min_y or origin.y > max_y:
                return None
        else:
            inv_d = 1.0 / direction.y
            t1 = (min_y - origin.y) * inv_d
            t2 = (max_y - origin.y) * inv_d
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)

        if t_min > t_max:
            return None

        hit_point = origin.add(direction.multiply(t_min))
        return {
            "body_id": body.body_id,
            "distance": t_min,
            "point": hit_point.to_dict(),
            "normal": Vector2D(0.0, 0.0).to_dict(),
        }

    def _raycast_circle(
        self,
        origin: Vector2D,
        direction: Vector2D,
        body: PhysicsBody,
        max_dist: float,
    ) -> Optional[Dict[str, Any]]:
        """Ray vs circle intersection test."""
        r = float(body.shape_data.get("radius", 1.0))
        center = body.position
        to_center = center.subtract(origin)

        proj = to_center.dot(direction)
        if proj < 0.0:
            return None

        closest = to_center.subtract(direction.multiply(proj))
        dist_sq = closest.length_sq()

        if dist_sq > r * r:
            return None

        half_chord = math.sqrt(r * r - dist_sq)
        t = proj - half_chord

        if t < 0.0 or t > max_dist:
            return None

        hit_point = origin.add(direction.multiply(t))
        normal = hit_point.subtract(center).normalize()

        return {
            "body_id": body.body_id,
            "distance": t,
            "point": hit_point.to_dict(),
            "normal": normal.to_dict(),
        }

    # ------------------------------------------------------------------
    # Spatial Queries
    # ------------------------------------------------------------------

    def query_aabb(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        layer_mask: int = 0xFFFFFFFF,
    ) -> List[str]:
        """Query all bodies whose AABB overlaps the given region."""
        result: List[str] = []
        for body in self._bodies.values():
            if not (body.layer & layer_mask):
                continue
            b_min_x, b_min_y, b_max_x, b_max_y = body.get_aabb()
            if self._check_aabb_overlap(min_x, max_x, b_min_x, b_max_x) and \
               self._check_aabb_overlap(min_y, max_y, b_min_y, b_max_y):
                result.append(body.body_id)
        return result

    def query_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        layer_mask: int = 0xFFFFFFFF,
    ) -> List[str]:
        """Query all bodies within a circular region."""
        result: List[str] = []
        center = Vector2D(center_x, center_y)
        radius_sq = radius * radius

        for body in self._bodies.values():
            if not (body.layer & layer_mask):
                continue

            b_min_x, b_min_y, b_max_x, b_max_y = body.get_aabb()
            # Broad-phase: check if AABB overlaps the circle's bounding box
            if not (b_max_x > center_x - radius and b_min_x < center_x + radius):
                continue
            if not (b_max_y > center_y - radius and b_min_y < center_y + radius):
                continue

            # Narrow-phase: check body center or closest point
            if body.shape == CollisionShape.CIRCLE:
                body_r = float(body.shape_data.get("radius", 1.0))
                dist_sq = center.distance_to(body.position)
                # Bodies overlap if distance between centers < sum of radii
                if dist_sq <= (radius + body_r) ** 2:
                    result.append(body.body_id)
            else:
                # For AABB, check if any corner or the closest point is within the circle
                closest_x = max(b_min_x, min(center_x, b_max_x))
                closest_y = max(b_min_y, min(center_y, b_max_y))
                dx = center_x - closest_x
                dy = center_y - closest_y
                if dx * dx + dy * dy <= radius_sq:
                    result.append(body.body_id)

        return result

    # ------------------------------------------------------------------
    # Simulation Step
    # ------------------------------------------------------------------

    def step(
        self, delta_time: float, iterations: int = 8
    ) -> List[CollisionEvent]:
        """Advance the simulation by delta_time seconds."""
        collisions: List[CollisionEvent] = []

        with self._lock:
            sub_dt = delta_time / max(iterations, 1)

            for _ in range(iterations):
                self._step_count += 1

                # Integrate
                self._integrate(sub_dt)

                # Broad phase
                self._rebuild_spatial_grid()
                pairs = self._get_potential_pairs()
                self._total_collision_checks += len(pairs)

                # Narrow phase + resolution
                for a_id, b_id in pairs:
                    body_a = self._bodies.get(a_id)
                    body_b = self._bodies.get(b_id)
                    if body_a is None or body_b is None:
                        continue

                    # Skip static-static
                    if body_a.body_type == BodyType.STATIC and body_b.body_type == BodyType.STATIC:
                        continue

                    # Layer mask filtering
                    if not (body_a.layer & body_b.mask) or not (body_b.layer & body_a.mask):
                        continue

                    event = self._check_collision(body_a, body_b)
                    if event is not None:
                        self._resolve_collision(event)
                        collisions.append(event)
                        self._total_collisions += 1

                        # Invoke callbacks
                        for callback in self._collision_callbacks.values():
                            try:
                                callback(event)
                            except Exception:
                                pass

                # Solve constraints
                for constraint in self._constraints.values():
                    self._solve_constraint(constraint)

        return collisions

    # ------------------------------------------------------------------
    # Gravity
    # ------------------------------------------------------------------

    def set_gravity(self, x: float, y: float) -> None:
        """Set the global gravity vector."""
        with self._lock:
            self._gravity = Vector2D(x, y)

    # ------------------------------------------------------------------
    # Collision Callbacks
    # ------------------------------------------------------------------

    def register_collision_callback(
        self, callback_id: str, callback: Callable[[CollisionEvent], None]
    ) -> bool:
        """Register a callback to be invoked on each collision."""
        with self._lock:
            self._collision_callbacks[callback_id] = callback
            return True

    def unregister_collision_callback(self, callback_id: str) -> bool:
        """Unregister a collision callback."""
        with self._lock:
            if callback_id in self._collision_callbacks:
                del self._collision_callbacks[callback_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Collision Pairs
    # ------------------------------------------------------------------

    def get_collision_pairs(self) -> List[Tuple[str, str]]:
        """Get all currently overlapping body pairs."""
        self._rebuild_spatial_grid()
        return self._get_potential_pairs()

    # ------------------------------------------------------------------
    # Sleep / Wake
    # ------------------------------------------------------------------

    def wake_body(self, body_id: str) -> bool:
        """Wake a sleeping body."""
        body = self._bodies.get(body_id)
        if body is None:
            return False
        body.is_sleeping = False
        return True

    def sleep_body(self, body_id: str) -> bool:
        """Force a body to sleep."""
        body = self._bodies.get(body_id)
        if body is None:
            return False
        body.is_sleeping = True
        return True

    # ------------------------------------------------------------------
    # Layer Queries
    # ------------------------------------------------------------------

    def get_bodies_by_layer(self, layer: int) -> List[PhysicsBody]:
        """Get all bodies on a specific layer."""
        result: List[PhysicsBody] = []
        for body in self._bodies.values():
            if body.layer == layer:
                result.append(body)
        return result

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        body_type_counts: Dict[str, int] = {}
        for body in self._bodies.values():
            t = body.body_type.value
            body_type_counts[t] = body_type_counts.get(t, 0) + 1

        shape_counts: Dict[str, int] = {}
        for body in self._bodies.values():
            s = body.shape.value
            shape_counts[s] = shape_counts.get(s, 0) + 1

        return {
            "total_bodies": len(self._bodies),
            "total_constraints": len(self._constraints),
            "total_callbacks": len(self._collision_callbacks),
            "step_count": self._step_count,
            "total_collision_checks": self._total_collision_checks,
            "total_collisions": self._total_collisions,
            "gravity": self._gravity.to_dict(),
            "cell_size": self._cell_size,
            "body_type_distribution": body_type_counts,
            "shape_distribution": shape_counts,
            "spatial_grid_cells": len(self._spatial_grid),
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire physics engine state."""
        with self._lock:
            self._bodies.clear()
            self._constraints.clear()
            self._collision_callbacks.clear()
            self._spatial_grid.clear()
            self._gravity = Vector2D(0.0, -9.81)
            self._step_count = 0
            self._total_collision_checks = 0
            self._total_collisions = 0


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_physics_engine() -> PhysicsEngine:
    """Get or create the singleton PhysicsEngine instance."""
    return PhysicsEngine.get_instance()