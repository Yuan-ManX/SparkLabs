"""
SparkLabs Engine - Physics World Simulation System

A complete physics simulation engine for the AI-native game engine.
Provides rigid body dynamics, force application, collision detection
and resolution, constraint solving, and particle physics. Supports
broad-phase spatial hashing and narrow-phase shape intersection tests
for efficient collision handling.

Architecture:
  PhysicsWorldEngine (Singleton)
    |-- PhysicsBody       — rigid body with position, rotation, velocity, mass
    |-- PhysicsForce      — global force field definition
    |-- PhysicsConstraint — joint/constraint between two bodies
    |-- CollisionEvent    — recorded collision data per event

Collision Pipeline:
  1. Broad Phase  — spatial hash grid culling
  2. Narrow Phase — shape-specific intersection tests
  3. Resolution   — impulse-based contact resolution
  4. Constraints  — joint iteration after collision response
"""

from __future__ import annotations

import json
import math
import random
import threading
import time as _time_module
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BodyType(str, Enum):
    """Classification of a physics body controlling its simulation behavior."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    KINEMATIC = "kinematic"
    TRIGGER = "trigger"
    RAGDOLL = "ragdoll"


class ForceType(str, Enum):
    """Type of global force applied to bodies within the physics world."""
    GRAVITY = "gravity"
    IMPULSE = "impulse"
    SPRING = "spring"
    DRAG = "drag"
    BUOYANCY = "buoyancy"
    WIND = "wind"
    EXPLOSION = "explosion"
    MAGNETIC = "magnetic"
    VORTEX = "vortex"


class CollisionShape(str, Enum):
    """Geometric shape used for collision detection on a physics body."""
    BOX = "box"
    SPHERE = "sphere"
    CAPSULE = "capsule"
    CYLINDER = "cylinder"
    CONE = "cone"
    MESH = "mesh"
    PLANE = "plane"
    TERRAIN = "terrain"


class ConstraintType(str, Enum):
    """Type of joint or constraint connecting two physics bodies."""
    HINGE = "hinge"
    SLIDER = "slider"
    SPRING = "spring"
    FIXED = "fixed"
    POINT = "point"
    DISTANCE = "distance"
    WELD = "weld"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PhysicsBody:
    """A rigid body in the physics simulation.

    Represents a single entity with position, rotation, velocity, mass,
    collision shape, and material properties. Bodies are simulated each
    frame based on their type (static, dynamic, kinematic, trigger, ragdoll).

    Position, rotation, velocity, and angular_velocity are stored as
    3-component tuples (x, y, z).
    """

    body_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    body_type: BodyType = BodyType.DYNAMIC
    shape: CollisionShape = CollisionShape.BOX
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mass: float = 1.0
    restitution: float = 0.3
    friction: float = 0.5
    is_sleeping: bool = False
    collision_layer: int = 1
    collision_mask: int = 0xFFFFFFFF
    user_data: Dict[str, Any] = field(default_factory=dict)

    # Internal accumulated force for the current frame
    _accumulated_force: Tuple[float, float, float] = field(
        default=(0.0, 0.0, 0.0), repr=False
    )
    _accumulated_torque: Tuple[float, float, float] = field(
        default=(0.0, 0.0, 0.0), repr=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "name": self.name,
            "body_type": self.body_type.value,
            "shape": self.shape.value,
            "position": list(self.position),
            "rotation": list(self.rotation),
            "velocity": list(self.velocity),
            "angular_velocity": list(self.angular_velocity),
            "mass": self.mass,
            "restitution": self.restitution,
            "friction": self.friction,
            "is_sleeping": self.is_sleeping,
            "collision_layer": self.collision_layer,
            "collision_mask": self.collision_mask,
            "user_data": dict(self.user_data),
        }

    @property
    def inverse_mass(self) -> float:
        """Return 1/mass for static/kinematic bodies, or 0 for infinite mass."""
        if self.body_type in (BodyType.STATIC, BodyType.KINEMATIC):
            return 0.0
        if self.mass <= 0.0:
            return 0.0
        return 1.0 / self.mass

    @property
    def speed(self) -> float:
        """Scalar magnitude of the linear velocity."""
        vx, vy, vz = self.velocity
        return math.sqrt(vx * vx + vy * vy + vz * vz)


@dataclass
class PhysicsForce:
    """A global force field that affects bodies within its influence.

    Forces are applied to bodies whose collision layer intersects the
    force's affected_layers. Each force type computes its effect
    differently (gravity is uniform, explosion decays with distance, etc.).
    """

    force_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    force_type: ForceType = ForceType.GRAVITY
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: Tuple[float, float, float] = (0.0, -1.0, 0.0)
    magnitude: float = 9.81
    falloff: float = 0.0
    duration: float = -1.0
    affected_layers: int = 0xFFFFFFFF

    _creation_time: float = field(
        default_factory=_time_module.time, repr=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "force_id": self.force_id,
            "name": self.name,
            "force_type": self.force_type.value,
            "origin": list(self.origin),
            "direction": list(self.direction),
            "magnitude": self.magnitude,
            "falloff": self.falloff,
            "duration": self.duration,
            "affected_layers": self.affected_layers,
        }

    @property
    def is_expired(self) -> bool:
        """Return True if the force has a finite duration and has elapsed."""
        if self.duration < 0.0:
            return False
        return (_time_module.time() - self._creation_time) >= self.duration

    @property
    def remaining_time(self) -> float:
        """Remaining duration in seconds, or -1 if infinite."""
        if self.duration < 0.0:
            return -1.0
        return max(0.0, self.duration - (_time_module.time() - self._creation_time))


@dataclass
class PhysicsConstraint:
    """A joint or constraint connecting two physics bodies.

    Constraints enforce a relationship between two bodies, such as
    limiting their relative position, rotation, or distance. Solved
    iteratively after each collision resolution step.
    """

    constraint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    constraint_type: ConstraintType = ConstraintType.FIXED
    body_a_id: str = ""
    body_b_id: str = ""
    anchor_a: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    anchor_b: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    limits: Tuple[float, float] = (-1.0, 1.0)
    stiffness: float = 0.8
    damping: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type.value,
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "anchor_a": list(self.anchor_a),
            "anchor_b": list(self.anchor_b),
            "limits": list(self.limits),
            "stiffness": self.stiffness,
            "damping": self.damping,
        }


@dataclass
class CollisionEvent:
    """A record of a collision between two bodies during a simulation step.

    Captures the bodies involved, the world-space contact point and normal,
    the impulse magnitude applied during resolution, and the timestamp of
    the event.
    """

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    body_a_id: str = ""
    body_b_id: str = ""
    contact_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    contact_normal: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    impulse: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "contact_point": list(self.contact_point),
            "contact_normal": list(self.contact_normal),
            "impulse": self.impulse,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Vector Math Helpers
# ---------------------------------------------------------------------------

def _vec3_add(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec3_sub(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec3_scale(
    v: Tuple[float, float, float], s: float
) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec3_dot(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec3_cross(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec3_length(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec3_normalize(
    v: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    length = _vec3_length(v)
    if length < 1e-10:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _vec3_lerp(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    t: float,
) -> Tuple[float, float, float]:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _vec3_distance_sq(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return dx * dx + dy * dy + dz * dz


# ---------------------------------------------------------------------------
# PhysicsWorldEngine Singleton
# ---------------------------------------------------------------------------

class PhysicsWorldEngine:
    """Physics simulation engine managing bodies, forces, constraints, and collisions.

    Provides a complete physics pipeline: broad-phase spatial hashing,
    narrow-phase shape intersection tests, impulse-based collision
    resolution, iterative constraint solving, and force integration.

    Usage:
        pw = get_physics_world()
        body = pw.create_body("crate", BodyType.DYNAMIC, CollisionShape.BOX, (0, 0, 0))
        pw.set_gravity(0, -9.81, 0)
        events = pw.step(0.016)
        result = pw.simulate_frames(60, 0.016)
    """

    _instance: Optional["PhysicsWorldEngine"] = None
    _lock = threading.RLock()

    # Physics constants
    SLEEP_THRESHOLD: float = 0.01
    SLEEP_FRAME_COUNT: int = 60
    CONSTRAINT_ITERATIONS: int = 8
    BAUMGARTE_FACTOR: float = 0.2
    ALLOWED_PENETRATION: float = 0.01

    def __new__(cls) -> "PhysicsWorldEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "PhysicsWorldEngine":
        """Return the singleton PhysicsWorldEngine instance."""
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._bodies: Dict[str, PhysicsBody] = {}
        self._forces: Dict[str, PhysicsForce] = {}
        self._constraints: Dict[str, PhysicsConstraint] = {}
        self._collision_events: deque = deque(maxlen=1000)
        self._sleep_counters: Dict[str, int] = {}

        self._gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)
        self._air_density: float = 1.225
        self._simulation_time: float = 0.0
        self._frame_number: int = 0
        self._tick_count: int = 0

        self._total_bodies_created: int = 0
        self._total_forces_created: int = 0
        self._total_constraints_created: int = 0
        self._total_collisions_processed: int = 0

    # ------------------------------------------------------------------
    # Body Management
    # ------------------------------------------------------------------

    def create_body(
        self,
        name: str = "",
        body_type: BodyType = BodyType.DYNAMIC,
        shape: CollisionShape = CollisionShape.BOX,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        mass: float = 1.0,
        restitution: float = 0.3,
        friction: float = 0.5,
        collision_layer: int = 1,
        collision_mask: int = 0xFFFFFFFF,
    ) -> PhysicsBody:
        """Create and register a new physics body.

        Args:
            name: Display name for the body.
            body_type: How the body is simulated (static, dynamic, etc.).
            shape: Collision geometry shape.
            position: World-space position as (x, y, z).
            mass: Mass in kilograms. Static bodies use infinite mass.
            restitution: Bounciness coefficient (0.0 to 1.0).
            friction: Surface friction coefficient.
            collision_layer: Bitmask layer this body belongs to.
            collision_mask: Bitmask of layers this body collides with.

        Returns:
            The newly created PhysicsBody instance.
        """
        with self._lock:
            body = PhysicsBody(
                name=name,
                body_type=body_type,
                shape=shape,
                position=position,
                mass=mass,
                restitution=restitution,
                friction=friction,
                collision_layer=collision_layer,
                collision_mask=collision_mask,
            )
            self._bodies[body.body_id] = body
            self._sleep_counters[body.body_id] = 0
            self._total_bodies_created += 1
            return body

    def remove_body(self, body_id: str) -> bool:
        """Remove a body from the simulation.

        Also removes any constraints that reference this body.

        Args:
            body_id: The ID of the body to remove.

        Returns:
            True if the body was found and removed, False otherwise.
        """
        with self._lock:
            if body_id not in self._bodies:
                return False
            del self._bodies[body_id]
            self._sleep_counters.pop(body_id, None)

            # Remove constraints referencing this body
            to_remove = [
                cid
                for cid, c in self._constraints.items()
                if c.body_a_id == body_id or c.body_b_id == body_id
            ]
            for cid in to_remove:
                del self._constraints[cid]

            return True

    def get_body(self, body_id: str) -> Optional[PhysicsBody]:
        """Retrieve a body by its ID.

        Args:
            body_id: The body ID to look up.

        Returns:
            The PhysicsBody if found, or None.
        """
        return self._bodies.get(body_id)

    def list_bodies(
        self, body_type: Optional[BodyType] = None
    ) -> List[PhysicsBody]:
        """List all bodies, optionally filtered by type.

        Args:
            body_type: Optional BodyType to filter by. If None, returns all bodies.

        Returns:
            List of matching PhysicsBody instances.
        """
        with self._lock:
            if body_type is None:
                return list(self._bodies.values())
            return [
                b for b in self._bodies.values() if b.body_type == body_type
            ]

    # ------------------------------------------------------------------
    # Force Application
    # ------------------------------------------------------------------

    def apply_force(
        self,
        body_id: str,
        force_type: ForceType,
        direction: Tuple[float, float, float],
        magnitude: float,
        duration: float = 0.0,
    ) -> Optional[PhysicsBody]:
        """Apply an instantaneous force to a specific body.

        The force is accumulated and applied during the next step() call.
        Impulse forces are applied immediately to velocity.

        Args:
            body_id: The target body ID.
            force_type: Type of force to apply.
            direction: Force direction vector (will be normalized internally).
            magnitude: Strength of the force.
            duration: Duration in seconds (0 = instantaneous impulse).

        Returns:
            The updated PhysicsBody, or None if body not found.
        """
        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return None
            if body.body_type == BodyType.STATIC:
                return body

            direction_norm = _vec3_normalize(direction)
            force_vec = _vec3_scale(direction_norm, magnitude)

            if force_type == ForceType.IMPULSE or duration <= 0.0:
                # Impulse: directly modify velocity
                body.velocity = _vec3_add(body.velocity, _vec3_scale(force_vec, body.inverse_mass))
            else:
                # Accumulate for later integration
                body._accumulated_force = _vec3_add(body._accumulated_force, force_vec)

            body.is_sleeping = False
            self._sleep_counters[body_id] = 0
            return body

    def create_global_force(
        self,
        name: str = "",
        force_type: ForceType = ForceType.GRAVITY,
        origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        direction: Tuple[float, float, float] = (0.0, -1.0, 0.0),
        magnitude: float = 9.81,
        falloff: float = 0.0,
        duration: float = -1.0,
        affected_layers: int = 0xFFFFFFFF,
    ) -> PhysicsForce:
        """Create a global force field that affects bodies in the world.

        Global forces are evaluated each simulation step for every body
        whose collision layer matches the affected_layers bitmask.

        Args:
            name: Display name for the force.
            force_type: The type of force field.
            origin: World-space origin of the force effect.
            direction: Primary direction of the force.
            magnitude: Strength of the force.
            falloff: Distance-based attenuation factor (0 = no falloff).
            duration: Lifetime in seconds (-1 = infinite).
            affected_layers: Bitmask of collision layers affected.

        Returns:
            The newly created PhysicsForce instance.
        """
        with self._lock:
            force = PhysicsForce(
                name=name,
                force_type=force_type,
                origin=origin,
                direction=direction,
                magnitude=magnitude,
                falloff=falloff,
                duration=duration,
                affected_layers=affected_layers,
            )
            self._forces[force.force_id] = force
            self._total_forces_created += 1
            return force

    def remove_global_force(self, force_id: str) -> bool:
        """Remove a global force from the world.

        Args:
            force_id: The ID of the force to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if force_id not in self._forces:
                return False
            del self._forces[force_id]
            return True

    # ------------------------------------------------------------------
    # Gravity
    # ------------------------------------------------------------------

    def set_gravity(self, x: float, y: float, z: float) -> None:
        """Set the world gravity vector.

        Args:
            x: Gravity acceleration along the X axis.
            y: Gravity acceleration along the Y axis.
            z: Gravity acceleration along the Z axis.
        """
        self._gravity = (x, y, z)

    def get_gravity(self) -> Tuple[float, float, float]:
        """Return the current world gravity vector."""
        return self._gravity

    # ------------------------------------------------------------------
    # Constraint Management
    # ------------------------------------------------------------------

    def create_constraint(
        self,
        constraint_type: ConstraintType,
        body_a_id: str,
        body_b_id: str,
        anchor_a: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        anchor_b: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        limits: Tuple[float, float] = (-1.0, 1.0),
        stiffness: float = 0.8,
        damping: float = 0.1,
    ) -> PhysicsConstraint:
        """Create a constraint (joint) connecting two bodies.

        Constraints enforce a geometric relationship between body A and
        body B, such as a fixed distance, hinge rotation, or spring
        connection. They are solved iteratively during each step.

        Args:
            constraint_type: The type of constraint.
            body_a_id: ID of the first body.
            body_b_id: ID of the second body.
            anchor_a: Local-space anchor point on body A.
            anchor_b: Local-space anchor point on body B.
            limits: (min, max) range for the constraint parameter.
            stiffness: Correction strength (0.0 to 1.0).
            damping: Velocity damping factor (0.0 to 1.0).

        Returns:
            The newly created PhysicsConstraint instance.
        """
        with self._lock:
            constraint = PhysicsConstraint(
                constraint_type=constraint_type,
                body_a_id=body_a_id,
                body_b_id=body_b_id,
                anchor_a=anchor_a,
                anchor_b=anchor_b,
                limits=limits,
                stiffness=stiffness,
                damping=damping,
            )
            self._constraints[constraint.constraint_id] = constraint
            self._total_constraints_created += 1
            return constraint

    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove a constraint from the world.

        Args:
            constraint_id: The ID of the constraint to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if constraint_id not in self._constraints:
                return False
            del self._constraints[constraint_id]
            return True

    # ------------------------------------------------------------------
    # Broad Phase — Spatial Hash Grid
    # ------------------------------------------------------------------

    def _broad_phase(
        self, cell_size: float = 2.0
    ) -> List[Tuple[str, str]]:
        """Perform broad-phase collision detection using spatial hashing.

        Bodies are assigned to grid cells based on their position. Only
        pairs of bodies that share a cell or adjacent cells are returned
        for further narrow-phase testing.

        Args:
            cell_size: Size of each spatial hash cell in world units.

        Returns:
            List of (body_a_id, body_b_id) candidate collision pairs.
        """
        grid: Dict[Tuple[int, int, int], List[str]] = {}
        active_bodies: List[PhysicsBody] = []

        for body in self._bodies.values():
            if body.body_type == BodyType.STATIC:
                active_bodies.append(body)
                continue
            if body.is_sleeping:
                continue
            active_bodies.append(body)

        for body in active_bodies:
            px, py, pz = body.position
            cx = int(math.floor(px / cell_size))
            cy = int(math.floor(py / cell_size))
            cz = int(math.floor(pz / cell_size))
            key = (cx, cy, cz)
            if key not in grid:
                grid[key] = []
            grid[key].append(body.body_id)

        pairs: Set[Tuple[str, str]] = set()
        neighbor_offsets = [
            (dx, dy, dz)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for dz in (-1, 0, 1)
        ]

        for (cx, cy, cz), cell_body_ids in grid.items():
            for dx, dy, dz in neighbor_offsets:
                nkey = (cx + dx, cy + dy, cz + dz)
                neighbor_ids = grid.get(nkey, [])
                for i, id_a in enumerate(cell_body_ids):
                    for id_b in neighbor_ids:
                        if id_a >= id_b:
                            continue
                        pair = (id_a, id_b) if id_a < id_b else (id_b, id_a)
                        pairs.add(pair)

        return list(pairs)

    # ------------------------------------------------------------------
    # Narrow Phase — Shape Intersection Tests
    # ------------------------------------------------------------------

    def _narrow_phase(
        self, body_a: PhysicsBody, body_b: PhysicsBody
    ) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float], float]]:
        """Perform narrow-phase collision detection between two bodies.

        Checks whether the collision layers overlap, then runs a
        shape-specific intersection test and returns contact data.

        Args:
            body_a: First body.
            body_b: Second body.

        Returns:
            Tuple of (contact_point, contact_normal, penetration_depth)
            if colliding, or None if no collision.
        """
        # Layer-mask check
        if (body_a.collision_layer & body_b.collision_mask) == 0:
            return None
        if (body_b.collision_layer & body_a.collision_mask) == 0:
            return None

        # Dispatch to shape-specific test
        shape_pair = (body_a.shape, body_b.shape)

        if CollisionShape.SPHERE in shape_pair and CollisionShape.SPHERE in shape_pair:
            return self._sphere_sphere_test(body_a, body_b)
        if CollisionShape.BOX in shape_pair and CollisionShape.BOX in shape_pair:
            return self._box_box_test(body_a, body_b)
        if CollisionShape.PLANE in shape_pair:
            return self._plane_body_test(body_a, body_b)
        # Generic sphere-primitive test for mixed shapes
        return self._sphere_sphere_test(body_a, body_b)

    def _sphere_sphere_test(
        self, body_a: PhysicsBody, body_b: PhysicsBody
    ) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float], float]]:
        """Sphere-sphere intersection test.

        Assumes a default radius of 0.5 for each body. Computes the
        distance between centers and checks if it is less than the sum
        of radii.

        Returns:
            (contact_point, normal, penetration) or None.
        """
        radius_a = 0.5
        radius_b = 0.5
        sum_radii = radius_a + radius_b

        pos_a = body_a.position
        pos_b = body_b.position
        dist_sq = _vec3_distance_sq(pos_a, pos_b)
        if dist_sq >= sum_radii * sum_radii or dist_sq < 1e-10:
            return None

        dist = math.sqrt(dist_sq)
        normal = _vec3_normalize(_vec3_sub(pos_a, pos_b))
        penetration = sum_radii - dist

        contact_point = _vec3_lerp(pos_a, pos_b, radius_a / sum_radii)
        return (contact_point, normal, penetration)

    def _box_box_test(
        self, body_a: PhysicsBody, body_b: PhysicsBody
    ) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float], float]]:
        """Box-box intersection test using simplified AABB overlap.

        Treats each box as a unit cube centered at the body position.
        Returns the minimum penetration axis and depth.

        Returns:
            (contact_point, normal, penetration) or None.
        """
        half_a = 0.5
        half_b = 0.5

        pa = body_a.position
        pb = body_b.position

        # Calculate overlap on each axis
        overlap_x = (half_a + half_b) - abs(pa[0] - pb[0])
        overlap_y = (half_a + half_b) - abs(pa[1] - pb[1])
        overlap_z = (half_a + half_b) - abs(pa[2] - pb[2])

        if overlap_x <= 0.0 or overlap_y <= 0.0 or overlap_z <= 0.0:
            return None

        # Minimum penetration axis
        if overlap_x <= overlap_y and overlap_x <= overlap_z:
            penetration = overlap_x
            normal = (1.0 if pa[0] > pb[0] else -1.0, 0.0, 0.0)
        elif overlap_y <= overlap_z:
            penetration = overlap_y
            normal = (0.0, 1.0 if pa[1] > pb[1] else -1.0, 0.0)
        else:
            penetration = overlap_z
            normal = (0.0, 0.0, 1.0 if pa[2] > pb[2] else -1.0)

        contact_x = (pa[0] + pb[0]) * 0.5
        contact_y = (pa[1] + pb[1]) * 0.5
        contact_z = (pa[2] + pb[2]) * 0.5
        return ((contact_x, contact_y, contact_z), normal, penetration)

    def _plane_body_test(
        self, body_a: PhysicsBody, body_b: PhysicsBody
    ) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float], float]]:
        """Plane-against-body intersection test.

        The plane is assumed to be at the origin of the plane body with
        normal pointing upward (0, 1, 0). The other body is treated as
        a sphere with radius 0.5.

        Returns:
            (contact_point, normal, penetration) or None.
        """
        if body_a.shape == CollisionShape.PLANE:
            plane_body = body_a
            other_body = body_b
        else:
            plane_body = body_b
            other_body = body_a

        plane_normal = (0.0, 1.0, 0.0)
        plane_pos = plane_body.position
        other_pos = other_body.position
        radius = 0.5

        signed_dist = _vec3_dot(_vec3_sub(other_pos, plane_pos), plane_normal)

        if signed_dist >= radius:
            return None

        penetration = radius - signed_dist
        contact_point = _vec3_sub(other_pos, _vec3_scale(plane_normal, radius))

        if body_a.shape == CollisionShape.PLANE:
            contact_normal = plane_normal
        else:
            contact_normal = _vec3_scale(plane_normal, -1.0)

        return (contact_point, contact_normal, penetration)

    # ------------------------------------------------------------------
    # Collision Resolution
    # ------------------------------------------------------------------

    def _resolve_collision(
        self,
        body_a: PhysicsBody,
        body_b: PhysicsBody,
        contact_point: Tuple[float, float, float],
        contact_normal: Tuple[float, float, float],
        penetration: float,
    ) -> CollisionEvent:
        """Resolve a collision between two bodies using impulse-based response.

        Applies positional correction to resolve penetration and computes
        the collision impulse based on relative velocity along the contact
        normal, with restitution and friction.

        Args:
            body_a: First body in collision.
            body_b: Second body in collision.
            contact_point: World-space contact point.
            contact_normal: Normal pointing from B toward A.
            penetration: Depth of penetration.

        Returns:
            A CollisionEvent describing the resolved collision.
        """
        inv_mass_a = body_a.inverse_mass
        inv_mass_b = body_b.inverse_mass
        total_inv_mass = inv_mass_a + inv_mass_b

        if total_inv_mass < 1e-10:
            return CollisionEvent(
                body_a_id=body_a.body_id,
                body_b_id=body_b.body_id,
                contact_point=contact_point,
                contact_normal=contact_normal,
                impulse=0.0,
            )

        # Positional correction (Baumgarte stabilization)
        slop = self.ALLOWED_PENETRATION
        correction_factor = self.BAUMGARTE_FACTOR / (1.0 / 60.0)
        if penetration > slop:
            correction = max(penetration - slop, 0.0) * correction_factor
            correction_vec = _vec3_scale(contact_normal, correction / total_inv_mass)
            body_a.position = _vec3_add(body_a.position, _vec3_scale(correction_vec, inv_mass_a))
            body_b.position = _vec3_sub(body_b.position, _vec3_scale(correction_vec, inv_mass_b))

        # Relative velocity
        rel_vel = _vec3_sub(body_a.velocity, body_b.velocity)
        vel_along_normal = _vec3_dot(rel_vel, contact_normal)

        # Only resolve if bodies are moving toward each other
        if vel_along_normal > 0.0:
            return CollisionEvent(
                body_a_id=body_a.body_id,
                body_b_id=body_b.body_id,
                contact_point=contact_point,
                contact_normal=contact_normal,
                impulse=0.0,
            )

        # Restitution (use the minimum of the two)
        restitution = min(body_a.restitution, body_b.restitution)

        # Impulse magnitude
        impulse_scalar = -(1.0 + restitution) * vel_along_normal / total_inv_mass

        # Friction
        tangent = _vec3_sub(rel_vel, _vec3_scale(contact_normal, vel_along_normal))
        tangent_len = _vec3_length(tangent)
        if tangent_len > 1e-10:
            tangent = _vec3_normalize(tangent)
            friction_coeff = min(body_a.friction, body_b.friction)
            friction_impulse = -_vec3_dot(rel_vel, tangent) / total_inv_mass
            friction_impulse = max(-impulse_scalar * friction_coeff,
                                  min(impulse_scalar * friction_coeff, friction_impulse))
            impulse_vec = _vec3_add(
                _vec3_scale(contact_normal, impulse_scalar),
                _vec3_scale(tangent, friction_impulse),
            )
        else:
            impulse_vec = _vec3_scale(contact_normal, impulse_scalar)

        # Apply impulse
        body_a.velocity = _vec3_add(body_a.velocity, _vec3_scale(impulse_vec, inv_mass_a))
        body_b.velocity = _vec3_sub(body_b.velocity, _vec3_scale(impulse_vec, inv_mass_b))

        # Wake bodies
        body_a.is_sleeping = False
        body_b.is_sleeping = False
        self._sleep_counters[body_a.body_id] = 0
        self._sleep_counters[body_b.body_id] = 0

        return CollisionEvent(
            body_a_id=body_a.body_id,
            body_b_id=body_b.body_id,
            contact_point=contact_point,
            contact_normal=contact_normal,
            impulse=impulse_scalar,
        )

    # ------------------------------------------------------------------
    # Constraint Solving
    # ------------------------------------------------------------------

    def _solve_constraints(self) -> None:
        """Solve all active constraints iteratively.

        Iterates through each constraint type (distance, spring, fixed,
        point, hinge, slider, weld) and applies positional corrections
        to satisfy the constraint relationship.

        For distance constraints, the bodies are pulled apart or pushed
        together to maintain the target distance. For spring constraints,
        a Hooke's-law force is applied. For fixed/weld constraints, the
        relative transform is locked.
        """
        for _ in range(self.CONSTRAINT_ITERATIONS):
            for constraint in self._constraints.values():
                body_a = self._bodies.get(constraint.body_a_id)
                body_b = self._bodies.get(constraint.body_b_id)
                if body_a is None or body_b is None:
                    continue

                pa = _vec3_add(body_a.position, constraint.anchor_a)
                pb = _vec3_add(body_b.position, constraint.anchor_b)
                delta = _vec3_sub(pb, pa)
                dist = _vec3_length(delta)

                if dist < 1e-10:
                    continue

                direction = _vec3_normalize(delta)

                inv_mass_a = body_a.inverse_mass
                inv_mass_b = body_b.inverse_mass
                total_inv_mass = inv_mass_a + inv_mass_b
                if total_inv_mass < 1e-10:
                    continue

                if constraint.constraint_type == ConstraintType.DISTANCE:
                    target_dist = constraint.limits[0]
                    if target_dist <= 0.0:
                        continue
                    correction = (dist - target_dist) * constraint.stiffness
                    offset = _vec3_scale(direction, correction / total_inv_mass)
                    body_a.position = _vec3_add(body_a.position, _vec3_scale(offset, inv_mass_a))
                    body_b.position = _vec3_sub(body_b.position, _vec3_scale(offset, inv_mass_b))

                    # Velocity damping
                    rel_vel = _vec3_sub(body_a.velocity, body_b.velocity)
                    vel_along = _vec3_dot(rel_vel, direction)
                    if vel_along > 0.0:
                        damping_impulse = vel_along * constraint.damping / total_inv_mass
                        damp_vec = _vec3_scale(direction, damping_impulse)
                        body_a.velocity = _vec3_sub(body_a.velocity, _vec3_scale(damp_vec, inv_mass_a))
                        body_b.velocity = _vec3_add(body_b.velocity, _vec3_scale(damp_vec, inv_mass_b))

                elif constraint.constraint_type == ConstraintType.SPRING:
                    rest_length = constraint.limits[0]
                    if rest_length <= 0.0:
                        continue
                    displacement = dist - rest_length
                    spring_force = -constraint.stiffness * displacement
                    force_vec = _vec3_scale(direction, spring_force)
                    body_a._accumulated_force = _vec3_add(body_a._accumulated_force, force_vec)
                    body_b._accumulated_force = _vec3_sub(body_b._accumulated_force, force_vec)

                elif constraint.constraint_type in (ConstraintType.FIXED, ConstraintType.WELD):
                    correction = dist * constraint.stiffness
                    offset = _vec3_scale(direction, correction / total_inv_mass)
                    body_a.position = _vec3_add(body_a.position, _vec3_scale(offset, inv_mass_a))
                    body_b.position = _vec3_sub(body_b.position, _vec3_scale(offset, inv_mass_b))

                    # Align velocities
                    vel_avg = _vec3_scale(
                        _vec3_add(body_a.velocity, body_b.velocity), 0.5
                    )
                    body_a.velocity = _vec3_lerp(body_a.velocity, vel_avg, constraint.stiffness)
                    body_b.velocity = _vec3_lerp(body_b.velocity, vel_avg, constraint.stiffness)

                elif constraint.constraint_type == ConstraintType.POINT:
                    # Point constraint: keep the anchor points coincident
                    correction = dist * constraint.stiffness
                    offset = _vec3_scale(direction, correction / total_inv_mass)
                    body_a.position = _vec3_add(body_a.position, _vec3_scale(offset, inv_mass_a))
                    body_b.position = _vec3_sub(body_b.position, _vec3_scale(offset, inv_mass_b))

                elif constraint.constraint_type == ConstraintType.HINGE:
                    # Hinge: pivot around a shared axis — keep anchor points coincident
                    correction = dist * constraint.stiffness
                    offset = _vec3_scale(direction, correction / total_inv_mass)
                    body_a.position = _vec3_add(body_a.position, _vec3_scale(offset, inv_mass_a))
                    body_b.position = _vec3_sub(body_b.position, _vec3_scale(offset, inv_mass_b))

                elif constraint.constraint_type == ConstraintType.SLIDER:
                    # Slider: allow movement along one axis, constrain the other two
                    correction = dist * constraint.stiffness
                    offset = _vec3_scale(direction, correction / total_inv_mass)
                    body_a.position = _vec3_add(body_a.position, _vec3_scale(offset, inv_mass_a))
                    body_b.position = _vec3_sub(body_b.position, _vec3_scale(offset, inv_mass_b))

    # ------------------------------------------------------------------
    # Force Integration
    # ------------------------------------------------------------------

    def _integrate_forces(self, delta_time: float) -> None:
        """Integrate forces and update velocities for all dynamic bodies.

        Applies gravity, global forces, and accumulated per-body forces,
        then updates velocities using Euler integration.

        Args:
            delta_time: Timestep duration in seconds.
        """
        for body in self._bodies.values():
            if body.body_type in (BodyType.STATIC, BodyType.KINEMATIC):
                continue
            if body.is_sleeping:
                continue

            inv_mass = body.inverse_mass
            if inv_mass <= 0.0:
                continue

            total_force = (0.0, 0.0, 0.0)

            # Gravity
            total_force = _vec3_add(total_force, _vec3_scale(self._gravity, body.mass))

            # Global forces
            expired_forces: List[str] = []
            for force in self._forces.values():
                if force.is_expired:
                    expired_forces.append(force.force_id)
                    continue
                if (body.collision_layer & force.affected_layers) == 0:
                    continue

                force_contribution = self._compute_force_contribution(force, body)
                total_force = _vec3_add(total_force, force_contribution)

            for fid in expired_forces:
                del self._forces[fid]

            # Accumulated forces
            total_force = _vec3_add(total_force, body._accumulated_force)

            # Euler integration of velocity
            acceleration = _vec3_scale(total_force, inv_mass)
            body.velocity = _vec3_add(body.velocity, _vec3_scale(acceleration, delta_time))

            # Reset accumulated forces
            body._accumulated_force = (0.0, 0.0, 0.0)
            body._accumulated_torque = (0.0, 0.0, 0.0)

    def _compute_force_contribution(
        self, force: PhysicsForce, body: PhysicsBody
    ) -> Tuple[float, float, float]:
        """Compute the force vector contributed by a global force to a body.

        Different force types compute their effect differently:
          - GRAVITY: uniform acceleration in the force direction
          - WIND: uniform force based on direction and magnitude
          - DRAG: opposes velocity, proportional to speed squared
          - EXPLOSION: radial force decaying with distance from origin
          - VORTEX: tangential force around the origin axis
          - BUOYANCY: upward force opposing gravity
          - MAGNETIC: attraction toward the origin
          - SPRING: force toward origin proportional to distance
          - IMPULSE: one-time impulse (applied via apply_force instead)

        Args:
            force: The global force definition.
            body: The body being affected.

        Returns:
            Force vector as (fx, fy, fz).
        """
        direction_norm = _vec3_normalize(force.direction)

        if force.force_type == ForceType.GRAVITY:
            return _vec3_scale(direction_norm, force.magnitude * body.mass)

        elif force.force_type == ForceType.WIND:
            return _vec3_scale(direction_norm, force.magnitude * body.mass * 0.1)

        elif force.force_type == ForceType.DRAG:
            vx, vy, vz = body.velocity
            speed = math.sqrt(vx * vx + vy * vy + vz * vz)
            if speed < 1e-10:
                return (0.0, 0.0, 0.0)
            drag_dir = _vec3_normalize(body.velocity)
            drag_mag = -force.magnitude * speed * speed * self._air_density * 0.5
            return _vec3_scale(drag_dir, drag_mag)

        elif force.force_type == ForceType.EXPLOSION:
            offset = _vec3_sub(body.position, force.origin)
            dist = _vec3_length(offset)
            if dist < 1e-10:
                return _vec3_scale(direction_norm, force.magnitude * body.mass)
            radial_dir = _vec3_normalize(offset)
            falloff_factor = 1.0 / (1.0 + force.falloff * dist * dist)
            return _vec3_scale(radial_dir, force.magnitude * body.mass * falloff_factor)

        elif force.force_type == ForceType.VORTEX:
            offset = _vec3_sub(body.position, force.origin)
            dist = _vec3_length(offset)
            if dist < 1e-10:
                return (0.0, 0.0, 0.0)
            tangential = _vec3_cross(direction_norm, offset)
            tangential_norm = _vec3_normalize(tangential)
            falloff_factor = 1.0 / (1.0 + force.falloff * dist * dist)
            return _vec3_scale(tangential_norm, force.magnitude * body.mass * falloff_factor)

        elif force.force_type == ForceType.BUOYANCY:
            return _vec3_scale(direction_norm, force.magnitude * body.mass)

        elif force.force_type == ForceType.MAGNETIC:
            offset = _vec3_sub(force.origin, body.position)
            dist = _vec3_length(offset)
            if dist < 1e-10:
                return (0.0, 0.0, 0.0)
            attraction_dir = _vec3_normalize(offset)
            falloff_factor = 1.0 / (1.0 + force.falloff * dist * dist)
            return _vec3_scale(attraction_dir, force.magnitude * body.mass * falloff_factor)

        elif force.force_type == ForceType.SPRING:
            offset = _vec3_sub(force.origin, body.position)
            dist = _vec3_length(offset)
            if dist < 1e-10:
                return (0.0, 0.0, 0.0)
            spring_dir = _vec3_normalize(offset)
            spring_force = force.magnitude * dist
            return _vec3_scale(spring_dir, spring_force * body.mass)

        else:
            return _vec3_scale(direction_norm, force.magnitude * body.mass)

    # ------------------------------------------------------------------
    # Position Integration
    # ------------------------------------------------------------------

    def _integrate_positions(self, delta_time: float) -> None:
        """Update positions of all dynamic bodies based on their velocities.

        Applies semi-implicit Euler integration: new_position = position + velocity * dt.

        Args:
            delta_time: Timestep duration in seconds.
        """
        for body in self._bodies.values():
            if body.body_type in (BodyType.STATIC, BodyType.KINEMATIC):
                continue
            if body.is_sleeping:
                continue

            body.position = _vec3_add(
                body.position,
                _vec3_scale(body.velocity, delta_time),
            )

    # ------------------------------------------------------------------
    # Sleep Management
    # ------------------------------------------------------------------

    def _update_sleep_state(self) -> None:
        """Update sleep state for all dynamic bodies.

        A body enters sleep when its speed has been below the threshold
        for SLEEP_FRAME_COUNT consecutive frames. A sleeping body is
        excluded from force integration and collision detection until
        woken by an external force or collision.
        """
        for body in self._bodies.values():
            if body.body_type in (BodyType.STATIC, BodyType.KINEMATIC, BodyType.RAGDOLL):
                continue

            body_id = body.body_id
            if body.speed < self.SLEEP_THRESHOLD:
                self._sleep_counters[body_id] = self._sleep_counters.get(body_id, 0) + 1
                if self._sleep_counters[body_id] >= self.SLEEP_FRAME_COUNT:
                    body.is_sleeping = True
            else:
                self._sleep_counters[body_id] = 0
                body.is_sleeping = False

    # ------------------------------------------------------------------
    # Main Simulation Step
    # ------------------------------------------------------------------

    def step(self, delta_time: float) -> List[CollisionEvent]:
        """Advance the physics simulation by one timestep.

        Full pipeline:
          1. Apply global forces and integrate velocities
          2. Broad-phase collision detection (spatial hash)
          3. Narrow-phase collision detection (shape intersection)
          4. Collision resolution (impulse-based)
          5. Constraint solving (iterative)
          6. Position integration
          7. Sleep state update
          8. Generate collision events

        Args:
            delta_time: Timestep duration in seconds.

        Returns:
            List of CollisionEvent objects for collisions detected this frame.
        """
        with self._lock:
            dt = max(0.0, min(delta_time, 0.1))  # Clamp to prevent explosion
            events: List[CollisionEvent] = []

            # 1. Integrate forces
            self._integrate_forces(dt)

            # 2. Broad phase
            candidate_pairs = self._broad_phase()

            # 3-4. Narrow phase + Collision resolution
            for id_a, id_b in candidate_pairs:
                body_a = self._bodies.get(id_a)
                body_b = self._bodies.get(id_b)
                if body_a is None or body_b is None:
                    continue
                if body_a.is_sleeping and body_b.is_sleeping:
                    continue
                if body_a.body_type == BodyType.TRIGGER or body_b.body_type == BodyType.TRIGGER:
                    # Trigger overlap: generate event without resolution
                    overlap = self._narrow_phase(body_a, body_b)
                    if overlap is not None:
                        contact_point, contact_normal, _ = overlap
                        event = CollisionEvent(
                            body_a_id=id_a,
                            body_b_id=id_b,
                            contact_point=contact_point,
                            contact_normal=contact_normal,
                            impulse=0.0,
                        )
                        events.append(event)
                        self._collision_events.append(event)
                        self._total_collisions_processed += 1
                    continue

                overlap = self._narrow_phase(body_a, body_b)
                if overlap is None:
                    continue

                contact_point, contact_normal, penetration = overlap
                event = self._resolve_collision(
                    body_a, body_b, contact_point, contact_normal, penetration
                )
                events.append(event)
                self._collision_events.append(event)
                self._total_collisions_processed += 1

            # 5. Solve constraints
            self._solve_constraints()

            # 6. Integrate positions
            self._integrate_positions(dt)

            # 7. Update sleep state
            self._update_sleep_state()

            # 8. Advance simulation time
            self._simulation_time += dt
            self._frame_number += 1
            self._tick_count += 1

            return events

    def simulate_frames(
        self, frame_count: int, delta_time: float
    ) -> Dict[str, Any]:
        """Run the simulation for multiple frames and collect results.

        Args:
            frame_count: Number of frames to simulate.
            delta_time: Fixed timestep per frame.

        Returns:
            Dict with 'total_events', 'events', 'final_state', and
            'simulation_time' keys.
        """
        all_events: List[Dict[str, Any]] = []
        total_event_count = 0

        for _ in range(frame_count):
            frame_events = self.step(delta_time)
            total_event_count += len(frame_events)
            all_events.extend([e.to_dict() for e in frame_events])

        return {
            "total_events": total_event_count,
            "events": all_events,
            "final_state": self.get_stats(),
            "simulation_time": round(self._simulation_time, 4),
        }

    # ------------------------------------------------------------------
    # Statistics and Query
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the physics world.

        Returns:
            Dict with body counts, force counts, constraint counts,
            collision metrics, and performance data.
        """
        with self._lock:
            body_type_counts: Dict[str, int] = {}
            for body in self._bodies.values():
                t = body.body_type.value
                body_type_counts[t] = body_type_counts.get(t, 0) + 1

            shape_counts: Dict[str, int] = {}
            for body in self._bodies.values():
                s = body.shape.value
                shape_counts[s] = shape_counts.get(s, 0) + 1

            sleeping_count = sum(1 for b in self._bodies.values() if b.is_sleeping)
            dynamic_count = sum(
                1 for b in self._bodies.values() if b.body_type == BodyType.DYNAMIC
            )

            force_type_counts: Dict[str, int] = {}
            for force in self._forces.values():
                t = force.force_type.value
                force_type_counts[t] = force_type_counts.get(t, 0) + 1

            constraint_type_counts: Dict[str, int] = {}
            for constraint in self._constraints.values():
                t = constraint.constraint_type.value
                constraint_type_counts[t] = constraint_type_counts.get(t, 0) + 1

            return {
                "total_bodies": len(self._bodies),
                "total_bodies_created": self._total_bodies_created,
                "body_type_distribution": body_type_counts,
                "shape_distribution": shape_counts,
                "dynamic_bodies": dynamic_count,
                "sleeping_bodies": sleeping_count,
                "total_forces": len(self._forces),
                "total_forces_created": self._total_forces_created,
                "force_type_distribution": force_type_counts,
                "total_constraints": len(self._constraints),
                "total_constraints_created": self._total_constraints_created,
                "constraint_type_distribution": constraint_type_counts,
                "total_collisions_processed": self._total_collisions_processed,
                "recent_collision_events": len(self._collision_events),
                "gravity": list(self._gravity),
                "frame_number": self._frame_number,
                "tick_count": self._tick_count,
                "simulation_time": round(self._simulation_time, 4),
            }

    def get_recent_collisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the most recent collision events.

        Args:
            limit: Maximum number of events to return.

        Returns:
            List of serialized CollisionEvent dicts.
        """
        with self._lock:
            events = list(self._collision_events)[-limit:]
            return [e.to_dict() for e in events]

    def reset(self) -> None:
        """Reset the entire physics world to its initial state."""
        with self._lock:
            self._bodies.clear()
            self._forces.clear()
            self._constraints.clear()
            self._collision_events.clear()
            self._sleep_counters.clear()
            self._gravity = (0.0, -9.81, 0.0)
            self._simulation_time = 0.0
            self._frame_number = 0
            self._tick_count = 0
            self._total_bodies_created = 0
            self._total_forces_created = 0
            self._total_constraints_created = 0
            self._total_collisions_processed = 0

    def to_json(self) -> str:
        """Serialize the entire physics world state to a JSON string.

        Returns:
            JSON string representation of the world state.
        """
        with self._lock:
            state = {
                "bodies": [b.to_dict() for b in self._bodies.values()],
                "forces": [f.to_dict() for f in self._forces.values()],
                "constraints": [c.to_dict() for c in self._constraints.values()],
                "gravity": list(self._gravity),
                "simulation_time": self._simulation_time,
                "frame_number": self._frame_number,
                "stats": self.get_stats(),
            }
            return json.dumps(state, indent=2)

    def from_json(self, json_str: str) -> bool:
        """Load physics world state from a JSON string.

        This replaces the current world state with the deserialized data.

        Args:
            json_str: JSON string previously produced by to_json().

        Returns:
            True if the world was successfully loaded.
        """
        try:
            state = json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return False

        with self._lock:
            self._bodies.clear()
            self._forces.clear()
            self._constraints.clear()
            self._collision_events.clear()
            self._sleep_counters.clear()

            for b_data in state.get("bodies", []):
                body = PhysicsBody(
                    body_id=b_data.get("body_id", uuid.uuid4().hex[:12]),
                    name=b_data.get("name", ""),
                    body_type=BodyType(b_data.get("body_type", "dynamic")),
                    shape=CollisionShape(b_data.get("shape", "box")),
                    position=tuple(b_data.get("position", [0, 0, 0])),
                    rotation=tuple(b_data.get("rotation", [0, 0, 0])),
                    velocity=tuple(b_data.get("velocity", [0, 0, 0])),
                    angular_velocity=tuple(b_data.get("angular_velocity", [0, 0, 0])),
                    mass=b_data.get("mass", 1.0),
                    restitution=b_data.get("restitution", 0.3),
                    friction=b_data.get("friction", 0.5),
                    is_sleeping=b_data.get("is_sleeping", False),
                    collision_layer=b_data.get("collision_layer", 1),
                    collision_mask=b_data.get("collision_mask", 0xFFFFFFFF),
                    user_data=b_data.get("user_data", {}),
                )
                self._bodies[body.body_id] = body
                self._sleep_counters[body.body_id] = 0

            for f_data in state.get("forces", []):
                force = PhysicsForce(
                    force_id=f_data.get("force_id", uuid.uuid4().hex[:12]),
                    name=f_data.get("name", ""),
                    force_type=ForceType(f_data.get("force_type", "gravity")),
                    origin=tuple(f_data.get("origin", [0, 0, 0])),
                    direction=tuple(f_data.get("direction", [0, -1, 0])),
                    magnitude=f_data.get("magnitude", 9.81),
                    falloff=f_data.get("falloff", 0.0),
                    duration=f_data.get("duration", -1.0),
                    affected_layers=f_data.get("affected_layers", 0xFFFFFFFF),
                )
                self._forces[force.force_id] = force

            for c_data in state.get("constraints", []):
                constraint = PhysicsConstraint(
                    constraint_id=c_data.get("constraint_id", uuid.uuid4().hex[:12]),
                    constraint_type=ConstraintType(c_data.get("constraint_type", "fixed")),
                    body_a_id=c_data.get("body_a_id", ""),
                    body_b_id=c_data.get("body_b_id", ""),
                    anchor_a=tuple(c_data.get("anchor_a", [0, 0, 0])),
                    anchor_b=tuple(c_data.get("anchor_b", [0, 0, 0])),
                    limits=tuple(c_data.get("limits", [-1.0, 1.0])),
                    stiffness=c_data.get("stiffness", 0.8),
                    damping=c_data.get("damping", 0.1),
                )
                self._constraints[constraint.constraint_id] = constraint

            self._gravity = tuple(state.get("gravity", [0.0, -9.81, 0.0]))
            self._simulation_time = state.get("simulation_time", 0.0)
            self._frame_number = state.get("frame_number", 0)

            return True

    def add_body(
        self,
        name: str = "",
        body_type: str = "dynamic",
        shape: str = "box",
        position: List[float] = None,
        mass: float = 1.0,
        restitution: float = 0.3,
        friction: float = 0.5,
        collision_layer: int = 1,
        collision_mask: int = 0xFFFFFFFF,
        velocity: List[float] = None,
        user_data: Dict[str, Any] = None,
    ) -> PhysicsBody:
        """Create a physics body from REST-friendly parameters.

        Convenience wrapper around create_body that accepts string
        enum values and list-based coordinates.

        Args:
            name: Display name for the body.
            body_type: Type string ("static", "dynamic", etc.).
            shape: Collision shape string ("box", "sphere", etc.).
            position: [x, y, z] position list.
            mass: Body mass in kilograms.
            restitution: Bounciness coefficient.
            friction: Surface friction coefficient.
            collision_layer: Bitmask layer.
            collision_mask: Bitmask of collidable layers.
            velocity: [vx, vy, vz] initial velocity list.
            user_data: Optional arbitrary metadata dict.

        Returns:
            The created PhysicsBody.
        """
        pos = tuple(position) if position else (0.0, 0.0, 0.0)
        vel = tuple(velocity) if velocity else (0.0, 0.0, 0.0)

        try:
            bt = BodyType(body_type)
        except ValueError:
            bt = BodyType.DYNAMIC

        try:
            cs = CollisionShape(shape)
        except ValueError:
            cs = CollisionShape.BOX

        body = self.create_body(
            name=name,
            body_type=bt,
            shape=cs,
            position=pos,
            mass=mass,
            restitution=restitution,
            friction=friction,
            collision_layer=collision_layer,
            collision_mask=collision_mask,
        )
        body.velocity = vel
        if user_data:
            body.user_data = user_data
        return body


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_physics_world() -> PhysicsWorldEngine:
    """Get or create the singleton PhysicsWorldEngine instance."""
    return PhysicsWorldEngine.get_instance()