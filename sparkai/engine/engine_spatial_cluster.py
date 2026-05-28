"""
SparkLabs Engine - Spatial Cluster

Spatial partitioning system for physics simulation optimization.
Divides the game world into manageable clusters (grid cells, octree nodes),
groups physics bodies by spatial locality, and enables efficient collision
detection by only checking bodies within the same or adjacent clusters.

Architecture:
  SpatialCluster (singleton)
    |-- Uniform Grid Partitioning (default strategy)
    |-- Spatial Body Registry (registration, update, removal)
    |-- Cluster Cell Management (activation, neighbor tracking)
    |-- Spatial Query Engine (AABB, sphere, ray, nearest neighbor)
    |-- Collision Candidate Resolution (same and adjacent clusters)

Strategies:
  - UNIFORM_GRID: fixed-size 3D grid cells
  - OCTREE: adaptive 3D hierarchical subdivision
  - QUADTREE: adaptive 2D hierarchical subdivision
  - KDTREE: binary space partitioning tree
  - BVH: bounding volume hierarchy

Query Types:
  - AABB_OVERLAP: axis-aligned bounding box overlap test
  - SPHERE_RADIUS: spherical radius overlap test
  - RAY_CAST: ray intersection along a direction
  - NEAREST_NEIGHBOR: k-nearest neighbor search
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

_time_module = time


class PartitionStrategy(Enum):
    UNIFORM_GRID = "uniform_grid"
    OCTREE = "octree"
    QUADTREE = "quadtree"
    KDTREE = "kdtree"
    BVH = "bvh"


class SpatialDimension(Enum):
    TWO_D = "2d"
    THREE_D = "3d"


class QueryType(Enum):
    AABB_OVERLAP = "aabb_overlap"
    SPHERE_RADIUS = "sphere_radius"
    RAY_CAST = "ray_cast"
    NEAREST_NEIGHBOR = "nearest_neighbor"


class BodyType(Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    KINEMATIC = "kinematic"
    TRIGGER = "trigger"


@dataclass
class SpatialBody:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    body_type: BodyType = BodyType.DYNAMIC
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounds_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounds_max: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mass: float = 1.0
    cluster_id: str = ""
    is_sleeping: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "body_type": self.body_type.value,
            "position": list(self.position),
            "bounds_min": list(self.bounds_min),
            "bounds_max": list(self.bounds_max),
            "velocity": list(self.velocity),
            "mass": self.mass,
            "cluster_id": self.cluster_id,
            "is_sleeping": self.is_sleeping,
            "created_at": self.created_at,
        }


@dataclass
class ClusterCell:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cell_index: Tuple[int, int, int] = (0, 0, 0)
    bounds_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounds_max: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    body_ids: List[str] = field(default_factory=list)
    neighbor_cell_ids: List[str] = field(default_factory=list)
    is_active: bool = False
    body_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cell_index": list(self.cell_index),
            "bounds_min": list(self.bounds_min),
            "bounds_max": list(self.bounds_max),
            "body_ids": self.body_ids,
            "neighbor_cell_ids": self.neighbor_cell_ids,
            "is_active": self.is_active,
            "body_count": self.body_count,
        }


@dataclass
class QueryResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    query_type: QueryType = QueryType.AABB_OVERLAP
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction_or_radius: Any = 0.0
    matched_body_ids: List[str] = field(default_factory=list)
    distance: Optional[float] = None
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        direction_or_radius_value: Any = self.direction_or_radius
        if isinstance(direction_or_radius_value, tuple):
            direction_or_radius_value = list(direction_or_radius_value)
        return {
            "id": self.id,
            "query_type": self.query_type.value,
            "origin": list(self.origin),
            "direction_or_radius": direction_or_radius_value,
            "matched_body_ids": self.matched_body_ids,
            "distance": self.distance,
            "created_at": self.created_at,
        }


class SpatialCluster:
    """
    Singleton spatial partitioning system for physics simulation.

    Organizes physics bodies into spatial clusters and provides
    efficient query operations for collision detection, ray casting,
    and nearest-neighbor searches.
    """

    _instance: Optional["SpatialCluster"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_BODIES_PER_CELL = 64
    MAX_NEIGHBOR_DEPTH = 1
    DEFAULT_SLEEP_VELOCITY_THRESHOLD = 0.001

    def __new__(cls) -> "SpatialCluster":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._bodies: Dict[str, SpatialBody] = {}
                    instance._clusters: Dict[str, ClusterCell] = {}
                    instance._grid_dimensions: Tuple[int, int, int] = (0, 0, 0)
                    instance._cell_size: float = 1.0
                    instance._strategy: PartitionStrategy = PartitionStrategy.UNIFORM_GRID
                    instance._world_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
                    instance._world_max: Tuple[float, float, float] = (0.0, 0.0, 0.0)
                    instance._dimension: SpatialDimension = SpatialDimension.THREE_D
                    instance._initialized: bool = False
                    instance._total_registrations: int = 0
                    instance._total_removals: int = 0
                    instance._total_queries: int = 0
                    instance._total_position_updates: int = 0
                    instance._index_to_cluster: Dict[Tuple[int, int, int], str] = {}
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SpatialCluster":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls.__new__(cls)
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize_grid(
        self,
        world_min: Tuple[float, float, float],
        world_max: Tuple[float, float, float],
        cell_size: float,
        strategy: PartitionStrategy = PartitionStrategy.UNIFORM_GRID,
    ) -> None:
        if cell_size <= 0.0:
            raise ValueError("cell_size must be greater than zero")
        if world_min[0] >= world_max[0] or world_min[1] >= world_max[1] or world_min[2] >= world_max[2]:
            raise ValueError("world_min must be strictly less than world_max in all dimensions")

        with self._lock:
            self._world_min = world_min
            self._world_max = world_max
            self._cell_size = cell_size
            self._strategy = strategy

            wx = world_max[0] - world_min[0]
            wy = world_max[1] - world_min[1]
            wz = world_max[2] - world_min[2]

            nx = max(1, int(math.ceil(wx / cell_size)))
            ny = max(1, int(math.ceil(wy / cell_size)))
            nz = max(1, int(math.ceil(wz / cell_size)))

            self._grid_dimensions = (nx, ny, nz)

            self._bodies.clear()
            self._clusters.clear()
            self._index_to_cluster.clear()

            for ix in range(nx):
                for iy in range(ny):
                    for iz in range(nz):
                        cell = ClusterCell(
                            cell_index=(ix, iy, iz),
                            bounds_min=(
                                world_min[0] + ix * cell_size,
                                world_min[1] + iy * cell_size,
                                world_min[2] + iz * cell_size,
                            ),
                            bounds_max=(
                                min(world_max[0], world_min[0] + (ix + 1) * cell_size),
                                min(world_max[1], world_min[1] + (iy + 1) * cell_size),
                                min(world_max[2], world_min[2] + (iz + 1) * cell_size),
                            ),
                            is_active=True,
                        )
                        self._clusters[cell.id] = cell
                        self._index_to_cluster[(ix, iy, iz)] = cell.id

            for cell in self._clusters.values():
                self._compute_neighbors(cell)

            self._initialized = True

    def _compute_neighbors(self, cell: ClusterCell) -> None:
        ix, iy, iz = cell.cell_index
        nx, ny, nz = self._grid_dimensions

        neighbors: List[str] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    nx_idx = ix + dx
                    ny_idx = iy + dy
                    nz_idx = iz + dz
                    if 0 <= nx_idx < nx and 0 <= ny_idx < ny and 0 <= nz_idx < nz:
                        neighbor_id = self._index_to_cluster.get((nx_idx, ny_idx, nz_idx))
                        if neighbor_id is not None:
                            neighbors.append(neighbor_id)
        cell.neighbor_cell_ids = neighbors

    def _compute_cell_index(
        self, position: Tuple[float, float, float]
    ) -> Optional[Tuple[int, int, int]]:
        if not self._initialized:
            return None

        wx_min, wy_min, wz_min = self._world_min
        wx_max, wy_max, wz_max = self._world_max

        if not (wx_min <= position[0] <= wx_max and
                wy_min <= position[1] <= wy_max and
                wz_min <= position[2] <= wz_max):
            return None

        ix = int((position[0] - wx_min) / self._cell_size)
        iy = int((position[1] - wy_min) / self._cell_size)
        iz = int((position[2] - wz_min) / self._cell_size)

        nx, ny, nz = self._grid_dimensions
        ix = max(0, min(ix, nx - 1))
        iy = max(0, min(iy, ny - 1))
        iz = max(0, min(iz, nz - 1))

        return (ix, iy, iz)

    def _get_cluster_id_for_position(
        self, position: Tuple[float, float, float]
    ) -> Optional[str]:
        cell_index = self._compute_cell_index(position)
        if cell_index is None:
            return None
        return self._index_to_cluster.get(cell_index)

    def _cells_touching_aabb(
        self,
        bounds_min: Tuple[float, float, float],
        bounds_max: Tuple[float, float, float],
    ) -> Generator[Tuple[int, int, int], None, None]:
        min_ix, min_iy, min_iz = self._clamp_cell_index(
            self._compute_cell_index(bounds_min)
        )
        max_ix, max_iy, max_iz = self._clamp_cell_index(
            self._compute_cell_index(bounds_max)
        )

        nx, ny, nz = self._grid_dimensions
        for ix in range(min_ix, max_ix + 1):
            for iy in range(min_iy, max_iy + 1):
                for iz in range(min_iz, max_iz + 1):
                    if 0 <= ix < nx and 0 <= iy < ny and 0 <= iz < nz:
                        yield (ix, iy, iz)

    def _clamp_cell_index(
        self, cell_index: Optional[Tuple[int, int, int]]
    ) -> Tuple[int, int, int]:
        if cell_index is None:
            return (0, 0, 0)
        nx, ny, nz = self._grid_dimensions
        return (
            max(0, min(cell_index[0], nx - 1)),
            max(0, min(cell_index[1], ny - 1)),
            max(0, min(cell_index[2], nz - 1)),
        )

    @staticmethod
    def _aabb_overlaps(
        a_min: Tuple[float, float, float],
        a_max: Tuple[float, float, float],
        b_min: Tuple[float, float, float],
        b_max: Tuple[float, float, float],
    ) -> bool:
        return (
            a_min[0] <= b_max[0] and a_max[0] >= b_min[0] and
            a_min[1] <= b_max[1] and a_max[1] >= b_min[1] and
            a_min[2] <= b_max[2] and a_max[2] >= b_min[2]
        )

    @staticmethod
    def _sphere_overlaps_aabb(
        center: Tuple[float, float, float],
        radius: float,
        aabb_min: Tuple[float, float, float],
        aabb_max: Tuple[float, float, float],
    ) -> bool:
        closest_x = max(aabb_min[0], min(center[0], aabb_max[0]))
        closest_y = max(aabb_min[1], min(center[1], aabb_max[1]))
        closest_z = max(aabb_min[2], min(center[2], aabb_max[2]))

        dx = center[0] - closest_x
        dy = center[1] - closest_y
        dz = center[2] - closest_z

        return (dx * dx + dy * dy + dz * dz) <= (radius * radius)

    @staticmethod
    def _point_to_point_distance(
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
    ) -> float:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        dz = a[2] - b[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    # ------------------------------------------------------------------
    # Body Registration
    # ------------------------------------------------------------------

    def register_body(
        self,
        body_type: BodyType,
        position: Tuple[float, float, float],
        bounds_min: Tuple[float, float, float],
        bounds_max: Tuple[float, float, float],
        velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        mass: float = 1.0,
    ) -> SpatialBody:
        self._ensure_initialized()

        with self._lock:
            body = SpatialBody(
                body_type=body_type,
                position=position,
                bounds_min=bounds_min,
                bounds_max=bounds_max,
                velocity=velocity,
                mass=mass,
            )

            cell_index = self._compute_cell_index(position)
            if cell_index is not None:
                cluster_id = self._index_to_cluster.get(cell_index)
                if cluster_id is not None:
                    body.cluster_id = cluster_id
                    cluster = self._clusters[cluster_id]
                    cluster.body_ids.append(body.id)
                    cluster.body_count = len(cluster.body_ids)

            self._bodies[body.id] = body
            self._total_registrations += 1
            return body

    def remove_body(self, body_id: str) -> bool:
        self._ensure_initialized()

        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return False

            cluster_id = body.cluster_id
            if cluster_id:
                cluster = self._clusters.get(cluster_id)
                if cluster is not None and body_id in cluster.body_ids:
                    cluster.body_ids.remove(body_id)
                    cluster.body_count = len(cluster.body_ids)

            del self._bodies[body_id]
            self._total_removals += 1
            return True

    def update_body_position(
        self,
        body_id: str,
        new_position: Tuple[float, float, float],
        new_velocity: Optional[Tuple[float, float, float]] = None,
    ) -> Optional[SpatialBody]:
        self._ensure_initialized()

        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return None

            body.position = new_position
            if new_velocity is not None:
                body.velocity = new_velocity

            new_cell_index = self._compute_cell_index(new_position)
            new_cluster_id: Optional[str] = None
            if new_cell_index is not None:
                new_cluster_id = self._index_to_cluster.get(new_cell_index)

            old_cluster_id = body.cluster_id
            if new_cluster_id != old_cluster_id:
                if old_cluster_id:
                    old_cluster = self._clusters.get(old_cluster_id)
                    if old_cluster is not None and body_id in old_cluster.body_ids:
                        old_cluster.body_ids.remove(body_id)
                        old_cluster.body_count = len(old_cluster.body_ids)

                if new_cluster_id:
                    new_cluster = self._clusters[new_cluster_id]
                    new_cluster.body_ids.append(body_id)
                    new_cluster.body_count = len(new_cluster.body_ids)
                    body.cluster_id = new_cluster_id
                else:
                    body.cluster_id = ""

                body.bounds_min = (
                    body.bounds_min[0] + (new_position[0] - body.position[0]),
                    body.bounds_min[1] + (new_position[1] - body.position[1]),
                    body.bounds_min[2] + (new_position[2] - body.position[2]),
                )
                body.bounds_max = (
                    body.bounds_max[0] + (new_position[0] - body.position[0]),
                    body.bounds_max[1] + (new_position[1] - body.position[1]),
                    body.bounds_max[2] + (new_position[2] - body.position[2]),
                )

            self._total_position_updates += 1
            return body

    def set_body_sleeping(self, body_id: str, is_sleeping: bool) -> bool:
        self._ensure_initialized()

        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return False
            body.is_sleeping = is_sleeping
            return True

    def get_body(self, body_id: str) -> Optional[SpatialBody]:
        self._ensure_initialized()
        return self._bodies.get(body_id)

    # ------------------------------------------------------------------
    # Cluster Queries
    # ------------------------------------------------------------------

    def get_bodies_in_cluster(self, cluster_id: str) -> List[SpatialBody]:
        self._ensure_initialized()

        with self._lock:
            cluster = self._clusters.get(cluster_id)
            if cluster is None:
                return []
            return [
                self._bodies[bid]
                for bid in cluster.body_ids
                if bid in self._bodies
            ]

    def get_potential_collisions(self, body_id: str) -> List[SpatialBody]:
        self._ensure_initialized()

        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return []

            if body.is_sleeping and body.body_type == BodyType.STATIC:
                return []

            cluster_id = body.cluster_id
            if not cluster_id:
                return []

            cluster = self._clusters.get(cluster_id)
            if cluster is None:
                return []

            candidate_ids: Set[str] = set()
            candidate_ids.update(cluster.body_ids)
            candidate_ids.discard(body_id)

            for neighbor_id in cluster.neighbor_cell_ids:
                neighbor = self._clusters.get(neighbor_id)
                if neighbor is not None:
                    candidate_ids.update(neighbor.body_ids)

            candidates: List[SpatialBody] = []
            for bid in candidate_ids:
                candidate = self._bodies.get(bid)
                if candidate is None:
                    continue
                if candidate.is_sleeping and candidate.body_type == BodyType.STATIC:
                    if body.is_sleeping:
                        continue
                if self._aabb_overlaps(
                    body.bounds_min, body.bounds_max,
                    candidate.bounds_min, candidate.bounds_max,
                ):
                    candidates.append(candidate)

            return candidates

    def get_cluster(self, cluster_id: str) -> Optional[ClusterCell]:
        self._ensure_initialized()
        return self._clusters.get(cluster_id)

    def list_active_clusters(self) -> List[ClusterCell]:
        self._ensure_initialized()
        return [c for c in self._clusters.values() if c.is_active]

    # ------------------------------------------------------------------
    # Spatial Queries
    # ------------------------------------------------------------------

    def query_aabb(
        self,
        bounds_min: Tuple[float, float, float],
        bounds_max: Tuple[float, float, float],
    ) -> List[SpatialBody]:
        self._ensure_initialized()

        with self._lock:
            touched_cell_ids: Set[str] = set()
            for cell_index in self._cells_touching_aabb(bounds_min, bounds_max):
                cluster_id = self._index_to_cluster.get(cell_index)
                if cluster_id:
                    touched_cell_ids.add(cluster_id)

            matched: Set[str] = set()
            for cell_id in touched_cell_ids:
                cluster = self._clusters.get(cell_id)
                if cluster is None:
                    continue
                for bid in cluster.body_ids:
                    if bid in matched:
                        continue
                    body = self._bodies.get(bid)
                    if body is None:
                        continue
                    if self._aabb_overlaps(bounds_min, bounds_max, body.bounds_min, body.bounds_max):
                        matched.add(bid)

            self._total_queries += 1
            return [self._bodies[bid] for bid in matched if bid in self._bodies]

    def query_sphere(
        self,
        center: Tuple[float, float, float],
        radius: float,
    ) -> List[SpatialBody]:
        self._ensure_initialized()

        with self._lock:
            expanded_min = (
                center[0] - radius,
                center[1] - radius,
                center[2] - radius,
            )
            expanded_max = (
                center[0] + radius,
                center[1] + radius,
                center[2] + radius,
            )

            touched_cell_ids: Set[str] = set()
            for cell_index in self._cells_touching_aabb(expanded_min, expanded_max):
                cluster_id = self._index_to_cluster.get(cell_index)
                if cluster_id:
                    touched_cell_ids.add(cluster_id)

            matched: Set[str] = set()
            radius_sq = radius * radius
            for cell_id in touched_cell_ids:
                cluster = self._clusters.get(cell_id)
                if cluster is None:
                    continue
                for bid in cluster.body_ids:
                    if bid in matched:
                        continue
                    body = self._bodies.get(bid)
                    if body is None:
                        continue
                    if self._sphere_overlaps_aabb(center, radius, body.bounds_min, body.bounds_max):
                        matched.add(bid)

            self._total_queries += 1
            return [self._bodies[bid] for bid in matched if bid in self._bodies]

    def query_ray(
        self,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float = float("inf"),
    ) -> QueryResult:
        self._ensure_initialized()

        result = QueryResult(
            query_type=QueryType.RAY_CAST,
            origin=origin,
            direction_or_radius=direction,
        )

        dir_len = math.sqrt(direction[0] ** 2 + direction[1] ** 2 + direction[2] ** 2)
        if dir_len < 1e-10:
            return result

        norm_dir = (
            direction[0] / dir_len,
            direction[1] / dir_len,
            direction[2] / dir_len,
        )

        end = (
            origin[0] + norm_dir[0] * max_distance,
            origin[1] + norm_dir[1] * max_distance,
            origin[2] + norm_dir[2] * max_distance,
        )

        ray_min = (
            min(origin[0], end[0]),
            min(origin[1], end[1]),
            min(origin[2], end[2]),
        )
        ray_max = (
            max(origin[0], end[0]),
            max(origin[1], end[1]),
            max(origin[2], end[2]),
        )

        with self._lock:
            touched_cell_ids: Set[str] = set()
            for cell_index in self._cells_touching_aabb(ray_min, ray_max):
                cluster_id = self._index_to_cluster.get(cell_index)
                if cluster_id:
                    touched_cell_ids.add(cluster_id)

            matched_pairs: List[Tuple[str, float]] = []
            matched_set: Set[str] = set()

            for cell_id in touched_cell_ids:
                cluster = self._clusters.get(cell_id)
                if cluster is None:
                    continue
                for bid in cluster.body_ids:
                    if bid in matched_set:
                        continue
                    body = self._bodies.get(bid)
                    if body is None:
                        continue
                    hit_dist = self._ray_aabb_intersection(
                        origin, norm_dir, body.bounds_min, body.bounds_max
                    )
                    if hit_dist is not None and hit_dist <= max_distance:
                        matched_set.add(bid)
                        matched_pairs.append((bid, hit_dist))

            matched_pairs.sort(key=lambda item: item[1])

            result.matched_body_ids = [bid for bid, _ in matched_pairs]
            if matched_pairs:
                result.distance = matched_pairs[0][1]

            self._total_queries += 1
            return result

    def query_nearest_neighbor(
        self,
        origin: Tuple[float, float, float],
        max_results: int = 10,
    ) -> List[SpatialBody]:
        self._ensure_initialized()

        with self._lock:
            search_radius = self._cell_size
            all_matched: Dict[str, float] = {}
            max_search_radius = max(
                self._world_max[0] - self._world_min[0],
                self._world_max[1] - self._world_min[1],
                self._world_max[2] - self._world_min[2],
            )

            while len(all_matched) < max_results and search_radius <= max_search_radius:
                expanded_min = (
                    origin[0] - search_radius,
                    origin[1] - search_radius,
                    origin[2] - search_radius,
                )
                expanded_max = (
                    origin[0] + search_radius,
                    origin[1] + search_radius,
                    origin[2] + search_radius,
                )

                touched_cell_ids: Set[str] = set()
                for cell_index in self._cells_touching_aabb(expanded_min, expanded_max):
                    cluster_id = self._index_to_cluster.get(cell_index)
                    if cluster_id:
                        touched_cell_ids.add(cluster_id)

                for cell_id in touched_cell_ids:
                    cluster = self._clusters.get(cell_id)
                    if cluster is None:
                        continue
                    for bid in cluster.body_ids:
                        if bid in all_matched:
                            continue
                        body = self._bodies.get(bid)
                        if body is None:
                            continue
                        dist = self._point_to_point_distance(origin, body.position)
                        all_matched[bid] = dist

                search_radius *= 2.0

            sorted_bodies = sorted(all_matched.items(), key=lambda item: item[1])
            result_body_ids = [bid for bid, _ in sorted_bodies[:max_results]]
            self._total_queries += 1
            return [self._bodies[bid] for bid in result_body_ids if bid in self._bodies]

    @staticmethod
    def _ray_aabb_intersection(
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        aabb_min: Tuple[float, float, float],
        aabb_max: Tuple[float, float, float],
    ) -> Optional[float]:
        tmin = float("-inf")
        tmax = float("inf")

        for i in range(3):
            if abs(direction[i]) < 1e-12:
                if origin[i] < aabb_min[i] or origin[i] > aabb_max[i]:
                    return None
            else:
                inv_d = 1.0 / direction[i]
                t1 = (aabb_min[i] - origin[i]) * inv_d
                t2 = (aabb_max[i] - origin[i]) * inv_d
                if t1 > t2:
                    t1, t2 = t2, t1
                tmin = max(tmin, t1)
                tmax = min(tmax, t2)

        if tmin > tmax or tmax < 0:
            return None

        return tmin if tmin >= 0 else tmax

    @staticmethod
    def _ray_sphere_intersection(
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        sphere_center: Tuple[float, float, float],
        radius: float,
    ) -> Optional[float]:
        oc = (
            origin[0] - sphere_center[0],
            origin[1] - sphere_center[1],
            origin[2] - sphere_center[2],
        )
        a = direction[0] ** 2 + direction[1] ** 2 + direction[2] ** 2
        b = 2.0 * (oc[0] * direction[0] + oc[1] * direction[1] + oc[2] * direction[2])
        c = oc[0] ** 2 + oc[1] ** 2 + oc[2] ** 2 - radius ** 2
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None
        sqrt_disc = math.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / (2 * a)
        t2 = (-b + sqrt_disc) / (2 * a)
        if t1 >= 0:
            return t1
        if t2 >= 0:
            return t2
        return None

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        if not self._initialized:
            return {
                "initialized": False,
                "strategy": None,
                "total_bodies": 0,
                "total_clusters": 0,
                "total_registrations": 0,
                "total_removals": 0,
                "total_queries": 0,
                "total_position_updates": 0,
            }

        active_clusters = sum(1 for c in self._clusters.values() if c.is_active)
        total_bodies = len(self._bodies)
        sleeping_bodies = sum(1 for b in self._bodies.values() if b.is_sleeping)
        static_bodies = sum(
            1 for b in self._bodies.values() if b.body_type == BodyType.STATIC
        )
        dynamic_bodies = sum(
            1 for b in self._bodies.values() if b.body_type == BodyType.DYNAMIC
        )
        kinematic_bodies = sum(
            1 for b in self._bodies.values() if b.body_type == BodyType.KINEMATIC
        )
        trigger_bodies = sum(
            1 for b in self._bodies.values() if b.body_type == BodyType.TRIGGER
        )
        orphan_bodies = sum(1 for b in self._bodies.values() if not b.cluster_id)

        max_bodies_in_cell = 0
        min_bodies_in_cell: Optional[int] = None
        total_non_empty_cells = 0

        for cell in self._clusters.values():
            count = cell.body_count
            if count > 0:
                total_non_empty_cells += 1
                max_bodies_in_cell = max(max_bodies_in_cell, count)
                if min_bodies_in_cell is None:
                    min_bodies_in_cell = count
                else:
                    min_bodies_in_cell = min(min_bodies_in_cell, count)

        if min_bodies_in_cell is None:
            min_bodies_in_cell = 0

        avg_bodies_per_cell = (
            total_bodies / total_non_empty_cells if total_non_empty_cells > 0 else 0.0
        )

        world_size = (
            self._world_max[0] - self._world_min[0],
            self._world_max[1] - self._world_min[1],
            self._world_max[2] - self._world_min[2],
        )

        return {
            "initialized": True,
            "strategy": self._strategy.value,
            "world_min": list(self._world_min),
            "world_max": list(self._world_max),
            "world_size": list(world_size),
            "cell_size": self._cell_size,
            "grid_dimensions": list(self._grid_dimensions),
            "total_clusters": len(self._clusters),
            "active_clusters": active_clusters,
            "total_bodies": total_bodies,
            "sleeping_bodies": sleeping_bodies,
            "static_bodies": static_bodies,
            "dynamic_bodies": dynamic_bodies,
            "kinematic_bodies": kinematic_bodies,
            "trigger_bodies": trigger_bodies,
            "orphan_bodies": orphan_bodies,
            "total_registrations": self._total_registrations,
            "total_removals": self._total_removals,
            "total_queries": self._total_queries,
            "total_position_updates": self._total_position_updates,
            "non_empty_cells": total_non_empty_cells,
            "max_bodies_in_cell": max_bodies_in_cell,
            "min_bodies_in_cell": min_bodies_in_cell,
            "avg_bodies_per_cell": round(avg_bodies_per_cell, 3),
        }

    # ------------------------------------------------------------------
    # Bulk Operations
    # ------------------------------------------------------------------

    def update_sleeping_bodies(self, velocity_threshold: float = 0.001) -> int:
        self._ensure_initialized()

        transition_count = 0
        with self._lock:
            for body in self._bodies.values():
                if body.body_type == BodyType.STATIC:
                    continue
                speed = math.sqrt(
                    body.velocity[0] ** 2
                    + body.velocity[1] ** 2
                    + body.velocity[2] ** 2
                )
                if speed < velocity_threshold and not body.is_sleeping:
                    body.is_sleeping = True
                    transition_count += 1
                elif speed >= velocity_threshold and body.is_sleeping:
                    body.is_sleeping = False
                    transition_count += 1

        return transition_count

    def get_cluster_ids_for_region(
        self,
        region_min: Tuple[float, float, float],
        region_max: Tuple[float, float, float],
    ) -> List[str]:
        self._ensure_initialized()

        cluster_ids: List[str] = []
        with self._lock:
            seen: Set[str] = set()
            for cell_index in self._cells_touching_aabb(region_min, region_max):
                cluster_id = self._index_to_cluster.get(cell_index)
                if cluster_id and cluster_id not in seen:
                    seen.add(cluster_id)
                    cluster_ids.append(cluster_id)

        return cluster_ids

    def get_body_count_in_region(
        self,
        region_min: Tuple[float, float, float],
        region_max: Tuple[float, float, float],
    ) -> int:
        self._ensure_initialized()

        cluster_ids = self.get_cluster_ids_for_region(region_min, region_max)
        total = 0
        with self._lock:
            for cid in cluster_ids:
                cluster = self._clusters.get(cid)
                if cluster is not None:
                    total += len(cluster.body_ids)
        return total

    def transfer_body(self, body_id: str, target_cluster_id: str) -> bool:
        self._ensure_initialized()

        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return False
            target_cluster = self._clusters.get(target_cluster_id)
            if target_cluster is None:
                return False

            old_cluster_id = body.cluster_id
            if old_cluster_id:
                old_cluster = self._clusters.get(old_cluster_id)
                if old_cluster is not None and body_id in old_cluster.body_ids:
                    old_cluster.body_ids.remove(body_id)
                    old_cluster.body_count = len(old_cluster.body_ids)

            body.cluster_id = target_cluster_id
            target_cluster.body_ids.append(body_id)
            target_cluster.body_count = len(target_cluster.body_ids)
            body.position = (
                (target_cluster.bounds_min[0] + target_cluster.bounds_max[0]) / 2,
                (target_cluster.bounds_min[1] + target_cluster.bounds_max[1]) / 2,
                (target_cluster.bounds_min[2] + target_cluster.bounds_max[2]) / 2,
            )
            return True

    def clear_all(self) -> int:
        self._ensure_initialized()

        with self._lock:
            count = len(self._bodies)
            self._bodies.clear()
            for cell in self._clusters.values():
                cell.body_ids.clear()
                cell.body_count = 0
            return count

    def reset(self) -> None:
        with self._lock:
            self._bodies.clear()
            self._clusters.clear()
            self._index_to_cluster.clear()
            self._grid_dimensions = (0, 0, 0)
            self._cell_size = 1.0
            self._strategy = PartitionStrategy.UNIFORM_GRID
            self._world_min = (0.0, 0.0, 0.0)
            self._world_max = (0.0, 0.0, 0.0)
            self._initialized = False
            self._total_registrations = 0
            self._total_removals = 0
            self._total_queries = 0
            self._total_position_updates = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError(
                "SpatialCluster not initialized. Call initialize_grid() first."
            )

    def is_initialized(self) -> bool:
        return self._initialized

    def get_grid_dimensions(self) -> Tuple[int, int, int]:
        return self._grid_dimensions

    def get_cell_size(self) -> float:
        return self._cell_size

    def get_strategy(self) -> PartitionStrategy:
        return self._strategy


def get_spatial_cluster() -> SpatialCluster:
    return SpatialCluster.get_instance()