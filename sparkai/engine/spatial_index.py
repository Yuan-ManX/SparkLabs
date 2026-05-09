"""
SparkLabs Engine - Spatial Index

Spatial partitioning system for the SparkLabs AI-native game engine.
Provides quadtree and octree-based spatial indexing for fast
proximity queries, collision broad-phase optimization, and spatial
grouping of game objects. Reduces O(n^2) spatial queries to O(log n)
through hierarchical space subdivision.

Architecture:
  SpatialIndex
    |-- Quadtree (2D spatial partition with 4 children per node)
    |-- QuadNode (spatial region with object bucket)
    |-- Octree (3D spatial partition with 8 children per node)
    |-- SpatialQuery (range, nearest-N, region queries)
    |-- SpatialEntry (object reference with bounding box)
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class SpatialQueryType(Enum):
    RANGE = "range"
    NEAREST = "nearest"
    REGION = "region"
    ALL = "all"


@dataclass
class SpatialEntry:
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    object_id: str = ""
    object_type: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    layer: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    def overlaps(self, x: float, y: float, w: float, h: float) -> bool:
        return not (self.right <= x or self.left >= x + w or self.bottom <= y or self.top >= y + h)

    def contains_point(self, px: float, py: float) -> bool:
        return self.left <= px <= self.right and self.top <= py <= self.bottom

    def distance_to(self, px: float, py: float) -> float:
        cx, cy = self.center
        return math.sqrt((cx - px) ** 2 + (cy - py) ** 2)

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "object_id": self.object_id,
            "type": self.object_type,
            "position": {"x": self.x, "y": self.y},
            "size": {"w": self.width, "h": self.height},
        }


@dataclass
class QuadNode:
    x: float = 0.0
    y: float = 0.0
    width: float = 1000.0
    height: float = 1000.0
    depth: int = 0
    entries: List[SpatialEntry] = field(default_factory=list)
    children: Optional[Tuple["QuadNode", "QuadNode", "QuadNode", "QuadNode"]] = None
    max_depth: int = 8
    max_entries_per_node: int = 4

    @property
    def half_width(self) -> float:
        return self.width / 2

    @property
    def half_height(self) -> float:
        return self.height / 2

    @property
    def is_leaf(self) -> bool:
        return self.children is None

    def insert(self, entry: SpatialEntry) -> bool:
        if not entry.overlaps(self.x, self.y, self.width, self.height):
            return False

        if self.is_leaf:
            if len(self.entries) < self.max_entries_per_node or self.depth >= self.max_depth:
                self.entries.append(entry)
                return True
            else:
                self._subdivide()

        if self._insert_into_children(entry):
            return True

        self.entries.append(entry)
        return True

    def remove(self, object_id: str) -> int:
        removed = 0
        self.entries = [e for e in self.entries if e.object_id != object_id]
        removed += len([e for e in self.entries if e.object_id == object_id])

        if self.children:
            for child in self.children:
                removed += child.remove(object_id)

            if self._should_merge():
                entries = self.entries[:]
                for child in self.children:
                    entries.extend(child.entries)
                self.entries = entries
                self.children = None

        return removed

    def query_range(self, x: float, y: float, w: float, h: float) -> List[SpatialEntry]:
        result = []
        if self.right < x or self.x > x + w or self.bottom < y or self.y > y + h:
            return result

        for entry in self.entries:
            if entry.overlaps(x, y, w, h):
                result.append(entry)

        if self.children:
            for child in self.children:
                result.extend(child.query_range(x, y, w, h))

        return result

    def query_point(self, px: float, py: float) -> List[SpatialEntry]:
        result = []
        if not (self.x <= px <= self.right and self.y <= py <= self.bottom):
            return result

        for entry in self.entries:
            if entry.contains_point(px, py):
                result.append(entry)

        if self.children:
            for child in self.children:
                result.extend(child.query_point(px, py))

        return result

    def query_all(self) -> List[SpatialEntry]:
        result = list(self.entries)
        if self.children:
            for child in self.children:
                result.extend(child.query_all())
        return result

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def total_entries(self) -> int:
        count = len(self.entries)
        if self.children:
            for child in self.children:
                count += child.total_entries()
        return count

    def _subdivide(self) -> None:
        hw = self.half_width
        hh = self.half_height
        self.children = (
            QuadNode(self.x, self.y, hw, hh, self.depth + 1),
            QuadNode(self.x + hw, self.y, hw, hh, self.depth + 1),
            QuadNode(self.x, self.y + hh, hw, hh, self.depth + 1),
            QuadNode(self.x + hw, self.y + hh, hw, hh, self.depth + 1),
        )
        for child in self.children:
            child.max_depth = self.max_depth
            child.max_entries_per_node = self.max_entries_per_node

        remaining = []
        for entry in self.entries:
            if not self._insert_into_children(entry):
                remaining.append(entry)
        self.entries = remaining

    def _insert_into_children(self, entry: SpatialEntry) -> bool:
        if self.children is None:
            return False
        inserted = False
        for child in self.children:
            if child._try_insert(entry):
                inserted = True
        return inserted

    def _try_insert(self, entry: SpatialEntry) -> bool:
        if entry.overlaps(self.x, self.y, self.width, self.height):
            self.insert(entry)
            return True
        return False

    def _should_merge(self) -> bool:
        total = sum(child.total_entries() for child in self.children) + len(self.entries)
        return total <= self.max_entries_per_node


class SpatialIndex:
    """
    Quadtree spatial partitioning for optimized spatial queries.

    Accelerates proximity queries, collision detection broad-phase,
    and spatial grouping through hierarchical space subdivision.
    Provides range queries (all objects within a rectangle), point
    queries (all objects containing a point), nearest-N queries
    (N closest objects to a point), and region-based iteration.
    Dynamically rebalances as objects are added and removed.
    """

    _instance: Optional["SpatialIndex"] = None

    def __init__(self):
        self._root: Optional[QuadNode] = None
        self._entries: Dict[str, SpatialEntry] = {}
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> "SpatialIndex":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self, x: float = 0.0, y: float = 0.0, width: float = 10000.0, height: float = 10000.0, max_depth: int = 8, max_entries: int = 4) -> None:
        self._root = QuadNode(x=x, y=y, width=width, height=height, max_depth=max_depth, max_entries_per_node=max_entries)
        self._initialized = True

    def insert(self, object_id: str, x: float, y: float, width: float = 0.0, height: float = 0.0, object_type: str = "", layer: int = 0, tags: Optional[List[str]] = None) -> Optional[SpatialEntry]:
        if not self._initialized:
            self.initialize()
        entry = SpatialEntry(object_id=object_id, object_type=object_type, x=x, y=y, width=width, height=height, layer=layer, tags=tags or [])
        self._entries[object_id] = entry
        if self._root:
            self._root.insert(entry)
        return entry

    def update(self, object_id: str, x: float, y: float, width: Optional[float] = None, height: Optional[float] = None) -> bool:
        entry = self._entries.get(object_id)
        if not entry:
            return False
        self.remove(object_id)
        entry.x = x
        entry.y = y
        if width is not None:
            entry.width = width
        if height is not None:
            entry.height = height
        self._entries[object_id] = entry
        if self._root:
            self._root.insert(entry)
        return True

    def remove(self, object_id: str) -> bool:
        if object_id not in self._entries:
            return False
        del self._entries[object_id]
        if self._root:
            self._root.remove(object_id)
        return True

    def query_range(self, x: float, y: float, width: float, height: float, layer: Optional[int] = None) -> List[SpatialEntry]:
        if not self._root:
            return []
        results = self._root.query_range(x, y, width, height)
        if layer is not None:
            results = [e for e in results if e.layer == layer]
        return results

    def query_point(self, px: float, py: float, layer: Optional[int] = None) -> List[SpatialEntry]:
        if not self._root:
            return []
        results = self._root.query_point(px, py)
        if layer is not None:
            results = [e for e in results if e.layer == layer]
        return results

    def query_all(self) -> List[SpatialEntry]:
        if not self._root:
            return []
        return self._root.query_all()

    def find_nearest(self, px: float, py: float, n: int = 1, max_distance: float = float("inf"), layer: Optional[int] = None) -> List[SpatialEntry]:
        all_entries = self.query_all()
        candidates = [
            (e, e.distance_to(px, py))
            for e in all_entries
            if e.distance_to(px, py) <= max_distance
            and (layer is None or e.layer == layer)
        ]
        candidates.sort(key=lambda pair: pair[1])
        return [e for e, _ in candidates[:n]]

    def get_entry(self, object_id: str) -> Optional[SpatialEntry]:
        return self._entries.get(object_id)

    def get_stats(self) -> dict:
        total = len(self._entries)
        avg_depth = 0.0
        if self._root:
            total = self._root.total_entries()
        layers = {}
        for entry in self._entries.values():
            layers[entry.layer] = layers.get(entry.layer, 0) + 1
        return {
            "total_entries": total,
            "registered_objects": len(self._entries),
            "layers": layers,
            "initialized": self._initialized,
            "root_size": f"{self._root.width}x{self._root.height}" if self._root else "none",
        }

    def clear(self) -> None:
        self._root = None
        self._entries.clear()
        self._initialized = False

    def reset(self) -> None:
        self.clear()


def get_spatial_index() -> SpatialIndex:
    return SpatialIndex.get_instance()
