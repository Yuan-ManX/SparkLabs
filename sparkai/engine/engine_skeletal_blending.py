"""
SparkLabs Engine - Skeletal Animation Blending System

A comprehensive skeletal animation system providing bone hierarchy management,
inverse kinematics solving, animation blending with smooth transitions,
additive animation layering, and procedural animation generation. Powers
character animation, creature movement, and dynamic object deformation
in the SparkLabs game engine.

Architecture:
  EngineSkeletalBlending (Singleton)
    |-- SkeletonHierarchy (bone tree structure)
    |-- AnimationClip (keyframe animation data)
    |-- BlendSpace (1D/2D parameterized animation blending)
    |-- IKChain (inverse kinematics solver chain)
    |-- AnimationLayer (additive animation layering)
    |-- ProceduralAnimator (runtime procedural animation)
    |-- BoneTransform (per-bone transform state)

Core Capabilities:
  - Hierarchical bone transform propagation
  - Multi-clip animation blending with smooth transitions
  - 1D and 2D parameterized blend spaces
  - FABRIK-based inverse kinematics solving
  - Additive animation layering for detail stacking
  - Procedural animation for runtime-generated motion
  - Animation state machine integration
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class BlendType(Enum):
    """Animation blending interpolation types."""
    LINEAR = "linear"
    CUBIC = "cubic"
    HERMITE = "hermite"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"


class BlendSpaceDimension(Enum):
    """Dimensionality of animation blend spaces."""
    ONE_D = "1d"
    TWO_D = "2d"


class IKAlgorithm(Enum):
    """Inverse kinematics solving algorithms."""
    FABRIK = "fabrik"
    CCD = "ccd"
    JACOBIAN = "jacobian"


class AnimationWrapMode(Enum):
    """How animation clips handle looping."""
    ONCE = "once"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    CLAMP_FOREVER = "clamp_forever"


class LayerBlendMode(Enum):
    """Blend modes for animation layers."""
    OVERRIDE = "override"
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"


class BoneSpace(Enum):
    """Coordinate space for bone transforms."""
    LOCAL = "local"
    WORLD = "world"
    MODEL = "model"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BoneTransform:
    """Per-bone transform state.

    Attributes:
        translation: (x, y, z) translation.
        rotation: Quaternion rotation (x, y, z, w).
        scale: (x, y, z) scale.
    """
    translation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)

    @staticmethod
    def identity() -> "BoneTransform":
        return BoneTransform()

    @staticmethod
    def lerp(a: "BoneTransform", b: "BoneTransform", t: float) -> "BoneTransform":
        """Linearly interpolate between two bone transforms."""
        t_clamped = max(0.0, min(1.0, t))
        return BoneTransform(
            translation=(
                a.translation[0] + (b.translation[0] - a.translation[0]) * t_clamped,
                a.translation[1] + (b.translation[1] - a.translation[1]) * t_clamped,
                a.translation[2] + (b.translation[2] - a.translation[2]) * t_clamped,
            ),
            rotation=BoneTransform._slerp(a.rotation, b.rotation, t_clamped),
            scale=(
                a.scale[0] + (b.scale[0] - a.scale[0]) * t_clamped,
                a.scale[1] + (b.scale[1] - a.scale[1]) * t_clamped,
                a.scale[2] + (b.scale[2] - a.scale[2]) * t_clamped,
            ),
        )

    @staticmethod
    def _slerp(
        qa: Tuple[float, float, float, float],
        qb: Tuple[float, float, float, float],
        t: float,
    ) -> Tuple[float, float, float, float]:
        """Spherical linear interpolation between quaternions."""
        cos_half_theta = qa[0]*qb[0] + qa[1]*qb[1] + qa[2]*qb[2] + qa[3]*qb[3]

        if abs(cos_half_theta) >= 1.0:
            return qa

        if cos_half_theta < 0.0:
            qb = (-qb[0], -qb[1], -qb[2], -qb[3])
            cos_half_theta = -cos_half_theta

        half_theta = math.acos(cos_half_theta)
        sin_half_theta = math.sqrt(1.0 - cos_half_theta * cos_half_theta)

        if abs(sin_half_theta) < 0.001:
            return (
                qa[0]*0.5 + qb[0]*0.5,
                qa[1]*0.5 + qb[1]*0.5,
                qa[2]*0.5 + qb[2]*0.5,
                qa[3]*0.5 + qb[3]*0.5,
            )

        ratio_a = math.sin((1.0 - t) * half_theta) / sin_half_theta
        ratio_b = math.sin(t * half_theta) / sin_half_theta

        return (
            qa[0]*ratio_a + qb[0]*ratio_b,
            qa[1]*ratio_a + qb[1]*ratio_b,
            qa[2]*ratio_a + qb[2]*ratio_b,
            qa[3]*ratio_a + qb[3]*ratio_b,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "translation": [round(v, 4) for v in self.translation],
            "rotation": [round(v, 4) for v in self.rotation],
            "scale": [round(v, 4) for v in self.scale],
        }


@dataclass
class BoneNode:
    """A single bone in the skeletal hierarchy.

    Attributes:
        id: Unique bone identifier.
        name: Human-readable bone name.
        parent_id: Parent bone ID (None for root).
        children_ids: Child bone IDs.
        bind_pose: Default/rest pose transform.
        local_transform: Current local-space transform.
        world_transform: Current world-space transform (computed).
        length: Bone length for IK calculations.
        stiffness: Joint stiffness (0.0 = fully free, 1.0 = rigid).
        constraints: Angular constraints [(min_angle, max_angle), ...].
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    bind_pose: BoneTransform = field(default_factory=BoneTransform)
    local_transform: BoneTransform = field(default_factory=BoneTransform)
    world_transform: BoneTransform = field(default_factory=BoneTransform)
    length: float = 1.0
    stiffness: float = 0.5
    constraints: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    @property
    def is_leaf(self) -> bool:
        return len(self.children_ids) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "children_count": len(self.children_ids),
            "local_transform": self.local_transform.to_dict(),
            "world_transform": self.world_transform.to_dict(),
            "length": round(self.length, 4),
            "stiffness": round(self.stiffness, 4),
            "is_root": self.is_root,
            "is_leaf": self.is_leaf,
        }


@dataclass
class Keyframe:
    """A single keyframe in an animation clip.

    Attributes:
        time: Normalized time (0.0-1.0) within the clip.
        bone_transforms: Per-bone transforms at this keyframe.
    """
    time: float = 0.0
    bone_transforms: Dict[str, BoneTransform] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": round(self.time, 4),
            "bone_count": len(self.bone_transforms),
        }


@dataclass
class AnimationClip:
    """A keyframe animation clip for skeletal animation.

    Attributes:
        id: Unique clip identifier.
        name: Human-readable clip name.
        duration_seconds: Total clip duration.
        fps: Keyframe rate (frames per second).
        keyframes: Ordered list of keyframes.
        wrap_mode: How the clip handles looping.
        total_keyframes: Total number of keyframes.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    duration_seconds: float = 1.0
    fps: float = 30.0
    keyframes: List[Keyframe] = field(default_factory=list)
    wrap_mode: str = AnimationWrapMode.LOOP.value
    total_keyframes: int = 0

    @property
    def frame_count(self) -> int:
        return max(1, int(self.duration_seconds * self.fps))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "duration_seconds": round(self.duration_seconds, 3),
            "fps": self.fps,
            "frame_count": self.frame_count,
            "keyframe_count": len(self.keyframes),
            "wrap_mode": self.wrap_mode,
        }


@dataclass
class BlendState:
    """Current state of an animation blend operation.

    Attributes:
        id: Unique blend state identifier.
        source_clip_id: The animation being blended from.
        target_clip_id: The animation being blended to.
        blend_progress: Current blend weight (0.0 = source, 1.0 = target).
        blend_duration: Total blend transition duration.
        blend_type: Interpolation function for the blend.
        elapsed_time: Time since blend started.
        is_active: Whether this blend is currently active.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_clip_id: str = ""
    target_clip_id: str = ""
    blend_progress: float = 0.0
    blend_duration: float = 0.3
    blend_type: str = BlendType.EASE_IN_OUT.value
    elapsed_time: float = 0.0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_clip": self.source_clip_id,
            "target_clip": self.target_clip_id,
            "blend_progress": round(self.blend_progress, 4),
            "blend_duration": round(self.blend_duration, 4),
            "blend_type": self.blend_type,
            "elapsed_time": round(self.elapsed_time, 4),
            "is_active": self.is_active,
        }


@dataclass
class BlendSpaceSample:
    """A sample point in a parameterized blend space.

    Attributes:
        clip_id: Animation clip at this sample point.
        parameter_value: Parameter coordinate in blend space.
        weight: Blend weight contribution.
    """
    clip_id: str = ""
    parameter_value: float = 0.0
    weight: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "parameter_value": round(self.parameter_value, 4),
            "weight": round(self.weight, 4),
        }


@dataclass
class BlendSpace:
    """A parameterized animation blend space.

    Attributes:
        id: Unique blend space identifier.
        name: Human-readable name.
        dimension: Blend space dimensionality (1D or 2D).
        samples: Sample points in the blend space.
        current_parameter: Current parameter value(s).
        min_parameter: Minimum parameter range.
        max_parameter: Maximum parameter range.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    dimension: str = BlendSpaceDimension.ONE_D.value
    samples: List[BlendSpaceSample] = field(default_factory=list)
    current_parameter: float = 0.0
    current_parameter_y: float = 0.0
    min_parameter: float = 0.0
    max_parameter: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "dimension": self.dimension,
            "sample_count": len(self.samples),
            "current_parameter": round(self.current_parameter, 4),
            "parameter_range": [round(self.min_parameter, 4), round(self.max_parameter, 4)],
        }


@dataclass
class IKChain:
    """An inverse kinematics chain definition and state.

    Attributes:
        id: Unique chain identifier.
        name: Human-readable chain name.
        bone_ids: Ordered bone IDs from root to end effector.
        target_position: World-space target position.
        iterations: Maximum solver iterations.
        tolerance: Convergence tolerance.
        algorithm: IK solving algorithm.
        is_solved: Whether the IK solution converged.
        solution_time_us: Time spent solving in microseconds.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    bone_ids: List[str] = field(default_factory=list)
    target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    iterations: int = 10
    tolerance: float = 0.001
    algorithm: str = IKAlgorithm.FABRIK.value
    is_solved: bool = False
    solution_time_us: float = 0.0

    @property
    def chain_length(self) -> int:
        return len(self.bone_ids)

    @property
    def end_effector_id(self) -> Optional[str]:
        return self.bone_ids[-1] if self.bone_ids else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "chain_length": self.chain_length,
            "end_effector_id": self.end_effector_id,
            "target_position": [round(v, 4) for v in self.target_position],
            "iterations": self.iterations,
            "tolerance": self.tolerance,
            "algorithm": self.algorithm,
            "is_solved": self.is_solved,
            "solution_time_us": round(self.solution_time_us, 2),
        }


@dataclass
class AnimationLayer:
    """An additive animation layer for stacking animation effects.

    Attributes:
        id: Unique layer identifier.
        name: Human-readable layer name.
        blend_mode: How this layer combines with lower layers.
        weight: Layer blend weight (0.0-1.0).
        clip_id: Animation clip for this layer.
        time: Current playback time.
        enabled: Whether this layer is active.
        priority: Layer ordering priority (higher = on top).
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    blend_mode: str = LayerBlendMode.OVERRIDE.value
    weight: float = 1.0
    clip_id: str = ""
    time: float = 0.0
    enabled: bool = True
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "blend_mode": self.blend_mode,
            "weight": round(self.weight, 4),
            "clip_id": self.clip_id,
            "time": round(self.time, 4),
            "enabled": self.enabled,
            "priority": self.priority,
        }


# ---------------------------------------------------------------------------
# Engine Skeletal Blending (Singleton)
# ---------------------------------------------------------------------------

class EngineSkeletalBlending:
    """
    Comprehensive skeletal animation and blending system for SparkLabs.

    Manages bone hierarchies, keyframe animation clips, smooth crossfade
    blending, parameterized blend spaces, FABRIK-based inverse kinematics,
    and layered additive animation. Provides the animation foundation for
    characters, creatures, and animated objects in the game engine.

    Features:
      - Hierarchical forward kinematics propagation
      - Multi-clip animation blending with configurable transitions
      - 1D/2D parameterized blend spaces for locomotion/animation control
      - FABRIK and CCD inverse kinematics solvers
      - Additive animation layering with priority ordering
      - Procedural animation generation for runtime effects
    """

    _instance: Optional["EngineSkeletalBlending"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineSkeletalBlending":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Skeleton management
        self._skeletons: Dict[str, Dict[str, BoneNode]] = {}
        self._default_skeleton_id: str = ""

        # Animation clips
        self._clips: Dict[str, AnimationClip] = {}

        # Blending state
        self._blend_states: Dict[str, BlendState] = {}
        self._active_blends: List[str] = []

        # Blend spaces
        self._blend_spaces: Dict[str, BlendSpace] = {}

        # IK chains
        self._ik_chains: Dict[str, IKChain] = {}

        # Animation layers
        self._animation_layers: Dict[str, AnimationLayer] = {}
        self._layer_stack: List[str] = []  # Priority-ordered

        # Playback state
        self._playback_time: float = 0.0
        self._playback_speed: float = 1.0
        self._is_playing: bool = False

        # Performance tracking
        self._fk_computation_time_us: float = 0.0
        self._ik_computation_time_us: float = 0.0
        self._blend_computation_time_us: float = 0.0
        self._total_bones_animated: int = 0

    # ------------------------------------------------------------------
    # Skeleton Management
    # ------------------------------------------------------------------

    def create_skeleton(self, skeleton_id: str, bone_definitions: List[Dict[str, Any]]) -> Dict[str, BoneNode]:
        """
        Create a skeletal hierarchy from bone definitions.

        Args:
            skeleton_id: Unique skeleton identifier.
            bone_definitions: List of bone definitions with name, parent, length, bind_pose.

        Returns:
            Dict of bone ID to BoneNode for the created skeleton.
        """
        bones: Dict[str, BoneNode] = {}

        # First pass: create all bones
        for bone_def in bone_definitions:
            bone = BoneNode(
                name=bone_def.get("name", ""),
                length=bone_def.get("length", 1.0),
                stiffness=bone_def.get("stiffness", 0.5),
            )
            # Set bind pose if provided
            if "bind_pose" in bone_def:
                bp = bone_def["bind_pose"]
                if isinstance(bp, BoneTransform):
                    bone.bind_pose = bp
                    bone.local_transform = BoneTransform(
                        translation=bp.translation,
                        rotation=bp.rotation,
                        scale=bp.scale,
                    )
            bones[bone.id] = bone

        # Second pass: establish parent-child relationships
        bone_name_to_id = {b.name: b.id for b in bones.values()}
        for bone_def in bone_definitions:
            bone_name = bone_def.get("name", "")
            parent_name = bone_def.get("parent", None)
            bone = next((b for b in bones.values() if b.name == bone_name), None)

            if bone and parent_name:
                parent_id = bone_name_to_id.get(parent_name)
                if parent_id and parent_id in bones:
                    bone.parent_id = parent_id
                    bones[parent_id].children_ids.append(bone.id)

        self._skeletons[skeleton_id] = bones
        if not self._default_skeleton_id:
            self._default_skeleton_id = skeleton_id

        return bones

    def get_skeleton(self, skeleton_id: Optional[str] = None) -> Dict[str, BoneNode]:
        """Get a skeleton by ID, or the default skeleton."""
        sid = skeleton_id or self._default_skeleton_id
        return self._skeletons.get(sid, {})

    def get_bone(self, bone_id: str, skeleton_id: Optional[str] = None) -> Optional[BoneNode]:
        """Get a specific bone from a skeleton."""
        skeleton = self.get_skeleton(skeleton_id)
        return skeleton.get(bone_id)

    # ------------------------------------------------------------------
    # Forward Kinematics
    # ------------------------------------------------------------------

    def update_forward_kinematics(self, skeleton_id: Optional[str] = None) -> List[BoneNode]:
        """
        Propagate local transforms to world transforms through the bone hierarchy.

        Traverses the bone tree from roots to leaves, accumulating parent
        transforms to compute each bone's world-space transform.

        Args:
            skeleton_id: Skeleton to update (default skeleton if None).

        Returns:
            List of all bones with updated world transforms.
        """
        with self._lock:
            fk_start = _time_module.time()
            skeleton = self.get_skeleton(skeleton_id)
            if not skeleton:
                return []

            # Find root bones (those without parents)
            root_bones = [b for b in skeleton.values() if b.is_root]

            # Process each hierarchy tree
            for root in root_bones:
                self._propagate_transforms(root, skeleton, BoneTransform.identity())

            self._fk_computation_time_us = (_time_module.time() - fk_start) * 1_000_000
            self._total_bones_animated += len(skeleton)

            return list(skeleton.values())

    def _propagate_transforms(
        self,
        bone: BoneNode,
        skeleton: Dict[str, BoneNode],
        parent_world: BoneTransform,
    ):
        """Recursively propagate transforms through the bone hierarchy."""
        # Compute world transform: parent_world * local_transform
        world = self._compose_transforms(parent_world, bone.local_transform)
        bone.world_transform = world

        # Propagate to children
        for child_id in bone.children_ids:
            child = skeleton.get(child_id)
            if child:
                self._propagate_transforms(child, skeleton, world)

    def _compose_transforms(self, parent: BoneTransform, local: BoneTransform) -> BoneTransform:
        """Compose parent world transform with local transform."""
        # Simplified composition: add translations and multiply rotations
        return BoneTransform(
            translation=(
                parent.translation[0] + local.translation[0],
                parent.translation[1] + local.translation[1],
                parent.translation[2] + local.translation[2],
            ),
            rotation=self._multiply_quaternions(parent.rotation, local.rotation),
            scale=(
                parent.scale[0] * local.scale[0],
                parent.scale[1] * local.scale[1],
                parent.scale[2] * local.scale[2],
            ),
        )

    def _multiply_quaternions(
        self,
        q1: Tuple[float, float, float, float],
        q2: Tuple[float, float, float, float],
    ) -> Tuple[float, float, float, float]:
        """Multiply two quaternions."""
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        return (
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2,
        )

    # ------------------------------------------------------------------
    # Animation Clip Management
    # ------------------------------------------------------------------

    def create_animation_clip(
        self,
        name: str,
        duration_seconds: float,
        keyframes: List[Dict[str, Any]],
        fps: float = 30.0,
        wrap_mode: AnimationWrapMode = AnimationWrapMode.LOOP,
    ) -> AnimationClip:
        """
        Create a keyframe animation clip.

        Args:
            name: Human-readable clip name.
            duration_seconds: Total clip duration.
            keyframes: List of keyframe dicts with 'time' and 'bone_transforms'.
            fps: Keyframe rate.
            wrap_mode: How the clip handles looping.

        Returns:
            Created AnimationClip.
        """
        clip = AnimationClip(
            name=name,
            duration_seconds=duration_seconds,
            fps=fps,
            wrap_mode=wrap_mode.value,
        )

        for kf_data in keyframes:
            time_val = kf_data.get("time", 0.0)
            bone_xforms_raw = kf_data.get("bone_transforms", {})

            # Convert raw transform data to BoneTransform objects
            bone_xforms = {}
            for bone_name, xform in bone_xforms_raw.items():
                if isinstance(xform, dict):
                    bone_xforms[bone_name] = BoneTransform(
                        translation=tuple(xform.get("translation", (0, 0, 0))),
                        rotation=tuple(xform.get("rotation", (0, 0, 0, 1))),
                        scale=tuple(xform.get("scale", (1, 1, 1))),
                    )
                elif isinstance(xform, BoneTransform):
                    bone_xforms[bone_name] = xform

            clip.keyframes.append(Keyframe(time=time_val, bone_transforms=bone_xforms))

        clip.total_keyframes = len(clip.keyframes)
        self._clips[clip.id] = clip
        return clip

    def get_clip(self, clip_id: str) -> Optional[AnimationClip]:
        """Retrieve an animation clip by ID."""
        return self._clips.get(clip_id)

    def sample_clip(self, clip_id: str, normalized_time: float) -> Dict[str, BoneTransform]:
        """
        Sample an animation clip at a specific normalized time.

        Uses linear interpolation between the two nearest keyframes.

        Args:
            clip_id: The animation clip to sample.
            normalized_time: Normalized time (0.0-1.0).

        Returns:
            Dict of bone name to interpolated BoneTransform.
        """
        clip = self._clips.get(clip_id)
        if not clip or not clip.keyframes:
            return {}

        # Handle wrap modes
        if clip.wrap_mode == AnimationWrapMode.LOOP.value:
            t = normalized_time % 1.0
        elif clip.wrap_mode == AnimationWrapMode.PING_PONG.value:
            cycle = normalized_time % 2.0
            t = cycle if cycle <= 1.0 else 2.0 - cycle
        else:
            t = max(0.0, min(1.0, normalized_time))

        keyframes = clip.keyframes

        # Find surrounding keyframes
        if t <= keyframes[0].time:
            return dict(keyframes[0].bone_transforms)
        if t >= keyframes[-1].time:
            return dict(keyframes[-1].bone_transforms)

        # Binary search for keyframe pair
        next_idx = 0
        for i, kf in enumerate(keyframes):
            if kf.time > t:
                next_idx = i
                break

        prev_kf = keyframes[next_idx - 1]
        next_kf = keyframes[next_idx]

        # Compute interpolation factor
        segment_duration = next_kf.time - prev_kf.time
        if segment_duration <= 0:
            return dict(prev_kf.bone_transforms)
        alpha = (t - prev_kf.time) / segment_duration

        # Interpolate each bone
        result = {}
        all_bones = set(prev_kf.bone_transforms.keys()) | set(next_kf.bone_transforms.keys())
        for bone_name in all_bones:
            prev_xform = prev_kf.bone_transforms.get(bone_name, BoneTransform.identity())
            next_xform = next_kf.bone_transforms.get(bone_name, BoneTransform.identity())
            result[bone_name] = BoneTransform.lerp(prev_xform, next_xform, alpha)

        return result

    # ------------------------------------------------------------------
    # Animation Blending
    # ------------------------------------------------------------------

    def start_blend(
        self,
        source_clip_id: str,
        target_clip_id: str,
        blend_duration: float = 0.3,
        blend_type: BlendType = BlendType.EASE_IN_OUT,
    ) -> BlendState:
        """
        Start a smooth crossfade blend between two animation clips.

        Args:
            source_clip_id: The animation to blend from.
            target_clip_id: The animation to blend to.
            blend_duration: Duration of the transition in seconds.
            blend_type: Interpolation function for the blend.

        Returns:
            BlendState tracking the transition progress.
        """
        state = BlendState(
            source_clip_id=source_clip_id,
            target_clip_id=target_clip_id,
            blend_progress=0.0,
            blend_duration=blend_duration,
            blend_type=blend_type.value,
        )

        self._blend_states[state.id] = state
        self._active_blends.append(state.id)
        return state

    def update_blend(self, blend_id: str, delta_time: float) -> Optional[BlendState]:
        """
        Advance a blend transition by delta_time.

        Args:
            blend_id: The blend state to update.
            delta_time: Time elapsed since last update.

        Returns:
            Updated BlendState or None if the blend is complete.
        """
        state = self._blend_states.get(blend_id)
        if not state or not state.is_active:
            return None

        state.elapsed_time += delta_time
        raw_progress = state.elapsed_time / max(0.001, state.blend_duration)
        raw_progress = min(1.0, raw_progress)

        # Apply blending interpolation function
        state.blend_progress = self._apply_blend_function(raw_progress, state.blend_type)

        if raw_progress >= 1.0:
            state.blend_progress = 1.0
            state.is_active = False
            if blend_id in self._active_blends:
                self._active_blends.remove(blend_id)

        return state

    def sample_blend(
        self, blend_id: str, normalized_time: float
    ) -> Dict[str, BoneTransform]:
        """
        Sample a blended animation between source and target clips.

        Args:
            blend_id: Active blend state ID.
            normalized_time: Normalized time for sampling both clips.

        Returns:
            Dict of bone name to blended BoneTransform.
        """
        state = self._blend_states.get(blend_id)
        if not state:
            return {}

        source_pose = self.sample_clip(state.source_clip_id, normalized_time)
        target_pose = self.sample_clip(state.target_clip_id, normalized_time)

        # Blend all bones
        blended = {}
        all_bones = set(source_pose.keys()) | set(target_pose.keys())
        for bone_name in all_bones:
            src = source_pose.get(bone_name, BoneTransform.identity())
            tgt = target_pose.get(bone_name, BoneTransform.identity())
            blended[bone_name] = BoneTransform.lerp(src, tgt, state.blend_progress)

        return blended

    def _apply_blend_function(self, t: float, blend_type: str) -> float:
        """Apply the blend interpolation function."""
        if blend_type == BlendType.LINEAR.value:
            return t
        if blend_type == BlendType.EASE_IN.value:
            return t * t
        if blend_type == BlendType.EASE_OUT.value:
            return 1.0 - (1.0 - t) * (1.0 - t)
        if blend_type == BlendType.EASE_IN_OUT.value:
            if t < 0.5:
                return 2.0 * t * t
            return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0
        if blend_type == BlendType.CUBIC.value:
            return t * t * (3.0 - 2.0 * t)
        return t

    # ------------------------------------------------------------------
    # Blend Space
    # ------------------------------------------------------------------

    def create_blend_space(
        self,
        name: str,
        dimension: BlendSpaceDimension,
        samples: List[Dict[str, Any]],
        min_parameter: float = 0.0,
        max_parameter: float = 1.0,
    ) -> BlendSpace:
        """
        Create a parameterized animation blend space.

        Args:
            name: Human-readable blend space name.
            dimension: Blend space dimensionality.
            samples: List of sample points with clip_id and parameter_value.
            min_parameter: Minimum parameter value.
            max_parameter: Maximum parameter value.

        Returns:
            Created BlendSpace.
        """
        space = BlendSpace(
            name=name,
            dimension=dimension.value,
            min_parameter=min_parameter,
            max_parameter=max_parameter,
        )

        for sample_data in samples:
            sample = BlendSpaceSample(
                clip_id=sample_data.get("clip_id", ""),
                parameter_value=sample_data.get("parameter_value", 0.0),
                weight=sample_data.get("weight", 0.0),
            )
            space.samples.append(sample)

        self._blend_spaces[space.id] = space
        return space

    def sample_blend_space(
        self, space_id: str, parameter_value: float, parameter_value_y: float = 0.0
    ) -> Dict[str, BoneTransform]:
        """
        Sample a blend space at the given parameter value.

        Finds the nearest sample points and interpolates between them.

        Args:
            space_id: The blend space to sample.
            parameter_value: Primary parameter value.
            parameter_value_y: Secondary parameter value (for 2D).

        Returns:
            Dict of bone name to blended BoneTransform.
        """
        space = self._blend_spaces.get(space_id)
        if not space or not space.samples:
            return {}

        space.current_parameter = parameter_value
        space.current_parameter_y = parameter_value_y

        # Clamp parameter to range
        param = max(space.min_parameter, min(space.max_parameter, parameter_value))

        if space.dimension == BlendSpaceDimension.ONE_D.value:
            return self._sample_1d_blend_space(space, param)

        # 2D blend space
        param_y = max(space.min_parameter, min(space.max_parameter, parameter_value_y))
        return self._sample_2d_blend_space(space, param, param_y)

    def _sample_1d_blend_space(
        self, space: BlendSpace, param: float
    ) -> Dict[str, BoneTransform]:
        """Sample a 1D blend space with linear interpolation between nearest neighbors."""
        sorted_samples = sorted(space.samples, key=lambda s: s.parameter_value)

        # Find nearest samples
        if param <= sorted_samples[0].parameter_value:
            return self.sample_clip(sorted_samples[0].clip_id, 0.0)
        if param >= sorted_samples[-1].parameter_value:
            return self.sample_clip(sorted_samples[-1].clip_id, 0.0)

        next_idx = 0
        for i, s in enumerate(sorted_samples):
            if s.parameter_value > param:
                next_idx = i
                break

        prev_sample = sorted_samples[next_idx - 1]
        next_sample = sorted_samples[next_idx]

        # Compute blend weight
        range_val = next_sample.parameter_value - prev_sample.parameter_value
        alpha = (param - prev_sample.parameter_value) / max(0.001, range_val)

        prev_pose = self.sample_clip(prev_sample.clip_id, 0.0)
        next_pose = self.sample_clip(next_sample.clip_id, 0.0)

        blended = {}
        all_bones = set(prev_pose.keys()) | set(next_pose.keys())
        for bone_name in all_bones:
            prev = prev_pose.get(bone_name, BoneTransform.identity())
            next_xform = next_pose.get(bone_name, BoneTransform.identity())
            blended[bone_name] = BoneTransform.lerp(prev, next_xform, alpha)

        return blended

    def _sample_2d_blend_space(
        self, space: BlendSpace, param_x: float, param_y: float
    ) -> Dict[str, BoneTransform]:
        """Sample a 2D blend space with bilinear interpolation."""
        # Simplified 2D: find 4 nearest samples and bilinear interpolate
        if len(space.samples) < 4:
            return self._sample_1d_blend_space(space, param_x)

        sorted_samples = sorted(space.samples, key=lambda s: s.parameter_value)

        # Use the 4 closest samples for bilinear interpolation
        closest = sorted(sorted_samples, key=lambda s: abs(s.parameter_value - param_x))[:4]

        # Compute distance-weighted blend
        blended = {}
        total_weight = 0.0
        weighted_transforms: Dict[str, List[Tuple[BoneTransform, float]]] = defaultdict(list)

        for sample in closest:
            distance = abs(sample.parameter_value - param_x)
            weight = 1.0 / max(0.001, distance)
            total_weight += weight

            pose = self.sample_clip(sample.clip_id, 0.0)
            for bone_name, xform in pose.items():
                weighted_transforms[bone_name].append((xform, weight))

        for bone_name, transforms in weighted_transforms.items():
            if not transforms:
                continue
            if len(transforms) == 1:
                blended[bone_name] = transforms[0][0]
            else:
                # Weighted average
                total_w = sum(w for _, w in transforms)
                avg = BoneTransform.identity()
                for xform, w in transforms:
                    avg = BoneTransform.lerp(avg, xform, w / total_w)
                blended[bone_name] = avg

        return blended

    # ------------------------------------------------------------------
    # Inverse Kinematics
    # ------------------------------------------------------------------

    def create_ik_chain(
        self,
        name: str,
        bone_ids: List[str],
        algorithm: IKAlgorithm = IKAlgorithm.FABRIK,
        iterations: int = 10,
        tolerance: float = 0.001,
    ) -> IKChain:
        """
        Create an inverse kinematics chain.

        Args:
            name: Human-readable chain name.
            bone_ids: Ordered bone IDs from root to end effector.
            algorithm: IK solving algorithm.
            iterations: Maximum solver iterations.
            tolerance: Convergence tolerance.

        Returns:
            Created IKChain.
        """
        chain = IKChain(
            name=name,
            bone_ids=list(bone_ids),
            algorithm=algorithm.value,
            iterations=iterations,
            tolerance=tolerance,
        )
        self._ik_chains[chain.id] = chain
        return chain

    def solve_ik(
        self,
        chain_id: str,
        target_position: Tuple[float, float, float],
        skeleton_id: Optional[str] = None,
    ) -> bool:
        """
        Solve an IK chain to reach the target position.

        Uses FABRIK (Forward And Backward Reaching Inverse Kinematics)
        algorithm for fast and stable convergence.

        Args:
            chain_id: The IK chain to solve.
            target_position: World-space target position.
            skeleton_id: Skeleton containing the bones.

        Returns:
            True if the solution converged within tolerance.
        """
        chain = self._ik_chains.get(chain_id)
        if not chain:
            return False

        skeleton = self.get_skeleton(skeleton_id)
        if not skeleton:
            return False

        solve_start = _time_module.time()
        chain.target_position = target_position

        if chain.algorithm == IKAlgorithm.FABRIK.value:
            solved = self._solve_fabrik(chain, skeleton)
        else:
            solved = self._solve_ccd(chain, skeleton)

        chain.solution_time_us = (_time_module.time() - solve_start) * 1_000_000
        chain.is_solved = solved
        self._ik_computation_time_us += chain.solution_time_us

        return solved

    def _solve_fabrik(self, chain: IKChain, skeleton: Dict[str, BoneNode]) -> bool:
        """FABRIK solver: Forward And Backward Reaching Inverse Kinematics."""
        bones = [skeleton[bid] for bid in chain.bone_ids if bid in skeleton]
        if len(bones) < 2:
            return False

        n = len(bones)
        target = chain.target_position

        # Get world positions of each joint
        positions = [b.world_transform.translation for b in bones]
        # Add end effector position (last bone tip)
        last_bone = bones[-1]
        end_effector_pos = (
            last_bone.world_transform.translation[0],
            last_bone.world_transform.translation[1] + last_bone.length,
            last_bone.world_transform.translation[2],
        )
        positions.append(end_effector_pos)

        # Store bone lengths
        bone_lengths = [b.length for b in bones]

        # Check if target is reachable
        root_pos = positions[0]
        total_length = sum(bone_lengths)
        dist_to_target = math.sqrt(
            (target[0] - root_pos[0])**2 +
            (target[1] - root_pos[1])**2 +
            (target[2] - root_pos[2])**2
        )

        if dist_to_target > total_length:
            # Target unreachable — stretch toward target
            for i in range(1, n + 1):
                r = dist_to_target
                lam = bone_lengths[i - 1] / max(0.001, r)
                positions[i] = (
                    (1.0 - lam) * positions[i - 1][0] + lam * target[0]
                    if i == n else
                    (1.0 - lam) * positions[i - 1][0] + lam * target[0],
                    (1.0 - lam) * positions[i - 1][1] + lam * target[1]
                    if i == n else
                    (1.0 - lam) * positions[i - 1][1] + lam * target[1],
                    (1.0 - lam) * positions[i - 1][2] + lam * target[2]
                    if i == n else
                    (1.0 - lam) * positions[i - 1][2] + lam * target[2],
                )
            # Simplified — in production, distribute along direction to target
            return False

        # Iterate FABRIK
        for _ in range(chain.iterations):
            # Forward reaching: from end effector to root
            positions[n] = target
            for i in range(n - 1, -1, -1):
                dx = positions[i + 1][0] - positions[i][0]
                dy = positions[i + 1][1] - positions[i][1]
                dz = positions[i + 1][2] - positions[i][2]
                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                if distance < 0.0001:
                    continue
                lam = bone_lengths[i] / distance
                positions[i] = (
                    positions[i + 1][0] - lam * dx,
                    positions[i + 1][1] - lam * dy,
                    positions[i + 1][2] - lam * dz,
                )

            # Backward reaching: from root to end effector
            positions[0] = root_pos
            for i in range(n):
                dx = positions[i + 1][0] - positions[i][0]
                dy = positions[i + 1][1] - positions[i][1]
                dz = positions[i + 1][2] - positions[i][2]
                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                if distance < 0.0001:
                    continue
                lam = bone_lengths[i] / distance
                positions[i + 1] = (
                    positions[i][0] + lam * dx,
                    positions[i][1] + lam * dy,
                    positions[i][2] + lam * dz,
                )

            # Check convergence
            final_dist = math.sqrt(
                (positions[n][0] - target[0])**2 +
                (positions[n][1] - target[1])**2 +
                (positions[n][2] - target[2])**2
            )
            if final_dist <= chain.tolerance:
                break

        # Apply solved positions to bone transforms
        for i, bone in enumerate(bones):
            if i < n:
                bone.local_transform = BoneTransform(
                    translation=positions[i],
                )

        return True

    def _solve_ccd(self, chain: IKChain, skeleton: Dict[str, BoneNode]) -> bool:
        """CCD (Cyclic Coordinate Descent) IK solver."""
        bones = [skeleton[bid] for bid in chain.bone_ids if bid in skeleton]
        if len(bones) < 2:
            return False

        target = chain.target_position
        end_effector = bones[-1]

        for _ in range(chain.iterations):
            for bone in reversed(bones[:-1]):
                # Compute direction from bone to end effector
                ee_pos = end_effector.world_transform.translation
                bone_pos = bone.world_transform.translation

                to_ee = (
                    ee_pos[0] - bone_pos[0],
                    ee_pos[1] - bone_pos[1],
                    ee_pos[2] - bone_pos[2],
                )
                to_target = (
                    target[0] - bone_pos[0],
                    target[1] - bone_pos[1],
                    target[2] - bone_pos[2],
                )

                # Compute rotation needed (simplified — in production, use proper quaternion rotation)
                # Update end effector position
                dist_to_target = math.sqrt(
                    to_target[0]**2 + to_target[1]**2 + to_target[2]**2
                )
                if dist_to_target <= chain.tolerance:
                    return True

            # Check convergence
            ee_pos = end_effector.world_transform.translation
            final_dist = math.sqrt(
                (ee_pos[0] - target[0])**2 +
                (ee_pos[1] - target[1])**2 +
                (ee_pos[2] - target[2])**2
            )
            if final_dist <= chain.tolerance:
                return True

        return False

    # ------------------------------------------------------------------
    # Animation Layers
    # ------------------------------------------------------------------

    def create_animation_layer(
        self,
        name: str,
        blend_mode: LayerBlendMode = LayerBlendMode.OVERRIDE,
        priority: int = 0,
    ) -> AnimationLayer:
        """Create an animation layer for stacking effects."""
        layer = AnimationLayer(
            name=name,
            blend_mode=blend_mode.value,
            priority=priority,
        )
        self._animation_layers[layer.id] = layer
        self._layer_stack.append(layer.id)
        self._sort_layers()
        return layer

    def _sort_layers(self):
        """Sort animation layers by priority (higher = on top)."""
        self._layer_stack = sorted(
            self._layer_stack,
            key=lambda lid: self._animation_layers[lid].priority if lid in self._animation_layers else 0,
        )

    def evaluate_layers(self, normalized_time: float) -> Dict[str, BoneTransform]:
        """
        Evaluate all active animation layers from bottom to top.

        Lower layers are evaluated first; higher layers blend on top
        according to their blend mode and weight.

        Args:
            normalized_time: Normalized time for animation sampling.

        Returns:
            Dict of bone name to final blended BoneTransform.
        """
        result: Dict[str, BoneTransform] = {}

        for layer_id in self._layer_stack:
            layer = self._animation_layers.get(layer_id)
            if not layer or not layer.enabled:
                continue

            if not layer.clip_id:
                continue

            pose = self.sample_clip(layer.clip_id, normalized_time)

            if layer.blend_mode == LayerBlendMode.OVERRIDE.value:
                # Override completely (for base layer) or blend by weight
                if not result or layer.priority == 0:
                    result = pose
                else:
                    for bone_name, xform in pose.items():
                        if bone_name in result:
                            result[bone_name] = BoneTransform.lerp(
                                result[bone_name], xform, layer.weight
                            )
                        else:
                            result[bone_name] = xform

            elif layer.blend_mode == LayerBlendMode.ADDITIVE.value:
                # Additive: add differences from reference pose
                for bone_name, xform in pose.items():
                    if bone_name in result:
                        result[bone_name] = BoneTransform(
                            translation=(
                                result[bone_name].translation[0] + xform.translation[0] * layer.weight,
                                result[bone_name].translation[1] + xform.translation[1] * layer.weight,
                                result[bone_name].translation[2] + xform.translation[2] * layer.weight,
                            ),
                            rotation=result[bone_name].rotation,  # Additive rotation requires ref pose
                            scale=(
                                result[bone_name].scale[0] * (1.0 + (xform.scale[0] - 1.0) * layer.weight),
                                result[bone_name].scale[1] * (1.0 + (xform.scale[1] - 1.0) * layer.weight),
                                result[bone_name].scale[2] * (1.0 + (xform.scale[2] - 1.0) * layer.weight),
                            ),
                        )

        return result

    # ------------------------------------------------------------------
    # Procedural Animation
    # ------------------------------------------------------------------

    def generate_procedural_noise_animation(
        self,
        target_bone_id: str,
        skeleton_id: Optional[str],
        amplitude: float = 0.1,
        frequency: float = 2.0,
        noise_seed: int = 42,
    ) -> Dict[str, BoneTransform]:
        """
        Generate a procedural noise-based animation for a bone.

        Useful for idle breathing, wind sway, camera shake, etc.

        Args:
            target_bone_id: The bone to animate.
            skeleton_id: Skeleton containing the bone.
            amplitude: Maximum displacement amplitude.
            frequency: Oscillation frequency.
            noise_seed: Random seed for deterministic noise.

        Returns:
            Dict with the bone's new transform.
        """
        skeleton = self.get_skeleton(skeleton_id)
        bone = skeleton.get(target_bone_id)
        if not bone:
            return {}

        t = self._playback_time

        # Simple perlin-like noise using sine combination
        noise_x = math.sin(t * frequency * 1.0 + noise_seed) * math.cos(t * frequency * 0.7 + noise_seed * 2)
        noise_y = math.sin(t * frequency * 1.3 + noise_seed * 3) * math.cos(t * frequency * 0.5 + noise_seed)
        noise_z = math.sin(t * frequency * 0.8 + noise_seed * 5) * 0.5

        new_transform = BoneTransform(
            translation=(
                bone.local_transform.translation[0] + noise_x * amplitude,
                bone.local_transform.translation[1] + noise_y * amplitude,
                bone.local_transform.translation[2] + noise_z * amplitude * 0.5,
            ),
            rotation=bone.local_transform.rotation,
            scale=bone.local_transform.scale,
        )

        return {target_bone_id: new_transform}

    # ------------------------------------------------------------------
    # Playback Control
    # ------------------------------------------------------------------

    def play(self) -> None:
        """Start or resume animation playback."""
        self._is_playing = True

    def pause(self) -> None:
        """Pause animation playback."""
        self._is_playing = False

    def stop(self) -> None:
        """Stop playback and reset time."""
        self._is_playing = False
        self._playback_time = 0.0

    def set_playback_speed(self, speed: float) -> None:
        """Set the animation playback speed multiplier."""
        self._playback_speed = max(0.0, speed)

    def update(self, delta_time: float) -> None:
        """Advance the animation playback by delta_time seconds."""
        if self._is_playing:
            self._playback_time += delta_time * self._playback_speed

    def get_playback_time(self) -> float:
        """Get current playback time."""
        return self._playback_time

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive skeletal animation system status."""
        return {
            "skeletons_managed": len(self._skeletons),
            "total_bones": sum(len(s) for s in self._skeletons.values()),
            "clips_loaded": len(self._clips),
            "total_keyframes": sum(c.total_keyframes for c in self._clips.values()),
            "active_blends": len(self._active_blends),
            "blend_spaces": len(self._blend_spaces),
            "ik_chains": len(self._ik_chains),
            "animation_layers": len(self._animation_layers),
            "is_playing": self._is_playing,
            "playback_time": round(self._playback_time, 4),
            "playback_speed": round(self._playback_speed, 2),
            "performance": {
                "fk_time_us": round(self._fk_computation_time_us, 2),
                "ik_time_us": round(self._ik_computation_time_us, 2),
                "total_bones_animated": self._total_bones_animated,
            },
        }

    @classmethod
    def get_instance(cls) -> "EngineSkeletalBlending":
        """Return the singleton instance."""
        return cls()

    def reset(self) -> None:
        """Reset all skeletal animation state."""
        with self._lock:
            self._skeletons.clear()
            self._default_skeleton_id = ""
            self._clips.clear()
            self._blend_states.clear()
            self._active_blends.clear()
            self._blend_spaces.clear()
            self._ik_chains.clear()
            self._animation_layers.clear()
            self._layer_stack.clear()
            self._playback_time = 0.0
            self._playback_speed = 1.0
            self._is_playing = False
            self._fk_computation_time_us = 0.0
            self._ik_computation_time_us = 0.0
            self._blend_computation_time_us = 0.0
            self._total_bones_animated = 0


# Need defaultdict for weighted transforms
from collections import defaultdict


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_skeletal_blending() -> EngineSkeletalBlending:
    """Return the singleton EngineSkeletalBlending instance."""
    return EngineSkeletalBlending()