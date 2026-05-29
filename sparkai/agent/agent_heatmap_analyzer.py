"""
SparkLabs Agent - Heatmap Analyzer

AI-driven player behavior heatmap analysis system for AI-native game design.
Processes player position data, identifies hotspots, dead zones, pathing
patterns, and generates actionable design insights from spatial telemetry.

Architecture:
  HeatmapAnalyzer (Singleton)
    |-- HeatmapGrid (spatial grid with weighted cell data)
    |-- HotspotDetection (identified cluster of interest)
    |-- DesignInsight (actionable design recommendation)

Heatmap Types:
  POSITION, DEATH, DAMAGE_TAKEN, DAMAGE_DEALT, ITEM_PICKUP, INTERACTION,
  PLAYER_PATH

Grid Resolutions:
  COARSE (16x16 cells), STANDARD (32x32), FINE (64x64), ULTRA_FINE (128x128)

Hotspot Categories:
  DANGER_ZONE, SAFE_ZONE, TRAFFIC_HUB, UNDISCOVERED, OVERPOPULATED, IDEAL_BALANCE

Analysis Modes:
  REAL_TIME, RETROSPECTIVE, COMPARATIVE, PREDICTIVE

Usage:
    analyzer = get_heatmap_analyzer()
    grid = analyzer.create_grid("level_01", HeatmapType.POSITION, GridResolution.STANDARD, 100, 100)
    analyzer.record_event(grid.id, 42.5, 67.3, 1.0)
    hotspots = analyzer.detect_hotspots(grid.id)
    insights = analyzer.generate_insights(grid.id)
    stats = analyzer.get_stats()
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


class HeatmapType(Enum):
    POSITION = "position"
    DEATH = "death"
    DAMAGE_TAKEN = "damage_taken"
    DAMAGE_DEALT = "damage_dealt"
    ITEM_PICKUP = "item_pickup"
    INTERACTION = "interaction"
    PLAYER_PATH = "player_path"


class GridResolution(Enum):
    COARSE = "coarse"
    STANDARD = "standard"
    FINE = "fine"
    ULTRA_FINE = "ultra_fine"

    @property
    def cell_dimension(self) -> int:
        _mapping = {
            GridResolution.COARSE: 16,
            GridResolution.STANDARD: 32,
            GridResolution.FINE: 64,
            GridResolution.ULTRA_FINE: 128,
        }
        return _mapping[self]


class HotspotCategory(Enum):
    DANGER_ZONE = "danger_zone"
    SAFE_ZONE = "safe_zone"
    TRAFFIC_HUB = "traffic_hub"
    UNDISCOVERED = "undiscovered"
    OVERPOPULATED = "overpopulated"
    IDEAL_BALANCE = "ideal_balance"


class AnalysisMode(Enum):
    REAL_TIME = "real_time"
    RETROSPECTIVE = "retrospective"
    COMPARATIVE = "comparative"
    PREDICTIVE = "predictive"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class HeatmapGrid:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    type: HeatmapType = HeatmapType.POSITION
    resolution: GridResolution = GridResolution.STANDARD
    width: float = 100.0
    height: float = 100.0
    cells: List[float] = field(default_factory=list)
    max_value: float = 0.0
    min_value: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    scene_id: str = ""

    def __post_init__(self) -> None:
        if not self.cells:
            dim = self.resolution.cell_dimension
            self.cells = [0.0] * (dim * dim)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "resolution": self.resolution.value,
            "width": self.width,
            "height": self.height,
            "cell_count": len(self.cells),
            "max_value": self.max_value,
            "min_value": self.min_value,
            "scene_id": self.scene_id,
            "created_at": self.created_at,
        }

    def _cell_index(self, x: float, y: float) -> int:
        dim = self.resolution.cell_dimension
        col = max(0, min(dim - 1, int(x / self.width * dim)))
        row = max(0, min(dim - 1, int(y / self.height * dim)))
        return row * dim + col

    def _cell_center(self, index: int) -> Tuple[float, float]:
        dim = self.resolution.cell_dimension
        col = index % dim
        row = index // dim
        cx = (col + 0.5) * self.width / dim
        cy = (row + 0.5) * self.height / dim
        return (cx, cy)


@dataclass
class HotspotDetection:
    grid_id: str = ""
    category: HotspotCategory = HotspotCategory.TRAFFIC_HUB
    center_x: float = 0.0
    center_y: float = 0.0
    radius: float = 0.0
    intensity: float = 0.0
    affected_cells: List[int] = field(default_factory=list)
    detected_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid_id": self.grid_id,
            "category": self.category.value,
            "center_x": round(self.center_x, 2),
            "center_y": round(self.center_y, 2),
            "radius": round(self.radius, 2),
            "intensity": round(self.intensity, 3),
            "affected_cell_count": len(self.affected_cells),
            "detected_at": self.detected_at,
        }


@dataclass
class DesignInsight:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    description: str = ""
    severity: str = "info"
    affected_area: str = ""
    suggestion: str = ""
    confidence: float = 0.0
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "affected_area": self.affected_area,
            "suggestion": self.suggestion,
            "confidence": round(self.confidence, 2),
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# HeatmapAnalyzer Singleton
# ---------------------------------------------------------------------------


class HeatmapAnalyzer:
    """AI-driven player behavior heatmap analysis system.

    Processes spatial player telemetry to detect hotspots, dead zones,
    pathing patterns, and design anomalies. Generates actionable insights
    for level designers to improve map flow, risk distribution, and
    content placement.

    Thread-safe via RLock with double-check locking in get_instance.
    """

    _instance: Optional["HeatmapAnalyzer"] = None
    _lock: threading.RLock = threading.RLock()

    _DEFAULT_RADIUS_MULTIPLIER = 0.08
    _SIGNIFICANCE_THRESHOLD = 0.05
    _DENSITY_CLUSTER_EPSILON = 0.15
    _MIN_CLUSTER_SIZE = 3
    _PATHING_RESOLUTION_STEPS = 20
    _TRAFFIC_THRESHOLD_HIGH = 2.0
    _TRAFFIC_THRESHOLD_LOW = 0.1
    _DANGER_PENALTY_WEIGHT = 3.0
    _MAX_GRIDS = 500
    _MAX_HOTSPOTS_PER_GRID = 200
    _MAX_INSIGHTS = 1000

    @classmethod
    def get_instance(cls) -> "HeatmapAnalyzer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._heatmap_grids: Dict[str, HeatmapGrid] = {}
        self._hotspots: Dict[str, List[HotspotDetection]] = {}
        self._insights: List[DesignInsight] = []
        self._stats: Dict[str, int] = {
            "grids_created": 0,
            "events_recorded": 0,
            "hotspots_detected": 0,
            "insights_generated": 0,
            "pathing_analyses": 0,
            "comparisons_performed": 0,
        }
        self._initialized: bool = True

    # ------------------------------------------------------------------
    # Grid Management
    # ------------------------------------------------------------------

    def create_grid(
        self,
        scene_id: str,
        type: HeatmapType = HeatmapType.POSITION,
        resolution: GridResolution = GridResolution.STANDARD,
        width: float = 100.0,
        height: float = 100.0,
    ) -> HeatmapGrid:
        with self._lock:
            if len(self._heatmap_grids) >= self._MAX_GRIDS:
                oldest_id = next(iter(self._heatmap_grids))
                del self._heatmap_grids[oldest_id]
                self._hotspots.pop(oldest_id, None)

            grid = HeatmapGrid(
                type=type,
                resolution=resolution,
                width=width,
                height=height,
                scene_id=scene_id,
            )
            self._heatmap_grids[grid.id] = grid
            self._hotspots[grid.id] = []
            self._stats["grids_created"] += 1
            return grid

    def get_grid(self, grid_id: str) -> Optional[HeatmapGrid]:
        return self._heatmap_grids.get(grid_id)

    # ------------------------------------------------------------------
    # Event Recording
    # ------------------------------------------------------------------

    def record_event(self, grid_id: str, x: float, y: float, weight: float = 1.0) -> None:
        grid = self._heatmap_grids.get(grid_id)
        if grid is None:
            return

        idx = grid._cell_index(x, y)
        grid.cells[idx] += weight

        if grid.cells[idx] > grid.max_value:
            grid.max_value = grid.cells[idx]
        if grid.cells[idx] < grid.min_value or len(grid.cells) == 0:
            grid.min_value = grid.cells[idx]

        self._stats["events_recorded"] += 1

    def record_batch(
        self, grid_id: str, events: List[Tuple[float, float, float]]
    ) -> None:
        grid = self._heatmap_grids.get(grid_id)
        if grid is None:
            return

        for x, y, weight in events:
            idx = grid._cell_index(x, y)
            grid.cells[idx] += weight
            if grid.cells[idx] > grid.max_value:
                grid.max_value = grid.cells[idx]

        min_cell = min(grid.cells) if grid.cells else 0.0
        grid.min_value = min_cell
        self._stats["events_recorded"] += len(events)

    # ------------------------------------------------------------------
    # Hotspot Detection
    # ------------------------------------------------------------------

    def detect_hotspots(self, grid_id: str) -> List[HotspotDetection]:
        grid = self._heatmap_grids.get(grid_id)
        if grid is None or not grid.cells:
            return []

        dim = grid.resolution.cell_dimension
        total_sum = sum(grid.cells)
        if total_sum <= 0:
            return []

        mean_val = total_sum / len(grid.cells)
        threshold = mean_val * 1.5

        above_threshold: Set[int] = set()
        for i, val in enumerate(grid.cells):
            if val >= threshold and val > 0:
                above_threshold.add(i)

        if not above_threshold:
            above_threshold = set(
                i for i, val in enumerate(grid.cells)
                if val >= mean_val and val > 0
            )

        visited: Set[int] = set()
        clusters: List[Set[int]] = []

        for cell_idx in sorted(above_threshold):
            if cell_idx in visited:
                continue
            cluster: Set[int] = set()
            stack = [cell_idx]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                cluster.add(current)
                neighbors = self._get_neighbors(current, dim)
                for nb in neighbors:
                    if nb in above_threshold and nb not in visited:
                        stack.append(nb)
            if len(cluster) >= self._MIN_CLUSTER_SIZE:
                clusters.append(cluster)

        hotspots: List[HotspotDetection] = []
        for cluster in clusters:
            if len(hotspots) >= self._MAX_HOTSPOTS_PER_GRID:
                break

            cluster_list = list(cluster)
            sum_x = 0.0
            sum_y = 0.0
            total_weight = 0.0
            for c in cluster_list:
                cx, cy = grid._cell_center(c)
                w = grid.cells[c]
                sum_x += cx * w
                sum_y += cy * w
                total_weight += w

            center_x = sum_x / total_weight if total_weight > 0 else 0.0
            center_y = sum_y / total_weight if total_weight > 0 else 0.0

            max_dist = 0.0
            for c in cluster_list:
                cx, cy = grid._cell_center(c)
                dist = math.sqrt((cx - center_x) ** 2 + (cy - center_y) ** 2)
                if dist > max_dist:
                    max_dist = dist
            radius = max_dist + grid.width / dim * 1.5

            avg_intensity = sum(grid.cells[c] for c in cluster_list) / len(cluster_list)
            normalized_intensity = avg_intensity / grid.max_value if grid.max_value > 0 else 0.0

            category = self._classify_hotspot(cluster_list, grid)

            hotspot = HotspotDetection(
                grid_id=grid_id,
                category=category,
                center_x=center_x,
                center_y=center_y,
                radius=radius,
                intensity=normalized_intensity,
                affected_cells=cluster_list,
            )
            hotspots.append(hotspot)

        with self._lock:
            self._hotspots[grid_id] = hotspots
            self._stats["hotspots_detected"] += len(hotspots)

        return hotspots

    def _get_neighbors(self, cell_idx: int, dim: int) -> List[int]:
        neighbors = []
        row = cell_idx // dim
        col = cell_idx % dim
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < dim and 0 <= nc < dim:
                    neighbors.append(nr * dim + nc)
        return neighbors

    def _classify_hotspot(
        self, cluster: List[int], grid: HeatmapGrid
    ) -> HotspotCategory:
        total_weight = sum(grid.cells[c] for c in cluster)
        avg_weight = total_weight / len(cluster)

        if grid.max_value > 0:
            norm_avg = avg_weight / grid.max_value
        else:
            norm_avg = 0.0

        if grid.type == HeatmapType.DEATH:
            return HotspotCategory.DANGER_ZONE if norm_avg > 0.5 else HotspotCategory.TRAFFIC_HUB

        if grid.type == HeatmapType.DAMAGE_TAKEN:
            return HotspotCategory.DANGER_ZONE if norm_avg > 0.4 else HotspotCategory.SAFE_ZONE

        if grid.type == HeatmapType.POSITION:
            if norm_avg > 0.8:
                return HotspotCategory.OVERPOPULATED
            if norm_avg < 0.1:
                return HotspotCategory.UNDISCOVERED
            if 0.4 <= norm_avg <= 0.7:
                return HotspotCategory.IDEAL_BALANCE
            return HotspotCategory.TRAFFIC_HUB

        if grid.type == HeatmapType.ITEM_PICKUP:
            if norm_avg > 0.7:
                return HotspotCategory.OVERPOPULATED
            if norm_avg < 0.05:
                return HotspotCategory.UNDISCOVERED
            return HotspotCategory.TRAFFIC_HUB

        if norm_avg > 0.6:
            return HotspotCategory.OVERPOPULATED
        if norm_avg < 0.05:
            return HotspotCategory.UNDISCOVERED
        if 0.3 <= norm_avg <= 0.6:
            return HotspotCategory.IDEAL_BALANCE
        return HotspotCategory.TRAFFIC_HUB

    def get_hotspots(self, grid_id: str) -> List[HotspotDetection]:
        return self._hotspots.get(grid_id, [])

    # ------------------------------------------------------------------
    # Pathing Analysis
    # ------------------------------------------------------------------

    def analyze_pathing(
        self,
        grid_id: str,
        player_trajectories: List[List[Tuple[float, float]]],
    ) -> Dict[str, Any]:
        grid = self._heatmap_grids.get(grid_id)
        if grid is None or not player_trajectories:
            return {"error": "grid not found or no trajectories provided"}

        dim = grid.resolution.cell_dimension

        path_counts: Dict[int, int] = {}
        for trajectory in player_trajectories:
            if len(trajectory) < 2:
                continue
            for i in range(len(trajectory)):
                x, y = trajectory[i]
                idx = grid._cell_index(x, y)
                path_counts[idx] = path_counts.get(idx, 0) + 1

        total_cells = dim * dim
        visited_cells = len(path_counts)
        coverage_ratio = visited_cells / total_cells if total_cells > 0 else 0.0

        if path_counts:
            max_count = max(path_counts.values())
            sorted_cells = sorted(path_counts.items(), key=lambda kv: kv[1], reverse=True)
            high_traffic = [
                {"index": idx, "count": cnt, "center": list(grid._cell_center(idx))}
                for idx, cnt in sorted_cells[:10]
            ]
            zero_traffic_indices = [
                i for i in range(total_cells) if i not in path_counts
            ]
            zero_traffic_count = len(zero_traffic_indices)
        else:
            max_count = 0
            high_traffic = []
            zero_traffic_count = total_cells

        trajectory_lengths = [len(t) for t in player_trajectories]
        avg_length = sum(trajectory_lengths) / len(trajectory_lengths) if trajectory_lengths else 0.0

        segment_directions: Dict[str, int] = {}
        for trajectory in player_trajectories:
            for i in range(len(trajectory) - 1):
                x1, y1 = trajectory[i]
                x2, y2 = trajectory[i + 1]
                dx = x2 - x1
                dy = y2 - y1
                if abs(dx) > abs(dy):
                    direction = "east" if dx >= 0 else "west"
                else:
                    direction = "south" if dy >= 0 else "north"
                segment_directions[direction] = segment_directions.get(direction, 0) + 1

        total_segments = sum(segment_directions.values()) or 1
        directional_bias = {
            d: round(c / total_segments, 3) for d, c in segment_directions.items()
        }

        dominant_dir = max(segment_directions, key=segment_directions.get) if segment_directions else "none"

        if coverage_ratio < 0.2:
            exploration_label = "under_explored"
        elif coverage_ratio < 0.5:
            exploration_label = "partially_explored"
        elif coverage_ratio < 0.8:
            exploration_label = "well_explored"
        else:
            exploration_label = "fully_mapped"

        self._stats["pathing_analyses"] += 1

        return {
            "grid_id": grid_id,
            "trajectory_count": len(player_trajectories),
            "avg_trajectory_length": round(avg_length, 1),
            "coverage_ratio": round(coverage_ratio, 4),
            "visited_cells": visited_cells,
            "total_cells": total_cells,
            "zero_traffic_cells": zero_traffic_count,
            "max_pass_count": max_count,
            "high_traffic_cells": high_traffic,
            "directional_bias": directional_bias,
            "dominant_direction": dominant_dir,
            "exploration_label": exploration_label,
        }

    # ------------------------------------------------------------------
    # Insight Generation
    # ------------------------------------------------------------------

    def generate_insights(self, grid_id: str) -> List[DesignInsight]:
        grid = self._heatmap_grids.get(grid_id)
        if grid is None:
            return []

        hotspots = self._hotspots.get(grid_id)
        if hotspots is None:
            hotspots = self.detect_hotspots(grid_id)

        insights: List[DesignInsight] = []

        for hs in hotspots:
            if hs.category == HotspotCategory.DANGER_ZONE:
                if hs.intensity > 0.7:
                    insights.append(DesignInsight(
                        title="Critical Danger Zone Detected",
                        description=(
                            f"A high-intensity danger zone at ({hs.center_x:.1f}, {hs.center_y:.1f}) "
                            f"with radius {hs.radius:.1f} affects {len(hs.affected_cells)} cells. "
                            f"Player death concentration is {hs.intensity:.0%} of maximum observed."
                        ),
                        severity="critical",
                        affected_area=f"({hs.center_x:.1f}, {hs.center_y:.1f}) radius {hs.radius:.1f}",
                        suggestion=(
                            "Consider reducing enemy density, adding cover objects, "
                            "or relocating the hazard source to reduce unfair difficulty."
                        ),
                        confidence=min(0.95, 0.5 + hs.intensity),
                    ))
                else:
                    insights.append(DesignInsight(
                        title="Moderate Danger Zone",
                        description=(
                            f"A moderate-risk zone at ({hs.center_x:.1f}, {hs.center_y:.1f}) "
                            f"covers {len(hs.affected_cells)} cells. "
                            f"Some players may find this area challenging."
                        ),
                        severity="warning",
                        affected_area=f"({hs.center_x:.1f}, {hs.center_y:.1f}) radius {hs.radius:.1f}",
                        suggestion=(
                            "Verify difficulty progression leads players through this area "
                            "with adequate preparation."
                        ),
                        confidence=0.5 + hs.intensity * 0.3,
                    ))

            elif hs.category == HotspotCategory.UNDISCOVERED:
                insights.append(DesignInsight(
                    title="Underutilized Area",
                    description=(
                        f"An underutilized region at ({hs.center_x:.1f}, {hs.center_y:.1f}) "
                        f"has abnormally low activity across {len(hs.affected_cells)} cells."
                    ),
                    severity="info",
                    affected_area=f"({hs.center_x:.1f}, {hs.center_y:.1f}) radius {hs.radius:.1f}",
                    suggestion=(
                        "Add incentives such as collectibles, shortcuts, or visual landmarks "
                        "to encourage exploration of this area."
                    ),
                    confidence=0.6,
                ))

            elif hs.category == HotspotCategory.OVERPOPULATED:
                insights.append(DesignInsight(
                    title="Congestion Area Identified",
                    description=(
                        f"A heavily congested area at ({hs.center_x:.1f}, {hs.center_y:.1f}) "
                        f"with {len(hs.affected_cells)} cells showing extreme player density."
                    ),
                    severity="warning",
                    affected_area=f"({hs.center_x:.1f}, {hs.center_y:.1f}) radius {hs.radius:.1f}",
                    suggestion=(
                        "Consider widening pathways, adding alternative routes, "
                        "or distributing content more evenly across the map."
                    ),
                    confidence=0.55 + hs.intensity * 0.25,
                ))

            elif hs.category == HotspotCategory.IDEAL_BALANCE:
                insights.append(DesignInsight(
                    title="Well-Balanced Zone",
                    description=(
                        f"An optimally balanced area at ({hs.center_x:.1f}, {hs.center_y:.1f}) "
                        f"shows healthy player engagement across {len(hs.affected_cells)} cells."
                    ),
                    severity="info",
                    affected_area=f"({hs.center_x:.1f}, {hs.center_y:.1f}) radius {hs.radius:.1f}",
                    suggestion="This area is working well. Use it as a reference for other zones.",
                    confidence=0.7,
                ))

            elif hs.category == HotspotCategory.TRAFFIC_HUB:
                insights.append(DesignInsight(
                    title="Traffic Hub",
                    description=(
                        f"A traffic convergence point at ({hs.center_x:.1f}, {hs.center_y:.1f}) "
                        f"where player paths frequently intersect."
                    ),
                    severity="info",
                    affected_area=f"({hs.center_x:.1f}, {hs.center_y:.1f}) radius {hs.radius:.1f}",
                    suggestion=(
                        "Ensure adequate visual cues and navigation aids at this junction. "
                        "Consider placing landmarks or signage."
                    ),
                    confidence=0.65,
                ))

            elif hs.category == HotspotCategory.SAFE_ZONE:
                insights.append(DesignInsight(
                    title="Safe Zone Confirmed",
                    description=(
                        f"A low-risk area at ({hs.center_x:.1f}, {hs.center_y:.1f}) "
                        f"with minimal damage events across {len(hs.affected_cells)} cells."
                    ),
                    severity="info",
                    affected_area=f"({hs.center_x:.1f}, {hs.center_y:.1f}) radius {hs.radius:.1f}",
                    suggestion="This area provides good respite for players. Maintain its safety profile.",
                    confidence=0.7,
                ))

        if not hotspots:
            data_coverage = sum(1 for v in grid.cells if v > 0) / max(1, len(grid.cells))
            if data_coverage < 0.1:
                insights.append(DesignInsight(
                    title="Insufficient Data Coverage",
                    description=(
                        f"Only {data_coverage:.0%} of grid cells contain event data. "
                        f"More telemetry is needed for meaningful analysis."
                    ),
                    severity="info",
                    affected_area="entire grid",
                    suggestion=(
                        "Collect more player session data before drawing design conclusions. "
                        "Target at least 25% cell coverage."
                    ),
                    confidence=0.9,
                ))
            else:
                insights.append(DesignInsight(
                    title="Uniform Activity Distribution",
                    description=(
                        f"No significant hotspots detected across {len(grid.cells)} cells. "
                        f"Player activity is evenly distributed."
                    ),
                    severity="info",
                    affected_area="entire grid",
                    suggestion="The map layout appears to promote even exploration. Review for intentional flow design.",
                    confidence=0.55,
                ))

        for ins in insights:
            if len(self._insights) >= self._MAX_INSIGHTS:
                self._insights.pop(0)
            self._insights.append(ins)

        self._stats["insights_generated"] += len(insights)
        return insights

    def get_insights(self) -> List[DesignInsight]:
        return list(self._insights)

    # ------------------------------------------------------------------
    # Grid Comparison
    # ------------------------------------------------------------------

    def compare_grids(self, grid_a_id: str, grid_b_id: str) -> Dict[str, Any]:
        grid_a = self._heatmap_grids.get(grid_a_id)
        grid_b = self._heatmap_grids.get(grid_b_id)
        if grid_a is None or grid_b is None:
            return {"error": "one or both grids not found"}

        dim_a = grid_a.resolution.cell_dimension
        dim_b = grid_b.resolution.cell_dimension

        cell_diffs: List[float] = []
        aligned_cells: int = 0
        total_delta: float = 0.0
        max_delta: float = 0.0
        max_delta_idx: int = -1
        increased_cells: int = 0
        decreased_cells: int = 0

        min_dim = min(dim_a, dim_b)
        total_aligned = min_dim * min_dim

        for row in range(min_dim):
            for col in range(min_dim):
                idx_a = row * dim_a + col
                idx_b = row * dim_b + col
                val_a = grid_a.cells[idx_a] if idx_a < len(grid_a.cells) else 0.0
                val_b = grid_b.cells[idx_b] if idx_b < len(grid_b.cells) else 0.0
                delta = val_b - val_a
                cell_diffs.append(delta)
                total_delta += abs(delta)
                if abs(delta) > abs(max_delta):
                    max_delta = delta
                    max_delta_idx = aligned_cells
                if delta > 0:
                    increased_cells += 1
                elif delta < 0:
                    decreased_cells += 1
                aligned_cells += 1

        mean_delta = total_delta / max(1, aligned_cells)
        unchanged_cells = aligned_cells - increased_cells - decreased_cells

        correlation = 0.0
        if aligned_cells > 0 and grid_a.max_value > 0 and grid_b.max_value > 0:
            sum_a, sum_b = 0.0, 0.0
            for row in range(min_dim):
                for col in range(min_dim):
                    idx_a = row * dim_a + col
                    idx_b = row * dim_b + col
                    val_a = grid_a.cells[idx_a] if idx_a < len(grid_a.cells) else 0.0
                    val_b = grid_b.cells[idx_b] if idx_b < len(grid_b.cells) else 0.0
                    sum_a += val_a
                    sum_b += val_b
            mean_a = sum_a / total_aligned
            mean_b = sum_b / total_aligned

            cov, var_a, var_b = 0.0, 0.0, 0.0
            for row in range(min_dim):
                for col in range(min_dim):
                    idx_a = row * dim_a + col
                    idx_b = row * dim_b + col
                    val_a = grid_a.cells[idx_a] if idx_a < len(grid_a.cells) else 0.0
                    val_b = grid_b.cells[idx_b] if idx_b < len(grid_b.cells) else 0.0
                    da = val_a - mean_a
                    db = val_b - mean_b
                    cov += da * db
                    var_a += da * da
                    var_b += db * db

            denom = math.sqrt(var_a * var_b)
            correlation = cov / denom if denom > 0 else 0.0

        max_delta_center = (0.0, 0.0)
        if max_delta_idx >= 0 and max_delta_idx < min_dim * min_dim:
            col = max_delta_idx % min_dim
            row = max_delta_idx // min_dim
            max_delta_center = grid_a._cell_center(row * min_dim + col)

        hottest_a = self._get_hottest_region(grid_a)
        hottest_b = self._get_hottest_region(grid_b)

        self._stats["comparisons_performed"] += 1

        return {
            "grid_a_id": grid_a_id,
            "grid_b_id": grid_b_id,
            "grid_a_type": grid_a.type.value,
            "grid_b_type": grid_b.type.value,
            "aligned_cells": total_aligned,
            "total_absolute_delta": round(total_delta, 2),
            "mean_delta": round(mean_delta, 4),
            "max_delta": round(max_delta, 4),
            "max_delta_center": [round(v, 2) for v in max_delta_center],
            "correlation": round(correlation, 4),
            "increased_cells": increased_cells,
            "decreased_cells": decreased_cells,
            "unchanged_cells": unchanged_cells,
            "grid_a_total_weight": round(sum(grid_a.cells), 2),
            "grid_b_total_weight": round(sum(grid_b.cells), 2),
            "hottest_region_a": hottest_a,
            "hottest_region_b": hottest_b,
            "similarity_pct": round(correlation * 100, 1) if correlation > 0 else 0.0,
        }

    def _get_hottest_region(self, grid: HeatmapGrid) -> Dict[str, Any]:
        if not grid.cells or grid.max_value <= 0:
            return {"center": [0, 0], "value": 0, "cell_index": -1}

        max_idx = max(range(len(grid.cells)), key=lambda i: grid.cells[i])
        cx, cy = grid._cell_center(max_idx)
        return {
            "center": [round(cx, 2), round(cy, 2)],
            "value": round(grid.cells[max_idx], 2),
            "cell_index": max_idx,
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "grids_created": self._stats["grids_created"],
            "events_recorded": self._stats["events_recorded"],
            "hotspots_detected": self._stats["hotspots_detected"],
            "insights_generated": self._stats["insights_generated"],
            "pathing_analyses": self._stats["pathing_analyses"],
            "comparisons_performed": self._stats["comparisons_performed"],
            "active_grids": len(self._heatmap_grids),
            "total_hotspots": sum(len(hs) for hs in self._hotspots.values()),
            "total_insights": len(self._insights),
        }


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------


def get_heatmap_analyzer() -> HeatmapAnalyzer:
    return HeatmapAnalyzer.get_instance()