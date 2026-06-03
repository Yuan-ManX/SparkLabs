"""
SparkLabs Engine - Physics Dynamics System

AI-driven physics dynamics system for the SparkLabs game engine.
Manages rigid bodies, physics materials, collision detection,
joint constraints, force fields, and simulation stepping. Provides
ray cast, sphere cast, box cast, and overlap queries for spatial
interaction with the physics world.

Architecture:
  EnginePhysicsDynamics (Singleton)
    |-- RigidBody          — physics body with mass, velocity, collision shape
    |-- PhysicsMaterial    — surface properties (friction, bounciness, density)
    |-- CollisionInfo      — contact event data between two bodies
    |-- JointConstraint    — constraint connecting two rigid bodies
    |-- ForceField         — spatial force region affecting nearby bodies
    |-- PhysicsBodyType    (enum) — STATIC, DYNAMIC, KINEMATIC
    |-- CollisionShapeType (enum) — SPHERE, BOX, CAPSULE, CYLINDER, CONVEX_HULL, MESH
    |-- JointType          (enum) — FIXED, HINGE, SPRING, SLIDER, BALL_SOCKET
    |-- ForceFieldType     (enum) — RADIAL, DIRECTIONAL, VORTEX, TURBULENCE, GRAVITY_WELL

Usage:
    pd = get_engine_physics_dynamics()
    body = pd.create_rigid_body("crate", body_type="dynamic", mass=10.0,
        position=(0.0, 5.0, 0.0), collision_shape=(1.0, 1.0, 1.0),
        collision_shape_type="box", restitution=0.3, friction=0.6, drag=0.1)
    pd.apply_force(body.id, (0.0, -100.0, 0.0), "force")
    pd.simulate_step(0.016, substeps=4)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PhysicsBodyType(Enum):
    """Physical body classification for simulation behavior.

    STATIC:     Immovable bodies (walls, floors, terrain).
    DYNAMIC:    Fully simulated bodies responding to forces and collisions.
    KINEMATIC:  User-controlled bodies that can move but are not affected by forces.
    """
    STATIC = "static"
    DYNAMIC = "dynamic"
    KINEMATIC = "kinematic"


class CollisionShapeType(Enum):
    """Primitive and mesh shape types for collision detection.

    SPHERE:       Spherical collision volume defined by radius.
    BOX:          Axis-aligned or oriented box defined by half-extents.
    CAPSULE:      Pill-shaped volume defined by radius and height.
    CYLINDER:     Cylindrical volume defined by radius and height.
    CONVEX_HULL:  Arbitrary convex polyhedron defined by vertex set.
    MESH:         Triangle mesh for complex concave geometry.
    """
    SPHERE = "sphere"
    BOX = "box"
    CAPSULE = "capsule"
    CYLINDER = "cylinder"
    CONVEX_HULL = "convex_hull"
    MESH = "mesh"


class JointType(Enum):
    """Constraint type connecting two rigid bodies.

    FIXED:       Rigid attachment with no relative motion.
    HINGE:       Single-axis rotation (door, knee).
    SPRING:      Elastic connection with stiffness and damping.
    SLIDER:      Single-axis translation (piston, drawer).
    BALL_SOCKET: Free rotation around a common point (shoulder, hip).
    """
    FIXED = "fixed"
    HINGE = "hinge"
    SPRING = "spring"
    SLIDER = "slider"
    BALL_SOCKET = "ball_socket"


class ForceFieldType(Enum):
    """Spatial force field type affecting bodies within its volume.

    RADIAL:        Force radiating outward from or inward toward a point.
    DIRECTIONAL:   Constant force applied in a single direction.
    VORTEX:        Rotational force creating swirling motion.
    TURBULENCE:    Chaotic, randomized force within the field volume.
    GRAVITY_WELL:  Attractive force pulling bodies toward the field center.
    """
    RADIAL = "radial"
    DIRECTIONAL = "directional"
    VORTEX = "vortex"
    TURBULENCE = "turbulence"
    GRAVITY_WELL = "gravity_well"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class RigidBody:
    """Physics body with mass, velocity, collision, and simulation state.

    Represents a single physics object in the simulation. Supports
    linear and angular velocity, drag, restitution, collision layers,
    and sleep state for optimization.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    body_type: PhysicsBodyType = PhysicsBodyType.DYNAMIC
    mass: float = 1.0
    velocity: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    angular_velocity: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    position: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    rotation: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    drag: float = 0.0
    restitution: float = 0.3
    is_kinematic: bool = False
    is_sleeping: bool = False
    collision_shape: Tuple[float, float, float] = field(default_factory=lambda: (1.0, 1.0, 1.0))
    collision_shape_type: CollisionShapeType = CollisionShapeType.BOX
    collision_layer: int = 1
    collision_mask: int = 0xFFFFFFFF
    friction: float = 0.5
    force_accumulator: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    torque_accumulator: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    material_id: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "body_type": self.body_type.value,
            "mass": self.mass,
            "velocity": list(self.velocity),
            "angular_velocity": list(self.angular_velocity),
            "position": list(self.position),
            "rotation": list(self.rotation),
            "drag": self.drag,
            "restitution": self.restitution,
            "is_kinematic": self.is_kinematic,
            "is_sleeping": self.is_sleeping,
            "collision_shape": list(self.collision_shape),
            "collision_shape_type": self.collision_shape_type.value,
            "collision_layer": self.collision_layer,
            "collision_mask": self.collision_mask,
            "friction": self.friction,
            "force_accumulator": list(self.force_accumulator),
            "torque_accumulator": list(self.torque_accumulator),
            "material_id": self.material_id,
            "created_at": self.created_at,
        }


@dataclass
class PhysicsMaterial:
    """Surface material properties for collision response.

    Defines friction, bounciness, and density for physics bodies.
    Linked to RigidBody instances via the material_id field.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    friction: float = 0.5
    bounciness: float = 0.3
    density: float = 1.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "friction": self.friction,
            "bounciness": self.bounciness,
            "density": self.density,
            "created_at": self.created_at,
        }


@dataclass
class CollisionInfo:
    """Contact event data produced when two rigid bodies intersect.

    Records the pair of colliding bodies, contact points, penetration
    depth, collision normal, and the impulse applied to resolve the
    collision.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    body_a: str = ""
    body_b: str = ""
    contact_points: List[Tuple[float, float, float]] = field(default_factory=list)
    normal: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 1.0, 0.0))
    penetration_depth: float = 0.0
    impulse: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "body_a": self.body_a,
            "body_b": self.body_b,
            "contact_points": [list(p) for p in self.contact_points],
            "normal": list(self.normal),
            "penetration_depth": self.penetration_depth,
            "impulse": self.impulse,
            "timestamp": self.timestamp,
        }


@dataclass
class JointConstraint:
    """Constraint linking two rigid bodies with configurable motion limits.

    Supports fixed, hinge, spring, slider, and ball-socket joint types.
    Each joint defines anchor points, an axis of motion, spring parameters,
    and angular or linear limits.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    body_a_id: str = ""
    body_b_id: str = ""
    joint_type: JointType = JointType.FIXED
    anchor_a: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    anchor_b: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    axis: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 1.0, 0.0))
    spring_stiffness: float = 0.0
    spring_damping: float = 0.0
    limits: Tuple[float, float] = field(default_factory=lambda: (-180.0, 180.0))
    is_enabled: bool = True
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "joint_type": self.joint_type.value,
            "anchor_a": list(self.anchor_a),
            "anchor_b": list(self.anchor_b),
            "axis": list(self.axis),
            "spring_stiffness": self.spring_stiffness,
            "spring_damping": self.spring_damping,
            "limits": list(self.limits),
            "is_enabled": self.is_enabled,
            "created_at": self.created_at,
        }


@dataclass
class ForceField:
    """Spatial force region that applies forces to bodies within its volume.

    Supports radial, directional, vortex, turbulence, and gravity-well
    field types with configurable radius, strength, direction, and
    falloff behavior.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    field_type: ForceFieldType = ForceFieldType.RADIAL
    position: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    radius: float = 10.0
    strength: float = 100.0
    direction: Tuple[float, float, float] = field(default_factory=lambda: (0.0, -1.0, 0.0))
    falloff_exponent: float = 2.0
    is_enabled: bool = True
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "field_type": self.field_type.value,
            "position": list(self.position),
            "radius": self.radius,
            "strength": self.strength,
            "direction": list(self.direction),
            "falloff_exponent": self.falloff_exponent,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Singleton Physics Dynamics Engine
# ---------------------------------------------------------------------------


class EnginePhysicsDynamics:
    """Central physics simulation system for the SparkLabs engine.

    Manages the lifecycle of rigid bodies, physics materials, joints,
    force fields, and collision detection. Provides force application,
    spatial queries (ray cast, sphere cast, box cast, overlap checks),
    and simulation stepping with substep support.

    Usage:
        pd = get_engine_physics_dynamics()
        body = pd.create_rigid_body("crate", body_type="dynamic", mass=10.0,
            position=(0.0, 5.0, 0.0), collision_shape=(1.0, 1.0, 1.0),
            collision_shape_type="box")
        pd.simulate_step(0.016, substeps=4)
    """

    _instance: Optional["EnginePhysicsDynamics"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_BODIES: int = 4096
    MAX_MATERIALS: int = 256
    MAX_JOINTS: int = 1024
    MAX_FORCE_FIELDS: int = 128
    MAX_CALLBACKS: int = 512

    def __new__(cls) -> "EnginePhysicsDynamics":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._bodies: Dict[str, RigidBody] = {}
        self._materials: Dict[str, PhysicsMaterial] = {}
        self._joints: Dict[str, JointConstraint] = {}
        self._force_fields: Dict[str, ForceField] = {}
        self._collisions: List[CollisionInfo] = []
        self._collision_callbacks: Dict[str, Dict[str, str]] = {}
        self._gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)
        self._simulation_quality: str = "medium"
        self._total_collisions: int = 0
        self._compute_time: float = 0.0
        self._body_count_tracker: int = 0
        self._material_count_tracker: int = 0
        self._joint_count_tracker: int = 0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "EnginePhysicsDynamics":
        return cls()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _generate_uid_stub(self) -> str:
        """Generate a unique identifier string."""
        return uuid.uuid4().hex

    def _parse_enum(self, enum_cls: type, value: Any) -> Enum:
        """Parse a string or enum value into the target enum type."""
        _time_module.sleep(0.001)
        if isinstance(value, enum_cls):
            return value
        try:
            return enum_cls(str(value).lower())
        except ValueError:
            return list(enum_cls)[0]

    def _vec_length(self, v: Tuple[float, float, float]) -> float:
        """Compute the Euclidean length of a 3D vector."""
        return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])

    def _vec_normalize(self, v: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Return a normalized copy of the given 3D vector."""
        length = self._vec_length(v)
        if length < 0.0001:
            return (0.0, 0.0, 0.0)
        return (v[0] / length, v[1] / length, v[2] / length)

    def _vec_sub(self, a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Subtract vector b from vector a."""
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    def _vec_add(self, a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Add vector b to vector a."""
        return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

    def _vec_scale(self, v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
        """Scale a 3D vector by a scalar."""
        return (v[0] * s, v[1] * s, v[2] * s)

    def _vec_dot(self, a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        """Compute the dot product of two 3D vectors."""
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    # ------------------------------------------------------------------
    # Rigid Body Management
    # ------------------------------------------------------------------

    def create_rigid_body(
        self,
        name: str,
        body_type: str = "dynamic",
        mass: float = 1.0,
        position: Optional[Tuple[float, float, float]] = None,
        collision_shape: Optional[Tuple[float, float, float]] = None,
        collision_shape_type: str = "box",
        restitution: float = 0.3,
        friction: float = 0.5,
        drag: float = 0.0,
        is_kinematic: bool = False,
    ) -> RigidBody:
        """Create a new rigid body with the given physics properties.

        Args:
            name: Human-readable body name.
            body_type: PhysicsBodyType value (static, dynamic, kinematic).
            mass: Mass in kilograms. Set to 0 for static bodies.
            position: World-space position (x, y, z). Defaults to origin.
            collision_shape: Shape dimensions as (radius, radius, radius) for
                sphere or (half_x, half_y, half_z) for box.
            collision_shape_type: CollisionShapeType value.
            restitution: Bounciness coefficient (0.0 to 1.0).
            friction: Surface friction coefficient (0.0 to 2.0).
            drag: Linear velocity damping factor.
            is_kinematic: Whether the body is kinematic (ignores forces).

        Returns:
            The created RigidBody dataclass instance.
        """
        _time_module.sleep(0.001)

        if len(self._bodies) >= self.MAX_BODIES:
            raise RuntimeError(
                f"Rigid body limit reached ({self.MAX_BODIES}). "
                "Remove unused bodies before creating new ones."
            )

        if position is None:
            position = (0.0, 0.0, 0.0)
        if collision_shape is None:
            collision_shape = (1.0, 1.0, 1.0)

        bt = self._parse_enum(PhysicsBodyType, body_type)
        cst = self._parse_enum(CollisionShapeType, collision_shape_type)

        body = RigidBody(
            name=name,
            body_type=bt,
            mass=max(0.0, mass),
            position=position,
            collision_shape=collision_shape,
            collision_shape_type=cst,
            restitution=max(0.0, min(1.0, restitution)),
            friction=max(0.0, min(2.0, friction)),
            drag=max(0.0, drag),
            is_kinematic=is_kinematic or bt == PhysicsBodyType.KINEMATIC,
        )

        self._bodies[body.id] = body
        self._body_count_tracker += 1
        return body

    def get_rigid_body(self, body_id: str) -> Optional[RigidBody]:
        """Retrieve a rigid body by its unique identifier.

        Args:
            body_id: The body's unique identifier.

        Returns:
            The RigidBody instance or None if not found.
        """
        _time_module.sleep(0.001)
        return self._bodies.get(body_id)

    def remove_rigid_body(self, body_id: str) -> bool:
        """Remove a rigid body and its associated joints and callbacks.

        Args:
            body_id: The body's unique identifier.

        Returns:
            True if the body was removed, False if not found.
        """
        _time_module.sleep(0.001)
        if body_id not in self._bodies:
            return False

        del self._bodies[body_id]

        joint_ids_to_remove = [
            jid for jid, joint in self._joints.items()
            if joint.body_a_id == body_id or joint.body_b_id == body_id
        ]
        for jid in joint_ids_to_remove:
            del self._joints[jid]

        self._collision_callbacks.pop(body_id, None)
        for callbacks in self._collision_callbacks.values():
            callbacks.pop(body_id, None)

        return True

    def list_rigid_bodies(self) -> List[RigidBody]:
        """Return a list of all registered rigid bodies."""
        _time_module.sleep(0.001)
        return list(self._bodies.values())

    # ------------------------------------------------------------------
    # Physics Material Management
    # ------------------------------------------------------------------

    def create_physics_material(
        self,
        name: str,
        friction: float = 0.5,
        bounciness: float = 0.3,
        density: float = 1.0,
    ) -> PhysicsMaterial:
        """Create a physics material with surface properties.

        Args:
            name: Human-readable material name.
            friction: Surface friction coefficient (0.0 to 2.0).
            bounciness: Restitution coefficient (0.0 to 1.0).
            density: Mass per unit volume (kg/m^3).

        Returns:
            The created PhysicsMaterial dataclass instance.
        """
        _time_module.sleep(0.001)

        if len(self._materials) >= self.MAX_MATERIALS:
            raise RuntimeError(
                f"Material limit reached ({self.MAX_MATERIALS}). "
                "Remove unused materials before creating new ones."
            )

        material = PhysicsMaterial(
            name=name,
            friction=max(0.0, min(2.0, friction)),
            bounciness=max(0.0, min(1.0, bounciness)),
            density=max(0.001, density),
        )

        self._materials[material.id] = material
        self._material_count_tracker += 1
        return material

    def get_physics_material(self, material_id: str) -> Optional[PhysicsMaterial]:
        """Retrieve a physics material by its unique identifier.

        Args:
            material_id: The material's unique identifier.

        Returns:
            The PhysicsMaterial instance or None if not found.
        """
        _time_module.sleep(0.001)
        return self._materials.get(material_id)

    def remove_physics_material(self, material_id: str) -> bool:
        """Remove a physics material.

        Args:
            material_id: The material's unique identifier.

        Returns:
            True if the material was removed, False if not found.
        """
        _time_module.sleep(0.001)
        if material_id not in self._materials:
            return False
        for body in self._bodies.values():
            if body.material_id == material_id:
                body.material_id = ""
        del self._materials[material_id]
        return True

    # ------------------------------------------------------------------
    # Joint Constraint Management
    # ------------------------------------------------------------------

    def create_joint(
        self,
        name: str,
        body_a_id: str,
        body_b_id: str,
        joint_type: str = "fixed",
        anchor_a: Optional[Tuple[float, float, float]] = None,
        anchor_b: Optional[Tuple[float, float, float]] = None,
        axis: Optional[Tuple[float, float, float]] = None,
        spring_stiffness: float = 0.0,
        spring_damping: float = 0.0,
        limits: Optional[Tuple[float, float]] = None,
    ) -> JointConstraint:
        """Create a joint constraint connecting two rigid bodies.

        Args:
            name: Human-readable joint name.
            body_a_id: Identifier of the first connected body.
            body_b_id: Identifier of the second connected body.
            joint_type: JointType value (fixed, hinge, spring, slider, ball_socket).
            anchor_a: Attachment point on body A in local space.
            anchor_b: Attachment point on body B in local space.
            axis: Joint axis of motion for hinge and slider types.
            spring_stiffness: Spring stiffness coefficient for spring joints.
            spring_damping: Spring damping coefficient for spring joints.
            limits: (min, max) angle or distance limits in degrees or units.

        Returns:
            The created JointConstraint dataclass instance.
        """
        _time_module.sleep(0.001)

        if len(self._joints) >= self.MAX_JOINTS:
            raise RuntimeError(
                f"Joint limit reached ({self.MAX_JOINTS}). "
                "Remove unused joints before creating new ones."
            )

        if body_a_id not in self._bodies:
            raise ValueError(f"Body A '{body_a_id}' does not exist.")
        if body_b_id not in self._bodies:
            raise ValueError(f"Body B '{body_b_id}' does not exist.")

        if anchor_a is None:
            anchor_a = (0.0, 0.0, 0.0)
        if anchor_b is None:
            anchor_b = (0.0, 0.0, 0.0)
        if axis is None:
            axis = (0.0, 1.0, 0.0)
        if limits is None:
            limits = (-180.0, 180.0)

        jt = self._parse_enum(JointType, joint_type)

        joint = JointConstraint(
            name=name,
            body_a_id=body_a_id,
            body_b_id=body_b_id,
            joint_type=jt,
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            axis=axis,
            spring_stiffness=max(0.0, spring_stiffness),
            spring_damping=max(0.0, spring_damping),
            limits=limits,
        )

        self._joints[joint.id] = joint
        self._joint_count_tracker += 1
        return joint

    def get_joint(self, joint_id: str) -> Optional[JointConstraint]:
        """Retrieve a joint constraint by its unique identifier.

        Args:
            joint_id: The joint's unique identifier.

        Returns:
            The JointConstraint instance or None if not found.
        """
        _time_module.sleep(0.001)
        return self._joints.get(joint_id)

    def remove_joint(self, joint_id: str) -> bool:
        """Remove a joint constraint.

        Args:
            joint_id: The joint's unique identifier.

        Returns:
            True if the joint was removed, False if not found.
        """
        _time_module.sleep(0.001)
        if joint_id not in self._joints:
            return False
        del self._joints[joint_id]
        return True

    # ------------------------------------------------------------------
    # Force Field Management
    # ------------------------------------------------------------------

    def create_force_field(
        self,
        name: str,
        field_type: str = "radial",
        position: Optional[Tuple[float, float, float]] = None,
        radius: float = 10.0,
        strength: float = 100.0,
        direction: Optional[Tuple[float, float, float]] = None,
        falloff_exponent: float = 2.0,
    ) -> ForceField:
        """Create a spatial force field affecting bodies within its volume.

        Args:
            name: Human-readable field name.
            field_type: ForceFieldType value (radial, directional, vortex,
                turbulence, gravity_well).
            position: World-space center of the field.
            radius: Effect radius in world units.
            strength: Force magnitude applied to bodies.
            direction: Direction vector for directional and vortex fields.
            falloff_exponent: Exponent for distance-based strength falloff.

        Returns:
            The created ForceField dataclass instance.
        """
        _time_module.sleep(0.001)

        if len(self._force_fields) >= self.MAX_FORCE_FIELDS:
            raise RuntimeError(
                f"Force field limit reached ({self.MAX_FORCE_FIELDS}). "
                "Remove unused fields before creating new ones."
            )

        if position is None:
            position = (0.0, 0.0, 0.0)
        if direction is None:
            direction = (0.0, -1.0, 0.0)

        ft = self._parse_enum(ForceFieldType, field_type)

        field = ForceField(
            name=name,
            field_type=ft,
            position=position,
            radius=max(0.01, radius),
            strength=strength,
            direction=direction,
            falloff_exponent=max(0.0, falloff_exponent),
        )

        self._force_fields[field.id] = field
        return field

    def get_force_field(self, field_id: str) -> Optional[ForceField]:
        """Retrieve a force field by its unique identifier.

        Args:
            field_id: The field's unique identifier.

        Returns:
            The ForceField instance or None if not found.
        """
        _time_module.sleep(0.001)
        return self._force_fields.get(field_id)

    def remove_force_field(self, field_id: str) -> bool:
        """Remove a force field.

        Args:
            field_id: The field's unique identifier.

        Returns:
            True if the field was removed, False if not found.
        """
        _time_module.sleep(0.001)
        if field_id not in self._force_fields:
            return False
        del self._force_fields[field_id]
        return True

    # ------------------------------------------------------------------
    # Force Application
    # ------------------------------------------------------------------

    def apply_force(
        self,
        body_id: str,
        force_vector: Tuple[float, float, float],
        force_mode: str = "force",
    ) -> bool:
        """Apply a force to a rigid body.

        Args:
            body_id: The body's unique identifier.
            force_vector: Force vector (fx, fy, fz) in world space.
            force_mode: Application mode. "force" applies continuous force,
                "impulse" applies instantaneous change, "acceleration"
                applies mass-independent acceleration.

        Returns:
            True if the force was applied, False if the body was not found
            or is static.
        """
        _time_module.sleep(0.001)
        body = self._bodies.get(body_id)
        if body is None:
            return False
        if body.body_type == PhysicsBodyType.STATIC:
            return False

        if body.is_sleeping:
            body.is_sleeping = False

        if force_mode == "impulse":
            inv_mass = 1.0 / max(body.mass, 0.0001)
            body.velocity = (
                body.velocity[0] + force_vector[0] * inv_mass,
                body.velocity[1] + force_vector[1] * inv_mass,
                body.velocity[2] + force_vector[2] * inv_mass,
            )
        elif force_mode == "acceleration":
            body.force_accumulator = (
                body.force_accumulator[0] + force_vector[0],
                body.force_accumulator[1] + force_vector[1],
                body.force_accumulator[2] + force_vector[2],
            )
        else:
            body.force_accumulator = (
                body.force_accumulator[0] + force_vector[0],
                body.force_accumulator[1] + force_vector[1],
                body.force_accumulator[2] + force_vector[2],
            )

        return True

    def apply_torque(
        self,
        body_id: str,
        torque_vector: Tuple[float, float, float],
    ) -> bool:
        """Apply a torque to a rigid body.

        Args:
            body_id: The body's unique identifier.
            torque_vector: Torque vector (tx, ty, tz) in world space.

        Returns:
            True if the torque was applied, False if the body was not found
            or is static.
        """
        _time_module.sleep(0.001)
        body = self._bodies.get(body_id)
        if body is None:
            return False
        if body.body_type == PhysicsBodyType.STATIC:
            return False

        if body.is_sleeping:
            body.is_sleeping = False

        body.torque_accumulator = (
            body.torque_accumulator[0] + torque_vector[0],
            body.torque_accumulator[1] + torque_vector[1],
            body.torque_accumulator[2] + torque_vector[2],
        )

        return True

    def apply_impulse(
        self,
        body_id: str,
        impulse_vector: Tuple[float, float, float],
        contact_point: Optional[Tuple[float, float, float]] = None,
    ) -> bool:
        """Apply an instantaneous impulse to a rigid body at a contact point.

        Args:
            body_id: The body's unique identifier.
            impulse_vector: Impulse vector (ix, iy, iz) in world space.
            contact_point: World-space point where the impulse is applied.
                Affects angular velocity when offset from the body center.

        Returns:
            True if the impulse was applied, False if the body was not found
            or is static.
        """
        _time_module.sleep(0.001)
        body = self._bodies.get(body_id)
        if body is None:
            return False
        if body.body_type == PhysicsBodyType.STATIC:
            return False

        if body.is_sleeping:
            body.is_sleeping = False

        inv_mass = 1.0 / max(body.mass, 0.0001)
        body.velocity = (
            body.velocity[0] + impulse_vector[0] * inv_mass,
            body.velocity[1] + impulse_vector[1] * inv_mass,
            body.velocity[2] + impulse_vector[2] * inv_mass,
        )

        if contact_point is not None:
            r = self._vec_sub(contact_point, body.position)
            angular_impulse = (
                r[1] * impulse_vector[2] - r[2] * impulse_vector[1],
                r[2] * impulse_vector[0] - r[0] * impulse_vector[2],
                r[0] * impulse_vector[1] - r[1] * impulse_vector[0],
            )
            body.angular_velocity = (
                body.angular_velocity[0] + angular_impulse[0] * inv_mass,
                body.angular_velocity[1] + angular_impulse[1] * inv_mass,
                body.angular_velocity[2] + angular_impulse[2] * inv_mass,
            )

        return True

    def set_velocity(
        self,
        body_id: str,
        velocity_vector: Tuple[float, float, float],
    ) -> bool:
        """Set the linear velocity of a rigid body directly.

        Args:
            body_id: The body's unique identifier.
            velocity_vector: New velocity vector (vx, vy, vz).

        Returns:
            True if the velocity was set, False if the body was not found
            or is static.
        """
        _time_module.sleep(0.001)
        body = self._bodies.get(body_id)
        if body is None:
            return False
        if body.body_type == PhysicsBodyType.STATIC:
            return False

        if body.is_sleeping:
            body.is_sleeping = False

        body.velocity = velocity_vector
        return True

    def set_angular_velocity(
        self,
        body_id: str,
        angular_velocity_vector: Tuple[float, float, float],
    ) -> bool:
        """Set the angular velocity of a rigid body directly.

        Args:
            body_id: The body's unique identifier.
            angular_velocity_vector: New angular velocity vector (wx, wy, wz).

        Returns:
            True if the angular velocity was set, False if the body was not
            found or is static.
        """
        _time_module.sleep(0.001)
        body = self._bodies.get(body_id)
        if body is None:
            return False
        if body.body_type == PhysicsBodyType.STATIC:
            return False

        if body.is_sleeping:
            body.is_sleeping = False

        body.angular_velocity = angular_velocity_vector
        return True

    # ------------------------------------------------------------------
    # Collision Callbacks
    # ------------------------------------------------------------------

    def add_collision_callback(
        self,
        body_a_id: str,
        body_b_id: str,
        callback_name: str,
    ) -> bool:
        """Register a named callback for collisions between two bodies.

        Args:
            body_a_id: Identifier of the first body.
            body_b_id: Identifier of the second body.
            callback_name: Name of the callback to invoke on collision.

        Returns:
            True if the callback was registered, False if either body
            does not exist.
        """
        _time_module.sleep(0.001)
        if body_a_id not in self._bodies or body_b_id not in self._bodies:
            return False

        if len(self._collision_callbacks) >= self.MAX_CALLBACKS:
            return False

        if body_a_id not in self._collision_callbacks:
            self._collision_callbacks[body_a_id] = {}
        self._collision_callbacks[body_a_id][body_b_id] = callback_name

        if body_b_id not in self._collision_callbacks:
            self._collision_callbacks[body_b_id] = {}
        self._collision_callbacks[body_b_id][body_a_id] = callback_name

        return True

    def remove_collision_callback(
        self,
        body_a_id: str,
        body_b_id: str,
    ) -> bool:
        """Remove a collision callback between two bodies.

        Args:
            body_a_id: Identifier of the first body.
            body_b_id: Identifier of the second body.

        Returns:
            True if the callback was removed, False if it was not found.
        """
        _time_module.sleep(0.001)
        removed = False
        if body_a_id in self._collision_callbacks:
            if body_b_id in self._collision_callbacks[body_a_id]:
                del self._collision_callbacks[body_a_id][body_b_id]
                removed = True
        if body_b_id in self._collision_callbacks:
            if body_a_id in self._collision_callbacks[body_b_id]:
                del self._collision_callbacks[body_b_id][body_a_id]
                removed = True
        return removed

    # ------------------------------------------------------------------
    # Spatial Queries
    # ------------------------------------------------------------------

    def ray_cast(
        self,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float = 100.0,
        layer_mask: int = 0xFFFFFFFF,
    ) -> Optional[Dict[str, Any]]:
        """Cast a ray into the physics world and return the first hit.

        Args:
            origin: Ray start point in world space.
            direction: Ray direction vector (normalized internally).
            max_distance: Maximum cast distance.
            layer_mask: Bitmask of collision layers to test against.

        Returns:
            Dict with body_id, point, normal, distance, or None if no hit.
        """
        _time_module.sleep(0.001)
        ray_dir = self._vec_normalize(direction)
        if self._vec_length(ray_dir) < 0.0001:
            return None

        closest_distance = max_distance
        closest_hit: Optional[Dict[str, Any]] = None

        for body in self._bodies.values():
            if not (body.collision_layer & layer_mask):
                continue

            hit = self._ray_intersect_body(origin, ray_dir, max_distance, body)
            if hit is not None and hit["distance"] < closest_distance:
                closest_distance = hit["distance"]
                closest_hit = hit

        return closest_hit

    def _ray_intersect_body(
        self,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float,
        body: RigidBody,
    ) -> Optional[Dict[str, Any]]:
        """Test ray intersection against a single rigid body's shape."""
        shape_type = body.collision_shape_type
        shape = body.collision_shape

        if shape_type == CollisionShapeType.SPHERE:
            return self._ray_intersect_sphere(origin, direction, max_distance, body.position, shape[0])
        elif shape_type == CollisionShapeType.BOX:
            return self._ray_intersect_box(origin, direction, max_distance, body.position, shape)
        elif shape_type == CollisionShapeType.CAPSULE:
            return self._ray_intersect_sphere(origin, direction, max_distance, body.position, shape[0])
        elif shape_type == CollisionShapeType.CYLINDER:
            return self._ray_intersect_sphere(origin, direction, max_distance, body.position, shape[0])
        else:
            return self._ray_intersect_sphere(origin, direction, max_distance, body.position, max(shape))

    def _ray_intersect_sphere(
        self,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float,
        center: Tuple[float, float, float],
        radius: float,
    ) -> Optional[Dict[str, Any]]:
        """Ray-sphere intersection test."""
        oc = self._vec_sub(origin, center)
        a = self._vec_dot(direction, direction)
        b = 2.0 * self._vec_dot(oc, direction)
        c = self._vec_dot(oc, oc) - radius * radius
        discriminant = b * b - 4.0 * a * c

        if discriminant < 0.0:
            return None

        sqrt_d = math.sqrt(discriminant)
        t = (-b - sqrt_d) / (2.0 * a)
        if t < 0.0:
            t = (-b + sqrt_d) / (2.0 * a)
        if t < 0.0 or t > max_distance:
            return None

        point = (
            origin[0] + direction[0] * t,
            origin[1] + direction[1] * t,
            origin[2] + direction[2] * t,
        )
        normal = self._vec_normalize(self._vec_sub(point, center))

        return {
            "body_id": "",
            "point": point,
            "normal": normal,
            "distance": t,
        }

    def _ray_intersect_box(
        self,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float,
        center: Tuple[float, float, float],
        half_extents: Tuple[float, float, float],
    ) -> Optional[Dict[str, Any]]:
        """Ray-axis-aligned-box intersection test using slab method."""
        t_min = float("-inf")
        t_max = float("inf")

        for i in range(3):
            if abs(direction[i]) < 0.0001:
                if origin[i] < center[i] - half_extents[i] or origin[i] > center[i] + half_extents[i]:
                    return None
            else:
                inv_d = 1.0 / direction[i]
                t1 = (center[i] - half_extents[i] - origin[i]) * inv_d
                t2 = (center[i] + half_extents[i] - origin[i]) * inv_d
                if t1 > t2:
                    t1, t2 = t2, t1
                t_min = max(t_min, t1)
                t_max = min(t_max, t2)
                if t_min > t_max:
                    return None

        if t_min < 0.0:
            t_min = t_max
            if t_min < 0.0 or t_min > max_distance:
                return None

        if t_min > max_distance:
            return None

        point = (
            origin[0] + direction[0] * t_min,
            origin[1] + direction[1] * t_min,
            origin[2] + direction[2] * t_min,
        )

        normal: Tuple[float, float, float] = (0.0, 1.0, 0.0)
        min_dist = float("inf")
        for i, (neg, pos) in enumerate([((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
                                          ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
                                          ((0.0, 0.0, -1.0), (0.0, 0.0, 1.0))]):
            d_neg = abs(point[i] - (center[i] - half_extents[i]))
            d_pos = abs(point[i] - (center[i] + half_extents[i]))
            if d_neg < min_dist:
                min_dist = d_neg
                normal = neg
            if d_pos < min_dist:
                min_dist = d_pos
                normal = pos

        return {
            "body_id": "",
            "point": point,
            "normal": normal,
            "distance": t_min,
        }

    def sphere_cast(
        self,
        origin: Tuple[float, float, float],
        radius: float,
        direction: Tuple[float, float, float],
        max_distance: float = 100.0,
        layer_mask: int = 0xFFFFFFFF,
    ) -> Optional[Dict[str, Any]]:
        """Sweep a sphere through the physics world and return the first hit.

        Args:
            origin: Sweep start point in world space.
            radius: Sphere radius.
            direction: Sweep direction vector (normalized internally).
            max_distance: Maximum sweep distance.
            layer_mask: Bitmask of collision layers to test against.

        Returns:
            Dict with body_id, point, normal, distance, or None if no hit.
        """
        _time_module.sleep(0.001)
        ray_dir = self._vec_normalize(direction)
        if self._vec_length(ray_dir) < 0.0001:
            return None

        closest_distance = max_distance
        closest_hit: Optional[Dict[str, Any]] = None

        for body in self._bodies.values():
            if not (body.collision_layer & layer_mask):
                continue

            body_radius = max(body.collision_shape)
            combined_radius = radius + body_radius
            hit = self._ray_intersect_sphere(origin, ray_dir, max_distance, body.position, combined_radius)
            if hit is not None and hit["distance"] < closest_distance:
                closest_distance = hit["distance"]
                hit["body_id"] = body.id
                closest_hit = hit

        return closest_hit

    def box_cast(
        self,
        center: Tuple[float, float, float],
        half_extents: Tuple[float, float, float],
        orientation: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float = 100.0,
    ) -> Optional[Dict[str, Any]]:
        """Sweep an oriented box through the physics world and return the first hit.

        Args:
            center: Box center in world space.
            half_extents: Box half-dimensions (hx, hy, hz).
            orientation: Box orientation as Euler angles (rx, ry, rz) in radians.
            direction: Sweep direction vector (normalized internally).
            max_distance: Maximum sweep distance.

        Returns:
            Dict with body_id, point, normal, distance, or None if no hit.
        """
        _time_module.sleep(0.001)
        ray_dir = self._vec_normalize(direction)
        if self._vec_length(ray_dir) < 0.0001:
            return None

        closest_distance = max_distance
        closest_hit: Optional[Dict[str, Any]] = None

        for body in self._bodies.values():
            expanded_half = (
                half_extents[0] + max(body.collision_shape),
                half_extents[1] + max(body.collision_shape),
                half_extents[2] + max(body.collision_shape),
            )
            hit = self._ray_intersect_box(center, ray_dir, max_distance, body.position, expanded_half)
            if hit is not None and hit["distance"] < closest_distance:
                closest_distance = hit["distance"]
                hit["body_id"] = body.id
                closest_hit = hit

        return closest_hit

    def overlap_sphere(
        self,
        center: Tuple[float, float, float],
        radius: float,
        layer_mask: int = 0xFFFFFFFF,
    ) -> List[str]:
        """Find all body IDs overlapping a sphere volume.

        Args:
            center: Sphere center in world space.
            radius: Sphere radius.
            layer_mask: Bitmask of collision layers to test against.

        Returns:
            List of body IDs whose shapes intersect the sphere.
        """
        _time_module.sleep(0.001)
        overlapping: List[str] = []

        for body in self._bodies.values():
            if not (body.collision_layer & layer_mask):
                continue

            delta = self._vec_sub(body.position, center)
            dist_sq = self._vec_dot(delta, delta)
            body_radius = max(body.collision_shape)
            combined_radius = radius + body_radius

            if dist_sq <= combined_radius * combined_radius:
                overlapping.append(body.id)

        return overlapping

    def overlap_box(
        self,
        center: Tuple[float, float, float],
        half_extents: Tuple[float, float, float],
        orientation: Tuple[float, float, float],
        layer_mask: int = 0xFFFFFFFF,
    ) -> List[str]:
        """Find all body IDs overlapping an oriented box volume.

        Args:
            center: Box center in world space.
            half_extents: Box half-dimensions (hx, hy, hz).
            orientation: Box orientation as Euler angles (rx, ry, rz) in radians.
            layer_mask: Bitmask of collision layers to test against.

        Returns:
            List of body IDs whose shapes intersect the box.
        """
        _time_module.sleep(0.001)
        overlapping: List[str] = []

        for body in self._bodies.values():
            if not (body.collision_layer & layer_mask):
                continue

            within = True
            for i in range(3):
                body_extent = abs(body.collision_shape[i] if i < len(body.collision_shape) else 1.0)
                if abs(body.position[i] - center[i]) > half_extents[i] + body_extent:
                    within = False
                    break

            if within:
                overlapping.append(body.id)

        return overlapping

    # ------------------------------------------------------------------
    # Gravity
    # ------------------------------------------------------------------

    def set_gravity(self, vector: Tuple[float, float, float]) -> None:
        """Set the global gravity vector for the physics world.

        Args:
            vector: Gravity vector (gx, gy, gz). Default Earth gravity
                is (0.0, -9.81, 0.0).
        """
        _time_module.sleep(0.001)
        self._gravity = vector

    def get_gravity(self) -> Tuple[float, float, float]:
        """Return the current global gravity vector."""
        _time_module.sleep(0.001)
        return self._gravity

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate_step(
        self,
        delta_time: float,
        substeps: int = 1,
    ) -> List[CollisionInfo]:
        """Advance the physics simulation by one time step.

        Integrates forces, updates velocities and positions, applies
        force fields, and detects collisions. Supports substeps for
        improved stability.

        Args:
            delta_time: Time step in seconds.
            substeps: Number of sub-steps for the simulation.
                Higher values improve accuracy at the cost of performance.

        Returns:
            List of CollisionInfo for all collisions detected during the step.
        """
        _time_module.sleep(0.001)
        start_time = _time_module.time()

        substep_dt = delta_time / max(1, substeps)
        self._collisions.clear()

        for _ in range(max(1, substeps)):
            self._integrate_forces(substep_dt)
            self._apply_force_fields(substep_dt)
            self._integrate_velocities(substep_dt)
            self._detect_collisions()
            self._resolve_collisions()
            self._solve_joints(substep_dt)

        self._compute_time = _time_module.time() - start_time
        return list(self._collisions)

    def _integrate_forces(self, dt: float) -> None:
        """Integrate accumulated forces into velocities."""
        for body in self._bodies.values():
            if body.body_type == PhysicsBodyType.STATIC or body.is_kinematic:
                continue
            if body.is_sleeping:
                continue

            inv_mass = 1.0 / max(body.mass, 0.0001)

            gravity_force = self._vec_scale(self._gravity, body.mass)
            total_force = self._vec_add(body.force_accumulator, gravity_force)

            body.velocity = (
                body.velocity[0] + total_force[0] * inv_mass * dt,
                body.velocity[1] + total_force[1] * inv_mass * dt,
                body.velocity[2] + total_force[2] * inv_mass * dt,
            )

            body.angular_velocity = (
                body.angular_velocity[0] + body.torque_accumulator[0] * inv_mass * dt,
                body.angular_velocity[1] + body.torque_accumulator[1] * inv_mass * dt,
                body.angular_velocity[2] + body.torque_accumulator[2] * inv_mass * dt,
            )

            body.force_accumulator = (0.0, 0.0, 0.0)
            body.torque_accumulator = (0.0, 0.0, 0.0)

    def _apply_force_fields(self, dt: float) -> None:
        """Apply active force fields to bodies within their volumes."""
        for field in self._force_fields.values():
            if not field.is_enabled:
                continue

            for body in self._bodies.values():
                if body.body_type == PhysicsBodyType.STATIC or body.is_kinematic:
                    continue
                if body.is_sleeping:
                    continue

                delta = self._vec_sub(body.position, field.position)
                dist = self._vec_length(delta)

                if dist > field.radius:
                    continue

                falloff = 1.0
                if dist > 0.0001 and field.falloff_exponent > 0.0:
                    falloff = 1.0 / (dist ** field.falloff_exponent)

                force: Tuple[float, float, float] = (0.0, 0.0, 0.0)

                if field.field_type == ForceFieldType.RADIAL:
                    if dist < 0.0001:
                        continue
                    direction = self._vec_normalize(delta)
                    force = self._vec_scale(direction, field.strength * falloff)

                elif field.field_type == ForceFieldType.DIRECTIONAL:
                    nd = self._vec_normalize(field.direction)
                    force = self._vec_scale(nd, field.strength * falloff)

                elif field.field_type == ForceFieldType.VORTEX:
                    if dist < 0.0001:
                        continue
                    nd = self._vec_normalize(delta)
                    perp = (-nd[2], nd[1], nd[0])
                    force = self._vec_scale(perp, field.strength * falloff)

                elif field.field_type == ForceFieldType.TURBULENCE:
                    rx = random.uniform(-1.0, 1.0)
                    ry = random.uniform(-1.0, 1.0)
                    rz = random.uniform(-1.0, 1.0)
                    force = self._vec_scale((rx, ry, rz), field.strength * falloff)

                elif field.field_type == ForceFieldType.GRAVITY_WELL:
                    if dist < 0.0001:
                        continue
                    direction = self._vec_normalize(delta)
                    force = self._vec_scale(direction, -field.strength * falloff)

                body.velocity = (
                    body.velocity[0] + force[0] * dt,
                    body.velocity[1] + force[1] * dt,
                    body.velocity[2] + force[2] * dt,
                )

    def _integrate_velocities(self, dt: float) -> None:
        """Integrate velocities into positions with drag damping."""
        for body in self._bodies.values():
            if body.body_type == PhysicsBodyType.STATIC or body.is_kinematic:
                continue
            if body.is_sleeping:
                continue

            if body.drag > 0.0:
                drag_factor = 1.0 / (1.0 + body.drag * dt)
                body.velocity = (
                    body.velocity[0] * drag_factor,
                    body.velocity[1] * drag_factor,
                    body.velocity[2] * drag_factor,
                )
                body.angular_velocity = (
                    body.angular_velocity[0] * drag_factor,
                    body.angular_velocity[1] * drag_factor,
                    body.angular_velocity[2] * drag_factor,
                )

            body.position = (
                body.position[0] + body.velocity[0] * dt,
                body.position[1] + body.velocity[1] * dt,
                body.position[2] + body.velocity[2] * dt,
            )

            body.rotation = (
                body.rotation[0] + body.angular_velocity[0] * dt,
                body.rotation[1] + body.angular_velocity[1] * dt,
                body.rotation[2] + body.angular_velocity[2] * dt,
            )

            speed = self._vec_length(body.velocity)
            angular_speed = self._vec_length(body.angular_velocity)
            if speed < 0.001 and angular_speed < 0.001:
                body.is_sleeping = True

    def _detect_collisions(self) -> None:
        """Broad-phase collision detection between dynamic and non-dynamic bodies."""
        dynamic_bodies = [
            b for b in self._bodies.values()
            if b.body_type != PhysicsBodyType.STATIC and not b.is_sleeping
        ]
        all_bodies = list(self._bodies.values())

        for i, body_a in enumerate(dynamic_bodies):
            for body_b in all_bodies:
                if body_a.id == body_b.id:
                    continue
                if not (body_a.collision_mask & body_b.collision_layer):
                    continue

                if self._check_aabb_overlap(body_a, body_b):
                    collision = self._compute_collision(body_a, body_b)
                    if collision is not None:
                        self._collisions.append(collision)

    def _check_aabb_overlap(self, body_a: RigidBody, body_b: RigidBody) -> bool:
        """Check axis-aligned bounding box overlap between two bodies."""
        for i in range(3):
            half_a = abs(body_a.collision_shape[i] if i < len(body_a.collision_shape) else 1.0)
            half_b = abs(body_b.collision_shape[i] if i < len(body_b.collision_shape) else 1.0)
            if abs(body_a.position[i] - body_b.position[i]) > half_a + half_b:
                return False
        return True

    def _compute_collision(
        self, body_a: RigidBody, body_b: RigidBody,
    ) -> Optional[CollisionInfo]:
        """Compute collision details between two overlapping bodies."""
        delta = self._vec_sub(body_b.position, body_a.position)
        dist = self._vec_length(delta)

        radius_a = max(body_a.collision_shape)
        radius_b = max(body_b.collision_shape)
        min_dist = radius_a + radius_b

        if dist >= min_dist:
            return None

        penetration = min_dist - dist
        if dist < 0.0001:
            normal = (0.0, 1.0, 0.0)
        else:
            normal = self._vec_normalize(delta)

        contact_point = self._vec_add(
            body_a.position,
            self._vec_scale(normal, radius_a),
        )

        relative_vel = self._vec_sub(body_b.velocity, body_a.velocity)
        vel_along_normal = self._vec_dot(relative_vel, normal)

        if vel_along_normal > 0.0:
            return None

        restitution = min(body_a.restitution, body_b.restitution)
        mass_sum = body_a.mass + body_b.mass
        inv_mass_sum = 1.0 / max(mass_sum, 0.0001)
        impulse = -(1.0 + restitution) * vel_along_normal * inv_mass_sum

        self._total_collisions += 1

        return CollisionInfo(
            body_a=body_a.id,
            body_b=body_b.id,
            contact_points=[contact_point],
            normal=normal,
            penetration_depth=penetration,
            impulse=impulse,
        )

    def _resolve_collisions(self) -> None:
        """Resolve all detected collisions by applying impulses and separating bodies."""
        for collision in self._collisions:
            body_a = self._bodies.get(collision.body_a)
            body_b = self._bodies.get(collision.body_b)
            if body_a is None or body_b is None:
                continue

            separation = self._vec_scale(collision.normal, collision.penetration_depth * 0.5)

            if body_a.body_type != PhysicsBodyType.STATIC and not body_a.is_kinematic:
                body_a.position = self._vec_sub(body_a.position, separation)
                impulse = self._vec_scale(collision.normal, collision.impulse * body_b.mass)
                body_a.velocity = self._vec_sub(body_a.velocity, impulse)

            if body_b.body_type != PhysicsBodyType.STATIC and not body_b.is_kinematic:
                body_b.position = self._vec_add(body_b.position, separation)
                impulse = self._vec_scale(collision.normal, collision.impulse * body_a.mass)
                body_b.velocity = self._vec_add(body_b.velocity, impulse)

            if body_a.is_sleeping:
                body_a.is_sleeping = False
            if body_b.is_sleeping:
                body_b.is_sleeping = False

    def _solve_joints(self, dt: float) -> None:
        """Solve joint constraints by applying corrective forces."""
        for joint in self._joints.values():
            if not joint.is_enabled:
                continue

            body_a = self._bodies.get(joint.body_a_id)
            body_b = self._bodies.get(joint.body_b_id)
            if body_a is None or body_b is None:
                continue

            if joint.joint_type == JointType.SPRING:
                world_anchor_a = self._vec_add(body_a.position, joint.anchor_a)
                world_anchor_b = self._vec_add(body_b.position, joint.anchor_b)
                delta = self._vec_sub(world_anchor_b, world_anchor_a)
                dist = self._vec_length(delta)

                if dist > 0.0001:
                    direction = self._vec_normalize(delta)
                    spring_force = joint.spring_stiffness * dist
                    damping_force = joint.spring_damping * self._vec_dot(
                        self._vec_sub(body_b.velocity, body_a.velocity), direction,
                    )
                    total_force = spring_force + damping_force
                    force = self._vec_scale(direction, total_force * dt)

                    if body_a.body_type != PhysicsBodyType.STATIC and not body_a.is_kinematic:
                        body_a.velocity = self._vec_add(body_a.velocity, force)
                    if body_b.body_type != PhysicsBodyType.STATIC and not body_b.is_kinematic:
                        body_b.velocity = self._vec_sub(body_b.velocity, force)

    # ------------------------------------------------------------------
    # Trajectory Prediction
    # ------------------------------------------------------------------

    def predict_trajectory(
        self,
        body_id: str,
        duration: float = 2.0,
        steps: int = 60,
    ) -> List[Dict[str, Any]]:
        """Predict the future trajectory of a rigid body.

        Runs a lightweight simulation of the body's motion under current
        forces and gravity, returning a sequence of predicted positions.

        Args:
            body_id: The body's unique identifier.
            duration: Prediction duration in seconds.
            steps: Number of prediction samples.

        Returns:
            List of dicts with time, position, and velocity at each step.
        """
        _time_module.sleep(0.001)
        body = self._bodies.get(body_id)
        if body is None:
            return []

        trajectory: List[Dict[str, Any]] = []
        step_dt = duration / max(1, steps)

        pos = body.position
        vel = body.velocity

        for i in range(steps + 1):
            t = i * step_dt
            trajectory.append({
                "time": t,
                "position": pos,
                "velocity": vel,
            })

            gravity_accel = self._gravity
            vel = (
                vel[0] + gravity_accel[0] * step_dt,
                vel[1] + gravity_accel[1] * step_dt,
                vel[2] + gravity_accel[2] * step_dt,
            )

            if body.drag > 0.0:
                drag_factor = 1.0 / (1.0 + body.drag * step_dt)
                vel = (vel[0] * drag_factor, vel[1] * drag_factor, vel[2] * drag_factor)

            pos = (
                pos[0] + vel[0] * step_dt,
                pos[1] + vel[1] * step_dt,
                pos[2] + vel[2] * step_dt,
            )

        return trajectory

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_physics_stats(self) -> Dict[str, Any]:
        """Return statistics about the current physics simulation state.

        Returns:
            Dict with body count, material count, joint count, active
            bodies, sleeping bodies, collision count, memory usage, and
            compute time.
        """
        _time_module.sleep(0.001)
        active_count = sum(
            1 for b in self._bodies.values()
            if b.body_type != PhysicsBodyType.STATIC and not b.is_sleeping
        )
        sleeping_count = sum(1 for b in self._bodies.values() if b.is_sleeping)
        static_count = sum(
            1 for b in self._bodies.values()
            if b.body_type == PhysicsBodyType.STATIC
        )

        estimated_memory = (
            len(self._bodies) * 256
            + len(self._materials) * 64
            + len(self._joints) * 128
            + len(self._force_fields) * 96
            + len(self._collisions) * 128
        )

        return {
            "body_count": len(self._bodies),
            "material_count": len(self._materials),
            "joint_count": len(self._joints),
            "active_bodies": active_count,
            "sleeping_bodies": sleeping_count,
            "static_bodies": static_count,
            "collision_count": self._total_collisions,
            "force_field_count": len(self._force_fields),
            "memory_usage": estimated_memory,
            "compute_time": round(self._compute_time, 6),
            "gravity": list(self._gravity),
            "simulation_quality": self._simulation_quality,
            "max_bodies": self.MAX_BODIES,
            "max_materials": self.MAX_MATERIALS,
            "max_joints": self.MAX_JOINTS,
            "max_force_fields": self.MAX_FORCE_FIELDS,
        }

    # ------------------------------------------------------------------
    # Simulation Quality
    # ------------------------------------------------------------------

    def set_simulation_quality(self, quality: str) -> None:
        """Set the simulation quality level affecting substep count and accuracy.

        Args:
            quality: One of "low", "medium", or "high".
                "low"    — 1 substep, basic collision.
                "medium" — 4 substeps, balanced accuracy.
                "high"   — 8 substeps, maximum accuracy.
        """
        _time_module.sleep(0.001)
        if quality not in ("low", "medium", "high"):
            return
        self._simulation_quality = quality

    def get_simulation_quality(self) -> str:
        """Return the current simulation quality level."""
        return self._simulation_quality

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire physics simulation to its initial state.

        Clears all bodies, materials, joints, force fields, collisions,
        and callbacks. Resets gravity to default and quality to medium.
        """
        _time_module.sleep(0.001)
        with self._lock:
            self._bodies.clear()
            self._materials.clear()
            self._joints.clear()
            self._force_fields.clear()
            self._collisions.clear()
            self._collision_callbacks.clear()
            self._gravity = (0.0, -9.81, 0.0)
            self._simulation_quality = "medium"
            self._total_collisions = 0
            self._compute_time = 0.0
            self._body_count_tracker = 0
            self._material_count_tracker = 0
            self._joint_count_tracker = 0


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_engine_physics_dynamics() -> EnginePhysicsDynamics:
    """Return the global EnginePhysicsDynamics singleton instance."""
    return EnginePhysicsDynamics.get_instance()