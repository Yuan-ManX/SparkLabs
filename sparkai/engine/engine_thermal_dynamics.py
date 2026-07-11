"""
SparkLabs Engine - Thermal Dynamics System

Simulates heat propagation, temperature diffusion, fire spread, phase
transitions (melting, freezing, boiling, condensing), and thermal-based
gameplay mechanics for the SparkLabs AI-native game engine. The system
maintains a set of thermal zones, each backed by a discretized
temperature grid, and steps them forward with conduction, convection,
and radiation transfer modes. Heat sources inject energy into zones,
fire fronts propagate across combustible materials, and materials can
transition between solid, liquid, gas, and plasma states.

Architecture:
  _ThermalDynamicsSystem (singleton)
    |-- HeatTransferMode, FireIntensity, FireStatus, PhaseState,
       ThermalZoneStatus, ThermalEventKind
    |-- ThermalConfig, ThermalZone, HeatSource, FireFront,
       MaterialThermal, TemperatureReading, PhaseTransition,
       ThermalSnapshot, ThermalStats, ThermalEvent
    |-- get_thermal_dynamics_system

Core Capabilities:
  - register_zone / get_zone / remove_zone / list_zones /
    set_zone_temperature / get_zone_temperature / get_zone_status
  - register_heat_source / get_heat_source / remove_heat_source /
    list_heat_sources / adjust_heat_source / toggle_heat_source
  - ignite_fire / get_fire / extinguish_fire / list_fires /
    spread_fire / get_fire_intensity / check_fire_spread / get_fire_front
  - register_material / get_material / list_materials / remove_material
  - measure_temperature / get_temperature_grid / compute_heat_flow /
    check_phase_transition / get_phase_transition / list_phase_transitions /
    apply_cooling / apply_heating
  - ai_predict_fire_spread / ai_optimize_cooling / ai_assess_thermal_risk
  - get_status / get_stats / get_snapshot / get_config / set_config /
    list_events / tick / reset_zone / get_temperature_readings /
    get_visualization_data / get_heat_map

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`_ThermalDynamicsSystem.get_instance` or the module-level
:func:`get_thermal_dynamics_system` factory.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sparkai.engine.engine_formation_system import (
    _clamp,
    _coerce_enum,
    _dataclass_to_dict,
    _evict_fifo_dict,
    _evict_fifo_list,
    _new_id,
    _now,
    _safe_float,
    _safe_int,
    _to_jsonable,
)


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_ZONES: int = 500
_MAX_HEAT_SOURCES: int = 1000
_MAX_FIRES: int = 500
_MAX_MATERIALS: int = 500
_MAX_PHASE_TRANSITIONS: int = 2000
_MAX_TEMPERATURE_READINGS: int = 5000
_MAX_EVENTS: int = 10000

# Default grid resolution for a newly registered thermal zone.
_DEFAULT_GRID_SIZE: int = 16

# Smallest temperature delta considered meaningful. Anything below this
# is treated as "no change" by the diffusion solver to avoid floating
# point churn.
_TEMP_EPSILON: float = 1e-4

# Absolute zero in Celsius. Used as a hard floor when cooling is applied.
_ABSOLUTE_ZERO_C: float = -273.15

# Smoothing kernel used by the heat-flow estimator. Larger values mix
# a wider neighborhood into the per-cell gradient estimate.
_FLOW_KERNEL_RADIUS: int = 1

# Mapping from fire intensity to a representative surface temperature in
# degrees Celsius. Used by ignition, spread, and risk computations.
_FIRE_INTENSITY_TEMPS: Dict[str, float] = {
    "smoldering": 250.0,
    "small": 450.0,
    "medium": 700.0,
    "large": 950.0,
    "inferno": 1300.0,
}

# Mapping from fire intensity to a unitless spread-rate multiplier.
_FIRE_INTENSITY_SPREAD: Dict[str, float] = {
    "smoldering": 0.1,
    "small": 0.3,
    "medium": 0.6,
    "large": 0.9,
    "inferno": 1.4,
}

# Risk score thresholds used by the AI risk assessment helper.
_RISK_LOW: float = 0.25
_RISK_MODERATE: float = 0.5
_RISK_HIGH: float = 0.75


# ---------------------------------------------------------------------------
# Module-level Lock
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()

# Small numeric epsilon reused across comparisons.
_EPSILON: float = 1e-9


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HeatTransferMode(str, Enum):
    """Mode of heat transfer between cells and zones."""
    CONDUCTION = "conduction"
    CONVECTION = "convection"
    RADIATION = "radiation"
    COMBINED = "combined"


class FireIntensity(str, Enum):
    """Intensity classification of a fire front."""
    SMOLDERING = "smoldering"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    INFERNO = "inferno"


class FireStatus(str, Enum):
    """Lifecycle status of a fire front."""
    IGNITION = "ignition"
    SPREADING = "spreading"
    PEAK = "peak"
    DYING = "dying"
    EXTINGUISHED = "extinguished"


class PhaseState(str, Enum):
    """Physical phase of a material at a given temperature."""
    SOLID = "solid"
    LIQUID = "liquid"
    GAS = "gas"
    PLASMA = "plasma"


class ThermalZoneStatus(str, Enum):
    """Operational status of a thermal zone."""
    STABLE = "stable"
    HEATING = "heating"
    COOLING = "cooling"
    CRITICAL = "critical"
    FROZEN = "frozen"
    BURNING = "burning"


class ThermalEventKind(str, Enum):
    """Audit event types emitted by the thermal dynamics system."""
    ZONE_REGISTERED = "zone_registered"
    ZONE_REMOVED = "zone_removed"
    ZONE_TEMPERATURE_SET = "zone_temperature_set"
    ZONE_RESET = "zone_reset"
    HEAT_SOURCE_REGISTERED = "heat_source_registered"
    HEAT_SOURCE_REMOVED = "heat_source_removed"
    HEAT_SOURCE_ADJUSTED = "heat_source_adjusted"
    HEAT_SOURCE_TOGGLED = "heat_source_toggled"
    FIRE_IGNITED = "fire_ignited"
    FIRE_SPREAD = "fire_spread"
    FIRE_EXTINGUISHED = "fire_extinguished"
    MATERIAL_REGISTERED = "material_registered"
    MATERIAL_REMOVED = "material_removed"
    PHASE_TRANSITION = "phase_transition"
    COOLING_APPLIED = "cooling_applied"
    HEATING_APPLIED = "heating_applied"
    TICK = "tick"
    CONFIG_UPDATED = "config_updated"
    AI_ASSESSMENT = "ai_assessment"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ThermalConfig:
    """Tunable runtime configuration for the thermal dynamics system."""
    grid_size: int = _DEFAULT_GRID_SIZE
    max_zones: int = _MAX_ZONES
    max_heat_sources: int = _MAX_HEAT_SOURCES
    max_fires: int = _MAX_FIRES
    max_materials: int = _MAX_MATERIALS
    global_ambient_temp: float = 20.0
    diffusion_rate: float = 0.1
    convection_coefficient: float = 0.05
    radiation_coefficient: float = 0.01
    fire_spread_rate: float = 0.3
    fire_decay_rate: float = 0.02
    cooling_loss_rate: float = 0.01
    enable_phase_transitions: bool = True
    enable_radiation: bool = True
    enable_convection: bool = True
    ai_analysis_frequency: int = 50
    critical_temp_threshold: float = 800.0
    freezing_temp_threshold: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ThermalZone:
    """A rectangular grid region with its own temperature field.

    Each cell holds a temperature in degrees Celsius. The zone tracks an
    ambient temperature that cells relax toward when no heat source is
    active, and a status flag derived from the average temperature.
    """
    zone_id: str
    name: str
    bounds: Tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0)
    grid_size: int = _DEFAULT_GRID_SIZE
    initial_temp: float = 20.0
    ambient_temp: float = 20.0
    status: str = ThermalZoneStatus.STABLE.value
    material_ids: List[str] = field(default_factory=list)
    heat_capacity: float = 1000.0
    cells: List[List[float]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HeatSource:
    """A heat-emitting entity such as a torch, lava vent, or sun."""
    source_id: str
    name: str
    zone_id: str
    power: float = 100.0
    mode: str = HeatTransferMode.CONDUCTION.value
    position: Tuple[float, float] = (0.0, 0.0)
    radius: float = 5.0
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FireFront:
    """A spreading fire edge with direction, intensity, and lifecycle."""
    fire_id: str
    zone_id: str
    position: Tuple[float, float] = (0.0, 0.0)
    direction: float = 0.0
    intensity: str = FireIntensity.SMALL.value
    status: str = FireStatus.IGNITION.value
    distance_traveled: float = 0.0
    max_distance: float = 100.0
    temperature: float = 450.0
    fuel_remaining: float = 1.0
    spread_rate: float = 0.3
    ignited_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MaterialThermal:
    """Thermal properties of a material used by the simulation."""
    material_id: str
    name: str
    conductivity: float = 0.5
    specific_heat: float = 800.0
    density: float = 1000.0
    melting_point: float = 0.0
    boiling_point: float = 100.0
    ignition_point: float = 300.0
    phase: str = PhaseState.SOLID.value
    flammability: float = 0.5
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TemperatureReading:
    """A single temperature measurement at a point in a zone."""
    reading_id: str
    zone_id: str
    position: Tuple[float, float] = (0.0, 0.0)
    temperature: float = 20.0
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhaseTransition:
    """Record of a material changing from one phase to another."""
    transition_id: str
    zone_id: str
    material_id: str
    from_phase: str = PhaseState.SOLID.value
    to_phase: str = PhaseState.LIQUID.value
    temperature: float = 0.0
    threshold: float = 0.0
    transition_type: str = "melting"
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ThermalStats:
    """Roll-up statistics maintained across the system lifetime."""
    total_zones: int = 0
    total_heat_sources: int = 0
    total_fires: int = 0
    total_materials: int = 0
    total_phase_transitions: int = 0
    total_temperature_readings: int = 0
    active_heat_sources: int = 0
    active_fires: int = 0
    burning_zones: int = 0
    frozen_zones: int = 0
    critical_zones: int = 0
    peak_temperature: float = 0.0
    min_temperature: float = 0.0
    avg_temperature: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ThermalSnapshot:
    """A point-in-time snapshot of the full system state."""
    timestamp: str
    zones: List[Dict[str, Any]] = field(default_factory=list)
    heat_sources: List[Dict[str, Any]] = field(default_factory=list)
    fires: List[Dict[str, Any]] = field(default_factory=list)
    materials: List[Dict[str, Any]] = field(default_factory=list)
    phase_transitions: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ThermalEvent:
    """An internal audit event emitted by the thermal dynamics system."""
    event_id: str
    timestamp: str
    event_type: str
    zone_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _make_grid(size: int, value: float) -> List[List[float]]:
    """Build a square grid filled with the given value."""
    n = max(1, _safe_int(size, _DEFAULT_GRID_SIZE))
    return [[_safe_float(value, 0.0) for _ in range(n)] for _ in range(n)]


def _grid_average(grid: List[List[float]]) -> float:
    """Return the arithmetic mean of all cells in a grid."""
    if not grid:
        return 0.0
    total = 0.0
    count = 0
    for row in grid:
        for cell in row:
            total += _safe_float(cell, 0.0)
            count += 1
    if count == 0:
        return 0.0
    return total / count


def _grid_max(grid: List[List[float]]) -> float:
    """Return the maximum cell value in a grid."""
    if not grid:
        return 0.0
    best = -math.inf
    for row in grid:
        for cell in row:
            v = _safe_float(cell, 0.0)
            if v > best:
                best = v
    return best if best != -math.inf else 0.0


def _grid_min(grid: List[List[float]]) -> float:
    """Return the minimum cell value in a grid."""
    if not grid:
        return 0.0
    best = math.inf
    for row in grid:
        for cell in row:
            v = _safe_float(cell, 0.0)
            if v < best:
                best = v
    return best if best != math.inf else 0.0


def _world_to_cell(
    position: Tuple[float, float],
    bounds: Tuple[float, float, float, float],
    grid_size: int,
) -> Tuple[int, int]:
    """Map a world-space (x, y) into grid cell indices (col, row)."""
    x, y = position
    min_x, min_y, max_x, max_y = bounds
    n = max(1, _safe_int(grid_size, _DEFAULT_GRID_SIZE))
    span_x = max(_EPSILON, max_x - min_x)
    span_y = max(_EPSILON, max_y - min_y)
    col = int((x - min_x) / span_x * n)
    row = int((y - min_y) / span_y * n)
    col = _clamp(col, 0, n - 1)
    row = _clamp(row, 0, n - 1)
    return col, row


def _cell_to_world(
    col: int,
    row: int,
    bounds: Tuple[float, float, float, float],
    grid_size: int,
) -> Tuple[float, float]:
    """Map grid cell indices to a world-space (x, y) at the cell center."""
    min_x, min_y, max_x, max_y = bounds
    n = max(1, _safe_int(grid_size, _DEFAULT_GRID_SIZE))
    span_x = max(_EPSILON, max_x - min_x)
    span_y = max(_EPSILON, max_y - min_y)
    x = min_x + (col + 0.5) / n * span_x
    y = min_y + (row + 0.5) / n * span_y
    return x, y


def _distance_2d(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Euclidean distance between two 2D points."""
    dx = _safe_float(a[0], 0.0) - _safe_float(b[0], 0.0)
    dy = _safe_float(a[1], 0.0) - _safe_float(b[1], 0.0)
    return math.sqrt(dx * dx + dy * dy)


def _classify_zone_status(
    avg_temp: float,
    ambient: float,
    config: ThermalConfig,
) -> str:
    """Derive a ThermalZoneStatus from the current average temperature."""
    avg = _safe_float(avg_temp, ambient)
    amb = _safe_float(ambient, config.global_ambient_temp)
    if avg >= config.critical_temp_threshold:
        return ThermalZoneStatus.CRITICAL.value
    if avg <= config.freezing_temp_threshold:
        return ThermalZoneStatus.FROZEN.value
    if avg > amb + _TEMP_EPSILON:
        return ThermalZoneStatus.HEATING.value
    if avg < amb - _TEMP_EPSILON:
        return ThermalZoneStatus.COOLING.value
    return ThermalZoneStatus.STABLE.value


def _intensity_to_temperature(intensity: str) -> float:
    """Map a fire intensity label to a representative temperature."""
    key = str(intensity).strip().lower()
    return _FIRE_INTENSITY_TEMPS.get(key, _FIRE_INTENSITY_TEMPS["small"])


def _intensity_to_spread(intensity: str) -> float:
    """Map a fire intensity label to a spread-rate multiplier."""
    key = str(intensity).strip().lower()
    return _FIRE_INTENSITY_SPREAD.get(key, _FIRE_INTENSITY_SPREAD["small"])


def _phase_for_temperature(
    temp: float,
    material: Optional[MaterialThermal],
) -> str:
    """Determine the PhaseState for a material at a given temperature."""
    t = _safe_float(temp, 0.0)
    if material is None:
        if t >= 10000.0:
            return PhaseState.PLASMA.value
        if t >= 100.0:
            return PhaseState.GAS.value
        if t >= 0.0:
            return PhaseState.LIQUID.value
        return PhaseState.SOLID.value
    if t >= material.boiling_point * 5.0:
        return PhaseState.PLASMA.value
    if t >= material.boiling_point:
        return PhaseState.GAS.value
    if t >= material.melting_point:
        return PhaseState.LIQUID.value
    return PhaseState.SOLID.value


def _transition_type(from_phase: str, to_phase: str) -> str:
    """Name a phase transition based on the source and target phases."""
    pair = (str(from_phase).lower(), str(to_phase).lower())
    if pair == ("solid", "liquid"):
        return "melting"
    if pair == ("liquid", "solid"):
        return "freezing"
    if pair == ("liquid", "gas"):
        return "boiling"
    if pair == ("gas", "liquid"):
        return "condensing"
    if pair == ("solid", "gas"):
        return "sublimating"
    if pair == ("gas", "solid"):
        return "depositing"
    if pair == ("gas", "plasma"):
        return "ionizing"
    if pair == ("plasma", "gas"):
        return "recombining"
    return "transition"


def _risk_label(score: float) -> str:
    """Map a numeric risk score to a human-readable label."""
    s = _clamp(_safe_float(score, 0.0), 0.0, 1.0)
    if s >= _RISK_HIGH:
        return "high"
    if s >= _RISK_MODERATE:
        return "moderate"
    if s >= _RISK_LOW:
        return "low"
    return "negligible"


# ---------------------------------------------------------------------------
# Thermal Dynamics System (Singleton)
# ---------------------------------------------------------------------------

class _ThermalDynamicsSystem:
    """Simulates heat propagation, fire spread, and phase transitions.

    The system is thread-safe and implemented as a singleton with
    double-checked locking. ``_init_lock`` guards singleton creation and
    seeding; ``_lock`` guards all mutating operations to keep internal
    dictionaries consistent.

    The simulation model is intentionally lightweight: each zone owns a
    square temperature grid, and each tick diffuses temperatures toward
    neighbors (conduction), relaxes toward the ambient baseline
    (convection), and radiates a fraction of energy away (radiation).
    Heat sources inject energy into the cells within their radius, and
    fire fronts ignite combustible materials and propagate outward.
    """

    _instance: Optional["_ThermalDynamicsSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._seeded: bool = False
        self._zones: Dict[str, ThermalZone] = {}
        self._heat_sources: Dict[str, HeatSource] = {}
        self._fires: Dict[str, FireFront] = {}
        self._materials: Dict[str, MaterialThermal] = {}
        self._phase_transitions: Dict[str, PhaseTransition] = {}
        self._temperature_readings: Dict[str, TemperatureReading] = {}
        self._events: List[ThermalEvent] = []
        self._config = ThermalConfig()
        self._stats = ThermalStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._reading_counter: int = 0
        self._transition_counter: int = 0
        self._global_time: float = 0.0

    @classmethod
    def get_instance(cls) -> "_ThermalDynamicsSystem":
        """Return the shared singleton, creating and seeding it if needed."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Explicitly seed the system if it has not been seeded yet."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed_data()
            self._initialized = True

    def _seed_data(self) -> None:
        """Populate the system with a canonical set of thermal data."""
        with self._lock:
            if self._seeded:
                return

            # ----------------------------------------------------------
            # Materials (5)
            # ----------------------------------------------------------
            material_seeds: List[Tuple[str, str, float, float, float, float, float, float, float, str, float]] = [
                ("mat_wood", "Wood", 0.15, 1700.0, 700.0, 0.0, 300.0, 250.0,
                 PhaseState.SOLID.value, 0.8),
                ("mat_stone", "Stone", 2.0, 900.0, 2700.0, 1200.0, 2700.0, 9999.0,
                 PhaseState.SOLID.value, 0.05),
                ("mat_iron", "Iron", 80.0, 450.0, 7800.0, 1538.0, 2862.0, 9999.0,
                 PhaseState.SOLID.value, 0.02),
                ("mat_water", "Water", 0.6, 4186.0, 1000.0, 0.0, 100.0, 9999.0,
                 PhaseState.LIQUID.value, 0.0),
                ("mat_ice", "Ice", 2.18, 2090.0, 917.0, -50.0, 0.0, 9999.0,
                 PhaseState.SOLID.value, 0.0),
            ]
            for (mid, name, cond, sh, dens, mp, bp, ign, phase, flam) in material_seeds:
                material = MaterialThermal(
                    material_id=mid,
                    name=name,
                    conductivity=cond,
                    specific_heat=sh,
                    density=dens,
                    melting_point=mp,
                    boiling_point=bp,
                    ignition_point=ign,
                    phase=phase,
                    flammability=flam,
                )
                self._materials[mid] = material

            # ----------------------------------------------------------
            # Thermal Zones (4)
            # ----------------------------------------------------------
            zone_seeds: List[Tuple[str, str, Tuple[float, float, float, float], float, float, List[str], float]] = [
                ("zone_forest", "Forest Grove", (0.0, 0.0, 120.0, 120.0),
                 18.0, 18.0, ["mat_wood", "mat_water"], 1200.0),
                ("zone_volcano", "Volcano Caldera", (200.0, 0.0, 320.0, 120.0),
                 320.0, 60.0, ["mat_stone", "mat_iron"], 1500.0),
                ("zone_tundra", "Frozen Tundra", (0.0, 200.0, 120.0, 320.0),
                 -15.0, -10.0, ["mat_ice", "mat_water"], 900.0),
                ("zone_desert", "Sunscorched Desert", (200.0, 200.0, 320.0, 320.0),
                 45.0, 35.0, ["mat_stone", "mat_iron"], 1100.0),
            ]
            for (zid, name, bounds, init_t, amb_t, mats, hc) in zone_seeds:
                grid = _make_grid(self._config.grid_size, init_t)
                zone = ThermalZone(
                    zone_id=zid,
                    name=name,
                    bounds=bounds,
                    grid_size=self._config.grid_size,
                    initial_temp=init_t,
                    ambient_temp=amb_t,
                    status=_classify_zone_status(init_t, amb_t, self._config),
                    material_ids=list(mats),
                    heat_capacity=hc,
                    cells=grid,
                )
                self._zones[zid] = zone

            # ----------------------------------------------------------
            # Heat Sources (3)
            # ----------------------------------------------------------
            heat_source_seeds: List[Tuple[str, str, str, float, str, Tuple[float, float], float, bool]] = [
                ("hs_lava_vent", "Lava Vent", "zone_volcano", 800.0,
                 HeatTransferMode.RADIATION.value, (260.0, 60.0), 25.0, True),
                ("hs_campfire", "Campfire", "zone_forest", 150.0,
                 HeatTransferMode.CONVECTION.value, (60.0, 60.0), 8.0, True),
                ("hs_sun_desert", "Desert Sun", "zone_desert", 220.0,
                 HeatTransferMode.RADIATION.value, (260.0, 260.0), 60.0, True),
            ]
            for (sid, name, zid, power, mode, pos, radius, active) in heat_source_seeds:
                source = HeatSource(
                    source_id=sid,
                    name=name,
                    zone_id=zid,
                    power=power,
                    mode=mode,
                    position=pos,
                    radius=radius,
                    active=active,
                )
                self._heat_sources[sid] = source

            # ----------------------------------------------------------
            # Fire Fronts (3)
            # ----------------------------------------------------------
            fire_seeds: List[Tuple[str, str, Tuple[float, float], float, str, str, float, float]] = [
                ("fire_forest_001", "zone_forest", (50.0, 60.0), 45.0,
                 FireIntensity.MEDIUM.value, FireStatus.SPREADING.value, 80.0, 0.6),
                ("fire_camp_002", "zone_forest", (62.0, 58.0), 90.0,
                 FireIntensity.SMALL.value, FireStatus.PEAK.value, 30.0, 0.3),
                ("fire_volcano_003", "zone_volcano", (250.0, 55.0), 180.0,
                 FireIntensity.LARGE.value, FireStatus.SPREADING.value, 120.0, 0.9),
            ]
            for (fid, zid, pos, direction, intensity, status, max_dist, fuel) in fire_seeds:
                fire = FireFront(
                    fire_id=fid,
                    zone_id=zid,
                    position=pos,
                    direction=direction,
                    intensity=intensity,
                    status=status,
                    max_distance=max_dist,
                    temperature=_intensity_to_temperature(intensity),
                    fuel_remaining=fuel,
                    spread_rate=_intensity_to_spread(intensity),
                )
                self._fires[fid] = fire

            # ----------------------------------------------------------
            # Phase Transitions (3)
            # ----------------------------------------------------------
            transition_seeds: List[Tuple[str, str, str, str, str, float, float, str]] = [
                ("pt_001", "zone_volcano", "mat_stone", PhaseState.SOLID.value,
                 PhaseState.LIQUID.value, 1250.0, 1200.0, "melting"),
                ("pt_002", "zone_tundra", "mat_water", PhaseState.LIQUID.value,
                 PhaseState.SOLID.value, -5.0, 0.0, "freezing"),
                ("pt_003", "zone_volcano", "mat_iron", PhaseState.SOLID.value,
                 PhaseState.LIQUID.value, 1540.0, 1538.0, "melting"),
            ]
            for (tid, zid, mid, from_p, to_p, temp, threshold, ttype) in transition_seeds:
                transition = PhaseTransition(
                    transition_id=tid,
                    zone_id=zid,
                    material_id=mid,
                    from_phase=from_p,
                    to_phase=to_p,
                    temperature=temp,
                    threshold=threshold,
                    transition_type=ttype,
                )
                self._phase_transitions[tid] = transition

            # ----------------------------------------------------------
            # Temperature Readings (3)
            # ----------------------------------------------------------
            reading_seeds: List[Tuple[str, str, Tuple[float, float], float]] = [
                ("tr_001", "zone_forest", (40.0, 50.0), 22.5),
                ("tr_002", "zone_volcano", (260.0, 60.0), 305.0),
                ("tr_003", "zone_tundra", (60.0, 260.0), -12.0),
            ]
            for (rid, zid, pos, temp) in reading_seeds:
                reading = TemperatureReading(
                    reading_id=rid,
                    zone_id=zid,
                    position=pos,
                    temperature=temp,
                )
                self._temperature_readings[rid] = reading

            # ----------------------------------------------------------
            # Events (6)
            # ----------------------------------------------------------
            event_seeds: List[Tuple[str, str, str]] = [
                (ThermalEventKind.ZONE_REGISTERED.value, "zone_forest",
                 "Forest Grove zone registered."),
                (ThermalEventKind.HEAT_SOURCE_REGISTERED.value, "zone_volcano",
                 "Lava Vent heat source registered."),
                (ThermalEventKind.FIRE_IGNITED.value, "zone_forest",
                 "Forest fire ignited at medium intensity."),
                (ThermalEventKind.PHASE_TRANSITION.value, "zone_volcano",
                 "Stone began melting in the caldera."),
                (ThermalEventKind.MATERIAL_REGISTERED.value, "",
                 "Wood, stone, iron, water, ice materials registered."),
                (ThermalEventKind.TICK.value, "",
                 "Initial thermal state seeded."),
            ]
            for kind, zid, desc in event_seeds:
                self._event_counter += 1
                self._events.append(ThermalEvent(
                    event_id=f"tevt_{self._event_counter:08d}",
                    timestamp=_now(),
                    event_type=kind,
                    zone_id=zid,
                    description=desc,
                ))
            _evict_fifo_list(self._events, _MAX_EVENTS)

            self._refresh_stats()
            self._seeded = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        zone_id: str = "",
        description: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event to the rolling event log."""
        self._event_counter += 1
        event = ThermalEvent(
            event_id=f"tevt_{self._event_counter:08d}",
            timestamp=_now(),
            event_type=event_type,
            zone_id=zone_id,
            description=description,
            metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        """Recompute the cached ThermalStats roll-up from current state."""
        self._stats.total_zones = len(self._zones)
        self._stats.total_heat_sources = len(self._heat_sources)
        self._stats.total_fires = len(self._fires)
        self._stats.total_materials = len(self._materials)
        self._stats.total_phase_transitions = len(self._phase_transitions)
        self._stats.total_temperature_readings = len(self._temperature_readings)
        self._stats.active_heat_sources = sum(
            1 for s in self._heat_sources.values() if s.active
        )
        active_fire_statuses = (
            FireStatus.IGNITION.value,
            FireStatus.SPREADING.value,
            FireStatus.PEAK.value,
        )
        self._stats.active_fires = sum(
            1 for f in self._fires.values() if f.status in active_fire_statuses
        )
        self._stats.burning_zones = sum(
            1 for z in self._zones.values()
            if z.status == ThermalZoneStatus.BURNING.value
        )
        self._stats.frozen_zones = sum(
            1 for z in self._zones.values()
            if z.status == ThermalZoneStatus.FROZEN.value
        )
        self._stats.critical_zones = sum(
            1 for z in self._zones.values()
            if z.status == ThermalZoneStatus.CRITICAL.value
        )
        peak = -math.inf
        lowest = math.inf
        temp_sum = 0.0
        temp_count = 0
        for zone in self._zones.values():
            avg = _grid_average(zone.cells)
            temp_sum += avg
            temp_count += 1
            cell_max = _grid_max(zone.cells)
            cell_min = _grid_min(zone.cells)
            if cell_max > peak:
                peak = cell_max
            if cell_min < lowest:
                lowest = cell_min
        self._stats.peak_temperature = peak if peak != -math.inf else 0.0
        self._stats.min_temperature = lowest if lowest != math.inf else 0.0
        self._stats.avg_temperature = (
            temp_sum / temp_count if temp_count > 0 else 0.0
        )
        self._stats.tick_count = self._tick_count

    def _update_zone_status(self, zone: ThermalZone) -> None:
        """Recompute and store the status of a zone from its grid."""
        avg = _grid_average(zone.cells)
        zone.status = _classify_zone_status(avg, zone.ambient_temp, self._config)
        zone.updated_at = _now()
        # Mark burning if any active fire is inside this zone.
        for fire in self._fires.values():
            if fire.zone_id != zone.zone_id:
                continue
            if fire.status in (
                FireStatus.IGNITION.value,
                FireStatus.SPREADING.value,
                FireStatus.PEAK.value,
            ):
                zone.status = ThermalZoneStatus.BURNING.value
                break

    def _apply_heat_source_to_grid(
        self,
        source: HeatSource,
        zone: ThermalZone,
        dt: float,
    ) -> None:
        """Inject heat from a single source into the zone grid."""
        if not source.active or source.power <= 0.0:
            return
        n = max(1, zone.grid_size)
        col, row = _world_to_cell(source.position, zone.bounds, n)
        radius_cells = max(1, int(source.radius / max(_EPSILON, (zone.bounds[2] - zone.bounds[0])) * n))
        # Energy scales with power, dt, and an inverse-square falloff.
        for dr in range(-radius_cells, radius_cells + 1):
            for dc in range(-radius_cells, radius_cells + 1):
                rr = row + dr
                cc = col + dc
                if rr < 0 or rr >= n or cc < 0 or cc >= n:
                    continue
                dist = math.sqrt(dr * dr + dc * dc)
                if dist > radius_cells:
                    continue
                falloff = 1.0 / (1.0 + dist * dist)
                delta = source.power * dt * falloff / max(_EPSILON, zone.heat_capacity)
                zone.cells[rr][cc] += delta

    def _diffuse_grid(
        self,
        zone: ThermalZone,
        dt: float,
    ) -> None:
        """Apply one diffusion step to a zone grid (conduction)."""
        n = max(1, zone.grid_size)
        if n < 2:
            return
        # Use a copy so updates do not feed back into the same step.
        prev = [list(row) for row in zone.cells]
        rate = _clamp(self._config.diffusion_rate * dt, 0.0, 0.25)
        for r in range(n):
            for c in range(n):
                neighbors = []
                if r > 0:
                    neighbors.append(prev[r - 1][c])
                if r < n - 1:
                    neighbors.append(prev[r + 1][c])
                if c > 0:
                    neighbors.append(prev[r][c - 1])
                if c < n - 1:
                    neighbors.append(prev[r][c + 1])
                if not neighbors:
                    continue
                neighbor_avg = sum(neighbors) / len(neighbors)
                current = prev[r][c]
                zone.cells[r][c] = current + rate * (neighbor_avg - current)

    def _apply_convection(
        self,
        zone: ThermalZone,
        dt: float,
    ) -> None:
        """Relax the grid toward the ambient temperature (convection)."""
        if not self._config.enable_convection:
            return
        n = max(1, zone.grid_size)
        coeff = _clamp(self._config.convection_coefficient * dt, 0.0, 0.5)
        ambient = zone.ambient_temp
        for r in range(n):
            for c in range(n):
                current = zone.cells[r][c]
                zone.cells[r][c] = current + coeff * (ambient - current)

    def _apply_radiation(
        self,
        zone: ThermalZone,
        dt: float,
    ) -> None:
        """Bleed a fraction of energy away (radiation to the environment)."""
        if not self._config.enable_radiation:
            return
        n = max(1, zone.grid_size)
        coeff = _clamp(self._config.radiation_coefficient * dt, 0.0, 0.5)
        ambient = zone.ambient_temp
        for r in range(n):
            for c in range(n):
                current = zone.cells[r][c]
                # Stefan-Boltzmann-ish cooling toward ambient. The linear
                # approximation keeps the simulation stable for large dt.
                delta = coeff * (current - ambient)
                zone.cells[r][c] = current - delta

    def _advance_fire(self, fire: FireFront, dt: float) -> None:
        """Advance a single fire front by one tick."""
        if fire.status == FireStatus.EXTINGUISHED.value:
            return
        # Consume fuel.
        fire.fuel_remaining = max(0.0, fire.fuel_remaining - self._config.fire_decay_rate * dt)
        if fire.fuel_remaining <= 0.0:
            fire.status = FireStatus.EXTINGUISHED.value
            fire.updated_at = _now()
            return
        # Move the front forward.
        travel = fire.spread_rate * self._config.fire_spread_rate * dt * 10.0
        rad = math.radians(fire.direction)
        x, y = fire.position
        fire.position = (x + math.cos(rad) * travel, y + math.sin(rad) * travel)
        fire.distance_traveled += travel
        if fire.distance_traveled >= fire.max_distance:
            fire.status = FireStatus.DYING.value
        elif fire.fuel_remaining < 0.3:
            fire.status = FireStatus.DYING.value
        elif fire.status == FireStatus.IGNITION.value:
            fire.status = FireStatus.SPREADING.value
        else:
            # Promote to peak when intensity is high and fuel is ample.
            if (fire.intensity in (FireIntensity.LARGE.value, FireIntensity.INFERNO.value)
                    and fire.fuel_remaining > 0.6
                    and fire.status == FireStatus.SPREADING.value):
                fire.status = FireStatus.PEAK.value
        fire.updated_at = _now()
        # Heat the zone near the fire position.
        zone = self._zones.get(fire.zone_id)
        if zone is not None:
            n = max(1, zone.grid_size)
            col, row = _world_to_cell(fire.position, zone.bounds, n)
            radius_cells = max(1, int(fire.spread_rate * 3.0))
            for dr in range(-radius_cells, radius_cells + 1):
                for dc in range(-radius_cells, radius_cells + 1):
                    rr = row + dr
                    cc = col + dc
                    if rr < 0 or rr >= n or cc < 0 or cc >= n:
                        continue
                    dist = math.sqrt(dr * dr + dc * dc)
                    if dist > radius_cells:
                        continue
                    falloff = 1.0 / (1.0 + dist * dist)
                    delta = fire.temperature * dt * falloff / max(_EPSILON, zone.heat_capacity)
                    zone.cells[rr][cc] += delta

    # ------------------------------------------------------------------
    # Zone Management
    # ------------------------------------------------------------------

    def register_zone(
        self,
        zone_id: str,
        name: str,
        bounds: Tuple[float, float, float, float],
        initial_temp: float,
        ambient_temp: float,
        material_ids: Optional[List[str]] = None,
        heat_capacity: float = 1000.0,
        grid_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ThermalZone]]:
        """Register a new thermal zone with its own temperature grid."""
        with self._lock:
            zid = str(zone_id).strip()
            if not zid:
                return False, "zone_id_required", None
            if zid in self._zones:
                return False, "already_exists", None
            if len(self._zones) >= self._config.max_zones:
                return False, "max_zones_reached", None
            try:
                b0, b1, b2, b3 = bounds
                bnds = (
                    _safe_float(b0, 0.0),
                    _safe_float(b1, 0.0),
                    _safe_float(b2, 100.0),
                    _safe_float(b3, 100.0),
                )
                if bnds[2] <= bnds[0] or bnds[3] <= bnds[1]:
                    return False, "invalid_bounds", None
            except (TypeError, ValueError):
                return False, "invalid_bounds", None
            init_t = _safe_float(initial_temp, self._config.global_ambient_temp)
            amb_t = _safe_float(ambient_temp, self._config.global_ambient_temp)
            gs = _safe_int(grid_size, self._config.grid_size)
            gs = max(2, min(128, gs))
            grid = _make_grid(gs, init_t)
            zone = ThermalZone(
                zone_id=zid,
                name=str(name),
                bounds=bnds,
                grid_size=gs,
                initial_temp=init_t,
                ambient_temp=amb_t,
                status=_classify_zone_status(init_t, amb_t, self._config),
                material_ids=list(material_ids) if material_ids else [],
                heat_capacity=max(_EPSILON, _safe_float(heat_capacity, 1000.0)),
                cells=grid,
                metadata=dict(metadata) if metadata else {},
            )
            self._zones[zid] = zone
            self._refresh_stats()
            self._emit(
                ThermalEventKind.ZONE_REGISTERED.value,
                zone_id=zid,
                description=f"Zone '{zone.name}' registered.",
                data={"zone_id": zid, "initial_temp": init_t, "ambient_temp": amb_t},
            )
            return True, "registered", zone

    def get_zone(self, zone_id: str) -> Optional[ThermalZone]:
        """Return a zone by id, or None if it does not exist."""
        return self._zones.get(str(zone_id).strip())

    def remove_zone(self, zone_id: str) -> Tuple[bool, str, Optional[ThermalZone]]:
        """Remove a zone and detach its heat sources and fires."""
        with self._lock:
            zid = str(zone_id).strip()
            zone = self._zones.pop(zid, None)
            if zone is None:
                return False, "not_found", None
            # Detach heat sources tied to this zone.
            for source in self._heat_sources.values():
                if source.zone_id == zid:
                    source.active = False
            # Detach fires tied to this zone.
            for fire in self._fires.values():
                if fire.zone_id == zid:
                    fire.status = FireStatus.EXTINGUISHED.value
            self._refresh_stats()
            self._emit(
                ThermalEventKind.ZONE_REMOVED.value,
                zone_id=zid,
                description=f"Zone '{zone.name}' removed.",
            )
            return True, "removed", zone

    def list_zones(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[ThermalZone]:
        """List zones, optionally filtered by status."""
        cap = max(1, _safe_int(limit, 100))
        result: List[ThermalZone] = []
        target = None
        if status is not None:
            coerced = _coerce_enum(ThermalZoneStatus, status)
            target = coerced.value if coerced else str(status).strip().lower()
        for zone in self._zones.values():
            if target is not None and zone.status != target:
                continue
            result.append(zone)
            if len(result) >= cap:
                break
        return result

    def set_zone_temperature(
        self,
        zone_id: str,
        temperature: float,
    ) -> Tuple[bool, str, Optional[ThermalZone]]:
        """Set every cell in a zone to a uniform temperature."""
        with self._lock:
            zone = self._zones.get(str(zone_id).strip())
            if zone is None:
                return False, "not_found", None
            t = max(_ABSOLUTE_ZERO_C, _safe_float(temperature, zone.ambient_temp))
            for r in range(zone.grid_size):
                for c in range(zone.grid_size):
                    zone.cells[r][c] = t
            zone.initial_temp = t
            self._update_zone_status(zone)
            self._refresh_stats()
            self._emit(
                ThermalEventKind.ZONE_TEMPERATURE_SET.value,
                zone_id=zone.zone_id,
                description=f"Zone temperature set to {t:.2f} C.",
                data={"temperature": t},
            )
            return True, "updated", zone

    def get_zone_temperature(self, zone_id: str) -> Tuple[bool, str, float]:
        """Return the average temperature of a zone."""
        zone = self._zones.get(str(zone_id).strip())
        if zone is None:
            return False, "not_found", 0.0
        return True, "ok", _grid_average(zone.cells)

    def get_zone_status(self, zone_id: str) -> Tuple[bool, str, str]:
        """Return the lifecycle status of a zone."""
        zone = self._zones.get(str(zone_id).strip())
        if zone is None:
            return False, "not_found", ""
        return True, "ok", zone.status

    # ------------------------------------------------------------------
    # Heat Source Management
    # ------------------------------------------------------------------

    def register_heat_source(
        self,
        source_id: str,
        name: str,
        zone_id: str,
        power: float,
        mode: str = HeatTransferMode.CONDUCTION.value,
        position: Tuple[float, float] = (0.0, 0.0),
        radius: float = 5.0,
        active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[HeatSource]]:
        """Register a heat source attached to a zone."""
        with self._lock:
            sid = str(source_id).strip()
            if not sid:
                return False, "source_id_required", None
            if sid in self._heat_sources:
                return False, "already_exists", None
            if len(self._heat_sources) >= self._config.max_heat_sources:
                return False, "max_heat_sources_reached", None
            zone = self._zones.get(str(zone_id).strip())
            if zone is None:
                return False, "zone_not_found", None
            mode_value = _coerce_enum(
                HeatTransferMode, mode, HeatTransferMode.CONDUCTION
            ).value
            try:
                pos = (
                    _safe_float(position[0], 0.0),
                    _safe_float(position[1], 0.0),
                )
            except (TypeError, IndexError):
                pos = (0.0, 0.0)
            source = HeatSource(
                source_id=sid,
                name=str(name),
                zone_id=zone.zone_id,
                power=max(0.0, _safe_float(power, 0.0)),
                mode=mode_value,
                position=pos,
                radius=max(_EPSILON, _safe_float(radius, 5.0)),
                active=bool(active),
                metadata=dict(metadata) if metadata else {},
            )
            self._heat_sources[sid] = source
            self._refresh_stats()
            self._emit(
                ThermalEventKind.HEAT_SOURCE_REGISTERED.value,
                zone_id=zone.zone_id,
                description=f"Heat source '{source.name}' registered.",
                data={"source_id": sid, "power": source.power, "mode": mode_value},
            )
            return True, "registered", source

    def get_heat_source(self, source_id: str) -> Optional[HeatSource]:
        """Return a heat source by id, or None if it does not exist."""
        return self._heat_sources.get(str(source_id).strip())

    def remove_heat_source(
        self,
        source_id: str,
    ) -> Tuple[bool, str, Optional[HeatSource]]:
        """Remove a heat source from the system."""
        with self._lock:
            sid = str(source_id).strip()
            source = self._heat_sources.pop(sid, None)
            if source is None:
                return False, "not_found", None
            self._refresh_stats()
            self._emit(
                ThermalEventKind.HEAT_SOURCE_REMOVED.value,
                zone_id=source.zone_id,
                description=f"Heat source '{source.name}' removed.",
            )
            return True, "removed", source

    def list_heat_sources(
        self,
        zone_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[HeatSource]:
        """List heat sources, optionally filtered by zone."""
        cap = max(1, _safe_int(limit, 100))
        result: List[HeatSource] = []
        target_zone = str(zone_id).strip() if zone_id is not None else None
        for source in self._heat_sources.values():
            if target_zone is not None and source.zone_id != target_zone:
                continue
            result.append(source)
            if len(result) >= cap:
                break
        return result

    def adjust_heat_source(
        self,
        source_id: str,
        power: float,
    ) -> Tuple[bool, str, Optional[HeatSource]]:
        """Adjust the power output of a heat source."""
        with self._lock:
            source = self._heat_sources.get(str(source_id).strip())
            if source is None:
                return False, "not_found", None
            new_power = max(0.0, _safe_float(power, 0.0))
            old_power = source.power
            source.power = new_power
            source.updated_at = _now()
            self._emit(
                ThermalEventKind.HEAT_SOURCE_ADJUSTED.value,
                zone_id=source.zone_id,
                description=f"Heat source '{source.name}' power {old_power:.2f} -> {new_power:.2f}.",
                data={"source_id": source.source_id, "old_power": old_power, "new_power": new_power},
            )
            return True, "adjusted", source

    def toggle_heat_source(
        self,
        source_id: str,
        active: bool,
    ) -> Tuple[bool, str, Optional[HeatSource]]:
        """Enable or disable a heat source without removing it."""
        with self._lock:
            source = self._heat_sources.get(str(source_id).strip())
            if source is None:
                return False, "not_found", None
            source.active = bool(active)
            source.updated_at = _now()
            self._refresh_stats()
            self._emit(
                ThermalEventKind.HEAT_SOURCE_TOGGLED.value,
                zone_id=source.zone_id,
                description=f"Heat source '{source.name}' {'activated' if active else 'deactivated'}.",
                data={"source_id": source.source_id, "active": source.active},
            )
            return True, "toggled", source

    # ------------------------------------------------------------------
    # Fire Management
    # ------------------------------------------------------------------

    def ignite_fire(
        self,
        fire_id: str,
        zone_id: str,
        position: Tuple[float, float],
        intensity: str = FireIntensity.SMALL.value,
        direction: float = 0.0,
        max_distance: float = 100.0,
        fuel: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[FireFront]]:
        """Ignite a new fire front at a position inside a zone."""
        with self._lock:
            fid = str(fire_id).strip()
            if not fid:
                return False, "fire_id_required", None
            if fid in self._fires:
                return False, "already_exists", None
            if len(self._fires) >= self._config.max_fires:
                return False, "max_fires_reached", None
            zone = self._zones.get(str(zone_id).strip())
            if zone is None:
                return False, "zone_not_found", None
            intensity_value = _coerce_enum(
                FireIntensity, intensity, FireIntensity.SMALL
            ).value
            try:
                pos = (
                    _safe_float(position[0], 0.0),
                    _safe_float(position[1], 0.0),
                )
            except (TypeError, IndexError):
                pos = (0.0, 0.0)
            fire = FireFront(
                fire_id=fid,
                zone_id=zone.zone_id,
                position=pos,
                direction=_safe_float(direction, 0.0) % 360.0,
                intensity=intensity_value,
                status=FireStatus.IGNITION.value,
                max_distance=max(0.0, _safe_float(max_distance, 100.0)),
                temperature=_intensity_to_temperature(intensity_value),
                fuel_remaining=_clamp(_safe_float(fuel, 1.0), 0.0, 1.0),
                spread_rate=_intensity_to_spread(intensity_value),
                metadata=dict(metadata) if metadata else {},
            )
            self._fires[fid] = fire
            self._update_zone_status(zone)
            self._refresh_stats()
            self._emit(
                ThermalEventKind.FIRE_IGNITED.value,
                zone_id=zone.zone_id,
                description=f"Fire '{fid}' ignited at {intensity_value} intensity.",
                data={"fire_id": fid, "intensity": intensity_value, "position": pos},
            )
            return True, "ignited", fire

    def get_fire(self, fire_id: str) -> Optional[FireFront]:
        """Return a fire front by id, or None if it does not exist."""
        return self._fires.get(str(fire_id).strip())

    def extinguish_fire(
        self,
        fire_id: str,
    ) -> Tuple[bool, str, Optional[FireFront]]:
        """Extinguish a fire front immediately."""
        with self._lock:
            fire = self._fires.get(str(fire_id).strip())
            if fire is None:
                return False, "not_found", None
            fire.status = FireStatus.EXTINGUISHED.value
            fire.fuel_remaining = 0.0
            fire.updated_at = _now()
            zone = self._zones.get(fire.zone_id)
            if zone is not None:
                self._update_zone_status(zone)
            self._refresh_stats()
            self._emit(
                ThermalEventKind.FIRE_EXTINGUISHED.value,
                zone_id=fire.zone_id,
                description=f"Fire '{fire.fire_id}' extinguished.",
                data={"fire_id": fire.fire_id},
            )
            return True, "extinguished", fire

    def list_fires(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[FireFront]:
        """List fire fronts, optionally filtered by status."""
        cap = max(1, _safe_int(limit, 100))
        result: List[FireFront] = []
        target = None
        if status is not None:
            coerced = _coerce_enum(FireStatus, status)
            target = coerced.value if coerced else str(status).strip().lower()
        for fire in self._fires.values():
            if target is not None and fire.status != target:
                continue
            result.append(fire)
            if len(result) >= cap:
                break
        return result

    def spread_fire(
        self,
        fire_id: str,
        direction: float,
        distance: float,
    ) -> Tuple[bool, str, Optional[FireFront]]:
        """Manually advance a fire front in a given direction."""
        with self._lock:
            fire = self._fires.get(str(fire_id).strip())
            if fire is None:
                return False, "not_found", None
            if fire.status == FireStatus.EXTINGUISHED.value:
                return False, "fire_extinguished", fire
            fire.direction = _safe_float(direction, fire.direction) % 360.0
            dist = max(0.0, _safe_float(distance, 0.0))
            rad = math.radians(fire.direction)
            x, y = fire.position
            fire.position = (x + math.cos(rad) * dist, y + math.sin(rad) * dist)
            fire.distance_traveled += dist
            if fire.distance_traveled >= fire.max_distance:
                fire.status = FireStatus.DYING.value
            elif fire.status == FireStatus.IGNITION.value:
                fire.status = FireStatus.SPREADING.value
            fire.updated_at = _now()
            # Heat the new position.
            zone = self._zones.get(fire.zone_id)
            if zone is not None:
                col, row = _world_to_cell(fire.position, zone.bounds, zone.grid_size)
                if 0 <= row < zone.grid_size and 0 <= col < zone.grid_size:
                    zone.cells[row][col] += fire.temperature * 0.05
                self._update_zone_status(zone)
            self._refresh_stats()
            self._emit(
                ThermalEventKind.FIRE_SPREAD.value,
                zone_id=fire.zone_id,
                description=f"Fire '{fire.fire_id}' spread {dist:.2f} units.",
                data={"fire_id": fire.fire_id, "direction": fire.direction, "distance": dist},
            )
            return True, "spread", fire

    def get_fire_intensity(self, fire_id: str) -> Tuple[bool, str, str]:
        """Return the intensity label of a fire front."""
        fire = self._fires.get(str(fire_id).strip())
        if fire is None:
            return False, "not_found", ""
        return True, "ok", fire.intensity

    def check_fire_spread(self, fire_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Return diagnostic information about a fire's spread potential."""
        fire = self._fires.get(str(fire_id).strip())
        if fire is None:
            return False, "not_found", {}
        zone = self._zones.get(fire.zone_id)
        zone_status = zone.status if zone else "unknown"
        # Estimate remaining travel budget.
        remaining_distance = max(0.0, fire.max_distance - fire.distance_traveled)
        # Estimate remaining fuel time at the current decay rate.
        decay = max(_EPSILON, self._config.fire_decay_rate)
        fuel_time = fire.fuel_remaining / decay
        # Determine whether the fire can still spread.
        can_spread = (
            fire.status != FireStatus.EXTINGUISHED.value
            and fire.fuel_remaining > 0.0
            and remaining_distance > 0.0
        )
        info = {
            "fire_id": fire.fire_id,
            "zone_id": fire.zone_id,
            "zone_status": zone_status,
            "status": fire.status,
            "intensity": fire.intensity,
            "fuel_remaining": fire.fuel_remaining,
            "remaining_distance": remaining_distance,
            "estimated_fuel_time": fuel_time,
            "can_spread": can_spread,
            "spread_rate": fire.spread_rate,
        }
        return True, "ok", info

    def get_fire_front(self, fire_id: str) -> Optional[FireFront]:
        """Return the full fire front record. Alias of get_fire."""
        return self.get_fire(fire_id)

    # ------------------------------------------------------------------
    # Material Thermal Properties
    # ------------------------------------------------------------------

    def register_material(
        self,
        material_id: str,
        name: str,
        conductivity: float,
        specific_heat: float,
        density: float,
        melting_point: float,
        boiling_point: float,
        ignition_point: float,
        flammability: float = 0.0,
        phase: str = PhaseState.SOLID.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[MaterialThermal]]:
        """Register a material with its thermal properties."""
        with self._lock:
            mid = str(material_id).strip()
            if not mid:
                return False, "material_id_required", None
            if mid in self._materials:
                return False, "already_exists", None
            if len(self._materials) >= self._config.max_materials:
                return False, "max_materials_reached", None
            phase_value = _coerce_enum(PhaseState, phase, PhaseState.SOLID).value
            material = MaterialThermal(
                material_id=mid,
                name=str(name),
                conductivity=max(0.0, _safe_float(conductivity, 0.0)),
                specific_heat=max(_EPSILON, _safe_float(specific_heat, 1000.0)),
                density=max(_EPSILON, _safe_float(density, 1000.0)),
                melting_point=_safe_float(melting_point, 0.0),
                boiling_point=_safe_float(boiling_point, 100.0),
                ignition_point=_safe_float(ignition_point, 9999.0),
                flammability=_clamp(_safe_float(flammability, 0.0), 0.0, 1.0),
                phase=phase_value,
                metadata=dict(metadata) if metadata else {},
            )
            # Ensure boiling point is at or above melting point.
            if material.boiling_point < material.melting_point:
                material.boiling_point = material.melting_point
            self._materials[mid] = material
            self._refresh_stats()
            self._emit(
                ThermalEventKind.MATERIAL_REGISTERED.value,
                description=f"Material '{material.name}' registered.",
                data={"material_id": mid, "phase": phase_value},
            )
            return True, "registered", material

    def get_material(self, material_id: str) -> Optional[MaterialThermal]:
        """Return a material by id, or None if it does not exist."""
        return self._materials.get(str(material_id).strip())

    def list_materials(self, limit: int = 100) -> List[MaterialThermal]:
        """List all registered materials up to the limit."""
        cap = max(1, _safe_int(limit, 100))
        return list(self._materials.values())[:cap]

    def remove_material(
        self,
        material_id: str,
    ) -> Tuple[bool, str, Optional[MaterialThermal]]:
        """Remove a material from the registry."""
        with self._lock:
            mid = str(material_id).strip()
            material = self._materials.pop(mid, None)
            if material is None:
