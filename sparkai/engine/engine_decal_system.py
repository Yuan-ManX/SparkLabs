"""
SparkLabs Engine - Decal System

Projected decal rendering for surface detail and environmental effects.
Manages planar, cylindrical, spherical, and mesh-surface decal projection
with atlas-based texture selection and configurable blend modes.

Architecture:
    DecalSystem
      |-- DecalProjector (texture source with projection type and sizing)
      |-- DecalAtlas (grid-based texture atlas with tile indexing)
      |-- DecalInstance (placed decal with world-space transform and blend mode)
      |-- DecalRenderBatch (optimized render batch gathered by camera proximity)

Decal Features:
    - PLANAR: flat projection along a plane normal
    - CYLINDRICAL: wraps around cylindrical surfaces
    - SPHERICAL: projects onto spherical geometry
    - MESH_SURFACE: conforms to underlying mesh vertices
    - ALPHA_BLEND: standard transparency blending
    - MULTIPLY: darkens the surface color
    - ADDITIVE: brightens the surface color for glow effects
    - NORMAL_MAP_ONLY: applies normal perturbation without color
    - ATLAS: tile-based texture atlases for batch-efficient decal selection
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DecalProjection(Enum):
    """Geometry projection method for applying decals to surfaces."""
    PLANAR = "planar"
    CYLINDRICAL = "cylindrical"
    SPHERICAL = "spherical"
    MESH_SURFACE = "mesh_surface"


class DecalBlendMode(Enum):
    """Rendering blend operation for decal color compositing."""
    OPAQUE = "opaque"
    ALPHA_BLEND = "alpha_blend"
    MULTIPLY = "multiply"
    ADDITIVE = "additive"
    NORMAL_MAP_ONLY = "normal_map_only"


class DecalLifetime(Enum):
    """Lifecycle behavior determining when a decal instance is removed."""
    PERMANENT = "permanent"
    TIME_BASED = "time_based"
    DISTANCE_BASED = "distance_based"
    TRIGGER_BASED = "trigger_based"


@dataclass
class DecalProjector:
    """Texture source definition with projection parameters for decal placement."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    texture_ref: str = ""
    projection: DecalProjection = DecalProjection.PLANAR
    size: Tuple[float, float] = (1.0, 1.0)
    aspect_ratio: float = 1.0
    depth: float = 0.5
    texture_tint_r: int = 255
    texture_tint_g: int = 255
    texture_tint_b: int = 255
    texture_tint_a: int = 255
    is_active: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "texture_ref": self.texture_ref,
            "projection": self.projection.value,
            "size": list(self.size),
            "aspect_ratio": round(self.aspect_ratio, 3),
            "depth": round(self.depth, 2),
            "texture_tint": [
                self.texture_tint_r,
                self.texture_tint_g,
                self.texture_tint_b,
                self.texture_tint_a,
            ],
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class DecalAtlas:
    """Grid-based texture atlas for efficient multi-decal batch rendering."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    texture_ref: str = ""
    grid: Tuple[int, int] = (4, 4)
    tile_count: int = 16
    tile_size_u: float = 0.25
    tile_size_v: float = 0.25
    is_active: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "texture_ref": self.texture_ref,
            "grid": list(self.grid),
            "tile_count": self.tile_count,
            "tile_size": [round(self.tile_size_u, 4), round(self.tile_size_v, 4)],
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    def get_tile_uv(self, tile_index: int) -> Tuple[float, float, float, float]:
        cols, rows = self.grid
        if cols <= 0 or rows <= 0:
            return (0.0, 0.0, 1.0, 1.0)

        max_tiles = cols * rows
        tile_index = tile_index % max_tiles
        col = tile_index % cols
        row = tile_index // cols

        u0 = col * self.tile_size_u
        v0 = row * self.tile_size_v
        u1 = u0 + self.tile_size_u
        v1 = v0 + self.tile_size_v

        return (u0, v0, u1, v1)


@dataclass
class DecalInstance:
    """Placed decal with world-space transform, atlas tile, and blend configuration."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    projector_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    atlas_id: str = ""
    tile_index: int = 0
    blend_mode: DecalBlendMode = DecalBlendMode.ALPHA_BLEND
    lifetime_type: DecalLifetime = DecalLifetime.PERMANENT
    max_lifetime: float = 0.0
    max_distance: float = 0.0
    elapsed_time: float = 0.0
    is_active: bool = True
    layer: int = 0
    sort_order: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "projector_id": self.projector_id,
            "position": list(self.position),
            "rotation": list(self.rotation),
            "scale": list(self.scale),
            "atlas_id": self.atlas_id,
            "tile_index": self.tile_index,
            "blend_mode": self.blend_mode.value,
            "lifetime_type": self.lifetime_type.value,
            "max_lifetime": round(self.max_lifetime, 2),
            "max_distance": round(self.max_distance, 2),
            "elapsed_time": round(self.elapsed_time, 3),
            "is_active": self.is_active,
            "layer": self.layer,
            "sort_order": self.sort_order,
            "created_at": self.created_at,
        }

    def distance_to(self, point: Tuple[float, float, float]) -> float:
        dx = self.position[0] - point[0]
        dy = self.position[1] - point[1]
        dz = self.position[2] - point[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)


@dataclass
class DecalRenderBatch:
    """Optimized collection of decal instances for a single draw call batch."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    instance_ids: List[str] = field(default_factory=list)
    camera_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    batch_size: int = 0
    total_count: int = 0
    draw_call_estimate: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "instance_count": len(self.instance_ids),
            "instance_ids": self.instance_ids,
            "camera_position": list(self.camera_position),
            "batch_size": self.batch_size,
            "total_count": self.total_count,
            "draw_call_estimate": self.draw_call_estimate,
            "created_at": self.created_at,
        }


class DecalSystem:
    """Projected decal rendering system for surface detail and environmental effects."""

    _instance: Optional["DecalSystem"] = None
    _lock = threading.RLock()

    MAX_PROJECTORS = 1024
    MAX_ATLASES = 256
    MAX_INSTANCES = 16384
    DEFAULT_MAX_CULL_DISTANCE = 50.0
    DEFAULT_MAX_BATCH_COUNT = 100

    def __init__(self) -> None:
        self._projectors: Dict[str, DecalProjector] = {}
        self._atlases: Dict[str, DecalAtlas] = {}
        self._instances: Dict[str, DecalInstance] = {}
        self._projector_to_instances: Dict[str, List[str]] = {}
        self._total_decal_placed: int = 0
        self._total_decal_removed: int = 0
        self._total_batches_gathered: int = 0
        self._max_cull_distance: float = self.DEFAULT_MAX_CULL_DISTANCE
        self._max_batch_count: int = self.DEFAULT_MAX_BATCH_COUNT

    @classmethod
    def get_instance(cls) -> "DecalSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Projector Management ----

    def create_projector(self,
                         name: str,
                         texture_ref: str = "",
                         projection: str = "planar",
                         size: Tuple[float, float] = (1.0, 1.0)) -> DecalProjector:
        try:
            proj = DecalProjection(projection.lower())
        except ValueError:
            proj = DecalProjection.PLANAR

        if len(self._projectors) >= self.MAX_PROJECTORS:
            raise RuntimeError(
                f"Projector limit reached ({self.MAX_PROJECTORS})"
            )

        width = max(0.01, size[0])
        height = max(0.01, size[1])

        projector = DecalProjector(
            name=name,
            texture_ref=texture_ref,
            projection=proj,
            size=(width, height),
            aspect_ratio=width / height,
        )
        self._projectors[projector.id] = projector
        self._projector_to_instances[projector.id] = []
        return projector

    def get_projector(self, projector_id: str) -> Optional[DecalProjector]:
        return self._projectors.get(projector_id)

    def list_projectors(self) -> List[DecalProjector]:
        return sorted(self._projectors.values(), key=lambda p: p.created_at)

    def remove_projector(self, projector_id: str) -> bool:
        projector = self._projectors.pop(projector_id, None)
        if projector is None:
            return False

        instance_ids = self._projector_to_instances.pop(projector_id, [])
        for instance_id in instance_ids:
            self._instances.pop(instance_id, None)

        return True

    # ---- Decal Placement ----

    def place_decal(self,
                    projector_id: str,
                    position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)) -> DecalInstance:
        if projector_id not in self._projectors:
            raise ValueError(f"Projector not found: {projector_id}")

        if len(self._instances) >= self.MAX_INSTANCES:
            raise RuntimeError(
                f"Decal instance limit reached ({self.MAX_INSTANCES})"
            )

        instance = DecalInstance(
            projector_id=projector_id,
            position=position,
            rotation=rotation,
            scale=scale,
        )
        self._instances[instance.id] = instance
        self._projector_to_instances[projector_id].append(instance.id)
        self._total_decal_placed += 1
        return instance

    def get_decal(self, instance_id: str) -> Optional[DecalInstance]:
        return self._instances.get(instance_id)

    def list_decals(self,
                    projector_id: Optional[str] = None) -> List[DecalInstance]:
        if projector_id is not None:
            instance_ids = self._projector_to_instances.get(projector_id, [])
            return [self._instances[i] for i in instance_ids if i in self._instances]
        return sorted(self._instances.values(), key=lambda d: d.created_at)

    def remove_decal(self, instance_id: str) -> bool:
        instance = self._instances.pop(instance_id, None)
        if instance is None:
            return False

        projector_instances = self._projector_to_instances.get(
            instance.projector_id, []
        )
        if instance_id in projector_instances:
            projector_instances.remove(instance_id)

        self._total_decal_removed += 1
        return True

    # ---- Atlas Management ----

    def configure_atlas(self,
                        name: str,
                        texture_ref: str = "",
                        grid: Tuple[int, int] = (4, 4)) -> DecalAtlas:
        cols, rows = grid
        cols = max(1, min(16, cols))
        rows = max(1, min(16, rows))

        if len(self._atlases) >= self.MAX_ATLASES:
            raise RuntimeError(
                f"Atlas limit reached ({self.MAX_ATLASES})"
            )

        atlas = DecalAtlas(
            name=name,
            texture_ref=texture_ref,
            grid=(cols, rows),
            tile_count=cols * rows,
            tile_size_u=1.0 / cols,
            tile_size_v=1.0 / rows,
        )
        self._atlases[atlas.id] = atlas
        return atlas

    def get_atlas(self, atlas_id: str) -> Optional[DecalAtlas]:
        return self._atlases.get(atlas_id)

    def list_atlases(self) -> List[DecalAtlas]:
        return sorted(self._atlases.values(), key=lambda a: a.created_at)

    def remove_atlas(self, atlas_id: str) -> bool:
        if atlas_id not in self._atlases:
            return False
        del self._atlases[atlas_id]

        for instance in self._instances.values():
            if instance.atlas_id == atlas_id:
                instance.atlas_id = ""
                instance.tile_index = 0

        return True

    # ---- Atlas Tile Selection ----

    def select_decal_from_atlas(self,
                                 instance_id: str,
                                 atlas_id: str,
                                 tile_index: int) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False

        atlas = self._atlases.get(atlas_id)
        if atlas is None:
            return False

        max_tiles = atlas.tile_count
        if max_tiles <= 0:
            return False

        instance.atlas_id = atlas_id
        instance.tile_index = tile_index % max_tiles
        return True

    # ---- Blend Mode ----

    def set_blend_mode(self,
                        instance_id: str,
                        blend_mode: str = "alpha_blend") -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False

        try:
            bm = DecalBlendMode(blend_mode.lower())
        except ValueError:
            return False

        instance.blend_mode = bm
        return True

    # ---- Lifetime Configuration ----

    def set_lifetime(self,
                     instance_id: str,
                     lifetime_type: str = "permanent",
                     max_lifetime: float = 0.0,
                     max_distance: float = 0.0) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False

        try:
            lt = DecalLifetime(lifetime_type.lower())
        except ValueError:
            return False

        instance.lifetime_type = lt
        instance.max_lifetime = max(0.0, max_lifetime)
        instance.max_distance = max(0.0, max_distance)
        return True

    # ---- Render Batch Gathering ----

    def gather_batch(self,
                     camera_position: Tuple[float, float, float],
                     max_count: int = 100) -> DecalRenderBatch:
        self._total_batches_gathered += 1

        max_count = max(1, min(max_count, self._max_batch_count))

        scored: List[Tuple[float, str]] = []
        for instance in self._instances.values():
            if not instance.is_active:
                continue
            dist = instance.distance_to(camera_position)
            if dist > self._max_cull_distance:
                continue
            scored.append((dist, instance.id))

        scored.sort(key=lambda x: x[0])
        selected = scored[:max_count]

        instance_ids = [item[1] for item in selected]

        batch = DecalRenderBatch(
            instance_ids=instance_ids,
            camera_position=camera_position,
            batch_size=len(instance_ids),
            total_count=len(self._instances),
        )

        unique_atlases = set()
        unique_projectors = set()
        for iid in instance_ids:
            inst = self._instances.get(iid)
            if inst:
                if inst.atlas_id:
                    unique_atlases.add(inst.atlas_id)
                unique_projectors.add(inst.projector_id)

        batch.draw_call_estimate = max(1, len(unique_atlases) + len(unique_projectors))

        return batch

    # ---- Distance Culling ----

    def cull_by_distance(self,
                          camera_pos: Tuple[float, float, float],
                          max_distance: float = 50.0) -> int:
        culled = 0
        max_dist = max(0.1, max_distance)

        for instance in list(self._instances.values()):
            if not instance.is_active:
                continue
            dist = instance.distance_to(camera_pos)
            if dist > max_dist:
                instance.is_active = False
                culled += 1

        return culled

    def set_max_cull_distance(self, distance: float) -> None:
        self._max_cull_distance = max(0.1, distance)

    def set_max_batch_count(self, count: int) -> None:
        self._max_batch_count = max(1, count)

    # ---- Update Tick ----

    def tick(self, delta_time: float = 0.016,
             camera_position: Optional[Tuple[float, float, float]] = None) -> int:
        expired: List[str] = []

        for instance in self._instances.values():
            if not instance.is_active:
                continue

            if instance.lifetime_type == DecalLifetime.TIME_BASED:
                instance.elapsed_time += delta_time
                if instance.max_lifetime > 0.0 and instance.elapsed_time >= instance.max_lifetime:
                    instance.is_active = False
                    expired.append(instance.id)

            elif instance.lifetime_type == DecalLifetime.DISTANCE_BASED:
                if camera_position is not None and instance.max_distance > 0.0:
                    dist = instance.distance_to(camera_position)
                    if dist > instance.max_distance:
                        instance.is_active = False
                        expired.append(instance.id)

            elif instance.lifetime_type == DecalLifetime.TRIGGER_BASED:
                pass

        for instance_id in expired:
            self.remove_decal(instance_id)

        return len(expired)

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        blend_counts: Dict[str, int] = {}
        lifetime_counts: Dict[str, int] = {}
        projection_counts: Dict[str, int] = {}
        active_count = 0

        for instance in self._instances.values():
            if instance.is_active:
                active_count += 1

            bm = instance.blend_mode.value
            blend_counts[bm] = blend_counts.get(bm, 0) + 1

            lt = instance.lifetime_type.value
            lifetime_counts[lt] = lifetime_counts.get(lt, 0) + 1

        for projector in self._projectors.values():
            proj = projector.projection.value
            projection_counts[proj] = projection_counts.get(proj, 0) + 1

        instances_per_projector = {}
        for pid, iids in self._projector_to_instances.items():
            instances_per_projector[pid] = len(iids)

        return {
            "total_projectors": len(self._projectors),
            "total_atlases": len(self._atlases),
            "total_instances": len(self._instances),
            "active_instances": active_count,
            "inactive_instances": len(self._instances) - active_count,
            "total_decal_placed": self._total_decal_placed,
            "total_decal_removed": self._total_decal_removed,
            "total_batches_gathered": self._total_batches_gathered,
            "blend_mode_distribution": blend_counts,
            "lifetime_distribution": lifetime_counts,
            "projection_distribution": projection_counts,
            "max_cull_distance": round(self._max_cull_distance, 1),
            "max_batch_count": self._max_batch_count,
            "max_projectors": self.MAX_PROJECTORS,
            "max_atlases": self.MAX_ATLASES,
            "max_instances": self.MAX_INSTANCES,
            "instances_per_projector": instances_per_projector,
        }

    # ---- Reset ----

    def reset(self) -> None:
        with self._lock:
            self._projectors.clear()
            self._atlases.clear()
            self._instances.clear()
            self._projector_to_instances.clear()
            self._total_decal_placed = 0
            self._total_decal_removed = 0
            self._total_batches_gathered = 0
            self._max_cull_distance = self.DEFAULT_MAX_CULL_DISTANCE
            self._max_batch_count = self.DEFAULT_MAX_BATCH_COUNT


def get_decal_system() -> DecalSystem:
    return DecalSystem.get_instance()