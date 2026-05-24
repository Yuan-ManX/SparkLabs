"""
SparkLabs Engine - Level-of-Detail System

Level-of-detail mesh selection and transition management system.
Selects optimal mesh representations based on camera distance, screen
coverage, and GPU budget constraints. Supports configurable transition
effects between LOD levels for smooth visual quality adaptation.

Architecture:
    LODSystem
      |-- LODGroup (entity-level container holding per-level mesh entries)
      |-- MeshLODEntry (single LOD level with mesh reference and distance threshold)
      |-- TransitionConfig (per-group transition behavior: pop, blend, dither, crossfade)
      |-- LODBudget (global triangle count and draw call limits for budget-based selection)

LOD Features:
    - DISTANCE_BASED: select LOD by camera-to-object distance
    - SCREEN_COVERAGE: select LOD by projected screen-space pixel area
    - BUDGET_BASED: select LOD honoring global triangle/draw-call budget
    - HYBRID: combines distance and screen coverage for balanced selection
    - SMOOTH_BLEND: interpolated geometry transition between two LOD levels
    - DITHER: pixel-level dissolve pattern for LOD transitions
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class LODLevel(Enum):
    """Mesh detail level from highest fidelity to most simplified representation."""
    LOD0_ULTRA = "lod0_ultra"
    LOD1_HIGH = "lod1_high"
    LOD2_MEDIUM = "lod2_medium"
    LOD3_LOW = "lod3_low"
    LOD4_MINIMAL = "lod4_minimal"
    LOD5_IMPOSTER = "lod5_imposter"


class TransitionType(Enum):
    """Visual effect applied when switching between LOD levels."""
    POP = "pop"
    SMOOTH_BLEND = "smooth_blend"
    DITHER = "dither"
    CROSSFADE = "crossfade"


class SelectionStrategy(Enum):
    """Method for determining which LOD level to display per frame."""
    DISTANCE_BASED = "distance_based"
    SCREEN_COVERAGE = "screen_coverage"
    BUDGET_BASED = "budget_based"
    HYBRID = "hybrid"


_LOD_DISTANCE_FALLOFF: Dict[LODLevel, float] = {
    LODLevel.LOD0_ULTRA: 15.0,
    LODLevel.LOD1_HIGH: 40.0,
    LODLevel.LOD2_MEDIUM: 80.0,
    LODLevel.LOD3_LOW: 150.0,
    LODLevel.LOD4_MINIMAL: 300.0,
    LODLevel.LOD5_IMPOSTER: 600.0,
}


_LOD_SCREEN_COVERAGE: Dict[LODLevel, float] = {
    LODLevel.LOD0_ULTRA: 0.15,
    LODLevel.LOD1_HIGH: 0.08,
    LODLevel.LOD2_MEDIUM: 0.04,
    LODLevel.LOD3_LOW: 0.02,
    LODLevel.LOD4_MINIMAL: 0.008,
    LODLevel.LOD5_IMPOSTER: 0.002,
}


_LOD_LEVEL_ORDER: List[LODLevel] = [
    LODLevel.LOD0_ULTRA,
    LODLevel.LOD1_HIGH,
    LODLevel.LOD2_MEDIUM,
    LODLevel.LOD3_LOW,
    LODLevel.LOD4_MINIMAL,
    LODLevel.LOD5_IMPOSTER,
]


@dataclass
class MeshLODEntry:
    """A single LOD level within a group, referencing a mesh and its threshold."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    group_id: str = ""
    level: LODLevel = LODLevel.LOD0_ULTRA
    mesh_ref: str = ""
    distance_threshold: float = 0.0
    screen_coverage_threshold: float = 0.0
    triangle_count: int = 0
    material_ref: str = ""
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "level": self.level.value,
            "mesh_ref": self.mesh_ref,
            "distance_threshold": round(self.distance_threshold, 2),
            "screen_coverage_threshold": round(self.screen_coverage_threshold, 4),
            "triangle_count": self.triangle_count,
            "material_ref": self.material_ref,
            "is_active": self.is_active,
        }


@dataclass
class TransitionConfig:
    """Controls how an LOD group transitions between detail levels."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    group_id: str = ""
    transition_type: TransitionType = TransitionType.SMOOTH_BLEND
    duration: float = 0.3
    dither_strength: float = 0.5
    crossfade_overlap: float = 0.1
    is_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "transition_type": self.transition_type.value,
            "duration": round(self.duration, 3),
            "dither_strength": round(self.dither_strength, 2),
            "crossfade_overlap": round(self.crossfade_overlap, 3),
            "is_enabled": self.is_enabled,
        }


@dataclass
class LODBudget:
    """Global budget constraints for budget-based LOD selection."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    max_triangles: int = 100000
    max_draw_calls: int = 500
    current_triangles: int = 0
    current_draw_calls: int = 0
    priority_bias: float = 1.0
    is_enforced: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "max_triangles": self.max_triangles,
            "max_draw_calls": self.max_draw_calls,
            "current_triangles": self.current_triangles,
            "current_draw_calls": self.current_draw_calls,
            "triangle_usage_pct": round(
                self.current_triangles / max(1, self.max_triangles) * 100.0, 1
            ),
            "draw_call_usage_pct": round(
                self.current_draw_calls / max(1, self.max_draw_calls) * 100.0, 1
            ),
            "priority_bias": round(self.priority_bias, 2),
            "is_enforced": self.is_enforced,
        }


@dataclass
class LODGroup:
    """Entity-level container holding per-level LOD entries and transition behavior."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    name: str = ""
    entries: Dict[str, MeshLODEntry] = field(default_factory=dict)
    transition_id: str = ""
    selection_strategy: SelectionStrategy = SelectionStrategy.DISTANCE_BASED
    active_level: LODLevel = LODLevel.LOD0_ULTRA
    forced_level: Optional[LODLevel] = None
    screen_coverage_fov: float = 60.0
    screen_coverage_height: float = 1080.0
    is_enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "name": self.name,
            "entry_count": len(self.entries),
            "entries": [e.to_dict() for e in self.entries.values()],
            "transition_id": self.transition_id,
            "selection_strategy": self.selection_strategy.value,
            "active_level": self.active_level.value,
            "forced_level": self.forced_level.value if self.forced_level else None,
            "screen_coverage_fov": round(self.screen_coverage_fov, 1),
            "screen_coverage_height": self.screen_coverage_height,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at,
        }


class LODSystem:
    """Level-of-detail mesh selection and transition management engine."""

    _instance: Optional["LODSystem"] = None
    _lock = threading.RLock()

    MAX_LOD_ENTRIES_PER_GROUP = 6
    MAX_LOD_GROUPS = 4096

    def __init__(self) -> None:
        self._groups: Dict[str, LODGroup] = {}
        self._transitions: Dict[str, TransitionConfig] = {}
        self._budget: Optional[LODBudget] = None
        self._entity_to_group: Dict[str, str] = {}
        self._total_evaluations: int = 0
        self._total_transitions_triggered: int = 0
        self._global_strategy: SelectionStrategy = SelectionStrategy.DISTANCE_BASED

    @classmethod
    def get_instance(cls) -> "LODSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- LOD Group Management ----

    def create_lod_group(self,
                         entity_id: str,
                         mesh_entries: Optional[List[Dict[str, Any]]] = None) -> LODGroup:
        existing_id = self._entity_to_group.get(entity_id)
        if existing_id is not None and existing_id in self._groups:
            return self._groups[existing_id]

        if len(self._groups) >= self.MAX_LOD_GROUPS:
            raise RuntimeError(
                f"LOD group limit reached ({self.MAX_LOD_GROUPS})"
            )

        group = LODGroup(
            entity_id=entity_id,
            name=f"LODGroup_{entity_id}",
            selection_strategy=self._global_strategy,
        )
        self._groups[group.id] = group
        self._entity_to_group[entity_id] = group.id

        if mesh_entries:
            for entry_data in mesh_entries:
                self.add_lod_level(
                    group_id=group.id,
                    level=entry_data.get("level", "LOD0_ULTRA"),
                    mesh_ref=entry_data.get("mesh_ref", ""),
                    distance_threshold=entry_data.get("distance_threshold", 0.0),
                )

        return group

    def add_lod_level(self,
                      group_id: str,
                      level: str = "LOD0_ULTRA",
                      mesh_ref: str = "",
                      distance_threshold: float = 0.0) -> MeshLODEntry:
        group = self._groups.get(group_id)
        if group is None:
            raise ValueError(f"LOD group not found: {group_id}")

        if len(group.entries) >= self.MAX_LOD_ENTRIES_PER_GROUP:
            raise ValueError(
                f"LOD group {group_id} has reached maximum entries "
                f"({self.MAX_LOD_ENTRIES_PER_GROUP})"
            )

        try:
            lod_level = LODLevel(level.lower())
        except ValueError:
            lod_level = LODLevel.LOD0_ULTRA

        for entry in group.entries.values():
            if entry.level == lod_level:
                entry.mesh_ref = mesh_ref
                entry.distance_threshold = distance_threshold
                return entry

        actual_distance = (
            distance_threshold
            if distance_threshold > 0.0
            else _LOD_DISTANCE_FALLOFF.get(lod_level, 80.0)
        )
        actual_coverage = _LOD_SCREEN_COVERAGE.get(lod_level, 0.05)

        entry = MeshLODEntry(
            group_id=group_id,
            level=lod_level,
            mesh_ref=mesh_ref,
            distance_threshold=actual_distance,
            screen_coverage_threshold=actual_coverage,
        )
        group.entries[entry.id] = entry

        if not group.entries or lod_level == LODLevel.LOD0_ULTRA:
            group.active_level = lod_level

        return entry

    # ---- Transition Configuration ----

    def set_transition(self,
                       group_id: str,
                       transition_type: str = "smooth_blend",
                       duration: float = 0.3) -> TransitionConfig:
        group = self._groups.get(group_id)
        if group is None:
            raise ValueError(f"LOD group not found: {group_id}")

        try:
            tt = TransitionType(transition_type.lower())
        except ValueError:
            tt = TransitionType.SMOOTH_BLEND

        if group.transition_id and group.transition_id in self._transitions:
            config = self._transitions[group.transition_id]
            config.transition_type = tt
            config.duration = max(0.0, duration)
            return config

        config = TransitionConfig(
            group_id=group_id,
            transition_type=tt,
            duration=max(0.0, duration),
        )
        self._transitions[config.id] = config
        group.transition_id = config.id
        return config

    def get_transition(self, group_id: str) -> Optional[TransitionConfig]:
        group = self._groups.get(group_id)
        if group is None or not group.transition_id:
            return None
        return self._transitions.get(group.transition_id)

    # ---- LOD Evaluation ----

    def evaluate_lod(self,
                     group_id: str,
                     camera_distance: float) -> LODLevel:
        group = self._groups.get(group_id)
        if group is None:
            return LODLevel.LOD0_ULTRA

        if not group.is_enabled:
            return group.active_level

        if group.forced_level is not None:
            return group.forced_level

        self._total_evaluations += 1

        strategy = group.selection_strategy

        if strategy == SelectionStrategy.DISTANCE_BASED:
            return self._evaluate_distance(group, camera_distance)

        elif strategy == SelectionStrategy.SCREEN_COVERAGE:
            return self._evaluate_screen_coverage(group, camera_distance)

        elif strategy == SelectionStrategy.BUDGET_BASED:
            return self._evaluate_budget(group)

        elif strategy == SelectionStrategy.HYBRID:
            dist_level = self._evaluate_distance(group, camera_distance)
            coverage_level = self._evaluate_screen_coverage(group, camera_distance)
            resolved = max(
                dist_level, coverage_level,
                key=lambda lv: _LOD_LEVEL_ORDER.index(lv),
            )
            return self._clamp_by_budget(resolved, group)

        return LODLevel.LOD0_ULTRA

    def _evaluate_distance(self,
                           group: LODGroup,
                           distance: float) -> LODLevel:
        selected = LODLevel.LOD0_ULTRA
        for level in _LOD_LEVEL_ORDER:
            threshold = _LOD_DISTANCE_FALLOFF.get(level, float("inf"))
            entry = self._find_entry_by_level(group, level)
            if entry is not None:
                threshold = entry.distance_threshold
            if distance <= threshold:
                selected = level
                break
        else:
            selected = LODLevel.LOD5_IMPOSTER

        previous = group.active_level
        if selected != previous:
            self._trigger_transition(group, previous, selected)
        group.active_level = selected
        return selected

    def _evaluate_screen_coverage(self,
                                   group: LODGroup,
                                   distance: float) -> LODLevel:
        if distance < 0.01:
            return LODLevel.LOD0_ULTRA

        fov_rad = math.radians(group.screen_coverage_fov)
        projected_size = 1.0 / (distance * math.tan(fov_rad * 0.5))
        coverage = projected_size / group.screen_coverage_height

        selected = LODLevel.LOD5_IMPOSTER
        for level in reversed(_LOD_LEVEL_ORDER):
            threshold = _LOD_SCREEN_COVERAGE.get(level, 0.0)
            entry = self._find_entry_by_level(group, level)
            if entry is not None:
                threshold = entry.screen_coverage_threshold
            if coverage >= threshold:
                selected = level
                break

        previous = group.active_level
        if selected != previous:
            self._trigger_transition(group, previous, selected)
        group.active_level = selected
        return selected

    def _evaluate_budget(self, group: LODGroup) -> LODLevel:
        if self._budget is None or not self._budget.is_enforced:
            return group.active_level

        budget = self._budget
        ratio = budget.current_triangles / max(1, budget.max_triangles)

        if ratio < 0.4:
            return min(group.active_level, LODLevel.LOD1_HIGH,
                       key=lambda lv: _LOD_LEVEL_ORDER.index(lv))

        if ratio < 0.7:
            target = LODLevel.LOD2_MEDIUM
        elif ratio < 0.9:
            target = LODLevel.LOD3_LOW
        elif ratio < 0.95:
            target = LODLevel.LOD4_MINIMAL
        else:
            target = LODLevel.LOD5_IMPOSTER

        selected = target
        previous = group.active_level
        if selected != previous:
            self._trigger_transition(group, previous, selected)
        group.active_level = selected
        return selected

    def _clamp_by_budget(self,
                          desired: LODLevel,
                          group: LODGroup) -> LODLevel:
        if self._budget is None or not self._budget.is_enforced:
            return desired

        budget = self._budget
        ratio = budget.current_triangles / max(1, budget.max_triangles)

        if ratio > 0.85:
            desired_idx = _LOD_LEVEL_ORDER.index(desired)
            clamped = min(desired_idx + 1, len(_LOD_LEVEL_ORDER) - 1)
            return _LOD_LEVEL_ORDER[clamped]

        return desired

    def _find_entry_by_level(self,
                              group: LODGroup,
                              level: LODLevel) -> Optional[MeshLODEntry]:
        for entry in group.entries.values():
            if entry.level == level and entry.is_active:
                return entry
        return None

    def _trigger_transition(self,
                            group: LODGroup,
                            from_level: LODLevel,
                            to_level: LODLevel) -> None:
        self._total_transitions_triggered += 1

        config = self.get_transition(group.id)
        if config is None or not config.is_enabled:
            return

        if config.transition_type == TransitionType.POP:
            group.active_level = to_level

    # ---- Global Budget ----

    def set_global_budget(self,
                          max_triangles: int = 100000,
                          max_draw_calls: int = 500) -> LODBudget:
        if self._budget is None:
            self._budget = LODBudget(
                max_triangles=max(1, max_triangles),
                max_draw_calls=max(1, max_draw_calls),
            )
        else:
            self._budget.max_triangles = max(1, max_triangles)
            self._budget.max_draw_calls = max(1, max_draw_calls)
        return self._budget

    def get_global_budget(self) -> Optional[LODBudget]:
        return self._budget

    def update_budget_usage(self,
                            triangles: int = 0,
                            draw_calls: int = 0) -> None:
        if self._budget is not None:
            self._budget.current_triangles = max(0, triangles)
            self._budget.current_draw_calls = max(0, draw_calls)

    def enforce_budget(self, enforce: bool = True) -> None:
        if self._budget is not None:
            self._budget.is_enforced = enforce

    # ---- Force LOD ----

    def force_lod(self,
                  entity_id: str,
                  level: str) -> bool:
        group_id = self._entity_to_group.get(entity_id)
        if group_id is None:
            return False

        group = self._groups.get(group_id)
        if group is None:
            return False

        try:
            forced = LODLevel(level.lower())
        except ValueError:
            return False

        group.forced_level = forced
        group.active_level = forced
        return True

    def clear_forced_lod(self, entity_id: str) -> bool:
        group_id = self._entity_to_group.get(entity_id)
        if group_id is None:
            return False

        group = self._groups.get(group_id)
        if group is None:
            return False

        group.forced_level = None
        return True

    # ---- Group Listing & Access ----

    def list_lod_groups(self) -> List[LODGroup]:
        return sorted(self._groups.values(), key=lambda g: g.created_at)

    def get_lod_group(self, group_id: str) -> Optional[LODGroup]:
        return self._groups.get(group_id)

    def get_lod_group_for_entity(self, entity_id: str) -> Optional[LODGroup]:
        group_id = self._entity_to_group.get(entity_id)
        if group_id is None:
            return None
        return self._groups.get(group_id)

    def remove_lod_group(self, group_id: str) -> bool:
        group = self._groups.pop(group_id, None)
        if group is None:
            return False

        if group.entity_id in self._entity_to_group:
            del self._entity_to_group[group.entity_id]

        if group.transition_id:
            self._transitions.pop(group.transition_id, None)

        return True

    # ---- Strategy Settings ----

    def set_selection_strategy(self,
                                group_id: str,
                                strategy: str) -> bool:
        group = self._groups.get(group_id)
        if group is None:
            return False

        try:
            ss = SelectionStrategy(strategy.lower())
        except ValueError:
            return False

        group.selection_strategy = ss
        return True

    def set_global_strategy(self, strategy: str) -> bool:
        try:
            ss = SelectionStrategy(strategy.lower())
        except ValueError:
            return False
        self._global_strategy = ss
        return True

    def set_screen_coverage_params(self,
                                    group_id: str,
                                    fov: float = 60.0,
                                    screen_height: float = 1080.0) -> bool:
        group = self._groups.get(group_id)
        if group is None:
            return False
        group.screen_coverage_fov = max(1.0, min(179.0, fov))
        group.screen_coverage_height = max(1.0, screen_height)
        return True

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        strategy_counts: Dict[str, int] = {}
        level_counts: Dict[str, int] = {}
        groups_with_transitions = 0

        for group in self._groups.values():
            strat = group.selection_strategy.value
            strategy_counts[strat] = strategy_counts.get(strat, 0) + 1

            lvl = group.active_level.value
            level_counts[lvl] = level_counts.get(lvl, 0) + 1

            if group.transition_id:
                groups_with_transitions += 1

        forced_groups = sum(
            1 for g in self._groups.values() if g.forced_level is not None
        )

        budget_stats = None
        if self._budget is not None:
            budget_stats = self._budget.to_dict()

        return {
            "total_groups": len(self._groups),
            "total_entities": len(self._entity_to_group),
            "total_entries": sum(len(g.entries) for g in self._groups.values()),
            "groups_with_transitions": groups_with_transitions,
            "forced_lod_groups": forced_groups,
            "strategy_distribution": strategy_counts,
            "active_level_distribution": level_counts,
            "total_evaluations": self._total_evaluations,
            "total_transitions_triggered": self._total_transitions_triggered,
            "global_strategy": self._global_strategy.value,
            "max_groups": self.MAX_LOD_GROUPS,
            "max_entries_per_group": self.MAX_LOD_ENTRIES_PER_GROUP,
            "budget": budget_stats,
        }

    # ---- Reset ----

    def reset(self) -> None:
        with self._lock:
            self._groups.clear()
            self._transitions.clear()
            self._budget = None
            self._entity_to_group.clear()
            self._total_evaluations = 0
            self._total_transitions_triggered = 0
            self._global_strategy = SelectionStrategy.DISTANCE_BASED


def get_lod_system() -> LODSystem:
    return LODSystem.get_instance()