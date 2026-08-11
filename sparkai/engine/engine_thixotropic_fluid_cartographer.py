"""
SparkLabs Engine - Thixotropic Fluid Cartographer"""

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

class CartographerPhase(Enum):
    """Phases of the thixotropic fluid cartographer cycle."""
    SAMPLE_FLUID = "sample_fluid"                                  # sample registered fluids and confirm their rheological state
    MAP_SHEAR_YIELD = "map_shear_yield"                            # chart shear-yield contours where the gel yields under stress
    CHART_VISCOSITY_RELAXATION = "chart_viscosity_relaxation"      # chart viscosity relaxation curves tracing rebuild at rest
    CARTOGRAPH_GEL_SOL_TRANSITION = "cartograph_gel_sol_transition"  # map gel-sol transition zones across the sample field
    EMIT_CONTOUR_MAP = "emit_contour_map"                          # emit the full cartography report with contours, curves, zones


class FluidClass(Enum):
    """Rheological classification of a thixotropic fluid sample."""
    PSEUDOPLASTIC = "pseudoplastic"        # shear-thinning without a true yield stress
    BINGHAM = "bingham"                    # linear flow above a yield stress
    CASSON = "casson"                      # square-root flow law above yield
    HERSCHEL_BULKLEY = "herschel_bulkley"  # generalized yield-stress fluid


class RheologicalState(Enum):
    """Rheological state of a fluid sample through the cycle."""
    GEL = "gel"            # resting gel structure
    YIELDING = "yielding"  # stress exceeds yield, structure breaking down
    FLOWING = "flowing"    # fully flowing under shear
    RELAXING = "relaxing"  # rebuilding structure after shear removal
    SET = "set"            # structure fully rebuilt


class ThixotropyTier(Enum):
    """Intensity of the thixotropic character of a fluid sample."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class FluidState(Enum):
    """Per-fluid lifecycle state within a cartographer cycle."""
    PENDING = "pending"
    SAMPLED = "sampled"
    MAPPED = "mapped"
    CHARTED = "charted"
    CARTOGRAPHED = "cartographed"
    EMITTED = "emitted"


class FluidVitality(Enum):
    """Overall vitality of the thixotropic fluid ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    DYNAMIC = "dynamic"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FluidSample:
    """A thixotropic fluid sample registered with the cartographer."""
    fluid_id: str
    entity_id: str
    fluid_label: str
    yield_stress: float                            # stress threshold above which the gel yields
    resting_viscosity: float                       # viscosity at rest (gel state)
    apparent_viscosity: float                      # current apparent viscosity under shear
    shear_rate: float                              # current applied shear rate
    thixotropy_area: float                         # hysteresis loop area (stress-thinning energy)
    fluid_class: FluidClass = FluidClass.HERSCHEL_BULKLEY
    rheological_state: RheologicalState = RheologicalState.GEL
    thixotropy_tier: ThixotropyTier = ThixotropyTier.MODERATE
    state: FluidState = FluidState.PENDING
    vitality: FluidVitality = FluidVitality.DORMANT
    created_at: float = field(default_factory=time.time)
    last_sheared_at: float = 0.0
    note: str = ""


# =============================================================================
# Cartographer
# =============================================================================

class ThixotropicFluidCartographer:
    """
    Thread-safe singleton that maps thixotropic fluid behaviors as shear-yield
    contours, viscosity-relaxation curves, and gel-sol transition zones.

    Fluids are keyed internally by entity_id so that each logical sample owns
    exactly one entry. The fluid_id is a generated handle for external
    lookups; lookups by fluid_id fall back to a linear scan of the registered
    fluid samples.

    Usage:
        cartographer = ThixotropicFluidCartographer.get_instance()
        cartographer.register_fluid(
            entity_id="fluid::drilling_mud",
            fluid_label="Drilling Mud",
            yield_stress=12.5,
        )
        cartographer.cycle()
        fluid = cartographer.get_fluid(fluid_id)
        report = cartographer.cartograph_fluids()
    """

    _instance: Optional["ThixotropicFluidCartographer"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Capacity caps.
    _MAX_FLUIDS = 100
    _MAX_EVENTS = 200
    _MAX_CONTOURS = 200
    _MAX_CURVES = 150
    _MAX_TRANSITIONS = 100
    _MAX_REPORTS = 120

    # Domain tuning constants.
    _TWO_PI = 2.0 * math.pi
    _MIN_YIELD_STRESS = 0.1
    _MAX_YIELD_STRESS = 100.0
    _VISCOSITY_FLOOR = 0.001                       # never let viscosity reach zero
    _SHEAR_RATE_BASE = 1.0                         # baseline shear rate
    _YIELD_RADIUS_BASE = 1.0                       # baseline radial reach of the yield contour
    _RELAXATION_HALFLIFE_BASE = 2.0                # baseline viscosity rebuild half-life (cycles)
    _TRANSITION_SHARPNESS_BASE = 1.0               # baseline gel-sol boundary sharpness
    _THIXOTROPY_AREA_SCALE = 10.0                  # scale for hysteresis loop area
    _CANONICAL_YIELD_RADIUS = 1.5                  # contours inside this mark tight yield
    _MODERATE_YIELD_RADIUS = 4.0                   # contours inside this mark moderate yield
    _WIDE_YIELD_RADIUS = 7.0                       # contours inside this mark wide yield
    _RELAXATION_FULL_FRACTION = 0.95               # fraction considered fully rebuilt
    _GEL_SOL_VISCOSITY_RATIO = 3.0                 # gel side is at least this much thicker than sol

    def __init__(self) -> None:
        # Internal dict keyed by entity_id (NOT fluid_id).
        self._fluids: Dict[str, FluidSample] = {}
        self._contours: Dict[str, Dict[str, Any]] = {}
        self._curves: Dict[str, Dict[str, Any]] = {}
        self._transitions: Dict[str, Dict[str, Any]] = {}
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._phase: CartographerPhase = CartographerPhase.SAMPLE_FLUID
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._fluids:
            self._seed_synthetic_fluids()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ThixotropicFluidCartographer":
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
            "fluids_registered": 0,
            "phase_runs": 0,
            "contours_mapped": 0,
            "curves_charts": 0,
            "transitions_cartographed": 0,
            "contour_maps_emitted": 0,
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
    def _parse_fluid_class(value: Any) -> FluidClass:
        """Parse a FluidClass from a string, enum, or None."""
        if value is None:
            return FluidClass.HERSCHEL_BULKLEY
        if isinstance(value, FluidClass):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for cls in FluidClass:
                if cls.value == lowered:
                    return cls
        return FluidClass.HERSCHEL_BULKLEY

    @staticmethod
    def _parse_thixotropy_tier(value: Any) -> ThixotropyTier:
        """Parse a ThixotropyTier from a string, enum, or None."""
        if value is None:
            return ThixotropyTier.MODERATE
        if isinstance(value, ThixotropyTier):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for tier in ThixotropyTier:
                if tier.value == lowered:
                    return tier
        return ThixotropyTier.MODERATE

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_thixotropy_tier(self, thixotropy_area: float) -> ThixotropyTier:
        """Classify the thixotropy tier from the hysteresis loop area."""
        if thixotropy_area < 2.0:
            return ThixotropyTier.LOW
        if thixotropy_area < 6.0:
            return ThixotropyTier.MODERATE
        if thixotropy_area < 12.0:
            return ThixotropyTier.HIGH
        return ThixotropyTier.EXTREME

    def _classify_rheological_state(
        self, shear_rate: float, yield_stress: float, apparent_viscosity: float,
        resting_viscosity: float,
    ) -> RheologicalState:
        """Classify the rheological state from the current shear and viscosity."""
        # Effective stress from the applied shear.
        effective_stress = shear_rate * max(apparent_viscosity, self._VISCOSITY_FLOOR)
        if effective_stress >= yield_stress * 1.2:
            return RheologicalState.FLOWING
        if effective_stress >= yield_stress:
            return RheologicalState.YIELDING
        # Below yield, decide between relaxing and set/gel by comparing to rest.
        if apparent_viscosity >= resting_viscosity * self._RELAXATION_FULL_FRACTION:
            return RheologicalState.SET
        return RheologicalState.RELAXING

    def _compute_yield_radius(self, yield_stress: float, shear_rate: float) -> float:
        """Compute the radial reach of the yield contour for a fluid.

        Higher yield stress and lower shear rate push the yield contour wider.
        """
        ys = max(yield_stress, self._MIN_YIELD_STRESS)
        sr = max(shear_rate, 0.01)
        radius = self._YIELD_RADIUS_BASE * math.sqrt(ys / sr)
        # Keep within a sensible bound.
        return max(0.1, min(radius, self._WIDE_YIELD_RADIUS * 1.5))

    def _compute_relaxation_half_life(self, thixotropy_area: float) -> float:
        """Compute the viscosity rebuild half-life from the thixotropy area."""
        # Stronger thixotropy rebuilds more slowly.
        return self._RELAXATION_HALFLIFE_BASE * (1.0 + math.log1p(max(thixotropy_area, 0.0)))

    def _color_for_tier(self, tier: ThixotropyTier) -> str:
        """Map a thixotropy tier to a preview color for the editor contour."""
        if tier == ThixotropyTier.LOW:
            return "#4682B4"      # steel blue - mild thinning
        if tier == ThixotropyTier.MODERATE:
            return "#FFD700"      # gold - moderate thinning
        if tier == ThixotropyTier.HIGH:
            return "#FF4500"      # orange-red - strong thinning
        return "#8B0000"          # dark red - extreme thinning

    # -------------------------------------------------------------------------
    # Fluid Management
    # -------------------------------------------------------------------------

    def register_fluid(
        self,
        entity_id: str,
        fluid_label: str,
        yield_stress: float = 10.0,
        resting_viscosity: float = 1.0,
        apparent_viscosity: float = 0.5,
        shear_rate: float = 1.0,
        thixotropy_area: float = 5.0,
        fluid_class: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new thixotropic fluid sample with its yield-stress profile."""
        with self._global_lock:
            if entity_id in self._fluids:
                return {"error": f"Fluid already registered: {entity_id}"}
            if len(self._fluids) >= self._MAX_FLUIDS:
                return {"error": f"Fluid cap reached ({self._MAX_FLUIDS})"}

            fluid_id = f"fluid_{entity_id}_{int(time.time() * 1000)}_{random.randint(100, 999)}"

            ys = max(
                self._MIN_YIELD_STRESS,
                min(self._MAX_YIELD_STRESS, float(yield_stress)),
            )
            resting = max(self._VISCOSITY_FLOOR, float(resting_viscosity))
            apparent = max(self._VISCOSITY_FLOOR, float(apparent_viscosity))
            sr = max(0.0, float(shear_rate))
            area = max(0.0, float(thixotropy_area))
            parsed_class = self._parse_fluid_class(fluid_class)
            parsed_tier = self._classify_thixotropy_tier(area)

            fluid = FluidSample(
                fluid_id=fluid_id,
                entity_id=entity_id,
                fluid_label=fluid_label,
                yield_stress=ys,
                resting_viscosity=resting,
                apparent_viscosity=apparent,
                shear_rate=sr,
                thixotropy_area=area,
                fluid_class=parsed_class,
                rheological_state=RheologicalState.GEL,
                thixotropy_tier=parsed_tier,
                state=FluidState.PENDING,
                vitality=FluidVitality.DORMANT,
                created_at=time.time(),
                last_sheared_at=0.0,
                note=note,
            )
            self._fluids[entity_id] = fluid
            self._update_stats(fluids_registered=1)
            self._record_event("fluid_registered", {
                "fluid_id": fluid_id,
                "entity_id": entity_id,
                "fluid_label": fluid_label,
                "yield_stress": ys,
                "fluid_class": parsed_class.value,
                "thixotropy_tier": parsed_tier.value,
            })

            return {
                "fluid_id": fluid_id,
                "entity_id": entity_id,
                "fluid_label": fluid_label,
                "yield_stress": ys,
                "resting_viscosity": resting,
                "apparent_viscosity": apparent,
                "shear_rate": sr,
                "thixotropy_area": area,
                "fluid_class": parsed_class.value,
                "thixotropy_tier": parsed_tier.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single thixotropic fluid cartographer cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic fluids on the very first cycle if none exist.
            if not self._fluids and self._cycle_count == 0:
                self._seed_synthetic_fluids()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = CartographerPhase.SAMPLE_FLUID
            phase_outputs.append(self._phase_sample_fluid())
            self._phase = CartographerPhase.MAP_SHEAR_YIELD
            phase_outputs.append(self._phase_map_shear_yield())
            self._phase = CartographerPhase.CHART_VISCOSITY_RELAXATION
            phase_outputs.append(self._phase_chart_viscosity_relaxation())
            self._phase = CartographerPhase.CARTOGRAPH_GEL_SOL_TRANSITION
            phase_outputs.append(self._phase_cartograph_gel_sol_transition())
            self._phase = CartographerPhase.EMIT_CONTOUR_MAP
            phase_outputs.append(self._phase_emit_contour_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_sample_fluid(self) -> Dict[str, Any]:
        """Sample phase: confirm pending fluid samples and their rheological state."""
        sampled_fluids = 0
        yield_sum = 0.0
        for fluid in self._fluids.values():
            # Recompute thixotropy tier in case the area was adjusted.
            fluid.thixotropy_tier = self._classify_thixotropy_tier(fluid.thixotropy_area)
            # Perturb the apparent viscosity slightly so the state evolves cycle to cycle.
            viscosity_delta = random.uniform(-0.05, 0.05) * fluid.resting_viscosity
            fluid.apparent_viscosity = max(
                self._VISCOSITY_FLOOR,
                fluid.apparent_viscosity + viscosity_delta,
            )
            # Classify the rheological state from the current conditions.
            fluid.rheological_state = self._classify_rheological_state(
                fluid.shear_rate,
                fluid.yield_stress,
                fluid.apparent_viscosity,
                fluid.resting_viscosity,
            )
            if fluid.state == FluidState.PENDING:
                fluid.state = FluidState.SAMPLED
            yield_sum += fluid.yield_stress
            sampled_fluids += 1
        avg_yield = (yield_sum / sampled_fluids) if sampled_fluids > 0 else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_sample_fluid", {
            "sampled_fluids": sampled_fluids,
            "avg_yield_stress": avg_yield,
        })
        return {
            "phase": "sample_fluid",
            "sampled_fluids": sampled_fluids,
            "avg_yield_stress": avg_yield,
        }

    def _phase_map_shear_yield(self) -> Dict[str, Any]:
        """Map phase: chart shear-yield contours where each fluid yields."""
        contours_mapped = 0
        for fluid in self._fluids.values():
            if fluid.state != FluidState.SAMPLED:
                continue
            # Chart a few contour points around the yield surface per fluid.
            base_radius = self._compute_yield_radius(fluid.yield_stress, fluid.shear_rate)
            for ring in range(3):
                if len(self._contours) >= self._MAX_CONTOURS:
                    break
                contour_id = (
                    f"contour_{fluid.fluid_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}_{ring}"
                )
                radius = base_radius * (0.75 + 0.25 * ring)
                angle = random.uniform(0.0, self._TWO_PI)
                # Yield strength falls off with radius.
                yield_strength = max(0.0, 1.0 - (radius / self._WIDE_YIELD_RADIUS))
                contour_entry = {
                    "contour_id": contour_id,
                    "fluid_id": fluid.fluid_id,
                    "entity_id": fluid.entity_id,
                    "shear_stress": fluid.yield_stress,
                    "yield_radius": radius,
                    "yield_angle": angle,
                    "yield_strength": yield_strength,
                    "fluid_class": fluid.fluid_class.value,
                    "thixotropy_tier": fluid.thixotropy_tier.value,
                    "ring": ring,
                    "created_at": time.time(),
                }
                self._contours[contour_id] = contour_entry
                contours_mapped += 1
            fluid.state = FluidState.MAPPED
            fluid.last_sheared_at = time.time()
        self._update_stats(phase_runs=1, contours_mapped=contours_mapped)
        self._record_event("phase_map_shear_yield", {"contours_mapped": contours_mapped})
        return {"phase": "map_shear_yield", "contours_mapped": contours_mapped}

    def _phase_chart_viscosity_relaxation(self) -> Dict[str, Any]:
        """Chart phase: chart viscosity relaxation curves tracing rebuild at rest."""
        curves_charted = 0
        for fluid in self._fluids.values():
            if fluid.state != FluidState.MAPPED:
                continue
            if len(self._curves) >= self._MAX_CURVES:
                break
            t_half = self._compute_relaxation_half_life(fluid.thixotropy_area)
            # Recovery fraction rises toward 1.0 as the gel rebuilds.
            recovery_fraction = min(1.0, fluid.apparent_viscosity / max(fluid.resting_viscosity, self._VISCOSITY_FLOOR))
            final_viscosity = fluid.resting_viscosity
            # Sample a few points along the exponential rebuild curve.
            points: List[float] = []
            for step in range(5):
                t = step * t_half
                # Exponential approach back to resting viscosity.
                v = fluid.apparent_viscosity + (final_viscosity - fluid.apparent_viscosity) * (
                    1.0 - math.exp(-t / max(t_half, 0.001))
                )
                points.append(round(v, 6))
            curve_id = (
                f"curve_{fluid.fluid_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            curve_entry = {
                "curve_id": curve_id,
                "fluid_id": fluid.fluid_id,
                "entity_id": fluid.entity_id,
                "t_half": t_half,
                "recovery_fraction": recovery_fraction,
                "initial_viscosity": fluid.apparent_viscosity,
                "final_viscosity": final_viscosity,
                "points": points,
                "thixotropy_tier": fluid.thixotropy_tier.value,
                "created_at": time.time(),
            }
            self._curves[curve_id] = curve_entry
            curves_charted += 1
            fluid.state = FluidState.CHARTED
        self._update_stats(phase_runs=1, curves_charts=curves_charted)
        self._record_event("phase_chart_viscosity_relaxation", {"curves_charted": curves_charted})
        return {"phase": "chart_viscosity_relaxation", "curves_charted": curves_charted}

    def _phase_cartograph_gel_sol_transition(self) -> Dict[str, Any]:
        """Cartograph phase: map gel-sol transition zones across the sample field."""
        transitions_cartographed = 0
        for fluid in self._fluids.values():
            if fluid.state != FluidState.CHARTED:
                continue
            if len(self._transitions) >= self._MAX_TRANSITIONS:
                break
            # Boundary sits where the yield contour lies.
            boundary_radius = self._compute_yield_radius(fluid.yield_stress, fluid.shear_rate)
            # Gel side is thick (resting), sol side is thin (sheared).
            gel_side_viscosity = fluid.resting_viscosity
            sol_side_viscosity = max(
                self._VISCOSITY_FLOOR,
                fluid.resting_viscosity / self._GEL_SOL_VISCOSITY_RATIO,
            )
            # Sharpness scales with thixotropy tier.
            sharpness_map = {
                ThixotropyTier.LOW: 0.5,
                ThixotropyTier.MODERATE: 1.0,
                ThixotropyTier.HIGH: 1.75,
                ThixotropyTier.EXTREME: 2.5,
            }
            transition_sharpness = (
                self._TRANSITION_SHARPNESS_BASE * sharpness_map.get(fluid.thixotropy_tier, 1.0)
            )
            transition_id = (
                f"trans_{fluid.fluid_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            transition_entry = {
                "transition_id": transition_id,
                "fluid_id": fluid.fluid_id,
                "entity_id": fluid.entity_id,
                "boundary_radius": boundary_radius,
                "gel_side_viscosity": gel_side_viscosity,
                "sol_side_viscosity": sol_side_viscosity,
                "transition_sharpness": transition_sharpness,
                "rheological_state": fluid.rheological_state.value,
                "thixotropy_tier": fluid.thixotropy_tier.value,
                "created_at": time.time(),
            }
            self._transitions[transition_id] = transition_entry
            transitions_cartographed += 1
            fluid.state = FluidState.CARTOGRAPHED
        self._update_stats(
            phase_runs=1,
            transitions_cartographed=transitions_cartographed,
        )
        self._record_event("phase_cartograph_gel_sol_transition", {
            "transitions_cartographed": transitions_cartographed,
        })
        return {
            "phase": "cartograph_gel_sol_transition",
            "transitions_cartographed": transitions_cartographed,
        }

    def _phase_emit_contour_map(self) -> Dict[str, Any]:
        """Emit phase: emit the full cartography report with contours, curves, zones."""
        emitted = 0
        for fluid in self._fluids.values():
            if fluid.state != FluidState.CARTOGRAPHED:
                continue
            fluid.state = FluidState.EMITTED
            emitted += 1
        # Stamp fluid vitality based on the contour population.
        for fluid in self._fluids.values():
            fluid.vitality = self._derive_vitality(fluid.fluid_id)
        # Build the emitted contour map report - one entry per emitted fluid.
        for fluid in self._fluids.values():
            if fluid.state != FluidState.EMITTED:
                continue
            report_id = (
                f"report_{fluid.fluid_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            report = {
                "report_id": report_id,
                "fluid_id": fluid.fluid_id,
                "entity_id": fluid.entity_id,
                "fluid_label": fluid.fluid_label,
                "fluid_class": fluid.fluid_class.value,
                "rheological_state": fluid.rheological_state.value,
                "thixotropy_tier": fluid.thixotropy_tier.value,
                "vitality": fluid.vitality.value,
                "color": self._color_for_tier(fluid.thixotropy_tier),
                "yield_stress": fluid.yield_stress,
                "apparent_viscosity": fluid.apparent_viscosity,
                "resting_viscosity": fluid.resting_viscosity,
                "contour_count": sum(
                    1 for c in self._contours.values() if c["fluid_id"] == fluid.fluid_id
                ),
                "curve_count": sum(
                    1 for c in self._curves.values() if c["fluid_id"] == fluid.fluid_id
                ),
                "transition_count": sum(
                    1 for c in self._transitions.values() if c["fluid_id"] == fluid.fluid_id
                ),
                "preview_url": f"/preview/thixotropic/{report_id}.svg",
                "state": "emitted",
                "created_at": time.time(),
            }
            # Cap the report collection.
            if len(self._reports) >= self._MAX_REPORTS:
                oldest_key = next(iter(self._reports))
                self._reports.pop(oldest_key, None)
            self._reports[report_id] = report
        map_size = (
            len(self._fluids) + len(self._contours)
            + len(self._curves) + len(self._transitions) + len(self._reports)
        )
        self._update_stats(phase_runs=1, contour_maps_emitted=1)
        self._record_event("phase_emit_contour_map", {
            "emitted": emitted,
            "map_size": map_size,
        })
        return {
            "phase": "emit_contour_map",
            "emitted": emitted,
            "map_size": map_size,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_fluid_by_id(self, fluid_id: str) -> Optional[FluidSample]:
        """Find a fluid sample by its fluid_id (linear scan over entity_id keys)."""
        for fluid in self._fluids.values():
            if fluid.fluid_id == fluid_id:
                return fluid
        return None

    def _derive_vitality(self, fluid_id: str) -> FluidVitality:
        """Derive vitality for a fluid from its contour and transition population."""
        contour_count = sum(
            1 for c in self._contours.values() if c["fluid_id"] == fluid_id
        )
        transition_count = sum(
            1 for t in self._transitions.values() if t["fluid_id"] == fluid_id
        )
        if contour_count == 0:
            return FluidVitality.DORMANT
        if transition_count >= 2 and contour_count >= 6:
            return FluidVitality.CHAOTIC
        if contour_count <= 1:
            return FluidVitality.STIRRING
        if contour_count <= 3:
            return FluidVitality.FLOWING
        return FluidVitality.DYNAMIC

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_fluids(self) -> None:
        """Seed a few synthetic fluid samples on the first cycle if empty."""
        seeds = [
            (
                "fluid::drilling_mud",
                "Drilling Mud",
                12.5,
                1.8,
                0.6,
                1.2,
                8.0,
                FluidClass.HERSCHEL_BULKLEY,
            ),
            (
                "fluid::ceramic_slip",
                "Ceramic Slip",
                6.0,
                2.4,
                0.9,
                0.8,
                4.5,
                FluidClass.CASSON,
            ),
            (
                "fluid::paint_coating",
                "Paint Coating",
                3.2,
                1.2,
                0.4,
                2.0,
                1.8,
                FluidClass.PSEUDOPLASTIC,
            ),
        ]
        for entity_id, fluid_label, ys, resting, apparent, sr, area, fclass in seeds:
            if entity_id in self._fluids:
                continue
            if len(self._fluids) >= self._MAX_FLUIDS:
                break
            self.register_fluid(
                entity_id=entity_id,
                fluid_label=fluid_label,
                yield_stress=ys,
                resting_viscosity=resting,
                apparent_viscosity=apparent,
                shear_rate=sr,
                thixotropy_area=area,
                fluid_class=fclass.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _fluid_to_dict(self, fluid: FluidSample) -> Dict[str, Any]:
        return {
            "fluid_id": fluid.fluid_id,
            "entity_id": fluid.entity_id,
            "fluid_label": fluid.fluid_label,
            "yield_stress": fluid.yield_stress,
            "resting_viscosity": fluid.resting_viscosity,
            "apparent_viscosity": fluid.apparent_viscosity,
            "shear_rate": fluid.shear_rate,
            "thixotropy_area": fluid.thixotropy_area,
            "fluid_class": fluid.fluid_class.value,
            "rheological_state": fluid.rheological_state.value,
            "thixotropy_tier": fluid.thixotropy_tier.value,
            "state": fluid.state.value,
            "vitality": fluid.vitality.value,
            "created_at": fluid.created_at,
            "last_sheared_at": fluid.last_sheared_at,
            "note": fluid.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "fluids": len(self._fluids),
                "contours": len(self._contours),
                "curves": len(self._curves),
                "transitions": len(self._transitions),
                "reports": len(self._reports),
                "stats": dict(self._stats),
            }

    def get_fluids(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            fluids = sorted(
                self._fluids.values(),
                key=lambda f: f.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(self._fluids),
                "fluids": [
                    {
                        "fluid_id": f.fluid_id,
                        "entity_id": f.entity_id,
                        "fluid_label": f.fluid_label,
                        "yield_stress": f.yield_stress,
                        "fluid_class": f.fluid_class.value,
                        "thixotropy_tier": f.thixotropy_tier.value,
                        "rheological_state": f.rheological_state.value,
                        "vitality": f.vitality.value,
                    }
                    for f in fluids
                ],
            }

    def get_fluid(self, fluid_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT fluid_id, so we
        # MUST iterate over values and match on the fluid_id attribute.
        with self._global_lock:
            fluid = self._find_fluid_by_id(fluid_id)
            if fluid is None:
                return {
                    "error": "fluid not found",
                    "fluid_id": fluid_id,
                }
            return self._fluid_to_dict(fluid)

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_contour_map(self) -> Dict[str, Any]:
        """Return the full contour map with fluids, contours, curves, and transitions."""
        with self._global_lock:
            return {
                "fluids": [self._fluid_to_dict(f) for f in self._fluids.values()],
                "contours": list(self._contours.values()),
                "curves": list(self._curves.values()),
                "transitions": list(self._transitions.values()),
                "reports": list(self._reports.values()),
                "fluid_count": len(self._fluids),
                "contour_count": len(self._contours),
                "curve_count": len(self._curves),
                "transition_count": len(self._transitions),
                "report_count": len(self._reports),
                "cycle_count": self._cycle_count,
            }

    def cartograph_fluids(self) -> Dict[str, Any]:
        """Produce a domain-specific cartography report across all fluid samples.

        Summarizes shear-yield contour reach, viscosity-relaxation signatures,
        and gel-sol transition boundaries into a single layered report for the
        editor.
        """
        with self._global_lock:
            tier_counts: Dict[str, int] = {tier.value: 0 for tier in ThixotropyTier}
            state_counts: Dict[str, int] = {state.value: 0 for state in RheologicalState}
            yield_radius_sum = 0.0
            half_life_sum = 0.0
            contour_count = len(self._contours)
            curve_count = len(self._curves)
            transition_count = len(self._transitions)
            for fluid in self._fluids.values():
                tier_counts[fluid.thixotropy_tier.value] += 1
                state_counts[fluid.rheological_state.value] += 1
                yield_radius_sum += self._compute_yield_radius(
                    fluid.yield_stress, fluid.shear_rate,
                )
                half_life_sum += self._compute_relaxation_half_life(fluid.thixotropy_area)
            fluid_count = len(self._fluids)
            avg_yield_radius = (yield_radius_sum / fluid_count) if fluid_count > 0 else 0.0
            avg_half_life = (half_life_sum / fluid_count) if fluid_count > 0 else 0.0
            report = {
                "fluid_count": fluid_count,
                "contour_count": contour_count,
                "curve_count": curve_count,
                "transition_count": transition_count,
                "avg_yield_radius": avg_yield_radius,
                "avg_relaxation_half_life": avg_half_life,
                "tier_distribution": tier_counts,
                "state_distribution": state_counts,
                "cycle_count": self._cycle_count,
                "cartographed_at": time.time(),
            }
            self._record_event("cartograph_fluids", {
                "fluid_count": fluid_count,
                "contour_count": contour_count,
                "transition_count": transition_count,
            })
            return report

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic fluids if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._fluids:
                self._seed_synthetic_fluids()
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
            self._fluids.clear()
            self._contours.clear()
            self._curves.clear()
            self._transitions.clear()
            self._reports.clear()
            self._phase = CartographerPhase.SAMPLE_FLUID
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so cycles produce meaningful output immediately.
            self._seed_synthetic_fluids()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
