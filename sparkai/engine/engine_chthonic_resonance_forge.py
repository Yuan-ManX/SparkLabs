"""
SparkLabs Engine - Chthonic Resonance Forge"""

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

class ChthonicPhase(Enum):
    """Phases of the chthonic resonance forge cycle."""
    STRIKE_THE_ANVIL = "strike_the_anvil"            # strike the deep anvil to initiate pending resonances at a depth and fundamental frequency
    TEMPER_FREQUENCY = "temper_frequency"            # temper the fundamental frequency through the subterranean strata, adjusting impedance
    PROPAGATE_HARMONIC = "propagate_harmonic"        # propagate the harmonic through abyssal layers and accumulate seismic coupling across layers
    ATTUNE_FOUNDATION = "attune_foundation"          # attune the foundational earth-frequency against the core and derive seismic vitality
    EMIT_FORGED_RESONANCE = "emit_forged_resonance"  # emit the forged resonance map with resonances, strata, and coupling profiles


class ResonanceClass(Enum):
    """Classification of a forged resonance by its subterranean origin."""
    BEDROCK = "bedrock"            # tight shallow strike rooted in solid bedrock
    MAGMA = "magma"                # hot mid-depth strike from molten strata
    TECTONIC = "tectonic"          # wide deep strike from plate-boundary stress
    CRYSTALLINE = "crystalline"    # resonant strike ringing through crystal cavities
    VOID = "void"                  # abyssal strike echoing through a subterranean void


class HarmonicLayer(Enum):
    """The subterranean layer a harmonic propagates through."""
    SURFACE = "surface"            # surface crust layer
    MANTLE = "mantle"              # upper mantle layer
    CORE = "core"                  # outer core layer
    ABYSS = "abyss"                # deep abyssal layer
    NETHER = "nether"              # foundational nether layer


class ForgeState(Enum):
    """State of an individual resonance through the forge cycle."""
    PENDING = "pending"            # registered but not yet struck
    STRUCK = "struck"              # anvil struck, frequency locked
    TEMPERED = "tempered"          # tempered through strata
    PROPAGATED = "propagated"      # harmonic propagated through layers
    ATTUNED = "attuned"            # attuned against the foundation
    EMITTED = "emitted"            # emitted into the forged map


class Vitality(Enum):
    """Overall seismic vitality of the forge ecosystem."""
    DORMANT = "dormant"
    HUMMING = "humming"
    RESONATING = "resonating"
    SEISMIC = "seismic"
    CATACLYSMIC = "cataclysmic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SubterraneanResonance:
    """A forged subterranean resonance tracked through the forge cycle."""
    resonance_id: str
    entity_id: str
    label: str
    depth: float                                  # meters below surface, >= 0.0
    fundamental_frequency: float                  # Hz, the struck fundamental
    harmonic_amplitude: float                     # 0.0-1.0, strike strength
    resonance_class: ResonanceClass = ResonanceClass.BEDROCK
    harmonic_layer: HarmonicLayer = HarmonicLayer.SURFACE
    state: ForgeState = ForgeState.PENDING
    vitality: Vitality = Vitality.DORMANT
    seismic_coupling: float = 0.0                 # 0.0-1.0, coupling into the foundation
    impedance: float = 1.0                        # strata impedance factor
    temper_delta: float = 0.0                     # frequency shift from tempering
    struck_at: float = 0.0
    tempered_at: float = 0.0
    propagated_at: float = 0.0
    attuned_at: float = 0.0
    emitted_at: float = 0.0
    created_at: float = field(default_factory=time.time)
    note: str = ""


@dataclass
class ResonanceStratum:
    """A subterranean stratum a harmonic propagates through."""
    stratum_id: str
    resonance_id: str
    layer: HarmonicLayer
    depth_band: float                             # depth at this layer
    impedance: float                              # layer impedance
    coupling: float                               # layer coupling contribution
    phase_offset: float                           # harmonic phase offset at this layer
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Forge
# =============================================================================

class ChthonicResonanceForge:
    """
    Thread-safe singleton that forges deep subterranean resonances.

    Resonances are keyed internally by entity_id so that each logical
    resonance owns exactly one entry. The resonance_id is a generated handle
    for external lookups; lookups by resonance_id fall back to a linear scan
    of the registered resonances.

    Usage:
        forge = ChthonicResonanceForge.get_instance()
        forge.register_resonance(
            entity_id="res::magma_hum",
            label="Magma Hum",
            depth=1200.0,
            fundamental_frequency=7.83,
        )
        forge.cycle()
        resonance = forge.get_resonance(resonance_id)
        resonances = forge.get_resonances()
    """

    _instance: Optional["ChthonicResonanceForge"] = None
    _instance_lock = threading.Lock()

    # Capacity caps.
    _MAX_RESONANCES = 100
    _MAX_EVENTS = 200
    _MAX_STRATA = 300
    _MAX_TEMPERINGS = 200
    _MAX_PROPAGATIONS = 200
    _MAX_FORGINGS = 80

    # Domain tuning constants.
    _MIN_DEPTH = 0.0
    _MAX_DEPTH = 10000.0
    _MIN_FREQUENCY = 0.1
    _MAX_FREQUENCY = 100.0
    _MIN_AMPLITUDE = 0.0
    _MAX_AMPLITUDE = 1.0
    _BEDROCK_DEPTH_MAX = 500.0
    _MAGMA_DEPTH_MAX = 2000.0
    _TECTONIC_DEPTH_MAX = 5000.0
    _CRYSTALLINE_DEPTH_MAX = 8000.0
    _IMPEDANCE_BASE = 1.0
    _TEMPER_SCALE = 0.02
    _COUPLING_DECAY = 0.85
    _FOUNDATION_FREQUENCY = 7.83
    _CATACLYSMIC_COUPLING = 0.9

    def __init__(self) -> None:
        # Instance-level reentrant lock guarding all mutable state.
        self._global_lock = threading.RLock()
        # Internal dict keyed by entity_id (NOT resonance_id).
        self._resonances: Dict[str, SubterraneanResonance] = {}
        self._strata: Dict[str, ResonanceStratum] = {}
        self._temperings: Dict[str, Dict[str, Any]] = {}
        self._propagations: Dict[str, Dict[str, Any]] = {}
        self._forgings: Dict[str, Dict[str, Any]] = {}
        self._phase: ChthonicPhase = ChthonicPhase.STRIKE_THE_ANVIL
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._resonances:
            self._seed_synthetic_resonances()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ChthonicResonanceForge":
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
            "resonances_registered": 0,
            "phase_runs": 0,
            "frequencies_tempered": 0,
            "harmonics_propagated": 0,
            "foundations_attuned": 0,
            "resonances_forged": 0,
            "resonances_emitted": 0,
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
    def _parse_resonance_class(value: Any) -> Optional[ResonanceClass]:
        """Parse a ResonanceClass from a string, enum, or None. Returns None if unset."""
        if value is None:
            return None
        if isinstance(value, ResonanceClass):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for rc in ResonanceClass:
                if rc.value == lowered:
                    return rc
        return None

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_resonance_class(self, depth: float, amplitude: float) -> ResonanceClass:
        """Classify a resonance by its depth and strike amplitude."""
        if depth <= self._BEDROCK_DEPTH_MAX:
            return ResonanceClass.BEDROCK
        if depth <= self._MAGMA_DEPTH_MAX:
            return ResonanceClass.MAGMA
        if depth <= self._TECTONIC_DEPTH_MAX:
            return ResonanceClass.TECTONIC
        if depth <= self._CRYSTALLINE_DEPTH_MAX:
            return ResonanceClass.CRYSTALLINE
        return ResonanceClass.VOID

    def _classify_harmonic_layer(self, depth: float) -> HarmonicLayer:
        """Classify the dominant harmonic layer from the depth."""
        if depth <= self._BEDROCK_DEPTH_MAX:
            return HarmonicLayer.SURFACE
        if depth <= self._MAGMA_DEPTH_MAX:
            return HarmonicLayer.MANTLE
        if depth <= self._TECTONIC_DEPTH_MAX:
            return HarmonicLayer.CORE
        if depth <= self._CRYSTALLINE_DEPTH_MAX:
            return HarmonicLayer.ABYSS
        return HarmonicLayer.NETHER

    def _compute_impedance(self, layer: HarmonicLayer, depth: float) -> float:
        """Compute the strata impedance for a layer at a given depth."""
        # Deeper, denser layers resist the harmonic more.
        layer_factor = {
            HarmonicLayer.SURFACE: 1.0,
            HarmonicLayer.MANTLE: 1.6,
            HarmonicLayer.CORE: 2.4,
            HarmonicLayer.ABYSS: 3.2,
            HarmonicLayer.NETHER: 4.0,
        }.get(layer, 1.0)
        depth_factor = 1.0 + (depth / self._MAX_DEPTH)
        return self._IMPEDANCE_BASE * layer_factor * depth_factor

    def _color_for_resonance_class(self, resonance_class: ResonanceClass) -> str:
        """Map a resonance class to a preview color for the editor map."""
        if resonance_class == ResonanceClass.BEDROCK:
            return "#8B4513"      # saddle brown - solid bedrock hum
        if resonance_class == ResonanceClass.MAGMA:
            return "#FF4500"      # orange-red - molten magma churn
        if resonance_class == ResonanceClass.TECTONIC:
            return "#2F4F4F"      # dark slate gray - plate-boundary stress
        if resonance_class == ResonanceClass.CRYSTALLINE:
            return "#00CED1"      # dark turquoise - crystal cavity ring
        return "#4B0082"          # indigo - subterranean void echo

    def _derive_vitality(self, coupling: float, depth: float) -> Vitality:
        """Derive seismic vitality from coupling strength and depth."""
        if coupling < 0.1:
            return Vitality.DORMANT
        if coupling < 0.35:
            return Vitality.HUMMING
        if coupling < 0.6:
            return Vitality.RESONATING
        if coupling < self._CATACLYSMIC_COUPLING:
            return Vitality.SEISMIC
        return Vitality.CATACLYSMIC

    # -------------------------------------------------------------------------
    # Resonance Management
    # -------------------------------------------------------------------------

    def register_resonance(
        self,
        entity_id: str,
        label: str,
        depth: float = 100.0,
        fundamental_frequency: float = 7.83,
        harmonic_amplitude: float = 0.5,
        resonance_class: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new subterranean resonance with its depth and fundamental frequency."""
        with self._global_lock:
            if entity_id in self._resonances:
                return {"error": f"Resonance already registered: {entity_id}"}
            if len(self._resonances) >= self._MAX_RESONANCES:
                return {"error": f"Resonance cap reached ({self._MAX_RESONANCES})"}

            resonance_id = (
                f"res_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            depth_safe = max(self._MIN_DEPTH, min(self._MAX_DEPTH, float(depth)))
            freq_safe = max(
                self._MIN_FREQUENCY, min(self._MAX_FREQUENCY, float(fundamental_frequency)),
            )
            amp_safe = max(
                self._MIN_AMPLITUDE, min(self._MAX_AMPLITUDE, float(harmonic_amplitude)),
            )

            parsed_class = self._parse_resonance_class(resonance_class)
            if parsed_class is None:
                parsed_class = self._classify_resonance_class(depth_safe, amp_safe)
            layer = self._classify_harmonic_layer(depth_safe)
            impedance = self._compute_impedance(layer, depth_safe)

            resonance = SubterraneanResonance(
                resonance_id=resonance_id,
                entity_id=entity_id,
                label=label,
                depth=depth_safe,
                fundamental_frequency=freq_safe,
                harmonic_amplitude=amp_safe,
                resonance_class=parsed_class,
                harmonic_layer=layer,
                state=ForgeState.PENDING,
                vitality=Vitality.DORMANT,
                seismic_coupling=0.0,
                impedance=impedance,
                temper_delta=0.0,
                struck_at=0.0,
                tempered_at=0.0,
                propagated_at=0.0,
                attuned_at=0.0,
                emitted_at=0.0,
                created_at=time.time(),
                note=note,
            )
            self._resonances[entity_id] = resonance
            self._update_stats(resonances_registered=1)
            self._record_event("resonance_registered", {
                "resonance_id": resonance_id,
                "entity_id": entity_id,
                "label": label,
                "depth": depth_safe,
                "fundamental_frequency": freq_safe,
                "resonance_class": parsed_class.value,
                "harmonic_layer": layer.value,
            })

            return {
                "resonance_id": resonance_id,
                "entity_id": entity_id,
                "label": label,
                "depth": depth_safe,
                "fundamental_frequency": freq_safe,
                "harmonic_amplitude": amp_safe,
                "resonance_class": parsed_class.value,
                "harmonic_layer": layer.value,
                "impedance": impedance,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single chthonic resonance forge cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic resonances on the very first cycle if none exist.
            if not self._resonances and self._cycle_count == 0:
                self._seed_synthetic_resonances()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = ChthonicPhase.STRIKE_THE_ANVIL
            phase_outputs.append(self._phase_strike_the_anvil())
            self._phase = ChthonicPhase.TEMPER_FREQUENCY
            phase_outputs.append(self._phase_temper_frequency())
            self._phase = ChthonicPhase.PROPAGATE_HARMONIC
            phase_outputs.append(self._phase_propagate_harmonic())
            self._phase = ChthonicPhase.ATTUNE_FOUNDATION
            phase_outputs.append(self._phase_attune_foundation())
            self._phase = ChthonicPhase.EMIT_FORGED_RESONANCE
            phase_outputs.append(self._phase_emit_forged_resonance())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_strike_the_anvil(self) -> Dict[str, Any]:
        """Strike phase: confirm pending resonances and lock their fundamentals."""
        struck_count = 0
        depth_sum = 0.0
        freq_sum = 0.0
        for resonance in self._resonances.values():
            if resonance.state != ForgeState.PENDING:
                continue
            # Recompute class and layer in case depth was adjusted.
            resonance.resonance_class = self._classify_resonance_class(
                resonance.depth, resonance.harmonic_amplitude,
            )
            resonance.harmonic_layer = self._classify_harmonic_layer(resonance.depth)
            resonance.impedance = self._compute_impedance(
                resonance.harmonic_layer, resonance.depth,
            )
            resonance.struck_at = time.time()
            resonance.state = ForgeState.STRUCK
            depth_sum += resonance.depth
            freq_sum += resonance.fundamental_frequency
            struck_count += 1
        avg_depth = (depth_sum / struck_count) if struck_count > 0 else 0.0
        avg_freq = (freq_sum / struck_count) if struck_count > 0 else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_strike_the_anvil", {
            "struck_count": struck_count,
            "avg_depth": avg_depth,
            "avg_fundamental_frequency": avg_freq,
        })
        return {
            "phase": "strike_the_anvil",
            "struck_count": struck_count,
            "avg_depth": avg_depth,
            "avg_fundamental_frequency": avg_freq,
        }

    def _phase_temper_frequency(self) -> Dict[str, Any]:
        """Temper phase: bend the fundamental frequency through the strata."""
        tempered_count = 0
        temper_delta_sum = 0.0
        for resonance in self._resonances.values():
            if resonance.state != ForgeState.STRUCK:
                continue
            # Tempering shifts the frequency proportional to impedance and amplitude.
            temper_delta = (
                random.uniform(-self._TEMPER_SCALE, self._TEMPER_SCALE)
                * resonance.fundamental_frequency
                * (1.0 + resonance.impedance * 0.1)
            )
            resonance.temper_delta = temper_delta
            resonance.fundamental_frequency = max(
                self._MIN_FREQUENCY,
                min(
                    self._MAX_FREQUENCY,
                    resonance.fundamental_frequency + temper_delta,
                ),
            )
            resonance.tempered_at = time.time()
            resonance.state = ForgeState.TEMPERED

            # Record the tempering entry.
            tempering_id = (
                f"temp_{resonance.resonance_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            tempering_entry = {
                "tempering_id": tempering_id,
                "resonance_id": resonance.resonance_id,
                "entity_id": resonance.entity_id,
                "temper_delta": temper_delta,
                "tempered_frequency": resonance.fundamental_frequency,
                "impedance": resonance.impedance,
                "layer": resonance.harmonic_layer.value,
                "created_at": resonance.tempered_at,
            }
            if len(self._temperings) >= self._MAX_TEMPERINGS:
                oldest_key = next(iter(self._temperings))
                self._temperings.pop(oldest_key, None)
            self._temperings[tempering_id] = tempering_entry
            temper_delta_sum += abs(temper_delta)
            tempered_count += 1
        avg_temper_delta = (
            (temper_delta_sum / tempered_count) if tempered_count > 0 else 0.0
        )
        self._update_stats(phase_runs=1, frequencies_tempered=tempered_count)
        self._record_event("phase_temper_frequency", {
            "tempered_count": tempered_count,
            "avg_temper_delta": avg_temper_delta,
        })
        return {
            "phase": "temper_frequency",
            "tempered_count": tempered_count,
            "avg_temper_delta": avg_temper_delta,
        }

    def _phase_propagate_harmonic(self) -> Dict[str, Any]:
        """Propagate phase: push the harmonic through abyssal layers and accumulate coupling."""
        propagated_count = 0
        coupling_sum = 0.0
        strata_created = 0
        for resonance in self._resonances.values():
            if resonance.state != ForgeState.TEMPERED:
                continue
            # Propagate through each layer, accumulating coupling with decay.
            coupling = resonance.harmonic_amplitude
            for layer in HarmonicLayer:
                layer_impedance = self._compute_impedance(layer, resonance.depth)
                layer_coupling = coupling / max(layer_impedance, 0.1)
                stratum_id = (
                    f"stratum_{resonance.resonance_id}_{layer.value}_"
                    f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
                )
                stratum = ResonanceStratum(
                    stratum_id=stratum_id,
                    resonance_id=resonance.resonance_id,
                    layer=layer,
                    depth_band=resonance.depth * (
                        0.2 + 0.2 * list(HarmonicLayer).index(layer)
                    ),
                    impedance=layer_impedance,
                    coupling=layer_coupling,
                    phase_offset=coupling * math.pi,
                    created_at=time.time(),
                )
                if len(self._strata) >= self._MAX_STRATA:
                    oldest_key = next(iter(self._strata))
                    self._strata.pop(oldest_key, None)
                self._strata[stratum_id] = stratum
                strata_created += 1
                coupling *= self._COUPLING_DECAY
            resonance.seismic_coupling = min(1.0, coupling * 2.0)
            resonance.propagated_at = time.time()
            resonance.state = ForgeState.PROPAGATED

            # Record the propagation entry.
            propagation_id = (
                f"prop_{resonance.resonance_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            propagation_entry = {
                "propagation_id": propagation_id,
                "resonance_id": resonance.resonance_id,
                "entity_id": resonance.entity_id,
                "seismic_coupling": resonance.seismic_coupling,
                "strata_created": len(HarmonicLayer),
                "created_at": resonance.propagated_at,
            }
            if len(self._propagations) >= self._MAX_PROPAGATIONS:
                oldest_key = next(iter(self._propagations))
                self._propagations.pop(oldest_key, None)
            self._propagations[propagation_id] = propagation_entry
            coupling_sum += resonance.seismic_coupling
            propagated_count += 1
        avg_coupling = (
            (coupling_sum / propagated_count) if propagated_count > 0 else 0.0
        )
        self._update_stats(phase_runs=1, harmonics_propagated=propagated_count)
        self._record_event("phase_propagate_harmonic", {
            "propagated_count": propagated_count,
            "avg_coupling": avg_coupling,
            "strata_created": strata_created,
        })
        return {
            "phase": "propagate_harmonic",
            "propagated_count": propagated_count,
            "avg_coupling": avg_coupling,
            "strata_created": strata_created,
        }

    def _phase_attune_foundation(self) -> Dict[str, Any]:
        """Attune phase: align resonances against the foundational earth-frequency."""
        attuned_count = 0
        detune_sum = 0.0
        vitality_counts: Dict[str, int] = {v.value: 0 for v in Vitality}
        for resonance in self._resonances.values():
            if resonance.state != ForgeState.PROPAGATED:
                continue
            detune = abs(resonance.fundamental_frequency - self._FOUNDATION_FREQUENCY)
            resonance.vitality = self._derive_vitality(
                resonance.seismic_coupling, resonance.depth,
            )
            vitality_counts[resonance.vitality.value] += 1
            resonance.attuned_at = time.time()
            resonance.state = ForgeState.ATTUNED
            detune_sum += detune
            attuned_count += 1
        avg_detune = (detune_sum / attuned_count) if attuned_count > 0 else 0.0
        self._update_stats(phase_runs=1, foundations_attuned=attuned_count)
        self._record_event("phase_attune_foundation", {
            "attuned_count": attuned_count,
            "avg_detune": avg_detune,
            "vitality_distribution": vitality_counts,
        })
        return {
            "phase": "attune_foundation",
            "attuned_count": attuned_count,
            "avg_detune": avg_detune,
            "vitality_distribution": vitality_counts,
        }

    def _phase_emit_forged_resonance(self) -> Dict[str, Any]:
        """Emit phase: emit the forged resonance map with resonances, strata, and profiles."""
        emitted_count = 0
        for resonance in self._resonances.values():
            if resonance.state != ForgeState.ATTUNED:
                continue
            resonance.emitted_at = time.time()
            resonance.state = ForgeState.EMITTED
            # Record the final forged artifact.
            forging_id = (
                f"forg_{resonance.resonance_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            forging_entry = {
                "forging_id": forging_id,
                "resonance_id": resonance.resonance_id,
                "entity_id": resonance.entity_id,
                "label": resonance.label,
                "depth": resonance.depth,
                "fundamental_frequency": resonance.fundamental_frequency,
                "seismic_coupling": resonance.seismic_coupling,
                "resonance_class": resonance.resonance_class.value,
                "harmonic_layer": resonance.harmonic_layer.value,
                "vitality": resonance.vitality.value,
                "color": self._color_for_resonance_class(resonance.resonance_class),
                "preview_url": f"/preview/chthonic/{forging_id}.svg",
                "created_at": resonance.emitted_at,
            }
            if len(self._forgings) >= self._MAX_FORGINGS:
                oldest_key = next(iter(self._forgings))
                self._forgings.pop(oldest_key, None)
            self._forgings[forging_id] = forging_entry
            emitted_count += 1
        map_size = (
            len(self._resonances) + len(self._strata)
            + len(self._temperings) + len(self._propagations)
            + len(self._forgings)
        )
        self._update_stats(phase_runs=1, resonances_emitted=emitted_count)
        self._record_event("phase_emit_forged_resonance", {
            "emitted_count": emitted_count,
            "map_size": map_size,
        })
        return {
            "phase": "emit_forged_resonance",
            "emitted_count": emitted_count,
            "map_size": map_size,
        }

    # -------------------------------------------------------------------------
    # Domain-Specific Action: Forge
    # -------------------------------------------------------------------------

    def forge_resonance(
        self,
        resonance_id: str,
        target_depth: Optional[float] = None,
        target_frequency: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Forge a single resonance through the full pass and return a forging report."""
        with self._global_lock:
            resonance = self._find_resonance_by_id(resonance_id)
            if resonance is None:
                return {
                    "error": "resonance not found",
                    "resonance_id": resonance_id,
                }

            # Apply optional target overrides before forging.
            if target_depth is not None:
                resonance.depth = max(
                    self._MIN_DEPTH, min(self._MAX_DEPTH, float(target_depth)),
                )
                resonance.resonance_class = self._classify_resonance_class(
                    resonance.depth, resonance.harmonic_amplitude,
                )
                resonance.harmonic_layer = self._classify_harmonic_layer(resonance.depth)
                resonance.impedance = self._compute_impedance(
                    resonance.harmonic_layer, resonance.depth,
                )
            if target_frequency is not None:
                resonance.fundamental_frequency = max(
                    self._MIN_FREQUENCY,
                    min(self._MAX_FREQUENCY, float(target_frequency)),
                )

            report: Dict[str, Any] = {
                "resonance_id": resonance.resonance_id,
                "entity_id": resonance.entity_id,
                "label": resonance.label,
                "depth": resonance.depth,
                "fundamental_frequency": resonance.fundamental_frequency,
                "resonance_class": resonance.resonance_class.value,
                "harmonic_layer": resonance.harmonic_layer.value,
                "stages": [],
            }

            # Stage 1: strike.
            resonance.struck_at = time.time()
            resonance.state = ForgeState.STRUCK
            report["stages"].append({
                "stage": "strike",
                "struck_at": resonance.struck_at,
                "fundamental_frequency": resonance.fundamental_frequency,
            })

            # Stage 2: temper.
            temper_delta = (
                random.uniform(-self._TEMPER_SCALE, self._TEMPER_SCALE)
                * resonance.fundamental_frequency
                * (1.0 + resonance.impedance * 0.1)
            )
            resonance.temper_delta = temper_delta
            resonance.fundamental_frequency = max(
                self._MIN_FREQUENCY,
                min(
                    self._MAX_FREQUENCY,
                    resonance.fundamental_frequency + temper_delta,
                ),
            )
            resonance.tempered_at = time.time()
            resonance.state = ForgeState.TEMPERED
            report["stages"].append({
                "stage": "temper",
                "temper_delta": temper_delta,
                "tempered_frequency": resonance.fundamental_frequency,
                "impedance": resonance.impedance,
            })

            # Stage 3: propagate.
            coupling = resonance.harmonic_amplitude
            for layer in HarmonicLayer:
                layer_impedance = self._compute_impedance(layer, resonance.depth)
                stratum_id = (
                    f"stratum_{resonance.resonance_id}_{layer.value}_"
                    f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
                )
                stratum = ResonanceStratum(
                    stratum_id=stratum_id,
                    resonance_id=resonance.resonance_id,
                    layer=layer,
                    depth_band=resonance.depth * (
                        0.2 + 0.2 * list(HarmonicLayer).index(layer)
                    ),
                    impedance=layer_impedance,
                    coupling=coupling / max(layer_impedance, 0.1),
                    phase_offset=coupling * math.pi,
                    created_at=time.time(),
                )
                if len(self._strata) >= self._MAX_STRATA:
                    oldest_key = next(iter(self._strata))
                    self._strata.pop(oldest_key, None)
                self._strata[stratum_id] = stratum
                coupling *= self._COUPLING_DECAY
            resonance.seismic_coupling = min(1.0, coupling * 2.0)
            resonance.propagated_at = time.time()
            resonance.state = ForgeState.PROPAGATED
            report["stages"].append({
                "stage": "propagate",
                "seismic_coupling": resonance.seismic_coupling,
                "strata_created": len(HarmonicLayer),
            })

            # Stage 4: attune.
            detune = abs(resonance.fundamental_frequency - self._FOUNDATION_FREQUENCY)
            resonance.vitality = self._derive_vitality(
                resonance.seismic_coupling, resonance.depth,
            )
            resonance.attuned_at = time.time()
            resonance.state = ForgeState.ATTUNED
            report["stages"].append({
                "stage": "attune",
                "detune": detune,
                "foundation_frequency": self._FOUNDATION_FREQUENCY,
                "vitality": resonance.vitality.value,
            })

            # Stage 5: emit.
            resonance.emitted_at = time.time()
            resonance.state = ForgeState.EMITTED
            forging_id = (
                f"forg_{resonance.resonance_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            forging_entry = {
                "forging_id": forging_id,
                "resonance_id": resonance.resonance_id,
                "entity_id": resonance.entity_id,
                "label": resonance.label,
                "depth": resonance.depth,
                "fundamental_frequency": resonance.fundamental_frequency,
                "seismic_coupling": resonance.seismic_coupling,
                "resonance_class": resonance.resonance_class.value,
                "harmonic_layer": resonance.harmonic_layer.value,
                "vitality": resonance.vitality.value,
                "color": self._color_for_resonance_class(resonance.resonance_class),
                "preview_url": f"/preview/chthonic/{forging_id}.svg",
                "created_at": resonance.emitted_at,
            }
            if len(self._forgings) >= self._MAX_FORGINGS:
                oldest_key = next(iter(self._forgings))
                self._forgings.pop(oldest_key, None)
            self._forgings[forging_id] = forging_entry
            report["stages"].append({
                "stage": "emit",
                "forging_id": forging_id,
                "emitted_at": resonance.emitted_at,
            })

            self._update_stats(resonances_forged=1)
            self._record_event("resonance_forged", {
                "resonance_id": resonance.resonance_id,
                "forging_id": forging_id,
                "vitality": resonance.vitality.value,
            })
            report["forging_id"] = forging_id
            report["seismic_coupling"] = resonance.seismic_coupling
            report["vitality"] = resonance.vitality.value
            return report

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_resonance_by_id(self, resonance_id: str) -> Optional[SubterraneanResonance]:
        """Find a resonance by its resonance_id (linear scan over entity_id keys)."""
        for resonance in self._resonances.values():
            if resonance.resonance_id == resonance_id:
                return resonance
        return None

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_resonances(self) -> None:
        """Seed a few synthetic resonances on the first cycle if empty."""
        seeds = [
            (
                "res::bedrock_hum",
                "Bedrock Hum",
                250.0,
                7.83,
                0.4,
                "bedrock",
            ),
            (
                "res::magma_churn",
                "Magma Churn",
                1500.0,
                4.2,
                0.65,
                "magma",
            ),
            (
                "res::tectonic_grumble",
                "Tectonic Grumble",
                4200.0,
                1.5,
                0.85,
                "tectonic",
            ),
        ]
        for entity_id, label, depth, freq, amp, rc in seeds:
            if entity_id in self._resonances:
                continue
            if len(self._resonances) >= self._MAX_RESONANCES:
                break
            self.register_resonance(
                entity_id=entity_id,
                label=label,
                depth=depth,
                fundamental_frequency=freq,
                harmonic_amplitude=amp,
                resonance_class=rc,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _resonance_to_dict(self, resonance: SubterraneanResonance) -> Dict[str, Any]:
        return {
            "resonance_id": resonance.resonance_id,
            "entity_id": resonance.entity_id,
            "label": resonance.label,
            "depth": resonance.depth,
            "fundamental_frequency": resonance.fundamental_frequency,
            "harmonic_amplitude": resonance.harmonic_amplitude,
            "resonance_class": resonance.resonance_class.value,
            "harmonic_layer": resonance.harmonic_layer.value,
            "state": resonance.state.value,
            "vitality": resonance.vitality.value,
            "seismic_coupling": resonance.seismic_coupling,
            "impedance": resonance.impedance,
            "temper_delta": resonance.temper_delta,
            "struck_at": resonance.struck_at,
            "tempered_at": resonance.tempered_at,
            "propagated_at": resonance.propagated_at,
            "attuned_at": resonance.attuned_at,
            "emitted_at": resonance.emitted_at,
            "created_at": resonance.created_at,
            "note": resonance.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "resonances": len(self._resonances),
                "strata": len(self._strata),
                "temperings": len(self._temperings),
                "propagations": len(self._propagations),
                "forgings": len(self._forgings),
                "stats": dict(self._stats),
            }

    def get_resonances(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            resonances = sorted(
                self._resonances.values(),
                key=lambda r: r.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(resonances),
                "resonances": [
                    {
                        "resonance_id": r.resonance_id,
                        "entity_id": r.entity_id,
                        "label": r.label,
                        "depth": r.depth,
                        "fundamental_frequency": r.fundamental_frequency,
                        "resonance_class": r.resonance_class.value,
                        "harmonic_layer": r.harmonic_layer.value,
                        "vitality": r.vitality.value,
                        "state": r.state.value,
                    }
                    for r in resonances
                ],
            }

    def get_resonance(self, resonance_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT resonance_id, so we
        # MUST iterate over values and match on the resonance_id attribute.
        with self._global_lock:
            for resonance in self._resonances.values():
                if resonance.resonance_id == resonance_id:
                    return self._resonance_to_dict(resonance)
            return {
                "error": "resonance not found",
                "resonance_id": resonance_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic resonances if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._resonances:
                self._seed_synthetic_resonances()
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
            self._resonances.clear()
            self._strata.clear()
            self._temperings.clear()
            self._propagations.clear()
            self._forgings.clear()
            self._phase = ChthonicPhase.STRIKE_THE_ANVIL
            self._cycle_count = 0
            self._init_stats()
            self._seed_synthetic_resonances()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
