"""
SparkLabs Agent - Cognitive Tide Orchestrator

The AgentCognitiveTideOrchestrator models agent attention as an ocean
whose tides are driven by the gravitational pull of cognitive bodies.
Goals, threats, curiosities, memories, and social demands are celestial
bodies orbiting an attention ocean. Each body exerts gravitational pull
proportional to its importance (mass) and inversely proportional to its
attentional distance.

This tidal metaphor captures how attention actually works in minds: it
does not switch discretely between targets, it rises and falls in waves.
When two high-mass bodies align (a deadline goal coinciding with an
urgent threat), a spring tide floods attention toward them, crowding
out everything else. When bodies oppose each other, a neap tide leaves
attention diffuse and scattered. Conflicting bodies of equal mass can
rip attention sideways in a maelstrom.

Core concepts:
  - MASS          : the importance/priority of a cognitive body (0.0-10.0)
  - ORBITAL_DIST  : how far the body sits from the attention center
  - GRAVITY       : pull = mass / (distance^2), drives tide height
  - TIDE LEVEL    : current attention height in a tidal zone (0.0-1.0)
  - CONJUNCTION   : bodies align -> spring tide (intense focus)
  - OPPOSITION    : bodies oppose -> neap tide (diffuse attention)
  - MAELSTROM     : equal-mass conflict tears attention into a vortex

Cognitive body types:
  GOAL        : long-term objectives, high mass, distant orbit
  THREAT      : immediate dangers, high mass, close orbit
  CURIOSITY   : exploration targets, low mass, variable orbit
  MEMORY      : recalled experiences, medium mass, distant orbit
  SOCIAL      : relationship demands, medium mass, medium orbit
  REFLECTION  : self-monitoring, low mass, close orbit

Tidal events:
  SPRING_TIDE     : bodies align, attention surges
  NEAP_TIDE       : bodies oppose, attention diffuses
  RIP_CURRENT     : conflict pulls attention sideways
  WAVE_CRASH      : sudden focus collapse
  STILL_WATER     : calm balanced attention
  MAELSTROM       : attention vortex from conflicting goals

Architecture:
  GRAVITATE  ->  ORBIT   ->  TIDE    ->  EBB        ->  CONSOLIDATE
  (bodies      (bodies     (combined   (attention     (ocean settles,
   exert        move along  forces      recedes from   focus locks
   gravity on   orbits,     create      low-priority   onto dominant
   the ocean)   shifting    tide        bodies)        bodies)
               pull)        levels)

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

class CognitiveBodyType(Enum):
    """Types of cognitive bodies that orbit the attention ocean."""
    GOAL = "goal"                # long-term objectives
    THREAT = "threat"            # immediate dangers
    CURIOSITY = "curiosity"      # exploration targets
    MEMORY = "memory"            # recalled experiences
    SOCIAL = "social"            # relationship demands
    REFLECTION = "reflection"    # self-monitoring


class TidePhase(Enum):
    """Phases of the cognitive tide cycle."""
    GRAVITATE = "gravitate"
    ORBIT = "orbit"
    TIDE = "tide"
    EBB = "ebb"
    CONSOLIDATE = "consolidate"


class TideEvent(Enum):
    """Events that occur during the tidal cycle."""
    SPRING_TIDE = "spring_tide"        # bodies align, attention surges
    NEAP_TIDE = "neap_tide"            # bodies oppose, attention diffuses
    RIP_CURRENT = "rip_current"        # conflict pulls attention sideways
    WAVE_CRASH = "wave_crash"          # sudden focus collapse
    STILL_WATER = "still_water"        # calm balanced attention
    MAELSTROM = "maelstrom"            # attention vortex from conflict


# =============================================================================
# Default Parameters by Body Type
# =============================================================================

# Default mass for each cognitive body type
DEFAULT_BODY_MASS: Dict[CognitiveBodyType, float] = {
    CognitiveBodyType.GOAL: 8.0,
    CognitiveBodyType.THREAT: 9.0,
    CognitiveBodyType.CURIOSITY: 3.0,
    CognitiveBodyType.MEMORY: 5.0,
    CognitiveBodyType.SOCIAL: 4.0,
    CognitiveBodyType.REFLECTION: 2.0,
}

# Default orbital distance for each body type (1.0 = close, 10.0 = far)
DEFAULT_ORBITAL_DISTANCE: Dict[CognitiveBodyType, float] = {
    CognitiveBodyType.GOAL: 7.0,
    CognitiveBodyType.THREAT: 2.0,
    CognitiveBodyType.CURIOSITY: 5.0,
    CognitiveBodyType.MEMORY: 8.0,
    CognitiveBodyType.SOCIAL: 4.0,
    CognitiveBodyType.REFLECTION: 3.0,
}

# Default orbital velocity for each body type (radians per cycle)
DEFAULT_ORBITAL_VELOCITY: Dict[CognitiveBodyType, float] = {
    CognitiveBodyType.GOAL: 0.05,
    CognitiveBodyType.THREAT: 0.25,
    CognitiveBodyType.CURIOSITY: 0.15,
    CognitiveBodyType.MEMORY: 0.03,
    CognitiveBodyType.SOCIAL: 0.10,
    CognitiveBodyType.REFLECTION: 0.20,
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class CognitiveBody:
    """A celestial body in the cognitive attention space."""
    body_id: str
    body_type: CognitiveBodyType
    label: str
    # Importance / priority of this body
    mass: float
    # Distance from the attention center (1.0 = close, 10.0 = far)
    orbital_distance: float
    # Current orbital angle in radians
    orbital_angle: float
    # Angular velocity (radians per cycle)
    orbital_velocity: float
    # Whether this body is currently active
    active: bool = True
    # How long this body has been in the system
    cycles_present: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class TidalZone:
    """A region of the attention ocean with its own tide level."""
    zone_id: str
    label: str
    # Baseline depth of this zone (0.0 = shallow, 1.0 = deep)
    baseline_depth: float
    # Current tide level (0.0 = low tide, 1.0 = high tide)
    current_tide: float
    # Target tide level the zone is moving toward
    target_tide: float
    # How much the tide fluctuates in this zone
    tidal_amplitude: float
    # Dominant body pulling on this zone
    dominant_body_id: Optional[str] = None
    # Whether this zone is in a disturbed state
    disturbed: bool = False
    last_updated: float = field(default_factory=time.time)


@dataclass
class TideEventRecord:
    """A recorded tidal event in the cognitive ocean."""
    event_id: str
    event_type: TideEvent
    # Intensity of the event (0.0-1.0)
    intensity: float
    # Body IDs involved in the event
    body_ids: List[str]
    # Zone where the event occurred
    zone_id: Optional[str]
    # Tide level change caused by the event
    tide_delta: float
    timestamp: float


@dataclass
class CognitiveTideStats:
    """Aggregate statistics for the cognitive tide system."""
    total_bodies: int = 0
    total_zones: int = 0
    total_events: int = 0
    total_spring_tides: int = 0
    total_neap_tides: int = 0
    total_rip_currents: int = 0
    total_maelstroms: int = 0
    total_wave_crashes: int = 0
    avg_tide_level: float = 0.0
    avg_gravity: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Cognitive Tide Orchestrator
# =============================================================================

class AgentCognitiveTideOrchestrator:
    """
    Singleton agent that models attention allocation as a tidal ocean driven
    by the gravitational pull of cognitive bodies.

    The orchestrator runs a 5-phase cycle:
      1. GRAVITATE   - Each active body exerts gravitational pull on zones
      2. ORBIT       - Bodies move along their orbits, shifting pull patterns
      3. TIDE        - Combined forces create tide levels (high/low attention)
      4. EBB         - Attention recedes from low-priority zones
      5. CONSOLIDATE - The ocean settles and focus crystallizes on dominants

    The tidal metaphor ensures attention feels organic: focus rises and falls
    in waves rather than switching like a boolean, and conflicting priorities
    create visible turbulence in the attention field.
    """

    _instance: Optional["AgentCognitiveTideOrchestrator"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_BODIES = 100
    MAX_ZONES = 50
    MAX_EVENT_HISTORY = 200
    MAX_BODIES_PER_ZONE = 15
    # Minimum mass for a body to remain active
    MIN_MASS = 0.1
    # Maximum mass
    MAX_MASS = 10.0
    # Minimum orbital distance
    MIN_DISTANCE = 0.5
    # Maximum orbital distance
    MAX_DISTANCE = 10.0
    # Gravitational constant (scaling factor)
    GRAVITATIONAL_CONSTANT = 0.5
    # How fast tide levels move toward targets
    TIDE_ADJUSTMENT_RATE = 0.15
    # Natural tide decay per cycle
    NATURAL_TIDE_DECAY = 0.03
    # Minimum tide level
    MIN_TIDE = 0.0
    # Maximum tide level
    MAX_TIDE = 1.0
    # Conjunction threshold (angle difference for spring tide)
    CONJUNCTION_THRESHOLD = 0.4
    # Opposition threshold (angle difference for neap tide)
    OPPOSITION_THRESHOLD = 2.5
    # Maelstrom threshold (gravity balance difference)
    MAELSTROM_THRESHOLD = 0.05
    # Wave crash threshold (rapid tide drop)
    WAVE_CRASH_THRESHOLD = 0.3
    # Still water threshold (low total gravity)
    STILL_WATER_THRESHOLD = 0.2

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._bodies: Dict[str, CognitiveBody] = {}
        self._zones: Dict[str, TidalZone] = {}
        self._event_history: Deque[TideEventRecord] = deque(
            maxlen=self.MAX_EVENT_HISTORY
        )
        self._stats = CognitiveTideStats()
        self._cycle_count: int = 0
        self._active: bool = False

    @classmethod
    def get_instance(cls) -> "AgentCognitiveTideOrchestrator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Cognitive Body Management
    # -------------------------------------------------------------------------

    def register_body(
        self,
        body_id: str,
        body_type: str,
        label: str,
        mass: Optional[float] = None,
        orbital_distance: Optional[float] = None,
        orbital_angle: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a new cognitive body in the attention space."""
        with self._lock:
            if body_id in self._bodies:
                return {"error": f"Body already registered: {body_id}"}
            if len(self._bodies) >= self.MAX_BODIES:
                return {"error": "Maximum bodies reached"}

            try:
                btype = CognitiveBodyType(body_type)
            except ValueError:
                return {"error": f"Unknown body type: {body_type}"}

            # Apply defaults if not provided
            if mass is None:
                mass = DEFAULT_BODY_MASS.get(btype, 5.0)
            mass = max(self.MIN_MASS, min(self.MAX_MASS, float(mass)))

            if orbital_distance is None:
                orbital_distance = DEFAULT_ORBITAL_DISTANCE.get(btype, 5.0)
            orbital_distance = max(
                self.MIN_DISTANCE, min(self.MAX_DISTANCE, float(orbital_distance))
            )

            if orbital_angle is None:
                orbital_angle = random.uniform(0, 2 * math.pi)
            else:
                orbital_angle = float(orbital_angle) % (2 * math.pi)

            velocity = DEFAULT_ORBITAL_VELOCITY.get(btype, 0.1)

            body = CognitiveBody(
                body_id=body_id,
                body_type=btype,
                label=label,
                mass=mass,
                orbital_distance=orbital_distance,
                orbital_angle=orbital_angle,
                orbital_velocity=velocity,
            )
            self._bodies[body_id] = body
            self._stats.total_bodies = len(self._bodies)
            return self._body_to_dict(body)

    def get_body(self, body_id: str) -> Dict[str, Any]:
        """Get the state of a cognitive body."""
        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return {"error": f"Body not found: {body_id}"}
            return self._body_to_dict(body)

    def list_bodies(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List cognitive bodies."""
        with self._lock:
            results = [self._body_to_dict(b) for b in self._bodies.values()]
            results.sort(key=lambda d: d.get("mass", 0), reverse=True)
            return results[:limit]

    def remove_body(self, body_id: str) -> Dict[str, Any]:
        """Remove a cognitive body."""
        with self._lock:
            if body_id not in self._bodies:
                return {"removed": False}
            del self._bodies[body_id]
            self._stats.total_bodies = len(self._bodies)
            # Clear dominant body references
            for zone in self._zones.values():
                if zone.dominant_body_id == body_id:
                    zone.dominant_body_id = None
            return {"removed": True, "body_id": body_id}

    def set_body_mass(self, body_id: str, mass: float) -> Dict[str, Any]:
        """Update the mass (importance) of a cognitive body."""
        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return {"error": f"Body not found: {body_id}"}
            body.mass = max(self.MIN_MASS, min(self.MAX_MASS, float(mass)))
            body.last_updated = time.time()
            return self._body_to_dict(body)

    # -------------------------------------------------------------------------
    # Tidal Zone Management
    # -------------------------------------------------------------------------

    def register_zone(
        self,
        zone_id: str,
        label: str,
        baseline_depth: float = 0.5,
        tidal_amplitude: float = 0.3,
    ) -> Dict[str, Any]:
        """Register a new tidal zone in the attention ocean."""
        with self._lock:
            if zone_id in self._zones:
                return {"error": f"Zone already registered: {zone_id}"}
            if len(self._zones) >= self.MAX_ZONES:
                return {"error": "Maximum zones reached"}

            zone = TidalZone(
                zone_id=zone_id,
                label=label,
                baseline_depth=max(0.0, min(1.0, float(baseline_depth))),
                current_tide=max(0.0, min(1.0, float(baseline_depth))),
                target_tide=max(0.0, min(1.0, float(baseline_depth))),
                tidal_amplitude=max(0.0, min(1.0, float(tidal_amplitude))),
            )
            self._zones[zone_id] = zone
            self._stats.total_zones = len(self._zones)
            return self._zone_to_dict(zone)

    def get_zone(self, zone_id: str) -> Dict[str, Any]:
        """Get the state of a tidal zone."""
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return {"error": f"Zone not found: {zone_id}"}
            return self._zone_to_dict(zone)

    def list_zones(self) -> List[Dict[str, Any]]:
        """List all tidal zones."""
        with self._lock:
            return [self._zone_to_dict(z) for z in self._zones.values()]

    def remove_zone(self, zone_id: str) -> Dict[str, Any]:
        """Remove a tidal zone."""
        with self._lock:
            if zone_id not in self._zones:
                return {"removed": False}
            del self._zones[zone_id]
            self._stats.total_zones = len(self._zones)
            return {"removed": True, "zone_id": zone_id}

    # -------------------------------------------------------------------------
    # Tide Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single cognitive tide cycle.

        Phases: GRAVITATE -> ORBIT -> TIDE -> EBB -> CONSOLIDATE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: GRAVITATE - Bodies exert gravitational pull on zones
            gravitate_info = self._gravitate_phase()

            # Phase 2: ORBIT - Bodies move along their orbits
            orbit_info = self._orbit_phase()

            # Phase 3: TIDE - Combined forces create tide levels
            tide_info = self._tide_phase()

            # Phase 4: EBB - Attention recedes from low-priority zones
            ebb_info = self._ebb_phase()

            # Phase 5: CONSOLIDATE - The ocean settles
            consolidate_info = self._consolidate_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            phase = TidePhase.CONSOLIDATE
            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "gravitate": gravitate_info,
                "orbit": orbit_info,
                "tide": tide_info,
                "ebb": ebb_info,
                "consolidate": consolidate_info,
                "total_bodies": len(self._bodies),
                "total_zones": len(self._zones),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _gravitate_phase(self) -> Dict[str, Any]:
        """Phase 1: Each active body exerts gravitational pull on zones."""
        total_gravity = 0.0
        body_gravities: Dict[str, float] = {}

        for body_id, body in self._bodies.items():
            if not body.active:
                continue
            # Gravitational pull = G * mass / distance^2
            gravity = self.GRAVITATIONAL_CONSTANT * body.mass / (
                body.orbital_distance ** 2
            )
            body_gravities[body_id] = gravity
            total_gravity += gravity

        return {
            "bodies_evaluated": len(body_gravities),
            "total_gravity": round(total_gravity, 4),
            "avg_gravity": round(total_gravity / max(1, len(body_gravities)), 4),
        }

    def _orbit_phase(self) -> Dict[str, Any]:
        """Phase 2: Bodies move along their orbits."""
        moved = 0
        for body in self._bodies.values():
            if not body.active:
                continue
            body.orbital_angle = (
                body.orbital_angle + body.orbital_velocity
            ) % (2 * math.pi)
            body.cycles_present += 1
            body.last_updated = time.time()
            moved += 1
        return {"bodies_moved": moved}

    def _tide_phase(self) -> Dict[str, Any]:
        """Phase 3: Combined gravitational forces create tide levels."""
        events: List[Dict[str, Any]] = []

        for zone in self._zones.values():
            # Calculate the combined gravitational pull on this zone
            # Each body contributes based on its gravity and angular alignment
            # with the zone's "receptive angle" (derived from baseline_depth)
            zone_angle = zone.baseline_depth * 2 * math.pi

            total_pull = 0.0
            dominant_id: Optional[str] = None
            dominant_gravity = 0.0
            body_pulls: List[Tuple[str, float, float]] = []  # (id, gravity, angle_diff)

            for body in self._bodies.values():
                if not body.active:
                    continue
                gravity = self.GRAVITATIONAL_CONSTANT * body.mass / (
                    body.orbital_distance ** 2
                )
                # Angular alignment: how close the body's angle is to the zone's
                angle_diff = abs(body.orbital_angle - zone_angle)
                angle_diff = min(angle_diff, 2 * math.pi - angle_diff)
                # Alignment factor: 1.0 when perfectly aligned, 0.0 when opposite
                alignment = math.cos(angle_diff / 2)
                effective_pull = gravity * max(0.0, alignment)
                total_pull += effective_pull
                body_pulls.append((body.body_id, effective_pull, angle_diff))

                if effective_pull > dominant_gravity:
                    dominant_gravity = effective_pull
                    dominant_id = body.body_id

            zone.dominant_body_id = dominant_id

            # Set target tide level based on total pull
            # Normalize: tide = baseline + pull * amplitude, clamped
            new_target = zone.baseline_depth + total_pull * zone.tidal_amplitude * 0.3
            new_target = max(self.MIN_TIDE, min(self.MAX_TIDE, new_target))
            zone.target_tide = new_target

            # Detect conjunctions and oppositions between bodies
            if len(body_pulls) >= 2:
                # Sort by angle to find closest pairs
                body_pulls.sort(key=lambda x: x[2])
                for i in range(len(body_pulls)):
                    for j in range(i + 1, len(body_pulls)):
                        bid_a, grav_a, _ = body_pulls[i]
                        bid_b, grav_b, _ = body_pulls[j]
                        # Check angular proximity via the stored angle diffs
                        # Use direct angle comparison
                        body_a = self._bodies.get(bid_a)
                        body_b = self._bodies.get(bid_b)
                        if body_a is None or body_b is None:
                            continue
                        pair_diff = abs(body_a.orbital_angle - body_b.orbital_angle)
                        pair_diff = min(pair_diff, 2 * math.pi - pair_diff)

                        # Spring tide: two high-mass bodies in conjunction
                        if (
                            pair_diff < self.CONJUNCTION_THRESHOLD
                            and body_a.mass >= 5.0
                            and body_b.mass >= 5.0
                            and grav_a > 0.1
                            and grav_b > 0.1
                        ):
                            intensity = min(1.0, (grav_a + grav_b) / 2)
                            event = self._record_event(
                                TideEvent.SPRING_TIDE,
                                intensity,
                                [bid_a, bid_b],
                                zone.zone_id,
                                intensity * 0.15,
                            )
                            events.append(event)
                            zone.target_tide = min(
                                self.MAX_TIDE, zone.target_tide + intensity * 0.15
                            )

                        # Neap tide: two high-mass bodies in opposition
                        elif (
                            pair_diff > self.OPPOSITION_THRESHOLD
                            and body_a.mass >= 5.0
                            and body_b.mass >= 5.0
                        ):
                            intensity = min(1.0, abs(grav_a - grav_b) / 2)
                            event = self._record_event(
                                TideEvent.NEAP_TIDE,
                                intensity,
                                [bid_a, bid_b],
                                zone.zone_id,
                                -intensity * 0.1,
                            )
                            events.append(event)
                            zone.target_tide = max(
                                self.MIN_TIDE, zone.target_tide - intensity * 0.1
                            )

                        # Maelstrom: equal-mass bodies in tight conflict
                        if (
                            pair_diff < self.CONJUNCTION_THRESHOLD
                            and abs(body_a.mass - body_b.mass) < 1.0
                            and body_a.mass >= 6.0
                            and body_b.mass >= 6.0
                            and abs(grav_a - grav_b) < self.MAELSTROM_THRESHOLD
                        ):
                            intensity = min(1.0, (grav_a + grav_b) / 2)
                            event = self._record_event(
                                TideEvent.MAELSTROM,
                                intensity,
                                [bid_a, bid_b],
                                zone.zone_id,
                                -intensity * 0.2,
                            )
                            events.append(event)
                            zone.disturbed = True
                            zone.target_tide = max(
                                self.MIN_TIDE, zone.target_tide - intensity * 0.2
                            )

            # Still water: very low total gravity
            if total_pull < self.STILL_WATER_THRESHOLD:
                event = self._record_event(
                    TideEvent.STILL_WATER,
                    1.0 - total_pull,
                    [],
                    zone.zone_id,
                    0.0,
                )
                events.append(event)

            zone.last_updated = time.time()

        return {
            "zones_updated": len(self._zones),
            "events_detected": len(events),
            "events": events[:10],
        }

    def _ebb_phase(self) -> Dict[str, Any]:
        """Phase 4: Attention recedes from zones with low gravitational pull."""
        receded = 0
        crashed = 0
        for zone in self._zones.values():
            # Move current tide toward target
            old_tide = zone.current_tide
            diff = zone.target_tide - zone.current_tide
            zone.current_tide += diff * self.TIDE_ADJUSTMENT_RATE
            zone.current_tide = max(
                self.MIN_TIDE, min(self.MAX_TIDE, zone.current_tide)
            )

            # Natural decay toward baseline
            zone.current_tide += (
                zone.baseline_depth - zone.current_tide
            ) * self.NATURAL_TIDE_DECAY

            # Detect wave crash: rapid tide drop
            if old_tide - zone.current_tide > self.WAVE_CRASH_THRESHOLD:
                event = self._record_event(
                    TideEvent.WAVE_CRASH,
                    old_tide - zone.current_tide,
                    [],
                    zone.zone_id,
                    -(old_tide - zone.current_tide),
                )
                crashed += 1

            # Zones with very low tide are receding
            if zone.current_tide < 0.2:
                receded += 1

            zone.last_updated = time.time()

        return {"zones_receded": receded, "wave_crashes": crashed}

    def _consolidate_phase(self) -> Dict[str, Any]:
        """Phase 5: The ocean settles and focus crystallizes."""
        # Clear disturbed flags on zones that have stabilized
        settled = 0
        for zone in self._zones.values():
            if zone.disturbed:
                # Check if tide has stabilized
                if abs(zone.target_tide - zone.current_tide) < 0.05:
                    zone.disturbed = False
                    settled += 1
            zone.last_updated = time.time()

        # Compute dominant bodies across all zones
        dominant_bodies: Dict[str, int] = {}
        for zone in self._zones.values():
            if zone.dominant_body_id:
                dominant_bodies[zone.dominant_body_id] = (
                    dominant_bodies.get(zone.dominant_body_id, 0) + 1
                )

        return {
            "zones_settled": settled,
            "dominant_body_count": len(dominant_bodies),
            "top_dominant": sorted(
                dominant_bodies.items(), key=lambda x: x[1], reverse=True
            )[:3],
        }

    # -------------------------------------------------------------------------
    # Event Recording
    # -------------------------------------------------------------------------

    def _record_event(
        self,
        event_type: TideEvent,
        intensity: float,
        body_ids: List[str],
        zone_id: Optional[str],
        tide_delta: float,
    ) -> Dict[str, Any]:
        """Record a tidal event and return its dictionary form."""
        event = TideEventRecord(
            event_id=f"tide_{event_type.value}_{int(time.time() * 1000)}_{random.randint(0, 999)}",
            event_type=event_type,
            intensity=max(0.0, min(1.0, intensity)),
            body_ids=body_ids,
            zone_id=zone_id,
            tide_delta=tide_delta,
            timestamp=time.time(),
        )
        self._event_history.append(event)
        self._stats.total_events += 1
        if event_type == TideEvent.SPRING_TIDE:
            self._stats.total_spring_tides += 1
        elif event_type == TideEvent.NEAP_TIDE:
            self._stats.total_neap_tides += 1
        elif event_type == TideEvent.RIP_CURRENT:
            self._stats.total_rip_currents += 1
        elif event_type == TideEvent.MAELSTROM:
            self._stats.total_maelstroms += 1
        elif event_type == TideEvent.WAVE_CRASH:
            self._stats.total_wave_crashes += 1
        return self._event_to_dict(event)

    def get_events(
        self, zone_id: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent tidal events, optionally filtered by zone."""
        with self._lock:
            results = []
            for event in reversed(self._event_history):
                if zone_id is not None and event.zone_id != zone_id:
                    continue
                results.append(self._event_to_dict(event))
                if len(results) >= limit:
                    break
            return results

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
        """Get the overall status of the cognitive tide system."""
        with self._lock:
            return {
                "total_bodies": len(self._bodies),
                "total_zones": len(self._zones),
                "active": self._stats.active,
                "cycle_count": self._cycle_count,
                "stats": {
                    "total_events": self._stats.total_events,
                    "total_spring_tides": self._stats.total_spring_tides,
                    "total_neap_tides": self._stats.total_neap_tides,
                    "total_rip_currents": self._stats.total_rip_currents,
                    "total_maelstroms": self._stats.total_maelstroms,
                    "total_wave_crashes": self._stats.total_wave_crashes,
                    "avg_tide_level": round(self._stats.avg_tide_level, 4),
                    "avg_gravity": round(self._stats.avg_gravity, 4),
                    "last_cycle_time_ms": self._stats.last_cycle_time_ms,
                },
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the cognitive tide system to its initial state."""
        with self._lock:
            self._bodies.clear()
            self._zones.clear()
            self._event_history.clear()
            self._stats = CognitiveTideStats()
            self._cycle_count = 0
            self._active = False
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Serialization Helpers
    # -------------------------------------------------------------------------

    def _update_avg_metrics(self) -> None:
        """Update running average metrics."""
        if self._zones:
            total_tide = sum(z.current_tide for z in self._zones.values())
            self._stats.avg_tide_level = total_tide / len(self._zones)
        if self._bodies:
            total_grav = 0.0
            for body in self._bodies.values():
                if body.active:
                    total_grav += self.GRAVITATIONAL_CONSTANT * body.mass / (
                        body.orbital_distance ** 2
                    )
            self._stats.avg_gravity = total_grav / max(1, len(self._bodies))

    def _body_to_dict(self, body: CognitiveBody) -> Dict[str, Any]:
        return {
            "body_id": body.body_id,
            "body_type": body.body_type.value,
            "label": body.label,
            "mass": round(body.mass, 4),
            "orbital_distance": round(body.orbital_distance, 4),
            "orbital_angle": round(body.orbital_angle, 4),
            "orbital_velocity": round(body.orbital_velocity, 4),
            "active": body.active,
            "cycles_present": body.cycles_present,
            "gravity": round(
                self.GRAVITATIONAL_CONSTANT * body.mass / (body.orbital_distance ** 2),
                4,
            ),
            "last_updated": body.last_updated,
        }

    def _zone_to_dict(self, zone: TidalZone) -> Dict[str, Any]:
        return {
            "zone_id": zone.zone_id,
            "label": zone.label,
            "baseline_depth": round(zone.baseline_depth, 4),
            "current_tide": round(zone.current_tide, 4),
            "target_tide": round(zone.target_tide, 4),
            "tidal_amplitude": round(zone.tidal_amplitude, 4),
            "dominant_body_id": zone.dominant_body_id,
            "disturbed": zone.disturbed,
            "last_updated": zone.last_updated,
        }

    def _event_to_dict(self, event: TideEventRecord) -> Dict[str, Any]:
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "intensity": round(event.intensity, 4),
            "body_ids": event.body_ids,
            "zone_id": event.zone_id,
            "tide_delta": round(event.tide_delta, 4),
            "timestamp": event.timestamp,
        }
