"""
SparkLabs Engine - Particle System

Particle emitter engine with configurable emission rates, lifetime
management, and interpolated properties. Designed for visual effects
in AI-generated games — explosions, trails, weather, magic effects.

Architecture:
  ParticleSystem
    |-- ParticleEmitter (emission rate, burst, looping)
    |-- ParticlePool (object pooling for performance)
    |-- PropertyCurve (interpolated lifetime properties)
    |-- RenderBatch (consolidated draw calls)

Particle Properties (per-lifetime curves):
  - position, velocity, acceleration
  - size, color (RGBA), rotation
  - gravity scale, damping

Usage:
    ps = ParticleSystem(max_particles=5000)
    emitter = ps.create_emitter("explosion",
        emission_rate=200, lifetime=1.5, burst=50,
        start_color=(1.0, 0.8, 0.0, 1.0),
        end_color=(1.0, 0.0, 0.0, 0.0),
    )
    ps.emit("explosion", position=(100, 200), direction=(0, -1))
    ps.update(0.016)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EmitterShape(Enum):
    POINT = "point"
    CIRCLE = "circle"
    RECT = "rect"
    CONE = "cone"
    LINE = "line"


class EmitterMode(Enum):
    CONTINUOUS = "continuous"
    BURST = "burst"
    ONE_SHOT = "one_shot"


@dataclass
class ColorRGBA:
    r: float = 1.0
    g: float = 1.0
    b: float = 1.0
    a: float = 1.0

    def lerp(self, other: ColorRGBA, t: float) -> ColorRGBA:
        t = max(0.0, min(1.0, t))
        return ColorRGBA(
            r=self.r + (other.r - self.r) * t,
            g=self.g + (other.g - self.g) * t,
            b=self.b + (other.b - self.b) * t,
            a=self.a + (other.a - self.a) * t,
        )

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.r, self.g, self.b, self.a)


@dataclass
class Particle:
    position: Tuple[float, float] = (0.0, 0.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    acceleration: Tuple[float, float] = (0.0, 0.0)
    lifetime: float = 1.0
    age: float = 0.0
    size: float = 1.0
    start_size: float = 1.0
    end_size: float = 0.0
    color: ColorRGBA = field(default_factory=ColorRGBA)
    start_color: ColorRGBA = field(default_factory=ColorRGBA)
    end_color: ColorRGBA = field(default_factory=ColorRGBA)
    rotation: float = 0.0
    angular_velocity: float = 0.0
    gravity_scale: float = 1.0
    alive: bool = True

    @property
    def progress(self) -> float:
        if self.lifetime <= 0:
            return 1.0
        return min(1.0, self.age / self.lifetime)

    @property
    def current_size(self) -> float:
        return self.start_size + (self.end_size - self.start_size) * self.progress

    @property
    def current_color(self) -> ColorRGBA:
        return self.start_color.lerp(self.end_color, self.progress)


@dataclass
class ParticleEmitter:
    name: str = ""
    shape: EmitterShape = EmitterShape.POINT
    mode: EmitterMode = EmitterMode.CONTINUOUS
    emission_rate: float = 100.0
    lifetime: float = 1.0
    lifetime_variance: float = 0.0
    speed: float = 100.0
    speed_variance: float = 0.0
    start_size: float = 10.0
    end_size: float = 0.0
    start_color: ColorRGBA = field(default_factory=ColorRGBA)
    end_color: ColorRGBA = field(default_factory=lambda: ColorRGBA(a=0.0))
    gravity_scale: float = 1.0
    angle: float = 0.0
    spread: float = math.pi / 4
    burst_count: int = 0
    looping: bool = True
    duration: float = 0.0
    elapsed: float = 0.0
    emission_accumulator: float = 0.0
    active: bool = True
    radius: float = 50.0


class ParticleSystem:
    """
    Particle engine for visual effects in game rendering.

    Creates and manages particle emitters with object pooling
    for efficient simulation. Supports interpolated size/color
    over particle lifetime with configurable emission shapes.

    Usage:
        ps = ParticleSystem(max_particles=5000)
        ps.create_emitter("sparks", emission_rate=300, lifetime=0.8,
                          speed=200, start_color=ColorRGBA(1,1,0,1),
                          end_color=ColorRGBA(1,0,0,0))
        ps.emit("sparks", (100, 100))
        ps.update(0.016)
        for p in ps.get_alive():
            draw_particle(p)
    """

    def __init__(self, max_particles: int = 5000, gravity: Tuple[float, float] = (0.0, -200.0)):
        self._max_particles = max_particles
        self._gravity = gravity
        self._particles: List[Particle] = []
        self._emitters: Dict[str, ParticleEmitter] = {}
        self._update_count: int = 0

    def create_emitter(
        self,
        name: str,
        shape: EmitterShape = EmitterShape.POINT,
        mode: EmitterMode = EmitterMode.CONTINUOUS,
        emission_rate: float = 100.0,
        lifetime: float = 1.0,
        speed: float = 100.0,
        start_size: float = 10.0,
        end_size: float = 0.0,
        start_color: Optional[ColorRGBA] = None,
        end_color: Optional[ColorRGBA] = None,
        spread: float = math.pi / 4,
        **kwargs,
    ) -> ParticleEmitter:
        emitter = ParticleEmitter(
            name=name, shape=shape, mode=mode,
            emission_rate=emission_rate,
            lifetime=lifetime, speed=speed,
            start_size=start_size, end_size=end_size,
            start_color=start_color or ColorRGBA(),
            end_color=end_color or ColorRGBA(a=0.0),
            spread=spread,
            **kwargs,
        )
        self._emitters[name] = emitter
        return emitter

    def get_emitter(self, name: str) -> Optional[ParticleEmitter]:
        return self._emitters.get(name)

    def remove_emitter(self, name: str) -> bool:
        return self._emitters.pop(name, None) is not None

    def emit(
        self,
        emitter_name: str,
        position: Tuple[float, float],
        direction: Tuple[float, float] = (0.0, -1.0),
        count: int = 0,
    ) -> int:
        emitter = self._emitters.get(emitter_name)
        if not emitter or not emitter.active:
            return 0

        to_emit = max(count, emitter.burst_count) if count > 0 or emitter.mode == EmitterMode.BURST else 0
        if to_emit <= 0:
            return 0

        spawned = 0
        for _ in range(to_emit):
            if len(self._particles) >= self._max_particles:
                break
            p = self._create_particle(emitter, position, direction)
            self._particles.append(p)
            spawned += 1
        return spawned

    def update(self, dt: float) -> None:
        self._update_count += 1

        for emitter in self._emitters.values():
            if not emitter.active:
                continue
            emitter.elapsed += dt
            if emitter.duration > 0 and emitter.elapsed >= emitter.duration:
                if emitter.looping:
                    emitter.elapsed = 0.0
                else:
                    emitter.active = False
                    continue

            if emitter.mode == EmitterMode.CONTINUOUS:
                emitter.emission_accumulator += emitter.emission_rate * dt
                while emitter.emission_accumulator >= 1.0:
                    emitter.emission_accumulator -= 1.0
                    if len(self._particles) < self._max_particles:
                        p = self._create_particle(emitter, (0, 0), (0, -1))
                        self._particles.append(p)

        alive: List[Particle] = []
        for p in self._particles:
            p.age += dt
            if p.age >= p.lifetime:
                p.alive = False
                continue

            gx = self._gravity[0] * p.gravity_scale
            gy = self._gravity[1] * p.gravity_scale

            ax = p.acceleration[0] + gx
            ay = p.acceleration[1] + gy

            vx = p.velocity[0] + ax * dt
            vy = p.velocity[1] + ay * dt
            px = p.position[0] + vx * dt
            py = p.position[1] + vy * dt

            p.velocity = (vx, vy)
            p.position = (px, py)
            p.rotation += p.angular_velocity * dt

            alive.append(p)

        self._particles = alive

    def get_alive(self) -> List[Particle]:
        return self._particles

    def get_count(self) -> int:
        return len(self._particles)

    def get_stats(self) -> dict:
        return {
            "particles": len(self._particles),
            "max_particles": self._max_particles,
            "emitters": len(self._emitters),
            "active_emitters": sum(1 for e in self._emitters.values() if e.active),
            "updates": self._update_count,
        }

    def clear(self) -> None:
        self._particles.clear()
        for e in self._emitters.values():
            e.active = True
            e.elapsed = 0.0
            e.emission_accumulator = 0.0

    def _create_particle(
        self, emitter: ParticleEmitter,
        position: Tuple[float, float],
        direction: Tuple[float, float],
    ) -> Particle:
        spawn_pos = position
        if emitter.shape == EmitterShape.CIRCLE:
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, emitter.radius)
            spawn_pos = (
                position[0] + math.cos(angle) * r,
                position[1] + math.sin(angle) * r,
            )

        base_angle = math.atan2(direction[1], direction[0])
        spread_angle = base_angle + random.uniform(-emitter.spread / 2, emitter.spread / 2)
        spd = emitter.speed + random.uniform(-emitter.speed_variance, emitter.speed_variance)
        spd = max(spd, 0.0)

        vx = math.cos(spread_angle) * spd
        vy = math.sin(spread_angle) * spd

        lt = emitter.lifetime + random.uniform(
            -emitter.lifetime_variance, emitter.lifetime_variance,
        )
        lt = max(lt, 0.01)

        return Particle(
            position=spawn_pos,
            velocity=(vx, vy),
            lifetime=lt,
            start_size=emitter.start_size,
            end_size=emitter.end_size,
            start_color=ColorRGBA(
                r=emitter.start_color.r, g=emitter.start_color.g,
                b=emitter.start_color.b, a=emitter.start_color.a,
            ),
            end_color=ColorRGBA(
                r=emitter.end_color.r, g=emitter.end_color.g,
                b=emitter.end_color.b, a=emitter.end_color.a,
            ),
            rotation=random.uniform(0, 2 * math.pi),
            angular_velocity=random.uniform(-math.pi, math.pi),
            gravity_scale=emitter.gravity_scale,
        )


_global_particle_system: Optional[ParticleSystem] = None


def get_particle_system() -> ParticleSystem:
    global _global_particle_system
    if _global_particle_system is None:
        _global_particle_system = ParticleSystem()
    return _global_particle_system
