"""
SparkLabs Engine - Cryogenic Flux Manifold"""

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

class ManifoldPhase(Enum):
    """Phases of the cryogenic flux manifold cycle."""
    REGISTER_FLUX_NODE = "register_flux_node"          # register cryogenic flux nodes with their sensors and initial flows
    SAMPLE_FLOW_RATE = "sample_flow_rate"              # sample each node's flow rate for this cycle, update the thermal regime
    ROUTE_CRYOGENIC_FLUX = "route_cryogenic_flux"      # route cryogenic flux between neighboring branches, flag surges
    CONDENSE_FLOW = "condense_flow"                    # condense the flow against the low-temperature envelope
    EMIT_MANIFOLD_MAP = "emit_manifold_map"            # emit the full manifold map with fluxes, temperatures, and condensation budgets


class FluxKind(Enum):
    """The kind of cryogenic flux being routed through the manifold."""
    LHe = "lhe"                # liquid helium ultra-cold flux
    LN2 = "ln2"                # liquid nitrogen cold flux
    LH2 = "lh2"                # liquid hydrogen flux
    LCH4 = "lch4"              # liquid methane flux


class CoolantKind(Enum):
    """The coolant medium driving the condensation duty of a flux node."""
    HELIUM = "helium"          # gaseous helium coolant loop
    NITROGEN = "nitrogen"      # gaseous nitrogen coolant loop
    HYDROGEN = "hydrogen"      # liquid hydrogen coolant loop
    NEON = "neon"              # neon-neon mixed coolant loop


class FlowPhaseState(Enum):
    """The flow phase state of a cryogenic flux node."""
    VAPOR = "vapor"            # fully vaporized flow
    MIST = "mist"              # two-phase mist flow
    LIQUID = "liquid"          # fully condensed liquid flow
    SLUSH = "slush"            # partially frozen slush flow
    SUPERCOOLED_LIQUID = "supercooled_liquid"  # below boiling point, stable


class ManifoldState(Enum):
    """State of an individual flux node through the manifold cycle."""
    PENDING = "pending"        # registered but not yet processed
    REGISTERED = "registered"  # confirmed and classified
    SAMPLED = "sampled"        # flow rate sampled this cycle
    ROUTED = "routed"          # cryogenic flux routed across branches
    CONDENSED = "condensed"    # flow condensed against the envelope
    EMITTED = "emitted"        # emitted into the manifold map


class Vitality(Enum):
    """Overall vitality of the cryogenic flux manifold ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    DYNAMIC = "dynamic"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FluxNode:
    """A cryogenic flux node routed by the flux manifold."""
    entity_id: str
    flux_id: str
    flux_label: str
    flow_rate: float                              # L/s of cryogenic flux
    coolant_temperature: float                    # K at the node
    line_pressure: float                          # kPa above baseline
    condensation_duty: float                      # kW of condensation duty
    branch_index: int                             # manifold branch the node sits on
    flux_kind: FluxKind = FluxKind.LHe
    coolant_kind: CoolantKind = CoolantKind.HELIUM
    flow_phase: FlowPhaseState = FlowPhaseState.VAPOR
    vitality: Vitality = Vitality.DORMANT
    thermal_balance: float = 0.0                  # net thermal imbalance, kW
    safe_temp_floor: float = 0.5                  # minimum safe temperature, K
    safe_temp_ceiling: float = 90.0               # maximum safe temperature, K
    state: ManifoldState = ManifoldState.PENDING
    created_at: float = field(default_factory=time.time)
    last_sampled_at: float = 0.0
    note: str = ""


# =============================================================================
# Cryogenic Flux Manifold
# =============================================================================

class CryogenicFluxManifold:
    """
    Thread-safe singleton that routes cryogenic flux across a condensation network.

    Flux nodes are keyed internally by entity_id so each logical node owns
    exactly one entry. The flux_id is a generated handle for external lookups;
    lookups by flux_id fall back to a linear scan of the registered fluxes.

    Usage:
        manifold = CryogenicFluxManifold.get_instance()
        manifold.register_flux(
            entity_id="flux::alpha",
            flux_label="Alpha Helium Loop",
            flow_rate=12.5,
        )
        manifold.cycle()
        flux = manifold.get_flux(flux_id)
        route_map = manifold.build_coolant_route_map()
    """

    _instance: Optional["CryogenicFluxManifold"] = None
    _instance_lock = threading.Lock()

    # Capacity caps.
    _MAX_FLUXES = 200
    _MAX_EVENTS = 200
    _MAX_THERMAL_LOGS = 200
    _MAX_CONDENSATION_LOGS = 200
    _MAX_ROUTE_MAPS = 120

    # Domain tuning constants.
    _FLOW_FLUCTUATION = 0.4              # base flow rate fluctuation magnitude, L/s
    _THERMAL_TOLERANCE = 0.03            # below this thermal imbalance is balanced
    _SAFE_TEMP_FLOOR_DEFAULT = 0.5       # default minimum safe temperature, K
    _SAFE_TEMP_CEILING_DEFAULT = 90.0    # default maximum safe temperature, K
    _CONDENSATION_THRESHOLD = 0.7        # duty ratio above which flow is condensing
    _SURGE_FLOW = 1.0                    # flow rate above which node is surging
    _DEPLETED_FLOW = 0.1                 # flow rate below which node is depleted
    _THROTTLE_FACTOR = 0.7               # throttle factor for collecting flow
    _CAP_FACTOR = 0.3                    # cap factor for surging flow
    _MIN_FLOW_RATE = 1e-4
    _MAX_FLOW_RATE = 5.0

    def __init__(self) -> None:
        # Instance-level reentrant lock for thread-safe operation.
        self._global_lock = threading.RLock()
        # Internal dict keyed by entity_id (NOT flux_id).
        self._fluxes: Dict[str, FluxNode] = {}
        self._thermal_logs: Dict[str, Dict[str, Any]] = {}
        self._condensation_logs: Dict[str, Dict[str, Any]] = {}
        self._route_maps: Dict[str, Dict[str, Any]] = {}
        self._phase: ManifoldPhase = ManifoldPhase.REGISTER_FLUX_NODE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._fluxes:
            self._seed_synthetic_fluxes()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "CryogenicFluxManifold":
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
            "fluxes_registered": 0,
            "phase_runs": 0,
            "flows_sampled": 0,
            "fluxes_routed": 0,
            "surge_nodes": 0,
            "flows_condensed": 0,
            "flows_capped": 0,
            "route_maps_emitted": 0,
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
    def _parse_flux_kind(value: Any) -> FluxKind:
        """Parse a FluxKind from a string, enum, or None."""
        if value is None:
            return FluxKind.LHe
        if isinstance(value, FluxKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in FluxKind:
                if kind.value == lowered:
                    return kind
        return FluxKind.LHe

    @staticmethod
    def _parse_coolant_kind(value: Any) -> CoolantKind:
        """Parse a CoolantKind from a string, enum, or None."""
        if value is None:
            return CoolantKind.HELIUM
        if isinstance(value, CoolantKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in CoolantKind:
                if kind.value == lowered:
                    return kind
        return CoolantKind.HELIUM

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_flow_phase(self, flow_rate: float, duty_ratio: float) -> FlowPhaseState:
        """Classify the flow phase from flow rate and condensation duty ratio."""
        if flow_rate >= self._SURGE_FLOW and duty_ratio >= self._CONDENSATION_THRESHOLD:
            return FlowPhaseState.SLUSH
        if duty_ratio >= self._CONDENSATION_THRESHOLD:
            return FlowPhaseState.LIQUID
        if flow_rate <= self._DEPLETED_FLOW:
            return FlowPhaseState.VAPOR
        if duty_ratio >= self._CONDENSATION_THRESHOLD * 0.5:
            return FlowPhaseState.SUPERCOOLED_LIQUID
        return FlowPhaseState.MIST

    def _derive_vitality(self, flux_id: str) -> Vitality:
        """Derive vitality for a flux node from its post-condensation state."""
        flux = self._find_flux_by_id(flux_id)
        if flux is None:
            return Vitality.DORMANT
        surging = abs(flux.thermal_balance) > self._THERMAL_TOLERANCE * 5.0
        if flux.flow_phase == FlowPhaseState.SLUSH and surging:
            return Vitality.CHAOTIC
        if flux.flow_phase == FlowPhaseState.MIST:
            return Vitality.FLOWING
        if flux.flow_phase == FlowPhaseState.LIQUID:
            return Vitality.DYNAMIC
        if flux.state in (ManifoldState.REGISTERED, ManifoldState.SAMPLED):
            return Vitality.STIRRING
        return Vitality.DORMANT

    def _color_for_phase(self, phase: FlowPhaseState) -> str:
        """Map a flow phase to a preview color for the editor manifold map."""
        if phase == FlowPhaseState.VAPOR:
            return "#87CEEB"  # sky blue - calm vapor flow
        if phase == FlowPhaseState.MIST:
            return "#B0C4DE"  # light steel blue - drifting mist
        if phase == FlowPhaseState.LIQUID:
            return "#4682B4"  # steel blue - condensed liquid
        if phase == FlowPhaseState.SUPERCOOLED_LIQUID:
            return "#5F9EA0"  # cadet blue - supercooled liquid
        return "#2F4F4F"      # dark slate gray - slush flow

    # -------------------------------------------------------------------------
    # Flux Management
    # -------------------------------------------------------------------------

    def register_flux(
        self,
        entity_id: str,
        flux_label: str,
        flow_rate: float = 8.0,
        coolant_temperature: float = 20.0,
        line_pressure: float = 0.0,
        condensation_duty: float = 0.0,
        branch_index: int = 0,
        flux_kind: Optional[str] = None,
        coolant_kind: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new cryogenic flux node with the manifold."""
        with self._global_lock:
            if entity_id in self._fluxes:
                return {"error": f"Flux already registered: {entity_id}"}
            if len(self._fluxes) >= self._MAX_FLUXES:
                return {"error": f"Flux cap reached ({self._MAX_FLUXES})"}

            flux_id = (
                f"flux_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            flow = max(
                self._MIN_FLOW_RATE,
                min(self._MAX_FLOW_RATE, float(flow_rate)),
            )
            parsed_kind = self._parse_flux_kind(flux_kind)
            parsed_coolant = self._parse_coolant_kind(coolant_kind)
            duty_ratio = max(0.0, min(1.0, float(condensation_duty)))
            phase = self._classify_flow_phase(flow, duty_ratio)

            flux = FluxNode(
                entity_id=entity_id,
                flux_id=flux_id,
                flux_label=flux_label,
                flow_rate=flow,
                coolant_temperature=float(coolant_temperature),
                line_pressure=float(line_pressure),
                condensation_duty=float(condensation_duty),
                branch_index=int(branch_index),
                flux_kind=parsed_kind,
                coolant_kind=parsed_coolant,
                flow_phase=phase,
                vitality=Vitality.DORMANT,
                thermal_balance=0.0,
                safe_temp_floor=self._SAFE_TEMP_FLOOR_DEFAULT,
                safe_temp_ceiling=self._SAFE_TEMP_CEILING_DEFAULT,
                state=ManifoldState.PENDING,
                created_at=time.time(),
                last_sampled_at=0.0,
                note=note,
            )
            self._fluxes[entity_id] = flux
            self._update_stats(fluxes_registered=1)
            self._record_event("flux_registered", {
                "flux_id": flux_id,
                "entity_id": entity_id,
                "flux_label": flux_label,
                "flow_rate": flux.flow_rate,
                "flux_kind": parsed_kind.value,
                "flow_phase": phase.value,
            })

            return {
                "flux_id": flux_id,
                "entity_id": entity_id,
                "flux_label": flux_label,
                "flow_rate": flux.flow_rate,
                "flux_kind": parsed_kind.value,
                "flow_phase": phase.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single cryogenic flux manifold cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic fluxes on the very first cycle if none exist.
            if not self._fluxes and self._cycle_count == 0:
                self._seed_synthetic_fluxes()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = ManifoldPhase.REGISTER_FLUX_NODE
            phase_outputs.append(self._phase_register_flux_node())
            self._phase = ManifoldPhase.SAMPLE_FLOW_RATE
            phase_outputs.append(self._phase_sample_flow_rate())
            self._phase = ManifoldPhase.ROUTE_CRYOGENIC_FLUX
            phase_outputs.append(self._phase_route_cryogenic_flux())
            self._phase = ManifoldPhase.CONDENSE_FLOW
            phase_outputs.append(self._phase_condense_flow())
            self._phase = ManifoldPhase.EMIT_MANIFOLD_MAP
            phase_outputs.append(self._phase_emit_manifold_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_flux_node(self) -> Dict[str, Any]:
        """Register phase: confirm pending flux nodes and their branch sensors."""
        registered = 0
        flow_sum = 0.0
        for flux in self._fluxes.values():
            if flux.state == ManifoldState.PENDING:
                flux.state = ManifoldState.REGISTERED
                registered += 1
            # Refresh flow phase classification in case flow was set externally.
            duty_ratio = max(0.0, min(1.0, flux.condensation_duty))
            flux.flow_phase = self._classify_flow_phase(flux.flow_rate, duty_ratio)
            flow_sum += flux.flow_rate
        avg_flow = (flow_sum / len(self._fluxes)) if self._fluxes else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_flux_node", {
            "registered": registered,
            "avg_flow": avg_flow,
        })
        return {
            "phase": "register_flux_node",
            "registered": registered,
            "avg_flow": avg_flow,
        }

    def _phase_sample_flow_rate(self) -> Dict[str, Any]:
        """Sample phase: sample each node's flow rate for this cycle."""
        sampled = 0
        for flux in self._fluxes.values():
            if flux.state != ManifoldState.REGISTERED:
                continue
            # Apply a small stochastic fluctuation to the flow rate.
            fluctuation = random.uniform(
                -self._FLOW_FLUCTUATION, self._FLOW_FLUCTUATION,
            )
            flux.flow_rate = max(0.0, flux.flow_rate + fluctuation)
            # Temperature drifts slightly with flow, clamped to physical bounds.
            drift = fluctuation * 0.5
            flux.coolant_temperature = max(
                self._MIN_FLOW_RATE,
                min(self._MAX_FLOW_RATE * 40.0, flux.coolant_temperature + drift),
            )
            duty_ratio = max(0.0, min(1.0, flux.condensation_duty))
            flux.flow_phase = self._classify_flow_phase(flux.flow_rate, duty_ratio)
            flux.last_sampled_at = time.time()
            flux.state = ManifoldState.SAMPLED
            sampled += 1
        self._update_stats(phase_runs=1, flows_sampled=sampled)
        self._record_event("phase_sample_flow_rate", {"sampled": sampled})
        return {"phase": "sample_flow_rate", "sampled": sampled}

    def _phase_route_cryogenic_flux(self) -> Dict[str, Any]:
        """Route phase: route cryogenic flux between neighboring branches."""
        routed = 0
        surging = 0
        fluxes = list(self._fluxes.values())
        for i, flux in enumerate(fluxes):
            if flux.state != ManifoldState.SAMPLED:
                continue
            # Compare this node's flow against the average of the others.
            if len(fluxes) <= 1:
                flux.thermal_balance = 0.0
            else:
                others = [f for j, f in enumerate(fluxes) if j != i]
                avg_other = sum(f.flow_rate for f in others) / len(others)
                # Thermal imbalance normalized by branch span.
                branch_span = max(flux.branch_index + 1, 1)
                flux.thermal_balance = (
                    flux.flow_rate - avg_other
                ) / branch_span
            if abs(flux.thermal_balance) <= self._THERMAL_TOLERANCE:
                routed += 1
            else:
                surging += 1
                # Record the thermal imbalance entry.
                log_id = (
                    f"thermal_{flux.flux_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "thermal_log_id": log_id,
                    "flux_id": flux.flux_id,
                    "entity_id": flux.entity_id,
                    "thermal_balance": flux.thermal_balance,
                    "flow_rate": flux.flow_rate,
                    "kind": "surge",
                    "created_at": time.time(),
                }
                # Cap the thermal log collection.
                if len(self._thermal_logs) >= self._MAX_THERMAL_LOGS:
                    oldest_key = next(iter(self._thermal_logs))
                    self._thermal_logs.pop(oldest_key, None)
                self._thermal_logs[log_id] = log_entry
            flux.state = ManifoldState.ROUTED
        self._update_stats(
            phase_runs=1,
            fluxes_routed=routed,
            surge_nodes=surging,
        )
        self._record_event("phase_route_cryogenic_flux", {
            "routed": routed,
            "surging": surging,
        })
        return {
            "phase": "route_cryogenic_flux",
            "routed": routed,
            "surging": surging,
        }

    def _phase_condense_flow(self) -> Dict[str, Any]:
        """Condense phase: condense the flow against the low-temperature envelope."""
        condensed = 0
        capped = 0
        for flux in self._fluxes.values():
            if flux.state != ManifoldState.ROUTED:
                continue
            temp = flux.coolant_temperature
            # Clamp the temperature to the safe envelope.
            if temp > flux.safe_temp_ceiling:
                flux.coolant_temperature = flux.safe_temp_ceiling
                temp = flux.safe_temp_ceiling
            elif temp < flux.safe_temp_floor:
                flux.coolant_temperature = flux.safe_temp_floor
                temp = flux.safe_temp_floor
            # Re-classify after clamping.
            duty_ratio = max(0.0, min(1.0, flux.condensation_duty))
            flux.flow_phase = self._classify_flow_phase(flux.flow_rate, duty_ratio)
            # Condense dispersion based on the clamped temperature.
            if flux.flow_rate > 0.0:
                if temp <= self._SAFE_TEMP_FLOOR_DEFAULT * 10.0:
                    flux.flow_rate *= self._CAP_FACTOR
                    capped += 1
                elif duty_ratio >= self._CONDENSATION_THRESHOLD * 0.5:
                    flux.flow_rate *= self._THROTTLE_FACTOR
                condensed += 1
                # Record the condensation log.
                log_id = (
                    f"cond_{flux.flux_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "condensation_id": log_id,
                    "flux_id": flux.flux_id,
                    "entity_id": flux.entity_id,
                    "coolant_temperature": temp,
                    "flow_rate": flux.flow_rate,
                    "flow_phase": flux.flow_phase.value,
                    "created_at": time.time(),
                }
                # Cap the condensation log collection.
                if len(self._condensation_logs) >= self._MAX_CONDENSATION_LOGS:
                    oldest_key = next(iter(self._condensation_logs))
                    self._condensation_logs.pop(oldest_key, None)
                self._condensation_logs[log_id] = log_entry
            # Line pressure tracks temperature within the envelope.
            flux.line_pressure = temp * 15.0
            flux.state = ManifoldState.CONDENSED
        self._update_stats(
            phase_runs=1,
            flows_condensed=condensed,
            flows_capped=capped,
        )
        self._record_event("phase_condense_flow", {
            "condensed": condensed,
            "capped": capped,
        })
        return {
            "phase": "condense_flow",
            "condensed": condensed,
            "capped": capped,
        }

    def _phase_emit_manifold_map(self) -> Dict[str, Any]:
        """Emit phase: emit the full manifold map with fluxes, temps, logs."""
        emitted = 0
        for flux in self._fluxes.values():
            if flux.state != ManifoldState.CONDENSED:
                continue
            flux.state = ManifoldState.EMITTED
            emitted += 1
        # Stamp vitality based on the post-condensation state.
        for flux in self._fluxes.values():
            flux.vitality = self._derive_vitality(flux.flux_id)
        # Build the consolidated manifold map entry.
        map_id = (
            f"map_{int(time.time() * 1000)}_{random.randint(100, 999)}"
        )
        manifold_map = {
            "map_id": map_id,
            "cycle_count": self._cycle_count,
            "flux_count": len(self._fluxes),
            "thermal_log_count": len(self._thermal_logs),
            "condensation_log_count": len(self._condensation_logs),
            "fluxes": [self._flux_to_dict(f) for f in self._fluxes.values()],
            "thermal_logs": list(self._thermal_logs.values()),
            "condensation_logs": list(self._condensation_logs.values()),
            "created_at": time.time(),
        }
        # Cap the manifold map collection.
        if len(self._route_maps) >= self._MAX_ROUTE_MAPS:
            oldest_key = next(iter(self._route_maps))
            self._route_maps.pop(oldest_key, None)
        self._route_maps[map_id] = manifold_map
        self._update_stats(phase_runs=1, route_maps_emitted=1)
        self._record_event("phase_emit_manifold_map", {
            "emitted": emitted,
            "map_id": map_id,
        })
        return {
            "phase": "emit_manifold_map",
            "emitted": emitted,
            "map_id": map_id,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_flux_by_id(self, flux_id: str) -> Optional[FluxNode]:
        """Find a flux by its flux_id (linear scan over entity_id keys)."""
        for flux in self._fluxes.values():
            if flux.flux_id == flux_id:
                return flux
        return None

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_fluxes(self) -> None:
        """Seed a few synthetic cryogenic flux nodes on the first cycle if empty."""
        seeds = [
            ("flux::alpha", "Alpha Helium Loop", 12.5, 20.0, 0, FluxKind.LHe, CoolantKind.HELIUM),
            ("flux::bravo", "Bravo Nitrogen Loop", 18.0, 77.0, 1, FluxKind.LN2, CoolantKind.NITROGEN),
            ("flux::charlie", "Charlie Hydrogen Loop", 6.0, 20.0, 2, FluxKind.LH2, CoolantKind.HYDROGEN),
        ]
        for entity_id, label, flow, temp, branch, kind, coolant in seeds:
            if entity_id in self._fluxes:
                continue
            if len(self._fluxes) >= self._MAX_FLUXES:
                break
            self.register_flux(
                entity_id=entity_id,
                flux_label=label,
                flow_rate=flow,
                coolant_temperature=temp,
                line_pressure=0.0,
                condensation_duty=0.4,
                branch_index=branch,
                flux_kind=kind.value,
                coolant_kind=coolant.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _flux_to_dict(self, flux: FluxNode) -> Dict[str, Any]:
        return {
            "entity_id": flux.entity_id,
            "flux_id": flux.flux_id,
            "flux_label": flux.flux_label,
            "flow_rate": flux.flow_rate,
            "coolant_temperature": flux.coolant_temperature,
            "line_pressure": flux.line_pressure,
            "condensation_duty": flux.condensation_duty,
            "branch_index": flux.branch_index,
            "flux_kind": flux.flux_kind.value,
            "coolant_kind": flux.coolant_kind.value,
            "flow_phase": flux.flow_phase.value,
            "vitality": flux.vitality.value,
            "thermal_balance": flux.thermal_balance,
            "safe_temp_floor": flux.safe_temp_floor,
            "safe_temp_ceiling": flux.safe_temp_ceiling,
            "state": flux.state.value,
            "created_at": flux.created_at,
            "last_sampled_at": flux.last_sampled_at,
            "note": flux.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "fluxes": len(self._fluxes),
                "thermal_logs": len(self._thermal_logs),
                "condensation_logs": len(self._condensation_logs),
                "route_maps": len(self._route_maps),
                "stats": dict(self._stats),
            }

    def get_fluxes(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            fluxes = sorted(
                self._fluxes.values(),
                key=lambda f: f.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(fluxes),
                "fluxes": [
                    {
                        "flux_id": f.flux_id,
                        "entity_id": f.entity_id,
                        "flux_label": f.flux_label,
                        "flow_rate": f.flow_rate,
                        "flux_kind": f.flux_kind.value,
                        "flow_phase": f.flow_phase.value,
                        "vitality": f.vitality.value,
                        "branch_index": f.branch_index,
                    }
                    for f in fluxes
                ],
            }

    def get_flux(self, flux_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT flux_id, so we
        # MUST iterate over values and match on the flux_id attribute.
        with self._global_lock:
            for flux in self._fluxes.values():
                if flux.flux_id == flux_id:
                    return self._flux_to_dict(flux)
            return {
                "error": "flux not found",
                "flux_id": flux_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic fluxes if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._fluxes:
                self._seed_synthetic_fluxes()
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
            self._fluxes.clear()
            self._thermal_logs.clear()
            self._condensation_logs.clear()
            self._route_maps.clear()
            self._phase = ManifoldPhase.REGISTER_FLUX_NODE
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so cycles produce meaningful output.
            if not self._fluxes:
                self._seed_synthetic_fluxes()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Routing
    # -------------------------------------------------------------------------

    def build_coolant_route_map(self) -> Dict[str, Any]:
        """Build a coolant route map: run a routing pass and return the map.

        Computes the current flow phase distribution, the thermal imbalance
        summary, and the condensation budget without advancing the cycle
        counter.
        """
        with self._global_lock:
            fluxes = list(self._fluxes.values())
            if not fluxes:
                return {
                    "routed": 0,
                    "phase_distribution": {},
                    "condensation_budget": 0.0,
                    "surge_count": 0,
                    "coolant_route_map": "no fluxes registered",
                }
            phase_counts: Dict[str, int] = {}
            total_duty = 0.0
            surging = 0
            for flux in fluxes:
                duty_ratio = max(0.0, min(1.0, flux.condensation_duty))
                phase = self._classify_flow_phase(flux.flow_rate, duty_ratio)
                phase_counts[phase.value] = phase_counts.get(phase.value, 0) + 1
                total_duty += flux.condensation_duty
                if abs(flux.thermal_balance) > self._THERMAL_TOLERANCE:
                    surging += 1
            return {
                "routed": len(fluxes),
                "phase_distribution": phase_counts,
                "condensation_budget": total_duty,
                "surge_count": surging,
                "cycle_count": self._cycle_count,
                "coolant_route_map": "routing pass complete",
            }