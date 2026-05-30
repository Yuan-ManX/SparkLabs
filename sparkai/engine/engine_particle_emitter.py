"""
SparkLabs Engine - Particle Emitter

A singleton GPU-optimized particle system for the SparkLabs game
engine. Provides billboarded sprite particles with configurable
emitters, force fields, and a library of preset visual effects.
Uses object pooling for minimal allocation overhead.

Architecture:
  ParticleEmitter (singleton)
    |-- Particle (individual particle state: position, velocity, life)
    |-- EmitterConfig (spawn rate, shape, color gradients, lifetime)
    |-- ParticlePool (pre-allocated particle buffer with recycling)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class EmitterShape(Enum):
    POINT = "point"
    SPHERE = "sphere"
    CONE = "cone"
    BOX = "box"
    CIRCLE = "circle"
    LINE = "line"
    MESH_SURFACE = "mesh_surface"


class BlendMode(Enum):
    ALPHA = "alpha"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"


class ForceType(Enum):
    GRAVITY = "gravity"
    WIND = "wind"
    VORTEX = "vortex"
    ATTRACTION = "attraction"
    TURBULENCE = "turbulence"
    DRAG = "drag"


class PresetEffect(Enum):
    FIRE = "fire"
    SMOKE = "smoke"
    MAGIC_SPARKLE = "magic_sparkle"
    EXPLOSION = "explosion"
    RAIN = "rain"
    SNOW = "snow"
    LEAVES = "leaves"
    DUST = "dust"
    BUBBLES = "bubbles"
    ELECTRIC = "electric"
    HEALING = "healing"
    POISON = "poison"
    TRAIL = "trail"
    CONFETTI = "confetti"
    FOG = "fog"
    STARFIELD = "starfield"
    LAVA = "lava"
    WATERFALL = "waterfall"
    LASER_GLOW = "laser_glow"
    IMPACT_SPARKS = "impact_sparks"


PARTICLE_POOL_DEFAULT_SIZE: int = 10000
PARTICLE_LIFETIME_EPSILON: float = 0.001


@dataclass
class Particle:
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    color: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])
    size: float = 1.0
    lifetime: float = 1.0
    age: float = 0.0
    rotation: float = 0.0
    angular_velocity: float = 0.0
    alive: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": list(self.position),
            "velocity": list(self.velocity),
            "color": list(self.color),
            "size": self.size,
            "lifetime": self.lifetime,
            "age": self.age,
            "rotation": self.rotation,
            "alive": self.alive,
        }


@dataclass
class EmitterConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    shape: EmitterShape = EmitterShape.POINT
    emission_rate: float = 50.0
    max_particles: int = 500
    lifetime_min: float = 1.0
    lifetime_max: float = 3.0
    speed_min: float = 1.0
    speed_max: float = 3.0
    size_start: float = 1.0
    size_end: float = 0.0
    color_start: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])
    color_end: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 0.0])
    blend_mode: BlendMode = BlendMode.ALPHA
    gravity_multiplier: float = 0.0
    spawn_radius: float = 0.0
    cone_angle: float = 0.0
    looping: bool = True
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "shape": self.shape.value,
            "emission_rate": self.emission_rate,
            "max_particles": self.max_particles,
            "lifetime_min": self.lifetime_min,
            "lifetime_max": self.lifetime_max,
            "speed_min": self.speed_min,
            "speed_max": self.speed_max,
            "size_start": self.size_start,
            "size_end": self.size_end,
            "color_start": list(self.color_start),
            "color_end": list(self.color_end),
            "blend_mode": self.blend_mode.value,
            "gravity_multiplier": self.gravity_multiplier,
            "looping": self.looping,
        }


@dataclass
class ForceField:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    force_type: ForceType = ForceType.GRAVITY
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    direction: List[float] = field(default_factory=lambda: [0.0, -1.0, 0.0])
    strength: float = 9.8
    radius: float = 100.0
    falloff: float = 2.0
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "force_type": self.force_type.value,
            "position": list(self.position),
            "direction": list(self.direction),
            "strength": self.strength,
            "radius": self.radius,
            "falloff": self.falloff,
            "active": self.active,
        }


@dataclass
class ActiveEmitter:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config: EmitterConfig = field(default_factory=EmitterConfig)
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    particles: List[Particle] = field(default_factory=list)
    elapsed: float = 0.0
    age: float = 0.0
    active: bool = True
    insert_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "config_name": self.config.name,
            "position": list(self.position),
            "active_particles": sum(1 for p in self.particles if p.alive),
            "total_particles": len(self.particles),
            "elapsed": self.elapsed,
            "active": self.active,
        }


class ParticleEmitter:
    """GPU-optimized particle system with preset effects and object pooling.

    Manages particle simulation including spawn, lifetime tracking,
    force field application, and size/color interpolation. Uses
    pre-allocated particle pools to minimize runtime allocation.
    """

    _instance: Optional[ParticleEmitter] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> ParticleEmitter:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> ParticleEmitter:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._active_emitters: List[ActiveEmitter] = []
        self._force_fields: List[ForceField] = []
        self._configs: List[EmitterConfig] = []
        self._particle_pool: List[Particle] = []
        self._pool_index: int = 0
        self._initialize_pool(PARTICLE_POOL_DEFAULT_SIZE)
        self._initialize_presets()

    def _get_or_create_singleton(self) -> ParticleEmitter:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        total_alive = sum(
            sum(1 for p in ae.particles if p.alive) for ae in self._active_emitters
        )
        return {
            "active_emitters": len(self._active_emitters),
            "total_configs": len(self._configs),
            "force_fields": len(self._force_fields),
            "alive_particles": total_alive,
            "pool_size": len(self._particle_pool),
            "pool_available": sum(1 for p in self._particle_pool if not p.alive),
        }

    # --- Config Operations ---

    def create_config(
        self,
        name: str,
        emission_rate: float = 50.0,
        max_particles: int = 500,
        lifetime_min: float = 1.0,
        lifetime_max: float = 3.0,
        speed_min: float = 1.0,
        speed_max: float = 3.0,
        shape: str = "point",
    ) -> EmitterConfig:
        config = EmitterConfig(
            name=name,
            emission_rate=emission_rate,
            max_particles=max_particles,
            lifetime_min=lifetime_min,
            lifetime_max=lifetime_max,
            speed_min=speed_min,
            speed_max=speed_max,
            shape=EmitterShape(shape),
        )
        self._configs.append(config)
        return config

    def get_preset(self, effect: str) -> EmitterConfig:
        preset = PresetEffect(effect)
        return self._generate_preset_config(preset)

    def list_configs(self) -> List[EmitterConfig]:
        return list(self._configs)

    # --- Emitter Operations ---

    def spawn_emitter(
        self,
        config_id: str,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> Optional[ActiveEmitter]:
        config = None
        for c in self._configs:
            if c.id == config_id:
                config = c
                break
        if not config:
            return None

        emitter = ActiveEmitter(
            config=config,
            position=list(position),
        )

        for _ in range(min(config.max_particles, config.max_particles // 4)):
            particle = self._acquire_particle()
            if particle:
                emitter.particles.append(particle)

        self._active_emitters.append(emitter)
        return emitter

    def spawn_preset(
        self,
        effect: str,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> ActiveEmitter:
        config = self._generate_preset_config(PresetEffect(effect))
        emitter = ActiveEmitter(
            config=config,
            position=list(position),
        )

        for _ in range(min(config.max_particles, config.max_particles // 4)):
            particle = self._acquire_particle()
            if particle:
                emitter.particles.append(particle)

        self._active_emitters.append(emitter)
        return emitter

    def kill_emitter(self, emitter_id: str) -> bool:
        for ae in self._active_emitters:
            if ae.id == emitter_id:
                for p in ae.particles:
                    p.alive = False
                ae.active = False
                return True
        return False

    def list_active_emitters(self) -> List[ActiveEmitter]:
        return [ae for ae in self._active_emitters if ae.active]

    # --- Simulation ---

    def simulate(self, delta_time: float) -> Dict[str, Any]:
        total_born = 0
        total_died = 0

        for ae in self._active_emitters:
            if not ae.active:
                continue

            ae.age += delta_time
            ae.elapsed += delta_time

            if ae.config.looping or ae.age <= ae.config.duration:
                spawn_count = int(ae.config.emission_rate * delta_time)
                total_born += spawn_count

                for _ in range(spawn_count):
                    particle = self._acquire_particle()
                    if particle is None:
                        continue

                    particle.alive = True
                    particle.age = 0.0
                    particle.lifetime = random.uniform(
                        ae.config.lifetime_min, ae.config.lifetime_max
                    )
                    particle.size = ae.config.size_start
                    particle.position = list(ae.position)
                    particle.color = list(ae.config.color_start)

                    spawn_offset = self._compute_spawn_offset(ae.config)
                    particle.position[0] += spawn_offset[0]
                    particle.position[1] += spawn_offset[1]
                    particle.position[2] += spawn_offset[2]

                    speed = random.uniform(ae.config.speed_min, ae.config.speed_max)
                    direction = self._compute_velocity_direction(ae.config)
                    particle.velocity = [d * speed for d in direction]

                    ae.particles.append(particle)

            for particle in ae.particles:
                if not particle.alive:
                    continue

                particle.age += delta_time
                if particle.age >= particle.lifetime - PARTICLE_LIFETIME_EPSILON:
                    particle.alive = False
                    total_died += 1
                    continue

                t = particle.age / max(particle.lifetime, PARTICLE_LIFETIME_EPSILON)
                particle.size = ae.config.size_start + (ae.config.size_end - ae.config.size_start) * t

                for i in range(4):
                    particle.color[i] = ae.config.color_start[i] + (ae.config.color_end[i] - ae.config.color_start[i]) * t

                for force in self._force_fields:
                    if not force.active:
                        continue
                    self._apply_force(particle, force)

                particle.velocity[1] -= ae.config.gravity_multiplier * delta_time
                for i in range(3):
                    particle.position[i] += particle.velocity[i] * delta_time

                particle.rotation += particle.angular_velocity * delta_time

        self._active_emitters = [ae for ae in self._active_emitters if ae.active]

        return {
            "emitters_alive": len([ae for ae in self._active_emitters if ae.active]),
            "particles_born": total_born,
            "particles_died": total_died,
            "total_active": sum(
                sum(1 for p in ae.particles if p.alive) for ae in self._active_emitters
            ),
        }

    # --- Force Fields ---

    def add_force_field(
        self,
        force_type: str = "gravity",
        strength: float = 9.8,
        direction: Tuple[float, float, float] = (0.0, -1.0, 0.0),
        radius: float = 100.0,
    ) -> ForceField:
        force = ForceField(
            force_type=ForceType(force_type),
            direction=list(direction),
            strength=strength,
            radius=radius,
        )
        self._force_fields.append(force)
        return force

    def list_force_fields(self) -> List[ForceField]:
        return list(self._force_fields)

    def remove_force_field(self, field_id: str) -> bool:
        for i, f in enumerate(self._force_fields):
            if f.id == field_id:
                self._force_fields.pop(i)
                return True
        return False

    # --- Pool Operations ---

    def reset(self) -> None:
        self._active_emitters.clear()
        self._force_fields.clear()
        for p in self._particle_pool:
            p.alive = False
        self._pool_index = 0

    # --- Internal ---

    def _initialize_pool(self, size: int) -> None:
        self._particle_pool = [Particle() for _ in range(size)]
        self._pool_index = 0

    def _acquire_particle(self) -> Optional[Particle]:
        for _ in range(len(self._particle_pool)):
            p = self._particle_pool[self._pool_index]
            self._pool_index = (self._pool_index + 1) % len(self._particle_pool)
            if not p.alive:
                return p
        return None

    def _compute_spawn_offset(self, config: EmitterConfig) -> Tuple[float, float, float]:
        shape = config.shape
        radius = config.spawn_radius
        if shape == EmitterShape.POINT:
            return (0.0, 0.0, 0.0)
        elif shape == EmitterShape.SPHERE:
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(0, math.pi)
            r = radius * random.random()
            return (
                r * math.sin(phi) * math.cos(theta),
                r * math.sin(phi) * math.sin(theta),
                r * math.cos(phi),
            )
        elif shape == EmitterShape.CIRCLE:
            angle = random.uniform(0, 2 * math.pi)
            r = radius * random.random()
            return (r * math.cos(angle), 0.0, r * math.sin(angle))
        elif shape == EmitterShape.BOX:
            return (
                random.uniform(-radius, radius),
                random.uniform(-radius, radius),
                random.uniform(-radius, radius),
            )
        elif shape == EmitterShape.CONE:
            angle = random.uniform(0, 2 * math.pi)
            spread = math.tan(config.cone_angle) * radius
            r = random.uniform(0, spread)
            return (
                r * math.cos(angle),
                radius,
                r * math.sin(angle),
            )
        return (0.0, 0.0, 0.0)

    def _compute_velocity_direction(self, config: EmitterConfig) -> Tuple[float, float, float]:
        if config.shape == EmitterShape.CONE:
            base_dir = (0.0, 1.0, 0.0)
            angle = random.uniform(0, 2 * math.pi)
            spread = random.uniform(0, config.cone_angle)
            return (
                base_dir[0] + spread * math.cos(angle),
                base_dir[1],
                base_dir[2] + spread * math.sin(angle),
            )
        theta = random.uniform(0, 2 * math.pi)
        phi = random.uniform(-math.pi / 2, math.pi / 2)
        return (
            math.cos(phi) * math.cos(theta),
            math.sin(phi),
            math.cos(phi) * math.sin(theta),
        )

    def _apply_force(self, particle: Particle, force: ForceField) -> None:
        dx = particle.position[0] - force.position[0]
        dy = particle.position[1] - force.position[1]
        dz = particle.position[2] - force.position[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        if dist > force.radius or dist < 0.001:
            return

        falloff_weight = max(0.0, 1.0 - (dist / force.radius))
        strength = force.strength * (falloff_weight ** force.falloff)

        if force.force_type == ForceType.GRAVITY:
            particle.velocity[1] -= strength * 0.016
        elif force.force_type == ForceType.WIND:
            for i in range(3):
                particle.velocity[i] += force.direction[i] * strength * 0.016
        elif force.force_type == ForceType.DRAG:
            for i in range(3):
                particle.velocity[i] *= max(0.0, 1.0 - strength * 0.016)

    def _initialize_presets(self) -> None:
        pass

    def _generate_preset_config(self, effect: PresetEffect) -> EmitterConfig:
        presets = {
            PresetEffect.FIRE: {
                "emission_rate": 80, "max_particles": 400, "lifetime_min": 0.5,
                "lifetime_max": 1.5, "speed_min": 0.5, "speed_max": 2.0,
                "size_start": 1.0, "size_end": 0.1,
                "color_start": [1.0, 0.6, 0.1, 1.0],
                "color_end": [1.0, 0.1, 0.0, 0.0],
                "blend_mode": "additive", "gravity_multiplier": -1.0,
                "shape": "cone", "cone_angle": 0.3,
            },
            PresetEffect.SMOKE: {
                "emission_rate": 20, "max_particles": 200, "lifetime_min": 2.0,
                "lifetime_max": 5.0, "speed_min": 0.3, "speed_max": 1.0,
                "size_start": 1.0, "size_end": 3.0,
                "color_start": [0.5, 0.5, 0.5, 0.6],
                "color_end": [0.3, 0.3, 0.3, 0.0],
                "blend_mode": "alpha", "gravity_multiplier": -0.5,
                "shape": "circle", "spawn_radius": 1.0,
            },
            PresetEffect.MAGIC_SPARKLE: {
                "emission_rate": 40, "max_particles": 300, "lifetime_min": 0.3,
                "lifetime_max": 1.0, "speed_min": 1.0, "speed_max": 3.0,
                "size_start": 0.3, "size_end": 0.0,
                "color_start": [0.8, 0.4, 1.0, 1.0],
                "color_end": [0.2, 0.0, 0.8, 0.0],
                "blend_mode": "additive", "gravity_multiplier": 0.0,
                "shape": "sphere", "spawn_radius": 2.0,
            },
            PresetEffect.EXPLOSION: {
                "emission_rate": 300, "max_particles": 800, "lifetime_min": 0.3,
                "lifetime_max": 1.5, "speed_min": 2.0, "speed_max": 8.0,
                "size_start": 0.5, "size_end": 0.05,
                "color_start": [1.0, 0.8, 0.2, 1.0],
                "color_end": [0.5, 0.2, 0.0, 0.0],
                "blend_mode": "additive", "gravity_multiplier": 0.5,
                "shape": "sphere", "spawn_radius": 0.5, "looping": False, "duration": 0.5,
            },
            PresetEffect.RAIN: {
                "emission_rate": 100, "max_particles": 1000, "lifetime_min": 1.0,
                "lifetime_max": 2.0, "speed_min": 5.0, "speed_max": 8.0,
                "size_start": 0.1, "size_end": 0.05,
                "color_start": [0.6, 0.7, 1.0, 0.5],
                "color_end": [0.4, 0.5, 0.8, 0.0],
                "blend_mode": "alpha", "gravity_multiplier": 0.0,
                "shape": "box", "spawn_radius": 20.0,
            },
        }

        preset = presets.get(effect, presets[PresetEffect.FIRE])
        config = EmitterConfig(
            name=f"preset_{effect.value}",
            emission_rate=preset.get("emission_rate", 50),
            max_particles=preset.get("max_particles", 500),
            lifetime_min=preset.get("lifetime_min", 1.0),
            lifetime_max=preset.get("lifetime_max", 3.0),
            speed_min=preset.get("speed_min", 1.0),
            speed_max=preset.get("speed_max", 3.0),
            size_start=preset.get("size_start", 1.0),
            size_end=preset.get("size_end", 0.0),
            color_start=preset.get("color_start", [1.0, 1.0, 1.0, 1.0]),
            color_end=preset.get("color_end", [1.0, 1.0, 1.0, 0.0]),
            blend_mode=BlendMode(preset.get("blend_mode", "alpha")),
            gravity_multiplier=preset.get("gravity_multiplier", 0.0),
            shape=EmitterShape(preset.get("shape", "point")),
            spawn_radius=preset.get("spawn_radius", 0.0),
            cone_angle=preset.get("cone_angle", 0.0),
            looping=preset.get("looping", True),
            duration=preset.get("duration", 0.0),
        )
        return config


def get_particle_emitter() -> ParticleEmitter:
    return ParticleEmitter.get_instance()