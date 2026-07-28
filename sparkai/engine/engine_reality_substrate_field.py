"""
SparkLabs Engine - Reality Substrate Field

The EngineRealitySubstrateField is the foundational coherence layer beneath
all engine and cognition subsystems. Every subsystem (physics, narrative,
emotion, memory, etc.) plugs into the substrate as a "resonator" with a
natural frequency. The substrate measures how aligned these resonators are
and detects when the world falls into or out of coherence.

When subsystems are coherent, the world feels "real" - events cascade
smoothly between physics, emotion, and narrative. When coherence breaks
down, the substrate raises "reality stress" signals that directors can
respond to, preventing the world from feeling disjointed or arbitrary.

The substrate also propagates "reality pulses" - periodic waves that
synchronize subsystems. A pulse emitted by the narrative system can
trigger sympathetic resonance in emotion and physics, creating emergent
moments where everything in the world aligns around a single beat.

Architecture:
  COHERE     ->  RESONATE     ->  HARMONIZE     ->  STABILIZE   ->  DECOHERE
  (register      (emit and       (subsystems      (lock in          (allow
   resonators    propagate       align to a       coherent state    controlled
   and measure   pulses across   shared phase)    and damp noise)   drift to
   baseline)     substrate)                                       avoid rigidity)

Resonator properties:
  - frequency    : natural oscillation rate (rad/cycle)
  - amplitude    : current energy of the resonator (0.0-1.0)
  - phase        : current phase offset (0.0-2*pi)
  - damping      : how quickly the resonator loses energy
  - coupling     : how strongly it influences neighbors

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

class SubstratePhase(Enum):
    """Phases of the reality substrate cycle."""
    COHERE = "cohere"            # measure baseline coherence
    RESONATE = "resonate"        # emit and propagate pulses
    HARMONIZE = "harmonize"      # align subsystems to shared phase
    STABILIZE = "stabilize"      # damp noise and lock in coherence
    DECOHERE = "decohere"        # allow controlled drift


class ResonatorDomain(Enum):
    """The domain a resonator belongs to."""
    PHYSICS = "physics"
    NARRATIVE = "narrative"
    EMOTION = "emotion"
    MEMORY = "memory"
    SOCIAL = "social"
    ECONOMY = "economy"
    PERCEPTION = "perception"
    COGNITION = "cognition"
    CUSTOM = "custom"


class PulseType(Enum):
    """Types of reality pulses."""
    NARRATIVE_BEAT = "narrative_beat"      # story milestone
    EMOTIONAL_SURGE = "emotional_surge"    # collective feeling shift
    PHYSICS_SHOCK = "physics_shock"        # collision/explosion
    MEMORY_ECHO = "memory_echo"            # recalled event ripples
    COGNITIVE_RESONANCE = "cognitive_resonance"  # insight alignment
    AMBIENT_HUM = "ambient_hum"            # background world pulse


class CoherenceState(Enum):
    """Overall state of the substrate."""
    UNIFIED = "unified"          # all resonators in phase
    ALIGNED = "aligned"          # most resonators in phase
    DRIFTING = "drifting"        # partial coherence
    FRAGMENTED = "fragmented"    # subsystems out of sync
    CHAOTIC = "chaotic"          # no coherence at all


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Resonator:
    """A subsystem plugged into the reality substrate."""
    resonator_id: str
    domain: ResonatorDomain
    label: str
    frequency: float                    # rad/cycle
    amplitude: float = 0.5              # 0.0-1.0
    phase: float = 0.0                  # 0.0-2*pi
    damping: float = 0.05               # energy loss per cycle
    coupling: float = 0.3               # influence on neighbors
    pinned: bool = False                # if True, phase is locked
    last_pulse_emitted: float = 0.0
    last_pulse_received: float = 0.0


@dataclass
class RealityPulse:
    """A wave propagating across the substrate."""
    pulse_id: str
    pulse_type: PulseType
    origin_resonator_id: str
    amplitude: float
    frequency: float
    phase: float
    timestamp: float = field(default_factory=time.time)
    propagated_to: List[str] = field(default_factory=list)


@dataclass
class CoherenceLink:
    """A coupling link between two resonators."""
    source_id: str
    target_id: str
    strength: float                      # 0.0-1.0
    phase_offset: float = 0.0            # desired phase offset


@dataclass
class SubstrateEvent:
    """Recorded substrate event."""
    event_id: str
    event_type: str
    description: str
    resonator_ids: List[str] = field(default_factory=list)
    coherence_delta: float = 0.0
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Engine
# =============================================================================

class EngineRealitySubstrateField:
    """
    Thread-safe singleton orchestrating cross-subsystem coherence.

    Usage:
        substrate = EngineRealitySubstrateField.get_instance()
        substrate.register_resonator("combat", ResonatorDomain.PHYSICS, "Combat")
        substrate.register_resonator("story", ResonatorDomain.NARRATIVE, "Story")
        substrate.link_resonators("combat", "story", strength=0.4)
        substrate.emit_pulse("story", PulseType.NARRATIVE_BEAT, 0.8)
        substrate.cycle()
        status = substrate.get_status()
    """

    _instance: Optional["EngineRealitySubstrateField"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._resonators: Dict[str, Resonator] = {}
        self._links: Dict[Tuple[str, str], CoherenceLink] = {}
        self._pulses: Deque[RealityPulse] = deque(maxlen=100)
        self._events: Deque[SubstrateEvent] = deque(maxlen=200)
        self._phase: SubstratePhase = SubstratePhase.COHERE
        self._cycle_count: int = 0
        self._global_lock = threading.RLock()
        self._coherence_history: Deque[float] = deque(maxlen=100)
        self._stats = {
            "total_pulses_emitted": 0,
            "total_pulses_propagated": 0,
            "total_harmonizations": 0,
            "total_decoherences": 0,
            "avg_coherence": 0.0,
            "peak_coherence": 0.0,
            "trough_coherence": 1.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineRealitySubstrateField":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Resonator Management
    # -------------------------------------------------------------------------

    def register_resonator(
        self,
        resonator_id: str,
        domain: ResonatorDomain,
        label: str,
        frequency: float = 1.0,
        amplitude: float = 0.5,
        damping: float = 0.05,
        coupling: float = 0.3,
    ) -> Dict[str, Any]:
        """Register a new resonator in the substrate."""
        with self._global_lock:
            if resonator_id in self._resonators:
                return {"error": f"Resonator already registered: {resonator_id}"}
            resonator = Resonator(
                resonator_id=resonator_id,
                domain=domain,
                label=label,
                frequency=max(0.01, frequency),
                amplitude=max(0.0, min(1.0, amplitude)),
                phase=random.uniform(0.0, 2.0 * math.pi),
                damping=max(0.0, min(1.0, damping)),
                coupling=max(0.0, min(1.0, coupling)),
            )
            self._resonators[resonator_id] = resonator
            self._record_event(
                "resonator_registered",
                f"Resonator {label} ({domain.value}) joined substrate",
                [resonator_id],
            )
            return self._summarize_resonator(resonator)

    def remove_resonator(self, resonator_id: str) -> Dict[str, Any]:
        """Remove a resonator from the substrate."""
        with self._global_lock:
            if resonator_id not in self._resonators:
                return {"error": f"Resonator not found: {resonator_id}"}
            # Remove associated links
            to_remove = [
                (s, t) for (s, t) in self._links if s == resonator_id or t == resonator_id
            ]
            for key in to_remove:
                del self._links[key]
            del self._resonators[resonator_id]
            self._record_event(
                "resonator_removed",
                f"Resonator {resonator_id} left substrate",
                [resonator_id],
            )
            return {"removed": resonator_id}

    def list_resonators(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all resonators."""
        with self._global_lock:
            return [self._summarize_resonator(r) for r in list(self._resonators.values())[:limit]]

    def get_resonator(self, resonator_id: str) -> Optional[Dict[str, Any]]:
        """Get one resonator's details."""
        with self._global_lock:
            r = self._resonators.get(resonator_id)
            return self._summarize_resonator(r) if r else None

    # -------------------------------------------------------------------------
    # Linking
    # -------------------------------------------------------------------------

    def link_resonators(
        self,
        source_id: str,
        target_id: str,
        strength: float = 0.5,
        phase_offset: float = 0.0,
    ) -> Dict[str, Any]:
        """Create a coherence link between two resonators."""
        with self._global_lock:
            if source_id not in self._resonators:
                return {"error": f"Source resonator not found: {source_id}"}
            if target_id not in self._resonators:
                return {"error": f"Target resonator not found: {target_id}"}
            if source_id == target_id:
                return {"error": "Cannot link a resonator to itself"}
            key = (source_id, target_id)
            self._links[key] = CoherenceLink(
                source_id=source_id,
                target_id=target_id,
                strength=max(0.0, min(1.0, strength)),
                phase_offset=phase_offset,
            )
            self._record_event(
                "link_created",
                f"Linked {source_id} -> {target_id} (strength={strength:.2f})",
                [source_id, target_id],
            )
            return {
                "source_id": source_id,
                "target_id": target_id,
                "strength": self._links[key].strength,
                "phase_offset": self._links[key].phase_offset,
            }

    def unlink_resonators(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """Remove a coherence link."""
        with self._global_lock:
            key = (source_id, target_id)
            if key not in self._links:
                return {"error": f"Link not found: {source_id} -> {target_id}"}
            del self._links[key]
            self._record_event(
                "link_removed",
                f"Unlinked {source_id} -> {target_id}",
                [source_id, target_id],
            )
            return {"removed": f"{source_id}->{target_id}"}

    def list_links(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all coherence links."""
        with self._global_lock:
            return [
                {
                    "source_id": link.source_id,
                    "target_id": link.target_id,
                    "strength": link.strength,
                    "phase_offset": link.phase_offset,
                }
                for link in list(self._links.values())[:limit]
            ]

    # -------------------------------------------------------------------------
    # Pulse Emission
    # -------------------------------------------------------------------------

    def emit_pulse(
        self,
        origin_id: str,
        pulse_type: PulseType,
        amplitude: float = 0.5,
    ) -> Dict[str, Any]:
        """Emit a reality pulse from a resonator."""
        with self._global_lock:
            origin = self._resonators.get(origin_id)
            if origin is None:
                return {"error": f"Origin resonator not found: {origin_id}"}
            pulse = RealityPulse(
                pulse_id=f"pulse_{int(time.time()*1000)}_{random.randint(0,9999):04d}",
                pulse_type=pulse_type,
                origin_resonator_id=origin_id,
                amplitude=max(0.0, min(1.0, amplitude)),
                frequency=origin.frequency,
                phase=origin.phase,
            )
            self._pulses.append(pulse)
            origin.amplitude = min(1.0, origin.amplitude + amplitude * 0.3)
            origin.last_pulse_emitted = time.time()
            self._stats["total_pulses_emitted"] += 1
            self._record_event(
                "pulse_emitted",
                f"{pulse_type.value} pulse from {origin_id} (amp={amplitude:.2f})",
                [origin_id],
            )
            return {
                "pulse_id": pulse.pulse_id,
                "pulse_type": pulse.pulse_type.value,
                "origin": origin_id,
                "amplitude": pulse.amplitude,
            }

    def list_pulses(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List recent pulses."""
        with self._global_lock:
            return [
                {
                    "pulse_id": p.pulse_id,
                    "pulse_type": p.pulse_type.value,
                    "origin_resonator_id": p.origin_resonator_id,
                    "amplitude": p.amplitude,
                    "frequency": p.frequency,
                    "phase": p.phase,
                    "propagated_to": p.propagated_to,
                    "timestamp": p.timestamp,
                }
                for p in list(self._pulses)[-limit:]
            ]

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single substrate cycle through all phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            for phase in SubstratePhase:
                self._phase = phase
                phase_outputs[phase.value] = self._run_phase(phase)

            coherence = self._compute_coherence()
            self._coherence_history.append(coherence)
            self._stats["avg_coherence"] = (
                sum(self._coherence_history) / len(self._coherence_history)
            )
            self._stats["peak_coherence"] = max(self._stats["peak_coherence"], coherence)
            self._stats["trough_coherence"] = min(self._stats["trough_coherence"], coherence)
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._cycle_count += 1

            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "coherence": coherence,
                "coherence_state": self._coherence_state(coherence).value,
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
            "final_coherence": self._coherence_history[-1] if self._coherence_history else 0.0,
            "stats": dict(self._stats),
        }

    def _run_phase(self, phase: SubstratePhase) -> Dict[str, Any]:
        """Dispatch to phase handler."""
        handlers = {
            SubstratePhase.COHERE: self._phase_cohere,
            SubstratePhase.RESONATE: self._phase_resonate,
            SubstratePhase.HARMONIZE: self._phase_harmonize,
            SubstratePhase.STABILIZE: self._phase_stabilize,
            SubstratePhase.DECOHERE: self._phase_decohere,
        }
        handler = handlers.get(phase)
        return handler() if handler else {"error": f"Unknown phase: {phase}"}

    # -------------------------------------------------------------------------
    # Phase Implementations
    # -------------------------------------------------------------------------

    def _phase_cohere(self) -> Dict[str, Any]:
        """COHERE: advance resonator phases and apply damping."""
        advanced = 0
        for r in self._resonators.values():
            if r.pinned:
                continue
            r.phase = (r.phase + r.frequency * r.amplitude) % (2.0 * math.pi)
            r.amplitude = max(0.0, r.amplitude - r.damping * 0.1)
            advanced += 1
        return {"advanced": advanced}

    def _phase_resonate(self) -> Dict[str, Any]:
        """RESONATE: propagate active pulses through links."""
        propagated = 0
        active_pulses = list(self._pulses)
        for pulse in active_pulses:
            origin_id = pulse.origin_resonator_id
            for (src, tgt), link in self._links.items():
                if src != origin_id or tgt in pulse.propagated_to:
                    continue
                target = self._resonators.get(tgt)
                if target is None or target.pinned:
                    continue
                # Apply pulse influence
                target.amplitude = min(1.0, target.amplitude + pulse.amplitude * link.strength * 0.2)
                # Pull phase toward pulse phase
                phase_diff = (pulse.phase - target.phase + math.pi) % (2.0 * math.pi) - math.pi
                target.phase = (target.phase + phase_diff * link.strength * 0.3) % (2.0 * math.pi)
                target.last_pulse_received = time.time()
                pulse.propagated_to.append(tgt)
                propagated += 1
        self._stats["total_pulses_propagated"] += propagated
        return {"propagated": propagated}

    def _phase_harmonize(self) -> Dict[str, Any]:
        """HARMONIZE: pull linked resonators toward shared phase."""
        harmonizations = 0
        for (src_id, tgt_id), link in self._links.items():
            src = self._resonators.get(src_id)
            tgt = self._resonators.get(tgt_id)
            if src is None or tgt is None or tgt.pinned:
                continue
            desired_phase = (src.phase + link.phase_offset) % (2.0 * math.pi)
            phase_diff = (desired_phase - tgt.phase + math.pi) % (2.0 * math.pi) - math.pi
            if abs(phase_diff) > 0.01:
                tgt.phase = (tgt.phase + phase_diff * link.strength * 0.1) % (2.0 * math.pi)
                harmonizations += 1
        self._stats["total_harmonizations"] += harmonizations
        return {"harmonizations": harmonizations}

    def _phase_stabilize(self) -> Dict[str, Any]:
        """STABILIZE: damp excess amplitude noise."""
        stabilized = 0
        for r in self._resonators.values():
            if r.amplitude > 0.9:
                r.amplitude = 0.9
                stabilized += 1
            elif r.amplitude < 0.05:
                r.amplitude = 0.05
                stabilized += 1
        return {"stabilized": stabilized}

    def _phase_decohere(self) -> Dict[str, Any]:
        """DECOHERE: introduce tiny random phase drift to avoid rigidity."""
        drifted = 0
        for r in self._resonators.values():
            if r.pinned:
                continue
            r.phase = (r.phase + random.uniform(-0.05, 0.05)) % (2.0 * math.pi)
            drifted += 1
        self._stats["total_decoherences"] += 1
        return {"drifted": drifted}

    # -------------------------------------------------------------------------
    # Coherence Computation
    # -------------------------------------------------------------------------

    def _compute_coherence(self) -> float:
        """Compute global coherence (0.0-1.0)."""
        if not self._resonators:
            return 0.0
        # Average pairwise phase alignment weighted by link strength
        if not self._links:
            # Use uniform pairwise alignment
            res_list = list(self._resonators.values())
            if len(res_list) < 2:
                return 1.0
            total = 0.0
            count = 0
            for i in range(len(res_list)):
                for j in range(i + 1, len(res_list)):
                    phase_diff = abs(
                        (res_list[i].phase - res_list[j].phase + math.pi) % (2.0 * math.pi) - math.pi
                    )
                    total += 1.0 - (phase_diff / math.pi)
                    count += 1
            return total / count if count > 0 else 1.0
        total = 0.0
        weight_sum = 0.0
        for link in self._links.values():
            src = self._resonators.get(link.source_id)
            tgt = self._resonators.get(link.target_id)
            if src is None or tgt is None:
                continue
            phase_diff = abs(
                (src.phase - tgt.phase - link.phase_offset + math.pi) % (2.0 * math.pi) - math.pi
            )
            alignment = 1.0 - (phase_diff / math.pi)
            total += alignment * link.strength
            weight_sum += link.strength
        return total / weight_sum if weight_sum > 0 else 0.0

    def _coherence_state(self, coherence: float) -> CoherenceState:
        """Classify the coherence value."""
        if coherence >= 0.9:
            return CoherenceState.UNIFIED
        if coherence >= 0.7:
            return CoherenceState.ALIGNED
        if coherence >= 0.4:
            return CoherenceState.DRIFTING
        if coherence >= 0.2:
            return CoherenceState.FRAGMENTED
        return CoherenceState.CHAOTIC

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global substrate status."""
        with self._global_lock:
            coherence = self._compute_coherence()
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_resonators": len(self._resonators),
                "total_links": len(self._links),
                "active_pulses": len(self._pulses),
                "coherence": coherence,
                "coherence_state": self._coherence_state(coherence).value,
                "stats": dict(self._stats),
            }

    def get_coherence_history(self, limit: int = 50) -> List[float]:
        """Get recent coherence values."""
        with self._global_lock:
            return list(self._coherence_history)[-limit:]

    def get_domain_summary(self) -> Dict[str, Any]:
        """Get coherence summary grouped by domain."""
        with self._global_lock:
            domains: Dict[str, List[float]] = {}
            for r in self._resonators.values():
                domains.setdefault(r.domain.value, []).append(r.amplitude)
            return {
                domain: {
                    "resonator_count": len(amps),
                    "avg_amplitude": sum(amps) / len(amps) if amps else 0.0,
                }
                for domain, amps in domains.items()
            }

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent substrate events."""
        with self._global_lock:
            return [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "description": e.description,
                    "resonator_ids": e.resonator_ids,
                    "coherence_delta": e.coherence_delta,
                    "timestamp": e.timestamp,
                }
                for e in list(self._events)[-limit:]
            ]

    # -------------------------------------------------------------------------
    # Tuning
    # -------------------------------------------------------------------------

    def set_resonator_amplitude(self, resonator_id: str, amplitude: float) -> Dict[str, Any]:
        """Manually adjust a resonator's amplitude."""
        with self._global_lock:
            r = self._resonators.get(resonator_id)
            if r is None:
                return {"error": f"Resonator not found: {resonator_id}"}
            r.amplitude = max(0.0, min(1.0, amplitude))
            return {"resonator_id": resonator_id, "amplitude": r.amplitude}

    def pin_resonator(self, resonator_id: str, pinned: bool = True) -> Dict[str, Any]:
        """Pin or unpin a resonator's phase."""
        with self._global_lock:
            r = self._resonators.get(resonator_id)
            if r is None:
                return {"error": f"Resonator not found: {resonator_id}"}
            r.pinned = pinned
            return {"resonator_id": resonator_id, "pinned": r.pinned}

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire substrate."""
        with self._global_lock:
            n_res = len(self._resonators)
            self._resonators.clear()
            self._links.clear()
            self._pulses.clear()
            self._events.clear()
            self._coherence_history.clear()
            self._phase = SubstratePhase.COHERE
            self._cycle_count = 0
            self._stats = {
                "total_pulses_emitted": 0,
                "total_pulses_propagated": 0,
                "total_harmonizations": 0,
                "total_decoherences": 0,
                "avg_coherence": 0.0,
                "peak_coherence": 0.0,
                "trough_coherence": 1.0,
                "last_cycle_time_ms": 0.0,
            }
            self._record_event(
                "substrate_reset",
                f"Substrate reset (cleared {n_res} resonators)",
                [],
            )
            return {"reset": True, "cleared_resonators": n_res}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _summarize_resonator(self, r: Resonator) -> Dict[str, Any]:
        """Summarize a resonator for API output."""
        return {
            "resonator_id": r.resonator_id,
            "domain": r.domain.value,
            "label": r.label,
            "frequency": r.frequency,
            "amplitude": r.amplitude,
            "phase": r.phase,
            "damping": r.damping,
            "coupling": r.coupling,
            "pinned": r.pinned,
            "last_pulse_emitted": r.last_pulse_emitted,
            "last_pulse_received": r.last_pulse_received,
        }

    def _record_event(
        self,
        event_type: str,
        description: str,
        resonator_ids: List[str],
        coherence_delta: float = 0.0,
    ) -> None:
        """Record a substrate event."""
        self._events.append(SubstrateEvent(
            event_id=f"evt_{int(time.time()*1000)}_{random.randint(0,9999):04d}",
            event_type=event_type,
            description=description,
            resonator_ids=resonator_ids,
            coherence_delta=coherence_delta,
        ))
