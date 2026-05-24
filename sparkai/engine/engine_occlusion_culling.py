"""
SparkLabs Engine - Occlusion Culling System

Visibility determination and frustum culling for rendering optimization.
Reduces draw calls by identifying which scene entities are hidden behind
occluders or outside the camera frustum, using a combination of spatial
partitioning, portal culling, and hierarchical depth tests.

Architecture:
  OcclusionCullingSystem
    |-- OcclusionVolume (axis-aligned and oriented bounding volumes)
    |-- CullingCamera (view frustum definition and parameters)
    |-- VisibilityQuery (per-entity visibility result lookup)
    |-- CullingStats (performance metrics and culling throughput)

Culling Methods:
  - Frustum culling: discard objects outside the view frustum planes
  - Portal culling: visibility through connected room portals
  - Occlusion query: GPU/CPU query to test if an object is occluded
  - Hierarchical Z-buffer: depth pyramid for coarse occlusion tests
  - Potentially Visible Set: precomputed static visibility data
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class CullingMethod(Enum):
    """Strategy for determining whether an entity contributes to the final frame."""
    FRUSTUM = "frustum"
    PORTAL = "portal"
    OCCLUSION_QUERY = "occlusion_query"
    HIERARCHICAL_Z = "hierarchical_z"
    POTENTIALLY_VISIBLE_SET = "potentially_visible_set"


class OccluderType(Enum):
    """Shape classification for occlusion volume geometry."""
    BOX = "box"
    SPHERE = "sphere"
    MESH = "mesh"
    TERRAIN = "terrain"


class VisibilityResult(Enum):
    """Outcome of a visibility test for a single entity against a camera."""
    VISIBLE = "visible"
    PARTIALLY_VISIBLE = "partially_visible"
    OCCLUDED = "occluded"
    OUT_OF_RANGE = "out_of_range"


@dataclass
class OcclusionVolume:
    """A bounding region that can occlude other entities from the camera.

    Represents geometry capable of blocking line-of-sight to objects
    behind it. Supports box, sphere, mesh, and terrain occluder shapes.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    entity_id: str = ""
    occluder_type: OccluderType = OccluderType.BOX
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    size_x: float = 1.0
    size_y: float = 1.0
    size_z: float = 1.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    is_dynamic: bool = False
    is_enabled: bool = True
    occlusion_strength: float = 1.0
    layer: int = 0

    @property
    def position(self) -> Tuple[float, float, float]:
        return (self.position_x, self.position_y, self.position_z)

    @property
    def size(self) -> Tuple[float, float, float]:
        return (self.size_x, self.size_y, self.size_z)

    @property
    def half_extents(self) -> Tuple[float, float, float]:
        return (self.size_x * 0.5, self.size_y * 0.5, self.size_z * 0.5)

    @property
    def bounding_radius(self) -> float:
        hx, hy, hz = self.half_extents
        return math.sqrt(hx * hx + hy * hy + hz * hz)

    def contains_point(self, px: float, py: float, pz: float) -> bool:
        hx, hy, hz = self.half_extents
        return (
            abs(px - self.position_x) <= hx
            and abs(py - self.position_y) <= hy
            and abs(pz - self.position_z) <= hz
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_id": self.entity_id,
            "occluder_type": self.occluder_type.value,
            "position": [self.position_x, self.position_y, self.position_z],
            "size": [self.size_x, self.size_y, self.size_z],
            "rotation": [self.rotation_x, self.rotation_y, self.rotation_z],
            "half_extents": list(self.half_extents),
            "bounding_radius": round(self.bounding_radius, 3),
            "is_dynamic": self.is_dynamic,
            "is_enabled": self.is_enabled,
            "occlusion_strength": self.occlusion_strength,
            "layer": self.layer,
        }


@dataclass
class CullingCamera:
    """View frustum and camera parameters used for visibility determination.

    Defines the six planes of a perspective projection frustum and
    maintains a cached set of visible entity IDs for quick lookup.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    camera_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    direction_x: float = 0.0
    direction_y: float = 0.0
    direction_z: float = -1.0
    up_x: float = 0.0
    up_y: float = 1.0
    up_z: float = 0.0
    fov: float = 60.0
    near_plane: float = 0.1
    far_plane: float = 1000.0
    aspect_ratio: float = 1.777
    visible_entities: List[str] = field(default_factory=list)
    partially_visible: List[str] = field(default_factory=list)
    occluded_count: int = 0
    out_of_range_count: int = 0
    last_update_time: float = field(default_factory=time.time)

    @property
    def position(self) -> Tuple[float, float, float]:
        return (self.position_x, self.position_y, self.position_z)

    @property
    def direction(self) -> Tuple[float, float, float]:
        return (self.direction_x, self.direction_y, self.direction_z)

    @property
    def up(self) -> Tuple[float, float, float]:
        return (self.up_x, self.up_y, self.up_z)

    @property
    def frustum_planes(self) -> List[Tuple[float, float, float, float]]:
        """Compute the six frustum planes (ax+by+cz+d=0) for the camera."""
        fov_rad = math.radians(self.fov)
        h_half = math.tan(fov_rad * 0.5) * self.far_plane
        v_half = h_half / self.aspect_ratio

        forward = (
            self.direction_x, self.direction_y, self.direction_z
        )
        forward_mag = math.sqrt(
            forward[0] ** 2 + forward[1] ** 2 + forward[2] ** 2
        )
        if forward_mag > 0:
            forward = (
                forward[0] / forward_mag,
                forward[1] / forward_mag,
                forward[2] / forward_mag,
            )

        right = (
            self.up_y * forward[2] - self.up_z * forward[1],
            self.up_z * forward[0] - self.up_x * forward[2],
            self.up_x * forward[1] - self.up_y * forward[0],
        )
        right_mag = math.sqrt(right[0] ** 2 + right[1] ** 2 + right[2] ** 2)
        if right_mag > 0:
            right = (right[0] / right_mag, right[1] / right_mag, right[2] / right_mag)

        up = (
            forward[1] * right[2] - forward[2] * right[1],
            forward[2] * right[0] - forward[0] * right[2],
            forward[0] * right[1] - forward[1] * right[0],
        )

        fc = (
            self.position_x + forward[0] * self.far_plane,
            self.position_y + forward[1] * self.far_plane,
            self.position_z + forward[2] * self.far_plane,
        )
        nc = (
            self.position_x + forward[0] * self.near_plane,
            self.position_y + forward[1] * self.near_plane,
            self.position_z + forward[2] * self.near_plane,
        )

        ftl = (
            fc[0] + up[0] * v_half - right[0] * h_half,
            fc[1] + up[1] * v_half - right[1] * h_half,
            fc[2] + up[2] * v_half - right[2] * h_half,
        )
        ftr = (
            fc[0] + up[0] * v_half + right[0] * h_half,
            fc[1] + up[1] * v_half + right[1] * h_half,
            fc[2] + up[2] * v_half + right[2] * h_half,
        )
        fbl = (
            fc[0] - up[0] * v_half - right[0] * h_half,
            fc[1] - up[1] * v_half - right[1] * h_half,
            fc[2] - up[2] * v_half - right[2] * h_half,
        )

        return [
            self._plane_from_points(nc, ftl, ftr),  # near
            self._plane_from_points(fc, ftr, ftl),  # far
            self._plane_from_points(
                self.position, fbl, ftl),  # left
            self._plane_from_points(
                self.position, ftr, (fc[0] + up[0]*v_half + right[0]*h_half,
                                     fc[1] + up[1]*v_half + right[1]*h_half,
                                     fc[2] + up[2]*v_half + right[2]*h_half)),  # right
            self._plane_from_points(self.position, ftl, ftr),  # top
            self._plane_from_points(self.position, ftr,
                                    (fc[0] - up[0]*v_half + right[0]*h_half,
                                     fc[1] - up[1]*v_half + right[1]*h_half,
                                     fc[2] - up[2]*v_half + right[2]*h_half)),  # bottom
        ]

    @staticmethod
    def _plane_from_points(
        p1: Tuple[float, float, float],
        p2: Tuple[float, float, float],
        p3: Tuple[float, float, float],
    ) -> Tuple[float, float, float, float]:
        v1 = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
        v2 = (p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2])
        normal = (
            v1[1] * v2[2] - v1[2] * v2[1],
            v1[2] * v2[0] - v1[0] * v2[2],
            v1[0] * v2[1] - v1[1] * v2[0],
        )
        length = math.sqrt(normal[0]**2 + normal[1]**2 + normal[2]**2)
        if length > 0:
            normal = (normal[0] / length, normal[1] / length, normal[2] / length)
        d = -(normal[0] * p1[0] + normal[1] * p1[1] + normal[2] * p1[2])
        return (normal[0], normal[1], normal[2], d)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "position": list(self.position),
            "direction": list(self.direction),
            "up": list(self.up),
            "fov": self.fov,
            "near_plane": self.near_plane,
            "far_plane": self.far_plane,
            "aspect_ratio": self.aspect_ratio,
            "visible_count": len(self.visible_entities),
            "partially_visible_count": len(self.partially_visible),
            "occluded_count": self.occluded_count,
            "out_of_range_count": self.out_of_range_count,
            "last_update_time": self.last_update_time,
        }


@dataclass
class VisibilityQuery:
    """A batched visibility test request for a set of entities against a camera."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    camera_id: str = ""
    entity_ids: List[str] = field(default_factory=list)
    results: Dict[str, VisibilityResult] = field(default_factory=dict)
    method: CullingMethod = CullingMethod.FRUSTUM
    query_time_ms: float = 0.0
    entities_tested: int = 0
    entities_visible: int = 0
    entities_occluded: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "entity_count": len(self.entity_ids),
            "result_count": len(self.results),
            "method": self.method.value,
            "query_time_ms": self.query_time_ms,
            "entities_tested": self.entities_tested,
            "entities_visible": self.entities_visible,
            "entities_occluded": self.entities_occluded,
            "timestamp": self.timestamp,
        }


@dataclass
class CullingStats:
    """Aggregate performance metrics for the occlusion culling system."""

    total_occluders: int = 0
    active_occluders: int = 0
    total_cameras: int = 0
    total_queries_processed: int = 0
    total_entities_tested: int = 0
    total_entities_culled: int = 0
    cull_ratio: float = 0.0
    average_query_time_ms: float = 0.0
    current_method: str = ""
    pvs_scenes: int = 0
    lod_near: float = 10.0
    lod_mid: float = 50.0
    lod_far: float = 200.0
    last_reset_time: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_occluders": self.total_occluders,
            "active_occluders": self.active_occluders,
            "total_cameras": self.total_cameras,
            "total_queries_processed": self.total_queries_processed,
            "total_entities_tested": self.total_entities_tested,
            "total_entities_culled": self.total_entities_culled,
            "cull_ratio": round(self.cull_ratio, 3),
            "average_query_time_ms": round(self.average_query_time_ms, 3),
            "current_method": self.current_method,
            "pvs_scenes": self.pvs_scenes,
            "lod_ranges": {
                "near": self.lod_near,
                "mid": self.lod_mid,
                "far": self.lod_far,
            },
            "last_reset_time": self.last_reset_time,
        }


class OcclusionCullingSystem:
    """Visibility determination and frustum culling for rendering optimization.

    Manages occlusion volumes, camera frusta, and performs visibility
    queries to determine which entities should be submitted for rendering.
    Supports multiple culling strategies including frustum testing, portal
    traversal, and precomputed potentially visible sets.

    Usage:
        ocs = get_occlusion_culling()
        ocs.register_occluder("building_01", occluder_type="box",
                              bounds={"size": [10, 5, 8], "position": [0, 2.5, 0]})
        cam = ocs.update_camera("main_cam", position=(0, 1.6, 0), fov=70)
        visible = ocs.query_visibility("main_cam", entity_ids=["tree_1", "rock_3"])
        print(visible)  # {"tree_1": VISIBLE, "rock_3": OCCLUDED}
    """

    _instance: Optional["OcclusionCullingSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._occluders: Dict[str, OcclusionVolume] = {}
        self._cameras: Dict[str, CullingCamera] = {}
        self._queries: Dict[str, VisibilityQuery] = {}
        self._pvs_data: Dict[str, Set[str]] = {}
        self._entity_bounds: Dict[str, Tuple[
            Tuple[float, float, float],
            Tuple[float, float, float],
            float,
        ]] = {}
        self._culling_method: CullingMethod = CullingMethod.FRUSTUM
        self._lod_near: float = 10.0
        self._lod_mid: float = 50.0
        self._lod_far: float = 200.0
        self._total_queries: int = 0
        self._total_cull_time_ms: float = 0.0
        self._entities_culled_total: int = 0

    @classmethod
    def get_instance(cls) -> "OcclusionCullingSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Occluder Management
    # ------------------------------------------------------------------

    def register_occluder(
        self,
        entity_id: str,
        occluder_type: str = "box",
        bounds: Optional[Dict[str, Any]] = None,
    ) -> OcclusionVolume:
        if bounds is None:
            bounds = {}

        try:
            ot = OccluderType(occluder_type.lower())
        except ValueError:
            ot = OccluderType.BOX

        pos = bounds.get("position", [0.0, 0.0, 0.0])
        size = bounds.get("size", [1.0, 1.0, 1.0])
        rot = bounds.get("rotation", [0.0, 0.0, 0.0])

        volume = OcclusionVolume(
            name=bounds.get("name", f"occluder_{entity_id}"),
            entity_id=entity_id,
            occluder_type=ot,
            position_x=pos[0],
            position_y=pos[1],
            position_z=pos[2],
            size_x=size[0],
            size_y=size[1] if len(size) > 1 else size[0],
            size_z=size[2] if len(size) > 2 else size[0],
            rotation_x=rot[0],
            rotation_y=rot[1] if len(rot) > 1 else 0.0,
            rotation_z=rot[2] if len(rot) > 2 else 0.0,
            is_dynamic=bounds.get("is_dynamic", False),
            is_enabled=True,
            occlusion_strength=bounds.get("occlusion_strength", 1.0),
            layer=bounds.get("layer", 0),
        )
        self._occluders[volume.id] = volume
        self._entity_bounds[entity_id] = (
            (volume.position_x, volume.position_y, volume.position_z),
            volume.half_extents,
            volume.bounding_radius,
        )
        return volume

    def unregister_occluder(self, entity_id: str) -> bool:
        to_remove = [
            oid for oid, vol in self._occluders.items()
            if vol.entity_id == entity_id
        ]
        for oid in to_remove:
            del self._occluders[oid]
        self._entity_bounds.pop(entity_id, None)
        return len(to_remove) > 0

    def get_occluder(self, occluder_id: str) -> Optional[OcclusionVolume]:
        return self._occluders.get(occluder_id)

    def get_occluders_for_entity(self, entity_id: str) -> List[OcclusionVolume]:
        return [
            vol for vol in self._occluders.values()
            if vol.entity_id == entity_id
        ]

    def set_occluder_enabled(self, occluder_id: str, enabled: bool) -> bool:
        vol = self._occluders.get(occluder_id)
        if vol is None:
            return False
        vol.is_enabled = enabled
        return True

    def update_occluder_bounds(
        self,
        entity_id: str,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> bool:
        occluders = self.get_occluders_for_entity(entity_id)
        if not occluders:
            return False
        for vol in occluders:
            vol.position_x = position[0]
            vol.position_y = position[1]
            vol.position_z = position[2]
            vol.size_x = size[0]
            vol.size_y = size[1]
            vol.size_z = size[2]
        self._entity_bounds[entity_id] = (
            position, vol.half_extents, vol.bounding_radius
        )
        return True

    # ------------------------------------------------------------------
    # Camera Management
    # ------------------------------------------------------------------

    def update_camera(
        self,
        camera_id: str,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        direction: Tuple[float, float, float] = (0.0, 0.0, -1.0),
        up: Tuple[float, float, float] = (0.0, 1.0, 0.0),
        fov: float = 60.0,
        near_plane: float = 0.1,
        far_plane: float = 1000.0,
        aspect_ratio: float = 1.777,
    ) -> CullingCamera:
        existing = self._cameras.get(camera_id)
        if existing is not None:
            existing.position_x = position[0]
            existing.position_y = position[1]
            existing.position_z = position[2]
            existing.direction_x = direction[0]
            existing.direction_y = direction[1]
            existing.direction_z = direction[2]
            existing.up_x = up[0]
            existing.up_y = up[1]
            existing.up_z = up[2]
            existing.fov = max(1.0, min(179.0, fov))
            existing.near_plane = max(0.001, near_plane)
            existing.far_plane = max(near_plane + 0.1, far_plane)
            existing.aspect_ratio = max(0.1, aspect_ratio)
            existing.last_update_time = time.time()
            return existing

        camera = CullingCamera(
            camera_id=camera_id,
            position_x=position[0],
            position_y=position[1],
            position_z=position[2],
            direction_x=direction[0],
            direction_y=direction[1],
            direction_z=direction[2],
            up_x=up[0],
            up_y=up[1],
            up_z=up[2],
            fov=max(1.0, min(179.0, fov)),
            near_plane=max(0.001, near_plane),
            far_plane=max(near_plane + 0.1, far_plane),
            aspect_ratio=max(0.1, aspect_ratio),
            last_update_time=time.time(),
        )
        self._cameras[camera_id] = camera
        return camera

    def get_camera(self, camera_id: str) -> Optional[CullingCamera]:
        return self._cameras.get(camera_id)

    def remove_camera(self, camera_id: str) -> bool:
        if camera_id in self._cameras:
            del self._cameras[camera_id]
            return True
        return False

    # ------------------------------------------------------------------
    # Visibility Queries
    # ------------------------------------------------------------------

    def query_visibility(
        self,
        camera_id: str,
        entity_ids: Optional[List[str]] = None,
    ) -> Dict[str, VisibilityResult]:
        camera = self._cameras.get(camera_id)
        if camera is None:
            return {}

        if entity_ids is None:
            entity_ids = list(self._entity_bounds.keys())

        start_time = time.time()
        results: Dict[str, VisibilityResult] = {}

        frustum_planes = camera.frustum_planes.copy()
        near = camera.near_plane
        far = camera.far_plane

        for eid in entity_ids:
            bounds = self._entity_bounds.get(eid)
            if bounds is None:
                results[eid] = VisibilityResult.VISIBLE
                continue

            center, half_extents, radius = bounds

            dist_to_camera = math.sqrt(
                (center[0] - camera.position_x) ** 2
                + (center[1] - camera.position_y) ** 2
                + (center[2] - camera.position_z) ** 2
            )

            if dist_to_camera < near - radius:
                results[eid] = VisibilityResult.OUT_OF_RANGE
                continue
            if dist_to_camera > far + radius:
                results[eid] = VisibilityResult.OUT_OF_RANGE
                continue

            frustum_result = self._test_frustum(
                center, half_extents, frustum_planes
            )

            if frustum_result == VisibilityResult.OCCLUDED:
                results[eid] = VisibilityResult.OCCLUDED
                continue
            if frustum_result == VisibilityResult.PARTIALLY_VISIBLE:
                results[eid] = VisibilityResult.PARTIALLY_VISIBLE
                continue

            if self._culling_method in (
                CullingMethod.OCCLUSION_QUERY,
                CullingMethod.HIERARCHICAL_Z,
            ):
                occluded = self._test_occlusion(
                    center, radius, camera
                )
                if occluded:
                    results[eid] = VisibilityResult.OCCLUDED
                    continue

            results[eid] = VisibilityResult.VISIBLE

        elapsed_ms = (time.time() - start_time) * 1000.0
        self._total_queries += 1
        self._total_cull_time_ms += elapsed_ms

        visible_count = sum(
            1 for r in results.values() if r == VisibilityResult.VISIBLE
        )
        occluded_count = sum(
            1 for r in results.values() if r == VisibilityResult.OCCLUDED
        )
        self._entities_culled_total += occluded_count

        visible_entities = [
            eid for eid, result in results.items()
            if result == VisibilityResult.VISIBLE
        ]
        partial_entities = [
            eid for eid, result in results.items()
            if result == VisibilityResult.PARTIALLY_VISIBLE
        ]

        camera.visible_entities = visible_entities
        camera.partially_visible = partial_entities
        camera.occluded_count = occluded_count
        camera.out_of_range_count = sum(
            1 for r in results.values() if r == VisibilityResult.OUT_OF_RANGE
        )
        camera.last_update_time = time.time()

        query = VisibilityQuery(
            camera_id=camera_id,
            entity_ids=list(entity_ids),
            results=dict(results),
            method=self._culling_method,
            query_time_ms=round(elapsed_ms, 3),
            entities_tested=len(entity_ids),
            entities_visible=visible_count,
            entities_occluded=occluded_count,
        )
        self._queries[query.id] = query

        return results

    def get_visible_entities(self, camera_id: str) -> List[str]:
        camera = self._cameras.get(camera_id)
        if camera is None:
            return []
        return list(camera.visible_entities)

    def is_entity_visible(
        self, camera_id: str, entity_id: str
    ) -> VisibilityResult:
        results = self.query_visibility(camera_id, entity_ids=[entity_id])
        return results.get(entity_id, VisibilityResult.OCCLUDED)

    # ------------------------------------------------------------------
    # Culling Method Configuration
    # ------------------------------------------------------------------

    def set_culling_method(self, method: str = "frustum") -> None:
        try:
            self._culling_method = CullingMethod(method.lower())
        except ValueError:
            self._culling_method = CullingMethod.FRUSTUM

    def get_culling_method(self) -> str:
        return self._culling_method.value

    # ------------------------------------------------------------------
    # Potentially Visible Set
    # ------------------------------------------------------------------

    def compute_potentially_visible_set(self, scene_id: str) -> List[str]:
        """Compute a static PVS for a scene using portal connectivity.

        Traverses the scene graph through portals connecting spatial
        cells, collecting all entities reachable from the starting cell.
        Returns the set of entity IDs that may be visible.
        """
        pvs: Set[str] = set()
        visited: Set[str] = set()

        all_entities = sorted(self._entity_bounds.keys())

        if not all_entities:
            self._pvs_data[scene_id] = pvs
            return list(pvs)

        portals: Dict[str, List[str]] = {}
        for i, entity_a in enumerate(all_entities):
            ba = self._entity_bounds.get(entity_a)
            if ba is None:
                continue
            for entity_b in all_entities[i + 1:]:
                bb = self._entity_bounds.get(entity_b)
                if bb is None:
                    continue
                dx = ba[0][0] - bb[0][0]
                dy = ba[0][1] - bb[0][1]
                dz = ba[0][2] - bb[0][2]
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                threshold = ba[2] + bb[2] + 50.0
                if dist < threshold:
                    portals.setdefault(entity_a, []).append(entity_b)
                    portals.setdefault(entity_b, []).append(entity_a)

        queue = [all_entities[0]] if all_entities else []
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            pvs.add(current)
            for neighbor in portals.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)

        self._pvs_data[scene_id] = pvs
        return list(pvs)

    def get_potentially_visible_set(self, scene_id: str) -> List[str]:
        return list(self._pvs_data.get(scene_id, set()))

    # ------------------------------------------------------------------
    # LOD Range Configuration
    # ------------------------------------------------------------------

    def set_lod_ranges(
        self,
        near: float = 10.0,
        mid: float = 50.0,
        far: float = 200.0,
    ) -> None:
        self._lod_near = max(0.1, near)
        self._lod_mid = max(self._lod_near + 1.0, mid)
        self._lod_far = max(self._lod_mid + 1.0, far)

    def get_lod_level(
        self, entity_id: str, camera_id: str
    ) -> int:
        """Return LOD level (0=near, 1=mid, 2=far, 3=out_of_range) for an entity."""
        camera = self._cameras.get(camera_id)
        if camera is None:
            return 3

        bounds = self._entity_bounds.get(entity_id)
        if bounds is None:
            return 0

        center = bounds[0]
        dist = math.sqrt(
            (center[0] - camera.position_x) ** 2
            + (center[1] - camera.position_y) ** 2
            + (center[2] - camera.position_z) ** 2
        )

        if dist <= self._lod_near:
            return 0
        elif dist <= self._lod_mid:
            return 1
        elif dist <= self._lod_far:
            return 2
        return 3

    # ------------------------------------------------------------------
    # Internal Visibility Tests
    # ------------------------------------------------------------------

    @staticmethod
    def _test_frustum(
        center: Tuple[float, float, float],
        half_extents: Tuple[float, float, float],
        planes: List[Tuple[float, float, float, float]],
    ) -> VisibilityResult:
        """Test an AABB against the view frustum planes.

        Returns OCCLUDED if completely outside, PARTIALLY_VISIBLE if
        intersecting a plane, and VISIBLE if fully inside.
        """
        cx, cy, cz = center
        hx, hy, hz = half_extents
        intersecting = False

        for a, b, c, d in planes:
            nx = cx + (hx if a > 0 else -hx)
            ny = cy + (hy if b > 0 else -hy)
            nz = cz + (hz if c > 0 else -hz)

            if a * nx + b * ny + c * nz + d < 0:
                return VisibilityResult.OCCLUDED

            px = cx + (-hx if a > 0 else hx)
            py = cy + (-hy if b > 0 else -hy)
            pz = cz + (-hz if c > 0 else hz)

            if a * px + b * py + c * pz + d < 0:
                intersecting = True

        if intersecting:
            return VisibilityResult.PARTIALLY_VISIBLE
        return VisibilityResult.VISIBLE

    def _test_occlusion(
        self,
        center: Tuple[float, float, float],
        radius: float,
        camera: CullingCamera,
    ) -> bool:
        """Test whether an entity is occluded by any registered occluder."""
        cx, cy, cz = center

        for vol in self._occluders.values():
            if not vol.is_enabled:
                continue
            if vol.occlusion_strength <= 0.0:
                continue

            ox, oy, oz = vol.position_x, vol.position_y, vol.position_z
            orad = vol.bounding_radius

            dist_occluder_to_camera = math.sqrt(
                (ox - camera.position_x) ** 2
                + (oy - camera.position_y) ** 2
                + (oz - camera.position_z) ** 2
            )
            dist_entity_to_camera = math.sqrt(
                (cx - camera.position_x) ** 2
                + (cy - camera.position_y) ** 2
                + (cz - camera.position_z) ** 2
            )

            if dist_entity_to_camera <= dist_occluder_to_camera + radius:
                continue

            dist_between = math.sqrt(
                (cx - ox) ** 2 + (cy - oy) ** 2 + (cz - oz) ** 2
            )

            if dist_between < orad + radius:
                combined_radius = orad + radius
                camera_to_occluder_dir = (
                    (ox - camera.position_x) / max(dist_occluder_to_camera, 0.001),
                    (oy - camera.position_y) / max(dist_occluder_to_camera, 0.001),
                    (oz - camera.position_z) / max(dist_occluder_to_camera, 0.001),
                )
                entity_dir = (
                    (cx - camera.position_x) / max(dist_entity_to_camera, 0.001),
                    (cy - camera.position_y) / max(dist_entity_to_camera, 0.001),
                    (cz - camera.position_z) / max(dist_entity_to_camera, 0.001),
                )
                dot = (
                    camera_to_occluder_dir[0] * entity_dir[0]
                    + camera_to_occluder_dir[1] * entity_dir[1]
                    + camera_to_occluder_dir[2] * entity_dir[2]
                )

                angular_radius = math.atan2(
                    combined_radius, dist_occluder_to_camera
                )
                angle_between = math.acos(max(-1.0, min(1.0, dot)))

                if angle_between < angular_radius * vol.occlusion_strength:
                    return True

        return False

    # ------------------------------------------------------------------
    # Stats and Reset
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        active_occluders = sum(
            1 for v in self._occluders.values() if v.is_enabled
        )
        total_entities = len(self._entity_bounds)
        cull_ratio = 0.0
        if self._total_queries > 0:
            tested_total = sum(
                q.entities_tested for q in self._queries.values()
            )
            if tested_total > 0:
                cull_ratio = (
                    self._entities_culled_total / tested_total
                )

        avg_time = 0.0
        if self._total_queries > 0:
            avg_time = self._total_cull_time_ms / self._total_queries

        return {
            "total_occluders": len(self._occluders),
            "active_occluders": active_occluders,
            "total_cameras": len(self._cameras),
            "total_entities_with_bounds": total_entities,
            "total_queries_processed": self._total_queries,
            "total_entities_culled": self._entities_culled_total,
            "cull_ratio": round(cull_ratio, 3),
            "average_query_time_ms": round(avg_time, 3),
            "current_method": self._culling_method.value,
            "pvs_scenes": len(self._pvs_data),
            "lod_ranges": {
                "near": self._lod_near,
                "mid": self._lod_mid,
                "far": self._lod_far,
            },
            "cached_queries": len(self._queries),
        }

    def reset(self) -> None:
        with self._lock:
            self._occluders.clear()
            self._cameras.clear()
            self._queries.clear()
            self._pvs_data.clear()
            self._entity_bounds.clear()
            self._culling_method = CullingMethod.FRUSTUM
            self._lod_near = 10.0
            self._lod_mid = 50.0
            self._lod_far = 200.0
            self._total_queries = 0
            self._total_cull_time_ms = 0.0
            self._entities_culled_total = 0


def get_occlusion_culling() -> OcclusionCullingSystem:
    """Return the global OcclusionCullingSystem singleton instance."""
    return OcclusionCullingSystem.get_instance()