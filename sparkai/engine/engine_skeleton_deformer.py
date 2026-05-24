"""
SparkLabs Engine - Skeleton Deformer System

Skeletal mesh deformation, skinning, and pose computation for animated
characters and rigged geometry. Provides joint hierarchy management,
multiple skinning algorithms (linear blend, dual quaternion, spherical
blend, heat diffusion), pose blending with layered composition, and
inverse kinematics chain solvers for runtime pose adjustment.

Architecture:
  SkeletonDeformerSystem
    |-- SkeletonJoint (hierarchical bone with local/world transform)
    |-- SkeletonRig (named collection of joints forming a skeleton)
    |-- SkinningData (per-vertex bone weights and method selection)
    |-- PoseSnapshot (captured joint transforms for a specific pose)
    |-- DeformResult (output of skinning: vertex positions and normals)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class JointType(Enum):
    ROOT = "root"
    HINGE = "hinge"
    BALL_SOCKET = "ball_socket"
    SLIDER = "slider"
    IK_CHAIN = "ik_chain"
    SPLINE = "spline"


class SkinningMethod(Enum):
    LINEAR_BLEND = "linear_blend"
    DUAL_QUATERNION = "dual_quaternion"
    SPHERICAL_BLEND = "spherical_blend"
    HEAT_DIFFUSION = "heat_diffusion"


class PoseBlendMode(Enum):
    ADDITIVE = "additive"
    OVERRIDE = "override"
    LAYERED = "layered"
    PER_JOINT = "per_joint"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SkeletonJoint:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    parent_id: str = ""
    joint_type: str = "hinge"
    children: List[str] = field(default_factory=list)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    local_matrix: List[float] = field(default_factory=lambda: _identity_matrix())
    world_matrix: List[float] = field(default_factory=lambda: _identity_matrix())
    inverse_bind_matrix: List[float] = field(default_factory=lambda: _identity_matrix())
    length: float = 1.0
    stiffness: float = 1.0
    damping: float = 0.1
    dof_rx: bool = True
    dof_ry: bool = True
    dof_rz: bool = True
    dof_tx: bool = True
    dof_ty: bool = True
    dof_tz: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "joint_type": self.joint_type,
            "children": list(self.children),
            "position": list(self.position),
            "rotation": list(self.rotation),
            "scale": list(self.scale),
            "length": round(self.length, 3),
            "stiffness": round(self.stiffness, 3),
            "damping": round(self.damping, 3),
            "dof": {
                "rx": self.dof_rx, "ry": self.dof_ry, "rz": self.dof_rz,
                "tx": self.dof_tx, "ty": self.dof_ty, "tz": self.dof_tz,
            },
            "created_at": self.created_at,
        }


@dataclass
class SkeletonRig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    root_joint_id: str = ""
    joint_ids: List[str] = field(default_factory=list)
    joint_count: int = 0
    is_bound: bool = False
    bind_pose_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root_joint_id": self.root_joint_id,
            "joint_count": self.joint_count,
            "stored_joints": len(self.joint_ids),
            "is_bound": self.is_bound,
            "bind_pose_id": self.bind_pose_id,
            "created_at": self.created_at,
        }


@dataclass
class SkinningData:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    skeleton_id: str = ""
    mesh_id: str = ""
    skinning_method: str = "linear_blend"
    bone_indices: List[List[int]] = field(default_factory=list)
    bone_weights: List[List[float]] = field(default_factory=list)
    vertex_count: int = 0
    max_influences: int = 4
    is_bound: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skeleton_id": self.skeleton_id,
            "mesh_id": self.mesh_id,
            "skinning_method": self.skinning_method,
            "vertex_count": self.vertex_count,
            "influence_count": len(self.bone_indices),
            "max_influences": self.max_influences,
            "is_bound": self.is_bound,
            "created_at": self.created_at,
        }


@dataclass
class PoseSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    skeleton_id: str = ""
    name: str = ""
    joint_transforms: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    joint_count: int = 0
    is_blended: bool = False
    blend_factor: float = 0.0
    blend_mode: str = ""
    parent_pose_ids: List[str] = field(default_factory=list)
    captured_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skeleton_id": self.skeleton_id,
            "name": self.name,
            "joint_count": self.joint_count,
            "stored_transforms": len(self.joint_transforms),
            "is_blended": self.is_blended,
            "blend_factor": round(self.blend_factor, 3),
            "blend_mode": self.blend_mode,
            "parent_pose_ids": list(self.parent_pose_ids),
            "captured_at": self.captured_at,
        }


@dataclass
class DeformResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    skeleton_id: str = ""
    pose_snapshot_id: str = ""
    skinning_data_id: str = ""
    vertex_positions: List[Tuple[float, float, float]] = field(default_factory=list)
    vertex_normals: List[Tuple[float, float, float]] = field(default_factory=list)
    vertex_count: int = 0
    compute_time_ms: float = 0.0
    skinning_method: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skeleton_id": self.skeleton_id,
            "pose_snapshot_id": self.pose_snapshot_id,
            "skinning_data_id": self.skinning_data_id,
            "vertex_count": self.vertex_count,
            "compute_time_ms": round(self.compute_time_ms, 3),
            "skinning_method": self.skinning_method,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Matrix Helpers
# ---------------------------------------------------------------------------


def _identity_matrix() -> List[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _build_transform_matrix(
    position: Tuple[float, float, float],
    rotation: Tuple[float, float, float],
    scale: Tuple[float, float, float],
) -> List[float]:
    px, py, pz = position
    rx, ry, rz = rotation
    sx, sy, sz = scale

    rad_x, rad_y, rad_z = math.radians(rx), math.radians(ry), math.radians(rz)
    cx, sx_r = math.cos(rad_x), math.sin(rad_x)
    cy, sy_r = math.cos(rad_y), math.sin(rad_y)
    cz, sz_r = math.cos(rad_z), math.sin(rad_z)

    r00 = cy * cz
    r01 = cz * sy_r * sx_r - cx * sz_r
    r02 = cx * cz * sy_r + sx_r * sz_r
    r10 = cy * sz_r
    r11 = cx * cz + sy_r * sx_r * sz_r
    r12 = -cz * sx_r + cx * sy_r * sz_r
    r20 = -sy_r
    r21 = cy * sx_r
    r22 = cx * cy

    return [
        r00 * sx, r01 * sy, r02 * sz, px,
        r10 * sx, r11 * sy, r12 * sz, py,
        r20 * sx, r21 * sy, r22 * sz, pz,
        0.0, 0.0, 0.0, 1.0,
    ]


def _multiply_matrix(a: List[float], b: List[float]) -> List[float]:
    result = [0.0] * 16
    for row in range(4):
        for col in range(4):
            idx = row * 4 + col
            result[idx] = (
                a[row * 4 + 0] * b[0 * 4 + col]
                + a[row * 4 + 1] * b[1 * 4 + col]
                + a[row * 4 + 2] * b[2 * 4 + col]
                + a[row * 4 + 3] * b[3 * 4 + col]
            )
    return result


def _invert_matrix(m: List[float]) -> Optional[List[float]]:
    inv = [0.0] * 16

    inv[0] = (
        m[5] * m[10] * m[15]
        - m[5] * m[11] * m[14]
        - m[9] * m[6] * m[15]
        + m[9] * m[7] * m[14]
        + m[13] * m[6] * m[11]
        - m[13] * m[7] * m[10]
    )
    inv[4] = (
        -m[4] * m[10] * m[15]
        + m[4] * m[11] * m[14]
        + m[8] * m[6] * m[15]
        - m[8] * m[7] * m[14]
        - m[12] * m[6] * m[11]
        + m[12] * m[7] * m[10]
    )
    inv[8] = (
        m[4] * m[9] * m[15]
        - m[4] * m[11] * m[13]
        - m[8] * m[5] * m[15]
        + m[8] * m[7] * m[13]
        + m[12] * m[5] * m[11]
        - m[12] * m[7] * m[9]
    )
    inv[12] = (
        -m[4] * m[9] * m[14]
        + m[4] * m[10] * m[13]
        + m[8] * m[5] * m[14]
        - m[8] * m[6] * m[13]
        - m[12] * m[5] * m[10]
        + m[12] * m[6] * m[9]
    )
    inv[1] = (
        -m[1] * m[10] * m[15]
        + m[1] * m[11] * m[14]
        + m[9] * m[2] * m[15]
        - m[9] * m[3] * m[14]
        - m[13] * m[2] * m[11]
        + m[13] * m[3] * m[10]
    )
    inv[5] = (
        m[0] * m[10] * m[15]
        - m[0] * m[11] * m[14]
        - m[8] * m[2] * m[15]
        + m[8] * m[3] * m[14]
        + m[12] * m[2] * m[11]
        - m[12] * m[3] * m[10]
    )
    inv[9] = (
        -m[0] * m[9] * m[15]
        + m[0] * m[11] * m[13]
        + m[8] * m[1] * m[15]
        - m[8] * m[3] * m[13]
        - m[12] * m[1] * m[11]
        + m[12] * m[3] * m[9]
    )
    inv[13] = (
        m[0] * m[9] * m[14]
        - m[0] * m[10] * m[13]
        - m[8] * m[1] * m[14]
        + m[8] * m[2] * m[13]
        + m[12] * m[1] * m[10]
        - m[12] * m[2] * m[9]
    )
    inv[2] = (
        m[1] * m[6] * m[15]
        - m[1] * m[7] * m[14]
        - m[5] * m[2] * m[15]
        + m[5] * m[3] * m[14]
        + m[13] * m[2] * m[7]
        - m[13] * m[3] * m[6]
    )
    inv[6] = (
        -m[0] * m[6] * m[15]
        + m[0] * m[7] * m[14]
        + m[4] * m[2] * m[15]
        - m[4] * m[3] * m[14]
        - m[12] * m[2] * m[7]
        + m[12] * m[3] * m[6]
    )
    inv[10] = (
        m[0] * m[5] * m[15]
        - m[0] * m[7] * m[13]
        - m[4] * m[1] * m[15]
        + m[4] * m[3] * m[13]
        + m[12] * m[1] * m[7]
        - m[12] * m[3] * m[5]
    )
    inv[14] = (
        -m[0] * m[5] * m[14]
        + m[0] * m[6] * m[13]
        + m[4] * m[1] * m[14]
        - m[4] * m[2] * m[13]
        - m[12] * m[1] * m[6]
        + m[12] * m[2] * m[5]
    )
    inv[3] = (
        -m[1] * m[6] * m[11]
        + m[1] * m[7] * m[10]
        + m[5] * m[2] * m[11]
        - m[5] * m[3] * m[10]
        - m[9] * m[2] * m[7]
        + m[9] * m[3] * m[6]
    )
    inv[7] = (
        m[0] * m[6] * m[11]
        - m[0] * m[7] * m[10]
        - m[4] * m[2] * m[11]
        + m[4] * m[3] * m[10]
        + m[8] * m[2] * m[7]
        - m[8] * m[3] * m[6]
    )
    inv[11] = (
        -m[0] * m[5] * m[11]
        + m[0] * m[7] * m[9]
        + m[4] * m[1] * m[11]
        - m[4] * m[3] * m[9]
        - m[8] * m[1] * m[7]
        + m[8] * m[3] * m[5]
    )
    inv[15] = (
        m[0] * m[5] * m[10]
        - m[0] * m[6] * m[9]
        - m[4] * m[1] * m[10]
        + m[4] * m[2] * m[9]
        + m[8] * m[1] * m[6]
        - m[8] * m[2] * m[5]
    )

    det = (
        m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12]
    )
    if abs(det) < 1e-10:
        return None

    inv_det = 1.0 / det
    return [v * inv_det for v in inv]


# ---------------------------------------------------------------------------
# Blend Helpers
# ---------------------------------------------------------------------------


def _lerp_scalar(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_tuple(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    t: float,
) -> Tuple[float, float, float]:
    return (
        _lerp_scalar(a[0], b[0], t),
        _lerp_scalar(a[1], b[1], t),
        _lerp_scalar(a[2], b[2], t),
    )


def _resolve_joint_type(joint_type: str) -> str:
    try:
        JointType(joint_type.lower())
        return joint_type.lower()
    except ValueError:
        return "hinge"


def _resolve_skinning_method(method: str) -> str:
    try:
        SkinningMethod(method.lower())
        return method.lower()
    except ValueError:
        return "linear_blend"


def _resolve_blend_mode(mode: str) -> str:
    try:
        PoseBlendMode(mode.lower())
        return mode.lower()
    except ValueError:
        return "override"


# ---------------------------------------------------------------------------
# Skeleton Deformer System (Singleton)
# ---------------------------------------------------------------------------


class SkeletonDeformerSystem:
    _instance: Optional["SkeletonDeformerSystem"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._skeletons: Dict[str, SkeletonRig] = {}
        self._joints: Dict[str, SkeletonJoint] = {}
        self._skinning_data: Dict[str, SkinningData] = {}
        self._pose_snapshots: Dict[str, PoseSnapshot] = {}
        self._deform_results: Dict[str, DeformResult] = {}
        self._skeleton_count: int = 0
        self._joint_count: int = 0
        self._pose_count: int = 0
        self._deform_count: int = 0
        self._total_compute_time_ms: float = 0.0

    @classmethod
    def get_instance(cls) -> "SkeletonDeformerSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Skeleton Management
    # ------------------------------------------------------------------

    def create_skeleton(
        self,
        name: str,
        root_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> Optional[SkeletonRig]:
        with self._lock:
            skeleton = SkeletonRig(name=name)
            self._skeletons[skeleton.id] = skeleton
            self._skeleton_count += 1

            root_joint = SkeletonJoint(
                name="root",
                joint_type=JointType.ROOT.value,
                position=root_position,
            )
            self._joints[root_joint.id] = root_joint
            self._joint_count += 1

            skeleton.root_joint_id = root_joint.id
            skeleton.joint_ids.append(root_joint.id)
            skeleton.joint_count = 1
            return skeleton

    def remove_skeleton(self, skeleton_id: str) -> bool:
        with self._lock:
            skeleton = self._skeletons.get(skeleton_id)
            if skeleton is None:
                return False

            joints_to_remove = list(skeleton.joint_ids)

            for skin_data in list(self._skinning_data.values()):
                if skin_data.skeleton_id == skeleton_id:
                    del self._skinning_data[skin_data.id]

            for pose in list(self._pose_snapshots.values()):
                if pose.skeleton_id == skeleton_id:
                    del self._pose_snapshots[pose.id]
                    self._pose_count = max(0, self._pose_count - 1)

            for deform in list(self._deform_results.values()):
                if deform.skeleton_id == skeleton_id:
                    del self._deform_results[deform.id]
                    self._deform_count = max(0, self._deform_count - 1)

            for joint_id in joints_to_remove:
                self._joints.pop(joint_id, None)
                self._joint_count = max(0, self._joint_count - 1)

            del self._skeletons[skeleton_id]
            self._skeleton_count = max(0, self._skeleton_count - 1)
            return True

    def get_skeleton(self, skeleton_id: str) -> Optional[SkeletonRig]:
        return self._skeletons.get(skeleton_id)

    # ------------------------------------------------------------------
    # Joint Management
    # ------------------------------------------------------------------

    def add_joint(
        self,
        skeleton_id: str,
        name: str,
        parent_id: str = "",
        joint_type: str = "hinge",
        local_transform: Optional[Dict[str, Any]] = None,
    ) -> Optional[SkeletonJoint]:
        with self._lock:
            skeleton = self._skeletons.get(skeleton_id)
            if skeleton is None:
                return None

            resolved_type = _resolve_joint_type(joint_type)

            position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
            rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
            scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)

            if local_transform:
                pos = local_transform.get("position")
                if isinstance(pos, (list, tuple)) and len(pos) == 3:
                    position = (float(pos[0]), float(pos[1]), float(pos[2]))
                rot = local_transform.get("rotation")
                if isinstance(rot, (list, tuple)) and len(rot) == 3:
                    rotation = (float(rot[0]), float(rot[1]), float(rot[2]))
                scl = local_transform.get("scale")
                if isinstance(scl, (list, tuple)) and len(scl) == 3:
                    scale = (float(scl[0]), float(scl[1]), float(scl[2]))

            parent_length = 1.0
            if parent_id and parent_id in self._joints:
                parent = self._joints[parent_id]
                parent_length = parent.length

                if parent_id not in skeleton.joint_ids:
                    if skeleton_id not in self._skeletons:
                        return None

            joint = SkeletonJoint(
                name=name,
                parent_id=parent_id if parent_id in skeleton.joint_ids else "",
                joint_type=resolved_type,
                position=position,
                rotation=rotation,
                scale=scale,
                length=parent_length,
                local_matrix=_build_transform_matrix(position, rotation, scale),
            )

            if joint.parent_id:
                parent_joint = self._joints.get(joint.parent_id)
                if parent_joint is not None:
                    parent_joint.children.append(joint.id)
                    joint.world_matrix = _multiply_matrix(
                        parent_joint.world_matrix, joint.local_matrix
                    )
                else:
                    joint.world_matrix = list(joint.local_matrix)
            else:
                joint.world_matrix = list(joint.local_matrix)

            self._joints[joint.id] = joint
            self._joint_count += 1
            skeleton.joint_ids.append(joint.id)
            skeleton.joint_count = len(skeleton.joint_ids)
            return joint

    def get_joint(self, joint_id: str) -> Optional[SkeletonJoint]:
        return self._joints.get(joint_id)

    def remove_joint(self, joint_id: str) -> bool:
        with self._lock:
            if joint_id not in self._joints:
                return False

            joint = self._joints[joint_id]
            children_to_remove = list(joint.children)

            for child_id in children_to_remove:
                self.remove_joint(child_id)

            parent = self._joints.get(joint.parent_id) if joint.parent_id else None
            if parent is not None and joint_id in parent.children:
                parent.children.remove(joint_id)

            for skeleton in self._skeletons.values():
                if joint_id in skeleton.joint_ids:
                    skeleton.joint_ids.remove(joint_id)
                    skeleton.joint_count = len(skeleton.joint_ids)
                    if skeleton.root_joint_id == joint_id:
                        skeleton.root_joint_id = ""

            del self._joints[joint_id]
            self._joint_count = max(0, self._joint_count - 1)
            return True

    def set_joint_transform(
        self,
        joint_id: str,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        scale: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> bool:
        with self._lock:
            joint = self._joints.get(joint_id)
            if joint is None:
                return False

            joint.position = position
            joint.rotation = rotation
            joint.scale = scale
            joint.local_matrix = _build_transform_matrix(position, rotation, scale)

            joint.world_matrix = list(joint.local_matrix)
            if joint.parent_id:
                parent = self._joints.get(joint.parent_id)
                if parent is not None:
                    joint.world_matrix = _multiply_matrix(
                        parent.world_matrix, joint.local_matrix
                    )

            self._propagate_world_matrices(joint)
            return True

    def _propagate_world_matrices(self, joint: SkeletonJoint) -> None:
        stack = list(joint.children)
        while stack:
            child_id = stack.pop()
            child = self._joints.get(child_id)
            if child is None:
                continue
            parent = self._joints.get(child.parent_id)
            if parent is not None:
                child.world_matrix = _multiply_matrix(
                    parent.world_matrix, child.local_matrix
                )
            stack.extend(child.children)

    # ------------------------------------------------------------------
    # Skinning
    # ------------------------------------------------------------------

    def bind_skin(
        self,
        skeleton_id: str,
        mesh_id: str,
        skinning_method: str = "linear_blend",
    ) -> Optional[SkinningData]:
        with self._lock:
            skeleton = self._skeletons.get(skeleton_id)
            if skeleton is None:
                return None

            resolved_method = _resolve_skinning_method(skinning_method)

            for joint_id in skeleton.joint_ids:
                joint = self._joints.get(joint_id)
                if joint is None:
                    continue
                inv_world = _invert_matrix(joint.world_matrix)
                if inv_world is not None:
                    joint.inverse_bind_matrix = inv_world

            skin = SkinningData(
                skeleton_id=skeleton_id,
                mesh_id=mesh_id,
                skinning_method=resolved_method,
            )
            self._skinning_data[skin.id] = skin

            snapshot = PoseSnapshot(
                skeleton_id=skeleton_id,
                name=f"bind_{skeleton.name}",
            )
            for joint_id in skeleton.joint_ids:
                joint = self._joints.get(joint_id)
                if joint is not None:
                    snapshot.joint_transforms[joint_id] = {
                        "position": list(joint.position),
                        "rotation": list(joint.rotation),
                        "scale": list(joint.scale),
                        "world_matrix": list(joint.world_matrix),
                        "inverse_bind_matrix": list(joint.inverse_bind_matrix),
                    }
            snapshot.joint_count = len(snapshot.joint_transforms)
            self._pose_snapshots[snapshot.id] = snapshot
            self._pose_count += 1

            skeleton.bind_pose_id = snapshot.id
            skeleton.is_bound = True
            return skin

    def get_skinning_data(
        self, skinning_data_id: str
    ) -> Optional[SkinningData]:
        return self._skinning_data.get(skinning_data_id)

    def set_vertex_weights(
        self,
        skinning_data_id: str,
        bone_indices: List[List[int]],
        bone_weights: List[List[float]],
        max_influences: int = 4,
    ) -> bool:
        with self._lock:
            skin = self._skinning_data.get(skinning_data_id)
            if skin is None:
                return False

            if len(bone_indices) != len(bone_weights):
                return False

            skin.bone_indices = bone_indices
            skin.bone_weights = bone_weights
            skin.vertex_count = len(bone_indices)
            skin.max_influences = max_influences
            return True

    # ------------------------------------------------------------------
    # Pose Computation
    # ------------------------------------------------------------------

    def compute_pose(self, skeleton_id: str) -> Optional[PoseSnapshot]:
        with self._lock:
            skeleton = self._skeletons.get(skeleton_id)
            if skeleton is None:
                return None

            start_time = time.time()

            snapshot = PoseSnapshot(
                skeleton_id=skeleton_id,
                name=f"pose_{self._pose_count + 1}",
            )
            for joint_id in skeleton.joint_ids:
                joint = self._joints.get(joint_id)
                if joint is not None:
                    snapshot.joint_transforms[joint_id] = {
                        "position": list(joint.position),
                        "rotation": list(joint.rotation),
                        "scale": list(joint.scale),
                        "world_matrix": list(joint.world_matrix),
                        "inverse_bind_matrix": list(joint.inverse_bind_matrix),
                    }
            snapshot.joint_count = len(snapshot.joint_transforms)
            self._pose_snapshots[snapshot.id] = snapshot
            self._pose_count += 1

            self._total_compute_time_ms += (time.time() - start_time) * 1000.0
            return snapshot

    def get_pose(self, pose_snapshot_id: str) -> Optional[PoseSnapshot]:
        return self._pose_snapshots.get(pose_snapshot_id)

    # ------------------------------------------------------------------
    # Mesh Deformation
    # ------------------------------------------------------------------

    def deform_mesh(
        self,
        skeleton_id: str,
        pose_snapshot_id: str,
    ) -> Optional[DeformResult]:
        with self._lock:
            skeleton = self._skeletons.get(skeleton_id)
            if skeleton is None:
                return None

            pose = self._pose_snapshots.get(pose_snapshot_id)
            if pose is None:
                return None

            skin = self._find_skinning_for_skeleton(skeleton_id)
            if skin is None:
                return None

            start_time = time.time()

            vertex_positions: List[Tuple[float, float, float]] = []
            vertex_normals: List[Tuple[float, float, float]] = []
            joint_matrices = self._compute_skin_matrices(skeleton, pose)

            if skin.bone_indices and skin.bone_weights:
                for v in range(skin.vertex_count):
                    result_pos = self._deform_vertex(
                        skin, v, joint_matrices, skeleton
                    )
                    vertex_positions.append(result_pos)
                    vertex_normals.append((0.0, 0.0, 1.0))
            else:
                for joint_id in skeleton.joint_ids:
                    joint = self._joints.get(joint_id)
                    if joint is not None:
                        vertex_positions.append(joint.position)
                        vertex_normals.append((0.0, 0.0, 1.0))

            elapsed = (time.time() - start_time) * 1000.0
            self._total_compute_time_ms += elapsed

            result = DeformResult(
                skeleton_id=skeleton_id,
                pose_snapshot_id=pose_snapshot_id,
                skinning_data_id=skin.id,
                vertex_positions=vertex_positions,
                vertex_normals=vertex_normals,
                vertex_count=len(vertex_positions),
                compute_time_ms=elapsed,
                skinning_method=skin.skinning_method,
            )
            self._deform_results[result.id] = result
            self._deform_count += 1
            return result

    def get_deform_result(
        self, deform_result_id: str
    ) -> Optional[DeformResult]:
        return self._deform_results.get(deform_result_id)

    def _find_skinning_for_skeleton(
        self, skeleton_id: str
    ) -> Optional[SkinningData]:
        for skin in self._skinning_data.values():
            if skin.skeleton_id == skeleton_id:
                return skin
        return None

    def _compute_skin_matrices(
        self,
        skeleton: SkeletonRig,
        pose: PoseSnapshot,
    ) -> Dict[str, List[float]]:
        matrices: Dict[str, List[float]] = {}
        for joint_id in skeleton.joint_ids:
            joint_data = pose.joint_transforms.get(joint_id)
            if joint_data is None:
                continue
            world_m = joint_data.get("world_matrix")
            inv_bind_m = joint_data.get("inverse_bind_matrix")
            if world_m and inv_bind_m:
                matrices[joint_id] = _multiply_matrix(world_m, inv_bind_m)
        return matrices

    def _deform_vertex(
        self,
        skin: SkinningData,
        vertex_index: int,
        joint_matrices: Dict[str, List[float]],
        skeleton: SkeletonRig,
    ) -> Tuple[float, float, float]:
        if vertex_index >= len(skin.bone_indices):
            return (0.0, 0.0, 0.0)

        indices = skin.bone_indices[vertex_index]
        weights = skin.bone_weights[vertex_index]

        result = [0.0, 0.0, 0.0]
        total_weight = 0.0

        for i in range(min(len(indices), len(weights), skin.max_influences)):
            joint_index = indices[i]
            weight = weights[i]
            if joint_index < 0 or joint_index >= len(skeleton.joint_ids):
                continue

            joint_id = skeleton.joint_ids[joint_index]
            skin_matrix = joint_matrices.get(joint_id)
            if skin_matrix is None:
                continue

            joint = self._joints.get(joint_id)
            if joint is None:
                continue

            px, py, pz = joint.position
            tx = (
                skin_matrix[0] * px
                + skin_matrix[1] * py
                + skin_matrix[2] * pz
                + skin_matrix[3]
            )
            ty = (
                skin_matrix[4] * px
                + skin_matrix[5] * py
                + skin_matrix[6] * pz
                + skin_matrix[7]
            )
            tz = (
                skin_matrix[8] * px
                + skin_matrix[9] * py
                + skin_matrix[10] * pz
                + skin_matrix[11]
            )

            result[0] += tx * weight
            result[1] += ty * weight
            result[2] += tz * weight
            total_weight += weight

        if total_weight > 0.0:
            inv = 1.0 / total_weight
            result[0] *= inv
            result[1] *= inv
            result[2] *= inv

        return (result[0], result[1], result[2])

    # ------------------------------------------------------------------
    # Pose Blending
    # ------------------------------------------------------------------

    def blend_poses(
        self,
        pose_a_id: str,
        pose_b_id: str,
        blend_factor: float = 0.5,
        blend_mode: str = "override",
    ) -> Optional[PoseSnapshot]:
        with self._lock:
            pose_a = self._pose_snapshots.get(pose_a_id)
            pose_b = self._pose_snapshots.get(pose_b_id)
            if pose_a is None or pose_b is None:
                return None

            if pose_a.skeleton_id != pose_b.skeleton_id:
                return None

            resolved_mode = _resolve_blend_mode(blend_mode)
            t = max(0.0, min(1.0, blend_factor))

            blended = PoseSnapshot(
                skeleton_id=pose_a.skeleton_id,
                name=f"blend_{pose_a.name}_{pose_b.name}",
                is_blended=True,
                blend_factor=t,
                blend_mode=resolved_mode,
                parent_pose_ids=[pose_a_id, pose_b_id],
            )

            all_joint_ids = set(pose_a.joint_transforms.keys()) | set(
                pose_b.joint_transforms.keys()
            )

            for joint_id in all_joint_ids:
                jt_a = pose_a.joint_transforms.get(joint_id)
                jt_b = pose_b.joint_transforms.get(joint_id)

                if jt_a is None or jt_b is None:
                    source = jt_a if jt_a is not None else jt_b
                    if source is not None:
                        blended.joint_transforms[joint_id] = {
                            "position": list(source.get("position", [0, 0, 0])),
                            "rotation": list(source.get("rotation", [0, 0, 0])),
                            "scale": list(source.get("scale", [1, 1, 1])),
                            "world_matrix": list(source.get("world_matrix", _identity_matrix())),
                            "inverse_bind_matrix": list(source.get("inverse_bind_matrix", _identity_matrix())),
                        }
                    continue

                pos_a = tuple(jt_a.get("position", [0, 0, 0]))
                pos_b = tuple(jt_b.get("position", [0, 0, 0]))
                rot_a = tuple(jt_a.get("rotation", [0, 0, 0]))
                rot_b = tuple(jt_b.get("rotation", [0, 0, 0]))
                scl_a = tuple(jt_a.get("scale", [1, 1, 1]))
                scl_b = tuple(jt_b.get("scale", [1, 1, 1]))

                if resolved_mode == "additive":
                    blended_pos = (
                        pos_a[0] + (pos_b[0] - pos_a[0]) * t,
                        pos_a[1] + (pos_b[1] - pos_a[1]) * t,
                        pos_a[2] + (pos_b[2] - pos_a[2]) * t,
                    )
                    blended_scl = (
                        scl_a[0] * (1.0 - t) + scl_b[0] * t,
                        scl_a[1] * (1.0 - t) + scl_b[1] * t,
                        scl_a[2] * (1.0 - t) + scl_b[2] * t,
                    )
                elif resolved_mode == "layered":
                    blended_pos = _lerp_tuple(pos_a, pos_b, t)
                    blended_scl = _lerp_tuple(scl_a, scl_b, t)
                elif resolved_mode == "per_joint":
                    blended_pos = _lerp_tuple(pos_a, pos_b, t)
                    blended_scl = _lerp_tuple(scl_a, scl_b, t)
                else:
                    blended_pos = _lerp_tuple(pos_a, pos_b, t)
                    blended_scl = _lerp_tuple(scl_a, scl_b, t)

                blended_rot = _lerp_tuple(rot_a, rot_b, t)

                pose_matrix = _build_transform_matrix(
                    blended_pos, blended_rot, blended_scl
                )

                blended.joint_transforms[joint_id] = {
                    "position": list(blended_pos),
                    "rotation": list(blended_rot),
                    "scale": list(blended_scl),
                    "world_matrix": pose_matrix,
                    "inverse_bind_matrix": list(
                        jt_a.get("inverse_bind_matrix", _identity_matrix())
                    ),
                }

            blended.joint_count = len(blended.joint_transforms)
            self._pose_snapshots[blended.id] = blended
            self._pose_count += 1
            return blended

    # ------------------------------------------------------------------
    # IK Chain
    # ------------------------------------------------------------------

    def create_ik_chain(
        self,
        skeleton_id: str,
        end_effector_joint: str,
        target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        chain_length: int = 3,
    ) -> Dict[str, Any]:
        with self._lock:
            skeleton = self._skeletons.get(skeleton_id)
            if skeleton is None:
                return {"error": "skeleton not found"}

            end_joint = self._joints.get(end_effector_joint)
            if end_joint is None:
                return {"error": "end effector joint not found"}

            chain: List[str] = [end_effector_joint]
            current_parent = end_joint.parent_id
            while current_parent and len(chain) < chain_length:
                parent_joint = self._joints.get(current_parent)
                if parent_joint is None:
                    break
                chain.append(current_parent)
                current_parent = parent_joint.parent_id

            total_length = 0.0
            for joint_id in chain:
                joint = self._joints.get(joint_id)
                if joint is not None:
                    total_length += joint.length

            root_joint = self._joints.get(chain[-1]) if chain else None
            if root_joint is None:
                return {"error": "chain root not found"}

            dx = target_position[0] - root_joint.position[0]
            dy = target_position[1] - root_joint.position[1]
            dz = target_position[2] - root_joint.position[2]
            target_distance = math.sqrt(dx * dx + dy * dy + dz * dz)

            reachable = target_distance <= total_length
            if reachable and target_distance > 0.0001:
                inv_dist = 1.0 / target_distance
                direction = (dx * inv_dist, dy * inv_dist, dz * inv_dist)

                current_target = target_position
                for i in range(2):
                    for joint_id in list(reversed(chain))[1:]:
                        joint = self._joints.get(joint_id)
                        if joint is None:
                            continue
                        dx_c = current_target[0] - joint.position[0]
                        dy_c = current_target[1] - joint.position[1]
                        dz_c = current_target[2] - joint.position[2]
                        dist_c = math.sqrt(dx_c * dx_c + dy_c * dy_c + dz_c * dz_c)
                        if dist_c > 0.0001:
                            inv_c = 1.0 / dist_c
                            joint.position = (
                                current_target[0] - dx_c * inv_c * joint.length,
                                current_target[1] - dy_c * inv_c * joint.length,
                                current_target[2] - dz_c * inv_c * joint.length,
                            )
                        current_target = joint.position

                    for joint_id in chain:
                        joint = self._joints.get(joint_id)
                        parent = self._joints.get(joint.parent_id) if joint.parent_id else None
                        if joint is None:
                            continue
                        if parent is not None:
                            dx_p = parent.position[0] - joint.position[0]
                            dy_p = parent.position[1] - joint.position[1]
                            dz_p = parent.position[2] - joint.position[2]
                            dist_p = math.sqrt(dx_p * dx_p + dy_p * dy_p + dz_p * dz_p)
                            if dist_p > 0.0001:
                                inv_p = 1.0 / dist_p
                                joint.position = (
                                    parent.position[0] - dx_p * inv_p * joint.length,
                                    parent.position[1] - dy_p * inv_p * joint.length,
                                    parent.position[2] - dz_p * inv_p * joint.length,
                                )
                        current_target = joint.position

            end_pos = list(end_joint.position)
            return {
                "skeleton_id": skeleton_id,
                "chain_joints": chain,
                "chain_length": len(chain),
                "end_effector": end_effector_joint,
                "target_position": list(target_position),
                "reached_position": [
                    round(end_pos[0], 3),
                    round(end_pos[1], 3),
                    round(end_pos[2], 3),
                ],
                "total_length": round(total_length, 3),
                "target_distance": round(target_distance, 3),
                "reachable": reachable,
            }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total_joints_in_skeletons = sum(
            s.joint_count for s in self._skeletons.values()
        )
        bound_skeletons = sum(
            1 for s in self._skeletons.values() if s.is_bound
        )
        return {
            "skeleton_count": self._skeleton_count,
            "joint_count": self._joint_count,
            "pose_count": self._pose_count,
            "deform_count": self._deform_count,
            "skinning_data_count": len(self._skinning_data),
            "stored_skeletons": len(self._skeletons),
            "stored_joints": len(self._joints),
            "stored_poses": len(self._pose_snapshots),
            "stored_deform_results": len(self._deform_results),
            "total_joints_in_skeletons": total_joints_in_skeletons,
            "bound_skeletons": bound_skeletons,
            "total_compute_time_ms": round(self._total_compute_time_ms, 3),
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._skeletons.clear()
            self._joints.clear()
            self._skinning_data.clear()
            self._pose_snapshots.clear()
            self._deform_results.clear()
            self._skeleton_count = 0
            self._joint_count = 0
            self._pose_count = 0
            self._deform_count = 0
            self._total_compute_time_ms = 0.0

    # ------------------------------------------------------------------
    # Query Helpers
    # ------------------------------------------------------------------

    def get_joints_by_type(self, joint_type: str) -> List[SkeletonJoint]:
        resolved = _resolve_joint_type(joint_type)
        return [
            j for j in self._joints.values()
            if j.joint_type == resolved
        ]

    def get_joints_for_skeleton(
        self, skeleton_id: str
    ) -> List[SkeletonJoint]:
        skeleton = self._skeletons.get(skeleton_id)
        if skeleton is None:
            return []
        return [
            j for j_id in skeleton.joint_ids
            if (j := self._joints.get(j_id))
        ]

    def get_all_skeletons(self) -> Dict[str, Dict[str, Any]]:
        return {sid: s.to_dict() for sid, s in self._skeletons.items()}

    def get_all_joints(self) -> Dict[str, Dict[str, Any]]:
        return {jid: j.to_dict() for jid, j in self._joints.items()}

    def get_all_poses(self) -> Dict[str, Dict[str, Any]]:
        return {pid: p.to_dict() for pid, p in self._pose_snapshots.items()}


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_skeleton_deformer() -> SkeletonDeformerSystem:
    return SkeletonDeformerSystem.get_instance()