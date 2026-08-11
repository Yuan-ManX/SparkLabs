"""
SparkLabs Engine - Fulminant Geyser Arbiter"""

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

class GeyserPhase(Enum):
    """Phases of the fulminant geyser arbiter cycle."""
    REGISTER_SPRING = "register_spring"                              # register geyser springs with their sensors and initial pressure
    MEASURE_RESERVOIR_PRESSURE = "measure_reservoir_pressure"        # measure each spring's reservoir pressure for this cycle, update the regime
    JUDGE_ERUPTION_TIMING = "judge_eruption_timing"                  # judge the eruption timing of each jet against the reservoir volume
    SETTLE_DISCHARGE_ORDER = "settle_discharge_order"                # settle the discharge order of the jets against their eruption timing
    EMIT_ERUPTION_ORDER_MAP = "emit_eruption_order_map"              # emit the full eruption-order map with pressures, timings, and orders


class SpringKind(Enum):
    """The mineral kind of a geyser spring."""
    SILICEOUS = "siliceous"          # silica-rich geyser water
    SULFURIC = "sulfuric"            # sulfur-rich acidic spring
    BICARBONATE = "bicarbonate"      # bicarbonate-rich spring
    CHLORIDE = "chloride"            # chloride-rich spring
    MIXED = "mixed"                  # mixed mineral spring


class DischargeKind(Enum):
    """The jet discharge regime of a geyser spring."""
    QUIET = "quiet"                  # quiet simmering spring
    BUBBLING = "bubbling"            # gentle bubbling jets
    SPURTING = "spurting"            # periodic spurting jets
    FULMINANT = "fulminant"          # explosive fulminant jets
    COLUMNAR = "columnar"            # towering column jets


class TimingState(Enum):
    """The eruption timing phase state of a geyser spring."""
    DORMANT = "dormant"              # low pressure, dormant spring
    PRESSURIZING = "pressurizing"    # reservoir building pressure
    IMPENDING = "impending"          # eruption approaching
    IMMINENT = "imminent"            # eruption threshold imminent
    ERUPTIVE = "eruptive"            # currently eruptive


class SpringState(Enum):
    """State of an individual geyser spring through the arbiter cycle."""
    PENDING = "pending"              # registered but not yet processed
    REGISTERED = "registered"        # confirmed and classified
    MEASURED = "measured"            # reservoir pressure measured this cycle
    JUDGED = "judged"                # eruption timing judged
    ORDERED = "ordered"              # discharge order settled
    EMITTED = "emitted"              # emitted into the eruption order map


class Vitality(Enum):
    """Overall vitality of the fulminant geyser ecosystem."""
    QUIET = "quiet"
    SIMMERING = "simmering"
    ACTIVE = "active"
    VIOLENT = "violent"
    CATASTROPHIC = "catastrophic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class GeyserSpring:
    """A fulminant geyser spring arbitrated by the geyser engine."""
    entity_id: str
    spring_id: str
    spring_label: str
    reservoir_pressure: float                    # MPa of reservoir pressure
    vent_temperature: float                      # K at the geyser vent
    jet_aperture: float                          # m of jet opening diameter
    reservoir_volume: float                      # km^3 of reservoir volume
    branch_index: int                            # branch of the geyser network
    spring_kind: SpringKind = SpringKind.SILICEOUS
    discharge_kind: DischargeKind = DischargeKind.QUIET
    timing_state: TimingState = TimingState.DORMANT
    vitality: Vitality = Vitality.QUIET
    timing_balance: float = 0.0                  # net timing imbalance, MPa
    safe_pressure_floor: float = 0.5             # minimum safe reservoir pressure, MPa
    safe_pressure_ceiling: float = 90.0          # maximum safe reservoir pressure, MPa
    state: SpringState = SpringState.PENDING
    created_at: float = field(default_factory=time.time)
    last_measured_at: float = 0.0
    note: str = ""


# =============================================================================
# Fulminant Geyser Arbiter
# =============================================================================

class FulminantGeyserArbiter:
    """
    Thread-safe singleton that arbitrates fulminant geysers.

    Springs are keyed internally by entity_id so each logical spring owns
    exactly one entry. The spring_id is a generated handle for external
    lookups; lookups by spring_id fall back to a linear scan of the
    registered springs.

    Usage:
        arbiter = FulminantGeyserArbiter.get_instance()
        arbiter.register_spring(
            entity_id="spring::alpha",
            spring_label="Alpha Siliceous Geyser",
            reservoir_pressure=12.5,
        )
        arbiter.cycle()
        spring = arbiter.get_spring(spring_id)
        order_map = arbiter.build_eruption_order_map()
    """

    _instance: Optional["FulminantGeyserArbiter"] = None
    _instance_lock = threading.Lock()

    # Capacity caps.
    _MAX_SPRINGS = 200
    _MAX_EVENTS = 200
    _MAX_TIMING_LOGS = 200
    _MAX_ERUPTION_LOGS = 200
    _MAX_ORDER_MAPS = 120

    # Domain tuning constants.
    _PRESSURE_FLUCTUATION = 0.4           # base reservoir pressure fluctuation magnitude, MPa
    _TIMING_TOLERANCE = 0.03              # below this timing imbalance is balanced
    _SAFE_PRESSURE_FLOOR_DEFAULT = 0.5    # default minimum safe reservoir pressure, MPa
    _SAFE_PRESSURE_CEILING_DEFAULT = 90.0  # default maximum safe reservoir pressure, MPa
    _ERUPTION_THRESHOLD = 0.7             # pressure ratio above which the jet is erupting
    _FULMINANT_PRESSURE = 1.0             # pressure above which the jet is fulminant
    _DEPLETED_PRESSURE = 0.1              # pressure below which the jet is depleted
    _THROTTLE_FACTOR = 0.7                # throttle factor for collecting pressure
    _CAP_FACTOR = 0.3                     # cap factor for fulminant pressure
    _MIN_RESERVOIR_PRESSURE = 1e-4
    _MAX_RESERVOIR_PRESSURE = 5.0

    def __init__(self) -> None:
        # Instance-level reentrant lock for thread-safe operation.
        self._global_lock = threading.RLock()
        # Internal dict keyed by entity_id (NOT spring_id).
        self._springs: Dict[str, GeyserSpring] = {}
        self._timing_logs: Dict[str, Dict[str, Any]] = {}
        self._eruption_logs: Dict[str, Dict[str, Any]] = {}
        self._order_maps: Dict[str, Dict[str, Any]] = {}
        self._phase: GeyserPhase = GeyserPhase.REGISTER_SPRING
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._springs:
            self._seed_synthetic_springs()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "FulminantGeyserArbiter":
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
            "springs_registered": 0,
            "phase_runs": 0,
            "pressures_measured": 0,
            "springs_judged": 0,
            "timing_surges": 0,
            "eruptions_predicted": 0,
            "spring_caps": 0,
            "order_maps_emitted": 0,
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
    def _parse_spring_kind(value: Any) -> SpringKind:
        """Parse a SpringKind from a string, enum, or None."""
        if value is None:
            return SpringKind.SILICEOUS
        if isinstance(value, SpringKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in SpringKind:
                if kind.value == lowered:
                    return kind
        return SpringKind.SILICEOUS

    @staticmethod
    def _parse_discharge_kind(value: Any) -> DischargeKind:
        """Parse a DischargeKind from a string, enum, or None."""
        if value is None:
            return DischargeKind.QUIET
        if isinstance(value, DischargeKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in DischargeKind:
                if kind.value == lowered:
                    return kind
        return DischargeKind.QUIET

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_timing_state(self, reservoir_pressure: float, pressure_ratio: float) -> TimingState:
        """Classify the eruption timing state from pressure and pressure ratio."""
        if reservoir_pressure >= self._FULMINANT_PRESSURE and pressure_ratio >= self._ERUPTION_THRESHOLD:
            return TimingState.ERUPTIVE
        if pressure_ratio >= self._ERUPTION_THRESHOLD:
            return TimingState.IMMINENT
        if reservoir_pressure <= self._DEPLETED_PRESSURE:
            return TimingState.DORMANT
        if pressure_ratio >= self._ERUPTION_THRESHOLD * 0.5:
            return TimingState.PRESSURIZING
        return TimingState.IMPENDING

    def _derive_vitality(self, spring_id: str) -> Vitality:
        """Derive vitality for a geyser spring from its post-judgment state."""
        spring = self._find_spring_by_id(spring_id)
        if spring is None:
            return Vitality.QUIET
        surging = abs(spring.timing_balance) > self._TIMING_TOLERANCE * 5.0
        if spring.timing_state == TimingState.ERUPTIVE and surging:
            return Vitality.CATASTROPHIC
        if spring.timing_state == TimingState.IMPENDING:
            return Vitality.SIMMERING
        if spring.timing_state == TimingState.PRESSURIZING:
            return Vitality.ACTIVE
        if spring.state in (SpringState.REGISTERED, SpringState.MEASURED):
            return Vitality.VIOLENT
        return Vitality.QUIET

    def _color_for_state(self, state: TimingState) -> str:
        """Map an eruption timing state to a preview color for the editor order map."""
        if state == TimingState.DORMANT:
            return "#8B0000"  # dark red - dormant spring
        if state == TimingState.IMPENDING:
            return "#FF4500"  # orange red - impending eruption
        if state == TimingState.PRESSURIZING:
            return "#FF8C00"  # dark orange - pressurizing reservoir
        if state == TimingState.IMMINENT:
            return "#FFA500"  # orange - imminent eruption
        return "#00CED1"      # dark turquoise - eruptive jet column

    # -------------------------------------------------------------------------
    # Spring Management
    # -------------------------------------------------------------------------

    def register_spring(
        self,
        entity_id: str,
        spring_label: str,
        reservoir_pressure: float = 8.0,
        vent_temperature: float = 380.0,
        jet_aperture: float = 1.0,
        reservoir_volume: float = 5.0,
        branch_index: int = 0,
        spring_kind: Optional[str] = None,
        discharge_kind: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new fulminant geyser spring with the engine."""
        with self._global_lock:
            if entity_id in self._springs:
                return {"error": f"Spring already registered: {entity_id}"}
            if len(self._springs) >= self._MAX_SPRINGS:
                return {"error": f"Spring cap reached ({self._MAX_SPRINGS})"}

            spring_id = (
                f"spring_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            pressure = max(
                self._MIN_RESERVOIR_PRESSURE,
                min(self._MAX_RESERVOIR_PRESSURE, float(reservoir_pressure)),
            )
            parsed_kind = self._parse_spring_kind(spring_kind)
            parsed_discharge = self._parse_discharge_kind(discharge_kind)
            pressure_ratio = max(0.0, min(1.0, reservoir_volume / 10.0))
            state = self._classify_timing_state(pressure, pressure_ratio)

            spring = GeyserSpring(
                entity_id=entity_id,
                spring_id=spring_id,
                spring_label=spring_label,
                reservoir_pressure=pressure,
                vent_temperature=float(vent_temperature),
                jet_aperture=float(jet_aperture),
                reservoir_volume=float(reservoir_volume),
                branch_index=int(branch_index),
                spring_kind=parsed_kind,
                discharge_kind=parsed_discharge,
                timing_state=state,
                vitality=Vitality.QUIET,
                timing_balance=0.0,
                safe_pressure_floor=self._SAFE_PRESSURE_FLOOR_DEFAULT,
                safe_pressure_ceiling=self._SAFE_PRESSURE_CEILING_DEFAULT,
                state=SpringState.PENDING,
                created_at=time.time(),
                last_measured_at=0.0,
                note=note,
            )
            self._springs[entity_id] = spring
            self._update_stats(springs_registered=1)
            self._record_event("spring_registered", {
                "spring_id": spring_id,
                "entity_id": entity_id,
                "spring_label": spring_label,
                "reservoir_pressure": spring.reservoir_pressure,
                "spring_kind": parsed_kind.value,
                "timing_state": state.value,
            })

            return {
                "spring_id": spring_id,
                "entity_id": entity_id,
                "spring_label": spring_label,
                "reservoir_pressure": spring.reservoir_pressure,
                "spring_kind": parsed_kind.value,
                "timing_state": state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single fulminant geyser arbiter cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic springs on the very first cycle if none exist.
            if not self._springs and self._cycle_count == 0:
                self._seed_synthetic_springs()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = GeyserPhase.REGISTER_SPRING
            phase_outputs.append(self._phase_register_spring())
            self._phase = GeyserPhase.MEASURE_RESERVOIR_PRESSURE
            phase_outputs.append(self._phase_measure_reservoir_pressure())
            self._phase = GeyserPhase.JUDGE_ERUPTION_TIMING
            phase_outputs.append(self._phase_judge_eruption_timing())
            self._phase = GeyserPhase.SETTLE_DISCHARGE_ORDER
            phase_outputs.append(self._phase_settle_discharge_order())
            self._phase = GeyserPhase.EMIT_ERUPTION_ORDER_MAP
            phase_outputs.append(self._phase_emit_eruption_order_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_spring(self) -> Dict[str, Any]:
        """Register phase: confirm pending geyser springs and their sensors."""
        registered = 0
        pressure_sum = 0.0
        for spring in self._springs.values():
            if spring.state == SpringState.PENDING:
                spring.state = SpringState.REGISTERED
                registered += 1
            # Refresh timing state classification in case pressure was set externally.
            pressure_ratio = max(0.0, min(1.0, spring.reservoir_volume / 10.0))
            spring.timing_state = self._classify_timing_state(spring.reservoir_pressure, pressure_ratio)
            pressure_sum += spring.reservoir_pressure
        avg_pressure = (pressure_sum / len(self._springs)) if self._springs else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_spring", {
            "registered": registered,
            "avg_pressure": avg_pressure,
        })
        return {
            "phase": "register_spring",
            "registered": registered,
            "avg_pressure": avg_pressure,
        }

    def _phase_measure_reservoir_pressure(self) -> Dict[str, Any]:
        """Measure phase: measure each spring's reservoir pressure for this cycle."""
        measured = 0
        for spring in self._springs.values():
            if spring.state != SpringState.REGISTERED:
                continue
            # Apply a small stochastic fluctuation to the reservoir pressure.
            fluctuation = random.uniform(
                -self._PRESSURE_FLUCTUATION, self._PRESSURE_FLUCTUATION,
            )
            spring.reservoir_pressure = max(0.0, spring.reservoir_pressure + fluctuation)
            # Vent temperature drifts slightly with pressure, clamped to physical bounds.
            drift = fluctuation * 50.0
            spring.vent_temperature = max(
                self._MIN_RESERVOIR_PRESSURE,
                min(self._MAX_RESERVOIR_PRESSURE * 800.0, spring.vent_temperature + drift),
            )
            pressure_ratio = max(0.0, min(1.0, spring.reservoir_volume / 10.0))
            spring.timing_state = self._classify_timing_state(spring.reservoir_pressure, pressure_ratio)
            spring.last_measured_at = time.time()
            spring.state = SpringState.MEASURED
            measured += 1
        self._update_stats(phase_runs=1, pressures_measured=measured)
        self._record_event("phase_measure_reservoir_pressure", {"measured": measured})
        return {"phase": "measure_reservoir_pressure", "measured": measured}

    def _phase_judge_eruption_timing(self) -> Dict[str, Any]:
        """Judge phase: judge the eruption timing of each jet against the reservoir."""
        judged = 0
        surging = 0
        springs = list(self._springs.values())
        for i, spring in enumerate(springs):
            if spring.state != SpringState.MEASURED:
                continue
            # Compare this spring's pressure against the average of the others.
            if len(springs) <= 1:
                spring.timing_balance = 0.0
            else:
                others = [s for j, s in enumerate(springs) if j != i]
                avg_other = sum(s.reservoir_pressure for s in others) / len(others)
                # Timing imbalance normalized by branch span.
                branch_span = max(spring.branch_index + 1, 1)
                spring.timing_balance = (
                    spring.reservoir_pressure - avg_other
                ) / branch_span
            if abs(spring.timing_balance) <= self._TIMING_TOLERANCE:
                judged += 1
            else:
                surging += 1
                # Record the timing imbalance entry.
                log_id = (
                    f"timing_{spring.spring_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "timing_id": log_id,
                    "spring_id": spring.spring_id,
                    "entity_id": spring.entity_id,
                    "timing_balance": spring.timing_balance,
                    "reservoir_pressure": spring.reservoir_pressure,
                    "kind": "surge",
                    "created_at": time.time(),
                }
                # Cap the timing log collection.
                if len(self._timing_logs) >= self._MAX_TIMING_LOGS:
                    oldest_key = next(iter(self._timing_logs))
                    self._timing_logs.pop(oldest_key, None)
                self._timing_logs[log_id] = log_entry
            spring.state = SpringState.JUDGED
        self._update_stats(
            phase_runs=1,
            springs_judged=judged,
            timing_surges=surging,
        )
        self._record_event("phase_judge_eruption_timing", {
            "judged": judged,
            "surging": surging,
        })
        return {
            "phase": "judge_eruption_timing",
            "judged": judged,
            "surging": surging,
        }

    def _phase_settle_discharge_order(self) -> Dict[str, Any]:
        """Settle phase: settle the discharge order of the jets against their timing."""
        ordered = 0
        capped = 0
        for spring in self._springs.values():
            if spring.state != SpringState.JUDGED:
                continue
            temp = spring.vent_temperature
            # Clamp the temperature to the safe envelope.
            if temp > spring.safe_pressure_ceiling * 15.0:
                spring.vent_temperature = spring.safe_pressure_ceiling * 15.0
                temp = spring.safe_pressure_ceiling * 15.0
            elif temp < spring.safe_pressure_floor:
                spring.vent_temperature = spring.safe_pressure_floor
                temp = spring.safe_pressure_floor
            # Re-classify after clamping.
            pressure_ratio = max(0.0, min(1.0, spring.reservoir_volume / 10.0))
            spring.timing_state = self._classify_timing_state(spring.reservoir_pressure, pressure_ratio)
            # Settle the discharge order based on the reservoir pressure and volume.
            if spring.reservoir_pressure > 0.0:
                if temp >= spring.safe_pressure_ceiling * 10.0:
                    spring.reservoir_pressure *= self._CAP_FACTOR
                    capped += 1
                elif pressure_ratio >= self._ERUPTION_THRESHOLD * 0.5:
                    spring.reservoir_pressure *= self._THROTTLE_FACTOR
                ordered += 1
                # Record the eruption timing log.
                log_id = (
                    f"erupt_{spring.spring_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "eruption_id": log_id,
                    "spring_id": spring.spring_id,
                    "entity_id": spring.entity_id,
                    "vent_temperature": temp,
                    "reservoir_pressure": spring.reservoir_pressure,
                    "timing_state": spring.timing_state.value,
                    "created_at": time.time(),
                }
                # Cap the eruption log collection.
                if len(self._eruption_logs) >= self._MAX_ERUPTION_LOGS:
                    oldest_key = next(iter(self._eruption_logs))
                    self._eruption_logs.pop(oldest_key, None)
                self._eruption_logs[log_id] = log_entry
            # Jet aperture tracks temperature within the envelope.
            spring.jet_aperture = temp * 0.001
            spring.state = SpringState.ORDERED
        self._update_stats(
            phase_runs=1,
            eruptions_predicted=ordered,
            spring_caps=capped,
        )
        self._record_event("phase_settle_discharge_order", {
            "ordered": ordered,
            "capped": capped,
        })
        return {
            "phase": "settle_discharge_order",
            "ordered": ordered,
            "capped": capped,
        }

    def _phase_emit_eruption_order_map(self) -> Dict[str, Any]:
        """Emit phase: emit the full eruption-order map with springs, temps, logs."""
        emitted = 0
        for spring in self._springs.values():
            if spring.state != SpringState.ORDERED:
                continue
            spring.state = SpringState.EMITTED
            emitted += 1
        # Stamp vitality based on the post-settlement state.
        for spring in self._springs.values():
            spring.vitality = self._derive_vitality(spring.spring_id)
        # Build the consolidated eruption-order map entry.
        map_id = (
            f"order_{int(time.time() * 1000)}_{random.randint(100, 999)}"
        )
        order_map = {
            "eruption_order_map_id": map_id,
            "cycle_count": self._cycle_count,
            "spring_count": len(self._springs),
            "timing_log_count": len(self._timing_logs),
            "eruption_log_count": len(self._eruption_logs),
            "springs": [self._spring_to_dict(s) for s in self._springs.values()],
            "timing_logs": list(self._timing_logs.values()),
            "eruption_logs": list(self._eruption_logs.values()),
            "created_at": time.time(),
        }
        # Cap the eruption-order map collection.
        if len(self._order_maps) >= self._MAX_ORDER_MAPS:
            oldest_key = next(iter(self._order_maps))
            self._order_maps.pop(oldest_key, None)
        self._order_maps[map_id] = order_map
        self._update_stats(phase_runs=1, order_maps_emitted=1)
        self._record_event("phase_emit_eruption_order_map", {
            "emitted": emitted,
            "eruption_order_map_id": map_id,
        })
        return {
            "phase": "emit_eruption_order_map",
            "emitted": emitted,
            "eruption_order_map_id": map_id,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_spring_by_id(self, spring_id: str) -> Optional[GeyserSpring]:
        """Find a spring by its spring_id (linear scan over entity_id keys)."""
        for spring in self._springs.values():
            if spring.spring_id == spring_id:
                return spring
        return None

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_springs(self) -> None:
        """Seed a few synthetic fulminant geyser springs on the first cycle if empty."""
        seeds = [
            ("spring::alpha", "Alpha Siliceous Geyser", 12.5, 380.0, 0, SpringKind.SILICEOUS, DischargeKind.SPURTING),
            ("spring::bravo", "Bravo Sulfuric Geyser", 18.0, 420.0, 1, SpringKind.SULFURIC, DischargeKind.FULMINANT),
            ("spring::charlie", "Charlie Bicarbonate Geyser", 6.0, 350.0, 2, SpringKind.BICARBONATE, DischargeKind.COLUMNAR),
        ]
        for entity_id, label, pressure, temp, branch, kind, discharge in seeds:
            if entity_id in self._springs:
                continue
            if len(self._springs) >= self._MAX_SPRINGS:
                break
            self.register_spring(
                entity_id=entity_id,
                spring_label=label,
                reservoir_pressure=pressure,
                vent_temperature=temp,
                jet_aperture=1.0,
                reservoir_volume=5.0,
                branch_index=branch,
                spring_kind=kind.value,
                discharge_kind=discharge.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _spring_to_dict(self, spring: GeyserSpring) -> Dict[str, Any]:
        return {
            "entity_id": spring.entity_id,
            "spring_id": spring.spring_id,
            "spring_label": spring.spring_label,
            "reservoir_pressure": spring.reservoir_pressure,
            "vent_temperature": spring.vent_temperature,
            "jet_aperture": spring.jet_aperture,
            "reservoir_volume": spring.reservoir_volume,
            "branch_index": spring.branch_index,
            "spring_kind": spring.spring_kind.value,
            "discharge_kind": spring.discharge_kind.value,
            "timing_state": spring.timing_state.value,
            "vitality": spring.vitality.value,
            "timing_balance": spring.timing_balance,
            "safe_pressure_floor": spring.safe_pressure_floor,
            "safe_pressure_ceiling": spring.safe_pressure_ceiling,
            "state": spring.state.value,
            "created_at": spring.created_at,
            "last_measured_at": spring.last_measured_at,
            "note": spring.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "springs": len(self._springs),
                "timing_logs": len(self._timing_logs),
                "eruption_logs": len(self._eruption_logs),
                "order_maps": len(self._order_maps),
                "stats": dict(self._stats),
            }

    def get_springs(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            springs = sorted(
                self._springs.values(),
                key=lambda s: s.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(springs),
                "springs": [
                    {
                        "spring_id": s.spring_id,
                        "entity_id": s.entity_id,
                        "spring_label": s.spring_label,
                        "reservoir_pressure": s.reservoir_pressure,
                        "spring_kind": s.spring_kind.value,
                        "timing_state": s.timing_state.value,
                        "vitality": s.vitality.value,
                        "branch_index": s.branch_index,
                    }
                    for s in springs
                ],
            }

    def get_spring(self, spring_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT spring_id, so we
        # MUST iterate over values and match on the spring_id attribute.
        with self._global_lock:
            for spring in self._springs.values():
                if spring.spring_id == spring_id:
                    return self._spring_to_dict(spring)
            return {
                "error": "spring not found",
                "spring_id": spring_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic springs if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._springs:
                self._seed_synthetic_springs()
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
            self._springs.clear()
            self._timing_logs.clear()
            self._eruption_logs.clear()
            self._order_maps.clear()
            self._phase = GeyserPhase.REGISTER_SPRING
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so cycles produce meaningful output.
            if not self._springs:
                self._seed_synthetic_springs()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Routing
    # -------------------------------------------------------------------------

    def build_eruption_order_map(self) -> Dict[str, Any]:
        """Build an eruption-order map: settle the discharge order and return the map.

        Computes the current eruption timing state distribution, the
        timing imbalance summary, and the eruption forecast without
        advancing the cycle counter.
        """
        with self._global_lock:
            springs = list(self._springs.values())
            if not springs:
                return {
                    "spring_count": 0,
                    "timing_state_distribution": {},
                    "eruption_forecast": 0.0,
                    "timing_surge_count": 0,
                    "eruption_order_map": "no springs registered",
                }
            state_counts: Dict[str, int] = {}
            total_forecast = 0.0
            surging = 0
            for spring in springs:
                pressure_ratio = max(0.0, min(1.0, spring.reservoir_volume / 10.0))
                state = self._classify_timing_state(spring.reservoir_pressure, pressure_ratio)
                state_counts[state.value] = state_counts.get(state.value, 0) + 1
                total_forecast += spring.reservoir_volume
                if abs(spring.timing_balance) > self._TIMING_TOLERANCE:
                    surging += 1
            return {
                "spring_count": len(springs),
                "timing_state_distribution": state_counts,
                "eruption_forecast": total_forecast,
                "timing_surge_count": surging,
                "cycle_count": self._cycle_count,
                "eruption_order_map": "settlement pass complete",
            }