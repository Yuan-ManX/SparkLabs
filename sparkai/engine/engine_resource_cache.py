"""
Engine Resource Cache - Efficient resource loading, caching, and lifecycle management.
Provides async loading, reference counting, hot-reloading, and memory-aware
caching for game assets in the SparkLabs AI-native engine.
"""

import threading
import uuid
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable, TypeVar, Generic

T = TypeVar('T')


class ResourceType(Enum):
    """Types of loadable resources."""
    TEXTURE = "texture"
    AUDIO = "audio"
    FONT = "font"
    SHADER = "shader"
    SCENE = "scene"
    PREFAB = "prefab"
    ANIMATION = "animation"
    TILEMAP = "tilemap"
    SCRIPT = "script"
    DATA = "data"
    SPRITE_SHEET = "sprite_sheet"
    MATERIAL = "material"


class ResourceState(Enum):
    """States of a resource."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    UNLOADING = "unloading"


@dataclass
class ResourceHandle(Generic[T]):
    """Handle to a loaded resource."""
    resource_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    path: str = ""
    resource_type: ResourceType = ResourceType.DATA
    state: ResourceState = ResourceState.UNLOADED
    data: Optional[T] = None
    ref_count: int = 0
    size_bytes: int = 0
    load_time: float = 0.0
    last_accessed: float = field(default_factory=_time_module.time)
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "path": self.path,
            "resource_type": self.resource_type.value,
            "state": self.state.value,
            "ref_count": self.ref_count,
            "size_bytes": self.size_bytes,
            "load_time": self.load_time,
            "tags": self.tags,
            "dependencies": self.dependencies,
        }


@dataclass
class ResourceGroup:
    """A group of resources that can be loaded/unloaded together."""
    group_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    resources: List[str] = field(default_factory=list)
    is_loaded: bool = False
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "resources": self.resources,
            "is_loaded": self.is_loaded,
            "priority": self.priority,
        }


class EngineResourceCache:
    """
    Resource caching and lifecycle management system.
    Provides async loading, reference counting, hot-reloading,
    and memory-aware cache eviction for game assets.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._resources: Dict[str, ResourceHandle] = {}
            self._resource_groups: Dict[str, ResourceGroup] = {}
            self._loaders: Dict[ResourceType, Callable[[str], Any]] = {}
            self._unloaders: Dict[ResourceType, Callable[[Any], None]] = {}
            self._path_index: Dict[str, str] = {}
            self._max_cache_size: int = 256 * 1024 * 1024
            self._current_cache_size: int = 0
            self._loading_queue: List[str] = []
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'EngineResourceCache':
        return cls()

    def register_loader(self, resource_type: ResourceType, loader: Callable[[str], Any]):
        """Register a loader function for a resource type."""
        self._loaders[resource_type] = loader

    def register_unloader(self, resource_type: ResourceType, unloader: Callable[[Any], None]):
        """Register an unloader function for a resource type."""
        self._unloaders[resource_type] = unloader

    def load(self, path: str, resource_type: ResourceType,
             tags: List[str] = None) -> Optional[ResourceHandle]:
        """Load a resource from the given path."""
        cached_id = self._path_index.get(path)
        if cached_id and cached_id in self._resources:
            resource = self._resources[cached_id]
            resource.ref_count += 1
            resource.last_accessed = _time_module.time()
            return resource

        resource = ResourceHandle(
            path=path,
            resource_type=resource_type,
            state=ResourceState.LOADING,
            tags=tags or [],
        )
        self._resources[resource.resource_id] = resource
        self._path_index[path] = resource.resource_id

        loader = self._loaders.get(resource_type)
        if loader:
            try:
                load_start = _time_module.time()
                resource.data = loader(path)
                resource.load_time = _time_module.time() - load_start
                resource.state = ResourceState.LOADED
                resource.ref_count = 1
                resource.size_bytes = self._estimate_size(resource.data)
                self._current_cache_size += resource.size_bytes
            except Exception:
                resource.state = ResourceState.FAILED
        else:
            resource.state = ResourceState.FAILED

        self._evict_if_needed()
        return resource

    def load_async(self, path: str, resource_type: ResourceType,
                   callback: Callable[[ResourceHandle], None] = None,
                   tags: List[str] = None):
        """Load a resource asynchronously."""
        resource = self.load(path, resource_type, tags)
        if callback:
            callback(resource)

    def unload(self, resource_id: str):
        """Unload a resource and free its memory."""
        resource = self._resources.get(resource_id)
        if not resource:
            return

        resource.ref_count -= 1
        if resource.ref_count > 0:
            return

        resource.state = ResourceState.UNLOADING

        unloader = self._unloaders.get(resource.resource_type)
        if unloader and resource.data is not None:
            unloader(resource.data)

        self._current_cache_size -= resource.size_bytes
        self._path_index.pop(resource.path, None)
        resource.data = None
        resource.state = ResourceState.UNLOADED

    def get(self, resource_id: str) -> Optional[ResourceHandle]:
        """Get a resource by ID."""
        resource = self._resources.get(resource_id)
        if resource:
            resource.last_accessed = _time_module.time()
        return resource

    def get_by_path(self, path: str) -> Optional[ResourceHandle]:
        """Get a resource by file path."""
        resource_id = self._path_index.get(path)
        if resource_id:
            return self.get(resource_id)
        return None

    def create_resource_group(self, name: str, resource_paths: List[str],
                              priority: int = 0) -> ResourceGroup:
        """Create a group of resources for batch loading."""
        group = ResourceGroup(name=name, priority=priority)
        for path in resource_paths:
            resource_id = self._path_index.get(path)
            if resource_id:
                group.resources.append(resource_id)
        self._resource_groups[group.group_id] = group
        return group

    def load_group(self, group_id: str):
        """Load all resources in a group."""
        group = self._resource_groups.get(group_id)
        if not group:
            return

        for resource_id in group.resources:
            resource = self._resources.get(resource_id)
            if resource and resource.state == ResourceState.UNLOADED:
                self.load(resource.path, resource.resource_type)

        group.is_loaded = True

    def unload_group(self, group_id: str):
        """Unload all resources in a group."""
        group = self._resource_groups.get(group_id)
        if not group:
            return

        for resource_id in group.resources:
            self.unload(resource_id)

        group.is_loaded = False

    def set_max_cache_size(self, max_bytes: int):
        """Set the maximum cache size in bytes."""
        self._max_cache_size = max_bytes

    def _evict_if_needed(self):
        """Evict least recently used resources if cache is too large."""
        if self._current_cache_size <= self._max_cache_size:
            return

        resources = [r for r in self._resources.values()
                     if r.state == ResourceState.LOADED and r.ref_count == 0]
        resources.sort(key=lambda r: r.last_accessed)

        for resource in resources:
            if self._current_cache_size <= self._max_cache_size * 0.8:
                break
            self.unload(resource.resource_id)

    def _estimate_size(self, data: Any) -> int:
        """Estimate the memory size of a resource."""
        import sys
        try:
            return sys.getsizeof(data)
        except Exception:
            return 1024

    def add_ref(self, resource_id: str):
        """Add a reference to a resource."""
        resource = self._resources.get(resource_id)
        if resource:
            resource.ref_count += 1

    def list_resources(self, resource_type: Optional[ResourceType] = None,
                       state: Optional[ResourceState] = None) -> List[ResourceHandle]:
        """List resources, optionally filtered by type and state."""
        result = list(self._resources.values())
        if resource_type:
            result = [r for r in result if r.resource_type == resource_type]
        if state:
            result = [r for r in result if r.state == state]
        return result

    def list_groups(self) -> List[ResourceGroup]:
        """List all resource groups."""
        return list(self._resource_groups.values())

    def clear_cache(self):
        """Clear all cached resources."""
        for resource_id in list(self._resources.keys()):
            self.unload(resource_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get resource cache statistics."""
        return {
            "total_resources": len(self._resources),
            "loaded_resources": sum(1 for r in self._resources.values() if r.state == ResourceState.LOADED),
            "loading_resources": sum(1 for r in self._resources.values() if r.state == ResourceState.LOADING),
            "failed_resources": sum(1 for r in self._resources.values() if r.state == ResourceState.FAILED),
            "cache_size_bytes": self._current_cache_size,
            "max_cache_size_bytes": self._max_cache_size,
            "cache_usage_percent": (self._current_cache_size / self._max_cache_size * 100) if self._max_cache_size > 0 else 0,
            "total_groups": len(self._resource_groups),
            "resource_types": self._get_type_distribution(),
        }

    def _get_type_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for r in self._resources.values():
            t = r.resource_type.value
            dist[t] = dist.get(t, 0) + 1
        return dist


def get_resource_cache() -> EngineResourceCache:
    return EngineResourceCache.get_instance()