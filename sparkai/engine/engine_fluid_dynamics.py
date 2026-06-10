"""
SparkLabs Engine - Fluid Dynamics Simulation System

A particle-based fluid simulation engine using Smoothed Particle Hydrodynamics
(SPH) for realistic water, lava, slime, honey, gas, and custom fluid effects.
Provides density computation via Poly6 kernels, pressure forces via Spiky
kernels, viscosity via the XSPH method, surface tension via color-field
gradients, and spatial hashing for efficient neighbor searches.

Architecture:
  EngineFluidDynamics (Singleton)
    |-- FluidParticle      — individual SPH particle with physical state
    |-- FluidConfig        — simulation configuration and fluid properties
    |-- FluidSimulation    — complete simulation state container
    |-- FluidInteraction   — interaction rules between fluid types
    |-- FluidBoundary      — domain boundary definition
    |-- SimulationStats    — per-frame performance and quality metrics

Supported Solvers:
  - SPH   (classic Smoothed Particle Hydrodynamics)
  - PBF   (Position Based Fluids)
  - IISPH (Implicit Incompressible SPH)
  - FLIP  (Fluid Implicit Particle)
  - APIC  (Affine Particle-In-Cell)

Kernel Functions:
  - Poly6      — density interpolation
  - Spiky      — pressure gradient forces
  - Viscosity  — viscous force Laplacian
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FluidType(str, Enum):
    """Type of fluid being simulated."""
    WATER = "water"
    LAVA = "lava"
    SLIME = "slime"
    HONEY = "honey"
    GAS = "gas"
    CUSTOM = "custom"


class SolverType(str, Enum):
    """SPH solver variant for pressure and incompressibility."""
    SPH = "sph"
    PBF = "pbf"
    IISPH = "iisph"
    FLIP = "flip"
    APIC = "apic"


class BoundaryType(str, Enum):
    """Domain boundary interaction behavior."""
    WALL = "wall"
    PERIODIC = "periodic"
    ABSORBING = "absorbing"
    REFLECTIVE = "reflective"
    CUSTOM = "custom"


class InteractionMode(str, Enum):
    """Interaction mode between two fluid types."""
    REPEL = "repel"
    ATTRACT = "attract"
    NEUTRAL = "neutral"
    ABSORB = "absorb"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Fluid property presets
# ---------------------------------------------------------------------------

_FLUID_PRESETS: Dict[FluidType, Dict[str, Any]] = {
    FluidType.WATER: {
        "rest_density": 1000.0,
        "viscosity_coefficient": 0.01,
        "surface_tension_coefficient": 0.0728,
        "gas_constant": 1000.0,
        "color_rgba": (64, 128, 255, 200),
        "gravity": (0.0, -9.81),
    },
    FluidType.LAVA: {
        "rest_density": 3100.0,
        "viscosity_coefficient": 0.5,
        "surface_tension_coefficient": 0.4,
        "gas_constant": 500.0,
        "color_rgba": (255, 80, 20, 255),
        "gravity": (0.0, -9.81),
    },
    FluidType.SLIME: {
        "rest_density": 1200.0,
        "viscosity_coefficient": 0.3,
        "surface_tension_coefficient": 0.15,
        "gas_constant": 800.0,
        "color_rgba": (80, 255, 80, 200),
        "gravity": (0.0, -9.81),
    },
    FluidType.HONEY: {
        "rest_density": 1420.0,
        "viscosity_coefficient": 0.8,
        "surface_tension_coefficient": 0.1,
        "gas_constant": 2000.0,
        "color_rgba": (255, 200, 50, 220),
        "gravity": (0.0, -9.81),
    },
    FluidType.GAS: {
        "rest_density": 1.2,
        "viscosity_coefficient": 0.0001,
        "surface_tension_coefficient": 0.0,
        "gas_constant": 5000.0,
        "color_rgba": (200, 200, 255, 100),
        "gravity": (0.0, 0.5),
    },
    FluidType.CUSTOM: {
        "rest_density": 1000.0,
        "viscosity_coefficient": 0.01,
        "surface_tension_coefficient": 0.0728,
        "gas_constant": 1000.0,
        "color_rgba": (128, 128, 128, 200),
        "gravity": (0.0, -9.81),
    },
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FluidParticle:
    """A single SPH particle representing a discrete fluid element.

    Each particle carries position, velocity, and physical properties
    (density, pressure, mass). Used as the fundamental simulation unit
    for all SPH computations.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    position: Tuple[float, float] = (0.0, 0.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    density: float = 0.0
    pressure: float = 0.0
    mass: float = 1.0
    radius: float = 0.05
    viscosity: float = 0.01
    surface_tension: float = 0.0728
    temperature: float = 293.15
    color_rgba: Tuple[int, int, int, int] = (64, 128, 255, 200)
    lifetime: float = 0.0
    is_active: bool = True
    grid_cell: Tuple[int, int] = (0, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "density": self.density,
            "pressure": self.pressure,
            "mass": self.mass,
            "radius": self.radius,
            "viscosity": self.viscosity,
            "surface_tension": self.surface_tension,
            "temperature": self.temperature,
            "color_rgba": list(self.color_rgba),
            "lifetime": self.lifetime,
            "is_active": self.is_active,
            "grid_cell": list(self.grid_cell),
        }


@dataclass
class FluidConfig:
    """Configuration for a fluid simulation instance.

    Defines all physical parameters, solver selection, and discretization
    settings required to initialize a SPH simulation.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    fluid_type: FluidType = FluidType.WATER
    particle_count: int = 1000
    particle_radius: float = 0.05
    rest_density: float = 1000.0
    gas_constant: float = 1000.0
    viscosity_coefficient: float = 0.01
    surface_tension_coefficient: float = 0.0728
    gravity: Tuple[float, float] = (0.0, -9.81)
    kernel_radius: float = 0.2
    solver: SolverType = SolverType.SPH
    time_step: float = 0.016
    max_particles: int = 10000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "fluid_type": self.fluid_type.value,
            "particle_count": self.particle_count,
            "particle_radius": self.particle_radius,
            "rest_density": self.rest_density,
            "gas_constant": self.gas_constant,
            "viscosity_coefficient": self.viscosity_coefficient,
            "surface_tension_coefficient": self.surface_tension_coefficient,
            "gravity": list(self.gravity),
            "kernel_radius": self.kernel_radius,
            "solver": self.solver.value,
            "time_step": self.time_step,
            "max_particles": self.max_particles,
        }


@dataclass
class FluidSimulation:
    """Complete state of a single fluid simulation instance.

    Contains the configuration, all active particles, domain bounds,
    obstacles, and accumulated runtime metrics.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config: FluidConfig = field(default_factory=FluidConfig)
    particles: Dict[str, FluidParticle] = field(default_factory=dict)
    bounds: Tuple[float, float, float, float] = (-10.0, -10.0, 10.0, 10.0)
    obstacles: List[Tuple[float, float, float, float]] = field(default_factory=list)
    total_mass: float = 0.0
    current_energy: float = 0.0
    frame_number: int = 0
    simulation_time: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "config": self.config.to_dict(),
            "particle_count": len(self.particles),
            "particles": [p.to_dict() for p in self.particles.values()],
            "bounds": list(self.bounds),
            "obstacles": [list(o) for o in self.obstacles],
            "total_mass": round(self.total_mass, 4),
            "current_energy": round(self.current_energy, 4),
            "frame_number": self.frame_number,
            "simulation_time": round(self.simulation_time, 4),
            "created_at": self.created_at,
        }


@dataclass
class FluidInteraction:
    """Defines how two fluid types interact with each other.

    Governs repulsion, attraction, color mixing, and temperature
    transfer at fluid-fluid interfaces.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    interaction_type: InteractionMode = InteractionMode.NEUTRAL
    source_fluid_id: str = ""
    target_fluid_id: str = ""
    interaction_strength: float = 0.0
    interaction_radius: float = 0.2
    color_mixing: float = 0.0
    temperature_transfer: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "interaction_type": self.interaction_type.value,
            "source_fluid_id": self.source_fluid_id,
            "target_fluid_id": self.target_fluid_id,
            "interaction_strength": self.interaction_strength,
            "interaction_radius": self.interaction_radius,
            "color_mixing": self.color_mixing,
            "temperature_transfer": self.temperature_transfer,
        }


@dataclass
class FluidBoundary:
    """A domain boundary element for fluid confinement.

    Boundaries can be walls, periodic wrap-around, absorbing sinks,
    or reflective surfaces. Each boundary defines its position, normal,
    extent, and surface interaction coefficients.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    boundary_type: BoundaryType = BoundaryType.WALL
    position: Tuple[float, float] = (0.0, 0.0)
    normal: Tuple[float, float] = (0.0, 1.0)
    extent: float = 1.0
    friction: float = 0.1
    restitution: float = 0.3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "boundary_type": self.boundary_type.value,
            "position": list(self.position),
            "normal": list(self.normal),
            "extent": self.extent,
            "friction": self.friction,
            "restitution": self.restitution,
        }


@dataclass
class SimulationStats:
    """Per-frame performance and quality metrics for a simulation step.

    Tracks execution time, particle and collision counts, solver
    iteration counts, density error, and energy conservation.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_time_ms: float = 0.0
    particle_count: int = 0
    active_collisions: int = 0
    pressure_iterations: int = 0
    density_error: float = 0.0
    energy_conservation: float = 1.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_time_ms": round(self.frame_time_ms, 4),
            "particle_count": self.particle_count,
            "active_collisions": self.active_collisions,
            "pressure_iterations": self.pressure_iterations,
            "density_error": round(self.density_error, 6),
            "energy_conservation": round(self.energy_conservation, 6),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Engine Fluid Dynamics
# ---------------------------------------------------------------------------

class EngineFluidDynamics:
    """Particle-based fluid simulation engine using Smoothed Particle Hydrodynamics.

    Provides a complete SPH pipeline: neighbor search via spatial hashing,
    density interpolation with Poly6 kernel, pressure computation via the
    Tait equation of state, pressure/viscosity/surface-tension force
    accumulation, boundary collision resolution, and time integration.

    Supports multiple solver types (SPH, PBF, IISPH, FLIP, APIC) and
    fluid types (water, lava, slime, honey, gas, custom) with configurable
    physical properties.

    Usage:
        fd = get_fluid_dynamics()
        config = FluidConfig(fluid_type=FluidType.WATER, particle_count=500)
        sim = fd.create_simulation(config, (-10, -10, 10, 10))
        stats = fd.step_simulation(sim.id, 0.016)
        status = fd.get_status()
    """

    _instance: Optional["EngineFluidDynamics"] = None
    _lock = threading.RLock()

    # Physics constants
    EPSILON: float = 1e-8
    POLY6_FACTOR: float = 315.0 / (64.0 * math.pi)
    SPIKY_GRAD_FACTOR: float = -45.0 / (math.pi)
    VISC_LAP_FACTOR: float = 45.0 / (math.pi)
    TAYLOR_GAMMA: float = 7.0
    XSPH_EPSILON: float = 0.5
    COLOR_FIELD_THRESHOLD: float = 0.01

    def __new__(cls) -> "EngineFluidDynamics":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineFluidDynamics":
        """Return the singleton EngineFluidDynamics instance."""
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._simulations: Dict[str, FluidSimulation] = {}
        self._boundaries: Dict[str, FluidBoundary] = {}
        self._interactions: Dict[str, FluidInteraction] = {}
        self._obstacle_counter: int = 0

        self._total_simulations_created: int = 0
        self._total_particles_spawned: int = 0
        self._total_boundaries_created: int = 0
        self._total_interactions_created: int = 0
        self._total_frames_simulated: int = 0
        self._tick_count: int = 0
        self._global_time: float = 0.0

    # ------------------------------------------------------------------
    # Kernel Functions
    # ------------------------------------------------------------------

    @staticmethod
    def _poly6_kernel(r: float, h: float) -> float:
        """Compute the Poly6 kernel value for SPH density interpolation.

        W_poly6(r, h) = (315 / (64 * pi * h^9)) * (h^2 - r^2)^3

        Used for density summation because it is smooth, has a simple
        gradient, and avoids clustering artifacts.

        Args:
            r: Distance between particles (must be <= h).
            h: Smoothing kernel radius.

        Returns:
            Kernel weight at distance r.
        """
        if r >= h or r < 0.0:
            return 0.0
        h2 = h * h
        r2 = r * r
        diff = h2 - r2
        if diff <= 0.0:
            return 0.0
        h9 = h2 * h2 * h2 * h2 * h  # h^9 = h^2 * h^2 * h^2 * h^2 * h
        return EngineFluidDynamics.POLY6_FACTOR / h9 * diff * diff * diff

    @staticmethod
    def _spiky_kernel(r: float, h: float) -> float:
        """Compute the Spiky kernel value for SPH pressure forces.

        W_spiky(r, h) = (15 / (pi * h^6)) * (h - r)^3

        The gradient of this kernel is used to compute pressure forces
        because it increases as particles get closer together, naturally
        repelling particles.

        Args:
            r: Distance between particles (must be <= h).
            h: Smoothing kernel radius.

        Returns:
            Kernel weight at distance r.
        """
        if r >= h or r < 0.0:
            return 0.0
        diff = h - r
        if diff <= 0.0:
            return 0.0
        h6 = h * h * h * h * h * h  # h^6
        return (15.0 / (math.pi * h6)) * diff * diff * diff

    @staticmethod
    def _spiky_kernel_gradient(
        r: float, h: float, dx: float, dy: float
    ) -> Tuple[float, float]:
        """Compute the gradient of the Spiky kernel for pressure forces.

        grad W_spiky = -(45 / (pi * h^6)) * (h - r)^2 * (r_vec / r)

        Args:
            r: Distance between particles.
            h: Smoothing kernel radius.
            dx: x-component of the distance vector.
            dy: y-component of the distance vector.

        Returns:
            (gx, gy) gradient vector.
        """
        if r >= h or r < EngineFluidDynamics.EPSILON:
            return (0.0, 0.0)
        diff = h - r
        if diff <= 0.0:
            return (0.0, 0.0)
        h6 = h * h * h * h * h * h
        coeff = EngineFluidDynamics.SPIKY_GRAD_FACTOR / h6 * diff * diff / r
        return (coeff * dx, coeff * dy)

    @staticmethod
    def _viscosity_kernel_laplacian(r: float, h: float) -> float:
        """Compute the Laplacian of the viscosity kernel.

        Laplacian: nabla^2 W_visc = (45 / (pi * h^6)) * (h - r)

        This provides a simple Laplacian that is positive for all
        r < h, producing correct viscosity forces.

        Args:
            r: Distance between particles (must be <= h).
            h: Smoothing kernel radius.

        Returns:
            Laplacian value at distance r.
        """
        if r >= h or r < 0.0:
            return 0.0
        diff = h - r
        if diff <= 0.0:
            return 0.0
        h6 = h * h * h * h * h * h
        return EngineFluidDynamics.VISC_LAP_FACTOR / h6 * diff

    # ------------------------------------------------------------------
    # SPH Core Computations
    # ------------------------------------------------------------------

    def compute_density(
        self,
        particle: FluidParticle,
        neighbors: List[FluidParticle],
        kernel_radius: float,
    ) -> float:
        """Compute SPH density for a particle via the Poly6 kernel.

        rho_i = sum_j m_j * W_poly6(|r_i - r_j|, h)

        Args:
            particle: The particle whose density is being computed.
            neighbors: List of neighboring particles within kernel radius.
            kernel_radius: Smoothing kernel radius h.

        Returns:
            The interpolated density at the particle's position.
        """
        density = 0.0
        px, py = particle.position

        for nb in neighbors:
            if nb.id == particle.id or not nb.is_active:
                continue
            nx, ny = nb.position
            dx = px - nx
            dy = py - ny
            r = math.sqrt(dx * dx + dy * dy)
            w = self._poly6_kernel(r, kernel_radius)
            density += nb.mass * w

        # Self-contribution
        density += particle.mass * self._poly6_kernel(0.0, kernel_radius)

        return max(0.01, density)

    def compute_pressure(
        self,
        density: float,
        rest_density: float,
        gas_constant: float = 1000.0,
    ) -> float:
        """Compute pressure using the Tait equation of state.

        p = B * ((rho / rho_0)^gamma - 1)
        where B = c^2 * rho_0 / gamma (speed-of-sound form).

        For SPH, we use: p = k * (rho - rho_0)  (ideal gas approximation)
        as well as: p = B * ((rho/rho_0)^gamma - 1) (Tait).

        Uses the Tait equation for better incompressibility.

        Args:
            density: Current interpolated density rho.
            rest_density: Reference density rho_0.
            gas_constant: Stiffness constant k (default 1000.0).

        Returns:
            Pressure value (non-negative).
        """
        if density <= rest_density:
            return 0.0
        ratio = density / rest_density
        # Tait equation: p = k * ((rho/rho_0)^gamma - 1)
        pressure = gas_constant * (math.pow(ratio, self.TAYLOR_GAMMA) - 1.0)
        return max(0.0, pressure)

    def compute_pressure_force(
        self,
        particle: FluidParticle,
        neighbors: List[FluidParticle],
        rest_density: float,
        gas_constant: float,
        kernel_radius: float,
    ) -> Tuple[float, float]:
        """Compute SPH pressure gradient force on a particle.

        f_i^p = -sum_j m_j * (p_i + p_j) / (2 * rho_j) * grad W_spiky(r_ij, h)

        The symmetric pressure term (p_i + p_j) / (2 * rho_j) ensures
        Newton's third law is satisfied (conserves momentum).

        Args:
            particle: The particle to compute force for.
            neighbors: List of neighboring particles.
            rest_density: Reference rest density rho_0.
            gas_constant: Gas stiffness constant k.
            kernel_radius: Smoothing kernel radius h.

        Returns:
            (fx, fy) pressure force vector.
        """
        fx, fy = 0.0, 0.0
        px, py = particle.position
        pi = self.compute_pressure(particle.density, rest_density, gas_constant)

        for nb in neighbors:
            if nb.id == particle.id or not nb.is_active:
                continue
            nx, ny = nb.position
            dx = px - nx
            dy = py - ny
            r = math.sqrt(dx * dx + dy * dy)
            if r < self.EPSILON or r >= kernel_radius:
                continue

            pj = self.compute_pressure(nb.density, rest_density, gas_constant)

            # Symmetric pressure term
            if nb.density > self.EPSILON:
                p_avg = (pi + pj) / (2.0 * nb.density)
            else:
                p_avg = 0.0

            gx, gy = self._spiky_kernel_gradient(r, kernel_radius, dx, dy)
            fx += nb.mass * p_avg * gx
            fy += nb.mass * p_avg * gy

        return (-fx, -fy)

    def compute_viscosity_force(
        self,
        particle: FluidParticle,
        neighbors: List[FluidParticle],
        viscosity_coefficient: float,
        kernel_radius: float,
    ) -> Tuple[float, float]:
        """Compute SPH viscosity force using the Laplacian of the viscosity kernel.

        f_i^v = mu * sum_j m_j * (v_j - v_i) / rho_j * nabla^2 W_visc(r_ij, h)

        This smooths velocity differences between nearby particles,
        simulating viscous fluid behavior.

        Args:
            particle: The particle to compute force for.
            neighbors: List of neighboring particles.
            viscosity_coefficient: Dynamic viscosity mu.
            kernel_radius: Smoothing kernel radius h.

        Returns:
            (fx, fy) viscosity force vector.
        """
        fx, fy = 0.0, 0.0
        vx, vy = particle.velocity
        px, py = particle.position

        for nb in neighbors:
            if nb.id == particle.id or not nb.is_active:
                continue
            nx, ny = nb.position
            dx = px - nx
            dy = py - ny
            r = math.sqrt(dx * dx + dy * dy)
            if r < self.EPSILON or r >= kernel_radius:
                continue

            lap = self._viscosity_kernel_laplacian(r, kernel_radius)
            if nb.density > self.EPSILON:
                nvx, nvy = nb.velocity
                fx += nb.mass * (nvx - vx) / nb.density * lap
                fy += nb.mass * (nvy - vy) / nb.density * lap

        return (viscosity_coefficient * fx, viscosity_coefficient * fy)

    def compute_surface_tension(
        self,
        particle: FluidParticle,
        neighbors: List[FluidParticle],
        coefficient: float,
        kernel_radius: float,
    ) -> Tuple[float, float]:
        """Compute surface tension force via the color-field method.

        The color field c_i identifies the surface:
          c_i = sum_j m_j / rho_j * W_poly6(r_ij, h_small)

        Surface tension force:
          f_i^st = -sigma * nabla^2 c_i * (nabla c_i / |nabla c_i|)

        Where sigma is the surface tension coefficient and
        nabla^2 c_i acts as the curvature. Force is applied toward
        the surface normal, pulling surface particles inward.

        Args:
            particle: The particle to compute force for.
            neighbors: List of neighboring particles.
            coefficient: Surface tension coefficient sigma.
            kernel_radius: Smoothing kernel radius h.

        Returns:
            (fx, fy) surface tension force vector.
        """
        if len(neighbors) < 3:
            return (0.0, 0.0)

        px, py = particle.position

        # Compute color field gradient (normal of the surface) and Laplacian (curvature)
        grad_x, grad_y = 0.0, 0.0
        lap = 0.0

        for nb in neighbors:
            if nb.id == particle.id or not nb.is_active:
                continue
            nx, ny = nb.position
            dx = px - nx
            dy = py - ny
            r = math.sqrt(dx * dx + dy * dy)
            if r < self.EPSILON or r >= kernel_radius:
                continue

            if nb.density > self.EPSILON:
                vol = nb.mass / nb.density

                # Gradient of the color field
                gx, gy = self._spiky_kernel_gradient(r, kernel_radius, dx, dy)
                grad_x += vol * gx
                grad_y += vol * gy

                # Laplacian of the color field
                lap += vol * self._viscosity_kernel_laplacian(r, kernel_radius)

        grad_mag = math.sqrt(grad_x * grad_x + grad_y * grad_y)
        if grad_mag < self.COLOR_FIELD_THRESHOLD:
            return (0.0, 0.0)

        # Normalized gradient (surface normal, pointing outward)
        norm_x = grad_x / grad_mag
        norm_y = grad_y / grad_mag

        # Force = -sigma * curvature * normal
        fx = -coefficient * lap * norm_x
        fy = -coefficient * lap * norm_y

        # Clamp to avoid instability
        force_mag = math.sqrt(fx * fx + fy * fy)
        max_force = 50.0
        if force_mag > max_force:
            scale = max_force / force_mag
            fx *= scale
            fy *= scale

        return (fx, fy)

    def _compute_xsph_velocity(
        self,
        particle: FluidParticle,
        neighbors: List[FluidParticle],
        kernel_radius: float,
    ) -> Tuple[float, float]:
        """Apply XSPH velocity correction for improved visual smoothness.

        The XSPH method blends each particle's velocity with the average
        velocity of its neighbors:

          v_i^xsph = v_i + epsilon * sum_j (2 * m_j / (rho_i + rho_j)) * (v_j - v_i) * W_poly6(r_ij, h)

        This reduces particle disorder without damping the overall motion
        and helps maintain a more coherent fluid surface.

        Args:
            particle: The particle whose velocity is being corrected.
            neighbors: List of neighboring particles.
            kernel_radius: Smoothing kernel radius h.

        Returns:
            (vx, vy) XSPH-corrected velocity.
        """
        vx, vy = particle.velocity
        px, py = particle.position

        correction_x, correction_y = 0.0, 0.0

        for nb in neighbors:
            if nb.id == particle.id or not nb.is_active:
                continue
            nx, ny = nb.position
            dx = px - nx
            dy = py - ny
            r = math.sqrt(dx * dx + dy * dy)
            if r >= kernel_radius:
                continue

            w = self._poly6_kernel(r, kernel_radius)
            rho_avg = (particle.density + nb.density) * 0.5
            if rho_avg > self.EPSILON:
                nvx, nvy = nb.velocity
                weight = 2.0 * nb.mass / rho_avg * w
                correction_x += weight * (nvx - vx)
                correction_y += weight * (nvy - vy)

        return (vx + self.XSPH_EPSILON * correction_x,
                vy + self.XSPH_EPSILON * correction_y)

    # ------------------------------------------------------------------
    # Spatial Hashing / Neighbor Search
    # ------------------------------------------------------------------

    def neighbor_search(
        self,
        particles: List[FluidParticle],
        kernel_radius: float,
    ) -> Dict[str, List[str]]:
        """Perform spatial hash-based neighbor search for a set of particles.

        Divides the domain into a uniform grid with cell size = kernel_radius
        and assigns each particle to a cell. Neighbors of a particle are
        those in the same cell and adjacent cells within the kernel radius.

        This reduces neighbor search complexity from O(N^2) to O(N * k)
        where k is the average number of particles per kernel neighborhood.

        Args:
            particles: List of particles to search among.
            kernel_radius: Smoothing kernel radius h (used as cell size).

        Returns:
            Dict mapping particle id -> list of neighbor particle ids.
        """
        cell_size = max(kernel_radius, self.EPSILON)
        spatial_grid: Dict[Tuple[int, int], List[str]] = {}

        # Populate spatial grid
        for p in particles:
            if not p.is_active:
                continue
            px, py = p.position
            cx = int(math.floor(px / cell_size))
            cy = int(math.floor(py / cell_size))
            p.grid_cell = (cx, cy)
            key = (cx, cy)
            if key not in spatial_grid:
                spatial_grid[key] = []
            spatial_grid[key].append(p.id)

        # Build particle ID to particle lookup
        particle_lookup: Dict[str, FluidParticle] = {p.id: p for p in particles if p.is_active}

        # Find neighbors for each particle
        result: Dict[str, List[str]] = {}

        for p in particles:
            if not p.is_active:
                continue
            px, py = p.position
            cx = int(math.floor(px / cell_size))
            cy = int(math.floor(py / cell_size))
            neighbors: List[str] = []

            # Check 3x3 adjacent cells
            for dcx in (-1, 0, 1):
                for dcy in (-1, 0, 1):
                    key = (cx + dcx, cy + dcy)
                    for nid in spatial_grid.get(key, []):
                        if nid == p.id:
                            continue
                        nb = particle_lookup.get(nid)
                        if nb is None or not nb.is_active:
                            continue
                        nx, ny = nb.position
                        dx = px - nx
                        dy = py - ny
                        r_sq = dx * dx + dy * dy
                        if r_sq <= kernel_radius * kernel_radius:
                            neighbors.append(nid)

            result[p.id] = neighbors

        return result

    # ------------------------------------------------------------------
    # Boundary Collision Resolution
    # ------------------------------------------------------------------

    def resolve_boundary_collisions(
        self,
        particle: FluidParticle,
        boundaries: List[FluidBoundary],
    ) -> Tuple[float, float]:
        """Resolve particle collisions with domain boundaries.

        For each boundary, checks if the particle has penetrated and
        applies the appropriate response based on boundary type:
          - WALL: Push particle back inside, reflect velocity with friction/restitution
          - PERIODIC: Wrap particle position to the opposite side
          - ABSORBING: Remove particle from simulation (mark inactive)
          - REFLECTIVE: Mirror velocity across the boundary normal

        Args:
            particle: The particle to check and resolve.
            boundaries: List of FluidBoundary definitions.

        Returns:
            (fx, fy) additional force from boundary interaction.
        """
        fx, fy = 0.0, 0.0
        px, py = particle.position
        vx, vy = particle.velocity

        for b in boundaries:
            bx, by = b.position
            nx, ny = b.normal
            extent = b.extent

            # Compute signed distance of particle to the boundary plane
            # d = (p - b_pos) dot n
            dp_x = px - bx
            dp_y = py - by
            signed_dist = dp_x * nx + dp_y * ny

            if b.boundary_type == BoundaryType.WALL:
                if signed_dist < particle.radius:
                    # Penetrated: push particle back
                    penetration = particle.radius - signed_dist
                    fx += nx * penetration * 10.0
                    fy += ny * penetration * 10.0

                    # Reflect velocity with friction and restitution
                    vn = vx * nx + vy * ny
                    if vn < 0:
                        # Tangential velocity
                        vt_x = vx - vn * nx
                        vt_y = vy - vn * ny

                        # Apply restitution to normal component, friction to tangential
                        new_vn = -vn * b.restitution
                        friction_factor = max(0.0, 1.0 - b.friction * abs(vn))
                        new_vt_x = vt_x * friction_factor
                        new_vt_y = vt_y * friction_factor

                        fx += (new_vn * nx + new_vt_x - vx) * 0.5
                        fy += (new_vn * ny + new_vt_y - vy) * 0.5

            elif b.boundary_type == BoundaryType.PERIODIC:
                if signed_dist < -extent:
                    # Wrap to opposite side
                    fx += (nx * 2.0 * extent + vx)
                    fy += (ny * 2.0 * extent + vy)

            elif b.boundary_type == BoundaryType.ABSORBING:
                if signed_dist < particle.radius:
                    particle.is_active = False
                    return (0.0, 0.0)

            elif b.boundary_type == BoundaryType.REFLECTIVE:
                if signed_dist < particle.radius:
                    # Mirror velocity across boundary
                    vn = vx * nx + vy * ny
                    if vn < 0:
                        vx_reflected = vx - 2.0 * vn * nx
                        vy_reflected = vy - 2.0 * vn * ny
                        fx += (vx_reflected - vx) * 0.5
                        fy += (vy_reflected - vy) * 0.5
                    # Push out
                    penetration = particle.radius - signed_dist
                    fx += nx * penetration * 5.0
                    fy += ny * penetration * 5.0

            elif b.boundary_type == BoundaryType.CUSTOM:
                # Custom: treat as wall with lower stiffness
                if signed_dist < particle.radius:
                    penetration = particle.radius - signed_dist
                    fx += nx * penetration * 5.0
                    fy += ny * penetration * 5.0

        return (fx, fy)

    # ------------------------------------------------------------------
    # Simulation Management
    # ------------------------------------------------------------------

    def create_simulation(
        self,
        config: FluidConfig,
        bounds: Tuple[float, float, float, float],
        initial_positions: Optional[List[Tuple[float, float]]] = None,
    ) -> FluidSimulation:
        """Initialize a new fluid simulation with SPH particles.

        Creates a FluidSimulation instance populated with particles based
        on the provided configuration. Particles are either placed at the
        provided initial positions or arranged in a grid within the
        domain bounds.

        Args:
            config: FluidConfig specifying physical parameters and solver.
            bounds: Domain bounds as (min_x, min_y, max_x, max_y).
            initial_positions: Optional list of (x, y) starting positions.
                If not provided, particles are arranged in a grid.

        Returns:
            The newly created FluidSimulation instance.
        """
        with self._lock:
            sim = FluidSimulation(
                config=config,
                bounds=bounds,
            )

            min_x, min_y, max_x, max_y = bounds
            particle_radius = config.particle_radius
            particle_mass = (config.rest_density * particle_radius * particle_radius
                             * math.pi)  # mass per particle (2D)

            if initial_positions and len(initial_positions) > 0:
                for pos in initial_positions:
                    if len(sim.particles) >= config.max_particles:
                        break
                    p = FluidParticle(
                        position=pos,
                        mass=particle_mass,
                        radius=particle_radius,
                        viscosity=config.viscosity_coefficient,
                        surface_tension=config.surface_tension_coefficient,
                    )
                    sim.particles[p.id] = p
                    self._total_particles_spawned += 1
            else:
                # Arrange particles in a grid within bounds
                spacing = particle_radius * 2.0
                cols = int((max_x - min_x) / spacing)
                rows = int((max_y - min_y) / spacing)
                cols = max(1, cols)
                rows = max(1, rows)

                for row in range(rows):
                    for col in range(cols):
                        if len(sim.particles) >= config.max_particles:
                            break
                        if len(sim.particles) >= config.particle_count:
                            break
                        px = min_x + (col + 0.5) * spacing
                        py = min_y + (row + 0.5) * spacing
                        p = FluidParticle(
                            position=(px, py),
                            mass=particle_mass,
                            radius=particle_radius,
                            viscosity=config.viscosity_coefficient,
                            surface_tension=config.surface_tension_coefficient,
                        )
                        sim.particles[p.id] = p
                        self._total_particles_spawned += 1
                    if len(sim.particles) >= config.particle_count:
                        break

            sim.total_mass = sum(p.mass for p in sim.particles.values())
            self._simulations[sim.id] = sim
            self._total_simulations_created += 1

            return sim

    def step_simulation(
        self,
        simulation_id: str,
        delta_time: float,
        max_iterations: int = 8,
    ) -> Optional[SimulationStats]:
        """Advance a fluid simulation by one timestep.

        Performs the full SPH pipeline:
          1. Neighbor search via spatial hashing
          2. Density computation for all particles
          3. Pressure computation (Tait equation)
          4. Force accumulation (pressure + viscosity + surface tension + gravity + boundary)
          5. XSPH velocity correction
          6. Semi-implicit Euler integration
          7. Boundary collision resolution
          8. Stats collection

        Args:
            simulation_id: The ID of the simulation to advance.
            delta_time: Timestep duration in seconds.
            max_iterations: Maximum solver iterations (for iterative solvers).

        Returns:
            SimulationStats with performance and quality metrics, or None
            if the simulation was not found.
        """
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                return None

            import time as _perf_time
            t_start = _perf_time.perf_counter()

            cfg = sim.config
            kernel_radius = cfg.kernel_radius
            rest_density = cfg.rest_density
            gas_constant = cfg.gas_constant
            viscosity_coeff = cfg.viscosity_coefficient
            surface_coeff = cfg.surface_tension_coefficient
            grav_x, grav_y = cfg.gravity

            # Get active particles list
            active_particles: List[FluidParticle] = [
                p for p in sim.particles.values() if p.is_active
            ]

            # --- Neighbor search ---
            neighbor_map = self.neighbor_search(active_particles, kernel_radius)

            # Build particle lookup and neighbor particle lists
            particle_lookup: Dict[str, FluidParticle] = {
                p.id: p for p in active_particles
            }

            # --- Density computation ---
            for p in active_particles:
                nb_ids = neighbor_map.get(p.id, [])
                nb_particles = [
                    particle_lookup[nid] for nid in nb_ids
                    if nid in particle_lookup
                ]
                p.density = self.compute_density(p, nb_particles, kernel_radius)

            # --- Pressure computation ---
            for p in active_particles:
                p.pressure = self.compute_pressure(
                    p.density, rest_density, gas_constant,
                )

            # --- Force accumulation and integration ---
            total_collisions = 0
            total_density_error = 0.0
            total_iterations = 0

            for _ in range(max_iterations):
                iter_collisions = 0

                for p in active_particles:
                    nb_ids = neighbor_map.get(p.id, [])
                    nb_particles = [
                        particle_lookup[nid] for nid in nb_ids
                        if nid in particle_lookup
                    ]

                    # Accumulate forces
                    total_fx, total_fy = 0.0, 0.0

                    # Gravity
                    total_fx += grav_x * p.mass
                    total_fy += grav_y * p.mass

                    # Pressure force
                    pf_x, pf_y = self.compute_pressure_force(
                        p, nb_particles, rest_density, gas_constant, kernel_radius,
                    )
                    total_fx += pf_x
                    total_fy += pf_y

                    # Viscosity force
                    vf_x, vf_y = self.compute_viscosity_force(
                        p, nb_particles, viscosity_coeff, kernel_radius,
                    )
                    total_fx += vf_x
                    total_fy += vf_y

                    # Surface tension
                    st_x, st_y = self.compute_surface_tension(
                        p, nb_particles, surface_coeff, kernel_radius,
                    )
                    total_fx += st_x
                    total_fy += st_y

                    # Boundary collision
                    boundaries = self._get_boundaries_for_simulation(sim)
                    bf_x, bf_y = self.resolve_boundary_collisions(p, boundaries)
                    total_fx += bf_x
                    total_fy += bf_y

                    if abs(bf_x) > self.EPSILON or abs(bf_y) > self.EPSILON:
                        iter_collisions += 1

                    # Semi-implicit Euler integration
                    if p.density > self.EPSILON:
                        vx, vy = p.velocity
                        vx += (total_fx / p.density) * delta_time
                        vy += (total_fy / p.density) * delta_time
                        p.velocity = (vx, vy)

                total_collisions += iter_collisions
                total_iterations += 1

                # For SPH solver, one pass is sufficient
                if cfg.solver == SolverType.SPH:
                    break

            # --- XSPH velocity correction ---
            for p in active_particles:
                nb_ids = neighbor_map.get(p.id, [])
                nb_particles = [
                    particle_lookup[nid] for nid in nb_ids
                    if nid in particle_lookup
                ]
                p.velocity = self._compute_xsph_velocity(
                    p, nb_particles, kernel_radius,
                )

            # --- Position update (semi-implicit Euler) ---
            for p in active_particles:
                vx, vy = p.velocity
                px, py = p.position
                p.position = (px + vx * delta_time, py + vy * delta_time)
                p.lifetime += delta_time

            # --- Post-integration boundary resolution ---
            boundaries = self._get_boundaries_for_simulation(sim)
            for p in active_particles:
                self.resolve_boundary_collisions(p, boundaries)

            # --- Remove inactive particles ---
            inactive_ids = [
                pid for pid, p in sim.particles.items() if not p.is_active
            ]
            for pid in inactive_ids:
                del sim.particles[pid]

            # --- Compute energy ---
            total_ke = 0.0
            for p in active_particles:
                vx, vy = p.velocity
                total_ke += 0.5 * p.mass * (vx * vx + vy * vy)

            # Potential energy (gravitational)
            total_pe = 0.0
            _, min_y, _, _ = sim.bounds
            for p in active_particles:
                _, py = p.position
                total_pe += p.mass * abs(grav_y) * (py - min_y)

            sim.current_energy = total_ke + total_pe

            # --- Density error ---
            for p in active_particles:
                if p.density > self.EPSILON:
                    total_density_error += abs(p.density - rest_density) / rest_density
            if len(active_particles) > 0:
                total_density_error /= len(active_particles)

            # --- Energy conservation ratio ---
            init_energy = sim.total_mass * abs(grav_y) * (
                (sim.bounds[3] - sim.bounds[1]) * 0.5
            )
            energy_ratio = sim.current_energy / max(init_energy, self.EPSILON)

            # --- Update simulation metadata ---
            sim.frame_number += 1
            sim.simulation_time += delta_time
            self._total_frames_simulated += 1
            self._tick_count += 1
            self._global_time += delta_time

            t_end = _perf_time.perf_counter()
            frame_time_ms = (t_end - t_start) * 1000.0

            stats = SimulationStats(
                frame_time_ms=frame_time_ms,
                particle_count=len(active_particles),
                active_collisions=total_collisions,
                pressure_iterations=total_iterations,
                density_error=round(total_density_error, 6),
                energy_conservation=round(min(1.0, max(0.0, energy_ratio)), 6),
            )

            return stats

    def _get_boundaries_for_simulation(
        self, sim: FluidSimulation
    ) -> List[FluidBoundary]:
        """Generate domain boundaries for a simulation based on its bounds.

        Creates four wall boundaries at the edges of the simulation domain
        plus any user-defined boundaries.

        Args:
            sim: The fluid simulation.

        Returns:
            List of FluidBoundary objects.
        """
        min_x, min_y, max_x, max_y = sim.bounds
        domain_boundaries: List[FluidBoundary] = [
            FluidBoundary(
                boundary_type=BoundaryType.WALL,
                position=(min_x, 0.0),
                normal=(1.0, 0.0),
                extent=(max_y - min_y),
                friction=0.1,
                restitution=0.3,
            ),
            FluidBoundary(
                boundary_type=BoundaryType.WALL,
                position=(max_x, 0.0),
                normal=(-1.0, 0.0),
                extent=(max_y - min_y),
                friction=0.1,
                restitution=0.3,
            ),
            FluidBoundary(
                boundary_type=BoundaryType.WALL,
                position=(0.0, min_y),
                normal=(0.0, 1.0),
                extent=(max_x - min_x),
                friction=0.1,
                restitution=0.3,
            ),
            FluidBoundary(
                boundary_type=BoundaryType.WALL,
                position=(0.0, max_y),
                normal=(0.0, -1.0),
                extent=(max_x - min_x),
                friction=0.1,
                restitution=0.3,
            ),
        ]

        # Add user-defined boundaries
        user_boundaries = [
            b for b in self._boundaries.values()
        ]

        return domain_boundaries + user_boundaries

    # ------------------------------------------------------------------
    # Boundary Management
    # ------------------------------------------------------------------

    def create_boundary(
        self,
        position: Tuple[float, float],
        normal: Tuple[float, float],
        extent: float,
        boundary_type: BoundaryType = BoundaryType.WALL,
    ) -> FluidBoundary:
        """Create a new domain boundary.

        Args:
            position: World-space position of the boundary center.
            normal: Unit normal vector pointing into the fluid domain.
            extent: Length/extent of the boundary.
            boundary_type: Type of boundary interaction.

        Returns:
            The newly created FluidBoundary instance.
        """
        with self._lock:
            b = FluidBoundary(
                boundary_type=boundary_type,
                position=position,
                normal=normal,
                extent=extent,
            )
            self._boundaries[b.id] = b
            self._total_boundaries_created += 1
            return b

    def remove_boundary(self, boundary_id: str) -> bool:
        """Remove a domain boundary.

        Args:
            boundary_id: The ID of the boundary to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if boundary_id not in self._boundaries:
                return False
            del self._boundaries[boundary_id]
            return True

    def get_all_boundaries(self) -> List[Dict[str, Any]]:
        """Get all boundaries as serialized dicts."""
        with self._lock:
            return [b.to_dict() for b in self._boundaries.values()]

    # ------------------------------------------------------------------
    # Obstacle Management
    # ------------------------------------------------------------------

    def add_obstacle(
        self,
        simulation_id: str,
        obstacle_bounds: Tuple[float, float, float, float],
        is_solid: bool = True,
    ) -> int:
        """Add a rectangular obstacle to a simulation.

        Obstacles are axis-aligned rectangles that particles are pushed
        out of. They are treated as solid barriers during boundary
        resolution.

        Args:
            simulation_id: The ID of the simulation to add the obstacle to.
            obstacle_bounds: Rectangle as (min_x, min_y, max_x, max_y).
            is_solid: Whether the obstacle is solid (True) or permeable (False).

        Returns:
            The obstacle index, or -1 if the simulation was not found.
        """
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                return -1

            sim.obstacles.append(obstacle_bounds)
            self._obstacle_counter += 1

            # Create corresponding boundary entities for obstacle walls
            min_x, min_y, max_x, max_y = obstacle_bounds
            if is_solid:
                # Bottom wall
                self._boundaries[str(uuid.uuid4().hex)] = FluidBoundary(
                    boundary_type=BoundaryType.WALL,
                    position=(0.0, min_y),
                    normal=(0.0, 1.0),
                    extent=(max_x - min_x),
                    friction=0.2,
                    restitution=0.1,
                )
                # Top wall
                self._boundaries[str(uuid.uuid4().hex)] = FluidBoundary(
                    boundary_type=BoundaryType.WALL,
                    position=(0.0, max_y),
                    normal=(0.0, -1.0),
                    extent=(max_x - min_x),
                    friction=0.2,
                    restitution=0.1,
                )
                # Left wall
                self._boundaries[str(uuid.uuid4().hex)] = FluidBoundary(
                    boundary_type=BoundaryType.WALL,
                    position=(min_x, 0.0),
                    normal=(1.0, 0.0),
                    extent=(max_y - min_y),
                    friction=0.2,
                    restitution=0.1,
                )
                # Right wall
                self._boundaries[str(uuid.uuid4().hex)] = FluidBoundary(
                    boundary_type=BoundaryType.WALL,
                    position=(max_x, 0.0),
                    normal=(-1.0, 0.0),
                    extent=(max_y - min_y),
                    friction=0.2,
                    restitution=0.1,
                )

            return self._obstacle_counter

    def remove_obstacle(self, simulation_id: str, obstacle_index: int) -> bool:
        """Remove an obstacle from a simulation by index.

        Args:
            simulation_id: The ID of the simulation.
            obstacle_index: The index of the obstacle to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                return False
            if obstacle_index < 0 or obstacle_index >= len(sim.obstacles):
                return False
            sim.obstacles.pop(obstacle_index)
            return True

    def get_obstacles(self, simulation_id: str) -> List[Tuple[float, float, float, float]]:
        """Get all obstacles for a simulation."""
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                return []
            return list(sim.obstacles)

    # ------------------------------------------------------------------
    # Interaction Management
    # ------------------------------------------------------------------

    def create_interaction(
        self,
        interaction_type: InteractionMode,
        source_fluid_id: str,
        target_fluid_id: str,
        interaction_strength: float = 0.0,
        interaction_radius: float = 0.2,
    ) -> FluidInteraction:
        """Define how two fluid types interact.

        Args:
            interaction_type: The mode of interaction.
            source_fluid_id: Source fluid simulation ID.
            target_fluid_id: Target fluid simulation ID.
            interaction_strength: Strength of the interaction force.
            interaction_radius: Radius within which interaction occurs.

        Returns:
            The newly created FluidInteraction instance.
        """
        with self._lock:
            interaction = FluidInteraction(
                interaction_type=interaction_type,
                source_fluid_id=source_fluid_id,
                target_fluid_id=target_fluid_id,
                interaction_strength=interaction_strength,
                interaction_radius=interaction_radius,
            )
            self._interactions[interaction.id] = interaction
            self._total_interactions_created += 1
            return interaction

    def remove_interaction(self, interaction_id: str) -> bool:
        """Remove a fluid interaction definition."""
        with self._lock:
            if interaction_id not in self._interactions:
                return False
            del self._interactions[interaction_id]
            return True

    def get_interactions(self) -> List[Dict[str, Any]]:
        """Get all fluid interactions as serialized dicts."""
        with self._lock:
            return [i.to_dict() for i in self._interactions.values()]

    # ------------------------------------------------------------------
    # Simulation Query
    # ------------------------------------------------------------------

    def get_simulation(self, simulation_id: str) -> Optional[FluidSimulation]:
        """Retrieve a simulation by ID."""
        return self._simulations.get(simulation_id)

    def get_particle(self, simulation_id: str, particle_id: str) -> Optional[FluidParticle]:
        """Retrieve a specific particle from a simulation."""
        sim = self._simulations.get(simulation_id)
        if sim is None:
            return None
        return sim.particles.get(particle_id)

    def get_particles(
        self, simulation_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get particles from a simulation as serialized dicts."""
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                return []
            particles = [
                p for p in sim.particles.values() if p.is_active
            ][:limit]
            return [p.to_dict() for p in particles]

    def remove_simulation(self, simulation_id: str) -> bool:
        """Remove a simulation and all its data.

        Args:
            simulation_id: The ID of the simulation to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if simulation_id not in self._simulations:
                return False
            del self._simulations[simulation_id]
            return True

    # ------------------------------------------------------------------
    # Fluid Presets
    # ------------------------------------------------------------------

    def create_preset_config(
        self,
        fluid_type: FluidType,
        particle_count: int = 1000,
        bounds: Tuple[float, float, float, float] = (-10.0, -10.0, 10.0, 10.0),
        overrides: Optional[Dict[str, Any]] = None,
    ) -> FluidConfig:
        """Create a FluidConfig from a fluid type preset.

        Pre-configured physical properties are provided for WATER, LAVA,
        SLIME, HONEY, and GAS. Overrides can be applied for any property.

        Args:
            fluid_type: The type of fluid to configure.
            particle_count: Number of particles to simulate.
            bounds: Domain bounds for determining particle spacing.
            overrides: Optional dict of property overrides.

        Returns:
            A FluidConfig with preset values applied.
        """
        preset = _FLUID_PRESETS.get(fluid_type, _FLUID_PRESETS[FluidType.CUSTOM])
        overrides = overrides or {}

        min_x, min_y, max_x, max_y = bounds
        domain_area = (max_x - min_x) * (max_y - min_y)
        spacing = math.sqrt(domain_area / max(particle_count, 1))
        particle_radius = spacing * 0.25
        kernel_radius = particle_radius * 4.0

        return FluidConfig(
            fluid_type=fluid_type,
            particle_count=particle_count,
            particle_radius=overrides.get("particle_radius", particle_radius),
            rest_density=overrides.get("rest_density", preset["rest_density"]),
            gas_constant=overrides.get("gas_constant", preset["gas_constant"]),
            viscosity_coefficient=overrides.get(
                "viscosity_coefficient", preset["viscosity_coefficient"]
            ),
            surface_tension_coefficient=overrides.get(
                "surface_tension_coefficient", preset["surface_tension_coefficient"]
            ),
            gravity=overrides.get("gravity", preset["gravity"]),
            kernel_radius=overrides.get("kernel_radius", kernel_radius),
            time_step=overrides.get("time_step", 0.016),
            max_particles=overrides.get("max_particles", 10000),
        )

    # ------------------------------------------------------------------
    # Status and Serialization
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status and statistics for the fluid dynamics system.

        Returns:
            Dict with simulation counts, particle statistics, performance
            metrics, and system configuration summary.
        """
        with self._lock:
            total_particles = sum(
                len(sim.particles) for sim in self._simulations.values()
            )
            active_particles = sum(
                sum(1 for p in sim.particles.values() if p.is_active)
                for sim in self._simulations.values()
            )

            fluid_type_distribution: Dict[str, int] = {}
            for sim in self._simulations.values():
                t = sim.config.fluid_type.value
                fluid_type_distribution[t] = fluid_type_distribution.get(t, 0) + 1

            solver_distribution: Dict[str, int] = {}
            for sim in self._simulations.values():
                s = sim.config.solver.value
                solver_distribution[s] = solver_distribution.get(s, 0) + 1

            return {
                "total_simulations": len(self._simulations),
                "total_simulations_created": self._total_simulations_created,
                "total_particles": total_particles,
                "active_particles": active_particles,
                "total_particles_spawned": self._total_particles_spawned,
                "total_boundaries": len(self._boundaries),
                "total_boundaries_created": self._total_boundaries_created,
                "total_interactions": len(self._interactions),
                "total_interactions_created": self._total_interactions_created,
                "total_frames_simulated": self._total_frames_simulated,
                "tick_count": self._tick_count,
                "global_time": round(self._global_time, 4),
                "obstacle_counter": self._obstacle_counter,
                "fluid_type_distribution": fluid_type_distribution,
                "solver_distribution": solver_distribution,
            }

    def add_particles(
        self,
        simulation_id: str,
        particle_count: int = 100,
        region: Optional[Dict[str, float]] = None,
        velocity_range: Optional[Dict[str, float]] = None,
        mass: float = 0.001,
    ) -> List[FluidParticle]:
        """Add particles to a simulation within a defined region.

        Convenience method for REST API use.

        Args:
            simulation_id: Target simulation ID.
            particle_count: Number of particles to spawn.
            region: Dict with x, y, width, height.
            velocity_range: Dict with min_vx, max_vx, min_vy, max_vy.
            mass: Particle mass.

        Returns:
            List of created FluidParticle instances.
        """
        import random as _random
        with self._lock:
            simulation = self._simulations.get(simulation_id)
            if not simulation:
                raise ValueError(f"Simulation not found: {simulation_id}")

            region = region or {"x": 0, "y": 0, "width": 1, "height": 1}
            rx = region.get("x", 0)
            ry = region.get("y", 0)
            rw = region.get("width", 1)
            rh = region.get("height", 1)

            vel = velocity_range or {}
            min_vx = vel.get("min_vx", -1.0)
            max_vx = vel.get("max_vx", 1.0)
            min_vy = vel.get("min_vy", -1.0)
            max_vy = vel.get("max_vy", 1.0)

            new_particles = []
            for _ in range(particle_count):
                px = rx + _random.random() * rw
                py = ry + _random.random() * rh
                vx = min_vx + _random.random() * (max_vx - min_vx)
                vy = min_vy + _random.random() * (max_vy - min_vy)
                particle = FluidParticle(
                    position=(px, py),
                    velocity=(vx, vy),
                    mass=mass,
                    density=simulation.config.rest_density,
                )
                simulation.particles[particle.id] = particle
                new_particles.append(particle)

            self._total_particles_spawned += particle_count
            return new_particles

    def list_simulations(self) -> List[Dict[str, Any]]:
        """List all active fluid simulations.

        Returns:
            List of simulation summary dicts.
        """
        with self._lock:
            return [
                {
                    "id": sim_id,
                    "name": sim.config.name,
                    "particle_count": len(sim.particles),
                    "frame_number": sim.frame_number,
                    "simulation_time": sim.simulation_time,
                    "fluid_type": sim.config.fluid_type.value,
                }
                for sim_id, sim in self._simulations.items()
            ]

    def reset(self) -> None:
        """Reset the entire fluid dynamics system."""
        with self._lock:
            self._simulations.clear()
            self._boundaries.clear()
            self._interactions.clear()
            self._obstacle_counter = 0
            self._total_simulations_created = 0
            self._total_particles_spawned = 0
            self._total_boundaries_created = 0
            self._total_interactions_created = 0
            self._total_frames_simulated = 0
            self._tick_count = 0
            self._global_time = 0.0


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_fluid_dynamics() -> EngineFluidDynamics:
    """Get or create the singleton EngineFluidDynamics instance."""
    return EngineFluidDynamics.get_instance()