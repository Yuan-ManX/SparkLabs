"""
SparkLabs Engine - Piezometric Aquifer Governor"""

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

class AquiferPhase(Enum):
    """Phases of the piezometric aquifer governor cycle."""
    REGISTER_AQUIFER = "register_aquifer"                  # register confined aquifers with their confining layers and initial heads
    SAMPLE_PIEZOMETRIC_HEAD = "sample_piezometric_head"    # sample each aquifer's piezometric head for this cycle, update pressure regime
    BALANCE_HYDRAULIC_GRADIENT = "balance_hydraulic_gradient"  # compute and balance hydraulic gradients between neighboring aquifers
    GOVERN_ARTESIAN_DISCHARGE = "govern_artesian_discharge"    # throttle or cap artesian discharge to stay within safe pressure envelopes
    EMIT_PRESSURE_REPORT = "emit_pressure_report"          # emit the full pressure report with aquifers, gradients, and discharge budgets


class AquiferKind(Enum):
    """The kind of confined aquifer being governed."""
    CONFINED = "confined"              # fully confined pressure cell
    SEMI_CONFINED = "semi_confined"    # leaky confining layer
    ARTESIAN = "artesian"              # flowing artesian aquifer
    LEAKY = "leaky"                    # leaky aquitard recharge


class PressureRegime(Enum):
    """The pressure regime classification of an aquifer's piezometric head."""
    SUBARTESIAN = "subartesian"        # head below ground surface
    ARTESIAN = "artesian"              # head above ground surface, flowing
    OVERPRESSURED = "overpressured"    # head exceeds safe envelope
    DEPLETED = "depleted"              # head below safe floor


class DischargeState(Enum):
    """The governance state of an artesian well's discharge."""
    PASSIVE = "passive"                # no active discharge
    FLOWING = "flowing"                # free-flowing artesian discharge
    THROTTLED = "throttled"            # discharge throttled to stay in envelope
    CAPPED = "capped"                  # discharge capped to protect the regime


class AquiferState(Enum):
    """State of an individual aquifer through the cycle."""
    PENDING = "pending"                # registered but not yet processed
    REGISTERED = "registered"          # confirmed and classified
    SAMPLED = "sampled"                # piezometric head sampled this cycle
    BALANCED = "balanced"              # hydraulic gradient balanced
    GOVERNED = "governed"              # discharge governed
    EMITTED = "emitted"                # emitted into the pressure report


class Vitality(Enum):
    """Overall vitality of the piezometric aquifer ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    DYNAMIC = "dynamic"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Aquifer:
    """A confined aquifer governed by the piezometric governor."""
    entity_id: str
    aquifer_id: str
    aquifer_label: str
    piezometric_head: float                       # head above datum, meters
    hydraulic_conductivity: float                 # m/s
    storativity: float                            # dimensionless
    confining_layer_thickness: float              # meters
    artesian_pressure: float                      # Pa above hydrostatic
    discharge_rate: float                         # m^3/s
    aquifer_kind: AquiferKind = AquiferKind.CONFINED
    pressure_regime: PressureRegime = PressureRegime.SUBARTESIAN
    discharge_state: DischargeState = DischargeState.PASSIVE
    vitality: Vitality = Vitality.DORMANT
    gradient_balance: float = 0.0                 # net gradient imbalance, m/m
    safe_head_floor: float = 5.0                  # minimum safe head, meters
    safe_head_ceiling: float = 95.0               # maximum safe head, meters
    state: AquiferState = AquiferState.PENDING
    created_at: float = field(default_factory=time.time)
    last_sampled_at: float = 0.0
    note: str = ""


# =============================================================================
# Governor
# =============================================================================

class PiezometricAquiferGovernor:
    """
    Thread-safe singleton that governs confined-aquifer pressure regimes.

    Aquifers are keyed internally by entity_id so each logical aquifer owns
    exactly one entry. The aquifer_id is a generated handle for external
    lookups; lookups by aquifer_id fall back to a linear scan of the
    registered aquifers.

    Usage:
        governor = PiezometricAquiferGovernor.get_instance()
        governor.register_aquifer(
            entity_id="aquifer::alpha",
            aquifer_label="Alpha Confined Cell",
            piezometric_head=42.5,
        )
        governor.cycle()
        aquifer = governor.get_aquifer(aquifer_id)
        report = governor.govern_aquifers()
    """

    _instance: Optional["PiezometricAquiferGovernor"] = None
    _instance_lock = threading.Lock()

    # Capacity caps.
    _MAX_AQUIFERS = 100
    _MAX_EVENTS = 200
    _MAX_GRADIENTS = 200
    _MAX_DISCHARGE_LOGS = 200
    _MAX_REPORTS = 120

    # Domain tuning constants.
    _HEAD_FLUCTUATION = 0.5              # base head fluctuation magnitude, meters
    _GRADIENT_TOLERANCE = 0.02           # below this gradient is balanced
    _SAFE_HEAD_FLOOR_DEFAULT = 5.0       # default minimum safe head, meters
    _SAFE_HEAD_CEILING_DEFAULT = 95.0    # default maximum safe head, meters
    _ARTESIAN_THRESHOLD_HEAD = 50.0      # head above which aquifer is artesian
    _OVERPRESSURED_HEAD = 90.0           # head above which aquifer is overpressured
    _DEPLETED_HEAD = 10.0                # head below which aquifer is depleted
    _DISCHARGE_THROTTLE_FACTOR = 0.7     # throttle factor for artesian discharge
    _DISCHARGE_CAP_FACTOR = 0.3          # cap factor for overpressured discharge
    _MIN_HYDRAULIC_CONDUCTIVITY = 1e-8
    _MAX_HYDRAULIC_CONDUCTIVITY = 1e-2

    def __init__(self) -> None:
        # Instance-level reentrant lock for thread-safe operation.
        self._global_lock = threading.RLock()
        # Internal dict keyed by entity_id (NOT aquifer_id).
        self._aquifers: Dict[str, Aquifer] = {}
        self._gradients: Dict[str, Dict[str, Any]] = {}
        self._discharge_logs: Dict[str, Dict[str, Any]] = {}
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._phase: AquiferPhase = AquiferPhase.REGISTER_AQUIFER
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._aquifers:
            self._seed_synthetic_aquifers()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "PiezometricAquiferGovernor":
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
            "aquifers_registered": 0,
            "phase_runs": 0,
            "heads_sampled": 0,
            "gradients_balanced": 0,
            "overgradient_cells": 0,
            "discharges_governed": 0,
            "discharges_capped": 0,
            "reports_emitted": 0,
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
    def _parse_aquifer_kind(value: Any) -> AquiferKind:
        """Parse an AquiferKind from a string, enum, or None."""
        if value is None:
            return AquiferKind.CONFINED
        if isinstance(value, AquiferKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in AquiferKind:
                if kind.value == lowered:
                    return kind
        return AquiferKind.CONFINED

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_pressure_regime(self, head: float) -> PressureRegime:
        """Classify the pressure regime from the piezometric head."""
        if head >= self._OVERPRESSURED_HEAD:
            return PressureRegime.OVERPRESSURED
        if head <= self._DEPLETED_HEAD:
            return PressureRegime.DEPLETED
        if head >= self._ARTESIAN_THRESHOLD_HEAD:
            return PressureRegime.ARTESIAN
        return PressureRegime.SUBARTESIAN

    def _classify_discharge_state(self, head: float, discharge_rate: float) -> DischargeState:
        """Classify the discharge state from head and current discharge rate."""
        if discharge_rate <= 0.0:
            return DischargeState.PASSIVE
        if head >= self._OVERPRESSURED_HEAD:
            return DischargeState.CAPPED
        if head >= self._ARTESIAN_THRESHOLD_HEAD:
            return DischargeState.THROTTLED
        return DischargeState.FLOWING

    def _derive_vitality(self, aquifer_id: str) -> Vitality:
        """Derive vitality for an aquifer from its post-governance state."""
        aquifer = self._find_aquifer_by_id(aquifer_id)
        if aquifer is None:
            return Vitality.DORMANT
        overgradient = abs(aquifer.gradient_balance) > self._GRADIENT_TOLERANCE * 5.0
        if aquifer.pressure_regime == PressureRegime.OVERPRESSURED and overgradient:
            return Vitality.CHAOTIC
        if aquifer.discharge_state == DischargeState.FLOWING:
            return Vitality.FLOWING
        if aquifer.pressure_regime == PressureRegime.ARTESIAN:
            return Vitality.DYNAMIC
        if aquifer.state in (AquiferState.REGISTERED, AquiferState.SAMPLED):
            return Vitality.STIRRING
        return Vitality.DORMANT

    def _color_for_regime(self, regime: PressureRegime) -> str:
        """Map a pressure regime to a preview color for the editor heatmap."""
        if regime == PressureRegime.SUBARTESIAN:
            return "#4169E1"  # royal blue - calm subartesian head
        if regime == PressureRegime.ARTESIAN:
            return "#32CD32"  # lime green - healthy artesian flow
        if regime == PressureRegime.OVERPRESSURED:
            return "#FF4500"  # orange-red - overpressured danger
        return "#8B0000"      # dark red - depleted head

    # -------------------------------------------------------------------------
    # Aquifer Management
    # -------------------------------------------------------------------------

    def register_aquifer(
        self,
        entity_id: str,
        aquifer_label: str,
        piezometric_head: float = 30.0,
        hydraulic_conductivity: float = 1e-5,
        storativity: float = 1e-4,
        confining_layer_thickness: float = 10.0,
        artesian_pressure: float = 0.0,
        discharge_rate: float = 0.0,
        aquifer_kind: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new confined aquifer with the governor."""
        with self._global_lock:
            if entity_id in self._aquifers:
                return {"error": f"Aquifer already registered: {entity_id}"}
            if len(self._aquifers) >= self._MAX_AQUIFERS:
                return {"error": f"Aquifer cap reached ({self._MAX_AQUIFERS})"}

            aquifer_id = (
                f"aquifer_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            k = max(
                self._MIN_HYDRAULIC_CONDUCTIVITY,
                min(self._MAX_HYDRAULIC_CONDUCTIVITY, float(hydraulic_conductivity)),
            )
            parsed_kind = self._parse_aquifer_kind(aquifer_kind)
            head = float(piezometric_head)
            regime = self._classify_pressure_regime(head)
            discharge = max(0.0, float(discharge_rate))
            discharge_st = self._classify_discharge_state(head, discharge)

            aquifer = Aquifer(
                entity_id=entity_id,
                aquifer_id=aquifer_id,
                aquifer_label=aquifer_label,
                piezometric_head=head,
                hydraulic_conductivity=k,
                storativity=float(storativity),
                confining_layer_thickness=float(confining_layer_thickness),
                artesian_pressure=float(artesian_pressure),
                discharge_rate=discharge,
                aquifer_kind=parsed_kind,
                pressure_regime=regime,
                discharge_state=discharge_st,
                vitality=Vitality.DORMANT,
                gradient_balance=0.0,
                safe_head_floor=self._SAFE_HEAD_FLOOR_DEFAULT,
                safe_head_ceiling=self._SAFE_HEAD_CEILING_DEFAULT,
                state=AquiferState.PENDING,
                created_at=time.time(),
                last_sampled_at=0.0,
                note=note,
            )
            self._aquifers[entity_id] = aquifer
            self._update_stats(aquifers_registered=1)
            self._record_event("aquifer_registered", {
                "aquifer_id": aquifer_id,
                "entity_id": entity_id,
                "aquifer_label": aquifer_label,
                "piezometric_head": head,
                "aquifer_kind": parsed_kind.value,
                "pressure_regime": regime.value,
            })

            return {
                "aquifer_id": aquifer_id,
                "entity_id": entity_id,
                "aquifer_label": aquifer_label,
                "piezometric_head": head,
                "aquifer_kind": parsed_kind.value,
                "pressure_regime": regime.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single piezometric aquifer governor cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic aquifers on the very first cycle if none exist.
            if not self._aquifers and self._cycle_count == 0:
                self._seed_synthetic_aquifers()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = AquiferPhase.REGISTER_AQUIFER
            phase_outputs.append(self._phase_register_aquifer())
            self._phase = AquiferPhase.SAMPLE_PIEZOMETRIC_HEAD
            phase_outputs.append(self._phase_sample_piezometric_head())
            self._phase = AquiferPhase.BALANCE_HYDRAULIC_GRADIENT
            phase_outputs.append(self._phase_balance_hydraulic_gradient())
            self._phase = AquiferPhase.GOVERN_ARTESIAN_DISCHARGE
            phase_outputs.append(self._phase_govern_artesian_discharge())
            self._phase = AquiferPhase.EMIT_PRESSURE_REPORT
            phase_outputs.append(self._phase_emit_pressure_report())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_aquifer(self) -> Dict[str, Any]:
        """Register phase: confirm pending aquifers and their confining layers."""
        registered = 0
        head_sum = 0.0
        for aquifer in self._aquifers.values():
            if aquifer.state == AquiferState.PENDING:
                aquifer.state = AquiferState.REGISTERED
                registered += 1
            # Refresh pressure regime classification in case head was set externally.
            aquifer.pressure_regime = self._classify_pressure_regime(aquifer.piezometric_head)
            head_sum += aquifer.piezometric_head
        avg_head = (head_sum / len(self._aquifers)) if self._aquifers else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_aquifer", {
            "registered": registered,
            "avg_head": avg_head,
        })
        return {
            "phase": "register_aquifer",
            "registered": registered,
            "avg_head": avg_head,
        }

    def _phase_sample_piezometric_head(self) -> Dict[str, Any]:
        """Sample phase: sample each aquifer's piezometric head for this cycle."""
        sampled = 0
        for aquifer in self._aquifers.values():
            if aquifer.state != AquiferState.REGISTERED:
                continue
            # Apply a small stochastic fluctuation to the head.
            fluctuation = random.uniform(
                -self._HEAD_FLUCTUATION, self._HEAD_FLUCTUATION,
            )
            aquifer.piezometric_head = max(
                0.0, aquifer.piezometric_head + fluctuation,
            )
            aquifer.pressure_regime = self._classify_pressure_regime(aquifer.piezometric_head)
            aquifer.last_sampled_at = time.time()
            aquifer.state = AquiferState.SAMPLED
            sampled += 1
        self._update_stats(phase_runs=1, heads_sampled=sampled)
        self._record_event("phase_sample_piezometric_head", {"sampled": sampled})
        return {"phase": "sample_piezometric_head", "sampled": sampled}

    def _phase_balance_hydraulic_gradient(self) -> Dict[str, Any]:
        """Balance phase: compute and balance hydraulic gradients between aquifers."""
        balanced = 0
        overgradient = 0
        aquifers = list(self._aquifers.values())
        for i, aquifer in enumerate(aquifers):
            if aquifer.state != AquiferState.SAMPLED:
                continue
            # Compare this aquifer's head against the average of the others.
            if len(aquifers) <= 1:
                aquifer.gradient_balance = 0.0
            else:
                others = [a for j, a in enumerate(aquifers) if j != i]
                avg_other = sum(a.piezometric_head for a in others) / len(others)
                # Gradient normalized by an assumed inter-aquifer distance.
                distance = max(aquifer.confining_layer_thickness, 1.0)
                aquifer.gradient_balance = (
                    aquifer.piezometric_head - avg_other
                ) / distance
            if abs(aquifer.gradient_balance) <= self._GRADIENT_TOLERANCE:
                balanced += 1
            else:
                overgradient += 1
                # Record the gradient imbalance entry.
                grad_id = (
                    f"grad_{aquifer.aquifer_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                grad_entry = {
                    "gradient_id": grad_id,
                    "aquifer_id": aquifer.aquifer_id,
                    "entity_id": aquifer.entity_id,
                    "gradient_balance": aquifer.gradient_balance,
                    "head": aquifer.piezometric_head,
                    "kind": "overgradient",
                    "created_at": time.time(),
                }
                # Cap the gradient collection.
                if len(self._gradients) >= self._MAX_GRADIENTS:
                    oldest_key = next(iter(self._gradients))
                    self._gradients.pop(oldest_key, None)
                self._gradients[grad_id] = grad_entry
            aquifer.state = AquiferState.BALANCED
        self._update_stats(
            phase_runs=1,
            gradients_balanced=balanced,
            overgradient_cells=overgradient,
        )
        self._record_event("phase_balance_hydraulic_gradient", {
            "balanced": balanced,
            "overgradient": overgradient,
        })
        return {
            "phase": "balance_hydraulic_gradient",
            "balanced": balanced,
            "overgradient": overgradient,
        }

    def _phase_govern_artesian_discharge(self) -> Dict[str, Any]:
        """Govern phase: throttle or cap artesian discharge within the safe envelope."""
        governed = 0
        capped = 0
        for aquifer in self._aquifers.values():
            if aquifer.state != AquiferState.BALANCED:
                continue
            head = aquifer.piezometric_head
            # Clamp the head to the safe envelope.
            if head > aquifer.safe_head_ceiling:
                aquifer.piezometric_head = aquifer.safe_head_ceiling
                head = aquifer.safe_head_ceiling
            elif head < aquifer.safe_head_floor:
                aquifer.piezometric_head = aquifer.safe_head_floor
                head = aquifer.safe_head_floor
            # Re-classify after clamping.
            aquifer.pressure_regime = self._classify_pressure_regime(head)
            # Govern discharge based on the clamped head.
            if aquifer.discharge_rate > 0.0:
                if head >= self._OVERPRESSURED_HEAD:
                    aquifer.discharge_rate *= self._DISCHARGE_CAP_FACTOR
                    aquifer.discharge_state = DischargeState.CAPPED
                    capped += 1
                elif head >= self._ARTESIAN_THRESHOLD_HEAD:
                    aquifer.discharge_rate *= self._DISCHARGE_THROTTLE_FACTOR
                    aquifer.discharge_state = DischargeState.THROTTLED
                else:
                    aquifer.discharge_state = DischargeState.FLOWING
                governed += 1
                # Record the discharge governance log.
                log_id = (
                    f"dis_{aquifer.aquifer_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "log_id": log_id,
                    "aquifer_id": aquifer.aquifer_id,
                    "entity_id": aquifer.entity_id,
                    "head": head,
                    "discharge_rate": aquifer.discharge_rate,
                    "discharge_state": aquifer.discharge_state.value,
                    "created_at": time.time(),
                }
                # Cap the discharge log collection.
                if len(self._discharge_logs) >= self._MAX_DISCHARGE_LOGS:
                    oldest_key = next(iter(self._discharge_logs))
                    self._discharge_logs.pop(oldest_key, None)
                self._discharge_logs[log_id] = log_entry
            else:
                aquifer.discharge_state = DischargeState.PASSIVE
            aquifer.state = AquiferState.GOVERNED
        self._update_stats(
            phase_runs=1,
            discharges_governed=governed,
            discharges_capped=capped,
        )
        self._record_event("phase_govern_artesian_discharge", {
            "governed": governed,
            "capped": capped,
        })
        return {
            "phase": "govern_artesian_discharge",
            "governed": governed,
            "capped": capped,
        }

    def _phase_emit_pressure_report(self) -> Dict[str, Any]:
        """Emit phase: emit the full pressure report with aquifers, gradients, logs."""
        emitted = 0
        for aquifer in self._aquifers.values():
            if aquifer.state != AquiferState.GOVERNED:
                continue
            aquifer.state = AquiferState.EMITTED
            emitted += 1
        # Stamp vitality based on the post-governance state.
        for aquifer in self._aquifers.values():
            aquifer.vitality = self._derive_vitality(aquifer.aquifer_id)
        # Build the consolidated report entry.
        report_id = (
            f"report_{int(time.time() * 1000)}_{random.randint(100, 999)}"
        )
        report = {
            "report_id": report_id,
            "cycle_count": self._cycle_count,
            "aquifer_count": len(self._aquifers),
            "gradient_count": len(self._gradients),
            "discharge_log_count": len(self._discharge_logs),
            "aquifers": [self._aquifer_to_dict(a) for a in self._aquifers.values()],
            "gradients": list(self._gradients.values()),
            "discharge_logs": list(self._discharge_logs.values()),
            "created_at": time.time(),
        }
        # Cap the report collection.
        if len(self._reports) >= self._MAX_REPORTS:
            oldest_key = next(iter(self._reports))
            self._reports.pop(oldest_key, None)
        self._reports[report_id] = report
        self._update_stats(phase_runs=1, reports_emitted=1)
        self._record_event("phase_emit_pressure_report", {
            "emitted": emitted,
            "report_id": report_id,
        })
        return {
            "phase": "emit_pressure_report",
            "emitted": emitted,
            "report_id": report_id,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_aquifer_by_id(self, aquifer_id: str) -> Optional[Aquifer]:
        """Find an aquifer by its aquifer_id (linear scan over entity_id keys)."""
        for aquifer in self._aquifers.values():
            if aquifer.aquifer_id == aquifer_id:
                return aquifer
        return None

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_aquifers(self) -> None:
        """Seed a few synthetic confined aquifers on the first cycle if empty."""
        seeds = [
            ("aquifer::alpha", "Alpha Confined Cell", 42.5, 1e-5, AquiferKind.CONFINED, 0.02),
            ("aquifer::bravo", "Bravo Artesian Cell", 65.0, 5e-5, AquiferKind.ARTESIAN, 0.05),
            ("aquifer::charlie", "Charlie Leaky Cell", 28.0, 2e-6, AquiferKind.LEAKY, 0.0),
        ]
        for entity_id, label, head, k, kind, discharge in seeds:
            if entity_id in self._aquifers:
                continue
            if len(self._aquifers) >= self._MAX_AQUIFERS:
                break
            self.register_aquifer(
                entity_id=entity_id,
                aquifer_label=label,
                piezometric_head=head,
                hydraulic_conductivity=k,
                storativity=1e-4,
                confining_layer_thickness=10.0,
                artesian_pressure=0.0,
                discharge_rate=discharge,
                aquifer_kind=kind.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _aquifer_to_dict(self, aquifer: Aquifer) -> Dict[str, Any]:
        return {
            "entity_id": aquifer.entity_id,
            "aquifer_id": aquifer.aquifer_id,
            "aquifer_label": aquifer.aquifer_label,
            "piezometric_head": aquifer.piezometric_head,
            "hydraulic_conductivity": aquifer.hydraulic_conductivity,
            "storativity": aquifer.storativity,
            "confining_layer_thickness": aquifer.confining_layer_thickness,
            "artesian_pressure": aquifer.artesian_pressure,
            "discharge_rate": aquifer.discharge_rate,
            "aquifer_kind": aquifer.aquifer_kind.value,
            "pressure_regime": aquifer.pressure_regime.value,
            "discharge_state": aquifer.discharge_state.value,
            "vitality": aquifer.vitality.value,
            "gradient_balance": aquifer.gradient_balance,
            "safe_head_floor": aquifer.safe_head_floor,
            "safe_head_ceiling": aquifer.safe_head_ceiling,
            "state": aquifer.state.value,
            "created_at": aquifer.created_at,
            "last_sampled_at": aquifer.last_sampled_at,
            "note": aquifer.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "aquifers": len(self._aquifers),
                "gradients": len(self._gradients),
                "discharge_logs": len(self._discharge_logs),
                "reports": len(self._reports),
                "stats": dict(self._stats),
            }

    def get_aquifers(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            aquifers = sorted(
                self._aquifers.values(),
                key=lambda a: a.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(aquifers),
                "aquifers": [
                    {
                        "aquifer_id": a.aquifer_id,
                        "entity_id": a.entity_id,
                        "aquifer_label": a.aquifer_label,
                        "piezometric_head": a.piezometric_head,
                        "aquifer_kind": a.aquifer_kind.value,
                        "pressure_regime": a.pressure_regime.value,
                        "discharge_state": a.discharge_state.value,
                        "vitality": a.vitality.value,
                    }
                    for a in aquifers
                ],
            }

    def get_aquifer(self, aquifer_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT aquifer_id, so we
        # MUST iterate over values and match on the aquifer_id attribute.
        with self._global_lock:
            for aquifer in self._aquifers.values():
                if aquifer.aquifer_id == aquifer_id:
                    return self._aquifer_to_dict(aquifer)
            return {
                "error": "aquifer not found",
                "aquifer_id": aquifer_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic aquifers if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._aquifers:
                self._seed_synthetic_aquifers()
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
            self._aquifers.clear()
            self._gradients.clear()
            self._discharge_logs.clear()
            self._reports.clear()
            self._phase = AquiferPhase.REGISTER_AQUIFER
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so cycles produce meaningful output.
            if not self._aquifers:
                self._seed_synthetic_aquifers()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Governance
    # -------------------------------------------------------------------------

    def govern_aquifers(self) -> Dict[str, Any]:
        """Govern aquifer pressure: run a governance pass and return a report.

        Computes the current pressure regime distribution, the gradient
        imbalance summary, and the discharge budget without advancing the
        cycle counter.
        """
        with self._global_lock:
            aquifers = list(self._aquifers.values())
            if not aquifers:
                return {
                    "governed": 0,
                    "regime_distribution": {},
                    "discharge_budget": 0.0,
                    "overgradient_count": 0,
                    "report": "no aquifers registered",
                }
            regime_counts: Dict[str, int] = {}
            total_discharge = 0.0
            overgradient = 0
            for aquifer in aquifers:
                regime = self._classify_pressure_regime(aquifer.piezometric_head)
                regime_counts[regime.value] = regime_counts.get(regime.value, 0) + 1
                total_discharge += aquifer.discharge_rate
                if abs(aquifer.gradient_balance) > self._GRADIENT_TOLERANCE:
                    overgradient += 1
            return {
                "governed": len(aquifers),
                "regime_distribution": regime_counts,
                "discharge_budget": total_discharge,
                "overgradient_count": overgradient,
                "cycle_count": self._cycle_count,
                "report": "governance pass complete",
            }
