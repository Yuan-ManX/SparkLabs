"""
Asset Pipeline - Game asset import, management, and export pipeline.

Architecture:
    AssetPipeline/
    |-- AssetCategory (sprite, audio, font, shader enumeration)
    |-- AssetFormat (file format enumeration)
    |-- AssetMetadata (asset descriptor dataclass)
    |-- ImportResult (import outcome dataclass)
    |-- AssetBundle (grouped asset collection dataclass)
    |-- AssetPipeline (global pipeline orchestration)

Manages the full asset lifecycle for AI-generated games. Handles asset
registration, metadata tracking, format validation, bundling, and provides
the AI agent with a clear view of all available game assets.
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class AssetCategory(Enum):
    SPRITE = auto()
    SPRITESHEET = auto()
    TILEMAP = auto()
    AUDIO_MUSIC = auto()
    AUDIO_SFX = auto()
    FONT = auto()
    SHADER = auto()
    BACKGROUND = auto()
    UI_ELEMENT = auto()
    DATA = auto()
    VIDEO = auto()


class AssetFormat(Enum):
    PNG = auto()
    JPG = auto()
    GIF = auto()
    MP3 = auto()
    OGG = auto()
    WAV = auto()
    TTF = auto()
    JSON = auto()
    GLSL = auto()
    MP4 = auto()
    WEBM = auto()


class ImportStatus(Enum):
    PENDING = auto()
    IMPORTING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class AssetMetadata:
    asset_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: AssetCategory = AssetCategory.SPRITE
    format: AssetFormat = AssetFormat.PNG
    source_path: str = ""
    file_size_bytes: int = 0
    width: int = 0
    height: int = 0
    duration_seconds: float = 0.0
    tags: List[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "category": self.category.name,
            "format": self.format.name,
            "source_path": self.source_path,
            "file_size": self.file_size_bytes,
            "dimensions": f"{self.width}x{self.height}" if self.width else None,
            "tags": self.tags,
        }


@dataclass
class ImportResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset: Optional[AssetMetadata] = None
    status: ImportStatus = ImportStatus.PENDING
    source: str = ""
    error_message: str = ""
    duration_ms: float = 0.0
    imported_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "asset_name": self.asset.name if self.asset else None,
            "status": self.status.name,
            "source": self.source,
            "error": self.error_message if self.status == ImportStatus.FAILED else None,
            "duration_ms": round(self.duration_ms, 1),
        }


@dataclass
class AssetBundle:
    bundle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    asset_ids: List[str] = field(default_factory=list)
    description: str = ""
    total_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "name": self.name,
            "asset_count": len(self.asset_ids),
            "total_size_bytes": self.total_size_bytes,
            "description": self.description,
        }


class AssetPipeline:
    _instance: Optional["AssetPipeline"] = None

    def __init__(self):
        self._assets: Dict[str, AssetMetadata] = {}
        self._bundles: Dict[str, AssetBundle] = {}
        self._import_results: List[ImportResult] = []
        self._category_indices: Dict[AssetCategory, List[str]] = {c: [] for c in AssetCategory}
        self._tag_index: Dict[str, List[str]] = {}
        self._recent_imports_limit: int = 200

    @classmethod
    def get_instance(cls) -> "AssetPipeline":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_asset(self, name: str = "", category: Any = None, 
                       format: Any = None, description: str = "",
                       source_path: str = "", tags: Any = None,
                       metadata: Optional[AssetMetadata] = None) -> str:
        if metadata is None:
            if not name:
                name = f"asset_{uuid.uuid4().hex[:8]}"
            if isinstance(category, str):
                try:
                    category = AssetCategory[category.upper()]
                except KeyError:
                    category = AssetCategory.SPRITE
            if category is None:
                category = AssetCategory.SPRITE
            if isinstance(format, str):
                try:
                    format = AssetFormat[format.upper()]
                except KeyError:
                    format = AssetFormat.PNG
            if format is None:
                format = AssetFormat.PNG
            if tags is None:
                tags = []
            metadata = AssetMetadata(
                name=name,
                category=category,
                format=format,
                source_path=source_path,
                description=description,
                tags=tags,
            )
        metadata.created_at = time.time()
        metadata.updated_at = time.time()
        self._assets[metadata.asset_id] = metadata
        self._category_indices[metadata.category].append(metadata.asset_id)
        for tag in metadata.tags:
            tag_lower = tag.lower()
            if tag_lower not in self._tag_index:
                self._tag_index[tag_lower] = []
            self._tag_index[tag_lower].append(metadata.asset_id)
        return metadata.asset_id

    def import_asset(self, name: str, category: AssetCategory, format: AssetFormat,
                     source_path: str = "", width: int = 0, height: int = 0,
                     tags: Optional[List[str]] = None,
                     description: str = "") -> ImportResult:
        started = time.time()

        if not name:
            result = ImportResult(
                status=ImportStatus.FAILED,
                source=source_path,
                error_message="Asset name is required",
                imported_at=time.time(),
            )
            self._import_results.append(result)
            self._trim_results()
            return result

        existing = self._find_by_name(name)
        if existing:
            result = ImportResult(
                asset=existing,
                status=ImportStatus.SKIPPED,
                source=source_path,
                imported_at=time.time(),
            )
            self._import_results.append(result)
            self._trim_results()
            return result

        metadata = AssetMetadata(
            name=name,
            category=category,
            format=format,
            source_path=source_path,
            width=width,
            height=height,
            tags=tags or [],
            description=description,
        )
        self.register_asset(metadata)

        result = ImportResult(
            asset=metadata,
            status=ImportStatus.COMPLETED,
            source=source_path,
            duration_ms=(time.time() - started) * 1000,
            imported_at=time.time(),
        )
        self._import_results.append(result)
        self._trim_results()
        return result

    def get_asset(self, asset_id: str) -> Optional[AssetMetadata]:
        return self._assets.get(asset_id)

    def get_by_category(self, category: AssetCategory) -> List[AssetMetadata]:
        return [self._assets[aid] for aid in self._category_indices.get(category, []) if aid in self._assets]

    def get_by_tag(self, tag: str) -> List[AssetMetadata]:
        tag_lower = tag.lower()
        ids = self._tag_index.get(tag_lower, [])
        return [self._assets[aid] for aid in ids if aid in self._assets]

    def search(self, query: str) -> List[AssetMetadata]:
        query_lower = query.lower()
        results = []
        for asset in self._assets.values():
            searchable = f"{asset.name} {asset.description} {' '.join(asset.tags)}".lower()
            if query_lower in searchable:
                results.append(asset)
        return results

    def remove_asset(self, asset_id: str) -> bool:
        if asset_id not in self._assets:
            return False
        asset = self._assets[asset_id]
        self._category_indices[asset.category].remove(asset_id)
        for tag in asset.tags:
            tag_lower = tag.lower()
            if tag_lower in self._tag_index:
                self._tag_index[tag_lower].remove(asset_id)
        del self._assets[asset_id]
        return True

    def create_bundle(self, name: str, asset_ids: Optional[List[str]] = None,
                      description: str = "") -> AssetBundle:
        ids = asset_ids or []
        total_size = sum(self._assets[aid].file_size_bytes for aid in ids if aid in self._assets)
        bundle = AssetBundle(
            name=name,
            asset_ids=ids,
            description=description,
            total_size_bytes=total_size,
        )
        self._bundles[bundle.bundle_id] = bundle
        return bundle

    def get_bundle(self, bundle_id: str) -> Optional[AssetBundle]:
        return self._bundles.get(bundle_id)

    def get_import_history(self, limit: int = 50) -> List[ImportResult]:
        return self._import_results[-limit:]

    def list_assets(self, category: Optional[AssetCategory] = None) -> List[AssetMetadata]:
        if category:
            return self.get_by_category(category)
        return list(self._assets.values())

    def list_categories(self) -> List[Dict[str, Any]]:
        return [{
            "category": c.name,
            "count": len(self._category_indices.get(c, [])),
        } for c in AssetCategory]

    def _find_by_name(self, name: str) -> Optional[AssetMetadata]:
        name_lower = name.lower()
        for asset in self._assets.values():
            if asset.name.lower() == name_lower:
                return asset
        return None

    def _trim_results(self) -> None:
        if len(self._import_results) > self._recent_imports_limit:
            self._import_results = self._import_results[-self._recent_imports_limit:]

    def get_stats(self) -> Dict[str, Any]:
        total_size = sum(a.file_size_bytes for a in self._assets.values())
        return {
            "asset_count": len(self._assets),
            "bundle_count": len(self._bundles),
            "import_count": len(self._import_results),
            "total_size_bytes": total_size,
            "categories": {c.name: len(ids) for c, ids in self._category_indices.items()},
            "unique_tags": len(self._tag_index),
            "failed_imports": sum(1 for r in self._import_results if r.status == ImportStatus.FAILED),
        }


def get_asset_pipeline() -> AssetPipeline:
    return AssetPipeline.get_instance()
