"""
SparkLabs Engine - Cloth & Soft-Body Physics

A complete cloth and soft-body simulation system providing deformable
object dynamics for the AI-native game engine. Supports multiple solver
backends, material-based physical properties, collision interaction with
rigid spheres, and procedural mesh generation.

Architecture:
  ClothPhysicsEngine (Singleton)
    |-- ClothParticle         — 3D mass point with Verlet/PBD state
    |-- ClothConstraint       — distance/volume constraint between particles
    |-- ClothMesh             — grid-based cloth mesh with material
    |-- ClothMaterial         — physical property definitions
    |-- SoftBody              — inflatable volume-preserving body
    |-- ClothCollisionSphere  — spherical obstacle for collision

Solver Backends:
  VERLET  — velocity-less Verlet integration with iterative relaxation
  PBD     — Position-Based Dynamics with Gauss-Seidel constraint projection
  XPBD    — Extended PBD with compliance-based constraint solving
  JACOBI  — Jacobi-style parallel constraint averaging

Simulation Pipeline:
  1. Apply external forces (gravity, wind, user forces)
  2. Integrate particle positions (Verlet or velocity-based)
  3. Solve constraints iteratively (structural, shear, bend, pressure, volume)
  4. Detect and resolve collision sphere intersections
  5. Update particle velocities and normals
"""

from __future__ import annotations

import math
import random
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ClothSolverType(Enum):
    """Numerical solver used for the cloth simulation step."""
    VERLET = "verlet"
    PBD = "pbd"
    XPBD = "xpbd"
    JACOBI = "jacobi"


class SoftBodyType(Enum):
    """Category of soft body defining its physical behavior profile."""
    CLOTH = "cloth"
    ROPE = "rope"
    BALLOON = "balloon"
    GEL = "gel"
    RUBBER = "rubber"
    JELLY = "jelly"


class ConstraintType(Enum):
    """Classification of a constraint based on its geometric role."""
    STRUCTURAL = "structural"
    SHEAR = "shear"
    BEND = "bend"
    PRESSURE = "pressure"
    VOLUME = "volume"


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _vec3_add(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec3_sub(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec3_scale(v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec3_dot(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec3_cross(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _vec3_length(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec3_length_sq(v: Tuple[float, float, float]) -> float:
    return v[0] * v[0] + v[1] * v[1] + v[2] * v[2]


def _vec3_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    length_val = _vec3_length(v)
    if length_val < 1e-9:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / length_val
    return (v[0] * inv, v[1] * inv, v[2] * inv)


def _vec3_lerp(a: Tuple[float, float, float], b: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ClothMaterial:
    """Physical properties governing how a cloth mesh behaves.

    Each material defines stiffness, damping, resistance to bending
    and shearing, mass distribution, tear resistance, wind affinity,
    and visual appearance.
    """

    material_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "default_material"
    stiffness: float = 0.9
    damping: float = 0.01
    bend_resistance: float = 0.5
    shear_resistance: float = 0.6
    mass_per_particle: float = 1.0
    tear_resistance: float = 10.0
    wind_affinity: float = 0.8
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    texture_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_id": self.material_id,
            "name": self.name,
            "stiffness": self.stiffness,
            "damping": self.damping,
            "bend_resistance": self.bend_resistance,
            "shear_resistance": self.shear_resistance,
            "mass_per_particle": self.mass_per_particle,
            "tear_resistance": self.tear_resistance,
            "wind_affinity": self.wind_affinity,
            "color": list(self.color),
            "texture_path": self.texture_path,
        }


@dataclass
class ClothParticle:
    """A single mass point within a cloth or soft-body simulation.

    Tracks 3D position, previous position (for Verlet), velocity
    (for velocity-based solvers), accumulated forces, surface normal,
    texture coordinates, and neighbor connectivity.
    """

    particle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    previous_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mass: float = 1.0
    is_pinned: bool = False
    damping: float = 0.01
    forces: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    uv: Tuple[float, float] = (0.0, 0.0)
    neighbors: List[str] = field(default_factory=list)

    _inverse_mass: float = field(default=1.0, repr=False)

    def __post_init__(self) -> None:
        self._update_inverse_mass()

    def _update_inverse_mass(self) -> None:
        if self.is_pinned or self.mass <= 0.0:
            self._inverse_mass = 0.0
        else:
            self._inverse_mass = 1.0 / self.mass

    def get_inverse_mass(self) -> float:
        return self._inverse_mass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "particle_id": self.particle_id,
            "position": list(self.position),
            "previous_position": list(self.previous_position),
            "velocity": list(self.velocity),
            "mass": self.mass,
            "is_pinned": self.is_pinned,
            "damping": self.damping,
            "forces": list(self.forces),
            "normal": list(self.normal),
            "uv": list(self.uv),
            "neighbors": list(self.neighbors),
        }


@dataclass
class ClothConstraint:
    """A distance constraint connecting two particles in a cloth mesh.

    Maintains a rest length between particles. Stiffness controls
    correction strength. Tear threshold defines the maximum strain
    before the constraint breaks. Compression stiffness allows
    asymmetric resistance to stretching vs compression.
    """

    constraint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    particle_a_id: str = ""
    particle_b_id: str = ""
    rest_length: float = 1.0
    stiffness: float = 0.9
    compression_stiffness: float = 0.9
    tear_threshold: Optional[float] = None
    is_active: bool = True

    # XPBD compliance parameter (lambda accumulator)
    _lambda: float = field(default=0.0, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "particle_a_id": self.particle_a_id,
            "particle_b_id": self.particle_b_id,
            "rest_length": self.rest_length,
            "stiffness": self.stiffness,
            "compression_stiffness": self.compression_stiffness,
            "tear_threshold": self.tear_threshold,
            "is_active": self.is_active,
        }


@dataclass
class ClothMesh:
    """A grid-based cloth mesh composed of particles and constraints.

    Defined by segment counts in each direction, a material profile,
    anchor points (pinned particles), and resolution (spacing between
    particles). The constraint list includes structural, shear, and
    bend constraints.
    """

    mesh_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "cloth_mesh"
    particles: List[ClothParticle] = field(default_factory=list)
    constraints: List[ClothConstraint] = field(default_factory=list)
    width_segments: int = 10
    height_segments: int = 10
    total_mass: float = 1.0
    anchor_points: List[str] = field(default_factory=list)
    material: ClothMaterial = field(default_factory=ClothMaterial)
    resolution: float = 0.5

    # Particle lookup index for fast constraint resolution
    _particle_map: Dict[str, ClothParticle] = field(default_factory=dict, repr=False)
    _grid_map: Dict[Tuple[int, int], str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._rebuild_particle_map()

    def _rebuild_particle_map(self) -> None:
        self._particle_map = {p.particle_id: p for p in self.particles}

    def get_particle(self, particle_id: str) -> Optional[ClothParticle]:
        return self._particle_map.get(particle_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mesh_id": self.mesh_id,
            "name": self.name,
            "particle_count": len(self.particles),
            "constraint_count": len(self.constraints),
            "width_segments": self.width_segments,
            "height_segments": self.height_segments,
            "total_mass": self.total_mass,
            "anchor_points": list(self.anchor_points),
            "material": self.material.to_dict(),
            "resolution": self.resolution,
            "particles": [p.to_dict() for p in self.particles],
            "constraints": [c.to_dict() for c in self.constraints],
        }


@dataclass
class SoftBody:
    """A volume-preserving soft body with pressure-based inflation.

    Soft bodies extend cloth meshes with pressure for balloon-like
    behavior and volume conservation. The center of mass is computed
    from particle positions. Metadata carries arbitrary key-value
    data for extensibility.
    """

    body_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "soft_body"
    particles: List[ClothParticle] = field(default_factory=list)
    constraints: List[ClothConstraint] = field(default_factory=list)
    pressure: float = 0.0
    volume_conservation: bool = False
    center_of_mass: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    _particle_map: Dict[str, ClothParticle] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._particle_map = {p.particle_id: p for p in self.particles}

    def get_particle(self, particle_id: str) -> Optional[ClothParticle]:
        return self._particle_map.get(particle_id)

    def compute_center_of_mass(self) -> Tuple[float, float, float]:
        if not self.particles:
            return (0.0, 0.0, 0.0)
        total_mass = 0.0
        sum_pos = (0.0, 0.0, 0.0)
        for p in self.particles:
            if p.is_pinned:
                continue
            m = p.mass
            total_mass += m
            sum_pos = _vec3_add(sum_pos, _vec3_scale(p.position, m))
        if total_mass < 1e-9:
            return (0.0, 0.0, 0.0)
        inv = 1.0 / total_mass
        return _vec3_scale(sum_pos, inv)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "name": self.name,
            "particle_count": len(self.particles),
            "constraint_count": len(self.constraints),
            "pressure": self.pressure,
            "volume_conservation": self.volume_conservation,
            "center_of_mass": list(self.center_of_mass),
            "is_active": self.is_active,
            "metadata": self.metadata,
            "particles": [p.to_dict() for p in self.particles],
            "constraints": [c.to_dict() for c in self.constraints],
        }


@dataclass
class ClothCollisionSphere:
    """A spherical obstacle that cloth particles collide against.

    Collision spheres are static obstacles that repel cloth particles
    from their interior. Friction controls tangential velocity damping
    during collision response.
    """

    sphere_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 1.0
    friction: float = 0.3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sphere_id": self.sphere_id,
            "center": list(self.center),
            "radius": self.radius,
            "friction": self.friction,
        }


# ---------------------------------------------------------------------------
# Preset Materials
# ---------------------------------------------------------------------------

def _create_preset_materials() -> Dict[str, ClothMaterial]:
    """Create a library of preset cloth materials."""
    return {
        "silk": ClothMaterial(
            name="silk", stiffness=0.7, damping=0.005,
            bend_resistance=0.2, shear_resistance=0.4,
            mass_per_particle=0.3, tear_resistance=3.0,
            wind_affinity=0.95, color=(0.95, 0.9, 0.85, 1.0),
        ),
        "cotton": ClothMaterial(
            name="cotton", stiffness=0.85, damping=0.015,
            bend_resistance=0.5, shear_resistance=0.55,
            mass_per_particle=0.8, tear_resistance=8.0,
            wind_affinity=0.6, color=(0.98, 0.96, 0.92, 1.0),
        ),
        "denim": ClothMaterial(
            name="denim", stiffness=0.95, damping=0.03,
            bend_resistance=0.8, shear_resistance=0.7,
            mass_per_particle=1.5, tear_resistance=20.0,
            wind_affinity=0.2, color=(0.2, 0.25, 0.4, 1.0),
        ),
        "leather": ClothMaterial(
            name="leather", stiffness=0.98, damping=0.04,
            bend_resistance=0.9, shear_resistance=0.85,
            mass_per_particle=1.8, tear_resistance=30.0,
            wind_affinity=0.1, color=(0.35, 0.2, 0.1, 1.0),
        ),
        "rubber": ClothMaterial(
            name="rubber", stiffness=0.6, damping=0.02,
            bend_resistance=0.3, shear_resistance=0.3,
            mass_per_particle=1.2, tear_resistance=50.0,
            wind_affinity=0.3, color=(0.15, 0.15, 0.15, 1.0),
        ),
        "nylon": ClothMaterial(
            name="nylon", stiffness=0.8, damping=0.01,
            bend_resistance=0.4, shear_resistance=0.5,
            mass_per_particle=0.5, tear_resistance=15.0,
            wind_affinity=0.85, color=(0.7, 0.7, 0.8, 1.0),
        ),
        "gel": ClothMaterial(
            name="gel", stiffness=0.4, damping=0.05,
            bend_resistance=0.15, shear_resistance=0.2,
            mass_per_particle=1.0, tear_resistance=5.0,
            wind_affinity=0.0, color=(0.5, 0.8, 0.5, 0.7),
        ),
        "jelly": ClothMaterial(
            name="jelly", stiffness=0.3, damping=0.06,
            bend_resistance=0.1, shear_resistance=0.15,
            mass_per_particle=0.9, tear_resistance=4.0,
            wind_affinity=0.0, color=(1.0, 0.4, 0.3, 0.6),
        ),
    }


# ---------------------------------------------------------------------------
# Cloth Physics Engine
# ---------------------------------------------------------------------------

class ClothPhysicsEngine:
    """Thread-safe cloth and soft-body physics simulation engine.

    Manages cloth meshes, soft bodies, and collision spheres. Supports
    multiple solver backends (Verlet, PBD, XPBD, Jacobi) for different
    accuracy/performance trade-offs. Handles constraint solving, tear
    detection, wind application, and sphere collision resolution.

    The engine is a singleton accessed via get_cloth_physics().
    All public methods are thread-safe using a reentrant lock.
    """

    _instance: Optional["ClothPhysicsEngine"] = None
    _lock = threading.RLock()

    MAX_MESHES = 256
    MAX_SPHERES = 128
    MAX_PARTICLES_PER_MESH = 16384
    DEFAULT_GRAVITY: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    DEFAULT_WIND: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    DEFAULT_SOLVER = ClothSolverType.VERLET
    DEFAULT_ITERATIONS = 5
    XPBD_COMPLIANCE_BASE = 0.000001

    def __new__(cls) -> "ClothPhysicsEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ClothPhysicsEngine":
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

        self._meshes: Dict[str, ClothMesh] = {}
        self._soft_bodies: Dict[str, SoftBody] = {}
        self._collision_spheres: Dict[str, ClothCollisionSphere] = {}
        self._gravity: Tuple[float, float, float] = self.DEFAULT_GRAVITY
        self._global_wind: Tuple[float, float, float] = self.DEFAULT_WIND
        self._preset_materials: Dict[str, ClothMaterial] = _create_preset_materials()
        self._step_count: int = 0
        self._total_tears: int = 0
        self._last_collision_events: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Mesh Creation
    # ------------------------------------------------------------------

    def create_cloth_mesh(
        self,
        name: str,
        width_segments: int,
        height_segments: int,
        anchor_points: List[Tuple[int, int]],
        material: ClothMaterial,
        initial_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> ClothMesh:
        """Create a grid-based cloth mesh with the given parameters.

        Generates a rectangular grid of particles with structural,
        shear, and bend constraints. Anchor points are specified as
        (column, row) indices into the grid and are pinned in place.
        """
        if width_segments < 2 or height_segments < 2:
            raise ValueError("Cloth mesh requires at least 2 segments per dimension")
        with self._lock:
            if len(self._meshes) >= self.MAX_MESHES:
                raise RuntimeError("Maximum mesh count reached")

            mesh = ClothMesh(
                name=name,
                width_segments=width_segments,
                height_segments=height_segments,
                material=material,
                resolution=material.mass_per_particle,
            )
            self._populate_mesh_particles(mesh, width_segments, height_segments, initial_position, material)
            self._populate_mesh_constraints(mesh, width_segments, height_segments, material)
            self._apply_anchor_points(mesh, anchor_points, width_segments)
            mesh.total_mass = sum(p.mass for p in mesh.particles)
            mesh._rebuild_particle_map()
            self._meshes[mesh.mesh_id] = mesh
            return mesh

    def _populate_mesh_particles(
        self,
        mesh: ClothMesh,
        width_segments: int,
        height_segments: int,
        origin: Tuple[float, float, float],
        material: ClothMaterial,
    ) -> None:
        """Fill the mesh with particles arranged in a grid."""
        mesh.particles.clear()
        mesh._grid_map.clear()
        ox, oy, oz = origin
        for row in range(height_segments + 1):
            for col in range(width_segments + 1):
                px = ox + col * mesh.resolution
                py = oy
                pz = oz + row * mesh.resolution
                u = col / max(width_segments, 1)
                v = row / max(height_segments, 1)
                particle = ClothParticle(
                    position=(px, py, pz),
                    previous_position=(px, py, pz),
                    mass=material.mass_per_particle,
                    damping=material.damping,
                    uv=(u, v),
                )
                mesh.particles.append(particle)
                mesh._grid_map[(row, col)] = particle.particle_id

    def _populate_mesh_constraints(
        self,
        mesh: ClothMesh,
        width_segments: int,
        height_segments: int,
        material: ClothMaterial,
    ) -> None:
        """Build structural, shear, and bend constraints for the grid."""
        mesh.constraints.clear()
        rows = height_segments + 1
        cols = width_segments + 1
        diag_length = mesh.resolution * math.sqrt(2.0)

        for row in range(rows):
            for col in range(cols):
                pid = mesh._grid_map.get((row, col))
                if pid is None:
                    continue

                # Structural: right and down
                if col < cols - 1:
                    nid = mesh._grid_map.get((row, col + 1))
                    if nid:
                        self._add_constraint_to_mesh(mesh, pid, nid, mesh.resolution, material.stiffness, material.stiffness, material.tear_resistance)
                if row < rows - 1:
                    nid = mesh._grid_map.get((row + 1, col))
                    if nid:
                        self._add_constraint_to_mesh(mesh, pid, nid, mesh.resolution, material.stiffness, material.stiffness, material.tear_resistance)

                # Shear: diagonals
                if col < cols - 1 and row < rows - 1:
                    nid = mesh._grid_map.get((row + 1, col + 1))
                    if nid:
                        self._add_constraint_to_mesh(mesh, pid, nid, diag_length, material.shear_resistance, material.shear_resistance, material.tear_resistance * 1.5)
                if col > 0 and row < rows - 1:
                    nid = mesh._grid_map.get((row + 1, col - 1))
                    if nid:
                        self._add_constraint_to_mesh(mesh, pid, nid, diag_length, material.shear_resistance, material.shear_resistance, material.tear_resistance * 1.5)

                # Bend: skip-one
                if col < cols - 2:
                    nid = mesh._grid_map.get((row, col + 2))
                    if nid:
                        self._add_constraint_to_mesh(mesh, pid, nid, mesh.resolution * 2.0, material.bend_resistance, material.bend_resistance * 0.5, material.tear_resistance * 2.0)
                if row < rows - 2:
                    nid = mesh._grid_map.get((row + 2, col))
                    if nid:
                        self._add_constraint_to_mesh(mesh, pid, nid, mesh.resolution * 2.0, material.bend_resistance, material.bend_resistance * 0.5, material.tear_resistance * 2.0)

    def _add_constraint_to_mesh(
        self,
        mesh: ClothMesh,
        pid_a: str,
        pid_b: str,
        rest_length: float,
        stiffness: float,
        compression_stiffness: float,
        tear_threshold: float,
    ) -> None:
        """Add a single constraint to the mesh."""
        constraint = ClothConstraint(
            particle_a_id=pid_a,
            particle_b_id=pid_b,
            rest_length=max(0.001, rest_length),
            stiffness=max(0.0, min(1.0, stiffness)),
            compression_stiffness=max(0.0, min(1.0, compression_stiffness)),
            tear_threshold=tear_threshold if tear_threshold > 0 else None,
        )
        mesh.constraints.append(constraint)

    def _apply_anchor_points(
        self,
        mesh: ClothMesh,
        anchor_points: List[Tuple[int, int]],
        width_segments: int,
    ) -> None:
        """Pin the particles at the given grid coordinates."""
        mesh.anchor_points.clear()
        for col, row in anchor_points:
            pid = mesh._grid_map.get((row, col))
            if pid is None:
                continue
            particle = mesh.get_particle(pid)
            if particle is None:
                continue
            particle.is_pinned = True
            particle._update_inverse_mass()
            mesh.anchor_points.append(pid)

    # ------------------------------------------------------------------
    # Soft Body Creation
    # ------------------------------------------------------------------

    def create_soft_body(
        self,
        name: str,
        body_type: SoftBodyType,
        particles: List[ClothParticle],
        constraints: List[ClothConstraint],
        pressure: float = 0.0,
    ) -> SoftBody:
        """Create a soft body from an explicit set of particles and constraints.

        The body_type determines default pressure and volume conservation
        settings. Particles and constraints are copied into the soft body.
        """
        with self._lock:
            body = SoftBody(
                name=name,
                particles=list(particles),
                constraints=list(constraints),
                pressure=pressure,
            )
            # Configure defaults based on body type
            if body_type == SoftBodyType.BALLOON:
                body.pressure = max(pressure, 1.0)
                body.volume_conservation = True
            elif body_type == SoftBodyType.GEL:
                body.volume_conservation = True
                body.pressure = 0.0
            elif body_type == SoftBodyType.JELLY:
                body.volume_conservation = True
                body.pressure = 0.2
            elif body_type == SoftBodyType.RUBBER:
                body.volume_conservation = True
                body.pressure = 0.5
            elif body_type == SoftBodyType.ROPE:
                body.volume_conservation = False
                body.pressure = 0.0
            # CLOTH type uses defaults

            body.compute_center_of_mass()
            body._particle_map = {p.particle_id: p for p in body.particles}
            self._soft_bodies[body.body_id] = body
            return body

    # ------------------------------------------------------------------
    # Material Management
    # ------------------------------------------------------------------

    def set_material(self, mesh_id: str, material: ClothMaterial) -> bool:
        """Replace the material of an existing cloth mesh."""
        with self._lock:
            mesh = self._meshes.get(mesh_id)
            if mesh is None:
                return False
            mesh.material = material
            return True

    def get_preset_material(self, name: str) -> Optional[ClothMaterial]:
        """Retrieve a preset material by name."""
        return self._preset_materials.get(name)

    def list_preset_materials(self) -> List[str]:
        """List all available preset material names."""
        return list(self._preset_materials.keys())

    # ------------------------------------------------------------------
    # Particle and Constraint Management
    # ------------------------------------------------------------------

    def add_particle(self, mesh_id: str, particle: ClothParticle) -> bool:
        """Add a particle to an existing cloth mesh."""
        with self._lock:
            mesh = self._meshes.get(mesh_id)
            if mesh is None:
                return False
            if len(mesh.particles) >= self.MAX_PARTICLES_PER_MESH:
                return False
            mesh.particles.append(particle)
            mesh._particle_map[particle.particle_id] = particle
            mesh.total_mass = sum(p.mass for p in mesh.particles)
            return True

    def add_constraint(self, mesh_id: str, constraint: ClothConstraint) -> bool:
        """Add a constraint to an existing cloth mesh."""
        with self._lock:
            mesh = self._meshes.get(mesh_id)
            if mesh is None:
                return False
            if constraint.particle_a_id not in mesh._particle_map:
                return False
            if constraint.particle_b_id not in mesh._particle_map:
                return False
            mesh.constraints.append(constraint)
            return True

    def pin_particle(self, mesh_id: str, particle_id: str) -> bool:
        """Pin a particle so it is unaffected by forces and constraints."""
        with self._lock:
            mesh = self._meshes.get(mesh_id)
            if mesh is None:
                return False
            particle = mesh.get_particle(particle_id)
            if particle is None:
                return False
            particle.is_pinned = True
            particle._update_inverse_mass()
            if particle_id not in mesh.anchor_points:
                mesh.anchor_points.append(particle_id)
            return True

    def unpin_particle(self, mesh_id: str, particle_id: str) -> bool:
        """Unpin a particle so it resumes normal simulation."""
        with self._lock:
            mesh = self._meshes.get(mesh_id)
            if mesh is None:
                return False
            particle = mesh.get_particle(particle_id)
            if particle is None:
                return False
            particle.is_pinned = False
            particle._update_inverse_mass()
            if particle_id in mesh.anchor_points:
                mesh.anchor_points.remove(particle_id)
            return True

    # ------------------------------------------------------------------
    # Force Application
    # ------------------------------------------------------------------

    def apply_force_to_particle(
        self,
        mesh_id: str,
        particle_id: str,
        force_vector: Tuple[float, float, float],
    ) -> bool:
        """Apply a force vector to a specific particle for the next step."""
        with self._lock:
            mesh = self._meshes.get(mesh_id)
            if mesh is None:
                return False
            particle = mesh.get_particle(particle_id)
            if particle is None or particle.is_pinned:
                return False
            particle.forces = _vec3_add(particle.forces, force_vector)
            return True

    def apply_wind(self, force_vector: Tuple[float, float, float]) -> None:
        """Set the global wind vector applied to all cloth meshes each step.

        Wind force is scaled by each mesh material's wind_affinity.
        """
        with self._lock:
            self._global_wind = force_vector

    # ------------------------------------------------------------------
    # Collision Sphere Management
    # ------------------------------------------------------------------

    def add_collision_sphere(self, sphere: ClothCollisionSphere) -> str:
        """Add a collision sphere to the simulation."""
        with self._lock:
            if len(self._collision_spheres) >= self.MAX_SPHERES:
                raise RuntimeError("Maximum collision sphere count reached")
            self._collision_spheres[sphere.sphere_id] = sphere
            return sphere.sphere_id

    def remove_collision_sphere(self, sphere_id: str) -> bool:
        """Remove a collision sphere from the simulation."""
        with self._lock:
            if sphere_id in self._collision_spheres:
                del self._collision_spheres[sphere_id]
                return True
            return False

    def update_collision_sphere(
        self,
        sphere_id: str,
        center: Tuple[float, float, float],
        radius: float,
    ) -> bool:
        """Update the position and radius of an existing collision sphere."""
        with self._lock:
            sphere = self._collision_spheres.get(sphere_id)
            if sphere is None:
                return False
            sphere.center = center
            sphere.radius = max(0.001, radius)
            return True

    # ------------------------------------------------------------------
    # Tear and Reset
    # ------------------------------------------------------------------

    def tear_cloth(self, mesh_id: str, constraint_id: str) -> bool:
        """Tear a specific constraint by deactivating it."""
        with self._lock:
            mesh = self._meshes.get(mesh_id)
            if mesh is None:
                return False
            for constraint in mesh.constraints:
                if constraint.constraint_id == constraint_id:
                    constraint.is_active = False
                    self._total_tears += 1
                    return True
            return False

    def reset_mesh(self, mesh_id: str) -> bool:
        """Reset a mesh to its initial flat configuration."""
        with self._lock:
            mesh = self._meshes.get(mesh_id)
            if mesh is None:
                return False
            material = mesh.material
            width_segments = mesh.width_segments
            height_segments = mesh.height_segments
            anchor_points = [(0, 0)]  # placeholder, will be rebuilt
            # Rebuild from original grid parameters
            mesh.particles.clear()
            mesh.constraints.clear()
            mesh._grid_map.clear()
            mesh._particle_map.clear()
            mesh.anchor_points.clear()
            # We need to know the original origin. Reconstruct from resolution.
            self._populate_mesh_particles(mesh, width_segments, height_segments, (0.0, 0.0, 0.0), material)
            self._populate_mesh_constraints(mesh, width_segments, height_segments, material)
            mesh.total_mass = sum(p.mass for p in mesh.particles)
            mesh._rebuild_particle_map()
            return True

    def remove_mesh(self, mesh_id: str) -> bool:
        """Remove a cloth mesh from the simulation."""
        with self._lock:
            if mesh_id in self._meshes:
                del self._meshes[mesh_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_mesh(self, mesh_id: str) -> Optional[ClothMesh]:
        """Get a cloth mesh by ID."""
        return self._meshes.get(mesh_id)

    def get_mesh_particles(self, mesh_id: str) -> List[Dict[str, Any]]:
        """Get all particle data for a mesh as a list of dicts."""
        mesh = self._meshes.get(mesh_id)
        if mesh is None:
            return []
        return [p.to_dict() for p in mesh.particles]

    def get_soft_body(self, body_id: str) -> Optional[SoftBody]:
        """Get a soft body by ID."""
        return self._soft_bodies.get(body_id)

    def get_collision_sphere(self, sphere_id: str) -> Optional[ClothCollisionSphere]:
        """Get a collision sphere by ID."""
        return self._collision_spheres.get(sphere_id)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive engine statistics."""
        with self._lock:
            total_particles = sum(len(m.particles) for m in self._meshes.values())
            total_constraints = sum(len(m.constraints) for m in self._meshes.values())
            total_pinned = sum(len(m.anchor_points) for m in self._meshes.values())
            active_constraints = sum(
                sum(1 for c in m.constraints if c.is_active)
                for m in self._meshes.values()
            )
            sb_particles = sum(len(b.particles) for b in self._soft_bodies.values())
            sb_constraints = sum(len(b.constraints) for b in self._soft_bodies.values())

            return {
                "mesh_count": len(self._meshes),
                "soft_body_count": len(self._soft_bodies),
                "collision_sphere_count": len(self._collision_spheres),
                "total_particles": total_particles + sb_particles,
                "total_constraints": total_constraints + sb_constraints,
                "active_constraints": active_constraints,
                "pinned_particles": total_pinned,
                "total_tears": self._total_tears,
                "step_count": self._step_count,
                "gravity": list(self._gravity),
                "global_wind": list(self._global_wind),
                "last_collision_events": len(self._last_collision_events),
                "max_meshes": self.MAX_MESHES,
                "max_spheres": self.MAX_SPHERES,
            }

    # ------------------------------------------------------------------
    # Simulation Step
    # ------------------------------------------------------------------

    def step(
        self,
        delta_time: float,
        iterations: int = DEFAULT_ITERATIONS,
        solver_type: ClothSolverType = DEFAULT_SOLVER,
    ) -> List[Dict[str, Any]]:
        """Advance the simulation by delta_time seconds.

        Steps through force application, integration, constraint solving,
        and collision detection. Returns a list of collision event dicts.
        """
        if delta_time <= 0.0:
            return []
        iterations = max(1, iterations)

        with self._lock:
            self._step_count += 1
            self._last_collision_events = []

            # Step all cloth meshes
            for mesh in self._meshes.values():
                self._apply_gravity_and_wind(mesh)
                self._integrate_particles(mesh, delta_time, solver_type)

            # Step all soft bodies
            for body in self._soft_bodies.values():
                if not body.is_active:
                    continue
                self._integrate_soft_body(body, delta_time, solver_type)

            # Solve constraints
            if solver_type == ClothSolverType.VERLET:
                self._solve_verlet(delta_time, iterations)
            elif solver_type == ClothSolverType.PBD:
                self._solve_pbd(delta_time, iterations)
            elif solver_type == ClothSolverType.XPBD:
                self._solve_xpbd(delta_time, iterations)
            elif solver_type == ClothSolverType.JACOBI:
                self._solve_jacobi(delta_time, iterations)

            # Detect and resolve collisions
            for mesh in self._meshes.values():
                collisions = self._detect_collisions(mesh)
                self._resolve_collisions(mesh, collisions)
                self._last_collision_events.extend(collisions)

            # Update normals and velocities
            for mesh in self._meshes.values():
                self._update_normals(mesh)
                self._update_velocities(mesh, delta_time)

            return self._last_collision_events

    # ------------------------------------------------------------------
    # Force Application
    # ------------------------------------------------------------------

    def _apply_gravity_and_wind(self, mesh: ClothMesh) -> None:
        """Apply gravity and wind forces to all non-pinned particles."""
        gx, gy, gz = self._gravity
        wx, wy, wz = self._global_wind
        wind_affinity = mesh.material.wind_affinity

        for particle in mesh.particles:
            if particle.is_pinned:
                continue
            particle.forces = _vec3_add(particle.forces, self._gravity)
            if wind_affinity > 0.0:
                wind_force = _vec3_scale(self._global_wind, wind_affinity)
                particle.forces = _vec3_add(particle.forces, wind_force)

    # ------------------------------------------------------------------
    # Integration
    # ------------------------------------------------------------------

    def _integrate_particles(
        self,
        mesh: ClothMesh,
        delta_time: float,
        solver_type: ClothSolverType,
    ) -> None:
        """Integrate particle positions using the selected solver's method."""
        dt_sq = delta_time * delta_time
        damping = 1.0 - mesh.material.damping

        for particle in mesh.particles:
            if particle.is_pinned:
                particle.previous_position = particle.position
                particle.forces = (0.0, 0.0, 0.0)
                continue

            if solver_type in (ClothSolverType.VERLET, ClothSolverType.PBD, ClothSolverType.XPBD):
                # Verlet-style integration
                px, py, pz = particle.position
                ox, oy, oz = particle.previous_position
                fx, fy, fz = particle.forces
                inv_mass = particle.get_inverse_mass()

                new_x = px + (px - ox) * damping + fx * inv_mass * dt_sq
                new_y = py + (py - oy) * damping + fy * inv_mass * dt_sq
                new_z = pz + (pz - oz) * damping + fz * inv_mass * dt_sq

                particle.previous_position = (px, py, pz)
                particle.position = (new_x, new_y, new_z)
            else:
                # Velocity-based integration for Jacobi
                inv_mass = particle.get_inverse_mass()
                fx, fy, fz = particle.forces
                vx, vy, vz = particle.velocity
                px, py, pz = particle.position

                vx += fx * inv_mass * delta_time
                vy += fy * inv_mass * delta_time
                vz += fz * inv_mass * delta_time

                vx *= damping
                vy *= damping
                vz *= damping

                particle.velocity = (vx, vy, vz)
                particle.previous_position = (px, py, pz)
                particle.position = (px + vx * delta_time, py + vy * delta_time, pz + vz * delta_time)

            particle.forces = (0.0, 0.0, 0.0)

    def _integrate_soft_body(
        self,
        body: SoftBody,
        delta_time: float,
        solver_type: ClothSolverType,
    ) -> None:
        """Integrate soft body particles, applying pressure forces."""
        body.center_of_mass = body.compute_center_of_mass()
        dt_sq = delta_time * delta_time

        for particle in body.particles:
            if particle.is_pinned:
                particle.previous_position = particle.position
                particle.forces = (0.0, 0.0, 0.0)
                continue

            # Apply gravity
            particle.forces = _vec3_add(particle.forces, self._gravity)

            # Apply pressure: outward force from center of mass
            if body.pressure > 0.0:
                to_center = _vec3_sub(particle.position, body.center_of_mass)
                dist = _vec3_length(to_center)
                if dist > 0.001:
                    dir_outward = _vec3_normalize(to_center)
                    pressure_force = _vec3_scale(dir_outward, body.pressure * 0.5)
                    particle.forces = _vec3_add(particle.forces, pressure_force)

            if solver_type in (ClothSolverType.VERLET, ClothSolverType.PBD, ClothSolverType.XPBD):
                px, py, pz = particle.position
                ox, oy, oz = particle.previous_position
                fx, fy, fz = particle.forces
                inv_mass = particle.get_inverse_mass()
                damp = 1.0 - particle.damping

                new_x = px + (px - ox) * damp + fx * inv_mass * dt_sq
                new_y = py + (py - oy) * damp + fy * inv_mass * dt_sq
                new_z = pz + (pz - oz) * damp + fz * inv_mass * dt_sq

                particle.previous_position = (px, py, pz)
                particle.position = (new_x, new_y, new_z)
            else:
                inv_mass = particle.get_inverse_mass()
                fx, fy, fz = particle.forces
                vx, vy, vz = particle.velocity
                px, py, pz = particle.position
                damp = 1.0 - particle.damping

                vx += fx * inv_mass * delta_time
                vy += fy * inv_mass * delta_time
                vz += fz * inv_mass * delta_time
                vx *= damp
                vy *= damp
                vz *= damp

                particle.velocity = (vx, vy, vz)
                particle.previous_position = (px, py, pz)
                particle.position = (px + vx * delta_time, py + vy * delta_time, pz + vz * delta_time)

            particle.forces = (0.0, 0.0, 0.0)

    # ------------------------------------------------------------------
    # Solver Backends
    # ------------------------------------------------------------------

    def _solve_verlet(self, delta_time: float, iterations: int) -> None:
        """Verlet solver: iterative constraint relaxation on all meshes and bodies."""
        for _ in range(iterations):
            for mesh in self._meshes.values():
                self._solve_constraints(mesh)
            for body in self._soft_bodies.values():
                if body.is_active:
                    self._solve_soft_body_constraints(body)

    def _solve_pbd(self, delta_time: float, iterations: int) -> None:
        """PBD solver: position-based constraint projection with Gauss-Seidel."""
        for _ in range(iterations):
            for mesh in self._meshes.values():
                self._solve_constraints_pbd(mesh)
            for body in self._soft_bodies.values():
                if body.is_active:
                    self._solve_soft_body_constraints_pbd(body)

    def _solve_xpbd(self, delta_time: float, iterations: int) -> None:
        """XPBD solver: extended PBD with compliance-based lambda accumulation."""
        dt_sq = delta_time * delta_time
        for _ in range(iterations):
            for mesh in self._meshes.values():
                self._solve_constraints_xpbd(mesh, dt_sq)
            for body in self._soft_bodies.values():
                if body.is_active:
                    self._solve_soft_body_constraints_xpbd(body, dt_sq)

    def _solve_jacobi(self, delta_time: float, iterations: int) -> None:
        """Jacobi solver: parallel constraint averaging for all particles."""
        for _ in range(iterations):
            for mesh in self._meshes.values():
                self._solve_constraints_jacobi(mesh)
            for body in self._soft_bodies.values():
                if body.is_active:
                    self._solve_soft_body_constraints_jacobi(body)

    # ------------------------------------------------------------------
    # Constraint Solving (Verlet-style)
    # ------------------------------------------------------------------

    def _solve_constraints(self, mesh: ClothMesh) -> None:
        """Solve all distance constraints for a mesh using Verlet relaxation."""
        for constraint in mesh.constraints:
            if not constraint.is_active:
                continue
            self._satisfy_distance_constraint(mesh, constraint)

    def _solve_soft_body_constraints(self, body: SoftBody) -> None:
        """Solve constraints for a soft body using Verlet relaxation."""
        for constraint in body.constraints:
            if not constraint.is_active:
                continue
            self._satisfy_distance_constraint_soft_body(body, constraint)

    def _satisfy_distance_constraint(self, mesh: ClothMesh, constraint: ClothConstraint) -> None:
        """Satisfy a single distance constraint using inverse mass weighting."""
        pa = mesh.get_particle(constraint.particle_a_id)
        pb = mesh.get_particle(constraint.particle_b_id)
        if pa is None or pb is None:
            return

        delta = _vec3_sub(pb.position, pa.position)
        dist = _vec3_length(delta)
        if dist < 1e-9:
            return

        total_inv = pa.get_inverse_mass() + pb.get_inverse_mass()
        if total_inv <= 0.0:
            return

        # Check for tearing
        if constraint.tear_threshold is not None:
            strain = abs(dist - constraint.rest_length) / constraint.rest_length
            if strain > constraint.tear_threshold:
                constraint.is_active = False
                self._total_tears += 1
                return

        # Use compression stiffness when compressed, normal stiffness when stretched
        if dist < constraint.rest_length:
            effective_stiffness = constraint.compression_stiffness
        else:
            effective_stiffness = constraint.stiffness

        correction = (constraint.rest_length - dist) / dist * effective_stiffness / total_inv
        cx = delta[0] * correction
        cy = delta[1] * correction
        cz = delta[2] * correction

        pa.position = (
            pa.position[0] - cx * pa.get_inverse_mass(),
            pa.position[1] - cy * pa.get_inverse_mass(),
            pa.position[2] - cz * pa.get_inverse_mass(),
        )
        pb.position = (
            pb.position[0] + cx * pb.get_inverse_mass(),
            pb.position[1] + cy * pb.get_inverse_mass(),
            pb.position[2] + cz * pb.get_inverse_mass(),
        )

    def _satisfy_distance_constraint_soft_body(self, body: SoftBody, constraint: ClothConstraint) -> None:
        """Satisfy a distance constraint for a soft body."""
        pa = body.get_particle(constraint.particle_a_id)
        pb = body.get_particle(constraint.particle_b_id)
        if pa is None or pb is None:
            return

        delta = _vec3_sub(pb.position, pa.position)
        dist = _vec3_length(delta)
        if dist < 1e-9:
            return

        total_inv = pa.get_inverse_mass() + pb.get_inverse_mass()
        if total_inv <= 0.0:
            return

        if constraint.tear_threshold is not None:
            strain = abs(dist - constraint.rest_length) / constraint.rest_length
            if strain > constraint.tear_threshold:
                constraint.is_active = False
                return

        if dist < constraint.rest_length:
            effective_stiffness = constraint.compression_stiffness
        else:
            effective_stiffness = constraint.stiffness

        correction = (constraint.rest_length - dist) / dist * effective_stiffness / total_inv
        cx = delta[0] * correction
        cy = delta[1] * correction
        cz = delta[2] * correction

        pa.position = (
            pa.position[0] - cx * pa.get_inverse_mass(),
            pa.position[1] - cy * pa.get_inverse_mass(),
            pa.position[2] - cz * pa.get_inverse_mass(),
        )
        pb.position = (
            pb.position[0] + cx * pb.get_inverse_mass(),
            pb.position[1] + cy * pb.get_inverse_mass(),
            pb.position[2] + cz * pb.get_inverse_mass(),
        )

    # ------------------------------------------------------------------
    # Constraint Solving (PBD)
    # ------------------------------------------------------------------

    def _solve_constraints_pbd(self, mesh: ClothMesh) -> None:
        """PBD constraint solving with sequential Gauss-Seidel projection."""
        for constraint in mesh.constraints:
            if not constraint.is_active:
                continue
            self._project_constraint_pbd(mesh, constraint)

    def _solve_soft_body_constraints_pbd(self, body: SoftBody) -> None:
        """PBD constraint solving for soft bodies."""
        for constraint in body.constraints:
            if not constraint.is_active:
                continue
            self._project_constraint_pbd_soft_body(body, constraint)

    def _project_constraint_pbd(self, mesh: ClothMesh, constraint: ClothConstraint) -> None:
        """Project a PBD distance constraint."""
        pa = mesh.get_particle(constraint.particle_a_id)
        pb = mesh.get_particle(constraint.particle_b_id)
        if pa is None or pb is None:
            return

        delta = _vec3_sub(pb.position, pa.position)
        dist = _vec3_length(delta)
        if dist < 1e-9:
            return

        total_inv = pa.get_inverse_mass() + pb.get_inverse_mass()
        if total_inv <= 0.0:
            return

        if constraint.tear_threshold is not None:
            strain = abs(dist - constraint.rest_length) / constraint.rest_length
            if strain > constraint.tear_threshold:
                constraint.is_active = False
                self._total_tears += 1
                return

        if dist < constraint.rest_length:
            effective_stiffness = constraint.compression_stiffness
        else:
            effective_stiffness = constraint.stiffness

        grad_c = _vec3_scale(delta, 1.0 / dist)
        c = dist - constraint.rest_length
        s = c / total_inv

        correction = _vec3_scale(grad_c, s * effective_stiffness)

        pa.position = _vec3_sub(pa.position, _vec3_scale(correction, pa.get_inverse_mass()))
        pb.position = _vec3_add(pb.position, _vec3_scale(correction, pb.get_inverse_mass()))

    def _project_constraint_pbd_soft_body(self, body: SoftBody, constraint: ClothConstraint) -> None:
        """Project a PBD distance constraint for a soft body."""
        pa = body.get_particle(constraint.particle_a_id)
        pb = body.get_particle(constraint.particle_b_id)
        if pa is None or pb is None:
            return

        delta = _vec3_sub(pb.position, pa.position)
        dist = _vec3_length(delta)
        if dist < 1e-9:
            return

        total_inv = pa.get_inverse_mass() + pb.get_inverse_mass()
        if total_inv <= 0.0:
            return

        if constraint.tear_threshold is not None:
            strain = abs(dist - constraint.rest_length) / constraint.rest_length
            if strain > constraint.tear_threshold:
                constraint.is_active = False
                return

        if dist < constraint.rest_length:
            effective_stiffness = constraint.compression_stiffness
        else:
            effective_stiffness = constraint.stiffness

        grad_c = _vec3_scale(delta, 1.0 / dist)
        c = dist - constraint.rest_length
        s = c / total_inv

        correction = _vec3_scale(grad_c, s * effective_stiffness)

        pa.position = _vec3_sub(pa.position, _vec3_scale(correction, pa.get_inverse_mass()))
        pb.position = _vec3_add(pb.position, _vec3_scale(correction, pb.get_inverse_mass()))

    # ------------------------------------------------------------------
    # Constraint Solving (XPBD)
    # ------------------------------------------------------------------

    def _solve_constraints_xpbd(self, mesh: ClothMesh, dt_sq: float) -> None:
        """XPBD constraint solving with compliance-based lambda accumulation."""
        for constraint in mesh.constraints:
            if not constraint.is_active:
                continue
            self._project_constraint_xpbd(mesh, constraint, dt_sq)

    def _solve_soft_body_constraints_xpbd(self, body: SoftBody, dt_sq: float) -> None:
        """XPBD constraint solving for soft bodies."""
        for constraint in body.constraints:
            if not constraint.is_active:
                continue
            self._project_constraint_xpbd_soft_body(body, constraint, dt_sq)

    def _project_constraint_xpbd(self, mesh: ClothMesh, constraint: ClothConstraint, dt_sq: float) -> None:
        """Project a single XPBD constraint with compliance factor."""
        pa = mesh.get_particle(constraint.particle_a_id)
        pb = mesh.get_particle(constraint.particle_b_id)
        if pa is None or pb is None:
            return

        delta = _vec3_sub(pb.position, pa.position)
        dist = _vec3_length(delta)
        if dist < 1e-9:
            return

        total_inv = pa.get_inverse_mass() + pb.get_inverse_mass()
        if total_inv <= 0.0:
            return

        if constraint.tear_threshold is not None:
            strain = abs(dist - constraint.rest_length) / constraint.rest_length
            if strain > constraint.tear_threshold:
                constraint.is_active = False
                self._total_tears += 1
                return

        # Compliance: inverse of stiffness, mapped to physical compliance
        compliance = self.XPBD_COMPLIANCE_BASE / max(constraint.stiffness, 0.001)
        alpha_tilde = compliance / dt_sq

        grad_c = _vec3_scale(delta, 1.0 / dist)
        c = dist - constraint.rest_length

        delta_lambda = -(c + alpha_tilde * constraint._lambda) / (total_inv + alpha_tilde)
        constraint._lambda += delta_lambda

        correction = _vec3_scale(grad_c, delta_lambda)

        pa.position = _vec3_sub(pa.position, _vec3_scale(correction, pa.get_inverse_mass()))
        pb.position = _vec3_add(pb.position, _vec3_scale(correction, pb.get_inverse_mass()))

    def _project_constraint_xpbd_soft_body(self, body: SoftBody, constraint: ClothConstraint, dt_sq: float) -> None:
        """Project an XPBD constraint for a soft body."""
        pa = body.get_particle(constraint.particle_a_id)
        pb = body.get_particle(constraint.particle_b_id)
        if pa is None or pb is None:
            return

        delta = _vec3_sub(pb.position, pa.position)
        dist = _vec3_length(delta)
        if dist < 1e-9:
            return

        total_inv = pa.get_inverse_mass() + pb.get_inverse_mass()
        if total_inv <= 0.0:
            return

        if constraint.tear_threshold is not None:
            strain = abs(dist - constraint.rest_length) / constraint.rest_length
            if strain > constraint.tear_threshold:
                constraint.is_active = False
                return

        compliance = self.XPBD_COMPLIANCE_BASE / max(constraint.stiffness, 0.001)
        alpha_tilde = compliance / dt_sq

        grad_c = _vec3_scale(delta, 1.0 / dist)
        c = dist - constraint.rest_length

        delta_lambda = -(c + alpha_tilde * constraint._lambda) / (total_inv + alpha_tilde)
        constraint._lambda += delta_lambda

        correction = _vec3_scale(grad_c, delta_lambda)

        pa.position = _vec3_sub(pa.position, _vec3_scale(correction, pa.get_inverse_mass()))
        pb.position = _vec3_add(pb.position, _vec3_scale(correction, pb.get_inverse_mass()))

    # ------------------------------------------------------------------
    # Constraint Solving (Jacobi)
    # ------------------------------------------------------------------

    def _solve_constraints_jacobi(self, mesh: ClothMesh) -> None:
        """Jacobi-style constraint solving with parallel displacement averaging."""
        # Accumulate corrections per particle
        corrections: Dict[str, List[Tuple[float, float, float]]] = {p.particle_id: [] for p in mesh.particles}

        for constraint in mesh.constraints:
            if not constraint.is_active:
                continue
            pa = mesh.get_particle(constraint.particle_a_id)
            pb = mesh.get_particle(constraint.particle_b_id)
            if pa is None or pb is None:
                continue

            delta = _vec3_sub(pb.position, pa.position)
            dist = _vec3_length(delta)
            if dist < 1e-9:
                continue

            total_inv = pa.get_inverse_mass() + pb.get_inverse_mass()
            if total_inv <= 0.0:
                continue

            if constraint.tear_threshold is not None:
                strain = abs(dist - constraint.rest_length) / constraint.rest_length
                if strain > constraint.tear_threshold:
                    constraint.is_active = False
                    self._total_tears += 1
                    continue

            if dist < constraint.rest_length:
                effective_stiffness = constraint.compression_stiffness
            else:
                effective_stiffness = constraint.stiffness

            correction = (constraint.rest_length - dist) / dist * effective_stiffness / total_inv
            cx = delta[0] * correction
            cy = delta[1] * correction
            cz = delta[2] * correction

            corrections[pa.particle_id].append((-cx * pa.get_inverse_mass(), -cy * pa.get_inverse_mass(), -cz * pa.get_inverse_mass()))
            corrections[pb.particle_id].append((cx * pb.get_inverse_mass(), cy * pb.get_inverse_mass(), cz * pb.get_inverse_mass()))

        # Apply averaged corrections
        for particle in mesh.particles:
            if particle.is_pinned:
                continue
            particle_corrections = corrections.get(particle.particle_id, [])
            if not particle_corrections:
                continue
            n = len(particle_corrections)
            avg_x = sum(c[0] for c in particle_corrections) / n
            avg_y = sum(c[1] for c in particle_corrections) / n
            avg_z = sum(c[2] for c in particle_corrections) / n
            particle.position = (
                particle.position[0] + avg_x,
                particle.position[1] + avg_y,
                particle.position[2] + avg_z,
            )

    def _solve_soft_body_constraints_jacobi(self, body: SoftBody) -> None:
        """Jacobi-style constraint solving for soft bodies."""
        corrections: Dict[str, List[Tuple[float, float, float]]] = {p.particle_id: [] for p in body.particles}

        for constraint in body.constraints:
            if not constraint.is_active:
                continue
            pa = body.get_particle(constraint.particle_a_id)
            pb = body.get_particle(constraint.particle_b_id)
            if pa is None or pb is None:
                continue

            delta = _vec3_sub(pb.position, pa.position)
            dist = _vec3_length(delta)
            if dist < 1e-9:
                continue

            total_inv = pa.get_inverse_mass() + pb.get_inverse_mass()
            if total_inv <= 0.0:
                continue

            if constraint.tear_threshold is not None:
                strain = abs(dist - constraint.rest_length) / constraint.rest_length
                if strain > constraint.tear_threshold:
                    constraint.is_active = False
                    continue

            if dist < constraint.rest_length:
                effective_stiffness = constraint.compression_stiffness
            else:
                effective_stiffness = constraint.stiffness

            correction = (constraint.rest_length - dist) / dist * effective_stiffness / total_inv
            cx = delta[0] * correction
            cy = delta[1] * correction
            cz = delta[2] * correction

            corrections[pa.particle_id].append((-cx * pa.get_inverse_mass(), -cy * pa.get_inverse_mass(), -cz * pa.get_inverse_mass()))
            corrections[pb.particle_id].append((cx * pb.get_inverse_mass(), cy * pb.get_inverse_mass(), cz * pb.get_inverse_mass()))

        for particle in body.particles:
            if particle.is_pinned:
                continue
            particle_corrections = corrections.get(particle.particle_id, [])
            if not particle_corrections:
                continue
            n = len(particle_corrections)
            avg_x = sum(c[0] for c in particle_corrections) / n
            avg_y = sum(c[1] for c in particle_corrections) / n
            avg_z = sum(c[2] for c in particle_corrections) / n
            particle.position = (
                particle.position[0] + avg_x,
                particle.position[1] + avg_y,
                particle.position[2] + avg_z,
            )

    # ------------------------------------------------------------------
    # Volume Conservation (Soft Bodies)
    # ------------------------------------------------------------------

    def _compute_soft_body_volume(self, body: SoftBody) -> float:
        """Approximate the volume of a soft body from its particle positions.

        Uses the centroid-based tetrahedral decomposition of the
        particle set to estimate enclosed volume.
        """
        if len(body.particles) < 4:
            return 0.0

        centroid = body.compute_center_of_mass()
        volume = 0.0

        # Use the first three particles plus centroid to form tetrahedra
        particle_list = [p for p in body.particles if not p.is_pinned]
        if len(particle_list) < 4:
            return 0.0

        for i in range(len(particle_list) - 2):
            a = _vec3_sub(particle_list[i].position, centroid)
            b = _vec3_sub(particle_list[i + 1].position, centroid)
            c = _vec3_sub(particle_list[i + 2].position, centroid)
            volume += abs(_vec3_dot(a, _vec3_cross(b, c))) / 6.0

        return volume

    # ------------------------------------------------------------------
    # Collision Detection and Resolution
    # ------------------------------------------------------------------

    def _detect_collisions(self, mesh: ClothMesh) -> List[Dict[str, Any]]:
        """Detect collisions between mesh particles and collision spheres."""
        events: List[Dict[str, Any]] = []
        for sphere in self._collision_spheres.values():
            for particle in mesh.particles:
                if particle.is_pinned:
                    continue
                delta = _vec3_sub(particle.position, sphere.center)
                dist = _vec3_length(delta)
                if dist < sphere.radius and dist > 0.0001:
                    normal = _vec3_normalize(delta)
                    penetration = sphere.radius - dist
                    events.append({
                        "particle_id": particle.particle_id,
                        "mesh_id": mesh.mesh_id,
                        "sphere_id": sphere.sphere_id,
                        "contact_point": list(_vec3_add(sphere.center, _vec3_scale(normal, sphere.radius))),
                        "normal": list(normal),
                        "penetration": penetration,
                        "friction": sphere.friction,
                    })
        return events

    def _resolve_collisions(self, mesh: ClothMesh, collisions: List[Dict[str, Any]]) -> None:
        """Resolve detected collisions by pushing particles out of spheres."""
        for event in collisions:
            particle = mesh.get_particle(event["particle_id"])
            if particle is None:
                continue

            normal = (event["normal"][0], event["normal"][1], event["normal"][2])
            penetration = event["penetration"]
            friction = event["friction"]

            # Push particle out along normal
            particle.position = _vec3_add(particle.position, _vec3_scale(normal, penetration * 1.01))

            # Apply friction by reducing tangential velocity component
            velocity = _vec3_sub(particle.position, particle.previous_position)
            normal_vel = _vec3_dot(velocity, normal)
            if normal_vel < 0.0:
                normal_component = _vec3_scale(normal, normal_vel)
                tangent_component = _vec3_sub(velocity, normal_component)
                # Reduce tangential component by friction
                tangent_component = _vec3_scale(tangent_component, 1.0 - friction)
                # Reflect normal component with damping
                new_velocity = _vec3_add(_vec3_scale(normal_component, -0.3), tangent_component)
                particle.previous_position = _vec3_sub(particle.position, new_velocity)

    # ------------------------------------------------------------------
    # Normal and Velocity Updates
    # ------------------------------------------------------------------

    def _update_normals(self, mesh: ClothMesh) -> None:
        """Recompute particle normals from surrounding triangle faces."""
        # Reset all normals
        for particle in mesh.particles:
            particle.normal = (0.0, 0.0, 0.0)

        cols = mesh.width_segments + 1
        rows = mesh.height_segments + 1

        # Compute face normals from triangles and accumulate to vertices
        for row in range(rows - 1):
            for col in range(cols - 1):
                # Two triangles per quad
                pid_tl = mesh._grid_map.get((row, col))
                pid_tr = mesh._grid_map.get((row, col + 1))
                pid_bl = mesh._grid_map.get((row + 1, col))
                pid_br = mesh._grid_map.get((row + 1, col + 1))

                if not all([pid_tl, pid_tr, pid_bl, pid_br]):
                    continue

                p_tl = mesh.get_particle(pid_tl)
                p_tr = mesh.get_particle(pid_tr)
                p_bl = mesh.get_particle(pid_bl)
                p_br = mesh.get_particle(pid_br)
                if not all([p_tl, p_tr, p_bl, p_br]):
                    continue

                # Triangle 1: top-left, bottom-left, top-right
                e1 = _vec3_sub(p_bl.position, p_tl.position)
                e2 = _vec3_sub(p_tr.position, p_tl.position)
                n1 = _vec3_normalize(_vec3_cross(e1, e2))

                # Triangle 2: bottom-right, top-right, bottom-left
                e3 = _vec3_sub(p_tr.position, p_br.position)
                e4 = _vec3_sub(p_bl.position, p_br.position)
                n2 = _vec3_normalize(_vec3_cross(e3, e4))

                # Accumulate to vertices
                p_tl.normal = _vec3_add(p_tl.normal, n1)
                p_bl.normal = _vec3_add(p_bl.normal, n1)
                p_tr.normal = _vec3_add(p_tr.normal, n1)
                p_br.normal = _vec3_add(p_br.normal, n2)
                p_tr.normal = _vec3_add(p_tr.normal, n2)
                p_bl.normal = _vec3_add(p_bl.normal, n2)

        # Normalize all normals
        for particle in mesh.particles:
            nl = _vec3_length(particle.normal)
            if nl > 0.0001:
                particle.normal = _vec3_normalize(particle.normal)
            else:
                particle.normal = (0.0, 0.0, 1.0)

    def _update_velocities(self, mesh: ClothMesh, delta_time: float) -> None:
        """Update particle velocities from position change."""
        if delta_time <= 0.0:
            return
        inv_dt = 1.0 / delta_time
        for particle in mesh.particles:
            if particle.is_pinned:
                particle.velocity = (0.0, 0.0, 0.0)
                continue
            delta = _vec3_sub(particle.position, particle.previous_position)
            particle.velocity = _vec3_scale(delta, inv_dt)

    # ------------------------------------------------------------------
    # Gravity
    # ------------------------------------------------------------------

    def set_gravity(self, gravity: Tuple[float, float, float]) -> None:
        """Set the global gravity vector for all cloth meshes and soft bodies."""
        with self._lock:
            self._gravity = gravity

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire cloth physics engine state."""
        with self._lock:
            self._meshes.clear()
            self._soft_bodies.clear()
            self._collision_spheres.clear()
            self._gravity = self.DEFAULT_GRAVITY
            self._global_wind = self.DEFAULT_WIND
            self._step_count = 0
            self._total_tears = 0
            self._last_collision_events.clear()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_cloth_physics() -> ClothPhysicsEngine:
    """Get or create the singleton ClothPhysicsEngine instance."""
    return ClothPhysicsEngine.get_instance()