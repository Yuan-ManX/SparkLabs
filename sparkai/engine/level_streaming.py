"""
SparkLabs Engine - Level Streaming System

Dynamic level loading and unloading for seamless AI-native
game worlds. Manages spatial partitioning of game levels
into streamable chunks with asynchronous loading queues,
priority-based scheduling, distance culling, and memory
budget enforcement. Enables large open worlds without
loading screens through progressive content delivery.

Architecture:
  LevelStreamingSystem
    |-- ChunkManager (spatial grid partitioning of world)
    |-- LoadQueue (priority-ordered async chunk loading)
    |-- UnloadManager (LRU-based chunk eviction)
    |-- DistanceCuller (view-frustum and distance-based culling)
    |-- MemoryBudgeter (enforce max loaded chunk count)
    |-- PlayerTracker (focal point for streaming radius)

Chunk States:
  - UNLOADED: not in memory
  - LOADING: async transfer in progress
  - LOADED: fully available for rendering
  - UNLOADING: being evicted from memory
  - FAILED: loading error occurred
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ChunkState(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    FAILED = "failed"


class ChunkPriority(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    PRELOAD = 1


@dataclass
class ChunkDefinition:
    chunk_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    grid_x: int = 0
    grid_y: int = 0
    world_center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    world_size: Tuple[float, float, float] = (64.0, 64.0, 64.0)
    asset_count: int = 0
    estimated_memory_mb: float = 0.0
    tags: List[str] = field(default_factory=list)

    @property
    def bounds_min(self) -> Tuple[float, float, float]:
        cx, cy, cz = self.world_center
        sx, sy, sz = self.world_size
        return (cx - sx/2, cy - sy/2, cz - sz/2)

    @property
    def bounds_max(self) -> Tuple[float, float, float]:
        cx, cy, cz = self.world_center
        sx, sy, sz = self.world_size
        return (cx + sx/2, cy + sy/2, cz + sz/2)

    def contains_point(self, point: Tuple[float, float, float]) -> bool:
        mn = self.bounds_min
        mx = self.bounds_max
        return (mn[0] <= point[0] <= mx[0] and
                mn[1] <= point[1] <= mx[1] and
                mn[2] <= point[2] <= mx[2])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "grid": (self.grid_x, self.grid_y),
            "center": list(self.world_center),
            "size": list(self.world_size),
            "memory_mb": self.estimated_memory_mb,
        }


@dataclass
class LoadedChunk:
    chunk_id: str = ""
    state: ChunkState = ChunkState.LOADED
    priority: ChunkPriority = ChunkPriority.MEDIUM
    load_progress: float = 1.0
    last_accessed: float = field(default_factory=time.time)
    loaded_at: float = field(default_factory=time.time)
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "state": self.state.value,
            "priority": self.priority.name,
            "progress": round(self.load_progress, 2),
        }


class LevelStreamingSystem:
    _instance: Optional[LevelStreamingSystem] = None

    @classmethod
    def get_instance(cls) -> LevelStreamingSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._chunks: Dict[str, ChunkDefinition] = {}
        self._loaded_chunks: Dict[str, LoadedChunk] = {}
        self._streaming_radius: float = 128.0
        self._max_loaded_chunks: int = 64
        self._max_loaded_memory_mb: float = 512.0
        self._player_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._loading_queue: List[Tuple[str, float]] = []
        self._total_chunks: int = 0
        self._load_events: int = 0
        self._unload_events: int = 0

    def define_chunk(self, grid_x: int, grid_y: int, world_center: Tuple[float, float, float],
                     world_size: Tuple[float, float, float] = (64.0, 64.0, 64.0),
                     estimated_memory_mb: float = 5.0, tags: Optional[List[str]] = None) -> ChunkDefinition:
        chunk = ChunkDefinition(
            grid_x=grid_x, grid_y=grid_y,
            world_center=world_center, world_size=world_size,
            estimated_memory_mb=estimated_memory_mb,
            tags=tags or [],
        )
        self._chunks[chunk.chunk_id] = chunk
        self._total_chunks += 1
        return chunk

    def set_player_position(self, position: Tuple[float, float, float]):
        self._player_position = position

    def set_streaming_radius(self, radius: float):
        self._streaming_radius = max(16.0, radius)

    def get_chunks_in_range(self, position: Optional[Tuple[float, float, float]] = None,
                            radius: Optional[float] = None) -> List[ChunkDefinition]:
        pos = position or self._player_position
        r = radius or self._streaming_radius
        r_sq = r * r

        in_range = []
        for chunk in self._chunks.values():
            cx, cy, cz = chunk.world_center
            px, py, pz = pos
            dist_sq = (cx - px) ** 2 + (cz - pz) ** 2
            if dist_sq <= r_sq:
                in_range.append(chunk)
        return in_range

    def _compute_chunk_distance(self, chunk_id: str) -> float:
        chunk = self._chunks.get(chunk_id)
        if chunk is None:
            return float("inf")
        cx, cy, cz = chunk.world_center
        px, py, pz = self._player_position
        return math.sqrt((cx - px) ** 2 + (cz - pz) ** 2)

    def _compute_priority(self, chunk_id: str) -> ChunkPriority:
        dist = self._compute_chunk_distance(chunk_id)
        if dist > self._streaming_radius * 1.2:
            return ChunkPriority.PRELOAD
        ratio = dist / self._streaming_radius if self._streaming_radius > 0 else 1.0
        if ratio < 0.3:
            return ChunkPriority.CRITICAL
        elif ratio < 0.6:
            return ChunkPriority.HIGH
        elif ratio < 0.9:
            return ChunkPriority.MEDIUM
        return ChunkPriority.LOW

    def update(self, delta_time: float = 0.0):
        in_range = self.get_chunks_in_range()
        in_range_ids = {c.chunk_id for c in in_range}

        for chunk in in_range:
            if chunk.chunk_id not in self._loaded_chunks:
                priority = self._compute_priority(chunk.chunk_id)
                self._loaded_chunks[chunk.chunk_id] = LoadedChunk(
                    chunk_id=chunk.chunk_id,
                    state=ChunkState.LOADING,
                    priority=priority,
                    load_progress=0.0,
                )
                self._load_events += 1

        for chunk in in_range:
            lc = self._loaded_chunks.get(chunk.chunk_id)
            if lc and lc.state == ChunkState.LOADING:
                lc.load_progress = min(1.0, lc.load_progress + delta_time * 2.0)
                if lc.load_progress >= 1.0:
                    lc.state = ChunkState.LOADED
                    lc.loaded_at = time.time()

        for loaded_id in list(self._loaded_chunks.keys()):
            if loaded_id not in in_range_ids:
                lc = self._loaded_chunks[loaded_id]
                if lc.state == ChunkState.LOADED:
                    lc.state = ChunkState.UNLOADING
                    lc.load_progress = 1.0
                elif lc.state == ChunkState.UNLOADING:
                    lc.load_progress = max(0.0, lc.load_progress - delta_time * 2.0)
                    if lc.load_progress <= 0.0:
                        del self._loaded_chunks[loaded_id]
                        self._unload_events += 1

        self._enforce_memory_limit()

    def _enforce_memory_limit(self):
        total_mem = 0.0
        for chunk_id, lc in self._loaded_chunks.items():
            chunk = self._chunks.get(chunk_id)
            if chunk and lc.state == ChunkState.LOADED:
                total_mem += chunk.estimated_memory_mb

        if total_mem > self._max_loaded_memory_mb or len([
            c for c in self._loaded_chunks.values() if c.state == ChunkState.LOADED
        ]) > self._max_loaded_chunks:
            candidates = sorted(
                [(cid, lc) for cid, lc in self._loaded_chunks.items() if lc.state == ChunkState.LOADED],
                key=lambda x: (x[1].priority.score if isinstance(x[1].priority, ChunkPriority) else x[1].priority.value, x[1].last_accessed)
            )
            for chunk_id, lc in candidates[:5]:
                lc.state = ChunkState.UNLOADING
                lc.load_progress = 1.0

    def get_loading_progress(self) -> float:
        loading = [lc for lc in self._loaded_chunks.values() if lc.state == ChunkState.LOADING]
        if not loading:
            return 1.0
        return sum(lc.load_progress for lc in loading) / len(loading)

    def get_loaded_chunks_list(self) -> List[Dict[str, Any]]:
        return [lc.to_dict() for lc in self._loaded_chunks.values()
                if lc.state in (ChunkState.LOADED, ChunkState.LOADING)]

    def get_current_memory_usage_mb(self) -> float:
        total = 0.0
        for chunk_id, lc in self._loaded_chunks.items():
            if lc.state == ChunkState.LOADED:
                chunk = self._chunks.get(chunk_id)
                if chunk:
                    total += chunk.estimated_memory_mb
        return total

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_chunks": self._total_chunks,
            "loaded_chunks": len([c for c in self._loaded_chunks.values() if c.state == ChunkState.LOADED]),
            "loading_chunks": len([c for c in self._loaded_chunks.values() if c.state == ChunkState.LOADING]),
            "load_events": self._load_events,
            "unload_events": self._unload_events,
            "streaming_radius": self._streaming_radius,
            "memory_usage_mb": round(self.get_current_memory_usage_mb(), 1),
            "loading_progress": round(self.get_loading_progress(), 2),
        }


def get_level_streaming() -> LevelStreamingSystem:
    return LevelStreamingSystem.get_instance()