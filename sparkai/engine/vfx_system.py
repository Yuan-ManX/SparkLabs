"""
VFX System - Visual effects creation, particle management, and runtime simulation.

Architecture:
    VFXSystem/
    |-- VFXType (effect category classification)
    |-- EmissionShape (particle spawn volume shapes)
    |-- VFXModule (pluggable effect behavior module)
    |-- VFXDefinition (complete visual effect with modules and parameters)
    |-- VFXSystem (unified effect lifecycle and runtime orchestrator)

Manages all visual effects including particle bursts, trails, beams, explosions,
weather, magic, environmental, and screen-space effects. Supports modular
behavior composition, looping effects, emission rate control, and render layer
ordering for the full visual pipeline.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class VFXType(Enum):
    PARTICLE_BURST = "particle_burst"
    TRAIL = "trail"
    BEAM = "beam"
    EXPLOSION = "explosion"
    WEATHER = "weather"
    MAGIC = "magic"
    ENVIRONMENTAL = "environmental"
    SCREEN_SPACE = "screen_space"


class EmissionShape(Enum):
    POINT = "point"
    SPHERE = "sphere"
    CONE = "cone"
    BOX = "box"
    CIRCLE = "circle"
    MESH_SURFACE = "mesh_surface"
    LINE = "line"


@dataclass
class VFXModule:
    module_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def update_param(self, key: str, value: Any) -> None:
        self.params[key] = value

    def get_param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_type": self.module_type,
            "params": self.params,
            "enabled": self.enabled,
        }


@dataclass
class VFXDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Effect"
    vfx_type: VFXType = VFXType.PARTICLE_BURST
    emission_shape: EmissionShape = EmissionShape.POINT
    max_particles: int = 1000
    duration: float = 2.0
    modules: List[VFXModule] = field(default_factory=list)
    material_ref: str = ""
    layer: int = 0
    sort_order: int = 0
    is_looping: bool = False
    emission_rate: float = 100.0

    def add_module(self, module: VFXModule) -> None:
        self.modules.append(module)

    def remove_module(self, module_type: str) -> bool:
        for i, mod in enumerate(self.modules):
            if mod.module_type == module_type:
                self.modules.pop(i)
                return True
        return False

    def get_module(self, module_type: str) -> Optional[VFXModule]:
        for mod in self.modules:
            if mod.module_type == module_type:
                return mod
        return None

    def module_count(self) -> int:
        return len(self.modules)

    def enabled_module_count(self) -> int:
        return sum(1 for m in self.modules if m.enabled)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id[:12],
            "name": self.name,
            "vfx_type": self.vfx_type.value,
            "emission_shape": self.emission_shape.value,
            "max_particles": self.max_particles,
            "duration": self.duration,
            "module_count": self.module_count(),
            "enabled_modules": self.enabled_module_count(),
            "material_ref": self.material_ref,
            "layer": self.layer,
            "sort_order": self.sort_order,
            "is_looping": self.is_looping,
            "emission_rate": self.emission_rate,
        }


class VFXSystem:
    """Unified visual effects creation, management, and runtime orchestration."""

    _instance: Optional["VFXSystem"] = None

    def __init__(self):
        self._effects: Dict[str, VFXDefinition] = {}
        self._active_instances: Dict[str, Dict[str, Any]] = {}
        self._effect_count: int = 0
        self._total_particles_emitted: int = 0
        self._total_play_calls: int = 0
        self._instance_counter: int = 0

    @classmethod
    def get_instance(cls) -> "VFXSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_effect(
        self,
        name: str,
        vfx_type: VFXType = VFXType.PARTICLE_BURST,
        emission_shape: EmissionShape = EmissionShape.POINT,
        max_particles: int = 1000,
        duration: float = 2.0,
        is_looping: bool = False,
    ) -> VFXDefinition:
        effect = VFXDefinition(
            name=name,
            vfx_type=vfx_type,
            emission_shape=emission_shape,
            max_particles=max_particles,
            duration=duration,
            is_looping=is_looping,
        )
        self._effects[effect.id] = effect
        self._effect_count += 1
        return effect

    def add_module(
        self,
        effect_id: str,
        module_type: str,
        params: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
    ) -> bool:
        effect = self._effects.get(effect_id)
        if not effect:
            return False

        module = VFXModule(
            module_type=module_type,
            params=params or {},
            enabled=enabled,
        )
        effect.add_module(module)
        return True

    def play_effect(
        self,
        effect_id: str,
        position_x: float = 0.0,
        position_y: float = 0.0,
        position_z: float = 0.0,
        scale: float = 1.0,
    ) -> Optional[str]:
        effect = self._effects.get(effect_id)
        if not effect:
            return None

        self._instance_counter += 1
        instance_id = f"{effect_id}_{self._instance_counter}"

        self._active_instances[instance_id] = {
            "effect_id": effect_id,
            "effect_name": effect.name,
            "started_at": time.time(),
            "position": (position_x, position_y, position_z),
            "scale": scale,
            "elapsed": 0.0,
            "is_finished": False,
            "particles_emitted": 0,
        }

        self._total_play_calls += 1

        return instance_id

    def stop_effect(self, instance_id: str) -> bool:
        instance = self._active_instances.pop(instance_id, None)
        if instance is None:
            return False
        instance["is_finished"] = True
        return True

    def update_particles(self, instance_id: str, delta_time: float) -> Dict[str, Any]:
        instance = self._active_instances.get(instance_id)
        if not instance:
            return {"error": "Instance not found"}

        effect_id = instance["effect_id"]
        effect = self._effects.get(effect_id)
        if not effect:
            self._active_instances.pop(instance_id, None)
            return {"error": "Effect definition not found"}

        instance["elapsed"] += delta_time

        if not effect.is_looping and instance["elapsed"] >= effect.duration:
            instance["is_finished"] = True

        if instance["is_finished"]:
            return {"status": "finished", "elapsed": instance["elapsed"]}

        emitted_this_frame = int(effect.emission_rate * delta_time)
        emitted_this_frame = min(emitted_this_frame, effect.max_particles - instance["particles_emitted"])

        if emitted_this_frame > 0:
            instance["particles_emitted"] += emitted_this_frame
            self._total_particles_emitted += emitted_this_frame

        progress = min(1.0, instance["elapsed"] / max(0.001, effect.duration))

        return {
            "status": "playing",
            "elapsed": instance["elapsed"],
            "progress": round(progress, 4),
            "particles_emitted": instance["particles_emitted"],
            "particles_this_frame": emitted_this_frame,
            "total_particles": instance["particles_emitted"],
            "max_particles": effect.max_particles,
            "is_finished": instance["is_finished"],
        }

    def set_emission_rate(self, effect_id: str, rate: float) -> bool:
        effect = self._effects.get(effect_id)
        if not effect:
            return False

        effect.emission_rate = max(0.0, rate)
        return True

    def get_active_effects(self) -> List[Dict[str, Any]]:
        active_list = []
        for instance_id, instance in self._active_instances.items():
            if not instance.get("is_finished"):
                active_list.append({
                    "instance_id": instance_id[:32],
                    "effect_name": instance.get("effect_name", ""),
                    "elapsed": instance.get("elapsed", 0.0),
                    "position": instance.get("position", (0, 0, 0)),
                    "scale": instance.get("scale", 1.0),
                })
        return active_list

    def get_effect(self, effect_id: str) -> Optional[VFXDefinition]:
        return self._effects.get(effect_id)

    def list_effects(self) -> List[VFXDefinition]:
        return list(self._effects.values())

    def list_by_type(self, vfx_type: VFXType) -> List[VFXDefinition]:
        return [e for e in self._effects.values() if e.vfx_type == vfx_type]

    def list_by_layer(self, layer: int) -> List[VFXDefinition]:
        return sorted(
            [e for e in self._effects.values() if e.layer == layer],
            key=lambda e: e.sort_order,
        )

    def delete_effect(self, effect_id: str) -> bool:
        if effect_id in self._effects:
            del self._effects[effect_id]
            self._effect_count = max(0, self._effect_count - 1)
            return True
        return False

    def get_active_count(self) -> int:
        return sum(
            1 for inst in self._active_instances.values()
            if not inst.get("is_finished", False)
        )

    def get_total_active_particles(self) -> int:
        return sum(
            inst.get("particles_emitted", 0)
            for inst in self._active_instances.values()
            if not inst.get("is_finished", False)
        )

    def cleanup_finished(self) -> int:
        finished_ids = [
            iid for iid, inst in self._active_instances.items()
            if inst.get("is_finished", False)
        ]
        for iid in finished_ids:
            del self._active_instances[iid]
        return len(finished_ids)

    def reset_all_effects(self) -> None:
        self._active_instances.clear()
        self._total_particles_emitted = 0
        self._total_play_calls = 0
        self._instance_counter = 0

    def get_stats(self) -> Dict[str, Any]:
        type_counts = {}
        for effect in self._effects.values():
            vtype = effect.vfx_type.value
            type_counts[vtype] = type_counts.get(vtype, 0) + 1

        shape_counts = {}
        for effect in self._effects.values():
            shape = effect.emission_shape.value
            shape_counts[shape] = shape_counts.get(shape, 0) + 1

        return {
            "total_effects": len(self._effects),
            "effect_count": self._effect_count,
            "active_instances": self.get_active_count(),
            "total_active_particles": self.get_total_active_particles(),
            "total_particles_emitted": self._total_particles_emitted,
            "total_play_calls": self._total_play_calls,
            "by_type": type_counts,
            "by_emission_shape": shape_counts,
            "avg_modules_per_effect": (
                sum(e.module_count() for e in self._effects.values()) / max(1, len(self._effects))
            ),
        }


def get_vfx_system() -> VFXSystem:
    return VFXSystem.get_instance()