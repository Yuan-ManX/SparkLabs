"""
SparkAI Agent - Asset Pipeline Engine

A comprehensive asset management system for the AI-native game engine.
Manages game assets (sprites, audio, models, shaders, fonts), tracks
asset metadata, handles format conversion pipelines, and provides
asset search and dependency tracking.

Architecture:
  AssetPipelineEngine
    |-- AssetRecord (individual asset metadata)
    |-- AssetCollection (grouped asset sets)
    |-- AssetDependency (inter-asset dependencies)
    |-- AssetPipeline (multi-step asset processing)
    |-- AssetSearchEngine (tag-based asset search)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class AssetFormat(Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    SVG = "svg"
    GLTF = "gltf"
    GLB = "glb"
    FBX = "fbx"
    OBJ = "obj"
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"
    TTF = "ttf"
    OTF = "otf"
    JSON = "json"
    YAML = "yaml"
    GLSL = "glsl"
    HLSL = "hlsl"
    SPRITE_SHEET = "sprite_sheet"
    TILEMAP = "tilemap"
    ATLAS = "atlas"


class AssetCategory(Enum):
    SPRITE = "sprite"
    TEXTURE = "texture"
    MODEL_3D = "model_3d"
    AUDIO = "audio"
    MUSIC = "music"
    FONT = "font"
    SHADER = "shader"
    ANIMATION = "animation"
    PARTICLE = "particle"
    UI = "ui"
    DATA = "data"
    SCENE = "scene"
    SCRIPT = "script"
    PREFAB = "prefab"


class AssetStatus(Enum):
    IMPORTED = "imported"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PipelineStepType(Enum):
    IMPORT = "import"
    CONVERT = "convert"
    OPTIMIZE = "optimize"
    VALIDATE = "validate"
    COMPRESS = "compress"
    GENERATE_MIPMAPS = "generate_mipmaps"
    EXTRACT_SPRITES = "extract_sprites"
    BAKE_LIGHTING = "bake_lighting"
    GENERATE_ATLAS = "generate_atlas"
    CUSTOM = "custom"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AssetRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: AssetCategory = AssetCategory.SPRITE
    format: AssetFormat = AssetFormat.PNG
    status: AssetStatus = AssetStatus.IMPORTED
    path: str = ""
    thumbnail: str = ""
    size_bytes: int = 0
    width: int = 0
    height: int = 0
    duration_ms: float = 0.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    collection_id: Optional[str] = None
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "format": self.format.value,
            "status": self.status.value,
            "path": self.path,
            "thumbnail": self.thumbnail,
            "size_bytes": self.size_bytes,
            "width": self.width,
            "height": self.height,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "metadata": self.metadata,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "collection_id": self.collection_id,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AssetCollection:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    asset_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "asset_count": len(self.asset_ids),
            "asset_ids": self.asset_ids,
            "tags": self.tags,
            "created_at": self.created_at,
        }


@dataclass
class PipelineStep:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    step_type: PipelineStepType = PipelineStepType.IMPORT
    params: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "step_type": self.step_type.value,
            "params": self.params,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class AssetPipeline:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    steps: List[PipelineStep] = field(default_factory=list)
    asset_ids: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "asset_ids": self.asset_ids,
            "status": self.status.value,
            "created_at": self.created_at,
        }


class AssetPipelineEngine:
    """
    Central asset management system for the SparkLabs AI-native game engine.

    Manages game assets, tracks metadata, handles processing pipelines,
    and provides search and dependency tracking.
    """

    def __init__(self) -> None:
        self._assets: Dict[str, AssetRecord] = {}
        self._collections: Dict[str, AssetCollection] = {}
        self._pipelines: Dict[str, AssetPipeline] = {}
        self._asset_count: int = 0
        self._collection_count: int = 0
        self._pipeline_count: int = 0
        self._seed_assets()

    def _seed_assets(self) -> None:
        seed_data = [
            ("hero_idle", "Hero Idle Sprite", AssetCategory.SPRITE, AssetFormat.SPRITE_SHEET,
             "sprites/hero_idle.png", 2048, 64, 64, ["character", "hero", "idle"]),
            ("hero_run", "Hero Run Sprite", AssetCategory.SPRITE, AssetFormat.SPRITE_SHEET,
             "sprites/hero_run.png", 4096, 64, 64, ["character", "hero", "run"]),
            ("village_bg", "Village Background", AssetCategory.TEXTURE, AssetFormat.PNG,
             "backgrounds/village.png", 524288, 1920, 1080, ["background", "village", "environment"]),
            ("tower_bg", "Tower Background", AssetCategory.TEXTURE, AssetFormat.PNG,
             "backgrounds/tower.png", 612352, 1920, 1080, ["background", "tower", "dungeon"]),
            ("main_theme", "Main Theme Music", AssetCategory.MUSIC, AssetFormat.OGG,
             "audio/main_theme.ogg", 3145728, 0, 0, ["music", "theme", "ambient"]),
            ("sword_sfx", "Sword Swing SFX", AssetCategory.AUDIO, AssetFormat.WAV,
             "audio/sword_swing.wav", 81920, 0, 0, ["sfx", "combat", "sword"]),
            ("pixel_font", "Pixel Font", AssetCategory.FONT, AssetFormat.TTF,
             "fonts/pixel.ttf", 32768, 0, 0, ["font", "pixel", "ui"]),
            ("hero_shader", "Hero Shader", AssetCategory.SHADER, AssetFormat.GLSL,
             "shaders/hero.glsl", 4096, 0, 0, ["shader", "character", "effects"]),
            ("hero_prefab", "Hero Prefab", AssetCategory.PREFAB, AssetFormat.JSON,
             "prefabs/hero.json", 8192, 0, 0, ["prefab", "character", "hero"]),
            ("tilemap_forest", "Forest Tilemap", AssetCategory.DATA, AssetFormat.TILEMAP,
             "tilemaps/forest.json", 16384, 0, 0, ["tilemap", "forest", "level"]),
        ]

        for aid, name, cat, fmt, path, size, w, h, tags in seed_data:
            asset = AssetRecord(
                id=aid,
                name=name,
                category=cat,
                format=fmt,
                status=AssetStatus.READY,
                path=path,
                size_bytes=size,
                width=w,
                height=h,
                tags=tags,
            )
            self._assets[aid] = asset
            self._asset_count += 1

        hero_collection = AssetCollection(
            name="Hero Assets",
            description="All assets related to the hero character",
            asset_ids=["hero_idle", "hero_run", "hero_shader", "hero_prefab"],
            tags=["character", "hero"],
        )
        self._collections[hero_collection.id] = hero_collection
        self._collection_count += 1

        env_collection = AssetCollection(
            name="Environment Assets",
            description="Background and environment assets",
            asset_ids=["village_bg", "tower_bg", "tilemap_forest"],
            tags=["environment", "background"],
        )
        self._collections[env_collection.id] = env_collection
        self._collection_count += 1

        self._assets["hero_idle"].dependencies = ["hero_shader"]
        self._assets["hero_shader"].dependents = ["hero_idle", "hero_run"]
        self._assets["hero_run"].dependencies = ["hero_shader"]
        self._assets["hero_prefab"].dependencies = ["hero_idle", "hero_run"]

    def register_asset(
        self,
        name: str,
        category: str = "sprite",
        format: str = "png",
        path: str = "",
        size_bytes: int = 0,
        width: int = 0,
        height: int = 0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssetRecord:
        asset = AssetRecord(
            name=name,
            category=AssetCategory(category),
            format=AssetFormat(format),
            path=path,
            size_bytes=size_bytes,
            width=width,
            height=height,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._assets[asset.id] = asset
        self._asset_count += 1
        return asset

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        asset = self._assets.get(asset_id)
        if asset:
            return asset.to_dict()
        return None

    def update_asset(self, asset_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        asset = self._assets.get(asset_id)
        if not asset:
            return None

        for key, value in updates.items():
            if key == "name":
                asset.name = value
            elif key == "tags":
                asset.tags = value
            elif key == "status":
                asset.status = AssetStatus(value)
            elif key == "metadata":
                asset.metadata.update(value)
            elif key == "path":
                asset.path = value

        asset.updated_at = time.time()
        return asset.to_dict()

    def remove_asset(self, asset_id: str) -> bool:
        if asset_id in self._assets:
            for other in self._assets.values():
                if asset_id in other.dependencies:
                    other.dependencies.remove(asset_id)
                if asset_id in other.dependents:
                    other.dependents.remove(asset_id)
            del self._assets[asset_id]
            self._asset_count -= 1
            return True
        return False

    def list_assets(
        self,
        category: Optional[AssetCategory] = None,
        status: Optional[AssetStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        assets = list(self._assets.values())
        if category:
            assets = [a for a in assets if a.category == category]
        if status:
            assets = [a for a in assets if a.status == status]
        if tags:
            assets = [a for a in assets if any(t in a.tags for t in tags)]
        assets.sort(key=lambda a: a.updated_at, reverse=True)
        return [a.to_dict() for a in assets[:limit]]

    def search_assets(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        query_words = set(query_lower.split())
        scored: List[Tuple[AssetRecord, float]] = []

        for asset in self._assets.values():
            score = 0.0
            name_words = set(asset.name.lower().split())
            score += len(query_words & name_words) * 3.0
            tag_match = len(query_words & set(t.lower() for t in asset.tags))
            score += tag_match * 2.0
            if query_lower in asset.path.lower():
                score += 1.0
            if score > 0:
                scored.append((asset, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [a.to_dict() for a, _ in scored[:limit]]

    def add_dependency(self, asset_id: str, depends_on_id: str) -> bool:
        asset = self._assets.get(asset_id)
        dep = self._assets.get(depends_on_id)
        if not asset or not dep:
            return False
        if depends_on_id not in asset.dependencies:
            asset.dependencies.append(depends_on_id)
        if asset_id not in dep.dependents:
            dep.dependents.append(asset_id)
        return True

    def remove_dependency(self, asset_id: str, depends_on_id: str) -> bool:
        asset = self._assets.get(asset_id)
        dep = self._assets.get(depends_on_id)
        if not asset or not dep:
            return False
        if depends_on_id in asset.dependencies:
            asset.dependencies.remove(depends_on_id)
        if asset_id in dep.dependents:
            dep.dependents.remove(asset_id)
        return True

    def get_dependencies(self, asset_id: str) -> Dict[str, Any]:
        asset = self._assets.get(asset_id)
        if not asset:
            return {"error": f"Asset '{asset_id}' not found"}

        deps = [self._assets[d].to_dict() for d in asset.dependencies if d in self._assets]
        dependents = [self._assets[d].to_dict() for d in asset.dependents if d in self._assets]

        return {
            "asset_id": asset_id,
            "dependencies": deps,
            "dependents": dependents,
        }

    def create_collection(
        self,
        name: str,
        description: str = "",
        asset_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> AssetCollection:
        collection = AssetCollection(
            name=name,
            description=description,
            asset_ids=asset_ids or [],
            tags=tags or [],
        )
        self._collections[collection.id] = collection
        self._collection_count += 1
        return collection

    def get_collection(self, collection_id: str) -> Optional[Dict[str, Any]]:
        collection = self._collections.get(collection_id)
        if collection:
            return collection.to_dict()
        return None

    def list_collections(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._collections.values()]

    def add_to_collection(self, collection_id: str, asset_id: str) -> bool:
        collection = self._collections.get(collection_id)
        if not collection:
            return False
        if asset_id not in collection.asset_ids:
            collection.asset_ids.append(asset_id)
        asset = self._assets.get(asset_id)
        if asset:
            asset.collection_id = collection_id
        return True

    def remove_from_collection(self, collection_id: str, asset_id: str) -> bool:
        collection = self._collections.get(collection_id)
        if not collection:
            return False
        if asset_id in collection.asset_ids:
            collection.asset_ids.remove(asset_id)
        asset = self._assets.get(asset_id)
        if asset and asset.collection_id == collection_id:
            asset.collection_id = None
        return True

    def create_pipeline(
        self,
        name: str,
        description: str = "",
        steps: Optional[List[Dict[str, Any]]] = None,
        asset_ids: Optional[List[str]] = None,
    ) -> AssetPipeline:
        pipeline = AssetPipeline(
            name=name,
            description=description,
            asset_ids=asset_ids or [],
        )
        if steps:
            for step_data in steps:
                step = PipelineStep(
                    name=step_data.get("name", ""),
                    step_type=PipelineStepType(step_data.get("step_type", "import")),
                    params=step_data.get("params", {}),
                )
                pipeline.steps.append(step)
        self._pipelines[pipeline.id] = pipeline
        self._pipeline_count += 1
        return pipeline

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline:
            return pipeline.to_dict()
        return None

    def list_pipelines(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._pipelines.values()]

    def execute_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return None

        pipeline.status = StepStatus.RUNNING
        for step in pipeline.steps:
            step.status = StepStatus.RUNNING
            step.started_at = time.time()
            step.result = {
                "step": step.name,
                "output": f"Processed: {step.step_type.value}",
            }
            step.status = StepStatus.COMPLETED
            step.completed_at = time.time()

        pipeline.status = StepStatus.COMPLETED
        return pipeline.to_dict()

    def get_stats(self) -> Dict[str, Any]:
        category_counts: Dict[str, int] = {}
        format_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}
        total_size: int = 0

        for asset in self._assets.values():
            category_counts[asset.category.value] = category_counts.get(asset.category.value, 0) + 1
            format_counts[asset.format.value] = format_counts.get(asset.format.value, 0) + 1
            status_counts[asset.status.value] = status_counts.get(asset.status.value, 0) + 1
            total_size += asset.size_bytes

        return {
            "total_assets": self._asset_count,
            "total_collections": self._collection_count,
            "total_pipelines": self._pipeline_count,
            "total_size_bytes": total_size,
            "by_category": category_counts,
            "by_format": format_counts,
            "by_status": status_counts,
        }


_global_asset_engine: Optional[AssetPipelineEngine] = None


def get_asset_engine() -> AssetPipelineEngine:
    global _global_asset_engine
    if _global_asset_engine is None:
        _global_asset_engine = AssetPipelineEngine()
    return _global_asset_engine
