"""
SparkLabs Engine - Mass NPC Crowd Simulation System

Manages large-scale NPC crowd behavior for the AI-native game engine.
Provides crowd groups, individual agents, Reynolds flocking (separation,
alignment, cohesion), grid-based pathfinding, panic and evacuation
simulation, density-zone flow control, and social behaviors such as
leader following, group formation, and queue formation.

Architecture:
  CrowdSimulationSystem (singleton)
    |-- CrowdAgentState, CrowdGroupType, FlockingMode, PanicLevel
    |-- CrowdAgent, CrowdGroup, DensityZone, PathfindingNode,
       PathfindingGrid, CrowdEvent, CrowdConfig, CrowdStats,
       CrowdSnapshot
    |-- get_crowd_simulation_system

Core Capabilities:
  - register_group / get_group / list_groups / remove_group
  - get_agent / list_agents / set_agent_target / change_agent_state
  - register_density_zone / get_density_zone / list_density_zones /
    remove_density_zone
  - trigger_panic / calm_panic
  - set_flocking_weights
  - calculate_density / get_crowd_flow
  - spawn_agents / despawn_agents
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`CrowdSimulationSystem.get_instance` or the module-level
:func:`get_crowd_simulation_system` factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_AGENTS: int = 50000
_MAX_GROUPS: int = 500
_MAX_DENSITY_ZONES: int = 200
_MAX_PATHFINDING_GRIDS: int = 100
_MAX_EVENTS: int = 20000
_MAX_NEIGHBOR_SCAN: int = 256


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dist3d(ax: float, ay: float, az: float,
            bx: float, by: float, bz: float) -> float:
    dx = ax - bx
    dy = ay - by
    dz = az - bz
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _normalize2d(vx: float, vy: float) -> Tuple[float, float]:
    mag = math.sqrt(vx * vx + vy * vy)
    if mag < 1e-8:
        return (0.0, 0.0)
    return (vx / mag, vy / mag)


def _dataclass_to_dict(obj: Any) -> Any:
    # Check __dataclass_fields__ BEFORE to_dict to avoid infinite recursion.
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            # Nested dataclasses take priority over to_dict.
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CrowdAgentState(str, Enum):
    """Movement and behavioral state of a crowd agent."""
    IDLE = "idle"
    WALKING = "walking"
    RUNNING = "running"
    PANICKING = "panicking"
    QUEUING = "queuing"
    FLEEING = "fleeing"
    GATHERED = "gathered"
    DISPERSING = "dispersing"


class CrowdGroupType(str, Enum):
    """Category of a crowd group that drives default behavior."""
    PEDESTRIAN = "pedestrian"
    SHOPPERS = "shoppers"
    SOLDIERS = "soldiers"
    PROTESTERS = "protesters"
    REFUGEES = "refugees"
    AUDIENCE = "audience"
    WORKERS = "workers"
    PILGRIMS = "pilgrims"


class FlockingMode(str, Enum):
    """Preset steering configuration for a group of agents."""
    NORMAL = "normal"
    TIGHT = "tight"
    LOOSE = "loose"
    PANIC = "panic"
    MILITARY = "military"
    FLOW = "flow"


class PanicLevel(str, Enum):
    """Severity of a panic event affecting a crowd group."""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class CrowdEventKind(str, Enum):
    """Audit event types emitted by the crowd simulation system."""
    GROUP_REGISTERED = "group_registered"
    GROUP_REMOVED = "group_removed"
    AGENT_SPAWNED = "agent_spawned"
    AGENT_DESPAWNED = "agent_despawned"
    AGENT_STATE_CHANGED = "agent_state_changed"
    AGENT_TARGET_SET = "agent_target_set"
    DENSITY_ZONE_REGISTERED = "density_zone_registered"
    DENSITY_ZONE_REMOVED = "density_zone_removed"
    PANIC_TRIGGERED = "panic_triggered"
    PANIC_CALMED = "panic_calmed"
    FLOCKING_WEIGHTS_SET = "flocking_weights_set"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Flocking preset weights per FlockingMode
# ---------------------------------------------------------------------------

_FLOCKING_PRESETS: Dict[str, Dict[str, float]] = {
    FlockingMode.NORMAL.value: {
        "separation": 1.5, "alignment": 1.0, "cohesion": 1.0, "goal": 1.2,
    },
    FlockingMode.TIGHT.value: {
        "separation": 1.0, "alignment": 1.8, "cohesion": 2.0, "goal": 0.8,
    },
    FlockingMode.LOOSE.value: {
        "separation": 2.0, "alignment": 0.6, "cohesion": 0.5, "goal": 1.5,
    },
    FlockingMode.PANIC.value: {
        "separation": 3.0, "alignment": 0.2, "cohesion": 0.2, "goal": 2.0,
    },
    FlockingMode.MILITARY.value: {
        "separation": 1.2, "alignment": 2.0, "cohesion": 1.6, "goal": 1.8,
    },
    FlockingMode.FLOW.value: {
        "separation": 1.8, "alignment": 1.4, "cohesion": 0.8, "goal": 1.0,
    },
}


def _resolve_flocking_weights(mode: str,
                              custom: Optional[Dict[str, float]] = None
                              ) -> Dict[str, float]:
    base = dict(_FLOCKING_PRESETS.get(mode, _FLOCKING_PRESETS[FlockingMode.NORMAL.value]))
    if custom:
        for k, v in custom.items():
            base[k] = float(v)
    return base


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class CrowdAgent:
    """An individual NPC agent within a crowd.

    Tracks position, velocity, target, behavioral state, fear, and
    social linkage to other agents for leader-following and grouping.
    """
    agent_id: str
    group_id: str
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    velocity_z: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    target_z: float = 0.0
    state: str = CrowdAgentState.IDLE.value
    speed: float = 0.0
    max_speed: float = 1.4
    radius: float = 0.5
    fear_level: float = 0.0
    leadership: float = 0.0
    social_id: str = ""
    queue_position: int = 0
    is_leader: bool = False
    is_active: bool = True
    spawned_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def distance_to_target(self) -> float:
        return _dist3d(self.position_x, self.position_y, self.position_z,
                       self.target_x, self.target_y, self.target_z)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrowdGroup:
    """A coordinated group of agents sharing flocking behavior.

    Stores membership, leader, steering weights, spawn and despawn
    waypoints, formation shape, and an optional target density zone.
    """
    group_id: str
    name: str
    group_type: str = CrowdGroupType.PEDESTRIAN.value
    agent_ids: List[str] = field(default_factory=list)
    leader_id: str = ""
    flocking_mode: str = FlockingMode.NORMAL.value
    behavior_weights: Dict[str, float] = field(default_factory=dict)
    target_zone: str = ""
    spawn_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    despawn_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    formation: str = "free"
    panic_level: str = PanicLevel.NONE.value
    is_active: bool = True
    created_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DensityZone:
    """A circular region enforcing a maximum agent density.

    Used to throttle crowd flow through gates, plazas, and corridors
    by counting agents within the zone radius against the cap.
    """
    zone_id: str
    name: str
    center_x: float
    center_y: float
    center_z: float = 0.0
    radius: float = 10.0
    max_density: int = 50
    current_count: int = 0
    flow_direction: str = ""
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PathfindingNode:
    """A single walkable cell in a grid-based pathfinding graph."""
    node_id: str
    grid_x: int
    grid_y: int
    world_x: float
    world_y: float
    is_walkable: bool = True
    cost: float = 1.0
    neighbors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PathfindingGrid:
    """A grid of pathfinding nodes covering a rectangular world area."""
    grid_id: str
    width: int
    height: int
    cell_size: float = 1.0
    origin_x: float = 0.0
    origin_y: float = 0.0
    nodes: Dict[str, PathfindingNode] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def node_at(self, grid_x: int, grid_y: int) -> Optional[PathfindingNode]:
        nid = f"{self.grid_id}_{grid_x}_{grid_y}"
        return self.nodes.get(nid)

    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        gx = int((world_x - self.origin_x) / self.cell_size)
        gy = int((world_y - self.origin_y) / self.cell_size)
        return (gx, gy)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrowdEvent:
    """An audit event recording a spawn, despawn, or state change."""
    event_id: str
    event_type: str
    timestamp: float
    agent_id: str = ""
    group_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrowdConfig:
    """Global tuning parameters for the crowd simulation."""
    max_agents: int = 50000
    max_groups: int = 500
    max_density_zones: int = 200
    flocking_separation_weight: float = 1.5
    flocking_alignment_weight: float = 1.0
    flocking_cohesion_weight: float = 1.0
    panic_spread_rate: float = 0.5
    panic_decay_rate: float = 0.05
    target_reach_threshold: float = 0.5
    agent_radius: float = 0.5
    max_speed_default: float = 1.4
    tick_rate: float = 10.0
    neighbor_radius: float = 5.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrowdStats:
    """Aggregate statistics for the simulation."""
    total_agents: int = 0
    total_groups: int = 0
    active_panics: int = 0
    total_events: int = 0
    agents_spawned: int = 0
    agents_despawned: int = 0
    panic_events: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrowdSnapshot:
    """A full state snapshot of the simulation at a point in time."""
    timestamp: float
    config: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    groups: List[Dict[str, Any]] = field(default_factory=list)
    agents: List[Dict[str, Any]] = field(default_factory=list)
    density_zones: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Crowd Simulation System
# ---------------------------------------------------------------------------

class CrowdSimulationSystem:
    """Manages mass NPC crowd groups, agents, flocking, panic, and density.

    Implements Reynolds flocking (separation, alignment, cohesion),
    goal seeking, leader following, queue formation, panic propagation
    and decay, density-zone enforcement, and grid-based pathfinding
    graph construction.
    """

    _instance: Optional["CrowdSimulationSystem"] = None
    _lock = threading.RLock()

    # Steering constants
    MAX_STEERING_FORCE: float = 8.0
    SEPARATION_RADIUS_FACTOR: float = 2.0
    QUEUE_SLOW_FACTOR: float = 0.3
    PANIC_SPEED_BOOST: float = 1.8

    def __init__(self) -> None:
        self._agents: Dict[str, CrowdAgent] = {}
        self._groups: Dict[str, CrowdGroup] = {}
        self._density_zones: Dict[str, DensityZone] = {}
        self._grids: Dict[str, PathfindingGrid] = {}
        self._events: List[CrowdEvent] = []
        self._stats = CrowdStats()
        self._config = CrowdConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "CrowdSimulationSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            # Density zones: market square, city gate, tavern area, temple plaza
            zones_data = [
                ("zone_market_square", "Market Square",
                 50.0, 50.0, 0.0, 15.0, 60, "north",
                 {"color": "#FFD700", "landmark": "market_stalls"}),
                ("zone_city_gate", "City Gate",
                 100.0, 5.0, 0.0, 8.0, 30, "east",
                 {"color": "#8B4513", "landmark": "main_gate"}),
                ("zone_tavern_area", "Tavern Area",
                 30.0, 80.0, 0.0, 10.0, 40, "west",
                 {"color": "#FF8C00", "landmark": "tavern"}),
                ("zone_temple_plaza", "Temple Plaza",
                 80.0, 90.0, 0.0, 12.0, 50, "south",
                 {"color": "#E6E6FA", "landmark": "temple"}),
            ]
            for zid, zname, cx, cy, cz, rad, md, flow, md_meta in zones_data:
                zone = DensityZone(
                    zone_id=zid, name=zname,
                    center_x=cx, center_y=cy, center_z=cz,
                    radius=rad, max_density=md,
                    flow_direction=flow, metadata=dict(md_meta),
                )
                self._density_zones[zid] = zone

            # Pathfinding grid covering the town area (0..120 x 0..110)
            self._build_seed_grid("grid_town", 0.0, 0.0, 120, 110, 2.0)

            # Crowd groups with seeded agents
            self._seed_group_marketplace_shoppers()
            self._seed_group_city_guards_patrol()
            self._seed_group_festival_crowd()
            self._seed_group_refugee_caravan()
            self._seed_group_worker_crew()

            self._refresh_density_counts()
            self._update_stats()
            self._initialized = True

    def _build_seed_grid(self, grid_id: str, origin_x: float, origin_y: float,
                         width: int, height: int, cell_size: float) -> None:
        grid = PathfindingGrid(
            grid_id=grid_id, width=width, height=height,
            cell_size=cell_size, origin_x=origin_x, origin_y=origin_y,
        )
        for gy in range(height):
            for gx in range(width):
                nid = f"{grid_id}_{gx}_{gy}"
                node = PathfindingNode(
                    node_id=nid, grid_x=gx, grid_y=gy,
                    world_x=origin_x + gx * cell_size,
                    world_y=origin_y + gy * cell_size,
                    is_walkable=True, cost=1.0,
                )
                # Link four-connected neighbors
                if gx > 0:
                    node.neighbors.append(f"{grid_id}_{gx - 1}_{gy}")
                if gx < width - 1:
                    node.neighbors.append(f"{grid_id}_{gx + 1}_{gy}")
                if gy > 0:
                    node.neighbors.append(f"{grid_id}_{gx}_{gy - 1}")
                if gy < height - 1:
                    node.neighbors.append(f"{grid_id}_{gx}_{gy + 1}")
                grid.nodes[nid] = node
        self._grids[grid_id] = grid

    def _seed_group_marketplace_shoppers(self) -> None:
        gid = "grp_marketplace_shoppers"
        group = CrowdGroup(
            group_id=gid, name="Marketplace Shoppers",
            group_type=CrowdGroupType.SHOPPERS.value,
            flocking_mode=FlockingMode.LOOSE.value,
            behavior_weights=_resolve_flocking_weights(FlockingMode.LOOSE.value),
            target_zone="zone_market_square",
            spawn_point=(45.0, 48.0, 0.0),
            despawn_point=(58.0, 55.0, 0.0),
            formation="free",
            metadata={"scene": "market", "mood": "bustling"},
        )
        self._groups[gid] = group
        shopper_starts = [
            (46.0, 47.0, 52.0, 53.0), (48.0, 50.0, 54.0, 49.0),
            (51.0, 46.0, 49.0, 55.0), (53.0, 52.0, 47.0, 48.0),
            (49.0, 54.0, 55.0, 51.0), (47.0, 49.0, 52.0, 47.0),
            (54.0, 48.0, 48.0, 54.0), (50.0, 51.0, 46.0, 52.0),
        ]
        leader_id = ""
        for idx, (sx, sy, tx, ty) in enumerate(shopper_starts):
            aid = f"agent_shopper_{idx + 1:02d}"
            is_lead = idx == 0
            agent = CrowdAgent(
                agent_id=aid, group_id=gid,
                position_x=sx, position_y=sy, position_z=0.0,
                velocity_x=0.0, velocity_y=0.0, velocity_z=0.0,
                target_x=tx, target_y=ty, target_z=0.0,
                state=CrowdAgentState.WALKING.value,
                speed=0.0, max_speed=1.2, radius=0.45,
                fear_level=0.0, leadership=0.6 if is_lead else 0.1,
                social_id="shopper_group_a" if is_lead else "shopper_group_b",
                is_leader=is_lead,
                metadata={"role": "shopper", "stall": idx % 4},
            )
            self._agents[aid] = agent
            group.agent_ids.append(aid)
            if is_lead:
                leader_id = aid
        group.leader_id = leader_id

    def _seed_group_city_guards_patrol(self) -> None:
        gid = "grp_city_guards_patrol"
        group = CrowdGroup(
            group_id=gid, name="City Guards Patrol",
            group_type=CrowdGroupType.SOLDIERS.value,
            flocking_mode=FlockingMode.MILITARY.value,
            behavior_weights=_resolve_flocking_weights(FlockingMode.MILITARY.value),
            target_zone="zone_city_gate",
            spawn_point=(96.0, 2.0, 0.0),
            despawn_point=(104.0, 8.0, 0.0),
            formation="column",
            metadata={"scene": "patrol", "faction": "city_watch"},
        )
        self._groups[gid] = group
        patrol_route = [
            (97.0, 3.0, 103.0, 7.0), (98.0, 4.0, 102.0, 6.0),
            (99.0, 3.0, 101.0, 5.0), (100.0, 5.0, 98.0, 4.0),
            (101.0, 6.0, 97.0, 3.0), (102.0, 4.0, 100.0, 6.0),
        ]
        leader_id = ""
        for idx, (sx, sy, tx, ty) in enumerate(patrol_route):
            aid = f"agent_guard_{idx + 1:02d}"
            is_lead = idx == 0
            agent = CrowdAgent(
                agent_id=aid, group_id=gid,
                position_x=sx, position_y=sy, position_z=0.0,
                velocity_x=0.0, velocity_y=0.0, velocity_z=0.0,
                target_x=tx, target_y=ty, target_z=0.0,
                state=CrowdAgentState.WALKING.value,
                speed=0.0, max_speed=1.6, radius=0.5,
                fear_level=0.0, leadership=0.9 if is_lead else 0.2,
                social_id="guard_squad_alpha",
                is_leader=is_lead,
                metadata={"rank": "captain" if is_lead else "soldier",
                          "weapon": "halberd"},
            )
            self._agents[aid] = agent
            group.agent_ids.append(aid)
            if is_lead:
                leader_id = aid
        group.leader_id = leader_id

    def _seed_group_festival_crowd(self) -> None:
        gid = "grp_festival_crowd"
        group = CrowdGroup(
            group_id=gid, name="Festival Crowd",
            group_type=CrowdGroupType.AUDIENCE.value,
            flocking_mode=FlockingMode.TIGHT.value,
            behavior_weights=_resolve_flocking_weights(FlockingMode.TIGHT.value),
            target_zone="zone_temple_plaza",
            spawn_point=(76.0, 86.0, 0.0),
            despawn_point=(84.0, 94.0, 0.0),
            formation="circle",
            metadata={"scene": "festival", "event": "spring_celebration"},
        )
        self._groups[gid] = group
        festival_starts = [
            (77.0, 87.0, 82.0, 92.0), (79.0, 88.0, 81.0, 91.0),
            (81.0, 86.0, 80.0, 93.0), (83.0, 89.0, 78.0, 90.0),
            (78.0, 91.0, 83.0, 88.0), (82.0, 90.0, 79.0, 89.0),
            (80.0, 92.0, 77.0, 87.0), (76.0, 89.0, 84.0, 91.0),
        ]
        leader_id = ""
        for idx, (sx, sy, tx, ty) in enumerate(festival_starts):
            aid = f"agent_festival_{idx + 1:02d}"
            is_lead = idx == 0
            agent = CrowdAgent(
                agent_id=aid, group_id=gid,
                position_x=sx, position_y=sy, position_z=0.0,
                velocity_x=0.0, velocity_y=0.0, velocity_z=0.0,
                target_x=tx, target_y=ty, target_z=0.0,
                state=CrowdAgentState.GATHERED.value,
                speed=0.0, max_speed=1.0, radius=0.4,
                fear_level=0.0, leadership=0.5 if is_lead else 0.1,
                social_id="festival_audience",
                is_leader=is_lead,
                metadata={"mood": "cheerful", "performance": idx % 3},
            )
            self._agents[aid] = agent
            group.agent_ids.append(aid)
            if is_lead:
                leader_id = aid
        group.leader_id = leader_id

    def _seed_group_refugee_caravan(self) -> None:
        gid = "grp_refugee_caravan"
        group = CrowdGroup(
            group_id=gid, name="Refugee Caravan",
            group_type=CrowdGroupType.REFUGEES.value,
            flocking_mode=FlockingMode.FLOW.value,
            behavior_weights=_resolve_flocking_weights(FlockingMode.FLOW.value),
            target_zone="zone_city_gate",
            spawn_point=(20.0, 10.0, 0.0),
            despawn_point=(100.0, 5.0, 0.0),
            formation="column",
            metadata={"scene": "caravan", "origin": "border_lands"},
        )
        self._groups[gid] = group
        caravan_starts = [
            (21.0, 11.0, 100.0, 5.0), (22.0, 9.0, 100.0, 5.0),
            (20.0, 12.0, 100.0, 5.0), (23.0, 10.0, 100.0, 5.0),
            (19.0, 11.0, 100.0, 5.0),
        ]
        leader_id = ""
        for idx, (sx, sy, tx, ty) in enumerate(caravan_starts):
            aid = f"agent_refugee_{idx + 1:02d}"
            is_lead = idx == 0
            agent = CrowdAgent(
                agent_id=aid, group_id=gid,
                position_x=sx, position_y=sy, position_z=0.0,
                velocity_x=0.0, velocity_y=0.0, velocity_z=0.0,
                target_x=tx, target_y=ty, target_z=0.0,
                state=CrowdAgentState.WALKING.value,
                speed=0.0, max_speed=0.9, radius=0.45,
                fear_level=0.2, leadership=0.7 if is_lead else 0.1,
                social_id="caravan_lead" if is_lead else "caravan_follow",
                is_leader=is_lead,
                metadata={"burden": idx % 2 == 0, "family": "fam_a"},
            )
            self._agents[aid] = agent
            group.agent_ids.append(aid)
            if is_lead:
                leader_id = aid
        group.leader_id = leader_id

    def _seed_group_worker_crew(self) -> None:
        gid = "grp_worker_crew"
        group = CrowdGroup(
            group_id=gid, name="Worker Crew",
            group_type=CrowdGroupType.WORKERS.value,
            flocking_mode=FlockingMode.NORMAL.value,
            behavior_weights=_resolve_flocking_weights(FlockingMode.NORMAL.value),
            target_zone="zone_tavern_area",
            spawn_point=(26.0, 78.0, 0.0),
            despawn_point=(34.0, 82.0, 0.0),
            formation="line",
            metadata={"scene": "construction", "task": "masonry"},
        )
        self._groups[gid] = group
        worker_starts = [
            (27.0, 77.0, 33.0, 81.0), (28.0, 79.0, 32.0, 80.0),
            (29.0, 78.0, 31.0, 82.0), (26.0, 80.0, 34.0, 79.0),
            (30.0, 81.0, 30.0, 78.0),
        ]
        leader_id = ""
        for idx, (sx, sy, tx, ty) in enumerate(worker_starts):
            aid = f"agent_worker_{idx + 1:02d}"
            is_lead = idx == 0
            agent = CrowdAgent(
                agent_id=aid, group_id=gid,
                position_x=sx, position_y=sy, position_z=0.0,
                velocity_x=0.0, velocity_y=0.0, velocity_z=0.0,
                target_x=tx, target_y=ty, target_z=0.0,
                state=CrowdAgentState.QUEUING.value,
                speed=0.0, max_speed=1.1, radius=0.5,
                fear_level=0.0, leadership=0.8 if is_lead else 0.1,
                social_id="crew_bravo",
                queue_position=idx,
                is_leader=is_lead,
                metadata={"trade": "mason", "shift": "day"},
            )
            self._agents[aid] = agent
            group.agent_ids.append(aid)
            if is_lead:
                leader_id = aid
        group.leader_id = leader_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_event(self, event_type: str, data: Dict[str, Any],
                   agent_id: str = "", group_id: str = "") -> None:
        self._event_counter += 1
        ev = CrowdEvent(
            event_id=f"cevt_{self._event_counter:06d}",
            event_type=event_type, timestamp=_now(),
            agent_id=agent_id, group_id=group_id, data=data,
        )
        self._events.append(ev)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _update_stats(self) -> None:
        self._stats.total_agents = sum(
            1 for a in self._agents.values() if a.is_active
        )
        self._stats.total_groups = len(self._groups)
        self._stats.active_panics = sum(
            1 for g in self._groups.values()
            if g.panic_level != PanicLevel.NONE.value
        )
        self._stats.total_events = len(self._events)

    def _refresh_density_counts(self) -> None:
        for zone in self._density_zones.values():
            count = 0
            for agent in self._agents.values():
                if not agent.is_active:
                    continue
                d = _dist3d(agent.position_x, agent.position_y, agent.position_z,
                            zone.center_x, zone.center_y, zone.center_z)
                if d <= zone.radius:
                    count += 1
            zone.current_count = count

    def _resolve_state(self, state: str) -> str:
        try:
            return CrowdAgentState(state).value
        except ValueError:
            return CrowdAgentState.IDLE.value

    def _resolve_group_type(self, group_type: str) -> str:
        try:
            return CrowdGroupType(group_type).value
        except ValueError:
            return CrowdGroupType.PEDESTRIAN.value

    def _resolve_flocking_mode(self, mode: str) -> str:
        try:
            return FlockingMode(mode).value
        except ValueError:
            return FlockingMode.NORMAL.value

    def _resolve_panic_level(self, level: str) -> str:
        try:
            return PanicLevel(level).value
        except ValueError:
            return PanicLevel.NONE.value

    def _panic_level_from_intensity(self, intensity: float) -> str:
        if intensity >= 0.9:
            return PanicLevel.EXTREME.value
        if intensity >= 0.6:
            return PanicLevel.HIGH.value
        if intensity >= 0.3:
            return PanicLevel.MODERATE.value
        if intensity > 0.0:
            return PanicLevel.LOW.value
        return PanicLevel.NONE.value

    # ------------------------------------------------------------------
    # Group Management
    # ------------------------------------------------------------------

    def register_group(self, group_id: str, name: str,
                       group_type: str = "pedestrian",
                       agent_count: int = 10,
                       spawn_point: Optional[Tuple[float, float, float]] = None,
                       target_point: Optional[Tuple[float, float, float]] = None,
                       flocking_mode: str = "normal",
                       leader_id: str = "",
                       formation: str = "free",
                       metadata: Optional[Dict[str, Any]] = None
                       ) -> Tuple[bool, str, Optional[CrowdGroup]]:
        with _LOCK:
            if group_id in self._groups:
                return False, "group_exists", None
            if len(self._groups) >= self._config.max_groups:
                return False, "max_groups", None
            spawn = spawn_point if spawn_point else (0.0, 0.0, 0.0)
            despawn = target_point if target_point else spawn
            resolved_mode = self._resolve_flocking_mode(flocking_mode)
            group = CrowdGroup(
                group_id=group_id, name=name,
                group_type=self._resolve_group_type(group_type),
                flocking_mode=resolved_mode,
                behavior_weights=_resolve_flocking_weights(resolved_mode),
                spawn_point=spawn, despawn_point=despawn,
                formation=formation,
                leader_id=leader_id,
                metadata=metadata or {},
            )
            self._groups[group_id] = group

            # Spawn the requested number of agents for the group.
            if agent_count > 0:
                self._spawn_group_agents(group, agent_count, spawn, target_point)

            self._log_event(CrowdEventKind.GROUP_REGISTERED.value,
                            {"name": name, "agent_count": agent_count},
                            group_id=group_id)
            self._update_stats()
            return True, "registered", group

    def _spawn_group_agents(self, group: CrowdGroup, count: int,
                            spawn_point: Tuple[float, float, float],
                            target_point: Optional[Tuple[float, float, float]]
                            ) -> int:
        sx, sy, sz = spawn_point
        tx, ty, tz = target_point if target_point else (sx, sy, sz)
        created = 0
        for i in range(count):
            if len(self._agents) >= self._config.max_agents:
                break
            aid = _new_id(f"agent_{group.group_id}")
            offset_x = (i % 5) * 0.8
            offset_y = (i // 5) * 0.8
            is_lead = (i == 0 and not group.leader_id)
            agent = CrowdAgent(
                agent_id=aid, group_id=group.group_id,
                position_x=sx + offset_x, position_y=sy + offset_y,
                position_z=sz,
                target_x=tx + offset_x, target_y=ty + offset_y, target_z=tz,
                state=CrowdAgentState.WALKING.value,
                max_speed=self._config.max_speed_default,
                radius=self._config.agent_radius,
                leadership=0.7 if is_lead else 0.1,
                is_leader=is_lead,
            )
            self._agents[aid] = agent
            group.agent_ids.append(aid)
            if is_lead:
                group.leader_id = aid
            created += 1
        return created

    def get_group(self, group_id: str) -> Optional[CrowdGroup]:
        with _LOCK:
            return self._groups.get(group_id)

    def list_groups(self, group_type: str = "",
                    active_only: bool = False) -> List[CrowdGroup]:
        with _LOCK:
            results = list(self._groups.values())
            if group_type:
                results = [g for g in results if g.group_type == group_type]
            if active_only:
                results = [g for g in results if g.is_active]
            return results

    def remove_group(self, group_id: str) -> Tuple[bool, str]:
        with _LOCK:
            group = self._groups.get(group_id)
            if group is None:
                return False, "group_not_found"
            for aid in list(group.agent_ids):
                self._agents.pop(aid, None)
            del self._groups[group_id]
            self._log_event(CrowdEventKind.GROUP_REMOVED.value,
                            {"group_id": group_id}, group_id=group_id)
            self._refresh_density_counts()
            self._update_stats()
            return True, "removed"

    # ------------------------------------------------------------------
    # Agent Management
    # ------------------------------------------------------------------

    def get_agent(self, agent_id: str) -> Optional[CrowdAgent]:
        with _LOCK:
            return self._agents.get(agent_id)

    def list_agents(self, group_id: str = "",
                    state: str = "") -> List[CrowdAgent]:
        with _LOCK:
            results = list(self._agents.values())
            if group_id:
                results = [a for a in results if a.group_id == group_id]
            if state:
                results = [a for a in results if a.state == state]
            return results

    def set_agent_target(self, agent_id: str, target_x: float,
                         target_y: float, target_z: float = 0.0
                         ) -> Tuple[bool, str]:
        with _LOCK:
            agent = self._agents.get(agent_id)
            if agent is None:
                return False, "agent_not_found"
            agent.target_x = target_x
            agent.target_y = target_y
            agent.target_z = target_z
            if agent.state == CrowdAgentState.IDLE.value:
                agent.state = CrowdAgentState.WALKING.value
            self._log_event(CrowdEventKind.AGENT_TARGET_SET.value,
                            {"target": [target_x, target_y, target_z]},
                            agent_id=agent_id)
            return True, "target_set"

    def change_agent_state(self, agent_id: str,
                           new_state: str
                           ) -> Tuple[bool, str, Optional[CrowdAgent]]:
        with _LOCK:
            agent = self._agents.get(agent_id)
            if agent is None:
                return False, "agent_not_found", None
            resolved = self._resolve_state(new_state)
            old_state = agent.state
            agent.state = resolved
            if resolved == CrowdAgentState.IDLE.value:
                agent.velocity_x = 0.0
                agent.velocity_y = 0.0
                agent.velocity_z = 0.0
                agent.speed = 0.0
            elif resolved == CrowdAgentState.RUNNING.value:
                agent.max_speed = self._config.max_speed_default * 1.8
            elif resolved == CrowdAgentState.WALKING.value:
                agent.max_speed = self._config.max_speed_default
            self._log_event(CrowdEventKind.AGENT_STATE_CHANGED.value,
                            {"old_state": old_state, "new_state": resolved},
                            agent_id=agent_id)
            return True, "state_changed", agent

    # ------------------------------------------------------------------
    # Density Zone Management
    # ------------------------------------------------------------------

    def register_density_zone(self, zone_id: str, name: str,
                              center_x: float, center_y: float, center_z: float,
                              radius: float, max_density: int = 50,
                              flow_direction: str = "",
                              metadata: Optional[Dict[str, Any]] = None
                              ) -> Tuple[bool, str, Optional[DensityZone]]:
        with _LOCK:
            if zone_id in self._density_zones:
                return False, "zone_exists", None
            if len(self._density_zones) >= self._config.max_density_zones:
                return False, "max_density_zones", None
            zone = DensityZone(
                zone_id=zone_id, name=name,
                center_x=center_x, center_y=center_y, center_z=center_z,
                radius=radius, max_density=max_density,
                flow_direction=flow_direction, metadata=metadata or {},
            )
            self._density_zones[zone_id] = zone
            self._refresh_density_counts()
            self._log_event(CrowdEventKind.DENSITY_ZONE_REGISTERED.value,
                            {"name": name, "radius": radius},
                            group_id=zone_id)
            self._update_stats()
            return True, "registered", zone

    def get_density_zone(self, zone_id: str) -> Optional[DensityZone]:
        with _LOCK:
            return self._density_zones.get(zone_id)

    def list_density_zones(self, active_only: bool = False) -> List[DensityZone]:
        with _LOCK:
            results = list(self._density_zones.values())
            if active_only:
                results = [z for z in results if z.is_active]
            return results

    def remove_density_zone(self, zone_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if zone_id not in self._density_zones:
                return False, "zone_not_found"
            del self._density_zones[zone_id]
            self._log_event(CrowdEventKind.DENSITY_ZONE_REMOVED.value,
                            {"zone_id": zone_id}, group_id=zone_id)
            return True, "removed"

    # ------------------------------------------------------------------
    # Panic Simulation
    # ------------------------------------------------------------------

    def trigger_panic(self, group_id: str, epicenter_x: float,
                      epicenter_y: float, epicenter_z: float,
                      intensity: float = 0.8,
                      spread_radius: float = 20.0) -> Tuple[bool, str]:
        with _LOCK:
            group = self._groups.get(group_id)
            if group is None:
                return False, "group_not_found"
            intensity = _clamp(intensity, 0.0, 1.0)
            panic_lvl = self._panic_level_from_intensity(intensity)
            group.panic_level = panic_lvl
            group.flocking_mode = FlockingMode.PANIC.value
            group.behavior_weights = _resolve_flocking_weights(
                FlockingMode.PANIC.value,
                {"goal": 2.5},
            )
            affected = 0
            for aid in group.agent_ids:
                agent = self._agents.get(aid)
                if agent is None or not agent.is_active:
                    continue
                d = _dist3d(agent.position_x, agent.position_y, agent.position_z,
                            epicenter_x, epicenter_y, epicenter_z)
                if d <= spread_radius:
                    proximity = 1.0 - (d / spread_radius) if spread_radius > 0 else 1.0
                    agent.fear_level = _clamp(
                        agent.fear_level + intensity * proximity, 0.0, 1.0)
                    agent.state = CrowdAgentState.PANICKING.value
                    agent.max_speed = self._config.max_speed_default * self.PANIC_SPEED_BOOST
                    # Flee directly away from the epicenter.
                    flee_vx = agent.position_x - epicenter_x
                    flee_vy = agent.position_y - epicenter_y
                    nx, ny = _normalize2d(flee_vx, flee_vy)
                    agent.velocity_x = nx * agent.max_speed
                    agent.velocity_y = ny * agent.max_speed
                    agent.speed = agent.max_speed
                    affected += 1
            self._stats.panic_events += 1
            self._log_event(CrowdEventKind.PANIC_TRIGGERED.value,
                            {"intensity": intensity, "panic_level": panic_lvl,
                             "spread_radius": spread_radius,
                             "affected": affected},
                            group_id=group_id)
            self._update_stats()
            return True, "panic_triggered"

    def calm_panic(self, group_id: str, calm_rate: float = 0.1
                   ) -> Tuple[bool, str]:
        with _LOCK:
            group = self._groups.get(group_id)
            if group is None:
                return False, "group_not_found"
            calm_rate = _clamp(calm_rate, 0.0, 1.0)
            for aid in group.agent_ids:
                agent = self._agents.get(aid)
                if agent is None or not agent.is_active:
                    continue
                agent.fear_level = _clamp(agent.fear_level - calm_rate, 0.0, 1.0)
                if agent.fear_level <= 0.05:
                    agent.fear_level = 0.0
                    if agent.state == CrowdAgentState.PANICKING.value:
                        agent.state = CrowdAgentState.WALKING.value
                    agent.max_speed = self._config.max_speed_default
            avg_fear = 0.0
            active_count = 0
            for aid in group.agent_ids:
                agent = self._agents.get(aid)
                if agent and agent.is_active:
                    avg_fear += agent.fear_level
                    active_count += 1
            if active_count > 0:
                avg_fear /= active_count
            if avg_fear <= 0.05:
                group.panic_level = PanicLevel.NONE.value
                group.flocking_mode = FlockingMode.NORMAL.value
                group.behavior_weights = _resolve_flocking_weights(
                    FlockingMode.NORMAL.value)
            else:
                group.panic_level = self._panic_level_from_intensity(avg_fear)
            self._log_event(CrowdEventKind.PANIC_CALMED.value,
                            {"calm_rate": calm_rate, "avg_fear": avg_fear},
                            group_id=group_id)
            self._update_stats()
            return True, "panic_calmed"

    # ------------------------------------------------------------------
    # Flocking Configuration
    # ------------------------------------------------------------------

    def set_flocking_weights(self, group_id: str, separation: float,
                             alignment: float,
                             cohesion: float
                             ) -> Tuple[bool, str, Optional[CrowdGroup]]:
        with _LOCK:
            group = self._groups.get(group_id)
            if group is None:
                return False, "group_not_found", None
            group.behavior_weights = {
                "separation": float(separation),
                "alignment": float(alignment),
                "cohesion": float(cohesion),
                "goal": group.behavior_weights.get("goal", 1.2),
            }
            self._log_event(CrowdEventKind.FLOCKING_WEIGHTS_SET.value,
                            {"separation": separation, "alignment": alignment,
                             "cohesion": cohesion},
                            group_id=group_id)
            return True, "weights_set", group

    # ------------------------------------------------------------------
    # Density and Flow Analysis
    # ------------------------------------------------------------------

    def calculate_density(self, zone_id: str) -> Optional[float]:
        with _LOCK:
            zone = self._density_zones.get(zone_id)
            if zone is None:
                return None
            count = 0
            for agent in self._agents.values():
                if not agent.is_active:
                    continue
                d = _dist3d(agent.position_x, agent.position_y, agent.position_z,
                            zone.center_x, zone.center_y, zone.center_z)
                if d <= zone.radius:
                    count += 1
            zone.current_count = count
            area = math.pi * zone.radius * zone.radius
            if area < 1e-8:
                return 0.0
            return count / area

    def get_crowd_flow(self, zone_x: float, zone_y: float,
                       radius: float = 10.0) -> Optional[Dict[str, Any]]:
        with _LOCK:
            if radius <= 0.0:
                return None
            count = 0
            sum_vx = 0.0
            sum_vy = 0.0
            sum_speed = 0.0
            for agent in self._agents.values():
                if not agent.is_active:
                    continue
                d = _dist3d(agent.position_x, agent.position_y, agent.position_z,
                            zone_x, zone_y, 0.0)
                if d <= radius:
                    count += 1
                    sum_vx += agent.velocity_x
                    sum_vy += agent.velocity_y
                    sum_speed += agent.speed
            if count == 0:
                return {
                    "center": [zone_x, zone_y],
                    "radius": radius,
                    "agent_count": 0,
                    "avg_velocity": [0.0, 0.0],
                    "avg_speed": 0.0,
                    "density": 0.0,
                }
            area = math.pi * radius * radius
            return {
                "center": [zone_x, zone_y],
                "radius": radius,
                "agent_count": count,
                "avg_velocity": [round(sum_vx / count, 4),
                                 round(sum_vy / count, 4)],
                "avg_speed": round(sum_speed / count, 4),
                "density": round(count / area, 4) if area > 0 else 0.0,
            }

    # ------------------------------------------------------------------
    # Spawn / Despawn
    # ------------------------------------------------------------------

    def spawn_agents(self, group_id: str, count: int,
                     spawn_point: Optional[Tuple[float, float, float]] = None
                     ) -> Tuple[bool, str, int]:
        with _LOCK:
            group = self._groups.get(group_id)
            if group is None:
                return False, "group_not_found", 0
            if count <= 0:
                return False, "invalid_count", 0
            spawn = spawn_point if spawn_point else group.spawn_point
            created = self._spawn_group_agents(group, count, spawn, None)
            self._stats.agents_spawned += created
            self._log_event(CrowdEventKind.AGENT_SPAWNED.value,
                            {"count": created, "spawn_point": list(spawn)},
                            group_id=group_id)
            self._refresh_density_counts()
            self._update_stats()
            return True, "spawned", created

    def despawn_agents(self, group_id: str, count: int = 1
                       ) -> Tuple[bool, str, int]:
        with _LOCK:
            group = self._groups.get(group_id)
            if group is None:
                return False, "group_not_found", 0
            if count <= 0:
                return False, "invalid_count", 0
            removed = 0
            # Despawn from the tail of the member list first.
            for aid in reversed(list(group.agent_ids)):
                if removed >= count:
                    break
                agent = self._agents.pop(aid, None)
                if agent is not None:
                    agent.is_active = False
                    group.agent_ids.remove(aid)
                    if group.leader_id == aid:
                        group.leader_id = group.agent_ids[0] if group.agent_ids else ""
                    removed += 1
            self._stats.agents_despawned += removed
            self._log_event(CrowdEventKind.AGENT_DESPAWNED.value,
                            {"count": removed}, group_id=group_id)
            self._refresh_density_counts()
            self._update_stats()
            return True, "despawned", removed

    # ------------------------------------------------------------------
    # Flocking computation (Reynolds boids)
    # ------------------------------------------------------------------

    def _compute_flocking(self, agent: CrowdAgent,
                          neighbors: List[CrowdAgent],
                          weights: Dict[str, float]
                          ) -> Tuple[float, float]:
        sep_x, sep_y = 0.0, 0.0
        align_x, align_y = 0.0, 0.0
        coh_x, coh_y = 0.0, 0.0
        sep_count = 0

        min_sep = agent.radius * self.SEPARATION_RADIUS_FACTOR
        for nb in neighbors:
            if nb.agent_id == agent.agent_id:
                continue
            dx = agent.position_x - nb.position_x
            dy = agent.position_y - nb.position_y
            dist = math.sqrt(dx * dx + dy * dy)
            # Separation
            if 1e-8 < dist < min_sep:
                weight = (min_sep - dist) / min_sep
                sep_x += (dx / dist) * weight
                sep_y += (dy / dist) * weight
                sep_count += 1
            # Alignment accumulator
            align_x += nb.velocity_x
            align_y += nb.velocity_y
            # Cohesion accumulator
            coh_x += nb.position_x
            coh_y += nb.position_y

        n_count = max(1, len(neighbors))
        fx, fy = 0.0, 0.0
        sw = weights.get("separation", self._config.flocking_separation_weight)
        aw = weights.get("alignment", self._config.flocking_alignment_weight)
        cw = weights.get("cohesion", self._config.flocking_cohesion_weight)

        if sep_count > 0:
            sep_x /= sep_count
            sep_y /= sep_count
            nx, ny = _normalize2d(sep_x, sep_y)
            fx += nx * sw
            fy += ny * sw

        align_x /= n_count
        align_y /= n_count
        anx, any_ = _normalize2d(align_x, align_y)
        fx += anx * aw
        fy += any_ * aw

        coh_x = coh_x / n_count - agent.position_x
        coh_y = coh_y / n_count - agent.position_y
        cnx, cny = _normalize2d(coh_x, coh_y)
        fx += cnx * cw
        fy += cny * cw

        # Clamp to maximum steering force.
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > self.MAX_STEERING_FORCE:
            fx = fx / mag * self.MAX_STEERING_FORCE
            fy = fy / mag * self.MAX_STEERING_FORCE
        return (fx, fy)

    def _compute_goal_force(self, agent: CrowdAgent,
                            goal_weight: float) -> Tuple[float, float]:
        dx = agent.target_x - agent.position_x
        dy = agent.target_y - agent.position_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1e-8:
            return (0.0, 0.0)
        desired_x = (dx / dist) * agent.max_speed
        desired_y = (dy / dist) * agent.max_speed
        steer_x = (desired_x - agent.velocity_x) * goal_weight
        steer_y = (desired_y - agent.velocity_y) * goal_weight
        return (steer_x, steer_y)

    def _compute_leader_follow(self, agent: CrowdAgent,
                               leader: Optional[CrowdAgent]
                               ) -> Tuple[float, float]:
        if leader is None or leader.agent_id == agent.agent_id:
            return (0.0, 0.0)
        dx = leader.position_x - agent.position_x
        dy = leader.position_y - agent.position_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1e-8:
            return (0.0, 0.0)
        desired_x = (dx / dist) * agent.max_speed
        desired_y = (dy / dist) * agent.max_speed
        return (desired_x - agent.velocity_x, desired_y - agent.velocity_y)

    def _find_neighbors(self, agent: CrowdAgent,
                        radius: float) -> List[CrowdAgent]:
        neighbors: List[CrowdAgent] = []
        r_sq = radius * radius
        scanned = 0
        for other in self._agents.values():
            if scanned >= _MAX_NEIGHBOR_SCAN:
                break
            if not other.is_active:
                continue
            if other.agent_id == agent.agent_id:
                continue
            dx = agent.position_x - other.position_x
            dy = agent.position_y - other.position_y
            if dx * dx + dy * dy <= r_sq:
                neighbors.append(other)
                scanned += 1
        return neighbors

    # ------------------------------------------------------------------
    # Tick / Simulation Step
    # ------------------------------------------------------------------

    def tick(self, dt: float = 0.1) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            threshold = self._config.target_reach_threshold
            neighbor_radius = self._config.neighbor_radius
            decay = self._config.panic_decay_rate

            moved_agents = 0
            reached_targets = 0
            state_transitions = 0

            for agent in self._agents.values():
                if not agent.is_active:
                    continue
                group = self._groups.get(agent.group_id)

                # Decay fear over time for panicked agents.
                if agent.fear_level > 0.0:
                    agent.fear_level = _clamp(
                        agent.fear_level - decay * dt, 0.0, 1.0)
                    if agent.fear_level <= 0.02:
                        agent.fear_level = 0.0
                        if agent.state == CrowdAgentState.PANICKING.value:
                            agent.state = CrowdAgentState.WALKING.value
                            agent.max_speed = self._config.max_speed_default
                            state_transitions += 1

                neighbors = self._find_neighbors(agent, neighbor_radius)
                weights = (group.behavior_weights if group
                           else _resolve_flocking_weights(FlockingMode.NORMAL.value))

                # Flocking steering.
                fx, fy = self._compute_flocking(agent, neighbors, weights)

                # Goal seeking.
                goal_w = weights.get("goal", 1.2)
                gfx, gfy = self._compute_goal_force(agent, goal_w)
                fx += gfx
                fy += gfy

                # Leader following for non-leader agents in formation groups.
                if group and group.leader_id and not agent.is_leader:
                    if agent.group_id == group.group_id:
                        leader = self._agents.get(group.leader_id)
                        lfx, lfy = self._compute_leader_follow(agent, leader)
                        fx += lfx * 0.5
                        fy += lfy * 0.5

                # Queue behavior slows agents near their target.
                if agent.state == CrowdAgentState.QUEUING.value:
                    fx *= self.QUEUE_SLOW_FACTOR
                    fy *= self.QUEUE_SLOW_FACTOR

                # Density-zone flow control: if the agent is inside a zone
                # that is over capacity, reduce forward speed.
                for zone in self._density_zones.values():
                    if not zone.is_active:
                        continue
                    d = _dist3d(agent.position_x, agent.position_y,
                                agent.position_z,
                                zone.center_x, zone.center_y, zone.center_z)
                    if d <= zone.radius and zone.current_count > zone.max_density:
                        fx *= 0.5
                        fy *= 0.5
                        break

                # Clamp total steering force.
                mag = math.sqrt(fx * fx + fy * fy)
                if mag > self.MAX_STEERING_FORCE:
                    fx = fx / mag * self.MAX_STEERING_FORCE
                    fy = fy / mag * self.MAX_STEERING_FORCE

                # Integrate velocity (Euler) on the XY plane.
                agent.velocity_x += fx * dt
                agent.velocity_y += fy * dt

                # Clamp to max speed.
                speed = math.sqrt(agent.velocity_x * agent.velocity_x
                                  + agent.velocity_y * agent.velocity_y)
                if speed > agent.max_speed:
                    scale = agent.max_speed / speed
                    agent.velocity_x *= scale
                    agent.velocity_y *= scale
                    speed = agent.max_speed
                agent.speed = speed

                # Integrate position.
                agent.position_x += agent.velocity_x * dt
                agent.position_y += agent.velocity_y * dt

                if speed > 1e-6:
                    moved_agents += 1

                # Check target reach.
                dist_to_target = agent.distance_to_target
                if dist_to_target < threshold:
                    agent.velocity_x = 0.0
                    agent.velocity_y = 0.0
                    agent.velocity_z = 0.0
                    agent.speed = 0.0
                    if agent.state in (CrowdAgentState.WALKING.value,
                                       CrowdAgentState.RUNNING.value,
                                       CrowdAgentState.FLEEING.value):
                        agent.state = CrowdAgentState.IDLE.value
                        state_transitions += 1
                    reached_targets += 1

            # Refresh group panic levels based on average fear.
            for group in self._groups.values():
                fears = []
                for aid in group.agent_ids:
                    a = self._agents.get(aid)
                    if a and a.is_active:
                        fears.append(a.fear_level)
                if fears:
                    avg = sum(fears) / len(fears)
                    group.panic_level = self._panic_level_from_intensity(avg)
                    if group.panic_level == PanicLevel.NONE.value \
                            and group.flocking_mode == FlockingMode.PANIC.value:
                        group.flocking_mode = FlockingMode.NORMAL.value
                        group.behavior_weights = _resolve_flocking_weights(
                            FlockingMode.NORMAL.value)

            self._refresh_density_counts()
            self._stats.tick_count = self._tick_count

            if self._tick_count % 30 == 0:
                self._log_event(CrowdEventKind.TICK.value,
                                {"tick": self._tick_count, "dt": dt,
                                 "moved": moved_agents,
                                 "reached": reached_targets})
            self._update_stats()
            return {
                "tick_count": self._tick_count,
                "moved_agents": moved_agents,
                "reached_targets": reached_targets,
                "state_transitions": state_transitions,
                "total_agents": self._stats.total_agents,
                "active_panics": self._stats.active_panics,
            }

    # ------------------------------------------------------------------
    # Config / Events / Status
    # ------------------------------------------------------------------

    def set_config(self, updates: Dict[str, Any]) -> Tuple[bool, str, CrowdConfig]:
        with _LOCK:
            changed = []
            for k, v in updates.items():
                if hasattr(self._config, k):
                    old_val = getattr(self._config, k)
                    setattr(self._config, k, v)
                    changed.append(f"{k}: {old_val}->{v}")
            if changed:
                self._log_event(CrowdEventKind.CONFIG_UPDATED.value,
                                {"changes": changed})
            return True, "updated", self._config

    def get_config(self) -> CrowdConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 100,
                    event_type: str = "") -> List[CrowdEvent]:
        with _LOCK:
            results = list(self._events)
            if event_type:
                results = [e for e in results if e.event_type == event_type]
            if limit > 0:
                results = results[-limit:]
            return results

    def get_stats(self) -> CrowdStats:
        with _LOCK:
            self._update_stats()
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            self._update_stats()
            state_dist: Dict[str, int] = {}
            for agent in self._agents.values():
                if agent.is_active:
                    state_dist[agent.state] = state_dist.get(agent.state, 0) + 1
            type_dist: Dict[str, int] = {}
            for group in self._groups.values():
                type_dist[group.group_type] = type_dist.get(group.group_type, 0) + 1
            return {
                "initialized": self._initialized,
                "total_agents": len(self._agents),
                "active_agents": self._stats.total_agents,
                "total_groups": len(self._groups),
                "total_density_zones": len(self._density_zones),
                "total_grids": len(self._grids),
                "active_panics": self._stats.active_panics,
                "total_events": len(self._events),
                "agents_spawned": self._stats.agents_spawned,
                "agents_despawned": self._stats.agents_despawned,
                "panic_events": self._stats.panic_events,
                "tick_count": self._tick_count,
                "state_distribution": state_dist,
                "group_type_distribution": type_dist,
            }

    def get_snapshot(self) -> CrowdSnapshot:
        with _LOCK:
            self._update_stats()
            return CrowdSnapshot(
                timestamp=_now(),
                config=self._config.to_dict(),
                stats=self._stats.to_dict(),
                groups=[g.to_dict() for g in list(self._groups.values())],
                agents=[a.to_dict() for a in list(self._agents.values())],
                density_zones=[z.to_dict() for z in list(self._density_zones.values())],
            )

    def reset(self) -> Tuple[bool, str]:
        with _LOCK:
            self._agents.clear()
            self._groups.clear()
            self._density_zones.clear()
            self._grids.clear()
            self._events.clear()
            self._stats = CrowdStats()
            self._config = CrowdConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
            self._log_event(CrowdEventKind.RESET.value, {})
            return True, "reset"


def get_crowd_simulation_system() -> CrowdSimulationSystem:
    """Factory that returns the singleton CrowdSimulationSystem instance."""
    return CrowdSimulationSystem.get_instance()
