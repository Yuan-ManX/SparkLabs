"""
SparkLabs Engine Physics Dynamics

2D rigidbody physics system with impulse-based dynamics, collision detection,
and constraint solving. Supports gravity, friction, and continuous collision
resolution.
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BodyType(str, Enum):
    """Type of rigidbody."""
    STATIC = "static"
    KINEMATIC = "kinematic"
    DYNAMIC = "dynamic"


class ShapeType(str, Enum):
    """Collision shape type."""
    CIRCLE = "circle"
    BOX = "box"
    POLYGON = "polygon"
    POINT = "point"


class CollisionState(str, Enum):
    """State of a collision."""
    START = "start"
    CONTINUE = "continue"
    END = "end"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Vector2:
    """2D vector for physics calculations."""
    x: float = 0.0
    y: float = 0.0

    def add(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def subtract(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def multiply(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalize(self) -> Vector2:
        len = self.length()
        if len > 0.0001:
            return self.multiply(1.0 / len)
        return Vector2(0, 0)

    def dot(self, other: Vector2) -> float:
        return self.x * other.x + self.y * other.y

    def perpendicular(self) -> Vector2:
        return Vector2(-self.y, self.x)

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_tuple(cls, t: Tuple[float, float]) -> Vector2:
        return cls(t[0], t[1])


@dataclass
class AABB:
    """Axis-aligned bounding box."""
    min: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    max: Vector2 = field(default_factory=lambda: Vector2(0, 0))

    def contains(self, point: Vector2) -> bool:
        return (
            point.x >= self.min.x and point.x <= self.max.x and
            point.y >= self.min.y and point.y <= self.max.y
        )

    def overlaps(self, other: AABB) -> bool:
        if self.max.x < other.min.x or self.min.x > other.max.x:
            return False
        if self.max.y < other.min.y or self.min.y > other.max.y:
            return False
        return True

    def expand(self, point: Vector2) -> AABB:
        self.min.x = min(self.min.x, point.x)
        self.min.y = min(self.min.y, point.y)
        self.max.x = max(self.max.x, point.x)
        self.max.y = max(self.max.y, point.y)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min": self.min.to_dict(),
            "max": self.max.to_dict(),
        }


@dataclass
class CollisionShape:
    """Collision shape definition."""
    shape_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    shape_type: ShapeType = ShapeType.CIRCLE
    offset: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    radius: float = 0.5
    width: float = 1.0
    height: float = 1.0
    vertices: List[Vector2] = field(default_factory=list)

    def compute_aabb(self, position: Vector2, rotation: float) -> AABB:
        if self.shape_type == ShapeType.CIRCLE:
            cx = position.x + self.offset.x
            cy = position.y + self.offset.y
            return AABB(
                Vector2(cx - self.radius, cy - self.radius),
                Vector2(cx + self.radius, cy + self.radius),
            )
        elif self.shape_type == ShapeType.BOX:
            hw = self.width * 0.5
            hh = self.height * 0.5
            cx = position.x + self.offset.x
            cy = position.y + self.offset.y
            return AABB(
                Vector2(cx - hw, cy - hh),
                Vector2(cx + hw, cy + hh),
            )
        return AABB()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shape_id": self.shape_id,
            "shape_type": self.shape_type.value,
            "offset": self.offset.to_dict(),
            "radius": self.radius,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class RigidBody:
    """Rigidbody definition."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    position: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    rotation: float = 0.0
    velocity: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    angular_velocity: float = 0.0
    mass: float = 1.0
    friction: float = 0.2
    restitution: float = 0.1
    body_type: BodyType = BodyType.DYNAMIC
    shape: CollisionShape = field(default_factory=CollisionShape)
    enabled: bool = True
    user_data: Dict[str, Any] = field(default_factory=dict)

    def get_inverse_mass(self) -> float:
        if self.body_type != BodyType.DYNAMIC or self.mass <= 0:
            return 0.0
        return 1.0 / self.mass

    def get_aabb(self) -> AABB:
        return self.shape.compute_aabb(self.position, self.rotation)

    def apply_force(self, force: Vector2, delta_time: float) -> None:
        if self.body_type != BodyType.DYNAMIC:
            return
        acceleration = force.multiply(1.0 / self.mass)
        self.velocity = self.velocity.add(acceleration.multiply(delta_time))

    def apply_impulse(self, impulse: Vector2, contact_point: Vector2) -> None:
        if self.body_type != BodyType.DYNAMIC:
            return
        self.velocity = self.velocity.add(impulse.multiply(self.get_inverse_mass()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "rotation": self.rotation,
            "velocity": self.velocity.to_dict(),
            "angular_velocity": self.angular_velocity,
            "mass": self.mass,
            "friction": self.friction,
            "restitution": self.restitution,
            "body_type": self.body_type.value,
            "shape": self.shape.to_dict(),
            "enabled": self.enabled,
        }


@dataclass
class Contact:
    """Contact between two colliding bodies."""
    contact_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    body_a_id: str = ""
    body_b_id: str = ""
    point: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    normal: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    depth: float = 0.0
    state: CollisionState = CollisionState.START
    frictional_impulse: float = 0.0
    normal_impulse: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contact_id": self.contact_id,
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "point": self.point.to_dict(),
            "normal": self.normal.to_dict(),
            "depth": self.depth,
            "state": self.state.value,
        }


@dataclass
class Joint:
    """Constraint joint between two bodies."""
    joint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    joint_type: str = "distance"
    body_a_id: str = ""
    body_b_id: str = ""
    anchor_a: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    anchor_b: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    length: float = 0.0
    frequency: float = 0.0
    damping_ratio: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "joint_id": self.joint_id,
            "joint_type": self.joint_type,
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "anchor_a": self.anchor_a.to_dict(),
            "anchor_b": self.anchor_b.to_dict(),
            "length": self.length,
            "enabled": self.enabled,
        }


@dataclass
class PhysicsContact:
    """Contact pair for collision resolution."""
    body_a: RigidBody
    body_b: RigidBody
    contact: Contact

# ---------------------------------------------------------------------------
# Engine Physics Dynamics
# ---------------------------------------------------------------------------


class EnginePhysicsDynamics:
    """
    2D rigidbody physics engine with impulse-based dynamics.

    Provides collision detection, constraint solving, and continuous
    collision resolution. Supports static, kinematic, and dynamic bodies
    with gravity, friction, and restitution.
    """

    _instance: Optional["EnginePhysicsDynamics"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EnginePhysicsDynamics":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EnginePhysicsDynamics":
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

        self._bodies: Dict[str, RigidBody] = {}
        self._joints: Dict[str, Joint] = {}
        self._contacts: Dict[str, Contact] = {}
        self._gravity: Vector2 = Vector2(0, -9.81)
        self._damping: float = 0.99
        self._max_velocity: float = 200.0
        self._velocity_iterations: int = 8
        self._position_iterations: int = 3
        self._total_bodies: int = 0
        self._total_contacts: int = 0
        self._total_collisions: int = 0
        self._contact_listeners: List[Callable[[Contact, CollisionState], None]] = []

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_gravity(self, x: float, y: float) -> None:
        """Set the gravity vector."""
        with self._lock:
            self._gravity = Vector2(x, y)

    def get_gravity(self) -> Vector2:
        """Get the current gravity vector."""
        return self._gravity

    def set_iterations(self, velocity: int, position: int) -> None:
        """Set solver iteration counts."""
        with self._lock:
            self._velocity_iterations = max(1, velocity)
            self._position_iterations = max(1, position)

    # ------------------------------------------------------------------
    # Body Management
    # ------------------------------------------------------------------

    def create_body(
        self,
        x: float = 0.0,
        y: float = 0.0,
        mass: float = 1.0,
        body_type: BodyType = BodyType.DYNAMIC,
    ) -> RigidBody:
        """Create a new rigidbody."""
        with self._lock:
            body = RigidBody(
                position=Vector2(x, y),
                mass=mass,
                body_type=body_type,
            )
            if mass <= 0:
                body.body_type = BodyType.STATIC
            self._bodies[body.id] = body
            self._total_bodies += 1
            return body

    def create_circle(
        self,
        x: float = 0.0,
        y: float = 0.0,
        radius: float = 0.5,
        mass: float = 1.0,
        body_type: BodyType = BodyType.DYNAMIC,
    ) -> RigidBody:
        """Create a new circular rigidbody."""
        with self._lock:
            body = self.create_body(x, y, mass, body_type)
            body.shape = CollisionShape(
                shape_type=ShapeType.CIRCLE,
                radius=radius,
            )
            return body

    def create_box(
        self,
        x: float = 0.0,
        y: float = 0.0,
        width: float = 1.0,
        height: float = 1.0,
        mass: float = 1.0,
        body_type: BodyType = BodyType.DYNAMIC,
    ) -> RigidBody:
        """Create a new box-shaped rigidbody."""
        with self._lock:
            body = self.create_body(x, y, mass, body_type)
            body.shape = CollisionShape(
                shape_type=ShapeType.BOX,
                width=width,
                height=height,
            )
            return body

    def destroy_body(self, body_id: str) -> bool:
        """Destroy a rigidbody."""
        with self._lock:
            if body_id in self._bodies:
                del self._bodies[body_id]
                # Remove contacts involving this body
                to_remove = [
                    cid for cid, c in self._contacts.items()
                    if c.body_a_id == body_id or c.body_b_id == body_id
                ]
                for cid in to_remove:
                    del self._contacts[cid]
                return True
            return False

    def get_body(self, body_id: str) -> Optional[RigidBody]:
        """Get a body by ID."""
        return self._bodies.get(body_id)

    def get_all_bodies(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all bodies."""
        with self._lock:
            bodies = list(self._bodies.values())[:limit]
            return [b.to_dict() for b in bodies]

    # ------------------------------------------------------------------
    # Joint Management
    # ------------------------------------------------------------------

    def create_distance_joint(
        self,
        body_a_id: str,
        body_b_id: str,
        anchor_a: Tuple[float, float],
        anchor_b: Tuple[float, float],
        length: float,
        frequency: float = 2.0,
        damping: float = 0.5,
    ) -> Optional[Joint]:
        """Create a distance joint between two bodies."""
        with self._lock:
            if body_a_id not in self._bodies or body_b_id not in self._bodies:
                return None
            joint = Joint(
                joint_type="distance",
                body_a_id=body_a_id,
                body_b_id=body_b_id,
                anchor_a=Vector2.from_tuple(anchor_a),
                anchor_b=Vector2.from_tuple(anchor_b),
                length=length,
                frequency=frequency,
                damping_ratio=damping,
            )
            self._joints[joint.joint_id] = joint
            return joint

    def destroy_joint(self, joint_id: str) -> bool:
        """Destroy a joint."""
        with self._lock:
            if joint_id in self._joints:
                del self._joints[joint_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Collision Detection
    # ------------------------------------------------------------------

    def check_collision(self, a: RigidBody, b: RigidBody) -> Optional[Contact]:
        """Check for collision between two bodies."""
        a_aabb = a.get_aabb()
        b_aabb = b.get_aabb()
        if not a_aabb.overlaps(b_aabb):
            return None

        if a.shape.shape_type == ShapeType.CIRCLE and b.shape.shape_type == ShapeType.CIRCLE:
            return self._circle_circle_collision(a, b)

        if a.shape.shape_type == ShapeType.CIRCLE and b.shape.shape_type == ShapeType.BOX:
            return self._circle_box_collision(a, b)

        if a.shape.shape_type == ShapeType.BOX and b.shape.shape_type == ShapeType.CIRCLE:
            contact = self._circle_box_collision(b, a)
            if contact:
                contact.normal = contact.normal.multiply(-1)
                contact.body_a_id = a.id
                contact.body_b_id = b.id
            return contact

        return None

    def _circle_circle_collision(self, a: RigidBody, b: RigidBody) -> Optional[Contact]:
        """Circle-circle collision detection."""
        a_center = a.position.add(a.shape.offset)
        b_center = b.position.add(b.shape.offset)
        distance_vec = b_center.subtract(a_center)
        distance = distance_vec.length()
        if distance > a.shape.radius + b.shape.radius:
            return None

        normal = distance_vec.normalize() if distance > 0 else Vector2(1, 0)
        depth = (a.shape.radius + b.shape.radius) - distance
        point = a_center.add(normal.multiply(a.shape.radius))

        return Contact(
            body_a_id=a.id,
            body_b_id=b.id,
            point=point,
            normal=normal,
            depth=depth,
        )

    def _circle_box_collision(self, circle: RigidBody, box: RigidBody) -> Optional[Contact]:
        """Circle-box collision detection."""
        circle_center = circle.position.add(circle.shape.offset)
        box_cx = box.position.x + box.shape.offset.x
        box_cy = box.position.y + box.shape.offset.y
        hw = box.shape.width * 0.5
        hh = box.shape.height * 0.5

        # Find closest point on box to circle center
        closest_x = max(box_cx - hw, min(circle_center.x, box_cx + hw))
        closest_y = max(box_cy - hh, min(circle_center.y, box_cy + hh))
        closest = Vector2(closest_x, closest_y)

        distance_vec = circle_center.subtract(closest)
        distance = distance_vec.length()
        if distance > circle.shape.radius:
            return None

        normal = distance_vec.normalize() if distance > 0 else Vector2(0, 1)

        return Contact(
            body_a_id=circle.id,
            body_b_id=box.id,
            point=closest,
            normal=normal,
            depth=circle.shape.radius - distance,
        )

    def find_contacts(self) -> List[Contact]:
        """Find all active contacts through broad-phase and narrow-phase."""
        with self._lock:
            bodies = list(self._bodies.values())
            new_contacts: List[Contact] = []

            for i in range(len(bodies)):
                for j in range(i + 1, len(bodies)):
                    a = bodies[i]
                    b = bodies[j]
                    if a.body_type == BodyType.STATIC and b.body_type == BodyType.STATIC:
                        continue
                    if not a.enabled or not b.enabled:
                        continue
                    contact = self.check_collision(a, b)
                    if contact:
                        new_contacts.append(contact)
                        self._total_collisions += 1

            # Update contact state
            old_contact_ids = set(self._contacts.keys())
            for contact in new_contacts:
                existing = self._contacts.get(contact.contact_id)
                if existing:
                    existing.state = CollisionState.CONTINUE
                    old_contact_ids.discard(contact.contact_id)
                else:
                    self._contacts[contact.contact_id] = contact
                    contact.state = CollisionState.START
            # Mark remaining as ended
            for cid in old_contact_ids:
                if cid in self._contacts:
                    self._contacts[cid].state = CollisionState.END

            self._total_contacts = len(self._contacts)
            return list(self._contacts.values())

    # ------------------------------------------------------------------
    # Integration and Solving
    # ------------------------------------------------------------------

    def step(self, delta_time: float) -> Dict[str, Any]:
        """Integrate and solve physics for one step."""
        with self._lock:
            # Find all contacts
            self.find_contacts()

            # Integrate velocities
            for body in self._bodies.values():
                if body.body_type != BodyType.DYNAMIC:
                    continue
                body.position = body.position.add(body.velocity.multiply(delta_time))
                body.apply_force(self._gravity.multiply(body.mass), delta_time)

            # Solve velocities
            for _ in range(self._velocity_iterations):
                for contact in self._contacts.values():
                    if contact.state == CollisionState.END:
                        continue
                    self._solve_velocity(contact)

            # Dampen velocities
            for body in self._bodies.values():
                if body.body_type != BodyType.DYNAMIC:
                    continue
                body.velocity = body.velocity.multiply(self._damping)
                # Clamp maximum velocity
                speed = body.velocity.length()
                if speed > self._max_velocity:
                    scale = self._max_velocity / speed
                    body.velocity = body.velocity.multiply(scale)

            # Solve positions
            for _ in range(self._position_iterations):
                for contact in self._contacts.values():
                    if contact.state == CollisionState.END:
                        continue
                    self._solve_position(contact)

            # Clear ended contacts
            ended = [cid for cid, c in self._contacts.items() if c.state == CollisionState.END]
            for cid in ended:
                del self._contacts[cid]

            return {
                "step_ms": delta_time * 1000,
                "bodies": len(self._bodies),
                "contacts": len(self._contacts),
                "collisions": self._total_collisions,
            }

    def _solve_velocity(self, contact: Contact) -> None:
        """Solve velocity-level constraints."""
        body_a = self._bodies.get(contact.body_a_id)
        body_b = self._bodies.get(contact.body_b_id)
        if not body_a or not body_b:
            return

        # Calculate relative velocity
        rel_vel = body_b.velocity.subtract(body_a.velocity)
        rel_vel_normal = rel_vel.dot(contact.normal)

        # Don't solve if separating
        if rel_vel_normal > 0:
            return

        # Calculate impulse magnitude
        inv_mass = body_a.get_inverse_mass() + body_b.get_inverse_mass()
        if inv_mass <= 0:
            return

        restitution = (body_a.restitution + body_b.restitution) * 0.5
        jn = -(1.0 + restitution) * rel_vel_normal / inv_mass

        # Apply impulse
        impulse = contact.normal.multiply(jn)
        body_a.velocity = body_a.velocity.subtract(impulse.multiply(body_a.get_inverse_mass()))
        body_b.velocity = body_b.velocity.add(impulse.multiply(body_b.get_inverse_mass()))

    def _solve_position(self, contact: Contact) -> None:
        """Solve position-level constraints."""
        body_a = self._bodies.get(contact.body_a_id)
        body_b = self._bodies.get(contact.body_b_id)
        if not body_a or not body_b:
            return

        if contact.depth > 0:
            inv_mass = body_a.get_inverse_mass() + body_b.get_inverse_mass()
            if inv_mass <= 0:
                return

            correction = contact.normal.multiply(contact.depth / inv_mass * 0.8)
            if body_a.body_type == BodyType.DYNAMIC:
                body_a.position = body_a.position.subtract(correction.multiply(body_a.get_inverse_mass()))
            if body_b.body_type == BodyType.DYNAMIC:
                body_b.position = body_b.position.add(correction.multiply(body_b.get_inverse_mass()))

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def query_point(self, x: float, y: float) -> List[str]:
        """Find all bodies containing a point."""
        point = Vector2(x, y)
        result: List[str] = []
        for body in self._bodies.values():
            aabb = body.get_aabb()
            if aabb.contains(point):
                result.append(body.id)
        return result

    def query_aabb(self, aabb: AABB) -> List[str]:
        """Find all bodies overlapping an AABB."""
        result: List[str] = []
        for body in self._bodies.values():
            if body.get_aabb().overlaps(aabb):
                result.append(body.id)
        return result

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        body_type_counts: Dict[str, int] = {}
        for body in self._bodies.values():
            t = body.body_type.value
            body_type_counts[t] = body_type_counts.get(t, 0) + 1

        return {
            "total_bodies": len(self._bodies),
            "total_joints": len(self._joints),
            "total_contacts": self._total_contacts,
            "total_collisions": self._total_collisions,
            "body_type_distribution": body_type_counts,
            "gravity": self._gravity.to_dict(),
            "velocity_iterations": self._velocity_iterations,
            "position_iterations": self._position_iterations,
        }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_physics_dynamics() -> EnginePhysicsDynamics:
    """Get or create the singleton EnginePhysicsDynamics instance."""
    return EnginePhysicsDynamics.get_instance()