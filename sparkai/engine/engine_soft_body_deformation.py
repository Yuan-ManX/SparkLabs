"""
SparkLabs Engine - Soft Body Deformation Physics System

A volumetric soft body deformation runtime for the SparkLabs AI-native game
engine. Bodies are represented as tetrahedral meshes with spring constraints
connecting vertices. The system handles elastic and plastic deformation,
tearing, fracture mechanics, and volume preservation. An AI assessment layer
analyzes stress distribution and tunes material parameters at runtime.

Architecture:
  SoftBodyDeformationSystem (singleton)
    |-- Tetrahedron, SoftBodyVertex, SpringConstraint, MaterialProperties
    |-- SoftBody, DeformationResult, TearRecord, FractureRecord
    |-- AIAssessment, SoftBodyStats, SoftBodyConfig, SoftBodySnapshot, SoftBodyEvent
    |-- DeformationType, MaterialBehavior, BodyStatus, TearMode
    |-- FracturePattern, SoftBodyEventKind, SolverMethod, VolumePreservation

Core Capabilities:
  - register_material / remove_material / get_material / list_materials:
    material lifecycle with Young's modulus, Poisson ratio, yield strength,
    ultimate strength, tear threshold, and fracture toughness.
  - register_body / remove_body / get_body / list_bodies: soft body lifecycle
    with vertices, tetrahedra, and spring constraints.
  - apply_force / apply_pressure / apply_impact / apply_twist / apply_bend:
    deformation drivers producing DeformationResult records.
  - compute_stress / compute_strain / check_yield: per-vertex stress and
    per-spring strain with yield-point detection.
  - apply_plastic_flow: convert elastic deformation into permanent set by
    updating spring rest lengths beyond the plastic threshold.
  - check_tear / propagate_tear: detect and extend tears when strain exceeds
    the material tear threshold.
  - check_fracture / fracture_body: detect and create fractures when
    accumulated damage exceeds fracture toughness.
  - pin_vertex / unpin_vertex / set_vertex_position / get_vertex /
    list_vertices: vertex-level manipulation.
  - ai_assess_body / ai_tune_material / ai_tune_global: AI-driven stress
    analysis, stability scoring, and material parameter tuning.
  - compute_volume / preserve_volume: tetrahedral volume computation and
    correction toward the rest volume.
  - reset_deformation / get_deformation_summary / get_stress_report /
    get_visualization_data: inspection and reset utilities.
  - get_stats / get_snapshot / get_status / get_config / set_config:
    observability and configuration management.
  - list_events / tick: event log and per-frame simulation step.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`SoftBodyDeformationSystem.get_instance` or the module-level
:func:`get_soft_body_deformation_system` factory.
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
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_BODIES: int = 500
_MAX_VERTICES_PER_BODY: int = 2000
_MAX_EVENTS: int = 5000
_EPSILON: float = 1e-9
_GRAVITY_DEFAULT: Tuple[float, float, float] = (0.0, -9.81, 0.0)


# ---------------------------------------------------------------------------
# Vector Helper Functions (3D)
# ---------------------------------------------------------------------------


def _vec_add(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_sub(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_scale(a: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (a[0] * s, a[1] * s, a[2] * s)


def _vec_dot(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_cross(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec_length(a: Tuple[float, float, float]) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _vec_normalize(a: Tuple[float, float, float]) -> Tuple[float, float, float]:
    length = _vec_length(a)
    if length < _EPSILON:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / length
    return (a[0] * inv, a[1] * inv, a[2] * inv)


def _vec_distance(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    return _vec_length(_vec_sub(a, b))


# ---------------------------------------------------------------------------
# General Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:10]
    return f"{prefix}_{base}" if prefix else base


def _clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


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
        return value.to_dict()
    return value


# ---------------------------------------------------------------------------
# Tetrahedron Volume Computation
# ---------------------------------------------------------------------------


def _tet_volume(
    p0: Tuple[float, float, float],
    p1: Tuple[float, float, float],
    p2: Tuple[float, float, float],
    p3: Tuple[float, float, float],
) -> float:
    """Compute the signed volume of a tetrahedron from four vertex positions.

    V = |det([p1-p0, p2-p0, p3-p0])| / 6
    """
    e1 = _vec_sub(p1, p0)
    e2 = _vec_sub(p2, p0)
    e3 = _vec_sub(p3, p0)
    cross = _vec_cross(e1, e2)
    det = _vec_dot(cross, e3)
    return abs(det) / 6.0


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class DeformationType(str, Enum):
    """Categorization of deformation applied to a soft body."""

    ELASTIC = "elastic"
    PLASTIC = "plastic"
    VISCOELASTIC = "viscoelastic"
    FRACTURE = "fracture"
    TEAR = "tear"
    COMPRESS = "compress"
    STRETCH = "stretch"
    BEND = "bend"
    TWIST = "twist"


class MaterialBehavior(str, Enum):
    """Constitutive model governing how a material responds to stress."""

    LINEAR_ELASTIC = "linear_elastic"
    NONLINEAR_ELASTIC = "nonlinear_elastic"
    HYPERELASTIC = "hyperelastic"
    ELASTOPLASTIC = "elastoplastic"
    VISCOELASTIC = "viscoelastic"
    RIGID = "rigid"
    FLUID = "fluid"


class BodyStatus(str, Enum):
    """Lifecycle state of a soft body within the simulation."""

    INTACT = "intact"
    DEFORMED = "deformed"
    YIELDING = "yielding"
    TEARING = "tearing"
    FRACTURED = "fractured"
    DESTROYED = "destroyed"


class TearMode(str, Enum):
    """Progression stage of a tear within a soft body."""

    NONE = "none"
    INITIATED = "initiated"
    PROPAGATING = "propagating"
    COMPLETE = "complete"


class FracturePattern(str, Enum):
    """Visual and structural pattern of a fracture event."""

    CLEAN = "clean"
    BRITTLE = "brittle"
    DUCTILE = "ductile"
    SPLINTER = "splinter"
    SHATTER = "shatter"
    PEEL = "peel"


class SoftBodyEventKind(str, Enum):
    """Event types emitted by the soft body deformation system."""

    BODY_REGISTERED = "body_registered"
    BODY_REMOVED = "body_removed"
    DEFORMATION_APPLIED = "deformation_applied"
    PLASTIC_FLOW = "plastic_flow"
    TEAR_INITIATED = "tear_initiated"
    TEAR_PROPAGATED = "tear_propagated"
    FRACTURE_DETECTED = "fracture_detected"
    BODY_DESTROYED = "body_destroyed"
    MATERIAL_TUNED = "material_tuned"
    STRESS_EXCEEDED = "stress_exceeded"


class SolverMethod(str, Enum):
    """Numerical solver used for integrating soft body dynamics."""

    MASS_SPRING = "mass_spring"
    FINITE_ELEMENT = "finite_element"
    POSITION_BASEED = "position_based"
    SHAPE_MATCHING = "shape_matching"
    LATTICE = "lattice"


class VolumePreservation(str, Enum):
    """Volume conservation strategy for a material or body."""

    NONE = "none"
    INCOMPRESSIBLE = "incompressible"
    NEAR_INCOMPRESSIBLE = "near_incompressible"
    COMPRESSIBLE = "compressible"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Tetrahedron:
    """A tetrahedral element defined by four vertex IDs.

    Tetrahedra are the volumetric building blocks of a soft body. Each tracks
    its rest volume and current volume for volume-preservation corrections.
    """

    id: str = field(default_factory=lambda: _new_id("tet"))
    vertex_ids: Tuple[str, str, str, str] = ("", "", "", "")
    rest_volume: float = 0.0
    current_volume: float = 0.0
    material_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "vertex_ids": list(self.vertex_ids),
            "rest_volume": self.rest_volume,
            "current_volume": self.current_volume,
            "material_id": self.material_id,
        }


@dataclass
class SoftBodyVertex:
    """A single vertex in a soft body mesh.

    Vertices carry position, velocity, mass, and a force accumulator used
    during integration. Pinned vertices are fixed in space and excluded
    from force integration.
    """

    id: str = field(default_factory=lambda: _new_id("vtx"))
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mass: float = 1.0
    pinned: bool = False
    force_accumulator: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "mass": self.mass,
            "pinned": self.pinned,
            "force_accumulator": list(self.force_accumulator),
        }


@dataclass
class SpringConstraint:
    """A spring connecting two vertices with elastic and plastic behavior.

    Springs store rest length, stiffness, damping, a yield point beyond which
    plastic deformation begins, and a plastic threshold controlling how much
    elastic deformation converts to permanent set.
    """

    id: str = field(default_factory=lambda: _new_id("spr"))
    vertex_a_id: str = ""
    vertex_b_id: str = ""
    rest_length: float = 1.0
    stiffness: float = 100.0
    damping: float = 0.1
    yield_point: float = 0.1
    plastic_threshold: float = 0.05
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "vertex_a_id": self.vertex_a_id,
            "vertex_b_id": self.vertex_b_id,
            "rest_length": self.rest_length,
            "stiffness": self.stiffness,
            "damping": self.damping,
            "yield_point": self.yield_point,
            "plastic_threshold": self.plastic_threshold,
            "active": self.active,
        }


@dataclass
class MaterialProperties:
    """Physical properties of a deformable material.

    Captures the constitutive parameters needed for stress-strain computation,
    yield detection, tearing, and fracture mechanics.
    """

    material_id: str = field(default_factory=lambda: _new_id("mat"))
    name: str = ""
    behavior: MaterialBehavior = MaterialBehavior.LINEAR_ELASTIC
    youngs_modulus: float = 1.0e6
    poissons_ratio: float = 0.3
    yield_strength: float = 1.0e5
    ultimate_strength: float = 2.0e5
    density: float = 1000.0
    damping_coefficient: float = 0.1
    tear_threshold: float = 0.5
    fracture_toughness: float = 1.0e3
    volume_preservation: VolumePreservation = VolumePreservation.COMPRESSIBLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_id": self.material_id,
            "name": self.name,
            "behavior": self.behavior.value,
            "youngs_modulus": self.youngs_modulus,
            "poissons_ratio": self.poissons_ratio,
            "yield_strength": self.yield_strength,
            "ultimate_strength": self.ultimate_strength,
            "density": self.density,
            "damping_coefficient": self.damping_coefficient,
            "tear_threshold": self.tear_threshold,
            "fracture_toughness": self.fracture_toughness,
            "volume_preservation": self.volume_preservation.value,
        }


@dataclass
class SoftBody:
    """A complete soft body composed of vertices, tetrahedra, and springs.

    The body tracks cumulative deformation, plastic deformation, elastic
    energy, center of mass, and bounding radius for broad-phase collision.
    """

    body_id: str = field(default_factory=lambda: _new_id("body"))
    name: str = ""
    vertices: Dict[str, SoftBodyVertex] = field(default_factory=dict)
    tetrahedra: List[Tetrahedron] = field(default_factory=list)
    springs: List[SpringConstraint] = field(default_factory=list)
    material_id: str = ""
    status: BodyStatus = BodyStatus.INTACT
    total_deformation: float = 0.0
    plastic_deformation: float = 0.0
    elastic_energy: float = 0.0
    center_of_mass: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounding_radius: float = 0.0
    damage_accumulated: float = 0.0
    rest_volume: float = 0.0
    current_volume: float = 0.0
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "name": self.name,
            "vertices": {k: v.to_dict() for k, v in self.vertices.items()},
            "tetrahedra": [t.to_dict() for t in self.tetrahedra],
            "springs": [s.to_dict() for s in self.springs],
            "material_id": self.material_id,
            "status": self.status.value,
            "total_deformation": self.total_deformation,
            "plastic_deformation": self.plastic_deformation,
            "elastic_energy": self.elastic_energy,
            "center_of_mass": list(self.center_of_mass),
            "bounding_radius": self.bounding_radius,
            "damage_accumulated": self.damage_accumulated,
            "rest_volume": self.rest_volume,
            "current_volume": self.current_volume,
            "created_at": self.created_at,
        }


@dataclass
class DeformationResult:
    """Outcome record produced by a deformation operation.

    Captures the deformation type, magnitude, direction, affected vertex IDs,
    dissipated energy, and whether the deformation is permanent.
    """

    body_id: str = ""
    deformation_type: DeformationType = DeformationType.ELASTIC
    magnitude: float = 0.0
    direction: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    affected_vertices: List[str] = field(default_factory=list)
    energy_dissipated: float = 0.0
    is_permanent: bool = False
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "deformation_type": self.deformation_type.value,
            "magnitude": self.magnitude,
            "direction": list(self.direction),
            "affected_vertices": list(self.affected_vertices),
            "energy_dissipated": self.energy_dissipated,
            "is_permanent": self.is_permanent,
            "timestamp": self.timestamp,
        }


@dataclass
class TearRecord:
    """Record of a tear event within a soft body.

    Tracks the tear ID, associated body, start and end vertex IDs, mode,
    length, and the list of spring IDs that were severed during propagation.
    """

    tear_id: str = field(default_factory=lambda: _new_id("tear"))
    body_id: str = ""
    start_vertex_id: str = ""
    end_vertex_id: str = ""
    mode: TearMode = TearMode.NONE
    length: float = 0.0
    propagated_springs: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tear_id": self.tear_id,
            "body_id": self.body_id,
            "start_vertex_id": self.start_vertex_id,
            "end_vertex_id": self.end_vertex_id,
            "mode": self.mode.value,
            "length": self.length,
            "propagated_springs": list(self.propagated_springs),
            "created_at": self.created_at,
        }


@dataclass
class FractureRecord:
    """Record of a fracture event that splits a body into fragments.

    Captures the fracture ID, associated body, pattern, fragment IDs,
    origin vertex, and energy released during the fracture.
    """

    fracture_id: str = field(default_factory=lambda: _new_id("frac"))
    body_id: str = ""
    pattern: FracturePattern = FracturePattern.CLEAN
    fragments: List[str] = field(default_factory=list)
    origin_vertex_id: str = ""
    energy_released: float = 0.0
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fracture_id": self.fracture_id,
            "body_id": self.body_id,
            "pattern": self.pattern.value,
            "fragments": list(self.fragments),
            "origin_vertex_id": self.origin_vertex_id,
            "energy_released": self.energy_released,
            "created_at": self.created_at,
        }


@dataclass
class AIAssessment:
    """AI-generated assessment of a soft body's stress and stability.

    Includes per-vertex stress distribution, recommended stiffness and damping
    values, identified risk areas, and an overall stability score.
    """

    body_id: str = ""
    stress_distribution: Dict[str, float] = field(default_factory=dict)
    recommended_stiffness: float = 100.0
    recommended_damping: float = 0.1
    risk_areas: List[str] = field(default_factory=list)
    stability_score: float = 1.0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "stress_distribution": dict(self.stress_distribution),
            "recommended_stiffness": self.recommended_stiffness,
            "recommended_damping": self.recommended_damping,
            "risk_areas": list(self.risk_areas),
            "stability_score": self.stability_score,
            "timestamp": self.timestamp,
        }


@dataclass
class SoftBodyStats:
    """Aggregate statistics across all soft bodies in the system."""

    total_bodies: int = 0
    active_bodies: int = 0
    destroyed_bodies: int = 0
    total_deformations: int = 0
    total_tears: int = 0
    total_fractures: int = 0
    total_plastic_flows: int = 0
    average_stress: float = 0.0
    peak_stress: float = 0.0
    total_energy_dissipated: float = 0.0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_bodies": self.total_bodies,
            "active_bodies": self.active_bodies,
            "destroyed_bodies": self.destroyed_bodies,
            "total_deformations": self.total_deformations,
            "total_tears": self.total_tears,
            "total_fractures": self.total_fractures,
            "total_plastic_flows": self.total_plastic_flows,
            "average_stress": self.average_stress,
            "peak_stress": self.peak_stress,
            "total_energy_dissipated": self.total_energy_dissipated,
            "timestamp": self.timestamp,
        }


@dataclass
class SoftBodyConfig:
    """Global configuration for the soft body deformation system."""

    max_bodies: int = _MAX_BODIES
    max_vertices_per_body: int = _MAX_VERTICES_PER_BODY
    solver_method: SolverMethod = SolverMethod.MASS_SPRING
    solver_iterations: int = 8
    global_gravity: Tuple[float, float, float] = _GRAVITY_DEFAULT
    global_damping: float = 0.02
    enable_tearing: bool = True
    enable_fracture: bool = True
    enable_plastic_flow: bool = True
    enable_volume_preservation: bool = True
    ai_tuning_frequency: int = 60
    stress_threshold_warning: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_bodies": self.max_bodies,
            "max_vertices_per_body": self.max_vertices_per_body,
            "solver_method": self.solver_method.value,
            "solver_iterations": self.solver_iterations,
            "global_gravity": list(self.global_gravity),
            "global_damping": self.global_damping,
            "enable_tearing": self.enable_tearing,
            "enable_fracture": self.enable_fracture,
            "enable_plastic_flow": self.enable_plastic_flow,
            "enable_volume_preservation": self.enable_volume_preservation,
            "ai_tuning_frequency": self.ai_tuning_frequency,
            "stress_threshold_warning": self.stress_threshold_warning,
        }


@dataclass
class SoftBodySnapshot:
    """Point-in-time snapshot of system-wide counts."""

    tick_count: int = 0
    active_bodies: int = 0
    total_vertices: int = 0
    total_tetrahedra: int = 0
    total_springs: int = 0
    total_deformations: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick_count": self.tick_count,
            "active_bodies": self.active_bodies,
            "total_vertices": self.total_vertices,
            "total_tetrahedra": self.total_tetrahedra,
            "total_springs": self.total_springs,
            "total_deformations": self.total_deformations,
            "timestamp": self.timestamp,
        }


@dataclass
class SoftBodyEvent:
    """An event emitted by the soft body deformation system."""

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: str = ""
    tick: int = 0
    body_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "tick": self.tick,
            "body_id": self.body_id,
            "payload": _to_jsonable(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Material Presets
# ---------------------------------------------------------------------------

_MATERIAL_PRESETS: Dict[str, Dict[str, Any]] = {
    "rubber": {
        "name": "Rubber",
        "behavior": MaterialBehavior.HYPERELASTIC,
        "youngs_modulus": 5.0e6,
        "poissons_ratio": 0.48,
        "yield_strength": 2.0e6,
        "ultimate_strength": 3.0e6,
        "density": 1100.0,
        "damping_coefficient": 0.05,
        "tear_threshold": 1.5,
        "fracture_toughness": 5.0e3,
        "volume_preservation": VolumePreservation.NEAR_INCOMPRESSIBLE,
    },
    "jelly": {
        "name": "Jelly",
        "behavior": MaterialBehavior.VISCOELASTIC,
        "youngs_modulus": 5.0e4,
        "poissons_ratio": 0.49,
        "yield_strength": 1.0e3,
        "ultimate_strength": 5.0e3,
        "density": 1050.0,
        "damping_coefficient": 0.3,
        "tear_threshold": 2.0,
        "fracture_toughness": 5.0e2,
        "volume_preservation": VolumePreservation.INCOMPRESSIBLE,
    },
    "metal": {
        "name": "Metal",
        "behavior": MaterialBehavior.ELASTOPLASTIC,
        "youngs_modulus": 2.0e11,
        "poissons_ratio": 0.3,
        "yield_strength": 2.5e8,
        "ultimate_strength": 4.0e8,
        "density": 7850.0,
        "damping_coefficient": 0.01,
        "tear_threshold": 0.05,
        "fracture_toughness": 5.0e7,
        "volume_preservation": VolumePreservation.COMPRESSIBLE,
    },
    "cloth": {
        "name": "Cloth",
        "behavior": MaterialBehavior.NONLINEAR_ELASTIC,
        "youngs_modulus": 1.0e5,
        "poissons_ratio": 0.1,
        "yield_strength": 5.0e4,
        "ultimate_strength": 1.0e5,
        "density": 300.0,
        "damping_coefficient": 0.08,
        "tear_threshold": 0.3,
        "fracture_toughness": 2.0e3,
        "volume_preservation": VolumePreservation.NONE,
    },
    "flesh": {
        "name": "Flesh",
        "behavior": MaterialBehavior.VISCOELASTIC,
        "youngs_modulus": 2.0e5,
        "poissons_ratio": 0.45,
        "yield_strength": 5.0e4,
        "ultimate_strength": 1.0e5,
        "density": 1060.0,
        "damping_coefficient": 0.15,
        "tear_threshold": 0.8,
        "fracture_toughness": 3.0e3,
        "volume_preservation": VolumePreservation.NEAR_INCOMPRESSIBLE,
    },
}


# ---------------------------------------------------------------------------
# Soft Body Deformation System Singleton
# ---------------------------------------------------------------------------


class SoftBodyDeformationSystem:
    """Volumetric soft body deformation with elastic, plastic, tear, and
    fracture mechanics.

    Implements the singleton pattern with double-checked locking. Consumers
    should obtain the instance via :meth:`get_instance` or the module-level
    :func:`get_soft_body_deformation_system` factory.

    Usage:
        system = get_soft_body_deformation_system()
        ok, msg, body = system.register_body("ball_01", "Ball", "rubber", ...)
        ok, msg, result = system.apply_force("ball_01", "vtx_0", (0, -10, 0))
        summary = system.tick(0.016)
    """

    _instance: Optional["SoftBodyDeformationSystem"] = None
    _init_lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        # Double-checked initialization guard so repeated construction is safe.
        if getattr(self, "_initialized", False):
            return
        with self._init_lock:
            if getattr(self, "_initialized", False):
                return

            self._materials: Dict[str, MaterialProperties] = {}
            self._bodies: Dict[str, SoftBody] = {}
            self._tears: Dict[str, TearRecord] = {}
            self._fractures: Dict[str, FractureRecord] = {}
            self._deformation_results: List[DeformationResult] = []
            self._events: List[SoftBodyEvent] = []

            self._config: SoftBodyConfig = SoftBodyConfig()
            self._tick_count: int = 0
            self._global_time: float = 0.0

            self._total_deformations: int = 0
            self._total_tears: int = 0
            self._total_fractures: int = 0
            self._total_plastic_flows: int = 0
            self._total_energy_dissipated: float = 0.0

            self._seeded: bool = False
            self._initialized: bool = True

    # ------------------------------------------------------------------
    # Singleton lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "SoftBodyDeformationSystem":
        """Return the singleton SoftBodyDeformationSystem, creating it if needed."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Tear down the singleton so a fresh instance can be built."""
        with cls._init_lock:
            cls._instance = None

    def initialize(self) -> Tuple[bool, str]:
        """Load seed data including materials, bodies, tears, and fractures.

        Idempotent: calling initialize() multiple times is safe and will not
        duplicate seed entries.
        """
        if self._seeded:
            return True, "Already initialized"
        self._load_seed_materials()
        self._load_seed_bodies()
        self._load_seed_tears()
        self._load_seed_fractures()
        self._load_seed_deformation_results()
        self._seeded = True
        self._emit(
            SoftBodyEventKind.BODY_REGISTERED.value,
            {"action": "initialize", "materials": len(self._materials),
             "bodies": len(self._bodies)},
        )
        return True, (
            f"Initialized with {len(self._materials)} materials, "
            f"{len(self._bodies)} bodies, "
            f"{len(self._tears)} tears, "
            f"{len(self._fractures)} fractures"
        )

    # ------------------------------------------------------------------
    # Seed Data Loading
    # ------------------------------------------------------------------

    def _load_seed_materials(self) -> None:
        """Load five material presets: rubber, jelly, metal, cloth, flesh."""
        for material_id, props in _MATERIAL_PRESETS.items():
            self._materials[material_id] = MaterialProperties(
                material_id=material_id,
                name=props["name"],
                behavior=props["behavior"],
                youngs_modulus=props["youngs_modulus"],
                poissons_ratio=props["poissons_ratio"],
                yield_strength=props["yield_strength"],
                ultimate_strength=props["ultimate_strength"],
                density=props["density"],
                damping_coefficient=props["damping_coefficient"],
                tear_threshold=props["tear_threshold"],
                fracture_toughness=props["fracture_toughness"],
                volume_preservation=props["volume_preservation"],
            )

    def _load_seed_bodies(self) -> None:
        """Load four soft body meshes: ball, bar, sheet, blob."""
        self._build_ball_body()
        self._build_bar_body()
        self._build_sheet_body()
        self._build_blob_body()

    def _build_ball_body(self) -> None:
        """Build a ball-shaped soft body with 8 vertices and tetrahedra."""
        vertices: Dict[str, SoftBodyVertex] = {}
        # Cube vertices centered at origin, edge length 2
        coords = [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
        ]
        for i, c in enumerate(coords):
            vid = f"ball_v{i}"
            vertices[vid] = SoftBodyVertex(
                id=vid,
                position=(float(c[0]), float(c[1]), float(c[2])),
                velocity=(0.0, 0.0, 0.0),
                mass=0.125,
                pinned=False,
            )

        # Springs along cube edges and face diagonals for structural integrity
        springs: List[SpringConstraint] = []
        edge_pairs = [
            (0, 1), (1, 2), (2, 3), (3, 0),  # bottom face
            (4, 5), (5, 6), (6, 7), (7, 4),  # top face
            (0, 4), (1, 5), (2, 6), (3, 7),  # vertical edges
            (0, 2), (1, 3), (4, 6), (5, 7),  # face diagonals
            (0, 6), (1, 7), (2, 4), (3, 5),  # body diagonals
        ]
        for a, b in edge_pairs:
            va = f"ball_v{a}"
            vb = f"ball_v{b}"
            rest_len = _vec_distance(vertices[va].position, vertices[vb].position)
            springs.append(SpringConstraint(
                id=_new_id("spr"),
                vertex_a_id=va,
                vertex_b_id=vb,
                rest_length=rest_len,
                stiffness=150.0,
                damping=0.05,
                yield_point=0.15,
                plastic_threshold=0.08,
                active=True,
            ))

        # Tetrahedra subdividing the cube into 5 tetrahedra
        tetrahedra: List[Tetrahedron] = []
        tet_verts = [
            (0, 1, 2, 6),
            (0, 2, 3, 6),
            (0, 3, 7, 6),
            (0, 7, 4, 6),
            (0, 4, 1, 6),
        ]
        for tv in tet_verts:
            v_ids = tuple(f"ball_v{i}" for i in tv)
            p0 = vertices[v_ids[0]].position
            p1 = vertices[v_ids[1]].position
            p2 = vertices[v_ids[2]].position
            p3 = vertices[v_ids[3]].position
            vol = _tet_volume(p0, p1, p2, p3)
            tetrahedra.append(Tetrahedron(
                id=_new_id("tet"),
                vertex_ids=v_ids,
                rest_volume=vol,
                current_volume=vol,
                material_id="rubber",
            ))

        body = SoftBody(
            body_id="body_ball",
            name="Rubber Ball",
            vertices=vertices,
            tetrahedra=tetrahedra,
            springs=springs,
            material_id="rubber",
            status=BodyStatus.INTACT,
        )
        self._finalize_body(body)

    def _build_bar_body(self) -> None:
        """Build a bar-shaped soft body with 8 vertices along a rectangular prism."""
        vertices: Dict[str, SoftBodyVertex] = {}
        coords = [
            (-2, -0.5, -0.5), (2, -0.5, -0.5), (2, 0.5, -0.5), (-2, 0.5, -0.5),
            (-2, -0.5, 0.5), (2, -0.5, 0.5), (2, 0.5, 0.5), (-2, 0.5, 0.5),
        ]
        for i, c in enumerate(coords):
            vid = f"bar_v{i}"
            vertices[vid] = SoftBodyVertex(
                id=vid,
                position=(float(c[0]), float(c[1]), float(c[2])),
                velocity=(0.0, 0.0, 0.0),
                mass=0.25,
                pinned=False,
            )

        springs: List[SpringConstraint] = []
        edge_pairs = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
            (0, 2), (1, 3), (4, 6), (5, 7),
            (0, 5), (1, 4), (2, 7), (3, 6),
        ]
        for a, b in edge_pairs:
            va = f"bar_v{a}"
            vb = f"bar_v{b}"
            rest_len = _vec_distance(vertices[va].position, vertices[vb].position)
            springs.append(SpringConstraint(
                id=_new_id("spr"),
                vertex_a_id=va,
                vertex_b_id=vb,
                rest_length=rest_len,
                stiffness=200.0,
                damping=0.02,
                yield_point=0.08,
                plastic_threshold=0.04,
                active=True,
            ))

        tetrahedra: List[Tetrahedron] = []
        tet_verts = [
            (0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6),
            (0, 7, 4, 6), (0, 4, 1, 6),
        ]
        for tv in tet_verts:
            v_ids = tuple(f"bar_v{i}" for i in tv)
            p0 = vertices[v_ids[0]].position
            p1 = vertices[v_ids[1]].position
            p2 = vertices[v_ids[2]].position
            p3 = vertices[v_ids[3]].position
            vol = _tet_volume(p0, p1, p2, p3)
            tetrahedra.append(Tetrahedron(
                id=_new_id("tet"),
                vertex_ids=v_ids,
                rest_volume=vol,
                current_volume=vol,
                material_id="metal",
            ))

        body = SoftBody(
            body_id="body_bar",
            name="Metal Bar",
            vertices=vertices,
            tetrahedra=tetrahedra,
            springs=springs,
            material_id="metal",
            status=BodyStatus.INTACT,
        )
        self._finalize_body(body)

    def _build_sheet_body(self) -> None:
        """Build a sheet-shaped soft body with a 3x3 grid of vertices."""
        vertices: Dict[str, SoftBodyVertex] = {}
        idx = 0
        for rz in range(3):
            for rx in range(3):
                vid = f"sheet_v{idx}"
                x = -1.0 + float(rx)
                z = -1.0 + float(rz)
                vertices[vid] = SoftBodyVertex(
                    id=vid,
                    position=(x, 0.0, z),
                    velocity=(0.0, 0.0, 0.0),
                    mass=0.1,
                    pinned=(rz == 0 and rx == 0),
                )
                idx += 1

        springs: List[SpringConstraint] = []
        # Horizontal and vertical neighbor connections
        for rz in range(3):
            for rx in range(3):
                i = rz * 3 + rx
                if rx < 2:
                    j = i + 1
                    self._add_grid_spring(vertices, springs, f"sheet_v{i}",
                                          f"sheet_v{j}", "cloth")
                if rz < 2:
                    j = i + 3
                    self._add_grid_spring(vertices, springs, f"sheet_v{i}",
                                          f"sheet_v{j}", "cloth")
        # Diagonal connections for shear resistance
        for rz in range(2):
            for rx in range(2):
                i = rz * 3 + rx
                self._add_grid_spring(vertices, springs, f"sheet_v{i}",
                                      f"sheet_v{i+4}", "cloth")
                self._add_grid_spring(vertices, springs, f"sheet_v{i+1}",
                                      f"sheet_v{i+3}", "cloth")

        # Flat tetrahedra with minimal volume (sheet is nearly 2D)
        tetrahedra: List[Tetrahedron] = []
        quads = [(0, 1, 4, 5), (1, 2, 5, 8), (3, 4, 6, 7), (4, 5, 7, 8)]
        for q in quads:
            v_ids = tuple(f"sheet_v{i}" for i in q)
            p0 = vertices[v_ids[0]].position
            p1 = vertices[v_ids[1]].position
            p2 = vertices[v_ids[2]].position
            p3 = vertices[v_ids[3]].position
            vol = _tet_volume(p0, p1, p2, p3)
            tetrahedra.append(Tetrahedron(
                id=_new_id("tet"),
                vertex_ids=v_ids,
                rest_volume=vol,
                current_volume=vol,
                material_id="cloth",
            ))

        body = SoftBody(
            body_id="body_sheet",
            name="Cloth Sheet",
            vertices=vertices,
            tetrahedra=tetrahedra,
            springs=springs,
            material_id="cloth",
            status=BodyStatus.INTACT,
        )
        self._finalize_body(body)

    def _build_blob_body(self) -> None:
        """Build a blob-shaped soft body with 8 irregularly placed vertices."""
        vertices: Dict[str, SoftBodyVertex] = {}
        coords = [
            (0.0, 1.2, 0.0), (1.0, 0.3, 0.5), (0.8, -0.8, -0.3),
            (-0.5, -1.0, 0.4), (-1.1, 0.1, -0.2), (-0.6, 0.8, 0.9),
            (0.3, 0.0, -1.1), (0.0, -0.3, 0.8),
        ]
        for i, c in enumerate(coords):
            vid = f"blob_v{i}"
            vertices[vid] = SoftBodyVertex(
                id=vid,
                position=(float(c[0]), float(c[1]), float(c[2])),
                velocity=(0.0, 0.0, 0.0),
                mass=0.15,
                pinned=False,
            )

        springs: List[SpringConstraint] = []
        # Connect each vertex to its next three neighbors for a dense mesh
        n = len(coords)
        for i in range(n):
            for j in range(1, 4):
                idx = (i + j) % n
                va = f"blob_v{i}"
                vb = f"blob_v{idx}"
                rest_len = _vec_distance(vertices[va].position, vertices[vb].position)
                springs.append(SpringConstraint(
                    id=_new_id("spr"),
                    vertex_a_id=va,
                    vertex_b_id=vb,
                    rest_length=rest_len,
                    stiffness=80.0,
                    damping=0.15,
                    yield_point=0.2,
                    plastic_threshold=0.1,
                    active=True,
                ))

        tetrahedra: List[Tetrahedron] = []
        tet_verts = [(0, 1, 7, 5), (1, 2, 7, 6), (2, 3, 7, 6),
                     (3, 4, 7, 5), (4, 5, 7, 0)]
        for tv in tet_verts:
            v_ids = tuple(f"blob_v{i}" for i in tv)
            p0 = vertices[v_ids[0]].position
            p1 = vertices[v_ids[1]].position
            p2 = vertices[v_ids[2]].position
            p3 = vertices[v_ids[3]].position
            vol = _tet_volume(p0, p1, p2, p3)
            tetrahedra.append(Tetrahedron(
                id=_new_id("tet"),
                vertex_ids=v_ids,
                rest_volume=vol,
                current_volume=vol,
                material_id="flesh",
            ))

        body = SoftBody(
            body_id="body_blob",
            name="Flesh Blob",
            vertices=vertices,
            tetrahedra=tetrahedra,
            springs=springs,
            material_id="flesh",
            status=BodyStatus.INTACT,
        )
        self._finalize_body(body)

    def _add_grid_spring(
        self,
        vertices: Dict[str, SoftBodyVertex],
        springs: List[SpringConstraint],
        va: str,
        vb: str,
        material_id: str,
    ) -> None:
        """Helper to add a spring between two grid vertices."""
        rest_len = _vec_distance(vertices[va].position, vertices[vb].position)
        springs.append(SpringConstraint(
            id=_new_id("spr"),
            vertex_a_id=va,
            vertex_b_id=vb,
            rest_length=rest_len,
            stiffness=50.0,
            damping=0.08,
            yield_point=0.12,
            plastic_threshold=0.06,
            active=True,
        ))

    def _finalize_body(self, body: SoftBody) -> None:
        """Compute derived body properties (center of mass, bounding radius,
        rest volume) and store it in the registry.
        """
        body.center_of_mass = self._compute_center_of_mass(body)
        body.bounding_radius = self._compute_bounding_radius(body)
        body.rest_volume = sum(t.rest_volume for t in body.tetrahedra)
        body.current_volume = body.rest_volume
        self._bodies[body.body_id] = body
        self._emit(
            SoftBodyEventKind.BODY_REGISTERED.value,
            {"body_id": body.body_id, "name": body.name,
             "vertices": len(body.vertices), "material_id": body.material_id},
            body_id=body.body_id,
        )

    def _load_seed_tears(self) -> None:
        """Load three seed tear records associated with seeded bodies."""
        tear_data = [
            ("tear_seed_1", "body_sheet", "sheet_v1", "sheet_v2",
             TearMode.INITIATED, 0.05, ["spr_seed_1"]),
            ("tear_seed_2", "body_blob", "blob_v2", "blob_v3",
             TearMode.PROPAGATING, 0.12, ["spr_seed_2", "spr_seed_3"]),
            ("tear_seed_3", "body_sheet", "sheet_v4", "sheet_v5",
             TearMode.COMPLETE, 0.08, ["spr_seed_4"]),
        ]
        for tid, bid, start_v, end_v, mode, length, springs in tear_data:
            tear = TearRecord(
                tear_id=tid,
                body_id=bid,
                start_vertex_id=start_v,
                end_vertex_id=end_v,
                mode=mode,
                length=length,
                propagated_springs=list(springs),
            )
            self._tears[tid] = tear

    def _load_seed_fractures(self) -> None:
        """Load two seed fracture records associated with seeded bodies."""
        frac_data = [
            ("frac_seed_1", "body_bar", FracturePattern.BRITTLE,
             ["frag_seed_1a", "frag_seed_1b"], "bar_v0", 1.5e5),
            ("frac_seed_2", "body_ball", FracturePattern.SHATTER,
             ["frag_seed_2a", "frag_seed_2b", "frag_seed_2c"],
             "ball_v2", 3.0e5),
        ]
        for fid, bid, pattern, fragments, origin, energy in frac_data:
            frac = FractureRecord(
                fracture_id=fid,
                body_id=bid,
                pattern=pattern,
                fragments=list(fragments),
                origin_vertex_id=origin,
                energy_released=energy,
            )
            self._fractures[fid] = frac

    def _load_seed_deformation_results(self) -> None:
        """Load five seed deformation result records."""
        deform_data = [
            ("body_ball", DeformationType.ELASTIC, 0.03, (0.0, -1.0, 0.0),
             ["ball_v0", "ball_v4"], 0.5, False),
            ("body_bar", DeformationType.PLASTIC, 0.06, (1.0, 0.0, 0.0),
             ["bar_v1", "bar_v5"], 1.2, True),
            ("body_sheet", DeformationType.TEAR, 0.05, (0.0, 0.0, 1.0),
             ["sheet_v1", "sheet_v2"], 0.8, True),
            ("body_blob", DeformationType.COMPRESS, 0.04, (0.0, -1.0, 0.0),
             ["blob_v2", "blob_v3"], 0.3, False),
            ("body_ball", DeformationType.STRETCH, 0.02, (1.0, 0.0, 0.0),
             ["ball_v1", "ball_v5"], 0.15, False),
        ]
        for bid, dtype, mag, direction, affected, energy, permanent in deform_data:
            result = DeformationResult(
                body_id=bid,
                deformation_type=dtype,
                magnitude=mag,
                direction=direction,
                affected_vertices=list(affected),
                energy_dissipated=energy,
                is_permanent=permanent,
            )
            self._deformation_results.append(result)
        self._total_deformations += len(deform_data)

    # ------------------------------------------------------------------
    # Internal computation helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        kind: str,
        payload: Dict[str, Any],
        body_id: str = "",
    ) -> None:
        """Emit an event into the internal event log."""
        event = SoftBodyEvent(
            event_id=_new_id("evt"),
            kind=kind,
            tick=self._tick_count,
            body_id=body_id,
            payload=payload,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _compute_center_of_mass(self, body: SoftBody) -> Tuple[float, float, float]:
        """Compute the mass-weighted center of mass of a body."""
        total_mass = 0.0
        cx = cy = cz = 0.0
        for v in body.vertices.values():
            m = max(v.mass, _EPSILON)
            total_mass += m
            cx += v.position[0] * m
            cy += v.position[1] * m
            cz += v.position[2] * m
        if total_mass < _EPSILON:
            return (0.0, 0.0, 0.0)
        return (cx / total_mass, cy / total_mass, cz / total_mass)

    def _compute_bounding_radius(self, body: SoftBody) -> float:
        """Compute the maximum distance from center of mass to any vertex."""
        com = body.center_of_mass
        max_dist = 0.0
        for v in body.vertices.values():
            dist = _vec_distance(v.position, com)
            if dist > max_dist:
                max_dist = dist
        return max_dist

    def _get_material_for_body(self, body: SoftBody) -> Optional[MaterialProperties]:
        """Look up the material assigned to a body."""
        return self._materials.get(body.material_id)

    def _clear_forces(self, body: SoftBody) -> None:
        """Reset all force accumulators to zero."""
        for v in body.vertices.values():
            v.force_accumulator = (0.0, 0.0, 0.0)

    def _apply_gravity(self, body: SoftBody) -> None:
        """Apply gravitational force to all non-pinned vertices."""
        gravity = self._config.global_gravity
        for v in body.vertices.values():
            if v.pinned:
                continue
            fx = v.force_accumulator[0] + gravity[0] * v.mass
            fy = v.force_accumulator[1] + gravity[1] * v.mass
            fz = v.force_accumulator[2] + gravity[2] * v.mass
            v.force_accumulator = (fx, fy, fz)

    def _apply_spring_forces(self, body: SoftBody) -> float:
        """Compute and apply spring forces. Returns total elastic energy."""
        total_energy = 0.0
        for spring in body.springs:
            if not spring.active:
                continue
            va = body.vertices.get(spring.vertex_a_id)
            vb = body.vertices.get(spring.vertex_b_id)
            if va is None or vb is None:
                continue
            delta = _vec_sub(vb.position, va.position)
            length = _vec_length(delta)
            if length < _EPSILON:
                continue
            direction = _vec_scale(delta, 1.0 / length)
            # Spring force: F = -k * (length - rest_length)
            stretch = length - spring.rest_length
            spring_force = spring.stiffness * stretch
            # Damping force based on relative velocity along spring direction
            rel_vel = _vec_sub(vb.velocity, va.velocity)
            damp_force = spring.damping * _vec_dot(rel_vel, direction)
            force_mag = spring_force + damp_force
            force_vec = _vec_scale(direction, force_mag)
            # Apply opposite forces to each vertex
            if not va.pinned:
                va.force_accumulator = _vec_add(va.force_accumulator, force_vec)
            if not vb.pinned:
                vb.force_accumulator = _vec_sub(vb.force_accumulator, force_vec)
            # Elastic energy: 0.5 * k * stretch^2
            total_energy += 0.5 * spring.stiffness * stretch * stretch
        return total_energy

    def _integrate(self, body: SoftBody, dt: float) -> None:
        """Semi-implicit Euler integration of vertex positions and velocities."""
        damping = 1.0 - _clamp(self._config.global_damping, 0.0, 1.0)
        for v in body.vertices.values():
            if v.pinned:
                v.velocity = (0.0, 0.0, 0.0)
                continue
            mass = max(v.mass, _EPSILON)
            ax = v.force_accumulator[0] / mass
            ay = v.force_accumulator[1] / mass
            az = v.force_accumulator[2] / mass
            # Update velocity with damping
            vx = (v.velocity[0] + ax * dt) * damping
            vy = (v.velocity[1] + ay * dt) * damping
            vz = (v.velocity[2] + az * dt) * damping
            v.velocity = (vx, vy, vz)
            # Update position
            v.position = (
                v.position[0] + vx * dt,
                v.position[1] + vy * dt,
                v.position[2] + vz * dt,
            )

    def _compute_spring_strain(self, body: SoftBody, spring: SpringConstraint) -> float:
        """Compute the strain of a single spring relative to its rest length."""
        va = body.vertices.get(spring.vertex_a_id)
        vb = body.vertices.get(spring.vertex_b_id)
        if va is None or vb is None:
            return 0.0
        length = _vec_distance(va.position, vb.position)
        if spring.rest_length < _EPSILON:
            return 0.0
        return (length - spring.rest_length) / spring.rest_length

    def _update_tetrahedra_volumes(self, body: SoftBody) -> None:
        """Update current_volume for all tetrahedra in a body."""
        for tet in body.tetrahedra:
            positions = []
            for vid in tet.vertex_ids:
                v = body.vertices.get(vid)
                if v is None:
                    positions.append((0.0, 0.0, 0.0))
                else:
                    positions.append(v.position)
            if len(positions) == 4:
                tet.current_volume = _tet_volume(
                    positions[0], positions[1], positions[2], positions[3]
                )

    def _find_adjacent_springs(
        self, body: SoftBody, vertex_id: str, exclude_spring_id: str = ""
    ) -> List[SpringConstraint]:
        """Find all active springs connected to a given vertex."""
        adjacent: List[SpringConstraint] = []
        for spring in body.springs:
            if not spring.active:
                continue
            if spring.id == exclude_spring_id:
                continue
            if spring.vertex_a_id == vertex_id or spring.vertex_b_id == vertex_id:
                adjacent.append(spring)
        return adjacent

    # ------------------------------------------------------------------
    # Material Management
    # ------------------------------------------------------------------

    def register_material(
        self,
        material_id: str,
        name: str,
        behavior: str,
        youngs_modulus: float,
        poissons_ratio: float,
        yield_strength: float,
        ultimate_strength: float,
        density: float,
        damping_coefficient: float,
        tear_threshold: float,
        fracture_toughness: float,
    ) -> Tuple[bool, str, Optional[MaterialProperties]]:
        """Register a new material with full physical properties.

        Args:
            material_id: Unique identifier for the material.
            name: Human-readable material name.
            behavior: Constitutive model (see MaterialBehavior values).
            youngs_modulus: Young's modulus in Pascals.
            poissons_ratio: Poisson's ratio (0 to 0.5).
            yield_strength: Stress at which plastic deformation begins.
            ultimate_strength: Stress at which failure occurs.
            density: Mass density in kg/m^3.
            damping_coefficient: Velocity damping coefficient.
            tear_threshold: Strain threshold for tear initiation.
            fracture_toughness: Energy threshold for fracture.

        Returns:
            Tuple of (success, message, material_properties).
        """
        mid = str(material_id).strip()
        if not mid:
            return False, "Material ID must not be empty", None
        if mid in self._materials:
            return False, f"Material '{mid}' already exists", None
        try:
            behavior_enum = MaterialBehavior(behavior)
        except (ValueError, KeyError):
            return False, f"Invalid behavior '{behavior}'", None
        if poissons_ratio < 0.0 or poissons_ratio > 0.5:
            return False, "Poisson's ratio must be between 0 and 0.5", None
        if density <= 0.0:
            return False, "Density must be positive", None
        if youngs_modulus <= 0.0:
            return False, "Young's modulus must be positive", None
        material = MaterialProperties(
            material_id=mid,
            name=str(name),
            behavior=behavior_enum,
            youngs_modulus=youngs_modulus,
            poissons_ratio=poissons_ratio,
            yield_strength=yield_strength,
            ultimate_strength=ultimate_strength,
            density=density,
            damping_coefficient=damping_coefficient,
            tear_threshold=tear_threshold,
            fracture_toughness=fracture_toughness,
            volume_preservation=VolumePreservation.COMPRESSIBLE,
        )
        self._materials[mid] = material
        self._emit(
            SoftBodyEventKind.MATERIAL_TUNED.value,
            {"material_id": mid, "name": name, "action": "registered"},
        )
        return True, f"Material '{mid}' registered", material

    def remove_material(self, material_id: str) -> Tuple[bool, str]:
        """Remove a material from the registry.

        Materials currently in use by bodies cannot be removed.
        """
        mid = str(material_id).strip()
        if mid not in self._materials:
            return False, f"Material '{mid}' not found"
        in_use = any(b.material_id == mid for b in self._bodies.values())
        if in_use:
            return False, f"Material '{mid}' is in use by one or more bodies"
        del self._materials[mid]
        self._emit(
            SoftBodyEventKind.MATERIAL_TUNED.value,
            {"material_id": mid, "action": "removed"},
        )
        return True, f"Material '{mid}' removed"

    def get_material(self, material_id: str) -> Optional[MaterialProperties]:
        """Retrieve a material by ID."""
        return self._materials.get(str(material_id).strip())

    def list_materials(self) -> List[MaterialProperties]:
        """List all registered materials."""
        return list(self._materials.values())

    # ------------------------------------------------------------------
    # Soft Body Lifecycle
    # ------------------------------------------------------------------

    def register_body(
        self,
        body_id: str,
        name: str,
        material_id: str,
        vertices: Dict[str, SoftBodyVertex],
        tetrahedra: List[Tetrahedron],
        springs: List[SpringConstraint],
    ) -> Tuple[bool, str, Optional[SoftBody]]:
        """Register a new soft body with vertices, tetrahedra, and springs.

        Args:
            body_id: Unique identifier for the body.
            name: Human-readable body name.
            material_id: Material to assign to this body.
            vertices: Dictionary of vertex ID to SoftBodyVertex.
            tetrahedra: List of Tetrahedron elements.
            springs: List of SpringConstraint connections.

        Returns:
            Tuple of (success, message, soft_body).
        """
        bid = str(body_id).strip()
        if not bid:
            return False, "Body ID must not be empty", None
        if bid in self._bodies:
            return False, f"Body '{bid}' already exists", None
        if material_id not in self._materials:
            return False, f"Material '{material_id}' not found", None
        if len(self._bodies) >= self._config.max_bodies:
            return False, "Maximum body count reached", None
        # Convert dict inputs to dataclass objects for API compatibility
        if vertices and isinstance(next(iter(vertices.values())), dict):
            converted = {}
            for vid, vdata in vertices.items():
                if isinstance(vdata, dict):
                    converted[vid] = SoftBodyVertex(
                        id=vdata.get("id", vid),
                        position=tuple(vdata.get("position", (0.0, 0.0, 0.0))),
                        velocity=tuple(vdata.get("velocity", (0.0, 0.0, 0.0))),
                        mass=vdata.get("mass", 1.0),
                        pinned=vdata.get("pinned", False),
                    )
                else:
                    converted[vid] = vdata
            vertices = converted
        if tetrahedra and isinstance(tetrahedra[0], dict):
            converted_tets = []
            for tdata in tetrahedra:
                if isinstance(tdata, dict):
                    converted_tets.append(Tetrahedron(
                        id=tdata.get("id", ""),
                        vertex_ids=tuple(tdata.get("vertex_ids", ("", "", "", ""))),
                        rest_volume=tdata.get("rest_volume", 0.0),
                        current_volume=tdata.get("current_volume", 0.0),
                    ))
                else:
                    converted_tets.append(tdata)
            tetrahedra = converted_tets
        if springs and isinstance(springs[0], dict):
            converted_springs = []
            for sdata in springs:
                if isinstance(sdata, dict):
                    converted_springs.append(SpringConstraint(
                        id=sdata.get("id", ""),
                        vertex_a_id=sdata.get("vertex_a_id", ""),
                        vertex_b_id=sdata.get("vertex_b_id", ""),
                        rest_length=sdata.get("rest_length", 1.0),
                        stiffness=sdata.get("stiffness", 100.0),
                        damping=sdata.get("damping", 0.1),
                        yield_point=sdata.get("yield_point", 0.1),
                        plastic_threshold=sdata.get("plastic_threshold", 0.05),
                        active=sdata.get("active", True),
                    ))
                else:
                    converted_springs.append(sdata)
            springs = converted_springs
        if len(vertices) > self._config.max_vertices_per_body:
            return False, (
                f"Body exceeds max vertices "
                f"({len(vertices)} > {self._config.max_vertices_per_body})"
            ), None
        if not vertices:
            return False, "Body must have at least one vertex", None

        body = SoftBody(
            body_id=bid,
            name=str(name),
            vertices=dict(vertices),
            tetrahedra=list(tetrahedra),
            springs=list(springs),
            material_id=str(material_id),
            status=BodyStatus.INTACT,
        )
        self._finalize_body(body)
        return True, f"Body '{bid}' registered", body

    def remove_body(self, body_id: str) -> Tuple[bool, str]:
        """Remove a soft body and its associated tears and fractures."""
        bid = str(body_id).strip()
        if bid not in self._bodies:
            return False, f"Body '{bid}' not found"
        del self._bodies[bid]
        # Remove associated tears
        tear_ids_to_remove = [
            tid for tid, t in self._tears.items() if t.body_id == bid
        ]
        for tid in tear_ids_to_remove:
            del self._tears[tid]
        # Remove associated fractures
        frac_ids_to_remove = [
            fid for fid, f in self._fractures.items() if f.body_id == bid
        ]
        for fid in frac_ids_to_remove:
            del self._fractures[fid]
        self._emit(
            SoftBodyEventKind.BODY_REMOVED.value,
            {"body_id": bid},
            body_id=bid,
        )
        return True, f"Body '{bid}' removed"

    def get_body(self, body_id: str) -> Optional[SoftBody]:
        """Retrieve a soft body by ID."""
        return self._bodies.get(str(body_id).strip())

    def list_bodies(self, status: Optional[str] = None) -> List[SoftBody]:
        """List all bodies, optionally filtered by status.

        Args:
            status: Optional status string (see BodyStatus values). If None,
                all bodies are returned.

        Returns:
            List of SoftBody instances matching the filter.
        """
        if status is None:
            return list(self._bodies.values())
        try:
            status_enum = BodyStatus(status)
        except (ValueError, KeyError):
            return []
        return [b for b in self._bodies.values() if b.status == status_enum]

    # ------------------------------------------------------------------
    # Deformation Drivers
    # ------------------------------------------------------------------

    def apply_force(
        self,
        body_id: str,
        vertex_id: str,
        force: Tuple[float, float, float],
    ) -> Tuple[bool, str, DeformationResult]:
        """Apply a force vector to a specific vertex.

        Args:
            body_id: Target body ID.
            vertex_id: Target vertex ID within the body.
            force: Force vector (fx, fy, fz).

        Returns:
            Tuple of (success, message, deformation_result).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", DeformationResult()
        vertex = body.vertices.get(str(vertex_id).strip())
        if vertex is None:
            return False, f"Vertex '{vertex_id}' not found in body '{bid}'", DeformationResult()
        if vertex.pinned:
            return False, f"Vertex '{vertex_id}' is pinned", DeformationResult()
        # Accumulate the applied force
        fx = vertex.force_accumulator[0] + force[0]
        fy = vertex.force_accumulator[1] + force[1]
        fz = vertex.force_accumulator[2] + force[2]
        vertex.force_accumulator = (fx, fy, fz)
        magnitude = _vec_length(force)
        direction = _vec_normalize(force)
        # Mark body as deformed
        if body.status == BodyStatus.INTACT:
            body.status = BodyStatus.DEFORMED
        result = DeformationResult(
            body_id=bid,
            deformation_type=DeformationType.ELASTIC,
            magnitude=magnitude,
            direction=direction,
            affected_vertices=[vertex.id],
            energy_dissipated=0.0,
            is_permanent=False,
        )
        self._deformation_results.append(result)
        _evict_fifo_list(self._deformation_results, _MAX_EVENTS)
        self._total_deformations += 1
        self._emit(
            SoftBodyEventKind.DEFORMATION_APPLIED.value,
            {"body_id": bid, "vertex_id": vertex.id,
             "type": "force", "magnitude": magnitude},
            body_id=bid,
        )
        return True, f"Force applied to vertex '{vertex.id}'", result

    def apply_pressure(
        self,
        body_id: str,
        pressure: float,
    ) -> Tuple[bool, str, DeformationResult]:
        """Apply uniform pressure to all vertices of a body.

        The pressure is directed along the inward normal from each vertex
        toward the center of mass, simulating volumetric compression or
        expansion.

        Args:
            body_id: Target body ID.
            pressure: Pressure magnitude (positive compresses, negative expands).

        Returns:
            Tuple of (success, message, deformation_result).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", DeformationResult()
        com = body.center_of_mass
        affected: List[str] = []
        total_force_mag = 0.0
        for v in body.vertices.values():
            if v.pinned:
                continue
            # Direction from vertex to center of mass (inward)
            to_center = _vec_sub(com, v.position)
            direction = _vec_normalize(to_center)
            # Force proportional to pressure and vertex mass
            force_mag = pressure * v.mass
            force_vec = _vec_scale(direction, force_mag)
            v.force_accumulator = _vec_add(v.force_accumulator, force_vec)
            affected.append(v.id)
            total_force_mag += abs(force_mag)
        if body.status == BodyStatus.INTACT:
            body.status = BodyStatus.DEFORMED
        avg_direction = (0.0, -1.0, 0.0) if pressure > 0 else (0.0, 1.0, 0.0)
        dtype = DeformationType.COMPRESS if pressure > 0 else DeformationType.STRETCH
        result = DeformationResult(
            body_id=bid,
            deformation_type=dtype,
            magnitude=total_force_mag,
            direction=avg_direction,
            affected_vertices=affected,
            energy_dissipated=0.0,
            is_permanent=False,
        )
        self._deformation_results.append(result)
        _evict_fifo_list(self._deformation_results, _MAX_EVENTS)
        self._total_deformations += 1
        self._emit(
            SoftBodyEventKind.DEFORMATION_APPLIED.value,
            {"body_id": bid, "type": "pressure", "pressure": pressure,
             "affected": len(affected)},
            body_id=bid,
        )
        return True, f"Pressure {pressure} applied to {len(affected)} vertices", result

    def apply_impact(
        self,
        body_id: str,
        contact_point: Tuple[float, float, float],
        impulse: Tuple[float, float, float],
        radius: float,
    ) -> Tuple[bool, str, DeformationResult]:
        """Apply an impact impulse to vertices within a radius of contact.

        The impulse is distributed to vertices based on their distance from
        the contact point, with closer vertices receiving a larger share.

        Args:
            body_id: Target body ID.
            contact_point: World-space point of impact.
            impulse: Impulse vector (ix, iy, iz).
            radius: Influence radius around the contact point.

        Returns:
            Tuple of (success, message, deformation_result).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", DeformationResult()
        if radius <= 0.0:
            return False, "Impact radius must be positive", DeformationResult()
        affected: List[str] = []
        total_energy = 0.0
        impulse_mag = _vec_length(impulse)
        impulse_dir = _vec_normalize(impulse)
        for v in body.vertices.values():
            if v.pinned:
                continue
            dist = _vec_distance(v.position, contact_point)
            if dist > radius:
                continue
            # Falloff: linear from 1.0 at center to 0.0 at radius
            falloff = 1.0 - (dist / radius)
            if falloff <= 0.0:
                continue
            scaled_impulse = _vec_scale(impulse, falloff)
            # Apply as instantaneous velocity change
            mass = max(v.mass, _EPSILON)
            dv = _vec_scale(scaled_impulse, 1.0 / mass)
            v.velocity = _vec_add(v.velocity, dv)
            affected.append(v.id)
            total_energy += 0.5 * mass * _vec_length(dv) * _vec_length(dv)
        if not affected:
            return False, "No vertices within impact radius", DeformationResult()
        if body.status == BodyStatus.INTACT:
            body.status = BodyStatus.DEFORMED
        # Accumulate damage for fracture checking
        body.damage_accumulated += total_energy
        result = DeformationResult(
            body_id=bid,
            deformation_type=DeformationType.ELASTIC,
            magnitude=impulse_mag,
            direction=impulse_dir,
            affected_vertices=affected,
            energy_dissipated=total_energy,
            is_permanent=False,
        )
        self._deformation_results.append(result)
        _evict_fifo_list(self._deformation_results, _MAX_EVENTS)
        self._total_deformations += 1
        self._total_energy_dissipated += total_energy
        self._emit(
            SoftBodyEventKind.DEFORMATION_APPLIED.value,
            {"body_id": bid, "type": "impact", "impulse": impulse_mag,
             "radius": radius, "affected": len(affected)},
            body_id=bid,
        )
        return True, f"Impact applied to {len(affected)} vertices", result

    def apply_twist(
        self,
        body_id: str,
        axis: Tuple[float, float, float],
        torque: float,
    ) -> Tuple[bool, str, DeformationResult]:
        """Apply a twisting torque around an axis through the center of mass.

        Each vertex receives a tangential force proportional to its distance
        from the axis and the torque magnitude.

        Args:
            body_id: Target body ID.
            axis: Rotation axis (will be normalized).
            torque: Torque magnitude.

        Returns:
            Tuple of (success, message, deformation_result).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", DeformationResult()
        axis_norm = _vec_normalize(axis)
        com = body.center_of_mass
        affected: List[str] = []
        total_mag = 0.0
        for v in body.vertices.values():
            if v.pinned:
                continue
            # Vector from center of mass to vertex
            r_vec = _vec_sub(v.position, com)
            # Project out the component along the axis to get perpendicular distance
            axial_component = _vec_scale(axis_norm, _vec_dot(r_vec, axis_norm))
            perp = _vec_sub(r_vec, axial_component)
            perp_len = _vec_length(perp)
            if perp_len < _EPSILON:
                continue
            # Tangential direction: cross product of axis and perpendicular vector
            tangent = _vec_cross(axis_norm, perp)
            tangent = _vec_normalize(tangent)
            # Force proportional to torque and distance from axis
            force_mag = torque * perp_len / max(len(body.vertices), 1)
            force_vec = _vec_scale(tangent, force_mag)
            v.force_accumulator = _vec_add(v.force_accumulator, force_vec)
            affected.append(v.id)
            total_mag += abs(force_mag)
        if not affected:
            return False, "No vertices available for twist", DeformationResult()
        if body.status == BodyStatus.INTACT:
            body.status = BodyStatus.DEFORMED
        result = DeformationResult(
            body_id=bid,
            deformation_type=DeformationType.TWIST,
            magnitude=total_mag,
            direction=axis_norm,
            affected_vertices=affected,
            energy_dissipated=0.0,
            is_permanent=False,
        )
        self._deformation_results.append(result)
        _evict_fifo_list(self._deformation_results, _MAX_EVENTS)
        self._total_deformations += 1
        self._emit(
            SoftBodyEventKind.DEFORMATION_APPLIED.value,
            {"body_id": bid, "type": "twist", "torque": torque,
             "affected": len(affected)},
            body_id=bid,
        )
        return True, f"Twist applied to {len(affected)} vertices", result

    def apply_bend(
        self,
        body_id: str,
        axis: Tuple[float, float, float],
        angle: float,
    ) -> Tuple[bool, str, DeformationResult]:
        """Apply a bending deformation around an axis.

        Vertices are displaced based on their position along the bending axis,
        creating a bending moment. The angle parameter controls the severity
        of the bend.

        Args:
            body_id: Target body ID.
            axis: Bending axis (will be normalized).
            angle: Bending angle in radians.

        Returns:
            Tuple of (success, message, deformation_result).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", DeformationResult()
        axis_norm = _vec_normalize(axis)
        com = body.center_of_mass
        affected: List[str] = []
        total_mag = 0.0
        for v in body.vertices.values():
            if v.pinned:
                continue
            # Vector from center of mass to vertex
            r_vec = _vec_sub(v.position, com)
            # Component along the bending axis
            axial = _vec_dot(r_vec, axis_norm)
            # Perpendicular component
            perp = _vec_sub(r_vec, _vec_scale(axis_norm, axial))
            # Bend force: proportional to axial position and angle
            # Vertices further along the axis get more bending force
            bend_force_mag = angle * axial * 10.0
            if _vec_length(perp) < _EPSILON:
                continue
            perp_dir = _vec_normalize(perp)
            force_vec = _vec_scale(perp_dir, bend_force_mag)
            v.force_accumulator = _vec_add(v.force_accumulator, force_vec)
            affected.append(v.id)
            total_mag += abs(bend_force_mag)
        if not affected:
            return False, "No vertices available for bending", DeformationResult()
        if body.status == BodyStatus.INTACT:
            body.status = BodyStatus.DEFORMED
        result = DeformationResult(
            body_id=bid,
            deformation_type=DeformationType.BEND,
            magnitude=total_mag,
            direction=axis_norm,
            affected_vertices=affected,
            energy_dissipated=0.0,
            is_permanent=False,
        )
        self._deformation_results.append(result)
        _evict_fifo_list(self._deformation_results, _MAX_EVENTS)
        self._total_deformations += 1
        self._emit(
            SoftBodyEventKind.DEFORMATION_APPLIED.value,
            {"body_id": bid, "type": "bend", "angle": angle,
             "affected": len(affected)},
            body_id=bid,
        )
        return True, f"Bend applied to {len(affected)} vertices", result

    # ------------------------------------------------------------------
    # Stress and Strain Computation
    # ------------------------------------------------------------------

    def compute_stress(
        self,
        body_id: str,
    ) -> Tuple[bool, str, Dict[str, float]]:
        """Compute per-vertex stress based on spring forces.

        Stress at each vertex is computed as the magnitude of the net spring
        force divided by the vertex mass, providing a mass-normalized stress
        measure.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, stress_dict) where stress_dict maps
            vertex IDs to stress values.
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", {}
        material = self._get_material_for_body(body)
        # Accumulate spring forces per vertex
        force_sum: Dict[str, Tuple[float, float, float]] = {
            vid: (0.0, 0.0, 0.0) for vid in body.vertices
        }
        for spring in body.springs:
            if not spring.active:
                continue
            va = body.vertices.get(spring.vertex_a_id)
            vb = body.vertices.get(spring.vertex_b_id)
            if va is None or vb is None:
                continue
            delta = _vec_sub(vb.position, va.position)
            length = _vec_length(delta)
            if length < _EPSILON:
                continue
            direction = _vec_scale(delta, 1.0 / length)
            stretch = length - spring.rest_length
            force_mag = spring.stiffness * stretch
            force_vec = _vec_scale(direction, force_mag)
            # Force on vertex_a is along direction, on vertex_b is opposite
            fa = force_sum.get(va.id, (0.0, 0.0, 0.0))
            force_sum[va.id] = _vec_add(fa, force_vec)
            fb = force_sum.get(vb.id, (0.0, 0.0, 0.0))
            force_sum[vb.id] = _vec_sub(fb, force_vec)
        stress_dict: Dict[str, float] = {}
        for vid, fvec in force_sum.items():
            v = body.vertices[vid]
            mass = max(v.mass, _EPSILON)
            # Stress = force magnitude / mass
            stress = _vec_length(fvec) / mass
            stress_dict[vid] = stress
        # Emit warning if stress exceeds threshold
        if material:
            max_stress = max(stress_dict.values()) if stress_dict else 0.0
            if max_stress > material.yield_strength * self._config.stress_threshold_warning:
                self._emit(
                    SoftBodyEventKind.STRESS_EXCEEDED.value,
                    {"body_id": bid, "max_stress": max_stress,
                     "threshold": material.yield_strength},
                    body_id=bid,
                )
        return True, f"Stress computed for {len(stress_dict)} vertices", stress_dict

    def compute_strain(
        self,
        body_id: str,
    ) -> Tuple[bool, str, Dict[str, float]]:
        """Compute per-spring strain (relative deformation).

        Strain = (current_length - rest_length) / rest_length

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, strain_dict) where strain_dict maps
            spring IDs to strain values.
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", {}
        strain_dict: Dict[str, float] = {}
        for spring in body.springs:
            if not spring.active:
                continue
            strain = self._compute_spring_strain(body, spring)
            strain_dict[spring.id] = strain
        return True, f"Strain computed for {len(strain_dict)} springs", strain_dict

    def check_yield(
        self,
        body_id: str,
    ) -> Tuple[bool, str, List[str]]:
        """Check which springs have exceeded their yield point.

        A spring yields when its strain magnitude exceeds the yield_point
        value, indicating the onset of plastic deformation.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, yielded_spring_ids).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", []
        yielded: List[str] = []
        for spring in body.springs:
            if not spring.active:
                continue
            strain = abs(self._compute_spring_strain(body, spring))
            if strain > spring.yield_point:
                yielded.append(spring.id)
        if yielded and body.status == BodyStatus.DEFORMED:
            body.status = BodyStatus.YIELDING
        return True, f"{len(yielded)} springs yielded", yielded

    # ------------------------------------------------------------------
    # Plastic Deformation
    # ------------------------------------------------------------------

    def apply_plastic_flow(
        self,
        body_id: str,
        dt: float,
    ) -> Tuple[bool, str, int]:
        """Convert elastic deformation to plastic for yielded springs.

        For each spring whose strain exceeds the plastic threshold, the rest
        length is gradually adjusted toward the current length, making the
        deformation permanent. The rate of conversion depends on dt.

        Args:
            body_id: Target body ID.
            dt: Time step controlling the rate of plastic flow.

        Returns:
            Tuple of (success, message, num_springs_converted).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", 0
        if not self._config.enable_plastic_flow:
            return True, "Plastic flow disabled", 0
        converted = 0
        total_plastic_delta = 0.0
        for spring in body.springs:
            if not spring.active:
                continue
            strain = abs(self._compute_spring_strain(body, spring))
            if strain <= spring.plastic_threshold:
                continue
            # Only convert if strain exceeds plastic threshold
            va = body.vertices.get(spring.vertex_a_id)
            vb = body.vertices.get(spring.vertex_b_id)
            if va is None or vb is None:
                continue
            current_length = _vec_distance(va.position, vb.position)
            # Gradual conversion: move rest_length toward current_length
            # Conversion rate proportional to dt and strain excess
            excess = strain - spring.plastic_threshold
            rate = _clamp(dt * excess * 2.0, 0.0, 0.5)
            old_rest = spring.rest_length
            spring.rest_length = old_rest + (current_length - old_rest) * rate
            delta = abs(spring.rest_length - old_rest)
            total_plastic_delta += delta
            if delta > _EPSILON:
                converted += 1
        if converted > 0:
            body.plastic_deformation += total_plastic_delta
            body.total_deformation += total_plastic_delta
            self._total_plastic_flows += converted
            self._emit(
                SoftBodyEventKind.PLASTIC_FLOW.value,
                {"body_id": bid, "springs_converted": converted,
                 "plastic_delta": total_plastic_delta},
                body_id=bid,
            )
        return True, f"Plastic flow applied to {converted} springs", converted

    # ------------------------------------------------------------------
    # Tear System
    # ------------------------------------------------------------------

    def check_tear(
        self,
        body_id: str,
    ) -> Tuple[bool, str, Optional[TearRecord]]:
        """Check for tear initiation when spring strain exceeds tear threshold.

        When a spring's strain exceeds the material's tear_threshold, a tear
        is initiated at that spring. The spring is deactivated and a TearRecord
        is created.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, tear_record). tear_record is None if
            no tear was detected.
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", None
        if not self._config.enable_tearing:
            return True, "Tearing disabled", None
        material = self._get_material_for_body(body)
        if material is None:
            return False, f"Material '{body.material_id}' not found", None
        for spring in body.springs:
            if not spring.active:
                continue
            strain = abs(self._compute_spring_strain(body, spring))
            if strain <= material.tear_threshold:
                continue
            # Initiate tear at this spring
            spring.active = False
            tear = TearRecord(
                tear_id=_new_id("tear"),
                body_id=bid,
                start_vertex_id=spring.vertex_a_id,
                end_vertex_id=spring.vertex_b_id,
                mode=TearMode.INITIATED,
                length=spring.rest_length,
                propagated_springs=[spring.id],
            )
            self._tears[tear.tear_id] = tear
            self._total_tears += 1
            body.status = BodyStatus.TEARING
            self._emit(
                SoftBodyEventKind.TEAR_INITIATED.value,
                {"body_id": bid, "tear_id": tear.tear_id,
                 "spring_id": spring.id, "strain": strain},
                body_id=bid,
            )
            return True, f"Tear initiated at spring '{spring.id}'", tear
        return True, "No tear detected", None

    def propagate_tear(
        self,
        body_id: str,
        tear_id: str,
    ) -> Tuple[bool, str, Optional[TearRecord]]:
        """Propagate an existing tear to adjacent springs.

        The tear extends to neighboring active springs connected to the tear
        endpoints, deactivating them if their strain exceeds a propagation
        threshold (half the tear threshold).

        Args:
            body_id: Target body ID.
            tear_id: ID of the tear to propagate.

        Returns:
            Tuple of (success, message, updated_tear_record).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", None
        tear = self._tears.get(str(tear_id).strip())
        if tear is None:
            return False, f"Tear '{tear_id}' not found", None
        if tear.body_id != bid:
            return False, f"Tear '{tear_id}' does not belong to body '{bid}'", None
        if tear.mode == TearMode.COMPLETE:
            return True, "Tear already complete", tear
        material = self._get_material_for_body(body)
        if material is None:
            return False, f"Material not found for body '{bid}'", None
        propagation_threshold = material.tear_threshold * 0.5
        newly_severed: List[str] = []
        # Find adjacent springs to both endpoints of the tear
        for endpoint_id in [tear.start_vertex_id, tear.end_vertex_id]:
            adjacent = self._find_adjacent_springs(body, endpoint_id)
            for spring in adjacent:
                if not spring.active:
                    continue
                if spring.id in tear.propagated_springs:
                    continue
                strain = abs(self._compute_spring_strain(body, spring))
                if strain > propagation_threshold:
                    spring.active = False
                    newly_severed.append(spring.id)
                    tear.propagated_springs.append(spring.id)
        if newly_severed:
            tear.mode = TearMode.PROPAGATING
            tear.length += len(newly_severed) * 0.01  # Approximate extension
            self._emit(
                SoftBodyEventKind.TEAR_PROPAGATED.value,
                {"body_id": bid, "tear_id": tear.tear_id,
                 "new_springs": len(newly_severed)},
                body_id=bid,
            )
            # Check if tear is complete (no more adjacent active springs)
            has_active_adjacent = False
            for endpoint_id in [tear.start_vertex_id, tear.end_vertex_id]:
                adjacent = self._find_adjacent_springs(body, endpoint_id)
                if adjacent:
                    has_active_adjacent = True
                    break
            if not has_active_adjacent:
                tear.mode = TearMode.COMPLETE
            return True, (
                f"Tear propagated to {len(newly_severed)} springs"
            ), tear
        else:
            tear.mode = TearMode.COMPLETE
            return True, "Tear propagation complete (no more eligible springs)", tear

    def get_tear(self, tear_id: str) -> Optional[TearRecord]:
        """Retrieve a tear record by ID."""
        return self._tears.get(str(tear_id).strip())

    def list_tears(self, body_id: str) -> List[TearRecord]:
        """List all tear records associated with a body."""
        bid = str(body_id).strip()
        return [t for t in self._tears.values() if t.body_id == bid]

    # ------------------------------------------------------------------
    # Fracture System
    # ------------------------------------------------------------------

    def check_fracture(
        self,
        body_id: str,
    ) -> Tuple[bool, str, Optional[FractureRecord]]:
        """Check if accumulated damage exceeds fracture toughness.

        When the body's accumulated damage exceeds the material's fracture
        toughness, a fracture is detected and a FractureRecord is created.
        The fracture origin is set to the vertex with the highest stress.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, fracture_record). fracture_record is
            None if no fracture was detected.
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", None
        if not self._config.enable_fracture:
            return True, "Fracture disabled", None
        material = self._get_material_for_body(body)
        if material is None:
            return False, f"Material not found for body '{bid}'", None
        if body.damage_accumulated <= material.fracture_toughness:
            return True, "No fracture detected", None
        # Find the vertex with highest stress as fracture origin
        ok, _, stress_dict = self.compute_stress(bid)
        if not ok or not stress_dict:
            origin_vertex = next(iter(body.vertices), "")
        else:
            origin_vertex = max(stress_dict, key=stress_dict.get, default="")
        # Determine fracture pattern based on material behavior
        pattern = self._determine_fracture_pattern(material)
        energy_released = body.damage_accumulated - material.fracture_toughness
        # Create fragments (conceptual: split body into two halves)
        fragment_ids = [
            f"frag_{_new_id()}",
            f"frag_{_new_id()}",
        ]
        fracture = FractureRecord(
            fracture_id=_new_id("frac"),
            body_id=bid,
            pattern=pattern,
            fragments=fragment_ids,
            origin_vertex_id=origin_vertex,
            energy_released=energy_released,
        )
        self._fractures[fracture.fracture_id] = fracture
        self._total_fractures += 1
        body.status = BodyStatus.FRACTURED
        body.damage_accumulated = 0.0
        self._total_energy_dissipated += energy_released
        self._emit(
            SoftBodyEventKind.FRACTURE_DETECTED.value,
            {"body_id": bid, "fracture_id": fracture.fracture_id,
             "pattern": pattern.value, "energy": energy_released},
            body_id=bid,
        )
        return True, f"Fracture detected: {pattern.value}", fracture

    def fracture_body(
        self,
        body_id: str,
        pattern: str,
    ) -> Tuple[bool, str, Optional[FractureRecord]]:
        """Force a fracture on a body with a specified pattern.

        Args:
            body_id: Target body ID.
            pattern: Fracture pattern (see FracturePattern values).

        Returns:
            Tuple of (success, message, fracture_record).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", None
        try:
            pattern_enum = FracturePattern(pattern)
        except (ValueError, KeyError):
            return False, f"Invalid fracture pattern '{pattern}'", None
        # Find the vertex with highest stress as origin
        ok, _, stress_dict = self.compute_stress(bid)
        if not ok or not stress_dict:
            origin_vertex = next(iter(body.vertices), "")
        else:
            origin_vertex = max(stress_dict, key=stress_dict.get, default="")
        energy_released = body.damage_accumulated + body.elastic_energy
        fragment_ids = [f"frag_{_new_id()}" for _ in range(self._estimate_fragment_count(pattern_enum))]
        fracture = FractureRecord(
            fracture_id=_new_id("frac"),
            body_id=bid,
            pattern=pattern_enum,
            fragments=fragment_ids,
            origin_vertex_id=origin_vertex,
            energy_released=energy_released,
        )
        self._fractures[fracture.fracture_id] = fracture
        self._total_fractures += 1
        body.status = BodyStatus.FRACTURED
        body.damage_accumulated = 0.0
        self._total_energy_dissipated += energy_released
        self._emit(
            SoftBodyEventKind.FRACTURE_DETECTED.value,
            {"body_id": bid, "fracture_id": fracture.fracture_id,
             "pattern": pattern_enum.value, "forced": True,
             "energy": energy_released},
            body_id=bid,
        )
        return True, f"Body fractured with pattern '{pattern_enum.value}'", fracture

    def _determine_fracture_pattern(
        self, material: MaterialProperties
    ) -> FracturePattern:
        """Determine a fracture pattern based on material behavior."""
        if material.behavior == MaterialBehavior.RIGID:
            return FracturePattern.BRITTLE
        if material.behavior == MaterialBehavior.ELASTOPLASTIC:
            return FracturePattern.DUCTILE
        if material.behavior == MaterialBehavior.HYPERELASTIC:
            return FracturePattern.PEEL
        if material.behavior == MaterialBehavior.VISCOELASTIC:
            return FracturePattern.DUCTILE
        if material.behavior == MaterialBehavior.NONLINEAR_ELASTIC:
            return FracturePattern.SPLINTER
        return FracturePattern.CLEAN

    def _estimate_fragment_count(self, pattern: FracturePattern) -> int:
        """Estimate the number of fragments based on fracture pattern."""
        if pattern == FracturePattern.SHATTER:
            return 4
        if pattern == FracturePattern.SPLINTER:
            return 3
        if pattern == FracturePattern.BRITTLE:
            return 3
        return 2

    def get_fracture(self, fracture_id: str) -> Optional[FractureRecord]:
        """Retrieve a fracture record by ID."""
        return self._fractures.get(str(fracture_id).strip())

    def list_fractures(self, body_id: str) -> List[FractureRecord]:
        """List all fracture records associated with a body."""
        bid = str(body_id).strip()
        return [f for f in self._fractures.values() if f.body_id == bid]

    # ------------------------------------------------------------------
    # Vertex Manipulation
    # ------------------------------------------------------------------

    def pin_vertex(self, body_id: str, vertex_id: str) -> Tuple[bool, str]:
        """Pin a vertex so it is fixed in space during simulation.

        Args:
            body_id: Target body ID.
            vertex_id: Vertex to pin.

        Returns:
            Tuple of (success, message).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found"
        vertex = body.vertices.get(str(vertex_id).strip())
        if vertex is None:
            return False, f"Vertex '{vertex_id}' not found in body '{bid}'"
        vertex.pinned = True
        vertex.velocity = (0.0, 0.0, 0.0)
        return True, f"Vertex '{vertex_id}' pinned"

    def unpin_vertex(self, body_id: str, vertex_id: str) -> Tuple[bool, str]:
        """Unpin a previously pinned vertex.

        Args:
            body_id: Target body ID.
            vertex_id: Vertex to unpin.

        Returns:
            Tuple of (success, message).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found"
        vertex = body.vertices.get(str(vertex_id).strip())
        if vertex is None:
            return False, f"Vertex '{vertex_id}' not found in body '{bid}'"
        vertex.pinned = False
        return True, f"Vertex '{vertex_id}' unpinned"

    def set_vertex_position(
        self,
        body_id: str,
        vertex_id: str,
        position: Tuple[float, float, float],
    ) -> Tuple[bool, str]:
        """Set the position of a vertex directly.

        Args:
            body_id: Target body ID.
            vertex_id: Vertex to move.
            position: New position (x, y, z).

        Returns:
            Tuple of (success, message).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found"
        vertex = body.vertices.get(str(vertex_id).strip())
        if vertex is None:
            return False, f"Vertex '{vertex_id}' not found in body '{bid}'"
        vertex.position = (float(position[0]), float(position[1]), float(position[2]))
        vertex.velocity = (0.0, 0.0, 0.0)
        # Update derived properties
        body.center_of_mass = self._compute_center_of_mass(body)
        body.bounding_radius = self._compute_bounding_radius(body)
        return True, f"Vertex '{vertex_id}' position set"

    def get_vertex(
        self,
        body_id: str,
        vertex_id: str,
    ) -> Optional[SoftBodyVertex]:
        """Retrieve a vertex from a body by ID."""
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return None
        return body.vertices.get(str(vertex_id).strip())

    def list_vertices(self, body_id: str) -> List[SoftBodyVertex]:
        """List all vertices in a body."""
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return []
        return list(body.vertices.values())

    # ------------------------------------------------------------------
    # AI Assessment and Tuning
    # ------------------------------------------------------------------

    def ai_assess_body(self, body_id: str) -> Tuple[bool, str, AIAssessment]:
        """Perform AI assessment of a body's stress distribution and stability.

        Analyzes per-vertex stress, identifies high-risk areas, and computes
        recommended stiffness and damping values along with an overall
        stability score.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, ai_assessment).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", AIAssessment()
        material = self._get_material_for_body(body)
        # Compute stress distribution
        ok, _, stress_dict = self.compute_stress(bid)
        if not ok:
            stress_dict = {}
        # Identify risk areas: vertices with stress above 70% of yield strength
        risk_threshold = 0.0
        if material:
            risk_threshold = material.yield_strength * 0.7
        risk_areas: List[str] = []
        for vid, stress in stress_dict.items():
            if stress > risk_threshold:
                risk_areas.append(vid)
        # Compute stability score: 1.0 (stable) to 0.0 (unstable)
        max_stress = max(stress_dict.values()) if stress_dict else 0.0
        if material and material.yield_strength > 0:
            stress_ratio = max_stress / material.yield_strength
            stability = _clamp(1.0 - stress_ratio, 0.0, 1.0)
        else:
            stability = 1.0
        # Recommend stiffness: increase if too much deformation, decrease if too stiff
        avg_strain = 0.0
        ok_s, _, strain_dict = self.compute_strain(bid)
        if ok_s and strain_dict:
            avg_strain = sum(abs(s) for s in strain_dict.values()) / len(strain_dict)
        if material:
            if avg_strain > material.yield_strength * 0.001:
                recommended_stiffness = material.youngs_modulus * 1.2
            elif avg_strain < 0.001:
                recommended_stiffness = material.youngs_modulus * 0.9
            else:
                recommended_stiffness = material.youngs_modulus
            recommended_damping = _clamp(
                material.damping_coefficient + (1.0 - stability) * 0.1,
                0.0, 1.0
            )
        else:
            recommended_stiffness = 100.0
            recommended_damping = 0.1
        assessment = AIAssessment(
            body_id=bid,
            stress_distribution=stress_dict,
            recommended_stiffness=recommended_stiffness,
            recommended_damping=recommended_damping,
            risk_areas=risk_areas,
            stability_score=stability,
        )
        return True, f"Assessment complete (stability={stability:.3f})", assessment

    def ai_tune_material(
        self,
        body_id: str,
        target_stiffness: float,
    ) -> Tuple[bool, str, MaterialProperties]:
        """AI-tune the material properties of a body toward a target stiffness.

        Adjusts the Young's modulus of the body's material toward the target
        stiffness and recalibrates damping based on the current stress state.
        The material is updated in place and a copy is returned.

        Args:
            body_id: Target body ID.
            target_stiffness: Desired Young's modulus in Pascals.

        Returns:
            Tuple of (success, message, updated_material).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", MaterialProperties()
        material = self._get_material_for_body(body)
        if material is None:
            return False, f"Material '{body.material_id}' not found", MaterialProperties()
        if target_stiffness <= 0.0:
            return False, "Target stiffness must be positive", MaterialProperties()
        # Gradual adjustment: move 50% toward target
        adjustment_rate = 0.5
        old_modulus = material.youngs_modulus
        material.youngs_modulus = old_modulus + (target_stiffness - old_modulus) * adjustment_rate
        # Adjust yield and ultimate strength proportionally
        ratio = material.youngs_modulus / max(old_modulus, _EPSILON)
        material.yield_strength = material.yield_strength * ratio
        material.ultimate_strength = material.ultimate_strength * ratio
        # Assess current state and adjust damping
        ok, _, assessment = self.ai_assess_body(bid)
        if ok:
            material.damping_coefficient = assessment.recommended_damping
        self._emit(
            SoftBodyEventKind.MATERIAL_TUNED.value,
            {"body_id": bid, "material_id": material.material_id,
             "old_modulus": old_modulus, "new_modulus": material.youngs_modulus,
             "target": target_stiffness},
            body_id=bid,
        )
        return True, (
            f"Material tuned: modulus {old_modulus:.2e} -> "
            f"{material.youngs_modulus:.2e}"
        ), material

    def ai_tune_global(self, aggression: float) -> Tuple[bool, str, int]:
        """AI-tune all bodies in the system based on their stress states.

        Iterates over all active bodies, assesses each, and adjusts material
        stiffness and damping. The aggression parameter controls how aggressively
        parameters are adjusted (0.0 = conservative, 1.0 = aggressive).

        Args:
            aggression: Tuning aggression factor (0.0 to 1.0).

        Returns:
            Tuple of (success, message, num_bodies_tuned).
        """
        aggression_clamped = _clamp(aggression, 0.0, 1.0)
        tuned = 0
        for body in self._bodies.values():
            if body.status in (BodyStatus.DESTROYED, BodyStatus.FRACTURED):
                continue
            ok, _, assessment = self.ai_assess_body(body.body_id)
            if not ok:
                continue
            material = self._get_material_for_body(body)
            if material is None:
                continue
            # Adjust stiffness toward recommended value with aggression scaling
            target = assessment.recommended_stiffness
            old_modulus = material.youngs_modulus
            rate = 0.3 + aggression_clamped * 0.4
            material.youngs_modulus = old_modulus + (target - old_modulus) * rate
            # Adjust damping
            material.damping_coefficient = _clamp(
                material.damping_coefficient +
                (assessment.recommended_damping - material.damping_coefficient) * rate,
                0.0, 1.0
            )
            tuned += 1
        if tuned > 0:
            self._emit(
                SoftBodyEventKind.MATERIAL_TUNED.value,
                {"action": "global_tune", "bodies_tuned": tuned,
                 "aggression": aggression_clamped},
            )
        return True, f"Global tuning applied to {tuned} bodies", tuned

    # ------------------------------------------------------------------
    # Volume Computation and Preservation
    # ------------------------------------------------------------------

    def compute_volume(self, body_id: str) -> Tuple[bool, str, float]:
        """Compute the current total volume of a body from its tetrahedra.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, volume).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", 0.0
        self._update_tetrahedra_volumes(body)
        total = sum(t.current_volume for t in body.tetrahedra)
        body.current_volume = total
        return True, f"Volume computed: {total:.6f}", total

    def preserve_volume(self, body_id: str) -> Tuple[bool, str, float]:
        """Apply volume correction to restore the body toward its rest volume.

        Computes the ratio of rest volume to current volume and scales vertex
        positions relative to the center of mass to correct volume drift. The
        correction strength depends on the material's volume preservation
        setting.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, correction_applied).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", 0.0
        if not self._config.enable_volume_preservation:
            return True, "Volume preservation disabled", 0.0
        material = self._get_material_for_body(body)
        if material is None:
            return False, f"Material not found for body '{bid}'", 0.0
        if material.volume_preservation == VolumePreservation.NONE:
            return True, "Material does not preserve volume", 0.0
        # Compute current volume
        ok, _, current_vol = self.compute_volume(bid)
        if not ok or current_vol < _EPSILON:
            return True, "Volume too small to correct", 0.0
        if body.rest_volume < _EPSILON:
            return True, "Rest volume is zero", 0.0
        # Determine correction strength based on preservation mode
        if material.volume_preservation == VolumePreservation.INCOMPRESSIBLE:
            strength = 1.0
        elif material.volume_preservation == VolumePreservation.NEAR_INCOMPRESSIBLE:
            strength = 0.5
        else:
            strength = 0.1
        # Volume ratio: scale = (rest/current)^(1/3) for 3D uniform scaling
        ratio = body.rest_volume / current_vol
        scale = ratio ** (1.0 / 3.0)
        # Blend toward target scale based on strength
        correction_scale = 1.0 + (scale - 1.0) * strength
        com = body.center_of_mass
        total_correction = 0.0
        for v in body.vertices.values():
            if v.pinned:
                continue
            # Scale position relative to center of mass
            offset = _vec_sub(v.position, com)
            new_offset = _vec_scale(offset, correction_scale)
            new_pos = _vec_add(com, new_offset)
            total_correction += _vec_distance(v.position, new_pos)
            v.position = new_pos
        # Update center of mass and bounding radius
        body.center_of_mass = self._compute_center_of_mass(body)
        body.bounding_radius = self._compute_bounding_radius(body)
        self._update_tetrahedra_volumes(body)
        body.current_volume = sum(t.current_volume for t in body.tetrahedra)
        return True, f"Volume corrected by {total_correction:.6f}", total_correction

    # ------------------------------------------------------------------
    # Reset and Inspection
    # ------------------------------------------------------------------

    def reset_deformation(self, body_id: str) -> Tuple[bool, str]:
        """Reset a body to its rest shape by restoring spring rest lengths.

        Reactivates all springs, resets vertex velocities, and clears
        accumulated deformation. The rest positions are not stored separately,
        so this restores spring rest lengths and clears forces rather than
        reverting vertex positions to an initial state.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found"
        # Reactivate all springs
        for spring in body.springs:
            spring.active = True
        # Reset vertex velocities and forces
        for v in body.vertices.values():
            v.velocity = (0.0, 0.0, 0.0)
            v.force_accumulator = (0.0, 0.0, 0.0)
        # Reset deformation tracking
        body.total_deformation = 0.0
        body.plastic_deformation = 0.0
        body.elastic_energy = 0.0
        body.damage_accumulated = 0.0
        body.status = BodyStatus.INTACT
        # Update tetrahedra volumes
        self._update_tetrahedra_volumes(body)
        body.current_volume = sum(t.current_volume for t in body.tetrahedra)
        # Remove associated tears and fractures
        tear_ids = [tid for tid, t in self._tears.items() if t.body_id == bid]
        for tid in tear_ids:
            del self._tears[tid]
        frac_ids = [fid for fid, f in self._fractures.items() if f.body_id == bid]
        for fid in frac_ids:
            del self._fractures[fid]
        self._emit(
            SoftBodyEventKind.DEFORMATION_APPLIED.value,
            {"body_id": bid, "action": "reset"},
            body_id=bid,
        )
        return True, f"Body '{bid}' deformation reset"

    def get_deformation_summary(
        self,
        body_id: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Get a summary of deformation state for a body.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, summary_dict).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", {}
        ok, _, strain_dict = self.compute_strain(bid)
        if not ok:
            strain_dict = {}
        active_springs = sum(1 for s in body.springs if s.active)
        severed_springs = len(body.springs) - active_springs
        summary: Dict[str, Any] = {
            "body_id": bid,
            "name": body.name,
            "status": body.status.value,
            "total_deformation": body.total_deformation,
            "plastic_deformation": body.plastic_deformation,
            "elastic_energy": body.elastic_energy,
            "damage_accumulated": body.damage_accumulated,
            "rest_volume": body.rest_volume,
            "current_volume": body.current_volume,
            "volume_ratio": (
                body.current_volume / body.rest_volume
                if body.rest_volume > _EPSILON else 1.0
            ),
            "total_springs": len(body.springs),
            "active_springs": active_springs,
            "severed_springs": severed_springs,
            "total_vertices": len(body.vertices),
            "total_tetrahedra": len(body.tetrahedra),
            "max_strain": max((abs(s) for s in strain_dict.values()), default=0.0),
            "avg_strain": (
                sum(abs(s) for s in strain_dict.values()) / len(strain_dict)
                if strain_dict else 0.0
            ),
            "tear_count": len(self.list_tears(bid)),
            "fracture_count": len(self.list_fractures(bid)),
        }
        return True, "Deformation summary generated", summary

    def get_stress_report(
        self,
        body_id: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Get a detailed stress report for a body.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, report_dict).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", {}
        ok, _, stress_dict = self.compute_stress(bid)
        if not ok:
            stress_dict = {}
        ok_s, _, strain_dict = self.compute_strain(bid)
        if not ok_s:
            strain_dict = {}
        material = self._get_material_for_body(body)
        stress_values = list(stress_dict.values())
        strain_values = [abs(s) for s in strain_dict.values()]
        report: Dict[str, Any] = {
            "body_id": bid,
            "material_id": body.material_id,
            "material_name": material.name if material else "",
            "yield_strength": material.yield_strength if material else 0.0,
            "ultimate_strength": material.ultimate_strength if material else 0.0,
            "stress_per_vertex": stress_dict,
            "strain_per_spring": strain_dict,
            "max_stress": max(stress_values) if stress_values else 0.0,
            "min_stress": min(stress_values) if stress_values else 0.0,
            "avg_stress": (
                sum(stress_values) / len(stress_values)
                if stress_values else 0.0
            ),
            "max_strain": max(strain_values) if strain_values else 0.0,
            "avg_strain": (
                sum(strain_values) / len(strain_values)
                if strain_values else 0.0
            ),
            "yield_ratio": (
                max(stress_values) / material.yield_strength
                if stress_values and material and material.yield_strength > 0
                else 0.0
            ),
            "high_stress_vertices": [
                vid for vid, s in stress_dict.items()
                if material and s > material.yield_strength * 0.7
            ],
        }
        return True, "Stress report generated", report

    def get_visualization_data(
        self,
        body_id: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Get visualization data for rendering a soft body.

        Returns vertex positions, spring connections, and tetrahedra in a
        format suitable for rendering pipelines.

        Args:
            body_id: Target body ID.

        Returns:
            Tuple of (success, message, viz_dict).
        """
        bid = str(body_id).strip()
        body = self._bodies.get(bid)
        if body is None:
            return False, f"Body '{bid}' not found", {}
        ok, _, stress_dict = self.compute_stress(bid)
        if not ok:
            stress_dict = {}
        vertex_data: List[Dict[str, Any]] = []
        for vid, v in body.vertices.items():
            vertex_data.append({
                "id": vid,
                "position": list(v.position),
                "velocity": list(v.velocity),
                "mass": v.mass,
                "pinned": v.pinned,
                "stress": stress_dict.get(vid, 0.0),
            })
        spring_data: List[Dict[str, Any]] = []
        for s in body.springs:
            spring_data.append({
                "id": s.id,
                "vertex_a": s.vertex_a_id,
                "vertex_b": s.vertex_b_id,
                "rest_length": s.rest_length,
                "active": s.active,
                "strain": self._compute_spring_strain(body, s),
            })
        tet_data: List[Dict[str, Any]] = []
        for t in body.tetrahedra:
            tet_data.append({
                "id": t.id,
                "vertex_ids": list(t.vertex_ids),
                "rest_volume": t.rest_volume,
                "current_volume": t.current_volume,
            })
        viz: Dict[str, Any] = {
            "body_id": bid,
            "name": body.name,
            "status": body.status.value,
            "center_of_mass": list(body.center_of_mass),
            "bounding_radius": body.bounding_radius,
            "vertices": vertex_data,
            "springs": spring_data,
            "tetrahedra": tet_data,
            "stress_range": [
                min(stress_dict.values()) if stress_dict else 0.0,
                max(stress_dict.values()) if stress_dict else 0.0,
            ],
        }
        return True, "Visualization data generated", viz

    # ------------------------------------------------------------------
    # System State and Configuration
    # ------------------------------------------------------------------

    def get_stats(self) -> SoftBodyStats:
        """Compute and return aggregate system statistics."""
        active = sum(
            1 for b in self._bodies.values()
            if b.status != BodyStatus.DESTROYED
        )
        destroyed = sum(
            1 for b in self._bodies.values()
            if b.status == BodyStatus.DESTROYED
        )
        # Compute average and peak stress across all bodies
        all_stresses: List[float] = []
        for body in self._bodies.values():
            ok, _, stress_dict = self.compute_stress(body.body_id)
            if ok and stress_dict:
                all_stresses.extend(stress_dict.values())
        avg_stress = (
            sum(all_stresses) / len(all_stresses)
            if all_stresses else 0.0
        )
        peak_stress = max(all_stresses) if all_stresses else 0.0
        return SoftBodyStats(
            total_bodies=len(self._bodies),
            active_bodies=active,
            destroyed_bodies=destroyed,
            total_deformations=self._total_deformations,
            total_tears=self._total_tears,
            total_fractures=self._total_fractures,
            total_plastic_flows=self._total_plastic_flows,
            average_stress=avg_stress,
            peak_stress=peak_stress,
            total_energy_dissipated=self._total_energy_dissipated,
            timestamp=_now(),
        )

    def get_snapshot(self) -> SoftBodySnapshot:
        """Return a point-in-time snapshot of system-wide counts."""
        total_v = sum(len(b.vertices) for b in self._bodies.values())
        total_t = sum(len(b.tetrahedra) for b in self._bodies.values())
        total_s = sum(len(b.springs) for b in self._bodies.values())
        return SoftBodySnapshot(
            tick_count=self._tick_count,
            active_bodies=len(self._bodies),
            total_vertices=total_v,
            total_tetrahedra=total_t,
            total_springs=total_s,
            total_deformations=self._total_deformations,
            timestamp=_now(),
        )

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary for the system."""
        return {
            "initialized": self._initialized,
            "seeded": self._seeded,
            "materials": len(self._materials),
            "bodies": len(self._bodies),
            "tears": len(self._tears),
            "fractures": len(self._fractures),
            "deformation_results": len(self._deformation_results),
            "events": len(self._events),
            "tick_count": self._tick_count,
            "global_time": self._global_time,
            "total_deformations": self._total_deformations,
            "total_energy_dissipated": self._total_energy_dissipated,
        }

    def get_config(self) -> SoftBodyConfig:
        """Return the current system configuration."""
        return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, SoftBodyConfig]:
        """Update system configuration with keyword arguments.

        Only known configuration fields are updated. Unknown keys are ignored
        with a warning message.

        Args:
            **kwargs: Configuration field names and new values.

        Returns:
            Tuple of (success, message, updated_config).
        """
        known_fields = {
            "max_bodies", "max_vertices_per_body", "solver_method",
            "solver_iterations", "global_gravity", "global_damping",
            "enable_tearing", "enable_fracture", "enable_plastic_flow",
            "enable_volume_preservation", "ai_tuning_frequency",
            "stress_threshold_warning",
        }
        updated: List[str] = []
        ignored: List[str] = []
        for key, value in kwargs.items():
            if key not in known_fields:
                ignored.append(key)
                continue
            if key == "solver_method":
                try:
                    value = SolverMethod(value)
                except (ValueError, KeyError):
                    return False, f"Invalid solver_method '{value}'", self._config
            elif key == "global_gravity":
                if not isinstance(value, (list, tuple)) or len(value) != 3:
                    return False, "global_gravity must be a 3-tuple", self._config
                value = tuple(float(v) for v in value)
            elif key in ("max_bodies", "max_vertices_per_body",
                         "solver_iterations", "ai_tuning_frequency"):
                value = _safe_int(value, getattr(self._config, key))
            elif key in ("global_damping", "stress_threshold_warning"):
                value = _safe_float(value, getattr(self._config, key))
            elif key in ("enable_tearing", "enable_fracture",
                         "enable_plastic_flow", "enable_volume_preservation"):
                value = bool(value)
            setattr(self._config, key, value)
            updated.append(key)
        msg = f"Updated: {', '.join(updated)}" if updated else "No fields updated"
        if ignored:
            msg += f"; Ignored: {', '.join(ignored)}"
        return True, msg, self._config

    def list_events(
        self,
        kind: Optional[str] = None,
        limit: int = 100,
    ) -> List[SoftBodyEvent]:
        """List events, optionally filtered by kind.

        Args:
            kind: Optional event kind string (see SoftBodyEventKind values).
                If None, all events are returned.
            limit: Maximum number of events to return (most recent first).

        Returns:
            List of SoftBodyEvent instances.
        """
        if kind is not None:
            filtered = [e for e in self._events if e.kind == kind]
        else:
            filtered = list(self._events)
        # Return most recent first, up to limit
        filtered.reverse()
        limit_clamped = max(0, _safe_int(limit, 100))
        return filtered[:limit_clamped]

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def tick(self, dt: float) -> Dict[str, Any]:
        """Advance the simulation by one time step.

        The tick performs the following steps for each active body:
          1. Clear force accumulators and apply gravity.
          2. Compute and apply spring forces.
          3. Integrate vertex positions and velocities.
          4. Check for yield (springs exceeding yield point).
          5. Apply plastic flow to yielded springs.
          6. Check for tear initiation.
          7. Propagate existing tears.
          8. Check for fracture.
          9. Preserve volume.

        Args:
            dt: Time step in seconds.

        Returns:
            Dictionary with tick summary statistics.
        """
        dt_clamped = max(0.0, _safe_float(dt, 0.016))
        self._tick_count += 1
        self._global_time += dt_clamped
        bodies_processed = 0
        yields_detected = 0
        tears_initiated = 0
        tears_propagated = 0
        fractures_detected = 0
        plastic_flows = 0
        volume_corrections = 0

        for body in list(self._bodies.values()):
            if body.status == BodyStatus.DESTROYED:
                continue
            bodies_processed += 1

            # Step 1: Clear forces and apply gravity
            self._clear_forces(body)
            self._apply_gravity(body)

            # Step 2: Apply spring forces and compute elastic energy
            body.elastic_energy = self._apply_spring_forces(body)

            # Step 3: Integrate positions and velocities
            for _ in range(self._config.solver_iterations):
                self._integrate(body, dt_clamped / max(self._config.solver_iterations, 1))

            # Step 4: Check yield
            ok_y, _, yielded = self.check_yield(body.body_id)
            if ok_y:
                yields_detected += len(yielded)

            # Step 5: Apply plastic flow
            if self._config.enable_plastic_flow:
                ok_p, _, converted = self.apply_plastic_flow(body.body_id, dt_clamped)
                if ok_p:
                    plastic_flows += converted

            # Step 6: Check for tear initiation
            if self._config.enable_tearing:
                ok_t, _, tear = self.check_tear(body.body_id)
                if ok_t and tear is not None:
                    tears_initiated += 1

            # Step 7: Propagate existing tears
            if self._config.enable_tearing:
                body_tears = self.list_tears(body.body_id)
                for tear in body_tears:
                    if tear.mode in (TearMode.INITIATED, TearMode.PROPAGATING):
                        ok_tp, _, _ = self.propagate_tear(body.body_id, tear.tear_id)
                        if ok_tp:
                            tears_propagated += 1

            # Step 8: Check for fracture
            if self._config.enable_fracture:
                ok_f, _, fracture = self.check_fracture(body.body_id)
                if ok_f and fracture is not None:
                    fractures_detected += 1

            # Step 9: Preserve volume
            if self._config.enable_volume_preservation:
                ok_v, _, correction = self.preserve_volume(body.body_id)
                if ok_v and correction > _EPSILON:
                    volume_corrections += 1

            # Update body status if destroyed
            if body.status == BodyStatus.FRACTURED:
                # Check if body should be destroyed (all springs severed)
                active_springs = sum(1 for s in body.springs if s.active)
                if active_springs == 0 and len(body.springs) > 0:
                    body.status = BodyStatus.DESTROYED
                    self._emit(
                        SoftBodyEventKind.BODY_DESTROYED.value,
                        {"body_id": body.body_id},
                        body_id=body.body_id,
                    )

            # Update center of mass and bounding radius
            body.center_of_mass = self._compute_center_of_mass(body)
            body.bounding_radius = self._compute_bounding_radius(body)

        # Periodic AI tuning
        if (self._config.ai_tuning_frequency > 0 and
                self._tick_count % self._config.ai_tuning_frequency == 0):
            self.ai_tune_global(0.3)

        return {
            "tick": self._tick_count,
            "dt": dt_clamped,
            "bodies_processed": bodies_processed,
            "yields_detected": yields_detected,
            "tears_initiated": tears_initiated,
            "tears_propagated": tears_propagated,
            "fractures_detected": fractures_detected,
            "plastic_flows": plastic_flows,
            "volume_corrections": volume_corrections,
            "total_deformations": self._total_deformations,
            "global_time": self._global_time,
        }


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_soft_body_deformation_system() -> SoftBodyDeformationSystem:
    """Return the singleton SoftBodyDeformationSystem instance, seeding on first use.

    This is the primary entry point for consumers of the soft body deformation
    system. It ensures the singleton is created and seed data is loaded before
    returning the instance.
    """
    inst = SoftBodyDeformationSystem.get_instance()
    if not getattr(inst, "_seeded", False):
        inst.initialize()
    return inst
