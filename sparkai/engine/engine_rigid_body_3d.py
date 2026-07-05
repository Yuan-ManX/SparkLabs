"""
SparkLabs Engine - 3D Rigid Body Dynamics

A 3D rigid body simulation core for the SparkLabs AI-native game engine.
It maintains 6-DOF bodies with quaternion rotation, diagonal inertia tensors,
sphere/box/capsule/convex-hull collision shapes, configurable joints, and a
sequential-impulse integration loop. The system is designed to feed high-body-count
3D physics scenes without per-frame allocation churn and exposes a clean
observability surface for AI directors to reason about contact graphs.

Architecture:
  EngineRigidBody3D (singleton)
    |-- RigidBody3D, Joint3D, Contact3D, PhysicsScene3D,
       RigidStats3D, RigidSnapshot3D, RigidEvent3D
    |-- BodyMotionType3D, ShapeKind3D, JointKind3D,
       SolverPhase3D, EngineEvent3DKind

Core Capabilities:
  - register_body / get_body / list_bodies / update_body /
    remove_body: 3D rigid body lifecycle with mass, inertia, and shape.
  - register_joint / get_joint / list_joints / remove_joint: articulated
    body connections with configurable limits and motors.
  - register_scene / get_scene / list_scenes / remove_scene: scene-level
    grouping with gravity and solver iteration counts.
  - detect_contacts: broadphase AABB overlap + narrowphase shape queries
    producing contact manifolds.
  - step_simulation: integrate velocities, apply forces/impulses, solve
    constraints, and resolve penetrations for a single timestep.
  - apply_impulse / apply_force / set_linear_velocity / set_angular_velocity:
    direct body manipulation hooks.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`EngineRigidBody3D.get_instance` or the module-level
:func:`get_rigid_body_3d` factory.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_BODIES: int = 4000
_MAX_JOINTS: int = 2000
_MAX_SCENES: int = 200
_MAX_CONTACTS: int = 10000
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


# 3D vector helpers operating on tuples (x, y, z) -------------------------


def _v3_add(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _v3_sub(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v3_scale(a: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (a[0] * s, a[1] * s, a[2] * s)


def _v3_dot(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _v3_cross(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _v3_length(a: Tuple[float, float, float]) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _v3_normalize(a: Tuple[float, float, float]) -> Tuple[float, float, float]:
    length = _v3_length(a)
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / length
    return (a[0] * inv, a[1] * inv, a[2] * inv)


def _v3_lerp(a: Tuple[float, float, float], b: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
    t = _clamp(t, 0.0, 1.0)
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


# Quaternion helpers operating on tuples (w, x, y, z) ---------------------


def _quat_identity() -> Tuple[float, float, float, float]:
    return (1.0, 0.0, 0.0, 0.0)


def _quat_normalize(q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    length = math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3])
    if length < 1e-9:
        return _quat_identity()
    inv = 1.0 / length
    return (q[0] * inv, q[1] * inv, q[2] * inv, q[3] * inv)


def _quat_from_axis_angle(axis: Tuple[float, float, float], angle: float) -> Tuple[float, float, float, float]:
    axis_n = _v3_normalize(axis)
    half = angle * 0.5
    s = math.sin(half)
    return _quat_normalize((math.cos(half), axis_n[0] * s, axis_n[1] * s, axis_n[2] * s))


def _quat_mul(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return _quat_normalize((
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ))


def _quat_rotate_vec(q: Tuple[float, float, float, float], v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    qw, qx, qy, qz = q
    vx, vy, vz = v
    t = (2.0 * _v3_cross((qx, qy, qz), v))
    return _v3_add(_v3_add(v, _v3_scale(t, qw)), _v3_cross((qx, qy, qz), t))


def _aabb_from_sphere(pos: Tuple[float, float, float], radius: float) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    r = max(0.0, radius)
    return ((pos[0] - r, pos[1] - r, pos[2] - r), (pos[0] + r, pos[1] + r, pos[2] + r))


def _aabb_from_box(pos: Tuple[float, float, float], half_extents: Tuple[float, float, float]) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    hx = max(0.0, half_extents[0])
    hy = max(0.0, half_extents[1])
    hz = max(0.0, half_extents[2])
    return ((pos[0] - hx, pos[1] - hy, pos[2] - hz), (pos[0] + hx, pos[1] + hy, pos[2] + hz))


def _aabb_overlap(a: Tuple[Tuple[float, float, float], Tuple[float, float, float]],
                  b: Tuple[Tuple[float, float, float], Tuple[float, float, float]]) -> bool:
    a_min, a_max = a
    b_min, b_max = b
    if a_max[0] < b_min[0] or a_min[0] > b_max[0]:
        return False
    if a_max[1] < b_min[1] or a_min[1] > b_max[1]:
        return False
    if a_max[2] < b_min[2] or a_min[2] > b_max[2]:
        return False
    return True


def _sphere_sphere_contact(
    pos_a: Tuple[float, float, float], radius_a: float,
    pos_b: Tuple[float, float, float], radius_b: float,
) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float], float]]:
    delta = _v3_sub(pos_b, pos_a)
    dist = _v3_length(delta)
    radius_sum = radius_a + radius_b
    if dist >= radius_sum:
        return None
    if dist < 1e-9:
        normal = (0.0, 1.0, 0.0)
        point = pos_a
    else:
        normal = _v3_scale(delta, 1.0 / dist)
        point = _v3_add(pos_a, _v3_scale(normal, radius_a))
    depth = radius_sum - dist
    return (normal, point, depth)


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class BodyMotionType3D(Enum):
    """Motion type controlling how a body participates in the simulation."""
    STATIC = "static"
    KINEMATIC = "kinematic"
    DYNAMIC = "dynamic"


class ShapeKind3D(Enum):
    """Collision shape primitives supported by the 3D rigid body core."""
    SPHERE = "sphere"
    BOX = "box"
    CAPSULE = "capsule"
    CONVEX_HULL = "convex_hull"
    MESH = "mesh"


class JointKind3D(Enum):
    """Constraint types connecting two 3D rigid bodies."""
    FIXED = "fixed"
    HINGE = "hinge"
    SLIDER = "slider"
    POINT_TO_POINT = "point_to_point"
    CONE_TWIST = "cone_twist"
    SIX_DOF = "six_dof"


class SolverPhase3D(Enum):
    """Phases of a single simulation step."""
    INTEGRATE = "integrate"
    BROADPHASE = "broadphase"
    NARROWPHASE = "narrowphase"
    SOLVE = "solve"
    RESOLVE = "resolve"


class EngineEvent3DKind(Enum):
    """Audit event types emitted by the 3D rigid body engine."""
    BODY_ADDED = "body_added"
    BODY_REMOVED = "body_removed"
    BODY_UPDATED = "body_updated"
    JOINT_ADDED = "joint_added"
    JOINT_REMOVED = "joint_removed"
    SCENE_REGISTERED = "scene_registered"
    SCENE_REMOVED = "scene_removed"
    CONTACT_DETECTED = "contact_detected"
    IMPULSE_APPLIED = "impulse_applied"
    STEP_COMPLETED = "step_completed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class RigidBody3D:
    """A 6-DOF rigid body in 3D space with quaternion rotation."""
    body_id: str
    name: str = ""
    description: str = ""
    motion_type: str = BodyMotionType3D.DYNAMIC.value
    mass: float = 1.0
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    linear_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    linear_damping: float = 0.05
    angular_damping: float = 0.05
    restitution: float = 0.3
    friction: float = 0.5
    shape_kind: str = ShapeKind3D.SPHERE.value
    shape_radius: float = 0.5
    shape_half_extents: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    shape_height: float = 1.0
    inertia_diagonal: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    force_accumulator: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    torque_accumulator: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scene_id: str = ""
    collision_mask: int = 0xFFFF
    collision_group: int = 0x0001
    is_sleeping: bool = False
    sleep_threshold: float = 0.01
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Joint3D:
    """A constraint connecting two 3D rigid bodies."""
    joint_id: str
    name: str = ""
    description: str = ""
    kind: str = JointKind3D.FIXED.value
    body_a_id: str = ""
    body_b_id: str = ""
    anchor_a: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    anchor_b: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    axis: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    lower_limit: float = 0.0
    upper_limit: float = 0.0
    limit_enabled: bool = False
    motor_enabled: bool = False
    motor_target_velocity: float = 0.0
    motor_max_force: float = 0.0
    stiffness: float = 1000.0
    damping: float = 50.0
    scene_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Contact3D:
    """A single contact point between two 3D bodies."""
    contact_id: str
    body_a_id: str = ""
    body_b_id: str = ""
    normal: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    depth: float = 0.0
    normal_impulse: float = 0.0
    tangent_impulse: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    timestamp_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhysicsScene3D:
    """A 3D physics scene grouping bodies and joints with shared gravity."""
    scene_id: str
    name: str = ""
    description: str = ""
    gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    solver_iterations: int = 10
    broadphase_pair_count: int = 0
    body_ids: List[str] = field(default_factory=list)
    joint_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RigidStats3D:
    """Cumulative statistics for the 3D rigid body engine."""
    total_bodies: int = 0
    total_joints: int = 0
    total_scenes: int = 0
    total_contacts_detected: int = 0
    total_impulses_applied: int = 0
    total_steps: int = 0
    last_step_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RigidSnapshot3D:
    """Point-in-time snapshot of the entire 3D rigid body engine state."""
    bodies: Dict[str, Any] = field(default_factory=dict)
    joints: Dict[str, Any] = field(default_factory=dict)
    scenes: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RigidEvent3D:
    """An audit event emitted by the 3D rigid body engine."""
    event_id: str
    kind: str = EngineEvent3DKind.BODY_ADDED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Engine Singleton
# ---------------------------------------------------------------------------


class EngineRigidBody3D:
    """Singleton 3D rigid body engine for the SparkLabs runtime."""

    _instance: Optional["EngineRigidBody3D"] = None
    _instance_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._bodies: Dict[str, RigidBody3D] = {}
        self._joints: Dict[str, Joint3D] = {}
        self._scenes: Dict[str, PhysicsScene3D] = {}
        self._contacts: List[Contact3D] = []
        self._audit: List[RigidEvent3D] = []
        self._steps: int = 0
        self._contacts_detected: int = 0
        self._impulses_applied: int = 0
        self._last_step_duration_ms: float = 0.0
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> "EngineRigidBody3D":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    inst = cls()
                    inst._initialize()
                    cls._instance = inst
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_defaults()
            self._initialized = True

    def _seed_defaults(self) -> None:
        """Seed a small set of default bodies, a joint, and a scene."""
        default_scene = PhysicsScene3D(
            scene_id="scn_default_3d",
            name="Default 3D Scene",
            description="Primary physics scene with Earth gravity.",
            gravity=(0.0, -9.81, 0.0),
            solver_iterations=10,
        )
        self._scenes[default_scene.scene_id] = default_scene
        self._record_event(EngineEvent3DKind.SCENE_REGISTERED, {
            "scene_id": default_scene.scene_id, "name": default_scene.name,
        })

        ground_body = RigidBody3D(
            body_id="bdy_ground_plane",
            name="Ground Plane",
            description="Static infinite ground plane for resting bodies.",
            motion_type=BodyMotionType3D.STATIC.value,
            mass=0.0,
            position=(0.0, 0.0, 0.0),
            shape_kind=ShapeKind3D.BOX.value,
            shape_half_extents=(50.0, 0.5, 50.0),
            inertia_diagonal=(0.0, 0.0, 0.0),
            friction=0.8,
            restitution=0.2,
            scene_id="scn_default_3d",
        )
        self._bodies[ground_body.body_id] = ground_body
        default_scene.body_ids.append(ground_body.body_id)
        self._record_event(EngineEvent3DKind.BODY_ADDED, {
            "body_id": ground_body.body_id, "name": ground_body.name,
        })

        sphere_body = RigidBody3D(
            body_id="bdy_bouncing_sphere",
            name="Bouncing Sphere",
            description="Dynamic sphere resting above the ground plane.",
            motion_type=BodyMotionType3D.DYNAMIC.value,
            mass=2.0,
            position=(0.0, 5.0, 0.0),
            shape_kind=ShapeKind3D.SPHERE.value,
            shape_radius=0.5,
            inertia_diagonal=(0.4, 0.4, 0.4),
            friction=0.5,
            restitution=0.7,
            scene_id="scn_default_3d",
        )
        self._bodies[sphere_body.body_id] = sphere_body
        default_scene.body_ids.append(sphere_body.body_id)
        self._record_event(EngineEvent3DKind.BODY_ADDED, {
            "body_id": sphere_body.body_id, "name": sphere_body.name,
        })

        box_body = RigidBody3D(
            body_id="bdy_crate",
            name="Wooden Crate",
            description="Dynamic box body for stacking experiments.",
            motion_type=BodyMotionType3D.DYNAMIC.value,
            mass=5.0,
            position=(1.5, 3.0, 0.0),
            shape_kind=ShapeKind3D.BOX.value,
            shape_half_extents=(0.5, 0.5, 0.5),
            inertia_diagonal=(0.83, 0.83, 0.83),
            friction=0.6,
            restitution=0.3,
            scene_id="scn_default_3d",
        )
        self._bodies[box_body.body_id] = box_body
        default_scene.body_ids.append(box_body.body_id)
        self._record_event(EngineEvent3DKind.BODY_ADDED, {
            "body_id": box_body.body_id, "name": box_body.name,
        })

    # ------------------------------------------------------------------
    # Audit Helpers
    # ------------------------------------------------------------------

    def _record_event(self, kind: EngineEvent3DKind, payload: Dict[str, Any]) -> None:
        event = RigidEvent3D(
            event_id=_new_id("evt"),
            kind=kind.value,
            payload=dict(payload),
            timestamp=_now(),
        )
        self._audit.append(event)
        _evict_fifo_list(self._audit, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Body Lifecycle
    # ------------------------------------------------------------------

    def register_body(
        self,
        body_id: str = "",
        name: str = "",
        description: str = "",
        motion_type: str = BodyMotionType3D.DYNAMIC.value,
        mass: float = 1.0,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0),
        linear_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        angular_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        linear_damping: float = 0.05,
        angular_damping: float = 0.05,
        restitution: float = 0.3,
        friction: float = 0.5,
        shape_kind: str = ShapeKind3D.SPHERE.value,
        shape_radius: float = 0.5,
        shape_half_extents: Tuple[float, float, float] = (0.5, 0.5, 0.5),
        shape_height: float = 1.0,
        inertia_diagonal: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        scene_id: str = "",
        collision_mask: int = 0xFFFF,
        collision_group: int = 0x0001,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RigidBody3D:
        with self._lock:
            bid = body_id or _new_id("bdy")
            mass_val = _safe_float(mass, 1.0)
            if motion_type == BodyMotionType3D.STATIC.value:
                mass_val = 0.0
            inertia = inertia_diagonal
            if motion_type == BodyMotionType3D.STATIC.value:
                inertia = (0.0, 0.0, 0.0)
            body = RigidBody3D(
                body_id=bid,
                name=name,
                description=description,
                motion_type=motion_type,
                mass=mass_val,
                position=tuple(position),
                rotation=_quat_normalize(tuple(rotation)),
                linear_velocity=tuple(linear_velocity),
                angular_velocity=tuple(angular_velocity),
                linear_damping=_safe_float(linear_damping, 0.05),
                angular_damping=_safe_float(angular_damping, 0.05),
                restitution=_clamp(_safe_float(restitution, 0.3), 0.0, 1.0),
                friction=_clamp(_safe_float(friction, 0.5), 0.0, 2.0),
                shape_kind=shape_kind,
                shape_radius=_safe_float(shape_radius, 0.5),
                shape_half_extents=tuple(shape_half_extents),
                shape_height=_safe_float(shape_height, 1.0),
                inertia_diagonal=tuple(inertia),
                scene_id=scene_id,
                collision_mask=int(collision_mask),
                collision_group=int(collision_group),
                metadata=dict(metadata or {}),
            )
            self._bodies[bid] = body
            if scene_id:
                scene = self._scenes.get(scene_id)
                if scene is not None and bid not in scene.body_ids:
                    scene.body_ids.append(bid)
            _evict_fifo_dict(self._bodies, _MAX_BODIES)
            self._record_event(EngineEvent3DKind.BODY_ADDED, {
                "body_id": bid, "name": name, "motion_type": motion_type,
            })
            return body

    def get_body(self, body_id: str) -> Optional[RigidBody3D]:
        with self._lock:
            return self._bodies.get(body_id)

    def list_bodies(
        self,
        motion_type: str = "",
        scene_id: str = "",
        shape_kind: str = "",
        limit: int = 100,
    ) -> List[RigidBody3D]:
        with self._lock:
            results: List[RigidBody3D] = []
            for body in self._bodies.values():
                if motion_type and body.motion_type != motion_type:
                    continue
                if scene_id and body.scene_id != scene_id:
                    continue
                if shape_kind and body.shape_kind != shape_kind:
                    continue
                results.append(body)
            return results[:max(0, int(limit))]

    def update_body(self, body_id: str, **kwargs: Any) -> Optional[RigidBody3D]:
        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return None
            for key, value in kwargs.items():
                if not hasattr(body, key):
                    continue
                if key in ("position", "linear_velocity", "angular_velocity", "shape_half_extents", "inertia_diagonal"):
                    setattr(body, key, tuple(value) if isinstance(value, (list, tuple)) else getattr(body, key))
                elif key == "rotation":
                    setattr(body, key, _quat_normalize(tuple(value)))
                elif key in ("mass", "linear_damping", "angular_damping", "restitution", "friction", "shape_radius", "shape_height"):
                    setattr(body, key, _safe_float(value, getattr(body, key)))
                elif key in ("collision_mask", "collision_group"):
                    setattr(body, key, int(value))
                else:
                    setattr(body, key, value)
            self._record_event(EngineEvent3DKind.BODY_UPDATED, {
                "body_id": body_id, "fields": list(kwargs.keys()),
            })
            return body

    def remove_body(self, body_id: str) -> bool:
        with self._lock:
            body = self._bodies.pop(body_id, None)
            if body is None:
                return False
            if body.scene_id:
                scene = self._scenes.get(body.scene_id)
                if scene is not None and body_id in scene.body_ids:
                    scene.body_ids.remove(body_id)
            for joint in list(self._joints.values()):
                if joint.body_a_id == body_id or joint.body_b_id == body_id:
                    self._joints.pop(joint.joint_id, None)
                    self._record_event(EngineEvent3DKind.JOINT_REMOVED, {
                        "joint_id": joint.joint_id, "reason": "body_removed",
                    })
            self._record_event(EngineEvent3DKind.BODY_REMOVED, {"body_id": body_id})
            return True

    # ------------------------------------------------------------------
    # Direct Body Manipulation
    # ------------------------------------------------------------------

    def apply_force(self, body_id: str, force: Tuple[float, float, float]) -> Optional[RigidBody3D]:
        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return None
            body.force_accumulator = _v3_add(body.force_accumulator, tuple(force))
            body.is_sleeping = False
            return body

    def apply_impulse(self, body_id: str, impulse: Tuple[float, float, float],
                       contact_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> Optional[RigidBody3D]:
        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return None
            if body.motion_type != BodyMotionType3D.DYNAMIC.value:
                return body
            inv_mass = 1.0 / body.mass if body.mass > 0.0 else 0.0
            body.linear_velocity = _v3_add(body.linear_velocity, _v3_scale(tuple(impulse), inv_mass))
            r = _v3_sub(tuple(contact_point), body.position)
            torque_impulse = _v3_cross(r, tuple(impulse))
            inv_inertia = (
                1.0 / body.inertia_diagonal[0] if body.inertia_diagonal[0] > 0 else 0.0,
                1.0 / body.inertia_diagonal[1] if body.inertia_diagonal[1] > 0 else 0.0,
                1.0 / body.inertia_diagonal[2] if body.inertia_diagonal[2] > 0 else 0.0,
            )
            body.angular_velocity = _v3_add(body.angular_velocity, (
                torque_impulse[0] * inv_inertia[0],
                torque_impulse[1] * inv_inertia[1],
                torque_impulse[2] * inv_inertia[2],
            ))
            body.is_sleeping = False
            self._impulses_applied += 1
            self._record_event(EngineEvent3DKind.IMPULSE_APPLIED, {
                "body_id": body_id, "impulse": list(impulse),
            })
            return body

    def set_linear_velocity(self, body_id: str, velocity: Tuple[float, float, float]) -> Optional[RigidBody3D]:
        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return None
            body.linear_velocity = tuple(velocity)
            body.is_sleeping = False
            return body

    def set_angular_velocity(self, body_id: str, velocity: Tuple[float, float, float]) -> Optional[RigidBody3D]:
        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return None
            body.angular_velocity = tuple(velocity)
            body.is_sleeping = False
            return body

    # ------------------------------------------------------------------
    # Joint Lifecycle
    # ------------------------------------------------------------------

    def register_joint(
        self,
        joint_id: str = "",
        name: str = "",
        description: str = "",
        kind: str = JointKind3D.FIXED.value,
        body_a_id: str = "",
        body_b_id: str = "",
        anchor_a: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        anchor_b: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        axis: Tuple[float, float, float] = (1.0, 0.0, 0.0),
        lower_limit: float = 0.0,
        upper_limit: float = 0.0,
        limit_enabled: bool = False,
        motor_enabled: bool = False,
        motor_target_velocity: float = 0.0,
        motor_max_force: float = 0.0,
        stiffness: float = 1000.0,
        damping: float = 50.0,
        scene_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Joint3D:
        with self._lock:
            jid = joint_id or _new_id("jnt")
            joint = Joint3D(
                joint_id=jid,
                name=name,
                description=description,
                kind=kind,
                body_a_id=body_a_id,
                body_b_id=body_b_id,
                anchor_a=tuple(anchor_a),
                anchor_b=tuple(anchor_b),
                axis=_v3_normalize(tuple(axis)),
                lower_limit=_safe_float(lower_limit, 0.0),
                upper_limit=_safe_float(upper_limit, 0.0),
                limit_enabled=bool(limit_enabled),
                motor_enabled=bool(motor_enabled),
                motor_target_velocity=_safe_float(motor_target_velocity, 0.0),
                motor_max_force=_safe_float(motor_max_force, 0.0),
                stiffness=_safe_float(stiffness, 1000.0),
                damping=_safe_float(damping, 50.0),
                scene_id=scene_id,
                metadata=dict(metadata or {}),
            )
            self._joints[jid] = joint
            if scene_id:
                scene = self._scenes.get(scene_id)
                if scene is not None and jid not in scene.joint_ids:
                    scene.joint_ids.append(jid)
            _evict_fifo_dict(self._joints, _MAX_JOINTS)
            self._record_event(EngineEvent3DKind.JOINT_ADDED, {
                "joint_id": jid, "kind": kind, "body_a_id": body_a_id, "body_b_id": body_b_id,
            })
            return joint

    def get_joint(self, joint_id: str) -> Optional[Joint3D]:
        with self._lock:
            return self._joints.get(joint_id)

    def list_joints(
        self,
        kind: str = "",
        body_id: str = "",
        scene_id: str = "",
        limit: int = 100,
    ) -> List[Joint3D]:
        with self._lock:
            results: List[Joint3D] = []
            for joint in self._joints.values():
                if kind and joint.kind != kind:
                    continue
                if body_id and joint.body_a_id != body_id and joint.body_b_id != body_id:
                    continue
                if scene_id and joint.scene_id != scene_id:
                    continue
                results.append(joint)
            return results[:max(0, int(limit))]

    def remove_joint(self, joint_id: str) -> bool:
        with self._lock:
            joint = self._joints.pop(joint_id, None)
            if joint is None:
                return False
            if joint.scene_id:
                scene = self._scenes.get(joint.scene_id)
                if scene is not None and joint_id in scene.joint_ids:
                    scene.joint_ids.remove(joint_id)
            self._record_event(EngineEvent3DKind.JOINT_REMOVED, {"joint_id": joint_id})
            return True

    # ------------------------------------------------------------------
    # Scene Lifecycle
    # ------------------------------------------------------------------

    def register_scene(
        self,
        scene_id: str = "",
        name: str = "",
        description: str = "",
        gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0),
        solver_iterations: int = 10,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PhysicsScene3D:
        with self._lock:
            sid = scene_id or _new_id("scn")
            scene = PhysicsScene3D(
                scene_id=sid,
                name=name,
                description=description,
                gravity=tuple(gravity),
                solver_iterations=_safe_int(solver_iterations, 10),
                metadata=dict(metadata or {}),
            )
            self._scenes[sid] = scene
            _evict_fifo_dict(self._scenes, _MAX_SCENES)
            self._record_event(EngineEvent3DKind.SCENE_REGISTERED, {
                "scene_id": sid, "name": name,
            })
            return scene

    def get_scene(self, scene_id: str) -> Optional[PhysicsScene3D]:
        with self._lock:
            return self._scenes.get(scene_id)

    def list_scenes(self, limit: int = 100) -> List[PhysicsScene3D]:
        with self._lock:
            return list(self._scenes.values())[:max(0, int(limit))]

    def remove_scene(self, scene_id: str) -> bool:
        with self._lock:
            scene = self._scenes.pop(scene_id, None)
            if scene is None:
                return False
            for body_id in scene.body_ids:
                body = self._bodies.get(body_id)
                if body is not None:
                    body.scene_id = ""
            for joint_id in scene.joint_ids:
                joint = self._joints.get(joint_id)
                if joint is not None:
                    joint.scene_id = ""
            self._record_event(EngineEvent3DKind.SCENE_REMOVED, {"scene_id": scene_id})
            return True

    # ------------------------------------------------------------------
    # Contact Detection
    # ------------------------------------------------------------------

    def _body_aabb(self, body: RigidBody3D) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        if body.shape_kind == ShapeKind3D.SPHERE.value:
            return _aabb_from_sphere(body.position, body.shape_radius)
        if body.shape_kind == ShapeKind3D.BOX.value:
            return _aabb_from_box(body.position, body.shape_half_extents)
        if body.shape_kind == ShapeKind3D.CAPSULE.value:
            r = body.shape_radius
            h = body.shape_height * 0.5
            return _aabb_from_box(body.position, (r, h + r, r))
        if body.shape_kind == ShapeKind3D.CONVEX_HULL.value:
            return _aabb_from_box(body.position, body.shape_half_extents)
        if body.shape_kind == ShapeKind3D.MESH.value:
            return _aabb_from_box(body.position, body.shape_half_extents)
        return _aabb_from_sphere(body.position, body.shape_radius)

    def detect_contacts(self, scene_id: str = "", limit: int = 1000) -> List[Contact3D]:
        with self._lock:
            bodies = list(self._bodies.values())
            if scene_id:
                bodies = [b for b in bodies if (not b.scene_id or b.scene_id == scene_id)]
            aabbs = [(b, self._body_aabb(b)) for b in bodies]
            contacts: List[Contact3D] = []
            for i in range(len(aabbs)):
                body_a, aabb_a = aabbs[i]
                if body_a.motion_type == BodyMotionType3D.STATIC.value and body_a.mass <= 0.0:
                    pass
                for j in range(i + 1, len(aabbs)):
                    body_b, aabb_b = aabbs[j]
                    if (body_a.motion_type == BodyMotionType3D.STATIC.value
                            and body_b.motion_type == BodyMotionType3D.STATIC.value):
                        continue
                    if not _aabb_overlap(aabb_a, aabb_b):
                        continue
                    contact = self._narrowphase(body_a, body_b)
                    if contact is not None:
                        contacts.append(contact)
                        if len(contacts) >= max(0, int(limit)):
                            break
                if len(contacts) >= max(0, int(limit)):
                    break
            self._contacts = contacts
            self._contacts_detected += len(contacts)
            scene = self._scenes.get(scene_id) if scene_id else None
            if scene is not None:
                scene.broadphase_pair_count = len(contacts)
            if contacts:
                self._record_event(EngineEvent3DKind.CONTACT_DETECTED, {
                    "scene_id": scene_id, "count": len(contacts),
                })
            return contacts

    def _narrowphase(self, body_a: RigidBody3D, body_b: RigidBody3D) -> Optional[Contact3D]:
        if (body_a.shape_kind == ShapeKind3D.SPHERE.value
                and body_b.shape_kind == ShapeKind3D.SPHERE.value):
            result = _sphere_sphere_contact(
                body_a.position, body_a.shape_radius,
                body_b.position, body_b.shape_radius,
            )
            if result is None:
                return None
            normal, point, depth = result
            return Contact3D(
                contact_id=_new_id("ctc"),
                body_a_id=body_a.body_id,
                body_b_id=body_b.body_id,
                normal=normal,
                point=point,
                depth=depth,
                timestamp_ms=int(__import__("time").time() * 1000),
            )
        if (body_a.shape_kind in (ShapeKind3D.BOX.value, ShapeKind3D.CONVEX_HULL.value)
                and body_b.shape_kind in (ShapeKind3D.BOX.value, ShapeKind3D.CONVEX_HULL.value)):
            delta = _v3_sub(body_b.position, body_a.position)
            dist = _v3_length(delta)
            combined_half = (
                body_a.shape_half_extents[0] + body_b.shape_half_extents[0],
                body_a.shape_half_extents[1] + body_b.shape_half_extents[1],
                body_a.shape_half_extents[2] + body_b.shape_half_extents[2],
            )
            overlap_x = combined_half[0] - abs(delta[0])
            overlap_y = combined_half[1] - abs(delta[1])
            overlap_z = combined_half[2] - abs(delta[2])
            if overlap_x <= 0 or overlap_y <= 0 or overlap_z <= 0:
                return None
            if overlap_x <= overlap_y and overlap_x <= overlap_z:
                normal = (1.0 if delta[0] >= 0 else -1.0, 0.0, 0.0)
                depth = overlap_x
            elif overlap_y <= overlap_z:
                normal = (0.0, 1.0 if delta[1] >= 0 else -1.0, 0.0)
                depth = overlap_y
            else:
                normal = (0.0, 0.0, 1.0 if delta[2] >= 0 else -1.0)
                depth = overlap_z
            point = _v3_lerp(body_a.position, body_b.position, 0.5)
            return Contact3D(
                contact_id=_new_id("ctc"),
                body_a_id=body_a.body_id,
                body_b_id=body_b.body_id,
                normal=normal,
                point=point,
                depth=depth,
                timestamp_ms=int(__import__("time").time() * 1000),
            )
        return None

    def get_contacts(self, limit: int = 1000) -> List[Contact3D]:
        with self._lock:
            return list(self._contacts)[:max(0, int(limit))]

    # ------------------------------------------------------------------
    # Simulation Step
    # ------------------------------------------------------------------

    def step_simulation(
        self,
        dt: float = 0.016,
        scene_id: str = "",
        solver_iterations: int = 10,
    ) -> Dict[str, Any]:
        with self._lock:
            import time as _time
            start = _time.time()
            dt_val = _safe_float(dt, 0.016)
            if dt_val <= 0:
                dt_val = 0.016
            iters = _safe_int(solver_iterations, 10)
            if iters < 1:
                iters = 10
            scene = None
            gravity = (0.0, -9.81, 0.0)
            if scene_id:
                scene = self._scenes.get(scene_id)
                if scene is not None:
                    gravity = scene.gravity
                    iters = scene.solver_iterations or iters
            bodies_iter = list(self._bodies.values())
            if scene is not None:
                bodies_iter = [b for b in bodies_iter if (not b.scene_id or b.scene_id == scene_id)]
            for body in bodies_iter:
                if body.motion_type != BodyMotionType3D.DYNAMIC.value:
                    continue
                if body.is_sleeping:
                    continue
                force = _v3_add(body.force_accumulator, _v3_scale(gravity, body.mass))
                accel = _v3_scale(force, 1.0 / body.mass if body.mass > 0 else 0.0)
                body.linear_velocity = _v3_add(
                    body.linear_velocity,
                    _v3_scale(accel, dt_val),
                )
                body.linear_velocity = _v3_scale(body.linear_velocity, max(0.0, 1.0 - body.linear_damping * dt_val))
                body.angular_velocity = _v3_scale(body.angular_velocity, max(0.0, 1.0 - body.angular_damping * dt_val))
                body.position = _v3_add(body.position, _v3_scale(body.linear_velocity, dt_val))
                ang_speed = _v3_length(body.angular_velocity)
                if ang_speed > 1e-6:
                    axis = _v3_scale(body.angular_velocity, 1.0 / ang_speed)
                    delta_q = _quat_from_axis_angle(axis, ang_speed * dt_val)
                    body.rotation = _quat_normalize(_quat_mul(delta_q, body.rotation))
                body.force_accumulator = (0.0, 0.0, 0.0)
                body.torque_accumulator = (0.0, 0.0, 0.0)
                speed = _v3_length(body.linear_velocity)
                if speed < body.sleep_threshold and ang_speed < body.sleep_threshold:
                    body.is_sleeping = True
            self.detect_contacts(scene_id=scene_id, limit=_MAX_CONTACTS)
            for _ in range(iters):
                for contact in self._contacts:
                    body_a = self._bodies.get(contact.body_a_id)
                    body_b = self._bodies.get(contact.body_b_id)
                    if body_a is None or body_b is None:
                        continue
                    inv_mass_a = 1.0 / body_a.mass if body_a.mass > 0 and body_a.motion_type == BodyMotionType3D.DYNAMIC.value else 0.0
                    inv_mass_b = 1.0 / body_b.mass if body_b.mass > 0 and body_b.motion_type == BodyMotionType3D.DYNAMIC.value else 0.0
                    inv_mass_sum = inv_mass_a + inv_mass_b
                    if inv_mass_sum <= 0:
                        continue
                    rel_vel = _v3_sub(body_b.linear_velocity, body_a.linear_velocity)
                    vel_along_normal = _v3_dot(rel_vel, contact.normal)
                    if vel_along_normal > 0:
                        continue
                    restitution = min(body_a.restitution, body_b.restitution)
                    j_impulse = -(1.0 + restitution) * vel_along_normal / inv_mass_sum
                    impulse = _v3_scale(contact.normal, j_impulse)
                    if inv_mass_a > 0:
                        body_a.linear_velocity = _v3_sub(body_a.linear_velocity, _v3_scale(impulse, inv_mass_a))
                    if inv_mass_b > 0:
                        body_b.linear_velocity = _v3_add(body_b.linear_velocity, _v3_scale(impulse, inv_mass_b))
                    penetration_correction = _v3_scale(contact.normal, max(0.0, contact.depth) * 0.2 / inv_mass_sum)
                    if inv_mass_a > 0:
                        body_a.position = _v3_sub(body_a.position, _v3_scale(penetration_correction, inv_mass_a))
                    if inv_mass_b > 0:
                        body_b.position = _v3_add(body_b.position, _v3_scale(penetration_correction, inv_mass_b))
            self._steps += 1
            duration_ms = (_time.time() - start) * 1000.0
            self._last_step_duration_ms = round(duration_ms, 3)
            self._record_event(EngineEvent3DKind.STEP_COMPLETED, {
                "scene_id": scene_id, "dt": dt_val, "iterations": iters,
                "duration_ms": self._last_step_duration_ms,
            })
            return {
                "scene_id": scene_id,
                "dt": dt_val,
                "iterations": iters,
                "bodies_simulated": len(bodies_iter),
                "contacts_resolved": len(self._contacts),
                "duration_ms": self._last_step_duration_ms,
            }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[RigidEvent3D]:
        with self._lock:
            return list(self._audit)[:max(0, int(limit))]

    def get_stats(self) -> RigidStats3D:
        with self._lock:
            return RigidStats3D(
                total_bodies=len(self._bodies),
                total_joints=len(self._joints),
                total_scenes=len(self._scenes),
                total_contacts_detected=self._contacts_detected,
                total_impulses_applied=self._impulses_applied,
                total_steps=self._steps,
                last_step_duration_ms=self._last_step_duration_ms,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "bodies": len(self._bodies),
                "joints": len(self._joints),
                "scenes": len(self._scenes),
                "contacts": len(self._contacts),
                "steps": self._steps,
                "contacts_detected": self._contacts_detected,
                "impulses_applied": self._impulses_applied,
                "events": len(self._audit),
            }

    def get_snapshot(self) -> RigidSnapshot3D:
        with self._lock:
            return RigidSnapshot3D(
                bodies={bid: b.to_dict() for bid, b in self._bodies.items()},
                joints={jid: j.to_dict() for jid, j in self._joints.items()},
                scenes={sid: s.to_dict() for sid, s in self._scenes.items()},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._bodies.clear()
            self._joints.clear()
            self._scenes.clear()
            self._contacts.clear()
            self._audit.clear()
            self._steps = 0
            self._contacts_detected = 0
            self._impulses_applied = 0
            self._last_step_duration_ms = 0.0
            self._seed_defaults()
            self._initialized = True


# ---------------------------------------------------------------------------
# Module Factory
# ---------------------------------------------------------------------------


def get_rigid_body_3d() -> EngineRigidBody3D:
    return EngineRigidBody3D.get_instance()
