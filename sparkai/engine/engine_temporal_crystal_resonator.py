"""
SparkLabs Engine - Temporal Crystal Resonator

The EngineTemporalCrystalResonator models game time as a crystal lattice
through which temporal events propagate as phonon vibrations. Rather than
treating time as a uniform line or a simple tree of branches, it treats
time as a crystalline medium: events create vibrations that travel along
lattice axes, refract at zone boundaries, dampen over distance, and
ultimately anneal into the crystal's permanent structure.

This crystal metaphor captures how time actually flows in living game
worlds: time is not a metronome, it is a medium with structure. Different
regions have different temporal densities (anisotropic time flow). Events
do not simply happen and vanish, they vibrate through the medium and
affect neighboring moments. Past and future are not isolated, they are
coupled through standing waves. And history does not freeze, it anneals,
locking stable patterns while healing micro-fractures.

Core concepts:
  - LATTICE   : a temporal crystal lattice with its own structure
  - PHONON    : a vibration traveling through the temporal lattice
  - FREQUENCY : the oscillation rate of a phonon
  - AMPLITUDE : the strength of a temporal vibration
  - AXIS      : a directional axis along which phonons propagate
  - FRACTURE  : a micro-fracture in the lattice from accumulated stress
  - ZONE      : a region of the lattice with distinct temporal properties

Lattice types:
  CHRONO    : linear time crystal, uniform propagation, stable
  CYCLIC    : cyclic time crystal, standing waves, recurring events
  BRANCHED  : branching time crystal, multi-axis propagation
  ENTROPIC  : entropic time crystal, decay-driven, high dampening
  RESONANT  : resonant time crystal, harmonic amplification

Temporal events:
  PHONON_BORN       : a new vibration is born in the lattice
  PROPAGATION       : a phonon propagates along an axis
  REFRACTION        : a phonon refracts at a zone boundary
  STANDING_WAVE     : a phonon forms a standing wave pattern
  DAMPING           : a phonon dampens below perceptibility
  MICRO_FRACTURE    : accumulated stress creates a lattice fracture
  ANNEAL_LOCK       : a stable vibration is annealed into the lattice

Architecture:
  VIBRATE  ->  PROPAGATE  ->  REFRACT  ->  DAMP  ->  ANNEAL
  (events  (phonons travel (vibrations   (phonons  (stable
   create  along lattice   refract at     dampen    patterns
   phonon  axes to reach   zone           over      anneal
   vibrat- neighboring     boundaries)    distance)  into the
   ions)   moments)                       permanent
                                             lattice)

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

class LatticeType(Enum):
    """Structural types of temporal crystal lattices."""
    CHRONO = "chrono"      # linear time, uniform propagation, stable
    CYCLIC = "cyclic"      # cyclic time, standing waves, recurring events
    BRANCHED = "branched"  # branching time, multi-axis propagation
    ENTROPIC = "entropic"  # entropic time, decay-driven, high dampening
    RESONANT = "resonant"  # resonant time, harmonic amplification


class TemporalPhase(Enum):
    """Phases of the temporal crystal cycle."""
    VIBRATE = "vibrate"
    PROPAGATE = "propagate"
    REFRACT = "refract"
    DAMP = "damp"
    ANNEAL = "anneal"


class TemporalEvent(Enum):
    """Events that occur during the temporal crystal cycle."""
    PHONON_BORN = "phonon_born"
    PROPAGATION = "propagation"
    REFRACTION = "refraction"
    STANDING_WAVE = "standing_wave"
    DAMPING = "damping"
    MICRO_FRACTURE = "micro_fracture"
    ANNEAL_LOCK = "anneal_lock"


# =============================================================================
# Default Parameters by Lattice Type
# =============================================================================

DEFAULT_LATTICE_DENSITY: Dict[LatticeType, float] = {
    LatticeType.CHRONO: 0.7,     # medium density, uniform
    LatticeType.CYCLIC: 0.8,     # high density, tight cycles
    LatticeType.BRANCHED: 0.5,   # lower density, more gaps for branches
    LatticeType.ENTROPIC: 0.3,   # low density, decay dominates
    LatticeType.RESONANT: 0.9,   # very high density, amplification
}

DEFAULT_LATTICE_DAMPING: Dict[LatticeType, float] = {
    LatticeType.CHRONO: 0.05,    # low damping, vibrations persist
    LatticeType.CYCLIC: 0.02,    # very low damping, standing waves survive
    LatticeType.BRANCHED: 0.08,  # medium damping
    LatticeType.ENTROPIC: 0.20,  # high damping, fast decay
    LatticeType.RESONANT: 0.01,  # minimal damping, amplification
}

DEFAULT_LATTICE_REFRACTIVE_INDEX: Dict[LatticeType, float] = {
    LatticeType.CHRONO: 1.0,     # no refraction, straight propagation
    LatticeType.CYCLIC: 1.2,     # slight refraction
    LatticeType.BRANCHED: 1.8,   # high refraction, branching
    LatticeType.ENTROPIC: 1.4,   # moderate refraction
    LatticeType.RESONANT: 0.8,   # convergent refraction, focusing
}

DEFAULT_LATTICE_STRESS_TOLERANCE: Dict[LatticeType, float] = {
    LatticeType.CHRONO: 0.85,
    LatticeType.CYCLIC: 0.75,
    LatticeType.BRANCHED: 0.60,
    LatticeType.ENTROPIC: 0.50,
    LatticeType.RESONANT: 0.90,
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class TemporalPhonon:
    """A vibration traveling through the temporal crystal lattice."""
    phonon_id: str
    label: str
    lattice_type: LatticeType
    frequency: float       # oscillation rate
    amplitude: float       # vibration strength
    # Propagation axis as a unit vector (2D for simplicity)
    axis: Tuple[float, float]
    # Current position in the lattice (normalized 0.0-1.0)
    position: Tuple[float, float]
    damping_rate: float
    refractive_index: float
    stress: float = 0.0          # accumulated stress on the phonon
    annealed: bool = False       # annealed phonons are permanent
    standing_wave: bool = False  # phonon has formed a standing wave
    age_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class LatticeZone:
    """A region of the temporal lattice with distinct properties."""
    zone_id: str
    label: str
    lattice_type: LatticeType
    # Zone boundary (center + radius on the lattice)
    center: Tuple[float, float]
    radius: float
    density: float
    refractive_index: float
    stress_tolerance: float
    # Micro-fractures within this zone
    fracture_count: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class LatticeFracture:
    """A micro-fracture in the temporal lattice from accumulated stress."""
    fracture_id: str
    zone_id: str
    position: Tuple[float, float]
    severity: float     # how severe the fracture is (0.0-1.0)
    healed: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class StandingWave:
    """A standing wave pattern formed by cyclic phonon resonance."""
    wave_id: str
    phonon_id: str
    zone_id: str
    frequency: float
    amplitude: float
    # Number of cycles the standing wave has persisted
    persistence: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class TemporalStats:
    """Aggregate statistics for the temporal crystal resonator."""
    total_phonons: int = 0
    total_zones: int = 0
    total_fractures: int = 0
    total_standing_waves: int = 0
    total_events: int = 0
    total_phonon_born: int = 0
    total_propagations: int = 0
    total_refractions: int = 0
    total_standing_waves_formed: int = 0
    total_dampings: int = 0
    total_fractures_formed: int = 0
    total_anneal_locks: int = 0
    avg_amplitude: float = 0.0
    avg_stress: float = 0.0
    last_cycle_time_ms: float = 0.0


# =============================================================================
# Temporal Crystal Resonator
# =============================================================================

class EngineTemporalCrystalResonator:
    """
    Temporal crystal resonator that models game time as a crystalline
    medium through which events propagate as phonon vibrations.

    Thread-safe singleton. Use get_instance() to obtain the global instance.
    """

    _instance: Optional["EngineTemporalCrystalResonator"] = None
    _instance_lock = threading.Lock()

    # Configuration constants
    MAX_PHONONS = 200
    MAX_ZONES = 30
    MAX_FRACTURES = 100
    MAX_STANDING_WAVES = 50
    MAX_EVENTS = 500

    MIN_AMPLITUDE = 0.01
    MAX_AMPLITUDE = 1.0
    MIN_FREQUENCY = 0.1
    MAX_FREQUENCY = 10.0
    MIN_DAMPING = 0.0
    MAX_DAMPING = 0.5
    MIN_DENSITY = 0.1
    MAX_DENSITY = 1.0
    MIN_REFRACTIVE = 0.5
    MAX_REFRACTIVE = 3.0

    PROPAGATION_STEP = 0.05       # distance per cycle
    STANDING_WAVE_THRESHOLD = 0.7  # amplitude needed for standing wave
    FRACTURE_STRESS_THRESHOLD = 0.8  # stress needed to create fracture
    ANNEAL_AMPLITUDE_THRESHOLD = 0.6  # amplitude needed for annealing
    DAMPING_FLUSH_THRESHOLD = 0.02   # below this, phonon is absorbed

    def __init__(self) -> None:
        self._phonons: Dict[str, TemporalPhonon] = {}
        self._zones: Dict[str, LatticeZone] = {}
        self._fractures: Deque[LatticeFracture] = deque(maxlen=self.MAX_FRACTURES)
        self._standing_waves: Deque[StandingWave] = deque(maxlen=self.MAX_STANDING_WAVES)
        self._event_history: Deque[Dict[str, Any]] = deque(maxlen=self.MAX_EVENTS)
        self._phonon_counter: int = 0
        self._fracture_counter: int = 0
        self._wave_counter: int = 0
        self._lattice_energy: float = 0.0
        self._stats = TemporalStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineTemporalCrystalResonator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Phonon Management
    # -------------------------------------------------------------------------

    def register_phonon(
        self,
        phonon_id: str,
        label: str,
        lattice_type: str = "chrono",
        frequency: Optional[float] = None,
        amplitude: Optional[float] = None,
        axis: Optional[List[float]] = None,
        position: Optional[List[float]] = None,
        damping_rate: Optional[float] = None,
        refractive_index: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a new temporal phonon in the crystal lattice."""
        with self._lock:
            if phonon_id in self._phonons:
                return {"error": f"Phonon already exists: {phonon_id}"}
            if len(self._phonons) >= self.MAX_PHONONS:
                return {"error": "Lattice at maximum phonon capacity"}

            try:
                ltype = LatticeType(lattice_type)
            except ValueError:
                return {"error": f"Unknown lattice type: {lattice_type}"}

            if frequency is None:
                frequency = random.uniform(1.0, 5.0)
            frequency = max(self.MIN_FREQUENCY, min(self.MAX_FREQUENCY, float(frequency)))

            if amplitude is None:
                amplitude = 0.6
            amplitude = max(self.MIN_AMPLITUDE, min(self.MAX_AMPLITUDE, float(amplitude)))

            if axis is None:
                angle = random.uniform(0.0, 2.0 * math.pi)
                axis = [math.cos(angle), math.sin(angle)]
            else:
                if len(axis) != 2:
                    return {"error": "axis must have exactly 2 elements"}
                mag = math.sqrt(axis[0] ** 2 + axis[1] ** 2)
                if mag < 1e-6:
                    return {"error": "axis vector cannot be zero"}
                axis = [axis[0] / mag, axis[1] / mag]

            if position is None:
                position = [random.random(), random.random()]
            else:
                if len(position) != 2:
                    return {"error": "position must have exactly 2 elements"}
                position = [
                    max(0.0, min(1.0, float(position[0]))),
                    max(0.0, min(1.0, float(position[1]))),
                ]

            if damping_rate is None:
                damping_rate = DEFAULT_LATTICE_DAMPING.get(ltype, 0.05)
            damping_rate = max(self.MIN_DAMPING, min(self.MAX_DAMPING, float(damping_rate)))

            if refractive_index is None:
                refractive_index = DEFAULT_LATTICE_REFRACTIVE_INDEX.get(ltype, 1.0)
            refractive_index = max(self.MIN_REFRACTIVE, min(self.MAX_REFRACTIVE, float(refractive_index)))

            phonon = TemporalPhonon(
                phonon_id=phonon_id,
                label=label,
                lattice_type=ltype,
                frequency=frequency,
                amplitude=amplitude,
                axis=(axis[0], axis[1]),
                position=(position[0], position[1]),
                damping_rate=damping_rate,
                refractive_index=refractive_index,
            )
            self._phonons[phonon_id] = phonon
            self._lattice_energy += amplitude
            self._stats.total_phonons = len(self._phonons)

            self._record_event(
                TemporalEvent.PHONON_BORN,
                intensity=amplitude,
                phonon_ids=[phonon_id],
                description=f"Phonon '{label}' ({ltype.value}) born in lattice",
            )
            return self._phonon_to_dict(phonon)

    def get_phonon(self, phonon_id: str) -> Dict[str, Any]:
        """Get the state of a specific temporal phonon."""
        with self._lock:
            phonon = self._phonons.get(phonon_id)
            if phonon is None:
                return {"error": f"Phonon not found: {phonon_id}"}
            return self._phonon_to_dict(phonon)

    def list_phonons(
        self, lattice_type: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """List phonons, optionally filtered by lattice type."""
        with self._lock:
            phonons = list(self._phonons.values())
            if lattice_type:
                try:
                    ltype = LatticeType(lattice_type)
                    phonons = [p for p in phonons if p.lattice_type == ltype]
                except ValueError:
                    return []
            phonons = phonons[:limit]
            return [self._phonon_to_dict(p) for p in phonons]

    def remove_phonon(self, phonon_id: str) -> Dict[str, Any]:
        """Remove a phonon from the lattice."""
        with self._lock:
            if phonon_id not in self._phonons:
                return {"removed": False, "phonon_id": phonon_id}
            phonon = self._phonons[phonon_id]
            self._lattice_energy = max(0.0, self._lattice_energy - phonon.amplitude)
            del self._phonons[phonon_id]
            self._stats.total_phonons = len(self._phonons)
            return {"removed": True, "phonon_id": phonon_id}

    def set_phonon_amplitude(
        self, phonon_id: str, amplitude: float, description: str = ""
    ) -> Dict[str, Any]:
        """Set the amplitude of a temporal phonon."""
        with self._lock:
            phonon = self._phonons.get(phonon_id)
            if phonon is None:
                return {"error": f"Phonon not found: {phonon_id}"}
            old_amp = phonon.amplitude
            phonon.amplitude = max(self.MIN_AMPLITUDE, min(self.MAX_AMPLITUDE, float(amplitude)))
            self._lattice_energy += phonon.amplitude - old_amp
            return {
                "phonon_id": phonon_id,
                "amplitude": round(phonon.amplitude, 4),
                "description": description,
            }

    def set_phonon_axis(
        self, phonon_id: str, axis: List[float], description: str = ""
    ) -> Dict[str, Any]:
        """Set the propagation axis of a temporal phonon."""
        with self._lock:
            phonon = self._phonons.get(phonon_id)
            if phonon is None:
                return {"error": f"Phonon not found: {phonon_id}"}
            if len(axis) != 2:
                return {"error": "axis must have exactly 2 elements"}
            mag = math.sqrt(axis[0] ** 2 + axis[1] ** 2)
            if mag < 1e-6:
                return {"error": "axis vector cannot be zero"}
            phonon.axis = (axis[0] / mag, axis[1] / mag)
            return {
                "phonon_id": phonon_id,
                "axis": [round(phonon.axis[0], 4), round(phonon.axis[1], 4)],
                "description": description,
            }

    # -------------------------------------------------------------------------
    # Zone Management
    # -------------------------------------------------------------------------

    def register_zone(
        self,
        zone_id: str,
        label: str,
        lattice_type: str = "chrono",
        center: Optional[List[float]] = None,
        radius: float = 0.2,
        density: Optional[float] = None,
        refractive_index: Optional[float] = None,
        stress_tolerance: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a temporal lattice zone."""
        with self._lock:
            if zone_id in self._zones:
                return {"error": f"Zone already exists: {zone_id}"}
            if len(self._zones) >= self.MAX_ZONES:
                return {"error": "Maximum zone count reached"}

            try:
                ltype = LatticeType(lattice_type)
            except ValueError:
                return {"error": f"Unknown lattice type: {lattice_type}"}

            if center is None:
                center = [random.random(), random.random()]
            else:
                if len(center) != 2:
                    return {"error": "center must have exactly 2 elements"}
                center = [
                    max(0.0, min(1.0, float(center[0]))),
                    max(0.0, min(1.0, float(center[1]))),
                ]
            radius = max(0.05, min(0.5, float(radius)))

            if density is None:
                density = DEFAULT_LATTICE_DENSITY.get(ltype, 0.7)
            density = max(self.MIN_DENSITY, min(self.MAX_DENSITY, float(density)))

            if refractive_index is None:
                refractive_index = DEFAULT_LATTICE_REFRACTIVE_INDEX.get(ltype, 1.0)
            refractive_index = max(self.MIN_REFRACTIVE, min(self.MAX_REFRACTIVE, float(refractive_index)))

            if stress_tolerance is None:
                stress_tolerance = DEFAULT_LATTICE_STRESS_TOLERANCE.get(ltype, 0.8)
            stress_tolerance = max(0.1, min(1.0, float(stress_tolerance)))

            zone = LatticeZone(
                zone_id=zone_id,
                label=label,
                lattice_type=ltype,
                center=(center[0], center[1]),
                radius=radius,
                density=density,
                refractive_index=refractive_index,
                stress_tolerance=stress_tolerance,
            )
            self._zones[zone_id] = zone
            self._stats.total_zones = len(self._zones)
            return self._zone_to_dict(zone)

    def list_zones(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List all temporal lattice zones."""
        with self._lock:
            return [self._zone_to_dict(z) for z in list(self._zones.values())[:limit]]

    def get_zone(self, zone_id: str) -> Dict[str, Any]:
        """Get a specific lattice zone."""
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return {"error": f"Zone not found: {zone_id}"}
            return self._zone_to_dict(zone)

    def remove_zone(self, zone_id: str) -> Dict[str, Any]:
        """Remove a temporal lattice zone."""
        with self._lock:
            if zone_id not in self._zones:
                return {"removed": False, "zone_id": zone_id}
            del self._zones[zone_id]
            self._stats.total_zones = len(self._zones)
            return {"removed": True, "zone_id": zone_id}

    # -------------------------------------------------------------------------
    # Fractures
    # -------------------------------------------------------------------------

    def list_fractures(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List lattice fractures."""
        with self._lock:
            return [self._fracture_to_dict(f) for f in list(self._fractures)[:limit]]

    def get_fracture(self, fracture_id: str) -> Dict[str, Any]:
        """Get a specific fracture."""
        with self._lock:
            for f in self._fractures:
                if f.fracture_id == fracture_id:
                    return self._fracture_to_dict(f)
            return {"error": f"Fracture not found: {fracture_id}"}

    # -------------------------------------------------------------------------
    # Standing Waves
    # -------------------------------------------------------------------------

    def list_standing_waves(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List standing wave patterns."""
        with self._lock:
            return [self._wave_to_dict(w) for w in list(self._standing_waves)[:limit]]

    def get_standing_wave(self, wave_id: str) -> Dict[str, Any]:
        """Get a specific standing wave."""
        with self._lock:
            for w in self._standing_waves:
                if w.wave_id == wave_id:
                    return self._wave_to_dict(w)
            return {"error": f"Standing wave not found: {wave_id}"}

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run one temporal crystal cycle."""
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: VIBRATE - phonons oscillate and accumulate energy
            vibrate_info = self._vibrate_phase()

            # Phase 2: PROPAGATE - phonons travel along their axes
            propagate_info = self._propagate_phase()

            # Phase 3: REFRACT - phonons refract at zone boundaries
            refract_info = self._refract_phase()

            # Phase 4: DAMP - phonons dampen over distance
            damp_info = self._damp_phase()

            # Phase 5: ANNEAL - stable vibrations lock into the lattice
            anneal_info = self._anneal_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            phase = TemporalPhase.ANNEAL
            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "vibrate": vibrate_info,
                "propagate": propagate_info,
                "refract": refract_info,
                "damp": damp_info,
                "anneal": anneal_info,
                "total_phonons": len(self._phonons),
                "total_zones": len(self._zones),
                "total_fractures": len(self._fractures),
                "total_standing_waves": len(self._standing_waves),
                "lattice_energy": round(self._lattice_energy, 4),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _vibrate_phase(self) -> Dict[str, Any]:
        """Phase 1: Phonons oscillate and accumulate stress over time."""
        vibrated = 0
        for phonon in self._phonons.values():
            phonon.age_cycles += 1
            if phonon.annealed:
                continue
            # Phonons with high frequency accumulate stress faster
            stress_gain = (phonon.frequency / self.MAX_FREQUENCY) * 0.05 * phonon.amplitude
            phonon.stress = min(1.0, phonon.stress + stress_gain)
            vibrated += 1
        self._stats.total_phonon_born += vibrated
        return {
            "phonons_vibrated": vibrated,
            "total_phonons": len(self._phonons),
        }

    def _propagate_phase(self) -> Dict[str, Any]:
        """Phase 2: Phonons travel along their propagation axes."""
        propagated = 0
        for phonon in self._phonons.values():
            if phonon.annealed:
                continue
            # Move along axis, with density affecting speed
            zone = self._find_zone_at(phonon.position)
            density = zone.density if zone else 0.7
            step = self.PROPAGATION_STEP * (1.0 - density * 0.5)
            new_x = phonon.position[0] + phonon.axis[0] * step
            new_y = phonon.position[1] + phonon.axis[1] * step
            # Wrap around lattice boundaries (toroidal topology)
            new_x = new_x % 1.0
            new_y = new_y % 1.0
            phonon.position = (new_x, new_y)
            propagated += 1

        if propagated > 0:
            self._record_event(
                TemporalEvent.PROPAGATION,
                intensity=0.5,
                phonon_ids=[],
                description=f"{propagated} phonons propagated along lattice axes",
            )
        self._stats.total_propagations += propagated
        return {
            "phonons_propagated": propagated,
        }

    def _refract_phase(self) -> Dict[str, Any]:
        """Phase 3: Phonons refract when crossing zone boundaries."""
        refractions = 0
        standing_waves_formed = 0
        for phonon in list(self._phonons.values()):
            if phonon.annealed:
                continue
            zone = self._find_zone_at(phonon.position)
            if zone is None:
                continue
            # Refraction: adjust axis based on zone's refractive index
            if zone.refractive_index != phonon.refractive_index:
                # Snell-like refraction (simplified)
                ratio = phonon.refractive_index / max(zone.refractive_index, 0.01)
                # Rotate axis slightly based on refractive difference
                angle_shift = (ratio - 1.0) * 0.3
                cos_a = math.cos(angle_shift)
                sin_a = math.sin(angle_shift)
                new_x = phonon.axis[0] * cos_a - phonon.axis[1] * sin_a
                new_y = phonon.axis[0] * sin_a + phonon.axis[1] * cos_a
                phonon.axis = (new_x, new_y)
                phonon.refractive_index = zone.refractive_index
                refractions += 1

            # Standing wave formation in cyclic/resonant zones
            if (
                zone.lattice_type in (LatticeType.CYCLIC, LatticeType.RESONANT)
                and not phonon.standing_wave
                and phonon.amplitude >= self.STANDING_WAVE_THRESHOLD
            ):
                phonon.standing_wave = True
                self._wave_counter += 1
                wave = StandingWave(
                    wave_id=f"wave_{self._wave_counter}",
                    phonon_id=phonon.phonon_id,
                    zone_id=zone.zone_id,
                    frequency=phonon.frequency,
                    amplitude=phonon.amplitude,
                )
                self._standing_waves.append(wave)
                standing_waves_formed += 1
                self._record_event(
                    TemporalEvent.STANDING_WAVE,
                    intensity=phonon.amplitude,
                    phonon_ids=[phonon.phonon_id],
                    description=f"Standing wave formed from '{phonon.label}' in zone '{zone.label}'",
                )

        if refractions > 0:
            self._record_event(
                TemporalEvent.REFRACTION,
                intensity=0.3,
                phonon_ids=[],
                description=f"{refractions} phonons refracted at zone boundaries",
            )
        self._stats.total_refractions += refractions
        self._stats.total_standing_waves_formed += standing_waves_formed
        self._stats.total_standing_waves = len(self._standing_waves)
        return {
            "refractions": refractions,
            "standing_waves_formed": standing_waves_formed,
            "total_standing_waves": len(self._standing_waves),
        }

    def _damp_phase(self) -> Dict[str, Any]:
        """Phase 4: Phonons dampen and may create fractures from stress."""
        damped = 0
        flushed = 0
        fractures_created = 0
        to_remove: List[str] = []
        energy_lost = 0.0
        for phonon in self._phonons.values():
            if phonon.annealed:
                continue
            # Dampen amplitude
            old_amp = phonon.amplitude
            phonon.amplitude = max(
                self.MIN_AMPLITUDE,
                phonon.amplitude - phonon.damping_rate * (1.0 - phonon.amplitude * 0.3),
            )
            energy_lost += old_amp - phonon.amplitude
            damped += 1

            # Stress-induced fractures
            zone = self._find_zone_at(phonon.position)
            if zone and phonon.stress >= self.FRACTURE_STRESS_THRESHOLD:
                if random.random() < 0.3:  # not every stressed phonon fractures
                    self._fracture_counter += 1
                    fracture = LatticeFracture(
                        fracture_id=f"frac_{self._fracture_counter}",
                        zone_id=zone.zone_id,
                        position=phonon.position,
                        severity=round(min(1.0, phonon.stress), 4),
                    )
                    self._fractures.append(fracture)
                    zone.fracture_count += 1
                    fractures_created += 1
                    # Stress is released by the fracture
                    phonon.stress *= 0.3
                    self._record_event(
                        TemporalEvent.MICRO_FRACTURE,
                        intensity=fracture.severity,
                        phonon_ids=[phonon.phonon_id],
                        description=f"Micro-fracture in zone '{zone.label}' from phonon '{phonon.label}'",
                    )

            # Flush phonons that have dampened below threshold
            if phonon.amplitude <= self.DAMPING_FLUSH_THRESHOLD:
                to_remove.append(phonon.phonon_id)
                flushed += 1

        for pid in to_remove:
            self.remove_phonon(pid)

        if damped > 0:
            self._record_event(
                TemporalEvent.DAMPING,
                intensity=0.2,
                phonon_ids=[],
                description=f"{damped} phonons dampened, {flushed} absorbed",
            )
        self._lattice_energy = max(0.0, self._lattice_energy - energy_lost)
        self._stats.total_dampings += damped
        self._stats.total_fractures_formed += fractures_created
        self._stats.total_fractures = len(self._fractures)
        return {
            "damped": damped,
            "flushed": flushed,
            "fractures_created": fractures_created,
            "energy_lost": round(energy_lost, 4),
        }

    def _anneal_phase(self) -> Dict[str, Any]:
        """Phase 5: Stable vibrations anneal into the permanent lattice."""
        annealed = 0
        fractures_healed = 0
        # Anneal high-amplitude, low-stress phonons
        for phonon in self._phonons.values():
            if phonon.annealed:
                continue
            if (
                phonon.amplitude >= self.ANNEAL_AMPLITUDE_THRESHOLD
                and phonon.stress < 0.4
            ):
                phonon.annealed = True
                annealed += 1
                self._record_event(
                    TemporalEvent.ANNEAL_LOCK,
                    intensity=phonon.amplitude,
                    phonon_ids=[phonon.phonon_id],
                    description=f"Phonon '{phonon.label}' annealed into permanent lattice",
                )

        # Heal low-severity fractures
        to_heal: List[str] = []
        for fracture in self._fractures:
            if not fracture.healed and fracture.severity < 0.3:
                fracture.healed = True
                fractures_healed += 1
                to_heal.append(fracture.fracture_id)
        # Remove healed fractures
        self._fractures = deque(
            (f for f in self._fractures if not f.healed),
            maxlen=self.MAX_FRACTURES,
        )

        self._stats.total_anneal_locks += annealed
        self._stats.total_fractures = len(self._fractures)
        return {
            "annealed": annealed,
            "fractures_healed": fractures_healed,
            "total_fractures": len(self._fractures),
        }

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
        """Get the overall status of the temporal crystal resonator."""
        with self._lock:
            self._stats.total_phonons = len(self._phonons)
            self._stats.total_zones = len(self._zones)
            self._stats.total_fractures = len(self._fractures)
            self._stats.total_standing_waves = len(self._standing_waves)
            self._stats.total_events = len(self._event_history)
            self._update_avg_metrics()
            return {
                "total_phonons": self._stats.total_phonons,
                "total_zones": self._stats.total_zones,
                "total_fractures": self._stats.total_fractures,
                "total_standing_waves": self._stats.total_standing_waves,
                "lattice_energy": round(self._lattice_energy, 4),
                "active": self._active,
                "cycle_count": self._cycle_count,
                "stats": {
                    "total_events": self._stats.total_events,
                    "total_phonon_born": self._stats.total_phonon_born,
                    "total_propagations": self._stats.total_propagations,
                    "total_refractions": self._stats.total_refractions,
                    "total_standing_waves_formed": self._stats.total_standing_waves_formed,
                    "total_dampings": self._stats.total_dampings,
                    "total_fractures_formed": self._stats.total_fractures_formed,
                    "total_anneal_locks": self._stats.total_anneal_locks,
                    "avg_amplitude": round(self._stats.avg_amplitude, 4),
                    "avg_stress": round(self._stats.avg_stress, 4),
                    "last_cycle_time_ms": self._stats.last_cycle_time_ms,
                },
            }

    def get_events(
        self, lattice_type: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent temporal events."""
        with self._lock:
            events = list(self._event_history)
            if lattice_type:
                events = [e for e in events if e.get("lattice_type") == lattice_type]
            return events[:limit]

    def reset(self) -> Dict[str, Any]:
        """Reset the temporal crystal resonator to its initial state."""
        with self._lock:
            self._phonons.clear()
            self._zones.clear()
            self._fractures.clear()
            self._standing_waves.clear()
            self._event_history.clear()
            self._phonon_counter = 0
            self._fracture_counter = 0
            self._wave_counter = 0
            self._lattice_energy = 0.0
            self._stats = TemporalStats()
            self._cycle_count = 0
            self._active = False
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _find_zone_at(self, position: Tuple[float, float]) -> Optional[LatticeZone]:
        """Find the zone containing the given position, if any."""
        for zone in self._zones.values():
            dx = position[0] - zone.center[0]
            dy = position[1] - zone.center[1]
            if math.sqrt(dx * dx + dy * dy) <= zone.radius:
                return zone
        return None

    def _record_event(
        self,
        event: TemporalEvent,
        intensity: float,
        phonon_ids: List[str],
        description: str,
    ) -> None:
        """Record a temporal event in the history."""
        self._event_history.append({
            "event_id": f"evt_{len(self._event_history) + 1}",
            "event_type": event.value,
            "intensity": round(intensity, 4),
            "phonon_ids": phonon_ids,
            "description": description,
            "timestamp": time.time(),
        })

    def _update_avg_metrics(self) -> None:
        """Update average metrics from current phonons."""
        if not self._phonons:
            self._stats.avg_amplitude = 0.0
            self._stats.avg_stress = 0.0
            return
        n = len(self._phonons)
        self._stats.avg_amplitude = sum(p.amplitude for p in self._phonons.values()) / n
        self._stats.avg_stress = sum(p.stress for p in self._phonons.values()) / n

    def _phonon_to_dict(self, p: TemporalPhonon) -> Dict[str, Any]:
        """Convert a phonon to a dictionary representation."""
        return {
            "phonon_id": p.phonon_id,
            "label": p.label,
            "lattice_type": p.lattice_type.value,
            "frequency": round(p.frequency, 4),
            "amplitude": round(p.amplitude, 4),
            "axis": [round(p.axis[0], 4), round(p.axis[1], 4)],
            "position": [round(p.position[0], 4), round(p.position[1], 4)],
            "damping_rate": round(p.damping_rate, 4),
            "refractive_index": round(p.refractive_index, 4),
            "stress": round(p.stress, 4),
            "annealed": p.annealed,
            "standing_wave": p.standing_wave,
            "age_cycles": p.age_cycles,
            "timestamp": p.timestamp,
        }

    def _zone_to_dict(self, z: LatticeZone) -> Dict[str, Any]:
        """Convert a zone to a dictionary representation."""
        return {
            "zone_id": z.zone_id,
            "label": z.label,
            "lattice_type": z.lattice_type.value,
            "center": [round(z.center[0], 4), round(z.center[1], 4)],
            "radius": round(z.radius, 4),
            "density": round(z.density, 4),
            "refractive_index": round(z.refractive_index, 4),
            "stress_tolerance": round(z.stress_tolerance, 4),
            "fracture_count": z.fracture_count,
            "timestamp": z.timestamp,
        }

    def _fracture_to_dict(self, f: LatticeFracture) -> Dict[str, Any]:
        """Convert a fracture to a dictionary representation."""
        return {
            "fracture_id": f.fracture_id,
            "zone_id": f.zone_id,
            "position": [round(f.position[0], 4), round(f.position[1], 4)],
            "severity": f.severity,
            "healed": f.healed,
            "timestamp": f.timestamp,
        }

    def _wave_to_dict(self, w: StandingWave) -> Dict[str, Any]:
        """Convert a standing wave to a dictionary representation."""
        return {
            "wave_id": w.wave_id,
            "phonon_id": w.phonon_id,
            "zone_id": w.zone_id,
            "frequency": round(w.frequency, 4),
            "amplitude": round(w.amplitude, 4),
            "persistence": w.persistence,
            "timestamp": w.timestamp,
        }
