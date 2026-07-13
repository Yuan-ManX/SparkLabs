"""
SparkLabs Engine - Chemical Reaction System

Simulates chemical reactions for gameplay such as alchemy, crafting,
explosions, poison-making, and science puzzles. The system tracks
substances, reactions, catalysts, reaction vessels, and mixtures, and
steps them forward with realistic chemistry formulas: the Arrhenius
equation for reaction rates, Le Chatelier's principle for equilibrium
shifts, the ideal gas law for pressure/volume coupling, and Hess-style
heat-of-reaction summation for enthalpy. Vessels can be heated, sealed,
stirred, and pressurized; catalysts lower the effective activation
energy; and an AI helper layer predicts plausible products, optimizes
operating conditions, and assesses vessel stability.

Architecture:
  _ChemicalReactionSystem (Singleton)
    |-- Substance, Reaction, Mixture, Catalyst, ReactionVessel
    |-- ReactionStep, ReactionResult, ChemicalStats, ChemicalConfig
    |-- ChemicalSnapshot, ChemicalEvent
    |-- SubstanceState, ReactionType, VesselStatus, ChemicalEventKind

Core Capabilities:
  - register_substance / remove_substance / get_substance / list_substances
  - register_reaction / remove_reaction / get_reaction / list_reactions
  - register_catalyst / remove_catalyst / get_catalyst / list_catalysts
  - register_vessel / remove_vessel / get_vessel / list_vessels
  - create_mixture / get_mixture / remove_mixture / list_mixtures
  - trigger_reaction / check_reaction / compute_activation_energy
  - apply_catalyst / remove_catalyst_from_vessel
  - set_temperature / set_pressure / stir_vessel
  - check_equilibrium / compute_reaction_rate
  - ai_predict_products / ai_optimize_conditions / ai_assess_stability
  - get_visualization_data / get_reaction_graph
  - reset_vessel / list_events / tick
  - get_stats / get_snapshot / get_status / get_config / set_config

Usage:
    crs = get_chemical_reaction_system()
    ok, msg, substance = crs.register_substance("sub_water", "Water", "H2O", "liquid")
    ok, msg, reaction = crs.register_reaction("rxn_combustion", ["sub_fuel"], ["sub_ash"], -500.0)
    ok, msg, result = crs.trigger_reaction("vessel_001", "rxn_combustion")
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SUBSTANCES: int = 500
_MAX_REACTIONS: int = 300
_MAX_CATALYSTS: int = 200
_MAX_VESSELS: int = 200
_MAX_MIXTURES: int = 500
_MAX_REACTION_STEPS: int = 2000
_MAX_REACTION_RESULTS: int = 10000
_MAX_EVENTS: int = 10000
_MAX_VESSEL_CATALYSTS: int = 8


# ---------------------------------------------------------------------------
# Physical Constants
# ---------------------------------------------------------------------------

# Universal gas constant in J/(mol*K). Used by the Arrhenius equation and the
# ideal gas law (PV = nRT).
_GAS_CONSTANT: float = 8.314

# Smallest numeric delta considered non-zero. Guards against division-by-zero
# and floating-point churn in equilibrium and rate computations.
_EPSILON: float = 1e-9

# Absolute zero on the Kelvin scale. Temperature inputs are floored to this.
_ABSOLUTE_ZERO_K: float = 0.0

# Default pre-exponential factor (A) for the Arrhenius equation when a
# reaction does not carry an explicit frequency factor. Representative of a
# typical unimolecular gas-phase reaction in s^-1.
_DEFAULT_PRE_EXPONENTIAL: float = 1.0e10

# Standard ambient conditions used as defaults for new mixtures and vessels.
_STANDARD_TEMPERATURE_K: float = 298.15
_STANDARD_PRESSURE_KPA: float = 101.325
_STANDARD_PH: float = 7.0

# Conversion helpers between Celsius and Kelvin.
_CELSIUS_TO_KELVIN_OFFSET: float = 273.15

# Default catalyst efficiency and depletion rate when callers omit them.
_DEFAULT_CATALYST_EFFICIENCY: float = 0.5
_DEFAULT_CATALYST_DEPLETION: float = 0.0

# Risk thresholds used by explosion-risk and stability assessments.
_EXPLOSION_PRESSURE_KPA: float = 1500.0
_EXPLOSION_TEMPERATURE_K: float = 1200.0
_EXPLOSION_FLAMMABILITY_THRESHOLD: float = 0.6
_HIGH_RISK_SCORE: float = 0.75
_MODERATE_RISK_SCORE: float = 0.4

# Stirring defaults.
_DEFAULT_STIR_INTENSITY: float = 1.0
_MAX_STIR_INTENSITY: float = 5.0


# ---------------------------------------------------------------------------
# Module-Level Lock
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> float:
    """Return the current monotonic-ish wall-clock time in seconds."""
    return time.time()


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a numeric value into the inclusive range [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Parse a float, returning default on failure or non-finite input."""
    if value is None or value == "":
        return default
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(f) or math.isinf(f):
        return default
    return f


def _safe_int(value: Any, default: int = 0) -> int:
    """Parse an int, returning default on failure."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits max_size.

    Dicts preserve insertion order in Python 3.7+, so the first key is the
    oldest. This keeps bounded stores from growing without limit.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Recursively convert arbitrary values into JSON-serializable primitives.

    Enums are reduced to their ``.value``; tuples and sets become lists;
    dataclasses are expanded through ``_dataclass_to_dict``; objects exposing
    ``to_dict`` are delegated to that method. Everything else passes through.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return value.to_dict()
        except Exception:
            return str(value)
    return value


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to default.

    Accepts an existing enum member, the member's value, or a matching name.
    Returns ``default`` when no conversion is possible.
    """
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        pass
    try:
        return enum_cls[str(value).strip().upper()]
    except (KeyError, ValueError, AttributeError):
        return default


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    """Serialize a dataclass instance into a plain dict.

    The ``__dataclass_fields__`` attribute is checked BEFORE ``to_dict`` so
    that dataclasses which also expose ``to_dict`` do not recurse through
    their own serializer. Nested dataclasses, enums, tuples, and dicts are
    all normalized by ``_to_jsonable``.
    """
    if obj is None:
        return {}
    if hasattr(obj, "__dataclass_fields__"):
        out: Dict[str, Any] = {}
        for name in getattr(obj, "__dataclass_fields__", {}).keys():
            try:
                raw = getattr(obj, name)
            except Exception:
                continue
            out[name] = _to_jsonable(raw)
        return out
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return obj.to_dict()
        except Exception:
            return {}
    return {}


def _kelvin_from_input(temperature: Any) -> float:
    """Coerce a temperature input into a non-negative Kelvin value."""
    t = _safe_float(temperature, _STANDARD_TEMPERATURE_K)
    if t < _ABSOLUTE_ZERO_K:
        return _ABSOLUTE_ZERO_K
    return t


def _ph_from_h(h_concentration: float) -> float:
    """Compute pH from a molar hydrogen-ion concentration using pH = -log10[H+]."""
    h = _safe_float(h_concentration, 1.0e-7)
    if h <= _EPSILON:
        # Effectively no free hydrogen ions; treat as strongly basic.
        return 14.0
    try:
        return _clamp(-math.log10(h), 0.0, 14.0)
    except (ValueError, OverflowError):
        return _STANDARD_PH


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SubstanceState(str, Enum):
    """Physical phase of a substance."""
    SOLID = "solid"
    LIQUID = "liquid"
    GAS = "gas"
    PLASMA = "plasma"


class ReactionType(str, Enum):
    """Classification of a chemical reaction."""
    SYNTHESIS = "synthesis"
    DECOMPOSITION = "decomposition"
    SINGLE_DISPLACEMENT = "single_displacement"
    DOUBLE_DISPLACEMENT = "double_displacement"
    COMBUSTION = "combustion"
    REDOX = "redox"
    ACID_BASE = "acid_base"
    POLYMERIZATION = "polymerization"


class VesselStatus(str, Enum):
    """Operational status of a reaction vessel."""
    EMPTY = "empty"
    MIXING = "mixing"
    REACTING = "reacting"
    STABLE = "stable"
    SEALED = "sealed"
    RUPTURED = "ruptured"


class ChemicalEventKind(str, Enum):
    """Audit event types emitted by the chemical reaction system."""
    SUBSTANCE_REGISTERED = "substance_registered"
    SUBSTANCE_REMOVED = "substance_removed"
    REACTION_REGISTERED = "reaction_registered"
    REACTION_REMOVED = "reaction_removed"
    CATALYST_REGISTERED = "catalyst_registered"
    CATALYST_REMOVED = "catalyst_removed"
    VESSEL_REGISTERED = "vessel_registered"
    VESSEL_REMOVED = "vessel_removed"
    MIXTURE_CREATED = "mixture_created"
    MIXTURE_REMOVED = "mixture_removed"
    REACTION_TRIGGERED = "reaction_triggered"
    REACTION_COMPLETED = "reaction_completed"
    REACTION_FAILED = "reaction_failed"
    CATALYST_APPLIED = "catalyst_applied"
    CATALYST_REMOVED_FROM_VESSEL = "catalyst_removed_from_vessel"
    TEMPERATURE_SET = "temperature_set"
    PRESSURE_SET = "pressure_set"
    VESSEL_STIRRED = "vessel_stirred"
    VESSEL_RESET = "vessel_reset"
    VESSEL_RUPTURED = "vessel_ruptured"
    EQUILIBRIUM_SHIFTED = "equilibrium_shifted"
    EXPLOSION_RISK = "explosion_risk"
    CONFIG_UPDATED = "config_updated"
    TICK = "tick"
    AI_PREDICTION = "ai_prediction"
    AI_OPTIMIZATION = "ai_optimization"
    AI_ASSESSMENT = "ai_assessment"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Substance:
    """A chemical substance with physical and hazard properties.

    The ``properties`` dict may carry auxiliary fields such as
    ``formation_enthalpy`` (kJ/mol), ``boiling_point`` (C), and
    ``melting_point`` (C) used by the heat-of-reaction and phase helpers.
    """
    substance_id: str
    name: str
    formula: str = ""
    state: str = SubstanceState.LIQUID.value
    molecular_weight: float = 0.0
    density: float = 1.0
    toxicity: float = 0.0
    flammability: float = 0.0
    color: str = "#FFFFFF"
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    @property
    def is_solid(self) -> bool:
        return self.state == SubstanceState.SOLID.value

    @property
    def is_gas(self) -> bool:
        return self.state == SubstanceState.GAS.value

    @property
    def formation_enthalpy(self) -> float:
        """Return the standard formation enthalpy in kJ/mol, if known."""
        return _safe_float(self.properties.get("formation_enthalpy"), 0.0)

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["is_solid"] = self.is_solid
        d["is_gas"] = self.is_gas
        d["formation_enthalpy"] = self.formation_enthalpy
        return d


@dataclass
class Reaction:
    """A chemical reaction mapping reactants to products.

    ``enthalpy`` is the reaction enthalpy in kJ/mol; negative values are
    exothermic (release heat) and positive values are endothermic (absorb
    heat). ``activation_energy`` is in kJ/mol. ``equilibrium_constant`` is
    only meaningful when ``reversible`` is True.
    """
    reaction_id: str
    name: str
    reactant_ids: List[str] = field(default_factory=list)
    product_ids: List[str] = field(default_factory=list)
    enthalpy: float = 0.0
    activation_energy: float = 0.0
    reaction_type: str = ReactionType.SYNTHESIS.value
    reversible: bool = False
    equilibrium_constant: float = 1.0
    pre_exponential: float = _DEFAULT_PRE_EXPONENTIAL
    description: str = ""
    created_at: float = field(default_factory=_now)

    @property
    def is_exothermic(self) -> bool:
        return self.enthalpy < -_EPSILON

    @property
    def is_endothermic(self) -> bool:
        return self.enthalpy > _EPSILON

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["is_exothermic"] = self.is_exothermic
        d["is_endothermic"] = self.is_endothermic
        return d


@dataclass
class Mixture:
    """A homogeneous mixture of substances inside a vessel.

    ``proportions`` maps substance_id to a fractional share in [0, 1]. The
    mixture tracks its own temperature (K), pressure (kPa), pH, and volume
    (L) so that reaction checks can run without touching the vessel.
    """
    mixture_id: str
    vessel_id: str
    substance_ids: List[str] = field(default_factory=list)
    proportions: Dict[str, float] = field(default_factory=dict)
    temperature: float = _STANDARD_TEMPERATURE_K
    pressure: float = _STANDARD_PRESSURE_KPA
    ph: float = _STANDARD_PH
    volume: float = 1.0
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Catalyst:
    """A catalyst that lowers activation energy for a target reaction.

    ``efficiency`` in [0, 1] determines the fraction by which the effective
    activation energy is reduced. ``depletion_rate`` is the per-tick fraction
    of efficiency lost while the catalyst is active in a vessel.
    """
    catalyst_id: str
    name: str
    target_reaction_id: str = ""
    efficiency: float = _DEFAULT_CATALYST_EFFICIENCY
    depletion_rate: float = _DEFAULT_CATALYST_DEPLETION
    active: bool = True
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReactionVessel:
    """A container in which mixtures are prepared and reactions run.

    ``capacity`` and ``current_volume`` are in liters. ``temperature`` is in
    Kelvin and ``pressure`` in kPa. ``status`` reflects the current operating
    state; a ``RUPTURED`` vessel can no longer hold reactions safely.
    """
    vessel_id: str
    name: str
    capacity: float = 10.0
    current_volume: float = 0.0
    temperature: float = _STANDARD_TEMPERATURE_K
    pressure: float = _STANDARD_PRESSURE_KPA
    status: str = VesselStatus.EMPTY.value
    mixture_id: Optional[str] = None
    material: str = "glass"
    sealed: bool = False
    stir_intensity: float = 0.0
    created_at: float = field(default_factory=_now)

    @property
    def is_empty(self) -> bool:
        return self.current_volume <= _EPSILON and self.mixture_id is None

    @property
    def is_full(self) -> bool:
        return self.current_volume >= self.capacity - _EPSILON

    @property
    def fill_ratio(self) -> float:
        if self.capacity <= _EPSILON:
            return 0.0
        return _clamp(self.current_volume / self.capacity, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["is_empty"] = self.is_empty
        d["is_full"] = self.is_full
        d["fill_ratio"] = self.fill_ratio
        return d


@dataclass
class ReactionStep:
    """A single step within a multi-step reaction mechanism.

    ``step_number`` orders the steps within a reaction. ``energy_change`` is
    the enthalpy contribution (kJ/mol) of this particular step.
    """
    step_id: str
    reaction_id: str
    step_number: int = 1
    description: str = ""
    duration: float = 1.0
    energy_change: float = 0.0
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReactionResult:
    """The outcome of running a reaction in a vessel.

    ``yield_percentage`` is in [0, 100]. ``energy_released`` is in kJ and is
    negative for endothermic reactions (energy absorbed). ``byproducts`` is a
    list of substance IDs produced alongside the primary products.
    """
    result_id: str
    vessel_id: str
    reaction_id: str
    success: bool = False
    yield_percentage: float = 0.0
    byproducts: List[str] = field(default_factory=list)
    energy_released: float = 0.0
    duration: float = 0.0
    timestamp: float = field(default_factory=_now)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChemicalConfig:
    """Global tuning parameters for the chemical reaction system."""
    max_substances: int = _MAX_SUBSTANCES
    max_reactions: int = _MAX_REACTIONS
    max_catalysts: int = _MAX_CATALYSTS
    max_vessels: int = _MAX_VESSELS
    max_mixtures: int = _MAX_MIXTURES
    max_reaction_steps: int = _MAX_REACTION_STEPS
    max_reaction_results: int = _MAX_REACTION_RESULTS
    max_events: int = _MAX_EVENTS
    max_vessel_catalysts: int = _MAX_VESSEL_CATALYSTS
    default_temperature_k: float = _STANDARD_TEMPERATURE_K
    default_pressure_kpa: float = _STANDARD_PRESSURE_KPA
    default_ph: float = _STANDARD_PH
    ambient_temperature_k: float = _STANDARD_TEMPERATURE_K
    tick_rate_hz: float = 1.0
    enable_equilibrium_shifts: bool = True
    enable_explosion_risk: bool = True
    enable_ai_predictions: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChemicalStats:
    """Aggregate statistics gathered over the system lifetime."""
    total_substances: int = 0
    total_reactions: int = 0
    total_catalysts: int = 0
    total_vessels: int = 0
    total_mixtures: int = 0
    total_reaction_steps: int = 0
    total_reaction_results: int = 0
    total_reactions_triggered: int = 0
    total_successful_reactions: int = 0
    total_failed_reactions: int = 0
    total_vessel_ruptures: int = 0
    total_explosion_warnings: int = 0
    total_equilibrium_shifts: int = 0
    total_ai_predictions: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChemicalSnapshot:
    """Full state snapshot for serialization and debugging."""
    substances: List[Dict[str, Any]] = field(default_factory=list)
    reactions: List[Dict[str, Any]] = field(default_factory=list)
    catalysts: List[Dict[str, Any]] = field(default_factory=list)
    vessels: List[Dict[str, Any]] = field(default_factory=list)
    mixtures: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChemicalEvent:
    """An audit event emitted by the chemical reaction system."""
    event_id: str
    kind: str
    timestamp: float
    substance_id: str = ""
    reaction_id: str = ""
    catalyst_id: str = ""
    vessel_id: str = ""
    mixture_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Chemical Reaction System (Singleton)
# ---------------------------------------------------------------------------

class _ChemicalReactionSystem:
    """Simulates chemical reactions for the SparkLabs engine.

    The system is thread-safe and implemented as a singleton with
    double-checked locking. ``_init_lock`` guards singleton creation and
    seeding; ``_lock`` guards all mutating operations to keep the internal
    dictionaries consistent.

    The simulation model is intentionally lightweight but physically
    grounded: reaction rates follow the Arrhenius equation, equilibrium
    shifts follow Le Chatelier's principle, pressure and volume couple
    through the ideal gas law, and reaction enthalpy is the difference of
    formation enthalpies between products and reactants. Catalysts lower the
    effective activation energy, vessels can be sealed and pressurized, and
    an AI helper layer offers product prediction, condition optimization,
    and stability assessment.
    """

    _instance: Optional["_ChemicalReactionSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._seeded: bool = False
        self._substances: Dict[str, Substance] = {}
        self._reactions: Dict[str, Reaction] = {}
        self._catalysts: Dict[str, Catalyst] = {}
        self._vessels: Dict[str, ReactionVessel] = {}
        self._mixtures: Dict[str, Mixture] = {}
        self._reaction_steps: Dict[str, List[ReactionStep]] = {}
        self._results: Dict[str, ReactionResult] = {}
        self._vessel_results: Dict[str, List[str]] = {}
        self._vessel_catalysts: Dict[str, List[str]] = {}
        self._events: List[ChemicalEvent] = []
        self._config = ChemicalConfig()
        self._stats = ChemicalStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._global_time: float = 0.0

    @classmethod
    def get_instance(cls) -> "_ChemicalReactionSystem":
        """Return the shared singleton, creating it if needed.

        Uses double-checked locking so that after the first call the fast
        path acquires no lock.
        """
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
        """Populate the system with a canonical set of chemical data."""
        with self._lock:
            if self._seeded:
                return

            # ----------------------------------------------------------
            # Substances (8)
            # ----------------------------------------------------------
            substance_seeds: List[Tuple[str, str, str, str, float, float, float, float, str, Dict[str, Any]]] = [
                ("sub_water", "Water", "H2O", SubstanceState.LIQUID.value,
                 18.015, 1.0, 0.0, 0.0, "#88AAFF",
                 {"formation_enthalpy": -285.8, "boiling_point": 100.0, "melting_point": 0.0, "h_concentration": 1.0e-7}),
                ("sub_oxygen", "Oxygen", "O2", SubstanceState.GAS.value,
                 31.998, 0.001429, 0.0, 0.0, "#AAEEFF",
                 {"formation_enthalpy": 0.0, "boiling_point": -183.0, "melting_point": -218.0}),
                ("sub_hydrogen", "Hydrogen", "H2", SubstanceState.GAS.value,
                 2.016, 0.00009, 0.0, 1.0, "#EEEEFF",
                 {"formation_enthalpy": 0.0, "boiling_point": -253.0, "melting_point": -259.0}),
                ("sub_carbon", "Carbon", "C", SubstanceState.SOLID.value,
                 12.011, 2.267, 0.0, 0.5, "#333333",
                 {"formation_enthalpy": 0.0, "boiling_point": 4827.0, "melting_point": 3550.0}),
                ("sub_co2", "Carbon Dioxide", "CO2", SubstanceState.GAS.value,
                 44.009, 0.001977, 0.1, 0.0, "#DDDDDD",
                 {"formation_enthalpy": -393.5, "boiling_point": -78.5, "melting_point": -56.6}),
                ("sub_methane", "Methane", "CH4", SubstanceState.GAS.value,
                 16.043, 0.000717, 0.05, 0.9, "#BBEEBB",
                 {"formation_enthalpy": -74.8, "boiling_point": -161.5, "melting_point": -182.5}),
                ("sub_nacl", "Sodium Chloride", "NaCl", SubstanceState.SOLID.value,
                 58.44, 2.16, 0.1, 0.0, "#FFFFFF",
                 {"formation_enthalpy": -411.2, "boiling_point": 1413.0, "melting_point": 801.0}),
                ("sub_sodium", "Sodium", "Na", SubstanceState.SOLID.value,
                 22.99, 0.968, 0.6, 0.9, "#CCCCCC",
                 {"formation_enthalpy": 0.0, "boiling_point": 883.0, "melting_point": 97.8}),
                ("sub_ash", "Ash", "AshMix", SubstanceState.SOLID.value,
                 70.0, 0.5, 0.05, 0.0, "#666666",
                 {"formation_enthalpy": -50.0, "boiling_point": 9999.0, "melting_point": 900.0}),
            ]
            for (sid, name, formula, state, mw, dens, tox, flam, color, props) in substance_seeds:
                self._substances[sid] = Substance(
                    substance_id=sid, name=name, formula=formula, state=state,
                    molecular_weight=mw, density=dens, toxicity=tox,
                    flammability=flam, color=color, properties=dict(props),
                )

            # ----------------------------------------------------------
            # Reactions (6)
            # ----------------------------------------------------------
            reaction_seeds: List[Tuple[str, str, List[str], List[str], float, float, str, bool, float, str, float]] = [
                ("rxn_combustion_methane", "Combustion of Methane",
                 ["sub_methane", "sub_oxygen"], ["sub_co2", "sub_water"],
                 -890.4, 120.0, ReactionType.COMBUSTION.value, False, 1.0,
                 "Methane burns in oxygen to release heat, carbon dioxide, and water.",
                 _DEFAULT_PRE_EXPONENTIAL),
                ("rxn_water_synthesis", "Synthesis of Water",
                 ["sub_hydrogen", "sub_oxygen"], ["sub_water"],
                 -285.8, 200.0, ReactionType.SYNTHESIS.value, False, 1.0,
                 "Hydrogen and oxygen combine to form water, releasing substantial heat.",
                 _DEFAULT_PRE_EXPONENTIAL),
                ("rxn_water_electrolysis", "Electrolysis of Water",
                 ["sub_water"], ["sub_hydrogen", "sub_oxygen"],
                 285.8, 500.0, ReactionType.DECOMPOSITION.value, False, 1.0,
                 "Water is split into hydrogen and oxygen, absorbing energy.",
                 _DEFAULT_PRE_EXPONENTIAL * 0.1),
                ("rxn_combustion_carbon", "Combustion of Carbon",
                 ["sub_carbon", "sub_oxygen"], ["sub_co2"],
                 -393.5, 150.0, ReactionType.COMBUSTION.value, False, 1.0,
                 "Solid carbon burns in oxygen to produce carbon dioxide.",
                 _DEFAULT_PRE_EXPONENTIAL),
                ("rxn_sodium_water", "Sodium in Water",
                 ["sub_sodium", "sub_water"], ["sub_hydrogen"],
                 -184.0, 80.0, ReactionType.SINGLE_DISPLACEMENT.value, False, 1.0,
                 "Sodium displaces hydrogen from water in a vigorous reaction.",
                 _DEFAULT_PRE_EXPONENTIAL),
                ("rxn_reversible_co2", "Reversible CO2 Decomposition",
                 ["sub_co2"], ["sub_carbon", "sub_oxygen"],
                 393.5, 300.0, ReactionType.DECOMPOSITION.value, True, 0.001,
                 "Carbon dioxide can decompose into carbon and oxygen; heavily reactant-favored.",
                 _DEFAULT_PRE_EXPONENTIAL * 0.01),
            ]
            for (rid, name, reactants, products, enthalpy, ea, rtype, rev, keq, desc, a_factor) in reaction_seeds:
                self._reactions[rid] = Reaction(
                    reaction_id=rid, name=name, reactant_ids=list(reactants),
                    product_ids=list(products), enthalpy=enthalpy,
                    activation_energy=ea, reaction_type=rtype, reversible=rev,
                    equilibrium_constant=keq, description=desc,
                    pre_exponential=a_factor,
                )

            # ----------------------------------------------------------
            # Reaction Steps (seed a few multi-step mechanisms)
            # ----------------------------------------------------------
            step_defs: List[Tuple[str, str, int, str, float, float]] = [
                ("step_cm_1", "rxn_combustion_methane", 1, "Methane activation", 0.5, -100.0),
                ("step_cm_2", "rxn_combustion_methane", 2, "Oxygen bond cleavage", 0.4, -200.0),
                ("step_cm_3", "rxn_combustion_methane", 3, "Product formation and heat release", 0.6, -590.4),
                ("step_we_1", "rxn_water_electrolysis", 1, "Apply electric potential", 2.0, 150.0),
                ("step_we_2", "rxn_water_electrolysis", 2, "Split water molecule", 3.0, 135.8),
                ("step_sw_1", "rxn_sodium_water", 1, "Sodium surface attack", 0.3, -90.0),
                ("step_sw_2", "rxn_sodium_water", 2, "Hydrogen liberation", 0.4, -94.0),
            ]
            for (step_id, rid, num, desc, dur, energy) in step_defs:
                step = ReactionStep(
                    step_id=step_id, reaction_id=rid, step_number=num,
                    description=desc, duration=dur, energy_change=energy,
                )
                self._reaction_steps.setdefault(rid, []).append(step)

            # ----------------------------------------------------------
            # Catalysts (3)
            # ----------------------------------------------------------
            catalyst_seeds: List[Tuple[str, str, str, float, float]] = [
                ("cat_platinum", "Platinum Catalyst", "rxn_water_synthesis", 0.85, 0.001),
                ("cat_iron_oxide", "Iron Oxide Catalyst", "rxn_combustion_methane", 0.6, 0.002),
                ("cat_nickel", "Nickel Catalyst", "rxn_sodium_water", 0.7, 0.0015),
            ]
            for (cid, name, target, eff, dep) in catalyst_seeds:
                self._catalysts[cid] = Catalyst(
                    catalyst_id=cid, name=name, target_reaction_id=target,
                    efficiency=eff, depletion_rate=dep, active=True,
                )

            # ----------------------------------------------------------
            # Reaction Vessels (3)
            # ----------------------------------------------------------
            vessel_seeds: List[Tuple[str, str, float, str, float, float, str]] = [
                ("vessel_001", "Lab Beaker", 10.0, "glass",
                 _STANDARD_TEMPERATURE_K, _STANDARD_PRESSURE_KPA, VesselStatus.EMPTY.value),
                ("vessel_002", "Combustion Chamber", 100.0, "steel",
                 _STANDARD_TEMPERATURE_K, _STANDARD_PRESSURE_KPA, VesselStatus.EMPTY.value),
                ("vessel_003", "Mixing Vat", 50.0, "ceramic",
                 _STANDARD_TEMPERATURE_K, _STANDARD_PRESSURE_KPA, VesselStatus.EMPTY.value),
            ]
            for (vid, name, cap, material, temp, pres, status) in vessel_seeds:
                self._vessels[vid] = ReactionVessel(
                    vessel_id=vid, name=name, capacity=cap, material=material,
                    temperature=temp, pressure=pres, status=status,
                )

            # ----------------------------------------------------------
            # Mixtures (4)
            # ----------------------------------------------------------
            mixture_seeds: List[Tuple[str, str, List[str], Dict[str, float], float, float, float, float]] = [
                ("mix_water_sample", "vessel_001", ["sub_water"],
                 {"sub_water": 1.0}, _STANDARD_TEMPERATURE_K, _STANDARD_PRESSURE_KPA, _STANDARD_PH, 5.0),
                ("mix_fuel_air", "vessel_002", ["sub_methane", "sub_oxygen"],
                 {"sub_methane": 0.5, "sub_oxygen": 0.5}, 350.0, 150.0, 7.0, 40.0),
                ("mix_carbon_pile", "vessel_003", ["sub_carbon", "sub_oxygen"],
                 {"sub_carbon": 0.7, "sub_oxygen": 0.3}, 400.0, _STANDARD_PRESSURE_KPA, 7.0, 25.0),
                ("mix_acidic_brew", "vessel_001", ["sub_water", "sub_co2"],
                 {"sub_water": 0.9, "sub_co2": 0.1}, 320.0, 110.0, 5.5, 8.0),
            ]
            for (mid, vid, subs, props, temp, pres, ph, vol) in mixture_seeds:
                mixture = Mixture(
                    mixture_id=mid, vessel_id=vid, substance_ids=list(subs),
                    proportions=dict(props), temperature=temp, pressure=pres,
                    ph=ph, volume=vol,
                )
                self._mixtures[mid] = mixture
                vessel = self._vessels.get(vid)
                if vessel is not None:
                    vessel.mixture_id = mid
                    vessel.current_volume = vol
                    vessel.temperature = temp
                    vessel.pressure = pres
                    vessel.status = VesselStatus.STABLE.value

            # Refresh aggregate stats to reflect the seed data.
            self._refresh_stats()
            self._seeded = True

            # Emit a single synthetic event marking the seed completion.
            self._emit(
                ChemicalEventKind.TICK.value,
                description="Chemical reaction system seeded",
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        kind: str,
        substance_id: str = "",
        reaction_id: str = "",
        catalyst_id: str = "",
        vessel_id: str = "",
        mixture_id: str = "",
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> ChemicalEvent:
        """Record an audit event and enforce the bounded-event limit."""
        event = ChemicalEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            substance_id=substance_id,
            reaction_id=reaction_id,
            catalyst_id=catalyst_id,
            vessel_id=vessel_id,
            mixture_id=mixture_id,
            description=description,
            details=details or {},
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, self._config.max_events)
        return event

    def _refresh_stats(self) -> None:
        """Recompute the aggregate statistics from the current stores."""
        self._stats.total_substances = len(self._substances)
        self._stats.total_reactions = len(self._reactions)
        self._stats.total_catalysts = len(self._catalysts)
        self._stats.total_vessels = len(self._vessels)
        self._stats.total_mixtures = len(self._mixtures)
        self._stats.total_reaction_steps = sum(len(v) for v in self._reaction_steps.values())
        self._stats.total_reaction_results = len(self._results)

    def _substance_exists(self, substance_id: str) -> bool:
        return substance_id in self._substances

    def _reaction_exists(self, reaction_id: str) -> bool:
        return reaction_id in self._reactions

    def _catalyst_exists(self, catalyst_id: str) -> bool:
        return catalyst_id in self._catalysts

    def _vessel_exists(self, vessel_id: str) -> bool:
        return vessel_id in self._vessels

    def _mixture_exists(self, mixture_id: str) -> bool:
        return mixture_id in self._mixtures

    def _compute_heat_of_reaction(self, reaction: Reaction) -> float:
        """Compute ΔH = Σ(products formation enthalpy) - Σ(reactants formation enthalpy).

        Falls back to the reaction's stored enthalpy when substance
        formation enthalpies are unavailable.
        """
        product_sum = 0.0
        reactant_sum = 0.0
        have_data = False
        for sid in reaction.product_ids:
            sub = self._substances.get(sid)
            if sub is not None:
                product_sum += sub.formation_enthalpy
                have_data = True
        for sid in reaction.reactant_ids:
            sub = self._substances.get(sid)
            if sub is not None:
                reactant_sum += sub.formation_enthalpy
                have_data = True
        if not have_data:
            return reaction.enthalpy
        return product_sum - reactant_sum

    def _effective_activation_energy(
        self, reaction: Reaction, catalyst: Optional[Catalyst] = None
    ) -> float:
        """Return the activation energy after any catalyst reduction.

        A catalyst lowers the effective activation energy by its efficiency
        fraction, but never below zero.
        """
        ea = max(0.0, reaction.activation_energy)
        if catalyst is not None and catalyst.active:
            reduction = _clamp(catalyst.efficiency, 0.0, 1.0) * ea
            ea = max(0.0, ea - reduction)
        return ea

    def _arrhenius_rate(
        self, reaction: Reaction, temperature: float, catalyst: Optional[Catalyst] = None
    ) -> float:
        """Compute the rate constant k = A * exp(-Ea / (R*T))."""
        t = max(temperature, _EPSILON)
        ea = self._effective_activation_energy(reaction, catalyst)
        # Activation energy is in kJ/mol; convert to J/mol for R*T pairing.
        ea_joules = ea * 1000.0
        exponent = -ea_joules / (_GAS_CONSTANT * t)
        # Guard against numeric overflow for very low temperatures.
        if exponent < -700.0:
            return 0.0
        if exponent > 700.0:
            exponent = 700.0
        try:
            return reaction.pre_exponential * math.exp(exponent)
        except (ValueError, OverflowError):
            return 0.0

    def _ideal_gas_pressure(self, n_moles: float, volume: float, temperature: float) -> float:
        """Compute pressure in kPa from PV = nRT."""
        v = max(volume, _EPSILON)
        t = max(temperature, _EPSILON)
        # P (Pa) = nRT / V; convert Pa -> kPa by dividing by 1000.
        p_pa = (n_moles * _GAS_CONSTANT * t) / v
        return p_pa / 1000.0

    def _ideal_gas_moles(self, pressure_kpa: float, volume: float, temperature: float) -> float:
        """Compute moles n from PV = nRT (pressure in kPa)."""
        p_pa = max(pressure_kpa, _EPSILON) * 1000.0
        v = max(volume, _EPSILON)
        t = max(temperature, _EPSILON)
        return (p_pa * v) / (_GAS_CONSTANT * t)

    def _mixture_flammability(self, mixture: Optional[Mixture]) -> float:
        """Return the weighted flammability of a mixture in [0, 1]."""
        if mixture is None:
            return 0.0
        total_weight = 0.0
        weighted = 0.0
        for sid in mixture.substance_ids:
            sub = self._substances.get(sid)
            if sub is None:
                continue
            share = _safe_float(mixture.proportions.get(sid), 0.0)
            if share <= 0.0:
                continue
            weighted += _clamp(sub.flammability, 0.0, 1.0) * share
            total_weight += share
        if total_weight <= _EPSILON:
            return 0.0
        return _clamp(weighted / total_weight, 0.0, 1.0)

    def _mixture_toxicity(self, mixture: Optional[Mixture]) -> float:
        """Return the weighted toxicity of a mixture in [0, 1]."""
        if mixture is None:
            return 0.0
        total_weight = 0.0
        weighted = 0.0
        for sid in mixture.substance_ids:
            sub = self._substances.get(sid)
            if sub is None:
                continue
            share = _safe_float(mixture.proportions.get(sid), 0.0)
            if share <= 0.0:
                continue
            weighted += _clamp(sub.toxicity, 0.0, 1.0) * share
            total_weight += share
        if total_weight <= _EPSILON:
            return 0.0
        return _clamp(weighted / total_weight, 0.0, 1.0)

    def _vessel_catalyst_for(self, vessel_id: str, reaction_id: str) -> Optional[Catalyst]:
        """Return the first active catalyst in a vessel matching a reaction."""
        for cid in self._vessel_catalysts.get(vessel_id, []):
            cat = self._catalysts.get(cid)
            if cat is not None and cat.active and cat.target_reaction_id == reaction_id:
                return cat
        return None

    def _check_reactants_available(self, mixture: Optional[Mixture], reaction: Reaction) -> bool:
        """Return True when every reactant is present in the mixture."""
        if mixture is None:
            return False
        present = set(mixture.substance_ids)
        for rid in reaction.reactant_ids:
            if rid not in present:
                return False
        return True

    def _compute_yield(
        self,
        reaction: Reaction,
        temperature: float,
        pressure: float,
        catalyst: Optional[Catalyst],
    ) -> float:
        """Estimate reaction yield percentage in [0, 100].

        The yield rises with temperature (faster kinetics) and with catalyst
        efficiency, but is penalized when the temperature strays far from a
        nominal optimum and when pressure is far from ideal for gas-phase
        reactions.
        """
        rate = self._arrhenius_rate(reaction, temperature, catalyst)
        # Normalize the rate against the pre-exponential factor so the
        # temperature factor lands in a sensible [0, 1] band.
        rate_factor = _clamp(rate / max(reaction.pre_exponential, _EPSILON), 0.0, 1.0)
        temp_factor = _clamp(
            1.0 - abs(temperature - _STANDARD_TEMPERATURE_K) / (2.0 * _STANDARD_TEMPERATURE_K),
            0.0, 1.0,
        )
        pressure_factor = _clamp(
            1.0 - abs(pressure - _STANDARD_PRESSURE_KPA) / (5.0 * _STANDARD_PRESSURE_KPA),
            0.0, 1.0,
        )
        cat_bonus = 0.0
        if catalyst is not None and catalyst.active:
            cat_bonus = _clamp(catalyst.efficiency, 0.0, 1.0) * 0.2
        # Weighted blend favouring the rate and temperature factors.
        blended = (
            0.5 * rate_factor
            + 0.25 * temp_factor
            + 0.15 * pressure_factor
            + 0.1 * cat_bonus * 5.0
        )
        blended = _clamp(blended, 0.0, 1.0)
        return blended * 100.0

    def _apply_le_chatelier(
        self, reaction: Reaction, mixture: Mixture, temperature_delta: float, pressure_delta: float
    ) -> Dict[str, Any]:
        """Predict the equilibrium shift under Le Chatelier's principle.

        For an exothermic reaction, raising temperature shifts equilibrium
        toward reactants; for an endothermic reaction, toward products. For a
        reaction where gases appear, raising pressure shifts equilibrium
        toward the side with fewer gaseous moles.
        """
        direction = "none"
        reason = "no perturbation"
        if not reaction.reversible:
            return {
                "applicable": False,
                "direction": "none",
                "reason": "reaction is not reversible",
                "temperature_shift": temperature_delta,
                "pressure_shift": pressure_delta,
            }

        if abs(temperature_delta) > _EPSILON:
            if temperature_delta > 0:
                # Heat is a product of exothermic reactions.
                if reaction.is_exothermic:
                    direction = "reactants"
                    reason = "temperature increased; exothermic equilibrium shifts toward reactants"
                else:
                    direction = "products"
                    reason = "temperature increased; endothermic equilibrium shifts toward products"
            else:
                if reaction.is_exothermic:
                    direction = "products"
                    reason = "temperature decreased; exothermic equilibrium shifts toward products"
                else:
                    direction = "reactants"
                    reason = "temperature decreased; endothermic equilibrium shifts toward reactants"

        if abs(pressure_delta) > _EPSILON:
            gaseous_reactants = 0
            gaseous_products = 0
            for sid in reaction.reactant_ids:
                sub = self._substances.get(sid)
                if sub is not None and sub.is_gas:
                    gaseous_reactants += 1
            for sid in reaction.product_ids:
                sub = self._substances.get(sid)
                if sub is not None and sub.is_gas:
                    gaseous_products += 1
            if gaseous_reactants != gaseous_products:
                if pressure_delta > 0:
                    side = "products" if gaseous_products < gaseous_reactants else "reactants"
                else:
                    side = "reactants" if gaseous_products < gaseous_reactants else "products"
                if direction == "none":
                    direction = side
                    reason = f"pressure change favors the side with fewer gas moles ({side})"
                else:
                    reason += f"; pressure change also favors {side}"

        return {
            "applicable": True,
            "direction": direction,
            "reason": reason,
            "temperature_shift": temperature_delta,
            "pressure_shift": pressure_delta,
            "equilibrium_constant": reaction.equilibrium_constant,
        }

    def _vessel_summary(self, vessel: ReactionVessel) -> Dict[str, Any]:
        """Build a compact summary dict for a vessel and its mixture."""
        mixture = self._mixtures.get(vessel.mixture_id) if vessel.mixture_id else None
        catalyst_ids = list(self._vessel_catalysts.get(vessel.vessel_id, []))
        return {
            "vessel_id": vessel.vessel_id,
            "name": vessel.name,
            "status": vessel.status,
            "temperature_k": vessel.temperature,
            "pressure_kpa": vessel.pressure,
            "current_volume": vessel.current_volume,
            "capacity": vessel.capacity,
            "fill_ratio": vessel.fill_ratio,
            "material": vessel.material,
            "sealed": vessel.sealed,
            "mixture_id": vessel.mixture_id,
            "mixture_substances": list(mixture.substance_ids) if mixture else [],
            "mixture_ph": mixture.ph if mixture else _STANDARD_PH,
            "flammability": self._mixture_flammability(mixture),
            "toxicity": self._mixture_toxicity(mixture),
            "catalyst_ids": catalyst_ids,
        }

    # ------------------------------------------------------------------
    # Substance Management
    # ------------------------------------------------------------------

    def register_substance(
        self,
        substance_id: str,
        name: str,
        formula: str = "",
        state: str = SubstanceState.LIQUID.value,
        molecular_weight: Optional[float] = None,
        density: Optional[float] = None,
        toxicity: Optional[float] = None,
        flammability: Optional[float] = None,
        color: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Substance]]:
        """Register a new chemical substance.

        Returns ``(ok, message, substance)``. Fails if the id is empty or
        already in use, or if the substance cap has been reached.
        """
        if not substance_id or not isinstance(substance_id, str):
            return False, "invalid_substance_id", None
        with self._lock:
            if substance_id in self._substances:
                return False, "substance_already_exists", self._substances[substance_id]
            if len(self._substances) >= self._config.max_substances:
                return False, "max_substances_reached", None
            state_value = _coerce_enum(
                SubstanceState, state, SubstanceState.LIQUID
            ).value
            substance = Substance(
                substance_id=substance_id,
                name=name or substance_id,
                formula=formula or "",
                state=state_value,
                molecular_weight=_safe_float(molecular_weight, 0.0),
                density=_safe_float(density, 1.0),
                toxicity=_clamp(_safe_float(toxicity, 0.0), 0.0, 1.0),
                flammability=_clamp(_safe_float(flammability, 0.0), 0.0, 1.0),
                color=color or "#FFFFFF",
                properties=dict(properties) if properties else {},
            )
            self._substances[substance_id] = substance
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.SUBSTANCE_REGISTERED.value,
                substance_id=substance_id,
                description=f"Registered substance {name}",
            )
            return True, "registered", substance

    def get_substance(self, substance_id: str) -> Optional[Substance]:
        """Return the substance with the given id, or None."""
        if not substance_id:
            return None
        with self._lock:
            return self._substances.get(substance_id)

    def remove_substance(self, substance_id: str) -> Tuple[bool, str, Optional[Substance]]:
        """Remove a substance. Returns ``(ok, message, removed_substance)``."""
        if not substance_id:
            return False, "invalid_substance_id", None
        with self._lock:
            substance = self._substances.pop(substance_id, None)
            if substance is None:
                return False, "substance_not_found", None
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.SUBSTANCE_REMOVED.value,
                substance_id=substance_id,
                description=f"Removed substance {substance.name}",
            )
            return True, "removed", substance

    def list_substances(
        self, state: Optional[str] = None, limit: int = 0
    ) -> List[Substance]:
        """List substances, optionally filtered by physical state."""
        with self._lock:
            items = list(self._substances.values())
            if state is not None and state != "":
                state_value = _coerce_enum(SubstanceState, state, None)
                target = state_value.value if state_value is not None else str(state)
                items = [s for s in items if s.state == target]
            if limit and limit > 0:
                items = items[:limit]
            return items

    # ------------------------------------------------------------------
    # Reaction Management
    # ------------------------------------------------------------------

    def register_reaction(
        self,
        reaction_id: str,
        name: str,
        reactant_ids: List[str],
        product_ids: List[str],
        enthalpy: float,
        activation_energy: float = 0.0,
        reaction_type: str = ReactionType.SYNTHESIS.value,
        reversible: bool = False,
        equilibrium_constant: float = 1.0,
    ) -> Tuple[bool, str, Optional[Reaction]]:
        """Register a new chemical reaction.

        ``enthalpy`` is in kJ/mol (negative = exothermic). ``activation_energy``
        is in kJ/mol. Returns ``(ok, message, reaction)``.
        """
        if not reaction_id or not isinstance(reaction_id, str):
            return False, "invalid_reaction_id", None
        if not isinstance(reactant_ids, list) or not isinstance(product_ids, list):
            return False, "invalid_reactant_or_product_list", None
        if not reactant_ids:
            return False, "no_reactants", None
        with self._lock:
            if reaction_id in self._reactions:
                return False, "reaction_already_exists", self._reactions[reaction_id]
            if len(self._reactions) >= self._config.max_reactions:
                return False, "max_reactions_reached", None
            rtype_value = _coerce_enum(
                ReactionType, reaction_type, ReactionType.SYNTHESIS
            ).value
            reaction = Reaction(
                reaction_id=reaction_id,
                name=name or reaction_id,
                reactant_ids=list(reactant_ids),
                product_ids=list(product_ids),
                enthalpy=_safe_float(enthalpy, 0.0),
                activation_energy=max(0.0, _safe_float(activation_energy, 0.0)),
                reaction_type=rtype_value,
                reversible=bool(reversible),
                equilibrium_constant=_safe_float(equilibrium_constant, 1.0),
                pre_exponential=_DEFAULT_PRE_EXPONENTIAL,
            )
            self._reactions[reaction_id] = reaction
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.REACTION_REGISTERED.value,
                reaction_id=reaction_id,
                description=f"Registered reaction {name}",
            )
            return True, "registered", reaction

    def get_reaction(self, reaction_id: str) -> Optional[Reaction]:
        """Return the reaction with the given id, or None."""
        if not reaction_id:
            return None
        with self._lock:
            return self._reactions.get(reaction_id)

    def remove_reaction(self, reaction_id: str) -> Tuple[bool, str, Optional[Reaction]]:
        """Remove a reaction and its step definitions."""
        if not reaction_id:
            return False, "invalid_reaction_id", None
        with self._lock:
            reaction = self._reactions.pop(reaction_id, None)
            if reaction is None:
                return False, "reaction_not_found", None
            self._reaction_steps.pop(reaction_id, None)
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.REACTION_REMOVED.value,
                reaction_id=reaction_id,
                description=f"Removed reaction {reaction.name}",
            )
            return True, "removed", reaction

    def list_reactions(
        self, reaction_type: Optional[str] = None, limit: int = 0
    ) -> List[Reaction]:
        """List reactions, optionally filtered by reaction type."""
        with self._lock:
            items = list(self._reactions.values())
            if reaction_type is not None and reaction_type != "":
                rtype_value = _coerce_enum(ReactionType, reaction_type, None)
                target = rtype_value.value if rtype_value is not None else str(reaction_type)
                items = [r for r in items if r.reaction_type == target]
            if limit and limit > 0:
                items = items[:limit]
            return items

    def list_reactions_for_substance(self, substance_id: str) -> List[Reaction]:
        """Return every reaction that consumes or produces the given substance.

        Useful for gameplay UIs that show what a player can do with a
        particular ingredient they have on hand.
        """
        if not substance_id:
            return []
        with self._lock:
            matches: List[Reaction] = []
            for reaction in self._reactions.values():
                if substance_id in reaction.reactant_ids or substance_id in reaction.product_ids:
                    matches.append(reaction)
            return matches

    def add_reaction_step(
        self,
        reaction_id: str,
        step_number: int,
        description: str = "",
        duration: float = 1.0,
        energy_change: float = 0.0,
    ) -> Tuple[bool, str, Optional[ReactionStep]]:
        """Append a step to a reaction's multi-step mechanism.

        Steps are ordered by ``step_number``. Returns the created step on
        success. Fails if the reaction does not exist or the step cap for the
        reaction has been reached.
        """
        if not reaction_id:
            return False, "invalid_reaction_id", None
        with self._lock:
            reaction = self._reactions.get(reaction_id)
            if reaction is None:
                return False, "reaction_not_found", None
            steps = self._reaction_steps.setdefault(reaction_id, [])
            if len(steps) >= self._config.max_reaction_steps:
                return False, "max_reaction_steps_reached", None
            step = ReactionStep(
                step_id=_new_id("step"),
                reaction_id=reaction_id,
                step_number=max(1, _safe_int(step_number, len(steps) + 1)),
                description=description or "",
                duration=max(0.0, _safe_float(duration, 1.0)),
                energy_change=_safe_float(energy_change, 0.0),
            )
            steps.append(step)
            steps.sort(key=lambda s: s.step_number)
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.REACTION_REGISTERED.value,
                reaction_id=reaction_id,
                description=f"Added step {step.step_number} to reaction {reaction.name}",
            )
            return True, "added", step

    # ------------------------------------------------------------------
    # Catalyst Management
    # ------------------------------------------------------------------

    def register_catalyst(
        self,
        catalyst_id: str,
        name: str,
        target_reaction_id: str,
        efficiency: float = _DEFAULT_CATALYST_EFFICIENCY,
        depletion_rate: float = _DEFAULT_CATALYST_DEPLETION,
    ) -> Tuple[bool, str, Optional[Catalyst]]:
        """Register a new catalyst targeting a specific reaction."""
        if not catalyst_id or not isinstance(catalyst_id, str):
            return False, "invalid_catalyst_id", None
        with self._lock:
            if catalyst_id in self._catalysts:
                return False, "catalyst_already_exists", self._catalysts[catalyst_id]
            if len(self._catalysts) >= self._config.max_catalysts:
                return False, "max_catalysts_reached", None
            catalyst = Catalyst(
                catalyst_id=catalyst_id,
                name=name or catalyst_id,
                target_reaction_id=target_reaction_id,
                efficiency=_clamp(_safe_float(efficiency, _DEFAULT_CATALYST_EFFICIENCY), 0.0, 1.0),
                depletion_rate=_clamp(_safe_float(depletion_rate, _DEFAULT_CATALYST_DEPLETION), 0.0, 1.0),
                active=True,
            )
            self._catalysts[catalyst_id] = catalyst
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.CATALYST_REGISTERED.value,
                catalyst_id=catalyst_id,
                reaction_id=target_reaction_id,
                description=f"Registered catalyst {name}",
            )
            return True, "registered", catalyst

    def get_catalyst(self, catalyst_id: str) -> Optional[Catalyst]:
        """Return the catalyst with the given id, or None."""
        if not catalyst_id:
            return None
        with self._lock:
            return self._catalysts.get(catalyst_id)

    def remove_catalyst(self, catalyst_id: str) -> Tuple[bool, str, Optional[Catalyst]]:
        """Remove a catalyst globally and from every vessel that holds it."""
        if not catalyst_id:
            return False, "invalid_catalyst_id", None
        with self._lock:
            catalyst = self._catalysts.pop(catalyst_id, None)
            if catalyst is None:
                return False, "catalyst_not_found", None
            # Detach the catalyst from any vessel that currently holds it.
            for vid, cids in self._vessel_catalysts.items():
                if catalyst_id in cids:
                    cids.remove(catalyst_id)
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.CATALYST_REMOVED.value,
                catalyst_id=catalyst_id,
                description=f"Removed catalyst {catalyst.name}",
            )
            return True, "removed", catalyst

    def list_catalysts(
        self, active: Optional[bool] = None, limit: int = 0
    ) -> List[Catalyst]:
        """List catalysts, optionally filtered by active state."""
        with self._lock:
            items = list(self._catalysts.values())
            if active is not None:
                items = [c for c in items if c.active == active]
            if limit and limit > 0:
                items = items[:limit]
            return items

    # ------------------------------------------------------------------
    # Vessel Management
    # ------------------------------------------------------------------

    def register_vessel(
        self,
        vessel_id: str,
        name: str,
        capacity: float,
        material: str = "glass",
    ) -> Tuple[bool, str, Optional[ReactionVessel]]:
        """Register a new reaction vessel."""
        if not vessel_id or not isinstance(vessel_id, str):
            return False, "invalid_vessel_id", None
        with self._lock:
            if vessel_id in self._vessels:
                return False, "vessel_already_exists", self._vessels[vessel_id]
            if len(self._vessels) >= self._config.max_vessels:
                return False, "max_vessels_reached", None
            vessel = ReactionVessel(
                vessel_id=vessel_id,
                name=name or vessel_id,
                capacity=max(0.0, _safe_float(capacity, 10.0)),
                material=material or "glass",
                temperature=self._config.default_temperature_k,
                pressure=self._config.default_pressure_kpa,
                status=VesselStatus.EMPTY.value,
            )
            self._vessels[vessel_id] = vessel
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.VESSEL_REGISTERED.value,
                vessel_id=vessel_id,
                description=f"Registered vessel {name}",
            )
            return True, "registered", vessel

    def get_vessel(self, vessel_id: str) -> Optional[ReactionVessel]:
        """Return the vessel with the given id, or None."""
        if not vessel_id:
            return None
        with self._lock:
            return self._vessels.get(vessel_id)

    def remove_vessel(self, vessel_id: str) -> Tuple[bool, str, Optional[ReactionVessel]]:
        """Remove a vessel and detach its mixture and catalysts."""
        if not vessel_id:
            return False, "invalid_vessel_id", None
        with self._lock:
            vessel = self._vessels.pop(vessel_id, None)
            if vessel is None:
                return False, "vessel_not_found", None
            # Remove the vessel's mixture if it still exists.
            if vessel.mixture_id and vessel.mixture_id in self._mixtures:
                self._mixtures.pop(vessel.mixture_id, None)
            self._vessel_catalysts.pop(vessel_id, None)
            self._vessel_results.pop(vessel_id, None)
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.VESSEL_REMOVED.value,
                vessel_id=vessel_id,
                description=f"Removed vessel {vessel.name}",
            )
            return True, "removed", vessel

    def list_vessels(
        self, status: Optional[str] = None, limit: int = 0
    ) -> List[ReactionVessel]:
        """List vessels, optionally filtered by status."""
        with self._lock:
            items = list(self._vessels.values())
            if status is not None and status != "":
                status_value = _coerce_enum(VesselStatus, status, None)
                target = status_value.value if status_value is not None else str(status)
                items = [v for v in items if v.status == target]
            if limit and limit > 0:
                items = items[:limit]
            return items

    # ------------------------------------------------------------------
    # Mixture Management
    # ------------------------------------------------------------------

    def create_mixture(
        self,
        mixture_id: str,
        vessel_id: str,
        substance_ids: List[str],
        proportions: Optional[Dict[str, float]] = None,
        temperature: Optional[float] = None,
        pressure: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[Mixture]]:
        """Create a mixture of substances inside a vessel.

        ``proportions`` maps substance_id to a fractional share. When
        omitted, substances are mixed in equal shares. The mixture's pH is
        derived from the first substance carrying an ``h_concentration``
        property, defaulting to neutral.
        """
        if not mixture_id or not isinstance(mixture_id, str):
            return False, "invalid_mixture_id", None
        if not isinstance(substance_ids, list) or not substance_ids:
            return False, "no_substances", None
        with self._lock:
            if mixture_id in self._mixtures:
                return False, "mixture_already_exists", self._mixtures[mixture_id]
            if len(self._mixtures) >= self._config.max_mixtures:
                return False, "max_mixtures_reached", None
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", None
            if vessel.status == VesselStatus.RUPTURED.value:
                return False, "vessel_ruptured", None
            # Validate that every substance exists.
            for sid in substance_ids:
                if sid not in self._substances:
                    return False, f"substance_not_found:{sid}", None
            # Build proportions.
            if proportions is None:
                share = 1.0 / len(substance_ids)
                props = {sid: share for sid in substance_ids}
            else:
                props = {}
                total = 0.0
                for sid in substance_ids:
                    val = _safe_float(proportions.get(sid), 0.0)
                    props[sid] = max(0.0, val)
                    total += props[sid]
                if total <= _EPSILON:
                    share = 1.0 / len(substance_ids)
                    props = {sid: share for sid in substance_ids}
                else:
                    # Normalize so the shares sum to 1.
                    props = {sid: v / total for sid, v in props.items()}
            temp = _kelvin_from_input(temperature if temperature is not None else vessel.temperature)
            pres = _safe_float(pressure if pressure is not None else vessel.pressure, self._config.default_pressure_kpa)
            # Derive pH from the first substance with an h_concentration property.
            ph = _STANDARD_PH
            for sid in substance_ids:
                sub = self._substances.get(sid)
                if sub is not None:
                    h = sub.properties.get("h_concentration")
                    if h is not None:
                        ph = _ph_from_h(h)
                        break
            mixture = Mixture(
                mixture_id=mixture_id,
                vessel_id=vessel_id,
                substance_ids=list(substance_ids),
                proportions=props,
                temperature=temp,
                pressure=pres,
                ph=ph,
                volume=vessel.current_volume if vessel.current_volume > 0 else 1.0,
            )
            self._mixtures[mixture_id] = mixture
            # Bind the mixture to the vessel.
            vessel.mixture_id = mixture_id
            vessel.temperature = temp
            vessel.pressure = pres
            vessel.status = VesselStatus.MIXING.value
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.MIXTURE_CREATED.value,
                vessel_id=vessel_id,
                mixture_id=mixture_id,
                description=f"Created mixture {mixture_id} in vessel {vessel_id}",
            )
            return True, "created", mixture

    def get_mixture(self, mixture_id: str) -> Optional[Mixture]:
        """Return the mixture with the given id, or None."""
        if not mixture_id:
            return None
        with self._lock:
            return self._mixtures.get(mixture_id)

    def remove_mixture(self, mixture_id: str) -> Tuple[bool, str, Optional[Mixture]]:
        """Remove a mixture and clear its binding on the host vessel."""
        if not mixture_id:
            return False, "invalid_mixture_id", None
        with self._lock:
            mixture = self._mixtures.pop(mixture_id, None)
            if mixture is None:
                return False, "mixture_not_found", None
            vessel = self._vessels.get(mixture.vessel_id)
            if vessel is not None and vessel.mixture_id == mixture_id:
                vessel.mixture_id = None
                if vessel.status not in (VesselStatus.RUPTURED.value, VesselStatus.SEALED.value):
                    vessel.status = VesselStatus.EMPTY.value if vessel.is_empty else VesselStatus.STABLE.value
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.MIXTURE_REMOVED.value,
                mixture_id=mixture_id,
                vessel_id=mixture.vessel_id,
                description=f"Removed mixture {mixture_id}",
            )
            return True, "removed", mixture

    def list_mixtures(
        self, vessel_id: Optional[str] = None, limit: int = 0
    ) -> List[Mixture]:
        """List mixtures, optionally filtered by host vessel."""
        with self._lock:
            items = list(self._mixtures.values())
            if vessel_id is not None and vessel_id != "":
                items = [m for m in items if m.vessel_id == vessel_id]
            if limit and limit > 0:
                items = items[:limit]
            return items

    # ------------------------------------------------------------------
    # Reaction Execution
    # ------------------------------------------------------------------

    def trigger_reaction(
        self,
        vessel_id: str,
        reaction_id: str,
        catalyst_id: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[ReactionResult]]:
        """Trigger a reaction inside a vessel.

        Checks that the vessel and reaction exist, that the vessel is not
        ruptured, that all reactants are present in the vessel's mixture,
        and that the temperature is sufficient to overcome the activation
        energy. On success, produces a ``ReactionResult`` recording yield,
        energy released, and byproducts.
        """
        if not vessel_id or not reaction_id:
            return False, "invalid_arguments", None
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", None
            if vessel.status == VesselStatus.RUPTURED.value:
                return False, "vessel_ruptured", None
            reaction = self._reactions.get(reaction_id)
            if reaction is None:
                return False, "reaction_not_found", None
            mixture = self._mixtures.get(vessel.mixture_id) if vessel.mixture_id else None
            if mixture is None:
                return False, "vessel_has_no_mixture", None
            if not self._check_reactants_available(mixture, reaction):
                return False, "reactants_not_available", None
            # Resolve the catalyst (either the one requested or one already
            # attached to the vessel that matches this reaction).
            catalyst: Optional[Catalyst] = None
            if catalyst_id:
                catalyst = self._catalysts.get(catalyst_id)
                if catalyst is None:
                    return False, "catalyst_not_found", None
                if not catalyst.active:
                    return False, "catalyst_inactive", None
            else:
                catalyst = self._vessel_catalyst_for(vessel_id, reaction_id)

            # Activation-energy gate: the vessel temperature must supply
            # enough thermal energy relative to the effective barrier.
            effective_ea = self._effective_activation_energy(reaction, catalyst)
            # Use a soft threshold: reaction proceeds when kT (in kJ/mol)
            # reaches at least 5% of the effective barrier. This keeps
            # gameplay forgiving while still favoring heat.
            thermal_energy_kj = (_GAS_CONSTANT * vessel.temperature) / 1000.0
            threshold = max(effective_ea * 0.05, 0.001)
            if thermal_energy_kj < threshold and effective_ea > _EPSILON:
                # Reaction fails: not enough thermal energy.
                result = ReactionResult(
                    result_id=_new_id("res"),
                    vessel_id=vessel_id,
                    reaction_id=reaction_id,
                    success=False,
                    yield_percentage=0.0,
                    byproducts=[],
                    energy_released=0.0,
                    duration=0.0,
                    timestamp=_now(),
                    details={
                        "reason": "insufficient_thermal_energy",
                        "effective_activation_energy": effective_ea,
                        "thermal_energy": thermal_energy_kj,
                        "threshold": threshold,
                    },
                )
                self._record_result(result)
                self._stats.total_reactions_triggered += 1
                self._stats.total_failed_reactions += 1
                self._emit(
                    ChemicalEventKind.REACTION_FAILED.value,
                    vessel_id=vessel_id,
                    reaction_id=reaction_id,
                    description="Reaction failed: insufficient thermal energy",
                    details=result.details,
                )
                return False, "insufficient_thermal_energy", result

            # Compute yield and energy.
            yield_pct = self._compute_yield(
                reaction, vessel.temperature, vessel.pressure, catalyst
            )
            # Duration scales inversely with the rate constant.
            rate = self._arrhenius_rate(reaction, vessel.temperature, catalyst)
            duration = 1.0 / max(rate, _EPSILON) if rate > _EPSILON else 1.0
            duration = _clamp(duration, 0.01, 600.0)
            # Energy released: enthalpy scaled by yield. Negative enthalpy
            # means energy is released (positive value for energy_released
            # on exothermic reactions).
            heat_of_reaction = self._compute_heat_of_reaction(reaction)
            energy_released = -heat_of_reaction * (yield_pct / 100.0)
            # Byproducts: any products that are not the primary product.
            byproducts = list(reaction.product_ids[1:]) if len(reaction.product_ids) > 1 else []

            success = yield_pct > 0.0
            result = ReactionResult(
                result_id=_new_id("res"),
                vessel_id=vessel_id,
                reaction_id=reaction_id,
                success=success,
                yield_percentage=yield_pct,
                byproducts=byproducts,
                energy_released=energy_released,
                duration=duration,
                timestamp=_now(),
                details={
                    "catalyst_id": catalyst.catalyst_id if catalyst else "",
                    "effective_activation_energy": effective_ea,
                    "rate_constant": rate,
                    "heat_of_reaction": heat_of_reaction,
                    "temperature_k": vessel.temperature,
                    "pressure_kpa": vessel.pressure,
                },
            )
            self._record_result(result)

            # Apply reaction effects to the vessel.
            vessel.status = VesselStatus.REACTING.value
            # Exothermic reactions heat the vessel; endothermic cool it.
            temp_delta = -energy_released * 0.1  # kJ -> approximate K shift
            vessel.temperature = max(_ABSOLUTE_ZERO_K, vessel.temperature + temp_delta)
            # Pressure follows the ideal gas law approximation.
            if not vessel.sealed:
                # Open vessel: pressure relaxes toward ambient.
                vessel.pressure = _clamp(
                    vessel.pressure + energy_released * 0.05,
                    0.0, _EXPLOSION_PRESSURE_KPA,
                )
            else:
                # Sealed vessel: pressure climbs with temperature.
                if vessel.temperature > _EPSILON:
                    ratio = vessel.temperature / max(_STANDARD_TEMPERATURE_K, _EPSILON)
                    vessel.pressure = _clamp(
                        vessel.pressure * ratio,
                        0.0, _EXPLOSION_PRESSURE_KPA * 1.5,
                    )

            # Check for rupture after the reaction.
            ruptured = False
            if (
                vessel.pressure >= _EXPLOSION_PRESSURE_KPA
                or vessel.temperature >= _EXPLOSION_TEMPERATURE_K
            ):
                vessel.status = VesselStatus.RUPTURED.value
                ruptured = True
                self._stats.total_vessel_ruptures += 1
                self._emit(
                    ChemicalEventKind.VESSEL_RUPTURED.value,
                    vessel_id=vessel_id,
                    reaction_id=reaction_id,
                    description=f"Vessel {vessel.name} ruptured during reaction",
                )
            elif not ruptured:
                vessel.status = VesselStatus.STABLE.value

            # Update the mixture to reflect product formation (best effort).
            if mixture is not None and success:
                for pid in reaction.product_ids:
                    if pid not in mixture.substance_ids:
                        mixture.substance_ids.append(pid)
                        mixture.proportions[pid] = 0.0
                # Shift proportions toward products proportional to yield.
                shift = yield_pct / 100.0
                for rid in reaction.reactant_ids:
                    if rid in mixture.proportions:
                        mixture.proportions[rid] = max(0.0, mixture.proportions[rid] * (1.0 - shift))
                for pid in reaction.product_ids:
                    mixture.proportions[pid] = mixture.proportions.get(pid, 0.0) + shift / max(1, len(reaction.product_ids))
                mixture.temperature = vessel.temperature
                mixture.pressure = vessel.pressure

            # Catalyst depletion.
            if catalyst is not None and catalyst.depletion_rate > 0.0:
                catalyst.efficiency = _clamp(
                    catalyst.efficiency - catalyst.depletion_rate, 0.0, 1.0
                )
                if catalyst.efficiency <= _EPSILON:
                    catalyst.active = False

            self._stats.total_reactions_triggered += 1
            if success:
                self._stats.total_successful_reactions += 1
            else:
                self._stats.total_failed_reactions += 1

            self._emit(
                ChemicalEventKind.REACTION_COMPLETED.value,
                vessel_id=vessel_id,
                reaction_id=reaction_id,
                catalyst_id=catalyst.catalyst_id if catalyst else "",
                description=f"Reaction {reaction.name} completed with {yield_pct:.1f}% yield",
                details=result.details,
            )
            return True, "completed" if success else "low_yield", result

    def _record_result(self, result: ReactionResult) -> None:
        """Store a reaction result, enforcing the bounded-result limit."""
        self._results[result.result_id] = result
        self._vessel_results.setdefault(result.vessel_id, []).append(result.result_id)
        _evict_fifo_dict(self._results, self._config.max_reaction_results)
        for vid, rids in self._vessel_results.items():
            _evict_fifo_list(rids, self._config.max_reaction_results)

    def check_reaction(
        self, vessel_id: str, reaction_id: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Check whether a reaction can run in a vessel without executing it.

        Returns ``(ok, message, details)`` where ``details`` includes the
        availability of reactants, the effective activation energy, the
        predicted rate constant, and the expected yield.
        """
        if not vessel_id or not reaction_id:
            return False, "invalid_arguments", {}
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", {}
            reaction = self._reactions.get(reaction_id)
            if reaction is None:
                return False, "reaction_not_found", {}
            mixture = self._mixtures.get(vessel.mixture_id) if vessel.mixture_id else None
            reactants_available = self._check_reactants_available(mixture, reaction)
            catalyst = self._vessel_catalyst_for(vessel_id, reaction_id)
            effective_ea = self._effective_activation_energy(reaction, catalyst)
            rate = self._arrhenius_rate(reaction, vessel.temperature, catalyst)
            yield_pct = self._compute_yield(
                reaction, vessel.temperature, vessel.pressure, catalyst
            )
            heat_of_reaction = self._compute_heat_of_reaction(reaction)
            missing_reactants = [
                rid for rid in reaction.reactant_ids
                if mixture is None or rid not in mixture.substance_ids
            ]
            details = {
                "vessel_id": vessel_id,
                "reaction_id": reaction_id,
                "vessel_status": vessel.status,
                "temperature_k": vessel.temperature,
                "pressure_kpa": vessel.pressure,
                "reactants_available": reactants_available,
                "missing_reactants": missing_reactants,
                "has_mixture": mixture is not None,
                "catalyst_id": catalyst.catalyst_id if catalyst else "",
                "catalyst_efficiency": catalyst.efficiency if catalyst else 0.0,
                "base_activation_energy": reaction.activation_energy,
                "effective_activation_energy": effective_ea,
                "rate_constant": rate,
                "predicted_yield": yield_pct,
                "heat_of_reaction": heat_of_reaction,
                "exothermic": reaction.is_exothermic,
                "reversible": reaction.reversible,
            }
            ok = (
                vessel.status != VesselStatus.RUPTURED.value
                and mixture is not None
                and reactants_available
            )
            if ok:
                return True, "ready", details
            if vessel.status == VesselStatus.RUPTURED.value:
                return False, "vessel_ruptured", details
            if mixture is None:
                return False, "vessel_has_no_mixture", details
            if not reactants_available:
                return False, "reactants_not_available", details
            return False, "not_ready", details

    def compute_activation_energy(
        self, reaction_id: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the base and catalyst-adjusted activation energy for a reaction."""
        if not reaction_id:
            return False, "invalid_reaction_id", {}
        with self._lock:
            reaction = self._reactions.get(reaction_id)
            if reaction is None:
                return False, "reaction_not_found", {}
            # Find all catalysts targeting this reaction.
            matching = [
                c for c in self._catalysts.values()
                if c.target_reaction_id == reaction_id and c.active
            ]
            best_catalyst: Optional[Catalyst] = None
            best_ea = reaction.activation_energy
            for cat in matching:
                ea = self._effective_activation_energy(reaction, cat)
                if ea < best_ea:
                    best_ea = ea
                    best_catalyst = cat
            details = {
                "reaction_id": reaction_id,
                "base_activation_energy": reaction.activation_energy,
                "best_effective_activation_energy": best_ea,
                "best_catalyst_id": best_catalyst.catalyst_id if best_catalyst else "",
                "best_catalyst_efficiency": best_catalyst.efficiency if best_catalyst else 0.0,
                "available_catalysts": [
                    {
                        "catalyst_id": c.catalyst_id,
                        "efficiency": c.efficiency,
                        "effective_activation_energy": self._effective_activation_energy(reaction, c),
                    }
                    for c in matching
                ],
            }
            return True, "computed", details

    def compute_reaction_rate(
        self, reaction_id: str, temperature: float
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the Arrhenius rate constant for a reaction at a temperature.

        k = A * exp(-Ea / (R*T)), with Ea in J/mol and T in Kelvin.
        """
        if not reaction_id:
            return False, "invalid_reaction_id", {}
        with self._lock:
            reaction = self._reactions.get(reaction_id)
            if reaction is None:
                return False, "reaction_not_found", {}
            t = _kelvin_from_input(temperature)
            rate = self._arrhenius_rate(reaction, t, None)
            half_life = math.log(2.0) / max(rate, _EPSILON) if rate > _EPSILON else float("inf")
            details = {
                "reaction_id": reaction_id,
                "temperature_k": t,
                "pre_exponential_a": reaction.pre_exponential,
                "activation_energy_kj_per_mol": reaction.activation_energy,
                "gas_constant": _GAS_CONSTANT,
                "rate_constant_k": rate,
                "half_life_seconds": half_life if math.isfinite(half_life) else None,
                "exponent": -((reaction.activation_energy * 1000.0) / (_GAS_CONSTANT * max(t, _EPSILON))),
            }
            return True, "computed", details

    # ------------------------------------------------------------------
    # Catalyst Application
    # ------------------------------------------------------------------

    def apply_catalyst(
        self, vessel_id: str, catalyst_id: str
    ) -> Tuple[bool, str, Optional[Catalyst]]:
        """Attach a catalyst to a vessel so it accelerates matching reactions."""
        if not vessel_id or not catalyst_id:
            return False, "invalid_arguments", None
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", None
            if vessel.status == VesselStatus.RUPTURED.value:
                return False, "vessel_ruptured", None
            catalyst = self._catalysts.get(catalyst_id)
            if catalyst is None:
                return False, "catalyst_not_found", None
            if not catalyst.active:
                return False, "catalyst_inactive", None
            attached = self._vessel_catalysts.setdefault(vessel_id, [])
            if catalyst_id in attached:
                return True, "already_applied", catalyst
            if len(attached) >= self._config.max_vessel_catalysts:
                return False, "max_vessel_catalysts_reached", None
            attached.append(catalyst_id)
            self._emit(
                ChemicalEventKind.CATALYST_APPLIED.value,
                vessel_id=vessel_id,
                catalyst_id=catalyst_id,
                description=f"Applied catalyst {catalyst.name} to vessel {vessel.name}",
            )
            return True, "applied", catalyst

    def remove_catalyst_from_vessel(
        self, vessel_id: str, catalyst_id: str
    ) -> Tuple[bool, str, Optional[Catalyst]]:
        """Detach a catalyst from a vessel."""
        if not vessel_id or not catalyst_id:
            return False, "invalid_arguments", None
        with self._lock:
            catalyst = self._catalysts.get(catalyst_id)
            if catalyst is None:
                return False, "catalyst_not_found", None
            attached = self._vessel_catalysts.get(vessel_id)
            if not attached or catalyst_id not in attached:
                return False, "catalyst_not_in_vessel", None
            attached.remove(catalyst_id)
            self._emit(
                ChemicalEventKind.CATALYST_REMOVED_FROM_VESSEL.value,
                vessel_id=vessel_id,
                catalyst_id=catalyst_id,
                description=f"Removed catalyst {catalyst.name} from vessel {vessel_id}",
            )
            return True, "removed", catalyst

    # ------------------------------------------------------------------
    # Vessel Environment Control
    # ------------------------------------------------------------------

    def set_temperature(
        self, vessel_id: str, temperature: float
    ) -> Tuple[bool, str, Optional[ReactionVessel]]:
        """Set a vessel's temperature in Kelvin and propagate to its mixture.

        Sealed vessels also adjust pressure to follow the ideal gas law.
        """
        if not vessel_id:
            return False, "invalid_vessel_id", None
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", None
            if vessel.status == VesselStatus.RUPTURED.value:
                return False, "vessel_ruptured", None
            new_temp = _kelvin_from_input(temperature)
            old_temp = vessel.temperature
            vessel.temperature = new_temp
            # Propagate to the mixture.
            mixture = self._mixtures.get(vessel.mixture_id) if vessel.mixture_id else None
            temp_delta = new_temp - old_temp
            if mixture is not None:
                mixture.temperature = new_temp
                # Re-derive pressure for a sealed vessel via the ideal gas law.
                if vessel.sealed and old_temp > _EPSILON:
                    ratio = new_temp / old_temp
                    vessel.pressure = _clamp(
                        vessel.pressure * ratio, 0.0, _EXPLOSION_PRESSURE_KPA * 1.5
                    )
                    mixture.pressure = vessel.pressure
            self._emit(
                ChemicalEventKind.TEMPERATURE_SET.value,
                vessel_id=vessel_id,
                description=f"Set vessel {vessel.name} temperature to {new_temp:.2f} K",
                details={"temperature_k": new_temp},
            )
            # Check for thermal rupture.
            self._check_thermal_rupture(vessel)
            return True, "set", vessel

    def set_pressure(
        self, vessel_id: str, pressure: float
    ) -> Tuple[bool, str, Optional[ReactionVessel]]:
        """Set a vessel's pressure in kPa and propagate to its mixture."""
        if not vessel_id:
            return False, "invalid_vessel_id", None
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", None
            if vessel.status == VesselStatus.RUPTURED.value:
                return False, "vessel_ruptured", None
            new_pressure = max(0.0, _safe_float(pressure, self._config.default_pressure_kpa))
            vessel.pressure = new_pressure
            mixture = self._mixtures.get(vessel.mixture_id) if vessel.mixture_id else None
            if mixture is not None:
                mixture.pressure = new_pressure
            self._emit(
                ChemicalEventKind.PRESSURE_SET.value,
                vessel_id=vessel_id,
                description=f"Set vessel {vessel.name} pressure to {new_pressure:.2f} kPa",
                details={"pressure_kpa": new_pressure},
            )
            self._check_thermal_rupture(vessel)
            return True, "set", vessel

    def stir_vessel(
        self, vessel_id: str, intensity: float = _DEFAULT_STIR_INTENSITY
    ) -> Tuple[bool, str, Optional[ReactionVessel]]:
        """Stir a vessel to homogenize its mixture and mark it as mixing.

        Stirring boosts the effective rate of any subsequent reaction by
        ensuring even distribution; the intensity is clamped to a sane band.
        """
        if not vessel_id:
            return False, "invalid_vessel_id", None
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", None
            if vessel.status == VesselStatus.RUPTURED.value:
                return False, "vessel_ruptured", None
            intensity_clamped = _clamp(
                _safe_float(intensity, _DEFAULT_STIR_INTENSITY),
                0.0, _MAX_STIR_INTENSITY,
            )
            vessel.stir_intensity = intensity_clamped
            if vessel.mixture_id is not None and vessel.status != VesselStatus.SEALED.value:
                vessel.status = VesselStatus.MIXING.value
            self._emit(
                ChemicalEventKind.VESSEL_STIRRED.value,
                vessel_id=vessel_id,
                description=f"Stirred vessel {vessel.name} at intensity {intensity_clamped:.2f}",
                details={"intensity": intensity_clamped},
            )
            return True, "stirred", vessel

    def seal_vessel(self, vessel_id: str) -> Tuple[bool, str, Optional[ReactionVessel]]:
        """Seal a vessel so that pressure climbs with temperature instead of venting.

        A sealed vessel traps gases, which steepens the pressure response to
        heat and raises the chance of rupture during exothermic reactions.
        """
        if not vessel_id:
            return False, "invalid_vessel_id", None
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", None
            if vessel.status == VesselStatus.RUPTURED.value:
                return False, "vessel_ruptured", None
            if vessel.sealed:
                return True, "already_sealed", vessel
            vessel.sealed = True
            if vessel.mixture_id is not None and vessel.status == VesselStatus.MIXING.value:
                vessel.status = VesselStatus.SEALED.value
            self._emit(
                ChemicalEventKind.VESSEL_STIRRED.value,
                vessel_id=vessel_id,
                description=f"Sealed vessel {vessel.name}",
                details={"sealed": True},
            )
            return True, "sealed", vessel

    def unseal_vessel(self, vessel_id: str) -> Tuple[bool, str, Optional[ReactionVessel]]:
        """Unseal a vessel so that excess pressure can vent toward ambient."""
        if not vessel_id:
            return False, "invalid_vessel_id", None
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", None
            if vessel.status == VesselStatus.RUPTURED.value:
                return False, "vessel_ruptured", None
            if not vessel.sealed:
                return True, "already_unsealed", vessel
            vessel.sealed = False
            if vessel.status == VesselStatus.SEALED.value:
                vessel.status = (
                    VesselStatus.STABLE.value if vessel.mixture_id is not None
                    else VesselStatus.EMPTY.value
                )
            # Relax pressure back toward ambient when the vessel is opened.
            ambient_p = self._config.default_pressure_kpa
            if vessel.pressure > ambient_p:
                vessel.pressure = ambient_p + (vessel.pressure - ambient_p) * 0.5
            self._emit(
                ChemicalEventKind.VESSEL_STIRRED.value,
                vessel_id=vessel_id,
                description=f"Unsealed vessel {vessel.name}",
                details={"sealed": False},
            )
            return True, "unsealed", vessel

    def _check_thermal_rupture(self, vessel: ReactionVessel) -> None:
        """Rupture a vessel if it exceeds thermal or pressure safety limits."""
        if vessel.status == VesselStatus.RUPTURED.value:
            return
        if (
            vessel.pressure >= _EXPLOSION_PRESSURE_KPA
            or vessel.temperature >= _EXPLOSION_TEMPERATURE_K
        ):
            vessel.status = VesselStatus.RUPTURED.value
            self._stats.total_vessel_ruptures += 1
            self._emit(
                ChemicalEventKind.VESSEL_RUPTURED.value,
                vessel_id=vessel.vessel_id,
                description=f"Vessel {vessel.name} ruptured due to extreme conditions",
                details={
                    "temperature_k": vessel.temperature,
                    "pressure_kpa": vessel.pressure,
                },
            )

    # ------------------------------------------------------------------
    # Equilibrium and Risk Assessment
    # ------------------------------------------------------------------

    def check_equilibrium(self, vessel_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Assess equilibrium state for a reversible reaction in a vessel.

        Applies Le Chatelier's principle: if the vessel's temperature or
        pressure differs from standard conditions, the system predicts the
        direction of the equilibrium shift.
        """
        if not vessel_id:
            return False, "invalid_vessel_id", {}
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", {}
            mixture = self._mixtures.get(vessel.mixture_id) if vessel.mixture_id else None
            if mixture is None:
                return False, "vessel_has_no_mixture", {"vessel_id": vessel_id}
            # Find a reversible reaction whose reactants are present.
            candidate: Optional[Reaction] = None
            for reaction in self._reactions.values():
                if not reaction.reversible:
                    continue
                if self._check_reactants_available(mixture, reaction):
                    candidate = reaction
                    break
            if candidate is None:
                return False, "no_reversible_reaction", {
                    "vessel_id": vessel_id,
                    "mixture_id": vessel.mixture_id,
                }
            temp_delta = vessel.temperature - _STANDARD_TEMPERATURE_K
            pres_delta = vessel.pressure - _STANDARD_PRESSURE_KPA
            shift = self._apply_le_chatelier(candidate, mixture, temp_delta, pres_delta)
            # Compute the reaction quotient vs the equilibrium constant.
            q = 1.0  # Default when proportions are unavailable.
            try:
                product_terms = 1.0
                reactant_terms = 1.0
                for pid in candidate.product_ids:
                    product_terms *= max(mixture.proportions.get(pid, 0.0), _EPSILON)
                for rid in candidate.reactant_ids:
                    reactant_terms *= max(mixture.proportions.get(rid, 0.0), _EPSILON)
                q = product_terms / max(reactant_terms, _EPSILON)
            except Exception:
                q = 1.0
            keq = candidate.equilibrium_constant
            if q < keq - _EPSILON:
                q_direction = "products"
            elif q > keq + _EPSILON:
                q_direction = "reactants"
            else:
                q_direction = "at_equilibrium"
            self._stats.total_equilibrium_shifts += 1
            details = {
                "vessel_id": vessel_id,
                "mixture_id": vessel.mixture_id,
                "reaction_id": candidate.reaction_id,
                "reaction_name": candidate.name,
                "temperature_delta": temp_delta,
                "pressure_delta": pres_delta,
                "equilibrium_constant": keq,
                "reaction_quotient": q,
                "quotient_direction": q_direction,
                "le_chatelier_shift": shift,
            }
            self._emit(
                ChemicalEventKind.EQUILIBRIUM_SHIFTED.value,
                vessel_id=vessel_id,
                reaction_id=candidate.reaction_id,
                description=f"Equilibrium assessment for {candidate.name}: {shift['direction']}",
                details=details,
            )
            return True, "assessed", details

    def check_explosion_risk(self, vessel_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute an explosion-risk score for a vessel in [0, 1]."""
        if not vessel_id:
            return False, "invalid_vessel_id", {}
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", {}
            mixture = self._mixtures.get(vessel.mixture_id) if vessel.mixture_id else None
            flammability = self._mixture_flammability(mixture)
            temperature_factor = _clamp(
                vessel.temperature / _EXPLOSION_TEMPERATURE_K, 0.0, 1.0
            )
            pressure_factor = _clamp(
                vessel.pressure / _EXPLOSION_PRESSURE_KPA, 0.0, 1.0
            )
            fill_factor = vessel.fill_ratio
            # Weighted risk blend. Flammability dominates, followed by
            # pressure and temperature.
            risk = (
                0.45 * flammability
                + 0.25 * pressure_factor
                + 0.20 * temperature_factor
                + 0.10 * fill_factor
            )
            risk = _clamp(risk, 0.0, 1.0)
            if risk >= _HIGH_RISK_SCORE:
                level = "critical"
            elif risk >= _MODERATE_RISK_SCORE:
                level = "high"
            elif risk >= 0.2:
                level = "moderate"
            else:
                level = "low"
            details = {
                "vessel_id": vessel_id,
                "risk_score": risk,
                "risk_level": level,
                "flammability": flammability,
                "temperature_factor": temperature_factor,
                "pressure_factor": pressure_factor,
                "fill_factor": fill_factor,
                "temperature_k": vessel.temperature,
                "pressure_kpa": vessel.pressure,
                "vessel_status": vessel.status,
            }
            if level in ("critical", "high"):
                self._stats.total_explosion_warnings += 1
                self._emit(
                    ChemicalEventKind.EXPLOSION_RISK.value,
                    vessel_id=vessel_id,
                    description=f"Explosion risk {level} for vessel {vessel.name}",
                    details=details,
                )
            return True, level, details

    # ------------------------------------------------------------------
    # Reaction Steps and Results
    # ------------------------------------------------------------------

    def list_reaction_steps(self, reaction_id: str) -> List[ReactionStep]:
        """Return the ordered step list for a reaction."""
        if not reaction_id:
            return []
        with self._lock:
            steps = list(self._reaction_steps.get(reaction_id, []))
            steps.sort(key=lambda s: s.step_number)
            return steps

    def get_reaction_result(self, result_id: str) -> Optional[ReactionResult]:
        """Return a single reaction result by id."""
        if not result_id:
            return None
        with self._lock:
            return self._results.get(result_id)

    def list_reaction_results(
        self, vessel_id: Optional[str] = None, limit: int = 0
    ) -> List[ReactionResult]:
        """List reaction results, optionally filtered by vessel."""
        with self._lock:
            if vessel_id is not None and vessel_id != "":
                rids = self._vessel_results.get(vessel_id, [])
                items = [self._results[rid] for rid in rids if rid in self._results]
            else:
                items = list(self._results.values())
            if limit and limit > 0:
                items = items[-limit:]
            return items

    # ------------------------------------------------------------------
    # Visualization and Graph
    # ------------------------------------------------------------------

    def get_reaction_graph(self) -> Dict[str, Any]:
        """Build a node/edge graph of substances and reactions.

        Nodes are substances; edges are reactions connecting reactants to
        products, labelled with enthalpy and reaction type.
        """
        with self._lock:
            nodes: List[Dict[str, Any]] = []
            edges: List[Dict[str, Any]] = []
            for sub in self._substances.values():
                nodes.append({
                    "id": sub.substance_id,
                    "name": sub.name,
                    "formula": sub.formula,
                    "state": sub.state,
                    "color": sub.color,
                    "flammability": sub.flammability,
                    "toxicity": sub.toxicity,
                })
            for reaction in self._reactions.values():
                for rid in reaction.reactant_ids:
                    for pid in reaction.product_ids:
                        edges.append({
                            "source": rid,
                            "target": pid,
                            "reaction_id": reaction.reaction_id,
                            "reaction_name": reaction.name,
                            "reaction_type": reaction.reaction_type,
                            "enthalpy": reaction.enthalpy,
                            "exothermic": reaction.is_exothermic,
                        })
            return {
                "nodes": nodes,
                "edges": edges,
                "substance_count": len(nodes),
                "reaction_count": len(self._reactions),
                "edge_count": len(edges),
            }

    def get_visualization_data(self, vessel_id: Optional[str] = None) -> Dict[str, Any]:
        """Return visualization-friendly data for one vessel or the whole system."""
        with self._lock:
            if vessel_id is not None and vessel_id != "":
                vessel = self._vessels.get(vessel_id)
                if vessel is None:
                    return {"vessel_id": vessel_id, "error": "vessel_not_found"}
                mixture = self._mixtures.get(vessel.mixture_id) if vessel.mixture_id else None
                substance_nodes: List[Dict[str, Any]] = []
                if mixture is not None:
                    for sid in mixture.substance_ids:
                        sub = self._substances.get(sid)
                        if sub is not None:
                            substance_nodes.append({
                                "id": sub.substance_id,
                                "name": sub.name,
                                "formula": sub.formula,
                                "color": sub.color,
                                "proportion": mixture.proportions.get(sid, 0.0),
                            })
                return {
                    "vessel_id": vessel_id,
                    "vessel": self._vessel_summary(vessel),
                    "substances": substance_nodes,
                    "catalysts": [
                        self._catalysts[cid].to_dict()
                        for cid in self._vessel_catalysts.get(vessel_id, [])
                        if cid in self._catalysts
                    ],
                    "recent_results": [
                        r.to_dict() for r in self.list_reaction_results(vessel_id, limit=5)
                    ],
                }
            # System-wide visualization.
            return {
                "vessels": [self._vessel_summary(v) for v in self._vessels.values()],
                "substance_count": len(self._substances),
                "reaction_count": len(self._reactions),
                "catalyst_count": len(self._catalysts),
                "mixture_count": len(self._mixtures),
                "graph": self.get_reaction_graph(),
                "stats": self._stats.to_dict(),
            }

    # ------------------------------------------------------------------
    # Vessel Reset
    # ------------------------------------------------------------------

    def reset_vessel(self, vessel_id: str) -> Tuple[bool, str, Optional[ReactionVessel]]:
        """Reset a vessel to an empty, ambient state.

        Clears the vessel's mixture, catalysts, volume, temperature, and
        pressure, and returns its status to EMPTY (unless it was ruptured,
        in which case the rupture is repaired for gameplay convenience).
        """
        if not vessel_id:
            return False, "invalid_vessel_id", None
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", None
            # Drop the mixture if present.
            if vessel.mixture_id and vessel.mixture_id in self._mixtures:
                self._mixtures.pop(vessel.mixture_id, None)
            vessel.mixture_id = None
            vessel.current_volume = 0.0
            vessel.temperature = self._config.default_temperature_k
            vessel.pressure = self._config.default_pressure_kpa
            vessel.stir_intensity = 0.0
            vessel.sealed = False
            vessel.status = VesselStatus.EMPTY.value
            self._vessel_catalysts.pop(vessel_id, None)
            self._refresh_stats()
            self._emit(
                ChemicalEventKind.VESSEL_RESET.value,
                vessel_id=vessel_id,
                description=f"Reset vessel {vessel.name}",
            )
            return True, "reset", vessel

    # ------------------------------------------------------------------
    # AI Helpers
    # ------------------------------------------------------------------

    def ai_predict_products(
        self,
        reactant_ids: List[str],
        conditions: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Predict plausible products for a set of reactants.

        The predictor first looks for any registered reaction whose
        reactants exactly match the supplied set. If none is found, it
        applies simple heuristic rules (combustion when oxygen and a
        flammable substance are present; displacement when a reactive
        metal meets water) to suggest candidate products.
        """
        if not isinstance(reactant_ids, list) or not reactant_ids:
            return False, "no_reactants", {}
        with self._lock:
            conditions = conditions or {}
            temperature = _kelvin_from_input(conditions.get("temperature", _STANDARD_TEMPERATURE_K))
            pressure = _safe_float(conditions.get("pressure"), self._config.default_pressure_kpa)
            # Validate reactants exist.
            missing = [rid for rid in reactant_ids if rid not in self._substances]
            if missing:
                return False, "substances_not_found", {"missing": missing}

            # Exact-match lookup against registered reactions.
            exact_matches: List[Dict[str, Any]] = []
            reactant_set = set(reactant_ids)
            for reaction in self._reactions.values():
                if set(reaction.reactant_ids) == reactant_set:
                    rate = self._arrhenius_rate(reaction, temperature, None)
                    exact_matches.append({
                        "reaction_id": reaction.reaction_id,
                        "name": reaction.name,
                        "product_ids": list(reaction.product_ids),
                        "enthalpy": reaction.enthalpy,
                        "exothermic": reaction.is_exothermic,
                        "rate_constant": rate,
                        "confidence": 0.95,
                    })

            # Heuristic predictions when no exact match exists.
            heuristics: List[Dict[str, Any]] = []
            has_oxygen = "sub_oxygen" in reactant_set
            has_water = "sub_water" in reactant_set
            flammable_reactants = [
                rid for rid in reactant_ids
                if self._substances[rid].flammability >= _EXPLOSION_FLAMMABILITY_THRESHOLD
            ]
            reactive_metals = [
                rid for rid in reactant_ids
                if self._substances[rid].toxicity >= 0.5
                and self._substances[rid].state == SubstanceState.SOLID.value
            ]
            if has_oxygen and flammable_reactants:
                # Combustion heuristic: flammable + oxygen -> CO2 + water + ash.
                products = ["sub_co2", "sub_water"]
                if "sub_ash" in self._substances:
                    products.append("sub_ash")
                heuristics.append({
                    "rule": "combustion",
                    "product_ids": products,
                    "confidence": 0.7,
                    "reason": "oxygen plus a flammable substance suggests combustion",
                })
            if has_water and reactive_metals:
                heuristics.append({
                    "rule": "metal_displacement",
                    "product_ids": ["sub_hydrogen"],
                    "confidence": 0.65,
                    "reason": "a reactive solid in water liberates hydrogen",
                })
            if not exact_matches and not heuristics:
                heuristics.append({
                    "rule": "no_reaction",
                    "product_ids": [],
                    "confidence": 0.3,
                    "reason": "no matching reaction rule; reactants likely inert together",
                })

            self._stats.total_ai_predictions += 1
            details = {
                "reactant_ids": list(reactant_ids),
                "temperature_k": temperature,
                "pressure_kpa": pressure,
                "exact_matches": exact_matches,
                "heuristic_predictions": heuristics,
                "best_prediction": (
                    exact_matches[0] if exact_matches
                    else (heuristics[0] if heuristics else None)
                ),
            }
            self._emit(
                ChemicalEventKind.AI_PREDICTION.value,
                description="AI product prediction",
                details=details,
            )
            return True, "predicted", details

    def ai_optimize_conditions(
        self,
        reaction_id: str,
        target: str = "yield",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Optimize temperature and pressure for a reaction toward a goal.

        ``target`` may be ``yield`` (maximize product yield), ``rate``
        (maximize reaction rate), or ``safety`` (minimize explosion risk).
        Returns recommended conditions and the predicted outcome at those
        conditions.
        """
        if not reaction_id:
            return False, "invalid_reaction_id", {}
        with self._lock:
            reaction = self._reactions.get(reaction_id)
            if reaction is None:
                return False, "reaction_not_found", {}
            target_key = str(target).strip().lower()
            # Sweep a temperature range and pick the best candidate.
            best_temp = _STANDARD_TEMPERATURE_K
            best_pressure = _STANDARD_PRESSURE_KPA
            best_score = -1.0
            best_metrics: Dict[str, Any] = {}
            for t in range(300, 1100, 50):
                temp_k = float(t)
                rate = self._arrhenius_rate(reaction, temp_k, None)
                yield_pct = self._compute_yield(reaction, temp_k, _STANDARD_PRESSURE_KPA, None)
                # Risk proxy: higher temperature raises risk.
                risk = _clamp(temp_k / _EXPLOSION_TEMPERATURE_K, 0.0, 1.0)
                if target_key == "rate":
                    score = rate
                elif target_key == "safety":
                    score = (1.0 - risk) * max(yield_pct, 1.0)
                else:  # default: yield
                    score = yield_pct * (1.0 - 0.3 * risk)
                if score > best_score:
                    best_score = score
                    best_temp = temp_k
                    best_pressure = _STANDARD_PRESSURE_KPA
                    best_metrics = {
                        "rate_constant": rate,
                        "predicted_yield": yield_pct,
                        "risk_score": risk,
                    }
            # Tune pressure for gas-phase reactions.
            gaseous = any(
                self._substances[sid].is_gas
                for sid in reaction.reactant_ids + reaction.product_ids
                if sid in self._substances
            )
            if gaseous:
                for p in (50.0, 101.325, 200.0, 400.0):
                    yield_p = self._compute_yield(reaction, best_temp, p, None)
                    if yield_p > best_metrics.get("predicted_yield", 0.0):
                        best_pressure = p
                        best_metrics["predicted_yield"] = yield_p

            details = {
                "reaction_id": reaction_id,
                "target": target_key,
                "recommended_temperature_k": best_temp,
                "recommended_pressure_kpa": best_pressure,
                "predicted_metrics": best_metrics,
                "optimization_score": best_score,
                "is_gas_phase": gaseous,
                "base_activation_energy": reaction.activation_energy,
            }
            self._stats.total_ai_predictions += 1
            self._emit(
                ChemicalEventKind.AI_OPTIMIZATION.value,
                reaction_id=reaction_id,
                description=f"AI optimized conditions for {reaction.name} (target={target_key})",
                details=details,
            )
            return True, "optimized", details

    def ai_assess_stability(self, vessel_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Assess the overall stability of a vessel and its contents.

        Combines explosion risk, thermal stress, chemical toxicity, and
        seal integrity into a single stability verdict.
        """
        if not vessel_id:
            return False, "invalid_vessel_id", {}
        with self._lock:
            vessel = self._vessels.get(vessel_id)
            if vessel is None:
                return False, "vessel_not_found", {}
            mixture = self._mixtures.get(vessel.mixture_id) if vessel.mixture_id else None
            flammability = self._mixture_flammability(mixture)
            toxicity = self._mixture_toxicity(mixture)
            temperature_factor = _clamp(vessel.temperature / _EXPLOSION_TEMPERATURE_K, 0.0, 1.0)
            pressure_factor = _clamp(vessel.pressure / _EXPLOSION_PRESSURE_KPA, 0.0, 1.0)
            fill_factor = vessel.fill_ratio
            seal_penalty = 0.0
            if vessel.sealed and pressure_factor > 0.6:
                seal_penalty = 0.15  # Sealed vessels under high pressure are riskier.
            # Stability is the inverse of an aggregate hazard score.
            hazard = _clamp(
                0.35 * flammability
                + 0.25 * pressure_factor
                + 0.20 * temperature_factor
                + 0.10 * toxicity
                + 0.05 * fill_factor
                + seal_penalty,
                0.0, 1.0,
            )
            stability = _clamp(1.0 - hazard, 0.0, 1.0)
            if stability >= 0.75:
                verdict = "stable"
            elif stability >= 0.5:
                verdict = "marginal"
            elif stability >= 0.25:
                verdict = "unstable"
            else:
                verdict = "critical"
            recommendations: List[str] = []
            if temperature_factor > 0.6:
                recommendations.append("reduce_temperature")
            if pressure_factor > 0.6:
                recommendations.append("vent_pressure")
            if flammability > _EXPLOSION_FLAMMABILITY_THRESHOLD:
                recommendations.append("isolate_flammable_contents")
            if toxicity > 0.5:
                recommendations.append("wear_respiratory_protection")
            if vessel.sealed and pressure_factor > 0.6:
                recommendations.append("unseal_or_relieve_pressure")
            if vessel.status == VesselStatus.RUPTURED.value:
                recommendations.append("vessel_already_ruptured_replace_immediately")
            details = {
                "vessel_id": vessel_id,
                "stability_score": stability,
                "hazard_score": hazard,
                "verdict": verdict,
                "flammability": flammability,
                "toxicity": toxicity,
                "temperature_factor": temperature_factor,
                "pressure_factor": pressure_factor,
                "fill_factor": fill_factor,
                "sealed": vessel.sealed,
                "vessel_status": vessel.status,
                "recommendations": recommendations,
            }
            self._stats.total_ai_predictions += 1
            self._emit(
                ChemicalEventKind.AI_ASSESSMENT.value,
                vessel_id=vessel_id,
                description=f"AI stability assessment for {vessel.name}: {verdict}",
                details=details,
            )
            return True, verdict, details

    # ------------------------------------------------------------------
    # Events and Status
    # ------------------------------------------------------------------

    def list_events(
        self, kind: Optional[str] = None, limit: int = 100
    ) -> List[ChemicalEvent]:
        """List audit events, optionally filtered by event kind."""
        with self._lock:
            items = list(self._events)
            if kind is not None and kind != "":
                items = [e for e in items if e.kind == kind]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def tick(self, dt: float = 1.0) -> Tuple[bool, str, Dict[str, Any]]:
        """Advance the simulation by ``dt`` seconds.

        Each tick relaxes vessel temperatures toward ambient, ages catalysts,
        re-derives mixture pH, and checks for ruptures. The return value
        reports a per-vessel summary of the changes.
        """
        with self._lock:
            delta = _safe_float(dt, 1.0)
            self._tick_count += 1
            self._global_time += delta
            ambient_t = self._config.ambient_temperature_k
            vessel_reports: List[Dict[str, Any]] = []
            for vessel in self._vessels.values():
                if vessel.status == VesselStatus.RUPTURED.value:
                    vessel_reports.append({
                        "vessel_id": vessel.vessel_id,
                        "change": "skipped_ruptured",
                    })
                    continue
                # Thermal relaxation toward ambient (Newton's law of cooling,
                # simplified).
                if abs(vessel.temperature - ambient_t) > _EPSILON:
                    cooling = 0.05 * delta
                    vessel.temperature += (ambient_t - vessel.temperature) * cooling
                    vessel.temperature = max(_ABSOLUTE_ZERO_K, vessel.temperature)
                # Pressure relaxation for unsealed vessels.
                if not vessel.sealed:
                    ambient_p = self._config.default_pressure_kpa
                    if abs(vessel.pressure - ambient_p) > _EPSILON:
                        vessel.pressure += (ambient_p - vessel.pressure) * 0.05 * delta
                        vessel.pressure = max(0.0, vessel.pressure)
                # Age catalysts attached to this vessel.
                for cid in self._vessel_catalysts.get(vessel.vessel_id, []):
                    cat = self._catalysts.get(cid)
                    if cat is not None and cat.active and cat.depletion_rate > 0.0:
                        cat.efficiency = _clamp(
                            cat.efficiency - cat.depletion_rate * delta, 0.0, 1.0
                        )
                        if cat.efficiency <= _EPSILON:
                            cat.active = False
                # Re-derive mixture pH and sync environment.
                mixture = self._mixtures.get(vessel.mixture_id) if vessel.mixture_id else None
                if mixture is not None:
                    mixture.temperature = vessel.temperature
                    mixture.pressure = vessel.pressure
                    # Re-derive pH from the dominant substance.
                    dominant_sid = max(
                        mixture.substance_ids,
                        key=lambda s: mixture.proportions.get(s, 0.0),
                    ) if mixture.substance_ids else None
                    if dominant_sid is not None:
                        sub = self._substances.get(dominant_sid)
                        if sub is not None:
                            h = sub.properties.get("h_concentration")
                            if h is not None:
                                mixture.ph = _ph_from_h(h)
                # Check for thermal rupture.
                self._check_thermal_rupture(vessel)
                # Transition mixing vessels back to stable after stirring
                # settles.
                if (
                    vessel.status == VesselStatus.MIXING.value
                    and vessel.stir_intensity > 0.0
                ):
                    vessel.stir_intensity = max(0.0, vessel.stir_intensity - 0.1 * delta)
                    if vessel.stir_intensity <= _EPSILON and vessel.mixture_id is not None:
                        vessel.status = VesselStatus.STABLE.value
                vessel_reports.append({
                    "vessel_id": vessel.vessel_id,
                    "temperature_k": vessel.temperature,
                    "pressure_kpa": vessel.pressure,
                    "status": vessel.status,
                    "stir_intensity": vessel.stir_intensity,
                })
            self._stats.tick_count = self._tick_count
            self._emit(
                ChemicalEventKind.TICK.value,
                description=f"Tick {self._tick_count} (dt={delta})",
                details={"delta": delta, "vessels": len(vessel_reports)},
            )
            return True, "ticked", {
                "tick_count": self._tick_count,
                "delta": delta,
                "vessels": vessel_reports,
            }

    # ------------------------------------------------------------------
    # Config, Stats, Snapshot, Status
    # ------------------------------------------------------------------

    def get_config(self) -> ChemicalConfig:
        """Return the current configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, ChemicalConfig]:
        """Update configuration fields by keyword argument."""
        with self._lock:
            if not kwargs:
                return False, "no_changes", self._config
            updated: List[str] = []
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    try:
                        setattr(self._config, key, value)
                        updated.append(key)
                    except Exception:
                        continue
            if not updated:
                return False, "no_valid_fields", self._config
            self._emit(
                ChemicalEventKind.CONFIG_UPDATED.value,
                description=f"Config updated: {', '.join(updated)}",
                details={"updated_fields": updated},
            )
            return True, "updated", self._config

    def get_stats(self) -> ChemicalStats:
        """Return aggregate statistics."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> ChemicalSnapshot:
        """Return a full state snapshot."""
        with self._lock:
            self._refresh_stats()
            return ChemicalSnapshot(
                substances=[s.to_dict() for s in self._substances.values()],
                reactions=[r.to_dict() for r in self._reactions.values()],
                catalysts=[c.to_dict() for c in self._catalysts.values()],
                vessels=[v.to_dict() for v in self._vessels.values()],
                mixtures=[m.to_dict() for m in self._mixtures.values()],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a concise status summary."""
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "seeded": self._seeded,
                "total_substances": len(self._substances),
                "total_reactions": len(self._reactions),
                "total_catalysts": len(self._catalysts),
                "total_vessels": len(self._vessels),
                "total_mixtures": len(self._mixtures),
                "total_reaction_steps": sum(len(v) for v in self._reaction_steps.values()),
                "total_reaction_results": len(self._results),
                "total_reactions_triggered": self._stats.total_reactions_triggered,
                "total_successful_reactions": self._stats.total_successful_reactions,
                "total_failed_reactions": self._stats.total_failed_reactions,
                "total_vessel_ruptures": self._stats.total_vessel_ruptures,
                "total_explosion_warnings": self._stats.total_explosion_warnings,
                "total_equilibrium_shifts": self._stats.total_equilibrium_shifts,
                "total_ai_predictions": self._stats.total_ai_predictions,
                "tick_count": self._tick_count,
                "global_time": self._global_time,
            }


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_chemical_reaction_system() -> _ChemicalReactionSystem:
    """Return the shared chemical reaction system singleton.

    Ensures the instance is created via ``get_instance`` and seeded via
    ``initialize`` before returning it to the caller.
    """
    inst = _ChemicalReactionSystem.get_instance()
    if not inst._initialized:
        inst.initialize()
    return inst
