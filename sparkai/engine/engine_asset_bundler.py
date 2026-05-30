"""
SparkLabs Engine - Asset Bundler

A singleton asset packaging and streaming system for the SparkLabs
game engine. Manages asset bundling with compression, dependency
tracking, streaming priority queues, and incremental patching for
efficient content delivery.

Architecture:
  AssetBundler (singleton)
    |-- AssetEntry (individual asset metadata: path, type, hash, deps)
    |-- AssetBundle (collection of assets with compression and versioning)
    |-- StreamingRequest (priority-based streaming queue entry)
    |-- PatchManifest (delta patch between bundle versions)
"""

from __future__ import annotations

import hashlib
import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


_time_module = time


class CompressionMethod(Enum):
    NONE = "none"
    LZ4 = "lz4"
    ZSTD = "zstd"
    BROTLI = "brotli"
    LZMA = "lzma"


class AssetType(Enum):
    TEXTURE = "texture"
    MESH = "mesh"
    AUDIO = "audio"
    ANIMATION = "animation"
    SHADER = "shader"
    FONT = "font"
    PREFAB = "prefab"
    SCRIPT = "script"
    DATA = "data"
    SCENE = "scene"


class BundleStatus(Enum):
    CREATED = "created"
    COMPRESSING = "compressing"
    COMPLETE = "complete"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class StreamPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


MAX_BUNDLE_SIZE: int = 536870912
STREAMING_TIMEOUT: float = 30.0
MAX_CONCURRENT_STREAMS: int = 8
CACHE_TTL: float = 3600.0


@dataclass
class AssetEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    path: str = ""
    asset_type: AssetType = AssetType.DATA
    size_bytes: int = 0
    hash: str = ""
    dependencies: List[str] = field(default_factory=list)
    compression: CompressionMethod = CompressionMethod.LZ4
    compressed_size: int = 0
    is_streamed: bool = False
    stream_priority: StreamPriority = StreamPriority.MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "asset_type": self.asset_type.value,
            "size_bytes": self.size_bytes,
            "hash": self.hash,
            "dependencies": list(self.dependencies),
            "compression": self.compression.value,
            "compressed_size": self.compressed_size,
            "is_streamed": self.is_streamed,
            "stream_priority": self.stream_priority.value,
        }


@dataclass
class AssetBundle:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    version: str = "1.0.0"
    assets: List[str] = field(default_factory=list)
    total_size: int = 0
    compressed_size: int = 0
    compression: CompressionMethod = CompressionMethod.LZ4
    status: BundleStatus = BundleStatus.CREATED
    dependencies: List[str] = field(default_factory=list)
    checksum: str = ""
    created_at: float = field(default_factory=_time_module.time)
    published_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "assets": list(self.assets),
            "total_size": self.total_size,
            "compressed_size": self.compressed_size,
            "compression": self.compression.value,
            "status": self.status.value,
            "dependencies": list(self.dependencies),
            "checksum": self.checksum,
            "created_at": self.created_at,
            "published_at": self.published_at,
        }


@dataclass
class StreamingRequest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_id: str = ""
    priority: StreamPriority = StreamPriority.MEDIUM
    requested_at: float = field(default_factory=_time_module.time)
    timeout_seconds: float = STREAMING_TIMEOUT
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "priority": self.priority.value,
            "requested_at": self.requested_at,
            "timeout_seconds": self.timeout_seconds,
            "status": self.status,
        }


@dataclass
class PatchManifest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    base_version: str = ""
    target_version: str = ""
    changed_assets: List[str] = field(default_factory=list)
    added_assets: List[str] = field(default_factory=list)
    removed_assets: List[str] = field(default_factory=list)
    total_patch_size: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "base_version": self.base_version,
            "target_version": self.target_version,
            "changed_assets": list(self.changed_assets),
            "added_assets": list(self.added_assets),
            "removed_assets": list(self.removed_assets),
            "total_patch_size": self.total_patch_size,
            "created_at": self.created_at,
        }


COMPRESSION_RATIOS: Dict[CompressionMethod, float] = {
    CompressionMethod.NONE: 1.0,
    CompressionMethod.LZ4: 0.55,
    CompressionMethod.ZSTD: 0.45,
    CompressionMethod.BROTLI: 0.40,
    CompressionMethod.LZMA: 0.35,
}

PRIORITY_ORDER: Dict[StreamPriority, int] = {
    StreamPriority.CRITICAL: 0,
    StreamPriority.HIGH: 1,
    StreamPriority.MEDIUM: 2,
    StreamPriority.LOW: 3,
    StreamPriority.BACKGROUND: 4,
}


class AssetBundler:
    """Singleton asset packaging and streaming system.

    Manages asset registration, bundle creation with compression,
    priority-based streaming queues, and incremental version patching
    for efficient content delivery across the engine pipeline.
    """

    _instance: Optional[AssetBundler] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> AssetBundler:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> AssetBundler:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._assets: Dict[str, AssetEntry] = {}
        self._bundles: Dict[str, AssetBundle] = {}
        self._stream_queue: List[StreamingRequest] = []
        self._streaming_active: int = 0
        self._cache: Dict[str, float] = {}

    def _get_or_create_singleton(self) -> AssetBundler:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_assets": len(self._assets),
            "total_bundles": len(self._bundles),
            "published_bundles": sum(
                1 for b in self._bundles.values() if b.status == BundleStatus.PUBLISHED
            ),
            "stream_queue_size": len(self._stream_queue),
            "active_streams": self._streaming_active,
            "cache_entries": len(self._cache),
            "total_asset_size": sum(a.size_bytes for a in self._assets.values()),
            "total_compressed_size": sum(a.compressed_size for a in self._assets.values()),
        }

    def register_asset(
        self,
        path: str,
        asset_type: str,
        size_bytes: int,
        hash: str,
        dependencies: Optional[List[str]] = None,
        compression: str = "lz4",
    ) -> AssetEntry:
        comp_method = CompressionMethod(compression)
        compressed_size = self._estimate_compressed_size(size_bytes, comp_method)

        entry = AssetEntry(
            path=path,
            asset_type=AssetType(asset_type),
            size_bytes=size_bytes,
            hash=hash,
            dependencies=dependencies if dependencies is not None else [],
            compression=comp_method,
            compressed_size=compressed_size,
        )
        self._assets[entry.id] = entry
        return entry

    def create_bundle(
        self,
        name: str,
        asset_ids: List[str],
        compression: str = "lz4",
        version: str = "1.0.0",
    ) -> AssetBundle:
        comp_method = CompressionMethod(compression)
        total_size = 0
        valid_ids: List[str] = []
        all_deps: List[str] = []

        for aid in asset_ids:
            entry = self._assets.get(aid)
            if entry is None:
                continue
            valid_ids.append(aid)
            total_size += entry.size_bytes
            for dep in entry.dependencies:
                if dep not in all_deps:
                    all_deps.append(dep)

        compressed_size = self._estimate_compressed_size(total_size, comp_method)
        checksum = self._compute_checksum(total_size, valid_ids)

        bundle = AssetBundle(
            name=name,
            version=version,
            assets=list(valid_ids),
            total_size=total_size,
            compressed_size=compressed_size,
            compression=comp_method,
            status=BundleStatus.COMPLETE,
            dependencies=list(all_deps),
            checksum=checksum,
        )
        self._bundles[bundle.id] = bundle
        return bundle

    def publish_bundle(self, bundle_id: str) -> Optional[AssetBundle]:
        bundle = self._bundles.get(bundle_id)
        if bundle is None:
            return None

        if bundle.status == BundleStatus.DEPRECATED:
            return None

        if bundle.total_size > MAX_BUNDLE_SIZE:
            return None

        bundle.status = BundleStatus.PUBLISHED
        bundle.published_at = _time_module.time()

        for bid, other in self._bundles.items():
            if bid != bundle_id and other.name == bundle.name and other.status == BundleStatus.PUBLISHED:
                other.status = BundleStatus.DEPRECATED

        return bundle

    def generate_patch(
        self,
        base_version: str,
        target_version: str,
    ) -> PatchManifest:
        base_bundle: Optional[AssetBundle] = None
        target_bundle: Optional[AssetBundle] = None

        for b in self._bundles.values():
            if b.version == base_version and b.status in (BundleStatus.PUBLISHED, BundleStatus.DEPRECATED):
                base_bundle = b
            if b.version == target_version and b.status in (BundleStatus.PUBLISHED, BundleStatus.DEPRECATED):
                target_bundle = b

        changed: List[str] = []
        added: List[str] = []
        removed: List[str] = []
        patch_size = 0

        if base_bundle is not None and target_bundle is not None:
            base_set = set(base_bundle.assets)
            target_set = set(target_bundle.assets)

            for aid in target_set - base_set:
                added.append(aid)
                entry = self._assets.get(aid)
                if entry is not None:
                    patch_size += entry.compressed_size

            for aid in base_set - target_set:
                removed.append(aid)

            for aid in base_set & target_set:
                entry = self._assets.get(aid)
                if entry is not None:
                    base_entry = self._assets.get(aid)
                    target_entry = self._assets.get(aid)
                    if base_entry is not None and target_entry is not None:
                        if base_entry.hash != target_entry.hash:
                            changed.append(aid)
                            patch_size += target_entry.compressed_size

        manifest = PatchManifest(
            base_version=base_version,
            target_version=target_version,
            changed_assets=changed,
            added_assets=added,
            removed_assets=removed,
            total_patch_size=patch_size,
        )
        return manifest

    def request_stream(
        self,
        asset_id: str,
        priority: str = "medium",
        timeout_seconds: float = STREAMING_TIMEOUT,
    ) -> StreamingRequest:
        request = StreamingRequest(
            asset_id=asset_id,
            priority=StreamPriority(priority),
            timeout_seconds=timeout_seconds,
        )
        self._stream_queue.append(request)
        self._sort_stream_queue()
        return request

    def get_stream_queue(self) -> List[StreamingRequest]:
        return list(self._stream_queue)

    def process_next_stream(self) -> Optional[StreamingRequest]:
        if not self._stream_queue:
            return None

        if self._streaming_active >= MAX_CONCURRENT_STREAMS:
            return None

        now = _time_module.time()
        self._stream_queue = [
            r for r in self._stream_queue
            if (now - r.requested_at) < r.timeout_seconds
        ]

        if not self._stream_queue:
            return None

        self._sort_stream_queue()
        request = self._stream_queue.pop(0)
        request.status = "streaming"
        self._streaming_active += 1

        self._cache[request.asset_id] = now + CACHE_TTL

        request.status = "completed"
        self._streaming_active = max(0, self._streaming_active - 1)
        return request

    def _compute_checksum(self, data_size: int, asset_ids: List[str]) -> str:
        combined = f"{data_size}_{'-'.join(sorted(asset_ids))}".encode("utf-8")
        return hashlib.sha256(combined).hexdigest()[:16]

    def _estimate_compressed_size(self, size_bytes: int, method: CompressionMethod) -> int:
        ratio = COMPRESSION_RATIOS.get(method, COMPRESSION_RATIOS[CompressionMethod.LZ4])
        noise = random.uniform(0.95, 1.05)
        return max(1, int(size_bytes * ratio * noise))

    def _sort_stream_queue(self) -> None:
        self._stream_queue.sort(key=lambda r: PRIORITY_ORDER.get(r.priority, 2))


def get_asset_bundler() -> AssetBundler:
    return AssetBundler.get_instance()