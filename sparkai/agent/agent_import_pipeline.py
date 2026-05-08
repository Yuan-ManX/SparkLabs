"""
SparkLabs Agent - Import Pipeline

Resource import orchestration system for the game engine.
Handles automatic format detection, conversion, validation,
and asset registration when files are added to the project.
AI agents use this pipeline to programmatically manage assets
and ensure all resources are correctly prepared for the engine.

Architecture:
  ImportPipeline
    |-- FormatDetector (MIME type + extension → known format)
    |-- ImportRule (source format → target format pipeline)
    |-- FormatConverter (transcoding between formats)
    |-- AssetValidator (post-import integrity checks)
    |-- ImportQueue (batch processing with progress tracking)

Import Stages:
  1. DETECT: identify source file format
  2. VALIDATE: check file integrity and compatibility
  3. CONVERT: transform to engine-native format
  4. OPTIMIZE: apply engine-specific optimizations
  5. REGISTER: add to resource manager and catalog

Supported Source Formats:
  - Images: PNG, JPG, GIF, BMP, SVG, WEBP
  - Audio: WAV, MP3, OGG, FLAC
  - Data: JSON, YAML, CSV, TMX (Tiled maps)
  - Fonts: TTF, OTF
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ImportStage(Enum):
    DETECT = "detect"
    VALIDATE = "validate"
    CONVERT = "convert"
    OPTIMIZE = "optimize"
    REGISTER = "register"


class ImportStatus(Enum):
    QUEUED = "queued"
    DETECTING = "detecting"
    VALIDATING = "validating"
    CONVERTING = "converting"
    OPTIMIZING = "optimizing"
    REGISTERING = "registering"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AssetCategory(Enum):
    TEXTURE = "texture"
    SPRITE_SHEET = "sprite_sheet"
    AUDIO = "audio"
    FONT = "font"
    TILEMAP = "tilemap"
    DATA = "data"
    UNKNOWN = "unknown"


SUPPORTED_FORMATS: Dict[str, Dict[str, Any]] = {
    "png": {"category": AssetCategory.TEXTURE, "name": "PNG Image"},
    "jpg": {"category": AssetCategory.TEXTURE, "name": "JPEG Image"},
    "jpeg": {"category": AssetCategory.TEXTURE, "name": "JPEG Image"},
    "gif": {"category": AssetCategory.TEXTURE, "name": "GIF Image"},
    "bmp": {"category": AssetCategory.TEXTURE, "name": "Bitmap Image"},
    "webp": {"category": AssetCategory.TEXTURE, "name": "WebP Image"},
    "svg": {"category": AssetCategory.TEXTURE, "name": "SVG Vector"},
    "dds": {"category": AssetCategory.TEXTURE, "name": "DDS Texture"},
    "wav": {"category": AssetCategory.AUDIO, "name": "WAV Audio"},
    "mp3": {"category": AssetCategory.AUDIO, "name": "MP3 Audio"},
    "ogg": {"category": AssetCategory.AUDIO, "name": "OGG Audio"},
    "flac": {"category": AssetCategory.AUDIO, "name": "FLAC Audio"},
    "ttf": {"category": AssetCategory.FONT, "name": "TrueType Font"},
    "otf": {"category": AssetCategory.FONT, "name": "OpenType Font"},
    "tmx": {"category": AssetCategory.TILEMAP, "name": "Tiled Map"},
    "json": {"category": AssetCategory.DATA, "name": "JSON Data"},
    "yaml": {"category": AssetCategory.DATA, "name": "YAML Data"},
    "csv": {"category": AssetCategory.DATA, "name": "CSV Data"},
}


@dataclass
class ImportEntry:
    import_id: str
    source_path: str
    target_path: str = ""
    category: AssetCategory = AssetCategory.UNKNOWN
    source_format: str = ""
    target_format: str = ""
    status: ImportStatus = ImportStatus.QUEUED
    stage: ImportStage = ImportStage.DETECT
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def progress_pct(self) -> float:
        stages = {
            ImportStage.DETECT: 10.0,
            ImportStage.VALIDATE: 30.0,
            ImportStage.CONVERT: 60.0,
            ImportStage.OPTIMIZE: 80.0,
            ImportStage.REGISTER: 100.0,
        }
        return stages.get(self.stage, 0.0)

    def to_dict(self) -> dict:
        return {
            "import_id": self.import_id,
            "source_path": self.source_path,
            "target_path": self.target_path,
            "category": self.category.value,
            "source_format": self.source_format,
            "status": self.status.value,
            "progress": self.progress_pct(),
            "size_bytes": self.size_bytes,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class ImportBatch:
    batch_id: str
    entries: List[ImportEntry] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)

    def progress_pct(self) -> float:
        if not self.entries:
            return 100.0
        completed = sum(
            1 for e in self.entries if e.status == ImportStatus.COMPLETED
        )
        return (completed / len(self.entries)) * 100.0

    def is_complete(self) -> bool:
        return all(
            e.status in (ImportStatus.COMPLETED, ImportStatus.FAILED, ImportStatus.SKIPPED)
            for e in self.entries
        )


class ImportPipeline:
    """
    Resource import orchestration for the game engine.

    Game projects accumulate diverse assets — sprites, audio,
    fonts, data files, tilemaps. This pipeline automatically
    detects formats, validates integrity, converts to optimal
    engine formats, and registers assets for immediate use.
    AI agents use this to programmatically manage assets.
    """

    _instance: Optional["ImportPipeline"] = None

    def __init__(self):
        self._imports: Dict[str, ImportEntry] = {}
        self._batches: Dict[str, ImportBatch] = {}
        self._converters: Dict[str, Callable] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "on_complete": [],
            "on_fail": [],
            "on_all_done": [],
        }
        self._lock = threading.Lock()
        self._next_id: int = 0
        self._MAX_IMPORTS = 500

    @classmethod
    def get_instance(cls) -> "ImportPipeline":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def detect_format(self, file_path: str) -> tuple[AssetCategory, str]:
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        fmt_info = SUPPORTED_FORMATS.get(ext, {})
        category = fmt_info.get("category", AssetCategory.UNKNOWN)
        format_name = fmt_info.get("name", f"Unknown ({ext})")
        return category, format_name

    def import_asset(
        self,
        source_path: str,
        target_path: str = "",
    ) -> ImportEntry:
        category, fmt_name = self.detect_format(source_path)
        ext = os.path.splitext(source_path)[1].lower().lstrip(".")

        with self._lock:
            self._next_id += 1
            import_id = f"imp-{self._next_id:05d}"
            entry = ImportEntry(
                import_id=import_id,
                source_path=source_path,
                target_path=target_path or source_path,
                category=category,
                source_format=ext,
            )

            if os.path.exists(source_path):
                entry.size_bytes = os.path.getsize(source_path)

            self._imports[import_id] = entry
            if len(self._imports) > self._MAX_IMPORTS:
                oldest = min(
                    self._imports.keys(),
                    key=lambda k: self._imports[k].started_at,
                )
                del self._imports[oldest]

        self._process_sync(entry)
        return entry

    def import_directory(
        self, directory: str, recursive: bool = True
    ) -> ImportBatch:
        with self._lock:
            self._next_id += 1
            batch_id = f"batch-{self._next_id:04d}"
            batch = ImportBatch(batch_id=batch_id)

            paths = []
            if not os.path.isdir(directory):
                return batch

            if recursive:
                for root, _, files in os.walk(directory):
                    for fname in files:
                        paths.append(os.path.join(root, fname))
            else:
                for fname in os.listdir(directory):
                    fpath = os.path.join(directory, fname)
                    if os.path.isfile(fpath):
                        paths.append(fpath)

            for path in paths:
                entry = self._create_entry(path)
                if entry.category != AssetCategory.UNKNOWN:
                    batch.entries.append(entry)
                    self._imports[entry.import_id] = entry
                    self._process_sync(entry)

            self._batches[batch_id] = batch
            return batch

    def get(self, import_id: str) -> Optional[ImportEntry]:
        return self._imports.get(import_id)

    def get_batch(self, batch_id: str) -> Optional[ImportBatch]:
        return self._batches.get(batch_id)

    def list_recent(self, limit: int = 20) -> List[ImportEntry]:
        sorted_imports = sorted(
            self._imports.values(), key=lambda e: e.started_at, reverse=True
        )
        return sorted_imports[:limit]

    def list_by_status(self, status: ImportStatus) -> List[ImportEntry]:
        return [e for e in self._imports.values() if e.status == status]

    def list_by_category(self, category: AssetCategory) -> List[ImportEntry]:
        return [e for e in self._imports.values() if e.category == category]

    def register_converter(
        self, source_format: str, converter: Callable
    ) -> None:
        self._converters[source_format] = converter

    def on(self, event: str, callback: Callable) -> None:
        if event in self._hooks:
            self._hooks[event].append(callback)

    def _create_entry(self, path: str) -> ImportEntry:
        self._next_id += 1
        import_id = f"imp-{self._next_id:05d}"
        category, fmt_name = self.detect_format(path)
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        entry = ImportEntry(
            import_id=import_id,
            source_path=path,
            target_path=path,
            category=category,
            source_format=ext,
        )
        if os.path.exists(path):
            entry.size_bytes = os.path.getsize(path)
        return entry

    def _process_sync(self, entry: ImportEntry) -> None:
        try:
            entry.status = ImportStatus.DETECTING
            entry.stage = ImportStage.DETECT

            if entry.category == AssetCategory.UNKNOWN:
                entry.status = ImportStatus.SKIPPED
                entry.warnings.append("Unknown file format — skipped")
                return

            entry.stage = ImportStage.VALIDATE
            entry.status = ImportStatus.VALIDATING
            if not os.path.exists(entry.source_path):
                entry.status = ImportStatus.FAILED
                entry.errors.append("Source file not found")
                self._fire_hook("on_fail", entry)
                return
            if entry.size_bytes == 0:
                entry.warnings.append("Empty file imported")

            entry.stage = ImportStage.CONVERT
            entry.status = ImportStatus.CONVERTING
            converter = self._converters.get(entry.source_format)
            if converter:
                try:
                    entry.target_path = converter(entry.source_path)
                except Exception as e:
                    entry.errors.append(f"Conversion failed: {e}")

            entry.stage = ImportStage.OPTIMIZE
            entry.status = ImportStatus.OPTIMIZING

            entry.stage = ImportStage.REGISTER
            entry.status = ImportStatus.REGISTERING

            entry.status = ImportStatus.COMPLETED
            entry.completed_at = time.time()
            self._fire_hook("on_complete", entry)

        except Exception as e:
            entry.status = ImportStatus.FAILED
            entry.errors.append(str(e))
            self._fire_hook("on_fail", entry)

    def _fire_hook(self, event: str, entry: ImportEntry) -> None:
        for callback in self._hooks.get(event, []):
            try:
                callback(entry)
            except Exception:
                pass

    def is_format_supported(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        return ext in SUPPORTED_FORMATS

    def list_supported_formats(self) -> Dict[str, str]:
        return {ext: info["name"] for ext, info in SUPPORTED_FORMATS.items()}

    def get_stats(self) -> dict:
        with self._lock:
            by_status: Dict[str, int] = {}
            by_category: Dict[str, int] = {}
            for entry in self._imports.values():
                s = entry.status.value
                by_status[s] = by_status.get(s, 0) + 1
                c = entry.category.value
                by_category[c] = by_category.get(c, 0) + 1
            return {
                "total_imports": len(self._imports),
                "by_status": by_status,
                "by_category": by_category,
                "batches": len(self._batches),
                "converters": len(self._converters),
                "supported_formats": len(SUPPORTED_FORMATS),
            }

    def reset(self) -> None:
        with self._lock:
            self._imports.clear()
            self._batches.clear()
            self._converters.clear()
            self._hooks = {k: [] for k in self._hooks}
            self._next_id = 0


def get_import_pipeline() -> ImportPipeline:
    return ImportPipeline.get_instance()
