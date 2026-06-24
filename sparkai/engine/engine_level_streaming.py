"""
SparkLabs Engine - Level Streaming System

A spatial level streaming system that partitions game worlds into cells,
manages asynchronous loading and unloading of level data, controls
detail level transitions, and predicts player movement for preemptive
content loading.

Architecture:
  LevelStreamingEngine (Singleton)
    |-- StreamingCell         — spatial partition of level data
    |-- CellLoader            — async loading/unloading orchestration
    |-- LODController         — detail level management per cell
    |-- StreamingPriorityQueue — load/unload prioritization
    |-- PreloadPredictor      — movement-based predictive loading

Streaming Pipeline:
  1. World partitioned into grid of StreamingCells
  2. Player position determines active cell radius
  3. Cells within radius are prioritized for loading
  4. LODController selects appropriate detail level
  5. CellLoader asynchronously loads/unloads cell data
  6. PreloadPredictor prefetches cells in movement direction
  7. StreamingPriorityQueue schedules load operations

Usage:
    engine = get_level_streaming_engine()
    engine.initialize_streaming_grid(world_size=(10000, 10000), cell_size=(500, 500))
    engine.set_viewer_position(1500.0, 2300.0)
    engine.update(delta_time)
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from heapq import heappush, heappop
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CellState(Enum):
    """Lifecycle state of a streaming cell."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    ERROR = "error"


class DetailLevel(Enum):
    """Level of detail for streaming cell content."""
    MINIMAL = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    ULTRA = 4


class LoadPriority(Enum):
    """Priority level for cell loading operations."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class StreamingStrategy(Enum):
    """Strategy for determining which cells to load."""
    RADIUS = "radius"
    FRUSTUM = "frustum"
    PREDICTIVE = "predictive"
    MANUAL = "manual"


class PreloadDirection(Enum):
    """Predicted movement directions for preloading."""
    FORWARD = "forward"
    LEFT = "left"
    RIGHT = "right"
    BACKWARD = "backward"
    STATIONARY = "stationary"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StreamingCell:
    """Spatial partition of level data for streaming.

    Each cell represents a fixed-size region of the game world. Cells
    are loaded/unloaded based on distance from the viewer, with
    content managed at multiple detail levels.
    """
    cell_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    grid_x: int = 0
    grid_y: int = 0
    world_x: float = 0.0
    world_y: float = 0.0
    cell_size: Tuple[float, float] = (500.0, 500.0)
    state: CellState = CellState.UNLOADED
    detail_level: DetailLevel = DetailLevel.MEDIUM
    priority: LoadPriority = LoadPriority.NORMAL
    distance_to_viewer: float = float("inf")
    last_access_time: float = 0.0
    load_start_time: float = 0.0
    entity_count: int = 0
    memory_usage: float = 0.0
    resident_entities: List[str] = field(default_factory=list)
    resident_assets: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def contains_point(self, x: float, y: float) -> bool:
        return (self.world_x <= x < self.world_x + self.cell_size[0] and
                self.world_y <= y < self.world_y + self.cell_size[1])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "world_x": self.world_x,
            "world_y": self.world_y,
            "cell_size": list(self.cell_size),
            "state": self.state.value,
            "detail_level": self.detail_level.value,
            "priority": self.priority.value,
            "distance_to_viewer": self.distance_to_viewer,
            "last_access_time": self.last_access_time,
            "entity_count": self.entity_count,
            "memory_usage": self.memory_usage,
            "error_message": self.error_message,
        }


@dataclass
class CellLoader:
    """Asynchronous cell loading and unloading orchestration.

    Manages the lifecycle of streaming cells, processing load/unload
    requests with configurable concurrency limits. Supports callbacks
    for load completion and error handling.
    """
    loader_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    max_concurrent_loads: int = 4
    max_concurrent_unloads: int = 2
    active_loads: int = 0
    active_unloads: int = 0
    total_loaded: int = 0
    total_unloaded: int = 0
    total_errors: int = 0
    _load_queue: deque = field(default_factory=deque, repr=False)
    _unload_queue: deque = field(default_factory=deque, repr=False)
    _on_load_complete: Optional[Callable] = None
    _on_unload_complete: Optional[Callable] = None
    _on_error: Optional[Callable] = None

    def enqueue_load(self, cell_id: str) -> None:
        """Enqueue a cell for loading."""
        if cell_id not in self._load_queue:
            self._load_queue.append(cell_id)

    def enqueue_unload(self, cell_id: str) -> None:
        """Enqueue a cell for unloading."""
        if cell_id not in self._unload_queue:
            self._unload_queue.append(cell_id)

    def process_queues(self, cells: Dict[str, StreamingCell]) -> int:
        """Process pending load and unload operations. Returns count processed."""
        processed = 0

        while self._unload_queue and self.active_unloads < self.max_concurrent_unloads:
            cell_id = self._unload_queue.popleft()
            cell = cells.get(cell_id)
            if cell and cell.state == CellState.LOADED:
                cell.state = CellState.UNLOADING
                self._unload_cell(cell)
                self.active_unloads += 1
                processed += 1

        while self._load_queue and self.active_loads < self.max_concurrent_loads:
            cell_id = self._load_queue.popleft()
            cell = cells.get(cell_id)
            if cell and cell.state == CellState.UNLOADED:
                cell.state = CellState.LOADING
                cell.load_start_time = _time_module.time()
                self._load_cell(cell)
                self.active_loads += 1
                processed += 1

        return processed

    def _load_cell(self, cell: StreamingCell) -> None:
        """Internal cell loading logic. Override for actual asset loading."""
        cell.state = CellState.LOADED
        cell.last_access_time = _time_module.time()
        cell.entity_count = 0
        cell.memory_usage = 0.0
        self.active_loads = max(0, self.active_loads - 1)
        self.total_loaded += 1
        if self._on_load_complete:
            self._on_load_complete(cell)

    def _unload_cell(self, cell: StreamingCell) -> None:
        """Internal cell unloading logic. Override for actual asset cleanup."""
        cell.state = CellState.UNLOADED
        cell.entity_count = 0
        cell.memory_usage = 0.0
        cell.resident_entities.clear()
        cell.resident_assets.clear()
        self.active_unloads = max(0, self.active_unloads - 1)
        self.total_unloaded += 1
        if self._on_unload_complete:
            self._on_unload_complete(cell)

    def set_load_callback(self, callback: Callable) -> None:
        self._on_load_complete = callback

    def set_unload_callback(self, callback: Callable) -> None:
        self._on_unload_complete = callback

    def set_error_callback(self, callback: Callable) -> None:
        self._on_error = callback

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loader_id": self.loader_id,
            "max_concurrent_loads": self.max_concurrent_loads,
            "max_concurrent_unloads": self.max_concurrent_unloads,
            "active_loads": self.active_loads,
            "active_unloads": self.active_unloads,
            "total_loaded": self.total_loaded,
            "total_unloaded": self.total_unloaded,
            "total_errors": self.total_errors,
            "load_queue_size": len(self._load_queue),
            "unload_queue_size": len(self._unload_queue),
        }


@dataclass
class LODController:
    """Detail level management for streaming cells.

    Determines the appropriate detail level for each cell based on
    distance from the viewer. Supports smooth LOD transitions with
    hysteresis to prevent rapid switching at boundaries.
    """
    controller_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    lod_distances: List[float] = field(default_factory=lambda: [
        500.0, 1000.0, 2000.0, 4000.0, 8000.0
    ])
    hysteresis: float = 100.0
    current_lod_counts: Dict[DetailLevel, int] = field(default_factory=dict)
    transition_count: int = 0

    def compute_lod(self, distance: float, current_lod: DetailLevel) -> DetailLevel:
        """Compute the appropriate detail level for a given distance."""
        target_lod = DetailLevel.ULTRA
        for i, dist in enumerate(self.lod_distances):
            if distance < dist:
                target_lod = DetailLevel(i)
                break

        if target_lod.value > current_lod.value:
            if distance < self.lod_distances[target_lod.value - 1] + self.hysteresis:
                return current_lod if current_lod.value < target_lod.value else target_lod
        elif target_lod.value < current_lod.value:
            if distance > self.lod_distances[current_lod.value - 1] - self.hysteresis:
                return current_lod if current_lod.value > target_lod.value else target_lod

        if target_lod != current_lod:
            self.transition_count += 1
        return target_lod

    def get_lod_stats(self) -> Dict[str, Any]:
        return {
            "lod_distances": list(self.lod_distances),
            "hysteresis": self.hysteresis,
            "transition_count": self.transition_count,
            "lod_counts": {
                lod.value: self.current_lod_counts.get(lod, 0)
                for lod in DetailLevel
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_lod_stats()


@dataclass
class StreamingPriorityQueue:
    """Priority queue for cell load/unload operations.

    Orders cells by importance for loading based on distance to viewer,
    priority level, and last access time. Uses a min-heap for efficient
    retrieval of the highest-priority cells.
    """
    queue_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    _load_heap: List[Tuple[float, str]] = field(default_factory=list, repr=False)
    _unload_heap: List[Tuple[float, str]] = field(default_factory=list, repr=False)
    total_prioritized: int = 0

    def push_load(self, cell_id: str, distance: float, priority: LoadPriority,
                  last_access: float) -> None:
        """Push a cell onto the load priority queue."""
        score = distance * 0.7 + priority.value * 100.0 - last_access * 0.01
        heappush(self._load_heap, (score, cell_id))
        self.total_prioritized += 1

    def push_unload(self, cell_id: str, distance: float, last_access: float) -> None:
        """Push a cell onto the unload priority queue (furthest first)."""
        score = -distance - last_access * 0.01
        heappush(self._unload_heap, (score, cell_id))

    def pop_load(self) -> Optional[str]:
        """Pop the highest-priority cell for loading."""
        if self._load_heap:
            return heappop(self._load_heap)[1]
        return None

    def pop_unload(self) -> Optional[str]:
        """Pop the highest-priority cell for unloading."""
        if self._unload_heap:
            return heappop(self._unload_heap)[1]
        return None

    def clear(self) -> None:
        self._load_heap.clear()
        self._unload_heap.clear()

    def size(self) -> int:
        return len(self._load_heap) + len(self._unload_heap)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_id": self.queue_id,
            "load_queue_size": len(self._load_heap),
            "unload_queue_size": len(self._unload_heap),
            "total_prioritized": self.total_prioritized,
        }


@dataclass
class PreloadPredictor:
    """Movement-based predictive loading for streaming cells.

    Analyzes the viewer's movement history to predict future positions
    and preemptively load cells in the predicted direction. Uses a
    velocity smoothing buffer for stable predictions.
    """
    predictor_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    prediction_horizon: float = 2.0
    velocity_smoothing: float = 0.85
    history_size: int = 10
    preload_cells_ahead: int = 3
    _position_history: deque = field(default_factory=deque, repr=False)
    _velocity: List[float] = field(default_factory=lambda: [0.0, 0.0])
    _predicted_position: List[float] = field(default_factory=lambda: [0.0, 0.0])
    _current_direction: PreloadDirection = PreloadDirection.STATIONARY

    def record_position(self, x: float, y: float) -> None:
        """Record a new viewer position for prediction."""
        self._position_history.append((x, y, _time_module.time()))
        if len(self._position_history) > self.history_size:
            self._position_history.popleft()
        self._update_velocity()
        self._predict()

    def _update_velocity(self) -> None:
        if len(self._position_history) < 2:
            self._velocity = [0.0, 0.0]
            return

        newest = self._position_history[-1]
        oldest = self._position_history[0]
        dt = newest[2] - oldest[2]
        if dt < 0.001:
            return

        raw_vx = (newest[0] - oldest[0]) / dt
        raw_vy = (newest[1] - oldest[1]) / dt
        self._velocity[0] = (self.velocity_smoothing * self._velocity[0] +
                             (1.0 - self.velocity_smoothing) * raw_vx)
        self._velocity[1] = (self.velocity_smoothing * self._velocity[1] +
                             (1.0 - self.velocity_smoothing) * raw_vy)

    def _predict(self) -> None:
        if len(self._position_history) < 1:
            return
        current = self._position_history[-1]
        self._predicted_position[0] = (current[0] +
                                       self._velocity[0] * self.prediction_horizon)
        self._predicted_position[1] = (current[1] +
                                       self._velocity[1] * self.prediction_horizon)

        speed = math.sqrt(self._velocity[0] ** 2 + self._velocity[1] ** 2)
        if speed < 0.5:
            self._current_direction = PreloadDirection.STATIONARY
        else:
            norm_vx = self._velocity[0] / speed
            norm_vy = self._velocity[1] / speed
            if abs(norm_vx) > abs(norm_vy):
                self._current_direction = (PreloadDirection.RIGHT if norm_vx > 0
                                           else PreloadDirection.LEFT)
            else:
                self._current_direction = (PreloadDirection.FORWARD if norm_vy > 0
                                           else PreloadDirection.BACKWARD)

    def get_predicted_position(self) -> Tuple[float, float]:
        return (self._predicted_position[0], self._predicted_position[1])

    def get_velocity(self) -> Tuple[float, float]:
        return (self._velocity[0], self._velocity[1])

    def get_direction(self) -> PreloadDirection:
        return self._current_direction

    def get_preload_offsets(self, cell_size: Tuple[float, float]
                            ) -> List[Tuple[float, float]]:
        """Get world-space offsets for cells to preload."""
        if self._current_direction == PreloadDirection.STATIONARY:
            return []

        offsets = []
        vx, vy = self._velocity
        speed = math.sqrt(vx * vx + vy * vy)
        if speed < 0.5:
            return []

        dx = (vx / speed) * cell_size[0]
        dy = (vy / speed) * cell_size[1]

        for i in range(1, self.preload_cells_ahead + 1):
            offsets.append((dx * i, dy * i))

        return offsets

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predictor_id": self.predictor_id,
            "prediction_horizon": self.prediction_horizon,
            "velocity": list(self._velocity),
            "predicted_position": list(self._predicted_position),
            "current_direction": self._current_direction.value,
            "history_size": len(self._position_history),
        }


# ---------------------------------------------------------------------------
# LevelStreamingEngine — Unified Level Streaming Singleton
# ---------------------------------------------------------------------------

class LevelStreamingEngine:
    """Complete level streaming system for SparkLabs.

    Partitions the game world into streaming cells, manages async
    loading/unloading, controls LOD transitions, and predicts player
    movement for preemptive content loading.
    """

    _instance: Optional["LevelStreamingEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "LevelStreamingEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "LevelStreamingEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._cells: Dict[str, StreamingCell] = {}
        self._cell_loader = CellLoader()
        self._lod_controller = LODController()
        self._priority_queue = StreamingPriorityQueue()
        self._preload_predictor = PreloadPredictor()
        self._strategy: StreamingStrategy = StreamingStrategy.PREDICTIVE
        self._viewer_position: List[float] = [0.0, 0.0]
        self._streaming_radius: float = 2000.0
        self._grid_dimensions: Tuple[int, int] = (0, 0)
        self._cell_size: Tuple[float, float] = (500.0, 500.0)
        self._world_size: Tuple[float, float] = (0.0, 0.0)
        self._is_initialized: bool = False
        self._frame_count: int = 0
        self._total_cells_loaded: int = 0

    def initialize_streaming_grid(self, world_size: Tuple[float, float],
                                  cell_size: Tuple[float, float]) -> None:
        """Initialize the streaming grid with world and cell dimensions."""
        self._world_size = world_size
        self._cell_size = cell_size
        grid_x = int(math.ceil(world_size[0] / cell_size[0]))
        grid_y = int(math.ceil(world_size[1] / cell_size[1]))
        self._grid_dimensions = (grid_x, grid_y)

        for gx in range(grid_x):
            for gy in range(grid_y):
                cell = StreamingCell(
                    grid_x=gx, grid_y=gy,
                    world_x=gx * cell_size[0],
                    world_y=gy * cell_size[1],
                    cell_size=cell_size,
                )
                self._cells[cell.cell_id] = cell

        self._is_initialized = True

    def set_viewer_position(self, x: float, y: float) -> None:
        """Update the viewer (player) position for streaming calculations."""
        self._viewer_position = [x, y]
        self._preload_predictor.record_position(x, y)

    def set_streaming_strategy(self, strategy: StreamingStrategy) -> None:
        """Set the cell selection strategy."""
        self._strategy = strategy

    def set_streaming_radius(self, radius: float) -> None:
        """Set the distance within which cells are loaded."""
        self._streaming_radius = radius

    def get_cell(self, cell_id: str) -> Optional[StreamingCell]:
        """Get a streaming cell by ID."""
        return self._cells.get(cell_id)

    def get_cell_at_position(self, x: float, y: float) -> Optional[StreamingCell]:
        """Get the cell containing a world position."""
        if not self._is_initialized:
            return None
        gx = int(x // self._cell_size[0])
        gy = int(y // self._cell_size[1])
        if 0 <= gx < self._grid_dimensions[0] and 0 <= gy < self._grid_dimensions[1]:
            for cell in self._cells.values():
                if cell.grid_x == gx and cell.grid_y == gy:
                    return cell
        return None

    def _get_cells_in_radius(self, cx: float, cy: float,
                             radius: float) -> List[StreamingCell]:
        """Get all cells within a radius of a position."""
        result = []
        for cell in self._cells.values():
            cell_center_x = cell.world_x + cell.cell_size[0] / 2.0
            cell_center_y = cell.world_y + cell.cell_size[1] / 2.0
            dx = cell_center_x - cx
            dy = cell_center_y - cy
            distance = math.sqrt(dx * dx + dy * dy)
            cell.distance_to_viewer = distance
            if distance <= radius:
                result.append(cell)
        return result

    def _update_cell_priorities(self) -> None:
        """Update the priority queue based on current viewer position."""
        self._priority_queue.clear()

        vx, vy = self._viewer_position
        active_cells = self._get_cells_in_radius(vx, vy, self._streaming_radius)

        for cell in active_cells:
            if cell.state == CellState.UNLOADED:
                priority = LoadPriority.HIGH if cell.distance_to_viewer < 500.0 else \
                          LoadPriority.NORMAL if cell.distance_to_viewer < 1000.0 else \
                          LoadPriority.LOW
                self._priority_queue.push_load(
                    cell.cell_id, cell.distance_to_viewer, priority,
                    cell.last_access_time
                )

        for cell in self._cells.values():
            if cell.state == CellState.LOADED and cell.distance_to_viewer > self._streaming_radius:
                self._priority_queue.push_unload(
                    cell.cell_id, cell.distance_to_viewer, cell.last_access_time
                )

    def _preload_predicted_cells(self) -> None:
        """Preload cells in the predicted movement direction."""
        offsets = self._preload_predictor.get_preload_offsets(self._cell_size)
        vx, vy = self._viewer_position
        for dx, dy in offsets:
            px = vx + dx
            py = vy + dy
            cell = self.get_cell_at_position(px, py)
            if cell and cell.state == CellState.UNLOADED:
                self._priority_queue.push_load(
                    cell.cell_id, 0.0, LoadPriority.HIGH, _time_module.time()
                )

    def _update_lod(self) -> None:
        """Update LOD levels for all loaded cells."""
        for cell in self._cells.values():
            if cell.state == CellState.LOADED:
                new_lod = self._lod_controller.compute_lod(
                    cell.distance_to_viewer, cell.detail_level
                )
                cell.detail_level = new_lod

        for lod in DetailLevel:
            self._lod_controller.current_lod_counts[lod] = sum(
                1 for c in self._cells.values()
                if c.state == CellState.LOADED and c.detail_level == lod
            )

    def update(self, delta_time: float) -> None:
        """Execute one frame of the streaming update loop."""
        if not self._is_initialized:
            return

        self._update_cell_priorities()

        if self._strategy == StreamingStrategy.PREDICTIVE:
            self._preload_predicted_cells()

        self._update_lod()

        processed = self._cell_loader.process_queues(self._cells)
        self._total_cells_loaded += processed
        self._frame_count += 1

    def force_load_cell(self, cell_id: str) -> bool:
        """Immediately load a specific cell."""
        cell = self._cells.get(cell_id)
        if cell is None:
            return False
        if cell.state == CellState.LOADED:
            return True
        cell.state = CellState.LOADING
        self._cell_loader._load_cell(cell)
        return True

    def force_unload_cell(self, cell_id: str) -> bool:
        """Immediately unload a specific cell."""
        cell = self._cells.get(cell_id)
        if cell is None:
            return False
        if cell.state == CellState.UNLOADED:
            return True
        cell.state = CellState.UNLOADING
        self._cell_loader._unload_cell(cell)
        return True

    def get_loaded_cells(self) -> List[StreamingCell]:
        """Get all currently loaded cells."""
        return [c for c in self._cells.values() if c.state == CellState.LOADED]

    def get_stats(self) -> Dict[str, Any]:
        cell_states = defaultdict(int)
        for cell in self._cells.values():
            cell_states[cell.state.value] += 1

        return {
            "total_cells": len(self._cells),
            "grid_dimensions": list(self._grid_dimensions),
            "cell_size": list(self._cell_size),
            "world_size": list(self._world_size),
            "streaming_radius": self._streaming_radius,
            "strategy": self._strategy.value,
            "viewer_position": list(self._viewer_position),
            "cell_states": dict(cell_states),
            "total_cells_loaded": self._total_cells_loaded,
            "frame_count": self._frame_count,
            "cell_loader": self._cell_loader.to_dict(),
            "lod_controller": self._lod_controller.to_dict(),
            "priority_queue": self._priority_queue.to_dict(),
            "preload_predictor": self._preload_predictor.to_dict(),
        }


# ---------------------------------------------------------------------------
# Convenience Accessor
# ---------------------------------------------------------------------------

def get_level_streaming_engine() -> LevelStreamingEngine:
    """Get the global LevelStreamingEngine singleton instance."""
    return LevelStreamingEngine()