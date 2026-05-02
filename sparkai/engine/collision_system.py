"""
SparkLabs Engine - Collision System

Spatial collision detection with broad-phase filtering and
narrow-phase intersection testing. Supports AABB, circle,
and point primitives. Implements spatial hashing for O(n)
broad-phase queries on large entity counts.

Architecture:
  CollisionSystem
    |-- SpatialHash (uniform grid for broad-phase pairing)
    |-- CollisionPrimitives (AABB, Circle, Point)
    |-- IntersectionTests (AABB×AABB, Circle×Circle, etc.)
    |-- CollisionLayer (filtering by layer masks)
    |-- TriggerVolume (non-physical overlap detection)

Collision Layers:
  Each entity belongs to one layer and checks against
  configurable layer masks. Layers are used for grouping
  (player vs enemy vs projectile vs terrain).
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import IntFlag, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class CollisionLayer(IntFlag):
    NONE = 0
    DEFAULT = auto()
    PLAYER = auto()
    ENEMY = auto()
    PROJECTILE = auto()
    TERRAIN = auto()
    PICKUP = auto()
    TRIGGER = auto()
    ALL = 0xFFFF


@dataclass
class AABB:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    width: float = 1.0
    height: float = 1.0
    depth: float = 1.0

    @property
    def min_x(self) -> float:
        return self.x - self.width / 2

    @property
    def max_x(self) -> float:
        return self.x + self.width / 2

    @property
    def min_y(self) -> float:
        return self.y - self.height / 2

    @property
    def max_y(self) -> float:
        return self.y + self.height / 2

    @property
    def min_z(self) -> float:
        return self.z - self.depth / 2

    @property
    def max_z(self) -> float:
        return self.z + self.depth / 2

    @property
    def center(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def contains_point(self, px: float, py: float, pz: float = 0.0) -> bool:
        return (
            self.min_x <= px <= self.max_x
            and self.min_y <= py <= self.max_y
            and self.min_z <= pz <= self.max_z
        )

    def overlaps_aabb(self, other: AABB) -> bool:
        return (
            self.min_x < other.max_x
            and self.max_x > other.min_x
            and self.min_y < other.max_y
            and self.max_y > other.min_y
            and self.min_z < other.max_z
            and self.max_z > other.min_z
        )

    def overlaps_circle(self, cx: float, cy: float, radius: float) -> bool:
        nearest_x = max(self.min_x, min(cx, self.max_x))
        nearest_y = max(self.min_y, min(cy, self.max_y))
        dx = cx - nearest_x
        dy = cy - nearest_y
        return (dx * dx + dy * dy) <= (radius * radius)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x, "y": self.y, "z": self.z,
            "width": self.width, "height": self.height, "depth": self.depth,
        }


@dataclass
class Collider:
    entity_id: str = ""
    aabb: AABB = field(default_factory=AABB)
    layer: CollisionLayer = CollisionLayer.DEFAULT
    mask: CollisionLayer = CollisionLayer.ALL
    is_trigger: bool = False
    is_static: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_collide_with(self, other: Collider) -> bool:
        return bool(self.mask & other.layer) and bool(other.mask & self.layer)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "aabb": self.aabb.to_dict(),
            "layer": self.layer.value if isinstance(self.layer, IntFlag) else self.layer,
            "mask": self.mask.value if isinstance(self.mask, IntFlag) else self.mask,
            "is_trigger": self.is_trigger,
            "is_static": self.is_static,
        }


@dataclass
class CollisionEvent:
    entity_a: str = ""
    entity_b: str = ""
    overlap: bool = False
    penetration_depth: float = 0.0
    contact_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SpatialHash:
    """
    Uniform grid spatial partitioning for broad-phase collision.

    Divides space into fixed-size cells. Entities are mapped
    to cells based on their AABB extent. Queries return only
    pairs within the same or neighboring cells, reducing
    O(n²) all-pairs to O(n) for uniform distributions.

    Cell size should be tuned to entity sizes for optimal
    performance: ~2× the average entity width.
    """

    def __init__(self, cell_size: float = 4.0):
        self._cell_size = max(cell_size, 0.1)
        self._cells: Dict[Tuple[int, int, int], List[Collider]] = {}
        self._entity_cells: Dict[str, Set[Tuple[int, int, int]]] = {}

    def _get_cells(self, aabb: AABB) -> List[Tuple[int, int, int]]:
        min_cell = (
            int(math.floor(aabb.min_x / self._cell_size)),
            int(math.floor(aabb.min_y / self._cell_size)),
            int(math.floor(aabb.min_z / self._cell_size)),
        )
        max_cell = (
            int(math.floor(aabb.max_x / self._cell_size)),
            int(math.floor(aabb.max_y / self._cell_size)),
            int(math.floor(aabb.max_z / self._cell_size)),
        )
        cells = []
        for x in range(min_cell[0], max_cell[0] + 1):
            for y in range(min_cell[1], max_cell[1] + 1):
                for z in range(min_cell[2], max_cell[2] + 1):
                    cells.append((x, y, z))
        return cells

    def insert(self, collider: Collider) -> None:
        self.remove(collider.entity_id)
        cells = self._get_cells(collider.aabb)
        cell_set = set(cells)
        self._entity_cells[collider.entity_id] = cell_set
        for cell in cells:
            self._cells.setdefault(cell, []).append(collider)

    def remove(self, entity_id: str) -> None:
        cells = self._entity_cells.pop(entity_id, set())
        for cell in cells:
            bucket = self._cells.get(cell)
            if bucket:
                self._cells[cell] = [c for c in bucket if c.entity_id != entity_id]

    def update(self, collider: Collider) -> None:
        self.insert(collider)

    def query_potential_pairs(self) -> List[Tuple[Collider, Collider]]:
        pairs: Set[Tuple[str, str]] = set()
        result: List[Tuple[Collider, Collider]] = []

        for cell, colliders in self._cells.items():
            for i in range(len(colliders)):
                for j in range(i + 1, len(colliders)):
                    a, b = colliders[i], colliders[j]
                    pair_key = tuple(sorted([a.entity_id, b.entity_id]))
                    if pair_key in pairs:
                        continue
                    pairs.add(pair_key)
                    result.append((a, b))

        return result

    def query_point(self, x: float, y: float, z: float = 0.0) -> List[Collider]:
        cell = (
            int(math.floor(x / self._cell_size)),
            int(math.floor(y / self._cell_size)),
            int(math.floor(z / self._cell_size)),
        )
        return self._cells.get(cell, [])

    def clear(self) -> None:
        self._cells.clear()
        self._entity_cells.clear()


class CollisionSystem:
    """
    Spatial collision detection engine.

    Detects overlaps between entities using broad-phase spatial
    hashing and narrow-phase intersection tests. Reports collision
    events for overlapping pairs and trigger volume entries/exits.

    Usage:
        cs = CollisionSystem()
        cs.add_collider(Collider(entity_id="player", aabb=AABB(x=0,y=0,width=1,height=2)))
        cs.update()
        events = cs.get_collision_events()
    """

    def __init__(self, cell_size: float = 4.0):
        self._spatial_hash = SpatialHash(cell_size=cell_size)
        self._colliders: Dict[str, Collider] = {}
        self._active_events: Dict[Tuple[str, str], CollisionEvent] = {}
        self._previous_overlaps: Set[Tuple[str, str]] = set()

    def add_collider(self, collider: Collider) -> Collider:
        self._colliders[collider.entity_id] = collider
        self._spatial_hash.insert(collider)
        return collider

    def remove_collider(self, entity_id: str) -> Optional[Collider]:
        collider = self._colliders.pop(entity_id, None)
        if collider:
            self._spatial_hash.remove(entity_id)
            keys_to_remove = [
                k for k in self._active_events
                if k[0] == entity_id or k[1] == entity_id
            ]
            for k in keys_to_remove:
                self._active_events.pop(k, None)
        return collider

    def update_collider(self, entity_id: str, aabb: AABB) -> bool:
        collider = self._colliders.get(entity_id)
        if not collider:
            return False
        collider.aabb = aabb
        self._spatial_hash.update(collider)
        return True

    def update(self) -> Tuple[List[CollisionEvent], Set[Tuple[str, str]]]:
        potential_pairs = self._spatial_hash.query_potential_pairs()
        current_overlaps: Set[Tuple[str, str]] = set()
        new_events: List[CollisionEvent] = []

        for a, b in potential_pairs:
            if not a.can_collide_with(b):
                continue
            if not a.aabb.overlaps_aabb(b.aabb):
                continue

            pair_key = tuple(sorted([a.entity_id, b.entity_id]))
            current_overlaps.add(pair_key)

            event = CollisionEvent(
                entity_a=a.entity_id,
                entity_b=b.entity_id,
                overlap=True,
                penetration_depth=0.0,
                contact_point=(
                    (a.aabb.x + b.aabb.x) / 2,
                    (a.aabb.y + b.aabb.y) / 2,
                    (a.aabb.z + b.aabb.z) / 2,
                ),
            )

            if pair_key in self._active_events:
                pass
            else:
                self._active_events[pair_key] = event
                new_events.append(event)

        exited = self._previous_overlaps - current_overlaps
        for pair_key in exited:
            self._active_events.pop(pair_key, None)

        self._previous_overlaps = current_overlaps
        return new_events, exited

    def get_collider(self, entity_id: str) -> Optional[Collider]:
        return self._colliders.get(entity_id)

    def get_active_events(self) -> Dict[Tuple[str, str], CollisionEvent]:
        return dict(self._active_events)

    def get_overlapping_entities(self, entity_id: str) -> List[str]:
        result = []
        for (a, b), event in self._active_events.items():
            if a == entity_id:
                result.append(b)
            elif b == entity_id:
                result.append(a)
        return result

    def raycast(
        self,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float = 100.0,
        layer_mask: CollisionLayer = CollisionLayer.ALL,
    ) -> Optional[Tuple[str, float, Tuple[float, float, float]]]:
        dx, dy, dz = direction
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 0.0001:
            return None
        dx, dy, dz = dx / length, dy / length, dz / length

        best_hit: Optional[Tuple[str, float, Tuple[float, float, float]]] = None
        best_t = max_distance

        step = self._spatial_hash._cell_size * 0.5
        t = 0.0
        while t < best_t:
            px = origin[0] + dx * t
            py = origin[1] + dy * t
            pz = origin[2] + dz * t
            nearby = self._spatial_hash.query_point(px, py, pz)
            for collider in nearby:
                if not (layer_mask & collider.layer):
                    continue
                if collider.aabb.contains_point(px, py, pz):
                    hit_distance = math.sqrt(
                        (px - origin[0]) ** 2 + (py - origin[1]) ** 2 + (pz - origin[2]) ** 2
                    )
                    if hit_distance < best_t:
                        best_t = hit_distance
                        best_hit = (collider.entity_id, hit_distance, (px, py, pz))
            t += step

        return best_hit

    def clear(self) -> None:
        self._colliders.clear()
        self._spatial_hash.clear()
        self._active_events.clear()
        self._previous_overlaps.clear()


_global_collision_system: Optional[CollisionSystem] = None


def get_collision_system() -> CollisionSystem:
    global _global_collision_system
    if _global_collision_system is None:
        _global_collision_system = CollisionSystem()
    return _global_collision_system
