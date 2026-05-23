"""
Shadow Casting System - Real-time 2D shadow projection and light occlusion for game rendering.

Architecture:
    ShadowCastingSystem/
    |-- LightType (point, directional, spot, ambient enumeration)
    |-- ShadowQuality (low, medium, high, ultra enumeration)
    |-- ShadowAlgorithm (ray_casting, shadow_map, projection enumeration)
    |-- ShadowLight (light source with shadow configuration)
    |-- Occluder (geometry that blocks light rays)
    |-- ShadowRegion (computed shadow area from light/occluder pair)
    |-- ShadowCastResult (aggregate shadow computation output)

Manages dynamic 2D shadows via ray casting from point lights against occluder
geometry. Computes shadow polygons, penumbra regions, and generates occlusion
maps for rendering. Supports multiple light types, quality presets, and
configurable shadow algorithms.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class LightType(Enum):
    POINT = "point"
    DIRECTIONAL = "directional"
    SPOT = "spot"
    AMBIENT = "ambient"


class ShadowQuality(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class ShadowAlgorithm(Enum):
    RAY_CASTING = "ray_casting"
    SHADOW_MAP = "shadow_map"
    PROJECTION = "projection"


@dataclass
class ShadowLight:
    """A light source capable of casting shadows in the 2D scene."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "ShadowLight"
    light_type: LightType = LightType.POINT
    position_x: float = 0.0
    position_y: float = 0.0
    intensity: float = 1.0
    color_r: int = 255
    color_g: int = 255
    color_b: int = 255
    radius: float = 200.0
    cast_shadows: bool = True
    shadow_resolution: int = 128
    shadow_softness: float = 0.5
    enabled: bool = True
    layer: int = 0
    inner_angle: float = 30.0
    outer_angle: float = 60.0
    direction_x: float = 0.0
    direction_y: float = -1.0

    @property
    def position(self) -> Tuple[float, float]:
        return (self.position_x, self.position_y)

    @property
    def color(self) -> Tuple[int, int, int]:
        return (self.color_r, self.color_g, self.color_b)

    def intensity_at_distance(self, distance: float) -> float:
        if distance >= self.radius:
            return 0.0
        ratio = distance / self.radius
        return self.intensity * max(0.0, 1.0 - ratio * ratio)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "light_type": self.light_type.value,
            "position": [self.position_x, self.position_y],
            "intensity": self.intensity,
            "color": [self.color_r, self.color_g, self.color_b],
            "radius": self.radius,
            "cast_shadows": self.cast_shadows,
            "shadow_resolution": self.shadow_resolution,
            "shadow_softness": self.shadow_softness,
            "enabled": self.enabled,
            "layer": self.layer,
            "inner_angle": self.inner_angle,
            "outer_angle": self.outer_angle,
            "direction": [self.direction_x, self.direction_y],
        }


@dataclass
class Occluder:
    """A 2D polygon that blocks light and casts shadows."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Occluder"
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    layer: int = 0
    enabled: bool = True
    opacity: float = 1.0
    height: float = 1.0
    cast_shadows: bool = True
    receive_shadows: bool = True
    bounding_radius: float = 0.0

    def __post_init__(self):
        self._recompute_bounds()

    def _recompute_bounds(self) -> None:
        if not self.vertices:
            self.bounding_radius = 0.0
            return
        cx = sum(v[0] for v in self.vertices) / len(self.vertices)
        cy = sum(v[1] for v in self.vertices) / len(self.vertices)
        max_dist = 0.0
        for vx, vy in self.vertices:
            dist = math.sqrt((vx - cx) ** 2 + (vy - cy) ** 2)
            if dist > max_dist:
                max_dist = dist
        self.bounding_radius = max_dist

    def get_edges(self) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        edges = []
        if len(self.vertices) < 2:
            return edges
        for i in range(len(self.vertices)):
            a = self.vertices[i]
            b = self.vertices[(i + 1) % len(self.vertices)]
            edges.append((a, b))
        return edges

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "vertex_count": len(self.vertices),
            "layer": self.layer,
            "enabled": self.enabled,
            "opacity": self.opacity,
            "height": self.height,
            "cast_shadows": self.cast_shadows,
            "receive_shadows": self.receive_shadows,
            "bounding_radius": self.bounding_radius,
        }


@dataclass
class ShadowRegion:
    """A region of shadow cast by an occluder from a specific light source."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    light_id: str = ""
    occluder_id: str = ""
    polygon: List[Tuple[float, float]] = field(default_factory=list)
    umbra_vertices: List[Tuple[float, float]] = field(default_factory=list)
    penumbra_vertices: List[Tuple[float, float]] = field(default_factory=list)
    opacity: float = 1.0
    depth: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "light_id": self.light_id,
            "occluder_id": self.occluder_id,
            "polygon_vertices": len(self.polygon),
            "umbra_vertices": len(self.umbra_vertices),
            "penumbra_vertices": len(self.penumbra_vertices),
            "opacity": self.opacity,
            "depth": self.depth,
        }


@dataclass
class ShadowCastResult:
    """Aggregate result of shadow computation for a single light source."""

    light_id: str = ""
    shadow_regions: List[ShadowRegion] = field(default_factory=list)
    occlusion_map: Dict[Tuple[int, int], float] = field(default_factory=dict)
    ray_count: int = 0
    computation_time_ms: float = 0.0
    total_shadow_area: float = 0.0
    occluders_processed: int = 0
    algorithm: ShadowAlgorithm = ShadowAlgorithm.RAY_CASTING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "light_id": self.light_id,
            "shadow_region_count": len(self.shadow_regions),
            "occlusion_map_cells": len(self.occlusion_map),
            "ray_count": self.ray_count,
            "computation_time_ms": self.computation_time_ms,
            "total_shadow_area": self.total_shadow_area,
            "occluders_processed": self.occluders_processed,
            "algorithm": self.algorithm.value,
        }


class ShadowCastingSystem:
    """
    Real-time 2D shadow casting system for dynamic lighting.

    Manages shadow-casting lights, occluder geometry, and computes
    shadow polygons using configurable ray-casting and shadow map
    algorithms. Supports multiple quality presets that control ray
    count and resolution.

    Usage:
        scs = get_shadow_casting()
        light = scs.add_light("torch", position=(100.0, 200.0))
        wall = scs.add_occluder("wall", vertices=[(0,0),(100,0),(100,10),(0,10)])
        result = scs.compute_shadows(light.id)
        for region in result.shadow_regions:
            render_shadow_polygon(region.polygon)
    """

    _instance: Optional["ShadowCastingSystem"] = None

    def __init__(self):
        self._lights: Dict[str, ShadowLight] = {}
        self._occluders: Dict[str, Occluder] = {}
        self._shadow_results: Dict[str, ShadowCastResult] = {}
        self._ambient_color: Tuple[int, int, int] = (40, 40, 40)
        self._ambient_intensity: float = 0.2
        self._quality: ShadowQuality = ShadowQuality.MEDIUM
        self._algorithm: ShadowAlgorithm = ShadowAlgorithm.RAY_CASTING
        self._enabled: bool = True
        self._update_count: int = 0

    @classmethod
    def get_instance(cls) -> "ShadowCastingSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Light management
    # ------------------------------------------------------------------

    def add_light(
        self,
        name: str,
        light_type: str = "point",
        position: Tuple[float, float] = (0.0, 0.0),
        intensity: float = 1.0,
        color: Tuple[int, int, int] = (255, 255, 255),
        radius: float = 200.0,
    ) -> ShadowLight:
        lt_map = {
            "point": LightType.POINT,
            "directional": LightType.DIRECTIONAL,
            "spot": LightType.SPOT,
            "ambient": LightType.AMBIENT,
        }
        resolved_type = lt_map.get(light_type.lower(), LightType.POINT)

        light = ShadowLight(
            name=name,
            light_type=resolved_type,
            position_x=position[0],
            position_y=position[1],
            intensity=max(0.0, intensity),
            color_r=min(255, max(0, color[0])),
            color_g=min(255, max(0, color[1])),
            color_b=min(255, max(0, color[2])),
            radius=max(1.0, radius),
        )
        self._lights[light.id] = light
        return light

    def remove_light(self, light_id: str) -> bool:
        if light_id in self._lights:
            del self._lights[light_id]
            self._shadow_results.pop(light_id, None)
            return True
        return False

    def get_light(self, light_id: str) -> Optional[ShadowLight]:
        return self._lights.get(light_id)

    def update_light_position(self, light_id: str, x: float, y: float) -> bool:
        light = self._lights.get(light_id)
        if light is None:
            return False
        light.position_x = x
        light.position_y = y
        return True

    def set_light_intensity(self, light_id: str, intensity: float) -> bool:
        light = self._lights.get(light_id)
        if light is None:
            return False
        light.intensity = max(0.0, intensity)
        return True

    def set_light_enabled(self, light_id: str, enabled: bool) -> bool:
        light = self._lights.get(light_id)
        if light is None:
            return False
        light.enabled = enabled
        return True

    def get_visible_lights(self) -> List[ShadowLight]:
        return [l for l in self._lights.values() if l.enabled]

    # ------------------------------------------------------------------
    # Occluder management
    # ------------------------------------------------------------------

    def add_occluder(
        self,
        name: str,
        vertices: List[Tuple[float, float]] = None,
        layer: int = 0,
    ) -> Occluder:
        if vertices is None:
            vertices = []
        occluder = Occluder(
            name=name,
            vertices=list(vertices),
            layer=max(0, layer),
        )
        self._occluders[occluder.id] = occluder
        return occluder

    def remove_occluder(self, occluder_id: str) -> bool:
        if occluder_id in self._occluders:
            del self._occluders[occluder_id]
            return True
        return False

    def get_occluder(self, occluder_id: str) -> Optional[Occluder]:
        return self._occluders.get(occluder_id)

    def set_occluder_vertices(
        self, occluder_id: str, vertices: List[Tuple[float, float]]
    ) -> bool:
        occluder = self._occluders.get(occluder_id)
        if occluder is None:
            return False
        occluder.vertices = list(vertices)
        occluder._recompute_bounds()
        return True

    def list_occluders(self, layer: Optional[int] = None) -> List[Occluder]:
        if layer is None:
            return list(self._occluders.values())
        return [o for o in self._occluders.values() if o.layer == layer]

    # ------------------------------------------------------------------
    # Shadow computation
    # ------------------------------------------------------------------

    def compute_shadows(self, light_id: str) -> ShadowCastResult:
        light = self._lights.get(light_id)
        result = ShadowCastResult(light_id=light_id, algorithm=self._algorithm)

        if light is None or not light.enabled or not light.cast_shadows:
            self._shadow_results[light_id] = result
            return result

        ray_count = self._get_quality_ray_count()
        result.ray_count = ray_count

        active_occluders = [
            o for o in self._occluders.values()
            if o.enabled and o.cast_shadows and len(o.vertices) >= 2
        ]

        result.occluders_processed = len(active_occluders)
        lx, ly = light.position_x, light.position_y

        for occluder in active_occluders:
            if not self._occluder_in_light_range(occluder, lx, ly, light.radius):
                continue

            edges = occluder.get_edges()
            shadow_region = self._compute_shadow_from_edges(
                light, occluder, edges, ray_count
            )
            if shadow_region is not None:
                result.shadow_regions.append(shadow_region)

        total_area = 0.0
        for region in result.shadow_regions:
            total_area += self._polygon_area(region.polygon)
        result.total_shadow_area = total_area

        result.occlusion_map = self._build_occlusion_map(result, light)
        self._shadow_results[light_id] = result
        return result

    def occlude_region(self, light_id: str, occluder_id: str) -> ShadowRegion:
        light = self._lights.get(light_id)
        occluder = self._occluders.get(occluder_id)

        region = ShadowRegion(
            light_id=light_id,
            occluder_id=occluder_id,
        )

        if light is None or occluder is None:
            return region

        if not occluder.enabled or not occluder.cast_shadows:
            return region

        lx, ly = light.position_x, light.position_y
        edges = occluder.get_edges()
        ray_count = self._get_quality_ray_count()

        computed = self._compute_shadow_from_edges(light, occluder, edges, ray_count)
        if computed is not None:
            region.polygon = computed.polygon
            region.umbra_vertices = computed.umbra_vertices
            region.penumbra_vertices = computed.penumbra_vertices
            region.opacity = occluder.opacity

        return region

    def get_occlusion_map(self, light_id: str) -> Dict:
        result = self._shadow_results.get(light_id)
        if result is None:
            return {}
        serializable = {}
        for (cx, cy), value in result.occlusion_map.items():
            serializable[f"{cx},{cy}"] = value
        return serializable

    # ------------------------------------------------------------------
    # Ambient light
    # ------------------------------------------------------------------

    def set_ambient_light(
        self,
        color: Tuple[int, int, int] = (40, 40, 40),
        intensity: float = 0.2,
    ) -> None:
        self._ambient_color = (
            min(255, max(0, color[0])),
            min(255, max(0, color[1])),
            min(255, max(0, color[2])),
        )
        self._ambient_intensity = max(0.0, min(1.0, intensity))

    # ------------------------------------------------------------------
    # Quality and algorithm
    # ------------------------------------------------------------------

    def set_shadow_quality(self, quality: str = "medium") -> None:
        q_map = {
            "low": ShadowQuality.LOW,
            "medium": ShadowQuality.MEDIUM,
            "high": ShadowQuality.HIGH,
            "ultra": ShadowQuality.ULTRA,
        }
        self._quality = q_map.get(quality.lower(), ShadowQuality.MEDIUM)

    def set_shadow_algorithm(self, algorithm: str = "ray_casting") -> None:
        a_map = {
            "ray_casting": ShadowAlgorithm.RAY_CASTING,
            "shadow_map": ShadowAlgorithm.SHADOW_MAP,
            "projection": ShadowAlgorithm.PROJECTION,
        }
        self._algorithm = a_map.get(algorithm.lower(), ShadowAlgorithm.RAY_CASTING)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    # ------------------------------------------------------------------
    # Stats and reset
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total_regions = sum(
            len(r.shadow_regions) for r in self._shadow_results.values()
        )
        return {
            "light_count": len(self._lights),
            "enabled_lights": sum(1 for l in self._lights.values() if l.enabled),
            "shadow_casting_lights": sum(
                1 for l in self._lights.values() if l.cast_shadows and l.enabled
            ),
            "occluder_count": len(self._occluders),
            "active_occluders": sum(1 for o in self._occluders.values() if o.enabled),
            "computed_light_results": len(self._shadow_results),
            "total_shadow_regions": total_regions,
            "quality": self._quality.value,
            "algorithm": self._algorithm.value,
            "ambient_intensity": self._ambient_intensity,
            "enabled": self._enabled,
            "update_count": self._update_count,
        }

    def reset(self) -> None:
        self._lights.clear()
        self._occluders.clear()
        self._shadow_results.clear()
        self._ambient_color = (40, 40, 40)
        self._ambient_intensity = 0.2
        self._quality = ShadowQuality.MEDIUM
        self._algorithm = ShadowAlgorithm.RAY_CASTING
        self._enabled = True
        self._update_count = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_quality_ray_count(self) -> int:
        """Return the number of rays to cast based on current quality setting."""
        mapping = {
            ShadowQuality.LOW: 64,
            ShadowQuality.MEDIUM: 128,
            ShadowQuality.HIGH: 256,
            ShadowQuality.ULTRA: 512,
        }
        return mapping.get(self._quality, 128)

    @staticmethod
    def _occluder_in_light_range(
        occluder: Occluder, lx: float, ly: float, light_radius: float
    ) -> bool:
        if not occluder.vertices:
            return False
        for vx, vy in occluder.vertices:
            dist = math.sqrt((vx - lx) ** 2 + (vy - ly) ** 2)
            if dist <= light_radius + occluder.bounding_radius:
                return True
        return False

    def _compute_shadow_from_edges(
        self,
        light: ShadowLight,
        occluder: Occluder,
        edges: List[Tuple[Tuple[float, float], Tuple[float, float]]],
        ray_count: int,
    ) -> Optional[ShadowRegion]:
        """Build a shadow polygon for a single occluder relative to a point light."""
        lx, ly = light.position_x, light.position_y
        shadow_vertices: List[Tuple[float, float]] = []
        umbra_vertices: List[Tuple[float, float]] = []
        penumbra_vertices: List[Tuple[float, float]] = []

        for edge_start, edge_end in edges:
            front_angle = math.atan2(edge_start[1] - ly, edge_start[0] - lx)
            back_angle = math.atan2(edge_end[1] - ly, edge_end[0] - lx)

            projection_distance = light.radius * 2.0

            umbra_vertices.append(edge_start)
            umbra_vertices.append(edge_end)

            front_proj_x = lx + math.cos(front_angle) * projection_distance
            front_proj_y = ly + math.sin(front_angle) * projection_distance
            back_proj_x = lx + math.cos(back_angle) * projection_distance
            back_proj_y = ly + math.sin(back_angle) * projection_distance

            shadow_vertices.append(edge_start)
            shadow_vertices.append((front_proj_x, front_proj_y))
            shadow_vertices.append((back_proj_x, back_proj_y))
            shadow_vertices.append(edge_end)

            soft_offset = light.shadow_softness * 10.0
            penumbra_start_a = (
                front_proj_x + math.cos(front_angle + 0.05) * soft_offset,
                front_proj_y + math.sin(front_angle + 0.05) * soft_offset,
            )
            penumbra_start_b = (
                back_proj_x + math.cos(back_angle - 0.05) * soft_offset,
                back_proj_y + math.sin(back_angle - 0.05) * soft_offset,
            )
            penumbra_vertices.append(penumbra_start_a)
            penumbra_vertices.append(penumbra_start_b)

        return ShadowRegion(
            light_id=light.id,
            occluder_id=occluder.id,
            polygon=shadow_vertices,
            umbra_vertices=umbra_vertices,
            penumbra_vertices=penumbra_vertices,
            opacity=occluder.opacity,
            depth=0.0,
        )

    def _build_occlusion_map(
        self, result: ShadowCastResult, light: ShadowLight
    ) -> Dict[Tuple[int, int], float]:
        """Generate a coarse grid occlusion map for the light's influence area."""
        occlusion_map: Dict[Tuple[int, int], float] = {}
        resolution = light.shadow_resolution
        if resolution <= 0:
            return occlusion_map

        cell_size = (light.radius * 2.0) / resolution
        lx, ly = light.position_x, light.position_y
        half_res = resolution // 2

        for gx in range(-half_res, half_res):
            for gy in range(-half_res, half_res):
                cx = lx + gx * cell_size + cell_size / 2
                cy = ly + gy * cell_size + cell_size / 2
                occlusion = self._sample_occlusion_at(cx, cy, result.shadow_regions)
                if occlusion > 0.0:
                    occlusion_map[(gx, gy)] = occlusion

        return occlusion_map

    @staticmethod
    def _sample_occlusion_at(
        px: float,
        py: float,
        shadow_regions: List[ShadowRegion],
    ) -> float:
        """Check whether a point falls inside any shadow region polygon."""
        for region in shadow_regions:
            if len(region.polygon) < 6:
                continue
            if ShadowCastingSystem._point_in_polygon(px, py, region.polygon):
                return region.opacity
        return 0.0

    @staticmethod
    def _point_in_polygon(
        px: float, py: float, polygon: List[Tuple[float, float]]
    ) -> bool:
        """Ray-casting point-in-polygon test."""
        inside = False
        n = len(polygon)
        if n < 3:
            return False
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > py) != (yj > py)) and (
                px < (xj - xi) * (py - yi) / (yj - yi) + xi
            ):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _polygon_area(polygon: List[Tuple[float, float]]) -> float:
        """Compute the signed area of a polygon using the shoelace formula."""
        n = len(polygon)
        if n < 3:
            return 0.0
        area = 0.0
        j = n - 1
        for i in range(n):
            area += (polygon[j][0] + polygon[i][0]) * (polygon[j][1] - polygon[i][1])
            j = i
        return abs(area) / 2.0


def get_shadow_casting() -> ShadowCastingSystem:
    """Return the global ShadowCastingSystem singleton instance."""
    return ShadowCastingSystem.get_instance()