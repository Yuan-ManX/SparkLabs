"""
SparkLabs Engine - Resource Loader

Structured resource preloading and caching system for
AI-generated game assets. Manages lifetime of textures,
audio clips, scripts, and data — with LRU eviction,
reference counting, and format auto-detection.

Architecture:
  ResourceLoader
    |-- ResourceHandle (ref-counted wrapper with load state)
    |-- ResourceCache (LRU eviction with configurable limits)
    |-- FormatDetector (extension-to-type mapping)
    |-- LoadQueue (priority-based progressive loading)

Resource States:
  - UNLOADED: registered but not loaded
  - LOADING: I/O in progress
  - LOADED: ready for use
  - ERROR: loading failed

Resource Types:
  - TEXTURE (.png, .jpg, .webp, .svg)
  - AUDIO (.wav, .mp3, .ogg)
  - SCRIPT (.py, .lua)
  - DATA (.json, .yaml, .csv, .toml)
  - FONT (.ttf, .otf, .woff2)
  - SHADER (.glsl, .wgsl)

Usage:
    rl = ResourceLoader(max_cache_mb=256)
    handle = rl.load("assets/player.png", resource_type="texture")
    rl.acquire("assets/player.png")  # bump ref count
    rl.release("assets/player.png")  # decrement ref count
    rl.preload_batch(["assets/bg.png", "assets/jump.wav"])
    stats = rl.get_cache_stats()
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ResourceState(Enum):
    UNLOADED = auto()
    LOADING = auto()
    LOADED = auto()
    ERROR = auto()
    EVICTED = auto()


class ResourceType(Enum):
    TEXTURE = auto()
    AUDIO = auto()
    SCRIPT = auto()
    DATA = auto()
    FONT = auto()
    SHADER = auto()
    PREFAB = auto()
    UNKNOWN = auto()


@dataclass
class ResourceHandle:
    path: str = ""
    resource_type: ResourceType = ResourceType.UNKNOWN
    state: ResourceState = ResourceState.UNLOADED
    data: Any = None
    size_bytes: int = 0
    ref_count: int = 0
    load_time_ms: float = 0.0
    last_access: float = 0.0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


EXTENSION_MAP: Dict[str, ResourceType] = {
    ".png": ResourceType.TEXTURE,
    ".jpg": ResourceType.TEXTURE,
    ".jpeg": ResourceType.TEXTURE,
    ".webp": ResourceType.TEXTURE,
    ".svg": ResourceType.TEXTURE,
    ".gif": ResourceType.TEXTURE,
    ".bmp": ResourceType.TEXTURE,
    ".wav": ResourceType.AUDIO,
    ".mp3": ResourceType.AUDIO,
    ".ogg": ResourceType.AUDIO,
    ".flac": ResourceType.AUDIO,
    ".py": ResourceType.SCRIPT,
    ".lua": ResourceType.SCRIPT,
    ".js": ResourceType.SCRIPT,
    ".ts": ResourceType.SCRIPT,
    ".json": ResourceType.DATA,
    ".yaml": ResourceType.DATA,
    ".yml": ResourceType.DATA,
    ".csv": ResourceType.DATA,
    ".toml": ResourceType.DATA,
    ".xml": ResourceType.DATA,
    ".ttf": ResourceType.FONT,
    ".otf": ResourceType.FONT,
    ".woff2": ResourceType.FONT,
    ".glsl": ResourceType.SHADER,
    ".wgsl": ResourceType.SHADER,
}


class ResourceCache:
    def __init__(self, max_size_bytes: int = 256 * 1024 * 1024):
        self._cache: Dict[str, ResourceHandle] = {}
        self._max_size = max_size_bytes
        self._current_size: int = 0
        self._hit_count: int = 0
        self._miss_count: int = 0

    def get(self, path: str) -> Optional[ResourceHandle]:
        handle = self._cache.get(path)
        if handle and handle.state == ResourceState.LOADED:
            handle.last_access = time.monotonic()
            self._hit_count += 1
            return handle
        self._miss_count += 1
        return None

    def put(self, path: str, handle: ResourceHandle) -> None:
        if path in self._cache:
            old = self._cache[path]
            self._current_size -= old.size_bytes

        while self._current_size + handle.size_bytes > self._max_size and self._cache:
            self._evict_lru()

        self._cache[path] = handle
        self._current_size += handle.size_bytes

    def remove(self, path: str) -> Optional[ResourceHandle]:
        handle = self._cache.pop(path, None)
        if handle:
            self._current_size -= handle.size_bytes
            handle.state = ResourceState.EVICTED
        return handle

    def _evict_lru(self) -> None:
        if not self._cache:
            return
        lru_path = min(self._cache, key=lambda p: self._cache[p].last_access)
        handle = self._cache.pop(lru_path, None)
        if handle:
            self._current_size -= handle.size_bytes
            handle.state = ResourceState.EVICTED

    def clear(self) -> int:
        count = len(self._cache)
        for handle in self._cache.values():
            handle.state = ResourceState.EVICTED
        self._cache.clear()
        self._current_size = 0
        return count

    @property
    def hit_rate(self) -> float:
        total = self._hit_count + self._miss_count
        return self._hit_count / total if total > 0 else 0.0

    @property
    def size_mb(self) -> float:
        return self._current_size / (1024 * 1024)


class LoadQueue:
    def __init__(self):
        self._queue: List[Tuple[str, int]] = []
        self._active: Set[str] = set()
        self._completed: Set[str] = set()
        self._failed: Set[str] = set()
        self._total: int = 0

    def enqueue(self, path: str, priority: int = 0) -> None:
        if path not in self._active and path not in self._completed:
            self._queue.append((path, priority))
            self._queue.sort(key=lambda x: x[1], reverse=True)

    def dequeue(self) -> Optional[str]:
        while self._queue:
            path, _ = self._queue.pop(0)
            if path not in self._completed and path not in self._failed:
                self._active.add(path)
                return path
        return None

    def mark_complete(self, path: str) -> None:
        self._active.discard(path)
        self._completed.add(path)
        self._total += 1

    def mark_failed(self, path: str) -> None:
        self._active.discard(path)
        self._failed.add(path)

    @property
    def pending(self) -> int:
        return len(self._queue) + len(self._active)

    @property
    def progress(self) -> float:
        done = len(self._completed) + len(self._failed)
        return done / max(self._total, 1)


class ResourceLoader:
    _instance: Optional["ResourceLoader"] = None

    def __init__(self, max_cache_mb: int = 256):
        self._cache = ResourceCache(max_size_bytes=max_cache_mb * 1024 * 1024)
        self._queue = LoadQueue()
        self._handles: Dict[str, ResourceHandle] = {}
        self._format_detector = EXTENSION_MAP
        self._load_callbacks: Dict[ResourceType, Callable] = {}
        self._total_loaded: int = 0
        self._total_failed: int = 0
        self._base_path: str = ""

    @classmethod
    def get_instance(cls) -> "ResourceLoader":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_base_path(self, path: str) -> None:
        self._base_path = path

    def _resolve_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        if self._base_path:
            return os.path.join(self._base_path, path)
        return path

    def detect_type(self, path: str) -> ResourceType:
        ext = os.path.splitext(path)[1].lower()
        return self._format_detector.get(ext, ResourceType.UNKNOWN)

    def acquire(self, path: str) -> Optional[ResourceHandle]:
        resolved = self._resolve_path(path)
        handle = self._cache.get(resolved)
        if handle:
            handle.ref_count += 1
            return handle
        return None

    def release(self, path: str) -> bool:
        resolved = self._resolve_path(path)
        handle = self._cache.get(resolved)
        if not handle:
            return False
        handle.ref_count = max(0, handle.ref_count - 1)
        if handle.ref_count == 0:
            self._cache.remove(resolved)
        return True

    def load(self, path: str, resource_type: Optional[ResourceType] = None) -> ResourceHandle:
        resolved = self._resolve_path(path)

        cached = self._cache.get(resolved)
        if cached:
            cached.ref_count += 1
            return cached

        rtype = resource_type or self.detect_type(resolved)
        start = time.monotonic()

        handle = ResourceHandle(
            path=resolved, resource_type=rtype,
            state=ResourceState.LOADING, ref_count=1,
            last_access=time.monotonic(),
        )

        try:
            data = self._load_simulated(resolved, rtype)
            elapsed = (time.monotonic() - start) * 1000

            handle.data = data
            handle.state = ResourceState.LOADED
            handle.size_bytes = len(str(data))
            handle.load_time_ms = elapsed

            self._cache.put(resolved, handle)
            self._handles[resolved] = handle
            self._total_loaded += 1

        except Exception as e:
            handle.state = ResourceState.ERROR
            handle.error_message = str(e)
            self._total_failed += 1

        return handle

    def preload_batch(
        self, paths: List[str], on_progress: Optional[Callable[[float], None]] = None
    ) -> Dict[str, ResourceHandle]:
        results: Dict[str, ResourceHandle] = {}
        total = len(paths)

        for i, path in enumerate(paths):
            handle = self.load(path)
            results[path] = handle
            if on_progress:
                on_progress((i + 1) / total)

        return results

    def unload(self, path: str) -> bool:
        resolved = self._resolve_path(path)
        if self._cache.remove(resolved):
            self._handles.pop(resolved, None)
            return True
        return False

    def unload_all(self) -> int:
        count = len(self._cache._cache)
        self._cache.clear()
        self._handles.clear()
        return count

    def get_handle(self, path: str) -> Optional[ResourceHandle]:
        resolved = self._resolve_path(path)
        return self._cache.get(resolved) or self._handles.get(resolved)

    def is_loaded(self, path: str) -> bool:
        handle = self.get_handle(path)
        return handle is not None and handle.state == ResourceState.LOADED

    def get_cache_stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._cache._cache),
            "size_mb": round(self._cache.size_mb, 2),
            "max_size_mb": self._cache._max_size // (1024 * 1024),
            "hit_rate": round(self._cache.hit_rate, 3),
            "hits": self._cache._hit_count,
            "misses": self._cache._miss_count,
        }

    def get_stats(self) -> Dict[str, Any]:
        loaded = sum(1 for h in self._handles.values() if h.state == ResourceState.LOADED)
        return {
            "total_loaded": self._total_loaded,
            "total_failed": self._total_failed,
            "currently_loaded": loaded,
            "known_extensions": len(EXTENSION_MAP),
            "cache": self.get_cache_stats(),
            "resources_by_type": {
                t.name.lower(): sum(1 for h in self._handles.values()
                                  if h.resource_type == t and h.state == ResourceState.LOADED)
                for t in ResourceType
            },
        }

    def _load_simulated(self, path: str, rtype: ResourceType) -> Any:
        return {
            "path": path,
            "type": rtype.name.lower(),
            "loaded_at": time.time(),
            "id": str(uuid.uuid4())[:8],
        }


def get_resource_loader() -> ResourceLoader:
    return ResourceLoader.get_instance()
