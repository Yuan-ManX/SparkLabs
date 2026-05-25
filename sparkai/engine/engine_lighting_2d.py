"""
SparkLabs Engine - 2D Lighting Engine

Dynamic 2D lighting system with point lights, spot lights, ambient light,
shadow casting, and light blending for 2D game scenes. Manages light
sources organized into layers with configurable blend modes, falloff
curves, and per-light shadow casting.

Architecture:
  Lighting2DEngine
    |-- LightSource (point, spot, directional, ambient, area, pulsating)
    |-- LightLayer (grouped lights with shared blend/ambient)
    |-- ShadowCaster2D (occlusion geometry for light rays)
    |-- LightingConfig (scene-level lighting parameters)

Lighting Pipeline:
  1. Collect active lights per layer within scene bounds
  2. For each light, compute attenuation and falloff
  3. Cast shadow rays against registered shadow casters
  4. Blend overlapping lights using layer blend mode
  5. Apply ambient contribution and tonemapping
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class LightType(Enum):
    """Classification of 2D light source behavior."""
    POINT = "point"
    SPOT = "spot"
    DIRECTIONAL = "directional"
    AMBIENT = "ambient"
    AREA = "area"
    PULSATING = "pulsating"


class ShadowQuality(Enum):
    """Resolution and fidelity tier for shadow casting."""
    OFF = "off"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class BlendMode(Enum):
    """Compositing operation for combining overlapping light contributions."""
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"


class LightFalloff(Enum):
    """Attenuation curve that determines how light intensity drops with distance."""
    LINEAR = "linear"
    QUADRATIC = "quadratic"
    SMOOTHSTEP = "smoothstep"
    CUSTOM_CURVE = "custom_curve"


@dataclass
class LightSource:
    """Individual 2D light emitter with position, color, and shadow settings."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    light_type: LightType = LightType.POINT
    position: Tuple[float, float] = (0.0, 0.0)
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    radius: float = 100.0
    falloff: LightFalloff = LightFalloff.QUADRATIC
    cast_shadows: bool = False
    shadow_quality: ShadowQuality = ShadowQuality.MEDIUM
    enabled: bool = True
    layer_mask: int = 1
    flicker_config: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "light_type": self.light_type.value,
            "position": list(self.position),
            "color": list(self.color),
            "intensity": self.intensity,
            "radius": self.radius,
            "falloff": self.falloff.value,
            "cast_shadows": self.cast_shadows,
            "shadow_quality": self.shadow_quality.value,
            "enabled": self.enabled,
            "layer_mask": self.layer_mask,
            "flicker_config": self.flicker_config,
            "created_at": self.created_at,
        }


@dataclass
class LightLayer:
    """Group of 2D lights sharing a common blend mode and ambient base."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    lights: List[str] = field(default_factory=list)
    blend_mode: BlendMode = BlendMode.ADDITIVE
    ambient_color: Tuple[float, float, float] = (0.05, 0.05, 0.05)
    ambient_intensity: float = 0.1
    z_order: int = 0
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "light_count": len(self.lights),
            "blend_mode": self.blend_mode.value,
            "ambient_color": list(self.ambient_color),
            "ambient_intensity": self.ambient_intensity,
            "z_order": self.z_order,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


@dataclass
class ShadowCaster2D:
    """Occlusion geometry that blocks light rays to produce shadows."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    cast_method: str = "hard"
    resolution: int = 256
    softness: float = 1.0
    self_shadow: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "cast_method": self.cast_method,
            "resolution": self.resolution,
            "softness": self.softness,
            "self_shadow": self.self_shadow,
            "created_at": self.created_at,
        }


@dataclass
class LightingConfig:
    """Scene-level parameters that control the global lighting pipeline."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scene_id: str = ""
    max_lights: int = 128
    default_ambient: Tuple[float, float, float] = (0.1, 0.1, 0.1)
    shadow_enabled: bool = True
    tonemapping: str = "linear"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scene_id": self.scene_id,
            "max_lights": self.max_lights,
            "default_ambient": list(self.default_ambient),
            "shadow_enabled": self.shadow_enabled,
            "tonemapping": self.tonemapping,
            "created_at": self.created_at,
        }


class Lighting2DEngine:
    """
    Dynamic 2D lighting system for game scenes.

    Manages light sources organized into layers, computes per-pixel
    or per-vertex lighting with attenuation, shadow casting, and
    multi-pass blending. Supports animated lights via flicker
    modulation and static light baking for performance.

    Usage:
        engine = get_lighting_2d()
        sun = engine.create_light("sun", "directional", (0, 200), (1.0, 0.95, 0.8), 1.5, 800)
        torch = engine.create_light("torch", "point", (320, 240), (1.0, 0.6, 0.2), 0.8, 120)
        torch = engine.set_flicker(torch.id, frequency=4.0, amplitude=0.3)
        result = engine.calculate_lighting((0, 0, 640, 480), ["player", "crate"])
    """

    _instance: Optional["Lighting2DEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_LIGHTS_PER_LAYER = 256
    MAX_LAYERS = 32
    MAX_SHADOW_CASTER_RESOLUTION = 2048
    SHADOW_RAY_COUNT = {
        "off": 0,
        "low": 16,
        "medium": 64,
        "high": 128,
        "ultra": 256,
    }

    def __new__(cls) -> "Lighting2DEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._lights: Dict[str, LightSource] = {}
        self._layers: Dict[str, LightLayer] = {}
        self._shadow_casters: Dict[str, ShadowCaster2D] = {}
        self._configs: Dict[str, LightingConfig] = {}
        self._light_map_cache: Dict[str, Any] = {}

        self._total_lights_created: int = 0
        self._total_shadows_cast: int = 0
        self._total_bakes: int = 0
        self._total_optimizations: int = 0

    @classmethod
    def get_instance(cls) -> "Lighting2DEngine":
        return cls()

    # ------------------------------------------------------------------
    # Light Creation and Management
    # ------------------------------------------------------------------

    def create_light(
        self,
        name: str,
        light_type: str = "point",
        position: Tuple[float, float] = (0.0, 0.0),
        color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        intensity: float = 1.0,
        radius: float = 100.0,
    ) -> LightSource:
        total = sum(len(layer.lights) for layer in self._layers.values())
        if total >= self.MAX_LIGHTS_PER_LAYER * self.MAX_LAYERS:
            raise RuntimeError(
                "Global light capacity reached. Remove unused lights "
                "before creating new ones."
            )

        try:
            lt = LightType(light_type.lower())
        except ValueError:
            lt = LightType.POINT

        light = LightSource(
            name=name,
            light_type=lt,
            position=position,
            color=(
                max(0.0, min(1.0, color[0])),
                max(0.0, min(1.0, color[1])),
                max(0.0, min(1.0, color[2])),
            ),
            intensity=max(0.0, intensity),
            radius=max(1.0, radius),
        )
        self._lights[light.id] = light
        self._total_lights_created += 1
        return light

    def get_light(self, light_id: str) -> Optional[LightSource]:
        return self._lights.get(light_id)

    def find_light_by_name(self, name: str) -> Optional[LightSource]:
        for light in self._lights.values():
            if light.name.lower() == name.lower():
                return light
        return None

    def remove_light(self, light_id: str) -> bool:
        if light_id not in self._lights:
            return False
        for layer in self._layers.values():
            if light_id in layer.lights:
                layer.lights.remove(light_id)
        del self._lights[light_id]
        self._light_map_cache.pop(light_id, None)
        return True

    def configure_light(self, light_id: str, **params: Any) -> Optional[LightSource]:
        light = self._lights.get(light_id)
        if light is None:
            return None

        if "name" in params:
            light.name = str(params["name"])
        if "light_type" in params:
            try:
                light.light_type = LightType(str(params["light_type"]).lower())
            except ValueError:
                pass
        if "position" in params:
            pos = params["position"]
            if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                light.position = (float(pos[0]), float(pos[1]))
        if "color" in params:
            c = params["color"]
            if isinstance(c, (list, tuple)) and len(c) >= 3:
                light.color = (
                    max(0.0, min(1.0, float(c[0]))),
                    max(0.0, min(1.0, float(c[1]))),
                    max(0.0, min(1.0, float(c[2]))),
                )
        if "intensity" in params:
            light.intensity = max(0.0, float(params["intensity"]))
        if "radius" in params:
            light.radius = max(1.0, float(params["radius"]))
        if "falloff" in params:
            try:
                light.falloff = LightFalloff(str(params["falloff"]).lower())
            except ValueError:
                pass
        if "cast_shadows" in params:
            light.cast_shadows = bool(params["cast_shadows"])
        if "shadow_quality" in params:
            try:
                light.shadow_quality = ShadowQuality(
                    str(params["shadow_quality"]).lower()
                )
            except ValueError:
                pass
        if "enabled" in params:
            light.enabled = bool(params["enabled"])
        if "layer_mask" in params:
            light.layer_mask = int(params["layer_mask"])
        if "flicker_config" in params:
            light.flicker_config = dict(params["flicker_config"])

        return light

    def get_light_count(self) -> int:
        return len(self._lights)

    # ------------------------------------------------------------------
    # Layer Management
    # ------------------------------------------------------------------

    def create_layer(
        self,
        name: str,
        blend_mode: str = "additive",
        ambient_color: Tuple[float, float, float] = (0.05, 0.05, 0.05),
    ) -> LightLayer:
        if len(self._layers) >= self.MAX_LAYERS:
            raise RuntimeError(
                f"Layer limit reached ({self.MAX_LAYERS}). "
                "Remove unused layers before creating new ones."
            )

        try:
            bm = BlendMode(blend_mode.lower())
        except ValueError:
            bm = BlendMode.ADDITIVE

        layer = LightLayer(
            name=name,
            blend_mode=bm,
            ambient_color=(
                max(0.0, min(1.0, ambient_color[0])),
                max(0.0, min(1.0, ambient_color[1])),
                max(0.0, min(1.0, ambient_color[2])),
            ),
            z_order=len(self._layers),
        )
        self._layers[layer.id] = layer
        return layer

    def get_layer(self, layer_id: str) -> Optional[LightLayer]:
        return self._layers.get(layer_id)

    def remove_layer(self, layer_id: str) -> bool:
        if layer_id not in self._layers:
            return False
        del self._layers[layer_id]
        return True

    def add_light_to_layer(self, layer_id: str, light_id: str) -> bool:
        layer = self._layers.get(layer_id)
        light = self._lights.get(light_id)
        if layer is None or light is None:
            return False
        if len(layer.lights) >= self.MAX_LIGHTS_PER_LAYER:
            return False
        if light_id not in layer.lights:
            layer.lights.append(light_id)
        return True

    def remove_light_from_layer(self, layer_id: str, light_id: str) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        if light_id in layer.lights:
            layer.lights.remove(light_id)
            return True
        return False

    def set_ambient(
        self,
        layer_id: str,
        color: Tuple[float, float, float],
        intensity: float,
    ) -> None:
        layer = self._layers.get(layer_id)
        if layer is None:
            return
        layer.ambient_color = (
            max(0.0, min(1.0, color[0])),
            max(0.0, min(1.0, color[1])),
            max(0.0, min(1.0, color[2])),
        )
        layer.ambient_intensity = max(0.0, intensity)

    # ------------------------------------------------------------------
    # Shadow Casting
    # ------------------------------------------------------------------

    def register_shadow_caster(
        self,
        entity_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> ShadowCaster2D:
        if config is None:
            config = {}

        caster = ShadowCaster2D(
            entity_id=entity_id,
            cast_method=config.get("cast_method", "hard"),
            resolution=min(
                self.MAX_SHADOW_CASTER_RESOLUTION,
                max(16, config.get("resolution", 256)),
            ),
            softness=max(0.0, min(10.0, config.get("softness", 1.0))),
            self_shadow=config.get("self_shadow", True),
        )
        self._shadow_casters[caster.id] = caster
        return caster

    def unregister_shadow_caster(self, caster_id: str) -> bool:
        if caster_id not in self._shadow_casters:
            return False
        del self._shadow_casters[caster_id]
        return True

    def get_shadow_casters(self) -> List[ShadowCaster2D]:
        return list(self._shadow_casters.values())

    def get_shadow_casters_for_entity(self, entity_id: str) -> List[ShadowCaster2D]:
        return [
            c for c in self._shadow_casters.values()
            if c.entity_id == entity_id
        ]

    # ------------------------------------------------------------------
    # Lighting Calculation
    # ------------------------------------------------------------------

    def calculate_lighting(
        self,
        scene_bounds: Tuple[float, float, float, float],
        visible_entities: List[str],
    ) -> Dict[str, Any]:
        min_x, min_y, max_x, max_y = scene_bounds
        lit_entities: Dict[str, Dict[str, Any]] = {}
        total_samples = 0

        sorted_layers = sorted(
            self._layers.values(), key=lambda l: l.z_order
        )

        for entity_id in visible_entities:
            entity_result: Dict[str, Any] = {
                "entity_id": entity_id,
                "light_contributions": [],
                "final_color": [0.0, 0.0, 0.0],
                "illuminance": 0.0,
                "shadow_fraction": 0.0,
            }

            entity_pos = self._resolve_entity_position(entity_id)

            for layer in sorted_layers:
                if not layer.enabled:
                    continue

                r, g, b = layer.ambient_color
                amb_r = r * layer.ambient_intensity
                amb_g = g * layer.ambient_intensity
                amb_b = b * layer.ambient_intensity
                entity_result["final_color"][0] += amb_r
                entity_result["final_color"][1] += amb_g
                entity_result["final_color"][2] += amb_b

                lights_at_point: List[Tuple[float, float, float, float]] = []

                for light_id in layer.lights:
                    light = self._lights.get(light_id)
                    if light is None or not light.enabled:
                        continue
                    if not self._light_in_bounds(light, scene_bounds):
                        continue

                    contrib = self._compute_light_contribution(
                        light, entity_pos
                    )
                    if contrib is None:
                        continue

                    attenuated = contrib
                    if light.cast_shadows:
                        shadow = self._cast_shadows(
                            light, list(self._shadow_casters.values()), scene_bounds
                        )
                        shadow_factor = max(0.0, min(1.0, shadow))
                        attenuated = (
                            attenuated[0] * (1.0 - shadow_factor),
                            attenuated[1] * (1.0 - shadow_factor),
                            attenuated[2] * (1.0 - shadow_factor),
                            attenuated[3],
                        )
                        entity_result["shadow_fraction"] = max(
                            entity_result["shadow_fraction"], shadow_factor
                        )
                        self._total_shadows_cast += 1

                    lights_at_point.append(attenuated)
                    total_samples += 1

                if lights_at_point:
                    blended = self._blend_lights(
                        lights_at_point, layer.blend_mode
                    )
                    entity_result["light_contributions"].append({
                        "layer_id": layer.id,
                        "layer_name": layer.name,
                        "blend_mode": layer.blend_mode.value,
                        "color": list(blended),
                        "light_count": len(lights_at_point),
                    })
                    entity_result["final_color"][0] += blended[0]
                    entity_result["final_color"][1] += blended[1]
                    entity_result["final_color"][2] += blended[2]

            entity_result["final_color"] = [
                max(0.0, min(1.0, c)) for c in entity_result["final_color"]
            ]
            entity_result["illuminance"] = (
                entity_result["final_color"][0] * 0.2126
                + entity_result["final_color"][1] * 0.7152
                + entity_result["final_color"][2] * 0.0722
            )
            lit_entities[entity_id] = entity_result

        return {
            "scene_bounds": list(scene_bounds),
            "entities": lit_entities,
            "entity_count": len(lit_entities),
            "total_samples": total_samples,
            "active_layers": sum(1 for l in self._layers.values() if l.enabled),
            "compute_time_ms": 0.0,
        }

    def _compute_light_contribution(
        self,
        light: LightSource,
        position: Tuple[float, float],
    ) -> Optional[Tuple[float, float, float, float]]:
        dx = position[0] - light.position[0]
        dy = position[1] - light.position[1]
        distance = math.sqrt(dx * dx + dy * dy)

        if light.light_type == LightType.AMBIENT:
            return (
                light.color[0] * light.intensity,
                light.color[1] * light.intensity,
                light.color[2] * light.intensity,
                light.intensity,
            )

        if distance > light.radius:
            return None

        if light.light_type == LightType.DIRECTIONAL:
            attenuation = 1.0
        elif light.light_type == LightType.SPOT:
            angle = math.atan2(dy, dx)
            attenuation = self._compute_spot_light(light, position, angle)
        elif light.light_type == LightType.PULSATING:
            attenuation = self._compute_point_light(light, position, distance)
            if light.flicker_config:
                freq = light.flicker_config.get("frequency", 2.0)
                amp = light.flicker_config.get("amplitude", 0.3)
                phase = light.flicker_config.get("phase", 0.0)
                flicker = 1.0 + amp * math.sin(
                    time.time() * freq * 2.0 * math.pi + phase
                )
                attenuation *= flicker
        else:
            attenuation = self._compute_point_light(light, position, distance)

        return (
            light.color[0] * attenuation * light.intensity,
            light.color[1] * attenuation * light.intensity,
            light.color[2] * attenuation * light.intensity,
            attenuation * light.intensity,
        )

    # ------------------------------------------------------------------
    # Internal Lighting Computations
    # ------------------------------------------------------------------

    def _compute_point_light(
        self,
        light: LightSource,
        position: Tuple[float, float],
        distance: float,
    ) -> float:
        normalized = max(0.0, min(1.0, distance / max(light.radius, 0.001)))

        if light.falloff == LightFalloff.LINEAR:
            attenuation = 1.0 - normalized
        elif light.falloff == LightFalloff.SMOOTHSTEP:
            t = 1.0 - normalized
            attenuation = t * t * (3.0 - 2.0 * t)
        elif light.falloff == LightFalloff.CUSTOM_CURVE:
            points = light.flicker_config.get("falloff_curve", [])
            if len(points) < 2:
                attenuation = 1.0 / (1.0 + normalized * normalized * 2.0)
            else:
                attenuation = self._evaluate_curve(points, normalized)
        else:
            attenuation = 1.0 / (1.0 + normalized * normalized * 2.0)

        return max(0.0, attenuation)

    def _compute_spot_light(
        self,
        light: LightSource,
        position: Tuple[float, float],
        angle: float,
    ) -> float:
        dx = position[0] - light.position[0]
        dy = position[1] - light.position[1]
        distance = math.sqrt(dx * dx + dy * dy)

        base_attenuation = self._compute_point_light(light, position, distance)

        cone_angle = light.flicker_config.get("cone_angle", math.radians(45))
        cone_dir = light.flicker_config.get("cone_direction", -math.pi / 2)

        delta = angle - cone_dir
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            delta += 2.0 * math.pi

        half_cone = cone_angle / 2.0
        if abs(delta) > half_cone:
            return 0.0

        spot_factor = 1.0 - (abs(delta) / half_cone)
        return base_attenuation * spot_factor

    def _cast_shadows(
        self,
        light: LightSource,
        casters: List[ShadowCaster2D],
        scene_bounds: Tuple[float, float, float, float],
    ) -> float:
        ray_count = self.SHADOW_RAY_COUNT.get(
            light.shadow_quality.value, 64
        )
        if ray_count == 0:
            return 0.0

        hits = 0
        lx, ly = light.position
        min_x, min_y, max_x, max_y = scene_bounds

        for i in range(ray_count):
            angle = 2.0 * math.pi * i / ray_count
            ray_end_x = lx + math.cos(angle) * light.radius
            ray_end_y = ly + math.sin(angle) * light.radius

            for caster in casters:
                caster_center = self._resolve_entity_position(caster.entity_id)
                if caster_center is None:
                    continue

                cx, cy = caster_center
                dist_to_caster = math.sqrt(
                    (cx - lx) ** 2 + (cy - ly) ** 2
                )
                if dist_to_caster > light.radius:
                    continue

                ray_length = light.radius
                hit = self._ray_circle_intersection(
                    lx, ly, ray_end_x, ray_end_y,
                    cx, cy,
                    16.0 + caster.softness * 4.0,
                )
                if hit:
                    hits += 1
                    break

        return hits / max(ray_count, 1)

    @staticmethod
    def _ray_circle_intersection(
        ox: float, oy: float,
        ex: float, ey: float,
        cx: float, cy: float,
        radius: float,
    ) -> bool:
        dx = ex - ox
        dy = ey - oy
        fx = ox - cx
        fy = oy - cy

        a = dx * dx + dy * dy
        b = 2.0 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - radius * radius

        discriminant = b * b - 4.0 * a * c
        if discriminant < 0:
            return False

        discriminant = math.sqrt(discriminant)
        t1 = (-b - discriminant) / (2.0 * a)
        t2 = (-b + discriminant) / (2.0 * a)

        return (0.0 <= t1 <= 1.0) or (0.0 <= t2 <= 1.0)

    def _blend_lights(
        self,
        lights_at_point: List[Tuple[float, float, float, float]],
        blend_mode: BlendMode,
    ) -> Tuple[float, float, float]:
        if not lights_at_point:
            return (0.0, 0.0, 0.0)

        r = g = b = 0.0

        if blend_mode == BlendMode.ADDITIVE:
            for lr, lg, lb, _ in lights_at_point:
                r += lr
                g += lg
                b += lb
        elif blend_mode == BlendMode.MULTIPLY:
            r = g = b = 1.0
            for lr, lg, lb, _ in lights_at_point:
                r *= max(0.0, lr)
                g *= max(0.0, lg)
                b *= max(0.0, lb)
        elif blend_mode == BlendMode.SCREEN:
            r = g = b = 1.0
            for lr, lg, lb, _ in lights_at_point:
                r = 1.0 - (1.0 - r) * (1.0 - lr)
                g = 1.0 - (1.0 - g) * (1.0 - lg)
                b = 1.0 - (1.0 - b) * (1.0 - lb)
        elif blend_mode == BlendMode.OVERLAY:
            for lr, lg, lb, _ in lights_at_point:
                if lr < 0.5:
                    r += 2.0 * r * lr
                else:
                    r += 1.0 - 2.0 * (1.0 - r) * (1.0 - lr)
                if lg < 0.5:
                    g += 2.0 * g * lg
                else:
                    g += 1.0 - 2.0 * (1.0 - g) * (1.0 - lg)
                if lb < 0.5:
                    b += 2.0 * b * lb
                else:
                    b += 1.0 - 2.0 * (1.0 - b) * (1.0 - lb)
        elif blend_mode == BlendMode.SOFT_LIGHT:
            for lr, lg, lb, _ in lights_at_point:
                r += (1.0 - 2.0 * lr) * r * r + 2.0 * lr * r
                g += (1.0 - 2.0 * lg) * g * g + 2.0 * lg * g
                b += (1.0 - 2.0 * lb) * b * b + 2.0 * lb * b

        return (
            max(0.0, min(1.0, r)),
            max(0.0, min(1.0, g)),
            max(0.0, min(1.0, b)),
        )

    def _generate_light_map(
        self,
        layer: LightLayer,
        bounds: Tuple[float, float, float, float],
    ) -> Dict[str, Any]:
        min_x, min_y, max_x, max_y = bounds
        width = int(max_x - min_x)
        height = int(max_y - min_y)
        light_map: List[List[List[float]]] = []

        for y in range(min(64, height)):
            row: List[List[float]] = []
            for x in range(min(64, width)):
                px = min_x + (x / max(63, 1)) * (max_x - min_x)
                py = min_y + (y / max(63, 1)) * (max_y - min_y)
                sample: List[float] = [0.0, 0.0, 0.0]

                for light_id in layer.lights:
                    light = self._lights.get(light_id)
                    if light is None or not light.enabled:
                        continue
                    contrib = self._compute_light_contribution(
                        light, (px, py)
                    )
                    if contrib is not None:
                        sample[0] += contrib[0]
                        sample[1] += contrib[1]
                        sample[2] += contrib[2]

                sample = [
                    max(0.0, min(1.0, c)) for c in sample
                ]
                row.append(sample)
            light_map.append(row)

        return {
            "layer_id": layer.id,
            "bounds": list(bounds),
            "resolution": [len(light_map[0]) if light_map else 0, len(light_map)],
            "data": light_map,
        }

    # ------------------------------------------------------------------
    # Flicker and Animation
    # ------------------------------------------------------------------

    def set_flicker(
        self,
        light_id: str,
        frequency: float = 2.0,
        amplitude: float = 0.3,
    ) -> Optional[LightSource]:
        light = self._lights.get(light_id)
        if light is None:
            return None

        light.flicker_config = {
            "frequency": max(0.1, frequency),
            "amplitude": max(0.0, min(1.0, amplitude)),
            "phase": light.flicker_config.get("phase", 0.0),
        }
        return light

    # ------------------------------------------------------------------
    # Optimization and Baking
    # ------------------------------------------------------------------

    def optimize_lights(
        self,
        scene_bounds: Tuple[float, float, float, float],
    ) -> int:
        min_x, min_y, max_x, max_y = scene_bounds
        culled = 0

        for light in list(self._lights.values()):
            if not light.enabled:
                continue
            if not self._light_in_bounds(light, scene_bounds):
                continue

            lx, ly = light.position
            margin = light.radius * 0.2

            if lx + light.radius < min_x - margin:
                light.enabled = False
                culled += 1
            elif lx - light.radius > max_x + margin:
                light.enabled = False
                culled += 1
            elif ly + light.radius < min_y - margin:
                light.enabled = False
                culled += 1
            elif ly - light.radius > max_y + margin:
                light.enabled = False
                culled += 1

        merged = self._merge_overlapping_lights()
        self._total_optimizations += 1
        return culled + merged

    def bake_lighting(self, layer_id: str) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False

        bounds = (0.0, 0.0, 1024.0, 768.0)
        light_map = self._generate_light_map(layer, bounds)
        cache_key = f"baked_{layer_id}_{int(time.time())}"
        self._light_map_cache[cache_key] = light_map
        self._total_bakes += 1
        return True

    def get_baked_lighting(self, key: str) -> Optional[Dict[str, Any]]:
        return self._light_map_cache.get(key)

    def _merge_overlapping_lights(self) -> int:
        merged = 0
        lights_list = list(self._lights.values())
        n = len(lights_list)

        for i in range(n):
            if not lights_list[i].enabled:
                continue
            for j in range(i + 1, n):
                if not lights_list[j].enabled:
                    continue
                if lights_list[i].light_type != lights_list[j].light_type:
                    continue

                dx = lights_list[i].position[0] - lights_list[j].position[0]
                dy = lights_list[i].position[1] - lights_list[j].position[1]
                dist = math.sqrt(dx * dx + dy * dy)

                threshold = min(lights_list[i].radius, lights_list[j].radius) * 0.1
                if dist < threshold:
                    lights_list[j].enabled = False
                    lights_list[i].intensity = max(
                        lights_list[i].intensity, lights_list[j].intensity
                    )
                    lights_list[i].radius = max(
                        lights_list[i].radius, lights_list[j].radius
                    )
                    merged += 1

        return merged

    @staticmethod
    def _light_in_bounds(
        light: LightSource,
        bounds: Tuple[float, float, float, float],
    ) -> bool:
        min_x, min_y, max_x, max_y = bounds
        lx, ly = light.position
        return not (
            lx + light.radius < min_x
            or lx - light.radius > max_x
            or ly + light.radius < min_y
            or ly - light.radius > max_y
        )

    # ------------------------------------------------------------------
    # Entity Position Resolution
    # ------------------------------------------------------------------

    def _resolve_entity_position(
        self, entity_id: str
    ) -> Tuple[float, float]:
        caster = next(
            (c for c in self._shadow_casters.values()
             if c.entity_id == entity_id), None
        )
        if caster is not None:
            return self._entity_positions.get(entity_id, (0.0, 0.0))
        return self._entity_positions.get(entity_id, (0.0, 0.0))

    @staticmethod
    def _evaluate_curve(
        points: List[Tuple[float, float]],
        t: float,
    ) -> float:
        if len(points) < 2:
            return max(0.0, 1.0 - t)

        t = max(0.0, min(1.0, t))
        for i in range(len(points) - 1):
            t0, v0 = points[i]
            t1, v1 = points[i + 1]
            if t0 <= t <= t1:
                if t1 == t0:
                    return v0
                alpha = (t - t0) / (t1 - t0)
                return v0 + (v1 - v0) * alpha

        return points[-1][1] if t >= points[-1][0] else points[0][1]

    # ------------------------------------------------------------------
    # Toggle and Utility
    # ------------------------------------------------------------------

    def toggle_light(self, light_id: str, enabled: bool) -> None:
        light = self._lights.get(light_id)
        if light is not None:
            light.enabled = enabled

    def toggle_layer(self, layer_id: str, enabled: bool) -> None:
        layer = self._layers.get(layer_id)
        if layer is not None:
            layer.enabled = enabled

    def list_lights(self) -> List[LightSource]:
        return list(self._lights.values())

    def list_layers(self) -> List[LightLayer]:
        return list(self._layers.values())

    # ------------------------------------------------------------------
    # Config Management
    # ------------------------------------------------------------------

    def create_config(
        self,
        scene_id: str,
        max_lights: int = 128,
        default_ambient: Tuple[float, float, float] = (0.1, 0.1, 0.1),
        shadow_enabled: bool = True,
        tonemapping: str = "linear",
    ) -> LightingConfig:
        config = LightingConfig(
            scene_id=scene_id,
            max_lights=max(1, max_lights),
            default_ambient=(
                max(0.0, min(1.0, default_ambient[0])),
                max(0.0, min(1.0, default_ambient[1])),
                max(0.0, min(1.0, default_ambient[2])),
            ),
            shadow_enabled=shadow_enabled,
            tonemapping=tonemapping,
        )
        self._configs[config.id] = config
        return config

    def get_config(self, config_id: str) -> Optional[LightingConfig]:
        return self._configs.get(config_id)

    def get_config_for_scene(self, scene_id: str) -> Optional[LightingConfig]:
        for config in self._configs.values():
            if config.scene_id == scene_id:
                return config
        return None

    # ------------------------------------------------------------------
    # Entity Position Tracking
    # ------------------------------------------------------------------

    def set_entity_position(
        self, entity_id: str, position: Tuple[float, float]
    ) -> None:
        if not hasattr(self, "_entity_positions"):
            self._entity_positions: Dict[str, Tuple[float, float]] = {}
        self._entity_positions[entity_id] = (
            float(position[0]), float(position[1])
        )

    def get_entity_position(
        self, entity_id: str
    ) -> Optional[Tuple[float, float]]:
        if not hasattr(self, "_entity_positions"):
            self._entity_positions = {}
        return self._entity_positions.get(entity_id)

    # ------------------------------------------------------------------
    # Stats and Reset
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total_lights = len(self._lights)
        enabled_lights = sum(1 for l in self._lights.values() if l.enabled)
        total_layers = len(self._layers)
        enabled_layers = sum(1 for l in self._layers.values() if l.enabled)
        total_casters = len(self._shadow_casters)

        light_type_counts: Dict[str, int] = {}
        for light in self._lights.values():
            lt = light.light_type.value
            light_type_counts[lt] = light_type_counts.get(lt, 0) + 1

        avg_radius = 0.0
        avg_intensity = 0.0
        if total_lights > 0:
            avg_radius = sum(
                l.radius for l in self._lights.values()
            ) / total_lights
            avg_intensity = sum(
                l.intensity for l in self._lights.values()
            ) / total_lights

        return {
            "total_lights": total_lights,
            "enabled_lights": enabled_lights,
            "total_layers": total_layers,
            "enabled_layers": enabled_layers,
            "max_layers": self.MAX_LAYERS,
            "max_lights_per_layer": self.MAX_LIGHTS_PER_LAYER,
            "total_shadow_casters": total_casters,
            "total_lights_created": self._total_lights_created,
            "total_shadows_cast": self._total_shadows_cast,
            "total_bakes": self._total_bakes,
            "total_optimizations": self._total_optimizations,
            "light_type_distribution": light_type_counts,
            "average_radius": round(avg_radius, 1),
            "average_intensity": round(avg_intensity, 2),
            "configs_managed": len(self._configs),
            "cached_light_maps": len(self._light_map_cache),
        }

    def reset(self) -> None:
        with self._lock:
            self._lights.clear()
            self._layers.clear()
            self._shadow_casters.clear()
            self._configs.clear()
            self._light_map_cache.clear()
            if hasattr(self, "_entity_positions"):
                self._entity_positions.clear()
            self._total_lights_created = 0
            self._total_shadows_cast = 0
            self._total_bakes = 0
            self._total_optimizations = 0


def get_lighting_2d() -> Lighting2DEngine:
    """Return the global Lighting2DEngine singleton instance."""
    return Lighting2DEngine.get_instance()