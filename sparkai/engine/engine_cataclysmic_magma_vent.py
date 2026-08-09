"""
SparkLabs Engine - Cataclysmic Magma Vent"""

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

class VentPhase(Enum):
    """Phases of the cataclysmic magma vent cycle."""
    REGISTER_VENT = "register_vent"                          # register magma vents with their sensors and initial surge
    SAMPLE_SURGE_PRESSURE = "sample_surge_pressure"          # sample each vent's surge pressure for this cycle, update the regime
    TRACK_CHAMBER_PRESSURIZATION = "track_chamber_pressurization"  # track the magma chamber's pressurization, flag pressure surges
    PREDICT_ERUPTION = "predict_eruption"                    # predict the eruption intensity for each vent against the chamber volume
    EMIT_SURGE_PRESSURE_MAP = "emit_surge_pressure_map"      # emit the full surge pressure map with pressures, temperatures, and forecasts


class MagmaKind(Enum):
    """The kind of magma surging through a vent."""
    BASALTIC = "basaltic"        # low-viscosity basalt magma
    ANDESITIC = "andesitic"      # intermediate andesite magma
    DACITIC = "dacitic"          # viscous dacite magma
    RHYOLITIC = "rhyolitic"      # high-viscosity rhyolite magma


class SurgeKind(Enum):
    """The surge regime of a magma vent."""
    STEADY = "steady"            # steady molten rock surge
    RISING = "rising"            # surge pressure rising
    PULSING = "pulsing"          # periodic pulse pressure
    SURGING = "surging"          # violent surge pressure
    COLLAPSING = "collapsing"    # collapsing surge pressure


class VentPressureState(Enum):
    """The surge pressure phase state of a magma vent."""
    QUIESCENT = "quiescent"      # low pressure, dormant vent
    PRESSURIZING = "pressurizing"  # chamber building pressure
    STABLE = "stable"            # steady surge pressure
    UNSTABLE = "unstable"        # fluctuating surge pressure
    EMINENT = "eminent"          # imminent eruption threshold


class VentState(Enum):
    """State of an individual magma vent through the vent cycle."""
    PENDING = "pending"          # registered but not yet processed
    REGISTERED = "registered"    # confirmed and classified
    SAMPLED = "sampled"          # surge pressure sampled this cycle
    TRACKED = "tracked"          # chamber pressurization tracked
    PREDICTED = "predicted"      # eruption intensity predicted
    EMITTED = "emitted"          # emitted into the surge pressure map


class Vitality(Enum):
    """Overall vitality of the cataclysmic magma vent ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    DYNAMIC = "dynamic"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MagmaVent:
    """A cataclysmic magma vent monitored by the vent engine."""
    entity_id: str
    vent_id: str
    vent_label: str
    surge_pressure: float                          # MPa of molten rock surge pressure
    chamber_temperature: float                     # K at the magma chamber
    vent_aperture: float                           # m of vent opening diameter
    chamber_volume: float                          # km^3 of magma chamber volume
    branch_index: int                              # vent branch of the volcano network
    magma_kind: MagmaKind = MagmaKind.BASALTIC
    surge_kind: SurgeKind = SurgeKind.STEADY
    pressure_state: VentPressureState = VentPressureState.QUIESCENT
    vitality: Vitality = Vitality.DORMANT
    pressurization_balance: float = 0.0            # net pressurization imbalance, MPa
    safe_pressure_floor: float = 0.5               # minimum safe surge pressure, MPa
    safe_pressure_ceiling: float = 90.0            # maximum safe surge pressure, MPa
    state: VentState = VentState.PENDING
    created_at: float = field(default_factory=time.time)
    last_sampled_at: float = 0.0
    note: str = ""


# =============================================================================
# Cataclysmic Magma Vent
# =============================================================================

class CataclysmicMagmaVent:
    """
    Thread-safe singleton that monitors cataclysmic magma vents.

    Vents are keyed internally by entity_id so each logical vent owns
    exactly one entry. The vent_id is a generated handle for external lookups;
    lookups by vent_id fall back to a linear scan of the registered vents.

    Usage:
        vent = CataclysmicMagmaVent.get_instance()
        vent.register_vent(
            entity_id="vent::alpha",
            magma_label="Alpha Basalt Vent",
            surge_pressure=12.5,
        )
        vent.cycle()
        magma = vent.get_magma_chamber(vent_id)
        surge_map = vent.build_surge_pressure_map()
    """

    _instance: Optional["CataclysmicMagmaVent"] = None
    _instance_lock = threading.Lock()

    # Capacity caps.
    _MAX_MAGMA = 200
    _MAX_EVENTS = 200
    _MAX_PRESSURIZATION_LOGS = 200
    _MAX_ERUPTION_LOGS = 200
    _MAX_SURGE_MAPS = 120

    # Domain tuning constants.
    _SURGE_FLUCTUATION = 0.4              # base surge pressure fluctuation magnitude, MPa
    _PRESSURE_TOLERANCE = 0.03            # below this pressurization imbalance is balanced
    _SAFE_PRESSURE_FLOOR_DEFAULT = 0.5    # default minimum safe surge pressure, MPa
    _SAFE_PRESSURE_CEILING_DEFAULT = 90.0  # default maximum safe surge pressure, MPa
    _ERUPTION_THRESHOLD = 0.7             # pressure ratio above which the vent is erupting
    _SURGE_PRESSURE = 1.0                 # surge pressure above which the vent is surging
    _DEPLETED_PRESSURE = 0.1              # surge pressure below which the vent is depleted
    _THROTTLE_FACTOR = 0.7                # throttle factor for collecting surge
    _CAP_FACTOR = 0.3                     # cap factor for surging surge
    _MIN_SURGE_PRESSURE = 1e-4
    _MAX_SURGE_PRESSURE = 5.0

    def __init__(self) -> None:
        # Instance-level reentrant lock for thread-safe operation.
        self._global_lock = threading.RLock()
        # Internal dict keyed by entity_id (NOT vent_id).
        self._vents: Dict[str, MagmaVent] = {}
        self._pressurization_logs: Dict[str, Dict[str, Any]] = {}
        self._eruption_logs: Dict[str, Dict[str, Any]] = {}
        self._surge_maps: Dict[str, Dict[str, Any]] = {}
        self._phase: VentPhase = VentPhase.REGISTER_VENT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._vents:
            self._seed_synthetic_magma()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "CataclysmicMagmaVent":
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
            "vents_registered": 0,
            "phase_runs": 0,
            "surges_sampled": 0,
            "vents_tracked": 0,
            "pressure_surges": 0,
            "eruptions_predicted": 0,
            "vent_caps": 0,
            "surge_maps_emitted": 0,
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
    def _parse_magma_kind(value: Any) -> MagmaKind:
        """Parse a MagmaKind from a string, enum, or None."""
        if value is None:
            return MagmaKind.BASALTIC
        if isinstance(value, MagmaKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in MagmaKind:
                if kind.value == lowered:
                    return kind
        return MagmaKind.BASALTIC

    @staticmethod
    def _parse_surge_kind(value: Any) -> SurgeKind:
        """Parse a SurgeKind from a string, enum, or None."""
        if value is None:
            return SurgeKind.STEADY
        if isinstance(value, SurgeKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in SurgeKind:
                if kind.value == lowered:
                    return kind
        return SurgeKind.STEADY

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_pressure_state(self, surge_pressure: float, pressure_ratio: float) -> VentPressureState:
        """Classify the surge pressure state from surge pressure and pressure ratio."""
        if surge_pressure >= self._SURGE_PRESSURE and pressure_ratio >= self._ERUPTION_THRESHOLD:
            return VentPressureState.EMINENT
        if pressure_ratio >= self._ERUPTION_THRESHOLD:
            return VentPressureState.UNSTABLE
        if surge_pressure <= self._DEPLETED_PRESSURE:
            return VentPressureState.QUIESCENT
        if pressure_ratio >= self._ERUPTION_THRESHOLD * 0.5:
            return VentPressureState.PRESSURIZING
        return VentPressureState.STABLE

    def _derive_vitality(self, vent_id: str) -> Vitality:
        """Derive vitality for a magma vent from its post-prediction state."""
        vent = self._find_vent_by_id(vent_id)
        if vent is None:
            return Vitality.DORMANT
        surging = abs(vent.pressurization_balance) > self._PRESSURE_TOLERANCE * 5.0
        if vent.pressure_state == VentPressureState.EMINENT and surging:
            return Vitality.CHAOTIC
        if vent.pressure_state == VentPressureState.STABLE:
            return Vitality.FLOWING
        if vent.pressure_state == VentPressureState.PRESSURIZING:
            return Vitality.DYNAMIC
        if vent.state in (VentState.REGISTERED, VentState.SAMPLED):
            return Vitality.STIRRING
        return Vitality.DORMANT

    def _color_for_state(self, state: VentPressureState) -> str:
        """Map a surge pressure state to a preview color for the editor surge map."""
        if state == VentPressureState.QUIESCENT:
            return "#8B0000"  # dark red - quiescent vent
        if state == VentPressureState.STABLE:
            return "#FF4500"  # orange red - stable surge
        if state == VentPressureState.PRESSURIZING:
            return "#FF8C00"  # dark orange - pressurizing chamber
        if state == VentPressureState.UNSTABLE:
            return "#FFA500"  # orange - unstable surge
        return "#FF0000"      # red - eminent eruption

    # -------------------------------------------------------------------------
    # Vent Management
    # -------------------------------------------------------------------------

    def register_vent(
        self,
        entity_id: str,
        magma_label: str,
        surge_pressure: float = 8.0,
        chamber_temperature: float = 1200.0,
        vent_aperture: float = 1.0,
        chamber_volume: float = 5.0,
        branch_index: int = 0,
        magma_kind: Optional[str] = None,
        surge_kind: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new cataclysmic magma vent with the engine."""
        with self._global_lock:
            if entity_id in self._vents:
                return {"error": f"Vent already registered: {entity_id}"}
            if len(self._vents) >= self._MAX_MAGMA:
                return {"error": f"Vent cap reached ({self._MAX_MAGMA})"}

            vent_id = (
                f"vent_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            surge = max(
                self._MIN_SURGE_PRESSURE,
                min(self._MAX_SURGE_PRESSURE, float(surge_pressure)),
            )
            parsed_kind = self._parse_magma_kind(magma_kind)
            parsed_surge = self._parse_surge_kind(surge_kind)
            pressure_ratio = max(0.0, min(1.0, chamber_volume / 10.0))
            state = self._classify_pressure_state(surge, pressure_ratio)

            vent = MagmaVent(
                entity_id=entity_id,
                vent_id=vent_id,
                vent_label=magma_label,
                surge_pressure=surge,
                chamber_temperature=float(chamber_temperature),
                vent_aperture=float(vent_aperture),
                chamber_volume=float(chamber_volume),
                branch_index=int(branch_index),
                magma_kind=parsed_kind,
                surge_kind=parsed_surge,
                pressure_state=state,
                vitality=Vitality.DORMANT,
                pressurization_balance=0.0,
                safe_pressure_floor=self._SAFE_PRESSURE_FLOOR_DEFAULT,
                safe_pressure_ceiling=self._SAFE_PRESSURE_CEILING_DEFAULT,
                state=VentState.PENDING,
                created_at=time.time(),
                last_sampled_at=0.0,
                note=note,
            )
            self._vents[entity_id] = vent
            self._update_stats(vents_registered=1)
            self._record_event("vent_registered", {
                "vent_id": vent_id,
                "entity_id": entity_id,
                "magma_label": magma_label,
                "surge_pressure": vent.surge_pressure,
                "magma_kind": parsed_kind.value,
                "pressure_state": state.value,
            })

            return {
                "vent_id": vent_id,
                "entity_id": entity_id,
                "magma_label": magma_label,
                "surge_pressure": vent.surge_pressure,
                "magma_kind": parsed_kind.value,
                "pressure_state": state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single cataclysmic magma vent cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic magma on the very first cycle if none exist.
            if not self._vents and self._cycle_count == 0:
                self._seed_synthetic_magma()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = VentPhase.REGISTER_VENT
            phase_outputs.append(self._phase_register_vent())
            self._phase = VentPhase.SAMPLE_SURGE_PRESSURE
            phase_outputs.append(self._phase_sample_surge_pressure())
            self._phase = VentPhase.TRACK_CHAMBER_PRESSURIZATION
            phase_outputs.append(self._phase_track_chamber_pressurization())
            self._phase = VentPhase.PREDICT_ERUPTION
            phase_outputs.append(self._phase_predict_eruption())
            self._phase = VentPhase.EMIT_SURGE_PRESSURE_MAP
            phase_outputs.append(self._phase_emit_surge_pressure_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_vent(self) -> Dict[str, Any]:
        """Register phase: confirm pending magma vents and their sensors."""
        registered = 0
        surge_sum = 0.0
        for vent in self._vents.values():
            if vent.state == VentState.PENDING:
                vent.state = VentState.REGISTERED
                registered += 1
            # Refresh surge pressure state classification in case surge was set externally.
            pressure_ratio = max(0.0, min(1.0, vent.chamber_volume / 10.0))
            vent.pressure_state = self._classify_pressure_state(vent.surge_pressure, pressure_ratio)
            surge_sum += vent.surge_pressure
        avg_surge = (surge_sum / len(self._vents)) if self._vents else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_vent", {
            "registered": registered,
            "avg_surge": avg_surge,
        })
        return {
            "phase": "register_vent",
            "registered": registered,
            "avg_surge": avg_surge,
        }

    def _phase_sample_surge_pressure(self) -> Dict[str, Any]:
        """Sample phase: sample each vent's surge pressure for this cycle."""
        sampled = 0
        for vent in self._vents.values():
            if vent.state != VentState.REGISTERED:
                continue
            # Apply a small stochastic fluctuation to the surge pressure.
            fluctuation = random.uniform(
                -self._SURGE_FLUCTUATION, self._SURGE_FLUCTUATION,
            )
            vent.surge_pressure = max(0.0, vent.surge_pressure + fluctuation)
            # Temperature drifts slightly with surge, clamped to physical bounds.
            drift = fluctuation * 50.0
            vent.chamber_temperature = max(
                self._MIN_SURGE_PRESSURE,
                min(self._MAX_SURGE_PRESSURE * 800.0, vent.chamber_temperature + drift),
            )
            pressure_ratio = max(0.0, min(1.0, vent.chamber_volume / 10.0))
            vent.pressure_state = self._classify_pressure_state(vent.surge_pressure, pressure_ratio)
            vent.last_sampled_at = time.time()
            vent.state = VentState.SAMPLED
            sampled += 1
        self._update_stats(phase_runs=1, surges_sampled=sampled)
        self._record_event("phase_sample_surge_pressure", {"sampled": sampled})
        return {"phase": "sample_surge_pressure", "sampled": sampled}

    def _phase_track_chamber_pressurization(self) -> Dict[str, Any]:
        """Track phase: track the magma chamber's pressurization between vents."""
        tracked = 0
        surging = 0
        vents = list(self._vents.values())
        for i, vent in enumerate(vents):
            if vent.state != VentState.SAMPLED:
                continue
            # Compare this vent's surge against the average of the others.
            if len(vents) <= 1:
                vent.pressurization_balance = 0.0
            else:
                others = [v for j, v in enumerate(vents) if j != i]
                avg_other = sum(v.surge_pressure for v in others) / len(others)
                # Pressurization imbalance normalized by branch span.
                branch_span = max(vent.branch_index + 1, 1)
                vent.pressurization_balance = (
                    vent.surge_pressure - avg_other
                ) / branch_span
            if abs(vent.pressurization_balance) <= self._PRESSURE_TOLERANCE:
                tracked += 1
            else:
                surging += 1
                # Record the pressurization imbalance entry.
                log_id = (
                    f"press_{vent.vent_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "pressurization_id": log_id,
                    "vent_id": vent.vent_id,
                    "entity_id": vent.entity_id,
                    "pressurization_balance": vent.pressurization_balance,
                    "surge_pressure": vent.surge_pressure,
                    "kind": "surge",
                    "created_at": time.time(),
                }
                # Cap the pressurization log collection.
                if len(self._pressurization_logs) >= self._MAX_PRESSURIZATION_LOGS:
                    oldest_key = next(iter(self._pressurization_logs))
                    self._pressurization_logs.pop(oldest_key, None)
                self._pressurization_logs[log_id] = log_entry
            vent.state = VentState.TRACKED
        self._update_stats(
            phase_runs=1,
            vents_tracked=tracked,
            pressure_surges=surging,
        )
        self._record_event("phase_track_chamber_pressurization", {
            "tracked": tracked,
            "surging": surging,
        })
        return {
            "phase": "track_chamber_pressurization",
            "tracked": tracked,
            "surging": surging,
        }

    def _phase_predict_eruption(self) -> Dict[str, Any]:
        """Predict phase: predict the eruption intensity for each vent."""
        predicted = 0
        capped = 0
        for vent in self._vents.values():
            if vent.state != VentState.TRACKED:
                continue
            temp = vent.chamber_temperature
            # Clamp the temperature to the safe envelope.
            if temp > vent.safe_pressure_ceiling * 15.0:
                vent.chamber_temperature = vent.safe_pressure_ceiling * 15.0
                temp = vent.safe_pressure_ceiling * 15.0
            elif temp < vent.safe_pressure_floor:
                vent.chamber_temperature = vent.safe_pressure_floor
                temp = vent.safe_pressure_floor
            # Re-classify after clamping.
            pressure_ratio = max(0.0, min(1.0, vent.chamber_volume / 10.0))
            vent.pressure_state = self._classify_pressure_state(vent.surge_pressure, pressure_ratio)
            # Predict eruption intensity based on the surge pressure and chamber.
            if vent.surge_pressure > 0.0:
                if temp >= vent.safe_pressure_ceiling * 10.0:
                    vent.surge_pressure *= self._CAP_FACTOR
                    capped += 1
                elif pressure_ratio >= self._ERUPTION_THRESHOLD * 0.5:
                    vent.surge_pressure *= self._THROTTLE_FACTOR
                predicted += 1
                # Record the eruption intensity log.
                log_id = (
                    f"erupt_{vent.vent_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "eruption_id": log_id,
                    "vent_id": vent.vent_id,
                    "entity_id": vent.entity_id,
                    "chamber_temperature": temp,
                    "surge_pressure": vent.surge_pressure,
                    "pressure_state": vent.pressure_state.value,
                    "created_at": time.time(),
                }
                # Cap the eruption log collection.
                if len(self._eruption_logs) >= self._MAX_ERUPTION_LOGS:
                    oldest_key = next(iter(self._eruption_logs))
                    self._eruption_logs.pop(oldest_key, None)
                self._eruption_logs[log_id] = log_entry
            # Surge pressure tracks temperature within the envelope.
            vent.vent_aperture = temp * 0.001
            vent.state = VentState.PREDICTED
        self._update_stats(
            phase_runs=1,
            eruptions_predicted=predicted,
            vent_caps=capped,
        )
        self._record_event("phase_predict_eruption", {
            "predicted": predicted,
            "capped": capped,
        })
        return {
            "phase": "predict_eruption",
            "predicted": predicted,
            "capped": capped,
        }

    def _phase_emit_surge_pressure_map(self) -> Dict[str, Any]:
        """Emit phase: emit the full surge pressure map with vents, temps, logs."""
        emitted = 0
        for vent in self._vents.values():
            if vent.state != VentState.PREDICTED:
                continue
            vent.state = VentState.EMITTED
            emitted += 1
        # Stamp vitality based on the post-prediction state.
        for vent in self._vents.values():
            vent.vitality = self._derive_vitality(vent.vent_id)
        # Build the consolidated surge pressure map entry.
        map_id = (
            f"surge_{int(time.time() * 1000)}_{random.randint(100, 999)}"
        )
        surge_map = {
            "surge_pressure_map_id": map_id,
            "cycle_count": self._cycle_count,
            "vent_count": len(self._vents),
            "pressurization_log_count": len(self._pressurization_logs),
            "eruption_log_count": len(self._eruption_logs),
            "vents": [self._vent_to_dict(v) for v in self._vents.values()],
            "pressurization_logs": list(self._pressurization_logs.values()),
            "eruption_logs": list(self._eruption_logs.values()),
            "created_at": time.time(),
        }
        # Cap the surge pressure map collection.
        if len(self._surge_maps) >= self._MAX_SURGE_MAPS:
            oldest_key = next(iter(self._surge_maps))
            self._surge_maps.pop(oldest_key, None)
        self._surge_maps[map_id] = surge_map
        self._update_stats(phase_runs=1, surge_maps_emitted=1)
        self._record_event("phase_emit_surge_pressure_map", {
            "emitted": emitted,
            "surge_pressure_map_id": map_id,
        })
        return {
            "phase": "emit_surge_pressure_map",
            "emitted": emitted,
            "surge_pressure_map_id": map_id,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_vent_by_id(self, vent_id: str) -> Optional[MagmaVent]:
        """Find a vent by its vent_id (linear scan over entity_id keys)."""
        for vent in self._vents.values():
            if vent.vent_id == vent_id:
                return vent
        return None

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_magma(self) -> None:
        """Seed a few synthetic cataclysmic magma vents on the first cycle if empty."""
        seeds = [
            ("vent::alpha", "Alpha Basalt Vent", 12.5, 1300.0, 0, MagmaKind.BASALTIC, SurgeKind.STEADY),
            ("vent::bravo", "Bravo Andesite Vent", 18.0, 1500.0, 1, MagmaKind.ANDESITIC, SurgeKind.RISING),
            ("vent::charlie", "Charlie Rhyolite Vent", 6.0, 1600.0, 2, MagmaKind.RHYOLITIC, SurgeKind.PULSING),
        ]
        for entity_id, label, surge, temp, branch, kind, surge_kind in seeds:
            if entity_id in self._vents:
                continue
            if len(self._vents) >= self._MAX_MAGMA:
                break
            self.register_vent(
                entity_id=entity_id,
                magma_label=label,
                surge_pressure=surge,
                chamber_temperature=temp,
                vent_aperture=1.0,
                chamber_volume=5.0,
                branch_index=branch,
                magma_kind=kind.value,
                surge_kind=surge_kind.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _vent_to_dict(self, vent: MagmaVent) -> Dict[str, Any]:
        return {
            "entity_id": vent.entity_id,
            "vent_id": vent.vent_id,
            "vent_label": vent.vent_label,
            "surge_pressure": vent.surge_pressure,
            "chamber_temperature": vent.chamber_temperature,
            "vent_aperture": vent.vent_aperture,
            "chamber_volume": vent.chamber_volume,
            "branch_index": vent.branch_index,
            "magma_kind": vent.magma_kind.value,
            "surge_kind": vent.surge_kind.value,
            "pressure_state": vent.pressure_state.value,
            "vitality": vent.vitality.value,
            "pressurization_balance": vent.pressurization_balance,
            "safe_pressure_floor": vent.safe_pressure_floor,
            "safe_pressure_ceiling": vent.safe_pressure_ceiling,
            "state": vent.state.value,
            "created_at": vent.created_at,
            "last_sampled_at": vent.last_sampled_at,
            "note": vent.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "vents": len(self._vents),
                "pressurization_logs": len(self._pressurization_logs),
                "eruption_logs": len(self._eruption_logs),
                "surge_maps": len(self._surge_maps),
                "stats": dict(self._stats),
            }

    def get_magma(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            vents = sorted(
                self._vents.values(),
                key=lambda v: v.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(vents),
                "magma": [
                    {
                        "vent_id": v.vent_id,
                        "entity_id": v.entity_id,
                        "vent_label": v.vent_label,
                        "surge_pressure": v.surge_pressure,
                        "magma_kind": v.magma_kind.value,
                        "pressure_state": v.pressure_state.value,
                        "vitality": v.vitality.value,
                        "branch_index": v.branch_index,
                    }
                    for v in vents
                ],
            }

    def get_magma_chamber(self, magma_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT magma_id, so we
        # MUST iterate over values and match on the vent_id attribute.
        with self._global_lock:
            for vent in self._vents.values():
                if vent.vent_id == magma_id:
                    return self._vent_to_dict(vent)
            return {
                "error": "magma not found",
                "magma_id": magma_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic magma if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._vents:
                self._seed_synthetic_magma()
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
            self._vents.clear()
            self._pressurization_logs.clear()
            self._eruption_logs.clear()
            self._surge_maps.clear()
            self._phase = VentPhase.REGISTER_VENT
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so cycles produce meaningful output.
            if not self._vents:
                self._seed_synthetic_magma()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Routing
    # -------------------------------------------------------------------------

    def build_surge_pressure_map(self) -> Dict[str, Any]:
        """Build a surge pressure map: run a prediction pass and return the map.

        Computes the current surge pressure state distribution, the
        pressurization imbalance summary, and the eruption forecast without
        advancing the cycle counter.
        """
        with self._global_lock:
            vents = list(self._vents.values())
            if not vents:
                return {
                    "vent_count": 0,
                    "pressure_state_distribution": {},
                    "eruption_forecast": 0.0,
                    "pressure_surge_count": 0,
                    "surge_pressure_map": "no vents registered",
                }
            state_counts: Dict[str, int] = {}
            total_forecast = 0.0
            surging = 0
            for vent in vents:
                pressure_ratio = max(0.0, min(1.0, vent.chamber_volume / 10.0))
                state = self._classify_pressure_state(vent.surge_pressure, pressure_ratio)
                state_counts[state.value] = state_counts.get(state.value, 0) + 1
                total_forecast += vent.chamber_volume
                if abs(vent.pressurization_balance) > self._PRESSURE_TOLERANCE:
                    surging += 1
            return {
                "vent_count": len(vents),
                "pressure_state_distribution": state_counts,
                "eruption_forecast": total_forecast,
                "pressure_surge_count": surging,
                "cycle_count": self._cycle_count,
                "surge_pressure_map": "prediction pass complete",
            }