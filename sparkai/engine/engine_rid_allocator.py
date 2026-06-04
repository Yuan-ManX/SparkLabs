"""
SparkAI Engine - Resource ID Allocator

Efficient Resource ID (RID) allocation system providing lightweight
handle-based resource management. Each resource is identified by a
compact integer handle rather than direct object pointers, enabling
safe dereferencing, validation, and lifetime management.

Supports multiple resource types, ownership tracking, reference counting,
and bulk operations for maximum allocation throughput.
"""

from __future__ import annotations

import threading
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RIDResourceType(str, Enum):
    TEXTURE = "texture"
    SHADER = "shader"
    MATERIAL = "material"
    MESH = "mesh"
    AUDIO = "audio"
    FONT = "font"
    SCENE = "scene"
    NODE = "node"
    COMPONENT = "component"
    ANIMATION = "animation"
    PHYSICS_BODY = "physics_body"
    PARTICLE_EMITTER = "particle_emitter"
    TILE_MAP = "tile_map"
    SPRITE = "sprite"
    RENDER_TARGET = "render_target"
    CUSTOM = "custom"


class RIDState(str, Enum):
    FREE = "free"
    ALLOCATED = "allocated"
    REFERENCED = "referenced"
    PENDING_DELETE = "pending_delete"
    LOCKED = "locked"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class RIDHandle:
    """Lightweight resource identifier handle."""
    rid: int = 0
    resource_type: RIDResourceType = RIDResourceType.CUSTOM
    state: RIDState = RIDState.FREE
    ref_count: int = 0
    owner_id: str = ""
    created_at: float = 0.0
    last_accessed: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rid": self.rid,
            "resource_type": self.resource_type.value,
            "state": self.state.value,
            "ref_count": self.ref_count,
            "owner_id": self.owner_id,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "metadata": self.metadata,
        }


@dataclass
class RIDPoolStats:
    """Statistics for a resource type pool."""
    resource_type: str = ""
    total_allocated: int = 0
    total_free: int = 0
    total_referenced: int = 0
    peak_allocated: int = 0
    allocation_count: int = 0
    deallocation_count: int = 0
    pool_capacity: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "total_allocated": self.total_allocated,
            "total_free": self.total_free,
            "total_referenced": self.total_referenced,
            "peak_allocated": self.peak_allocated,
            "allocation_count": self.allocation_count,
            "deallocation_count": self.deallocation_count,
            "pool_capacity": self.pool_capacity,
            "utilization": round(
                (self.total_allocated / max(self.pool_capacity, 1)) * 100, 2
            ),
        }


# ---------------------------------------------------------------------------
# RID Allocator
# ---------------------------------------------------------------------------

class EngineRIDAllocator:
    """
    Resource ID allocation and management system.

    Provides compact integer handles for all engine resources, supporting
    safe allocation, reference counting, bulk operations, and pool-based
    resource management.
    """

    _instance: Optional["EngineRIDAllocator"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EngineRIDAllocator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineRIDAllocator":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        # Core RID storage: rid -> RIDHandle
        self._handles: Dict[int, RIDHandle] = {}
        # Free lists per resource type
        self._free_lists: Dict[RIDResourceType, List[int]] = {}
        # Pool capacities per type
        self._pool_capacities: Dict[RIDResourceType, int] = {
            RIDResourceType.TEXTURE: 10000,
            RIDResourceType.SHADER: 1000,
            RIDResourceType.MATERIAL: 5000,
            RIDResourceType.MESH: 20000,
            RIDResourceType.AUDIO: 5000,
            RIDResourceType.FONT: 1000,
            RIDResourceType.SCENE: 1000,
            RIDResourceType.NODE: 50000,
            RIDResourceType.COMPONENT: 100000,
            RIDResourceType.ANIMATION: 5000,
            RIDResourceType.PHYSICS_BODY: 10000,
            RIDResourceType.PARTICLE_EMITTER: 5000,
            RIDResourceType.TILE_MAP: 1000,
            RIDResourceType.SPRITE: 100000,
            RIDResourceType.RENDER_TARGET: 100,
            RIDResourceType.CUSTOM: 10000,
        }
        # Next RID counter per type
        self._next_rids: Dict[RIDResourceType, int] = {}
        # Initialize free lists
        for rtype in RIDResourceType:
            self._next_rids[rtype] = 1
            self._free_lists[rtype] = []

        self._total_allocations: int = 0
        self._total_deallocations: int = 0
        self._peak_handles: int = 0

    # ------------------------------------------------------------------
    # Allocation
    # ------------------------------------------------------------------

    def allocate(
        self, resource_type: RIDResourceType,
        owner_id: str = "", metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Allocate a new RID for the given resource type.
        Returns the integer RID handle.
        """
        with self._lock:
            # Try free list first
            free_list = self._free_lists[resource_type]
            if free_list:
                rid = free_list.pop()
            else:
                rid = self._next_rids[resource_type]
                self._next_rids[resource_type] += 1

            handle = RIDHandle(
                rid=rid,
                resource_type=resource_type,
                state=RIDState.ALLOCATED,
                owner_id=owner_id,
                created_at=_time_module.time(),
                last_accessed=_time_module.time(),
                metadata=metadata or {},
            )
            self._handles[rid] = handle
            self._total_allocations += 1
            self._peak_handles = max(self._peak_handles, len(self._handles))
            return rid

    def allocate_bulk(
        self, resource_type: RIDResourceType, count: int,
        owner_id: str = "",
    ) -> List[int]:
        """Allocate multiple RIDs at once."""
        with self._lock:
            rids: List[int] = []
            for _ in range(count):
                rid = self.allocate(resource_type, owner_id=owner_id)
                rids.append(rid)
            return rids

    def allocate_range(
        self, resource_type: RIDResourceType, count: int,
        owner_id: str = "",
    ) -> Tuple[int, int]:
        """Allocate a contiguous range of RIDs. Returns (start_rid, count)."""
        with self._lock:
            start = self._next_rids[resource_type]
            self._next_rids[resource_type] += count
            now = _time_module.time()
            for i in range(count):
                rid = start + i
                handle = RIDHandle(
                    rid=rid,
                    resource_type=resource_type,
                    state=RIDState.ALLOCATED,
                    owner_id=owner_id,
                    created_at=now,
                    last_accessed=now,
                )
                self._handles[rid] = handle
            self._total_allocations += count
            self._peak_handles = max(self._peak_handles, len(self._handles))
            return start, count

    # ------------------------------------------------------------------
    # Deallocation
    # ------------------------------------------------------------------

    def deallocate(self, rid: int) -> bool:
        """Deallocate a RID and return it to the free list."""
        with self._lock:
            handle = self._handles.get(rid)
            if not handle:
                return False
            if handle.state == RIDState.LOCKED:
                return False

            rtype = handle.resource_type
            handle.state = RIDState.FREE
            handle.owner_id = ""
            handle.ref_count = 0
            handle.metadata.clear()
            self._free_lists[rtype].append(rid)
            self._total_deallocations += 1
            return True

    def deallocate_bulk(self, rids: List[int]) -> int:
        """Deallocate multiple RIDs. Returns count of successfully deallocated."""
        with self._lock:
            count = 0
            for rid in rids:
                if self.deallocate(rid):
                    count += 1
            return count

    def deallocate_by_owner(self, owner_id: str) -> int:
        """Deallocate all RIDs owned by a specific owner."""
        with self._lock:
            to_free: List[int] = []
            for rid, handle in self._handles.items():
                if handle.owner_id == owner_id and handle.state != RIDState.LOCKED:
                    to_free.append(rid)
            return self.deallocate_bulk(to_free)

    # ------------------------------------------------------------------
    # Reference Counting
    # ------------------------------------------------------------------

    def add_reference(self, rid: int) -> bool:
        """Increment reference count for a RID."""
        with self._lock:
            handle = self._handles.get(rid)
            if not handle or handle.state == RIDState.FREE:
                return False
            handle.ref_count += 1
            handle.state = RIDState.REFERENCED
            handle.last_accessed = _time_module.time()
            return True

    def remove_reference(self, rid: int) -> int:
        """Decrement reference count. Returns remaining count."""
        with self._lock:
            handle = self._handles.get(rid)
            if not handle:
                return -1
            handle.ref_count = max(0, handle.ref_count - 1)
            if handle.ref_count == 0 and handle.state == RIDState.REFERENCED:
                handle.state = RIDState.ALLOCATED
            handle.last_accessed = _time_module.time()
            return handle.ref_count

    # ------------------------------------------------------------------
    # Validation & Query
    # ------------------------------------------------------------------

    def is_valid(self, rid: int) -> bool:
        """Check if a RID is valid and allocated."""
        with self._lock:
            handle = self._handles.get(rid)
            return (
                handle is not None
                and handle.state != RIDState.FREE
                and handle.state != RIDState.PENDING_DELETE
            )

    def get_handle(self, rid: int) -> Optional[RIDHandle]:
        """Get the handle for a RID."""
        with self._lock:
            return self._handles.get(rid)

    def get_type(self, rid: int) -> Optional[RIDResourceType]:
        """Get the resource type of a RID."""
        with self._lock:
            handle = self._handles.get(rid)
            return handle.resource_type if handle else None

    def lock(self, rid: int) -> bool:
        """Lock a RID to prevent deallocation."""
        with self._lock:
            handle = self._handles.get(rid)
            if not handle or handle.state == RIDState.FREE:
                return False
            handle.state = RIDState.LOCKED
            return True

    def unlock(self, rid: int) -> bool:
        """Unlock a RID."""
        with self._lock:
            handle = self._handles.get(rid)
            if not handle or handle.state != RIDState.LOCKED:
                return False
            handle.state = (
                RIDState.REFERENCED if handle.ref_count > 0
                else RIDState.ALLOCATED
            )
            return True

    def get_owner_rids(self, owner_id: str) -> List[int]:
        """Get all RIDs owned by an owner."""
        with self._lock:
            return [
                rid for rid, h in self._handles.items()
                if h.owner_id == owner_id and h.state != RIDState.FREE
            ]

    def get_type_rids(self, resource_type: RIDResourceType) -> List[int]:
        """Get all RIDs of a specific type."""
        with self._lock:
            return [
                rid for rid, h in self._handles.items()
                if h.resource_type == resource_type
                and h.state != RIDState.FREE
            ]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_pool_stats(self, resource_type: RIDResourceType) -> RIDPoolStats:
        """Get statistics for a resource type pool."""
        with self._lock:
            handles = [
                h for h in self._handles.values()
                if h.resource_type == resource_type
            ]
            allocated = [h for h in handles if h.state == RIDState.ALLOCATED]
            free_count = len(self._free_lists.get(resource_type, []))
            referenced = [h for h in handles if h.state == RIDState.REFERENCED]

            return RIDPoolStats(
                resource_type=resource_type.value,
                total_allocated=len(allocated),
                total_free=max(0, self._pool_capacities.get(resource_type, 0) - len(allocated) - len(referenced)),
                total_referenced=len(referenced),
                peak_allocated=self._peak_handles,
                allocation_count=len(handles),
                deallocation_count=free_count,
                pool_capacity=self._pool_capacities.get(resource_type, 0),
            )

    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall allocator statistics."""
        with self._lock:
            pools = {}
            for rtype in RIDResourceType:
                stats = self.get_pool_stats(rtype)
                pools[rtype.value] = stats.to_dict()

            return {
                "total_allocations": self._total_allocations,
                "total_deallocations": self._total_deallocations,
                "active_handles": len(self._handles),
                "peak_handles": self._peak_handles,
                "total_pools": len(self._pool_capacities),
                "pools": pools,
                "total_capacity": sum(self._pool_capacities.values()),
                "overall_utilization": round(
                    (len(self._handles) / max(sum(self._pool_capacities.values()), 1)) * 100, 2
                ),
            }

    def validate_system(self) -> Dict[str, Any]:
        """Validate the allocator's internal consistency."""
        with self._lock:
            issues: List[str] = []
            locked_orphans: List[int] = []
            stale_refs: List[int] = []

            for rid, handle in self._handles.items():
                if handle.state == RIDState.LOCKED and handle.ref_count == 0:
                    locked_orphans.append(rid)
                if handle.state == RIDState.REFERENCED and handle.ref_count == 0:
                    stale_refs.append(rid)

            if locked_orphans:
                issues.append(f"Found {len(locked_orphans)} locked orphan RIDs")
            if stale_refs:
                issues.append(f"Found {len(stale_refs)} stale referenced RIDs")

            return {
                "is_valid": len(issues) == 0,
                "issues": issues,
                "locked_orphans": locked_orphans,
                "stale_refs": stale_refs,
                "total_handles": len(self._handles),
                "free_lists_total": sum(len(fl) for fl in self._free_lists.values()),
            }

    def compact(self) -> int:
        """Compact the allocator by cleaning up stale handles. Returns count freed."""
        with self._lock:
            to_free: List[int] = []
            for rid, handle in self._handles.items():
                if handle.state == RIDState.PENDING_DELETE:
                    to_free.append(rid)
                elif (
                    handle.state == RIDState.ALLOCATED
                    and handle.ref_count == 0
                    and handle.owner_id == ""
                ):
                    to_free.append(rid)
            return self.deallocate_bulk(to_free)


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_rid_allocator() -> EngineRIDAllocator:
    return EngineRIDAllocator.get_instance()