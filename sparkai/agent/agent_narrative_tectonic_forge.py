"""
SparkLabs Agent - Narrative Tectonic Forge

The AgentNarrativeTectonicForge models narrative structure as tectonic
plates drifting across the story world. Rather than treating plot as a
fixed script or a tree of branching choices, it treats stories as
geological formations: narrative plates drift slowly along their vectors,
stress accumulates where plates meet, ruptures release that stress as
plot twists, uplift raises new climactic mountains, and subduction
recycles exhausted storylines back into the narrative mantle.

This tectonic metaphor captures how stories actually breathe in living
worlds: narratives do not stay frozen, they drift and press against each
other. Tension does not dissipate on its own, it builds until something
gives way. Twists are not authored in isolation, they erupt from
accumulated pressure. And old storylines do not simply vanish, they
subduct and feed the magma that drives new revelations.

Core concepts:
  - PLATE     : a narrative stratum drifting across the story world
  - VECTOR    : the direction a plate is drifting (intent vector)
  - STRESS    : accumulated tension at plate boundaries (0.0-1.0)
  - FAULT     : a boundary where two plates meet and grind
  - SEISM     : a seismic event (plot twist) released by a rupture
  - MANTLE    : the reservoir of recycled narrative material

Plate types:
  CHARACTER  : character-driven plates, slow drift, deep subduction
  PLOT       : event-driven plates, fast drift, frequent ruptures
  THEME      : thematic plates, very slow drift, massive uplift
  SETTING    : world-building plates, stable, broad foundations
  CONFLICT   : tension-driven plates, high stress, explosive seisms

Tectonic events:
  PLATE_BIRTH      : a new narrative plate forms from the mantle
  DRIFT_MOTION     : a plate drifts along its vector
  STRESS_BUILDUP   : tension accumulates at a fault boundary
  SEISMIC_RUPTURE  : a fault ruptures, releasing a plot twist
  MOUNTAIN_UPHILL  : stress uplifts a new climactic mountain
  SUBDUCTION       : an exhausted plate subducts into the mantle
  MANTLE_PLUME     : recycled material erupts as a new plate

Architecture:
  DRIFT  ->  STRESS  ->  RUPTURE  ->  UPLIFT  ->  SUBDUCT
  (plates  (tension    (faults      (uplift      (exhausted
   drift   accumulates rupture      raises       plates sink
   along   at faults)  into plot    climactic    back into
   vectors)            twists)      mountains)   the mantle)

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
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class PlateType(Enum):
    """Structural types of narrative plates."""
    CHARACTER = "character"    # character-driven, slow drift, deep
    PLOT = "plot"              # event-driven, fast drift, volatile
    THEME = "theme"            # thematic, very slow, massive uplift
    SETTING = "setting"        # world-building, stable, broad
    CONFLICT = "conflict"      # tension-driven, high stress, explosive


class TectonicPhase(Enum):
    """Phases of the narrative tectonic cycle."""
    DRIFT = "drift"
    STRESS = "stress"
    RUPTURE = "rupture"
    UPLIFT = "uplift"
    SUBDUCT = "subduct"


class TectonicEvent(Enum):
    """Events that occur during the tectonic cycle."""
    PLATE_BIRTH = "plate_birth"
    DRIFT_MOTION = "drift_motion"
    STRESS_BUILDUP = "stress_buildup"
    SEISMIC_RUPTURE = "seismic_rupture"
    MOUNTAIN_UPHILL = "mountain_uphill"
    SUBDUCTION = "subduction"
    MANTLE_PLUME = "mantle_plume"


# =============================================================================
# Default Parameters by Plate Type
# =============================================================================

# Default drift rate for each plate type
DEFAULT_PLATE_DRIFT: Dict[PlateType, float] = {
    PlateType.CHARACTER: 0.04,
    PlateType.PLOT: 0.12,
    PlateType.THEME: 0.02,
    PlateType.SETTING: 0.03,
    PlateType.CONFLICT: 0.10,
}

# Default mass for each plate type (heavier plates drift slower)
DEFAULT_PLATE_MASS: Dict[PlateType, float] = {
    PlateType.CHARACTER: 0.7,
    PlateType.PLOT: 0.4,
    PlateType.THEME: 0.9,
    PlateType.SETTING: 0.85,
    PlateType.CONFLICT: 0.55,
}

# Default stress tolerance before rupture
DEFAULT_PLATE_TOLERANCE: Dict[PlateType, float] = {
    PlateType.CHARACTER: 0.7,
    PlateType.PLOT: 0.4,
    PlateType.THEME: 0.85,
    PlateType.SETTING: 0.8,
    PlateType.CONFLICT: 0.3,
}

# Default narrative richness (content density)
DEFAULT_PLATE_RICHNESS: Dict[PlateType, float] = {
    PlateType.CHARACTER: 0.7,
    PlateType.PLOT: 0.5,
    PlateType.THEME: 0.85,
    PlateType.SETTING: 0.75,
    PlateType.CONFLICT: 0.6,
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class NarrativePlate:
    """A narrative plate drifting across the story world."""
    plate_id: str
    label: str
    plate_type: PlateType
    # Narrative mass (heavier = slower drift, deeper subduction)
    mass: float
    # Drift vector [dx, dy] (direction and speed of narrative motion)
    drift_vector: List[float]
    # Current drift progress along the vector (0.0-1.0)
    drift_progress: float
    # Accumulated stress at boundaries (0.0-1.0)
    stress: float
    # Stress tolerance before rupture
    stress_tolerance: float
    # Narrative richness / content density (0.0-1.0)
    richness: float
    # Current elevation (uplift from mountain formation, 0.0-1.0)
    elevation: float
    # Whether the plate has ruptured recently
    ruptured: bool = False
    # Whether the plate is subducting (being recycled)
    subducting: bool = False
    # Number of seismic events released
    seism_count: int = 0
    # Mantle depth (how deep it has subducted, 0.0 = surface)
    mantle_depth: float = 0.0
    age_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class FaultBoundary:
    """A boundary where two narrative plates meet and grind."""
    fault_id: str
    plate_a_id: str
    plate_b_id: str
    # Compressive stress at this fault (0.0-1.0)
    stress: float
    # Slip rate - how fast the plates grind past each other
    slip_rate: float
    # Whether this fault has ruptured
    ruptured: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class SeismRecord:
    """A recorded seismic event (plot twist) from a ruptured fault."""
    seism_id: str
    source_fault_id: str
    plate_a_id: str
    plate_b_id: str
    # Magnitude of the seism (0.0-1.0)
    magnitude: float
    # Whether it produced an uplift (climactic mountain)
    produced_uplift: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class TectonicStats:
    """Aggregate statistics for the narrative tectonic forge."""
    total_plates: int = 0
    total_faults: int = 0
    total_seisms: int = 0
    total_events: int = 0
    total_plate_births: int = 0
    total_drift_motions: int = 0
    total_ruptures: int = 0
    total_uplifts: int = 0
    total_subductions: int = 0
    total_mantle_plumes: int = 0
    avg_stress: float = 0.0
    avg_richness: float = 0.0
    avg_elevation: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Narrative Tectonic Forge
# =============================================================================

class AgentNarrativeTectonicForge:
    """
    Singleton agent subsystem that models narrative as tectonic plates
    drifting across the story world. Plates drift along their vectors,
    stress accumulates at faults where plates meet, ruptures release
    seismic plot twists, uplift raises climactic mountains, and
    subduction recycles exhausted plates back into the narrative mantle.

    The forge runs a 5-phase cycle:
      1. DRIFT    - Plates move along their drift vectors
      2. STRESS   - Tension accumulates at fault boundaries
      3. RUPTURE  - Over-stressed faults release seismic plot twists
      4. UPLIFT   - Released stress uplifts new climactic mountains
      5. SUBDUCT  - Exhausted plates sink into the mantle and recycle

    The tectonic metaphor ensures narrative feels alive: stories drift
    and press against each other, tension builds until it must release,
    and old material feeds new revelations through the mantle.
    """

    _instance: Optional["AgentNarrativeTectonicForge"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_PLATES = 80
    MAX_FAULTS = 150
    MAX_SEISMS = 100
    MAX_EVENT_HISTORY = 200
    MAX_MANTLE_MATERIAL = 50
    # Drift progress bounds
    MIN_DRIFT = 0.0
    MAX_DRIFT = 1.0
    # How fast drift_progress moves
    DRIFT_ADJUSTMENT_RATE = 0.08
    # Natural stress accumulation per cycle
    NATURAL_STRESS_GAIN = 0.03
    # Stress added by forced tension
    FORCED_STRESS_GAIN = 0.2
    # Stress tolerance bounds
    MIN_TOLERANCE = 0.1
    MAX_TOLERANCE = 1.0
    # Stress bounds
    MIN_STRESS = 0.0
    MAX_STRESS = 1.0
    # Richness bounds
    MIN_RICHNESS = 0.0
    MAX_RICHNESS = 1.0
    # Elevation bounds
    MIN_ELEVATION = 0.0
    MAX_ELEVATION = 1.0
    # Mass bounds
    MIN_MASS = 0.1
    MAX_MASS = 1.0
    # Mantle depth bounds
    MAX_MANTLE_DEPTH = 1.0
    # Probability of spontaneous plate birth from mantle
    SPONTANEOUS_BIRTH_PROBABILITY = 0.12
    # Minimum stress to trigger rupture
    RUPTURE_STRESS_THRESHOLD = 0.6
    # Mantle material needed to spawn a new plate
    MANTEL_PLUME_THRESHOLD = 3
    # Richness threshold for subduction (plates below this can subduct)
    SUBDUCTION_RICHNESS_THRESHOLD = 0.15
    # Probability of subduction per eligible plate
    SUBDUCTION_PROBABILITY = 0.25
    # Elevation gain per uplift event
    UPLIFT_GAIN = 0.18
    # Elevation erosion per cycle
    ELEVATION_EROSION = 0.02
    # Richness gain per drift cycle
    RICHNESS_DRIFT_GAIN = 0.04

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._plates: Dict[str, NarrativePlate] = {}
        self._faults: Deque[FaultBoundary] = deque(maxlen=self.MAX_FAULTS)
        self._seisms: Deque[SeismRecord] = deque(maxlen=self.MAX_SEISMS)
        self._event_history: Deque[Dict[str, Any]] = deque(
            maxlen=self.MAX_EVENT_HISTORY
        )
        # Mantle material pool - recycled narrative substance
        self._mantle_material: float = 0.0
        self._stats = TectonicStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._fault_counter: int = 0
        self._seism_counter: int = 0
        self._event_counter: int = 0

    @classmethod
    def get_instance(cls) -> "AgentNarrativeTectonicForge":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Plate Management
    # -------------------------------------------------------------------------

    def register_plate(
        self,
        plate_id: str,
        label: str,
        plate_type: str = "plot",
        mass: Optional[float] = None,
        drift_vector: Optional[List[float]] = None,
        richness: Optional[float] = None,
        stress_tolerance: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a new narrative plate in the forge."""
        with self._lock:
            if plate_id in self._plates:
                return {"error": f"Plate already registered: {plate_id}"}
            if len(self._plates) >= self.MAX_PLATES:
                return {"error": "Maximum plates reached"}

            try:
                ptype = PlateType(plate_type)
            except ValueError:
                return {"error": f"Unknown plate type: {plate_type}"}

            if mass is None:
                mass = DEFAULT_PLATE_MASS.get(ptype, 0.5)
            mass = max(self.MIN_MASS, min(self.MAX_MASS, float(mass)))

            if drift_vector is None:
                # Random unit vector scaled by drift rate
                angle = random.uniform(0, 2 * math.pi)
                rate = DEFAULT_PLATE_DRIFT.get(ptype, 0.08)
                drift_vector = [math.cos(angle) * rate, math.sin(angle) * rate]
            else:
                if len(drift_vector) != 2:
                    return {"error": "drift_vector must have exactly 2 elements"}
                drift_vector = [float(drift_vector[0]), float(drift_vector[1])]

            if richness is None:
                richness = DEFAULT_PLATE_RICHNESS.get(ptype, 0.5)
            richness = max(self.MIN_RICHNESS, min(self.MAX_RICHNESS, float(richness)))

            if stress_tolerance is None:
                stress_tolerance = DEFAULT_PLATE_TOLERANCE.get(ptype, 0.5)
            stress_tolerance = max(self.MIN_TOLERANCE, min(self.MAX_TOLERANCE, float(stress_tolerance)))

            plate = NarrativePlate(
                plate_id=plate_id,
                label=label,
                plate_type=ptype,
                mass=mass,
                drift_vector=drift_vector,
                drift_progress=0.2,
                stress=0.0,
                stress_tolerance=stress_tolerance,
                richness=richness,
                elevation=0.0,
            )
            self._plates[plate_id] = plate

            # Check for fault boundaries with existing plates
            self._check_fault_boundaries(plate_id)

            self._stats.total_plates = len(self._plates)
            return self._plate_to_dict(plate)

    def get_plate(self, plate_id: str) -> Dict[str, Any]:
        """Get the state of a specific narrative plate."""
        with self._lock:
            plate = self._plates.get(plate_id)
            if plate is None:
                return {"error": f"Plate not found: {plate_id}"}
            return self._plate_to_dict(plate)

    def list_plates(
        self, plate_type: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """List plates, optionally filtered by plate type."""
        with self._lock:
            plates = list(self._plates.values())
            if plate_type:
                try:
                    ptype = PlateType(plate_type)
                    plates = [p for p in plates if p.plate_type == ptype]
                except ValueError:
                    return []
            plates = plates[:limit]
            return [self._plate_to_dict(p) for p in plates]

    def remove_plate(self, plate_id: str) -> Dict[str, Any]:
        """Remove a plate from the forge."""
        with self._lock:
            if plate_id not in self._plates:
                return {"removed": False, "plate_id": plate_id}
            # Remove faults referencing this plate
            self._faults = deque(
                (f for f in self._faults
                 if f.plate_a_id != plate_id and f.plate_b_id != plate_id),
                maxlen=self.MAX_FAULTS,
            )
            del self._plates[plate_id]
            self._stats.total_plates = len(self._plates)
            self._stats.total_faults = len(self._faults)
            return {"removed": True, "plate_id": plate_id}

    def set_plate_drift_vector(
        self, plate_id: str, drift_vector: List[float], description: str = ""
    ) -> Dict[str, Any]:
        """Set the drift vector of a narrative plate."""
        with self._lock:
            plate = self._plates.get(plate_id)
            if plate is None:
                return {"error": f"Plate not found: {plate_id}"}
            if len(drift_vector) != 2:
                return {"error": "drift_vector must have exactly 2 elements"}
            plate.drift_vector = [float(drift_vector[0]), float(drift_vector[1])]
            return {
                "plate_id": plate_id,
                "drift_vector": plate.drift_vector,
                "description": description,
            }

    def apply_tension(
        self, plate_id: str, magnitude: float = 0.2, description: str = ""
    ) -> Dict[str, Any]:
        """Apply narrative tension to a plate, increasing its stress."""
        with self._lock:
            plate = self._plates.get(plate_id)
            if plate is None:
                return {"error": f"Plate not found: {plate_id}"}
            magnitude = max(0.0, min(1.0, float(magnitude)))
            plate.stress = min(self.MAX_STRESS, plate.stress + magnitude)
            return {
                "plate_id": plate_id,
                "stress": round(plate.stress, 4),
                "description": description,
            }

    # -------------------------------------------------------------------------
    # Fault Management
    # -------------------------------------------------------------------------

    def list_faults(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List fault boundaries between plates."""
        with self._lock:
            faults = list(self._faults)[:limit]
            return [self._fault_to_dict(f) for f in faults]

    def get_fault(self, fault_id: str) -> Dict[str, Any]:
        """Get a specific fault boundary."""
        with self._lock:
            for f in self._faults:
                if f.fault_id == fault_id:
                    return self._fault_to_dict(f)
            return {"error": f"Fault not found: {fault_id}"}

    # -------------------------------------------------------------------------
    # Seism Management
    # -------------------------------------------------------------------------

    def list_seisms(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List recorded seismic events (plot twists)."""
        with self._lock:
            seisms = list(self._seisms)[:limit]
            return [self._seism_to_dict(s) for s in seisms]

    def get_seism(self, seism_id: str) -> Dict[str, Any]:
        """Get a specific seismic event."""
        with self._lock:
            for s in self._seisms:
                if s.seism_id == seism_id:
                    return self._seism_to_dict(s)
            return {"error": f"Seism not found: {seism_id}"}

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single narrative tectonic cycle.

        Phases: DRIFT -> STRESS -> RUPTURE -> UPLIFT -> SUBDUCT
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: DRIFT - plates move along their vectors
            drift_info = self._drift_phase()

            # Phase 2: STRESS - tension accumulates at faults
            stress_info = self._stress_phase()

            # Phase 3: RUPTURE - over-stressed faults release seisms
            rupture_info = self._rupture_phase()

            # Phase 4: UPLIFT - released stress raises mountains
            uplift_info = self._uplift_phase()

            # Phase 5: SUBDUCT - exhausted plates sink into the mantle
            subduct_info = self._subduct_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            phase = TectonicPhase.SUBDUCT
            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "drift": drift_info,
                "stress": stress_info,
                "rupture": rupture_info,
                "uplift": uplift_info,
                "subduct": subduct_info,
                "total_plates": len(self._plates),
                "total_faults": len(self._faults),
                "total_seisms": len(self._seisms),
                "mantle_material": round(self._mantle_material, 4),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _drift_phase(self) -> Dict[str, Any]:
        """Phase 1: Plates drift along their vectors."""
        drift_motions = 0
        for plate in self._plates.values():
            plate.age_cycles += 1
            # Drift progress advances based on vector magnitude and inverse mass
            vec_mag = math.sqrt(plate.drift_vector[0] ** 2 + plate.drift_vector[1] ** 2)
            drift_gain = (vec_mag / max(plate.mass, 0.1)) * self.DRIFT_ADJUSTMENT_RATE * 5.0
            plate.drift_progress = min(
                self.MAX_DRIFT, plate.drift_progress + drift_gain
            )
            # Richness grows with drift (exploration enriches narrative)
            if plate.richness < self.MAX_RICHNESS:
                plate.richness = min(
                    self.MAX_RICHNESS,
                    plate.richness + self.RICHNESS_DRIFT_GAIN * 0.5,
                )
            drift_motions += 1

            if drift_motions <= 3:  # Record events for first few
                self._record_event(
                    TectonicEvent.DRIFT_MOTION,
                    intensity=drift_gain,
                    plate_ids=[plate.plate_id],
                    description=f"Plate '{plate.label}' drifts (progress={plate.drift_progress:.3f})",
                )

        self._stats.total_drift_motions += drift_motions
        return {
            "drift_motions": drift_motions,
            "plates_drifted": drift_motions,
        }

    def _stress_phase(self) -> Dict[str, Any]:
        """Phase 2: Tension accumulates at fault boundaries."""
        stress_buildups = 0
        total_stress = 0.0

        # Natural stress accumulation on plates
        for plate in self._plates.values():
            plate.stress = min(
                self.MAX_STRESS,
                plate.stress + self.NATURAL_STRESS_GAIN,
            )

        # Stress builds at faults
        for fault in self._faults:
            plate_a = self._plates.get(fault.plate_a_id)
            plate_b = self._plates.get(fault.plate_b_id)
            if plate_a is None or plate_b is None:
                continue
            # Stress builds based on combined plate stress
            avg_stress = (plate_a.stress + plate_b.stress) / 2
            fault.stress = min(self.MAX_STRESS, fault.stress + avg_stress * 0.15)
            # Slip rate based on mass differential
            mass_diff = abs(plate_a.mass - plate_b.mass)
            fault.slip_rate = min(1.0, fault.slip_rate + mass_diff * 0.1)
            total_stress += fault.stress
            stress_buildups += 1

        if stress_buildups > 0:
            self._record_event(
                TectonicEvent.STRESS_BUILDUP,
                intensity=min(1.0, total_stress / max(stress_buildups, 1)),
                plate_ids=[],
                description=f"{stress_buildups} faults accumulated stress",
            )
        self._stats.total_events += stress_buildups
        return {
            "stress_buildups": stress_buildups,
            "total_fault_stress": round(total_stress, 4),
        }

    def _rupture_phase(self) -> Dict[str, Any]:
        """Phase 3: Over-stressed faults rupture into seismic plot twists."""
        ruptures = 0
        seisms_released = 0

        for fault in self._faults:
            if fault.stress >= self.RUPTURE_STRESS_THRESHOLD and not fault.ruptured:
                fault.ruptured = True
                ruptures += 1
                # Magnitude based on accumulated stress
                magnitude = min(1.0, fault.stress)
                self._seism_counter += 1
                seism = SeismRecord(
                    seism_id=f"seism_{self._seism_counter}",
                    source_fault_id=fault.fault_id,
                    plate_a_id=fault.plate_a_id,
                    plate_b_id=fault.plate_b_id,
                    magnitude=magnitude,
                )
                self._seisms.append(seism)
                seisms_released += 1

                # Stress is released from the plates
                plate_a = self._plates.get(fault.plate_a_id)
                plate_b = self._plates.get(fault.plate_b_id)
                if plate_a:
                    plate_a.stress = max(self.MIN_STRESS, plate_a.stress - magnitude * 0.6)
                    plate_a.ruptured = True
                    plate_a.seism_count += 1
                if plate_b:
                    plate_b.stress = max(self.MIN_STRESS, plate_b.stress - magnitude * 0.6)
                    plate_b.ruptured = True
                    plate_b.seism_count += 1

                self._record_event(
                    TectonicEvent.SEISMIC_RUPTURE,
                    intensity=magnitude,
                    plate_ids=[fault.plate_a_id, fault.plate_b_id],
                    description=f"Fault '{fault.fault_id}' ruptured (magnitude={magnitude:.3f})",
                )

        # Reset rupture flags after the phase
        for fault in self._faults:
            fault.ruptured = False
            fault.stress = max(self.MIN_STRESS, fault.stress * 0.3)  # residual stress

        # Clear plate rupture flags
        for plate in self._plates.values():
            plate.ruptured = False

        self._stats.total_ruptures += ruptures
        self._stats.total_seisms = len(self._seisms)
        return {
            "faults_ruptured": ruptures,
            "seisms_released": seisms_released,
        }

    def _uplift_phase(self) -> Dict[str, Any]:
        """Phase 4: Released stress uplifts new climactic mountains."""
        uplifts = 0
        for seism in self._seisms:
            if seism.produced_uplift:
                continue
            # High-magnitude seisms produce uplift
            if seism.magnitude >= 0.5:
                seism.produced_uplift = True
                plate_a = self._plates.get(seism.plate_a_id)
                plate_b = self._plates.get(seism.plate_b_id)
                for plate in (plate_a, plate_b):
                    if plate is not None:
                        plate.elevation = min(
                            self.MAX_ELEVATION,
                            plate.elevation + self.UPLIFT_GAIN * seism.magnitude,
                        )
                        uplifts += 1
                self._record_event(
                    TectonicEvent.MOUNTAIN_UPHILL,
                    intensity=seism.magnitude,
                    plate_ids=[seism.plate_a_id, seism.plate_b_id],
                    description=f"Seism '{seism.seism_id}' uplifted climactic mountain",
                )

        # Erosion: elevation slowly decays
        for plate in self._plates.values():
            if plate.elevation > 0:
                plate.elevation = max(
                    self.MIN_ELEVATION,
                    plate.elevation - self.ELEVATION_EROSION,
                )

        self._stats.total_uplifts += uplifts
        return {
            "uplifts_raised": uplifts,
        }

    def _subduct_phase(self) -> Dict[str, Any]:
        """Phase 5: Exhausted plates subduct into the mantle and recycle."""
        subductions = 0
        mantle_plumes = 0
        to_remove: List[str] = []

        for plate_id, plate in self._plates.items():
            # Plates with very low richness can subduct
            if (plate.richness < self.SUBDUCTION_RICHNESS_THRESHOLD
                    and not plate.subducting
                    and random.random() < self.SUBDUCTION_PROBABILITY):
                plate.subducting = True
                plate.mantle_depth = min(
                    self.MAX_MANTLE_DEPTH, plate.mantle_depth + 0.5
                )
                # Recycle mass into mantle material
                self._mantle_material += plate.mass * plate.richness * 2.0
                subductions += 1
                self._record_event(
                    TectonicEvent.SUBDUCTION,
                    intensity=plate.mass,
                    plate_ids=[plate_id],
                    description=f"Plate '{plate.label}' subducted into mantle",
                )
                to_remove.append(plate_id)

        for pid in to_remove:
            self.remove_plate(pid)

        # Mantle plume: if enough material accumulates, spawn a new plate
        if (self._mantle_material >= self.MANTEL_PLUME_THRESHOLD
                and len(self._plates) < self.MAX_PLATES
                and random.random() < 0.5):
            self._mantle_material -= self.MANTEL_PLUME_THRESHOLD
            ptype = random.choice(list(PlateType))
            new_id = f"plume_{self._cycle_count}_{mantle_plumes}"
            label = f"Mantle-forged {ptype.value} narrative"
            result = self.register_plate(
                new_id, label, ptype.value,
                richness=0.6, mass=0.6,
            )
            if "error" not in result:
                mantle_plumes += 1
                self._record_event(
                    TectonicEvent.MANTLE_PLUME,
                    intensity=0.7,
                    plate_ids=[new_id],
                    description=f"Mantle plume birthed new plate '{new_id}'",
                )

        self._stats.total_subductions += subductions
        self._stats.total_mantle_plumes += mantle_plumes
        return {
            "subductions": subductions,
            "mantle_plumes": mantle_plumes,
            "mantle_material": round(self._mantle_material, 4),
        }

    def _check_fault_boundaries(self, new_plate_id: str) -> None:
        """Check if a new plate forms fault boundaries with existing ones."""
        new_plate = self._plates.get(new_plate_id)
        if new_plate is None:
            return
        for other_id, other in self._plates.items():
            if other_id == new_plate_id:
                continue
            # Faults form between plates of different types (tension zones)
            # or same type (compression zones)
            mass_diff = abs(new_plate.mass - other.mass)
            # Higher chance of fault if plates are different types or similar mass
            if new_plate.plate_type != other.plate_type or mass_diff < 0.3:
                self._fault_counter += 1
                fault = FaultBoundary(
                    fault_id=f"fault_{self._fault_counter}",
                    plate_a_id=new_plate_id,
                    plate_b_id=other_id,
                    stress=0.1,
                    slip_rate=0.1,
                )
                self._faults.append(fault)
                self._record_event(
                    TectonicEvent.STRESS_BUILDUP,
                    intensity=0.1,
                    plate_ids=[new_plate_id, other_id],
                    description=f"Fault '{fault.fault_id}' formed between '{new_plate.label}' and '{other.label}'",
                )

    # -------------------------------------------------------------------------
    # Simulation & Status
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles and return the final status."""
        cycles = max(1, min(100, int(cycles)))
        last_cycle = None
        for _ in range(cycles):
            last_cycle = self.run_cycle()
        return {
            "cycles_run": cycles,
            "last_cycle": last_cycle,
            "status": self.get_status(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the tectonic forge."""
        with self._lock:
            self._stats.total_plates = len(self._plates)
            self._stats.total_faults = len(self._faults)
            self._stats.total_seisms = len(self._seisms)
            self._stats.total_events = len(self._event_history)
            self._update_avg_metrics()
            return {
                "total_plates": self._stats.total_plates,
                "total_faults": self._stats.total_faults,
                "total_seisms": self._stats.total_seisms,
                "mantle_material": round(self._mantle_material, 4),
                "active": self._active,
                "cycle_count": self._cycle_count,
                "stats": {
                    "total_events": self._stats.total_events,
                    "total_plate_births": self._stats.total_plate_births,
                    "total_drift_motions": self._stats.total_drift_motions,
                    "total_ruptures": self._stats.total_ruptures,
                    "total_uplifts": self._stats.total_uplifts,
                    "total_subductions": self._stats.total_subductions,
                    "total_mantle_plumes": self._stats.total_mantle_plumes,
                    "avg_stress": round(self._stats.avg_stress, 4),
                    "avg_richness": round(self._stats.avg_richness, 4),
                    "avg_elevation": round(self._stats.avg_elevation, 4),
                    "last_cycle_time_ms": self._stats.last_cycle_time_ms,
                },
            }

    def get_events(
        self, plate_type: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent tectonic events, optionally filtered by plate type."""
        with self._lock:
            events = list(self._event_history)
            if plate_type:
                events = [e for e in events if e.get("plate_type") == plate_type]
            return events[:limit]

    def reset(self) -> Dict[str, Any]:
        """Reset the tectonic forge to its initial state."""
        with self._lock:
            self._plates.clear()
            self._faults.clear()
            self._seisms.clear()
            self._event_history.clear()
            self._mantle_material = 0.0
            self._stats = TectonicStats()
            self._cycle_count = 0
            self._active = False
            self._fault_counter = 0
            self._seism_counter = 0
            self._event_counter = 0
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _record_event(
        self,
        event: TectonicEvent,
        intensity: float,
        plate_ids: List[str],
        description: str,
    ) -> None:
        """Record a tectonic event in the history."""
        self._event_counter += 1
        self._event_history.append({
            "event_id": f"te_{self._event_counter}",
            "event_type": event.value,
            "intensity": round(max(0.0, min(1.0, intensity)), 4),
            "plate_ids": plate_ids,
            "description": description,
            "timestamp": time.time(),
        })

    def _update_avg_metrics(self) -> None:
        """Update average metrics from current plates."""
        if not self._plates:
            self._stats.avg_stress = 0.0
            self._stats.avg_richness = 0.0
            self._stats.avg_elevation = 0.0
            return
        n = len(self._plates)
        self._stats.avg_stress = sum(p.stress for p in self._plates.values()) / n
        self._stats.avg_richness = sum(p.richness for p in self._plates.values()) / n
        self._stats.avg_elevation = sum(p.elevation for p in self._plates.values()) / n

    def _plate_to_dict(self, plate: NarrativePlate) -> Dict[str, Any]:
        """Convert a plate to a dictionary representation."""
        return {
            "plate_id": plate.plate_id,
            "label": plate.label,
            "plate_type": plate.plate_type.value,
            "mass": round(plate.mass, 4),
            "drift_vector": [round(v, 4) for v in plate.drift_vector],
            "drift_progress": round(plate.drift_progress, 4),
            "stress": round(plate.stress, 4),
            "stress_tolerance": round(plate.stress_tolerance, 4),
            "richness": round(plate.richness, 4),
            "elevation": round(plate.elevation, 4),
            "ruptured": plate.ruptured,
            "subducting": plate.subducting,
            "seism_count": plate.seism_count,
            "mantle_depth": round(plate.mantle_depth, 4),
            "age_cycles": plate.age_cycles,
            "timestamp": plate.timestamp,
        }

    def _fault_to_dict(self, f: FaultBoundary) -> Dict[str, Any]:
        """Convert a fault boundary to a dictionary representation."""
        return {
            "fault_id": f.fault_id,
            "plate_a_id": f.plate_a_id,
            "plate_b_id": f.plate_b_id,
            "stress": round(f.stress, 4),
            "slip_rate": round(f.slip_rate, 4),
            "ruptured": f.ruptured,
            "timestamp": f.timestamp,
        }

    def _seism_to_dict(self, s: SeismRecord) -> Dict[str, Any]:
        """Convert a seism record to a dictionary representation."""
        return {
            "seism_id": s.seism_id,
            "source_fault_id": s.source_fault_id,
            "plate_a_id": s.plate_a_id,
            "plate_b_id": s.plate_b_id,
            "magnitude": round(s.magnitude, 4),
            "produced_uplift": s.produced_uplift,
            "timestamp": s.timestamp,
        }
