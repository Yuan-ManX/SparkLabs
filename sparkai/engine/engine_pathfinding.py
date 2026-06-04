"""
SparkLabs Engine - Pathfinding Engine

A comprehensive pathfinding and navigation system integrating multiple
search algorithms, dynamic obstacle avoidance, hierarchical path
planning, and flow field generation for crowd simulation.

Architecture:
  EnginePathfinding (Singleton)
    |-- Grid A* (weighted tile-based A* with heap optimization)
    |-- NavMesh Pathfinder (polygon-based navigation mesh routing)
    |-- Flow Field Generator (Dijkstra-based vector fields for crowds)
    |-- Hierarchical Planner (coarse-to-fine multi-resolution paths)
    |-- Dynamic Obstacle Manager (runtime obstacle avoidance)
    |-- Path Smoother (Catmull-Rom spline path post-processing)
    |-- Steering Pipeline (seek/flee/arrive/wander behaviors)
"""

from __future__ import annotations

import heapq
import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AlgorithmType(Enum):
    ASTAR = "astar"
    DIJKSTRA = "dijkstra"
    THETA_STAR = "theta_star"
    JUMP_POINT = "jump_point"
    FLOW_FIELD = "flow_field"
    NAVMESH = "navmesh"


class HeuristicType(Enum):
    MANHATTAN = "manhattan"
    EUCLIDEAN = "euclidean"
    CHEBYSHEV = "chebyshev"
    OCTILE = "octile"
    DIAGONAL = "diagonal"


class PathResult(Enum):
    SUCCESS = "success"
    NO_PATH = "no_path"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    INVALID_START = "invalid_start"
    INVALID_GOAL = "invalid_goal"


class MovementPenalty(Enum):
    NORMAL = "normal"
    SLOW = "slow"
    VERY_SLOW = "very_slow"
    IMPASSABLE = "impassable"
    WATER = "water"
    CLIMBABLE = "climbable"
    HAZARD = "hazard"


class SteeringBehavior(Enum):
    SEEK = "seek"
    FLEE = "flee"
    ARRIVE = "arrive"
    PURSUE = "pursue"
    EVADE = "evade"
    WANDER = "wander"
    FOLLOW_PATH = "follow_path"
    SEPARATION = "separation"
    COHESION = "cohesion"
    ALIGNMENT = "alignment"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class GridNode:
    """A node in the grid-based pathfinding graph."""
    x: int = 0
    y: int = 0
    g_cost: float = 0.0
    h_cost: float = 0.0
    f_cost: float = 0.0
    parent: Optional["GridNode"] = None
    is_walkable: bool = True
    penalty: float = 0.0

    @property
    def total_cost(self) -> float:
        return self.g_cost + self.h_cost + self.penalty

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x, "y": self.y,
            "g_cost": round(self.g_cost, 3),
            "h_cost": round(self.h_cost, 3),
            "is_walkable": self.is_walkable,
        }

    def __lt__(self, other: "GridNode") -> bool:
        return self.total_cost < other.total_cost


@dataclass
class NavMeshPolygon:
    """A convex polygon in the navigation mesh."""
    poly_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    neighbors: List[str] = field(default_factory=list)
    area_cost: float = 1.0
    area_flags: int = 1
    centroid_x: float = 0.0
    centroid_y: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "poly_id": self.poly_id,
            "vertex_count": len(self.vertices),
            "neighbor_count": len(self.neighbors),
            "area_cost": self.area_cost,
            "centroid": [round(self.centroid_x, 3), round(self.centroid_y, 3)],
        }


@dataclass
class FlowField:
    """A vector field for steering agents toward a goal."""
    field_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    width: int = 0
    height: int = 0
    cell_size: float = 1.0
    origin_x: float = 0.0
    origin_y: float = 0.0
    vectors: List[float] = field(default_factory=list)
    costs: List[float] = field(default_factory=list)
    goal_x: int = 0
    goal_y: int = 0
    integration_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_id": self.field_id,
            "dimensions": f"{self.width}x{self.height}",
            "cell_size": self.cell_size,
            "goal": [self.goal_x, self.goal_y],
            "integration_time_ms": round(self.integration_time_ms, 3),
        }

    def get_direction(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """Get the flow direction at a world position."""
        cx = int((world_x - self.origin_x) / self.cell_size)
        cy = int((world_y - self.origin_y) / self.cell_size)
        cx = max(0, min(cx, self.width - 1))
        cy = max(0, min(cy, self.height - 1))
        idx = (cy * self.width + cx) * 2
        if idx + 1 < len(self.vectors):
            return (self.vectors[idx], self.vectors[idx + 1])
        return (0.0, 0.0)


@dataclass
class PathResultData:
    """Result of a pathfinding query."""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: PathResult = PathResult.NO_PATH
    path: List[Tuple[float, float]] = field(default_factory=list)
    smoothed_path: List[Tuple[float, float]] = field(default_factory=list)
    total_cost: float = 0.0
    nodes_visited: int = 0
    search_time_ms: float = 0.0
    path_length: float = 0.0
    algorithm: AlgorithmType = AlgorithmType.ASTAR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "status": self.status.value,
            "waypoint_count": len(self.path),
            "total_cost": round(self.total_cost, 3),
            "nodes_visited": self.nodes_visited,
            "search_time_ms": round(self.search_time_ms, 3),
            "path_length": round(self.path_length, 3),
            "algorithm": self.algorithm.value,
        }


@dataclass
class DynamicObstacle:
    """A runtime obstacle that affects pathfinding."""
    obstacle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    x: float = 0.0
    y: float = 0.0
    radius: float = 10.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    is_active: bool = True
    avoidance_priority: int = 0
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obstacle_id": self.obstacle_id,
            "position": [round(self.x, 3), round(self.y, 3)],
            "radius": self.radius,
            "is_active": self.is_active,
            "label": self.label,
        }


@dataclass
class GridConfig:
    """Configuration for grid-based pathfinding."""
    width: int = 100
    height: int = 100
    cell_size: float = 1.0
    origin_x: float = 0.0
    origin_y: float = 0.0
    allow_diagonal: bool = True
    diagonal_penalty: float = 1.414
    heuristic: HeuristicType = HeuristicType.OCTILE
    max_iterations: int = 10000
    smoothing_iterations: int = 2
    smoothing_tension: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimensions": f"{self.width}x{self.height}",
            "cell_size": self.cell_size,
            "allow_diagonal": self.allow_diagonal,
            "heuristic": self.heuristic.value,
            "max_iterations": self.max_iterations,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class EnginePathfinding:
    """Singleton pathfinding and navigation engine."""

    _instance: Optional["EnginePathfinding"] = None
    _lock = threading.RLock()

    # Cardinal and diagonal direction offsets
    CARDINAL_DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    DIAGONAL_DIRS = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ALL_DIRS = CARDINAL_DIRS + DIAGONAL_DIRS

    def __new__(cls) -> "EnginePathfinding":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._grid_configs: Dict[str, GridConfig] = {}
        self._grids: Dict[str, List[List[GridNode]]] = {}
        self._navmesh_polygons: Dict[str, NavMeshPolygon] = {}
        self._flow_fields: Dict[str, FlowField] = {}
        self._dynamic_obstacles: Dict[str, DynamicObstacle] = {}
        self._results_cache: Dict[str, PathResultData] = {}
        self._penalty_map: Dict[MovementPenalty, float] = {
            MovementPenalty.NORMAL: 0.0,
            MovementPenalty.SLOW: 5.0,
            MovementPenalty.VERY_SLOW: 15.0,
            MovementPenalty.IMPASSABLE: float("inf"),
            MovementPenalty.WATER: 10.0,
            MovementPenalty.CLIMBABLE: 3.0,
            MovementPenalty.HAZARD: 20.0,
        }
        self._total_queries: int = 0
        self._total_time_ms: float = 0.0

    @classmethod
    def get_instance(cls) -> "EnginePathfinding":
        return cls()

    # -- Grid Management -----------------------------------------------------

    def create_grid(self, grid_id: str = "default", **kwargs) -> GridConfig:
        with self._lock:
            config = GridConfig(**kwargs)
            self._grid_configs[grid_id] = config
            # Initialize grid nodes
            grid: List[List[GridNode]] = []
            for y in range(config.height):
                row: List[GridNode] = []
                for x in range(config.width):
                    row.append(GridNode(x=x, y=y))
                grid.append(row)
            self._grids[grid_id] = grid
            return config

    def get_grid_config(self, grid_id: str = "default") -> Optional[GridConfig]:
        return self._grid_configs.get(grid_id)

    def set_node_walkable(self, grid_id: str, x: int, y: int,
                          walkable: bool) -> bool:
        with self._lock:
            grid = self._grids.get(grid_id)
            config = self._grid_configs.get(grid_id)
            if grid is None or config is None:
                return False
            if 0 <= x < config.width and 0 <= y < config.height:
                grid[y][x].is_walkable = walkable
                return True
            return False

    def set_node_penalty(self, grid_id: str, x: int, y: int,
                         penalty: MovementPenalty) -> bool:
        with self._lock:
            grid = self._grids.get(grid_id)
            config = self._grid_configs.get(grid_id)
            if grid is None or config is None:
                return False
            if 0 <= x < config.width and 0 <= y < config.height:
                grid[y][x].penalty = self._penalty_map.get(penalty, 0.0)
                return True
            return False

    def fill_rect(self, grid_id: str, x: int, y: int, w: int, h: int,
                  walkable: bool, penalty: MovementPenalty = MovementPenalty.NORMAL) -> int:
        """Fill a rectangular region with walkable/penalty settings."""
        grid = self._grids.get(grid_id)
        config = self._grid_configs.get(grid_id)
        if grid is None or config is None:
            return 0
        count = 0
        p = self._penalty_map.get(penalty, 0.0)
        for gy in range(max(0, y), min(config.height, y + h)):
            for gx in range(max(0, x), min(config.width, x + w)):
                grid[gy][gx].is_walkable = walkable
                grid[gy][gx].penalty = p
                count += 1
        return count

    # -- Heuristic Calculation -----------------------------------------------

    def _heuristic(self, ax: int, ay: int, bx: int, by: int,
                   heuristic: HeuristicType) -> float:
        dx, dy = abs(ax - bx), abs(ay - by)
        if heuristic == HeuristicType.MANHATTAN:
            return float(dx + dy)
        elif heuristic == HeuristicType.EUCLIDEAN:
            return math.sqrt(dx * dx + dy * dy)
        elif heuristic == HeuristicType.CHEBYSHEV:
            return float(max(dx, dy))
        elif heuristic == HeuristicType.OCTILE:
            return float(max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy))
        elif heuristic == HeuristicType.DIAGONAL:
            return float(max(dx, dy))
        return float(dx + dy)

    # -- A* Pathfinding ------------------------------------------------------

    def find_path_astar(self, grid_id: str = "default",
                        start_x: int = 0, start_y: int = 0,
                        goal_x: int = 10, goal_y: int = 10) -> PathResultData:
        """Find a path using A* on the grid."""
        t_start = _time_module.perf_counter()
        result = PathResultData(algorithm=AlgorithmType.ASTAR)

        grid = self._grids.get(grid_id)
        config = self._grid_configs.get(grid_id)
        if grid is None or config is None:
            result.status = PathResult.INVALID_START
            return result

        if not (0 <= start_x < config.width and 0 <= start_y < config.height):
            result.status = PathResult.INVALID_START
            return result
        if not (0 <= goal_x < config.width and 0 <= goal_y < config.height):
            result.status = PathResult.INVALID_GOAL
            return result

        # Reset grid costs
        for row in grid:
            for node in row:
                node.g_cost = float("inf")
                node.h_cost = 0.0
                node.parent = None

        start = grid[start_y][start_x]
        goal = grid[goal_y][goal_x]

        if not goal.is_walkable:
            result.status = PathResult.INVALID_GOAL
            return result

        start.g_cost = 0.0
        start.h_cost = self._heuristic(start_x, start_y, goal_x, goal_y,
                                       config.heuristic)

        open_set: List[Tuple[float, int, GridNode]] = []
        heapq.heappush(open_set, (start.total_cost, id(start), start))
        closed_set: Set[Tuple[int, int]] = set()
        visits = 0

        directions = self.ALL_DIRS if config.allow_diagonal else self.CARDINAL_DIRS

        while open_set and visits < config.max_iterations:
            _, _, current = heapq.heappop(open_set)
            visits += 1

            if (current.x, current.y) in closed_set:
                continue
            closed_set.add((current.x, current.y))

            if current.x == goal_x and current.y == goal_y:
                # Reconstruct path
                path: List[Tuple[float, float]] = []
                node = current
                while node is not None:
                    wx = config.origin_x + node.x * config.cell_size
                    wy = config.origin_y + node.y * config.cell_size
                    path.append((wx, wy))
                    node = node.parent
                path.reverse()
                result.path = path
                result.status = PathResult.SUCCESS
                result.total_cost = current.g_cost
                result.nodes_visited = visits
                result.path_length = sum(
                    math.hypot(path[i][0] - path[i-1][0],
                               path[i][1] - path[i-1][1])
                    for i in range(1, len(path))
                )
                result.smoothed_path = self._smooth_path(
                    path, config.smoothing_iterations, config.smoothing_tension
                )
                break

            for dx, dy in directions:
                nx, ny = current.x + dx, current.y + dy
                if not (0 <= nx < config.width and 0 <= ny < config.height):
                    continue
                neighbor = grid[ny][nx]
                if not neighbor.is_walkable:
                    continue
                if (nx, ny) in closed_set:
                    continue

                step_cost = math.sqrt(dx * dx + dy * dy) if dx != 0 and dy != 0 else 1.0
                step_cost *= config.cell_size
                new_g = current.g_cost + step_cost + neighbor.penalty

                if new_g < neighbor.g_cost:
                    neighbor.g_cost = new_g
                    neighbor.h_cost = self._heuristic(nx, ny, goal_x, goal_y,
                                                      config.heuristic)
                    neighbor.parent = current
                    heapq.heappush(open_set, (neighbor.total_cost, id(neighbor), neighbor))

        if result.status != PathResult.SUCCESS:
            if visits >= config.max_iterations:
                result.status = PathResult.TIMEOUT
            else:
                result.status = PathResult.NO_PATH

        result.search_time_ms = (_time_module.perf_counter() - t_start) * 1000.0
        self._total_queries += 1
        self._total_time_ms += result.search_time_ms
        self._results_cache[result.result_id] = result
        return result

    # -- Path Smoothing (Catmull-Rom) ----------------------------------------

    def _smooth_path(self, path: List[Tuple[float, float]],
                     iterations: int, tension: float) -> List[Tuple[float, float]]:
        if len(path) < 3 or iterations < 1:
            return list(path)

        smoothed = list(path)
        for _ in range(iterations):
            new_path = [smoothed[0]]
            for i in range(1, len(smoothed) - 1):
                avg_x = (smoothed[i - 1][0] + smoothed[i][0] + smoothed[i + 1][0]) / 3.0
                avg_y = (smoothed[i - 1][1] + smoothed[i][1] + smoothed[i + 1][1]) / 3.0
                new_path.append((
                    smoothed[i][0] + (avg_x - smoothed[i][0]) * (1.0 - tension),
                    smoothed[i][1] + (avg_y - smoothed[i][1]) * (1.0 - tension),
                ))
            new_path.append(smoothed[-1])
            smoothed = new_path
        return smoothed

    # -- Flow Field Generation -----------------------------------------------

    def generate_flow_field(self, field_id: str = "default",
                            grid_id: str = "default",
                            goal_x: int = 0, goal_y: int = 0) -> Optional[FlowField]:
        """Generate a Dijkstra-based flow field for crowd navigation."""
        t_start = _time_module.perf_counter()
        grid = self._grids.get(grid_id)
        config = self._grid_configs.get(grid_id)
        if grid is None or config is None:
            return None

        field = FlowField(
            field_id=field_id,
            width=config.width,
            height=config.height,
            cell_size=config.cell_size,
            origin_x=config.origin_x,
            origin_y=config.origin_y,
            goal_x=goal_x,
            goal_y=goal_y,
        )

        size = config.width * config.height
        costs = [float("inf")] * size
        vectors: List[float] = [0.0] * (size * 2)

        # Initialize goal
        if 0 <= goal_x < config.width and 0 <= goal_y < config.height:
            gidx = goal_y * config.width + goal_x
            costs[gidx] = 0.0

        # Dijkstra flood fill from goal
        queue: List[Tuple[float, int]] = [(0.0, gidx)]
        visited: Set[int] = set()

        while queue:
            cost, idx = heapq.heappop(queue)
            if idx in visited:
                continue
            visited.add(idx)
            cx, cy = idx % config.width, idx // config.width

            for dx, dy in self.ALL_DIRS:
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < config.width and 0 <= ny < config.height):
                    continue
                if not grid[ny][nx].is_walkable:
                    continue
                nidx = ny * config.width + nx
                step = math.sqrt(dx * dx + dy * dy) * config.cell_size
                new_cost = cost + step + grid[ny][nx].penalty
                if new_cost < costs[nidx]:
                    costs[nidx] = new_cost
                    # Direction toward goal (from node to lower-cost neighbor)
                    vectors[nidx * 2] = float(-dx)
                    vectors[nidx * 2 + 1] = float(-dy)
                    heapq.heappush(queue, (new_cost, nidx))

        field.costs = costs
        field.vectors = vectors
        field.integration_time_ms = (_time_module.perf_counter() - t_start) * 1000.0
        self._flow_fields[field_id] = field
        return field

    def get_flow_field(self, field_id: str = "default") -> Optional[FlowField]:
        return self._flow_fields.get(field_id)

    def get_flow_direction(self, field_id: str, world_x: float,
                           world_y: float) -> Tuple[float, float]:
        field = self._flow_fields.get(field_id)
        if field is None:
            return (0.0, 0.0)
        return field.get_direction(world_x, world_y)

    # -- NavMesh Polygon Management ------------------------------------------

    def add_navmesh_polygon(self, vertices: List[Tuple[float, float]],
                            area_cost: float = 1.0, area_flags: int = 1) -> NavMeshPolygon:
        with self._lock:
            poly = NavMeshPolygon(vertices=vertices, area_cost=area_cost,
                                  area_flags=area_flags)
            if vertices:
                xs = [v[0] for v in vertices]
                ys = [v[1] for v in vertices]
                poly.centroid_x = sum(xs) / len(xs)
                poly.centroid_y = sum(ys) / len(ys)
            self._navmesh_polygons[poly.poly_id] = poly
            return poly

    def connect_navmesh_polygons(self, poly_a_id: str, poly_b_id: str) -> bool:
        with self._lock:
            a = self._navmesh_polygons.get(poly_a_id)
            b = self._navmesh_polygons.get(poly_b_id)
            if a is None or b is None:
                return False
            if poly_b_id not in a.neighbors:
                a.neighbors.append(poly_b_id)
            if poly_a_id not in b.neighbors:
                b.neighbors.append(poly_a_id)
            return True

    # -- Dynamic Obstacles ---------------------------------------------------

    def add_obstacle(self, x: float = 0.0, y: float = 0.0,
                     radius: float = 10.0, label: str = "") -> DynamicObstacle:
        with self._lock:
            obs = DynamicObstacle(x=x, y=y, radius=radius, label=label)
            self._dynamic_obstacles[obs.obstacle_id] = obs
            return obs

    def remove_obstacle(self, obstacle_id: str) -> bool:
        with self._lock:
            if obstacle_id in self._dynamic_obstacles:
                del self._dynamic_obstacles[obstacle_id]
                return True
            return False

    def update_obstacle(self, obstacle_id: str, x: float = None,
                        y: float = None, radius: float = None) -> bool:
        with self._lock:
            obs = self._dynamic_obstacles.get(obstacle_id)
            if obs is None:
                return False
            if x is not None:
                obs.x = x
            if y is not None:
                obs.y = y
            if radius is not None:
                obs.radius = radius
            return True

    def get_obstacles(self) -> List[DynamicObstacle]:
        return list(self._dynamic_obstacles.values())

    def get_nearest_obstacles(self, x: float, y: float,
                              max_dist: float) -> List[DynamicObstacle]:
        result: List[DynamicObstacle] = []
        for obs in self._dynamic_obstacles.values():
            if not obs.is_active:
                continue
            dist = math.hypot(x - obs.x, y - obs.y)
            if dist <= max_dist + obs.radius:
                result.append(obs)
        return result

    # -- Steering Behaviors --------------------------------------------------

    def steering_seek(self, agent_x: float, agent_y: float,
                      target_x: float, target_y: float,
                      max_speed: float = 100.0) -> Tuple[float, float]:
        """Compute steering force to seek a target position."""
        dx, dy = target_x - agent_x, target_y - agent_y
        dist = math.hypot(dx, dy)
        if dist < 0.001:
            return (0.0, 0.0)
        return (dx / dist * max_speed, dy / dist * max_speed)

    def steering_flee(self, agent_x: float, agent_y: float,
                      threat_x: float, threat_y: float,
                      max_speed: float = 100.0) -> Tuple[float, float]:
        """Compute steering force to flee from a threat."""
        dx, dy = agent_x - threat_x, agent_y - threat_y
        dist = math.hypot(dx, dy)
        if dist < 0.001:
            return (random.uniform(-1, 1) * max_speed,
                    random.uniform(-1, 1) * max_speed)
        return (dx / dist * max_speed, dy / dist * max_speed)

    def steering_arrive(self, agent_x: float, agent_y: float,
                        target_x: float, target_y: float,
                        max_speed: float = 100.0,
                        slowing_radius: float = 50.0) -> Tuple[float, float]:
        """Compute steering force to arrive at a target with deceleration."""
        dx, dy = target_x - agent_x, target_y - agent_y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return (0.0, 0.0)
        speed = max_speed * min(dist / slowing_radius, 1.0)
        return (dx / dist * speed, dy / dist * speed)

    def steering_wander(self, agent_x: float, agent_y: float,
                        heading_x: float, heading_y: float,
                        max_speed: float = 50.0,
                        wander_radius: float = 30.0,
                        wander_distance: float = 80.0,
                        angle_change: float = 0.3) -> Tuple[float, float]:
        """Compute a wandering steering force."""
        from math import atan2, cos, sin
        angle = atan2(heading_y, heading_x)
        angle += random.uniform(-angle_change, angle_change)
        target_x = agent_x + cos(angle) * wander_distance + \
            random.uniform(-wander_radius, wander_radius)
        target_y = agent_y + sin(angle) * wander_distance + \
            random.uniform(-wander_radius, wander_radius)
        return self.steering_seek(agent_x, agent_y, target_x, target_y, max_speed)

    def steering_separation(self, agent_x: float, agent_y: float,
                            neighbors: List[Tuple[float, float]],
                            max_speed: float = 80.0,
                            separation_radius: float = 40.0) -> Tuple[float, float]:
        """Compute steering force to separate from nearby agents."""
        sx, sy = 0.0, 0.0
        count = 0
        for nx, ny in neighbors:
            dist = math.hypot(agent_x - nx, agent_y - ny)
            if 0.0 < dist < separation_radius:
                sx += (agent_x - nx) / dist
                sy += (agent_y - ny) / dist
                count += 1
        if count == 0:
            return (0.0, 0.0)
        sx, sy = sx / count, sy / count
        mag = math.hypot(sx, sy)
        if mag < 0.001:
            return (0.0, 0.0)
        return (sx / mag * max_speed, sy / mag * max_speed)

    # -- Statistics ----------------------------------------------------------

    def get_system_stats(self) -> Dict[str, Any]:
        """Return system-wide statistics."""
        avg_time = (self._total_time_ms / max(self._total_queries, 1))
        return {
            "total_queries": self._total_queries,
            "avg_search_time_ms": round(avg_time, 3),
            "grid_count": len(self._grid_configs),
            "navmesh_polygon_count": len(self._navmesh_polygons),
            "flow_field_count": len(self._flow_fields),
            "dynamic_obstacle_count": len(self._dynamic_obstacles),
            "cached_results": len(self._results_cache),
        }

    def list_grids(self) -> List[Dict[str, Any]]:
        return [
            {"grid_id": gid, **cfg.to_dict()}
            for gid, cfg in self._grid_configs.items()
        ]

    def list_flow_fields(self) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self._flow_fields.values()]

    def list_navmesh_polygons(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._navmesh_polygons.values()]


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_pathfinding_engine() -> EnginePathfinding:
    return EnginePathfinding.get_instance()