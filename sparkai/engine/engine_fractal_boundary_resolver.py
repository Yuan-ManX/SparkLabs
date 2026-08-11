"""
SparkLabs Engine - Fractal Boundary Resolver"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class ResolutionPhase(Enum):
    """Phases of the fractal boundary resolution cycle."""
    SEED = "seed"              # seed boundary control points from region adjacency
    SUBDIVIDE = "subdivide"    # recursively subdivide boundary segments via midpoint displacement
    ROUGHEN = "roughen"        # perturb subdivision points by the roughness coefficient
    SMOOTH = "smooth"          # tame excessive jaggedness within tolerance
    COMMIT = "commit"          # commit resolved boundary geometry, update metrics, write events


class BoundaryState(Enum):
    """State of an individual boundary."""
    RAW = "raw"                  # registered but not yet seeded
    SEEDED = "seeded"            # control points placed
    SUBDIVIDED = "subdivided"    # segments recursively split
    REFINED = "refined"          # roughened and smoothed
    FINALIZED = "finalized"      # committed geometry


class FractalClass(Enum):
    """Classification of a boundary by its fractal dimension."""
    EUCLIDEAN = "euclidean"            # dimension near 1.0 - clean line
    NEAR_EUCLIDEAN = "near_euclidean"  # slightly above 1.0
    NATURAL = "natural"                # typical coastline range
    RUGGED = "rugged"                  # rough terrain range
    CORIACEOUS = "coriaceous"          # extremely rugged


class TopologyKind(Enum):
    """The topological role a boundary plays between two regions."""
    RIDGE = "ridge"        # mountain ridge between two land regions
    VALLEY = "valley"      # valley between two high regions
    COAST = "coast"        # land meets sea
    FAULT = "fault"        # tectonic fault line
    SHORE = "shore"        # shore of a lake or river


class Vitality(Enum):
    """Overall vitality of the fractal boundary ecosystem."""
    LATENT = "latent"          # few boundaries, little activity
    EMERGING = "emerging"      # boundaries seeded, subdividing
    ACTIVE = "active"          # healthy subdivision and refinement
    SURGING = "surging"        # many boundaries finalizing per cycle
    SATURATED = "saturated"    # at capacity, cannot accept more boundaries


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Boundary:
    """A fractal boundary between two adjacent regions."""
    boundary_id: str
    entity_id: str                                   # region pair key like "region::forest_mountain"
    region_a: str
    region_b: str
    fractal_dimension: float = 1.35
    recursion_depth: int = 4
    roughness: float = 0.55
    state: BoundaryState = BoundaryState.RAW
    fractal_class: FractalClass = FractalClass.NATURAL
    topology_kind: TopologyKind = TopologyKind.RIDGE
    vitality: Vitality = Vitality.LATENT
    control_points: List[List[float]] = field(default_factory=list)
    segment_count: int = 0
    length_units: float = 0.0
    last_seeded_at: float = 0.0
    last_committed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolutionConfig:
    """Configuration for the fractal boundary resolver."""
    max_boundaries: int = 200
    default_fractal_dimension: float = 1.35
    max_recursion_depth: int = 6
    roughness_default: float = 0.55
    smooth_tolerance: float = 0.08
    min_segment_length: float = 0.05
    dimension_floor: float = 1.0
    dimension_ceiling: float = 1.95


# =============================================================================
# Resolver
# =============================================================================

class FractalBoundaryResolver:
    """
    Thread-safe singleton that resolves region boundaries using fractal geometry.

    Usage:
        resolver = FractalBoundaryResolver.get_instance()
        resolver.register_boundary(
            entity_id="region::forest_mountain",
            region_a="forest",
            region_b="mountain",
        )
        resolver.cycle()
        info = resolver.get_boundary(boundary_id)
    """

    _instance: Optional["FractalBoundaryResolver"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    _MAX_BOUNDARIES = 200
    _MAX_EVENTS = 200

    # Tuning constants
    _VITALITY_SURGING_FINALIZED_FRACTION = 0.6
    _VITALITY_SATURATED_FRACTION = 0.9
    _SUBDIVISION_POINT_CAP = 1024

    def __init__(self) -> None:
        # Internal dict keyed by entity_id (the region pair key), NOT by boundary_id.
        self._boundaries: Dict[str, Boundary] = {}
        self._phase: ResolutionPhase = ResolutionPhase.SEED
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._config: ResolutionConfig = ResolutionConfig()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "FractalBoundaryResolver":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> None:
        self._stats = {
            "cycles_completed": 0,
            "uptime_started_at": time.time(),
            "boundaries_registered": 0,
            "phase_runs": 0,
            "seeds_placed": 0,
            "subdivisions": 0,
            "roughness_applications": 0,
            "smoothing_passes": 0,
            "boundaries_finalized": 0,
            "events_recorded": 0,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key not in self._stats:
                # Ignore unknown keys to keep callers simple.
                continue
            current = self._stats[key]
            if isinstance(current, (int, float)) and isinstance(value, (int, float)):
                self._stats[key] = current + value
            else:
                self._stats[key] = value

    def _record_event(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload or {},
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })
        self._stats["events_recorded"] += 1

    # -------------------------------------------------------------------------
    # Boundary Management
    # -------------------------------------------------------------------------

    def register_boundary(
        self,
        entity_id: str,
        region_a: str,
        region_b: str,
        fractal_dimension: Optional[float] = None,
        recursion_depth: Optional[int] = None,
        roughness: Optional[float] = None,
        topology_kind: Optional[TopologyKind] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Register a new boundary between two adjacent regions."""
        with self._global_lock:
            if entity_id in self._boundaries:
                return {"error": f"Boundary already registered for entity: {entity_id}"}
            if len(self._boundaries) >= self._MAX_BOUNDARIES:
                return {"error": f"Boundary cap reached ({self._MAX_BOUNDARIES})"}
            dim = self._config.default_fractal_dimension if fractal_dimension is None else fractal_dimension
            dim = max(self._config.dimension_floor, min(self._config.dimension_ceiling, dim))
            depth = self._config.max_recursion_depth if recursion_depth is None else recursion_depth
            depth = max(1, min(self._config.max_recursion_depth, depth))
            rough = self._config.roughness_default if roughness is None else roughness
            rough = max(0.0, min(1.0, rough))
            topo = topology_kind or self._infer_topology(region_a, region_b)
            boundary_id = f"bnd_{entity_id}_{int(time.time() * 1000)}_{random.randint(100, 999)}"
            boundary = Boundary(
                boundary_id=boundary_id,
                entity_id=entity_id,
                region_a=region_a,
                region_b=region_b,
                fractal_dimension=dim,
                recursion_depth=depth,
                roughness=rough,
                state=BoundaryState.RAW,
                fractal_class=self._classify_fractal(dim),
                topology_kind=topo,
                vitality=Vitality.LATENT,
                control_points=[],
                segment_count=0,
                length_units=0.0,
                last_seeded_at=0.0,
                last_committed_at=0.0,
                metadata=dict(metadata) if metadata else {},
            )
            self._boundaries[entity_id] = boundary
            self._update_stats(boundaries_registered=1)
            self._record_event("boundary_registered", {
                "boundary_id": boundary_id,
                "entity_id": entity_id,
                "region_a": region_a,
                "region_b": region_b,
                "fractal_dimension": dim,
                "roughness": rough,
                "topology_kind": topo.value,
            })
            return {
                "boundary_id": boundary_id,
                "entity_id": entity_id,
                "region_a": region_a,
                "region_b": region_b,
                "fractal_dimension": dim,
                "recursion_depth": depth,
                "roughness": rough,
                "fractal_class": boundary.fractal_class.value,
                "topology_kind": boundary.topology_kind.value,
                "state": boundary.state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single fractal boundary resolution cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic boundaries on the very first cycle if none exist.
            if not self._boundaries and self._cycle_count == 0:
                self._seed_synthetic_boundaries()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = ResolutionPhase.SEED
            phase_outputs.append(self._phase_seed())
            self._phase = ResolutionPhase.SUBDIVIDE
            phase_outputs.append(self._phase_subdivide())
            self._phase = ResolutionPhase.ROUGHEN
            phase_outputs.append(self._phase_roughen())
            self._phase = ResolutionPhase.SMOOTH
            phase_outputs.append(self._phase_smooth())
            self._phase = ResolutionPhase.COMMIT
            phase_outputs.append(self._phase_commit())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_seed(self) -> Dict[str, Any]:
        """Seed phase: place control points along each raw boundary from adjacency."""
        seeded = 0
        for boundary in self._boundaries.values():
            if boundary.state != BoundaryState.RAW:
                continue
            boundary.control_points = self._seed_control_points(boundary)
            boundary.state = BoundaryState.SEEDED
            boundary.last_seeded_at = time.time()
            seeded += 1
        self._update_stats(phase_runs=1, seeds_placed=seeded)
        self._record_event("phase_seed", {"seeded": seeded})
        return {"phase": "seed", "seeded": seeded}

    def _phase_subdivide(self) -> Dict[str, Any]:
        """Subdivide phase: recursively split segments via midpoint displacement."""
        subdivisions = 0
        for boundary in self._boundaries.values():
            if boundary.state != BoundaryState.SEEDED:
                continue
            points = boundary.control_points
            if len(points) < 2:
                boundary.state = BoundaryState.SUBDIVIDED
                continue
            for _ in range(boundary.recursion_depth):
                if len(points) >= self._SUBDIVISION_POINT_CAP:
                    break
                new_points: List[List[float]] = [points[0]]
                for i in range(len(points) - 1):
                    a = points[i]
                    b = points[i + 1]
                    mid = self._midpoint_displacement(a, b, boundary.fractal_dimension)
                    new_points.append(mid)
                    new_points.append(b)
                    subdivisions += 1
                points = new_points
                points = self._trim_short_segments(points, self._config.min_segment_length)
            boundary.control_points = points
            boundary.segment_count = max(0, len(points) - 1)
            boundary.state = BoundaryState.SUBDIVIDED
        self._update_stats(phase_runs=1, subdivisions=subdivisions)
        self._record_event("phase_subdivide", {"subdivisions": subdivisions})
        return {"phase": "subdivide", "subdivisions": subdivisions}

    def _phase_roughen(self) -> Dict[str, Any]:
        """Roughen phase: perturb subdivision points by the roughness coefficient."""
        applications = 0
        for boundary in self._boundaries.values():
            if boundary.state != BoundaryState.SUBDIVIDED:
                continue
            points = boundary.control_points
            if len(points) < 3:
                boundary.state = BoundaryState.REFINED
                continue
            # Perturb interior points only; keep endpoints fixed.
            perturbed: List[List[float]] = [points[0]]
            for i in range(1, len(points) - 1):
                p = points[i]
                amp = boundary.roughness * 0.1
                px = p[0] + random.uniform(-amp, amp)
                py = p[1] + random.uniform(-amp, amp)
                perturbed.append([px, py])
                applications += 1
            perturbed.append(points[-1])
            boundary.control_points = perturbed
            boundary.state = BoundaryState.REFINED
        self._update_stats(phase_runs=1, roughness_applications=applications)
        self._record_event("phase_roughen", {"applications": applications})
        return {"phase": "roughen", "applications": applications}

    def _phase_smooth(self) -> Dict[str, Any]:
        """Smooth phase: tame excessive jaggedness within tolerance."""
        passes = 0
        tolerance = self._config.smooth_tolerance
        for boundary in self._boundaries.values():
            if boundary.state != BoundaryState.REFINED:
                continue
            points = boundary.control_points
            if len(points) < 3:
                boundary.state = BoundaryState.FINALIZED
                continue
            # Average each interior point with its neighbors only when the
            # local deviation exceeds the tolerance.
            smoothed: List[List[float]] = [points[0]]
            for i in range(1, len(points) - 1):
                prev = points[i - 1]
                curr = points[i]
                nxt = points[i + 1]
                deviation = abs(curr[0] - (prev[0] + nxt[0]) / 2.0) + \
                            abs(curr[1] - (prev[1] + nxt[1]) / 2.0)
                if deviation > tolerance:
                    sx = (prev[0] + curr[0] * 2.0 + nxt[0]) / 4.0
                    sy = (prev[1] + curr[1] * 2.0 + nxt[1]) / 4.0
                    smoothed.append([sx, sy])
                    passes += 1
                else:
                    smoothed.append(curr)
            smoothed.append(points[-1])
            boundary.control_points = smoothed
        self._update_stats(phase_runs=1, smoothing_passes=passes)
        self._record_event("phase_smooth", {"passes": passes})
        return {"phase": "smooth", "passes": passes}

    def _phase_commit(self) -> Dict[str, Any]:
        """Commit phase: finalize geometry, update fractal metrics, write events."""
        committed = 0
        for boundary in self._boundaries.values():
            if boundary.state == BoundaryState.FINALIZED:
                # Already finalized this run; just re-measure.
                boundary.length_units = self._measure_length(boundary.control_points)
                boundary.segment_count = max(0, len(boundary.control_points) - 1)
                continue
            if boundary.state != BoundaryState.REFINED:
                continue
            boundary.length_units = self._measure_length(boundary.control_points)
            boundary.segment_count = max(0, len(boundary.control_points) - 1)
            boundary.state = BoundaryState.FINALIZED
            boundary.last_committed_at = time.time()
            # Reclassify fractal class in case dimension drifted during refinement.
            boundary.fractal_class = self._classify_fractal(boundary.fractal_dimension)
            boundary.vitality = self._derive_boundary_vitality()
            committed += 1
            self._record_event("boundary_finalized", {
                "boundary_id": boundary.boundary_id,
                "entity_id": boundary.entity_id,
                "segment_count": boundary.segment_count,
                "length_units": boundary.length_units,
                "fractal_class": boundary.fractal_class.value,
            })
        self._update_stats(phase_runs=1, boundaries_finalized=committed)
        self._record_event("phase_commit", {"committed": committed})
        return {"phase": "commit", "committed": committed}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _seed_control_points(self, boundary: Boundary) -> List[List[float]]:
        """Place initial control points along a boundary from region adjacency."""
        anchor_a = [0.0, 0.0]
        anchor_b = [10.0, 0.0]
        n = 4
        points: List[List[float]] = [anchor_a]
        for i in range(1, n):
            t = i / n
            x = anchor_a[0] + (anchor_b[0] - anchor_a[0]) * t
            y = anchor_a[1] + (anchor_b[1] - anchor_a[1]) * t
            # Topology kind drives the baseline offset shape.
            y += self._topology_baseline_offset(boundary.topology_kind, t)
            points.append([x, y])
        points.append(anchor_b)
        return points

    def _midpoint_displacement(self, a: List[float], b: List[float],
                                fractal_dimension: float) -> List[float]:
        """Compute a displaced midpoint between two points."""
        mx = (a[0] + b[0]) / 2.0
        my = (a[1] + b[1]) / 2.0
        seg_len = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        # The displacement magnitude scales with segment length and the
        # distance of the fractal dimension from euclidean (1.0).
        displacement_scale = seg_len * (fractal_dimension - 1.0) * 0.5
        displacement_scale = max(0.0, displacement_scale)
        dy = random.uniform(-displacement_scale, displacement_scale)
        return [mx, my + dy]

    def _trim_short_segments(self, points: List[List[float]],
                              min_length: float) -> List[List[float]]:
        """Drop interior points whose neighbors are too close."""
        if len(points) < 3:
            return points
        result: List[List[float]] = [points[0]]
        for i in range(1, len(points)):
            prev = result[-1]
            curr = points[i]
            dist = ((curr[0] - prev[0]) ** 2 + (curr[1] - prev[1]) ** 2) ** 0.5
            if dist >= min_length or i == len(points) - 1:
                result.append(curr)
        return result

    def _measure_length(self, points: List[List[float]]) -> float:
        """Sum the Euclidean length of a polyline."""
        total = 0.0
        for i in range(len(points) - 1):
            a = points[i]
            b = points[i + 1]
            total += ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        return total

    def _classify_fractal(self, dimension: float) -> FractalClass:
        """Classify a boundary by its fractal dimension."""
        if dimension < 1.05:
            return FractalClass.EUCLIDEAN
        if dimension < 1.2:
            return FractalClass.NEAR_EUCLIDEAN
        if dimension < 1.4:
            return FractalClass.NATURAL
        if dimension < 1.6:
            return FractalClass.RUGGED
        return FractalClass.CORIACEOUS

    def _infer_topology(self, region_a: str, region_b: str) -> TopologyKind:
        """Infer a default topology kind from the names of two regions."""
        a = (region_a or "").lower()
        b = (region_b or "").lower()
        combined = f"{a} {b}"
        if "sea" in combined or "ocean" in combined or "coast" in combined:
            return TopologyKind.COAST
        if "lake" in combined or "river" in combined or "shore" in combined:
            return TopologyKind.SHORE
        if "fault" in combined:
            return TopologyKind.FAULT
        if "valley" in combined:
            return TopologyKind.VALLEY
        return TopologyKind.RIDGE

    def _topology_baseline_offset(self, kind: TopologyKind, t: float) -> float:
        """A baseline y-offset shape for a topology kind at parameter t in [0,1]."""
        if kind == TopologyKind.RIDGE:
            return 1.0 - abs(2.0 * t - 1.0)
        if kind == TopologyKind.VALLEY:
            return -1.0 + abs(2.0 * t - 1.0)
        if kind == TopologyKind.COAST:
            return 0.3 * (1.0 - abs(2.0 * t - 1.0))
        if kind == TopologyKind.FAULT:
            return 0.5 if t > 0.5 else -0.5
        if kind == TopologyKind.SHORE:
            return 0.2 * (1.0 - abs(2.0 * t - 1.0))
        return 0.0

    def _derive_boundary_vitality(self) -> Vitality:
        """Per-boundary vitality once finalized."""
        return Vitality.ACTIVE

    def _derive_vitality(self) -> Vitality:
        """Overall ecosystem vitality from boundary population and progress."""
        count = len(self._boundaries)
        if count == 0:
            return Vitality.LATENT
        if count >= self._MAX_BOUNDARIES * self._VITALITY_SATURATED_FRACTION:
            return Vitality.SATURATED
        finalized = sum(
            1 for b in self._boundaries.values()
            if b.state == BoundaryState.FINALIZED
        )
        if finalized == 0:
            return Vitality.EMERGING
        if finalized >= count * self._VITALITY_SURGING_FINALIZED_FRACTION:
            return Vitality.SURGING
        return Vitality.ACTIVE

    def _boundary_to_dict(self, boundary: Boundary) -> Dict[str, Any]:
        return {
            "boundary_id": boundary.boundary_id,
            "entity_id": boundary.entity_id,
            "region_a": boundary.region_a,
            "region_b": boundary.region_b,
            "fractal_dimension": boundary.fractal_dimension,
            "recursion_depth": boundary.recursion_depth,
            "roughness": boundary.roughness,
            "state": boundary.state.value,
            "fractal_class": boundary.fractal_class.value,
            "topology_kind": boundary.topology_kind.value,
            "vitality": boundary.vitality.value,
            "control_points": boundary.control_points,
            "segment_count": boundary.segment_count,
            "length_units": boundary.length_units,
            "last_seeded_at": boundary.last_seeded_at,
            "last_committed_at": boundary.last_committed_at,
            "metadata": dict(boundary.metadata),
        }

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_boundaries(self) -> None:
        """Seed ~5-8 synthetic boundaries on first cycle if empty."""
        seeds = [
            ("region::forest_mountain", "forest", "mountain", TopologyKind.RIDGE, 1.4, 0.6),
            ("region::plains_forest", "plains", "forest", TopologyKind.VALLEY, 1.25, 0.5),
            ("region::coast_sea", "coast", "sea", TopologyKind.COAST, 1.3, 0.55),
            ("region::desert_canyon", "desert", "canyon", TopologyKind.FAULT, 1.5, 0.7),
            ("region::lake_shore", "lake", "shore", TopologyKind.SHORE, 1.2, 0.45),
            ("region::tundra_taiga", "tundra", "taiga", TopologyKind.RIDGE, 1.35, 0.55),
            ("region::swamp_marsh", "swamp", "marsh", TopologyKind.SHORE, 1.28, 0.5),
        ]
        for entity_id, region_a, region_b, topo, dim, rough in seeds:
            if len(self._boundaries) >= self._MAX_BOUNDARIES:
                break
            if entity_id in self._boundaries:
                continue
            self.register_boundary(
                entity_id=entity_id,
                region_a=region_a,
                region_b=region_b,
                fractal_dimension=dim,
                roughness=rough,
                topology_kind=topo,
            )

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "boundaries": len(self._boundaries),
                "vitality": self._derive_vitality().value,
                "stats": dict(self._stats),
            }

    def get_boundaries(self, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            boundaries = sorted(
                self._boundaries.values(),
                key=lambda b: b.last_committed_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(boundaries),
                "boundaries": [self._boundary_to_dict(b) for b in boundaries],
            }

    def get_boundary(self, boundary_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, not boundary_id, so we
        # do a fallback search across values matching on boundary_id.
        with self._global_lock:
            for boundary in self._boundaries.values():
                if boundary.boundary_id == boundary_id:
                    return self._boundary_to_dict(boundary)
            return {"error": "boundary not found", "boundary_id": boundary_id}

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic boundaries if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._boundaries:
                self._seed_synthetic_boundaries()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._boundaries.clear()
            self._events_log.clear()
            self._phase = ResolutionPhase.SEED
            self._cycle_count = 0
            self._init_stats()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
