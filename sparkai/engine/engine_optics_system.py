"""Engine optics system: light physics simulation for gameplay.

Simulates optical phenomena including reflection, refraction, dispersion,
lenses, mirrors, prisms, optical fibers, and laser propagation for
gameplay mechanics such as optical puzzles, laser combat, and stealth.

The system implements the canonical optics formulas:
  - Speed of light in vacuum: c = 3.0e8 m/s.
  - Snell's law: n1 * sin(theta1) = n2 * sin(theta2).
  - Critical angle: theta_c = arcsin(n2 / n1) when n1 > n2.
  - Total internal reflection occurs when the incident angle exceeds
    the critical angle at a boundary from a denser to a rarer medium.
  - Thin lens equation: 1/f = 1/do + 1/di.
  - Lateral magnification: m = -di / do.
  - Spherical mirror focal length: f = R / 2.
  - Lensmaker's equation (thin lens): 1/f = (n - 1) * (1/R1 - 1/R2).
  - Beer-Lambert absorption: I = I0 * exp(-alpha * d).
  - Numerical aperture: NA = sqrt(n_core^2 - n_clad^2).
  - Acceptance angle: theta_a = arcsin(NA / n_external).
  - Fresnel reflectance (Schlick approximation):
    R(theta) = R0 + (1 - R0) * (1 - cos(theta))^5,
    where R0 = ((n1 - n2) / (n1 + n2))^2.
  - Gaussian beam divergence: theta = lambda / (pi * w0).
  - Cauchy dispersion: n(lambda) = A + B / lambda^2.
  - Wavelength-to-color mapping across the visible spectrum 380-750 nm.

Architecture:
  _OpticsSystem (Singleton)
    |-- LightSource, Mirror, Lens, Prism, OpticalFiber, Detector
    |-- Medium, LightRay, Spectrum
    |-- OpticsConfig, OpticsStats, OpticsSnapshot, OpticsEvent
    |-- LightSourceType, MirrorType, LensType, PrismType
    |-- MediumType, OpticsEventKind, RayStatus

Core Capabilities:
  - register_light_source / get_light_source / list_light_sources /
    update_light_source / remove_light_source
  - register_mirror / get_mirror / list_mirrors /
    update_mirror / remove_mirror
  - register_lens / get_lens / list_lenses / update_lens / remove_lens
  - register_prism / get_prism / list_prisms / update_prism / remove_prism
  - register_optical_fiber / get_optical_fiber / list_optical_fibers /
    update_optical_fiber / remove_optical_fiber
  - register_detector / get_detector / list_detectors /
    update_detector / remove_detector
  - register_medium / get_medium / list_mediums /
    update_medium / remove_medium
  - emit_ray / list_rays / clear_rays
  - trace_ray / trace_ray_path / compute_reflection / compute_refraction
  - compute_dispersion / compute_lens_image / compute_focal_point
  - compute_critical_angle / compute_numerical_aperture
  - compute_acceptance_angle / compute_fresnel_coefficients
  - compute_beam_divergence / wavelength_to_color
  - measure_intensity / measure_wavelength / measure_spectrum / get_light_map
  - ai_predict_light_path / ai_optimize_lens_configuration / ai_assess_visibility
  - get_config / set_config / get_status / get_stats / get_snapshot
  - list_events / tick / get_visualization_data / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`_OpticsSystem.get_instance` or the module-level
:func:`get_optics_system` factory.

Usage:
    osys = get_optics_system()
    ok, msg, source = osys.register_light_source(
        "src_laser_red", source_type=LightSourceType.LASER,
        position=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0),
        wavelength=650.0, intensity=1.0,
    )
    ok, msg, ray = osys.trace_ray(
        origin=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0),
        wavelength=650.0, intensity=1.0,
    )
    ok, msg, result = osys.ai_predict_light_path(
        source_id="src_laser_red", max_bounces=10,
    )
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
# Physical Constants
# ---------------------------------------------------------------------------

# Speed of light in vacuum, in meters per second.
_SPEED_OF_LIGHT: float = 2.99792458e8

# Planck constant in joule-seconds, used for photon energy calculations.
_PLANCK_CONSTANT: float = 6.62607015e-34

# Boltzmann constant in joules per kelvin.
_BOLTZMANN_CONSTANT: float = 1.380649e-23

# Tiny epsilon used to avoid division by zero in vector and distance ops.
_EPSILON: float = 1e-9

# Default refractive index of air at standard temperature and pressure.
_DEFAULT_AIR_INDEX: float = 1.0003

# Wavelength range of the visible spectrum in nanometers.
_VISIBLE_MIN_NM: float = 380.0
_VISIBLE_MAX_NM: float = 750.0

# Default ambient light intensity (normalized 0..1).
_AMBIENT_LIGHT: float = 0.15

# Default time step for the tick method, in seconds (~60 FPS).
_DEFAULT_TIME_STEP: float = 0.016


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Each bounded store uses FIFO eviction once its capacity is exceeded.
# The numbers are generous so that gameplay-heavy scenes can keep a long
# history of rays, events, and measurements without silently dropping
# data that AI analysis might still need.

_MAX_SOURCES: int = 500
_MAX_MIRRORS: int = 500
_MAX_LENSES: int = 400
_MAX_PRISMS: int = 300
_MAX_FIBERS: int = 300
_MAX_DETECTORS: int = 400
_MAX_MEDIUMS: int = 200
_MAX_RAYS: int = 5000
_MAX_EVENTS: int = 10000
_MAX_SPECTRA: int = 2000
_MAX_LIGHT_MAP_CELLS: int = 8192


# ---------------------------------------------------------------------------
# Module-level Lock
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a Z suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, falling back to default on failure."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Coerce a value to int, falling back to default on failure."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Drop the oldest entries from a dict until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Drop the oldest entries from a list until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value into JSON-serializable primitives."""
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

    The dataclass field set is inspected first so that nested dataclasses
    and Enum-typed fields are normalized into JSON-friendly values via
    :func:`_to_jsonable`. Tuples become lists, Enums become their values,
    and nested dataclasses are recursively expanded.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        return instance
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


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


# ---------------------------------------------------------------------------
# Vector Helpers (3D)
# ---------------------------------------------------------------------------


def _vec_add(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_sub(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_scale(
    v: Tuple[float, float, float], s: float
) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec_dot(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_cross(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec_length(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Return the unit-length version of v, or a zero vector if v is null."""
    length = _vec_length(v)
    if length < _EPSILON:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _vec_distance(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    return _vec_length(_vec_sub(a, b))


def _vec_negate(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (-v[0], -v[1], -v[2])


def _vec_lerp(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    t: float,
) -> Tuple[float, float, float]:
    """Linear interpolation between two 3D vectors."""
    t = _clamp(t, 0.0, 1.0)
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _to_vec3(
    value: Any, default: Tuple[float, float, float] = (0.0, 0.0, 0.0)
) -> Tuple[float, float, float]:
    """Coerce a list/tuple/None into a 3-float tuple."""
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        try:
            return (float(value[0]), float(value[1]), float(value[2]))
        except (IndexError, TypeError, ValueError):
            return default
    return default


def _to_vec2(
    value: Any, default: Tuple[float, float] = (0.0, 0.0)
) -> Tuple[float, float]:
    """Coerce a list/tuple/None into a 2-float tuple."""
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        try:
            return (float(value[0]), float(value[1]))
        except (IndexError, TypeError, ValueError):
            return default
    return default


# ---------------------------------------------------------------------------
# Optics Physics Helpers
# ---------------------------------------------------------------------------


def _reflect_direction(
    incident: Tuple[float, float, float],
    normal: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    """Compute the reflected ray direction using the law of reflection.

    The incident vector points toward the surface. The normal points
    away from the surface on the same side as the incoming ray origin.
    Formula: R = D - 2 * (D . N) * N
    """
    dot = _vec_dot(incident, normal)
    return _vec_sub(incident, _vec_scale(normal, 2.0 * dot))


def _refract_direction(
    incident: Tuple[float, float, float],
    normal: Tuple[float, float, float],
    n1: float,
    n2: float,
) -> Tuple[Optional[Tuple[float, float, float]], bool]:
    """Compute the refracted ray direction using Snell's law.

    Returns (refracted_direction, tir) where tir is True when total
    internal reflection occurs. When tir is True the refracted direction
    is None and the caller should fall back to reflection.
    """
    cos_i = -_vec_dot(incident, normal)
    # Ensure the normal points against the incident direction.
    if cos_i < 0.0:
        normal = _vec_negate(normal)
        cos_i = -cos_i
    eta = n1 / n2
    sin_t2 = eta * eta * (1.0 - cos_i * cos_i)
    if sin_t2 > 1.0:
        # Total internal reflection: no transmitted ray.
        return (None, True)
    cos_t = math.sqrt(1.0 - sin_t2)
    refracted = _vec_add(
        _vec_scale(incident, eta),
        _vec_scale(normal, eta * cos_i - cos_t),
    )
    return (_vec_normalize(refracted), False)


def _critical_angle(n1: float, n2: float) -> Optional[float]:
    """Compute the critical angle for total internal reflection.

    Only defined when n1 > n2 (denser to rarer medium). Returns None
    when TIR is not possible.
    """
    if n1 <= n2 or n1 < _EPSILON:
        return None
    ratio = n2 / n1
    if ratio > 1.0:
        return None
    return math.asin(ratio)


def _fresnel_reflectance(
    cos_theta: float, n1: float, n2: float
) -> float:
    """Compute Fresnel reflectance using the Schlick approximation.

    Returns a value in [0, 1] representing the fraction of light
    reflected at the interface. The remainder is transmitted.
    """
    r0 = ((n1 - n2) / (n1 + n2)) ** 2
    cos_x = _clamp(cos_theta, 0.0, 1.0)
    # When going from denser to rarer medium, use the transmitted angle.
    n_ratio = n1 / n2
    sin_t2 = n_ratio * n_ratio * (1.0 - cos_x * cos_x)
    if sin_t2 > 1.0:
        # Total internal reflection: everything reflects.
        return 1.0
    cos_x = math.sqrt(1.0 - sin_t2)
    return r0 + (1.0 - r0) * (1.0 - cos_x) ** 5


def _beer_lambert(
    intensity_0: float, absorption_coeff: float, distance: float
) -> float:
    """Beer-Lambert law: I = I0 * exp(-alpha * d).

    Computes the remaining intensity after light travels a given
    distance through an absorbing medium with coefficient alpha.
    """
    i0 = _safe_float(intensity_0, 0.0)
    alpha = max(0.0, _safe_float(absorption_coeff, 0.0))
    d = max(0.0, _safe_float(distance, 0.0))
    return i0 * math.exp(-alpha * d)


def _thin_lens_equation(
    do: float, f: float
) -> Tuple[float, float]:
    """Thin lens equation: 1/f = 1/do + 1/di.

    Returns (di, magnification) where di is the image distance and
    magnification is the lateral magnification m = -di / do. When do
    equals f the image is at infinity.
    """
    do_val = _safe_float(do, 0.0)
    f_val = _safe_float(f, 0.0)
    if abs(do_val) < _EPSILON or abs(f_val) < _EPSILON:
        return (0.0, 0.0)
    if abs(do_val - f_val) < _EPSILON:
        return (float("inf"), float("inf"))
    di = 1.0 / (1.0 / f_val - 1.0 / do_val)
    m = -di / do_val
    return (di, m)


def _mirror_focal_length(curvature_radius: float) -> float:
    """Spherical mirror focal length: f = R / 2.

    Positive R gives a concave mirror (converging). Negative R gives
    a convex mirror (diverging). The focal length is half the radius.
    """
    return _safe_float(curvature_radius, 0.0) / 2.0


def _lensmaker_focal_length(
    n_lens: float,
    r1: float,
    r2: float,
    n_medium: float = 1.0,
) -> float:
    """Lensmaker's equation for a thin lens:

    1/f = (n - n_medium) * (1/R1 - 1/R2)

    R1 is the radius of the first surface (light-side). R2 is the
    radius of the second surface. Sign convention: radii are positive
    if the center of curvature is on the outgoing side.
    """
    n_rel = _safe_float(n_lens, 1.0) - _safe_float(n_medium, 1.0)
    r1_val = _safe_float(r1, 0.0)
    r2_val = _safe_float(r2, 0.0)
    inv_r1 = 1.0 / r1_val if abs(r1_val) > _EPSILON else 0.0
    inv_r2 = 1.0 / r2_val if abs(r2_val) > _EPSILON else 0.0
    power = n_rel * (inv_r1 - inv_r2)
    if abs(power) < _EPSILON:
        return 0.0
    return 1.0 / power


def _numerical_aperture(n_core: float, n_clad: float) -> float:
    """Numerical aperture of an optical fiber: NA = sqrt(n_core^2 - n_clad^2)."""
    val = _safe_float(n_core, 1.0) ** 2 - _safe_float(n_clad, 1.0) ** 2
    return math.sqrt(max(0.0, val))


def _acceptance_angle(
    n_core: float, n_clad: float, n_external: float = 1.0
) -> float:
    """Acceptance angle of an optical fiber in radians.

    theta_a = arcsin(NA / n_external). Caps at pi/2 when NA >= n_external.
    """
    na = _numerical_aperture(n_core, n_clad)
    n_ext = max(_EPSILON, _safe_float(n_external, 1.0))
    if na >= n_ext:
        return math.pi / 2.0
    return math.asin(na / n_ext)


def _gaussian_beam_divergence(
    wavelength_nm: float, waist_um: float
) -> float:
    """Gaussian beam divergence angle in radians.

    theta = lambda / (pi * w0), where lambda is the wavelength and
    w0 is the beam waist. Wavelength is in nanometers, waist in
    micrometers; both are converted to meters internally.
    """
    lam = _safe_float(wavelength_nm, 550.0) * 1e-9
    w0 = max(_EPSILON, _safe_float(waist_um, 1.0)) * 1e-6
    return lam / (math.pi * w0)


def _cauchy_index(
    wavelength_nm: float, A: float, B: float
) -> float:
    """Cauchy's dispersion equation: n = A + B / lambda^2.

    Wavelength is in nanometers. A and B are material-specific
    coefficients. This is a simple model valid for visible light.
    """
    lam = max(_EPSILON, _safe_float(wavelength_nm, 550.0))
    return _safe_float(A, 1.5) + _safe_float(B, 4500.0) / (lam * lam)


def _photon_energy(wavelength_nm: float) -> float:
    """Photon energy in electron-volts for a given wavelength in nm.

    E = h * c / lambda. Returns the energy in eV for convenience.
    """
    lam_m = max(_EPSILON, _safe_float(wavelength_nm, 550.0) * 1e-9)
    joules = (_PLANCK_CONSTANT * _SPEED_OF_LIGHT) / lam_m
    return joules / 1.602176634e-19


def _wavelength_to_rgb(
    wavelength_nm: float,
) -> Tuple[float, float, float]:
    """Convert a wavelength in nanometers to an approximate RGB tuple.

    Uses a piecewise linear approximation of the visible spectrum from
    380 nm (violet) to 750 nm (red). Values outside the visible range
    return black. Each channel is in [0, 1].
    """
    w = _safe_float(wavelength_nm, 550.0)
    if w < _VISIBLE_MIN_NM or w > _VISIBLE_MAX_NM:
        return (0.0, 0.0, 0.0)
    if w < 440.0:
        r = -(w - 440.0) / (440.0 - 380.0)
        g = 0.0
        b = 1.0
    elif w < 490.0:
        r = 0.0
        g = (w - 440.0) / (490.0 - 440.0)
        b = 1.0
    elif w < 510.0:
        r = 0.0
        g = 1.0
        b = -(w - 510.0) / (510.0 - 490.0)
    elif w < 580.0:
        r = (w - 510.0) / (580.0 - 510.0)
        g = 1.0
        b = 0.0
    elif w < 645.0:
        r = 1.0
        g = -(w - 645.0) / (645.0 - 580.0)
        b = 0.0
    else:
        r = 1.0
        g = 0.0
        b = 0.0
    # Intensity falloff near the edges of the visible spectrum.
    if w < 420.0:
        factor = 0.3 + 0.7 * (w - _VISIBLE_MIN_NM) / (420.0 - _VISIBLE_MIN_NM)
    elif w > 700.0:
        factor = 0.3 + 0.7 * (_VISIBLE_MAX_NM - w) / (
            _VISIBLE_MAX_NM - 700.0
        )
    else:
        factor = 1.0
    return (_clamp(r * factor), _clamp(g * factor), _clamp(b * factor))


def _wavelength_label(wavelength_nm: float) -> str:
    """Return a human-readable color band name for a wavelength."""
    w = _safe_float(wavelength_nm, 550.0)
    if w < 380.0:
        return "ultraviolet"
    if w < 450.0:
        return "violet"
    if w < 485.0:
        return "blue"
    if w < 500.0:
        return "cyan"
    if w < 565.0:
        return "green"
    if w < 590.0:
        return "yellow"
    if w < 625.0:
        return "orange"
    if w <= 750.0:
        return "red"
    return "infrared"


def _ray_plane_intersection(
    origin: Tuple[float, float, float],
    direction: Tuple[float, float, float],
    plane_point: Tuple[float, float, float],
    plane_normal: Tuple[float, float, float],
) -> Optional[float]:
    """Compute the intersection parameter t of a ray with a plane.

    Returns t such that the hit point is origin + t * direction, or
    None when the ray is parallel to the plane. A negative t means the
    intersection is behind the ray origin.
    """
    denom = _vec_dot(direction, plane_normal)
    if abs(denom) < _EPSILON:
        return None
    diff = _vec_sub(plane_point, origin)
    t = _vec_dot(diff, plane_normal) / denom
    return t


def _point_segment_distance(
    p: Tuple[float, float, float],
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
) -> float:
    """Shortest distance from point p to the line segment a-b."""
    ab = _vec_sub(b, a)
    ab_len2 = _vec_dot(ab, ab)
    if ab_len2 < _EPSILON:
        return _vec_distance(p, a)
    t = _clamp(_vec_dot(_vec_sub(p, a), ab) / ab_len2, 0.0, 1.0)
    proj = _vec_add(a, _vec_scale(ab, t))
    return _vec_distance(p, proj)


def _angle_between(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    """Angle in radians between two vectors."""
    na = _vec_normalize(a)
    nb = _vec_normalize(b)
    dot = _clamp(_vec_dot(na, nb), -1.0, 1.0)
    return math.acos(dot)


def _intensity_label(intensity: float) -> str:
    """Map a normalized intensity value to a qualitative label."""
    i = _clamp(_safe_float(intensity, 0.0), 0.0, 1.0)
    if i >= 0.8:
        return "brilliant"
    if i >= 0.5:
        return "bright"
    if i >= 0.25:
        return "moderate"
    if i >= 0.05:
        return "dim"
    return "faint"


def _visibility_label(score: float) -> str:
    """Map a visibility score in [0, 1] to a qualitative label."""
    s = _clamp(_safe_float(score, 0.0), 0.0, 1.0)
    if s >= 0.85:
        return "fully_exposed"
    if s >= 0.6:
        return "clearly_visible"
    if s >= 0.35:
        return "partially_visible"
    if s >= 0.1:
        return "barely_visible"
    return "hidden"


def _confidence_label(probability: float) -> str:
    """Map a probability in [0, 1] to a confidence label."""
    p = _clamp(_safe_float(probability, 0.0), 0.0, 1.0)
    if p >= 0.85:
        return "certain"
    if p >= 0.6:
        return "likely"
    if p >= 0.35:
        return "possible"
    if p >= 0.1:
        return "unlikely"
    return "negligible"


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class LightSourceType(Enum):
    """Classification of a light source by its emission mechanism."""
    LASER = "laser"
    LED = "led"
    INCANDESCENT = "incandescent"
    FLUORESCENT = "fluorescent"
    SUNLIGHT = "sunlight"
    POINT = "point"
    SPOT = "spot"
    AMBIENT = "ambient"
    ARC = "arc"


class MirrorType(Enum):
    """Classification of a mirror by its surface curvature."""
    PLANE = "plane"
    CONCAVE = "concave"
    CONVEX = "convex"


class LensType(Enum):
    """Classification of a lens by its surface geometry."""
    BICONVEX = "biconvex"
    BICONCAVE = "biconcave"
    PLANO_CONVEX = "plano_convex"
    PLANO_CONCAVE = "plano_concave"
    CONVERGING = "converging"
    DIVERGING = "diverging"


class PrismType(Enum):
    """Classification of a prism by its cross-section shape."""
    TRIANGULAR = "triangular"
    RIGHT_ANGLE = "right_angle"
    EQUILATERAL = "equilateral"
    PORRO = "porro"
    PENTA = "penta"
    DISPERSIVE = "dispersive"


class MediumType(Enum):
    """Classification of an optical medium by its composition."""
    VACUUM = "vacuum"
    AIR = "air"
    WATER = "water"
    GLASS = "glass"
    CROWN_GLASS = "crown_glass"
    FLINT_GLASS = "flint_glass"
    DIAMOND = "diamond"
    ACRYLIC = "acrylic"
    FUSED_SILICA = "fused_silica"
    SAPPHIRE = "sapphire"
    CUSTOM = "custom"


class PolarizationType(Enum):
    """Classification of light polarization state."""
    UNPOLARIZED = "unpolarized"
    LINEAR = "linear"
    CIRCULAR = "circular"
    ELLIPTICAL = "elliptical"


class RayStatus(Enum):
    """Lifecycle status of a traced light ray."""
    ACTIVE = "active"
    REFLECTED = "reflected"
    REFRACTED = "refracted"
    ABSORBED = "absorbed"
    BLOCKED = "blocked"
    TERMINATED = "terminated"
    ESCAPED = "escaped"


class OpticsEventKind(Enum):
    """Audit event types emitted by the optics system."""
    SOURCE_REGISTERED = "source_registered"
    SOURCE_REMOVED = "source_removed"
    SOURCE_UPDATED = "source_updated"
    MIRROR_REGISTERED = "mirror_registered"
    MIRROR_REMOVED = "mirror_removed"
    MIRROR_UPDATED = "mirror_updated"
    LENS_REGISTERED = "lens_registered"
    LENS_REMOVED = "lens_removed"
    LENS_UPDATED = "lens_updated"
    PRISM_REGISTERED = "prism_registered"
    PRISM_REMOVED = "prism_removed"
    PRISM_UPDATED = "prism_updated"
    FIBER_REGISTERED = "fiber_registered"
    FIBER_REMOVED = "fiber_removed"
    FIBER_UPDATED = "fiber_updated"
    DETECTOR_REGISTERED = "detector_registered"
    DETECTOR_REMOVED = "detector_removed"
    DETECTOR_UPDATED = "detector_updated"
    MEDIUM_REGISTERED = "medium_registered"
    MEDIUM_REMOVED = "medium_removed"
    MEDIUM_UPDATED = "medium_updated"
    RAY_EMITTED = "ray_emitted"
    RAY_TRACED = "ray_traced"
    RAY_REFLECTED = "ray_reflected"
    RAY_REFRACTED = "ray_refracted"
    RAY_ABSORBED = "ray_absorbed"
    RAY_TERMINATED = "ray_terminated"
    RAYS_CLEARED = "rays_cleared"
    INTENSITY_MEASURED = "intensity_measured"
    WAVELENGTH_MEASURED = "wavelength_measured"
    SPECTRUM_MEASURED = "spectrum_measured"
    LIGHT_MAP_GENERATED = "light_map_generated"
    DISPERSION_COMPUTED = "dispersion_computed"
    LENS_IMAGE_COMPUTED = "lens_image_computed"
    FOCAL_POINT_COMPUTED = "focal_point_computed"
    CRITICAL_ANGLE_COMPUTED = "critical_angle_computed"
    FRESNEL_COMPUTED = "fresnel_computed"
    AI_ASSESSMENT = "ai_assessment"
    CONFIG_UPDATED = "config_updated"
    TICK = "tick"
    SYSTEM_RESET = "system_reset"


# ---------------------------------------------------------------------------
# Entity Data Classes
# ---------------------------------------------------------------------------


@dataclass
class LightSource:
    """A light-emitting entity in 3D space.

    Each source has a position, emission direction, dominant wavelength
    in nanometers, intensity (normalized 0..1), optical power in watts,
    beam divergence in radians, and a polarization state. Coherent
    sources (lasers) produce collimated beams; incoherent sources
    (incandescent, LED) produce spread emission.
    """
    source_id: str = ""
    name: str = ""
    source_type: str = LightSourceType.POINT.value
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    wavelength_nm: float = 550.0
    intensity: float = 1.0
    power_w: float = 1.0
    divergence_rad: float = 0.0
    polarization: str = PolarizationType.UNPOLARIZED.value
    coherent: bool = False
    color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Mirror:
    """A reflective surface in 3D space.

    Plane mirrors reflect light at the same angle of incidence. Concave
    mirrors converge light to a focal point at f = R/2. Convex mirrors
    diverge light, producing virtual focal points. The reflectivity
    coefficient is in [0, 1]; 1.0 is a perfect mirror.
    """
    mirror_id: str = ""
    name: str = ""
    mirror_type: str = MirrorType.PLANE.value
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    curvature_radius: float = 0.0
    focal_length: float = 0.0
    reflectivity: float = 1.0
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    size: Tuple[float, float] = (1.0, 1.0)
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Lens:
    """A refractive optical element that focuses or defocuses light.

    The lens is described by its type, position, surface normal, focal
    length, two radii of curvature, thickness, refractive index, and
    clear aperture diameter. Converging lenses (biconvex, plano-convex)
    have positive focal lengths; diverging lenses (biconcave,
    plano-concave) have negative focal lengths.
    """
    lens_id: str = ""
    name: str = ""
    lens_type: str = LensType.BICONVEX.value
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    focal_length: float = 0.1
    radius_left: float = 0.5
    radius_right: float = -0.5
    thickness: float = 0.01
    refractive_index: float = 1.52
    diameter: float = 0.05
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Prism:
    """A dispersive optical element that splits light by wavelength.

    The prism has an apex angle in radians, a refractive index (or
    Cauchy coefficients for wavelength-dependent dispersion), a base
    length, height, and rotation. Light entering the prism is refracted
    at each surface, and different wavelengths bend at different angles
    due to dispersion.
    """
    prism_id: str = ""
    name: str = ""
    prism_type: str = PrismType.TRIANGULAR.value
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    apex_angle_rad: float = math.radians(60.0)
    refractive_index: float = 1.52
    cauchy_a: float = 1.50
    cauchy_b: float = 4500.0
    base_length: float = 0.05
    height: float = 0.05
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OpticalFiber:
    """A waveguide that transmits light via total internal reflection.

    The fiber has a core refractive index, cladding refractive index,
    core radius, acceptance angle, and numerical aperture. Light enters
    within the acceptance cone and propagates along the fiber with
    attenuation described by the Beer-Lambert law.
    """
    fiber_id: str = ""
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    length: float = 1.0
    core_index: float = 1.50
    cladding_index: float = 1.48
    core_radius: float = 0.00005
    acceptance_angle: float = 0.0
    numerical_aperture: float = 0.0
    attenuation_per_m: float = 0.0
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Detector:
    """A light-sensitive sensor that measures incident light.

    The detector has a position, facing direction, sensitivity in
    amperes per watt, a wavelength sensitivity range, and a detection
    threshold. When light hits the detector above the threshold, it
    records the reading and the timestamp.
    """
    detector_id: str = ""
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    sensitivity: float = 0.5
    wavelength_min_nm: float = _VISIBLE_MIN_NM
    wavelength_max_nm: float = _VISIBLE_MAX_NM
    threshold: float = 0.01
    active: bool = True
    last_reading: float = 0.0
    last_reading_time: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Medium:
    """An optical medium with a refractive index and absorption.

    The medium has a refractive index n (dimensionless), an absorption
    coefficient alpha in 1/m, a scattering coefficient in 1/m, and
    physical properties (temperature, density). Light traveling through
    the medium is attenuated by the Beer-Lambert law.
    """
    medium_id: str = ""
    name: str = ""
    medium_type: str = MediumType.AIR.value
    refractive_index: float = _DEFAULT_AIR_INDEX
    absorption_coeff: float = 0.0
    scattering_coeff: float = 0.0
    temperature_k: float = 293.15
    density_kg_m3: float = 1.225
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LightRay:
    """A traced light ray with a full propagation path.

    The ray starts at an origin, travels along a direction, and has a
    wavelength, intensity, polarization, and the ID of the medium it
    currently inhabits. The path is a list of points the ray has
    visited, including reflection and refraction vertices. The bounce
    count limits recursion depth in the tracer.
    """
    ray_id: str = ""
    source_id: str = ""
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    wavelength_nm: float = 550.0
    intensity: float = 1.0
    initial_intensity: float = 1.0
    polarization: str = PolarizationType.UNPOLARIZED.value
    medium_id: str = "air"
    status: str = RayStatus.ACTIVE.value
    path: List[Tuple[float, float, float]] = field(default_factory=list)
    age_s: float = 0.0
    parent_ray_id: str = ""
    bounce_count: int = 0
    total_distance: float = 0.0
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Spectrum:
    """A spectral distribution of light intensity vs wavelength.

    The spectrum holds parallel lists of wavelengths (in nm) and
    intensities (normalized 0..1). It is used by detectors and the
    measure_spectrum method to describe the color content of light
    arriving at a point.
    """
    spectrum_id: str = ""
    source_id: str = ""
    wavelengths: List[float] = field(default_factory=list)
    intensities: List[float] = field(default_factory=list)
    peak_wavelength_nm: float = 550.0
    bandwidth_nm: float = 0.0
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Config / Stats / Snapshot / Event
# ---------------------------------------------------------------------------


@dataclass
class OpticsConfig:
    """Tunable runtime configuration for the optics system."""
    max_sources: int = _MAX_SOURCES
    max_mirrors: int = _MAX_MIRRORS
    max_lenses: int = _MAX_LENSES
    max_prisms: int = _MAX_PRISMS
    max_fibers: int = _MAX_FIBERS
    max_detectors: int = _MAX_DETECTORS
    max_mediums: int = _MAX_MEDIUMS
    max_rays: int = _MAX_RAYS
    max_events: int = _MAX_EVENTS
    max_spectra: int = _MAX_SPECTRA
    time_step: float = _DEFAULT_TIME_STEP
    ambient_light: float = _AMBIENT_LIGHT
    air_refractive_index: float = _DEFAULT_AIR_INDEX
    max_bounces: int = 16
    ray_segment_length: float = 100.0
    light_map_resolution: int = 32
    enable_polarization: bool = True
    enable_interference: bool = False
    enable_absorption: bool = True
    enable_scattering: bool = False
    enable_dispersion: bool = True
    enable_fresnel: bool = True
    enable_beam_divergence: bool = True
    verbose: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OpticsStats:
    """Roll-up statistics maintained across the system lifetime."""
    total_sources: int = 0
    active_sources: int = 0
    total_mirrors: int = 0
    active_mirrors: int = 0
    total_lenses: int = 0
    active_lenses: int = 0
    total_prisms: int = 0
    active_prisms: int = 0
    total_fibers: int = 0
    active_fibers: int = 0
    total_detectors: int = 0
    active_detectors: int = 0
    total_mediums: int = 0
    total_rays_traced: int = 0
    total_rays_active: int = 0
    total_reflections: int = 0
    total_refractions: int = 0
    total_absorptions: int = 0
    total_measurements: int = 0
    total_spectra: int = 0
    total_light_maps: int = 0
    total_ai_assessments: int = 0
    total_dispersion_computations: int = 0
    total_lens_images: int = 0
    total_focal_points: int = 0
    tick_count: int = 0
    simulation_time_s: float = 0.0
    peak_intensity: float = 0.0
    avg_ray_bounces: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OpticsSnapshot:
    """A point-in-time snapshot of the full system state."""
    timestamp: str = field(default_factory=_now)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    mirrors: List[Dict[str, Any]] = field(default_factory=list)
    lenses: List[Dict[str, Any]] = field(default_factory=list)
    prisms: List[Dict[str, Any]] = field(default_factory=list)
    fibers: List[Dict[str, Any]] = field(default_factory=list)
    detectors: List[Dict[str, Any]] = field(default_factory=list)
    mediums: List[Dict[str, Any]] = field(default_factory=list)
    rays: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OpticsEvent:
    """An internal audit event emitted by the optics system."""
    event_id: str = ""
    timestamp: str = field(default_factory=_now)
    event_type: str = OpticsEventKind.SOURCE_REGISTERED.value
    description: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Optics System (Singleton)
# ---------------------------------------------------------------------------


class _OpticsSystem:
    """A light physics simulator for gameplay mechanics.

    The system is thread-safe and implemented as a singleton with
    double-checked locking. ``_init_lock`` guards singleton creation
    and seeding; ``_lock`` guards all mutating operations so the
    internal dictionaries stay consistent across concurrent callers.

    The simulation model covers reflection, refraction, dispersion,
    absorption, lens imaging, mirror optics, optical fiber propagation,
    and laser beam dynamics. Each formula is implemented directly from
    the standard physics textbook equations, and all computations are
    deterministic so AI agents can reason about outcomes.
    """

    _instance: Optional["_OpticsSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._seeded: bool = False
        self._sources: Dict[str, LightSource] = {}
        self._mirrors: Dict[str, Mirror] = {}
        self._lenses: Dict[str, Lens] = {}
        self._prisms: Dict[str, Prism] = {}
        self._fibers: Dict[str, OpticalFiber] = {}
        self._detectors: Dict[str, Detector] = {}
        self._mediums: Dict[str, Medium] = {}
        self._rays: Dict[str, LightRay] = {}
        self._spectra: Dict[str, Spectrum] = {}
        self._events: List[OpticsEvent] = []
        self._config = OpticsConfig()
        self._stats = OpticsStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._ray_counter: int = 0
        self._spectrum_counter: int = 0
        self._simulation_time: float = 0.0
        self._bounce_accum: float = 0.0
        self._bounce_count: int = 0

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "_OpticsSystem":
        """Return the shared singleton, creating it if needed.

        Uses double-checked locking so the lock is only acquired on
        the very first call. After that the instance is already set
        and the fast path skips the lock entirely.
        """
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Explicitly seed the system if it has not been seeded yet."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed_data()
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        description: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event to the rolling event log."""
        self._event_counter += 1
        event = OpticsEvent(
            event_id=f"opevt_{self._event_counter:08d}",
            timestamp=_now(),
            event_type=event_type,
            description=description,
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)

    def _refresh_stats(self) -> None:
        """Recompute the cached OpticsStats roll-up from current state."""
        self._stats.total_sources = len(self._sources)
        self._stats.active_sources = sum(
            1 for s in self._sources.values() if s.active
        )
        self._stats.total_mirrors = len(self._mirrors)
        self._stats.active_mirrors = sum(
            1 for m in self._mirrors.values() if m.active
        )
        self._stats.total_lenses = len(self._lenses)
        self._stats.active_lenses = sum(
            1 for l in self._lenses.values() if l.active
        )
        self._stats.total_prisms = len(self._prisms)
        self._stats.active_prisms = sum(
            1 for p in self._prisms.values() if p.active
        )
        self._stats.total_fibers = len(self._fibers)
        self._stats.active_fibers = sum(
            1 for f in self._fibers.values() if f.active
        )
        self._stats.total_detectors = len(self._detectors)
        self._stats.active_detectors = sum(
            1 for d in self._detectors.values() if d.active
        )
        self._stats.total_mediums = len(self._mediums)
        self._stats.total_rays_active = sum(
            1 for r in self._rays.values()
            if r.status == RayStatus.ACTIVE.value
        )
        self._stats.total_spectra = len(self._spectra)
        self._stats.tick_count = self._tick_count
        self._stats.simulation_time_s = self._simulation_time
        peak = 0.0
        for src in self._sources.values():
            if src.active and src.intensity > peak:
                peak = src.intensity
        for ray in self._rays.values():
            if ray.intensity > peak:
                peak = ray.intensity
        self._stats.peak_intensity = peak
        if self._bounce_count > 0:
            self._stats.avg_ray_bounces = (
                self._bounce_accum / self._bounce_count
            )

    def _medium_index(self, medium_id: str) -> float:
        """Look up the refractive index for a medium ID, defaulting to air."""
        medium = self._mediums.get(str(medium_id).strip())
        if medium is not None:
            return medium.refractive_index
        return self._config.air_refractive_index

    def _default_medium_for_type(
        self, medium_type: str
    ) -> Tuple[float, float]:
        """Return (refractive_index, absorption_coeff) for a medium type."""
        table = {
            MediumType.VACUUM.value: (1.0, 0.0),
            MediumType.AIR.value: (_DEFAULT_AIR_INDEX, 0.0),
            MediumType.WATER.value: (1.333, 0.02),
            MediumType.GLASS.value: (1.52, 0.01),
            MediumType.CROWN_GLASS.value: (1.52, 0.005),
            MediumType.FLINT_GLASS.value: (1.62, 0.008),
            MediumType.DIAMOND.value: (2.417, 0.002),
            MediumType.ACRYLIC.value: (1.49, 0.05),
            MediumType.FUSED_SILICA.value: (1.46, 0.001),
            MediumType.SAPPHIRE.value: (1.77, 0.001),
        }
        return table.get(str(medium_type).lower(), (_DEFAULT_AIR_INDEX, 0.0))

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the system with a canonical set of optics data.

        Called once during :meth:`initialize`. The seed includes six
        light sources, four mirrors, four lenses, three prisms, three
        optical fibers, four detectors, and six mediums so that the
        system is immediately usable for gameplay and demos.
        """
        with self._lock:
            if self._seeded:
                return

            # ----------------------------------------------------------
            # Mediums (6)
            # ----------------------------------------------------------
            medium_seeds: List[Medium] = [
                Medium(
                    medium_id="med_vacuum",
                    name="Vacuum",
                    medium_type=MediumType.VACUUM.value,
                    refractive_index=1.0,
                    absorption_coeff=0.0,
                    scattering_coeff=0.0,
                    temperature_k=2.7,
                    density_kg_m3=0.0,
                    active=True,
                    metadata={"scene": "demo"},
                ),
                Medium(
                    medium_id="med_air",
                    name="Air at STP",
                    medium_type=MediumType.AIR.value,
                    refractive_index=_DEFAULT_AIR_INDEX,
                    absorption_coeff=0.0,
                    scattering_coeff=0.0001,
                    temperature_k=293.15,
                    density_kg_m3=1.225,
                    active=True,
                    metadata={"scene": "demo"},
                ),
                Medium(
                    medium_id="med_water",
                    name="Water at 20C",
                    medium_type=MediumType.WATER.value,
                    refractive_index=1.333,
                    absorption_coeff=0.02,
                    scattering_coeff=0.005,
                    temperature_k=293.15,
                    density_kg_m3=998.0,
                    active=True,
                    metadata={"scene": "demo"},
                ),
                Medium(
                    medium_id="med_crown_glass",
                    name="Crown Glass BK7",
                    medium_type=MediumType.CROWN_GLASS.value,
                    refractive_index=1.517,
                    absorption_coeff=0.005,
                    scattering_coeff=0.0,
                    temperature_k=293.15,
                    density_kg_m3=2510.0,
                    active=True,
                    metadata={"scene": "demo", "cauchy_a": 1.5046,
                              "cauchy_b": 4200.0},
                ),
                Medium(
                    medium_id="med_flint_glass",
                    name="Flint Glass SF2",
                    medium_type=MediumType.FLINT_GLASS.value,
                    refractive_index=1.648,
                    absorption_coeff=0.008,
                    scattering_coeff=0.0,
                    temperature_k=293.15,
                    density_kg_m3=3860.0,
                    active=True,
                    metadata={"scene": "demo", "cauchy_a": 1.6156,
                              "cauchy_b": 12900.0},
                ),
                Medium(
                    medium_id="med_diamond",
                    name="Diamond",
                    medium_type=MediumType.DIAMOND.value,
                    refractive_index=2.417,
                    absorption_coeff=0.002,
                    scattering_coeff=0.0,
                    temperature_k=293.15,
                    density_kg_m3=3520.0,
                    active=True,
                    metadata={"scene": "demo"},
                ),
            ]
            for med in medium_seeds:
                self._mediums[med.medium_id] = med

            # ----------------------------------------------------------
            # Light Sources (6)
            # ----------------------------------------------------------
            source_seeds: List[LightSource] = [
                LightSource(
                    source_id="src_laser_red",
                    name="Red Laser Pointer",
                    source_type=LightSourceType.LASER.value,
                    position=(0.0, 1.0, 0.0),
                    direction=(1.0, 0.0, 0.0),
                    wavelength_nm=650.0,
                    intensity=0.95,
                    power_w=0.005,
                    divergence_rad=0.001,
                    polarization=PolarizationType.LINEAR.value,
                    coherent=True,
                    color=_wavelength_to_rgb(650.0),
                    active=True,
                    metadata={"scene": "demo", "owner": "player"},
                ),
                LightSource(
                    source_id="src_laser_green",
                    name="Green Laser Module",
                    source_type=LightSourceType.LASER.value,
                    position=(0.0, 2.0, 0.0),
                    direction=(1.0, 0.0, 0.0),
                    wavelength_nm=532.0,
                    intensity=0.9,
                    power_w=0.05,
                    divergence_rad=0.0008,
                    polarization=PolarizationType.LINEAR.value,
                    coherent=True,
                    color=_wavelength_to_rgb(532.0),
                    active=True,
                    metadata={"scene": "demo", "owner": "player"},
                ),
                LightSource(
                    source_id="src_led_white",
                    name="White LED Panel",
                    source_type=LightSourceType.LED.value,
                    position=(5.0, 3.0, -2.0),
                    direction=(0.0, -1.0, 0.0),
                    wavelength_nm=550.0,
                    intensity=0.7,
                    power_w=10.0,
                    divergence_rad=0.5,
                    polarization=PolarizationType.UNPOLARIZED.value,
                    coherent=False,
                    color=_wavelength_to_rgb(550.0),
                    active=True,
                    metadata={"scene": "demo", "broadband": True},
                ),
                LightSource(
                    source_id="src_sun",
                    name="Sunlight",
                    source_type=LightSourceType.SUNLIGHT.value,
                    position=(50.0, 50.0, 0.0),
                    direction=(-1.0, -1.0, 0.0),
                    wavelength_nm=500.0,
                    intensity=1.0,
                    power_w=1361.0,
                    divergence_rad=0.0046,
                    polarization=PolarizationType.UNPOLARIZED.value,
                    coherent=False,
                    color=_wavelength_to_rgb(500.0),
                    active=True,
                    metadata={"scene": "demo", "solar_constant_w_m2": 1361.0},
                ),
                LightSource(
                    source_id="src_flashlight",
                    name="Tactical Flashlight",
                    source_type=LightSourceType.SPOT.value,
                    position=(10.0, 1.5, 5.0),
                    direction=(1.0, 0.0, -0.5),
                    wavelength_nm=600.0,
                    intensity=0.6,
                    power_w=3.0,
                    divergence_rad=0.2,
                    polarization=PolarizationType.UNPOLARIZED.value,
                    coherent=False,
                    color=_wavelength_to_rgb(600.0),
                    active=True,
                    metadata={"scene": "demo", "cone_angle_deg": 15.0},
                ),
                LightSource(
                    source_id="src_incandescent",
                    name="Incandescent Bulb",
                    source_type=LightSourceType.INCANDESCENT.value,
                    position=(3.0, 4.0, 3.0),
                    direction=(0.0, -1.0, 0.0),
                    wavelength_nm=580.0,
                    intensity=0.5,
                    power_w=60.0,
                    divergence_rad=math.pi,
                    polarization=PolarizationType.UNPOLARIZED.value,
                    coherent=False,
                    color=_wavelength_to_rgb(580.0),
                    active=True,
                    metadata={"scene": "demo", "color_temp_k": 2800.0},
                ),
            ]
            for src in source_seeds:
                self._sources[src.source_id] = src

            # ----------------------------------------------------------
            # Mirrors (4)
            # ----------------------------------------------------------
            mirror_seeds: List[Mirror] = [
                Mirror(
                    mirror_id="mir_plane_01",
                    name="Front Surface Mirror",
                    mirror_type=MirrorType.PLANE.value,
                    position=(10.0, 1.0, 0.0),
                    normal=(-1.0, 0.0, 0.0),
                    curvature_radius=0.0,
                    focal_length=0.0,
                    reflectivity=0.98,
                    rotation=(0.0, 0.0, 0.0),
                    size=(0.5, 0.5),
                    active=True,
                    metadata={"scene": "demo"},
                ),
                Mirror(
                    mirror_id="mir_concave_01",
                    name="Concave Telescope Mirror",
                    mirror_type=MirrorType.CONCAVE.value,
                    position=(15.0, 2.0, 0.0),
                    normal=(-1.0, 0.0, 0.0),
                    curvature_radius=2.0,
                    focal_length=1.0,
                    reflectivity=0.95,
                    rotation=(0.0, 0.0, 0.0),
                    size=(0.3, 0.3),
                    active=True,
                    metadata={"scene": "demo"},
                ),
                Mirror(
                    mirror_id="mir_convex_01",
                    name="Convex Security Mirror",
                    mirror_type=MirrorType.CONVEX.value,
                    position=(5.0, 3.0, -5.0),
                    normal=(0.0, -1.0, 0.0),
                    curvature_radius=-1.5,
                    focal_length=-0.75,
                    reflectivity=0.92,
                    rotation=(0.0, 0.0, 0.0),
                    size=(0.4, 0.4),
                    active=True,
                    metadata={"scene": "demo"},
                ),
                Mirror(
                    mirror_id="mir_plane_angled",
                    name="Angled Deflector Mirror",
                    mirror_type=MirrorType.PLANE.value,
                    position=(7.0, 1.0, 3.0),
                    normal=(-0.707, 0.0, -0.707),
                    curvature_radius=0.0,
                    focal_length=0.0,
                    reflectivity=0.99,
                    rotation=(0.0, math.radians(45.0), 0.0),
                    size=(0.3, 0.3),
                    active=True,
                    metadata={"scene": "demo", "angle_deg": 45.0},
                ),
            ]
            for mir in mirror_seeds:
                self._mirrors[mir.mirror_id] = mir

            # ----------------------------------------------------------
            # Lenses (4)
            # ----------------------------------------------------------
            lens_seeds: List[Lens] = [
                Lens(
                    lens_id="lens_biconvex_01",
                    name="Focusing Lens f=100mm",
                    lens_type=LensType.BICONVEX.value,
                    position=(3.0, 1.0, 0.0),
                    normal=(1.0, 0.0, 0.0),
                    focal_length=0.1,
                    radius_left=0.1,
                    radius_right=-0.1,
                    thickness=0.005,
                    refractive_index=1.517,
                    diameter=0.025,
                    active=True,
                    metadata={"scene": "demo"},
                ),
                Lens(
                    lens_id="lens_biconcave_01",
                    name="Diverging Lens f=-50mm",
                    lens_type=LensType.BICONCAVE.value,
                    position=(4.0, 2.0, 0.0),
                    normal=(1.0, 0.0, 0.0),
                    focal_length=-0.05,
                    radius_left=-0.05,
                    radius_right=0.05,
                    thickness=0.003,
                    refractive_index=1.517,
                    diameter=0.02,
                    active=True,
                    metadata={"scene": "demo"},
                ),
                Lens(
                    lens_id="lens_plano_convex_01",
                    name="Collimator Lens f=200mm",
                    lens_type=LensType.PLANO_CONVEX.value,
                    position=(6.0, 1.0, -2.0),
                    normal=(1.0, 0.0, 0.0),
                    focal_length=0.2,
                    radius_left=0.1,
                    radius_right=0.0,
                    thickness=0.004,
                    refractive_index=1.517,
                    diameter=0.04,
                    active=True,
                    metadata={"scene": "demo"},
                ),
                Lens(
                    lens_id="lens_plano_concave_01",
                    name="Beam Expander Lens f=-150mm",
                    lens_type=LensType.PLANO_CONCAVE.value,
                    position=(8.0, 2.0, 1.0),
                    normal=(1.0, 0.0, 0.0),
                    focal_length=-0.15,
                    radius_left=-0.08,
                    radius_right=0.0,
                    thickness=0.003,
                    refractive_index=1.517,
                    diameter=0.035,
                    active=True,
                    metadata={"scene": "demo"},
                ),
            ]
            for lens in lens_seeds:
                self._lenses[lens.lens_id] = lens

            # ----------------------------------------------------------
            # Prisms (3)
            # ----------------------------------------------------------
            prism_seeds: List[Prism] = [
                Prism(
                    prism_id="prism_equilateral_01",
                    name="Equilateral Dispersive Prism",
                    prism_type=PrismType.EQUILATERAL.value,
                    position=(12.0, 1.0, 0.0),
                    apex_angle_rad=math.radians(60.0),
                    refractive_index=1.52,
                    cauchy_a=1.5046,
                    cauchy_b=4200.0,
                    base_length=0.05,
                    height=0.05,
                    rotation=(0.0, 0.0, 0.0),
                    active=True,
                    metadata={"scene": "demo", "material": "crown_glass"},
                ),
                Prism(
                    prism_id="prism_right_angle_01",
                    name="Right-Angle Prism",
                    prism_type=PrismType.RIGHT_ANGLE.value,
                    position=(14.0, 2.0, 2.0),
                    apex_angle_rad=math.radians(90.0),
                    refractive_index=1.517,
                    cauchy_a=1.5046,
                    cauchy_b=4200.0,
                    base_length=0.04,
                    height=0.04,
                    rotation=(0.0, math.radians(45.0), 0.0),
                    active=True,
                    metadata={"scene": "demo"},
                ),
                Prism(
                    prism_id="prism_dispersive_flint",
                    name="Flint Glass Dispersive Prism",
                    prism_type=PrismType.DISPERSIVE.value,
                    position=(16.0, 1.5, -1.0),
                    apex_angle_rad=math.radians(60.0),
                    refractive_index=1.648,
                    cauchy_a=1.6156,
                    cauchy_b=12900.0,
                    base_length=0.05,
                    height=0.05,
                    rotation=(0.0, 0.0, 0.0),
                    active=True,
                    metadata={"scene": "demo", "material": "flint_glass"},
                ),
            ]
            for prism in prism_seeds:
                self._prisms[prism.prism_id] = prism

            # ----------------------------------------------------------
            # Optical Fibers (3)
            # ----------------------------------------------------------
            fiber_seeds: List[OpticalFiber] = [
                OpticalFiber(
                    fiber_id="fiber_single_mode_01",
                    name="Single-Mode Fiber",
                    position=(0.0, 0.0, 0.0),
                    direction=(0.0, 0.0, 1.0),
                    length=10.0,
                    core_index=1.475,
                    cladding_index=1.46,
                    core_radius=4.5e-6,
                    acceptance_angle=_acceptance_angle(1.475, 1.46, 1.0),
                    numerical_aperture=_numerical_aperture(1.475, 1.46),
                    attenuation_per_m=0.0002,
                    active=True,
                    metadata={"scene": "demo", "type": "single_mode"},
                ),
                OpticalFiber(
                    fiber_id="fiber_multi_mode_01",
                    name="Multi-Mode Fiber",
                    position=(2.0, 0.0, 0.0),
                    direction=(0.0, 0.0, 1.0),
                    length=5.0,
                    core_index=1.49,
                    cladding_index=1.40,
                    core_radius=50e-6,
                    acceptance_angle=_acceptance_angle(1.49, 1.40, 1.0),
                    numerical_aperture=_numerical_aperture(1.49, 1.40),
                    attenuation_per_m=0.001,
                    active=True,
                    metadata={"scene": "demo", "type": "multi_mode"},
                ),
                OpticalFiber(
                    fiber_id="fiber_plastic_01",
                    name="Plastic Optical Fiber",
                    position=(4.0, 0.0, 0.0),
                    direction=(0.0, 1.0, 0.0),
                    length=2.0,
                    core_index=1.49,
                    cladding_index=1.402,
                    core_radius=250e-6,
                    acceptance_angle=_acceptance_angle(1.49, 1.402, 1.0),
                    numerical_aperture=_numerical_aperture(1.49, 1.402),
                    attenuation_per_m=0.18,
                    active=True,
                    metadata={"scene": "demo", "type": "plastic"},
                ),
            ]
            for fiber in fiber_seeds:
                self._fibers[fiber.fiber_id] = fiber

            # ----------------------------------------------------------
            # Detectors (4)
            # ----------------------------------------------------------
            detector_seeds: List[Detector] = [
                Detector(
                    detector_id="det_photodiode_01",
                    name="Silicon Photodiode",
                    position=(20.0, 1.0, 0.0),
                    direction=(-1.0, 0.0, 0.0),
                    sensitivity=0.6,
                    wavelength_min_nm=400.0,
                    wavelength_max_nm=1100.0,
                    threshold=0.001,
                    active=True,
                    metadata={"scene": "demo", "type": "si_photodiode"},
                ),
                Detector(
                    detector_id="det_ccd_01",
                    name="CCD Camera Sensor",
                    position=(18.0, 2.0, 2.0),
                    direction=(-1.0, 0.0, 0.0),
                    sensitivity=0.4,
                    wavelength_min_nm=380.0,
                    wavelength_max_nm=750.0,
                    threshold=0.0005,
                    active=True,
                    metadata={"scene": "demo", "type": "ccd"},
                ),
                Detector(
                    detector_id="det_thermal_01",
                    name="Thermal Power Meter",
                    position=(15.0, 1.0, -3.0),
                    direction=(0.0, 1.0, 0.0),
                    sensitivity=0.3,
                    wavelength_min_nm=700.0,
                    wavelength_max_nm=2000.0,
                    threshold=0.01,
                    active=True,
                    metadata={"scene": "demo", "type": "thermal"},
                ),
                Detector(
                    detector_id="det_uv_sensor_01",
                    name="UV Sensor",
                    position=(5.0, 4.0, 5.0),
                    direction=(0.0, -1.0, 0.0),
                    sensitivity=0.5,
                    wavelength_min_nm=200.0,
                    wavelength_max_nm=400.0,
                    threshold=0.002,
                    active=True,
                    metadata={"scene": "demo", "type": "uv"},
                ),
            ]
            for det in detector_seeds:
                self._detectors[det.detector_id] = det

            self._seeded = True
            self._emit(
                OpticsEventKind.SYSTEM_RESET.value,
                "Optics system seeded with initial data.",
                {
                    "sources": len(self._sources),
                    "mirrors": len(self._mirrors),
                    "lenses": len(self._lenses),
                    "prisms": len(self._prisms),
                    "fibers": len(self._fibers),
                    "detectors": len(self._detectors),
                    "mediums": len(self._mediums),
                },
            )
            self._refresh_stats()

    # ------------------------------------------------------------------
    # Light Source Lifecycle
    # ------------------------------------------------------------------

    def register_light_source(
        self,
        source_id: str = "",
        name: str = "",
        source_type: str = LightSourceType.POINT.value,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        direction: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        wavelength_nm: float = 550.0,
        intensity: float = 1.0,
        power_w: float = 1.0,
        divergence_rad: float = 0.0,
        polarization: str = PolarizationType.UNPOLARIZED.value,
        coherent: bool = False,
        active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[LightSource]]:
        """Register a new light source in the system.

        If ``source_id`` is empty, a unique ID is generated automatically.
        The ``source_type`` is coerced to a valid :class:`LightSourceType`.
        The color is computed from the wavelength using the standard
        wavelength-to-RGB mapping.
        """
        with self._lock:
            sid = str(source_id or "").strip()
            if not sid:
                sid = _new_id("src")
            if sid in self._sources:
                return (False, f"Light source '{sid}' already exists.",
                        self._sources[sid])
            if len(self._sources) >= self._config.max_sources:
                _evict_fifo_dict(self._sources, self._config.max_sources)
            stype = _coerce_enum(LightSourceType, source_type,
                                  LightSourceType.POINT)
            stype_val = (stype.value if isinstance(stype, LightSourceType)
                         else LightSourceType.POINT.value)
            pol = _coerce_enum(PolarizationType, polarization,
                                PolarizationType.UNPOLARIZED)
            pol_val = (pol.value if isinstance(pol, PolarizationType)
                       else PolarizationType.UNPOLARIZED.value)
            wl = max(1.0, _safe_float(wavelength_nm, 550.0))
            source = LightSource(
                source_id=sid,
                name=str(name) if name else sid,
                source_type=stype_val,
                position=_to_vec3(position),
                direction=_vec_normalize(_to_vec3(direction, (0.0, 0.0, 1.0))),
                wavelength_nm=wl,
                intensity=_clamp(_safe_float(intensity, 1.0), 0.0, 1.0),
                power_w=max(0.0, _safe_float(power_w, 1.0)),
                divergence_rad=max(0.0, _safe_float(divergence_rad, 0.0)),
                polarization=pol_val,
                coherent=bool(coherent),
                color=_wavelength_to_rgb(wl),
                active=bool(active),
                metadata=metadata or {},
            )
            self._sources[sid] = source
            self._emit(
                OpticsEventKind.SOURCE_REGISTERED.value,
                f"Light source '{sid}' registered.",
                {"source_id": sid, "source_type": stype_val,
                 "wavelength_nm": wl},
            )
            self._refresh_stats()
            return (True, f"Light source '{sid}' registered.", source)

    def get_light_source(self, source_id: str) -> Optional[LightSource]:
        """Return the light source with the given ID, or None."""
        with self._lock:
            return self._sources.get(str(source_id or "").strip())

    def list_light_sources(
        self,
        source_type: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[LightSource]:
        """List light sources, optionally filtered by type and active state."""
        with self._lock:
            stype_val = ""
            if source_type:
                st = _coerce_enum(LightSourceType, source_type, None)
                stype_val = (st.value if isinstance(st, LightSourceType)
                             else str(source_type))
            results: List[LightSource] = []
            for src in self._sources.values():
                if stype_val and src.source_type != stype_val:
                    continue
                if active_only and not src.active:
                    continue
                results.append(src)
            return results[:max(0, int(limit))]

    def update_light_source(
        self,
        source_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[LightSource]]:
        """Apply partial updates to an existing light source.

        Accepts a dict of field names to new values. Only the provided
        keys are applied; unknown keys are silently ignored.
        """
        with self._lock:
            sid = str(source_id or "").strip()
            src = self._sources.get(sid)
            if src is None:
                return (False, f"Light source '{sid}' not found.", None)
            if "name" in updates:
                src.name = str(updates["name"])
            if "source_type" in updates:
                st = _coerce_enum(LightSourceType, updates["source_type"], None)
                if isinstance(st, LightSourceType):
                    src.source_type = st.value
            if "position" in updates:
                src.position = _to_vec3(updates["position"], src.position)
            if "direction" in updates:
                src.direction = _vec_normalize(
                    _to_vec3(updates["direction"], src.direction)
                )
            if "wavelength_nm" in updates:
                src.wavelength_nm = max(1.0, _safe_float(
                    updates["wavelength_nm"], src.wavelength_nm))
                src.color = _wavelength_to_rgb(src.wavelength_nm)
            if "intensity" in updates:
                src.intensity = _clamp(_safe_float(
                    updates["intensity"], src.intensity), 0.0, 1.0)
            if "power_w" in updates:
                src.power_w = max(0.0, _safe_float(updates["power_w"], src.power_w))
            if "divergence_rad" in updates:
                src.divergence_rad = max(0.0, _safe_float(
                    updates["divergence_rad"], src.divergence_rad))
            if "polarization" in updates:
                pol = _coerce_enum(PolarizationType, updates["polarization"], None)
                if isinstance(pol, PolarizationType):
                    src.polarization = pol.value
            if "coherent" in updates:
                src.coherent = bool(updates["coherent"])
            if "active" in updates:
                src.active = bool(updates["active"])
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                src.metadata = dict(updates["metadata"])
            src.updated_at = _now()
            self._emit(
                OpticsEventKind.SOURCE_UPDATED.value,
                f"Light source '{sid}' updated.",
                {"source_id": sid},
            )
            self._refresh_stats()
            return (True, f"Light source '{sid}' updated.", src)

    def remove_light_source(
        self, source_id: str
    ) -> Tuple[bool, str, Optional[LightSource]]:
        """Remove a light source from the system and return it."""
        with self._lock:
            sid = str(source_id or "").strip()
            src = self._sources.pop(sid, None)
            if src is None:
                return (False, f"Light source '{sid}' not found.", None)
            self._emit(
                OpticsEventKind.SOURCE_REMOVED.value,
                f"Light source '{sid}' removed.",
                {"source_id": sid},
            )
            self._refresh_stats()
            return (True, f"Light source '{sid}' removed.", src)

    # ------------------------------------------------------------------
    # Mirror Lifecycle
    # ------------------------------------------------------------------

    def register_mirror(
        self,
        mirror_id: str = "",
        name: str = "",
        mirror_type: str = MirrorType.PLANE.value,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        normal: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        curvature_radius: float = 0.0,
        reflectivity: float = 1.0,
        rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        size: Tuple[float, float] = (1.0, 1.0),
        active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Mirror]]:
        """Register a new mirror in the system.

        For concave and convex mirrors, the focal length is computed
        automatically from the curvature radius as f = R / 2. Plane
        mirrors have zero curvature and zero focal length.
        """
        with self._lock:
            mid = str(mirror_id or "").strip()
            if not mid:
                mid = _new_id("mir")
            if mid in self._mirrors:
                return (False, f"Mirror '{mid}' already exists.",
                        self._mirrors[mid])
            if len(self._mirrors) >= self._config.max_mirrors:
                _evict_fifo_dict(self._mirrors, self._config.max_mirrors)
            mtype = _coerce_enum(MirrorType, mirror_type, MirrorType.PLANE)
            mtype_val = (mtype.value if isinstance(mtype, MirrorType)
                         else MirrorType.PLANE.value)
            cr = _safe_float(curvature_radius, 0.0)
            fl = _mirror_focal_length(cr) if cr != 0.0 else 0.0
            mirror = Mirror(
                mirror_id=mid,
                name=str(name) if name else mid,
                mirror_type=mtype_val,
                position=_to_vec3(position),
                normal=_vec_normalize(_to_vec3(normal, (0.0, 0.0, 1.0))),
                curvature_radius=cr,
                focal_length=fl,
                reflectivity=_clamp(_safe_float(reflectivity, 1.0), 0.0, 1.0),
                rotation=_to_vec3(rotation),
                size=_to_vec2(size, (1.0, 1.0)),
                active=bool(active),
                metadata=metadata or {},
            )
            self._mirrors[mid] = mirror
            self._emit(
                OpticsEventKind.MIRROR_REGISTERED.value,
                f"Mirror '{mid}' registered.",
                {"mirror_id": mid, "mirror_type": mtype_val,
                 "focal_length": fl},
            )
            self._refresh_stats()
            return (True, f"Mirror '{mid}' registered.", mirror)

    def get_mirror(self, mirror_id: str) -> Optional[Mirror]:
        """Return the mirror with the given ID, or None."""
        with self._lock:
            return self._mirrors.get(str(mirror_id or "").strip())

    def list_mirrors(
        self,
        mirror_type: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[Mirror]:
        """List mirrors, optionally filtered by type and active state."""
        with self._lock:
            mtype_val = ""
            if mirror_type:
                mt = _coerce_enum(MirrorType, mirror_type, None)
                mtype_val = (mt.value if isinstance(mt, MirrorType)
                             else str(mirror_type))
            results: List[Mirror] = []
            for mir in self._mirrors.values():
                if mtype_val and mir.mirror_type != mtype_val:
                    continue
                if active_only and not mir.active:
                    continue
                results.append(mir)
            return results[:max(0, int(limit))]

    def update_mirror(
        self,
        mirror_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[Mirror]]:
        """Apply partial updates to an existing mirror."""
        with self._lock:
            mid = str(mirror_id or "").strip()
            mir = self._mirrors.get(mid)
            if mir is None:
                return (False, f"Mirror '{mid}' not found.", None)
            if "name" in updates:
                mir.name = str(updates["name"])
            if "mirror_type" in updates:
                mt = _coerce_enum(MirrorType, updates["mirror_type"], None)
                if isinstance(mt, MirrorType):
                    mir.mirror_type = mt.value
            if "position" in updates:
                mir.position = _to_vec3(updates["position"], mir.position)
            if "normal" in updates:
                mir.normal = _vec_normalize(
                    _to_vec3(updates["normal"], mir.normal))
            if "curvature_radius" in updates:
                mir.curvature_radius = _safe_float(
                    updates["curvature_radius"], mir.curvature_radius)
                mir.focal_length = (_mirror_focal_length(mir.curvature_radius)
                                    if mir.curvature_radius != 0.0 else 0.0)
            if "reflectivity" in updates:
                mir.reflectivity = _clamp(_safe_float(
                    updates["reflectivity"], mir.reflectivity), 0.0, 1.0)
            if "rotation" in updates:
                mir.rotation = _to_vec3(updates["rotation"], mir.rotation)
            if "size" in updates:
                mir.size = _to_vec2(updates["size"], mir.size)
            if "active" in updates:
                mir.active = bool(updates["active"])
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                mir.metadata = dict(updates["metadata"])
            mir.updated_at = _now()
            self._emit(
                OpticsEventKind.MIRROR_UPDATED.value,
                f"Mirror '{mid}' updated.",
                {"mirror_id": mid},
            )
            self._refresh_stats()
            return (True, f"Mirror '{mid}' updated.", mir)

    def remove_mirror(
        self, mirror_id: str
    ) -> Tuple[bool, str, Optional[Mirror]]:
        """Remove a mirror from the system and return it."""
        with self._lock:
            mid = str(mirror_id or "").strip()
            mir = self._mirrors.pop(mid, None)
            if mir is None:
                return (False, f"Mirror '{mid}' not found.", None)
            self._emit(
                OpticsEventKind.MIRROR_REMOVED.value,
                f"Mirror '{mid}' removed.",
                {"mirror_id": mid},
            )
            self._refresh_stats()
            return (True, f"Mirror '{mid}' removed.", mir)

    # ------------------------------------------------------------------
    # Lens Lifecycle
    # ------------------------------------------------------------------

    def register_lens(
        self,
        lens_id: str = "",
        name: str = "",
        lens_type: str = LensType.BICONVEX.value,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        normal: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        focal_length: float = 0.1,
        radius_left: float = 0.5,
        radius_right: float = -0.5,
        thickness: float = 0.01,
        refractive_index: float = 1.52,
        diameter: float = 0.05,
        active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Lens]]:
        """Register a new lens in the system.

        The focal length can be provided directly or computed from the
        lensmaker's equation using the two radii of curvature and the
        refractive index.
        """
        with self._lock:
            lid = str(lens_id or "").strip()
            if not lid:
                lid = _new_id("lens")
            if lid in self._lenses:
                return (False, f"Lens '{lid}' already exists.",
                        self._lenses[lid])
            if len(self._lenses) >= self._config.max_lenses:
                _evict_fifo_dict(self._lenses, self._config.max_lenses)
            ltype = _coerce_enum(LensType, lens_type, LensType.BICONVEX)
            ltype_val = (ltype.value if isinstance(ltype, LensType)
                         else LensType.BICONVEX.value)
            lens = Lens(
                lens_id=lid,
                name=str(name) if name else lid,
                lens_type=ltype_val,
                position=_to_vec3(position),
                normal=_vec_normalize(_to_vec3(normal, (0.0, 0.0, 1.0))),
                focal_length=_safe_float(focal_length, 0.1),
                radius_left=_safe_float(radius_left, 0.5),
                radius_right=_safe_float(radius_right, -0.5),
                thickness=max(0.0, _safe_float(thickness, 0.01)),
                refractive_index=max(1.0, _safe_float(refractive_index, 1.52)),
                diameter=max(0.0, _safe_float(diameter, 0.05)),
                active=bool(active),
                metadata=metadata or {},
            )
            self._lenses[lid] = lens
            self._emit(
                OpticsEventKind.LENS_REGISTERED.value,
                f"Lens '{lid}' registered.",
                {"lens_id": lid, "lens_type": ltype_val,
                 "focal_length": lens.focal_length},
            )
            self._refresh_stats()
            return (True, f"Lens '{lid}' registered.", lens)

    def get_lens(self, lens_id: str) -> Optional[Lens]:
        """Return the lens with the given ID, or None."""
        with self._lock:
            return self._lenses.get(str(lens_id or "").strip())

    def list_lenses(
        self,
        lens_type: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[Lens]:
        """List lenses, optionally filtered by type and active state."""
        with self._lock:
            ltype_val = ""
            if lens_type:
                lt = _coerce_enum(LensType, lens_type, None)
                ltype_val = (lt.value if isinstance(lt, LensType)
                             else str(lens_type))
            results: List[Lens] = []
            for lens in self._lenses.values():
                if ltype_val and lens.lens_type != ltype_val:
                    continue
                if active_only and not lens.active:
                    continue
                results.append(lens)
            return results[:max(0, int(limit))]

    def update_lens(
        self,
        lens_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[Lens]]:
        """Apply partial updates to an existing lens."""
        with self._lock:
            lid = str(lens_id or "").strip()
            lens = self._lenses.get(lid)
            if lens is None:
                return (False, f"Lens '{lid}' not found.", None)
            if "name" in updates:
                lens.name = str(updates["name"])
            if "lens_type" in updates:
                lt = _coerce_enum(LensType, updates["lens_type"], None)
                if isinstance(lt, LensType):
                    lens.lens_type = lt.value
            if "position" in updates:
                lens.position = _to_vec3(updates["position"], lens.position)
            if "normal" in updates:
                lens.normal = _vec_normalize(
                    _to_vec3(updates["normal"], lens.normal))
            if "focal_length" in updates:
                lens.focal_length = _safe_float(
                    updates["focal_length"], lens.focal_length)
            if "radius_left" in updates:
                lens.radius_left = _safe_float(
                    updates["radius_left"], lens.radius_left)
            if "radius_right" in updates:
                lens.radius_right = _safe_float(
                    updates["radius_right"], lens.radius_right)
            if "thickness" in updates:
                lens.thickness = max(0.0, _safe_float(
                    updates["thickness"], lens.thickness))
            if "refractive_index" in updates:
                lens.refractive_index = max(1.0, _safe_float(
                    updates["refractive_index"], lens.refractive_index))
            if "diameter" in updates:
                lens.diameter = max(0.0, _safe_float(
                    updates["diameter"], lens.diameter))
            if "active" in updates:
                lens.active = bool(updates["active"])
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                lens.metadata = dict(updates["metadata"])
            lens.updated_at = _now()
            self._emit(
                OpticsEventKind.LENS_UPDATED.value,
                f"Lens '{lid}' updated.",
                {"lens_id": lid},
            )
            self._refresh_stats()
            return (True, f"Lens '{lid}' updated.", lens)

    def remove_lens(
        self, lens_id: str
    ) -> Tuple[bool, str, Optional[Lens]]:
        """Remove a lens from the system and return it."""
        with self._lock:
            lid = str(lens_id or "").strip()
            lens = self._lenses.pop(lid, None)
            if lens is None:
                return (False, f"Lens '{lid}' not found.", None)
            self._emit(
                OpticsEventKind.LENS_REMOVED.value,
                f"Lens '{lid}' removed.",
                {"lens_id": lid},
            )
            self._refresh_stats()
            return (True, f"Lens '{lid}' removed.", lens)

    # ------------------------------------------------------------------
    # Prism Lifecycle
    # ------------------------------------------------------------------

    def register_prism(
        self,
        prism_id: str = "",
        name: str = "",
        prism_type: str = PrismType.TRIANGULAR.value,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        apex_angle_rad: float = math.radians(60.0),
        refractive_index: float = 1.52,
        cauchy_a: float = 1.50,
        cauchy_b: float = 4500.0,
        base_length: float = 0.05,
        height: float = 0.05,
        rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Prism]]:
        """Register a new prism in the system.

        The prism has both a base refractive index and Cauchy
        dispersion coefficients (A, B) for wavelength-dependent
        refractive index calculation via n = A + B / lambda^2.
        """
        with self._lock:
            pid = str(prism_id or "").strip()
            if not pid:
                pid = _new_id("prism")
            if pid in self._prisms:
                return (False, f"Prism '{pid}' already exists.",
                        self._prisms[pid])
            if len(self._prisms) >= self._config.max_prisms:
                _evict_fifo_dict(self._prisms, self._config.max_prisms)
            ptype = _coerce_enum(PrismType, prism_type, PrismType.TRIANGULAR)
            ptype_val = (ptype.value if isinstance(ptype, PrismType)
                         else PrismType.TRIANGULAR.value)
            prism = Prism(
                prism_id=pid,
                name=str(name) if name else pid,
                prism_type=ptype_val,
                position=_to_vec3(position),
                apex_angle_rad=max(0.0, _safe_float(apex_angle_rad,
                                                     math.radians(60.0))),
                refractive_index=max(1.0, _safe_float(refractive_index, 1.52)),
                cauchy_a=_safe_float(cauchy_a, 1.50),
                cauchy_b=_safe_float(cauchy_b, 4500.0),
                base_length=max(0.0, _safe_float(base_length, 0.05)),
                height=max(0.0, _safe_float(height, 0.05)),
                rotation=_to_vec3(rotation),
                active=bool(active),
                metadata=metadata or {},
            )
            self._prisms[pid] = prism
            self._emit(
                OpticsEventKind.PRISM_REGISTERED.value,
                f"Prism '{pid}' registered.",
                {"prism_id": pid, "prism_type": ptype_val,
                 "apex_angle_deg": math.degrees(prism.apex_angle_rad)},
            )
            self._refresh_stats()
            return (True, f"Prism '{pid}' registered.", prism)

    def get_prism(self, prism_id: str) -> Optional[Prism]:
        """Return the prism with the given ID, or None."""
        with self._lock:
            return self._prisms.get(str(prism_id or "").strip())

    def list_prisms(
        self,
        prism_type: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[Prism]:
        """List prisms, optionally filtered by type and active state."""
        with self._lock:
            ptype_val = ""
            if prism_type:
                pt = _coerce_enum(PrismType, prism_type, None)
                ptype_val = (pt.value if isinstance(pt, PrismType)
                             else str(prism_type))
            results: List[Prism] = []
            for prism in self._prisms.values():
                if ptype_val and prism.prism_type != ptype_val:
                    continue
                if active_only and not prism.active:
                    continue
                results.append(prism)
            return results[:max(0, int(limit))]

    def update_prism(
        self,
        prism_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[Prism]]:
        """Apply partial updates to an existing prism."""
        with self._lock:
            pid = str(prism_id or "").strip()
            prism = self._prisms.get(pid)
            if prism is None:
                return (False, f"Prism '{pid}' not found.", None)
            if "name" in updates:
                prism.name = str(updates["name"])
            if "prism_type" in updates:
                pt = _coerce_enum(PrismType, updates["prism_type"], None)
                if isinstance(pt, PrismType):
                    prism.prism_type = pt.value
            if "position" in updates:
                prism.position = _to_vec3(updates["position"], prism.position)
            if "apex_angle_rad" in updates:
                prism.apex_angle_rad = max(0.0, _safe_float(
                    updates["apex_angle_rad"], prism.apex_angle_rad))
            if "refractive_index" in updates:
                prism.refractive_index = max(1.0, _safe_float(
                    updates["refractive_index"], prism.refractive_index))
            if "cauchy_a" in updates:
                prism.cauchy_a = _safe_float(updates["cauchy_a"], prism.cauchy_a)
            if "cauchy_b" in updates:
                prism.cauchy_b = _safe_float(updates["cauchy_b"], prism.cauchy_b)
            if "base_length" in updates:
                prism.base_length = max(0.0, _safe_float(
                    updates["base_length"], prism.base_length))
            if "height" in updates:
                prism.height = max(0.0, _safe_float(
                    updates["height"], prism.height))
            if "rotation" in updates:
                prism.rotation = _to_vec3(updates["rotation"], prism.rotation)
            if "active" in updates:
                prism.active = bool(updates["active"])
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                prism.metadata = dict(updates["metadata"])
            prism.updated_at = _now()
            self._emit(
                OpticsEventKind.PRISM_UPDATED.value,
                f"Prism '{pid}' updated.",
                {"prism_id": pid},
            )
            self._refresh_stats()
            return (True, f"Prism '{pid}' updated.", prism)

    def remove_prism(
        self, prism_id: str
    ) -> Tuple[bool, str, Optional[Prism]]:
        """Remove a prism from the system and return it."""
        with self._lock:
            pid = str(prism_id or "").strip()
            prism = self._prisms.pop(pid, None)
            if prism is None:
                return (False, f"Prism '{pid}' not found.", None)
            self._emit(
                OpticsEventKind.PRISM_REMOVED.value,
                f"Prism '{pid}' removed.",
                {"prism_id": pid},
            )
            self._refresh_stats()
            return (True, f"Prism '{pid}' removed.", prism)

    # ------------------------------------------------------------------
    # Optical Fiber Lifecycle
    # ------------------------------------------------------------------

    def register_optical_fiber(
        self,
        fiber_id: str = "",
        name: str = "",
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        direction: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        length: float = 1.0,
        core_index: float = 1.50,
        cladding_index: float = 1.48,
        core_radius: float = 50e-6,
        attenuation_per_m: float = 0.001,
        active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[OpticalFiber]]:
        """Register a new optical fiber in the system.

        The acceptance angle and numerical aperture are computed
        automatically from the core and cladding refractive indices.
        """
        with self._lock:
            fid = str(fiber_id or "").strip()
            if not fid:
                fid = _new_id("fiber")
            if fid in self._fibers:
                return (False, f"Optical fiber '{fid}' already exists.",
                        self._fibers[fid])
            if len(self._fibers) >= self._config.max_fibers:
                _evict_fifo_dict(self._fibers, self._config.max_fibers)
            n_core = max(1.0, _safe_float(core_index, 1.50))
            n_clad = max(1.0, _safe_float(cladding_index, 1.48))
            fiber = OpticalFiber(
                fiber_id=fid,
                name=str(name) if name else fid,
                position=_to_vec3(position),
                direction=_vec_normalize(_to_vec3(direction, (0.0, 0.0, 1.0))),
                length=max(0.0, _safe_float(length, 1.0)),
                core_index=n_core,
                cladding_index=n_clad,
                core_radius=max(0.0, _safe_float(core_radius, 50e-6)),
                acceptance_angle=_acceptance_angle(n_core, n_clad, 1.0),
                numerical_aperture=_numerical_aperture(n_core, n_clad),
                attenuation_per_m=max(0.0, _safe_float(attenuation_per_m, 0.001)),
                active=bool(active),
                metadata=metadata or {},
            )
            self._fibers[fid] = fiber
            self._emit(
                OpticsEventKind.FIBER_REGISTERED.value,
                f"Optical fiber '{fid}' registered.",
                {"fiber_id": fid, "numerical_aperture": fiber.numerical_aperture,
                 "acceptance_angle_rad": fiber.acceptance_angle},
            )
            self._refresh_stats()
            return (True, f"Optical fiber '{fid}' registered.", fiber)

    def get_optical_fiber(self, fiber_id: str) -> Optional[OpticalFiber]:
        """Return the optical fiber with the given ID, or None."""
        with self._lock:
            return self._fibers.get(str(fiber_id or "").strip())

    def list_optical_fibers(
        self,
        active_only: bool = False,
        limit: int = 100,
    ) -> List[OpticalFiber]:
        """List optical fibers, optionally filtered by active state."""
        with self._lock:
            results: List[OpticalFiber] = []
            for fiber in self._fibers.values():
                if active_only and not fiber.active:
                    continue
                results.append(fiber)
            return results[:max(0, int(limit))]

    def update_optical_fiber(
        self,
        fiber_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[OpticalFiber]]:
        """Apply partial updates to an existing optical fiber.

        When core_index or cladding_index changes, the acceptance angle
        and numerical aperture are recomputed automatically.
        """
        with self._lock:
            fid = str(fiber_id or "").strip()
            fiber = self._fibers.get(fid)
            if fiber is None:
                return (False, f"Optical fiber '{fid}' not found.", None)
            if "name" in updates:
                fiber.name = str(updates["name"])
            if "position" in updates:
                fiber.position = _to_vec3(updates["position"], fiber.position)
            if "direction" in updates:
                fiber.direction = _vec_normalize(
                    _to_vec3(updates["direction"], fiber.direction))
            if "length" in updates:
                fiber.length = max(0.0, _safe_float(updates["length"], fiber.length))
            if "core_index" in updates:
                fiber.core_index = max(1.0, _safe_float(
                    updates["core_index"], fiber.core_index))
            if "cladding_index" in updates:
                fiber.cladding_index = max(1.0, _safe_float(
                    updates["cladding_index"], fiber.cladding_index))
            if "core_radius" in updates:
                fiber.core_radius = max(0.0, _safe_float(
                    updates["core_radius"], fiber.core_radius))
            if "attenuation_per_m" in updates:
                fiber.attenuation_per_m = max(0.0, _safe_float(
                    updates["attenuation_per_m"], fiber.attenuation_per_m))
            if "active" in updates:
                fiber.active = bool(updates["active"])
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                fiber.metadata = dict(updates["metadata"])
            # Recompute derived properties.
            fiber.acceptance_angle = _acceptance_angle(
                fiber.core_index, fiber.cladding_index, 1.0)
            fiber.numerical_aperture = _numerical_aperture(
                fiber.core_index, fiber.cladding_index)
            fiber.updated_at = _now()
            self._emit(
                OpticsEventKind.FIBER_UPDATED.value,
                f"Optical fiber '{fid}' updated.",
                {"fiber_id": fid},
            )
            self._refresh_stats()
            return (True, f"Optical fiber '{fid}' updated.", fiber)

    def remove_optical_fiber(
        self, fiber_id: str
    ) -> Tuple[bool, str, Optional[OpticalFiber]]:
        """Remove an optical fiber from the system and return it."""
        with self._lock:
            fid = str(fiber_id or "").strip()
            fiber = self._fibers.pop(fid, None)
            if fiber is None:
                return (False, f"Optical fiber '{fid}' not found.", None)
            self._emit(
                OpticsEventKind.FIBER_REMOVED.value,
                f"Optical fiber '{fid}' removed.",
                {"fiber_id": fid},
            )
            self._refresh_stats()
            return (True, f"Optical fiber '{fid}' removed.", fiber)

    # ------------------------------------------------------------------
    # Detector Lifecycle
    # ------------------------------------------------------------------

    def register_detector(
        self,
        detector_id: str = "",
        name: str = "",
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        direction: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        sensitivity: float = 0.5,
        wavelength_min_nm: float = _VISIBLE_MIN_NM,
        wavelength_max_nm: float = _VISIBLE_MAX_NM,
        threshold: float = 0.01,
        active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Detector]]:
        """Register a new light detector in the system.

        Detectors measure incident light intensity within a specified
        wavelength range and above a detection threshold.
        """
        with self._lock:
            did = str(detector_id or "").strip()
            if not did:
                did = _new_id("det")
            if did in self._detectors:
                return (False, f"Detector '{did}' already exists.",
                        self._detectors[did])
            if len(self._detectors) >= self._config.max_detectors:
                _evict_fifo_dict(self._detectors, self._config.max_detectors)
            wmin = max(1.0, _safe_float(wavelength_min_nm, _VISIBLE_MIN_NM))
            wmax = max(wmin, _safe_float(wavelength_max_nm, _VISIBLE_MAX_NM))
            detector = Detector(
                detector_id=did,
                name=str(name) if name else did,
                position=_to_vec3(position),
                direction=_vec_normalize(_to_vec3(direction, (0.0, 0.0, 1.0))),
                sensitivity=_clamp(_safe_float(sensitivity, 0.5), 0.0, 1.0),
                wavelength_min_nm=wmin,
                wavelength_max_nm=wmax,
                threshold=max(0.0, _safe_float(threshold, 0.01)),
                active=bool(active),
                metadata=metadata or {},
            )
            self._detectors[did] = detector
            self._emit(
                OpticsEventKind.DETECTOR_REGISTERED.value,
                f"Detector '{did}' registered.",
                {"detector_id": did, "wavelength_range_nm": [wmin, wmax]},
            )
            self._refresh_stats()
            return (True, f"Detector '{did}' registered.", detector)

    def get_detector(self, detector_id: str) -> Optional[Detector]:
        """Return the detector with the given ID, or None."""
        with self._lock:
            return self._detectors.get(str(detector_id or "").strip())

    def list_detectors(
        self,
        active_only: bool = False,
        limit: int = 100,
    ) -> List[Detector]:
        """List detectors, optionally filtered by active state."""
        with self._lock:
            results: List[Detector] = []
            for det in self._detectors.values():
                if active_only and not det.active:
                    continue
                results.append(det)
            return results[:max(0, int(limit))]

    def update_detector(
        self,
        detector_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[Detector]]:
        """Apply partial updates to an existing detector."""
        with self._lock:
            did = str(detector_id or "").strip()
            det = self._detectors.get(did)
            if det is None:
                return (False, f"Detector '{did}' not found.", None)
            if "name" in updates:
                det.name = str(updates["name"])
            if "position" in updates:
                det.position = _to_vec3(updates["position"], det.position)
            if "direction" in updates:
                det.direction = _vec_normalize(
                    _to_vec3(updates["direction"], det.direction))
            if "sensitivity" in updates:
                det.sensitivity = _clamp(_safe_float(
                    updates["sensitivity"], det.sensitivity), 0.0, 1.0)
            if "wavelength_min_nm" in updates:
                det.wavelength_min_nm = max(1.0, _safe_float(
                    updates["wavelength_min_nm"], det.wavelength_min_nm))
            if "wavelength_max_nm" in updates:
                det.wavelength_max_nm = max(det.wavelength_min_nm,
                    _safe_float(updates["wavelength_max_nm"], det.wavelength_max_nm))
            if "threshold" in updates:
                det.threshold = max(0.0, _safe_float(
                    updates["threshold"], det.threshold))
            if "active" in updates:
                det.active = bool(updates["active"])
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                det.metadata = dict(updates["metadata"])
            det.updated_at = _now()
            self._emit(
                OpticsEventKind.DETECTOR_UPDATED.value,
                f"Detector '{did}' updated.",
                {"detector_id": did},
            )
            self._refresh_stats()
            return (True, f"Detector '{did}' updated.", det)

    def remove_detector(
        self, detector_id: str
    ) -> Tuple[bool, str, Optional[Detector]]:
        """Remove a detector from the system and return it."""
        with self._lock:
            did = str(detector_id or "").strip()
            det = self._detectors.pop(did, None)
            if det is None:
                return (False, f"Detector '{did}' not found.", None)
            self._emit(
                OpticsEventKind.DETECTOR_REMOVED.value,
                f"Detector '{did}' removed.",
                {"detector_id": did},
            )
            self._refresh_stats()
            return (True, f"Detector '{did}' removed.", det)

    # ------------------------------------------------------------------
    # Medium Lifecycle
    # ------------------------------------------------------------------

    def register_medium(
        self,
        medium_id: str = "",
        name: str = "",
        medium_type: str = MediumType.AIR.value,
        refractive_index: float = _DEFAULT_AIR_INDEX,
        absorption_coeff: float = 0.0,
        scattering_coeff: float = 0.0,
        temperature_k: float = 293.15,
        density_kg_m3: float = 1.225,
        active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Medium]]:
        """Register a new optical medium in the system.

        If the medium type matches a known type (air, water, glass,
        etc.), default values are loaded for any unspecified fields.
        """
        with self._lock:
            mid = str(medium_id or "").strip()
            if not mid:
                mid = _new_id("med")
            if mid in self._mediums:
                return (False, f"Medium '{mid}' already exists.",
                        self._mediums[mid])
            if len(self._mediums) >= self._config.max_mediums:
                _evict_fifo_dict(self._mediums, self._config.max_mediums)
            mtype = _coerce_enum(MediumType, medium_type, MediumType.AIR)
            mtype_val = (mtype.value if isinstance(mtype, MediumType)
                         else MediumType.AIR.value)
            # Use default values for known medium types when not overridden.
            default_n, default_abs = self._default_medium_for_type(mtype_val)
            n_val = _safe_float(refractive_index, default_n)
            abs_val = _safe_float(absorption_coeff, default_abs)
            medium = Medium(
                medium_id=mid,
                name=str(name) if name else mid,
                medium_type=mtype_val,
                refractive_index=max(1.0, n_val),
                absorption_coeff=max(0.0, abs_val),
                scattering_coeff=max(0.0, _safe_float(scattering_coeff, 0.0)),
                temperature_k=max(0.0, _safe_float(temperature_k, 293.15)),
                density_kg_m3=max(0.0, _safe_float(density_kg_m3, 1.225)),
                active=bool(active),
                metadata=metadata or {},
            )
            self._mediums[mid] = medium
            self._emit(
                OpticsEventKind.MEDIUM_REGISTERED.value,
                f"Medium '{mid}' registered.",
                {"medium_id": mid, "medium_type": mtype_val,
                 "refractive_index": n_val},
            )
            self._refresh_stats()
            return (True, f"Medium '{mid}' registered.", medium)

    def get_medium(self, medium_id: str) -> Optional[Medium]:
        """Return the medium with the given ID, or None."""
        with self._lock:
            return self._mediums.get(str(medium_id or "").strip())

    def list_mediums(
        self,
        medium_type: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[Medium]:
        """List mediums, optionally filtered by type and active state."""
        with self._lock:
            mtype_val = ""
            if medium_type:
                mt = _coerce_enum(MediumType, medium_type, None)
                mtype_val = (mt.value if isinstance(mt, MediumType)
                             else str(medium_type))
            results: List[Medium] = []
            for med in self._mediums.values():
                if mtype_val and med.medium_type != mtype_val:
                    continue
                if active_only and not med.active:
                    continue
                results.append(med)
            return results[:max(0, int(limit))]

    def update_medium(
        self,
        medium_id: str,
        updates: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[Medium]]:
        """Apply partial updates to an existing medium."""
        with self._lock:
            mid = str(medium_id or "").strip()
            med = self._mediums.get(mid)
            if med is None:
                return (False, f"Medium '{mid}' not found.", None)
            if "name" in updates:
                med.name = str(updates["name"])
            if "medium_type" in updates:
                mt = _coerce_enum(MediumType, updates["medium_type"], None)
                if isinstance(mt, MediumType):
                    med.medium_type = mt.value
            if "refractive_index" in updates:
                med.refractive_index = max(1.0, _safe_float(
                    updates["refractive_index"], med.refractive_index))
            if "absorption_coeff" in updates:
                med.absorption_coeff = max(0.0, _safe_float(
                    updates["absorption_coeff"], med.absorption_coeff))
            if "scattering_coeff" in updates:
                med.scattering_coeff = max(0.0, _safe_float(
                    updates["scattering_coeff"], med.scattering_coeff))
            if "temperature_k" in updates:
                med.temperature_k = max(0.0, _safe_float(
                    updates["temperature_k"], med.temperature_k))
            if "density_kg_m3" in updates:
                med.density_kg_m3 = max(0.0, _safe_float(
                    updates["density_kg_m3"], med.density_kg_m3))
            if "active" in updates:
                med.active = bool(updates["active"])
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                med.metadata = dict(updates["metadata"])
            med.updated_at = _now()
            self._emit(
                OpticsEventKind.MEDIUM_UPDATED.value,
                f"Medium '{mid}' updated.",
                {"medium_id": mid},
            )
            self._refresh_stats()
            return (True, f"Medium '{mid}' updated.", med)

    def remove_medium(
        self, medium_id: str
    ) -> Tuple[bool, str, Optional[Medium]]:
        """Remove a medium from the system and return it."""
        with self._lock:
            mid = str(medium_id or "").strip()
            med = self._mediums.pop(mid, None)
            if med is None:
                return (False, f"Medium '{mid}' not found.", None)
            self._emit(
                OpticsEventKind.MEDIUM_REMOVED.value,
                f"Medium '{mid}' removed.",
                {"medium_id": mid},
            )
            self._refresh_stats()
            return (True, f"Medium '{mid}' removed.", med)

    # ------------------------------------------------------------------
    # Ray Management
    # ------------------------------------------------------------------

    def emit_ray(
        self,
        source_id: str = "",
        origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        direction: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        wavelength_nm: float = 550.0,
        intensity: float = 1.0,
        polarization: str = PolarizationType.UNPOLARIZED.value,
        medium_id: str = "air",
        parent_ray_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[LightRay]]:
        """Emit a new light ray from an origin or from a registered source.

        If ``source_id`` is provided and found, the origin, direction,
        wavelength, and intensity are taken from the source. Otherwise
        the explicit parameters are used.
        """
        with self._lock:
            self._ray_counter += 1
            rid = f"ray_{self._ray_counter:08d}"
            src = self._sources.get(str(source_id or "").strip())
            if src is not None:
                ray_origin = src.position
                ray_dir = _vec_normalize(src.direction)
                ray_wl = src.wavelength_nm
                ray_int = src.intensity
                ray_pol = src.polarization
                sid = src.source_id
            else:
                ray_origin = _to_vec3(origin)
                ray_dir = _vec_normalize(_to_vec3(direction, (0.0, 0.0, 1.0)))
                ray_wl = max(1.0, _safe_float(wavelength_nm, 550.0))
                ray_int = _clamp(_safe_float(intensity, 1.0), 0.0, 1.0)
                pol = _coerce_enum(PolarizationType, polarization,
                                    PolarizationType.UNPOLARIZED)
                ray_pol = (pol.value if isinstance(pol, PolarizationType)
                           else PolarizationType.UNPOLARIZED.value)
                sid = str(source_id or "").strip()
            if len(self._rays) >= self._config.max_rays:
                _evict_fifo_dict(self._rays, self._config.max_rays)
            ray = LightRay(
                ray_id=rid,
                source_id=sid,
                origin=ray_origin,
                direction=ray_dir,
                wavelength_nm=ray_wl,
                intensity=ray_int,
                initial_intensity=ray_int,
                polarization=ray_pol,
                medium_id=str(medium_id or "air"),
                status=RayStatus.ACTIVE.value,
                path=[ray_origin],
                age_s=0.0,
                parent_ray_id=str(parent_ray_id or ""),
                bounce_count=0,
                total_distance=0.0,
                metadata=metadata or {},
            )
            self._rays[rid] = ray
            self._stats.total_rays_traced += 1
            self._emit(
                OpticsEventKind.RAY_EMITTED.value,
                f"Ray '{rid}' emitted from '{sid}'.",
                {"ray_id": rid, "source_id": sid,
                 "wavelength_nm": ray_wl, "intensity": ray_int},
            )
            self._refresh_stats()
            return (True, f"Ray '{rid}' emitted.", ray)

    def list_rays(
        self,
        status: str = "",
        source_id: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[LightRay]:
        """List rays, optionally filtered by status and source."""
        with self._lock:
            status_val = ""
            if status:
                st = _coerce_enum(RayStatus, status, None)
                status_val = (st.value if isinstance(st, RayStatus)
                              else str(status))
            sid = str(source_id or "").strip()
            results: List[LightRay] = []
            for ray in self._rays.values():
                if status_val and ray.status != status_val:
                    continue
                if sid and ray.source_id != sid:
                    continue
                if active_only and ray.status != RayStatus.ACTIVE.value:
                    continue
                results.append(ray)
            return results[:max(0, int(limit))]

    def clear_rays(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Clear all traced rays from the system."""
        with self._lock:
            count = len(self._rays)
            self._rays.clear()
            self._emit(
                OpticsEventKind.RAYS_CLEARED.value,
                f"Cleared {count} rays.",
                {"count": count},
            )
            self._refresh_stats()
            return (True, f"Cleared {count} rays.", {"count": count})

    # ------------------------------------------------------------------
    # Ray Tracing and Physics
    # ------------------------------------------------------------------

    def trace_ray(
        self,
        origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        direction: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        wavelength_nm: float = 550.0,
        intensity: float = 1.0,
        max_bounces: int = 0,
        source_id: str = "",
        medium_id: str = "air",
    ) -> Tuple[bool, str, Optional[LightRay]]:
        """Trace a ray through the optical scene, bouncing off mirrors
        and refracting through lenses up to max_bounces times.

        The ray starts at origin and travels along direction. At each
        bounce, the ray interacts with the nearest mirror or lens in its
        path. Intensity is attenuated by reflectivity, Fresnel losses,
        and Beer-Lambert absorption through the medium.
        """
        with self._lock:
            bounces = max(0, int(max_bounces)) if max_bounces > 0 else self._config.max_bounces
            ray_origin = _to_vec3(origin)
            ray_dir = _vec_normalize(_to_vec3(direction, (0.0, 0.0, 1.0)))
            ray_wl = max(1.0, _safe_float(wavelength_nm, 550.0))
            ray_int = _clamp(_safe_float(intensity, 1.0), 0.0, 1.0)
            n_air = self._config.air_refractive_index
            path: List[Tuple[float, float, float]] = [ray_origin]
            current_pos = ray_origin
            current_dir = ray_dir
            current_int = ray_int
            bounce_count = 0
            total_dist = 0.0
            status = RayStatus.ACTIVE.value
            for _ in range(bounces):
                if current_int < 0.001:
                    status = RayStatus.ABSORBED.value
                    break
                # Find the nearest mirror intersection.
                best_t = self._config.ray_segment_length
                best_mirror: Optional[Mirror] = None
                for mir in self._mirrors.values():
                    if not mir.active:
                        continue
                    t = _ray_plane_intersection(
                        current_pos, current_dir, mir.position, mir.normal)
                    if t is not None and _EPSILON < t < best_t:
                        best_t = t
                        best_mirror = mir
                if best_mirror is not None:
                    hit_point = _vec_add(current_pos, _vec_scale(current_dir, best_t))
                    path.append(hit_point)
                    total_dist += best_t
                    seg_int = _beer_lambert(
                        current_int, 0.0, best_t)
                    reflected_int = seg_int * best_mirror.reflectivity
                    current_dir = _reflect_direction(current_dir, best_mirror.normal)
                    current_dir = _vec_normalize(current_dir)
                    current_pos = hit_point
                    current_int = reflected_int
                    bounce_count += 1
                    self._stats.total_reflections += 1
                    self._emit(
                        OpticsEventKind.RAY_REFLECTED.value,
                        f"Ray reflected off mirror '{best_mirror.mirror_id}'.",
                        {"mirror_id": best_mirror.mirror_id,
                         "bounce": bounce_count,
                         "intensity": current_int},
                    )
                    continue
                # Find the nearest lens intersection (simple refraction).
                best_lens: Optional[Lens] = None
                best_t_lens = self._config.ray_segment_length
                for lens in self._lenses.values():
                    if not lens.active:
                        continue
                    t = _ray_plane_intersection(
                        current_pos, current_dir, lens.position, lens.normal)
                    if t is not None and _EPSILON < t < best_t_lens:
                        best_t_lens = t
                        best_lens = lens
                if best_lens is not None:
                    hit_point = _vec_add(
                        current_pos, _vec_scale(current_dir, best_t_lens))
                    path.append(hit_point)
                    total_dist += best_t_lens
                    n1 = n_air
                    n2 = best_lens.refractive_index
                    refracted, tir = _refract_direction(
                        current_dir, best_lens.normal, n1, n2)
                    if self._config.enable_fresnel:
                        cos_i = abs(_vec_dot(current_dir, best_lens.normal))
                        r_coeff = _fresnel_reflectance(cos_i, n1, n2)
                        current_int = current_int * (1.0 - r_coeff)
                    if tir or refracted is None:
                        current_dir = _reflect_direction(
                            current_dir, best_lens.normal)
                    else:
                        current_dir = _vec_normalize(refracted)
                    current_pos = hit_point
                    bounce_count += 1
                    self._stats.total_refractions += 1
                    self._emit(
                        OpticsEventKind.RAY_REFRACTED.value,
                        f"Ray refracted through lens '{best_lens.lens_id}'.",
                        {"lens_id": best_lens.lens_id,
                         "bounce": bounce_count,
                         "intensity": current_int},
                    )
                    continue
                # No hit: ray escapes to the segment end.
                end_point = _vec_add(
                    current_pos, _vec_scale(current_dir, best_t))
                path.append(end_point)
                total_dist += best_t
                status = RayStatus.ESCAPED.value
                break
            else:
                status = RayStatus.TERMINATED.value
            self._ray_counter += 1
            rid = f"ray_{self._ray_counter:08d}"
            ray = LightRay(
                ray_id=rid,
                source_id=str(source_id or "").strip(),
                origin=ray_origin,
                direction=ray_dir,
                wavelength_nm=ray_wl,
                intensity=current_int,
                initial_intensity=ray_int,
                polarization=PolarizationType.UNPOLARIZED.value,
                medium_id=str(medium_id or "air"),
                status=status,
                path=path,
                age_s=0.0,
                parent_ray_id="",
                bounce_count=bounce_count,
                total_distance=total_dist,
                metadata={},
            )
            self._rays[rid] = ray
            self._stats.total_rays_traced += 1
            self._bounce_accum += bounce_count
            self._bounce_count += 1
            self._emit(
                OpticsEventKind.RAY_TRACED.value,
                f"Ray '{rid}' traced: {bounce_count} bounces, "
                f"status={status}.",
                {"ray_id": rid, "bounces": bounce_count,
                 "total_distance": total_dist, "status": status},
            )
            self._refresh_stats()
            return (True, f"Ray '{rid}' traced.", ray)

    def trace_ray_path(
        self,
        ray_id: str,
        max_bounces: int = 0,
    ) -> Tuple[bool, str, List[Tuple[float, float, float]]]:
        """Continue tracing an existing ray and return its extended path."""
        with self._lock:
            ray = self._rays.get(str(ray_id or "").strip())
            if ray is None:
                return (False, f"Ray '{ray_id}' not found.", [])
            if ray.status != RayStatus.ACTIVE.value:
                return (True, "Ray is no longer active.", list(ray.path))
            bounces = (max(0, int(max_bounces)) if max_bounces > 0
                       else self._config.max_bounces)
            current_pos = ray.path[-1] if ray.path else ray.origin
            current_dir = ray.direction
            current_int = ray.intensity
            new_path: List[Tuple[float, float, float]] = []
            for _ in range(bounces):
                if current_int < 0.001:
                    ray.status = RayStatus.ABSORBED.value
                    break
                best_t = self._config.ray_segment_length
                best_mirror: Optional[Mirror] = None
                for mir in self._mirrors.values():
                    if not mir.active:
                        continue
                    t = _ray_plane_intersection(
                        current_pos, current_dir, mir.position, mir.normal)
                    if t is not None and _EPSILON < t < best_t:
                        best_t = t
                        best_mirror = mir
                if best_mirror is not None:
                    hit = _vec_add(current_pos, _vec_scale(current_dir, best_t))
                    new_path.append(hit)
                    current_int = current_int * best_mirror.reflectivity
                    current_dir = _vec_normalize(
                        _reflect_direction(current_dir, best_mirror.normal))
                    current_pos = hit
                    ray.bounce_count += 1
                    self._stats.total_reflections += 1
                    continue
                end_point = _vec_add(
                    current_pos, _vec_scale(current_dir, best_t))
                new_path.append(end_point)
                ray.status = RayStatus.ESCAPED.value
                break
            else:
                ray.status = RayStatus.TERMINATED.value
            ray.path.extend(new_path)
            ray.intensity = current_int
            self._emit(
                OpticsEventKind.RAY_TRACED.value,
                f"Ray '{ray.ray_id}' path extended by {len(new_path)} points.",
                {"ray_id": ray.ray_id, "new_points": len(new_path)},
            )
            self._refresh_stats()
            return (True, f"Path extended by {len(new_path)} points.",
                    list(ray.path))

    def compute_reflection(
        self,
        incident: Tuple[float, float, float],
        normal: Tuple[float, float, float],
        reflectivity: float = 1.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the reflected direction and intensity for a ray.

        Uses the law of reflection: R = D - 2 * (D . N) * N.
        """
        with self._lock:
            inc = _vec_normalize(_to_vec3(incident, (0.0, 0.0, 1.0)))
            nrm = _vec_normalize(_to_vec3(normal, (0.0, 0.0, 1.0)))
            reflected = _reflect_direction(inc, nrm)
            reflected = _vec_normalize(reflected)
            angle_in = _angle_between(_vec_negate(inc), nrm)
            refl = _clamp(_safe_float(reflectivity, 1.0), 0.0, 1.0)
            self._stats.total_reflections += 1
            self._emit(
                OpticsEventKind.RAY_REFLECTED.value,
                "Reflection computed.",
                {"angle_in_rad": angle_in,
                 "angle_in_deg": math.degrees(angle_in),
                 "reflectivity": refl},
            )
            return (True, "Reflection computed.", {
                "incident": list(inc),
                "normal": list(nrm),
                "reflected": list(reflected),
                "angle_in_rad": angle_in,
                "angle_in_deg": math.degrees(angle_in),
                "reflectivity": refl,
            })

    def compute_refraction(
        self,
        incident: Tuple[float, float, float],
        normal: Tuple[float, float, float],
        n1: float = 1.0,
        n2: float = 1.5,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the refracted direction using Snell's law.

        Returns the refracted direction, the incident and refracted
        angles, whether total internal reflection occurred, and the
        Fresnel reflectance at the interface.
        """
        with self._lock:
            inc = _vec_normalize(_to_vec3(incident, (0.0, 0.0, 1.0)))
            nrm = _vec_normalize(_to_vec3(normal, (0.0, 0.0, 1.0)))
            idx1 = max(_EPSILON, _safe_float(n1, 1.0))
            idx2 = max(_EPSILON, _safe_float(n2, 1.5))
            refracted, tir = _refract_direction(inc, nrm, idx1, idx2)
            cos_i = abs(_vec_dot(inc, nrm))
            angle_i = math.acos(_clamp(cos_i, -1.0, 1.0))
            fresnel_r = _fresnel_reflectance(cos_i, idx1, idx2)
            self._stats.total_refractions += 1
            self._emit(
                OpticsEventKind.RAY_REFRACTED.value,
                "Refraction computed.",
                {"n1": idx1, "n2": idx2, "tir": tir,
                 "angle_in_rad": angle_i},
            )
            return (True, "Refraction computed.", {
                "incident": list(inc),
                "normal": list(nrm),
                "refracted": list(refracted) if refracted else None,
                "n1": idx1,
                "n2": idx2,
                "angle_in_rad": angle_i,
                "angle_in_deg": math.degrees(angle_i),
                "total_internal_reflection": tir,
                "fresnel_reflectance": fresnel_r,
                "fresnel_transmittance": 1.0 - fresnel_r,
            })

    def compute_dispersion(
        self,
        prism_id: str = "",
        wavelength_min_nm: float = 400.0,
        wavelength_max_nm: float = 700.0,
        num_samples: int = 7,
        cauchy_a: float = 0.0,
        cauchy_b: float = 0.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute chromatic dispersion through a prism.

        Uses Cauchy's equation n = A + B / lambda^2 to compute the
        refractive index for each wavelength sample, then calculates the
        deviation angle for each. Returns a list of (wavelength, n,
        deviation) tuples describing how the prism splits white light.
        """
        with self._lock:
            prism = self._prisms.get(str(prism_id or "").strip())
            if prism is None and not cauchy_a and not cauchy_b:
                return (False, f"Prism '{prism_id}' not found.", {})
            A = _safe_float(cauchy_a, 0.0) if cauchy_a else (
                prism.cauchy_a if prism else 1.50)
            B = _safe_float(cauchy_b, 0.0) if cauchy_b else (
                prism.cauchy_b if prism else 4500.0)
            apex = prism.apex_angle_rad if prism else math.radians(60.0)
            wmin = max(1.0, _safe_float(wavelength_min_nm, 400.0))
            wmax = max(wmin, _safe_float(wavelength_max_nm, 700.0))
            n_samples = max(2, min(100, int(num_samples)))
            n_air = self._config.air_refractive_index
            results: List[Dict[str, Any]] = []
            for i in range(n_samples):
                if n_samples > 1:
                    wl = wmin + (wmax - wmin) * i / (n_samples - 1)
                else:
                    wl = wmin
                n_prism = _cauchy_index(wl, A, B)
                # Deviation angle for minimum deviation through a prism:
                # sin((delta_min + A) / 2) = n * sin(A / 2)
                sin_half_apex = math.sin(apex / 2.0)
                arg = n_prism * sin_half_apex
                if abs(arg) <= 1.0:
                    delta_min = 2.0 * math.asin(arg) - apex
                else:
                    delta_min = math.pi - apex
                results.append({
                    "wavelength_nm": wl,
                    "refractive_index": n_prism,
                    "deviation_rad": delta_min,
                    "deviation_deg": math.degrees(delta_min),
                    "color_label": _wavelength_label(wl),
                })
            self._stats.total_dispersion_computations += 1
            self._emit(
                OpticsEventKind.DISPERSION_COMPUTED.value,
                f"Dispersion computed for {len(results)} wavelengths.",
                {"prism_id": prism_id if prism else "custom",
                 "sample_count": len(results)},
            )
            return (True, f"Dispersion computed for {len(results)} samples.", {
                "prism_id": prism_id if prism else "custom",
                "cauchy_a": A,
                "cauchy_b": B,
                "apex_angle_rad": apex,
                "apex_angle_deg": math.degrees(apex),
                "samples": results,
            })

    def compute_lens_image(
        self,
        lens_id: str,
        object_distance: float,
        object_height: float = 1.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the image formed by a lens using the thin lens equation.

        Given the object distance (do) and the lens focal length (f),
        computes the image distance (di) and magnification (m) using
        1/f = 1/do + 1/di and m = -di/do.
        """
        with self._lock:
            lens = self._lenses.get(str(lens_id or "").strip())
            if lens is None:
                return (False, f"Lens '{lens_id}' not found.", {})
            do = max(_EPSILON, _safe_float(object_distance, 0.1))
            ho = _safe_float(object_height, 1.0)
            f = lens.focal_length
            di, mag = _thin_lens_equation(do, f)
            hi = mag * ho
            if di == float("inf"):
                image_type = "at_infinity"
                real_image = False
            elif di > 0:
                image_type = "real"
                real_image = True
            else:
                image_type = "virtual"
                real_image = False
            self._stats.total_lens_images += 1
            self._emit(
                OpticsEventKind.LENS_IMAGE_COMPUTED.value,
                f"Lens image computed for '{lens_id}': {image_type}.",
                {"lens_id": lens_id, "di": di, "magnification": mag},
            )
            return (True, f"Image is {image_type}.", {
                "lens_id": lens_id,
                "focal_length": f,
                "object_distance": do,
                "object_height": ho,
                "image_distance": di,
                "image_height": hi,
                "magnification": mag,
                "image_type": image_type,
                "real_image": real_image,
            })

    def compute_focal_point(
        self,
        lens_id: str = "",
        mirror_id: str = "",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the focal point of a lens or mirror.

        For lenses, the focal length is stored directly. For mirrors,
        it is computed as f = R / 2. The focal point position is
        computed by offsetting from the element position along its
        normal by the focal length.
        """
        with self._lock:
            if lens_id:
                lens = self._lenses.get(str(lens_id or "").strip())
                if lens is None:
                    return (False, f"Lens '{lens_id}' not found.", {})
                f = lens.focal_length
                nrm = lens.normal
                pos = lens.position
                focal_pos = _vec_add(pos, _vec_scale(nrm, f))
                self._stats.total_focal_points += 1
                self._emit(
                    OpticsEventKind.FOCAL_POINT_COMPUTED.value,
                    f"Focal point computed for lens '{lens_id}'.",
                    {"lens_id": lens_id, "focal_length": f},
                )
                return (True, "Lens focal point computed.", {
                    "element_type": "lens",
                    "element_id": lens_id,
                    "focal_length": f,
                    "element_position": list(pos),
                    "element_normal": list(nrm),
                    "focal_point": list(focal_pos),
                })
            if mirror_id:
                mir = self._mirrors.get(str(mirror_id or "").strip())
                if mir is None:
                    return (False, f"Mirror '{mirror_id}' not found.", {})
                f = mir.focal_length
                nrm = mir.normal
                pos = mir.position
                focal_pos = _vec_add(pos, _vec_scale(nrm, f))
                self._stats.total_focal_points += 1
                self._emit(
                    OpticsEventKind.FOCAL_POINT_COMPUTED.value,
                    f"Focal point computed for mirror '{mirror_id}'.",
                    {"mirror_id": mirror_id, "focal_length": f},
                )
                return (True, "Mirror focal point computed.", {
                    "element_type": "mirror",
                    "element_id": mirror_id,
                    "focal_length": f,
                    "element_position": list(pos),
                    "element_normal": list(nrm),
                    "focal_point": list(focal_pos),
                })
            return (False, "Must provide lens_id or mirror_id.", {})

    def compute_critical_angle(
        self,
        n1: float,
        n2: float,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the critical angle for total internal reflection.

        The critical angle is defined only when n1 > n2 (light traveling
        from a denser medium to a rarer medium). Below this angle all
        light is transmitted; at or above it, total internal reflection
        occurs.
        """
        with self._lock:
            idx1 = max(_EPSILON, _safe_float(n1, 1.0))
            idx2 = max(_EPSILON, _safe_float(n2, 1.0))
            angle = _critical_angle(idx1, idx2)
            self._emit(
                OpticsEventKind.CRITICAL_ANGLE_COMPUTED.value,
                "Critical angle computed.",
                {"n1": idx1, "n2": idx2,
                 "critical_angle_rad": angle or 0.0},
            )
            return (True, "Critical angle computed.", {
                "n1": idx1,
                "n2": idx2,
                "critical_angle_rad": angle if angle is not None else 0.0,
                "critical_angle_deg": (math.degrees(angle)
                                       if angle is not None else 0.0),
                "tir_possible": angle is not None,
            })

    def compute_numerical_aperture(
        self,
        n_core: float,
        n_clad: float,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the numerical aperture of an optical fiber.

        NA = sqrt(n_core^2 - n_clad^2). The NA determines the
        light-gathering ability of the fiber.
        """
        with self._lock:
            nc = max(_EPSILON, _safe_float(n_core, 1.50))
            ncl = max(_EPSILON, _safe_float(n_clad, 1.48))
            na = _numerical_aperture(nc, ncl)
            return (True, "Numerical aperture computed.", {
                "n_core": nc,
                "n_cladding": ncl,
                "numerical_aperture": na,
            })

    def compute_acceptance_angle(
        self,
        n_core: float,
        n_clad: float,
        n_external: float = 1.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the acceptance angle of an optical fiber.

        theta_a = arcsin(NA / n_external). Light entering within this
        cone angle will be guided by total internal reflection.
        """
        with self._lock:
            nc = max(_EPSILON, _safe_float(n_core, 1.50))
            ncl = max(_EPSILON, _safe_float(n_clad, 1.48))
            ne = max(_EPSILON, _safe_float(n_external, 1.0))
            na = _numerical_aperture(nc, ncl)
            theta = _acceptance_angle(nc, ncl, ne)
            return (True, "Acceptance angle computed.", {
                "n_core": nc,
                "n_cladding": ncl,
                "n_external": ne,
                "numerical_aperture": na,
                "acceptance_angle_rad": theta,
                "acceptance_angle_deg": math.degrees(theta),
            })

    def compute_fresnel_coefficients(
        self,
        cos_theta: float,
        n1: float,
        n2: float,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute Fresnel reflection and transmission coefficients.

        Uses the Schlick approximation for unpolarized light. Returns
        the reflectance R and transmittance T = 1 - R.
        """
        with self._lock:
            cos_t = _clamp(_safe_float(cos_theta, 1.0), 0.0, 1.0)
            idx1 = max(_EPSILON, _safe_float(n1, 1.0))
            idx2 = max(_EPSILON, _safe_float(n2, 1.5))
            R = _fresnel_reflectance(cos_t, idx1, idx2)
            T = 1.0 - R
            self._emit(
                OpticsEventKind.FRESNEL_COMPUTED.value,
                "Fresnel coefficients computed.",
                {"n1": idx1, "n2": idx2, "R": R, "T": T},
            )
            return (True, "Fresnel coefficients computed.", {
                "cos_theta": cos_t,
                "n1": idx1,
                "n2": idx2,
                "reflectance": R,
                "transmittance": T,
            })

    def compute_beam_divergence(
        self,
        wavelength_nm: float,
        beam_waist_um: float,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the divergence angle of a Gaussian laser beam.

        theta = lambda / (pi * w0), where lambda is the wavelength
        and w0 is the beam waist radius.
        """
        with self._lock:
            wl = max(1.0, _safe_float(wavelength_nm, 550.0))
            w0 = max(_EPSILON, _safe_float(beam_waist_um, 1.0))
            theta = _gaussian_beam_divergence(wl, w0)
            return (True, "Beam divergence computed.", {
                "wavelength_nm": wl,
                "beam_waist_um": w0,
                "divergence_rad": theta,
                "divergence_mrad": theta * 1000.0,
                "divergence_deg": math.degrees(theta),
            })

    def wavelength_to_color(
        self,
        wavelength_nm: float,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Convert a wavelength in nanometers to an RGB color tuple.

        Maps the visible spectrum (380-750 nm) to approximate RGB
        values. Also returns a human-readable color band label.
        """
        with self._lock:
            wl = max(1.0, _safe_float(wavelength_nm, 550.0))
            rgb = _wavelength_to_rgb(wl)
            label = _wavelength_label(wl)
            energy_ev = _photon_energy(wl)
            return (True, f"Wavelength {wl:.1f} nm is {label}.", {
                "wavelength_nm": wl,
                "rgb": list(rgb),
                "color_label": label,
                "photon_energy_eV": energy_ev,
                "in_visible_range": (
                    _VISIBLE_MIN_NM <= wl <= _VISIBLE_MAX_NM
                ),
            })

    # ------------------------------------------------------------------
    # Measurement Methods
    # ------------------------------------------------------------------

    def measure_intensity(
        self,
        detector_id: str,
        source_id: str = "",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Measure light intensity at a detector position.

        Computes the inverse-square-law intensity from each active
        source (or a specific source) reaching the detector, applies
        Beer-Lambert absorption through the medium, and checks the
        detector wavelength sensitivity. Returns the total measured
        intensity and whether it exceeds the detector threshold.
        """
        with self._lock:
            det = self._detectors.get(str(detector_id or "").strip())
            if det is None:
                return (False, f"Detector '{detector_id}' not found.", {})
            total_intensity = self._config.ambient_light
            contributing: List[Dict[str, Any]] = []
            sources_to_check = (
                [self._sources[str(source_id).strip()]]
                if source_id and str(source_id).strip() in self._sources
                else list(self._sources.values())
            )
            for src in sources_to_check:
                if not src.active:
                    continue
                if not (det.wavelength_min_nm <= src.wavelength_nm
                        <= det.wavelength_max_nm):
                    continue
                distance = _vec_distance(src.position, det.position)
                if distance < _EPSILON:
                    distance = _EPSILON
                # Inverse square law.
                raw = src.intensity / (4.0 * math.pi * distance * distance)
                # Directional sensitivity: dot product of source
                # direction and the direction from source to detector.
                to_det = _vec_normalize(_vec_sub(det.position, src.position))
                dir_factor = _clamp(_vec_dot(src.direction, to_det), 0.0, 1.0)
                if src.source_type == LightSourceType.LASER.value:
                    dir_factor = max(dir_factor, 0.9)
                raw *= dir_factor
                # Apply detector sensitivity.
                measured = raw * det.sensitivity
                total_intensity += measured
                contributing.append({
                    "source_id": src.source_id,
                    "source_wavelength_nm": src.wavelength_nm,
                    "distance_m": distance,
                    "raw_intensity": raw,
                    "measured_intensity": measured,
                    "directional_factor": dir_factor,
                })
            total_intensity = _clamp(total_intensity, 0.0, 1.0)
            above_threshold = total_intensity >= det.threshold
            det.last_reading = total_intensity
            det.last_reading_time = _now()
            self._stats.total_measurements += 1
            self._emit(
                OpticsEventKind.INTENSITY_MEASURED.value,
                f"Intensity measured at '{detector_id}': "
                f"{total_intensity:.4f}.",
                {"detector_id": detector_id,
                 "intensity": total_intensity,
                 "above_threshold": above_threshold},
            )
            return (True, _intensity_label(total_intensity), {
                "detector_id": detector_id,
                "total_intensity": total_intensity,
                "intensity_label": _intensity_label(total_intensity),
                "above_threshold": above_threshold,
                "threshold": det.threshold,
                "contributing_sources": contributing,
                "ambient_light": self._config.ambient_light,
            })

    def measure_wavelength(
        self,
        detector_id: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Measure the dominant wavelength at a detector position.

        Finds the active source with the highest intensity contribution
        to the detector and returns its wavelength as the dominant
        wavelength.
        """
        with self._lock:
            det = self._detectors.get(str(detector_id or "").strip())
            if det is None:
                return (False, f"Detector '{detector_id}' not found.", {})
            best_wl = 0.0
            best_int = 0.0
            best_src = ""
            for src in self._sources.values():
                if not src.active:
                    continue
                if not (det.wavelength_min_nm <= src.wavelength_nm
                        <= det.wavelength_max_nm):
                    continue
                distance = _vec_distance(src.position, det.position)
                if distance < _EPSILON:
                    distance = _EPSILON
                raw = src.intensity / (4.0 * math.pi * distance * distance)
                if raw > best_int:
                    best_int = raw
                    best_wl = src.wavelength_nm
                    best_src = src.source_id
            if best_wl < _EPSILON:
                return (True, "No detectable light.", {
                    "detector_id": detector_id,
                    "dominant_wavelength_nm": 0.0,
                    "color_label": "none",
                    "source_id": "",
                })
            self._stats.total_measurements += 1
            self._emit(
                OpticsEventKind.WAVELENGTH_MEASURED.value,
                f"Wavelength measured at '{detector_id}': {best_wl:.1f} nm.",
                {"detector_id": detector_id,
                 "wavelength_nm": best_wl,
                 "source_id": best_src},
            )
            return (True, f"Dominant wavelength: {best_wl:.1f} nm.", {
                "detector_id": detector_id,
                "dominant_wavelength_nm": best_wl,
                "color_label": _wavelength_label(best_wl),
                "rgb": list(_wavelength_to_rgb(best_wl)),
                "source_id": best_src,
                "intensity": best_int,
            })

    def measure_spectrum(
        self,
        detector_id: str,
        num_samples: int = 37,
    ) -> Tuple[bool, str, Optional[Spectrum]]:
        """Measure the spectral distribution at a detector position.

        Samples the wavelength sensitivity range of the detector and
        computes the intensity contribution from all active sources at
        each wavelength. Returns a Spectrum dataclass.
        """
        with self._lock:
            det = self._detectors.get(str(detector_id or "").strip())
            if det is None:
                return (False, f"Detector '{detector_id}' not found.", None)
            n = max(2, min(200, int(num_samples)))
            wmin = det.wavelength_min_nm
            wmax = det.wavelength_max_nm
            wavelengths: List[float] = []
            intensities: List[float] = []
            for i in range(n):
                wl = wmin + (wmax - wmin) * i / (n - 1) if n > 1 else wmin
                total = self._config.ambient_light * 0.1
                for src in self._sources.values():
                    if not src.active:
                        continue
                    if not (wmin <= src.wavelength_nm <= wmax):
                        continue
                    distance = _vec_distance(src.position, det.position)
                    if distance < _EPSILON:
                        distance = _EPSILON
                    # Gaussian spectral peak centered at source wavelength.
                    sigma = 20.0
                    weight = math.exp(
                        -((wl - src.wavelength_nm) ** 2) / (2 * sigma * sigma)
                    )
                    raw = (src.intensity /
                           (4.0 * math.pi * distance * distance)) * weight
                    total += raw * det.sensitivity
                wavelengths.append(round(wl, 2))
                intensities.append(_clamp(total, 0.0, 1.0))
            peak_idx = max(range(len(intensities)), key=lambda k: intensities[k])
            peak_wl = wavelengths[peak_idx]
            half_max = intensities[peak_idx] / 2.0
            bw_lo = wavelengths[0]
            bw_hi = wavelengths[-1]
            for i, val in enumerate(intensities):
                if val >= half_max:
                    bw_lo = wavelengths[i]
                    break
            for i in range(len(intensities) - 1, -1, -1):
                if intensities[i] >= half_max:
                    bw_hi = wavelengths[i]
                    break
            bandwidth = bw_hi - bw_lo
            self._spectrum_counter += 1
            spec_id = f"spec_{self._spectrum_counter:08d}"
            spectrum = Spectrum(
                spectrum_id=spec_id,
                source_id=detector_id,
                wavelengths=wavelengths,
                intensities=intensities,
                peak_wavelength_nm=peak_wl,
                bandwidth_nm=bandwidth,
                metadata={"detector_id": detector_id},
            )
            self._spectra[spec_id] = spectrum
            self._stats.total_spectra += 1
            self._stats.total_measurements += 1
            self._emit(
                OpticsEventKind.SPECTRUM_MEASURED.value,
                f"Spectrum measured at '{detector_id}': "
                f"peak {peak_wl:.1f} nm.",
                {"detector_id": detector_id,
                 "peak_wavelength_nm": peak_wl,
                 "bandwidth_nm": bandwidth},
            )
            return (True, f"Peak at {peak_wl:.1f} nm.", spectrum)

    def get_light_map(
        self,
        bounds: Tuple[float, float, float, float] = (
            0.0, 0.0, 20.0, 20.0),
        resolution: int = 0,
        height: float = 0.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Generate a 2D light intensity map over a rectangular area.

        Samples the (x, z) plane at the given height and computes the
        total light intensity at each grid point from all active light
        sources. Returns a grid of intensity values for visualization
        and AI analysis.
        """
        with self._lock:
            min_x, min_z, max_x, max_z = bounds
            res = max(4, min(128, int(resolution))) if resolution > 0 else (
                self._config.light_map_resolution)
            n_x = res
            n_z = res
            if max_x <= min_x:
                max_x = min_x + 1.0
            if max_z <= min_z:
                max_z = min_z + 1.0
            dx = (max_x - min_x) / max(1, n_x - 1)
            dz = (max_z - min_z) / max(1, n_z - 1)
            grid: List[List[float]] = []
            active_sources = [s for s in self._sources.values() if s.active]
            for iz in range(n_z):
                z = min_z + iz * dz
                row: List[float] = []
                for ix in range(n_x):
                    x = min_x + ix * dx
                    pos = (x, height, z)
                    total = self._config.ambient_light
                    for src in active_sources:
                        dist = _vec_distance(src.position, pos)
                        if dist < _EPSILON:
                            dist = _EPSILON
                        raw = src.intensity / (4.0 * math.pi * dist * dist)
                        to_pos = _vec_normalize(_vec_sub(pos, src.position))
                        dir_factor = _clamp(
                            _vec_dot(src.direction, to_pos), 0.0, 1.0)
                        if src.source_type == LightSourceType.LASER.value:
                            dir_factor = max(dir_factor, 0.9)
                        total += raw * dir_factor
                    row.append(_clamp(total, 0.0, 1.0))
                grid.append(row)
            self._stats.total_light_maps += 1
            self._emit(
                OpticsEventKind.LIGHT_MAP_GENERATED.value,
                f"Light map generated: {n_x}x{n_z} grid.",
                {"resolution": [n_x, n_z], "bounds": list(bounds)},
            )
            return (True, f"Light map: {n_x}x{n_z} grid.", {
                "bounds": list(bounds),
                "resolution": [n_x, n_z],
                "height": height,
                "grid": grid,
                "active_source_count": len(active_sources),
            })

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def ai_predict_light_path(
        self,
        origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        direction: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        wavelength_nm: float = 550.0,
        max_bounces: int = 0,
        medium_id: str = "air",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Predict the full path of a light ray through the optical scene.

        Traces a ray from the given origin along the given direction and
        returns a structured prediction containing the path points, the
        expected intensity at each segment, the elements the ray will
        interact with, and a confidence estimate for the prediction. The
        confidence is derived from the number of bounces, the residual
        intensity, and whether the ray terminated cleanly.
        """
        with self._lock:
            ok, msg, ray = self.trace_ray(
                origin=origin,
                direction=direction,
                wavelength_nm=wavelength_nm,
                intensity=1.0,
                max_bounces=max_bounces,
                source_id="",
                medium_id=medium_id,
            )
            if not ok or ray is None:
                self._stats.total_ai_assessments += 1
                self._emit(
                    OpticsEventKind.AI_ASSESSMENT.value,
                    "Light path prediction failed.",
                    {"origin": list(origin),
                     "direction": list(direction),
                     "success": False},
                )
                return (False, msg, {
                    "success": False,
                    "path": [],
                    "interactions": [],
                    "predicted_intensity": 0.0,
                    "confidence": 0.0,
                    "wavelength_nm": wavelength_nm,
                })
            path = list(ray.path)
            interactions: List[Dict[str, Any]] = []
            if ray.bounce_count > 0 and len(path) >= 2:
                for idx in range(1, len(path)):
                    seg_start = path[idx - 1]
                    seg_end = path[idx]
                    seg_len = _vec_distance(seg_start, seg_end)
                    nearest_mirror_id = ""
                    nearest_dist = float("inf")
                    for mir in self._mirrors.values():
                        if not mir.active:
                            continue
                        d = _vec_distance(seg_end, mir.position)
                        if d < nearest_dist:
                            nearest_dist = d
                            nearest_mirror_id = mir.mirror_id
                    nearest_lens_id = ""
                    nearest_lens_dist = float("inf")
                    for lens in self._lenses.values():
                        if not lens.active:
                            continue
                        d = _vec_distance(seg_end, lens.position)
                        if d < nearest_lens_dist:
                            nearest_lens_dist = d
                            nearest_lens_id = lens.lens_id
                    element_type = "free_space"
                    element_id = ""
                    if nearest_dist < 0.5 and nearest_dist < nearest_lens_dist:
                        element_type = "mirror"
                        element_id = nearest_mirror_id
                    elif nearest_lens_dist < 0.5:
                        element_type = "lens"
                        element_id = nearest_lens_id
                    interactions.append({
                        "segment_index": idx,
                        "start": list(seg_start),
                        "end": list(seg_end),
                        "length": seg_len,
                        "element_type": element_type,
                        "element_id": element_id,
                    })
            residual = ray.intensity
            if ray.initial_intensity > _EPSILON:
                loss_ratio = 1.0 - (residual / ray.initial_intensity)
            else:
                loss_ratio = 1.0
            bounce_penalty = min(1.0, ray.bounce_count / 20.0)
            confidence = _clamp(
                (1.0 - bounce_penalty) * (1.0 - 0.5 * loss_ratio), 0.0, 1.0)
            if ray.status == RayStatus.ESCAPED.value:
                confidence = _clamp(confidence + 0.05, 0.0, 1.0)
            elif ray.status == RayStatus.ABSORBED.value:
                confidence = _clamp(confidence - 0.1, 0.0, 1.0)
            self._stats.total_ai_assessments += 1
            self._emit(
                OpticsEventKind.AI_ASSESSMENT.value,
                f"Light path predicted: {len(path)} points, "
                f"confidence={confidence:.2f}.",
                {"path_points": len(path),
                 "bounces": ray.bounce_count,
                 "confidence": confidence,
                 "residual_intensity": residual,
                 "status": ray.status},
            )
            self._refresh_stats()
            return (True, f"Path predicted with {confidence:.0%} confidence.", {
                "success": True,
                "ray_id": ray.ray_id,
                "path": [list(p) for p in path],
                "interactions": interactions,
                "bounce_count": ray.bounce_count,
                "predicted_intensity": residual,
                "initial_intensity": ray.initial_intensity,
                "loss_ratio": loss_ratio,
                "status": ray.status,
                "wavelength_nm": wavelength_nm,
                "total_distance": ray.total_distance,
                "confidence": confidence,
                "confidence_label": _confidence_label(confidence),
            })

    def ai_optimize_lens_configuration(
        self,
        target_wavelength_nm: float = 550.0,
        desired_focal_length: float = 0.1,
        element_count: int = 1,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Optimize a lens configuration for a target focal length.

        Evaluates the registered lenses and proposes an arrangement that
        best matches the desired focal length at the target wavelength.
        For multi-element configurations, the system computes the
        effective focal length of combined lenses using the power formula
        1/f_eff = 1/f1 + 1/f2 + ... and selects the combination with the
        smallest deviation from the target.
        """
        with self._lock:
            target_wl = max(1.0, _safe_float(target_wavelength_nm, 550.0))
            target_f = _safe_float(desired_focal_length, 0.1)
            n_elements = max(1, min(5, int(element_count)))
            candidates = [l for l in self._lenses.values() if l.active]
            if not candidates:
                self._stats.total_ai_assessments += 1
                self._emit(
                    OpticsEventKind.AI_ASSESSMENT.value,
                    "Lens optimization failed: no active lenses.",
                    {"target_focal_length": target_f,
                     "success": False},
                )
                return (False, "No active lenses available.", {
                    "success": False,
                    "target_focal_length": target_f,
                    "target_wavelength_nm": target_wl,
                })
            scored: List[Tuple[float, List[Lens], float]] = []
            if n_elements == 1:
                for lens in candidates:
                    f = lens.focal_length
                    if abs(f) < _EPSILON:
                        continue
                    deviation = abs(f - target_f)
                    scored.append((deviation, [lens], f))
            else:
                from itertools import combinations
                for r in range(1, n_elements + 1):
                    for combo in combinations(candidates, r):
                        power = 0.0
                        valid = True
                        for lens in combo:
                            f = lens.focal_length
                            if abs(f) < _EPSILON:
                                valid = False
                                break
                            power += 1.0 / f
                        if not valid or abs(power) < _EPSILON:
                            continue
                        f_eff = 1.0 / power
                        deviation = abs(f_eff - target_f)
                        scored.append((deviation, list(combo), f_eff))
            if not scored:
                self._stats.total_ai_assessments += 1
                self._emit(
                    OpticsEventKind.AI_ASSESSMENT.value,
                    "Lens optimization failed: no valid combination.",
                    {"target_focal_length": target_f},
                )
                return (False, "No valid lens combination found.", {
                    "success": False,
                    "target_focal_length": target_f,
                    "target_wavelength_nm": target_wl,
                })
            scored.sort(key=lambda item: item[0])
            best_dev, best_combo, best_f = scored[0]
            match_quality = _clamp(1.0 - (best_dev / max(_EPSILON, abs(target_f))), 0.0, 1.0)
            color = _wavelength_to_rgb(target_wl)
            color_label = _wavelength_label(target_wl)
            photon_e = _photon_energy(target_wl)
            recommendation = "use_single_element"
            if len(best_combo) > 1:
                recommendation = "combine_elements"
            if best_dev < 0.001:
                advice = "near_exact_match"
            elif best_dev < 0.01:
                advice = "good_match"
            elif best_dev < 0.05:
                advice = "acceptable_match"
            else:
                advice = "poor_match_consider_custom_lens"
            self._stats.total_ai_assessments += 1
            self._emit(
                OpticsEventKind.AI_ASSESSMENT.value,
                f"Lens configuration optimized: {len(best_combo)} elements, "
                f"f={best_f:.4f}, deviation={best_dev:.4f}.",
                {"element_count": len(best_combo),
                 "effective_focal_length": best_f,
                 "deviation": best_dev,
                 "match_quality": match_quality},
            )
            self._refresh_stats()
            return (True, f"Optimal configuration: {len(best_combo)} lens(es).", {
                "success": True,
                "target_focal_length": target_f,
                "target_wavelength_nm": target_wl,
                "wavelength_color": list(color),
                "wavelength_label": color_label,
                "photon_energy_ev": photon_e,
                "selected_lenses": [l.lens_id for l in best_combo],
                "lens_details": [l.to_dict() for l in best_combo],
                "effective_focal_length": best_f,
                "deviation": best_dev,
                "match_quality": match_quality,
                "match_quality_label": _confidence_label(match_quality),
                "recommendation": recommendation,
                "advice": advice,
                "alternatives": [
                    {"lenses": [l.lens_id for l in combo],
                     "focal_length": f_eff,
                     "deviation": dev}
                    for dev, combo, f_eff in scored[1:4]
                ],
            })

    def ai_assess_visibility(
        self,
        observer_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        target_position: Tuple[float, float, float] = (10.0, 0.0, 0.0),
        observer_direction: Tuple[float, float, float] = (1.0, 0.0, 0.0),
        wavelength_nm: float = 550.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Assess the visibility of a target from an observer position.

        Computes the light intensity at the target position, the angle
        between the observer's facing direction and the target, the
        distance, and any occluding mirrors in the line of sight. Returns
        a visibility score from 0 (invisible) to 1 (clearly visible)
        along with a human-readable label.
        """
        with self._lock:
            obs_pos = _to_vec3(observer_position)
            tgt_pos = _to_vec3(target_position, (10.0, 0.0, 0.0))
            obs_dir = _vec_normalize(_to_vec3(observer_direction, (1.0, 0.0, 0.0)))
            wl = max(1.0, _safe_float(wavelength_nm, 550.0))
            distance = _vec_distance(obs_pos, tgt_pos)
            if distance < _EPSILON:
                self._stats.total_ai_assessments += 1
                self._emit(
                    OpticsEventKind.AI_ASSESSMENT.value,
                    "Visibility assessment: observer and target coincide.",
                    {"distance": 0.0, "visibility": 1.0},
                )
                return (True, "Observer and target are at the same point.", {
                    "success": True,
                    "distance": 0.0,
                    "visibility_score": 1.0,
                    "visibility_label": "coincident",
                    "wavelength_nm": wl,
                })
            to_target = _vec_normalize(_vec_sub(tgt_pos, obs_pos))
            cos_angle = _clamp(_vec_dot(obs_dir, to_target), -1.0, 1.0)
            view_angle = math.degrees(math.acos(cos_angle))
            in_front = cos_angle > 0.0
            active_sources = [s for s in self._sources.values() if s.active]
            target_intensity = self._config.ambient_light
            contributing: List[Dict[str, Any]] = []
            for src in active_sources:
                dist_src = _vec_distance(src.position, tgt_pos)
                if dist_src < _EPSILON:
                    dist_src = _EPSILON
                raw = src.intensity / (4.0 * math.pi * dist_src * dist_src)
                to_target_from_src = _vec_normalize(_vec_sub(tgt_pos, src.position))
                dir_factor = _clamp(_vec_dot(src.direction, to_target_from_src), 0.0, 1.0)
                if src.source_type == LightSourceType.LASER.value:
                    dir_factor = max(dir_factor, 0.9)
                contribution = raw * dir_factor
                target_intensity += contribution
                if contribution > 0.001:
                    contributing.append({
                        "source_id": src.source_id,
                        "contribution": contribution,
                        "distance": dist_src,
                    })
            target_intensity = _clamp(target_intensity, 0.0, 1.0)
            occluders: List[str] = []
            for mir in self._mirrors.values():
                if not mir.active:
                    continue
                t = _ray_plane_intersection(obs_pos, to_target, mir.position, mir.normal)
                if t is not None and _EPSILON < t < distance:
                    occluders.append(mir.mirror_id)
            occluded = len(occluders) > 0
            distance_penalty = _clamp(1.0 - (distance / 50.0), 0.0, 1.0)
            angle_penalty = _clamp(cos_angle, 0.0, 1.0) if in_front else 0.0
            occlusion_penalty = 0.0 if occluded else 1.0
            light_factor = _clamp(target_intensity, 0.0, 1.0)
            visibility = _clamp(
                distance_penalty * 0.3
                + angle_penalty * 0.35
                + occlusion_penalty * 0.2
                + light_factor * 0.15,
                0.0, 1.0,
            )
            if occluded:
                visibility = _clamp(visibility * 0.2, 0.0, 1.0)
            if not in_front:
                visibility = _clamp(visibility * 0.1, 0.0, 1.0)
            self._stats.total_ai_assessments += 1
            self._emit(
                OpticsEventKind.AI_ASSESSMENT.value,
                f"Visibility assessed: score={visibility:.2f}, "
                f"distance={distance:.2f}m, occluded={occluded}.",
                {"distance": distance,
                 "view_angle_deg": view_angle,
                 "target_intensity": target_intensity,
                 "occluded": occluded,
                 "occluder_count": len(occluders),
                 "visibility": visibility},
            )
            self._refresh_stats()
            return (True, f"Visibility score: {visibility:.0%}.", {
                "success": True,
                "observer_position": list(obs_pos),
                "target_position": list(tgt_pos),
                "distance": distance,
                "view_angle_deg": view_angle,
                "in_field_of_view": in_front,
                "target_intensity": target_intensity,
                "ambient_light": self._config.ambient_light,
                "active_source_count": len(active_sources),
                "contributing_sources": contributing,
                "occluded": occluded,
                "occluders": occluders,
                "occluder_count": len(occluders),
                "visibility_score": visibility,
                "visibility_label": _visibility_label(visibility),
                "wavelength_nm": wl,
                "wavelength_color": list(_wavelength_to_rgb(wl)),
                "intensity_label": _intensity_label(target_intensity),
                "distance_penalty": distance_penalty,
                "angle_penalty": angle_penalty,
                "occlusion_penalty": occlusion_penalty,
                "light_factor": light_factor,
            })

    # ------------------------------------------------------------------
    # System Methods
    # ------------------------------------------------------------------

    def get_config(self) -> Dict[str, Any]:
        """Return the current runtime configuration as a plain dict."""
        with self._lock:
            return self._config.to_dict()

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, Dict[str, Any]]:
        """Update one or more configuration fields.

        Only fields that are actually provided in ``kwargs`` are updated;
        all other fields keep their current values. Unknown keys are
        collected and reported back as ignored so callers can detect
        typos without breaking the update.
        """
        with self._lock:
            if not kwargs:
                return (False, "No configuration fields provided.", {})
            current = self._config.to_dict()
            updated_fields: Dict[str, Any] = {}
            ignored: List[str] = []
            field_map = {
                "max_sources", "max_mirrors", "max_lenses", "max_prisms",
                "max_fibers", "max_detectors", "max_mediums", "max_rays",
                "max_events", "max_spectra", "time_step", "ambient_light",
                "air_refractive_index", "max_bounces", "ray_segment_length",
                "light_map_resolution", "enable_polarization",
                "enable_interference", "enable_absorption",
                "enable_scattering", "enable_dispersion",
                "enable_fresnel", "enable_beam_divergence",
                "verbose", "metadata",
            }
            for key, value in kwargs.items():
                if key not in field_map:
                    ignored.append(key)
                    continue
                if key in ("max_sources", "max_mirrors", "max_lenses",
                           "max_prisms", "max_fibers", "max_detectors",
                           "max_mediums", "max_rays", "max_events",
                           "max_spectra", "max_bounces",
                           "light_map_resolution"):
                    setattr(self._config, key, max(1, _safe_int(value, getattr(self._config, key))))
                elif key in ("time_step", "ambient_light",
                             "air_refractive_index",
                             "ray_segment_length"):
                    setattr(self._config, key, _safe_float(value, getattr(self._config, key)))
                elif key in ("enable_polarization", "enable_interference",
                             "enable_absorption", "enable_scattering",
                             "enable_dispersion", "enable_fresnel",
                             "enable_beam_divergence", "verbose"):
                    setattr(self._config, key, bool(value))
                elif key == "metadata":
                    if isinstance(value, dict):
                        self._config.metadata.update(value)
                else:
                    setattr(self._config, key, value)
                updated_fields[key] = getattr(self._config, key)
            self._emit(
                OpticsEventKind.CONFIG_UPDATED.value,
                f"Configuration updated: {len(updated_fields)} field(s).",
                {"updated": updated_fields, "ignored": ignored},
            )
            return (True, f"Updated {len(updated_fields)} field(s).", {
                "updated": updated_fields,
                "ignored": ignored,
                "config": self._config.to_dict(),
                "previous": {k: current.get(k) for k in updated_fields},
            })

    def get_status(self) -> Dict[str, Any]:
        """Return a high-level status summary of the system."""
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "seeded": self._seeded,
                "tick_count": self._tick_count,
                "simulation_time_s": self._simulation_time,
                "total_sources": len(self._sources),
                "active_sources": sum(1 for s in self._sources.values() if s.active),
                "total_mirrors": len(self._mirrors),
                "total_lenses": len(self._lenses),
                "total_prisms": len(self._prisms),
                "total_fibers": len(self._fibers),
                "total_detectors": len(self._detectors),
                "total_mediums": len(self._mediums),
                "active_rays": sum(1 for r in self._rays.values()
                                   if r.status == RayStatus.ACTIVE.value),
                "total_rays_traced": self._stats.total_rays_traced,
                "event_count": len(self._events),
                "ambient_light": self._config.ambient_light,
                "air_refractive_index": self._config.air_refractive_index,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Return the cached statistics roll-up."""
        with self._lock:
            self._refresh_stats()
            return self._stats.to_dict()

    def get_snapshot(self) -> Dict[str, Any]:
        """Capture a full point-in-time snapshot of the system state."""
        with self._lock:
            self._refresh_stats()
            recent_events = self._events[-self._config.max_events:]
            snapshot = OpticsSnapshot(
                timestamp=_now(),
                sources=[s.to_dict() for s in self._sources.values()],
                mirrors=[m.to_dict() for m in self._mirrors.values()],
                lenses=[l.to_dict() for l in self._lenses.values()],
                prisms=[p.to_dict() for p in self._prisms.values()],
                fibers=[f.to_dict() for f in self._fibers.values()],
                detectors=[d.to_dict() for d in self._detectors.values()],
                mediums=[m.to_dict() for m in self._mediums.values()],
                rays=[r.to_dict() for r in list(self._rays.values())[-200:]],
                events=[e.to_dict() for e in recent_events[-200:]],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
            )
            self._emit(
                OpticsEventKind.TICK.value,
                "Snapshot captured.",
                {"sources": len(snapshot.sources),
                 "rays": len(snapshot.rays)},
            )
            return snapshot.to_dict()

    def list_events(
        self,
        event_type: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """List audit events with optional filtering and pagination.

        Filters by event type when provided, then applies offset and
        limit for pagination. Returns the matching events as dicts in
        chronological order (oldest first).
        """
        with self._lock:
            et = str(event_type or "").strip().lower()
            lim = max(0, min(int(limit), len(self._events))) if limit > 0 else len(self._events)
            off = max(0, int(offset))
            matches: List[OpticsEvent] = []
            for event in self._events:
                if et and event.event_type.lower() != et:
                    continue
                matches.append(event)
            total = len(matches)
            page = matches[off:off + lim] if lim > 0 else matches[off:]
            return (True, f"{len(page)} event(s).", {
                "events": [e.to_dict() for e in page],
                "total": total,
                "limit": lim,
                "offset": off,
                "filtered_by": et or "all",
            })

    def tick(
        self,
        delta_time: float = 0.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Advance the simulation by one time step.

        Advances the internal simulation clock, ages all active rays,
        and recomputes statistics. The delta_time overrides the default
        time step when provided; otherwise the configured time step is
        used.
        """
        with self._lock:
            dt = _safe_float(delta_time, self._config.time_step)
            if dt <= 0.0:
                dt = self._config.time_step
            self._tick_count += 1
            self._simulation_time += dt
            aged_count = 0
            terminated: List[str] = []
            for rid, ray in list(self._rays.items()):
                if ray.status != RayStatus.ACTIVE.value:
                    continue
                ray.age_s += dt
                aged_count += 1
                if ray.age_s > 10.0:
                    ray.status = RayStatus.TERMINATED.value
                    terminated.append(rid)
            if terminated:
                self._emit(
                    OpticsEventKind.RAY_TERMINATED.value,
                    f"{len(terminated)} ray(s) terminated by age limit.",
                    {"ray_ids": terminated, "age_limit_s": 10.0},
                )
            self._refresh_stats()
            self._emit(
                OpticsEventKind.TICK.value,
                f"Tick {self._tick_count}: dt={dt:.4f}s, "
                f"t={self._simulation_time:.4f}s.",
                {"tick": self._tick_count,
                 "delta_time": dt,
                 "simulation_time": self._simulation_time,
                 "aged_rays": aged_count,
                 "terminated_rays": len(terminated)},
            )
            return (True, f"Tick {self._tick_count} completed.", {
                "tick": self._tick_count,
                "delta_time": dt,
                "simulation_time": self._simulation_time,
                "aged_rays": aged_count,
                "terminated_rays": len(terminated),
                "active_rays": sum(1 for r in self._rays.values()
                                   if r.status == RayStatus.ACTIVE.value),
                "stats": self._stats.to_dict(),
            })

    def get_visualization_data(
        self,
        include_rays: bool = True,
        include_light_map: bool = False,
        bounds: Tuple[float, float, float, float] = (0.0, 0.0, 20.0, 20.0),
        height: float = 0.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Assemble a visualization payload for the renderer.

        Collects all active optical elements, optionally the traced rays,
        and optionally a light map into a single payload suitable for a
        frontend renderer or debug overlay.
        """
        with self._lock:
            sources = [s.to_dict() for s in self._sources.values() if s.active]
            mirrors = [m.to_dict() for m in self._mirrors.values() if m.active]
            lenses = [l.to_dict() for l in self._lenses.values() if l.active]
            prisms = [p.to_dict() for p in self._prisms.values() if p.active]
            fibers = [f.to_dict() for f in self._fibers.values() if f.active]
            detectors = [d.to_dict() for d in self._detectors.values() if d.active]
            mediums = [m.to_dict() for m in self._mediums.values() if m.active]
            rays: List[Dict[str, Any]] = []
            if include_rays:
                for ray in list(self._rays.values())[-500:]:
                    rays.append({
                        "ray_id": ray.ray_id,
                        "path": [list(p) for p in ray.path],
                        "wavelength_nm": ray.wavelength_nm,
                        "intensity": ray.intensity,
                        "status": ray.status,
                        "color": list(_wavelength_to_rgb(ray.wavelength_nm)),
                        "bounce_count": ray.bounce_count,
                    })
            light_map: Optional[Dict[str, Any]] = None
            if include_light_map:
                ok_lm, msg_lm, lm = self.get_light_map(bounds=bounds, height=height)
                if ok_lm:
                    light_map = lm
            self._refresh_stats()
            return (True, "Visualization data assembled.", {
                "timestamp": _now(),
                "tick_count": self._tick_count,
                "simulation_time_s": self._simulation_time,
                "sources": sources,
                "mirrors": mirrors,
                "lenses": lenses,
                "prisms": prisms,
                "fibers": fibers,
                "detectors": detectors,
                "mediums": mediums,
                "rays": rays,
                "light_map": light_map,
                "stats": self._stats.to_dict(),
                "config": self._config.to_dict(),
                "counts": {
                    "sources": len(sources),
                    "mirrors": len(mirrors),
                    "lenses": len(lenses),
                    "prisms": len(prisms),
                    "fibers": len(fibers),
                    "detectors": len(detectors),
                    "mediums": len(mediums),
                    "rays": len(rays),
                },
            })

    def reset(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Reset the system to its initial seeded state.

        Clears all registered entities, rays, spectra, and events, then
        re-seeds the default dataset. Configuration is preserved so
        runtime tuning survives a reset.
        """
        with self._lock:
            prev_counts = {
                "sources": len(self._sources),
                "mirrors": len(self._mirrors),
                "lenses": len(self._lenses),
                "prisms": len(self._prisms),
                "fibers": len(self._fibers),
                "detectors": len(self._detectors),
                "mediums": len(self._mediums),
                "rays": len(self._rays),
                "spectra": len(self._spectra),
                "events": len(self._events),
            }
            self._sources.clear()
            self._mirrors.clear()
            self._lenses.clear()
            self._prisms.clear()
            self._fibers.clear()
            self._detectors.clear()
            self._mediums.clear()
            self._rays.clear()
            self._spectra.clear()
            self._events.clear()
            self._tick_count = 0
            self._event_counter = 0
            self._ray_counter = 0
            self._spectrum_counter = 0
            self._simulation_time = 0.0
            self._bounce_accum = 0.0
            self._bounce_count = 0
            self._stats = OpticsStats()
            self._seeded = False
            self._seed_data()
            self._emit(
                OpticsEventKind.SYSTEM_RESET.value,
                "System reset to seeded state.",
                {"previous_counts": prev_counts},
            )
            self._refresh_stats()
            return (True, "System reset complete.", {
                "previous_counts": prev_counts,
                "current_counts": {
                    "sources": len(self._sources),
                    "mirrors": len(self._mirrors),
                    "lenses": len(self._lenses),
                    "prisms": len(self._prisms),
                    "fibers": len(self._fibers),
                    "detectors": len(self._detectors),
                    "mediums": len(self._mediums),
                },
                "tick_count": self._tick_count,
                "simulation_time_s": self._simulation_time,
            })


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------


def get_optics_system() -> _OpticsSystem:
    """Return the shared :class:`_OpticsSystem` singleton instance.

    This is the public entry point for the optics subsystem. The
    singleton is created on first call using double-checked locking,
    and the default seed data is populated automatically.
    """
    system = _OpticsSystem.get_instance()
    system.initialize()
    return system
