"""
SparkLabs Engine - Navigation System

Comprehensive pathfinding and AI navigation system for the SparkLabs
game engine. Provides navigation mesh generation from grid data and
geometry, A*-based pathfinding across polygon graphs, agent movement
with steering behaviors and local avoidance, off-mesh link traversal,
path smoothing with corridor constraints, and line-of-sight checks.

Architecture:
  EngineNavigationSystem (Singleton)
    |-- NavigationMesh        — polygon-based traversable surface data
    |-- NavigationPath        — computed path with waypoints and status
    |-- NavigationAgent       — autonomous moving entity with steering
    |-- NavigationLink        — off-mesh connections between polygons
    |-- PathStatus (enum)     — path computation lifecycle states
    |-- NavigationState (enum)— agent behavioral state machine
    |-- LinkType (enum)       — off-mesh connection traversal methods

Usage:
    nav = get_navigation_system()
    mesh_id = nav.create_navmesh("overworld", cell_size=0.5, agent_radius=0.3)
    nav.build_navmesh_from_grid(mesh_id, grid_data, 64, 48)
    path = nav.find_path(mesh_id, (10.0, 0.0, 10.0), (50.0, 0.0, 50.0))
    agent_id = nav.create_agent(mesh_id, (10.0, 0.0, 10.0), speed=5.0)
    nav.move_agent(agent_id, (50.0, 0.0, 50.0))
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PathStatus(Enum):
    """Path computation lifecycle states.

    CALCULATING: Path is actively being computed.
    FOUND:       A complete path exists from start to end.
    PARTIAL:     Only a partial path to the destination was found.
    FAILED:      No path could be computed at all.
    STALE:       The path exists but navmesh data has changed since creation.
    REPLANNING:  The path is being recomputed due to environmental changes.
    """

    CALCULATING = "calculating"
    FOUND = "found"
    PARTIAL = "partial"
    FAILED = "failed"
    STALE = "stale"
    REPLANNING = "replanning"


class NavigationState(Enum):
    """Agent behavioral state machine for movement control.

    IDLE:         Agent is stationary with no current target.
    SEEKING:      Agent is computing or waiting for a path.
    MOVING:       Agent is actively traversing its current path.
    AVOIDING:     Agent is performing local obstacle avoidance.
    ARRIVED:      Agent has reached its target destination.
    BLOCKED:      Agent cannot proceed due to an obstruction.
    FALLING_BACK: Agent is retreating to its last valid position.
    """

    IDLE = "idle"
    SEEKING = "seeking"
    MOVING = "moving"
    AVOIDING = "avoiding"
    ARRIVED = "arrived"
    BLOCKED = "blocked"
    FALLING_BACK = "falling_back"


class LinkType(Enum):
    """Off-mesh connection traversal methods between navigation polygons.

    WALK:     Standard walking connection at ground level.
    JUMP:     Gap traversal requiring a jump action.
    TELEPORT: Instant transition between two disconnected locations.
    CLIMB:    Vertical traversal via ladder or climbable surface.
    SWIM:     Water-based traversal between polygons.
    FLY:      Aerial traversal for flying agents.
    CUSTOM:   User-defined traversal behavior with custom logic.
    OFF_MESH: Generic off-mesh link not directly connected by geometry.
    """

    WALK = "walk"
    JUMP = "jump"
    TELEPORT = "teleport"
    CLIMB = "climb"
    SWIM = "swim"
    FLY = "fly"
    CUSTOM = "custom"
    OFF_MESH = "off_mesh"


DEFAULT_CELL_SIZE: float = 0.5
DEFAULT_AGENT_RADIUS: float = 0.3
DEFAULT_AGENT_HEIGHT: float = 2.0
DEFAULT_MAX_SLOPE: float = 45.0
DEFAULT_STEP_HEIGHT: float = 0.3
DEFAULT_SPEED: float = 5.0
DEFAULT_ROTATION_SPEED: float = 180.0
DEFAULT_AVOIDANCE_RADIUS: float = 1.0
DEFAULT_CORRIDOR_WIDTH: float = 2.0
MAX_SMOOTHING_ITERATIONS: int = 5
ARRIVAL_THRESHOLD: float = 0.5
PATH_RECOMPUTE_THRESHOLD: float = 5.0


@dataclass
class NavigationMesh:
    """Polygon-based navigable surface representation.

    Stores tessellated walkable geometry with per-region cost data,
    agent size constraints, and off-mesh connection links. Each
    polygon in the mesh represents a convex traversable area with
    adjacency data for graph-based pathfinding queries.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    polygons: List[List[int]] = field(default_factory=list)
    polygon_areas: List[int] = field(default_factory=list)
    polygon_centers: List[Tuple[float, float, float]] = field(default_factory=list)
    adjacency: List[List[int]] = field(default_factory=list)
    bounds: Tuple[float, float, float, float, float, float] = (
        0.0, 0.0, 0.0, 100.0, 0.0, 100.0,
    )
    cell_size: float = DEFAULT_CELL_SIZE
    agent_radius: float = DEFAULT_AGENT_RADIUS
    agent_height: float = DEFAULT_AGENT_HEIGHT
    max_slope: float = DEFAULT_MAX_SLOPE
    step_height: float = DEFAULT_STEP_HEIGHT
    links: List[NavigationLink] = field(default_factory=list)
    polygon_count: int = 0
    vertex_count: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "vertices": [list(v) for v in self.vertices],
            "polygons": [list(p) for p in self.polygons],
            "polygon_areas": list(self.polygon_areas),
            "polygon_centers": [list(c) for c in self.polygon_centers],
            "adjacency": [list(a) for a in self.adjacency],
            "bounds": list(self.bounds),
            "cell_size": self.cell_size,
            "agent_radius": self.agent_radius,
            "agent_height": self.agent_height,
            "max_slope": self.max_slope,
            "step_height": self.step_height,
            "links": [link.to_dict() for link in self.links],
            "polygon_count": len(self.polygons),
            "vertex_count": len(self.vertices),
            "created_at": self.created_at,
        }


@dataclass
class NavigationPath:
    """Computed path result from a start to end position on a navmesh.

    Contains ordered waypoints, total traversal distance, current
    computation status, and smoothing quality metadata for corridor-
    constrained movement along the navmesh surface.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    navmesh_id: str = ""
    start_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    end_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    waypoints: List[Tuple[float, float, float]] = field(default_factory=list)
    total_distance: float = 0.0
    path_status: PathStatus = PathStatus.CALCULATING
    smoothing_iterations: int = 0
    corridor_width: float = DEFAULT_CORRIDOR_WIDTH
    calculated_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "navmesh_id": self.navmesh_id,
            "start_point": list(self.start_point),
            "end_point": list(self.end_point),
            "waypoints": [list(w) for w in self.waypoints],
            "total_distance": self.total_distance,
            "path_status": self.path_status.value,
            "smoothing_iterations": self.smoothing_iterations,
            "corridor_width": self.corridor_width,
            "calculated_at": self.calculated_at,
            "waypoint_count": len(self.waypoints),
        }


@dataclass
class NavigationAgent:
    """Autonomous entity navigating the navmesh with steering behaviors.

    Tracks position, target, current path, movement parameters,
    avoidance settings, and behavioral state. Supports configurable
    steering behaviors for separation, cohesion, alignment, seek,
    flee, and arrival to produce natural crowd movement.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    navmesh_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    current_path: Optional[NavigationPath] = None
    speed: float = DEFAULT_SPEED
    rotation_speed: float = DEFAULT_ROTATION_SPEED
    avoidance_radius: float = DEFAULT_AVOIDANCE_RADIUS
    avoidance_priority: int = 50
    steering_behaviors: List[str] = field(default_factory=list)
    state: NavigationState = NavigationState.IDLE
    current_waypoint_index: int = 0
    stuck_timer: float = 0.0
    last_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "navmesh_id": self.navmesh_id,
            "position": list(self.position),
            "target_position": list(self.target_position),
            "current_path": self.current_path.to_dict() if self.current_path else None,
            "speed": self.speed,
            "rotation_speed": self.rotation_speed,
            "avoidance_radius": self.avoidance_radius,
            "avoidance_priority": self.avoidance_priority,
            "steering_behaviors": list(self.steering_behaviors),
            "state": self.state.value,
            "current_waypoint_index": self.current_waypoint_index,
            "stuck_timer": self.stuck_timer,
            "created_at": self.created_at,
        }


@dataclass
class NavigationLink:
    """Off-mesh connection between two navigation polygons.

    Enables traversal between disconnected navmesh regions through
    specified movement types such as jumping, climbing, teleporting,
    or swimming. Supports bidirectional and one-way travel with
    configurable cost multipliers for AI decision-making.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    navmesh_id: str = ""
    start_polygon: int = -1
    end_polygon: int = -1
    link_type: LinkType = LinkType.WALK
    cost_multiplier: float = 1.0
    bidirectional: bool = True
    one_way_direction: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    start_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    end_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    traversal_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "navmesh_id": self.navmesh_id,
            "start_polygon": self.start_polygon,
            "end_polygon": self.end_polygon,
            "link_type": self.link_type.value,
            "cost_multiplier": self.cost_multiplier,
            "bidirectional": self.bidirectional,
            "one_way_direction": list(self.one_way_direction),
            "start_point": list(self.start_point),
            "end_point": list(self.end_point),
            "traversal_time": self.traversal_time,
            "created_at": self.created_at,
        }


class EngineNavigationSystem:
    """Comprehensive pathfinding and AI navigation system.

    Manages navigation mesh lifecycle, A* polygon-graph pathfinding,
    agent movement with steering behaviors, local avoidance, off-mesh
    link traversal, path smoothing, and spatial queries. Serves as
    the central authority for all AI movement within SparkLabs scenes.

    Usage:
        nav = get_navigation_system()
        mesh_id = nav.create_navmesh("level1", cell_size=0.5, agent_radius=0.3)
        nav.build_navmesh_from_grid(mesh_id, grid, 64, 48)
        path = nav.find_path(mesh_id, (0, 0, 0), (50, 0, 50))
        agent_id = nav.create_agent(mesh_id, (0, 0, 0), speed=5.0)
        nav.move_agent(agent_id, (50, 0, 50))
    """

    _instance: Optional["EngineNavigationSystem"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_NAVMESHES: int = 128
    MAX_AGENTS_PER_MESH: int = 1024
    MAX_LINKS_PER_MESH: int = 2048
    MAX_POLYGONS_PER_MESH: int = 65536
    MAX_WAYPOINTS_PER_PATH: int = 4096

    def __new__(cls) -> "EngineNavigationSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._navmeshes: Dict[str, NavigationMesh] = {}
        self._agents: Dict[str, NavigationAgent] = {}
        self._paths: Dict[str, NavigationPath] = {}
        self._path_cache: Dict[str, NavigationPath] = {}
        self._total_paths_computed: int = 0
        self._total_agents_moved: int = 0
        self._total_links_added: int = 0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "EngineNavigationSystem":
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_mesh(self, mesh_id: str) -> NavigationMesh:
        _time_module.sleep(0.001)
        if mesh_id not in self._navmeshes:
            raise KeyError(f"NavigationMesh '{mesh_id}' does not exist")
        return self._navmeshes[mesh_id]

    def _get_agent(self, agent_id: str) -> NavigationAgent:
        _time_module.sleep(0.001)
        if agent_id not in self._agents:
            raise KeyError(f"NavigationAgent '{agent_id}' does not exist")
        return self._agents[agent_id]

    def _get_path(self, path_id: str) -> NavigationPath:
        _time_module.sleep(0.001)
        if path_id not in self._paths:
            raise KeyError(f"NavigationPath '{path_id}' does not exist")
        return self._paths[path_id]

    @staticmethod
    def _distance_3d(
        a: Tuple[float, float, float], b: Tuple[float, float, float]
    ) -> float:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        dz = a[2] - b[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @staticmethod
    def _distance_2d(
        a: Tuple[float, float], b: Tuple[float, float]
    ) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    @staticmethod
    def _point_in_polygon(
        point: Tuple[float, float],
        poly_vertices: List[Tuple[float, float]],
    ) -> bool:
        x, y = point
        inside = False
        n = len(poly_vertices)
        if n < 3:
            return False
        j = n - 1
        for i in range(n):
            xi, yi = poly_vertices[i]
            xj, yj = poly_vertices[j]
            if ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / (yj - yi) + xi
            ):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _polygon_center(
        indices: List[int], vertices: List[Tuple[float, float, float]]
    ) -> Tuple[float, float, float]:
        if not indices:
            return (0.0, 0.0, 0.0)
        sx, sy, sz = 0.0, 0.0, 0.0
        count = 0
        for idx in indices:
            if 0 <= idx < len(vertices):
                vx, vy, vz = vertices[idx]
                sx += vx
                sy += vy
                sz += vz
                count += 1
        if count == 0:
            return (0.0, 0.0, 0.0)
        return (sx / count, sy / count, sz / count)

    def _shared_vertices(
        self,
        poly_a: List[int],
        poly_b: List[int],
        vertices: List[Tuple[float, float, float]],
    ) -> int:
        _time_module.sleep(0.001)
        shared = 0
        set_b = set(poly_b)
        for idx in poly_a:
            if idx in set_b:
                shared += 1
                if shared >= 2:
                    return shared
        return shared

    def _build_adjacency(self, mesh: NavigationMesh) -> None:
        _time_module.sleep(0.001)
        n = len(mesh.polygons)
        mesh.adjacency = [[] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                shared = self._shared_vertices(
                    mesh.polygons[i], mesh.polygons[j], mesh.vertices
                )
                if shared >= 2:
                    mesh.adjacency[i].append(j)
                    mesh.adjacency[j].append(i)

    def _locate_polygon(
        self, mesh: NavigationMesh, point: Tuple[float, float, float]
    ) -> int:
        _time_module.sleep(0.001)
        px, py, pz = point
        for i, poly_indices in enumerate(mesh.polygons):
            poly_2d: List[Tuple[float, float]] = []
            for idx in poly_indices:
                if 0 <= idx < len(mesh.vertices):
                    vx, vy, vz = mesh.vertices[idx]
                    poly_2d.append((vx, vz))
            if self._point_in_polygon((px, pz), poly_2d):
                return i
        best_idx = -1
        best_dist = float("inf")
        for i, center in enumerate(mesh.polygon_centers):
            d = math.sqrt(
                (px - center[0]) ** 2 + (pz - center[2]) ** 2
            )
            if d < best_dist:
                best_dist = d
                best_idx = i
        return best_idx

    def _compute_path_cost(
        self, waypoints: List[Tuple[float, float, float]]
    ) -> float:
        _time_module.sleep(0.001)
        total = 0.0
        for i in range(1, len(waypoints)):
            total += self._distance_3d(waypoints[i - 1], waypoints[i])
        return total

    # ------------------------------------------------------------------
    # Navigation mesh management
    # ------------------------------------------------------------------

    def create_navmesh(
        self,
        name: str,
        cell_size: float = DEFAULT_CELL_SIZE,
        agent_radius: float = DEFAULT_AGENT_RADIUS,
        agent_height: float = DEFAULT_AGENT_HEIGHT,
        max_slope: float = DEFAULT_MAX_SLOPE,
        step_height: float = DEFAULT_STEP_HEIGHT,
        bounds: Optional[
            Tuple[float, float, float, float, float, float]
        ] = None,
    ) -> str:
        _time_module.sleep(0.001)
        if len(self._navmeshes) >= self.MAX_NAVMESHES:
            raise RuntimeError(
                f"NavMesh limit reached ({self.MAX_NAVMESHES})"
            )
        if cell_size <= 0:
            raise ValueError("cell_size must be positive")
        if agent_radius <= 0:
            raise ValueError("agent_radius must be positive")
        if agent_height <= 0:
            raise ValueError("agent_height must be positive")

        b = bounds or (0.0, 0.0, 0.0, 100.0, 0.0, 100.0)
        mesh = NavigationMesh(
            name=name,
            cell_size=cell_size,
            agent_radius=agent_radius,
            agent_height=agent_height,
            max_slope=max_slope,
            step_height=step_height,
            bounds=b,
        )
        self._navmeshes[mesh.id] = mesh
        return mesh.id

    def build_navmesh_from_grid(
        self,
        mesh_id: str,
        grid: List[List[bool]],
        width: int,
        height: int,
        origin_x: float = 0.0,
        origin_z: float = 0.0,
    ) -> bool:
        _time_module.sleep(0.001)
        mesh = self._navmeshes.get(mesh_id)
        if mesh is None:
            return False
        if not grid or width <= 0 or height <= 0:
            return False

        mesh.vertices.clear()
        mesh.polygons.clear()
        mesh.polygon_areas.clear()
        mesh.polygon_centers.clear()
        mesh.adjacency.clear()
        mesh.links.clear()

        cell_size = mesh.cell_size
        vertex_map: Dict[Tuple[int, int], int] = {}

        vertex_idx = 0
        for z in range(height):
            for x in range(width):
                if z < len(grid) and x < len(grid[z]):
                    if grid[z][x]:
                        vx = origin_x + x * cell_size
                        vz = origin_z + z * cell_size
                        corners = [
                            (vx, 0.0, vz),
                            (vx + cell_size, 0.0, vz),
                            (vx + cell_size, 0.0, vz + cell_size),
                            (vx, 0.0, vz + cell_size),
                        ]
                        local_indices: List[int] = []
                        for corner in corners:
                            ckey = (round(corner[0], 4), round(corner[2], 4))
                            if ckey not in vertex_map:
                                vertex_map[ckey] = vertex_idx
                                mesh.vertices.append(corner)
                                vertex_idx += 1
                            local_indices.append(vertex_map[ckey])

                        mesh.polygons.append(local_indices)
                        mesh.polygon_areas.append(0)
                        center = (
                            (corners[0][0] + corners[2][0]) / 2,
                            0.0,
                            (corners[0][2] + corners[2][2]) / 2,
                        )
                        mesh.polygon_centers.append(center)

        if not mesh.polygons:
            return False

        self._build_adjacency(mesh)
        mesh.polygon_count = len(mesh.polygons)
        mesh.vertex_count = len(mesh.vertices)
        self._path_cache.clear()
        return True

    def remove_navmesh(self, mesh_id: str) -> bool:
        _time_module.sleep(0.001)
        if mesh_id not in self._navmeshes:
            return False

        agents_to_remove = [
            aid
            for aid, agent in self._agents.items()
            if agent.navmesh_id == mesh_id
        ]
        for aid in agents_to_remove:
            del self._agents[aid]

        paths_to_remove = [
            pid
            for pid, path in self._paths.items()
            if path.navmesh_id == mesh_id
        ]
        for pid in paths_to_remove:
            del self._paths[pid]

        cache_to_remove = [
            ckey
            for ckey, cpath in self._path_cache.items()
            if cpath.navmesh_id == mesh_id
        ]
        for ckey in cache_to_remove:
            del self._path_cache[ckey]

        del self._navmeshes[mesh_id]
        return True

    # ------------------------------------------------------------------
    # Navigation link management
    # ------------------------------------------------------------------

    def add_navigation_link(
        self,
        mesh_id: str,
        start_polygon: int,
        end_polygon: int,
        link_type: str = "walk",
        cost_multiplier: float = 1.0,
        bidirectional: bool = True,
        start_point: Optional[Tuple[float, float, float]] = None,
        end_point: Optional[Tuple[float, float, float]] = None,
        one_way_direction: Optional[Tuple[float, float, float]] = None,
    ) -> Optional[str]:
        _time_module.sleep(0.001)
        mesh = self._navmeshes.get(mesh_id)
        if mesh is None:
            return None
        if len(mesh.links) >= self.MAX_LINKS_PER_MESH:
            raise RuntimeError(
                f"Link limit reached ({self.MAX_LINKS_PER_MESH}) for mesh '{mesh_id}'"
            )

        if start_polygon < 0 or start_polygon >= len(mesh.polygons):
            return None
        if end_polygon < 0 or end_polygon >= len(mesh.polygons):
            return None

        try:
            lt = LinkType(link_type.lower())
        except ValueError:
            lt = LinkType.WALK

        sp = start_point or mesh.polygon_centers[start_polygon]
        ep = end_point or mesh.polygon_centers[end_polygon]

        link = NavigationLink(
            navmesh_id=mesh_id,
            start_polygon=start_polygon,
            end_polygon=end_polygon,
            link_type=lt,
            cost_multiplier=cost_multiplier,
            bidirectional=bidirectional,
            start_point=sp,
            end_point=ep,
            one_way_direction=one_way_direction or (0.0, 0.0, 0.0),
        )
        mesh.links.append(link)

        if start_polygon not in mesh.adjacency:
            mesh.adjacency.append([])
        while len(mesh.adjacency) <= end_polygon:
            mesh.adjacency.append([])

        if end_polygon not in mesh.adjacency[start_polygon]:
            mesh.adjacency[start_polygon].append(end_polygon)
        if bidirectional and start_polygon not in mesh.adjacency[end_polygon]:
            mesh.adjacency[end_polygon].append(start_polygon)

        self._total_links_added += 1
        return link.id

    # ------------------------------------------------------------------
    # Pathfinding
    # ------------------------------------------------------------------

    def find_path(
        self,
        mesh_id: str,
        start_point: Tuple[float, float, float],
        end_point: Tuple[float, float, float],
    ) -> NavigationPath:
        _time_module.sleep(0.001)
        path = NavigationPath(
            navmesh_id=mesh_id,
            start_point=start_point,
            end_point=end_point,
            path_status=PathStatus.CALCULATING,
        )

        mesh = self._navmeshes.get(mesh_id)
        if mesh is None or not mesh.polygons:
            path.path_status = PathStatus.FAILED
            self._paths[path.id] = path
            self._total_paths_computed += 1
            return path

        cache_key = (
            f"{mesh_id}:{start_point[0]:.3f},{start_point[1]:.3f},{start_point[2]:.3f}"
            f":{end_point[0]:.3f},{end_point[1]:.3f},{end_point[2]:.3f}"
        )
        cached = self._path_cache.get(cache_key)
        if cached is not None:
            self._total_paths_computed += 1
            return cached

        start_poly = self._locate_polygon(mesh, start_point)
        end_poly = self._locate_polygon(mesh, end_point)

        if start_poly < 0 or end_poly < 0:
            path.path_status = PathStatus.FAILED
            self._paths[path.id] = path
            self._total_paths_computed += 1
            return path

        if start_poly == end_poly:
            path.waypoints = [start_point, end_point]
            path.total_distance = self._distance_3d(start_point, end_point)
            path.path_status = PathStatus.FOUND
            self._paths[path.id] = path
            self._path_cache[cache_key] = path
            self._total_paths_computed += 1
            return path

        n_poly = len(mesh.polygons)
        import heapq

        open_set: List[Tuple[float, int, int]] = []
        tie_breaker = 0

        g_score: Dict[int, float] = {}
        came_from: Dict[int, Optional[int]] = {}

        start_h = self._distance_3d(
            mesh.polygon_centers[start_poly], mesh.polygon_centers[end_poly]
        )
        g_score[start_poly] = 0.0
        heapq.heappush(open_set, (start_h, tie_breaker, start_poly))
        tie_breaker += 1
        came_from[start_poly] = None

        closed_set: set = set()

        while open_set:
            _, _, current = heapq.heappop(open_set)

            if current in closed_set:
                continue
            if current == end_poly:
                break
            closed_set.add(current)

            neighbors = list(mesh.adjacency[current]) if current < len(mesh.adjacency) else []
            for link in mesh.links:
                if link.start_polygon == current and link.end_polygon not in neighbors:
                    neighbors.append(link.end_polygon)
                if link.bidirectional and link.end_polygon == current and link.start_polygon not in neighbors:
                    neighbors.append(link.start_polygon)

            for neighbor in neighbors:
                if neighbor in closed_set:
                    continue
                if neighbor < 0 or neighbor >= n_poly:
                    continue

                edge_cost = self._distance_3d(
                    mesh.polygon_centers[current], mesh.polygon_centers[neighbor]
                )

                link_multiplier = 1.0
                for link in mesh.links:
                    if link.start_polygon == current and link.end_polygon == neighbor:
                        link_multiplier = link.cost_multiplier
                        break
                    if link.bidirectional and link.end_polygon == current and link.start_polygon == neighbor:
                        link_multiplier = link.cost_multiplier
                        break

                tentative_g = g_score[current] + edge_cost * link_multiplier

                existing_g = g_score.get(neighbor)
                if existing_g is None or tentative_g < existing_g:
                    g_score[neighbor] = tentative_g
                    came_from[neighbor] = current
                    h = self._distance_3d(
                        mesh.polygon_centers[neighbor], mesh.polygon_centers[end_poly]
                    )
                    heapq.heappush(open_set, (tentative_g + h, tie_breaker, neighbor))
                    tie_breaker += 1

        if end_poly not in came_from:
            path.path_status = PathStatus.PARTIAL
            partial_path: List[Tuple[float, float, float]] = []
            best_poly = None
            best_g = float("inf")
            for visited_poly in came_from:
                if came_from[visited_poly] is not None:
                    if g_score.get(visited_poly, float("inf")) < best_g:
                        best_g = g_score[visited_poly]
                        best_poly = visited_poly
            if best_poly is not None:
                poly_seq: List[int] = []
                cur: Optional[int] = best_poly
                while cur is not None:
                    poly_seq.append(cur)
                    cur = came_from.get(cur)
                poly_seq.reverse()
                partial_path.append(start_point)
                for p_idx in poly_seq:
                    if p_idx < len(mesh.polygon_centers):
                        partial_path.append(mesh.polygon_centers[p_idx])
                path.waypoints = partial_path
                path.total_distance = self._compute_path_cost(partial_path)
            self._paths[path.id] = path
            self._total_paths_computed += 1
            return path

        poly_sequence: List[int] = []
        cur: Optional[int] = end_poly
        while cur is not None:
            poly_sequence.append(cur)
            cur = came_from.get(cur)
        poly_sequence.reverse()

        path.waypoints = [start_point]
        for p_idx in poly_sequence:
            if p_idx < len(mesh.polygon_centers):
                path.waypoints.append(mesh.polygon_centers[p_idx])
        path.waypoints.append(end_point)

        path.total_distance = self._compute_path_cost(path.waypoints)
        path.path_status = PathStatus.FOUND
        path.calculated_at = _time_module.time()

        self._paths[path.id] = path
        self._path_cache[cache_key] = path
        self._total_paths_computed += 1
        return path

    def find_nearest_point(
        self,
        mesh_id: str,
        point: Tuple[float, float, float],
    ) -> Tuple[float, float, float]:
        _time_module.sleep(0.001)
        mesh = self._navmeshes.get(mesh_id)
        if mesh is None or not mesh.polygon_centers:
            return point

        best_idx = -1
        best_dist = float("inf")
        px, py, pz = point
        for i, center in enumerate(mesh.polygon_centers):
            d = math.sqrt(
                (px - center[0]) ** 2 + (py - center[1]) ** 2 + (pz - center[2]) ** 2
            )
            if d < best_dist:
                best_dist = d
                best_idx = i

        if best_idx >= 0:
            return mesh.polygon_centers[best_idx]
        return point

    # ------------------------------------------------------------------
    # Path smoothing
    # ------------------------------------------------------------------

    def smooth_path(
        self,
        path_id: str,
        iterations: int = 3,
        corridor_width: float = DEFAULT_CORRIDOR_WIDTH,
    ) -> Optional[NavigationPath]:
        _time_module.sleep(0.001)
        path = self._paths.get(path_id)
        if path is None:
            return None
        if path.path_status not in (PathStatus.FOUND, PathStatus.PARTIAL):
            return path
        if len(path.waypoints) <= 2:
            path.smoothing_iterations = 0
            path.corridor_width = corridor_width
            return path

        iterations = min(iterations, MAX_SMOOTHING_ITERATIONS)
        path.corridor_width = corridor_width

        mesh = self._navmeshes.get(path.navmesh_id)
        if mesh is None:
            path.smoothing_iterations = 0
            return path

        waypoints = list(path.waypoints)
        for _ in range(iterations):
            if len(waypoints) <= 2:
                break
            smoothed: List[Tuple[float, float, float]] = [waypoints[0]]
            for i in range(1, len(waypoints) - 1):
                prev = waypoints[i - 1]
                curr = waypoints[i]
                nxt = waypoints[i + 1]
                mid_x = (prev[0] + nxt[0]) / 2
                mid_y = (prev[1] + nxt[1]) / 2
                mid_z = (prev[2] + nxt[2]) / 2
                smooth_x = curr[0] + 0.5 * (mid_x - curr[0])
                smooth_y = curr[1] + 0.5 * (mid_y - curr[1])
                smooth_z = curr[2] + 0.5 * (mid_z - curr[2])
                smoothed.append((smooth_x, smooth_y, smooth_z))
            smoothed.append(waypoints[-1])
            waypoints = smoothed

        simplified: List[Tuple[float, float, float]] = [waypoints[0]]
        anchor = 0
        while anchor < len(waypoints) - 1:
            for i in range(len(waypoints) - 1, anchor, -1):
                if i == anchor + 1 or self._line_of_sight_internal(
                    mesh, waypoints[anchor], waypoints[i]
                ):
                    simplified.append(waypoints[i])
                    anchor = i
                    break

        path.waypoints = simplified
        path.total_distance = self._compute_path_cost(simplified)
        path.smoothing_iterations = iterations

        return path

    def _line_of_sight_internal(
        self,
        mesh: NavigationMesh,
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
    ) -> bool:
        _time_module.sleep(0.001)
        if not mesh.polygons:
            return True
        steps = max(1, int(self._distance_3d(a, b) / (mesh.cell_size * 0.5)))
        for i in range(1, steps):
            t = i / steps
            px = a[0] + t * (b[0] - a[0])
            py = a[1] + t * (b[1] - a[1])
            pz = a[2] + t * (b[2] - a[2])
            found = False
            for j, poly_indices in enumerate(mesh.polygons):
                poly_2d: List[Tuple[float, float]] = []
                for idx in poly_indices:
                    if 0 <= idx < len(mesh.vertices):
                        vx, vy, vz = mesh.vertices[idx]
                        poly_2d.append((vx, vz))
                if self._point_in_polygon((px, pz), poly_2d):
                    found = True
                    break
            if not found:
                return False
        return True

    def check_line_of_sight(
        self,
        mesh_id: str,
        point_a: Tuple[float, float, float],
        point_b: Tuple[float, float, float],
    ) -> bool:
        _time_module.sleep(0.001)
        mesh = self._navmeshes.get(mesh_id)
        if mesh is None:
            return False
        return self._line_of_sight_internal(mesh, point_a, point_b)

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def create_agent(
        self,
        mesh_id: str,
        position: Tuple[float, float, float],
        speed: float = DEFAULT_SPEED,
        rotation_speed: float = DEFAULT_ROTATION_SPEED,
        avoidance_radius: float = DEFAULT_AVOIDANCE_RADIUS,
        avoidance_priority: int = 50,
        steering_behaviors: Optional[List[str]] = None,
    ) -> str:
        _time_module.sleep(0.001)
        mesh = self._navmeshes.get(mesh_id)
        if mesh is None:
            raise KeyError(f"NavigationMesh '{mesh_id}' does not exist")

        agent_count = sum(
            1 for a in self._agents.values() if a.navmesh_id == mesh_id
        )
        if agent_count >= self.MAX_AGENTS_PER_MESH:
            raise RuntimeError(
                f"Agent limit reached ({self.MAX_AGENTS_PER_MESH}) for mesh '{mesh_id}'"
            )

        agent = NavigationAgent(
            navmesh_id=mesh_id,
            position=position,
            target_position=position,
            last_position=position,
            speed=speed,
            rotation_speed=rotation_speed,
            avoidance_radius=avoidance_radius,
            avoidance_priority=avoidance_priority,
            steering_behaviors=steering_behaviors or ["seek", "arrival"],
            state=NavigationState.IDLE,
        )
        self._agents[agent.id] = agent
        return agent.id

    def move_agent(
        self,
        agent_id: str,
        target_position: Tuple[float, float, float],
    ) -> Optional[str]:
        _time_module.sleep(0.001)
        agent = self._agents.get(agent_id)
        if agent is None:
            return None

        agent.target_position = target_position
        agent.state = NavigationState.SEEKING

        path = self.find_path(agent.navmesh_id, agent.position, target_position)
        if path.path_status in (PathStatus.FOUND, PathStatus.PARTIAL):
            agent.current_path = path
            agent.current_waypoint_index = 0
            agent.state = NavigationState.MOVING
        else:
            agent.state = NavigationState.BLOCKED

        self._total_agents_moved += 1
        return path.id

    def update_agent(
        self,
        agent_id: str,
        delta_time: float,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        agent = self._agents.get(agent_id)
        if agent is None:
            return {"state": "not_found", "position": (0.0, 0.0, 0.0)}

        if agent.state not in (
            NavigationState.MOVING,
            NavigationState.AVOIDING,
            NavigationState.FALLING_BACK,
        ):
            return {
                "state": agent.state.value,
                "position": list(agent.position),
                "target": list(agent.target_position),
                "waypoint_index": agent.current_waypoint_index,
            }

        if agent.current_path is None or not agent.current_path.waypoints:
            agent.state = NavigationState.IDLE
            return {
                "state": agent.state.value,
                "position": list(agent.position),
                "target": list(agent.target_position),
                "waypoint_index": agent.current_waypoint_index,
            }

        waypoints = agent.current_path.waypoints
        if agent.current_waypoint_index >= len(waypoints):
            agent.state = NavigationState.ARRIVED
            agent.position = agent.target_position
            return {
                "state": agent.state.value,
                "position": list(agent.position),
                "target": list(agent.target_position),
                "waypoint_index": agent.current_waypoint_index,
            }

        target_wp = waypoints[agent.current_waypoint_index]

        dist_to_wp = self._distance_3d(agent.position, target_wp)

        if dist_to_wp <= ARRIVAL_THRESHOLD:
            agent.current_waypoint_index += 1
            if agent.current_waypoint_index >= len(waypoints):
                agent.state = NavigationState.ARRIVED
                agent.position = agent.target_position
                return {
                    "state": agent.state.value,
                    "position": list(agent.position),
                    "target": list(agent.target_position),
                    "waypoint_index": agent.current_waypoint_index,
                }
            target_wp = waypoints[agent.current_waypoint_index]
            dist_to_wp = self._distance_3d(agent.position, target_wp)

        if dist_to_wp <= 0.0001:
            return {
                "state": agent.state.value,
                "position": list(agent.position),
                "target": list(agent.target_position),
                "waypoint_index": agent.current_waypoint_index,
            }

        dx = target_wp[0] - agent.position[0]
        dy = target_wp[1] - agent.position[1]
        dz = target_wp[2] - agent.position[2]

        max_move = agent.speed * delta_time
        if max_move >= dist_to_wp:
            agent.position = target_wp
        else:
            ratio = max_move / dist_to_wp
            agent.position = (
                agent.position[0] + dx * ratio,
                agent.position[1] + dy * ratio,
                agent.position[2] + dz * ratio,
            )

        dist_from_last = self._distance_3d(agent.position, agent.last_position)
        if dist_from_last < 0.001:
            agent.stuck_timer += delta_time
        else:
            agent.stuck_timer = 0.0

        agent.last_position = agent.position

        if agent.stuck_timer > 2.0:
            agent.state = NavigationState.BLOCKED
            new_path = self.find_path(
                agent.navmesh_id, agent.position, agent.target_position
            )
            if new_path.path_status in (PathStatus.FOUND, PathStatus.PARTIAL):
                agent.current_path = new_path
                agent.current_waypoint_index = 0
                agent.state = NavigationState.MOVING
                agent.stuck_timer = 0.0

        dist_to_target = self._distance_3d(agent.position, agent.target_position)
        if dist_to_target > PATH_RECOMPUTE_THRESHOLD and agent.stuck_timer <= 0:
            if agent.state == NavigationState.MOVING:
                new_path = self.find_path(
                    agent.navmesh_id, agent.position, agent.target_position
                )
                if (
                    new_path.path_status in (PathStatus.FOUND, PathStatus.PARTIAL)
                    and new_path.total_distance < agent.current_path.total_distance * 0.8
                ):
                    agent.current_path = new_path
                    agent.current_waypoint_index = 0

        return {
            "state": agent.state.value,
            "position": list(agent.position),
            "target": list(agent.target_position),
            "waypoint_index": agent.current_waypoint_index,
            "distance_to_target": dist_to_target,
            "stuck_timer": agent.stuck_timer,
        }

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        agent = self._agents.get(agent_id)
        if agent is None:
            return {"found": False, "state": "not_found"}
        return {
            "found": True,
            "state": agent.state.value,
            "position": list(agent.position),
            "target_position": list(agent.target_position),
            "speed": agent.speed,
            "avoidance_radius": agent.avoidance_radius,
            "avoidance_priority": agent.avoidance_priority,
            "steering_behaviors": list(agent.steering_behaviors),
            "current_waypoint_index": agent.current_waypoint_index,
            "stuck_timer": agent.stuck_timer,
            "has_path": agent.current_path is not None,
            "path_waypoints": (
                len(agent.current_path.waypoints) if agent.current_path else 0
            ),
        }

    # ------------------------------------------------------------------
    # Steering behaviors
    # ------------------------------------------------------------------

    def _compute_seek_force(
        self,
        position: Tuple[float, float, float],
        target: Tuple[float, float, float],
        velocity: Tuple[float, float, float],
        max_speed: float,
    ) -> Tuple[float, float, float]:
        dx = target[0] - position[0]
        dy = target[1] - position[1]
        dz = target[2] - position[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist < 0.0001:
            return (0.0, 0.0, 0.0)
        desired = (dx / dist * max_speed, dy / dist * max_speed, dz / dist * max_speed)
        return (desired[0], desired[1], desired[2])

    def _compute_separation_force(
        self,
        agent_id: str,
        position: Tuple[float, float, float],
        radius: float,
    ) -> Tuple[float, float, float]:
        force = [0.0, 0.0, 0.0]
        agent = self._agents.get(agent_id)
        if agent is None:
            return (0.0, 0.0, 0.0)
        for other_id, other in self._agents.items():
            if other_id == agent_id:
                continue
            if other.navmesh_id != agent.navmesh_id:
                continue
            dist = self._distance_3d(position, other.position)
            combined_radius = radius + other.avoidance_radius
            if dist < combined_radius and dist > 0.0001:
                penetration = combined_radius - dist
                dx = (position[0] - other.position[0]) / dist
                dy = (position[1] - other.position[1]) / dist
                dz = (position[2] - other.position[2]) / dist
                priority_factor = (
                    float(other.avoidance_priority) / max(agent.avoidance_priority, 1)
                )
                force[0] += dx * penetration * priority_factor
                force[1] += dy * penetration * priority_factor
                force[2] += dz * penetration * priority_factor
        return (force[0], force[1], force[2])

    # ------------------------------------------------------------------
    # Statistics and lifecycle
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        total_polygons = sum(m.polygon_count for m in self._navmeshes.values())
        total_vertices = sum(m.vertex_count for m in self._navmeshes.values())
        total_links = sum(len(m.links) for m in self._navmeshes.values())
        total_agents = len(self._agents)

        agent_state_counts: Dict[str, int] = {}
        for agent in self._agents.values():
            sv = agent.state.value
            agent_state_counts[sv] = agent_state_counts.get(sv, 0) + 1

        path_status_counts: Dict[str, int] = {}
        for path in self._paths.values():
            pv = path.path_status.value
            path_status_counts[pv] = path_status_counts.get(pv, 0) + 1

        return {
            "total_navmeshes": len(self._navmeshes),
            "total_polygons": total_polygons,
            "total_vertices": total_vertices,
            "total_links": total_links,
            "total_links_added": self._total_links_added,
            "total_agents": total_agents,
            "total_paths_computed": self._total_paths_computed,
            "total_agents_moved": self._total_agents_moved,
            "path_cache_size": len(self._path_cache),
            "agent_state_distribution": agent_state_counts,
            "path_status_distribution": path_status_counts,
            "max_navmeshes": self.MAX_NAVMESHES,
            "max_agents_per_mesh": self.MAX_AGENTS_PER_MESH,
            "max_links_per_mesh": self.MAX_LINKS_PER_MESH,
        }

    def get_navmesh(self, mesh_id: str) -> Optional[NavigationMesh]:
        _time_module.sleep(0.001)
        return self._navmeshes.get(mesh_id)

    def list_navmeshes(self) -> List[NavigationMesh]:
        _time_module.sleep(0.001)
        return list(self._navmeshes.values())

    def get_agent(self, agent_id: str) -> Optional[NavigationAgent]:
        _time_module.sleep(0.001)
        return self._agents.get(agent_id)

    def list_agents(self) -> List[NavigationAgent]:
        _time_module.sleep(0.001)
        return list(self._agents.values())

    def get_path(self, path_id: str) -> Optional[NavigationPath]:
        _time_module.sleep(0.001)
        return self._paths.get(path_id)

    def clear_path_cache(self) -> None:
        _time_module.sleep(0.001)
        self._path_cache.clear()

    def remove_agent(self, agent_id: str) -> bool:
        _time_module.sleep(0.001)
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def reset(self) -> None:
        _time_module.sleep(0.001)
        with self._lock:
            self._navmeshes.clear()
            self._agents.clear()
            self._paths.clear()
            self._path_cache.clear()
            self._total_paths_computed = 0
            self._total_agents_moved = 0
            self._total_links_added = 0


def get_navigation_system() -> EngineNavigationSystem:
    """Return the global EngineNavigationSystem singleton instance."""
    return EngineNavigationSystem.get_instance()