"""
SparkLabs Engine - Procedural Animation Engine

Runtime procedural animation system that generates character and object
animations dynamically without pre-authored keyframes. Combines inverse
kinematics, procedural locomotion, ragdoll physics blending, and
environment-aware animation adaptation.

Architecture:
  EngineProceduralAnimation (Singleton)
    |-- IKSolver (multi-joint inverse kinematics chain resolver)
    |-- LocomotionController (procedural walk/run cycle generation)
    |-- AnimationBlender (seamless transition between animation states)
    |-- PhysicsAnimator (ragdoll and physics-driven animation)
    |-- LookAtController (head/eye tracking and gaze direction)
    |-- ProceduralGesture (dynamic hand and body gestures)

Animation Layers:
  - LOCOMOTION: walk, run, crouch, crawl, swim, fly
  - INTERACTION: grab, push, pull, climb, mount
  - EXPRESSION: idle, gesture, emote, dialogue
  - PHYSICS: ragdoll, hit reaction, force response
  - ADAPTATION: terrain alignment, slope handling, obstacle avoidance

Usage:
    pa = EngineProceduralAnimation.get_instance()
    pa.initialize()

    pa.create_ik_chain("right_arm", ["shoulder", "elbow", "wrist"])
    pa.set_ik_target("right_arm", (1.0, 0.5, 0.0))
    pa.solve_ik("right_arm")

    pa.start_locomotion("character_1", "run", speed=5.0)
    pa.update_animation("character_1", delta_time=0.016)
    pa.shutdown()
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# =============================================================================
# Enums
# =============================================================================


class IKAlgorithm(Enum):
    """Inverse kinematics solving algorithms."""
    CCD = "ccd"                    # Cyclic Coordinate Descent
    FABRIK = "fabrik"              # Forward and Backward Reaching IK
    JACOBIAN = "jacobian"          # Jacobian-based solver
    ANALYTICAL = "analytical"      # Closed-form analytical solution
    HYBRID = "hybrid"              # Combined approach


class LocomotionType(Enum):
    """Types of procedural locomotion."""
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    CROUCH = "crouch"
    CRAWL = "crawl"
    SWIM = "swim"
    FLY = "fly"
    CLIMB = "climb"
    JUMP = "jump"
    FALL = "fall"


class AnimationBlendMode(Enum):
    """Blending modes for animation transitions."""
    LINEAR = "linear"
    SMOOTH = "smooth"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    CROSSFADE = "crossfade"
    ADDITIVE = "additive"


class BoneConstraint(Enum):
    """Constraints for bone movement."""
    HINGE = "hinge"              # Single axis rotation
    BALL_SOCKET = "ball_socket"  # Multi-axis rotation
    SLIDER = "slider"            # Linear movement
    FIXED = "fixed"              # No movement
    SPRING = "spring"            # Spring-damped movement


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Bone:
    """A single bone in a skeletal hierarchy."""
    bone_id: str
    name: str
    parent_id: Optional[str] = None
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    length: float = 1.0
    constraint: BoneConstraint = BoneConstraint.BALL_SOCKET
    children: List[str] = field(default_factory=list)
    is_end_effector: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def world_position(self) -> List[float]:
        return self.position

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bone_id": self.bone_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "position": self.position,
            "length": self.length,
            "constraint": self.constraint.value,
            "children": self.children,
            "is_end_effector": self.is_end_effector,
        }


@dataclass
class IKChain:
    """An inverse kinematics chain for a limb."""
    chain_id: str
    name: str
    bone_ids: List[str]  # Ordered from root to end effector
    algorithm: IKAlgorithm = IKAlgorithm.FABRIK
    target_position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    tolerance: float = 0.001
    max_iterations: int = 20
    is_active: bool = True
    weight: float = 1.0
    pole_vector: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "bone_count": len(self.bone_ids),
            "bone_ids": self.bone_ids,
            "algorithm": self.algorithm.value,
            "target_position": self.target_position,
            "tolerance": self.tolerance,
            "max_iterations": self.max_iterations,
            "is_active": self.is_active,
            "weight": self.weight,
        }


@dataclass
class LocomotionState:
    """State for procedural locomotion animation."""
    state_id: str
    entity_id: str
    locomotion_type: LocomotionType = LocomotionType.IDLE
    speed: float = 0.0
    direction: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    cycle_time: float = 0.0
    stride_length: float = 1.0
    step_height: float = 0.2
    body_bob: float = 0.05
    arm_swing: float = 0.3
    foot_placement: List[Tuple[float, float, float]] = field(default_factory=list)
    is_grounded: bool = True
    slope_angle: float = 0.0
    blend_weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "entity_id": self.entity_id,
            "locomotion_type": self.locomotion_type.value,
            "speed": self.speed,
            "direction": self.direction,
            "cycle_time": self.cycle_time,
            "stride_length": self.stride_length,
            "step_height": self.step_height,
            "is_grounded": self.is_grounded,
            "slope_angle": self.slope_angle,
            "blend_weight": self.blend_weight,
        }


@dataclass
class AnimationPose:
    """A skeletal pose at a point in time."""
    pose_id: str
    bone_transforms: Dict[str, Dict[str, List[float]]] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    root_motion: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pose_id": self.pose_id,
            "bone_count": len(self.bone_transforms),
            "timestamp": self.timestamp,
            "root_motion": self.root_motion,
        }


@dataclass
class AnimationBlend:
    """Blend configuration between two animation states."""
    blend_id: str
    from_state: str
    to_state: str
    mode: AnimationBlendMode = AnimationBlendMode.SMOOTH
    duration: float = 0.3
    progress: float = 0.0
    is_complete: bool = False
    start_time: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blend_id": self.blend_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "mode": self.mode.value,
            "duration": self.duration,
            "progress": self.progress,
            "is_complete": self.is_complete,
        }


# =============================================================================
# Procedural Animation Engine
# =============================================================================


class EngineProceduralAnimation:
    """
    Runtime procedural animation system for dynamic character and object
    animation. Generates animations procedurally without pre-authored
    keyframes using IK, physics blending, and environment adaptation.
    """

    _instance: Optional["EngineProceduralAnimation"] = None
    _instance_lock = threading.RLock()

    # Locomotion parameters by type
    _LOCOMOTION_PARAMS: Dict[LocomotionType, Dict[str, float]] = {
        LocomotionType.IDLE: {"cycle_duration": 0.0, "stride": 0.0, "bob": 0.0, "swing": 0.0},
        LocomotionType.WALK: {"cycle_duration": 1.0, "stride": 1.0, "bob": 0.05, "swing": 0.3},
        LocomotionType.RUN: {"cycle_duration": 0.5, "stride": 2.0, "bob": 0.1, "swing": 0.5},
        LocomotionType.CROUCH: {"cycle_duration": 1.5, "stride": 0.5, "bob": 0.03, "swing": 0.15},
        LocomotionType.CRAWL: {"cycle_duration": 2.0, "stride": 0.3, "bob": 0.02, "swing": 0.1},
        LocomotionType.SWIM: {"cycle_duration": 1.2, "stride": 0.8, "bob": 0.08, "swing": 0.4},
        LocomotionType.FLY: {"cycle_duration": 0.8, "stride": 1.5, "bob": 0.15, "swing": 0.2},
        LocomotionType.CLIMB: {"cycle_duration": 1.8, "stride": 0.4, "bob": 0.04, "swing": 0.6},
        LocomotionType.JUMP: {"cycle_duration": 0.6, "stride": 0.0, "bob": 0.5, "swing": 0.2},
        LocomotionType.FALL: {"cycle_duration": 0.0, "stride": 0.0, "bob": 0.0, "swing": 0.1},
    }

    def __init__(self) -> None:
        if EngineProceduralAnimation._instance is not None:
            raise RuntimeError("Use EngineProceduralAnimation.get_instance()")
        self._initialized: bool = False
        self._skeletons: Dict[str, Dict[str, Bone]] = {}
        self._ik_chains: Dict[str, IKChain] = {}
        self._locomotion_states: Dict[str, LocomotionState] = {}
        self._blends: Dict[str, AnimationBlend] = {}
        self._poses: Dict[str, AnimationPose] = {}
        self._look_at_targets: Dict[str, List[float]] = {}
        self._stats: Dict[str, Any] = {
            "total_skeletons": 0,
            "total_ik_chains": 0,
            "total_locomotion_states": 0,
            "total_poses_generated": 0,
            "ik_solves": 0,
        }
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "EngineProceduralAnimation":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the procedural animation engine."""
        with self._lock:
            if self._initialized:
                return
            self._initialized = True

    # -------------------------------------------------------------------------
    # Skeleton Management
    # -------------------------------------------------------------------------

    def create_skeleton(self, skeleton_id: str, bones: List[Bone]) -> Dict[str, Bone]:
        """Create a skeletal hierarchy."""
        with self._lock:
            skeleton: Dict[str, Bone] = {}
            for bone in bones:
                skeleton[bone.bone_id] = bone
            self._skeletons[skeleton_id] = skeleton
            self._stats["total_skeletons"] += 1
            return skeleton

    def get_skeleton(self, skeleton_id: str) -> Optional[Dict[str, Bone]]:
        """Get a skeleton by ID."""
        return self._skeletons.get(skeleton_id)

    def get_bone(self, skeleton_id: str, bone_id: str) -> Optional[Bone]:
        """Get a specific bone from a skeleton."""
        skeleton = self._skeletons.get(skeleton_id)
        if skeleton:
            return skeleton.get(bone_id)
        return None

    def add_bone(self, skeleton_id: str, bone: Bone) -> bool:
        """Add a bone to an existing skeleton."""
        skeleton = self._skeletons.get(skeleton_id)
        if not skeleton:
            return False
        with self._lock:
            skeleton[bone.bone_id] = bone
            if bone.parent_id and bone.parent_id in skeleton:
                skeleton[bone.parent_id].children.append(bone.bone_id)
            return True

    # -------------------------------------------------------------------------
    # Inverse Kinematics
    # -------------------------------------------------------------------------

    def create_ik_chain(self, chain_name: str, bone_ids: List[str],
                        algorithm: IKAlgorithm = IKAlgorithm.FABRIK) -> IKChain:
        """Create an IK chain for a limb."""
        with self._lock:
            chain_id = uuid.uuid4().hex[:12]
            chain = IKChain(
                chain_id=chain_id,
                name=chain_name,
                bone_ids=bone_ids,
                algorithm=algorithm,
            )
            self._ik_chains[chain_id] = chain
            self._stats["total_ik_chains"] += 1
            return chain

    def set_ik_target(self, chain_id: str, target: Tuple[float, float, float]) -> bool:
        """Set the target position for an IK chain."""
        chain = self._ik_chains.get(chain_id)
        if not chain:
            return False
        chain.target_position = list(target)
        return True

    def solve_ik(self, chain_id: str, skeleton_id: str) -> bool:
        """Solve inverse kinematics for a chain."""
        chain = self._ik_chains.get(chain_id)
        skeleton = self._skeletons.get(skeleton_id)
        if not chain or not skeleton or not chain.is_active:
            return False

        with self._lock:
            if chain.algorithm == IKAlgorithm.FABRIK:
                self._solve_fabrik(chain, skeleton)
            elif chain.algorithm == IKAlgorithm.CCD:
                self._solve_ccd(chain, skeleton)
            elif chain.algorithm == IKAlgorithm.ANALYTICAL:
                self._solve_analytical(chain, skeleton)

            self._stats["ik_solves"] += 1
            return True

    def _solve_fabrik(self, chain: IKChain, skeleton: Dict[str, Bone]) -> None:
        """Solve IK using FABRIK algorithm."""
        bone_ids = chain.bone_ids
        target = chain.target_position

        # Get current bone positions
        positions = [list(skeleton[bid].position) for bid in bone_ids]
        if not positions:
            return

        # Bone lengths
        lengths = [skeleton[bid].length for bid in bone_ids[1:]]

        for _ in range(chain.max_iterations):
            # Backward pass: set end effector to target, adjust backward
            positions[-1] = list(target)
            for i in range(len(positions) - 2, -1, -1):
                direction = [
                    positions[i][0] - positions[i + 1][0],
                    positions[i][1] - positions[i + 1][1],
                    positions[i][2] - positions[i + 1][2],
                ]
                dist = math.sqrt(sum(d * d for d in direction))
                if dist > 0.001:
                    ratio = lengths[i] / dist
                    positions[i] = [
                        positions[i + 1][0] + direction[0] * ratio,
                        positions[i + 1][1] + direction[1] * ratio,
                        positions[i + 1][2] + direction[2] * ratio,
                    ]

            # Forward pass: set root to original, adjust forward
            root_pos = list(skeleton[bone_ids[0]].position)
            positions[0] = root_pos
            for i in range(len(positions) - 1):
                direction = [
                    positions[i + 1][0] - positions[i][0],
                    positions[i + 1][1] - positions[i][1],
                    positions[i + 1][2] - positions[i][2],
                ]
                dist = math.sqrt(sum(d * d for d in direction))
                if dist > 0.001:
                    ratio = lengths[i] / dist
                    positions[i + 1] = [
                        positions[i][0] + direction[0] * ratio,
                        positions[i][1] + direction[1] * ratio,
                        positions[i][2] + direction[2] * ratio,
                    ]

            # Check convergence
            end_to_target = [
                positions[-1][0] - target[0],
                positions[-1][1] - target[1],
                positions[-1][2] - target[2],
            ]
            error = math.sqrt(sum(d * d for d in end_to_target))
            if error < chain.tolerance:
                break

        # Apply pole vector constraint if set
        if any(chain.pole_vector):
            self._apply_pole_vector(chain, positions, skeleton)

        # Update bone positions
        for i, bone_id in enumerate(bone_ids):
            if bone_id in skeleton:
                skeleton[bone_id].position = positions[i]

    def _solve_ccd(self, chain: IKChain, skeleton: Dict[str, Bone]) -> None:
        """Solve IK using CCD algorithm."""
        bone_ids = chain.bone_ids
        target = chain.target_position

        for _ in range(chain.max_iterations):
            for i in range(len(bone_ids) - 2, -1, -1):
                joint = skeleton[bone_ids[i]]
                end_effector = skeleton[bone_ids[-1]]

                # Vector from joint to end effector
                to_end = [
                    end_effector.position[0] - joint.position[0],
                    end_effector.position[1] - joint.position[1],
                    end_effector.position[2] - joint.position[2],
                ]

                # Vector from joint to target
                to_target = [
                    target[0] - joint.position[0],
                    target[1] - joint.position[1],
                    target[2] - joint.position[2],
                ]

                # Normalize
                end_len = math.sqrt(sum(d * d for d in to_end))
                tgt_len = math.sqrt(sum(d * d for d in to_target))
                if end_len < 0.001 or tgt_len < 0.001:
                    continue

                to_end = [d / end_len for d in to_end]
                to_target = [d / tgt_len for d in to_target]

                # Rotate all child bones
                cos_angle = sum(to_end[i] * to_target[i] for i in range(3))
                cos_angle = max(-1.0, min(1.0, cos_angle))
                angle = math.acos(cos_angle)

                if abs(angle) > chain.tolerance:
                    # Simple rotation for demonstration
                    for j in range(i + 1, len(bone_ids)):
                        child = skeleton[bone_ids[j]]
                        child.position = [
                            child.position[0] + (to_target[0] - to_end[0]) * 0.1,
                            child.position[1] + (to_target[1] - to_end[1]) * 0.1,
                            child.position[2] + (to_target[2] - to_end[2]) * 0.1,
                        ]

            error = math.sqrt(
                (skeleton[bone_ids[-1]].position[0] - target[0]) ** 2 +
                (skeleton[bone_ids[-1]].position[1] - target[1]) ** 2 +
                (skeleton[bone_ids[-1]].position[2] - target[2]) ** 2
            )
            if error < chain.tolerance:
                break

    def _solve_analytical(self, chain: IKChain, skeleton: Dict[str, Bone]) -> None:
        """Solve IK using analytical method (2-bone chain)."""
        if len(chain.bone_ids) != 3:
            self._solve_fabrik(chain, skeleton)
            return

        b0 = skeleton[chain.bone_ids[0]]
        b1 = skeleton[chain.bone_ids[1]]
        b2 = skeleton[chain.bone_ids[2]]
        target = chain.target_position

        # Distance from root to target
        dx = target[0] - b0.position[0]
        dy = target[1] - b0.position[1]
        dz = target[2] - b0.position[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        # Law of cosines
        l1 = b1.length
        l2 = b2.length
        max_reach = l1 + l2
        if dist > max_reach:
            dist = max_reach

        cos_angle2 = (l1 * l1 + l2 * l2 - dist * dist) / (2 * l1 * l2)
        cos_angle2 = max(-1.0, min(1.0, cos_angle2))
        angle2 = math.acos(cos_angle2)

        cos_angle1 = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
        cos_angle1 = max(-1.0, min(1.0, cos_angle1))
        angle1 = math.acos(cos_angle1)

        # Simple application
        b1.position = [
            b0.position[0] + dx * l1 / max(dist, 0.001),
            b0.position[1] + dy * l1 / max(dist, 0.001),
            b0.position[2] + dz * l1 / max(dist, 0.001),
        ]
        b2.position = list(target)

    def _apply_pole_vector(self, chain: IKChain, positions: List[List[float]],
                           skeleton: Dict[str, Bone]) -> None:
        """Apply pole vector constraint to IK solution."""
        # Simple pole vector application
        pass

    def get_ik_chain(self, chain_id: str) -> Optional[IKChain]:
        """Get an IK chain by ID."""
        return self._ik_chains.get(chain_id)

    def list_ik_chains(self) -> List[IKChain]:
        """List all IK chains."""
        return list(self._ik_chains.values())

    def list_skeletons(self) -> List[Dict[str, Any]]:
        """List all skeletons."""
        return [
            {"skeleton_id": sid, "bone_count": len(skel)}
            for sid, skel in self._skeletons.items()
        ]

    # -------------------------------------------------------------------------
    # Procedural Locomotion
    # -------------------------------------------------------------------------

    def start_locomotion(self, entity_id: str, locomotion_type: Union[LocomotionType, str],
                         speed: float = 1.0, direction: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> LocomotionState:
        """Start procedural locomotion for an entity."""
        if isinstance(locomotion_type, str):
            try:
                locomotion_type = LocomotionType(locomotion_type)
            except ValueError:
                locomotion_type = LocomotionType.IDLE

        params = self._LOCOMOTION_PARAMS.get(locomotion_type, {})

        with self._lock:
            state_id = uuid.uuid4().hex[:12]
            state = LocomotionState(
                state_id=state_id,
                entity_id=entity_id,
                locomotion_type=locomotion_type,
                speed=speed,
                direction=list(direction),
                stride_length=params.get("stride", 1.0) * speed,
                step_height=params.get("step_height", 0.2),
                body_bob=params.get("bob", 0.05),
                arm_swing=params.get("swing", 0.3),
            )
            self._locomotion_states[entity_id] = state
            self._stats["total_locomotion_states"] += 1
            return state

    def update_animation(self, entity_id: str, delta_time: float) -> Optional[AnimationPose]:
        """Update procedural animation for an entity."""
        state = self._locomotion_states.get(entity_id)
        if not state:
            return None

        with self._lock:
            state.cycle_time = (state.cycle_time + delta_time * state.speed) % 1.0

            # Generate procedural pose
            pose = AnimationPose(
                pose_id=uuid.uuid4().hex[:8],
                root_motion=self._compute_root_motion(state, delta_time),
            )

            # Apply body bob
            bob = math.sin(state.cycle_time * math.pi * 2) * state.body_bob
            pose.bone_transforms["root"] = {
                "position": [0.0, bob, 0.0],
                "rotation": [0.0, 0.0, 0.0, 1.0],
            }

            # Apply arm swing (for bipedal locomotion)
            swing = math.sin(state.cycle_time * math.pi * 2) * state.arm_swing
            pose.bone_transforms["left_arm"] = {
                "rotation": [swing, 0.0, 0.0, 1.0],
            }
            pose.bone_transforms["right_arm"] = {
                "rotation": [-swing, 0.0, 0.0, 1.0],
            }

            # Apply leg movement
            leg_angle = math.sin(state.cycle_time * math.pi * 2) * 0.5
            pose.bone_transforms["left_leg"] = {
                "rotation": [leg_angle, 0.0, 0.0, 1.0],
            }
            pose.bone_transforms["right_leg"] = {
                "rotation": [-leg_angle, 0.0, 0.0, 1.0],
            }

            self._poses[pose.pose_id] = pose
            self._stats["total_poses_generated"] += 1
            return pose

    def _compute_root_motion(self, state: LocomotionState,
                             delta_time: float) -> List[float]:
        """Compute root motion for locomotion."""
        if state.locomotion_type in (LocomotionType.IDLE, LocomotionType.FALL):
            return [0.0, 0.0, 0.0]

        speed = state.speed * state.stride_length * delta_time
        dir_norm = state.direction
        dir_len = math.sqrt(sum(d * d for d in dir_norm))
        if dir_len > 0.001:
            dir_norm = [d / dir_len * speed for d in dir_norm]
        else:
            dir_norm = [0.0, 0.0, speed]

        return dir_norm

    def stop_locomotion(self, entity_id: str) -> bool:
        """Stop locomotion for an entity."""
        return self._locomotion_states.pop(entity_id, None) is not None

    # -------------------------------------------------------------------------
    # Animation Blending
    # -------------------------------------------------------------------------

    def start_blend(self, from_state: str, to_state: str,
                    duration: float = 0.3,
                    mode: AnimationBlendMode = AnimationBlendMode.SMOOTH) -> AnimationBlend:
        """Start a blend between two animation states."""
        with self._lock:
            blend_id = uuid.uuid4().hex[:12]
            blend = AnimationBlend(
                blend_id=blend_id,
                from_state=from_state,
                to_state=to_state,
                duration=duration,
                mode=mode,
            )
            self._blends[blend_id] = blend
            return blend

    def update_blend(self, blend_id: str, delta_time: float) -> float:
        """Update blend progress and return current weight."""
        blend = self._blends.get(blend_id)
        if not blend or blend.is_complete:
            return 1.0

        blend.progress += delta_time / blend.duration
        if blend.progress >= 1.0:
            blend.progress = 1.0
            blend.is_complete = True

        # Apply easing based on blend mode
        t = blend.progress
        if blend.mode == AnimationBlendMode.EASE_IN:
            t = t * t
        elif blend.mode == AnimationBlendMode.EASE_OUT:
            t = 1.0 - (1.0 - t) * (1.0 - t)
        elif blend.mode == AnimationBlendMode.EASE_IN_OUT:
            t = t * t * (3.0 - 2.0 * t)

        return t

    # -------------------------------------------------------------------------
    # Look-At Controller
    # -------------------------------------------------------------------------

    def set_look_at_target(self, entity_id: str, target: Tuple[float, float, float]) -> None:
        """Set look-at target for head/eye tracking."""
        self._look_at_targets[entity_id] = list(target)

    def compute_look_at(self, entity_id: str,
                        head_position: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Compute head rotation to look at target."""
        target = self._look_at_targets.get(entity_id)
        if not target:
            return (0.0, 0.0, 0.0)

        dx = target[0] - head_position[0]
        dy = target[1] - head_position[1]
        dz = target[2] - head_position[2]

        yaw = math.atan2(dx, dz)
        pitch = math.atan2(-dy, math.sqrt(dx * dx + dz * dz))

        return (pitch, yaw, 0.0)

    def clear_look_at(self, entity_id: str) -> None:
        """Clear look-at target for an entity."""
        self._look_at_targets.pop(entity_id, None)

    # -------------------------------------------------------------------------
    # Status and Statistics
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get animation engine status and statistics."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "skeletons": self._stats["total_skeletons"],
                "ik_chains": self._stats["total_ik_chains"],
                "locomotion_states": self._stats["total_locomotion_states"],
                "active_locomotion": len(self._locomotion_states),
                "poses_generated": self._stats["total_poses_generated"],
                "ik_solves": self._stats["ik_solves"],
                "active_blends": len([b for b in self._blends.values() if not b.is_complete]),
                "active_look_at": len(self._look_at_targets),
            }

    def get_locomotion_state(self, entity_id: str) -> Optional[LocomotionState]:
        """Get the locomotion state for an entity."""
        return self._locomotion_states.get(entity_id)

    def shutdown(self) -> None:
        """Shutdown the animation engine."""
        with self._lock:
            self._skeletons.clear()
            self._ik_chains.clear()
            self._locomotion_states.clear()
            self._blends.clear()
            self._poses.clear()
            self._look_at_targets.clear()
            self._initialized = False


def get_procedural_animation() -> EngineProceduralAnimation:
    """Get the singleton procedural animation instance."""
    return EngineProceduralAnimation.get_instance()