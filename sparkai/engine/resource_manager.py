"""
SparkLabs Engine - Resource Manager

Centralized asset loading, caching, and dependency tracking for
game resources. Manages the lifecycle of textures, audio clips,
fonts, tilemaps, and custom data files with reference counting
and lazy loading.

Architecture:
  ResourceManager
    |-- ResourceCache (LRU + TTL in-memory storage)
    |-- ResourceLoader (file I/O with format detection)
    |-- DependencyGraph (forward/reverse dependency edges)
    |-- ReferenceCounter (auto-unload on zero references)

Resource Types:
  - texture: sprites, backgrounds, UI images
  - audio: sfx clips, music tracks
  - font: bitmap and TTF fonts
  - tilemap: tile data and tileset references
  - data: JSON/YAML configuration files
  - script: game logic scripts

Usage:
    rm = ResourceManager(base_path="./assets")
    rm.load("sprite_player.png", resource_type="texture")
    tex = rm.get("sprite_player.png")
    rm.reference("sprite_player.png")  # increment ref count
    rm.release("sprite_player.png")    # decrement, auto-unload at 0
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ResourceType(Enum):
    TEXTURE = "texture"
    AUDIO = "audio"
    FONT = "font"
    TILEMAP = "tilemap"
    DATA = "data"
    SCRIPT = "script"
    ANIMATION = "animation"
    SHADER = "shader"
    CUSTOM = "custom"


class ResourceStatus(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    EVICTED = "evicted"


@dataclass
class ResourceHandle:
    resource_id: str = ""
    resource_type: ResourceType = ResourceType.CUSTOM
    path: str = ""
    data: Any = None
    status: ResourceStatus = ResourceStatus.UNLOADED
    ref_count: int = 0
    load_time_ms: float = 0.0
    last_accessed: float = 0.0
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)


class ResourceManager:
    """
    Asset lifecycle manager for game resources.

    Provides lazy loading, reference-counted caching, and
    dependency tracking. Automatically unloads resources
    when reference count drops to zero.

    Usage:
        rm = ResourceManager("./assets")
        
        # Load a sprite texture
        handle = rm.load("player.png", ResourceType.TEXTURE)
        
        # Get the loaded data
        texture_data = rm.get("player.png")
        
        # Increment reference count (another entity uses it)
        rm.reference("player.png")
        
        # When done, release 
        rm.release("player.png")  # unloads if refs reach 0
    """

    def __init__(
        self,
        base_path: str = ".",
        max_cache_size_mb: int = 512,
        max_handles: int = 10000,
    ):
        self._base_path = os.path.expanduser(base_path)
        self._max_cache_bytes = max_cache_size_mb * 1024 * 1024
        self._max_handles = max_handles
        self._handles: Dict[str, ResourceHandle] = {}
        self._total_loaded: int = 0
        self._total_evicted: int = 0
        self._total_load_time_ms: float = 0.0
        self._loaders: Dict[ResourceType, Callable[[str], Any]] = {}

    def register_loader(
        self, resource_type: ResourceType, loader: Callable[[str], Any],
    ) -> None:
        self._loaders[resource_type] = loader

    def load(
        self,
        resource_id: str,
        resource_type: ResourceType = ResourceType.CUSTOM,
        path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResourceHandle:
        existing = self._handles.get(resource_id)
        if existing and existing.status == ResourceStatus.LOADED:
            existing.last_accessed = time.time()
            existing.ref_count += 1
            return existing

        file_path = path or os.path.join(self._base_path, resource_id)

        handle = ResourceHandle(
            resource_id=resource_id,
            resource_type=resource_type,
            path=file_path,
            metadata=metadata or {},
        )

        start = time.monotonic()
        try:
            if resource_type in self._loaders:
                handle.data = self._loaders[resource_type](file_path)
            else:
                handle.data = self._load_default(file_path, resource_type)
            handle.status = ResourceStatus.LOADED
        except Exception:
            handle.status = ResourceStatus.FAILED

        elapsed = (time.monotonic() - start) * 1000.0
        handle.load_time_ms = elapsed
        handle.ref_count = 1
        handle.last_accessed = time.time()
        self._total_loaded += 1
        self._total_load_time_ms += elapsed

        self._handles[resource_id] = handle

        if len(self._handles) > self._max_handles:
            self._evict_lru(max(1, self._max_handles // 10))

        return handle

    def get(self, resource_id: str) -> Any:
        handle = self._handles.get(resource_id)
        if handle and handle.status == ResourceStatus.LOADED:
            handle.last_accessed = time.time()
            return handle.data
        return None

    def get_handle(self, resource_id: str) -> Optional[ResourceHandle]:
        return self._handles.get(resource_id)

    def reference(self, resource_id: str) -> int:
        handle = self._handles.get(resource_id)
        if handle and handle.status == ResourceStatus.LOADED:
            handle.ref_count += 1
            handle.last_accessed = time.time()
            return handle.ref_count
        return 0

    def release(self, resource_id: str) -> int:
        handle = self._handles.get(resource_id)
        if not handle:
            return 0
        handle.ref_count = max(0, handle.ref_count - 1)
        if handle.ref_count <= 0:
            self._unload(resource_id)
        return handle.ref_count

    def add_dependency(self, dependent: str, dependency: str) -> None:
        dh = self._handles.get(dependent)
        dep = self._handles.get(dependency)
        if dh and dep:
            dh.dependencies.add(dependency)
            dep.dependents.add(dependent)

    def get_dependencies(self, resource_id: str) -> List[str]:
        handle = self._handles.get(resource_id)
        if handle:
            return list(handle.dependencies)
        return []

    def unload(self, resource_id: str) -> bool:
        return self._unload(resource_id)

    def unload_all(self, resource_type: Optional[ResourceType] = None) -> int:
        count = 0
        to_unload = []
        for rid, handle in self._handles.items():
            if resource_type is None or handle.resource_type == resource_type:
                to_unload.append(rid)
        for rid in to_unload:
            if self._unload(rid):
                count += 1
        return count

    def preload(self, resource_ids: List[str]) -> int:
        count = 0
        for rid in resource_ids:
            try:
                self.load(rid)
                count += 1
            except Exception:
                pass
        return count

    def get_stats(self) -> dict:
        loaded = sum(
            1 for h in self._handles.values()
            if h.status == ResourceStatus.LOADED
        )
        total_size = sum(
            h.size_bytes for h in self._handles.values()
            if h.status == ResourceStatus.LOADED
        )
        return {
            "total_handles": len(self._handles),
            "loaded": loaded,
            "total_loaded_all_time": self._total_loaded,
            "evicted": self._total_evicted,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "avg_load_ms": round(
                self._total_load_time_ms / max(self._total_loaded, 1), 2,
            ),
            "base_path": self._base_path,
        }

    def clear(self) -> None:
        for rid in list(self._handles.keys()):
            self._unload(rid)
        self._total_loaded = 0
        self._total_evicted = 0
        self._total_load_time_ms = 0.0

    @staticmethod
    def _load_default(file_path: str, resource_type: ResourceType) -> Any:
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)
        ext = Path(file_path).suffix.lower()
        if ext in ('.json',):
            with open(file_path, 'r') as f:
                return json.load(f)
        if ext in ('.txt', '.md', '.yaml', '.yml', '.csv'):
            with open(file_path, 'r') as f:
                return f.read()
        with open(file_path, 'rb') as f:
            return f.read()

    def _unload(self, resource_id: str) -> bool:
        handle = self._handles.pop(resource_id, None)
        if not handle:
            return False
        handle.data = None
        handle.status = ResourceStatus.UNLOADED
        for dep_rid in handle.dependencies:
            self.release(dep_rid)
        self._total_evicted += 1
        return True

    def _evict_lru(self, count: int) -> None:
        loaded = [
            (rid, h) for rid, h in self._handles.items()
            if h.status == ResourceStatus.LOADED and h.ref_count <= 0
        ]
        loaded.sort(key=lambda x: x[1].last_accessed)
        for rid, handle in loaded[:count]:
            self._unload(rid)


_global_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = ResourceManager()
    return _global_resource_manager
