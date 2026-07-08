"""
SparkLabs Engine - Ragdoll Physics System

Simulates articulated character bodies as connected rigid segments
linked by constrained joints. Activated on death, impact, or scripted
events to produce natural falling and slumping motion.

Each ragdoll consists of bone segments (head, torso, limbs) connected
by joints with angular limits, gravity response, ground collision,
and external impulse application. Designed for character death
sequences, impact reactions, and physical comedy effects.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> float:
    return time.time()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _length3(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _normalize3(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    n = _length3(v)
    if n < 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _add3(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub3(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale3(v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * _clamp(t, 0.0, 1.0)


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_RAGDOLLS = 500
_MAX_BONES = 16000
_MAX_JOINTS = 32000
_MAX_IMPULSES = 5000
_MAX_EVENTS = 5000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BoneType(str, Enum):
    """Type of bone in the ragdoll skeleton."""
    HEAD = "head"
    NECK = "neck"
    CHEST = "chest"
    PELVIS = "pelvis"
    UPPER_ARM_L = "upper_arm_l"
    UPPER_ARM_R = "upper_arm_r"
    LOWER_ARM_L = "lower_arm_l"
    LOWER_ARM_R = "lower_arm_r"
    HAND_L = "hand_l"
    HAND_R = "hand_r"
    UPPER_LEG_L = "upper_leg_l"
    UPPER_LEG_R = "upper_leg_r"
    LOWER_LEG_L = "lower_leg_l"
    LOWER_LEG_R = "lower_leg_r"
    FOOT_L = "foot_l"
    FOOT_R = "foot_r"
    SPINE = "spine"
    CUSTOM = "custom"


class JointType(str, Enum):
    """Type of joint connecting two bones."""
    BALL = "ball"
    HINGE = "hinge"
    CONE = "cone"
    FIXED = "fixed"
    TWIST = "twist"


class RagdollState(str, Enum):
    """Operational state of a ragdoll instance."""
    ACTIVE = "active"
    SETTLED = "settled"
    REMOVED = "removed"
    FROZEN = "frozen"


class RagdollEventKind(str, Enum):
    RAGDOLL_CREATED = "ragdoll_created"
    RAGDOLL_REMOVED = "ragdoll_removed"
    RAGDOLL_FROZEN = "ragdoll_frozen"
    RAGDOLL_SETTLED = "ragdoll_settled"
    IMPULSE_APPLIED = "impulse_applied"
    BONE_COLLISION = "bone_collision"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class BoneSpec:
    """Specification of a single ragdoll bone segment."""
    bone_id: str
    bone_type: str = BoneType.CUSTOM.value
    parent_id: str = ""
    mass: float = 5.0
    radius: float = 0.08
    length: float = 0.4
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    grounded: bool = False
    friction: float = 0.6
    restitution: float = 0.2

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class JointSpec:
    """Specification of a constrained joint between two bones."""
    joint_id: str
    joint_type: str = JointType.CONE.value
    parent_bone_id: str = ""
    child_bone_id: str = ""
    anchor: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    min_angle: float = -45.0
    max_angle: float = 45.0
    twist_limit: float = 30.0
    stiffness: float = 0.8
    damping: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RagdollProfile:
    """A complete ragdoll instance with bones and joints."""
    ragdoll_id: str
    name: str = ""
    entity_id: str = ""
    bones: Dict[str, BoneSpec] = field(default_factory=dict)
    joints: Dict[str, JointSpec] = field(default_factory=dict)
    state: str = RagdollState.ACTIVE.value
    gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    air_drag: float = 0.02
    ground_friction: float = 0.6
    ground_y: float = 0.0
    settle_threshold: float = 0.3
    settle_time: float = 2.0
    elapsed: float = 0.0
    low_motion_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ImpulseRequest:
    """An external impulse applied to a ragdoll bone."""
    impulse_id: str
    ragdoll_id: str
    bone_id: str
    force: Tuple[float, float, float]
    application_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RagdollConfig:
    max_ragdolls: int = 200
    max_bones_per_ragdoll: int = 32
    gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    air_drag: float = 0.02
    ground_friction: float = 0.6
    restitution: float = 0.2
    settle_threshold: float = 0.3
    settle_time: float = 2.0
    auto_settle: bool = True
    auto_remove_after_settle: bool = False
    auto_remove_delay: float = 10.0
    bone_solver_iterations: int = 4

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RagdollStats:
    total_ragdolls: int = 0
    active_ragdolls: int = 0
    settled_ragdolls: int = 0
    frozen_ragdolls: int = 0
    total_bones: int = 0
    total_joints: int = 0
    total_impulses: int = 0
    total_collisions: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RagdollSnapshot:
    ragdolls: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RagdollEvent:
    event_id: str
    kind: str
    timestamp: float
    ragdoll_id: Optional[str] = None
    bone_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Ragdoll Physics System
# ---------------------------------------------------------------------------

class RagdollPhysicsSystem:
    """Manages ragdoll instances with bone-joint physics simulation."""

    _instance: Optional["RagdollPhysicsSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._ragdolls: Dict[str, RagdollProfile] = {}
        self._impulses: List[ImpulseRequest] = []
        self._events: List[RagdollEvent] = []
        self._stats = RagdollStats()
        self._config = RagdollConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._impulse_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "RagdollPhysicsSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed a sample humanoid ragdoll."""
        ragdoll = self._build_humanoid("rddl_sample_guard", "Fallen Guard", "ent_guard_01")
        self._ragdolls[ragdoll.ragdoll_id] = ragdoll
        self._stats.total_ragdolls = 1
        self._stats.active_ragdolls = 1
        self._stats.total_bones = len(ragdoll.bones)
        self._stats.total_joints = len(ragdoll.joints)
        self._initialized = True

    def _build_humanoid(self, ragdoll_id: str, name: str, entity_id: str, origin: Tuple[float, float, float] = (0.0, 1.0, 0.0)) -> RagdollProfile:
        """Build a standard humanoid ragdoll skeleton."""
        ragdoll = RagdollProfile(
            ragdoll_id=ragdoll_id,
            name=name,
            entity_id=entity_id,
            gravity=self._config.gravity,
            air_drag=self._config.air_drag,
            ground_friction=self._config.ground_friction,
            settle_threshold=self._config.settle_threshold,
            settle_time=self._config.settle_time,
        )
        ox, oy, oz = origin
        bones_data = [
            ("bone_pelvis", BoneType.PELVIS.value, "", 15.0, 0.12, 0.15, (ox, oy, oz)),
            ("bone_spine", BoneType.SPINE.value, "bone_pelvis", 8.0, 0.10, 0.35, (ox, oy + 0.25, oz)),
            ("bone_chest", BoneType.CHEST.value, "bone_spine", 12.0, 0.14, 0.30, (ox, oy + 0.55, oz)),
            ("bone_neck", BoneType.NECK.value, "bone_chest", 2.0, 0.05, 0.12, (ox, oy + 0.75, oz)),
            ("bone_head", BoneType.HEAD.value, "bone_neck", 5.0, 0.11, 0.20, (ox, oy + 0.92, oz)),
            ("bone_upper_arm_l", BoneType.UPPER_ARM_L.value, "bone_chest", 3.0, 0.05, 0.28, (ox + 0.20, oy + 0.55, oz)),
            ("bone_lower_arm_l", BoneType.LOWER_ARM_L.value, "bone_upper_arm_l", 2.0, 0.04, 0.26, (ox + 0.20, oy + 0.27, oz)),
            ("bone_hand_l", BoneType.HAND_L.value, "bone_lower_arm_l", 1.0, 0.06, 0.12, (ox + 0.20, oy + 0.10, oz)),
            ("bone_upper_arm_r", BoneType.UPPER_ARM_R.value, "bone_chest", 3.0, 0.05, 0.28, (ox - 0.20, oy + 0.55, oz)),
            ("bone_lower_arm_r", BoneType.LOWER_ARM_R.value, "bone_upper_arm_r", 2.0, 0.04, 0.26, (ox - 0.20, oy + 0.27, oz)),
            ("bone_hand_r", BoneType.HAND_R.value, "bone_lower_arm_r", 1.0, 0.06, 0.12, (ox - 0.20, oy + 0.10, oz)),
            ("bone_upper_leg_l", BoneType.UPPER_LEG_L.value, "bone_pelvis", 5.0, 0.07, 0.40, (ox + 0.08, oy - 0.15, oz)),
            ("bone_lower_leg_l", BoneType.LOWER_LEG_L.value, "bone_upper_leg_l", 3.0, 0.05, 0.38, (ox + 0.08, oy - 0.55, oz)),
            ("bone_foot_l", BoneType.FOOT_L.value, "bone_lower_leg_l", 2.0, 0.06, 0.20, (ox + 0.08, oy - 0.93, oz + 0.05)),
            ("bone_upper_leg_r", BoneType.UPPER_LEG_R.value, "bone_pelvis", 5.0, 0.07, 0.40, (ox - 0.08, oy - 0.15, oz)),
            ("bone_lower_leg_r", BoneType.LOWER_LEG_R.value, "bone_upper_leg_r", 3.0, 0.05, 0.38, (ox - 0.08, oy - 0.55, oz)),
            ("bone_foot_r", BoneType.FOOT_R.value, "bone_lower_leg_r", 2.0, 0.06, 0.20, (ox - 0.08, oy - 0.93, oz + 0.05)),
        ]
        for bid, btype, parent, mass, radius, length, pos in bones_data:
            ragdoll.bones[bid] = BoneSpec(
                bone_id=bid,
                bone_type=btype,
                parent_id=parent,
                mass=mass,
                radius=radius,
                length=length,
                position=pos,
            )
        joints_data = [
            ("jnt_neck", JointType.CONE.value, "bone_chest", "bone_neck", (ox, oy + 0.72, oz), -45.0, 45.0, 30.0),
            ("jnt_head", JointType.BALL.value, "bone_neck", "bone_head", (ox, oy + 0.85, oz), -30.0, 30.0, 20.0),
            ("jnt_spine", JointType.CONE.value, "bone_pelvis", "bone_spine", (ox, oy + 0.12, oz), -20.0, 20.0, 15.0),
            ("jnt_chest", JointType.CONE.value, "bone_spine", "bone_chest", (ox, oy + 0.42, oz), -15.0, 15.0, 10.0),
            ("jnt_shoulder_l", JointType.BALL.value, "bone_chest", "bone_upper_arm_l", (ox + 0.18, oy + 0.55, oz), -90.0, 90.0, 60.0),
            ("jnt_elbow_l", JointType.HINGE.value, "bone_upper_arm_l", "bone_lower_arm_l", (ox + 0.20, oy + 0.30, oz), 0.0, 140.0, 0.0),
            ("jnt_wrist_l", JointType.HINGE.value, "bone_lower_arm_l", "bone_hand_l", (ox + 0.20, oy + 0.12, oz), -30.0, 30.0, 0.0),
            ("jnt_shoulder_r", JointType.BALL.value, "bone_chest", "bone_upper_arm_r", (ox - 0.18, oy + 0.55, oz), -90.0, 90.0, 60.0),
            ("jnt_elbow_r", JointType.HINGE.value, "bone_upper_arm_r", "bone_lower_arm_r", (ox - 0.20, oy + 0.30, oz), 0.0, 140.0, 0.0),
            ("jnt_wrist_r", JointType.HINGE.value, "bone_lower_arm_r", "bone_hand_r", (ox - 0.20, oy + 0.12, oz), -30.0, 30.0, 0.0),
            ("jnt_hip_l", JointType.CONE.value, "bone_pelvis", "bone_upper_leg_l", (ox + 0.08, oy - 0.08, oz), -60.0, 60.0, 40.0),
            ("jnt_knee_l", JointType.HINGE.value, "bone_upper_leg_l", "bone_lower_leg_l", (ox + 0.08, oy - 0.40, oz), 0.0, 150.0, 0.0),
            ("jnt_ankle_l", JointType.HINGE.value, "bone_lower_leg_l", "bone_foot_l", (ox + 0.08, oy - 0.80, oz), -20.0, 30.0, 0.0),
            ("jnt_hip_r", JointType.CONE.value, "bone_pelvis", "bone_upper_leg_r", (ox - 0.08, oy - 0.08, oz), -60.0, 60.0, 40.0),
            ("jnt_knee_r", JointType.HINGE.value, "bone_upper_leg_r", "bone_lower_leg_r", (ox - 0.08, oy - 0.40, oz), 0.0, 150.0, 0.0),
            ("jnt_ankle_r", JointType.HINGE.value, "bone_lower_leg_r", "bone_foot_r", (ox - 0.08, oy - 0.80, oz), -20.0, 30.0, 0.0),
        ]
        for jid, jtype, parent_bone, child_bone, anchor, min_ang, max_ang, twist in joints_data:
            ragdoll.joints[jid] = JointSpec(
                joint_id=jid,
                joint_type=jtype,
                parent_bone_id=parent_bone,
                child_bone_id=child_bone,
                anchor=anchor,
                min_angle=min_ang,
                max_angle=max_ang,
                twist_limit=twist,
            )
        return ragdoll

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"revt_{self._event_counter:08d}"

    def _next_impulse_id(self) -> str:
        self._impulse_counter += 1
        return f"rimp_{self._impulse_counter:08d}"

    def _record_event(self, kind: str, **kwargs: Any) -> RagdollEvent:
        event = RagdollEvent(
            event_id=self._next_event_id(),
            kind=kind,
            timestamp=_now(),
            **kwargs,
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]
        return event

    # ------------------------------------------------------------------
    # Ragdoll Management
    # ------------------------------------------------------------------

    def create_ragdoll(self, ragdoll: RagdollProfile) -> Dict[str, Any]:
        if len(self._ragdolls) >= _MAX_RAGDOLLS and ragdoll.ragdoll_id not in self._ragdolls:
            oldest_id = next(iter(self._ragdolls))
            self._ragdolls.pop(oldest_id, None)
        was_new = ragdoll.ragdoll_id not in self._ragdolls
        self._ragdolls[ragdoll.ragdoll_id] = ragdoll
        self._stats.total_ragdolls = len(self._ragdolls)
        self._stats.active_ragdolls = sum(1 for r in self._ragdolls.values() if r.state == RagdollState.ACTIVE.value)
        self._stats.settled_ragdolls = sum(1 for r in self._ragdolls.values() if r.state == RagdollState.SETTLED.value)
        self._stats.frozen_ragdolls = sum(1 for r in self._ragdolls.values() if r.state == RagdollState.FROZEN.value)
        self._stats.total_bones = sum(len(r.bones) for r in self._ragdolls.values())
        self._stats.total_joints = sum(len(r.joints) for r in self._ragdolls.values())
        self._record_event(
            RagdollEventKind.RAGDOLL_CREATED if was_new else RagdollEventKind.CONFIG_UPDATED,
            ragdoll_id=ragdoll.ragdoll_id,
            details={"name": ragdoll.name, "bones": len(ragdoll.bones), "joints": len(ragdoll.joints)},
        )
        return {"ragdoll_id": ragdoll.ragdoll_id, "created": True}

    def create_humanoid(self, ragdoll_id: str, name: str = "", entity_id: str = "", origin: Tuple[float, float, float] = (0.0, 1.0, 0.0)) -> Dict[str, Any]:
        """Convenience method to create a standard humanoid ragdoll."""
        ragdoll = self._build_humanoid(ragdoll_id, name, entity_id, origin)
        return self.create_ragdoll(ragdoll)

    def remove_ragdoll(self, ragdoll_id: str) -> Dict[str, Any]:
        if ragdoll_id not in self._ragdolls:
            return {"ragdoll_id": ragdoll_id, "removed": False, "reason": "not found"}
        self._ragdolls.pop(ragdoll_id)
        self._stats.total_ragdolls = len(self._ragdolls)
        self._stats.active_ragdolls = sum(1 for r in self._ragdolls.values() if r.state == RagdollState.ACTIVE.value)
        self._stats.settled_ragdolls = sum(1 for r in self._ragdolls.values() if r.state == RagdollState.SETTLED.value)
        self._stats.frozen_ragdolls = sum(1 for r in self._ragdolls.values() if r.state == RagdollState.FROZEN.value)
        self._stats.total_bones = sum(len(r.bones) for r in self._ragdolls.values())
        self._stats.total_joints = sum(len(r.joints) for r in self._ragdolls.values())
        self._record_event(RagdollEventKind.RAGDOLL_REMOVED, ragdoll_id=ragdoll_id)
        return {"ragdoll_id": ragdoll_id, "removed": True}

    def get_ragdoll(self, ragdoll_id: str) -> Optional[RagdollProfile]:
        return self._ragdolls.get(ragdoll_id)

    def list_ragdolls(self, state: Optional[str] = None, entity_id: Optional[str] = None, limit: int = 100) -> List[RagdollProfile]:
        results: List[RagdollProfile] = []
        for r in self._ragdolls.values():
            if state is not None and r.state != state:
                continue
            if entity_id is not None and r.entity_id != entity_id:
                continue
            results.append(r)
        return results[:max(0, min(limit, len(results)))]

    def freeze_ragdoll(self, ragdoll_id: str, frozen: bool) -> Dict[str, Any]:
        r = self._ragdolls.get(ragdoll_id)
        if r is None:
            return {"ragdoll_id": ragdoll_id, "updated": False, "reason": "not found"}
        r.state = RagdollState.FROZEN.value if frozen else RagdollState.ACTIVE.value
        r.updated_at = _now()
        self._stats.active_ragdolls = sum(1 for x in self._ragdolls.values() if x.state == RagdollState.ACTIVE.value)
        self._stats.frozen_ragdolls = sum(1 for x in self._ragdolls.values() if x.state == RagdollState.FROZEN.value)
        self._record_event(RagdollEventKind.RAGDOLL_FROZEN if frozen else RagdollEventKind.CONFIG_UPDATED, ragdoll_id=ragdoll_id)
        return {"ragdoll_id": ragdoll_id, "frozen": frozen}

    # ------------------------------------------------------------------
    # Bone and Joint queries
    # ------------------------------------------------------------------

    def get_bone(self, ragdoll_id: str, bone_id: str) -> Optional[BoneSpec]:
        r = self._ragdolls.get(ragdoll_id)
        if r is None:
            return None
        return r.bones.get(bone_id)

    def list_bones(self, ragdoll_id: str) -> List[BoneSpec]:
        r = self._ragdolls.get(ragdoll_id)
        if r is None:
            return []
        return list(r.bones.values())

    def get_joint(self, ragdoll_id: str, joint_id: str) -> Optional[JointSpec]:
        r = self._ragdolls.get(ragdoll_id)
        if r is None:
            return None
        return r.joints.get(joint_id)

    def list_joints(self, ragdoll_id: str) -> List[JointSpec]:
        r = self._ragdolls.get(ragdoll_id)
        if r is None:
            return []
        return list(r.joints.values())

    # ------------------------------------------------------------------
    # Impulse application
    # ------------------------------------------------------------------

    def apply_impulse(self, ragdoll_id: str, bone_id: str, force: Tuple[float, float, float], application_point: Optional[Tuple[float, float, float]] = None) -> Dict[str, Any]:
        r = self._ragdolls.get(ragdoll_id)
        if r is None:
            return {"ragdoll_id": ragdoll_id, "applied": False, "reason": "ragdoll not found"}
        bone = r.bones.get(bone_id)
        if bone is None:
            return {"ragdoll_id": ragdoll_id, "applied": False, "reason": "bone not found"}
        if application_point is None:
            application_point = bone.position
        impulse = ImpulseRequest(
            impulse_id=self._next_impulse_id(),
            ragdoll_id=ragdoll_id,
            bone_id=bone_id,
            force=force,
            application_point=application_point,
        )
        self._impulses.append(impulse)
        if len(self._impulses) > _MAX_IMPULSES:
            self._impulses = self._impulses[-_MAX_IMPULSES:]
        # Apply velocity change immediately
        inv_mass = 1.0 / max(bone.mass, 0.1)
        bone.velocity = _add3(bone.velocity, _scale3(force, inv_mass))
        # Wake the ragdoll if settled
        if r.state == RagdollState.SETTLED.value:
            r.state = RagdollState.ACTIVE.value
            r.low_motion_time = 0.0
            self._stats.active_ragdolls = sum(1 for x in self._ragdolls.values() if x.state == RagdollState.ACTIVE.value)
            self._stats.settled_ragdolls = sum(1 for x in self._ragdolls.values() if x.state == RagdollState.SETTLED.value)
        self._stats.total_impulses += 1
        self._record_event(
            RagdollEventKind.IMPULSE_APPLIED,
            ragdoll_id=ragdoll_id,
            bone_id=bone_id,
            details={"force": list(force), "impulse_id": impulse.impulse_id},
        )
        return {"impulse_id": impulse.impulse_id, "applied": True}

    # ------------------------------------------------------------------
    # Physics simulation
    # ------------------------------------------------------------------

    def _simulate_bone(self, bone: BoneSpec, ragdoll: RagdollProfile, delta_time: float) -> None:
        """Integrate a single bone's physics for one tick."""
        if bone.grounded:
            # Ground friction reduces velocity
            friction = ragdoll.ground_friction
            bone.velocity = _scale3(bone.velocity, max(0.0, 1.0 - friction * delta_time * 5.0))
            bone.angular_velocity = _scale3(bone.angular_velocity, max(0.0, 1.0 - friction * delta_time * 3.0))

        # Apply gravity
        gravity = _scale3(ragdoll.gravity, delta_time)
        bone.velocity = _add3(bone.velocity, gravity)

        # Apply air drag
        drag = ragdoll.air_drag * delta_time
        bone.velocity = _scale3(bone.velocity, max(0.0, 1.0 - drag))
        bone.angular_velocity = _scale3(bone.angular_velocity, max(0.0, 1.0 - drag * 0.5))

        # Integrate position
        bone.position = _add3(bone.position, _scale3(bone.velocity, delta_time))
        bone.rotation = _add3(bone.rotation, _scale3(bone.angular_velocity, delta_time))

        # Ground collision
        bone_radius = bone.radius
        ground_y = ragdoll.ground_y + bone_radius
        if bone.position[1] < ground_y:
            bone.position = (bone.position[0], ground_y, bone.position[2])
            # Bounce with restitution
            if bone.velocity[1] < 0:
                bone.velocity = (bone.velocity[0], -bone.velocity[1] * ragdoll.metadata.get("restitution", self._config.restitution), bone.velocity[2])
                if abs(bone.velocity[1]) < 0.5:
                    bone.velocity = (bone.velocity[0] * 0.8, 0.0, bone.velocity[2] * 0.8)
                    bone.grounded = True
                else:
                    self._stats.total_collisions += 1
                    self._record_event(
                        RagdollEventKind.BONE_COLLISION,
                        ragdoll_id=ragdoll.ragdoll_id,
                        bone_id=bone.bone_id,
                        details={"position": list(bone.position), "impact_speed": abs(bone.velocity[1])},
                    )
            else:
                bone.grounded = True
        else:
            bone.grounded = False

    def _solve_joints(self, ragdoll: RagdollProfile, delta_time: float) -> None:
        """Apply joint constraints by pulling connected bones toward anchor points."""
        for joint in ragdoll.joints.values():
            parent = ragdoll.bones.get(joint.parent_bone_id)
            child = ragdoll.bones.get(joint.child_bone_id)
            if parent is None or child is None:
                continue
            # Distance-based constraint: pull child toward anchor relative to parent
            desired_offset = _sub3(joint.anchor, parent.position)
            current_offset = _sub3(child.position, parent.position)
            correction = _sub3(desired_offset, current_offset)
            stiffness = joint.stiffness * 0.5
            correction_force = _scale3(correction, stiffness)
            total_mass = parent.mass + child.mass
            if total_mass > 0:
                parent_factor = child.mass / total_mass
                child_factor = parent.mass / total_mass
                parent.velocity = _sub3(parent.velocity, _scale3(correction_force, parent_factor * delta_time * 10.0))
                child.velocity = _add3(child.velocity, _scale3(correction_force, child_factor * delta_time * 10.0))
            # Angular damping
            damping = joint.damping * delta_time
            avg_angular = _scale3(_add3(parent.angular_velocity, child.angular_velocity), 0.5)
            parent.angular_velocity = _lerp_vec3(parent.angular_velocity, avg_angular, damping)
            child.angular_velocity = _lerp_vec3(child.angular_velocity, avg_angular, damping)

    def _check_settled(self, ragdoll: RagdollProfile, delta_time: float) -> bool:
        """Check if the ragdoll has settled (low motion for sustained period)."""
        total_motion = 0.0
        for bone in ragdoll.bones.values():
            speed = _length3(bone.velocity)
            angular_speed = _length3(bone.angular_velocity)
            total_motion += speed + angular_speed * 0.5
        avg_motion = total_motion / max(len(ragdoll.bones), 1)
        if avg_motion < ragdoll.settle_threshold:
            ragdoll.low_motion_time += delta_time
        else:
            ragdoll.low_motion_time = 0.0
        return ragdoll.low_motion_time >= ragdoll.settle_time

    # ------------------------------------------------------------------
    # Tick / lifecycle
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        now = _now()
        for ragdoll in self._ragdolls.values():
            if ragdoll.state != RagdollState.ACTIVE.value:
                continue
            ragdoll.elapsed += delta_time
            # Simulate each bone
            for bone in ragdoll.bones.values():
                self._simulate_bone(bone, ragdoll, delta_time)
            # Solve joint constraints
            for _ in range(self._config.bone_solver_iterations):
                self._solve_joints(ragdoll, delta_time)
            # Check settling
            if self._config.auto_settle and self._check_settled(ragdoll, delta_time):
                ragdoll.state = RagdollState.SETTLED.value
                ragdoll.updated_at = now
                self._stats.active_ragdolls -= 1
                self._stats.settled_ragdolls += 1
                self._record_event(RagdollEventKind.RAGDOLL_SETTLED, ragdoll_id=ragdoll.ragdoll_id)
                # Auto-remove after delay
                if self._config.auto_remove_after_settle and ragdoll.elapsed > self._config.auto_remove_delay:
                    self.remove_ragdoll(ragdoll.ragdoll_id)
        self._record_event(RagdollEventKind.TICK, details={"delta_time": delta_time, "tick": self._tick_count})
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]
        return {"tick": self._tick_count, "delta_time": delta_time}

    def get_config(self) -> RagdollConfig:
        return self._config

    def set_config(self, config: RagdollConfig) -> Dict[str, Any]:
        self._config = config
        self._record_event(RagdollEventKind.CONFIG_UPDATED, details={"max_ragdolls": config.max_ragdolls})
        return {"updated": True}

    def list_events(self, ragdoll_id: Optional[str] = None, bone_id: Optional[str] = None, limit: int = 100) -> List[RagdollEvent]:
        results: List[RagdollEvent] = []
        for e in self._events:
            if ragdoll_id is not None and e.ragdoll_id != ragdoll_id:
                continue
            if bone_id is not None and e.bone_id != bone_id:
                continue
            results.append(e)
        return list(reversed(results))[:max(0, min(limit, len(results)))]

    def get_stats(self) -> RagdollStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_ragdolls": len(self._ragdolls),
            "active_ragdolls": sum(1 for r in self._ragdolls.values() if r.state == RagdollState.ACTIVE.value),
            "settled_ragdolls": sum(1 for r in self._ragdolls.values() if r.state == RagdollState.SETTLED.value),
            "frozen_ragdolls": sum(1 for r in self._ragdolls.values() if r.state == RagdollState.FROZEN.value),
            "total_bones": sum(len(r.bones) for r in self._ragdolls.values()),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> RagdollSnapshot:
        return RagdollSnapshot(
            ragdolls=[r.to_dict() for r in self._ragdolls.values()],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        self._ragdolls.clear()
        self._impulses.clear()
        self._events.clear()
        self._stats = RagdollStats()
        self._tick_count = 0
        self._event_counter = 0
        self._impulse_counter = 0
        self._initialized = False
        self._seed()
        self._record_event(RagdollEventKind.RESET)
        return {"reset": True, "initialized": self._initialized}


def _lerp_vec3(a: Tuple[float, float, float], b: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
    t = _clamp(t, 0.0, 1.0)
    return (_lerp(a[0], b[0], t), _lerp(a[1], b[1], t), _lerp(a[2], b[2], t))


def get_ragdoll_physics() -> RagdollPhysicsSystem:
    return RagdollPhysicsSystem.get_instance()
