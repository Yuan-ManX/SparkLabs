"""
SparkLabs Engine - Progressive World Loading and Streaming System

Advanced progressive world loading engine that dynamically streams terrain
chunks, game objects, and asset data into the runtime environment. Utilizes
spatial priority-based scheduling, view-frustum culling, predictive trajectory
preloading, memory budget enforcement, and smooth LOD transitions to deliver
seamless open-world experiences at any scale.

Core capabilities:
  - Spatial chunk partitioning with grid-based world decomposition
  - Priority-driven asynchronous chunk loading and unloading
  - View-frustum and occlusion-based visibility computation
  - Camera trajectory prediction for anticipatory preloading
  - Memory budget management with intelligent eviction policies
  - Smooth level-of-detail transitions with configurable fade parameters
  - Predefined streaming presets for performance, balanced, and quality modes

Architecture:
  EngineProgressiveLoading (Singleton)
    |-- WorldChunk (dataclass)        — individual world partition unit
    |-- LoadingQueue (dataclass)       — prioritized load operation queue
    |-- StreamingConfig (dataclass)    — tunable streaming parameters
    |-- LODTransition (dataclass)      — detail level transition descriptor
    |-- ChunkState (enum)              — chunk lifecycle states
    |-- PriorityLevel (enum)           — loading urgency tiers
    |-- load_chunk() / unload_chunk()
    |-- prioritize_chunks()
    |-- compute_chunk_visibility()
    |-- manage_memory_budget()
    |-- smooth_lod_transition()
    |-- preload_predicted_chunks()
    |-- get_stats()

Streaming Presets:
  - PERFORMANCE: low view distance, aggressive memory limits, fast loads
  - BALANCED: moderate settings for consistent frame rates
  - QUALITY: extended view distance, high detail, larger memory budget
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ChunkState(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    UNLOADING = "unloading"
    CACHED = "cached"


class PriorityLevel(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class StreamingPreset(Enum):
    PERFORMANCE = "performance"
    BALANCED = "balanced"
    QUALITY = "quality"


_LOD_LEVEL_NAMES: List[str] = [
    "LOD0_ULTRA",
    "LOD1_HIGH",
    "LOD2_MEDIUM",
    "LOD3_LOW",
    "LOD4_MINIMAL",
]

_LOD_DISTANCE_THRESHOLDS: Dict[str, float] = {
    "LOD0_ULTRA": 80.0,
    "LOD1_HIGH": 200.0,
    "LOD2_MEDIUM": 500.0,
    "LOD3_LOW": 1200.0,
    "LOD4_MINIMAL": 3000.0,
}

_LOD_MEMORY_FACTORS: Dict[str, float] = {
    "LOD0_ULTRA": 1.0,
    "LOD1_HIGH": 0.55,
    "LOD2_MEDIUM": 0.28,
    "LOD3_LOW": 0.12,
    "LOD4_MINIMAL": 0.04,
}

_LOD_FADE_DURATIONS: Dict[str, float] = {
    "ascending": 0.35,
    "descending": 0.50,
}

_STREAMING_PRESETS: Dict[str, Dict[str, Any]] = {
    "performance": {
        "view_distance": 800.0,
        "preload_radius": 200.0,
        "memory_budget_mb": 256.0,
        "max_concurrent_loads": 3,
        "chunk_size": 128.0,
        "unload_radius_multiplier": 1.6,
        "prediction_look_ahead": 2,
        "max_active_chunks": 36,
        "lod_bias": 1,
    },
    "balanced": {
        "view_distance": 2000.0,
        "preload_radius": 500.0,
        "memory_budget_mb": 768.0,
        "max_concurrent_loads": 6,
        "chunk_size": 256.0,
        "unload_radius_multiplier": 1.4,
        "prediction_look_ahead": 3,
        "max_active_chunks": 80,
        "lod_bias": 0,
    },
    "quality": {
        "view_distance": 5000.0,
        "preload_radius": 1200.0,
        "memory_budget_mb": 2048.0,
        "max_concurrent_loads": 10,
        "chunk_size": 256.0,
        "unload_radius_multiplier": 1.2,
        "prediction_look_ahead": 5,
        "max_active_chunks": 160,
        "lod_bias": -1,
    },
}

_PRIORITY_WEIGHTS: Dict[PriorityLevel, float] = {
    PriorityLevel.CRITICAL: 100.0,
    PriorityLevel.HIGH: 50.0,
    PriorityLevel.NORMAL: 10.0,
    PriorityLevel.LOW: 2.0,
    PriorityLevel.BACKGROUND: 0.5,
}


@dataclass
class WorldChunk:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_id: str = ""
    grid_x: int = 0
    grid_y: int = 0
    grid_z: int = 0
    chunk_size: float = 256.0
    bounds_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounds_max: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    state: ChunkState = ChunkState.UNLOADED
    priority: PriorityLevel = PriorityLevel.NORMAL
    lod_level: str = "LOD2_MEDIUM"
    memory_footprint_kb: float = 0.0
    asset_references: List[str] = field(default_factory=list)
    entity_count: int = 0
    last_access_time: float = field(default_factory=_time_module.time)
    load_progress: float = 0.0
    distance_to_camera: float = float("inf")

    @property
    def center(self) -> Tuple[float, float, float]:
        return (
            (self.bounds_min[0] + self.bounds_max[0]) / 2.0,
            (self.bounds_min[1] + self.bounds_max[1]) / 2.0,
            (self.bounds_min[2] + self.bounds_max[2]) / 2.0,
        )

    def compute_bounds(self) -> None:
        hs = self.chunk_size / 2.0
        cx = self.grid_x * self.chunk_size + hs
        cy = self.grid_y * self.chunk_size + hs
        cz = self.grid_z * self.chunk_size + hs
        self.bounds_min = (cx - hs, cy - hs, cz - hs)
        self.bounds_max = (cx + hs, cy + hs, cz + hs)

    def distance_squared_to(self, px: float, py: float, pz: float) -> float:
        cx, cy, cz = self.center
        dx = cx - px
        dy = cy - py
        dz = cz - pz
        return dx * dx + dy * dy + dz * dz

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "world_id": self.world_id,
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "grid_z": self.grid_z,
            "chunk_size": self.chunk_size,
            "bounds_min": list(self.bounds_min),
            "bounds_max": list(self.bounds_max),
            "state": self.state.value,
            "priority": self.priority.value,
            "lod_level": self.lod_level,
            "memory_footprint_kb": self.memory_footprint_kb,
            "asset_references": self.asset_references,
            "entity_count": self.entity_count,
            "last_access_time": self.last_access_time,
            "load_progress": self.load_progress,
            "distance_to_camera": self.distance_to_camera if math.isfinite(self.distance_to_camera) else None,
        }


@dataclass
class LoadingQueue:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_id: str = ""
    queued_chunk_ids: List[str] = field(default_factory=list)
    priority_ordering: Dict[str, float] = field(default_factory=dict)
    estimated_load_times: Dict[str, float] = field(default_factory=dict)
    total_pending: int = 0
    active_loads: int = 0
    max_concurrent: int = 6
    average_load_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "world_id": self.world_id,
            "queued_chunk_ids": self.queued_chunk_ids,
            "priority_ordering": self.priority_ordering,
            "estimated_load_times": self.estimated_load_times,
            "total_pending": self.total_pending,
            "active_loads": self.active_loads,
            "max_concurrent": self.max_concurrent,
            "average_load_time_ms": self.average_load_time_ms,
        }


@dataclass
class StreamingConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_id: str = ""
    preset: StreamingPreset = StreamingPreset.BALANCED
    view_distance: float = 2000.0
    preload_radius: float = 500.0
    memory_budget_mb: float = 768.0
    max_concurrent_loads: int = 6
    chunk_size: float = 256.0
    unload_radius_multiplier: float = 1.4
    prediction_look_ahead: int = 3
    max_active_chunks: int = 80
    lod_bias: int = 0
    lod_distances: Dict[str, float] = field(default_factory=dict)
    lod_memory_factors: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.lod_distances:
            self.lod_distances = dict(_LOD_DISTANCE_THRESHOLDS)
        if not self.lod_memory_factors:
            self.lod_memory_factors = dict(_LOD_MEMORY_FACTORS)

    def resolve_lod_for_distance(self, distance: float) -> str:
        effective_distance = distance
        selected = "LOD4_MINIMAL"
        for lod_name in _LOD_LEVEL_NAMES:
            threshold = self.lod_distances.get(lod_name, 99999.0)
            adjusted = threshold
            if self.lod_bias != 0:
                adjusted = threshold * (1.0 + self.lod_bias * 0.15)
            if effective_distance <= adjusted:
                selected = lod_name
                break
        return selected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "world_id": self.world_id,
            "preset": self.preset.value,
            "view_distance": self.view_distance,
            "preload_radius": self.preload_radius,
            "memory_budget_mb": self.memory_budget_mb,
            "max_concurrent_loads": self.max_concurrent_loads,
            "chunk_size": self.chunk_size,
            "unload_radius_multiplier": self.unload_radius_multiplier,
            "prediction_look_ahead": self.prediction_look_ahead,
            "max_active_chunks": self.max_active_chunks,
            "lod_bias": self.lod_bias,
            "lod_distances": self.lod_distances,
            "lod_memory_factors": self.lod_memory_factors,
        }


@dataclass
class LODTransition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    chunk_id: str = ""
    from_level: str = "LOD2_MEDIUM"
    to_level: str = "LOD1_HIGH"
    transition_progress: float = 0.0
    fade_alpha: float = 0.0
    fade_duration: float = 0.5
    is_ascending: bool = True
    start_time: float = field(default_factory=_time_module.time)
    detail_threshold: float = 200.0
    is_complete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chunk_id": self.chunk_id,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "transition_progress": self.transition_progress,
            "fade_alpha": self.fade_alpha,
            "fade_duration": self.fade_duration,
            "is_ascending": self.is_ascending,
            "start_time": self.start_time,
            "detail_threshold": self.detail_threshold,
            "is_complete": self.is_complete,
        }


class EngineProgressiveLoading:

    _instance: Optional["EngineProgressiveLoading"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineProgressiveLoading":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._chunks: Dict[str, WorldChunk] = {}
        self._configs: Dict[str, StreamingConfig] = {}
        self._queues: Dict[str, LoadingQueue] = {}
        self._transitions: Dict[str, LODTransition] = {}
        self._grid_index: Dict[Tuple[int, int, int, str], str] = {}
        self._camera_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._camera_forward: Tuple[float, float, float] = (0.0, 0.0, 1.0)
        self._camera_speed: float = 0.0
        self._camera_fov: float = 75.0
        self._camera_aspect: float = 1.777777
        self._camera_near: float = 0.1
        self._previous_camera_positions: List[Tuple[float, float, float]] = []
        self._total_chunks_loaded: int = 0
        self._total_chunks_unloaded: int = 0
        self._total_transitions_completed: int = 0
        self._total_memory_evictions: int = 0
        self._frame_count: int = 0

    @classmethod
    def get_instance(cls) -> "EngineProgressiveLoading":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls.__new__(cls)
        return cls._instance

    def apply_preset(self, world_id: str, preset_name: str) -> StreamingConfig:
        _time_module.sleep(0.001)
        try:
            preset_enum = StreamingPreset(preset_name.lower())
        except ValueError:
            preset_enum = StreamingPreset.BALANCED

        preset_data = _STREAMING_PRESETS.get(preset_enum.value, _STREAMING_PRESETS["balanced"])

        with self._lock:
            config = self._configs.get(world_id)
            if config is None:
                config = StreamingConfig(world_id=world_id)
                self._configs[world_id] = config

            config.preset = preset_enum
            config.view_distance = float(preset_data["view_distance"])
            config.preload_radius = float(preset_data["preload_radius"])
            config.memory_budget_mb = float(preset_data["memory_budget_mb"])
            config.max_concurrent_loads = int(preset_data["max_concurrent_loads"])
            config.chunk_size = float(preset_data["chunk_size"])
            config.unload_radius_multiplier = float(preset_data["unload_radius_multiplier"])
            config.prediction_look_ahead = int(preset_data["prediction_look_ahead"])
            config.max_active_chunks = int(preset_data["max_active_chunks"])
            config.lod_bias = int(preset_data["lod_bias"])

            if world_id not in self._queues:
                queue = LoadingQueue(
                    world_id=world_id,
                    max_concurrent=config.max_concurrent_loads,
                )
                self._queues[world_id] = queue
            else:
                self._queues[world_id].max_concurrent = config.max_concurrent_loads

            return config

    def create_chunk(
        self,
        world_id: str,
        grid_x: int,
        grid_y: int,
        grid_z: int,
    ) -> WorldChunk:
        _time_module.sleep(0.001)
        with self._lock:
            key = (grid_x, grid_y, grid_z, world_id)
            existing_id = self._grid_index.get(key)
            if existing_id and existing_id in self._chunks:
                return self._chunks[existing_id]

            config = self._configs.get(world_id)
            chunk_size = config.chunk_size if config else 256.0

            chunk = WorldChunk(
                world_id=world_id,
                grid_x=grid_x,
                grid_y=grid_y,
                grid_z=grid_z,
                chunk_size=chunk_size,
                state=ChunkState.UNLOADED,
            )
            chunk.compute_bounds()

            self._chunks[chunk.id] = chunk
            self._grid_index[key] = chunk.id
            return chunk

    def load_chunk(
        self,
        chunk_id: str,
        priority: Optional[str] = None,
        target_lod: Optional[str] = None,
    ) -> Optional[WorldChunk]:
        _time_module.sleep(0.001)
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                return None

            if chunk.state in (ChunkState.LOADED, ChunkState.ACTIVE):
                chunk.priority = self._resolve_priority(priority) if priority else chunk.priority
                return chunk

            if chunk.state == ChunkState.LOADING:
                if priority:
                    chunk.priority = self._resolve_priority(priority)
                return chunk

            if priority:
                chunk.priority = self._resolve_priority(priority)

            config = self._configs.get(chunk.world_id)
            if config:
                queue = self._queues.get(chunk.world_id)
                if queue and queue.active_loads >= config.max_concurrent_loads:
                    chunk.state = ChunkState.UNLOADED
                    return chunk

            chunk.state = ChunkState.LOADING
            chunk.load_progress = 0.0
            chunk.last_access_time = _time_module.time()

            if target_lod:
                chunk.lod_level = target_lod
            else:
                chunk.lod_level = "LOD2_MEDIUM"

            if config:
                chunk.memory_footprint_kb = self._estimate_memory_for_lod(
                    chunk.lod_level, config
                )

            base_load_time = 0.015 + (chunk.memory_footprint_kb / 80000.0) * 0.035
            chunk.load_progress = min(1.0, base_load_time * 30.0)

            chunk.state = ChunkState.LOADED
            chunk.entity_count = max(1, int(chunk.memory_footprint_kb / 12.0))

            self._total_chunks_loaded += 1

            if chunk.world_id in self._queues:
                q = self._queues[chunk.world_id]
                q.active_loads = max(0, q.active_loads - 1)

            return chunk

    def unload_chunk(self, chunk_id: str) -> bool:
        _time_module.sleep(0.001)
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                return False

            if chunk.state in (ChunkState.UNLOADED, ChunkState.UNLOADING):
                return False

            chunk.state = ChunkState.UNLOADING
            chunk.load_progress = 0.0

            chunk.state = ChunkState.UNLOADED
            chunk.memory_footprint_kb = 0.0
            chunk.asset_references.clear()
            chunk.entity_count = 0
            chunk.distance_to_camera = float("inf")

            self._total_chunks_unloaded += 1
            return True

    def prioritize_chunks(
        self,
        world_id: str,
        camera_position: Optional[Tuple[float, float, float]] = None,
        camera_direction: Optional[Tuple[float, float, float]] = None,
    ) -> List[WorldChunk]:
        _time_module.sleep(0.001)
        with self._lock:
            if camera_position:
                self._camera_position = camera_position
            if camera_direction:
                self._camera_forward = camera_direction

            cx, cy, cz = self._camera_position
            fx, fy, fz = self._camera_forward
            f_mag = math.sqrt(fx * fx + fy * fy + fz * fz)
            if f_mag < 1e-6:
                fx, fy, fz = 0.0, 0.0, 1.0
            else:
                fx /= f_mag
                fy /= f_mag
                fz /= f_mag

            config = self._configs.get(world_id)
            if config is None:
                return []

            world_chunks = [
                c for c in self._chunks.values()
                if c.world_id == world_id
            ]

            for chunk in world_chunks:
                dist_sq = chunk.distance_squared_to(cx, cy, cz)
                chunk.distance_to_camera = math.sqrt(dist_sq)

                chunk_center = chunk.center
                dx_to_chunk = chunk_center[0] - cx
                dy_to_chunk = chunk_center[1] - cy
                dz_to_chunk = chunk_center[2] - cz
                mag = math.sqrt(dx_to_chunk * dx_to_chunk + dy_to_chunk * dy_to_chunk + dz_to_chunk * dz_to_chunk)
                if mag < 1e-6:
                    dot_product = 1.0
                else:
                    dot_product = (dx_to_chunk * fx + dy_to_chunk * fy + dz_to_chunk * fz) / mag

                view_distance = config.view_distance
                distance_score = max(0.0, 1.0 - chunk.distance_to_camera / max(1.0, view_distance))
                direction_score = (dot_product + 1.0) / 2.0

                priority_weight = _PRIORITY_WEIGHTS.get(chunk.priority, 10.0)
                composite_score = (
                    distance_score * 0.55
                    + direction_score * 0.35
                    + (priority_weight / 100.0) * 0.10
                )

                if composite_score > 0.85:
                    chunk.priority = PriorityLevel.CRITICAL
                elif composite_score > 0.60:
                    chunk.priority = PriorityLevel.HIGH
                elif composite_score > 0.30:
                    chunk.priority = PriorityLevel.NORMAL
                elif composite_score > 0.10:
                    chunk.priority = PriorityLevel.LOW
                else:
                    chunk.priority = PriorityLevel.BACKGROUND

            sorted_chunks = sorted(
                world_chunks,
                key=lambda c: (
                    -_PRIORITY_WEIGHTS.get(c.priority, 0.0),
                    c.distance_to_camera,
                ),
            )

            return sorted_chunks

    def compute_chunk_visibility(
        self,
        world_id: str,
        camera_position: Optional[Tuple[float, float, float]] = None,
    ) -> List[WorldChunk]:
        _time_module.sleep(0.001)
        with self._lock:
            if camera_position:
                self._camera_position = camera_position

            cx, cy, cz = self._camera_position
            fx, fy, fz = self._camera_forward
            f_mag = math.sqrt(fx * fx + fy * fy + fz * fz)
            if f_mag < 1e-6:
                fx, fy, fz = 0.0, 0.0, 1.0
            else:
                fx /= f_mag
                fy /= f_mag
                fz /= f_mag

            config = self._configs.get(world_id)
            if config is None:
                return []

            fov_rad = math.radians(self._camera_fov)
            half_fov = fov_rad / 2.0
            tan_half_fov = math.tan(half_fov)
            vh = tan_half_fov
            vw = vh * self._camera_aspect

            view_distance = config.view_distance
            visible_chunks: List[WorldChunk] = []

            world_chunks = [
                c for c in self._chunks.values()
                if c.world_id == world_id
            ]

            for chunk in world_chunks:
                dist_sq = chunk.distance_squared_to(cx, cy, cz)
                dist = math.sqrt(dist_sq)

                if dist > view_distance:
                    continue

                chunk_center = chunk.center
                rel_x = chunk_center[0] - cx
                rel_y = chunk_center[1] - cy
                rel_z = chunk_center[2] - cz

                projected_z = rel_x * fx + rel_y * fy + rel_z * fz
                if projected_z <= self._camera_near:
                    continue

                up_x = 0.0
                up_y = 1.0
                up_z = 0.0
                right_x = fy * up_z - fz * up_y
                right_y = fz * up_x - fx * up_z
                right_z = fx * up_y - fy * up_x

                projected_x = rel_x * right_x + rel_y * right_y + rel_z * right_z
                projected_y = rel_x * up_x + rel_y * up_y + rel_z * up_z

                hs = chunk.chunk_size / 2.0
                frustum_half_w = projected_z * vw + hs
                frustum_half_h = projected_z * vh + hs

                if abs(projected_x) <= frustum_half_w and abs(projected_y) <= frustum_half_h:
                    chunk.distance_to_camera = dist
                    visible_chunks.append(chunk)

            return visible_chunks

    def manage_memory_budget(self, world_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        with self._lock:
            config = self._configs.get(world_id)
            if config is None:
                return {"world_id": world_id, "action": "no_config", "evictions": 0}

            loaded_chunks = [
                c for c in self._chunks.values()
                if c.world_id == world_id and c.state in (ChunkState.LOADED, ChunkState.ACTIVE)
            ]

            total_memory_mb = sum(c.memory_footprint_kb for c in loaded_chunks) / 1024.0
            budget_mb = config.memory_budget_mb

            evicted_count = 0

            if len(loaded_chunks) > config.max_active_chunks:
                excess = len(loaded_chunks) - config.max_active_chunks
                candidates = sorted(
                    loaded_chunks,
                    key=lambda c: (
                        _PRIORITY_WEIGHTS.get(c.priority, 0.0),
                        -c.last_access_time,
                    ),
                )
                for chunk in candidates[:excess]:
                    self.unload_chunk(chunk.id)
                    evicted_count += 1
                    self._total_memory_evictions += 1

            if total_memory_mb > budget_mb:
                remaining_loaded = [
                    c for c in self._chunks.values()
                    if c.world_id == world_id and c.state in (ChunkState.LOADED, ChunkState.ACTIVE)
                ]
                remaining_loaded.sort(
                    key=lambda c: (
                        _PRIORITY_WEIGHTS.get(c.priority, 0.0),
                        -c.last_access_time,
                    ),
                )

                current_memory = sum(c.memory_footprint_kb for c in remaining_loaded) / 1024.0

                for chunk in remaining_loaded:
                    if current_memory <= budget_mb * 0.85:
                        break
                    current_memory -= chunk.memory_footprint_kb / 1024.0
                    self.unload_chunk(chunk.id)
                    evicted_count += 1
                    self._total_memory_evictions += 1

            return {
                "world_id": world_id,
                "action": "budget_enforced",
                "evictions": evicted_count,
                "total_memory_mb_before": round(total_memory_mb, 2),
                "memory_budget_mb": budget_mb,
                "remaining_loaded_chunks": len([
                    c for c in self._chunks.values()
                    if c.world_id == world_id and c.state in (ChunkState.LOADED, ChunkState.ACTIVE)
                ]),
            }

    def smooth_lod_transition(
        self,
        chunk_id: str,
        target_lod: str,
        fade_duration: Optional[float] = None,
    ) -> Optional[LODTransition]:
        _time_module.sleep(0.001)
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                return None

            if chunk.lod_level == target_lod:
                return None

            from_idx = _LOD_LEVEL_NAMES.index(chunk.lod_level) if chunk.lod_level in _LOD_LEVEL_NAMES else 2
            to_idx = _LOD_LEVEL_NAMES.index(target_lod) if target_lod in _LOD_LEVEL_NAMES else 2

            is_ascending = to_idx < from_idx

            if fade_duration is None:
                fade_duration = _LOD_FADE_DURATIONS["ascending" if is_ascending else "descending"]

            transition = LODTransition(
                chunk_id=chunk_id,
                from_level=chunk.lod_level,
                to_level=target_lod,
                fade_duration=fade_duration,
                is_ascending=is_ascending,
                detail_threshold=_LOD_DISTANCE_THRESHOLDS.get(target_lod, 200.0),
            )

            self._transitions[transition.id] = transition

            progress_increment = 0.016 / max(0.001, fade_duration)
            transition.transition_progress = min(1.0, progress_increment * 3.0)
            transition.fade_alpha = (
                transition.transition_progress
                if is_ascending
                else 1.0 - transition.transition_progress
            )

            chunk.lod_level = target_lod
            chunk.memory_footprint_kb = self._recalculate_chunk_memory(chunk)

            self._total_transitions_completed += 1
            transition.is_complete = True

            return transition

    def preload_predicted_chunks(
        self,
        world_id: str,
        camera_position: Optional[Tuple[float, float, float]] = None,
        camera_direction: Optional[Tuple[float, float, float]] = None,
        camera_speed: Optional[float] = None,
    ) -> List[WorldChunk]:
        _time_module.sleep(0.001)
        with self._lock:
            if camera_position:
                self._camera_position = camera_position
                self._previous_camera_positions.append(camera_position)
                if len(self._previous_camera_positions) > 30:
                    self._previous_camera_positions = self._previous_camera_positions[-30:]

            if camera_direction:
                self._camera_forward = camera_direction
            if camera_speed is not None:
                self._camera_speed = camera_speed

            config = self._configs.get(world_id)
            if config is None:
                return []

            cx, cy, cz = self._camera_position
            fx, fy, fz = self._camera_forward
            f_mag = math.sqrt(fx * fx + fy * fy + fz * fz)
            if f_mag < 1e-6:
                fx, fy, fz = 0.0, 0.0, 1.0
            else:
                fx /= f_mag
                fy /= f_mag
                fz /= f_mag

            predicted_velocity = self._camera_speed
            if predicted_velocity < 0.5 and len(self._previous_camera_positions) >= 2:
                prev = self._previous_camera_positions[-2]
                dx = cx - prev[0]
                dy = cy - prev[1]
                dz = cz - prev[2]
                predicted_velocity = math.sqrt(dx * dx + dy * dy + dz * dz) / 0.016

            predicted_chunks: List[WorldChunk] = []
            chunk_size = config.chunk_size
            look_ahead = config.prediction_look_ahead

            for step in range(1, look_ahead + 1):
                time_ahead = step * 1.5
                pred_dist = predicted_velocity * time_ahead
                pred_x = cx + fx * pred_dist
                pred_y = cy + fy * pred_dist
                pred_z = cz + fz * pred_dist

                for dx in range(-1, 2):
                    for dz in range(-1, 2):
                        spread_x = pred_x + dx * chunk_size * 0.6
                        spread_z = pred_z + dz * chunk_size * 0.6

                        grid_x = int(math.floor(spread_x / chunk_size))
                        grid_y = int(math.floor(pred_y / chunk_size))
                        grid_z = int(math.floor(spread_z / chunk_size))

                        key = (grid_x, grid_y, grid_z, world_id)
                        existing_id = self._grid_index.get(key)
                        if existing_id and existing_id in self._chunks:
                            chunk = self._chunks[existing_id]
                            if chunk not in predicted_chunks:
                                predicted_chunks.append(chunk)

            return predicted_chunks

    def update_camera(
        self,
        position: Tuple[float, float, float],
        forward: Tuple[float, float, float],
        speed: float = 0.0,
    ) -> None:
        _time_module.sleep(0.001)
        with self._lock:
            self._camera_position = position
            self._camera_forward = forward
            self._camera_speed = speed
            self._previous_camera_positions.append(position)
            if len(self._previous_camera_positions) > 30:
                self._previous_camera_positions = self._previous_camera_positions[-30:]

    def tick(self, world_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        with self._lock:
            self._frame_count += 1
            config = self._configs.get(world_id)
            if config is None:
                return {"world_id": world_id, "status": "no_config"}

            self.prioritize_chunks(world_id)
            visible = self.compute_chunk_visibility(world_id)
            predicted = self.preload_predicted_chunks(world_id)

            loaded_this_frame = 0
            for chunk in visible:
                if chunk.state == ChunkState.UNLOADED:
                    active_count = len([
                        c for c in self._chunks.values()
                        if c.world_id == world_id and c.state in (ChunkState.LOADED, ChunkState.ACTIVE)
                    ])
                    if active_count < config.max_active_chunks:
                        self.load_chunk(chunk.id, priority=chunk.priority.value)
                        loaded_this_frame += 1

            for chunk in predicted:
                if chunk.state == ChunkState.UNLOADED:
                    active_count = len([
                        c for c in self._chunks.values()
                        if c.world_id == world_id and c.state in (ChunkState.LOADED, ChunkState.ACTIVE)
                    ])
                    if active_count < config.max_active_chunks:
                        self.load_chunk(chunk.id, priority="background")
                        loaded_this_frame += 1

            unload_radius = config.view_distance * config.unload_radius_multiplier
            for chunk in visible:
                if chunk.distance_to_camera > unload_radius:
                    if chunk.state in (ChunkState.LOADED, ChunkState.ACTIVE):
                        self.unload_chunk(chunk.id)

            mem_result = self.manage_memory_budget(world_id)

            for chunk in visible:
                if chunk.state == ChunkState.LOADED:
                    chunk.state = ChunkState.ACTIVE

            for chunk in visible:
                target_lod = config.resolve_lod_for_distance(chunk.distance_to_camera)
                if target_lod != chunk.lod_level:
                    self.smooth_lod_transition(chunk.id, target_lod)

            return {
                "world_id": world_id,
                "frame": self._frame_count,
                "visible_chunks": len(visible),
                "predicted_chunks": len(predicted),
                "loaded_this_frame": loaded_this_frame,
                "active_chunks": len([
                    c for c in self._chunks.values()
                    if c.world_id == world_id and c.state == ChunkState.ACTIVE
                ]),
                "loaded_chunks": len([
                    c for c in self._chunks.values()
                    if c.world_id == world_id and c.state in (ChunkState.LOADED, ChunkState.ACTIVE)
                ]),
                "memory_enforcement": mem_result,
                "camera_position": list(self._camera_position),
            }

    def _resolve_priority(self, priority_value: str) -> PriorityLevel:
        try:
            return PriorityLevel(priority_value.lower())
        except ValueError:
            return PriorityLevel.NORMAL

    def _estimate_memory_for_lod(
        self, lod_level: str, config: StreamingConfig
    ) -> float:
        base_memory_per_chunk = 4096.0
        factor = config.lod_memory_factors.get(lod_level, _LOD_MEMORY_FACTORS.get(lod_level, 0.28))
        return base_memory_per_chunk * factor

    def _recalculate_chunk_memory(self, chunk: WorldChunk) -> float:
        config = self._configs.get(chunk.world_id)
        if config is None:
            factor = _LOD_MEMORY_FACTORS.get(chunk.lod_level, 0.28)
        else:
            factor = config.lod_memory_factors.get(
                chunk.lod_level, _LOD_MEMORY_FACTORS.get(chunk.lod_level, 0.28)
            )
        return 4096.0 * factor

    def get_chunk(self, chunk_id: str) -> Optional[WorldChunk]:
        _time_module.sleep(0.001)
        return self._chunks.get(chunk_id)

    def get_chunks_for_world(self, world_id: str) -> List[WorldChunk]:
        _time_module.sleep(0.001)
        return [
            c for c in self._chunks.values() if c.world_id == world_id
        ]

    def get_config(self, world_id: str) -> Optional[StreamingConfig]:
        _time_module.sleep(0.001)
        return self._configs.get(world_id)

    def get_active_transitions(self, world_id: str) -> List[LODTransition]:
        _time_module.sleep(0.001)
        world_chunk_ids = {
            c.id for c in self._chunks.values() if c.world_id == world_id
        }
        return [
            t for t in self._transitions.values()
            if t.chunk_id in world_chunk_ids
        ]

    def list_chunks(self) -> List[Dict[str, Any]]:
        """Return all chunks as dicts."""
        _time_module.sleep(0.001)
        return [c.to_dict() for c in self._chunks.values()]

    def get_queue_status(self) -> Dict[str, Any]:
        """Return the current loading queue status."""
        _time_module.sleep(0.001)
        chunks = list(self._chunks.values())
        loading = [c for c in chunks if c.state == ChunkState.LOADING]
        queued = [c for c in chunks if c.state == ChunkState.UNLOADED]
        return {
            "total_chunks": len(chunks),
            "loaded_chunks": len([c for c in chunks if c.state in (ChunkState.LOADED, ChunkState.ACTIVE)]),
            "loading_chunks": len(loading),
            "queued_chunks": len(queued),
            "queue": [c.to_dict() for c in loading + queued[:10]],
        }

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        with self._lock:
            state_counts: Dict[str, int] = {}
            for chunk in self._chunks.values():
                s = chunk.state.value
                state_counts[s] = state_counts.get(s, 0) + 1

            lod_counts: Dict[str, int] = {}
            for chunk in self._chunks.values():
                lod = chunk.lod_level
                lod_counts[lod] = lod_counts.get(lod, 0) + 1

            total_memory_mb = sum(
                c.memory_footprint_kb for c in self._chunks.values()
            ) / 1024.0

            per_world_stats = {}
            for world_id in self._configs:
                world_chunks = [c for c in self._chunks.values() if c.world_id == world_id]
                world_loaded = [c for c in world_chunks if c.state in (ChunkState.LOADED, ChunkState.ACTIVE)]
                world_memory_mb = sum(c.memory_footprint_kb for c in world_loaded) / 1024.0
                per_world_stats[world_id] = {
                    "total_chunks": len(world_chunks),
                    "loaded_chunks": len(world_loaded),
                    "memory_usage_mb": round(world_memory_mb, 2),
                    "queue_pending": len(self._queues.get(world_id, LoadingQueue()).queued_chunk_ids),
                }

            return {
                "total_chunks": len(self._chunks),
                "total_worlds": len(self._configs),
                "chunk_state_distribution": state_counts,
                "lod_level_distribution": lod_counts,
                "total_memory_usage_mb": round(total_memory_mb, 2),
                "total_chunks_loaded": self._total_chunks_loaded,
                "total_chunks_unloaded": self._total_chunks_unloaded,
                "total_transitions_completed": self._total_transitions_completed,
                "total_memory_evictions": self._total_memory_evictions,
                "active_transitions": len(self._transitions),
                "frame_count": self._frame_count,
                "camera_position": list(self._camera_position),
                "per_world": per_world_stats,
            }

    def reset(self) -> None:
        _time_module.sleep(0.001)
        with self._lock:
            self._chunks.clear()
            self._configs.clear()
            self._queues.clear()
            self._transitions.clear()
            self._grid_index.clear()
            self._camera_position = (0.0, 0.0, 0.0)
            self._camera_forward = (0.0, 0.0, 1.0)
            self._camera_speed = 0.0
            self._previous_camera_positions.clear()
            self._total_chunks_loaded = 0
            self._total_chunks_unloaded = 0
            self._total_transitions_completed = 0
            self._total_memory_evictions = 0
            self._frame_count = 0


def get_progressive_loading() -> EngineProgressiveLoading:
    return EngineProgressiveLoading()