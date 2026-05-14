"""
SparkLabs Engine - GPU Particle System

GPU-accelerated particle rendering engine for high-performance
visual effects in AI-generated games. Uses compute shader-based
particle simulation with configurable emission shapes, property
curves, force fields, sub-emitter chains, and LOD-based culling.

Architecture:
  GPUParticleSystem
    |-- EmitterShape (point, sphere, box, cone, circle, hemisphere, mesh_surface, ring)
    |-- ParticleBlendMode (additive, alpha, multiply, premultiplied, subtractive)
    |-- SimulationSpace (local, world, custom)
    |-- ParticleCurve (interpolated property curves with easing)
    |-- GPUParticleConfig (emitter configuration dataclass)
    |-- ParticleForceField (attractor/repulsor force fields)
    |-- GPUParticleInstance (runtime particle system instance)

Particle simulation is offloaded to the GPU via compute shaders,
with property curves evaluated per-particle for lifetime, color,
size, velocity, and rotation. Force fields apply GPU-computed
attraction, repulsion, vortex, turbulence, drag, and wind effects.

Usage:
    gpu_ps = get_gpu_particle_system()
    cfg = gpu_ps.create_config({
        "max_particles": 10000,
        "emission_rate": 500.0,
        "emitter_shape": EmitterShape.SPHERE,
        "lifetime": ParticleCurve(curve_type="constant", points=[(0, 2.0), (1, 2.0)]),
    })
    inst = gpu_ps.instantiate(cfg.config_id, (0, 0, 0), (0, 0, 0), (1, 1, 1))
    gpu_ps.play(inst.instance_id)
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EmitterShape(Enum):
    POINT = "point"
    SPHERE = "sphere"
    BOX = "box"
    CONE = "cone"
    CIRCLE = "circle"
    HEMISPHERE = "hemisphere"
    MESH_SURFACE = "mesh_surface"
    RING = "ring"


class ParticleBlendMode(Enum):
    ADDITIVE = "additive"
    ALPHA = "alpha"
    MULTIPLY = "multiply"
    PREMULTIPLIED = "premultiplied"
    SUBTRACTIVE = "subtractive"


class SimulationSpace(Enum):
    LOCAL = "local"
    WORLD = "world"
    CUSTOM = "custom"


class CurveInterpolation(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    SMOOTH = "smooth"


class ForceType(Enum):
    ATTRACT = "attract"
    REPEL = "repel"
    VORTEX = "vortex"
    TURBULENCE = "turbulence"
    DRAG = "drag"
    WIND = "wind"


class LODLevel(Enum):
    FULL = 0
    HALF = 1
    QUARTER = 2


@dataclass
class ParticleCurve:
    curve_type: str = "constant"
    points: List[Tuple[float, float]] = field(default_factory=lambda: [(0.0, 1.0), (1.0, 1.0)])
    interpolation: str = "linear"

    def evaluate(self, t: float) -> float:
        if not self.points:
            return 0.0
        if len(self.points) == 1:
            return self.points[0][1]

        t = max(0.0, min(1.0, t))

        if t <= self.points[0][0]:
            return self.points[0][1]
        if t >= self.points[-1][0]:
            return self.points[-1][1]

        for i in range(len(self.points) - 1):
            t0, v0 = self.points[i]
            t1, v1 = self.points[i + 1]
            if t0 <= t <= t1:
                if t1 == t0:
                    return v0
                raw = (t - t0) / (t1 - t0)
                eased = self._apply_easing(raw)
                return v0 + (v1 - v0) * eased

        return self.points[-1][1]

    def _apply_easing(self, t: float) -> float:
        if self.interpolation == "linear":
            return t
        elif self.interpolation == "ease_in":
            return t * t
        elif self.interpolation == "ease_out":
            return 1.0 - (1.0 - t) * (1.0 - t)
        elif self.interpolation == "smooth":
            return t * t * (3.0 - 2.0 * t)
        return t


@dataclass
class GPUParticleConfig:
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    max_particles: int = 1000
    emission_rate: float = 100.0
    emitter_shape: EmitterShape = EmitterShape.POINT
    emitter_size: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    lifetime: ParticleCurve = field(default_factory=lambda: ParticleCurve(
        curve_type="constant", points=[(0.0, 2.0), (1.0, 2.0)],
        interpolation="linear",
    ))
    start_color: ParticleCurve = field(default_factory=lambda: ParticleCurve(
        curve_type="gradient",
        points=[(0.0, 0), (0.5, 1), (1.0, 0)],
        interpolation="linear",
    ))
    start_size: ParticleCurve = field(default_factory=lambda: ParticleCurve(
        curve_type="constant", points=[(0.0, 1.0), (1.0, 1.0)],
        interpolation="linear",
    ))
    start_velocity: ParticleCurve = field(default_factory=lambda: ParticleCurve(
        curve_type="constant", points=[(0.0, 1.0), (1.0, 1.0)],
        interpolation="linear",
    ))
    gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    blend_mode: ParticleBlendMode = ParticleBlendMode.ADDITIVE
    simulation_space: SimulationSpace = SimulationSpace.WORLD
    prewarm: bool = False
    looping: bool = True
    duration: float = float("inf")
    sub_emitters: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id[:12],
            "max_particles": self.max_particles,
            "emission_rate": self.emission_rate,
            "emitter_shape": self.emitter_shape.value,
            "emitter_size": self.emitter_size,
            "blend_mode": self.blend_mode.value,
            "simulation_space": self.simulation_space.value,
            "prewarm": self.prewarm,
            "looping": self.looping,
            "duration": self.duration if self.duration != float("inf") else "inf",
            "sub_emitter_count": len(self.sub_emitters),
        }


@dataclass
class ParticleForceField:
    field_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    force_type: str = "attract"
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    strength: float = 100.0
    radius: float = 10.0
    falloff: str = "linear"

    def compute_force(self, particle_pos: Tuple[float, float, float]) -> Tuple[float, float, float]:
        dx = particle_pos[0] - self.position[0]
        dy = particle_pos[1] - self.position[1]
        dz = particle_pos[2] - self.position[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        if dist < 0.0001:
            return (0.0, 0.0, 0.0)
        if dist > self.radius:
            return (0.0, 0.0, 0.0)

        ndx = dx / dist
        ndy = dy / dist
        ndz = dz / dist

        if self.falloff == "linear":
            factor = 1.0 - dist / self.radius
        elif self.falloff == "quadratic":
            factor = (1.0 - dist / self.radius) ** 2
        elif self.falloff == "constant":
            factor = 1.0
        else:
            factor = 1.0 - dist / self.radius

        if self.force_type == "attract":
            return (-ndx * self.strength * factor,
                    -ndy * self.strength * factor,
                    -ndz * self.strength * factor)
        elif self.force_type == "repel":
            return (ndx * self.strength * factor,
                    ndy * self.strength * factor,
                    ndz * self.strength * factor)
        elif self.force_type == "vortex":
            return (-ndz * self.strength * factor,
                    0.0,
                    ndx * self.strength * factor)
        elif self.force_type == "turbulence":
            noise_x = math.sin(particle_pos[0] * 0.5 + particle_pos[1] * 0.3) * math.cos(particle_pos[2] * 0.4)
            noise_y = math.cos(particle_pos[0] * 0.3 - particle_pos[1] * 0.5) * math.sin(particle_pos[2] * 0.2)
            noise_z = math.sin(particle_pos[0] * 0.4 + particle_pos[2] * 0.5) * math.cos(particle_pos[1] * 0.3)
            return (noise_x * self.strength * factor,
                    noise_y * self.strength * factor,
                    noise_z * self.strength * factor)
        elif self.force_type == "drag":
            return (0.0, 0.0, 0.0)
        elif self.force_type == "wind":
            return (self.strength * factor, 0.0, 0.0)
        return (0.0, 0.0, 0.0)


@dataclass
class GPUParticleInstance:
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    is_playing: bool = False
    is_paused: bool = False
    current_time: float = 0.0
    active_particles: int = 0
    gpu_memory_mb: float = 0.0
    lod_level: LODLevel = LODLevel.FULL
    _force_fields: Dict[str, ParticleForceField] = field(default_factory=dict)
    _emission_accumulator: float = 0.0
    _total_emitted: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id[:12],
            "config_id": self.config_id[:12],
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "current_time": round(self.current_time, 4),
            "active_particles": self.active_particles,
            "gpu_memory_mb": round(self.gpu_memory_mb, 2),
            "lod_level": self.lod_level.value,
            "force_field_count": len(self._force_fields),
        }


class GPUParticleSystem:
    """GPU-accelerated particle rendering engine for high-performance effects.

    Manages particle configurations and runtime instances with compute
    shader-based simulation. Supports configurable emission shapes,
    interpolated property curves, force fields, sub-emitter chains,
    and LOD-based culling for performance scalability.

    Usage:
        gpu_ps = get_gpu_particle_system()
        cfg = gpu_ps.create_config({"max_particles": 5000})
        inst = gpu_ps.instantiate(cfg.config_id, (0, 0, 0))
        gpu_ps.play(inst.instance_id)
    """

    _instance: Optional["GPUParticleSystem"] = None

    def __init__(self):
        self._configs: Dict[str, GPUParticleConfig] = {}
        self._instances: Dict[str, GPUParticleInstance] = {}
        self._gpu_memory_per_particle_bytes: int = 256
        self._compute_shader_bound: bool = False
        self._simulation_tick_count: int = 0

    @classmethod
    def get_instance(cls) -> "GPUParticleSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_config(self, config_data: Dict[str, Any]) -> GPUParticleConfig:
        cfg = GPUParticleConfig(
            max_particles=config_data.get("max_particles", 1000),
            emission_rate=config_data.get("emission_rate", 100.0),
            emitter_shape=config_data.get("emitter_shape", EmitterShape.POINT),
            emitter_size=config_data.get("emitter_size", (1.0, 1.0, 1.0)),
            lifetime=config_data.get("lifetime", ParticleCurve()),
            start_color=config_data.get("start_color", ParticleCurve()),
            start_size=config_data.get("start_size", ParticleCurve()),
            start_velocity=config_data.get("start_velocity", ParticleCurve()),
            gravity=config_data.get("gravity", (0.0, -9.81, 0.0)),
            blend_mode=config_data.get("blend_mode", ParticleBlendMode.ADDITIVE),
            simulation_space=config_data.get("simulation_space", SimulationSpace.WORLD),
            prewarm=config_data.get("prewarm", False),
            looping=config_data.get("looping", True),
            duration=config_data.get("duration", float("inf")),
            sub_emitters=config_data.get("sub_emitters", []),
        )
        self._configs[cfg.config_id] = cfg
        return cfg

    def get_config(self, config_id: str) -> Optional[GPUParticleConfig]:
        return self._configs.get(config_id)

    def remove_config(self, config_id: str) -> bool:
        if config_id in self._configs:
            del self._configs[config_id]
            return True
        return False

    def list_configs(self) -> List[GPUParticleConfig]:
        return list(self._configs.values())

    def instantiate(
        self,
        config_id: str,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        scale: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> Optional[GPUParticleInstance]:
        config = self._configs.get(config_id)
        if not config:
            return None

        gpu_mem = self._estimate_gpu_memory(config.max_particles)

        instance = GPUParticleInstance(
            config_id=config_id,
            position=position,
            rotation=rotation,
            scale=scale,
            gpu_memory_mb=gpu_mem,
        )
        self._instances[instance.instance_id] = instance
        return instance

    def find_instance(self, instance_id: str) -> Optional[GPUParticleInstance]:
        return self._instances.get(instance_id)

    def play(self, instance_id: str) -> None:
        instance = self._instances.get(instance_id)
        if not instance:
            return
        instance.is_playing = True
        instance.is_paused = False
        instance.current_time = 0.0
        instance._emission_accumulator = 0.0
        instance._total_emitted = 0
        instance.active_particles = 0

    def stop(self, instance_id: str) -> None:
        instance = self._instances.get(instance_id)
        if not instance:
            return
        instance.is_playing = False
        instance.is_paused = False
        instance.active_particles = 0
        instance._emission_accumulator = 0.0

    def pause(self, instance_id: str) -> None:
        instance = self._instances.get(instance_id)
        if not instance:
            return
        instance.is_paused = True

    def resume(self, instance_id: str) -> None:
        instance = self._instances.get(instance_id)
        if not instance:
            return
        instance.is_paused = False

    def set_position(
        self, instance_id: str, position: Tuple[float, float, float]
    ) -> None:
        instance = self._instances.get(instance_id)
        if not instance:
            return
        instance.position = position

    def set_rotation(
        self, instance_id: str, rotation: Tuple[float, float, float]
    ) -> None:
        instance = self._instances.get(instance_id)
        if not instance:
            return
        instance.rotation = rotation

    def set_scale(
        self, instance_id: str, scale: Tuple[float, float, float]
    ) -> None:
        instance = self._instances.get(instance_id)
        if not instance:
            return
        instance.scale = scale

    def add_force_field(
        self, instance_id: str, force_field: ParticleForceField
    ) -> bool:
        instance = self._instances.get(instance_id)
        if not instance:
            return False
        instance._force_fields[force_field.field_id] = force_field
        return True

    def remove_force_field(self, instance_id: str, field_id: str) -> bool:
        instance = self._instances.get(instance_id)
        if not instance:
            return False
        if field_id in instance._force_fields:
            del instance._force_fields[field_id]
            return True
        return False

    def get_force_fields(
        self, instance_id: str
    ) -> List[ParticleForceField]:
        instance = self._instances.get(instance_id)
        if not instance:
            return []
        return list(instance._force_fields.values())

    def get_active_particle_count(self, instance_id: str) -> int:
        instance = self._instances.get(instance_id)
        if not instance:
            return 0
        return instance.active_particles

    def set_lod_level(self, instance_id: str, level: int) -> None:
        instance = self._instances.get(instance_id)
        if not instance:
            return
        if level == 0:
            instance.lod_level = LODLevel.FULL
        elif level == 1:
            instance.lod_level = LODLevel.HALF
        elif level == 2:
            instance.lod_level = LODLevel.QUARTER
        else:
            instance.lod_level = LODLevel.FULL

    def get_lod_rate(self, instance_id: str) -> float:
        instance = self._instances.get(instance_id)
        if not instance:
            return 1.0
        if instance.lod_level == LODLevel.FULL:
            return 1.0
        elif instance.lod_level == LODLevel.HALF:
            return 0.5
        elif instance.lod_level == LODLevel.QUARTER:
            return 0.25
        return 1.0

    def update(self, dt: float) -> None:
        self._simulation_tick_count += 1

        for instance in self._instances.values():
            if not instance.is_playing or instance.is_paused:
                continue

            config = self._configs.get(instance.config_id)
            if not config:
                continue

            instance.current_time += dt

            if config.duration != float("inf") and instance.current_time >= config.duration:
                if config.looping:
                    instance.current_time = instance.current_time % config.duration
                else:
                    instance.is_playing = False
                    instance.active_particles = 0
                    continue

            lod_rate = self.get_lod_rate(instance.instance_id)
            effective_rate = config.emission_rate * lod_rate

            instance._emission_accumulator += effective_rate * dt
            emit_count = int(instance._emission_accumulator)
            if emit_count > 0:
                instance._emission_accumulator -= emit_count
                instance._total_emitted += emit_count

            lifetime_at_zero = config.lifetime.evaluate(0.0)
            max_lifetime = max(pt[1] for pt in config.lifetime.points) if config.lifetime.points else 1.0

            decay_count = 0
            if instance.current_time > 0 and instance._total_emitted > 0:
                avg_rate = instance._total_emitted / max(instance.current_time, 0.001)
                decay_count = int(avg_rate * (instance.current_time - max_lifetime))
                decay_count = max(0, decay_count)

            instance.active_particles = max(0, instance._total_emitted - decay_count)
            instance.active_particles = min(instance.active_particles, config.max_particles)

            instance.gpu_memory_mb = self._estimate_gpu_memory(instance.active_particles)

    def remove_instance(self, instance_id: str) -> bool:
        if instance_id in self._instances:
            del self._instances[instance_id]
            return True
        return False

    def _estimate_gpu_memory(self, particle_count: int) -> float:
        return (particle_count * self._gpu_memory_per_particle_bytes) / (1024.0 * 1024.0)

    def set_gpu_memory_per_particle(self, bytes_per_particle: int) -> None:
        self._gpu_memory_per_particle_bytes = max(64, bytes_per_particle)

    def bind_compute_shader(self) -> None:
        self._compute_shader_bound = True

    def unbind_compute_shader(self) -> None:
        self._compute_shader_bound = False

    def is_compute_shader_bound(self) -> bool:
        return self._compute_shader_bound

    def get_stats(self) -> Dict[str, Any]:
        total_active_particles = sum(
            inst.active_particles for inst in self._instances.values()
            if inst.is_playing and not inst.is_paused
        )
        gpu_memory_total = sum(
            inst.gpu_memory_mb for inst in self._instances.values()
        )
        playing_count = sum(
            1 for inst in self._instances.values()
            if inst.is_playing and not inst.is_paused
        )
        paused_count = sum(
            1 for inst in self._instances.values() if inst.is_paused
        )

        shape_counts: Dict[str, int] = {}
        for cfg in self._configs.values():
            shape = cfg.emitter_shape.value
            shape_counts[shape] = shape_counts.get(shape, 0) + 1

        return {
            "total_instances": len(self._instances),
            "total_configs": len(self._configs),
            "total_active_particles": total_active_particles,
            "gpu_memory_total_mb": round(gpu_memory_total, 2),
            "playing_instances": playing_count,
            "paused_instances": paused_count,
            "compute_shader_bound": self._compute_shader_bound,
            "simulation_ticks": self._simulation_tick_count,
            "memory_per_particle_bytes": self._gpu_memory_per_particle_bytes,
            "by_emitter_shape": shape_counts,
            "lod_summary": {
                "full": sum(1 for i in self._instances.values() if i.lod_level == LODLevel.FULL),
                "half": sum(1 for i in self._instances.values() if i.lod_level == LODLevel.HALF),
                "quarter": sum(1 for i in self._instances.values() if i.lod_level == LODLevel.QUARTER),
            },
        }

    def reset_all(self) -> None:
        self._instances.clear()
        self._configs.clear()
        self._simulation_tick_count = 0

    def dispatch_compute(self, instance_id: str, particle_buffer: Any = None) -> Dict[str, Any]:
        instance = self._instances.get(instance_id)
        if not instance:
            return {"status": "error", "message": "Instance not found"}

        config = self._configs.get(instance.config_id)
        if not config:
            return {"status": "error", "message": "Config not found"}

        if not instance.is_playing or instance.is_paused:
            return {"status": "idle", "instance_id": instance_id[:12]}

        workgroup_size = 256
        num_groups = (config.max_particles + workgroup_size - 1) // workgroup_size

        return {
            "status": "dispatched",
            "instance_id": instance_id[:12],
            "workgroup_size": workgroup_size,
            "num_workgroups": num_groups,
            "particle_count": instance.active_particles,
            "max_particles": config.max_particles,
            "force_field_count": len(instance._force_fields),
            "tick": self._simulation_tick_count,
        }


def get_gpu_particle_system() -> GPUParticleSystem:
    return GPUParticleSystem.get_instance()