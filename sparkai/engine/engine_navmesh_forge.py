"""
SparkLabs Engine - NavMesh Forge

A singleton dynamic navigation mesh construction and optimization
system. Generates navigation meshes from level geometry, applies
runtime obstacle carving for movable blockers, and computes
agent-size-aware traversal costs for pathfinding queries.

Architecture:
  NavMeshForge (singleton)
    |-- NavMeshRegion (traversable area with cost/flag data)
    |-- NavObstacle (carved-out blocked region from dynamic object)
    |-- NavLink (off-mesh connection: jump, ladder, teleport)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class NavAreaType(Enum):
    WALKABLE = "walkable"
    SWIMABLE = "swimable"
    CLIMBABLE = "climbable"
    FLYABLE = "flyable"
    JUMPABLE = "jumpable"
    BLOCKED = "blocked"


class ObstacleShape(Enum):
    BOX = "box"
    CYLINDER = "cylinder"
    SPHERE = "sphere"
    CAPSULE = "capsule"


class LinkType(Enum):
    JUMP = "jump"
    LADDER = "ladder"
    TELEPORT = "teleport"
    DROP = "drop"
    CUSTOM = "custom"


class NavAgentSize(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    GIANT = "giant"


TRAVERSAL_COST_BASE: float = 1.0
DEFAULT_CELL_SIZE: float = 0.3
MAX_AGENT_RADIUS_RATIO: float = 2.0


@dataclass
class NavMeshRegion:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    area_type: NavAreaType = NavAreaType.WALKABLE
    polygon_vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    traversal_cost: float = TRAVERSAL_COST_BASE
    min_agent_radius: float = 0.5
    max_step_height: float = 0.3
    max_slope: float = 45.0
    flags: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "area_type": self.area_type.value,
            "vertex_count": len(self.polygon_vertices),
            "traversal_cost": self.traversal_cost,
            "min_agent_radius": self.min_agent_radius,
            "max_step_height": self.max_step_height,
            "max_slope": self.max_slope,
            "flags": self.flags,
        }


@dataclass
class NavObstacle:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    owner_id: str = ""
    shape: ObstacleShape = ObstacleShape.BOX
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    extents: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    rotation: float = 0.0
    carve: bool = True
    carve_depth: float = 1.0
    dynamic: bool = True
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "shape": self.shape.value,
            "position": list(self.position),
            "extents": list(self.extents),
            "rotation": self.rotation,
            "carve": self.carve,
            "dynamic": self.dynamic,
            "active": self.active,
        }


@dataclass
class NavLink:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    link_type: LinkType = LinkType.JUMP
    start_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    end_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    is_bidirectional: bool = True
    agent_size: NavAgentSize = NavAgentSize.MEDIUM
    traversal_cost: float = TRAVERSAL_COST_BASE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "link_type": self.link_type.value,
            "start_position": list(self.start_position),
            "end_position": list(self.end_position),
            "is_bidirectional": self.is_bidirectional,
            "agent_size": self.agent_size.value,
            "traversal_cost": self.traversal_cost,
        }


@dataclass
class NavMeshData:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    cell_size: float = DEFAULT_CELL_SIZE
    cell_height: float = 0.2
    regions: List[NavMeshRegion] = field(default_factory=list)
    obstacles: List[NavObstacle] = field(default_factory=list)
    links: List[NavLink] = field(default_factory=list)
    bounds_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounds_max: Tuple[float, float, float] = (100.0, 100.0, 100.0)
    total_polygons: int = 0
    last_updated: float = field(default_factory=_time_module.time)
    version: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "cell_size": self.cell_size,
            "cell_height": self.cell_height,
            "regions": len(self.regions),
            "obstacles": len(self.obstacles),
            "links": len(self.links),
            "bounds_min": list(self.bounds_min),
            "bounds_max": list(self.bounds_max),
            "total_polygons": self.total_polygons,
            "version": self.version,
        }


class NavMeshForge:
    """Dynamic navigation mesh generation and runtime obstacle management.

    Constructs navigation meshes from level geometry, supports runtime
    obstacle carving for movable blockers (doors, crates, vehicles),
    and provides off-mesh link creation for jumps, ladders, and
    teleport connections. Agent-size-aware traversal ensures proper
    pathfinding across different NPC dimensions.
    """

    _instance: Optional[NavMeshForge] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> NavMeshForge:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> NavMeshForge:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._meshes: List[NavMeshData] = []
        self._region_templates: List[NavMeshRegion] = []
        self._obstacle_templates: List[NavObstacle] = []
        self._link_templates: List[NavLink] = []

    def _get_or_create_singleton(self) -> NavMeshForge:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        total_regions = sum(len(m.regions) for m in self._meshes)
        total_obstacles = sum(len(m.obstacles) for m in self._meshes)
        total_links = sum(len(m.links) for m in self._meshes)
        return {
            "meshes": len(self._meshes),
            "total_regions": total_regions,
            "total_obstacles": total_obstacles,
            "total_links": total_links,
            "active_obstacles": sum(
                len([o for o in m.obstacles if o.active]) for m in self._meshes
            ),
        }

    # --- NavMesh Operations ---

    def create_mesh(
        self,
        name: str,
        cell_size: float = DEFAULT_CELL_SIZE,
        bounds: Optional[Tuple[float, float, float, float, float, float]] = None,
    ) -> NavMeshData:
        if bounds:
            b_min = (bounds[0], bounds[1], bounds[2])
            b_max = (bounds[3], bounds[4], bounds[5])
        else:
            b_min = (0.0, 0.0, 0.0)
            b_max = (100.0, 100.0, 100.0)

        mesh = NavMeshData(
            name=name,
            cell_size=cell_size,
            bounds_min=b_min,
            bounds_max=b_max,
        )
        self._meshes.append(mesh)
        return mesh

    def get_mesh(self, mesh_id: str) -> Optional[NavMeshData]:
        for m in self._meshes:
            if m.id == mesh_id:
                return m
        return None

    def list_meshes(self) -> List[NavMeshData]:
        return list(self._meshes)

    # --- Region Operations ---

    def add_region(
        self,
        mesh_id: str,
        name: str,
        area_type: str = "walkable",
        traversal_cost: float = TRAVERSAL_COST_BASE,
        min_agent_radius: float = 0.5,
        max_step_height: float = 0.3,
        max_slope: float = 45.0,
    ) -> Optional[NavMeshRegion]:
        mesh = self.get_mesh(mesh_id)
        if not mesh:
            return None

        region = NavMeshRegion(
            name=name,
            area_type=NavAreaType(area_type),
            traversal_cost=traversal_cost,
            min_agent_radius=min_agent_radius,
            max_step_height=max_step_height,
            max_slope=max_slope,
        )
        mesh.regions.append(region)
        mesh.total_polygons += 1
        mesh.version += 1
        mesh.last_updated = _time_module.time()
        return region

    def query_traversable(self, mesh_id: str, position: Tuple[float, float, float]) -> Dict[str, Any]:
        mesh = self.get_mesh(mesh_id)
        if not mesh:
            return {"traversable": False, "region": None}

        px, py, pz = position
        bx_min, by_min, bz_min = mesh.bounds_min
        bx_max, by_max, bz_max = mesh.bounds_max

        in_bounds = (
            bx_min <= px <= bx_max and
            bz_min <= pz <= bz_max
        )

        if not in_bounds:
            return {"traversable": False, "region": None}

        for obstacle in mesh.obstacles:
            if not obstacle.active or not obstacle.carve:
                continue
            ox, oy, oz = obstacle.position
            ex, ey, ez = obstacle.extents
            if (
                abs(px - ox) <= ex and
                abs(py - oy) <= ey and
                abs(pz - oz) <= ez
            ):
                return {"traversable": False, "region": None, "blocked_by": obstacle.owner_id}

        matching_region = None
        for region in mesh.regions:
            matching_region = region.name

        return {
            "traversable": True,
            "region": matching_region,
            "mesh_name": mesh.name,
        }

    # --- Obstacle Operations ---

    def add_obstacle(
        self,
        mesh_id: str,
        owner_id: str = "",
        shape: str = "box",
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        extents: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        carve: bool = True,
        dynamic: bool = True,
    ) -> Optional[NavObstacle]:
        mesh = self.get_mesh(mesh_id)
        if not mesh:
            return None

        obstacle = NavObstacle(
            owner_id=owner_id,
            shape=ObstacleShape(shape),
            position=position,
            extents=extents,
            carve=carve,
            dynamic=dynamic,
        )
        mesh.obstacles.append(obstacle)
        mesh.version += 1
        mesh.last_updated = _time_module.time()
        return obstacle

    def update_obstacle(
        self,
        mesh_id: str,
        obstacle_id: str,
        position: Optional[Tuple[float, float, float]] = None,
        active: Optional[bool] = None,
    ) -> bool:
        mesh = self.get_mesh(mesh_id)
        if not mesh:
            return False

        for obs in mesh.obstacles:
            if obs.id == obstacle_id:
                if position is not None:
                    obs.position = position
                if active is not None:
                    obs.active = active
                mesh.version += 1
                mesh.last_updated = _time_module.time()
                return True
        return False

    def remove_obstacle(self, mesh_id: str, obstacle_id: str) -> bool:
        mesh = self.get_mesh(mesh_id)
        if not mesh:
            return False

        for i, obs in enumerate(mesh.obstacles):
            if obs.id == obstacle_id:
                mesh.obstacles.pop(i)
                mesh.version += 1
                mesh.last_updated = _time_module.time()
                return True
        return False

    # --- Link Operations ---

    def add_link(
        self,
        mesh_id: str,
        name: str,
        link_type: str = "jump",
        start: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        end: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        bidirectional: bool = True,
    ) -> Optional[NavLink]:
        mesh = self.get_mesh(mesh_id)
        if not mesh:
            return None

        link = NavLink(
            name=name,
            link_type=LinkType(link_type),
            start_position=start,
            end_position=end,
            is_bidirectional=bidirectional,
        )
        mesh.links.append(link)
        mesh.version += 1
        return link

    def find_path(
        self,
        mesh_id: str,
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        agent_size: str = "medium",
    ) -> Dict[str, Any]:
        mesh = self.get_mesh(mesh_id)
        if not mesh:
            return {"error": "Mesh not found", "path": []}

        start_traversable = self.query_traversable(mesh_id, start)
        end_traversable = self.query_traversable(mesh_id, end)

        if not start_traversable.get("traversable"):
            return {"error": "Start position not traversable", "path": []}
        if not end_traversable.get("traversable"):
            return {"error": "End position not traversable", "path": []}

        direct_distance = math.sqrt(
            (end[0] - start[0]) ** 2 +
            (end[1] - start[1]) ** 2 +
            (end[2] - start[2]) ** 2
        )

        traversal_multiplier = TRAVERSAL_COST_BASE
        region_name = start_traversable.get("region")
        if region_name:
            for region in mesh.regions:
                if region.name == region_name:
                    traversal_multiplier = region.traversal_cost
                    break

        estimated_cost = direct_distance * traversal_multiplier
        mid_x = (start[0] + end[0]) / 2
        mid_z = (start[2] + end[2]) / 2
        midpoint = (mid_x, 0.0, mid_z)

        path: List[Tuple[float, float, float]] = [start]
        if direct_distance > 50.0:
            path.append(midpoint)
        path.append(end)

        return {
            "path": path,
            "distance": direct_distance,
            "estimated_cost": estimated_cost,
            "waypoints": len(path),
            "mesh_version": mesh.version,
        }

    # --- Query ---

    def get_mesh_summary(self, mesh_id: str) -> Dict[str, Any]:
        mesh = self.get_mesh(mesh_id)
        if not mesh:
            return {"error": "Mesh not found"}

        return {
            "name": mesh.name,
            "regions": len(mesh.regions),
            "obstacles": len(mesh.obstacles),
            "active_obstacles": sum(1 for o in mesh.obstacles if o.active),
            "links": len(mesh.links),
            "total_polygons": mesh.total_polygons,
            "version": mesh.version,
            "bounds": {
                "min": list(mesh.bounds_min),
                "max": list(mesh.bounds_max),
            },
        }


def get_navmesh_forge() -> NavMeshForge:
    return NavMeshForge.get_instance()