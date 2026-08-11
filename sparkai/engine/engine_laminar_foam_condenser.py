"""
SparkLabs Engine - Laminar Foam Condenser"""

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

class FoamCondenserPhase(Enum):
    """Phases of the laminar foam condenser cycle."""
    REGISTER_FOAM = "register_foam"                          # register foam layers with their sensors and initial density
    SAMPLE_BUBBLE_DENSITY = "sample_bubble_density"          # sample each layer's bubble density for this cycle, update the regime
    COMPRESS_LAYERS = "compress_layers"                      # compress the smooth layered vapor, flag collapse against the thickness
    CONDENSE_LIQUID = "condense_liquid"                      # condense the vapor into dense liquid, track the yield
    EMIT_COLLAPSE_MAP = "emit_collapse_map"                  # emit the full foam-collapse map with densities, temperatures, and rates


class FoamKind(Enum):
    """The kind of foam bubbling through a condenser layer."""
    MICRO = "micro"            # fine micro-bubble foam
    FINE = "fine"              # small uniform-bubble foam
    COARSE = "coarse"          # large coarse-bubble foam
    MACRO = "macro"            # oversized macro-bubble foam


class FlowRegime(Enum):
    """The laminar flow regime of a foam layer."""
    SMOOTH = "smooth"          # smooth non-turbulent flow
    LAYERED = "layered"        # distinct laminar strata
    CREEPING = "creeping"      # very low velocity stratified flow
    SLIDING = "sliding"        # adjacent layers sliding past each other
    TURBULENT = "turbulent"    # flow breaking out of the laminar regime


class CollapseState(Enum):
    """The bubble-density phase state of a foam layer."""
    STABLE = "stable"          # steady foam, low collapse rate
    DENSIFYING = "densifying"  # layers packing closer together
    COLLAPSING = "collapsing"  # bubbles bursting, density rising
    CRITICAL = "critical"      # near-total foam collapse
    CONDENSED = "condensed"    # fully collapsed into dense liquid


class LayerState(Enum):
    """State of an individual foam layer through the condenser cycle."""
    PENDING = "pending"          # registered but not yet processed
    REGISTERED = "registered"    # confirmed and classified
    SAMPLED = "sampled"          # bubble density sampled this cycle
    COMPRESSED = "compressed"    # layered vapor compressed this cycle
    CONDENSED = "condensed"      # vapor condensed into dense liquid
    EMITTED = "emitted"          # emitted into the foam-collapse map


class Vitality(Enum):
    """Overall vitality of the laminar foam condenser ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    DYNAMIC = "dynamic"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FoamLayer:
    """A laminar foam layer condensed by the condenser engine."""
    entity_id: str
    foam_id: str
    foam_label: str
    bubble_density: float                        # bubbles per cubic meter
    layer_temperature: float                     # K in the foam layer
    layer_thickness: float                       # m of foam layer depth
    vapor_volume: float                          # m^3 of liquid-laden vapor
    layer_index: int                             # laminar stratum index of the stack
    foam_kind: FoamKind = FoamKind.FINE
    flow_regime: FlowRegime = FlowRegime.SMOOTH
    collapse_state: CollapseState = CollapseState.STABLE
    vitality: Vitality = Vitality.DORMANT
    collapse_rate: float = 0.0                   # bubbles bursting per second
    safe_density_floor: float = 0.5              # minimum safe bubble density
    safe_density_ceiling: float = 95.0           # maximum safe bubble density
    state: LayerState = LayerState.PENDING
    created_at: float = field(default_factory=time.time)
    last_sampled_at: float = 0.0
    note: str = ""


# =============================================================================
# Laminar Foam Condenser
# =============================================================================

class LaminarFoamCondenser:
    """
    Thread-safe singleton that condenses laminar foams.

    Layers are keyed internally by entity_id so each logical foam owns
    exactly one entry. The foam_id is a generated handle for external lookups;
    lookups by foam_id fall back to a linear scan of the registered layers.

    Usage:
        condenser = LaminarFoamCondenser.get_instance()
        condenser.register_foam(
            entity_id="foam::alpha",
            foam_label="Alpha Fine Foam",
            bubble_density=12.5,
        )
        condenser.cycle()
        layer = condenser.get_foam(foam_id)
        collapse_map = condenser.build_foam_collapse_map()
    """

    _instance: Optional["LaminarFoamCondenser"] = None
    _instance_lock = threading.Lock()

    # Capacity caps.
    _MAX_FOAMS = 200
    _MAX_EVENTS = 200
    _MAX_COLLAPSE_LOGS = 200
    _MAX_CONDENSATION_LOGS = 200
    _MAX_COLLAPSE_MAPS = 120

    # Domain tuning constants.
    _DENSITY_FLUCTUATION = 0.4              # base bubble density fluctuation magnitude
    _COLLAPSE_TOLERANCE = 0.03              # below this collapse imbalance is stable
    _SAFE_DENSITY_FLOOR_DEFAULT = 0.5       # default minimum safe bubble density
    _SAFE_DENSITY_CEILING_DEFAULT = 95.0    # default maximum safe bubble density
    _COLLAPSE_THRESHOLD = 0.7               # density ratio above which the layer is collapsing
    _DENSE_DENSITY = 1.0                    # bubble density above which the layer is dense
    _SPARSE_DENSITY = 0.1                   # bubble density below which the layer is sparse
    _LIQUID_FACTOR = 0.7                    # liquid factor for condensing vapor
    _CAP_FACTOR = 0.3                       # cap factor for over-dense foams
    _MIN_BUBBLE_DENSITY = 1e-4
    _MAX_BUBBLE_DENSITY = 5.0

    def __init__(self) -> None:
        # Instance-level reentrant lock for thread-safe operation.
        self._global_lock = threading.RLock()
        # Internal dict keyed by entity_id (NOT foam_id).
        self._foams: Dict[str, FoamLayer] = {}
        self._collapse_logs: Dict[str, Dict[str, Any]] = {}
        self._condensation_logs: Dict[str, Dict[str, Any]] = {}
        self._collapse_maps: Dict[str, Dict[str, Any]] = {}
        self._phase: FoamCondenserPhase = FoamCondenserPhase.REGISTER_FOAM
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._foams:
            self._seed_synthetic_foams()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "LaminarFoamCondenser":
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
            "foams_registered": 0,
            "phase_runs": 0,
            "densities_sampled": 0,
            "layers_compressed": 0,
            "collapses_flagged": 0,
            "liquid_yields": 0,
            "foam_caps": 0,
            "collapse_maps_emitted": 0,
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
    def _parse_foam_kind(value: Any) -> FoamKind:
        """Parse a FoamKind from a string, enum, or None."""
        if value is None:
            return FoamKind.FINE
        if isinstance(value, FoamKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in FoamKind:
                if kind.value == lowered:
                    return kind
        return FoamKind.FINE

    @staticmethod
    def _parse_flow_regime(value: Any) -> FlowRegime:
        """Parse a FlowRegime from a string, enum, or None."""
        if value is None:
            return FlowRegime.SMOOTH
        if isinstance(value, FlowRegime):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for regime in FlowRegime:
                if regime.value == lowered:
                    return regime
        return FlowRegime.SMOOTH

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_collapse_state(self, bubble_density: float, density_ratio: float) -> CollapseState:
        """Classify the collapse state from bubble density and density ratio."""
        if bubble_density >= self._DENSE_DENSITY and density_ratio >= self._COLLAPSE_THRESHOLD:
            return CollapseState.CRITICAL
        if density_ratio >= self._COLLAPSE_THRESHOLD:
            return CollapseState.COLLAPSING
        if bubble_density <= self._SPARSE_DENSITY:
            return CollapseState.CONDENSED
        if density_ratio >= self._COLLAPSE_THRESHOLD * 0.5:
            return CollapseState.DENSIFYING
        return CollapseState.STABLE

    def _derive_vitality(self, foam_id: str) -> Vitality:
        """Derive vitality for a foam layer from its post-condensation state."""
        layer = self._find_foam_by_id(foam_id)
        if layer is None:
            return Vitality.DORMANT
        collapsing = abs(layer.collapse_rate) > self._COLLAPSE_TOLERANCE * 5.0
        if layer.collapse_state == CollapseState.CRITICAL and collapsing:
            return Vitality.CHAOTIC
        if layer.collapse_state == CollapseState.STABLE:
            return Vitality.FLOWING
        if layer.collapse_state == CollapseState.DENSIFYING:
            return Vitality.DYNAMIC
        if layer.state in (LayerState.REGISTERED, LayerState.SAMPLED):
            return Vitality.STIRRING
        return Vitality.DORMANT

    def _color_for_state(self, state: CollapseState) -> str:
        """Map a collapse state to a preview color for the editor collapse map."""
        if state == CollapseState.STABLE:
            return "#00695C"  # teal - stable foam
        if state == CollapseState.DENSIFYING:
            return "#00838F"  # cyan - densifying layer
        if state == CollapseState.COLLAPSING:
            return "#F57C00"  # orange - collapsing foam
        if state == CollapseState.CRITICAL:
            return "#D32F2F"  # red - critical collapse
        return "#455A64"      # blue grey - condensed liquid

    # -------------------------------------------------------------------------
    # Foam Layer Management
    # -------------------------------------------------------------------------

    def register_foam(
        self,
        entity_id: str,
        foam_label: str,
        bubble_density: float = 8.0,
        layer_temperature: float = 340.0,
        layer_thickness: float = 1.0,
        vapor_volume: float = 5.0,
        layer_index: int = 0,
        foam_kind: Optional[str] = None,
        flow_regime: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new laminar foam layer with the condenser engine."""
        with self._global_lock:
            if entity_id in self._foams:
                return {"error": f"Foam already registered: {entity_id}"}
            if len(self._foams) >= self._MAX_FOAMS:
                return {"error": f"Foam cap reached ({self._MAX_FOAMS})"}

            foam_id = (
                f"foam_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            density = max(
                self._MIN_BUBBLE_DENSITY,
                min(self._MAX_BUBBLE_DENSITY, float(bubble_density)),
            )
            parsed_kind = self._parse_foam_kind(foam_kind)
            parsed_flow = self._parse_flow_regime(flow_regime)
            density_ratio = max(0.0, min(1.0, vapor_volume / 10.0))
            state = self._classify_collapse_state(density, density_ratio)

            layer = FoamLayer(
                entity_id=entity_id,
                foam_id=foam_id,
                foam_label=foam_label,
                bubble_density=density,
                layer_temperature=float(layer_temperature),
                layer_thickness=float(layer_thickness),
                vapor_volume=float(vapor_volume),
                layer_index=int(layer_index),
                foam_kind=parsed_kind,
                flow_regime=parsed_flow,
                collapse_state=state,
                vitality=Vitality.DORMANT,
                collapse_rate=0.0,
                safe_density_floor=self._SAFE_DENSITY_FLOOR_DEFAULT,
                safe_density_ceiling=self._SAFE_DENSITY_CEILING_DEFAULT,
                state=LayerState.PENDING,
                created_at=time.time(),
                last_sampled_at=0.0,
                note=note,
            )
            self._foams[entity_id] = layer
            self._update_stats(foams_registered=1)
            self._record_event("foam_registered", {
                "foam_id": foam_id,
                "entity_id": entity_id,
                "foam_label": foam_label,
                "bubble_density": layer.bubble_density,
                "foam_kind": parsed_kind.value,
                "collapse_state": state.value,
            })

            return {
                "foam_id": foam_id,
                "entity_id": entity_id,
                "foam_label": foam_label,
                "bubble_density": layer.bubble_density,
                "foam_kind": parsed_kind.value,
                "collapse_state": state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single laminar foam condenser cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic foam on the very first cycle if none exist.
            if not self._foams and self._cycle_count == 0:
                self._seed_synthetic_foams()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = FoamCondenserPhase.REGISTER_FOAM
            phase_outputs.append(self._phase_register_foam())
            self._phase = FoamCondenserPhase.SAMPLE_BUBBLE_DENSITY
            phase_outputs.append(self._phase_sample_bubble_density())
            self._phase = FoamCondenserPhase.COMPRESS_LAYERS
            phase_outputs.append(self._phase_compress_layers())
            self._phase = FoamCondenserPhase.CONDENSE_LIQUID
            phase_outputs.append(self._phase_condense_liquid())
            self._phase = FoamCondenserPhase.EMIT_COLLAPSE_MAP
            phase_outputs.append(self._phase_emit_collapse_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_foam(self) -> Dict[str, Any]:
        """Register phase: confirm pending foam layers and their sensors."""
        registered = 0
        density_sum = 0.0
        for layer in self._foams.values():
            if layer.state == LayerState.PENDING:
                layer.state = LayerState.REGISTERED
                registered += 1
            # Refresh collapse state classification in case density was set externally.
            density_ratio = max(0.0, min(1.0, layer.vapor_volume / 10.0))
            layer.collapse_state = self._classify_collapse_state(layer.bubble_density, density_ratio)
            density_sum += layer.bubble_density
        avg_density = (density_sum / len(self._foams)) if self._foams else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_foam", {
            "registered": registered,
            "avg_density": avg_density,
        })
        return {
            "phase": "register_foam",
            "registered": registered,
            "avg_density": avg_density,
        }

    def _phase_sample_bubble_density(self) -> Dict[str, Any]:
        """Sample phase: sample each layer's bubble density for this cycle."""
        sampled = 0
        for layer in self._foams.values():
            if layer.state != LayerState.REGISTERED:
                continue
            # Apply a small stochastic fluctuation to the bubble density.
            fluctuation = random.uniform(
                -self._DENSITY_FLUCTUATION, self._DENSITY_FLUCTUATION,
            )
            layer.bubble_density = max(0.0, layer.bubble_density + fluctuation)
            # Temperature drifts slightly with density, clamped to physical bounds.
            drift = fluctuation * 40.0
            layer.layer_temperature = max(
                self._MIN_BUBBLE_DENSITY,
                min(self._MAX_BUBBLE_DENSITY * 200.0, layer.layer_temperature + drift),
            )
            density_ratio = max(0.0, min(1.0, layer.vapor_volume / 10.0))
            layer.collapse_state = self._classify_collapse_state(layer.bubble_density, density_ratio)
            layer.last_sampled_at = time.time()
            layer.state = LayerState.SAMPLED
            sampled += 1
        self._update_stats(phase_runs=1, densities_sampled=sampled)
        self._record_event("phase_sample_bubble_density", {"sampled": sampled})
        return {"phase": "sample_bubble_density", "sampled": sampled}

    def _phase_compress_layers(self) -> Dict[str, Any]:
        """Compress phase: compress the smooth layered vapor between layers."""
        compressed = 0
        collapsing = 0
        layers = list(self._foams.values())
        for i, layer in enumerate(layers):
            if layer.state != LayerState.SAMPLED:
                continue
            # Compare this layer's density against the average of the others.
            if len(layers) <= 1:
                layer.collapse_rate = 0.0
            else:
                others = [l for j, l in enumerate(layers) if j != i]
                avg_other = sum(l.bubble_density for l in others) / len(others)
                # Collapse imbalance normalized by stratum span.
                stratum_span = max(layer.layer_index + 1, 1)
                layer.collapse_rate = (
                    layer.bubble_density - avg_other
                ) / stratum_span
            if abs(layer.collapse_rate) <= self._COLLAPSE_TOLERANCE:
                compressed += 1
            else:
                collapsing += 1
                # Record the collapse imbalance entry.
                log_id = (
                    f"coll_{layer.foam_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "collapse_id": log_id,
                    "foam_id": layer.foam_id,
                    "entity_id": layer.entity_id,
                    "collapse_rate": layer.collapse_rate,
                    "bubble_density": layer.bubble_density,
                    "kind": "collapse",
                    "created_at": time.time(),
                }
                # Cap the collapse log collection.
                if len(self._collapse_logs) >= self._MAX_COLLAPSE_LOGS:
                    oldest_key = next(iter(self._collapse_logs))
                    self._collapse_logs.pop(oldest_key, None)
                self._collapse_logs[log_id] = log_entry
            layer.state = LayerState.COMPRESSED
        self._update_stats(
            phase_runs=1,
            layers_compressed=compressed,
            collapses_flagged=collapsing,
        )
        self._record_event("phase_compress_layers", {
            "compressed": compressed,
            "collapsing": collapsing,
        })
        return {
            "phase": "compress_layers",
            "compressed": compressed,
            "collapsing": collapsing,
        }

    def _phase_condense_liquid(self) -> Dict[str, Any]:
        """Condense phase: condense the vapor into dense liquid for each layer."""
        condensed = 0
        capped = 0
        for layer in self._foams.values():
            if layer.state != LayerState.COMPRESSED:
                continue
            temp = layer.layer_temperature
            # Clamp the temperature to the safe envelope.
            if temp > layer.safe_density_ceiling * 4.0:
                layer.layer_temperature = layer.safe_density_ceiling * 4.0
                temp = layer.safe_density_ceiling * 4.0
            elif temp < layer.safe_density_floor:
                layer.layer_temperature = layer.safe_density_floor
                temp = layer.safe_density_floor
            # Re-classify after clamping.
            density_ratio = max(0.0, min(1.0, layer.vapor_volume / 10.0))
            layer.collapse_state = self._classify_collapse_state(layer.bubble_density, density_ratio)
            # Condense vapor into liquid based on the bubble density and layer.
            if layer.bubble_density > 0.0:
                if temp >= layer.safe_density_ceiling * 3.0:
                    layer.bubble_density *= self._CAP_FACTOR
                    capped += 1
                elif density_ratio >= self._COLLAPSE_THRESHOLD * 0.5:
                    layer.bubble_density *= self._LIQUID_FACTOR
                condensed += 1
                # Record the condensation yield log.
                yield_id = (
                    f"liquid_{layer.foam_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "yield_id": yield_id,
                    "foam_id": layer.foam_id,
                    "entity_id": layer.entity_id,
                    "layer_temperature": temp,
                    "bubble_density": layer.bubble_density,
                    "collapse_state": layer.collapse_state.value,
                    "created_at": time.time(),
                }
                # Cap the condensation log collection.
                if len(self._condensation_logs) >= self._MAX_CONDENSATION_LOGS:
                    oldest_key = next(iter(self._condensation_logs))
                    self._condensation_logs.pop(oldest_key, None)
                self._condensation_logs[yield_id] = log_entry
            # Vapor volume tracks temperature within the envelope.
            layer.layer_thickness = temp * 0.001
            layer.state = LayerState.CONDENSED
        self._update_stats(
            phase_runs=1,
            liquid_yields=condensed,
            foam_caps=capped,
        )
        self._record_event("phase_condense_liquid", {
            "condensed": condensed,
            "capped": capped,
        })
        return {
            "phase": "condense_liquid",
            "condensed": condensed,
            "capped": capped,
        }

    def _phase_emit_collapse_map(self) -> Dict[str, Any]:
        """Emit phase: emit the full foam-collapse map with layers, temps, logs."""
        emitted = 0
        for layer in self._foams.values():
            if layer.state != LayerState.CONDENSED:
                continue
            layer.state = LayerState.EMITTED
            emitted += 1
        # Stamp vitality based on the post-condensation state.
        for layer in self._foams.values():
            layer.vitality = self._derive_vitality(layer.foam_id)
        # Build the consolidated foam-collapse map entry.
        map_id = (
            f"collapse_{int(time.time() * 1000)}_{random.randint(100, 999)}"
        )
        collapse_map = {
            "collapse_map_id": map_id,
            "cycle_count": self._cycle_count,
            "layer_count": len(self._foams),
            "collapse_log_count": len(self._collapse_logs),
            "condensation_log_count": len(self._condensation_logs),
            "foams": [self._layer_to_dict(l) for l in self._foams.values()],
            "collapse_logs": list(self._collapse_logs.values()),
            "condensation_logs": list(self._condensation_logs.values()),
            "created_at": time.time(),
        }
        # Cap the collapse map collection.
        if len(self._collapse_maps) >= self._MAX_COLLAPSE_MAPS:
            oldest_key = next(iter(self._collapse_maps))
            self._collapse_maps.pop(oldest_key, None)
        self._collapse_maps[map_id] = collapse_map
        self._update_stats(phase_runs=1, collapse_maps_emitted=1)
        self._record_event("phase_emit_collapse_map", {
            "emitted": emitted,
            "collapse_map_id": map_id,
        })
        return {
            "phase": "emit_collapse_map",
            "emitted": emitted,
            "collapse_map_id": map_id,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_foam_by_id(self, foam_id: str) -> Optional[FoamLayer]:
        """Find a foam layer by its foam_id (linear scan over entity_id keys)."""
        for layer in self._foams.values():
            if layer.foam_id == foam_id:
                return layer
        return None

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_foams(self) -> None:
        """Seed a few synthetic laminar foams on the first cycle if empty."""
        seeds = [
            ("foam::alpha", "Alpha Fine Foam", 12.5, 340.0, 0, FoamKind.FINE, FlowRegime.SMOOTH),
            ("foam::bravo", "Bravo Coarse Foam", 18.0, 360.0, 1, FoamKind.COARSE, FlowRegime.LAYERED),
            ("foam::charlie", "Charlie Micro Foam", 6.0, 380.0, 2, FoamKind.MICRO, FlowRegime.CREEPING),
        ]
        for entity_id, label, density, temp, index, kind, regime in seeds:
            if entity_id in self._foams:
                continue
            if len(self._foams) >= self._MAX_FOAMS:
                break
            self.register_foam(
                entity_id=entity_id,
                foam_label=label,
                bubble_density=density,
                layer_temperature=temp,
                layer_thickness=1.0,
                vapor_volume=5.0,
                layer_index=index,
                foam_kind=kind.value,
                flow_regime=regime.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _layer_to_dict(self, layer: FoamLayer) -> Dict[str, Any]:
        return {
            "entity_id": layer.entity_id,
            "foam_id": layer.foam_id,
            "foam_label": layer.foam_label,
            "bubble_density": layer.bubble_density,
            "layer_temperature": layer.layer_temperature,
            "layer_thickness": layer.layer_thickness,
            "vapor_volume": layer.vapor_volume,
            "layer_index": layer.layer_index,
            "foam_kind": layer.foam_kind.value,
            "flow_regime": layer.flow_regime.value,
            "collapse_state": layer.collapse_state.value,
            "vitality": layer.vitality.value,
            "collapse_rate": layer.collapse_rate,
            "safe_density_floor": layer.safe_density_floor,
            "safe_density_ceiling": layer.safe_density_ceiling,
            "state": layer.state.value,
            "created_at": layer.created_at,
            "last_sampled_at": layer.last_sampled_at,
            "note": layer.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "foams": len(self._foams),
                "collapse_logs": len(self._collapse_logs),
                "condensation_logs": len(self._condensation_logs),
                "collapse_maps": len(self._collapse_maps),
                "stats": dict(self._stats),
            }

    def get_foams(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            layers = sorted(
                self._foams.values(),
                key=lambda l: l.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(layers),
                "foams": [
                    {
                        "foam_id": l.foam_id,
                        "entity_id": l.entity_id,
                        "foam_label": l.foam_label,
                        "bubble_density": l.bubble_density,
                        "foam_kind": l.foam_kind.value,
                        "collapse_state": l.collapse_state.value,
                        "vitality": l.vitality.value,
                        "layer_index": l.layer_index,
                    }
                    for l in layers
                ],
            }

    def get_foam(self, foam_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT foam_id, so we
        # MUST iterate over values and match on the foam_id attribute.
        with self._global_lock:
            for layer in self._foams.values():
                if layer.foam_id == foam_id:
                    return self._layer_to_dict(layer)
            return {
                "error": "foam not found",
                "foam_id": foam_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic foam if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._foams:
                self._seed_synthetic_foams()
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
            self._foams.clear()
            self._collapse_logs.clear()
            self._condensation_logs.clear()
            self._collapse_maps.clear()
            self._phase = FoamCondenserPhase.REGISTER_FOAM
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so cycles produce meaningful output.
            if not self._foams:
                self._seed_synthetic_foams()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Routing
    # -------------------------------------------------------------------------

    def build_foam_collapse_map(self) -> Dict[str, Any]:
        """Build a foam-collapse map: run a condensation pass and return the map.

        Computes the current collapse state distribution, the foam-collapse
        rate summary, and the liquid yield estimate without advancing the
        cycle counter.
        """
        with self._global_lock:
            layers = list(self._foams.values())
            if not layers:
                return {
                    "layer_count": 0,
                    "collapse_state_distribution": {},
                    "liquid_yield_estimate": 0.0,
                    "collapse_flag_count": 0,
                    "foam_collapse_map": "no foams registered",
                }
            state_counts: Dict[str, int] = {}
            total_yield = 0.0
            collapsing = 0
            for layer in layers:
                density_ratio = max(0.0, min(1.0, layer.vapor_volume / 10.0))
                state = self._classify_collapse_state(layer.bubble_density, density_ratio)
                state_counts[state.value] = state_counts.get(state.value, 0) + 1
                total_yield += layer.vapor_volume
                if abs(layer.collapse_rate) > self._COLLAPSE_TOLERANCE:
                    collapsing += 1
            return {
                "layer_count": len(layers),
                "collapse_state_distribution": state_counts,
                "liquid_yield_estimate": total_yield,
                "collapse_flag_count": collapsing,
                "cycle_count": self._cycle_count,
                "foam_collapse_map": "condensation pass complete",
            }