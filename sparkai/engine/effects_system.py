"""
Effects System - Visual post-processing pipeline for layers and game objects.

Architecture:
    EffectsSystem/
    |-- EffectType (bloom, blur, vignette, color-grading, etc.)
    |-- EffectBlend (compositing blend mode enumeration)
    |-- EffectConfig (effect parameter configuration dataclass)
    |-- EffectInstance (active effect on a target dataclass)
    |-- EffectStack (ordered render chain dataclass)
    |-- EffectsSystem (global effects orchestration)

Manages a configurable post-processing stack that the AI game editor can
compose and configure. Supports per-layer and per-object effect chains with
parameter animation, enable/disable toggling, and shader-based rendering.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class EffectType(Enum):
    BLOOM = auto()
    BLUR_GAUSSIAN = auto()
    BLUR_MOTION = auto()
    VIGNETTE = auto()
    COLOR_GRADING = auto()
    CHROMATIC_ABERRATION = auto()
    GRAIN = auto()
    SCANLINES = auto()
    PIXELATE = auto()
    OUTLINE = auto()
    GLOW = auto()
    DROP_SHADOW = auto()
    COLOR_OVERLAY = auto()
    DISTORTION = auto()
    CUSTOM = auto()


class EffectBlend(Enum):
    NORMAL = auto()
    ADDITIVE = auto()
    MULTIPLY = auto()
    SCREEN = auto()
    OVERLAY = auto()


@dataclass
class EffectConfig:
    effect_type: EffectType = EffectType.BLOOM
    intensity: float = 1.0
    blend: EffectBlend = EffectBlend.NORMAL
    params: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.effect_type.name,
            "intensity": self.intensity,
            "blend": self.blend.name,
            "params": self.params,
        }


@dataclass
class EffectInstance:
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config: EffectConfig = field(default_factory=EffectConfig)
    enabled: bool = True
    sort_order: int = 0
    target_id: str = ""
    target_type: str = "layer"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "config": self.config.to_dict(),
            "enabled": self.enabled,
            "sort_order": self.sort_order,
            "target_id": self.target_id,
            "target_type": self.target_type,
        }


@dataclass
class EffectStack:
    stack_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Default Stack"
    effects: List[EffectInstance] = field(default_factory=list)
    target_id: str = ""
    target_type: str = "layer"

    def get_sorted_effects(self) -> List[EffectInstance]:
        return sorted(
            [e for e in self.effects if e.enabled],
            key=lambda e: e.sort_order,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stack_id": self.stack_id,
            "name": self.name,
            "effect_count": len(self.effects),
            "enabled_count": sum(1 for e in self.effects if e.enabled),
            "target_id": self.target_id,
            "target_type": self.target_type,
            "effects": [e.to_dict() for e in self.get_sorted_effects()],
        }


class EffectsSystem:
    _instance: Optional["EffectsSystem"] = None

    def __init__(self):
        self._stacks: Dict[str, EffectStack] = {}
        self._presets: Dict[str, EffectConfig] = {}
        self._global_enabled: bool = True
        self._register_default_presets()

    def _register_default_presets(self) -> None:
        self._presets["bloom_soft"] = EffectConfig(
            effect_type=EffectType.BLOOM,
            intensity=0.5,
            params={"threshold": 0.8, "radius": 4.0, "softness": 2.0},
        )
        self._presets["blur_light"] = EffectConfig(
            effect_type=EffectType.BLUR_GAUSSIAN,
            intensity=0.3,
            params={"radius": 2.0, "passes": 1},
        )
        self._presets["vignette_dark"] = EffectConfig(
            effect_type=EffectType.VIGNETTE,
            intensity=0.6,
            params={"radius": 0.8, "softness": 0.3, "color_r": 0.0, "color_g": 0.0, "color_b": 0.0},
        )
        self._presets["retro"] = EffectConfig(
            effect_type=EffectType.SCANLINES,
            intensity=0.4,
            params={"line_spacing": 2.0, "offset": 0.0},
        )
        self._presets["pixel_art"] = EffectConfig(
            effect_type=EffectType.PIXELATE,
            intensity=1.0,
            params={"pixel_size": 4.0},
        )
        self._presets["chromatic"] = EffectConfig(
            effect_type=EffectType.CHROMATIC_ABERRATION,
            intensity=0.5,
            params={"offset_r": 2.0, "offset_b": -2.0},
        )

    @classmethod
    def get_instance(cls) -> "EffectsSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_stack(self, name: str = "Stack", target_id: str = "",
                     target_type: str = "layer") -> EffectStack:
        stack = EffectStack(name=name, target_id=target_id, target_type=target_type)
        self._stacks[stack.stack_id] = stack
        return stack

    def get_stack(self, stack_id: str) -> Optional[EffectStack]:
        return self._stacks.get(stack_id)

    def find_stacks_for_target(self, target_id: str) -> List[EffectStack]:
        return [s for s in self._stacks.values() if s.target_id == target_id]

    def remove_stack(self, stack_id: str) -> bool:
        if stack_id in self._stacks:
            del self._stacks[stack_id]
            return True
        return False

    def add_effect(self, stack_id: str, effect_config: EffectConfig,
                   sort_order: Optional[int] = None) -> Optional[EffectInstance]:
        stack = self._stacks.get(stack_id)
        if not stack:
            return None
        instance = EffectInstance(
            config=effect_config,
            target_id=stack.target_id,
            target_type=stack.target_type,
        )
        if sort_order is not None:
            instance.sort_order = sort_order
        else:
            instance.sort_order = len(stack.effects)
        stack.effects.append(instance)
        return instance

    def add_effect_by_preset(self, stack_id: str, preset_name: str,
                             sort_order: Optional[int] = None) -> Optional[EffectInstance]:
        config = self._presets.get(preset_name)
        if not config:
            return None
        return self.add_effect(stack_id, config, sort_order)

    def remove_effect(self, stack_id: str, instance_id: str) -> bool:
        stack = self._stacks.get(stack_id)
        if not stack:
            return False
        for i, effect in enumerate(stack.effects):
            if effect.instance_id == instance_id:
                stack.effects.pop(i)
                return True
        return False

    def set_effect_enabled(self, stack_id: str, instance_id: str, enabled: bool) -> bool:
        stack = self._stacks.get(stack_id)
        if not stack:
            return False
        for effect in stack.effects:
            if effect.instance_id == instance_id:
                effect.enabled = enabled
                return True
        return False

    def set_effect_intensity(self, stack_id: str, instance_id: str, intensity: float) -> bool:
        stack = self._stacks.get(stack_id)
        if not stack:
            return False
        for effect in stack.effects:
            if effect.instance_id == instance_id:
                effect.config.intensity = max(0.0, min(2.0, intensity))
                return True
        return False

    def set_effect_param(self, stack_id: str, instance_id: str,
                         param_name: str, value: float) -> bool:
        stack = self._stacks.get(stack_id)
        if not stack:
            return False
        for effect in stack.effects:
            if effect.instance_id == instance_id:
                effect.config.params[param_name] = value
                return True
        return False

    def reorder_effect(self, stack_id: str, instance_id: str, new_order: int) -> bool:
        stack = self._stacks.get(stack_id)
        if not stack:
            return False
        for effect in stack.effects:
            if effect.instance_id == instance_id:
                effect.sort_order = new_order
                return True
        return False

    def list_stacks(self) -> List[EffectStack]:
        return list(self._stacks.values())

    def list_presets(self) -> List[Dict[str, Any]]:
        return [{"name": name, **config.to_dict()} for name, config in self._presets.items()]

    def set_global_enabled(self, enabled: bool) -> None:
        self._global_enabled = enabled

    def get_stats(self) -> Dict[str, Any]:
        total_effects = sum(len(s.effects) for s in self._stacks.values())
        enabled_effects = sum(
            sum(1 for e in s.effects if e.enabled) for s in self._stacks.values()
        )
        return {
            "stack_count": len(self._stacks),
            "preset_count": len(self._presets),
            "total_effects": total_effects,
            "enabled_effects": enabled_effects,
            "global_enabled": self._global_enabled,
            "presets": list(self._presets.keys()),
        }


def get_effects_system() -> EffectsSystem:
    return EffectsSystem.get_instance()
