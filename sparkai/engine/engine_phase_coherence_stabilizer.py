"""
SparkLabs Engine - Phase Coherence Stabilizer"""

from __future__ import annotations

import logging
import math
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

class StabilizationPhase(Enum):
    """Phases of the phase coherence stabilization cycle."""
    MEASURE = "measure"        # measure the current phase distribution
    COUPLE = "couple"          # apply coupling forces between oscillators
    DRIFT = "drift"            # allow controlled phase drift
    LOCK = "lock"              # lock coherent clusters into stable relations
    COMMIT = "commit"          # commit the new phase state and emit events


class CoherenceState(Enum):
    """Per-oscillator coherence state."""
    CHAOTIC = "chaotic"              # phase spread is large, no coherence
    DRIFTING = "drifting"            # phase is wandering, weak coherence
    PARTIAL = "partial"              # some coherence, not yet locked
    LOCKED = "locked"                # phase is locked to neighbors
    SUPERCOHERENT = "supercoherent"  # phase is tightly locked, near-unison


class CouplingTopology(Enum):
    """How an oscillator connects to its neighbors."""
    NONE = "none"                            # no coupling
    NEAREST_NEIGHBOR = "nearest_neighbor"    # adjacent in cluster order
    ALL_TO_ALL = "all_to_all"                # every other oscillator
    SMALL_WORLD = "small_world"              # local ring plus a few long-range links
    SCALE_FREE = "scale_free"                # hubs attract more links


class FrequencyBand(Enum):
    """Frequency band of an oscillator."""
    SUB_BASS = "sub_bass"    # below 1 Hz
    BASS = "bass"            # 1-4 Hz
    MID = "mid"              # 4-12 Hz
    TREBLE = "treble"        # 12-30 Hz
    ULTRA = "ultra"          # above 30 Hz


class Vitality(Enum):
    """Overall vitality of an oscillator."""
    LATENT = "latent"        # amplitude very low, barely active
    EMERGING = "emerging"    # amplitude rising, finding its voice
    ACTIVE = "active"        # healthy amplitude, contributing
    SURGING = "surging"      # high amplitude, dominant
    SATURATED = "saturated"  # maxed amplitude, may be over-driving


# =============================================================================
# Config
# =============================================================================

@dataclass
class StabilizationConfig:
    """Tuning parameters for the phase coherence stabilizer."""
    max_oscillators: int = 200
    coupling_default: float = 0.35
    drift_tolerance: float = 0.12
    lock_threshold: float = 0.78
    supercoherent_threshold: float = 0.92
    phase_wrap: float = 6.283185307179586  # 2 * pi
    measurement_window: int = 8


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Oscillator:
    """A single coupled oscillator in the simulation."""
    oscillator_id: str
    entity_id: str                                  # cluster key, e.g. "cluster::combat_rhythm"
    cluster_label: str
    natural_frequency_hz: float
    current_phase: float
    coupling_strength: float
    coherence_state: CoherenceState = CoherenceState.CHAOTIC
    topology: CouplingTopology = CouplingTopology.NEAREST_NEIGHBOR
    frequency_band: FrequencyBand = FrequencyBand.MID
    vitality: Vitality = Vitality.LATENT
    locked_neighbors: List[str] = field(default_factory=list)
    amplitude: float = 0.5
    last_measured_at: float = field(default_factory=time.time)
    last_committed_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Stabilizer
# =============================================================================

class PhaseCoherenceStabilizer:
    """
    Thread-safe singleton orchestrating phase coherence stabilization.

    Usage:
        stabilizer = PhaseCoherenceStabilizer.get_instance()
        stabilizer.register_oscillator(
            entity_id="cluster::combat_rhythm",
            cluster_label="Combat Rhythm",
        )
        stabilizer.cycle()
        state = stabilizer.get_oscillator(oscillator_id)
    """

    _instance: Optional["PhaseCoherenceStabilizer"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    _MAX_OSCILLATORS = 200
    _MAX_EVENTS = 200

    # Tuning constants
    _COUPLE_TIME_STEP = 0.1             # discrete time step for Kuramoto coupling
    _DRIFT_BASE = 0.04                  # baseline drift scale before tolerance
    _AMPLITUDE_DECAY = 0.98             # amplitude decay per cycle
    _AMPLITUDE_COHERENCE_BOOST = 0.05   # amplitude gain when coherent

    def __init__(self) -> None:
        # Internal dict is keyed by entity_id (the cluster key), NOT by oscillator_id.
        self._oscillators: Dict[str, Oscillator] = {}
        self._phase: StabilizationPhase = StabilizationPhase.MEASURE
        self._cycle_count: int = 0
        self._osc_counter: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._config: StabilizationConfig = StabilizationConfig()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "PhaseCoherenceStabilizer":
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
            "oscillators_registered": 0,
            "phase_runs": 0,
            "measurements_taken": 0,
            "couplings_applied": 0,
            "drift_events": 0,
            "clusters_locked": 0,
            "supercoherent_clusters": 0,
            "events_recorded": 0,
            "avg_coherence": 0.0,
            "avg_phase": 0.0,
            "active_oscillators": 0,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        """Increment numeric stats that already exist in the stats dict."""
        for key, value in kwargs.items():
            if key not in self._stats:
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
        self._update_stats(events_recorded=1)

    # -------------------------------------------------------------------------
    # Oscillator Registration
    # -------------------------------------------------------------------------

    def register_oscillator(self, entity_id: str, cluster_label: str,
                            natural_frequency_hz: float = 1.0,
                            coupling_strength: Optional[float] = None,
                            current_phase: Optional[float] = None,
                            topology: CouplingTopology = CouplingTopology.NEAREST_NEIGHBOR,
                            frequency_band: Optional[FrequencyBand] = None,
                            amplitude: float = 0.5,
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Register a new oscillator keyed by its entity (cluster) id."""
        with self._global_lock:
            if len(self._oscillators) >= self._MAX_OSCILLATORS:
                return {"error": f"Oscillator cap reached: {self._MAX_OSCILLATORS}"}
            if entity_id in self._oscillators:
                return {"error": f"Oscillator already registered for entity: {entity_id}"}

            self._osc_counter += 1
            oscillator_id = f"osc_{self._osc_counter:04d}"

            if coupling_strength is None:
                coupling_strength = self._config.coupling_default
            if current_phase is None:
                current_phase = random.uniform(0.0, self._config.phase_wrap)
            if frequency_band is None:
                frequency_band = self._classify_frequency_band(natural_frequency_hz)

            osc = Oscillator(
                oscillator_id=oscillator_id,
                entity_id=entity_id,
                cluster_label=cluster_label,
                natural_frequency_hz=natural_frequency_hz,
                current_phase=current_phase % self._config.phase_wrap,
                coupling_strength=coupling_strength,
                coherence_state=CoherenceState.CHAOTIC,
                topology=topology,
                frequency_band=frequency_band,
                vitality=self._classify_vitality(amplitude),
                locked_neighbors=[],
                amplitude=amplitude,
                last_measured_at=time.time(),
                last_committed_at=time.time(),
                metadata=metadata or {},
            )
            self._oscillators[entity_id] = osc
            self._update_stats(oscillators_registered=1)
            self._record_event("oscillator_registered", {
                "oscillator_id": oscillator_id,
                "entity_id": entity_id,
                "cluster_label": cluster_label,
                "natural_frequency_hz": natural_frequency_hz,
                "coupling_strength": coupling_strength,
            })
            return {
                "oscillator_id": oscillator_id,
                "entity_id": entity_id,
                "cluster_label": cluster_label,
                "natural_frequency_hz": natural_frequency_hz,
                "current_phase": osc.current_phase,
                "coupling_strength": coupling_strength,
                "topology": topology.value,
                "frequency_band": frequency_band.value,
                "amplitude": amplitude,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single stabilization cycle through all five phases."""
        with self._global_lock:
            if not self._oscillators:
                self._seed_synthetic_oscillators()

            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._update_stats(phase_runs=1)

            phase_outputs: List[Dict[str, Any]] = []
            self._phase = StabilizationPhase.MEASURE
            phase_outputs.append(self._phase_measure())
            self._phase = StabilizationPhase.COUPLE
            phase_outputs.append(self._phase_couple())
            self._phase = StabilizationPhase.DRIFT
            phase_outputs.append(self._phase_drift())
            self._phase = StabilizationPhase.LOCK
            phase_outputs.append(self._phase_lock())
            self._phase = StabilizationPhase.COMMIT
            phase_outputs.append(self._phase_commit())

            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_measure(self) -> Dict[str, Any]:
        """Measure phase distribution and coherence across all oscillators."""
        oscs = list(self._oscillators.values())
        now = time.time()
        measured = 0
        for osc in oscs:
            osc.last_measured_at = now
            measured += 1

        coherence = self._compute_order_parameter(oscs)
        mean_phase = self._compute_mean_phase(oscs)
        spread = self._compute_phase_spread(oscs)

        # Classify per-oscillator coherence state from local coherence.
        for osc in oscs:
            local_coh = self._local_coherence(osc)
            osc.coherence_state = self._classify_coherence(local_coh)

        self._stats["avg_coherence"] = coherence
        self._stats["avg_phase"] = mean_phase
        self._stats["active_oscillators"] = sum(
            1 for o in oscs
            if o.vitality in (Vitality.ACTIVE, Vitality.SURGING, Vitality.SATURATED)
        )
        self._update_stats(measurements_taken=measured)
        self._record_event("phase_measure", {
            "measured": measured,
            "coherence": coherence,
            "mean_phase": mean_phase,
            "spread": spread,
        })
        return {
            "phase": "measure",
            "measured": measured,
            "coherence": coherence,
            "mean_phase": mean_phase,
            "spread": spread,
        }

    def _phase_couple(self) -> Dict[str, Any]:
        """Apply Kuramoto-style coupling forces between connected oscillators."""
        oscs = list(self._oscillators.values())
        if not oscs:
            return {"phase": "couple", "coupled": 0, "couplings_applied": 0}

        wrap = self._config.phase_wrap
        dt = self._COUPLE_TIME_STEP
        couplings_applied = 0
        coupled = 0

        for osc in oscs:
            neighbors = self._get_neighbors(osc)
            if not neighbors:
                continue
            coupled += 1
            phase_delta = 0.0
            for nbr in neighbors:
                diff = nbr.current_phase - osc.current_phase
                # Wrap difference to [-pi, pi].
                diff = ((diff + math.pi) % wrap) - math.pi
                phase_delta += math.sin(diff)
                couplings_applied += 1
            mean_delta = phase_delta / len(neighbors)
            osc.current_phase = (
                osc.current_phase + osc.coupling_strength * mean_delta * dt
            ) % wrap

        self._update_stats(couplings_applied=couplings_applied)
        self._record_event("phase_couple", {
            "coupled": coupled,
            "couplings_applied": couplings_applied,
        })
        return {
            "phase": "couple",
            "coupled": coupled,
            "couplings_applied": couplings_applied,
        }

    def _phase_drift(self) -> Dict[str, Any]:
        """Allow controlled phase drift to preserve rhythmic diversity."""
        wrap = self._config.phase_wrap
        tolerance = self._config.drift_tolerance
        drifted = 0
        for osc in self._oscillators.values():
            # Locked and supercoherent oscillators resist drift.
            if osc.coherence_state in (CoherenceState.LOCKED, CoherenceState.SUPERCOHERENT):
                continue
            drift = random.uniform(-tolerance, tolerance) * self._DRIFT_BASE
            osc.current_phase = (osc.current_phase + drift) % wrap
            drifted += 1
        self._update_stats(drift_events=drifted)
        self._record_event("phase_drift", {
            "drifted": drifted,
            "tolerance": tolerance,
        })
        return {
            "phase": "drift",
            "drifted": drifted,
            "tolerance": tolerance,
        }

    def _phase_lock(self) -> Dict[str, Any]:
        """Lock coherent clusters into stable phase relationships."""
        locked_count = 0
        supercoherent_count = 0
        for osc in self._oscillators.values():
            local_coh = self._local_coherence(osc)
            if local_coh >= self._config.supercoherent_threshold:
                osc.coherence_state = CoherenceState.SUPERCOHERENT
                supercoherent_count += 1
                osc.locked_neighbors = [
                    n.oscillator_id for n in self._get_neighbors(osc)
                ]
                locked_count += 1
            elif local_coh >= self._config.lock_threshold:
                osc.coherence_state = CoherenceState.LOCKED
                locked_count += 1
                osc.locked_neighbors = [
                    n.oscillator_id for n in self._get_neighbors(osc)
                ]
            else:
                osc.locked_neighbors = []
        self._update_stats(
            clusters_locked=locked_count,
            supercoherent_clusters=supercoherent_count,
        )
        self._record_event("phase_lock", {
            "locked": locked_count,
            "supercoherent": supercoherent_count,
        })
        return {
            "phase": "lock",
            "locked": locked_count,
            "supercoherent": supercoherent_count,
        }

    def _phase_commit(self) -> Dict[str, Any]:
        """Commit the new phase state and update coherence metrics."""
        wrap = self._config.phase_wrap
        now = time.time()
        committed = 0
        for osc in self._oscillators.values():
            osc.current_phase = osc.current_phase % wrap
            osc.last_committed_at = now
            # Amplitude tracks coherence: coherent oscillators grow, others decay.
            local_coh = self._local_coherence(osc)
            boost = (
                self._AMPLITUDE_COHERENCE_BOOST
                if local_coh >= self._config.lock_threshold
                else 0.0
            )
            osc.amplitude = min(1.0, osc.amplitude * self._AMPLITUDE_DECAY + boost)
            osc.vitality = self._classify_vitality(osc.amplitude)
            committed += 1
        self._record_event("phase_commit", {"committed": committed})
        return {
            "phase": "commit",
            "committed": committed,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _get_neighbors(self, osc: Oscillator) -> List[Oscillator]:
        """Return the neighbor oscillators for the given oscillator."""
        oscs = list(self._oscillators.values())
        if len(oscs) <= 1:
            return []
        if osc.topology == CouplingTopology.NONE:
            return []
        # Sort by entity_id for deterministic neighbor selection.
        ordered = sorted(oscs, key=lambda o: o.entity_id)
        idx = next(
            (i for i, o in enumerate(ordered) if o.entity_id == osc.entity_id), None
        )
        if idx is None:
            return []
        others = [o for o in ordered if o.entity_id != osc.entity_id]
        if osc.topology == CouplingTopology.ALL_TO_ALL:
            return others
        if osc.topology == CouplingTopology.NEAREST_NEIGHBOR:
            n = len(ordered)
            prev = ordered[(idx - 1) % n]
            nxt = ordered[(idx + 1) % n]
            nbrs: List[Oscillator] = []
            if prev.entity_id != osc.entity_id:
                nbrs.append(prev)
            if nxt.entity_id != osc.entity_id:
                nbrs.append(nxt)
            return nbrs
        if osc.topology == CouplingTopology.SMALL_WORLD:
            n = len(ordered)
            prev = ordered[(idx - 1) % n]
            nxt = ordered[(idx + 1) % n]
            nbrs = []
            if prev.entity_id != osc.entity_id:
                nbrs.append(prev)
            if nxt.entity_id != osc.entity_id:
                nbrs.append(nxt)
            # Add one long-range link if available.
            if others:
                long_range = random.choice(others)
                if long_range.entity_id not in {o.entity_id for o in nbrs}:
                    nbrs.append(long_range)
            return nbrs
        if osc.topology == CouplingTopology.SCALE_FREE:
            # Prefer high-amplitude hubs.
            ranked = sorted(others, key=lambda o: o.amplitude, reverse=True)
            return ranked[:min(3, len(ranked))]
        return []

    def _compute_order_parameter(self, oscs: List[Oscillator]) -> float:
        """Compute the Kuramoto order parameter (0=chaotic, 1=unison)."""
        if not oscs:
            return 0.0
        real = sum(math.cos(o.current_phase) for o in oscs)
        imag = sum(math.sin(o.current_phase) for o in oscs)
        return math.sqrt(real * real + imag * imag) / len(oscs)

    def _compute_mean_phase(self, oscs: List[Oscillator]) -> float:
        """Compute the mean phase angle via circular mean."""
        if not oscs:
            return 0.0
        real = sum(math.cos(o.current_phase) for o in oscs)
        imag = sum(math.sin(o.current_phase) for o in oscs)
        return math.atan2(imag, real) % self._config.phase_wrap

    def _compute_phase_spread(self, oscs: List[Oscillator]) -> float:
        """Compute circular spread (0=unison, 1=max spread)."""
        if not oscs:
            return 0.0
        r = self._compute_order_parameter(oscs)
        return 1.0 - r

    def _local_coherence(self, osc: Oscillator) -> float:
        """Compute local coherence between an oscillator and its neighbors."""
        neighbors = self._get_neighbors(osc)
        if not neighbors:
            # No neighbors means no coupling; coherence is low.
            return 0.0
        wrap = self._config.phase_wrap
        agreements: List[float] = []
        for nbr in neighbors:
            diff = abs(nbr.current_phase - osc.current_phase)
            diff = min(diff, wrap - diff)
            # agreement = 1 when phases match, 0 when opposite.
            agreement = 1.0 - (diff / math.pi)
            agreements.append(max(0.0, agreement))
        return sum(agreements) / len(agreements)

    def _classify_coherence(self, local_coh: float) -> CoherenceState:
        """Classify coherence state from a local coherence value."""
        if local_coh >= self._config.supercoherent_threshold:
            return CoherenceState.SUPERCOHERENT
        if local_coh >= self._config.lock_threshold:
            return CoherenceState.LOCKED
        if local_coh >= 0.4:
            return CoherenceState.PARTIAL
        if local_coh >= 0.2:
            return CoherenceState.DRIFTING
        return CoherenceState.CHAOTIC

    def _classify_frequency_band(self, freq_hz: float) -> FrequencyBand:
        """Classify the frequency band from a frequency in hertz."""
        if freq_hz < 1.0:
            return FrequencyBand.SUB_BASS
        if freq_hz < 4.0:
            return FrequencyBand.BASS
        if freq_hz < 12.0:
            return FrequencyBand.MID
        if freq_hz < 30.0:
            return FrequencyBand.TREBLE
        return FrequencyBand.ULTRA

    def _classify_vitality(self, amplitude: float) -> Vitality:
        """Classify vitality from an amplitude value."""
        if amplitude < 0.2:
            return Vitality.LATENT
        if amplitude < 0.4:
            return Vitality.EMERGING
        if amplitude < 0.7:
            return Vitality.ACTIVE
        if amplitude < 0.9:
            return Vitality.SURGING
        return Vitality.SATURATED

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "oscillators": len(self._oscillators),
                "stats": dict(self._stats),
            }

    def get_oscillators(self, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            oscs = sorted(
                self._oscillators.values(),
                key=lambda o: o.last_committed_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(oscs),
                "oscillators": [self._oscillator_to_dict(o) for o in oscs],
            }

    def get_oscillator(self, oscillator_id: str) -> Dict[str, Any]:
        # Internal dict is keyed by entity_id, NOT by oscillator_id.
        # Fallback search: iterate values and match by oscillator_id.
        with self._global_lock:
            for osc in self._oscillators.values():
                if osc.oscillator_id == oscillator_id:
                    return self._oscillator_to_dict(osc)
            return {"error": "oscillator not found", "oscillator_id": oscillator_id}

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic oscillators and run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_oscillators()
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
            self._oscillators.clear()
            self._events_log.clear()
            self._phase = StabilizationPhase.MEASURE
            self._cycle_count = 0
            self._osc_counter = 0
            self._init_stats()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
                "cycles_completed": self._stats["cycles_completed"],
            }

    # -------------------------------------------------------------------------
    # Seed
    # -------------------------------------------------------------------------

    def _seed_synthetic_oscillators(self) -> None:
        """Seed a small population of synthetic oscillators on first cycle."""
        seeds = [
            ("cluster::combat_rhythm", "Combat Rhythm", 2.0, 0.4, CouplingTopology.NEAREST_NEIGHBOR),
            ("cluster::ambient_drone", "Ambient Drone", 0.5, 0.2, CouplingTopology.ALL_TO_ALL),
            ("cluster::narrative_pulse", "Narrative Pulse", 1.0, 0.5, CouplingTopology.SMALL_WORLD),
            ("cluster::weather_cycle", "Weather Cycle", 0.2, 0.3, CouplingTopology.SCALE_FREE),
            ("cluster::dialogue_cadence", "Dialogue Cadence", 4.0, 0.6, CouplingTopology.NEAREST_NEIGHBOR),
            ("cluster::economy_oscillation", "Economy Oscillation", 0.8, 0.45, CouplingTopology.ALL_TO_ALL),
            ("cluster::ai_thought_wave", "AI Thought Wave", 8.0, 0.55, CouplingTopology.SMALL_WORLD),
        ]
        for entity_id, label, freq, coupling, topology in seeds:
            if entity_id not in self._oscillators:
                self.register_oscillator(
                    entity_id=entity_id,
                    cluster_label=label,
                    natural_frequency_hz=freq,
                    coupling_strength=coupling,
                    topology=topology,
                )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _oscillator_to_dict(self, osc: Oscillator) -> Dict[str, Any]:
        return {
            "oscillator_id": osc.oscillator_id,
            "entity_id": osc.entity_id,
            "cluster_label": osc.cluster_label,
            "natural_frequency_hz": osc.natural_frequency_hz,
            "current_phase": osc.current_phase,
            "coupling_strength": osc.coupling_strength,
            "coherence_state": osc.coherence_state.value,
            "topology": osc.topology.value,
            "frequency_band": osc.frequency_band.value,
            "vitality": osc.vitality.value,
            "locked_neighbors": list(osc.locked_neighbors),
            "amplitude": osc.amplitude,
            "last_measured_at": osc.last_measured_at,
            "last_committed_at": osc.last_committed_at,
            "metadata": dict(osc.metadata),
        }
