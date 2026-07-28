"""
SparkLabs Engine - Mythic Resonance Chamber

The EngineMythicResonanceChamber is the deep pattern layer where archetypal
narrative structures resonate through the game world. Rather than scripting
stories, the chamber maintains a set of primordial archetypes (Hero, Shadow,
Mentor, Trickster, Threshold Guardian, etc.) that vibrate at different
frequencies depending on current gameplay events.

When player actions align with an archetype's pattern, that archetype's
resonance increases. As resonance builds, the archetype begins to influence
the world: the Shadow archetype might strengthen enemies, the Mentor might
reveal hidden knowledge, the Trickster might introduce chaos. This creates
emergent narrative meaning that arises naturally from gameplay rather than
from scripted plot points.

The chamber also detects when multiple archetypes are in tension (e.g., Hero
vs Shadow) and uses that tension to generate dramatic pressure. When tension
peaks, it crystallizes into a "mythic moment" - a gameplay beat where the
narrative significance is amplified.

Architecture:
  ATTUNE     ->  RESONATE     ->  AMPLIFY     ->  DISSOLVE    ->  CRYSTALLIZE
  (register     (feed events    (boost the      (let stale      (convert peak
   archetypes   into chamber    dominant        resonance        resonance into
   and set      and measure     archetype and    fade to keep     crystallized
   base freq)   resonance)      suppress)       flow)            mythic moments)

Archetype properties:
  - frequency     : base vibration rate (how quickly it responds)
  - resonance     : current activation level (0.0-1.0)
  - tension       : unresolved dramatic pressure (0.0-1.0)
  - polarity      : light (positive) / shadow (negative) / neutral
  - domain        : which gameplay domain it influences

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

class ChamberPhase(Enum):
    """Phases of the mythic resonance cycle."""
    ATTUNE = "attune"              # register and tune archetypes
    RESONATE = "resonate"          # feed events and measure resonance
    AMPLIFY = "amplify"            # boost dominant, suppress minor
    DISSOLVE = "dissolve"          # let stale resonance fade
    CRYSTALLIZE = "crystallize"    # convert peaks into mythic moments


class ArchetypePolarity(Enum):
    """Light/shadow alignment of an archetype."""
    LIGHT = "light"              # constructive, heroic, nurturing
    SHADOW = "shadow"            # destructive, antagonistic, challenging
    NEUTRAL = "neutral"          # transformative, ambiguous


class MythicEventType(Enum):
    """Types of events that feed the chamber."""
    VICTORY = "victory"            # triumph over challenge
    DEFEAT = "defeat"              # loss or failure
    SACRIFICE = "sacrifice"        # giving up something precious
    BETRAYAL = "betrayal"          # trust broken
    DISCOVERY = "discovery"        # new knowledge or territory
    TRANSFORMATION = "transformation"  # fundamental change
    ALLIANCE = "alliance"          # bonds forged
    SEPARATION = "separation"      # bonds broken
    CHALLENGE = "challenge"        # trial or test
    REVELATION = "revelation"      # hidden truth unveiled


class CrystallizationType(Enum):
    """Types of mythic moments that crystallize."""
    CALL_TO_ADVENTURE = "call_to_adventure"    # Hero resonance peaks
    DARK_NIGHT = "dark_night"                  # Shadow resonance peaks
    MENTOR_GIFT = "mentor_gift"                # Mentor resonance peaks
    TRICKSTER_CHAOS = "trickster_chaos"        # Trickster resonance peaks
    REBIRTH = "rebirth"                        # Transformation peaks
    SACRED_MARRIAGE = "sacred_marriage"        # Alliance + light peaks
    APOCALYPSE = "apocalypse"                   # Shadow + tension peaks
    ASCENSION = "ascension"                     # Light + revelation peaks


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Archetype:
    """A primordial narrative archetype."""
    archetype_id: str
    label: str
    polarity: ArchetypePolarity
    domain: str                   # gameplay domain (combat, social, etc.)
    frequency: float = 0.5        # how quickly it responds (0.0-1.0)
    resonance: float = 0.0        # current activation (0.0-1.0)
    tension: float = 0.0          # unresolved pressure (0.0-1.0)
    target_resonance: float = 0.0 # where resonance is heading
    excitations: int = 0          # how many times activated
    last_excited: float = 0.0
    description: str = ""


@dataclass
class MythicEvent:
    """An event fed into the chamber."""
    event_id: str
    event_type: MythicEventType
    source: str                   # who/what triggered it
    intensity: float = 0.5        # 0.0-1.0
    target_archetypes: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    description: str = ""


@dataclass
class ArchetypeTension:
    """Tension between two archetypes."""
    archetype_a: str
    archetype_b: str
    tension: float = 0.0          # 0.0-1.0
    last_peak: float = 0.0


@dataclass
class CrystallizedMoment:
    """A mythic moment that crystallized from peak resonance."""
    moment_id: str
    crystallization_type: CrystallizationType
    primary_archetype: str
    resonance_at_peak: float
    tension_at_peak: float
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    consumed: bool = False


# =============================================================================
# Engine
# =============================================================================

class EngineMythicResonanceChamber:
    """
    Thread-safe singleton orchestrating mythic archetype resonance.

    Usage:
        chamber = EngineMythicResonanceChamber.get_instance()
        chamber.register_archetype("hero", "Hero", ArchetypePolarity.LIGHT, "combat")
        chamber.register_archetype("shadow", "Shadow", ArchetypePolarity.SHADOW, "combat")
        chamber.feed_event("evt_1", MythicEventType.VICTORY, "player", 0.8, ["hero"])
        chamber.cycle()
        moments = chamber.get_crystallized_moments()
    """

    _instance: Optional["EngineMythicResonanceChamber"] = None
    _lock = threading.RLock()

    # Default archetype event affinities
    _EVENT_AFFINITY: Dict[MythicEventType, List[Tuple[str, float]]] = {
        MythicEventType.VICTORY: [("hero", 0.8), ("mentor", 0.3)],
        MythicEventType.DEFEAT: [("shadow", 0.7), ("threshold_guardian", 0.4)],
        MythicEventType.SACRIFICE: [("hero", 0.6), ("mentor", 0.5)],
        MythicEventType.BETRAYAL: [("trickster", 0.8), ("shadow", 0.6)],
        MythicEventType.DISCOVERY: [("mentor", 0.7), ("trickster", 0.3)],
        MythicEventType.TRANSFORMATION: [("shapeshifter", 0.8), ("mentor", 0.4)],
        MythicEventType.ALLIANCE: [("hero", 0.5), ("mentor", 0.5)],
        MythicEventType.SEPARATION: [("shadow", 0.5), ("trickster", 0.4)],
        MythicEventType.CHALLENGE: [("threshold_guardian", 0.8), ("hero", 0.4)],
        MythicEventType.REVELATION: [("mentor", 0.8), ("shapeshifter", 0.3)],
    }

    def __init__(self) -> None:
        self._archetypes: Dict[str, Archetype] = {}
        self._tensions: Dict[str, ArchetypeTension] = {}
        self._moments: Deque[CrystallizedMoment] = deque(maxlen=100)
        self._pending_events: Deque[MythicEvent] = deque(maxlen=200)
        self._phase: ChamberPhase = ChamberPhase.ATTUNE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_archetypes": 0,
            "total_events_fed": 0,
            "total_crystallizations": 0,
            "avg_resonance": 0.0,
            "max_resonance": 0.0,
            "total_tension": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineMythicResonanceChamber":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Archetype Registration
    # -------------------------------------------------------------------------

    def register_archetype(
        self,
        archetype_id: str,
        label: str,
        polarity: ArchetypePolarity,
        domain: str,
        frequency: float = 0.5,
        description: str = "",
    ) -> Dict[str, Any]:
        """Register a new archetype in the chamber."""
        with self._global_lock:
            if archetype_id in self._archetypes:
                return {"error": f"Archetype already registered: {archetype_id}"}
            archetype = Archetype(
                archetype_id=archetype_id,
                label=label,
                polarity=polarity,
                domain=domain,
                frequency=max(0.0, min(1.0, frequency)),
                description=description,
            )
            self._archetypes[archetype_id] = archetype
            self._stats["total_archetypes"] = len(self._archetypes)
            self._record_event("archetype_registered", {
                "archetype_id": archetype_id,
                "polarity": polarity.value,
                "domain": domain,
            })
            return {
                "archetype_id": archetype_id,
                "label": label,
                "polarity": polarity.value,
                "domain": domain,
                "frequency": archetype.frequency,
                "resonance": 0.0,
            }

    def remove_archetype(self, archetype_id: str) -> Dict[str, Any]:
        """Remove an archetype from the chamber."""
        with self._global_lock:
            if archetype_id not in self._archetypes:
                return {"error": f"Archetype not found: {archetype_id}"}
            del self._archetypes[archetype_id]
            # Clean up tensions
            to_remove = [
                k for k, t in self._tensions.items()
                if t.archetype_a == archetype_id or t.archetype_b == archetype_id
            ]
            for k in to_remove:
                del self._tensions[k]
            self._stats["total_archetypes"] = len(self._archetypes)
            return {"removed": archetype_id}

    def list_archetypes(self) -> List[Dict[str, Any]]:
        """List all registered archetypes."""
        with self._global_lock:
            return [self._summarize_archetype(a) for a in self._archetypes.values()]

    def get_archetype(self, archetype_id: str) -> Optional[Dict[str, Any]]:
        """Get details of one archetype."""
        with self._global_lock:
            a = self._archetypes.get(archetype_id)
            return self._summarize_archetype(a, full=True) if a else None

    # -------------------------------------------------------------------------
    # Tension Linking
    # -------------------------------------------------------------------------

    def link_archetypes(
        self,
        archetype_a: str,
        archetype_b: str,
        initial_tension: float = 0.0,
    ) -> Dict[str, Any]:
        """Link two archetypes in a tension relationship."""
        with self._global_lock:
            if archetype_a not in self._archetypes:
                return {"error": f"Archetype not found: {archetype_a}"}
            if archetype_b not in self._archetypes:
                return {"error": f"Archetype not found: {archetype_b}"}
            key = self._tension_key(archetype_a, archetype_b)
            if key in self._tensions:
                self._tensions[key].tension = max(0.0, min(1.0, initial_tension))
            else:
                self._tensions[key] = ArchetypeTension(
                    archetype_a=archetype_a,
                    archetype_b=archetype_b,
                    tension=max(0.0, min(1.0, initial_tension)),
                )
            return {
                "archetype_a": archetype_a,
                "archetype_b": archetype_b,
                "tension": self._tensions[key].tension,
            }

    def unlink_archetypes(self, archetype_a: str, archetype_b: str) -> Dict[str, Any]:
        """Remove a tension link between two archetypes."""
        with self._global_lock:
            key = self._tension_key(archetype_a, archetype_b)
            if key not in self._tensions:
                return {"error": f"Tension link not found: {archetype_a} <-> {archetype_b}"}
            del self._tensions[key]
            return {"unlinked": f"{archetype_a} <-> {archetype_b}"}

    def _tension_key(self, a: str, b: str) -> str:
        """Generate a canonical key for a tension pair."""
        return "|".join(sorted([a, b]))

    # -------------------------------------------------------------------------
    # Event Feeding
    # -------------------------------------------------------------------------

    def feed_event(
        self,
        event_id: str,
        event_type: MythicEventType,
        source: str,
        intensity: float = 0.5,
        target_archetypes: Optional[List[str]] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        """Feed a gameplay event into the chamber."""
        with self._global_lock:
            event = MythicEvent(
                event_id=event_id,
                event_type=event_type,
                source=source,
                intensity=max(0.0, min(1.0, intensity)),
                target_archetypes=target_archetypes or [],
                description=description,
            )
            self._pending_events.append(event)
            self._stats["total_events_fed"] += 1
            # Immediately apply resonance to target or affinity-mapped archetypes
            affected: List[str] = list(event.target_archetypes)
            if not affected:
                # Use affinity mapping
                for arch_id, boost in self._EVENT_AFFINITY.get(event_type, []):
                    if arch_id in self._archetypes:
                        affected.append(arch_id)
            for arch_id in affected:
                archetype = self._archetypes.get(arch_id)
                if archetype is None:
                    continue
                boost = event.intensity * archetype.frequency * 0.3
                archetype.target_resonance = min(1.0, archetype.target_resonance + boost)
                archetype.excitations += 1
                archetype.last_excited = time.time()
            self._record_event("event_fed", {
                "event_id": event_id,
                "event_type": event_type.value,
                "affected": affected,
            })
            return {
                "event_id": event_id,
                "event_type": event_type.value,
                "affected_archetypes": affected,
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single mythic resonance cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            # ATTUNE: settle target resonance toward current
            self._phase = ChamberPhase.ATTUNE
            phase_outputs["attune"] = self._phase_attune()
            # RESONATE: process pending events and move resonance toward target
            self._phase = ChamberPhase.RESONATE
            phase_outputs["resonate"] = self._phase_resonate()
            # AMPLIFY: boost dominant archetype, suppress minor
            self._phase = ChamberPhase.AMPLIFY
            phase_outputs["amplify"] = self._phase_amplify()
            # DISSOLVE: let stale resonance fade
            self._phase = ChamberPhase.DISSOLVE
            phase_outputs["dissolve"] = self._phase_dissolve()
            # CRYSTALLIZE: convert peaks into mythic moments
            self._phase = ChamberPhase.CRYSTALLIZE
            phase_outputs["crystallize"] = self._phase_crystallize()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles."""
        if cycles < 1 or cycles > 1000:
            return {"error": "cycles must be 1-1000"}
        for _ in range(cycles):
            self.cycle()
        return {
            "cycles_run": cycles,
            "final_phase": self._phase.value,
            "stats": dict(self._stats),
        }

    def _phase_attune(self) -> Dict[str, Any]:
        """ATTUNE: move resonance toward target gradually."""
        tuned = 0
        for archetype in self._archetypes.values():
            diff = archetype.target_resonance - archetype.resonance
            if abs(diff) < 0.01:
                continue
            archetype.resonance += diff * 0.3
            tuned += 1
        return {"tuned": tuned}

    def _phase_resonate(self) -> Dict[str, Any]:
        """RESONATE: update tensions based on resonance."""
        # Process pending events (already applied in feed_event, just clear)
        processed = len(self._pending_events)
        self._pending_events.clear()
        # Update tensions between linked archetypes
        for tension in self._tensions.values():
            a = self._archetypes.get(tension.archetype_a)
            b = self._archetypes.get(tension.archetype_b)
            if a is None or b is None:
                continue
            # Tension grows when both are resonating but have opposite polarity
            if a.polarity != b.polarity:
                conflict = min(a.resonance, b.resonance) * 0.15
                tension.tension = min(1.0, tension.tension + conflict)
            else:
                # Same polarity reduces tension
                tension.tension = max(0.0, tension.tension - 0.02)
        return {"events_processed": processed, "tensions_updated": len(self._tensions)}

    def _phase_amplify(self) -> Dict[str, Any]:
        """AMPLIFY: boost the dominant archetype, suppress others slightly."""
        if not self._archetypes:
            return {"amplified": 0, "suppressed": 0}
        dominant = max(self._archetypes.values(), key=lambda a: a.resonance)
        amplified = 0
        suppressed = 0
        for archetype in self._archetypes.values():
            if archetype.archetype_id == dominant.archetype_id:
                archetype.resonance = min(1.0, archetype.resonance + 0.05)
                amplified += 1
            else:
                archetype.resonance = max(0.0, archetype.resonance - 0.02)
                suppressed += 1
        return {"amplified": amplified, "suppressed": suppressed, "dominant": dominant.archetype_id}

    def _phase_dissolve(self) -> Dict[str, Any]:
        """DISSOLVE: let resonance and tension decay to maintain flow."""
        dissolved_resonance = 0
        dissolved_tension = 0
        for archetype in self._archetypes.values():
            decay = 0.03 * (1.0 - archetype.frequency)
            archetype.resonance = max(0.0, archetype.resonance - decay)
            archetype.target_resonance = max(0.0, archetype.target_resonance - decay * 0.5)
            if archetype.resonance > 0.01:
                dissolved_resonance += 1
        for tension in self._tensions.values():
            tension.tension = max(0.0, tension.tension - 0.05)
            if tension.tension > 0.01:
                dissolved_tension += 1
        return {"resonance_decayed": dissolved_resonance, "tension_decayed": dissolved_tension}

    def _phase_crystallize(self) -> Dict[str, Any]:
        """CRYSTALLIZE: convert peak resonance into mythic moments."""
        crystallized = 0
        for archetype in self._archetypes.values():
            if archetype.resonance < 0.7:
                continue
            # Determine crystallization type
            cryst_type = self._determine_crystallization(archetype)
            if cryst_type is None:
                continue
            # Check if we already have an unconsumed moment of this type
            has_existing = any(
                m.crystallization_type == cryst_type and not m.consumed
                for m in self._moments
            )
            if has_existing:
                continue
            # Find peak tension
            peak_tension = 0.0
            for t in self._tensions.values():
                if t.archetype_a == archetype.archetype_id or t.archetype_b == archetype.archetype_id:
                    peak_tension = max(peak_tension, t.tension)
            moment = CrystallizedMoment(
                moment_id=f"moment_{archetype.archetype_id}_{int(time.time() * 1000)}",
                crystallization_type=cryst_type,
                primary_archetype=archetype.archetype_id,
                resonance_at_peak=archetype.resonance,
                tension_at_peak=peak_tension,
                description=f"{cryst_type.value.replace('_', ' ').title()} triggered by {archetype.label}",
            )
            self._moments.append(moment)
            crystallized += 1
            self._stats["total_crystallizations"] += 1
            # Consume some resonance
            archetype.resonance *= 0.5
            archetype.target_resonance *= 0.5
            self._record_event("crystallized", {
                "moment_id": moment.moment_id,
                "type": cryst_type.value,
                "archetype": archetype.archetype_id,
                "resonance": moment.resonance_at_peak,
            })
        return {"crystallized": crystallized, "total_moments": len(self._moments)}

    def _determine_crystallization(self, archetype: Archetype) -> Optional[CrystallizationType]:
        """Determine what type of mythic moment to crystallize."""
        mapping = {
            "hero": CrystallizationType.CALL_TO_ADVENTURE,
            "shadow": CrystallizationType.DARK_NIGHT,
            "mentor": CrystallizationType.MENTOR_GIFT,
            "trickster": CrystallizationType.TRICKSTER_CHAOS,
            "shapeshifter": CrystallizationType.REBIRTH,
        }
        result = mapping.get(archetype.archetype_id)
        if result is not None:
            return result
        # Fall back to polarity-based mapping
        if archetype.polarity == ArchetypePolarity.LIGHT:
            return CrystallizationType.ASCENSION
        if archetype.polarity == ArchetypePolarity.SHADOW:
            return CrystallizationType.APOCALYPSE
        return CrystallizationType.REBIRTH

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global chamber status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_archetypes": len(self._archetypes),
                "total_tensions": len(self._tensions),
                "total_moments": len(self._moments),
                "stats": dict(self._stats),
            }

    def get_tensions(self) -> List[Dict[str, Any]]:
        """Get all tension relationships."""
        with self._global_lock:
            return [
                {
                    "archetype_a": t.archetype_a,
                    "archetype_b": t.archetype_b,
                    "tension": t.tension,
                    "last_peak": t.last_peak,
                }
                for t in self._tensions.values()
            ]

    def get_crystallized_moments(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get crystallized mythic moments."""
        with self._global_lock:
            return [
                {
                    "moment_id": m.moment_id,
                    "type": m.crystallization_type.value,
                    "primary_archetype": m.primary_archetype,
                    "resonance_at_peak": m.resonance_at_peak,
                    "tension_at_peak": m.tension_at_peak,
                    "timestamp": m.timestamp,
                    "description": m.description,
                    "consumed": m.consumed,
                }
                for m in list(self._moments)[-limit:]
            ]

    def consume_moment(self, moment_id: str) -> Dict[str, Any]:
        """Mark a crystallized moment as consumed."""
        with self._global_lock:
            for m in self._moments:
                if m.moment_id == moment_id:
                    m.consumed = True
                    return {"consumed": moment_id}
            return {"error": f"Moment not found: {moment_id}"}

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent chamber events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire chamber."""
        with self._global_lock:
            n = len(self._archetypes)
            self._archetypes.clear()
            self._tensions.clear()
            self._moments.clear()
            self._pending_events.clear()
            self._phase = ChamberPhase.ATTUNE
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = {
                "total_archetypes": 0,
                "total_events_fed": 0,
                "total_crystallizations": 0,
                "avg_resonance": 0.0,
                "max_resonance": 0.0,
                "total_tension": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            self._record_event("chamber_reset", {"cleared_archetypes": n})
            return {"reset": True, "cleared_archetypes": n}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _summarize_archetype(self, a: Archetype, full: bool = False) -> Dict[str, Any]:
        """Summarize an archetype for API output."""
        summary: Dict[str, Any] = {
            "archetype_id": a.archetype_id,
            "label": a.label,
            "polarity": a.polarity.value,
            "domain": a.domain,
            "frequency": a.frequency,
            "resonance": a.resonance,
            "target_resonance": a.target_resonance,
            "tension": a.tension,
            "excitations": a.excitations,
            "last_excited": a.last_excited,
        }
        if full:
            summary["description"] = a.description
        return summary

    def _update_stats(self) -> None:
        """Recompute aggregate statistics."""
        if not self._archetypes:
            self._stats["avg_resonance"] = 0.0
            self._stats["max_resonance"] = 0.0
            self._stats["total_tension"] = 0.0
            return
        resonances = [a.resonance for a in self._archetypes.values()]
        self._stats["avg_resonance"] = sum(resonances) / len(resonances)
        self._stats["max_resonance"] = max(resonances)
        self._stats["total_tension"] = sum(t.tension for t in self._tensions.values())

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a chamber event."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
