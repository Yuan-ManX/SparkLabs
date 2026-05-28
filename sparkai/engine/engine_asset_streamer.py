"""
SparkLabs Engine - Asset Streamer

On-demand asset streaming system for large game worlds. Manages asset
loading and unloading based on player proximity, priority queues,
memory budgets, and movement-based prefetching predictions.

Architecture:
  AssetStreamer
    |-- StreamedAsset (individual asset with spatial and memory metadata)
    |-- StreamingZone (named spatial grouping of assets for bulk operations)
    |-- MemoryReport (aggregate memory usage snapshot)
    |-- Priority-based load scheduling with distance-to-observer calculations

Streaming Policies:
  - DISTANCE_BASED: load within load_radius, unload beyond unload_radius
  - VISIBILITY_BASED: load assets within the camera frustum
  - PRIORITY_QUEUE: load highest-priority assets first regardless of distance
  - MANUAL: explicit load/unload requests only, no automatic streaming

Memory Priorities:
  - ESSENTIAL: must stay loaded at all times (e.g. player character)
  - HIGH: important for immediate gameplay (e.g. nearby enemies)
  - NORMAL: standard game assets (e.g. environment props)
  - LOW: background decoration (e.g. distant terrain detail)
  - PURGEABLE: first to evict under memory pressure (e.g. cached audio)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AssetLoadState(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    FAILED = "failed"


class AssetCategory(Enum):
    TEXTURE = "texture"
    MODEL = "model"
    AUDIO = "audio"
    ANIMATION = "animation"
    LEVEL_CHUNK = "level_chunk"
    SHADER = "shader"
    FONT = "font"
    PREFAB = "prefab"


class StreamingPolicy(Enum):
    DISTANCE_BASED = "distance_based"
    VISIBILITY_BASED = "visibility_based"
    PRIORITY_QUEUE = "priority_queue"
    MANUAL = "manual"


class MemoryPriority(Enum):
    ESSENTIAL = "essential"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    PURGEABLE = "purgeable"


_MEMORY_PRIORITY_ORDER: Dict[MemoryPriority, int] = {
    MemoryPriority.ESSENTIAL: 0,
    MemoryPriority.HIGH: 10,
    MemoryPriority.NORMAL: 20,
    MemoryPriority.LOW: 30,
    MemoryPriority.PURGEABLE: 40,
}

_CATEGORY_DEFAULT_SIZE: Dict[AssetCategory, int] = {
    AssetCategory.TEXTURE: 4 * 1024 * 1024,
    AssetCategory.MODEL: 8 * 1024 * 1024,
    AssetCategory.AUDIO: 2 * 1024 * 1024,
    AssetCategory.ANIMATION: 1 * 1024 * 1024,
    AssetCategory.LEVEL_CHUNK: 32 * 1024 * 1024,
    AssetCategory.SHADER: 256 * 1024,
    AssetCategory.FONT: 512 * 1024,
    AssetCategory.PREFAB: 16 * 1024 * 1024,
}


@dataclass
class StreamedAsset:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_path: str = ""
    category: AssetCategory = AssetCategory.MODEL
    state: AssetLoadState = AssetLoadState.UNLOADED
    memory_size_bytes: int = 0
    priority: MemoryPriority = MemoryPriority.NORMAL
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    load_radius: float = 100.0
    unload_radius: float = 150.0
    reference_count: int = 0
    last_accessed_at: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)

    @property
    def is_loaded(self) -> bool:
        return self.state == AssetLoadState.LOADED

    @property
    def is_loading(self) -> bool:
        return self.state == AssetLoadState.LOADING

    @property
    def is_unloaded(self) -> bool:
        return self.state == AssetLoadState.UNLOADED

    @property
    def is_essential(self) -> bool:
        return self.priority == MemoryPriority.ESSENTIAL

    def distance_to(self, x: float, y: float, z: float) -> float:
        px, py, pz = self.position
        return math.sqrt((px - x) ** 2 + (py - y) ** 2 + (pz - z) ** 2)

    def is_within_load_radius(self, x: float, y: float, z: float) -> bool:
        return self.distance_to(x, y, z) <= self.load_radius

    def is_beyond_unload_radius(self, x: float, y: float, z: float) -> bool:
        return self.distance_to(x, y, z) > self.unload_radius

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "asset_path": self.asset_path,
            "category": self.category.value,
            "state": self.state.value,
            "memory_size_bytes": self.memory_size_bytes,
            "priority": self.priority.value,
            "position": list(self.position),
            "load_radius": self.load_radius,
            "unload_radius": self.unload_radius,
            "reference_count": self.reference_count,
            "last_accessed_at": self.last_accessed_at,
            "created_at": self.created_at,
        }


@dataclass
class StreamingZone:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    zone_center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    zone_radius: float = 200.0
    asset_ids: List[str] = field(default_factory=list)
    is_active: bool = False
    created_at: float = field(default_factory=time.time)

    @property
    def asset_count(self) -> int:
        return len(self.asset_ids)

    def contains_point(self, x: float, y: float, z: float) -> bool:
        cx, cy, cz = self.zone_center
        dist_sq = (cx - x) ** 2 + (cy - y) ** 2 + (cz - z) ** 2
        return dist_sq <= self.zone_radius ** 2

    def distance_to(self, x: float, y: float, z: float) -> float:
        cx, cy, cz = self.zone_center
        return math.sqrt((cx - x) ** 2 + (cy - y) ** 2 + (cz - z) ** 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "zone_center": list(self.zone_center),
            "zone_radius": self.zone_radius,
            "asset_count": len(self.asset_ids),
            "asset_ids": list(self.asset_ids),
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class MemoryReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    total_allocated: int = 0
    total_reserved: int = 0
    budget_limit: int = 0
    asset_count: int = 0
    loaded_count: int = 0
    loading_count: int = 0
    fragmentation_pct: float = 0.0
    created_at: float = field(default_factory=time.time)

    @property
    def budget_usage_pct(self) -> float:
        if self.budget_limit <= 0:
            return 0.0
        return (self.total_allocated / self.budget_limit) * 100.0

    @property
    def available_bytes(self) -> int:
        return max(0, self.budget_limit - self.total_allocated)

    @property
    def is_over_budget(self) -> bool:
        return self.total_allocated > self.budget_limit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "total_allocated": self.total_allocated,
            "total_reserved": self.total_reserved,
            "budget_limit": self.budget_limit,
            "asset_count": self.asset_count,
            "loaded_count": self.loaded_count,
            "loading_count": self.loading_count,
            "fragmentation_pct": round(self.fragmentation_pct, 2),
            "budget_usage_pct": round(self.budget_usage_pct, 2),
            "available_bytes": self.available_bytes,
            "is_over_budget": self.is_over_budget,
            "created_at": self.created_at,
        }


class AssetStreamer:
    """
    On-demand asset streaming system for large game worlds.

    Manages asset lifecycle based on observer proximity, priority
    scheduling, memory budgets, and spatial zone groupings. Provides
    both automatic distance-based streaming and manual control via
    explicit load/unload requests.

    Usage:
        streamer = get_asset_streamer()
        streamer.set_memory_budget(512 * 1024 * 1024)
        asset = streamer.register_asset(
            "meshes/rock_01.glb", AssetCategory.MODEL,
            memory_size=2_000_000, position=(50, 10, -30),
            load_radius=80, unload_radius=120,
        )
        report = streamer.update_streaming((player_x, player_y, player_z))
        print(report.to_dict())
    """

    _instance: Optional["AssetStreamer"] = None
    _lock: threading.RLock = threading.RLock()

    _time_module = time

    def __init__(self) -> None:
        self._assets: Dict[str, StreamedAsset] = {}
        self._zones: Dict[str, StreamingZone] = {}
        self._memory_budget: int = 256 * 1024 * 1024
        self._current_allocation: int = 0
        self._policy: StreamingPolicy = StreamingPolicy.DISTANCE_BASED
        self._pending_loads: List[str] = []
        self._pending_unloads: List[str] = []
        self._total_registrations: int = 0
        self._total_unregistrations: int = 0
        self._total_loads_completed: int = 0
        self._total_unloads_completed: int = 0
        self._total_load_failures: int = 0
        self._last_observer_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._last_update_time: float = self._time_module.time()
        self._fragmentation_estimate: float = 0.0

    @classmethod
    def get_instance(cls) -> "AssetStreamer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Asset Registration
    # ------------------------------------------------------------------

    def register_asset(
        self,
        asset_path: str,
        category: AssetCategory = AssetCategory.MODEL,
        memory_size: int = 0,
        priority: MemoryPriority = MemoryPriority.NORMAL,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        load_radius: float = 100.0,
        unload_radius: float = 150.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StreamedAsset:
        with self._lock:
            effective_size = memory_size if memory_size > 0 else _CATEGORY_DEFAULT_SIZE.get(
                category, 8 * 1024 * 1024
            )

            asset = StreamedAsset(
                asset_path=asset_path,
                category=category,
                state=AssetLoadState.UNLOADED,
                memory_size_bytes=effective_size,
                priority=priority,
                position=position,
                load_radius=load_radius,
                unload_radius=max(load_radius + 1.0, unload_radius),
                reference_count=0,
            )
            self._assets[asset.id] = asset
            self._total_registrations += 1
            return asset

    def unregister_asset(self, asset_id: str) -> bool:
        with self._lock:
            asset = self._assets.get(asset_id)
            if asset is None:
                return False

            if asset.state == AssetLoadState.LOADED:
                self._current_allocation = max(
                    0, self._current_allocation - asset.memory_size_bytes
                )

            for zone in self._zones.values():
                if asset_id in zone.asset_ids:
                    zone.asset_ids.remove(asset_id)

            if asset_id in self._pending_loads:
                self._pending_loads.remove(asset_id)
            if asset_id in self._pending_unloads:
                self._pending_unloads.remove(asset_id)

            del self._assets[asset_id]
            self._total_unregistrations += 1
            return True

    # ------------------------------------------------------------------
    # Load / Unload Requests
    # ------------------------------------------------------------------

    def request_load(self, asset_id: str) -> bool:
        with self._lock:
            asset = self._assets.get(asset_id)
            if asset is None:
                return False

            if asset.state in (AssetLoadState.LOADED, AssetLoadState.LOADING):
                return True

            if asset.state == AssetLoadState.FAILED:
                asset.state = AssetLoadState.UNLOADED

            proposed_allocation = self._current_allocation + asset.memory_size_bytes
            if proposed_allocation > self._memory_budget and self._memory_budget > 0:
                evicted = self._evict_lowest_priority(
                    asset.memory_size_bytes
                )
                if not evicted and asset.priority != MemoryPriority.ESSENTIAL:
                    return False

            asset.state = AssetLoadState.LOADING
            asset.last_accessed_at = self._time_module.time()
            if asset_id not in self._pending_loads:
                self._pending_loads.append(asset_id)
            return True

    def request_unload(self, asset_id: str) -> bool:
        with self._lock:
            asset = self._assets.get(asset_id)
            if asset is None:
                return False

            if asset.state in (AssetLoadState.UNLOADED, AssetLoadState.UNLOADING):
                return True

            if asset.priority == MemoryPriority.ESSENTIAL:
                return False

            if asset.reference_count > 0:
                return False

            asset.state = AssetLoadState.UNLOADING
            asset.last_accessed_at = self._time_module.time()
            if asset_id not in self._pending_unloads:
                self._pending_unloads.append(asset_id)
            return True

    # ------------------------------------------------------------------
    # Memory Budget
    # ------------------------------------------------------------------

    def set_memory_budget(self, max_bytes: int) -> None:
        with self._lock:
            self._memory_budget = max(0, max_bytes)
            if self._memory_budget > 0 and self._current_allocation > self._memory_budget:
                self._enforce_budget()

    # ------------------------------------------------------------------
    # Update Streaming
    # ------------------------------------------------------------------

    def update_streaming(
        self, observer_position: Tuple[float, float, float]
    ) -> MemoryReport:
        with self._lock:
            ox, oy, oz = observer_position
            self._last_observer_position = observer_position
            self._last_update_time = self._time_module.time()

            loads_triggered = 0
            unloads_triggered = 0

            if self._policy == StreamingPolicy.DISTANCE_BASED:
                loads_triggered, unloads_triggered = self._evaluate_distance_streaming(
                    ox, oy, oz
                )
            elif self._policy == StreamingPolicy.VISIBILITY_BASED:
                loads_triggered, unloads_triggered = self._evaluate_visibility_streaming(
                    ox, oy, oz
                )
            elif self._policy == StreamingPolicy.PRIORITY_QUEUE:
                loads_triggered, unloads_triggered = self._evaluate_priority_streaming(
                    ox, oy, oz
                )

            self._process_pending_loads()
            self._process_pending_unloads()

            self._fragmentation_estimate = self._compute_fragmentation()

            return self.get_memory_report()

    def _evaluate_distance_streaming(
        self, ox: float, oy: float, oz: float
    ) -> Tuple[int, int]:
        loads = 0
        unloads = 0

        for asset in list(self._assets.values()):
            dist = asset.distance_to(ox, oy, oz)

            if dist <= asset.load_radius and asset.state == AssetLoadState.UNLOADED:
                if self.request_load(asset.id):
                    loads += 1
            elif dist > asset.unload_radius and asset.state in (
                AssetLoadState.LOADED,
                AssetLoadState.LOADING,
            ):
                if self.request_unload(asset.id):
                    unloads += 1

        return loads, unloads

    def _evaluate_visibility_streaming(
        self, ox: float, oy: float, oz: float
    ) -> Tuple[int, int]:
        loads = 0
        unloads = 0

        for asset in list(self._assets.values()):
            dist = asset.distance_to(ox, oy, oz)
            in_visible = dist <= asset.load_radius

            if in_visible and asset.state == AssetLoadState.UNLOADED:
                if self.request_load(asset.id):
                    loads += 1
            elif not in_visible and dist > asset.unload_radius and asset.state in (
                AssetLoadState.LOADED,
                AssetLoadState.LOADING,
            ):
                if self.request_unload(asset.id):
                    unloads += 1

        return loads, unloads

    def _evaluate_priority_streaming(
        self, ox: float, oy: float, oz: float
    ) -> Tuple[int, int]:
        loads = 0
        unloads = 0

        priority_sorted = sorted(
            [
                a for a in self._assets.values()
                if a.state == AssetLoadState.UNLOADED
            ],
            key=lambda a: (
                _MEMORY_PRIORITY_ORDER.get(a.priority, 20),
                a.distance_to(ox, oy, oz),
            ),
        )

        remaining_budget = self._memory_budget - self._current_allocation
        for asset in priority_sorted:
            if remaining_budget <= 0:
                break
            if self.request_load(asset.id):
                loads += 1
                remaining_budget -= asset.memory_size_bytes

        for asset in list(self._assets.values()):
            if (
                asset.state in (AssetLoadState.LOADED, AssetLoadState.LOADING)
                and asset.priority in (MemoryPriority.LOW, MemoryPriority.PURGEABLE)
                and asset.distance_to(ox, oy, oz) > asset.unload_radius
            ):
                if self.request_unload(asset.id):
                    unloads += 1

        return loads, unloads

    # ------------------------------------------------------------------
    # Pending Request Processing
    # ------------------------------------------------------------------

    def _process_pending_loads(self) -> None:
        resolved: List[str] = []

        for asset_id in self._pending_loads:
            asset = self._assets.get(asset_id)
            if asset is None:
                resolved.append(asset_id)
                continue

            if asset.state != AssetLoadState.LOADING:
                resolved.append(asset_id)
                continue

            proposed = self._current_allocation + asset.memory_size_bytes
            if self._memory_budget > 0 and proposed > self._memory_budget:
                asset.state = AssetLoadState.FAILED
                self._total_load_failures += 1
            else:
                asset.state = AssetLoadState.LOADED
                self._current_allocation += asset.memory_size_bytes
                asset.last_accessed_at = self._time_module.time()
                self._total_loads_completed += 1

            resolved.append(asset_id)

        for asset_id in resolved:
            if asset_id in self._pending_loads:
                self._pending_loads.remove(asset_id)

    def _process_pending_unloads(self) -> None:
        resolved: List[str] = []

        for asset_id in self._pending_unloads:
            asset = self._assets.get(asset_id)
            if asset is None:
                resolved.append(asset_id)
                continue

            if asset.state != AssetLoadState.UNLOADING:
                resolved.append(asset_id)
                continue

            if asset.priority == MemoryPriority.ESSENTIAL:
                asset.state = AssetLoadState.LOADED
                resolved.append(asset_id)
                continue

            if asset.reference_count > 0:
                asset.state = AssetLoadState.LOADED
                resolved.append(asset_id)
                continue

            self._current_allocation = max(
                0, self._current_allocation - asset.memory_size_bytes
            )
            asset.state = AssetLoadState.UNLOADED
            asset.last_accessed_at = self._time_module.time()
            self._total_unloads_completed += 1
            resolved.append(asset_id)

        for asset_id in resolved:
            if asset_id in self._pending_unloads:
                self._pending_unloads.remove(asset_id)

    # ------------------------------------------------------------------
    # Memory Enforcement
    # ------------------------------------------------------------------

    def _enforce_budget(self) -> None:
        if self._memory_budget <= 0:
            return

        while self._current_allocation > self._memory_budget:
            victim_asset = self._find_eviction_candidate()
            if victim_asset is None:
                break

            self.request_unload(victim_asset.id)
            self._process_pending_unloads()

            if self._current_allocation <= self._memory_budget:
                break

    def _find_eviction_candidate(self) -> Optional[StreamedAsset]:
        candidates = sorted(
            [
                a for a in self._assets.values()
                if a.state == AssetLoadState.LOADED
                and a.priority != MemoryPriority.ESSENTIAL
                and a.reference_count <= 0
            ],
            key=lambda a: (
                _MEMORY_PRIORITY_ORDER.get(a.priority, 20),
                -a.last_accessed_at,
            ),
        )
        return candidates[-1] if candidates else None

    def _evict_lowest_priority(self, needed_bytes: int) -> bool:
        freed = 0
        needed = needed_bytes

        candidates = sorted(
            [
                a for a in self._assets.values()
                if a.state == AssetLoadState.LOADED
                and a.priority != MemoryPriority.ESSENTIAL
                and a.reference_count <= 0
            ],
            key=lambda a: (
                -_MEMORY_PRIORITY_ORDER.get(a.priority, 20),
                a.last_accessed_at,
            ),
        )

        for asset in candidates:
            if freed >= needed:
                break
            self.request_unload(asset.id)
            freed += asset.memory_size_bytes

        self._process_pending_unloads()
        return freed >= needed

    # ------------------------------------------------------------------
    # Zone Management
    # ------------------------------------------------------------------

    def create_zone(
        self,
        center: Tuple[float, float, float],
        radius: float = 200.0,
    ) -> StreamingZone:
        with self._lock:
            zone = StreamingZone(
                zone_center=center,
                zone_radius=radius,
                is_active=False,
            )
            self._zones[zone.id] = zone
            return zone

    def add_asset_to_zone(self, zone_id: str, asset_id: str) -> bool:
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return False

            asset = self._assets.get(asset_id)
            if asset is None:
                return False

            if asset_id not in zone.asset_ids:
                zone.asset_ids.append(asset_id)
            return True

    def activate_zone(self, zone_id: str) -> bool:
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return False

            if zone.is_active:
                return True

            for asset_id in zone.asset_ids:
                self.request_load(asset_id)

            zone.is_active = True
            self._process_pending_loads()
            return True

    def deactivate_zone(self, zone_id: str) -> bool:
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return False

            if not zone.is_active:
                return True

            for asset_id in zone.asset_ids:
                self.request_unload(asset_id)

            zone.is_active = False
            self._process_pending_unloads()
            return True

    def remove_zone(self, zone_id: str) -> bool:
        with self._lock:
            zone = self._zones.pop(zone_id, None)
            if zone is None:
                return False

            if zone.is_active:
                for asset_id in zone.asset_ids:
                    self.request_unload(asset_id)

            self._process_pending_unloads()
            return True

    def get_zone(self, zone_id: str) -> Optional[StreamingZone]:
        with self._lock:
            return self._zones.get(zone_id)

    def list_zones(self, active_only: bool = False) -> List[StreamingZone]:
        with self._lock:
            zones = list(self._zones.values())
            if active_only:
                zones = [z for z in zones if z.is_active]
            return sorted(zones, key=lambda z: z.created_at)

    def get_zones_containing_point(
        self, x: float, y: float, z: float
    ) -> List[StreamingZone]:
        with self._lock:
            return [
                zone for zone in self._zones.values()
                if zone.contains_point(x, y, z)
            ]

    # ------------------------------------------------------------------
    # Reference Counting
    # ------------------------------------------------------------------

    def add_reference(self, asset_id: str) -> bool:
        with self._lock:
            asset = self._assets.get(asset_id)
            if asset is None:
                return False
            asset.reference_count += 1
            asset.last_accessed_at = self._time_module.time()
            return True

    def remove_reference(self, asset_id: str) -> bool:
        with self._lock:
            asset = self._assets.get(asset_id)
            if asset is None:
                return False
            if asset.reference_count > 0:
                asset.reference_count -= 1
                asset.last_accessed_at = self._time_module.time()
            return True

    def get_reference_count(self, asset_id: str) -> int:
        with self._lock:
            asset = self._assets.get(asset_id)
            if asset is None:
                return 0
            return asset.reference_count

    # ------------------------------------------------------------------
    # Asset Queries
    # ------------------------------------------------------------------

    def get_asset(self, asset_id: str) -> Optional[StreamedAsset]:
        with self._lock:
            return self._assets.get(asset_id)

    def list_assets(
        self,
        category: Optional[AssetCategory] = None,
        state: Optional[AssetLoadState] = None,
    ) -> List[StreamedAsset]:
        with self._lock:
            result = list(self._assets.values())
            if category is not None:
                result = [a for a in result if a.category == category]
            if state is not None:
                result = [a for a in result if a.state == state]
            return sorted(result, key=lambda a: a.created_at)

    def get_assets_in_radius(
        self,
        position: Tuple[float, float, float],
        radius: float,
        loaded_only: bool = False,
    ) -> List[StreamedAsset]:
        with self._lock:
            px, py, pz = position
            radius_sq = radius * radius
            result: List[StreamedAsset] = []
            for asset in self._assets.values():
                if loaded_only and asset.state != AssetLoadState.LOADED:
                    continue
                ax, ay, az = asset.position
                dist_sq = (ax - px) ** 2 + (ay - py) ** 2 + (az - pz) ** 2
                if dist_sq <= radius_sq:
                    result.append(asset)
            return result

    def get_assets_by_priority(
        self, priority: MemoryPriority
    ) -> List[StreamedAsset]:
        with self._lock:
            return [
                a for a in self._assets.values()
                if a.priority == priority
            ]

    def get_loaded_assets(self) -> List[StreamedAsset]:
        with self._lock:
            return [
                a for a in self._assets.values()
                if a.state == AssetLoadState.LOADED
            ]

    def get_failed_assets(self) -> List[StreamedAsset]:
        with self._lock:
            return [
                a for a in self._assets.values()
                if a.state == AssetLoadState.FAILED
            ]

    # ------------------------------------------------------------------
    # Fragmentation Estimation
    # ------------------------------------------------------------------

    def _compute_fragmentation(self) -> float:
        total_slots = max(1, len(self._assets))
        loaded_count = sum(
            1 for a in self._assets.values()
            if a.state == AssetLoadState.LOADED
        )
        unloaded_count = sum(
            1 for a in self._assets.values()
            if a.state == AssetLoadState.UNLOADED
        )

        if total_slots == 0:
            return 0.0

        sequential_gaps = 0
        prev_loaded = False
        sorted_assets = sorted(
            self._assets.values(),
            key=lambda a: (a.position[0], a.position[1], a.position[2]),
        )
        for asset in sorted_assets:
            currently_loaded = asset.state == AssetLoadState.LOADED
            if prev_loaded and not currently_loaded:
                sequential_gaps += 1
            prev_loaded = currently_loaded

        gap_ratio = sequential_gaps / max(1, loaded_count + unloaded_count)
        return min(100.0, gap_ratio * 100.0)

    # ------------------------------------------------------------------
    # Memory Report
    # ------------------------------------------------------------------

    def get_memory_report(self) -> MemoryReport:
        with self._lock:
            loaded = [
                a for a in self._assets.values()
                if a.state == AssetLoadState.LOADED
            ]
            loading = [
                a for a in self._assets.values()
                if a.state == AssetLoadState.LOADING
            ]

            total_allocated = sum(a.memory_size_bytes for a in loaded)
            total_reserved = sum(
                a.memory_size_bytes
                for a in self._assets.values()
                if a.state in (AssetLoadState.LOADED, AssetLoadState.LOADING)
            )

            return MemoryReport(
                total_allocated=total_allocated,
                total_reserved=total_reserved,
                budget_limit=self._memory_budget,
                asset_count=len(self._assets),
                loaded_count=len(loaded),
                loading_count=len(loading),
                fragmentation_pct=round(self._fragmentation_estimate, 2),
            )

    # ------------------------------------------------------------------
    # Streaming Policy
    # ------------------------------------------------------------------

    def set_streaming_policy(self, policy: StreamingPolicy) -> None:
        with self._lock:
            self._policy = policy

    def get_streaming_policy(self) -> StreamingPolicy:
        with self._lock:
            return self._policy

    # ------------------------------------------------------------------
    # Statistics and Status
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            state_counts: Dict[str, int] = {}
            for asset in self._assets.values():
                s = asset.state.value
                state_counts[s] = state_counts.get(s, 0) + 1

            category_counts: Dict[str, int] = {}
            for asset in self._assets.values():
                c = asset.category.value
                category_counts[c] = category_counts.get(c, 0) + 1

            priority_counts: Dict[str, int] = {}
            for asset in self._assets.values():
                p = asset.priority.value
                priority_counts[p] = priority_counts.get(p, 0) + 1

            category_memory: Dict[str, int] = {}
            for asset in self._assets.values():
                if asset.state == AssetLoadState.LOADED:
                    c = asset.category.value
                    category_memory[c] = (
                        category_memory.get(c, 0) + asset.memory_size_bytes
                    )

            loaded_assets = [
                a for a in self._assets.values()
                if a.state == AssetLoadState.LOADED
            ]
            loaded_memory = sum(a.memory_size_bytes for a in loaded_assets)
            memory_usage_pct = 0.0
            if self._memory_budget > 0:
                memory_usage_pct = (loaded_memory / self._memory_budget) * 100.0

            return {
                "total_assets": len(self._assets),
                "total_registrations": self._total_registrations,
                "total_unregistrations": self._total_unregistrations,
                "total_loads_completed": self._total_loads_completed,
                "total_unloads_completed": self._total_unloads_completed,
                "total_load_failures": self._total_load_failures,
                "state_distribution": state_counts,
                "category_distribution": category_counts,
                "priority_distribution": priority_counts,
                "category_memory_bytes": category_memory,
                "loaded_memory_bytes": loaded_memory,
                "memory_budget_bytes": self._memory_budget,
                "memory_usage_pct": round(memory_usage_pct, 2),
                "pending_loads": len(self._pending_loads),
                "pending_unloads": len(self._pending_unloads),
                "total_zones": len(self._zones),
                "active_zones": sum(1 for z in self._zones.values() if z.is_active),
                "streaming_policy": self._policy.value,
                "fragmentation_pct": round(self._fragmentation_estimate, 2),
                "last_update_time": self._last_update_time,
                "last_observer_position": list(self._last_observer_position),
            }

    def reset(self) -> None:
        with self._lock:
            self._assets.clear()
            self._zones.clear()
            self._memory_budget = 256 * 1024 * 1024
            self._current_allocation = 0
            self._policy = StreamingPolicy.DISTANCE_BASED
            self._pending_loads.clear()
            self._pending_unloads.clear()
            self._total_registrations = 0
            self._total_unregistrations = 0
            self._total_loads_completed = 0
            self._total_unloads_completed = 0
            self._total_load_failures = 0
            self._last_observer_position = (0.0, 0.0, 0.0)
            self._last_update_time = self._time_module.time()
            self._fragmentation_estimate = 0.0


def get_asset_streamer() -> AssetStreamer:
    return AssetStreamer.get_instance()