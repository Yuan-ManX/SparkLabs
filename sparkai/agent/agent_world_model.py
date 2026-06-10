"""
SparkLabs Agent - World Model

Internal mental model of the game world for AI agents. Provides
spatial reasoning, state prediction, strategic planning, and
pathfinding capabilities. Agents maintain their own localized
world model that is continuously updated with observed entities,
terrain knowledge, and predicted trajectories.

Architecture:
  AgentWorldModel (Singleton)
    |-- WorldEntity (tracked game objects with position/velocity/type)
    |-- SpatialCell (partitioned grid cell with density/hazard data)
    |-- TrajectoryPrediction (entity movement forecasting)
    |-- StrategicZone (combat/exploration/resource/safe/danger zones)
    |-- WorldSnapshot (point-in-time full state capture)

Key Features:
  - Spatial grid partitioning for efficient radius queries
  - Velocity-based trajectory prediction with obstacle avoidance
  - Threat detection using distance and approach vector analysis
  - Strategic zone identification via entity density and type clustering
  - Simplified A* pathfinding through spatial grid traversal
  - Point-in-time world snapshots for state comparison and rollback

Usage:
    wm = get_agent_world_model()
    wm.update_entity("player_1", entity_type=WorldEntityType.PLAYER, position=(100, 200))
    threats = wm.detect_threats("player_1", 50.0)
    path = wm.find_path((0, 0), (500, 300), avoid_entities=["enemy_1"])
    snapshot = wm.snapshot()
    stats = wm.get_stats()
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SpatialGridResolution(str, Enum):
    """Resolution levels for the spatial partitioning grid."""
    COARSE = "coarse"
    MEDIUM = "medium"
    FINE = "fine"
    ULTRA_FINE = "ultra_fine"


class PredictionHorizon(str, Enum):
    """Time horizons for trajectory and state prediction."""
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class WorldEntityType(str, Enum):
    """Types of entities tracked in the world model."""
    PLAYER = "player"
    NPC = "npc"
    ITEM = "item"
    OBSTACLE = "obstacle"
    TERRAIN = "terrain"
    HAZARD = "hazard"
    RESOURCE = "resource"
    TRIGGER = "trigger"


class TerrainFeature(str, Enum):
    """Terrain features that affect movement and pathfinding."""
    WALL = "wall"
    PLATFORM = "platform"
    GAP = "gap"
    SLOPE = "slope"
    WATER = "water"
    LAVA = "lava"
    DOOR = "door"
    BRIDGE = "bridge"


class ZoneType(str, Enum):
    """Types of strategic zones identified in the world model."""
    COMBAT = "combat"
    EXPLORATION = "exploration"
    RESOURCE = "resource"
    SAFE = "safe"
    DANGER = "danger"


# ---------------------------------------------------------------------------
# Resolution Constants
# ---------------------------------------------------------------------------

_RESOLUTION_CELL_SIZES: Dict[str, float] = {
    SpatialGridResolution.COARSE.value: 200.0,
    SpatialGridResolution.MEDIUM.value: 100.0,
    SpatialGridResolution.FINE.value: 50.0,
    SpatialGridResolution.ULTRA_FINE.value: 25.0,
}

_HORIZON_STEPS: Dict[str, int] = {
    PredictionHorizon.SHORT_TERM.value: 5,
    PredictionHorizon.MEDIUM_TERM.value: 20,
    PredictionHorizon.LONG_TERM.value: 60,
}

_HORIZON_MAX_DISTANCE: Dict[str, float] = {
    PredictionHorizon.SHORT_TERM.value: 200.0,
    PredictionHorizon.MEDIUM_TERM.value: 800.0,
    PredictionHorizon.LONG_TERM.value: 3000.0,
}

_IMPASSABLE_TERRAIN: Set[str] = {
    TerrainFeature.WALL.value,
    TerrainFeature.GAP.value,
    TerrainFeature.LAVA.value,
    TerrainFeature.WATER.value,
}

_HAZARD_TYPES: Set[str] = {
    WorldEntityType.HAZARD.value,
    WorldEntityType.OBSTACLE.value,
}

_DEFAULT_THREAT_TYPES: Set[str] = {
    WorldEntityType.NPC.value,
    WorldEntityType.HAZARD.value,
}

_ZONE_IGNORE_TYPES: Set[str] = {
    WorldEntityType.TERRAIN.value,
    WorldEntityType.OBSTACLE.value,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WorldEntity:
    """A tracked entity in the world model.

    Attributes:
        id: Unique entity identifier (auto-generated).
        entity_type: Category of entity (player, npc, item, obstacle, etc.).
        position: (x, y) world coordinates.
        velocity: (vx, vy) movement vector.
        size: Bounding radius for collision and spatial queries.
        health: Current health value (0.0-1.0 where 0 is destroyed).
        tags: User-defined tags for filtering and categorization.
        properties: Arbitrary key-value metadata.
        last_updated: Timestamp of the last update to this entity.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_type: WorldEntityType = WorldEntityType.NPC
    position: Tuple[float, float] = (0.0, 0.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    size: float = 1.0
    health: float = 1.0
    tags: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=_time_module.time)

    @property
    def speed(self) -> float:
        """Current scalar speed of the entity."""
        return math.sqrt(self.velocity[0] ** 2 + self.velocity[1] ** 2)

    @property
    def is_moving(self) -> bool:
        """Whether the entity is currently in motion."""
        return self.speed > 0.001

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type.value,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "size": self.size,
            "health": self.health,
            "tags": list(self.tags),
            "properties": dict(self.properties),
            "last_updated": self.last_updated,
            "speed": round(self.speed, 4),
            "is_moving": self.is_moving,
        }


@dataclass
class SpatialCell:
    """A single cell in the spatial partitioning grid.

    Attributes:
        cell_x: Grid X coordinate of this cell.
        cell_y: Grid Y coordinate of this cell.
        entities: List of entity IDs within this cell.
        density: Number of entities per cell area (normalized).
        hazard_level: Aggregate hazard rating (0.0-1.0) within this cell.
        traversable: Whether this cell can be traversed by agents.
    """
    cell_x: int = 0
    cell_y: int = 0
    entities: List[str] = field(default_factory=list)
    density: float = 0.0
    hazard_level: float = 0.0
    traversable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_x": self.cell_x,
            "cell_y": self.cell_y,
            "entity_count": len(self.entities),
            "entities": list(self.entities),
            "density": round(self.density, 4),
            "hazard_level": round(self.hazard_level, 4),
            "traversable": self.traversable,
        }


@dataclass
class TrajectoryPrediction:
    """Predicted movement trajectory for an entity.

    Attributes:
        id: Unique prediction identifier (auto-generated).
        entity_id: The entity this prediction is for.
        predicted_path: Sequence of (x, y) positions the entity will occupy.
        confidence: Confidence score (0.0-1.0) in this prediction.
        time_horizon: The prediction horizon used.
        collision_risks: List of entity IDs that may collide with this entity.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    predicted_path: List[Tuple[float, float]] = field(default_factory=list)
    confidence: float = 0.5
    time_horizon: PredictionHorizon = PredictionHorizon.SHORT_TERM
    collision_risks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "predicted_path": [list(p) for p in self.predicted_path],
            "path_length": len(self.predicted_path),
            "confidence": round(self.confidence, 4),
            "time_horizon": self.time_horizon.value,
            "collision_risks": list(self.collision_risks),
        }


@dataclass
class StrategicZone:
    """A zone of strategic interest identified in the world model.

    Attributes:
        id: Unique zone identifier (auto-generated).
        zone_type: Type of strategic zone (combat, exploration, resource, etc.).
        bounds: (min_x, min_y, max_x, max_y) bounding rectangle.
        priority: Importance score (0.0-1.0) for this zone.
        entities_present: List of entity IDs within this zone.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    zone_type: ZoneType = ZoneType.SAFE
    bounds: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    priority: float = 0.0
    entities_present: List[str] = field(default_factory=list)

    @property
    def center(self) -> Tuple[float, float]:
        """Center point of the zone."""
        return (
            (self.bounds[0] + self.bounds[2]) / 2.0,
            (self.bounds[1] + self.bounds[3]) / 2.0,
        )

    @property
    def area(self) -> float:
        """Area of the zone bounding rectangle."""
        w = self.bounds[2] - self.bounds[0]
        h = self.bounds[3] - self.bounds[1]
        return max(0.0, w * h)

    def contains_point(self, x: float, y: float) -> bool:
        """Check whether a point lies within this zone's bounds."""
        return (
            self.bounds[0] <= x <= self.bounds[2]
            and self.bounds[1] <= y <= self.bounds[3]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "zone_type": self.zone_type.value,
            "bounds": list(self.bounds),
            "center": list(self.center),
            "area": round(self.area, 2),
            "priority": round(self.priority, 4),
            "entities_present": list(self.entities_present),
        }


@dataclass
class WorldSnapshot:
    """A point-in-time capture of the entire world model state.

    Attributes:
        id: Unique snapshot identifier (auto-generated).
        timestamp: Real-world time when this snapshot was taken.
        entities: Serialized entity data.
        spatial_grid: Serialized spatial grid state.
        strategic_zones: Serialized strategic zone data.
        events: List of notable changes since last snapshot.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=_time_module.time)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    spatial_grid: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    strategic_zones: List[Dict[str, Any]] = field(default_factory=list)
    events: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "entity_count": len(self.entities),
            "entities": list(self.entities),
            "grid_cell_count": len(self.spatial_grid),
            "spatial_grid": dict(self.spatial_grid),
            "strategic_zone_count": len(self.strategic_zones),
            "strategic_zones": list(self.strategic_zones),
            "events": list(self.events),
        }


# ---------------------------------------------------------------------------
# AgentWorldModel (Singleton)
# ---------------------------------------------------------------------------

class AgentWorldModel:
    """Internal mental model of the game world for AI agents.

    Provides spatial reasoning, state prediction, strategic planning,
    and pathfinding capabilities. Each agent maintains its own world
    model instance that is continuously updated with observed entities,
    terrain knowledge, and predicted trajectories.

    Usage:
        wm = get_agent_world_model()
        wm.update_entity("player_1", entity_type=WorldEntityType.PLAYER,
                         position=(100, 200), velocity=(5, 0))
        threats = wm.detect_threats("player_1", 50.0)
        path = wm.find_path((0, 0), (500, 300))
        zones = wm.identify_strategic_zones()
        stats = wm.get_stats()
    """

    _instance: Optional["AgentWorldModel"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_ENTITIES = 5000
    _MAX_SNAPSHOTS = 200
    _DEFAULT_CELL_SIZE = 100.0
    _DEFAULT_THREAT_RADIUS = 100.0
    _TRAJECTORY_TIME_STEP = 0.1
    _PATHFINDING_STRAIGHT_COST = 1.0
    _PATHFINDING_DIAGONAL_COST = 1.414
    _PATHFINDING_HAZARD_PENALTY = 5.0
    _PATHFINDING_DENSITY_PENALTY = 2.0
    _MAX_PATH_ITERATIONS = 5000

    def __new__(cls) -> "AgentWorldModel":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentWorldModel":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._entities: Dict[str, WorldEntity] = {}
        self._spatial_grid: Dict[Tuple[int, int], SpatialCell] = {}
        self._grid_resolution: SpatialGridResolution = SpatialGridResolution.MEDIUM
        self._cell_size: float = _RESOLUTION_CELL_SIZES[SpatialGridResolution.MEDIUM.value]
        self._strategic_zones: List[StrategicZone] = []
        self._snapshots: List[WorldSnapshot] = []
        self._terrain_features: Dict[Tuple[int, int], Set[str]] = {}
        self._events: List[str] = []

        self._stats: Dict[str, Any] = {
            "total_entities_updated": 0,
            "total_entities_removed": 0,
            "total_grid_builds": 0,
            "total_trajectories_predicted": 0,
            "total_snapshots_taken": 0,
            "total_threats_detected": 0,
            "total_paths_found": 0,
            "total_zone_analyses": 0,
        }

    # ------------------------------------------------------------------
    # Entity Management
    # ------------------------------------------------------------------

    def update_entity(self, entity_id: str, **kwargs: Any) -> WorldEntity:
        """Register or update a tracked entity in the world model.

        If the entity_id does not exist, a new WorldEntity is created.
        If it already exists, its fields are updated with the provided kwargs.

        Args:
            entity_id: Unique identifier for the entity.
            **kwargs: Fields to set or update (entity_type, position,
                      velocity, size, health, tags, properties).

        Returns:
            The created or updated WorldEntity.
        """
        with self._lock:
            if entity_id in self._entities:
                entity = self._entities[entity_id]
            else:
                # Accept entity_type as string or enum
                entity_type_raw = kwargs.pop("entity_type", WorldEntityType.NPC)
                if isinstance(entity_type_raw, str):
                    entity_type_raw = WorldEntityType(entity_type_raw)
                entity = WorldEntity(id=entity_id, entity_type=entity_type_raw)
                self._entities[entity_id] = entity

            # Update mutable fields
            if "entity_type" in kwargs:
                et = kwargs["entity_type"]
                if isinstance(et, str):
                    et = WorldEntityType(et)
                entity.entity_type = et
            if "position" in kwargs:
                pos = kwargs["position"]
                entity.position = (float(pos[0]), float(pos[1]))
            if "velocity" in kwargs:
                vel = kwargs["velocity"]
                entity.velocity = (float(vel[0]), float(vel[1]))
            if "size" in kwargs:
                entity.size = float(kwargs["size"])
            if "health" in kwargs:
                entity.health = max(0.0, min(1.0, float(kwargs["health"])))
            if "tags" in kwargs:
                entity.tags = list(kwargs["tags"])
            if "properties" in kwargs:
                entity.properties = dict(kwargs["properties"])

            entity.last_updated = _time_module.time()
            self._stats["total_entities_updated"] += 1
            return entity

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity from tracking.

        Args:
            entity_id: The entity to remove.

        Returns:
            True if the entity was found and removed, False otherwise.
        """
        with self._lock:
            if entity_id in self._entities:
                del self._entities[entity_id]
                self._stats["total_entities_removed"] += 1
                return True
            return False

    def get_entity(self, entity_id: str) -> Optional[WorldEntity]:
        """Get a tracked entity by its ID.

        Args:
            entity_id: The entity ID to look up.

        Returns:
            The WorldEntity if found, or None.
        """
        return self._entities.get(entity_id)

    def get_entities_by_type(
        self, entity_type: WorldEntityType,
    ) -> List[WorldEntity]:
        """Filter tracked entities by their type.

        Args:
            entity_type: The WorldEntityType to filter by. Accepts string or enum.

        Returns:
            List of matching WorldEntity objects.
        """
        if isinstance(entity_type, str):
            entity_type = WorldEntityType(entity_type)
        return [
            e for e in self._entities.values()
            if e.entity_type == entity_type
        ]

    def get_entities_in_radius(
        self, x: float, y: float, radius: float,
        entity_type: Optional[WorldEntityType] = None,
    ) -> List[WorldEntity]:
        """Spatial query for entities within a given radius.

        Uses the spatial grid for efficient lookup if available, falling
        back to brute-force distance checks.

        Args:
            x: Center X coordinate.
            y: Center Y coordinate.
            radius: Search radius in world units.
            entity_type: Optional filter by entity type.

        Returns:
            List of WorldEntity objects within the radius, sorted nearest first.
        """
        results: List[Tuple[float, WorldEntity]] = []
        radius_sq = radius * radius

        # Use spatial grid for efficient candidate lookup
        if self._spatial_grid:
            cells_in_radius = int(math.ceil(radius / self._cell_size))
            cx, cy = self._world_to_cell(x, y)
            candidates: Set[str] = set()
            for dx in range(-cells_in_radius, cells_in_radius + 1):
                for dy in range(-cells_in_radius, cells_in_radius + 1):
                    cell = self._spatial_grid.get((cx + dx, cy + dy))
                    if cell:
                        candidates.update(cell.entities)

            for eid in candidates:
                entity = self._entities.get(eid)
                if entity is None:
                    continue
                if entity_type is not None and entity.entity_type != entity_type:
                    continue
                dist_sq = (entity.position[0] - x) ** 2 + (entity.position[1] - y) ** 2
                if dist_sq <= radius_sq:
                    results.append((dist_sq, entity))
        else:
            # Fallback: scan all entities
            if isinstance(entity_type, str):
                entity_type = WorldEntityType(entity_type)
            for entity in self._entities.values():
                if entity_type is not None and entity.entity_type != entity_type:
                    continue
                dist_sq = (entity.position[0] - x) ** 2 + (entity.position[1] - y) ** 2
                if dist_sq <= radius_sq:
                    results.append((dist_sq, entity))

        results.sort(key=lambda item: item[0])
        return [entity for _, entity in results]

    # ------------------------------------------------------------------
    # Spatial Grid
    # ------------------------------------------------------------------

    def build_spatial_grid(
        self, resolution: SpatialGridResolution = SpatialGridResolution.MEDIUM,
    ) -> Dict[Tuple[int, int], SpatialCell]:
        """Rebuild the spatial partitioning grid.

        Clears the existing grid and redistributes all entities into
        cells based on their current positions. Each cell tracks entity
        density, hazard level, and traversability.

        Args:
            resolution: Grid resolution level.

        Returns:
            The rebuilt spatial grid dictionary.
        """
        with self._lock:
            if isinstance(resolution, str):
                resolution = SpatialGridResolution(resolution)

            self._grid_resolution = resolution
            self._cell_size = _RESOLUTION_CELL_SIZES.get(
                resolution.value, self._DEFAULT_CELL_SIZE,
            )
            self._spatial_grid.clear()

            # Assign each entity to its cell
            for entity in self._entities.values():
                cx, cy = self._world_to_cell(
                    entity.position[0], entity.position[1],
                )
                cell_key = (cx, cy)
                if cell_key not in self._spatial_grid:
                    self._spatial_grid[cell_key] = SpatialCell(
                        cell_x=cx, cell_y=cy,
                    )
                self._spatial_grid[cell_key].entities.append(entity.id)

            # Compute cell metadata
            for cell in self._spatial_grid.values():
                # Density: entities per cell area, normalized
                cell.density = len(cell.entities) / max(1.0, self._cell_size)

                # Hazard level: fraction of entities in this cell that are hazards
                hazard_count = 0
                for eid in cell.entities:
                    entity = self._entities.get(eid)
                    if entity and entity.entity_type.value in _HAZARD_TYPES:
                        hazard_count += 1
                cell.hazard_level = (
                    hazard_count / max(1, len(cell.entities))
                    if cell.entities else 0.0
                )

                # Traversability: check terrain features
                terrain_types = self._terrain_features.get(
                    (cell.cell_x, cell.cell_y), set(),
                )
                has_impassable = bool(
                    terrain_types & _IMPASSABLE_TERRAIN,
                )
                cell.traversable = not has_impassable and cell.hazard_level < 0.8

            self._stats["total_grid_builds"] += 1
            return dict(self._spatial_grid)

    def get_cell(self, x: float, y: float) -> Optional[SpatialCell]:
        """Get the spatial cell at a given world coordinate.

        Args:
            x: World X coordinate.
            y: World Y coordinate.

        Returns:
            The SpatialCell at that coordinate, or None if the grid
            has not been built or the cell is empty.
        """
        cx, cy = self._world_to_cell(x, y)
        return self._spatial_grid.get((cx, cy))

    def set_terrain(
        self, x: float, y: float, feature: TerrainFeature,
    ) -> None:
        """Record a terrain feature at a given world coordinate.

        Args:
            x: World X coordinate.
            y: World Y coordinate.
            feature: The terrain feature to record.
        """
        if isinstance(feature, str):
            feature = TerrainFeature(feature)
        cx, cy = self._world_to_cell(x, y)
        cell_key = (cx, cy)
        if cell_key not in self._terrain_features:
            self._terrain_features[cell_key] = set()
        self._terrain_features[cell_key].add(feature.value)

        # Update traversability for existing grid cell
        cell = self._spatial_grid.get(cell_key)
        if cell:
            if feature.value in _IMPASSABLE_TERRAIN:
                cell.traversable = False

    def clear_terrain(self, x: float, y: float) -> None:
        """Remove all terrain features at a given world coordinate.

        Args:
            x: World X coordinate.
            y: World Y coordinate.
        """
        cx, cy = self._world_to_cell(x, y)
        cell_key = (cx, cy)
        self._terrain_features.pop(cell_key, None)

        # Re-evaluate traversability
        cell = self._spatial_grid.get(cell_key)
        if cell:
            cell.traversable = cell.hazard_level < 0.8

    # ------------------------------------------------------------------
    # Trajectory Prediction
    # ------------------------------------------------------------------

    def predict_trajectory(
        self,
        entity_id: str,
        horizon: PredictionHorizon = PredictionHorizon.SHORT_TERM,
    ) -> Optional[TrajectoryPrediction]:
        """Predict the future path of an entity based on its velocity and obstacles.

        Simulates forward movement in discrete time steps, accounting for
        the entity's current velocity and checking for obstacles and terrain
        that may alter or block the path.

        Args:
            entity_id: The entity to predict for.
            horizon: How far into the future to predict.

        Returns:
            A TrajectoryPrediction with the predicted path, or None if
            the entity is not tracked.
        """
        entity = self._entities.get(entity_id)
        if entity is None:
            return None

        if isinstance(horizon, str):
            horizon = PredictionHorizon(horizon)

        steps = _HORIZON_STEPS.get(horizon.value, 5)
        max_distance = _HORIZON_MAX_DISTANCE.get(horizon.value, 200.0)
        time_step = self._TRAJECTORY_TIME_STEP

        predicted_path: List[Tuple[float, float]] = [
            (entity.position[0], entity.position[1]),
        ]
        current_x, current_y = entity.position
        vx, vy = entity.velocity
        collision_risks: Set[str] = set()

        total_distance = 0.0

        for step in range(steps):
            # Compute next position based on current velocity
            next_x = current_x + vx * time_step
            next_y = current_y + vy * time_step

            # Check cell traversability at next position
            target_cell = self.get_cell(next_x, next_y)
            if target_cell and not target_cell.traversable:
                # Entity would hit an obstacle; try to slide along edges
                # Try horizontal slide
                slide_cell_x = self.get_cell(next_x, current_y)
                if slide_cell_x and slide_cell_x.traversable:
                    next_y = current_y
                    vy *= 0.5  # Dampen vertical velocity
                # Try vertical slide
                slide_cell_y = self.get_cell(current_x, next_y)
                if slide_cell_y and slide_cell_y.traversable:
                    next_x = current_x
                    vx *= 0.5  # Dampen horizontal velocity
                if not target_cell.traversable and (
                    (slide_cell_x and not slide_cell_x.traversable)
                    and (slide_cell_y and not slide_cell_y.traversable)
                ):
                    # Fully blocked; stop prediction
                    break

            step_distance = math.sqrt(
                (next_x - current_x) ** 2 + (next_y - current_y) ** 2,
            )
            total_distance += step_distance
            if total_distance > max_distance:
                break

            predicted_path.append((next_x, next_y))
            current_x, current_y = next_x, next_y

            # Check for potential collisions with other entities at this position
            nearby = self.get_entities_in_radius(current_x, current_y, entity.size * 2.0)
            for other in nearby:
                if other.id != entity_id:
                    collision_risks.add(other.id)

        # Compute confidence based on entity speed, obstacles, and horizon
        if entity.speed < 0.001:
            confidence = 0.95  # Stationary entities are highly predictable
        else:
            # More steps = more uncertainty
            steps_factor = 1.0 - min(0.5, steps / 100.0)
            # Collision risks reduce confidence
            collision_factor = 1.0 - min(0.3, len(collision_risks) * 0.05)
            confidence = steps_factor * collision_factor

        self._stats["total_trajectories_predicted"] += 1

        return TrajectoryPrediction(
            entity_id=entity_id,
            predicted_path=predicted_path,
            confidence=round(confidence, 4),
            time_horizon=horizon,
            collision_risks=list(collision_risks),
        )

    def predict_state(
        self, timestamp_offset: float,
    ) -> Dict[str, List[Tuple[float, float]]]:
        """Predict future world state by simulating all entities forward.

        Each tracked entity is advanced by the given time offset based
        on its current velocity, producing a predicted position map.

        Args:
            timestamp_offset: Number of seconds to simulate forward.

        Returns:
            A dict mapping entity_id to its predicted path over the offset.
        """
        predicted_state: Dict[str, List[Tuple[float, float]]] = {}

        time_step = self._TRAJECTORY_TIME_STEP
        total_steps = max(1, int(timestamp_offset / time_step))

        for entity in self._entities.values():
            path: List[Tuple[float, float]] = []
            cx, cy = entity.position
            vx, vy = entity.velocity

            for _ in range(min(total_steps, 100)):
                cx += vx * time_step
                cy += vy * time_step
                path.append((round(cx, 2), round(cy, 2)))

            predicted_state[entity.id] = path

        return predicted_state

    # ------------------------------------------------------------------
    # Strategic Zones
    # ------------------------------------------------------------------

    def identify_strategic_zones(self) -> List[StrategicZone]:
        """Analyze the spatial grid to find zones of strategic interest.

        Scans all populated grid cells and clusters them into zones
        based on entity types, density, and hazard levels. Zones are
        classified as COMBAT, EXPLORATION, RESOURCE, SAFE, or DANGER.

        Returns:
            List of identified StrategicZone objects, sorted by priority
            descending.
        """
        zones: List[StrategicZone] = []

        if not self._spatial_grid:
            self.build_spatial_grid()

        # Group cells by entity composition
        combat_cells: List[Tuple[int, int]] = []
        resource_cells: List[Tuple[int, int]] = []
        danger_cells: List[Tuple[int, int]] = []
        safe_cells: List[Tuple[int, int]] = []

        for (cx, cy), cell in self._spatial_grid.items():
            if not cell.entities:
                continue

            npc_count = 0
            item_count = 0
            resource_count = 0
            hazard_count = 0

            for eid in cell.entities:
                entity = self._entities.get(eid)
                if entity is None:
                    continue
                et = entity.entity_type.value
                if et == WorldEntityType.NPC.value:
                    npc_count += 1
                elif et == WorldEntityType.ITEM.value:
                    item_count += 1
                elif et == WorldEntityType.RESOURCE.value:
                    resource_count += 1
                elif et in _HAZARD_TYPES:
                    hazard_count += 1

            total = len(cell.entities)
            if hazard_count > total * 0.5:
                danger_cells.append((cx, cy))
            elif resource_count > 0 or item_count > 0:
                resource_cells.append((cx, cy))
            elif npc_count > 0:
                combat_cells.append((cx, cy))
            elif hazard_count == 0 and total > 0:
                safe_cells.append((cx, cy))

        # Create zones from clustered cells
        zones.extend(self._cluster_cells_to_zones(
            combat_cells, ZoneType.COMBAT,
        ))
        zones.extend(self._cluster_cells_to_zones(
            resource_cells, ZoneType.RESOURCE,
        ))
        zones.extend(self._cluster_cells_to_zones(
            danger_cells, ZoneType.DANGER,
        ))
        zones.extend(self._cluster_cells_to_zones(
            safe_cells, ZoneType.SAFE,
        ))

        # Add exploration zones for large empty areas
        if not safe_cells:
            zones.extend(self._identify_exploration_zones())

        # Compute priority for each zone
        for zone in zones:
            entity_count = len(zone.entities_present)
            if zone.zone_type == ZoneType.COMBAT:
                zone.priority = min(1.0, entity_count * 0.1)
            elif zone.zone_type == ZoneType.RESOURCE:
                zone.priority = min(1.0, entity_count * 0.15)
            elif zone.zone_type == ZoneType.DANGER:
                zone.priority = min(1.0, entity_count * 0.12)
            elif zone.zone_type == ZoneType.SAFE:
                zone.priority = min(1.0, entity_count * 0.05 + 0.1)
            else:
                zone.priority = 0.05 * entity_count

        zones.sort(key=lambda z: z.priority, reverse=True)
        self._strategic_zones = zones
        self._stats["total_zone_analyses"] += 1
        return zones

    def _cluster_cells_to_zones(
        self,
        cells: List[Tuple[int, int]],
        zone_type: ZoneType,
    ) -> List[StrategicZone]:
        """Cluster nearby cells into strategic zones.

        Uses a simple distance-based clustering: cells within 2 grid units
        of each other are grouped into the same zone.

        Args:
            cells: List of (cell_x, cell_y) tuples to cluster.
            zone_type: The type of zone to create.

        Returns:
            List of StrategicZone objects.
        """
        if not cells:
            return []

        visited: Set[Tuple[int, int]] = set()
        zones: List[StrategicZone] = []

        for seed_cell in cells:
            if seed_cell in visited:
                continue

            # Flood-fill cluster
            cluster: List[Tuple[int, int]] = []
            queue: List[Tuple[int, int]] = [seed_cell]
            visited.add(seed_cell)

            while queue:
                current = queue.pop(0)
                cluster.append(current)
                cx, cy = current

                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        neighbor = (cx + dx, cy + dy)
                        if neighbor in visited:
                            continue
                        if neighbor not in cells:
                            continue
                        # Use set membership via the cells list
                        found = False
                        for c in cells:
                            if c == neighbor:
                                found = True
                                break
                        if not found:
                            continue
                        visited.add(neighbor)
                        queue.append(neighbor)

            if not cluster:
                continue

            # Compute zone bounds
            min_x = min(c[0] for c in cluster)
            min_y = min(c[1] for c in cluster)
            max_x = max(c[0] for c in cluster)
            max_y = max(c[1] for c in cluster)

            # Collect entity IDs from all cells in the cluster
            entity_ids: List[str] = []
            for cx, cy in cluster:
                cell = self._spatial_grid.get((cx, cy))
                if cell:
                    entity_ids.extend(cell.entities)

            zone = StrategicZone(
                zone_type=zone_type,
                bounds=(
                    min_x * self._cell_size,
                    min_y * self._cell_size,
                    (max_x + 1) * self._cell_size,
                    (max_y + 1) * self._cell_size,
                ),
                entities_present=entity_ids,
            )
            zones.append(zone)

        return zones

    def _identify_exploration_zones(self) -> List[StrategicZone]:
        """Identify exploration zones in unpopulated areas.

        Scans for large empty rectangular regions in the grid that
        could be interesting for exploration.

        Returns:
            List of StrategicZone objects with EXPLORATION type.
        """
        zones: List[StrategicZone] = []

        if not self._spatial_grid:
            return zones

        populated: Set[Tuple[int, int]] = set(
            (c.cell_x, c.cell_y)
            for c in self._spatial_grid.values()
            if c.entities
        )

        if not populated:
            return zones

        min_cx = min(p[0] for p in populated)
        max_cx = max(p[0] for p in populated)
        min_cy = min(p[1] for p in populated)
        max_cy = max(p[1] for p in populated)

        # Search for empty rectangular regions at the edges
        search_bounds = [
            (min_cx - 10, min_cy - 10, min_cx - 1, max_cy + 10),  # Left edge
            (max_cx + 1, min_cy - 10, max_cx + 10, max_cy + 10),   # Right edge
            (min_cx - 10, min_cy - 10, max_cx + 10, min_cy - 1),    # Bottom edge
            (min_cx - 10, max_cy + 1, max_cx + 10, max_cy + 10),    # Top edge
        ]

        for search_min_x, search_min_y, search_max_x, search_max_y in search_bounds:
            width = search_max_x - search_min_x
            height = search_max_y - search_min_y
            if width <= 0 or height <= 0:
                continue

            zone = StrategicZone(
                zone_type=ZoneType.EXPLORATION,
                bounds=(
                    search_min_x * self._cell_size,
                    search_min_y * self._cell_size,
                    search_max_x * self._cell_size,
                    search_max_y * self._cell_size,
                ),
                priority=0.1,
            )
            zones.append(zone)

        return zones

    # ------------------------------------------------------------------
    # Threat Detection
    # ------------------------------------------------------------------

    def detect_threats(
        self,
        agent_id: str,
        threat_radius: float = 100.0,
        threat_types: Optional[Set[str]] = None,
    ) -> List[WorldEntity]:
        """Find entities that pose threats to a given agent.

        A threat is defined as an entity of a threatening type that is
        within the threat radius AND moving toward the agent (based on
        velocity direction), or a stationary hazard within the radius.

        Args:
            agent_id: The entity ID to check threats for.
            threat_radius: Maximum distance to check for threats.
            threat_types: Set of entity type values considered threatening.
                          Defaults to NPC and HAZARD types.

        Returns:
            List of threatening WorldEntity objects sorted by danger level
            (closest and fastest-approaching first).
        """
        agent = self._entities.get(agent_id)
        if agent is None:
            return []

        if threat_types is None:
            threat_types = _DEFAULT_THREAT_TYPES

        # Get nearby entities
        nearby = self.get_entities_in_radius(
            agent.position[0], agent.position[1], threat_radius,
        )

        threats: List[Tuple[float, WorldEntity]] = []

        for entity in nearby:
            if entity.id == agent_id:
                continue
            if entity.entity_type.value not in threat_types:
                continue

            # Compute threat score
            dist = math.sqrt(
                (entity.position[0] - agent.position[0]) ** 2
                + (entity.position[1] - agent.position[1]) ** 2,
            )
            if dist < 0.001:
                dist = 0.001

            # Approach factor: is the entity moving toward the agent?
            dx = agent.position[0] - entity.position[0]
            dy = agent.position[1] - entity.position[1]
            dist_vec_mag = math.sqrt(dx ** 2 + dy ** 2) or 1.0
            dx_norm = dx / dist_vec_mag
            dy_norm = dy / dist_vec_mag

            speed = entity.speed
            if speed > 0.001:
                vel_mag = speed or 1.0
                approach_dot = (
                    (entity.velocity[0] / vel_mag) * dx_norm
                    + (entity.velocity[1] / vel_mag) * dy_norm
                )
            else:
                approach_dot = 0.0

            # Immediate threats: within entity size * 3
            if dist <= entity.size * 3.0:
                threat_score = 1.0
            else:
                # Score based on proximity and approach direction
                proximity_score = 1.0 - min(1.0, dist / threat_radius)
                approach_score = max(0.0, approach_dot) * 0.5 + 0.5
                threat_score = proximity_score * 0.4 + approach_score * 0.6

            if threat_score > 0.0:
                threats.append((threat_score, entity))

        threats.sort(key=lambda item: item[0], reverse=True)
        self._stats["total_threats_detected"] += len(threats)
        return [entity for _, entity in threats]

    # ------------------------------------------------------------------
    # Pathfinding
    # ------------------------------------------------------------------

    def find_path(
        self,
        start_pos: Tuple[float, float],
        end_pos: Tuple[float, float],
        avoid_entities: Optional[List[str]] = None,
    ) -> List[Tuple[float, float]]:
        """Find a path through the spatial grid using simplified A*.

        Navigates from start to end position using only traversable
        cells. Cells with hazards or high density incur movement penalties.
        Optionally avoids specific entities by blocking their cells.

        Args:
            start_pos: Starting world coordinates (x, y).
            end_pos: Target world coordinates (x, y).
            avoid_entities: Optional list of entity IDs whose cells to avoid.

        Returns:
            List of (x, y) waypoints from start to end. Returns an empty
            list if no path is found.
        """
        if not self._spatial_grid:
            self.build_spatial_grid()

        avoid_set = set(avoid_entities) if avoid_entities else set()

        start_cell = self._world_to_cell(start_pos[0], start_pos[1])
        end_cell = self._world_to_cell(end_pos[0], end_pos[1])

        if start_cell == end_cell:
            return [start_pos, end_pos]

        # Compute which cells to avoid (cells containing excluded entities)
        blocked_cells: Set[Tuple[int, int]] = set()
        for cell_key, cell in self._spatial_grid.items():
            if any(eid in avoid_set for eid in cell.entities):
                blocked_cells.add(cell_key)

        # A* data structures
        open_set: List[Tuple[float, int, int]] = []
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {start_cell: 0.0}
        closed_set: Set[Tuple[int, int]] = set()

        import heapq

        start_h = self._heuristic(start_cell, end_cell)
        heapq.heappush(open_set, (start_h, start_cell[0], start_cell[1]))

        iterations = 0
        found_path = False

        while open_set and iterations < self._MAX_PATH_ITERATIONS:
            iterations += 1
            _, cx, cy = heapq.heappop(open_set)
            current = (cx, cy)

            if current in closed_set:
                continue
            closed_set.add(current)

            if current == end_cell:
                found_path = True
                break

            for neighbor in self._get_neighbors(current, blocked_cells):
                if neighbor in closed_set:
                    continue

                cell = self._spatial_grid.get(neighbor)
                move_cost = self._PATHFINDING_STRAIGHT_COST

                # Penalize diagonal movement
                if neighbor[0] != current[0] and neighbor[1] != current[1]:
                    move_cost = self._PATHFINDING_DIAGONAL_COST

                # Penalize hazardous and dense cells
                if cell:
                    move_cost += cell.hazard_level * self._PATHFINDING_HAZARD_PENALTY
                    move_cost += cell.density * self._PATHFINDING_DENSITY_PENALTY

                tentative_g = g_score.get(current, float("inf")) + move_cost

                if tentative_g < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + self._heuristic(neighbor, end_cell)
                    heapq.heappush(open_set, (f_score, neighbor[0], neighbor[1]))
                    came_from[neighbor] = current

        if not found_path:
            self._stats["total_paths_found"] += 1
            return []

        # Reconstruct path
        path_cells: List[Tuple[int, int]] = []
        current = end_cell
        while current != start_cell:
            path_cells.append(current)
            current = came_from.get(current, start_cell)
        path_cells.append(start_cell)
        path_cells.reverse()

        # Convert cell coordinates to world positions (cell center)
        half_cell = self._cell_size / 2.0
        waypoints: List[Tuple[float, float]] = []

        # Start at exact start position
        waypoints.append((float(start_pos[0]), float(start_pos[1])))

        for i, cell_coord in enumerate(path_cells):
            wx = cell_coord[0] * self._cell_size + half_cell
            wy = cell_coord[1] * self._cell_size + half_cell

            if i == len(path_cells) - 1:
                # Last point: use exact end position
                waypoints.append((float(end_pos[0]), float(end_pos[1])))
            else:
                waypoints.append((wx, wy))

        self._stats["total_paths_found"] += 1
        return waypoints

    def _heuristic(
        self,
        cell_a: Tuple[int, int],
        cell_b: Tuple[int, int],
    ) -> float:
        """Octile distance heuristic for grid-based A*."""
        dx = abs(cell_a[0] - cell_b[0])
        dy = abs(cell_a[1] - cell_b[1])
        return (
            self._PATHFINDING_STRAIGHT_COST * max(dx, dy)
            + (self._PATHFINDING_DIAGONAL_COST - self._PATHFINDING_STRAIGHT_COST)
            * min(dx, dy)
        )

    def _get_neighbors(
        self,
        cell: Tuple[int, int],
        blocked_cells: Set[Tuple[int, int]],
    ) -> List[Tuple[int, int]]:
        """Get traversable neighboring cells (8-connected)."""
        neighbors: List[Tuple[int, int]] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = cell[0] + dx, cell[1] + dy
                neighbor = (nx, ny)

                # Check if blocked by avoid_entities
                if neighbor in blocked_cells:
                    continue

                # Check traversability
                grid_cell = self._spatial_grid.get(neighbor)
                if grid_cell and not grid_cell.traversable:
                    continue

                neighbors.append(neighbor)

        return neighbors

    # ------------------------------------------------------------------
    # Nearest Entity Query
    # ------------------------------------------------------------------

    def find_nearest(
        self,
        target_type: WorldEntityType,
        from_pos: Tuple[float, float],
        max_radius: float = float("inf"),
    ) -> Optional[WorldEntity]:
        """Find the nearest entity of a given type from a position.

        Args:
            target_type: The WorldEntityType to search for.
            from_pos: (x, y) position to search from.
            max_radius: Maximum search radius. Unlimited if not specified.

        Returns:
            The nearest matching WorldEntity, or None if none found.
        """
        if isinstance(target_type, str):
            target_type = WorldEntityType(target_type)

        best_dist = float("inf")
        best_entity: Optional[WorldEntity] = None

        for entity in self._entities.values():
            if entity.entity_type != target_type:
                continue

            dist_sq = (
                (entity.position[0] - from_pos[0]) ** 2
                + (entity.position[1] - from_pos[1]) ** 2
            )

            if dist_sq < best_dist:
                dist = math.sqrt(dist_sq)
                if dist <= max_radius:
                    best_dist = dist_sq
                    best_entity = entity

        return best_entity

    # ------------------------------------------------------------------
    # World Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> WorldSnapshot:
        """Create a point-in-time snapshot of the entire world model.

        Captures all entities, the spatial grid, strategic zones, and
        recent events into a serializable WorldSnapshot for later
        comparison or rollback.

        Returns:
            A WorldSnapshot containing the current world state.
        """
        with self._lock:
            # Serialize entities
            entity_data = [
                e.to_dict() for e in self._entities.values()
            ]

            # Serialize spatial grid
            grid_data: Dict[str, Dict[str, Any]] = {}
            for cell_key, cell in self._spatial_grid.items():
                grid_data[f"{cell_key[0]},{cell_key[1]}"] = cell.to_dict()

            # Serialize strategic zones
            zone_data = [
                z.to_dict() for z in self._strategic_zones
            ]

            # Collect recent events
            events = list(self._events[-50:])

            snapshot = WorldSnapshot(
                timestamp=_time_module.time(),
                entities=entity_data,
                spatial_grid=grid_data,
                strategic_zones=zone_data,
                events=events,
            )

            # Maintain snapshot history limit
            self._snapshots.append(snapshot)
            if len(self._snapshots) > self._MAX_SNAPSHOTS:
                self._snapshots.pop(0)

            self._stats["total_snapshots_taken"] += 1
            return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[WorldSnapshot]:
        """Retrieve a previously taken snapshot by its ID.

        Args:
            snapshot_id: The snapshot ID to retrieve.

        Returns:
            The WorldSnapshot if found, or None.
        """
        for snap in self._snapshots:
            if snap.id == snapshot_id:
                return snap
        return None

    def compare_snapshots(
        self, snapshot_a_id: str, snapshot_b_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Compare two snapshots and compute the differences.

        Args:
            snapshot_a_id: ID of the earlier snapshot.
            snapshot_b_id: ID of the later snapshot.

        Returns:
            A dict with entity changes, zone changes, and time delta,
            or None if either snapshot is not found.
        """
        snap_a = self.get_snapshot(snapshot_a_id)
        snap_b = self.get_snapshot(snapshot_b_id)
        if not snap_a or not snap_b:
            return None

        entity_ids_a = {e["id"] for e in snap_a.entities}
        entity_ids_b = {e["id"] for e in snap_b.entities}

        return {
            "time_delta": round(snap_b.timestamp - snap_a.timestamp, 4),
            "entities_added": list(entity_ids_b - entity_ids_a),
            "entities_removed": list(entity_ids_a - entity_ids_b),
            "entities_retained": list(entity_ids_a & entity_ids_b),
            "total_entities_a": len(snap_a.entities),
            "total_entities_b": len(snap_b.entities),
            "zone_count_a": len(snap_a.strategic_zones),
            "zone_count_b": len(snap_b.strategic_zones),
            "events_since_a": snap_b.events,
        }

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(self, event_description: str) -> None:
        """Record a notable world event.

        Args:
            event_description: Human-readable description of the event.
        """
        timestamp = _time_module.time()
        self._events.append(
            f"[{timestamp:.3f}] {event_description}",
        )

    def get_recent_events(self, limit: int = 20) -> List[str]:
        """Get the most recent world events.

        Args:
            limit: Maximum number of events to return.

        Returns:
            List of recent event strings.
        """
        return list(self._events[-limit:])

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics about the world model.

        Returns:
            A dict with entity counts, grid status, and operational metrics.
        """
        with self._lock:
            entity_type_counts: Dict[str, int] = {}
            for entity in self._entities.values():
                et = entity.entity_type.value
                entity_type_counts[et] = entity_type_counts.get(et, 0) + 1

            moving_count = sum(
                1 for e in self._entities.values() if e.is_moving
            )

            return {
                "total_entities": len(self._entities),
                "entity_types": entity_type_counts,
                "moving_entities": moving_count,
                "stationary_entities": len(self._entities) - moving_count,
                "spatial_grid": {
                    "resolution": self._grid_resolution.value,
                    "cell_size": self._cell_size,
                    "cell_count": len(self._spatial_grid),
                    "total_entities_indexed": sum(
                        len(c.entities) for c in self._spatial_grid.values()
                    ),
                },
                "strategic_zones": len(self._strategic_zones),
                "terrain_features": len(self._terrain_features),
                "snapshots": len(self._snapshots),
                "events_recorded": len(self._events),
                "operations": dict(self._stats),
                "memory_estimate_bytes": self._estimate_memory_usage(),
            }

    def _estimate_memory_usage(self) -> int:
        """Rough estimate of memory used by the world model.

        Returns:
            Estimated memory usage in bytes.
        """
        # Rough per-entity overhead estimate
        entity_bytes = len(self._entities) * 512
        grid_bytes = len(self._spatial_grid) * 256
        zone_bytes = len(self._strategic_zones) * 128
        snapshot_bytes = len(self._snapshots) * 1024
        return entity_bytes + grid_bytes + zone_bytes + snapshot_bytes

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _world_to_cell(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coordinates to grid cell coordinates.

        Args:
            x: World X coordinate.
            y: World Y coordinate.

        Returns:
            (cell_x, cell_y) tuple.
        """
        return (
            int(math.floor(x / self._cell_size)),
            int(math.floor(y / self._cell_size)),
        )

    def _cell_to_world_center(
        self, cell_x: int, cell_y: int,
    ) -> Tuple[float, float]:
        """Convert grid cell coordinates to the cell's world center.

        Args:
            cell_x: Cell X coordinate.
            cell_y: Cell Y coordinate.

        Returns:
            (world_x, world_y) center point of the cell.
        """
        half = self._cell_size / 2.0
        return (
            cell_x * self._cell_size + half,
            cell_y * self._cell_size + half,
        )

    # ------------------------------------------------------------------
    # Serialization & Reset
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entire world model state to a dict.

        Returns:
            A dict containing the full serializable world model state.
        """
        with self._lock:
            return {
                "grid_resolution": self._grid_resolution.value,
                "cell_size": self._cell_size,
                "entity_count": len(self._entities),
                "entities": {
                    eid: entity.to_dict()
                    for eid, entity in self._entities.items()
                },
                "spatial_grid": {
                    f"{k[0]},{k[1]}": cell.to_dict()
                    for k, cell in self._spatial_grid.items()
                },
                "terrain_features": {
                    f"{k[0]},{k[1]}": list(v)
                    for k, v in self._terrain_features.items()
                },
                "strategic_zones": [z.to_dict() for z in self._strategic_zones],
                "snapshot_count": len(self._snapshots),
                "events": list(self._events),
                "stats": dict(self._stats),
            }

    def reset(self) -> None:
        """Reset the world model to its initial empty state."""
        with self._lock:
            self._entities.clear()
            self._spatial_grid.clear()
            self._grid_resolution = SpatialGridResolution.MEDIUM
            self._cell_size = _RESOLUTION_CELL_SIZES[SpatialGridResolution.MEDIUM.value]
            self._strategic_zones.clear()
            self._snapshots.clear()
            self._terrain_features.clear()
            self._events.clear()
            self._stats = {
                "total_entities_updated": 0,
                "total_entities_removed": 0,
                "total_grid_builds": 0,
                "total_trajectories_predicted": 0,
                "total_snapshots_taken": 0,
                "total_threats_detected": 0,
                "total_paths_found": 0,
                "total_zone_analyses": 0,
            }


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_agent_world_model() -> AgentWorldModel:
    """Get the singleton AgentWorldModel instance.

    Returns:
        The global world model instance.
    """
    return AgentWorldModel.get_instance()