"""
SparkLabs Agent - Asset Optimization Engine

Intelligent game asset analysis and optimization for AI-native
content pipelines. Evaluates textures, meshes, audio clips, and
animation data to identify optimization opportunities, reduce
memory footprint, and improve runtime performance without
degrading visual or gameplay quality.

Architecture:
  AssetOptimizationEngine
    |-- TextureAnalyzer (resolution, format, compression audit)
    |-- MeshOptimizer (polygon reduction, LOD generation)
    |-- AudioCompressor (bitrate analysis, format conversion)
    |-- AnimationCompactor (keyframe reduction, curve simplification)
    |-- BundleOptimizer (atlas generation, dependency dedup)
    |-- OptimizationReport (before/after metrics comparison)

Optimization Strategies:
  - COMPRESS: reduce file size with lossy/lossless compression
  - DOWNSAMPLE: reduce resolution while maintaining quality
  - ATLAS: combine textures into sprite sheets
  - LOD: generate level-of-detail mesh variants
  - DEDUPLICATE: identify and remove duplicate assets
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AssetType(Enum):
    TEXTURE = "texture"
    MESH = "mesh"
    AUDIO = "audio"
    ANIMATION = "animation"
    FONT = "font"
    SPRITE_SHEET = "sprite_sheet"


class OptimizationAction(Enum):
    COMPRESS = "compress"
    DOWNSAMPLE = "downsample"
    ATLAS = "atlas"
    LOD = "lod"
    CONVERT = "convert"
    DEDUPLICATE = "deduplicate"
    UNCHANGED = "unchanged"


class QualityPreset(Enum):
    MAXIMUM = "maximum"
    HIGH = "high"
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    MINIMAL = "minimal"


@dataclass
class AssetProfile:
    asset_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    asset_type: AssetType = AssetType.TEXTURE
    name: str = ""
    path: str = ""
    current_size_bytes: int = 0
    dimensions: Optional[Tuple[int, int, int]] = None
    format: str = "unknown"
    usage_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "type": self.asset_type.value,
            "name": self.name,
            "size_bytes": self.current_size_bytes,
            "format": self.format,
            "usage_count": self.usage_count,
        }


@dataclass
class OptimizationResult:
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    asset_id: str = ""
    action: OptimizationAction = OptimizationAction.UNCHANGED
    original_size: int = 0
    optimized_size: int = 0
    savings_bytes: int = 0
    quality_impact: float = 0.0
    recommendation: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def savings_percent(self) -> float:
        return (self.savings_bytes / max(1, self.original_size)) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "asset_id": self.asset_id,
            "action": self.action.value,
            "original_size": self.original_size,
            "optimized_size": self.optimized_size,
            "savings_percent": round(self.savings_percent, 2),
            "quality_impact": self.quality_impact,
        }


class AssetOptimizationEngine:
    _instance: Optional[AssetOptimizationEngine] = None

    TEXTURE_FORMATS = ["png", "jpg", "jpeg", "webp", "tga", "bmp", "dds"]
    AUDIO_FORMATS = ["wav", "mp3", "ogg", "flac", "aiff"]
    MESH_FORMATS = ["obj", "fbx", "gltf", "glb", "dae"]

    @classmethod
    def get_instance(cls) -> AssetOptimizationEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._asset_profiles: Dict[str, AssetProfile] = {}
        self._optimization_results: List[OptimizationResult] = []
        self._quality_preset: QualityPreset = QualityPreset.BALANCED
        self._total_savings_bytes: int = 0
        self._max_texture_size: int = 4096
        self._compression_enabled: bool = True
        self._auto_atlas: bool = False

    def set_quality_preset(self, preset: QualityPreset):
        self._quality_preset = preset
        preset_configs = {
            QualityPreset.MAXIMUM: {"max_texture_size": 8192, "compression": False},
            QualityPreset.HIGH: {"max_texture_size": 4096, "compression": False},
            QualityPreset.BALANCED: {"max_texture_size": 2048, "compression": True},
            QualityPreset.PERFORMANCE: {"max_texture_size": 1024, "compression": True},
            QualityPreset.MINIMAL: {"max_texture_size": 512, "compression": True},
        }
        config = preset_configs[preset]
        self._max_texture_size = config["max_texture_size"]
        self._compression_enabled = config["compression"]

    def register_asset(self, profile: AssetProfile) -> str:
        self._asset_profiles[profile.asset_id] = profile
        return profile.asset_id

    def analyze_asset(self, asset_id: str) -> List[OptimizationResult]:
        profile = self._asset_profiles.get(asset_id)
        if profile is None:
            return []

        results = []
        if profile.asset_type == AssetType.TEXTURE:
            results.extend(self._analyze_texture(profile))
        elif profile.asset_type == AssetType.AUDIO:
            results.extend(self._analyze_audio(profile))
        elif profile.asset_type == AssetType.MESH:
            results.extend(self._analyze_mesh(profile))
        elif profile.asset_type == AssetType.ANIMATION:
            results.extend(self._analyze_animation(profile))

        if not results:
            results.append(OptimizationResult(
                asset_id=asset_id,
                action=OptimizationAction.UNCHANGED,
                original_size=profile.current_size_bytes,
                optimized_size=profile.current_size_bytes,
                savings_bytes=0,
                recommendation="No optimization needed",
            ))

        self._optimization_results.extend(results)
        for r in results:
            self._total_savings_bytes += r.savings_bytes
        return results

    def _analyze_texture(self, profile: AssetProfile) -> List[OptimizationResult]:
        results = []
        width = (profile.dimensions or (2048,))[0] if profile.dimensions else 2048

        if width > self._max_texture_size and self._compression_enabled:
            reduction = int((1 - self._max_texture_size / width) * profile.current_size_bytes)
            results.append(OptimizationResult(
                asset_id=profile.asset_id,
                action=OptimizationAction.DOWNSAMPLE,
                original_size=profile.current_size_bytes,
                optimized_size=profile.current_size_bytes - reduction,
                savings_bytes=reduction,
                recommendation=f"Reduce resolution from {width}px to {self._max_texture_size}px",
                quality_impact=0.15,
            ))

        if self._compression_enabled and profile.format in ("png", "tga", "bmp"):
            estimated_savings = int(profile.current_size_bytes * 0.4)
            results.append(OptimizationResult(
                asset_id=profile.asset_id,
                action=OptimizationAction.COMPRESS,
                original_size=profile.current_size_bytes,
                optimized_size=profile.current_size_bytes - estimated_savings,
                savings_bytes=estimated_savings,
                recommendation=f"Convert from {profile.format} to compressed format",
                quality_impact=0.05,
            ))

        return results

    def _analyze_audio(self, profile: AssetProfile) -> List[OptimizationResult]:
        results = []
        if self._compression_enabled and profile.format in ("wav", "aiff", "flac"):
            estimated_savings = int(profile.current_size_bytes * 0.6)
            results.append(OptimizationResult(
                asset_id=profile.asset_id,
                action=OptimizationAction.COMPRESS,
                original_size=profile.current_size_bytes,
                optimized_size=profile.current_size_bytes - estimated_savings,
                savings_bytes=estimated_savings,
                recommendation=f"Convert {profile.format} to compressed audio (ogg/mp3)",
                quality_impact=0.1,
            ))
        return results

    def _analyze_mesh(self, profile: AssetProfile) -> List[OptimizationResult]:
        results = []
        if profile.current_size_bytes > 1024 * 1024:  # 1MB
            lod_savings = int(profile.current_size_bytes * 0.3)
            results.append(OptimizationResult(
                asset_id=profile.asset_id,
                action=OptimizationAction.LOD,
                original_size=profile.current_size_bytes,
                optimized_size=profile.current_size_bytes - lod_savings,
                savings_bytes=lod_savings,
                recommendation="Generate LOD variants for large mesh",
                quality_impact=0.0,
            ))
        return results

    def _analyze_animation(self, profile: AssetProfile) -> List[OptimizationResult]:
        results = []
        if profile.current_size_bytes > 512 * 1024:
            estimated_savings = int(profile.current_size_bytes * 0.2)
            results.append(OptimizationResult(
                asset_id=profile.asset_id,
                action=OptimizationAction.COMPRESS,
                original_size=profile.current_size_bytes,
                optimized_size=profile.current_size_bytes - estimated_savings,
                savings_bytes=estimated_savings,
                recommendation="Compact keyframes through curve simplification",
                quality_impact=0.02,
            ))
        return results

    def analyze_all(self) -> Dict[str, List[OptimizationResult]]:
        results = {}
        for asset_id in self._asset_profiles:
            results[asset_id] = self.analyze_asset(asset_id)
        return results

    def get_savings_summary(self) -> Dict[str, Any]:
        total = self._total_savings_bytes
        results = self._optimization_results
        return {
            "total_savings_bytes": total,
            "total_savings_mb": round(total / (1024 * 1024), 2),
            "assets_analyzed": len(self._asset_profiles),
            "optimizations_found": len([r for r in results if r.action != OptimizationAction.UNCHANGED]),
            "unchanged_count": len([r for r in results if r.action == OptimizationAction.UNCHANGED]),
            "quality_preset": self._quality_preset.value,
            "by_action": {
                action.value: len([r for r in results if r.action == action])
                for action in OptimizationAction
            },
        }

    def find_duplicates(self) -> List[Tuple[str, str, int]]:
        size_groups: Dict[int, List[str]] = {}
        for aid, profile in self._asset_profiles.items():
            size = profile.current_size_bytes
            if size > 0:
                if size not in size_groups:
                    size_groups[size] = []
                size_groups[size].append(aid)
        duplicates = []
        for size, aid_list in size_groups.items():
            if len(aid_list) > 1:
                for duplicate_id in aid_list[1:]:
                    duplicates.append((aid_list[0], duplicate_id, size))
        return duplicates

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_assets": len(self._asset_profiles),
            **self.get_savings_summary(),
            "duplicates_found": len(self.find_duplicates()),
            "by_type": {
                at.value: len([p for p in self._asset_profiles.values() if p.asset_type == at])
                for at in AssetType
            },
        }


def get_asset_optimizer() -> AssetOptimizationEngine:
    return AssetOptimizationEngine.get_instance()