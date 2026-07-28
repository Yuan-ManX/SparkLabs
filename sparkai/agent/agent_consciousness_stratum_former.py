"""
Agent Consciousness Stratum Former
==================================

Models agent consciousness as geological strata where each layer represents a
different level of awareness. Experiences sediment on the surface, compress
into deeper layers over time, and occasionally trigger tectonic shifts when
subsurface stress accumulates.

Stratum layers (surface -> deep):
  REFLEXIVE     - instant reactions, reflex arcs
  REACTIVE      - learned stimulus-response patterns
  REFLECTIVE    - self-aware deliberation
  METACOGNITIVE - thinking about thinking
  TRANSCENDENT  - abstract symbolic thought

Cycle phases: SEDIMENT -> COMPRESS -> SHIFT -> ERODE -> CRYSTALLIZE
  SEDIMENT    - new experiences deposit on the surface layer
  COMPRESS    - deeper strata consolidate under accumulated weight
  SHIFT       - tectonic stress causes strata to displace
  ERODE       - surface layers wear away, exposing older material
  CRYSTALLIZE - stable patterns form crystalline structures

Events:
  EARTHQUAKE         - sudden tectonic shift releases accumulated stress
  VOLCANIC_ERUPTION  - deep transcendent material breaches the surface
  STRATUM_COLLAPSE   - a weakened layer gives way
  CRYSTAL_FORMATION  - a stable thought-pattern crystallizes
  EROSION_EVENT      - significant surface material lost
  FAULT_LINE         - a fracture propagates between layers
"""

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================

class StratumLayer(Enum):
    """Layers of consciousness from surface to depth."""
    REFLEXIVE = "reflexive"          # instant reactions
    REACTIVE = "reactive"            # learned responses
    REFLECTIVE = "reflective"        # self-aware thought
    METACOGNITIVE = "metacognitive"  # thinking about thinking
    TRANSCENDENT = "transcendent"    # abstract symbolic thought


class StratumPhase(Enum):
    """Phases of the consciousness stratum cycle."""
    SEDIMENT = "sediment"
    COMPRESS = "compress"
    SHIFT = "shift"
    ERODE = "erode"
    CRYSTALLIZE = "crystallize"


class StratumEvent(Enum):
    """Events that occur during the stratum cycle."""
    EARTHQUAKE = "earthquake"              # sudden tectonic shift
    VOLCANIC_ERUPTION = "volcanic_eruption"  # deep material surfaces
    STRATUM_COLLAPSE = "stratum_collapse"  # layer gives way
    CRYSTAL_FORMATION = "crystal_formation"  # pattern stabilizes
    EROSION_EVENT = "erosion_event"        # surface material lost
    FAULT_LINE = "fault_line"              # fracture between layers


# =============================================================================
# Default Parameters by Layer
# =============================================================================

# Default depth for each stratum layer (0.0 = surface, 1.0 = deepest)
DEFAULT_LAYER_DEPTH: Dict[StratumLayer, float] = {
    StratumLayer.REFLEXIVE: 0.1,
    StratumLayer.REACTIVE: 0.3,
    StratumLayer.REFLECTIVE: 0.55,
    StratumLayer.METACOGNITIVE: 0.8,
    StratumLayer.TRANSCENDENT: 1.0,
}

# Default density (stability) for each layer
DEFAULT_LAYER_DENSITY: Dict[StratumLayer, float] = {
    StratumLayer.REFLEXIVE: 0.4,     # loose, easily eroded
    StratumLayer.REACTIVE: 0.55,
    StratumLayer.REFLECTIVE: 0.7,
    StratumLayer.METACOGNITIVE: 0.82,
    StratumLayer.TRANSCENDENT: 0.92, # dense, very stable
}

# Default permeability (how easily experiences pass through) for each layer
DEFAULT_LAYER_PERMEABILITY: Dict[StratumLayer, float] = {
    StratumLayer.REFLEXIVE: 0.85,    # experiences pass easily
    StratumLayer.REACTIVE: 0.6,
    StratumLayer.REFLECTIVE: 0.35,
    StratumLayer.METACOGNITIVE: 0.18,
    StratumLayer.TRANSCENDENT: 0.08, # almost impenetrable
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class SedimentDeposit:
    """An experience deposited onto the consciousness strata."""
    deposit_id: str
    label: str
    # Which layer the deposit currently resides in
    layer: StratumLayer
    # Depth within the layer (0.0 = top, 1.0 = bottom)
    depth: float
    # Mass/weight of the experience (influences compression)
    mass: float
    # How much the deposit has compressed (0.0 = fresh, 1.0 = fully compressed)
    compression: float
    # Whether the deposit has crystallized into a stable pattern
    crystallized: bool
    # Emotional charge carried by the deposit (0.0-1.0)
    emotional_charge: float
    # Age in cycles
    age_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class CrystalPattern:
    """A stable thought-pattern that crystallized from sediment."""
    crystal_id: str
    label: str
    # Layer where the crystal formed
    layer: StratumLayer
    # Stability of the crystal (0.0-1.0)
    stability: float
    # Number of deposits that merged into this crystal
    source_count: int
    # Resonant frequency of the crystal (degrees, 0-360)
    resonance: float
    age_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class FaultLine:
    """A fracture between two stratum layers."""
    fault_id: str
    # The two layers separated by the fault
    upper_layer: StratumLayer
    lower_layer: StratumLayer
    # Severity of the fracture (0.0-1.0)
    severity: float
    # Whether the fault is actively propagating
    active: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class StratumEventRecord:
    """A recorded stratum event."""
    event_id: str
    event_type: StratumEvent
    intensity: float
    layer: Optional[StratumLayer]
    deposit_ids: List[str]
    depth_delta: float
    description: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class StratumStats:
    """Aggregate statistics for the stratum former."""
    total_deposits: int = 0
    total_crystals: int = 0
    total_faults: int = 0
    total_events: int = 0
    total_earthquakes: int = 0
    total_eruptions: int = 0
    total_collapses: int = 0
    total_crystal_formations: int = 0
    total_erosion_events: int = 0
    total_fault_lines: int = 0
    avg_compression: float = 0.0
    avg_depth: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Main Class
# =============================================================================

class AgentConsciousnessStratumFormer:
    """Forms and manages consciousness strata for AI agents.

    Models consciousness as a geological formation where experiences sediment,
    compress, shift, erode, and crystallize into stable patterns.
    """

    _instance: Optional["AgentConsciousnessStratumFormer"] = None
    _instance_lock = threading.Lock()

    # Configuration constants
    MAX_DEPOSITS = 200
    MAX_CRYSTALS = 100
    MAX_FAULTS = 50
    MAX_EVENT_HISTORY = 200
    MIN_MASS = 0.1
    MAX_MASS = 10.0
    MIN_DEPTH = 0.0
    MAX_DEPTH = 1.0
    MIN_COMPRESSION = 0.0
    MAX_COMPRESSION = 1.0
    COMPRESSION_RATE = 0.08
    NATURAL_COMPRESSION_DECAY = 0.03
    EROSION_RATE = 0.05
    CRYSTALLIZATION_THRESHOLD = 0.85
    EARTHQUAKE_STRESS_THRESHOLD = 0.75
    VOLCANIC_ERUPTION_CHARGE = 0.8
    STRATUM_COLLAPSE_THRESHOLD = 0.15
    FAULT_PROPAGATION_THRESHOLD = 0.5
    SEDIMENT_PASSAGE_DECAY = 0.15
    DEPOSIT_PERMEABILITY_FACTOR = 0.4

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._deposits: Dict[str, SedimentDeposit] = {}
        self._crystals: Dict[str, CrystalPattern] = {}
        self._faults: Dict[str, FaultLine] = {}
        self._event_history: List[StratumEventRecord] = []
        self._stats = StratumStats()
        self._cycle_count: int = 0
        self._active: bool = False
        # Track accumulated stress per layer for earthquake detection
        self._layer_stress: Dict[StratumLayer, float] = {
            layer: 0.0 for layer in StratumLayer
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentConsciousnessStratumFormer":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Deposit Management
    # -------------------------------------------------------------------------

    def register_deposit(
        self,
        deposit_id: str,
        label: str,
        layer: str = "reflexive",
        mass: Optional[float] = None,
        emotional_charge: float = 0.3,
    ) -> Dict[str, Any]:
        """Register a new experience deposit on the consciousness strata."""
        with self._lock:
            if deposit_id in self._deposits:
                return {"error": f"Deposit already registered: {deposit_id}"}
            if len(self._deposits) >= self.MAX_DEPOSITS:
                return {"error": "Maximum deposits reached"}

            try:
                slayer = StratumLayer(layer)
            except ValueError:
                return {"error": f"Unknown layer: {layer}"}

            if mass is None:
                mass = 2.0
            mass = max(self.MIN_MASS, min(self.MAX_MASS, float(mass)))
            charge = max(0.0, min(1.0, float(emotional_charge)))

            depth = DEFAULT_LAYER_DEPTH.get(slayer, 0.5)
            deposit = SedimentDeposit(
                deposit_id=deposit_id,
                label=label,
                layer=slayer,
                depth=depth,
                mass=mass,
                compression=0.0,
                crystallized=False,
                emotional_charge=charge,
            )
            self._deposits[deposit_id] = deposit
            self._stats.total_deposits = len(self._deposits)
            return self._deposit_to_dict(deposit)

    def get_deposit(self, deposit_id: str) -> Dict[str, Any]:
        """Get the state of a sediment deposit."""
        with self._lock:
            deposit = self._deposits.get(deposit_id)
            if deposit is None:
                return {"error": f"Deposit not found: {deposit_id}"}
            return self._deposit_to_dict(deposit)

    def list_deposits(
        self, layer: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """List sediment deposits, optionally filtered by layer."""
        with self._lock:
            target_layer = None
            if layer is not None:
                try:
                    target_layer = StratumLayer(layer)
                except ValueError:
                    return []
            results = []
            for deposit in self._deposits.values():
                if target_layer is not None and deposit.layer != target_layer:
                    continue
                results.append(self._deposit_to_dict(deposit))
            results.sort(key=lambda d: d.get("mass", 0), reverse=True)
            return results[:limit]

    def remove_deposit(self, deposit_id: str) -> Dict[str, Any]:
        """Remove a sediment deposit."""
        with self._lock:
            if deposit_id not in self._deposits:
                return {"removed": False}
            del self._deposits[deposit_id]
            self._stats.total_deposits = len(self._deposits)
            return {"removed": True, "deposit_id": deposit_id}

    def set_deposit_mass(self, deposit_id: str, mass: float) -> Dict[str, Any]:
        """Update the mass (weight) of a sediment deposit."""
        with self._lock:
            deposit = self._deposits.get(deposit_id)
            if deposit is None:
                return {"error": f"Deposit not found: {deposit_id}"}
            deposit.mass = max(self.MIN_MASS, min(self.MAX_MASS, float(mass)))
            deposit.timestamp = time.time()
            return self._deposit_to_dict(deposit)

    # -------------------------------------------------------------------------
    # Crystal Management
    # -------------------------------------------------------------------------

    def get_crystal(self, crystal_id: str) -> Dict[str, Any]:
        """Get the state of a crystal pattern."""
        with self._lock:
            crystal = self._crystals.get(crystal_id)
            if crystal is None:
                return {"error": f"Crystal not found: {crystal_id}"}
            return self._crystal_to_dict(crystal)

    def list_crystals(
        self, layer: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """List crystal patterns, optionally filtered by layer."""
        with self._lock:
            target_layer = None
            if layer is not None:
                try:
                    target_layer = StratumLayer(layer)
                except ValueError:
                    return []
            results = []
            for crystal in self._crystals.values():
                if target_layer is not None and crystal.layer != target_layer:
                    continue
                results.append(self._crystal_to_dict(crystal))
            results.sort(key=lambda d: d.get("stability", 0), reverse=True)
            return results[:limit]

    def remove_crystal(self, crystal_id: str) -> Dict[str, Any]:
        """Remove a crystal pattern."""
        with self._lock:
            if crystal_id not in self._crystals:
                return {"removed": False}
            del self._crystals[crystal_id]
            self._stats.total_crystals = len(self._crystals)
            return {"removed": True, "crystal_id": crystal_id}

    # -------------------------------------------------------------------------
    # Fault Management
    # -------------------------------------------------------------------------

    def get_fault(self, fault_id: str) -> Dict[str, Any]:
        """Get the state of a fault line."""
        with self._lock:
            fault = self._faults.get(fault_id)
            if fault is None:
                return {"error": f"Fault not found: {fault_id}"}
            return self._fault_to_dict(fault)

    def list_faults(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List fault lines between stratum layers."""
        with self._lock:
            results = [self._fault_to_dict(f) for f in self._faults.values()]
            results.sort(key=lambda d: d.get("severity", 0), reverse=True)
            return results[:limit]

    # -------------------------------------------------------------------------
    # Stratum Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single consciousness stratum cycle.

        Phases: SEDIMENT -> COMPRESS -> SHIFT -> ERODE -> CRYSTALLIZE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: SEDIMENT - deposits settle and age
            sediment_info = self._sediment_phase()

            # Phase 2: COMPRESS - deposits compress under accumulated weight
            compress_info = self._compress_phase()

            # Phase 3: SHIFT - tectonic stress causes displacement
            shift_info = self._shift_phase()

            # Phase 4: ERODE - surface deposits wear away
            erode_info = self._erode_phase()

            # Phase 5: CRYSTALLIZE - stable patterns form crystals
            crystallize_info = self._crystallize_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            phase = StratumPhase.CRYSTALLIZE
            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "sediment": sediment_info,
                "compress": compress_info,
                "shift": shift_info,
                "erode": erode_info,
                "crystallize": crystallize_info,
                "total_deposits": len(self._deposits),
                "total_crystals": len(self._crystals),
                "total_faults": len(self._faults),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _sediment_phase(self) -> Dict[str, Any]:
        """Phase 1: Deposits settle, age, and accumulate stress."""
        aged = 0
        stress_added = 0.0
        for deposit in self._deposits.values():
            deposit.age_cycles += 1
            aged += 1
            # Stress accumulates proportional to mass and emotional charge
            stress = deposit.mass * 0.02 * (1.0 + deposit.emotional_charge)
            self._layer_stress[deposit.layer] += stress
            stress_added += stress
        return {
            "deposits_aged": aged,
            "stress_accumulated": round(stress_added, 4),
        }

    def _compress_phase(self) -> Dict[str, Any]:
        """Phase 2: Deposits compress under accumulated weight."""
        compressed = 0
        total_delta = 0.0
        for deposit in self._deposits.values():
            if deposit.crystallized:
                continue
            # Compression rate depends on mass and layer density
            layer_density = DEFAULT_LAYER_DENSITY.get(deposit.layer, 0.5)
            rate = self.COMPRESSION_RATE * (1.0 - layer_density * 0.3)
            old_comp = deposit.compression
            deposit.compression = min(
                self.MAX_COMPRESSION,
                deposit.compression + rate * (1.0 + deposit.mass * 0.05),
            )
            total_delta += deposit.compression - old_comp
            compressed += 1
        return {
            "deposits_compressed": compressed,
            "avg_compression_delta": round(
                total_delta / max(1, compressed), 4
            ),
        }

    def _shift_phase(self) -> Dict[str, Any]:
        """Phase 3: Tectonic stress causes strata to shift."""
        shifts = 0
        earthquakes = 0
        eruptions = 0
        faults_formed = 0

        for layer, stress in list(self._layer_stress.items()):
            if stress >= self.EARTHQUAKE_STRESS_THRESHOLD:
                # Earthquake: release stress and shift deposits
                intensity = min(1.0, stress / self.EARTHQUAKE_STRESS_THRESHOLD)
                affected_ids: List[str] = []
                for deposit in self._deposits.values():
                    if deposit.layer == layer:
                        # Shift deposit depth
                        deposit.depth = max(
                            self.MIN_DEPTH,
                            min(self.MAX_DEPTH, deposit.depth + random.uniform(-0.1, 0.1)),
                        )
                        affected_ids.append(deposit.deposit_id)
                        shifts += 1

                self._record_event(
                    StratumEvent.EARTHQUAKE,
                    intensity,
                    layer,
                    affected_ids,
                    random.uniform(-0.1, 0.1),
                    f"Tectonic shift in {layer.value} layer",
                )
                earthquakes += 1
                self._layer_stress[layer] *= 0.3  # Release most stress

                # Earthquake may form a fault line
                layers_list = list(StratumLayer)
                idx = layers_list.index(layer)
                if idx > 0 and random.random() < 0.4:
                    upper = layers_list[idx - 1]
                    fault_id = f"fault_{int(time.time() * 1000)}_{random.randint(0, 999)}"
                    fault = FaultLine(
                        fault_id=fault_id,
                        upper_layer=upper,
                        lower_layer=layer,
                        severity=random.uniform(0.3, 0.7),
                        active=True,
                    )
                    self._faults[fault_id] = fault
                    faults_formed += 1
                    self._record_event(
                        StratumEvent.FAULT_LINE,
                        fault.severity,
                        None,
                        [],
                        0.0,
                        f"Fault formed between {upper.value} and {layer.value}",
                    )

            # Volcanic eruption: deep transcendent material surfaces
            if (
                layer == StratumLayer.TRANSCENDENT
                and stress >= self.VOLCANIC_ERUPTION_CHARGE
            ):
                # Pull a random deep deposit to the surface
                deep_deposits = [
                    d for d in self._deposits.values()
                    if d.layer == StratumLayer.TRANSCENDENT and not d.crystallized
                ]
                if deep_deposits:
                    target = random.choice(deep_deposits)
                    target.layer = StratumLayer.REFLEXIVE
                    target.depth = DEFAULT_LAYER_DEPTH[StratumLayer.REFLEXIVE]
                    target.compression *= 0.5  # Decompression during eruption
                    self._record_event(
                        StratumEvent.VOLCANIC_ERUPTION,
                        min(1.0, stress),
                        StratumLayer.TRANSCENDENT,
                        [target.deposit_id],
                        -0.9,
                        f"Deep material '{target.label}' surfaced",
                    )
                    eruptions += 1
                self._layer_stress[layer] *= 0.2

        # Decay all stress naturally
        for layer in self._layer_stress:
            self._layer_stress[layer] *= 0.95

        return {
            "deposits_shifted": shifts,
            "earthquakes": earthquakes,
            "volcanic_eruptions": eruptions,
            "faults_formed": faults_formed,
        }

    def _erode_phase(self) -> Dict[str, Any]:
        """Phase 4: Surface deposits erode over time."""
        eroded_count = 0
        removed_count = 0
        surface_layer = StratumLayer.REFLEXIVE
        for deposit_id in list(self._deposits.keys()):
            deposit = self._deposits[deposit_id]
            if deposit.layer != surface_layer or deposit.crystallized:
                continue
            # Erosion reduces mass
            deposit.mass -= self.EROSION_RATE * (1.0 - deposit.compression)
            eroded_count += 1

            # Stratum collapse: very low mass deposits collapse
            if deposit.mass <= self.STRATUM_COLLAPSE_THRESHOLD:
                self._record_event(
                    StratumEvent.STRATUM_COLLAPSE,
                    1.0 - deposit.mass,
                    deposit.layer,
                    [deposit_id],
                    -deposit.depth,
                    f"Deposit '{deposit.label}' collapsed",
                )
                del self._deposits[deposit_id]
                removed_count += 1
                self._stats.total_collapses += 1
            elif deposit.mass <= self.MIN_MASS:
                # Significant erosion event
                self._record_event(
                    StratumEvent.EROSION_EVENT,
                    0.5,
                    deposit.layer,
                    [deposit_id],
                    0.0,
                    f"Deposit '{deposit.label}' heavily eroded",
                )

        self._stats.total_deposits = len(self._deposits)
        self._stats.total_erosion_events += eroded_count
        return {
            "deposits_eroded": eroded_count,
            "deposits_removed": removed_count,
        }

    def _crystallize_phase(self) -> Dict[str, Any]:
        """Phase 5: Highly compressed deposits crystallize into stable patterns."""
        crystallized = 0
        for deposit in list(self._deposits.values()):
            if deposit.crystallized:
                continue
            if deposit.compression >= self.CRYSTALLIZATION_THRESHOLD:
                deposit.crystallized = True
                crystal_id = (
                    f"crystal_{deposit.deposit_id}_{int(time.time() * 1000)}"
                )
                crystal = CrystalPattern(
                    crystal_id=crystal_id,
                    label=deposit.label,
                    layer=deposit.layer,
                    stability=min(1.0, deposit.compression),
                    source_count=1,
                    resonance=(deposit.emotional_charge * 360.0) % 360.0,
                )
                self._crystals[crystal_id] = crystal
                self._record_event(
                    StratumEvent.CRYSTAL_FORMATION,
                    crystal.stability,
                    deposit.layer,
                    [deposit.deposit_id],
                    0.0,
                    f"Deposit '{deposit.label}' crystallized",
                )
                crystallized += 1

        self._stats.total_crystals = len(self._crystals)
        return {
            "crystals_formed": crystallized,
            "total_crystals": len(self._crystals),
        }

    # -------------------------------------------------------------------------
    # Event Recording
    # -------------------------------------------------------------------------

    def _record_event(
        self,
        event_type: StratumEvent,
        intensity: float,
        layer: Optional[StratumLayer],
        deposit_ids: List[str],
        depth_delta: float,
        description: str = "",
    ) -> Dict[str, Any]:
        """Record a stratum event."""
        event = StratumEventRecord(
            event_id=f"evt_{int(time.time() * 1000)}_{random.randint(0, 9999)}",
            event_type=event_type,
            intensity=max(0.0, min(1.0, float(intensity))),
            layer=layer,
            deposit_ids=deposit_ids,
            depth_delta=float(depth_delta),
            description=description,
        )
        self._event_history.append(event)
        if len(self._event_history) > self.MAX_EVENT_HISTORY:
            self._event_history.pop(0)

        self._stats.total_events += 1
        if event_type == StratumEvent.EARTHQUAKE:
            self._stats.total_earthquakes += 1
        elif event_type == StratumEvent.VOLCANIC_ERUPTION:
            self._stats.total_eruptions += 1
        elif event_type == StratumEvent.STRATUM_COLLAPSE:
            self._stats.total_collapses += 1
        elif event_type == StratumEvent.CRYSTAL_FORMATION:
            self._stats.total_crystal_formations += 1
        elif event_type == StratumEvent.EROSION_EVENT:
            self._stats.total_erosion_events += 1
        elif event_type == StratumEvent.FAULT_LINE:
            self._stats.total_fault_lines += 1
        return self._event_to_dict(event)

    def get_events(
        self, layer: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent stratum events, optionally filtered by layer."""
        with self._lock:
            target_layer = None
            if layer is not None:
                try:
                    target_layer = StratumLayer(layer)
                except ValueError:
                    return []
            results = []
            for event in reversed(self._event_history):
                if target_layer is not None and event.layer != target_layer:
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
        """Get the overall status of the stratum former."""
        with self._lock:
            return {
                "total_deposits": len(self._deposits),
                "total_crystals": len(self._crystals),
                "total_faults": len(self._faults),
                "active": self._stats.active,
                "cycle_count": self._cycle_count,
                "stats": {
                    "total_events": self._stats.total_events,
                    "total_earthquakes": self._stats.total_earthquakes,
                    "total_eruptions": self._stats.total_eruptions,
                    "total_collapses": self._stats.total_collapses,
                    "total_crystal_formations": self._stats.total_crystal_formations,
                    "total_erosion_events": self._stats.total_erosion_events,
                    "total_fault_lines": self._stats.total_fault_lines,
                    "avg_compression": round(self._stats.avg_compression, 4),
                    "avg_depth": round(self._stats.avg_depth, 4),
                    "last_cycle_time_ms": self._stats.last_cycle_time_ms,
                },
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the stratum former to its initial state."""
        with self._lock:
            self._deposits.clear()
            self._crystals.clear()
            self._faults.clear()
            self._event_history.clear()
            self._stats = StratumStats()
            self._cycle_count = 0
            self._active = False
            self._layer_stress = {layer: 0.0 for layer in StratumLayer}
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Serialization Helpers
    # -------------------------------------------------------------------------

    def _update_avg_metrics(self) -> None:
        """Update running average metrics."""
        if self._deposits:
            total_comp = sum(d.compression for d in self._deposits.values())
            total_depth = sum(d.depth for d in self._deposits.values())
            self._stats.avg_compression = total_comp / len(self._deposits)
            self._stats.avg_depth = total_depth / len(self._deposits)

    def _deposit_to_dict(self, deposit: SedimentDeposit) -> Dict[str, Any]:
        return {
            "deposit_id": deposit.deposit_id,
            "label": deposit.label,
            "layer": deposit.layer.value,
            "depth": round(deposit.depth, 4),
            "mass": round(deposit.mass, 4),
            "compression": round(deposit.compression, 4),
            "crystallized": deposit.crystallized,
            "emotional_charge": round(deposit.emotional_charge, 4),
            "age_cycles": deposit.age_cycles,
            "timestamp": deposit.timestamp,
        }

    def _crystal_to_dict(self, crystal: CrystalPattern) -> Dict[str, Any]:
        return {
            "crystal_id": crystal.crystal_id,
            "label": crystal.label,
            "layer": crystal.layer.value,
            "stability": round(crystal.stability, 4),
            "source_count": crystal.source_count,
            "resonance": round(crystal.resonance, 2),
            "age_cycles": crystal.age_cycles,
            "timestamp": crystal.timestamp,
        }

    def _fault_to_dict(self, fault: FaultLine) -> Dict[str, Any]:
        return {
            "fault_id": fault.fault_id,
            "upper_layer": fault.upper_layer.value,
            "lower_layer": fault.lower_layer.value,
            "severity": round(fault.severity, 4),
            "active": fault.active,
            "timestamp": fault.timestamp,
        }

    def _event_to_dict(self, event: StratumEventRecord) -> Dict[str, Any]:
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "intensity": round(event.intensity, 4),
            "layer": event.layer.value if event.layer else None,
            "deposit_ids": event.deposit_ids,
            "depth_delta": round(event.depth_delta, 4),
            "description": event.description,
            "timestamp": event.timestamp,
        }
