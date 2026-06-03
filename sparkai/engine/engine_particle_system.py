"""
SparkLabs Engine - Particle System

A comprehensive particle effects engine for the SparkLabs game
framework. Manages the full lifecycle of particle emitters, individual
particle simulation, and composite effect orchestration. Supports
multiple emission shapes, blend modes, and trigger-based effect
composition for building explosions, trails, ambient effects, and
custom visual phenomena.

Architecture:
  EngineParticleSystem (Singleton)
    |-- ParticleEmitter        — emission configuration and lifecycle
    |-- ParticleDefinition     — per-particle state (position, velocity, color)
    |-- ParticleEffect         — composite of multiple emitters with triggers
    |-- EmissionShape (enum)   — spawn geometry shapes
    |-- BlendMode (enum)       — rendering blend operations
    |-- ParticleTrigger (enum) — effect activation conditions

Usage:
    ps = get_particle_system()
    emitter_id = ps.create_emitter("fire_emitter", emission_shape="cone",
        emission_rate=80, max_particles=400, particle_lifetime=(0.5, 1.5),
        speed_range=(0.5, 2.0), blend_mode="additive")
    ps.start_emitter(emitter_id)
    ps.update_particles(0.016)
    active = ps.get_active_particles()
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


class EmissionShape(Enum):
    """Geometry shape defining the spawn region of particles.

    POINT:       Single point origin.
    CIRCLE:      Flat circular area around the emitter.
    RECTANGLE:   Axis-aligned rectangular region.
    CONE:        Directional cone with configurable angle.
    EDGE:        Linear edge segment.
    RING:        Hollow ring around the emitter center.
    SPHERE:      Volumetric spherical shell.
    HEMISPHERE:  Half-sphere dome shape.
    """

    POINT = "point"
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    CONE = "cone"
    EDGE = "edge"
    RING = "ring"
    SPHERE = "sphere"
    HEMISPHERE = "hemisphere"


class BlendMode(Enum):
    """Rendering blend operation for particle compositing.

    NORMAL:         Standard alpha blending.
    ADDITIVE:       Additive blend for fire, magic, glow effects.
    MULTIPLY:       Darkening multiply blend for shadows and smoke.
    SCREEN:         Screen blend for light and soft glow.
    ALPHA:          Traditional alpha transparency.
    PREMULTIPLIED:  Pre-multiplied alpha for correct compositing.
    """

    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    ALPHA = "alpha"
    PREMULTIPLIED = "premultiplied"


class ParticleTrigger(Enum):
    """Activation conditions for composite particle effects.

    ON_SPAWN:     Trigger when the effect is first spawned.
    ON_DEATH:     Trigger when the effect's duration expires.
    ON_COLLISION: Trigger upon collision with world geometry.
    MANUAL:       Triggered explicitly via code.
    TIMED:        Triggered at a scheduled time offset.
    """

    ON_SPAWN = "on_spawn"
    ON_DEATH = "on_death"
    ON_COLLISION = "on_collision"
    MANUAL = "manual"
    TIMED = "timed"


# ------------------------------------------------------------------
# Pre-defined effect templates
# ------------------------------------------------------------------

_EXPLOSION_TEMPLATE: Dict[str, Any] = {
    "name": "Explosion",
    "description": "High-energy burst with debris, fire, and smoke layers",
    "emitters": [
        {
            "name": "explosion_core",
            "emission_shape": "sphere",
            "emission_rate": 300,
            "max_particles": 600,
            "particle_lifetime": (0.2, 0.8),
            "speed_range": (3.0, 10.0),
            "spread": 6.283,
            "blend_mode": "additive",
            "burst_count": 300,
            "looping": False,
        },
        {
            "name": "explosion_sparks",
            "emission_shape": "sphere",
            "emission_rate": 150,
            "max_particles": 300,
            "particle_lifetime": (0.3, 1.2),
            "speed_range": (2.0, 7.0),
            "spread": 6.283,
            "blend_mode": "additive",
            "burst_count": 150,
            "looping": False,
        },
        {
            "name": "explosion_smoke",
            "emission_shape": "hemisphere",
            "emission_rate": 40,
            "max_particles": 100,
            "particle_lifetime": (1.0, 3.0),
            "speed_range": (0.5, 2.0),
            "spread": 1.5,
            "gravity": (0.0, -0.5, 0.0),
            "blend_mode": "alpha",
            "burst_count": 40,
            "looping": False,
        },
    ],
    "duration": 1.5,
    "looping": False,
    "trigger_on": "on_spawn",
    "tags": ["explosion", "burst", "combat", "destruction"],
}

_TRAIL_TEMPLATE: Dict[str, Any] = {
    "name": "Trail",
    "description": "Continuous trailing ribbon effect for projectiles and movement",
    "emitters": [
        {
            "name": "trail_ribbon",
            "emission_shape": "point",
            "emission_rate": 60,
            "max_particles": 200,
            "particle_lifetime": (0.3, 0.8),
            "speed_range": (0.1, 0.5),
            "spread": 0.1,
            "blend_mode": "additive",
            "burst_count": 0,
            "looping": True,
        },
    ],
    "duration": 0.0,
    "looping": True,
    "trigger_on": "on_spawn",
    "tags": ["trail", "movement", "projectile", "continuous"],
}

_AMBIENT_TEMPLATE: Dict[str, Any] = {
    "name": "Ambient",
    "description": "Soft atmospheric particles for mood and environment",
    "emitters": [
        {
            "name": "ambient_dust",
            "emission_shape": "rectangle",
            "emission_rate": 10,
            "max_particles": 100,
            "particle_lifetime": (3.0, 8.0),
            "speed_range": (0.1, 0.5),
            "spread": 6.283,
            "gravity": (0.0, 0.05, 0.0),
            "blend_mode": "alpha",
            "burst_count": 0,
            "looping": True,
        },
    ],
    "duration": 0.0,
    "looping": True,
    "trigger_on": "on_spawn",
    "tags": ["ambient", "atmosphere", "dust", "environment"],
}


@dataclass
class ParticleEmitter:
    """Configuration and runtime state for a single particle emitter.

    Defines the emission rate, shape, lifetime range, velocity range,
    direction, spread, gravity, blend mode, and burst behavior for
    spawning particles. Supports looping and auto-start for automatic
    activation on creation.
    """

    emitter_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    position: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    emission_shape: EmissionShape = EmissionShape.POINT
    emission_rate: float = 50.0
    max_particles: int = 500
    particle_lifetime: Tuple[float, float] = field(default_factory=lambda: (1.0, 3.0))
    speed_range: Tuple[float, float] = field(default_factory=lambda: (1.0, 3.0))
    direction: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 1.0, 0.0))
    spread: float = 0.785
    gravity: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    texture: str = ""
    blend_mode: BlendMode = BlendMode.ALPHA
    burst_count: int = 0
    looping: bool = True
    auto_start: bool = False
    active: bool = False
    elapsed: float = 0.0
    emission_accumulator: float = 0.0
    shape_radius: float = 1.0
    shape_width: float = 1.0
    shape_height: float = 1.0
    cone_angle: float = 0.523
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emitter_id": self.emitter_id,
            "name": self.name,
            "position": list(self.position),
            "emission_shape": self.emission_shape.value,
            "emission_rate": self.emission_rate,
            "max_particles": self.max_particles,
            "particle_lifetime": list(self.particle_lifetime),
            "speed_range": list(self.speed_range),
            "direction": list(self.direction),
            "spread": self.spread,
            "gravity": list(self.gravity),
            "texture": self.texture,
            "blend_mode": self.blend_mode.value,
            "burst_count": self.burst_count,
            "looping": self.looping,
            "auto_start": self.auto_start,
            "active": self.active,
            "elapsed": self.elapsed,
            "shape_radius": self.shape_radius,
            "shape_width": self.shape_width,
            "shape_height": self.shape_height,
            "cone_angle": self.cone_angle,
            "created_at": self.created_at,
        }


@dataclass
class ParticleDefinition:
    """Individual particle state for simulation and rendering.

    Tracks per-particle properties including position, velocity, lifetime,
    interpolated size and color endpoints, alpha fade, rotation, and
    liveness flag for recycling.
    """

    particle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    emitter_id: str = ""
    position: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    velocity: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    lifetime: float = 1.0
    size_start: float = 1.0
    size_end: float = 0.0
    color_start: Tuple[float, float, float] = field(default_factory=lambda: (1.0, 1.0, 1.0))
    color_end: Tuple[float, float, float] = field(default_factory=lambda: (1.0, 1.0, 1.0))
    alpha_start: float = 1.0
    alpha_end: float = 0.0
    rotation_start: float = 0.0
    rotation_end: float = 0.0
    age: float = 0.0
    alive: bool = True
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "particle_id": self.particle_id,
            "emitter_id": self.emitter_id,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "lifetime": self.lifetime,
            "size_start": self.size_start,
            "size_end": self.size_end,
            "color_start": list(self.color_start),
            "color_end": list(self.color_end),
            "alpha_start": self.alpha_start,
            "alpha_end": self.alpha_end,
            "rotation_start": self.rotation_start,
            "rotation_end": self.rotation_end,
            "age": self.age,
            "alive": self.alive,
            "progress": self.age / max(self.lifetime, 0.0001),
            "current_size": self.size_start + (self.size_end - self.size_start) * (self.age / max(self.lifetime, 0.0001)),
            "current_alpha": self.alpha_start + (self.alpha_end - self.alpha_start) * (self.age / max(self.lifetime, 0.0001)),
            "created_at": self.created_at,
        }


@dataclass
class ParticleEffect:
    """Composite effect composed of multiple emitters with trigger logic.

    Groups several ParticleEmitter configurations into a single named
    effect that can be activated with trigger conditions. Supports
    duration limits, looping, position offsets, and tag-based querying.
    """

    effect_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    emitters: List[ParticleEmitter] = field(default_factory=list)
    duration: float = 0.0
    looping: bool = False
    trigger_on: ParticleTrigger = ParticleTrigger.ON_SPAWN
    position_offset: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    tags: List[str] = field(default_factory=list)
    elapsed: float = 0.0
    active: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "name": self.name,
            "emitters": [e.to_dict() for e in self.emitters],
            "emitter_count": len(self.emitters),
            "duration": self.duration,
            "looping": self.looping,
            "trigger_on": self.trigger_on.value,
            "position_offset": list(self.position_offset),
            "tags": list(self.tags),
            "elapsed": self.elapsed,
            "active": self.active,
            "created_at": self.created_at,
        }


class EngineParticleSystem:
    """Comprehensive particle effects engine for the SparkLabs framework.

    Manages the full lifecycle of particle emitters, individual particle
    simulation, and composite effect orchestration. Provides methods for
    creating emitters with configurable shapes and blend modes, building
    multi-emitter effects with trigger logic, and running per-frame
    particle updates with interpolation.

    Usage:
        ps = get_particle_system()
        emitter_id = ps.create_emitter("fire", emission_shape="cone",
            emission_rate=80, max_particles=400, particle_lifetime=(0.5, 1.5),
            speed_range=(0.5, 2.0), blend_mode="additive")
        ps.start_emitter(emitter_id)
        ps.update_particles(0.016)
        active = ps.get_active_particles()
    """

    _instance: Optional["EngineParticleSystem"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_EMITTERS: int = 512
    MAX_PARTICLES_GLOBAL: int = 50000
    MAX_EFFECTS: int = 256
    MAX_PARTICLES_PER_EMITTER: int = 10000

    def __new__(cls) -> "EngineParticleSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._emitters: Dict[str, ParticleEmitter] = {}
        self._particles: Dict[str, ParticleDefinition] = {}
        self._effects: Dict[str, ParticleEffect] = {}
        self._emitter_particles: Dict[str, List[str]] = {}
        self._total_particles_spawned: int = 0
        self._total_particles_destroyed: int = 0
        self._total_emitters_created: int = 0
        self._total_effects_created: int = 0
        self._total_bursts_fired: int = 0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "EngineParticleSystem":
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_emitter(self, emitter_id: str) -> ParticleEmitter:
        _time_module.sleep(0.001)
        if emitter_id not in self._emitters:
            raise KeyError(f"ParticleEmitter '{emitter_id}' does not exist")
        return self._emitters[emitter_id]

    def _get_effect(self, effect_id: str) -> ParticleEffect:
        _time_module.sleep(0.001)
        if effect_id not in self._effects:
            raise KeyError(f"ParticleEffect '{effect_id}' does not exist")
        return self._effects[effect_id]

    def _parse_enum(self, enum_cls: type, value: Any) -> Enum:
        _time_module.sleep(0.001)
        if isinstance(value, enum_cls):
            return value
        try:
            return enum_cls(str(value).lower())
        except ValueError:
            return list(enum_cls)[0]

    def _compute_spawn_position(
        self,
        emitter: ParticleEmitter,
        shape: EmissionShape,
    ) -> Tuple[float, float, float]:
        _time_module.sleep(0.001)
        px, py, pz = emitter.position

        if shape == EmissionShape.POINT:
            return (px, py, pz)

        elif shape == EmissionShape.CIRCLE:
            angle = random.uniform(0.0, 2.0 * math.pi)
            r = random.uniform(0.0, emitter.shape_radius)
            return (px + math.cos(angle) * r, py, pz + math.sin(angle) * r)

        elif shape == EmissionShape.RECTANGLE:
            hw = emitter.shape_width * 0.5
            hh = emitter.shape_height * 0.5
            return (
                px + random.uniform(-hw, hw),
                py,
                pz + random.uniform(-hh, hh),
            )

        elif shape == EmissionShape.CONE:
            angle = random.uniform(0.0, 2.0 * math.pi)
            spread_r = random.uniform(0.0, emitter.shape_radius)
            return (
                px + math.cos(angle) * spread_r,
                py,
                pz + math.sin(angle) * spread_r,
            )

        elif shape == EmissionShape.EDGE:
            t = random.uniform(-0.5, 0.5)
            return (
                px + t * emitter.shape_width,
                py,
                pz,
            )

        elif shape == EmissionShape.RING:
            angle = random.uniform(0.0, 2.0 * math.pi)
            inner = emitter.shape_radius * 0.5
            outer = emitter.shape_radius
            r = random.uniform(inner, outer)
            return (px + math.cos(angle) * r, py, pz + math.sin(angle) * r)

        elif shape == EmissionShape.SPHERE:
            theta = random.uniform(0.0, 2.0 * math.pi)
            phi = random.uniform(0.0, math.pi)
            r = emitter.shape_radius * random.random()
            return (
                px + r * math.sin(phi) * math.cos(theta),
                py + r * math.sin(phi) * math.sin(theta),
                pz + r * math.cos(phi),
            )

        elif shape == EmissionShape.HEMISPHERE:
            theta = random.uniform(0.0, 2.0 * math.pi)
            phi = random.uniform(0.0, math.pi * 0.5)
            r = emitter.shape_radius * random.random()
            return (
                px + r * math.sin(phi) * math.cos(theta),
                py + r * math.cos(phi),
                pz + r * math.sin(phi) * math.sin(theta),
            )

        return (px, py, pz)

    def _compute_velocity(
        self,
        emitter: ParticleEmitter,
    ) -> Tuple[float, float, float]:
        _time_module.sleep(0.001)
        dx, dy, dz = emitter.direction
        dir_len = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dir_len < 0.0001:
            dx, dy, dz = 0.0, 1.0, 0.0
            dir_len = 1.0

        ndx = dx / dir_len
        ndy = dy / dir_len
        ndz = dz / dir_len

        half_spread = emitter.spread * 0.5
        pitch = random.uniform(-half_spread, half_spread)
        yaw = random.uniform(-half_spread, half_spread)

        cos_p = math.cos(pitch)
        sin_p = math.sin(pitch)
        cos_y = math.cos(yaw)
        sin_y = math.sin(yaw)

        vx = ndx * cos_p * cos_y - ndz * sin_y + ndy * sin_p * cos_y
        vy = ndy * cos_p - ndx * sin_p
        vz = ndz * cos_p * cos_y + ndx * sin_y + ndy * sin_p * sin_y

        v_len = math.sqrt(vx * vx + vy * vy + vz * vz)
        if v_len < 0.0001:
            vx, vy, vz = ndx, ndy, ndz
            v_len = 1.0

        speed = random.uniform(emitter.speed_range[0], emitter.speed_range[1])
        return (vx / v_len * speed, vy / v_len * speed, vz / v_len * speed)

    def _spawn_single_particle(self, emitter: ParticleEmitter) -> Optional[ParticleDefinition]:
        _time_module.sleep(0.001)
        if len(self._particles) >= self.MAX_PARTICLES_GLOBAL:
            return None

        emitter_particles = self._emitter_particles.get(emitter.emitter_id, [])
        if len(emitter_particles) >= emitter.max_particles:
            return None

        shape = emitter.emission_shape
        position = self._compute_spawn_position(emitter, shape)
        velocity = self._compute_velocity(emitter)

        lifetime = random.uniform(
            emitter.particle_lifetime[0], emitter.particle_lifetime[1]
        )
        lifetime = max(lifetime, 0.01)

        particle = ParticleDefinition(
            emitter_id=emitter.emitter_id,
            position=position,
            velocity=velocity,
            lifetime=lifetime,
            size_start=1.0,
            size_end=0.0,
            color_start=(1.0, 1.0, 1.0),
            color_end=(1.0, 1.0, 1.0),
            alpha_start=1.0,
            alpha_end=0.0,
            rotation_start=random.uniform(0.0, 2.0 * math.pi),
            rotation_end=random.uniform(0.0, 2.0 * math.pi),
        )

        self._particles[particle.particle_id] = particle
        emitter_particles.append(particle.particle_id)
        self._emitter_particles[emitter.emitter_id] = emitter_particles
        self._total_particles_spawned += 1
        return particle

    def _remove_particle(self, particle_id: str) -> None:
        _time_module.sleep(0.001)
        if particle_id not in self._particles:
            return
        particle = self._particles[particle_id]
        emitter_id = particle.emitter_id
        if emitter_id in self._emitter_particles:
            particles_list = self._emitter_particles[emitter_id]
            if particle_id in particles_list:
                particles_list.remove(particle_id)
        del self._particles[particle_id]
        self._total_particles_destroyed += 1

    # ------------------------------------------------------------------
    # Emitter management
    # ------------------------------------------------------------------

    def create_emitter(
        self,
        name: str,
        position: Optional[Tuple[float, float, float]] = None,
        emission_shape: str = "point",
        emission_rate: float = 50.0,
        max_particles: int = 500,
        particle_lifetime: Optional[Tuple[float, float]] = None,
        speed_range: Optional[Tuple[float, float]] = None,
        direction: Optional[Tuple[float, float, float]] = None,
        spread: float = 0.785,
        gravity: Optional[Tuple[float, float, float]] = None,
        texture: str = "",
        blend_mode: str = "alpha",
        burst_count: int = 0,
        looping: bool = True,
        auto_start: bool = False,
        shape_radius: float = 1.0,
        shape_width: float = 1.0,
        shape_height: float = 1.0,
        cone_angle: float = 0.523,
    ) -> ParticleEmitter:
        """Create a new particle emitter with the given configuration.

        Args:
            name: Human-readable emitter name.
            position: World-space origin (x, y, z). Defaults to (0, 0, 0).
            emission_shape: Shape of the spawn region. One of point, circle,
                rectangle, cone, edge, ring, sphere, hemisphere.
            emission_rate: Particles emitted per second.
            max_particles: Maximum alive particles for this emitter.
            particle_lifetime: (min, max) lifetime range per particle.
            speed_range: (min, max) initial speed range per particle.
            direction: Normalized emission direction vector.
            spread: Angular spread in radians around the direction.
            gravity: Constant acceleration applied to particles.
            texture: Asset key for the particle sprite.
            blend_mode: Rendering blend mode.
            burst_count: Particles emitted on first activation.
            looping: Whether emission restarts after max_particles is reached.
            auto_start: Begin emitting immediately on creation.
            shape_radius: Radius for circle, sphere, hemisphere, ring shapes.
            shape_width: Width for rectangle and edge shapes.
            shape_height: Height for rectangle shape.
            cone_angle: Cone half-angle in radians for cone shape.

        Returns:
            The created ParticleEmitter dataclass instance.
        """
        _time_module.sleep(0.001)
        if len(self._emitters) >= self.MAX_EMITTERS:
            raise RuntimeError(
                f"Emitter limit reached ({self.MAX_EMITTERS})"
            )

        if particle_lifetime is None:
            particle_lifetime = (1.0, 3.0)
        if speed_range is None:
            speed_range = (1.0, 3.0)
        if position is None:
            position = (0.0, 0.0, 0.0)
        if direction is None:
            direction = (0.0, 1.0, 0.0)
        if gravity is None:
            gravity = (0.0, 0.0, 0.0)

        shape = self._parse_enum(EmissionShape, emission_shape)
        bm = self._parse_enum(BlendMode, blend_mode)

        emitter = ParticleEmitter(
            name=name,
            position=position,
            emission_shape=shape,
            emission_rate=emission_rate,
            max_particles=max_particles,
            particle_lifetime=particle_lifetime,
            speed_range=speed_range,
            direction=direction,
            spread=spread,
            gravity=gravity,
            texture=texture,
            blend_mode=bm,
            burst_count=burst_count,
            looping=looping,
            auto_start=auto_start,
            active=auto_start,
            shape_radius=shape_radius,
            shape_width=shape_width,
            shape_height=shape_height,
            cone_angle=cone_angle,
        )

        self._emitters[emitter.emitter_id] = emitter
        self._emitter_particles[emitter.emitter_id] = []
        self._total_emitters_created += 1

        if auto_start:
            if burst_count > 0:
                self.burst_emit(emitter.emitter_id, burst_count)

        return emitter

    def start_emitter(self, emitter_id: str) -> bool:
        """Activate an emitter so it begins spawning particles.

        Args:
            emitter_id: The emitter's unique identifier.

        Returns:
            True if the emitter was found and started, False otherwise.
        """
        _time_module.sleep(0.001)
        emitter = self._emitters.get(emitter_id)
        if emitter is None:
            return False
        emitter.active = True
        emitter.elapsed = 0.0
        emitter.emission_accumulator = 0.0
        if emitter.burst_count > 0:
            self.burst_emit(emitter_id, emitter.burst_count)
        return True

    def stop_emitter(self, emitter_id: str) -> bool:
        """Deactivate an emitter to halt particle spawning.

        Existing particles continue their lifecycle; only new
        spawning is prevented.

        Args:
            emitter_id: The emitter's unique identifier.

        Returns:
            True if the emitter was found and stopped, False otherwise.
        """
        _time_module.sleep(0.001)
        emitter = self._emitters.get(emitter_id)
        if emitter is None:
            return False
        emitter.active = False
        return True

    def burst_emit(
        self,
        emitter_id: str,
        count: Optional[int] = None,
    ) -> int:
        """Instantaneously spawn a batch of particles from an emitter.

        Args:
            emitter_id: The emitter's unique identifier.
            count: Number of particles to spawn. Uses emitter's
                burst_count if not specified.

        Returns:
            The number of particles actually spawned.
        """
        _time_module.sleep(0.001)
        emitter = self._emitters.get(emitter_id)
        if emitter is None:
            return 0

        spawn_count = count if count is not None else emitter.burst_count
        if spawn_count <= 0:
            return 0

        spawned = 0
        for _ in range(spawn_count):
            if self._spawn_single_particle(emitter) is not None:
                spawned += 1

        self._total_bursts_fired += 1
        return spawned

    def set_emitter_property(
        self,
        emitter_id: str,
        property_name: str,
        value: Any,
    ) -> bool:
        """Set a runtime property on an existing emitter.

        Supported properties: position, emission_rate, max_particles,
        particle_lifetime, speed_range, direction, spread, gravity,
        texture, blend_mode, burst_count, looping, active,
        shape_radius, shape_width, shape_height, cone_angle.

        Args:
            emitter_id: The emitter's unique identifier.
            property_name: Name of the property to modify.
            value: New value for the property.

        Returns:
            True if the property was set successfully, False otherwise.
        """
        _time_module.sleep(0.001)
        emitter = self._emitters.get(emitter_id)
        if emitter is None:
            return False

        settable_properties = {
            "position", "emission_rate", "max_particles",
            "particle_lifetime", "speed_range", "direction",
            "spread", "gravity", "texture", "blend_mode",
            "burst_count", "looping", "active",
            "shape_radius", "shape_width", "shape_height",
            "cone_angle",
        }

        if property_name not in settable_properties:
            return False

        if property_name == "emission_shape":
            emitter.emission_shape = self._parse_enum(EmissionShape, value)
        elif property_name == "blend_mode":
            emitter.blend_mode = self._parse_enum(BlendMode, value)
        elif property_name in (
            "position", "direction", "gravity",
            "particle_lifetime", "speed_range",
        ):
            setattr(emitter, property_name, tuple(value))
        else:
            setattr(emitter, property_name, value)

        return True

    def get_emitter(self, emitter_id: str) -> Optional[ParticleEmitter]:
        """Retrieve an emitter by its unique identifier.

        Args:
            emitter_id: The emitter's unique identifier.

        Returns:
            The ParticleEmitter instance or None if not found.
        """
        _time_module.sleep(0.001)
        return self._emitters.get(emitter_id)

    def list_emitters(self) -> List[ParticleEmitter]:
        """Return a list of all registered emitters."""
        _time_module.sleep(0.001)
        return list(self._emitters.values())

    def remove_emitter(self, emitter_id: str) -> bool:
        """Remove an emitter and all its associated particles.

        Args:
            emitter_id: The emitter's unique identifier.

        Returns:
            True if the emitter was removed, False if not found.
        """
        _time_module.sleep(0.001)
        if emitter_id not in self._emitters:
            return False

        particle_ids = list(self._emitter_particles.get(emitter_id, []))
        for pid in particle_ids:
            self._remove_particle(pid)

        self._emitter_particles.pop(emitter_id, None)
        del self._emitters[emitter_id]
        return True

    # ------------------------------------------------------------------
    # Effect management
    # ------------------------------------------------------------------

    def create_effect(
        self,
        name: str,
        emitters: Optional[List[ParticleEmitter]] = None,
        duration: float = 0.0,
        looping: bool = False,
        trigger_on: str = "on_spawn",
        position_offset: Optional[Tuple[float, float, float]] = None,
        tags: Optional[List[str]] = None,
    ) -> ParticleEffect:
        """Create a composite particle effect from multiple emitters.

        Args:
            name: Human-readable effect name.
            emitters: List of ParticleEmitter instances composing the effect.
            duration: Total effect duration in seconds. 0 means infinite.
            looping: Whether the effect repeats after duration expires.
            trigger_on: Activation trigger condition.
            position_offset: Offset applied to all emitter positions.
            tags: String tags for categorization and querying.

        Returns:
            The created ParticleEffect dataclass instance.
        """
        _time_module.sleep(0.001)
        if len(self._effects) >= self.MAX_EFFECTS:
            raise RuntimeError(
                f"Effect limit reached ({self.MAX_EFFECTS})"
            )

        if position_offset is None:
            position_offset = (0.0, 0.0, 0.0)
        if tags is None:
            tags = []

        trigger = self._parse_enum(ParticleTrigger, trigger_on)

        effect = ParticleEffect(
            name=name,
            emitters=emitters or [],
            duration=duration,
            looping=looping,
            trigger_on=trigger,
            position_offset=position_offset,
            tags=tags,
        )

        self._effects[effect.effect_id] = effect
        self._total_effects_created += 1

        for emitter in effect.emitters:
            if emitter.emitter_id not in self._emitters:
                self._emitters[emitter.emitter_id] = emitter
                self._emitter_particles[emitter.emitter_id] = []
                self._total_emitters_created += 1

        return effect

    def spawn_particles(
        self,
        emitter_id: str,
        position: Optional[Tuple[float, float, float]] = None,
        count: Optional[int] = None,
    ) -> int:
        """Spawn particles from a specific emitter at an optional position.

        Temporarily overrides the emitter's position for this spawn
        operation if a position is provided.

        Args:
            emitter_id: The emitter's unique identifier.
            position: Override spawn position. Uses emitter's position if None.
            count: Number of particles to spawn. Uses emitter's
                emission_rate fraction if None.

        Returns:
            The number of particles actually spawned.
        """
        _time_module.sleep(0.001)
        emitter = self._emitters.get(emitter_id)
        if emitter is None:
            return 0

        original_position = emitter.position
        if position is not None:
            emitter.position = position

        spawn_count = count if count is not None else max(1, int(emitter.emission_rate * 0.1))
        spawned = 0
        for _ in range(spawn_count):
            if self._spawn_single_particle(emitter) is not None:
                spawned += 1

        emitter.position = original_position
        return spawned

    def update_particles(self, delta_time: float) -> Dict[str, Any]:
        """Advance all active particle simulations by one frame.

        Handles continuous emission, particle aging, velocity integration,
        gravity application, and dead particle cleanup.

        Args:
            delta_time: Frame delta time in seconds.

        Returns:
            Statistics dict with born, died, and active counts.
        """
        _time_module.sleep(0.001)
        total_spawned = 0
        total_destroyed = 0

        for emitter in self._emitters.values():
            if not emitter.active:
                continue

            emitter.elapsed += delta_time
            emitter.emission_accumulator += emitter.emission_rate * delta_time

            while emitter.emission_accumulator >= 1.0:
                emitter.emission_accumulator -= 1.0
                if self._spawn_single_particle(emitter) is not None:
                    total_spawned += 1

            if not emitter.looping and emitter.elapsed >= 5.0:
                emitter.active = False

        for effect in self._effects.values():
            if not effect.active:
                continue
            effect.elapsed += delta_time
            if effect.duration > 0.0 and effect.elapsed >= effect.duration:
                if effect.looping:
                    effect.elapsed = 0.0
                else:
                    effect.active = False

        dead_particles: List[str] = []
        for particle_id, particle in self._particles.items():
            if not particle.alive:
                dead_particles.append(particle_id)
                continue

            particle.age += delta_time
            if particle.age >= particle.lifetime:
                particle.alive = False
                dead_particles.append(particle_id)
                continue

            emitter = self._emitters.get(particle.emitter_id)
            if emitter is not None:
                gx, gy, gz = emitter.gravity
                vx, vy, vz = particle.velocity
                vx += gx * delta_time
                vy += gy * delta_time
                vz += gz * delta_time
                particle.velocity = (vx, vy, vz)

            px, py, pz = particle.position
            vx, vy, vz = particle.velocity
            particle.position = (
                px + vx * delta_time,
                py + vy * delta_time,
                pz + vz * delta_time,
            )

        for pid in dead_particles:
            self._remove_particle(pid)
            total_destroyed += 1

        return {
            "particles_spawned": total_spawned,
            "particles_destroyed": total_destroyed,
            "total_active": len(self._particles),
            "total_emitters_active": sum(1 for e in self._emitters.values() if e.active),
            "total_effects_active": sum(1 for e in self._effects.values() if e.active),
        }

    def get_active_particles(self) -> List[ParticleDefinition]:
        """Return all currently alive particles across all emitters.

        Returns:
            List of alive ParticleDefinition instances.
        """
        _time_module.sleep(0.001)
        return [p for p in self._particles.values() if p.alive]

    def get_particles_by_emitter(self, emitter_id: str) -> List[ParticleDefinition]:
        """Return all particles belonging to a specific emitter.

        Args:
            emitter_id: The emitter's unique identifier.

        Returns:
            List of ParticleDefinition instances for the emitter.
        """
        _time_module.sleep(0.001)
        particle_ids = self._emitter_particles.get(emitter_id, [])
        return [
            self._particles[pid]
            for pid in particle_ids
            if pid in self._particles and self._particles[pid].alive
        ]

    def activate_effect(
        self,
        effect_id: str,
        position: Optional[Tuple[float, float, float]] = None,
    ) -> bool:
        """Activate a composite effect, starting all its emitters.

        Args:
            effect_id: The effect's unique identifier.
            position: World position to place the effect.

        Returns:
            True if the effect was activated, False if not found.
        """
        _time_module.sleep(0.001)
        effect = self._effects.get(effect_id)
        if effect is None:
            return False

        effect.active = True
        effect.elapsed = 0.0

        for emitter in effect.emitters:
            if position is not None:
                ox, oy, oz = effect.position_offset
                px, py, pz = position
                emitter.position = (px + ox, py + oy, pz + oz)
            emitter.active = True
            emitter.elapsed = 0.0
            emitter.emission_accumulator = 0.0
            if emitter.burst_count > 0:
                self.burst_emit(emitter.emitter_id, emitter.burst_count)

        return True

    def deactivate_effect(self, effect_id: str) -> bool:
        """Deactivate a composite effect, stopping all its emitters.

        Args:
            effect_id: The effect's unique identifier.

        Returns:
            True if the effect was deactivated, False if not found.
        """
        _time_module.sleep(0.001)
        effect = self._effects.get(effect_id)
        if effect is None:
            return False

        effect.active = False
        for emitter in effect.emitters:
            emitter.active = False
        return True

    def get_effect(self, effect_id: str) -> Optional[ParticleEffect]:
        """Retrieve an effect by its unique identifier.

        Args:
            effect_id: The effect's unique identifier.

        Returns:
            The ParticleEffect instance or None if not found.
        """
        _time_module.sleep(0.001)
        return self._effects.get(effect_id)

    def list_effects(self) -> List[ParticleEffect]:
        """Return a list of all registered effects."""
        _time_module.sleep(0.001)
        return list(self._effects.values())

    def remove_effect(self, effect_id: str) -> bool:
        """Remove an effect and optionally its associated emitters.

        Args:
            effect_id: The effect's unique identifier.

        Returns:
            True if the effect was removed, False if not found.
        """
        _time_module.sleep(0.001)
        if effect_id not in self._effects:
            return False
        del self._effects[effect_id]
        return True

    # ------------------------------------------------------------------
    # Preset effect factories
    # ------------------------------------------------------------------

    def create_explosion_effect(
        self,
        position: Optional[Tuple[float, float, float]] = None,
        scale: float = 1.0,
    ) -> ParticleEffect:
        """Create a pre-configured explosion effect with layered emitters.

        Produces a high-energy burst with a bright core flash, scattered
        sparks, and a trailing smoke plume. Automatically activates
        on spawn and stops after its duration.

        Args:
            position: World-space origin of the explosion.
            scale: Multiplier for emitter parameters (radius, rate, speed).

        Returns:
            The created ParticleEffect dataclass instance.
        """
        _time_module.sleep(0.001)
        if position is None:
            position = (0.0, 0.0, 0.0)

        positions = (
            (position[0], position[1] + 0.5 * scale, position[2]),
            (position[0], position[1] + 0.3 * scale, position[2]),
            (position[0], position[1], position[2]),
        )

        core_emitter = self.create_emitter(
            name="explosion_core",
            position=positions[0],
            emission_shape="sphere",
            emission_rate=300.0 * scale,
            max_particles=int(600 * scale),
            particle_lifetime=(0.15, 0.6),
            speed_range=(3.0 * scale, 10.0 * scale),
            spread=6.283,
            gravity=(0.0, -0.1, 0.0),
            blend_mode="additive",
            burst_count=int(300 * scale),
            looping=False,
            shape_radius=0.3 * scale,
        )

        spark_emitter = self.create_emitter(
            name="explosion_sparks",
            position=positions[1],
            emission_shape="sphere",
            emission_rate=150.0 * scale,
            max_particles=int(300 * scale),
            particle_lifetime=(0.3, 1.0),
            speed_range=(2.0 * scale, 7.0 * scale),
            spread=6.283,
            gravity=(0.0, -0.3, 0.0),
            blend_mode="additive",
            burst_count=int(150 * scale),
            looping=False,
            shape_radius=0.5 * scale,
        )

        smoke_emitter = self.create_emitter(
            name="explosion_smoke",
            position=positions[2],
            emission_shape="hemisphere",
            emission_rate=40.0 * scale,
            max_particles=int(100 * scale),
            particle_lifetime=(1.0, 2.5),
            speed_range=(0.5 * scale, 2.0 * scale),
            spread=1.2,
            gravity=(0.0, -0.5, 0.0),
            blend_mode="alpha",
            burst_count=int(40 * scale),
            looping=False,
            shape_radius=1.0 * scale,
        )

        effect = self.create_effect(
            name=f"explosion_{uuid.uuid4().hex[:8]}",
            emitters=[core_emitter, spark_emitter, smoke_emitter],
            duration=1.5,
            looping=False,
            trigger_on="on_spawn",
            position_offset=(0.0, 0.0, 0.0),
            tags=["explosion", "burst", "combat", "destruction"],
        )

        self.activate_effect(effect.effect_id, position)
        return effect

    def create_trail_effect(
        self,
        position: Optional[Tuple[float, float, float]] = None,
        direction: Optional[Tuple[float, float, float]] = None,
        scale: float = 1.0,
    ) -> ParticleEffect:
        """Create a pre-configured continuous trail effect.

        Produces a ribbon-like particle stream suitable for projectiles,
        movement trails, and magical after-effects. Runs continuously
        until manually deactivated.

        Args:
            position: World-space origin of the trail emitter.
            direction: Direction of the trail emission.
            scale: Multiplier for emitter parameters.

        Returns:
            The created ParticleEffect dataclass instance.
        """
        _time_module.sleep(0.001)
        if position is None:
            position = (0.0, 0.0, 0.0)
        if direction is None:
            direction = (0.0, 1.0, 0.0)

        trail_emitter = self.create_emitter(
            name="trail_ribbon",
            position=position,
            emission_shape="point",
            emission_rate=60.0 * scale,
            max_particles=int(200 * scale),
            particle_lifetime=(0.25, 0.7),
            speed_range=(0.1, 0.4),
            direction=direction,
            spread=0.15,
            gravity=(0.0, 0.0, 0.0),
            blend_mode="additive",
            burst_count=0,
            looping=True,
            auto_start=True,
        )

        effect = self.create_effect(
            name=f"trail_{uuid.uuid4().hex[:8]}",
            emitters=[trail_emitter],
            duration=0.0,
            looping=True,
            trigger_on="on_spawn",
            position_offset=(0.0, 0.0, 0.0),
            tags=["trail", "movement", "projectile", "continuous"],
        )

        self.activate_effect(effect.effect_id, position)
        return effect

    def create_ambient_effect(
        self,
        position: Optional[Tuple[float, float, float]] = None,
        area_width: float = 10.0,
        area_height: float = 10.0,
        scale: float = 1.0,
    ) -> ParticleEffect:
        """Create a pre-configured ambient atmospheric effect.

        Produces soft, slow-moving particles such as dust motes, floating
        embers, or magical sparkles within a defined rectangular area.
        Runs continuously until manually deactivated.

        Args:
            position: Center of the ambient effect area.
            area_width: Width of the rectangular emission zone.
            area_height: Height of the rectangular emission zone.
            scale: Multiplier for emitter parameters.

        Returns:
            The created ParticleEffect dataclass instance.
        """
        _time_module.sleep(0.001)
        if position is None:
            position = (0.0, 0.0, 0.0)

        ambient_emitter = self.create_emitter(
            name="ambient_dust",
            position=position,
            emission_shape="rectangle",
            emission_rate=8.0 * scale,
            max_particles=int(80 * scale),
            particle_lifetime=(3.0, 7.0),
            speed_range=(0.05, 0.3),
            direction=(0.0, 1.0, 0.0),
            spread=6.283,
            gravity=(0.0, 0.03, 0.0),
            blend_mode="alpha",
            burst_count=0,
            looping=True,
            auto_start=True,
            shape_width=area_width,
            shape_height=area_height,
        )

        effect = self.create_effect(
            name=f"ambient_{uuid.uuid4().hex[:8]}",
            emitters=[ambient_emitter],
            duration=0.0,
            looping=True,
            trigger_on="on_spawn",
            position_offset=(0.0, 0.0, 0.0),
            tags=["ambient", "atmosphere", "dust", "environment"],
        )

        self.activate_effect(effect.effect_id, position)
        return effect

    # ------------------------------------------------------------------
    # Statistics and lifecycle
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics about the particle system.

        Returns:
            Dict with emitter counts, particle counts, effect counts,
            and performance metrics.
        """
        _time_module.sleep(0.001)
        active_emitters = sum(1 for e in self._emitters.values() if e.active)
        active_particles = sum(1 for p in self._particles.values() if p.alive)
        active_effects = sum(1 for e in self._effects.values() if e.active)

        shape_distribution: Dict[str, int] = {}
        for emitter in self._emitters.values():
            shape_name = emitter.emission_shape.value
            shape_distribution[shape_name] = shape_distribution.get(shape_name, 0) + 1

        blend_distribution: Dict[str, int] = {}
        for emitter in self._emitters.values():
            blend_name = emitter.blend_mode.value
            blend_distribution[blend_name] = blend_distribution.get(blend_name, 0) + 1

        return {
            "total_emitters": len(self._emitters),
            "active_emitters": active_emitters,
            "total_particles_alive": active_particles,
            "total_particles_spawned": self._total_particles_spawned,
            "total_particles_destroyed": self._total_particles_destroyed,
            "total_effects": len(self._effects),
            "active_effects": active_effects,
            "total_emitters_created": self._total_emitters_created,
            "total_effects_created": self._total_effects_created,
            "total_bursts_fired": self._total_bursts_fired,
            "shape_distribution": shape_distribution,
            "blend_distribution": blend_distribution,
            "max_emitters": self.MAX_EMITTERS,
            "max_particles_global": self.MAX_PARTICLES_GLOBAL,
            "max_effects": self.MAX_EFFECTS,
            "max_particles_per_emitter": self.MAX_PARTICLES_PER_EMITTER,
        }

    def reset(self) -> None:
        """Reset the entire particle system to its initial state.

        Clears all emitters, particles, effects, and counters.
        """
        _time_module.sleep(0.001)
        with self._lock:
            self._emitters.clear()
            self._particles.clear()
            self._effects.clear()
            self._emitter_particles.clear()
            self._total_particles_spawned = 0
            self._total_particles_destroyed = 0
            self._total_emitters_created = 0
            self._total_effects_created = 0
            self._total_bursts_fired = 0


def get_particle_system() -> EngineParticleSystem:
    """Return the global EngineParticleSystem singleton instance."""
    return EngineParticleSystem.get_instance()