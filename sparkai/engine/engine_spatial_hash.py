"""
Engine Spatial Hash - Spatial partitioning system for efficient spatial queries.
Provides grid-based spatial hashing, neighbor queries, region queries,
and dynamic object tracking for the SparkLabs game engine.
"""

import threading
import uuid
import time as _time_module
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any


@dataclass
class SpatialObject:
    """An object in the spatial hash grid."""
    object_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    position: Tuple[float, float] = (0.0, 0.0)
    size: Tuple[float, float] = (1.0, 1.0)
    layer: str = "default"
    properties: Dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "entity_id": self.entity_id,
            "position": list(self.position),
            "size": list(self.size),
            "layer": self.layer,
            "properties": self.properties,
        }


@dataclass
class SpatialQuery:
    """A spatial query definition."""
    query_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    center: Tuple[float, float] = (0.0, 0.0)
    radius: float = 10.0
    layer_filter: Optional[str] = None
    max_results: int = 100
    sort_by_distance: bool = True


class EngineSpatialHash:
    """
    Spatial partitioning system for efficient spatial queries.
    Uses grid-based spatial hashing, neighbor queries, region queries,
    and dynamic object tracking for performance optimization.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._objects: Dict[str, SpatialObject] = {}
            self._grid: Dict[Tuple[int, int], Set[str]] = {}
            self._cell_size: float = 10.0
            self._layer_grids: Dict[str, Dict[Tuple[int, int], Set[str]]] = {}
            self._query_cache: Dict[str, List[SpatialObject]] = {}
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'EngineSpatialHash':
        return cls()

    def set_cell_size(self, size: float):
        """Set the grid cell size."""
        self._cell_size = max(1.0, size)

    def insert(self, entity_id: str, position: Tuple[float, float],
               size: Tuple[float, float] = (1.0, 1.0),
               layer: str = "default", properties: Dict[str, Any] = None) -> SpatialObject:
        """Insert an object into the spatial hash."""
        obj = SpatialObject(
            entity_id=entity_id,
            position=position,
            size=size,
            layer=layer,
            properties=properties or {},
        )
        self._objects[obj.object_id] = obj
        self._add_to_grid(obj)
        return obj

    def update(self, object_id: str, position: Tuple[float, float],
               size: Optional[Tuple[float, float]] = None):
        """Update an object's position and size."""
        obj = self._objects.get(object_id)
        if not obj:
            return

        old_cells = self._get_cells(obj.position, obj.size)
        obj.position = position
        if size:
            obj.size = size
        new_cells = self._get_cells(obj.position, obj.size)

        if old_cells != new_cells:
            self._remove_from_grid(obj, old_cells)
            self._add_to_grid(obj)

        obj.last_updated = _time_module.time()

    def remove(self, object_id: str):
        """Remove an object from the spatial hash."""
        obj = self._objects.pop(object_id, None)
        if obj:
            self._remove_from_grid(obj)

    def _add_to_grid(self, obj: SpatialObject):
        """Add object to grid cells."""
        cells = self._get_cells(obj.position, obj.size)
        for cell in cells:
            self._grid.setdefault(cell, set()).add(obj.object_id)
            self._layer_grids.setdefault(obj.layer, {}).setdefault(cell, set()).add(obj.object_id)

    def _remove_from_grid(self, obj: SpatialObject, cells: List[Tuple[int, int]] = None):
        """Remove object from grid cells."""
        if cells is None:
            cells = self._get_cells(obj.position, obj.size)
        for cell in cells:
            grid_cell = self._grid.get(cell, set())
            grid_cell.discard(obj.object_id)
            layer_grid = self._layer_grids.get(obj.layer, {}).get(cell, set())
            layer_grid.discard(obj.object_id)

    def _get_cells(self, position: Tuple[float, float],
                   size: Tuple[float, float]) -> List[Tuple[int, int]]:
        """Get all grid cells that an object overlaps."""
        min_x = int((position[0] - size[0] / 2) / self._cell_size)
        max_x = int((position[0] + size[0] / 2) / self._cell_size)
        min_y = int((position[1] - size[1] / 2) / self._cell_size)
        max_y = int((position[1] + size[1] / 2) / self._cell_size)

        cells = []
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                cells.append((x, y))
        return cells

    def _get_cell(self, x: float, y: float) -> Tuple[int, int]:
        """Get the grid cell for a point."""
        return (int(x / self._cell_size), int(y / self._cell_size))

    def query_radius(self, center: Tuple[float, float], radius: float,
                     layer: Optional[str] = None,
                     max_results: int = 100) -> List[SpatialObject]:
        """Query objects within a radius of a point."""
        radius_sq = radius * radius
        search_cells = self._get_cells(center, (radius * 2, radius * 2))

        candidates: Set[str] = set()
        for cell in search_cells:
            if layer:
                layer_grid = self._layer_grids.get(layer, {})
                candidates.update(layer_grid.get(cell, set()))
            else:
                candidates.update(self._grid.get(cell, set()))

        results = []
        for obj_id in candidates:
            obj = self._objects.get(obj_id)
            if not obj:
                continue
            dx = obj.position[0] - center[0]
            dy = obj.position[1] - center[1]
            dist_sq = dx * dx + dy * dy
            if dist_sq <= radius_sq:
                results.append(obj)

        results.sort(key=lambda o: (o.position[0] - center[0]) ** 2 + (o.position[1] - center[1]) ** 2)
        return results[:max_results]

    def query_rect(self, min_x: float, min_y: float, max_x: float, max_y: float,
                   layer: Optional[str] = None) -> List[SpatialObject]:
        """Query objects within a rectangular region."""
        width = max_x - min_x
        height = max_y - min_y
        center = ((min_x + max_x) / 2, (min_y + max_y) / 2)
        search_cells = self._get_cells(center, (width, height))

        candidates: Set[str] = set()
        for cell in search_cells:
            if layer:
                layer_grid = self._layer_grids.get(layer, {})
                candidates.update(layer_grid.get(cell, set()))
            else:
                candidates.update(self._grid.get(cell, set()))

        results = []
        for obj_id in candidates:
            obj = self._objects.get(obj_id)
            if not obj:
                continue
            obj_min_x = obj.position[0] - obj.size[0] / 2
            obj_max_x = obj.position[0] + obj.size[0] / 2
            obj_min_y = obj.position[1] - obj.size[1] / 2
            obj_max_y = obj.position[1] + obj.size[1] / 2

            if obj_max_x >= min_x and obj_min_x <= max_x and obj_max_y >= min_y and obj_min_y <= max_y:
                results.append(obj)

        return results

    def query_nearest(self, center: Tuple[float, float], k: int = 1,
                      layer: Optional[str] = None,
                      max_radius: float = 100.0) -> List[SpatialObject]:
        """Query the k nearest objects to a point."""
        results = self.query_radius(center, max_radius, layer, k)
        return results[:k]

    def query_line(self, start: Tuple[float, float], end: Tuple[float, float],
                   width: float = 1.0, layer: Optional[str] = None) -> List[SpatialObject]:
        """Query objects along a line segment."""
        min_x = min(start[0], end[0]) - width
        max_x = max(start[0], end[0]) + width
        min_y = min(start[1], end[1]) - width
        max_y = max(start[1], end[1]) + width

        candidates = self.query_rect(min_x, min_y, max_x, max_y, layer)
        results = []

        dx = end[0] - start[0]
        dy = end[1] - start[1]
        line_len_sq = dx * dx + dy * dy

        if line_len_sq == 0:
            return candidates

        for obj in candidates:
            t = max(0, min(1, ((obj.position[0] - start[0]) * dx + (obj.position[1] - start[1]) * dy) / line_len_sq))
            proj_x = start[0] + t * dx
            proj_y = start[1] + t * dy
            dist_sq = (obj.position[0] - proj_x) ** 2 + (obj.position[1] - proj_y) ** 2

            if dist_sq <= (width + max(obj.size[0], obj.size[1]) / 2) ** 2:
                results.append(obj)

        return results

    def get_object(self, object_id: str) -> Optional[SpatialObject]:
        """Get an object by ID."""
        return self._objects.get(object_id)

    def get_by_entity(self, entity_id: str) -> List[SpatialObject]:
        """Get all spatial objects for an entity."""
        return [obj for obj in self._objects.values() if obj.entity_id == entity_id]

    def get_layer_objects(self, layer: str) -> List[SpatialObject]:
        """Get all objects in a specific layer."""
        return [obj for obj in self._objects.values() if obj.layer == layer]

    def clear(self):
        """Clear all objects from the spatial hash."""
        self._objects.clear()
        self._grid.clear()
        self._layer_grids.clear()
        self._query_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get spatial hash statistics."""
        grid_cells = self._grid
        total_objects = len(self._objects)
        total_cells = len(grid_cells)

        if total_cells > 0:
            avg_objects_per_cell = sum(len(c) for c in grid_cells.values()) / total_cells
        else:
            avg_objects_per_cell = 0.0

        return {
            "total_objects": total_objects,
            "total_cells": total_cells,
            "cell_size": self._cell_size,
            "avg_objects_per_cell": round(avg_objects_per_cell, 2),
            "layers": list(self._layer_grids.keys()),
            "layer_counts": {layer: len(self._layer_grids[layer]) for layer in self._layer_grids},
        }


def get_spatial_hash() -> EngineSpatialHash:
    return EngineSpatialHash.get_instance()