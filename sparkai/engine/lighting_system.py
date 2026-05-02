"""
Lighting System - 2D dynamic lighting with point lights, ambient light, and masks.

Architecture:
    LightingSystem/
    |-- LightType (point, directional, spot enumeration)
    |-- BlendMode (additive, multiplicative, subtractive enumeration)
    |-- LightConfig (light source configuration dataclass)
    |-- LightSource (active light instance dataclass)
    |-- LightingLayer (render layer with blending dataclass)
    |-- LightingSystem (global lighting orchestration)

Manages 2D lighting with configurable light sources, ambient lighting,
blend modes, and layer compositing. Supports light culling, falloff curves,
and shadow mask integration.
"""

from __future__ import annotations

import uuid
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class LightType(Enum):
    POINT = auto()
    DIRECTIONAL = auto()
    SPOT = auto()


class BlendMode(Enum):
    ADDITIVE = auto()
    MULTIPLICATIVE = auto()
    SUBTRACTIVE = auto()


class FalloffMode(Enum):
    LINEAR = "linear"
    QUADRATIC = "quadratic"
    SMOOTHSTEP = "smoothstep"


@dataclass
class LightConfig:
    light_type: LightType = LightType.POINT
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    intensity: float = 1.0
    radius: float = 200.0
    falloff: FalloffMode = FalloffMode.QUADRATIC
    blend: BlendMode = BlendMode.ADDITIVE
    cast_shadows: bool = False
    shadow_resolution: int = 256
    inner_angle: float = 30.0
    outer_angle: float = 60.0
    jitter: float = 0.0
    flicker_frequency: float = 0.0
    flicker_amplitude: float = 0.0


@dataclass
class LightSource:
    light_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Light"
    config: LightConfig = field(default_factory=LightConfig)
    position: Tuple[float, float] = (0.0, 0.0)
    direction: Tuple[float, float] = (0.0, -1.0)
    enabled: bool = True
    layer: int = 0
    cull_mask: int = 0xFFFFFFFF
    elapsed: float = 0.0
    owner_id: str = ""

    def compute_attenuation(self, distance: float) -> float:
        if distance >= self.config.radius:
            return 0.0
        ratio = distance / self.config.radius
        if self.config.falloff == FalloffMode.LINEAR:
            return max(0.0, 1.0 - ratio)
        elif self.config.falloff == FalloffMode.QUADRATIC:
            return max(0.0, 1.0 - ratio * ratio)
        elif self.config.falloff == FalloffMode.SMOOTHSTEP:
            t = max(0.0, min(1.0, 1.0 - ratio))
            return t * t * (3.0 - 2.0 * t)
        return 0.0

    def get_effective_intensity(self) -> float:
        intensity = self.config.intensity
        if self.config.flicker_frequency > 0:
            noise = math.sin(self.elapsed * self.config.flicker_frequency * 2 * math.pi)
            intensity += noise * self.config.flicker_amplitude
        if self.config.jitter > 0:
            import random
            intensity += random.uniform(-self.config.jitter, self.config.jitter)
        return max(0.0, intensity)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "light_id": self.light_id,
            "name": self.name,
            "type": self.config.light_type.name,
            "position": list(self.position),
            "direction": list(self.direction),
            "intensity": self.config.intensity,
            "radius": self.config.radius,
            "enabled": self.enabled,
            "layer": self.layer,
            "color": list(self.config.color),
            "blend": self.config.blend.name,
            "cast_shadows": self.config.cast_shadows,
        }


@dataclass
class LightingLayer:
    layer_name: str = "default"
    layer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    blend: BlendMode = BlendMode.ADDITIVE
    opacity: float = 1.0
    visible: bool = True
    sort_order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "layer_name": self.layer_name,
            "blend": self.blend.name,
            "opacity": self.opacity,
            "visible": self.visible,
            "sort_order": self.sort_order,
        }


class LightingSystem:
    _instance: Optional["LightingSystem"] = None

    def __init__(self):
        self._lights: Dict[str, LightSource] = {}
        self._layers: Dict[str, LightingLayer] = {}
        self._ambient_color: Tuple[float, float, float, float] = (0.1, 0.1, 0.15, 1.0)
        self._ambient_intensity: float = 0.3
        self._global_light_mask: int = 0xFFFFFFFF
        self._enabled: bool = True

    @classmethod
    def get_instance(cls) -> "LightingSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_light(self, light: LightSource) -> str:
        self._lights[light.light_id] = light
        return light.light_id

    def create_light(
        self,
        name: str = "Light",
        light_type: LightType = LightType.POINT,
        position: Tuple[float, float] = (0.0, 0.0),
        color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        intensity: float = 1.0,
        radius: float = 200.0,
    ) -> LightSource:
        config = LightConfig(
            light_type=light_type,
            color=color,
            intensity=intensity,
            radius=radius,
        )
        light = LightSource(name=name, config=config, position=position)
        self._lights[light.light_id] = light
        return light

    def remove_light(self, light_id: str) -> bool:
        if light_id in self._lights:
            del self._lights[light_id]
            return True
        return False

    def get_light(self, light_id: str) -> Optional[LightSource]:
        return self._lights.get(light_id)

    def set_light_position(self, light_id: str, x: float, y: float) -> bool:
        light = self._lights.get(light_id)
        if light:
            light.position = (x, y)
            return True
        return False

    def set_light_enabled(self, light_id: str, enabled: bool) -> bool:
        light = self._lights.get(light_id)
        if light:
            light.enabled = enabled
            return True
        return False

    def list_lights(self) -> List[LightSource]:
        return list(self._lights.values())

    def add_layer(self, layer: LightingLayer) -> str:
        self._layers[layer.layer_id] = layer
        return layer.layer_id

    def create_layer(
        self,
        name: str = "default",
        blend: BlendMode = BlendMode.ADDITIVE,
        opacity: float = 1.0,
    ) -> LightingLayer:
        layer = LightingLayer(layer_name=name, blend=blend, opacity=opacity)
        self._layers[layer.layer_id] = layer
        return layer

    def remove_layer(self, layer_id: str) -> bool:
        if layer_id in self._layers:
            del self._layers[layer_id]
            return True
        return False

    def list_layers(self) -> List[LightingLayer]:
        return sorted(self._layers.values(), key=lambda l: l.sort_order)

    def set_ambient(self, color: Tuple[float, float, float, float], intensity: float) -> None:
        self._ambient_color = color
        self._ambient_intensity = intensity

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def query_lights_in_range(
        self, position: Tuple[float, float], radius: float
    ) -> List[LightSource]:
        px, py = position
        results = []
        for light in self._lights.values():
            if not light.enabled:
                continue
            lx, ly = light.position
            dist = math.sqrt((lx - px) ** 2 + (ly - py) ** 2)
            effective_range = max(light.config.radius, radius)
            if dist <= effective_range:
                results.append(light)
        return results

    def update(self, dt: float) -> None:
        for light in self._lights.values():
            if light.enabled:
                light.elapsed += dt

    def get_stats(self) -> Dict[str, Any]:
        return {
            "light_count": len(self._lights),
            "layer_count": len(self._layers),
            "enabled_lights": sum(1 for l in self._lights.values() if l.enabled),
            "shadow_casters": sum(1 for l in self._lights.values() if l.config.cast_shadows),
            "ambient_intensity": self._ambient_intensity,
            "enabled": self._enabled,
        }


def get_lighting_system() -> LightingSystem:
    return LightingSystem.get_instance()
