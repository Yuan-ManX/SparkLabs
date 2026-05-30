"""
SparkLabs Engine - LOD Gate

A singleton level-of-detail management system for mesh complexity,
texture resolution, and draw distance tiers. Provides smooth LOD
transitions with configurable distance thresholds for optimizing
rendering performance across hardware tiers.

Architecture:
  LODGate (singleton)
    |-- LODLevel (distance thresholds, mesh reduction, texture mip)
    |-- LODProfile (hardware-tier target configuration)
    |-- LODGroup (object with multiple LOD variants)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class QualityTier(Enum):
    ULTRA = "ultra"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class LODTransition(Enum):
    NONE = "none"
    DITHER = "dither"
    CROSSFADE = "crossfade"
    POP = "pop"


class MeshReductionMethod(Enum):
    NONE = "none"
    DECIMATE = "decimate"
    BILLBOARD = "billboard"
    IMPOSTER = "imposter"
    SIMPLIFY = "simplify"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class LODLevel:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    level_index: int = 0
    distance_threshold: float = 0.0
    triangle_reduction: float = 0.0
    texture_mip_level: int = 0
    shadow_casting: bool = True
    bone_count: int = 64
    vertex_animation: bool = True
    reduction_method: MeshReductionMethod = MeshReductionMethod.NONE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "level_index": self.level_index,
            "distance_threshold": self.distance_threshold,
            "triangle_reduction": self.triangle_reduction,
            "texture_mip_level": self.texture_mip_level,
            "shadow_casting": self.shadow_casting,
            "bone_count": self.bone_count,
            "vertex_animation": self.vertex_animation,
            "reduction_method": self.reduction_method.value,
        }


@dataclass
class LODProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    quality_tier: QualityTier = QualityTier.HIGH
    transition_mode: LODTransition = LODTransition.DITHER
    transition_duration: float = 0.3
    bias: float = 1.0
    max_distance: float = 500.0
    screen_size_ratio: float = 0.5
    force_cull_distance: float = 1000.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "quality_tier": self.quality_tier.value,
            "transition_mode": self.transition_mode.value,
            "transition_duration": self.transition_duration,
            "bias": self.bias,
            "max_distance": self.max_distance,
            "screen_size_ratio": self.screen_size_ratio,
            "force_cull_distance": self.force_cull_distance,
            "metadata": dict(self.metadata),
        }


@dataclass
class LODGroup:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    object_id: str = ""
    lod_levels: List[LODLevel] = field(default_factory=list)
    current_level: int = 0
    last_transition_time: float = 0.0
    distance_to_camera: float = 0.0
    visible: bool = True
    transition_progress: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "object_id": self.object_id,
            "lod_levels": [lvl.to_dict() for lvl in self.lod_levels],
            "current_level": self.current_level,
            "distance_to_camera": self.distance_to_camera,
            "visible": self.visible,
            "transition_progress": self.transition_progress,
        }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

MIN_LOD_DISTANCE_STEP: float = 0.5
DEFAULT_MAX_DISTANCE: float = 500.0


class LODGate:
    """Dynamic level-of-detail management for rendering optimization.

    Controls mesh complexity, texture resolution, and draw distance
    tiers. Applies smooth LOD transitions using dithering or crossfade
    based on camera proximity and screen-size heuristics.
    """

    _instance: Optional[LODGate] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> LODGate:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> LODGate:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._groups: List[LODGroup] = []
        self._profiles: List[LODProfile] = []
        self._active_profile: Optional[LODProfile] = None
        self._camera_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._culled_groups: int = 0
        self._total_transitions: int = 0
        self._initialize_default_profiles()

    def _get_or_create_singleton(self) -> LODGate:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "lod_groups": len(self._groups),
            "active_profile": self._active_profile.name if self._active_profile else "none",
            "profiles": len(self._profiles),
            "culled_groups": self._culled_groups,
            "total_transitions": self._total_transitions,
            "visible_groups": sum(1 for g in self._groups if g.visible),
        }

    # --- Profile Operations ---

    def create_profile(
        self,
        name: str,
        quality_tier: str = "high",
        transition_mode: str = "dither",
        bias: float = 1.0,
    ) -> LODProfile:
        profile = LODProfile(
            name=name,
            quality_tier=QualityTier(quality_tier),
            transition_mode=LODTransition(transition_mode),
            bias=bias,
        )
        self._profiles.append(profile)
        return profile

    def set_active_profile(self, profile_id: str) -> bool:
        for p in self._profiles:
            if p.id == profile_id:
                self._active_profile = p
                return True
        return False

    def list_profiles(self) -> List[LODProfile]:
        return list(self._profiles)

    # --- LOD Group Operations ---

    def register_group(
        self,
        name: str,
        object_id: str = "",
    ) -> LODGroup:
        group = LODGroup(
            name=name,
            object_id=object_id,
        )
        self._groups.append(group)
        return group

    def add_lod_level(
        self,
        group_id: str,
        distance: float,
        triangle_reduction: float = 0.0,
        texture_mip: int = 0,
        method: str = "none",
    ) -> Optional[LODLevel]:
        group = self._find_group(group_id)
        if not group:
            return None

        level = LODLevel(
            level_index=len(group.lod_levels),
            distance_threshold=distance,
            triangle_reduction=triangle_reduction,
            texture_mip_level=texture_mip,
            reduction_method=MeshReductionMethod(method),
        )
        group.lod_levels.append(level)
        group.lod_levels.sort(key=lambda lvl: lvl.distance_threshold)
        return level

    def update_camera(
        self,
        position: Tuple[float, float, float],
    ) -> None:
        self._camera_position = position

    def compute_lod(self, delta_time: float) -> Dict[str, Any]:
        transitions = 0
        newly_culled = 0

        profile = self._active_profile
        max_dist = profile.max_distance if profile else DEFAULT_MAX_DISTANCE
        force_cull = profile.force_cull_distance if profile else DEFAULT_MAX_DISTANCE * 2

        for group in self._groups:
            dx = self._camera_position[0]
            dy = self._camera_position[1]
            dz = self._camera_position[2]
            group.distance_to_camera = math.sqrt(dx * dx + dy * dy + dz * dz)

            if group.distance_to_camera > force_cull:
                if group.visible:
                    group.visible = False
                    newly_culled += 1
                continue
            else:
                group.visible = True

            if group.distance_to_camera > max_dist:
                continue

            if not group.lod_levels:
                continue

            target_level = 0
            for i, level in enumerate(group.lod_levels):
                if group.distance_to_camera >= level.distance_threshold:
                    target_level = i

            bias = profile.bias if profile else 1.0
            adjusted_distance = group.distance_to_camera * bias
            for i, level in enumerate(group.lod_levels):
                if adjusted_distance >= level.distance_threshold:
                    target_level = i

            if target_level != group.current_level:
                group.current_level = target_level
                group.last_transition_time = _time_module.time()
                group.transition_progress = 0.0
                transitions += 1
            else:
                if group.transition_progress < 1.0:
                    group.transition_progress += delta_time / max(
                        0.01,
                        profile.transition_duration if profile else 0.3,
                    )
                    group.transition_progress = min(1.0, group.transition_progress)

        self._total_transitions += transitions
        self._culled_groups = sum(1 for g in self._groups if not g.visible)

        return {
            "transitions": transitions,
            "culled_groups": self._culled_groups,
            "visible_groups": sum(1 for g in self._groups if g.visible),
            "groups_updated": len(self._groups),
        }

    def get_group_lod_state(self, group_id: str) -> Optional[Dict[str, Any]]:
        group = self._find_group(group_id)
        if not group:
            return None

        return {
            "group_name": group.name,
            "current_level": group.current_level,
            "distance": group.distance_to_camera,
            "visible": group.visible,
            "transition_progress": group.transition_progress,
            "lod_count": len(group.lod_levels),
            "current_lod": (
                group.lod_levels[group.current_level].to_dict()
                if group.lod_levels and group.current_level < len(group.lod_levels)
                else None
            ),
        }

    def list_groups(self) -> List[LODGroup]:
        return list(self._groups)

    # --- Internal ---

    def _find_group(self, group_id: str) -> Optional[LODGroup]:
        for g in self._groups:
            if g.id == group_id:
                return g
        return None

    def _initialize_default_profiles(self) -> None:
        defaults = [
            ("Ultra", "ultra", "dither", 1.5),
            ("High", "high", "dither", 1.0),
            ("Medium", "medium", "crossfade", 0.7),
            ("Low", "low", "pop", 0.4),
        ]
        for name, tier, transition, bias in defaults:
            profile = LODProfile(
                name=name,
                quality_tier=QualityTier(tier),
                transition_mode=LODTransition(transition),
                bias=bias,
            )
            self._profiles.append(profile)
        if self._profiles:
            self._active_profile = self._profiles[1]


def get_lod_gate() -> LODGate:
    return LODGate.get_instance()