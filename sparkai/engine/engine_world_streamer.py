"""
SparkLabs Engine World Streamer

Advanced world streaming system for large open worlds with chunk-based
loading and unloading. Manages spatial partitioning, LOD transitions,
and asynchronous asset loading to enable seamless open-world experiences.
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


class ChunkState(str, Enum):
    """Loading state of a world chunk."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    UNLOADING = "unloading"
    FROZEN = "frozen"
    ERROR = "error"


class DetailLevel(str, Enum):
    """Level of detail for world chunks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    CINEMATIC = "cinematic"


class StreamingStrategy(str, Enum):
    """Strategy for world streaming."""
    RADIUS_BASED = "radius_based"
    FRUSTUM_BASED = "frustum_based"
    PRIORITY_QUEUE = "priority_queue"
    PREDICTIVE = "predictive"
    HYBRID = "hybrid"


class LoadPriority(str, Enum):
    """Priority level for chunk loading."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class WorldChunk:
    """A spatial chunk in the streaming world."""
    chunk_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    grid_x: int = 0
    grid_y: int = 0
    world_x: float = 0.0
    world_y: float = 0.0
    chunk_size: float = 256.0
    state: ChunkState = ChunkState.UNLOADED
    detail_level: DetailLevel = DetailLevel.HIGH
    priority: LoadPriority = LoadPriority.NORMAL
    entity_count: int = 0
    memory_usage_bytes: int = 0
    load_time_ms: float = 0.0
    last_accessed: float = field(default_factory=_time_module.time)
    distance_to_camera: float = float("inf")
    contained_biomes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "world_x": self.world_x,
            "world_y": self.world_y,
            "chunk_size": self.chunk_size,
            "state": self.state.value,
            "detail_level": self.detail_level.value,
            "priority": self.priority.value,
            "entity_count": self.entity_count,
            "memory_usage_bytes": self.memory_usage_bytes,
            "load_time_ms": self.load_time_ms,
            "distance_to_camera": (
                None if self.distance_to_camera == float("inf")
                else round(self.distance_to_camera, 1)
            ),
            "contained_biomes": self.contained_biomes,
            "tags": self.tags,
        }


@dataclass
class StreamingRegion:
    """A named region composed of multiple chunks."""
    region_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Unnamed Region"
    chunk_ids: List[str] = field(default_factory=list)
    center_x: float = 0.0
    center_y: float = 0.0
    radius: float = 500.0
    is_active: bool = False
    priority: LoadPriority = LoadPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "name": self.name,
            "chunk_ids": self.chunk_ids,
            "chunk_count": len(self.chunk_ids),
            "center_x": self.center_x,
            "center_y": self.center_y,
            "radius": self.radius,
            "is_active": self.is_active,
            "priority": self.priority.value,
        }


@dataclass
class StreamingConfig:
    """Configuration for the world streaming system."""
    chunk_size: float = 256.0
    load_radius: float = 768.0
    unload_radius: float = 1024.0
    max_loaded_chunks: int = 64
    max_concurrent_loads: int = 4
    max_memory_mb: int = 512
    preload_threshold: float = 0.7
    detail_distance_low: float = 768.0
    detail_distance_medium: float = 512.0
    detail_distance_high: float = 256.0
    detail_distance_ultra: float = 128.0
    strategy: StreamingStrategy = StreamingStrategy.HYBRID
    freeze_dormant_after_s: float = 300.0
    enable_preloading: bool = True
    enable_async_loading: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_size": self.chunk_size,
            "load_radius": self.load_radius,
            "unload_radius": self.unload_radius,
            "max_loaded_chunks": self.max_loaded_chunks,
            "max_concurrent_loads": self.max_concurrent_loads,
            "max_memory_mb": self.max_memory_mb,
            "preload_threshold": self.preload_threshold,
            "detail_distances": {
                "low": self.detail_distance_low,
                "medium": self.detail_distance_medium,
                "high": self.detail_distance_high,
                "ultra": self.detail_distance_ultra,
            },
            "strategy": self.strategy.value,
            "freeze_dormant_after_s": self.freeze_dormant_after_s,
            "enable_preloading": self.enable_preloading,
            "enable_async_loading": self.enable_async_loading,
        }


# ---------------------------------------------------------------------------
# Engine World Streamer
# ---------------------------------------------------------------------------


class EngineWorldStreamer:
    """
    Advanced world streaming system for large open worlds.

    Manages spatial partitioning into loadable chunks, determines which
    chunks to load based on camera proximity and priority, and handles
    LOD transitions for optimal performance.
    """

    _instance: Optional["EngineWorldStreamer"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EngineWorldStreamer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineWorldStreamer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._config = StreamingConfig()
        self._chunks: Dict[str, WorldChunk] = {}
        self._regions: Dict[str, StreamingRegion] = {}
        self._camera_x: float = 0.0
        self._camera_y: float = 0.0
        self._total_memory_used: int = 0
        self._total_chunks_loaded: int = 0
        self._total_chunks_created: int = 0
        self._load_queue: List[Tuple[str, LoadPriority]] = []
        self._unload_queue: List[str] = []
        self._load_operations_in_flight: int = 0
        self._streaming_active: bool = False
        self._tick_count: int = 0

        # Precomputed spatial index
        self._spatial_index: Dict[Tuple[int, int], str] = {}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(self, **kwargs) -> StreamingConfig:
        """Update streaming configuration."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
            return self._config

    def get_config(self) -> StreamingConfig:
        """Get current configuration."""
        return self._config

    # ------------------------------------------------------------------
    # Chunk Management
    # ------------------------------------------------------------------

    def create_chunk(
        self,
        grid_x: int = 0,
        grid_y: int = 0,
        priority: LoadPriority = LoadPriority.NORMAL,
        tags: Optional[List[str]] = None,
    ) -> WorldChunk:
        """Create a new world chunk at the specified grid position."""
        with self._lock:
            key = (grid_x, grid_y)
            existing_id = self._spatial_index.get(key)
            if existing_id and existing_id in self._chunks:
                return self._chunks[existing_id]

            chunk = WorldChunk(
                grid_x=grid_x,
                grid_y=grid_y,
                world_x=grid_x * self._config.chunk_size,
                world_y=grid_y * self._config.chunk_size,
                chunk_size=self._config.chunk_size,
                priority=priority,
                tags=tags or [],
            )
            self._chunks[chunk.chunk_id] = chunk
            self._spatial_index[key] = chunk.chunk_id
            self._total_chunks_created += 1
            return chunk

    def get_chunk(self, chunk_id: str) -> Optional[WorldChunk]:
        """Get a chunk by ID."""
        return self._chunks.get(chunk_id)

    def get_chunk_at(self, grid_x: int, grid_y: int) -> Optional[WorldChunk]:
        """Get chunk at grid position."""
        chunk_id = self._spatial_index.get((grid_x, grid_y))
        if chunk_id:
            return self._chunks.get(chunk_id)
        return None

    def get_chunk_at_world(self, world_x: float, world_y: float) -> Optional[WorldChunk]:
        """Get chunk containing world coordinates."""
        grid_x = int(world_x // self._config.chunk_size)
        grid_y = int(world_y // self._config.chunk_size)
        return self.get_chunk_at(grid_x, grid_y)

    def request_chunk_load(
        self, chunk_id: str, priority: LoadPriority = LoadPriority.NORMAL
    ) -> bool:
        """Request loading of a chunk."""
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                return False
            if chunk.state in (ChunkState.LOADED, ChunkState.ACTIVE, ChunkState.LOADING):
                return False
            chunk.priority = priority
            chunk.state = ChunkState.LOADING
            self._load_queue.append((chunk_id, priority))
            return True

    def request_chunk_unload(self, chunk_id: str) -> bool:
        """Request unloading of a chunk."""
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                return False
            if chunk.state in (ChunkState.UNLOADED, ChunkState.UNLOADING):
                return False
            chunk.state = ChunkState.UNLOADING
            self._unload_queue.append(chunk_id)
            return True

    def set_chunk_detail(
        self, chunk_id: str, detail: DetailLevel
    ) -> bool:
        """Set the detail level for a chunk."""
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                return False
            chunk.detail_level = detail
            return True

    # ------------------------------------------------------------------
    # Spatial Indexing
    # ------------------------------------------------------------------

    def generate_world_grid(
        self,
        center_x: float = 0.0,
        center_y: float = 0.0,
        grid_radius: int = 5,
        priority: LoadPriority = LoadPriority.NORMAL,
    ) -> List[WorldChunk]:
        """Generate a grid of chunks around a center point."""
        center_gx = int(center_x // self._config.chunk_size)
        center_gy = int(center_y // self._config.chunk_size)

        chunks = []
        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                chunk = self.create_chunk(
                    grid_x=center_gx + dx,
                    grid_y=center_gy + dy,
                    priority=priority,
                )
                chunks.append(chunk)
        return chunks

    # ------------------------------------------------------------------
    # Region Management
    # ------------------------------------------------------------------

    def create_region(
        self,
        name: str = "Unnamed Region",
        center_x: float = 0.0,
        center_y: float = 0.0,
        radius: float = 500.0,
        priority: LoadPriority = LoadPriority.NORMAL,
    ) -> StreamingRegion:
        """Create a named region and generate its chunks."""
        with self._lock:
            region = StreamingRegion(
                name=name,
                center_x=center_x,
                center_y=center_y,
                radius=radius,
                priority=priority,
            )
            self._regions[region.region_id] = region
            return region

    def activate_region(self, region_id: str) -> bool:
        """Activate a region and begin loading its chunks."""
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return False

            region.is_active = True
            for chunk_id in region._chunk_ids:
                self.request_chunk_load(chunk_id, region.priority)
            return True

    def deactivate_region(self, region_id: str) -> bool:
        """Deactivate a region and queue its chunks for unloading."""
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return False

            region.is_active = False
            for chunk_id in region._chunk_ids:
                self.request_chunk_unload(chunk_id)
            return True

    # ------------------------------------------------------------------
    # Core Streaming Tick
    # ------------------------------------------------------------------

    def set_camera_position(self, x: float, y: float) -> None:
        """Update the camera position for streaming calculations."""
        with self._lock:
            self._camera_x = x
            self._camera_y = y

            # Update distances for all chunks
            for chunk in self._chunks.values():
                cx = chunk.world_x + chunk.chunk_size / 2
                cy = chunk.world_y + chunk.chunk_size / 2
                chunk.distance_to_camera = math.sqrt(
                    (cx - x) ** 2 + (cy - y) ** 2
                )

    def tick(self, delta_time: float = 0.016) -> Dict[str, Any]:
        """
        Advance the streaming system. Processes load/unload queues,
        updates LOD levels, and manages memory budget.
        """
        with self._lock:
            self._tick_count += 1
            changes: Dict[str, Any] = {
                "chunks_loaded": 0,
                "chunks_unloaded": 0,
                "detail_transitions": 0,
            }

            # Process unload queue first to free memory
            unloaded_count = 0
            while self._unload_queue and unloaded_count < self._config.max_concurrent_loads:
                chunk_id = self._unload_queue.pop(0)
                chunk = self._chunks.get(chunk_id)
                if chunk:
                    chunk.state = ChunkState.UNLOADED
                    self._total_chunks_loaded = max(0, self._total_chunks_loaded - 1)
                    self._total_memory_used = max(0, self._total_memory_used - chunk.memory_usage_bytes)
                    chunk.memory_usage_bytes = 0
                    unloaded_count += 1
            changes["chunks_unloaded"] = unloaded_count

            # Process load queue sorted by priority
            if self._load_operations_in_flight < self._config.max_concurrent_loads:
                self._load_queue.sort(
                    key=lambda x: (
                        0 if x[1] == LoadPriority.CRITICAL else
                        1 if x[1] == LoadPriority.HIGH else
                        2 if x[1] == LoadPriority.NORMAL else
                        3 if x[1] == LoadPriority.LOW else 4
                    )
                )
                loaded_count = 0
                loaded_ids = []
                while (
                    self._load_queue
                    and loaded_count < self._config.max_concurrent_loads
                    and self._total_chunks_loaded < self._config.max_loaded_chunks
                ):
                    chunk_id, _ = self._load_queue.pop(0)
                    chunk = self._chunks.get(chunk_id)
                    if chunk and chunk.state == ChunkState.LOADING:
                        chunk.state = ChunkState.LOADED
                        chunk.load_time_ms = delta_time * 1000
                        chunk.memory_usage_bytes = int(
                            chunk.chunk_size * chunk.chunk_size * 64
                        )
                        chunk.last_accessed = _time_module.time()
                        self._total_chunks_loaded += 1
                        self._total_memory_used += chunk.memory_usage_bytes
                        loaded_count += 1
                        loaded_ids.append(chunk_id)
                changes["chunks_loaded"] = loaded_count

            # Update detail levels based on distance
            detail_changes = 0
            for chunk in self._chunks.values():
                if chunk.state not in (ChunkState.LOADED, ChunkState.ACTIVE):
                    continue

                dist = chunk.distance_to_camera
                if dist == float("inf"):
                    continue

                new_detail = self._compute_detail_level(dist)
                if chunk.detail_level != new_detail:
                    chunk.detail_level = new_detail
                    detail_changes += 1
            changes["detail_transitions"] = detail_changes

            # Freeze dormant chunks
            now = _time_module.time()
            for chunk in self._chunks.values():
                if chunk.state == ChunkState.LOADED:
                    dormant_time = now - chunk.last_accessed
                    if dormant_time > self._config.freeze_dormant_after_s:
                        chunk.state = ChunkState.FROZEN

            return changes

    def _compute_detail_level(self, distance: float) -> DetailLevel:
        """Compute appropriate detail level based on distance."""
        if distance <= self._config.detail_distance_ultra:
            return DetailLevel.ULTRA
        elif distance <= self._config.detail_distance_high:
            return DetailLevel.HIGH
        elif distance <= self._config.detail_distance_medium:
            return DetailLevel.MEDIUM
        elif distance <= self._config.detail_distance_low:
            return DetailLevel.LOW
        else:
            return DetailLevel.LOW

    def get_chunks_in_radius(
        self, center_x: float, center_y: float, radius: float
    ) -> List[WorldChunk]:
        """Get all chunks within a radius of a point."""
        result = []
        for chunk in self._chunks.values():
            cx = chunk.world_x + chunk.chunk_size / 2
            cy = chunk.world_y + chunk.chunk_size / 2
            dist = math.sqrt((cx - center_x) ** 2 + (cy - center_y) ** 2)
            if dist <= radius:
                result.append(chunk)
        return result

    # ------------------------------------------------------------------
    # Streaming Control
    # ------------------------------------------------------------------

    def start_streaming(self) -> None:
        """Activate the streaming system."""
        with self._lock:
            self._streaming_active = True

    def stop_streaming(self) -> None:
        """Deactivate the streaming system."""
        with self._lock:
            self._streaming_active = False
            self._load_queue.clear()
            self._unload_queue.clear()
            self._load_operations_in_flight = 0

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_all_chunks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all chunks as dictionaries."""
        chunks = list(self._chunks.values())[:limit]
        return [c.to_dict() for c in chunks]

    def get_all_regions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all regions as dictionaries."""
        regions = list(self._regions.values())[:limit]
        return [r.to_dict() for r in regions]

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        state_counts = {}
        for chunk in self._chunks.values():
            s = chunk.state.value
            state_counts[s] = state_counts.get(s, 0) + 1

        detail_counts = {}
        for chunk in self._chunks.values():
            if chunk.state in (ChunkState.LOADED, ChunkState.ACTIVE):
                d = chunk.detail_level.value
                detail_counts[d] = detail_counts.get(d, 0) + 1

        return {
            "total_chunks": len(self._chunks),
            "total_regions": len(self._regions),
            "total_created": self._total_chunks_created,
            "total_loaded": self._total_chunks_loaded,
            "total_memory_bytes": self._total_memory_used,
            "total_memory_mb": round(self._total_memory_used / (1024 * 1024), 2),
            "state_distribution": state_counts,
            "detail_distribution": detail_counts,
            "load_queue_size": len(self._load_queue),
            "unload_queue_size": len(self._unload_queue),
            "loads_in_flight": self._load_operations_in_flight,
            "camera_position": (self._camera_x, self._camera_y),
            "streaming_active": self._streaming_active,
            "tick_count": self._tick_count,
            "config": self._config.to_dict(),
        }

    def get_loaded_chunks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get currently loaded chunks."""
        loaded = [
            c for c in self._chunks.values()
            if c.state in (ChunkState.LOADED, ChunkState.ACTIVE)
        ]
        return [c.to_dict() for c in loaded[:limit]]


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_world_streamer() -> EngineWorldStreamer:
    """Get or create the singleton EngineWorldStreamer instance."""
    return EngineWorldStreamer.get_instance()