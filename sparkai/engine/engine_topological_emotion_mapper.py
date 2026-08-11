"""
SparkLabs Engine - Topological Emotion Mapper"""

from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class MappingPhase(Enum):
    """Phases of the topological emotion mapping cycle."""
    PROJECT = "project"        # raw affect vectors land on the manifold
    DEFORM = "deform"          # regions bend under affective flow gradients
    CLASSIFY = "classify"      # each region is labeled with a feature
    STITCH = "stitch"          # boundary discontinuities are knit together
    PERSIST = "persist"        # state is folded back and invariants refreshed


class TopologicalFeature(Enum):
    """The topological feature a region exhibits."""
    PEAK = "peak"              # local maximum of positive curvature
    SADDLE = "saddle"          # curvature changes sign across the region
    BASIN = "basin"            # local minimum of negative curvature
    RIDGE = "ridge"            # elongated band of elevated curvature
    PLATEAU = "plateau"        # nearly flat, low curvature magnitude


class BoundaryType(Enum):
    """How a region's boundary behaves under affective flow."""
    OPEN = "open"                  # flow passes freely in and out
    CLOSED = "closed"              # flow is contained within the region
    SEMI_PERMEABLE = "semi_permeable"  # flow filters through selectively
    ABSORBING = "absorbing"        # flow enters but does not leave
    REFLECTING = "reflecting"      # flow bounces back into the source


class ManifoldClass(Enum):
    """The global topological class a region belongs to."""
    SPHERE = "sphere"          # genus 0, simply connected
    TORUS = "torus"            # genus 1, one handle
    HYPERBOLIC = "hyperbolic"  # negative curvature dominates
    FOLDED = "folded"          # multiple handles, self-adjacent
    FRACTAL = "fractal"        # recursive boundary structure


class Vitality(Enum):
    """Overall vitality of the affective manifold."""
    LATENT = "latent"          # few regions, little curvature activity
    EMERGING = "emerging"      # regions present, curvature beginning to move
    ACTIVE = "active"          # healthy deformation and stitching
    SURGING = "surging"        # strong curvature flux across many regions
    SATURATED = "saturated"    # too many regions near curvature ceiling


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EmotionRegion:
    """A region of the affective manifold occupied by one emotion."""
    region_id: str
    entity_id: str                                      # the affect_key, e.g. "affect::joy"
    emotion_label: str
    curvature: float = 0.0                              # signed mean curvature
    genus: int = 0                                      # number of handles
    boundary_type: BoundaryType = BoundaryType.OPEN
    feature: TopologicalFeature = TopologicalFeature.PLATEAU
    manifold_class: ManifoldClass = ManifoldClass.SPHERE
    euler_characteristic: int = 2                       # 2 - 2*genus for closed surfaces
    vitality: Vitality = Vitality.LATENT
    area_units: float = 1.0                             # extent of the region on the manifold
    neighbors: List[str] = field(default_factory=list)  # adjacent region_ids
    last_projected_at: float = 0.0
    last_stitched_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MappingConfig:
    """Tuning parameters for the mapping cycle."""
    max_regions: int = 200
    curvature_floor: float = -2.0
    curvature_ceiling: float = 2.0
    deformation_rate: float = 0.22
    stitch_tolerance: float = 0.08
    genus_max: int = 5
    projection_decay: float = 0.94


# =============================================================================
# Mapper
# =============================================================================

class TopologicalEmotionMapper:
    """
    Thread-safe singleton orchestrating the topological emotion manifold.

    Usage:
        mapper = TopologicalEmotionMapper.get_instance()
        mapper.register_region(entity_id="affect::joy", emotion_label="joy")
        mapper.cycle()
        region = mapper.get_region(region_id)
    """

    _instance: Optional["TopologicalEmotionMapper"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    _MAX_REGIONS = 200
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        # Internal dict is keyed by entity_id (the affect_key), NOT by region_id.
        self._regions: Dict[str, EmotionRegion] = {}
        self._phase: MappingPhase = MappingPhase.PROJECT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._config: MappingConfig = MappingConfig()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "TopologicalEmotionMapper":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> Dict[str, Any]:
        self._stats = {
            "cycles_completed": 0,
            "uptime_started_at": time.time(),
            "regions_registered": 0,
            "phase_runs": 0,
            "projections_applied": 0,
            "deformations": 0,
            "features_classified": 0,
            "stitches_performed": 0,
            "euler_updates": 0,
            "events_recorded": 0,
            "vitality": Vitality.LATENT.value,
            "avg_curvature": 0.0,
        }
        return self._stats

    def _update_stats(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key in self._stats and isinstance(self._stats[key], (int, float)) \
                    and isinstance(value, (int, float)):
                self._stats[key] += value
            else:
                self._stats[key] = value

    def _record_event(self, event_type: str,
                      payload: Optional[Dict[str, Any]] = None) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload or {},
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })
        self._update_stats(events_recorded=1)

    def _derive_vitality(self) -> Vitality:
        region_count = len(self._regions)
        if region_count == 0:
            return Vitality.LATENT
        magnitudes = [abs(r.curvature) for r in self._regions.values()]
        avg_magnitude = sum(magnitudes) / len(magnitudes)
        near_ceiling = sum(
            1 for r in self._regions.values()
            if abs(r.curvature) >= self._config.curvature_ceiling * 0.85
        )
        if near_ceiling >= 5:
            return Vitality.SATURATED
        if avg_magnitude >= 1.2 or region_count >= 12:
            return Vitality.SURGING
        if avg_magnitude >= 0.4 or region_count >= 4:
            return Vitality.ACTIVE
        if region_count >= 1:
            return Vitality.EMERGING
        return Vitality.LATENT

    # -------------------------------------------------------------------------
    # Region Management
    # -------------------------------------------------------------------------

    def register_region(
        self,
        entity_id: str,
        emotion_label: str,
        curvature: float = 0.0,
        genus: int = 0,
        boundary_type: BoundaryType = BoundaryType.OPEN,
    ) -> Dict[str, Any]:
        """Register a new emotion region on the manifold."""
        with self._global_lock:
            if entity_id in self._regions:
                return {"error": f"emotion region already registered for entity: {entity_id}"}
            if len(self._regions) >= self._MAX_REGIONS:
                return {"error": f"region cap reached ({self._MAX_REGIONS})"}
            region_id = f"region_{uuid.uuid4().hex[:12]}"
            region = EmotionRegion(
                region_id=region_id,
                entity_id=entity_id,
                emotion_label=emotion_label,
                curvature=self._clamp_curvature(curvature),
                genus=max(0, min(self._config.genus_max, genus)),
                boundary_type=boundary_type,
            )
            region.manifold_class = self._classify_manifold(region)
            region.feature = self._classify_feature(region.curvature)
            region.euler_characteristic = self._compute_euler(region)
            region.vitality = self._derive_vitality()
            self._regions[entity_id] = region
            self._update_stats(regions_registered=1)
            self._record_event("region_registered", {
                "region_id": region_id,
                "entity_id": entity_id,
                "emotion_label": emotion_label,
            })
            return self._region_to_dict(region)

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single mapping cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            if not self._regions:
                self._seed_synthetic_regions()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = MappingPhase.PROJECT
            phase_outputs.append({"phase": self._phase.value,
                                  "result": self._phase_project()})
            self._phase = MappingPhase.DEFORM
            phase_outputs.append({"phase": self._phase.value,
                                  "result": self._phase_deform()})
            self._phase = MappingPhase.CLASSIFY
            phase_outputs.append({"phase": self._phase.value,
                                  "result": self._phase_classify()})
            self._phase = MappingPhase.STITCH
            phase_outputs.append({"phase": self._phase.value,
                                  "result": self._phase_stitch()})
            self._phase = MappingPhase.PERSIST
            phase_outputs.append({"phase": self._phase.value,
                                  "result": self._phase_persist()})
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._refresh_derived_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_project(self) -> Dict[str, Any]:
        """Project phase: raw affect vectors land on the manifold, bending curvature."""
        projected = 0
        now = time.time()
        for region in self._regions.values():
            # Synthesize an affect vector from the region's current state and a
            # small random flux representing incoming affective signal.
            flux = random.uniform(-0.3, 0.3)
            signal = region.curvature * self._config.projection_decay + flux
            region.curvature = self._clamp_curvature(signal)
            region.last_projected_at = now
            projected += 1
        self._update_stats(projections_applied=projected, phase_runs=1)
        self._record_event("phase_project", {"projected": projected})
        return {"projected": projected}

    def _phase_deform(self) -> Dict[str, Any]:
        """Deform phase: regions bend under affective flow gradients."""
        deformed = 0
        for region in self._regions.values():
            # The gradient is the difference between a region's curvature and
            # the mean curvature of its neighbors. A region bends toward its
            # neighbors when the gradient is steep.
            neighbor_curvatures = self._neighbor_curvatures(region)
            if neighbor_curvatures:
                neighbor_mean = sum(neighbor_curvatures) / len(neighbor_curvatures)
            else:
                neighbor_mean = region.curvature
            gradient = neighbor_mean - region.curvature
            delta = gradient * self._config.deformation_rate
            previous_curvature = region.curvature
            region.curvature = self._clamp_curvature(region.curvature + delta)
            # Strong gradients can open a new handle (raise genus) up to the cap.
            if abs(gradient) > 0.5 and random.random() < 0.15 \
                    and region.genus < self._config.genus_max:
                region.genus += 1
            # Area stretches when curvature magnitude grows.
            region.area_units = max(0.1, region.area_units + abs(delta) * 0.5)
            if abs(region.curvature - previous_curvature) > 1e-6:
                deformed += 1
        self._update_stats(deformations=deformed, phase_runs=1)
        self._record_event("phase_deform", {"deformed": deformed})
        return {"deformed": deformed}

    def _phase_classify(self) -> Dict[str, Any]:
        """Classify phase: label each region with a topological feature."""
        classified = 0
        for region in self._regions.values():
            neighbor_curvatures = self._neighbor_curvatures(region)
            region.feature = self._classify_feature(region.curvature, neighbor_curvatures)
            region.manifold_class = self._classify_manifold(region)
            classified += 1
        self._update_stats(features_classified=classified, phase_runs=1)
        self._record_event("phase_classify", {"classified": classified})
        return {"classified": classified}

    def _phase_stitch(self) -> Dict[str, Any]:
        """Stitch phase: knit boundary discontinuities between adjacent regions."""
        stitched = 0
        now = time.time()
        region_ids = list(self._regions.keys())
        # Pairwise pass: regions whose curvature difference falls within the
        # stitch tolerance become neighbors and have their boundaries smoothed.
        for i, eid_a in enumerate(region_ids):
            region_a = self._regions[eid_a]
            for eid_b in region_ids[i + 1:]:
                region_b = self._regions[eid_b]
                gap = abs(region_a.curvature - region_b.curvature)
                if gap > self._config.stitch_tolerance:
                    continue
                if region_b.region_id not in region_a.neighbors:
                    region_a.neighbors.append(region_b.region_id)
                if region_a.region_id not in region_b.neighbors:
                    region_b.neighbors.append(region_a.region_id)
                # Smooth the shared boundary: nudge both curvatures toward their mean.
                mean_curvature = (region_a.curvature + region_b.curvature) / 2.0
                region_a.curvature = self._clamp_curvature(
                    region_a.curvature * 0.7 + mean_curvature * 0.3
                )
                region_b.curvature = self._clamp_curvature(
                    region_b.curvature * 0.7 + mean_curvature * 0.3
                )
                region_a.last_stitched_at = now
                region_b.last_stitched_at = now
                stitched += 1
        self._update_stats(stitches_performed=stitched, phase_runs=1)
        self._record_event("phase_stitch", {"stitched": stitched})
        return {"stitched": stitched}

    def _phase_persist(self) -> Dict[str, Any]:
        """Persist phase: refresh invariants and fold state back into the manifold."""
        persisted = 0
        euler_updates = 0
        for region in self._regions.values():
            previous_euler = region.euler_characteristic
            region.euler_characteristic = self._compute_euler(region)
            if region.euler_characteristic != previous_euler:
                euler_updates += 1
            region.vitality = self._derive_vitality()
            persisted += 1
        self._update_stats(euler_updates=euler_updates, phase_runs=1)
        self._record_event("phase_persist", {
            "persisted": persisted,
            "euler_updates": euler_updates,
        })
        return {"persisted": persisted, "euler_updates": euler_updates}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _clamp_curvature(self, value: float) -> float:
        return max(self._config.curvature_floor,
                   min(self._config.curvature_ceiling, value))

    def _neighbor_curvatures(self, region: EmotionRegion) -> List[float]:
        out: List[float] = []
        for other in self._regions.values():
            if other.region_id in region.neighbors:
                out.append(other.curvature)
        return out

    def _classify_feature(self, curvature: float,
                          neighbor_curvatures: Optional[List[float]] = None) -> TopologicalFeature:
        """Label a region with a topological feature from its curvature profile."""
        magnitude = abs(curvature)
        if magnitude < 0.15:
            return TopologicalFeature.PLATEAU
        # A saddle has neighbors pulling in the opposite curvature direction.
        if neighbor_curvatures:
            neighbor_mean = sum(neighbor_curvatures) / len(neighbor_curvatures)
            if abs(curvature - neighbor_mean) < 0.1 and magnitude >= 0.3 \
                    and (curvature > 0) != (neighbor_mean > 0):
                return TopologicalFeature.SADDLE
        if curvature > 0:
            if magnitude >= 1.0:
                return TopologicalFeature.PEAK
            return TopologicalFeature.RIDGE
        # Negative curvature: deep basins vs shallow ridges of inverse curvature.
        if magnitude >= 1.0:
            return TopologicalFeature.BASIN
        return TopologicalFeature.RIDGE

    def _classify_manifold(self, region: EmotionRegion) -> ManifoldClass:
        """Assign a global manifold class from genus and curvature."""
        if region.genus >= 3:
            return ManifoldClass.FRACTAL
        if region.genus >= 2:
            return ManifoldClass.FOLDED
        if region.genus == 1:
            return ManifoldClass.TORUS
        if region.curvature < -0.5:
            return ManifoldClass.HYPERBOLIC
        return ManifoldClass.SPHERE

    def _compute_euler(self, region: EmotionRegion) -> int:
        """Compute the Euler characteristic from genus and boundary behavior."""
        base = 2 - 2 * region.genus
        # Open and absorbing boundaries remove a boundary component; closed and
        # reflecting boundaries keep the surface intact.
        if region.boundary_type in (BoundaryType.OPEN, BoundaryType.SEMI_PERMEABLE,
                                    BoundaryType.ABSORBING):
            base -= 1
        return base

    def _region_to_dict(self, region: EmotionRegion) -> Dict[str, Any]:
        return {
            "region_id": region.region_id,
            "entity_id": region.entity_id,
            "emotion_label": region.emotion_label,
            "curvature": region.curvature,
            "genus": region.genus,
            "boundary_type": region.boundary_type.value,
            "feature": region.feature.value,
            "manifold_class": region.manifold_class.value,
            "euler_characteristic": region.euler_characteristic,
            "vitality": region.vitality.value,
            "area_units": region.area_units,
            "neighbors": list(region.neighbors),
            "last_projected_at": region.last_projected_at,
            "last_stitched_at": region.last_stitched_at,
            "metadata": dict(region.metadata),
        }

    def _refresh_derived_stats(self) -> None:
        curvatures = [r.curvature for r in self._regions.values()]
        self._stats["avg_curvature"] = (
            sum(curvatures) / len(curvatures) if curvatures else 0.0
        )
        self._stats["regions_registered"] = len(self._regions)
        self._stats["vitality"] = self._derive_vitality().value

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "regions": len(self._regions),
                "stats": dict(self._stats),
            }

    def get_regions(self, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            regions = sorted(
                self._regions.values(),
                key=lambda r: r.last_projected_at,
                reverse=True,
            )[:limit]
            return {
                "regions": [self._region_to_dict(r) for r in regions],
                "count": len(regions),
            }

    def get_region(self, region_id: str) -> Dict[str, Any]:
        with self._global_lock:
            # The internal dict is keyed by entity_id (the affect_key), so we
            # fall back to a linear search over values to match by region_id.
            for region in self._regions.values():
                if region.region_id == region_id:
                    return self._region_to_dict(region)
            return {"error": "emotion region not found", "region_id": region_id}

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic regions, then run multiple cycles in sequence."""
        with self._global_lock:
            self._seed_synthetic_regions()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_regions(self) -> None:
        """Seed a small synthetic affective manifold with distinct emotions."""
        seed_emotions = [
            ("affect::sorrow", "sorrow", -0.8, 0, BoundaryType.SEMI_PERMEABLE),
            ("affect::anger", "anger", -1.2, 1, BoundaryType.REFLECTING),
            ("affect::wonder", "wonder", 0.6, 1, BoundaryType.OPEN),
            ("affect::fear", "fear", -0.5, 0, BoundaryType.ABSORBING),
            ("affect::tenderness", "tenderness", 0.9, 0, BoundaryType.OPEN),
            ("affect::resolve", "resolve", 1.1, 0, BoundaryType.CLOSED),
            ("affect::dread", "dread", -1.5, 2, BoundaryType.REFLECTING),
        ]
        for entity_id, label, curvature, genus, boundary in seed_emotions:
            if entity_id in self._regions:
                continue
            self.register_region(
                entity_id=entity_id,
                emotion_label=label,
                curvature=curvature,
                genus=genus,
                boundary_type=boundary,
            )

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._regions.clear()
            self._events_log.clear()
            self._phase = MappingPhase.PROJECT
            self._cycle_count = 0
            self._init_stats()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
