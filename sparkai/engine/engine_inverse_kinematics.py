"""
SparkLabs Engine - Inverse Kinematics Engine

IK solver for character animation, supporting FABRIK and CCD algorithms.
Manages bone chains, end-effector positioning, and joint constraints for
procedural animation and ragdoll posing.

Architecture:
  InverseKinematicsEngine (Singleton)
    |-- IKBoneChain      — ordered chain of joints from root to end-effector
    |-- IKJoint          — single joint with position, rotation, and constraints
    |-- IKEffector       — target position/rotation for the end of a chain
    |-- IKSolution       — computed solution with joint positions and rotations

Solver Pipeline:
  1. FABRIK   — Forward And Backward Reaching Inverse Kinematics
  2. CCD      — Cyclic Coordinate Descent
  3. Jacobian — Jacobian transpose method (linear approximation)
  4. Constraints — angle, distance, and position limits
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Set


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class IKSolverType(Enum):
    """Type of inverse kinematics solver algorithm."""
    FABRIK = "fabrik"
    CCD = "ccd"
    JACOBIAN = "jacobian"
    ANALYTICAL = "analytical"


class JointType(Enum):
    """Type of joint determining degrees of freedom."""
    REVOLUTE = "revolute"
    PRISMATIC = "prismatic"
    BALL = "ball"
    FIXED = "fixed"


class ConstraintType(Enum):
    """Type of constraint applied to a joint."""
    ANGLE_LIMIT = "angle_limit"
    DISTANCE_LIMIT = "distance_limit"
    POSITION_LIMIT = "position_limit"
    NONE = "none"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class IKJoint:
    """A single joint in an inverse kinematics bone chain."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    joint_type: JointType = JointType.BALL
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    bone_length: float = 1.0
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "position": list(self.position),
            "rotation": list(self.rotation),
            "joint_type": self.joint_type.value,
            "parent_id": self.parent_id,
            "child_ids": list(self.child_ids),
            "bone_length": self.bone_length,
            "constraint_count": len(self.constraints),
            "metadata": dict(self.metadata),
        }


@dataclass
class IKBoneChain:
    """An ordered chain of joints from root to end-effector."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    joints: Dict[str, IKJoint] = field(default_factory=dict)
    root_joint_id: str = ""
    end_effector_id: str = ""
    chain_length: int = 0
    solver_type: IKSolverType = IKSolverType.FABRIK
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "joint_count": len(self.joints),
            "root_joint_id": self.root_joint_id,
            "end_effector_id": self.end_effector_id,
            "chain_length": self.chain_length,
            "solver_type": self.solver_type.value,
            "metadata": dict(self.metadata),
        }

    def get_ordered_joints(self) -> List[IKJoint]:
        """Return joints in order from root to end-effector."""
        ordered: List[IKJoint] = []
        current_id = self.root_joint_id
        visited: Set[str] = set()
        while current_id and current_id not in visited:
            joint = self.joints.get(current_id)
            if joint is None:
                break
            visited.add(current_id)
            ordered.append(joint)
            # Find next child along the main chain
            if joint.child_ids:
                current_id = joint.child_ids[0]
            else:
                break
        return ordered


@dataclass
class IKEffector:
    """Target specification for the end of a bone chain."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    chain_id: str = ""
    target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    target_rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    weight: float = 1.0
    reach_tolerance: float = 0.001
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "target_position": list(self.target_position),
            "target_rotation": list(self.target_rotation),
            "weight": self.weight,
            "reach_tolerance": self.reach_tolerance,
            "metadata": dict(self.metadata),
        }


@dataclass
class IKSolution:
    """Result of an inverse kinematics solve operation."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    chain_id: str = ""
    joint_positions: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    joint_rotations: Dict[str, Tuple[float, float, float, float]] = field(default_factory=dict)
    iterations: int = 0
    error: float = 0.0
    converged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "joint_count": len(self.joint_positions),
            "iterations": self.iterations,
            "error": round(self.error, 6),
            "converged": self.converged,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Vector Math Helpers
# ---------------------------------------------------------------------------

def _vec3_add(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec3_sub(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec3_scale(v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec3_length(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec3_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    length = _vec3_length(v)
    if length < 0.0000001:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _vec3_dot(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec3_cross(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec3_distance(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _vec3_lerp(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    t: float,
) -> Tuple[float, float, float]:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


# ---------------------------------------------------------------------------
# Inverse Kinematics Engine
# ---------------------------------------------------------------------------

class InverseKinematicsEngine:
    """
    Inverse kinematics solver for procedural character animation.

    Supports FABRIK and CCD algorithms with configurable bone chains,
    end-effector targets, and joint constraints. Provides iterative
    solving with convergence detection and error metrics.
    """

    _instance: Optional["InverseKinematicsEngine"] = None
    _lock = threading.RLock()

    _DEFAULT_MAX_ITERATIONS: int = 50
    _DEFAULT_TOLERANCE: float = 0.001
    _DEFAULT_DAMPING: float = 0.5

    def __new__(cls) -> "InverseKinematicsEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "InverseKinematicsEngine":
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

        self._chains: Dict[str, IKBoneChain] = {}
        self._effectors: Dict[str, IKEffector] = {}
        self._solutions: Dict[str, List[IKSolution]] = {}
        self._solve_count: int = 0
        self._total_iterations: int = 0
        self._creation_time: float = time.time()

    # ------------------------------------------------------------------
    # Chain Management
    # ------------------------------------------------------------------

    def create_chain(
        self,
        name: str,
        solver_type: IKSolverType = IKSolverType.FABRIK,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IKBoneChain:
        """Create a new bone chain for inverse kinematics solving.

        Args:
            name: Human-readable name for the chain.
            solver_type: The IK algorithm to use for this chain.
            metadata: Optional arbitrary metadata.

        Returns:
            The newly created IKBoneChain.
        """
        with self._lock:
            chain = IKBoneChain(
                name=name,
                solver_type=solver_type,
                metadata=metadata or {},
            )
            self._chains[chain.id] = chain
            return chain

    def add_joint(
        self,
        chain_id: str,
        name: str,
        position: Tuple[float, float, float],
        joint_type: JointType = JointType.BALL,
        bone_length: float = 1.0,
        parent_id: Optional[str] = None,
        constraints: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[IKJoint]:
        """Add a joint to a bone chain.

        If no parent_id is specified, the joint is appended to the end of
        the chain. If this is the first joint, it becomes the root.
        """
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None

            joint = IKJoint(
                name=name,
                position=position,
                joint_type=joint_type,
                parent_id=parent_id,
                bone_length=bone_length,
                constraints=constraints or [],
                metadata=metadata or {},
            )

            if joint.id in chain.joints:
                return None

            chain.joints[joint.id] = joint
            chain.chain_length = len(chain.joints)

            # Set as root if first joint
            if not chain.root_joint_id:
                chain.root_joint_id = joint.id

            # Link to parent
            if parent_id is not None and parent_id in chain.joints:
                parent = chain.joints[parent_id]
                if joint.id not in parent.child_ids:
                    parent.child_ids.append(joint.id)

            # Update end-effector: the last joint without children
            if not chain.end_effector_id or parent_id == chain.end_effector_id:
                chain.end_effector_id = joint.id

            return joint

    def set_effector(
        self,
        chain_id: str,
        target_position: Tuple[float, float, float],
        target_rotation: Optional[Tuple[float, float, float, float]] = None,
        weight: float = 1.0,
        reach_tolerance: float = _DEFAULT_TOLERANCE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[IKEffector]:
        """Set the target position and rotation for a chain's end-effector."""
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None

            effector = IKEffector(
                chain_id=chain_id,
                target_position=target_position,
                target_rotation=target_rotation or (0.0, 0.0, 0.0, 1.0),
                weight=max(0.0, min(1.0, weight)),
                reach_tolerance=reach_tolerance,
                metadata=metadata or {},
            )
            self._effectors[effector.id] = effector
            return effector

    def get_chain(self, chain_id: str) -> Optional[IKBoneChain]:
        """Get a bone chain by its ID."""
        return self._chains.get(chain_id)

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------

    def solve(
        self,
        chain_id: str,
        effector_id: str,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        tolerance: float = _DEFAULT_TOLERANCE,
        damping: float = _DEFAULT_DAMPING,
    ) -> Optional[IKSolution]:
        """Solve the inverse kinematics for a chain given an effector target.

        Dispatches to the appropriate solver based on the chain's solver_type.
        """
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None

            effector = self._effectors.get(effector_id)
            if effector is None:
                return None

            solver_type = chain.solver_type

            if solver_type == IKSolverType.FABRIK:
                solution = self.solve_fabrik(chain, effector, max_iterations, tolerance)
            elif solver_type == IKSolverType.CCD:
                solution = self.solve_ccd(chain, effector, max_iterations, tolerance)
            elif solver_type == IKSolverType.JACOBIAN:
                solution = self.solve_jacobian(chain, effector, max_iterations, tolerance, damping)
            elif solver_type == IKSolverType.ANALYTICAL:
                solution = self.solve_analytical(chain, effector)
            else:
                return None

            if solution is not None:
                self._solve_count += 1
                self._total_iterations += solution.iterations
                if chain_id not in self._solutions:
                    self._solutions[chain_id] = []
                self._solutions[chain_id].append(solution)

            return solution

    # ------------------------------------------------------------------
    # FABRIK Solver
    # ------------------------------------------------------------------

    def solve_fabrik(
        self,
        chain: IKBoneChain,
        effector: IKEffector,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        tolerance: float = _DEFAULT_TOLERANCE,
    ) -> IKSolution:
        """Solve using the Forward And Backward Reaching Inverse Kinematics algorithm.

        FABRIK iteratively adjusts joint positions by:
        1. Backward pass: move the end-effector to the target, then propagate
           adjustments back toward the root.
        2. Forward pass: move the root to its original position, then propagate
           adjustments forward toward the end-effector.
        3. Repeat until convergence or max iterations reached.
        """
        ordered = chain.get_ordered_joints()
        if len(ordered) < 2:
            return IKSolution(
                chain_id=chain.id,
                joint_positions={j.id: j.position for j in ordered},
                joint_rotations={j.id: j.rotation for j in ordered},
                iterations=0,
                error=_vec3_distance(ordered[-1].position, effector.target_position) if ordered else 0.0,
                converged=False,
            )

        # Store original root position
        root_pos = ordered[0].position

        # Work with current joint positions
        positions: List[Tuple[float, float, float]] = [j.position for j in ordered]
        bone_lengths: List[float] = [j.bone_length for j in ordered]
        target = effector.target_position

        # Total chain reach
        total_length = sum(bone_lengths)

        converged = False
        final_error = 0.0

        for iteration in range(max_iterations):
            # Backward pass
            positions[-1] = target
            for i in range(len(positions) - 2, -1, -1):
                direction = _vec3_normalize(_vec3_sub(positions[i], positions[i + 1]))
                positions[i] = _vec3_add(positions[i + 1], _vec3_scale(direction, bone_lengths[i]))

            # Forward pass
            positions[0] = root_pos
            for i in range(len(positions) - 1):
                direction = _vec3_normalize(_vec3_sub(positions[i + 1], positions[i]))
                positions[i + 1] = _vec3_add(positions[i], _vec3_scale(direction, bone_lengths[i]))

            # Check convergence
            error = _vec3_distance(positions[-1], target)
            final_error = error

            if error <= tolerance:
                converged = True
                break

        # Apply constraints
        positions = self.apply_constraints(chain, positions)

        # Build solution
        joint_positions: Dict[str, Tuple[float, float, float]] = {}
        joint_rotations: Dict[str, Tuple[float, float, float, float]] = {}

        for i, joint in enumerate(ordered):
            joint_positions[joint.id] = positions[i]
            # Compute rotation from direction vectors
            if i < len(ordered) - 1:
                direction = _vec3_normalize(_vec3_sub(positions[i + 1], positions[i]))
                joint_rotations[joint.id] = self._direction_to_quaternion(direction)
            else:
                joint_rotations[joint.id] = joint.rotation

        return IKSolution(
            chain_id=chain.id,
            joint_positions=joint_positions,
            joint_rotations=joint_rotations,
            iterations=iteration + 1,
            error=final_error,
            converged=converged,
        )

    # ------------------------------------------------------------------
    # CCD Solver
    # ------------------------------------------------------------------

    def solve_ccd(
        self,
        chain: IKBoneChain,
        effector: IKEffector,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        tolerance: float = _DEFAULT_TOLERANCE,
    ) -> IKSolution:
        """Solve using Cyclic Coordinate Descent.

        CCD iteratively rotates each joint (starting from the end-effector's
        parent back to the root) to minimize the distance between the
        end-effector and the target.
        """
        ordered = chain.get_ordered_joints()
        if len(ordered) < 2:
            return IKSolution(
                chain_id=chain.id,
                joint_positions={j.id: j.position for j in ordered},
                joint_rotations={j.id: j.rotation for j in ordered},
                iterations=0,
                error=_vec3_distance(ordered[-1].position, effector.target_position) if ordered else 0.0,
                converged=False,
            )

        positions: List[Tuple[float, float, float]] = [j.position for j in ordered]
        target = effector.target_position

        converged = False
        final_error = 0.0

        for iteration in range(max_iterations):
            # Iterate from end-effector's parent backward to root
            for i in range(len(ordered) - 2, -1, -1):
                joint_pos = positions[i]
                end_pos = positions[-1]

                # Vectors from joint to end-effector and from joint to target
                to_end = _vec3_normalize(_vec3_sub(end_pos, joint_pos))
                to_target = _vec3_normalize(_vec3_sub(target, joint_pos))

                # Compute rotation axis and angle
                cos_angle = _vec3_dot(to_end, to_target)
                cos_angle = max(-1.0, min(1.0, cos_angle))
                angle = math.acos(cos_angle)

                if angle < 0.000001:
                    continue

                # Clamp angle for stability
                angle = min(angle, math.radians(45.0))

                rotation_axis = _vec3_cross(to_end, to_target)
                axis_length = _vec3_length(rotation_axis)
                if axis_length < 0.0000001:
                    continue

                rotation_axis = _vec3_scale(rotation_axis, 1.0 / axis_length)

                # Rotate all downstream joints
                for j in range(i + 1, len(positions)):
                    relative = _vec3_sub(positions[j], joint_pos)
                    rotated = self._rotate_vector(relative, rotation_axis, angle)
                    positions[j] = _vec3_add(joint_pos, rotated)

            error = _vec3_distance(positions[-1], target)
            final_error = error

            if error <= tolerance:
                converged = True
                break

        # Apply constraints
        positions = self.apply_constraints(chain, positions)

        joint_positions: Dict[str, Tuple[float, float, float]] = {}
        joint_rotations: Dict[str, Tuple[float, float, float, float]] = {}

        for i, joint in enumerate(ordered):
            joint_positions[joint.id] = positions[i]
            if i < len(ordered) - 1:
                direction = _vec3_normalize(_vec3_sub(positions[i + 1], positions[i]))
                joint_rotations[joint.id] = self._direction_to_quaternion(direction)
            else:
                joint_rotations[joint.id] = joint.rotation

        return IKSolution(
            chain_id=chain.id,
            joint_positions=joint_positions,
            joint_rotations=joint_rotations,
            iterations=iteration + 1,
            error=final_error,
            converged=converged,
        )

    # ------------------------------------------------------------------
    # Jacobian Solver
    # ------------------------------------------------------------------

    def solve_jacobian(
        self,
        chain: IKBoneChain,
        effector: IKEffector,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        tolerance: float = _DEFAULT_TOLERANCE,
        damping: float = _DEFAULT_DAMPING,
    ) -> IKSolution:
        """Solve using the Jacobian transpose method.

        This is a gradient-based approach that uses the Jacobian matrix to
        map joint angle changes to end-effector position changes. The
        transpose of the Jacobian provides a direction to reduce error.
        """
        ordered = chain.get_ordered_joints()
        if len(ordered) < 2:
            return IKSolution(
                chain_id=chain.id,
                joint_positions={j.id: j.position for j in ordered},
                joint_rotations={j.id: j.rotation for j in ordered},
                iterations=0,
                error=_vec3_distance(ordered[-1].position, effector.target_position) if ordered else 0.0,
                converged=False,
            )

        positions: List[Tuple[float, float, float]] = [j.position for j in ordered]
        target = effector.target_position

        converged = False
        final_error = 0.0

        for iteration in range(max_iterations):
            end_pos = positions[-1]
            error_vec = _vec3_sub(target, end_pos)
            error = _vec3_length(error_vec)
            final_error = error

            if error <= tolerance:
                converged = True
                break

            # For each joint (except end-effector), compute the Jacobian column
            for i in range(len(ordered) - 1):
                joint_pos = positions[i]

                # The axis of rotation is perpendicular to the bone direction
                # and the error direction
                bone_dir = _vec3_normalize(_vec3_sub(positions[i + 1], joint_pos))

                # Cross product gives the instantaneous velocity direction
                axis = _vec3_cross(bone_dir, error_vec)
                axis_length = _vec3_length(axis)
                if axis_length < 0.0000001:
                    continue

                axis = _vec3_scale(axis, 1.0 / axis_length)

                # Scale the rotation by the error and damping
                angle = error * damping * 0.5
                angle = min(angle, math.radians(30.0))

                # Rotate downstream joints
                for j in range(i + 1, len(positions)):
                    relative = _vec3_sub(positions[j], joint_pos)
                    rotated = self._rotate_vector(relative, axis, angle)
                    positions[j] = _vec3_add(joint_pos, rotated)

        positions = self.apply_constraints(chain, positions)

        joint_positions: Dict[str, Tuple[float, float, float]] = {}
        joint_rotations: Dict[str, Tuple[float, float, float, float]] = {}

        for i, joint in enumerate(ordered):
            joint_positions[joint.id] = positions[i]
            if i < len(ordered) - 1:
                direction = _vec3_normalize(_vec3_sub(positions[i + 1], positions[i]))
                joint_rotations[joint.id] = self._direction_to_quaternion(direction)
            else:
                joint_rotations[joint.id] = joint.rotation

        return IKSolution(
            chain_id=chain.id,
            joint_positions=joint_positions,
            joint_rotations=joint_rotations,
            iterations=iteration + 1,
            error=final_error,
            converged=converged,
        )

    # ------------------------------------------------------------------
    # Analytical Solver
    # ------------------------------------------------------------------

    def solve_analytical(
        self,
        chain: IKBoneChain,
        effector: IKEffector,
    ) -> IKSolution:
        """Solve analytically for a 2-joint chain (e.g., upper arm + forearm).

        This uses the law of cosines to directly compute the elbow angle.
        For chains longer than 2 joints, falls back to FABRIK.
        """
        ordered = chain.get_ordered_joints()
        if len(ordered) < 2:
            return IKSolution(
                chain_id=chain.id,
                joint_positions={j.id: j.position for j in ordered},
                joint_rotations={j.id: j.rotation for j in ordered},
                iterations=0,
                error=_vec3_distance(ordered[-1].position, effector.target_position) if ordered else 0.0,
                converged=False,
            )

        if len(ordered) != 3:
            # Fall back to FABRIK for chains other than 2-bone
            return self.solve_fabrik(chain, effector)

        # 2-bone chain: root, mid, end
        root_pos = ordered[0].position
        l1 = ordered[1].bone_length  # Upper bone length
        l2 = ordered[2].bone_length  # Lower bone length
        target = effector.target_position

        # Distance from root to target
        root_to_target = _vec3_sub(target, root_pos)
        dist = _vec3_length(root_to_target)

        # Clamp distance to reachable range
        max_reach = l1 + l2
        min_reach = abs(l1 - l2)

        if dist > max_reach:
            root_to_target = _vec3_scale(root_to_target, max_reach / dist)
            dist = max_reach
        elif dist < min_reach and dist > 0.0001:
            root_to_target = _vec3_scale(root_to_target, min_reach / dist)
            dist = min_reach

        # Law of cosines for the elbow angle
        cos_angle = (l1 * l1 + dist * dist - l2 * l2) / (2.0 * l1 * dist)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        mid_angle = math.acos(cos_angle)

        # Direction from root to target
        if dist > 0.0001:
            root_dir = _vec3_normalize(root_to_target)
        else:
            root_dir = (0.0, 0.0, 1.0)

        # Compute a perpendicular axis for the elbow bend
        ref_axis = (0.0, 1.0, 0.0)
        if abs(_vec3_dot(root_dir, ref_axis)) > 0.99:
            ref_axis = (1.0, 0.0, 0.0)

        bend_axis = _vec3_normalize(_vec3_cross(root_dir, ref_axis))

        mid_pos = _vec3_add(
            root_pos,
            _vec3_scale(
                self._rotate_vector(root_dir, bend_axis, mid_angle),
                l1,
            ),
        )

        positions = [root_pos, mid_pos, target]
        positions = self.apply_constraints(chain, positions)

        joint_positions: Dict[str, Tuple[float, float, float]] = {}
        joint_rotations: Dict[str, Tuple[float, float, float, float]] = {}

        for i, joint in enumerate(ordered):
            joint_positions[joint.id] = positions[i]
            if i < len(ordered) - 1:
                direction = _vec3_normalize(_vec3_sub(positions[i + 1], positions[i]))
                joint_rotations[joint.id] = self._direction_to_quaternion(direction)
            else:
                joint_rotations[joint.id] = joint.rotation

        error = _vec3_distance(positions[-1], target)

        return IKSolution(
            chain_id=chain.id,
            joint_positions=joint_positions,
            joint_rotations=joint_rotations,
            iterations=1,
            error=error,
            converged=error <= effector.reach_tolerance,
        )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    def apply_constraints(
        self,
        chain: IKBoneChain,
        positions: List[Tuple[float, float, float]],
    ) -> List[Tuple[float, float, float]]:
        """Apply joint constraints to a list of positions.

        Supports angle limits, distance limits, and position limits.
        """
        ordered = chain.get_ordered_joints()
        constrained = list(positions)

        for i, joint in enumerate(ordered):
            if not joint.constraints:
                continue

            for constraint in joint.constraints:
                ctype = constraint.get("type", "")

                if ctype == ConstraintType.ANGLE_LIMIT.value:
                    constrained = self._apply_angle_limit(
                        constrained, ordered, i, constraint
                    )
                elif ctype == ConstraintType.DISTANCE_LIMIT.value:
                    constrained = self._apply_distance_limit(
                        constrained, i, constraint
                    )
                elif ctype == ConstraintType.POSITION_LIMIT.value:
                    constrained = self._apply_position_limit(
                        constrained, i, constraint
                    )

        return constrained

    def _apply_angle_limit(
        self,
        positions: List[Tuple[float, float, float]],
        ordered: List[IKJoint],
        joint_index: int,
        constraint: Dict[str, Any],
    ) -> List[Tuple[float, float, float]]:
        """Clamp the angle at a joint to within [min_angle, max_angle] degrees."""
        if joint_index == 0 or joint_index >= len(positions) - 1:
            return positions

        min_angle = math.radians(constraint.get("min_angle", 0.0))
        max_angle = math.radians(constraint.get("max_angle", 180.0))

        prev_pos = positions[joint_index - 1]
        current_pos = positions[joint_index]
        next_pos = positions[joint_index + 1]

        bone_in = _vec3_normalize(_vec3_sub(prev_pos, current_pos))
        bone_out = _vec3_normalize(_vec3_sub(next_pos, current_pos))

        cos_angle = _vec3_dot(bone_in, bone_out)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        angle = math.acos(cos_angle)

        if angle < min_angle:
            # Need to rotate bone_out to increase the angle
            axis = _vec3_normalize(_vec3_cross(bone_in, bone_out))
            axis_length = _vec3_length(_vec3_cross(bone_in, bone_out))
            if axis_length < 0.0000001:
                return positions
            axis = _vec3_scale(axis, 1.0 / axis_length)

            bone_length = _vec3_distance(current_pos, next_pos)
            new_dir = self._rotate_vector(bone_in, axis, min_angle)
            positions[joint_index + 1] = _vec3_add(current_pos, _vec3_scale(new_dir, bone_length))

        elif angle > max_angle:
            axis = _vec3_normalize(_vec3_cross(bone_in, bone_out))
            axis_length = _vec3_length(_vec3_cross(bone_in, bone_out))
            if axis_length < 0.0000001:
                return positions
            axis = _vec3_scale(axis, 1.0 / axis_length)

            bone_length = _vec3_distance(current_pos, next_pos)
            new_dir = self._rotate_vector(bone_in, axis, max_angle)
            positions[joint_index + 1] = _vec3_add(current_pos, _vec3_scale(new_dir, bone_length))

        return positions

    def _apply_distance_limit(
        self,
        positions: List[Tuple[float, float, float]],
        joint_index: int,
        constraint: Dict[str, Any],
    ) -> List[Tuple[float, float, float]]:
        """Clamp the distance between two joints."""
        min_dist = constraint.get("min_distance", 0.0)
        max_dist = constraint.get("max_distance", float("inf"))

        if joint_index >= len(positions) - 1:
            return positions

        current = positions[joint_index]
        next_pos = positions[joint_index + 1]
        dist = _vec3_distance(current, next_pos)

        if dist < min_dist and dist > 0.0001:
            direction = _vec3_normalize(_vec3_sub(next_pos, current))
            positions[joint_index + 1] = _vec3_add(current, _vec3_scale(direction, min_dist))
        elif dist > max_dist:
            direction = _vec3_normalize(_vec3_sub(next_pos, current))
            positions[joint_index + 1] = _vec3_add(current, _vec3_scale(direction, max_dist))

        return positions

    def _apply_position_limit(
        self,
        positions: List[Tuple[float, float, float]],
        joint_index: int,
        constraint: Dict[str, Any],
    ) -> List[Tuple[float, float, float]]:
        """Clamp a joint's position within a bounding box."""
        min_x = constraint.get("min_x", float("-inf"))
        min_y = constraint.get("min_y", float("-inf"))
        min_z = constraint.get("min_z", float("-inf"))
        max_x = constraint.get("max_x", float("inf"))
        max_y = constraint.get("max_y", float("inf"))
        max_z = constraint.get("max_z", float("inf"))

        x, y, z = positions[joint_index]
        positions[joint_index] = (
            max(min_x, min(max_x, x)),
            max(min_y, min(max_y, y)),
            max(min_z, min(max_z, z)),
        )
        return positions

    # ------------------------------------------------------------------
    # Rotation Helpers
    # ------------------------------------------------------------------

    def _rotate_vector(
        self,
        v: Tuple[float, float, float],
        axis: Tuple[float, float, float],
        angle: float,
    ) -> Tuple[float, float, float]:
        """Rotate a vector around an axis by a given angle using Rodrigues' formula."""
        axis = _vec3_normalize(axis)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        dot_va = _vec3_dot(v, axis)
        cross_va = _vec3_cross(axis, v)

        return (
            v[0] * cos_a + cross_va[0] * sin_a + axis[0] * dot_va * (1.0 - cos_a),
            v[1] * cos_a + cross_va[1] * sin_a + axis[1] * dot_va * (1.0 - cos_a),
            v[2] * cos_a + cross_va[2] * sin_a + axis[2] * dot_va * (1.0 - cos_a),
        )

    def _direction_to_quaternion(
        self, direction: Tuple[float, float, float]
    ) -> Tuple[float, float, float, float]:
        """Convert a direction vector to a quaternion (identity rotation from Z-up)."""
        ref_dir = (0.0, 0.0, 1.0)
        d = _vec3_dot(ref_dir, direction)
        if d > 0.999999:
            return (0.0, 0.0, 0.0, 1.0)
        if d < -0.999999:
            return (0.0, 1.0, 0.0, 0.0)

        axis = _vec3_cross(ref_dir, direction)
        axis = _vec3_normalize(axis)
        angle = math.acos(d)

        half_angle = angle * 0.5
        s = math.sin(half_angle)
        return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(half_angle))

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics including chain counts and solve metrics."""
        with self._lock:
            chain_details: List[Dict[str, Any]] = []
            for chain in self._chains.values():
                solutions = self._solutions.get(chain.id, [])
                chain_details.append({
                    "chain_id": chain.id,
                    "name": chain.name,
                    "joint_count": len(chain.joints),
                    "solver_type": chain.solver_type.value,
                    "solution_count": len(solutions),
                })

            return {
                "chain_count": len(self._chains),
                "effector_count": len(self._effectors),
                "total_solutions": self._solve_count,
                "total_iterations": self._total_iterations,
                "avg_iterations": round(
                    self._total_iterations / max(1, self._solve_count), 1
                ),
                "uptime_seconds": round(time.time() - self._creation_time, 1),
                "chains": chain_details,
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire inverse kinematics engine state."""
        with self._lock:
            self._chains.clear()
            self._effectors.clear()
            self._solutions.clear()
            self._solve_count = 0
            self._total_iterations = 0
            self._creation_time = time.time()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_inverse_kinematics() -> InverseKinematicsEngine:
    """Get or create the singleton InverseKinematicsEngine instance."""
    return InverseKinematicsEngine.get_instance()