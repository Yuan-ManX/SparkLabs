"""
SparkLabs Engine - Pathfinding System

A* grid-based pathfinding with configurable heuristics and
obstacle avoidance. Designed for AI-generated NPC movement
and navigation within game worlds.

Architecture:
  PathfindingSystem
    |-- GridMap (walkable/blocked cell representation)
    |-- AStarSearcher (priority queue + heuristic)
    |-- PathSmoother (reduce zigzag in raw paths)
    |-- NavigationAgent (steering behaviors on path)

Heuristics:
  - MANHATTAN: |dx| + |dy| (grid with 4-way movement)
  - CHEBYSHEV: max(|dx|, |dy|) (grid with 8-way movement)
  - EUCLIDEAN: sqrt(dx² + dy²) (any direction)

Usage:
    pf = PathfindingSystem(grid_width=100, grid_height=100, cell_size=32)
    pf.set_blocked(10, 12, True)  # mark an obstacle
    path = pf.find_path((0, 0), (20, 30))
    if path:
        for node in path:
            print(f"Move to ({node[0]}, {node[1]})")
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class HeuristicType(Enum):
    MANHATTAN = "manhattan"
    CHEBYSHEV = "chebyshev"
    EUCLIDEAN = "euclidean"
    OCTILE = "octile"


@dataclass
class PathNode:
    x: int = 0
    y: int = 0
    g: float = 0.0
    h: float = 0.0
    parent: Optional[PathNode] = None

    @property
    def f(self) -> float:
        return self.g + self.h

    def __lt__(self, other: PathNode) -> bool:
        return self.f < other.f

    @property
    def position(self) -> Tuple[int, int]:
        return (self.x, self.y)


class PathfindingSystem:
    """
    A* pathfinding system for grid-based navigation.

    Builds a grid representation with walkable/blocked cells,
    performs A* search with configurable heuristics, and
    returns smoothed paths for natural movement.

    Usage:
        pf = PathfindingSystem(100, 100, 32)
        pf.set_blocked(15, 20, True)
        path = pf.find_path((5, 5), (45, 60))
        distances = pf.compute_distances((10, 10))
    """

    def __init__(
        self,
        grid_width: int = 100,
        grid_height: int = 100,
        cell_size: float = 32.0,
        heuristic: HeuristicType = HeuristicType.OCTILE,
        diagonal_cost: float = math.sqrt(2),
    ):
        self._width = grid_width
        self._height = grid_height
        self._cell_size = cell_size
        self._heuristic = heuristic
        self._diagonal_cost = diagonal_cost
        self._blocked: List[List[bool]] = [
            [False] * grid_height for _ in range(grid_width)
        ]
        self._weights: List[List[float]] = [
            [1.0] * grid_height for _ in range(grid_width)
        ]
        self._search_count: int = 0
        self._total_nodes_explored: int = 0

    def set_blocked(self, x: int, y: int, blocked: bool = True) -> None:
        if 0 <= x < self._width and 0 <= y < self._height:
            self._blocked[x][y] = blocked

    def set_weight(self, x: int, y: int, weight: float = 1.0) -> None:
        if 0 <= x < self._width and 0 <= y < self._height:
            self._weights[x][y] = max(0.1, weight)

    def is_blocked(self, x: int, y: int) -> bool:
        if 0 <= x < self._width and 0 <= y < self._height:
            return self._blocked[x][y]
        return True

    def block_area(
        self, x1: int, y1: int, x2: int, y2: int, blocked: bool = True,
    ) -> None:
        for x in range(max(0, x1), min(self._width, x2 + 1)):
            for y in range(max(0, y1), min(self._height, y2 + 1)):
                self._blocked[x][y] = blocked

    def find_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        allow_diagonal: bool = True,
    ) -> Optional[List[Tuple[int, int]]]:
        self._search_count += 1

        sx, sy = start
        gx, gy = goal

        if not self._in_bounds(sx, sy) or not self._in_bounds(gx, gy):
            return None
        if self._blocked[sx][sy] or self._blocked[gx][gy]:
            return None

        open_list: List[Tuple[float, int, PathNode]] = []
        closed: Set[Tuple[int, int]] = set()
        node_grid: Dict[Tuple[int, int], PathNode] = {}

        start_node = PathNode(x=sx, y=sy, g=0.0,
                              h=self._compute_h(sx, sy, gx, gy))
        heapq.heappush(open_list, (start_node.f, id(start_node), start_node))
        node_grid[(sx, sy)] = start_node

        directions = [
            (0, 1), (1, 0), (0, -1), (-1, 0),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        ]
        dir_count = 8 if allow_diagonal else 4

        while open_list:
            _, _, current = heapq.heappop(open_list)
            nodes_explored = 1
            self._total_nodes_explored += 1

            if (current.x, current.y) in closed:
                continue

            if current.x == gx and current.y == gy:
                return self._reconstruct_path(current)

            closed.add((current.x, current.y))

            for i in range(dir_count):
                dx, dy = directions[i]
                nx, ny = current.x + dx, current.y + dy

                if not self._in_bounds(nx, ny) or (nx, ny) in closed:
                    continue
                if self._blocked[nx][ny]:
                    continue

                if i >= 4:
                    cost = self._diagonal_cost
                else:
                    cost = 1.0

                cost *= self._weights[nx][ny]
                new_g = current.g + cost

                existing = node_grid.get((nx, ny))
                if existing and existing.g <= new_g:
                    continue

                h = self._compute_h(nx, ny, gx, gy)
                neighbor = PathNode(x=nx, y=ny, g=new_g, h=h, parent=current)
                node_grid[(nx, ny)] = neighbor
                heapq.heappush(open_list, (neighbor.f, id(neighbor), neighbor))

        return None

    def compute_distances(
        self, source: Tuple[int, int], max_distance: float = float('inf'),
    ) -> Dict[Tuple[int, int], float]:
        sx, sy = source
        if not self._in_bounds(sx, sy) or self._blocked[sx][sy]:
            return {}

        distances: Dict[Tuple[int, int], float] = {(sx, sy): 0.0}
        frontier: List[Tuple[float, int, int]] = [(0.0, sx, sy)]
        visited: Set[Tuple[int, int]] = set()

        while frontier:
            dist, cx, cy = heapq.heappop(frontier)
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))

            for dx, dy in [(0,1),(1,0),(0,-1),(-1,0)]:
                nx, ny = cx + dx, cy + dy
                if not self._in_bounds(nx, ny) or self._blocked[nx][ny]:
                    continue
                nd = dist + 1.0
                if nd > max_distance:
                    continue
                prev = distances.get((nx, ny), float('inf'))
                if nd < prev:
                    distances[(nx, ny)] = nd
                    heapq.heappush(frontier, (nd, nx, ny))

        return distances

    def world_to_grid(self, wx: float, wy: float) -> Tuple[int, int]:
        return (int(wx // self._cell_size), int(wy // self._cell_size))

    def grid_to_world(self, gx: int, gy: int) -> Tuple[float, float]:
        return (
            gx * self._cell_size + self._cell_size / 2,
            gy * self._cell_size + self._cell_size / 2,
        )

    def smooth_path(self, path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        if len(path) <= 2:
            return list(path)

        smoothed = [path[0]]
        i = 0
        while i < len(path) - 1:
            best = i + 1
            for j in range(i + 2, min(i + 6, len(path))):
                if self._line_of_sight(path[i], path[j]):
                    best = j
            smoothed.append(path[best])
            i = best
        return smoothed

    def _line_of_sight(
        self, a: Tuple[int, int], b: Tuple[int, int],
    ) -> bool:
        x1, y1 = a
        x2, y2 = b
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x2 > x1 else -1
        sy = 1 if y2 > y1 else -1
        err = dx - dy

        cx, cy = x1, y1
        while cx != x2 or cy != y2:
            if self._blocked[cx][cy]:
                return False
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy
        return True

    def get_stats(self) -> dict:
        blocked_cells = sum(
            1 for x in range(self._width) for y in range(self._height)
            if self._blocked[x][y]
        )
        return {
            "grid_size": f"{self._width}x{self._height}",
            "cell_size": self._cell_size,
            "blocked_cells": blocked_cells,
            "blocked_pct": round(
                blocked_cells / max(self._width * self._height, 1) * 100, 1,
            ),
            "searches": self._search_count,
            "avg_nodes": round(
                self._total_nodes_explored / max(self._search_count, 1), 1,
            ),
            "heuristic": self._heuristic.value,
        }

    def clear(self) -> None:
        self._blocked = [[False] * self._height for _ in range(self._width)]
        self._weights = [[1.0] * self._height for _ in range(self._width)]
        self._search_count = 0
        self._total_nodes_explored = 0

    def resize(self, new_width: int, new_height: int) -> None:
        self._blocked = [[False] * new_height for _ in range(new_width)]
        self._weights = [[1.0] * new_height for _ in range(new_width)]
        self._width = new_width
        self._height = new_height

    @staticmethod
    def _reconstruct_path(node: PathNode) -> List[Tuple[int, int]]:
        path: List[Tuple[int, int]] = []
        current: Optional[PathNode] = node
        while current:
            path.append((current.x, current.y))
            current = current.parent
        path.reverse()
        return path

    def _compute_h(self, x: int, y: int, gx: int, gy: int) -> float:
        dx = abs(x - gx)
        dy = abs(y - gy)
        if self._heuristic == HeuristicType.MANHATTAN:
            return float(dx + dy)
        elif self._heuristic == HeuristicType.CHEBYSHEV:
            return float(max(dx, dy))
        elif self._heuristic == HeuristicType.EUCLIDEAN:
            return math.sqrt(dx * dx + dy * dy)
        else:  # OCTILE
            return float(max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy))

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self._width and 0 <= y < self._height


_global_pathfinding: Optional[PathfindingSystem] = None


def get_pathfinding() -> PathfindingSystem:
    global _global_pathfinding
    if _global_pathfinding is None:
        _global_pathfinding = PathfindingSystem()
    return _global_pathfinding
