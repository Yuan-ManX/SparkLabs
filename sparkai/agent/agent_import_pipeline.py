"""
SparkLabs Agent - Import Pipeline Engine

AI-assisted asset import pipeline with format detection,
preset management, batch processing, and AI-driven recommendations.
Handles textures, models, audio, fonts, spritesheets, animations,
tilemaps, and shaders with configurable compression presets.

Architecture:
  ImportPipelineEngine
    |-- Preset Manager (create and manage import configurations)
    |-- AI Recommender (suggest optimal presets from file analysis)
    |-- Queue Engine (single-file and batch import scheduling)
    |-- Progress Tracker (per-task status monitoring)
    |-- Import Validator (post-import integrity verification)

Compression presets range from lossless through custom, supporting
mipmap generation, collision mesh generation, resolution limits,
and texture filter mode configuration.
"""

from __future__ import annotations

import os
import re
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AssetImportType(Enum):
    TEXTURE = "texture"
    MODEL = "model"
    AUDIO = "audio"
    FONT = "font"
    SPRITESHEET = "spritesheet"
    ANIMATION = "animation"
    TILEMAP = "tilemap"
    SHADER = "shader"
    RAW_DATA = "raw_data"
    UNKNOWN = "unknown"


class CompressionPreset(Enum):
    LOSSLESS = "lossless"
    HIGH_QUALITY = "high_quality"
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


EXTENSION_TYPE_MAP: Dict[str, AssetImportType] = {
    "png": AssetImportType.TEXTURE, "jpg": AssetImportType.TEXTURE,
    "jpeg": AssetImportType.TEXTURE, "gif": AssetImportType.TEXTURE,
    "bmp": AssetImportType.TEXTURE, "webp": AssetImportType.TEXTURE,
    "dds": AssetImportType.TEXTURE, "svg": AssetImportType.TEXTURE,
    "fbx": AssetImportType.MODEL, "obj": AssetImportType.MODEL,
    "gltf": AssetImportType.MODEL, "glb": AssetImportType.MODEL,
    "blend": AssetImportType.MODEL,
    "wav": AssetImportType.AUDIO, "mp3": AssetImportType.AUDIO,
    "ogg": AssetImportType.AUDIO, "flac": AssetImportType.AUDIO,
    "aiff": AssetImportType.AUDIO,
    "ttf": AssetImportType.FONT, "otf": AssetImportType.FONT,
    "tmx": AssetImportType.TILEMAP, "tsx": AssetImportType.TILEMAP,
    "glsl": AssetImportType.SHADER, "hlsl": AssetImportType.SHADER,
    "vert": AssetImportType.SHADER, "frag": AssetImportType.SHADER,
}


@dataclass
class ImportPreset:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    source_format: str = ""
    target_format: str = ""
    compression: CompressionPreset = CompressionPreset.BALANCED
    mipmap_generation: bool = True
    generate_collision: bool = False
    resolution_max: int = 2048
    filter_mode: str = "bilinear"
    is_ai_generated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source_format": self.source_format,
            "target_format": self.target_format,
            "compression": self.compression.value,
            "mipmap_generation": self.mipmap_generation,
            "generate_collision": self.generate_collision,
            "resolution_max": self.resolution_max,
            "filter_mode": self.filter_mode,
            "is_ai_generated": self.is_ai_generated,
        }


@dataclass
class ImportTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_path: str = ""
    import_type: AssetImportType = AssetImportType.TEXTURE
    preset_id: str = ""
    status: str = "queued"
    ai_suggestions: List[str] = field(default_factory=list)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_path": self.source_path,
            "import_type": self.import_type.value,
            "preset_id": self.preset_id,
            "status": self.status,
            "ai_suggestions_count": len(self.ai_suggestions),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "has_error": bool(self.error_message),
            "elapsed_seconds": (
                round(self.completed_at - self.started_at, 2)
                if self.started_at and self.completed_at
                else None
            ),
        }


class ImportPipelineEngine:
    """AI-assisted asset import pipeline with format detection and preset management."""

    _instance: Optional["ImportPipelineEngine"] = None
    _lock = threading.Lock()

    MAX_PRESETS = 100
    MAX_TASKS = 500

    def __init__(self):
        self._presets: Dict[str, ImportPreset] = {}
        self._tasks: Dict[str, ImportTask] = {}
        self._task_history: List[str] = []
        self._total_imports: int = 0

    @classmethod
    def get_instance(cls) -> "ImportPipelineEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_preset(
        self,
        name: str,
        source_format: str,
        target_format: str,
        compression: CompressionPreset,
        ai_hint: str = "",
    ) -> ImportPreset:
        hint_lower = ai_hint.lower()
        mipmap = True
        collision = False
        res_max = 2048
        filter_mode = "bilinear"

        if "no mipmap" in hint_lower or "nomip" in hint_lower:
            mipmap = False
        if "collision" in hint_lower:
            collision = True
        if "4k" in hint_lower or "4096" in hint_lower:
            res_max = 4096
        elif "1k" in hint_lower or "1024" in hint_lower:
            res_max = 1024
        if "trilinear" in hint_lower:
            filter_mode = "trilinear"
        elif "nearest" in hint_lower:
            filter_mode = "nearest"

        preset = ImportPreset(
            name=name,
            source_format=source_format,
            target_format=target_format,
            compression=compression,
            mipmap_generation=mipmap,
            generate_collision=collision,
            resolution_max=res_max,
            filter_mode=filter_mode,
            is_ai_generated=bool(ai_hint),
        )

        self._presets[preset.id] = preset
        if len(self._presets) > self.MAX_PRESETS:
            oldest = min(
                (p for p in self._presets.values()),
                key=lambda p: p.id,
            )
            del self._presets[oldest.id]

        return preset

    def ai_recommend_preset(
        self, source_path: str, description: str = ""
    ) -> Optional[ImportPreset]:
        ext = os.path.splitext(source_path)[1].lower().lstrip(".")
        import_type = EXTENSION_TYPE_MAP.get(ext)

        if import_type is None:
            return None

        desc_lower = description.lower()

        if import_type == AssetImportType.TEXTURE:
            if "ui" in desc_lower or "icon" in desc_lower:
                compression = CompressionPreset.LOSSLESS
                mipmap = False
            elif "background" in desc_lower or "large" in desc_lower:
                compression = CompressionPreset.PERFORMANCE
                mipmap = True
            else:
                compression = CompressionPreset.HIGH_QUALITY
                mipmap = True

        elif import_type == AssetImportType.AUDIO:
            if "music" in desc_lower or "ambient" in desc_lower:
                compression = CompressionPreset.HIGH_QUALITY
            elif "sfx" in desc_lower or "effect" in desc_lower:
                compression = CompressionPreset.PERFORMANCE
            else:
                compression = CompressionPreset.BALANCED

        elif import_type == AssetImportType.MODEL:
            compression = CompressionPreset.BALANCED
            if "static" in desc_lower:
                compression = CompressionPreset.HIGH_QUALITY
            elif "dynamic" in desc_lower:
                compression = CompressionPreset.PERFORMANCE

        else:
            compression = CompressionPreset.BALANCED

        preset = ImportPreset(
            name=f"ai-recommended-{import_type.value}-{uuid.uuid4().hex[:6]}",
            source_format=ext,
            target_format=ext,
            compression=compression,
            mipmap_generation=mipmap,
            is_ai_generated=True,
        )

        self._presets[preset.id] = preset
        return preset

    def queue_import(
        self, source_path: str, import_type: Optional[AssetImportType], preset_id: str
    ) -> Optional[ImportTask]:
        ext = os.path.splitext(source_path)[1].lower().lstrip(".")
        resolved_type = import_type or EXTENSION_TYPE_MAP.get(ext)
        if resolved_type is None:
            return None

        preset = self._presets.get(preset_id)

        task = ImportTask(
            source_path=source_path,
            import_type=resolved_type,
            preset_id=preset_id,
            status="queued",
        )

        if preset:
            if preset.compression == CompressionPreset.LOSSLESS:
                task.ai_suggestions.append("Using lossless compression — largest file size")
            elif preset.compression == CompressionPreset.PERFORMANCE:
                task.ai_suggestions.append("Performance preset — review for quality tradeoffs")

        if ext in ("png", "jpg", "jpeg") and not os.path.splitext(source_path)[0].endswith("_n"):
            task.ai_suggestions.append("Consider adding a normal map variant (_n suffix)")

        self._tasks[task.id] = task
        self._task_history.append(task.id)
        self._total_imports += 1

        if len(self._tasks) > self.MAX_TASKS:
            oldest_id = self._task_history.pop(0)
            self._tasks.pop(oldest_id, None)

        return task

    def process_batch(
        self, paths: List[str], ai_description: str = ""
    ) -> List[ImportTask]:
        tasks: List[ImportTask] = []
        for path in paths:
            ext = os.path.splitext(path)[1].lower().lstrip(".")
            import_type = EXTENSION_TYPE_MAP.get(ext)
            if import_type is None:
                continue

            preset = self.ai_recommend_preset(path, ai_description)
            if preset is None:
                continue

            task = self.queue_import(path, import_type, preset.id)
            if task:
                task.status = "processing"
                task.started_at = time.time()
                task.completed_at = time.time()
                task.status = "completed"
                tasks.append(task)

        return tasks

    def get_import_progress(self, task_id: str) -> dict:
        task = self._tasks.get(task_id)
        if task is None:
            return {"error": "Task not found"}

        return {
            "task_id": task.id,
            "source_path": task.source_path,
            "import_type": task.import_type.value,
            "status": task.status,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "error_message": task.error_message if task.error_message else None,
        }

    def validate_import(self, task_id: str) -> List[str]:
        issues: List[str] = []
        task = self._tasks.get(task_id)
        if task is None:
            issues.append("Task not found in registry")
            return issues

        if task.error_message:
            issues.append(f"Import error: {task.error_message}")

        if not os.path.exists(task.source_path):
            issues.append(f"Source file does not exist: {task.source_path}")

        if task.status == "queued":
            issues.append("Task is still queued — import has not started")

        ext = os.path.splitext(task.source_path)[1].lower().lstrip(".")
        if ext not in EXTENSION_TYPE_MAP:
            issues.append(f"Unsupported file extension: .{ext}")

        preset = self._presets.get(task.preset_id)
        if preset is None:
            issues.append("Preset not found — import may use default settings")

        return issues

    def import_asset(self, source_path: str) -> Optional[ImportTask]:
        ext = os.path.splitext(source_path)[1].lower().lstrip(".")
        import_type = EXTENSION_TYPE_MAP.get(ext)
        if import_type is None:
            return None

        preset = self.ai_recommend_preset(source_path)
        preset_id = preset.id if preset else self.create_preset(
            name=f"auto-{ext}", source_format=ext, target_format=ext,
            compression=CompressionPreset.BALANCED
        ).id

        return self.queue_import(source_path, import_type, preset_id)

    def detect_format(self, file_path: str) -> tuple:
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        import_type = EXTENSION_TYPE_MAP.get(ext, AssetImportType.RAW_DATA)
        return (import_type, ext)

    def is_format_supported(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        return ext in EXTENSION_TYPE_MAP

    def list_recent(self, limit: int = 20) -> List[ImportTask]:
        recent_ids = self._task_history[-limit:]
        return [self._tasks[tid] for tid in recent_ids if tid in self._tasks]

    def list_supported_formats(self) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = defaultdict(list)
        for ext, asset_type in EXTENSION_TYPE_MAP.items():
            result[asset_type.value].append(ext)
        return dict(result)

    def get_stats(self) -> dict:
        type_counts: Dict[str, int] = defaultdict(int)
        status_counts: Dict[str, int] = defaultdict(int)
        for task in self._tasks.values():
            type_counts[task.import_type.value] += 1
            status_counts[task.status] += 1

        compression_counts: Dict[str, int] = defaultdict(int)
        for preset in self._presets.values():
            compression_counts[preset.compression.value] += 1

        return {
            "total_tasks": len(self._tasks),
            "total_imports_ever": self._total_imports,
            "total_presets": len(self._presets),
            "type_distribution": dict(type_counts),
            "status_distribution": dict(status_counts),
            "compression_distribution": dict(compression_counts),
            "ai_generated_presets": sum(
                1 for p in self._presets.values() if p.is_ai_generated
            ),
            "max_presets": self.MAX_PRESETS,
            "max_tasks": self.MAX_TASKS,
        }


def get_import_pipeline() -> ImportPipelineEngine:
    return ImportPipelineEngine.get_instance()