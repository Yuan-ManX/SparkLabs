"""
SparkLabs Engine - Quantum Entanglement Field

The EngineQuantumEntanglementField models engine state as a field of
quantum-entangled particles. Rather than treating game state as a
deterministic set of variables that change discretely, it treats state
as superpositions of possibilities that propagate correlations through
entanglement, collapse into definite outcomes when measured, and
decohere back into classical uncertainty over time.

This quantum metaphor captures how game state actually behaves in
living worlds: many outcomes coexist as possibilities until something
forces a decision. Changes do not stay local, they ripple through
entangled partners instantly. Decisions do not produce single outcomes,
they produce probability distributions. And entanglement does not last
forever, it decoheres as the world drifts back toward classical
behavior, requiring fresh entanglement to maintain coherence.

Core concepts:
  - PARTICLE     : a quantum state holder in the engine field
  - SUPERPOSITION: the probability amplitudes of possible states
  - ENTANGLEMENT : a coupling where measuring one particle affects another
  - COHERENCE    : how quantum-like the particle still is (0.0-1.0)
  - MEASUREMENT  : an observation that collapses superposition
  - DECOHERENCE  : the gradual loss of quantum properties over time

Particle types:
  QUBIT       : binary state particle, two-state superposition
  QUTRIT      : ternary state particle, three-state superposition
  OSCILLATOR  : wave-like particle, continuous phase superposition
  ENTANGLER   : coupling particle, mediates entanglement between others
  ANCHOR      : measurement anchor, stable particle that resists collapse

Quantum events:
  PARTICLE_BIRTH    : a new particle is added to the field
  SUPERPOSITION_SET : a particle's superposition amplitudes are configured
  ENTANGLEMENT_FORM : two particles become entangled
  MEASUREMENT_EVENT : a particle is measured, collapsing its superposition
  COLLAPSE_PROPAGATE: a collapse propagates to entangled partners
  DECOHERENCE_DECAY : a particle loses coherence over time
  FIELD_RECOHERE    : the field re-establishes coherence through entanglement

Architecture:
  SUPERPOSE  ->  ENTANGLE  ->  MEASURE  ->  COLLAPSE  ->  DECOHERE
  (particles   (particles    (observing  (collapsed    (coherence
   prepare     become         forces a    state         decays back
   their       entangled      definite    propagates    toward
   states)     through        outcome)    to partners)  classical
               coupling)                                uncertainty)

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

class ParticleType(Enum):
    """Types of quantum particles in the entanglement field."""
    QUBIT = "qubit"          # binary state, two-state superposition
    QUTRIT = "qutrit"        # ternary state, three-state superposition
    OSCILLATOR = "oscillator"  # wave-like, continuous phase
    ENTANGLER = "entangler"  # coupling mediator
    ANCHOR = "anchor"        # stable measurement anchor


class QuantumPhase(Enum):
    """Phases of the quantum entanglement cycle."""
    SUPERPOSE = "superpose"
    ENTANGLE = "entangle"
    MEASURE = "measure"
    COLLAPSE = "collapse"
    DECOHERE = "decohere"


class QuantumEvent(Enum):
    """Events that occur during the quantum cycle."""
    PARTICLE_BIRTH = "particle_birth"
    SUPERPOSITION_SET = "superposition_set"
    ENTANGLEMENT_FORM = "entanglement_form"
    MEASUREMENT_EVENT = "measurement_event"
    COLLAPSE_PROPAGATE = "collapse_propagate"
    DECOHERENCE_DECAY = "decoherence_decay"
    FIELD_RECOHERE = "field_recohere"


# =============================================================================
# Default Parameters by Particle Type
# =============================================================================

# Default coherence for each particle type
DEFAULT_PARTICLE_COHERENCE: Dict[ParticleType, float] = {
    ParticleType.QUBIT: 0.85,
    ParticleType.QUTRIT: 0.75,
    ParticleType.OSCILLATOR: 0.7,
    ParticleType.ENTANGLER: 0.95,
    ParticleType.ANCHOR: 0.99,
}

# Default number of basis states for each particle type
DEFAULT_PARTICLE_STATES: Dict[ParticleType, int] = {
    ParticleType.QUBIT: 2,
    ParticleType.QUTRIT: 3,
    ParticleType.OSCILLATOR: 4,
    ParticleType.ENTANGLER: 2,
    ParticleType.ANCHOR: 1,
}

# Default decoherence rate for each particle type
DEFAULT_PARTICLE_DECOHERE: Dict[ParticleType, float] = {
    ParticleType.QUBIT: 0.05,
    ParticleType.QUTRIT: 0.07,
    ParticleType.OSCILLATOR: 0.10,
    ParticleType.ENTANGLER: 0.02,
    ParticleType.ANCHOR: 0.005,
}

# Default entanglement affinity for each particle type
DEFAULT_PARTICLE_AFFINITY: Dict[ParticleType, float] = {
    ParticleType.QUBIT: 0.6,
    ParticleType.QUTRIT: 0.5,
    ParticleType.OSCILLATOR: 0.4,
    ParticleType.ENTANGLER: 0.95,
    ParticleType.ANCHOR: 0.2,
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class QuantumParticle:
    """A quantum particle in the entanglement field."""
    particle_id: str
    label: str
    particle_type: ParticleType
    # Number of basis states in the superposition
    state_count: int
    # Probability amplitudes for each basis state (normalized to sum=1.0)
    amplitudes: List[float]
    # Current coherence (0.0 = fully classical, 1.0 = fully quantum)
    coherence: float
    # Decoherence rate per cycle
    decohere_rate: float
    # Affinity for forming entanglements
    entanglement_affinity: float
    # Current collapsed state index (None if still in superposition)
    collapsed_state: Optional[int] = None
    # Whether this particle has been measured
    measured: bool = False
    # Number of entanglements this particle participates in
    entanglement_count: int = 0
    # Number of times this particle has been measured
    measurement_count: int = 0
    age_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class EntanglementLink:
    """A quantum entanglement between two particles."""
    link_id: str
    particle_a_id: str
    particle_b_id: str
    # Strength of the entanglement correlation (0.0-1.0)
    correlation: float
    # Whether the entanglement has been broken by measurement
    broken: bool = False
    # Phase relationship: "in_phase" or "anti_phase"
    phase_relation: str = "in_phase"
    timestamp: float = field(default_factory=time.time)


@dataclass
class MeasurementRecord:
    """A recorded measurement event that collapsed a superposition."""
    measurement_id: str
    particle_id: str
    # The state that was observed
    observed_state: int
    # The probability that was assigned to this state before measurement
    observed_probability: float
    # Whether this measurement propagated to entangled partners
    propagated: bool = False
    # Number of partners affected by propagation
    partners_affected: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class QuantumStats:
    """Aggregate statistics for the quantum entanglement field."""
    total_particles: int = 0
    total_entanglements: int = 0
    total_measurements: int = 0
    total_events: int = 0
    total_particle_births: int = 0
    total_superpositions_set: int = 0
    total_entanglements_formed: int = 0
    total_measurements_made: int = 0
    total_collapses_propagated: int = 0
    total_decoherence_decays: int = 0
    total_field_recoheres: int = 0
    avg_coherence: float = 0.0
    avg_entanglement_count: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Engine Quantum Entanglement Field
# =============================================================================

class EngineQuantumEntanglementField:
    """
    Singleton engine subsystem that models game state as a field of
    quantum-entangled particles. Particles prepare superpositions of
    possible states, become entangled through coupling, collapse into
    definite outcomes when measured, propagate collapses to entangled
    partners, and decohere back toward classical uncertainty over time.

    The field runs a 5-phase cycle:
      1. SUPERPOSE  - Particles prepare their superposition amplitudes
      2. ENTANGLE   - Particles form entanglement links with compatible partners
      3. MEASURE    - Particles are observed, collapsing to definite states
      4. COLLAPSE   - Collapsed states propagate to entangled partners
      5. DECOHERE   - Coherence decays, returning particles toward classical

    The quantum metaphor ensures game state feels alive: possibilities
    coexist until observed, correlations ripple instantly through
    entanglement, and coherence requires active maintenance.
    """

    _instance: Optional["EngineQuantumEntanglementField"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_PARTICLES = 100
    MAX_ENTANGLEMENTS = 200
    MAX_MEASUREMENTS = 100
    MAX_EVENT_HISTORY = 200
    # Coherence bounds
    MIN_COHERENCE = 0.0
    MAX_COHERENCE = 1.0
    # Amplitude bounds
    MIN_AMPLITUDE = 0.0
    MAX_AMPLITUDE = 1.0
    # Correlation bounds
    MIN_CORRELATION = 0.0
    MAX_CORRELATION = 1.0
    # Affinity bounds
    MIN_AFFINITY = 0.0
    MAX_AFFINITY = 1.0
    # Probability of spontaneous measurement per cycle
    SPONTANEOUS_MEASUREMENT_PROBABILITY = 0.10
    # Minimum correlation to maintain an entanglement
    ENTANGLEMENT_MIN_CORRELATION = 0.3
    # Entanglement formation probability for compatible pairs
    ENTANGLEMENT_FORM_PROBABILITY = 0.25
    # Minimum affinity similarity for entanglement
    ENTANGLEMENT_AFFINITY_THRESHOLD = 0.4
    # Coherence gain when entangled (mutual reinforcement)
    ENTANGLEMENT_COHERENCE_GAIN = 0.03
    # Maximum entanglements per particle
    MAX_ENTANGLEMENTS_PER_PARTICLE = 5
    # Decoherence rate multiplier when isolated
    ISOLATED_DECOHERE_MULTIPLIER = 1.5
    # Field recohere probability (entangled particles reinforce each other)
    FIELD_RECOHERE_PROBABILITY = 0.30

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._particles: Dict[str, QuantumParticle] = {}
        self._entanglements: Deque[EntanglementLink] = deque(maxlen=self.MAX_ENTANGLEMENTS)
        self._measurements: Deque[MeasurementRecord] = deque(maxlen=self.MAX_MEASUREMENTS)
        self._event_history: Deque[Dict[str, Any]] = deque(
            maxlen=self.MAX_EVENT_HISTORY
        )
        self._stats = QuantumStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._entanglement_counter: int = 0
        self._measurement_counter: int = 0
        self._event_counter: int = 0

    @classmethod
    def get_instance(cls) -> "EngineQuantumEntanglementField":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Particle Management
    # -------------------------------------------------------------------------

    def register_particle(
        self,
        particle_id: str,
        label: str,
        particle_type: str = "qubit",
        state_count: Optional[int] = None,
        amplitudes: Optional[List[float]] = None,
        coherence: Optional[float] = None,
        decohere_rate: Optional[float] = None,
        entanglement_affinity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a new quantum particle in the field."""
        with self._lock:
            if particle_id in self._particles:
                return {"error": f"Particle already registered: {particle_id}"}
            if len(self._particles) >= self.MAX_PARTICLES:
                return {"error": "Maximum particles reached"}

            try:
                ptype = ParticleType(particle_type)
            except ValueError:
                return {"error": f"Unknown particle type: {particle_type}"}

            if state_count is None:
                state_count = DEFAULT_PARTICLE_STATES.get(ptype, 2)
            state_count = max(1, min(8, int(state_count)))

            if amplitudes is None:
                # Uniform superposition
                amplitudes = [1.0 / state_count] * state_count
            else:
                if len(amplitudes) != state_count:
                    return {"error": f"amplitudes must have {state_count} elements"}
                amplitudes = [max(self.MIN_AMPLITUDE, float(a)) for a in amplitudes]
                # Normalize
                total = sum(amplitudes)
                if total <= 0:
                    amplitudes = [1.0 / state_count] * state_count
                else:
                    amplitudes = [a / total for a in amplitudes]

            if coherence is None:
                coherence = DEFAULT_PARTICLE_COHERENCE.get(ptype, 0.7)
            coherence = max(self.MIN_COHERENCE, min(self.MAX_COHERENCE, float(coherence)))

            if decohere_rate is None:
                decohere_rate = DEFAULT_PARTICLE_DECOHERE.get(ptype, 0.05)
            decohere_rate = max(0.0, min(0.5, float(decohere_rate)))

            if entanglement_affinity is None:
                entanglement_affinity = DEFAULT_PARTICLE_AFFINITY.get(ptype, 0.5)
            entanglement_affinity = max(
                self.MIN_AFFINITY, min(self.MAX_AFFINITY, float(entanglement_affinity))
            )

            particle = QuantumParticle(
                particle_id=particle_id,
                label=label,
                particle_type=ptype,
                state_count=state_count,
                amplitudes=amplitudes,
                coherence=coherence,
                decohere_rate=decohere_rate,
                entanglement_affinity=entanglement_affinity,
            )
            self._particles[particle_id] = particle
            self._stats.total_particles = len(self._particles)
            self._record_event(
                QuantumEvent.PARTICLE_BIRTH,
                intensity=coherence,
                particle_ids=[particle_id],
                description=f"Particle '{label}' ({ptype.value}) added to field",
            )
            return self._particle_to_dict(particle)

    def get_particle(self, particle_id: str) -> Dict[str, Any]:
        """Get the state of a specific quantum particle."""
        with self._lock:
            particle = self._particles.get(particle_id)
            if particle is None:
                return {"error": f"Particle not found: {particle_id}"}
            return self._particle_to_dict(particle)

    def list_particles(
        self, particle_type: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """List particles, optionally filtered by particle type."""
        with self._lock:
            particles = list(self._particles.values())
            if particle_type:
                try:
                    ptype = ParticleType(particle_type)
                    particles = [p for p in particles if p.particle_type == ptype]
                except ValueError:
                    return []
            particles = particles[:limit]
            return [self._particle_to_dict(p) for p in particles]

    def remove_particle(self, particle_id: str) -> Dict[str, Any]:
        """Remove a particle from the field."""
        with self._lock:
            if particle_id not in self._particles:
                return {"removed": False, "particle_id": particle_id}
            # Remove entanglements referencing this particle
            self._entanglements = deque(
                (e for e in self._entanglements
                 if e.particle_a_id != particle_id and e.particle_b_id != particle_id),
                maxlen=self.MAX_ENTANGLEMENTS,
            )
            del self._particles[particle_id]
            self._stats.total_particles = len(self._particles)
            self._stats.total_entanglements = len(self._entanglements)
            return {"removed": True, "particle_id": particle_id}

    def set_particle_amplitudes(
        self, particle_id: str, amplitudes: List[float], description: str = ""
    ) -> Dict[str, Any]:
        """Set the superposition amplitudes of a particle."""
        with self._lock:
            particle = self._particles.get(particle_id)
            if particle is None:
                return {"error": f"Particle not found: {particle_id}"}
            if len(amplitudes) != particle.state_count:
                return {"error": f"amplitudes must have {particle.state_count} elements"}
            amplitudes = [max(self.MIN_AMPLITUDE, float(a)) for a in amplitudes]
            total = sum(amplitudes)
            if total <= 0:
                return {"error": "amplitudes must sum to a positive value"}
            amplitudes = [a / total for a in amplitudes]
            particle.amplitudes = amplitudes
            # Setting amplitudes restores the particle to superposition
            particle.collapsed_state = None
            particle.measured = False
            self._record_event(
                QuantumEvent.SUPERPOSITION_SET,
                intensity=particle.coherence,
                particle_ids=[particle_id],
                description=f"Superposition set for '{particle.label}': {description}",
            )
            return {
                "particle_id": particle_id,
                "amplitudes": [round(a, 4) for a in particle.amplitudes],
                "description": description,
            }

    def measure_particle(
        self, particle_id: str, force_state: Optional[int] = None
    ) -> Dict[str, Any]:
        """Measure a particle, collapsing its superposition into a definite state."""
        with self._lock:
            particle = self._particles.get(particle_id)
            if particle is None:
                return {"error": f"Particle not found: {particle_id}"}

            if force_state is not None:
                if force_state < 0 or force_state >= particle.state_count:
                    return {"error": f"force_state must be in [0, {particle.state_count - 1}]"}
                observed = force_state
                observed_prob = particle.amplitudes[force_state]
            else:
                # Weighted random selection based on amplitudes
                r = random.random()
                cumulative = 0.0
                observed = 0
                observed_prob = particle.amplitudes[0]
                for i, amp in enumerate(particle.amplitudes):
                    cumulative += amp
                    if r <= cumulative:
                        observed = i
                        observed_prob = amp
                        break

            self._measurement_counter += 1
            measurement = MeasurementRecord(
                measurement_id=f"meas_{self._measurement_counter}",
                particle_id=particle_id,
                observed_state=observed,
                observed_probability=observed_prob,
            )
            self._measurements.append(measurement)

            # Collapse the particle
            particle.collapsed_state = observed
            particle.measured = True
            particle.measurement_count += 1
            # Collapse reduces coherence
            particle.coherence = max(self.MIN_COHERENCE, particle.coherence * 0.7)

            self._record_event(
                QuantumEvent.MEASUREMENT_EVENT,
                intensity=observed_prob,
                particle_ids=[particle_id],
                description=f"Particle '{particle.label}' measured -> state {observed} (p={observed_prob:.3f})",
            )

            return {
                "particle_id": particle_id,
                "observed_state": observed,
                "observed_probability": round(observed_prob, 4),
                "measurement_id": measurement.measurement_id,
            }

    # -------------------------------------------------------------------------
    # Entanglement Management
    # -------------------------------------------------------------------------

    def register_entanglement(
        self,
        particle_a_id: str,
        particle_b_id: str,
        correlation: Optional[float] = None,
        phase_relation: str = "in_phase",
    ) -> Dict[str, Any]:
        """Register an entanglement between two particles."""
        with self._lock:
            if particle_a_id not in self._particles:
                return {"error": f"Particle not found: {particle_a_id}"}
            if particle_b_id not in self._particles:
                return {"error": f"Particle not found: {particle_b_id}"}
            if particle_a_id == particle_b_id:
                return {"error": "Cannot entangle a particle with itself"}

            pa = self._particles[particle_a_id]
            pb = self._particles[particle_b_id]

            # Check entanglement count limits
            if pa.entanglement_count >= self.MAX_ENTANGLEMENTS_PER_PARTICLE:
                return {"error": f"Particle {particle_a_id} at max entanglements"}
            if pb.entanglement_count >= self.MAX_ENTANGLEMENTS_PER_PARTICLE:
                return {"error": f"Particle {particle_b_id} at max entanglements"}

            # Check for duplicate
            for e in self._entanglements:
                if ((e.particle_a_id == particle_a_id and e.particle_b_id == particle_b_id)
                        or (e.particle_a_id == particle_b_id and e.particle_b_id == particle_a_id)):
                    if not e.broken:
                        return {"error": "Entanglement already exists"}

            if correlation is None:
                correlation = (pa.entanglement_affinity + pb.entanglement_affinity) / 2
            correlation = max(self.MIN_CORRELATION, min(self.MAX_CORRELATION, float(correlation)))

            if phase_relation not in ("in_phase", "anti_phase"):
                phase_relation = "in_phase"

            self._entanglement_counter += 1
            link = EntanglementLink(
                link_id=f"ent_{self._entanglement_counter}",
                particle_a_id=particle_a_id,
                particle_b_id=particle_b_id,
                correlation=correlation,
                phase_relation=phase_relation,
            )
            self._entanglements.append(link)
            pa.entanglement_count += 1
            pb.entanglement_count += 1

            self._record_event(
                QuantumEvent.ENTANGLEMENT_FORM,
                intensity=correlation,
                particle_ids=[particle_a_id, particle_b_id],
                description=f"Entanglement formed: '{pa.label}' <-> '{pb.label}' (corr={correlation:.3f})",
            )

            return self._entanglement_to_dict(link)

    def list_entanglements(
        self, particle_id: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """List entanglement links, optionally filtered by particle."""
        with self._lock:
            links = list(self._entanglements)
            if particle_id:
                links = [
                    e for e in links
                    if e.particle_a_id == particle_id or e.particle_b_id == particle_id
                ]
            links = links[:limit]
            return [self._entanglement_to_dict(e) for e in links]

    def get_entanglement(self, link_id: str) -> Dict[str, Any]:
        """Get a specific entanglement link."""
        with self._lock:
            for e in self._entanglements:
                if e.link_id == link_id:
                    return self._entanglement_to_dict(e)
            return {"error": f"Entanglement not found: {link_id}"}

    def remove_entanglement(self, link_id: str) -> Dict[str, Any]:
        """Remove an entanglement link."""
        with self._lock:
            target = None
            for e in self._entanglements:
                if e.link_id == link_id:
                    target = e
                    break
            if target is None:
                return {"removed": False, "link_id": link_id}
            # Decrement entanglement counts
            pa = self._particles.get(target.particle_a_id)
            pb = self._particles.get(target.particle_b_id)
            if pa:
                pa.entanglement_count = max(0, pa.entanglement_count - 1)
            if pb:
                pb.entanglement_count = max(0, pb.entanglement_count - 1)
            self._entanglements = deque(
                (e for e in self._entanglements if e.link_id != link_id),
                maxlen=self.MAX_ENTANGLEMENTS,
            )
            return {"removed": True, "link_id": link_id}

    def set_entanglement_correlation(
        self, link_id: str, correlation: float, description: str = ""
    ) -> Dict[str, Any]:
        """Set the correlation strength of an entanglement link."""
        with self._lock:
            for e in self._entanglements:
                if e.link_id == link_id:
                    correlation = max(
                        self.MIN_CORRELATION, min(self.MAX_CORRELATION, float(correlation))
                    )
                    e.correlation = correlation
                    return {
                        "link_id": link_id,
                        "correlation": round(correlation, 4),
                        "description": description,
                    }
            return {"error": f"Entanglement not found: {link_id}"}

    # -------------------------------------------------------------------------
    # Measurement Management
    # -------------------------------------------------------------------------

    def list_measurements(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List recorded measurement events."""
        with self._lock:
            measurements = list(self._measurements)[:limit]
            return [self._measurement_to_dict(m) for m in measurements]

    def get_measurement(self, measurement_id: str) -> Dict[str, Any]:
        """Get a specific measurement record."""
        with self._lock:
            for m in self._measurements:
                if m.measurement_id == measurement_id:
                    return self._measurement_to_dict(m)
            return {"error": f"Measurement not found: {measurement_id}"}

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single quantum entanglement cycle.

        Phases: SUPERPOSE -> ENTANGLE -> MEASURE -> COLLAPSE -> DECOHERE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: SUPERPOSE - particles prepare their states
            superpose_info = self._superpose_phase()

            # Phase 2: ENTANGLE - particles form entanglement links
            entangle_info = self._entangle_phase()

            # Phase 3: MEASURE - particles are observed
            measure_info = self._measure_phase()

            # Phase 4: COLLAPSE - collapsed states propagate
            collapse_info = self._collapse_phase()

            # Phase 5: DECOHERE - coherence decays
            decohere_info = self._decohere_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            phase = QuantumPhase.DECOHERE
            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "superpose": superpose_info,
                "entangle": entangle_info,
                "measure": measure_info,
                "collapse": collapse_info,
                "decohere": decohere_info,
                "total_particles": len(self._particles),
                "total_entanglements": len(self._entanglements),
                "total_measurements": len(self._measurements),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _superpose_phase(self) -> Dict[str, Any]:
        """Phase 1: Particles prepare their superposition amplitudes."""
        superpositions_set = 0
        for particle in self._particles.values():
            particle.age_cycles += 1
            # Reset collapsed particles back to superposition if coherence is high enough
            if particle.measured and particle.coherence > 0.5:
                # Restore to a new superposition centered on the collapsed state
                base_amp = 0.6
                remaining = 1.0 - base_amp
                other_amp = remaining / max(1, particle.state_count - 1)
                new_amps = [other_amp] * particle.state_count
                if 0 <= particle.collapsed_state < particle.state_count:
                    new_amps[particle.collapsed_state] = base_amp
                particle.amplitudes = new_amps
                particle.collapsed_state = None
                particle.measured = False
                superpositions_set += 1

            # Coherent particles' amplitudes drift slightly (quantum fluctuation)
            if not particle.measured and particle.coherence > 0.3:
                fluctuation = 0.03 * particle.coherence
                new_amps = []
                for amp in particle.amplitudes:
                    delta = random.uniform(-fluctuation, fluctuation)
                    new_amps.append(max(0.0, amp + delta))
                total = sum(new_amps)
                if total > 0:
                    particle.amplitudes = [a / total for a in new_amps]

        self._stats.total_superpositions_set += superpositions_set
        return {
            "superpositions_set": superpositions_set,
            "particles_in_superposition": sum(
                1 for p in self._particles.values() if not p.measured
            ),
        }

    def _entangle_phase(self) -> Dict[str, Any]:
        """Phase 2: Particles form entanglement links with compatible partners."""
        entanglements_formed = 0
        recohered = 0

        particle_list = list(self._particles.values())
        for i in range(len(particle_list)):
            for j in range(i + 1, len(particle_list)):
                pa = particle_list[i]
                pb = particle_list[j]
                if (pa.entanglement_count >= self.MAX_ENTANGLEMENTS_PER_PARTICLE
                        or pb.entanglement_count >= self.MAX_ENTANGLEMENTS_PER_PARTICLE):
                    continue
                # Check if already entangled
                already = False
                for e in self._entanglements:
                    if e.broken:
                        continue
                    if ((e.particle_a_id == pa.particle_id and e.particle_b_id == pb.particle_id)
                            or (e.particle_a_id == pb.particle_id and e.particle_b_id == pa.particle_id)):
                        already = True
                        break
                if already:
                    continue

                # Affinity similarity check
                affinity_diff = abs(pa.entanglement_affinity - pb.entanglement_affinity)
                if (affinity_diff < self.ENTANGLEMENT_AFFINITY_THRESHOLD
                        and random.random() < self.ENTANGLEMENT_FORM_PROBABILITY):
                    result = self.register_entanglement(
                        pa.particle_id, pb.particle_id,
                        phase_relation=random.choice(["in_phase", "anti_phase"]),
                    )
                    if "error" not in result:
                        entanglements_formed += 1

        # Mutual reinforcement: entangled particles gain coherence
        for e in self._entanglements:
            if e.broken:
                continue
            pa = self._particles.get(e.particle_a_id)
            pb = self._particles.get(e.particle_b_id)
            if pa and pb and e.correlation > self.ENTANGLEMENT_MIN_CORRELATION:
                gain = self.ENTANGLEMENT_COHERENCE_GAIN * e.correlation
                pa.coherence = min(self.MAX_COHERENCE, pa.coherence + gain)
                pb.coherence = min(self.MAX_COHERENCE, pb.coherence + gain)
                if random.random() < self.FIELD_RECOHERE_PROBABILITY * 0.1:
                    recohered += 1

        if recohered > 0:
            self._record_event(
                QuantumEvent.FIELD_RECOHERE,
                intensity=0.5,
                particle_ids=[],
                description=f"Field recohered {recohered} particle pairs",
            )

        self._stats.total_entanglements_formed += entanglements_formed
        self._stats.total_field_recoheres += recohered
        return {
            "entanglements_formed": entanglements_formed,
            "recohered_pairs": recohered,
        }

    def _measure_phase(self) -> Dict[str, Any]:
        """Phase 3: Particles are observed, collapsing to definite states."""
        measurements_made = 0
        for particle in self._particles.values():
            if particle.measured:
                continue
            # Spontaneous measurement
            if random.random() < self.SPONTANEOUS_MEASUREMENT_PROBABILITY:
                result = self.measure_particle(particle.particle_id)
                if "error" not in result:
                    measurements_made += 1

        self._stats.total_measurements_made += measurements_made
        return {
            "measurements_made": measurements_made,
        }

    def _collapse_phase(self) -> Dict[str, Any]:
        """Phase 4: Collapsed states propagate to entangled partners."""
        propagations = 0
        # Iterate over a snapshot because measure_particle() below appends new
        # measurement records to self._measurements, which would otherwise
        # raise "deque mutated during iteration".
        for measurement in list(self._measurements):
            if measurement.propagated:
                continue
            # Find entangled partners of the measured particle
            partners = []
            for e in self._entanglements:
                if e.broken:
                    continue
                if e.particle_a_id == measurement.particle_id:
                    partners.append((e.particle_b_id, e))
                elif e.particle_b_id == measurement.particle_id:
                    partners.append((e.particle_a_id, e))

            affected = 0
            source_particle = self._particles.get(measurement.particle_id)
            if source_particle is None:
                continue

            for partner_id, link in partners:
                partner = self._particles.get(partner_id)
                if partner is None or partner.measured:
                    continue

                # Propagate the collapse based on correlation and phase relation
                if link.phase_relation == "anti_phase":
                    # Anti-correlated: partner collapses to a different state
                    if source_particle.collapsed_state is not None:
                        # Pick a different state
                        other_states = [
                            s for s in range(partner.state_count)
                            if s != source_particle.collapsed_state
                        ]
                        if other_states:
                            forced = random.choice(other_states)
                        else:
                            forced = source_particle.collapsed_state
                    else:
                        forced = None
                else:
                    # In-phase: partner collapses to the same state (if compatible)
                    if source_particle.collapsed_state is not None:
                        forced = min(source_particle.collapsed_state, partner.state_count - 1)
                    else:
                        forced = None

                if forced is not None:
                    result = self.measure_particle(partner_id, force_state=forced)
                    if "error" not in result:
                        affected += 1
                        propagations += 1

                # Entanglement is broken after propagation (measurement destroys it)
                link.broken = True
                if source_particle:
                    source_particle.entanglement_count = max(
                        0, source_particle.entanglement_count - 1
                    )
                partner.entanglement_count = max(0, partner.entanglement_count - 1)

            measurement.propagated = True
            measurement.partners_affected = affected

            if affected > 0:
                self._record_event(
                    QuantumEvent.COLLAPSE_PROPAGATE,
                    intensity=0.8,
                    particle_ids=[measurement.particle_id],
                    description=f"Measurement {measurement.measurement_id} propagated to {affected} partners",
                )

        # Clean up broken entanglements
        self._entanglements = deque(
            (e for e in self._entanglements if not e.broken),
            maxlen=self.MAX_ENTANGLEMENTS,
        )

        self._stats.total_collapses_propagated += propagations
        return {
            "propagations": propagations,
        }

    def _decohere_phase(self) -> Dict[str, Any]:
        """Phase 5: Coherence decays, returning particles toward classical."""
        decoherence_decays = 0
        for particle in self._particles.values():
            # Decoherence rate is higher for isolated particles
            multiplier = (
                self.ISOLATED_DECOHERE_MULTIPLIER
                if particle.entanglement_count == 0
                else 1.0
            )
            decay = particle.decohere_rate * multiplier
            if particle.coherence > self.MIN_COHERENCE:
                particle.coherence = max(
                    self.MIN_COHERENCE,
                    particle.coherence - decay,
                )
                if decay > 0:
                    decoherence_decays += 1

        if decoherence_decays > 0:
            self._record_event(
                QuantumEvent.DECOHERENCE_DECAY,
                intensity=0.3,
                particle_ids=[],
                description=f"{decoherence_decays} particles decohered",
            )

        self._stats.total_decoherence_decays += decoherence_decays
        return {
            "particles_decohered": decoherence_decays,
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
        """Get the overall status of the quantum field."""
        with self._lock:
            self._stats.total_particles = len(self._particles)
            self._stats.total_entanglements = len(self._entanglements)
            self._stats.total_measurements = len(self._measurements)
            self._stats.total_events = len(self._event_history)
            self._update_avg_metrics()
            return {
                "total_particles": self._stats.total_particles,
                "total_entanglements": self._stats.total_entanglements,
                "total_measurements": self._stats.total_measurements,
                "active": self._active,
                "cycle_count": self._cycle_count,
                "stats": {
                    "total_events": self._stats.total_events,
                    "total_particle_births": self._stats.total_particle_births,
                    "total_superpositions_set": self._stats.total_superpositions_set,
                    "total_entanglements_formed": self._stats.total_entanglements_formed,
                    "total_measurements_made": self._stats.total_measurements_made,
                    "total_collapses_propagated": self._stats.total_collapses_propagated,
                    "total_decoherence_decays": self._stats.total_decoherence_decays,
                    "total_field_recoheres": self._stats.total_field_recoheres,
                    "avg_coherence": round(self._stats.avg_coherence, 4),
                    "avg_entanglement_count": round(self._stats.avg_entanglement_count, 4),
                    "last_cycle_time_ms": self._stats.last_cycle_time_ms,
                },
            }

    def get_events(
        self, particle_type: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent quantum events, optionally filtered by particle type."""
        with self._lock:
            events = list(self._event_history)
            if particle_type:
                events = [e for e in events if e.get("particle_type") == particle_type]
            return events[:limit]

    def reset(self) -> Dict[str, Any]:
        """Reset the quantum field to its initial state."""
        with self._lock:
            self._particles.clear()
            self._entanglements.clear()
            self._measurements.clear()
            self._event_history.clear()
            self._stats = QuantumStats()
            self._cycle_count = 0
            self._active = False
            self._entanglement_counter = 0
            self._measurement_counter = 0
            self._event_counter = 0
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _record_event(
        self,
        event: QuantumEvent,
        intensity: float,
        particle_ids: List[str],
        description: str,
    ) -> None:
        """Record a quantum event in the history."""
        self._event_counter += 1
        self._event_history.append({
            "event_id": f"qe_{self._event_counter}",
            "event_type": event.value,
            "intensity": round(max(0.0, min(1.0, intensity)), 4),
            "particle_ids": particle_ids,
            "description": description,
            "timestamp": time.time(),
        })

    def _update_avg_metrics(self) -> None:
        """Update average metrics from current particles."""
        if not self._particles:
            self._stats.avg_coherence = 0.0
            self._stats.avg_entanglement_count = 0.0
            return
        n = len(self._particles)
        self._stats.avg_coherence = sum(
            p.coherence for p in self._particles.values()
        ) / n
        self._stats.avg_entanglement_count = sum(
            p.entanglement_count for p in self._particles.values()
        ) / n

    def _particle_to_dict(self, particle: QuantumParticle) -> Dict[str, Any]:
        """Convert a particle to a dictionary representation."""
        return {
            "particle_id": particle.particle_id,
            "label": particle.label,
            "particle_type": particle.particle_type.value,
            "state_count": particle.state_count,
            "amplitudes": [round(a, 4) for a in particle.amplitudes],
            "coherence": round(particle.coherence, 4),
            "decohere_rate": round(particle.decohere_rate, 4),
            "entanglement_affinity": round(particle.entanglement_affinity, 4),
            "collapsed_state": particle.collapsed_state,
            "measured": particle.measured,
            "entanglement_count": particle.entanglement_count,
            "measurement_count": particle.measurement_count,
            "age_cycles": particle.age_cycles,
            "timestamp": particle.timestamp,
        }

    def _entanglement_to_dict(self, e: EntanglementLink) -> Dict[str, Any]:
        """Convert an entanglement link to a dictionary representation."""
        return {
            "link_id": e.link_id,
            "particle_a_id": e.particle_a_id,
            "particle_b_id": e.particle_b_id,
            "correlation": round(e.correlation, 4),
            "phase_relation": e.phase_relation,
            "broken": e.broken,
            "timestamp": e.timestamp,
        }

    def _measurement_to_dict(self, m: MeasurementRecord) -> Dict[str, Any]:
        """Convert a measurement record to a dictionary representation."""
        return {
            "measurement_id": m.measurement_id,
            "particle_id": m.particle_id,
            "observed_state": m.observed_state,
            "observed_probability": round(m.observed_probability, 4),
            "propagated": m.propagated,
            "partners_affected": m.partners_affected,
            "timestamp": m.timestamp,
        }
