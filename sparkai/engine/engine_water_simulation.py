"""
SparkLabs Engine - Water Simulation

A 2D water physics simulation system for the SparkLabs AI-native game
engine. Provides water body definitions, spring-based wave propagation,
Archimedes buoyancy, fluid drag, surface mesh generation, and particle
splash effects.

Architecture:
  EngineWaterSimulation (Singleton)
    |-- WaterBody         — water region definition with properties
    |-- WaveSimulator     — wave propagation algorithm
    |-- BuoyancyCalculator — object floating physics
    |-- FluidDrag         — drag forces on submerged objects
    |-- SurfaceRenderer   — surface mesh generation for rendering
    |-- SplashGenerator   — particle splash effects
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

class WaterBodyType(str, Enum):
    """Type of water body shape."""
    RECTANGULAR = "rectangular"
    POLYGONAL = "polygonal"
    CIRCULAR = "circular"
    RIVER = "river"
    OCEAN = "ocean"


class WavePattern(str, Enum):
    """Pre-defined wave behavior patterns."""
    CALM = "calm"
    GENTLE = "gentle"
    CHOPPY = "choppy"
    STORMY = "stormy"
    TSUNAMI = "tsunami"


class SplashType(str, Enum):
    """Type of splash event."""
    ENTRY = "entry"
    EXIT = "exit"
    RAINDROP = "raindrop"
    EXPLOSION = "explosion"
    WAKE = "wake"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WaterBody:
    """Water region definition with physical properties.

    Represents a bounded water area with configurable density, viscosity,
    surface tension, wave parameters, and current forces.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "WaterBody"
    body_type: WaterBodyType = WaterBodyType.RECTANGULAR

    # Bounds (x, y is the top-left corner for rectangular)
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 50.0

    # Surface definition — list of (x, y) tuples along the water surface
    surface_points: List[Tuple[float, float]] = field(default_factory=list)

    # Physical properties
    depth: float = 10.0
    density: float = 1000.0
    viscosity: float = 0.001
    surface_tension: float = 0.072

    # Wave parameters
    wave_amplitude: float = 0.5
    wave_frequency: float = 1.0
    wave_speed: float = 2.0
    wave_damping: float = 0.02

    # Current forces
    current_x: float = 0.0
    current_y: float = 0.0

    # Wind force
    wind: float = 0.0

    # Visual
    color_rgba: Tuple[int, int, int, int] = (64, 128, 255, 200)

    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize water body to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "body_type": self.body_type.value if hasattr(self.body_type, 'value') else self.body_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "surface_points": self.surface_points,
            "depth": self.depth,
            "density": self.density,
            "viscosity": self.viscosity,
            "surface_tension": self.surface_tension,
            "wave_amplitude": self.wave_amplitude,
            "wave_frequency": self.wave_frequency,
            "wave_speed": self.wave_speed,
            "wave_damping": self.wave_damping,
            "current_x": self.current_x,
            "current_y": self.current_y,
            "wind": self.wind,
            "color_rgba": self.color_rgba,
            "created_at": self.created_at,
        }


@dataclass
class BuoyantObject:
    """Floating object tracked by the water simulation.

    Maintains physical state needed for buoyancy and drag calculations,
    including submerged depth ratio and accumulated buoyancy force.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "BuoyantObject"
    water_body_id: str = ""

    # Position and dimensions
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0

    # Physical properties
    mass: float = 1.0
    volume: float = 1.0
    drag_coefficient: float = 0.47

    # Computed state
    submerged_depth: float = 0.0
    buoyancy_force: float = 0.0
    drag_force_x: float = 0.0
    drag_force_y: float = 0.0
    is_floating: bool = False

    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize buoyant object to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "water_body_id": self.water_body_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
            "mass": self.mass,
            "volume": self.volume,
            "drag_coefficient": self.drag_coefficient,
            "submerged_depth": self.submerged_depth,
            "buoyancy_force": self.buoyancy_force,
            "drag_force_x": self.drag_force_x,
            "drag_force_y": self.drag_force_y,
            "is_floating": self.is_floating,
            "created_at": self.created_at,
        }


@dataclass
class WavePoint:
    """Single point in the spring-based wave simulation grid.

    Each point is connected to its left and right neighbors via a
    spring-damper model, enabling realistic wave propagation.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    water_body_id: str = ""
    index: int = 0

    # Position
    x: float = 0.0
    y: float = 0.0
    rest_y: float = 0.0

    # Dynamics
    displacement: float = 0.0
    velocity: float = 0.0

    # Neighbor links within the wave grid
    left_neighbor_index: int = -1
    right_neighbor_index: int = -1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize wave point to dictionary."""
        return {
            "id": self.id,
            "water_body_id": self.water_body_id,
            "index": self.index,
            "x": self.x,
            "y": self.y,
            "rest_y": self.rest_y,
            "displacement": self.displacement,
            "velocity": self.velocity,
            "left_neighbor_index": self.left_neighbor_index,
            "right_neighbor_index": self.right_neighbor_index,
        }


@dataclass
class SplashParticle:
    """Individual splash particle for visual effects.

    Particles are spawned on object entry/exit and follow simple
    ballistic trajectories with gravity and lifetime decay.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    water_body_id: str = ""

    # Position and velocity
    x: float = 0.0
    y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0

    # Lifetime tracking
    lifetime: float = 0.0
    max_lifetime: float = 1.0

    # Visual properties
    size: float = 0.05
    opacity: float = 1.0
    splash_type: SplashType = SplashType.ENTRY

    def to_dict(self) -> Dict[str, Any]:
        """Serialize splash particle to dictionary."""
        return {
            "id": self.id,
            "water_body_id": self.water_body_id,
            "x": self.x,
            "y": self.y,
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
            "lifetime": self.lifetime,
            "max_lifetime": self.max_lifetime,
            "size": self.size,
            "opacity": self.opacity,
            "splash_type": self.splash_type.value if hasattr(self.splash_type, 'value') else self.splash_type,
        }


@dataclass
class WaterSurface:
    """Renderable surface mesh definition.

    Contains the vertex array for drawing the water surface, suitable
    for passing directly to a rendering backend (tessellated mesh or
    line strip).
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    water_body_id: str = ""

    # Surface vertices — list of (x, y)
    points: List[Tuple[float, float]] = field(default_factory=list)

    # Generation parameters
    vertex_count: int = 128
    resolution: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize water surface to dictionary."""
        return {
            "id": self.id,
            "water_body_id": self.water_body_id,
            "points": self.points,
            "vertex_count": self.vertex_count,
            "resolution": self.resolution,
        }


# ---------------------------------------------------------------------------
# Pre-defined wave pattern presets
# ---------------------------------------------------------------------------

_WAVE_PATTERN_PRESETS: Dict[WavePattern, Dict[str, float]] = {
    WavePattern.CALM: {
        "amplitude": 0.1,
        "frequency": 0.5,
        "speed": 1.0,
        "damping": 0.01,
    },
    WavePattern.GENTLE: {
        "amplitude": 0.4,
        "frequency": 1.0,
        "speed": 2.0,
        "damping": 0.02,
    },
    WavePattern.CHOPPY: {
        "amplitude": 1.5,
        "frequency": 2.5,
        "speed": 5.0,
        "damping": 0.04,
    },
    WavePattern.STORMY: {
        "amplitude": 3.0,
        "frequency": 4.0,
        "speed": 8.0,
        "damping": 0.06,
    },
    WavePattern.TSUNAMI: {
        "amplitude": 6.0,
        "frequency": 0.3,
        "speed": 12.0,
        "damping": 0.01,
    },
}


# ---------------------------------------------------------------------------
# Engine Water Simulation
# ---------------------------------------------------------------------------

class EngineWaterSimulation:
    """2D water physics simulation engine.

    Manages water bodies, wave simulation, buoyancy/drag forces, surface
    mesh generation, and splash particle effects. Uses a spring-damper
    wave model and Archimedes-principle buoyancy.

    Usage:
        ws = get_water_simulation()
        wb_id = ws.create_water_body("ocean", WaterBodyType.RECTANGULAR,
                                     0, 300, 800, 200, depth=50.0)
        obj_id = ws.add_buoyant_object(wb_id, "boat", 100, 280, 2.0, 1.0, 10.0)
        ws.update(16)
        surface = ws.get_surface_points(wb_id)
    """

    _instance: Optional["EngineWaterSimulation"] = None
    _lock: threading.RLock = threading.RLock()

    # Physics constants
    GRAVITY: float = 9.81
    SPRING_CONSTANT: float = 0.03
    SPREAD_FACTOR: float = 0.2
    DEFAULT_RESOLUTION: int = 128

    def __new__(cls) -> "EngineWaterSimulation":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineWaterSimulation":
        """Return the singleton EngineWaterSimulation instance."""
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._water_bodies: Dict[str, WaterBody] = {}
        self._wave_points: Dict[str, List[WavePoint]] = {}
        self._buoyant_objects: Dict[str, BuoyantObject] = {}
        self._splash_particles: Dict[str, Dict[str, SplashParticle]] = {}
        self._surfaces: Dict[str, WaterSurface] = {}

        self._total_water_bodies_created: int = 0
        self._total_buoyant_objects_created: int = 0
        self._total_splashes_generated: int = 0
        self._total_particles_spawned: int = 0
        self._tick_count: int = 0
        self._wind_force: float = 0.0
        self._global_time: float = 0.0

        self._initialized = True

    # ------------------------------------------------------------------
    # Water Body Management
    # ------------------------------------------------------------------

    def create_water_body(
        self,
        name: str,
        body_type: WaterBodyType,
        x: float,
        y: float,
        width: float,
        height: float,
        **kwargs: Any,
    ) -> WaterBody:
        """Create a new water body region.

        Args:
            name: Display name for the water body.
            body_type: Shape type (RECTANGULAR, CIRCULAR, RIVER, etc.).
            x: Left edge X coordinate in world space.
            y: Top edge Y coordinate (surface level) in world space.
            width: Horizontal extent.
            height: Vertical extent (depth).
            **kwargs: Optional overrides for density, viscosity,
                surface_tension, wave_amplitude, wave_frequency,
                wave_speed, wave_damping, current_x, current_y,
                color_rgba, depth.

        Returns:
            The newly created WaterBody dataclass instance.
        """
        with self._lock:
            wb = WaterBody(
                name=name,
                body_type=body_type,
                x=x,
                y=y,
                width=width,
                height=height,
                depth=kwargs.get("depth", 10.0),
                density=kwargs.get("density", 1000.0),
                viscosity=kwargs.get("viscosity", 0.001),
                surface_tension=kwargs.get("surface_tension", 0.072),
                wave_amplitude=kwargs.get("wave_amplitude", 0.5),
                wave_frequency=kwargs.get("wave_frequency", 1.0),
                wave_speed=kwargs.get("wave_speed", 2.0),
                wave_damping=kwargs.get("wave_damping", 0.02),
                current_x=kwargs.get("current_x", 0.0),
                current_y=kwargs.get("current_y", 0.0),
                color_rgba=kwargs.get("color_rgba", (64, 128, 255, 200)),
            )

            self._water_bodies[wb.id] = wb
            self._total_water_bodies_created += 1

            # Build wave point grid along the surface
            self._initialize_wave_points(wb)

            # Build surface renderer
            self._surfaces[wb.id] = WaterSurface(
                water_body_id=wb.id,
                vertex_count=kwargs.get("surface_vertex_count", self.DEFAULT_RESOLUTION),
                resolution=kwargs.get("surface_resolution", width / self.DEFAULT_RESOLUTION),
            )

            # Initialize splash particle storage
            self._splash_particles[wb.id] = {}

            return wb

    def remove_water_body(self, water_body_id: str) -> bool:
        """Remove a water body and all associated data.

        Args:
            water_body_id: The ID of the water body to remove.

        Returns:
            True if the water body was found and removed, False otherwise.
        """
        with self._lock:
            if water_body_id not in self._water_bodies:
                return False

            del self._water_bodies[water_body_id]
            self._wave_points.pop(water_body_id, None)
            self._surfaces.pop(water_body_id, None)
            self._splash_particles.pop(water_body_id, None)

            # Remove buoyant objects referencing this water body
            to_remove = [
                oid for oid, obj in self._buoyant_objects.items()
                if obj.water_body_id == water_body_id
            ]
            for oid in to_remove:
                del self._buoyant_objects[oid]

            return True

    def get_water_body(self, water_body_id: str) -> Optional[WaterBody]:
        """Retrieve a water body by ID.

        Args:
            water_body_id: The water body ID.

        Returns:
            The WaterBody instance or None if not found.
        """
        return self._water_bodies.get(water_body_id)

    def get_all_water_bodies(self) -> List[Dict[str, Any]]:
        """List all water bodies as dictionaries.

        Returns:
            A list of serialized water body dictionaries.
        """
        with self._lock:
            return [wb.to_dict() for wb in self._water_bodies.values()]

    # ------------------------------------------------------------------
    # Wave Point Initialization
    # ------------------------------------------------------------------

    def _initialize_wave_points(self, wb: WaterBody) -> None:
        """Build the spring-connected wave point grid along the surface.

        Args:
            wb: The water body to build wave points for.
        """
        points: List[WavePoint] = []
        resolution = max(2, self.DEFAULT_RESOLUTION)
        step = wb.width / (resolution - 1)

        for i in range(resolution):
            px = wb.x + i * step
            py = wb.y
            wp = WavePoint(
                water_body_id=wb.id,
                index=i,
                x=px,
                y=py,
                rest_y=py,
                displacement=0.0,
                velocity=0.0,
                left_neighbor_index=i - 1,
                right_neighbor_index=i + 1 if i < resolution - 1 else -1,
            )
            points.append(wp)

        # Fix endpoints (boundary conditions)
        points[0].velocity = 0.0
        points[-1].velocity = 0.0

        self._wave_points[wb.id] = points

    # ------------------------------------------------------------------
    # Update Tick
    # ------------------------------------------------------------------

    def update(self, delta_time_ms: float) -> Dict[str, Any]:
        """Advance the water simulation by one frame.

        Performs wave propagation, buoyancy computation, drag force
        calculation, and splash particle lifetime management.

        Args:
            delta_time_ms: Frame delta in milliseconds.

        Returns:
            Dict with counts of active bodies, objects, and particles.
        """
        dt = delta_time_ms / 1000.0
        self._global_time += dt
        self._tick_count += 1

        with self._lock:
            updates_performed = 0
            buoyancy_updates = 0
            particles_updated = 0

            for wb_id, wb in self._water_bodies.items():
                # Wave propagation
                self._update_waves(wb, dt)

                # Buoyancy for objects in this water body
                for obj in self._buoyant_objects.values():
                    if obj.water_body_id == wb_id:
                        self._compute_buoyancy(obj, wb)
                        self._compute_drag(obj, wb)
                        buoyancy_updates += 1

                # Update splash particles
                particles_updated += self._update_splash_particles(wb_id, dt)

                updates_performed += 1

        return {
            "total_water_bodies": len(self._water_bodies),
            "total_buoyant_objects": len(self._buoyant_objects),
            "updates_performed": updates_performed,
            "buoyancy_updates": buoyancy_updates,
            "particles_updated": particles_updated,
            "delta_time_ms": delta_time_ms,
        }

    # ------------------------------------------------------------------
    # Wave Simulation (Spring-Damper Model)
    # ------------------------------------------------------------------

    def _update_waves(self, wb: WaterBody, dt: float) -> None:
        """Advance wave propagation using a spring-damper model.

        1. Calculate spring forces between neighboring points
        2. Apply wind-driven displacement
        3. Integrate velocities and positions
        4. Apply damping

        Args:
            wb: The water body whose waves are being updated.
            dt: Delta time in seconds.
        """
        points = self._wave_points.get(wb.id)
        if not points:
            return

        k = self.SPRING_CONSTANT * wb.wave_speed
        damping = wb.wave_damping

        # Pass 1: Compute accelerations from neighbor displacement differences
        accelerations: List[float] = [0.0] * len(points)

        for i in range(1, len(points) - 1):
            wp = points[i]
            left = points[wp.left_neighbor_index]
            right = points[wp.right_neighbor_index]

            # Spring force proportional to displacement difference
            left_diff = left.displacement - wp.displacement
            right_diff = right.displacement - wp.displacement
            spring_force = k * (left_diff + right_diff)

            # Damping force proportional to velocity
            damping_force = -damping * wp.velocity

            # Wind contribution based on amplitude and frequency
            wind = self._wind_force * math.sin(
                self._global_time * wb.wave_frequency * 2.0 * math.pi
                + wp.x * 0.1
            )

            accelerations[i] = spring_force + damping_force + wind * 0.01

        # Pass 2: Integrate using semi-implicit Euler
        for i in range(1, len(points) - 1):
            wp = points[i]
            wp.velocity += accelerations[i] * dt
            wp.displacement += wp.velocity * dt

            # Clamp displacement to prevent numerical blow-up
            max_disp = wb.wave_amplitude * 5.0
            wp.displacement = max(-max_disp, min(max_disp, wp.displacement))

            # Update visual Y position
            wp.y = wp.rest_y + wp.displacement

        # Enforce boundary conditions (fixed endpoints)
        points[0].displacement = 0.0
        points[0].velocity = 0.0
        points[-1].displacement = 0.0
        points[-1].velocity = 0.0

    # ------------------------------------------------------------------
    # Buoyancy Physics (Archimedes Principle)
    # ------------------------------------------------------------------

    def _compute_buoyancy(self, obj: BuoyantObject, wb: WaterBody) -> None:
        """Calculate buoyancy force using Archimedes' principle.

        The buoyancy force equals the weight of displaced fluid:
            F_buoyancy = density * gravity * displaced_volume

        Args:
            obj: The buoyant object to compute forces for.
            wb: The water body the object resides in.
        """
        # Determine how much of the object is below the surface
        # Surface Y is the water level at the object's X position
        surface_y = self._get_surface_y_at(wb, obj.x)

        # Object's bottom edge Y
        bottom_y = obj.y - obj.height * 0.5
        # Object's top edge Y
        top_y = obj.y + obj.height * 0.5

        if bottom_y >= surface_y:
            # Entirely above water — no buoyancy
            obj.submerged_depth = 0.0
            obj.buoyancy_force = 0.0
            obj.is_floating = False
            return

        if top_y <= surface_y:
            # Fully submerged
            obj.submerged_depth = obj.height
        else:
            # Partially submerged
            obj.submerged_depth = surface_y - bottom_y

        submerged_ratio = obj.submerged_depth / obj.height
        submerged_volume = obj.volume * min(1.0, max(0.0, submerged_ratio))

        # Archimedes: buoyancy = fluid_density * gravity * displaced_volume
        buoyancy = wb.density * self.GRAVITY * submerged_volume

        obj.buoyancy_force = buoyancy
        obj.is_floating = buoyancy >= obj.mass * self.GRAVITY

    # ------------------------------------------------------------------
    # Fluid Drag (Quadratic Drag Model)
    # ------------------------------------------------------------------

    def _compute_drag(self, obj: BuoyantObject, wb: WaterBody) -> None:
        """Calculate fluid drag force proportional to velocity squared.

        Drag force: F_drag = 0.5 * density * Cd * A * v^2
        Direction opposes velocity relative to fluid current.

        Args:
            obj: The buoyant object.
            wb: The water body providing current and fluid properties.
        """
        if obj.submerged_depth <= 0.001:
            obj.drag_force_x = 0.0
            obj.drag_force_y = 0.0
            return

        # Relative velocity (object velocity minus current)
        rel_vx = obj.velocity_x - wb.current_x
        rel_vy = obj.velocity_y - wb.current_y

        # Cross-sectional area (approximate based on submerged ratio)
        submerged_ratio = min(1.0, obj.submerged_depth / obj.height)
        cross_area_x = obj.height * submerged_ratio  # frontal area for horizontal
        cross_area_y = obj.width  # frontal area for vertical

        fluid_factor = 0.5 * wb.density * obj.drag_coefficient

        # Horizontal drag
        speed_x = abs(rel_vx)
        drag_x = fluid_factor * cross_area_x * speed_x * speed_x
        if rel_vx > 0:
            drag_x = -drag_x
        elif rel_vx < 0:
            pass  # drag_x already positive (force opposes velocity)

        obj.drag_force_x = drag_x if rel_vx != 0 else 0.0

        # Vertical drag
        speed_y = abs(rel_vy)
        drag_y = fluid_factor * cross_area_y * speed_y * speed_y
        if rel_vy > 0:
            drag_y = -drag_y

        obj.drag_force_y = drag_y if rel_vy != 0 else 0.0

    def _get_surface_y_at(self, wb: WaterBody, x: float) -> float:
        """Get the water surface Y at a given X coordinate.

        Interpolates between wave points to find the displaced surface
        height.

        Args:
            wb: The water body.
            x: World X coordinate.

        Returns:
            Y coordinate of the water surface at the given X.
        """
        points = self._wave_points.get(wb.id)
        if not points:
            return wb.y

        # Clamp X to water body bounds
        clamped_x = max(wb.x, min(wb.x + wb.width, x))

        # Find the two surrounding wave points and interpolate
        resolution = len(points)
        step = wb.width / (resolution - 1)
        float_index = (clamped_x - wb.x) / step

        idx0 = int(float_index)
        idx1 = min(idx0 + 1, resolution - 1)
        idx0 = max(0, idx0)

        if idx0 == idx1:
            return points[idx0].y

        t = float_index - idx0
        return points[idx0].y + (points[idx1].y - points[idx0].y) * t

    # ------------------------------------------------------------------
    # Buoyant Object Management
    # ------------------------------------------------------------------

    def add_buoyant_object(
        self,
        water_body_id: str,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        mass: float,
        **kwargs: Any,
    ) -> Optional[BuoyantObject]:
        """Register a buoyant object with a water body.

        Args:
            water_body_id: ID of the water body this object floats in.
            name: Display name.
            x, y: World position of the object center.
            width, height: Object dimensions.
            mass: Object mass in kg.
            **kwargs: Optional overrides for volume, drag_coefficient.

        Returns:
            The BuoyantObject instance, or None if water body not found.
        """
        with self._lock:
            if water_body_id not in self._water_bodies:
                return None

            obj = BuoyantObject(
                name=name,
                water_body_id=water_body_id,
                x=x,
                y=y,
                width=width,
                height=height,
                mass=mass,
                volume=kwargs.get("volume", width * height),
                drag_coefficient=kwargs.get("drag_coefficient", 0.47),
            )

            self._buoyant_objects[obj.id] = obj
            self._total_buoyant_objects_created += 1

            return obj

    def update_buoyant_object(
        self,
        obj_id: str,
        x: float,
        y: float,
        velocity_x: float = 0.0,
        velocity_y: float = 0.0,
    ) -> bool:
        """Update the position and velocity of a tracked buoyant object.

        Args:
            obj_id: The buoyant object ID.
            x, y: New world position.
            velocity_x, velocity_y: Current velocity components.

        Returns:
            True if updated successfully, False if object not found.
        """
        obj = self._buoyant_objects.get(obj_id)
        if not obj:
            return False

        obj.x = x
        obj.y = y
        obj.velocity_x = velocity_x
        obj.velocity_y = velocity_y
        return True

    def remove_buoyant_object(self, obj_id: str) -> bool:
        """Remove a buoyant object from the simulation.

        Args:
            obj_id: The buoyant object ID.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if obj_id not in self._buoyant_objects:
                return False
            del self._buoyant_objects[obj_id]
            return True

    # ------------------------------------------------------------------
    # Buoyancy Query
    # ------------------------------------------------------------------

    def get_buoyancy_force(self, obj_id: str) -> Dict[str, Any]:
        """Get current buoyancy and drag forces for an object.

        Args:
            obj_id: The buoyant object ID.

        Returns:
            Dict with buoyancy_force, drag_force_x, drag_force_y,
            submerged_depth, is_floating. Empty dict if not found.
        """
        obj = self._buoyant_objects.get(obj_id)
        if not obj:
            return {}

        return {
            "buoyancy_force": obj.buoyancy_force,
            "drag_force_x": obj.drag_force_x,
            "drag_force_y": obj.drag_force_y,
            "submerged_depth": obj.submerged_depth,
            "is_floating": obj.is_floating,
        }

    # ------------------------------------------------------------------
    # Surface Rendering
    # ------------------------------------------------------------------

    def get_surface_points(self, water_body_id: str) -> List[Tuple[float, float]]:
        """Get the surface vertex array for rendering.

        Returns a list of (x, y) tuples representing displaced surface
        points that can be drawn as a line strip or tessellated mesh.

        Args:
            water_body_id: The water body ID.

        Returns:
            List of (x, y) tuples for the water surface.
        """
        points = self._wave_points.get(water_body_id)
        if not points:
            return []

        result = [(wp.x, wp.y) for wp in points]

        # Update the cached surface
        surface = self._surfaces.get(water_body_id)
        if surface:
            surface.points = result

        return result

    # ------------------------------------------------------------------
    # Splash Effects
    # ------------------------------------------------------------------

    def generate_splash(
        self,
        water_body_id: str,
        x: float,
        y: float,
        velocity: float,
        splash_type: SplashType = SplashType.ENTRY,
    ) -> List[SplashParticle]:
        """Generate splash particles at a given location.

        Splash particle count and spread scale with impact velocity.
        Particles follow ballistic trajectories with gravity.

        Args:
            water_body_id: The water body to splash into.
            x, y: Impact world position.
            velocity: Impact velocity magnitude.
            splash_type: Type of splash (ENTRY, EXIT, RAINDROP, etc.).
                Accepts both SplashType enum and string values.

        Returns:
            List of created SplashParticle instances.
        """
        # Accept both string and enum for splash_type
        if isinstance(splash_type, str):
            splash_type = SplashType(splash_type)

        with self._lock:
            if water_body_id not in self._water_bodies:
                return []

            # Particle count scales with impact velocity
            base_count = 20
            particle_count = int(base_count + velocity * 3.0)
            particle_count = max(5, min(particle_count, 200))

            created: List[SplashParticle] = []
            spread = velocity * 0.3
            lifetime_base = min(2.0, velocity * 0.2 + 0.3)

            for _ in range(particle_count):
                # Random direction in upper hemisphere (splash goes upward)
                angle = random.uniform(-math.pi, math.pi)
                speed = random.uniform(velocity * 0.1, velocity * 1.2)

                particle = SplashParticle(
                    water_body_id=water_body_id,
                    x=x + random.uniform(-spread * 0.3, spread * 0.3),
                    y=y,
                    velocity_x=math.cos(angle) * speed * 0.5,
                    velocity_y=abs(math.sin(angle)) * speed,
                    lifetime=0.0,
                    max_lifetime=random.uniform(lifetime_base * 0.5, lifetime_base * 1.5),
                    size=random.uniform(0.02, 0.08),
                    opacity=1.0,
                    splash_type=splash_type,
                )

                self._splash_particles[water_body_id][particle.id] = particle
                created.append(particle)
                self._total_particles_spawned += 1

            self._total_splashes_generated += 1
            return created

    def get_splash_particles(
        self, water_body_id: str
    ) -> List[Dict[str, Any]]:
        """Get all active splash particles for a water body.

        Args:
            water_body_id: The water body ID.

        Returns:
            List of serialized splash particle dicts.
        """
        particles = self._splash_particles.get(water_body_id)
        if not particles:
            return []

        return [p.to_dict() for p in particles.values()]

    def _update_splash_particles(self, water_body_id: str, dt: float) -> int:
        """Update splash particle physics and lifetimes.

        Applies gravity, moves particles, decays opacity and size,
        removes expired particles.

        Args:
            water_body_id: The water body ID.
            dt: Delta time in seconds.

        Returns:
            Number of particles that remain alive after the update.
        """
        particles = self._splash_particles.get(water_body_id)
        if not particles:
            return 0

        expired: List[str] = []

        for pid, p in particles.items():
            p.lifetime += dt

            if p.lifetime >= p.max_lifetime:
                expired.append(pid)
                continue

            # Apply gravity
            p.velocity_y -= self.GRAVITY * dt * 0.5

            # Update position
            p.x += p.velocity_x * dt
            p.y += p.velocity_y * dt

            # Fade opacity based on remaining lifetime
            progress = p.lifetime / p.max_lifetime
            p.opacity = 1.0 - progress

            # Shrink particle over its lifetime
            p.size *= (1.0 - dt * 0.5)

        for pid in expired:
            del particles[pid]

        return len(particles)

    # ------------------------------------------------------------------
    # Wave Parameter Control
    # ------------------------------------------------------------------

    def set_wave_parameters(
        self,
        water_body_id: str,
        amplitude: float,
        frequency: float,
        speed: float,
    ) -> bool:
        """Adjust wave parameters for a specific water body.

        Args:
            water_body_id: The water body ID.
            amplitude: New wave amplitude.
            frequency: New wave frequency.
            speed: New wave propagation speed.

        Returns:
            True if parameters were applied, False if water body not found.
        """
        wb = self._water_bodies.get(water_body_id)
        if not wb:
            return False

        wb.wave_amplitude = amplitude
        wb.wave_frequency = frequency
        wb.wave_speed = speed
        return True

    def set_wave_pattern(
        self,
        water_body_id: str,
        pattern: WavePattern,
    ) -> bool:
        """Apply a pre-defined wave pattern preset.

        Args:
            water_body_id: The water body ID.
            pattern: The wave pattern enum value.

        Returns:
            True if applied, False if water body not found.
        """
        wb = self._water_bodies.get(water_body_id)
        if not wb:
            return False

        preset = _WAVE_PATTERN_PRESETS.get(pattern)
        if not preset:
            return False

        wb.wave_amplitude = preset["amplitude"]
        wb.wave_frequency = preset["frequency"]
        wb.wave_speed = preset["speed"]
        wb.wave_damping = preset["damping"]
        return True

    def set_wind_force(self, water_body_id: Optional[str] = None, force: float = 0.0) -> None:
        """Set wind force affecting water bodies.

        When water_body_id is provided, sets wind force for that specific body.
        When None, sets the global wind force for all bodies.

        Positive values push waves rightward; negative leftward.

        Args:
            water_body_id: Optional water body ID for per-body wind.
            force: Wind force magnitude and direction.
        """
        if water_body_id is not None and water_body_id in self._water_bodies:
            self._water_bodies[water_body_id].wind = force
        else:
            self._wind_force = force

    # ------------------------------------------------------------------
    # Statistics and Serialization
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics about the water simulation.

        Returns:
            Dict with counts, distribution data, and timing info.
        """
        body_type_distribution: Dict[str, int] = {}
        for wb in self._water_bodies.values():
            t = wb.body_type.value
            body_type_distribution[t] = body_type_distribution.get(t, 0) + 1

        total_active_particles = sum(
            len(p) for p in self._splash_particles.values()
        )

        floating_count = sum(
            1 for obj in self._buoyant_objects.values() if obj.is_floating
        )

        return {
            "total_ticks": self._tick_count,
            "total_water_bodies": len(self._water_bodies),
            "total_water_bodies_created": self._total_water_bodies_created,
            "body_type_distribution": body_type_distribution,
            "total_buoyant_objects": len(self._buoyant_objects),
            "total_buoyant_objects_created": self._total_buoyant_objects_created,
            "floating_objects": floating_count,
            "total_splashes_generated": self._total_splashes_generated,
            "total_particles_spawned": self._total_particles_spawned,
            "active_splash_particles": total_active_particles,
            "global_time": self._global_time,
            "wind_force": self._wind_force,
            "gravity": self.GRAVITY,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entire water simulation state.

        Returns:
            Dict representation of all water bodies, buoyant objects,
            surfaces, and active splash particles.
        """
        with self._lock:
            return {
                "water_bodies": [wb.to_dict() for wb in self._water_bodies.values()],
                "buoyant_objects": [
                    obj.to_dict() for obj in self._buoyant_objects.values()
                ],
                "surfaces": [s.to_dict() for s in self._surfaces.values()],
                "stats": self.get_stats(),
            }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_water_simulation() -> EngineWaterSimulation:
    """Get or create the singleton EngineWaterSimulation instance."""
    return EngineWaterSimulation.get_instance()