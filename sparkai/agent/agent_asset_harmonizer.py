"""
SparkLabs Agent - Asset Harmonizer

Consistency validation engine that checks visual, audio, and spatial
coherence across all game assets. Detects style mismatches, palette
conflicts, resolution gaps, and ensures a unified aesthetic vision
for AI-native game creation.

Architecture:
  AssetHarmonizer
    |-- AssetDescriptor (registered asset metadata and dimensions)
    |-- HarmonizationReport (pairwise compatibility analysis)
    |-- StyleClassifier (visual style profile detection)
    |-- DimensionComparator (cross-dimension consistency scoring)
    |-- ConflictResolver (recommendation generation for mismatches)

Harmonization Dimensions:
  - Visual Style: art direction coherence across all visual assets
  - Color Palette: chromatic harmony and mood consistency
  - Spatial Coherence: scale, proportion, and grid alignment
  - Audio Style: sonic identity and mix consistency
  - Performance Budget: polycount, texture size, shader complexity
  - Resolution Tier: texture resolution and LOD consistency
  - Texture Density: texel density across surfaces
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class AssetDimension(Enum):
    VISUAL_STYLE = "visual_style"
    COLOR_PALETTE = "color_palette"
    SPATIAL_COHERENCE = "spatial_coherence"
    AUDIO_STYLE = "audio_style"
    PERFORMANCE_BUDGET = "performance_budget"
    RESOLUTION_TIER = "resolution_tier"
    TEXTURE_DENSITY = "texture_density"


class StyleProfile(Enum):
    REALISTIC = "realistic"
    STYLIZED_CARTOON = "stylized_cartoon"
    PIXEL_ART = "pixel_art"
    LOW_POLY = "low_poly"
    PHOTOREAL = "photoreal"
    HAND_DRAWN = "hand_drawn"
    VOXEL = "voxel"
    CEL_SHADED = "cel_shaded"


@dataclass
class AssetDescriptor:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    asset_type: str = ""
    category: str = ""
    dimensions: Dict[str, str] = field(default_factory=dict)
    file_format: str = ""
    file_size_kb: float = 0.0
    resolution_tier: str = "medium"
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "asset_type": self.asset_type,
            "category": self.category,
            "dimensions": self.dimensions,
            "file_format": self.file_format,
            "file_size_kb": self.file_size_kb,
            "resolution_tier": self.resolution_tier,
            "dependencies": self.dependencies,
        }


@dataclass
class HarmonizationReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_a_id: str = ""
    asset_b_id: str = ""
    dimension: AssetDimension = AssetDimension.VISUAL_STYLE
    compatibility_score: float = 1.0
    conflicts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    severity: str = "none"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "asset_a_id": self.asset_a_id,
            "asset_b_id": self.asset_b_id,
            "dimension": self.dimension.value,
            "compatibility_score": self.compatibility_score,
            "conflicts": self.conflicts,
            "recommendations": self.recommendations,
            "severity": self.severity,
        }


class AssetHarmonizer:
    """
    Asset consistency validation engine for AI-native game creation.

    Checks visual, audio, and spatial coherence across all game assets.
    Detects style mismatches and provides harmonization recommendations.
    """

    _instance: Optional[AssetHarmonizer] = None

    @classmethod
    def get_instance(cls) -> AssetHarmonizer:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._assets: Dict[str, AssetDescriptor] = {}
        self._reports: List[HarmonizationReport] = []
        self._asset_count: int = 0
        self._report_count: int = 0
        self._style_groups: Dict[str, List[str]] = {}

    def register_asset(
        self,
        name: str,
        asset_type: str,
        category: str,
        dimensions: Dict[str, str],
    ) -> AssetDescriptor:
        descriptor = AssetDescriptor(
            name=name,
            asset_type=asset_type,
            category=category,
            dimensions=dimensions,
            file_format=dimensions.get("file_format", ""),
            resolution_tier=dimensions.get("resolution_tier", "medium"),
        )
        self._assets[descriptor.id] = descriptor
        self._asset_count += 1

        style_value = dimensions.get("visual_style", "")
        if style_value:
            if style_value not in self._style_groups:
                self._style_groups[style_value] = []
            self._style_groups[style_value].append(descriptor.id)

        return descriptor

    def check_compatibility(
        self, asset_a_id: str, asset_b_id: str
    ) -> Dict[str, Any]:
        asset_a = self._assets.get(asset_a_id)
        asset_b = self._assets.get(asset_b_id)

        if not asset_a or not asset_b:
            return {
                "is_compatible": False,
                "error": "One or both assets not found",
            }

        dimension_scores: Dict[str, float] = {}
        all_conflicts: List[str] = []
        all_recommendations: List[str] = []

        for dimension in AssetDimension:
            score, conflicts, recs = self._score_dimension(
                asset_a, asset_b, dimension
            )
            dimension_scores[dimension.value] = score
            all_conflicts.extend(conflicts)
            all_recommendations.extend(recs)

            report = HarmonizationReport(
                asset_a_id=asset_a_id,
                asset_b_id=asset_b_id,
                dimension=dimension,
                compatibility_score=score,
                conflicts=conflicts,
                recommendations=recs,
                severity=self._compute_severity(score),
            )
            self._reports.append(report)
            self._report_count += 1

        avg_score = (
            sum(dimension_scores.values()) / len(dimension_scores)
            if dimension_scores else 0
        )

        return {
            "asset_a": asset_a.name,
            "asset_b": asset_b.name,
            "overall_compatibility": round(avg_score, 3),
            "dimension_scores": dimension_scores,
            "conflicts": list(set(all_conflicts)),
            "recommendations": list(set(all_recommendations)),
            "is_compatible": avg_score >= 0.5,
            "severity": self._compute_severity(avg_score),
        }

    def batch_check(self, asset_ids: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for i in range(len(asset_ids)):
            for j in range(i + 1, len(asset_ids)):
                result = self.check_compatibility(asset_ids[i], asset_ids[j])
                results.append(result)
        return results

    def get_style_profile(self, asset_id: str) -> Optional[StyleProfile]:
        asset = self._assets.get(asset_id)
        if not asset:
            return None

        style_value = asset.dimensions.get("visual_style", "")
        try:
            return StyleProfile(style_value)
        except ValueError:
            return None

    def find_clashing_assets(self) -> List[Dict[str, Any]]:
        clashes: List[Dict[str, Any]] = []
        asset_list = list(self._assets.values())

        for i in range(len(asset_list)):
            for j in range(i + 1, len(asset_list)):
                a = asset_list[i]
                b = asset_list[j]
                style_a = a.dimensions.get("visual_style", "")
                style_b = b.dimensions.get("visual_style", "")

                if style_a and style_b and style_a != style_b:
                    compat = self._compute_style_compatibility(style_a, style_b)
                    if compat < 0.5:
                        clashes.append({
                            "asset_a": a.name,
                            "asset_b": b.name,
                            "style_a": style_a,
                            "style_b": style_b,
                            "compatibility": compat,
                            "severity": self._compute_severity(compat),
                        })

        return sorted(clashes, key=lambda x: x["compatibility"])

    def suggest_replacements(self, asset_id: str) -> List[Dict[str, Any]]:
        asset = self._assets.get(asset_id)
        if not asset:
            return []

        target_style = asset.dimensions.get("visual_style", "")
        if not target_style:
            return []

        suggestions: List[Dict[str, Any]] = []
        for other_id, other in self._assets.items():
            if other_id == asset_id:
                continue
            other_style = other.dimensions.get("visual_style", "")
            if other_style == target_style:
                score = self._compute_overall_match(asset, other)
                suggestions.append({
                    "asset_id": other_id,
                    "asset_name": other.name,
                    "match_score": score,
                    "shared_dimensions": self._count_shared_dimensions(asset, other),
                })

        return sorted(suggestions, key=lambda x: x["match_score"], reverse=True)[:10]

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        asset = self._assets.get(asset_id)
        if asset:
            return asset.to_dict()
        return None

    def list_assets(
        self,
        asset_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        assets = list(self._assets.values())
        if asset_type:
            assets = [a for a in assets if a.asset_type == asset_type]
        if category:
            assets = [a for a in assets if a.category == category]
        return [a.to_dict() for a in assets]

    def _score_dimension(
        self,
        asset_a: AssetDescriptor,
        asset_b: AssetDescriptor,
        dimension: AssetDimension,
    ) -> Tuple[float, List[str], List[str]]:
        conflicts: List[str] = []
        recommendations: List[str] = []

        if dimension == AssetDimension.VISUAL_STYLE:
            return self._score_visual_style(asset_a, asset_b, conflicts, recommendations)
        elif dimension == AssetDimension.COLOR_PALETTE:
            return self._score_color_palette(asset_a, asset_b, conflicts, recommendations)
        elif dimension == AssetDimension.SPATIAL_COHERENCE:
            return self._score_spatial(asset_a, asset_b, conflicts, recommendations)
        elif dimension == AssetDimension.AUDIO_STYLE:
            return self._score_audio(asset_a, asset_b, conflicts, recommendations)
        elif dimension == AssetDimension.PERFORMANCE_BUDGET:
            return self._score_performance(asset_a, asset_b, conflicts, recommendations)
        elif dimension == AssetDimension.RESOLUTION_TIER:
            return self._score_resolution(asset_a, asset_b, conflicts, recommendations)
        elif dimension == AssetDimension.TEXTURE_DENSITY:
            return self._score_texture(asset_a, asset_b, conflicts, recommendations)

        return 1.0, [], []

    def _score_visual_style(
        self,
        a: AssetDescriptor,
        b: AssetDescriptor,
        conflicts: List[str],
        recommendations: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        style_a = a.dimensions.get("visual_style", "")
        style_b = b.dimensions.get("visual_style", "")
        score = self._compute_style_compatibility(style_a, style_b)

        if score < 0.5:
            conflicts.append(
                f"Visual style mismatch: {a.name}({style_a}) vs {b.name}({style_b})"
            )
            recommendations.append(
                f"Consider unifying visual style to either '{style_a}' or '{style_b}'"
            )

        return round(score, 3), conflicts, recommendations

    def _score_color_palette(
        self,
        a: AssetDescriptor,
        b: AssetDescriptor,
        conflicts: List[str],
        recommendations: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        palette_a = a.dimensions.get("color_palette", "")
        palette_b = b.dimensions.get("color_palette", "")

        if not palette_a and not palette_b:
            return 0.7, conflicts, recommendations

        if palette_a == palette_b:
            return 1.0, conflicts, recommendations

        if palette_a and palette_b:
            conflicts.append(
                f"Color palette mismatch: {a.name}({palette_a}) vs {b.name}({palette_b})"
            )
            recommendations.append("Define a unified color palette for the project")
            return 0.4, conflicts, recommendations

        return 0.6, conflicts, recommendations

    def _score_spatial(
        self,
        a: AssetDescriptor,
        b: AssetDescriptor,
        conflicts: List[str],
        recommendations: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        spatial_a = a.dimensions.get("spatial_coherence", "")
        spatial_b = b.dimensions.get("spatial_coherence", "")

        if spatial_a == spatial_b:
            return 1.0, conflicts, recommendations

        compatible_pairs = {
            ("grid_aligned", "grid_aligned"): 1.0,
            ("free_placement", "free_placement"): 1.0,
            ("grid_aligned", "free_placement"): 0.5,
            ("", ""): 0.7,
        }

        score = compatible_pairs.get((spatial_a, spatial_b), 0.3)
        if score < 0.5:
            conflicts.append(
                f"Spatial coherence mismatch: {a.name}({spatial_a}) vs {b.name}({spatial_b})"
            )
            recommendations.append("Align spatial reference systems between assets")

        return score, conflicts, recommendations

    def _score_audio(
        self,
        a: AssetDescriptor,
        b: AssetDescriptor,
        conflicts: List[str],
        recommendations: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        audio_a = a.dimensions.get("audio_style", "")
        audio_b = b.dimensions.get("audio_style", "")

        if audio_a == audio_b:
            return 1.0, conflicts, recommendations

        if audio_a and audio_b:
            conflicts.append(
                f"Audio style mismatch: {a.name}({audio_a}) vs {b.name}({audio_b})"
            )
            recommendations.append("Establish consistent audio identity across assets")
            return 0.4, conflicts, recommendations

        return 0.7, conflicts, recommendations

    def _score_performance(
        self,
        a: AssetDescriptor,
        b: AssetDescriptor,
        conflicts: List[str],
        recommendations: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        budget_a = a.dimensions.get("performance_budget", "")
        budget_b = b.dimensions.get("performance_budget", "")

        if budget_a == budget_b:
            return 1.0, conflicts, recommendations

        budgets = ["low", "medium", "high", "ultra"]
        idx_a = budgets.index(budget_a) if budget_a in budgets else 1
        idx_b = budgets.index(budget_b) if budget_b in budgets else 1

        diff = abs(idx_a - idx_b)
        if diff == 0:
            score = 1.0
        elif diff == 1:
            score = 0.7
        elif diff == 2:
            score = 0.4
        else:
            score = 0.2

        if score < 0.5:
            conflicts.append(
                f"Performance budget gap: {a.name}({budget_a}) vs {b.name}({budget_b})"
            )
            recommendations.append("Normalize performance budgets across assets")

        return score, conflicts, recommendations

    def _score_resolution(
        self,
        a: AssetDescriptor,
        b: AssetDescriptor,
        conflicts: List[str],
        recommendations: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        res_a = a.resolution_tier
        res_b = b.resolution_tier

        if res_a == res_b:
            return 1.0, conflicts, recommendations

        tiers = ["low", "medium", "high", "ultra"]
        idx_a = tiers.index(res_a) if res_a in tiers else 1
        idx_b = tiers.index(res_b) if res_b in tiers else 1

        diff = abs(idx_a - idx_b)
        if diff <= 1:
            return 0.8, conflicts, recommendations

        conflicts.append(
            f"Resolution tier gap: {a.name}({res_a}) vs {b.name}({res_b})"
        )
        recommendations.append("Match resolution tiers or create LOD variants")
        return 0.3, conflicts, recommendations

    def _score_texture(
        self,
        a: AssetDescriptor,
        b: AssetDescriptor,
        conflicts: List[str],
        recommendations: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        density_a = a.dimensions.get("texture_density", "")
        density_b = b.dimensions.get("texture_density", "")

        if density_a == density_b:
            return 1.0, conflicts, recommendations

        if density_a and density_b:
            conflicts.append(
                f"Texture density mismatch: {a.name}({density_a}) vs {b.name}({density_b})"
            )
            recommendations.append("Standardize texel density across assets")
            return 0.5, conflicts, recommendations

        return 0.8, conflicts, recommendations

    def _compute_style_compatibility(self, style_a: str, style_b: str) -> float:
        if not style_a or not style_b:
            return 0.5

        if style_a == style_b:
            return 1.0

        compatible_pairs: Set[Tuple[str, str]] = {
            ("realistic", "photoreal"),
            ("stylized_cartoon", "cel_shaded"),
            ("low_poly", "voxel"),
            ("pixel_art", "hand_drawn"),
        }

        pair = (min(style_a, style_b), max(style_a, style_b))
        if pair in compatible_pairs:
            return 0.6

        return 0.2

    def _compute_overall_match(
        self, a: AssetDescriptor, b: AssetDescriptor
    ) -> float:
        score = 0.0
        count = 0

        for dim in AssetDimension:
            dim_score, _, _ = self._score_dimension(a, b, dim)
            score += dim_score
            count += 1

        return round(score / count if count > 0 else 0.0, 3)

    def _count_shared_dimensions(
        self, a: AssetDescriptor, b: AssetDescriptor
    ) -> int:
        shared = 0
        all_keys = set(a.dimensions.keys()) | set(b.dimensions.keys())
        for key in all_keys:
            if a.dimensions.get(key) == b.dimensions.get(key):
                shared += 1
        return shared

    def _compute_severity(self, score: float) -> str:
        if score >= 0.8:
            return "none"
        elif score >= 0.6:
            return "minor"
        elif score >= 0.4:
            return "moderate"
        elif score >= 0.2:
            return "major"
        return "critical"

    def get_reports(
        self,
        asset_id: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        reports = self._reports
        if asset_id:
            reports = [
                r for r in reports
                if r.asset_a_id == asset_id or r.asset_b_id == asset_id
            ]
        if severity:
            reports = [r for r in reports if r.severity == severity]
        return [r.to_dict() for r in reports]

    def get_stats(self) -> Dict[str, Any]:
        category_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        style_counts: Dict[str, int] = {}

        for asset in self._assets.values():
            category_counts[asset.category] = category_counts.get(asset.category, 0) + 1
            type_counts[asset.asset_type] = type_counts.get(asset.asset_type, 0) + 1
            style = asset.dimensions.get("visual_style", "unknown")
            style_counts[style] = style_counts.get(style, 0) + 1

        critical_reports = sum(
            1 for r in self._reports if r.severity == "critical"
        )

        return {
            "total_assets": self._asset_count,
            "total_reports": self._report_count,
            "by_category": category_counts,
            "by_type": type_counts,
            "by_style": style_counts,
            "critical_conflicts": critical_reports,
            "available_dimensions": [d.value for d in AssetDimension],
            "available_styles": [s.value for s in StyleProfile],
            "style_groups": {
                style: len(ids) for style, ids in self._style_groups.items()
            },
        }


def get_asset_harmonizer() -> AssetHarmonizer:
    return AssetHarmonizer.get_instance()