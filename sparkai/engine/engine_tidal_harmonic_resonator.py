"""
SparkLabs Engine - Tidal Harmonic Resonator"""

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

class TidalPhase(Enum):
    """Phases of the tidal harmonic resonator cycle."""
    MEASURE_TIDAL_OSCILLATION = "measure_tidal_oscillation"  # measure each tidal component's amplitude for this cycle, update tidal regime
    ALIGN_HARMONIC_NODES = "align_harmonic_nodes"            # align harmonic node balance between neighboring components
    TUNE_RESONANT_BASE = "tune_resonant_base"               # tune the resonant base to stay within the safe amplitude envelope
    STABILIZE_HARMONIC_LOCK = "stabilize_harmonic_lock"      # stabilize the harmonic lock and hold the resonant ratio
    EMIT_RESONANCE_GRAPH = "emit_resonance_graph"            # emit the full resonance graph with tones, amplitudes, and node balances


class TideKind(Enum):
    """The kind of tidal component being resonated."""
    SEMIDIURNAL = "semidiurnal"      # two high waters each lunar day
    DIURNAL = "diurnal"              # one high water each lunar day
    MIXED = "mixed"                  # mixed semidiurnal and diurnal character
    SPRING = "spring"                # maximal tidal range at syzygy
    NEAP = "neap"                    # minimal tidal range at quadrature


class HarmonicOrder(Enum):
    """The harmonic order of a tidal tone's oscillation."""
    FUNDAMENTAL = "fundamental"          # the principal tidal harmonic
    FIRST_OVERTONE = "first_overtone"    # the first overtone harmonic
    SECOND_OVERTONE = "second_overtone"  # the second overtone harmonic
    THIRD_OVERTONE = "third_overtone"    # the third overtone harmonic


class ResonanceState(Enum):
    """The resonance state of a tidal tone's harmonic lock."""
    DETUNED = "detuned"                      # below the resonance threshold
    NEAR_RESONANT = "near_resonant"          # approaching the resonance threshold
    RESONANT = "resonant"                    # at the resonance threshold
    SUSTAINED_CYCLE = "sustained_cycle"      # holding the resonant ratio steadily


class TidalBranchState(Enum):
    """State of an individual harmonic tone through the cycle."""
    PENDING = "pending"        # registered but not yet processed
    MEASURED = "measured"      # tidal amplitude measured this cycle
    ALIGNED = "aligned"        # harmonic node balance aligned
    TUNED = "tuned"            # resonant base tuned within the envelope
    LOCKED = "locked"          # harmonic lock stabilized
    EMITTED = "emitted"        # emitted into the resonance graph


class Vitality(Enum):
    """Overall vitality of the tidal harmonic ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    SWELLING = "swelling"
    SURGING = "surging"
    RESONANT = "resonant"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Tide:
    """A tidal harmonic tone resonated by the resonator."""
    entity_id: str
    tone_id: str
    tone_label: str
    amplitude: float                              # meters of tidal amplitude
    period_seconds: float                         # seconds of the governing period
    resonance_ratio: float                        # 0.0 to 1.0
    deep_water_depth: float                       # meters above the datum
    phase_offset: float                           # radians of phase offset
    node_drift: float                             # m/s of harmonic node drift
    tide_kind: TideKind = TideKind.SEMIDIURNAL
    harmonic_order: HarmonicOrder = HarmonicOrder.FUNDAMENTAL
    resonance_state: ResonanceState = ResonanceState.DETUNED
    vitality: Vitality = Vitality.DORMANT
    node_balance: float = 0.0                     # net node imbalance, meters
    safe_amplitude_floor: float = 0.05            # minimum safe amplitude, meters
    safe_amplitude_ceiling: float = 1.20          # maximum safe amplitude, meters
    state: TidalBranchState = TidalBranchState.PENDING
    created_at: float = field(default_factory=time.time)
    last_measured_at: float = 0.0
    note: str = ""


# =============================================================================
# Resonator
# =============================================================================

class TidalHarmonicResonator:
    """
    Thread-safe singleton that tunes tidal harmonic resonances.

    Harmonic tones are keyed internally by entity_id so each logical tidal
    component owns exactly one entry. The tone_id is a generated handle for
    external lookups; lookups by tone_id fall back to a linear scan of the
    registered tones.

    Usage:
        resonator = TidalHarmonicResonator.get_instance()
        resonator.register_tide(
            entity_id="tide::alpha",
            tone_label="Alpha Semidiurnal Tone",
            amplitude=1.2,
        )
        resonator.cycle()
        tone = resonator.get_tone(tone_id)
        resonance_graph = resonator.build_resonance_graph()
    """

    _instance: Optional["TidalHarmonicResonator"] = None
    _instance_lock = threading.Lock()

    # Capacity caps.
    _MAX_TONES = 200
    _MAX_EVENTS = 200
    _MAX_ALIGNMENT_LOGS = 200
    _MAX_TUNING_LOGS = 200
    _MAX_GRAPHS = 120

    # Domain tuning constants.
    _AMPLITUDE_FLUCTUATION = 0.4           # base tidal amplitude fluctuation magnitude, meters
    _NODE_TOLERANCE = 0.03                 # below this node imbalance is aligned
    _SAFE_AMPLITUDE_FLOOR_DEFAULT = 0.05   # default minimum safe amplitude, meters
    _SAFE_AMPLITUDE_CEILING_DEFAULT = 1.20 # default maximum safe amplitude, meters
    _RESONANCE_THRESHOLD = 0.7             # resonance ratio above which a tone is resonant
    _RESONANT_RATIO = 1.0                  # resonance ratio at full resonance
    _DEPLETED_AMPLITUDE = 0.1              # amplitude below which a tone is depleted
    _LOCK_THROTTLE_FACTOR = 0.7            # throttle factor for near-resonant drift
    _LOCK_CAP_FACTOR = 0.3                 # cap factor for resonant drift
    _MIN_AMPLITUDE = 1e-4
    _MAX_AMPLITUDE = 5.0

    def __init__(self) -> None:
        # Instance-level reentrant lock for thread-safe operation.
        self._global_lock = threading.RLock()
        # Internal dict keyed by entity_id (NOT tone_id).
        self._tones: Dict[str, Tide] = {}
        self._alignment_logs: Dict[str, Dict[str, Any]] = {}
        self._tuning_logs: Dict[str, Dict[str, Any]] = {}
        self._resonance_graphs: Dict[str, Dict[str, Any]] = {}
        self._phase: TidalPhase = TidalPhase.MEASURE_TIDAL_OSCILLATION
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._tones:
            self._seed_synthetic_tones()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "TidalHarmonicResonator":
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
            "tones_registered": 0,
            "phase_runs": 0,
            "oscillations_measured": 0,
            "nodes_aligned": 0,
            "detuned_nodes": 0,
            "bases_tuned": 0,
            "locks_stabilized": 0,
            "locks_held": 0,
            "graphs_emitted": 0,
            "events_recorded": 0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key not in self._stats:
                # Ignore unknown keys to keep callers simple.
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
        self._stats["events_recorded"] += 1

    # -------------------------------------------------------------------------
    # Parsing Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_tide_kind(value: Any) -> TideKind:
        """Parse a TideKind from a string, enum, or None."""
        if value is None:
            return TideKind.SEMIDIURNAL
        if isinstance(value, TideKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in TideKind:
                if kind.value == lowered:
                    return kind
        return TideKind.SEMIDIURNAL

    @staticmethod
    def _parse_harmonic_order(value: Any) -> HarmonicOrder:
        """Parse a HarmonicOrder from a string, enum, or None."""
        if value is None:
            return HarmonicOrder.FUNDAMENTAL
        if isinstance(value, HarmonicOrder):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for order in HarmonicOrder:
                if order.value == lowered:
                    return order
        return HarmonicOrder.FUNDAMENTAL

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_resonance_state(self, amplitude: float, resonance: float) -> ResonanceState:
        """Classify the resonance state from amplitude and resonance ratio."""
        if amplitude >= self._RESONANT_RATIO and resonance >= self._RESONANCE_THRESHOLD:
            return ResonanceState.SUSTAINED_CYCLE
        if resonance >= self._RESONANCE_THRESHOLD:
            return ResonanceState.RESONANT
        if amplitude <= self._DEPLETED_AMPLITUDE:
            return ResonanceState.DETUNED
        return ResonanceState.NEAR_RESONANT

    def _classify_lock_state(self, amplitude: float, node_drift: float) -> ResonanceState:
        """Classify the harmonic lock state from amplitude and current node drift."""
        if node_drift <= 0.0:
            return ResonanceState.DETUNED
        if amplitude >= self._RESONANT_RATIO:
            return ResonanceState.SUSTAINED_CYCLE
        if amplitude >= self._RESONANCE_THRESHOLD * 0.5:
            return ResonanceState.RESONANT
        return ResonanceState.NEAR_RESONANT

    def _derive_vitality(self, tone_id: str) -> Vitality:
        """Derive vitality for a harmonic tone from its post-lock state."""
        tone = self._find_tone_by_id(tone_id)
        if tone is None:
            return Vitality.DORMANT
        surging = abs(tone.node_balance) > self._NODE_TOLERANCE * 5.0
        if tone.resonance_state == ResonanceState.SUSTAINED_CYCLE and surging:
            return Vitality.RESONANT
        if tone.resonance_state == ResonanceState.NEAR_RESONANT:
            return Vitality.SURGING
        if tone.resonance_state == ResonanceState.RESONANT:
            return Vitality.SWELLING
        if tone.state in (TidalBranchState.MEASURED, TidalBranchState.ALIGNED):
            return Vitality.STIRRING
        return Vitality.DORMANT

    def _color_for_resonance(self, state: ResonanceState) -> str:
        """Map a resonance state to a preview color for the editor graph."""
        if state == ResonanceState.DETUNED:
            return "#7F8C8D"  # slate gray - detuned tone
        if state == ResonanceState.NEAR_RESONANT:
            return "#85C1E9"  # light blue - near-resonant tone
        if state == ResonanceState.RESONANT:
            return "#2E86C1"  # strong blue - resonant tone
        return "#1ABC9C"      # teal - sustained-cycle tone

    # -------------------------------------------------------------------------
    # Tone Management
    # -------------------------------------------------------------------------

    def register_tide(
        self,
        entity_id: str,
        tone_label: str,
        amplitude: float = 0.8,
        period_seconds: float = 44700.0,
        resonance_ratio: float = 0.4,
        deep_water_depth: float = 1000.0,
        phase_offset: float = 0.0,
        node_drift: float = 0.0,
        tide_kind: Optional[str] = None,
        harmonic_order: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new tidal harmonic tone with the resonator."""
        with self._global_lock:
            if entity_id in self._tones:
                return {"error": f"Tone already registered: {entity_id}"}
            if len(self._tones) >= self._MAX_TONES:
                return {"error": f"Tone cap reached ({self._MAX_TONES})"}

            tone_id = (
                f"tone_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            amp = max(
                self._MIN_AMPLITUDE,
                min(self._MAX_AMPLITUDE, float(amplitude)),
            )
            parsed_kind = self._parse_tide_kind(tide_kind)
            parsed_order = self._parse_harmonic_order(harmonic_order)
            resonance = max(0.0, min(1.0, float(resonance_ratio)))
            phase = self._classify_resonance_state(amp, resonance)
            drift = max(0.0, float(node_drift))
            lock_state = self._classify_lock_state(amp, drift)

            tone = Tide(
                entity_id=entity_id,
                tone_id=tone_id,
                tone_label=tone_label,
                amplitude=amp,
                period_seconds=float(period_seconds),
                resonance_ratio=resonance,
                deep_water_depth=float(deep_water_depth),
                phase_offset=float(phase_offset),
                node_drift=drift,
                tide_kind=parsed_kind,
                harmonic_order=parsed_order,
                resonance_state=phase,
                vitality=Vitality.DORMANT,
                node_balance=0.0,
                safe_amplitude_floor=self._SAFE_AMPLITUDE_FLOOR_DEFAULT,
                safe_amplitude_ceiling=self._SAFE_AMPLITUDE_CEILING_DEFAULT,
                state=TidalBranchState.PENDING,
                created_at=time.time(),
                last_measured_at=0.0,
                note=note,
            )
            self._tones[entity_id] = tone
            self._update_stats(tones_registered=1)
            self._record_event("tone_registered", {
                "tone_id": tone_id,
                "entity_id": entity_id,
                "tone_label": tone_label,
                "amplitude": tone.amplitude,
                "tide_kind": parsed_kind.value,
                "resonance_state": phase.value,
            })

            return {
                "tone_id": tone_id,
                "entity_id": entity_id,
                "tone_label": tone_label,
                "amplitude": tone.amplitude,
                "tide_kind": parsed_kind.value,
                "resonance_state": phase.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single tidal harmonic resonator cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic tones on the very first cycle if none exist.
            if not self._tones and self._cycle_count == 0:
                self._seed_synthetic_tones()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = TidalPhase.MEASURE_TIDAL_OSCILLATION
            phase_outputs.append(self._phase_measure_tidal_oscillation())
            self._phase = TidalPhase.ALIGN_HARMONIC_NODES
            phase_outputs.append(self._phase_align_harmonic_nodes())
            self._phase = TidalPhase.TUNE_RESONANT_BASE
            phase_outputs.append(self._phase_tune_resonant_base())
            self._phase = TidalPhase.STABILIZE_HARMONIC_LOCK
            phase_outputs.append(self._phase_stabilize_harmonic_lock())
            self._phase = TidalPhase.EMIT_RESONANCE_GRAPH
            phase_outputs.append(self._phase_emit_resonance_graph())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_measure_tidal_oscillation(self) -> Dict[str, Any]:
        """Measure phase: confirm pending harmonic tones and measure their amplitudes."""
        measured = 0
        amplitude_sum = 0.0
        for tone in self._tones.values():
            if tone.state == TidalBranchState.PENDING:
                tone.state = TidalBranchState.MEASURED
                measured += 1
            # Refresh resonance classification in case amplitude was set externally.
            tone.resonance_state = self._classify_resonance_state(
                tone.amplitude, tone.resonance_ratio,
            )
            amplitude_sum += tone.amplitude
        avg_amplitude = (amplitude_sum / len(self._tones)) if self._tones else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_measure_tidal_oscillation", {
            "measured": measured,
            "avg_amplitude": avg_amplitude,
        })
        return {
            "phase": "measure_tidal_oscillation",
            "measured": measured,
            "avg_amplitude": avg_amplitude,
        }

    def _phase_align_harmonic_nodes(self) -> Dict[str, Any]:
        """Align phase: align each tone's amplitude for this cycle."""
        aligned = 0
        for tone in self._tones.values():
            if tone.state != TidalBranchState.MEASURED:
                continue
            # Apply a small stochastic fluctuation to the tidal amplitude.
            fluctuation = random.uniform(
                -self._AMPLITUDE_FLUCTUATION, self._AMPLITUDE_FLUCTUATION,
            )
            tone.amplitude = max(0.0, tone.amplitude + fluctuation)
            # Resonance ratio drifts slightly with amplitude, clamped to bounds.
            drift = fluctuation * 0.01
            tone.resonance_ratio = max(
                0.0,
                min(1.0, tone.resonance_ratio + drift),
            )
            tone.resonance_state = self._classify_resonance_state(
                tone.amplitude, tone.resonance_ratio,
            )
            tone.last_measured_at = time.time()
            tone.state = TidalBranchState.ALIGNED
            aligned += 1
        self._update_stats(phase_runs=1, oscillations_measured=aligned)
        self._record_event("phase_align_harmonic_nodes", {"aligned": aligned})
        return {"phase": "align_harmonic_nodes", "aligned": aligned}

    def _phase_tune_resonant_base(self) -> Dict[str, Any]:
        """Tune phase: align harmonic node balance between neighboring tones."""
        tuned = 0
        detuned = 0
        tones = list(self._tones.values())
        for i, tone in enumerate(tones):
            if tone.state != TidalBranchState.ALIGNED:
                continue
            # Compare this tone's amplitude against the average of the others.
            if len(tones) <= 1:
                tone.node_balance = 0.0
            else:
                others = [t for j, t in enumerate(tones) if j != i]
                avg_other = sum(t.amplitude for t in others) / len(others)
                # Node imbalance normalized by an assumed tidal basin depth.
                depth = max(tone.deep_water_depth, 1.0) / 1000.0
                tone.node_balance = (
                    tone.amplitude - avg_other
                ) / max(depth, 0.001)
            if abs(tone.node_balance) <= self._NODE_TOLERANCE:
                tuned += 1
            else:
                detuned += 1
                # Record the alignment imbalance entry.
                log_id = (
                    f"align_{tone.tone_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "alignment_log_id": log_id,
                    "tone_id": tone.tone_id,
                    "entity_id": tone.entity_id,
                    "node_balance": tone.node_balance,
                    "amplitude": tone.amplitude,
                    "kind": "detuned",
                    "created_at": time.time(),
                }
                # Cap the alignment log collection.
                if len(self._alignment_logs) >= self._MAX_ALIGNMENT_LOGS:
                    oldest_key = next(iter(self._alignment_logs))
                    self._alignment_logs.pop(oldest_key, None)
                self._alignment_logs[log_id] = log_entry
            tone.state = TidalBranchState.TUNED
        self._update_stats(
            phase_runs=1,
            nodes_aligned=tuned,
            detuned_nodes=detuned,
        )
        self._record_event("phase_tune_resonant_base", {
            "tuned": tuned,
            "detuned": detuned,
        })
        return {
            "phase": "tune_resonant_base",
            "tuned": tuned,
            "detuned": detuned,
        }

    def _phase_stabilize_harmonic_lock(self) -> Dict[str, Any]:
        """Stabilize phase: tune the resonant base within the safe envelope."""
        stabilized = 0
        held = 0
        for tone in self._tones.values():
            if tone.state != TidalBranchState.TUNED:
                continue
            amplitude = tone.amplitude
            # Clamp the amplitude to the safe envelope.
            if amplitude > tone.safe_amplitude_ceiling:
                tone.amplitude = tone.safe_amplitude_ceiling
                amplitude = tone.safe_amplitude_ceiling
            elif amplitude < tone.safe_amplitude_floor:
                tone.amplitude = tone.safe_amplitude_floor
                amplitude = tone.safe_amplitude_floor
            # Re-classify after clamping.
            tone.resonance_state = self._classify_resonance_state(
                amplitude, tone.resonance_ratio,
            )
            # Stabilize node drift based on the clamped amplitude.
            if tone.node_drift > 0.0:
                if amplitude >= self._RESONANT_RATIO:
                    tone.node_drift *= self._LOCK_CAP_FACTOR
                    tone.resonance_state = ResonanceState.SUSTAINED_CYCLE
                    held += 1
                elif amplitude >= self._RESONANCE_THRESHOLD * 0.5:
                    tone.node_drift *= self._LOCK_THROTTLE_FACTOR
                    tone.resonance_state = ResonanceState.RESONANT
                else:
                    tone.resonance_state = ResonanceState.NEAR_RESONANT
                stabilized += 1
                # Record the tuning log.
                log_id = (
                    f"tune_{tone.tone_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "tuning_id": log_id,
                    "tone_id": tone.tone_id,
                    "entity_id": tone.entity_id,
                    "amplitude": amplitude,
                    "node_drift": tone.node_drift,
                    "resonance_state": tone.resonance_state.value,
                    "created_at": time.time(),
                }
                # Cap the tuning log collection.
                if len(self._tuning_logs) >= self._MAX_TUNING_LOGS:
                    oldest_key = next(iter(self._tuning_logs))
                    self._tuning_logs.pop(oldest_key, None)
                self._tuning_logs[log_id] = log_entry
            else:
                tone.resonance_state = ResonanceState.DETUNED
            # Phase offset tracks amplitude within the envelope.
            tone.phase_offset = amplitude * 0.5
            tone.state = TidalBranchState.LOCKED
        self._update_stats(
            phase_runs=1,
            bases_tuned=stabilized,
            locks_held=held,
        )
        self._record_event("phase_stabilize_harmonic_lock", {
            "stabilized": stabilized,
            "held": held,
        })
        return {
            "phase": "stabilize_harmonic_lock",
            "stabilized": stabilized,
            "held": held,
        }

    def _phase_emit_resonance_graph(self) -> Dict[str, Any]:
        """Emit phase: emit the full resonance graph with tones, amplitudes, logs."""
        emitted = 0
        for tone in self._tones.values():
            if tone.state != TidalBranchState.LOCKED:
                continue
            tone.state = TidalBranchState.EMITTED
            emitted += 1
        # Stamp vitality based on the post-lock state.
        for tone in self._tones.values():
            tone.vitality = self._derive_vitality(tone.tone_id)
        # Build the consolidated resonance graph entry.
        graph_id = (
            f"graph_{int(time.time() * 1000)}_{random.randint(100, 999)}"
        )
        resonance_graph = {
            "graph_id": graph_id,
            "cycle_count": self._cycle_count,
            "tone_count": len(self._tones),
            "alignment_log_count": len(self._alignment_logs),
            "tuning_log_count": len(self._tuning_logs),
            "tones": [self._tone_to_dict(t) for t in self._tones.values()],
            "alignment_logs": list(self._alignment_logs.values()),
            "tuning_logs": list(self._tuning_logs.values()),
            "created_at": time.time(),
        }
        # Cap the resonance graph collection.
        if len(self._resonance_graphs) >= self._MAX_GRAPHS:
            oldest_key = next(iter(self._resonance_graphs))
            self._resonance_graphs.pop(oldest_key, None)
        self._resonance_graphs[graph_id] = resonance_graph
        self._update_stats(phase_runs=1, graphs_emitted=1)
        self._record_event("phase_emit_resonance_graph", {
            "emitted": emitted,
            "graph_id": graph_id,
        })
        return {
            "phase": "emit_resonance_graph",
            "emitted": emitted,
            "graph_id": graph_id,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_tone_by_id(self, tone_id: str) -> Optional[Tide]:
        """Find a tone by its tone_id (linear scan over entity_id keys)."""
        for tone in self._tones.values():
            if tone.tone_id == tone_id:
                return tone
        return None

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_tones(self) -> None:
        """Seed a few synthetic tidal harmonic tones on the first cycle if empty."""
        seeds = [
            ("tide::alpha", "Alpha Semidiurnal Tone", 1.2, 0.45, TideKind.SEMIDIURNAL, 0.04),
            ("tide::bravo", "Bravo Spring Tone", 1.8, 0.85, TideKind.SPRING, 0.06),
            ("tide::charlie", "Charlie Diurnal Tone", 0.6, 0.18, TideKind.DIURNAL, 0.0),
        ]
        for entity_id, label, amplitude, resonance, kind, drift in seeds:
            if entity_id in self._tones:
                continue
            if len(self._tones) >= self._MAX_TONES:
                break
            self.register_tide(
                entity_id=entity_id,
                tone_label=label,
                amplitude=amplitude,
                period_seconds=44700.0,
                resonance_ratio=resonance,
                deep_water_depth=1200.0,
                phase_offset=0.0,
                node_drift=drift,
                tide_kind=kind.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _tone_to_dict(self, tone: Tide) -> Dict[str, Any]:
        return {
            "entity_id": tone.entity_id,
            "tone_id": tone.tone_id,
            "tone_label": tone.tone_label,
            "amplitude": tone.amplitude,
            "period_seconds": tone.period_seconds,
            "resonance_ratio": tone.resonance_ratio,
            "deep_water_depth": tone.deep_water_depth,
            "phase_offset": tone.phase_offset,
            "node_drift": tone.node_drift,
            "tide_kind": tone.tide_kind.value,
            "harmonic_order": tone.harmonic_order.value,
            "resonance_state": tone.resonance_state.value,
            "vitality": tone.vitality.value,
            "node_balance": tone.node_balance,
            "safe_amplitude_floor": tone.safe_amplitude_floor,
            "safe_amplitude_ceiling": tone.safe_amplitude_ceiling,
            "state": tone.state.value,
            "created_at": tone.created_at,
            "last_measured_at": tone.last_measured_at,
            "note": tone.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "tones": len(self._tones),
                "alignment_logs": len(self._alignment_logs),
                "tuning_logs": len(self._tuning_logs),
                "resonance_graphs": len(self._resonance_graphs),
                "stats": dict(self._stats),
            }

    def get_tones(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            tones = sorted(
                self._tones.values(),
                key=lambda t: t.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(tones),
                "tones": [
                    {
                        "tone_id": t.tone_id,
                        "entity_id": t.entity_id,
                        "tone_label": t.tone_label,
                        "amplitude": t.amplitude,
                        "tide_kind": t.tide_kind.value,
                        "resonance_state": t.resonance_state.value,
                        "vitality": t.vitality.value,
                    }
                    for t in tones
                ],
            }

    def get_tone(self, tone_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT tone_id, so we
        # MUST iterate over values and match on the tone_id attribute.
        with self._global_lock:
            for tone in self._tones.values():
                if tone.tone_id == tone_id:
                    return self._tone_to_dict(tone)
            return {
                "error": "tone not found",
                "tone_id": tone_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic tones if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._tones:
                self._seed_synthetic_tones()
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
            self._tones.clear()
            self._alignment_logs.clear()
            self._tuning_logs.clear()
            self._resonance_graphs.clear()
            self._phase = TidalPhase.MEASURE_TIDAL_OSCILLATION
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so cycles produce meaningful output.
            if not self._tones:
                self._seed_synthetic_tones()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Resonance
    # -------------------------------------------------------------------------

    def build_resonance_graph(self) -> Dict[str, Any]:
        """Build a resonance graph: run a resonance pass and return the graph.

        Computes the current resonance state distribution, the node imbalance
        summary, and the drift budget without advancing the cycle counter.
        """
        with self._global_lock:
            tones = list(self._tones.values())
            if not tones:
                return {
                    "resonated": 0,
                    "resonance_distribution": {},
                    "drift_budget": 0.0,
                    "detuned_count": 0,
                    "resonance_graph": "no tones registered",
                }
            resonance_counts: Dict[str, int] = {}
            total_drift = 0.0
            detuned = 0
            for tone in tones:
                state = self._classify_resonance_state(
                    tone.amplitude, tone.resonance_ratio,
                )
                resonance_counts[state.value] = resonance_counts.get(state.value, 0) + 1
                total_drift += tone.node_drift
                if abs(tone.node_balance) > self._NODE_TOLERANCE:
                    detuned += 1
            return {
                "resonated": len(tones),
                "resonance_distribution": resonance_counts,
                "drift_budget": total_drift,
                "detuned_count": detuned,
                "cycle_count": self._cycle_count,
                "resonance_graph": "resonance pass complete",
            }