"""
SparkLabs Engine - Spatial Harmonics Resonator

The EngineSpatialHarmonicsResonator models spatial relationships as
harmonic resonance fields. Each location in the game world vibrates at
characteristic frequencies that attract or repel certain types of events.
Like geographic feng shui made algorithmic and dynamic.

Locations have frequency profiles across multiple harmonic bands:
  - TENSION     : attracts conflict, danger, combat
  - SERENITY    : attracts rest, healing, reflection
  - MYSTERY     : attracts discovery, secrets, transformation
  - PROSPERITY  : attracts trade, fortune, growth
  - DECAY       : attracts loss, ruin, corruption

When a location's frequency aligns with an event type, that event
resonates there (more likely to occur and more impactful). When
frequencies conflict, interference patterns emerge: constructive
interference amplifies, destructive interference suppresses.

Architecture:
  HARMONIZE  ->  MEASURE  ->  RESONATE  ->  INTERFERE  ->  ATTUNE
  (establish    (measure     (identify      (handle          (adjust
   field map     current      locations      conflicting      field
   for world)    resonance    where events   frequencies)     based on
                 levels)      should occur)                   events)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class HarmonicBand(Enum):
    """Frequency bands that locations resonate on."""
    TENSION = "tension"
    SERENITY = "serenity"
    MYSTERY = "mystery"
    PROSPERITY = "prosperity"
    DECAY = "decay"


class ResonatorPhase(Enum):
    """Phases of the spatial harmonics cycle."""
    HARMONIZE = "harmonize"
    MEASURE = "measure"
    RESONATE = "resonate"
    INTERFERE = "interfere"
    ATTUNE = "attune"


class EventType(Enum):
    """Types of events that can resonate with locations."""
    COMBAT = "combat"
    HEALING = "healing"
    DISCOVERY = "discovery"
    TRADE = "trade"
    CORRUPTION = "corruption"
    RITUAL = "ritual"
    SOCIAL = "social"
    NATURAL = "natural"


class InterferenceType(Enum):
    """Types of interference between frequencies."""
    CONSTRUCTIVE = "constructive"   # amplifies
    DESTRUCTIVE = "destructive"     # suppresses
    NEUTRAL = "neutral"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class HarmonicLocation:
    """A location with a frequency profile across harmonic bands."""
    location_id: str
    name: str
    position: Tuple[float, float, float]
    # Frequency amplitudes per band (0.0 - 1.0)
    frequencies: Dict[HarmonicBand, float]
    # Radius of influence
    influence_radius: float = 20.0
    # How much the field can shift (0-1)
    mutability: float = 0.3
    # History of events that occurred here
    event_history: List[str] = field(default_factory=list)
    # Last measurement
    last_measured_at: float = 0.0
    # Dominant band (computed)
    dominant_band: HarmonicBand = HarmonicBand.SERENITY


@dataclass
class ResonanceReading:
    """A measurement of resonance at a location for an event type."""
    location_id: str
    event_type: EventType
    resonance_score: float       # 0.0 = none, 1.0 = perfect
    dominant_band: HarmonicBand
    interference: InterferenceType
    contributing_bands: Dict[str, float]  # band -> contribution
    measured_at: float = field(default_factory=time.time)


@dataclass
class FieldEvent:
    """An event that occurred in the harmonic field."""
    event_id: str
    location_id: str
    event_type: EventType
    timestamp: float
    intensity: float
    # Frequency shifts caused by this event
    frequency_shifts: Dict[str, float] = field(default_factory=dict)
    description: str = ""


@dataclass
class HarmonicsStats:
    """Aggregate statistics for the resonator."""
    total_cycles: int = 0
    total_locations: int = 0
    total_readings: int = 0
    total_events_recorded: int = 0
    total_interferences: int = 0
    avg_resonance: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Engine Spatial Harmonics Resonator
# =============================================================================

class EngineSpatialHarmonicsResonator:
    """
    Singleton engine module that models spatial resonance fields.

    The resonator runs a 5-phase cycle:
      1. HARMONIZE - Establish the field map by computing interactions
      2. MEASURE   - Measure resonance levels at each location
      3. RESONATE  - Identify where events should occur for maximum impact
      4. INTERFERE - Handle conflicting frequencies (constructive/destructive)
      5. ATTUNE    - Adjust the field based on events that occurred

    The resonator ensures the world has geographic character: certain
    places feel right for certain things, and events shape the field
    over time.
    """

    _instance: Optional["EngineSpatialHarmonicsResonator"] = None
    _instance_lock = threading.Lock()

    # Event-to-band affinity matrix (which band attracts which event)
    EVENT_BAND_AFFINITY: Dict[EventType, Dict[HarmonicBand, float]] = {
        EventType.COMBAT: {
            HarmonicBand.TENSION: 0.9, HarmonicBand.DECAY: 0.3,
            HarmonicBand.SERENITY: -0.5, HarmonicBand.PROSPERITY: -0.2,
            HarmonicBand.MYSTERY: 0.1,
        },
        EventType.HEALING: {
            HarmonicBand.SERENITY: 0.9, HarmonicBand.PROSPERITY: 0.3,
            HarmonicBand.TENSION: -0.5, HarmonicBand.DECAY: -0.6,
            HarmonicBand.MYSTERY: 0.2,
        },
        EventType.DISCOVERY: {
            HarmonicBand.MYSTERY: 0.9, HarmonicBand.SERENITY: 0.2,
            HarmonicBand.TENSION: 0.1, HarmonicBand.DECAY: 0.1,
            HarmonicBand.PROSPERITY: 0.1,
        },
        EventType.TRADE: {
            HarmonicBand.PROSPERITY: 0.9, HarmonicBand.SERENITY: 0.2,
            HarmonicBand.TENSION: -0.3, HarmonicBand.DECAY: -0.5,
            HarmonicBand.MYSTERY: 0.0,
        },
        EventType.CORRUPTION: {
            HarmonicBand.DECAY: 0.9, HarmonicBand.TENSION: 0.4,
            HarmonicBand.SERENITY: -0.7, HarmonicBand.PROSPERITY: -0.4,
            HarmonicBand.MYSTERY: 0.2,
        },
        EventType.RITUAL: {
            HarmonicBand.MYSTERY: 0.7, HarmonicBand.TENSION: 0.3,
            HarmonicBand.SERENITY: 0.3, HarmonicBand.DECAY: 0.2,
            HarmonicBand.PROSPERITY: 0.0,
        },
        EventType.SOCIAL: {
            HarmonicBand.PROSPERITY: 0.5, HarmonicBand.SERENITY: 0.5,
            HarmonicBand.TENSION: -0.2, HarmonicBand.DECAY: -0.3,
            HarmonicBand.MYSTERY: 0.1,
        },
        EventType.NATURAL: {
            HarmonicBand.SERENITY: 0.4, HarmonicBand.MYSTERY: 0.3,
            HarmonicBand.PROSPERITY: 0.2, HarmonicBand.TENSION: 0.1,
            HarmonicBand.DECAY: 0.1,
        },
    }

    # How much an event shifts the field (per intensity unit)
    EVENT_FIELD_INFLUENCE = 0.05
    # Natural field drift per cycle (toward neutral)
    FIELD_DRIFT_RATE = 0.01
    # Neutral frequency level
    NEUTRAL_FREQUENCY = 0.2

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._locations: Dict[str, HarmonicLocation] = {}
        self._readings: Deque[ResonanceReading] = deque(maxlen=200)
        self._events: Deque[FieldEvent] = deque(maxlen=200)
        self._stats = HarmonicsStats()
        self._cycle_count: int = 0
        self._active: bool = False

    @classmethod
    def get_instance(cls) -> "EngineSpatialHarmonicsResonator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Location Registration
    # -------------------------------------------------------------------------

    def register_location(self, location_id: str, name: str,
                          position: Tuple[float, float, float],
                          frequencies: Optional[Dict[str, float]] = None,
                          influence_radius: float = 20.0,
                          mutability: float = 0.3) -> Dict[str, Any]:
        """Register a new harmonic location."""
        with self._lock:
            if location_id in self._locations:
                return {"error": f"Location already exists: {location_id}"}
            # Parse frequencies
            freq_dict: Dict[HarmonicBand, float] = {}
            if frequencies:
                for band_str, value in frequencies.items():
                    try:
                        band = HarmonicBand(band_str)
                        freq_dict[band] = max(0.0, min(1.0, float(value)))
                    except (ValueError, TypeError):
                        continue
            # Fill missing bands with neutral
            for band in HarmonicBand:
                if band not in freq_dict:
                    freq_dict[band] = self.NEUTRAL_FREQUENCY
            location = HarmonicLocation(
                location_id=location_id,
                name=name,
                position=position,
                frequencies=freq_dict,
                influence_radius=max(1.0, float(influence_radius)),
                mutability=max(0.0, min(1.0, float(mutability))),
                last_measured_at=time.time(),
            )
            location.dominant_band = self._compute_dominant_band(location)
            self._locations[location_id] = location
            self._stats.total_locations = len(self._locations)
            return self._location_to_dict(location)

    def remove_location(self, location_id: str) -> Dict[str, Any]:
        with self._lock:
            loc = self._locations.pop(location_id, None)
            if loc is None:
                return {"error": f"Location not found: {location_id}"}
            self._stats.total_locations = len(self._locations)
            return {"removed": True, "location_id": location_id}

    def _compute_dominant_band(self, location: HarmonicLocation) -> HarmonicBand:
        """Compute the dominant frequency band for a location."""
        if not location.frequencies:
            return HarmonicBand.SERENITY
        return max(location.frequencies.items(), key=lambda x: x[1])[0]

    # -------------------------------------------------------------------------
    # Phase 1: HARMONIZE - Establish field map
    # -------------------------------------------------------------------------

    def _harmonize_phase(self) -> Dict[str, Any]:
        """Compute interactions between nearby locations."""
        interactions = 0
        location_list = list(self._locations.values())
        for i, loc_a in enumerate(location_list):
            for loc_b in location_list[i + 1:]:
                dist = self._distance(loc_a.position, loc_b.position)
                # Check if within mutual influence
                if dist < loc_a.influence_radius + loc_b.influence_radius:
                    interactions += 1
        return {
            "total_locations": len(self._locations),
            "field_interactions": interactions,
        }

    # -------------------------------------------------------------------------
    # Phase 2: MEASURE - Measure resonance levels
    # -------------------------------------------------------------------------

    def measure_resonance(self, location_id: str, event_type: str) -> Dict[str, Any]:
        """Measure the resonance of an event type at a location."""
        with self._lock:
            location = self._locations.get(location_id)
            if location is None:
                return {"error": f"Location not found: {location_id}"}
            try:
                etype = EventType(event_type)
            except ValueError:
                return {"error": f"Invalid event type: {event_type}"}
            reading = self._compute_resonance(location, etype)
            self._readings.append(reading)
            self._stats.total_readings += 1
            location.last_measured_at = time.time()
            return self._reading_to_dict(reading)

    def _compute_resonance(self, location: HarmonicLocation,
                           event_type: EventType) -> ResonanceReading:
        """Compute resonance score for an event at a location."""
        affinity = self.EVENT_BAND_AFFINITY.get(event_type, {})
        contributing: Dict[str, float] = {}
        total_score = 0.0
        positive_contributions = 0.0
        negative_contributions = 0.0

        for band, aff in affinity.items():
            freq = location.frequencies.get(band, self.NEUTRAL_FREQUENCY)
            contribution = freq * aff
            contributing[band.value] = round(contribution, 3)
            total_score += contribution
            if contribution > 0:
                positive_contributions += contribution
            else:
                negative_contributions += abs(contribution)

        # Resonance score: normalized to 0-1
        max_possible = sum(max(0, a) for a in affinity.values())
        if max_possible > 0:
            resonance = max(0.0, total_score / max_possible)
        else:
            resonance = 0.0

        # Determine interference
        if positive_contributions > 0 and negative_contributions > 0:
            ratio = min(positive_contributions, negative_contributions) / \
                    max(positive_contributions, negative_contributions)
            if ratio > 0.5:
                interference = InterferenceType.DESTRUCTIVE
            elif ratio > 0.2:
                interference = InterferenceType.NEUTRAL
            else:
                interference = InterferenceType.CONSTRUCTIVE
        else:
            interference = InterferenceType.CONSTRUCTIVE

        return ResonanceReading(
            location_id=location.location_id,
            event_type=event_type,
            resonance_score=round(resonance, 3),
            dominant_band=location.dominant_band,
            interference=interference,
            contributing_bands=contributing,
        )

    def _measure_phase(self) -> Dict[str, Any]:
        """Measure resonance for all locations across key event types."""
        if not self._locations:
            return {"measurements": 0}
        measurements = 0
        for location in self._locations.values():
            # Measure for a representative event type
            etype = self._band_to_event_type(location.dominant_band)
            reading = self._compute_resonance(location, etype)
            self._readings.append(reading)
            measurements += 1
        self._stats.total_readings += measurements
        self._update_avg_resonance()
        return {"measurements": measurements}

    def _band_to_event_type(self, band: HarmonicBand) -> EventType:
        """Map a dominant band to its primary event type."""
        mapping = {
            HarmonicBand.TENSION: EventType.COMBAT,
            HarmonicBand.SERENITY: EventType.HEALING,
            HarmonicBand.MYSTERY: EventType.DISCOVERY,
            HarmonicBand.PROSPERITY: EventType.TRADE,
            HarmonicBand.DECAY: EventType.CORRUPTION,
        }
        return mapping.get(band, EventType.NATURAL)

    # -------------------------------------------------------------------------
    # Phase 3: RESONATE - Find best locations for events
    # -------------------------------------------------------------------------

    def find_resonant_locations(self, event_type: str,
                                 limit: int = 5) -> List[Dict[str, Any]]:
        """Find the most resonant locations for an event type."""
        with self._lock:
            try:
                etype = EventType(event_type)
            except ValueError:
                return []
            results: List[Dict[str, Any]] = []
            for location in self._locations.values():
                reading = self._compute_resonance(location, etype)
                results.append({
                    "location_id": location.location_id,
                    "name": location.name,
                    "resonance_score": reading.resonance_score,
                    "interference": reading.interference.value,
                    "dominant_band": reading.dominant_band.value,
                    "contributing_bands": reading.contributing_bands,
                })
            results.sort(key=lambda x: x["resonance_score"], reverse=True)
            return results[:limit]

    def _resonate_phase(self) -> Dict[str, Any]:
        """Identify the most resonant location-event pairings."""
        recommendations: List[Dict[str, Any]] = []
        for etype in EventType:
            best = None
            best_score = 0.0
            for location in self._locations.values():
                reading = self._compute_resonance(location, etype)
                if reading.resonance_score > best_score:
                    best_score = reading.resonance_score
                    best = (location, reading)
            if best is not None and best_score > 0.3:
                loc, reading = best
                recommendations.append({
                    "event_type": etype.value,
                    "location_id": loc.location_id,
                    "location_name": loc.name,
                    "resonance_score": reading.resonance_score,
                    "interference": reading.interference.value,
                })
        return {
            "recommendations": recommendations[:10],
            "total_pairings": len(recommendations),
        }

    # -------------------------------------------------------------------------
    # Phase 4: INTERFERE - Handle conflicting frequencies
    # -------------------------------------------------------------------------

    def _interfere_phase(self) -> Dict[str, Any]:
        """Detect and process interference patterns."""
        constructive = 0
        destructive = 0
        neutral = 0
        # Check recent readings for interference
        recent = list(self._readings)[-20:]
        for reading in recent:
            if reading.interference == InterferenceType.CONSTRUCTIVE:
                constructive += 1
            elif reading.interference == InterferenceType.DESTRUCTIVE:
                destructive += 1
            else:
                neutral += 1
        self._stats.total_interferences += constructive + destructive
        return {
            "constructive": constructive,
            "destructive": destructive,
            "neutral": neutral,
        }

    # -------------------------------------------------------------------------
    # Phase 5: ATTUNE - Adjust field based on events
    # -------------------------------------------------------------------------

    def record_field_event(self, location_id: str, event_type: str,
                           intensity: float = 0.5,
                           description: str = "") -> Dict[str, Any]:
        """Record an event that occurred at a location, shifting the field."""
        with self._lock:
            location = self._locations.get(location_id)
            if location is None:
                return {"error": f"Location not found: {location_id}"}
            try:
                etype = EventType(event_type)
            except ValueError:
                return {"error": f"Invalid event type: {event_type}"}
            intensity = max(0.0, min(1.0, float(intensity)))
            # Compute frequency shifts based on event affinity
            affinity = self.EVENT_BAND_AFFINITY.get(etype, {})
            shifts: Dict[str, float] = {}
            for band, aff in affinity.items():
                current = location.frequencies.get(band, self.NEUTRAL_FREQUENCY)
                shift = aff * self.EVENT_FIELD_INFLUENCE * intensity * location.mutability
                new_val = max(0.0, min(1.0, current + shift))
                location.frequencies[band] = new_val
                if abs(shift) > 0.001:
                    shifts[band.value] = round(shift, 4)
            # Update dominant band
            location.dominant_band = self._compute_dominant_band(location)
            # Record event
            event = FieldEvent(
                event_id=f"fe_{int(time.time() * 1000)}_{len(self._events)}",
                location_id=location_id,
                event_type=etype,
                timestamp=time.time(),
                intensity=intensity,
                frequency_shifts=shifts,
                description=description or f"{etype.value} at {location.name}",
            )
            self._events.append(event)
            location.event_history.append(event.event_id)
            self._stats.total_events_recorded += 1
            return self._field_event_to_dict(event)

    def _attune_phase(self) -> Dict[str, Any]:
        """Apply natural field drift toward neutral."""
        drifted = 0
        for location in self._locations.values():
            drifted_this = False
            for band in HarmonicBand:
                current = location.frequencies.get(band, self.NEUTRAL_FREQUENCY)
                # Drift toward neutral
                if abs(current - self.NEUTRAL_FREQUENCY) > 0.01:
                    direction = 1 if current < self.NEUTRAL_FREQUENCY else -1
                    location.frequencies[band] = current + direction * self.FIELD_DRIFT_RATE
                    drifted_this = True
            if drifted_this:
                location.dominant_band = self._compute_dominant_band(location)
                drifted += 1
        return {"locations_drifted": drifted}

    # -------------------------------------------------------------------------
    # Resonator Cycle Orchestration
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single spatial harmonics cycle.

        Phases: HARMONIZE -> MEASURE -> RESONATE -> INTERFERE -> ATTUNE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: HARMONIZE
            phase = ResonatorPhase.HARMONIZE
            harmonize_info = self._harmonize_phase()

            # Phase 2: MEASURE
            phase = ResonatorPhase.MEASURE
            measure_info = self._measure_phase()

            # Phase 3: RESONATE
            phase = ResonatorPhase.RESONATE
            resonate_info = self._resonate_phase()

            # Phase 4: INTERFERE
            phase = ResonatorPhase.INTERFERE
            interfere_info = self._interfere_phase()

            # Phase 5: ATTUNE
            phase = ResonatorPhase.ATTUNE
            attune_info = self._attune_phase()

            elapsed_ms = (time.time() - start_time) * 1000
            self._cycle_count += 1
            self._stats.total_cycles += 1
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._update_avg_resonance()

            self._active = False

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "harmonize": harmonize_info,
                "measure": measure_info,
                "resonate": resonate_info,
                "interfere": interfere_info,
                "attune": attune_info,
                "total_locations": len(self._locations),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple harmonics cycles with synthetic data."""
        with self._lock:
            if not self._locations:
                self._seed_synthetic_locations()
            results = []
            for i in range(max(1, cycles)):
                # Occasionally record events to shift the field
                if i % 2 == 0 and self._locations:
                    loc = random.choice(list(self._locations.values()))
                    etype = random.choice(list(EventType))
                    self.record_field_event(
                        location_id=loc.location_id,
                        event_type=etype.value,
                        intensity=round(random.uniform(0.3, 0.9), 2),
                    )
                results.append(self.run_cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_stats": self._stats_to_dict(),
            }

    def _seed_synthetic_locations(self) -> None:
        """Seed synthetic locations for simulation."""
        locations_data = [
            ("loc_tavern", "Dragon's Rest Tavern", (10, 20, 0),
             {"prosperity": 0.7, "social": 0.5, "tension": 0.2}),
            ("loc_ruins", "Ancient Ruins", (-30, 40, 0),
             {"mystery": 0.8, "decay": 0.5, "tension": 0.3}),
            ("loc_temple", "Sunlit Temple", (50, -20, 0),
             {"serenity": 0.9, "mystery": 0.3, "prosperity": 0.2}),
            ("loc_battleground", "Old Battleground", (-20, -30, 0),
             {"tension": 0.9, "decay": 0.6, "mystery": 0.2}),
            ("loc_market", "Grand Market", (30, 30, 0),
             {"prosperity": 0.8, "serenity": 0.2, "tension": 0.1}),
            ("loc_swamp", "Mistwood Swamp", (-50, 10, 0),
             {"decay": 0.7, "mystery": 0.6, "tension": 0.3}),
        ]
        for lid, name, pos, freqs in locations_data:
            self.register_location(lid, name, pos, freqs)

    # -------------------------------------------------------------------------
    # Query and Inspection
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "total_locations": len(self._locations),
                "stats": self._stats_to_dict(),
            }

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_cycles": self._stats.total_cycles,
            "total_locations": self._stats.total_locations,
            "total_readings": self._stats.total_readings,
            "total_events_recorded": self._stats.total_events_recorded,
            "total_interferences": self._stats.total_interferences,
            "avg_resonance": self._stats.avg_resonance,
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }

    def list_locations(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._location_to_dict(loc)
                    for loc in list(self._locations.values())[:limit]]

    def get_location(self, location_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            loc = self._locations.get(location_id)
            return self._location_to_dict(loc) if loc else None

    def list_readings(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._reading_to_dict(r) for r in list(self._readings)[-limit:]]

    def list_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._field_event_to_dict(e) for e in list(self._events)[-limit:]]

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            count = len(self._locations)
            self._locations.clear()
            self._readings.clear()
            self._events.clear()
            self._stats = HarmonicsStats()
            self._cycle_count = 0
            return {"reset": True, "cleared_locations": count}

    def _update_avg_resonance(self) -> None:
        if not self._readings:
            self._stats.avg_resonance = 0.0
            return
        recent = list(self._readings)[-20:]
        self._stats.avg_resonance = round(
            sum(r.resonance_score for r in recent) / len(recent), 3
        )

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    @staticmethod
    def _distance(a: Tuple[float, float, float],
                  b: Tuple[float, float, float]) -> float:
        return math.sqrt(
            (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
        )

    # -------------------------------------------------------------------------
    # Serialization helpers
    # -------------------------------------------------------------------------

    def _location_to_dict(self, loc: HarmonicLocation) -> Dict[str, Any]:
        return {
            "location_id": loc.location_id,
            "name": loc.name,
            "position": list(loc.position),
            "frequencies": {k.value: round(v, 3) for k, v in loc.frequencies.items()},
            "influence_radius": loc.influence_radius,
            "mutability": loc.mutability,
            "dominant_band": loc.dominant_band.value,
            "event_history_count": len(loc.event_history),
            "last_measured_at": loc.last_measured_at,
        }

    def _reading_to_dict(self, r: ResonanceReading) -> Dict[str, Any]:
        return {
            "location_id": r.location_id,
            "event_type": r.event_type.value,
            "resonance_score": r.resonance_score,
            "dominant_band": r.dominant_band.value,
            "interference": r.interference.value,
            "contributing_bands": r.contributing_bands,
            "measured_at": r.measured_at,
        }

    def _field_event_to_dict(self, e: FieldEvent) -> Dict[str, Any]:
        return {
            "event_id": e.event_id,
            "location_id": e.location_id,
            "event_type": e.event_type.value,
            "timestamp": e.timestamp,
            "intensity": round(e.intensity, 3),
            "frequency_shifts": e.frequency_shifts,
            "description": e.description,
        }
