"""
SparkLabs Engine - Electromagnetic Field System

Simulates electromagnetic physics for gameplay inside the SparkLabs
AI-native game engine. The system maintains a set of point charges,
spatial magnetic fields, electrical circuits, conductors, induction
coils, and electromagnetic sources, then evaluates the coupled electric
and magnetic fields they produce. Designers can use the system to drive
electricity puzzles, magnetic platforms, electromagnetic weapons, circuit
mechanics, and induction-based contraptions.

The physics model is intentionally lightweight but grounded in classical
electromagnetism. Electric fields follow Coulomb's law, magnetic fields
superpose with distance-based falloff, the Lorentz force drives charge
motion during the tick loop, Faraday's law governs induction coils, and
Ohm's law ties circuit voltage, current, and resistance together. The
deterministic tick loop integrates charge motion with an explicit Euler
step and refreshes coil flux history so that subsequent EMF queries
reflect the latest state.

Architecture:
  _ElectromagneticFieldSystem (Singleton)
    |-- Charge, MagneticField, Circuit, Conductor, InductionCoil
    |-- EMSource, FieldLine, EMStats, EMConfig, EMSnapshot, EMEvent
    |-- ChargeType, FieldType, CircuitStatus, ConductorType, EMEventKind

Core Capabilities:
  - register_charge / remove_charge / get_charge / list_charges
  - register_magnetic_field / remove_magnetic_field / get_magnetic_field / list_magnetic_fields
  - register_circuit / remove_circuit / get_circuit / list_circuits
  - register_conductor / remove_conductor / get_conductor / list_conductors
  - compute_electric_field / compute_magnetic_field / compute_force
  - check_induction / compute_emf
  - apply_voltage / apply_current / check_short_circuit
  - register_induction_coil / remove_induction_coil / get_induction_coil
  - ai_assess_field_strength / ai_optimize_circuit / ai_predict_interference
  - get_field_map / get_visualization_data / get_field_lines
  - reset_field / list_events / tick
  - get_stats / get_snapshot / get_status / get_config / set_config

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`_ElectromagneticFieldSystem.get_instance` or the module-level
:func:`get_electromagnetic_field_system` factory.

Physics Reference:
  The system evaluates the following classical electromagnetism formulas
  every time a field, force, flux, or circuit query is issued. The
  notation matches the variable names used in the implementation.

  - Coulomb's law (force between two point charges)::
        F = k * q1 * q2 / r^2
    where ``k`` is the Coulomb constant (8.99e9 N m^2 / C^2), ``q1`` and
    ``q2`` are the charge values in Coulombs, and ``r`` is the distance
    between them in meters. The force is repulsive for like signs and
    attractive for opposite signs.

  - Electric field of a point charge::
        E = k * q / r^2
    The field points radially outward for positive charges and inward
    for negative charges. The total field at a point is the vector sum
    of the contributions from every registered charge.

  - Magnetic force on a moving charge (Lorentz force, magnetic term)::
        F = q * (v x B)
    where ``v`` is the charge velocity and ``B`` is the local magnetic
    flux density. The full Lorentz force combines the electric and
    magnetic terms: ``F = q * E + q * (v x B)``.

  - Magnetic flux through a coil::
        Phi = B . (A * n_hat) = B * A * cos(theta)
    where ``A`` is the coil area, ``n_hat`` is the coil's unit normal,
    and ``theta`` is the angle between ``B`` and ``n_hat``.

  - Faraday's law of induction::
        EMF = -N * dPhi/dt
    where ``N`` is the number of turns and ``dPhi/dt`` is the rate of
    change of the magnetic flux through the coil.

  - Ohm's law::
        V = I * R
    relating voltage (V), current (I), and resistance (R) for a closed
    circuit. The aggregate resistance is the sum of edge resistances
    plus the resistance of any attached conductors.

  - Magnetic field falloff:
    Inside a field's radius the field is uniform. Outside, permanent
    magnets fall off as 1/r^3 (dipole-like) while electromagnets and
    solenoids fall off as 1/r^2.

Usage:
    em = get_electromagnetic_field_system()
    ok, msg, charge = em.register_charge("ch_001", (10.0, 0.0, 0.0), 1.5e-6)
    ok, msg, field = em.compute_electric_field((5.0, 0.0, 0.0))
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Physical & Capacity Constants
# ---------------------------------------------------------------------------

# Coulomb's constant in N * m^2 / C^2. Governs the strength of the
# electrostatic interaction between point charges.
_COULOMB_CONSTANT: float = 8.99e9

# Vacuum permeability scaled for gameplay. Used when translating a coil's
# field back into a magnetic flux density contribution.
_PERMEABILITY_FACTOR: float = 1.25663706e-6

# Smallest magnitude considered non-zero. Guards against division-by-zero
# in field, force, and flux calculations.
_EPSILON: float = 1e-9

# Speed of light in m/s. Used by the interference predictor to translate
# an EM source frequency into a wavelength.
_SPEED_OF_LIGHT: float = 2.998e8

# Bounded store capacities. When a store exceeds its capacity the oldest
# entries are evicted in FIFO order to keep memory growth predictable.
_MAX_CHARGES: int = 500
_MAX_MAGNETIC_FIELDS: int = 300
_MAX_CIRCUITS: int = 200
_MAX_CONDUCTORS: int = 500
_MAX_INDUCTION_COILS: int = 300
_MAX_EM_SOURCES: int = 200
_MAX_FIELD_LINES: int = 1000
_MAX_EVENTS: int = 10000

# Default timestep used when no explicit dt is supplied to the simulation
# loop or when a coil EMF is queried before the first tick.
_DEFAULT_DT: float = 0.016

# Default spatial extent used by the field map sampler when the runtime
# configuration does not override it. The tuple encodes
# (min_x, min_y, min_z, max_x, max_y, max_z).
_DEFAULT_FIELD_BOUNDS: Tuple[float, float, float, float, float, float] = (
    -50.0, -50.0, -50.0, 50.0, 50.0, 50.0,
)

# Default conductor resistivity table (Ohm * meter). The values are
# approximate bulk resistivities at room temperature and are used to seed
# a sensible resistance-per-meter when a conductor is registered without
# an explicit value.
_MATERIAL_RESISTIVITY: Dict[str, float] = {
    "copper": 1.68e-8,
    "aluminum": 2.82e-8,
    "silver": 1.59e-8,
    "gold": 2.44e-8,
    "iron": 9.71e-8,
}

# Risk thresholds used by the AI interference predictor. A source whose
# normalized coupling score crosses these bands is tagged accordingly.
_RISK_LOW: float = 0.25
_RISK_MODERATE: float = 0.5
_RISK_HIGH: float = 0.75


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ChargeType(str, Enum):
    """Sign classification of a point charge."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class FieldType(str, Enum):
    """Construction class of a spatial magnetic field."""
    PERMANENT = "permanent"
    ELECTROMAGNET = "electromagnet"
    SOLENOID = "solenoid"


class CircuitStatus(str, Enum):
    """Operational status of an electrical circuit."""
    OPEN = "open"
    CLOSED = "closed"
    SHORTED = "shorted"
    BLOWN = "blown"


class ConductorType(str, Enum):
    """Material classification of a conductor."""
    COPPER = "copper"
    ALUMINUM = "aluminum"
    SILVER = "silver"
    GOLD = "gold"
    IRON = "iron"


class EMSourceType(str, Enum):
    """Emission mode of an electromagnetic source."""
    STATIC = "static"
    AC = "ac"
    DC = "dc"
    PULSE = "pulse"


class FieldLineType(str, Enum):
    """Kind of field a field line traces."""
    ELECTRIC = "electric"
    MAGNETIC = "magnetic"


class EMEventKind(str, Enum):
    """Audit event types emitted by the electromagnetic field system."""
    CHARGE_REGISTERED = "charge_registered"
    CHARGE_REMOVED = "charge_removed"
    CHARGE_MOVED = "charge_moved"
    MAGNETIC_FIELD_REGISTERED = "magnetic_field_registered"
    MAGNETIC_FIELD_REMOVED = "magnetic_field_removed"
    MAGNETIC_FIELD_TOGGLED = "magnetic_field_toggled"
    CIRCUIT_REGISTERED = "circuit_registered"
    CIRCUIT_REMOVED = "circuit_removed"
    CIRCUIT_ELEMENT_CONNECTED = "circuit_element_connected"
    CIRCUIT_ELEMENT_DISCONNECTED = "circuit_element_disconnected"
    VOLTAGE_APPLIED = "voltage_applied"
    CURRENT_APPLIED = "current_applied"
    SHORT_CIRCUIT_DETECTED = "short_circuit_detected"
    CIRCUIT_BLOWN = "circuit_blown"
    CONDUCTOR_REGISTERED = "conductor_registered"
    CONDUCTOR_REMOVED = "conductor_removed"
    COIL_REGISTERED = "coil_registered"
    COIL_REMOVED = "coil_removed"
    INDUCTION_DETECTED = "induction_detected"
    EMF_COMPUTED = "emf_computed"
    EM_SOURCE_REGISTERED = "em_source_registered"
    EM_SOURCE_REMOVED = "em_source_removed"
    EM_SOURCE_TOGGLED = "em_source_toggled"
    FIELD_LINE_GENERATED = "field_line_generated"
    FIELD_RESET = "field_reset"
    TICK = "tick"
    CONFIG_UPDATED = "config_updated"
    AI_ASSESSMENT = "ai_assessment"


# ---------------------------------------------------------------------------
# Helper Functions (module-level)
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.utcnow().isoformat() + "Z"


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
    try:
        if value is None:
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Parse an int, returning default on failure."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits max_size."""
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


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to default."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Recursively convert arbitrary values into JSON-serializable types."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Serialize a dataclass instance into a plain dict.

    The ``__dataclass_fields__`` attribute is checked before any
    ``to_dict`` method so that dataclasses which also expose one do not
    recurse through their own serializer.
    """
    if instance is None:
        return {}
    if hasattr(instance, "__dataclass_fields__"):
        out: Dict[str, Any] = {}
        for name in getattr(instance, "__dataclass_fields__", {}).keys():
            try:
                raw = getattr(instance, name)
            except Exception:
                continue
            out[name] = _to_jsonable(raw)
        return out
    if isinstance(instance, dict):
        return {str(k): _to_jsonable(v) for k, v in instance.items()}
    if hasattr(instance, "to_dict") and callable(instance.to_dict):
        return instance.to_dict()
    return {}


# ---------------------------------------------------------------------------
# Vector Helpers (3-tuples)
# ---------------------------------------------------------------------------

def _vec_add(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    """Component-wise addition of two 3-vectors."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_sub(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    """Component-wise subtraction of two 3-vectors (a - b)."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_scale(
    v: Tuple[float, float, float],
    s: float,
) -> Tuple[float, float, float]:
    """Scale a 3-vector by a scalar."""
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec_dot(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
) -> float:
    """Dot product of two 3-vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_cross(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    """Cross product of two 3-vectors (a x b)."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec_length(v: Tuple[float, float, float]) -> float:
    """Euclidean length of a 3-vector."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Return the unit-length direction of a 3-vector.

    A zero (or near-zero) vector returns the zero vector so callers do
    not need to special-case the degenerate direction.
    """
    n = _vec_length(v)
    if n < _EPSILON:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _vec_distance(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
) -> float:
    """Euclidean distance between two 3-points."""
    return _vec_length(_vec_sub(a, b))


def _vec_lerp(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    t: float,
) -> Tuple[float, float, float]:
    """Linear interpolation between two 3-vectors by parameter t."""
    tt = _clamp(t, 0.0, 1.0)
    return (
        a[0] + (b[0] - a[0]) * tt,
        a[1] + (b[1] - a[1]) * tt,
        a[2] + (b[2] - a[2]) * tt,
    )


def _vec_angle(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
) -> float:
    """Angle in radians between two 3-vectors."""
    na = _vec_length(a)
    nb = _vec_length(b)
    if na < _EPSILON or nb < _EPSILON:
        return 0.0
    cos_t = _clamp(_vec_dot(a, b) / (na * nb), -1.0, 1.0)
    return math.acos(cos_t)


def _coerce_position(value: Any) -> Tuple[float, float, float]:
    """Coerce a sequence of numbers into a 3-tuple position vector."""
    if value is None:
        return (0.0, 0.0, 0.0)
    if isinstance(value, (list, tuple)):
        if len(value) >= 3:
            return (
                _safe_float(value[0], 0.0),
                _safe_float(value[1], 0.0),
                _safe_float(value[2], 0.0),
            )
        if len(value) == 2:
            return (
                _safe_float(value[0], 0.0),
                _safe_float(value[1], 0.0),
                0.0,
            )
        if len(value) == 1:
            return (_safe_float(value[0], 0.0), 0.0, 0.0)
    return (0.0, 0.0, 0.0)


def _classify_charge_type(charge_value: float) -> str:
    """Derive a ChargeType label from a signed charge value."""
    q = _safe_float(charge_value, 0.0)
    if q > _EPSILON:
        return ChargeType.POSITIVE.value
    if q < -_EPSILON:
        return ChargeType.NEGATIVE.value
    return ChargeType.NEUTRAL.value


def _material_resistivity(material: str) -> float:
    """Look up the bulk resistivity for a conductor material."""
    key = str(material).strip().lower()
    return _MATERIAL_RESISTIVITY.get(key, _MATERIAL_RESISTIVITY["copper"])


def _strength_label(magnitude: float) -> str:
    """Map a field magnitude to a coarse qualitative label."""
    m = abs(_safe_float(magnitude, 0.0))
    if m >= 1.0e6:
        return "extreme"
    if m >= 1.0e3:
        return "high"
    if m >= 1.0:
        return "moderate"
    if m >= 1.0e-3:
        return "low"
    return "negligible"


def _risk_label(score: float) -> str:
    """Map a numeric risk score in [0, 1] to a human-readable label."""
    s = _clamp(_safe_float(score, 0.0), 0.0, 1.0)
    if s >= _RISK_HIGH:
        return "high"
    if s >= _RISK_MODERATE:
        return "moderate"
    if s >= _RISK_LOW:
        return "low"
    return "negligible"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Charge:
    """A point charge that contributes to the electric field.

    The charge value is expressed in Coulombs. Pinned charges are
    excluded from the integration step in ``tick`` so that designers can
    anchor sources of field without them drifting under their own
    interactions.
    """
    charge_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    charge_value: float = 0.0
    charge_type: str = ChargeType.NEUTRAL.value
    pinned: bool = False
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mass: float = 1.0
    net_force: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MagneticField:
    """A spatial magnetic field region with a uniform central vector.

    The ``field_vector`` is expressed in Tesla and represents the field
    at the region's center. Inside ``radius`` the field is treated as
    uniform; outside it falls off with distance so that overlapping
    fields blend smoothly.
    """
    field_id: str
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    field_vector: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 10.0
    field_type: str = FieldType.PERMANENT.value
    active: bool = True
    strength: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Circuit:
    """An electrical circuit composed of nodes and edges.

    Edges are stored as dictionaries carrying an ``edge_id``, a
    ``resistance`` in Ohms, and a ``voltage`` in Volts. The aggregate
    ``resistance`` field is the sum of edge resistances and is refreshed
    whenever the edge set changes.
    """
    circuit_id: str
    name: str = ""
    nodes: List[str] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    voltage: float = 0.0
    current: float = 0.0
    status: str = CircuitStatus.OPEN.value
    resistance: float = 0.0
    connected_elements: List[str] = field(default_factory=list)
    power: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Conductor:
    """A linear conductor segment that participates in a circuit.

    The total resistance is the product of the per-meter resistance and
    the conductor length. When ``connected_circuit_id`` is set the
    conductor contributes its resistance to that circuit.
    """
    conductor_id: str
    name: str = ""
    material: str = ConductorType.COPPER.value
    resistance_per_meter: float = 0.0
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    length: float = 1.0
    connected_circuit_id: Optional[str] = None
    total_resistance: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InductionCoil:
    """A coil that develops an EMF when the magnetic flux through it changes.

    The ``orientation`` is the unit normal of the coil face and is used
    together with the local magnetic field to compute the flux via
    ``Phi = B . (A * n_hat)``. The previous flux is retained so that
    Faraday's law can be evaluated on demand.
    """
    coil_id: str
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    turns: int = 1
    area: float = 1.0
    magnetic_flux: float = 0.0
    induced_emf: float = 0.0
    orientation: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    previous_flux: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EMSource:
    """An electromagnetic emission source such as an antenna or coil gun.

    The ``source_type`` governs how the source couples to nearby
    charges and coils: DC sources bias static fields, AC sources drive
    oscillating coupling, pulse sources emit transient bursts, and
    static sources describe a steady ambient field.
    """
    source_id: str
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    frequency: float = 0.0
    power: float = 0.0
    source_type: str = EMSourceType.STATIC.value
    active: bool = True
    radius: float = 25.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FieldLine:
    """A traced field line used for visualization.

    The line is stored as a polyline of 3D points plus the aggregate
    field strength sampled along the trace.
    """
    line_id: str
    start_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    end_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    field_strength: float = 0.0
    field_type: str = FieldLineType.ELECTRIC.value
    segments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EMConfig:
    """Tunable runtime configuration for the electromagnetic system."""
    coulomb_constant: float = _COULOMB_CONSTANT
    permeability_factor: float = _PERMEABILITY_FACTOR
    max_charges: int = _MAX_CHARGES
    max_magnetic_fields: int = _MAX_MAGNETIC_FIELDS
    max_circuits: int = _MAX_CIRCUITS
    max_conductors: int = _MAX_CONDUCTORS
    max_induction_coils: int = _MAX_INDUCTION_COILS
    max_em_sources: int = _MAX_EM_SOURCES
    max_field_lines: int = _MAX_FIELD_LINES
    max_events: int = _MAX_EVENTS
    short_circuit_resistance: float = 0.1
    fuse_current_threshold: float = 100.0
    induction_emf_threshold: float = 0.01
    default_dt: float = _DEFAULT_DT
    field_line_step: float = 0.5
    field_line_max_steps: int = 50
    field_map_resolution: int = 16
    field_map_bounds: Tuple[float, float, float, float, float, float] = _DEFAULT_FIELD_BOUNDS
    enable_charge_dynamics: bool = True
    enable_induction: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EMStats:
    """Roll-up statistics maintained across the system lifetime."""
    total_charges: int = 0
    total_magnetic_fields: int = 0
    total_circuits: int = 0
    total_conductors: int = 0
    total_induction_coils: int = 0
    total_em_sources: int = 0
    total_field_lines: int = 0
    active_magnetic_fields: int = 0
    active_em_sources: int = 0
    open_circuits: int = 0
    closed_circuits: int = 0
    shorted_circuits: int = 0
    blown_circuits: int = 0
    total_emf_computations: int = 0
    total_force_computations: int = 0
    total_inductions_detected: int = 0
    total_short_circuits: int = 0
    total_charges_moved: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EMSnapshot:
    """A point-in-time snapshot of the full system state."""
    timestamp: str = field(default_factory=_now)
    charges: List[Dict[str, Any]] = field(default_factory=list)
    magnetic_fields: List[Dict[str, Any]] = field(default_factory=list)
    circuits: List[Dict[str, Any]] = field(default_factory=list)
    conductors: List[Dict[str, Any]] = field(default_factory=list)
    induction_coils: List[Dict[str, Any]] = field(default_factory=list)
    em_sources: List[Dict[str, Any]] = field(default_factory=list)
    field_lines: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EMEvent:
    """An internal audit event emitted by the electromagnetic system."""
    event_id: str
    timestamp: str
    event_type: str
    charge_id: Optional[str] = None
    field_id: Optional[str] = None
    circuit_id: Optional[str] = None
    conductor_id: Optional[str] = None
    coil_id: Optional[str] = None
    source_id: Optional[str] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Electromagnetic Field System (Singleton)
# ---------------------------------------------------------------------------

class _ElectromagneticFieldSystem:
    """Simulates electromagnetic physics for gameplay.

    The system is thread-safe and implemented as a singleton with
    double-checked locking. ``_init_lock`` guards singleton creation and
    the one-time seed pass; ``_lock`` guards all mutating operations to
    keep the internal dictionaries consistent across threads.

    The physics model is deliberately compact so it can run every frame
    without specialized solvers. Electric fields sum Coulomb
    contributions from every charge, magnetic fields superpose with
    distance-based falloff, the Lorentz force advances free charges
    during ``tick``, and Faraday's law evaluates induction coils against
    their retained flux history.
    """

    _instance: Optional["_ElectromagneticFieldSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._seeded: bool = False
        self._charges: Dict[str, Charge] = {}
        self._magnetic_fields: Dict[str, MagneticField] = {}
        self._circuits: Dict[str, Circuit] = {}
        self._conductors: Dict[str, Conductor] = {}
        self._induction_coils: Dict[str, InductionCoil] = {}
        self._em_sources: Dict[str, EMSource] = {}
        self._field_lines: Dict[str, FieldLine] = {}
        self._events: List[EMEvent] = []
        self._config = EMConfig()
        self._stats = EMStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._field_line_counter: int = 0
        self._global_time: float = 0.0
        self._last_dt: float = _DEFAULT_DT

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "_ElectromagneticFieldSystem":
        """Return the shared singleton, creating it if needed.

        Uses double-checked locking so that the singleton is created
        exactly once even when multiple threads race on the first call.
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
        """Seed the system exactly once with the canonical demo data."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed_data()
            self._initialized = True

    def _seed_data(self) -> None:
        """Populate the system with a baseline set of electromagnetic data.

        The seed is intentionally compact but covers every entity type so
        that downstream tools can exercise the full API without first
        having to register objects by hand.
        """
        with self._lock:
            if self._seeded:
                return

            # ----------------------------------------------------------
            # Charges (5)
            # ----------------------------------------------------------
            charge_seeds: List[Tuple[str, Tuple[float, float, float], float, bool, float, Tuple[float, float, float]]] = [
                ("ch_seed_pos_a", (10.0, 0.0, 0.0), 1.5e-6, True, 1.0, (0.0, 0.0, 0.0)),
                ("ch_seed_neg_b", (-10.0, 0.0, 0.0), -2.0e-6, True, 1.0, (0.0, 0.0, 0.0)),
                ("ch_seed_pos_c", (0.0, 10.0, 0.0), 3.0e-6, False, 0.5, (0.0, 0.0, 0.0)),
                ("ch_seed_neg_d", (0.0, -10.0, 0.0), -1.0e-6, False, 0.5, (0.0, 0.0, 0.0)),
                ("ch_seed_neutral_e", (0.0, 0.0, 10.0), 0.0, True, 2.0, (0.0, 0.0, 0.0)),
            ]
            for cid, pos, q, pinned, mass, vel in charge_seeds:
                charge = Charge(
                    charge_id=cid,
                    position=pos,
                    charge_value=q,
                    charge_type=_classify_charge_type(q),
                    pinned=pinned,
                    velocity=vel,
                    mass=max(_EPSILON, mass),
                )
                self._charges[cid] = charge

            # ----------------------------------------------------------
            # Magnetic Fields (3)
            # ----------------------------------------------------------
            field_seeds: List[Tuple[str, str, Tuple[float, float, float], Tuple[float, float, float], float, str, bool]] = [
                ("mf_seed_perm", "Permanent Magnet Platform",
                 (0.0, 5.0, 0.0), (0.0, 1.5, 0.0), 12.0,
                 FieldType.PERMANENT.value, True),
                ("mf_seed_electro", "Electromagnetic Lift",
                 (20.0, 0.0, 0.0), (0.0, 0.0, 2.0), 8.0,
                 FieldType.ELECTROMAGNET.value, True),
                ("mf_seed_solenoid", "Solenoid Barrel",
                 (-20.0, 0.0, 0.0), (1.0, 0.0, 0.0), 6.0,
                 FieldType.SOLENOID.value, True),
            ]
            for fid, name, pos, vec, radius, ftype, active in field_seeds:
                mf = MagneticField(
                    field_id=fid,
                    name=name,
                    position=pos,
                    field_vector=vec,
                    radius=max(_EPSILON, radius),
                    field_type=ftype,
                    active=active,
                    strength=_vec_length(vec),
                )
                self._magnetic_fields[fid] = mf

            # ----------------------------------------------------------
            # Circuits (3)
            # ----------------------------------------------------------
            circuit_seeds: List[Tuple[str, str, float, float, str]] = [
                ("cir_seed_main", "Main Power Loop", 12.0, 4.0, CircuitStatus.CLOSED.value),
                ("cir_seed_logic", "Logic Grid", 5.0, 10.0, CircuitStatus.CLOSED.value),
                ("cir_seed_fuse", "Fuse Protected Line", 24.0, 0.05, CircuitStatus.SHORTED.value),
            ]
            for cid, name, voltage, resistance, status in circuit_seeds:
                edges: List[Dict[str, Any]] = [
                    {"edge_id": f"{cid}_e1", "resistance": resistance * 0.4, "voltage": voltage * 0.5},
                    {"edge_id": f"{cid}_e2", "resistance": resistance * 0.6, "voltage": voltage * 0.5},
                ]
                current = voltage / max(resistance, _EPSILON) if status != CircuitStatus.OPEN.value else 0.0
                circuit = Circuit(
                    circuit_id=cid,
                    name=name,
                    nodes=[f"{cid}_n1", f"{cid}_n2", f"{cid}_n3"],
                    edges=edges,
                    voltage=voltage,
                    current=current,
                    status=status,
                    resistance=resistance,
                    power=voltage * current,
                )
                self._circuits[cid] = circuit

            # ----------------------------------------------------------
            # Conductors (4)
            # ----------------------------------------------------------
            conductor_seeds: List[Tuple[str, str, str, Tuple[float, float, float], float, Optional[str]]] = [
                ("cond_seed_copper", "Copper Trunk", ConductorType.COPPER.value,
                 (5.0, 0.0, 0.0), 10.0, "cir_seed_main"),
                ("cond_seed_alum", "Aluminum Branch", ConductorType.ALUMINUM.value,
                 (15.0, 0.0, 0.0), 6.0, "cir_seed_logic"),
                ("cond_seed_silver", "Silver Bus", ConductorType.SILVER.value,
                 (-5.0, 0.0, 0.0), 4.0, "cir_seed_main"),
                ("cond_seed_iron", "Iron Ground Strap", ConductorType.IRON.value,
                 (0.0, -5.0, 0.0), 8.0, None),
            ]
            for cond_id, name, material, pos, length, circuit_id in conductor_seeds:
                rpm = _material_resistivity(material) * 1.0e3
                conductor = Conductor(
                    conductor_id=cond_id,
                    name=name,
                    material=material,
                    resistance_per_meter=rpm,
                    position=pos,
                    length=max(_EPSILON, length),
                    connected_circuit_id=circuit_id,
                    total_resistance=rpm * max(_EPSILON, length),
                )
                self._conductors[cond_id] = conductor

            # ----------------------------------------------------------
            # Induction Coils (2)
            # ----------------------------------------------------------
            coil_seeds: List[Tuple[str, str, Tuple[float, float, float], int, float, Tuple[float, float, float]]] = [
                ("coil_seed_a", "Pickup Coil Alpha",
                 (0.0, 5.0, 1.0), 100, 0.05, (0.0, 1.0, 0.0)),
                ("coil_seed_b", "Tank Coil Beta",
                 (20.0, 0.0, 1.0), 200, 0.02, (0.0, 0.0, 1.0)),
            ]
            for coil_id, name, pos, turns, area, orient in coil_seeds:
                coil = InductionCoil(
                    coil_id=coil_id,
                    name=name,
                    position=pos,
                    turns=max(1, turns),
                    area=max(_EPSILON, area),
                    orientation=_vec_normalize(orient),
                )
                self._induction_coils[coil_id] = coil

            # ----------------------------------------------------------
            # EM Sources (2)
            # ----------------------------------------------------------
            source_seeds: List[Tuple[str, str, Tuple[float, float, float], float, float, str, bool]] = [
                ("ems_seed_ac", "AC Antenna",
                 (0.0, 0.0, 15.0), 2.45e9, 50.0, EMSourceType.AC.value, True),
                ("ems_seed_pulse", "Pulse Emitter",
                 (25.0, 0.0, 0.0), 1.0e6, 200.0, EMSourceType.PULSE.value, True),
            ]
            for sid, name, pos, freq, power, stype, active in source_seeds:
                source = EMSource(
                    source_id=sid,
                    name=name,
                    position=pos,
                    frequency=max(0.0, freq),
                    power=max(0.0, power),
                    source_type=stype,
                    active=active,
                )
                self._em_sources[sid] = source

            # ----------------------------------------------------------
            # Seed Events (6)
            # ----------------------------------------------------------
            event_seeds: List[Tuple[str, str, str]] = [
                (EMEventKind.CHARGE_REGISTERED.value, "5 baseline charges registered."),
                (EMEventKind.MAGNETIC_FIELD_REGISTERED.value, "3 baseline magnetic fields registered."),
                (EMEventKind.CIRCUIT_REGISTERED.value, "3 baseline circuits registered."),
                (EMEventKind.CONDUCTOR_REGISTERED.value, "4 baseline conductors registered."),
                (EMEventKind.EM_SOURCE_REGISTERED.value, "2 baseline EM sources registered."),
                (EMEventKind.TICK.value, "Initial electromagnetic state seeded."),
            ]
            for kind, desc in event_seeds:
                self._event_counter += 1
                self._events.append(EMEvent(
                    event_id=f"emevt_{self._event_counter:08d}",
                    timestamp=_now(),
                    event_type=kind,
                    description=desc,
                ))
            _evict_fifo_list(self._events, self._config.max_events)

            self._refresh_stats()
            self._seeded = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_event_id(self) -> str:
        """Return a monotonically increasing event identifier."""
        self._event_counter += 1
        return f"emevt_{self._event_counter:08d}"

    def _emit(
        self,
        event_type: str,
        description: str = "",
        charge_id: Optional[str] = None,
        field_id: Optional[str] = None,
        circuit_id: Optional[str] = None,
        conductor_id: Optional[str] = None,
        coil_id: Optional[str] = None,
        source_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> EMEvent:
        """Append an audit event to the rolling event log."""
        event = EMEvent(
            event_id=self._next_event_id(),
            timestamp=_now(),
            event_type=event_type,
            charge_id=charge_id,
            field_id=field_id,
            circuit_id=circuit_id,
            conductor_id=conductor_id,
            coil_id=coil_id,
            source_id=source_id,
            description=description,
            metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)
        return event

    def _refresh_stats(self) -> None:
        """Recompute the cached EMStats roll-up from the current state."""
        self._stats.total_charges = len(self._charges)
        self._stats.total_magnetic_fields = len(self._magnetic_fields)
        self._stats.total_circuits = len(self._circuits)
        self._stats.total_conductors = len(self._conductors)
        self._stats.total_induction_coils = len(self._induction_coils)
        self._stats.total_em_sources = len(self._em_sources)
        self._stats.total_field_lines = len(self._field_lines)
        self._stats.active_magnetic_fields = sum(
            1 for f in self._magnetic_fields.values() if f.active
        )
        self._stats.active_em_sources = sum(
            1 for s in self._em_sources.values() if s.active
        )
        self._stats.open_circuits = sum(
            1 for c in self._circuits.values()
            if c.status == CircuitStatus.OPEN.value
        )
        self._stats.closed_circuits = sum(
            1 for c in self._circuits.values()
            if c.status == CircuitStatus.CLOSED.value
        )
        self._stats.shorted_circuits = sum(
            1 for c in self._circuits.values()
            if c.status == CircuitStatus.SHORTED.value
        )
        self._stats.blown_circuits = sum(
            1 for c in self._circuits.values()
            if c.status == CircuitStatus.BLOWN.value
        )
        self._stats.tick_count = self._tick_count

    def _recompute_circuit(self, circuit: Circuit) -> None:
        """Recompute the aggregate resistance and power of a circuit.

        The aggregate resistance is the sum of edge resistances plus the
        resistance of any conductors currently attached to the circuit.
        Ohm's law then derives the current from the voltage (or vice
        versa) and the circuit status is refreshed.
        """
        edge_resistance = 0.0
        for edge in circuit.edges:
            edge_resistance += _safe_float(edge.get("resistance", 0.0), 0.0)
        conductor_resistance = 0.0
        for conductor in self._conductors.values():
            if conductor.connected_circuit_id == circuit.circuit_id:
                conductor_resistance += conductor.total_resistance
        circuit.resistance = edge_resistance + conductor_resistance
        if circuit.resistance < _EPSILON:
            # Treat a zero-resistance energized loop as a short.
            if abs(circuit.voltage) > _EPSILON:
                circuit.status = CircuitStatus.SHORTED.value
                circuit.current = 0.0
            else:
                circuit.current = 0.0
        else:
            circuit.current = circuit.voltage / circuit.resistance
        # Fuse check: an over-current blows the circuit.
        if abs(circuit.current) > self._config.fuse_current_threshold:
            circuit.status = CircuitStatus.BLOWN.value
            circuit.current = 0.0
        # Short check: very low resistance with applied voltage.
        if (
            circuit.resistance < self._config.short_circuit_resistance
            and abs(circuit.voltage) > _EPSILON
            and circuit.status != CircuitStatus.BLOWN.value
        ):
            circuit.status = CircuitStatus.SHORTED.value
        # Open check: zero voltage demotes a closed circuit to open.
        if (
            abs(circuit.voltage) < _EPSILON
            and circuit.status not in (
                CircuitStatus.SHORTED.value,
                CircuitStatus.BLOWN.value,
            )
        ):
            circuit.status = CircuitStatus.OPEN.value
        if circuit.status == CircuitStatus.OPEN.value:
            circuit.power = 0.0
        elif circuit.status == CircuitStatus.CLOSED.value:
            circuit.power = circuit.voltage * circuit.current
        else:
            circuit.power = 0.0
        circuit.updated_at = _now()

    def _circuit_summary(self, circuit: Circuit) -> Dict[str, Any]:
        """Build a compact summary dict describing a circuit's state.

        The summary is used by the AI helpers and the snapshot builder so
        they do not have to re-derive the same fields in multiple places.
        """
        return {
            "circuit_id": circuit.circuit_id,
            "name": circuit.name,
            "status": circuit.status,
            "voltage": circuit.voltage,
            "current": circuit.current,
            "resistance": circuit.resistance,
            "power": circuit.power,
            "node_count": len(circuit.nodes),
            "edge_count": len(circuit.edges),
            "connected_element_count": len(circuit.connected_elements),
        }

    def _validate_charge_value(self, charge_value: Any) -> Optional[str]:
        """Return an error message if a charge value is not finite.

        A None return means the value is acceptable. The check rejects
        NaN and infinity so the field integrals stay well-defined.
        """
        try:
            q = float(charge_value)
        except (TypeError, ValueError):
            return "charge_value must be a number"
        if math.isnan(q) or math.isinf(q):
            return "charge_value must be finite"
        return None

    def _charges_within_radius(
        self,
        position: Tuple[float, float, float],
        radius: float,
    ) -> List[Charge]:
        """Return all charges whose position lies within radius of a point."""
        r = max(0.0, _safe_float(radius, 0.0))
        results: List[Charge] = []
        for charge in self._charges.values():
            if _vec_distance(position, charge.position) <= r:
                results.append(charge)
        return results

    def _nearest_charge(
        self,
        position: Tuple[float, float, float],
    ) -> Optional[Charge]:
        """Return the charge closest to a position, or None when empty."""
        best: Optional[Charge] = None
        best_dist = math.inf
        for charge in self._charges.values():
            d = _vec_distance(position, charge.position)
            if d < best_dist:
                best_dist = d
                best = charge
        return best

    # ------------------------------------------------------------------
    # Charge Management
    # ------------------------------------------------------------------

    def register_charge(
        self,
        charge_id: str,
        position: Tuple[float, float, float],
        charge_value: float,
        charge_type: Optional[str] = None,
        pinned: bool = False,
        mass: float = 1.0,
    ) -> Tuple[bool, str, Optional[Charge]]:
        """Register a new point charge or replace an existing one."""
        with self._lock:
            cid = str(charge_id).strip()
            if not cid:
                return False, "invalid_charge_id", None
            pos = _coerce_position(position)
            q = _safe_float(charge_value, 0.0)
            ctype_enum = _coerce_enum(ChargeType, charge_type)
            ctype = ctype_enum.value if ctype_enum else _classify_charge_type(q)
            charge = Charge(
                charge_id=cid,
                position=pos,
                charge_value=q,
                charge_type=ctype,
                pinned=bool(pinned),
                velocity=(0.0, 0.0, 0.0),
                mass=max(_EPSILON, _safe_float(mass, 1.0)),
            )
            is_new = cid not in self._charges
            if is_new:
                _evict_fifo_dict(self._charges, self._config.max_charges)
            self._charges[cid] = charge
            self._refresh_stats()
            self._emit(
                EMEventKind.CHARGE_REGISTERED.value if is_new else EMEventKind.CHARGE_REMOVED.value,
                description=f"Charge '{cid}' registered ({ctype}, {q:.3e} C).",
                charge_id=cid,
                data={"charge_value": q, "charge_type": ctype, "pinned": charge.pinned},
            )
            return True, "registered" if is_new else "replaced", charge

    def get_charge(self, charge_id: str) -> Optional[Charge]:
        """Return the charge with the given id, or None."""
        with self._lock:
            return self._charges.get(str(charge_id).strip())

    def remove_charge(self, charge_id: str) -> Tuple[bool, str, Optional[Charge]]:
        """Remove a charge from the system."""
        with self._lock:
            cid = str(charge_id).strip()
            charge = self._charges.pop(cid, None)
            if charge is None:
                return False, "not_found", None
            self._refresh_stats()
            self._emit(
                EMEventKind.CHARGE_REMOVED.value,
                description=f"Charge '{cid}' removed.",
                charge_id=cid,
                data={"charge_value": charge.charge_value},
            )
            return True, "removed", charge

    def list_charges(
        self,
        charge_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Charge]:
        """List registered charges, optionally filtered by type."""
        with self._lock:
            target: Optional[str] = None
            if charge_type is not None:
                coerced = _coerce_enum(ChargeType, charge_type)
                target = coerced.value if coerced else str(charge_type).strip().lower()
            results: List[Charge] = []
            for charge in self._charges.values():
                if target is not None and charge.charge_type != target:
                    continue
                results.append(charge)
            cap = max(0, _safe_int(limit, 100))
            return results[:cap]

    # ------------------------------------------------------------------
    # Magnetic Field Management
    # ------------------------------------------------------------------

    def register_magnetic_field(
        self,
        field_id: str,
        position: Tuple[float, float, float],
        field_vector: Tuple[float, float, float],
        radius: float,
        field_type: Optional[str] = None,
        name: str = "",
        active: bool = True,
    ) -> Tuple[bool, str, Optional[MagneticField]]:
        """Register a spatial magnetic field region."""
        with self._lock:
            fid = str(field_id).strip()
            if not fid:
                return False, "invalid_field_id", None
            pos = _coerce_position(position)
            vec = _coerce_position(field_vector)
            r = max(_EPSILON, _safe_float(radius, 1.0))
            ftype_enum = _coerce_enum(FieldType, field_type, default=FieldType.PERMANENT)
            ftype = ftype_enum.value if ftype_enum else FieldType.PERMANENT.value
            mf = MagneticField(
                field_id=fid,
                name=str(name),
                position=pos,
                field_vector=vec,
                radius=r,
                field_type=ftype,
                active=bool(active),
                strength=_vec_length(vec),
            )
            is_new = fid not in self._magnetic_fields
            if is_new:
                _evict_fifo_dict(self._magnetic_fields, self._config.max_magnetic_fields)
            self._magnetic_fields[fid] = mf
            self._refresh_stats()
            self._emit(
                EMEventKind.MAGNETIC_FIELD_REGISTERED.value,
                description=f"Magnetic field '{fid}' registered ({ftype}, {mf.strength:.3e} T).",
                field_id=fid,
                data={"field_type": ftype, "radius": r, "strength": mf.strength},
            )
            return True, "registered" if is_new else "replaced", mf

    def get_magnetic_field(self, field_id: str) -> Optional[MagneticField]:
        """Return the magnetic field with the given id, or None."""
        with self._lock:
            return self._magnetic_fields.get(str(field_id).strip())

    def remove_magnetic_field(self, field_id: str) -> Tuple[bool, str, Optional[MagneticField]]:
        """Remove a magnetic field from the system."""
        with self._lock:
            fid = str(field_id).strip()
            mf = self._magnetic_fields.pop(fid, None)
            if mf is None:
                return False, "not_found", None
            self._refresh_stats()
            self._emit(
                EMEventKind.MAGNETIC_FIELD_REMOVED.value,
                description=f"Magnetic field '{fid}' removed.",
                field_id=fid,
            )
            return True, "removed", mf

    def list_magnetic_fields(
        self,
        field_type: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = 100,
    ) -> List[MagneticField]:
        """List magnetic fields, optionally filtered by type or state."""
        with self._lock:
            target: Optional[str] = None
            if field_type is not None:
                coerced = _coerce_enum(FieldType, field_type)
                target = coerced.value if coerced else str(field_type).strip().lower()
            results: List[MagneticField] = []
            for mf in self._magnetic_fields.values():
                if target is not None and mf.field_type != target:
                    continue
                if active is not None and mf.active != active:
                    continue
                results.append(mf)
            cap = max(0, _safe_int(limit, 100))
            return results[:cap]

    # ------------------------------------------------------------------
    # Circuit Management
    # ------------------------------------------------------------------

    def register_circuit(
        self,
        circuit_id: str,
        name: str,
        voltage: float,
        resistance: float = 0.0,
    ) -> Tuple[bool, str, Optional[Circuit]]:
        """Register a new circuit with an optional initial resistance."""
        with self._lock:
            cid = str(circuit_id).strip()
            if not cid:
                return False, "invalid_circuit_id", None
            v = _safe_float(voltage, 0.0)
            r = max(0.0, _safe_float(resistance, 0.0))
            edges: List[Dict[str, Any]] = []
            if r > _EPSILON:
                edges.append({"edge_id": f"{cid}_seed_edge", "resistance": r, "voltage": v})
            circuit = Circuit(
                circuit_id=cid,
                name=str(name),
                nodes=[f"{cid}_n1", f"{cid}_n2"],
                edges=edges,
                voltage=v,
                resistance=r,
                status=CircuitStatus.OPEN.value if abs(v) < _EPSILON else CircuitStatus.CLOSED.value,
            )
            is_new = cid not in self._circuits
            if is_new:
                _evict_fifo_dict(self._circuits, self._config.max_circuits)
            self._circuits[cid] = circuit
            self._recompute_circuit(circuit)
            self._refresh_stats()
            self._emit(
                EMEventKind.CIRCUIT_REGISTERED.value,
                description=f"Circuit '{cid}' registered (V={v:.3e}, R={r:.3e}).",
                circuit_id=cid,
                data={"voltage": v, "resistance": r, "status": circuit.status},
            )
            return True, "registered" if is_new else "replaced", circuit

    def get_circuit(self, circuit_id: str) -> Optional[Circuit]:
        """Return the circuit with the given id, or None."""
        with self._lock:
            return self._circuits.get(str(circuit_id).strip())

    def remove_circuit(self, circuit_id: str) -> Tuple[bool, str, Optional[Circuit]]:
        """Remove a circuit and detach any conductors bound to it."""
        with self._lock:
            cid = str(circuit_id).strip()
            circuit = self._circuits.pop(cid, None)
            if circuit is None:
                return False, "not_found", None
            # Detach conductors so they no longer report a stale binding.
            for conductor in self._conductors.values():
                if conductor.connected_circuit_id == cid:
                    conductor.connected_circuit_id = None
                    conductor.updated_at = _now()
            self._refresh_stats()
            self._emit(
                EMEventKind.CIRCUIT_REMOVED.value,
                description=f"Circuit '{cid}' removed.",
                circuit_id=cid,
            )
            return True, "removed", circuit

    def list_circuits(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Circuit]:
        """List circuits, optionally filtered by status."""
        with self._lock:
            target: Optional[str] = None
            if status is not None:
                coerced = _coerce_enum(CircuitStatus, status)
                target = coerced.value if coerced else str(status).strip().lower()
            results: List[Circuit] = []
            for circuit in self._circuits.values():
                if target is not None and circuit.status != target:
                    continue
                results.append(circuit)
            cap = max(0, _safe_int(limit, 100))
            return results[:cap]

    def connect_circuit_element(
        self,
        circuit_id: str,
        element_type: str,
        element_id: str,
    ) -> Tuple[bool, str, Optional[Circuit]]:
        """Attach a node, edge, or conductor to an existing circuit."""
        with self._lock:
            cid = str(circuit_id).strip()
            circuit = self._circuits.get(cid)
            if circuit is None:
                return False, "circuit_not_found", None
            eid = str(element_id).strip()
            if not eid:
                return False, "invalid_element_id", circuit
            etype = str(element_type).strip().lower()
            if etype == "node":
                if eid not in circuit.nodes:
                    circuit.nodes.append(eid)
            elif etype == "edge":
                circuit.edges.append({"edge_id": eid, "resistance": 0.0, "voltage": 0.0})
            elif etype == "conductor":
                conductor = self._conductors.get(eid)
                if conductor is None:
                    return False, "conductor_not_found", circuit
                conductor.connected_circuit_id = cid
                conductor.updated_at = _now()
                if eid not in circuit.connected_elements:
                    circuit.connected_elements.append(eid)
            else:
                return False, "invalid_element_type", circuit
            self._recompute_circuit(circuit)
            self._emit(
                EMEventKind.CIRCUIT_ELEMENT_CONNECTED.value,
                description=f"Element '{eid}' ({etype}) connected to circuit '{cid}'.",
                circuit_id=cid,
                conductor_id=eid if etype == "conductor" else None,
                data={"element_type": etype, "element_id": eid},
            )
            return True, "connected", circuit

    def disconnect_circuit_element(
        self,
        circuit_id: str,
        element_id: str,
    ) -> Tuple[bool, str, Optional[Circuit]]:
        """Detach a node, edge, or conductor from a circuit."""
        with self._lock:
            cid = str(circuit_id).strip()
            circuit = self._circuits.get(cid)
            if circuit is None:
                return False, "circuit_not_found", None
            eid = str(element_id).strip()
            removed = False
            if eid in circuit.nodes:
                circuit.nodes.remove(eid)
                removed = True
            before_edges = len(circuit.edges)
            circuit.edges = [e for e in circuit.edges if e.get("edge_id") != eid]
            if len(circuit.edges) != before_edges:
                removed = True
            if eid in circuit.connected_elements:
                circuit.connected_elements.remove(eid)
                removed = True
            conductor = self._conductors.get(eid)
            if conductor is not None and conductor.connected_circuit_id == cid:
                conductor.connected_circuit_id = None
                conductor.updated_at = _now()
                removed = True
            if not removed:
                return False, "element_not_found", circuit
            self._recompute_circuit(circuit)
            self._emit(
                EMEventKind.CIRCUIT_ELEMENT_DISCONNECTED.value,
                description=f"Element '{eid}' disconnected from circuit '{cid}'.",
                circuit_id=cid,
                conductor_id=eid,
            )
            return True, "disconnected", circuit

    # ------------------------------------------------------------------
    # Conductor Management
    # ------------------------------------------------------------------

    def register_conductor(
        self,
        conductor_id: str,
        material: str,
        position: Tuple[float, float, float],
        length: float,
        circuit_id: Optional[str] = None,
        resistance_per_meter: Optional[float] = None,
        name: str = "",
    ) -> Tuple[bool, str, Optional[Conductor]]:
        """Register a conductor segment made of the given material."""
        with self._lock:
            cond_id = str(conductor_id).strip()
            if not cond_id:
                return False, "invalid_conductor_id", None
            mat_enum = _coerce_enum(ConductorType, material, default=ConductorType.COPPER)
            mat = mat_enum.value if mat_enum else ConductorType.COPPER.value
            pos = _coerce_position(position)
            ln = max(_EPSILON, _safe_float(length, 1.0))
            if resistance_per_meter is None:
                rpm = _material_resistivity(mat) * 1.0e3
            else:
                rpm = max(0.0, _safe_float(resistance_per_meter, 0.0))
            conductor = Conductor(
                conductor_id=cond_id,
                name=str(name),
                material=mat,
                resistance_per_meter=rpm,
                position=pos,
                length=ln,
                connected_circuit_id=str(circuit_id).strip() if circuit_id else None,
                total_resistance=rpm * ln,
            )
            is_new = cond_id not in self._conductors
            if is_new:
                _evict_fifo_dict(self._conductors, self._config.max_conductors)
            self._conductors[cond_id] = conductor
            # If the conductor binds to a circuit, refresh that circuit so
            # its aggregate resistance reflects the new attachment.
            if conductor.connected_circuit_id:
                bound = self._circuits.get(conductor.connected_circuit_id)
                if bound is not None:
                    self._recompute_circuit(bound)
            self._refresh_stats()
            self._emit(
                EMEventKind.CONDUCTOR_REGISTERED.value,
                description=f"Conductor '{cond_id}' registered ({mat}, {ln:.2f} m).",
                conductor_id=cond_id,
                data={
                    "material": mat,
                    "length": ln,
                    "total_resistance": conductor.total_resistance,
                    "circuit_id": conductor.connected_circuit_id,
                },
            )
            return True, "registered" if is_new else "replaced", conductor

    def get_conductor(self, conductor_id: str) -> Optional[Conductor]:
        """Return the conductor with the given id, or None."""
        with self._lock:
            return self._conductors.get(str(conductor_id).strip())

    def remove_conductor(self, conductor_id: str) -> Tuple[bool, str, Optional[Conductor]]:
        """Remove a conductor and detach it from any bound circuit."""
        with self._lock:
            cond_id = str(conductor_id).strip()
            conductor = self._conductors.pop(cond_id, None)
            if conductor is None:
                return False, "not_found", None
            if conductor.connected_circuit_id:
                bound = self._circuits.get(conductor.connected_circuit_id)
                if bound is not None:
                    if cond_id in bound.connected_elements:
                        bound.connected_elements.remove(cond_id)
                    self._recompute_circuit(bound)
            self._refresh_stats()
            self._emit(
                EMEventKind.CONDUCTOR_REMOVED.value,
                description=f"Conductor '{cond_id}' removed.",
                conductor_id=cond_id,
            )
            return True, "removed", conductor

    def list_conductors(
        self,
        material: Optional[str] = None,
        circuit_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Conductor]:
        """List conductors, optionally filtered by material or circuit."""
        with self._lock:
            target_mat: Optional[str] = None
            if material is not None:
                coerced = _coerce_enum(ConductorType, material)
                target_mat = coerced.value if coerced else str(material).strip().lower()
            target_circuit = str(circuit_id).strip() if circuit_id else None
            results: List[Conductor] = []
            for conductor in self._conductors.values():
                if target_mat is not None and conductor.material != target_mat:
                    continue
                if target_circuit is not None and conductor.connected_circuit_id != target_circuit:
                    continue
                results.append(conductor)
            cap = max(0, _safe_int(limit, 100))
            return results[:cap]

    # ------------------------------------------------------------------
    # Induction Coil Management
    # ------------------------------------------------------------------

    def register_induction_coil(
        self,
        coil_id: str,
        position: Tuple[float, float, float],
        turns: int,
        area: float,
        orientation: Optional[Tuple[float, float, float]] = None,
        name: str = "",
    ) -> Tuple[bool, str, Optional[InductionCoil]]:
        """Register an induction coil with the given geometry."""
        with self._lock:
            coid = str(coil_id).strip()
            if not coid:
                return False, "invalid_coil_id", None
            pos = _coerce_position(position)
            t = max(1, _safe_int(turns, 1))
            a = max(_EPSILON, _safe_float(area, 1.0))
            if orientation is None:
                orient = (0.0, 0.0, 1.0)
            else:
                orient = _vec_normalize(_coerce_position(orientation))
                if orient == (0.0, 0.0, 0.0):
                    orient = (0.0, 0.0, 1.0)
            coil = InductionCoil(
                coil_id=coid,
                name=str(name),
                position=pos,
                turns=t,
                area=a,
                orientation=orient,
            )
            is_new = coid not in self._induction_coils
            if is_new:
                _evict_fifo_dict(self._induction_coils, self._config.max_induction_coils)
            self._induction_coils[coid] = coil
            self._refresh_stats()
            self._emit(
                EMEventKind.COIL_REGISTERED.value,
                description=f"Induction coil '{coid}' registered (N={t}, A={a:.3e}).",
                coil_id=coid,
                data={"turns": t, "area": a, "orientation": list(orient)},
            )
            return True, "registered" if is_new else "replaced", coil

    def get_induction_coil(self, coil_id: str) -> Optional[InductionCoil]:
        """Return the induction coil with the given id, or None."""
        with self._lock:
            return self._induction_coils.get(str(coil_id).strip())

    def remove_induction_coil(self, coil_id: str) -> Tuple[bool, str, Optional[InductionCoil]]:
        """Remove an induction coil from the system."""
        with self._lock:
            coid = str(coil_id).strip()
            coil = self._induction_coils.pop(coid, None)
            if coil is None:
                return False, "not_found", None
            self._refresh_stats()
            self._emit(
                EMEventKind.COIL_REMOVED.value,
                description=f"Induction coil '{coid}' removed.",
                coil_id=coid,
            )
            return True, "removed", coil

    def list_induction_coils(self, limit: int = 100) -> List[InductionCoil]:
        """List registered induction coils."""
        with self._lock:
            cap = max(0, _safe_int(limit, 100))
            return list(self._induction_coils.values())[:cap]

    # ------------------------------------------------------------------
    # EM Source Management
    # ------------------------------------------------------------------

    def register_em_source(
        self,
        source_id: str,
        position: Tuple[float, float, float],
        frequency: float,
        power: float,
        source_type: Optional[str] = None,
        name: str = "",
        active: bool = True,
        radius: float = 25.0,
    ) -> Tuple[bool, str, Optional[EMSource]]:
        """Register an electromagnetic emission source."""
        with self._lock:
            sid = str(source_id).strip()
            if not sid:
                return False, "invalid_source_id", None
            pos = _coerce_position(position)
            freq = max(0.0, _safe_float(frequency, 0.0))
            pwr = max(0.0, _safe_float(power, 0.0))
            stype_enum = _coerce_enum(EMSourceType, source_type, default=EMSourceType.STATIC)
            stype = stype_enum.value if stype_enum else EMSourceType.STATIC.value
            source = EMSource(
                source_id=sid,
                name=str(name),
                position=pos,
                frequency=freq,
                power=pwr,
                source_type=stype,
                active=bool(active),
                radius=max(_EPSILON, _safe_float(radius, 25.0)),
            )
            is_new = sid not in self._em_sources
            if is_new:
                _evict_fifo_dict(self._em_sources, self._config.max_em_sources)
            self._em_sources[sid] = source
            self._refresh_stats()
            self._emit(
                EMEventKind.EM_SOURCE_REGISTERED.value,
                description=f"EM source '{sid}' registered ({stype}, {freq:.3e} Hz).",
                source_id=sid,
                data={"frequency": freq, "power": pwr, "source_type": stype},
            )
            return True, "registered" if is_new else "replaced", source

    def get_em_source(self, source_id: str) -> Optional[EMSource]:
        """Return the EM source with the given id, or None."""
        with self._lock:
            return self._em_sources.get(str(source_id).strip())

    def remove_em_source(self, source_id: str) -> Tuple[bool, str, Optional[EMSource]]:
        """Remove an EM source from the system."""
        with self._lock:
            sid = str(source_id).strip()
            source = self._em_sources.pop(sid, None)
            if source is None:
                return False, "not_found", None
            self._refresh_stats()
            self._emit(
                EMEventKind.EM_SOURCE_REMOVED.value,
                description=f"EM source '{sid}' removed.",
                source_id=sid,
            )
            return True, "removed", source

    def list_em_sources(
        self,
        source_type: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = 100,
    ) -> List[EMSource]:
        """List EM sources, optionally filtered by type or state."""
        with self._lock:
            target: Optional[str] = None
            if source_type is not None:
                coerced = _coerce_enum(EMSourceType, source_type)
                target = coerced.value if coerced else str(source_type).strip().lower()
            results: List[EMSource] = []
            for source in self._em_sources.values():
                if target is not None and source.source_type != target:
                    continue
                if active is not None and source.active != active:
                    continue
                results.append(source)
            cap = max(0, _safe_int(limit, 100))
            return results[:cap]

    # ------------------------------------------------------------------
    # Field Computations
    # ------------------------------------------------------------------

    def _electric_field_at(
        self,
        position: Tuple[float, float, float],
        exclude: Optional[str] = None,
    ) -> Tuple[Tuple[float, float, float], List[str]]:
        """Sum Coulomb electric field contributions at a point.

        Returns the field vector and the list of charge ids that
        contributed. The optional ``exclude`` id skips a charge so a
        charge never evaluates its own self-field.
        """
        k = self._config.coulomb_constant
        accumulated = (0.0, 0.0, 0.0)
        contributors: List[str] = []
        for charge in self._charges.values():
            if exclude is not None and charge.charge_id == exclude:
                continue
            delta = _vec_sub(position, charge.position)
            dist = _vec_length(delta)
            if dist < _EPSILON:
                # Avoid singular self-field; treat as negligible.
                continue
            magnitude = k * charge.charge_value / (dist * dist)
            direction = _vec_scale(delta, 1.0 / dist)
            contribution = _vec_scale(direction, magnitude)
            accumulated = _vec_add(accumulated, contribution)
            contributors.append(charge.charge_id)
        return accumulated, contributors

    def _magnetic_field_at(
        self,
        position: Tuple[float, float, float],
    ) -> Tuple[Tuple[float, float, float], List[str]]:
        """Sum magnetic field contributions at a point.

        Inside a field's radius the contribution equals the stored
        field vector. Outside, the contribution falls off: permanent
        magnets use a dipole-like 1/r^3 curve while electromagnets and
        solenoids use a gentler 1/r^2 curve.
        """
        accumulated = (0.0, 0.0, 0.0)
        contributors: List[str] = []
        for mf in self._magnetic_fields.values():
            if not mf.active:
                continue
            delta = _vec_sub(position, mf.position)
            dist = _vec_length(delta)
            radius = max(_EPSILON, mf.radius)
            if dist <= radius:
                contribution = mf.field_vector
            else:
                ratio = radius / dist
                if mf.field_type == FieldType.PERMANENT.value:
                    falloff = ratio * ratio * ratio
                else:
                    falloff = ratio * ratio
                contribution = _vec_scale(mf.field_vector, falloff)
            accumulated = _vec_add(accumulated, contribution)
            contributors.append(mf.field_id)
        return accumulated, contributors

    def compute_electric_field(
        self,
        position: Tuple[float, float, float],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the electric field vector at a position (V/m).

        Evaluates ``E = k * q / r^2`` for every registered charge and
        sums the resulting vectors. The direction of each contribution
        is radial from the charge to the sample point; the sign of ``q``
        is carried by the charge value itself so a negative charge
        naturally produces an inward-pointing contribution.
        """
        with self._lock:
            pos = _coerce_position(position)
            vec, contributors = self._electric_field_at(pos)
            magnitude = _vec_length(vec)
            self._emit(
                EMEventKind.EMF_COMPUTED.value,
                description="Electric field sampled.",
                data={
                    "position": list(pos),
                    "vector": list(vec),
                    "magnitude": magnitude,
                    "contributors": contributors,
                    "field_kind": "electric",
                },
            )
            return True, "ok", {
                "position": list(pos),
                "vector": list(vec),
                "magnitude": magnitude,
                "contributors": contributors,
                "strength_label": _strength_label(magnitude),
            }

    def compute_magnetic_field(
        self,
        position: Tuple[float, float, float],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the magnetic field vector at a position (Tesla).

        Sums the contributions of every active magnetic field. Inside a
        field's radius the contribution equals the stored field vector;
        outside, permanent magnets attenuate as 1/r^3 while
        electromagnets and solenoids attenuate as 1/r^2. The superposition
        of overlapping fields produces the final vector at the sample point.
        """
        with self._lock:
            pos = _coerce_position(position)
            vec, contributors = self._magnetic_field_at(pos)
            magnitude = _vec_length(vec)
            self._emit(
                EMEventKind.EMF_COMPUTED.value,
                description="Magnetic field sampled.",
                data={
                    "position": list(pos),
                    "vector": list(vec),
                    "magnitude": magnitude,
                    "contributors": contributors,
                    "field_kind": "magnetic",
                },
            )
            return True, "ok", {
                "position": list(pos),
                "vector": list(vec),
                "magnitude": magnitude,
                "contributors": contributors,
                "strength_label": _strength_label(magnitude),
            }

    def compute_force(self, charge_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the Lorentz force on a charge.

        The Lorentz force combines the electric and magnetic
        contributions: ``F = q * E + q * (v x B)``. The electric term
        ``q * E`` is Coulomb's force on the charge due to every other
        charge in the system. The magnetic term ``q * (v x B)`` is the
        cross product of the charge velocity with the local magnetic
        flux density, scaled by the charge value. The result is stored
        on the charge so the tick loop can integrate it.
        """
        with self._lock:
            cid = str(charge_id).strip()
            charge = self._charges.get(cid)
            if charge is None:
                return False, "not_found", {}
            e_vec, e_contributors = self._electric_field_at(charge.position, exclude=cid)
            b_vec, b_contributors = self._magnetic_field_at(charge.position)
            # Electric component: F_e = q * E
            electric_force = _vec_scale(e_vec, charge.charge_value)
            # Magnetic component: F_b = q * (v x B)
            magnetic_force = _vec_scale(
                _vec_cross(charge.velocity, b_vec),
                charge.charge_value,
            )
            total = _vec_add(electric_force, magnetic_force)
            charge.net_force = total
            charge.updated_at = _now()
            self._stats.total_force_computations += 1
            self._emit(
                EMEventKind.EMF_COMPUTED.value,
                description=f"Lorentz force computed for charge '{cid}'.",
                charge_id=cid,
                data={
                    "electric_force": list(electric_force),
                    "magnetic_force": list(magnetic_force),
                    "total_force": list(total),
                    "electric_contributors": e_contributors,
                    "magnetic_contributors": b_contributors,
                },
            )
            return True, "ok", {
                "charge_id": cid,
                "electric_force": list(electric_force),
                "magnetic_force": list(magnetic_force),
                "total_force": list(total),
                "magnitude": _vec_length(total),
                "electric_contributors": e_contributors,
                "magnetic_contributors": b_contributors,
            }

    # ------------------------------------------------------------------
    # Induction & EMF
    # ------------------------------------------------------------------

    def _flux_through_coil(
        self,
        coil: InductionCoil,
    ) -> Tuple[float, Tuple[float, float, float]]:
        """Compute the magnetic flux through a coil.

        Flux is ``Phi = B . (A * n_hat)`` where ``n_hat`` is the coil's
        unit normal. Returns the scalar flux and the local B vector.
        """
        b_vec, _ = self._magnetic_field_at(coil.position)
        normal = _vec_normalize(coil.orientation)
        if normal == (0.0, 0.0, 0.0):
            normal = (0.0, 0.0, 1.0)
        flux = coil.area * _vec_dot(b_vec, normal)
        return flux, b_vec

    def compute_emf(self, coil_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the induced EMF across a coil via Faraday's law.

        ``EMF = -N * dPhi/dt``. The magnetic flux ``Phi`` is obtained
        from ``Phi = B . (A * n_hat)`` where ``B`` is the local magnetic
        field, ``A`` is the coil area, and ``n_hat`` is the coil's unit
        normal. The previous flux is retained on the coil so the time
        derivative is the difference between the current and previous
        flux divided by the last known dt. The negative sign reflects
        Lenz's law: the induced EMF opposes the change in flux.
        """
        with self._lock:
            coid = str(coil_id).strip()
            coil = self._induction_coils.get(coid)
            if coil is None:
                return False, "not_found", {}
            if not self._config.enable_induction:
                return True, "disabled", {
                    "coil_id": coid,
                    "flux": coil.magnetic_flux,
                    "previous_flux": coil.previous_flux,
                    "emf": 0.0,
                    "dt": 0.0,
                    "b_vector": [0.0, 0.0, 0.0],
                }
            flux, b_vec = self._flux_through_coil(coil)
            previous = coil.magnetic_flux
            dt = max(_EPSILON, self._last_dt)
            d_flux = flux - previous
            emf = -coil.turns * d_flux / dt
            coil.previous_flux = previous
            coil.magnetic_flux = flux
            coil.induced_emf = emf
            coil.updated_at = _now()
            self._stats.total_emf_computations += 1
            self._emit(
                EMEventKind.EMF_COMPUTED.value,
                description=f"EMF computed for coil '{coid}' ({emf:.3e} V).",
                coil_id=coid,
                data={
                    "flux": flux,
                    "previous_flux": previous,
                    "d_flux": d_flux,
                    "emf": emf,
                    "dt": dt,
                    "b_vector": list(b_vec),
                },
            )
            return True, "ok", {
                "coil_id": coid,
                "flux": flux,
                "previous_flux": previous,
                "d_flux": d_flux,
                "emf": emf,
                "dt": dt,
                "b_vector": list(b_vec),
                "turns": coil.turns,
                "area": coil.area,
            }

    def check_induction(self, coil_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Check whether a coil's induced EMF exceeds the induction threshold."""
        with self._lock:
            ok, msg, payload = self.compute_emf(coil_id)
            if not ok:
                return ok, msg, payload
            emf = _safe_float(payload.get("emf", 0.0), 0.0)
            threshold = self._config.induction_emf_threshold
            induced = abs(emf) > threshold
            if induced:
                self._stats.total_inductions_detected += 1
                self._emit(
                    EMEventKind.INDUCTION_DETECTED.value,
                    description=f"Induction detected on coil '{coil_id}' ({emf:.3e} V).",
                    coil_id=str(coil_id).strip(),
                    data={"emf": emf, "threshold": threshold},
                )
            payload["induced"] = induced
            payload["threshold"] = threshold
            return True, "induced" if induced else "quiet", payload

    # ------------------------------------------------------------------
    # Circuit Operations
    # ------------------------------------------------------------------

    def apply_voltage(
        self,
        circuit_id: str,
        voltage: float,
    ) -> Tuple[bool, str, Optional[Circuit]]:
        """Apply a voltage to a circuit and recompute its state.

        Uses Ohm's law (``I = V / R``) to derive the new current from the
        applied voltage and the circuit's aggregate resistance. The
        circuit status is then refreshed: a very low resistance with an
        applied voltage flags the circuit as shorted, and an over-current
        above the fuse threshold blows it. A blown circuit rejects
        further voltage applications.
        """
        with self._lock:
            cid = str(circuit_id).strip()
            circuit = self._circuits.get(cid)
            if circuit is None:
                return False, "not_found", None
            if circuit.status == CircuitStatus.BLOWN.value:
                return False, "circuit_blown", circuit
            v = _safe_float(voltage, 0.0)
            circuit.voltage = v
            self._recompute_circuit(circuit)
            event_kind = EMEventKind.VOLTAGE_APPLIED.value
            if circuit.status == CircuitStatus.SHORTED.value:
                event_kind = EMEventKind.SHORT_CIRCUIT_DETECTED.value
                self._stats.total_short_circuits += 1
            elif circuit.status == CircuitStatus.BLOWN.value:
                event_kind = EMEventKind.CIRCUIT_BLOWN.value
            self._emit(
                event_kind,
                description=f"Voltage {v:.3e} V applied to circuit '{cid}'.",
                circuit_id=cid,
                data={
                    "voltage": v,
                    "current": circuit.current,
                    "resistance": circuit.resistance,
                    "status": circuit.status,
                    "power": circuit.power,
                },
            )
            return True, circuit.status, circuit

    def apply_current(
        self,
        circuit_id: str,
        current: float,
    ) -> Tuple[bool, str, Optional[Circuit]]:
        """Drive a circuit with a current source and recompute its state.

        The voltage is back-derived from Ohm's law (``V = I * R``) so
        that the circuit's stored voltage remains consistent with the
        applied current and aggregate resistance.
        """
        with self._lock:
            cid = str(circuit_id).strip()
            circuit = self._circuits.get(cid)
            if circuit is None:
                return False, "not_found", None
            if circuit.status == CircuitStatus.BLOWN.value:
                return False, "circuit_blown", circuit
            i = _safe_float(current, 0.0)
            circuit.current = i
            circuit.voltage = i * circuit.resistance
            self._recompute_circuit(circuit)
            # ``_recompute_circuit`` may overwrite current from voltage;
            # restore the driven current for an active (non-shorted,
            # non-blown) circuit so the caller's intent is honored.
            if circuit.status == CircuitStatus.CLOSED.value:
                circuit.current = i
                circuit.power = circuit.voltage * i
            event_kind = EMEventKind.CURRENT_APPLIED.value
            if circuit.status == CircuitStatus.SHORTED.value:
                event_kind = EMEventKind.SHORT_CIRCUIT_DETECTED.value
                self._stats.total_short_circuits += 1
            elif circuit.status == CircuitStatus.BLOWN.value:
                event_kind = EMEventKind.CIRCUIT_BLOWN.value
            self._emit(
                event_kind,
                description=f"Current {i:.3e} A applied to circuit '{cid}'.",
                circuit_id=cid,
                data={
                    "current": i,
                    "voltage": circuit.voltage,
                    "resistance": circuit.resistance,
                    "status": circuit.status,
                    "power": circuit.power,
                },
            )
            return True, circuit.status, circuit

    def check_short_circuit(self, circuit_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Inspect a circuit for short-circuit conditions.

        A circuit is considered shorted when its aggregate resistance
        falls below the configured ``short_circuit_resistance`` threshold
        while a non-zero voltage is applied. The check also reports
        whether the circuit has blown its fuse so callers can distinguish
        a recoverable short from a permanently damaged circuit.
        """
        with self._lock:
            cid = str(circuit_id).strip()
            circuit = self._circuits.get(cid)
            if circuit is None:
                return False, "not_found", {}
            threshold = self._config.short_circuit_resistance
            is_short = (
                circuit.resistance < threshold
                and abs(circuit.voltage) > _EPSILON
            )
            is_blown = circuit.status == CircuitStatus.BLOWN.value
            if is_short and not is_blown:
                self._stats.total_short_circuits += 1
                self._emit(
                    EMEventKind.SHORT_CIRCUIT_DETECTED.value,
                    description=f"Short-circuit detected on '{cid}' (R={circuit.resistance:.3e}).",
                    circuit_id=cid,
                    data={"resistance": circuit.resistance, "threshold": threshold},
                )
            return True, "short" if is_short else "ok", {
                "circuit_id": cid,
                "resistance": circuit.resistance,
                "threshold": threshold,
                "is_short": is_short,
                "is_blown": is_blown,
                "voltage": circuit.voltage,
                "current": circuit.current,
                "status": circuit.status,
            }

    # ------------------------------------------------------------------
    # Field Visualization
    # ------------------------------------------------------------------

    def get_field_lines(
        self,
        position: Tuple[float, float, float],
        field_type: Optional[str] = None,
        count: int = 8,
    ) -> List[FieldLine]:
        """Trace field lines radiating from a position.

        The tracer steps along the local field direction. For electric
        fields the step direction follows the E vector; for magnetic
        fields it follows the B vector. A small probe offset is used to
        seed each line so the requested number of lines fan out around
        the start position.
        """
        with self._lock:
            pos = _coerce_position(position)
            ftype_enum = _coerce_enum(FieldLineType, field_type, default=FieldLineType.ELECTRIC)
            ftype = ftype_enum.value if ftype_enum else FieldLineType.ELECTRIC.value
            line_count = max(1, _safe_int(count, 8))
            step = max(_EPSILON, self._config.field_line_step)
            max_steps = max(1, _safe_int(self._config.field_line_max_steps, 50))
            lines: List[FieldLine] = []
            # Seed directions distributed on a unit sphere around the start.
            for i in range(line_count):
                angle = (2.0 * math.pi * i) / max(1, line_count)
                if ftype == FieldLineType.ELECTRIC.value:
                    seed_dir = (math.cos(angle), math.sin(angle), 0.0)
                else:
                    seed_dir = (0.0, math.cos(angle), math.sin(angle))
                start = _vec_add(pos, _vec_scale(_vec_normalize(seed_dir), step))
                segments: List[Dict[str, Any]] = [{"point": list(pos)}]
                current = start
                last_strength = 0.0
                for _ in range(max_steps):
                    if ftype == FieldLineType.ELECTRIC.value:
                        vec, _ = self._electric_field_at(current)
                    else:
                        vec, _ = self._magnetic_field_at(current)
                    strength = _vec_length(vec)
                    last_strength = strength
                    if strength < _EPSILON:
                        break
                    direction = _vec_scale(vec, 1.0 / strength)
                    nxt = _vec_add(current, _vec_scale(direction, step))
                    segments.append({"point": list(nxt), "strength": strength})
                    current = nxt
                self._field_line_counter += 1
                line = FieldLine(
                    line_id=f"fl_{self._field_line_counter:08d}",
                    start_position=pos,
                    end_position=current,
                    field_strength=last_strength,
                    field_type=ftype,
                    segments=segments,
                )
                self._field_lines[line.line_id] = line
                lines.append(line)
            _evict_fifo_dict(self._field_lines, self._config.max_field_lines)
            self._refresh_stats()
            self._emit(
                EMEventKind.FIELD_LINE_GENERATED.value,
                description=f"{len(lines)} {ftype} field lines traced from {list(pos)}.",
                data={"count": len(lines), "field_type": ftype, "start": list(pos)},
            )
            return lines

    def get_field_map(self, resolution: int = 16) -> Dict[str, Any]:
        """Sample the electric field magnitude on a regular 3D grid.

        The grid spans the configured ``field_map_bounds`` and is
        downsampled to ``resolution`` samples per axis. Each cell holds
        the magnitude of the electric field vector at the cell center,
        computed by summing the Coulomb contributions of every charge.
        The result is suitable for feeding into a heatmap renderer or a
        gameplay region analyzer.
        """
        with self._lock:
            res = max(2, _safe_int(resolution, self._config.field_map_resolution))
            bounds = self._config.field_map_bounds
            min_x, min_y, min_z, max_x, max_y, max_z = bounds
            span_x = max(_EPSILON, max_x - min_x)
            span_y = max(_EPSILON, max_y - min_y)
            span_z = max(_EPSILON, max_z - min_z)
            grid: List[List[List[float]]] = []
            max_magnitude = 0.0
            for iz in range(res):
                plane: List[List[float]] = []
                z = min_z + (iz + 0.5) / res * span_z
                for iy in range(res):
                    row: List[float] = []
                    y = min_y + (iy + 0.5) / res * span_y
                    for ix in range(res):
                        x = min_x + (ix + 0.5) / res * span_x
                        vec, _ = self._electric_field_at((x, y, z))
                        m = _vec_length(vec)
                        if m > max_magnitude:
                            max_magnitude = m
                        row.append(m)
                    plane.append(row)
                grid.append(plane)
            return {
                "resolution": res,
                "bounds": list(bounds),
                "field_kind": "electric",
                "grid": grid,
                "max_magnitude": max_magnitude,
                "strength_label": _strength_label(max_magnitude),
            }

    def get_visualization_data(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a compact rendering payload for the whole field.

        When ``zone_id`` is provided, only entities whose metadata
        carries a matching ``zone`` tag are included. Otherwise every
        registered entity is returned.
        """
        with self._lock:
            def _in_zone(meta: Dict[str, Any]) -> bool:
                if zone_id is None:
                    return True
                return str(meta.get("zone", "")).strip() == str(zone_id).strip()

            charges = [c.to_dict() for c in self._charges.values() if _in_zone(c.metadata)]
            fields = [f.to_dict() for f in self._magnetic_fields.values() if _in_zone(f.metadata)]
            circuits = [c.to_dict() for c in self._circuits.values() if _in_zone(c.metadata)]
            conductors = [c.to_dict() for c in self._conductors.values() if _in_zone(c.metadata)]
            coils = [c.to_dict() for c in self._induction_coils.values() if _in_zone(c.metadata)]
            sources = [s.to_dict() for s in self._em_sources.values() if _in_zone(s.metadata)]
            return {
                "zone_id": zone_id,
                "charges": charges,
                "magnetic_fields": fields,
                "circuits": circuits,
                "conductors": conductors,
                "induction_coils": coils,
                "em_sources": sources,
                "counts": {
                    "charges": len(charges),
                    "magnetic_fields": len(fields),
                    "circuits": len(circuits),
                    "conductors": len(conductors),
                    "induction_coils": len(coils),
                    "em_sources": len(sources),
                },
            }

    # ------------------------------------------------------------------
    # AI Helpers
    # ------------------------------------------------------------------

    def ai_assess_field_strength(
        self,
        position: Tuple[float, float, float],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Assess the combined field strength at a position.

        The helper samples both the electric and magnetic field, scores
        the combined intensity, and returns a qualitative label together
        with a recommendation that gameplay scripts can act on.
        """
        with self._lock:
            pos = _coerce_position(position)
            e_vec, e_contrib = self._electric_field_at(pos)
            b_vec, b_contrib = self._magnetic_field_at(pos)
            e_mag = _vec_length(e_vec)
            b_mag = _vec_length(b_vec)
            # Normalize each magnitude to a 0..1 score using a soft log
            # curve so that very large and very small values both map
            # cleanly into the assessment bands.
            e_score = _clamp(math.log10(1.0 + e_mag) / 12.0, 0.0, 1.0)
            b_score = _clamp(math.log10(1.0 + b_mag) / 6.0, 0.0, 1.0)
            combined = _clamp(0.5 * (e_score + b_score), 0.0, 1.0)
            label = _risk_label(combined)
            recommendation: str
            if label == "high":
                recommendation = "Deploy shielding and restrict player access."
            elif label == "moderate":
                recommendation = "Monitor exposure and prepare countermeasures."
            elif label == "low":
                recommendation = "Safe for standard gameplay interactions."
            else:
                recommendation = "No action required."
            self._emit(
                EMEventKind.AI_ASSESSMENT.value,
                description=f"AI field assessment at {list(pos)} ({label}).",
                data={
                    "position": list(pos),
                    "e_magnitude": e_mag,
                    "b_magnitude": b_mag,
                    "combined_score": combined,
                    "label": label,
                },
            )
            return True, label, {
                "position": list(pos),
                "electric_vector": list(e_vec),
                "magnetic_vector": list(b_vec),
                "electric_magnitude": e_mag,
                "magnetic_magnitude": b_mag,
                "electric_label": _strength_label(e_mag),
                "magnetic_label": _strength_label(b_mag),
                "combined_score": combined,
                "label": label,
                "recommendation": recommendation,
                "electric_contributors": e_contrib,
                "magnetic_contributors": b_contrib,
            }

    def ai_optimize_circuit(self, circuit_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Suggest optimizations to reduce a circuit's power loss.

        The analysis identifies high-resistance edges, flags conductor
        materials that could be swapped for a lower-resistivity
        alternative, and estimates the power savings achievable by
        adopting the suggested changes.
        """
        with self._lock:
            cid = str(circuit_id).strip()
            circuit = self._circuits.get(cid)
            if circuit is None:
                return False, "not_found", {}
            # Rank edges by resistance.
            edges_ranked = sorted(
                circuit.edges,
                key=lambda e: _safe_float(e.get("resistance", 0.0), 0.0),
                reverse=True,
            )
            hot_edges = [
                {
                    "edge_id": e.get("edge_id", ""),
                    "resistance": _safe_float(e.get("resistance", 0.0), 0.0),
                }
                for e in edges_ranked[:3]
            ]
            # Suggest material swaps for attached conductors.
            suggestions: List[Dict[str, Any]] = []
            for conductor in self._conductors.values():
                if conductor.connected_circuit_id != cid:
                    continue
                current_r = conductor.total_resistance
                best_material = conductor.material
                best_r = current_r
                for mat, rho in _MATERIAL_RESISTIVITY.items():
                    if mat == conductor.material:
                        continue
                    candidate_r = rho * 1.0e3 * conductor.length
                    if candidate_r < best_r:
                        best_r = candidate_r
                        best_material = mat
                if best_material != conductor.material:
                    suggestions.append({
                        "conductor_id": conductor.conductor_id,
                        "current_material": conductor.material,
                        "suggested_material": best_material,
                        "current_resistance": current_r,
                        "suggested_resistance": best_r,
                        "resistance_reduction": current_r - best_r,
                    })
            current_power = circuit.power
            # Estimate savings from the suggested conductor swaps alone.
            total_reduction = sum(s["resistance_reduction"] for s in suggestions)
            new_resistance = max(_EPSILON, circuit.resistance - total_reduction)
            optimized_current = (
                circuit.voltage / new_resistance
                if circuit.status == CircuitStatus.CLOSED.value
                else 0.0
            )
            optimized_power = circuit.voltage * optimized_current
            power_delta = optimized_power - current_power
            strategy: str
            if total_reduction > _EPSILON:
                strategy = "replace_conductors"
            elif hot_edges and hot_edges[0]["resistance"] > 0.0:
                strategy = "redistribute_edges"
            else:
                strategy = "none"
            self._emit(
                EMEventKind.AI_ASSESSMENT.value,
                description=f"AI circuit optimization for '{cid}' ({strategy}).",
                circuit_id=cid,
                data={
                    "strategy": strategy,
                    "power_delta": power_delta,
                    "suggestion_count": len(suggestions),
                },
            )
            return True, strategy, {
                "circuit_id": cid,
                "current_resistance": circuit.resistance,
                "optimized_resistance": new_resistance,
                "current_power": current_power,
                "optimized_power": optimized_power,
                "power_delta": power_delta,
                "hot_edges": hot_edges,
                "conductor_suggestions": suggestions,
                "strategy": strategy,
            }

    def ai_predict_interference(
        self,
        source_id: str,
        radius: float,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Predict EM interference from a source within a radius.

        Each nearby charge, coil, and circuit is scored by a coupling
        model that combines distance, source power, and (for AC and
        pulse sources) frequency alignment. The result lists the most
        affected entities and an aggregate risk label.
        """
        with self._lock:
            sid = str(source_id).strip()
            source = self._em_sources.get(sid)
            if source is None:
                return False, "not_found", {}
            r = max(_EPSILON, _safe_float(radius, source.radius))
            wavelength = (
                _SPEED_OF_LIGHT / source.frequency
                if source.frequency > _EPSILON
                else float("inf")
            )
            affected_charges: List[Dict[str, Any]] = []
            for charge in self._charges.values():
                dist = _vec_distance(source.position, charge.position)
                if dist > r:
                    continue
                # Coupling falls off with square of distance; frequency
                # modulates the score for AC/pulse sources.
                distance_factor = 1.0 - _clamp(dist / r, 0.0, 1.0)
                freq_factor = 1.0
                if source.source_type in (EMSourceType.AC.value, EMSourceType.PULSE.value):
                    freq_factor = 1.0 + math.log10(1.0 + source.frequency) / 12.0
                power_factor = _clamp(math.log10(1.0 + source.power) / 4.0, 0.0, 1.0)
                score = _clamp(distance_factor * freq_factor * power_factor, 0.0, 1.0)
                affected_charges.append({
                    "entity_type": "charge",
                    "entity_id": charge.charge_id,
                    "distance": dist,
                    "score": score,
                })
            affected_charges.sort(key=lambda e: e["score"], reverse=True)
            affected_coils: List[Dict[str, Any]] = []
            for coil in self._induction_coils.values():
                dist = _vec_distance(source.position, coil.position)
                if dist > r:
                    continue
                distance_factor = 1.0 - _clamp(dist / r, 0.0, 1.0)
                # Coils are extra sensitive to AC sources at frequencies
                # comparable to their effective pickup area.
                freq_factor = 1.0
                if source.source_type == EMSourceType.AC.value:
                    freq_factor = 1.0 + math.log10(1.0 + source.frequency) / 10.0
                power_factor = _clamp(math.log10(1.0 + source.power) / 4.0, 0.0, 1.0)
                score = _clamp(distance_factor * freq_factor * power_factor, 0.0, 1.0)
                affected_coils.append({
                    "entity_type": "coil",
                    "entity_id": coil.coil_id,
                    "distance": dist,
                    "score": score,
                    "turns": coil.turns,
                })
            affected_coils.sort(key=lambda e: e["score"], reverse=True)
            affected_circuits: List[Dict[str, Any]] = []
            for circuit in self._circuits.values():
                # Circuits do not have a single position; use the average
                # of their conductor positions as a representative point.
                positions: List[Tuple[float, float, float]] = []
                for conductor in self._conductors.values():
                    if conductor.connected_circuit_id == circuit.circuit_id:
                        positions.append(conductor.position)
                if not positions:
                    continue
                avg = (
                    sum(p[0] for p in positions) / len(positions),
                    sum(p[1] for p in positions) / len(positions),
                    sum(p[2] for p in positions) / len(positions),
                )
                dist = _vec_distance(source.position, avg)
                if dist > r:
                    continue
                distance_factor = 1.0 - _clamp(dist / r, 0.0, 1.0)
                power_factor = _clamp(math.log10(1.0 + source.power) / 4.0, 0.0, 1.0)
                score = _clamp(distance_factor * power_factor, 0.0, 1.0)
                affected_circuits.append({
                    "entity_type": "circuit",
                    "entity_id": circuit.circuit_id,
                    "distance": dist,
                    "score": score,
                    "status": circuit.status,
                })
            affected_circuits.sort(key=lambda e: e["score"], reverse=True)
            all_scores = (
                [e["score"] for e in affected_charges]
                + [e["score"] for e in affected_coils]
                + [e["score"] for e in affected_circuits]
            )
            aggregate = (
                sum(all_scores) / len(all_scores) if all_scores else 0.0
            )
            label = _risk_label(aggregate)
            self._emit(
                EMEventKind.AI_ASSESSMENT.value,
                description=f"AI interference prediction for source '{sid}' ({label}).",
                source_id=sid,
                data={
                    "radius": r,
                    "aggregate_score": aggregate,
                    "label": label,
                    "affected_count": len(all_scores),
                },
            )
            return True, label, {
                "source_id": sid,
                "source_type": source.source_type,
                "frequency": source.frequency,
                "power": source.power,
                "wavelength": wavelength,
                "radius": r,
                "affected_charges": affected_charges[:10],
                "affected_coils": affected_coils[:10],
                "affected_circuits": affected_circuits[:10],
                "aggregate_score": aggregate,
                "label": label,
                "total_affected": len(all_scores),
            }

    # ------------------------------------------------------------------
    # Events & Lifecycle
    # ------------------------------------------------------------------

    def list_events(
        self,
        kind: Optional[str] = None,
        limit: int = 100,
    ) -> List[EMEvent]:
        """Return recent events, optionally filtered by event kind."""
        with self._lock:
            target: Optional[str] = None
            if kind is not None:
                coerced = _coerce_enum(EMEventKind, kind)
                target = coerced.value if coerced else str(kind).strip().lower()
            results: List[EMEvent] = []
            for event in reversed(self._events):
                if target is not None and event.event_type != target:
                    continue
                results.append(event)
                if len(results) >= max(0, _safe_int(limit, 100)):
                    break
            return results

    def reset_field(self, zone_id: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Reset the field, optionally scoped to a metadata zone tag.

        With no ``zone_id`` the entire system is cleared and re-seeded
        with the baseline data. When a zone id is supplied, only
        entities whose metadata carries a matching ``zone`` tag are
        removed, leaving the rest of the simulation intact.
        """
        with self._lock:
            if zone_id is None:
                self._charges.clear()
                self._magnetic_fields.clear()
                self._circuits.clear()
                self._conductors.clear()
                self._induction_coils.clear()
                self._em_sources.clear()
                self._field_lines.clear()
                self._events.clear()
                self._stats = EMStats()
                self._tick_count = 0
                self._event_counter = 0
                self._field_line_counter = 0
                self._global_time = 0.0
                self._last_dt = self._config.default_dt
                self._seeded = False
                self._seed_data()
                self._emit(
                    EMEventKind.FIELD_RESET.value,
                    description="Electromagnetic field reset and re-seeded.",
                )
                self._refresh_stats()
                return True, "reset", {
                    "zone_id": None,
                    "charges": len(self._charges),
                    "magnetic_fields": len(self._magnetic_fields),
                    "circuits": len(self._circuits),
                }
            target = str(zone_id).strip()
            removed = {"charges": 0, "magnetic_fields": 0, "circuits": 0,
                       "conductors": 0, "induction_coils": 0, "em_sources": 0}
            for store, key, kind in (
                (self._charges, "charges", "charge_id"),
                (self._magnetic_fields, "magnetic_fields", "field_id"),
                (self._circuits, "circuits", "circuit_id"),
                (self._conductors, "conductors", "conductor_id"),
                (self._induction_coils, "induction_coils", "coil_id"),
                (self._em_sources, "em_sources", "source_id"),
            ):
                to_remove = [
                    eid for eid, ent in store.items()
                    if str(ent.metadata.get("zone", "")).strip() == target
                ]
                for eid in to_remove:
                    store.pop(eid, None)
                    removed[key] += 1
            self._refresh_stats()
            self._emit(
                EMEventKind.FIELD_RESET.value,
                description=f"Field reset for zone '{target}'.",
                data={"zone_id": target, "removed": removed},
            )
            return True, "reset_zone", {"zone_id": target, "removed": removed}

    def tick(self, dt: Optional[float] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """Advance the electromagnetic simulation by one time step.

        The tick refreshes coil flux history so subsequent EMF queries
        have a meaningful ``dPhi`` to differentiate, and integrates free
        charge motion under the Lorentz force using an explicit Euler
        step. Pinned charges are skipped so designers can anchor field
        sources.
        """
        with self._lock:
            step = max(_EPSILON, _safe_float(dt, self._config.default_dt))
            self._last_dt = step
            self._tick_count += 1
            self._global_time += step
            moved = 0
            if self._config.enable_charge_dynamics:
                # Compute forces first so every charge sees a consistent
                # field snapshot for this step.
                for charge in self._charges.values():
                    if charge.pinned:
                        charge.net_force = (0.0, 0.0, 0.0)
                        continue
                    e_vec, _ = self._electric_field_at(charge.position, exclude=charge.charge_id)
                    b_vec, _ = self._magnetic_field_at(charge.position)
                    electric_force = _vec_scale(e_vec, charge.charge_value)
                    magnetic_force = _vec_scale(
                        _vec_cross(charge.velocity, b_vec),
                        charge.charge_value,
                    )
                    charge.net_force = _vec_add(electric_force, magnetic_force)
                # Integrate motion with explicit Euler.
                for charge in self._charges.values():
                    if charge.pinned:
                        continue
                    acceleration = _vec_scale(charge.net_force, 1.0 / max(_EPSILON, charge.mass))
                    new_velocity = _vec_add(charge.velocity, _vec_scale(acceleration, step))
                    new_position = _vec_add(charge.position, _vec_scale(new_velocity, step))
                    old_position = charge.position
                    charge.velocity = new_velocity
                    charge.position = new_position
                    charge.updated_at = _now()
                    moved += 1
                    if _vec_distance(old_position, new_position) > _EPSILON:
                        self._stats.total_charges_moved += 1
            # Refresh coil flux baseline so the next EMF query measures
            # the change accumulated over this step.
            if self._config.enable_induction:
                for coil in self._induction_coils.values():
                    flux, _ = self._flux_through_coil(coil)
                    coil.previous_flux = coil.magnetic_flux
                    coil.magnetic_flux = flux
                    coil.updated_at = _now()
            self._refresh_stats()
            self._emit(
                EMEventKind.TICK.value,
                description=f"Tick {self._tick_count} (dt={step:.4f}s, moved={moved}).",
                data={
                    "tick": self._tick_count,
                    "dt": step,
                    "global_time": self._global_time,
                    "charges_moved": moved,
                },
            )
            return True, "ok", {
                "tick": self._tick_count,
                "dt": step,
                "global_time": self._global_time,
                "charges_moved": moved,
                "total_charges": len(self._charges),
                "total_magnetic_fields": len(self._magnetic_fields),
            }

    # ------------------------------------------------------------------
    # Configuration & Observability
    # ------------------------------------------------------------------

    def get_config(self) -> EMConfig:
        """Return the current runtime configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, EMConfig]:
        """Update one or more configuration fields."""
        with self._lock:
            changed: List[str] = []
            for key, value in kwargs.items():
                if not hasattr(self._config, key):
                    continue
                if key == "metadata":
                    if isinstance(value, dict):
                        self._config.metadata = dict(value)
                        changed.append(key)
                    continue
                if key == "field_map_bounds":
                    coerced = _coerce_position(value)
                    # Expand the 3-tuple into a 6-element bounds box.
                    self._config.field_map_bounds = (
                        -abs(coerced[0]), -abs(coerced[1]), -abs(coerced[2]),
                        abs(coerced[0]), abs(coerced[1]), abs(coerced[2]),
                    )
                    changed.append(key)
                    continue
                current = getattr(self._config, key)
                if isinstance(current, bool):
                    setattr(self._config, key, bool(value))
                elif isinstance(current, int):
                    setattr(self._config, key, _safe_int(value, current))
                elif isinstance(current, float):
                    setattr(self._config, key, _safe_float(value, current))
                else:
                    setattr(self._config, key, value)
                changed.append(key)
            self._emit(
                EMEventKind.CONFIG_UPDATED.value,
                description=f"Config updated: {', '.join(changed) if changed else 'no changes'}.",
                data={"changed_fields": changed},
            )
            return True, "updated", self._config

    def get_stats(self) -> EMStats:
        """Return the cached statistics roll-up."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> EMSnapshot:
        """Return a point-in-time snapshot of the entire system state."""
        with self._lock:
            self._refresh_stats()
            return EMSnapshot(
                timestamp=_now(),
                charges=[c.to_dict() for c in self._charges.values()],
                magnetic_fields=[f.to_dict() for f in self._magnetic_fields.values()],
                circuits=[c.to_dict() for c in self._circuits.values()],
                conductors=[c.to_dict() for c in self._conductors.values()],
                induction_coils=[c.to_dict() for c in self._induction_coils.values()],
                em_sources=[s.to_dict() for s in self._em_sources.values()],
                field_lines=[l.to_dict() for l in self._field_lines.values()],
                events=[e.to_dict() for e in self._events[-50:]],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a lightweight status summary."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "seeded": self._seeded,
                "tick_count": self._tick_count,
                "global_time": self._global_time,
                "last_dt": self._last_dt,
                "total_charges": len(self._charges),
                "total_magnetic_fields": len(self._magnetic_fields),
                "total_circuits": len(self._circuits),
                "total_conductors": len(self._conductors),
                "total_induction_coils": len(self._induction_coils),
                "total_em_sources": len(self._em_sources),
                "total_field_lines": len(self._field_lines),
                "active_magnetic_fields": self._stats.active_magnetic_fields,
                "active_em_sources": self._stats.active_em_sources,
                "open_circuits": self._stats.open_circuits,
                "closed_circuits": self._stats.closed_circuits,
                "shorted_circuits": self._stats.shorted_circuits,
                "blown_circuits": self._stats.blown_circuits,
            }


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "ChargeType",
    "FieldType",
    "CircuitStatus",
    "ConductorType",
    "EMSourceType",
    "FieldLineType",
    "EMEventKind",
    # Data classes
    "Charge",
    "MagneticField",
    "Circuit",
    "Conductor",
    "InductionCoil",
    "EMSource",
    "FieldLine",
    "EMConfig",
    "EMStats",
    "EMSnapshot",
    "EMEvent",
    # Factory
    "get_electromagnetic_field_system",
]


def get_electromagnetic_field_system() -> _ElectromagneticFieldSystem:
    """Return the shared electromagnetic field system singleton.

    The factory calls ``get_instance`` to obtain (or create) the
    singleton and then ensures it has been seeded by invoking
    ``initialize`` exactly once.
    """
    inst = _ElectromagneticFieldSystem.get_instance()
    if not inst._initialized:
        inst.initialize()
    return inst
