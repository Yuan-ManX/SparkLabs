"""
SparkLabs Engine - Granular Physics Simulation System

A particle-based granular material simulation engine for sand, snow, gravel,
dirt, rice, beans, salt, powder, debris, ash, cobble, and dust. The system
fills a genuine physics gap in the engine: fluid dynamics covers liquids and
gases, while this module covers the distinct rheology of granular solids.

Physics models implemented:
  - Particle-based granular dynamics with penalty-based contact resolution
    and Coulomb friction, integrated with velocity-Verlet.
  - Mohr-Coulomb yield criterion for shear failure of granular assemblies.
  - Angle of repose computation and avalanche triggering for cohesive and
    cohesionless materials.
  - Percolation and segregation (Brazil nut effect) under vibration.
  - Beverloo law for hopper and orifice mass flow rates.
  - Janssen effect for saturated wall pressure in granular columns.
  - Packing density, terminal velocity, and slope stability analysis.

Architecture:
  _GranularPhysicsSystem (Singleton)
    |-- GranularParticle     -- individual granular particle with state
    |-- GranularPile         -- cohesive pile/cone of particles
    |-- GranularEmitter      -- continuous particle source
    |-- GranularObstacle     -- static or moving obstacle
    |-- GranularConfig       -- simulation configuration
    |-- GranularStats        -- per-step metrics
    |-- GranularSnapshot     -- full state for serialization
    |-- GranularEvent        -- event log entry
    |-- MaterialProperties   -- per-material physical constants

Threading:
  Singleton creation is guarded by a class-level ``_init_lock`` using
  double-checked locking. All mutable state is guarded by an instance-level
  ``_lock`` (a reentrant lock). A ``_seeded`` flag guarantees the default
  piles, emitters, and obstacles are created exactly once.

Coordinate system:
  Three-dimensional, right-handed, with +Y pointing up. Gravity acts in the
  -Y direction by default. Positions and velocities are 3-tuples of floats.
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GRAVITY_DEFAULT: float = 9.81
_EPSILON: float = 1e-9
_PI: float = math.pi

# Default simulation domain as (min_x, min_y, min_z, max_x, max_y, max_z).
_DEFAULT_DOMAIN: Tuple[float, float, float, float, float, float] = (
    -25.0,
    -25.0,
    0.0,
    25.0,
    25.0,
    50.0,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GranularMaterial(str, Enum):
    """Granular material types with distinct physical properties."""

    SAND = "sand"
    SNOW = "snow"
    GRAVEL = "gravel"
    DIRT = "dirt"
    RICE = "rice"
    BEANS = "beans"
    SALT = "salt"
    POWDER = "powder"
    DEBRIS = "debris"
    ASH = "ash"
    COBBLE = "cobble"
    DUST = "dust"


class ObstacleShape(str, Enum):
    """Shape of a granular obstacle."""

    BOX = "box"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    PLANE = "plane"
    MESH = "mesh"


class GranularEventKind(str, Enum):
    """Kinds of events recorded by the granular physics system."""

    EMITTER_REGISTERED = "emitter_registered"
    EMITTER_REMOVED = "emitter_removed"
    OBSTACLE_REGISTERED = "obstacle_registered"
    OBSTACLE_REMOVED = "obstacle_removed"
    PILE_CREATED = "pile_created"
    PILE_REMOVED = "pile_removed"
    PARTICLE_ADDED = "particle_added"
    PARTICLE_REMOVED = "particle_removed"
    AVALANCHE_TRIGGERED = "avalanche_triggered"
    SIMULATION_STEP = "simulation_step"
    CONFIG_CHANGED = "config_changed"
    SYSTEM_RESET = "system_reset"
    AI_PREDICTION = "ai_prediction"


class ContactType(str, Enum):
    """Type of contact resolved during simulation."""

    PARTICLE_PARTICLE = "particle_particle"
    PARTICLE_OBSTACLE = "particle_obstacle"
    PARTICLE_BOUNDARY = "particle_boundary"


# ---------------------------------------------------------------------------
# Material property presets
# ---------------------------------------------------------------------------

_MATERIAL_PRESETS: Dict[GranularMaterial, Dict[str, Any]] = {
    GranularMaterial.SAND: {
        "density": 1600.0,
        "friction_angle": 34.0,
        "cohesion": 0.0,
        "percolation_rate": 0.18,
        "color": "tan",
    },
    GranularMaterial.SNOW: {
        "density": 300.0,
        "friction_angle": 38.0,
        "cohesion": 50.0,
        "percolation_rate": 0.06,
        "color": "white",
    },
    GranularMaterial.GRAVEL: {
        "density": 1800.0,
        "friction_angle": 36.0,
        "cohesion": 0.0,
        "percolation_rate": 0.22,
        "color": "gray",
    },
    GranularMaterial.DIRT: {
        "density": 1400.0,
        "friction_angle": 30.0,
        "cohesion": 20.0,
        "percolation_rate": 0.12,
        "color": "brown",
    },
    GranularMaterial.RICE: {
        "density": 850.0,
        "friction_angle": 35.0,
        "cohesion": 0.0,
        "percolation_rate": 0.20,
        "color": "white",
    },
    GranularMaterial.BEANS: {
        "density": 750.0,
        "friction_angle": 32.0,
        "cohesion": 0.0,
        "percolation_rate": 0.26,
        "color": "red",
    },
    GranularMaterial.SALT: {
        "density": 1200.0,
        "friction_angle": 40.0,
        "cohesion": 5.0,
        "percolation_rate": 0.10,
        "color": "white",
    },
    GranularMaterial.POWDER: {
        "density": 500.0,
        "friction_angle": 25.0,
        "cohesion": 100.0,
        "percolation_rate": 0.04,
        "color": "white",
    },
    GranularMaterial.DEBRIS: {
        "density": 2000.0,
        "friction_angle": 45.0,
        "cohesion": 0.0,
        "percolation_rate": 0.30,
        "color": "dark_gray",
    },
    GranularMaterial.ASH: {
        "density": 700.0,
        "friction_angle": 33.0,
        "cohesion": 10.0,
        "percolation_rate": 0.08,
        "color": "gray",
    },
    GranularMaterial.COBBLE: {
        "density": 2200.0,
        "friction_angle": 42.0,
        "cohesion": 0.0,
        "percolation_rate": 0.34,
        "color": "slate_gray",
    },
    GranularMaterial.DUST: {
        "density": 400.0,
        "friction_angle": 22.0,
        "cohesion": 80.0,
        "percolation_rate": 0.03,
        "color": "light_gray",
    },
}


# ---------------------------------------------------------------------------
# Vector helpers (3D)
# ---------------------------------------------------------------------------

def _vec_add(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Return the element-wise sum of two 3D vectors."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_sub(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Return the element-wise difference of two 3D vectors."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_scale(
    a: Tuple[float, float, float], s: float
) -> Tuple[float, float, float]:
    """Return a 3D vector scaled by a scalar."""
    return (a[0] * s, a[1] * s, a[2] * s)


def _vec_dot(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    """Return the dot product of two 3D vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_cross(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Return the cross product of two 3D vectors."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec_length(a: Tuple[float, float, float]) -> float:
    """Return the Euclidean length of a 3D vector."""
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _vec_normalize(a: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Return the unit vector along ``a``; returns zero vector if ``a`` is zero."""
    length = _vec_length(a)
    if length < _EPSILON:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / length
    return (a[0] * inv, a[1] * inv, a[2] * inv)


def _safe_float(value: float) -> Optional[float]:
    """Convert infinite or NaN floats to None for JSON serialization."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isinf(f) or math.isnan(f):
        return None
    return f


def _coerce_material(value) -> GranularMaterial:
    """Coerce a string or GranularMaterial to a GranularMaterial enum member."""
    if isinstance(value, GranularMaterial):
        return value
    if isinstance(value, str):
        try:
            return GranularMaterial(value.lower())
        except ValueError:
            try:
                return GranularMaterial[value.upper()]
            except KeyError:
                return GranularMaterial.SAND
    return GranularMaterial.SAND


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` to the closed interval ``[low, high]``."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between ``a`` and ``b`` by parameter ``t``."""
    return a + (b - a) * _clamp(t, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MaterialProperties:
    """Physical properties of a granular material.

    Attributes:
        material: Material enum value.
        density: Bulk density in kg/m^3.
        friction_angle: Internal friction angle in degrees (Mohr-Coulomb).
        cohesion: Cohesion intercept in Pa.
        percolation_rate: Dimensionless percolation/segregation coefficient.
        color: Symbolic color name used by renderers.
    """

    material: GranularMaterial = GranularMaterial.SAND
    density: float = 1600.0
    friction_angle: float = 34.0
    cohesion: float = 0.0
    percolation_rate: float = 0.18
    color: str = "tan"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material": self.material.value,
            "density": _safe_float(self.density),
            "friction_angle": _safe_float(self.friction_angle),
            "cohesion": _safe_float(self.cohesion),
            "percolation_rate": _safe_float(self.percolation_rate),
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaterialProperties":
        """Construct a MaterialProperties instance from a serialized dict."""
        material_raw = data.get("material", "sand")
        if isinstance(material_raw, GranularMaterial):
            material = material_raw
        else:
            material = GranularMaterial(str(material_raw))
        return cls(
            material=material,
            density=float(data.get("density", 1600.0)),
            friction_angle=float(data.get("friction_angle", 34.0)),
            cohesion=float(data.get("cohesion", 0.0)),
            percolation_rate=float(data.get("percolation_rate", 0.18)),
            color=str(data.get("color", "tan")),
        )


@dataclass
class GranularParticle:
    """A single granular particle.

    Attributes:
        particle_id: Unique identifier.
        position: Center position in world space (x, y, z) in meters.
        velocity: Velocity vector (vx, vy, vz) in m/s.
        radius: Particle radius in meters.
        mass: Particle mass in kg.
        density: Particle material density in kg/m^3.
        friction_coef: Coulomb friction coefficient (dimensionless).
        restitution: Coefficient of restitution (0..1).
        material_type: Material enum value.
        temperature: Temperature in Kelvin (affects cohesion for some models).
        is_static: If True, the particle does not move (treated as fixed).
    """

    particle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 0.05
    mass: float = 0.01
    density: float = 1600.0
    friction_coef: float = 0.5
    restitution: float = 0.2
    material_type: GranularMaterial = GranularMaterial.SAND
    temperature: float = 293.15
    is_static: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "particle_id": self.particle_id,
            "position": [float(self.position[0]), float(self.position[1]), float(self.position[2])],
            "velocity": [float(self.velocity[0]), float(self.velocity[1]), float(self.velocity[2])],
            "radius": _safe_float(self.radius),
            "mass": _safe_float(self.mass),
            "density": _safe_float(self.density),
            "friction_coef": _safe_float(self.friction_coef),
            "restitution": _safe_float(self.restitution),
            "material_type": self.material_type.value,
            "temperature": _safe_float(self.temperature),
            "is_static": bool(self.is_static),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GranularParticle":
        """Reconstruct a particle from a serialized dict."""
        material_raw = data.get("material_type", "sand")
        if isinstance(material_raw, GranularMaterial):
            material = material_raw
        else:
            material = GranularMaterial(str(material_raw))
        pos = data.get("position", [0.0, 0.0, 0.0])
        vel = data.get("velocity", [0.0, 0.0, 0.0])
        return cls(
            particle_id=str(data.get("particle_id", uuid.uuid4().hex)),
            position=(float(pos[0]), float(pos[1]), float(pos[2])),
            velocity=(float(vel[0]), float(vel[1]), float(vel[2])),
            radius=float(data.get("radius", 0.05)),
            mass=float(data.get("mass", 0.01)),
            density=float(data.get("density", 1600.0)),
            friction_coef=float(data.get("friction_coef", 0.5)),
            restitution=float(data.get("restitution", 0.2)),
            material_type=material,
            temperature=float(data.get("temperature", 293.15)),
            is_static=bool(data.get("is_static", False)),
        )

    def kinetic_energy(self) -> float:
        """Return the translational kinetic energy of the particle in Joules."""
        v2 = _vec_dot(self.velocity, self.velocity)
        return 0.5 * self.mass * v2

    def volume(self) -> float:
        """Return the spherical volume of the particle in cubic meters."""
        return (4.0 / 3.0) * _PI * self.radius * self.radius * self.radius


@dataclass
class GranularPile:
    """A pile of granular material forming a cone-like heap.

    Attributes:
        pile_id: Unique identifier.
        name: Human-readable name.
        material_type: Material of the pile.
        particles: List of particle identifiers belonging to the pile.
        center: Center of the pile base (x, y, z).
        height: Pile height in meters.
        base_radius: Base radius in meters.
        angle_of_repose: Current angle of repose in degrees.
        volume: Total volume of material in cubic meters.
    """

    pile_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Unnamed Pile"
    material_type: GranularMaterial = GranularMaterial.SAND
    particles: List[str] = field(default_factory=list)
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    height: float = 0.0
    base_radius: float = 0.0
    angle_of_repose: float = 34.0
    volume: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pile_id": self.pile_id,
            "name": self.name,
            "material_type": self.material_type.value,
            "particles": list(self.particles),
            "center": [float(self.center[0]), float(self.center[1]), float(self.center[2])],
            "height": _safe_float(self.height),
            "base_radius": _safe_float(self.base_radius),
            "angle_of_repose": _safe_float(self.angle_of_repose),
            "volume": _safe_float(self.volume),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GranularPile":
        """Reconstruct a GranularPile from a serialized dict."""
        material_raw = data.get("material_type", "sand")
        if isinstance(material_raw, GranularMaterial):
            material = material_raw
        else:
            material = GranularMaterial(str(material_raw))
        center = data.get("center", [0.0, 0.0, 0.0])
        return cls(
            pile_id=str(data.get("pile_id", uuid.uuid4().hex)),
            name=str(data.get("name", "Unnamed Pile")),
            material_type=material,
            particles=list(data.get("particles", [])),
            center=(float(center[0]), float(center[1]), float(center[2])),
            height=float(data.get("height", 0.0)),
            base_radius=float(data.get("base_radius", 0.0)),
            angle_of_repose=float(data.get("angle_of_repose", 34.0)),
            volume=float(data.get("volume", 0.0)),
        )


@dataclass
class GranularEmitter:
    """A continuous source of granular particles.

    Attributes:
        emitter_id: Unique identifier.
        name: Human-readable name.
        position: Emission origin (x, y, z).
        rate: Emission rate in particles per second.
        particle_template: A particle used as a template for new emissions.
        velocity: Initial emission velocity vector.
        spread_angle: Cone half-angle of emission randomness in degrees.
        max_particles: Cap on the number of live particles from this emitter.
    """

    emitter_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Unnamed Emitter"
    position: Tuple[float, float, float] = (0.0, 5.0, 0.0)
    rate: float = 10.0
    particle_template: GranularParticle = field(default_factory=GranularParticle)
    velocity: Tuple[float, float, float] = (0.0, -1.0, 0.0)
    spread_angle: float = 15.0
    max_particles: int = 1000
    material_type: GranularMaterial = GranularMaterial.SAND

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emitter_id": self.emitter_id,
            "name": self.name,
            "position": [float(self.position[0]), float(self.position[1]), float(self.position[2])],
            "rate": _safe_float(self.rate),
            "particle_template": self.particle_template.to_dict(),
            "velocity": [float(self.velocity[0]), float(self.velocity[1]), float(self.velocity[2])],
            "spread_angle": _safe_float(self.spread_angle),
            "max_particles": int(self.max_particles),
            "material_type": self.material_type.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GranularEmitter":
        """Reconstruct a GranularEmitter from a serialized dict."""
        material_raw = data.get("material_type", "sand")
        if isinstance(material_raw, GranularMaterial):
            material = material_raw
        else:
            material = GranularMaterial(str(material_raw))
        position = data.get("position", [0.0, 5.0, 0.0])
        velocity = data.get("velocity", [0.0, -1.0, 0.0])
        template_raw = data.get("particle_template", {})
        template = GranularParticle.from_dict(template_raw)
        return cls(
            emitter_id=str(data.get("emitter_id", uuid.uuid4().hex)),
            name=str(data.get("name", "Unnamed Emitter")),
            position=(float(position[0]), float(position[1]), float(position[2])),
            rate=float(data.get("rate", 10.0)),
            particle_template=template,
            velocity=(float(velocity[0]), float(velocity[1]), float(velocity[2])),
            spread_angle=float(data.get("spread_angle", 15.0)),
            max_particles=int(data.get("max_particles", 1000)),
            material_type=material,
        )


@dataclass
class GranularObstacle:
    """A static or moving obstacle that particles collide with.

    Attributes:
        obstacle_id: Unique identifier.
        name: Human-readable name.
        shape: Obstacle shape enum.
        bounds: Shape-specific bounds tuple. For BOX this is
            (min_x, min_y, min_z, max_x, max_y, max_z); for SPHERE it is
            (center_x, center_y, center_z, radius); for CYLINDER it is
            (center_x, center_y, center_z, radius, height); for PLANE it is
            (point_x, point_y, point_z, normal_x, normal_y, normal_z).
        friction: Coulomb friction coefficient at the surface.
        is_static: If False, the obstacle may move (future extension).
    """

    obstacle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Unnamed Obstacle"
    shape: ObstacleShape = ObstacleShape.BOX
    bounds: Tuple[float, ...] = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    friction: float = 0.4
    is_static: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obstacle_id": self.obstacle_id,
            "name": self.name,
            "shape": self.shape.value,
            "bounds": [float(b) for b in self.bounds],
            "friction": _safe_float(self.friction),
            "is_static": bool(self.is_static),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GranularObstacle":
        """Reconstruct a GranularObstacle from a serialized dict."""
        shape_raw = data.get("shape", "box")
        if isinstance(shape_raw, ObstacleShape):
            shape = shape_raw
        else:
            shape = ObstacleShape(str(shape_raw))
        bounds = tuple(float(b) for b in data.get("bounds", (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)))
        return cls(
            obstacle_id=str(data.get("obstacle_id", uuid.uuid4().hex)),
            name=str(data.get("name", "Unnamed Obstacle")),
            shape=shape,
            bounds=bounds,
            friction=float(data.get("friction", 0.4)),
            is_static=bool(data.get("is_static", True)),
        )


@dataclass
class GranularConfig:
    """Simulation configuration.

    Attributes:
        gravity: Gravitational acceleration magnitude in m/s^2.
        global_friction: Default Coulomb friction coefficient.
        global_restitution: Default coefficient of restitution.
        time_step: Integration time step in seconds.
        max_particles: Hard cap on total simulated particles.
        contact_stiffness: Penalty force stiffness for contacts in N/m.
        damping: Velocity damping coefficient (drag per second).
        vibration_amplitude: Vibration amplitude in meters.
        vibration_frequency: Vibration frequency in Hz.
        domain: Simulation domain bounds tuple.
        solver_iterations: Number of constraint solver iterations per step.
        use_friction: Whether to apply Coulomb friction.
        use_cohesion: Whether to apply cohesive forces.
    """

    gravity: float = 9.81
    global_friction: float = 0.5
    global_restitution: float = 0.2
    time_step: float = 0.016
    max_particles: int = 5000
    contact_stiffness: float = 50000.0
    damping: float = 0.05
    vibration_amplitude: float = 0.0
    vibration_frequency: float = 0.0
    domain: Tuple[float, float, float, float, float, float] = _DEFAULT_DOMAIN
    solver_iterations: int = 4
    use_friction: bool = True
    use_cohesion: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gravity": _safe_float(self.gravity),
            "global_friction": _safe_float(self.global_friction),
            "global_restitution": _safe_float(self.global_restitution),
            "time_step": _safe_float(self.time_step),
            "max_particles": int(self.max_particles),
            "contact_stiffness": _safe_float(self.contact_stiffness),
            "damping": _safe_float(self.damping),
            "vibration_amplitude": _safe_float(self.vibration_amplitude),
            "vibration_frequency": _safe_float(self.vibration_frequency),
            "domain": [float(b) for b in self.domain],
            "solver_iterations": int(self.solver_iterations),
            "use_friction": bool(self.use_friction),
            "use_cohesion": bool(self.use_cohesion),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GranularConfig":
        """Construct a GranularConfig from a serialized dict."""
        domain_raw = data.get("domain", list(_DEFAULT_DOMAIN))
        domain = tuple(float(b) for b in domain_raw)
        return cls(
            gravity=float(data.get("gravity", 9.81)),
            global_friction=float(data.get("global_friction", 0.5)),
            global_restitution=float(data.get("global_restitution", 0.2)),
            time_step=float(data.get("time_step", 0.016)),
            max_particles=int(data.get("max_particles", 5000)),
            contact_stiffness=float(data.get("contact_stiffness", 50000.0)),
            damping=float(data.get("damping", 0.05)),
            vibration_amplitude=float(data.get("vibration_amplitude", 0.0)),
            vibration_frequency=float(data.get("vibration_frequency", 0.0)),
            domain=domain,
            solver_iterations=int(data.get("solver_iterations", 4)),
            use_friction=bool(data.get("use_friction", True)),
            use_cohesion=bool(data.get("use_cohesion", True)),
        )


@dataclass
class GranularStats:
    """Per-step simulation statistics.

    Attributes:
        particle_count: Number of active particles.
        pile_count: Number of piles.
        active_contacts: Number of contacts resolved this step.
        sim_time: Total simulated time in seconds.
        total_energy: Total kinetic energy of the system in Joules.
        avg_velocity: Average particle speed in m/s.
    """

    particle_count: int = 0
    pile_count: int = 0
    active_contacts: int = 0
    sim_time: float = 0.0
    total_energy: float = 0.0
    avg_velocity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "particle_count": int(self.particle_count),
            "pile_count": int(self.pile_count),
            "active_contacts": int(self.active_contacts),
            "sim_time": _safe_float(self.sim_time),
            "total_energy": _safe_float(self.total_energy),
            "avg_velocity": _safe_float(self.avg_velocity),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GranularStats":
        """Reconstruct GranularStats from a serialized dict."""
        return cls(
            particle_count=int(data.get("particle_count", 0)),
            pile_count=int(data.get("pile_count", 0)),
            active_contacts=int(data.get("active_contacts", 0)),
            sim_time=float(data.get("sim_time", 0.0)),
            total_energy=float(data.get("total_energy", 0.0)),
            avg_velocity=float(data.get("avg_velocity", 0.0)),
        )


@dataclass
class GranularSnapshot:
    """Full serialized state of the granular physics system.

    Used for checkpointing, networking, and debugging.

    Attributes:
        timestamp: Wall-clock time at snapshot creation.
        sim_time: Simulated time at snapshot creation.
        config: Simulation configuration.
        particles: All active particles.
        piles: All piles.
        emitters: All emitters.
        obstacles: All obstacles.
        stats: Latest statistics.
    """

    timestamp: float = field(default_factory=_time_module.time)
    sim_time: float = 0.0
    config: GranularConfig = field(default_factory=GranularConfig)
    particles: List[GranularParticle] = field(default_factory=list)
    piles: List[GranularPile] = field(default_factory=list)
    emitters: List[GranularEmitter] = field(default_factory=list)
    obstacles: List[GranularObstacle] = field(default_factory=list)
    stats: GranularStats = field(default_factory=GranularStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": _safe_float(self.timestamp),
            "sim_time": _safe_float(self.sim_time),
            "config": self.config.to_dict(),
            "particles": [p.to_dict() for p in self.particles],
            "piles": [p.to_dict() for p in self.piles],
            "emitters": [e.to_dict() for e in self.emitters],
            "obstacles": [o.to_dict() for o in self.obstacles],
            "stats": self.stats.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GranularSnapshot":
        """Reconstruct a GranularSnapshot from a serialized dict."""
        config = GranularConfig.from_dict(data.get("config", {}))
        particles = [
            GranularParticle.from_dict(p) for p in data.get("particles", [])
        ]
        piles = [GranularPile.from_dict(p) for p in data.get("piles", [])]
        emitters = [
            GranularEmitter.from_dict(e) for e in data.get("emitters", [])
        ]
        obstacles = [
            GranularObstacle.from_dict(o) for o in data.get("obstacles", [])
        ]
        stats = GranularStats.from_dict(data.get("stats", {}))
        return cls(
            timestamp=float(data.get("timestamp", _time_module.time())),
            sim_time=float(data.get("sim_time", 0.0)),
            config=config,
            particles=particles,
            piles=piles,
            emitters=emitters,
            obstacles=obstacles,
            stats=stats,
        )


@dataclass
class GranularEvent:
    """An event recorded in the granular physics event log.

    Attributes:
        event_id: Unique identifier.
        kind: Event kind enum.
        timestamp: Wall-clock time of the event.
        sim_time: Simulated time of the event.
        payload: Arbitrary structured data describing the event.
    """

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: GranularEventKind = GranularEventKind.SIMULATION_STEP
    timestamp: float = field(default_factory=_time_module.time)
    sim_time: float = 0.0
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": _safe_float(self.timestamp),
            "sim_time": _safe_float(self.sim_time),
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GranularEvent":
        """Reconstruct a GranularEvent from a serialized dict."""
        kind_raw = data.get("kind", "simulation_step")
        if isinstance(kind_raw, GranularEventKind):
            kind = kind_raw
        else:
            kind = GranularEventKind(str(kind_raw))
        return cls(
            event_id=str(data.get("event_id", uuid.uuid4().hex)),
            kind=kind,
            timestamp=float(data.get("timestamp", _time_module.time())),
            sim_time=float(data.get("sim_time", 0.0)),
            payload=dict(data.get("payload", {})),
        )


# ---------------------------------------------------------------------------
# Main singleton class
# ---------------------------------------------------------------------------

class _GranularPhysicsSystem:
    """Singleton granular physics simulation system.

    The system manages particles, piles, emitters, and obstacles, and steps
    the simulation forward using velocity-Verlet integration with a
    penalty-based contact model and Coulomb friction.

    Usage:
        from sparkai.engine.engine_granular_physics import get_granular_physics
        gps = get_granular_physics()
        gps.initialize()
        stats = gps.tick(0.016)
    """

    _instance: Optional["_GranularPhysicsSystem"] = None
    _init_lock = threading.RLock()

    # Physics constants used across the solver.
    EPSILON: float = _EPSILON
    BEVERLOO_CONSTANT: float = 0.58
    BEVERLOO_DIAMETER_FACTOR: float = 1.5
    JANSSEN_COEFFICIENT: float = 0.4
    RANDOM_CLOSE_PACKING: float = 0.64
    RANDOM_LOOSE_PACKING: float = 0.55
    DRAG_COEFFICIENT_SPHERE: float = 0.47

    def __new__(cls) -> "_GranularPhysicsSystem":
        # Double-checked locking on the class-level init lock.
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    instance._seeded = False
                    instance._lock = threading.RLock()
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "_GranularPhysicsSystem":
        """Return the singleton _GranularPhysicsSystem instance."""
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            self._initialized = True

            # Configuration and global state.
            self._config: GranularConfig = GranularConfig()
            self._domain: Tuple[float, float, float, float, float, float] = _DEFAULT_DOMAIN

            # Primary particle storage keyed by particle_id.
            self._particles: Dict[str, GranularParticle] = {}
            # Particle identifiers grouped by material for fast filtering.
            self._particles_by_material: Dict[GranularMaterial, List[str]] = {
                m: [] for m in GranularMaterial
            }
            # Pile storage keyed by pile_id.
            self._piles: Dict[str, GranularPile] = {}
            # Emitter storage keyed by emitter_id.
            self._emitters: Dict[str, GranularEmitter] = {}
            # Obstacle storage keyed by obstacle_id.
            self._obstacles: Dict[str, GranularObstacle] = {}
            # Per-emitter accumulated emission fractional carry.
            self._emitter_carry: Dict[str, float] = {}

            # Material property table.
            self._materials: Dict[GranularMaterial, MaterialProperties] = {}
            self._load_material_presets()

            # Accumulators and counters.
            self._sim_time: float = 0.0
            self._tick_count: int = 0
            self._total_particles_spawned: int = 0
            self._total_contacts: int = 0
            self._total_avalanches: int = 0
            self._last_contact_count: int = 0
            self._last_stats: GranularStats = GranularStats()
            self._paused: bool = False

            # Event log capped at a reasonable size.
            self._events: List[GranularEvent] = []
            self._max_events: int = 1000

            # Spatial grid for broad-phase neighbor queries.
            self._grid_cell_size: float = 0.5
            self._grid: Dict[Tuple[int, int, int], List[str]] = {}

            # Seed default data exactly once.
            self._seed_default_data()

    # ------------------------------------------------------------------
    # Initialization and seeding
    # ------------------------------------------------------------------

    def _load_material_presets(self) -> None:
        """Populate the material property table from the preset dictionary."""
        for material, preset in _MATERIAL_PRESETS.items():
            self._materials[material] = MaterialProperties(
                material=material,
                density=float(preset["density"]),
                friction_angle=float(preset["friction_angle"]),
                cohesion=float(preset["cohesion"]),
                percolation_rate=float(preset["percolation_rate"]),
                color=str(preset["color"]),
            )

    def _seed_default_data(self) -> None:
        """Create the default piles, emitters, and obstacles exactly once."""
        if self._seeded:
            return
        with self._lock:
            if self._seeded:
                return
            self._seeded = True

            # Default piles.
            self.create_pile(
                name="Sand Dune",
                material=GranularMaterial.SAND,
                count=500,
                center=(0.0, 0.0, 0.0),
                base_radius=4.0,
                height=3.0,
            )
            self.create_pile(
                name="Snow Drift",
                material=GranularMaterial.SNOW,
                count=300,
                center=(8.0, 0.0, -3.0),
                base_radius=3.0,
                height=2.0,
            )
            self.create_pile(
                name="Gravel Heap",
                material=GranularMaterial.GRAVEL,
                count=200,
                center=(-7.0, 0.0, 4.0),
                base_radius=2.5,
                height=1.8,
            )

            # Default emitters.
            sand_template = self._make_template_particle(GranularMaterial.SAND)
            snow_template = self._make_template_particle(GranularMaterial.SNOW)
            debris_template = self._make_template_particle(GranularMaterial.DEBRIS)

            self.register_emitter(
                GranularEmitter(
                    name="Sand Faucet",
                    position=(2.0, 10.0, 2.0),
                    rate=30.0,
                    particle_template=sand_template,
                    velocity=(0.0, -1.0, 0.0),
                    spread_angle=10.0,
                    max_particles=800,
                    material_type=GranularMaterial.SAND,
                )
            )
            self.register_emitter(
                GranularEmitter(
                    name="Snow Maker",
                    position=(8.0, 12.0, -3.0),
                    rate=20.0,
                    particle_template=snow_template,
                    velocity=(0.0, -0.8, 0.0),
                    spread_angle=25.0,
                    max_particles=600,
                    material_type=GranularMaterial.SNOW,
                )
            )
            self.register_emitter(
                GranularEmitter(
                    name="Debris Chute",
                    position=(-7.0, 11.0, 4.0),
                    rate=15.0,
                    particle_template=debris_template,
                    velocity=(0.0, -1.5, 0.0),
                    spread_angle=8.0,
                    max_particles=400,
                    material_type=GranularMaterial.DEBRIS,
                )
            )

            # Default obstacles.
            self.register_obstacle(
                GranularObstacle(
                    name="Ramp",
                    shape=ObstacleShape.PLANE,
                    bounds=(0.0, 0.0, 0.0, 0.0, 1.0, 0.0),
                    friction=0.4,
                    is_static=True,
                )
            )
            self.register_obstacle(
                GranularObstacle(
                    name="Container",
                    shape=ObstacleShape.BOX,
                    bounds=(-3.0, 0.0, -3.0, 3.0, 2.0, 3.0),
                    friction=0.5,
                    is_static=True,
                )
            )
            self.register_obstacle(
                GranularObstacle(
                    name="Pillar",
                    shape=ObstacleShape.CYLINDER,
                    bounds=(5.0, 0.0, 5.0, 0.6, 4.0),
                    friction=0.3,
                    is_static=True,
                )
            )

    def _make_template_particle(self, material: GranularMaterial) -> GranularParticle:
        """Build a template particle for a material using its property table."""
        props = self._materials.get(material)
        if props is None:
            props = MaterialProperties(material=material)
        radius = 0.06
        if material == GranularMaterial.POWDER or material == GranularMaterial.DUST:
            radius = 0.015
        elif material == GranularMaterial.SALT:
            radius = 0.02
        elif material == GranularMaterial.RICE:
            radius = 0.03
        elif material == GranularMaterial.BEANS:
            radius = 0.04
        elif material == GranularMaterial.COBBLE or material == GranularMaterial.DEBRIS:
            radius = 0.09
        volume = (4.0 / 3.0) * _PI * radius * radius * radius
        mass = volume * props.density
        friction_coef = math.tan(math.radians(props.friction_angle))
        return GranularParticle(
            position=(0.0, 0.0, 0.0),
            velocity=(0.0, 0.0, 0.0),
            radius=radius,
            mass=mass,
            density=props.density,
            friction_coef=friction_coef,
            restitution=self._config.global_restitution,
            material_type=material,
            temperature=293.15,
            is_static=False,
        )

    # ------------------------------------------------------------------
    # Material accessors
    # ------------------------------------------------------------------

    def list_materials(self) -> List[GranularMaterial]:
        """Return all supported granular material enum values."""
        return list(GranularMaterial)

    def get_material_properties(self, material: GranularMaterial) -> MaterialProperties:
        """Return the MaterialProperties for the given material.

        Falls back to a default properties instance if the material has no
        preset entry.
        """
        material = _coerce_material(material)
        props = self._materials.get(material)
        if props is None:
            props = MaterialProperties(material=material)
        return props

    def set_material_properties(self, material: GranularMaterial, **kwargs: Any) -> None:
        """Override properties for a material.

        Accepts keyword arguments matching MaterialProperties fields:
        density, friction_angle, cohesion, percolation_rate, color.
        """
        material = _coerce_material(material)
        with self._lock:
            current = self._materials.get(material, MaterialProperties(material=material))
            if "density" in kwargs:
                current.density = float(kwargs["density"])
            if "friction_angle" in kwargs:
                current.friction_angle = float(kwargs["friction_angle"])
            if "cohesion" in kwargs:
                current.cohesion = float(kwargs["cohesion"])
            if "percolation_rate" in kwargs:
                current.percolation_rate = float(kwargs["percolation_rate"])
            if "color" in kwargs:
                current.color = str(kwargs["color"])
            self._materials[material] = current

    # ------------------------------------------------------------------
    # Emitter management
    # ------------------------------------------------------------------

    def register_emitter(self, emitter: GranularEmitter) -> str:
        """Register a granular emitter and return its identifier."""
        with self._lock:
            self._emitters[emitter.emitter_id] = emitter
            self._emitter_carry[emitter.emitter_id] = 0.0
            self._record_event(
                GranularEventKind.EMITTER_REGISTERED,
                {
                    "emitter_id": emitter.emitter_id,
                    "name": emitter.name,
                    "rate": emitter.rate,
                    "material": emitter.material_type.value,
                },
            )
            return emitter.emitter_id

    def get_emitter(self, emitter_id: str) -> Optional[GranularEmitter]:
        """Return the emitter with the given id, or None."""
        with self._lock:
            return self._emitters.get(emitter_id)

    def list_emitters(self) -> List[GranularEmitter]:
        """Return a list of all registered emitters."""
        with self._lock:
            return list(self._emitters.values())

    def remove_emitter(self, emitter_id: str) -> bool:
        """Remove an emitter by id. Returns True if removed."""
        with self._lock:
            if emitter_id not in self._emitters:
                return False
            del self._emitters[emitter_id]
            self._emitter_carry.pop(emitter_id, None)
            self._record_event(
                GranularEventKind.EMITTER_REMOVED,
                {"emitter_id": emitter_id},
            )
            return True

    def count_emitters(self) -> int:
        """Return the number of registered emitters."""
        with self._lock:
            return len(self._emitters)

    # ------------------------------------------------------------------
    # Obstacle management
    # ------------------------------------------------------------------

    def register_obstacle(self, obstacle: GranularObstacle) -> str:
        """Register an obstacle and return its identifier."""
        with self._lock:
            self._obstacles[obstacle.obstacle_id] = obstacle
            self._record_event(
                GranularEventKind.OBSTACLE_REGISTERED,
                {
                    "obstacle_id": obstacle.obstacle_id,
                    "name": obstacle.name,
                    "shape": obstacle.shape.value,
                },
            )
            return obstacle.obstacle_id

    def get_obstacle(self, obstacle_id: str) -> Optional[GranularObstacle]:
        """Return the obstacle with the given id, or None."""
        with self._lock:
            return self._obstacles.get(obstacle_id)

    def list_obstacles(self) -> List[GranularObstacle]:
        """Return a list of all registered obstacles."""
        with self._lock:
            return list(self._obstacles.values())

    def remove_obstacle(self, obstacle_id: str) -> bool:
        """Remove an obstacle by id. Returns True if removed."""
        with self._lock:
            if obstacle_id not in self._obstacles:
                return False
            del self._obstacles[obstacle_id]
            self._record_event(
                GranularEventKind.OBSTACLE_REMOVED,
                {"obstacle_id": obstacle_id},
            )
            return True

    def count_obstacles(self) -> int:
        """Return the number of registered obstacles."""
        with self._lock:
            return len(self._obstacles)

    # ------------------------------------------------------------------
    # Particle management
    # ------------------------------------------------------------------

    def add_particle(self, particle: GranularParticle) -> str:
        """Add a particle to the simulation and return its identifier.

        Returns an empty string if the particle cap has been reached.
        """
        with self._lock:
            if len(self._particles) >= self._config.max_particles:
                return ""
            self._particles[particle.particle_id] = particle
            mat_list = self._particles_by_material.setdefault(
                particle.material_type, []
            )
            if particle.particle_id not in mat_list:
                mat_list.append(particle.particle_id)
            self._total_particles_spawned += 1
            self._record_event(
                GranularEventKind.PARTICLE_ADDED,
                {
                    "particle_id": particle.particle_id,
                    "material": particle.material_type.value,
                },
            )
            return particle.particle_id

    def remove_particle(self, particle_id: str) -> bool:
        """Remove a particle by id. Returns True if removed."""
        with self._lock:
            particle = self._particles.get(particle_id)
            if particle is None:
                return False
            del self._particles[particle_id]
            mat_list = self._particles_by_material.get(particle.material_type)
            if mat_list is not None and particle_id in mat_list:
                mat_list.remove(particle_id)
            self._record_event(
                GranularEventKind.PARTICLE_REMOVED,
                {"particle_id": particle_id},
            )
            return True

    def get_particle(self, particle_id: str) -> Optional[GranularParticle]:
        """Return the particle with the given id, or None."""
        with self._lock:
            return self._particles.get(particle_id)

    def list_particles(
        self, material: Optional[GranularMaterial] = None
    ) -> List[GranularParticle]:
        """Return a list of particles, optionally filtered by material."""
        if material is not None:
            material = _coerce_material(material)
        with self._lock:
            if material is None:
                return list(self._particles.values())
            ids = self._particles_by_material.get(material, [])
            return [self._particles[pid] for pid in ids if pid in self._particles]

    def count_particles(self) -> int:
        """Return the total number of active particles."""
        with self._lock:
            return len(self._particles)

    def count_particles_by_material(
        self, material: GranularMaterial
    ) -> int:
        """Return the number of active particles of the given material."""
        material = _coerce_material(material)
        with self._lock:
            ids = self._particles_by_material.get(material, [])
            return sum(1 for pid in ids if pid in self._particles)

    def clear_particles(self) -> int:
        """Remove all particles. Returns the number removed."""
        with self._lock:
            count = len(self._particles)
            self._particles.clear()
            for mat in self._particles_by_material:
                self._particles_by_material[mat] = []
            self._grid.clear()
            return count

    def emit_particles(self, dt: float) -> int:
        """Emit particles from all registered emitters for a time interval.

        Returns the total number of particles emitted.
        """
        if dt <= 0.0:
            return 0
        total_emitted = 0
        with self._lock:
            for emitter in list(self._emitters.values()):
                if len(self._particles) >= self._config.max_particles:
                    break
                live_count = self.count_particles_by_material(emitter.material_type)
                if live_count >= emitter.max_particles:
                    continue
                carry = self._emitter_carry.get(emitter.emitter_id, 0.0)
                to_emit_f = emitter.rate * dt + carry
                to_emit = int(to_emit_f)
                self._emitter_carry[emitter.emitter_id] = to_emit_f - float(to_emit)
                remaining_capacity = emitter.max_particles - live_count
                if to_emit > remaining_capacity:
                    to_emit = max(0, remaining_capacity)
                for _ in range(to_emit):
                    if len(self._particles) >= self._config.max_particles:
                        break
                    particle = self._instantiate_emission(emitter)
                    if self.add_particle(particle):
                        total_emitted += 1
        return total_emitted

    def _instantiate_emission(self, emitter: GranularEmitter) -> GranularParticle:
        """Create a single particle instance from an emitter template.

        Applies the emitter velocity with a randomized cone spread.
        """
        template = emitter.particle_template
        # Random direction within a cone around the emitter velocity.
        spread = math.radians(emitter.spread_angle)
        # Use a deterministic-ish pseudo-random based on uuid to avoid
        # importing random at module scope; random is fine here.
        import random

        u = random.random()
        v = random.random()
        theta = spread * math.sqrt(u)
        phi = 2.0 * _PI * v
        # Build a local frame around the emitter velocity direction.
        vel_dir = _vec_normalize(emitter.velocity)
        # Pick an arbitrary up vector not parallel to vel_dir.
        up = (0.0, 1.0, 0.0)
        if abs(_vec_dot(up, vel_dir)) > 0.99:
            up = (1.0, 0.0, 0.0)
        axis1 = _vec_normalize(_vec_cross(up, vel_dir))
        axis2 = _vec_normalize(_vec_cross(vel_dir, axis1))
        # Spherical-to-cartesian in the local frame.
        sin_theta = math.sin(theta)
        offset = _vec_add(
            _vec_scale(axis1, sin_theta * math.cos(phi)),
            _vec_scale(axis2, sin_theta * math.sin(phi)),
        )
        direction = _vec_normalize(_vec_add(vel_dir, offset))
        speed = _vec_length(emitter.velocity)
        # Slight position jitter at the emitter origin.
        jitter = (
            (random.random() - 0.5) * 0.05,
            (random.random() - 0.5) * 0.05,
            (random.random() - 0.5) * 0.05,
        )
        position = _vec_add(emitter.position, jitter)
        return GranularParticle(
            position=position,
            velocity=_vec_scale(direction, speed),
            radius=template.radius,
            mass=template.mass,
            density=template.density,
            friction_coef=template.friction_coef,
            restitution=template.restitution,
            material_type=template.material_type,
            temperature=template.temperature,
            is_static=False,
        )

    # ------------------------------------------------------------------
    # Pile management
    # ------------------------------------------------------------------

    def create_pile(
        self,
        name: str,
        material: GranularMaterial,
        count: int,
        center: Tuple[float, float, float],
        base_radius: float,
        height: float,
    ) -> str:
        """Create a conical pile of particles and return its identifier.

        Particles are distributed within a cone of the given base radius and
        height. The pile's angle of repose is derived from the material
        friction angle.
        """
        material = _coerce_material(material)
        with self._lock:
            pile = GranularPile(
                name=name,
                material_type=material,
                center=center,
                height=height,
                base_radius=base_radius,
                angle_of_repose=self.compute_angle_of_repose(material),
            )
            self._piles[pile.pile_id] = pile
            props = self._materials.get(material)
            density = props.density if props else 1600.0
            cone_volume = (1.0 / 3.0) * _PI * base_radius * base_radius * height
            pile.volume = cone_volume * self.RANDOM_LOOSE_PACKING
            # Generate particles for the pile.
            template = self._make_template_particle(material)
            particle_volume = template.volume()
            actual_count = count
            if count <= 0:
                # Estimate count from volume and particle volume.
                if particle_volume > 0.0:
                    actual_count = int(pile.volume / particle_volume)
                    actual_count = max(1, min(actual_count, 2000))
                else:
                    actual_count = 100
            for i in range(actual_count):
                if len(self._particles) >= self._config.max_particles:
                    break
                particle = self._make_pile_particle(
                    template, center, base_radius, height, density
                )
                if self.add_particle(particle):
                    pile.particles.append(particle.particle_id)
            self._record_event(
                GranularEventKind.PILE_CREATED,
                {
                    "pile_id": pile.pile_id,
                    "name": name,
                    "material": material.value,
                    "count": len(pile.particles),
                },
            )
            return pile.pile_id

    def _make_pile_particle(
        self,
        template: GranularParticle,
        center: Tuple[float, float, float],
        base_radius: float,
        height: float,
        density: float,
    ) -> GranularParticle:
        """Create a single particle placed within a conical pile volume."""
        import random

        # Sample a point inside a cone: base at y=0, apex at y=height.
        # Use rejection sampling for uniform volume distribution.
        for _ in range(32):
            y = random.random() * height
            # Radius at height y shrinks linearly.
            max_r = base_radius * (1.0 - y / max(height, _EPSILON))
            r = max_r * math.sqrt(random.random())
            theta = 2.0 * _PI * random.random()
            x = r * math.cos(theta)
            z = r * math.sin(theta)
            # Reject if outside the cone (numerical guard).
            if r <= max_r + _EPSILON:
                break
        position = (center[0] + x, center[1] + y, center[2] + z)
        return GranularParticle(
            position=position,
            velocity=(0.0, 0.0, 0.0),
            radius=template.radius,
            mass=template.mass,
            density=density,
            friction_coef=template.friction_coef,
            restitution=template.restitution,
            material_type=template.material_type,
            temperature=template.temperature,
            is_static=False,
        )

    def get_pile(self, pile_id: str) -> Optional[GranularPile]:
        """Return the pile with the given id, or None."""
        with self._lock:
            return self._piles.get(pile_id)

    def list_piles(self) -> List[GranularPile]:
        """Return a list of all piles."""
        with self._lock:
            return list(self._piles.values())

    def remove_pile(self, pile_id: str, remove_particles: bool = False) -> bool:
        """Remove a pile by id. Returns True if removed.

        If ``remove_particles`` is True, the particles belonging to the pile
        are also removed from the simulation.
        """
        with self._lock:
            pile = self._piles.get(pile_id)
            if pile is None:
                return False
            if remove_particles:
                for pid in list(pile.particles):
                    self.remove_particle(pid)
            del self._piles[pile_id]
            self._record_event(
                GranularEventKind.PILE_REMOVED,
                {"pile_id": pile_id, "removed_particles": remove_particles},
            )
            return True

    def count_piles(self) -> int:
        """Return the number of piles."""
        with self._lock:
            return len(self._piles)

    def find_pile_at(
        self, point: Tuple[float, float, float]
    ) -> Optional[GranularPile]:
        """Return the pile whose base contains the given point, or None."""
        with self._lock:
            best: Optional[GranularPile] = None
            best_dist = math.inf
            for pile in self._piles.values():
                cx, cy, cz = pile.center
                dx = point[0] - cx
                dz = point[2] - cz
                dist = math.sqrt(dx * dx + dz * dz)
                if dist <= pile.base_radius and dist < best_dist:
                    best = pile
                    best_dist = dist
            return best

    # ------------------------------------------------------------------
    # Spatial grid (broad phase)
    # ------------------------------------------------------------------

    def _rebuild_spatial_grid(self) -> None:
        """Rebuild the uniform spatial hash grid from current particles."""
        self._grid.clear()
        cell = self._grid_cell_size
        for pid, particle in self._particles.items():
            if particle.is_static:
                continue
            cx = int(math.floor(particle.position[0] / cell))
            cy = int(math.floor(particle.position[1] / cell))
            cz = int(math.floor(particle.position[2] / cell))
            key = (cx, cy, cz)
            bucket = self._grid.get(key)
            if bucket is None:
                bucket = []
                self._grid[key] = bucket
            bucket.append(pid)

    def _grid_neighbors(
        self, particle: GranularParticle
    ) -> List[str]:
        """Return candidate neighbor particle ids from the spatial grid."""
        cell = self._grid_cell_size
        cx = int(math.floor(particle.position[0] / cell))
        cy = int(math.floor(particle.position[1] / cell))
        cz = int(math.floor(particle.position[2] / cell))
        neighbors: List[str] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    key = (cx + dx, cy + dy, cz + dz)
                    bucket = self._grid.get(key)
                    if bucket:
                        neighbors.extend(bucket)
        return neighbors

    # ------------------------------------------------------------------
    # Simulation lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config=None) -> None:
        """Initialize or re-initialize the simulation with optional config."""
        with self._lock:
            if config is not None:
                if isinstance(config, dict):
                    config = GranularConfig.from_dict(config)
                self._config = config
            self._domain = self._config.domain
            self._sim_time = 0.0
            self._tick_count = 0
            self._total_contacts = 0
            self._last_contact_count = 0
            self._last_stats = GranularStats()
            self._rebuild_spatial_grid()

    def tick(self, dt: Optional[float] = None) -> GranularStats:
        """Advance the simulation by one time step.

        Args:
            dt: Time step in seconds. If None, uses the configured time step.

        Returns:
            GranularStats for the completed step.
        """
        if self._paused:
            return self._last_stats
        with self._lock:
            step_dt = float(dt) if dt is not None else self._config.time_step
            if step_dt <= 0.0:
                return self._last_stats

            # Emit from registered sources.
            self.emit_particles(step_dt)

            # Apply external forces (gravity, vibration).
            self.apply_gravity(step_dt)
            if self._config.vibration_amplitude > 0.0:
                self.apply_vibration(step_dt)

            # Integrate particle positions and velocities.
            self.step_particles(step_dt)

            # Resolve contacts and collisions.
            contacts = self.handle_contacts()
            self.resolve_collisions()

            # Apply damping and friction.
            self.apply_friction(step_dt)

            self._sim_time += step_dt
            self._tick_count += 1
            self._total_contacts += contacts
            self._last_contact_count = contacts

            stats = self._compute_stats(contacts)
            self._last_stats = stats
            self._record_event(
                GranularEventKind.SIMULATION_STEP,
                {
                    "dt": step_dt,
                    "contacts": contacts,
                    "particles": stats.particle_count,
                    "sim_time": stats.sim_time,
                },
            )
            return stats

    def step(self, dt: Optional[float] = None) -> GranularStats:
        """Alias for ``tick``."""
        return self.tick(dt)

    def reset(self, reseed: bool = False) -> None:
        """Reset the simulation to an empty state.

        Args:
            reseed: If True, recreate the default seed data after clearing.
        """
        with self._lock:
            self._particles.clear()
            for mat in self._particles_by_material:
                self._particles_by_material[mat] = []
            self._piles.clear()
            self._emitters.clear()
            self._emitter_carry.clear()
            self._obstacles.clear()
            self._grid.clear()
            self._sim_time = 0.0
            self._tick_count = 0
            self._total_contacts = 0
            self._total_avalanches = 0
            self._total_particles_spawned = 0
            self._last_contact_count = 0
            self._last_stats = GranularStats()
            self._paused = False
            self._record_event(GranularEventKind.SYSTEM_RESET, {"reseed": reseed})
            if reseed:
                self._seeded = False
                self._seed_default_data()

    def pause(self) -> None:
        """Pause the simulation; subsequent ticks become no-ops."""
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        """Resume a paused simulation."""
        with self._lock:
            self._paused = False

    def is_paused(self) -> bool:
        """Return True if the simulation is paused."""
        with self._lock:
            return self._paused

    # ------------------------------------------------------------------
    # Force computation and integration
    # ------------------------------------------------------------------

    def compute_forces(self) -> Dict[str, Tuple[float, float, float]]:
        """Compute the net force on each non-static particle.

        Forces include gravity, contact forces (penalty-based), and viscous
        damping. Returns a dict mapping particle_id to a force vector.
        """
        forces: Dict[str, Tuple[float, float, float]] = {}
        gravity_vec = (0.0, -self._config.gravity, 0.0)
        with self._lock:
            for pid, particle in self._particles.items():
                if particle.is_static:
                    continue
                force = _vec_scale(gravity_vec, particle.mass)
                # Damping force: F = -c * v
                damping_force = _vec_scale(particle.velocity, -self._config.damping * particle.mass)
                force = _vec_add(force, damping_force)
                forces[pid] = force
            # Add contact forces.
            contact_forces = self._compute_contact_forces()
            for pid, cf in contact_forces.items():
                base = forces.get(pid, (0.0, 0.0, 0.0))
                forces[pid] = _vec_add(base, cf)
        return forces

    def _compute_contact_forces(self) -> Dict[str, Tuple[float, float, float]]:
        """Compute penalty-based contact forces between particles.

        Uses a normal repulsion proportional to overlap and a tangential
        Coulomb friction force capped by mu * |F_n|.
        """
        forces: Dict[str, Tuple[float, float, float]] = {}
        k = self._config.contact_stiffness
        damping = self._config.damping
        self._rebuild_spatial_grid()
        for pid, particle in self._particles.items():
            if particle.is_static:
                continue
            neighbor_ids = self._grid_neighbors(particle)
            for nid in neighbor_ids:
                if nid <= pid:
                    continue
                other = self._particles.get(nid)
                if other is None:
                    continue
                delta = _vec_sub(other.position, particle.position)
                dist = _vec_length(delta)
                min_dist = particle.radius + other.radius
                if dist >= min_dist or dist < _EPSILON:
                    continue
                n_hat = _vec_normalize(delta)
                overlap = min_dist - dist
                # Normal force magnitude (penalty + viscous damping).
                v_rel = _vec_sub(other.velocity, particle.velocity)
                v_n = _vec_dot(v_rel, n_hat)
                fn_mag = k * overlap + damping * abs(v_n) * (particle.mass + other.mass) * 0.5
                # Coulomb friction.
                v_t = _vec_sub(v_rel, _vec_scale(n_hat, v_n))
                v_t_dir = _vec_normalize(v_t)
                mu = 0.5 * (particle.friction_coef + other.friction_coef)
                if not self._config.use_friction:
                    mu = 0.0
                ft_mag = mu * fn_mag
                # Tangential viscous component for stability.
                kt = k * 0.25
                ft_visc = kt * _vec_length(v_t)
                ft_mag = min(ft_mag, ft_visc)
                fn_vec = _vec_scale(n_hat, fn_mag)
                ft_vec = _vec_scale(v_t_dir, ft_mag)
                # Apply equal and opposite forces.
                f_on_other = _vec_add(fn_vec, ft_vec)
                f_on_self = _vec_scale(f_on_other, -1.0)
                forces[pid] = _vec_add(forces.get(pid, (0.0, 0.0, 0.0)), f_on_self)
                forces[nid] = _vec_add(forces.get(nid, (0.0, 0.0, 0.0)), f_on_other)
                # Cohesion (simple attractive force for cohesive materials).
                if self._config.use_cohesion:
                    cohesion = self._cohesion_between(particle, other)
                    if cohesion > 0.0:
                        cohesion_vec = _vec_scale(n_hat, -cohesion)
                        forces[pid] = _vec_add(forces.get(pid, (0.0, 0.0, 0.0)), _vec_scale(cohesion_vec, -1.0))
                        forces[nid] = _vec_add(forces.get(nid, (0.0, 0.0, 0.0)), cohesion_vec)
        return forces

    def _cohesion_between(
        self, a: GranularParticle, b: GranularParticle
    ) -> float:
        """Return the cohesive attraction magnitude between two particles.

        Based on the average cohesion of their materials scaled by contact
        area. Returns 0.0 if either material has no cohesion.
        """
        props_a = self._materials.get(a.material_type)
        props_b = self._materials.get(b.material_type)
        if props_a is None or props_b is None:
            return 0.0
        cohesion = 0.5 * (props_a.cohesion + props_b.cohesion)
        if cohesion <= 0.0:
            return 0.0
        # Contact area approximation.
        min_dist = a.radius + b.radius
        delta = _vec_sub(b.position, a.position)
        dist = _vec_length(delta)
        overlap = max(0.0, min_dist - dist)
        if overlap <= 0.0:
            return 0.0
        contact_radius = math.sqrt(overlap * min(a.radius, b.radius))
        area = _PI * contact_radius * contact_radius
        return cohesion * area * 1e-3

    def apply_gravity(self, dt: float) -> None:
        """Apply gravitational acceleration to all non-static particles.

        This updates velocities by g * dt. Position integration is performed
        by ``step_particles``.
        """
        if dt <= 0.0:
            return
        g = self._config.gravity
        gravity_vec = (0.0, -g * dt, 0.0)
        with self._lock:
            for particle in self._particles.values():
                if particle.is_static:
                    continue
                particle.velocity = _vec_add(particle.velocity, gravity_vec)

    def apply_friction(self, dt: float) -> None:
        """Apply velocity damping and rolling friction to particles.

        The damping term models air drag and inter-particle viscous losses.
        Rolling friction reduces tangential velocity proportional to the
        normal load (approximated by gravity here).
        """
        if dt <= 0.0:
            return
        damping = self._config.damping
        g = self._config.gravity
        with self._lock:
            for particle in self._particles.values():
                if particle.is_static:
                    continue
                # Linear damping.
                damp_factor = max(0.0, 1.0 - damping * dt)
                particle.velocity = _vec_scale(particle.velocity, damp_factor)
                # Rolling friction: reduce horizontal velocity slightly based
                # on the normal force (mass * g) and friction coefficient.
                rolling_coef = 0.01 * particle.friction_coef
                decel = rolling_coef * g * dt
                speed = _vec_length(particle.velocity)
                if speed > _EPSILON and decel > 0.0:
                    new_speed = max(0.0, speed - decel)
                    scale = new_speed / speed
                    particle.velocity = _vec_scale(particle.velocity, scale)

    def apply_vibration(self, dt: float) -> None:
        """Apply vibration forces to particles (Brazil nut effect driver).

        The vibration is a sinusoidal vertical acceleration applied as an
        impulse to velocities. Used in conjunction with percolation.
        """
        if dt <= 0.0:
            return
        amp = self._config.vibration_amplitude
        freq = self._config.vibration_frequency
        if amp <= 0.0 or freq <= 0.0:
            return
        omega = 2.0 * _PI * freq
        phase = math.sin(omega * self._sim_time)
        accel = amp * omega * omega * phase
        impulse = accel * dt
        with self._lock:
            for particle in self._particles.values():
                if particle.is_static:
                    continue
                # Vertical vibration impulse.
                v = particle.velocity
                particle.velocity = (v[0], v[1] + impulse, v[2])
                # Small random lateral kick to break symmetry.
                import random

                kick = amp * omega * 0.01 * (random.random() - 0.5)
                particle.velocity = (
                    v[0] + kick,
                    particle.velocity[1],
                    v[2] + kick,
                )

    def step_particles(self, dt: float) -> None:
        """Advance particle positions and velocities using velocity-Verlet.

        Velocity-Verlet is symplectic and stable for the stiff contact forces
        used in granular dynamics:

            v(t + dt/2) = v(t) + a(t) * dt/2
            x(t + dt)   = x(t) + v(t + dt/2) * dt
            a(t + dt)   = compute_acceleration(x(t + dt))
            v(t + dt)   = v(t + dt/2) + a(t + dt) * dt/2
        """
        if dt <= 0.0:
            return
        with self._lock:
            # Compute current accelerations from forces.
            forces = self._compute_contact_forces()
            gravity_vec = (0.0, -self._config.gravity, 0.0)
            accels: Dict[str, Tuple[float, float, float]] = {}
            for pid, particle in self._particles.items():
                if particle.is_static:
                    continue
                f = forces.get(pid, (0.0, 0.0, 0.0))
                f = _vec_add(f, _vec_scale(gravity_vec, particle.mass))
                accels[pid] = _vec_scale(f, 1.0 / max(particle.mass, _EPSILON))

            # Half-step velocity update.
            for pid, particle in self._particles.items():
                if particle.is_static:
                    continue
                a = accels.get(pid, (0.0, 0.0, 0.0))
                half_vel = _vec_add(particle.velocity, _vec_scale(a, dt * 0.5))
                # Position update.
                new_pos = _vec_add(particle.position, _vec_scale(half_vel, dt))
                particle.position = new_pos
                particle.velocity = half_vel

            # Recompute accelerations at the new positions.
            forces_new = self._compute_contact_forces()
            accels_new: Dict[str, Tuple[float, float, float]] = {}
            for pid, particle in self._particles.items():
                if particle.is_static:
                    continue
                f = forces_new.get(pid, (0.0, 0.0, 0.0))
                f = _vec_add(f, _vec_scale(gravity_vec, particle.mass))
                accels_new[pid] = _vec_scale(f, 1.0 / max(particle.mass, _EPSILON))

            # Final half-step velocity update.
            for pid, particle in self._particles.items():
                if particle.is_static:
                    continue
                a = accels_new.get(pid, (0.0, 0.0, 0.0))
                particle.velocity = _vec_add(particle.velocity, _vec_scale(a, dt * 0.5))

            # Enforce domain bounds.
            self._enforce_domain_bounds()

    def _enforce_domain_bounds(self) -> None:
        """Clamp particle positions to the simulation domain and reflect."""
        min_x, min_y, min_z, max_x, max_y, max_z = self._domain
        restitution = self._config.global_restitution
        with self._lock:
            for particle in self._particles.values():
                if particle.is_static:
                    continue
                px, py, pz = particle.position
                vx, vy, vz = particle.velocity
                if px < min_x:
                    px = min_x
                    if vx < 0.0:
                        vx = -vx * restitution
                elif px > max_x:
                    px = max_x
                    if vx > 0.0:
                        vx = -vx * restitution
                if py < min_y:
                    py = min_y
                    if vy < 0.0:
                        vy = -vy * restitution
                    # Apply ground friction.
                    if self._config.use_friction:
                        vx *= 1.0 - min(1.0, particle.friction_coef)
                        vz *= 1.0 - min(1.0, particle.friction_coef)
                elif py > max_y:
                    py = max_y
                    if vy > 0.0:
                        vy = -vy * restitution
                if pz < min_z:
                    pz = min_z
                    if vz < 0.0:
                        vz = -vz * restitution
                elif pz > max_z:
                    pz = max_z
                    if vz > 0.0:
                        vz = -vz * restitution
                particle.position = (px, py, pz)
                particle.velocity = (vx, vy, vz)

    # ------------------------------------------------------------------
    # Contact and collision resolution
    # ------------------------------------------------------------------

    def handle_contacts(self) -> int:
        """Detect and resolve particle-particle and particle-boundary contacts.

        Uses the penalty-based contact model with position correction to
        reduce overlap. Returns the number of contacts resolved.
        """
        contact_count = 0
        with self._lock:
            self._rebuild_spatial_grid()
            # Particle-particle contacts.
            resolved: set = set()
            for pid, particle in self._particles.items():
                if particle.is_static:
                    continue
                neighbor_ids = self._grid_neighbors(particle)
                for nid in neighbor_ids:
                    if nid == pid:
                        continue
                    pair_key = (pid, nid) if pid < nid else (nid, pid)
                    if pair_key in resolved:
                        continue
                    other = self._particles.get(nid)
                    if other is None:
                        continue
                    if self._resolve_particle_pair(particle, other):
                        contact_count += 1
                        resolved.add(pair_key)
            # Particle-obstacle contacts.
            for particle in list(self._particles.values()):
                if particle.is_static:
                    continue
                for obstacle in self._obstacles.values():
                    if self._resolve_obstacle_contact(particle, obstacle):
                        contact_count += 1
        self._last_contact_count = contact_count
        return contact_count

    def _resolve_particle_pair(
        self, a: GranularParticle, b: GranularParticle
    ) -> bool:
        """Resolve a single particle-particle contact in place.

        Returns True if a contact was detected and resolved.
        """
        delta = _vec_sub(b.position, a.position)
        dist = _vec_length(delta)
        min_dist = a.radius + b.radius
        if dist >= min_dist or dist < _EPSILON:
            return False
        n_hat = _vec_normalize(delta)
        overlap = min_dist - dist
        # Position correction split by inverse mass.
        inv_a = 0.0 if a.is_static else 1.0 / max(a.mass, _EPSILON)
        inv_b = 0.0 if b.is_static else 1.0 / max(b.mass, _EPSILON)
        inv_sum = inv_a + inv_b
        if inv_sum <= 0.0:
            return True
        correction = _vec_scale(n_hat, overlap / inv_sum)
        if not a.is_static:
            a.position = _vec_sub(a.position, _vec_scale(correction, inv_a))
        if not b.is_static:
            b.position = _vec_add(b.position, _vec_scale(correction, inv_b))
        # Velocity reflection along normal with restitution.
        v_rel = _vec_sub(b.velocity, a.velocity)
        v_n = _vec_dot(v_rel, n_hat)
        if v_n < 0.0:
            restitution = 0.5 * (a.restitution + b.restitution)
            j = -(1.0 + restitution) * v_n / inv_sum
            impulse = _vec_scale(n_hat, j)
            if not a.is_static:
                a.velocity = _vec_sub(a.velocity, _vec_scale(impulse, inv_a))
            if not b.is_static:
                b.velocity = _vec_add(b.velocity, _vec_scale(impulse, inv_b))
            # Tangential friction impulse.
            v_t = _vec_sub(v_rel, _vec_scale(n_hat, v_n))
            v_t_dir = _vec_normalize(v_t)
            mu = 0.5 * (a.friction_coef + b.friction_coef)
            if not self._config.use_friction:
                mu = 0.0
            jt = -_vec_dot(v_rel, v_t_dir) / inv_sum
            jt = max(-mu * abs(j), min(mu * abs(j), jt))
            t_impulse = _vec_scale(v_t_dir, jt)
            if not a.is_static:
                a.velocity = _vec_sub(a.velocity, _vec_scale(t_impulse, inv_a))
            if not b.is_static:
                b.velocity = _vec_add(b.velocity, _vec_scale(t_impulse, inv_b))
        return True

    def _resolve_obstacle_contact(
        self, particle: GranularParticle, obstacle: GranularObstacle
    ) -> bool:
        """Resolve contact between a particle and an obstacle.

        Returns True if a contact was detected and resolved.
        """
        if obstacle.shape == ObstacleShape.BOX:
            return self._resolve_box_contact(particle, obstacle)
        if obstacle.shape == ObstacleShape.SPHERE:
            return self._resolve_sphere_obstacle_contact(particle, obstacle)
        if obstacle.shape == ObstacleShape.CYLINDER:
            return self._resolve_cylinder_contact(particle, obstacle)
        if obstacle.shape == ObstacleShape.PLANE:
            return self._resolve_plane_contact(particle, obstacle)
        return False

    def _resolve_box_contact(
        self, particle: GranularParticle, obstacle: GranularObstacle
    ) -> bool:
        """Resolve contact between a particle and an axis-aligned box.

        The box is treated as a solid volume; particles outside are pushed
        away when they penetrate the surface.
        """
        if len(obstacle.bounds) < 6:
            return False
        min_x, min_y, min_z, max_x, max_y, max_z = obstacle.bounds
        px, py, pz = particle.position
        r = particle.radius
        # Find the closest point on the box to the particle center.
        closest_x = _clamp(px, min_x, max_x)
        closest_y = _clamp(py, min_y, max_y)
        closest_z = _clamp(pz, min_z, max_z)
        delta = (px - closest_x, py - closest_y, pz - closest_z)
        dist = _vec_length(delta)
        # If the particle center is inside the box, push it to the nearest face.
        inside = (min_x <= px <= max_x) and (min_y <= py <= max_y) and (min_z <= pz <= max_z)
        if inside:
            # Compute distances to each face.
            d_pos_x = max_x - px
            d_neg_x = px - min_x
            d_pos_y = max_y - py
            d_neg_y = py - min_y
            d_pos_z = max_z - pz
            d_neg_z = pz - min_z
            min_d = min(d_pos_x, d_neg_x, d_pos_y, d_neg_y, d_pos_z, d_neg_z)
            if min_d == d_pos_x:
                normal = (1.0, 0.0, 0.0)
                penetration = min_d + r
                new_pos = (max_x + r, py, pz)
            elif min_d == d_neg_x:
                normal = (-1.0, 0.0, 0.0)
                penetration = min_d + r
                new_pos = (min_x - r, py, pz)
            elif min_d == d_pos_y:
                normal = (0.0, 1.0, 0.0)
                penetration = min_d + r
                new_pos = (px, max_y + r, pz)
            elif min_d == d_neg_y:
                normal = (0.0, -1.0, 0.0)
                penetration = min_d + r
                new_pos = (px, min_y - r, pz)
            elif min_d == d_pos_z:
                normal = (0.0, 0.0, 1.0)
                penetration = min_d + r
                new_pos = (px, py, max_z + r)
            else:
                normal = (0.0, 0.0, -1.0)
                penetration = min_d + r
                new_pos = (px, py, min_z - r)
            particle.position = new_pos
            self._apply_obstacle_impulse(particle, normal, obstacle)
            return True
        if dist >= r or dist < _EPSILON:
            return False
        normal = _vec_normalize(delta)
        penetration = r - dist
        particle.position = _vec_add(particle.position, _vec_scale(normal, penetration))
        self._apply_obstacle_impulse(particle, normal, obstacle)
        return True

    def _resolve_sphere_obstacle_contact(
        self, particle: GranularParticle, obstacle: GranularObstacle
    ) -> bool:
        """Resolve contact between a particle and a spherical obstacle."""
        if len(obstacle.bounds) < 4:
            return False
        cx, cy, cz, radius = obstacle.bounds[:4]
        center = (cx, cy, cz)
        delta = _vec_sub(particle.position, center)
        dist = _vec_length(delta)
        min_dist = radius + particle.radius
        if dist >= min_dist or dist < _EPSILON:
            return False
        normal = _vec_normalize(delta)
        penetration = min_dist - dist
        particle.position = _vec_add(particle.position, _vec_scale(normal, penetration))
        self._apply_obstacle_impulse(particle, normal, obstacle)
        return True

    def _resolve_cylinder_contact(
        self, particle: GranularParticle, obstacle: GranularObstacle
    ) -> bool:
        """Resolve contact between a particle and a vertical cylinder."""
        if len(obstacle.bounds) < 5:
            return False
        cx, cy, cz, radius, height = obstacle.bounds[:5]
        px, py, pz = particle.position
        r = particle.radius
        # Radial distance from cylinder axis.
        dx = px - cx
        dz = pz - cz
        radial = math.sqrt(dx * dx + dz * dz)
        # Top and bottom caps.
        if py + r < cy or py - r > cy + height:
            return False
        # Side contact.
        if radial >= radius + r or radial < _EPSILON:
            # Check cap contacts.
            if py < cy:
                # Bottom cap.
                if py + r > cy and radial <= radius:
                    normal = (0.0, -1.0, 0.0)
                    penetration = cy - (py - r)
                    particle.position = (px, py - penetration, pz)
                    self._apply_obstacle_impulse(particle, normal, obstacle)
                    return True
                return False
            if py > cy + height:
                if py - r < cy + height and radial <= radius:
                    normal = (0.0, 1.0, 0.0)
                    penetration = (py + r) - (cy + height)
                    particle.position = (px, py - penetration, pz)
                    self._apply_obstacle_impulse(particle, normal, obstacle)
                    return True
                return False
            return False
        if radial > radius:
            # Outside the cylinder laterally.
            penetration = radial - radius
            if penetration >= r:
                return False
            normal = (dx / radial, 0.0, dz / radial)
            push = r - penetration
            particle.position = (px + normal[0] * push, py, pz + normal[2] * push)
            self._apply_obstacle_impulse(particle, normal, obstacle)
            return True
        # Inside the cylinder laterally: push to nearest side.
        normal = (dx / radial, 0.0, dz / radial) if radial > _EPSILON else (1.0, 0.0, 0.0)
        push = radius - radial + r
        particle.position = (px + normal[0] * push, py, pz + normal[2] * push)
        self._apply_obstacle_impulse(particle, normal, obstacle)
        return True

    def _resolve_plane_contact(
        self, particle: GranularParticle, obstacle: GranularObstacle
    ) -> bool:
        """Resolve contact between a particle and an infinite plane.

        The plane is defined by a point and a normal. Particles below the
        plane (in the negative normal direction) are pushed to the surface.
        """
        if len(obstacle.bounds) < 6:
            return False
        px_, py_, pz_ = obstacle.bounds[0], obstacle.bounds[1], obstacle.bounds[2]
        nx_, ny_, nz_ = obstacle.bounds[3], obstacle.bounds[4], obstacle.bounds[5]
        point = (px_, py_, pz_)
        normal = _vec_normalize((nx_, ny_, nz_))
        delta = _vec_sub(particle.position, point)
        signed_dist = _vec_dot(delta, normal)
        if signed_dist >= particle.radius:
            return False
        penetration = particle.radius - signed_dist
        particle.position = _vec_add(
            particle.position, _vec_scale(normal, penetration)
        )
        self._apply_obstacle_impulse(particle, normal, obstacle)
        return True

    def _apply_obstacle_impulse(
        self, particle: GranularParticle,
        normal: Tuple[float, float, float],
        obstacle: GranularObstacle,
    ) -> None:
        """Apply normal restitution and tangential friction to a particle.

        The normal points away from the obstacle surface toward the particle.
        """
        v = particle.velocity
        v_n = _vec_dot(v, normal)
        if v_n < 0.0:
            restitution = particle.restitution
            # Reflect normal velocity.
            v_normal = _vec_scale(normal, v_n)
            v_tangent = _vec_sub(v, v_normal)
            v_normal_new = _vec_scale(v_normal, -restitution)
            # Tangential friction.
            mu = obstacle.friction
            if not self._config.use_friction:
                mu = 0.0
            v_tangent_new = _vec_scale(v_tangent, max(0.0, 1.0 - mu))
            particle.velocity = _vec_add(v_normal_new, v_tangent_new)

    def resolve_collisions(self) -> int:
        """Resolve broad collision constraints including obstacle contacts.

        This is a second pass after ``handle_contacts`` that applies
        additional solver iterations for stability with dense piles.

        Returns the number of additional corrections applied.
        """
        corrections = 0
        with self._lock:
            for _ in range(max(1, self._config.solver_iterations - 1)):
                local_count = 0
                self._rebuild_spatial_grid()
                resolved: set = set()
                for pid, particle in self._particles.items():
                    if particle.is_static:
                        continue
                    neighbor_ids = self._grid_neighbors(particle)
                    for nid in neighbor_ids:
                        if nid == pid:
                            continue
                        pair_key = (pid, nid) if pid < nid else (nid, pid)
                        if pair_key in resolved:
                            continue
                        other = self._particles.get(nid)
                        if other is None:
                            continue
                        if self._resolve_particle_pair(particle, other):
                            local_count += 1
                            resolved.add(pair_key)
                if local_count == 0:
                    break
                corrections += local_count
        return corrections

    # ------------------------------------------------------------------
    # Physics computations: Mohr-Coulomb, angle of repose, avalanches
    # ------------------------------------------------------------------

    def compute_angle_of_repose(
        self, material: GranularMaterial
    ) -> float:
        """Return the angle of repose in degrees for a material.

        For cohesionless materials the angle of repose approximates the
        friction angle. Cohesion increases the stable angle slightly:

            tan(theta) = tan(phi) + 2 * c / (rho * g * d)

        where c is cohesion, rho is bulk density, g is gravity, and d is a
        representative particle diameter.
        """
        material = _coerce_material(material)
        props = self._materials.get(material)
        if props is None:
            return 30.0
        phi = math.radians(props.friction_angle)
        tan_phi = math.tan(phi)
        # Cohesion contribution.
        if props.cohesion > 0.0 and props.density > 0.0:
            d = 0.05  # Representative particle diameter in meters.
            cohesion_term = 2.0 * props.cohesion / (props.density * self._config.gravity * d)
            tan_theta = tan_phi + cohesion_term
        else:
            tan_theta = tan_phi
        theta = math.atan(tan_theta)
        # Cap at a physically reasonable maximum.
        return min(math.degrees(theta), 60.0)

    def simulate_avalanche(
        self, pile_id: str, intensity: float = 1.0
    ) -> int:
        """Trigger an avalanche on a pile and return the particles mobilized.

        Particles above the angle of repose are given a downhill velocity
        proportional to the deviation from the stable angle and the
        ``intensity`` parameter.
        """
        with self._lock:
            pile = self._piles.get(pile_id)
            if pile is None:
                return 0
            stable_angle = self.compute_angle_of_repose(pile.material_type)
            stable_rad = math.radians(stable_angle)
            cx, cy, cz = pile.center
            mobilized = 0
            for pid in list(pile.particles):
                particle = self._particles.get(pid)
                if particle is None or particle.is_static:
                    continue
                px, py, pz = particle.position
                dx = px - cx
                dz = pz - cz
                radial = math.sqrt(dx * dx + dz * dz)
                height_above_base = py - cy
                if radial < _EPSILON or height_above_base <= 0.0:
                    continue
                # Local slope angle approximated by height/radius ratio.
                local_slope = math.atan2(height_above_base, radial)
                if local_slope <= stable_rad:
                    continue
                # Direction of steepest descent (radially outward, downward).
                downhill = _vec_normalize((dx, 0.0, dz))
                deviation = local_slope - stable_rad
                speed = intensity * math.sqrt(2.0 * self._config.gravity * height_above_base) * math.sin(deviation)
                speed = min(speed, 5.0)
                particle.velocity = _vec_add(
                    particle.velocity,
                    _vec_scale(downhill, speed),
                )
                # Reduce vertical velocity slightly to simulate sliding.
                particle.velocity = (
                    particle.velocity[0],
                    particle.velocity[1] - 0.2 * speed,
                    particle.velocity[2],
                )
                mobilized += 1
            if mobilized > 0:
                self._total_avalanches += 1
                self._record_event(
                    GranularEventKind.AVALANCHE_TRIGGERED,
                    {
                        "pile_id": pile_id,
                        "mobilized": mobilized,
                        "intensity": intensity,
                        "stable_angle": stable_angle,
                    },
                )
            return mobilized

    def check_slope_stability(
        self, pile_id: str
    ) -> float:
        """Assess slope stability of a pile.

        Returns a stability factor in [0, 1] where 1.0 is fully stable and
        0.0 means imminent failure. Values are derived from the ratio of
        resisting shear strength to driving shear stress (factor of safety).

        FoS = (c + sigma_n * tan(phi)) / tau
        Stability is the clamped, normalized factor of safety.
        """
        with self._lock:
            pile = self._piles.get(pile_id)
            if pile is None:
                return 1.0
            props = self._materials.get(pile.material_type)
            if props is None:
                return 1.0
            phi = math.radians(props.friction_angle)
            tan_phi = math.tan(phi)
            c = props.cohesion
            cx, cy, cz = pile.center
            # Average driving shear stress approximated from pile geometry.
            # tau ~ rho * g * H * sin(theta) * cos(theta)
            theta = math.radians(pile.angle_of_repose)
            sigma_n = props.density * self._config.gravity * pile.height * math.cos(theta) * math.cos(theta)
            tau = props.density * self._config.gravity * pile.height * math.sin(theta) * math.cos(theta)
            if tau < _EPSILON:
                return 1.0
            fos = (c + sigma_n * tan_phi) / tau
            return _clamp(fos, 0.0, 1.0)

    def compute_stress(
        self,
        point: Tuple[float, float, float],
        radius: float = 0.5,
    ) -> Dict[str, Any]:
        """Compute the local stress tensor at a point using the virial method.

        The virial stress for a set of particles in a region is:

            sigma_ij = (1/V) * sum_p m_p * v_i * v_j
                     + (1/V) * sum_c f_i * r_j

        where V is the region volume, the first sum is over particles in the
        region, and the second sum is over contacts in the region.

        Returns a dict with the 3x3 stress tensor (as nested lists), the
        principal stresses, and the mean and deviatoric stress.
        """
        with self._lock:
            region_volume = (4.0 / 3.0) * _PI * radius * radius * radius
            if region_volume < _EPSILON:
                region_volume = _EPSILON
            # Collect particles in the region.
            in_region: List[GranularParticle] = []
            for particle in self._particles.values():
                delta = _vec_sub(particle.position, point)
                if _vec_length(delta) <= radius:
                    in_region.append(particle)
            # Initialize stress tensor.
            sigma = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
            # Kinetic (velocity) contribution.
            for p in in_region:
                for i in range(3):
                    for j in range(3):
                        sigma[i][j] += p.mass * p.velocity[i] * p.velocity[j]
            # Contact force contribution (pairwise).
            contact_forces = self._compute_contact_forces()
            for pid, particle in self._particles.items():
                if particle not in in_region:
                    continue
                f = contact_forces.get(pid, (0.0, 0.0, 0.0))
                for i in range(3):
                    for j in range(3):
                        sigma[i][j] += 0.5 * f[i] * particle.position[j]
            # Normalize by volume.
            inv_v = 1.0 / region_volume
            for i in range(3):
                for j in range(3):
                    sigma[i][j] *= inv_v
            # Compute principal stresses via eigenvalues of the symmetric tensor.
            principals = self._eigenvalues_3x3_symmetric(sigma)
            principals.sort()
            sigma_1, sigma_2, sigma_3 = principals[2], principals[1], principals[0]
            mean_stress = (sigma_1 + sigma_2 + sigma_3) / 3.0
            deviatoric = sigma_1 - sigma_3
            return {
                "tensor": [[_safe_float(sigma[i][j]) for j in range(3)] for i in range(3)],
                "principal_stresses": [
                    _safe_float(sigma_1),
                    _safe_float(sigma_2),
                    _safe_float(sigma_3),
                ],
                "mean_stress": _safe_float(mean_stress),
                "deviatoric_stress": _safe_float(deviatoric),
                "particle_count": len(in_region),
                "region_volume": _safe_float(region_volume),
            }

    def _eigenvalues_3x3_symmetric(
        self, m: List[List[float]]
    ) -> List[float]:
        """Compute eigenvalues of a 3x3 symmetric matrix.

        Uses the characteristic polynomial and trigonometric solution for
        symmetric matrices to ensure real eigenvalues.
        """
        a = m[0][0]
        b = m[1][1]
        c = m[2][2]
        d = m[0][1]
        e = m[0][2]
        f = m[1][2]
        p1 = d * d + e * e + f * f
        if p1 < _EPSILON:
            # Diagonal matrix.
            return [a, b, c]
        q = (a + b + c) / 3.0
        p2 = (a - q) * (a - q) + (b - q) * (b - q) + (c - q) * (c - q) + 2.0 * p1
        p = math.sqrt(p2 / 6.0)
        if p < _EPSILON:
            return [q, q, q]
        # B = (1/p) * (M - q*I)
        b_matrix = [
            [(a - q) / p, d / p, e / p],
            [d / p, (b - q) / p, f / p],
            [e / p, f / p, (c - q) / p],
        ]
        # det(B) / 2
        det_b = (
            b_matrix[0][0]
            * (b_matrix[1][1] * b_matrix[2][2] - b_matrix[1][2] * b_matrix[2][1])
            - b_matrix[0][1]
            * (b_matrix[1][0] * b_matrix[2][2] - b_matrix[1][2] * b_matrix[2][0])
            + b_matrix[0][2]
            * (b_matrix[1][0] * b_matrix[2][1] - b_matrix[1][1] * b_matrix[2][0])
        )
        r = det_b / 2.0
        r = max(-1.0, min(1.0, r))
        phi = math.acos(r)
        # Eigenvalues.
        eig1 = q + 2.0 * p * math.cos(phi / 3.0)
        eig3 = q + 2.0 * p * math.cos((phi + 2.0 * _PI) / 3.0)
        eig2 = 3.0 * q - eig1 - eig3
        return [eig1, eig2, eig3]

    def compute_yield_criterion(
        self,
        stress: Optional[Dict[str, Any]] = None,
        material: GranularMaterial = GranularMaterial.SAND,
        point: Optional[Tuple[float, float, float]] = None,
    ) -> Dict[str, Any]:
        """Evaluate the Mohr-Coulomb yield criterion.

        f = (sigma_1 - sigma_3) - (sigma_1 + sigma_3) * sin(phi) - 2*c*cos(phi)

        f < 0: stable, f = 0: at yield, f > 0: yielded (failed).

        Compression is taken as positive (geotechnical convention). If
        ``stress`` is None and ``point`` is provided, the stress is computed
        at that point.
        """
        props = self._materials.get(material)
        if props is None:
            props = MaterialProperties(material=material)
        phi = math.radians(props.friction_angle)
        c = props.cohesion
        if stress is None:
            if point is None:
                return {
                    "yield_function": 0.0,
                    "stable": True,
                    "friction_angle": props.friction_angle,
                    "cohesion": c,
                }
            stress = self.compute_stress(point)
        principals = stress.get("principal_stresses", [0.0, 0.0, 0.0])
        if not principals or len(principals) < 3:
            return {
                "yield_function": 0.0,
                "stable": True,
                "friction_angle": props.friction_angle,
                "cohesion": c,
            }
        # Convert to compression-positive convention.
        sigma_1 = -float(principals[0])
        sigma_3 = -float(principals[2])
        sin_phi = math.sin(phi)
        cos_phi = math.cos(phi)
        f = (sigma_1 - sigma_3) - (sigma_1 + sigma_3) * sin_phi - 2.0 * c * cos_phi
        return {
            "yield_function": _safe_float(f),
            "stable": bool(f < 0.0),
            "sigma_1": _safe_float(sigma_1),
            "sigma_3": _safe_float(sigma_3),
            "friction_angle": props.friction_angle,
            "cohesion": c,
            "material": material.value,
        }

    def check_stability(
        self, point: Tuple[float, float, float]
    ) -> Dict[str, Any]:
        """Check stability at a point by computing the yield criterion.

        Uses the dominant material near the point.
        """
        with self._lock:
            # Find the nearest non-static particle to determine the material.
            nearest: Optional[GranularParticle] = None
            nearest_dist = math.inf
            for particle in self._particles.values():
                d = _vec_length(_vec_sub(particle.position, point))
                if d < nearest_dist:
                    nearest_dist = d
                    nearest = particle
            material = nearest.material_type if nearest else GranularMaterial.SAND
            stress = self.compute_stress(point)
            yield_result = self.compute_yield_criterion(stress, material)
            return {
                "point": [float(point[0]), float(point[1]), float(point[2])],
                "material": material.value,
                "yield": yield_result,
                "nearest_particle_distance": _safe_float(nearest_dist),
            }

    # ------------------------------------------------------------------
    # Packing, percolation, flow, pressure
    # ------------------------------------------------------------------

    def compute_packing_density(
        self,
        center: Tuple[float, float, float],
        radius: float,
    ) -> float:
        """Compute the packing fraction in a spherical region.

        phi = sum(particle_volumes) / region_volume

        Capped at the random close packing limit for reporting.
        """
        with self._lock:
            region_volume = (4.0 / 3.0) * _PI * radius * radius * radius
            if region_volume < _EPSILON:
                return 0.0
            total_volume = 0.0
            for particle in self._particles.values():
                delta = _vec_sub(particle.position, center)
                if _vec_length(delta) <= radius:
                    total_volume += particle.volume()
            packing = total_volume / region_volume
            return _clamp(packing, 0.0, self.RANDOM_CLOSE_PACKING)

    def compute_percolation_rate(
        self,
        large_radius: float,
        small_radius: float,
        packing_density: Optional[float] = None,
        material: GranularMaterial = GranularMaterial.SAND,
    ) -> float:
        """Compute the percolation/segregation rate (Brazil nut effect).

        Under vibration, larger particles rise at a rate proportional to the
        vibration energy, the size ratio, and the available free volume:

            dn/dt = k * (A * f)^2 * (r_large/r_small - 1) * (1 - phi/phi_c)

        Returns the rate in meters per second (typical magnitude 1e-4..1e-2).
        """
        props = self._materials.get(material)
        if props is None:
            k = 0.18
        else:
            k = props.percolation_rate
        if small_radius < _EPSILON or large_radius <= small_radius:
            return 0.0
        amp = self._config.vibration_amplitude
        freq = self._config.vibration_frequency
        if amp <= 0.0 or freq <= 0.0:
            # Without vibration, percolation is negligible.
            base_energy = 0.01
        else:
            base_energy = (amp * freq) ** 2
        if packing_density is None:
            packing_density = self.RANDOM_LOOSE_PACKING
        free_volume = max(0.0, 1.0 - packing_density / self.RANDOM_CLOSE_PACKING)
        size_ratio = large_radius / small_radius - 1.0
        rate = k * base_energy * size_ratio * free_volume
        return rate

    def compute_mass_flow_rate(
        self,
        opening_diameter: float,
        material: GranularMaterial = GranularMaterial.SAND,
        particle_diameter: Optional[float] = None,
    ) -> float:
        """Compute the mass flow rate through an orifice (Beverloo law).

        W = C * rho * sqrt(g) * (D - k * d)^(5/2)

        where C is the Beverloo constant (~0.58), k ~ 1.5, D is the opening
        diameter, d is the particle diameter, and rho is the bulk density.

        Returns the mass flow rate in kg/s.
        """
        props = self._materials.get(material)
        rho = props.density if props else 1600.0
        if particle_diameter is None:
            # Estimate from material: larger materials have larger particles.
            if material == GranularMaterial.POWDER or material == GranularMaterial.DUST:
                particle_diameter = 0.003
            elif material == GranularMaterial.SALT:
                particle_diameter = 0.004
            elif material == GranularMaterial.RICE:
                particle_diameter = 0.006
            elif material == GranularMaterial.BEANS:
                particle_diameter = 0.008
            elif material == GranularMaterial.COBBLE or material == GranularMaterial.DEBRIS:
                particle_diameter = 0.018
            else:
                particle_diameter = 0.012
        effective_diameter = opening_diameter - self.BEVERLOO_DIAMETER_FACTOR * particle_diameter
        if effective_diameter <= 0.0:
            return 0.0
        return (
            self.BEVERLOO_CONSTANT
            * rho
            * math.sqrt(self._config.gravity)
            * (effective_diameter ** 2.5)
        )

    def compute_terminal_velocity(
        self,
        particle: Optional[GranularParticle] = None,
        fluid_density: float = 1.225,
        drag_coefficient: Optional[float] = None,
    ) -> float:
        """Compute the terminal velocity of a particle in a fluid.

        v_t = sqrt(2 * m * g / (rho_f * C_d * A))

        where A is the cross-sectional area of the particle.
        """
        if particle is None:
            # Use a default sand-like particle.
            particle = self._make_template_particle(GranularMaterial.SAND)
        if drag_coefficient is None:
            drag_coefficient = self.DRAG_COEFFICIENT_SPHERE
        area = _PI * particle.radius * particle.radius
        denom = fluid_density * drag_coefficient * area
        if denom < _EPSILON:
            return math.inf
        v_t = math.sqrt(2.0 * particle.mass * self._config.gravity / denom)
        return v_t

    def compute_pressure(
        self,
        column_height: float,
        material: GranularMaterial = GranularMaterial.SAND,
        silo_radius: float = 1.0,
        wall_friction: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compute the bottom pressure of a granular column (Janssen effect).

        Unlike a fluid, granular pressure saturates with depth due to wall
        friction redirecting force to the walls:

            P(z) = rho * g * lambda * (1 - exp(-z / lambda))
            lambda = R / (2 * K * mu_wall)

        where K is the Janssen coefficient (~0.4) and mu_wall is the wall
        friction coefficient.

        Returns a dict with the bottom pressure, hydrostatic reference, and
        saturation pressure.
        """
        material = _coerce_material(material)
        props = self._materials.get(material)
        rho = props.density if props else 1600.0
        if wall_friction is None:
            if props is not None:
                wall_friction = math.tan(math.radians(props.friction_angle)) * 0.6
            else:
                wall_friction = 0.3
        if wall_friction < _EPSILON:
            wall_friction = _EPSILON
        lam = silo_radius / (2.0 * self.JANSSEN_COEFFICIENT * wall_friction)
        saturation_pressure = rho * self._config.gravity * lam
        bottom_pressure = saturation_pressure * (1.0 - math.exp(-column_height / lam))
        hydrostatic = rho * self._config.gravity * column_height
        return {
            "bottom_pressure": _safe_float(bottom_pressure),
            "hydrostatic_pressure": _safe_float(hydrostatic),
            "saturation_pressure": _safe_float(saturation_pressure),
            "janssen_length": _safe_float(lam),
            "column_height": _safe_float(column_height),
            "material": material.value,
        }

    # ------------------------------------------------------------------
    # Statistics and status
    # ------------------------------------------------------------------

    def _compute_stats(self, contacts: int) -> GranularStats:
        """Compute the current GranularStats from particle state."""
        particle_count = len(self._particles)
        total_energy = 0.0
        total_speed = 0.0
        moving_count = 0
        for particle in self._particles.values():
            if particle.is_static:
                continue
            total_energy += particle.kinetic_energy()
            speed = _vec_length(particle.velocity)
            total_speed += speed
            moving_count += 1
        avg_velocity = total_speed / moving_count if moving_count > 0 else 0.0
        return GranularStats(
            particle_count=particle_count,
            pile_count=len(self._piles),
            active_contacts=contacts,
            sim_time=self._sim_time,
            total_energy=total_energy,
            avg_velocity=avg_velocity,
        )

    def get_stats(self) -> GranularStats:
        """Return the latest statistics, recomputing if needed."""
        with self._lock:
            return self._compute_stats(self._last_contact_count)

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary summarizing the system state."""
        with self._lock:
            return {
                "initialized": bool(self._initialized),
                "seeded": bool(self._seeded),
                "paused": bool(self._paused),
                "sim_time": _safe_float(self._sim_time),
                "tick_count": int(self._tick_count),
                "particle_count": len(self._particles),
                "pile_count": len(self._piles),
                "emitter_count": len(self._emitters),
                "obstacle_count": len(self._obstacles),
                "material_count": len(self._materials),
                "total_particles_spawned": int(self._total_particles_spawned),
                "total_contacts": int(self._total_contacts),
                "total_avalanches": int(self._total_avalanches),
                "last_contact_count": int(self._last_contact_count),
                "domain": [float(b) for b in self._domain],
                "time_step": _safe_float(self._config.time_step),
                "gravity": _safe_float(self._config.gravity),
            }

    def get_config(self) -> GranularConfig:
        """Return the current configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> None:
        """Update configuration fields by keyword argument.

        Accepts any GranularConfig field name. Unknown keys are ignored.
        Records a CONFIG_CHANGED event.
        """
        with self._lock:
            changes: Dict[str, Any] = {}
            for key, value in kwargs.items():
                if not hasattr(self._config, key):
                    continue
                if key == "domain":
                    value = tuple(float(b) for b in value)
                    self._domain = value
                elif key in ("max_particles", "solver_iterations"):
                    value = int(value)
                elif key in ("use_friction", "use_cohesion"):
                    value = bool(value)
                else:
                    value = float(value)
                setattr(self._config, key, value)
                changes[key] = value
            if changes:
                self._record_event(
                    GranularEventKind.CONFIG_CHANGED,
                    {"changes": changes},
                )

    # ------------------------------------------------------------------
    # Snapshot and serialization
    # ------------------------------------------------------------------

    def get_snapshot(self) -> GranularSnapshot:
        """Return a full snapshot of the current state for serialization."""
        with self._lock:
            return GranularSnapshot(
                sim_time=self._sim_time,
                config=self._config,
                particles=list(self._particles.values()),
                piles=list(self._piles.values()),
                emitters=list(self._emitters.values()),
                obstacles=list(self._obstacles.values()),
                stats=self._compute_stats(self._last_contact_count),
            )

    def get_visualization_data(self) -> Dict[str, Any]:
        """Return data structured for renderer consumption.

        Includes per-particle position, radius, and color, plus obstacle and
        pile outlines. Designed to be directly usable by a rendering layer.
        """
        with self._lock:
            particles_data = []
            for particle in self._particles.values():
                props = self._materials.get(particle.material_type)
                color = props.color if props else "gray"
                particles_data.append(
                    {
                        "id": particle.particle_id,
                        "position": [float(particle.position[0]), float(particle.position[1]), float(particle.position[2])],
                        "radius": _safe_float(particle.radius),
                        "velocity": [float(particle.velocity[0]), float(particle.velocity[1]), float(particle.velocity[2])],
                        "material": particle.material_type.value,
                        "color": color,
                        "is_static": bool(particle.is_static),
                    }
                )
            piles_data = []
            for pile in self._piles.values():
                props = self._materials.get(pile.material_type)
                color = props.color if props else "gray"
                piles_data.append(
                    {
                        "id": pile.pile_id,
                        "name": pile.name,
                        "center": [float(pile.center[0]), float(pile.center[1]), float(pile.center[2])],
                        "height": _safe_float(pile.height),
                        "base_radius": _safe_float(pile.base_radius),
                        "angle_of_repose": _safe_float(pile.angle_of_repose),
                        "color": color,
                        "particle_count": len(pile.particles),
                    }
                )
            obstacles_data = [o.to_dict() for o in self._obstacles.values()]
            emitters_data = [
                {
                    "id": e.emitter_id,
                    "name": e.name,
                    "position": [float(e.position[0]), float(e.position[1]), float(e.position[2])],
                    "rate": _safe_float(e.rate),
                    "material": e.material_type.value,
                }
                for e in self._emitters.values()
            ]
            return {
                "particles": particles_data,
                "piles": piles_data,
                "obstacles": obstacles_data,
                "emitters": emitters_data,
                "stats": self._compute_stats(self._last_contact_count).to_dict(),
                "domain": [float(b) for b in self._domain],
                "sim_time": _safe_float(self._sim_time),
            }

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: GranularEventKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an event in the event log (caller must hold the lock)."""
        event = GranularEvent(
            kind=kind,
            sim_time=self._sim_time,
            payload=payload or {},
        )
        self._events.append(event)
        if len(self._events) > self._max_events:
            # Drop the oldest events to bound memory.
            del self._events[: len(self._events) - self._max_events]

    def list_events(
        self,
        limit: int = 100,
        kind: Optional[GranularEventKind] = None,
    ) -> List[GranularEvent]:
        """Return recent events, optionally filtered by kind.

        Events are returned newest-first.
        """
        with self._lock:
            events = list(self._events)
        if kind is not None:
            events = [e for e in events if e.kind == kind]
        events.reverse()
        if limit > 0:
            events = events[:limit]
        return events

    def clear_events(self) -> int:
        """Clear the event log. Returns the number of events removed."""
        with self._lock:
            count = len(self._events)
            self._events.clear()
            return count

    # ------------------------------------------------------------------
    # AI methods
    # ------------------------------------------------------------------

    def ai_predict_flow(
        self,
        scenario: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Predict granular flow patterns for a hypothetical scenario.

        The prediction uses a simplified kinematic model: the flow direction
        follows the steepest descent of the pile surface, and the flow speed
        scales with the deviation from the angle of repose.

        Scenario keys:
            material: Material to predict for.
            slope_angle: Slope angle in degrees.
            pile_height: Pile height in meters.
            vibration: Optional vibration amplitude in meters.

        Returns a dict with predicted flow direction, speed, mass flux, and
        an avalanche risk score in [0, 1].
        """
        material_raw = scenario.get("material", "sand")
        if isinstance(material_raw, GranularMaterial):
            material = material_raw
        else:
            material = GranularMaterial(str(material_raw))
        slope_angle = float(scenario.get("slope_angle", 30.0))
        pile_height = float(scenario.get("pile_height", 1.0))
        vibration = float(scenario.get("vibration", 0.0))
        props = self._materials.get(material)
        if props is None:
            props = MaterialProperties(material=material)
        repose_angle = self.compute_angle_of_repose(material)
        deviation = slope_angle - repose_angle
        # Flow speed model.
        if deviation <= 0.0:
            flow_speed = 0.0
            avalanche_risk = max(0.0, 0.2 + deviation * 0.01)
        else:
            flow_speed = math.sqrt(2.0 * self._config.gravity * pile_height) * math.sin(math.radians(deviation))
            flow_speed = min(flow_speed, 8.0)
            avalanche_risk = min(1.0, 0.3 + 0.05 * deviation)
        # Vibration increases risk.
        if vibration > 0.0:
            avalanche_risk = min(1.0, avalanche_risk + 0.1 * vibration)
        # Mass flux estimate (kg/s per meter of width).
        mass_flux = props.density * flow_speed * pile_height * 0.5
        prediction = {
            "material": material.value,
            "slope_angle": _safe_float(slope_angle),
            "repose_angle": _safe_float(repose_angle),
            "deviation": _safe_float(deviation),
            "flow_speed": _safe_float(flow_speed),
            "flow_direction": "downslope",
            "mass_flux": _safe_float(mass_flux),
            "avalanche_risk": _safe_float(avalanche_risk),
            "stable": bool(deviation <= 0.0),
        }
        self._record_event(
            GranularEventKind.AI_PREDICTION,
            {"prediction_type": "flow", "scenario": scenario, "result": prediction},
        )
        return prediction

    def ai_optimize_simulation(
        self,
        metric: str = "balance",
    ) -> Dict[str, Any]:
        """Optimize solver parameters for a target metric.

        Supported metrics:
            - "balance": balance accuracy and performance.
            - "accuracy": maximize physical accuracy.
            - "performance": maximize throughput.

        Returns recommended configuration values and the rationale.
        """
        particle_count = len(self._particles)
        current_dt = self._config.time_step
        current_iter = self._config.solver_iterations
        recommended: Dict[str, Any] = {}
        rationale: List[str] = []
        if metric == "accuracy":
            recommended["time_step"] = min(current_dt, 0.008)
            recommended["solver_iterations"] = max(current_iter, 6)
            recommended["contact_stiffness"] = self._config.contact_stiffness * 1.2
            rationale.append("Smaller time step and more solver iterations improve contact resolution.")
        elif metric == "performance":
            recommended["time_step"] = max(current_dt, 0.02)
            recommended["solver_iterations"] = max(1, min(current_iter, 2))
            recommended["contact_stiffness"] = self._config.contact_stiffness * 0.8
            rationale.append("Larger time step and fewer iterations increase throughput.")
        else:  # balance
            if particle_count > 2000:
                recommended["time_step"] = max(0.012, min(current_dt, 0.02))
                recommended["solver_iterations"] = max(2, min(current_iter, 3))
                rationale.append("Large particle count: moderate step and iterations to maintain throughput.")
            else:
                recommended["time_step"] = min(current_dt, 0.012)
                recommended["solver_iterations"] = max(3, min(current_iter + 1, 5))
                rationale.append("Small particle count: tighter step and more iterations for accuracy.")
            recommended["contact_stiffness"] = self._config.contact_stiffness
        # Grid cell size tuning based on average particle radius.
        avg_radius = 0.05
        if self._particles:
            total_r = sum(p.radius for p in self._particles.values())
            avg_radius = total_r / len(self._particles)
        recommended["grid_cell_size"] = max(0.1, avg_radius * 4.0)
        rationale.append("Grid cell size set to roughly four times the average particle radius for broad-phase efficiency.")
        optimization = {
            "metric": metric,
            "particle_count": int(particle_count),
            "current": {
                "time_step": _safe_float(current_dt),
                "solver_iterations": int(current_iter),
                "contact_stiffness": _safe_float(self._config.contact_stiffness),
                "grid_cell_size": _safe_float(self._grid_cell_size),
            },
            "recommended": {k: (_safe_float(v) if isinstance(v, float) else v) for k, v in recommended.items()},
            "rationale": rationale,
        }
        self._record_event(
            GranularEventKind.AI_PREDICTION,
            {"prediction_type": "optimization", "result": optimization},
        )
        return optimization

    def ai_assess_stability(
        self,
        target: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assess the stability of a pile, slope, or region.

        Target keys:
            pile_id: Identifier of a pile to assess.
            point: (x, y, z) point for local stability assessment.
            material: Material for hypothetical assessment.
            slope_angle: Slope angle in degrees for hypothetical assessment.

        Returns a dict with a stability score in [0, 1], the factor of
        safety, failure mode, and recommended remediation.
        """
        pile_id = target.get("pile_id")
        point = target.get("point")
        material_raw = target.get("material", "sand")
        if isinstance(material_raw, GranularMaterial):
            material = material_raw
        else:
            material = GranularMaterial(str(material_raw))
        slope_angle = float(target.get("slope_angle", 30.0))
        result: Dict[str, Any] = {
            "target": target,
            "material": material.value,
        }
        if pile_id is not None:
            with self._lock:
                pile = self._piles.get(str(pile_id))
            if pile is None:
                result["error"] = "pile_not_found"
                result["stability_score"] = 0.0
                return result
            fos = self.check_slope_stability(pile.pile_id)
            repose = self.compute_angle_of_repose(pile.material_type)
            current_angle = pile.angle_of_repose
            deviation = current_angle - repose
            result["stability_score"] = _safe_float(fos)
            result["factor_of_safety"] = _safe_float(fos)
            result["current_angle"] = _safe_float(current_angle)
            result["repose_angle"] = _safe_float(repose)
            result["deviation"] = _safe_float(deviation)
            if fos >= 0.8:
                result["failure_mode"] = "none"
                result["remediation"] = "No action needed."
            elif fos >= 0.5:
                result["failure_mode"] = "marginal"
                result["remediation"] = "Reduce pile height or add containment."
            else:
                result["failure_mode"] = "avalanche_imminent"
                result["remediation"] = "Flatten the pile or trigger a controlled avalanche."
        elif point is not None:
            point_t = (float(point[0]), float(point[1]), float(point[2]))
            stability = self.check_stability(point_t)
            yield_f = stability["yield"]["yield_function"]
            if yield_f is None:
                yield_f = 0.0
            score = _clamp(1.0 - float(yield_f) * 1e-6, 0.0, 1.0)
            result["stability_score"] = _safe_float(score)
            result["yield_function"] = _safe_float(yield_f)
            result["stable"] = bool(yield_f < 0.0)
            result["failure_mode"] = "none" if yield_f < 0.0 else "shear_failure"
            result["remediation"] = "Reduce load or add cohesion." if yield_f >= 0.0 else "No action needed."
        else:
            # Hypothetical slope assessment.
            repose = self.compute_angle_of_repose(material)
            deviation = slope_angle - repose
            props = self._materials.get(material)
            cohesion = props.cohesion if props else 0.0
            if deviation <= 0.0:
                score = 1.0 + 0.02 * (-deviation)
                score = min(1.0, score)
                failure_mode = "none"
                remediation = "Slope is below the angle of repose."
            else:
                score = max(0.0, 1.0 - 0.05 * deviation)
                if cohesion > 0.0:
                    score = min(1.0, score + 0.01 * cohesion / 100.0)
                failure_mode = "avalanche" if deviation > 5.0 else "marginal"
                remediation = "Reduce slope angle below the angle of repose."
            result["stability_score"] = _safe_float(score)
            result["slope_angle"] = _safe_float(slope_angle)
            result["repose_angle"] = _safe_float(repose)
            result["deviation"] = _safe_float(deviation)
            result["failure_mode"] = failure_mode
            result["remediation"] = remediation
        self._record_event(
            GranularEventKind.AI_PREDICTION,
            {"prediction_type": "stability", "result": result},
        )
        return result

    # ------------------------------------------------------------------
    # Aggregate physics queries
    # ------------------------------------------------------------------

    def compute_total_mass(
        self, material: Optional[GranularMaterial] = None
    ) -> float:
        """Return the total mass of particles, optionally filtered by material."""
        if material is not None:
            material = _coerce_material(material)
        with self._lock:
            if material is None:
                return sum(p.mass for p in self._particles.values())
            ids = self._particles_by_material.get(material, [])
            return sum(
                self._particles[pid].mass
                for pid in ids
                if pid in self._particles
            )

    def compute_total_volume(
        self, material: Optional[GranularMaterial] = None
    ) -> float:
        """Return the total particle volume, optionally filtered by material."""
        if material is not None:
            material = _coerce_material(material)
        with self._lock:
            if material is None:
                return sum(p.volume() for p in self._particles.values())
            ids = self._particles_by_material.get(material, [])
            return sum(
                self._particles[pid].volume()
                for pid in ids
                if pid in self._particles
            )

    def compute_kinetic_energy(
        self, material: Optional[GranularMaterial] = None
    ) -> float:
        """Return the total translational kinetic energy in Joules."""
        if material is not None:
            material = _coerce_material(material)
        with self._lock:
            if material is None:
                return sum(
                    p.kinetic_energy() for p in self._particles.values()
                )
            ids = self._particles_by_material.get(material, [])
            return sum(
                self._particles[pid].kinetic_energy()
                for pid in ids
                if pid in self._particles
            )

    def compute_potential_energy(
        self, material: Optional[GranularMaterial] = None
    ) -> float:
        """Return the gravitational potential energy relative to y=0.

        PE = m * g * y, summed over all non-static particles.
        """
        if material is not None:
            material = _coerce_material(material)
        g = self._config.gravity
        with self._lock:
            if material is None:
                return sum(
                    p.mass * g * p.position[1]
                    for p in self._particles.values()
                    if not p.is_static
                )
            ids = self._particles_by_material.get(material, [])
            return sum(
                self._particles[pid].mass * g * self._particles[pid].position[1]
                for pid in ids
                if pid in self._particles and not self._particles[pid].is_static
            )

    def compute_total_energy(
        self, material: Optional[GranularMaterial] = None
    ) -> float:
        """Return the sum of kinetic and potential energy in Joules."""
        if material is not None:
            material = _coerce_material(material)
        return self.compute_kinetic_energy(material) + self.compute_potential_energy(
            material
        )

    def compute_total_momentum(
        self, material: Optional[GranularMaterial] = None
    ) -> Tuple[float, float, float]:
        """Return the total linear momentum vector (kg*m/s)."""
        if material is not None:
            material = _coerce_material(material)
        with self._lock:
            px = 0.0
            py = 0.0
            pz = 0.0
            if material is None:
                iterator: Iterable[GranularParticle] = self._particles.values()
            else:
                ids = self._particles_by_material.get(material, [])
                iterator = (
                    self._particles[pid]
                    for pid in ids
                    if pid in self._particles
                )
            for p in iterator:
                if p.is_static:
                    continue
                px += p.mass * p.velocity[0]
                py += p.mass * p.velocity[1]
                pz += p.mass * p.velocity[2]
            return (px, py, pz)

    def compute_center_of_mass(
        self, material: Optional[GranularMaterial] = None
    ) -> Tuple[float, float, float]:
        """Return the center of mass of the particles.

        Returns (0, 0, 0) if there are no particles.
        """
        if material is not None:
            material = _coerce_material(material)
        with self._lock:
            total_mass = 0.0
            mx = 0.0
            my = 0.0
            mz = 0.0
            if material is None:
                iterator: Iterable[GranularParticle] = self._particles.values()
            else:
                ids = self._particles_by_material.get(material, [])
                iterator = (
                    self._particles[pid]
                    for pid in ids
                    if pid in self._particles
                )
            for p in iterator:
                total_mass += p.mass
                mx += p.mass * p.position[0]
                my += p.mass * p.position[1]
                mz += p.mass * p.position[2]
            if total_mass < _EPSILON:
                return (0.0, 0.0, 0.0)
            return (mx / total_mass, my / total_mass, mz / total_mass)

    def compute_bounding_box(
        self, material: Optional[GranularMaterial] = None
    ) -> Tuple[float, float, float, float, float, float]:
        """Return the axis-aligned bounding box of particle centers.

        Returns (min_x, min_y, min_z, max_x, max_y, max_z). If there are no
        particles, returns the simulation domain bounds.
        """
        with self._lock:
            if material is None:
                iterator: Iterable[GranularParticle] = self._particles.values()
            else:
                ids = self._particles_by_material.get(material, [])
                iterator = (
                    self._particles[pid]
                    for pid in ids
                    if pid in self._particles
                )
            min_x = min_y = min_z = math.inf
            max_x = max_y = max_z = -math.inf
            found = False
            for p in iterator:
                found = True
                px, py, pz = p.position
                if px < min_x:
                    min_x = px
                if py < min_y:
                    min_y = py
                if pz < min_z:
                    min_z = pz
                if px > max_x:
                    max_x = px
                if py > max_y:
                    max_y = py
                if pz > max_z:
                    max_z = pz
            if not found:
                return self._domain
            return (min_x, min_y, min_z, max_x, max_y, max_z)

    def compute_average_speed(
        self, material: Optional[GranularMaterial] = None
    ) -> float:
        """Return the mean speed of non-static particles in m/s."""
        if material is not None:
            material = _coerce_material(material)
        with self._lock:
            if material is None:
                iterator: Iterable[GranularParticle] = self._particles.values()
            else:
                ids = self._particles_by_material.get(material, [])
                iterator = (
                    self._particles[pid]
                    for pid in ids
                    if pid in self._particles
                )
            total = 0.0
            count = 0
            for p in iterator:
                if p.is_static:
                    continue
                total += _vec_length(p.velocity)
                count += 1
            return total / count if count > 0 else 0.0

    def compute_max_speed(
        self, material: Optional[GranularMaterial] = None
    ) -> float:
        """Return the maximum speed of any non-static particle in m/s."""
        if material is not None:
            material = _coerce_material(material)
        with self._lock:
            if material is None:
                iterator: Iterable[GranularParticle] = self._particles.values()
            else:
                ids = self._particles_by_material.get(material, [])
                iterator = (
                    self._particles[pid]
                    for pid in ids
                    if pid in self._particles
                )
            max_speed = 0.0
            for p in iterator:
                if p.is_static:
                    continue
                speed = _vec_length(p.velocity)
                if speed > max_speed:
                    max_speed = speed
            return max_speed

    def compute_material_distribution(self) -> Dict[str, int]:
        """Return a dict mapping material name to active particle count."""
        with self._lock:
            result: Dict[str, int] = {}
            for material in GranularMaterial:
                ids = self._particles_by_material.get(material, [])
                count = sum(1 for pid in ids if pid in self._particles)
                result[material.value] = count
            return result

    def compute_size_distribution(
        self,
        material: Optional[GranularMaterial] = None,
        bins: int = 10,
    ) -> Dict[str, Any]:
        """Return a histogram of particle radii.

        Returns a dict with bin edges, counts, and summary statistics
        (min, max, mean, median radius).
        """
        if material is not None:
            material = _coerce_material(material)
        with self._lock:
            if material is None:
                radii = [p.radius for p in self._particles.values()]
            else:
                ids = self._particles_by_material.get(material, [])
                radii = [
                    self._particles[pid].radius
                    for pid in ids
                    if pid in self._particles
                ]
            if not radii:
                return {
                    "bins": bins,
                    "edges": [],
                    "counts": [],
                    "min": None,
                    "max": None,
                    "mean": None,
                    "median": None,
                }
            r_min = min(radii)
            r_max = max(radii)
            if r_max - r_min < _EPSILON:
                edges = [r_min, r_max + _EPSILON]
                counts = [len(radii)]
            else:
                step = (r_max - r_min) / bins
                edges = [r_min + i * step for i in range(bins + 1)]
                counts = [0] * bins
                for r in radii:
                    idx = int((r - r_min) / step)
                    if idx >= bins:
                        idx = bins - 1
                    counts[idx] += 1
            sorted_radii = sorted(radii)
            n = len(sorted_radii)
            median = sorted_radii[n // 2]
            mean = sum(radii) / n
            return {
                "bins": bins,
                "edges": [_safe_float(e) for e in edges],
                "counts": counts,
                "min": _safe_float(r_min),
                "max": _safe_float(r_max),
                "mean": _safe_float(mean),
                "median": _safe_float(median),
            }

    def get_particle_summary(self) -> Dict[str, Any]:
        """Return an aggregated summary of the particle population."""
        with self._lock:
            count = len(self._particles)
            static_count = sum(
                1 for p in self._particles.values() if p.is_static
            )
            moving_count = count - static_count
            return {
                "total": count,
                "static": static_count,
                "moving": moving_count,
                "total_mass": _safe_float(self.compute_total_mass()),
                "total_volume": _safe_float(self.compute_total_volume()),
                "total_kinetic_energy": _safe_float(self.compute_kinetic_energy()),
                "total_potential_energy": _safe_float(self.compute_potential_energy()),
                "center_of_mass": [
                    _safe_float(v) for v in self.compute_center_of_mass()
                ],
                "bounding_box": [
                    _safe_float(v) for v in self.compute_bounding_box()
                ],
                "average_speed": _safe_float(self.compute_average_speed()),
                "max_speed": _safe_float(self.compute_max_speed()),
                "material_distribution": self.compute_material_distribution(),
            }

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------

    def nearest_particles(
        self,
        point: Tuple[float, float, float],
        k: int = 1,
        material: Optional[GranularMaterial] = None,
    ) -> List[GranularParticle]:
        """Return the k particles nearest to a point, sorted by distance."""
        if k <= 0:
            return []
        with self._lock:
            if material is None:
                candidates: Iterable[GranularParticle] = list(
                    self._particles.values()
                )
            else:
                ids = self._particles_by_material.get(material, [])
                candidates = [
                    self._particles[pid]
                    for pid in ids
                    if pid in self._particles
                ]
            scored: List[Tuple[float, GranularParticle]] = []
            for p in candidates:
                d = _vec_length(_vec_sub(p.position, point))
                scored.append((d, p))
            scored.sort(key=lambda item: item[0])
            return [p for _, p in scored[:k]]

    def particles_in_sphere(
        self,
        center: Tuple[float, float, float],
        radius: float,
        material: Optional[GranularMaterial] = None,
    ) -> List[GranularParticle]:
        """Return all particles whose centers lie within a sphere."""
        with self._lock:
            if material is None:
                iterator: Iterable[GranularParticle] = self._particles.values()
            else:
                ids = self._particles_by_material.get(material, [])
                iterator = (
                    self._particles[pid]
                    for pid in ids
                    if pid in self._particles
                )
            result: List[GranularParticle] = []
            for p in iterator:
                if _vec_length(_vec_sub(p.position, center)) <= radius:
                    result.append(p)
            return result

    def particles_in_box(
        self,
        min_corner: Tuple[float, float, float],
        max_corner: Tuple[float, float, float],
        material: Optional[GranularMaterial] = None,
    ) -> List[GranularParticle]:
        """Return all particles whose centers lie within an axis-aligned box."""
        with self._lock:
            if material is None:
                iterator: Iterable[GranularParticle] = self._particles.values()
            else:
                ids = self._particles_by_material.get(material, [])
                iterator = (
                    self._particles[pid]
                    for pid in ids
                    if pid in self._particles
                )
            result: List[GranularParticle] = []
            for p in iterator:
                px, py, pz = p.position
                if (
                    min_corner[0] <= px <= max_corner[0]
                    and min_corner[1] <= py <= max_corner[1]
                    and min_corner[2] <= pz <= max_corner[2]
                ):
                    result.append(p)
            return result

    # ------------------------------------------------------------------
    # Particle mutation helpers
    # ------------------------------------------------------------------

    def set_particle_position(
        self,
        particle_id: str,
        position: Tuple[float, float, float],
    ) -> bool:
        """Set the position of a particle. Returns True if the particle exists."""
        with self._lock:
            particle = self._particles.get(particle_id)
            if particle is None:
                return False
            particle.position = (
                float(position[0]),
                float(position[1]),
                float(position[2]),
            )
            return True

    def set_particle_velocity(
        self,
        particle_id: str,
        velocity: Tuple[float, float, float],
    ) -> bool:
        """Set the velocity of a particle. Returns True if the particle exists."""
        with self._lock:
            particle = self._particles.get(particle_id)
            if particle is None:
                return False
            particle.velocity = (
                float(velocity[0]),
                float(velocity[1]),
                float(velocity[2]),
            )
            return True

    def apply_impulse(
        self,
        particle_id: str,
        impulse: Tuple[float, float, float],
    ) -> bool:
        """Apply a velocity impulse (delta-v) to a particle.

        The impulse is added directly to the velocity, scaled by inverse mass
        so that the result is a momentum change of m * delta_v.

        Returns True if the particle exists.
        """
        with self._lock:
            particle = self._particles.get(particle_id)
            if particle is None or particle.is_static:
                return False
            delta_v = _vec_scale(impulse, 1.0 / max(particle.mass, _EPSILON))
            particle.velocity = _vec_add(particle.velocity, delta_v)
            return True

    def apply_radial_force(
        self,
        center: Tuple[float, float, float],
        magnitude: float,
        falloff: float = 1.0,
        radius: float = 5.0,
    ) -> int:
        """Apply a radial force field to nearby particles.

        Particles within ``radius`` of ``center`` receive an outward (or
        inward, if magnitude is negative) velocity impulse. The impulse falls
        off linearly with distance, modulated by ``falloff``.

        Returns the number of particles affected.
        """
        affected = 0
        with self._lock:
            for particle in list(self._particles.values()):
                if particle.is_static:
                    continue
                delta = _vec_sub(particle.position, center)
                dist = _vec_length(delta)
                if dist > radius or dist < _EPSILON:
                    continue
                direction = _vec_scale(delta, 1.0 / dist)
                # Linear falloff: 1 at center, 0 at radius.
                strength = magnitude * (1.0 - (dist / radius) * falloff)
                if strength == 0.0:
                    continue
                impulse = _vec_scale(direction, strength)
                delta_v = _vec_scale(impulse, 1.0 / max(particle.mass, _EPSILON))
                particle.velocity = _vec_add(particle.velocity, delta_v)
                affected += 1
        return affected

    def add_particle_at(
        self,
        position: Tuple[float, float, float],
        material: GranularMaterial = GranularMaterial.SAND,
        velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> str:
        """Create and add a particle of the given material at a position.

        Returns the new particle id, or an empty string if the cap is reached.
        """
        material = _coerce_material(material)
        template = self._make_template_particle(material)
        particle = GranularParticle(
            position=(float(position[0]), float(position[1]), float(position[2])),
            velocity=(float(velocity[0]), float(velocity[1]), float(velocity[2])),
            radius=template.radius,
            mass=template.mass,
            density=template.density,
            friction_coef=template.friction_coef,
            restitution=template.restitution,
            material_type=material,
            temperature=template.temperature,
            is_static=False,
        )
        return self.add_particle(particle)

    def spawn_burst(
        self,
        position: Tuple[float, float, float],
        count: int,
        material: GranularMaterial = GranularMaterial.SAND,
        speed: float = 2.0,
    ) -> int:
        """Spawn a burst of particles radiating outward from a point.

        Particles are given random outward velocities with magnitude up to
        ``speed``. Returns the number actually spawned.
        """
        material = _coerce_material(material)
        import random

        spawned = 0
        with self._lock:
            for _ in range(count):
                if len(self._particles) >= self._config.max_particles:
                    break
                # Random direction on a unit sphere.
                theta = 2.0 * _PI * random.random()
                z = 2.0 * random.random() - 1.0
                r = math.sqrt(max(0.0, 1.0 - z * z))
                direction = (r * math.cos(theta), z, r * math.sin(theta))
                vel = _vec_scale(direction, speed * (0.5 + 0.5 * random.random()))
                if self.add_particle_at(position, material, vel):
                    spawned += 1
        return spawned

    # ------------------------------------------------------------------
    # Pile geometry refresh
    # ------------------------------------------------------------------

    def update_pile_geometry(self, pile_id: str) -> bool:
        """Recompute a pile's center, height, and base radius from its particles.

        Useful after simulation steps have moved particles away from their
        original cone layout. Returns True if the pile exists.
        """
        with self._lock:
            pile = self._piles.get(pile_id)
            if pile is None:
                return False
            positions: List[Tuple[float, float, float]] = []
            for pid in pile.particles:
                particle = self._particles.get(pid)
                if particle is not None:
                    positions.append(particle.position)
            if not positions:
                pile.height = 0.0
                pile.base_radius = 0.0
                pile.volume = 0.0
                return True
            cx = sum(p[0] for p in positions) / len(positions)
            cy = sum(p[1] for p in positions) / len(positions)
            cz = sum(p[2] for p in positions) / len(positions)
            min_y = min(p[1] for p in positions)
            max_y = max(p[1] for p in positions)
            height = max_y - min_y
            # Base radius from the maximum radial distance at the base layer.
            base_radius = 0.0
            for p in positions:
                dx = p[0] - cx
                dz = p[2] - cz
                radial = math.sqrt(dx * dx + dz * dz)
                if radial > base_radius:
                    base_radius = radial
            pile.center = (cx, cy, cz)
            pile.height = height
            pile.base_radius = base_radius
            cone_volume = (1.0 / 3.0) * _PI * base_radius * base_radius * height
            pile.volume = cone_volume * self.RANDOM_LOOSE_PACKING
            return True

    def refresh_all_piles(self) -> int:
        """Refresh geometry for every pile. Returns the number refreshed."""
        with self._lock:
            pile_ids = list(self._piles.keys())
        refreshed = 0
        for pile_id in pile_ids:
            if self.update_pile_geometry(pile_id):
                refreshed += 1
        return refreshed

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def export_json(self) -> Dict[str, Any]:
        """Return the full system state as a JSON-serializable dict.

        Equivalent to ``get_snapshot().to_dict()`` but also includes the
        material property table and recent event log.
        """
        with self._lock:
            snapshot = self.get_snapshot()
            data = snapshot.to_dict()
            data["materials"] = {
                m.value: p.to_dict() for m, p in self._materials.items()
            }
            data["events"] = [e.to_dict() for e in self._events[-100:]]
            data["status"] = self.get_status()
            return data

    def import_json(self, data: Dict[str, Any]) -> None:
        """Replace the current state with a snapshot loaded from a dict.

        The configuration, particles, piles, emitters, and obstacles are
        restored. The event log is not restored. Seed data is not recreated.
        """
        with self._lock:
            if "config" in data:
                self._config = GranularConfig.from_dict(data["config"])
                self._domain = self._config.domain
            self._particles.clear()
            for mat in self._particles_by_material:
                self._particles_by_material[mat] = []
            for p_data in data.get("particles", []):
                particle = GranularParticle.from_dict(p_data)
                self._particles[particle.particle_id] = particle
                mat_list = self._particles_by_material.setdefault(
                    particle.material_type, []
                )
                mat_list.append(particle.particle_id)
            self._piles.clear()
            for p_data in data.get("piles", []):
                pile = GranularPile.from_dict(p_data)
                self._piles[pile.pile_id] = pile
            self._emitters.clear()
            self._emitter_carry.clear()
            for e_data in data.get("emitters", []):
                emitter = GranularEmitter.from_dict(e_data)
                self._emitters[emitter.emitter_id] = emitter
                self._emitter_carry[emitter.emitter_id] = 0.0
            self._obstacles.clear()
            for o_data in data.get("obstacles", []):
                obstacle = GranularObstacle.from_dict(o_data)
                self._obstacles[obstacle.obstacle_id] = obstacle
            if "materials" in data:
                for m_name, m_data in data["materials"].items():
                    try:
                        material = GranularMaterial(m_name)
                    except ValueError:
                        continue
                    self._materials[material] = MaterialProperties.from_dict(m_data)
            self._sim_time = float(data.get("sim_time", 0.0))
            self._rebuild_spatial_grid()

    def merge_snapshot(self, snapshot: GranularSnapshot) -> None:
        """Merge a snapshot's particles into the current state.

        Existing particles with the same id are overwritten. Piles, emitters,
        and obstacles are added if not already present. Useful for loading
        incremental checkpoints.
        """
        with self._lock:
            for particle in snapshot.particles:
                if len(self._particles) >= self._config.max_particles:
                    break
                self._particles[particle.particle_id] = particle
                mat_list = self._particles_by_material.setdefault(
                    particle.material_type, []
                )
                if particle.particle_id not in mat_list:
                    mat_list.append(particle.particle_id)
            for pile in snapshot.piles:
                self._piles[pile.pile_id] = pile
            for emitter in snapshot.emitters:
                if emitter.emitter_id not in self._emitters:
                    self._emitters[emitter.emitter_id] = emitter
                    self._emitter_carry[emitter.emitter_id] = 0.0
            for obstacle in snapshot.obstacles:
                self._obstacles[obstacle.obstacle_id] = obstacle

    def validate_state(self) -> Dict[str, Any]:
        """Run sanity checks on the current state.

        Returns a dict with the number of issues found, grouped by category:
        NaN/inf positions, NaN/inf velocities, negative radii/masses, and
        orphaned pile particle references.
        """
        with self._lock:
            bad_positions = 0
            bad_velocities = 0
            negative_radius = 0
            negative_mass = 0
            for p in self._particles.values():
                if any(
                    math.isnan(v) or math.isinf(v) for v in p.position
                ):
                    bad_positions += 1
                if any(
                    math.isnan(v) or math.isinf(v) for v in p.velocity
                ):
                    bad_velocities += 1
                if p.radius <= 0.0:
                    negative_radius += 1
                if p.mass <= 0.0:
                    negative_mass += 1
            orphaned_pile_refs = 0
            for pile in self._piles.values():
                for pid in pile.particles:
                    if pid not in self._particles:
                        orphaned_pile_refs += 1
            issues = bad_positions + bad_velocities + negative_radius + negative_mass + orphaned_pile_refs
            return {
                "valid": issues == 0,
                "total_issues": issues,
                "bad_positions": bad_positions,
                "bad_velocities": bad_velocities,
                "negative_radius": negative_radius,
                "negative_mass": negative_mass,
                "orphaned_pile_refs": orphaned_pile_refs,
                "particle_count": len(self._particles),
                "pile_count": len(self._piles),
            }

    # ------------------------------------------------------------------
    # Contact and vibration helpers
    # ------------------------------------------------------------------

    def get_last_contact_count(self) -> int:
        """Return the number of contacts resolved in the most recent step."""
        with self._lock:
            return self._last_contact_count

    def set_vibration(
        self, amplitude: float, frequency: float
    ) -> None:
        """Configure vibration parameters for the Brazil nut effect driver."""
        self.set_config(
            vibration_amplitude=float(amplitude),
            vibration_frequency=float(frequency),
        )

    def clear_vibration(self) -> None:
        """Disable vibration by setting amplitude and frequency to zero."""
        self.set_vibration(0.0, 0.0)

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def get_sim_time(self) -> float:
        """Return the total simulated time in seconds."""
        with self._lock:
            return self._sim_time

    def get_tick_count(self) -> int:
        """Return the total number of ticks executed."""
        with self._lock:
            return self._tick_count

    def set_gravity(self, gravity: float) -> None:
        """Set the gravitational acceleration magnitude."""
        self.set_config(gravity=gravity)

    def set_time_step(self, dt: float) -> None:
        """Set the simulation time step."""
        self.set_config(time_step=dt)

    def set_domain(
        self,
        domain: Tuple[float, float, float, float, float, float],
    ) -> None:
        """Set the simulation domain bounds."""
        self.set_config(domain=domain)

    def get_domain(self) -> Tuple[float, float, float, float, float, float]:
        """Return the simulation domain bounds."""
        with self._lock:
            return self._domain

    def total_particles_spawned(self) -> int:
        """Return the cumulative count of particles ever spawned."""
        with self._lock:
            return self._total_particles_spawned

    def total_contacts_resolved(self) -> int:
        """Return the cumulative count of contacts resolved."""
        with self._lock:
            return self._total_contacts

    def total_avalanches_triggered(self) -> int:
        """Return the cumulative count of avalanches triggered."""
        with self._lock:
            return self._total_avalanches


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def get_granular_physics() -> _GranularPhysicsSystem:
    """Return the singleton _GranularPhysicsSystem instance.

    This is the primary entry point for the granular physics system.
    """
    return _GranularPhysicsSystem.get_instance()
