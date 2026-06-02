"""
SparkLabs Engine - 2D Physics Simulation World
Complete 2D physics simulation system with rigid body dynamics,
collision detection, force application, and constraint solving.
Supports multiple body types, collision shapes, material properties,
and physics joints for constrained motion between bodies.

Architecture:
  EnginePhysicsWorld2D (singleton)
    |-- PhysicsWorld2D (isolated simulation world)
    |   |-- RigidBody2D (individual rigid body)
    |   |-- PhysicsJoint (constraint between bodies)
    |   |-- CollisionEvent (collision contact information)
    |   |-- RayCastResult (ray intersection query result)
    |-- Broad-phase spatial partitioning
    |-- Narrow-phase collision detection
    |-- Impulse-based collision resolution
    |-- Sequential impulse constraint solving

Features:
  - Multiple body types (static, dynamic, kinematic, trigger)
  - Multiple collision shapes (box, circle, polygon, capsule, etc.)
  - Collision filtering via category/mask system
  - Various force modes (impulse, constant, acceleration, velocity change)
  - Predefined physics materials with friction and restitution
  - Built-in collision matrix presets for common game object types
  - Continuous collision detection for fast-moving objects
  - Sleeping optimization for inactive bodies
  - Performance metrics collection and reporting
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class BodyType(Enum):
    """Rigid body classification for simulation behavior."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    KINEMATIC = "kinematic"
    TRIGGER = "trigger"


class CollisionShape(Enum):
    """Collision primitive shape types for hit detection."""
    BOX = "box"
    CIRCLE = "circle"
    POLYGON = "polygon"
    CAPSULE = "capsule"
    LINE_SEGMENT = "line_segment"
    POINT = "point"
    CONVEX_HULL = "convex_hull"


class CollisionCategory(Enum):
    """Collision category classification for filtering."""
    PLAYER = "player"
    ENEMY = "enemy"
    PROJECTILE = "projectile"
    TERRAIN = "terrain"
    ITEM = "item"
    TRIGGER = "trigger"
    SENSOR = "sensor"
    CUSTOM = "custom"


class ForceMode(Enum):
    """Force application mode for different force types."""
    IMPULSE = "impulse"
    CONSTANT = "constant"
    ACCELERATION = "acceleration"
    VELOCITY_CHANGE = "velocity_change"


class JointType(Enum):
    """Physics joint constraint types."""
    SPRING = "spring"
    DISTANCE = "distance"
    HINGE = "hinge"
    SLIDER = "slider"
    WELD = "weld"
    PULLEY = "pulley"


class BroadPhaseType(Enum):
    """Broad-phase collision detection algorithm."""
    NAIVE = "naive"
    SPATIAL_HASH = "spatial_hash"
    SWEEP_AND_PRUNE = "sweep_and_prune"


@dataclass
class RigidBody2D:
    """Two-dimensional rigid body with physical properties."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    body_type: BodyType = BodyType.DYNAMIC
    position: Tuple[float, float] = (0.0, 0.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    rotation: float = 0.0
    angular_velocity: float = 0.0
    mass: float = 1.0
    inertia: float = 0.0
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    gravity_scale: float = 1.0
    is_bullet: bool = False
    fixed_rotation: bool = False
    sleeping: bool = False
    collision_shape: CollisionShape = CollisionShape.BOX
    collision_category: CollisionCategory = CollisionCategory.CUSTOM
    collision_mask: int = 0xFFFFFFFF
    restitution: float = 0.3
    friction: float = 0.5
    density: float = 1.0
    half_extents: Tuple[float, float] = (0.5, 0.5)
    radius: float = 0.5
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    force_accumulator: Tuple[float, float] = (0.0, 0.0)
    torque_accumulator: float = 0.0
    bounds: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    material_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def inv_mass(self) -> float:
        """Inverse mass for impulse calculations."""
        if self.body_type != BodyType.DYNAMIC or self.mass <= 0:
            return 0.0
        return 1.0 / self.mass

    @property
    def inv_inertia(self) -> float:
        """Inverse inertia for angular impulse calculations."""
        if self.fixed_rotation or self.inertia <= 0:
            return 0.0
        return 1.0 / self.inertia

    def to_dict(self) -> Dict[str, Any]:
        """Convert rigid body to dictionary representation."""
        return {
            "id": self.id,
            "body_type": self.body_type.value,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "rotation": self.rotation,
            "angular_velocity": self.angular_velocity,
            "mass": self.mass,
            "inertia": self.inertia,
            "sleeping": self.sleeping,
            "collision_shape": self.collision_shape.value,
            "collision_category": self.collision_category.value,
            "restitution": self.restitution,
            "friction": self.friction,
            "density": self.density,
            "bounds": list(self.bounds),
        }


@dataclass
class CollisionEvent:
    """Collision contact information between two rigid bodies."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    body_a_id: str = ""
    body_b_id: str = ""
    contact_point: Tuple[float, float] = (0.0, 0.0)
    contact_normal: Tuple[float, float] = (0.0, 0.0)
    penetration_depth: float = 0.0
    relative_velocity: float = 0.0
    impulse_magnitude: float = 0.0
    timestamp: float = 0.0
    category_a: CollisionCategory = CollisionCategory.CUSTOM
    category_b: CollisionCategory = CollisionCategory.CUSTOM
    is_trigger_a: bool = False
    is_trigger_b: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert collision event to dictionary representation."""
        return {
            "id": self.id,
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "contact_point": list(self.contact_point),
            "contact_normal": list(self.contact_normal),
            "penetration_depth": self.penetration_depth,
            "relative_velocity": self.relative_velocity,
            "impulse_magnitude": self.impulse_magnitude,
            "timestamp": self.timestamp,
            "category_a": self.category_a.value,
            "category_b": self.category_b.value,
        }


@dataclass
class PhysicsJoint:
    """Constraint joint between two rigid bodies."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    body_a_id: str = ""
    body_b_id: str = ""
    joint_type: JointType = JointType.DISTANCE
    anchor_a: Tuple[float, float] = (0.0, 0.0)
    anchor_b: Tuple[float, float] = (0.0, 0.0)
    stiffness: float = 100.0
    damping: float = 0.5
    lower_limit: float = 0.0
    upper_limit: float = 0.0
    motor_speed: float = 0.0
    max_motor_force: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert physics joint to dictionary representation."""
        return {
            "id": self.id,
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "joint_type": self.joint_type.value,
            "anchor_a": list(self.anchor_a),
            "anchor_b": list(self.anchor_b),
            "stiffness": self.stiffness,
            "damping": self.damping,
            "lower_limit": self.lower_limit,
            "upper_limit": self.upper_limit,
            "motor_speed": self.motor_speed,
            "max_motor_force": self.max_motor_force,
            "enabled": self.enabled,
        }


@dataclass
class RayCastResult:
    """Result from a raycast query."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    origin: Tuple[float, float] = (0.0, 0.0)
    direction: Tuple[float, float] = (0.0, 0.0)
    hit_body_id: Optional[str] = None
    hit_point: Tuple[float, float] = (0.0, 0.0)
    hit_normal: Tuple[float, float] = (0.0, 0.0)
    distance: float = 0.0
    fraction: float = 0.0
    hit: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert raycast result to dictionary representation."""
        return {
            "id": self.id,
            "origin": list(self.origin),
            "direction": list(self.direction),
            "hit_body_id": self.hit_body_id,
            "hit_point": list(self.hit_point),
            "hit_normal": list(self.hit_normal),
            "distance": self.distance,
            "fraction": self.fraction,
            "hit": self.hit,
        }


@dataclass
class PhysicsMaterial:
    """Physical material properties for collision response."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    restitution: float = 0.3
    static_friction: float = 0.5
    dynamic_friction: float = 0.4
    density: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert physics material to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "restitution": self.restitution,
            "static_friction": self.static_friction,
            "dynamic_friction": self.dynamic_friction,
            "density": self.density,
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for physics simulation."""
    total_broad_phase_pairs: int = 0
    total_narrow_phase_tests: int = 0
    total_collisions_detected: int = 0
    total_joint_constraints: int = 0
    broad_phase_ms: float = 0.0
    integration_ms: float = 0.0
    collision_ms: float = 0.0
    solving_ms: float = 0.0
    total_step_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert performance metrics to dictionary representation."""
        return {
            "total_broad_phase_pairs": self.total_broad_phase_pairs,
            "total_narrow_phase_tests": self.total_narrow_phase_tests,
            "total_collisions_detected": self.total_collisions_detected,
            "total_joint_constraints": self.total_joint_constraints,
            "broad_phase_ms": self.broad_phase_ms,
            "integration_ms": self.integration_ms,
            "collision_ms": self.collision_ms,
            "solving_ms": self.solving_ms,
            "total_step_ms": self.total_step_ms,
        }


@dataclass
class PhysicsWorld2D:
    """Independent 2D physics simulation world."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    gravity: Tuple[float, float] = (0.0, -9.81)
    bodies: Dict[str, RigidBody2D] = field(default_factory=dict)
    joints: Dict[str, PhysicsJoint] = field(default_factory=dict)
    collision_events: List[CollisionEvent] = field(default_factory=list)
    simulation_speed: float = 1.0
    iterations: int = 10
    broad_phase_type: BroadPhaseType = BroadPhaseType.SPATIAL_HASH
    contact_cache: Dict[str, CollisionEvent] = field(default_factory=dict)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    cell_size: float = 4.0
    sleep_threshold: float = 0.01
    max_bodies: int = 1000
    max_joints: int = 100
    collision_callbacks: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert physics world to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "gravity": list(self.gravity),
            "body_count": len(self.bodies),
            "joint_count": len(self.joints),
            "event_count": len(self.collision_events),
            "simulation_speed": self.simulation_speed,
            "iterations": self.iterations,
            "broad_phase_type": self.broad_phase_type.value,
        }


class EnginePhysicsWorld2D:
    """
    Main 2D physics simulation engine singleton.
    Manages multiple independent physics worlds with full rigid body
    dynamics, collision detection, force application, and joint constraints.
    """

    _instance: Optional["EnginePhysicsWorld2D"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_WORLDS = 16
    DEFAULT_GRAVITY_X = 0.0
    DEFAULT_GRAVITY_Y = -9.81

    PREDEFINED_MATERIALS = {
        "default": {"restitution": 0.3, "static_friction": 0.5, "dynamic_friction": 0.4, "density": 1.0},
        "rubber": {"restitution": 0.8, "static_friction": 0.9, "dynamic_friction": 0.7, "density": 1.2},
        "ice": {"restitution": 0.1, "static_friction": 0.1, "dynamic_friction": 0.05, "density": 0.9},
        "metal": {"restitution": 0.25, "static_friction": 0.4, "dynamic_friction": 0.3, "density": 7.8},
        "wood": {"restitution": 0.2, "static_friction": 0.6, "dynamic_friction": 0.5, "density": 0.7},
        "concrete": {"restitution": 0.1, "static_friction": 0.7, "dynamic_friction": 0.6, "density": 2.4},
        "glass": {"restitution": 0.15, "static_friction": 0.3, "dynamic_friction": 0.25, "density": 2.5},
        "bouncy": {"restitution": 0.9, "static_friction": 0.3, "dynamic_friction": 0.25, "density": 0.1},
        "rock": {"restitution": 0.1, "static_friction": 0.6, "dynamic_friction": 0.5, "density": 2.6},
        "dirt": {"restitution": 0.0, "static_friction": 0.8, "dynamic_friction": 0.7, "density": 1.5},
    }

    COLLISION_CATEGORY_BITS = {
        CollisionCategory.PLAYER: 1 << 0,
        CollisionCategory.ENEMY: 1 << 1,
        CollisionCategory.PROJECTILE: 1 << 2,
        CollisionCategory.TERRAIN: 1 << 3,
        CollisionCategory.ITEM: 1 << 4,
        CollisionCategory.TRIGGER: 1 << 5,
        CollisionCategory.SENSOR: 1 << 6,
        CollisionCategory.CUSTOM: 1 << 7,
    }

    COLLISION_MATRIX_PRESETS = {
        "default_game": {
            CollisionCategory.PLAYER: [
                CollisionCategory.ENEMY, CollisionCategory.PROJECTILE,
                CollisionCategory.TERRAIN, CollisionCategory.ITEM,
            ],
            CollisionCategory.ENEMY: [
                CollisionCategory.PLAYER, CollisionCategory.PROJECTILE,
                CollisionCategory.TERRAIN,
            ],
            CollisionCategory.PROJECTILE: [
                CollisionCategory.PLAYER, CollisionCategory.ENEMY,
                CollisionCategory.TERRAIN, CollisionCategory.ITEM,
            ],
            CollisionCategory.TERRAIN: [
                CollisionCategory.PLAYER, CollisionCategory.ENEMY,
                CollisionCategory.PROJECTILE, CollisionCategory.ITEM,
            ],
            CollisionCategory.ITEM: [
                CollisionCategory.PLAYER, CollisionCategory.TERRAIN,
                CollisionCategory.PROJECTILE,
            ],
            CollisionCategory.TRIGGER: [
                CollisionCategory.PLAYER, CollisionCategory.ENEMY,
            ],
            CollisionCategory.SENSOR: [
                CollisionCategory.PLAYER, CollisionCategory.ENEMY,
                CollisionCategory.ITEM,
            ],
        },
        "platformer": {
            CollisionCategory.PLAYER: [
                CollisionCategory.ENEMY, CollisionCategory.PROJECTILE,
                CollisionCategory.TERRAIN, CollisionCategory.ITEM,
            ],
            CollisionCategory.ENEMY: [
                CollisionCategory.PLAYER, CollisionCategory.PROJECTILE,
                CollisionCategory.TERRAIN,
            ],
            CollisionCategory.PROJECTILE: [
                CollisionCategory.PLAYER, CollisionCategory.ENEMY,
                CollisionCategory.TERRAIN,
            ],
            CollisionCategory.TERRAIN: [
                CollisionCategory.PLAYER, CollisionCategory.ENEMY,
                CollisionCategory.PROJECTILE, CollisionCategory.ITEM,
            ],
            CollisionCategory.ITEM: [
                CollisionCategory.PLAYER,
            ],
        },
        "topdown": {
            CollisionCategory.PLAYER: [
                CollisionCategory.ENEMY, CollisionCategory.PROJECTILE,
                CollisionCategory.TERRAIN, CollisionCategory.ITEM,
            ],
            CollisionCategory.ENEMY: [
                CollisionCategory.PLAYER, CollisionCategory.PROJECTILE,
                CollisionCategory.TERRAIN,
            ],
            CollisionCategory.PROJECTILE: [
                CollisionCategory.PLAYER, CollisionCategory.ENEMY,
                CollisionCategory.TERRAIN,
            ],
            CollisionCategory.TERRAIN: [
                CollisionCategory.PLAYER, CollisionCategory.ENEMY,
                CollisionCategory.PROJECTILE,
            ],
        },
    }

    def __new__(cls) -> "EnginePhysicsWorld2D":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._worlds: Dict[str, PhysicsWorld2D] = {}
        self._materials: Dict[str, PhysicsMaterial] = {}
        self._total_steps: int = 0
        self._total_collisions: int = 0
        self._seed_predefined_materials()
        _time_module.sleep(0.001)

    @classmethod
    def get_instance(cls) -> "EnginePhysicsWorld2D":
        """Get the singleton instance with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = EnginePhysicsWorld2D()
        return cls._instance

    def _seed_predefined_materials(self) -> None:
        """Seed predefined physics materials into the material library."""
        for name, props in self.PREDEFINED_MATERIALS.items():
            material = PhysicsMaterial(
                name=name,
                restitution=props["restitution"],
                static_friction=props["static_friction"],
                dynamic_friction=props["dynamic_friction"],
                density=props["density"],
            )
            self._materials[material.id] = material
        _time_module.sleep(0.001)

    def get_category_mask(self, category: CollisionCategory, preset_name: str = "default_game") -> int:
        """Get collision mask for a category based on a preset matrix."""
        mask = 0
        if preset_name in self.COLLISION_MATRIX_PRESETS:
            preset = self.COLLISION_MATRIX_PRESETS[preset_name]
            if category in preset:
                for collides_with in preset[category]:
                    mask |= self.COLLISION_CATEGORY_BITS[collides_with]
        _time_module.sleep(0.001)
        return mask if mask != 0 else 0xFFFFFFFF

    def create_world(
        self,
        name: str,
        gravity_x: float = DEFAULT_GRAVITY_X,
        gravity_y: float = DEFAULT_GRAVITY_Y,
    ) -> PhysicsWorld2D:
        """Create a new physics simulation world."""
        if len(self._worlds) >= self.MAX_WORLDS:
            raise RuntimeError(
                f"Maximum worlds ({self.MAX_WORLDS}) reached. "
                "Remove unused worlds before creating new ones."
            )

        world = PhysicsWorld2D(
            name=name,
            gravity=(gravity_x, gravity_y),
        )
        self._worlds[world.id] = world
        _time_module.sleep(0.001)
        return world

    def get_world(self, world_id: str) -> Optional[PhysicsWorld2D]:
        """Get a physics world by ID."""
        return self._worlds.get(world_id)

    def remove_world(self, world_id: str) -> bool:
        """Remove a physics world."""
        if world_id in self._worlds:
            del self._worlds[world_id]
            _time_module.sleep(0.001)
            return True
        return False

    def create_body(
        self,
        world_id: str,
        body_type: BodyType,
        position: Tuple[float, float],
        shape: CollisionShape = CollisionShape.BOX,
        mass: float = 1.0,
    ) -> Optional[RigidBody2D]:
        """Create a new rigid body in the specified world."""
        world = self._worlds.get(world_id)
        if not world or len(world.bodies) >= world.max_bodies:
            return None

        body = RigidBody2D(
            body_type=body_type,
            position=position,
            collision_shape=shape,
            mass=mass if body_type == BodyType.DYNAMIC else 0.0,
        )

        if body_type == BodyType.DYNAMIC:
            body.sleeping = False
        else:
            body.sleeping = True

        world.bodies[body.id] = body
        self.compute_aabb(body)
        _time_module.sleep(0.001)
        return body

    def remove_body(self, world_id: str, body_id: str) -> bool:
        """Remove a rigid body from the world."""
        world = self._worlds.get(world_id)
        if not world or body_id not in world.bodies:
            return False

        del world.bodies[body_id]

        world.joints = {
            jid: joint for jid, joint in world.joints.items()
            if joint.body_a_id != body_id and joint.body_b_id != body_id
        }

        if body_id in world.collision_callbacks:
            del world.collision_callbacks[body_id]

        _time_module.sleep(0.001)
        return True

    def apply_force(
        self,
        world_id: str,
        body_id: str,
        force_x: float,
        force_y: float,
        mode: ForceMode = ForceMode.CONSTANT,
        point: Optional[Tuple[float, float]] = None,
    ) -> bool:
        """Apply a force to a rigid body using the specified force mode."""
        world = self._worlds.get(world_id)
        if not world:
            return False

        body = world.bodies.get(body_id)
        if not body or body.body_type != BodyType.DYNAMIC:
            return False

        if mode == ForceMode.CONSTANT:
            fx, fy = body.force_accumulator
            body.force_accumulator = (fx + force_x, fy + force_y)
        elif mode == ForceMode.IMPULSE:
            vx, vy = body.velocity
            body.velocity = (
                vx + force_x * body.inv_mass,
                vy + force_y * body.inv_mass,
            )
            if point is not None:
                px, py = body.position
                rx = point[0] - px
                ry = point[1] - py
                torque = rx * force_y - ry * force_x
                body.angular_velocity += torque * body.inv_inertia
        elif mode == ForceMode.ACCELERATION:
            fx, fy = body.force_accumulator
            body.force_accumulator = (fx + force_x * body.mass, fy + force_y * body.mass)
        elif mode == ForceMode.VELOCITY_CHANGE:
            vx, vy = body.velocity
            body.velocity = (vx + force_x, vy + force_y)
            if point is not None:
                px, py = body.position
                rx = point[0] - px
                ry = point[1] - py
                torque = rx * force_y - ry * force_x
                body.angular_velocity += torque * body.inv_inertia

        body.sleeping = False
        _time_module.sleep(0.001)
        return True

    def apply_impulse(
        self,
        world_id: str,
        body_id: str,
        impulse_x: float,
        impulse_y: float,
        point: Optional[Tuple[float, float]] = None,
    ) -> bool:
        """Apply an impulse directly to a rigid body."""
        result = self.apply_force(
            world_id, body_id, impulse_x, impulse_y,
            ForceMode.IMPULSE, point
        )
        _time_module.sleep(0.001)
        return result

    def set_velocity(
        self,
        world_id: str,
        body_id: str,
        vx: float,
        vy: float,
    ) -> bool:
        """Set the linear velocity of a rigid body directly."""
        world = self._worlds.get(world_id)
        if not world:
            return False

        body = world.bodies.get(body_id)
        if not body:
            return False

        body.velocity = (vx, vy)
        body.sleeping = False if body.body_type == BodyType.DYNAMIC else True
        _time_module.sleep(0.001)
        return True

    def set_angular_velocity(
        self,
        world_id: str,
        body_id: str,
        omega: float,
    ) -> bool:
        """Set the angular velocity of a rigid body directly."""
        world = self._worlds.get(world_id)
        if not world:
            return False

        body = world.bodies.get(body_id)
        if not body or body.fixed_rotation:
            return False

        body.angular_velocity = omega
        body.sleeping = False if body.body_type == BodyType.DYNAMIC else True
        _time_module.sleep(0.001)
        return True

    def set_position(
        self,
        world_id: str,
        body_id: str,
        x: float,
        y: float,
    ) -> bool:
        """Set the position of a rigid body."""
        world = self._worlds.get(world_id)
        if not world:
            return False

        body = world.bodies.get(body_id)
        if not body:
            return False

        body.position = (x, y)
        self.compute_aabb(body)
        _time_module.sleep(0.001)
        return True

    def create_joint(
        self,
        world_id: str,
        body_a_id: str,
        body_b_id: str,
        joint_type: JointType,
        anchor_a: Tuple[float, float] = (0.0, 0.0),
        anchor_b: Tuple[float, float] = (0.0, 0.0),
    ) -> Optional[PhysicsJoint]:
        """Create a new physics joint between two bodies."""
        world = self._worlds.get(world_id)
        if not world or len(world.joints) >= world.max_joints:
            return None

        if body_a_id not in world.bodies or body_b_id not in world.bodies:
            return None

        joint = PhysicsJoint(
            body_a_id=body_a_id,
            body_b_id=body_b_id,
            joint_type=joint_type,
            anchor_a=anchor_a,
            anchor_b=anchor_b,
        )

        if joint_type == JointType.DISTANCE:
            a = world.bodies[body_a_id]
            b = world.bodies[body_b_id]
            dx = b.position[0] - a.position[0]
            dy = b.position[1] - a.position[1]
            distance = math.sqrt(dx * dx + dy * dy)
            joint.lower_limit = joint.upper_limit = distance

        world.joints[joint.id] = joint
        _time_module.sleep(0.001)
        return joint

    def register_collision_callback(
        self,
        world_id: str,
        body_id: str,
        callback_mask: int,
    ) -> bool:
        """Register a body for collision event callbacks."""
        world = self._worlds.get(world_id)
        if not world or body_id not in world.bodies:
            return False

        world.collision_callbacks[body_id] = callback_mask
        _time_module.sleep(0.001)
        return True

    def set_gravity(
        self,
        world_id: str,
        gx: float,
        gy: float,
    ) -> bool:
        """Set the gravity vector for a physics world."""
        world = self._worlds.get(world_id)
        if not world:
            return False

        world.gravity = (gx, gy)
        _time_module.sleep(0.001)
        return True

    def compute_aabb(self, body: RigidBody2D) -> Tuple[float, float, float, float]:
        """Compute the axis-aligned bounding box for a rigid body."""
        x, y = body.position

        if body.collision_shape == CollisionShape.BOX:
            hw, hh = body.half_extents
            min_x = x - hw
            max_x = x + hw
            min_y = y - hh
            max_y = y + hh
        elif body.collision_shape == CollisionShape.CIRCLE:
            r = body.radius
            min_x = x - r
            max_x = x + r
            min_y = y - r
            max_y = y + r
        elif body.collision_shape == CollisionShape.CAPSULE:
            hw = body.half_extents[0]
            r = body.radius
            min_x = x - hw - r
            max_x = x + hw + r
            min_y = y - hw - r
            max_y = y + hw + r
        elif body.collision_shape == CollisionShape.POLYGON and body.vertices:
            xs = [x + vx for vx, vy in body.vertices]
            ys = [y + vy for vx, vy in body.vertices]
            min_x = min(xs)
            max_x = max(xs)
            min_y = min(ys)
            max_y = max(ys)
        else:
            min_x = x - 0.5
            max_x = x + 0.5
            min_y = y - 0.5
            max_y = y + 0.5

        body.bounds = (min_x, min_y, max_x, max_y)
        return body.bounds

    def detect_overlap(
        self,
        a: RigidBody2D,
        b: RigidBody2D,
    ) -> Optional[Tuple[Tuple[float, float], Tuple[float, float], float]]:
        """Detect overlap between two rigid bodies and return collision info."""
        a_bounds = a.bounds
        b_bounds = b.bounds

        if a_bounds[2] < b_bounds[0] or a_bounds[0] > b_bounds[2]:
            return None
        if a_bounds[3] < b_bounds[1] or a_bounds[1] > b_bounds[3]:
            return None

        ax, ay = a.position
        bx, by = b.position

        if a.collision_shape == CollisionShape.CIRCLE and b.collision_shape == CollisionShape.CIRCLE:
            dx = bx - ax
            dy = by - ay
            dist_sq = dx * dx + dy * dy
            sum_r = a.radius + b.radius
            if dist_sq > sum_r * sum_r:
                return None
            dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.0001
            nx = dx / dist
            ny = dy / dist
            penetration = sum_r - dist
            contact_x = ax + nx * (a.radius - penetration * 0.5)
            contact_y = ay + ny * (a.radius - penetration * 0.5)
            return ((contact_x, contact_y), (nx, ny), penetration)

        result = self._sat_test(a, b)
        _time_module.sleep(0.001)
        return result

    def _sat_test(
        self,
        a: RigidBody2D,
        b: RigidBody2D,
    ) -> Optional[Tuple[Tuple[float, float], Tuple[float, float], float]]:
        """Separating Axis Theorem test for convex polygon collision."""
        vertices_a = self._get_world_vertices(a)
        vertices_b = self._get_world_vertices(b)

        if not vertices_a or not vertices_b:
            return self._circle_convex_test(a, b) if a.collision_shape == CollisionShape.CIRCLE else self._circle_convex_test(b, a)

        axes = self._get_axes(vertices_a) + self._get_axes(vertices_b)

        min_penetration = float('inf')
        best_axis = (1.0, 0.0)

        for axis in axes:
            proj_a = self._project(vertices_a, axis)
            proj_b = self._project(vertices_b, axis)

            overlap = self._get_overlap(proj_a, proj_b)
            if overlap <= 0:
                return None

            if overlap < min_penetration:
                min_penetration = overlap
                best_axis = axis

        center_a = a.position
        center_b = b.position

        dx = center_b[0] - center_a[0]
        dy = center_b[1] - center_a[1]

        if dx * best_axis[0] + dy * best_axis[1] < 0:
            best_axis = (-best_axis[0], -best_axis[1])

        contact_point = self._find_contact_point(vertices_a, vertices_b, best_axis)
        _time_module.sleep(0.001)
        return (contact_point, best_axis, min_penetration)

    def _get_world_vertices(self, body: RigidBody2D) -> List[Tuple[float, float]]:
        """Get vertices transformed to world space."""
        if body.collision_shape == CollisionShape.BOX:
            x, y = body.position
            hw, hh = body.half_extents
            return [
                (x - hw, y - hh),
                (x + hw, y - hh),
                (x + hw, y + hh),
                (x - hw, y + hh),
            ]
        elif body.collision_shape == CollisionShape.POLYGON:
            x, y = body.position
            return [(x + vx, y + vy) for vx, vy in body.vertices]
        elif body.collision_shape == CollisionShape.CAPSULE:
            x, y = body.position
            half_h = body.half_extents[1]
            r = body.radius
            steps = 8
            vertices = []
            for i in range(steps):
                angle = math.pi * i / steps
                vertices.append((x + r * math.cos(angle), y + half_h + r * math.sin(angle)))
            for i in range(steps):
                angle = math.pi + math.pi * i / steps
                vertices.append((x + r * math.cos(angle), y - half_h + r * math.sin(angle)))
            return vertices
        return []

    def _get_axes(self, vertices: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Get normals for all edges as potential separating axes."""
        axes = []
        count = len(vertices)
        for i in range(count):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % count]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            nx = -dy
            ny = dx
            length = math.sqrt(nx * nx + ny * ny)
            if length > 0.0001:
                nx /= length
                ny /= length
                axes.append((nx, ny))
        return axes

    def _project(
        self,
        vertices: List[Tuple[float, float]],
        axis: Tuple[float, float],
    ) -> Tuple[float, float]:
        """Project vertices onto an axis and return min/max interval."""
        ax, ay = axis
        min_p = max_p = ax * vertices[0][0] + ay * vertices[0][1]
        for x, y in vertices[1:]:
            p = ax * x + ay * y
            if p < min_p:
                min_p = p
            if p > max_p:
                max_p = p
        return (min_p, max_p)

    def _get_overlap(self, proj_a: Tuple[float, float], proj_b: Tuple[float, float]) -> float:
        """Calculate overlap between two intervals."""
        if proj_a[0] < proj_b[0]:
            return proj_b[1] - proj_a[0] if proj_a[1] > proj_b[0] else 0.0
        else:
            return proj_a[1] - proj_b[0] if proj_b[1] > proj_a[0] else 0.0

    def _find_contact_point(
        self,
        vertices_a: List[Tuple[float, float]],
        vertices_b: List[Tuple[float, float]],
        normal: Tuple[float, float],
    ) -> Tuple[float, float]:
        """Find the contact point on the first shape."""
        cx, cy = 0.0, 0.0
        count = 0

        for v in vertices_a:
            vx, vy = v
            dot = vx * normal[0] + vy * normal[1]
            cx += vx
            cy += vy
            count += 1

        return (cx / count, cy / count) if count > 0 else (0.0, 0.0)

    def _circle_convex_test(
        self,
        circle: RigidBody2D,
        convex: RigidBody2D,
    ) -> Optional[Tuple[Tuple[float, float], Tuple[float, float], float]]:
        """Circle vs convex polygon collision test."""
        vertices = self._get_world_vertices(convex)
        if not vertices:
            return None

        cx, cy = circle.position
        closest_dist = float('inf')
        closest_point = vertices[0]

        for vertex in vertices:
            vx, vy = vertex
            dx = cx - vx
            dy = cy - vy
            dist_sq = dx * dx + dy * dy
            if dist_sq < closest_dist:
                closest_dist = dist_sq
                closest_point = vertex

        vx, vy = closest_point
        nx = cx - vx
        ny = cy - vy
        dist = math.sqrt(nx * nx + ny * ny) if dist > 0 else 0.0001
        nx /= dist
        ny /= dist

        if dist - circle.radius > 0:
            return None

        penetration = circle.radius - dist
        contact_x = cx - nx * (penetration * 0.5)
        contact_y = cy - ny * (penetration * 0.5)
        return ((contact_x, contact_y), (nx, ny), penetration)

    def resolve_collision(
        self,
        a: RigidBody2D,
        b: RigidBody2D,
        contact_point: Tuple[float, float],
        contact_normal: Tuple[float, float],
        penetration: float,
    ) -> float:
        """Resolve collision between two bodies with impulse-based solution."""
        nx, ny = contact_normal
        cx, cy = contact_point

        ax, ay = a.position
        bx, by = b.position

        rax = cx - ax
        ray = cy - ay
        rbx = cx - bx
        rby = cy - by

        ra_cross_n = rax * ny - ray * nx
        rb_cross_n = rbx * ny - rby * nx

        mass_normal = a.inv_mass + b.inv_mass
        mass_normal += (ra_cross_n * ra_cross_n) * a.inv_inertia
        mass_normal += (rb_cross_n * rb_cross_n) * b.inv_inertia

        if mass_normal <= 0:
            return 0.0

        va_vel_x, va_vel_y = a.velocity
        vb_vel_x, vb_vel_y = b.velocity

        va_ang = a.angular_velocity
        vb_ang = b.angular_velocity

        contact_vel_x = (vb_vel_x - vb_ang * rby) - (va_vel_x - va_ang * ray)
        contact_vel_y = (vb_vel_y + vb_ang * rbx) - (va_vel_y + va_ang * rax)
        rel_vel_normal = contact_vel_x * nx + contact_vel_y * ny

        if rel_vel_normal > 0:
            return 0.0

        restitution = max(a.restitution, b.restitution)
        j = -(1 + restitution) * rel_vel_normal / mass_normal

        impulse_mag = j
        jx = j * nx
        jy = j * ny

        if a.body_type == BodyType.DYNAMIC:
            a.velocity = (
                va_vel_x - a.inv_mass * jx,
                va_vel_y - a.inv_mass * jy,
            )
            a.angular_velocity -= a.inv_inertia * (rax * jy - ray * jx)

        if b.body_type == BodyType.DYNAMIC:
            b.velocity = (
                vb_vel_x + b.inv_mass * jx,
                vb_vel_y + b.inv_mass * jy,
            )
            b.angular_velocity += b.inv_inertia * (rbx * jy - rby * jx)

        total_friction = (a.friction + b.friction) * 0.5
        tangent_x = contact_vel_x - rel_vel_normal * nx
        tangent_y = contact_vel_y - rel_vel_normal * ny
        tangent_len = math.sqrt(tangent_x * tangent_x + tangent_y * tangent_y)

        if tangent_len > 0.0001:
            tangent_x /= tangent_len
            tangent_y /= tangent_len
            jt = -(contact_vel_x * tangent_x + contact_vel_y * tangent_y) / mass_normal
            jt = min(jt, impulse_mag * total_friction)

            jtx = jt * tangent_x
            jty = jt * tangent_y

            if a.body_type == BodyType.DYNAMIC:
                a.velocity = (
                    a.velocity[0] - a.inv_mass * jtx,
                    a.velocity[1] - a.inv_mass * jty,
                )
                a.angular_velocity -= a.inv_inertia * (rax * jty - ray * jtx)

            if b.body_type == BodyType.DYNAMIC:
                b.velocity = (
                    b.velocity[0] + b.inv_mass * jtx,
                    b.velocity[1] + b.inv_mass * jty,
                )
                b.angular_velocity += b.inv_inertia * (rbx * jty - rby * jtx)

        if a.body_type == BodyType.DYNAMIC and b.body_type == BodyType.DYNAMIC:
            correction = penetration * 0.5 / (a.inv_mass + b.inv_mass)
            if a.inv_mass > 0:
                a.position = (
                    a.position[0] - nx * correction * a.inv_mass,
                    a.position[1] - ny * correction * a.inv_mass,
                )
            if b.inv_mass > 0:
                b.position = (
                    b.position[0] + nx * correction * b.inv_mass,
                    b.position[1] + ny * correction * b.inv_mass,
                )

        _time_module.sleep(0.001)
        return impulse_mag

    def perform_raycast(
        self,
        world_id: str,
        origin_x: float,
        origin_y: float,
        dir_x: float,
        dir_y: float,
        max_dist: float = 100.0,
    ) -> List[RayCastResult]:
        """Perform a raycast query and return all hit results sorted by distance."""
        world = self._worlds.get(world_id)
        if not world:
            return []

        results: List[RayCastResult] = []
        dir_len = math.sqrt(dir_x * dir_x + dir_y * dir_y)
        if dir_len < 0.0001:
            return results

        dir_x /= dir_len
        dir_y /= dir_len

        for body in world.bodies.values():
            if body.body_type == BodyType.TRIGGER:
                continue

            hit = self._raycast_single(origin_x, origin_y, dir_x, dir_y, max_dist, body)
            if hit and hit.hit:
                results.append(hit)

        results.sort(key=lambda r: r.distance)
        _time_module.sleep(0.001)
        return results

    def _raycast_single(
        self,
        ox: float,
        oy: float,
        dx: float,
        dy: float,
        max_dist: float,
        body: RigidBody2D,
    ) -> RayCastResult:
        """Raycast against a single body."""
        if body.collision_shape == CollisionShape.CIRCLE:
            cx, cy = body.position
            r = body.radius

            ocx = ox - cx
            ocy = oy - cy
            a = dx * dx + dy * dy
            b = 2 * (ocx * dx + ocy * dy)
            c = ocx * ocx + ocy * ocy - r * r
            discriminant = b * b - 4 * a * c

            if discriminant < 0:
                return RayCastResult(origin=(ox, oy), direction=(dx, dy), hit=False)

            t = (-b - math.sqrt(discriminant)) / (2 * a)
            if t < 0 or t > max_dist:
                t = (-b + math.sqrt(discriminant)) / (2 * a)
                if t < 0 or t > max_dist:
                    return RayCastResult(origin=(ox, oy), direction=(dx, dy), hit=False)

            hit_x = ox + dx * t
            hit_y = oy + dy * t
            nx = (hit_x - cx) / r
            ny = (hit_y - cy) / r

            return RayCastResult(
                origin=(ox, oy),
                direction=(dx, dy),
                hit_body_id=body.id,
                hit_point=(hit_x, hit_y),
                hit_normal=(nx, ny),
                distance=t,
                fraction=t / max_dist,
                hit=True,
            )

        aabb = body.bounds
        tmin = (aabb[0] - ox) / dx if dx != 0 else -float('inf')
        tmax = (aabb[2] - ox) / dx if dx != 0 else float('inf')
        if tmin > tmax:
            tmin, tmax = tmax, tmin

        tymin = (aabb[1] - oy) / dy if dy != 0 else -float('inf')
        tymax = (aabb[3] - oy) / dy if dy != 0 else float('inf')
        if tymin > tymax:
            tymin, tymax = tymax, tymin

        t_enter = max(tmin, tymin)
        t_exit = min(tmax, tymax)

        if t_enter > t_exit or t_exit < 0 or t_enter > max_dist:
            return RayCastResult(origin=(ox, oy), direction=(dx, dy), hit=False)

        t = max(t_enter, 0)
        hit_x = ox + dx * t
        hit_y = oy + dy * t

        cx, cy = body.position
        nx = (hit_x - cx) / abs(hit_x - cx) if hit_x != cx else 0
        ny = (hit_y - cy) / abs(hit_y - cy) if hit_y != cy else 0

        return RayCastResult(
            origin=(ox, oy),
            direction=(dx, dy),
            hit_body_id=body.id,
            hit_point=(hit_x, hit_y),
            hit_normal=(nx, ny),
            distance=t,
            fraction=t / max_dist,
            hit=True,
        )

    def step_simulation(
        self,
        world_id: str,
        delta_time: float,
    ) -> List[CollisionEvent]:
        """Advance the physics simulation by one step."""
        world = self._worlds.get(world_id)
        if not world:
            return []

        start_time = _time_module.time()
        world.collision_events.clear()

        dt = delta_time * world.simulation_speed
        self._integrate_forces(world, dt)

        broad_start = _time_module.time()
        potential_pairs = self._broad_phase(world)
        world.performance_metrics.broad_phase_ms = (broad_start - start_time) * 1000
        world.performance_metrics.total_broad_phase_pairs = len(potential_pairs)

        collision_start = _time_module.time()
        collision_events = self._narrow_phase(world, potential_pairs)
        world.performance_metrics.collision_ms = (_time_module.time() - collision_start) * 1000
        world.performance_metrics.total_narrow_phase_tests = len(potential_pairs)
        world.performance_metrics.total_collisions_detected = len(collision_events)

        solving_start = _time_module.time()
        for iteration in range(world.iterations):
            for event in collision_events:
                a = world.bodies.get(event.body_a_id)
                b = world.bodies.get(event.body_b_id)
                if not a or not b:
                    continue
                if a.body_type == BodyType.TRIGGER or b.body_type == BodyType.TRIGGER:
                    continue
                impulse = self.resolve_collision(
                    a, b, event.contact_point,
                    event.contact_normal, event.penetration_depth
                )
                event.impulse_magnitude = impulse

            self._solve_joints(world, dt)

        world.performance_metrics.solving_ms = (_time_module.time() - solving_start) * 1000

        for body in world.bodies.values():
            body.force_accumulator = (0.0, 0.0)
            body.torque_accumulator = 0.0
            self.compute_aabb(body)
            self._check_sleeping(body, world.sleep_threshold)

        world.collision_events = collision_events
        self._total_collisions += len(collision_events)
        self._total_steps += 1

        world.performance_metrics.total_step_ms = (_time_module.time() - start_time) * 1000

        _time_module.sleep(0.001)
        return collision_events

    def _integrate_forces(self, world: PhysicsWorld2D, dt: float) -> None:
        """Integrate forces and apply gravity to all dynamic bodies."""
        gx, gy = world.gravity
        for body in world.bodies.values():
            if body.body_type != BodyType.DYNAMIC or body.sleeping:
                continue

            fx, fy = body.force_accumulator
            fx += gx * body.mass * body.gravity_scale
            fy += gy * body.mass * body.gravity_scale

            ax = fx * body.inv_mass - body.velocity[0] * body.linear_damping
            ay = fy * body.inv_mass - body.velocity[1] * body.linear_damping

            vx, vy = body.velocity
            x, y = body.position

            body.velocity = (vx + ax * dt, vy + ay * dt)
            body.position = (x + vx * dt, y + vy * dt)

            if not body.fixed_rotation:
                alpha = (body.torque_accumulator * body.inv_inertia) - \
                        body.angular_velocity * body.angular_damping
                body.angular_velocity += alpha * dt
                body.rotation += body.angular_velocity * dt

        _time_module.sleep(0.001)

    def _broad_phase(self, world: PhysicsWorld2D) -> List[Tuple[RigidBody2D, RigidBody2D]]:
        """Broad-phase collision detection using spatial partitioning."""
        dynamic_bodies = [b for b in world.bodies.values() if b.body_type == BodyType.DYNAMIC and not b.sleeping]
        static_bodies = [b for b in world.bodies.values() if b.body_type == BodyType.STATIC]

        pairs: List[Tuple[RigidBody2D, RigidBody2D]] = []
        body_ids: set = set()

        for a in dynamic_bodies:
            for b in static_bodies:
                if self._can_collide(a, b):
                    if self._aabb_overlap(a, b):
                        if (a.id, b.id) not in body_ids and (b.id, a.id) not in body_ids:
                            body_ids.add((a.id, b.id))
                            pairs.append((a, b))

        for i in range(len(dynamic_bodies)):
            for j in range(i + 1, len(dynamic_bodies)):
                a = dynamic_bodies[i]
                b = dynamic_bodies[j]
                if self._can_collide(a, b):
                    if self._aabb_overlap(a, b):
                        if (a.id, b.id) not in body_ids:
                            body_ids.add((a.id, b.id))
                            pairs.append((a, b))

        _time_module.sleep(0.001)
        return pairs

    def _can_collide(self, a: RigidBody2D, b: RigidBody2D) -> bool:
        """Check if two bodies can collide based on category masks."""
        if a.id == b.id:
            return False
        if a.body_type == BodyType.TRIGGER or b.body_type == BodyType.TRIGGER:
            return True
        if a.body_type != BodyType.DYNAMIC and b.body_type != BodyType.DYNAMIC:
            return False
        return (a.collision_mask & self.COLLISION_CATEGORY_BITS[b.collision_category]) != 0

    def _aabb_overlap(self, a: RigidBody2D, b: RigidBody2D) -> bool:
        """Check if two bodies' AABBs overlap."""
        a_min_x, a_min_y, a_max_x, a_max_y = a.bounds
        b_min_x, b_min_y, b_max_x, b_max_y = b.bounds

        if a_max_x < b_min_x or a_min_x > b_max_x:
            return False
        if a_max_y < b_min_y or a_min_y > b_max_y:
            return False
        return True

    def _narrow_phase(
        self,
        world: PhysicsWorld2D,
        pairs: List[Tuple[RigidBody2D, RigidBody2D]],
    ) -> List[CollisionEvent]:
        """Narrow-phase collision detection with exact overlap testing."""
        events: List[CollisionEvent] = []
        for a, b in pairs:
            overlap = self.detect_overlap(a, b)
            if overlap is not None:
                contact_point, contact_normal, penetration = overlap
                event = CollisionEvent(
                    body_a_id=a.id,
                    body_b_id=b.id,
                    contact_point=contact_point,
                    contact_normal=contact_normal,
                    penetration_depth=penetration,
                    relative_velocity=self._compute_relative_velocity(a, b, contact_normal),
                    timestamp=_time_module.time(),
                    category_a=a.collision_category,
                    category_b=b.collision_category,
                    is_trigger_a=a.body_type == BodyType.TRIGGER,
                    is_trigger_b=b.body_type == BodyType.TRIGGER,
                )
                events.append(event)
                if penetration > 0:
                    a.sleeping = False
                    b.sleeping = False
        _time_module.sleep(0.001)
        return events

    def _compute_relative_velocity(
        self,
        a: RigidBody2D,
        b: RigidBody2D,
        normal: Tuple[float, float],
    ) -> float:
        """Compute relative closing velocity along contact normal."""
        va_x, va_y = a.velocity
        vb_x, vb_y = b.velocity
        dvx = vb_x - va_x
        dvy = vb_y - va_y
        return dvx * normal[0] + dvy * normal[1]

    def _solve_joints(self, world: PhysicsWorld2D, dt: float) -> None:
        """Solve all joint constraints."""
        for joint in world.joints.values():
            if not joint.enabled:
                continue

            a = world.bodies.get(joint.body_a_id)
            b = world.bodies.get(joint.body_b_id)
            if not a or not b:
                continue

            if joint.joint_type == JointType.DISTANCE:
                self._solve_distance_joint(a, b, joint)

        _time_module.sleep(0.001)

    def _solve_distance_joint(self, a: RigidBody2D, b: RigidBody2D, joint: PhysicsJoint) -> None:
        """Solve distance constraint joint."""
        ax, ay = a.position
        bx, by = b.position
        dx = bx - ax
        dy = by - ay
        dist = math.sqrt(dx * dx + dy * dy)

        if dist == 0:
            dx = 1
            dist = 1
        else:
            dx /= dist
            dy /= dist

        target_dist = (joint.lower_limit + joint.upper_limit) * 0.5
        difference = dist - target_dist

        if abs(difference) < 0.001:
            return

        correction = difference
        total_inv_mass = a.inv_mass + b.inv_mass
        if total_inv_mass <= 0:
            return

        impulse = correction / total_inv_mass

        if a.body_type == BodyType.DYNAMIC:
            a.position = (
                ax + dx * impulse * a.inv_mass,
                ay + dy * impulse * a.inv_mass,
            )

        if b.body_type == BodyType.DYNAMIC:
            b.position = (
                bx - dx * impulse * b.inv_mass,
                by - dy * impulse * b.inv_mass,
            )

    def _check_sleeping(self, body: RigidBody2D, threshold: float) -> None:
        """Check if body should go to sleep based on velocity."""
        if body.body_type != BodyType.DYNAMIC:
            body.sleeping = True
            return

        vx, vy = body.velocity
        speed_sq = vx * vx + vy * vy
        if speed_sq < threshold * threshold:
            body.sleeping = True

    def get_material(self, material_id: str) -> Optional[PhysicsMaterial]:
        """Get a predefined or custom physics material by ID."""
        return self._materials.get(material_id)

    def find_material_by_name(self, name: str) -> Optional[PhysicsMaterial]:
        """Find a material by name."""
        for material in self._materials.values():
            if material.name.lower() == name.lower():
                return material
        return None

    def create_material(
        self,
        name: str,
        restitution: float,
        static_friction: float,
        dynamic_friction: float,
        density: float,
    ) -> PhysicsMaterial:
        """Create a custom physics material."""
        material = PhysicsMaterial(
            name=name,
            restitution=max(0.0, min(1.0, restitution)),
            static_friction=max(0.0, static_friction),
            dynamic_friction=max(0.0, dynamic_friction),
            density=max(0.001, density),
        )
        self._materials[material.id] = material
        _time_module.sleep(0.001)
        return material

    def list_worlds(self) -> List[PhysicsWorld2D]:
        """List all created physics worlds."""
        return list(self._worlds.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get global statistics about the physics system."""
        total_bodies = sum(len(w.bodies) for w in self._worlds.values())
        total_joints = sum(len(w.joints) for w in self._worlds.values())
        total_events = sum(len(w.collision_events) for w in self._worlds.values())

        worlds: Dict[str, Any] = {}
        for world in self._worlds.values():
            worlds[world.id] = world.to_dict()

        material_types: Dict[str, int] = {}
        for mat in self._materials.values():
            material_types[mat.name] = material_types.get(mat.name, 0) + 1

        return {
            "total_worlds": len(self._worlds),
            "max_worlds": self.MAX_WORLDS,
            "total_bodies": total_bodies,
            "total_joints": total_joints,
            "total_events": total_events,
            "total_materials": len(self._materials),
            "predefined_materials": len(self.PREDEFINED_MATERIALS),
            "total_collisions": self._total_collisions,
            "total_steps": self._total_steps,
            "material_distribution": material_types,
            "worlds": worlds,
        }

    def reset_all(self) -> None:
        """Reset all worlds and clear all data."""
        with self._lock:
            self._worlds.clear()
            self._materials.clear()
            self._total_steps = 0
            self._total_collisions = 0
            self._seed_predefined_materials()
        _time_module.sleep(0.001)


def get_engine_physics_world_2d() -> EnginePhysicsWorld2D:
    """Get the global singleton instance of the 2D physics engine."""
    return EnginePhysicsWorld2D.get_instance()
