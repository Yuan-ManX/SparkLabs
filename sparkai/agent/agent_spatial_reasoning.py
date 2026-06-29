"""
SparkLabs Agent - Spatial Reasoning Engine

Spatial cognition for AI agents: reasoning about 2D/3D space,
relative positioning, containment, distance semantics, visibility,
reachability, and spatial problem-solving.

Agents use this module to answer questions like "is the player within
reach?", "where should I take cover?", "can the player see me?", and
to reason about layout for level design and tactical AI.

Architecture:
  SpatialReasoningEngine (Singleton, double-checked locking)
    |-- SpatialRelation     -- topological relations between entities
    |-- SpatialEntity       -- a positioned object in space
    |-- SpatialRegion       -- a bounded area/volume
    |-- SpatialConstraint   -- a spatial constraint between entities
    |-- SpatialReasoningSnapshot -- complete engine snapshot

Subsystems:
  1. Entity Placement -- register entities with positions and dimensions
  2. Topological Ops  -- compute containment, adjacency, overlap relations
  3. Distance Metrics -- Euclidean, Manhattan, Chebyshev distance
  4. Visibility       -- line-of-sight checks with obstacle occlusion
  5. Reachability    -- whether one entity can reach another
  6. Spatial Queries -- find nearest, within range, in region, along ray
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SpatialRelation(Enum):
    """Topological relations between two spatial entities."""
    DISJOINT = "disjoint"           # No overlap, not touching
    TOUCHES = "touches"             # Boundaries meet but interiors don't overlap
    OVERLAPS = "overlaps"           # Interiors partially overlap
    CONTAINS = "contains"           # A fully contains B
    WITHIN = "within"                # A is fully within B
    EQUALS = "equals"               # Identical bounds
    INTERSECTS = "intersects"       # Any kind of intersection


class DistanceMetric(Enum):
    """Distance computation strategy."""
    EUCLIDEAN = "euclidean"
    MANHATTAN = "manhattan"
    CHEBYSHEV = "chebyshev"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SpatialEntity:
    """A positioned object in 2D or 3D space."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    width: float = 0.0
    height: float = 0.0
    depth: float = 0.0
    is_3d: bool = False
    is_obstacle: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def center(self) -> Tuple[float, float, float]:
        if self.is_3d:
            return (
                self.x + self.width / 2,
                self.y + self.height / 2,
                self.z + self.depth / 2,
            )
        return (self.x + self.width / 2, self.y + self.height / 2, 0.0)

    @property
    def bounds(self) -> Tuple[float, float, float, float, float, float]:
        """Returns (min_x, min_y, min_z, max_x, max_y, max_z)."""
        return (
            self.x, self.y, self.z,
            self.x + self.width, self.y + self.height, self.z + self.depth,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
            "is_3d": self.is_3d,
            "is_obstacle": self.is_obstacle,
            "center": self.center,
            "bounds": self.bounds,
            "metadata": dict(self.metadata),
        }


@dataclass
class SpatialRegion:
    """A bounded area or volume in space."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    min_x: float = 0.0
    min_y: float = 0.0
    min_z: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0
    max_z: float = 0.0
    is_3d: bool = False
    region_type: str = "generic"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def contains_point(self, x: float, y: float, z: float = 0.0) -> bool:
        if self.is_3d:
            return (self.min_x <= x <= self.max_x and
                    self.min_y <= y <= self.max_y and
                    self.min_z <= z <= self.max_z)
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def contains_entity(self, entity: SpatialEntity) -> bool:
        """Check if an entity is fully within this region."""
        ex_min, ey_min, ez_min, ex_max, ey_max, ez_max = entity.bounds
        return (self.min_x <= ex_min and self.max_x >= ex_max and
                self.min_y <= ey_min and self.max_y >= ey_max)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "min_x": self.min_x,
            "min_y": self.min_y,
            "min_z": self.min_z,
            "max_x": self.max_x,
            "max_y": self.max_y,
            "max_z": self.max_z,
            "is_3d": self.is_3d,
            "region_type": self.region_type,
            "metadata": dict(self.metadata),
        }


@dataclass
class SpatialConstraint:
    """A spatial constraint between two entities."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entity_a_id: str = ""
    entity_b_id: str = ""
    relation: SpatialRelation = SpatialRelation.DISJOINT
    max_distance: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_a_id": self.entity_a_id,
            "entity_b_id": self.entity_b_id,
            "relation": self.relation.value,
            "max_distance": self.max_distance,
            "metadata": dict(self.metadata),
        }


@dataclass
class SpatialReasoningSnapshot:
    """Complete snapshot of the Spatial Reasoning Engine."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    entity_count: int = 0
    region_count: int = 0
    constraint_count: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "entity_count": self.entity_count,
            "region_count": self.region_count,
            "constraint_count": self.constraint_count,
            "stats": dict(self.stats),
        }


# ---------------------------------------------------------------------------
# Singleton Engine
# ---------------------------------------------------------------------------

class SpatialReasoningEngine:
    """Singleton spatial reasoning engine for AI agents."""

    _instance: Optional["SpatialReasoningEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "SpatialReasoningEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.__init_singleton()
        return cls._instance

    def __init_singleton(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._entities: Dict[str, SpatialEntity] = {}
        self._regions: Dict[str, SpatialRegion] = {}
        self._constraints: List[SpatialConstraint] = []
        self._handlers: Dict[str, Callable] = {}
        self._stats: Dict[str, Any] = {
            "queries_total": 0,
            "relations_computed": 0,
            "visibility_checks": 0,
            "reachability_checks": 0,
        }

    @classmethod
    def get_instance(cls) -> "SpatialReasoningEngine":
        return cls()

    # -- Entity management --------------------------------------------------

    def add_entity(self, entity: SpatialEntity) -> SpatialEntity:
        with self._instance_lock:
            self._entities[entity.id] = entity
            return entity

    def create_entity(self, name: str, x: float, y: float, z: float = 0.0,
                      width: float = 0.0, height: float = 0.0, depth: float = 0.0,
                      is_3d: bool = False, is_obstacle: bool = False) -> SpatialEntity:
        entity = SpatialEntity(
            name=name, x=x, y=y, z=z,
            width=width, height=height, depth=depth,
            is_3d=is_3d, is_obstacle=is_obstacle,
        )
        return self.add_entity(entity)

    def get_entity(self, entity_id: str) -> Optional[SpatialEntity]:
        with self._instance_lock:
            return self._entities.get(entity_id)

    def get_all_entities(self) -> List[SpatialEntity]:
        with self._instance_lock:
            return list(self._entities.values())

    def remove_entity(self, entity_id: str) -> bool:
        with self._instance_lock:
            if entity_id in self._entities:
                del self._entities[entity_id]
                self._constraints = [
                    c for c in self._constraints
                    if c.entity_a_id != entity_id and c.entity_b_id != entity_id
                ]
                return True
            return False

    # -- Region management --------------------------------------------------

    def add_region(self, region: SpatialRegion) -> SpatialRegion:
        with self._instance_lock:
            self._regions[region.id] = region
            return region

    def create_region(self, name: str, min_x: float, min_y: float,
                      max_x: float, max_y: float, region_type: str = "generic") -> SpatialRegion:
        region = SpatialRegion(
            name=name, min_x=min_x, min_y=min_y,
            max_x=max_x, max_y=max_y,
            region_type=region_type,
        )
        return self.add_region(region)

    def get_region(self, region_id: str) -> Optional[SpatialRegion]:
        with self._instance_lock:
            return self._regions.get(region_id)

    def get_all_regions(self) -> List[SpatialRegion]:
        with self._instance_lock:
            return list(self._regions.values())

    # -- Distance computation -----------------------------------------------

    def distance(self, a_id: str, b_id: str, metric: DistanceMetric = DistanceMetric.EUCLIDEAN) -> Optional[float]:
        """Compute the distance between two entities."""
        a = self.get_entity(a_id)
        b = self.get_entity(b_id)
        if a is None or b is None:
            return None
        self._stats["queries_total"] += 1
        ax, ay, az = a.center
        bx, by, bz = b.center
        if metric == DistanceMetric.EUCLIDEAN:
            if a.is_3d or b.is_3d:
                return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)
            return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)
        elif metric == DistanceMetric.MANHATTAN:
            if a.is_3d or b.is_3d:
                return abs(ax - bx) + abs(ay - by) + abs(az - bz)
            return abs(ax - bx) + abs(ay - by)
        else:  # CHEBYSHEV
            if a.is_3d or b.is_3d:
                return max(abs(ax - bx), abs(ay - by), abs(az - bz))
            return max(abs(ax - bx), abs(ay - by))

    # -- Topological relations ---------------------------------------------

    def compute_relation(self, a: SpatialEntity, b: SpatialEntity) -> SpatialRelation:
        """Compute the topological relation between two entities."""
        self._stats["relations_computed"] += 1
        ax_min, ay_min, _, ax_max, ay_max, _ = a.bounds
        bx_min, by_min, _, bx_max, by_max, _ = b.bounds
        # No overlap
        if ax_max < bx_min or bx_max < ax_min or ay_max < by_min or by_max < ay_min:
            # Check touching
            tol = 1e-9
            if (abs(ax_max - bx_min) < tol or abs(bx_max - ax_min) < tol or
                abs(ay_max - by_min) < tol or abs(by_max - ay_min) < tol):
                return SpatialRelation.TOUCHES
            return SpatialRelation.DISJOINT
        # Check equals
        tol = 1e-9
        if (abs(ax_min - bx_min) < tol and abs(ax_max - bx_max) < tol and
            abs(ay_min - by_min) < tol and abs(ay_max - by_max) < tol):
            return SpatialRelation.EQUALS
        # Check contains / within
        if ax_min <= bx_min and ax_max >= bx_max and ay_min <= by_min and ay_max >= by_max:
            return SpatialRelation.CONTAINS
        if bx_min <= ax_min and bx_max >= ax_max and by_min <= ay_min and by_max >= ay_max:
            return SpatialRelation.WITHIN
        return SpatialRelation.OVERLAPS

    def check_relation(self, a_id: str, b_id: str, expected: SpatialRelation) -> bool:
        a = self.get_entity(a_id)
        b = self.get_entity(b_id)
        if a is None or b is None:
            return False
        return self.compute_relation(a, b) == expected

    # -- Visibility ---------------------------------------------------------

    def check_visibility(self, observer_id: str, target_id: str) -> Dict[str, Any]:
        """Check if an observer can see a target, considering obstacles."""
        self._stats["visibility_checks"] += 1
        observer = self.get_entity(observer_id)
        target = self.get_entity(target_id)
        if observer is None or target is None:
            return {"visible": False, "reason": "entity_not_found"}
        ox, oy, _ = observer.center
        tx, ty, _ = target.center
        # Check for obstacles blocking line of sight
        blocking_obstacles: List[str] = []
        for entity in self._entities.values():
            if entity.id in (observer_id, target_id) or not entity.is_obstacle:
                continue
            if self._line_intersects_entity(ox, oy, tx, ty, entity):
                blocking_obstacles.append(entity.id)
        visible = len(blocking_obstacles) == 0
        dist = self.distance(observer_id, target_id)
        return {
            "visible": visible,
            "distance": dist,
            "blocking_obstacles": blocking_obstacles,
        }

    def _line_intersects_entity(self, x1: float, y1: float, x2: float, y2: float,
                                 entity: SpatialEntity) -> bool:
        """Check if a line segment intersects an entity's bounding box."""
        ex_min = entity.x
        ey_min = entity.y
        ex_max = entity.x + entity.width
        ey_max = entity.y + entity.height
        # Liang-Barsky line clipping algorithm
        dx = x2 - x1
        dy = y2 - y1
        p = [-dx, dx, -dy, dy]
        q = [x1 - ex_min, ex_max - x1, y1 - ey_min, ey_max - y1]
        u1, u2 = 0.0, 1.0
        for i in range(4):
            if p[i] == 0:
                if q[i] < 0:
                    return False
            else:
                t = q[i] / p[i]
                if p[i] < 0:
                    u1 = max(u1, t)
                else:
                    u2 = min(u2, t)
        return u1 < u2

    # -- Reachability ------------------------------------------------------

    def check_reachability(self, source_id: str, target_id: str, max_distance: float = float('inf')) -> Dict[str, Any]:
        """Check if source can reach target within a max distance."""
        self._stats["reachability_checks"] += 1
        dist = self.distance(source_id, target_id)
        if dist is None:
            return {"reachable": False, "reason": "entity_not_found"}
        reachable = dist <= max_distance
        return {
            "reachable": reachable,
            "distance": dist,
            "max_distance": max_distance,
            "within_range": reachable,
        }

    # -- Spatial queries ---------------------------------------------------

    def query_nearest(self, target_id: str, exclude: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Find the nearest entity to the target."""
        self._stats["queries_total"] += 1
        target = self.get_entity(target_id)
        if target is None:
            return None
        exclude_set = set(exclude or [])
        exclude_set.add(target_id)
        nearest_id: Optional[str] = None
        nearest_dist = float('inf')
        with self._instance_lock:
            for entity in self._entities.values():
                if entity.id in exclude_set:
                    continue
                dist = self.distance(target_id, entity.id)
                if dist is not None and dist < nearest_dist:
                    nearest_dist = dist
                    nearest_id = entity.id
        if nearest_id is None:
            return None
        return {"entity_id": nearest_id, "distance": nearest_dist}

    def query_within_range(self, target_id: str, radius: float) -> List[Dict[str, Any]]:
        """Find all entities within a radius of the target."""
        self._stats["queries_total"] += 1
        results: List[Dict[str, Any]] = []
        with self._instance_lock:
            for entity in self._entities.values():
                if entity.id == target_id:
                    continue
                dist = self.distance(target_id, entity.id)
                if dist is not None and dist <= radius:
                    results.append({"entity_id": entity.id, "distance": dist})
        results.sort(key=lambda r: r["distance"])
        return results

    def query_in_region(self, region_id: str) -> List[str]:
        """Find all entities within a region."""
        self._stats["queries_total"] += 1
        region = self.get_region(region_id)
        if region is None:
            return []
        results: List[str] = []
        with self._instance_lock:
            for entity in self._entities.values():
                if region.contains_entity(entity):
                    results.append(entity.id)
        return results

    def query_along_ray(self, origin_x: float, origin_y: float, direction_x: float, direction_y: float,
                        max_distance: float = 1000.0) -> List[str]:
        """Find all entities along a ray from origin in a direction."""
        self._stats["queries_total"] += 1
        # Normalize direction
        mag = math.sqrt(direction_x ** 2 + direction_y ** 2)
        if mag < 1e-9:
            return []
        dx = direction_x / mag
        dy = direction_y / mag
        end_x = origin_x + dx * max_distance
        end_y = origin_y + dy * max_distance
        results: List[str] = []
        with self._instance_lock:
            for entity in self._entities.values():
                if self._line_intersects_entity(origin_x, origin_y, end_x, end_y, entity):
                    results.append(entity.id)
        return results

    # -- Constraint management ----------------------------------------------

    def add_constraint(self, constraint: SpatialConstraint) -> SpatialConstraint:
        with self._instance_lock:
            self._constraints.append(constraint)
            return constraint

    def validate_constraints(self) -> Dict[str, Any]:
        """Validate all spatial constraints."""
        violations: List[Dict[str, Any]] = []
        checked = 0
        for c in self._constraints:
            a = self.get_entity(c.entity_a_id)
            b = self.get_entity(c.entity_b_id)
            if a is None or b is None:
                continue
            checked += 1
            actual = self.compute_relation(a, b)
            violated = False
            if c.relation != SpatialRelation.INTERSECTS and actual != c.relation:
                violated = True
            elif c.relation == SpatialRelation.INTERSECTS and actual == SpatialRelation.DISJOINT:
                violated = True
            if c.max_distance is not None:
                dist = self.distance(c.entity_a_id, c.entity_b_id)
                if dist is not None and dist > c.max_distance:
                    violated = True
            if violated:
                violations.append({
                    "constraint_id": c.id,
                    "expected_relation": c.relation.value,
                    "actual_relation": actual.value,
                    "entity_a": c.entity_a_id,
                    "entity_b": c.entity_b_id,
                })
        return {
            "checked": checked,
            "violations": violations,
            "all_satisfied": len(violations) == 0,
        }

    # -- Status and snapshot ------------------------------------------------

    def register_handler(self, event: str, handler: Callable) -> None:
        with self._instance_lock:
            self._handlers[event] = handler

    def get_status(self) -> Dict[str, Any]:
        with self._instance_lock:
            return {
                "engine_id": id(self),
                "entity_count": len(self._entities),
                "region_count": len(self._regions),
                "constraint_count": len(self._constraints),
                "stats": dict(self._stats),
            }

    def get_snapshot(self) -> SpatialReasoningSnapshot:
        with self._instance_lock:
            return SpatialReasoningSnapshot(
                entity_count=len(self._entities),
                region_count=len(self._regions),
                constraint_count=len(self._constraints),
                stats=dict(self._stats),
            )

    def reset(self) -> None:
        with self._instance_lock:
            self._entities.clear()
            self._regions.clear()
            self._constraints.clear()
            self._stats = {
                "queries_total": 0,
                "relations_computed": 0,
                "visibility_checks": 0,
                "reachability_checks": 0,
            }


# Module-level factory
def get_spatial_reasoning_engine() -> SpatialReasoningEngine:
    return SpatialReasoningEngine.get_instance()
