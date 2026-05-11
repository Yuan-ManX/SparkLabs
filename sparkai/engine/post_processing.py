"""
SparkLabs Engine - Post Processing System

Real-time screen-space visual effect pipeline for AI-native games.
Manages composable effect stacks with configurable parameters,
priority-based ordering, and layer mask filtering for cinematic
rendering, stylized visuals, and gameplay-driven feedback.

Architecture:
  PostProcessingSystem
    |-- EffectStackManager (ordered effect layer composition)
    |-- ParameterBlender (smooth parameter interpolation)
    |-- RenderTargetChain (multi-pass render target management)
    |-- LayerFilter (camera-layer selective effect application)

Effect Types:
  - BLOOM, VIGNETTE, CHROMATIC_ABERRATION, COLOR_GRADING
  - MOTION_BLUR, DEPTH_OF_FIELD, AMBIENT_OCCLUSION
  - FILM_GRAIN, LENS_FLARE, PIXELATION
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PostProcessEffect(Enum):
    BLOOM = "bloom"
    VIGNETTE = "vignette"
    CHROMATIC_ABERRATION = "chromatic_aberration"
    COLOR_GRADING = "color_grading"
    MOTION_BLUR = "motion_blur"
    DEPTH_OF_FIELD = "depth_of_field"
    AMBIENT_OCCLUSION = "ambient_occlusion"
    FILM_GRAIN = "film_grain"
    LENS_FLARE = "lens_flare"
    PIXELATION = "pixelation"


@dataclass
class EffectParams:
    enabled: bool = True
    intensity: float = 1.0
    threshold: float = 0.5
    radius: float = 1.0
    color_tint_r: float = 1.0
    color_tint_g: float = 1.0
    color_tint_b: float = 1.0
    quality_level: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "intensity": self.intensity,
            "threshold": self.threshold,
            "radius": self.radius,
            "color_tint": [self.color_tint_r, self.color_tint_g, self.color_tint_b],
            "quality_level": self.quality_level,
        }

    @property
    def color_tint(self) -> Tuple[float, float, float]:
        return (self.color_tint_r, self.color_tint_g, self.color_tint_b)


DEFAULT_EFFECT_PARAMS: Dict[PostProcessEffect, EffectParams] = {
    PostProcessEffect.BLOOM: EffectParams(
        enabled=False, intensity=0.5, threshold=0.8, radius=1.5, quality_level=3,
    ),
    PostProcessEffect.VIGNETTE: EffectParams(
        enabled=False, intensity=0.4, threshold=0.3, radius=1.2, quality_level=1,
    ),
    PostProcessEffect.CHROMATIC_ABERRATION: EffectParams(
        enabled=False, intensity=0.3, threshold=0.0, radius=0.5, quality_level=2,
    ),
    PostProcessEffect.COLOR_GRADING: EffectParams(
        enabled=False, intensity=1.0, threshold=0.0, radius=0.0,
        color_tint_r=1.0, color_tint_g=1.0, color_tint_b=1.0, quality_level=2,
    ),
    PostProcessEffect.MOTION_BLUR: EffectParams(
        enabled=False, intensity=0.6, threshold=0.05, radius=0.8, quality_level=2,
    ),
    PostProcessEffect.DEPTH_OF_FIELD: EffectParams(
        enabled=False, intensity=0.5, threshold=0.0, radius=2.0, quality_level=3,
    ),
    PostProcessEffect.AMBIENT_OCCLUSION: EffectParams(
        enabled=False, intensity=0.8, threshold=0.3, radius=1.0, quality_level=2,
    ),
    PostProcessEffect.FILM_GRAIN: EffectParams(
        enabled=False, intensity=0.15, threshold=0.0, radius=0.0, quality_level=1,
    ),
    PostProcessEffect.LENS_FLARE: EffectParams(
        enabled=False, intensity=0.7, threshold=0.6, radius=1.0, quality_level=2,
    ),
    PostProcessEffect.PIXELATION: EffectParams(
        enabled=False, intensity=0.5, threshold=0.0, radius=4.0, quality_level=1,
    ),
}


@dataclass
class PostProcessStack:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    effects: List[EffectParams] = field(default_factory=list)
    priority: int = 0
    layer_mask: int = 0xFFFFFFFF

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "effect_count": len(self.effects),
            "priority": self.priority,
            "layer_mask": self.layer_mask,
        }


class PostProcessingSystem:
    _instance: Optional[PostProcessingSystem] = None

    def __init__(self):
        self._stacks: Dict[str, PostProcessStack] = {}
        self._effect_registry: Dict[str, Dict[PostProcessEffect, EffectParams]] = {}
        self._frames_rendered: int = 0
        self._active_effect_count: Dict[str, int] = {}

    @classmethod
    def get_instance(cls) -> PostProcessingSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_stack(
        self,
        name: str,
        priority: int = 0,
        layer_mask: int = 0xFFFFFFFF,
    ) -> str:
        stack = PostProcessStack(
            name=name,
            priority=priority,
            layer_mask=layer_mask,
        )
        self._stacks[stack.id] = stack
        self._effect_registry[stack.id] = {}
        self._active_effect_count[stack.id] = 0
        return stack.id

    def remove_stack(self, stack_id: str) -> bool:
        if stack_id not in self._stacks:
            return False
        del self._stacks[stack_id]
        self._effect_registry.pop(stack_id, None)
        self._active_effect_count.pop(stack_id, None)
        return True

    def add_effect(
        self,
        stack_id: str,
        effect_type: PostProcessEffect,
        custom_params: Optional[EffectParams] = None,
    ) -> bool:
        stack = self._stacks.get(stack_id)
        if stack is None:
            return False

        registry = self._effect_registry.setdefault(stack_id, {})

        if effect_type in registry:
            return False

        params = custom_params if custom_params is not None else EffectParams(
            **DEFAULT_EFFECT_PARAMS.get(effect_type, EffectParams()).__dict__
        )

        registry[effect_type] = params
        stack.effects.append(params)
        if params.enabled:
            self._active_effect_count[stack_id] = (
                self._active_effect_count.get(stack_id, 0) + 1
            )
        return True

    def remove_effect(self, stack_id: str, effect_type: PostProcessEffect) -> bool:
        stack = self._stacks.get(stack_id)
        if stack is None:
            return False

        registry = self._effect_registry.get(stack_id)
        if registry is None or effect_type not in registry:
            return False

        params = registry[effect_type]
        if params in stack.effects:
            stack.effects.remove(params)

        if params.enabled:
            self._active_effect_count[stack_id] = max(
                0, self._active_effect_count.get(stack_id, 1) - 1
            )

        del registry[effect_type]
        return True

    def set_effect_params(
        self,
        stack_id: str,
        effect_type: PostProcessEffect,
        intensity: Optional[float] = None,
        threshold: Optional[float] = None,
        radius: Optional[float] = None,
        color_tint: Optional[Tuple[float, float, float]] = None,
        quality_level: Optional[int] = None,
    ) -> bool:
        registry = self._effect_registry.get(stack_id)
        if registry is None or effect_type not in registry:
            return False

        params = registry[effect_type]

        if intensity is not None:
            params.intensity = max(0.0, min(1.0, intensity))
        if threshold is not None:
            params.threshold = max(0.0, min(1.0, threshold))
        if radius is not None:
            params.radius = max(0.0, radius)
        if color_tint is not None:
            params.color_tint_r = max(0.0, min(1.0, color_tint[0]))
            params.color_tint_g = max(0.0, min(1.0, color_tint[1]))
            params.color_tint_b = max(0.0, min(1.0, color_tint[2]))
        if quality_level is not None:
            params.quality_level = max(0, min(4, quality_level))

        return True

    def enable_effect(self, stack_id: str, effect_type: PostProcessEffect) -> bool:
        registry = self._effect_registry.get(stack_id)
        if registry is None or effect_type not in registry:
            return False

        params = registry[effect_type]
        if not params.enabled:
            params.enabled = True
            self._active_effect_count[stack_id] = (
                self._active_effect_count.get(stack_id, 0) + 1
            )
        return True

    def disable_effect(self, stack_id: str, effect_type: PostProcessEffect) -> bool:
        registry = self._effect_registry.get(stack_id)
        if registry is None or effect_type not in registry:
            return False

        params = registry[effect_type]
        if params.enabled:
            params.enabled = False
            self._active_effect_count[stack_id] = max(
                0, self._active_effect_count.get(stack_id, 1) - 1
            )
        return True

    def render_frame(self, stack_id: str) -> Dict[str, Any]:
        stack = self._stacks.get(stack_id)
        if stack is None:
            return {"error": "stack not found"}

        self._frames_rendered += 1

        applied_effects: List[str] = []
        for effect_type, params in self._effect_registry.get(stack_id, {}).items():
            if params.enabled and params.intensity > 0.0:
                applied_effects.append(effect_type.value)

        return {
            "stack_id": stack_id,
            "frame": self._frames_rendered,
            "effects_applied": applied_effects,
            "effect_count": len(applied_effects),
        }

    def get_stack(self, stack_id: str) -> Optional[PostProcessStack]:
        return self._stacks.get(stack_id)

    def get_effect_params(
        self, stack_id: str, effect_type: PostProcessEffect
    ) -> Optional[EffectParams]:
        registry = self._effect_registry.get(stack_id)
        if registry is None:
            return None
        return registry.get(effect_type)

    def get_active_effects(self, stack_id: str) -> List[Dict[str, Any]]:
        registry = self._effect_registry.get(stack_id)
        if registry is None:
            return []

        active = []
        for effect_type, params in registry.items():
            if params.enabled:
                active.append({
                    "effect": effect_type.value,
                    "intensity": params.intensity,
                    "quality_level": params.quality_level,
                })
        return active

    def get_sorted_stacks(self) -> List[PostProcessStack]:
        return sorted(self._stacks.values(), key=lambda s: s.priority, reverse=True)

    def get_all_stacks(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for stack_id, stack in self._stacks.items():
            result[stack_id] = stack.to_dict()
        return result

    def get_stats(self) -> Dict[str, Any]:
        stack_details = {}
        for stack_id, stack in self._stacks.items():
            registry = self._effect_registry.get(stack_id, {})
            active_count = sum(1 for p in registry.values() if p.enabled)
            stack_details[stack_id] = {
                "name": stack.name,
                "priority": stack.priority,
                "total_effects": len(registry),
                "active_effects": active_count,
            }
        return {
            "total_stacks": len(self._stacks),
            "frames_rendered": self._frames_rendered,
            "stacks": stack_details,
        }


def get_post_processing() -> PostProcessingSystem:
    return PostProcessingSystem.get_instance()