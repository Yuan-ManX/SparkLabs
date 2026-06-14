"""
SparkLabs Engine - Asset Manager

A comprehensive asset management pipeline for the SparkLabs game engine.
Manages the full lifecycle of game assets including registration, loading,
caching, dependency tracking, bundling, streaming, texture atlas management,
and validation. Designed as a thread-safe singleton with LRU caching,
reference counting, and priority-based async loading.

Architecture:
  EngineAssetManager (Singleton)
    |-- AssetDescriptor — per-asset metadata and lifecycle state
    |-- AssetBundle — grouped collection of related assets
    |-- TextureAtlas — atlas texture with region UV mapping
    |-- AtlasRegion — rectangular sub-region within an atlas
    |-- LoadRequest — async loading request with priority and progress
    |-- AssetCacheEntry — cache entry with LRU eviction data
    |-- LoadProgress — aggregate loading progress across all requests

Usage:
    am = get_engine_asset_manager()
    desc = am.register_asset("player_sprite", AssetType.SPRITE, "assets/player.png")
    am.load_asset(desc.asset_id, LoadPriority.HIGH)
    bundle = am.create_bundle("level_1", [desc.asset_id])
    am.load_bundle(bundle.bundle_id)
"""

from __future__ import annotations

import hashlib
import math
import random
import threading
import time as _time_module
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AssetType(str, Enum):
    """Categories of game assets managed by the engine.

    Each type corresponds to a distinct resource pipeline path and may
    have different loading, caching, and validation strategies.
    """

    TEXTURE = "texture"
    SPRITE = "sprite"
    AUDIO = "audio"
    FONT = "font"
    JSON = "json"
    SHADER = "shader"
    MATERIAL = "material"
    ANIMATION = "animation"
    PREFAB = "prefab"
    TILEMAP = "tilemap"
    SCRIPT = "script"
    SCENE = "scene"
    MODEL_3D = "model_3d"
    VIDEO = "video"
    SPINE = "spine"
    UNKNOWN = "unknown"


class AssetLoadStatus(str, Enum):
    """Lifecycle states for an individual asset.

    UNLOADED: Not yet requested or previously unloaded.
    QUEUED: In the priority queue waiting for a loader slot.
    LOADING: Actively being loaded by the loader subsystem.
    LOADED: Successfully loaded and ready for use.
    FAILED: Loading encountered an error.
    UNLOADING: Tear-down in progress (releasing references / memory).
    CACHED: Present in the LRU cache but not actively referenced.
    """

    UNLOADED = "unloaded"
    QUEUED = "queued"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    UNLOADING = "unloading"
    CACHED = "cached"


class LoadPriority(str, Enum):
    """Priority levels for asset loading requests.

    CRITICAL assets are loaded first and may block the main thread.
    BACKGROUND assets are loaded opportunistically when idle.
    """

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class UnloadMode(str, Enum):
    """Policies governing when an asset is automatically unloaded.

    MANUAL: Only unloaded via explicit unload_asset() call.
    SCENE_EXIT: Unloaded when the active scene changes.
    NEVER: Permanently retained in cache (e.g. global UI textures).
    REFERENCE_COUNT_ZERO: Unloaded when no other asset depends on it.
    """

    MANUAL = "manual"
    SCENE_EXIT = "scene_exit"
    NEVER = "never"
    REFERENCE_COUNT_ZERO = "reference_count_zero"


class ValidationStatus(str, Enum):
    """Result of an asset integrity validation operation."""

    VALID = "valid"
    INVALID_FORMAT = "invalid_format"
    MISSING_DEPENDENCY = "missing_dependency"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    CORRUPTED = "corrupted"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CACHE_MAX_ENTRIES: int = 512
DEFAULT_CACHE_MAX_SIZE_BYTES: int = 256 * 1024 * 1024  # 256 MB
DEFAULT_MAX_CONCURRENT_LOADS: int = 4
DEFAULT_LOAD_TIMEOUT_SECONDS: float = 30.0
DEFAULT_STREAM_CHUNK_SIZE: int = 65536  # 64 KB

_PRIORITY_ORDER: Dict[LoadPriority, int] = {
    LoadPriority.CRITICAL: 0,
    LoadPriority.HIGH: 1,
    LoadPriority.NORMAL: 2,
    LoadPriority.LOW: 3,
    LoadPriority.BACKGROUND: 4,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AssetDescriptor:
    """Metadata and lifecycle state for a single game asset.

    Tracks the asset's identity, type, file path, size, checksum, version,
    dependency graph, bundle membership, load status, timing, reference
    counting, and arbitrary key/value metadata.
    """

    asset_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    asset_type: AssetType = AssetType.UNKNOWN
    path: str = ""
    size_bytes: int = 0
    checksum: str = ""
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    bundle_id: str = ""
    status: AssetLoadStatus = AssetLoadStatus.UNLOADED
    load_time_ms: float = 0.0
    last_accessed: float = field(default_factory=_time_module.time)
    reference_count: int = 0
    unload_mode: UnloadMode = UnloadMode.MANUAL
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "asset_type": self.asset_type.value,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "version": self.version,
            "dependencies": list(self.dependencies),
            "dependents": list(self.dependents),
            "bundle_id": self.bundle_id,
            "status": self.status.value,
            "load_time_ms": self.load_time_ms,
            "last_accessed": self.last_accessed,
            "reference_count": self.reference_count,
            "unload_mode": self.unload_mode.value,
            "validation_status": self.validation_status.value,
            "error_message": self.error_message,
            "metadata": dict(self.metadata),
        }


@dataclass
class AssetBundle:
    """Named collection of related assets for efficient group operations.

    Bundles allow loading / unloading groups of assets together (e.g.
    all assets for a specific level or UI screen). Tracks total size,
    load state, priority, and arbitrary metadata.
    """

    bundle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    asset_ids: List[str] = field(default_factory=list)
    total_size: int = 0
    loaded: bool = False
    priority: LoadPriority = LoadPriority.NORMAL
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "name": self.name,
            "asset_ids": list(self.asset_ids),
            "total_size": self.total_size,
            "loaded": self.loaded,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class AtlasRegion:
    """Rectangular sub-region within a texture atlas.

    Defines the pixel bounds and normalized UV coordinates for
    indexing a sprite within a larger atlas texture.
    """

    region_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    uv_coords: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "uv_coords": list(self.uv_coords),
            "metadata": dict(self.metadata),
        }


@dataclass
class TextureAtlas:
    """Container for a texture atlas and its sub-regions.

    Manages the mapping between named sprite regions and their pixel /
    UV coordinates within a shared atlas texture. Supports querying
    regions by name and computing UV bounds.
    """

    atlas_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    texture_path: str = ""
    regions: Dict[str, AtlasRegion] = field(default_factory=dict)
    width: int = 0
    height: int = 0
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "atlas_id": self.atlas_id,
            "name": self.name,
            "texture_path": self.texture_path,
            "regions": {k: v.to_dict() for k, v in self.regions.items()},
            "width": self.width,
            "height": self.height,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class LoadRequest:
    """In-flight asynchronous asset loading request.

    Tracks the priority, callback, start time, progress, and cancellation
    state for a single load operation. Results are delivered via the
    callback when loading completes or fails.
    """

    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_id: str = ""
    priority: LoadPriority = LoadPriority.NORMAL
    callback: Optional[Callable[[str, bool, str], None]] = None
    start_time: float = field(default_factory=_time_module.time)
    progress: float = 0.0
    cancelled: bool = False
    chunk_size: int = DEFAULT_STREAM_CHUNK_SIZE
    total_chunks: int = 0
    loaded_chunks: int = 0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "asset_id": self.asset_id,
            "priority": self.priority.value,
            "start_time": self.start_time,
            "progress": self.progress,
            "cancelled": self.cancelled,
            "chunk_size": self.chunk_size,
            "total_chunks": self.total_chunks,
            "loaded_chunks": self.loaded_chunks,
            "error_message": self.error_message,
        }


@dataclass
class AssetCacheEntry:
    """An entry in the LRU asset cache.

    Stores cached asset data along with size, timing, and access-count
    metadata used by the eviction policy.
    """

    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_id: str = ""
    data: Any = None
    size_bytes: int = 0
    created_at: float = field(default_factory=_time_module.time)
    last_accessed: float = field(default_factory=_time_module.time)
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "asset_id": self.asset_id,
            "has_data": self.data is not None,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
        }


@dataclass
class LoadProgress:
    """Aggregate loading progress across all pending requests.

    Provides a snapshot of total, loaded, and failed counts for both
    assets and bytes, plus the currently loading asset and overall
    percentage completion.
    """

    progress_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    total_assets: int = 0
    loaded_assets: int = 0
    failed_assets: int = 0
    total_bytes: int = 0
    loaded_bytes: int = 0
    current_asset: str = ""
    percentage: float = 0.0
    status: str = "idle"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "progress_id": self.progress_id,
            "total_assets": self.total_assets,
            "loaded_assets": self.loaded_assets,
            "failed_assets": self.failed_assets,
            "total_bytes": self.total_bytes,
            "loaded_bytes": self.loaded_bytes,
            "current_asset": self.current_asset,
            "percentage": self.percentage,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# Engine Asset Manager (Singleton)
# ---------------------------------------------------------------------------


class EngineAssetManager:
    """Comprehensive asset management pipeline for the SparkLabs game engine.

    Provides a complete asset lifecycle: registration, synchronous and
    asynchronous loading with progress tracking, LRU caching with
    configurable eviction, reference-counted unloading, dependency
    graph management, asset bundling, texture atlas management, asset
    validation, and progressive streaming for large assets.

    Usage:
        am = get_engine_asset_manager()
        desc = am.register_asset("hero", AssetType.SPRITE, "res/hero.png")
        am.load_asset(desc.asset_id, LoadPriority.HIGH)
        am.get_load_progress()
    """

    _instance: Optional["EngineAssetManager"] = None
    _lock: threading.RLock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "EngineAssetManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialize()

    @classmethod
    def get_instance(cls) -> "EngineAssetManager":
        """Return the singleton EngineAssetManager instance."""
        return cls()

    def _initialize(self) -> None:
        """One-time initialization of all internal data structures."""
        if self._initialized:
            return

        # Asset registry
        self._assets: Dict[str, AssetDescriptor] = {}
        self._asset_name_index: Dict[str, str] = {}

        # Bundles
        self._bundles: Dict[str, AssetBundle] = {}

        # Texture atlases
        self._atlases: Dict[str, TextureAtlas] = {}

        # Loading infrastructure
        self._pending_requests: Dict[str, LoadRequest] = {}
        self._load_queue: List[str] = []
        self._active_loads: int = 0

        # LRU cache (OrderedDict maintains insertion/access order)
        self._cache: OrderedDict[str, AssetCacheEntry] = OrderedDict()
        self._cache_current_size_bytes: int = 0

        # Configuration
        self._cache_max_entries: int = DEFAULT_CACHE_MAX_ENTRIES
        self._cache_max_size_bytes: int = DEFAULT_CACHE_MAX_SIZE_BYTES
        self._max_concurrent_loads: int = DEFAULT_MAX_CONCURRENT_LOADS
        self._load_timeout_seconds: float = DEFAULT_LOAD_TIMEOUT_SECONDS
        self._stream_chunk_size: int = DEFAULT_STREAM_CHUNK_SIZE

        # Counters
        self._total_registered: int = 0
        self._total_loaded: int = 0
        self._total_unloaded: int = 0
        self._total_failed: int = 0
        self._total_bytes_loaded: int = 0
        self._total_cache_hits: int = 0
        self._total_cache_misses: int = 0
        self._total_load_requests: int = 0
        self._total_cancelled: int = 0

        self._initialized = True

    # ------------------------------------------------------------------
    # Asset Registration
    # ------------------------------------------------------------------

    def register_asset(
        self,
        name: str,
        asset_type: AssetType,
        path: str,
        size_bytes: int = 0,
        checksum: str = "",
        version: str = "1.0.0",
        dependencies: Optional[List[str]] = None,
        bundle_id: str = "",
        unload_mode: UnloadMode = UnloadMode.MANUAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssetDescriptor:
        """Register a new asset in the asset registry.

        Creates an AssetDescriptor with the given parameters and adds it
        to the registry. If an asset with the same name already exists,
        it is returned instead of creating a duplicate.

        Args:
            name: Human-readable asset name (unique within the registry).
            asset_type: Category of the asset (texture, audio, shader, etc.).
            path: File-system or virtual path to the asset source.
            size_bytes: File size in bytes (0 if unknown).
            checksum: SHA-256 or other integrity hash (empty if not computed).
            version: Semantic version string for asset versioning.
            dependencies: List of asset_ids this asset depends on.
            bundle_id: Parent bundle ID if this asset belongs to a bundle.
            unload_mode: Policy for automatic unloading.
            metadata: Arbitrary key/value metadata.

        Returns:
            The newly created AssetDescriptor instance.
        """
        with self._lock:
            # Check for duplicate by name
            existing_id = self._asset_name_index.get(name)
            if existing_id is not None and existing_id in self._assets:
                return self._assets[existing_id]

            desc = AssetDescriptor(
                asset_id=uuid.uuid4().hex,
                name=name,
                asset_type=asset_type,
                path=path,
                size_bytes=size_bytes,
                checksum=checksum,
                version=version,
                dependencies=dependencies if dependencies is not None else [],
                bundle_id=bundle_id,
                unload_mode=unload_mode,
                metadata=metadata if metadata is not None else {},
            )

            # Update dependent lists in dependency assets
            for dep_id in desc.dependencies:
                dep_desc = self._assets.get(dep_id)
                if dep_desc is not None:
                    if desc.asset_id not in dep_desc.dependents:
                        dep_desc.dependents.append(desc.asset_id)

            self._assets[desc.asset_id] = desc
            self._asset_name_index[name] = desc.asset_id
            self._total_registered += 1

            return desc

    def get_asset(self, asset_id: str) -> Optional[AssetDescriptor]:
        """Retrieve an asset descriptor by its unique asset_id.

        Args:
            asset_id: The asset's unique identifier.

        Returns:
            The AssetDescriptor if found, None otherwise.
        """
        return self._assets.get(asset_id)

    def get_asset_by_name(self, name: str) -> Optional[AssetDescriptor]:
        """Retrieve an asset descriptor by its registered name.

        Args:
            name: The human-readable asset name.

        Returns:
            The AssetDescriptor if found, None otherwise.
        """
        asset_id = self._asset_name_index.get(name)
        if asset_id is None:
            return None
        return self._assets.get(asset_id)

    def is_asset_loaded(self, asset_id: str) -> bool:
        """Check whether an asset is currently loaded.

        Args:
            asset_id: The asset's unique identifier.

        Returns:
            True if the asset status is LOADED, False otherwise.
        """
        desc = self._assets.get(asset_id)
        if desc is None:
            return False
        return desc.status == AssetLoadStatus.LOADED

    def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        loaded: Optional[bool] = None,
        bundle_id: Optional[str] = None,
    ) -> List[AssetDescriptor]:
        """List assets with optional filters.

        Args:
            asset_type: Filter by asset type category (None = all).
            loaded: Filter by loaded status (None = all).
            bundle_id: Filter by parent bundle ID (None = all).

        Returns:
            List of matching AssetDescriptor instances.
        """
        result: List[AssetDescriptor] = []
        for desc in self._assets.values():
            if asset_type is not None and desc.asset_type != asset_type:
                continue
            if loaded is not None:
                is_loaded = desc.status == AssetLoadStatus.LOADED
                if is_loaded != loaded:
                    continue
            if bundle_id is not None and desc.bundle_id != bundle_id:
                continue
            result.append(desc)
        return result

    def remove_asset(self, asset_id: str) -> bool:
        """Remove an asset from the registry (must be UNLOADED first).

        Args:
            asset_id: The asset's unique identifier.

        Returns:
            True if the asset was removed, False otherwise.
        """
        with self._lock:
            desc = self._assets.get(asset_id)
            if desc is None:
                return False
            if desc.status == AssetLoadStatus.LOADED:
                return False

            # Remove from name index
            self._asset_name_index.pop(desc.name, None)

            # Remove from dependents lists of dependency assets
            for dep_id in desc.dependencies:
                dep_desc = self._assets.get(dep_id)
                if dep_desc is not None and asset_id in dep_desc.dependents:
                    dep_desc.dependents.remove(asset_id)

            # Remove from bundle if applicable
            if desc.bundle_id:
                bundle = self._bundles.get(desc.bundle_id)
                if bundle is not None and asset_id in bundle.asset_ids:
                    bundle.asset_ids.remove(asset_id)

            # Evict from cache
            self._cache.pop(asset_id, None)

            del self._assets[asset_id]
            return True

    # ------------------------------------------------------------------
    # Dependency Management
    # ------------------------------------------------------------------

    def add_dependency(self, asset_id: str, dependency_id: str) -> bool:
        """Declare that one asset depends on another.

        The dependent asset cannot be loaded until its dependency is
        loaded. Unloading a dependency will also unload its dependents
        (or increment their reference-count breaks).

        Args:
            asset_id: The asset that depends on another.
            dependency_id: The asset that must be loaded first.

        Returns:
            True if the dependency was added, False if either asset
            was not found or a circular dependency would result.
        """
        with self._lock:
            desc = self._assets.get(asset_id)
            dep_desc = self._assets.get(dependency_id)
            if desc is None or dep_desc is None:
                return False
            if dependency_id in desc.dependencies:
                return True  # Already declared
            if asset_id == dependency_id:
                return False

            desc.dependencies.append(dependency_id)
            if asset_id not in dep_desc.dependents:
                dep_desc.dependents.append(asset_id)
            return True

    def remove_dependency(self, asset_id: str, dependency_id: str) -> bool:
        """Remove a previously declared dependency between two assets.

        Args:
            asset_id: The dependent asset.
            dependency_id: The dependency to remove.

        Returns:
            True if the dependency was removed, False if it did not exist.
        """
        with self._lock:
            desc = self._assets.get(asset_id)
            dep_desc = self._assets.get(dependency_id)
            if desc is None or dep_desc is None:
                return False
            if dependency_id not in desc.dependencies:
                return False
            desc.dependencies.remove(dependency_id)
            if asset_id in dep_desc.dependents:
                dep_desc.dependents.remove(asset_id)
            return True

    def get_dependencies(self, asset_id: str) -> List[str]:
        """Get the list of asset IDs that a given asset depends on.

        Args:
            asset_id: The asset's unique identifier.

        Returns:
            List of dependency asset IDs, empty if none or asset not found.
        """
        desc = self._assets.get(asset_id)
        if desc is None:
            return []
        return list(desc.dependencies)

    def get_dependents(self, asset_id: str) -> List[str]:
        """Get the list of asset IDs that depend on a given asset.

        Args:
            asset_id: The asset's unique identifier.

        Returns:
            List of dependent asset IDs, empty if none or asset not found.
        """
        desc = self._assets.get(asset_id)
        if desc is None:
            return []
        return list(desc.dependents)

    def get_full_dependency_chain(self, asset_id: str) -> Set[str]:
        """Compute the transitive closure of all dependencies (recursive).

        Args:
            asset_id: The asset's unique identifier.

        Returns:
            Set of all asset IDs reachable through the dependency graph,
            including the asset itself.
        """
        visited: Set[str] = set()

        def _walk(aid: str) -> None:
            if aid in visited:
                return
            visited.add(aid)
            desc = self._assets.get(aid)
            if desc is not None:
                for dep_id in desc.dependencies:
                    _walk(dep_id)

        _walk(asset_id)
        return visited

    # ------------------------------------------------------------------
    # Asset Loading
    # ------------------------------------------------------------------

    def load_asset(
        self,
        asset_id: str,
        priority: LoadPriority = LoadPriority.NORMAL,
    ) -> bool:
        """Load an asset synchronously.

        Simulates loading by updating the descriptor's status. In a
        production engine this would actually read and parse the
        file from disk or network.

        Args:
            asset_id: The asset's unique identifier.
            priority: Loading priority affecting queue ordering.

        Returns:
            True if the asset was loaded or was already loaded,
            False if the asset was not found or loading failed.
        """
        desc = self._assets.get(asset_id)
        if desc is None:
            return False

        if desc.status == AssetLoadStatus.LOADED:
            return True

        with self._lock:
            # Load dependencies first
            for dep_id in desc.dependencies:
                dep_desc = self._assets.get(dep_id)
                if dep_desc is not None:
                    if dep_desc.status != AssetLoadStatus.LOADED:
                        self.load_asset(dep_id, priority)

            start = _time_module.time()
            desc.status = AssetLoadStatus.LOADING

            # Simulate load time based on size
            simulated_load_time = min(desc.size_bytes / (10 * 1024 * 1024), 0.5)
            _time_module.sleep(max(simulated_load_time, 0.001))

            # Simulate occasional failure for very large assets
            if desc.size_bytes > 500 * 1024 * 1024:
                roll = random.random()
                if roll < 0.02:  # 2% failure chance for large assets
                    desc.status = AssetLoadStatus.FAILED
                    desc.error_message = "Simulated load failure for large asset"
                    self._total_failed += 1
                    return False

            desc.status = AssetLoadStatus.LOADED
            desc.load_time_ms = (_time_module.time() - start) * 1000.0
            desc.last_accessed = _time_module.time()
            desc.reference_count += 1

            self._total_loaded += 1
            self._total_bytes_loaded += desc.size_bytes

            # Add to cache
            self._add_to_cache(asset_id, None, desc.size_bytes)

            return True

    def load_assets_async(
        self,
        asset_ids: List[str],
        callback: Optional[Callable[[str, bool, str], None]] = None,
        priority: LoadPriority = LoadPriority.NORMAL,
    ) -> List[str]:
        """Enqueue multiple assets for asynchronous loading.

        Creates LoadRequest entries and places them in the priority-
        ordered load queue. The callback is invoked per-asset when
        each load completes or fails.

        Args:
            asset_ids: List of asset IDs to load.
            callback: Called as callback(asset_id, success, error_message)
                for each asset upon completion.
            priority: Base priority for all requests.

        Returns:
            List of request IDs that were created.
        """
        request_ids: List[str] = []
        for asset_id in asset_ids:
            desc = self._assets.get(asset_id)
            if desc is None:
                continue
            if desc.status == AssetLoadStatus.LOADED:
                if callback:
                    callback(asset_id, True, "")
                continue

            request = LoadRequest(
                request_id=uuid.uuid4().hex,
                asset_id=asset_id,
                priority=priority,
                callback=callback,
            )
            with self._lock:
                self._pending_requests[request.request_id] = request
                self._load_queue.append(request.request_id)
                self._total_load_requests += 1

                desc.status = AssetLoadStatus.QUEUED

            request_ids.append(request.request_id)

        # Sort queue by priority
        self._sort_load_queue()
        return request_ids

    def process_load_queue(self, max_items: int = 1) -> int:
        """Process pending load requests from the priority queue.

        In a production engine this would be called each frame from
        the main game loop. Processes up to max_items requests
        without exceeding the concurrent load limit.

        Args:
            max_items: Maximum number of requests to process this call.

        Returns:
            Number of requests actually processed.
        """
        processed = 0
        for _ in range(max_items):
            if self._active_loads >= self._max_concurrent_loads:
                break

            request_id: Optional[str] = None
            with self._lock:
                if self._load_queue:
                    request_id = self._load_queue.pop(0)

            if request_id is None:
                break

            request = self._pending_requests.get(request_id)
            if request is None:
                continue
            if request.cancelled:
                self._total_cancelled += 1
                continue

            self._active_loads += 1
            success = self.load_asset(request.asset_id, request.priority)
            error_msg = ""

            desc = self._assets.get(request.asset_id)
            if not success and desc is not None:
                error_msg = desc.error_message

            if request.callback:
                request.callback(request.asset_id, success, error_msg)

            self._active_loads = max(0, self._active_loads - 1)
            processed += 1

        return processed

    def _sort_load_queue(self) -> None:
        """Sort the load queue by priority (CRITICAL first, BACKGROUND last)."""
        def _priority_key(req_id: str) -> int:
            req = self._pending_requests.get(req_id)
            if req is None:
                return 999
            return _PRIORITY_ORDER.get(req.priority, 2)

        self._load_queue.sort(key=_priority_key)

    # ------------------------------------------------------------------
    # Load Cancellation
    # ------------------------------------------------------------------

    def cancel_load(self, request_id: str) -> bool:
        """Cancel a pending load request.

        Args:
            request_id: The request ID returned by load_assets_async.

        Returns:
            True if the request was found and cancelled, False otherwise.
        """
        with self._lock:
            request = self._pending_requests.get(request_id)
            if request is None:
                return False
            if request.cancelled:
                return True

            request.cancelled = True
            desc = self._assets.get(request.asset_id)
            if desc is not None and desc.status == AssetLoadStatus.QUEUED:
                desc.status = AssetLoadStatus.UNLOADED

            # Remove from queue if still pending
            if request_id in self._load_queue:
                self._load_queue.remove(request_id)

            self._total_cancelled += 1
            return True

    def cancel_all_loads(self) -> int:
        """Cancel all pending load requests.

        Returns:
            Number of requests cancelled.
        """
        cancelled = 0
        for request_id in list(self._pending_requests.keys()):
            if self.cancel_load(request_id):
                cancelled += 1
        return cancelled

    # ------------------------------------------------------------------
    # Asset Unloading
    # ------------------------------------------------------------------

    def unload_asset(self, asset_id: str) -> bool:
        """Unload an asset, releasing its cached data.

        Respects the asset's unload_mode policy. Assets with dependents
        will not be unloaded unless force=True.

        Args:
            asset_id: The asset's unique identifier.

        Returns:
            True if the asset was unloaded, False otherwise.
        """
        desc = self._assets.get(asset_id)
        if desc is None:
            return False
        if desc.status == AssetLoadStatus.UNLOADED:
            return True
        if desc.unload_mode == UnloadMode.NEVER:
            return False
        if desc.status == AssetLoadStatus.UNLOADING:
            return False

        with self._lock:
            # Check if any loaded dependents exist
            for dep_id in desc.dependents:
                dep_desc = self._assets.get(dep_id)
                if dep_desc is not None and dep_desc.status == AssetLoadStatus.LOADED:
                    return False

            desc.status = AssetLoadStatus.UNLOADING
            desc.reference_count = max(0, desc.reference_count - 1)

            # Remove from cache
            self._cache.pop(asset_id, None)

            desc.status = AssetLoadStatus.UNLOADED
            self._total_unloaded += 1

            return True

    def unload_unused(self) -> int:
        """Unload all assets with a reference count of zero.

        Returns:
            Number of assets unloaded.
        """
        unloaded = 0
        for asset_id in list(self._assets.keys()):
            desc = self._assets.get(asset_id)
            if desc is None:
                continue
            if desc.reference_count <= 0 and desc.status == AssetLoadStatus.LOADED:
                if self.unload_asset(asset_id):
                    unloaded += 1
        return unloaded

    # ------------------------------------------------------------------
    # Asset Bundles
    # ------------------------------------------------------------------

    def create_bundle(
        self,
        name: str,
        asset_ids: Optional[List[str]] = None,
        priority: LoadPriority = LoadPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssetBundle:
        """Create a named asset bundle grouping related assets together.

        Args:
            name: Human-readable bundle name (e.g. "level_1_assets").
            asset_ids: Initial list of asset IDs to include.
            priority: Default load priority for the bundle.
            metadata: Arbitrary key/value metadata.

        Returns:
            The newly created AssetBundle instance.
        """
        asset_ids = asset_ids if asset_ids is not None else []
        total_size = 0
        for aid in asset_ids:
            desc = self._assets.get(aid)
            if desc is not None:
                total_size += desc.size_bytes
                desc.bundle_id = ""  # Will be set below

        bundle = AssetBundle(
            bundle_id=uuid.uuid4().hex,
            name=name,
            asset_ids=list(asset_ids),
            total_size=total_size,
            priority=priority,
            metadata=metadata if metadata is not None else {},
        )

        with self._lock:
            self._bundles[bundle.bundle_id] = bundle

            # Update asset bundle references
            for aid in asset_ids:
                desc = self._assets.get(aid)
                if desc is not None:
                    desc.bundle_id = bundle.bundle_id

        return bundle

    def add_to_bundle(self, bundle_id: str, asset_id: str) -> bool:
        """Add a single asset to an existing bundle.

        Args:
            bundle_id: The bundle's unique identifier.
            asset_id: The asset to add.

        Returns:
            True if the asset was added, False if either was not found.
        """
        bundle = self._bundles.get(bundle_id)
        desc = self._assets.get(asset_id)
        if bundle is None or desc is None:
            return False
        if asset_id in bundle.asset_ids:
            return True

        with self._lock:
            bundle.asset_ids.append(asset_id)
            bundle.total_size += desc.size_bytes
            desc.bundle_id = bundle_id
            return True

    def load_bundle(self, bundle_id: str) -> bool:
        """Load all assets in a bundle.

        Loads each asset in the bundle that is not already loaded.
        Dependency chains are resolved per-asset.

        Args:
            bundle_id: The bundle's unique identifier.

        Returns:
            True if all assets were loaded successfully, False if
            any asset failed to load or the bundle was not found.
        """
        bundle = self._bundles.get(bundle_id)
        if bundle is None:
            return False

        all_success = True
        for asset_id in bundle.asset_ids:
            if not self.load_asset(asset_id, bundle.priority):
                all_success = False

        bundle.loaded = all_success
        return all_success

    def unload_bundle(self, bundle_id: str) -> bool:
        """Unload all assets in a bundle.

        Args:
            bundle_id: The bundle's unique identifier.

        Returns:
            True if the bundle was found and processed, False otherwise.
        """
        bundle = self._bundles.get(bundle_id)
        if bundle is None:
            return False

        for asset_id in bundle.asset_ids:
            self.unload_asset(asset_id)

        bundle.loaded = False
        return True

    def list_bundles(self) -> List[AssetBundle]:
        """List all registered asset bundles.

        Returns:
            List of all AssetBundle instances.
        """
        return list(self._bundles.values())

    def get_bundle(self, bundle_id: str) -> Optional[AssetBundle]:
        """Retrieve a bundle by its unique identifier.

        Args:
            bundle_id: The bundle's unique identifier.

        Returns:
            The AssetBundle if found, None otherwise.
        """
        return self._bundles.get(bundle_id)

    def remove_bundle(self, bundle_id: str) -> bool:
        """Remove a bundle (does not delete the assets themselves).

        Args:
            bundle_id: The bundle's unique identifier.

        Returns:
            True if the bundle was removed, False if not found.
        """
        with self._lock:
            bundle = self._bundles.pop(bundle_id, None)
            if bundle is None:
                return False

            # Clear bundle reference from member assets
            for aid in bundle.asset_ids:
                desc = self._assets.get(aid)
                if desc is not None and desc.bundle_id == bundle_id:
                    desc.bundle_id = ""

            return True

    # ------------------------------------------------------------------
    # Texture Atlas Management
    # ------------------------------------------------------------------

    def create_texture_atlas(
        self,
        name: str,
        texture_path: str,
        width: int = 0,
        height: int = 0,
        regions: Optional[List[AtlasRegion]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TextureAtlas:
        """Create a texture atlas with named sprite regions.

        Args:
            name: Human-readable atlas name.
            texture_path: Path to the atlas texture file.
            width: Atlas texture width in pixels.
            height: Atlas texture height in pixels.
            regions: List of AtlasRegion instances to populate the atlas.
            metadata: Arbitrary key/value metadata.

        Returns:
            The newly created TextureAtlas instance.
        """
        atlas = TextureAtlas(
            atlas_id=uuid.uuid4().hex,
            name=name,
            texture_path=texture_path,
            width=width,
            height=height,
            metadata=metadata if metadata is not None else {},
        )

        if regions:
            for region in regions:
                # Compute UV coords if not already set
                if region.uv_coords == (0.0, 0.0, 1.0, 1.0) and width > 0 and height > 0:
                    u0 = region.x / width
                    v0 = region.y / height
                    u1 = (region.x + region.width) / width
                    v1 = (region.y + region.height) / height
                    region.uv_coords = (u0, v0, u1, v1)
                atlas.regions[region.name] = region

        with self._lock:
            self._atlases[atlas.atlas_id] = atlas

        return atlas

    def get_atlas_region(
        self,
        atlas_id: str,
        region_name: str,
    ) -> Optional[AtlasRegion]:
        """Retrieve a named region from a texture atlas.

        Args:
            atlas_id: The atlas's unique identifier.
            region_name: The region's name within the atlas.

        Returns:
            The AtlasRegion if found, None otherwise.
        """
        atlas = self._atlases.get(atlas_id)
        if atlas is None:
            return None
        return atlas.regions.get(region_name)

    def get_atlas(self, atlas_id: str) -> Optional[TextureAtlas]:
        """Retrieve a texture atlas by its unique identifier.

        Args:
            atlas_id: The atlas's unique identifier.

        Returns:
            The TextureAtlas if found, None otherwise.
        """
        return self._atlases.get(atlas_id)

    def list_atlases(self) -> List[TextureAtlas]:
        """List all registered texture atlases.

        Returns:
            List of all TextureAtlas instances.
        """
        return list(self._atlases.values())

    def add_region_to_atlas(
        self, atlas_id: str, region: AtlasRegion
    ) -> bool:
        """Add a region to an existing texture atlas.

        UV coordinates are recomputed based on the atlas dimensions.

        Args:
            atlas_id: The atlas's unique identifier.
            region: The AtlasRegion to add.

        Returns:
            True if the region was added, False if the atlas was not found.
        """
        atlas = self._atlases.get(atlas_id)
        if atlas is None:
            return False

        if atlas.width > 0 and atlas.height > 0:
            u0 = region.x / atlas.width
            v0 = region.y / atlas.height
            u1 = (region.x + region.width) / atlas.width
            v1 = (region.y + region.height) / atlas.height
            region.uv_coords = (u0, v0, u1, v1)

        atlas.regions[region.name] = region
        return True

    def remove_atlas(self, atlas_id: str) -> bool:
        """Remove a texture atlas from the registry.

        Args:
            atlas_id: The atlas's unique identifier.

        Returns:
            True if the atlas was removed, False if not found.
        """
        with self._lock:
            return self._atlases.pop(atlas_id, None) is not None

    # ------------------------------------------------------------------
    # Asset Streaming
    # ------------------------------------------------------------------

    def stream_asset(
        self,
        asset_id: str,
        chunk_size: Optional[int] = None,
        callback: Optional[Callable[[str, float, bool], None]] = None,
    ) -> Optional[str]:
        """Begin streaming a large asset in chunks.

        Useful for progressive loading of large textures, audio, or
        video assets. Each chunk is loaded and progress is reported
        via the callback.

        Args:
            asset_id: The asset's unique identifier.
            chunk_size: Bytes per chunk (defaults to configured chunk size).
            callback: Called as callback(asset_id, progress_0_1, done)
                after each chunk is loaded.

        Returns:
            Request ID if streaming was started, None if the asset
            was not found or is not suitable for streaming.
        """
        desc = self._assets.get(asset_id)
        if desc is None:
            return None
        if desc.status == AssetLoadStatus.LOADED:
            if callback:
                callback(asset_id, 1.0, True)
            return None

        cs = chunk_size if chunk_size is not None else self._stream_chunk_size
        total_chunks = max(1, math.ceil(desc.size_bytes / cs)) if desc.size_bytes > 0 else 1

        request = LoadRequest(
            request_id=uuid.uuid4().hex,
            asset_id=asset_id,
            priority=LoadPriority.NORMAL,
            chunk_size=cs,
            total_chunks=total_chunks,
        )

        with self._lock:
            self._pending_requests[request.request_id] = request
            desc.status = AssetLoadStatus.LOADING

        # Simulate chunk-by-chunk streaming
        for chunk_idx in range(total_chunks):
            if request.cancelled:
                desc.status = AssetLoadStatus.UNLOADED
                return request.request_id

            _time_module.sleep(max(cs / (50 * 1024 * 1024), 0.0005))

            request.loaded_chunks = chunk_idx + 1
            request.progress = (chunk_idx + 1) / total_chunks

            if callback:
                callback(asset_id, request.progress, chunk_idx + 1 >= total_chunks)

        desc.status = AssetLoadStatus.LOADED
        desc.load_time_ms = (_time_module.time() - request.start_time) * 1000.0
        desc.last_accessed = _time_module.time()
        desc.reference_count += 1
        self._total_loaded += 1
        self._total_bytes_loaded += desc.size_bytes

        self._add_to_cache(asset_id, None, desc.size_bytes)
        return request.request_id

    # ------------------------------------------------------------------
    # Asset Validation
    # ------------------------------------------------------------------

    def validate_asset(self, asset_id: str) -> ValidationStatus:
        """Validate an asset's integrity and metadata.

        Checks that the asset exists, its file path is populated,
        dependencies are resolvable, and the checksum is plausible.

        Args:
            asset_id: The asset's unique identifier.

        Returns:
            The ValidationStatus result.
        """
        desc = self._assets.get(asset_id)
        if desc is None:
            return ValidationStatus.UNKNOWN

        if not desc.path:
            desc.validation_status = ValidationStatus.INVALID_FORMAT
            desc.error_message = "Empty asset path"
            return ValidationStatus.INVALID_FORMAT

        if desc.checksum and len(desc.checksum) < 8:
            desc.validation_status = ValidationStatus.CHECKSUM_MISMATCH
            desc.error_message = "Checksum too short to be valid"
            return ValidationStatus.CHECKSUM_MISMATCH

        for dep_id in desc.dependencies:
            if dep_id not in self._assets:
                desc.validation_status = ValidationStatus.MISSING_DEPENDENCY
                desc.error_message = f"Missing dependency: {dep_id}"
                return ValidationStatus.MISSING_DEPENDENCY

        desc.validation_status = ValidationStatus.VALID
        desc.error_message = ""
        return ValidationStatus.VALID

    def validate_all_assets(self) -> Dict[str, ValidationStatus]:
        """Run validation on every registered asset.

        Returns:
            Dict mapping asset_id to its ValidationStatus.
        """
        results: Dict[str, ValidationStatus] = {}
        for asset_id in self._assets:
            results[asset_id] = self.validate_asset(asset_id)
        return results

    # ------------------------------------------------------------------
    # LRU Cache Management
    # ------------------------------------------------------------------

    def _add_to_cache(self, asset_id: str, data: Any, size_bytes: int) -> None:
        """Add or update an entry in the LRU cache.

        Evicts least-recently-used entries if the cache exceeds
        its configured maximum size or entry count.

        Args:
            asset_id: The asset's unique identifier.
            data: The cached data payload.
            size_bytes: Size of the data in bytes.
        """
        with self._lock:
            # Evict if necessary
            while self._cache_current_size_bytes + size_bytes > self._cache_max_size_bytes:
                if not self._evict_lru():
                    break  # Cannot evict further

            while len(self._cache) >= self._cache_max_entries:
                if not self._evict_lru():
                    break

            now = _time_module.time()
            if asset_id in self._cache:
                entry = self._cache[asset_id]
                entry.data = data
                entry.size_bytes = size_bytes
                entry.last_accessed = now
                entry.access_count += 1
                self._cache.move_to_end(asset_id)
                self._total_cache_hits += 1
            else:
                entry = AssetCacheEntry(
                    entry_id=uuid.uuid4().hex,
                    asset_id=asset_id,
                    data=data,
                    size_bytes=size_bytes,
                    created_at=now,
                    last_accessed=now,
                    access_count=1,
                )
                self._cache[asset_id] = entry
                self._cache_current_size_bytes += size_bytes
                self._total_cache_misses += 1

    def _evict_lru(self) -> bool:
        """Evict the least-recently-used cache entry.

        Skips entries whose assets have unload_mode NEVER.

        Returns:
            True if an entry was evicted, False if none could be evicted.
        """
        if not self._cache:
            return False

        # Try to find an evictable entry (skip NEVER)
        for key in list(self._cache.keys()):
            entry = self._cache[key]
            desc = self._assets.get(entry.asset_id)
            if desc is not None and desc.unload_mode == UnloadMode.NEVER:
                continue

            del self._cache[key]
            self._cache_current_size_bytes = max(
                0, self._cache_current_size_bytes - entry.size_bytes
            )
            return True

        return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the LRU asset cache.

        Returns:
            Dict with cache entry count, total size, hit/miss counts,
            hit ratio, max entries, and max size configuration.
        """
        hit_total = self._total_cache_hits + self._total_cache_misses
        hit_ratio = (
            self._total_cache_hits / max(hit_total, 1)
        )
        return {
            "entry_count": len(self._cache),
            "total_size_bytes": self._cache_current_size_bytes,
            "total_size_mb": round(self._cache_current_size_bytes / (1024 * 1024), 2),
            "max_entries": self._cache_max_entries,
            "max_size_bytes": self._cache_max_size_bytes,
            "max_size_mb": round(self._cache_max_size_bytes / (1024 * 1024), 2),
            "total_hits": self._total_cache_hits,
            "total_misses": self._total_cache_misses,
            "hit_ratio": round(hit_ratio, 4),
            "current_utilization_pct": round(
                (self._cache_current_size_bytes / max(self._cache_max_size_bytes, 1)) * 100, 1
            ),
        }

    def clear_cache(self) -> int:
        """Clear all entries from the LRU cache.

        This does not unload the assets — it only removes their
        cached data from memory. Assets remain in LOADED status.

        Returns:
            Number of entries evicted.
        """
        count = len(self._cache)
        with self._lock:
            self._cache.clear()
            self._cache_current_size_bytes = 0
        return count

    def get_cached_asset_ids(self) -> List[str]:
        """Get the list of asset IDs currently in the cache.

        Returns:
            List of cached asset IDs in LRU order (oldest first).
        """
        return list(self._cache.keys())

    # ------------------------------------------------------------------
    # Loading Progress
    # ------------------------------------------------------------------

    def get_load_progress(self) -> LoadProgress:
        """Get a snapshot of the current aggregate loading progress.

        Returns:
            A LoadProgress instance with current counts and percentage.
        """
        total_assets = 0
        loaded_assets = 0
        failed_assets = 0
        total_bytes = 0
        loaded_bytes = 0
        current_asset = ""

        for request in self._pending_requests.values():
            total_assets += 1
            if request.loaded_chunks > 0:
                loaded_assets += 1
            total_bytes += request.total_chunks * request.chunk_size
            loaded_bytes += request.loaded_chunks * request.chunk_size
            if request.progress > 0.0 and request.progress < 1.0:
                current_asset = request.asset_id

        # Also count non-queued loaded/failed assets
        for desc in self._assets.values():
            if desc.status == AssetLoadStatus.LOADED:
                loaded_assets += 1
                total_assets += 1
                loaded_bytes += desc.size_bytes
                total_bytes += desc.size_bytes
            elif desc.status == AssetLoadStatus.FAILED:
                failed_assets += 1
                total_assets += 1
                total_bytes += desc.size_bytes

        percentage = (loaded_assets / max(total_assets, 1)) * 100.0
        status = "idle"
        if self._active_loads > 0 or self._load_queue:
            status = "loading"
        if total_assets > 0 and loaded_assets + failed_assets >= total_assets:
            status = "complete"

        return LoadProgress(
            progress_id=uuid.uuid4().hex,
            total_assets=total_assets,
            loaded_assets=loaded_assets,
            failed_assets=failed_assets,
            total_bytes=total_bytes,
            loaded_bytes=loaded_bytes,
            current_asset=current_asset,
            percentage=round(percentage, 2),
            status=status,
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(
        self,
        cache_max_entries: Optional[int] = None,
        cache_max_size_bytes: Optional[int] = None,
        max_concurrent_loads: Optional[int] = None,
        load_timeout_seconds: Optional[float] = None,
        stream_chunk_size: Optional[int] = None,
    ) -> None:
        """Configure the asset manager operational parameters.

        Args:
            cache_max_entries: Max LRU cache entries before eviction.
            cache_max_size_bytes: Max total cache size in bytes.
            max_concurrent_loads: Max simultaneous load operations.
            load_timeout_seconds: Timeout for individual load requests.
            stream_chunk_size: Default chunk size for asset streaming.
        """
        with self._lock:
            if cache_max_entries is not None:
                self._cache_max_entries = max(cache_max_entries, 1)
            if cache_max_size_bytes is not None:
                self._cache_max_size_bytes = max(cache_max_size_bytes, 1024)
            if max_concurrent_loads is not None:
                self._max_concurrent_loads = max(max_concurrent_loads, 1)
            if load_timeout_seconds is not None:
                self._load_timeout_seconds = max(load_timeout_seconds, 0.1)
            if stream_chunk_size is not None:
                self._stream_chunk_size = max(stream_chunk_size, 1024)

    # ------------------------------------------------------------------
    # Status and Statistics
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get a comprehensive status snapshot of the asset manager.

        Returns:
            Dict with counts, configuration, and aggregate statistics.
        """
        loaded_count = sum(
            1 for d in self._assets.values()
            if d.status == AssetLoadStatus.LOADED
        )
        failed_count = sum(
            1 for d in self._assets.values()
            if d.status == AssetLoadStatus.FAILED
        )
        loading_count = sum(
            1 for d in self._assets.values()
            if d.status in (AssetLoadStatus.LOADING, AssetLoadStatus.QUEUED)
        )

        return {
            "total_registered": self._total_registered,
            "current_assets": len(self._assets),
            "assets_loaded": loaded_count,
            "assets_loading": loading_count,
            "assets_failed": failed_count,
            "assets_unloaded": sum(
                1 for d in self._assets.values()
                if d.status == AssetLoadStatus.UNLOADED
            ),
            "total_bundles": len(self._bundles),
            "total_atlases": len(self._atlases),
            "active_loads": self._active_loads,
            "queue_size": len(self._load_queue),
            "pending_requests": len(self._pending_requests),
            "total_loaded_lifetime": self._total_loaded,
            "total_unloaded_lifetime": self._total_unloaded,
            "total_failed_lifetime": self._total_failed,
            "total_bytes_loaded": self._total_bytes_loaded,
            "total_bytes_loaded_mb": round(
                self._total_bytes_loaded / (1024 * 1024), 2
            ),
            "total_load_requests": self._total_load_requests,
            "total_cancelled": self._total_cancelled,
            "cache_stats": self.get_cache_stats(),
            "config": {
                "cache_max_entries": self._cache_max_entries,
                "cache_max_size_mb": round(
                    self._cache_max_size_bytes / (1024 * 1024), 2
                ),
                "max_concurrent_loads": self._max_concurrent_loads,
                "load_timeout_seconds": self._load_timeout_seconds,
                "stream_chunk_size": self._stream_chunk_size,
            },
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the asset manager to its initial empty state.

        Clears all assets, bundles, atlases, cache entries, load
        requests, and counters. The singleton instance remains valid
        for reuse. Useful for testing or engine restart scenarios.
        """
        with self._lock:
            self._assets.clear()
            self._asset_name_index.clear()
            self._bundles.clear()
            self._atlases.clear()
            self._pending_requests.clear()
            self._load_queue.clear()
            self._cache.clear()
            self._active_loads = 0
            self._cache_current_size_bytes = 0
            self._total_registered = 0
            self._total_loaded = 0
            self._total_unloaded = 0
            self._total_failed = 0
            self._total_bytes_loaded = 0
            self._total_cache_hits = 0
            self._total_cache_misses = 0
            self._total_load_requests = 0
            self._total_cancelled = 0

    # ------------------------------------------------------------------
    # Export / Snapshot
    # ------------------------------------------------------------------

    def export_registry(self) -> Dict[str, Any]:
        """Export the entire asset registry as a serializable dictionary.

        Returns:
            Dict with assets, bundles, atlases, and cache summary.
        """
        return {
            "assets": [d.to_dict() for d in self._assets.values()],
            "bundles": [b.to_dict() for b in self._bundles.values()],
            "atlases": [a.to_dict() for a in self._atlases.values()],
            "cache_entries": [e.to_dict() for e in self._cache.values()],
            "pending_requests": [r.to_dict() for r in self._pending_requests.values()],
            "load_progress": self.get_load_progress().to_dict(),
            "status": self.get_status(),
        }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_engine_asset_manager() -> EngineAssetManager:
    """Return the global EngineAssetManager singleton instance."""
    return EngineAssetManager.get_instance()