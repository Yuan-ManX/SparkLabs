"""
SparkLabs Engine - Physics Joint and Constraint System

A comprehensive physics joint and constraint management layer for the
SparkLabs AI-native game engine. It provides a rich library of joint
types (hinge, spring, piston, ball-socket, fixed, slider, cone-twist,
custom), an integrated motor system with configurable torque and
target velocity, damped spring behavior, angular and linear limits,
breakable constraints that fail under configurable stress thresholds,
joint chains for ragdolls, ropes, and mechanical linkages, an AI-driven
parameter tuning pipeline for realistic physics, a configurable
constraint solver, debug visualization data, and per-joint stress
tracking for breakage detection.

Architecture:
  PhysicsJointConstraintSystem (Singleton)
    |-- JointType / ConstraintType / JointStatus
    |-- MotorMode / BreakCondition / JointAxis
    |-- SolverType / JointEventKind
    |-- JointAnchor / JointLimit / MotorConfig
    |-- SpringConfig / BreakThreshold / JointBody
    |-- PhysicsJoint / JointChain / JointConfig
    |-- JointStats / JointSnapshot / JointEvent

Design notes:
  - Thread-safe singleton using double-checked locking with an RLock.
  - All public mutating operations return structured tuples so callers
    can branch on success without raising exceptions for expected
    failures.
  - Data structures serialize to plain dicts via to_dict() so they can
    be handed to the AI narrative layer or persisted to save files.
  - Seed data is loaded on first initialization so the engine has a
    usable starting set of joint types, sample joints, and joint chains
    available out of the box.
  - AI parameter tuning uses a deterministic heuristic optimizer that
    adjusts stiffness, damping, motor torque, and spring rest lengths
    based on observed stress and stability metrics.

Usage:
    system = get_physics_joint_constraint_system()
    joint = system.register_joint(
        name="door_hinge",
        joint_type=JointType.HINGE,
        body_a_id="wall_01",
        body_b_id="door_01",
    )
    report = system.tick(0.016)
    system.ai_tune_parameters(joint.joint_id)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> float:
    """Return the current wall-clock time in seconds."""
    return time.time()


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, falling back to default on failure."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Coerce a value to int, falling back to default on failure."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a scalar into the inclusive range [lo, hi]."""
    if hi < lo:
        lo, hi = hi, lo
    return max(lo, min(hi, value))


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by t (clamped to [0, 1])."""
    return a + (b - a) * _clamp(t, 0.0, 1.0)


def _length3(v: Tuple[float, float, float]) -> float:
    """Euclidean length of a 3-vector."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _normalize3(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Return the unit vector of v, or a zero vector if v is near zero."""
    n = _length3(v)
    if n < 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _sub3(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Component-wise subtraction of two 3-vectors."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add3(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Component-wise addition of two 3-vectors."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale3(v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    """Scale a 3-vector by a scalar."""
    return (v[0] * s, v[1] * s, v[2] * s)


def _dot3(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    """Dot product of two 3-vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross3(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Cross product of two 3-vectors."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _angle_between(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    """Angle in radians between two 3-vectors."""
    na = _length3(a)
    nb = _length3(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    cos_theta = _clamp(_dot3(a, b) / (na * nb), -1.0, 1.0)
    return math.acos(cos_theta)


def _dataclass_to_dict(obj: Any) -> Any:
    """Recursively convert a dataclass (and nested structures) to a dict."""
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            result[k] = _dataclass_to_dict(v)
        return result
    if isinstance(obj, list):
        return [_dataclass_to_dict(i) for i in obj]
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {kk: _dataclass_to_dict(vv) for kk, vv in obj.items()}
    if isinstance(obj, Enum):
        return obj.value
    return obj


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_JOINTS = 8000
_MAX_JOINT_TYPES = 128
_MAX_CHAINS = 512
_MAX_EVENTS = 4000
_MAX_STRESS_HISTORY = 256


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class JointType(str, Enum):
    """Classification of a joint by the degrees of freedom it permits."""
    HINGE = "hinge"
    SPRING = "spring"
    PISTON = "piston"
    BALL_SOCKET = "ball_socket"
    FIXED = "fixed"
    SLIDER = "slider"
    CONE_TWIST = "cone_twist"
    CUSTOM = "custom"


class ConstraintType(str, Enum):
    """The mathematical form of the underlying constraint equation."""
    POINT = "point"
    DISTANCE = "distance"
    ANGULAR = "angular"
    LINEAR = "linear"
    SIX_DOF = "six_dof"
    GENERIC = "generic"


class JointStatus(str, Enum):
    """Operational state of a joint instance."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BROKEN = "broken"
    LOCKED = "locked"
    DAMAGED = "damaged"


class MotorMode(str, Enum):
    """Control strategy applied by a joint motor."""
    OFF = "off"
    VELOCITY = "velocity"
    POSITION = "position"
    FORCE = "force"
    SERVO = "servo"


class BreakCondition(str, Enum):
    """Criterion used to decide when a breakable joint snaps."""
    NONE = "none"
    FORCE = "force"
    TORQUE = "torque"
    IMPULSE = "impulse"
    STRESS = "stress"
    ANGLE = "angle"
    DISTANCE = "distance"


class JointAxis(str, Enum):
    """Axis or axis combination along which a joint operates."""
    X = "x"
    Y = "y"
    Z = "z"
    XY = "xy"
    XZ = "xz"
    YZ = "yz"
    XYZ = "xyz"


class SolverType(str, Enum):
    """Iterative solver used to resolve constraint forces."""
    SEQUENTIAL_IMPULSE = "sequential_impulse"
    PROJECTED_GAUSS_SEIDEL = "projected_gauss_seidel"
    JACOBI = "jacobi"
    CONJUGATE_GRADIENT = "conjugate_gradient"
    NESTEROV = "nesterov"


class JointEventKind(str, Enum):
    """Kind of event recorded by the joint system."""
    JOINT_REGISTERED = "joint_registered"
    JOINT_REMOVED = "joint_removed"
    JOINT_BROKEN = "joint_broken"
    JOINT_REPAIRED = "joint_repaired"
    JOINT_LOCKED = "joint_locked"
    JOINT_UNLOCKED = "joint_unlocked"
    MOTOR_ENABLED = "motor_enabled"
    MOTOR_DISABLED = "motor_disabled"
    SPRING_CONFIGURED = "spring_configured"
    LIMIT_SET = "limit_set"
    BREAK_THRESHOLD_SET = "break_threshold_set"
    CHAIN_CREATED = "chain_created"
    CHAIN_JOINT_ADDED = "chain_joint_added"
    CHAIN_JOINT_REMOVED = "chain_joint_removed"
    AI_TUNED = "ai_tuned"
    AUTO_BALANCED = "auto_balanced"
    CHAIN_OPTIMIZED = "chain_optimized"
    SOLVER_CONFIGURED = "solver_configured"
    STRESS_COMPUTED = "stress_computed"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class JointAnchor:
    """Anchor point describing where a joint attaches to a body."""
    body_id: str = ""
    local_offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    world_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: Tuple[float, float, float] = (0.0, 1.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class JointLimit:
    """Angular and linear motion limits for a joint."""
    min_angle: float = -math.pi
    max_angle: float = math.pi
    min_distance: float = 0.0
    max_distance: float = 0.0
    twist_limit: float = math.pi
    cone_limit: float = math.pi
    enable_angular_limit: bool = False
    enable_linear_limit: bool = False
    bounce: float = 0.0
    softness: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    def clamp_angle(self, angle: float) -> float:
        """Clamp an angle into the configured angular range."""
        return _clamp(angle, self.min_angle, self.max_angle)

    def clamp_distance(self, distance: float) -> float:
        """Clamp a distance into the configured linear range."""
        return _clamp(distance, self.min_distance, self.max_distance)


@dataclass
class MotorConfig:
    """Configuration for a joint motor."""
    mode: str = MotorMode.OFF.value
    target_velocity: float = 0.0
    max_torque: float = 100.0
    max_force: float = 100.0
    target_position: float = 0.0
    servo_kp: float = 1.0
    servo_kd: float = 0.1
    acceleration: float = 10.0
    enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpringConfig:
    """Configuration for a damped spring joint."""
    stiffness: float = 50.0
    damping: float = 5.0
    rest_length: float = 1.0
    min_length: float = 0.0
    max_length: float = 10.0
    enable_limit: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    def compute_spring_force(self, length: float, velocity: float) -> float:
        """Return the spring force for the given length and velocity."""
        clamped = _clamp(length, self.min_length, self.max_length)
        extension = clamped - self.rest_length
        return -(self.stiffness * extension + self.damping * velocity)


@dataclass
class BreakThreshold:
    """Thresholds at which a breakable joint will snap."""
    condition: str = BreakCondition.NONE.value
    max_force: float = 1e9
    max_torque: float = 1e9
    max_impulse: float = 1e9
    max_stress: float = 1e9
    max_angle: float = math.pi * 2.0
    max_distance: float = 1e9
    breakable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class JointBody:
    """Snapshot of a physics body connected by a joint."""
    body_id: str = ""
    mass: float = 1.0
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    inverse_mass: float = 1.0
    inverse_inertia: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    def __post_init__(self) -> None:
        # Recompute inverse mass when a positive mass is supplied.
        if self.mass > 0.0:
            self.inverse_mass = 1.0 / self.mass
            # Approximate inverse inertia from a uniform sphere assumption.
            self.inverse_inertia = 2.5 / (self.mass * 0.2 * 0.2)


@dataclass
class PhysicsJoint:
    """A single joint instance connecting two bodies."""
    joint_id: str = field(default_factory=lambda: f"jnt_{uuid.uuid4().hex[:10]}")
    name: str = ""
    joint_type: str = JointType.HINGE.value
    constraint_type: str = ConstraintType.GENERIC.value
    body_a: JointBody = field(default_factory=JointBody)
    body_b: JointBody = field(default_factory=JointBody)
    anchor_a: JointAnchor = field(default_factory=JointAnchor)
    anchor_b: JointAnchor = field(default_factory=JointAnchor)
    axis: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    limit: JointLimit = field(default_factory=JointLimit)
    motor: MotorConfig = field(default_factory=MotorConfig)
    spring: SpringConfig = field(default_factory=SpringConfig)
    break_threshold: BreakThreshold = field(default_factory=BreakThreshold)
    status: str = JointStatus.ACTIVE.value
    current_stress: float = 0.0
    current_force: float = 0.0
    current_torque: float = 0.0
    current_impulse: float = 0.0
    current_angle: float = 0.0
    current_distance: float = 0.0
    solver_iterations: int = 8
    collision_enabled: bool = False
    visualization_enabled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    stress_history: List[float] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    chain_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    def is_active(self) -> bool:
        """Return True when the joint is in the ACTIVE status."""
        return self.status == JointStatus.ACTIVE.value

    def record_stress(self, stress: float) -> None:
        """Push a stress sample into the rolling history window."""
        self.stress_history.append(stress)
        if len(self.stress_history) > _MAX_STRESS_HISTORY:
            self.stress_history = self.stress_history[-_MAX_STRESS_HISTORY:]
        self.current_stress = stress
        self.updated_at = _now()


@dataclass
class JointChain:
    """A connected sequence of joints forming a linkage or ragdoll."""
    chain_id: str = field(default_factory=lambda: f"chn_{uuid.uuid4().hex[:10]}")
    name: str = ""
    joint_ids: List[str] = field(default_factory=list)
    root_joint_id: str = ""
    tip_joint_id: str = ""
    closed: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    def length(self) -> int:
        """Return the number of joints in the chain."""
        return len(self.joint_ids)


@dataclass
class JointConfig:
    """Global configuration for the joint and constraint system."""
    solver_type: str = SolverType.SEQUENTIAL_IMPULSE.value
    solver_iterations: int = 8
    solver_accuracy: float = 1e-5
    global_gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    global_damping: float = 0.02
    global_air_drag: float = 0.01
    enable_breakable_joints: bool = True
    enable_stress_tracking: bool = True
    enable_visualization: bool = False
    max_joints: int = _MAX_JOINTS
    max_chains: int = _MAX_CHAINS
    ai_tuning_aggression: float = 0.5
    ai_tuning_stability_target: float = 0.8
    warm_starting: bool = True
    split_impulse: bool = True
    bias_factor: float = 0.2

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class JointStats:
    """Aggregated statistics for the joint system."""
    total_joints: int = 0
    active_joints: int = 0
    broken_joints: int = 0
    locked_joints: int = 0
    damaged_joints: int = 0
    total_joint_types: int = 0
    total_chains: int = 0
    total_motors_enabled: int = 0
    total_springs: int = 0
    total_breakable: int = 0
    total_stress_samples: int = 0
    average_stress: float = 0.0
    peak_stress: float = 0.0
    tick_count: int = 0
    total_breaks: int = 0
    total_ai_tunes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class JointSnapshot:
    """Point-in-time snapshot of the entire joint system."""
    joints: List[Dict[str, Any]] = field(default_factory=list)
    chains: List[Dict[str, Any]] = field(default_factory=list)
    joint_types: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class JointEvent:
    """An event recorded by the joint system."""
    event_id: str
    kind: str
    timestamp: float
    joint_id: Optional[str] = None
    chain_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Joint Type Descriptor (used by the registry of known joint types)
# ---------------------------------------------------------------------------

@dataclass
class JointTypeDescriptor:
    """Descriptor for a registered joint type template."""
    type_id: str
    joint_type: str = JointType.CUSTOM.value
    display_name: str = ""
    description: str = ""
    default_axis: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    default_limit: JointLimit = field(default_factory=JointLimit)
    default_motor: MotorConfig = field(default_factory=MotorConfig)
    default_spring: SpringConfig = field(default_factory=SpringConfig)
    default_break: BreakThreshold = field(default_factory=BreakThreshold)
    supports_motor: bool = False
    supports_spring: bool = False
    supports_limits: bool = False
    supports_breakable: bool = False
    degrees_of_freedom: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Physics Joint Constraint System
# ---------------------------------------------------------------------------

class PhysicsJointConstraintSystem:
    """Manages physics joints, constraints, motors, springs, and chains.

    Provides a unified registry for joint instances and joint type
    templates, a motor and spring configuration layer, breakable
    constraint evaluation, joint chain construction for ragdolls and
    ropes, an AI-driven parameter tuning pipeline, a configurable
    constraint solver, debug visualization data export, and per-joint
    stress tracking. The system is a thread-safe singleton.

    Usage:
        system = get_physics_joint_constraint_system()
        joint = system.register_joint(name="hinge_01", joint_type=JointType.HINGE)
        report = system.tick(0.016)
    """

    _instance: Optional["PhysicsJointConstraintSystem"] = None
    _lock = threading.RLock()
    _init_lock = threading.RLock()

    # -- internal constants ------------------------------------------------
    EPSILON: float = 1e-9
    MAX_EVENTS: int = _MAX_EVENTS

    def __init__(self) -> None:
        self._initialized: bool = False
        self._seeded: bool = False
        self._joints: Dict[str, PhysicsJoint] = {}
        self._joint_types: Dict[str, JointTypeDescriptor] = {}
        self._chains: Dict[str, JointChain] = {}
        self._events: List[JointEvent] = []
        self._config: JointConfig = JointConfig()
        self._stats: JointStats = JointStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._joint_counter: int = 0
        self._chain_counter: int = 0
        self._total_breaks: int = 0
        self._total_ai_tunes: int = 0
        self._total_stress_samples: int = 0
        self._peak_stress: float = 0.0
        self._stress_sum: float = 0.0
        self._initialized = True

    # ------------------------------------------------------------------
    # Singleton lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "PhysicsJointConstraintSystem":
        """Return the singleton instance, creating it if needed.

        Uses double-checked locking so that once the instance exists
        no lock acquisition is required on the hot path.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Tear down the singleton so a fresh instance can be built."""
        with cls._lock:
            cls._instance = None

    def initialize(self) -> Tuple[bool, str]:
        """Load seed data and default joint type templates.

        Idempotent: calling initialize() multiple times is safe and
        will not duplicate seed entries.
        """
        with self._init_lock:
            if self._seeded:
                return True, "Already initialized"
            self._load_default_joint_types()
            self._load_seed_joints()
            self._load_seed_chains()
            self._seeded = True
            self._emit(
                JointEventKind.JOINT_REGISTERED,
                {
                    "action": "initialize",
                    "joint_types": len(self._joint_types),
                    "joints": len(self._joints),
                    "chains": len(self._chains),
                },
            )
            return True, (
                f"Initialized with {len(self._joint_types)} joint types, "
                f"{len(self._joints)} sample joints, "
                f"{len(self._chains)} joint chains"
            )

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"jevt_{self._event_counter:08d}"

    def _emit(
        self,
        kind: JointEventKind,
        payload: Optional[Dict[str, Any]] = None,
        joint_id: Optional[str] = None,
        chain_id: Optional[str] = None,
    ) -> JointEvent:
        """Record an event, capping the total stored to MAX_EVENTS."""
        event = JointEvent(
            event_id=self._next_event_id(),
            kind=kind.value,
            timestamp=_now(),
            joint_id=joint_id,
            chain_id=chain_id,
            details=dict(payload or {}),
        )
        self._events.append(event)
        if len(self._events) > self.MAX_EVENTS:
            # Drop the oldest entries to stay within the cap.
            self._events = self._events[-self.MAX_EVENTS:]
        return event

    # ------------------------------------------------------------------
    # Joint type registry
    # ------------------------------------------------------------------

    def _load_default_joint_types(self) -> None:
        """Register the built-in joint type templates."""
        builtins: List[JointTypeDescriptor] = [
            JointTypeDescriptor(
                type_id="jt_hinge",
                joint_type=JointType.HINGE.value,
                display_name="Hinge Joint",
                description="Rotational pivot around a single axis.",
                default_axis=(0.0, 0.0, 1.0),
                default_limit=JointLimit(
                    min_angle=-math.pi,
                    max_angle=math.pi,
                    enable_angular_limit=True,
                ),
                default_motor=MotorConfig(max_torque=200.0),
                supports_motor=True,
                supports_limits=True,
                supports_breakable=True,
                degrees_of_freedom=1,
            ),
            JointTypeDescriptor(
                type_id="jt_spring",
                joint_type=JointType.SPRING.value,
                display_name="Spring Joint",
                description="Damped elastic connection between two bodies.",
                default_spring=SpringConfig(stiffness=60.0, damping=4.0, rest_length=1.5),
                supports_spring=True,
                supports_breakable=True,
                degrees_of_freedom=3,
            ),
            JointTypeDescriptor(
                type_id="jt_piston",
                joint_type=JointType.PISTON.value,
                display_name="Piston Joint",
                description="Combined slider and hinge along one axis.",
                default_axis=(1.0, 0.0, 0.0),
                default_limit=JointLimit(
                    min_distance=0.0,
                    max_distance=2.0,
                    min_angle=0.0,
                    max_angle=0.0,
                    enable_linear_limit=True,
                    enable_angular_limit=True,
                ),
                default_motor=MotorConfig(max_torque=150.0, max_force=300.0),
                supports_motor=True,
                supports_limits=True,
                supports_breakable=True,
                degrees_of_freedom=2,
            ),
            JointTypeDescriptor(
                type_id="jt_ball_socket",
                joint_type=JointType.BALL_SOCKET.value,
                display_name="Ball-Socket Joint",
                description="Multi-axis rotational pivot with a cone limit.",
                default_limit=JointLimit(
                    cone_limit=math.pi / 2.0,
                    twist_limit=math.pi / 2.0,
                    enable_angular_limit=True,
                ),
                supports_limits=True,
                supports_breakable=True,
                degrees_of_freedom=3,
            ),
            JointTypeDescriptor(
                type_id="jt_fixed",
                joint_type=JointType.FIXED.value,
                display_name="Fixed Joint",
                description="Rigidly fuses two bodies together.",
                default_break=BreakThreshold(max_force=5000.0, breakable=True),
                supports_breakable=True,
                degrees_of_freedom=0,
            ),
            JointTypeDescriptor(
                type_id="jt_slider",
                joint_type=JointType.SLIDER.value,
                display_name="Slider Joint",
                description="Linear translation along a single axis.",
                default_axis=(1.0, 0.0, 0.0),
                default_limit=JointLimit(
                    min_distance=-1.0,
                    max_distance=1.0,
                    enable_linear_limit=True,
                ),
                default_motor=MotorConfig(max_force=200.0),
                supports_motor=True,
                supports_limits=True,
                supports_breakable=True,
                degrees_of_freedom=1,
            ),
            JointTypeDescriptor(
                type_id="jt_cone_twist",
                joint_type=JointType.CONE_TWIST.value,
                display_name="Cone-Twist Joint",
                description="Cone-limited swing with an independent twist limit.",
                default_limit=JointLimit(
                    cone_limit=math.pi / 3.0,
                    twist_limit=math.pi / 4.0,
                    enable_angular_limit=True,
                ),
                supports_limits=True,
                supports_breakable=True,
                degrees_of_freedom=3,
            ),
            JointTypeDescriptor(
                type_id="jt_custom",
                joint_type=JointType.CUSTOM.value,
                display_name="Custom Joint",
                description="User-defined generic six-DOF constraint.",
                default_limit=JointLimit(enable_angular_limit=True, enable_linear_limit=True),
                supports_motor=True,
                supports_spring=True,
                supports_limits=True,
                supports_breakable=True,
                degrees_of_freedom=6,
            ),
        ]
        for descriptor in builtins:
            self._joint_types[descriptor.type_id] = descriptor
        self._stats.total_joint_types = len(self._joint_types)

    def register_joint_type(
        self,
        type_id: str,
        joint_type: JointType = JointType.CUSTOM,
        display_name: str = "",
        description: str = "",
        degrees_of_freedom: int = 6,
        supports_motor: bool = False,
        supports_spring: bool = False,
        supports_limits: bool = False,
        supports_breakable: bool = False,
    ) -> Tuple[bool, str, Optional[JointTypeDescriptor]]:
        """Register a new joint type template."""
        if isinstance(joint_type, str):
            try:
                joint_type = JointType(joint_type)
            except ValueError:
                return False, f"Unknown joint type '{joint_type}'", None
        if not type_id:
            return False, "Joint type id must not be empty", None
        if type_id in self._joint_types:
            return False, f"Joint type '{type_id}' already exists", None
        if len(self._joint_types) >= _MAX_JOINT_TYPES:
            return False, "Maximum joint type capacity reached", None
        descriptor = JointTypeDescriptor(
            type_id=type_id,
            joint_type=joint_type.value,
            display_name=display_name or type_id,
            description=description,
            supports_motor=supports_motor,
            supports_spring=supports_spring,
            supports_limits=supports_limits,
            supports_breakable=supports_breakable,
            degrees_of_freedom=degrees_of_freedom,
        )
        self._joint_types[type_id] = descriptor
        self._stats.total_joint_types = len(self._joint_types)
        self._emit(
            JointEventKind.JOINT_REGISTERED,
            {"type_id": type_id, "joint_type": joint_type.value},
        )
        return True, f"Registered joint type '{type_id}'", descriptor

    def get_joint_type(self, type_id: str) -> Optional[JointTypeDescriptor]:
        """Return a joint type descriptor by id, or None."""
        return self._joint_types.get(type_id)

    def list_joint_types(self) -> List[JointTypeDescriptor]:
        """Return all registered joint type descriptors."""
        return list(self._joint_types.values())

    def _descriptor_for(self, joint_type: JointType) -> Optional[JointTypeDescriptor]:
        """Find a descriptor matching a JointType enum value."""
        for descriptor in self._joint_types.values():
            if descriptor.joint_type == joint_type.value:
                return descriptor
        return None

    # ------------------------------------------------------------------
    # Joint registration and lookup
    # ------------------------------------------------------------------

    def register_joint(
        self,
        name: str = "",
        joint_type: JointType = JointType.HINGE,
        body_a_id: str = "",
        body_b_id: str = "",
        anchor_a: Optional[Tuple[float, float, float]] = None,
        anchor_b: Optional[Tuple[float, float, float]] = None,
        axis: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        mass_a: float = 1.0,
        mass_b: float = 1.0,
        type_id: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[PhysicsJoint]]:
        """Register a new joint instance connecting two bodies."""
        if isinstance(joint_type, str):
            try:
                joint_type = JointType(joint_type)
            except ValueError:
                return False, f"Unknown joint type '{joint_type}'", None

        if len(self._joints) >= self._config.max_joints:
            return False, "Maximum joint capacity reached", None

        descriptor = None
        if type_id:
            descriptor = self._joint_types.get(type_id)
            if descriptor is None:
                return False, f"Unknown joint type id '{type_id}'", None
        else:
            descriptor = self._descriptor_for(joint_type)
            if descriptor is None:
                # Fall back to a generic descriptor so registration succeeds.
                descriptor = JointTypeDescriptor(
                    type_id=f"jt_{joint_type.value}",
                    joint_type=joint_type.value,
                )

        self._joint_counter += 1
        joint = PhysicsJoint(
            name=name or f"joint_{self._joint_counter:04d}",
            joint_type=joint_type.value,
            constraint_type=ConstraintType.GENERIC.value,
            body_a=JointBody(body_id=body_a_id, mass=mass_a),
            body_b=JointBody(body_id=body_b_id, mass=mass_b),
            anchor_a=JointAnchor(
                body_id=body_a_id,
                local_offset=anchor_a or (0.0, 0.0, 0.0),
                world_position=anchor_a or (0.0, 0.0, 0.0),
            ),
            anchor_b=JointAnchor(
                body_id=body_b_id,
                local_offset=anchor_b or (0.0, 0.0, 0.0),
                world_position=anchor_b or (0.0, 0.0, 0.0),
            ),
            axis=_normalize3(axis),
            limit=JointLimit(
                min_angle=descriptor.default_limit.min_angle,
                max_angle=descriptor.default_limit.max_angle,
                min_distance=descriptor.default_limit.min_distance,
                max_distance=descriptor.default_limit.max_distance,
                twist_limit=descriptor.default_limit.twist_limit,
                cone_limit=descriptor.default_limit.cone_limit,
                enable_angular_limit=descriptor.default_limit.enable_angular_limit,
                enable_linear_limit=descriptor.default_limit.enable_linear_limit,
            ),
            motor=MotorConfig(
                mode=descriptor.default_motor.mode,
                max_torque=descriptor.default_motor.max_torque,
                max_force=descriptor.default_motor.max_force,
                enabled=False,
            ),
            spring=SpringConfig(
                stiffness=descriptor.default_spring.stiffness,
                damping=descriptor.default_spring.damping,
                rest_length=descriptor.default_spring.rest_length,
                min_length=descriptor.default_spring.min_length,
                max_length=descriptor.default_spring.max_length,
            ),
            break_threshold=BreakThreshold(
                condition=descriptor.default_break.condition,
                max_force=descriptor.default_break.max_force,
                max_torque=descriptor.default_break.max_torque,
                max_impulse=descriptor.default_break.max_impulse,
                max_stress=descriptor.default_break.max_stress,
                breakable=descriptor.default_break.breakable,
            ),
            solver_iterations=self._config.solver_iterations,
        )

        # Compute the initial distance between the two anchor points.
        joint.current_distance = _length3(
            _sub3(joint.anchor_a.world_position, joint.anchor_b.world_position)
        )

        self._joints[joint.joint_id] = joint
        self._stats.total_joints = len(self._joints)
        self._stats.active_joints += 1
        if joint.break_threshold.breakable:
            self._stats.total_breakable += 1
        if joint.joint_type == JointType.SPRING.value:
            self._stats.total_springs += 1

        self._emit(
            JointEventKind.JOINT_REGISTERED,
            {
                "name": joint.name,
                "joint_type": joint.joint_type,
                "body_a": body_a_id,
                "body_b": body_b_id,
            },
            joint_id=joint.joint_id,
        )
        return True, f"Registered joint '{joint.name}'", joint

    def remove_joint(self, joint_id: str) -> Tuple[bool, str]:
        """Remove a joint by id. Also detaches it from any chain."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found"

        # Detach from any chain that includes this joint.
        for chain in self._chains.values():
            if joint_id in chain.joint_ids:
                chain.joint_ids = [j for j in chain.joint_ids if j != joint_id]
                chain.updated_at = _now()
                if chain.root_joint_id == joint_id:
                    chain.root_joint_id = chain.joint_ids[0] if chain.joint_ids else ""
                if chain.tip_joint_id == joint_id:
                    chain.tip_joint_id = chain.joint_ids[-1] if chain.joint_ids else ""

        # Update aggregate stats.
        if joint.is_active():
            self._stats.active_joints -= 1
        if joint.status == JointStatus.BROKEN.value:
            self._stats.broken_joints -= 1
        if joint.status == JointStatus.LOCKED.value:
            self._stats.locked_joints -= 1
        if joint.status == JointStatus.DAMAGED.value:
            self._stats.damaged_joints -= 1
        if joint.break_threshold.breakable:
            self._stats.total_breakable -= 1
        if joint.joint_type == JointType.SPRING.value:
            self._stats.total_springs -= 1
        if joint.motor.enabled:
            self._stats.total_motors_enabled -= 1

        del self._joints[joint_id]
        self._stats.total_joints = len(self._joints)
        self._emit(
            JointEventKind.JOINT_REMOVED,
            {"name": joint.name},
            joint_id=joint_id,
        )
        return True, f"Removed joint '{joint.name}'"

    def get_joint(self, joint_id: str) -> Optional[PhysicsJoint]:
        """Return a joint by id, or None if not found."""
        return self._joints.get(joint_id)

    def list_joints(
        self, joint_type: Optional[JointType] = None, status: Optional[JointStatus] = None
    ) -> List[PhysicsJoint]:
        """Return joints, optionally filtered by type and/or status."""
        results: List[PhysicsJoint] = []
        for joint in self._joints.values():
            if joint_type is not None and joint.joint_type != joint_type.value:
                continue
            if status is not None and joint.status != status.value:
                continue
            results.append(joint)
        return results

    # ------------------------------------------------------------------
    # Motor configuration
    # ------------------------------------------------------------------

    def set_motor_config(
        self, joint_id: str, **kwargs: Any
    ) -> Tuple[bool, str, Optional[MotorConfig]]:
        """Update motor configuration fields for a joint."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found", None
        valid_fields = {
            "mode",
            "target_velocity",
            "max_torque",
            "max_force",
            "target_position",
            "servo_kp",
            "servo_kd",
            "acceleration",
            "enabled",
        }
        unknown = [k for k in kwargs if k not in valid_fields]
        if unknown:
            return False, f"Unknown motor fields: {', '.join(unknown)}", None
        for key, value in kwargs.items():
            setattr(joint.motor, key, value)
        joint.updated_at = _now()
        self._emit(
            JointEventKind.MOTOR_ENABLED if joint.motor.enabled else JointEventKind.MOTOR_DISABLED,
            {"fields": list(kwargs.keys())},
            joint_id=joint_id,
        )
        return True, f"Motor config updated for joint '{joint.name}'", joint.motor

    def get_motor_config(self, joint_id: str) -> Optional[MotorConfig]:
        """Return the motor configuration for a joint."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return None
        return joint.motor

    def enable_motor(
        self, joint_id: str, mode: MotorMode = MotorMode.VELOCITY, target_velocity: float = 0.0
    ) -> Tuple[bool, str]:
        """Enable the motor on a joint with the given mode and target."""
        if isinstance(mode, str):
            try:
                mode = MotorMode(mode)
            except ValueError:
                return False, f"Unknown motor mode '{mode}'"
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found"
        was_enabled = joint.motor.enabled
        joint.motor.enabled = True
        joint.motor.mode = mode.value
        joint.motor.target_velocity = target_velocity
        joint.updated_at = _now()
        if not was_enabled:
            self._stats.total_motors_enabled += 1
        self._emit(
            JointEventKind.MOTOR_ENABLED,
            {"mode": mode.value, "target_velocity": target_velocity},
            joint_id=joint_id,
        )
        return True, f"Motor enabled for joint '{joint.name}'"

    def disable_motor(self, joint_id: str) -> Tuple[bool, str]:
        """Disable the motor on a joint."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found"
        was_enabled = joint.motor.enabled
        joint.motor.enabled = False
        joint.motor.mode = MotorMode.OFF.value
        joint.updated_at = _now()
        if was_enabled:
            self._stats.total_motors_enabled -= 1
        self._emit(
            JointEventKind.MOTOR_DISABLED,
            {},
            joint_id=joint_id,
        )
        return True, f"Motor disabled for joint '{joint.name}'"

    # ------------------------------------------------------------------
    # Spring configuration
    # ------------------------------------------------------------------

    def set_spring_config(
        self, joint_id: str, **kwargs: Any
    ) -> Tuple[bool, str, Optional[SpringConfig]]:
        """Update spring configuration fields for a joint."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found", None
        valid_fields = {
            "stiffness",
            "damping",
            "rest_length",
            "min_length",
            "max_length",
            "enable_limit",
        }
        unknown = [k for k in kwargs if k not in valid_fields]
        if unknown:
            return False, f"Unknown spring fields: {', '.join(unknown)}", None
        for key, value in kwargs.items():
            setattr(joint.spring, key, value)
        # Ensure the rest length stays inside the limit range when limits are on.
        if joint.spring.enable_limit:
            joint.spring.rest_length = _clamp(
                joint.spring.rest_length,
                joint.spring.min_length,
                joint.spring.max_length,
            )
        joint.updated_at = _now()
        self._emit(
            JointEventKind.SPRING_CONFIGURED,
            {"fields": list(kwargs.keys())},
            joint_id=joint_id,
        )
        return True, f"Spring config updated for joint '{joint.name}'", joint.spring

    def get_spring_config(self, joint_id: str) -> Optional[SpringConfig]:
        """Return the spring configuration for a joint."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return None
        return joint.spring

    # ------------------------------------------------------------------
    # Joint limits
    # ------------------------------------------------------------------

    def set_joint_limit(
        self, joint_id: str, **kwargs: Any
    ) -> Tuple[bool, str, Optional[JointLimit]]:
        """Update joint limit fields for a joint."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found", None
        valid_fields = {
            "min_angle",
            "max_angle",
            "min_distance",
            "max_distance",
            "twist_limit",
            "cone_limit",
            "enable_angular_limit",
            "enable_linear_limit",
            "bounce",
            "softness",
        }
        unknown = [k for k in kwargs if k not in valid_fields]
        if unknown:
            return False, f"Unknown limit fields: {', '.join(unknown)}", None
        for key, value in kwargs.items():
            setattr(joint.limit, key, value)
        # Normalize the angular range so min <= max.
        if joint.limit.min_angle > joint.limit.max_angle:
            joint.limit.min_angle, joint.limit.max_angle = (
                joint.limit.max_angle,
                joint.limit.min_angle,
            )
        joint.updated_at = _now()
        self._emit(
            JointEventKind.LIMIT_SET,
            {"fields": list(kwargs.keys())},
            joint_id=joint_id,
        )
        return True, f"Limit updated for joint '{joint.name}'", joint.limit

    def get_joint_limit(self, joint_id: str) -> Optional[JointLimit]:
        """Return the limit configuration for a joint."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return None
        return joint.limit

    # ------------------------------------------------------------------
    # Breakable joints
    # ------------------------------------------------------------------

    def set_break_threshold(
        self, joint_id: str, **kwargs: Any
    ) -> Tuple[bool, str, Optional[BreakThreshold]]:
        """Update break threshold fields for a joint."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found", None
        valid_fields = {
            "condition",
            "max_force",
            "max_torque",
            "max_impulse",
            "max_stress",
            "max_angle",
            "max_distance",
            "breakable",
        }
        unknown = [k for k in kwargs if k not in valid_fields]
        if unknown:
            return False, f"Unknown break fields: {', '.join(unknown)}", None
        was_breakable = joint.break_threshold.breakable
        for key, value in kwargs.items():
            setattr(joint.break_threshold, key, value)
        if joint.break_threshold.breakable and not was_breakable:
            self._stats.total_breakable += 1
        elif not joint.break_threshold.breakable and was_breakable:
            self._stats.total_breakable -= 1
        joint.updated_at = _now()
        self._emit(
            JointEventKind.BREAK_THRESHOLD_SET,
            {"fields": list(kwargs.keys())},
            joint_id=joint_id,
        )
        return True, f"Break threshold updated for joint '{joint.name}'", joint.break_threshold

    def check_break_condition(self, joint_id: str) -> Tuple[bool, str, bool]:
        """Evaluate the break condition for a joint.

        Returns (success, message, should_break).
        """
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found", False
        if not joint.break_threshold.breakable:
            return True, "Joint is not breakable", False
        if not joint.is_active():
            return True, "Joint is not active", False

        threshold = joint.break_threshold
        condition = threshold.condition
        should_break = False
        reason = ""

        if condition == BreakCondition.FORCE.value:
            should_break = joint.current_force >= threshold.max_force
            reason = f"force {joint.current_force:.2f} >= {threshold.max_force:.2f}"
        elif condition == BreakCondition.TORQUE.value:
            should_break = joint.current_torque >= threshold.max_torque
            reason = f"torque {joint.current_torque:.2f} >= {threshold.max_torque:.2f}"
        elif condition == BreakCondition.IMPULSE.value:
            should_break = joint.current_impulse >= threshold.max_impulse
            reason = f"impulse {joint.current_impulse:.2f} >= {threshold.max_impulse:.2f}"
        elif condition == BreakCondition.STRESS.value:
            should_break = joint.current_stress >= threshold.max_stress
            reason = f"stress {joint.current_stress:.2f} >= {threshold.max_stress:.2f}"
        elif condition == BreakCondition.ANGLE.value:
            should_break = abs(joint.current_angle) >= threshold.max_angle
            reason = f"angle {joint.current_angle:.2f} >= {threshold.max_angle:.2f}"
        elif condition == BreakCondition.DISTANCE.value:
            should_break = joint.current_distance >= threshold.max_distance
            reason = f"distance {joint.current_distance:.2f} >= {threshold.max_distance:.2f}"
        else:
            # When no specific condition is set, use a combined check.
            should_break = (
                joint.current_force >= threshold.max_force
                or joint.current_torque >= threshold.max_torque
                or joint.current_stress >= threshold.max_stress
            )
            reason = "combined threshold exceeded"

        if should_break:
            return True, f"Break condition met: {reason}", True
        return True, "Break condition not met", False

    def break_joint(self, joint_id: str) -> Tuple[bool, str]:
        """Force-break a joint, moving it to the BROKEN status."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found"
        if joint.status == JointStatus.BROKEN.value:
            return True, f"Joint '{joint.name}' is already broken"
        was_active = joint.is_active()
        joint.status = JointStatus.BROKEN.value
        joint.updated_at = _now()
        if was_active:
            self._stats.active_joints -= 1
        self._stats.broken_joints += 1
        self._total_breaks += 1
        self._stats.total_breaks = self._total_breaks
        self._emit(
            JointEventKind.JOINT_BROKEN,
            {
                "force": joint.current_force,
                "torque": joint.current_torque,
                "stress": joint.current_stress,
            },
            joint_id=joint_id,
        )
        return True, f"Joint '{joint.name}' broken"

    def repair_joint(self, joint_id: str) -> Tuple[bool, str]:
        """Restore a broken or damaged joint to active status."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found"
        if joint.is_active():
            return True, f"Joint '{joint.name}' is already active"
        if joint.status == JointStatus.BROKEN.value:
            self._stats.broken_joints -= 1
        elif joint.status == JointStatus.LOCKED.value:
            self._stats.locked_joints -= 1
        elif joint.status == JointStatus.DAMAGED.value:
            self._stats.damaged_joints -= 1
        joint.status = JointStatus.ACTIVE.value
        joint.current_stress = 0.0
        joint.current_force = 0.0
        joint.current_torque = 0.0
        joint.current_impulse = 0.0
        joint.stress_history.clear()
        joint.updated_at = _now()
        self._stats.active_joints += 1
        self._emit(
            JointEventKind.JOINT_REPAIRED,
            {},
            joint_id=joint_id,
        )
        return True, f"Joint '{joint.name}' repaired"

    def lock_joint(self, joint_id: str) -> Tuple[bool, str]:
        """Lock a joint so it cannot move, without breaking it."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found"
        if joint.status == JointStatus.LOCKED.value:
            return True, f"Joint '{joint.name}' is already locked"
        was_active = joint.is_active()
        joint.status = JointStatus.LOCKED.value
        joint.updated_at = _now()
        if was_active:
            self._stats.active_joints -= 1
        self._stats.locked_joints += 1
        self._emit(
            JointEventKind.JOINT_LOCKED,
            {},
            joint_id=joint_id,
        )
        return True, f"Joint '{joint.name}' locked"

    def unlock_joint(self, joint_id: str) -> Tuple[bool, str]:
        """Unlock a previously locked joint."""
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found"
        if joint.status != JointStatus.LOCKED.value:
            return True, f"Joint '{joint.name}' is not locked"
        joint.status = JointStatus.ACTIVE.value
        joint.updated_at = _now()
        self._stats.locked_joints -= 1
        self._stats.active_joints += 1
        self._emit(
            JointEventKind.JOINT_UNLOCKED,
            {},
            joint_id=joint_id,
        )
        return True, f"Joint '{joint.name}' unlocked"

    # ------------------------------------------------------------------
    # Joint chains
    # ------------------------------------------------------------------

    def create_joint_chain(
        self,
        name: str,
        joint_ids: Optional[List[str]] = None,
        closed: bool = False,
        description: str = "",
    ) -> Tuple[bool, str, Optional[JointChain]]:
        """Create a new joint chain from a list of joint ids."""
        if not name:
            return False, "Chain name must not be empty", None
        if len(self._chains) >= self._config.max_chains:
            return False, "Maximum chain capacity reached", None

        # Validate that every joint id exists.
        validated: List[str] = []
        for jid in joint_ids or []:
            if jid not in self._joints:
                return False, f"Joint '{jid}' not found", None
            validated.append(jid)

        self._chain_counter += 1
        chain = JointChain(
            chain_id=f"chn_{self._chain_counter:04d}",
            name=name,
            joint_ids=validated,
            closed=closed,
            description=description,
        )
        if validated:
            chain.root_joint_id = validated[0]
            chain.tip_joint_id = validated[-1]

        # Tag each joint with its chain membership.
        for jid in validated:
            joint = self._joints.get(jid)
            if joint is not None:
                joint.chain_id = chain.chain_id

        self._chains[chain.chain_id] = chain
        self._stats.total_chains = len(self._chains)
        self._emit(
            JointEventKind.CHAIN_CREATED,
            {"name": name, "joint_count": len(validated), "closed": closed},
            chain_id=chain.chain_id,
        )
        return True, f"Created chain '{name}'", chain

    def add_to_chain(self, chain_id: str, joint_id: str, at_end: bool = True) -> Tuple[bool, str]:
        """Append (or prepend) a joint to an existing chain."""
        chain = self._chains.get(chain_id)
        if chain is None:
            return False, f"Chain '{chain_id}' not found"
        if joint_id not in self._joints:
            return False, f"Joint '{joint_id}' not found"
        if joint_id in chain.joint_ids:
            return False, f"Joint '{joint_id}' already in chain '{chain.name}'"
        if at_end:
            chain.joint_ids.append(joint_id)
            chain.tip_joint_id = joint_id
            if not chain.root_joint_id:
                chain.root_joint_id = joint_id
        else:
            chain.joint_ids.insert(0, joint_id)
            chain.root_joint_id = joint_id
            if not chain.tip_joint_id:
                chain.tip_joint_id = joint_id
        joint = self._joints[joint_id]
        joint.chain_id = chain.chain_id
        chain.updated_at = _now()
        self._emit(
            JointEventKind.CHAIN_JOINT_ADDED,
            {"joint_id": joint_id, "at_end": at_end},
            chain_id=chain_id,
        )
        return True, f"Added joint '{joint_id}' to chain '{chain.name}'"

    def remove_from_chain(self, chain_id: str, joint_id: str) -> Tuple[bool, str]:
        """Remove a joint from a chain."""
        chain = self._chains.get(chain_id)
        if chain is None:
            return False, f"Chain '{chain_id}' not found"
        if joint_id not in chain.joint_ids:
            return False, f"Joint '{joint_id}' not in chain '{chain.name}'"
        chain.joint_ids = [j for j in chain.joint_ids if j != joint_id]
        if chain.root_joint_id == joint_id:
            chain.root_joint_id = chain.joint_ids[0] if chain.joint_ids else ""
        if chain.tip_joint_id == joint_id:
            chain.tip_joint_id = chain.joint_ids[-1] if chain.joint_ids else ""
        joint = self._joints.get(joint_id)
        if joint is not None:
            joint.chain_id = ""
        chain.updated_at = _now()
        self._emit(
            JointEventKind.CHAIN_JOINT_REMOVED,
            {"joint_id": joint_id},
            chain_id=chain_id,
        )
        return True, f"Removed joint '{joint_id}' from chain '{chain.name}'"

    def get_joint_chain(self, chain_id: str) -> Optional[JointChain]:
        """Return a chain by id, or None."""
        return self._chains.get(chain_id)

    def list_joint_chains(self) -> List[JointChain]:
        """Return all registered joint chains."""
        return list(self._chains.values())

    # ------------------------------------------------------------------
    # AI parameter tuning
    # ------------------------------------------------------------------

    def ai_tune_parameters(
        self, joint_id: str, aggression: Optional[float] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Run an AI-driven heuristic tuning pass on a single joint.

        Adjusts stiffness, damping, motor torque, and spring rest length
        based on observed stress and stability metrics. The aggression
        parameter controls how far the optimizer is willing to move the
        values (0.0 = conservative, 1.0 = aggressive).
        """
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found", None

        agg = _clamp(
            aggression if aggression is not None else self._config.ai_tuning_aggression,
            0.0,
            1.0,
        )
        target_stability = self._config.ai_tuning_stability_target

        # Gather historical stress statistics.
        history = joint.stress_history or [joint.current_stress]
        avg_stress = sum(history) / len(history)
        peak_stress = max(history)
        variance = sum((s - avg_stress) ** 2 for s in history) / max(len(history), 1)
        stability = _clamp(1.0 - math.sqrt(variance) / (avg_stress + self.EPSILON), 0.0, 1.0)

        changes: Dict[str, Any] = {}

        # Tune spring stiffness and damping toward the stability target.
        if joint.joint_type in (JointType.SPRING.value, JointType.CUSTOM.value):
            old_stiffness = joint.spring.stiffness
            old_damping = joint.spring.damping
            # If the joint is too jittery (low stability), raise damping.
            if stability < target_stability:
                joint.spring.damping = old_damping * (1.0 + agg * 0.4)
            # If stress is consistently high, soften the spring.
            if avg_stress > 0.0 and peak_stress > avg_stress * 2.0:
                joint.spring.stiffness = old_stiffness * (1.0 - agg * 0.2)
            else:
                # If stress is low and stable, stiffen slightly for responsiveness.
                joint.spring.stiffness = old_stiffness * (1.0 + agg * 0.1)
            joint.spring.stiffness = max(1.0, joint.spring.stiffness)
            joint.spring.damping = max(0.1, joint.spring.damping)
            if abs(joint.spring.stiffness - old_stiffness) > self.EPSILON:
                changes["stiffness"] = {"from": old_stiffness, "to": joint.spring.stiffness}
            if abs(joint.spring.damping - old_damping) > self.EPSILON:
                changes["damping"] = {"from": old_damping, "to": joint.spring.damping}

        # Tune motor torque based on load.
        if joint.motor.enabled:
            old_torque = joint.motor.max_torque
            if avg_stress > old_torque * 0.8:
                joint.motor.max_torque = old_torque * (1.0 + agg * 0.3)
            elif avg_stress < old_torque * 0.2:
                joint.motor.max_torque = max(10.0, old_torque * (1.0 - agg * 0.1))
            if abs(joint.motor.max_torque - old_torque) > self.EPSILON:
                changes["max_torque"] = {"from": old_torque, "to": joint.motor.max_torque}

        # Tune solver iterations for high-stress joints.
        if peak_stress > 0.0 and avg_stress > 0.0:
            if peak_stress > avg_stress * 3.0 and joint.solver_iterations < 16:
                joint.solver_iterations += int(agg * 4) + 1
                changes["solver_iterations"] = joint.solver_iterations

        joint.updated_at = _now()
        self._total_ai_tunes += 1
        self._stats.total_ai_tunes = self._total_ai_tunes

        report = {
            "joint_id": joint_id,
            "aggression": round(agg, 4),
            "avg_stress": round(avg_stress, 4),
            "peak_stress": round(peak_stress, 4),
            "stability": round(stability, 4),
            "changes": changes,
        }
        self._emit(
            JointEventKind.AI_TUNED,
            report,
            joint_id=joint_id,
        )
        return True, f"AI tuning applied to joint '{joint.name}'", report

    def auto_balance_joint(
        self, joint_id: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Balance a joint so the two connected bodies share load evenly.

        Adjusts the inverse mass ratio and spring rest length so that
        neither body carries a disproportionate share of the constraint
        load. Useful for stabilizing articulated structures.
        """
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found", None

        body_a = joint.body_a
        body_b = joint.body_b

        # Compute a balanced mass ratio so neither side dominates.
        total_inverse = body_a.inverse_mass + body_b.inverse_mass
        if total_inverse < self.EPSILON:
            ratio_a = 0.5
            ratio_b = 0.5
        else:
            ratio_a = body_b.inverse_mass / total_inverse
            ratio_b = body_a.inverse_mass / total_inverse

        changes: Dict[str, Any] = {}

        # For spring joints, set the rest length to the current distance so
        # the joint settles into equilibrium rather than pulling.
        if joint.joint_type in (JointType.SPRING.value, JointType.CUSTOM.value):
            old_rest = joint.spring.rest_length
            joint.spring.rest_length = _clamp(
                joint.current_distance,
                joint.spring.min_length if joint.spring.enable_limit else 0.0,
                joint.spring.max_length if joint.spring.enable_limit else 1e9,
            )
            if abs(joint.spring.rest_length - old_rest) > self.EPSILON:
                changes["rest_length"] = {"from": old_rest, "to": joint.spring.rest_length}

        # Equalize damping to the average so both sides settle together.
        target_damping = (joint.spring.damping + joint.motor.servo_kd) / 2.0
        if joint.motor.enabled:
            old_kd = joint.motor.servo_kd
            joint.motor.servo_kd = target_damping
            changes["servo_kd"] = {"from": old_kd, "to": target_damping}

        joint.updated_at = _now()
        report = {
            "joint_id": joint_id,
            "load_ratio_a": round(ratio_a, 4),
            "load_ratio_b": round(ratio_b, 4),
            "balanced": True,
            "changes": changes,
        }
        self._emit(
            JointEventKind.AUTO_BALANCED,
            report,
            joint_id=joint_id,
        )
        return True, f"Auto-balanced joint '{joint.name}'", report

    def optimize_chain(
        self, chain_id: str, aggression: Optional[float] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Run AI tuning across every joint in a chain.

        Returns a summary of the per-joint tuning results plus a chain
        level stability score. Joints are tuned from root to tip so that
        upstream adjustments inform downstream parameters.
        """
        chain = self._chains.get(chain_id)
        if chain is None:
            return False, f"Chain '{chain_id}' not found", None
        if not chain.joint_ids:
            return False, f"Chain '{chain.name}' has no joints", None

        per_joint: List[Dict[str, Any]] = []
        stress_sum = 0.0
        stability_sum = 0.0
        tuned_count = 0

        for jid in chain.joint_ids:
            ok, msg, report = self.ai_tune_parameters(jid, aggression=aggression)
            if ok and report is not None:
                per_joint.append({"joint_id": jid, "report": report})
                stress_sum += report.get("avg_stress", 0.0)
                stability_sum += report.get("stability", 0.0)
                tuned_count += 1
            else:
                per_joint.append({"joint_id": jid, "error": msg})

        count = max(tuned_count, 1)
        summary = {
            "chain_id": chain_id,
            "chain_name": chain.name,
            "joints_tuned": tuned_count,
            "total_joints": len(chain.joint_ids),
            "avg_stress": round(stress_sum / count, 4),
            "avg_stability": round(stability_sum / count, 4),
            "per_joint": per_joint,
        }
        self._emit(
            JointEventKind.CHAIN_OPTIMIZED,
            summary,
            chain_id=chain_id,
        )
        return True, f"Optimized chain '{chain.name}'", summary

    # ------------------------------------------------------------------
    # Solver configuration
    # ------------------------------------------------------------------

    def set_solver_config(
        self,
        solver_type: Optional[SolverType] = None,
        iterations: Optional[int] = None,
        accuracy: Optional[float] = None,
        warm_starting: Optional[bool] = None,
        split_impulse: Optional[bool] = None,
        bias_factor: Optional[float] = None,
    ) -> Tuple[bool, str, JointConfig]:
        """Update the global constraint solver configuration."""
        if isinstance(solver_type, str):
            try:
                solver_type = SolverType(solver_type)
            except ValueError:
                return False, f"Unknown solver type '{solver_type}'", self._config
        changes: List[str] = []
        if solver_type is not None:
            self._config.solver_type = solver_type.value
            changes.append(f"solver_type={solver_type.value}")
        if iterations is not None:
            if iterations < 1:
                return False, "Solver iterations must be >= 1", self._config
            self._config.solver_iterations = iterations
            changes.append(f"iterations={iterations}")
        if accuracy is not None:
            if accuracy <= 0.0:
                return False, "Solver accuracy must be positive", self._config
            self._config.solver_accuracy = accuracy
            changes.append(f"accuracy={accuracy}")
        if warm_starting is not None:
            self._config.warm_starting = warm_starting
            changes.append(f"warm_starting={warm_starting}")
        if split_impulse is not None:
            self._config.split_impulse = split_impulse
            changes.append(f"split_impulse={split_impulse}")
        if bias_factor is not None:
            self._config.bias_factor = _clamp(bias_factor, 0.0, 1.0)
            changes.append(f"bias_factor={self._config.bias_factor}")

        # Propagate iteration count to all existing joints.
        if iterations is not None:
            for joint in self._joints.values():
                joint.solver_iterations = max(joint.solver_iterations, iterations)

        self._emit(
            JointEventKind.SOLVER_CONFIGURED,
            {"changes": changes},
        )
        return True, f"Solver config updated: {', '.join(changes)}", self._config

    def get_solver_config(self) -> JointConfig:
        """Return the current solver configuration."""
        return self._config

    # ------------------------------------------------------------------
    # Stress tracking
    # ------------------------------------------------------------------

    def compute_stress(self, joint_id: str) -> Tuple[bool, str, float]:
        """Compute and record the current stress on a joint.

        Stress is a combined metric derived from force, torque, and the
        deviation from the rest configuration. The value is pushed into
        the joint stress history for trend analysis.
        """
        joint = self._joints.get(joint_id)
        if joint is None:
            return False, f"Joint '{joint_id}' not found", 0.0
        if not joint.is_active():
            return True, "Joint not active, stress is zero", 0.0

        # Force component (normalized by max force capacity).
        force_component = joint.current_force / max(
            joint.break_threshold.max_force, self.EPSILON
        )
        # Torque component.
        torque_component = joint.current_torque / max(
            joint.break_threshold.max_torque, self.EPSILON
        )
        # Distance deviation from rest length for springs.
        distance_deviation = 0.0
        if joint.joint_type in (JointType.SPRING.value, JointType.CUSTOM.value):
            rest = joint.spring.rest_length
            distance_deviation = abs(joint.current_distance - rest) / max(rest, self.EPSILON)
        # Angular deviation from the center of the limit range.
        angle_center = (joint.limit.min_angle + joint.limit.max_angle) / 2.0
        angle_half = max(
            (joint.limit.max_angle - joint.limit.min_angle) / 2.0,
            self.EPSILON,
        )
        angular_deviation = abs(joint.current_angle - angle_center) / angle_half

        # Weighted combination of all components.
        stress = (
            0.35 * force_component
            + 0.25 * torque_component
            + 0.20 * distance_deviation
            + 0.20 * angular_deviation
        )
        stress = max(0.0, stress)

        if self._config.enable_stress_tracking:
            joint.record_stress(stress)
            self._total_stress_samples += 1
            self._stress_sum += stress
            if stress > self._peak_stress:
                self._peak_stress = stress
            self._stats.total_stress_samples = self._total_stress_samples
            self._stats.average_stress = self._stress_sum / max(self._total_stress_samples, 1)
            self._stats.peak_stress = self._peak_stress

        self._emit(
            JointEventKind.STRESS_COMPUTED,
            {
                "stress": round(stress, 6),
                "force_component": round(force_component, 6),
                "torque_component": round(torque_component, 6),
                "distance_deviation": round(distance_deviation, 6),
                "angular_deviation": round(angular_deviation, 6),
            },
            joint_id=joint_id,
        )
        return True, f"Stress computed for joint '{joint.name}'", stress

    def get_stress_report(self, joint_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a stress report for one joint or the whole system."""
        if joint_id is not None:
            joint = self._joints.get(joint_id)
            if joint is None:
                return {"error": f"Joint '{joint_id}' not found"}
            history = joint.stress_history
            avg = sum(history) / len(history) if history else 0.0
            peak = max(history) if history else 0.0
            return {
                "joint_id": joint_id,
                "name": joint.name,
                "current_stress": round(joint.current_stress, 6),
                "average_stress": round(avg, 6),
                "peak_stress": round(peak, 6),
                "samples": len(history),
                "status": joint.status,
                "breakable": joint.break_threshold.breakable,
                "break_condition": joint.break_threshold.condition,
                "max_stress": joint.break_threshold.max_stress,
            }

        # System-wide report.
        per_joint: List[Dict[str, Any]] = []
        total_stress = 0.0
        peak = 0.0
        for jid, joint in self._joints.items():
            if not joint.is_active():
                continue
            total_stress += joint.current_stress
            if joint.current_stress > peak:
                peak = joint.current_stress
            per_joint.append(
                {
                    "joint_id": jid,
                    "name": joint.name,
                    "current_stress": round(joint.current_stress, 6),
                    "status": joint.status,
                }
            )
        active_count = sum(1 for j in self._joints.values() if j.is_active())
        return {
            "total_joints": len(self._joints),
            "active_joints": active_count,
            "average_stress": round(total_stress / max(active_count, 1), 6),
            "peak_stress": round(peak, 6),
            "system_average_stress": round(self._stats.average_stress, 6),
            "system_peak_stress": round(self._stats.peak_stress, 6),
            "total_samples": self._stats.total_stress_samples,
            "joints": per_joint,
        }

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------

    def get_visualization_data(
        self, joint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return debug visualization data for one joint or all joints."""
        joints_to_render: List[PhysicsJoint] = []
        if joint_id is not None:
            joint = self._joints.get(joint_id)
            if joint is None:
                return {"error": f"Joint '{joint_id}' not found"}
            joints_to_render.append(joint)
        else:
            joints_to_render = list(self._joints.values())

        segments: List[Dict[str, Any]] = []
        anchors: List[Dict[str, Any]] = []
        axes: List[Dict[str, Any]] = []
        limits: List[Dict[str, Any]] = []
        for joint in joints_to_render:
            color = {
                JointStatus.ACTIVE.value: (0.2, 0.8, 0.2),
                JointStatus.INACTIVE.value: (0.5, 0.5, 0.5),
                JointStatus.BROKEN.value: (0.9, 0.1, 0.1),
                JointStatus.LOCKED.value: (0.9, 0.7, 0.1),
                JointStatus.DAMAGED.value: (0.9, 0.5, 0.1),
            }.get(joint.status, (0.8, 0.8, 0.8))

            segments.append(
                {
                    "joint_id": joint.joint_id,
                    "name": joint.name,
                    "joint_type": joint.joint_type,
                    "from": list(joint.anchor_a.world_position),
                    "to": list(joint.anchor_b.world_position),
                    "color": color,
                    "status": joint.status,
                    "stress": round(joint.current_stress, 4),
                }
            )
            anchors.append(
                {
                    "joint_id": joint.joint_id,
                    "anchor_a": list(joint.anchor_a.world_position),
                    "anchor_b": list(joint.anchor_b.world_position),
                }
            )
            # Draw the joint axis scaled by the current stress.
            axis_end = _add3(
                joint.anchor_a.world_position,
                _scale3(joint.axis, 0.5 + joint.current_stress),
            )
            axes.append(
                {
                    "joint_id": joint.joint_id,
                    "origin": list(joint.anchor_a.world_position),
                    "end": list(axis_end),
                    "axis": list(joint.axis),
                }
            )
            if joint.limit.enable_angular_limit or joint.limit.enable_linear_limit:
                limits.append(
                    {
                        "joint_id": joint.joint_id,
                        "min_angle": joint.limit.min_angle,
                        "max_angle": joint.limit.max_angle,
                        "min_distance": joint.limit.min_distance,
                        "max_distance": joint.limit.max_distance,
                        "enable_angular": joint.limit.enable_angular_limit,
                        "enable_linear": joint.limit.enable_linear_limit,
                    }
                )

        return {
            "joint_count": len(joints_to_render),
            "segments": segments,
            "anchors": anchors,
            "axes": axes,
            "limits": limits,
            "chains": [
                {
                    "chain_id": c.chain_id,
                    "name": c.name,
                    "joint_ids": list(c.joint_ids),
                    "closed": c.closed,
                }
                for c in self._chains.values()
            ],
        }

    # ------------------------------------------------------------------
    # Simulation tick
    # ------------------------------------------------------------------

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance the joint system by dt seconds of simulated time.

        For each active joint the system computes the current force,
        torque, distance, and angle from the connected body states,
        evaluates the break condition, and records stress. Motors and
        springs apply their configured forces. Returns a summary dict.
        """
        if dt <= 0:
            return {"tick": self._tick_count, "skipped": True, "reason": "dt <= 0"}

        self._tick_count += 1
        self._stats.tick_count = self._tick_count

        stress_computed = 0
        breaks_detected = 0
        motors_evaluated = 0
        springs_evaluated = 0
        solver_iterations_total = 0

        for joint in list(self._joints.values()):
            if not joint.is_active():
                continue

            # Update the current distance from anchor positions.
            delta = _sub3(joint.anchor_a.world_position, joint.anchor_b.world_position)
            joint.current_distance = _length3(delta)

            # Update the current angle from the axis and delta vectors.
            if _length3(delta) > self.EPSILON:
                joint.current_angle = _angle_between(delta, joint.axis)

            # Apply spring forces if a spring is configured.
            if joint.joint_type in (JointType.SPRING.value, JointType.CUSTOM.value):
                rel_vel = _length3(
                    _sub3(joint.body_a.velocity, joint.body_b.velocity)
                )
                spring_force = joint.spring.compute_spring_force(
                    joint.current_distance, rel_vel
                )
                joint.current_force = abs(spring_force)
                springs_evaluated += 1

            # Apply motor forces if the motor is enabled.
            if joint.motor.enabled:
                motor_force = self._evaluate_motor(joint, dt)
                joint.current_torque = abs(motor_force)
                motors_evaluated += 1

            # Accumulate impulse from force and torque over the timestep.
            joint.current_impulse = (
                joint.current_force * dt + joint.current_torque * dt
            )

            # Run the configured solver iterations.
            for _ in range(joint.solver_iterations):
                solver_iterations_total += 1
                # In a full engine this would solve the constraint equations;
                # here we apply a bias correction toward the rest configuration.
                self._apply_solver_step(joint, dt)

            # Compute and record stress.
            ok, _, stress = self.compute_stress(joint.joint_id)
            if ok:
                stress_computed += 1

            # Evaluate break conditions for breakable joints.
            if joint.break_threshold.breakable:
                ok_b, _, should_break = self.check_break_condition(joint.joint_id)
                if ok_b and should_break:
                    self.break_joint(joint.joint_id)
                    breaks_detected += 1

            joint.updated_at = _now()

        # Recompute aggregate stats.
        self._stats.active_joints = sum(1 for j in self._joints.values() if j.is_active())
        self._stats.broken_joints = sum(
            1 for j in self._joints.values() if j.status == JointStatus.BROKEN.value
        )
        self._stats.locked_joints = sum(
            1 for j in self._joints.values() if j.status == JointStatus.LOCKED.value
        )
        self._stats.damaged_joints = sum(
            1 for j in self._joints.values() if j.status == JointStatus.DAMAGED.value
        )
        self._stats.total_motors_enabled = sum(
            1 for j in self._joints.values() if j.motor.enabled
        )

        summary = {
            "tick": self._tick_count,
            "dt": dt,
            "active_joints": self._stats.active_joints,
            "stress_computed": stress_computed,
            "breaks_detected": breaks_detected,
            "motors_evaluated": motors_evaluated,
            "springs_evaluated": springs_evaluated,
            "solver_iterations": solver_iterations_total,
            "average_stress": round(self._stats.average_stress, 6),
            "peak_stress": round(self._stats.peak_stress, 6),
        }
        self._emit(JointEventKind.TICK, summary)
        return summary

    def _evaluate_motor(self, joint: PhysicsJoint, dt: float) -> float:
        """Compute the motor force/torque for this timestep."""
        mode = joint.motor.mode
        if mode == MotorMode.OFF.value:
            return 0.0
        if mode == MotorMode.FORCE.value:
            return joint.motor.max_force
        if mode == MotorMode.VELOCITY.value:
            current_vel = _length3(joint.body_a.angular_velocity)
            error = joint.motor.target_velocity - current_vel
            force = _clamp(
                error * joint.motor.max_torque,
                -joint.motor.max_torque,
                joint.motor.max_torque,
            )
            return force
        if mode == MotorMode.POSITION.value:
            target = joint.motor.target_position
            error = target - joint.current_angle
            force = _clamp(
                error * joint.motor.servo_kp * joint.motor.max_torque,
                -joint.motor.max_torque,
                joint.motor.max_torque,
            )
            return force
        if mode == MotorMode.SERVO.value:
            target = joint.motor.target_position
            pos_error = target - joint.current_angle
            current_vel = _length3(joint.body_a.angular_velocity)
            vel_error = joint.motor.target_velocity - current_vel
            force = _clamp(
                pos_error * joint.motor.servo_kp + vel_error * joint.motor.servo_kd,
                -joint.motor.max_torque,
                joint.motor.max_torque,
            )
            return force
        return 0.0

    def _apply_solver_step(self, joint: PhysicsJoint, dt: float) -> None:
        """Apply one solver iteration of constraint correction.

        This is a simplified sequential-impulse style correction that
        pushes the two anchors toward each other along the constraint
        axis proportional to the inverse mass ratio.
        """
        body_a = joint.body_a
        body_b = joint.body_b
        total_inverse = body_a.inverse_mass + body_b.inverse_mass
        if total_inverse < self.EPSILON:
            return

        delta = _sub3(joint.anchor_b.world_position, joint.anchor_a.world_position)
        distance = _length3(delta)
        if distance < self.EPSILON:
            return

        # Compute the positional error and a bias-corrected impulse.
        direction = _normalize3(delta)
        # For springs, the target distance is the rest length; for others
        # the target is zero (rigid connection).
        if joint.joint_type in (JointType.SPRING.value, JointType.CUSTOM.value):
            target_distance = joint.spring.rest_length
        else:
            target_distance = 0.0
        error = distance - target_distance
        bias = error * self._config.bias_factor / max(dt, self.EPSILON)
        impulse_magnitude = -(error + bias * dt) / total_inverse
        impulse = _scale3(direction, impulse_magnitude)

        # Apply the impulse to the body positions (positional correction).
        correction_a = _scale3(impulse, body_a.inverse_mass)
        correction_b = _scale3(impulse, body_b.inverse_mass)
        joint.anchor_a.world_position = _add3(
            joint.anchor_a.world_position, correction_a
        )
        joint.anchor_b.world_position = _sub3(
            joint.anchor_b.world_position, correction_b
        )

        # Apply angular limits when enabled.
        if joint.limit.enable_angular_limit:
            joint.current_angle = joint.limit.clamp_angle(joint.current_angle)
        if joint.limit.enable_linear_limit:
            joint.current_distance = joint.limit.clamp_distance(joint.current_distance)

    # ------------------------------------------------------------------
    # Stats, snapshot, status, config
    # ------------------------------------------------------------------

    def get_stats(self) -> JointStats:
        """Return rolled-up statistics for the system."""
        self._stats.total_joints = len(self._joints)
        self._stats.total_chains = len(self._chains)
        self._stats.total_joint_types = len(self._joint_types)
        self._stats.active_joints = sum(1 for j in self._joints.values() if j.is_active())
        self._stats.broken_joints = sum(
            1 for j in self._joints.values() if j.status == JointStatus.BROKEN.value
        )
        self._stats.locked_joints = sum(
            1 for j in self._joints.values() if j.status == JointStatus.LOCKED.value
        )
        self._stats.damaged_joints = sum(
            1 for j in self._joints.values() if j.status == JointStatus.DAMAGED.value
        )
        self._stats.total_motors_enabled = sum(
            1 for j in self._joints.values() if j.motor.enabled
        )
        self._stats.total_springs = sum(
            1 for j in self._joints.values() if j.joint_type == JointType.SPRING.value
        )
        self._stats.total_breakable = sum(
            1 for j in self._joints.values() if j.break_threshold.breakable
        )
        return self._stats

    def get_snapshot(self) -> JointSnapshot:
        """Return a point-in-time snapshot of the whole system."""
        return JointSnapshot(
            joints=[j.to_dict() for j in self._joints.values()],
            chains=[c.to_dict() for c in self._chains.values()],
            joint_types=[t.to_dict() for t in self._joint_types.values()],
            stats=self.get_stats().to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def get_status(self) -> Dict[str, Any]:
        """Return a concise status report for monitoring."""
        return {
            "initialized": self._seeded,
            "tick_count": self._tick_count,
            "joint_count": len(self._joints),
            "active_joints": sum(1 for j in self._joints.values() if j.is_active()),
            "broken_joints": sum(
                1 for j in self._joints.values() if j.status == JointStatus.BROKEN.value
            ),
            "chain_count": len(self._chains),
            "joint_type_count": len(self._joint_types),
            "motors_enabled": sum(1 for j in self._joints.values() if j.motor.enabled),
            "breakable_joints": sum(
                1 for j in self._joints.values() if j.break_threshold.breakable
            ),
            "total_breaks": self._total_breaks,
            "total_ai_tunes": self._total_ai_tunes,
            "average_stress": round(self._stats.average_stress, 6),
            "peak_stress": round(self._stats.peak_stress, 6),
            "solver_type": self._config.solver_type,
            "solver_iterations": self._config.solver_iterations,
        }

    def get_config(self) -> JointConfig:
        """Return the current configuration."""
        return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, JointConfig]:
        """Update one or more configuration fields by keyword."""
        valid_fields = {
            "solver_type",
            "solver_iterations",
            "solver_accuracy",
            "global_damping",
            "global_air_drag",
            "enable_breakable_joints",
            "enable_stress_tracking",
            "enable_visualization",
            "max_joints",
            "max_chains",
            "ai_tuning_aggression",
            "ai_tuning_stability_target",
            "warm_starting",
            "split_impulse",
            "bias_factor",
        }
        unknown = [k for k in kwargs if k not in valid_fields]
        if unknown:
            return False, f"Unknown config fields: {', '.join(unknown)}", self._config
        for key, value in kwargs.items():
            if key == "solver_iterations":
                value = max(1, _safe_int(value, self._config.solver_iterations))
            elif key == "max_joints":
                value = max(1, _safe_int(value, self._config.max_joints))
            elif key == "max_chains":
                value = max(1, _safe_int(value, self._config.max_chains))
            elif key in (
                "solver_accuracy",
                "global_damping",
                "global_air_drag",
                "ai_tuning_aggression",
                "ai_tuning_stability_target",
                "bias_factor",
            ):
                value = _safe_float(value, getattr(self._config, key))
            elif key in (
                "enable_breakable_joints",
                "enable_stress_tracking",
                "enable_visualization",
                "warm_starting",
                "split_impulse",
            ):
                value = bool(value)
            elif key == "solver_type":
                if isinstance(value, SolverType):
                    value = value.value
                elif isinstance(value, str):
                    # Accept raw string values that match a SolverType.
                    pass
            setattr(self._config, key, value)
        self._emit(
            JointEventKind.CONFIG_UPDATED,
            {"fields": list(kwargs.keys())},
        )
        return True, f"Config updated: {len(kwargs)} field(s)", self._config

    def list_events(
        self, kind: Optional[JointEventKind] = None, limit: Optional[int] = None
    ) -> List[JointEvent]:
        """Return recorded events, optionally filtered by kind."""
        events = self._events
        if kind is not None:
            events = [e for e in events if e.kind == kind.value]
        if limit is not None and limit > 0:
            events = events[-limit:]
        return list(events)

    def reset(self) -> Tuple[bool, str]:
        """Clear all joints, chains, and events, keeping joint types."""
        self._joints.clear()
        self._chains.clear()
        self._events.clear()
        self._stats = JointStats()
        self._tick_count = 0
        self._event_counter = 0
        self._joint_counter = 0
        self._chain_counter = 0
        self._total_breaks = 0
        self._total_ai_tunes = 0
        self._total_stress_samples = 0
        self._peak_stress = 0.0
        self._stress_sum = 0.0
        self._stats.total_joint_types = len(self._joint_types)
        self._emit(JointEventKind.RESET, {})
        return True, "System reset complete"

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _load_seed_joints(self) -> None:
        """Create five sample joints demonstrating the joint types."""
        # Joint 1: Hinge connecting a wall to a door.
        ok, _, hinge = self.register_joint(
            name="seed_door_hinge",
            joint_type=JointType.HINGE,
            body_a_id="seed_wall_01",
            body_b_id="seed_door_01",
            anchor_a=(0.0, 1.0, 0.0),
            anchor_b=(0.0, 1.0, 0.0),
            axis=(0.0, 1.0, 0.0),
            mass_a=0.0,
            mass_b=15.0,
        )
        if ok and hinge is not None:
            self.set_joint_limit(
                hinge.joint_id,
                min_angle=-math.pi / 2.0,
                max_angle=math.pi / 2.0,
                enable_angular_limit=True,
            )
            self.set_break_threshold(
                hinge.joint_id,
                condition=BreakCondition.TORQUE.value,
                max_torque=500.0,
                breakable=True,
            )
            self.enable_motor(hinge.joint_id, MotorMode.VELOCITY, target_velocity=0.5)

        # Joint 2: Spring connecting two crates.
        ok, _, spring = self.register_joint(
            name="seed_crate_spring",
            joint_type=JointType.SPRING,
            body_a_id="seed_crate_01",
            body_b_id="seed_crate_02",
            anchor_a=(1.0, 0.5, 0.0),
            anchor_b=(-1.0, 0.5, 0.0),
            mass_a=10.0,
            mass_b=10.0,
        )
        if ok and spring is not None:
            self.set_spring_config(
                spring.joint_id,
                stiffness=80.0,
                damping=6.0,
                rest_length=2.0,
                min_length=0.5,
                max_length=4.0,
                enable_limit=True,
            )
            self.set_break_threshold(
                spring.joint_id,
                condition=BreakCondition.DISTANCE.value,
                max_distance=5.0,
                breakable=True,
            )

        # Joint 3: Piston for a hydraulic arm.
        ok, _, piston = self.register_joint(
            name="seed_hydraulic_piston",
            joint_type=JointType.PISTON,
            body_a_id="seed_piston_base",
            body_b_id="seed_piston_rod",
            anchor_a=(0.0, 0.0, 0.0),
            anchor_b=(0.0, 0.0, 0.0),
            axis=(0.0, 1.0, 0.0),
            mass_a=50.0,
            mass_b=5.0,
        )
        if ok and piston is not None:
            self.set_joint_limit(
                piston.joint_id,
                min_distance=0.2,
                max_distance=1.5,
                enable_linear_limit=True,
            )
            self.set_motor_config(
                piston.joint_id,
                mode=MotorMode.VELOCITY.value,
                target_velocity=0.3,
                max_force=400.0,
                enabled=True,
            )

        # Joint 4: Ball-socket for a character shoulder.
        ok, _, ball = self.register_joint(
            name="seed_shoulder_ball",
            joint_type=JointType.BALL_SOCKET,
            body_a_id="seed_torso_01",
            body_b_id="seed_upper_arm_01",
            anchor_a=(0.2, 0.5, 0.0),
            anchor_b=(0.0, 0.0, 0.0),
            mass_a=30.0,
            mass_b=3.0,
        )
        if ok and ball is not None:
            self.set_joint_limit(
                ball.joint_id,
                cone_limit=math.pi / 2.5,
                twist_limit=math.pi / 3.0,
                enable_angular_limit=True,
            )
            self.set_break_threshold(
                ball.joint_id,
                condition=BreakCondition.STRESS.value,
                max_stress=0.9,
                breakable=True,
            )

        # Joint 5: Fixed weld joining two metal plates.
        ok, _, fixed = self.register_joint(
            name="seed_plate_weld",
            joint_type=JointType.FIXED,
            body_a_id="seed_plate_01",
            body_b_id="seed_plate_02",
            anchor_a=(0.5, 0.0, 0.0),
            anchor_b=(-0.5, 0.0, 0.0),
            mass_a=20.0,
            mass_b=20.0,
        )
        if ok and fixed is not None:
            self.set_break_threshold(
                fixed.joint_id,
                condition=BreakCondition.FORCE.value,
                max_force=5000.0,
                breakable=True,
            )

    def _load_seed_chains(self) -> None:
        """Create three sample joint chains for ragdolls, ropes, and linkages."""
        # Build a small ragdoll-style spine chain from new joints.
        spine_joints: List[str] = []
        spine_segments = [
            ("seed_pelvis", "seed_spine_l1", (0.0, 0.1, 0.0)),
            ("seed_spine_l1", "seed_spine_l2", (0.0, 0.25, 0.0)),
            ("seed_spine_l2", "seed_chest", (0.0, 0.4, 0.0)),
            ("seed_chest", "seed_neck", (0.0, 0.55, 0.0)),
            ("seed_neck", "seed_head", (0.0, 0.7, 0.0)),
        ]
        prev_id = ""
        for i, (body_a, body_b, anchor) in enumerate(spine_segments):
            ok, _, joint = self.register_joint(
                name=f"seed_spine_chain_{i:02d}",
                joint_type=JointType.CONE_TWIST if i < 4 else JointType.BALL_SOCKET,
                body_a_id=body_a,
                body_b_id=body_b,
                anchor_a=anchor,
                anchor_b=(0.0, 0.0, 0.0),
                axis=(0.0, 1.0, 0.0),
                mass_a=10.0 - i,
                mass_b=max(1.0, 8.0 - i),
            )
            if ok and joint is not None:
                self.set_joint_limit(
                    joint.joint_id,
                    cone_limit=math.pi / 4.0,
                    twist_limit=math.pi / 6.0,
                    enable_angular_limit=True,
                )
                spine_joints.append(joint.joint_id)
                prev_id = joint.joint_id
        if spine_joints:
            self.create_joint_chain(
                name="seed_ragdoll_spine",
                joint_ids=spine_joints,
                closed=False,
                description="Articulated spine chain for a humanoid ragdoll.",
            )

        # Build a rope chain from a sequence of spring joints.
        rope_joints: List[str] = []
        rope_segments = 6
        for i in range(rope_segments):
            ok, _, joint = self.register_joint(
                name=f"seed_rope_segment_{i:02d}",
                joint_type=JointType.SPRING,
                body_a_id=f"seed_rope_node_{i:02d}",
                body_b_id=f"seed_rope_node_{i + 1:02d}",
                anchor_a=(0.0, -0.25 * i, 0.0),
                anchor_b=(0.0, -0.25 * (i + 1), 0.0),
                mass_a=0.5,
                mass_b=0.5,
            )
            if ok and joint is not None:
                self.set_spring_config(
                    joint.joint_id,
                    stiffness=200.0,
                    damping=2.0,
                    rest_length=0.25,
                    min_length=0.2,
                    max_length=0.35,
                    enable_limit=True,
                )
                self.set_break_threshold(
                    joint.joint_id,
                    condition=BreakCondition.FORCE.value,
                    max_force=50.0,
                    breakable=True,
                )
                rope_joints.append(joint.joint_id)
        if rope_joints:
            self.create_joint_chain(
                name="seed_rope_chain",
                joint_ids=rope_joints,
                closed=False,
                description="Six-segment rope built from damped spring joints.",
            )

        # Build a closed mechanical linkage from slider joints.
        linkage_joints: List[str] = []
        linkage_count = 4
        for i in range(linkage_count):
            ok, _, joint = self.register_joint(
                name=f"seed_linkage_{i:02d}",
                joint_type=JointType.SLIDER,
                body_a_id=f"seed_link_bar_{i:02d}",
                body_b_id=f"seed_link_bar_{(i + 1) % linkage_count:02d}",
                anchor_a=(0.5, 0.0, 0.0),
                anchor_b=(-0.5, 0.0, 0.0),
                axis=(1.0, 0.0, 0.0),
                mass_a=5.0,
                mass_b=5.0,
            )
            if ok and joint is not None:
                self.set_joint_limit(
                    joint.joint_id,
                    min_distance=-0.3,
                    max_distance=0.3,
                    enable_linear_limit=True,
                )
                self.enable_motor(joint.joint_id, MotorMode.POSITION, target_velocity=0.0)
                linkage_joints.append(joint.joint_id)
        if linkage_joints:
            self.create_joint_chain(
                name="seed_closed_linkage",
                joint_ids=linkage_joints,
                closed=True,
                description="Closed four-bar mechanical linkage driven by slider motors.",
            )


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------

def get_physics_joint_constraint_system() -> PhysicsJointConstraintSystem:
    """Return the singleton PhysicsJointConstraintSystem instance.

    On first call the system is automatically initialized with seed
    data so callers receive a ready-to-use system without an explicit
    initialize() call.
    """
    inst = PhysicsJointConstraintSystem.get_instance()
    if not getattr(inst, "_seeded", False):
        inst.initialize()
    return inst
