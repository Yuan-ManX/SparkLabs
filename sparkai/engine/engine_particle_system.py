"""
SparkLabs Engine - GPU-Friendly Particle Emitter System

A GPU-friendly particle emitter system that manages the full lifecycle of
particle emitters, individual particle simulation, and frame-by-frame
updates. Supports multiple emission shapes, blend modes, simulation spaces,
and emitter lifetime modes for building explosions, trails, ambient effects,
and custom visual phenomena.

Architecture:
  EngineParticleSystem (Singleton)
    |-- Particle           — per-particle state (position, velocity, color, size)
    |-- EmitterConfig      — emission configuration (shape, rate, lifetime, blend)
    |-- EmitterState       — runtime emitter tracking
    |-- ParticleReport     — aggregate statistics snapshot

Usage:
    ps = get_particle_system()
    config = EmitterConfig(name="fire", emission_shape=EmissionShape.CONE,
        emission_rate=80.0, max_particles=400)
    state = ps.create_emitter(config, 100.0, 200.0)
    all_particles = ps.update_all(0.016)
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

class EmissionShape(str, Enum):
    """Geometry shape defining the spawn region of particles."""
    POINT = "point"
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    RING = "ring"
    CONE = "cone"
    LINE = "line"


class ParticleBlendMode(str, Enum):
    """Rendering blend operation for particle compositing."""
    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"


class SimulationSpace(str, Enum):
    """Coordinate space for particle motion simulation."""
    LOCAL = "local"
    WORLD = "world"


class EmitterLifetime(str, Enum):
    """Emitter lifetime behavior mode."""
    CONTINUOUS = "continuous"
    BURST = "burst"
    DURATION = "duration"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Particle:
    """Individual particle state for simulation and rendering.

    Tracks per-particle properties including position, velocity, lifetime,
    interpolated size and color endpoints, rotation, and liveness flag.
    """

    particle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    emitter_id: str = ""
    texture_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    acceleration_x: float = 0.0
    acceleration_y: float = 0.0
    life_elapsed: float = 0.0
    life_max: float = 1.0
    size_start: float = 1.0
    size_end: float = 0.0
    color_rgba_start: Tuple[int, int, int, int] = (255, 255, 255, 255)
    color_rgba_end: Tuple[int, int, int, int] = (255, 255, 255, 0)
    rotation_start: float = 0.0
    rotation_end: float = 0.0
    angular_velocity: float = 0.0
    active: bool = True
    blend_mode: ParticleBlendMode = ParticleBlendMode.NORMAL
    gravity_scale: float = 1.0

    @property
    def life_ratio(self) -> float:
        """Normalized 0..1 ratio of elapsed lifetime."""
        return self.life_elapsed / max(self.life_max, 0.0001)

    @property
    def current_size(self) -> float:
        """Interpolated size based on life ratio."""
        return self.size_start + (self.size_end - self.size_start) * self.life_ratio

    @property
    def current_color_rgba(self) -> Tuple[int, int, int, int]:
        """Interpolated color based on life ratio."""
        t = self.life_ratio
        return (
            int(self.color_rgba_start[0] + (self.color_rgba_end[0] - self.color_rgba_start[0]) * t),
            int(self.color_rgba_start[1] + (self.color_rgba_end[1] - self.color_rgba_start[1]) * t),
            int(self.color_rgba_start[2] + (self.color_rgba_end[2] - self.color_rgba_start[2]) * t),
            int(self.color_rgba_start[3] + (self.color_rgba_end[3] - self.color_rgba_start[3]) * t),
        )

    @property
    def current_rotation(self) -> float:
        """Interpolated rotation based on life ratio."""
        return self.rotation_start + (self.rotation_end - self.rotation_start) * self.life_ratio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "particle_id": self.particle_id,
            "emitter_id": self.emitter_id,
            "texture_id": self.texture_id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
            "acceleration_x": self.acceleration_x,
            "acceleration_y": self.acceleration_y,
            "life_elapsed": self.life_elapsed,
            "life_max": self.life_max,
            "life_ratio": round(self.life_ratio, 4),
            "size_start": self.size_start,
            "size_end": self.size_end,
            "current_size": round(self.current_size, 4),
            "color_rgba_start": list(self.color_rgba_start),
            "color_rgba_end": list(self.color_rgba_end),
            "current_color_rgba": list(self.current_color_rgba),
            "rotation_start": self.rotation_start,
            "rotation_end": self.rotation_end,
            "angular_velocity": self.angular_velocity,
            "current_rotation": round(self.current_rotation, 4),
            "active": self.active,
            "blend_mode": self.blend_mode.value,
            "gravity_scale": self.gravity_scale,
        }


@dataclass
class EmitterConfig:
    """Configuration for a particle emitter.

    Defines emission rate, shape, lifetime range, speed range, gravity,
    damping, radial/tangential acceleration, blend mode, and more.
    """

    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "emitter"
    texture_id: str = "default"
    emission_shape: EmissionShape = EmissionShape.POINT
    emission_rate: float = 10.0
    emission_burst_count: int = 0
    emitter_lifetime: EmitterLifetime = EmitterLifetime.CONTINUOUS
    emitter_duration: float = 5.0
    simulation_space: SimulationSpace = SimulationSpace.WORLD
    blend_mode: ParticleBlendMode = ParticleBlendMode.NORMAL
    life_min: float = 1.0
    life_max: float = 3.0
    speed_min: float = 50.0
    speed_max: float = 150.0
    angle_min: float = 0.0
    angle_max: float = 360.0
    size_start_min: float = 4.0
    size_start_max: float = 8.0
    size_end_min: float = 0.0
    size_end_max: float = 2.0
    color_start: Tuple[int, int, int, int] = (255, 255, 255, 255)
    color_end: Tuple[int, int, int, int] = (255, 255, 255, 0)
    gravity_x: float = 0.0
    gravity_y: float = -98.0
    radial_accel: float = 0.0
    tangential_accel: float = 0.0
    damping: float = 0.98
    circle_radius: float = 50.0
    rect_width: float = 100.0
    rect_height: float = 50.0
    ring_inner_radius: float = 20.0
    ring_outer_radius: float = 50.0
    cone_angle: float = 45.0
    line_length: float = 100.0
    max_particles: int = 500
    prewarm: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "texture_id": self.texture_id,
            "emission_shape": self.emission_shape.value,
            "emission_rate": self.emission_rate,
            "emission_burst_count": self.emission_burst_count,
            "emitter_lifetime": self.emitter_lifetime.value,
            "emitter_duration": self.emitter_duration,
            "simulation_space": self.simulation_space.value,
            "blend_mode": self.blend_mode.value,
            "life_min": self.life_min,
            "life_max": self.life_max,
            "speed_min": self.speed_min,
            "speed_max": self.speed_max,
            "angle_min": self.angle_min,
            "angle_max": self.angle_max,
            "size_start_min": self.size_start_min,
            "size_start_max": self.size_start_max,
            "size_end_min": self.size_end_min,
            "size_end_max": self.size_end_max,
            "color_start": list(self.color_start),
            "color_end": list(self.color_end),
            "gravity_x": self.gravity_x,
            "gravity_y": self.gravity_y,
            "radial_accel": self.radial_accel,
            "tangential_accel": self.tangential_accel,
            "damping": self.damping,
            "circle_radius": self.circle_radius,
            "rect_width": self.rect_width,
            "rect_height": self.rect_height,
            "ring_inner_radius": self.ring_inner_radius,
            "ring_outer_radius": self.ring_outer_radius,
            "cone_angle": self.cone_angle,
            "line_length": self.line_length,
            "max_particles": self.max_particles,
            "prewarm": self.prewarm,
        }


@dataclass
class EmitterState:
    """Runtime state tracking for an active particle emitter."""

    emitter_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    config: EmitterConfig = field(default_factory=EmitterConfig)
    position_x: float = 0.0
    position_y: float = 0.0
    rotation: float = 0.0
    active: bool = False
    elapsed: float = 0.0
    particle_count: int = 0
    accumulation: float = 0.0
    burst_triggered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emitter_id": self.emitter_id,
            "config": self.config.to_dict(),
            "position_x": self.position_x,
            "position_y": self.position_y,
            "rotation": self.rotation,
            "active": self.active,
            "elapsed": self.elapsed,
            "particle_count": self.particle_count,
            "accumulation": self.accumulation,
            "burst_triggered": self.burst_triggered,
        }


@dataclass
class ParticleReport:
    """Aggregate statistics snapshot for the particle system."""

    emitter_id: str = ""
    active_particles: int = 0
    total_emitted: int = 0
    draw_calls_estimate: int = 0
    memory_kb: float = 0.0
    fps_estimate: float = 60.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emitter_id": self.emitter_id,
            "active_particles": self.active_particles,
            "total_emitted": self.total_emitted,
            "draw_calls_estimate": self.draw_calls_estimate,
            "memory_kb": round(self.memory_kb, 2),
            "fps_estimate": round(self.fps_estimate, 1),
        }


# ---------------------------------------------------------------------------
# EngineParticleSystem — Thread-Safe Singleton
# ---------------------------------------------------------------------------

class EngineParticleSystem:
    """GPU-friendly particle emitter system for the SparkLabs framework.

    Manages the full lifecycle of particle emitters, individual particle
    simulation, and frame-by-frame updates. Provides methods for creating
    emitters with configurable shapes and blend modes, updating particles
    per frame with interpolation, and burst emission.

    Usage:
        ps = get_particle_system()
        config = EmitterConfig(name="fire", emission_shape=EmissionShape.CONE,
            emission_rate=80.0, max_particles=400)
        state = ps.create_emitter(config, 100.0, 200.0)
        all_particles = ps.update_all(0.016)
    """

    _instance: Optional["EngineParticleSystem"] = None
    _lock: threading.RLock = threading.RLock()

    # Memory estimate per particle in bytes
    _BYTES_PER_PARTICLE: int = 128

    def __new__(cls) -> "EngineParticleSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineParticleSystem":
        return cls()

    def _initialize(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._emitters: Dict[str, EmitterState] = {}
        self._particle_pools: Dict[str, List[Particle]] = {}
        self._active_particles: int = 0
        self._max_particles: int = 10000
        self._creation_counter: int = 0
        self._initialized: bool = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_spawn_position(
        self,
        state: EmitterState,
        config: EmitterConfig,
    ) -> Tuple[float, float]:
        """Compute particle spawn position based on emission shape and emitter position/rotation."""
        px = state.position_x
        py = state.position_y
        shape = config.emission_shape

        if shape == EmissionShape.POINT:
            return (px, py)

        elif shape == EmissionShape.CIRCLE:
            angle = random.uniform(0.0, 2.0 * math.pi)
            r = random.uniform(0.0, config.circle_radius)
            return (px + math.cos(angle) * r, py + math.sin(angle) * r)

        elif shape == EmissionShape.RECTANGLE:
            hw = config.rect_width * 0.5
            hh = config.rect_height * 0.5
            return (px + random.uniform(-hw, hw), py + random.uniform(-hh, hh))

        elif shape == EmissionShape.RING:
            angle = random.uniform(0.0, 2.0 * math.pi)
            r = random.uniform(config.ring_inner_radius, config.ring_outer_radius)
            return (px + math.cos(angle) * r, py + math.sin(angle) * r)

        elif shape == EmissionShape.CONE:
            half_angle = math.radians(config.cone_angle * 0.5)
            angle_offset = random.uniform(-half_angle, half_angle)
            rot_rad = math.radians(state.rotation)
            emit_angle = rot_rad + angle_offset
            r = random.uniform(0.0, config.circle_radius)
            return (px + math.cos(emit_angle) * r, py + math.sin(emit_angle) * r)

        elif shape == EmissionShape.LINE:
            t = random.uniform(-0.5, 0.5)
            rot_rad = math.radians(state.rotation)
            half_len = config.line_length * 0.5
            offset = t * config.line_length
            return (
                px + math.cos(rot_rad) * offset,
                py + math.sin(rot_rad) * offset,
            )

        return (px, py)

    def _compute_velocity(
        self,
        state: EmitterState,
        config: EmitterConfig,
    ) -> Tuple[float, float]:
        """Compute particle initial velocity based on angle range and speed range."""
        angle_deg = random.uniform(config.angle_min, config.angle_max)
        emitter_rot_rad = math.radians(state.rotation)
        emit_angle_rad = emitter_rot_rad + math.radians(angle_deg)

        speed = random.uniform(config.speed_min, config.speed_max)

        vx = math.cos(emit_angle_rad) * speed
        vy = math.sin(emit_angle_rad) * speed
        return (vx, vy)

    # ------------------------------------------------------------------
    # Emitter management
    # ------------------------------------------------------------------

    def create_emitter(
        self,
        config: EmitterConfig,
        pos_x: float,
        pos_y: float,
        rotation: float = 0.0,
    ) -> EmitterState:
        """Create and register a new emitter with the given configuration.

        Args:
            config: Emitter configuration defining shape, rate, lifetime, etc.
            pos_x: World-space X position.
            pos_y: World-space Y position.
            rotation: Emitter rotation in degrees.

        Returns:
            The created EmitterState instance.
        """
        emitter_id = uuid.uuid4().hex[:12]
        state = EmitterState(
            emitter_id=emitter_id,
            config=config,
            position_x=pos_x,
            position_y=pos_y,
            rotation=rotation,
            active=True,
            elapsed=0.0,
            particle_count=0,
            accumulation=0.0,
            burst_triggered=False,
        )

        self._emitters[emitter_id] = state
        self._particle_pools[emitter_id] = []
        self._creation_counter += 1

        # Prewarm if configured
        if config.prewarm:
            self._prewarm_state(state)

        return state

    def update_emitter(
        self, emitter_id: str, delta_time: float
    ) -> List[Particle]:
        """Update a single emitter: emit new particles, update existing ones, remove dead ones.

        Args:
            emitter_id: The emitter's unique identifier.
            delta_time: Frame delta time in seconds.

        Returns:
            List of currently active particles for this emitter.
        """
        state = self._emitters.get(emitter_id)
        if state is None:
            return []

        if not state.active:
            return self._particle_pools.get(emitter_id, [])

        if delta_time <= 0.0:
            return self._particle_pools.get(emitter_id, [])

        config = state.config

        # Update elapsed time
        state.elapsed += delta_time

        # Check emitter lifetime
        if config.emitter_lifetime == EmitterLifetime.DURATION:
            if state.elapsed >= config.emitter_duration:
                state.active = False
                return self._particle_pools.get(emitter_id, [])

        # Emit new particles (continuous and burst)
        particles = self._particle_pools.get(emitter_id, [])

        if config.emitter_lifetime in (EmitterLifetime.CONTINUOUS, EmitterLifetime.DURATION):
            # Fractional emission accumulation
            state.accumulation += config.emission_rate * delta_time
            while state.accumulation >= 1.0:
                state.accumulation -= 1.0
                if len(particles) < config.max_particles:
                    particle = self._emit_particle(state)
                    if particle is not None:
                        particles.append(particle)

        # Handle burst if not yet triggered
        if config.emitter_lifetime == EmitterLifetime.BURST and not state.burst_triggered:
            state.burst_triggered = True
            burst_count = config.emission_burst_count if config.emission_burst_count > 0 else int(config.emission_rate)
            for _ in range(burst_count):
                if len(particles) < config.max_particles:
                    particle = self._emit_particle(state)
                    if particle is not None:
                        particles.append(particle)
            state.active = False

        # Update existing particles
        alive_particles: List[Particle] = []
        for particle in particles:
            self._update_particle(particle, config, delta_time)
            if particle.active and particle.life_elapsed < particle.life_max:
                alive_particles.append(particle)
            else:
                self._active_particles = max(0, self._active_particles - 1)

        self._particle_pools[emitter_id] = alive_particles
        return alive_particles

    def update_all(self, delta_time: float) -> Dict[str, List[Particle]]:
        """Update all active emitters.

        Args:
            delta_time: Frame delta time in seconds.

        Returns:
            Dict mapping emitter_id to list of active particles.
        """
        result: Dict[str, List[Particle]] = {}
        for emitter_id in list(self._emitters.keys()):
            particles = self.update_emitter(emitter_id, delta_time)
            if particles:
                result[emitter_id] = particles
        return result

    def _emit_particle(self, state: EmitterState) -> Optional[Particle]:
        """Create a single particle based on the emitter's configuration.

        Calculates initial position based on emission shape, velocity based
        on angle range and speed range, and applies emitter rotation to the
        emission direction.

        Args:
            state: The emitter state.

        Returns:
            A new Particle instance, or None if global limit is reached.
        """
        if self._active_particles >= self._max_particles:
            return None

        config = state.config

        # Compute spawn position
        pos_x, pos_y = self._compute_spawn_position(state, config)

        # Compute initial velocity
        vel_x, vel_y = self._compute_velocity(state, config)

        # Randomize lifetime
        lifetime = random.uniform(config.life_min, config.life_max)
        lifetime = max(lifetime, 0.01)

        # Randomize size endpoints
        size_start = random.uniform(config.size_start_min, config.size_start_max)
        size_end = random.uniform(config.size_end_min, config.size_end_max)

        # Randomize rotation endpoints
        rot_start = random.uniform(0.0, 360.0)
        rot_end = random.uniform(0.0, 360.0)
        angular_vel = random.uniform(-180.0, 180.0)

        particle = Particle(
            particle_id=uuid.uuid4().hex[:12],
            emitter_id=state.emitter_id,
            texture_id=config.texture_id,
            position_x=pos_x,
            position_y=pos_y,
            velocity_x=vel_x,
            velocity_y=vel_y,
            acceleration_x=0.0,
            acceleration_y=0.0,
            life_elapsed=0.0,
            life_max=lifetime,
            size_start=size_start,
            size_end=size_end,
            color_rgba_start=config.color_start,
            color_rgba_end=config.color_end,
            rotation_start=rot_start,
            rotation_end=rot_end,
            angular_velocity=angular_vel,
            active=True,
            blend_mode=config.blend_mode,
            gravity_scale=1.0,
        )

        state.particle_count += 1
        self._active_particles += 1
        return particle

    def _update_particle(
        self,
        particle: Particle,
        config: EmitterConfig,
        delta_time: float,
    ) -> None:
        """Update particle position, velocity, life, size, and color.

        Applies gravity, radial/tangential acceleration, damping, and
        interpolates size and color based on life ratio.

        Args:
            particle: The particle to update.
            config: The emitter configuration.
            delta_time: Frame delta time in seconds.
        """
        if not particle.active:
            return

        # Advance life
        particle.life_elapsed += delta_time

        # Dead check
        if particle.life_elapsed >= particle.life_max:
            particle.active = False
            return

        # Compute radial and tangential accelerations
        rad_accel_x = 0.0
        rad_accel_y = 0.0
        tan_accel_x = 0.0
        tan_accel_y = 0.0

        dist_sq = particle.position_x * particle.position_x + particle.position_y * particle.position_y
        if dist_sq > 0.0001:
            dist = math.sqrt(dist_sq)
            # Radial direction (normalized position from origin)
            rad_x = particle.position_x / dist
            rad_y = particle.position_y / dist
            # Tangential direction (perpendicular to radial)
            tan_x = -rad_y
            tan_y = rad_x

            rad_accel_x = rad_x * config.radial_accel
            rad_accel_y = rad_y * config.radial_accel
            tan_accel_x = tan_x * config.tangential_accel
            tan_accel_y = tan_y * config.tangential_accel

        # Apply acceleration: gravity + radial + tangential
        particle.acceleration_x = config.gravity_x * particle.gravity_scale + rad_accel_x + tan_accel_x
        particle.acceleration_y = config.gravity_y * particle.gravity_scale + rad_accel_y + tan_accel_y

        # Integrate velocity
        particle.velocity_x += particle.acceleration_x * delta_time
        particle.velocity_y += particle.acceleration_y * delta_time

        # Apply damping (velocity multiplier per second)
        damping_factor = config.damping ** delta_time
        particle.velocity_x *= damping_factor
        particle.velocity_y *= damping_factor

        # Integrate position
        particle.position_x += particle.velocity_x * delta_time
        particle.position_y += particle.velocity_y * delta_time

        # Update rotation
        particle.rotation_start += particle.angular_velocity * delta_time

    # ------------------------------------------------------------------
    # Emitter query and control
    # ------------------------------------------------------------------

    def get_emitter_state(self, emitter_id: str) -> Optional[EmitterState]:
        """Get current state of an emitter.

        Args:
            emitter_id: The emitter's unique identifier.

        Returns:
            The EmitterState instance, or None if not found.
        """
        return self._emitters.get(emitter_id)

    def set_emitter_position(self, emitter_id: str, x: float, y: float) -> bool:
        """Move an emitter to a new position.

        Args:
            emitter_id: The emitter's unique identifier.
            x: New world-space X position.
            y: New world-space Y position.

        Returns:
            True if the emitter was found and moved, False otherwise.
        """
        state = self._emitters.get(emitter_id)
        if state is None:
            return False
        state.position_x = x
        state.position_y = y
        return True

    def set_emitter_rotation(self, emitter_id: str, rotation: float) -> bool:
        """Set emitter rotation in degrees.

        Args:
            emitter_id: The emitter's unique identifier.
            rotation: Rotation angle in degrees.

        Returns:
            True if the emitter was found and rotated, False otherwise.
        """
        state = self._emitters.get(emitter_id)
        if state is None:
            return False
        state.rotation = rotation
        return True

    def set_emitter_active(self, emitter_id: str, active: bool) -> bool:
        """Activate or deactivate an emitter.

        Args:
            emitter_id: The emitter's unique identifier.
            active: True to activate, False to deactivate.

        Returns:
            True if the emitter was found, False otherwise.
        """
        state = self._emitters.get(emitter_id)
        if state is None:
            return False
        state.active = active
        return True

    def remove_emitter(self, emitter_id: str) -> bool:
        """Remove emitter and all its particles.

        Args:
            emitter_id: The emitter's unique identifier.

        Returns:
            True if the emitter was removed, False if not found.
        """
        if emitter_id not in self._emitters:
            return False

        # Count particles being removed
        particles = self._particle_pools.pop(emitter_id, [])
        self._active_particles = max(0, self._active_particles - len(particles))
        del self._emitters[emitter_id]
        return True

    def burst(self, emitter_id: str, count: int) -> List[Particle]:
        """Emit a burst of particles immediately.

        Args:
            emitter_id: The emitter's unique identifier.
            count: Number of particles to emit in this burst.

        Returns:
            List of newly created particles.
        """
        state = self._emitters.get(emitter_id)
        if state is None:
            return []

        if count <= 0:
            return []

        particles = self._particle_pools.get(emitter_id, [])
        new_particles: List[Particle] = []

        config = state.config
        max_allowed = config.max_particles - len(particles)
        actual_count = min(count, max_allowed)

        for _ in range(actual_count):
            particle = self._emit_particle(state)
            if particle is not None:
                particles.append(particle)
                new_particles.append(particle)

        self._particle_pools[emitter_id] = particles
        return new_particles

    # ------------------------------------------------------------------
    # Statistics and lifecycle
    # ------------------------------------------------------------------

    def get_active_stats(self) -> Dict[str, Any]:
        """Return statistics about the particle system.

        Returns:
            Dict with active_emitters, active_particles, memory estimate, and more.
        """
        active_emitter_count = sum(1 for s in self._emitters.values() if s.active)
        total_particles = sum(len(p) for p in self._particle_pools.values())
        memory_kb = total_particles * self._BYTES_PER_PARTICLE / 1024.0

        return {
            "active_emitters": active_emitter_count,
            "total_emitters": len(self._emitters),
            "active_particles": self._active_particles,
            "total_particles_tracked": total_particles,
            "max_particles": self._max_particles,
            "memory_estimate_kb": round(memory_kb, 2),
            "creation_counter": self._creation_counter,
        }

    def clear_all(self) -> None:
        """Clear all emitters and particles."""
        with self._lock:
            self._emitters.clear()
            self._particle_pools.clear()
            self._active_particles = 0
            self._creation_counter = 0

    def set_max_particles(self, max_count: int) -> None:
        """Set global particle limit.

        Args:
            max_count: Maximum number of particles allowed globally.
        """
        self._max_particles = max(max_count, 0)

    def prewarm_emitter(self, emitter_id: str) -> None:
        """Pre-simulate an emitter to fill its initial state.

        Advances the emitter by its full particle lifetime to populate
        the particle pool before the first visible frame.

        Args:
            emitter_id: The emitter's unique identifier.
        """
        state = self._emitters.get(emitter_id)
        if state is None:
            return
        self._prewarm_state(state)

    def _prewarm_state(self, state: EmitterState) -> None:
        """Internal prewarm routine for a single emitter state."""
        config = state.config
        max_lifetime = config.life_max
        if max_lifetime <= 0.0:
            return

        # Simulate enough steps to fill the emitter
        steps = max(1, int(max_lifetime / 0.016))
        sim_dt = max_lifetime / steps

        was_active = state.active
        state.active = True

        for _ in range(steps):
            self.update_emitter(state.emitter_id, sim_dt)

        state.active = was_active


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_particle_system() -> EngineParticleSystem:
    """Return the global EngineParticleSystem singleton instance."""
    return EngineParticleSystem.get_instance()