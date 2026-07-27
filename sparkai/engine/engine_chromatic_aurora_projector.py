"""
SparkLabs Engine - Chromatic Aurora Projector

The EngineChromaticAuroraProjector models atmospheric lighting and sky
color as aurora borealis phenomena. Rather than treating lighting as
static color values, it treats the sky as a plasma of charged particles
drifting along magnetic field lines, colliding with atmospheric
molecules, and emitting photons at characteristic wavelengths.

This aurora metaphor captures how atmospheric lighting actually feels in
living game worlds: colors do not switch, they shimmer and drift. A
sunset does not end, it dissolves into twilight. A storm does not darken
the sky uniformly, it creates curtains of shadow and shafts of light.
Two color zones near each other do not blend linearly, they interfere
like aurora curtains creating shimmering boundaries.

Core concepts:
  - EXCITATION  : energy level of a color zone (0.0-1.0)
  - HUE         : dominant wavelength of emitted light (0-360 degrees)
  - SATURATION  : purity of the color (0.0-1.0)
  - LUMINANCE   : brightness of the emitted light (0.0-1.0)
  - FIELD LINE  : magnetic connection between two zones guiding particles
  - CURTAIN     : organized particle flow creating a visible aurora band
  - SHIMMER     : rapid oscillation of color at a zone boundary

Color zone types:
  TWILIGHT : warm oranges/purples, low excitation
  ZENITH   : deep blues/violets, medium excitation
  HORIZON  : gold/amber, variable excitation
  NADIR    : dark teal/indigo, low excitation
  CORONA   : shifting rainbow, high excitation
  VOID     : near-black, minimal excitation

Particle types:
  PHOTON       : light emission particle
  CHROMOPHORE  : color carrier particle
  SCINTILLATOR : sparkle-effect particle
  DRIFTER      : slow ambient particle

Aurora events:
  CURTAIN_FORM    : organized flow creates an aurora curtain
  CORONA_BURST    : rainbow corona appears
  SHIMMER         : rapid color oscillation at a boundary
  DISSIPATION     : aurora fades
  RESONANCE_GLOW  : multiple zones synchronize colors
  BLACKOUT        : zone goes dark

Architecture:
  EXCITE  ->  DRIFT   ->  COLLIDE  ->  EMIT     ->  DISSIPATE
  (particles  (particles  (particles   (organized   (energy
   gain       move along  interact    light         decays,
   energy     field       with        emission      aurora
   from       lines       atmosphere, creates       fades)
   magnetic   between     emitting    aurora
   field)     zones)      color)      patterns)

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

class ColorZoneType(Enum):
    """Types of color zones in the atmospheric lighting field."""
    TWILIGHT = "twilight"    # warm oranges/purples
    ZENITH = "zenith"        # deep blues/violets
    HORIZON = "horizon"      # gold/amber
    NADIR = "nadir"          # dark teal/indigo
    CORONA = "corona"        # shifting rainbow
    VOID = "void"            # near-black


class AuroraPhase(Enum):
    """Phases of the aurora projection cycle."""
    EXCITE = "excite"
    DRIFT = "drift"
    COLLIDE = "collide"
    EMIT = "emit"
    DISSIPATE = "dissipate"


class ParticleType(Enum):
    """Types of charged particles in the aurora field."""
    PHOTON = "photon"            # light emission
    CHROMOPHORE = "chromophore"  # color carrier
    SCINTILLATOR = "scintillator"  # sparkle effect
    DRIFTER = "drifter"          # slow ambient


class AuroraEvent(Enum):
    """Events that occur during the aurora cycle."""
    CURTAIN_FORM = "curtain_form"      # organized flow creates curtain
    CORONA_BURST = "corona_burst"      # rainbow corona appears
    SHIMMER = "shimmer"                # rapid color oscillation
    DISSIPATION = "dissipation"        # aurora fades
    RESONANCE_GLOW = "resonance_glow"  # zones synchronize
    BLACKOUT = "blackout"              # zone goes dark


# =============================================================================
# Default Parameters by Zone Type
# =============================================================================

# Default hue (degrees) for each color zone type
DEFAULT_ZONE_HUE: Dict[ColorZoneType, float] = {
    ColorZoneType.TWILIGHT: 25.0,    # warm orange
    ColorZoneType.ZENITH: 240.0,     # deep blue
    ColorZoneType.HORIZON: 45.0,     # gold/amber
    ColorZoneType.NADIR: 200.0,      # dark teal
    ColorZoneType.CORONA: 180.0,     # cyan (shifting)
    ColorZoneType.VOID: 270.0,       # near-black indigo
}

# Default saturation for each zone type
DEFAULT_ZONE_SATURATION: Dict[ColorZoneType, float] = {
    ColorZoneType.TWILIGHT: 0.7,
    ColorZoneType.ZENITH: 0.8,
    ColorZoneType.HORIZON: 0.85,
    ColorZoneType.NADIR: 0.5,
    ColorZoneType.CORONA: 0.9,
    ColorZoneType.VOID: 0.2,
}

# Default luminance for each zone type
DEFAULT_ZONE_LUMINANCE: Dict[ColorZoneType, float] = {
    ColorZoneType.TWILIGHT: 0.4,
    ColorZoneType.ZENITH: 0.3,
    ColorZoneType.HORIZON: 0.6,
    ColorZoneType.NADIR: 0.15,
    ColorZoneType.CORONA: 0.7,
    ColorZoneType.VOID: 0.05,
}

# Default excitation for each zone type
DEFAULT_ZONE_EXCITATION: Dict[ColorZoneType, float] = {
    ColorZoneType.TWILIGHT: 0.3,
    ColorZoneType.ZENITH: 0.5,
    ColorZoneType.HORIZON: 0.6,
    ColorZoneType.NADIR: 0.2,
    ColorZoneType.CORONA: 0.9,
    ColorZoneType.VOID: 0.05,
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class ColorZone:
    """A region of the atmospheric lighting field with its own color state."""
    zone_id: str
    label: str
    zone_type: ColorZoneType
    # Current excitation level (0.0-1.0)
    excitation: float
    # Target excitation the zone is moving toward
    target_excitation: float
    # Dominant hue in degrees (0-360)
    hue: float
    # Target hue for smooth transitions
    target_hue: float
    # Color saturation (0.0-1.0)
    saturation: float
    # Color luminance / brightness (0.0-1.0)
    luminance: float
    # How much the hue shifts per cycle (degrees)
    hue_drift_rate: float
    # Whether this zone is actively emitting
    emitting: bool = True
    last_updated: float = field(default_factory=time.time)


@dataclass
class ChargedParticle:
    """A charged particle drifting through the aurora field."""
    particle_id: str
    particle_type: ParticleType
    # Current energy level (0.0-1.0)
    energy: float
    # Source zone where the particle originated
    source_zone_id: str
    # Target zone the particle is drifting toward
    target_zone_id: str
    # Hue the particle carries (degrees)
    hue: float
    # Drift progress from source to target (0.0-1.0)
    progress: float
    # Drift speed per cycle
    drift_speed: float
    # Whether the particle is still active
    active: bool = True
    timestamp: float = field(default_factory=time.time)


@dataclass
class MagneticLine:
    """A magnetic field line connecting two color zones."""
    source_id: str
    target_id: str
    # Field strength (0.0-1.0)
    field_strength: float
    # Polarity: True = attractive, False = repulsive
    polarity: bool = True


@dataclass
class AuroraCurtain:
    """An organized aurora curtain formed by particle flow."""
    curtain_id: str
    # Zones the curtain spans
    zone_ids: List[str]
    # Range of hues in the curtain
    hue_min: float
    hue_max: float
    # Intensity of the curtain (0.0-1.0)
    intensity: float
    # Drift direction in degrees
    drift_direction: float
    # How long the curtain has existed
    age_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AuroraStats:
    """Aggregate statistics for the aurora projector."""
    total_zones: int = 0
    total_particles: int = 0
    total_curtains: int = 0
    total_events: int = 0
    total_curtain_forms: int = 0
    total_corona_bursts: int = 0
    total_shimmers: int = 0
    total_blackouts: int = 0
    total_resonance_glows: int = 0
    avg_excitation: float = 0.0
    avg_luminance: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Engine Chromatic Aurora Projector
# =============================================================================

class EngineChromaticAuroraProjector:
    """
    Singleton engine subsystem that models atmospheric lighting as aurora
    phenomena driven by charged particles in a magnetic field.

    The projector runs a 5-phase cycle:
      1. EXCITE     - Particles gain energy from the magnetic field
      2. DRIFT      - Particles move along field lines between zones
      3. COLLIDE    - Particles interact with the atmosphere, emitting color
      4. EMIT       - Organized light emission creates aurora patterns
      5. DISSIPATE  - Energy decays and aurora curtains fade

    The aurora metaphor ensures atmospheric lighting feels alive: colors
    drift and shimmer rather than holding static values, and transitions
    between lighting states unfold as flowing curtains of light.
    """

    _instance: Optional["EngineChromaticAuroraProjector"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_ZONES = 80
    MAX_PARTICLES = 400
    MAX_CURTAINS = 50
    MAX_EVENT_HISTORY = 200
    MAX_FIELD_LINES_PER_ZONE = 8
    # Minimum excitation
    MIN_EXCITATION = 0.0
    # Maximum excitation
    MAX_EXCITATION = 1.0
    # How fast excitation moves toward target
    EXCITATION_ADJUSTMENT_RATE = 0.12
    # Natural excitation decay per cycle
    NATURAL_EXCITATION_DECAY = 0.04
    # How fast hue moves toward target
    HUE_ADJUSTMENT_RATE = 0.1
    # Minimum particle energy
    MIN_ENERGY = 0.0
    # Maximum particle energy
    MAX_ENERGY = 1.0
    # Particle energy decay per cycle
    PARTICLE_ENERGY_DECAY = 0.06
    # Minimum energy for a particle to remain active
    MIN_PARTICLE_ENERGY = 0.02
    # Probability of spontaneous particle emission per zone per cycle
    EMISSION_PROBABILITY = 0.25
    # Curtain formation threshold (minimum particle flow)
    CURTAIN_FORM_THRESHOLD = 3
    # Corona burst excitation threshold
    CORONA_BURST_THRESHOLD = 0.85
    # Shimmer threshold (hue difference at boundary)
    SHIMMER_THRESHOLD = 60.0
    # Blackout threshold (excitation below this)
    BLACKOUT_THRESHOLD = 0.05
    # Resonance glow threshold (hue similarity)
    RESONANCE_HUE_THRESHOLD = 15.0

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._zones: Dict[str, ColorZone] = {}
        self._particles: Deque[ChargedParticle] = deque(maxlen=self.MAX_PARTICLES)
        self._field_lines: Dict[str, List[MagneticLine]] = {}
        self._curtains: Deque[AuroraCurtain] = deque(maxlen=self.MAX_CURTAINS)
        self._event_history: Deque[Dict[str, Any]] = deque(
            maxlen=self.MAX_EVENT_HISTORY
        )
        self._stats = AuroraStats()
        self._cycle_count: int = 0
        self._active: bool = False

    @classmethod
    def get_instance(cls) -> "EngineChromaticAuroraProjector":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Color Zone Management
    # -------------------------------------------------------------------------

    def register_zone(
        self,
        zone_id: str,
        label: str,
        zone_type: str = "twilight",
        excitation: Optional[float] = None,
        hue: Optional[float] = None,
        saturation: Optional[float] = None,
        luminance: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a new color zone in the aurora field."""
        with self._lock:
            if zone_id in self._zones:
                return {"error": f"Zone already registered: {zone_id}"}
            if len(self._zones) >= self.MAX_ZONES:
                return {"error": "Maximum zones reached"}

            try:
                ztype = ColorZoneType(zone_type)
            except ValueError:
                return {"error": f"Unknown zone type: {zone_type}"}

            # Apply defaults if not provided
            if excitation is None:
                excitation = DEFAULT_ZONE_EXCITATION.get(ztype, 0.3)
            excitation = max(self.MIN_EXCITATION, min(self.MAX_EXCITATION, float(excitation)))

            if hue is None:
                hue = DEFAULT_ZONE_HUE.get(ztype, 180.0)
            hue = float(hue) % 360.0

            if saturation is None:
                saturation = DEFAULT_ZONE_SATURATION.get(ztype, 0.7)
            saturation = max(0.0, min(1.0, float(saturation)))

            if luminance is None:
                luminance = DEFAULT_ZONE_LUMINANCE.get(ztype, 0.4)
            luminance = max(0.0, min(1.0, float(luminance)))

            zone = ColorZone(
                zone_id=zone_id,
                label=label,
                zone_type=ztype,
                excitation=excitation,
                target_excitation=excitation,
                hue=hue,
                target_hue=hue,
                saturation=saturation,
                luminance=luminance,
                hue_drift_rate=random.uniform(-2.0, 2.0),
            )
            self._zones[zone_id] = zone
            self._field_lines[zone_id] = []
            self._stats.total_zones = len(self._zones)
            return self._zone_to_dict(zone)

    def get_zone(self, zone_id: str) -> Dict[str, Any]:
        """Get the state of a color zone."""
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return {"error": f"Zone not found: {zone_id}"}
            return self._zone_to_dict(zone)

    def list_zones(self) -> List[Dict[str, Any]]:
        """List all color zones."""
        with self._lock:
            return [self._zone_to_dict(z) for z in self._zones.values()]

    def remove_zone(self, zone_id: str) -> Dict[str, Any]:
        """Remove a color zone."""
        with self._lock:
            if zone_id not in self._zones:
                return {"removed": False}
            del self._zones[zone_id]
            # Remove field lines referencing this zone
            for zid, lines in self._field_lines.items():
                self._field_lines[zid] = [
                    l for l in lines if l.target_id != zone_id
                ]
            self._field_lines.pop(zone_id, None)
            self._stats.total_zones = len(self._zones)
            return {"removed": True, "zone_id": zone_id}

    def set_zone_excitation(
        self, zone_id: str, excitation: float, description: str = ""
    ) -> Dict[str, Any]:
        """Set the target excitation level for a zone."""
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return {"error": f"Zone not found: {zone_id}"}
            old_exc = zone.target_excitation
            new_exc = max(self.MIN_EXCITATION, min(self.MAX_EXCITATION, float(excitation)))
            zone.target_excitation = new_exc
            zone.last_updated = time.time()

            # Record event based on excitation change
            event_type: Optional[AuroraEvent] = None
            if new_exc < self.BLACKOUT_THRESHOLD:
                event_type = AuroraEvent.BLACKOUT
                self._stats.total_blackouts += 1
            elif new_exc >= self.CORONA_BURST_THRESHOLD and old_exc < self.CORONA_BURST_THRESHOLD:
                event_type = AuroraEvent.CORONA_BURST
                self._stats.total_corona_bursts += 1

            if event_type is not None:
                self._record_event(
                    event_type,
                    abs(new_exc - old_exc),
                    [zone_id],
                    description,
                )

            return self._zone_to_dict(zone)

    # -------------------------------------------------------------------------
    # Magnetic Field Line Management
    # -------------------------------------------------------------------------

    def link_zones(
        self, source_id: str, target_id: str,
        field_strength: float = 0.5, polarity: bool = True,
    ) -> Dict[str, Any]:
        """Create a magnetic field line between two zones."""
        with self._lock:
            if source_id not in self._zones:
                return {"error": f"Source zone not found: {source_id}"}
            if target_id not in self._zones:
                return {"error": f"Target zone not found: {target_id}"}
            if source_id == target_id:
                return {"error": "Cannot link zone to itself"}

            lines = self._field_lines.get(source_id, [])
            if len(lines) >= self.MAX_FIELD_LINES_PER_ZONE:
                return {"error": "Maximum field lines reached for source zone"}

            # Check if link already exists
            for line in lines:
                if line.target_id == target_id:
                    line.field_strength = max(0.0, min(1.0, field_strength))
                    line.polarity = polarity
                    return {"field_line": self._line_to_dict(line, source_id)}

            line = MagneticLine(
                source_id=source_id,
                target_id=target_id,
                field_strength=max(0.0, min(1.0, field_strength)),
                polarity=polarity,
            )
            lines.append(line)
            self._field_lines[source_id] = lines
            return {"field_line": self._line_to_dict(line, source_id)}

    def unlink_zones(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """Remove a magnetic field line between two zones."""
        with self._lock:
            lines = self._field_lines.get(source_id, [])
            original_len = len(lines)
            self._field_lines[source_id] = [
                l for l in lines if l.target_id != target_id
            ]
            removed = original_len - len(self._field_lines[source_id])
            return {"removed": removed, "source_id": source_id, "target_id": target_id}

    def get_field_lines(self, zone_id: str) -> Dict[str, Any]:
        """Get all magnetic field lines for a zone."""
        with self._lock:
            if zone_id not in self._zones:
                return {"error": f"Zone not found: {zone_id}"}
            lines = self._field_lines.get(zone_id, [])
            return {
                "zone_id": zone_id,
                "field_lines": [self._line_to_dict(l, zone_id) for l in lines],
                "total": len(lines),
            }

    # -------------------------------------------------------------------------
    # Particle Emission
    # -------------------------------------------------------------------------

    def emit_particle(
        self, zone_id: str, particle_type: str = "photon",
        energy: float = 0.5, target_zone_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Emit a charged particle from a zone."""
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return {"error": f"Zone not found: {zone_id}"}
            try:
                ptype = ParticleType(particle_type)
            except ValueError:
                return {"error": f"Unknown particle type: {particle_type}"}

            # Determine target zone
            if target_zone_id is None:
                lines = self._field_lines.get(zone_id, [])
                if lines:
                    line = random.choice(lines)
                    target_zone_id = line.target_id
                else:
                    return {"error": "No target zone and no field lines available"}
            if target_zone_id not in self._zones:
                return {"error": f"Target zone not found: {target_zone_id}"}

            en = max(self.MIN_ENERGY, min(self.MAX_ENERGY, float(energy)))
            particle = ChargedParticle(
                particle_id=f"part_{zone_id}_{ptype.value}_{int(time.time() * 1000)}_{random.randint(0, 999)}",
                particle_type=ptype,
                energy=en,
                source_zone_id=zone_id,
                target_zone_id=target_zone_id,
                hue=zone.hue,
                progress=0.0,
                drift_speed=random.uniform(0.1, 0.4),
            )
            self._particles.append(particle)
            self._stats.total_particles = len(self._particles)
            return self._particle_to_dict(particle)

    # -------------------------------------------------------------------------
    # Aurora Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single aurora projection cycle.

        Phases: EXCITE -> DRIFT -> COLLIDE -> EMIT -> DISSIPATE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: EXCITE - Particles gain energy from the magnetic field
            excite_info = self._excite_phase()

            # Phase 2: DRIFT - Particles move along field lines
            drift_info = self._drift_phase()

            # Phase 3: COLLIDE - Particles interact with atmosphere
            collide_info = self._collide_phase()

            # Phase 4: EMIT - Organized light emission creates aurora patterns
            emit_info = self._emit_phase()

            # Phase 5: DISSIPATE - Energy decays and curtains fade
            dissipate_info = self._dissipate_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            phase = AuroraPhase.DISSIPATE
            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "excite": excite_info,
                "drift": drift_info,
                "collide": collide_info,
                "emit": emit_info,
                "dissipate": dissipate_info,
                "total_zones": len(self._zones),
                "active_particles": len(self._particles),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _excite_phase(self) -> Dict[str, Any]:
        """Phase 1: Particles and zones gain energy from the magnetic field."""
        excited = 0
        for zone in self._zones.values():
            # Move excitation toward target
            diff = zone.target_excitation - zone.excitation
            zone.excitation += diff * self.EXCITATION_ADJUSTMENT_RATE
            zone.excitation = max(
                self.MIN_EXCITATION, min(self.MAX_EXCITATION, zone.excitation)
            )
            # Natural decay toward baseline
            baseline = DEFAULT_ZONE_EXCITATION.get(zone.zone_type, 0.3)
            zone.excitation += (baseline - zone.excitation) * self.NATURAL_EXCITATION_DECAY
            zone.excitation = max(
                self.MIN_EXCITATION, min(self.MAX_EXCITATION, zone.excitation)
            )
            # Hue drift
            zone.hue = (zone.hue + zone.hue_drift_rate) % 360.0
            if zone.target_hue is not None:
                hue_diff = (zone.target_hue - zone.hue + 540.0) % 360.0 - 180.0
                zone.hue = (zone.hue + hue_diff * self.HUE_ADJUSTMENT_RATE) % 360.0
            excited += 1

        # Boost particle energy from field lines
        for particle in self._particles:
            if not particle.active:
                continue
            lines = self._field_lines.get(particle.source_zone_id, [])
            for line in lines:
                if line.target_id == particle.target_zone_id:
                    boost = line.field_strength * 0.05
                    if not line.polarity:
                        boost = -boost
                    particle.energy = max(
                        self.MIN_ENERGY,
                        min(self.MAX_ENERGY, particle.energy + boost),
                    )
                    break

        return {"zones_excited": excited, "particles_boosted": len(self._particles)}

    def _drift_phase(self) -> Dict[str, Any]:
        """Phase 2: Particles drift along field lines toward target zones."""
        drifted = 0
        arrived: List[ChargedParticle] = []
        for particle in list(self._particles):
            if not particle.active:
                continue
            particle.progress += particle.drift_speed
            if particle.progress >= 1.0:
                arrived.append(particle)
                drifted += 1

        # Process arrived particles
        for particle in arrived:
            self._handle_particle_arrival(particle)

        # Spontaneous emission from high-excitation zones
        emitted = 0
        for zone in self._zones.values():
            if zone.excitation > 0.5 and random.random() < self.EMISSION_PROBABILITY:
                lines = self._field_lines.get(zone.zone_id, [])
                if lines:
                    line = random.choice(lines)
                    ptype = random.choice(list(ParticleType))
                    particle = ChargedParticle(
                        particle_id=f"part_{zone.zone_id}_{ptype.value}_{int(time.time()*1000)}_{random.randint(0,999)}",
                        particle_type=ptype,
                        energy=zone.excitation * 0.5,
                        source_zone_id=zone.zone_id,
                        target_zone_id=line.target_id,
                        hue=zone.hue,
                        progress=0.0,
                        drift_speed=random.uniform(0.1, 0.4),
                    )
                    self._particles.append(particle)
                    emitted += 1

        self._stats.total_particles = len(self._particles)
        return {"particles_arrived": drifted, "particles_emitted": emitted}

    def _handle_particle_arrival(self, particle: ChargedParticle) -> None:
        """Handle a particle arriving at its target zone."""
        target = self._zones.get(particle.target_zone_id)
        if target is None:
            particle.active = False
            return

        # Transfer energy and hue to the target zone
        target.excitation = min(
            self.MAX_EXCITATION, target.excitation + particle.energy * 0.1
        )
        # Blend hues
        hue_diff = (particle.hue - target.hue + 540.0) % 360.0 - 180.0
        target.hue = (target.hue + hue_diff * 0.15) % 360.0

        particle.active = False

    def _collide_phase(self) -> Dict[str, Any]:
        """Phase 3: Particles interact with the atmosphere, emitting color."""
        collisions = 0
        shimmers = 0
        for zone in self._zones.values():
            # Check for shimmer: large hue difference with linked zones
            lines = self._field_lines.get(zone.zone_id, [])
            for line in lines:
                other = self._zones.get(line.target_id)
                if other is None:
                    continue
                hue_diff = abs(zone.hue - other.hue)
                hue_diff = min(hue_diff, 360.0 - hue_diff)
                if hue_diff > self.SHIMMER_THRESHOLD and line.field_strength > 0.3:
                    # Shimmer event
                    self._record_event(
                        AuroraEvent.SHIMMER,
                        min(1.0, hue_diff / 180.0),
                        [zone.zone_id, line.target_id],
                        f"Shimmer between {zone.zone_id} and {line.target_id}",
                    )
                    shimmers += 1
                    collisions += 1

            # Particles colliding with this zone
            for particle in self._particles:
                if not particle.active:
                    continue
                if particle.target_zone_id == zone.zone_id and particle.progress >= 0.8:
                    collisions += 1

        return {"collisions": collisions, "shimmers": shimmers}

    def _emit_phase(self) -> Dict[str, Any]:
        """Phase 4: Organized light emission creates aurora curtains."""
        # Check for curtain formation: enough particles flowing between zones
        flow_counts: Dict[Tuple[str, str], int] = {}
        for particle in self._particles:
            if not particle.active:
                continue
            key = (particle.source_zone_id, particle.target_zone_id)
            flow_counts[key] = flow_counts.get(key, 0) + 1

        curtains_formed = 0
        for (src, tgt), count in flow_counts.items():
            if count >= self.CURTAIN_FORM_THRESHOLD:
                src_zone = self._zones.get(src)
                tgt_zone = self._zones.get(tgt)
                if src_zone is None or tgt_zone is None:
                    continue
                hue_min = min(src_zone.hue, tgt_zone.hue)
                hue_max = max(src_zone.hue, tgt_zone.hue)
                curtain = AuroraCurtain(
                    curtain_id=f"curtain_{src}_{tgt}_{int(time.time() * 1000)}",
                    zone_ids=[src, tgt],
                    hue_min=hue_min,
                    hue_max=hue_max,
                    intensity=min(1.0, count / 10.0),
                    drift_direction=random.uniform(0, 360),
                )
                self._curtains.append(curtain)
                curtains_formed += 1
                self._record_event(
                    AuroraEvent.CURTAIN_FORM,
                    curtain.intensity,
                    [src, tgt],
                    f"Curtain formed between {src} and {tgt}",
                )

        # Check for resonance glow: zones with similar hues
        zone_list = list(self._zones.values())
        resonance_count = 0
        for i in range(len(zone_list)):
            for j in range(i + 1, len(zone_list)):
                hue_diff = abs(zone_list[i].hue - zone_list[j].hue)
                hue_diff = min(hue_diff, 360.0 - hue_diff)
                if (
                    hue_diff < self.RESONANCE_HUE_THRESHOLD
                    and zone_list[i].excitation > 0.4
                    and zone_list[j].excitation > 0.4
                ):
                    # Synchronize hues slightly
                    avg_hue = (zone_list[i].hue + zone_list[j].hue) / 2.0
                    zone_list[i].target_hue = avg_hue
                    zone_list[j].target_hue = avg_hue
                    resonance_count += 1

        if resonance_count > 0:
            self._record_event(
                AuroraEvent.RESONANCE_GLOW,
                min(1.0, resonance_count / 10.0),
                [z.zone_id for z in zone_list[:5]],
                f"Resonance glow across {resonance_count} pairs",
            )

        return {
            "curtains_formed": curtains_formed,
            "resonance_pairs": resonance_count,
            "total_curtains": len(self._curtains),
        }

    def _dissipate_phase(self) -> Dict[str, Any]:
        """Phase 5: Energy decays and aurora curtains fade."""
        # Decay particle energy
        decayed = 0
        for particle in self._particles:
            if not particle.active:
                continue
            particle.energy -= self.PARTICLE_ENERGY_DECAY
            if particle.energy < self.MIN_PARTICLE_ENERGY:
                particle.active = False
                decayed += 1

        # Age curtains and remove old ones
        curtains_before = len(self._curtains)
        for curtain in self._curtains:
            curtain.age_cycles += 1
            curtain.intensity *= 0.92  # gradual fade
        # Remove faded curtains
        while self._curtains and self._curtains[0].intensity < 0.05:
            self._curtains.popleft()
        curtains_removed = curtains_before - len(self._curtains)

        # Record dissipation if many curtains faded
        if curtains_removed > 0:
            self._record_event(
                AuroraEvent.DISSIPATION,
                min(1.0, curtains_removed / 10.0),
                [],
                f"{curtains_removed} curtains dissipated",
            )

        self._stats.total_particles = len(self._particles)
        self._stats.total_curtains = len(self._curtains)
        return {
            "particles_decayed": decayed,
            "curtains_removed": curtains_removed,
            "active_curtains": len(self._curtains),
        }

    # -------------------------------------------------------------------------
    # Event Recording
    # -------------------------------------------------------------------------

    def _record_event(
        self,
        event_type: AuroraEvent,
        intensity: float,
        zone_ids: List[str],
        description: str,
    ) -> Dict[str, Any]:
        """Record an aurora event and return its dictionary form."""
        event = {
            "event_id": f"aurora_{event_type.value}_{int(time.time() * 1000)}_{random.randint(0, 999)}",
            "event_type": event_type.value,
            "intensity": max(0.0, min(1.0, intensity)),
            "zone_ids": zone_ids,
            "description": description,
            "timestamp": time.time(),
        }
        self._event_history.append(event)
        self._stats.total_events += 1
        if event_type == AuroraEvent.CURTAIN_FORM:
            self._stats.total_curtain_forms += 1
        elif event_type == AuroraEvent.CORONA_BURST:
            self._stats.total_corona_bursts += 1
        elif event_type == AuroraEvent.SHIMMER:
            self._stats.total_shimmers += 1
        elif event_type == AuroraEvent.BLACKOUT:
            self._stats.total_blackouts += 1
        elif event_type == AuroraEvent.RESONANCE_GLOW:
            self._stats.total_resonance_glows += 1
        return event

    def get_events(
        self, zone_id: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent aurora events, optionally filtered by zone."""
        with self._lock:
            results = []
            for event in reversed(self._event_history):
                if zone_id is not None and zone_id not in event.get("zone_ids", []):
                    continue
                results.append(event)
                if len(results) >= limit:
                    break
            return results

    def get_curtains(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get active aurora curtains."""
        with self._lock:
            results = [self._curtain_to_dict(c) for c in self._curtains]
            results.sort(key=lambda d: d.get("intensity", 0), reverse=True)
            return results[:limit]

    # -------------------------------------------------------------------------
    # Simulation & Status
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles and return a summary."""
        cycles = max(1, min(100, int(cycles)))
        results: List[Dict[str, Any]] = []
        with self._lock:
            for _ in range(cycles):
                results.append(self.run_cycle())
        last = results[-1] if results else {}
        return {
            "cycles_run": len(results),
            "last_cycle": last,
            "status": self.get_status(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the aurora projector."""
        with self._lock:
            return {
                "total_zones": len(self._zones),
                "active_particles": len(self._particles),
                "active_curtains": len(self._curtains),
                "active": self._stats.active,
                "cycle_count": self._cycle_count,
                "stats": {
                    "total_events": self._stats.total_events,
                    "total_curtain_forms": self._stats.total_curtain_forms,
                    "total_corona_bursts": self._stats.total_corona_bursts,
                    "total_shimmers": self._stats.total_shimmers,
                    "total_blackouts": self._stats.total_blackouts,
                    "total_resonance_glows": self._stats.total_resonance_glows,
                    "avg_excitation": round(self._stats.avg_excitation, 4),
                    "avg_luminance": round(self._stats.avg_luminance, 4),
                    "last_cycle_time_ms": self._stats.last_cycle_time_ms,
                },
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the aurora projector to its initial state."""
        with self._lock:
            self._zones.clear()
            self._particles.clear()
            self._field_lines.clear()
            self._curtains.clear()
            self._event_history.clear()
            self._stats = AuroraStats()
            self._cycle_count = 0
            self._active = False
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Serialization Helpers
    # -------------------------------------------------------------------------

    def _update_avg_metrics(self) -> None:
        """Update running average metrics."""
        if self._zones:
            total_exc = sum(z.excitation for z in self._zones.values())
            total_lum = sum(z.luminance for z in self._zones.values())
            self._stats.avg_excitation = total_exc / len(self._zones)
            self._stats.avg_luminance = total_lum / len(self._zones)

    def _zone_to_dict(self, zone: ColorZone) -> Dict[str, Any]:
        return {
            "zone_id": zone.zone_id,
            "label": zone.label,
            "zone_type": zone.zone_type.value,
            "excitation": round(zone.excitation, 4),
            "target_excitation": round(zone.target_excitation, 4),
            "hue": round(zone.hue, 2),
            "target_hue": round(zone.target_hue, 2),
            "saturation": round(zone.saturation, 4),
            "luminance": round(zone.luminance, 4),
            "hue_drift_rate": round(zone.hue_drift_rate, 4),
            "emitting": zone.emitting,
            "last_updated": zone.last_updated,
        }

    def _particle_to_dict(self, particle: ChargedParticle) -> Dict[str, Any]:
        return {
            "particle_id": particle.particle_id,
            "particle_type": particle.particle_type.value,
            "energy": round(particle.energy, 4),
            "source_zone_id": particle.source_zone_id,
            "target_zone_id": particle.target_zone_id,
            "hue": round(particle.hue, 2),
            "progress": round(particle.progress, 4),
            "drift_speed": round(particle.drift_speed, 4),
            "active": particle.active,
            "timestamp": particle.timestamp,
        }

    def _line_to_dict(self, line: MagneticLine, source_id: str) -> Dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": line.target_id,
            "field_strength": round(line.field_strength, 4),
            "polarity": line.polarity,
        }

    def _curtain_to_dict(self, curtain: AuroraCurtain) -> Dict[str, Any]:
        return {
            "curtain_id": curtain.curtain_id,
            "zone_ids": curtain.zone_ids,
            "hue_min": round(curtain.hue_min, 2),
            "hue_max": round(curtain.hue_max, 2),
            "intensity": round(curtain.intensity, 4),
            "drift_direction": round(curtain.drift_direction, 2),
            "age_cycles": curtain.age_cycles,
            "timestamp": curtain.timestamp,
        }
