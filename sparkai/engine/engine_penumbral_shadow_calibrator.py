"""
SparkLabs Engine - Penumbral Shadow Calibrator"""

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

class ShadowPhase(Enum):
    """Phases of the penumbral shadow calibrator cycle."""
    REGISTER_SHADOW = "register_shadow"                    # register penumbral shadows with their gradient slopes and initial intensities
    SAMPLE_PENUMBRAL_INTENSITY = "sample_penumbral_intensity"  # sample each shadow's penumbral intensity for this cycle, update shadow regime
    BALANCE_SHADOW_GRADIENT = "balance_shadow_gradient"    # compute and balance gradient profiles between neighboring shadows
    CALIBRATE_BOUNDARY = "calibrate_boundary"              # throttle or cap calibration offsets to stay within the safe intensity envelope
    EMIT_SHADOW_GRADIENT_MAP = "emit_shadow_gradient_map"  # emit the full shadow gradient map with shadows, gradients, and calibration budgets


class ShadowKind(Enum):
    """The kind of penumbral shadow being calibrated."""
    TOTAL_PENUMBRA = "total_penumbra"      # total eclipse penumbral zone
    PARTIAL_PENUMBRA = "partial_penumbra"  # partial eclipse penumbral zone
    ANNULAR_PENUMBRA = "annular_penumbra"  # annular eclipse penumbral zone
    HYBRID_PENUMBRA = "hybrid_penumbra"    # hybrid eclipse penumbral zone


class ShadowRegime(Enum):
    """The intensity regime classification of a penumbral shadow."""
    DEPLETED = "depleted"          # intensity below safe floor
    DIM = "dim"                    # intensity below visible threshold
    VISIBLE = "visible"           # healthy visible penumbra
    OVERSATURATED = "oversaturated"  # intensity exceeds safe envelope


class CalibrationState(Enum):
    """The governance state of a shadow's calibration offset."""
    PASSIVE = "passive"            # no active calibration
    ADJUSTING = "adjusting"        # free-adjusting calibration offset
    THROTTLED = "throttled"        # calibration throttled to stay in envelope
    LOCKED = "locked"              # calibration locked to protect the regime


class ShadowState(Enum):
    """State of an individual shadow through the cycle."""
    PENDING = "pending"            # registered but not yet processed
    REGISTERED = "registered"      # confirmed and classified
    SAMPLED = "sampled"            # penumbral intensity sampled this cycle
    BALANCED = "balanced"          # gradient profile balanced
    CALIBRATED = "calibrated"      # calibration offset governed
    EMITTED = "emitted"            # emitted into the shadow gradient map


class Vitality(Enum):
    """Overall vitality of the penumbral shadow ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    DYNAMIC = "dynamic"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Shadow:
    """A penumbral shadow calibrated by the shadow calibrator."""
    entity_id: str
    shadow_id: str
    shadow_label: str
    penumbral_intensity: float                      # intensity above datum, 0-100
    gradient_slope: float                           # gradient steepness, per meter
    gradient_width: float                           # width of the gradient zone, meters
    umbral_distance: float                          # distance to umbral core, meters
    penumbral_pressure: float                       # Pa above ambient
    calibration_offset: float                       # adjustment applied per cycle
    shadow_kind: ShadowKind = ShadowKind.PARTIAL_PENUMBRA
    shadow_regime: ShadowRegime = ShadowRegime.DIM
    calibration_state: CalibrationState = CalibrationState.PASSIVE
    vitality: Vitality = Vitality.DORMANT
    gradient_balance: float = 0.0                   # net gradient imbalance, per meter
    safe_intensity_floor: float = 5.0               # minimum safe intensity
    safe_intensity_ceiling: float = 95.0            # maximum safe intensity
    state: ShadowState = ShadowState.PENDING
    created_at: float = field(default_factory=time.time)
    last_sampled_at: float = 0.0
    note: str = ""


# =============================================================================
# Calibrator
# =============================================================================

class PenumbralShadowCalibrator:
    """
    Thread-safe singleton that calibrates penumbral shadow boundaries.

    Shadows are keyed internally by entity_id so each logical shadow owns
    exactly one entry. The shadow_id is a generated handle for external
    lookups; lookups by shadow_id fall back to a linear scan of the
    registered shadows.

    Usage:
        calibrator = PenumbralShadowCalibrator.get_instance()
        calibrator.register_shadow(
            entity_id="shadow::alpha",
            shadow_label="Alpha Penumbral Cell",
            penumbral_intensity=42.5,
        )
        calibrator.cycle()
        shadow = calibrator.get_shadow(shadow_id)
        report = calibrator.build_shadow_gradient_map()
    """

    _instance: Optional["PenumbralShadowCalibrator"] = None
    _instance_lock = threading.Lock()

    # Capacity caps.
    _MAX_SHADOWS = 200
    _MAX_EVENTS = 200
    _MAX_GRADIENTS = 200
    _MAX_CALIBRATION_LOGS = 200
    _MAX_REPORTS = 120

    # Domain tuning constants.
    _INTENSITY_FLUCTUATION = 0.5            # base intensity fluctuation magnitude
    _GRADIENT_TOLERANCE = 0.02             # below this gradient is balanced
    _SAFE_INTENSITY_FLOOR_DEFAULT = 5.0    # default minimum safe intensity
    _SAFE_INTENSITY_CEILING_DEFAULT = 95.0  # default maximum safe intensity
    _VISIBLE_THRESHOLD_INTENSITY = 50.0    # intensity above which shadow is visible
    _OVERSATURATED_INTENSITY = 90.0        # intensity above which shadow is oversaturated
    _DEPLETED_INTENSITY = 10.0             # intensity below which shadow is depleted
    _CALIBRATION_THROTTLE_FACTOR = 0.7     # throttle factor for calibration offset
    _CALIBRATION_LOCK_FACTOR = 0.3         # lock factor for oversaturated calibration
    _MIN_GRADIENT_SLOPE = 1e-8
    _MAX_GRADIENT_SLOPE = 1e-2

    def __init__(self) -> None:
        # Instance-level reentrant lock for thread-safe operation.
        self._global_lock = threading.RLock()
        # Internal dict keyed by entity_id (NOT shadow_id).
        self._shadows: Dict[str, Shadow] = {}
        self._gradients: Dict[str, Dict[str, Any]] = {}
        self._calibration_logs: Dict[str, Dict[str, Any]] = {}
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._phase: ShadowPhase = ShadowPhase.REGISTER_SHADOW
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._shadows:
            self._seed_synthetic_shadows()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "PenumbralShadowCalibrator":
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
            "shadows_registered": 0,
            "phase_runs": 0,
            "intensities_sampled": 0,
            "gradients_balanced": 0,
            "overgradient_cells": 0,
            "calibrations_governed": 0,
            "calibrations_locked": 0,
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
    def _parse_shadow_kind(value: Any) -> ShadowKind:
        """Parse a ShadowKind from a string, enum, or None."""
        if value is None:
            return ShadowKind.PARTIAL_PENUMBRA
        if isinstance(value, ShadowKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in ShadowKind:
                if kind.value == lowered:
                    return kind
        return ShadowKind.PARTIAL_PENUMBRA

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_shadow_regime(self, intensity: float) -> ShadowRegime:
        """Classify the intensity regime from the penumbral intensity."""
        if intensity >= self._OVERSATURATED_INTENSITY:
            return ShadowRegime.OVERSATURATED
        if intensity <= self._DEPLETED_INTENSITY:
            return ShadowRegime.DEPLETED
        if intensity >= self._VISIBLE_THRESHOLD_INTENSITY:
            return ShadowRegime.VISIBLE
        return ShadowRegime.DIM

    def _classify_calibration_state(self, intensity: float, calibration_offset: float) -> CalibrationState:
        """Classify the calibration state from intensity and current calibration offset."""
        if calibration_offset <= 0.0:
            return CalibrationState.PASSIVE
        if intensity >= self._OVERSATURATED_INTENSITY:
            return CalibrationState.LOCKED
        if intensity >= self._VISIBLE_THRESHOLD_INTENSITY:
            return CalibrationState.THROTTLED
        return CalibrationState.ADJUSTING

    def _derive_vitality(self, shadow_id: str) -> Vitality:
        """Derive vitality for a shadow from its post-calibration state."""
        shadow = self._find_shadow_by_id(shadow_id)
        if shadow is None:
            return Vitality.DORMANT
        overgradient = abs(shadow.gradient_balance) > self._GRADIENT_TOLERANCE * 5.0
        if shadow.shadow_regime == ShadowRegime.OVERSATURATED and overgradient:
            return Vitality.CHAOTIC
        if shadow.calibration_state == CalibrationState.ADJUSTING:
            return Vitality.FLOWING
        if shadow.shadow_regime == ShadowRegime.VISIBLE:
            return Vitality.DYNAMIC
        if shadow.state in (ShadowState.REGISTERED, ShadowState.SAMPLED):
            return Vitality.STIRRING
        return Vitality.DORMANT

    def _color_for_regime(self, regime: ShadowRegime) -> str:
        """Map an intensity regime to a preview color for the editor heatmap."""
        if regime == ShadowRegime.DIM:
            return "#4169E1"  # royal blue - calm dim penumbra
        if regime == ShadowRegime.VISIBLE:
            return "#32CD32"  # lime green - healthy visible penumbra
        if regime == ShadowRegime.OVERSATURATED:
            return "#FF4500"  # orange-red - oversaturated danger
        return "#8B0000"      # dark red - depleted intensity

    # -------------------------------------------------------------------------
    # Shadow Management
    # -------------------------------------------------------------------------

    def register_shadow(
        self,
        entity_id: str,
        shadow_label: str,
        penumbral_intensity: float = 30.0,
        gradient_slope: float = 1e-5,
        gradient_width: float = 1e-4,
        umbral_distance: float = 10.0,
        penumbral_pressure: float = 0.0,
        calibration_offset: float = 0.0,
        shadow_kind: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new penumbral shadow with the calibrator."""
        with self._global_lock:
            if entity_id in self._shadows:
                return {"error": f"Shadow already registered: {entity_id}"}
            if len(self._shadows) >= self._MAX_SHADOWS:
                return {"error": f"Shadow cap reached ({self._MAX_SHADOWS})"}

            shadow_id = (
                f"shadow_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            slope = max(
                self._MIN_GRADIENT_SLOPE,
                min(self._MAX_GRADIENT_SLOPE, float(gradient_slope)),
            )
            parsed_kind = self._parse_shadow_kind(shadow_kind)
            intensity = float(penumbral_intensity)
            regime = self._classify_shadow_regime(intensity)
            offset = max(0.0, float(calibration_offset))
            calib_st = self._classify_calibration_state(intensity, offset)

            shadow = Shadow(
                entity_id=entity_id,
                shadow_id=shadow_id,
                shadow_label=shadow_label,
                penumbral_intensity=intensity,
                gradient_slope=slope,
                gradient_width=float(gradient_width),
                umbral_distance=float(umbral_distance),
                penumbral_pressure=float(penumbral_pressure),
                calibration_offset=offset,
                shadow_kind=parsed_kind,
                shadow_regime=regime,
                calibration_state=calib_st,
                vitality=Vitality.DORMANT,
                gradient_balance=0.0,
                safe_intensity_floor=self._SAFE_INTENSITY_FLOOR_DEFAULT,
                safe_intensity_ceiling=self._SAFE_INTENSITY_CEILING_DEFAULT,
                state=ShadowState.PENDING,
                created_at=time.time(),
                last_sampled_at=0.0,
                note=note,
            )
            self._shadows[entity_id] = shadow
            self._update_stats(shadows_registered=1)
            self._record_event("shadow_registered", {
                "shadow_id": shadow_id,
                "entity_id": entity_id,
                "shadow_label": shadow_label,
                "penumbral_intensity": intensity,
                "shadow_kind": parsed_kind.value,
                "shadow_regime": regime.value,
            })

            return {
                "shadow_id": shadow_id,
                "entity_id": entity_id,
                "shadow_label": shadow_label,
                "penumbral_intensity": intensity,
                "shadow_kind": parsed_kind.value,
                "shadow_regime": regime.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single penumbral shadow calibrator cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic shadows on the very first cycle if none exist.
            if not self._shadows and self._cycle_count == 0:
                self._seed_synthetic_shadows()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = ShadowPhase.REGISTER_SHADOW
            phase_outputs.append(self._phase_register_shadow())
            self._phase = ShadowPhase.SAMPLE_PENUMBRAL_INTENSITY
            phase_outputs.append(self._phase_sample_penumbral_intensity())
            self._phase = ShadowPhase.BALANCE_SHADOW_GRADIENT
            phase_outputs.append(self._phase_balance_shadow_gradient())
            self._phase = ShadowPhase.CALIBRATE_BOUNDARY
            phase_outputs.append(self._phase_calibrate_boundary())
            self._phase = ShadowPhase.EMIT_SHADOW_GRADIENT_MAP
            phase_outputs.append(self._phase_emit_shadow_gradient_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_shadow(self) -> Dict[str, Any]:
        """Register phase: confirm pending shadows and their gradient slopes."""
        registered = 0
        intensity_sum = 0.0
        for shadow in self._shadows.values():
            if shadow.state == ShadowState.PENDING:
                shadow.state = ShadowState.REGISTERED
                registered += 1
            # Refresh intensity regime classification in case intensity was set externally.
            shadow.shadow_regime = self._classify_shadow_regime(shadow.penumbral_intensity)
            intensity_sum += shadow.penumbral_intensity
        avg_intensity = (intensity_sum / len(self._shadows)) if self._shadows else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_shadow", {
            "registered": registered,
            "avg_intensity": avg_intensity,
        })
        return {
            "phase": "register_shadow",
            "registered": registered,
            "avg_intensity": avg_intensity,
        }

    def _phase_sample_penumbral_intensity(self) -> Dict[str, Any]:
        """Sample phase: sample each shadow's penumbral intensity for this cycle."""
        sampled = 0
        for shadow in self._shadows.values():
            if shadow.state != ShadowState.REGISTERED:
                continue
            # Apply a small stochastic fluctuation to the intensity.
            fluctuation = random.uniform(
                -self._INTENSITY_FLUCTUATION, self._INTENSITY_FLUCTUATION,
            )
            shadow.penumbral_intensity = max(
                0.0, shadow.penumbral_intensity + fluctuation,
            )
            shadow.shadow_regime = self._classify_shadow_regime(shadow.penumbral_intensity)
            shadow.last_sampled_at = time.time()
            shadow.state = ShadowState.SAMPLED
            sampled += 1
        self._update_stats(phase_runs=1, intensities_sampled=sampled)
        self._record_event("phase_sample_penumbral_intensity", {"sampled": sampled})
        return {"phase": "sample_penumbral_intensity", "sampled": sampled}

    def _phase_balance_shadow_gradient(self) -> Dict[str, Any]:
        """Balance phase: compute and balance gradient profiles between shadows."""
        balanced = 0
        overgradient = 0
        shadows = list(self._shadows.values())
        for i, shadow in enumerate(shadows):
            if shadow.state != ShadowState.SAMPLED:
                continue
            # Compare this shadow's intensity against the average of the others.
            if len(shadows) <= 1:
                shadow.gradient_balance = 0.0
            else:
                others = [s for j, s in enumerate(shadows) if j != i]
                avg_other = sum(s.penumbral_intensity for s in others) / len(others)
                # Gradient normalized by an assumed inter-shadow distance.
                distance = max(shadow.umbral_distance, 1.0)
                shadow.gradient_balance = (
                    shadow.penumbral_intensity - avg_other
                ) / distance
            if abs(shadow.gradient_balance) <= self._GRADIENT_TOLERANCE:
                balanced += 1
            else:
                overgradient += 1
                # Record the gradient imbalance entry.
                grad_id = (
                    f"grad_{shadow.shadow_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                grad_entry = {
                    "gradient_id": grad_id,
                    "shadow_id": shadow.shadow_id,
                    "entity_id": shadow.entity_id,
                    "gradient_balance": shadow.gradient_balance,
                    "intensity": shadow.penumbral_intensity,
                    "kind": "overgradient",
                    "created_at": time.time(),
                }
                # Cap the gradient collection.
                if len(self._gradients) >= self._MAX_GRADIENTS:
                    oldest_key = next(iter(self._gradients))
                    self._gradients.pop(oldest_key, None)
                self._gradients[grad_id] = grad_entry
            shadow.state = ShadowState.BALANCED
        self._update_stats(
            phase_runs=1,
            gradients_balanced=balanced,
            overgradient_cells=overgradient,
        )
        self._record_event("phase_balance_shadow_gradient", {
            "balanced": balanced,
            "overgradient": overgradient,
        })
        return {
            "phase": "balance_shadow_gradient",
            "balanced": balanced,
            "overgradient": overgradient,
        }

    def _phase_calibrate_boundary(self) -> Dict[str, Any]:
        """Calibrate phase: throttle or lock calibration offsets within the safe envelope."""
        governed = 0
        locked = 0
        for shadow in self._shadows.values():
            if shadow.state != ShadowState.BALANCED:
                continue
            intensity = shadow.penumbral_intensity
            # Clamp the intensity to the safe envelope.
            if intensity > shadow.safe_intensity_ceiling:
                shadow.penumbral_intensity = shadow.safe_intensity_ceiling
                intensity = shadow.safe_intensity_ceiling
            elif intensity < shadow.safe_intensity_floor:
                shadow.penumbral_intensity = shadow.safe_intensity_floor
                intensity = shadow.safe_intensity_floor
            # Re-classify after clamping.
            shadow.shadow_regime = self._classify_shadow_regime(intensity)
            # Govern calibration offset based on the clamped intensity.
            if shadow.calibration_offset > 0.0:
                if intensity >= self._OVERSATURATED_INTENSITY:
                    shadow.calibration_offset *= self._CALIBRATION_LOCK_FACTOR
                    shadow.calibration_state = CalibrationState.LOCKED
                    locked += 1
                elif intensity >= self._VISIBLE_THRESHOLD_INTENSITY:
                    shadow.calibration_offset *= self._CALIBRATION_THROTTLE_FACTOR
                    shadow.calibration_state = CalibrationState.THROTTLED
                else:
                    shadow.calibration_state = CalibrationState.ADJUSTING
                governed += 1
                # Record the calibration governance log.
                log_id = (
                    f"cal_{shadow.shadow_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "log_id": log_id,
                    "shadow_id": shadow.shadow_id,
                    "entity_id": shadow.entity_id,
                    "intensity": intensity,
                    "calibration_offset": shadow.calibration_offset,
                    "calibration_state": shadow.calibration_state.value,
                    "created_at": time.time(),
                }
                # Cap the calibration log collection.
                if len(self._calibration_logs) >= self._MAX_CALIBRATION_LOGS:
                    oldest_key = next(iter(self._calibration_logs))
                    self._calibration_logs.pop(oldest_key, None)
                self._calibration_logs[log_id] = log_entry
            else:
                shadow.calibration_state = CalibrationState.PASSIVE
            shadow.state = ShadowState.CALIBRATED
        self._update_stats(
            phase_runs=1,
            calibrations_governed=governed,
            calibrations_locked=locked,
        )
        self._record_event("phase_calibrate_boundary", {
            "governed": governed,
            "locked": locked,
        })
        return {
            "phase": "calibrate_boundary",
            "governed": governed,
            "locked": locked,
        }

    def _phase_emit_shadow_gradient_map(self) -> Dict[str, Any]:
        """Emit phase: emit the full shadow gradient map with shadows, gradients, logs."""
        emitted = 0
        for shadow in self._shadows.values():
            if shadow.state != ShadowState.CALIBRATED:
                continue
            shadow.state = ShadowState.EMITTED
            emitted += 1
        # Stamp vitality based on the post-calibration state.
        for shadow in self._shadows.values():
            shadow.vitality = self._derive_vitality(shadow.shadow_id)
        # Build the consolidated report entry.
        report_id = (
            f"report_{int(time.time() * 1000)}_{random.randint(100, 999)}"
        )
        report = {
            "report_id": report_id,
            "cycle_count": self._cycle_count,
            "shadow_count": len(self._shadows),
            "gradient_count": len(self._gradients),
            "calibration_log_count": len(self._calibration_logs),
            "shadows": [self._shadow_to_dict(s) for s in self._shadows.values()],
            "gradients": list(self._gradients.values()),
            "calibration_logs": list(self._calibration_logs.values()),
            "created_at": time.time(),
        }
        # Cap the report collection.
        if len(self._reports) >= self._MAX_REPORTS:
            oldest_key = next(iter(self._reports))
            self._reports.pop(oldest_key, None)
        self._reports[report_id] = report
        self._update_stats(phase_runs=1, reports_emitted=1)
        self._record_event("phase_emit_shadow_gradient_map", {
            "emitted": emitted,
            "report_id": report_id,
        })
        return {
            "phase": "emit_shadow_gradient_map",
            "emitted": emitted,
            "report_id": report_id,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_shadow_by_id(self, shadow_id: str) -> Optional[Shadow]:
        """Find a shadow by its shadow_id (linear scan over entity_id keys)."""
        for shadow in self._shadows.values():
            if shadow.shadow_id == shadow_id:
                return shadow
        return None

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_shadows(self) -> None:
        """Seed a few synthetic penumbral shadows on the first cycle if empty."""
        seeds = [
            ("shadow::alpha", "Alpha Penumbral Cell", 42.5, 1e-5, ShadowKind.PARTIAL_PENUMBRA, 0.02),
            ("shadow::bravo", "Bravo Visible Cell", 65.0, 5e-5, ShadowKind.TOTAL_PENUMBRA, 0.05),
            ("shadow::charlie", "Charlie Dim Cell", 28.0, 2e-6, ShadowKind.ANNULAR_PENUMBRA, 0.0),
        ]
        for entity_id, label, intensity, slope, kind, offset in seeds:
            if entity_id in self._shadows:
                continue
            if len(self._shadows) >= self._MAX_SHADOWS:
                break
            self.register_shadow(
                entity_id=entity_id,
                shadow_label=label,
                penumbral_intensity=intensity,
                gradient_slope=slope,
                gradient_width=1e-4,
                umbral_distance=10.0,
                penumbral_pressure=0.0,
                calibration_offset=offset,
                shadow_kind=kind.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _shadow_to_dict(self, shadow: Shadow) -> Dict[str, Any]:
        return {
            "entity_id": shadow.entity_id,
            "shadow_id": shadow.shadow_id,
            "shadow_label": shadow.shadow_label,
            "penumbral_intensity": shadow.penumbral_intensity,
            "gradient_slope": shadow.gradient_slope,
            "gradient_width": shadow.gradient_width,
            "umbral_distance": shadow.umbral_distance,
            "penumbral_pressure": shadow.penumbral_pressure,
            "calibration_offset": shadow.calibration_offset,
            "shadow_kind": shadow.shadow_kind.value,
            "shadow_regime": shadow.shadow_regime.value,
            "calibration_state": shadow.calibration_state.value,
            "vitality": shadow.vitality.value,
            "gradient_balance": shadow.gradient_balance,
            "safe_intensity_floor": shadow.safe_intensity_floor,
            "safe_intensity_ceiling": shadow.safe_intensity_ceiling,
            "state": shadow.state.value,
            "created_at": shadow.created_at,
            "last_sampled_at": shadow.last_sampled_at,
            "note": shadow.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "shadows": len(self._shadows),
                "gradients": len(self._gradients),
                "calibration_logs": len(self._calibration_logs),
                "reports": len(self._reports),
                "stats": dict(self._stats),
            }

    def get_shadows(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            shadows = sorted(
                self._shadows.values(),
                key=lambda s: s.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(shadows),
                "shadows": [
                    {
                        "shadow_id": s.shadow_id,
                        "entity_id": s.entity_id,
                        "shadow_label": s.shadow_label,
                        "penumbral_intensity": s.penumbral_intensity,
                        "shadow_kind": s.shadow_kind.value,
                        "shadow_regime": s.shadow_regime.value,
                        "calibration_state": s.calibration_state.value,
                        "vitality": s.vitality.value,
                    }
                    for s in shadows
                ],
            }

    def get_shadow(self, shadow_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT shadow_id, so we
        # MUST iterate over values and match on the shadow_id attribute.
        with self._global_lock:
            for shadow in self._shadows.values():
                if shadow.shadow_id == shadow_id:
                    return self._shadow_to_dict(shadow)
            return {
                "error": "shadow not found",
                "shadow_id": shadow_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic shadows if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._shadows:
                self._seed_synthetic_shadows()
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
            self._shadows.clear()
            self._gradients.clear()
            self._calibration_logs.clear()
            self._reports.clear()
            self._phase = ShadowPhase.REGISTER_SHADOW
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so cycles produce meaningful output.
            if not self._shadows:
                self._seed_synthetic_shadows()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Calibration
    # -------------------------------------------------------------------------

    def build_shadow_gradient_map(self) -> Dict[str, Any]:
        """Build a shadow gradient map: run a calibration pass and return a report.

        Computes the current intensity regime distribution, the gradient
        imbalance summary, and the calibration budget without advancing the
        cycle counter.
        """
        with self._global_lock:
            shadows = list(self._shadows.values())
            if not shadows:
                return {
                    "calibrated": 0,
                    "regime_distribution": {},
                    "calibration_budget": 0.0,
                    "overgradient_count": 0,
                    "report": "no shadows registered",
                }
            regime_counts: Dict[str, int] = {}
            total_offset = 0.0
            overgradient = 0
            for shadow in shadows:
                regime = self._classify_shadow_regime(shadow.penumbral_intensity)
                regime_counts[regime.value] = regime_counts.get(regime.value, 0) + 1
                total_offset += shadow.calibration_offset
                if abs(shadow.gradient_balance) > self._GRADIENT_TOLERANCE:
                    overgradient += 1
            return {
                "calibrated": len(shadows),
                "regime_distribution": regime_counts,
                "calibration_budget": total_offset,
                "overgradient_count": overgradient,
                "cycle_count": self._cycle_count,
                "report": "shadow gradient map complete",
            }
