"""
Pathfinding System - A* pathfinding on grid and navigation mesh.

Architecture:
    PathfindingSystem/
    |-- NavigationGrid (grid-based world representation)
    |-- NavMesh (triangle-based navigation mesh)
    |-- PathNode (A* search node)
    |-- NavigationPath (computed path result)

Provides grid-based A* with multiple heuristic methods and navmesh-based
triangle-graph pathfinding. Supports path smoothing, caching, and cost
multiplier per cell for terrain-aware navigation.
"""

from __future__ import annotations

import heapq
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class HeuristicMethod(Enum):
    MANHATTAN = "manhattan"
    EUCLIDEAN = "euclidean"
    CHEBYSHEV = "chebyshev"
    OCTILE = "octile"
    DIJKSTRA = "dijkstra"


class AreaType(Enum):
    WALKABLE = "walkable"
    SWIM = "swim"
    FLY = "fly"
    CLIMB = "climb"
    JUMP = "jump"
    OBSTACLE = "obstacle"


class SmoothingMethod(Enum):
    NONE = "none"
    SIMPLE = "simple"
    CHAIKIN = "chaikin"
    CATMULL_ROM = "catmull_rom"


@dataclass
class GridCell:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    x: int = 0
    y: int = 0
    is_walkable: bool = True
    cost_multiplier: float = 1.0
    tags: List[str] = field(default_factory=list)


@dataclass
class NavigationGrid:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    width: int = 0
    height: int = 0
    cell_size: float = 1.0
    origin_x: float = 0.0
    origin_y: float = 0.0
    cells: Dict[str, GridCell] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class PathNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    x: int = 0
    y: int = 0
    world_x: float = 0.0
    world_y: float = 0.0
    cost_so_far: float = 0.0
    estimated_total: float = 0.0


@dataclass
class NavigationPath:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    grid_id: str = ""
    start_x: int = 0
    start_y: int = 0
    end_x: int = 0
    end_y: int = 0
    nodes: List[PathNode] = field(default_factory=list)
    total_cost: float = 0.0
    algorithm: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class NavMeshTriangle:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    neighbors: List[str] = field(default_factory=list)
    area_type: str = "walkable"
    cost_multiplier: float = 1.0


@dataclass
class NavMesh:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    triangles: Dict[str, NavMeshTriangle] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class PathfindingSystem:
    _instance: Optional["PathfindingSystem"] = None
    _lock: threading.RLock = threading.RLock()

    NEIGHBOR_DIRECTIONS_4 = [(0, -1), (1, 0), (0, 1), (-1, 0)]

    NEIGHBOR_DIRECTIONS_8 = [
        (0, -1), (1, -1), (1, 0), (1, 1),
        (0, 1), (-1, 1), (-1, 0), (-1, -1),
    ]

    DIAGONAL_PAIRS = {
        (1, -1): ((1, 0), (0, -1)),
        (1, 1): ((1, 0), (0, 1)),
        (-1, 1): ((-1, 0), (0, 1)),
        (-1, -1): ((-1, 0), (0, -1)),
    }

    def __init__(self) -> None:
        self._grids: Dict[str, NavigationGrid] = {}
        self._nav_meshes: Dict[str, NavMesh] = {}
        self._paths: Dict[str, NavigationPath] = {}
        self._grid_count: int = 0
        self._mesh_count: int = 0
        self._path_count: int = 0
        self._path_cache: Dict[str, NavigationPath] = {}

    @classmethod
    def get_instance(cls) -> "PathfindingSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Grid Management
    # ------------------------------------------------------------------

    def create_grid(
        self,
        name: str,
        width: int,
        height: int,
        cell_size: float = 1.0,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
    ) -> str:
        grid = NavigationGrid(
            name=name,
            width=width,
            height=height,
            cell_size=cell_size,
            origin_x=origin_x,
            origin_y=origin_y,
        )
        for y in range(height):
            for x in range(width):
                cell = GridCell(x=x, y=y, is_walkable=True, cost_multiplier=1.0)
                key = f"{x},{y}"
                grid.cells[key] = cell
        self._grids[grid.id] = grid
        self._grid_count += 1
        return grid.id

    def set_cell(
        self,
        grid_id: str,
        x: int,
        y: int,
        is_walkable: bool,
        cost_multiplier: float = 1.0,
        tags: Optional[List[str]] = None,
    ) -> bool:
        grid = self._grids.get(grid_id)
        if grid is None:
            return False
        if x < 0 or x >= grid.width or y < 0 or y >= grid.height:
            return False
        key = f"{x},{y}"
        cell = grid.cells.get(key)
        if cell is None:
            cell = GridCell(x=x, y=y)
            grid.cells[key] = cell
        cell.is_walkable = is_walkable
        cell.cost_multiplier = cost_multiplier
        if tags is not None:
            cell.tags = tags
        self._path_cache.clear()
        return True

    def set_cell_region(
        self,
        grid_id: str,
        min_x: int,
        min_y: int,
        max_x: int,
        max_y: int,
        is_walkable: bool,
    ) -> int:
        grid = self._grids.get(grid_id)
        if grid is None:
            return 0
        count = 0
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if 0 <= x < grid.width and 0 <= y < grid.height:
                    key = f"{x},{y}"
                    cell = grid.cells.get(key)
                    if cell is None:
                        cell = GridCell(x=x, y=y)
                        grid.cells[key] = cell
                    cell.is_walkable = is_walkable
                    count += 1
        if count > 0:
            self._path_cache.clear()
        return count

    # ------------------------------------------------------------------
    # Coordinate Conversion
    # ------------------------------------------------------------------

    def world_to_grid(
        self, grid_id: str, world_x: float, world_y: float
    ) -> Tuple[int, int]:
        grid = self._grids.get(grid_id)
        if grid is None or grid.cell_size <= 0:
            return (0, 0)
        gx = int((world_x - grid.origin_x) / grid.cell_size)
        gy = int((world_y - grid.origin_y) / grid.cell_size)
        return (gx, gy)

    def grid_to_world(
        self, grid_id: str, grid_x: int, grid_y: int
    ) -> Tuple[float, float]:
        grid = self._grids.get(grid_id)
        if grid is None:
            return (0.0, 0.0)
        wx = grid.origin_x + (grid_x + 0.5) * grid.cell_size
        wy = grid.origin_y + (grid_y + 0.5) * grid.cell_size
        return (wx, wy)

    # ------------------------------------------------------------------
    # Heuristic Functions
    # ------------------------------------------------------------------

    @staticmethod
    def _heuristic(
        dx: float, dy: float, method: HeuristicMethod
    ) -> float:
        if method == HeuristicMethod.MANHATTAN:
            return dx + dy
        elif method == HeuristicMethod.EUCLIDEAN:
            return math.sqrt(dx * dx + dy * dy)
        elif method == HeuristicMethod.CHEBYSHEV:
            return max(dx, dy)
        elif method == HeuristicMethod.OCTILE:
            return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)
        elif method == HeuristicMethod.DIJKSTRA:
            return 0.0
        return math.sqrt(dx * dx + dy * dy)

    # ------------------------------------------------------------------
    # A* Pathfinding
    # ------------------------------------------------------------------

    def find_path(
        self,
        grid_id: str,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        heuristic: HeuristicMethod = HeuristicMethod.EUCLIDEAN,
    ) -> NavigationPath:
        path = NavigationPath(
            grid_id=grid_id,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            algorithm=f"astar_{heuristic.value}",
        )

        grid = self._grids.get(grid_id)
        if grid is None:
            return path

        if start_x == end_x and start_y == end_y:
            wx, wy = self.grid_to_world(grid_id, start_x, start_y)
            node = PathNode(x=start_x, y=start_y, world_x=wx, world_y=wy)
            path.nodes = [node]
            self._paths[path.id] = path
            self._path_count += 1
            return path

        start_key = f"{start_x},{start_y}"
        end_key = f"{end_x},{end_y}"

        start_cell = grid.cells.get(start_key)
        end_cell = grid.cells.get(end_key)
        if start_cell is None or end_cell is None:
            return path
        if not end_cell.is_walkable:
            return path
        if not start_cell.is_walkable:
            start_cell.is_walkable = True

        open_set: List[Tuple[float, int, int, int]] = []
        tie_breaker = 0

        g_score: Dict[Tuple[int, int], float] = {}
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}

        start_h = self._heuristic(
            abs(end_x - start_x), abs(end_y - start_y), heuristic
        )
        g_score[(start_x, start_y)] = 0.0
        heapq.heappush(open_set, (start_h, tie_breaker, start_x, start_y))
        tie_breaker += 1
        came_from[(start_x, start_y)] = None

        closed_set: Set[Tuple[int, int]] = set()

        while open_set:
            _, _, cx, cy = heapq.heappop(open_set)

            if (cx, cy) in closed_set:
                continue

            if cx == end_x and cy == end_y:
                break

            closed_set.add((cx, cy))

            for dx, dy in self.NEIGHBOR_DIRECTIONS_8:
                nx, ny = cx + dx, cy + dy

                if (nx, ny) in closed_set:
                    continue

                if nx < 0 or nx >= grid.width or ny < 0 or ny >= grid.height:
                    continue

                nkey = f"{nx},{ny}"
                neighbor_cell = grid.cells.get(nkey)
                if neighbor_cell is None or not neighbor_cell.is_walkable:
                    continue

                if (dx, dy) in self.DIAGONAL_PAIRS:
                    ax, ay = self.DIAGONAL_PAIRS[(dx, dy)][0]
                    bx, by = self.DIAGONAL_PAIRS[(dx, dy)][1]
                    ckey_a = f"{cx + ax},{cy + ay}"
                    ckey_b = f"{cx + bx},{cy + by}"
                    cell_a = grid.cells.get(ckey_a)
                    cell_b = grid.cells.get(ckey_b)
                    if cell_a is None or not cell_a.is_walkable:
                        continue
                    if cell_b is None or not cell_b.is_walkable:
                        continue

                move_cost = math.sqrt(dx * dx + dy * dy) * neighbor_cell.cost_multiplier
                tentative_g = g_score[(cx, cy)] + move_cost

                existing_g = g_score.get((nx, ny))
                if existing_g is None or tentative_g < existing_g:
                    g_score[(nx, ny)] = tentative_g
                    came_from[(nx, ny)] = (cx, cy)
                    h = self._heuristic(
                        abs(end_x - nx), abs(end_y - ny), heuristic
                    )
                    f = tentative_g + h
                    heapq.heappush(open_set, (f, tie_breaker, nx, ny))
                    tie_breaker += 1

        if (end_x, end_y) not in came_from:
            self._paths[path.id] = path
            self._path_count += 1
            return path

        node_coords: List[Tuple[int, int]] = []
        current: Optional[Tuple[int, int]] = (end_x, end_y)
        while current is not None:
            node_coords.append(current)
            current = came_from.get(current)

        node_coords.reverse()
        total_cost = g_score.get((end_x, end_y), 0.0)

        path_nodes: List[PathNode] = []
        for nx, ny in node_coords:
            wx, wy = self.grid_to_world(grid_id, nx, ny)
            node = PathNode(x=nx, y=ny, world_x=wx, world_y=wy)
            path_nodes.append(node)

        path.nodes = path_nodes
        path.total_cost = total_cost

        cache_key = f"{grid_id}:{start_x},{start_y}:{end_x},{end_y}"
        self._path_cache[cache_key] = path

        self._paths[path.id] = path
        self._path_count += 1
        return path

    # ------------------------------------------------------------------
    # Path Smoothing
    # ------------------------------------------------------------------

    def smooth_path(self, path_id: str, method: SmoothingMethod) -> NavigationPath:
        path = self._paths.get(path_id)
        if path is None:
            return NavigationPath()
        if method == SmoothingMethod.NONE or len(path.nodes) <= 2:
            return path

        grid = self._grids.get(path.grid_id)
        if grid is None:
            return path

        if method == SmoothingMethod.SIMPLE:
            path.nodes = self._smooth_simple(path.nodes, grid)
        elif method == SmoothingMethod.CHAIKIN:
            path.nodes = self._smooth_chaikin(path.nodes, grid)
        elif method == SmoothingMethod.CATMULL_ROM:
            path.nodes = self._smooth_catmull_rom(path.nodes, grid)

        path.total_cost = self._compute_path_cost(path.nodes)
        return path

    def _smooth_simple(
        self, nodes: List[PathNode], grid: NavigationGrid
    ) -> List[PathNode]:
        if len(nodes) <= 2:
            return nodes
        result: List[PathNode] = [nodes[0]]
        anchor = 0
        while anchor < len(nodes) - 1:
            for i in range(len(nodes) - 1, anchor, -1):
                if self._line_of_sight(nodes[anchor], nodes[i], grid):
                    result.append(nodes[i])
                    anchor = i
                    break
            else:
                anchor += 1
                result.append(nodes[anchor])
        return result

    def _line_of_sight(
        self, a: PathNode, b: PathNode, grid: NavigationGrid
    ) -> bool:
        x0, y0 = float(a.x), float(a.y)
        x1, y1 = float(b.x), float(b.y)
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        steps = int(max(dx, dy))
        if steps == 0:
            return True
        for i in range(1, steps):
            t = i / steps
            cx = int(round(x0 + t * (x1 - x0)))
            cy = int(round(y0 + t * (y1 - y0)))
            if cx == a.x and cy == a.y:
                continue
            if cx == b.x and cy == b.y:
                continue
            key = f"{cx},{cy}"
            cell = grid.cells.get(key)
            if cell is None or not cell.is_walkable:
                return False
        return True

    def _smooth_chaikin(
        self, nodes: List[PathNode], grid: NavigationGrid
    ) -> List[PathNode]:
        if len(nodes) < 3:
            return list(nodes)
        ratio = 0.25
        for _ in range(2):
            if len(nodes) < 3:
                break
            new_nodes: List[PathNode] = [nodes[0]]
            for i in range(len(nodes) - 1):
                p0 = nodes[i]
                p1 = nodes[i + 1]
                qx = p0.world_x + ratio * (p1.world_x - p0.world_x)
                qy = p0.world_y + ratio * (p1.world_y - p0.world_y)
                rx = p0.world_x + (1 - ratio) * (p1.world_x - p0.world_x)
                ry = p0.world_y + (1 - ratio) * (p1.world_y - p0.world_y)
                if i < len(nodes) - 2 or True:
                    new_nodes.append(PathNode(
                        x=p0.x, y=p0.y, world_x=qx, world_y=qy
                    ))
                new_nodes.append(PathNode(
                    x=p1.x, y=p1.y, world_x=rx, world_y=ry
                ))
            new_nodes.append(nodes[-1])
            nodes = new_nodes
        return nodes

    def _smooth_catmull_rom(
        self, nodes: List[PathNode], grid: NavigationGrid
    ) -> List[PathNode]:
        if len(nodes) < 4:
            return list(nodes)
        result: List[PathNode] = [nodes[0]]
        segments = len(nodes) - 1
        for i in range(segments):
            p0 = nodes[max(i - 1, 0)]
            p1 = nodes[i]
            p2 = nodes[min(i + 1, len(nodes) - 1)]
            p3 = nodes[min(i + 2, len(nodes) - 1)]
            for t_idx in range(1, 5):
                t = t_idx / 5.0
                tt = t * t
                ttt = tt * t
                wx = 0.5 * (
                    (2 * p1.world_x)
                    + (-p0.world_x + p2.world_x) * t
                    + (2 * p0.world_x - 5 * p1.world_x + 4 * p2.world_x - p3.world_x) * tt
                    + (-p0.world_x + 3 * p1.world_x - 3 * p2.world_x + p3.world_x) * ttt
                )
                wy = 0.5 * (
                    (2 * p1.world_y)
                    + (-p0.world_y + p2.world_y) * t
                    + (2 * p0.world_y - 5 * p1.world_y + 4 * p2.world_y - p3.world_y) * tt
                    + (-p0.world_y + 3 * p1.world_y - 3 * p2.world_y + p3.world_y) * ttt
                )
                result.append(PathNode(
                    x=p1.x, y=p1.y, world_x=wx, world_y=wy
                ))
        result.append(nodes[-1])
        return result

    def _compute_path_cost(self, nodes: List[PathNode]) -> float:
        total = 0.0
        for i in range(1, len(nodes)):
            dx = nodes[i].world_x - nodes[i - 1].world_x
            dy = nodes[i].world_y - nodes[i - 1].world_y
            total += math.sqrt(dx * dx + dy * dy)
        return total

    # ------------------------------------------------------------------
    # Path Queries
    # ------------------------------------------------------------------

    def get_path_length(self, path_id: str) -> float:
        path = self._paths.get(path_id)
        if path is None:
            return 0.0
        return self._compute_path_cost(path.nodes)

    def is_reachable(
        self,
        grid_id: str,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
    ) -> bool:
        cached = self.get_cached_path(grid_id, start_x, start_y, end_x, end_y)
        if cached is not None:
            return len(cached.nodes) > 0

        path = self.find_path(
            grid_id, start_x, start_y, end_x, end_y,
            heuristic=HeuristicMethod.EUCLIDEAN,
        )
        return len(path.nodes) > 0

    # ------------------------------------------------------------------
    # Path Cache
    # ------------------------------------------------------------------

    def get_cached_path(
        self,
        grid_id: str,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
    ) -> Optional[NavigationPath]:
        cache_key = f"{grid_id}:{start_x},{start_y}:{end_x},{end_y}"
        return self._path_cache.get(cache_key)

    def clear_cache(self) -> None:
        self._path_cache.clear()

    # ------------------------------------------------------------------
    # NavMesh Management
    # ------------------------------------------------------------------

    def create_nav_mesh(self, name: str) -> str:
        mesh = NavMesh(name=name)
        self._nav_meshes[mesh.id] = mesh
        self._mesh_count += 1
        return mesh.id

    def add_triangle(
        self,
        mesh_id: str,
        vertices: List[Tuple[float, float]],
        area_type: str = "walkable",
        cost_multiplier: float = 1.0,
    ) -> Optional[str]:
        mesh = self._nav_meshes.get(mesh_id)
        if mesh is None:
            return None
        if len(vertices) != 3:
            return None
        triangle = NavMeshTriangle(
            vertices=vertices,
            area_type=area_type,
            cost_multiplier=cost_multiplier,
        )
        mesh.triangles[triangle.id] = triangle
        return triangle.id

    def build_nav_mesh_neighbors(self, mesh_id: str) -> int:
        mesh = self._nav_meshes.get(mesh_id)
        if mesh is None:
            return 0

        for tri in mesh.triangles.values():
            tri.neighbors = []

        tri_ids = list(mesh.triangles.keys())
        count = 0
        for i in range(len(tri_ids)):
            for j in range(i + 1, len(tri_ids)):
                a = mesh.triangles[tri_ids[i]]
                b = mesh.triangles[tri_ids[j]]
                if self._triangles_share_edge(a.vertices, b.vertices):
                    a.neighbors.append(b.id)
                    b.neighbors.append(a.id)
                    count += 2

        return count

    @staticmethod
    def _triangles_share_edge(
        a: List[Tuple[float, float]],
        b: List[Tuple[float, float]],
    ) -> bool:
        shared = 0
        for va in a:
            for vb in b:
                dx = va[0] - vb[0]
                dy = va[1] - vb[1]
                if math.sqrt(dx * dx + dy * dy) < 0.001:
                    shared += 1
                    if shared >= 2:
                        return True
        return False

    # ------------------------------------------------------------------
    # NavMesh Pathfinding
    # ------------------------------------------------------------------

    def find_path_on_mesh(
        self,
        mesh_id: str,
        start_pos: Tuple[float, float],
        end_pos: Tuple[float, float],
        area_types: Optional[List[str]] = None,
    ) -> NavigationPath:
        path = NavigationPath(
            grid_id=mesh_id,
            start_x=0,
            start_y=0,
            end_x=0,
            end_y=0,
            algorithm="astar_navmesh",
        )

        mesh = self._nav_meshes.get(mesh_id)
        if mesh is None or len(mesh.triangles) == 0:
            return path

        valid_types = set(area_types) if area_types else {"walkable"}

        start_tri = self._locate_triangle(mesh, start_pos)
        end_tri = self._locate_triangle(mesh, end_pos)

        if start_tri is None or end_tri is None:
            return path

        if start_tri.area_type not in valid_types or end_tri.area_type not in valid_types:
            return path

        if start_tri.id == end_tri.id:
            node_start = PathNode(x=0, y=0, world_x=start_pos[0], world_y=start_pos[1])
            node_end = PathNode(x=0, y=0, world_x=end_pos[0], world_y=end_pos[1])
            path.nodes = [node_start, node_end]
            self._paths[path.id] = path
            self._path_count += 1
            return path

        open_set: List[Tuple[float, int, str]] = []
        tie_breaker = 0

        g_score: Dict[str, float] = {}
        came_from: Dict[str, Optional[str]] = {}

        sh = self._triangle_heuristic(start_tri, end_tri)
        g_score[start_tri.id] = 0.0
        heapq.heappush(open_set, (sh, tie_breaker, start_tri.id))
        tie_breaker += 1
        came_from[start_tri.id] = None

        closed_set: Set[str] = set()

        while open_set:
            _, _, current_id = heapq.heappop(open_set)

            if current_id in closed_set:
                continue
            if current_id == end_tri.id:
                break

            closed_set.add(current_id)
            current_tri = mesh.triangles.get(current_id)
            if current_tri is None:
                continue

            for neighbor_id in current_tri.neighbors:
                if neighbor_id in closed_set:
                    continue
                neighbor = mesh.triangles.get(neighbor_id)
                if neighbor is None:
                    continue
                if neighbor.area_type not in valid_types:
                    continue

                edge_cost = self._triangle_distance(
                    current_tri, neighbor
                ) * neighbor.cost_multiplier

                tentative_g = g_score[current_id] + edge_cost
                existing_g = g_score.get(neighbor_id)
                if existing_g is None or tentative_g < existing_g:
                    g_score[neighbor_id] = tentative_g
                    came_from[neighbor_id] = current_id
                    h = self._triangle_heuristic(neighbor, end_tri)
                    heapq.heappush(open_set, (tentative_g + h, tie_breaker, neighbor_id))
                    tie_breaker += 1

        if end_tri.id not in came_from:
            self._paths[path.id] = path
            self._path_count += 1
            return path

        tri_sequence: List[str] = []
        current: Optional[str] = end_tri.id
        while current is not None:
            tri_sequence.append(current)
            current = came_from.get(current)
        tri_sequence.reverse()

        path_nodes: List[PathNode] = []
        for i, tid in enumerate(tri_sequence):
            tri = mesh.triangles.get(tid)
            if tri is None:
                continue
            if i == 0:
                cx, cy = start_pos
            elif i == len(tri_sequence) - 1:
                cx, cy = end_pos
            else:
                cx = sum(v[0] for v in tri.vertices) / 3.0
                cy = sum(v[1] for v in tri.vertices) / 3.0
            path_nodes.append(PathNode(x=0, y=0, world_x=cx, world_y=cy))

        path.nodes = path_nodes
        path.total_cost = self._compute_path_cost(path_nodes)
        self._paths[path.id] = path
        self._path_count += 1
        return path

    @staticmethod
    def _locate_triangle(
        mesh: NavMesh, pos: Tuple[float, float]
    ) -> Optional[NavMeshTriangle]:
        px, py = pos
        for tri in mesh.triangles.values():
            if PathfindingSystem._point_in_triangle(px, py, tri.vertices):
                return tri
        best_tri = None
        best_dist = float("inf")
        for tri in mesh.triangles.values():
            cx = sum(v[0] for v in tri.vertices) / 3.0
            cy = sum(v[1] for v in tri.vertices) / 3.0
            d = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
            if d < best_dist:
                best_dist = d
                best_tri = tri
        return best_tri

    @staticmethod
    def _point_in_triangle(
        px: float, py: float, vertices: List[Tuple[float, float]]
    ) -> bool:
        if len(vertices) != 3:
            return False
        (x0, y0), (x1, y1), (x2, y2) = vertices
        d1 = (px - x1) * (y0 - y1) - (x0 - x1) * (py - y1)
        d2 = (px - x2) * (y1 - y2) - (x1 - x2) * (py - y2)
        d3 = (px - x0) * (y2 - y0) - (x2 - x0) * (py - y0)
        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (has_neg and has_pos)

    @staticmethod
    def _triangle_heuristic(
        a: NavMeshTriangle, b: NavMeshTriangle
    ) -> float:
        ax = sum(v[0] for v in a.vertices) / 3.0
        ay = sum(v[1] for v in a.vertices) / 3.0
        bx = sum(v[0] for v in b.vertices) / 3.0
        by = sum(v[1] for v in b.vertices) / 3.0
        return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)

    @staticmethod
    def _triangle_distance(
        a: NavMeshTriangle, b: NavMeshTriangle
    ) -> float:
        ax = sum(v[0] for v in a.vertices) / 3.0
        ay = sum(v[1] for v in a.vertices) / 3.0
        bx = sum(v[0] for v in b.vertices) / 3.0
        by = sum(v[1] for v in b.vertices) / 3.0
        return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, int]:
        return {
            "grid_count": self._grid_count,
            "mesh_count": self._mesh_count,
            "path_count": self._path_count,
            "cache_size": len(self._path_cache),
        }


def get_pathfinding_system() -> PathfindingSystem:
    return PathfindingSystem.get_instance()


get_pathfinding = get_pathfinding_system