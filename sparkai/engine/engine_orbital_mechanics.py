"""Engine orbital mechanics system: N-body gravity and orbital trajectory simulation.

Simulates celestial body dynamics, Keplerian orbits, satellite maneuvers,
Hohmann transfers, and trajectory prediction for space-based gameplay
including orbital combat, space exploration, and station management.

Core physics implemented:
  - Newton's law of universal gravitation
  - Kepler's three laws of planetary motion
  - Vis-viva equation for orbital velocity
  - Escape and circular orbit velocity
  - Hohmann transfer orbits
  - Sphere of influence (Laplace)
  - Specific orbital energy
  - N-body numerical integration (velocity-Verlet)
  - Tidal forces and delta-v budgeting

The module exposes a thread-safe singleton accessible through the
``get_orbital_mechanics_system`` factory function.
"""
from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Physical Constants (SI units)
# ---------------------------------------------------------------------------

GRAVITATIONAL_CONSTANT = 6.674e-11  # N*m^2/kg^2
AU = 1.496e11  # Astronomical unit in meters
SOLAR_MASS = 1.989e30  # kg
EARTH_MASS = 5.972e24  # kg
EARTH_RADIUS = 6.371e6  # m
SPEED_OF_LIGHT = 2.998e8  # m/s
JULIAN_DAY = 86400.0  # seconds
STANDARD_GRAVITY = 9.80665  # m/s^2

# Vector type alias: (x, y, z) in meters
Vec3 = Tuple[float, float, float]


# ---------------------------------------------------------------------------
# Vector helper functions
# ---------------------------------------------------------------------------

def _vadd(a: Vec3, b: Vec3) -> Vec3:
    """Add two 3D vectors."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vsub(a: Vec3, b: Vec3) -> Vec3:
    """Subtract vector b from vector a."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vscale(a: Vec3, s: float) -> Vec3:
    """Scale a 3D vector by a scalar."""
    return (a[0] * s, a[1] * s, a[2] * s)


def _vdot(a: Vec3, b: Vec3) -> float:
    """Dot product of two 3D vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vcross(a: Vec3, b: Vec3) -> Vec3:
    """Cross product of two 3D vectors."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vlen(a: Vec3) -> float:
    """Euclidean length of a 3D vector."""
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _vnormalize(a: Vec3) -> Vec3:
    """Return the unit vector of a, or zero vector if a is near zero length."""
    n = _vlen(a)
    if n < 1e-12:
        return (0.0, 0.0, 0.0)
    return (a[0] / n, a[1] / n, a[2] / n)


def _vdist(a: Vec3, b: Vec3) -> float:
    """Euclidean distance between two points in 3D space."""
    return _vlen(_vsub(a, b))


def _vlerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    """Linear interpolation between two 3D vectors."""
    t = max(0.0, min(1.0, t))
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _v_to_list(a: Vec3) -> List[float]:
    """Convert a 3D vector tuple to a list."""
    return [a[0], a[1], a[2]]


def _list_to_v(a: Sequence[float]) -> Vec3:
    """Convert a sequence of floats to a 3D vector tuple."""
    if a is None:
        return (0.0, 0.0, 0.0)
    if len(a) >= 3:
        return (float(a[0]), float(a[1]), float(a[2]))
    if len(a) == 2:
        return (float(a[0]), float(a[1]), 0.0)
    if len(a) == 1:
        return (float(a[0]), 0.0, 0.0)
    return (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def _now() -> float:
    """Return the current wall-clock time in seconds since the epoch."""
    return time.time()


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value to the range [lo, hi]."""
    return max(lo, min(hi, value))


def _gen_id(prefix: str, provided: Optional[str] = None) -> str:
    """Generate an identifier with the given prefix, or use the provided id."""
    if provided:
        return str(provided)
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _dataclass_to_dict(obj: Any) -> Any:
    """Recursively convert a dataclass instance to a dictionary."""
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            result[k] = _dataclass_to_dict(v)
        return result
    if isinstance(obj, list):
        return [_dataclass_to_dict(i) for i in obj]
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {kk: _dataclass_to_dict(vv) for kk, vv in obj.items()}
    if isinstance(obj, Enum):
        return obj.value
    return obj


def _solve_kepler(mean_anomaly: float, eccentricity: float, tol: float = 1e-8,
                  max_iter: int = 50) -> float:
    """Solve Kepler's equation M = E - e*sin(E) for the eccentric anomaly E.

    Uses Newton-Raphson iteration. The mean anomaly M must be in radians
    and the eccentricity e in [0, 1).
    """
    # Normalize mean anomaly to [-pi, pi]
    m = mean_anomaly % (2.0 * math.pi)
    if m > math.pi:
        m -= 2.0 * math.pi
    elif m < -math.pi:
        m += 2.0 * math.pi

    # Initial guess
    e_anom = m + eccentricity * math.sin(m)
    for _ in range(max_iter):
        f = e_anom - eccentricity * math.sin(e_anom) - m
        fp = 1.0 - eccentricity * math.cos(e_anom)
        if abs(fp) < 1e-15:
            break
        delta = f / fp
        e_anom -= delta
        if abs(delta) < tol:
            break
    return e_anom


def _true_anomaly_from_eccentric(eccentric_anomaly: float, eccentricity: float) -> float:
    """Convert eccentric anomaly to true anomaly in radians."""
    e = eccentric_anomaly
    ec = eccentricity
    sin_nu = math.sqrt(1.0 - ec * ec) * math.sin(e)
    cos_nu = math.cos(e) - ec
    nu = math.atan2(sin_nu, cos_nu)
    return nu


def _mean_anomaly_from_true(true_anomaly: float, eccentricity: float) -> float:
    """Convert true anomaly to mean anomaly in radians."""
    nu = true_anomaly
    ec = eccentricity
    e_anom = math.atan2(
        math.sqrt(1.0 - ec * ec) * math.sin(nu),
        ec + math.cos(nu),
    )
    m = e_anom - ec * math.sin(e_anom)
    return m


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_BODIES = 500
_MAX_ORBITS = 1000
_MAX_SATELLITES = 500
_MAX_ASTEROIDS = 2000
_MAX_STATIONS = 200
_MAX_THRUSTERS = 1000
_MAX_MANEUVERS = 2000
_MAX_TRAJECTORIES = 500
_MAX_EVENTS = 5000
_MAX_TRAJECTORY_POINTS = 10000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BodyType(Enum):
    """Classification of celestial bodies and artificial objects."""
    STAR = "star"
    PLANET = "planet"
    MOON = "moon"
    ASTEROID = "asteroid"
    COMET = "comet"
    DWARF_PLANET = "dwarf_planet"
    SPACE_STATION = "space_station"
    SATELLITE = "satellite"
    PROBE = "probe"
    DEBRIS = "debris"


class OrbitType(Enum):
    """Geometric classification of an orbit based on eccentricity."""
    CIRCULAR = "circular"
    ELLIPTICAL = "elliptical"
    PARABOLIC = "parabolic"
    HYPERBOLIC = "hyperbolic"


class ThrusterType(Enum):
    """Propulsion technology categories for spacecraft thrusters."""
    CHEMICAL = "chemical"
    ION = "ion"
    NUCLEAR = "nuclear"
    SOLAR_SAIL = "solar_sail"
    FUSION = "fusion"
    ANTIMATTER = "antimatter"
    COLD_GAS = "cold_gas"


class ManeuverType(Enum):
    """Categories of orbital maneuvers."""
    HOHMANN_TRANSFER = "hohmann_transfer"
    ORBIT_RAISE = "orbit_raise"
    ORBIT_LOWER = "orbit_lower"
    PLANE_CHANGE = "plane_change"
    FLYBY = "flyby"
    BRAKING = "braking"
    CIRCULARIZE = "circularize"
    DEORBIT = "deorbit"
    RENDEZVOUS = "rendezvous"
    STATION_KEEPING = "station_keeping"


class OrbitalEventKind(Enum):
    """Types of events recorded by the orbital mechanics system."""
    BODY_REGISTERED = "body_registered"
    BODY_REMOVED = "body_removed"
    BODY_UPDATED = "body_updated"
    ORBIT_COMPUTED = "orbit_computed"
    SATELLITE_REGISTERED = "satellite_registered"
    SATELLITE_REMOVED = "satellite_removed"
    SATELLITE_UPDATED = "satellite_updated"
    ASTEROID_REGISTERED = "asteroid_registered"
    ASTEROID_REMOVED = "asteroid_removed"
    STATION_REGISTERED = "station_registered"
    STATION_REMOVED = "station_removed"
    THRUSTER_REGISTERED = "thruster_registered"
    THRUSTER_REMOVED = "thruster_removed"
    MANEUVER_PLANNED = "maneuver_planned"
    MANEUVER_EXECUTED = "maneuver_executed"
    MANEUVER_CANCELED = "maneuver_canceled"
    COLLISION_WARNING = "collision_warning"
    COLLISION_DETECTED = "collision_detected"
    TRAJECTORY_COMPUTED = "trajectory_computed"
    SYSTEM_TICK = "system_tick"
    SYSTEM_RESET = "system_reset"
    CONFIG_UPDATED = "config_updated"
    FUEL_DEPLETED = "fuel_depleted"
    ORBIT_DECAYED = "orbit_decayed"


class BodyStatus(Enum):
    """Operational status of a body or spacecraft."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DESTROYED = "destroyed"
    DEORBITED = "deorbited"
    PARKED = "parked"
    TRANSIT = "transit"


# ---------------------------------------------------------------------------
# Entity Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CelestialBody:
    """A celestial body such as a star, planet, or moon.

    Positions and velocities are in the inertial frame centered on the
    system barycenter, measured in meters and meters per second.
    """
    body_id: str
    name: str
    body_type: str
    mass_kg: float
    radius_m: float
    position: Vec3 = (0.0, 0.0, 0.0)
    velocity: Vec3 = (0.0, 0.0, 0.0)
    parent_id: Optional[str] = None
    status: str = BodyStatus.ACTIVE.value
    color: str = "#FFFFFF"
    description: str = ""
    albedo: float = 0.3
    axial_tilt_rad: float = 0.0
    rotation_period_s: float = 0.0
    atmosphere_pressure_pa: float = 0.0
    temperature_k: float = 273.15
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Orbit:
    """Keplerian orbital elements describing a body's path around its parent.

    All angular elements are in radians and distances in meters.
    """
    orbit_id: str
    body_id: str
    parent_id: str
    semi_major_axis_m: float
    eccentricity: float
    inclination_rad: float
    longitude_ascending_node_rad: float
    argument_of_periapsis_rad: float
    true_anomaly_rad: float
    period_s: float = 0.0
    apoapsis_m: float = 0.0
    periapsis_m: float = 0.0
    mean_motion_rad_s: float = 0.0
    specific_orbital_energy_jkg: float = 0.0
    specific_angular_momentum_m2s: float = 0.0
    orbit_type: str = OrbitType.ELLIPTICAL.value
    epoch_s: float = 0.0
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Satellite:
    """An artificial satellite orbiting a celestial body."""
    satellite_id: str
    name: str
    body_id: Optional[str] = None
    parent_id: Optional[str] = None
    mass_kg: float = 100.0
    fuel_kg: float = 50.0
    dry_mass_kg: float = 50.0
    position: Vec3 = (0.0, 0.0, 0.0)
    velocity: Vec3 = (0.0, 0.0, 0.0)
    thrust_n: float = 0.0
    isp_s: float = 300.0
    thruster_ids: List[str] = field(default_factory=list)
    status: str = BodyStatus.ACTIVE.value
    mission: str = ""
    operator: str = ""
    launch_time: float = 0.0
    design_life_s: float = 0.0
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Asteroid:
    """An asteroid, typically in a belt or on a potentially hazardous trajectory."""
    asteroid_id: str
    name: str
    mass_kg: float
    radius_m: float
    position: Vec3 = (0.0, 0.0, 0.0)
    velocity: Vec3 = (0.0, 0.0, 0.0)
    parent_id: Optional[str] = None
    spectral_class: str = "C"
    composition: str = ""
    hazard_level: str = "low"
    status: str = BodyStatus.ACTIVE.value
    spin_period_s: float = 0.0
    albedo: float = 0.1
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpaceStation:
    """A crewed or uncrewed space station in a stable orbit."""
    station_id: str
    name: str
    parent_id: Optional[str] = None
    mass_kg: float = 100000.0
    position: Vec3 = (0.0, 0.0, 0.0)
    velocity: Vec3 = (0.0, 0.0, 0.0)
    crew_capacity: int = 0
    crew_count: int = 0
    fuel_kg: float = 1000.0
    status: str = BodyStatus.ACTIVE.value
    orbit_altitude_m: float = 0.0
    modules: List[str] = field(default_factory=list)
    description: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Thruster:
    """A propulsion unit that can be mounted on a satellite or station."""
    thruster_id: str
    name: str
    thruster_type: str
    thrust_n: float
    isp_s: float
    fuel_consumption_kg_s: float = 0.0
    max_burn_time_s: float = 0.0
    mass_kg: float = 0.0
    status: str = BodyStatus.ACTIVE.value
    description: str = ""
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Maneuver:
    """A planned or executed orbital maneuver."""
    maneuver_id: str
    satellite_id: str
    maneuver_type: str
    delta_v_m_s: float
    execution_time: float
    duration_s: float = 0.0
    fuel_required_kg: float = 0.0
    thruster_id: Optional[str] = None
    target_orbit_id: Optional[str] = None
    status: str = "planned"
    description: str = ""
    result_position: Optional[Vec3] = None
    result_velocity: Optional[Vec3] = None
    created_at: float = 0.0
    executed_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Trajectory:
    """A predicted or recorded trajectory as a series of position points."""
    trajectory_id: str
    body_id: str
    points: List[Vec3] = field(default_factory=list)
    times: List[float] = field(default_factory=list)
    velocities: List[Vec3] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    step_s: float = 1.0
    description: str = ""
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Configuration, Statistics, Snapshot, and Event Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class OrbitalConfig:
    """Runtime configuration for the orbital mechanics system."""
    time_scale: float = 1.0
    dt: float = 1.0
    integration_method: str = "velocity_verlet"
    max_substeps: int = 10
    collision_detection: bool = True
    collision_tolerance_m: float = 1000.0
    trajectory_steps: int = 500
    trajectory_step_s: float = 60.0
    event_buffer_size: int = _MAX_EVENTS
    auto_seed: bool = True
    gravity_softening_m: float = 1.0
    max_bodies: int = _MAX_BODIES
    max_satellites: int = _MAX_SATELLITES
    max_asteroids: int = _MAX_ASTEROIDS
    max_stations: int = _MAX_STATIONS
    enable_tidal_forces: bool = False
    enable_atmospheric_drag: bool = False
    enable_relativistic_correction: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OrbitalStats:
    """Statistics tracked by the orbital mechanics system."""
    total_bodies: int = 0
    total_orbits: int = 0
    total_satellites: int = 0
    total_asteroids: int = 0
    total_stations: int = 0
    total_thrusters: int = 0
    total_maneuvers: int = 0
    total_maneuvers_executed: int = 0
    total_trajectories: int = 0
    total_events: int = 0
    total_ticks: int = 0
    total_delta_v_m_s: float = 0.0
    total_fuel_consumed_kg: float = 0.0
    total_collisions_detected: int = 0
    total_collision_warnings: int = 0
    simulation_time_s: float = 0.0
    wall_time_s: float = 0.0
    last_tick_duration_s: float = 0.0
    avg_tick_duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OrbitalSnapshot:
    """A point-in-time snapshot of the entire orbital system state."""
    snapshot_id: str
    timestamp: float
    simulation_time_s: float
    bodies: List[Dict[str, Any]] = field(default_factory=list)
    satellites: List[Dict[str, Any]] = field(default_factory=list)
    asteroids: List[Dict[str, Any]] = field(default_factory=list)
    stations: List[Dict[str, Any]] = field(default_factory=list)
    maneuvers: List[Dict[str, Any]] = field(default_factory=list)
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OrbitalEvent:
    """An event recorded by the orbital mechanics system."""
    event_id: str
    kind: str
    timestamp: float
    simulation_time: float = 0.0
    body_id: Optional[str] = None
    satellite_id: Optional[str] = None
    description: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Main System Class
# ---------------------------------------------------------------------------

class _OrbitalMechanicsSystem:
    """Thread-safe singleton managing all orbital mechanics simulation state.

    The system holds collections of celestial bodies, satellites, asteroids,
    space stations, thrusters, maneuvers, and trajectories. It performs N-body
    gravitational integration, computes Keplerian orbital elements, and
    provides trajectory prediction and maneuver planning capabilities.
    """

    _instance: Optional["_OrbitalMechanicsSystem"] = None
    _init_lock = threading.RLock()
    _lock = threading.RLock()
    _initialized: bool = False
    _seeded: bool = False

    def __init__(self) -> None:
        """Initialize the orbital mechanics system with empty collections."""
        self._lock_local = threading.RLock()
        self._bodies: Dict[str, CelestialBody] = {}
        self._orbits: Dict[str, Orbit] = {}
        self._satellites: Dict[str, Satellite] = {}
        self._asteroids: Dict[str, Asteroid] = {}
        self._stations: Dict[str, SpaceStation] = {}
        self._thrusters: Dict[str, Thruster] = {}
        self._maneuvers: Dict[str, Maneuver] = {}
        self._trajectories: Dict[str, Trajectory] = {}
        self._events: List[OrbitalEvent] = []
        self._config = OrbitalConfig()
        self._stats = OrbitalStats()
        self._tick_count: int = 0
        _sim_start_time = _now()
        self._wall_time_s: float = 0.0
        self._sim_start_wall: float = _sim_start_time
        self._last_tick_wall: float = _sim_start_time
        self._simulation_time_s: float = 0.0
        self._event_counter: int = 0
        self._body_counter: int = 0
        self._orbit_counter: int = 0
        self._satellite_counter: int = 0
        self._asteroid_counter: int = 0
        self._station_counter: int = 0
        self._thruster_counter: int = 0
        self._maneuver_counter: int = 0
        self._trajectory_counter: int = 0
        self._tick_durations: List[float] = []

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "_OrbitalMechanicsSystem":
        """Return the singleton instance, creating and seeding it on first call.

        Uses double-checked locking to ensure thread safety without
        acquiring the lock on every call after initialization.
        """
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    inst = cls()
                    inst._initialize()
                    cls._instance = inst
        return cls._instance

    def _initialize(self) -> None:
        """Perform one-time initialization including seeding default data."""
        if self._initialized:
            return
        with self._lock_local:
            if self._initialized:
                return
            self._stats.wall_time_s = 0.0
            self._sim_start_wall = _now()
            self._last_tick_wall = self._sim_start_wall
            if self._config.auto_seed and not self._seeded:
                self._seed()
            self._initialized = True

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _next_event_id(self) -> str:
        """Generate the next sequential event identifier."""
        self._event_counter += 1
        return f"oevt_{self._event_counter:08d}"

    def _record_event(self, kind: str, description: str = "",
                      body_id: Optional[str] = None,
                      satellite_id: Optional[str] = None,
                      **data: Any) -> OrbitalEvent:
        """Record an event in the event log and update statistics."""
        event = OrbitalEvent(
            event_id=self._next_event_id(),
            kind=kind,
            timestamp=_now(),
            simulation_time=self._simulation_time_s,
            body_id=body_id,
            satellite_id=satellite_id,
            description=description,
            data=data,
        )
        self._events.append(event)
        if len(self._events) > self._config.event_buffer_size:
            # Drop oldest events when the buffer is full
            drop_count = len(self._events) - self._config.event_buffer_size
            del self._events[:drop_count]
        self._stats.total_events = len(self._events)
        return event

    # ------------------------------------------------------------------
    # Seeding default solar system data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the system with a default star, planets, moons, and craft.

        The seed data represents a compact star system with a central star,
        four planets, three moons, three satellites, three asteroids, and
        two space stations. All orbital parameters are computed from
        physical relationships using Newtonian gravity.
        """
        if self._seeded:
            return
        with self._lock_local:
            if self._seeded:
                return

            # Central star
            sol = CelestialBody(
                body_id="body_sol",
                name="Sol Prime",
                body_type=BodyType.STAR.value,
                mass_kg=1.989e30,
                radius_m=6.96e8,
                position=(0.0, 0.0, 0.0),
                velocity=(0.0, 0.0, 0.0),
                parent_id=None,
                color="#FDB813",
                description="Central G-type main sequence star",
                temperature_k=5778.0,
                albedo=0.0,
                created_at=_now(),
            )
            self._bodies[sol.body_id] = sol

            # Planets with orbital parameters
            planet_data = [
                ("body_mercurion", "Mercurion", 3.301e23, 2.440e6, 5.79e10,
                 0.2056, 7.005, "#8C8C8C", "Innermost rocky planet"),
                ("body_venusia", "Venusia", 4.867e24, 6.052e6, 1.082e11,
                 0.0067, 3.395, "#E6C229", "Hot terrestrial planet"),
                ("body_terranis", "Terranis", 5.972e24, 6.371e6, 1.496e11,
                 0.0167, 0.000, "#4A90D9", "Habitable terrestrial planet"),
                ("body_martius", "Martius", 6.417e23, 3.390e6, 2.279e11,
                 0.0934, 1.850, "#CD5C5C", "Cold desert planet"),
            ]

            mu_sun = GRAVITATIONAL_CONSTANT * sol.mass_kg
            for (pid, pname, pmass, pradius, p_sma, p_ecc, p_inc_deg, pcolor, pdesc) in planet_data:
                inc_rad = math.radians(p_inc_deg)
                # Circular orbit velocity at semi-major axis distance
                v_circ = math.sqrt(mu_sun / p_sma)
                # Position at periapsis on the ecliptic plane
                pos = (p_sma, 0.0, 0.0)
                # Velocity perpendicular to radius for near-circular orbit
                vel = (0.0, v_circ * math.sqrt(1.0 - p_ecc), 0.0)
                # Apply inclination by rotating velocity in the z direction
                vel = (vel[0], vel[1] * math.cos(inc_rad), vel[1] * math.sin(inc_rad))
                body = CelestialBody(
                    body_id=pid,
                    name=pname,
                    body_type=BodyType.PLANET.value,
                    mass_kg=pmass,
                    radius_m=pradius,
                    position=pos,
                    velocity=vel,
                    parent_id=sol.body_id,
                    color=pcolor,
                    description=pdesc,
                    temperature_k=288.0,
                    albedo=0.3,
                    created_at=_now(),
                )
                self._bodies[pid] = body

                # Compute orbit for this planet
                self._compute_and_store_orbit(pid, sol.body_id, mu_sun)

            # Moons orbiting planets
            moon_data = [
                ("body_luna", "Luna", 7.342e22, 1.737e6, "body_terranis",
                 3.844e8, 0.0549, 5.145, "#C0C0C0", "Natural satellite of Terranis"),
                ("body_phobos2", "Phobos2", 1.066e16, 1.112e4, "body_martius",
                 9.376e6, 0.0151, 1.08, "#8B7355", "Inner moon of Martius"),
                ("body_deimos2", "Deimos2", 1.476e15, 6.2e3, "body_martius",
                 2.346e7, 0.0002, 1.79, "#A0522D", "Outer moon of Martius"),
            ]

            for (mid, mname, mmass, mradius, mparent, m_sma, m_ecc, m_inc_deg, mcolor, mdesc) in moon_data:
                parent = self._bodies.get(mparent)
                if parent is None:
                    continue
                mu_parent = GRAVITATIONAL_CONSTANT * parent.mass_kg
                inc_rad = math.radians(m_inc_deg)
                v_circ = math.sqrt(mu_parent / m_sma)
                # Moon position relative to parent, then offset by parent position
                rel_pos = (m_sma, 0.0, 0.0)
                abs_pos = _vadd(parent.position, rel_pos)
                # Velocity is parent velocity plus orbital velocity
                rel_vel = (0.0, v_circ * math.sqrt(1.0 - m_ecc), 0.0)
                rel_vel = (rel_vel[0], rel_vel[1] * math.cos(inc_rad), rel_vel[1] * math.sin(inc_rad))
                abs_vel = _vadd(parent.velocity, rel_vel)
                moon = CelestialBody(
                    body_id=mid,
                    name=mname,
                    body_type=BodyType.MOON.value,
                    mass_kg=mmass,
                    radius_m=mradius,
                    position=abs_pos,
                    velocity=abs_vel,
                    parent_id=mparent,
                    color=mcolor,
                    description=mdesc,
                    albedo=0.12,
                    created_at=_now(),
                )
                self._bodies[mid] = moon
                self._compute_and_store_orbit(mid, mparent, mu_parent)

            # Satellites orbiting Terranis (Earth-like)
            earth = self._bodies.get("body_terranis")
            if earth is not None:
                mu_earth = GRAVITATIONAL_CONSTANT * earth.mass_kg
                sat_data = [
                    ("sat_aegis_1", "Aegis-1 Comm Relay", 4.2e6, 500.0, 50.0,
                     "Communications relay in low orbit", 1200.0, 300.0),
                    ("sat_hubble_x", "Hubble-X Telescope", 5.5e5, 800.0, 30.0,
                     "Deep space observation telescope", 550.0, 280.0),
                    ("sat_gps_prime", "GPS-Prime Nav", 2.0e7, 200.0, 20.0,
                     "Global navigation satellite", 20000.0e3, 250.0),
                ]
                for (sid, sname, alt_m, smass, sfuel, sdesc, sisp, sthrust) in sat_data:
                    r = earth.radius_m + alt_m
                    v = math.sqrt(mu_earth / r)
                    sat_pos = _vadd(earth.position, (r, 0.0, 0.0))
                    sat_vel = _vadd(earth.velocity, (0.0, v, 0.0))
                    sat = Satellite(
                        satellite_id=sid,
                        name=sname,
                        body_id=None,
                        parent_id=earth.body_id,
                        mass_kg=smass,
                        fuel_kg=sfuel,
                        dry_mass_kg=smass - sfuel,
                        position=sat_pos,
                        velocity=sat_vel,
                        thrust_n=sthrust,
                        isp_s=sisp,
                        status=BodyStatus.ACTIVE.value,
                        mission=sdesc,
                        operator="SparkLabs Space Division",
                        launch_time=_now(),
                        created_at=_now(),
                    )
                    self._satellites[sid] = sat

            # Asteroids in a belt between Martius and the outer system
            asteroid_data = [
                ("ast_vesta_minor", "Vesta Minor", 2.6e20, 2.63e5,
                 3.5e11, 0.089, 7.14, "V-type", "Differentiated asteroid"),
                ("ast_ceres_prime", "Ceres Prime", 9.4e20, 4.73e5,
                 4.14e11, 0.076, 10.59, "C-type", "Dwarf planet candidate"),
                ("ast_pallas_echo", "Pallas Echo", 2.1e20, 2.55e5,
                 4.1e11, 0.231, 34.84, "B-type", "Highly inclined asteroid"),
            ]
            for (aid, aname, amass, aradius, a_sma, a_ecc, a_inc_deg, aclass, adesc) in asteroid_data:
                inc_rad = math.radians(a_inc_deg)
                v_circ = math.sqrt(mu_sun / a_sma)
                apos = (a_sma * math.cos(inc_rad), a_sma * math.sin(inc_rad), 0.0)
                avel = (-v_circ * math.sin(inc_rad), v_circ * math.cos(inc_rad), 0.0)
                asteroid = Asteroid(
                    asteroid_id=aid,
                    name=aname,
                    mass_kg=amass,
                    radius_m=aradius,
                    position=apos,
                    velocity=avel,
                    parent_id=sol.body_id,
                    spectral_class=aclass,
                    composition=adesc,
                    hazard_level="low",
                    status=BodyStatus.ACTIVE.value,
                    spin_period_s=50000.0,
                    albedo=0.09,
                    created_at=_now(),
                )
                self._asteroids[aid] = asteroid

            # Space stations
            if earth is not None:
                station_data = [
                    ("sta_gammo_1", "Gamma Orbital Station", 420000.0,
                     7, 3, "Modular research station in low orbit",
                     ["habitation", "lab", "docking", "solar"]),
                    ("sta_beta_gate", "Beta Gateway Hub", 35786.0e3,
                     12, 5, "Geostationary transfer hub",
                     ["hub", "fuel_depot", "docking", "comms", "habitation"]),
                ]
                for (stid, sname, stalt, stcrew, stcurcrew, stdesc, stmodules) in station_data:
                    r = earth.radius_m + stalt
                    v = math.sqrt(mu_earth / r)
                    stpos = _vadd(earth.position, (r, 0.0, 0.0))
                    stvel = _vadd(earth.velocity, (0.0, v, 0.0))
                    station = SpaceStation(
                        station_id=stid,
                        name=sname,
                        parent_id=earth.body_id,
                        mass_kg=420000.0,
                        position=stpos,
                        velocity=stvel,
                        crew_capacity=stcrew,
                        crew_count=stcurcrew,
                        fuel_kg=5000.0,
                        status=BodyStatus.ACTIVE.value,
                        orbit_altitude_m=stalt,
                        modules=stmodules,
                        description=stdesc,
                        created_at=_now(),
                    )
                    self._stations[stid] = station

            # Thrusters for satellites
            thruster_data = [
                ("thr_chem_main", "Main Chemical Thruster", ThrusterType.CHEMICAL.value,
                 500.0, 300.0, 1.67, 3600.0, 50.0, "Primary chemical propulsion"),
                ("thr_ion_aux", "Auxiliary Ion Thruster", ThrusterType.ION.value,
                 0.5, 3000.0, 1.67e-4, 50000.0, 10.0, "High-efficiency ion propulsion"),
                ("thr_nuke_heavy", "Heavy Nuclear Thruster", ThrusterType.NUCLEAR.value,
                 1000.0, 900.0, 1.11, 10000.0, 200.0, "Nuclear thermal propulsion"),
            ]
            for (tid, tname, ttype, tthrust, tisp, tfuel, tmaxburn, tmass, tdesc) in thruster_data:
                thr = Thruster(
                    thruster_id=tid,
                    name=tname,
                    thruster_type=ttype,
                    thrust_n=tthrust,
                    isp_s=tisp,
                    fuel_consumption_kg_s=tfuel,
                    max_burn_time_s=tmaxburn,
                    mass_kg=tmass,
                    description=tdesc,
                    created_at=_now(),
                )
                self._thrusters[tid] = thr

            # Assign thrusters to satellites
            if "sat_aegis_1" in self._satellites:
                self._satellites["sat_aegis_1"].thruster_ids = ["thr_chem_main"]
            if "sat_hubble_x" in self._satellites:
                self._satellites["sat_hubble_x"].thruster_ids = ["thr_ion_aux"]

            self._update_stats_counts()
            self._stats.wall_time_s = 0.0
            self._sim_start_wall = _now()
            self._seeded = True

            self._record_event(
                OrbitalEventKind.SYSTEM_RESET.value,
                description="Orbital mechanics system seeded with default data",
            )

    def _compute_and_store_orbit(self, body_id: str, parent_id: str, mu: float) -> Optional[Orbit]:
        """Compute orbital elements from a body's state vectors and store them.

        Parameters:
            body_id: Identifier of the orbiting body.
            parent_id: Identifier of the central body being orbited.
            mu: Standard gravitational parameter GM of the parent body.

        Returns the computed Orbit or None if the body was not found.
        """
        body = self._bodies.get(body_id)
        parent = self._bodies.get(parent_id)
        if body is None or parent is None:
            return None

        r_vec = _vsub(body.position, parent.position)
        v_vec = _vsub(body.velocity, parent.velocity)
        r = _vlen(r_vec)
        if r < 1e-3:
            return None

        v = _vlen(v_vec)
        h_vec = _vcross(r_vec, v_vec)
        h = _vlen(h_vec)
        if h < 1e-3:
            return None

        # Specific orbital energy
        energy = v * v / 2.0 - mu / r
        # Semi-major axis
        if abs(energy) < 1e-6:
            a = float('inf')
        else:
            a = -mu / (2.0 * energy)

        # Eccentricity vector
        e_vec = _vsub(_vscale(_vcross(v_vec, h_vec), 1.0 / mu), _vscale(r_vec, 1.0 / r))
        e = _vlen(e_vec)

        # Inclination
        inc = math.acos(_clamp(h_vec[2] / h, -1.0, 1.0))

        # Node vector (points toward ascending node)
        n_vec = _vcross((0.0, 0.0, 1.0), h_vec)
        n = _vlen(n_vec)

        # Longitude of ascending node
        if n < 1e-6:
            omega_big = 0.0
        else:
            omega_big = math.acos(_clamp(n_vec[0] / n, -1.0, 1.0))
            if n_vec[1] < 0:
                omega_big = 2.0 * math.pi - omega_big

        # Argument of periapsis
        if e < 1e-6 or n < 1e-6:
            omega_small = 0.0
        else:
            omega_small = math.acos(_clamp(_vdot(n_vec, e_vec) / (n * e), -1.0, 1.0))
            if e_vec[2] < 0:
                omega_small = 2.0 * math.pi - omega_small

        # True anomaly
        if e < 1e-6:
            nu = 0.0
        else:
            nu = math.acos(_clamp(_vdot(e_vec, r_vec) / (e * r), -1.0, 1.0))
            if _vdot(r_vec, v_vec) < 0:
                nu = 2.0 * math.pi - nu

        # Orbit classification
        if e < 1e-6:
            orbit_type = OrbitType.CIRCULAR.value
        elif e < 1.0 - 1e-6:
            orbit_type = OrbitType.ELLIPTICAL.value
        elif e < 1.0 + 1e-6:
            orbit_type = OrbitType.PARABOLIC.value
        else:
            orbit_type = OrbitType.HYPERBOLIC.value

        # Period and mean motion for bound orbits
        period = 0.0
        mean_motion = 0.0
        if a > 0 and a != float('inf'):
            period = 2.0 * math.pi * math.sqrt(a * a * a / mu)
            mean_motion = 2.0 * math.pi / period if period > 0 else 0.0

        apoapsis = a * (1.0 + e) if a > 0 else float('inf')
        periapsis = a * (1.0 - e) if a > 0 else 0.0

        self._orbit_counter += 1
        orbit = Orbit(
            orbit_id=f"orb_{self._orbit_counter:08d}",
            body_id=body_id,
            parent_id=parent_id,
            semi_major_axis_m=a,
            eccentricity=e,
            inclination_rad=inc,
            longitude_ascending_node_rad=omega_big,
            argument_of_periapsis_rad=omega_small,
            true_anomaly_rad=nu,
            period_s=period,
            apoapsis_m=apoapsis,
            periapsis_m=periapsis,
            mean_motion_rad_s=mean_motion,
            specific_orbital_energy_jkg=energy,
            specific_angular_momentum_m2s=h,
            orbit_type=orbit_type,
            epoch_s=self._simulation_time_s,
            created_at=_now(),
        )
        self._orbits[orbit.orbit_id] = orbit
        return orbit

    def _update_stats_counts(self) -> None:
        """Refresh the count-based statistics from current collections."""
        self._stats.total_bodies = len(self._bodies)
        self._stats.total_orbits = len(self._orbits)
        self._stats.total_satellites = len(self._satellites)
        self._stats.total_asteroids = len(self._asteroids)
        self._stats.total_stations = len(self._stations)
        self._stats.total_thrusters = len(self._thrusters)
        self._stats.total_maneuvers = len(self._maneuvers)
        self._stats.total_trajectories = len(self._trajectories)

    # ------------------------------------------------------------------
    # Celestial Body Management
    # ------------------------------------------------------------------

    def register_body(self, body_id: Optional[str] = None, name: str = "",
                      body_type: str = BodyType.PLANET.value,
                      mass_kg: float = 0.0, radius_m: float = 0.0,
                      position: Optional[Sequence[float]] = None,
                      velocity: Optional[Sequence[float]] = None,
                      parent_id: Optional[str] = None,
                      color: str = "#FFFFFF",
                      description: str = "",
                      **kwargs: Any) -> Dict[str, Any]:
        """Register a new celestial body in the system.

        If body_id is not provided, one is generated automatically.
        The position and velocity default to the origin if not specified.
        Returns a dictionary with the body_id and the created body data.
        """
        with self._lock_local:
            bid = _gen_id("body", body_id)
            if bid in self._bodies:
                return {"ok": False, "error": f"Body already exists: {bid}"}
            if len(self._bodies) >= self._config.max_bodies:
                return {"ok": False, "error": "Maximum body capacity reached"}

            pos = _list_to_v(position) if position else (0.0, 0.0, 0.0)
            vel = _list_to_v(velocity) if velocity else (0.0, 0.0, 0.0)

            body = CelestialBody(
                body_id=bid,
                name=name or f"Body-{bid[-6:]}",
                body_type=body_type,
                mass_kg=mass_kg,
                radius_m=radius_m,
                position=pos,
                velocity=vel,
                parent_id=parent_id,
                color=color,
                description=description,
                albedo=kwargs.get("albedo", 0.3),
                axial_tilt_rad=kwargs.get("axial_tilt_rad", 0.0),
                rotation_period_s=kwargs.get("rotation_period_s", 0.0),
                atmosphere_pressure_pa=kwargs.get("atmosphere_pressure_pa", 0.0),
                temperature_k=kwargs.get("temperature_k", 273.15),
                status=kwargs.get("status", BodyStatus.ACTIVE.value),
                created_at=_now(),
                updated_at=_now(),
            )
            self._bodies[bid] = body
            self._body_counter += 1

            # Compute orbit if a parent is specified and exists
            if parent_id and parent_id in self._bodies:
                parent = self._bodies[parent_id]
                mu = GRAVITATIONAL_CONSTANT * parent.mass_kg
                self._compute_and_store_orbit(bid, parent_id, mu)

            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.BODY_REGISTERED.value,
                description=f"Body registered: {body.name}",
                body_id=bid,
                mass_kg=mass_kg,
                body_type=body_type,
            )
            return {"ok": True, "body_id": bid, "body": body.to_dict()}

    def get_body(self, body_id: str) -> Optional[Dict[str, Any]]:
        """Return the celestial body with the given id, or None if not found."""
        with self._lock_local:
            body = self._bodies.get(body_id)
            if body is None:
                return None
            return body.to_dict()

    def list_bodies(self, body_type: Optional[str] = None,
                    parent_id: Optional[str] = None,
                    status: Optional[str] = None,
                    limit: int = 100,
                    offset: int = 0) -> List[Dict[str, Any]]:
        """List celestial bodies with optional filtering by type, parent, or status.

        Results are paginated using limit and offset parameters.
        """
        with self._lock_local:
            results: List[Dict[str, Any]] = []
            for body in self._bodies.values():
                if body_type is not None and body.body_type != body_type:
                    continue
                if parent_id is not None and body.parent_id != parent_id:
                    continue
                if status is not None and body.status != status:
                    continue
                results.append(body.to_dict())
            results = results[offset:offset + limit]
            return results

    def update_body(self, body_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Update attributes of an existing celestial body.

        Only provided keyword arguments are applied; all other fields remain
        unchanged. Returns a dictionary with ok flag and the updated body.
        """
        with self._lock_local:
            body = self._bodies.get(body_id)
            if body is None:
                return {"ok": False, "error": f"Body not found: {body_id}"}

            # Apply allowed field updates
            allowed_fields = {
                "name", "body_type", "mass_kg", "radius_m", "parent_id",
                "color", "description", "albedo", "axial_tilt_rad",
                "rotation_period_s", "atmosphere_pressure_pa", "temperature_k",
                "status",
            }
            changed = False
            for k, v in kwargs.items():
                if k in allowed_fields and hasattr(body, k):
                    setattr(body, k, v)
                    changed = True
                elif k == "position" and v is not None:
                    body.position = _list_to_v(v)
                    changed = True
                elif k == "velocity" and v is not None:
                    body.velocity = _list_to_v(v)
                    changed = True

            if changed:
                body.updated_at = _now()
                # Recompute orbit if parent exists
                if body.parent_id and body.parent_id in self._bodies:
                    parent = self._bodies[body.parent_id]
                    mu = GRAVITATIONAL_CONSTANT * parent.mass_kg
                    self._compute_and_store_orbit(body_id, body.parent_id, mu)

                self._record_event(
                    OrbitalEventKind.BODY_UPDATED.value,
                    description=f"Body updated: {body.name}",
                    body_id=body_id,
                )
            return {"ok": True, "body": body.to_dict()}

    def remove_body(self, body_id: str) -> Dict[str, Any]:
        """Remove a celestial body and any orbits referencing it.

        Returns the removed body data, or an error dictionary if not found.
        """
        with self._lock_local:
            body = self._bodies.pop(body_id, None)
            if body is None:
                return {"ok": False, "error": f"Body not found: {body_id}"}

            # Remove orbits for this body
            orbits_to_remove = [
                oid for oid, o in self._orbits.items()
                if o.body_id == body_id or o.parent_id == body_id
            ]
            for oid in orbits_to_remove:
                self._orbits.pop(oid, None)

            # Re-parent children to the removed body's parent
            for child in self._bodies.values():
                if child.parent_id == body_id:
                    child.parent_id = body.parent_id

            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.BODY_REMOVED.value,
                description=f"Body removed: {body.name}",
                body_id=body_id,
            )
            return {"ok": True, "body": body.to_dict()}

    # ------------------------------------------------------------------
    # Orbit Management
    # ------------------------------------------------------------------

    def compute_orbit(self, body_id: str, parent_id: Optional[str] = None
                      ) -> Dict[str, Any]:
        """Compute and store the Keplerian orbit of a body around its parent.

        If parent_id is not specified, the body's existing parent_id is used.
        Returns the computed orbital elements or an error dictionary.
        """
        with self._lock_local:
            body = self._bodies.get(body_id)
            if body is None:
                return {"ok": False, "error": f"Body not found: {body_id}"}

            pid = parent_id or body.parent_id
            if pid is None:
                return {"ok": False, "error": "No parent body specified"}

            parent = self._bodies.get(pid)
            if parent is None:
                return {"ok": False, "error": f"Parent body not found: {pid}"}

            mu = GRAVITATIONAL_CONSTANT * parent.mass_kg
            orbit = self._compute_and_store_orbit(body_id, pid, mu)
            if orbit is None:
                return {"ok": False, "error": "Failed to compute orbit (degenerate state)"}

            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.ORBIT_COMPUTED.value,
                description=f"Orbit computed for {body.name}",
                body_id=body_id,
                orbit_id=orbit.orbit_id,
            )
            return {"ok": True, "orbit": orbit.to_dict()}

    def get_orbit(self, orbit_id: str) -> Optional[Dict[str, Any]]:
        """Return the orbit with the given id, or None if not found."""
        with self._lock_local:
            orbit = self._orbits.get(orbit_id)
            if orbit is None:
                return None
            return orbit.to_dict()

    def list_orbits(self, body_id: Optional[str] = None,
                    parent_id: Optional[str] = None,
                    orbit_type: Optional[str] = None,
                    limit: int = 100,
                    offset: int = 0) -> List[Dict[str, Any]]:
        """List orbits with optional filtering by body, parent, or orbit type."""
        with self._lock_local:
            results: List[Dict[str, Any]] = []
            for orbit in self._orbits.values():
                if body_id is not None and orbit.body_id != body_id:
                    continue
                if parent_id is not None and orbit.parent_id != parent_id:
                    continue
                if orbit_type is not None and orbit.orbit_type != orbit_type:
                    continue
                results.append(orbit.to_dict())
            results = results[offset:offset + limit]
            return results

    def compute_period(self, semi_major_axis_m: float, parent_mass_kg: float
                       ) -> float:
        """Compute the orbital period using Kepler's third law.

        T = 2*pi * sqrt(a^3 / GM)
        Returns the period in seconds.
        """
        mu = GRAVITATIONAL_CONSTANT * parent_mass_kg
        if mu <= 0 or semi_major_axis_m <= 0:
            return 0.0
        return 2.0 * math.pi * math.sqrt(semi_major_axis_m ** 3 / mu)

    def compute_apoapsis(self, semi_major_axis_m: float, eccentricity: float
                         ) -> float:
        """Compute the apoapsis distance: r_a = a * (1 + e)."""
        return semi_major_axis_m * (1.0 + eccentricity)

    def compute_periapsis(self, semi_major_axis_m: float, eccentricity: float
                          ) -> float:
        """Compute the periapsis distance: r_p = a * (1 - e)."""
        return semi_major_axis_m * (1.0 - eccentricity)

    def compute_semi_major_axis(self, period_s: float, parent_mass_kg: float
                                ) -> float:
        """Compute the semi-major axis from the orbital period.

        Derived from Kepler's third law: a = (GM * T^2 / (4*pi^2))^(1/3)
        """
        mu = GRAVITATIONAL_CONSTANT * parent_mass_kg
        if mu <= 0 or period_s <= 0:
            return 0.0
        return (mu * period_s * period_s / (4.0 * math.pi * math.pi)) ** (1.0 / 3.0)

    def compute_eccentricity(self, periapsis_m: float, apoapsis_m: float
                             ) -> float:
        """Compute eccentricity from periapsis and apoapsis distances.

        e = (r_a - r_p) / (r_a + r_p)
        """
        total = periapsis_m + apoapsis_m
        if total < 1e-9:
            return 0.0
        return abs(apoapsis_m - periapsis_m) / total

    # ------------------------------------------------------------------
    # Satellite Management
    # ------------------------------------------------------------------

    def register_satellite(self, satellite_id: Optional[str] = None,
                           name: str = "",
                           parent_id: Optional[str] = None,
                           mass_kg: float = 100.0,
                           fuel_kg: float = 50.0,
                           position: Optional[Sequence[float]] = None,
                           velocity: Optional[Sequence[float]] = None,
                           thrust_n: float = 0.0,
                           isp_s: float = 300.0,
                           mission: str = "",
                           operator: str = "",
                           **kwargs: Any) -> Dict[str, Any]:
        """Register a new satellite in the system.

        If satellite_id is not provided, one is generated automatically.
        Returns a dictionary with the satellite_id and created satellite data.
        """
        with self._lock_local:
            sid = _gen_id("sat", satellite_id)
            if sid in self._satellites:
                return {"ok": False, "error": f"Satellite already exists: {sid}"}
            if len(self._satellites) >= self._config.max_satellites:
                return {"ok": False, "error": "Maximum satellite capacity reached"}

            pos = _list_to_v(position) if position else (0.0, 0.0, 0.0)
            vel = _list_to_v(velocity) if velocity else (0.0, 0.0, 0.0)

            sat = Satellite(
                satellite_id=sid,
                name=name or f"Satellite-{sid[-6:]}",
                body_id=None,
                parent_id=parent_id,
                mass_kg=mass_kg,
                fuel_kg=fuel_kg,
                dry_mass_kg=kwargs.get("dry_mass_kg", mass_kg - fuel_kg),
                position=pos,
                velocity=vel,
                thrust_n=thrust_n,
                isp_s=isp_s,
                thruster_ids=kwargs.get("thruster_ids", []),
                status=kwargs.get("status", BodyStatus.ACTIVE.value),
                mission=mission,
                operator=operator,
                launch_time=_now(),
                design_life_s=kwargs.get("design_life_s", 0.0),
                created_at=_now(),
                updated_at=_now(),
            )
            self._satellites[sid] = sat
            self._satellite_counter += 1
            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.SATELLITE_REGISTERED.value,
                description=f"Satellite registered: {sat.name}",
                satellite_id=sid,
            )
            return {"ok": True, "satellite_id": sid, "satellite": sat.to_dict()}

    def get_satellite(self, satellite_id: str) -> Optional[Dict[str, Any]]:
        """Return the satellite with the given id, or None if not found."""
        with self._lock_local:
            sat = self._satellites.get(satellite_id)
            if sat is None:
                return None
            return sat.to_dict()

    def list_satellites(self, parent_id: Optional[str] = None,
                        status: Optional[str] = None,
                        limit: int = 100,
                        offset: int = 0) -> List[Dict[str, Any]]:
        """List satellites with optional filtering by parent or status."""
        with self._lock_local:
            results: List[Dict[str, Any]] = []
            for sat in self._satellites.values():
                if parent_id is not None and sat.parent_id != parent_id:
                    continue
                if status is not None and sat.status != status:
                    continue
                results.append(sat.to_dict())
            results = results[offset:offset + limit]
            return results

    def update_satellite(self, satellite_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Update attributes of an existing satellite.

        Only provided keyword arguments are applied. Returns a dictionary
        with ok flag and the updated satellite data.
        """
        with self._lock_local:
            sat = self._satellites.get(satellite_id)
            if sat is None:
                return {"ok": False, "error": f"Satellite not found: {satellite_id}"}

            allowed_fields = {
                "name", "parent_id", "mass_kg", "fuel_kg", "dry_mass_kg",
                "thrust_n", "isp_s", "thruster_ids", "status", "mission",
                "operator", "design_life_s",
            }
            changed = False
            for k, v in kwargs.items():
                if k in allowed_fields and hasattr(sat, k):
                    setattr(sat, k, v)
                    changed = True
                elif k == "position" and v is not None:
                    sat.position = _list_to_v(v)
                    changed = True
                elif k == "velocity" and v is not None:
                    sat.velocity = _list_to_v(v)
                    changed = True

            if changed:
                sat.updated_at = _now()
                self._record_event(
                    OrbitalEventKind.SATELLITE_UPDATED.value,
                    description=f"Satellite updated: {sat.name}",
                    satellite_id=satellite_id,
                )
            return {"ok": True, "satellite": sat.to_dict()}

    def remove_satellite(self, satellite_id: str) -> Dict[str, Any]:
        """Remove a satellite from the system and return its data."""
        with self._lock_local:
            sat = self._satellites.pop(satellite_id, None)
            if sat is None:
                return {"ok": False, "error": f"Satellite not found: {satellite_id}"}

            # Remove maneuvers for this satellite
            maneuvers_to_remove = [
                mid for mid, m in self._maneuvers.items()
                if m.satellite_id == satellite_id
            ]
            for mid in maneuvers_to_remove:
                self._maneuvers.pop(mid, None)

            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.SATELLITE_REMOVED.value,
                description=f"Satellite removed: {sat.name}",
                satellite_id=satellite_id,
            )
            return {"ok": True, "satellite": sat.to_dict()}

    # ------------------------------------------------------------------
    # Asteroid Management
    # ------------------------------------------------------------------

    def register_asteroid(self, asteroid_id: Optional[str] = None,
                          name: str = "",
                          mass_kg: float = 0.0,
                          radius_m: float = 0.0,
                          position: Optional[Sequence[float]] = None,
                          velocity: Optional[Sequence[float]] = None,
                          parent_id: Optional[str] = None,
                          spectral_class: str = "C",
                          composition: str = "",
                          hazard_level: str = "low",
                          **kwargs: Any) -> Dict[str, Any]:
        """Register a new asteroid in the system.

        If asteroid_id is not provided, one is generated automatically.
        Returns a dictionary with the asteroid_id and created asteroid data.
        """
        with self._lock_local:
            aid = _gen_id("ast", asteroid_id)
            if aid in self._asteroids:
                return {"ok": False, "error": f"Asteroid already exists: {aid}"}
            if len(self._asteroids) >= self._config.max_asteroids:
                return {"ok": False, "error": "Maximum asteroid capacity reached"}

            pos = _list_to_v(position) if position else (0.0, 0.0, 0.0)
            vel = _list_to_v(velocity) if velocity else (0.0, 0.0, 0.0)

            asteroid = Asteroid(
                asteroid_id=aid,
                name=name or f"Asteroid-{aid[-6:]}",
                mass_kg=mass_kg,
                radius_m=radius_m,
                position=pos,
                velocity=vel,
                parent_id=parent_id,
                spectral_class=spectral_class,
                composition=composition,
                hazard_level=hazard_level,
                status=kwargs.get("status", BodyStatus.ACTIVE.value),
                spin_period_s=kwargs.get("spin_period_s", 0.0),
                albedo=kwargs.get("albedo", 0.1),
                created_at=_now(),
                updated_at=_now(),
            )
            self._asteroids[aid] = asteroid
            self._asteroid_counter += 1
            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.ASTEROID_REGISTERED.value,
                description=f"Asteroid registered: {asteroid.name}",
                body_id=aid,
            )
            return {"ok": True, "asteroid_id": aid, "asteroid": asteroid.to_dict()}

    def get_asteroid(self, asteroid_id: str) -> Optional[Dict[str, Any]]:
        """Return the asteroid with the given id, or None if not found."""
        with self._lock_local:
            ast = self._asteroids.get(asteroid_id)
            if ast is None:
                return None
            return ast.to_dict()

    def list_asteroids(self, parent_id: Optional[str] = None,
                       hazard_level: Optional[str] = None,
                       status: Optional[str] = None,
                       limit: int = 100,
                       offset: int = 0) -> List[Dict[str, Any]]:
        """List asteroids with optional filtering by parent, hazard, or status."""
        with self._lock_local:
            results: List[Dict[str, Any]] = []
            for ast in self._asteroids.values():
                if parent_id is not None and ast.parent_id != parent_id:
                    continue
                if hazard_level is not None and ast.hazard_level != hazard_level:
                    continue
                if status is not None and ast.status != status:
                    continue
                results.append(ast.to_dict())
            results = results[offset:offset + limit]
            return results

    def update_asteroid(self, asteroid_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Update attributes of an existing asteroid."""
        with self._lock_local:
            ast = self._asteroids.get(asteroid_id)
            if ast is None:
                return {"ok": False, "error": f"Asteroid not found: {asteroid_id}"}

            allowed_fields = {
                "name", "mass_kg", "radius_m", "parent_id",
                "spectral_class", "composition", "hazard_level",
                "status", "spin_period_s", "albedo",
            }
            changed = False
            for k, v in kwargs.items():
                if k in allowed_fields and hasattr(ast, k):
                    setattr(ast, k, v)
                    changed = True
                elif k == "position" and v is not None:
                    ast.position = _list_to_v(v)
                    changed = True
                elif k == "velocity" and v is not None:
                    ast.velocity = _list_to_v(v)
                    changed = True

            if changed:
                ast.updated_at = _now()
                self._record_event(
                    OrbitalEventKind.BODY_UPDATED.value,
                    description=f"Asteroid updated: {ast.name}",
                    body_id=asteroid_id,
                )
            return {"ok": True, "asteroid": ast.to_dict()}

    def remove_asteroid(self, asteroid_id: str) -> Dict[str, Any]:
        """Remove an asteroid from the system and return its data."""
        with self._lock_local:
            ast = self._asteroids.pop(asteroid_id, None)
            if ast is None:
                return {"ok": False, "error": f"Asteroid not found: {asteroid_id}"}
            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.ASTEROID_REMOVED.value,
                description=f"Asteroid removed: {ast.name}",
                body_id=asteroid_id,
            )
            return {"ok": True, "asteroid": ast.to_dict()}

    # ------------------------------------------------------------------
    # Space Station Management
    # ------------------------------------------------------------------

    def register_space_station(self, station_id: Optional[str] = None,
                               name: str = "",
                               parent_id: Optional[str] = None,
                               mass_kg: float = 100000.0,
                               position: Optional[Sequence[float]] = None,
                               velocity: Optional[Sequence[float]] = None,
                               crew_capacity: int = 0,
                               crew_count: int = 0,
                               fuel_kg: float = 1000.0,
                               orbit_altitude_m: float = 0.0,
                               modules: Optional[List[str]] = None,
                               description: str = "",
                               **kwargs: Any) -> Dict[str, Any]:
        """Register a new space station in the system.

        If station_id is not provided, one is generated automatically.
        Returns a dictionary with the station_id and created station data.
        """
        with self._lock_local:
            sid = _gen_id("sta", station_id)
            if sid in self._stations:
                return {"ok": False, "error": f"Station already exists: {sid}"}
            if len(self._stations) >= self._config.max_stations:
                return {"ok": False, "error": "Maximum station capacity reached"}

            pos = _list_to_v(position) if position else (0.0, 0.0, 0.0)
            vel = _list_to_v(velocity) if velocity else (0.0, 0.0, 0.0)

            station = SpaceStation(
                station_id=sid,
                name=name or f"Station-{sid[-6:]}",
                parent_id=parent_id,
                mass_kg=mass_kg,
                position=pos,
                velocity=vel,
                crew_capacity=crew_capacity,
                crew_count=crew_count,
                fuel_kg=fuel_kg,
                status=kwargs.get("status", BodyStatus.ACTIVE.value),
                orbit_altitude_m=orbit_altitude_m,
                modules=modules or [],
                description=description,
                created_at=_now(),
                updated_at=_now(),
            )
            self._stations[sid] = station
            self._station_counter += 1
            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.STATION_REGISTERED.value,
                description=f"Space station registered: {station.name}",
                body_id=sid,
            )
            return {"ok": True, "station_id": sid, "station": station.to_dict()}

    def get_space_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Return the space station with the given id, or None if not found."""
        with self._lock_local:
            st = self._stations.get(station_id)
            if st is None:
                return None
            return st.to_dict()

    def list_space_stations(self, parent_id: Optional[str] = None,
                            status: Optional[str] = None,
                            limit: int = 100,
                            offset: int = 0) -> List[Dict[str, Any]]:
        """List space stations with optional filtering by parent or status."""
        with self._lock_local:
            results: List[Dict[str, Any]] = []
            for st in self._stations.values():
                if parent_id is not None and st.parent_id != parent_id:
                    continue
                if status is not None and st.status != status:
                    continue
                results.append(st.to_dict())
            results = results[offset:offset + limit]
            return results

    def update_space_station(self, station_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Update attributes of an existing space station."""
        with self._lock_local:
            st = self._stations.get(station_id)
            if st is None:
                return {"ok": False, "error": f"Station not found: {station_id}"}

            allowed_fields = {
                "name", "parent_id", "mass_kg", "crew_capacity", "crew_count",
                "fuel_kg", "status", "orbit_altitude_m", "modules", "description",
            }
            changed = False
            for k, v in kwargs.items():
                if k in allowed_fields and hasattr(st, k):
                    setattr(st, k, v)
                    changed = True
                elif k == "position" and v is not None:
                    st.position = _list_to_v(v)
                    changed = True
                elif k == "velocity" and v is not None:
                    st.velocity = _list_to_v(v)
                    changed = True

            if changed:
                st.updated_at = _now()
                self._record_event(
                    OrbitalEventKind.BODY_UPDATED.value,
                    description=f"Station updated: {st.name}",
                    body_id=station_id,
                )
            return {"ok": True, "station": st.to_dict()}

    def remove_space_station(self, station_id: str) -> Dict[str, Any]:
        """Remove a space station from the system and return its data."""
        with self._lock_local:
            st = self._stations.pop(station_id, None)
            if st is None:
                return {"ok": False, "error": f"Station not found: {station_id}"}
            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.STATION_REMOVED.value,
                description=f"Station removed: {st.name}",
                body_id=station_id,
            )
            return {"ok": True, "station": st.to_dict()}

    # ------------------------------------------------------------------
    # Thruster Management
    # ------------------------------------------------------------------

    def register_thruster(self, thruster_id: Optional[str] = None,
                          name: str = "",
                          thruster_type: str = ThrusterType.CHEMICAL.value,
                          thrust_n: float = 0.0,
                          isp_s: float = 300.0,
                          fuel_consumption_kg_s: float = 0.0,
                          max_burn_time_s: float = 0.0,
                          mass_kg: float = 0.0,
                          description: str = "",
                          **kwargs: Any) -> Dict[str, Any]:
        """Register a new thruster in the system.

        If thruster_id is not provided, one is generated automatically.
        Returns a dictionary with the thruster_id and created thruster data.
        """
        with self._lock_local:
            tid = _gen_id("thr", thruster_id)
            if tid in self._thrusters:
                return {"ok": False, "error": f"Thruster already exists: {tid}"}
            if len(self._thrusters) >= _MAX_THRUSTERS:
                return {"ok": False, "error": "Maximum thruster capacity reached"}

            # Auto-compute fuel consumption from thrust and Isp if not provided
            if fuel_consumption_kg_s <= 0.0 and isp_s > 0.0 and thrust_n > 0.0:
                # mdot = F / (Isp * g0)
                fuel_consumption_kg_s = thrust_n / (isp_s * STANDARD_GRAVITY)

            thr = Thruster(
                thruster_id=tid,
                name=name or f"Thruster-{tid[-6:]}",
                thruster_type=thruster_type,
                thrust_n=thrust_n,
                isp_s=isp_s,
                fuel_consumption_kg_s=fuel_consumption_kg_s,
                max_burn_time_s=max_burn_time_s,
                mass_kg=mass_kg,
                status=kwargs.get("status", BodyStatus.ACTIVE.value),
                description=description,
                created_at=_now(),
            )
            self._thrusters[tid] = thr
            self._thruster_counter += 1
            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.THRUSTER_REGISTERED.value,
                description=f"Thruster registered: {thr.name}",
            )
            return {"ok": True, "thruster_id": tid, "thruster": thr.to_dict()}

    def get_thruster(self, thruster_id: str) -> Optional[Dict[str, Any]]:
        """Return the thruster with the given id, or None if not found."""
        with self._lock_local:
            thr = self._thrusters.get(thruster_id)
            if thr is None:
                return None
            return thr.to_dict()

    def list_thrusters(self, thruster_type: Optional[str] = None,
                       status: Optional[str] = None,
                       limit: int = 100,
                       offset: int = 0) -> List[Dict[str, Any]]:
        """List thrusters with optional filtering by type or status."""
        with self._lock_local:
            results: List[Dict[str, Any]] = []
            for thr in self._thrusters.values():
                if thruster_type is not None and thr.thruster_type != thruster_type:
                    continue
                if status is not None and thr.status != status:
                    continue
                results.append(thr.to_dict())
            results = results[offset:offset + limit]
            return results

    def remove_thruster(self, thruster_id: str) -> Dict[str, Any]:
        """Remove a thruster from the system and return its data."""
        with self._lock_local:
            thr = self._thrusters.pop(thruster_id, None)
            if thr is None:
                return {"ok": False, "error": f"Thruster not found: {thruster_id}"}
            # Remove this thruster from any satellites that have it equipped
            for sat in self._satellites.values():
                if thruster_id in sat.thruster_ids:
                    sat.thruster_ids = [t for t in sat.thruster_ids if t != thruster_id]
            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.THRUSTER_REMOVED.value,
                description=f"Thruster removed: {thr.name}",
            )
            return {"ok": True, "thruster": thr.to_dict()}

    # ------------------------------------------------------------------
    # Maneuver Management
    # ------------------------------------------------------------------

    def plan_maneuver(self, satellite_id: str,
                      maneuver_type: str = ManeuverType.HOHMANN_TRANSFER.value,
                      delta_v_m_s: float = 0.0,
                      execution_time: float = 0.0,
                      duration_s: float = 0.0,
                      thruster_id: Optional[str] = None,
                      target_orbit_id: Optional[str] = None,
                      description: str = "",
                      **kwargs: Any) -> Dict[str, Any]:
        """Plan a new orbital maneuver for a satellite.

        Computes the fuel required based on the delta-v and the satellite's
        thruster Isp using the Tsiolkovsky rocket equation.
        Returns a dictionary with the maneuver_id and planned maneuver data.
        """
        with self._lock_local:
            sat = self._satellites.get(satellite_id)
            if sat is None:
                return {"ok": False, "error": f"Satellite not found: {satellite_id}"}

            mid = _gen_id("man", kwargs.get("maneuver_id"))
            if mid in self._maneuvers:
                return {"ok": False, "error": f"Maneuver already exists: {mid}"}
            if len(self._maneuvers) >= _MAX_MANEUVERS:
                return {"ok": False, "error": "Maximum maneuver capacity reached"}

            # Determine Isp from thruster or satellite default
            isp = sat.isp_s
            if thruster_id and thruster_id in self._thrusters:
                isp = self._thrusters[thruster_id].isp_s

            # Compute fuel required using Tsiolkovsky rocket equation
            # delta_v = Isp * g0 * ln(m0 / m1)
            # m1 = m0 / exp(delta_v / (Isp * g0))
            # fuel = m0 - m1 = m0 * (1 - 1/exp(...))
            fuel_required = 0.0
            if isp > 0.0 and delta_v_m_s > 0.0:
                mass_ratio = math.exp(delta_v_m_s / (isp * STANDARD_GRAVITY))
                fuel_required = sat.mass_kg * (1.0 - 1.0 / mass_ratio)

            maneuver = Maneuver(
                maneuver_id=mid,
                satellite_id=satellite_id,
                maneuver_type=maneuver_type,
                delta_v_m_s=delta_v_m_s,
                execution_time=execution_time,
                duration_s=duration_s,
                fuel_required_kg=fuel_required,
                thruster_id=thruster_id,
                target_orbit_id=target_orbit_id,
                status="planned",
                description=description,
                created_at=_now(),
            )
            self._maneuvers[mid] = maneuver
            self._maneuver_counter += 1
            self._update_stats_counts()
            self._record_event(
                OrbitalEventKind.MANEUVER_PLANNED.value,
                description=f"Maneuver planned for {sat.name}: {maneuver_type}",
                satellite_id=satellite_id,
                maneuver_id=mid,
                delta_v_m_s=delta_v_m_s,
                fuel_required_kg=fuel_required,
            )
            return {"ok": True, "maneuver_id": mid, "maneuver": maneuver.to_dict()}

    def execute_maneuver(self, maneuver_id: str) -> Dict[str, Any]:
        """Execute a planned maneuver, applying delta-v to the satellite.

        Consumes fuel from the satellite and updates its velocity vector.
        Returns a dictionary with the execution result.
        """
        with self._lock_local:
            maneuver = self._maneuvers.get(maneuver_id)
            if maneuver is None:
                return {"ok": False, "error": f"Maneuver not found: {maneuver_id}"}
            if maneuver.status == "executed":
                return {"ok": False, "error": "Maneuver already executed"}
            if maneuver.status == "canceled":
                return {"ok": False, "error": "Maneuver was canceled"}

            sat = self._satellites.get(maneuver.satellite_id)
            if sat is None:
                return {"ok": False, "error": "Satellite not found for maneuver"}

            # Check fuel availability
            if sat.fuel_kg < maneuver.fuel_required_kg:
                self._record_event(
                    OrbitalEventKind.FUEL_DEPLETED.value,
                    description=f"Insufficient fuel for maneuver {maneuver_id}",
                    satellite_id=sat.satellite_id,
                )
                return {"ok": False, "error": "Insufficient fuel for maneuver"}

            # Determine thrust direction: along current velocity vector (prograde)
            v_dir = _vnormalize(sat.velocity)
            if _vlen(v_dir) < 1e-9:
                # If velocity is zero, use position vector from parent
                if sat.parent_id and sat.parent_id in self._bodies:
                    parent = self._bodies[sat.parent_id]
                    v_dir = _vnormalize(_vsub(sat.position, parent.position))
                else:
                    v_dir = (1.0, 0.0, 0.0)

            # Apply delta-v along the prograde direction
            dv_vec = _vscale(v_dir, maneuver.delta_v_m_s)
            new_vel = _vadd(sat.velocity, dv_vec)

            # Consume fuel and update mass
            sat.fuel_kg -= maneuver.fuel_required_kg
            sat.mass_kg -= maneuver.fuel_required_kg
            sat.velocity = new_vel

            # Record result state
            maneuver.result_position = sat.position
            maneuver.result_velocity = new_vel
            maneuver.status = "executed"
            maneuver.executed_at = _now()
            sat.updated_at = _now()

            self._stats.total_maneuvers_executed += 1
            self._stats.total_delta_v_m_s += maneuver.delta_v_m_s
            self._stats.total_fuel_consumed_kg += maneuver.fuel_required_kg

            self._record_event(
                OrbitalEventKind.MANEUVER_EXECUTED.value,
                description=f"Maneuver executed: {maneuver.maneuver_type}",
                satellite_id=sat.satellite_id,
                maneuver_id=maneuver_id,
                delta_v_m_s=maneuver.delta_v_m_s,
                fuel_consumed_kg=maneuver.fuel_required_kg,
            )
            return {"ok": True, "maneuver": maneuver.to_dict()}

    def get_maneuver(self, maneuver_id: str) -> Optional[Dict[str, Any]]:
        """Return the maneuver with the given id, or None if not found."""
        with self._lock_local:
            m = self._maneuvers.get(maneuver_id)
            if m is None:
                return None
            return m.to_dict()

    def list_maneuvers(self, satellite_id: Optional[str] = None,
                       maneuver_type: Optional[str] = None,
                       status: Optional[str] = None,
                       limit: int = 100,
                       offset: int = 0) -> List[Dict[str, Any]]:
        """List maneuvers with optional filtering by satellite, type, or status."""
        with self._lock_local:
            results: List[Dict[str, Any]] = []
            for m in self._maneuvers.values():
                if satellite_id is not None and m.satellite_id != satellite_id:
                    continue
                if maneuver_type is not None and m.maneuver_type != maneuver_type:
                    continue
                if status is not None and m.status != status:
                    continue
                results.append(m.to_dict())
            results = results[offset:offset + limit]
            return results

    def cancel_maneuver(self, maneuver_id: str) -> Dict[str, Any]:
        """Cancel a planned maneuver that has not yet been executed."""
        with self._lock_local:
            m = self._maneuvers.get(maneuver_id)
            if m is None:
                return {"ok": False, "error": f"Maneuver not found: {maneuver_id}"}
            if m.status == "executed":
                return {"ok": False, "error": "Cannot cancel an executed maneuver"}
            m.status = "canceled"
            self._record_event(
                OrbitalEventKind.MANEUVER_CANCELED.value,
                description=f"Maneuver canceled: {m.maneuver_type}",
                satellite_id=m.satellite_id,
                maneuver_id=maneuver_id,
            )
            return {"ok": True, "maneuver": m.to_dict()}

    # ------------------------------------------------------------------
    # Physics Computations
    # ------------------------------------------------------------------

    def compute_gravity(self, mass1_kg: float, mass2_kg: float,
                        distance_m: float) -> float:
        """Compute the gravitational force between two masses.

        Uses Newton's law of universal gravitation:
            F = G * m1 * m2 / r^2
        Returns the force magnitude in Newtons.
        """
        if distance_m < self._config.gravity_softening_m:
            distance_m = self._config.gravity_softening_m
        return GRAVITATIONAL_CONSTANT * mass1_kg * mass2_kg / (distance_m * distance_m)

    def compute_velocity(self, semi_major_axis_m: float, distance_m: float,
                         parent_mass_kg: float) -> float:
        """Compute orbital speed at a given distance using the vis-viva equation.

        v^2 = GM * (2/r - 1/a)
        Returns the velocity magnitude in meters per second.
        """
        mu = GRAVITATIONAL_CONSTANT * parent_mass_kg
        if mu <= 0 or distance_m <= 0:
            return 0.0
        v_sq = mu * (2.0 / distance_m - 1.0 / semi_major_axis_m)
        if v_sq < 0.0:
            return 0.0
        return math.sqrt(v_sq)

    def compute_escape_velocity(self, parent_mass_kg: float,
                                distance_m: float) -> float:
        """Compute the escape velocity at a given distance from a mass.

        v_esc = sqrt(2 * G * M / r)
        Returns the escape velocity in meters per second.
        """
        mu = GRAVITATIONAL_CONSTANT * parent_mass_kg
        if mu <= 0 or distance_m <= 0:
            return 0.0
        return math.sqrt(2.0 * mu / distance_m)

    def compute_orbital_velocity(self, parent_mass_kg: float,
                                 distance_m: float) -> float:
        """Compute the circular orbit velocity at a given distance.

        v_circ = sqrt(G * M / r)
        Returns the velocity in meters per second.
        """
        mu = GRAVITATIONAL_CONSTANT * parent_mass_kg
        if mu <= 0 or distance_m <= 0:
            return 0.0
        return math.sqrt(mu / distance_m)

    def compute_hohmann_transfer(self, r1_m: float, r2_m: float,
                                 parent_mass_kg: float) -> Dict[str, Any]:
        """Compute the parameters of a Hohmann transfer between two circular orbits.

        A Hohmann transfer is the most fuel-efficient two-impulse maneuver
        between two coplanar circular orbits. It uses an elliptical transfer
        orbit tangent to both the initial and final orbits.

        Parameters:
            r1_m: Radius of the initial circular orbit in meters.
            r2_m: Radius of the final circular orbit in meters.
            parent_mass_kg: Mass of the central body in kilograms.

        Returns a dictionary with delta_v1, delta_v2, total delta-v,
        transfer time, and transfer orbit semi-major axis.
        """
        mu = GRAVITATIONAL_CONSTANT * parent_mass_kg
        if mu <= 0 or r1_m <= 0 or r2_m <= 0:
            return {"ok": False, "error": "Invalid parameters for Hohmann transfer"}

        # Circular orbit velocities
        v1 = math.sqrt(mu / r1_m)
        v2 = math.sqrt(mu / r2_m)

        # Transfer orbit semi-major axis (average of the two radii)
        a_transfer = (r1_m + r2_m) / 2.0

        # Velocity at periapsis and apoapsis of the transfer orbit (vis-viva)
        v_transfer_peri = math.sqrt(mu * (2.0 / r1_m - 1.0 / a_transfer))
        v_transfer_apo = math.sqrt(mu * (2.0 / r2_m - 1.0 / a_transfer))

        # Delta-v at each impulse
        dv1 = abs(v_transfer_peri - v1)
        dv2 = abs(v2 - v_transfer_apo)
        dv_total = dv1 + dv2

        # Transfer time is half the orbital period of the transfer ellipse
        transfer_time = math.pi * math.sqrt(a_transfer ** 3 / mu)

        return {
            "ok": True,
            "r1_m": r1_m,
            "r2_m": r2_m,
            "v1_m_s": v1,
            "v2_m_s": v2,
            "delta_v1_m_s": dv1,
            "delta_v2_m_s": dv2,
            "delta_v_total_m_s": dv_total,
            "transfer_time_s": transfer_time,
            "transfer_semi_major_axis_m": a_transfer,
            "transfer_apoapsis_m": max(r1_m, r2_m),
            "transfer_periapsis_m": min(r1_m, r2_m),
        }

    def compute_sphere_of_influence(self, body_mass_kg: float,
                                    parent_mass_kg: float,
                                    semi_major_axis_m: float) -> float:
        """Compute the Laplace sphere of influence radius.

        r_SOI = a * (m / M)^(2/5)
        Returns the sphere of influence radius in meters.
        """
        if parent_mass_kg <= 0 or semi_major_axis_m <= 0:
            return 0.0
        ratio = body_mass_kg / parent_mass_kg
        return semi_major_axis_m * (ratio ** 0.4)

    def compute_delta_v(self, isp_s: float, mass_initial_kg: float,
                        mass_final_kg: float) -> float:
        """Compute the delta-v from the Tsiolkovsky rocket equation.

        delta_v = Isp * g0 * ln(m0 / m1)
        Returns the delta-v in meters per second.
        """
        if isp_s <= 0 or mass_initial_kg <= 0 or mass_final_kg <= 0:
            return 0.0
        if mass_final_kg >= mass_initial_kg:
            return 0.0
        return isp_s * STANDARD_GRAVITY * math.log(mass_initial_kg / mass_final_kg)

    def compute_specific_orbital_energy(self, semi_major_axis_m: float,
                                        parent_mass_kg: float) -> float:
        """Compute the specific orbital energy.

        epsilon = -GM / (2 * a)
        Returns the specific energy in Joules per kilogram.
        """
        mu = GRAVITATIONAL_CONSTANT * parent_mass_kg
        if semi_major_axis_m <= 0:
            return 0.0
        return -mu / (2.0 * semi_major_axis_m)

    def compute_inclination(self, position: Sequence[float],
                            velocity: Sequence[float],
                            parent_position: Optional[Sequence[float]] = None,
                            parent_velocity: Optional[Sequence[float]] = None
                            ) -> float:
        """Compute orbital inclination from state vectors.

        The inclination is the angle between the orbital angular momentum
        vector and the z-axis of the inertial frame. Returns radians.
        """
        r = _list_to_v(position)
        v = _list_to_v(velocity)
        if parent_position is not None:
            r = _vsub(r, _list_to_v(parent_position))
        if parent_velocity is not None:
            v = _vsub(v, _list_to_v(parent_velocity))

        h = _vcross(r, v)
        h_mag = _vlen(h)
        if h_mag < 1e-9:
            return 0.0
        return math.acos(_clamp(h[2] / h_mag, -1.0, 1.0))

    def compute_orbital_elements(self, position: Sequence[float],
                                 velocity: Sequence[float],
                                 parent_mass_kg: float,
                                 parent_position: Optional[Sequence[float]] = None,
                                 parent_velocity: Optional[Sequence[float]] = None
                                 ) -> Dict[str, Any]:
        """Compute all six Keplerian orbital elements from state vectors.

        Returns a dictionary with semi_major_axis_m, eccentricity,
        inclination_rad, longitude_ascending_node_rad,
        argument_of_periapsis_rad, and true_anomaly_rad.
        """
        r_vec = _list_to_v(position)
        v_vec = _list_to_v(velocity)
        if parent_position is not None:
            r_vec = _vsub(r_vec, _list_to_v(parent_position))
        if parent_velocity is not None:
            v_vec = _vsub(v_vec, _list_to_v(parent_velocity))

        r = _vlen(r_vec)
        v = _vlen(v_vec)
        mu = GRAVITATIONAL_CONSTANT * parent_mass_kg

        if r < 1e-3 or mu <= 0:
            return {"ok": False, "error": "Degenerate state vectors"}

        h_vec = _vcross(r_vec, v_vec)
        h = _vlen(h_vec)
        if h < 1e-9:
            return {"ok": False, "error": "Degenerate angular momentum"}

        energy = v * v / 2.0 - mu / r
        a = -mu / (2.0 * energy) if abs(energy) > 1e-6 else float('inf')

        e_vec = _vsub(_vscale(_vcross(v_vec, h_vec), 1.0 / mu), _vscale(r_vec, 1.0 / r))
        e = _vlen(e_vec)

        inc = math.acos(_clamp(h_vec[2] / h, -1.0, 1.0))

        n_vec = _vcross((0.0, 0.0, 1.0), h_vec)
        n = _vlen(n_vec)

        if n < 1e-6:
            omega_big = 0.0
        else:
            omega_big = math.acos(_clamp(n_vec[0] / n, -1.0, 1.0))
            if n_vec[1] < 0:
                omega_big = 2.0 * math.pi - omega_big

        if e < 1e-6 or n < 1e-6:
            omega_small = 0.0
        else:
            omega_small = math.acos(_clamp(_vdot(n_vec, e_vec) / (n * e), -1.0, 1.0))
            if e_vec[2] < 0:
                omega_small = 2.0 * math.pi - omega_small

        if e < 1e-6:
            nu = 0.0
        else:
            nu = math.acos(_clamp(_vdot(e_vec, r_vec) / (e * r), -1.0, 1.0))
            if _vdot(r_vec, v_vec) < 0:
                nu = 2.0 * math.pi - nu

        return {
            "ok": True,
            "semi_major_axis_m": a,
            "eccentricity": e,
            "inclination_rad": inc,
            "longitude_ascending_node_rad": omega_big,
            "argument_of_periapsis_rad": omega_small,
            "true_anomaly_rad": nu,
            "specific_orbital_energy_jkg": energy,
            "specific_angular_momentum_m2s": h,
        }

    def compute_geostationary_orbit(self, parent_mass_kg: float,
                                    parent_rotation_period_s: float) -> Dict[str, Any]:
        """Compute the geostationary orbit altitude for a body.

        A geostationary orbit has a period matching the body's rotation
        period, keeping the satellite above a fixed point on the equator.

        Returns a dictionary with altitude, orbital radius, and velocity.
        """
        if parent_mass_kg <= 0 or parent_rotation_period_s <= 0:
            return {"ok": False, "error": "Invalid parameters"}

        mu = GRAVITATIONAL_CONSTANT * parent_mass_kg
        # From Kepler's third law: a = (mu * T^2 / (4*pi^2))^(1/3)
        a = (mu * parent_rotation_period_s ** 2 / (4.0 * math.pi * math.pi)) ** (1.0 / 3.0)
        v = math.sqrt(mu / a)
        return {
            "ok": True,
            "orbital_radius_m": a,
            "orbital_velocity_m_s": v,
            "orbital_period_s": parent_rotation_period_s,
        }

    def compute_tidal_force(self, body_mass_kg: float, body_radius_m: float,
                            parent_mass_kg: float,
                            distance_m: float) -> float:
        """Compute the tidal force across a body due to a parent mass.

        The tidal force arises from the gradient of gravitational acceleration
        across the body's diameter:
            F_tidal = 2 * G * M_parent * m_body * R_body / r^3
        Returns the tidal force magnitude in Newtons.
        """
        if distance_m <= 0 or body_radius_m <= 0:
            return 0.0
        return (2.0 * GRAVITATIONAL_CONSTANT * parent_mass_kg * body_mass_kg
                * body_radius_m / (distance_m ** 3))

    # ------------------------------------------------------------------
    # Trajectory Computation and Propagation
    # ------------------------------------------------------------------

    def compute_trajectory(self, body_id: str, steps: int = 0,
                           step_s: float = 0.0,
                           description: str = "") -> Dict[str, Any]:
        """Compute a predicted trajectory for a body using Keplerian propagation.

        Propagates the body's orbit forward in time, sampling positions at
        regular intervals. For two-body dynamics, this uses the analytic
        Kepler equation solver rather than numerical integration.
        Returns a dictionary with the trajectory_id and sampled points.
        """
        with self._lock_local:
            body = self._bodies.get(body_id)
            if body is None:
                # Check satellites and asteroids
                sat = self._satellites.get(body_id)
                if sat is not None:
                    pos, vel = sat.position, sat.velocity
                    parent_id = sat.parent_id
                else:
                    ast = self._asteroids.get(body_id)
                    if ast is not None:
                        pos, vel = ast.position, ast.velocity
                        parent_id = ast.parent_id
                    else:
                        return {"ok": False, "error": f"Body not found: {body_id}"}
            else:
                pos, vel = body.position, body.velocity
                parent_id = body.parent_id

            if parent_id is None or parent_id not in self._bodies:
                return {"ok": False, "error": "No parent body for trajectory computation"}

            parent = self._bodies[parent_id]
            mu = GRAVITATIONAL_CONSTANT * parent.mass_kg

            n_steps = steps if steps > 0 else self._config.trajectory_steps
            dt = step_s if step_s > 0 else self._config.trajectory_step_s

            # Compute orbital elements from current state
            r_vec = _vsub(pos, parent.position)
            v_vec = _vsub(vel, parent.velocity)
            elements = self.compute_orbital_elements(pos, vel, parent.mass_kg,
                                                     parent.position, parent.velocity)
            if not elements.get("ok"):
                return {"ok": False, "error": "Failed to compute orbital elements"}

            a = elements["semi_major_axis_m"]
            e = elements["eccentricity"]
            inc = elements["inclination_rad"]
            omega_big = elements["longitude_ascending_node_rad"]
            omega_small = elements["argument_of_periapsis_rad"]
            nu0 = elements["true_anomaly_rad"]

            if a <= 0 or a == float('inf'):
                return {"ok": False, "error": "Trajectory computation requires bound orbit"}

            # Mean motion
            n = math.sqrt(mu / (a ** 3))

            # Current mean anomaly
            M0 = _mean_anomaly_from_true(nu0, e)

            # Generate trajectory points
            points: List[Vec3] = []
            times: List[float] = []
            velocities: List[Vec3] = []

            for i in range(n_steps):
                t = i * dt
                M = M0 + n * t
                # Solve Kepler's equation for eccentric anomaly
                E = _solve_kepler(M, e)
                # True anomaly
                nu = _true_anomaly_from_eccentric(E, e)
                # Radius
                r = a * (1.0 - e * math.cos(E))
                # Position in orbital plane
                x_orb = r * math.cos(nu)
                y_orb = r * math.sin(nu)
                # Velocity in orbital plane (from vis-viva and geometry)
                v_radial = math.sqrt(mu / a) * (e * math.sin(nu)) / math.sqrt(1.0 - e * e)
                v_tangential = math.sqrt(mu / a) * (1.0 + e * math.cos(nu)) / math.sqrt(1.0 - e * e)
                vx_orb = v_radial * math.cos(nu) - v_tangential * math.sin(nu)
                vy_orb = v_radial * math.sin(nu) + v_tangential * math.cos(nu)

                # Rotate from orbital plane to 3D inertial frame
                cos_w = math.cos(omega_small)
                sin_w = math.sin(omega_small)
                cos_O = math.cos(omega_big)
                sin_O = math.sin(omega_big)
                cos_i = math.cos(inc)
                sin_i = math.sin(inc)

                # Rotation: argument of periapsis, inclination, longitude of ascending node
                x1 = cos_w * x_orb - sin_w * y_orb
                y1 = sin_w * x_orb + cos_w * y_orb
                x2 = x1
                y2 = cos_i * y1
                z2 = sin_i * y1
                x3 = cos_O * x2 - sin_O * y2
                y3 = sin_O * x2 + cos_O * y2
                z3 = z2

                # Translate to parent position
                point = _vadd(parent.position, (x3, y3, z3))

                # Rotate velocity the same way
                vx1 = cos_w * vx_orb - sin_w * vy_orb
                vy1 = sin_w * vx_orb + cos_w * vy_orb
                vx2 = vx1
                vy2 = cos_i * vy1
                vz2 = sin_i * vy1
                vx3 = cos_O * vx2 - sin_O * vy2
                vy3 = sin_O * vx2 + cos_O * vy2
                vz3 = vz2
                vel_point = _vadd(parent.velocity, (vx3, vy3, vz3))

                points.append(point)
                times.append(t)
                velocities.append(vel_point)

            tid = f"traj_{uuid.uuid4().hex[:12]}"
            trajectory = Trajectory(
                trajectory_id=tid,
                body_id=body_id,
                points=points,
                times=times,
                velocities=velocities,
                start_time=self._simulation_time_s,
                end_time=self._simulation_time_s + n_steps * dt,
                step_s=dt,
                description=description or f"Trajectory for {body_id}",
                created_at=_now(),
            )
            self._trajectories[tid] = trajectory
            self._trajectory_counter += 1
            self._update_stats_counts()

            self._record_event(
                OrbitalEventKind.TRAJECTORY_COMPUTED.value,
                description=f"Trajectory computed for {body_id}",
                body_id=body_id,
                trajectory_id=tid,
                points=len(points),
            )
            return {"ok": True, "trajectory_id": tid, "trajectory": trajectory.to_dict()}

    def propagate_orbit(self, orbit_id: str, time_s: float) -> Dict[str, Any]:
        """Propagate an orbit forward by a given time and return the predicted state.

        Solves Kepler's equation to find the body's position and velocity
        at the specified time in the future.
        """
        with self._lock_local:
            orbit = self._orbits.get(orbit_id)
            if orbit is None:
                return {"ok": False, "error": f"Orbit not found: {orbit_id}"}

            parent = self._bodies.get(orbit.parent_id)
            body = self._bodies.get(orbit.body_id)
            if parent is None:
                return {"ok": False, "error": "Parent body not found"}

            mu = GRAVITATIONAL_CONSTANT * parent.mass_kg
            a = orbit.semi_major_axis_m
            e = orbit.eccentricity

            if a <= 0 or a == float('inf'):
                return {"ok": False, "error": "Cannot propagate unbound orbit"}

            # Mean motion
            n = math.sqrt(mu / (a ** 3))

            # Current mean anomaly from current true anomaly
            M0 = _mean_anomaly_from_true(orbit.true_anomaly_rad, e)
            # Future mean anomaly
            M = M0 + n * time_s
            # Solve for eccentric anomaly
            E = _solve_kepler(M, e)
            # True anomaly
            nu = _true_anomaly_from_eccentric(E, e)
            # Radius
            r = a * (1.0 - e * math.cos(E))

            # Position in orbital plane
            x_orb = r * math.cos(nu)
            y_orb = r * math.sin(nu)

            # Velocity in orbital plane
            p = a * (1.0 - e * e)
            h = math.sqrt(mu * p)
            vx_orb = -mu / h * math.sin(nu)
            vy_orb = mu / h * (e + math.cos(nu))

            # Rotate to inertial frame
            inc = orbit.inclination_rad
            omega_big = orbit.longitude_ascending_node_rad
            omega_small = orbit.argument_of_periapsis_rad

            cos_w = math.cos(omega_small)
            sin_w = math.sin(omega_small)
            cos_O = math.cos(omega_big)
            sin_O = math.sin(omega_big)
            cos_i = math.cos(inc)
            sin_i = math.sin(inc)

            x1 = cos_w * x_orb - sin_w * y_orb
            y1 = sin_w * x_orb + cos_w * y_orb
            x2 = x1
            y2 = cos_i * y1
            z2 = sin_i * y1
            x3 = cos_O * x2 - sin_O * y2
            y3 = sin_O * x2 + cos_O * y2
            z3 = z2

            vx1 = cos_w * vx_orb - sin_w * vy_orb
            vy1 = sin_w * vx_orb + cos_w * vy_orb
            vx2 = vx1
            vy2 = cos_i * vy1
            vz2 = sin_i * vy1
            vx3 = cos_O * vx2 - sin_O * vy2
            vy3 = sin_O * vx2 + cos_O * vy2
            vz3 = vz2

            position = _vadd(parent.position, (x3, y3, z3))
            velocity = _vadd(parent.velocity, (vx3, vy3, vz3))

            return {
                "ok": True,
                "orbit_id": orbit_id,
                "time_s": time_s,
                "position": _v_to_list(position),
                "velocity": _v_to_list(velocity),
                "true_anomaly_rad": nu,
                "distance_m": r,
                "speed_m_s": _vlen(velocity),
            }

    def predict_position(self, body_id: str, time_s: float) -> Dict[str, Any]:
        """Predict the position of a body at a future time.

        Uses the body's stored orbit for analytic propagation if available,
        otherwise falls back to computing from current state vectors.
        """
        with self._lock_local:
            # Find orbit for this body
            body_orbit: Optional[Orbit] = None
            for o in self._orbits.values():
                if o.body_id == body_id:
                    body_orbit = o
                    break

            if body_orbit is not None:
                return self.propagate_orbit(body_orbit.orbit_id, time_s)

            # No orbit stored, try to compute one from current state
            body = self._bodies.get(body_id)
            if body is None:
                sat = self._satellites.get(body_id)
                if sat is not None:
                    pos, vel = sat.position, sat.velocity
                    parent_id = sat.parent_id
                else:
                    ast = self._asteroids.get(body_id)
                    if ast is not None:
                        pos, vel = ast.position, ast.velocity
                        parent_id = ast.parent_id
                    else:
                        return {"ok": False, "error": f"Body not found: {body_id}"}
            else:
                pos, vel = body.position, body.velocity
                parent_id = body.parent_id

            if parent_id is None or parent_id not in self._bodies:
                return {"ok": False, "error": "No parent for position prediction"}

            parent = self._bodies[parent_id]
            result = self._compute_and_store_orbit(body_id, parent_id,
                                                   GRAVITATIONAL_CONSTANT * parent.mass_kg)
            if result is None:
                return {"ok": False, "error": "Failed to compute orbit for prediction"}

            return self.propagate_orbit(result.orbit_id, time_s)

    def predict_collision(self, body_id_a: str, body_id_b: str,
                          time_horizon_s: float = 86400.0,
                          steps: int = 100) -> Dict[str, Any]:
        """Predict the closest approach between two bodies over a time horizon.

        Samples both trajectories and finds the minimum distance. If the
        minimum distance is below the collision tolerance, a collision is
        predicted.
        """
        with self._lock_local:
            dt = time_horizon_s / steps
            min_dist = float('inf')
            min_dist_time = 0.0

            pos_a = self._get_entity_position(body_id_a)
            pos_b = self._get_entity_position(body_id_b)
            if pos_a is None or pos_b is None:
                return {"ok": False, "error": "Could not find both bodies"}

            for i in range(steps + 1):
                t = i * dt
                pred_a = self.predict_position(body_id_a, t)
                pred_b = self.predict_position(body_id_b, t)
                if not pred_a.get("ok") or not pred_b.get("ok"):
                    continue
                pa = _list_to_v(pred_a["position"])
                pb = _list_to_v(pred_b["position"])
                dist = _vdist(pa, pb)
                if dist < min_dist:
                    min_dist = dist
                    min_dist_time = t

            will_collide = min_dist <= self._config.collision_tolerance_m
            if will_collide:
                self._stats.total_collision_warnings += 1
                self._record_event(
                    OrbitalEventKind.COLLISION_WARNING.value,
                    description=f"Collision predicted between {body_id_a} and {body_id_b}",
                    body_id=body_id_a,
                    data={"body_b": body_id_b, "min_distance_m": min_dist,
                          "time_to_closest_s": min_dist_time},
                )

            return {
                "ok": True,
                "body_a": body_id_a,
                "body_b": body_id_b,
                "min_distance_m": min_dist,
                "time_to_closest_s": min_dist_time,
                "will_collide": will_collide,
                "collision_tolerance_m": self._config.collision_tolerance_m,
            }

    def _get_entity_position(self, entity_id: str) -> Optional[Vec3]:
        """Get the current position of any tracked entity by its id."""
        body = self._bodies.get(entity_id)
        if body is not None:
            return body.position
        sat = self._satellites.get(entity_id)
        if sat is not None:
            return sat.position
        ast = self._asteroids.get(entity_id)
        if ast is not None:
            return ast.position
        st = self._stations.get(entity_id)
        if st is not None:
            return st.position
        return None

    def _get_entity_velocity(self, entity_id: str) -> Optional[Vec3]:
        """Get the current velocity of any tracked entity by its id."""
        body = self._bodies.get(entity_id)
        if body is not None:
            return body.velocity
        sat = self._satellites.get(entity_id)
        if sat is not None:
            return sat.velocity
        ast = self._asteroids.get(entity_id)
        if ast is not None:
            return ast.velocity
        st = self._stations.get(entity_id)
        if st is not None:
            return st.velocity
        return None

    # ------------------------------------------------------------------
    # Measurements
    # ------------------------------------------------------------------

    def measure_distance(self, body_id_a: str, body_id_b: str) -> Dict[str, Any]:
        """Measure the current distance between two entities."""
        with self._lock_local:
            pos_a = self._get_entity_position(body_id_a)
            pos_b = self._get_entity_position(body_id_b)
            if pos_a is None or pos_b is None:
                return {"ok": False, "error": "One or both bodies not found"}
            dist = _vdist(pos_a, pos_b)
            return {
                "ok": True,
                "body_a": body_id_a,
                "body_b": body_id_b,
                "distance_m": dist,
            }

    def measure_velocity(self, body_id: str) -> Dict[str, Any]:
        """Measure the current speed and velocity vector of an entity."""
        with self._lock_local:
            vel = self._get_entity_velocity(body_id)
            if vel is None:
                return {"ok": False, "error": f"Body not found: {body_id}"}
            return {
                "ok": True,
                "body_id": body_id,
                "velocity": _v_to_list(vel),
                "speed_m_s": _vlen(vel),
            }

    def get_orbital_map(self, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a hierarchical map of bodies and their children.

        If parent_id is specified, only children of that body are included.
        Otherwise, the full hierarchy starting from root bodies is returned.
        """
        with self._lock_local:
            # Build parent-to-children mapping for all entity types
            children_map: Dict[str, List[Dict[str, Any]]] = {}
            root_bodies: List[Dict[str, Any]] = []

            for body in self._bodies.values():
                entry = {
                    "id": body.body_id,
                    "name": body.name,
                    "type": body.body_type,
                    "mass_kg": body.mass_kg,
                    "radius_m": body.radius_m,
                    "parent_id": body.parent_id,
                    "position": _v_to_list(body.position),
                    "color": body.color,
                    "children": [],
                }
                if body.parent_id is None:
                    root_bodies.append(entry)
                else:
                    children_map.setdefault(body.parent_id, []).append(entry)

            # Recursively attach children
            def attach_children(node: Dict[str, Any]) -> None:
                node["children"] = children_map.get(node["id"], [])
                for child in node["children"]:
                    attach_children(child)

            for root in root_bodies:
                attach_children(root)

            if parent_id is not None:
                # Return only the subtree rooted at parent_id
                for root in root_bodies:
                    if root["id"] == parent_id:
                        return {"ok": True, "map": root}
                    # Search in children
                    found = self._find_in_map(root, parent_id)
                    if found is not None:
                        return {"ok": True, "map": found}
                return {"ok": False, "error": f"Parent body not found: {parent_id}"}

            return {"ok": True, "map": root_bodies}

    def _find_in_map(self, node: Dict[str, Any], target_id: str) -> Optional[Dict[str, Any]]:
        """Recursively search for a node by id in the orbital map tree."""
        if node["id"] == target_id:
            return node
        for child in node.get("children", []):
            found = self._find_in_map(child, target_id)
            if found is not None:
                return found
        return None

    def get_trajectory_data(self, trajectory_id: str) -> Optional[Dict[str, Any]]:
        """Return the full trajectory data for a given trajectory id."""
        with self._lock_local:
            traj = self._trajectories.get(trajectory_id)
            if traj is None:
                return None
            return traj.to_dict()

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def ai_predict_trajectory(self, body_id: str, time_horizon_s: float = 3600.0,
                              confidence: float = 0.95) -> Dict[str, Any]:
        """Predict a body's future trajectory using analytic propagation.

        Uses Keplerian orbital mechanics to compute the body's path over the
        specified time horizon. The confidence parameter adjusts the number
        of sample points, trading computation for precision.

        Returns a dictionary with predicted positions, velocities, and
        metadata about the prediction including the orbital elements used.
        """
        with self._lock_local:
            # Determine sample count from confidence
            base_steps = 100
            n_steps = max(50, int(base_steps * confidence))
            dt = time_horizon_s / n_steps

            result = self.compute_trajectory(body_id, steps=n_steps, step_s=dt,
                                             description=f"AI trajectory prediction for {body_id}")
            if not result.get("ok"):
                return result

            trajectory = result["trajectory"]
            # Compute additional metadata
            body = self._bodies.get(body_id)
            parent_id = body.parent_id if body else None
            parent = self._bodies.get(parent_id) if parent_id else None

            metadata = {
                "method": "keplerian_analytic",
                "confidence": confidence,
                "time_horizon_s": time_horizon_s,
                "sample_count": len(trajectory["points"]),
                "parent_body": parent_id,
                "parent_mass_kg": parent.mass_kg if parent else 0.0,
            }

            # Identify key trajectory events (apoapsis and periapsis crossings)
            key_events: List[Dict[str, Any]] = []
            prev_dist = None
            prev_increasing = None
            for i, point in enumerate(trajectory["points"]):
                if parent is None:
                    continue
                dist = _vdist(_list_to_v(point), parent.position)
                if prev_dist is not None:
                    increasing = dist > prev_dist
                    if prev_increasing is not None and increasing != prev_increasing:
                        event_type = "apoapsis" if prev_increasing else "periapsis"
                        key_events.append({
                            "type": event_type,
                            "time_s": trajectory["times"][i],
                            "distance_m": prev_dist,
                            "index": i - 1,
                        })
                    prev_increasing = increasing
                prev_dist = dist

            return {
                "ok": True,
                "body_id": body_id,
                "trajectory_id": result["trajectory_id"],
                "trajectory": trajectory,
                "metadata": metadata,
                "key_events": key_events,
            }

    def ai_optimize_orbit(self, satellite_id: str,
                          target_altitude_m: float,
                          strategy: str = "hohmann") -> Dict[str, Any]:
        """Find the optimal maneuver sequence to reach a target orbit.

        Analyzes the satellite's current orbit and computes the most efficient
        transfer to the target altitude. The default Hohmann strategy produces
        a two-impulse transfer, which is optimal for coplanar circular orbits.

        Returns a dictionary with the recommended maneuver plan including
        delta-v requirements, fuel costs, and transfer time.
        """
        with self._lock_local:
            sat = self._satellites.get(satellite_id)
            if sat is None:
                return {"ok": False, "error": f"Satellite not found: {satellite_id}"}
            if sat.parent_id is None or sat.parent_id not in self._bodies:
                return {"ok": False, "error": "Satellite has no valid parent body"}

            parent = self._bodies[sat.parent_id]
            mu = GRAVITATIONAL_CONSTANT * parent.mass_kg

            # Current orbital radius (distance from parent)
            r_current = _vdist(sat.position, parent.position)
            r_target = parent.radius_m + target_altitude_m

            if r_current <= 0 or r_target <= 0:
                return {"ok": False, "error": "Invalid orbital radii"}

            # Compute Hohmann transfer
            hohmann = self.compute_hohmann_transfer(r_current, r_target, parent.mass_kg)
            if not hohmann.get("ok"):
                return hohmann

            # Determine Isp
            isp = sat.isp_s
            if sat.thruster_ids and sat.thruster_ids[0] in self._thrusters:
                isp = self._thrusters[sat.thruster_ids[0]].isp_s

            # Compute fuel required for each impulse
            def fuel_for_dv(dv: float, m0: float) -> float:
                if isp <= 0 or dv <= 0:
                    return 0.0
                ratio = math.exp(dv / (isp * STANDARD_GRAVITY))
                return m0 * (1.0 - 1.0 / ratio)

            fuel1 = fuel_for_dv(hohmann["delta_v1_m_s"], sat.mass_kg)
            fuel2 = fuel_for_dv(hohmann["delta_v2_m_s"], sat.mass_kg - fuel1)
            total_fuel = fuel1 + fuel2

            # Check if satellite has enough fuel
            fuel_sufficient = sat.fuel_kg >= total_fuel

            # Determine if raising or lowering orbit
            direction = "raise" if r_target > r_current else "lower"
            maneuver_type = (ManeuverType.ORBIT_RAISE.value if direction == "raise"
                             else ManeuverType.ORBIT_LOWER.value)

            # Build recommended maneuver plan
            plan = [
                {
                    "step": 1,
                    "name": f"Transfer burn ({direction} orbit)",
                    "delta_v_m_s": hohmann["delta_v1_m_s"],
                    "fuel_kg": fuel1,
                    "description": "First impulse to enter transfer ellipse",
                    "maneuver_type": maneuver_type,
                },
                {
                    "step": 2,
                    "name": "Circularization burn",
                    "delta_v_m_s": hohmann["delta_v2_m_s"],
                    "fuel_kg": fuel2,
                    "description": "Second impulse to circularize at target orbit",
                    "maneuver_type": ManeuverType.CIRCULARIZE.value,
                    "delay_s": hohmann["transfer_time_s"],
                },
            ]

            return {
                "ok": True,
                "satellite_id": satellite_id,
                "strategy": strategy,
                "current_radius_m": r_current,
                "target_radius_m": r_target,
                "current_altitude_m": r_current - parent.radius_m,
                "target_altitude_m": target_altitude_m,
                "direction": direction,
                "total_delta_v_m_s": hohmann["delta_v_total_m_s"],
                "total_fuel_kg": total_fuel,
                "fuel_available_kg": sat.fuel_kg,
                "fuel_sufficient": fuel_sufficient,
                "transfer_time_s": hohmann["transfer_time_s"],
                "maneuver_plan": plan,
                "isp_s": isp,
            }

    def ai_assess_collision_risk(self, body_id: str,
                                 time_horizon_s: float = 86400.0,
                                 threat_bodies: Optional[List[str]] = None
                                 ) -> Dict[str, Any]:
        """Assess the collision risk for a body against all or specified threats.

        Propagates trajectories and computes closest approaches. Each threat
        is assigned a risk level based on the minimum distance relative to
        the collision tolerance.

        Returns a dictionary with per-threat risk assessments and an overall
        risk summary.
        """
        with self._lock_local:
            # Determine the set of threat bodies to check
            if threat_bodies is None:
                # Check against all other bodies, satellites, and asteroids
                threat_bodies = []
                for bid in self._bodies:
                    if bid != body_id:
                        threat_bodies.append(bid)
                for sid in self._satellites:
                    if sid != body_id:
                        threat_bodies.append(sid)
                for aid in self._asteroids:
                    if aid != body_id:
                        threat_bodies.append(aid)

            assessments: List[Dict[str, Any]] = []
            high_risk_count = 0
            medium_risk_count = 0
            low_risk_count = 0
            min_distance = float('inf')
            most_dangerous: Optional[str] = None

            for threat_id in threat_bodies:
                prediction = self.predict_collision(body_id, threat_id, time_horizon_s,
                                                    steps=50)
                if not prediction.get("ok"):
                    continue

                dist = prediction["min_distance_m"]
                tolerance = self._config.collision_tolerance_m

                if dist <= tolerance:
                    risk_level = "critical"
                    high_risk_count += 1
                elif dist <= tolerance * 10:
                    risk_level = "high"
                    high_risk_count += 1
                elif dist <= tolerance * 100:
                    risk_level = "medium"
                    medium_risk_count += 1
                else:
                    risk_level = "low"
                    low_risk_count += 1

                assessments.append({
                    "threat_id": threat_id,
                    "min_distance_m": dist,
                    "time_to_closest_s": prediction["time_to_closest_s"],
                    "will_collide": prediction["will_collide"],
                    "risk_level": risk_level,
                })

                if dist < min_distance:
                    min_distance = dist
                    most_dangerous = threat_id

            # Sort assessments by distance (closest first)
            assessments.sort(key=lambda a: a["min_distance_m"])

            # Determine overall risk level
            if high_risk_count > 0:
                overall_risk = "high"
            elif medium_risk_count > 0:
                overall_risk = "medium"
            else:
                overall_risk = "low"

            return {
                "ok": True,
                "body_id": body_id,
                "time_horizon_s": time_horizon_s,
                "threats_assessed": len(assessments),
                "overall_risk": overall_risk,
                "high_risk_count": high_risk_count,
                "medium_risk_count": medium_risk_count,
                "low_risk_count": low_risk_count,
                "min_distance_m": min_distance if min_distance != float('inf') else 0.0,
                "most_dangerous_threat": most_dangerous,
                "assessments": assessments,
            }

    # ------------------------------------------------------------------
    # System Methods
    # ------------------------------------------------------------------

    def get_config(self) -> Dict[str, Any]:
        """Return the current system configuration."""
        with self._lock_local:
            return self._config.to_dict()

    def set_config(self, **kwargs: Any) -> Dict[str, Any]:
        """Update system configuration fields.

        Only provided keyword arguments are applied; all other fields remain
        unchanged. Returns the updated configuration.
        """
        with self._lock_local:
            changed_fields: List[str] = []
            for k, v in kwargs.items():
                if hasattr(self._config, k):
                    setattr(self._config, k, v)
                    changed_fields.append(k)
            if changed_fields:
                self._record_event(
                    OrbitalEventKind.CONFIG_UPDATED.value,
                    description=f"Configuration updated: {', '.join(changed_fields)}",
                    fields=changed_fields,
                )
            return {"ok": True, "config": self._config.to_dict(),
                    "changed_fields": changed_fields}

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the system.

        Includes initialization state, seed state, tick count, simulation
        time, entity counts, and wall-clock uptime.
        """
        with self._lock_local:
            now = _now()
            wall_uptime = now - self._sim_start_wall if self._sim_start_wall > 0 else 0.0
            return {
                "ok": True,
                "initialized": self._initialized,
                "seeded": self._seeded,
                "tick_count": self._tick_count,
                "simulation_time_s": self._simulation_time_s,
                "wall_uptime_s": wall_uptime,
                "time_scale": self._config.time_scale,
                "integration_method": self._config.integration_method,
                "entity_counts": {
                    "bodies": len(self._bodies),
                    "orbits": len(self._orbits),
                    "satellites": len(self._satellites),
                    "asteroids": len(self._asteroids),
                    "stations": len(self._stations),
                    "thrusters": len(self._thrusters),
                    "maneuvers": len(self._maneuvers),
                    "trajectories": len(self._trajectories),
                    "events": len(self._events),
                },
            }

    def get_stats(self) -> Dict[str, Any]:
        """Return accumulated statistics for the orbital mechanics system."""
        with self._lock_local:
            self._stats.total_ticks = self._tick_count
            self._stats.simulation_time_s = self._simulation_time_s
            self._stats.wall_time_s = _now() - self._sim_start_wall
            return self._stats.to_dict()

    def get_snapshot(self) -> Dict[str, Any]:
        """Capture a point-in-time snapshot of the entire orbital system state.

        The snapshot includes all bodies, satellites, asteroids, stations,
        and maneuvers serialized as dictionaries.
        """
        with self._lock_local:
            snapshot = OrbitalSnapshot(
                snapshot_id=f"snap_{uuid.uuid4().hex[:12]}",
                timestamp=_now(),
                simulation_time_s=self._simulation_time_s,
                bodies=[b.to_dict() for b in self._bodies.values()],
                satellites=[s.to_dict() for s in self._satellites.values()],
                asteroids=[a.to_dict() for a in self._asteroids.values()],
                stations=[st.to_dict() for st in self._stations.values()],
                maneuvers=[m.to_dict() for m in self._maneuvers.values()],
                tick_count=self._tick_count,
            )
            return snapshot.to_dict()

    def list_events(self, kind: Optional[str] = None,
                    body_id: Optional[str] = None,
                    satellite_id: Optional[str] = None,
                    limit: int = 100,
                    offset: int = 0,
                    sort_desc: bool = True) -> List[Dict[str, Any]]:
        """List events with optional filtering by kind, body, or satellite.

        Events are returned in chronological order by default, or reverse
        chronological order if sort_desc is True.
        """
        with self._lock_local:
            results: List[OrbitalEvent] = []
            for evt in self._events:
                if kind is not None and evt.kind != kind:
                    continue
                if body_id is not None and evt.body_id != body_id:
                    continue
                if satellite_id is not None and evt.satellite_id != satellite_id:
                    continue
                results.append(evt)
            if sort_desc:
                results.reverse()
            results = results[offset:offset + limit]
            return [e.to_dict() for e in results]

    # ------------------------------------------------------------------
    # N-body Physics and Simulation Tick
    # ------------------------------------------------------------------

    def _compute_n_body_accelerations(self,
                                      bodies: List[Tuple[str, Vec3, float]]
                                      ) -> Dict[str, Vec3]:
        """Compute gravitational acceleration on each body from all others.

        Parameters:
            bodies: List of (id, position, mass) tuples for all bodies.

        Returns a mapping from body id to its acceleration vector.
        Uses gravitational softening to avoid singularities at close range.
        """
        accelerations: Dict[str, Vec3] = {}
        n = len(bodies)
        for i in range(n):
            id_i, pos_i, mass_i = bodies[i]
            acc = (0.0, 0.0, 0.0)
            for j in range(n):
                if i == j:
                    continue
                id_j, pos_j, mass_j = bodies[j]
                r_vec = _vsub(pos_j, pos_i)
                r = _vlen(r_vec)
                if r < self._config.gravity_softening_m:
                    r = self._config.gravity_softening_m
                # Acceleration magnitude: a = G * m_j / r^2
                a_mag = GRAVITATIONAL_CONSTANT * mass_j / (r * r)
                # Direction unit vector from i to j
                direction = _vscale(r_vec, 1.0 / r)
                acc = _vadd(acc, _vscale(direction, a_mag))
            accelerations[id_i] = acc
        return accelerations

    def tick(self, dt: Optional[float] = None) -> Dict[str, Any]:
        """Advance the orbital simulation by one time step.

        Performs N-body gravitational integration using the velocity-Verlet
        method, which is symplectic and conserves energy better than Euler.
        Also executes any maneuvers scheduled for the current simulation time,
        updates orbital elements, and checks for collisions.

        Parameters:
            dt: Time step in seconds. If None, uses the configured default.

        Returns a dictionary with tick results including updated positions,
        velocities, and any events triggered during the step.
        """
        with self._lock_local:
            step_start = _now()
            time_step = dt if dt is not None else self._config.dt
            time_step *= self._config.time_scale

            # Collect all dynamic entities with their state vectors
            entities: List[Tuple[str, Vec3, Vec3, float, str]] = []
            for body in self._bodies.values():
                if body.body_type == BodyType.STAR.value:
                    # Stars are fixed at the origin for stability
                    continue
                entities.append((body.body_id, body.position, body.velocity,
                                 body.mass_kg, "body"))
            for sat in self._satellites.values():
                if sat.status == BodyStatus.ACTIVE.value:
                    entities.append((sat.satellite_id, sat.position, sat.velocity,
                                     sat.mass_kg, "satellite"))
            for ast in self._asteroids.values():
                if ast.status == BodyStatus.ACTIVE.value:
                    entities.append((ast.asteroid_id, ast.position, ast.velocity,
                                     ast.mass_kg, "asteroid"))
            for st in self._stations.values():
                if st.status == BodyStatus.ACTIVE.value:
                    entities.append((st.station_id, st.position, st.velocity,
                                     st.mass_kg, "station"))

            # Build body list for acceleration computation
            n_body_list: List[Tuple[str, Vec3, float]] = [
                (eid, pos, mass) for eid, pos, vel, mass, etype in entities
            ]
            # Include the star as a gravitational source but not integrated
            for body in self._bodies.values():
                if body.body_type == BodyType.STAR.value:
                    n_body_list.append((body.body_id, body.position, body.mass_kg))

            # Velocity-Verlet integration step
            # Step 1: compute current accelerations
            acc_current = self._compute_n_body_accelerations(n_body_list)

            # Step 2: update positions: x(t+dt) = x(t) + v(t)*dt + 0.5*a(t)*dt^2
            new_positions: Dict[str, Vec3] = {}
            for eid, pos, vel, mass, etype in entities:
                a = acc_current.get(eid, (0.0, 0.0, 0.0))
                new_pos = _vadd(
                    _vadd(pos, _vscale(vel, time_step)),
                    _vscale(a, 0.5 * time_step * time_step),
                )
                new_positions[eid] = new_pos

            # Step 3: rebuild body list with new positions for new accelerations
            updated_n_body_list: List[Tuple[str, Vec3, float]] = []
            for eid, pos, vel, mass, etype in entities:
                updated_n_body_list.append((eid, new_positions[eid], mass))
            for body in self._bodies.values():
                if body.body_type == BodyType.STAR.value:
                    updated_n_body_list.append((body.body_id, body.position, body.mass_kg))

            # Step 4: compute new accelerations at updated positions
            acc_new = self._compute_n_body_accelerations(updated_n_body_list)

            # Step 5: update velocities: v(t+dt) = v(t) + 0.5*(a(t)+a(t+dt))*dt
            new_velocities: Dict[str, Vec3] = {}
            for eid, pos, vel, mass, etype in entities:
                a_old = acc_current.get(eid, (0.0, 0.0, 0.0))
                a_new = acc_new.get(eid, (0.0, 0.0, 0.0))
                avg_acc = _vscale(_vadd(a_old, a_new), 0.5)
                new_vel = _vadd(vel, _vscale(avg_acc, time_step))
                new_velocities[eid] = new_vel

            # Apply updated positions and velocities back to entities
            for eid, pos, vel, mass, etype in entities:
                new_pos = new_positions[eid]
                new_vel = new_velocities[eid]
                if etype == "body":
                    body = self._bodies.get(eid)
                    if body is not None:
                        body.position = new_pos
                        body.velocity = new_vel
                        body.updated_at = _now()
                elif etype == "satellite":
                    sat = self._satellites.get(eid)
                    if sat is not None:
                        sat.position = new_pos
                        sat.velocity = new_vel
                        sat.updated_at = _now()
                elif etype == "asteroid":
                    ast = self._asteroids.get(eid)
                    if ast is not None:
                        ast.position = new_pos
                        ast.velocity = new_vel
                        ast.updated_at = _now()
                elif etype == "station":
                    st = self._stations.get(eid)
                    if st is not None:
                        st.position = new_pos
                        st.velocity = new_vel
                        st.updated_at = _now()

            # Execute maneuvers scheduled for the current simulation time
            maneuvers_executed: List[str] = []
            for maneuver in list(self._maneuvers.values()):
                if maneuver.status != "planned":
                    continue
                if maneuver.execution_time <= self._simulation_time_s + time_step:
                    result = self.execute_maneuver(maneuver.maneuver_id)
                    if result.get("ok"):
                        maneuvers_executed.append(maneuver.maneuver_id)

            # Recompute orbits for bodies that have parents
            for body in self._bodies.values():
                if body.parent_id and body.parent_id in self._bodies:
                    parent = self._bodies[body.parent_id]
                    mu = GRAVITATIONAL_CONSTANT * parent.mass_kg
                    self._compute_and_store_orbit(body.body_id, body.parent_id, mu)

            # Collision detection
            collisions_detected: List[Dict[str, Any]] = []
            if self._config.collision_detection:
                all_positions: List[Tuple[str, Vec3, float, float]] = []
                for body in self._bodies.values():
                    all_positions.append((body.body_id, body.position,
                                          body.radius_m, body.mass_kg))
                for sat in self._satellites.values():
                    all_positions.append((sat.satellite_id, sat.position, 2.0, sat.mass_kg))
                for ast in self._asteroids.values():
                    all_positions.append((ast.asteroid_id, ast.position,
                                          ast.radius_m, ast.mass_kg))
                for st in self._stations.values():
                    all_positions.append((st.station_id, st.position, 50.0, st.mass_kg))

                for i in range(len(all_positions)):
                    for j in range(i + 1, len(all_positions)):
                        id_a, pos_a, rad_a, mass_a = all_positions[i]
                        id_b, pos_b, rad_b, mass_b = all_positions[j]
                        dist = _vdist(pos_a, pos_b)
                        min_dist = rad_a + rad_b
                        if dist <= min_dist + self._config.collision_tolerance_m:
                            collision = {
                                "body_a": id_a,
                                "body_b": id_b,
                                "distance_m": dist,
                                "min_safe_distance_m": min_dist,
                            }
                            collisions_detected.append(collision)
                            self._stats.total_collisions_detected += 1
                            self._record_event(
                                OrbitalEventKind.COLLISION_DETECTED.value,
                                description=f"Collision detected: {id_a} and {id_b}",
                                body_id=id_a,
                                data={"body_b": id_b, "distance_m": dist},
                            )

            # Update simulation time and tick count
            self._simulation_time_s += time_step
            self._tick_count += 1

            # Track tick duration for performance stats
            tick_duration = _now() - step_start
            self._stats.last_tick_duration_s = tick_duration
            self._tick_durations.append(tick_duration)
            if len(self._tick_durations) > 100:
                self._tick_durations.pop(0)
            if self._tick_durations:
                self._stats.avg_tick_duration_s = (
                    sum(self._tick_durations) / len(self._tick_durations)
                )

            self._record_event(
                OrbitalEventKind.SYSTEM_TICK.value,
                description=f"Tick {self._tick_count}: dt={time_step}s",
                data={"dt": time_step, "entities": len(entities)},
            )

            return {
                "ok": True,
                "tick": self._tick_count,
                "dt": time_step,
                "simulation_time_s": self._simulation_time_s,
                "entities_updated": len(entities),
                "maneuvers_executed": maneuvers_executed,
                "collisions_detected": collisions_detected,
                "tick_duration_s": tick_duration,
            }

    # ------------------------------------------------------------------
    # Visualization and Reset
    # ------------------------------------------------------------------

    def get_visualization_data(self, include_trajectories: bool = False,
                               include_orbits: bool = True) -> Dict[str, Any]:
        """Return data formatted for rendering the orbital system visually.

        Includes all bodies, satellites, asteroids, and stations with their
        positions, colors, and sizes. Optionally includes orbit paths and
        trajectory lines for rendering.
        """
        with self._lock_local:
            vis_bodies: List[Dict[str, Any]] = []
            for body in self._bodies.values():
                vis_bodies.append({
                    "id": body.body_id,
                    "name": body.name,
                    "type": body.body_type,
                    "position": _v_to_list(body.position),
                    "velocity": _v_to_list(body.velocity),
                    "mass_kg": body.mass_kg,
                    "radius_m": body.radius_m,
                    "color": body.color,
                    "parent_id": body.parent_id,
                    "status": body.status,
                })

            vis_satellites: List[Dict[str, Any]] = []
            for sat in self._satellites.values():
                vis_satellites.append({
                    "id": sat.satellite_id,
                    "name": sat.name,
                    "position": _v_to_list(sat.position),
                    "velocity": _v_to_list(sat.velocity),
                    "mass_kg": sat.mass_kg,
                    "fuel_kg": sat.fuel_kg,
                    "parent_id": sat.parent_id,
                    "status": sat.status,
                    "mission": sat.mission,
                })

            vis_asteroids: List[Dict[str, Any]] = []
            for ast in self._asteroids.values():
                vis_asteroids.append({
                    "id": ast.asteroid_id,
                    "name": ast.name,
                    "position": _v_to_list(ast.position),
                    "velocity": _v_to_list(ast.velocity),
                    "mass_kg": ast.mass_kg,
                    "radius_m": ast.radius_m,
                    "parent_id": ast.parent_id,
                    "hazard_level": ast.hazard_level,
                    "spectral_class": ast.spectral_class,
                })

            vis_stations: List[Dict[str, Any]] = []
            for st in self._stations.values():
                vis_stations.append({
                    "id": st.station_id,
                    "name": st.name,
                    "position": _v_to_list(st.position),
                    "velocity": _v_to_list(st.velocity),
                    "mass_kg": st.mass_kg,
                    "crew_count": st.crew_count,
                    "crew_capacity": st.crew_capacity,
                    "parent_id": st.parent_id,
                    "orbit_altitude_m": st.orbit_altitude_m,
                })

            result: Dict[str, Any] = {
                "ok": True,
                "simulation_time_s": self._simulation_time_s,
                "tick_count": self._tick_count,
                "bodies": vis_bodies,
                "satellites": vis_satellites,
                "asteroids": vis_asteroids,
                "stations": vis_stations,
                "scale": "meters",
            }

            # Optionally include orbit paths for visualization
            if include_orbits:
                vis_orbits: List[Dict[str, Any]] = []
                for orbit in self._orbits.values():
                    parent = self._bodies.get(orbit.parent_id)
                    if parent is None:
                        continue
                    # Sample orbit points by propagating through one period
                    n_samples = 60
                    orbit_points: List[List[float]] = []
                    if orbit.period_s > 0 and orbit.semi_major_axis_m > 0:
                        dt_sample = orbit.period_s / n_samples
                        for i in range(n_samples):
                            t = i * dt_sample
                            pred = self.propagate_orbit(orbit.orbit_id, t)
                            if pred.get("ok"):
                                orbit_points.append(pred["position"])
                    vis_orbits.append({
                        "orbit_id": orbit.orbit_id,
                        "body_id": orbit.body_id,
                        "parent_id": orbit.parent_id,
                        "orbit_type": orbit.orbit_type,
                        "semi_major_axis_m": orbit.semi_major_axis_m,
                        "eccentricity": orbit.eccentricity,
                        "inclination_rad": orbit.inclination_rad,
                        "period_s": orbit.period_s,
                        "apoapsis_m": orbit.apoapsis_m,
                        "periapsis_m": orbit.periapsis_m,
                        "path_points": orbit_points,
                    })
                result["orbits"] = vis_orbits

            # Optionally include trajectory lines
            if include_trajectories:
                vis_trajectories: List[Dict[str, Any]] = []
                for traj in self._trajectories.values():
                    vis_trajectories.append({
                        "trajectory_id": traj.trajectory_id,
                        "body_id": traj.body_id,
                        "points": [_v_to_list(p) for p in traj.points],
                        "start_time": traj.start_time,
                        "end_time": traj.end_time,
                    })
                result["trajectories"] = vis_trajectories

            return result

    def reset(self) -> Dict[str, Any]:
        """Reset the orbital mechanics system to its initial seeded state.

        Clears all bodies, satellites, asteroids, stations, thrusters,
        maneuvers, trajectories, and events, then re-seeds the default
        system data. The tick count and simulation time are also reset.
        """
        with self._lock_local:
            # Clear all collections
            self._bodies.clear()
            self._orbits.clear()
            self._satellites.clear()
            self._asteroids.clear()
            self._stations.clear()
            self._thrusters.clear()
            self._maneuvers.clear()
            self._trajectories.clear()
            self._events.clear()

            # Reset counters and timers
            self._tick_count = 0
            self._simulation_time_s = 0.0
            self._wall_time_s = 0.0
            self._sim_start_wall = _now()
            self._last_tick_wall = self._sim_start_wall
            self._event_counter = 0
            self._body_counter = 0
            self._orbit_counter = 0
            self._satellite_counter = 0
            self._asteroid_counter = 0
            self._station_counter = 0
            self._thruster_counter = 0
            self._maneuver_counter = 0
            self._trajectory_counter = 0
            self._tick_durations.clear()

            # Reset statistics
            self._stats = OrbitalStats()

            # Mark as not seeded and re-seed
            self._seeded = False
            self._seed()

            self._record_event(
                OrbitalEventKind.SYSTEM_RESET.value,
                description="Orbital mechanics system reset to initial state",
            )
            self._update_stats_counts()
            return {
                "ok": True,
                "reset": True,
                "initialized": self._initialized,
                "seeded": self._seeded,
                "entity_counts": {
                    "bodies": len(self._bodies),
                    "satellites": len(self._satellites),
                    "asteroids": len(self._asteroids),
                    "stations": len(self._stations),
                    "thrusters": len(self._thrusters),
                },
            }


# ---------------------------------------------------------------------------
# Module-level Factory Function
# ---------------------------------------------------------------------------

def get_orbital_mechanics_system() -> _OrbitalMechanicsSystem:
    """Return the singleton _OrbitalMechanicsSystem instance.

    This is the primary entry point for accessing the orbital mechanics
    system. The instance is created on first call and reused on subsequent
    calls, with thread-safe double-checked locking on initialization.
    """
    return _OrbitalMechanicsSystem.get_instance()