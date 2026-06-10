"""
SparkLabs Engine - Crowd Dynamics Simulation System

A comprehensive crowd simulation engine for large-scale NPC behavior
management. Provides flow field generation, density management, group
dynamics, and multi-agent steering behaviors for realistic crowd
movement in the AI-native game engine.

Architecture:
  EngineCrowdDynamics (Singleton)
    |-- CrowdAgent        — individual NPC with position, velocity, goals
    |-- CrowdGroup        — formation-based group of agents
    |-- FlowField         — grid-based velocity vector field for crowd routing
    |-- CrowdDensityRegion — high-density zone detection and tracking
    |-- CrowdEvent        — perturbation events affecting crowd behavior
    |-- SimulationFrame   — snapshot of the simulation state at a tick

Steering Behaviors:
  - Reynolds Flocking (cohesion, alignment, separation)
  - Velocity Obstacle collision avoidance (RVO / ORCA-lite)
  - Eikonal-based flow field generation via fast marching
  - Gaussian kernel density estimation for heat maps
  - Formation marching for coordinated group movement
  - Event-driven crowd perturbation (panic, attraction, repulsion)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CrowdBehavior(Enum):
    """Steering behavior mode for a crowd agent."""
    FLOCKING = "flocking"
    FLOW_FIELD = "flow_field"
    GOAL_SEEKING = "goal_seeking"
    IDLE = "idle"
    FLEEING = "fleeing"
    QUEUING = "queuing"
    FORMATION = "formation"


class CrowdDensityLevel(Enum):
    """Density classification for a spatial region."""
    SPARSE = "sparse"
    MODERATE = "moderate"
    DENSE = "dense"
    VERY_DENSE = "very_dense"
    CRITICAL = "critical"


class FormationType(Enum):
    """Formation shape for coordinated group movement."""
    LINE = "line"
    COLUMN = "column"
    WEDGE = "wedge"
    CIRCLE = "circle"
    SQUARE = "square"
    CUSTOM = "custom"


class AvoidanceStrategy(Enum):
    """Collision avoidance algorithm selection."""
    NONE = "none"
    STEER = "steer"
    PREDICTIVE = "predictive"
    RECIPROCAL_VELOCITY_OBSTACLE = "reciprocal_velocity_obstacle"
    OPTIMAL_RECIPROCAL_COLLISION = "optimal_reciprocal_collision"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CrowdAgent:
    """An individual agent in the crowd simulation.

    Represents a single NPC with position, velocity, steering parameters,
    and behavioral state. Used as both input and output of the simulation
    update step.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    position: Tuple[float, float] = (0.0, 0.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    radius: float = 0.5
    max_speed: float = 1.4
    preferred_speed: float = 1.0
    goal_position: Tuple[float, float] = (0.0, 0.0)
    current_behavior: CrowdBehavior = CrowdBehavior.GOAL_SEEKING
    group_id: str = ""
    avoidance_priority: float = 0.5
    density_weight: float = 1.0
    accumulated_force: Tuple[float, float] = (0.0, 0.0)
    neighbor_count: int = 0
    time_to_goal: float = 0.0
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "radius": self.radius,
            "max_speed": self.max_speed,
            "preferred_speed": self.preferred_speed,
            "goal_position": list(self.goal_position),
            "current_behavior": self.current_behavior.value if hasattr(self.current_behavior, 'value') else self.current_behavior,
            "group_id": self.group_id,
            "avoidance_priority": self.avoidance_priority,
            "density_weight": self.density_weight,
            "accumulated_force": list(self.accumulated_force),
            "neighbor_count": self.neighbor_count,
            "time_to_goal": self.time_to_goal,
            "active": self.active,
            "metadata": dict(self.metadata),
        }

    @property
    def speed(self) -> float:
        """Current scalar speed of the agent."""
        vx, vy = self.velocity
        return math.sqrt(vx * vx + vy * vy)

    @property
    def direction(self) -> Tuple[float, float]:
        """Normalized direction vector of the agent's velocity."""
        vx, vy = self.velocity
        mag = self.speed
        if mag < 1e-8:
            return (0.0, 0.0)
        return (vx / mag, vy / mag)

    @property
    def distance_to_goal(self) -> float:
        """Euclidean distance from the agent to its goal position."""
        px, py = self.position
        gx, gy = self.goal_position
        dx = gx - px
        dy = gy - py
        return math.sqrt(dx * dx + dy * dy)


@dataclass
class CrowdGroup:
    """A coordinated group of agents moving in formation.

    Manages formation type, inter-agent spacing, and steering weights
    that balance group cohesion against individual goal seeking.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    group_name: str = "CrowdGroup"
    members: List[str] = field(default_factory=list)
    formation_type: FormationType = FormationType.LINE
    formation_spacing: float = 1.5
    cohesion_weight: float = 0.6
    alignment_weight: float = 0.4
    separation_weight: float = 0.8
    leader_id: str = ""
    target_center: Tuple[float, float] = (0.0, 0.0)
    target_direction: Tuple[float, float] = (1.0, 0.0)
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "group_name": self.group_name,
            "members": list(self.members),
            "formation_type": self.formation_type.value if hasattr(self.formation_type, 'value') else self.formation_type,
            "formation_spacing": self.formation_spacing,
            "cohesion_weight": self.cohesion_weight,
            "alignment_weight": self.alignment_weight,
            "separation_weight": self.separation_weight,
            "leader_id": self.leader_id,
            "target_center": list(self.target_center),
            "target_direction": list(self.target_direction),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class FlowField:
    """A grid-based flow field for crowd navigation.

    Each cell contains a preferred velocity vector and density / cost
    scalar. Agents sample the flow field at their position to obtain
    steering guidance without per-agent pathfinding.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    grid_width: int = 64
    grid_height: int = 64
    cell_size: float = 1.0
    origin: Tuple[float, float] = (0.0, 0.0)
    velocity_vectors: List[List[Tuple[float, float]]] = field(default_factory=list)
    density_map: List[List[float]] = field(default_factory=list)
    cost_map: List[List[float]] = field(default_factory=list)
    max_speed: float = 1.4
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "grid_width": self.grid_width,
            "grid_height": self.grid_height,
            "cell_size": self.cell_size,
            "origin": list(self.origin),
            "velocity_vectors": [
                [list(v) for v in row] for row in self.velocity_vectors
            ],
            "density_map": [list(row) for row in self.density_map],
            "cost_map": [list(row) for row in self.cost_map],
            "max_speed": self.max_speed,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    def sample_velocity(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """Sample the flow field velocity at a world-space position.

        Returns bilinearly interpolated velocity vector, or (0,0) if
        outside the grid bounds.
        """
        ox, oy = self.origin
        gx = (world_x - ox) / self.cell_size
        gy = (world_y - oy) / self.cell_size
        ix = int(gx)
        iy = int(gy)
        if ix < 0 or ix + 1 >= self.grid_width or iy < 0 or iy + 1 >= self.grid_height:
            return (0.0, 0.0)
        if not self.velocity_vectors or len(self.velocity_vectors) != self.grid_height:
            return (0.0, 0.0)
        fx = gx - ix
        fy = gy - iy
        v00 = self.velocity_vectors[iy][ix]
        v10 = self.velocity_vectors[iy][ix + 1]
        v01 = self.velocity_vectors[iy + 1][ix]
        v11 = self.velocity_vectors[iy + 1][ix + 1]
        vx = (v00[0] * (1.0 - fx) * (1.0 - fy) +
              v10[0] * fx * (1.0 - fy) +
              v01[0] * (1.0 - fx) * fy +
              v11[0] * fx * fy)
        vy = (v00[1] * (1.0 - fx) * (1.0 - fy) +
              v10[1] * fx * (1.0 - fy) +
              v01[1] * (1.0 - fx) * fy +
              v11[1] * fx * fy)
        return (vx, vy)

    def sample_density(self, world_x: float, world_y: float) -> float:
        """Sample the density map at a world-space position."""
        ox, oy = self.origin
        gx = (world_x - ox) / self.cell_size
        gy = (world_y - oy) / self.cell_size
        ix = int(gx)
        iy = int(gy)
        if (ix < 0 or ix >= self.grid_width or iy < 0 or iy >= self.grid_height):
            return 0.0
        if not self.density_map or len(self.density_map) != self.grid_height:
            return 0.0
        return self.density_map[iy][ix]


@dataclass
class CrowdDensityRegion:
    """A cluster of high-density cells detected in the density map.

    Used to identify congestion zones, trigger flow control, or
    adjust agent routing to avoid bottlenecks.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    bounds: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    density: float = 0.0
    level: CrowdDensityLevel = CrowdDensityLevel.SPARSE
    agent_count: int = 0
    capacity: float = 100.0
    flow_rate: float = 0.0
    centroid: Tuple[float, float] = (0.0, 0.0)
    detected_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "bounds": list(self.bounds),
            "density": self.density,
            "level": self.level.value if hasattr(self.level, 'value') else self.level,
            "agent_count": self.agent_count,
            "capacity": self.capacity,
            "flow_rate": self.flow_rate,
            "centroid": list(self.centroid),
            "detected_at": self.detected_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class CrowdEvent:
    """A dynamic event that perturbs the crowd (panic, attraction, etc.).

    Events propagate outward from a position with configurable radius,
    intensity, and duration. Agents within the event radius have their
    behavior temporarily overridden.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = "panic"
    position: Tuple[float, float] = (0.0, 0.0)
    radius: float = 10.0
    intensity: float = 1.0
    duration: float = 5.0
    start_time: float = field(default_factory=_time_module.time)
    propagation_speed: float = 3.0
    affected_agent_count: int = 0
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed(self) -> float:
        """Time in seconds since the event started."""
        return _time_module.time() - self.start_time

    @property
    def remaining(self) -> float:
        """Remaining duration in seconds."""
        return max(0.0, self.duration - self.elapsed)

    @property
    def current_radius(self) -> float:
        """Current propagation radius based on elapsed time and speed."""
        propagated = self.elapsed * self.propagation_speed
        return min(self.radius, propagated)

    @property
    def is_expired(self) -> bool:
        """Whether the event has completed its full duration."""
        return self.elapsed >= self.duration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "position": list(self.position),
            "radius": self.radius,
            "intensity": self.intensity,
            "duration": self.duration,
            "start_time": self.start_time,
            "propagation_speed": self.propagation_speed,
            "affected_agent_count": self.affected_agent_count,
            "active": self.active,
            "elapsed": self.elapsed,
            "remaining": self.remaining,
            "current_radius": self.current_radius,
            "metadata": dict(self.metadata),
        }


@dataclass
class SimulationFrame:
    """A snapshot of the simulation state at a single timestep.

    Captures agent states, density map, and performance metrics
    for debugging, replay, or data export.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    delta_time: float = 0.016
    agent_states: Dict[str, Tuple[float, float, float, float]] = field(default_factory=dict)
    density_map: List[List[float]] = field(default_factory=list)
    total_agents: int = 0
    computational_cost_ms: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "delta_time": self.delta_time,
            "agent_states": {
                aid: list(state) for aid, state in self.agent_states.items()
            },
            "density_map": [list(row) for row in self.density_map],
            "total_agents": self.total_agents,
            "computational_cost_ms": self.computational_cost_ms,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Density Level Thresholds
# ---------------------------------------------------------------------------

_DENSITY_LEVEL_THRESHOLDS: List[Tuple[float, CrowdDensityLevel]] = [
    (0.0, CrowdDensityLevel.SPARSE),
    (0.3, CrowdDensityLevel.MODERATE),
    (0.6, CrowdDensityLevel.DENSE),
    (0.8, CrowdDensityLevel.VERY_DENSE),
    (0.95, CrowdDensityLevel.CRITICAL),
]


def _density_to_level(density: float) -> CrowdDensityLevel:
    """Map a normalized density value (0.0-1.0) to a density level enum."""
    density = max(0.0, min(1.0, density))
    result = CrowdDensityLevel.SPARSE
    for threshold, level in _DENSITY_LEVEL_THRESHOLDS:
        if density >= threshold:
            result = level
    return result


# ---------------------------------------------------------------------------
# Formation Offsets
# ---------------------------------------------------------------------------

def _compute_formation_offsets(
    count: int,
    formation_type: FormationType,
    spacing: float,
    direction: Tuple[float, float],
) -> List[Tuple[float, float]]:
    """Generate relative offset positions for agents in a formation.

    Args:
        count: Number of agents in the formation.
        formation_type: The formation shape.
        spacing: Distance between adjacent agents.
        direction: Forward-facing direction vector of the formation.

    Returns:
        List of (dx, dy) offsets relative to the formation center.
    """
    dx, dy = direction
    mag = math.sqrt(dx * dx + dy * dy)
    if mag < 1e-8:
        dx, dy = (1.0, 0.0)
    else:
        dx, dy = dx / mag, dy / mag
    perp_x, perp_y = -dy, dx

    offsets: List[Tuple[float, float]] = []

    if formation_type == FormationType.LINE:
        for i in range(count):
            offset = (i - (count - 1) / 2.0) * spacing
            offsets.append((perp_x * offset, perp_y * offset))

    elif formation_type == FormationType.COLUMN:
        for i in range(count):
            offset = (i - (count - 1) / 2.0) * spacing
            offsets.append((dx * offset, dy * offset))

    elif formation_type == FormationType.WEDGE:
        for i in range(count):
            row = int(math.sqrt(i))
            col = i - row * row
            offsets.append((
                dx * (-row * spacing) + perp_x * ((col - row / 2.0) * spacing),
                dy * (-row * spacing) + perp_y * ((col - row / 2.0) * spacing),
            ))

    elif formation_type == FormationType.CIRCLE:
        for i in range(count):
            angle = 2.0 * math.pi * i / count
            offsets.append((
                (dx * math.cos(angle) + perp_x * math.sin(angle)) * spacing * 0.8,
                (dy * math.cos(angle) + perp_y * math.sin(angle)) * spacing * 0.8,
            ))

    elif formation_type == FormationType.SQUARE:
        side = max(2, int(math.ceil(math.sqrt(count))))
        for i in range(count):
            row = i // side
            col = i % side
            offsets.append((
                perp_x * ((col - (side - 1) / 2.0) * spacing),
                dy * (-(row - (side - 1) / 2.0) * spacing) + perp_y * 0,
            ))
            # Actually use direction-aware offsets
            offsets[-1] = (
                perp_x * ((col - (side - 1) / 2.0) * spacing) + dx * (-(row - (side - 1) / 2.0) * spacing),
                perp_y * ((col - (side - 1) / 2.0) * spacing) + dy * (-(row - (side - 1) / 2.0) * spacing),
            )

    else:
        # CUSTOM / default: line
        for i in range(count):
            offset = (i - (count - 1) / 2.0) * spacing
            offsets.append((perp_x * offset, perp_y * offset))

    return offsets


# ---------------------------------------------------------------------------
# Main Singleton Class
# ---------------------------------------------------------------------------

class EngineCrowdDynamics:
    """Crowd simulation engine for large-scale NPC behavior management.

    Provides flow field generation, density management, group dynamics,
    and multi-agent steering behaviors including Reynolds flocking,
    velocity-obstacle collision avoidance, and Eikonal-based flow field
    computation.

    Usage:
        cd = EngineCrowdDynamics()
        agent = cd.spawn_agent((10.0, 5.0), (50.0, 30.0))
        flow_field = cd.compute_flow_field((0, 0), (64, 64), [], [(50, 30)])
        updated = cd.update([agent], [], 0.016)
    """

    _instance: Optional["EngineCrowdDynamics"] = None
    _lock = threading.RLock()

    # Physics constants
    MAX_AGENT_RADIUS: float = 2.0
    MIN_SEPARATION_DISTANCE: float = 0.1
    NEIGHBOR_RADIUS_MULTIPLIER: float = 3.0
    MAX_STEERING_FORCE: float = 5.0
    FLOW_FIELD_WEIGHT: float = 0.7
    GOAL_SEEKING_WEIGHT: float = 1.0

    def __new__(cls) -> "EngineCrowdDynamics":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineCrowdDynamics":
        """Return the singleton EngineCrowdDynamics instance."""
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._agents: Dict[str, CrowdAgent] = {}
        self._groups: Dict[str, CrowdGroup] = {}
        self._flow_fields: Dict[str, FlowField] = {}
        self._density_regions: Dict[str, CrowdDensityRegion] = {}
        self._active_events: Dict[str, CrowdEvent] = {}
        self._simulation_frames: List[SimulationFrame] = []
        self._neighbor_cache: Dict[str, List[str]] = {}
        self._obstacles: List[Tuple[float, float, float, float]] = []

        self._total_agents_spawned: int = 0
        self._total_groups_created: int = 0
        self._total_flow_fields_computed: int = 0
        self._total_events_triggered: int = 0
        self._total_frames_simulated: int = 0
        self._tick_count: int = 0
        self._simulation_time: float = 0.0
        self._frame_number: int = 0

    # ------------------------------------------------------------------
    # Agent Management
    # ------------------------------------------------------------------

    def spawn_agent(
        self,
        position: Tuple[float, float],
        goal: Tuple[float, float],
        radius: float = 0.5,
        max_speed: float = 1.4,
        group_id: str = "",
    ) -> CrowdAgent:
        """Create and register a new crowd agent.

        Args:
            position: World-space (x, y) starting position.
            goal: World-space (x, y) target position the agent moves toward.
            radius: Collision radius of the agent.
            max_speed: Maximum movement speed in units per second.
            group_id: Optional group identifier for coordinated movement.

        Returns:
            The newly created CrowdAgent instance.
        """
        with self._lock:
            agent = CrowdAgent(
                position=position,
                goal_position=goal,
                radius=max(0.1, min(self.MAX_AGENT_RADIUS, radius)),
                max_speed=max(0.1, max_speed),
                preferred_speed=max(0.1, max_speed * 0.7),
                group_id=group_id,
            )
            self._agents[agent.id] = agent
            self._total_agents_spawned += 1
            return agent

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the simulation.

        Args:
            agent_id: The ID of the agent to remove.

        Returns:
            True if the agent was found and removed, False otherwise.
        """
        with self._lock:
            if agent_id not in self._agents:
                return False
            agent = self._agents.pop(agent_id)
            # Remove from group membership
            if agent.group_id:
                group = self._groups.get(agent.group_id)
                if group and agent_id in group.members:
                    group.members.remove(agent_id)
            self._neighbor_cache.pop(agent_id, None)
            return True

    def get_agent(self, agent_id: str) -> Optional[CrowdAgent]:
        """Retrieve an agent by ID."""
        return self._agents.get(agent_id)

    def set_agent_goal(self, agent_id: str, goal: Tuple[float, float]) -> bool:
        """Update the target goal position for an agent.

        Args:
            agent_id: The agent ID.
            goal: New world-space target position.

        Returns:
            True if the agent was found and updated.
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        agent.goal_position = goal
        return True

    def set_agent_behavior(self, agent_id: str, behavior: CrowdBehavior) -> bool:
        """Change the steering behavior mode for an agent."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        agent.current_behavior = behavior
        return True

    # ------------------------------------------------------------------
    # Group Management
    # ------------------------------------------------------------------

    def spawn_group(
        self,
        group_name: str,
        positions: List[Tuple[float, float]],
        goals: List[Tuple[float, float]],
        formation: FormationType = FormationType.LINE,
    ) -> CrowdGroup:
        """Create a group of agents moving together in formation.

        Spawns one agent per position-goal pair and assigns them
        all to the same group with the specified formation type.

        Args:
            group_name: Display name for the group.
            positions: List of starting positions, one per agent.
            goals: List of goal positions, one per agent.
            formation: The formation shape for coordinated movement.

        Returns:
            The newly created CrowdGroup instance.
        """
        with self._lock:
            group = CrowdGroup(
                group_name=group_name,
                formation_type=formation,
            )
            self._groups[group.id] = group
            self._total_groups_created += 1

            count = min(len(positions), len(goals))
            for i in range(count):
                agent = CrowdAgent(
                    position=positions[i],
                    goal_position=goals[i],
                    group_id=group.id,
                    current_behavior=CrowdBehavior.FORMATION,
                )
                self._agents[agent.id] = agent
                self._total_agents_spawned += 1
                group.members.append(agent.id)

            if group.members:
                group.leader_id = group.members[0]

            return group

    def set_group_formation(self, group_id: str, formation: FormationType) -> bool:
        """Change the formation type for a group."""
        group = self._groups.get(group_id)
        if group is None:
            return False
        group.formation_type = formation
        return True

    def set_group_target(self, group_id: str, target_center: Tuple[float, float],
                         target_direction: Tuple[float, float] = (1.0, 0.0)) -> bool:
        """Set the movement target and direction for a group."""
        group = self._groups.get(group_id)
        if group is None:
            return False
        group.target_center = target_center
        group.target_direction = target_direction
        return True

    # ------------------------------------------------------------------
    # Flow Field Computation
    # ------------------------------------------------------------------

    def compute_flow_field(
        self,
        origin: Tuple[float, float],
        dimensions: Tuple[int, int],
        obstacles: List[Tuple[float, float, float]],
        goals: List[Tuple[float, float]],
    ) -> FlowField:
        """Generate a flow field using Eikonal-based fast marching.

        Constructs a grid of preferred velocity vectors that guide agents
        toward the nearest goal while avoiding obstacle cells. Uses a
        simplified fast-marching method to propagate distance/direction
        from goals outward through the grid.

        Args:
            origin: World-space (x, y) of the bottom-left grid corner.
            dimensions: (grid_width, grid_height) in cells.
            obstacles: List of (x, y, radius) obstacle positions.
            goals: List of (x, y) goal positions that attract the flow.

        Returns:
            A FlowField with populated velocity_vectors, density_map,
            and cost_map.
        """
        grid_w, grid_h = dimensions
        cell_size = 1.0

        with self._lock:
            flow_field = FlowField(
                grid_width=grid_w,
                grid_height=grid_h,
                cell_size=cell_size,
                origin=origin,
            )
            self._total_flow_fields_computed += 1

            # Initialize cost map: 0 = free, INF = blocked
            INF_COST = 1e9
            cost_map: List[List[float]] = [
                [0.0 for _ in range(grid_w)] for _ in range(grid_h)
            ]

            for ox, oy, orad in obstacles:
                min_cx = max(0, int((ox - orad - origin[0]) / cell_size))
                max_cx = min(grid_w - 1, int((ox + orad - origin[0]) / cell_size))
                min_cy = max(0, int((oy - orad - origin[1]) / cell_size))
                max_cy = min(grid_h - 1, int((oy + orad - origin[1]) / cell_size))
                for cy in range(min_cy, max_cy + 1):
                    for cx in range(min_cx, max_cx + 1):
                        wx = origin[0] + (cx + 0.5) * cell_size
                        wy = origin[1] + (cy + 0.5) * cell_size
                        if (wx - ox) ** 2 + (wy - oy) ** 2 <= orad ** 2:
                            cost_map[cy][cx] = INF_COST

            # Distance field from goals (fast marching)
            dist_field: List[List[float]] = [
                [INF_COST for _ in range(grid_w)] for _ in range(grid_h)
            ]
            dir_x: List[List[float]] = [
                [0.0 for _ in range(grid_w)] for _ in range(grid_h)
            ]
            dir_y: List[List[float]] = [
                [0.0 for _ in range(grid_w)] for _ in range(grid_h)
            ]

            # Initialize goal cells
            frontier: List[Tuple[int, int, float]] = []
            for gx_world, gy_world in goals:
                gx = int((gx_world - origin[0]) / cell_size)
                gy = int((gy_world - origin[1]) / cell_size)
                if 0 <= gx < grid_w and 0 <= gy < grid_h:
                    if cost_map[gy][gx] < INF_COST:
                        dist_field[gy][gx] = 0.0
                        dir_x[gy][gx] = 0.0
                        dir_y[gy][gx] = 0.0
                        frontier.append((gx, gy, 0.0))

            # Sort frontier by distance
            frontier.sort(key=lambda x: x[2])

            # Fast marching propagation
            visited: Set[Tuple[int, int]] = set()
            neighbor_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]

            while frontier:
                frontier.sort(key=lambda x: x[2])
                cx, cy, cd = frontier.pop(0)
                if (cx, cy) in visited:
                    continue
                visited.add((cx, cy))

                for nox, noy in neighbor_offsets:
                    nx, ny = cx + nox, cy + noy
                    if nx < 0 or nx >= grid_w or ny < 0 or ny >= grid_h:
                        continue
                    if (nx, ny) in visited:
                        continue
                    if cost_map[ny][nx] >= INF_COST:
                        continue

                    new_dist = cd + cell_size
                    if new_dist < dist_field[ny][nx]:
                        dist_field[ny][nx] = new_dist
                        dir_x[ny][nx] = float(cx - nx)
                        dir_y[ny][nx] = float(cy - ny)
                        frontier.append((nx, ny, new_dist))

            # Build velocity vectors from the gradient of the distance field
            velocity_vectors: List[List[Tuple[float, float]]] = []
            for cy in range(grid_h):
                row: List[Tuple[float, float]] = []
                for cx in range(grid_w):
                    if cost_map[cy][cx] >= INF_COST:
                        row.append((0.0, 0.0))
                    else:
                        d = dist_field[cy][cx]
                        if d >= INF_COST * 0.5:
                            row.append((0.0, 0.0))
                        else:
                            vx = -dir_x[cy][cx]
                            vy = -dir_y[cy][cx]
                            mag = math.sqrt(vx * vx + vy * vy)
                            if mag > 1e-8:
                                vx /= mag
                                vy /= mag
                                vx *= flow_field.max_speed
                                vy *= flow_field.max_speed
                            else:
                                vx, vy = 0.0, 0.0
                            row.append((vx, vy))
                velocity_vectors.append(row)

            flow_field.velocity_vectors = velocity_vectors
            flow_field.cost_map = cost_map

            # Build density map from cost (inverse relationship)
            max_dist = 0.0
            for row in dist_field:
                for v in row:
                    if v < INF_COST * 0.5:
                        max_dist = max(max_dist, v)
            if max_dist < 1e-6:
                max_dist = 1.0

            density_map: List[List[float]] = []
            for cy in range(grid_h):
                drow: List[float] = []
                for cx in range(grid_w):
                    if cost_map[cy][cx] >= INF_COST:
                        drow.append(1.0)
                    else:
                        drow.append(min(1.0, dist_field[cy][cx] / max_dist))
                density_map.append(drow)
            flow_field.density_map = density_map

            self._flow_fields[flow_field.id] = flow_field
            return flow_field

    # ------------------------------------------------------------------
    # Density Map Computation
    # ------------------------------------------------------------------

    def compute_density_map(
        self,
        agents: List[CrowdAgent],
        grid_bounds: Tuple[float, float, float, float],
        cell_size: float = 1.0,
    ) -> List[List[float]]:
        """Compute a density heatmap from agent positions using Gaussian kernels.

        Each agent contributes a Gaussian radial-basis function centered
        at its position. The resulting density map can be used to detect
        congestion zones and adjust agent routing.

        Args:
            agents: List of agents to include in the density estimate.
            grid_bounds: (min_x, min_y, max_x, max_y) world-space extents.
            cell_size: Size of each grid cell in world units.

        Returns:
            2D list of density values normalized to [0.0, 1.0].
        """
        min_x, min_y, max_x, max_y = grid_bounds
        if max_x <= min_x or max_y <= min_y:
            return []

        grid_w = max(1, int((max_x - min_x) / cell_size))
        grid_h = max(1, int((max_y - min_y) / cell_size))

        density: List[List[float]] = [
            [0.0 for _ in range(grid_w)] for _ in range(grid_h)
        ]

        # Gaussian kernel bandwidth proportional to cell size
        sigma = cell_size * 1.5
        sigma_sq_2 = 2.0 * sigma * sigma
        norm_factor = 1.0 / (2.0 * math.pi * sigma * sigma)

        for agent in agents:
            if not agent.active:
                continue
            ax, ay = agent.position
            # Determine bounding box of influence for this agent
            influence = 3.0 * sigma + agent.radius
            min_cx = max(0, int((ax - influence - min_x) / cell_size))
            max_cx = min(grid_w - 1, int((ax + influence - min_x) / cell_size))
            min_cy = max(0, int((ay - influence - min_y) / cell_size))
            max_cy = min(grid_h - 1, int((ay + influence - min_y) / cell_size))

            for cy in range(min_cy, max_cy + 1):
                for cx in range(min_cx, max_cx + 1):
                    cell_wx = min_x + (cx + 0.5) * cell_size
                    cell_wy = min_y + (cy + 0.5) * cell_size
                    dx = cell_wx - ax
                    dy = cell_wy - ay
                    dist_sq = dx * dx + dy * dy
                    gauss_val = norm_factor * math.exp(-dist_sq / sigma_sq_2)
                    density[cy][cx] += gauss_val * agent.density_weight

        # Normalize to [0, 1]
        max_density = 0.0
        for row in density:
            for v in row:
                if v > max_density:
                    max_density = v
        if max_density > 1e-8:
            for cy in range(grid_h):
                for cx in range(grid_w):
                    density[cy][cx] = min(1.0, density[cy][cx] / max_density)

        return density

    # ------------------------------------------------------------------
    # Density Region Detection
    # ------------------------------------------------------------------

    def detect_density_regions(
        self,
        density_map: List[List[float]],
        threshold: float = 0.7,
    ) -> List[CrowdDensityRegion]:
        """Detect contiguous high-density regions in a density map.

        Uses flood-fill clustering to find connected components where
        density exceeds the given threshold. Each region is classified
        by its average density level.

        Args:
            density_map: 2D grid of density values in [0, 1].
            threshold: Minimum density to consider a cell as congested.

        Returns:
            List of CrowdDensityRegion instances describing each cluster.
        """
        if not density_map or not density_map[0]:
            return []

        grid_h = len(density_map)
        grid_w = len(density_map[0])
        visited: List[List[bool]] = [
            [False for _ in range(grid_w)] for _ in range(grid_h)
        ]
        regions: List[CrowdDensityRegion] = []

        for sy in range(grid_h):
            for sx in range(grid_w):
                if visited[sy][sx]:
                    continue
                if density_map[sy][sx] < threshold:
                    visited[sy][sx] = True
                    continue

                # Flood-fill this region
                stack: List[Tuple[int, int]] = [(sx, sy)]
                cells: List[Tuple[int, int]] = []
                min_cx, min_cy = grid_w, grid_h
                max_cx, max_cy = 0, 0
                total_density = 0.0

                while stack:
                    cx, cy = stack.pop()
                    if cx < 0 or cx >= grid_w or cy < 0 or cy >= grid_h:
                        continue
                    if visited[cy][cx]:
                        continue
                    if density_map[cy][cx] < threshold:
                        visited[cy][cx] = True
                        continue
                    visited[cy][cx] = True
                    cells.append((cx, cy))
                    total_density += density_map[cy][cx]
                    min_cx = min(min_cx, cx)
                    max_cx = max(max_cx, cx)
                    min_cy = min(min_cy, cy)
                    max_cy = max(max_cy, cy)
                    for nox, noy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        stack.append((cx + nox, cy + noy))

                if not cells:
                    continue

                avg_density = total_density / len(cells)
                level = _density_to_level(avg_density)
                # Estimate capacity as number of cells
                capacity = float(len(cells))
                # Estimate flow rate inversely proportional to density
                flow_rate = max(0.0, 1.0 - avg_density) * capacity

                region = CrowdDensityRegion(
                    bounds=(float(min_cx), float(min_cy),
                            float(max_cx), float(max_cy)),
                    density=round(avg_density, 4),
                    level=level,
                    agent_count=len(cells),
                    capacity=capacity,
                    flow_rate=round(flow_rate, 4),
                    centroid=(
                        (min_cx + max_cx) / 2.0,
                        (min_cy + max_cy) / 2.0,
                    ),
                )
                self._density_regions[region.id] = region
                regions.append(region)

        return regions

    # ------------------------------------------------------------------
    # Reynolds Flocking
    # ------------------------------------------------------------------

    def apply_flocking(
        self,
        agent: CrowdAgent,
        neighbors: List[CrowdAgent],
    ) -> Tuple[float, float]:
        """Compute Reynolds flocking steering force for an agent.

        Combines three weighted components:
          - Cohesion: steer toward the average position of neighbors
          - Alignment: steer toward the average velocity of neighbors
          - Separation: steer away from neighbors that are too close

        Args:
            agent: The agent to compute steering for.
            neighbors: List of nearby agents within perception range.

        Returns:
            A (fx, fy) steering force vector.
        """
        if not neighbors:
            return (0.0, 0.0)

        ax, ay = agent.position
        avx, avy = agent.velocity

        # --- Cohesion ---
        cohesion_x, cohesion_y = 0.0, 0.0
        for n in neighbors:
            nx, ny = n.position
            cohesion_x += nx
            cohesion_y += ny
        cohesion_x /= len(neighbors)
        cohesion_y /= len(neighbors)
        cohesion_x -= ax
        cohesion_y -= ay
        # Normalize and scale to max speed
        cmag = math.sqrt(cohesion_x * cohesion_x + cohesion_y * cohesion_y)
        if cmag > 1e-8:
            cohesion_x = (cohesion_x / cmag) * agent.max_speed - avx
            cohesion_y = (cohesion_y / cmag) * agent.max_speed - avy

        # --- Alignment ---
        align_x, align_y = 0.0, 0.0
        for n in neighbors:
            nvx, nvy = n.velocity
            align_x += nvx
            align_y += nvy
        align_x /= len(neighbors)
        align_y /= len(neighbors)
        amag = math.sqrt(align_x * align_x + align_y * align_y)
        if amag > 1e-8:
            align_x = (align_x / amag) * agent.max_speed - avx
            align_y = (align_y / amag) * agent.max_speed - avy

        # --- Separation ---
        sep_x, sep_y = 0.0, 0.0
        sep_count = 0
        min_dist = agent.radius * 2.0
        for n in neighbors:
            nx, ny = n.position
            dx = ax - nx
            dy = ay - ny
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < min_dist and dist > 1e-8:
                weight = (min_dist - dist) / min_dist
                sep_x += (dx / dist) * weight
                sep_y += (dy / dist) * weight
                sep_count += 1
        if sep_count > 0:
            sep_x /= sep_count
            sep_y /= sep_count
            smag = math.sqrt(sep_x * sep_x + sep_y * sep_y)
            if smag > 1e-8:
                sep_x = (sep_x / smag) * agent.max_speed - avx
                sep_y = (sep_y / smag) * agent.max_speed - avy

        # Weighted combination
        group = self._groups.get(agent.group_id) if agent.group_id else None
        cw = group.cohesion_weight if group else 0.6
        aw = group.alignment_weight if group else 0.4
        sw = group.separation_weight if group else 0.8

        fx = cw * cohesion_x + aw * align_x + sw * sep_x
        fy = cw * cohesion_y + aw * align_y + sw * sep_y

        # Clamp to max steering force
        fmag = math.sqrt(fx * fx + fy * fy)
        if fmag > self.MAX_STEERING_FORCE:
            fx = fx / fmag * self.MAX_STEERING_FORCE
            fy = fy / fmag * self.MAX_STEERING_FORCE

        return (fx, fy)

    # ------------------------------------------------------------------
    # Collision Avoidance
    # ------------------------------------------------------------------

    def compute_collision_avoidance(
        self,
        agent: CrowdAgent,
        neighbors: List[CrowdAgent],
        obstacles: List[Tuple[float, float, float]],
    ) -> Tuple[float, float]:
        """Compute collision avoidance steering force.

        Uses a reciprocal velocity obstacle (RVO-lite) approach:
          - For each neighbor, compute the velocity obstacle cone
          - Select a velocity outside all obstacle cones closest to the
            agent's preferred velocity
          - Return the steering delta from current velocity

        Args:
            agent: The agent computing avoidance.
            neighbors: Nearby agents to avoid.
            obstacles: Static obstacle positions as (x, y, radius).

        Returns:
            A (fx, fy) steering force vector.
        """
        avoid_x, avoid_y = 0.0, 0.0
        active_avoid = 0

        ax, ay = agent.position
        avx, avy = agent.velocity
        ar = agent.radius
        time_horizon = 2.0

        # Agent-agent avoidance (RVO-lite)
        for nb in neighbors:
            nx, ny = nb.position
            nvx, nvy = nb.velocity
            nr = nb.radius
            combined_radius = ar + nr + self.MIN_SEPARATION_DISTANCE

            # Relative position and velocity
            rx = nx - ax
            ry = ny - ay
            rvx = nvx - avx
            rvy = nvy - avy

            dist = math.sqrt(rx * rx + ry * ry)
            if dist < 1e-8:
                dist = 1e-8

            # Time to closest approach
            rv_dot_r = rvx * rx + rvy * ry
            if rv_dot_r >= 0:
                # Neighbors moving away — minimal avoidance
                continue

            # Closest approach distance
            rv_mag_sq = rvx * rvx + rvy * rvy
            if rv_mag_sq < 1e-8:
                # Relative stationary — push apart
                if dist < combined_radius * 1.5:
                    avoid_x += (ax - nx) / dist * 0.5
                    avoid_y += (ay - ny) / dist * 0.5
                    active_avoid += 1
                continue

            t_cpa = -rv_dot_r / rv_mag_sq
            t_cpa = min(t_cpa, time_horizon)

            closest_x = rx + rvx * t_cpa
            closest_y = ry + rvy * t_cpa
            closest_dist_sq = closest_x * closest_x + closest_y * closest_y

            if closest_dist_sq < combined_radius * combined_radius:
                # Collision predicted — compute avoidance
                closest_dist = math.sqrt(closest_dist_sq)
                if closest_dist < 1e-8:
                    closest_dist = 1e-8
                penetration = combined_radius - closest_dist
                weight = penetration / combined_radius
                avoid_x += (rx / dist) * weight * -1.0
                avoid_y += (ry / dist) * weight * -1.0
                active_avoid += 1

        # Obstacle avoidance
        for ox, oy, orad in obstacles:
            dx = ax - ox
            dy = ay - oy
            dist = math.sqrt(dx * dx + dy * dy)
            combined_radius = ar + orad + self.MIN_SEPARATION_DISTANCE
            if dist < combined_radius * 1.5 and dist > 1e-8:
                penetration = combined_radius - dist
                weight = penetration / combined_radius
                avoid_x += (dx / dist) * weight
                avoid_y += (dy / dist) * weight
                active_avoid += 1

        if active_avoid == 0:
            return (0.0, 0.0)

        avoid_x /= active_avoid
        avoid_y /= active_avoid

        # Scale to preferred speed
        amag = math.sqrt(avoid_x * avoid_x + avoid_y * avoid_y)
        if amag > 1e-8:
            target_vx = (avoid_x / amag) * agent.preferred_speed
            target_vy = (avoid_y / amag) * agent.preferred_speed
        else:
            return (0.0, 0.0)

        steering_x = target_vx - avx
        steering_y = target_vy - avy

        # Clamp
        smag = math.sqrt(steering_x * steering_x + steering_y * steering_y)
        if smag > self.MAX_STEERING_FORCE:
            steering_x = steering_x / smag * self.MAX_STEERING_FORCE
            steering_y = steering_y / smag * self.MAX_STEERING_FORCE

        return (steering_x, steering_y)

    # ------------------------------------------------------------------
    # Crowd Events
    # ------------------------------------------------------------------

    def trigger_crowd_event(
        self,
        event: CrowdEvent,
        agents: List[CrowdAgent],
    ) -> Dict[str, Any]:
        """Trigger a crowd event and compute its effects on agents.

        Agents within the event's propagation radius are affected based
        on event type:
          - "panic": Agents flee from the event position, max_speed increased
          - "attraction": Agents are drawn toward the event position
          - "repulsion": Agents are pushed away from the event position
          - "disperse": Agents reverse direction and scatter
          - "halt": Agents stop moving temporarily

        Args:
            event: The CrowdEvent to trigger.
            agents: List of all agents to check for effect.

        Returns:
            Dict with affected_agent_ids, affected_count, and event_type.
        """
        event.active = True
        event.start_time = _time_module.time()
        event.affected_agent_count = 0
        self._active_events[event.id] = event
        self._total_events_triggered += 1

        affected_ids: List[str] = []
        ex, ey = event.position

        for agent in agents:
            if not agent.active:
                continue
            ax, ay = agent.position
            dx = ax - ex
            dy = ay - ey
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= event.current_radius and dist > 1e-8:
                affected_ids.append(agent.id)
                event.affected_agent_count += 1
                weight = 1.0 - (dist / event.current_radius)
                weight *= event.intensity

                if event.event_type == "panic":
                    flee_x = (dx / dist) * agent.max_speed * 2.0
                    flee_y = (dy / dist) * agent.max_speed * 2.0
                    agent.velocity = (flee_x, flee_y)
                    agent.current_behavior = CrowdBehavior.FLEEING
                    agent.max_speed = min(agent.max_speed * 1.5, 5.0)

                elif event.event_type == "attraction":
                    attract_x = -(dx / dist) * agent.max_speed * weight
                    attract_y = -(dy / dist) * agent.max_speed * weight
                    vx, vy = agent.velocity
                    agent.velocity = (
                        vx + attract_x * 0.3,
                        vy + attract_y * 0.3,
                    )

                elif event.event_type == "repulsion":
                    push_x = (dx / dist) * agent.max_speed * weight * 1.5
                    push_y = (dy / dist) * agent.max_speed * weight * 1.5
                    vx, vy = agent.velocity
                    agent.velocity = (
                        vx + push_x * 0.3,
                        vy + push_y * 0.3,
                    )

                elif event.event_type == "disperse":
                    scatter_angle = random.uniform(0, 2.0 * math.pi)
                    scatter_speed = agent.max_speed * (0.5 + weight)
                    agent.velocity = (
                        math.cos(scatter_angle) * scatter_speed,
                        math.sin(scatter_angle) * scatter_speed,
                    )
                    agent.current_behavior = CrowdBehavior.FLEEING

                elif event.event_type == "halt":
                    agent.velocity = (0.0, 0.0)
                    agent.current_behavior = CrowdBehavior.IDLE

        return {
            "event_id": event.id,
            "event_type": event.event_type,
            "affected_agent_ids": affected_ids,
            "affected_count": event.affected_agent_count,
            "total_agents": len(agents),
            "radius": event.current_radius,
            "intensity": event.intensity,
        }

    # ------------------------------------------------------------------
    # Main Update Loop
    # ------------------------------------------------------------------

    def update(
        self,
        agents: List[CrowdAgent],
        obstacles: List[Tuple[float, float, float]],
        delta_time: float,
    ) -> List[CrowdAgent]:
        """Advance the crowd simulation by one timestep.

        For each agent, computes neighbor set, applies the appropriate
        steering behavior (flocking, goal seeking, flow field, fleeing,
        formation), calculates collision avoidance, integrates velocity
        and position, and captures a simulation frame snapshot.

        Args:
            agents: List of CrowdAgent instances to update (mutated in place).
            obstacles: List of (x, y, radius) static obstacle descriptors.
            delta_time: Timestep duration in seconds.

        Returns:
            The list of updated agents (same objects, mutated).
        """
        import time as _perf_time

        t_start = _perf_time.perf_counter()

        with self._lock:
            self._tick_count += 1
            self._simulation_time += delta_time
            self._frame_number += 1

            # Build neighbor cache using spatial hashing
            cell_size = self.NEIGHBOR_RADIUS_MULTIPLIER * self.MAX_AGENT_RADIUS
            spatial_grid: Dict[Tuple[int, int], List[int]] = {}

            for agent in agents:
                if not agent.active:
                    continue
                ax, ay = agent.position
                cx = int(ax / cell_size)
                cy = int(ay / cell_size)
                key = (cx, cy)
                spatial_grid.setdefault(key, []).append(agent.id)

            # Update each agent
            for agent in agents:
                if not agent.active:
                    continue

                # --- Find neighbors ---
                ax, ay = agent.position
                cx = int(ax / cell_size)
                cy = int(ay / cell_size)
                neighbor_ids: Set[str] = set()
                neighbor_radius = agent.radius * self.NEIGHBOR_RADIUS_MULTIPLIER + 2.0

                for dcx in (-1, 0, 1):
                    for dcy in (-1, 0, 1):
                        key = (cx + dcx, cy + dcy)
                        for nid in spatial_grid.get(key, []):
                            if nid != agent.id:
                                neighbor_ids.add(nid)

                neighbors: List[CrowdAgent] = []
                for nid in neighbor_ids:
                    nb = self._agents.get(nid)
                    if nb is None or not nb.active:
                        continue
                    nx, ny = nb.position
                    dx = ax - nx
                    dy = ay - ny
                    if dx * dx + dy * dy <= neighbor_radius * neighbor_radius:
                        neighbors.append(nb)

                agent.neighbor_count = len(neighbors)

                # --- Compute steering force ---
                total_force_x, total_force_y = 0.0, 0.0

                if agent.current_behavior == CrowdBehavior.FLOCKING:
                    fx, fy = self.apply_flocking(agent, neighbors)
                    total_force_x += fx
                    total_force_y += fy

                elif agent.current_behavior == CrowdBehavior.FORMATION:
                    # Formation: steer toward formation goal position
                    group = self._groups.get(agent.group_id) if agent.group_id else None
                    if group:
                        member_index = group.members.index(agent.id) if agent.id in group.members else 0
                        offsets = _compute_formation_offsets(
                            len(group.members), group.formation_type,
                            group.formation_spacing, group.target_direction,
                        )
                        if member_index < len(offsets):
                            off_x, off_y = offsets[member_index]
                            form_goal_x = group.target_center[0] + off_x
                            form_goal_y = group.target_center[1] + off_y
                        else:
                            form_goal_x, form_goal_y = group.target_center
                        # Steer toward formation goal
                        dx = form_goal_x - ax
                        dy = form_goal_y - ay
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist > 1e-8:
                            desired_x = (dx / dist) * agent.max_speed
                            desired_y = (dy / dist) * agent.max_speed
                            total_force_x += desired_x - agent.velocity[0]
                            total_force_y += desired_y - agent.velocity[1]
                        # Also apply flocking within the group
                        fx, fy = self.apply_flocking(agent, neighbors)
                        total_force_x += fx
                        total_force_y += fy
                    else:
                        gx, gy = agent.goal_position
                        dx = gx - ax
                        dy = gy - ay
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist > 1e-8:
                            desired_x = (dx / dist) * agent.max_speed
                            desired_y = (dy / dist) * agent.max_speed
                            total_force_x += desired_x - agent.velocity[0]
                            total_force_y += desired_y - agent.velocity[1]

                elif agent.current_behavior == CrowdBehavior.GOAL_SEEKING:
                    gx, gy = agent.goal_position
                    dx = gx - ax
                    dy = gy - ay
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > 0.1:
                        desired_x = (dx / dist) * agent.max_speed
                        desired_y = (dy / dist) * agent.max_speed
                        total_force_x += (desired_x - agent.velocity[0]) * self.GOAL_SEEKING_WEIGHT
                        total_force_y += (desired_y - agent.velocity[1]) * self.GOAL_SEEKING_WEIGHT

                elif agent.current_behavior == CrowdBehavior.FLEEING:
                    gx, gy = agent.goal_position
                    dx = ax - gx
                    dy = ay - gy
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > 1e-8:
                        desired_x = (dx / dist) * agent.max_speed
                        desired_y = (dy / dist) * agent.max_speed
                        total_force_x += desired_x - agent.velocity[0]
                        total_force_y += desired_y - agent.velocity[1]

                elif agent.current_behavior == CrowdBehavior.QUEUING:
                    # Move slowly toward goal, maintain separation
                    gx, gy = agent.goal_position
                    dx = gx - ax
                    dy = gy - ay
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > 1e-8:
                        reduced_speed = agent.max_speed * 0.3
                        desired_x = (dx / dist) * reduced_speed
                        desired_y = (dy / dist) * reduced_speed
                        total_force_x += desired_x - agent.velocity[0]
                        total_force_y += desired_y - agent.velocity[1]

                # --- Collision avoidance ---
                avoid_x, avoid_y = self.compute_collision_avoidance(
                    agent, neighbors, obstacles,
                )
                total_force_x += avoid_x
                total_force_y += avoid_y

                # --- Clamp total force ---
                fmag = math.sqrt(total_force_x * total_force_x + total_force_y * total_force_y)
                if fmag > self.MAX_STEERING_FORCE:
                    total_force_x = total_force_x / fmag * self.MAX_STEERING_FORCE
                    total_force_y = total_force_y / fmag * self.MAX_STEERING_FORCE

                agent.accumulated_force = (total_force_x, total_force_y)

                # --- Integrate (Euler) ---
                vx, vy = agent.velocity
                vx += total_force_x * delta_time
                vy += total_force_y * delta_time

                # Clamp to max speed
                speed = math.sqrt(vx * vx + vy * vy)
                if speed > agent.max_speed:
                    vx = vx / speed * agent.max_speed
                    vy = vy / speed * agent.max_speed

                # Apply velocity obstacle adjustments for RVO-like behavior
                if speed > 1e-8:
                    for nb in neighbors:
                        nb_vx, nb_vy = nb.velocity
                        nb_speed = math.sqrt(nb_vx * nb_vx + nb_vy * nb_vy)
                        if nb_speed > 1e-8:
                            # Reciprocal velocity adjustment
                            rel_vx = vx - nb_vx
                            rel_vy = vy - nb_vy
                            nx = nb.position[0] - ax
                            ny = nb.position[1] - ay
                            n_dist = math.sqrt(nx * nx + ny * ny) + 1e-8
                            n_hat_x = nx / n_dist
                            n_hat_y = ny / n_dist
                            rel_dot_n = rel_vx * n_hat_x + rel_vy * n_hat_y
                            min_dist = agent.radius + nb.radius + 0.1
                            if rel_dot_n > 0 and n_dist < min_dist * 2.0:
                                correction = rel_dot_n * 0.5
                                vx -= n_hat_x * correction
                                vy -= n_hat_y * correction

                agent.velocity = (vx, vy)

                # Update position
                px, py = agent.position
                agent.position = (
                    px + vx * delta_time,
                    py + vy * delta_time,
                )

                # Compute time to goal
                gx, gy = agent.goal_position
                goal_dx = gx - agent.position[0]
                goal_dy = gy - agent.position[1]
                goal_dist = math.sqrt(goal_dx * goal_dx + goal_dy * goal_dy)
                if speed > 1e-8:
                    agent.time_to_goal = goal_dist / speed
                else:
                    agent.time_to_goal = float("inf")

                # Check if goal reached
                if goal_dist < 0.3:
                    agent.velocity = (0.0, 0.0)
                    agent.position = agent.goal_position
                    agent.current_behavior = CrowdBehavior.IDLE
                    agent.time_to_goal = 0.0

            # --- Update active events ---
            expired_events: List[str] = []
            for eid, evt in self._active_events.items():
                if evt.is_expired:
                    evt.active = False
                    expired_events.append(eid)
                else:
                    evt.affected_agent_count = 0
                    ex, ey = evt.position
                    for agent in agents:
                        if not agent.active:
                            continue
                        ax, ay = agent.position
                        dx = ax - ex
                        dy = ay - ey
                        if dx * dx + dy * dy <= evt.current_radius * evt.current_radius:
                            evt.affected_agent_count += 1
            for eid in expired_events:
                del self._active_events[eid]

            # --- Capture simulation frame ---
            agent_states: Dict[str, Tuple[float, float, float, float]] = {}
            for agent in agents:
                ax, ay = agent.position
                avx, avy = agent.velocity
                agent_states[agent.id] = (ax, ay, avx, avy)

            t_end = _perf_time.perf_counter()
            cost_ms = (t_end - t_start) * 1000.0

            frame = SimulationFrame(
                frame_number=self._frame_number,
                delta_time=delta_time,
                agent_states=agent_states,
                total_agents=sum(1 for a in agents if a.active),
                computational_cost_ms=round(cost_ms, 4),
            )
            self._simulation_frames.append(frame)
            self._total_frames_simulated += 1

        return agents

    # ------------------------------------------------------------------
    # Status and Serialization
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the current simulation status and statistics.

        Returns:
            Dict with agent/group counts, performance metrics, and
            active event summaries.
        """
        with self._lock:
            active_agents = sum(1 for a in self._agents.values() if a.active)
            behavior_dist: Dict[str, int] = {}
            for agent in self._agents.values():
                if agent.active:
                    b = agent.current_behavior.value if hasattr(agent.current_behavior, 'value') else agent.current_behavior
                    behavior_dist[b] = behavior_dist.get(b, 0) + 1

            return {
                "total_agents": len(self._agents),
                "active_agents": active_agents,
                "total_agents_spawned": self._total_agents_spawned,
                "total_groups": len(self._groups),
                "total_groups_created": self._total_groups_created,
                "total_flow_fields": len(self._flow_fields),
                "total_flow_fields_computed": self._total_flow_fields_computed,
                "total_density_regions": len(self._density_regions),
                "active_events": len(self._active_events),
                "total_events_triggered": self._total_events_triggered,
                "total_frames_simulated": self._total_frames_simulated,
                "tick_count": self._tick_count,
                "simulation_time": round(self._simulation_time, 4),
                "frame_number": self._frame_number,
                "behavior_distribution": behavior_dist,
                "neighbor_cache_size": len(self._neighbor_cache),
            }

    def create_agent(
        self,
        name: str = "",
        position: Tuple[float, float] = (0, 0),
        velocity: Tuple[float, float] = (0, 0),
        max_speed: float = 5.0,
        preferred_speed: float = 3.0,
        radius: float = 0.5,
        group_id: str = "",
        behavior: str = "flocking",
    ) -> CrowdAgent:
        """Create a single crowd agent.

        Convenience wrapper around spawn_agent for REST API use.

        Args:
            name: Display name for the agent.
            position: Initial (x, y) position.
            velocity: Initial velocity vector.
            max_speed: Maximum movement speed.
            preferred_speed: Preferred cruising speed.
            radius: Agent collision radius.
            group_id: Optional group identifier.
            behavior: Behavior mode string.

        Returns:
            The created CrowdAgent.
        """
        goal = (
            position[0] + velocity[0] * 10.0,
            position[1] + velocity[1] * 10.0,
        )
        agent = self.spawn_agent(
            position=position,
            goal=goal,
            radius=radius,
            max_speed=max_speed,
            group_id=group_id,
        )
        if hasattr(agent, 'agent_name'):
            agent.agent_name = name
        if behavior:
            try:
                agent.current_behavior = CrowdBehavior(behavior)
            except ValueError:
                agent.current_behavior = CrowdBehavior.FLOCKING
        return agent

    def create_group(
        self,
        name: str = "",
        cohesion_weight: float = 0.3,
        alignment_weight: float = 0.3,
        separation_weight: float = 0.4,
        formation: str = "none",
    ) -> CrowdGroup:
        """Create a crowd group with specified weights and formation.

        Convenience wrapper for REST API use.

        Args:
            name: Group name.
            cohesion_weight: Cohesion steering weight.
            alignment_weight: Alignment steering weight.
            separation_weight: Separation steering weight.
            formation: Formation type string.

        Returns:
            The created CrowdGroup.
        """
        try:
            formation_type = FormationType(formation)
        except ValueError:
            formation_type = FormationType.NONE
        group = self.spawn_group(
            group_name=name,
            positions=[(0.0, 0.0)],
            goals=[(0.0, 0.0)],
            formation=formation_type,
        )
        if group:
            group.cohesion_weight = cohesion_weight
            group.alignment_weight = alignment_weight
            group.separation_weight = separation_weight
        return group

    def add_obstacle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Add a rectangular obstacle to the simulation.

        Args:
            x: Left coordinate.
            y: Top coordinate.
            width: Obstacle width.
            height: Obstacle height.
        """
        with self._lock:
            self._obstacles.append((x, y, width, height))

    def create_flow_field(
        self,
        name: str = "",
        resolution: Tuple[int, int] = (10, 10),
        field_data: Optional[List[List[Tuple[float, float]]]] = None,
    ) -> FlowField:
        """Create a flow field for crowd navigation.

        Args:
            name: Field name.
            resolution: Grid resolution (cols, rows).
            field_data: Optional pre-computed flow vectors.

        Returns:
            The created FlowField.
        """
        flow = FlowField(
            name=name,
            resolution=resolution,
        )
        if field_data:
            flow.field_data = field_data
        self._flow_fields[flow.id] = flow
        self._total_flow_fields_computed += 1
        return flow

    def reset(self) -> None:
        """Reset the entire crowd dynamics simulation."""
        with self._lock:
            self._agents.clear()
            self._groups.clear()
            self._flow_fields.clear()
            self._density_regions.clear()
            self._active_events.clear()
            self._obstacles.clear()
            self._simulation_frames.clear()
            self._neighbor_cache.clear()
            self._total_agents_spawned = 0
            self._total_groups_created = 0
            self._total_flow_fields_computed = 0
            self._total_events_triggered = 0
            self._total_frames_simulated = 0
            self._tick_count = 0
            self._simulation_time = 0.0
            self._frame_number = 0

    def get_simulation_frames(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent simulation frame snapshots.

        Args:
            limit: Maximum number of most recent frames to return.

        Returns:
            List of serialized SimulationFrame dicts.
        """
        with self._lock:
            recent = self._simulation_frames[-limit:] if limit > 0 else self._simulation_frames
            return [f.to_dict() for f in recent]

    def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get all currently active agents as serialized dicts."""
        with self._lock:
            return [a.to_dict() for a in self._agents.values() if a.active]

    def get_active_events(self) -> List[Dict[str, Any]]:
        """Get all active crowd events as serialized dicts."""
        with self._lock:
            return [e.to_dict() for e in self._active_events.values() if e.active]


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_crowd_dynamics() -> EngineCrowdDynamics:
    """Get or create the singleton EngineCrowdDynamics instance."""
    return EngineCrowdDynamics.get_instance()