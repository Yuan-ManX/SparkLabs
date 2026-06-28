"""
SparkLabs Engine - Resource Streaming Engine

Asynchronous resource streaming system that enables large-scale game worlds
to load and unload resources dynamically based on player position and
visibility. Supports priority-based loading, preloading zones, and
graceful degradation for memory-constrained environments.

Architecture:
  ResourceStreamingEngine (Singleton)
    |-- StreamingZone (spatial region with associated resources)
    |-- ResourceRequest (load/unload request with priority)
    |-- StreamingScheduler (manages request queue and execution)
    |-- MemoryBudget (tracks and enforces memory limits)
    |-- PreloadPredictor (anticipates future resource needs)

Streaming Policies:
  - PROXIMITY: load based on distance from camera/player
  - VISIBILITY: load only visible resources
  - PRIORITY: load by resource priority
  - PREDICTIVE: preload based on movement prediction
  - BUDGETED: load within memory budget constraints

Usage:
    rs = ResourceStreamingEngine.get_instance()
    rs.initialize()

    rs.register_zone("zone_forest", bounds=(0, 0, 100, 100), resources=["tree_1", "rock_3"])
    rs.update_player_position("player_1", (50, 50))
    rs.process_frame()
    rs.shutdown()
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class StreamingPolicy(Enum):
    """Policies for resource streaming."""
    PROXIMITY = "proximity"       # Distance-based loading
    VISIBILITY = "visibility"     # Load only visible resources
    PRIORITY = "priority"         # Priority-based loading
    PREDICTIVE = "predictive"     # Preload based on prediction
    BUDGETED = "budgeted"         # Load within memory budget


class ResourceState(Enum):
    """States of a streamed resource."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    FAILED = "failed"
    CACHED = "cached"


class RequestPriority(Enum):
    """Priority levels for resource requests."""
    CRITICAL = 1    # Must load immediately (player character, UI)
    HIGH = 2        # Important for current view
    MEDIUM = 3      # Near future usefulness
    LOW = 4         # Background loading
    PRELOAD = 5     # Speculative preloading


class ZoneState(Enum):
    """States of a streaming zone."""
    INACTIVE = "inactive"
    PRELOADING = "preloading"
    ACTIVE = "active"
    UNLOADING = "unloading"
    CACHED = "cached"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class StreamingZone:
    """A spatial region with associated resources."""
    zone_id: str
    bounds: Tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
    resource_ids: List[str] = field(default_factory=list)
    state: ZoneState = ZoneState.INACTIVE
    priority: int = 0
    load_radius: float = 200.0
    unload_radius: float = 300.0
    center: Tuple[float, float] = (0.0, 0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def contains_point(self, point: Tuple[float, float]) -> bool:
        """Check if a point is within this zone."""
        x, y = point
        return self.bounds[0] <= x <= self.bounds[2] and self.bounds[1] <= y <= self.bounds[3]

    def distance_to(self, point: Tuple[float, float]) -> float:
        """Calculate distance from zone center to a point."""
        dx = self.center[0] - point[0]
        dy = self.center[1] - point[1]
        return math.sqrt(dx * dx + dy * dy)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "bounds": list(self.bounds),
            "resource_count": len(self.resource_ids),
            "resource_ids": self.resource_ids,
            "state": self.state.value,
            "priority": self.priority,
            "load_radius": self.load_radius,
            "unload_radius": self.unload_radius,
            "center": list(self.center),
            "metadata": self.metadata,
        }


@dataclass
class ResourceRequest:
    """A request to load or unload a resource."""
    request_id: str
    resource_id: str
    action: str  # "load" or "unload"
    priority: RequestPriority = RequestPriority.MEDIUM
    zone_id: str = ""
    callback: Optional[Callable[[str, bool], None]] = None
    created_at: float = field(default_factory=time.time)
    timeout_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "resource_id": self.resource_id,
            "action": self.action,
            "priority": self.priority.value,
            "zone_id": self.zone_id,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
        }


@dataclass
class MemoryBudget:
    """Memory budget tracking for resource management."""
    total_memory_mb: float = 1024.0
    used_memory_mb: float = 0.0
    reserved_memory_mb: float = 0.0
    warning_threshold: float = 0.75
    critical_threshold: float = 0.90
    resource_sizes: Dict[str, float] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)

    @property
    def available_memory_mb(self) -> float:
        return max(0.0, self.total_memory_mb - self.used_memory_mb - self.reserved_memory_mb)

    @property
    def usage_ratio(self) -> float:
        return (self.used_memory_mb + self.reserved_memory_mb) / max(self.total_memory_mb, 1.0)

    @property
    def is_warning(self) -> bool:
        return self.usage_ratio >= self.warning_threshold

    @property
    def is_critical(self) -> bool:
        return self.usage_ratio >= self.critical_threshold

    def can_allocate(self, size_mb: float) -> bool:
        return self.available_memory_mb >= size_mb

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_memory_mb": self.total_memory_mb,
            "used_memory_mb": self.used_memory_mb,
            "reserved_memory_mb": self.reserved_memory_mb,
            "available_memory_mb": self.available_memory_mb,
            "usage_ratio": self.usage_ratio,
            "is_warning": self.is_warning,
            "is_critical": self.is_critical,
        }


@dataclass
class StreamingStats:
    """Statistics for the streaming engine."""
    zones_active: int = 0
    zones_preloading: int = 0
    resources_loaded: int = 0
    resources_loading: int = 0
    requests_pending: int = 0
    requests_completed: int = 0
    requests_failed: int = 0
    total_loaded_mb: float = 0.0
    frames_processed: int = 0
    last_frame_time_ms: float = 0.0
    avg_frame_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zones_active": self.zones_active,
            "zones_preloading": self.zones_preloading,
            "resources_loaded": self.resources_loaded,
            "resources_loading": self.resources_loading,
            "requests_pending": self.requests_pending,
            "requests_completed": self.requests_completed,
            "requests_failed": self.requests_failed,
            "total_loaded_mb": self.total_loaded_mb,
            "frames_processed": self.frames_processed,
            "last_frame_time_ms": self.last_frame_time_ms,
            "avg_frame_time_ms": self.avg_frame_time_ms,
        }


# =============================================================================
# Resource Streaming Engine
# =============================================================================


class ResourceStreamingEngine:
    """
    Asynchronous resource streaming engine for large game worlds.
    Manages dynamic loading/unloading of resources based on spatial proximity.
    """

    _instance: Optional["ResourceStreamingEngine"] = None
    _instance_lock = threading.RLock()

    # Default resource size estimates in MB
    _DEFAULT_RESOURCE_SIZES: Dict[str, float] = {
        "texture": 4.0,
        "mesh": 2.0,
        "audio": 3.0,
        "animation": 1.0,
        "prefab": 0.5,
        "shader": 0.1,
        "material": 0.1,
        "tilemap": 8.0,
        "level": 50.0,
    }

    def __init__(self) -> None:
        if ResourceStreamingEngine._instance is not None:
            raise RuntimeError("Use ResourceStreamingEngine.get_instance()")
        self._initialized: bool = False
        self._zones: Dict[str, StreamingZone] = {}
        self._resources: Dict[str, ResourceState] = {}
        self._resource_zones: Dict[str, List[str]] = defaultdict(list)
        self._request_queue: List[ResourceRequest] = []
        self._active_requests: Dict[str, ResourceRequest] = {}
        self._completed_requests: deque = deque(maxlen=200)
        self._player_positions: Dict[str, Tuple[float, float]] = {}
        self._budget = MemoryBudget()
        self._stats = StreamingStats()
        self._policy = StreamingPolicy.PROXIMITY
        self._load_callbacks: Dict[str, Callable] = {}
        self._unload_callbacks: Dict[str, Callable] = {}
        self._max_loads_per_frame: int = 10
        self._max_unloads_per_frame: int = 5
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "ResourceStreamingEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, total_memory_mb: float = 1024.0,
                   max_loads_per_frame: int = 10,
                   max_unloads_per_frame: int = 5,
                   policy: StreamingPolicy = StreamingPolicy.PROXIMITY) -> None:
        """Initialize the resource streaming engine."""
        with self._lock:
            if self._initialized:
                return
            self._budget.total_memory_mb = total_memory_mb
            self._max_loads_per_frame = max_loads_per_frame
            self._max_unloads_per_frame = max_unloads_per_frame
            self._policy = policy
            self._initialized = True

    def register_zone(self, zone_id: str, bounds: Tuple[float, float, float, float],
                      resource_ids: Optional[List[str]] = None,
                      priority: int = 0, load_radius: float = 200.0,
                      unload_radius: float = 300.0) -> StreamingZone:
        """Register a streaming zone with the engine."""
        with self._lock:
            center_x = (bounds[0] + bounds[2]) / 2.0
            center_y = (bounds[1] + bounds[3]) / 2.0

            zone = StreamingZone(
                zone_id=zone_id,
                bounds=bounds,
                resource_ids=resource_ids or [],
                priority=priority,
                load_radius=load_radius,
                unload_radius=unload_radius,
                center=(center_x, center_y),
            )
            self._zones[zone_id] = zone

            for rid in zone.resource_ids:
                if rid not in self._resources:
                    self._resources[rid] = ResourceState.UNLOADED
                self._resource_zones[rid].append(zone_id)

            return zone

    def register_resource(self, resource_id: str, resource_type: str = "texture",
                          size_mb: Optional[float] = None,
                          load_callback: Optional[Callable[[str], bool]] = None,
                          unload_callback: Optional[Callable[[str], bool]] = None) -> None:
        """Register a resource with the streaming engine."""
        with self._lock:
            if resource_id not in self._resources:
                self._resources[resource_id] = ResourceState.UNLOADED

            if size_mb is None:
                size_mb = self._DEFAULT_RESOURCE_SIZES.get(resource_type, 1.0)
            self._budget.resource_sizes[resource_id] = size_mb

            if load_callback:
                self._load_callbacks[resource_id] = load_callback
            if unload_callback:
                self._unload_callbacks[resource_id] = unload_callback

    def update_player_position(self, player_id: str, position: Tuple[float, float]) -> None:
        """Update a player's position for proximity-based streaming."""
        with self._lock:
            self._player_positions[player_id] = position

    def process_frame(self, delta_time: float = 0.016) -> Dict[str, Any]:
        """Process one frame of streaming operations."""
        with self._lock:
            start_time = time.time()

            # 1. Evaluate zone states based on player positions
            self._evaluate_zones()

            # 2. Generate load/unload requests
            self._generate_requests()

            # 3. Sort requests by priority
            self._request_queue.sort(key=lambda r: r.priority.value)

            # 4. Process load requests (limited per frame)
            loads_processed = 0
            unloads_processed = 0
            new_requests: List[ResourceRequest] = []

            for request in self._request_queue:
                if request.action == "load" and loads_processed < self._max_loads_per_frame:
                    if self._process_load_request(request):
                        loads_processed += 1
                        continue
                elif request.action == "unload" and unloads_processed < self._max_unloads_per_frame:
                    if self._process_unload_request(request):
                        unloads_processed += 1
                        continue
                new_requests.append(request)

            self._request_queue = new_requests

            # 5. Update stats
            frame_time = (time.time() - start_time) * 1000.0
            self._stats.frames_processed += 1
            self._stats.last_frame_time_ms = frame_time
            self._stats.avg_frame_time_ms = (
                (self._stats.avg_frame_time_ms * (self._stats.frames_processed - 1) + frame_time)
                / self._stats.frames_processed
            )
            self._stats.requests_pending = len(self._request_queue)
            self._budget.last_updated = time.time()

            return {
                "loads_processed": loads_processed,
                "unloads_processed": unloads_processed,
                "pending_requests": len(self._request_queue),
                "frame_time_ms": frame_time,
                "budget": self._budget.to_dict(),
            }

    def _evaluate_zones(self) -> None:
        """Evaluate zone states based on player proximity."""
        if not self._player_positions:
            return

        # Find closest player to each zone
        for zone in self._zones.values():
            min_distance = float("inf")
            for pos in self._player_positions.values():
                dist = zone.distance_to(pos)
                if dist < min_distance:
                    min_distance = dist

            if min_distance <= zone.load_radius:
                if zone.state in (ZoneState.INACTIVE, ZoneState.CACHED):
                    zone.state = ZoneState.PRELOADING
                    self._stats.zones_preloading += 1
                elif zone.state == ZoneState.PRELOADING:
                    zone.state = ZoneState.ACTIVE
                    self._stats.zones_active += 1
                    self._stats.zones_preloading = max(0, self._stats.zones_preloading - 1)
            elif min_distance > zone.unload_radius:
                if zone.state == ZoneState.ACTIVE:
                    zone.state = ZoneState.UNLOADING
                    self._stats.zones_active = max(0, self._stats.zones_active - 1)
                elif zone.state == ZoneState.UNLOADING:
                    zone.state = ZoneState.INACTIVE
            elif min_distance > zone.load_radius:
                if zone.state == ZoneState.ACTIVE:
                    zone.state = ZoneState.UNLOADING
                    self._stats.zones_active = max(0, self._stats.zones_active - 1)

    def _generate_requests(self) -> None:
        """Generate load/unload requests based on zone states."""
        for zone in self._zones.values():
            if zone.state == ZoneState.PRELOADING or zone.state == ZoneState.ACTIVE:
                for rid in zone.resource_ids:
                    state = self._resources.get(rid, ResourceState.UNLOADED)
                    if state == ResourceState.UNLOADED:
                        # Check if already queued
                        if not any(r.resource_id == rid and r.action == "load"
                                   for r in self._request_queue):
                            self._request_queue.append(ResourceRequest(
                                request_id=uuid.uuid4().hex[:12],
                                resource_id=rid,
                                action="load",
                                priority=RequestPriority.MEDIUM,
                                zone_id=zone.zone_id,
                            ))

            elif zone.state == ZoneState.UNLOADING:
                for rid in zone.resource_ids:
                    state = self._resources.get(rid, ResourceState.UNLOADED)
                    if state == ResourceState.LOADED:
                        # Check if needed by any active zone
                        needed = False
                        for other_zone in self._zones.values():
                            if other_zone.state in (ZoneState.ACTIVE, ZoneState.PRELOADING):
                                if rid in other_zone.resource_ids:
                                    needed = True
                                    break
                        if not needed:
                            if not any(r.resource_id == rid and r.action == "unload"
                                       for r in self._request_queue):
                                self._request_queue.append(ResourceRequest(
                                    request_id=uuid.uuid4().hex[:12],
                                    resource_id=rid,
                                    action="unload",
                                    priority=RequestPriority.LOW,
                                    zone_id=zone.zone_id,
                                ))

    def _process_load_request(self, request: ResourceRequest) -> bool:
        """Process a resource load request."""
        rid = request.resource_id
        size = self._budget.resource_sizes.get(rid, 1.0)

        # Check memory budget
        if not self._budget.can_allocate(size):
            if request.retry_count < request.max_retries:
                request.retry_count += 1
                return False
            self._stats.requests_failed += 1
            return True  # Remove from queue

        # Mark as loading
        self._resources[rid] = ResourceState.LOADING
        self._budget.reserved_memory_mb += size
        self._stats.resources_loading += 1

        # Execute load callback
        callback = self._load_callbacks.get(rid)
        if callback:
            try:
                success = callback(rid)
            except Exception:
                success = False
        else:
            success = True  # Simulated load

        if success:
            self._resources[rid] = ResourceState.LOADED
            self._budget.used_memory_mb += size
            self._budget.reserved_memory_mb -= size
            self._stats.resources_loaded += 1
            self._stats.resources_loading = max(0, self._stats.resources_loading - 1)
            self._stats.total_loaded_mb += size
            self._stats.requests_completed += 1
        else:
            self._resources[rid] = ResourceState.FAILED
            self._budget.reserved_memory_mb -= size
            self._stats.resources_loading = max(0, self._stats.resources_loading - 1)
            self._stats.requests_failed += 1

        return True  # Remove from queue

    def _process_unload_request(self, request: ResourceRequest) -> bool:
        """Process a resource unload request."""
        rid = request.resource_id

        if self._resources.get(rid) != ResourceState.LOADED:
            return True  # Already unloaded, remove from queue

        # Mark as unloading
        self._resources[rid] = ResourceState.UNLOADING

        # Execute unload callback
        callback = self._unload_callbacks.get(rid)
        if callback:
            try:
                success = callback(rid)
            except Exception:
                success = False
        else:
            success = True

        if success:
            self._resources[rid] = ResourceState.UNLOADED
            size = self._budget.resource_sizes.get(rid, 1.0)
            self._budget.used_memory_mb = max(0.0, self._budget.used_memory_mb - size)
            self._stats.resources_loaded = max(0, self._stats.resources_loaded - 1)
            self._stats.total_loaded_mb = max(0.0, self._stats.total_loaded_mb - size)
            self._stats.requests_completed += 1
        else:
            self._resources[rid] = ResourceState.LOADED  # Restore

        return True

    def preload_zone(self, zone_id: str) -> bool:
        """Force preload a specific zone."""
        with self._lock:
            zone = self._zones.get(zone_id)
            if not zone:
                return False
            zone.state = ZoneState.PRELOADING
            for rid in zone.resource_ids:
                if rid in self._resources and self._resources[rid] == ResourceState.UNLOADED:
                    self._request_queue.append(ResourceRequest(
                        request_id=uuid.uuid4().hex[:12],
                        resource_id=rid,
                        action="load",
                        priority=RequestPriority.HIGH,
                        zone_id=zone_id,
                    ))
            return True

    def unload_zone(self, zone_id: str) -> bool:
        """Force unload a specific zone."""
        with self._lock:
            zone = self._zones.get(zone_id)
            if not zone:
                return False
            zone.state = ZoneState.UNLOADING
            for rid in zone.resource_ids:
                if rid in self._resources and self._resources[rid] == ResourceState.LOADED:
                    self._request_queue.append(ResourceRequest(
                        request_id=uuid.uuid4().hex[:12],
                        resource_id=rid,
                        action="unload",
                        priority=RequestPriority.HIGH,
                        zone_id=zone_id,
                    ))
            return True

    def set_memory_budget(self, total_mb: float) -> None:
        """Update the total memory budget."""
        with self._lock:
            self._budget.total_memory_mb = total_mb

    def set_policy(self, policy: StreamingPolicy) -> None:
        """Change the streaming policy."""
        with self._lock:
            self._policy = policy

    def get_zone(self, zone_id: str) -> Optional[StreamingZone]:
        """Get a streaming zone by ID."""
        return self._zones.get(zone_id)

    def create_zone(self, zone_name: str, priority: int = 1,
                    bounds: Optional[Tuple[float, float, float, float]] = None,
                    resource_ids: Optional[List[str]] = None) -> StreamingZone:
        """Create a new streaming zone with auto-generated bounds."""
        with self._lock:
            if bounds is None:
                idx = len(self._zones)
                bounds = (float(idx * 100), 0.0, float(idx * 100 + 100), 100.0)
            return self.register_zone(
                zone_id=zone_name,
                bounds=bounds,
                resource_ids=resource_ids or [],
                priority=priority,
            )

    def list_zones(self) -> List[StreamingZone]:
        """List all registered zones."""
        return list(self._zones.values())

    def get_resource_state(self, resource_id: str) -> Optional[ResourceState]:
        """Get the current state of a resource."""
        return self._resources.get(resource_id)

    def get_status(self) -> Dict[str, Any]:
        """Get engine status and statistics."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "policy": self._policy.value,
                "zone_count": len(self._zones),
                "resource_count": len(self._resources),
                "player_count": len(self._player_positions),
                "budget": self._budget.to_dict(),
                "stats": self._stats.to_dict(),
                "zones": [z.to_dict() for z in self._zones.values()],
            }

    def shutdown(self) -> None:
        """Shutdown the streaming engine."""
        with self._lock:
            self._zones.clear()
            self._resources.clear()
            self._resource_zones.clear()
            self._request_queue.clear()
            self._active_requests.clear()
            self._completed_requests.clear()
            self._player_positions.clear()
            self._load_callbacks.clear()
            self._unload_callbacks.clear()
            self._initialized = False


def get_resource_streaming_engine() -> ResourceStreamingEngine:
    """Get the ResourceStreamingEngine singleton instance."""
    return ResourceStreamingEngine.get_instance()