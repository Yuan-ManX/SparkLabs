"""Engine radiation field system: ionizing radiation physics simulation.

Simulates radioactive decay, radiation propagation, contamination spread,
shielding attenuation, and dosimetry for gameplay mechanics in sci-fi,
survival, and post-apocalyptic game scenarios.

The system models four fundamental radiation categories (alpha, beta,
gamma, neutron), exponential radioactive decay, parent/daughter isotope
chains, inverse-square intensity falloff, material attenuation with
half-value layers, absorbed/equivalent/effective dose computation, and
dynamic surface/volume contamination zones that spread over time. It is
intended for gameplay tuning rather than regulatory accuracy; physics
constants are simplified but internally consistent so designers can
author convincing radioactive hazards, fallout fields, reactor meltdowns,
and shielding puzzles.

Thread safety
-------------
The system is implemented as a singleton guarded by ``threading.RLock``.
The class-level ``_init_lock`` guards singleton creation and one-time
seeding; the instance-level ``_lock`` guards every mutating operation to
keep the internal dictionaries consistent. Consumers should obtain the
instance through :meth:`_RadiationFieldSystem.get_instance` or the
module-level :func:`get_radiation_field_system` factory.

Physics summary
---------------
- Activity: ``A(t) = A0 * exp(-lambda * t)``, ``lambda = ln(2) / T_half``
- Inverse-square intensity: ``I(r) = I0 / (4 * pi * r^2)``
- Linear attenuation: ``I = I0 * exp(-mu * x)``
- Half-value layer: ``HVL = ln(2) / mu``
- Absorbed dose (Gray): ``D = E_absorbed / mass``
- Equivalent dose (Sievert): ``H = D * QF``
- Quality factors: alpha=20, beta=1, gamma=1, neutron=5..20
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ============================================================================
# Physical constants (SI units unless noted)
# ============================================================================

_LN2: float = math.log(2.0)
_4PI: float = 4.0 * math.pi
_BQ_PER_SV_S_DEFAULT: float = 1.0  # placeholder; real conversion is energy-dependent
_MEV_TO_JOULE: float = 1.602176634e-13
_AVOGADRO: float = 6.02214076e23
_SECONDS_PER_HOUR: float = 3600.0
_MILLISV_PER_SV: float = 1000.0
_MICROS_PER_MILLI: float = 1000.0

# Default quality factors by radiation type (dimensionless).
_DEFAULT_QUALITY_FACTORS: Dict["RadiationType", float] = {}


# ============================================================================
# Enums
# ============================================================================

class RadiationType(Enum):
    """Categories of ionizing radiation simulated by the system."""

    ALPHA = "alpha"
    BETA = "beta"
    GAMMA = "gamma"
    NEUTRON = "neutron"


class DecayMode(Enum):
    """Modes of radioactive decay supported by the isotope model."""

    ALPHA_DECAY = "alpha_decay"
    BETA_MINUS = "beta_minus"
    BETA_PLUS = "beta_plus"
    GAMMA_EMISSION = "gamma_emission"
    NEUTRON_EMISSION = "neutron_emission"
    ELECTRON_CAPTURE = "electron_capture"
    SPONTANEOUS_FISSION = "spontaneous_fission"
    ISOMERIC_TRANSITION = "isomeric_transition"
    STABLE = "stable"


class ShieldingType(Enum):
    """Material categories used for radiation shielding."""

    LEAD = "lead"
    CONCRETE = "concrete"
    WATER = "water"
    STEEL = "steel"
    BORON = "boron"
    POLYETHYLENE = "polyethylene"
    DEPLETED_URANIUM = "depleted_uranium"
    GLASS = "glass"
    EARTH = "earth"
    TUNGSTEN = "tungsten"


class ContaminationLevel(Enum):
    """Severity levels for contamination zones.

    The numeric value doubles as a sorting key so callers can compare
    severity with ordinary integer ordering.
    """

    CLEAN = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    LETHAL = 4


class RadiationEventKind(Enum):
    """Event categories emitted by the radiation field system."""

    SOURCE_REGISTERED = "source_registered"
    SOURCE_UPDATED = "source_updated"
    SOURCE_REMOVED = "source_removed"
    SHIELDING_REGISTERED = "shielding_registered"
    SHIELDING_UPDATED = "shielding_updated"
    SHIELDING_REMOVED = "shielding_removed"
    ZONE_REGISTERED = "zone_registered"
    ZONE_UPDATED = "zone_updated"
    ZONE_REMOVED = "zone_removed"
    DOSIMETER_REGISTERED = "dosimeter_registered"
    DOSIMETER_UPDATED = "dosimeter_updated"
    DOSIMETER_REMOVED = "dosimeter_removed"
    DETECTOR_REGISTERED = "detector_registered"
    DETECTOR_UPDATED = "detector_updated"
    DETECTOR_REMOVED = "detector_removed"
    ISOTOPE_REGISTERED = "isotope_registered"
    ISOTOPE_REMOVED = "isotope_removed"
    DECAY_UPDATED = "decay_updated"
    CONTAMINATION_SPREAD = "contamination_spread"
    DOSIMETER_ALARM = "dosimeter_alarm"
    DETECTOR_READING = "detector_reading"
    CONFIG_CHANGED = "config_changed"
    SYSTEM_RESET = "system_reset"
    AI_PREDICTION = "ai_prediction"
    TICK = "tick"
    ALARM_CLEARED = "alarm_cleared"
    DETECTOR_CALIBRATED = "detector_calibrated"


class DetectorStatus(Enum):
    """Operational status of a radiation detector."""

    ACTIVE = "active"
    IDLE = "idle"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"
    CALIBRATING = "calibrating"
    ALARM = "alarm"
    FAULT = "fault"


# Populate the quality-factor lookup now that RadiationType exists.
_DEFAULT_QUALITY_FACTORS = {
    RadiationType.ALPHA: 20.0,
    RadiationType.BETA: 1.0,
    RadiationType.GAMMA: 1.0,
    RadiationType.NEUTRON: 10.0,
}


# ============================================================================
# Module-level helpers
# ============================================================================

def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` to the inclusive ``[low, high]`` range."""

    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_value(v):
    """Return ``v.value`` for enums, or ``v`` unchanged for plain values."""

    if hasattr(v, "value"):
        return v.value
    return v


def _coerce_enum(enum_cls, value, default=None):
    """Convert a string/int to an enum member, returning default on failure.

    Tries value-based lookup first (``enum_cls(value)``), then name-based
    lookup (``enum_cls[value.upper()]``) so both ``RadiationType("gamma")``
    and ``ContaminationLevel["HIGH"]`` style inputs coerce correctly.
    """

    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        pass
    if isinstance(value, str):
        try:
            return enum_cls[value.upper()]
        except KeyError:
            pass
        try:
            return enum_cls[value]
        except KeyError:
            pass
    return default


def _now_ts() -> float:
    """Return a monotonic-style timestamp used for event ordering."""

    return time.time()


def _distance_2d(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Euclidean distance between two 2D points."""

    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)


def _distance_3d(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    """Euclidean distance between two 3D points."""

    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _point_in_bounds(
    point: Tuple[float, float, float],
    bounds: Tuple[float, float, float, float, float, float],
) -> bool:
    """Return True when ``point`` lies inside the axis-aligned ``bounds``.

    Bounds are interpreted as ``(min_x, min_y, min_z, max_x, max_y, max_z)``.
    """

    min_x, min_y, min_z, max_x, max_y, max_z = bounds
    return (
        min_x <= point[0] <= max_x
        and min_y <= point[1] <= max_y
        and min_z <= point[2] <= max_z
    )


def _classify_contamination_level(activity_bq_m2: float) -> "ContaminationLevel":
    """Map a surface activity density to a contamination severity level."""

    if activity_bq_m2 <= 0.0:
        return ContaminationLevel.CLEAN
    if activity_bq_m2 < 1.0e4:
        return ContaminationLevel.LOW
    if activity_bq_m2 < 1.0e6:
        return ContaminationLevel.MODERATE
    if activity_bq_m2 < 1.0e8:
        return ContaminationLevel.HIGH
    return ContaminationLevel.LETHAL


def _classify_zone_area(bounds: Tuple[float, float, float, float, float, float]) -> float:
    """Return the volume (m^3) enclosed by axis-aligned ``bounds``."""

    min_x, min_y, min_z, max_x, max_y, max_z = bounds
    return max(0.0, (max_x - min_x) * (max_y - min_y) * (max_z - min_z))


def _default_attenuation_coeff(material: "ShieldingType", rtype: "RadiationType") -> float:
    """Return a plausible linear attenuation coefficient (1/m).

    The numbers are tuned for gameplay, not regulatory accuracy. They are
    deliberately distinct per (material, radiation-type) pair so shielding
    puzzles require thoughtful material selection.
    """

    table: Dict[Tuple[ShieldingType, RadiationType], float] = {
        (ShieldingType.LEAD, RadiationType.ALPHA): 1.0e5,
        (ShieldingType.LEAD, RadiationType.BETA): 5.0e3,
        (ShieldingType.LEAD, RadiationType.GAMMA): 6.0e1,
        (ShieldingType.LEAD, RadiationType.NEUTRON): 8.0e-1,
        (ShieldingType.CONCRETE, RadiationType.ALPHA): 8.0e4,
        (ShieldingType.CONCRETE, RadiationType.BETA): 3.0e3,
        (ShieldingType.CONCRETE, RadiationType.GAMMA): 1.5e1,
        (ShieldingType.CONCRETE, RadiationType.NEUTRON): 1.2e0,
        (ShieldingType.WATER, RadiationType.ALPHA): 7.0e4,
        (ShieldingType.WATER, RadiationType.BETA): 2.0e3,
        (ShieldingType.WATER, RadiationType.GAMMA): 6.0e0,
        (ShieldingType.WATER, RadiationType.NEUTRON): 4.0e0,
        (ShieldingType.STEEL, RadiationType.ALPHA): 9.0e4,
        (ShieldingType.STEEL, RadiationType.BETA): 4.0e3,
        (ShieldingType.STEEL, RadiationType.GAMMA): 4.5e1,
        (ShieldingType.STEEL, RadiationType.NEUTRON): 6.0e-1,
        (ShieldingType.BORON, RadiationType.ALPHA): 7.5e4,
        (ShieldingType.BORON, RadiationType.BETA): 2.5e3,
        (ShieldingType.BORON, RadiationType.GAMMA): 1.0e1,
        (ShieldingType.BORON, RadiationType.NEUTRON): 2.0e1,
        (ShieldingType.POLYETHYLENE, RadiationType.ALPHA): 6.0e4,
        (ShieldingType.POLYETHYLENE, RadiationType.BETA): 2.0e3,
        (ShieldingType.POLYETHYLENE, RadiationType.GAMMA): 4.0e0,
        (ShieldingType.POLYETHYLENE, RadiationType.NEUTRON): 6.0e0,
        (ShieldingType.DEPLETED_URANIUM, RadiationType.ALPHA): 1.1e5,
        (ShieldingType.DEPLETED_URANIUM, RadiationType.BETA): 5.5e3,
        (ShieldingType.DEPLETED_URANIUM, RadiationType.GAMMA): 8.0e1,
        (ShieldingType.DEPLETED_URANIUM, RadiationType.NEUTRON): 5.0e-1,
        (ShieldingType.GLASS, RadiationType.ALPHA): 7.0e4,
        (ShieldingType.GLASS, RadiationType.BETA): 2.8e3,
        (ShieldingType.GLASS, RadiationType.GAMMA): 9.0e0,
        (ShieldingType.GLASS, RadiationType.NEUTRON): 5.0e-1,
        (ShieldingType.EARTH, RadiationType.ALPHA): 7.5e4,
        (ShieldingType.EARTH, RadiationType.BETA): 2.6e3,
        (ShieldingType.EARTH, RadiationType.GAMMA): 1.2e1,
        (ShieldingType.EARTH, RadiationType.NEUTRON): 1.0e0,
        (ShieldingType.TUNGSTEN, RadiationType.ALPHA): 1.0e5,
        (ShieldingType.TUNGSTEN, RadiationType.BETA): 5.2e3,
        (ShieldingType.TUNGSTEN, RadiationType.GAMMA): 7.0e1,
        (ShieldingType.TUNGSTEN, RadiationType.NEUTRON): 7.0e-1,
    }
    return table.get((material, rtype), 1.0e1)


def _default_material_density(material: "ShieldingType") -> float:
    """Return a representative density (kg/m^3) for a shielding material."""

    return {
        ShieldingType.LEAD: 11340.0,
        ShieldingType.CONCRETE: 2400.0,
        ShieldingType.WATER: 1000.0,
        ShieldingType.STEEL: 7850.0,
        ShieldingType.BORON: 2460.0,
        ShieldingType.POLYETHYLENE: 950.0,
        ShieldingType.DEPLETED_URANIUM: 19050.0,
        ShieldingType.GLASS: 2500.0,
        ShieldingType.EARTH: 1600.0,
        ShieldingType.TUNGSTEN: 19300.0,
    }.get(material, 2000.0)


def _quality_factor(rtype: "RadiationType", energy_mev: float = 0.0) -> float:
    """Return the radiation quality (weighting) factor for dose conversion.

    For neutrons the factor scales with kinetic energy to reflect the
    strongly energy-dependent biological effectiveness.
    """

    if rtype == RadiationType.ALPHA:
        return 20.0
    if rtype == RadiationType.BETA:
        return 1.0
    if rtype == RadiationType.GAMMA:
        return 1.0
    if rtype == RadiationType.NEUTRON:
        # Simple piecewise approximation matching ICRP trends.
        if energy_mev < 1.0e-6:
            return 5.0
        if energy_mev < 0.01:
            return 10.0
        if energy_mev < 0.1:
            return 20.0
        if energy_mev < 1.0:
            return 15.0
        if energy_mev < 10.0:
            return 10.0
        return 5.0
    return 1.0


def _level_to_multiplier(level: "ContaminationLevel") -> float:
    """Map a contamination level to a spread-rate multiplier."""

    return {
        ContaminationLevel.CLEAN: 0.0,
        ContaminationLevel.LOW: 0.15,
        ContaminationLevel.MODERATE: 0.4,
        ContaminationLevel.HIGH: 0.7,
        ContaminationLevel.LETHAL: 1.0,
    }.get(level, 0.0)


def _level_to_dose_rate_sv_per_h(level: "ContaminationLevel") -> float:
    """Return a representative ambient dose rate (Sv/h) for a zone level."""

    return {
        ContaminationLevel.CLEAN: 0.0,
        ContaminationLevel.LOW: 1.0e-6,
        ContaminationLevel.MODERATE: 1.0e-5,
        ContaminationLevel.HIGH: 1.0e-3,
        ContaminationLevel.LETHAL: 5.0e0,
    }.get(level, 0.0)


def _format_dose(dose_sv: float) -> str:
    """Format a dose value with a sensible SI prefix for display."""

    if dose_sv == 0.0:
        return "0 Sv"
    if abs(dose_sv) >= 1.0:
        return f"{dose_sv:.3f} Sv"
    if abs(dose_sv) >= 1.0e-3:
        return f"{dose_sv * 1.0e3:.3f} mSv"
    return f"{dose_sv * 1.0e6:.3f} uSv"


def _new_id(prefix: str) -> str:
    """Generate a short unique identifier with a descriptive prefix."""

    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ============================================================================
# Entity dataclasses
# ============================================================================

@dataclass
class Isotope:
    """A nuclide with decay parameters.

    Attributes
    ----------
    isotope_id:
        Stable identifier used for cross-lookups.
    name:
        Human-readable symbol, e.g. ``"Cs-137"``.
    half_life_s:
        Half-life in seconds. ``math.inf`` indicates a stable nuclide.
    decay_mode:
        Primary decay pathway.
    daughter_isotope:
        Identifier of the resulting nuclide, or ``None`` for stable isotopes.
    radiation_type:
        Dominant radiation type emitted by the decay.
    energy_mev:
        Average energy per decay (MeV).
    atomic_mass:
        Atomic mass in atomic mass units.
    branching_ratio:
        Fraction of decays following this pathway (0..1).
    """

    isotope_id: str
    name: str
    half_life_s: float
    decay_mode: DecayMode = DecayMode.STABLE
    daughter_isotope: Optional[str] = None
    radiation_type: RadiationType = RadiationType.GAMMA
    energy_mev: float = 0.0
    atomic_mass: float = 0.0
    branching_ratio: float = 1.0

    @property
    def decay_constant(self) -> float:
        """Return lambda = ln(2) / T_half (1/s), or 0 for stable isotopes."""

        if self.half_life_s <= 0.0 or math.isinf(self.half_life_s):
            return 0.0
        return _LN2 / self.half_life_s

    @property
    def is_stable(self) -> bool:
        """Return True when the isotope does not decay."""

        return (
            self.half_life_s <= 0.0
            or math.isinf(self.half_life_s)
            or self.decay_mode == DecayMode.STABLE
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the isotope to a plain dictionary."""

        return {
            "isotope_id": self.isotope_id,
            "name": self.name,
            "half_life_s": None if math.isinf(self.half_life_s) else self.half_life_s,
            "decay_mode": self.decay_mode.value,
            "daughter_isotope": self.daughter_isotope,
            "radiation_type": self.radiation_type.value,
            "energy_mev": self.energy_mev,
            "atomic_mass": self.atomic_mass,
            "branching_ratio": self.branching_ratio,
            "decay_constant": self.decay_constant,
            "is_stable": self.is_stable,
        }


@dataclass
class DecayProduct:
    """A daughter product produced by a decay step.

    Attributes
    ----------
    isotope_id:
        Identifier of the produced nuclide.
    branching_ratio:
        Fraction of parent decays yielding this product (0..1).
    delay_s:
        Mean delay before the daughter appears (for metastable chains).
    """

    isotope_id: str
    branching_ratio: float = 1.0
    delay_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the decay product to a plain dictionary."""

        return {
            "isotope_id": self.isotope_id,
            "branching_ratio": self.branching_ratio,
            "delay_s": self.delay_s,
        }


@dataclass
class RadiationSource:
    """A localized radioactive emitter.

    Attributes
    ----------
    source_id:
        Stable identifier.
    isotope_id:
        Identifier of the isotope that defines the source's decay.
    activity_bq:
        Current activity in becquerels (decays per second).
    position:
        3D world position in metres.
    radius:
        Effective physical radius (m) used for self-shielding and overlap.
    intensity_sv_per_h:
        Cached dose rate at 1 m, recomputed on demand.
    age_s:
        Accumulated simulation age (s) used for decay bookkeeping.
    active:
        Whether the source currently emits radiation.
    name:
        Optional display name.
    """

    source_id: str
    isotope_id: str
    activity_bq: float
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 0.1
    intensity_sv_per_h: float = 0.0
    age_s: float = 0.0
    active: bool = True
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the source to a plain dictionary."""

        return {
            "source_id": self.source_id,
            "isotope_id": self.isotope_id,
            "activity_bq": self.activity_bq,
            "position": list(self.position),
            "radius": self.radius,
            "intensity_sv_per_h": self.intensity_sv_per_h,
            "age_s": self.age_s,
            "active": self.active,
            "name": self.name,
        }


@dataclass
class ShieldingMaterial:
    """A slab of shielding placed between sources and protected targets.

    Attributes
    ----------
    material_id:
        Stable identifier.
    type:
        Material category driving the attenuation table.
    thickness_m:
        Physical thickness in metres.
    attenuation_coeff:
        Linear attenuation coefficient mu (1/m) for the dominant radiation
        type. Recomputed when material or radiation type changes.
    density_kg_m3:
        Material density (kg/m^3).
    radiation_type:
        Radiation type the attenuation coefficient applies to.
    position:
        Optional 3D placement used for line-of-sight checks.
    name:
        Optional display name.
    """

    material_id: str
    type: ShieldingType = ShieldingType.LEAD
    thickness_m: float = 0.05
    attenuation_coeff: float = 60.0
    density_kg_m3: float = 11340.0
    radiation_type: RadiationType = RadiationType.GAMMA
    position: Optional[Tuple[float, float, float]] = None
    name: str = ""

    @property
    def half_value_layer(self) -> float:
        """Thickness that halves the transmitted intensity (m)."""

        if self.attenuation_coeff <= 0.0:
            return math.inf
        return _LN2 / self.attenuation_coeff

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the shielding to a plain dictionary."""

        return {
            "material_id": self.material_id,
            "type": self.type.value,
            "thickness_m": self.thickness_m,
            "attenuation_coeff": self.attenuation_coeff,
            "density_kg_m3": self.density_kg_m3,
            "radiation_type": self.radiation_type.value,
            "position": list(self.position) if self.position else None,
            "half_value_layer": self.half_value_layer,
            "name": self.name,
        }


@dataclass
class ContaminationZone:
    """A volumetric region contaminated by radioactive material.

    Attributes
    ----------
    zone_id:
        Stable identifier.
    name:
        Display name.
    bounds:
        Axis-aligned bounding box ``(min_x, min_y, min_z, max_x, max_y, max_z)``.
    level:
        Severity bucket used for gameplay logic.
    isotope_id:
        Primary isotope responsible for the contamination.
    activity_bq_m2:
        Surface activity density (Bq/m^2).
    volume_bq_m3:
        Volume activity concentration (Bq/m^3) for airborne contamination.
    area:
        Enclosed volume in cubic metres (cached from bounds).
    age_s:
        Accumulated age used for decay and spread bookkeeping.
    spread_rate:
        Per-tick expansion factor of the zone bounds.
    """

    zone_id: str
    name: str
    bounds: Tuple[float, float, float, float, float, float]
    level: ContaminationLevel = ContaminationLevel.LOW
    isotope_id: str = ""
    activity_bq_m2: float = 0.0
    volume_bq_m3: float = 0.0
    area: float = 0.0
    age_s: float = 0.0
    spread_rate: float = 0.02

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the zone to a plain dictionary."""

        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "bounds": list(self.bounds),
            "level": self.level.value,
            "level_name": self.level.name,
            "isotope_id": self.isotope_id,
            "activity_bq_m2": self.activity_bq_m2,
            "volume_bq_m3": self.volume_bq_m3,
            "area": self.area,
            "age_s": self.age_s,
            "spread_rate": self.spread_rate,
        }


@dataclass
class Dosimeter:
    """A personal or area dosimeter that accumulates dose over time.

    Attributes
    ----------
    dosimeter_id:
        Stable identifier.
    position:
        3D position in metres.
    cumulative_dose_sv:
        Lifetime accumulated dose (Sv).
    alarm_threshold_sv:
        Dose at which the device raises an alarm.
    is_alarming:
        Whether the alarm is currently raised.
    dose_rate_sv_per_h:
        Most recently measured dose rate.
    active:
        Whether the device is currently tracking dose.
    name:
        Optional display name.
    """

    dosimeter_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    cumulative_dose_sv: float = 0.0
    alarm_threshold_sv: float = 0.1
    is_alarming: bool = False
    dose_rate_sv_per_h: float = 0.0
    active: bool = True
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the dosimeter to a plain dictionary."""

        return {
            "dosimeter_id": self.dosimeter_id,
            "position": list(self.position),
            "cumulative_dose_sv": self.cumulative_dose_sv,
            "alarm_threshold_sv": self.alarm_threshold_sv,
            "is_alarming": self.is_alarming,
            "dose_rate_sv_per_h": self.dose_rate_sv_per_h,
            "active": self.active,
            "name": self.name,
            "formatted_dose": _format_dose(self.cumulative_dose_sv),
        }


@dataclass
class RadiationDetector:
    """A directional or area radiation detector.

    Attributes
    ----------
    detector_id:
        Stable identifier.
    position:
        3D position in metres.
    reading_sv_per_h:
        Most recent instantaneous dose-rate reading.
    type:
        Radiation type the detector is most sensitive to.
    status:
        Current operational status.
    range_sv_per_h:
        Maximum measurable dose rate before overload.
    sensitivity:
        Calibration multiplier applied to raw measurements.
    calibration_age_s:
        Time since the last calibration.
    name:
        Optional display name.
    """

    detector_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    reading_sv_per_h: float = 0.0
    type: RadiationType = RadiationType.GAMMA
    status: DetectorStatus = DetectorStatus.IDLE
    range_sv_per_h: float = 10.0
    sensitivity: float = 1.0
    calibration_age_s: float = 0.0
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the detector to a plain dictionary."""

        return {
            "detector_id": self.detector_id,
            "position": list(self.position),
            "reading_sv_per_h": self.reading_sv_per_h,
            "type": self.type.value,
            "status": self.status.value,
            "range_sv_per_h": self.range_sv_per_h,
            "sensitivity": self.sensitivity,
            "calibration_age_s": self.calibration_age_s,
            "name": self.name,
            "formatted_reading": _format_dose(self.reading_sv_per_h),
        }


# ============================================================================
# Config / Stats / Snapshot / Event
# ============================================================================

@dataclass
class RadiationConfig:
    """Tunable configuration for the radiation field system.

    All fields have sensible defaults so a freshly constructed config is
    immediately usable. ``set_config`` accepts keyword arguments matching
    any field name and updates only the supplied ones.
    """

    time_scale: float = 1.0
    background_radiation_usv_per_h: float = 0.12
    dose_rate_unit: str = "Sv/h"
    max_events: int = 500
    decay_enabled: bool = True
    contamination_spread_enabled: bool = True
    shielding_enabled: bool = True
    dosimeter_integration_enabled: bool = True
    detector_auto_overload: bool = True
    world_bounds: Tuple[float, float, float, float, float, float] = (
        -500.0, -500.0, -100.0, 500.0, 500.0, 300.0,
    )
    default_alarm_threshold_sv: float = 0.05
    spread_baseline_rate: float = 0.02
    ambient_temperature_c: float = 20.0
    humidity_fraction: float = 0.5
    simulation_step_s: float = 0.016

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the config to a plain dictionary."""

        return {
            "time_scale": self.time_scale,
            "background_radiation_usv_per_h": self.background_radiation_usv_per_h,
            "dose_rate_unit": self.dose_rate_unit,
            "max_events": self.max_events,
            "decay_enabled": self.decay_enabled,
            "contamination_spread_enabled": self.contamination_spread_enabled,
            "shielding_enabled": self.shielding_enabled,
            "dosimeter_integration_enabled": self.dosimeter_integration_enabled,
            "detector_auto_overload": self.detector_auto_overload,
            "world_bounds": list(self.world_bounds),
            "default_alarm_threshold_sv": self.default_alarm_threshold_sv,
            "spread_baseline_rate": self.spread_baseline_rate,
            "ambient_temperature_c": self.ambient_temperature_c,
            "humidity_fraction": self.humidity_fraction,
            "simulation_step_s": self.simulation_step_s,
        }

    def update(self, **kwargs: Any) -> Dict[str, Any]:
        """Update fields from keyword arguments and return the change set."""

        changed: Dict[str, Any] = {}
        for key, value in kwargs.items():
            if not hasattr(self, key):
                continue
            old_value = getattr(self, key)
            if old_value == value:
                continue
            setattr(self, key, value)
            changed[key] = {"old": old_value, "new": value}
        return changed


@dataclass
class RadiationStats:
    """Aggregate statistics tracked by the system."""

    total_sources: int = 0
    total_shieldings: int = 0
    total_zones: int = 0
    total_dosimeters: int = 0
    total_detectors: int = 0
    total_isotopes: int = 0
    total_dose_sv: float = 0.0
    peak_dose_rate_sv_per_h: float = 0.0
    simulation_time_s: float = 0.0
    total_events: int = 0
    total_measurements: int = 0
    total_decay_steps: int = 0
    total_spread_events: int = 0
    total_alarms: int = 0
    total_ai_predictions: int = 0
    last_tick_dt: float = 0.0
    last_tick_ts: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the stats to a plain dictionary."""

        return {
            "total_sources": self.total_sources,
            "total_shieldings": self.total_shieldings,
            "total_zones": self.total_zones,
            "total_dosimeters": self.total_dosimeters,
            "total_detectors": self.total_detectors,
            "total_isotopes": self.total_isotopes,
            "total_dose_sv": self.total_dose_sv,
            "peak_dose_rate_sv_per_h": self.peak_dose_rate_sv_per_h,
            "simulation_time_s": self.simulation_time_s,
            "total_events": self.total_events,
            "total_measurements": self.total_measurements,
            "total_decay_steps": self.total_decay_steps,
            "total_spread_events": self.total_spread_events,
            "total_alarms": self.total_alarms,
            "total_ai_predictions": self.total_ai_predictions,
            "last_tick_dt": self.last_tick_dt,
            "last_tick_ts": self.last_tick_ts,
        }


@dataclass
class RadiationSnapshot:
    """A point-in-time snapshot of the entire system state."""

    timestamp: float
    simulation_time_s: float
    config: Dict[str, Any]
    stats: Dict[str, Any]
    sources: List[Dict[str, Any]] = field(default_factory=list)
    shieldings: List[Dict[str, Any]] = field(default_factory=list)
    zones: List[Dict[str, Any]] = field(default_factory=list)
    dosimeters: List[Dict[str, Any]] = field(default_factory=list)
    detectors: List[Dict[str, Any]] = field(default_factory=list)
    isotopes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the snapshot to a plain dictionary."""

        return {
            "timestamp": self.timestamp,
            "simulation_time_s": self.simulation_time_s,
            "config": self.config,
            "stats": self.stats,
            "sources": self.sources,
            "shieldings": self.shieldings,
            "zones": self.zones,
            "dosimeters": self.dosimeters,
            "detectors": self.detectors,
            "isotopes": self.isotopes,
        }


@dataclass
class RadiationEvent:
    """An event emitted by the system for logging and gameplay hooks."""

    event_id: str
    kind: RadiationEventKind
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the event to a plain dictionary."""

        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }


# ============================================================================
# Main system class
# ============================================================================

class _RadiationFieldSystem:
    """Simulates ionizing radiation fields for an AI-native game engine.

    The class is a thread-safe singleton. External code should never
    instantiate it directly; use :meth:`get_instance` or the module-level
    :func:`get_radiation_field_system` factory instead.

    The system stores isotopes, sources, shielding materials,
    contamination zones, dosimeters, and detectors in dictionaries keyed
    by their stable identifier. Every mutating operation acquires the
    instance lock and emits a :class:`RadiationEvent` so gameplay code
    can react to state changes through :meth:`list_events`.
    """

    _instance: Optional["_RadiationFieldSystem"] = None
    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._seeded: bool = False

        self._isotopes: Dict[str, Isotope] = {}
        self._sources: Dict[str, RadiationSource] = {}
        self._shieldings: Dict[str, ShieldingMaterial] = {}
        self._zones: Dict[str, ContaminationZone] = {}
        self._dosimeters: Dict[str, Dosimeter] = {}
        self._detectors: Dict[str, RadiationDetector] = {}

        self._config: RadiationConfig = RadiationConfig()
        self._stats: RadiationStats = RadiationStats()
        self._events: List[RadiationEvent] = []

        self._simulation_time_s: float = 0.0
        self._last_tick_ts: float = _now_ts()

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "_RadiationFieldSystem":
        """Return the shared singleton, creating and seeding it if needed.

        Uses double-checked locking: the first (lock-free) check avoids
        contention after initialization, while the inner check inside the
        lock guards against the race where two threads both observe a
        ``None`` instance before either takes the lock.
        """

        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    inst = cls()
                    inst._initialize()
                    cls._instance = inst
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization and seeding
    # ------------------------------------------------------------------

    def _initialize(self) -> None:
        """Mark the system as initialized and seed canonical data."""

        with self._lock:
            if self._initialized:
                return
            self._initialized = True
            self._seed_data()
            self._emit(
                RadiationEventKind.SYSTEM_RESET,
                {"reason": "initialized", "seeded": self._seeded},
            )

    def _seed_data(self) -> None:
        """Populate the system with a canonical set of radiation data.

        Seeding is idempotent: if ``_seeded`` is already True the call is
        a no-op so repeated initialization never duplicates entries.
        """

        with self._lock:
            if self._seeded:
                return

            # ----------------------------------------------------------
            # Isotopes (8) covering alpha, beta, gamma, neutron emitters
            # ----------------------------------------------------------
            isotope_seeds: List[Tuple[str, str, float, DecayMode, Optional[str], RadiationType, float, float, float]] = [
                ("iso_u238", "U-238", 1.41e17, DecayMode.ALPHA_DECAY, "iso_th234",
                 RadiationType.ALPHA, 4.27, 238.05, 1.0),
                ("iso_th234", "Th-234", 2.08e6, DecayMode.BETA_MINUS, "iso_pa234",
                 RadiationType.BETA, 0.27, 234.04, 1.0),
                ("iso_pa234", "Pa-234", 2.41e4, DecayMode.BETA_MINUS, "iso_u234",
                 RadiationType.BETA, 2.23, 234.06, 1.0),
                ("iso_u234", "U-234", 7.74e12, DecayMode.ALPHA_DECAY, "iso_th230",
                 RadiationType.ALPHA, 4.86, 234.04, 1.0),
                ("iso_cs137", "Cs-137", 9.49e8, DecayMode.BETA_MINUS, "iso_ba137m",
                 RadiationType.BETA, 1.176, 136.91, 1.0),
                ("iso_ba137m", "Ba-137m", 955.0, DecayMode.ISOMERIC_TRANSITION, "iso_ba137",
                 RadiationType.GAMMA, 0.662, 136.91, 0.946),
                ("iso_ba137", "Ba-137", math.inf, DecayMode.STABLE, None,
                 RadiationType.GAMMA, 0.0, 136.91, 1.0),
                ("iso_co60", "Co-60", 1.66e8, DecayMode.BETA_MINUS, "iso_ni60",
                 RadiationType.GAMMA, 2.5, 59.93, 1.0),
                ("iso_ni60", "Ni-60", math.inf, DecayMode.STABLE, None,
                 RadiationType.GAMMA, 0.0, 59.93, 1.0),
                ("iso_cf252", "Cf-252", 2.65e8, DecayMode.SPONTANEOUS_FISSION, "iso_misc_fp",
                 RadiationType.NEUTRON, 2.1, 252.08, 1.0),
                ("iso_misc_fp", "Fission Products", math.inf, DecayMode.STABLE, None,
                 RadiationType.BETA, 0.0, 100.0, 1.0),
                ("iso_sr90", "Sr-90", 9.21e8, DecayMode.BETA_MINUS, "iso_y90",
                 RadiationType.BETA, 0.546, 89.91, 1.0),
                ("iso_y90", "Y-90", 2.30e6, DecayMode.BETA_MINUS, "iso_zr90",
                 RadiationType.BETA, 2.28, 89.91, 1.0),
                ("iso_zr90", "Zr-90", math.inf, DecayMode.STABLE, None,
                 RadiationType.BETA, 0.0, 89.90, 1.0),
            ]
            for (iid, name, hl, mode, daughter, rtype, energy, mass, br) in isotope_seeds:
                isotope = Isotope(
                    isotope_id=iid,
                    name=name,
                    half_life_s=hl,
                    decay_mode=mode,
                    daughter_isotope=daughter,
                    radiation_type=rtype,
                    energy_mev=energy,
                    atomic_mass=mass,
                    branching_ratio=br,
                )
                self._isotopes[iid] = isotope

            # ----------------------------------------------------------
            # Radiation sources (5)
            # ----------------------------------------------------------
            source_seeds: List[Tuple[str, str, str, float, Tuple[float, float, float], float, str]] = [
                ("src_reactor_core", "Reactor Core Fragment", "iso_u238",
                 5.0e12, (0.0, 0.0, 0.0), 1.5, "Reactor Core Fragment"),
                ("src_cesium_spill", "Cs-137 Spill", "iso_cs137",
                 2.5e10, (40.0, 12.0, 0.0), 0.4, "Cs-137 Spill"),
                ("src_cobalt_pellet", "Co-60 Pellet", "iso_co60",
                 8.0e9, (-25.0, 18.0, 1.0), 0.05, "Co-60 Pellet"),
                ("src_californium", "Cf-252 Neutron Source", "iso_cf252",
                 1.0e8, (80.0, -30.0, 0.5), 0.03, "Cf-252 Neutron Source"),
                ("src_strontium_drums", "Sr-90 Storage Drums", "iso_sr90",
                 4.0e10, (-60.0, -45.0, 0.0), 1.2, "Sr-90 Storage Drums"),
            ]
            for (sid, _, isotope_id, activity, pos, radius, name) in source_seeds:
                source = RadiationSource(
                    source_id=sid,
                    isotope_id=isotope_id,
                    activity_bq=activity,
                    position=pos,
                    radius=radius,
                    name=name,
                )
                source.intensity_sv_per_h = self._estimate_source_intensity(source)
                self._sources[sid] = source

            # ----------------------------------------------------------
            # Shielding materials (5)
            # ----------------------------------------------------------
            shielding_seeds: List[Tuple[str, str, ShieldingType, float, RadiationType, Optional[Tuple[float, float, float]], str]] = [
                ("shld_lead_vault", "Lead Vault Door", ShieldingType.LEAD, 0.10,
                 RadiationType.GAMMA, (10.0, 0.0, 0.0), "Lead Vault Door"),
                ("shld_concrete_wall", "Reactor Concrete Wall", ShieldingType.CONCRETE, 1.20,
                 RadiationType.GAMMA, (-5.0, 0.0, 0.0), "Reactor Concrete Wall"),
                ("shld_water_pool", "Spent Fuel Pool", ShieldingType.WATER, 3.50,
                 RadiationType.GAMMA, (50.0, 12.0, -1.0), "Spent Fuel Pool"),
                ("shld_boron_panel", "Boron Neutron Panel", ShieldingType.BORON, 0.08,
                 RadiationType.NEUTRON, (78.0, -30.0, 0.5), "Boron Neutron Panel"),
                ("shld_poly_block", "Polyethylene Moderator", ShieldingType.POLYETHYLENE, 0.25,
                 RadiationType.NEUTRON, (82.0, -30.0, 0.5), "Polyethylene Moderator"),
            ]
            for (mid, _, mtype, thickness, rtype, pos, name) in shielding_seeds:
                material = ShieldingMaterial(
                    material_id=mid,
                    type=mtype,
                    thickness_m=thickness,
                    attenuation_coeff=_default_attenuation_coeff(mtype, rtype),
                    density_kg_m3=_default_material_density(mtype),
                    radiation_type=rtype,
                    position=pos,
                    name=name,
                )
                self._shieldings[mid] = material

            # ----------------------------------------------------------
            # Contamination zones (5)
            # ----------------------------------------------------------
            zone_seeds: List[Tuple[str, str, Tuple[float, float, float, float, float, float], ContaminationLevel, str, float, float, float]] = [
                ("zone_reactor_floor", "Reactor Hall Floor", (-20.0, -20.0, -0.5, 20.0, 20.0, 0.5),
                 ContaminationLevel.LETHAL, "iso_cs137", 8.0e8, 0.0, 0.03),
                ("zone_vent_shaft", "Contaminated Vent Shaft", (8.0, 8.0, 0.5, 12.0, 12.0, 20.0),
                 ContaminationLevel.HIGH, "iso_cs137", 2.0e7, 1.0e6, 0.05),
                ("zone_outer_yard", "Outer Storage Yard", (-90.0, -60.0, -0.5, -30.0, 0.0, 0.5),
                 ContaminationLevel.MODERATE, "iso_sr90", 4.0e5, 0.0, 0.02),
                ("zone_hot_cell", "Hot Cell Interior", (35.0, 5.0, 0.0, 45.0, 15.0, 3.0),
                 ContaminationLevel.HIGH, "iso_co60", 1.5e7, 0.0, 0.04),
                ("zone_safe_corridor", "Decon Corridor", (-5.0, 22.0, -0.5, 5.0, 30.0, 0.5),
                 ContaminationLevel.LOW, "iso_cs137", 2.0e3, 0.0, 0.01),
            ]
            for (zid, name, bounds, level, isotope_id, activity, vol_activity, spread) in zone_seeds:
                zone = ContaminationZone(
                    zone_id=zid,
                    name=name,
                    bounds=bounds,
                    level=level,
                    isotope_id=isotope_id,
                    activity_bq_m2=activity,
                    volume_bq_m3=vol_activity,
                    area=_classify_zone_area(bounds),
                    spread_rate=spread,
                )
                self._zones[zid] = zone

            # ----------------------------------------------------------
            # Dosimeters (4)
            # ----------------------------------------------------------
            dosimeter_seeds: List[Tuple[str, Tuple[float, float, float], float, str]] = [
                ("dsm_player", (0.0, 0.0, 1.0), 0.1, "Player Dosimeter"),
                ("dsm_reactor_worker", (-10.0, 0.0, 1.0), 0.05, "Reactor Worker Dosimeter"),
                ("dsm_hot_cell", (40.0, 10.0, 1.5), 0.02, "Hot Cell Dosimeter"),
                ("dsm_yard_patrol", (-60.0, -30.0, 1.0), 0.25, "Yard Patrol Dosimeter"),
            ]
            for (did, pos, threshold, name) in dosimeter_seeds:
                dosimeter = Dosimeter(
                    dosimeter_id=did,
                    position=pos,
                    alarm_threshold_sv=threshold,
                    name=name,
                )
                self._dosimeters[did] = dosimeter

            # ----------------------------------------------------------
            # Detectors (4)
            # ----------------------------------------------------------
            detector_seeds: List[Tuple[str, Tuple[float, float, float], RadiationType, float, float, str]] = [
                ("det_geiger_a", (0.0, 5.0, 1.0), RadiationType.BETA, 1.0e-3, 1.0, "Geiger Counter A"),
                ("det_scint", (40.0, 12.0, 1.5), RadiationType.GAMMA, 100.0, 1.2, "Scintillation Detector"),
                ("det_neutron", (80.0, -30.0, 1.0), RadiationType.NEUTRON, 10.0, 0.9, "Neutron Rem Counter"),
                ("det_alpha_probe", (-10.0, 0.0, 0.1), RadiationType.ALPHA, 1.0e-2, 1.0, "Alpha Probe"),
            ]
            for (did, pos, rtype, rng, sens, name) in detector_seeds:
                detector = RadiationDetector(
                    detector_id=did,
                    position=pos,
                    type=rtype,
                    range_sv_per_h=rng,
                    sensitivity=sens,
                    status=DetectorStatus.IDLE,
                    name=name,
                )
                self._detectors[did] = detector

            self._seeded = True
            self._refresh_stats_unlocked()

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        kind: RadiationEventKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> RadiationEvent:
        """Append an event and trim the buffer to ``max_events``."""

        event = RadiationEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now_ts(),
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        max_events = max(1, int(self._config.max_events))
        if len(self._events) > max_events:
            # Drop the oldest entries to keep memory bounded.
            del self._events[: len(self._events) - max_events]
        self._stats.total_events = len(self._events)
        return event

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    def _refresh_stats_unlocked(self) -> None:
        """Recompute aggregate counts that derive from the collections."""

        self._stats.total_isotopes = len(self._isotopes)
        self._stats.total_sources = len(self._sources)
        self._stats.total_shieldings = len(self._shieldings)
        self._stats.total_zones = len(self._zones)
        self._stats.total_dosimeters = len(self._dosimeters)
        self._stats.total_detectors = len(self._detectors)
        self._stats.simulation_time_s = self._simulation_time_s

    # ------------------------------------------------------------------
    # Isotope management
    # ------------------------------------------------------------------

    def register_isotope(
        self,
        isotope_id: Optional[str] = None,
        name: str = "",
        half_life_s: float = math.inf,
        decay_mode: DecayMode = DecayMode.STABLE,
        daughter_isotope: Optional[str] = None,
        radiation_type: RadiationType = RadiationType.GAMMA,
        energy_mev: float = 0.0,
        atomic_mass: float = 0.0,
        branching_ratio: float = 1.0,
    ) -> Isotope:
        """Register a new isotope and return the stored record.

        If ``isotope_id`` is omitted a unique identifier is generated.
        Registering an existing identifier replaces the record and emits
        an update event instead of a registration event.
        """

        with self._lock:
            isotope_id = isotope_id or _new_id("iso")
            existing = self._isotopes.get(isotope_id)
            isotope = Isotope(
                isotope_id=isotope_id,
                name=name or isotope_id,
                half_life_s=half_life_s,
                decay_mode=_coerce_enum(DecayMode, decay_mode, DecayMode.STABLE),
                daughter_isotope=daughter_isotope,
                radiation_type=_coerce_enum(RadiationType, radiation_type, RadiationType.GAMMA),
                energy_mev=energy_mev,
                atomic_mass=atomic_mass,
                branching_ratio=_clamp(branching_ratio, 0.0, 1.0),
            )
            self._isotopes[isotope_id] = isotope
            kind = (
                RadiationEventKind.ISOTOPE_REGISTERED
                if existing is None
                else RadiationEventKind.ISOTOPE_REGISTERED
            )
            self._emit(kind, {"isotope_id": isotope_id, "name": isotope.name})
            self._refresh_stats_unlocked()
            return isotope

    def get_isotope(self, isotope_id: str) -> Optional[Isotope]:
        """Return the isotope with the given identifier, or ``None``."""

        with self._lock:
            return self._isotopes.get(isotope_id)

    def list_isotopes(
        self,
        radiation_type: Optional[RadiationType] = None,
        stable: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> List[Isotope]:
        """Return isotopes optionally filtered by radiation type and stability."""

        with self._lock:
            items = list(self._isotopes.values())
        if radiation_type is not None:
            items = [i for i in items if i.radiation_type == radiation_type]
        if stable is not None:
            items = [i for i in items if i.is_stable == stable]
        if limit is not None and limit >= 0:
            items = items[:limit]
        return items

    def remove_isotope(self, isotope_id: str) -> Optional[Isotope]:
        """Remove and return the isotope, or ``None`` if it was not present."""

        with self._lock:
            isotope = self._isotopes.pop(isotope_id, None)
            if isotope is not None:
                self._emit(
                    RadiationEventKind.ISOTOPE_REMOVED,
                    {"isotope_id": isotope_id, "name": isotope.name},
                )
                self._refresh_stats_unlocked()
            return isotope

    # ------------------------------------------------------------------
    # Radiation source management
    # ------------------------------------------------------------------

    def register_source(
        self,
        source_id: Optional[str] = None,
        isotope_id: str = "",
        activity_bq: float = 0.0,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        radius: float = 0.1,
        name: str = "",
        active: bool = True,
    ) -> RadiationSource:
        """Register a radiation source, generating an ID when omitted."""

        with self._lock:
            source_id = source_id or _new_id("src")
            source = RadiationSource(
                source_id=source_id,
                isotope_id=isotope_id,
                activity_bq=max(0.0, float(activity_bq)),
                position=tuple(float(c) for c in position),
                radius=max(0.0, float(radius)),
                name=name,
                active=active,
            )
            source.intensity_sv_per_h = self._estimate_source_intensity(source)
            self._sources[source_id] = source
            self._emit(
                RadiationEventKind.SOURCE_REGISTERED,
                {
                    "source_id": source_id,
                    "isotope_id": isotope_id,
                    "activity_bq": source.activity_bq,
                },
            )
            self._refresh_stats_unlocked()
            return source

    def get_source(self, source_id: str) -> Optional[RadiationSource]:
        """Return the source with the given identifier, or ``None``."""

        with self._lock:
            return self._sources.get(source_id)

    def list_sources(
        self,
        isotope_id: Optional[str] = None,
        active: Optional[bool] = None,
        within_bounds: Optional[Tuple[float, float, float, float, float, float]] = None,
        limit: Optional[int] = None,
    ) -> List[RadiationSource]:
        """Return sources filtered by isotope, activity, or spatial bounds."""

        with self._lock:
            items = list(self._sources.values())
        if isotope_id is not None:
            items = [s for s in items if s.isotope_id == isotope_id]
        if active is not None:
            items = [s for s in items if s.active == active]
        if within_bounds is not None:
            items = [s for s in items if _point_in_bounds(s.position, within_bounds)]
        if limit is not None and limit >= 0:
            items = items[:limit]
        return items

    def update_source(self, source_id: str, **kwargs: Any) -> Optional[RadiationSource]:
        """Update fields of a source by keyword argument and return it.

        Unknown keys are ignored so callers can safely pass broad payloads.
        """

        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return None
            changed: Dict[str, Any] = {}
            for key, value in kwargs.items():
                if key == "position":
                    source.position = tuple(float(c) for c in value)
                    changed[key] = list(source.position)
                elif key == "activity_bq":
                    source.activity_bq = max(0.0, float(value))
                    changed[key] = source.activity_bq
                elif key == "radius":
                    source.radius = max(0.0, float(value))
                    changed[key] = source.radius
                elif hasattr(source, key):
                    old_value = getattr(source, key)
                    setattr(source, key, value)
                    changed[key] = {"old": old_value, "new": value}
            source.intensity_sv_per_h = self._estimate_source_intensity(source)
            self._emit(
                RadiationEventKind.SOURCE_UPDATED,
                {"source_id": source_id, "changed": changed},
            )
            return source

    def remove_source(self, source_id: str) -> Optional[RadiationSource]:
        """Remove and return the source, or ``None`` if it was not present."""

        with self._lock:
            source = self._sources.pop(source_id, None)
            if source is not None:
                self._emit(
                    RadiationEventKind.SOURCE_REMOVED,
                    {"source_id": source_id, "isotope_id": source.isotope_id},
                )
                self._refresh_stats_unlocked()
            return source

    # ------------------------------------------------------------------
    # Shielding management
    # ------------------------------------------------------------------

    def register_shielding(
        self,
        material_id: Optional[str] = None,
        type: ShieldingType = ShieldingType.LEAD,
        thickness_m: float = 0.05,
        radiation_type: RadiationType = RadiationType.GAMMA,
        position: Optional[Tuple[float, float, float]] = None,
        attenuation_coeff: Optional[float] = None,
        name: str = "",
    ) -> ShieldingMaterial:
        """Register a shielding slab. The attenuation coefficient is derived
        from the (material, radiation type) pair when not supplied."""

        with self._lock:
            material_id = material_id or _new_id("shld")
            type = _coerce_enum(ShieldingType, type, ShieldingType.LEAD)
            radiation_type = _coerce_enum(RadiationType, radiation_type, RadiationType.GAMMA)
            coeff = (
                float(attenuation_coeff)
                if attenuation_coeff is not None
                else _default_attenuation_coeff(type, radiation_type)
            )
            material = ShieldingMaterial(
                material_id=material_id,
                type=type,
                thickness_m=max(0.0, float(thickness_m)),
                attenuation_coeff=max(0.0, float(coeff)),
                density_kg_m3=_default_material_density(type),
                radiation_type=radiation_type,
                position=tuple(float(c) for c in position) if position else None,
                name=name,
            )
            self._shieldings[material_id] = material
            self._emit(
                RadiationEventKind.SHIELDING_REGISTERED,
                {"material_id": material_id, "type": _safe_value(type), "thickness_m": material.thickness_m},
            )
            self._refresh_stats_unlocked()
            return material

    def get_shielding(self, material_id: str) -> Optional[ShieldingMaterial]:
        """Return the shielding material with the given identifier."""

        with self._lock:
            return self._shieldings.get(material_id)

    def list_shieldings(
        self,
        type: Optional[ShieldingType] = None,
        radiation_type: Optional[RadiationType] = None,
        limit: Optional[int] = None,
    ) -> List[ShieldingMaterial]:
        """Return shielding materials optionally filtered by type."""

        with self._lock:
            items = list(self._shieldings.values())
        if type is not None:
            items = [m for m in items if m.type == type]
        if radiation_type is not None:
            items = [m for m in items if m.radiation_type == radiation_type]
        if limit is not None and limit >= 0:
            items = items[:limit]
        return items

    def update_shielding(self, material_id: str, **kwargs: Any) -> Optional[ShieldingMaterial]:
        """Update fields of a shielding material by keyword argument."""

        with self._lock:
            material = self._shieldings.get(material_id)
            if material is None:
                return None
            changed: Dict[str, Any] = {}
            for key, value in kwargs.items():
                if key == "type":
                    material.type = value
                    material.density_kg_m3 = _default_material_density(value)
                    material.attenuation_coeff = _default_attenuation_coeff(value, material.radiation_type)
                    changed[key] = value.value
                elif key == "radiation_type":
                    material.radiation_type = value
                    material.attenuation_coeff = _default_attenuation_coeff(material.type, value)
                    changed[key] = value.value
                elif key == "thickness_m":
                    material.thickness_m = max(0.0, float(value))
                    changed[key] = material.thickness_m
                elif key == "attenuation_coeff":
                    material.attenuation_coeff = max(0.0, float(value))
                    changed[key] = material.attenuation_coeff
                elif key == "position":
                    material.position = tuple(float(c) for c in value) if value else None
                    changed[key] = list(material.position) if material.position else None
                elif hasattr(material, key):
                    old_value = getattr(material, key)
                    setattr(material, key, value)
                    changed[key] = {"old": old_value, "new": value}
            self._emit(
                RadiationEventKind.SHIELDING_UPDATED,
                {"material_id": material_id, "changed": changed},
            )
            return material

    def remove_shielding(self, material_id: str) -> Optional[ShieldingMaterial]:
        """Remove and return the shielding material, or ``None``."""

        with self._lock:
            material = self._shieldings.pop(material_id, None)
            if material is not None:
                self._emit(
                    RadiationEventKind.SHIELDING_REMOVED,
                    {"material_id": material_id, "type": material.type.value},
                )
                self._refresh_stats_unlocked()
            return material

    # ------------------------------------------------------------------
    # Contamination zone management
    # ------------------------------------------------------------------

    def register_contamination_zone(
        self,
        zone_id: Optional[str] = None,
        name: str = "",
        bounds: Tuple[float, float, float, float, float, float] = (
            0.0, 0.0, 0.0, 1.0, 1.0, 1.0,
        ),
        level: ContaminationLevel = ContaminationLevel.LOW,
        isotope_id: str = "",
        activity_bq_m2: float = 0.0,
        volume_bq_m3: float = 0.0,
        spread_rate: Optional[float] = None,
    ) -> ContaminationZone:
        """Register a contamination zone with the given parameters.

        When ``level`` is omitted it is derived from the surface activity.
        ``spread_rate`` defaults to the config baseline when not supplied.
        """

        with self._lock:
            zone_id = zone_id or _new_id("zone")
            level = _coerce_enum(ContaminationLevel, level, None)
            if level is None:
                level = _classify_contamination_level(activity_bq_m2)
            if spread_rate is None:
                spread_rate = self._config.spread_baseline_rate
            zone = ContaminationZone(
                zone_id=zone_id,
                name=name or zone_id,
                bounds=tuple(float(b) for b in bounds),
                level=level,
                isotope_id=isotope_id,
                activity_bq_m2=max(0.0, float(activity_bq_m2)),
                volume_bq_m3=max(0.0, float(volume_bq_m3)),
                area=_classify_zone_area(bounds),
                spread_rate=float(spread_rate),
            )
            self._zones[zone_id] = zone
            self._emit(
                RadiationEventKind.ZONE_REGISTERED,
                {
                    "zone_id": zone_id,
                    "level": zone.level.name,
                    "area": zone.area,
                },
            )
            self._refresh_stats_unlocked()
            return zone

    def get_contamination_zone(self, zone_id: str) -> Optional[ContaminationZone]:
        """Return the contamination zone with the given identifier."""

        with self._lock:
            return self._zones.get(zone_id)

    def list_contamination_zones(
        self,
        level: Optional[ContaminationLevel] = None,
        isotope_id: Optional[str] = None,
        contains_point: Optional[Tuple[float, float, float]] = None,
        limit: Optional[int] = None,
    ) -> List[ContaminationZone]:
        """Return zones filtered by level, isotope, or point containment."""

        with self._lock:
            items = list(self._zones.values())
        if level is not None:
            items = [z for z in items if z.level == level]
        if isotope_id is not None:
            items = [z for z in items if z.isotope_id == isotope_id]
        if contains_point is not None:
            items = [z for z in items if _point_in_bounds(contains_point, z.bounds)]
        # Order by severity (descending) so callers see the worst zones first.
        items.sort(key=lambda z: z.level.value, reverse=True)
        if limit is not None and limit >= 0:
            items = items[:limit]
        return items

    def update_contamination_zone(self, zone_id: str, **kwargs: Any) -> Optional[ContaminationZone]:
        """Update fields of a contamination zone by keyword argument."""

        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return None
            changed: Dict[str, Any] = {}
            for key, value in kwargs.items():
                if key == "bounds":
                    zone.bounds = tuple(float(b) for b in value)
                    zone.area = _classify_zone_area(zone.bounds)
                    changed[key] = list(zone.bounds)
                elif key == "level":
                    new_level = _coerce_enum(ContaminationLevel, value, zone.level)
                    zone.level = new_level
                    changed[key] = new_level.name
                elif key == "activity_bq_m2":
                    zone.activity_bq_m2 = max(0.0, float(value))
                    # Re-bucket the severity when activity changes.
                    zone.level = _classify_contamination_level(zone.activity_bq_m2)
                    changed[key] = zone.activity_bq_m2
                elif key == "volume_bq_m3":
                    zone.volume_bq_m3 = max(0.0, float(value))
                    changed[key] = zone.volume_bq_m3
                elif key == "spread_rate":
                    zone.spread_rate = max(0.0, float(value))
                    changed[key] = zone.spread_rate
                elif hasattr(zone, key):
                    old_value = getattr(zone, key)
                    setattr(zone, key, value)
                    changed[key] = {"old": old_value, "new": value}
            self._emit(
                RadiationEventKind.ZONE_UPDATED,
                {"zone_id": zone_id, "changed": changed},
            )
            return zone

    def remove_contamination_zone(self, zone_id: str) -> Optional[ContaminationZone]:
        """Remove and return the contamination zone, or ``None``."""

        with self._lock:
            zone = self._zones.pop(zone_id, None)
            if zone is not None:
                self._emit(
                    RadiationEventKind.ZONE_REMOVED,
                    {"zone_id": zone_id, "level": zone.level.name},
                )
                self._refresh_stats_unlocked()
            return zone

    # ------------------------------------------------------------------
    # Dosimeter management
    # ------------------------------------------------------------------

    def register_dosimeter(
        self,
        dosimeter_id: Optional[str] = None,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        alarm_threshold_sv: Optional[float] = None,
        name: str = "",
        active: bool = True,
    ) -> Dosimeter:
        """Register a dosimeter, deriving the alarm threshold from config."""

        with self._lock:
            dosimeter_id = dosimeter_id or _new_id("dsm")
            threshold = (
                float(alarm_threshold_sv)
                if alarm_threshold_sv is not None
                else self._config.default_alarm_threshold_sv
            )
            dosimeter = Dosimeter(
                dosimeter_id=dosimeter_id,
                position=tuple(float(c) for c in position),
                alarm_threshold_sv=max(0.0, threshold),
                name=name,
                active=active,
            )
            self._dosimeters[dosimeter_id] = dosimeter
            self._emit(
                RadiationEventKind.DOSIMETER_REGISTERED,
                {"dosimeter_id": dosimeter_id, "threshold": dosimeter.alarm_threshold_sv},
            )
            self._refresh_stats_unlocked()
            return dosimeter

    def get_dosimeter(self, dosimeter_id: str) -> Optional[Dosimeter]:
        """Return the dosimeter with the given identifier."""

        with self._lock:
            return self._dosimeters.get(dosimeter_id)

    def list_dosimeters(
        self,
        active: Optional[bool] = None,
        alarming: Optional[bool] = None,
        within_bounds: Optional[Tuple[float, float, float, float, float, float]] = None,
        limit: Optional[int] = None,
    ) -> List[Dosimeter]:
        """Return dosimeters filtered by activity, alarm state, or bounds."""

        with self._lock:
            items = list(self._dosimeters.values())
        if active is not None:
            items = [d for d in items if d.active == active]
        if alarming is not None:
            items = [d for d in items if d.is_alarming == alarming]
        if within_bounds is not None:
            items = [d for d in items if _point_in_bounds(d.position, within_bounds)]
        if limit is not None and limit >= 0:
            items = items[:limit]
        return items

    def update_dosimeter(self, dosimeter_id: str, **kwargs: Any) -> Optional[Dosimeter]:
        """Update fields of a dosimeter by keyword argument."""

        with self._lock:
            dosimeter = self._dosimeters.get(dosimeter_id)
            if dosimeter is None:
                return None
            changed: Dict[str, Any] = {}
            for key, value in kwargs.items():
                if key == "position":
                    dosimeter.position = tuple(float(c) for c in value)
                    changed[key] = list(dosimeter.position)
                elif key == "alarm_threshold_sv":
                    dosimeter.alarm_threshold_sv = max(0.0, float(value))
                    changed[key] = dosimeter.alarm_threshold_sv
                elif key == "cumulative_dose_sv":
                    dosimeter.cumulative_dose_sv = max(0.0, float(value))
                    changed[key] = dosimeter.cumulative_dose_sv
                elif hasattr(dosimeter, key):
                    old_value = getattr(dosimeter, key)
                    setattr(dosimeter, key, value)
                    changed[key] = {"old": old_value, "new": value}
            # Re-evaluate alarm state after the update.
            dosimeter.is_alarming = dosimeter.cumulative_dose_sv >= dosimeter.alarm_threshold_sv
            self._emit(
                RadiationEventKind.DOSIMETER_UPDATED,
                {"dosimeter_id": dosimeter_id, "changed": changed},
            )
            return dosimeter

    def remove_dosimeter(self, dosimeter_id: str) -> Optional[Dosimeter]:
        """Remove and return the dosimeter, or ``None``."""

        with self._lock:
            dosimeter = self._dosimeters.pop(dosimeter_id, None)
            if dosimeter is not None:
                self._emit(
                    RadiationEventKind.DOSIMETER_REMOVED,
                    {"dosimeter_id": dosimeter_id},
                )
                self._refresh_stats_unlocked()
            return dosimeter

    def acknowledge_dosimeter_alarm(self, dosimeter_id: str) -> Optional[Dosimeter]:
        """Clear the alarm flag on a dosimeter without resetting its dose."""

        with self._lock:
            dosimeter = self._dosimeters.get(dosimeter_id)
            if dosimeter is None:
                return None
            if dosimeter.is_alarming:
                dosimeter.is_alarming = False
                self._emit(
                    RadiationEventKind.ALARM_CLEARED,
                    {"dosimeter_id": dosimeter_id, "cumulative_dose_sv": dosimeter.cumulative_dose_sv},
                )
            return dosimeter

    # ------------------------------------------------------------------
    # Detector management
    # ------------------------------------------------------------------

    def register_detector(
        self,
        detector_id: Optional[str] = None,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        type: RadiationType = RadiationType.GAMMA,
        range_sv_per_h: float = 10.0,
        sensitivity: float = 1.0,
        status: DetectorStatus = DetectorStatus.IDLE,
        name: str = "",
    ) -> RadiationDetector:
        """Register a radiation detector with the given sensitivity."""

        with self._lock:
            detector_id = detector_id or _new_id("det")
            type = _coerce_enum(RadiationType, type, RadiationType.GAMMA)
            status = _coerce_enum(DetectorStatus, status, DetectorStatus.IDLE)
            detector = RadiationDetector(
                detector_id=detector_id,
                position=tuple(float(c) for c in position),
                type=type,
                range_sv_per_h=max(1.0e-6, float(range_sv_per_h)),
                sensitivity=max(0.0, float(sensitivity)),
                status=status,
                name=name,
            )
            self._detectors[detector_id] = detector
            self._emit(
                RadiationEventKind.DETECTOR_REGISTERED,
                {"detector_id": detector_id, "type": _safe_value(type)},
            )
            self._refresh_stats_unlocked()
            return detector

    def get_detector(self, detector_id: str) -> Optional[RadiationDetector]:
        """Return the detector with the given identifier."""

        with self._lock:
            return self._detectors.get(detector_id)

    def list_detectors(
        self,
        type: Optional[RadiationType] = None,
        status: Optional[DetectorStatus] = None,
        within_bounds: Optional[Tuple[float, float, float, float, float, float]] = None,
        limit: Optional[int] = None,
    ) -> List[RadiationDetector]:
        """Return detectors filtered by type, status, or spatial bounds."""

        with self._lock:
            items = list(self._detectors.values())
        if type is not None:
            items = [d for d in items if d.type == type]
        if status is not None:
            items = [d for d in items if d.status == status]
        if within_bounds is not None:
            items = [d for d in items if _point_in_bounds(d.position, within_bounds)]
        if limit is not None and limit >= 0:
            items = items[:limit]
        return items

    def update_detector(self, detector_id: str, **kwargs: Any) -> Optional[RadiationDetector]:
        """Update fields of a detector by keyword argument."""

        with self._lock:
            detector = self._detectors.get(detector_id)
            if detector is None:
                return None
            changed: Dict[str, Any] = {}
            for key, value in kwargs.items():
                if key == "position":
                    detector.position = tuple(float(c) for c in value)
                    changed[key] = list(detector.position)
                elif key == "range_sv_per_h":
                    detector.range_sv_per_h = max(1.0e-6, float(value))
                    changed[key] = detector.range_sv_per_h
                elif key == "sensitivity":
                    detector.sensitivity = max(0.0, float(value))
                    changed[key] = detector.sensitivity
                elif key == "status":
                    detector.status = value
                    changed[key] = value.value
                elif key == "type":
                    detector.type = value
                    changed[key] = value.value
                elif hasattr(detector, key):
                    old_value = getattr(detector, key)
                    setattr(detector, key, value)
                    changed[key] = {"old": old_value, "new": value}
            self._emit(
                RadiationEventKind.DETECTOR_UPDATED,
                {"detector_id": detector_id, "changed": changed},
            )
            return detector

    def remove_detector(self, detector_id: str) -> Optional[RadiationDetector]:
        """Remove and return the detector, or ``None``."""

        with self._lock:
            detector = self._detectors.pop(detector_id, None)
            if detector is not None:
                self._emit(
                    RadiationEventKind.DETECTOR_REMOVED,
                    {"detector_id": detector_id},
                )
                self._refresh_stats_unlocked()
            return detector

    def calibrate_detector(
        self,
        detector_id: str,
        calibration_sv_per_h: Optional[float] = None,
    ) -> Optional[RadiationDetector]:
        """Recalibrate a detector, optionally adjusting its sensitivity.

        When a known dose rate is supplied the sensitivity is scaled so
        that the next reading matches the supplied value. The calibration
        age is reset to zero and the status is set to ``ACTIVE``.
        """

        with self._lock:
            detector = self._detectors.get(detector_id)
            if detector is None:
                return None
            if calibration_sv_per_h is not None and detector.reading_sv_per_h > 0.0:
                ratio = float(calibration_sv_per_h) / detector.reading_sv_per_h
                detector.sensitivity = max(0.01, detector.sensitivity * ratio)
            detector.calibration_age_s = 0.0
            detector.status = DetectorStatus.ACTIVE
            self._emit(
                RadiationEventKind.DETECTOR_CALIBRATED,
                {"detector_id": detector_id, "sensitivity": detector.sensitivity},
            )
            return detector

    # ------------------------------------------------------------------
    # Physics: decay, intensity, attenuation, dose
    # ------------------------------------------------------------------

    def compute_half_life(self, isotope_id: str) -> Optional[float]:
        """Return the half-life (s) of an isotope, or ``None`` if unknown."""

        with self._lock:
            isotope = self._isotopes.get(isotope_id)
        if isotope is None:
            return None
        return isotope.half_life_s

    def compute_decay(
        self,
        isotope_id: str,
        initial_activity_bq: float,
        elapsed_s: float,
    ) -> Optional[float]:
        """Return the remaining activity after ``elapsed_s`` seconds.

        Implements ``A(t) = A0 * exp(-lambda * t)``. Returns the input
        activity unchanged for stable isotopes.
        """

        with self._lock:
            isotope = self._isotopes.get(isotope_id)
        if isotope is None:
            return None
        if isotope.is_stable or elapsed_s <= 0.0:
            return float(initial_activity_bq)
        return float(initial_activity_bq) * math.exp(-isotope.decay_constant * elapsed_s)

    def compute_intensity(
        self,
        source_id: str,
        point: Tuple[float, float, float],
    ) -> Optional[float]:
        """Return the unshielded dose rate (Sv/h) at ``point`` from a source.

        Combines the source's current intensity with inverse-square falloff.
        Returns ``None`` for unknown sources.
        """

        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return None
            isotope = self._isotopes.get(source.isotope_id)
            distance = _distance_3d(source.position, point)
            distance = max(distance, source.radius, 0.01)
            base_sv_per_h = source.intensity_sv_per_h
            if isotope is not None:
                qf = _quality_factor(isotope.radiation_type, isotope.energy_mev)
                energy_j = isotope.energy_mev * _MEV_TO_JOULE
                # Rough intensity: activity * energy / (4 pi r^2) scaled by QF.
                if distance > 0.0 and source.activity_bq > 0.0:
                    fluence = source.activity_bq * energy_j / (_4PI * distance * distance)
                    # Convert J/s/m^2 to Sv/h using a coarse constant.
                    base_sv_per_h = fluence * qf * 3600.0 * 1.0e3
            return max(0.0, base_sv_per_h)

    def compute_distance_attenuation(
        self,
        source_position: Tuple[float, float, float],
        target_position: Tuple[float, float, float],
        source_radius: float = 0.1,
    ) -> float:
        """Return the inverse-square attenuation factor between two points.

        The result is a dimensionless multiplier in ``(0, 1]`` representing
        the fraction of intensity that reaches the target from a unit source.
        """

        distance = _distance_3d(source_position, target_position)
        distance = max(distance, source_radius, 0.01)
        return 1.0 / (_4PI * distance * distance)

    def compute_attenuation(
        self,
        intensity_sv_per_h: float,
        material_id: str,
    ) -> Optional[float]:
        """Return the intensity after passing through a shielding material.

        Implements ``I = I0 * exp(-mu * x)``. Returns ``None`` for unknown
        materials.
        """

        with self._lock:
            material = self._shieldings.get(material_id)
        if material is None:
            return None
        if material.attenuation_coeff <= 0.0:
            return float(intensity_sv_per_h)
        return float(intensity_sv_per_h) * math.exp(
            -material.attenuation_coeff * material.thickness_m
        )

    def compute_hvl(self, material_id: str) -> Optional[float]:
        """Return the half-value layer (m) of a shielding material."""

        with self._lock:
            material = self._shieldings.get(material_id)
        if material is None:
            return None
        if material.attenuation_coeff <= 0.0:
            return math.inf
        return _LN2 / material.attenuation_coeff

    def compute_quality_factor(
        self,
        radiation_type: RadiationType,
        energy_mev: float = 0.0,
    ) -> float:
        """Return the radiation weighting factor for dose conversion."""

        return _quality_factor(radiation_type, energy_mev)

    def compute_dose(
        self,
        intensity_sv_per_h: float,
        exposure_s: float,
    ) -> float:
        """Return the absorbed dose (Sv) for an exposure duration.

        ``D = dose_rate * time``. Negative exposures are clamped to zero.
        """

        if exposure_s <= 0.0 or intensity_sv_per_h <= 0.0:
            return 0.0
        return float(intensity_sv_per_h) * float(exposure_s) / _SECONDS_PER_HOUR

    def compute_dose_rate(
        self,
        dose_sv: float,
        exposure_s: float,
    ) -> float:
        """Return the dose rate (Sv/h) implied by a dose and exposure time."""

        if exposure_s <= 0.0:
            return 0.0
        return float(dose_sv) * _SECONDS_PER_HOUR / float(exposure_s)

    def compute_shielding_required(
        self,
        intensity_sv_per_h: float,
        target_sv_per_h: float,
        material_id: str,
    ) -> Optional[float]:
        """Return the shielding thickness (m) needed to reach a target rate.

        Solves ``I0 * exp(-mu * x) = I_target`` for ``x``. Returns ``None``
        for unknown materials, ``0.0`` when the target is already met, and
        ``math.inf`` when the material cannot attenuate the radiation.
        """

        with self._lock:
            material = self._shieldings.get(material_id)
        if material is None:
            return None
        if target_sv_per_h >= intensity_sv_per_h:
            return 0.0
        if material.attenuation_coeff <= 0.0:
            return math.inf
        if target_sv_per_h <= 0.0:
            return math.inf
        return math.log(intensity_sv_per_h / target_sv_per_h) / material.attenuation_coeff

    def check_contamination_spread(
        self,
        zone_id: str,
        time_horizon_s: float,
    ) -> Optional[Dict[str, Any]]:
        """Estimate how far a zone will spread within ``time_horizon_s``.

        Returns a dictionary with the projected bounds and activity decay.
        Returns ``None`` when the zone does not exist.
        """

        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return None
            isotope = self._isotopes.get(zone.isotope_id)
            decay_factor = 1.0
            if isotope is not None and not isotope.is_stable:
                decay_factor = math.exp(-isotope.decay_constant * time_horizon_s)
            spread = max(0.0, zone.spread_rate) * time_horizon_s
            min_x, min_y, min_z, max_x, max_y, max_z = zone.bounds
            projected_bounds = (
                min_x - spread,
                min_y - spread,
                min_z,
                max_x + spread,
                max_y + spread,
                max_z,
            )
            return {
                "zone_id": zone_id,
                "time_horizon_s": time_horizon_s,
                "spread_m": spread,
                "projected_bounds": list(projected_bounds),
                "activity_factor": decay_factor,
                "projected_activity_bq_m2": zone.activity_bq_m2 * decay_factor,
            }

    # ------------------------------------------------------------------
    # Internal physics helpers
    # ------------------------------------------------------------------

    def _estimate_source_intensity(self, source: RadiationSource) -> float:
        """Estimate the dose rate at 1 m from the source (Sv/h).

        Uses the isotope's energy and quality factor in a simplified
        point-source model. Returns 0.0 when the isotope is unknown or
        inactive.
        """

        if not source.active or source.activity_bq <= 0.0:
            return 0.0
        isotope = self._isotopes.get(source.isotope_id)
        if isotope is None:
            return 0.0
        energy_j = isotope.energy_mev * _MEV_TO_JOULE
        qf = _quality_factor(isotope.radiation_type, isotope.energy_mev)
        unit_distance = max(source.radius, 0.01, 1.0)
        fluence = source.activity_bq * energy_j / (_4PI * unit_distance * unit_distance)
        return max(0.0, fluence * qf * 3600.0 * 1.0e3)

    def _intensity_at_point_unlocked(
        self,
        point: Tuple[float, float, float],
        radiation_type: Optional[RadiationType] = None,
    ) -> float:
        """Return the total dose rate (Sv/h) reaching ``point``.

        Sums the contribution of every active source, applies inverse-square
        falloff, and attenuates the result by every shielding material whose
        radiation type matches the source's emitted radiation (when enabled).
        """

        total: float = 0.0
        for source in self._sources.values():
            if not source.active or source.activity_bq <= 0.0:
                continue
            isotope = self._isotopes.get(source.isotope_id)
            if isotope is None:
                continue
            if radiation_type is not None and isotope.radiation_type != radiation_type:
                continue
            distance = _distance_3d(source.position, point)
            distance = max(distance, source.radius, 0.01)
            energy_j = isotope.energy_mev * _MEV_TO_JOULE
            qf = _quality_factor(isotope.radiation_type, isotope.energy_mev)
            fluence = source.activity_bq * energy_j / (_4PI * distance * distance)
            intensity = max(0.0, fluence * qf * 3600.0 * 1.0e3)
            if self._config.shielding_enabled:
                for material in self._shieldings.values():
                    if material.radiation_type != isotope.radiation_type:
                        continue
                    if material.attenuation_coeff <= 0.0:
                        continue
                    intensity *= math.exp(-material.attenuation_coeff * material.thickness_m)
            total += intensity

        # Add ambient contribution from contamination zones that contain
        # the query point, weighted by the zone's severity bucket.
        for zone in self._zones.values():
            if zone.level == ContaminationLevel.CLEAN:
                continue
            if not _point_in_bounds(point, zone.bounds):
                continue
            total += _level_to_dose_rate_sv_per_h(zone.level)

        # Add a constant background baseline.
        total += self._config.background_radiation_usv_per_h / _MICROS_PER_MILLI / _MILLISV_PER_SV
        return total

    # ------------------------------------------------------------------
    # Measurement API
    # ------------------------------------------------------------------

    def measure_radiation(
        self,
        point: Tuple[float, float, float],
        radiation_type: Optional[RadiationType] = None,
    ) -> Dict[str, Any]:
        """Return a synthetic dose-rate measurement at ``point``."""

        radiation_type = _coerce_enum(RadiationType, radiation_type, None)
        with self._lock:
            total = self._intensity_at_point_unlocked(point, radiation_type)
            # Decompose the contribution by radiation type for telemetry.
            breakdown: Dict[str, float] = {}
            for rtype in RadiationType:
                breakdown[rtype.value] = self._intensity_at_point_unlocked(point, rtype)
            self._stats.total_measurements += 1
            self._emit(
                RadiationEventKind.DETECTOR_READING,
                {
                    "point": list(point),
                    "reading_sv_per_h": total,
                    "breakdown": breakdown,
                    "filtered_type": radiation_type.value if radiation_type else None,
                },
            )
        return {
            "point": list(point),
            "reading_sv_per_h": total,
            "reading_usv_per_h": total * 1.0e6,
            "formatted": _format_dose(total),
            "breakdown": breakdown,
            "filtered_type": radiation_type.value if radiation_type else None,
            "timestamp": _now_ts(),
        }

    def measure_dose(
        self,
        point: Tuple[float, float, float],
        exposure_s: float,
    ) -> Dict[str, Any]:
        """Return the accumulated dose (Sv) at ``point`` over ``exposure_s``."""

        reading = self.measure_radiation(point)
        dose_sv = self.compute_dose(reading["reading_sv_per_h"], exposure_s)
        return {
            "point": list(point),
            "exposure_s": exposure_s,
            "dose_rate_sv_per_h": reading["reading_sv_per_h"],
            "dose_sv": dose_sv,
            "dose_msv": dose_sv * 1.0e3,
            "formatted": _format_dose(dose_sv),
            "timestamp": _now_ts(),
        }

    def measure_contamination(
        self,
        point: Tuple[float, float, float],
    ) -> Dict[str, Any]:
        """Return contamination data for the zone containing ``point``."""

        with self._lock:
            containing = [
                z for z in self._zones.values()
                if _point_in_bounds(point, z.bounds)
            ]
            if not containing:
                return {
                    "point": list(point),
                    "contaminated": False,
                    "level": ContaminationLevel.CLEAN.name,
                    "activity_bq_m2": 0.0,
                    "volume_bq_m3": 0.0,
                    "zone_id": None,
                    "isotope_id": None,
                    "timestamp": _now_ts(),
                }
            # Pick the most severe zone at this point.
            containing.sort(key=lambda z: z.level.value, reverse=True)
            zone = containing[0]
            isotope = self._isotopes.get(zone.isotope_id)
            self._stats.total_measurements += 1
        return {
            "point": list(point),
            "contaminated": zone.level != ContaminationLevel.CLEAN,
            "level": zone.level.name,
            "level_value": zone.level.value,
            "activity_bq_m2": zone.activity_bq_m2,
            "volume_bq_m3": zone.volume_bq_m3,
            "zone_id": zone.zone_id,
            "zone_name": zone.name,
            "isotope_id": zone.isotope_id,
            "isotope_name": isotope.name if isotope else None,
            "timestamp": _now_ts(),
        }

    def get_radiation_map(
        self,
        bounds: Optional[Tuple[float, float, float, float, float, float]] = None,
        resolution: int = 10,
    ) -> Dict[str, Any]:
        """Return a coarse 2D radiation heat map over the world bounds.

        The map is sampled on a regular grid in the z=0 plane. Each cell
        records the dose rate in Sv/h. ``resolution`` is clamped to a sane
        range to bound computation cost.
        """

        with self._lock:
            world_bounds = bounds or self._config.world_bounds
            res = int(_clamp(resolution, 2, 64))
            min_x, min_y, _, max_x, max_y, _ = world_bounds
            step_x = (max_x - min_x) / max(1, res - 1)
            step_y = (max_y - min_y) / max(1, res - 1)
            grid: List[List[float]] = []
            max_value = 0.0
            for j in range(res):
                row: List[float] = []
                y = min_y + j * step_y
                for i in range(res):
                    x = min_x + i * step_x
                    value = self._intensity_at_point_unlocked((x, y, 0.0))
                    row.append(value)
                    if value > max_value:
                        max_value = value
                grid.append(row)
        return {
            "bounds": list(world_bounds),
            "resolution": res,
            "grid": grid,
            "max_sv_per_h": max_value,
            "unit": "Sv/h",
            "timestamp": _now_ts(),
        }

    def get_dose_map(
        self,
        exposure_s: float = 1.0,
        bounds: Optional[Tuple[float, float, float, float, float, float]] = None,
        resolution: int = 10,
    ) -> Dict[str, Any]:
        """Return a 2D accumulated-dose map (Sv) for the given exposure."""

        radiation_map = self.get_radiation_map(bounds=bounds, resolution=resolution)
        dose_grid: List[List[float]] = []
        max_dose = 0.0
        for row in radiation_map["grid"]:
            dose_row = [self.compute_dose(v, exposure_s) for v in row]
            dose_grid.append(dose_row)
            for d in dose_row:
                if d > max_dose:
                    max_dose = d
        return {
            "bounds": radiation_map["bounds"],
            "resolution": radiation_map["resolution"],
            "exposure_s": exposure_s,
            "grid": dose_grid,
            "max_dose_sv": max_dose,
            "unit": "Sv",
            "timestamp": _now_ts(),
        }

    # ------------------------------------------------------------------
    # AI methods
    # ------------------------------------------------------------------

    def ai_predict_contamination_spread(
        self,
        zone_id: str,
        horizon_s: float = 3600.0,
        wind_vector: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> Dict[str, Any]:
        """Predict the spread of a contamination zone using a simple model.

        The model blends isotropic spread with an anisotropic drift driven
        by the supplied wind vector. Decay is applied to the projected
        activity. The function returns a description suitable for gameplay
        AI planners (e.g. recommending evacuation corridors).
        """

        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return {
                    "zone_id": zone_id,
                    "error": "unknown zone",
                    "predictions": [],
                }
            isotope = self._isotopes.get(zone.isotope_id)
            decay_factor = 1.0
            if isotope is not None and not isotope.is_stable:
                decay_factor = math.exp(-isotope.decay_constant * horizon_s)
            multiplier = _level_to_multiplier(zone.level)
            spread = (
                max(0.0, zone.spread_rate)
                + multiplier * 0.05
            ) * horizon_s
            drift_x = wind_vector[0] * horizon_s * 0.01
            drift_y = wind_vector[1] * horizon_s * 0.01
            min_x, min_y, min_z, max_x, max_y, max_z = zone.bounds
            predicted_bounds = (
                min_x - spread + drift_x,
                min_y - spread + drift_y,
                min_z,
                max_x + spread + drift_x,
                max_y + spread + drift_y,
                max_z,
            )
            projected_activity = zone.activity_bq_m2 * decay_factor
            projected_level = _classify_contamination_level(projected_activity)
            # Identify which registered zones overlap the projected bounds.
            affected_zones: List[str] = []
            for other_id, other in self._zones.items():
                if other_id == zone_id:
                    continue
                if self._bounds_overlap(other.bounds, predicted_bounds):
                    affected_zones.append(other_id)
            self._stats.total_ai_predictions += 1
            self._emit(
                RadiationEventKind.AI_PREDICTION,
                {
                    "model": "contamination_spread",
                    "zone_id": zone_id,
                    "horizon_s": horizon_s,
                    "predicted_level": projected_level.name,
                },
            )
        return {
            "zone_id": zone_id,
            "horizon_s": horizon_s,
            "decay_factor": decay_factor,
            "spread_m": spread,
            "drift": [drift_x, drift_y, 0.0],
            "predicted_bounds": list(predicted_bounds),
            "predicted_activity_bq_m2": projected_activity,
            "predicted_level": projected_level.name,
            "affected_zones": affected_zones,
            "recommendation": self._spread_recommendation(projected_level, affected_zones),
            "timestamp": _now_ts(),
        }

    def _spread_recommendation(
        self,
        level: ContaminationLevel,
        affected: Sequence[str],
    ) -> str:
        """Produce a gameplay-facing recommendation for a predicted spread."""

        if level == ContaminationLevel.LETHAL:
            return "evacuate immediately and seal affected corridors"
        if level == ContaminationLevel.HIGH:
            return "restrict access and deploy remote drones"
        if level == ContaminationLevel.MODERATE:
            return "issue protective-equipment order and monitor dosimeters"
        if level == ContaminationLevel.LOW:
            return "post caution signage and re-measure in 15 minutes"
        return "no action required"

    def _bounds_overlap(
        self,
        a: Tuple[float, float, float, float, float, float],
        b: Tuple[float, float, float, float, float, float],
    ) -> bool:
        """Return True when two axis-aligned bounding boxes overlap."""

        return not (
            a[0] > b[3]
            or a[3] < b[0]
            or a[1] > b[4]
            or a[4] < b[1]
            or a[2] > b[5]
            or a[5] < b[2]
        )

    def ai_optimize_shielding(
        self,
        source_id: str,
        target_point: Tuple[float, float, float],
        target_sv_per_h: float,
        candidate_material_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Pick the most mass-efficient shielding combination to hit a target.

        Evaluates each candidate material and returns the one requiring the
        smallest thickness (and therefore the least mass per unit area) to
        bring the dose rate at ``target_point`` below ``target_sv_per_h``.
        """

        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return {"source_id": source_id, "error": "unknown source"}
            baseline = self._intensity_at_point_unlocked(target_point)
            candidates: List[str] = list(candidate_material_ids) if candidate_material_ids else list(self._shieldings.keys())
            results: List[Dict[str, Any]] = []
            for material_id in candidates:
                material = self._shieldings.get(material_id)
                if material is None:
                    continue
                thickness = self.compute_shielding_required(
                    baseline, target_sv_per_h, material_id
                )
                if thickness is None:
                    continue
                mass_per_m2 = (
                    material.density_kg_m3 * thickness
                    if thickness != math.inf
                    else math.inf
                )
                results.append({
                    "material_id": material_id,
                    "type": material.type.value,
                    "thickness_m": thickness,
                    "mass_per_m2": mass_per_m2,
                    "hvl_m": material.half_value_layer,
                    "attenuation_coeff": material.attenuation_coeff,
                })
            results.sort(key=lambda r: r["mass_per_m2"])
            best = results[0] if results else None
            self._stats.total_ai_predictions += 1
            self._emit(
                RadiationEventKind.AI_PREDICTION,
                {
                    "model": "shielding_optimization",
                    "source_id": source_id,
                    "baseline_sv_per_h": baseline,
                    "best_material": best["material_id"] if best else None,
                },
            )
        return {
            "source_id": source_id,
            "target_point": list(target_point),
            "target_sv_per_h": target_sv_per_h,
            "baseline_sv_per_h": baseline,
            "best": best,
            "candidates": results,
            "timestamp": _now_ts(),
        }

    def ai_assess_radiation_risk(
        self,
        point: Tuple[float, float, float],
        exposure_s: float = 3600.0,
    ) -> Dict[str, Any]:
        """Assess the radiological risk to a character at ``point``.

        Combines the measured dose rate with exposure time to project an
        accumulated dose, then maps the dose onto a qualitative risk tier
        and a list of recommended gameplay actions.
        """

        reading = self.measure_radiation(point)
        dose_sv = self.compute_dose(reading["reading_sv_per_h"], exposure_s)
        contamination = self.measure_contamination(point)
        with self._lock:
            self._stats.total_ai_predictions += 1
            self._emit(
                RadiationEventKind.AI_PREDICTION,
                {
                    "model": "risk_assessment",
                    "point": list(point),
                    "dose_sv": dose_sv,
                },
            )
        risk_tier, effects, recommendations = self._risk_tier_for_dose(dose_sv)
        return {
            "point": list(point),
            "exposure_s": exposure_s,
            "dose_rate_sv_per_h": reading["reading_sv_per_h"],
            "projected_dose_sv": dose_sv,
            "projected_dose_msv": dose_sv * 1.0e3,
            "formatted_dose": _format_dose(dose_sv),
            "contamination": contamination,
            "risk_tier": risk_tier,
            "health_effects": effects,
            "recommendations": recommendations,
            "timestamp": _now_ts(),
        }

    def _risk_tier_for_dose(
        self,
        dose_sv: float,
    ) -> Tuple[str, List[str], List[str]]:
        """Return a qualitative risk tier, health effects, and advice."""

        if dose_sv < 1.0e-4:
            return (
                "negligible",
                ["no observable health impact"],
                ["continue normal activity"],
            )
        if dose_sv < 1.0e-3:
            return (
                "minimal",
                ["within natural background variation"],
                ["monitor dosimeter periodically"],
            )
        if dose_sv < 0.1:
            return (
                "low",
                ["slightly elevated cancer risk over lifetime"],
                ["limit time in zone", "check protective equipment"],
            )
        if dose_sv < 1.0:
            return (
                "moderate",
                ["mild radiation sickness possible at upper end"],
                ["rotate personnel", "issue stable iodine if iodine isotopes present"],
            )
        if dose_sv < 5.0:
            return (
                "high",
                ["acute radiation syndrome likely, nausea and vomiting"],
                ["evacuate immediately", "begin medical screening"],
            )
        if dose_sv < 20.0:
            return (
                "severe",
                ["severe ARS, bone marrow suppression, fatal without treatment"],
                ["full evacuation", "hospitalize exposed personnel"],
            )
        return (
            "lethal",
            ["central nervous system failure, death within days"],
            ["abandon area", "activate emergency protocols"],
        )

    # ------------------------------------------------------------------
    # Tick / simulation
    # ------------------------------------------------------------------

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance the simulation by ``dt`` seconds (scaled by time_scale).

        The tick performs four jobs: advances decay of every source,
        spreads contamination zones, integrates dose on dosimeters, and
        refreshes detector readings. It returns a summary of the work
        performed so callers can drive telemetry.
        """

        with self._lock:
            scaled_dt = max(0.0, float(dt)) * self._config.time_scale
            self._simulation_time_s += scaled_dt
            self._stats.last_tick_dt = scaled_dt
            self._stats.last_tick_ts = _now_ts()
            decay_steps = 0
            spread_events = 0
            alarms_raised = 0
            peak_rate = self._stats.peak_dose_rate_sv_per_h

            # 1. Advance radioactive decay on every active source.
            if self._config.decay_enabled and scaled_dt > 0.0:
                for source in self._sources.values():
                    if not source.active:
                        continue
                    isotope = self._isotopes.get(source.isotope_id)
                    if isotope is None or isotope.is_stable:
                        source.age_s += scaled_dt
                        continue
                    source.activity_bq *= math.exp(-isotope.decay_constant * scaled_dt)
                    source.age_s += scaled_dt
                    source.intensity_sv_per_h = self._estimate_source_intensity(source)
                    decay_steps += 1

            # 2. Spread contamination zones and decay their activity.
            if self._config.contamination_spread_enabled and scaled_dt > 0.0:
                for zone in self._zones.values():
                    if zone.level == ContaminationLevel.CLEAN:
                        continue
                    isotope = self._isotopes.get(zone.isotope_id)
                    decay_factor = 1.0
                    if isotope is not None and not isotope.is_stable:
                        decay_factor = math.exp(-isotope.decay_constant * scaled_dt)
                    zone.activity_bq_m2 *= decay_factor
                    zone.volume_bq_m3 *= decay_factor
                    zone.age_s += scaled_dt
                    expansion = zone.spread_rate * scaled_dt
                    if expansion > 0.0:
                        min_x, min_y, min_z, max_x, max_y, max_z = zone.bounds
                        zone.bounds = (
                            min_x - expansion,
                            min_y - expansion,
                            min_z,
                            max_x + expansion,
                            max_y + expansion,
                            max_z,
                        )
                        zone.area = _classify_zone_area(zone.bounds)
                        spread_events += 1
                    new_level = _classify_contamination_level(zone.activity_bq_m2)
                    if new_level != zone.level:
                        zone.level = new_level

            # 3. Integrate dose on every active dosimeter.
            if self._config.dosimeter_integration_enabled and scaled_dt > 0.0:
                for dosimeter in self._dosimeters.values():
                    if not dosimeter.active:
                        continue
                    rate = self._intensity_at_point_unlocked(dosimeter.position)
                    dose_step = rate * scaled_dt / _SECONDS_PER_HOUR
                    dosimeter.cumulative_dose_sv += dose_step
                    dosimeter.dose_rate_sv_per_h = rate
                    self._stats.total_dose_sv += dose_step
                    if rate > peak_rate:
                        peak_rate = rate
                    if (
                        dosimeter.cumulative_dose_sv >= dosimeter.alarm_threshold_sv
                        and not dosimeter.is_alarming
                    ):
                        dosimeter.is_alarming = True
                        alarms_raised += 1
                        self._emit(
                            RadiationEventKind.DOSIMETER_ALARM,
                            {
                                "dosimeter_id": dosimeter.dosimeter_id,
                                "cumulative_dose_sv": dosimeter.cumulative_dose_sv,
                                "threshold_sv": dosimeter.alarm_threshold_sv,
                            },
                        )

            # 4. Refresh detector readings and apply overload transitions.
            for detector in self._detectors.values():
                if detector.status == DetectorStatus.OFFLINE:
                    continue
                rate = self._intensity_at_point_unlocked(detector.position, detector.type)
                # Apply the detector sensitivity calibration.
                detector.reading_sv_per_h = rate * detector.sensitivity
                detector.calibration_age_s += scaled_dt
                if self._config.detector_auto_overload:
                    if detector.reading_sv_per_h > detector.range_sv_per_h:
                        if detector.status != DetectorStatus.OVERLOADED:
                            detector.status = DetectorStatus.OVERLOADED
                    elif detector.status == DetectorStatus.OVERLOADED:
                        detector.status = DetectorStatus.ACTIVE
                    elif detector.status == DetectorStatus.IDLE:
                        detector.status = DetectorStatus.ACTIVE
                if rate > peak_rate:
                    peak_rate = rate

            self._stats.peak_dose_rate_sv_per_h = peak_rate
            self._stats.total_decay_steps += decay_steps
            self._stats.total_spread_events += spread_events
            self._stats.total_alarms += alarms_raised
            self._refresh_stats_unlocked()
            self._emit(
                RadiationEventKind.TICK,
                {
                    "dt": scaled_dt,
                    "simulation_time_s": self._simulation_time_s,
                    "decay_steps": decay_steps,
                    "spread_events": spread_events,
                    "alarms_raised": alarms_raised,
                },
            )
            return {
                "dt": scaled_dt,
                "simulation_time_s": self._simulation_time_s,
                "decay_steps": decay_steps,
                "spread_events": spread_events,
                "alarms_raised": alarms_raised,
                "peak_dose_rate_sv_per_h": peak_rate,
            }

    # ------------------------------------------------------------------
    # Configuration, status, stats, snapshot, events
    # ------------------------------------------------------------------

    def get_config(self) -> RadiationConfig:
        """Return the current configuration object."""

        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Dict[str, Any]:
        """Update configuration fields and return the change set.

        Only fields present on :class:`RadiationConfig` are applied; unknown
        keys are ignored. Emits a ``CONFIG_CHANGED`` event describing the
        old and new values for each changed field.
        """

        with self._lock:
            changed = self._config.update(**kwargs)
            if changed:
                self._emit(
                    RadiationEventKind.CONFIG_CHANGED,
                    {"changed": changed},
                )
            return changed

    def get_status(self) -> Dict[str, Any]:
        """Return a high-level status snapshot for monitoring."""

        with self._lock:
            alarming = [d.dosimeter_id for d in self._dosimeters.values() if d.is_alarming]
            overloaded = [d.detector_id for d in self._detectors.values() if d.status == DetectorStatus.OVERLOADED]
            lethal_zones = [z.zone_id for z in self._zones.values() if z.level == ContaminationLevel.LETHAL]
            return {
                "initialized": self._initialized,
                "seeded": self._seeded,
                "simulation_time_s": self._simulation_time_s,
                "uptime_s": _now_ts() - self._last_tick_ts + self._simulation_time_s,
                "sources": len(self._sources),
                "shieldings": len(self._shieldings),
                "zones": len(self._zones),
                "dosimeters": len(self._dosimeters),
                "detectors": len(self._detectors),
                "isotopes": len(self._isotopes),
                "alarming_dosimeters": alarming,
                "overloaded_detectors": overloaded,
                "lethal_zones": lethal_zones,
                "peak_dose_rate_sv_per_h": self._stats.peak_dose_rate_sv_per_h,
            }

    def get_stats(self) -> RadiationStats:
        """Return the aggregate statistics object."""

        with self._lock:
            self._refresh_stats_unlocked()
            return self._stats

    def get_snapshot(self) -> RadiationSnapshot:
        """Return a complete point-in-time snapshot of the system state."""

        with self._lock:
            self._refresh_stats_unlocked()
            snapshot = RadiationSnapshot(
                timestamp=_now_ts(),
                simulation_time_s=self._simulation_time_s,
                config=self._config.to_dict(),
                stats=self._stats.to_dict(),
                sources=[s.to_dict() for s in self._sources.values()],
                shieldings=[m.to_dict() for m in self._shieldings.values()],
                zones=[z.to_dict() for z in self._zones.values()],
                dosimeters=[d.to_dict() for d in self._dosimeters.values()],
                detectors=[d.to_dict() for d in self._detectors.values()],
                isotopes=[i.to_dict() for i in self._isotopes.values()],
            )
        return snapshot

    def list_events(
        self,
        kind: Optional[RadiationEventKind] = None,
        since_ts: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[RadiationEvent]:
        """Return events optionally filtered by kind and timestamp.

        Events are returned newest-last to match insertion order. Pass
        ``limit`` to fetch only the most recent ``limit`` events.
        """

        with self._lock:
            events = list(self._events)
        if kind is not None:
            events = [e for e in events if e.kind == kind]
        if since_ts is not None:
            events = [e for e in events if e.timestamp >= since_ts]
        if limit is not None and limit >= 0:
            events = events[-limit:]
        return events

    def get_visualization_data(self) -> Dict[str, Any]:
        """Return data suitable for an in-engine radiation overlay.

        Includes source positions, zone bounds, dosimeter readings, and a
        low-resolution radiation map. The map is intentionally coarse so it
        can be uploaded to a GPU each frame without dominating frame time.
        """

        with self._lock:
            sources = [s.to_dict() for s in self._sources.values()]
            zones = [z.to_dict() for z in self._zones.values()]
            dosimeters = [d.to_dict() for d in self._dosimeters.values()]
            detectors = [d.to_dict() for d in self._detectors.values()]
            shieldings = [m.to_dict() for m in self._shieldings.values()]
        radiation_map = self.get_radiation_map(resolution=12)
        return {
            "sources": sources,
            "zones": zones,
            "dosimeters": dosimeters,
            "detectors": detectors,
            "shieldings": shieldings,
            "radiation_map": radiation_map,
            "background_usv_per_h": self._config.background_radiation_usv_per_h,
            "timestamp": _now_ts(),
        }

    def get_background_radiation(self) -> float:
        """Return the configured ambient background dose rate (uSv/h)."""

        with self._lock:
            return float(self._config.background_radiation_usv_per_h)

    def reset(self) -> None:
        """Clear all registered entities and reset statistics.

        Seed data is not re-populated automatically; call
        :func:`get_radiation_field_system` again or invoke ``_seed_data``
        indirectly by recreating the singleton if seeding is required.
        """

        with self._lock:
            self._isotopes.clear()
            self._sources.clear()
            self._shieldings.clear()
            self._zones.clear()
            self._dosimeters.clear()
            self._detectors.clear()
            self._events.clear()
            self._simulation_time_s = 0.0
            self._last_tick_ts = _now_ts()
            self._stats = RadiationStats()
            self._seeded = False
            self._emit(
                RadiationEventKind.SYSTEM_RESET,
                {"reason": "manual reset"},
            )
            # Re-seed so the system remains immediately useful after reset.
            self._seed_data()


# ============================================================================
# Module-level factory
# ============================================================================

def get_radiation_field_system() -> _RadiationFieldSystem:
    """Return the shared radiation field system singleton.

    This is the canonical entry point for external callers. It guarantees
    the singleton has been initialized and seeded before returning.
    """

    inst = _RadiationFieldSystem.get_instance()
    if not inst._initialized:
        inst._initialize()
    return inst
