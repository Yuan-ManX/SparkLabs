"""
SparkLabs Engine - Tension Topology Cartographer

The EngineTensionTopologyCartographer models how dramatic tension forms
topological surfaces across the narrative landscape. Rather than treating
tension as a single scalar value that goes up and down, the cartographer
maps tension as a terrain - with peaks of climax, valleys of calm, ridges
of sustained suspense, cliffs of sudden shock, and plateaus of simmering
unease.

Dramatic tension is not a line; it is a landscape. A story does not simply
"get more tense" - it develops a tension topology where some subplots form
soaring peaks while others create gentle valleys, where a ridge of suspense
connects two climactic peaks, and where a sudden cliff drops the audience
from calm into chaos. The shape of this topology - not just its height -
is what gives a story its dramatic texture.

The cartographer models five forces:
  - Surveying: tension points are surveyed across the narrative landscape,
    each with a position (where in the story) and elevation (how tense)
  - Contouring: surveyed points are connected into contour lines that
    reveal the shape of the tension terrain
  - Gradient: the steepness of tension change is computed - gentle slopes
    build suspense, steep cliffs create shock
  - Peaking: the highest tension points form dramatic peaks that serve
    as narrative climaxes
  - Erosion: tension erodes over time - peaks flatten, ridges lower,
    and the terrain gradually returns to baseline

This produces a narrative where tension has genuine shape - where the
audience can feel the difference between approaching a peak (rising
anticipation), crossing a ridge (sustained suspense), or standing on a
plateau (simmering tension) - and where the dramatic landscape itself
becomes a character in the story.

Architecture:
  SURVEY   ->  CONTOUR  ->  GRADIENT  ->  PEAK    ->  ERODE
  (tension  (points      (steepness   (highest    (tension
   points   connected    of tension   points      erodes:
   surveyed into contour  change      form       peaks flatten,
   across    lines        computed -  dramatic   ridges lower,
   the       revealing    gentle      peaks      terrain
   narrative the shape    slopes =    serving     returns to
   landscape of the       suspense,   as          baseline)
   with      tension      steep       climaxes)
   position  terrain)     cliffs =
   and                    shock)
   elevation)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class TopologyPhase(Enum):
    """Phases of the tension topology cycle."""
    SURVEY = "survey"           # survey tension points
    CONTOUR = "contour"         # connect into contour lines
    GRADIENT = "gradient"       # compute steepness
    PEAK = "peak"               # identify dramatic peaks
    ERODE = "erode"             # tension erodes over time


class TensionType(Enum):
    """Types of dramatic tension."""
    CONFLICT = "conflict"       # opposing forces clash
    SUSPENSE = "suspense"       # anticipation of unknown outcome
    MYSTERY = "mystery"         # puzzle needing resolution
    DREAD = "dread"             # anticipation of bad outcome
    HOPE = "hope"               # anticipation of good outcome
    DILEMMA = "dilemma"         # impossible choice
    BETRAYAL = "betrayal"       # trust about to break
    REVELATION = "revelation"   # truth about to surface
    PURSUIT = "pursuit"         # chase, escape
    STAKES = "stakes"           # what could be lost


class TerrainFeature(Enum):
    """Types of terrain features in the tension topology."""
    PEAK = "peak"               # climax, highest tension
    RIDGE = "ridge"             # sustained high tension
    PLATEAU = "plateau"         # steady moderate tension
    VALLEY = "valley"           # low tension, rest point
    CLIFF = "cliff"             # sudden tension spike
    SLOPE = "slope"             # gradual tension change
    BASIN = "basin"             # enclosed low-tension area
    COL = "col"                 # saddle between two peaks
    SUMMIT = "summit"           # the highest peak of all


class TensionState(Enum):
    """State of a tension point."""
    RISING = "rising"           # tension increasing
    HOLDING = "holding"         # tension sustained
    FALLING = "falling"         # tension decreasing
    DORMANT = "dormant"         # tension inactive
    PEAKED = "peaked"           # at maximum
    ERODING = "eroding"         # gradually fading


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TensionPoint:
    """A point of dramatic tension in the narrative landscape."""
    point_id: str
    label: str
    tension_type: TensionType
    x: float = 0.5              # narrative position (0.0-1.0)
    y: float = 0.5              # subplot position (0.0-1.0)
    elevation: float = 0.5      # tension level (0.0-1.0)
    state: TensionState = TensionState.RISING
    gradient: float = 0.0       # rate of change
    connected_to: List[str] = field(default_factory=list)
    feature: TerrainFeature = TerrainFeature.SLOPE
    last_updated: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    description: str = ""
    stakeholders: List[str] = field(default_factory=list)


@dataclass
class ContourLine:
    """A contour line connecting points of similar tension."""
    contour_id: str
    elevation: float            # the tension level this contour represents
    point_ids: List[str] = field(default_factory=list)
    feature: TerrainFeature = TerrainFeature.SLOPE
    length: float = 0.0         # total path length
    closed: bool = False        # whether it forms a closed loop
    created_at: float = field(default_factory=time.time)


@dataclass
class DramaticPeak:
    """A identified dramatic peak in the tension topology."""
    peak_id: str
    point_id: str               # the highest point
    label: str
    elevation: float            # peak tension level
    tension_type: TensionType
    surrounding_points: List[str] = field(default_factory=list)
    feature: TerrainFeature = TerrainFeature.PEAK
    prominence: float = 0.5     # how much it stands out from surroundings
    isolation: float = 0.5      # distance to nearest rival peak
    identified_at: float = field(default_factory=time.time)
    is_summit: bool = False     # the highest peak of all


# =============================================================================
# Tension Topology Cartographer
# =============================================================================

class EngineTensionTopologyCartographer:
    """
    Thread-safe singleton orchestrating tension topology mapping.

    Usage:
        cartographer = EngineTensionTopologyCartographer.get_instance()
        cartographer.survey_point("t_battle", "The Great Battle",
                                 TensionType.CONFLICT, x=0.6, y=0.5,
                                 elevation=0.85)
        cartographer.survey_point("t_chase", "The Chase",
                                 TensionType.PURSUIT, x=0.55, y=0.5,
                                 elevation=0.7)
        cartographer.connect_points("t_battle", "t_chase")
        cartographer.cycle()
    """

    _instance: Optional["EngineTensionTopologyCartographer"] = None
    _lock = threading.RLock()

    # Elevation threshold for peak identification
    _PEAK_THRESHOLD = 0.65
    # Gradient threshold for cliff classification
    _CLIFF_GRADIENT = 0.4
    # Gradient threshold for slope classification
    _SLOPE_GRADIENT = 0.1
    # Erosion rate per cycle
    _EROSION_RATE = 0.02
    # Contour elevation interval
    _CONTOUR_INTERVAL = 0.2
    # Distance threshold for point connection
    _CONNECTION_DISTANCE = 0.35

    def __init__(self) -> None:
        self._points: Dict[str, TensionPoint] = {}
        self._contours: Dict[str, ContourLine] = {}
        self._peaks: Dict[str, DramaticPeak] = {}
        self._phase: TopologyPhase = TopologyPhase.SURVEY
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {
            "total_points": 0,
            "total_contours": 0,
            "total_peaks": 0,
            "summit_elevation": 0.0,
            "avg_elevation": 0.0,
            "avg_gradient": 0.0,
            "rising_points": 0,
            "holding_points": 0,
            "falling_points": 0,
            "dormant_points": 0,
            "peaked_points": 0,
            "eroding_points": 0,
            "cliffs": 0,
            "ridges": 0,
            "plateaus": 0,
            "valleys": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineTensionTopologyCartographer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Point Management
    # -------------------------------------------------------------------------

    def survey_point(
        self,
        point_id: str,
        label: str,
        tension_type: TensionType,
        x: float = 0.5,
        y: float = 0.5,
        elevation: float = 0.5,
        description: str = "",
        stakeholders: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Survey a new tension point in the narrative landscape."""
        with self._global_lock:
            if point_id in self._points:
                return {"error": f"Point already exists: {point_id}"}
            point = TensionPoint(
                point_id=point_id,
                label=label,
                tension_type=tension_type,
                x=max(0.0, min(1.0, x)),
                y=max(0.0, min(1.0, y)),
                elevation=max(0.0, min(1.0, elevation)),
                description=description,
                stakeholders=stakeholders or [],
            )
            self._points[point_id] = point
            self._record_event("point_surveyed", {
                "point_id": point_id,
                "label": label,
                "tension_type": tension_type.value,
                "elevation": point.elevation,
            })
            return {
                "point_id": point_id,
                "label": label,
                "tension_type": tension_type.value,
                "x": point.x, "y": point.y,
                "elevation": point.elevation,
                "state": point.state.value,
            }

    def update_elevation(
        self, point_id: str, new_elevation: float,
    ) -> Dict[str, Any]:
        """Update the elevation (tension level) of a point."""
        with self._global_lock:
            point = self._points.get(point_id)
            if point is None:
                return {"error": f"Point not found: {point_id}"}
            old_elevation = point.elevation
            point.elevation = max(0.0, min(1.0, new_elevation))
            point.gradient = point.elevation - old_elevation
            point.last_updated = time.time()
            # update state
            if point.gradient > 0.05:
                point.state = TensionState.RISING
            elif point.gradient < -0.05:
                point.state = TensionState.FALLING
            elif point.elevation > self._PEAK_THRESHOLD:
                point.state = TensionState.PEAKED
            elif abs(point.gradient) < 0.02:
                point.state = TensionState.HOLDING
            self._record_event("elevation_updated", {
                "point_id": point_id,
                "old": old_elevation,
                "new": point.elevation,
                "gradient": point.gradient,
            })
            return {
                "point_id": point_id,
                "elevation": point.elevation,
                "gradient": point.gradient,
                "state": point.state.value,
            }

    def connect_points(
        self, point_a: str, point_b: str,
    ) -> Dict[str, Any]:
        """Connect two tension points."""
        with self._global_lock:
            pa = self._points.get(point_a)
            pb = self._points.get(point_b)
            if pa is None or pb is None:
                return {"error": "Point not found"}
            if point_b not in pa.connected_to:
                pa.connected_to.append(point_b)
            if point_a not in pb.connected_to:
                pb.connected_to.append(point_a)
            return {
                "point_a": point_a,
                "point_b": point_b,
                "connections_a": len(pa.connected_to),
                "connections_b": len(pb.connected_to),
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single tension topology cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = TopologyPhase.SURVEY
            phase_outputs["survey"] = self._phase_survey()
            self._phase = TopologyPhase.CONTOUR
            phase_outputs["contour"] = self._phase_contour()
            self._phase = TopologyPhase.GRADIENT
            phase_outputs["gradient"] = self._phase_gradient()
            self._phase = TopologyPhase.PEAK
            phase_outputs["peak"] = self._phase_peak()
            self._phase = TopologyPhase.ERODE
            phase_outputs["erode"] = self._phase_erode()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_survey(self) -> Dict[str, Any]:
        """Survey phase: update point states based on current elevation."""
        updated = 0
        for point in self._points.values():
            if point.state == TensionState.DORMANT:
                continue
            # check if elevation changed
            if abs(point.gradient) < 0.01 and point.elevation > self._PEAK_THRESHOLD:
                if point.state != TensionState.PEAKED:
                    point.state = TensionState.PEAKED
                    updated += 1
            elif abs(point.gradient) < 0.01 and point.elevation < 0.3:
                if point.state != TensionState.DORMANT:
                    point.state = TensionState.DORMANT
                    updated += 1
            elif abs(point.gradient) < 0.01:
                if point.state != TensionState.HOLDING:
                    point.state = TensionState.HOLDING
                    updated += 1
            # decay gradient
            point.gradient = point.gradient * 0.8
            updated += 1
        return {
            "points_updated": updated,
            "total_points": len(self._points),
        }

    def _phase_contour(self) -> Dict[str, Any]:
        """Contour phase: group points into contour lines by elevation."""
        self._contours.clear()
        # group points by elevation bands
        bands: Dict[int, List[str]] = {}
        for point in self._points.values():
            band = int(point.elevation / self._CONTOUR_INTERVAL)
            bands.setdefault(band, []).append(point.point_id)
        contours_formed = 0
        for band, point_ids in bands.items():
            if len(point_ids) < 1:
                continue
            elevation = band * self._CONTOUR_INTERVAL + self._CONTOUR_INTERVAL / 2
            # check if points form a connected group
            connected_group = self._find_connected_group(point_ids)
            for group in connected_group:
                contour_id = f"contour_{band}_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
                # determine feature type
                if elevation > self._PEAK_THRESHOLD:
                    feature = TerrainFeature.RIDGE if len(group) > 2 else TerrainFeature.PEAK
                elif elevation < 0.2:
                    feature = TerrainFeature.VALLEY
                elif len(group) > 3:
                    feature = TerrainFeature.PLATEAU
                else:
                    feature = TerrainFeature.SLOPE
                # compute path length (approximate)
                length = 0.0
                for i in range(len(group) - 1):
                    pa = self._points.get(group[i])
                    pb = self._points.get(group[i + 1])
                    if pa and pb:
                        length += math.sqrt((pa.x - pb.x) ** 2 + (pa.y - pb.y) ** 2)
                contour = ContourLine(
                    contour_id=contour_id,
                    elevation=elevation,
                    point_ids=group,
                    feature=feature,
                    length=length,
                    closed=len(group) > 3,
                )
                self._contours[contour_id] = contour
                contours_formed += 1
        return {
            "contours_formed": contours_formed,
            "total_contours": len(self._contours),
        }

    def _phase_gradient(self) -> Dict[str, Any]:
        """Gradient phase: classify terrain features based on gradients."""
        cliffs = 0
        slopes = 0
        plateaus = 0
        for point in self._points.values():
            # compute gradient to connected points
            if not point.connected_to:
                continue
            max_gradient = 0.0
            for adj_id in point.connected_to:
                adj = self._points.get(adj_id)
                if adj is None:
                    continue
                distance = math.sqrt((point.x - adj.x) ** 2 + (point.y - adj.y) ** 2)
                if distance < 0.01:
                    continue
                gradient = abs(point.elevation - adj.elevation) / distance
                max_gradient = max(max_gradient, gradient)
            # classify feature
            if max_gradient > self._CLIFF_GRADIENT:
                point.feature = TerrainFeature.CLIFF
                cliffs += 1
            elif max_gradient < self._SLOPE_GRADIENT and point.elevation > 0.4:
                point.feature = TerrainFeature.PLATEAU
                plateaus += 1
            elif max_gradient < self._SLOPE_GRADIENT and point.elevation < 0.3:
                point.feature = TerrainFeature.VALLEY
            else:
                point.feature = TerrainFeature.SLOPE
                slopes += 1
        return {
            "cliffs": cliffs,
            "slopes": slopes,
            "plateaus": plateaus,
            "total_classified": cliffs + slopes + plateaus,
        }

    def _phase_peak(self) -> Dict[str, Any]:
        """Peak phase: identify dramatic peaks."""
        self._peaks.clear()
        # find points above peak threshold
        candidates = [
            p for p in self._points.values()
            if p.elevation >= self._PEAK_THRESHOLD
        ]
        # sort by elevation descending
        candidates.sort(key=lambda p: p.elevation, reverse=True)
        peaks_identified = 0
        summit_id = None
        summit_elevation = 0.0
        for point in candidates:
            # find surrounding points (lower elevation, nearby)
            surrounding = []
            for other in self._points.values():
                if other.point_id == point.point_id:
                    continue
                distance = math.sqrt((point.x - other.x) ** 2 + (point.y - other.y) ** 2)
                if distance < self._CONNECTION_DISTANCE and other.elevation < point.elevation:
                    surrounding.append(other.point_id)
            # compute prominence (how much it stands out)
            if surrounding:
                surrounding_elevations = [
                    self._points[sid].elevation for sid in surrounding
                    if sid in self._points
                ]
                avg_surrounding = sum(surrounding_elevations) / len(surrounding_elevations) if surrounding_elevations else 0.0
                prominence = point.elevation - avg_surrounding
            else:
                prominence = point.elevation
            # compute isolation (distance to nearest higher peak)
            isolation = 1.0
            for other in candidates:
                if other.elevation <= point.elevation:
                    continue
                distance = math.sqrt((point.x - other.x) ** 2 + (point.y - other.y) ** 2)
                isolation = min(isolation, distance)
            # determine if summit
            is_summit = False
            if point.elevation > summit_elevation:
                summit_elevation = point.elevation
                summit_id = point.point_id
            peak_id = f"peak_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
            peak = DramaticPeak(
                peak_id=peak_id,
                point_id=point.point_id,
                label=point.label,
                elevation=point.elevation,
                tension_type=point.tension_type,
                surrounding_points=surrounding,
                prominence=prominence,
                isolation=isolation,
            )
            self._peaks[peak_id] = peak
            peaks_identified += 1
            point.feature = TerrainFeature.PEAK
        # mark summit
        if summit_id:
            for peak in self._peaks.values():
                if peak.point_id == summit_id:
                    peak.is_summit = True
                    peak.feature = TerrainFeature.SUMMIT
                    self._record_event("summit_identified", {
                        "peak_id": peak.peak_id,
                        "point_id": summit_id,
                        "elevation": summit_elevation,
                    })
                    break
        return {
            "peaks_identified": peaks_identified,
            "summit_elevation": summit_elevation,
            "total_peaks": len(self._peaks),
        }

    def _phase_erode(self) -> Dict[str, Any]:
        """Erosion phase: tension erodes over time."""
        eroded = 0
        flattened = 0
        for point in self._points.values():
            if point.state == TensionState.DORMANT:
                continue
            old_elevation = point.elevation
            # erosion rate is higher for peaks
            if point.elevation > self._PEAK_THRESHOLD:
                erosion = self._EROSION_RATE * 1.5
            else:
                erosion = self._EROSION_RATE
            point.elevation = max(0.0, point.elevation - erosion)
            point.gradient = point.elevation - old_elevation
            if point.gradient < -0.01:
                point.state = TensionState.ERODING
                eroded += 1
            # peaks that erode below threshold flatten
            if old_elevation > self._PEAK_THRESHOLD and point.elevation < self._PEAK_THRESHOLD:
                point.feature = TerrainFeature.SLOPE
                flattened += 1
        return {
            "points_eroded": eroded,
            "peaks_flattened": flattened,
            "avg_elevation": (
                sum(p.elevation for p in self._points.values()) / len(self._points)
                if self._points else 0.0
            ),
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_point(self, point_id: str) -> Dict[str, Any]:
        """Get a specific tension point."""
        with self._global_lock:
            p = self._points.get(point_id)
            if p is None:
                return {"error": f"Point not found: {point_id}"}
            return self._serialize_point(p)

    def get_all_points(self) -> List[Dict[str, Any]]:
        """Get all tension points."""
        with self._global_lock:
            return [self._serialize_point(p) for p in self._points.values()]

    def get_contours(self) -> List[Dict[str, Any]]:
        """Get all contour lines."""
        with self._global_lock:
            return [
                {
                    "contour_id": c.contour_id,
                    "elevation": c.elevation,
                    "point_ids": list(c.point_ids),
                    "feature": c.feature.value,
                    "length": c.length,
                    "closed": c.closed,
                }
                for c in self._contours.values()
            ]

    def get_peaks(self) -> List[Dict[str, Any]]:
        """Get all identified dramatic peaks."""
        with self._global_lock:
            return [
                {
                    "peak_id": p.peak_id,
                    "point_id": p.point_id,
                    "label": p.label,
                    "elevation": p.elevation,
                    "tension_type": p.tension_type.value,
                    "surrounding_points": list(p.surrounding_points),
                    "feature": p.feature.value,
                    "prominence": p.prominence,
                    "isolation": p.isolation,
                    "is_summit": p.is_summit,
                }
                for p in self._peaks.values()
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the cartographer."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles and return the final status."""
        with self._global_lock:
            for _ in range(max(1, cycles)):
                self.cycle()
            return self.get_status()

    def reset(self) -> Dict[str, Any]:
        """Reset the entire cartographer."""
        with self._global_lock:
            self._points.clear()
            self._contours.clear()
            self._peaks.clear()
            self._phase = TopologyPhase.SURVEY
            self._cycle_count = 0
            self._events_log.clear()
            self._init_stats()
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _find_connected_group(self, point_ids: List[str]) -> List[List[str]]:
        """Find groups of connected points within a set."""
        if not point_ids:
            return []
        point_set = set(point_ids)
        visited: Set[str] = set()
        groups: List[List[str]] = []
        for pid in point_ids:
            if pid in visited:
                continue
            # BFS to find connected group
            group = []
            queue = deque([pid])
            visited.add(pid)
            while queue:
                current = queue.popleft()
                group.append(current)
                point = self._points.get(current)
                if point is None:
                    continue
                for adj_id in point.connected_to:
                    if adj_id in point_set and adj_id not in visited:
                        visited.add(adj_id)
                        queue.append(adj_id)
            if group:
                groups.append(group)
        return groups

    def _serialize_point(self, p: TensionPoint) -> Dict[str, Any]:
        return {
            "point_id": p.point_id,
            "label": p.label,
            "tension_type": p.tension_type.value,
            "x": p.x,
            "y": p.y,
            "elevation": p.elevation,
            "state": p.state.value,
            "gradient": p.gradient,
            "connected_to": list(p.connected_to),
            "feature": p.feature.value,
            "last_updated": p.last_updated,
            "created_at": p.created_at,
            "description": p.description,
            "stakeholders": list(p.stakeholders),
        }

    def _update_stats(self) -> None:
        total_points = len(self._points)
        rising = 0
        holding = 0
        falling = 0
        dormant = 0
        peaked = 0
        eroding = 0
        cliffs = 0
        ridges = 0
        plateaus = 0
        valleys = 0
        total_elevation = 0.0
        total_gradient = 0.0
        for p in self._points.values():
            total_elevation += p.elevation
            total_gradient += abs(p.gradient)
            if p.state == TensionState.RISING:
                rising += 1
            elif p.state == TensionState.HOLDING:
                holding += 1
            elif p.state == TensionState.FALLING:
                falling += 1
            elif p.state == TensionState.DORMANT:
                dormant += 1
            elif p.state == TensionState.PEAKED:
                peaked += 1
            elif p.state == TensionState.ERODING:
                eroding += 1
            if p.feature == TerrainFeature.CLIFF:
                cliffs += 1
            elif p.feature == TerrainFeature.RIDGE:
                ridges += 1
            elif p.feature == TerrainFeature.PLATEAU:
                plateaus += 1
            elif p.feature == TerrainFeature.VALLEY:
                valleys += 1
        summit_elevation = max((p.elevation for p in self._points.values()), default=0.0)
        self._stats["total_points"] = total_points
        self._stats["total_contours"] = len(self._contours)
        self._stats["total_peaks"] = len(self._peaks)
        self._stats["summit_elevation"] = summit_elevation
        self._stats["avg_elevation"] = total_elevation / total_points if total_points else 0.0
        self._stats["avg_gradient"] = total_gradient / total_points if total_points else 0.0
        self._stats["rising_points"] = rising
        self._stats["holding_points"] = holding
        self._stats["falling_points"] = falling
        self._stats["dormant_points"] = dormant
        self._stats["peaked_points"] = peaked
        self._stats["eroding_points"] = eroding
        self._stats["cliffs"] = cliffs
        self._stats["ridges"] = ridges
        self._stats["plateaus"] = plateaus
        self._stats["valleys"] = valleys

    def _init_stats(self) -> None:
        self._stats = {
            "total_points": 0,
            "total_contours": 0,
            "total_peaks": 0,
            "summit_elevation": 0.0,
            "avg_elevation": 0.0,
            "avg_gradient": 0.0,
            "rising_points": 0,
            "holding_points": 0,
            "falling_points": 0,
            "dormant_points": 0,
            "peaked_points": 0,
            "eroding_points": 0,
            "cliffs": 0,
            "ridges": 0,
            "plateaus": 0,
            "valleys": 0,
            "last_cycle_time_ms": 0.0,
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
