"""
SparkLabs Engine - Procedural Animation System

Runtime procedural animation engine providing inverse kinematics (IK)
solvers, procedural walk cycles, ragdoll physics blending, and dynamic
motion synthesis for interactive game characters.

Architecture:
  EngineProceduralAnimation (Singleton)
    |-- IK Solvers (CCD, FABRIK, Jacobian, Two-Bone, Hybrid)
    |-- Procedural Motion Generator (walk, run, sneak, crawl, jump, swim, fly, idle)
    |-- Animation Blend Tree (linear, smooth-step, ease, additive, override blending)
    |-- Bone Constraint System (position, rotation, scale, look-at, distance, angle)
    |-- Physics-Blend System (ragdoll-to-animation weighted blending)
    |-- Dynamic Motion Synthesis (bobbing, swaying, secondary motion, breathing)

Key Capabilities:
  - Multiple IK solver methods with configurable iterations and tolerance
  - Procedural gait cycles driven by speed, stride length, and terrain slope
  - Weighted animation blending with smooth transitions and ease curves
  - Per-bone constraints for artist-directed motion control
  - Seamless blending between keyframe animation and ragdoll physics
  - Idle breathing and sway dynamics for lifelike stationary characters
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

class IKMethod(Enum):
    """Inverse kinematics solver methods."""
    CCD = "ccd"                    # Cyclic Coordinate Descent
    FABRIK = "fabrik"              # Forward And Backward Reaching IK
    JACOBIAN = "jacobian"          # Jacobian transpose / pseudoinverse
    TWO_BONE = "two_bone"          # Analytic two-bone IK (elbow/knee)
    HYBRID = "hybrid"              # CCD + FABRIK hybrid solver


class AnimationBlendMode(Enum):
    """Interpolation and blending modes for animation transitions."""
    LINEAR = "linear"
    SMOOTH_STEP = "smooth_step"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    ADDITIVE = "additive"
    OVERRIDE = "override"


class MotionStyle(Enum):
    """Procedural motion categories for character animation synthesis."""
    WALK = "walk"
    RUN = "run"
    SNEAK = "sneak"
    CRAWL = "crawl"
    JUMP = "jump"
    SWIM = "swim"
    FLY = "fly"
    IDLE = "idle"


class BoneConstraintType(Enum):
    """Types of per-bone constraints for procedural control."""
    POSITION = "position"
    ROTATION = "rotation"
    SCALE = "scale"
    LOOK_AT = "look_at"
    DISTANCE = "distance"
    ANGLE = "angle"


class ProceduralEffectType(Enum):
    """Categories of dynamic procedural effects applied to skeletons."""
    BOBBING = "bobbing"
    SWAYING = "swaying"
    SECONDARY_MOTION = "secondary_motion"
    BREATHING = "breathing"
    REACTIVE = "reactive"
    PHYSICS_DRIVEN = "physics_driven"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Bone:
    """Single bone in a skeletal hierarchy with constraints."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    parent_id: Optional[str] = None
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    length: float = 1.0
    children: List[str] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    rest_pose: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "position": list(self.position),
            "rotation": list(self.rotation),
            "length": round(self.length, 4),
            "children": list(self.children),
            "constraint_count": len(self.constraints),
            "rest_pose": {
                k: list(v) for k, v in self.rest_pose.items()
            },
        }


@dataclass
class Skeleton:
    """Hierarchical bone structure representing a character rig."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    root_bone_id: str = ""
    bones: Dict[str, Bone] = field(default_factory=dict)
    bone_order: List[str] = field(default_factory=list)
    total_bones: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root_bone_id": self.root_bone_id,
            "total_bones": self.total_bones,
            "bone_order": list(self.bone_order),
            "bone_ids": list(self.bones.keys()),
        }


@dataclass
class IKTarget:
    """Inverse kinematics solver target for a bone chain."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    bone_chain: List[str] = field(default_factory=list)
    target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    iterations: int = 10
    tolerance: float = 0.001
    method: IKMethod = IKMethod.CCD
    enabled: bool = True
    current_error: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "bone_chain": list(self.bone_chain),
            "target_position": list(self.target_position),
            "iterations": self.iterations,
            "tolerance": round(self.tolerance, 6),
            "method": self.method.value,
            "enabled": self.enabled,
            "current_error": round(self.current_error, 6),
        }


@dataclass
class ProceduralMotion:
    """Configuration and state for a procedural motion generator."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    motion_type: MotionStyle = MotionStyle.WALK
    target_skeleton_id: str = ""
    speed: float = 1.0
    stride_length: float = 1.0
    step_height: float = 0.15
    hip_sway: float = 0.05
    arm_swing: float = 0.3
    body_bob: float = 0.03
    ground_clearance: float = 0.02
    parameters: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "motion_type": self.motion_type.value,
            "target_skeleton_id": self.target_skeleton_id,
            "speed": round(self.speed, 3),
            "stride_length": round(self.stride_length, 3),
            "step_height": round(self.step_height, 3),
            "hip_sway": round(self.hip_sway, 3),
            "arm_swing": round(self.arm_swing, 3),
            "body_bob": round(self.body_bob, 3),
            "ground_clearance": round(self.ground_clearance, 3),
            "parameters": dict(self.parameters),
        }


@dataclass
class AnimationBlend:
    """Blend tree node that combines multiple animation sources."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    blend_mode: AnimationBlendMode = AnimationBlendMode.LINEAR
    source_animations: List[str] = field(default_factory=list)
    blend_weights: List[float] = field(default_factory=list)
    blend_duration: float = 0.3
    transition_window: float = 0.1
    current_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "blend_mode": self.blend_mode.value,
            "source_animations": list(self.source_animations),
            "blend_weights": [round(w, 4) for w in self.blend_weights],
            "blend_duration": round(self.blend_duration, 3),
            "transition_window": round(self.transition_window, 3),
            "current_time": round(self.current_time, 3),
        }


# ---------------------------------------------------------------------------
# EngineProceduralAnimation (Singleton)
# ---------------------------------------------------------------------------

class EngineProceduralAnimation:
    """
    Runtime procedural animation engine.

    Provides IK solving, procedural motion generation, animation
    blending, bone constraints, and ragdoll-to-animation physics
    blending for character rigs.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._skeletons: Dict[str, Skeleton] = {}
        self._ik_targets: Dict[str, IKTarget] = {}
        self._procedural_motions: Dict[str, ProceduralMotion] = {}
        self._blend_trees: Dict[str, AnimationBlend] = {}
        self._constraints: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        self._animation_cache: Dict[str, Dict[str, Any]] = {}
        self._stats: Dict[str, Any] = {
            "ik_solves_total": 0,
            "motions_generated": 0,
            "blends_evaluated": 0,
            "constraint_applications": 0,
            "physics_blends": 0,
            "last_update_time": 0.0,
        }

    # ------------------------------------------------------------------
    # Singleton Access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineProceduralAnimation":
        return cls()

    # ------------------------------------------------------------------
    # Skeleton Management
    # ------------------------------------------------------------------

    def create_skeleton(self, name: str, bones_data: List[Dict[str, Any]]) -> Skeleton:
        """
        Build a skeleton from a list of bone hierarchy definitions.

        Each entry in bones_data should contain keys: name, parent_id
        (optional), position, rotation, length. Bones are linked into
        a hierarchy via parent_id references.
        """
        skeleton = Skeleton(name=name, total_bones=len(bones_data))

        # First pass: create all Bone objects
        for bd in bones_data:
            bone = Bone(
                name=bd.get("name", ""),
                parent_id=bd.get("parent_id"),
                position=tuple(bd.get("position", (0.0, 0.0, 0.0))),
                rotation=tuple(bd.get("rotation", (0.0, 0.0, 0.0))),
                length=float(bd.get("length", 1.0)),
                constraints=list(bd.get("constraints", [])),
                rest_pose={
                    "position": tuple(bd.get("position", (0.0, 0.0, 0.0))),
                    "rotation": tuple(bd.get("rotation", (0.0, 0.0, 0.0))),
                },
            )
            skeleton.bones[bone.id] = bone

        # Second pass: link children
        for bone in skeleton.bones.values():
            if bone.parent_id and bone.parent_id in skeleton.bones:
                parent = skeleton.bones[bone.parent_id]
                if bone.id not in parent.children:
                    parent.children.append(bone.id)
            elif bone.parent_id is None or bone.parent_id not in skeleton.bones:
                if not skeleton.root_bone_id:
                    skeleton.root_bone_id = bone.id

        # Build breadth-first bone order
        skeleton.bone_order = self._compute_bone_order(skeleton)

        self._skeletons[skeleton.id] = skeleton
        return skeleton

    def _compute_bone_order(self, skeleton: Skeleton) -> List[str]:
        """Compute a breadth-first bone traversal order for the skeleton."""
        order: List[str] = []
        if not skeleton.root_bone_id:
            return order
        queue: List[str] = [skeleton.root_bone_id]
        while queue:
            bone_id = queue.pop(0)
            order.append(bone_id)
            bone = skeleton.bones.get(bone_id)
            if bone:
                queue.extend(bone.children)
        return order

    # ------------------------------------------------------------------
    # Inverse Kinematics
    # ------------------------------------------------------------------

    def add_ik_chain(
        self,
        skeleton_id: str,
        chain: List[str],
        target: Tuple[float, float, float],
        method: IKMethod = IKMethod.CCD,
        iterations: int = 10,
    ) -> IKTarget:
        """
        Register an IK solver target for a bone chain on a skeleton.

        The chain lists bone IDs from base to end-effector.
        """
        ik_target = IKTarget(
            bone_chain=list(chain),
            target_position=target,
            iterations=iterations,
            method=method,
        )
        self._ik_targets[ik_target.id] = ik_target
        return ik_target

    def solve_ik(
        self,
        skeleton_id: str,
        ik_target_id: str,
        max_iterations: int = 0,
    ) -> Skeleton:
        """
        Solve inverse kinematics for the specified IK target on the
        given skeleton, updating bone positions in place.

        Internally dispatches to the concrete solver based on the
        IKTarget.method field. Returns the updated skeleton.
        """
        skeleton = self._skeletons.get(skeleton_id)
        ik_target = self._ik_targets.get(ik_target_id)
        if skeleton is None or ik_target is None:
            if skeleton is None:
                raise ValueError(f"Skeleton '{skeleton_id}' not found")
            raise ValueError(f"IK target '{ik_target_id}' not found")

        if not ik_target.enabled:
            return skeleton

        iterations = max_iterations if max_iterations > 0 else ik_target.iterations

        if ik_target.method == IKMethod.CCD:
            ik_target.current_error = self._solve_ccd(
                skeleton, ik_target, iterations
            )
        elif ik_target.method == IKMethod.FABRIK:
            ik_target.current_error = self._solve_fabrik(
                skeleton, ik_target, iterations
            )
        elif ik_target.method == IKMethod.TWO_BONE:
            ik_target.current_error = self._solve_two_bone(
                skeleton, ik_target
            )
        elif ik_target.method == IKMethod.JACOBIAN:
            ik_target.current_error = self._solve_jacobian(
                skeleton, ik_target, iterations
            )
        elif ik_target.method == IKMethod.HYBRID:
            ik_target.current_error = self._solve_hybrid(
                skeleton, ik_target, iterations
            )

        self._stats["ik_solves_total"] += 1
        self._stats["last_update_time"] = _time_module.time()
        return skeleton

    def _solve_ccd(
        self, skeleton: Skeleton, ik_target: IKTarget, iterations: int
    ) -> float:
        """Cyclic Coordinate Descent IK solver."""
        target = ik_target.target_position
        chain = ik_target.bone_chain
        tolerance = ik_target.tolerance

        for _ in range(iterations):
            for i in range(len(chain) - 1, 0, -1):
                bone_id = chain[i]
                bone = skeleton.bones.get(bone_id)
                if bone is None:
                    continue

                # End-effector position (approximate as bone tip)
                ee_x = bone.position[0] + bone.length * math.cos(bone.rotation[0])
                ee_y = bone.position[1] + bone.length * math.sin(bone.rotation[1])
                ee_z = bone.position[2]
                ee = (ee_x, ee_y, ee_z)

                # Vector from bone base to end-effector
                to_ee = (ee[0] - bone.position[0], ee[1] - bone.position[1], ee[2] - bone.position[2])
                # Vector from bone base to target
                to_target = (target[0] - bone.position[0], target[1] - bone.position[1], target[2] - bone.position[2])

                # Compute rotation needed
                angle = self._angle_between(to_ee, to_target)
                if abs(angle) < tolerance:
                    continue

                # Rotate bone toward target (simplified 2D-plane rotation around Z)
                bone_rot = list(bone.rotation)
                bone_rot[2] += angle * 0.5  # half-step toward target
                bone.rotation = tuple(bone_rot)

                # Propagate position update to children
                self._propagate_transform(skeleton, bone_id)

            # Check convergence
            if len(chain) > 0:
                end_bone = skeleton.bones.get(chain[-1])
                if end_bone:
                    ee_x = end_bone.position[0] + end_bone.length * math.cos(end_bone.rotation[0])
                    ee_y = end_bone.position[1] + end_bone.length * math.sin(end_bone.rotation[1])
                    err = math.dist((ee_x, ee_y, end_bone.position[2]), target)
                    if err < tolerance:
                        return err

        # Final error
        if len(chain) > 0:
            end_bone = skeleton.bones.get(chain[-1])
            if end_bone:
                ee_x = end_bone.position[0] + end_bone.length * math.cos(end_bone.rotation[0])
                ee_y = end_bone.position[1] + end_bone.length * math.sin(end_bone.rotation[1])
                return math.dist((ee_x, ee_y, end_bone.position[2]), target)

        return ik_target.current_error

    def _solve_fabrik(
        self, skeleton: Skeleton, ik_target: IKTarget, iterations: int
    ) -> float:
        """Forward And Backward Reaching Inverse Kinematics solver."""
        target = ik_target.target_position
        chain = ik_target.bone_chain
        tolerance = ik_target.tolerance

        # Collect joint positions along the chain
        joint_positions: List[Tuple[float, float, float]] = []
        for bone_id in chain:
            bone = skeleton.bones.get(bone_id)
            if bone:
                joint_positions.append(bone.position)

        if len(joint_positions) < 2:
            return 0.0

        # Bone lengths (distance between consecutive joints)
        bone_lengths: List[float] = []
        for i in range(len(joint_positions) - 1):
            d = math.dist(joint_positions[i], joint_positions[i + 1])
            bone_lengths.append(max(d, 0.001))

        for _ in range(iterations):
            # Backward pass: from end-effector to base
            joint_positions[-1] = target
            for i in range(len(joint_positions) - 2, -1, -1):
                direction = (
                    joint_positions[i][0] - joint_positions[i + 1][0],
                    joint_positions[i][1] - joint_positions[i + 1][1],
                    joint_positions[i][2] - joint_positions[i + 1][2],
                )
                dist = math.sqrt(direction[0]**2 + direction[1]**2 + direction[2]**2)
                if dist < 1e-9:
                    continue
                nd = (direction[0] / dist, direction[1] / dist, direction[2] / dist)
                joint_positions[i] = (
                    joint_positions[i + 1][0] + nd[0] * bone_lengths[i],
                    joint_positions[i + 1][1] + nd[1] * bone_lengths[i],
                    joint_positions[i + 1][2] + nd[2] * bone_lengths[i],
                )

            # Forward pass: from base to end-effector
            # (Base position unchanged)
            for i in range(len(joint_positions) - 1):
                direction = (
                    joint_positions[i + 1][0] - joint_positions[i][0],
                    joint_positions[i + 1][1] - joint_positions[i][1],
                    joint_positions[i + 1][2] - joint_positions[i][2],
                )
                dist = math.sqrt(direction[0]**2 + direction[1]**2 + direction[2]**2)
                if dist < 1e-9:
                    continue
                nd = (direction[0] / dist, direction[1] / dist, direction[2] / dist)
                joint_positions[i + 1] = (
                    joint_positions[i][0] + nd[0] * bone_lengths[i],
                    joint_positions[i][1] + nd[1] * bone_lengths[i],
                    joint_positions[i][2] + nd[2] * bone_lengths[i],
                )

            # Check convergence
            err = math.dist(joint_positions[-1], target)
            if err < tolerance:
                # Write positions back to bones
                for idx, bone_id in enumerate(chain):
                    bone = skeleton.bones.get(bone_id)
                    if bone:
                        bone.position = joint_positions[idx]
                return err

        # Write positions back to bones
        for idx, bone_id in enumerate(chain):
            bone = skeleton.bones.get(bone_id)
            if bone:
                bone.position = joint_positions[idx]

        return math.dist(joint_positions[-1], target)

    def _solve_two_bone(self, skeleton: Skeleton, ik_target: IKTarget) -> float:
        """Analytic two-bone IK solver (e.g., arm: shoulder-elbow-wrist)."""
        chain = ik_target.bone_chain
        target = ik_target.target_position

        if len(chain) < 3:
            return self._solve_ccd(skeleton, ik_target, 5)

        bone0 = skeleton.bones.get(chain[0])
        bone1 = skeleton.bones.get(chain[1])
        bone2 = skeleton.bones.get(chain[2])
        if bone0 is None or bone1 is None or bone2 is None:
            return 0.0

        # Law of cosines solution
        l1 = bone0.length
        l2 = bone1.length
        base = bone0.position
        d = math.dist(base, target)
        d = max(min(d, l1 + l2 - 0.001), abs(l1 - l2) + 0.001)

        # Angle between upper bone and line to target
        cos_a = (l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d)
        cos_a = max(-1.0, min(1.0, cos_a))
        # Angle between upper and lower bone
        cos_b = (l1 * l1 + l2 * l2 - d * d) / (2.0 * l1 * l2)
        cos_b = max(-1.0, min(1.0, cos_b))

        # Direction from base to target
        dir_x = target[0] - base[0]
        dir_y = target[1] - base[1]
        dir_z = target[2] - base[2]
        dir_len = math.sqrt(dir_x**2 + dir_y**2 + dir_z**2)
        if dir_len < 1e-9:
            return math.dist(base, target)

        ndx, ndy, ndz = dir_x / dir_len, dir_y / dir_len, dir_z / dir_len

        # Base-to-target angle in the 2D plane
        base_angle = math.atan2(ndy, ndx)

        # Upper bone new rotation
        rot0 = list(bone0.rotation)
        rot0[2] = base_angle - math.acos(cos_a)
        bone0.rotation = tuple(rot0)

        # Elbow position
        elbow_x = base[0] + l1 * math.cos(rot0[2])
        elbow_y = base[1] + l1 * math.sin(rot0[2])
        bone1.position = (elbow_x, elbow_y, base[2])
        self._propagate_transform(skeleton, chain[1])

        # Lower bone rotation
        rot1 = list(bone1.rotation)
        rot1[2] = base_angle + math.pi - math.acos(cos_b)
        bone1.rotation = tuple(rot1)

        # End-effector position
        ee_x = elbow_x + l2 * math.cos(rot1[2])
        ee_y = elbow_y + l2 * math.sin(rot1[2])
        bone2.position = (ee_x, ee_y, base[2])
        self._propagate_transform(skeleton, chain[2])

        return math.dist((ee_x, ee_y, base[2]), target)

    def _solve_jacobian(
        self, skeleton: Skeleton, ik_target: IKTarget, iterations: int
    ) -> float:
        """Jacobian transpose / pseudoinverse IK solver (simplified)."""
        target = ik_target.target_position
        chain = ik_target.bone_chain
        tolerance = ik_target.tolerance

        for _ in range(iterations):
            # Compute end-effector position
            if not chain:
                break
            end_bone = skeleton.bones.get(chain[-1])
            if end_bone is None:
                break

            ee_x = end_bone.position[0] + end_bone.length * math.cos(end_bone.rotation[0])
            ee_y = end_bone.position[1] + end_bone.length * math.sin(end_bone.rotation[1])
            ee_z = end_bone.position[2]
            ee = (ee_x, ee_y, ee_z)

            error = (target[0] - ee[0], target[1] - ee[1], target[2] - ee[2])
            err_mag = math.sqrt(error[0]**2 + error[1]**2 + error[2]**2)
            if err_mag < tolerance:
                return err_mag

            # Stepping factor
            step = 0.1 * err_mag

            # Simplified Jacobian: move each bone slightly toward target
            for bone_id in reversed(chain):
                bone = skeleton.bones.get(bone_id)
                if bone is None:
                    continue
                # Gradient step toward target
                new_pos = list(bone.position)
                new_pos[0] += step * error[0] / err_mag * 0.5
                new_pos[1] += step * error[1] / err_mag * 0.5
                new_pos[2] += step * error[2] / err_mag * 0.5
                bone.position = tuple(new_pos)  # type: ignore[arg-type]
                self._propagate_transform(skeleton, bone_id)

        if chain:
            end_bone = skeleton.bones.get(chain[-1])
            if end_bone:
                ee_x = end_bone.position[0] + end_bone.length * math.cos(end_bone.rotation[0])
                ee_y = end_bone.position[1] + end_bone.length * math.sin(end_bone.rotation[1])
                return math.dist((ee_x, ee_y, end_bone.position[2]), target)

        return ik_target.current_error

    def _solve_hybrid(
        self, skeleton: Skeleton, ik_target: IKTarget, iterations: int
    ) -> float:
        """Hybrid solver: FABRIK for positioning, then CCD refinement."""
        err = self._solve_fabrik(skeleton, ik_target, max(iterations // 2, 3))
        err = self._solve_ccd(skeleton, ik_target, max(iterations // 2, 3))
        return err

    def _propagate_transform(self, skeleton: Skeleton, bone_id: str):
        """Recursively propagate a bone's transform to all its descendants."""
        bone = skeleton.bones.get(bone_id)
        if bone is None:
            return
        for child_id in bone.children:
            child = skeleton.bones.get(child_id)
            if child is None:
                continue
            # Position child at the tip of the parent bone
            px = bone.position[0] + bone.length * math.cos(bone.rotation[0])
            py = bone.position[1] + bone.length * math.sin(bone.rotation[1])
            pz = bone.position[2]
            child.position = (px, py, pz)
            self._propagate_transform(skeleton, child_id)

    # ------------------------------------------------------------------
    # Procedural Motion Generation
    # ------------------------------------------------------------------

    def create_procedural_motion(
        self,
        skeleton_id: str,
        motion_style: MotionStyle,
        speed: float = 1.0,
        stride_length: float = 1.0,
    ) -> ProceduralMotion:
        """
        Create a procedural motion generator for a skeleton.

        Configures default gait parameters based on motion style.
        """
        skeleton = self._skeletons.get(skeleton_id)
        if skeleton is None:
            raise ValueError(f"Skeleton '{skeleton_id}' not found")

        # Style-specific default parameters
        style_defaults: Dict[MotionStyle, Dict[str, float]] = {
            MotionStyle.WALK: {"step_height": 0.15, "hip_sway": 0.05, "arm_swing": 0.3, "body_bob": 0.03},
            MotionStyle.RUN: {"step_height": 0.3, "hip_sway": 0.08, "arm_swing": 0.6, "body_bob": 0.06},
            MotionStyle.SNEAK: {"step_height": 0.08, "hip_sway": 0.02, "arm_swing": 0.1, "body_bob": 0.02},
            MotionStyle.CRAWL: {"step_height": 0.03, "hip_sway": 0.1, "arm_swing": 0.15, "body_bob": 0.01},
            MotionStyle.JUMP: {"step_height": 0.8, "hip_sway": 0.0, "arm_swing": 0.4, "body_bob": 0.5},
            MotionStyle.SWIM: {"step_height": 0.2, "hip_sway": 0.12, "arm_swing": 0.5, "body_bob": 0.04},
            MotionStyle.FLY: {"step_height": 0.0, "hip_sway": 0.05, "arm_swing": 0.2, "body_bob": 0.08},
            MotionStyle.IDLE: {"step_height": 0.0, "hip_sway": 0.0, "arm_swing": 0.0, "body_bob": 0.0},
        }

        defaults = style_defaults.get(motion_style, style_defaults[MotionStyle.WALK])

        motion = ProceduralMotion(
            motion_type=motion_style,
            target_skeleton_id=skeleton_id,
            speed=speed,
            stride_length=stride_length,
            step_height=defaults["step_height"],
            hip_sway=defaults["hip_sway"],
            arm_swing=defaults["arm_swing"],
            body_bob=defaults["body_bob"],
            ground_clearance=0.02,
            parameters={"phase": 0.0, "cycle_time": stride_length / max(speed, 0.01)},
        )

        self._procedural_motions[motion.id] = motion
        return motion

    def update_procedural_motion(
        self,
        motion_id: str,
        delta_time: float,
        ground_contacts: Optional[List[Dict[str, Any]]] = None,
    ) -> Skeleton:
        """
        Generate a procedural animation frame for the given motion.

        Advances the gait phase, computes bone offsets for the stride
        cycle, and applies hip sway, arm swing, and body bobbing.
        """
        motion = self._procedural_motions.get(motion_id)
        if motion is None:
            raise ValueError(f"ProceduralMotion '{motion_id}' not found")

        skeleton = self._skeletons.get(motion.target_skeleton_id)
        if skeleton is None:
            raise ValueError(f"Skeleton '{motion.target_skeleton_id}' not found")

        # Advance phase
        cycle_time = motion.parameters.get("cycle_time", 1.0)
        phase_delta = delta_time * motion.speed / max(cycle_time, 0.01)
        phase = (motion.parameters.get("phase", 0.0) + phase_delta) % 1.0
        motion.parameters["phase"] = phase

        if motion.motion_type == MotionStyle.IDLE:
            return skeleton

        # Identify key bones by name convention
        hip_bone = self._find_bone_by_name(skeleton, ["hip", "pelvis", "hips", "root"])
        left_leg = self._find_bone_by_name(skeleton, ["left_leg", "leg_l", "thigh_l", "left_thigh"])
        right_leg = self._find_bone_by_name(skeleton, ["right_leg", "leg_r", "thigh_r", "right_thigh"])
        left_arm = self._find_bone_by_name(skeleton, ["left_arm", "arm_l", "upperarm_l", "left_upperarm"])
        right_arm = self._find_bone_by_name(skeleton, ["right_arm", "arm_r", "upperarm_r", "right_upperarm"])

        # Two-phase gait: left leg at phase 0, right leg at phase 0.5
        left_phase = phase
        right_phase = (phase + 0.5) % 1.0

        # Body bobbing (sinusoidal vertical offset)
        bob_offset = math.sin(phase * 2.0 * math.pi) * motion.body_bob
        if hip_bone:
            pos = list(hip_bone.position)
            pos[1] += bob_offset
            hip_bone.position = tuple(pos)  # type: ignore[arg-type]

        # Hip sway (lateral sinusoidal motion)
        sway_offset = math.sin(phase * 4.0 * math.pi) * motion.hip_sway
        if hip_bone:
            pos = list(hip_bone.position)
            pos[0] += sway_offset
            hip_bone.position = tuple(pos)  # type: ignore[arg-type]

        # Leg step cycle
        if left_leg:
            leg_rot = list(left_leg.rotation)
            leg_rot[2] = math.sin(left_phase * 2.0 * math.pi) * motion.step_height * 3.0
            left_leg.rotation = tuple(leg_rot)  # type: ignore[arg-type]

        if right_leg:
            leg_rot = list(right_leg.rotation)
            leg_rot[2] = math.sin(right_phase * 2.0 * math.pi) * motion.step_height * 3.0
            right_leg.rotation = tuple(leg_rot)  # type: ignore[arg-type]

        # Arm swing
        if left_arm:
            arm_rot = list(left_arm.rotation)
            arm_rot[2] = math.sin(right_phase * 2.0 * math.pi) * motion.arm_swing
            left_arm.rotation = tuple(arm_rot)  # type: ignore[arg-type]

        if right_arm:
            arm_rot = list(right_arm.rotation)
            arm_rot[2] = math.sin(left_phase * 2.0 * math.pi) * motion.arm_swing
            right_arm.rotation = tuple(arm_rot)  # type: ignore[arg-type]

        self._stats["motions_generated"] += 1
        self._stats["last_update_time"] = _time_module.time()
        return skeleton

    def _find_bone_by_name(self, skeleton: Skeleton, candidates: List[str]) -> Optional[Bone]:
        """Find a bone whose name contains any of the candidate substrings."""
        for bone_id, bone in skeleton.bones.items():
            lower_name = bone.name.lower()
            for candidate in candidates:
                if candidate in lower_name:
                    return bone
        return None

    # ------------------------------------------------------------------
    # Animation Blend Tree
    # ------------------------------------------------------------------

    def create_blend_tree(
        self,
        skeleton_id: str,
        animations: List[str],
        blend_mode: AnimationBlendMode = AnimationBlendMode.LINEAR,
    ) -> AnimationBlend:
        """
        Create an animation blend tree combining multiple animation
        sources with configurable blending mode.
        """
        skeleton = self._skeletons.get(skeleton_id)
        if skeleton is None:
            raise ValueError(f"Skeleton '{skeleton_id}' not found")

        num_sources = len(animations)
        # Initialize with equal weights
        base_weight = 1.0 / max(num_sources, 1)
        weights = [base_weight] * num_sources

        blend = AnimationBlend(
            blend_mode=blend_mode,
            source_animations=list(animations),
            blend_weights=weights,
        )

        self._blend_trees[blend.id] = blend
        return blend

    def update_blend_tree(
        self,
        blend_id: str,
        weights: List[float],
        delta_time: float,
    ) -> Skeleton:
        """
        Evaluate a blend tree with new weights, producing a blended
        skeleton pose via the configured blend mode.

        Interpolates current weights toward target weights over the
        blend duration for smooth transitions.
        """
        blend = self._blend_trees.get(blend_id)
        if blend is None:
            raise ValueError(f"AnimationBlend '{blend_id}' not found")

        # Advance time
        blend.current_time += delta_time

        # Normalize incoming weights
        total = sum(weights) if sum(weights) > 0 else 1.0
        target_weights = [w / total for w in weights]

        # Smoothly interpolate toward target weights
        blend_factor = min(delta_time / max(blend.blend_duration, 0.001), 1.0)
        for i in range(min(len(blend.blend_weights), len(target_weights))):
            # Apply ease function based on blend mode
            if blend.blend_mode == AnimationBlendMode.SMOOTH_STEP:
                t = blend_factor * blend_factor * (3.0 - 2.0 * blend_factor)
            elif blend.blend_mode == AnimationBlendMode.EASE_IN:
                t = blend_factor * blend_factor
            elif blend.blend_mode == AnimationBlendMode.EASE_OUT:
                t = 1.0 - (1.0 - blend_factor) * (1.0 - blend_factor)
            else:  # LINEAR, ADDITIVE, OVERRIDE
                t = blend_factor

            blend.blend_weights[i] = (
                blend.blend_weights[i] * (1.0 - t) + target_weights[i] * t
            )

        # Store cached animation data for each source
        cache_key = f"blend_{blend_id}"
        self._animation_cache[cache_key] = {
            "blend_mode": blend.blend_mode.value,
            "weights": list(blend.blend_weights),
            "time": blend.current_time,
            "sources": list(blend.source_animations),
        }

        self._stats["blends_evaluated"] += 1
        self._stats["last_update_time"] = _time_module.time()

        # Return a placeholder skeleton — in a full implementation this
        # would return the blended bone transforms from actual animation data.
        skeleton_id = blend.source_animations[0] if blend.source_animations else ""
        skeleton = self._skeletons.get(skeleton_id)
        if skeleton is None:
            skeleton = Skeleton(name="blend_output")
        return skeleton

    # ------------------------------------------------------------------
    # Bone Constraints
    # ------------------------------------------------------------------

    def add_bone_constraint(
        self,
        skeleton_id: str,
        bone_id: str,
        constraint_type: BoneConstraintType,
        params: Dict[str, Any],
    ) -> bool:
        """
        Add a constraint to a specific bone in a skeleton.

        Supported constraint types:
          - POSITION: clamp to min/max bounds
          - ROTATION: clamp to min/max angle ranges
          - SCALE: clamp to min/max scale factors
          - LOOK_AT: orient toward a target point
          - DISTANCE: maintain distance between two points
          - ANGLE: restrict angular range between bones
        """
        skeleton = self._skeletons.get(skeleton_id)
        if skeleton is None:
            return False

        bone = skeleton.bones.get(bone_id)
        if bone is None:
            return False

        constraint_entry = {
            "type": constraint_type.value,
            "params": dict(params),
            "created_at": _time_module.time(),
        }
        bone.constraints.append(constraint_entry)

        # Track constraints globally
        if skeleton_id not in self._constraints:
            self._constraints[skeleton_id] = {}
        if bone_id not in self._constraints[skeleton_id]:
            self._constraints[skeleton_id][bone_id] = []
        self._constraints[skeleton_id][bone_id].append(constraint_entry)

        self._stats["constraint_applications"] += 1

        # Apply constraint immediately if relevant
        if constraint_type == BoneConstraintType.POSITION:
            min_bounds = params.get("min_position")
            max_bounds = params.get("max_position")
            if min_bounds and max_bounds:
                pos = list(bone.position)
                for axis in range(3):
                    pos[axis] = max(min_bounds[axis], min(pos[axis], max_bounds[axis]))
                bone.position = tuple(pos)  # type: ignore[arg-type]

        elif constraint_type == BoneConstraintType.ROTATION:
            min_rot = params.get("min_rotation")
            max_rot = params.get("max_rotation")
            if min_rot and max_rot:
                rot = list(bone.rotation)
                for axis in range(3):
                    rot[axis] = max(min_rot[axis], min(rot[axis], max_rot[axis]))
                bone.rotation = tuple(rot)  # type: ignore[arg-type]

        elif constraint_type == BoneConstraintType.SCALE:
            min_scale = params.get("min_scale")
            max_scale = params.get("max_scale")
            if min_scale is not None and max_scale is not None:
                bone.length = max(min_scale, min(bone.length, max_scale))

        elif constraint_type == BoneConstraintType.LOOK_AT:
            target = params.get("target")
            if target:
                direction = (
                    target[0] - bone.position[0],
                    target[1] - bone.position[1],
                    target[2] - bone.position[2],
                )
                angle_z = math.atan2(direction[1], direction[0])
                rot = list(bone.rotation)
                rot[2] = angle_z
                bone.rotation = tuple(rot)  # type: ignore[arg-type]

        elif constraint_type == BoneConstraintType.DISTANCE:
            anchor = params.get("anchor_position")
            min_dist = params.get("min_distance", 0.0)
            max_dist = params.get("max_distance", float("inf"))
            if anchor:
                d = math.dist(bone.position, anchor)
                if d < min_dist or d > max_dist:
                    # Clamp distance
                    clamped_d = max(min_dist, min(d, max_dist))
                    if d > 0:
                        scale = clamped_d / d
                        pos = list(bone.position)
                        for axis in range(3):
                            pos[axis] = anchor[axis] + (pos[axis] - anchor[axis]) * scale
                        bone.position = tuple(pos)  # type: ignore[arg-type]

        elif constraint_type == BoneConstraintType.ANGLE:
            ref_bone_id = params.get("reference_bone_id")
            min_angle = params.get("min_angle", -math.pi)
            max_angle = params.get("max_angle", math.pi)
            if ref_bone_id:
                ref_bone = skeleton.bones.get(ref_bone_id)
                if ref_bone:
                    angle_diff = bone.rotation[2] - ref_bone.rotation[2]
                    if angle_diff < min_angle or angle_diff > max_angle:
                        clamped = max(min_angle, min(angle_diff, max_angle))
                        rot = list(bone.rotation)
                        rot[2] = ref_bone.rotation[2] + clamped
                        bone.rotation = tuple(rot)  # type: ignore[arg-type]

        return True

    # ------------------------------------------------------------------
    # Physics Blending
    # ------------------------------------------------------------------

    def apply_physics_blend(
        self,
        skeleton_id: str,
        rigidbody_states: Dict[str, Dict[str, Any]],
        blend_weight: float,
    ) -> Skeleton:
        """
        Blend ragdoll physics simulation results with animated bone
        transforms using a weighted interpolation.

        rigidbody_states maps bone IDs to physics-simulated transforms
        with keys: 'position', 'rotation'. blend_weight in [0,1]
        controls the mix (0 = full animation, 1 = full ragdoll).
        """
        skeleton = self._skeletons.get(skeleton_id)
        if skeleton is None:
            raise ValueError(f"Skeleton '{skeleton_id}' not found")

        blend_w = max(0.0, min(1.0, blend_weight))
        anim_w = 1.0 - blend_w

        for bone_id, rb_state in rigidbody_states.items():
            bone = skeleton.bones.get(bone_id)
            if bone is None:
                continue

            rb_pos = rb_state.get("position")
            rb_rot = rb_state.get("rotation")

            if rb_pos:
                pos = list(bone.position)
                for axis in range(min(3, len(rb_pos))):
                    pos[axis] = pos[axis] * anim_w + rb_pos[axis] * blend_w
                bone.position = tuple(pos)  # type: ignore[arg-type]

            if rb_rot:
                rot = list(bone.rotation)
                for axis in range(min(3, len(rb_rot))):
                    rot[axis] = rot[axis] * anim_w + rb_rot[axis] * blend_w
                bone.rotation = tuple(rot)  # type: ignore[arg-type]

        self._stats["physics_blends"] += 1
        self._stats["last_update_time"] = _time_module.time()
        return skeleton

    # ------------------------------------------------------------------
    # Dynamic Motion Synthesis
    # ------------------------------------------------------------------

    def generate_idle_motion(
        self,
        skeleton_id: str,
        breathing_rate: float = 0.3,
        sway_intensity: float = 0.02,
    ) -> Skeleton:
        """
        Generate a dynamic idle animation with breathing and subtle
        body sway for a stationary character.
        """
        skeleton = self._skeletons.get(skeleton_id)
        if skeleton is None:
            raise ValueError(f"Skeleton '{skeleton_id}' not found")

        t = _time_module.time()

        # Breathing: sinusoidal chest/spine scale or vertical bob
        breath = math.sin(t * breathing_rate * 2.0 * math.pi) * sway_intensity * 0.5

        # Sway: slow lateral oscillation
        sway = math.sin(t * 0.5 * math.pi) * sway_intensity

        # Find torso bones by name
        spine = self._find_bone_by_name(skeleton, ["spine", "chest", "torso", "spine1"])
        head = self._find_bone_by_name(skeleton, ["head", "neck"])

        if spine:
            pos = list(spine.position)
            pos[1] += breath  # vertical breathing motion
            pos[0] += sway   # lateral sway
            spine.position = tuple(pos)  # type: ignore[arg-type]

        if head:
            pos = list(head.position)
            pos[0] += sway * 1.5  # head sways more than body
            pos[1] += breath * 0.7
            head.position = tuple(pos)  # type: ignore[arg-type]

        # Subtle arm dangle with secondary motion
        left_arm = self._find_bone_by_name(skeleton, ["left_arm", "arm_l", "upperarm_l"])
        right_arm = self._find_bone_by_name(skeleton, ["right_arm", "arm_r", "upperarm_r"])

        if left_arm:
            rot = list(left_arm.rotation)
            rot[2] += math.sin(t * 1.3) * sway_intensity * 0.3
            left_arm.rotation = tuple(rot)  # type: ignore[arg-type]

        if right_arm:
            rot = list(right_arm.rotation)
            rot[2] += math.sin(t * 1.3 + math.pi) * sway_intensity * 0.3
            right_arm.rotation = tuple(rot)  # type: ignore[arg-type]

        self._stats["motions_generated"] += 1
        self._stats["last_update_time"] = _time_module.time()
        return skeleton

    def generate_walk_cycle(
        self,
        skeleton_id: str,
        speed: float = 1.0,
        terrain_slope: float = 0.0,
    ) -> Skeleton:
        """
        Generate a dynamic walk cycle adapted to terrain slope.

        Speed controls gait frequency; terrain_slope (radians) adjusts
        foot placement and body lean to match inclined surfaces.
        """
        motion = self.create_procedural_motion(
            skeleton_id, MotionStyle.WALK, speed=speed, stride_length=speed * 0.8
        )
        motion.parameters["terrain_slope"] = terrain_slope

        # Adjust step height based on slope (steeper = higher steps)
        if abs(terrain_slope) > 0.1:
            motion.step_height += abs(terrain_slope) * 0.3

        # Body lean: lean forward on uphill, backward on downhill
        body_lean = terrain_slope * 0.15

        # Generate one frame at the current phase
        skeleton = self.update_procedural_motion(motion.id, delta_time=1.0 / 60.0)

        # Apply body lean to root/spine
        hip = self._find_bone_by_name(skeleton, ["hip", "pelvis", "hips", "root"])
        if hip and body_lean != 0.0:
            rot = list(hip.rotation)
            rot[2] += body_lean  # pitch lean
            hip.rotation = tuple(rot)  # type: ignore[arg-type]

        return skeleton

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _angle_between(
        self,
        v1: Tuple[float, float, float],
        v2: Tuple[float, float, float],
    ) -> float:
        """Compute the angle in radians between two 3D vectors."""
        dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)
        if mag1 < 1e-12 or mag2 < 1e-12:
            return 0.0
        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        return math.acos(cos_angle)

    def get_status(self) -> Dict[str, Any]:
        """Return a status summary of the procedural animation engine."""
        total_bones = sum(s.total_bones for s in self._skeletons.values())
        total_constraints = sum(
            len(bone_list)
            for skel_map in self._constraints.values()
            for bone_list in skel_map.values()
        )
        return {
            "skeletons_count": len(self._skeletons),
            "ik_chains": len(self._ik_targets),
            "motions": len(self._procedural_motions),
            "blends": len(self._blend_trees),
            "bones_total": total_bones,
            "constraints": total_constraints,
            "stats": dict(self._stats),
        }

    def reset(self) -> None:
        """Reset all state in the procedural animation engine."""
        self._skeletons.clear()
        self._ik_targets.clear()
        self._procedural_motions.clear()
        self._blend_trees.clear()
        self._constraints.clear()
        self._animation_cache.clear()
        self._stats = {
            "ik_solves_total": 0,
            "motions_generated": 0,
            "blends_evaluated": 0,
            "constraint_applications": 0,
            "physics_blends": 0,
            "last_update_time": 0.0,
        }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

_procedural_animation: Optional[EngineProceduralAnimation] = None


def get_procedural_animation() -> EngineProceduralAnimation:
    """Return the singleton EngineProceduralAnimation instance."""
    global _procedural_animation
    if _procedural_animation is None:
        _procedural_animation = EngineProceduralAnimation()
    return _procedural_animation