"""
SparkLabs Engine - Scene Streamer

Dynamic world streaming system that partitions large game worlds into
manageable chunks and loads/unloads them based on camera proximity.
Supports priority-based loading, preloading prediction, and smooth
level-of-detail transitions for seamless open-world experiences.

Architecture:
  SceneStreamer
    |-- ChunkManager (chunk lifecycle and memory management)
    |-- LoadBalancer (prioritized async chunk loading)
    |-- ProximityTracker (distance-based load/unload decisions)
    |-- LODController (detail level transitions)
    |-- PredictionEngine (predictive preloading based on movement)

Streaming Policies:
  - DISTANCE_BASED: load within radius, unload beyond
  - PRIORITY_BASED: load high-priority chunks first
  - PREDICTIVE: preload chunks ahead of camera direction
  - LOD_BASED: load high-detail near, low-detail far
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ChunkState(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    ERROR = "error"


class RequestType(Enum):
    LOAD = "load"
    UNLOAD = "unload"
    SWAP_LOD = "swap_lod"


class RequestStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StreamPolicy(Enum):
    DISTANCE_BASED = "distance_based"
    PRIORITY_BASED = "priority_based"
    PREDICTIVE = "predictive"
    LOD_BASED = "lod_based"


class LODLevel(Enum):
    ULTRA = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    MINIMAL = 4


LOD_DISTANCE_DEFAULTS: Dict[LODLevel, float] = {
    LODLevel.ULTRA: 50.0,
    LODLevel.HIGH: 100.0,
    LODLevel.MEDIUM: 200.0,
    LODLevel.LOW: 400.0,
    LODLevel.MINIMAL: 800.0,
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
    priority: int = 5
    entities: List[str] = field(default_factory=list)
    last_accessed: float = field(default_factory=time.time)
    memory_estimate_kb: float = 0.0
    lod_level: LODLevel = LODLevel.HIGH

    @property
    def grid_key(self) -> Tuple[int, int, int]:
        return (self.grid_x, self.grid_y, self.grid_z)

    @property
    def center(self) -> Tuple[float, float, float]:
        return (
            (self.bounds_min[0] + self.bounds_max[0]) / 2.0,
            (self.bounds_min[1] + self.bounds_max[1]) / 2.0,
            (self.bounds_min[2] + self.bounds_max[2]) / 2.0,
        )

    def contains_point(self, x: float, y: float, z: float) -> bool:
        return (
            self.bounds_min[0] <= x <= self.bounds_max[0]
            and self.bounds_min[1] <= y <= self.bounds_max[1]
            and self.bounds_min[2] <= z <= self.bounds_max[2]
        )

    def distance_to(self, x: float, y: float, z: float) -> float:
        cx, cy, cz = self.center
        return math.sqrt((cx - x) ** 2 + (cy - y) ** 2 + (cz - z) ** 2)

    def set_bounds_from_grid(self) -> None:
        hs = self.chunk_size / 2.0
        center_x = self.grid_x * self.chunk_size + hs
        center_y = self.grid_y * self.chunk_size + hs
        center_z = self.grid_z * self.chunk_size + hs
        self.bounds_min = (center_x - hs, center_y - hs, center_z - hs)
        self.bounds_max = (center_x + hs, center_y + hs, center_z + hs)

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
            "priority": self.priority,
            "entities": self.entities,
            "last_accessed": self.last_accessed,
            "memory_estimate_kb": self.memory_estimate_kb,
            "lod_level": self.lod_level.name,
        }


@dataclass
class StreamingConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_id: str = ""
    load_radius_chunks: int = 3
    unload_radius_chunks: int = 5
    max_loaded_chunks: int = 64
    preload_direction_chunks: int = 2
    lod_distances: Dict[LODLevel, float] = field(default_factory=lambda: dict(LOD_DISTANCE_DEFAULTS))
    async_loading: bool = True
    memory_budget_mb: float = 512.0

    def get_lod_for_distance(self, distance: float) -> LODLevel:
        sorted_levels = sorted(self.lod_distances.items(), key=lambda x: x[1])
        for level, threshold in sorted_levels:
            if distance <= threshold:
                return level
        return LODLevel.MINIMAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "world_id": self.world_id,
            "load_radius_chunks": self.load_radius_chunks,
            "unload_radius_chunks": self.unload_radius_chunks,
            "max_loaded_chunks": self.max_loaded_chunks,
            "preload_direction_chunks": self.preload_direction_chunks,
            "lod_distances": {k.name: v for k, v in self.lod_distances.items()},
            "async_loading": self.async_loading,
            "memory_budget_mb": self.memory_budget_mb,
        }


@dataclass
class ChunkRequest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    chunk_id: str = ""
    request_type: RequestType = RequestType.LOAD
    priority: int = 5
    created_at: float = field(default_factory=time.time)
    status: RequestStatus = RequestStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chunk_id": self.chunk_id,
            "request_type": self.request_type.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "status": self.status.value,
        }


@dataclass
class CameraState:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    forward_direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    speed: float = 0.0
    view_distance: float = 800.0

    @property
    def forward_normalized(self) -> Tuple[float, float, float]:
        dx, dy, dz = self.forward_direction
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 0.0001:
            return (0.0, 0.0, 1.0)
        return (dx / length, dy / length, dz / length)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "world_id": self.world_id,
            "position": list(self.position),
            "forward_direction": list(self.forward_direction),
            "speed": self.speed,
            "view_distance": self.view_distance,
        }


class SceneStreamer:
    """
    Dynamic world streaming system for large seamless open worlds.

    Manages spatial chunk partitioning with distance-based loading,
    priority scheduling, LOD transitions, and predictive preloading.
    Coordinates multiple cameras across multiple worlds.
    """

    _instance: Optional["SceneStreamer"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._worlds: Dict[str, StreamingConfig] = {}
        self._chunks: Dict[str, WorldChunk] = {}
        self._configs: Dict[str, StreamingConfig] = {}
        self._requests: List[ChunkRequest] = []
        self._cameras: Dict[str, CameraState] = {}
        self._total_loads: int = 0
        self._total_unloads: int = 0
        self._total_lod_swaps: int = 0
        self._failed_requests: int = 0

        self._seed_default_config()

    @classmethod
    def get_instance(cls) -> "SceneStreamer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # World Management
    # ------------------------------------------------------------------

    def create_world(self, world_id: str, chunk_size: float = 256.0) -> StreamingConfig:
        with self._lock:
            if world_id in self._configs:
                return self._configs[world_id]

            config = StreamingConfig(
                world_id=world_id,
                load_radius_chunks=3,
                unload_radius_chunks=5,
                max_loaded_chunks=64,
                preload_direction_chunks=2,
                lod_distances=dict(LOD_DISTANCE_DEFAULTS),
                async_loading=True,
                memory_budget_mb=512.0,
            )
            self._configs[world_id] = config
            self._worlds[world_id] = config
            return config

    # ------------------------------------------------------------------
    # Chunk Management
    # ------------------------------------------------------------------

    def add_chunk(
        self,
        world_id: str,
        grid_x: int,
        grid_y: int,
        grid_z: int,
        priority: int = 5,
        chunk_size: float = 256.0,
    ) -> Optional[WorldChunk]:
        with self._lock:
            config = self._configs.get(world_id)
            if config is None:
                return None

            existing = self._find_chunk_by_grid(world_id, grid_x, grid_y, grid_z)
            if existing is not None:
                return existing

            chunk = WorldChunk(
                world_id=world_id,
                grid_x=grid_x,
                grid_y=grid_y,
                grid_z=grid_z,
                chunk_size=chunk_size,
                priority=priority,
                state=ChunkState.UNLOADED,
            )
            chunk.set_bounds_from_grid()
            self._chunks[chunk.id] = chunk
            return chunk

    def remove_chunk(self, chunk_id: str) -> bool:
        with self._lock:
            if chunk_id not in self._chunks:
                return False
            del self._chunks[chunk_id]
            self._requests = [r for r in self._requests if r.chunk_id != chunk_id]
            return True

    def _find_chunk_by_grid(
        self, world_id: str, grid_x: int, grid_y: int, grid_z: int
    ) -> Optional[WorldChunk]:
        for chunk in self._chunks.values():
            if (
                chunk.world_id == world_id
                and chunk.grid_x == grid_x
                and chunk.grid_y == grid_y
                and chunk.grid_z == grid_z
            ):
                return chunk
        return None

    def get_chunk_at_position(
        self, world_id: str, x: float, y: float, z: float
    ) -> Optional[WorldChunk]:
        with self._lock:
            config = self._configs.get(world_id)
            if config is None:
                return None
            for chunk in self._chunks.values():
                if chunk.world_id == world_id and chunk.contains_point(x, y, z):
                    return chunk
            return None

    def get_loaded_chunks(self, world_id: str) -> List[WorldChunk]:
        with self._lock:
            return [
                chunk
                for chunk in self._chunks.values()
                if chunk.world_id == world_id and chunk.state == ChunkState.LOADED
            ]

    def get_chunks_in_radius(
        self, world_id: str, position: Tuple[float, float, float], radius: float
    ) -> List[WorldChunk]:
        with self._lock:
            px, py, pz = position
            radius_sq = radius * radius
            result: List[WorldChunk] = []
            for chunk in self._chunks.values():
                if chunk.world_id != world_id:
                    continue
                cx, cy, cz = chunk.center
                dist_sq = (cx - px) ** 2 + (cy - py) ** 2 + (cz - pz) ** 2
                if dist_sq <= radius_sq:
                    result.append(chunk)
            return result

    def set_chunk_priority(self, chunk_id: str, priority: int) -> bool:
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                return False
            chunk.priority = max(0, min(10, priority))
            return True

    # ------------------------------------------------------------------
    # Camera Management
    # ------------------------------------------------------------------

    def update_camera(
        self,
        camera_id: str,
        world_id: str,
        position: Tuple[float, float, float],
        forward: Tuple[float, float, float],
        speed: float,
    ) -> CameraState:
        with self._lock:
            cam = self._cameras.get(camera_id)
            if cam is None:
                cam = CameraState(
                    id=camera_id,
                    world_id=world_id,
                    position=position,
                    forward_direction=forward,
                    speed=speed,
                )
                self._cameras[camera_id] = cam
            else:
                cam.world_id = world_id
                cam.position = position
                cam.forward_direction = forward
                cam.speed = speed
            return cam

    # ------------------------------------------------------------------
    # Main Tick Logic
    # ------------------------------------------------------------------

    def tick(self, delta_time: float) -> Dict[str, Any]:
        """Per-frame streamer logic: evaluate proximity, issue requests, process queue, enforce limits."""
        with self._lock:
            frame_loads: int = 0
            frame_unloads: int = 0
            frame_lod_swaps: int = 0
            frame_failures: int = 0

            for camera_id, camera in self._cameras.items():
                config = self._configs.get(camera.world_id)
                if config is None:
                    continue

                lod_swaps = self._compute_lod_transitions(camera.world_id, camera, config)
                frame_lod_swaps += len(lod_swaps)
                for chunk_id, new_lod in lod_swaps:
                    self._issue_request(chunk_id, RequestType.SWAP_LOD, priority=3)

                load_radius = config.load_radius_chunks * self._get_chunk_size(camera.world_id)

                world_chunks = [
                    c for c in self._chunks.values() if c.world_id == camera.world_id
                ]

                for chunk in world_chunks:
                    dist = chunk.distance_to(*camera.position)

                    if (
                        dist <= load_radius
                        and chunk.state == ChunkState.UNLOADED
                        and self._count_loaded(camera.world_id) < config.max_loaded_chunks
                    ):
                        self._issue_request(chunk.id, RequestType.LOAD, priority=chunk.priority)
                        frame_loads += 1
                    elif (
                        dist > config.unload_radius_chunks * self._get_chunk_size(camera.world_id)
                        and chunk.state == ChunkState.LOADED
                    ):
                        self._issue_request(chunk.id, RequestType.UNLOAD, priority=1)
                        frame_unloads += 1

                predicted = self.predict_preload_chunks(camera.world_id, camera_id)
                for chunk in predicted:
                    if (
                        chunk.state == ChunkState.UNLOADED
                        and self._count_loaded(camera.world_id) < config.max_loaded_chunks
                    ):
                        self._issue_request(chunk.id, RequestType.LOAD, priority=6)
                        frame_loads += 1

            completed, failed = self._process_requests(delta_time)
            frame_failures += failed

            self._enforce_memory_limits()

            return {
                "frame_loads": frame_loads,
                "frame_unloads": frame_unloads,
                "frame_lod_swaps": frame_lod_swaps,
                "frame_failures": frame_failures,
                "requests_completed": completed,
                "requests_failed": failed,
                "total_loaded_chunks": sum(
                    self._count_loaded(wid) for wid in self._configs
                ),
                "total_pending_requests": len(
                    [r for r in self._requests if r.status == RequestStatus.PENDING]
                ),
                "active_cameras": len(self._cameras),
                "active_worlds": len(self._configs),
            }

    def _get_chunk_size(self, world_id: str) -> float:
        world_chunks = [c for c in self._chunks.values() if c.world_id == world_id]
        if world_chunks:
            return world_chunks[0].chunk_size
        return 256.0

    def _count_loaded(self, world_id: str) -> int:
        return len([
            c
            for c in self._chunks.values()
            if c.world_id == world_id and c.state == ChunkState.LOADED
        ])

    # ------------------------------------------------------------------
    # Request Management
    # ------------------------------------------------------------------

    def _issue_request(
        self,
        chunk_id: str,
        request_type: RequestType,
        priority: int = 5,
    ) -> Optional[ChunkRequest]:
        existing = [
            r
            for r in self._requests
            if r.chunk_id == chunk_id
            and r.request_type == request_type
            and r.status in (RequestStatus.PENDING, RequestStatus.PROCESSING)
        ]
        if existing:
            return existing[0]

        request = ChunkRequest(
            chunk_id=chunk_id,
            request_type=request_type,
            priority=priority,
            status=RequestStatus.PENDING,
        )
        self._requests.append(request)
        return request

    def _process_requests(self, delta_time: float) -> Tuple[int, int]:
        completed = 0
        failed = 0

        pending = sorted(
            [r for r in self._requests if r.status == RequestStatus.PENDING],
            key=lambda r: (-r.priority, r.created_at),
        )

        max_per_frame = max(1, int(len(pending) * 0.3) + 2)

        processed = 0
        for request in pending:
            if processed >= max_per_frame:
                break

            request.status = RequestStatus.PROCESSING
            chunk = self._chunks.get(request.chunk_id)

            if chunk is None:
                request.status = RequestStatus.FAILED
                self._failed_requests += 1
                failed += 1
                processed += 1
                continue

            if request.request_type == RequestType.LOAD:
                chunk.state = ChunkState.LOADING
                chunk.last_accessed = time.time()

                request.status = RequestStatus.COMPLETED
                chunk.state = ChunkState.LOADED
                chunk.last_accessed = time.time()
                self._total_loads += 1
                completed += 1

            elif request.request_type == RequestType.UNLOAD:
                chunk.state = ChunkState.UNLOADING
                chunk.last_accessed = time.time()

                chunk.entities.clear()
                chunk.memory_estimate_kb = 0.0
                chunk.state = ChunkState.UNLOADED
                request.status = RequestStatus.COMPLETED
                self._total_unloads += 1
                completed += 1

            elif request.request_type == RequestType.SWAP_LOD:
                config = self._configs.get(chunk.world_id)
                if config is None:
                    request.status = RequestStatus.FAILED
                    self._failed_requests += 1
                    failed += 1
                    processed += 1
                    continue

                camera = self._find_camera_for_world(chunk.world_id)
                if camera is not None:
                    dist = chunk.distance_to(*camera.position)
                    new_lod = config.get_lod_for_distance(dist)
                    chunk.lod_level = new_lod

                request.status = RequestStatus.COMPLETED
                self._total_lod_swaps += 1
                completed += 1

            processed += 1

        self._requests = [
            r
            for r in self._requests
            if r.status not in (RequestStatus.COMPLETED, RequestStatus.FAILED)
            or time.time() - r.created_at < 5.0
        ]

        return completed, failed

    def _find_camera_for_world(self, world_id: str) -> Optional[CameraState]:
        for camera in self._cameras.values():
            if camera.world_id == world_id:
                return camera
        return None

    # ------------------------------------------------------------------
    # LOD Transitions
    # ------------------------------------------------------------------

    def _compute_lod_transitions(
        self, world_id: str, camera: CameraState, config: StreamingConfig
    ) -> List[Tuple[str, LODLevel]]:
        transitions: List[Tuple[str, LODLevel]] = []
        for chunk in self._chunks.values():
            if chunk.world_id != world_id:
                continue
            if chunk.state != ChunkState.LOADED:
                continue

            dist = chunk.distance_to(*camera.position)
            target_lod = config.get_lod_for_distance(dist)

            if target_lod != chunk.lod_level:
                transitions.append((chunk.id, target_lod))

        return transitions

    # ------------------------------------------------------------------
    # Predictive Preloading
    # ------------------------------------------------------------------

    def predict_preload_chunks(
        self, world_id: str, camera_id: str
    ) -> List[WorldChunk]:
        with self._lock:
            camera = self._cameras.get(camera_id)
            if camera is None or camera.world_id != world_id:
                return []

            config = self._configs.get(world_id)
            if config is None:
                return []

            fnx, fny, fnz = camera.forward_normalized
            px, py, pz = camera.position
            chunk_size = self._get_chunk_size(world_id)

            preload_chunks: List[WorldChunk] = []
            look_ahead = config.preload_direction_chunks

            for i in range(1, look_ahead + 1):
                sample_x = px + fnx * chunk_size * i
                sample_y = py + fny * chunk_size * i
                sample_z = pz + fnz * chunk_size * i

                for dy in range(-1, 2):
                    for dz in range(-1, 2):
                        neighbor_x = sample_x + dy * chunk_size * 0.5
                        neighbor_z = sample_z + dz * chunk_size * 0.5

                        grid_x = int(math.floor(neighbor_x / chunk_size))
                        grid_y = int(math.floor(sample_y / chunk_size))
                        grid_z = int(math.floor(neighbor_z / chunk_size))

                        chunk = self._find_chunk_by_grid(world_id, grid_x, grid_y, grid_z)
                        if chunk is not None and chunk not in preload_chunks:
                            preload_chunks.append(chunk)

            return preload_chunks

    # ------------------------------------------------------------------
    # Memory Enforcement
    # ------------------------------------------------------------------

    def _enforce_memory_limits(self) -> None:
        for world_id, config in self._configs.items():
            loaded = [
                c
                for c in self._chunks.values()
                if c.world_id == world_id and c.state == ChunkState.LOADED
            ]

            if len(loaded) > config.max_loaded_chunks:
                excess = len(loaded) - config.max_loaded_chunks
                candidates = sorted(
                    loaded,
                    key=lambda c: (c.priority, -c.last_accessed),
                )
                for chunk in candidates[:excess]:
                    self._issue_request(chunk.id, RequestType.UNLOAD, priority=0)

            total_mem_mb = sum(
                c.memory_estimate_kb for c in loaded
            ) / 1024.0
            if total_mem_mb > config.memory_budget_mb:
                candidates = sorted(
                    loaded,
                    key=lambda c: (c.priority, -c.last_accessed),
                )
                for chunk in candidates:
                    if total_mem_mb <= config.memory_budget_mb:
                        break
                    total_mem_mb -= chunk.memory_estimate_kb / 1024.0
                    self._issue_request(chunk.id, RequestType.UNLOAD, priority=0)

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_default_config(self) -> None:
        default_config = StreamingConfig(
            world_id="__default__",
            load_radius_chunks=3,
            unload_radius_chunks=5,
            max_loaded_chunks=64,
            preload_direction_chunks=2,
            lod_distances={
                LODLevel.ULTRA: 50.0,
                LODLevel.HIGH: 100.0,
                LODLevel.MEDIUM: 200.0,
                LODLevel.LOW: 400.0,
                LODLevel.MINIMAL: 800.0,
            },
            async_loading=True,
            memory_budget_mb=512.0,
        )
        self._configs[default_config.world_id] = default_config
        self._worlds[default_config.world_id] = default_config

    # ------------------------------------------------------------------
    # Statistics and Queries
    # ------------------------------------------------------------------

    def get_streaming_stats(self, world_id: str) -> Dict[str, Any]:
        with self._lock:
            config = self._configs.get(world_id)
            chunks_in_world = [
                c for c in self._chunks.values() if c.world_id == world_id
            ]
            state_counts: Dict[str, int] = {}
            for chunk in chunks_in_world:
                s = chunk.state.value
                state_counts[s] = state_counts.get(s, 0) + 1

            loaded = [c for c in chunks_in_world if c.state == ChunkState.LOADED]
            total_memory_kb = sum(c.memory_estimate_kb for c in loaded)

            lod_counts: Dict[str, int] = {}
            for chunk in chunks_in_world:
                lod = chunk.lod_level.name
                lod_counts[lod] = lod_counts.get(lod, 0) + 1

            return {
                "world_id": world_id,
                "total_chunks": len(chunks_in_world),
                "state_counts": state_counts,
                "lod_counts": lod_counts,
                "memory_usage_kb": total_memory_kb,
                "memory_usage_mb": round(total_memory_kb / 1024.0, 2),
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_chunks = len(self._chunks)
            total_loaded = sum(
                self._count_loaded(wid) for wid in self._configs
            )
            pending_count = len(
                [r for r in self._requests if r.status == RequestStatus.PENDING]
            )
            processing_count = len(
                [r for r in self._requests if r.status == RequestStatus.PROCESSING]
            )

            total_memory_kb = sum(
                c.memory_estimate_kb
                for c in self._chunks.values()
                if c.state == ChunkState.LOADED
            )

            return {
                "total_chunks": total_chunks,
                "total_loaded_chunks": total_loaded,
                "total_worlds": len(self._configs),
                "total_cameras": len(self._cameras),
                "pending_requests": pending_count,
                "processing_requests": processing_count,
                "total_loads": self._total_loads,
                "total_unloads": self._total_unloads,
                "total_lod_swaps": self._total_lod_swaps,
                "failed_requests": self._failed_requests,
                "total_memory_kb": total_memory_kb,
                "total_memory_mb": round(total_memory_kb / 1024.0, 2),
                "worlds": {
                    wid: self.get_streaming_stats(wid) for wid in self._configs
                },
            }


def get_scene_streamer() -> SceneStreamer:
    return SceneStreamer.get_instance()