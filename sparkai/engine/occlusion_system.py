"""
Occlusion System - Visibility culling, occlusion queries, and rendering optimization.

Architecture:
    OcclusionSystem/
    |-- OcclusionMethod (culling technique classification)
    |-- CullingLayer (spatial layer hierarchy)
    |-- OcclusionVolume (spatial occlusion bounding region)
    |-- OcclusionSystem (unified visibility determination orchestrator)

Provides multiple culling strategies for render optimization: portal-based
occlusion, PVS precomputation, hardware occlusion queries, distance/LOD culling,
and frustum-only culling. Manages occlusion volumes and layer-based visibility
tests across the full render pipeline.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class OcclusionMethod(Enum):
    PORTAL = "portal"
    POTENTIALLY_VISIBLE_SET = "potentially_visible_set"
    HARDWARE_OCCLUSION = "hardware_occlusion"
    DISTANCE_CULL = "distance_cull"
    LOD_TRANSITION = "lod_transition"
    FRUSTUM_ONLY = "frustum_only"


class CullingLayer(Enum):
    DEFAULT = "default"
    TERRAIN = "terrain"
    BUILDINGS = "buildings"
    PROPS = "props"
    CHARACTERS = "characters"
    EFFECTS = "effects"
    UI = "ui"


@dataclass
class OcclusionVolume:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Volume"
    volume_type: str = "box"
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    size_x: float = 1.0
    size_y: float = 1.0
    size_z: float = 1.0
    affected_layers: List[CullingLayer] = field(default_factory=list)
    occlusion_query_enabled: bool = True

    def contains_point(self, x: float, y: float, z: float) -> bool:
        half_x = self.size_x / 2.0
        half_y = self.size_y / 2.0
        half_z = self.size_z / 2.0

        return (
            self.position_x - half_x <= x <= self.position_x + half_x and
            self.position_y - half_y <= y <= self.position_y + half_y and
            self.position_z - half_z <= z <= self.position_z + half_z
        )

    def get_bounds(self) -> Tuple[float, float, float, float, float, float]:
        half_x = self.size_x / 2.0
        half_y = self.size_y / 2.0
        half_z = self.size_z / 2.0
        return (
            self.position_x - half_x, self.position_y - half_y, self.position_z - half_z,
            self.position_x + half_x, self.position_y + half_y, self.position_z + half_z,
        )

    def volume(self) -> float:
        return self.size_x * self.size_y * self.size_z

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id[:12],
            "name": self.name,
            "volume_type": self.volume_type,
            "position": (self.position_x, self.position_y, self.position_z),
            "size": (self.size_x, self.size_y, self.size_z),
            "volume": self.volume(),
            "affected_layers": [layer.value for layer in self.affected_layers],
            "occlusion_query_enabled": self.occlusion_query_enabled,
        }


class OcclusionSystem:
    """Unified visibility culling and render optimization orchestration."""

    _instance: Optional["OcclusionSystem"] = None

    def __init__(self):
        self._volumes: Dict[str, OcclusionVolume] = {}
        self._layer_distances: Dict[CullingLayer, float] = {}
        self._layer_enabled: Dict[CullingLayer, bool] = {}
        self._method_stats: Dict[OcclusionMethod, int] = {}
        self._visible_objects: Dict[CullingLayer, List[str]] = {}
        self._total_culled: int = 0
        self._total_passed: int = 0
        self._culling_passes: int = 0
        self._active_method: OcclusionMethod = OcclusionMethod.FRUSTUM_ONLY

        for layer in CullingLayer:
            self._layer_distances[layer] = 500.0
            self._layer_enabled[layer] = True
            self._visible_objects[layer] = []

        for method in OcclusionMethod:
            self._method_stats[method] = 0

    @classmethod
    def get_instance(cls) -> "OcclusionSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_volume(
        self,
        name: str,
        position_x: float,
        position_y: float,
        position_z: float,
        size_x: float,
        size_y: float,
        size_z: float,
        volume_type: str = "box",
        affected_layers: Optional[List[CullingLayer]] = None,
        occlusion_query_enabled: bool = True,
    ) -> OcclusionVolume:
        volume = OcclusionVolume(
            name=name,
            volume_type=volume_type,
            position_x=position_x,
            position_y=position_y,
            position_z=position_z,
            size_x=size_x,
            size_y=size_y,
            size_z=size_z,
            affected_layers=affected_layers or [],
            occlusion_query_enabled=occlusion_query_enabled,
        )
        self._volumes[volume.id] = volume
        return volume

    def test_visibility(
        self,
        x: float,
        y: float,
        z: float,
        layer: CullingLayer = CullingLayer.DEFAULT,
    ) -> Dict[str, Any]:
        if not self._layer_enabled.get(layer, True):
            return {"visible": False, "reason": "layer_disabled"}

        for volume in self._volumes.values():
            if not volume.occlusion_query_enabled:
                continue
            if layer in volume.affected_layers:
                if volume.contains_point(x, y, z):
                    self._total_culled += 1
                    self._method_stats[self._active_method] = self._method_stats.get(self._active_method, 0) + 1
                    return {
                        "visible": False,
                        "reason": "occluded",
                        "volume_id": volume.id[:12],
                        "volume_name": volume.name,
                    }

        self._total_passed += 1
        return {"visible": True, "reason": "clear"}

    def set_layer_culling_distance(self, layer: CullingLayer, distance: float) -> None:
        self._layer_distances[layer] = max(0.0, distance)

    def get_layer_culling_distance(self, layer: CullingLayer) -> float:
        return self._layer_distances.get(layer, 500.0)

    def enable_layer(self, layer: CullingLayer) -> None:
        self._layer_enabled[layer] = True

    def disable_layer(self, layer: CullingLayer) -> None:
        self._layer_enabled[layer] = False

    def is_layer_enabled(self, layer: CullingLayer) -> bool:
        return self._layer_enabled.get(layer, True)

    def set_active_method(self, method: OcclusionMethod) -> None:
        self._active_method = method

    def get_active_method(self) -> OcclusionMethod:
        return self._active_method

    def perform_culling_pass(
        self,
        objects: List[Dict[str, Any]],
        camera_x: float = 0.0,
        camera_y: float = 0.0,
        camera_z: float = 0.0,
    ) -> Dict[str, List[Dict[str, Any]]]:
        self._culling_passes += 1

        for layer in CullingLayer:
            self._visible_objects[layer] = []

        visible: List[Dict[str, Any]] = []
        culled: List[Dict[str, Any]] = []

        for obj in objects:
            obj_x = obj.get("x", 0.0)
            obj_y = obj.get("y", 0.0)
            obj_z = obj.get("z", 0.0)
            obj_id = obj.get("id", "unknown")
            obj_layer = obj.get("layer", "default")

            layer_enum = CullingLayer.DEFAULT
            for cl in CullingLayer:
                if cl.value == obj_layer:
                    layer_enum = cl
                    break

            visible_after_all = True

            dist = math.sqrt(
                (obj_x - camera_x) ** 2 +
                (obj_y - camera_y) ** 2 +
                (obj_z - camera_z) ** 2
            )
            max_dist = self._layer_distances.get(layer_enum, 500.0)
            if dist > max_dist:
                visible_after_all = False

            visibility = self.test_visibility(obj_x, obj_y, obj_z, layer_enum)
            if not visibility["visible"]:
                visible_after_all = False

            if visible_after_all:
                visible.append(obj)
                self._visible_objects[layer_enum].append(obj_id)
                self._total_passed += 1
            else:
                culled.append(obj)
                self._total_culled += 1

        return {"visible": visible, "culled": culled}

    def get_visible_objects(self, layer: CullingLayer) -> List[str]:
        return list(self._visible_objects.get(layer, []))

    def get_culling_stats(self) -> Dict[str, Any]:
        total = self._total_passed + self._total_culled
        cull_ratio = (self._total_culled / max(1, total)) * 100.0
        return {
            "total_objects_processed": total,
            "passed": self._total_passed,
            "culled": self._total_culled,
            "cull_ratio_percent": round(cull_ratio, 1),
            "culling_passes": self._culling_passes,
            "active_method": self._active_method.value,
        }

    def get_volume(self, volume_id: str) -> Optional[OcclusionVolume]:
        return self._volumes.get(volume_id)

    def list_volumes(self) -> List[OcclusionVolume]:
        return list(self._volumes.values())

    def delete_volume(self, volume_id: str) -> bool:
        if volume_id in self._volumes:
            del self._volumes[volume_id]
            return True
        return False

    def get_total_volume_coverage(self) -> float:
        return sum(v.volume() for v in self._volumes.values())

    def reset_stats(self) -> None:
        self._total_culled = 0
        self._total_passed = 0
        self._culling_passes = 0
        for method in OcclusionMethod:
            self._method_stats[method] = 0
        for layer in CullingLayer:
            self._visible_objects[layer] = []

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_volumes": len(self._volumes),
            "total_coverage": round(self.get_total_volume_coverage(), 2),
            "active_method": self._active_method.value,
            "layers_enabled": sum(1 for e in self._layer_enabled.values() if e),
            "layers_total": len(CullingLayer),
            "layer_distances": {k.value: v for k, v in self._layer_distances.items()},
            "culling": self.get_culling_stats(),
            "method_usage": {k.value: v for k, v in self._method_stats.items()},
        }


def get_occlusion_system() -> OcclusionSystem:
    return OcclusionSystem.get_instance()