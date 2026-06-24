"""
SparkLabs Engine - Fluid Simulation Engine

Real-time 2D fluid dynamics using grid-based Navier-Stokes simulation.
Supports velocity fields, density advection, diffusion, external forces,
and particle-based visualization.

Architecture:
  FluidSimulationEngine (Singleton)
    |-- FluidGrid       — grid-based velocity, density, and pressure fields
    |-- FluidParticle   — Lagrangian particles for visualization
    |-- FluidSource     — continuous emission of density and velocity
    |-- FluidObstacle   — solid boundaries affecting flow

Simulation Pipeline (Stam-style):
  1. Add Forces    — apply external forces (gravity, wind, user input)
  2. Advect        — transport velocity and density along the velocity field
  3. Diffuse       — simulate viscous diffusion
  4. Project       — enforce incompressibility via pressure solve
  5. Emit Particles — generate Lagrangian particles for rendering
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

class FluidSolverType(Enum):
    """Type of fluid simulation solver."""
    STAM = "stam"
    PIC = "pic"
    FLIP = "flip"
    SPH = "sph"


class BoundaryType(Enum):
    """Type of boundary condition at grid edges."""
    WALL = "wall"
    PERIODIC = "periodic"
    OUTFLOW = "outflow"
    INFLOW = "inflow"
    NONE = "none"


class FluidDomain(Enum):
    """Shape of the simulation domain."""
    SQUARE = "square"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FluidGrid:
    """Grid-based fluid field storing velocity, density, pressure, and divergence."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    width: int = 64
    height: int = 64
    cell_size: float = 1.0
    velocity_x: List[List[float]] = field(default_factory=list)
    velocity_y: List[List[float]] = field(default_factory=list)
    density: List[List[float]] = field(default_factory=list)
    pressure: List[List[float]] = field(default_factory=list)
    divergence: List[List[float]] = field(default_factory=list)
    boundary_type: BoundaryType = BoundaryType.WALL
    solver_type: FluidSolverType = FluidSolverType.STAM
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.velocity_x:
            self.velocity_x = [[0.0] * self.width for _ in range(self.height)]
        if not self.velocity_y:
            self.velocity_y = [[0.0] * self.width for _ in range(self.height)]
        if not self.density:
            self.density = [[0.0] * self.width for _ in range(self.height)]
        if not self.pressure:
            self.pressure = [[0.0] * self.width for _ in range(self.height)]
        if not self.divergence:
            self.divergence = [[0.0] * self.width for _ in range(self.height)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "cell_size": self.cell_size,
            "boundary_type": self.boundary_type.value,
            "solver_type": self.solver_type.value,
            "total_cells": self.width * self.height,
            "metadata": dict(self.metadata),
        }


@dataclass
class FluidParticle:
    """A Lagrangian particle for fluid visualization."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    position_x: float = 0.0
    position_y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    density: float = 0.0
    pressure: float = 0.0
    mass: float = 1.0
    lifetime: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position_x": round(self.position_x, 4),
            "position_y": round(self.position_y, 4),
            "velocity_x": round(self.velocity_x, 4),
            "velocity_y": round(self.velocity_y, 4),
            "density": round(self.density, 4),
            "pressure": round(self.pressure, 4),
            "mass": self.mass,
            "lifetime": round(self.lifetime, 4),
            "metadata": dict(self.metadata),
        }


@dataclass
class FluidSource:
    """A continuous source that emits density and velocity into the fluid field."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    position_x: float = 0.0
    position_y: float = 0.0
    radius: float = 1.0
    emission_rate: float = 1.0
    density: float = 1.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "radius": self.radius,
            "emission_rate": self.emission_rate,
            "density": self.density,
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
            "is_active": self.is_active,
            "metadata": dict(self.metadata),
        }


@dataclass
class FluidObstacle:
    """A solid obstacle that blocks fluid flow."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    is_solid: bool = True
    friction: float = 0.5
    bounce_factor: float = 0.3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "vertex_count": len(self.vertices),
            "is_solid": self.is_solid,
            "friction": self.friction,
            "bounce_factor": self.bounce_factor,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Fluid Simulation Engine
# ---------------------------------------------------------------------------

class FluidSimulationEngine:
    """
    Real-time 2D fluid dynamics simulation engine.

    Implements a Stam-style grid-based Navier-Stokes solver with velocity
    advection, viscous diffusion, pressure projection, and external force
    application. Supports particle-based visualization through Lagrangian
    particle emission and advection.
    """

    _instance: Optional["FluidSimulationEngine"] = None
    _lock = threading.RLock()

    _DEFAULT_GRID_SIZE: int = 64
    _DEFAULT_VISCOSITY: float = 0.0001
    _DEFAULT_DIFFUSION: float = 0.00001
    _DEFAULT_DENSITY_DECAY: float = 0.999
    _DEFAULT_MAX_PARTICLES: int = 10000
    _DEFAULT_PARTICLE_LIFETIME: float = 5.0

    def __new__(cls) -> "FluidSimulationEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "FluidSimulationEngine":
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

        self._grids: Dict[str, FluidGrid] = {}
        self._particles: Dict[str, FluidParticle] = {}
        self._sources: Dict[str, FluidSource] = {}
        self._obstacles: Dict[str, FluidObstacle] = {}
        self._viscosity: float = self._DEFAULT_VISCOSITY
        self._diffusion: float = self._DEFAULT_DIFFUSION
        self._density_decay: float = self._DEFAULT_DENSITY_DECAY
        self._step_count: int = 0
        self._total_particles_emitted: int = 0
        self._creation_time: float = time.time()

    # ------------------------------------------------------------------
    # Grid Management
    # ------------------------------------------------------------------

    def create_grid(
        self,
        width: int = _DEFAULT_GRID_SIZE,
        height: int = _DEFAULT_GRID_SIZE,
        cell_size: float = 1.0,
        boundary_type: BoundaryType = BoundaryType.WALL,
        solver_type: FluidSolverType = FluidSolverType.STAM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FluidGrid:
        """Create a new fluid simulation grid.

        Args:
            width: Number of cells horizontally.
            height: Number of cells vertically.
            cell_size: Physical size of each cell.
            boundary_type: Boundary condition at domain edges.
            solver_type: The simulation algorithm to use.
            metadata: Optional arbitrary metadata.

        Returns:
            The newly created FluidGrid.
        """
        with self._lock:
            grid = FluidGrid(
                width=width,
                height=height,
                cell_size=cell_size,
                boundary_type=boundary_type,
                solver_type=solver_type,
                metadata=metadata or {},
            )
            self._grids[grid.id] = grid
            return grid

    def get_grid(self, grid_id: str) -> Optional[FluidGrid]:
        """Get a fluid grid by its ID."""
        return self._grids.get(grid_id)

    # ------------------------------------------------------------------
    # Source Management
    # ------------------------------------------------------------------

    def create_source(
        self,
        position_x: float,
        position_y: float,
        radius: float = 1.0,
        emission_rate: float = 1.0,
        density: float = 1.0,
        velocity_x: float = 0.0,
        velocity_y: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FluidSource:
        """Create a fluid source that emits density and velocity into a grid.

        Args:
            position_x: X position of the source center.
            position_y: Y position of the source center.
            radius: Emission radius in grid cells.
            emission_rate: Rate of density emission per step.
            density: Density value emitted per cell.
            velocity_x: X velocity of emitted fluid.
            velocity_y: Y velocity of emitted fluid.
            metadata: Optional arbitrary metadata.

        Returns:
            The newly created FluidSource.
        """
        with self._lock:
            source = FluidSource(
                position_x=position_x,
                position_y=position_y,
                radius=radius,
                emission_rate=emission_rate,
                density=density,
                velocity_x=velocity_x,
                velocity_y=velocity_y,
                metadata=metadata or {},
            )
            self._sources[source.id] = source
            return source

    def set_source_active(self, source_id: str, active: bool) -> bool:
        """Enable or disable a fluid source."""
        source = self._sources.get(source_id)
        if source is None:
            return False
        source.is_active = active
        return True

    # ------------------------------------------------------------------
    # Obstacle Management
    # ------------------------------------------------------------------

    def add_obstacle(
        self,
        vertices: List[Tuple[float, float]],
        is_solid: bool = True,
        friction: float = 0.5,
        bounce_factor: float = 0.3,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FluidObstacle:
        """Add a solid obstacle that blocks fluid flow.

        Args:
            vertices: List of (x, y) vertices defining the obstacle shape.
            is_solid: Whether the obstacle is fully solid.
            friction: Friction coefficient for velocity damping.
            bounce_factor: Velocity reflection coefficient at boundaries.
            metadata: Optional arbitrary metadata.

        Returns:
            The newly created FluidObstacle.
        """
        with self._lock:
            obstacle = FluidObstacle(
                vertices=list(vertices),
                is_solid=is_solid,
                friction=friction,
                bounce_factor=bounce_factor,
                metadata=metadata or {},
            )
            self._obstacles[obstacle.id] = obstacle
            return obstacle

    def remove_obstacle(self, obstacle_id: str) -> bool:
        """Remove an obstacle from the simulation."""
        with self._lock:
            if obstacle_id in self._obstacles:
                del self._obstacles[obstacle_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Particle Management
    # ------------------------------------------------------------------

    def add_particles(
        self,
        grid_id: str,
        count: int,
        position_x: float = 0.0,
        position_y: float = 0.0,
        velocity_x: float = 0.0,
        velocity_y: float = 0.0,
        spread: float = 0.5,
        lifetime: float = _DEFAULT_PARTICLE_LIFETIME,
    ) -> int:
        """Add Lagrangian particles to the simulation for visualization.

        Particles are emitted around the given position with random spread.

        Args:
            grid_id: The grid to associate particles with.
            count: Number of particles to emit.
            position_x: Center X position for emission.
            position_y: Center Y position for emission.
            velocity_x: Base X velocity for particles.
            velocity_y: Base Y velocity for particles.
            spread: Random spread radius for particle positions.
            lifetime: How long each particle lives in seconds.

        Returns:
            The number of particles actually added (limited by max).
        """
        with self._lock:
            current_count = len(self._particles)
            available = max(0, self._DEFAULT_MAX_PARTICLES - current_count)
            count = min(count, available)

            for _ in range(count):
                import random
                px = position_x + random.uniform(-spread, spread)
                py = position_y + random.uniform(-spread, spread)
                vx = velocity_x + random.uniform(-0.1, 0.1)
                vy = velocity_y + random.uniform(-0.1, 0.1)

                particle = FluidParticle(
                    position_x=px,
                    position_y=py,
                    velocity_x=vx,
                    velocity_y=vy,
                    density=grid_id,  # Store grid_id in density for lookup
                    lifetime=lifetime,
                    metadata={"grid_id": grid_id},
                )
                self._particles[particle.id] = particle
                self._total_particles_emitted += 1

            return count

    def get_particles(self, grid_id: Optional[str] = None) -> List[FluidParticle]:
        """Get all particles, optionally filtered by grid ID."""
        with self._lock:
            if grid_id is None:
                return list(self._particles.values())
            return [
                p for p in self._particles.values()
                if p.metadata.get("grid_id") == grid_id
            ]

    # ------------------------------------------------------------------
    # Simulation Step
    # ------------------------------------------------------------------

    def step(
        self,
        grid_id: str,
        delta_time: float = 0.016,
        num_iterations: int = 4,
    ) -> Optional[FluidGrid]:
        """Advance the fluid simulation by one time step.

        Performs the full Stam-style pipeline:
        1. Apply source emissions
        2. Apply external forces
        3. Advect velocity and density
        4. Diffuse velocity
        5. Project to enforce incompressibility
        6. Advect particles

        Args:
            grid_id: The grid to simulate.
            delta_time: Time step in seconds.
            num_iterations: Number of Jacobi iterations for diffusion/projection.

        Returns:
            The updated FluidGrid, or None if the grid doesn't exist.
        """
        with self._lock:
            grid = self._grids.get(grid_id)
            if grid is None:
                return None

            dt = max(0.0001, min(0.1, delta_time))

            # Apply sources
            self._apply_sources(grid, dt)

            # Apply obstacle boundaries
            self._apply_obstacles(grid)

            # Advect velocity
            self.advect(grid, dt)

            # Diffuse velocity
            self.diffuse(grid, dt, num_iterations)

            # Project to enforce incompressibility
            self.project(grid, num_iterations)

            # Decay density
            self._decay_density(grid)

            # Advect particles
            self._advect_particles(grid, dt)

            self._step_count += 1
            return grid

    # ------------------------------------------------------------------
    # Advection
    # ------------------------------------------------------------------

    def advect(self, grid: FluidGrid, delta_time: float) -> None:
        """Advect velocity and density fields along the velocity field.

        Uses semi-Lagrangian back-tracing to find the source of fluid
        arriving at each cell.
        """
        dt = delta_time
        w = grid.width
        h = grid.height

        new_vx = [[0.0] * w for _ in range(h)]
        new_vy = [[0.0] * w for _ in range(h)]
        new_density = [[0.0] * w for _ in range(h)]

        for y in range(h):
            for x in range(w):
                # Back-trace the position
                back_x = x - grid.velocity_x[y][x] * dt
                back_y = y - grid.velocity_y[y][x] * dt

                # Clamp to grid boundaries
                back_x = max(0.5, min(w - 1.5, back_x))
                back_y = max(0.5, min(h - 1.5, back_y))

                # Bilinear interpolation
                ix0 = int(back_x)
                iy0 = int(back_y)
                ix1 = ix0 + 1
                iy1 = iy0 + 1

                fx = back_x - ix0
                fy = back_y - iy0

                ix0 = max(0, min(w - 1, ix0))
                iy0 = max(0, min(h - 1, iy0))
                ix1 = max(0, min(w - 1, ix1))
                iy1 = max(0, min(h - 1, iy1))

                # Interpolate velocity X
                vx00 = grid.velocity_x[iy0][ix0]
                vx10 = grid.velocity_x[iy0][ix1]
                vx01 = grid.velocity_x[iy1][ix0]
                vx11 = grid.velocity_x[iy1][ix1]
                new_vx[y][x] = (
                    vx00 * (1.0 - fx) * (1.0 - fy)
                    + vx10 * fx * (1.0 - fy)
                    + vx01 * (1.0 - fx) * fy
                    + vx11 * fx * fy
                )

                # Interpolate velocity Y
                vy00 = grid.velocity_y[iy0][ix0]
                vy10 = grid.velocity_y[iy0][ix1]
                vy01 = grid.velocity_y[iy1][ix0]
                vy11 = grid.velocity_y[iy1][ix1]
                new_vy[y][x] = (
                    vy00 * (1.0 - fx) * (1.0 - fy)
                    + vy10 * fx * (1.0 - fy)
                    + vy01 * (1.0 - fx) * fy
                    + vy11 * fx * fy
                )

                # Interpolate density
                d00 = grid.density[iy0][ix0]
                d10 = grid.density[iy0][ix1]
                d01 = grid.density[iy1][ix0]
                d11 = grid.density[iy1][ix1]
                new_density[y][x] = (
                    d00 * (1.0 - fx) * (1.0 - fy)
                    + d10 * fx * (1.0 - fy)
                    + d01 * (1.0 - fx) * fy
                    + d11 * fx * fy
                )

        grid.velocity_x = new_vx
        grid.velocity_y = new_vy
        grid.density = new_density

    # ------------------------------------------------------------------
    # Diffusion
    # ------------------------------------------------------------------

    def diffuse(
        self, grid: FluidGrid, delta_time: float, num_iterations: int = 4
    ) -> None:
        """Simulate viscous diffusion of the velocity field.

        Uses Gauss-Seidel relaxation to solve the diffusion equation.
        """
        w = grid.width
        h = grid.height
        visc = self._viscosity
        a = delta_time * visc * w * h

        for _ in range(num_iterations):
            for y in range(1, h - 1):
                for x in range(1, w - 1):
                    grid.velocity_x[y][x] = (
                        grid.velocity_x[y][x]
                        + a
                        * (
                            grid.velocity_x[y - 1][x]
                            + grid.velocity_x[y + 1][x]
                            + grid.velocity_x[y][x - 1]
                            + grid.velocity_x[y][x + 1]
                            - 4.0 * grid.velocity_x[y][x]
                        )
                    ) / (1.0 + 4.0 * a)

                    grid.velocity_y[y][x] = (
                        grid.velocity_y[y][x]
                        + a
                        * (
                            grid.velocity_y[y - 1][x]
                            + grid.velocity_y[y + 1][x]
                            + grid.velocity_y[y][x - 1]
                            + grid.velocity_y[y][x + 1]
                            - 4.0 * grid.velocity_y[y][x]
                        )
                    ) / (1.0 + 4.0 * a)

        self._set_boundary(grid)

    # ------------------------------------------------------------------
    # Projection (Incompressibility)
    # ------------------------------------------------------------------

    def project(self, grid: FluidGrid, num_iterations: int = 4) -> None:
        """Enforce incompressibility by solving the pressure Poisson equation.

        Computes the divergence of the velocity field, solves for pressure
        using Gauss-Seidel relaxation, then subtracts the pressure gradient
        from the velocity field.
        """
        w = grid.width
        h = grid.height

        # Compute divergence
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                grid.divergence[y][x] = -0.5 * (
                    (grid.velocity_x[y][x + 1] - grid.velocity_x[y][x - 1])
                    + (grid.velocity_y[y + 1][x] - grid.velocity_y[y - 1][x])
                ) / w

                grid.pressure[y][x] = 0.0

        self._set_boundary_pressure(grid)

        # Gauss-Seidel relaxation for pressure
        for _ in range(num_iterations):
            for y in range(1, h - 1):
                for x in range(1, w - 1):
                    grid.pressure[y][x] = 0.25 * (
                        grid.divergence[y][x]
                        + grid.pressure[y - 1][x]
                        + grid.pressure[y + 1][x]
                        + grid.pressure[y][x - 1]
                        + grid.pressure[y][x + 1]
                    )

            self._set_boundary_pressure(grid)

        # Subtract pressure gradient from velocity
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                grid.velocity_x[y][x] -= 0.5 * w * (grid.pressure[y][x + 1] - grid.pressure[y][x - 1])
                grid.velocity_y[y][x] -= 0.5 * h * (grid.pressure[y + 1][x] - grid.pressure[y - 1][x])

        self._set_boundary(grid)

    # ------------------------------------------------------------------
    # Force Application
    # ------------------------------------------------------------------

    def apply_force(
        self,
        grid_id: str,
        force_x: float,
        force_y: float,
        position_x: Optional[float] = None,
        position_y: Optional[float] = None,
        radius: float = 1.0,
    ) -> bool:
        """Apply an external force to the velocity field.

        If position is specified, the force is applied in a circular region
        around that position. Otherwise, it's applied globally.

        Args:
            grid_id: The target grid.
            force_x: X component of the force.
            force_y: Y component of the force.
            position_x: Optional X center of application region.
            position_y: Optional Y center of application region.
            radius: Radius of the application region.

        Returns:
            True if the force was applied, False if the grid was not found.
        """
        with self._lock:
            grid = self._grids.get(grid_id)
            if grid is None:
                return False

            w = grid.width
            h = grid.height

            if position_x is None or position_y is None:
                # Global force
                for y in range(1, h - 1):
                    for x in range(1, w - 1):
                        grid.velocity_x[y][x] += force_x
                        grid.velocity_y[y][x] += force_y
            else:
                # Localized force
                gx = int(position_x)
                gy = int(position_y)
                r = int(radius)
                for y in range(max(1, gy - r), min(h - 1, gy + r + 1)):
                    for x in range(max(1, gx - r), min(w - 1, gx + r + 1)):
                        dx = x - position_x
                        dy = y - position_y
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist <= radius:
                            falloff = 1.0 - dist / max(radius, 0.01)
                            grid.velocity_x[y][x] += force_x * falloff
                            grid.velocity_y[y][x] += force_y * falloff

            return True

    # ------------------------------------------------------------------
    # Source Application
    # ------------------------------------------------------------------

    def _apply_sources(self, grid: FluidGrid, delta_time: float) -> None:
        """Apply all active fluid sources to the grid."""
        w = grid.width
        h = grid.height

        for source in self._sources.values():
            if not source.is_active:
                continue

            gx = int(source.position_x)
            gy = int(source.position_y)
            r = int(source.radius)

            for y in range(max(1, gy - r), min(h - 1, gy + r + 1)):
                for x in range(max(1, gx - r), min(w - 1, gx + r + 1)):
                    dx = x - source.position_x
                    dy = y - source.position_y
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist <= source.radius:
                        falloff = 1.0 - dist / max(source.radius, 0.01)
                        grid.density[y][x] += source.density * source.emission_rate * delta_time * falloff
                        grid.velocity_x[y][x] += source.velocity_x * delta_time * falloff
                        grid.velocity_y[y][x] += source.velocity_y * delta_time * falloff

    # ------------------------------------------------------------------
    # Obstacle Handling
    # ------------------------------------------------------------------

    def _apply_obstacles(self, grid: FluidGrid) -> None:
        """Apply obstacle boundaries to zero out velocity in solid cells."""
        w = grid.width
        h = grid.height

        for obstacle in self._obstacles.values():
            if not obstacle.is_solid or not obstacle.vertices:
                continue

            # Compute bounding box of the obstacle
            min_x = min(v[0] for v in obstacle.vertices)
            max_x = max(v[0] for v in obstacle.vertices)
            min_y = min(v[1] for v in obstacle.vertices)
            max_y = max(v[1] for v in obstacle.vertices)

            for y in range(max(0, int(min_y)), min(h, int(max_y) + 1)):
                for x in range(max(0, int(min_x)), min(w, int(max_x) + 1)):
                    if self._point_in_polygon(x, y, obstacle.vertices):
                        # Apply friction and bounce
                        grid.velocity_x[y][x] *= obstacle.friction * obstacle.bounce_factor
                        grid.velocity_y[y][x] *= obstacle.friction * obstacle.bounce_factor
                        grid.density[y][x] = 0.0

    def _point_in_polygon(
        self, px: float, py: float, vertices: List[Tuple[float, float]]
    ) -> bool:
        """Check if a point is inside a polygon using the ray casting algorithm."""
        inside = False
        n = len(vertices)
        j = n - 1

        for i in range(n):
            xi, yi = vertices[i]
            xj, yj = vertices[j]

            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    # ------------------------------------------------------------------
    # Density Decay
    # ------------------------------------------------------------------

    def _decay_density(self, grid: FluidGrid) -> None:
        """Apply density decay to gradually dissipate density over time."""
        w = grid.width
        h = grid.height
        decay = self._density_decay

        for y in range(h):
            for x in range(w):
                grid.density[y][x] *= decay

    # ------------------------------------------------------------------
    # Particle Advection
    # ------------------------------------------------------------------

    def _advect_particles(self, grid: FluidGrid, delta_time: float) -> None:
        """Advect Lagrangian particles along the velocity field."""
        w = grid.width
        h = grid.height
        expired: List[str] = []

        for pid, particle in self._particles.items():
            if particle.metadata.get("grid_id") != grid.id:
                continue

            # Get velocity at particle position via bilinear interpolation
            px = particle.position_x
            py = particle.position_y

            ix = int(px)
            iy = int(py)
            if ix < 0 or ix >= w - 1 or iy < 0 or iy >= h - 1:
                expired.append(pid)
                continue

            fx = px - ix
            fy = py - iy

            vx = (
                grid.velocity_x[iy][ix] * (1.0 - fx) * (1.0 - fy)
                + grid.velocity_x[iy][ix + 1] * fx * (1.0 - fy)
                + grid.velocity_x[iy + 1][ix] * (1.0 - fx) * fy
                + grid.velocity_x[iy + 1][ix + 1] * fx * fy
            )
            vy = (
                grid.velocity_y[iy][ix] * (1.0 - fx) * (1.0 - fy)
                + grid.velocity_y[iy][ix + 1] * fx * (1.0 - fy)
                + grid.velocity_y[iy + 1][ix] * (1.0 - fx) * fy
                + grid.velocity_y[iy + 1][ix + 1] * fx * fy
            )

            particle.velocity_x = vx
            particle.velocity_y = vy
            particle.position_x += vx * delta_time
            particle.position_y += vy * delta_time

            # Clamp to grid boundaries
            particle.position_x = max(0.0, min(w - 1.0, particle.position_x))
            particle.position_y = max(0.0, min(h - 1.0, particle.position_y))

            # Update lifetime
            particle.lifetime -= delta_time
            if particle.lifetime <= 0.0:
                expired.append(pid)

        for pid in expired:
            del self._particles[pid]

    # ------------------------------------------------------------------
    # Boundary Conditions
    # ------------------------------------------------------------------

    def _set_boundary(self, grid: FluidGrid) -> None:
        """Apply boundary conditions to the velocity field."""
        w = grid.width
        h = grid.height

        if grid.boundary_type == BoundaryType.WALL:
            # Top and bottom edges: reverse vertical velocity
            for x in range(1, w - 1):
                grid.velocity_y[0][x] = -grid.velocity_y[1][x]
                grid.velocity_y[h - 1][x] = -grid.velocity_y[h - 2][x]

            # Left and right edges: reverse horizontal velocity
            for y in range(1, h - 1):
                grid.velocity_x[y][0] = -grid.velocity_x[y][1]
                grid.velocity_x[y][w - 1] = -grid.velocity_x[y][w - 2]

        elif grid.boundary_type == BoundaryType.OUTFLOW:
            # Copy velocity from interior to edges (no reflection)
            for x in range(1, w - 1):
                grid.velocity_y[0][x] = grid.velocity_y[1][x]
                grid.velocity_y[h - 1][x] = grid.velocity_y[h - 2][x]
            for y in range(1, h - 1):
                grid.velocity_x[y][0] = grid.velocity_x[y][1]
                grid.velocity_x[y][w - 1] = grid.velocity_x[y][w - 2]

        elif grid.boundary_type == BoundaryType.PERIODIC:
            # Wrap around
            for x in range(1, w - 1):
                grid.velocity_y[0][x] = grid.velocity_y[h - 2][x]
                grid.velocity_y[h - 1][x] = grid.velocity_y[1][x]
            for y in range(1, h - 1):
                grid.velocity_x[y][0] = grid.velocity_x[y][w - 2]
                grid.velocity_x[y][w - 1] = grid.velocity_x[y][1]

        # Corner velocity averaging
        grid.velocity_x[0][0] = 0.5 * (grid.velocity_x[0][1] + grid.velocity_x[1][0])
        grid.velocity_x[0][w - 1] = 0.5 * (grid.velocity_x[0][w - 2] + grid.velocity_x[1][w - 1])
        grid.velocity_x[h - 1][0] = 0.5 * (grid.velocity_x[h - 1][1] + grid.velocity_x[h - 2][0])
        grid.velocity_x[h - 1][w - 1] = 0.5 * (grid.velocity_x[h - 1][w - 2] + grid.velocity_x[h - 2][w - 1])

        grid.velocity_y[0][0] = 0.5 * (grid.velocity_y[0][1] + grid.velocity_y[1][0])
        grid.velocity_y[0][w - 1] = 0.5 * (grid.velocity_y[0][w - 2] + grid.velocity_y[1][w - 1])
        grid.velocity_y[h - 1][0] = 0.5 * (grid.velocity_y[h - 1][1] + grid.velocity_y[h - 2][0])
        grid.velocity_y[h - 1][w - 1] = 0.5 * (grid.velocity_y[h - 1][w - 2] + grid.velocity_y[h - 2][w - 1])

    def _set_boundary_pressure(self, grid: FluidGrid) -> None:
        """Apply boundary conditions to the pressure field."""
        w = grid.width
        h = grid.height

        # Copy pressure from interior to edges
        for x in range(1, w - 1):
            grid.pressure[0][x] = grid.pressure[1][x]
            grid.pressure[h - 1][x] = grid.pressure[h - 2][x]

        for y in range(1, h - 1):
            grid.pressure[y][0] = grid.pressure[y][1]
            grid.pressure[y][w - 1] = grid.pressure[y][w - 2]

        # Corners
        grid.pressure[0][0] = 0.5 * (grid.pressure[0][1] + grid.pressure[1][0])
        grid.pressure[0][w - 1] = 0.5 * (grid.pressure[0][w - 2] + grid.pressure[1][w - 1])
        grid.pressure[h - 1][0] = 0.5 * (grid.pressure[h - 1][1] + grid.pressure[h - 2][0])
        grid.pressure[h - 1][w - 1] = 0.5 * (grid.pressure[h - 1][w - 2] + grid.pressure[h - 2][w - 1])

    # ------------------------------------------------------------------
    # Grid Utilities
    # ------------------------------------------------------------------

    def get_field_stats(self, grid_id: str) -> Optional[Dict[str, Any]]:
        """Get statistical information about a grid's fields."""
        grid = self._grids.get(grid_id)
        if grid is None:
            return None

        w = grid.width
        h = grid.height

        total_density = 0.0
        max_density = 0.0
        total_velocity = 0.0
        max_velocity = 0.0

        for y in range(h):
            for x in range(w):
                total_density += grid.density[y][x]
                max_density = max(max_density, grid.density[y][x])
                vel_mag = math.sqrt(
                    grid.velocity_x[y][x] ** 2 + grid.velocity_y[y][x] ** 2
                )
                total_velocity += vel_mag
                max_velocity = max(max_velocity, vel_mag)

        num_cells = w * h

        return {
            "total_density": round(total_density, 4),
            "avg_density": round(total_density / max(num_cells, 1), 6),
            "max_density": round(max_density, 4),
            "total_velocity_magnitude": round(total_velocity, 4),
            "avg_velocity_magnitude": round(total_velocity / max(num_cells, 1), 6),
            "max_velocity_magnitude": round(max_velocity, 4),
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics including grid counts and simulation metrics."""
        with self._lock:
            grid_details: List[Dict[str, Any]] = []
            for grid in self._grids.values():
                particle_count = sum(
                    1 for p in self._particles.values()
                    if p.metadata.get("grid_id") == grid.id
                )
                grid_details.append({
                    "grid_id": grid.id,
                    "width": grid.width,
                    "height": grid.height,
                    "cell_size": grid.cell_size,
                    "boundary_type": grid.boundary_type.value,
                    "solver_type": grid.solver_type.value,
                    "particle_count": particle_count,
                })

            return {
                "grid_count": len(self._grids),
                "source_count": len(self._sources),
                "obstacle_count": len(self._obstacles),
                "particle_count": len(self._particles),
                "total_particles_emitted": self._total_particles_emitted,
                "step_count": self._step_count,
                "viscosity": self._viscosity,
                "diffusion": self._diffusion,
                "density_decay": self._density_decay,
                "max_particles": self._DEFAULT_MAX_PARTICLES,
                "uptime_seconds": round(time.time() - self._creation_time, 1),
                "grids": grid_details,
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire fluid simulation engine state."""
        with self._lock:
            self._grids.clear()
            self._particles.clear()
            self._sources.clear()
            self._obstacles.clear()
            self._step_count = 0
            self._total_particles_emitted = 0
            self._creation_time = time.time()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_fluid_simulation() -> FluidSimulationEngine:
    """Get or create the singleton FluidSimulationEngine instance."""
    return FluidSimulationEngine.get_instance()