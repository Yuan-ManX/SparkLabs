"""
SparkLabs Engine - Dynamic Weather & Atmosphere System

Manages a living weather simulation across geographic zones, atmospheric
conditions, wind layers, cloud coverage, and timed weather transitions.
The system owns a registry of weather zones (each a geographic region
with its own current weather state, wind, clouds, and atmosphere), a
library of predefined weather patterns that can be applied to zones,
smooth transitions between weather states, forecasts that project a
zone's weather forward in time, and an audit trail of every lifecycle
event.

An integrated AI layer can generate a complete weather state from a
natural-language context (biome, season, time of day, mood), suggest a
weather pattern that supports a gameplay goal (combat, stealth,
exploration, racing, horror, celebration, survival), and optimize
transition durations so weather changes feel realistic rather than
abrupt.

Architecture:
  DynamicWeatherSystem (singleton)
    |-- WeatherType, WeatherIntensity, WeatherPhase, WindDirection,
       CloudCoverage, WeatherStatus, Season, FogType,
       WeatherEventKind
    |-- WindState, CloudLayer, AtmosphericConditions, WeatherState,
       WeatherZone, WeatherPattern, WeatherTransition, WeatherForecast,
       WeatherConfig, WeatherStats, WeatherSnapshot, WeatherEvent
    |-- get_dynamic_weather_system

Core Capabilities:
  - register_zone / get_zone / list_zones / remove_zone / update_zone:
    weather zone registry management with FIFO eviction.
  - set_weather / get_weather / transition_to / get_transition /
    list_transitions / update_transition / remove_transition: weather
    state control and smooth interpolated transitions between weather
    types over time.
  - register_pattern / get_pattern / list_patterns / remove_pattern /
    update_pattern / apply_pattern: weather pattern library management
    and application to zones.
  - create_forecast / get_forecast / list_forecasts / remove_forecast:
    forward-looking weather forecasts per zone.
  - set_wind / get_wind / get_atmosphere / set_cloud_layer /
    get_cloud_layer: wind, atmospheric, and cloud layer access.
  - auto_generate_weather: AI-driven weather generation from a context
    describing biome, season, time of day, and mood.
  - suggest_pattern: AI-driven pattern suggestion that picks or builds a
    weather pattern to support a gameplay goal.
  - optimize_transitions: AI-driven optimization that tunes transition
    durations for realism.
  - get_status / get_stats / get_snapshot / get_config / set_config /
    tick / reset / list_events: observability, tuning, and lifecycle.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`DynamicWeatherSystem.get_instance` or the module-level
:func:`get_dynamic_weather_system` factory. All public methods are guarded
by the re-entrant lock.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest entry
# is evicted in FIFO order to keep memory growth predictable under heavy
# dynamic use (for example a game that swaps weather every few seconds
# during a storm cutscene or registers a fresh forecast every tick).
_MAX_ZONES: int = 500
_MAX_PATTERNS: int = 1000
_MAX_TRANSITIONS: int = 500
_MAX_FORECASTS: int = 1000
_MAX_EVENTS: int = 10000

# Numeric bounds for common atmospheric parameters.
_TEMPERATURE_MIN: float = -60.0
_TEMPERATURE_MAX: float = 60.0
_HUMIDITY_MIN: float = 0.0
_HUMIDITY_MAX: float = 100.0
_PRESSURE_MIN: float = 800.0
_PRESSURE_MAX: float = 1100.0
_WIND_SPEED_MIN: float = 0.0
_WIND_SPEED_MAX: float = 120.0
_VISIBILITY_MIN: float = 0.0
_VISIBILITY_MAX: float = 50000.0
_TURBULENCE_MIN: float = 0.0
_TURBULENCE_MAX: float = 1.0
_AIR_QUALITY_MIN: float = 0.0
_AIR_QUALITY_MAX: float = 100.0
_CLOUD_DENSITY_MIN: float = 0.0
_CLOUD_DENSITY_MAX: float = 1.0
_CONFIDENCE_MIN: float = 0.0
_CONFIDENCE_MAX: float = 1.0
_SIM_SPEED_MIN: float = 0.0
_SIM_SPEED_MAX: float = 100.0
_INTENSITY_MULT_MIN: float = 0.0
_INTENSITY_MULT_MAX: float = 2.0
_LATITUDE_MIN: float = -90.0
_LATITUDE_MAX: float = 90.0
_LONGITUDE_MIN: float = -180.0
_LONGITUDE_MAX: float = 180.0

# List limits.
_DEFAULT_LIST_LIMIT: int = 100
_MAX_LIST_LIMIT: int = 500


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix.

    Used as the default factory for ``created_at`` / ``updated_at`` fields
    and for event timestamps throughout the module.
    """
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier with an
            underscore. When omitted the bare hexadecimal id is returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits ``max_size``.

    Uses insertion-order iteration so the first inserted key is dropped
    first. This keeps memory growth bounded for FIFO-style stores.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits ``max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to ``default``.

    Accepts either an existing enum member or its raw value. Returns
    ``default`` when the value cannot be resolved.
    """
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value into a JSON-serializable form.

    Handles enums (by value), dicts, lists, tuples, sets, dataclasses
    (via ``__dataclass_fields__``), and objects exposing ``to_dict``.
    """
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
    """Convert a dataclass instance into a dict of JSON-serializable values.

    Checks ``__dataclass_fields__`` BEFORE ``to_dict`` to avoid recursion
    when a dataclass also defines a ``to_dict`` method that delegates back
    to this helper.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value to the inclusive ``[low, high]`` range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float, returning ``default`` on failure."""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int, returning ``default`` on failure."""
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WeatherType(str, Enum):
    """Classification of a weather condition by its physical family.

    Each value names a canonical weather kind that the system can seed
    with sensible default atmospheric properties (temperature, humidity,
    visibility, pressure, wind speed, cloud coverage, fog type).
    """

    CLEAR = "clear"
    CLOUDY = "cloudy"
    FOG = "fog"
    DRIZZLE = "drizzle"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    BLIZZARD = "blizzard"
    HAIL = "hail"
    SANDSTORM = "sandstorm"
    WINDY = "windy"
    HEAT_WAVE = "heat_wave"
    AURORA = "aurora"


class WeatherIntensity(str, Enum):
    """Severity tier of a weather condition.

    LIGHT is a gentle ambient effect, MODERATE is the default gameplay
    intensity, HEAVY noticeably impairs visibility and movement, and
    EXTREME represents hazardous conditions such as blizzards and
    thunderstorms at their peak.
    """

    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    EXTREME = "extreme"


class WeatherPhase(str, Enum):
    """Lifecycle phase of a weather condition within its duration.

    DEVELOPING is the ramp-up, PEAK is the sustained maximum, DISSIPATING
    is the ramp-down, and CLEARING is the return to calm after the
    condition has elapsed.
    """

    CLEARING = "clearing"
    DEVELOPING = "developing"
    PEAK = "peak"
    DISSIPATING = "dissipating"


class WindDirection(str, Enum):
    """Compass direction the wind is blowing FROM.

    VARIABLE is used when the wind direction shifts too frequently to
    pin to a single cardinal or intercardinal direction.
    """

    N = "N"
    NE = "NE"
    E = "E"
    SE = "SE"
    S = "S"
    SW = "SW"
    W = "W"
    NW = "NW"
    VARIABLE = "variable"


class CloudCoverage(str, Enum):
    """Amount of sky covered by clouds in okta-like buckets.

    CLEAR is no meaningful cloud cover, SCATTERED is scattered cumulus,
    BROKEN is a broken layer with gaps, and OVERCAST is a fully covered
    sky.
    """

    CLEAR = "clear"
    SCATTERED = "scattered"
    BROKEN = "broken"
    OVERCAST = "overcast"


class WeatherStatus(str, Enum):
    """Lifecycle state of a weather zone within the system."""

    IDLE = "idle"
    TRANSITIONING = "transitioning"
    ACTIVE = "active"
    PAUSED = "paused"


class Season(str, Enum):
    """Season of the year, used to bias temperature and weather choice."""

    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class FogType(str, Enum):
    """Classification of fog when present.

    NONE means no fog, MIST is light reduced visibility, FOG is moderate
    reduced visibility, DENSE_FOG is severe reduced visibility,
    RADIATION_FOG forms on clear calm nights, and ADVECTION_FOG forms
    when warm moist air moves over a cooler surface.
    """

    NONE = "none"
    MIST = "mist"
    FOG = "fog"
    DENSE_FOG = "dense_fog"
    RADIATION_FOG = "radiation_fog"
    ADVECTION_FOG = "advection_fog"


class WeatherEventKind(str, Enum):
    """Audit event kinds emitted by the dynamic weather system."""

    ZONE_CREATED = "zone_created"
    ZONE_REMOVED = "zone_removed"
    WEATHER_CHANGED = "weather_changed"
    STORM_STARTED = "storm_started"
    STORM_ENDED = "storm_ended"
    WIND_SHIFTED = "wind_shifted"
    CONFIG_CHANGED = "config_changed"
    SYSTEM_RESET = "system_reset"


# ---------------------------------------------------------------------------
# Weather Properties Table
# ---------------------------------------------------------------------------

# Default atmospheric properties for every WeatherType. Centralizing the
# properties here keeps the seed data, set_weather, and the AI generator
# consistent and avoids magic numbers scattered through the code. Each
# entry provides a baseline temperature (Celsius), humidity (percent),
# visibility (meters), pressure (hPa), wind speed (m/s), cloud coverage,
# fog type, and the default intensity tier.
_WEATHER_PROPERTIES: Dict[str, Dict[str, Any]] = {
    WeatherType.CLEAR.value: {
        "temperature": 22.0, "humidity": 45.0, "visibility": 10000.0,
        "pressure": 1013.0, "wind_speed": 3.0,
        "cloud_coverage": CloudCoverage.CLEAR.value,
        "fog_type": FogType.NONE.value,
        "default_intensity": WeatherIntensity.LIGHT.value,
    },
    WeatherType.CLOUDY.value: {
        "temperature": 18.0, "humidity": 60.0, "visibility": 8000.0,
        "pressure": 1010.0, "wind_speed": 5.0,
        "cloud_coverage": CloudCoverage.OVERCAST.value,
        "fog_type": FogType.NONE.value,
        "default_intensity": WeatherIntensity.MODERATE.value,
    },
    WeatherType.FOG.value: {
        "temperature": 12.0, "humidity": 90.0, "visibility": 500.0,
        "pressure": 1015.0, "wind_speed": 1.0,
        "cloud_coverage": CloudCoverage.BROKEN.value,
        "fog_type": FogType.FOG.value,
        "default_intensity": WeatherIntensity.MODERATE.value,
    },
    WeatherType.DRIZZLE.value: {
        "temperature": 14.0, "humidity": 85.0, "visibility": 4000.0,
        "pressure": 1008.0, "wind_speed": 4.0,
        "cloud_coverage": CloudCoverage.OVERCAST.value,
        "fog_type": FogType.MIST.value,
        "default_intensity": WeatherIntensity.LIGHT.value,
    },
    WeatherType.RAIN.value: {
        "temperature": 15.0, "humidity": 80.0, "visibility": 3000.0,
        "pressure": 1005.0, "wind_speed": 6.0,
        "cloud_coverage": CloudCoverage.OVERCAST.value,
        "fog_type": FogType.NONE.value,
        "default_intensity": WeatherIntensity.MODERATE.value,
    },
    WeatherType.HEAVY_RAIN.value: {
        "temperature": 14.0, "humidity": 88.0, "visibility": 1500.0,
        "pressure": 1000.0, "wind_speed": 8.0,
        "cloud_coverage": CloudCoverage.OVERCAST.value,
        "fog_type": FogType.MIST.value,
        "default_intensity": WeatherIntensity.HEAVY.value,
    },
    WeatherType.THUNDERSTORM.value: {
        "temperature": 22.0, "humidity": 85.0, "visibility": 1000.0,
        "pressure": 995.0, "wind_speed": 12.0,
        "cloud_coverage": CloudCoverage.OVERCAST.value,
        "fog_type": FogType.NONE.value,
        "default_intensity": WeatherIntensity.HEAVY.value,
    },
    WeatherType.SNOW.value: {
        "temperature": -3.0, "humidity": 75.0, "visibility": 2000.0,
        "pressure": 1010.0, "wind_speed": 5.0,
        "cloud_coverage": CloudCoverage.OVERCAST.value,
        "fog_type": FogType.NONE.value,
        "default_intensity": WeatherIntensity.MODERATE.value,
    },
    WeatherType.BLIZZARD.value: {
        "temperature": -15.0, "humidity": 70.0, "visibility": 200.0,
        "pressure": 1000.0, "wind_speed": 20.0,
        "cloud_coverage": CloudCoverage.OVERCAST.value,
        "fog_type": FogType.DENSE_FOG.value,
        "default_intensity": WeatherIntensity.EXTREME.value,
    },
    WeatherType.HAIL.value: {
        "temperature": 5.0, "humidity": 75.0, "visibility": 2000.0,
        "pressure": 1000.0, "wind_speed": 10.0,
        "cloud_coverage": CloudCoverage.OVERCAST.value,
        "fog_type": FogType.NONE.value,
        "default_intensity": WeatherIntensity.HEAVY.value,
    },
    WeatherType.SANDSTORM.value: {
        "temperature": 35.0, "humidity": 15.0, "visibility": 300.0,
        "pressure": 1005.0, "wind_speed": 18.0,
        "cloud_coverage": CloudCoverage.SCATTERED.value,
        "fog_type": FogType.NONE.value,
        "default_intensity": WeatherIntensity.EXTREME.value,
    },
    WeatherType.WINDY.value: {
        "temperature": 17.0, "humidity": 50.0, "visibility": 9000.0,
        "pressure": 1010.0, "wind_speed": 15.0,
        "cloud_coverage": CloudCoverage.SCATTERED.value,
        "fog_type": FogType.NONE.value,
        "default_intensity": WeatherIntensity.MODERATE.value,
    },
    WeatherType.HEAT_WAVE.value: {
        "temperature": 40.0, "humidity": 25.0, "visibility": 8000.0,
        "pressure": 1018.0, "wind_speed": 2.0,
        "cloud_coverage": CloudCoverage.CLEAR.value,
        "fog_type": FogType.NONE.value,
        "default_intensity": WeatherIntensity.EXTREME.value,
    },
    WeatherType.AURORA.value: {
        "temperature": -20.0, "humidity": 60.0, "visibility": 9000.0,
        "pressure": 1015.0, "wind_speed": 2.0,
        "cloud_coverage": CloudCoverage.CLEAR.value,
        "fog_type": FogType.NONE.value,
        "default_intensity": WeatherIntensity.LIGHT.value,
    },
}

# Weather types considered storms for event tracking and statistics.
_STORM_WEATHER_TYPES: set = {
    WeatherType.THUNDERSTORM.value,
    WeatherType.BLIZZARD.value,
    WeatherType.SANDSTORM.value,
    WeatherType.HAIL.value,
    WeatherType.HEAVY_RAIN.value,
}


def _weather_properties(weather_type: str) -> Dict[str, Any]:
    """Return the default atmospheric properties for a weather type.

    Falls back to the CLEAR properties when the weather type is not in
    the canonical table so unknown types remain usable with sane
    defaults.
    """
    return _WEATHER_PROPERTIES.get(
        weather_type, _WEATHER_PROPERTIES[WeatherType.CLEAR.value]
    )


# Base temperature per biome (Celsius) used by the AI generator.
_BIOME_BASE_TEMP: Dict[str, float] = {
    "temperate": 18.0,
    "desert": 32.0,
    "arctic": -10.0,
    "tropical": 28.0,
    "volcanic": 35.0,
    "coastal": 20.0,
    "forest": 16.0,
    "mountain": 5.0,
    "ocean": 22.0,
    "tundra": -5.0,
    "grassland": 17.0,
}

# Temperature delta per season applied on top of the biome base.
_SEASON_TEMP_DELTA: Dict[str, float] = {
    Season.SPRING.value: 0.0,
    Season.SUMMER.value: 8.0,
    Season.AUTUMN.value: -3.0,
    Season.WINTER.value: -12.0,
}


def _biome_base_temperature(biome: str, season: str) -> float:
    """Return a baseline temperature for a biome and season pair."""
    base = _BIOME_BASE_TEMP.get(biome, 18.0)
    delta = _SEASON_TEMP_DELTA.get(season, 0.0)
    return _clamp(base + delta, _TEMPERATURE_MIN, _TEMPERATURE_MAX)


def _make_wind_state(
    direction: str = WindDirection.N.value,
    speed: float = 0.0,
    gusts: Optional[float] = None,
    turbulence: Optional[float] = None,
    wind_id: str = "",
) -> "WindState":
    """Build a WindState with clamped fields and sensible gust defaults.

    When gusts are not provided they default to a small multiple of the
    sustained speed so a wind state always carries a believable gust
    value. Turbulence defaults to a fraction of the speed scaled into the
    ``[0.0, 1.0]`` range.
    """
    safe_speed = _clamp(_safe_float(speed, 0.0), _WIND_SPEED_MIN, _WIND_SPEED_MAX)
    if gusts is None:
        gusts = min(safe_speed * 1.4, _WIND_SPEED_MAX)
    safe_gusts = _clamp(_safe_float(gusts, safe_speed), _WIND_SPEED_MIN, _WIND_SPEED_MAX)
    if turbulence is None:
        turbulence = _clamp(safe_speed / _WIND_SPEED_MAX, _TURBULENCE_MIN, _TURBULENCE_MAX)
    safe_turb = _clamp(
        _safe_float(turbulence, 0.0), _TURBULENCE_MIN, _TURBULENCE_MAX
    )
    direction_enum = _coerce_enum(WindDirection, direction, WindDirection.N)
    return WindState(
        wind_id=wind_id or _new_id("wind"),
        direction=direction_enum.value,
        speed=safe_speed,
        gusts=safe_gusts,
        turbulence=safe_turb,
        created_at=_now(),
        updated_at=_now(),
        metadata={},
    )


def _make_cloud_layer(
    coverage: str = CloudCoverage.CLEAR.value,
    height: float = 1000.0,
    density: Optional[float] = None,
    cloud_type: str = "cumulus",
    cloud_id: str = "",
) -> "CloudLayer":
    """Build a CloudLayer with clamped fields and a density derived from
    coverage when one is not supplied."""
    coverage_enum = _coerce_enum(CloudCoverage, coverage, CloudCoverage.CLEAR)
    if density is None:
        coverage_density = {
            CloudCoverage.CLEAR.value: 0.05,
            CloudCoverage.SCATTERED.value: 0.3,
            CloudCoverage.BROKEN.value: 0.6,
            CloudCoverage.OVERCAST.value: 0.9,
        }
        density = coverage_density.get(coverage_enum.value, 0.05)
    safe_density = _clamp(
        _safe_float(density, 0.05), _CLOUD_DENSITY_MIN, _CLOUD_DENSITY_MAX
    )
    return CloudLayer(
        cloud_id=cloud_id or _new_id("cloud"),
        coverage=coverage_enum.value,
        height=max(0.0, _safe_float(height, 1000.0)),
        density=safe_density,
        cloud_type=cloud_type or "cumulus",
        created_at=_now(),
        updated_at=_now(),
        metadata={},
    )


def _make_atmosphere(
    temperature: float = 20.0,
    humidity: float = 50.0,
    pressure: float = 1013.25,
    air_quality: float = 100.0,
    visibility: float = 10000.0,
    atmosphere_id: str = "",
) -> "AtmosphericConditions":
    """Build an AtmosphericConditions with all fields clamped to bounds."""
    return AtmosphericConditions(
        atmosphere_id=atmosphere_id or _new_id("atm"),
        temperature=_clamp(_safe_float(temperature, 20.0), _TEMPERATURE_MIN, _TEMPERATURE_MAX),
        humidity=_clamp(_safe_float(humidity, 50.0), _HUMIDITY_MIN, _HUMIDITY_MAX),
        pressure=_clamp(_safe_float(pressure, 1013.25), _PRESSURE_MIN, _PRESSURE_MAX),
        air_quality=_clamp(_safe_float(air_quality, 100.0), _AIR_QUALITY_MIN, _AIR_QUALITY_MAX),
        visibility=_clamp(_safe_float(visibility, 10000.0), _VISIBILITY_MIN, _VISIBILITY_MAX),
        created_at=_now(),
        updated_at=_now(),
        metadata={},
    )


def _make_weather_state(
    weather_type: str = WeatherType.CLEAR.value,
    intensity: Optional[str] = None,
    temperature: Optional[float] = None,
    humidity: Optional[float] = None,
    visibility: Optional[float] = None,
    pressure: Optional[float] = None,
    wind_speed: Optional[float] = None,
    wind_direction: str = WindDirection.N.value,
    cloud_coverage: Optional[str] = None,
    fog_type: Optional[str] = None,
    duration: float = 0.0,
    state_id: str = "",
) -> "WeatherState":
    """Build a WeatherState using weather-type defaults for unset fields.

    Any field left as None pulls its value from the canonical
    ``_WEATHER_PROPERTIES`` table so a caller can supply just a weather
    type and still receive a fully populated, believable state.
    """
    type_enum = _coerce_enum(WeatherType, weather_type, WeatherType.CLEAR)
    props = _weather_properties(type_enum.value)
    intensity_enum = _coerce_enum(
        WeatherIntensity, intensity, None
    )
    if intensity_enum is None:
        intensity_enum = WeatherIntensity(props["default_intensity"])
    cloud_enum = _coerce_enum(
        CloudCoverage, cloud_coverage, CloudCoverage(props["cloud_coverage"])
    )
    fog_enum = _coerce_enum(FogType, fog_type, FogType(props["fog_type"]))
    direction_enum = _coerce_enum(WindDirection, wind_direction, WindDirection.N)
    return WeatherState(
        state_id=state_id or _new_id("wstate"),
        weather_type=type_enum.value,
        intensity=intensity_enum.value,
        phase=WeatherPhase.PEAK.value,
        temperature=_clamp(
            _safe_float(temperature, props["temperature"]),
            _TEMPERATURE_MIN, _TEMPERATURE_MAX,
        ),
        humidity=_clamp(
            _safe_float(humidity, props["humidity"]),
            _HUMIDITY_MIN, _HUMIDITY_MAX,
        ),
        wind_speed=_clamp(
            _safe_float(wind_speed, props["wind_speed"]),
            _WIND_SPEED_MIN, _WIND_SPEED_MAX,
        ),
        wind_direction=direction_enum.value,
        visibility=_clamp(
            _safe_float(visibility, props["visibility"]),
            _VISIBILITY_MIN, _VISIBILITY_MAX,
        ),
        pressure=_clamp(
            _safe_float(pressure, props["pressure"]),
            _PRESSURE_MIN, _PRESSURE_MAX,
        ),
        cloud_coverage=cloud_enum.value,
        fog_type=fog_enum.value,
        duration=max(0.0, _safe_float(duration, 0.0)),
        elapsed=0.0,
        created_at=_now(),
        updated_at=_now(),
        metadata={},
    )


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class WindState:
    """The wind conditions for a zone.

    Attributes:
        wind_id: Unique wind state identifier.
        direction: The WindDirection value name the wind blows FROM.
        speed: Sustained wind speed in meters per second.
        gusts: Peak gust speed in meters per second.
        turbulence: Turbulence factor in ``[0.0, 1.0]``.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    wind_id: str
    direction: str = WindDirection.N.value
    speed: float = 0.0
    gusts: float = 0.0
    turbulence: float = 0.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CloudLayer:
    """A cloud layer above a zone.

    Attributes:
        cloud_id: Unique cloud layer identifier.
        coverage: The CloudCoverage value name.
        height: Cloud base height in meters.
        density: Cloud density in ``[0.0, 1.0]``.
        cloud_type: Free-form cloud type name (e.g. "cumulus", "stratus").
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    cloud_id: str
    coverage: str = CloudCoverage.CLEAR.value
    height: float = 1000.0
    density: float = 0.05
    cloud_type: str = "cumulus"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AtmosphericConditions:
    """The atmospheric conditions for a zone.

    Attributes:
        atmosphere_id: Unique atmosphere identifier.
        temperature: Air temperature in Celsius.
        humidity: Relative humidity in percent.
        pressure: Atmospheric pressure in hPa.
        air_quality: Air quality index in ``[0.0, 100.0]`` (higher is better).
        visibility: Visibility in meters.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    atmosphere_id: str
    temperature: float = 20.0
    humidity: float = 50.0
    pressure: float = 1013.25
    air_quality: float = 100.0
    visibility: float = 10000.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherState:
    """The current weather state of a zone.

    Bundles the weather type, intensity, lifecycle phase, and the
    atmospheric scalars (temperature, humidity, wind, visibility,
    pressure) that describe the condition. The wind and cloud details
    live on the zone as WindState and CloudLayer objects; this state
    carries scalar snapshots so it can be serialized and compared without
    pulling in the full sub-objects.

    Attributes:
        state_id: Unique state identifier.
        weather_type: The WeatherType value name.
        intensity: The WeatherIntensity value name.
        phase: The WeatherPhase value name.
        temperature: Air temperature in Celsius.
        humidity: Relative humidity in percent.
        wind_speed: Sustained wind speed in meters per second.
        wind_direction: The WindDirection value name.
        visibility: Visibility in meters.
        pressure: Atmospheric pressure in hPa.
        cloud_coverage: The CloudCoverage value name.
        fog_type: The FogType value name.
        duration: Intended duration of the condition in seconds.
        elapsed: Seconds elapsed since the condition began.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    state_id: str
    weather_type: str = WeatherType.CLEAR.value
    intensity: str = WeatherIntensity.LIGHT.value
    phase: str = WeatherPhase.PEAK.value
    temperature: float = 20.0
    humidity: float = 50.0
    wind_speed: float = 0.0
    wind_direction: str = WindDirection.N.value
    visibility: float = 10000.0
    pressure: float = 1013.25
    cloud_coverage: str = CloudCoverage.CLEAR.value
    fog_type: str = FogType.NONE.value
    duration: float = 0.0
    elapsed: float = 0.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherZone:
    """A geographic zone with its own weather state.

    A zone is the primary unit of weather management. It owns a current
    WeatherState, a WindState, an AtmosphericConditions snapshot, and a
    CloudLayer. Zones are independent: changing the weather in one zone
    does not affect another.

    Attributes:
        zone_id: Unique zone identifier.
        name: Display name.
        biome: Free-form biome name (e.g. "temperate", "desert").
        season: The Season value name.
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        area: Area in square kilometers.
        current_state: The current WeatherState (may be None before init).
        wind: The current WindState.
        atmosphere: The current AtmosphericConditions.
        cloud_layer: The current CloudLayer.
        status: The WeatherStatus value name.
        active: Whether the zone is being simulated.
        tags: Searchable tags for filtering.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    zone_id: str
    name: str
    biome: str = "temperate"
    season: str = Season.SPRING.value
    latitude: float = 0.0
    longitude: float = 0.0
    area: float = 0.0
    current_state: Optional[WeatherState] = None
    wind: Optional[WindState] = None
    atmosphere: Optional[AtmosphericConditions] = None
    cloud_layer: Optional[CloudLayer] = None
    status: str = WeatherStatus.IDLE.value
    active: bool = True
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherTransition:
    """A smooth transition between two weather states over time.

    Transitions interpolate a zone's weather from a source weather type
    to a target weather type over a duration using an easing function.
    The progress field tracks how far the transition has advanced
    (0.0 to 1.0).

    Attributes:
        transition_id: Unique transition identifier.
        zone_id: The zone the transition applies to.
        from_type: The source WeatherType value name.
        to_type: The destination WeatherType value name.
        from_intensity: The source WeatherIntensity value name.
        to_intensity: The destination WeatherIntensity value name.
        duration: Transition duration in seconds.
        easing: Easing function name (e.g. "linear", "ease_in_out").
        active: Whether the transition is currently in progress.
        progress: Current progress from 0.0 to 1.0.
        created_at: Creation timestamp.
        metadata: Free-form extension data.
    """

    transition_id: str
    zone_id: str
    from_type: str = WeatherType.CLEAR.value
    to_type: str = WeatherType.CLEAR.value
    from_intensity: str = WeatherIntensity.LIGHT.value
    to_intensity: str = WeatherIntensity.LIGHT.value
    duration: float = 1.0
    easing: str = "linear"
    active: bool = False
    progress: float = 0.0
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherPattern:
    """A predefined weather pattern that can be applied to a zone.

    A pattern bundles a target weather type, intensity, duration, wind,
    temperature, humidity, cloud coverage, fog type, and visibility into
    a reusable recipe. An optional ordered ``steps`` list describes a
    sequence of weather changes the pattern drives when applied.

    Attributes:
        pattern_id: Unique pattern identifier.
        name: Display name.
        description: Human-readable description.
        weather_type: The WeatherType value name the pattern produces.
        intensity: The WeatherIntensity value name.
        duration: Pattern duration in seconds.
        wind_direction: The WindDirection value name.
        wind_speed: Wind speed in meters per second.
        temperature: Target temperature in Celsius.
        humidity: Target humidity in percent.
        cloud_coverage: The CloudCoverage value name.
        fog_type: The FogType value name.
        visibility: Target visibility in meters.
        steps: Ordered list of step dicts (each with weather_type,
            intensity, and offset_seconds) describing the pattern sequence.
        tags: Searchable tags for filtering.
        enabled: Whether the pattern is eligible for application.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    pattern_id: str
    name: str
    description: str = ""
    weather_type: str = WeatherType.CLEAR.value
    intensity: str = WeatherIntensity.MODERATE.value
    duration: float = 3600.0
    wind_direction: str = WindDirection.N.value
    wind_speed: float = 0.0
    temperature: float = 20.0
    humidity: float = 50.0
    cloud_coverage: str = CloudCoverage.SCATTERED.value
    fog_type: str = FogType.NONE.value
    visibility: float = 10000.0
    steps: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherForecast:
    """A forward-looking weather forecast for a zone.

    A forecast projects a zone's weather forward in time as an ordered
    list of entries, each describing a predicted weather type, intensity,
    temperature, and the hour offset from the issue time.

    Attributes:
        forecast_id: Unique forecast identifier.
        zone_id: The zone the forecast applies to.
        hours_ahead: Number of hours the forecast covers.
        issued_at: Issue timestamp.
        entries: Ordered list of forecast entry dicts (each with
            weather_type, intensity, temperature, hour_offset).
        confidence: Forecast confidence in ``[0.0, 1.0]``.
        created_at: Creation timestamp.
        metadata: Free-form extension data.
    """

    forecast_id: str
    zone_id: str
    hours_ahead: int = 24
    issued_at: str = field(default_factory=_now)
    entries: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.8
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherConfig:
    """Global tuning parameters for the dynamic weather system.

    Attributes:
        max_zones: Maximum number of zones retained before FIFO eviction.
        max_patterns: Maximum number of patterns retained.
        max_transitions: Maximum number of transitions retained.
        max_forecasts: Maximum number of forecasts retained.
        max_events: Maximum number of audit events retained.
        default_season: Default season for new zones.
        enable_wind: Whether wind simulation is globally enabled.
        enable_fog: Whether fog effects are globally enabled.
        enable_clouds: Whether cloud layers are globally enabled.
        simulation_speed: Multiplier on elapsed simulation time.
        metadata: Free-form extension data.
    """

    max_zones: int = _MAX_ZONES
    max_patterns: int = _MAX_PATTERNS
    max_transitions: int = _MAX_TRANSITIONS
    max_forecasts: int = _MAX_FORECASTS
    max_events: int = _MAX_EVENTS
    default_season: str = Season.SPRING.value
    enable_wind: bool = True
    enable_fog: bool = True
    enable_clouds: bool = True
    simulation_speed: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherStats:
    """Aggregate statistics for the dynamic weather system.

    Attributes:
        total_zones: Total number of registered zones.
        total_patterns: Total number of registered patterns.
        total_transitions: Total number of registered transitions.
        total_forecasts: Total number of registered forecasts.
        active_zones: Number of zones currently active.
        active_transitions: Number of transitions currently in progress.
        total_weather_changes: Cumulative count of weather changes.
        total_storms: Cumulative count of storms started.
        total_patterns_applied: Cumulative count of pattern applications.
        tick_count: Number of ticks processed.
    """

    total_zones: int = 0
    total_patterns: int = 0
    total_transitions: int = 0
    total_forecasts: int = 0
    active_zones: int = 0
    active_transitions: int = 0
    total_weather_changes: int = 0
    total_storms: int = 0
    total_patterns_applied: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherSnapshot:
    """Full state snapshot of the dynamic weather system.

    Attributes:
        timestamp: Snapshot timestamp.
        zones: Serialized zone list (bounded for size).
        patterns: Serialized pattern list.
        transitions: Serialized transition list.
        forecasts: Serialized forecast list.
        events: Serialized event list (bounded for size).
        stats: Serialized statistics.
    """

    timestamp: str = field(default_factory=_now)
    zones: List[Dict[str, Any]] = field(default_factory=list)
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    forecasts: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherEvent:
    """An audit event emitted by the dynamic weather system.

    Attributes:
        event_id: Unique event identifier.
        timestamp: Event timestamp.
        event_type: The WeatherEventKind value name.
        zone_id: The zone id the event concerns (when applicable).
        description: Human-readable summary of the event.
        metadata: Free-form extension data.
    """

    event_id: str
    timestamp: str = field(default_factory=_now)
    event_type: str = ""
    zone_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Dynamic Weather System
# ---------------------------------------------------------------------------


class DynamicWeatherSystem:
    """Manages weather zones, patterns, transitions, forecasts, winds,
    atmospheres, cloud layers, and the AI weather generation pipeline.

    The system is a thread-safe singleton. All public methods take the
    instance lock before mutating shared state so that concurrent calls
    from gameplay, simulation, and editor threads remain consistent.
    """

    _instance: Optional["DynamicWeatherSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        # Primary stores
        self._zones: Dict[str, WeatherZone] = {}
        self._patterns: Dict[str, WeatherPattern] = {}
        self._transitions: Dict[str, WeatherTransition] = {}
        self._forecasts: Dict[str, WeatherForecast] = {}
        self._events: List[WeatherEvent] = []
        # Config and stats
        self._config = WeatherConfig()
        self._stats = WeatherStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._transition_counter: int = 0
        self._forecast_counter: int = 0
        self.initialize()

    @classmethod
    def get_instance(cls) -> "DynamicWeatherSystem":
        """Return the singleton DynamicWeatherSystem instance.

        Uses double-checked locking so the instance is created exactly
        once even when multiple threads call this concurrently on first
        use.
        """
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the system with seed data (idempotent).

        Guarded by the init lock so repeated calls are no-ops after the
        first successful seed. This is invoked from ``__init__`` and from
        ``reset`` to repopulate the default data set.
        """
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed()
            self._initialized = True

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the system with seed data.

        Seeds six weather zones covering distinct biomes (temperate,
        desert, arctic, tropical, volcanic, coastal), eight weather
        patterns covering the canonical weather families, six weather
        transitions, five forecasts, and six audit events.
        """
        now = _now()

        # --- Weather Zones (6) ---
        # Each zone is built from a biome, season, and an initial weather
        # type. The initial weather state, wind, atmosphere, and cloud
        # layer are derived from the weather-type properties table.
        zone_seeds: List[Dict[str, Any]] = [
            {
                "zone_id": "zone_temperate_field",
                "name": "Temperate Field",
                "biome": "temperate",
                "season": Season.SPRING.value,
                "latitude": 45.0, "longitude": 10.0, "area": 50.0,
                "weather_type": WeatherType.CLEAR.value,
                "intensity": WeatherIntensity.LIGHT.value,
                "wind_direction": WindDirection.SW.value,
                "wind_speed": 4.0,
                "tags": ["grassland", "mild", "starter"],
            },
            {
                "zone_id": "zone_desert_oasis",
                "name": "Desert Oasis",
                "biome": "desert",
                "season": Season.SUMMER.value,
                "latitude": 25.0, "longitude": 40.0, "area": 80.0,
                "weather_type": WeatherType.HEAT_WAVE.value,
                "intensity": WeatherIntensity.HEAVY.value,
                "wind_direction": WindDirection.NE.value,
                "wind_speed": 6.0,
                "tags": ["desert", "hot", "dry"],
            },
            {
                "zone_id": "zone_arctic_tundra",
                "name": "Arctic Tundra",
                "biome": "arctic",
                "season": Season.WINTER.value,
                "latitude": 70.0, "longitude": -20.0, "area": 120.0,
                "weather_type": WeatherType.SNOW.value,
                "intensity": WeatherIntensity.MODERATE.value,
                "wind_direction": WindDirection.N.value,
                "wind_speed": 8.0,
                "tags": ["arctic", "cold", "snow"],
            },
            {
                "zone_id": "zone_tropical_jungle",
                "name": "Tropical Jungle",
                "biome": "tropical",
                "season": Season.SUMMER.value,
                "latitude": 5.0, "longitude": 100.0, "area": 60.0,
                "weather_type": WeatherType.RAIN.value,
                "intensity": WeatherIntensity.MODERATE.value,
                "wind_direction": WindDirection.SE.value,
                "wind_speed": 5.0,
                "tags": ["tropical", "humid", "rain"],
            },
            {
                "zone_id": "zone_volcanic_wastes",
                "name": "Volcanic Wastes",
                "biome": "volcanic",
                "season": Season.SUMMER.value,
                "latitude": 35.0, "longitude": 140.0, "area": 40.0,
                "weather_type": WeatherType.CLOUDY.value,
                "intensity": WeatherIntensity.MODERATE.value,
                "wind_direction": WindDirection.W.value,
                "wind_speed": 7.0,
                "tags": ["volcanic", "harsh", "ash"],
            },
            {
                "zone_id": "zone_coastal_bay",
                "name": "Coastal Bay",
                "biome": "coastal",
                "season": Season.AUTUMN.value,
                "latitude": 40.0, "longitude": -70.0, "area": 90.0,
                "weather_type": WeatherType.WINDY.value,
                "intensity": WeatherIntensity.MODERATE.value,
                "wind_direction": WindDirection.E.value,
                "wind_speed": 12.0,
                "tags": ["coastal", "windy", "ocean"],
            },
        ]

        for seed in zone_seeds:
            props = _weather_properties(seed["weather_type"])
            state = _make_weather_state(
                weather_type=seed["weather_type"],
                intensity=seed["intensity"],
                wind_direction=seed["wind_direction"],
                wind_speed=seed["wind_speed"],
                duration=3600.0,
            )
            # Bias the temperature toward the biome/season baseline so the
            # seeded zones reflect their geography rather than the generic
            # weather-type default.
            biome_temp = _biome_base_temperature(seed["biome"], seed["season"])
            state.temperature = round(
                _clamp(
                    (state.temperature + biome_temp) / 2.0,
                    _TEMPERATURE_MIN, _TEMPERATURE_MAX,
                ),
                2,
            )
            wind = _make_wind_state(
                direction=seed["wind_direction"],
                speed=seed["wind_speed"],
            )
            atmosphere = _make_atmosphere(
                temperature=state.temperature,
                humidity=state.humidity,
                pressure=state.pressure,
                visibility=state.visibility,
                air_quality=80.0 if seed["biome"] != "volcanic" else 55.0,
            )
            cloud = _make_cloud_layer(
                coverage=props["cloud_coverage"],
                height=1200.0,
                cloud_type="cumulus",
            )
            zone = WeatherZone(
                zone_id=seed["zone_id"],
                name=seed["name"],
                biome=seed["biome"],
                season=seed["season"],
                latitude=_clamp(
                    _safe_float(seed["latitude"], 0.0),
                    _LATITUDE_MIN, _LATITUDE_MAX,
                ),
                longitude=_clamp(
                    _safe_float(seed["longitude"], 0.0),
                    _LONGITUDE_MIN, _LONGITUDE_MAX,
                ),
                area=max(0.0, _safe_float(seed["area"], 0.0)),
                current_state=state,
                wind=wind,
                atmosphere=atmosphere,
                cloud_layer=cloud,
                status=WeatherStatus.ACTIVE.value,
                active=True,
                tags=list(seed.get("tags", [])),
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
            )
            self._zones[zone.zone_id] = zone

        # --- Weather Patterns (8) ---
        # Each pattern is a reusable recipe for a canonical weather family.
        pattern_seeds: List[Dict[str, Any]] = [
            {
                "pattern_id": "pattern_gentle_rain",
                "name": "Gentle Rain",
                "description": "Soft steady drizzle that lifts the mood.",
                "weather_type": WeatherType.RAIN.value,
                "intensity": WeatherIntensity.LIGHT.value,
                "duration": 1800.0,
                "wind_direction": WindDirection.SW.value,
                "wind_speed": 4.0,
                "temperature": 15.0,
                "humidity": 80.0,
                "cloud_coverage": CloudCoverage.OVERCAST.value,
                "fog_type": FogType.NONE.value,
                "visibility": 4000.0,
                "tags": ["rain", "calm", "ambient"],
                "steps": [
                    {"weather_type": WeatherType.CLOUDY.value, "intensity": WeatherIntensity.LIGHT.value, "offset_seconds": 0},
                    {"weather_type": WeatherType.RAIN.value, "intensity": WeatherIntensity.LIGHT.value, "offset_seconds": 300},
                ],
            },
            {
                "pattern_id": "pattern_thunderstorm",
                "name": "Thunderstorm",
                "description": "Dramatic thunderstorm with heavy rain and lightning.",
                "weather_type": WeatherType.THUNDERSTORM.value,
                "intensity": WeatherIntensity.HEAVY.value,
                "duration": 2400.0,
                "wind_direction": WindDirection.SW.value,
                "wind_speed": 14.0,
                "temperature": 22.0,
                "humidity": 85.0,
                "cloud_coverage": CloudCoverage.OVERCAST.value,
                "fog_type": FogType.NONE.value,
                "visibility": 1000.0,
                "tags": ["storm", "dramatic", "rain"],
                "steps": [
                    {"weather_type": WeatherType.CLOUDY.value, "intensity": WeatherIntensity.MODERATE.value, "offset_seconds": 0},
                    {"weather_type": WeatherType.HEAVY_RAIN.value, "intensity": WeatherIntensity.HEAVY.value, "offset_seconds": 600},
                    {"weather_type": WeatherType.THUNDERSTORM.value, "intensity": WeatherIntensity.HEAVY.value, "offset_seconds": 1200},
                ],
            },
            {
                "pattern_id": "pattern_blizzard",
                "name": "Blizzard",
                "description": "Howling blizzard with near-zero visibility.",
                "weather_type": WeatherType.BLIZZARD.value,
                "intensity": WeatherIntensity.EXTREME.value,
                "duration": 3600.0,
                "wind_direction": WindDirection.N.value,
                "wind_speed": 22.0,
                "temperature": -15.0,
                "humidity": 70.0,
                "cloud_coverage": CloudCoverage.OVERCAST.value,
                "fog_type": FogType.DENSE_FOG.value,
                "visibility": 200.0,
                "tags": ["storm", "cold", "snow", "harsh"],
                "steps": [
                    {"weather_type": WeatherType.SNOW.value, "intensity": WeatherIntensity.MODERATE.value, "offset_seconds": 0},
                    {"weather_type": WeatherType.BLIZZARD.value, "intensity": WeatherIntensity.EXTREME.value, "offset_seconds": 900},
                ],
            },
            {
                "pattern_id": "pattern_heat_wave",
                "name": "Heat Wave",
                "description": "Oppressive heat wave under a cloudless sky.",
                "weather_type": WeatherType.HEAT_WAVE.value,
                "intensity": WeatherIntensity.EXTREME.value,
                "duration": 7200.0,
                "wind_direction": WindDirection.N.value,
                "wind_speed": 2.0,
                "temperature": 42.0,
                "humidity": 22.0,
                "cloud_coverage": CloudCoverage.CLEAR.value,
                "fog_type": FogType.NONE.value,
                "visibility": 9000.0,
                "tags": ["hot", "harsh", "desert"],
                "steps": [
                    {"weather_type": WeatherType.CLEAR.value, "intensity": WeatherIntensity.LIGHT.value, "offset_seconds": 0},
                    {"weather_type": WeatherType.HEAT_WAVE.value, "intensity": WeatherIntensity.EXTREME.value, "offset_seconds": 1800},
                ],
            },
            {
                "pattern_id": "pattern_sandstorm",
                "name": "Sandstorm",
                "description": "Choking sandstorm driven by gale-force winds.",
                "weather_type": WeatherType.SANDSTORM.value,
                "intensity": WeatherIntensity.EXTREME.value,
                "duration": 3000.0,
                "wind_direction": WindDirection.NE.value,
                "wind_speed": 20.0,
                "temperature": 36.0,
                "humidity": 12.0,
                "cloud_coverage": CloudCoverage.SCATTERED.value,
                "fog_type": FogType.NONE.value,
                "visibility": 300.0,
                "tags": ["storm", "harsh", "desert", "wind"],
                "steps": [
                    {"weather_type": WeatherType.WINDY.value, "intensity": WeatherIntensity.MODERATE.value, "offset_seconds": 0},
                    {"weather_type": WeatherType.SANDSTORM.value, "intensity": WeatherIntensity.EXTREME.value, "offset_seconds": 600},
                ],
            },
            {
                "pattern_id": "pattern_clear_sky",
                "name": "Clear Sky",
                "description": "Peaceful clear sky with a gentle breeze.",
                "weather_type": WeatherType.CLEAR.value,
                "intensity": WeatherIntensity.LIGHT.value,
                "duration": 5400.0,
                "wind_direction": WindDirection.NW.value,
                "wind_speed": 3.0,
                "temperature": 22.0,
                "humidity": 45.0,
                "cloud_coverage": CloudCoverage.CLEAR.value,
                "fog_type": FogType.NONE.value,
                "visibility": 10000.0,
                "tags": ["calm", "pleasant", "clear"],
                "steps": [
                    {"weather_type": WeatherType.CLEAR.value, "intensity": WeatherIntensity.LIGHT.value, "offset_seconds": 0},
                ],
            },
            {
                "pattern_id": "pattern_foggy_morning",
                "name": "Foggy Morning",
                "description": "Still morning blanketed in soft radiation fog.",
                "weather_type": WeatherType.FOG.value,
                "intensity": WeatherIntensity.MODERATE.value,
                "duration": 2700.0,
                "wind_direction": WindDirection.N.value,
                "wind_speed": 1.0,
                "temperature": 12.0,
                "humidity": 92.0,
                "cloud_coverage": CloudCoverage.BROKEN.value,
                "fog_type": FogType.RADIATION_FOG.value,
                "visibility": 500.0,
                "tags": ["fog", "mysterious", "calm"],
                "steps": [
                    {"weather_type": WeatherType.FOG.value, "intensity": WeatherIntensity.MODERATE.value, "offset_seconds": 0},
                    {"weather_type": WeatherType.CLEAR.value, "intensity": WeatherIntensity.LIGHT.value, "offset_seconds": 1800},
                ],
            },
            {
                "pattern_id": "pattern_aurora_night",
                "name": "Aurora Night",
                "description": "Cold clear night lit by dancing auroras.",
                "weather_type": WeatherType.AURORA.value,
                "intensity": WeatherIntensity.LIGHT.value,
                "duration": 9000.0,
                "wind_direction": WindDirection.N.value,
                "wind_speed": 2.0,
                "temperature": -20.0,
                "humidity": 55.0,
                "cloud_coverage": CloudCoverage.CLEAR.value,
                "fog_type": FogType.NONE.value,
                "visibility": 9500.0,
                "tags": ["aurora", "night", "beautiful", "cold"],
                "steps": [
                    {"weather_type": WeatherType.CLEAR.value, "intensity": WeatherIntensity.LIGHT.value, "offset_seconds": 0},
                    {"weather_type": WeatherType.AURORA.value, "intensity": WeatherIntensity.LIGHT.value, "offset_seconds": 1800},
                ],
            },
        ]

        for seed in pattern_seeds:
            pattern = WeatherPattern(
                pattern_id=seed["pattern_id"],
                name=seed["name"],
                description=seed["description"],
                weather_type=seed["weather_type"],
                intensity=seed["intensity"],
                duration=max(0.0, _safe_float(seed["duration"], 3600.0)),
                wind_direction=seed["wind_direction"],
                wind_speed=_clamp(
                    _safe_float(seed["wind_speed"], 0.0),
                    _WIND_SPEED_MIN, _WIND_SPEED_MAX,
                ),
                temperature=_clamp(
                    _safe_float(seed["temperature"], 20.0),
                    _TEMPERATURE_MIN, _TEMPERATURE_MAX,
                ),
                humidity=_clamp(
                    _safe_float(seed["humidity"], 50.0),
                    _HUMIDITY_MIN, _HUMIDITY_MAX,
                ),
                cloud_coverage=seed["cloud_coverage"],
                fog_type=seed["fog_type"],
                visibility=_clamp(
                    _safe_float(seed["visibility"], 10000.0),
                    _VISIBILITY_MIN, _VISIBILITY_MAX,
                ),
                steps=list(seed.get("steps", [])),
                tags=list(seed.get("tags", [])),
                enabled=True,
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
            )
            self._patterns[pattern.pattern_id] = pattern

        # --- Transitions (6) ---
        transition_seeds: List[Dict[str, Any]] = [
            {
                "transition_id": "trans_clear_to_rain",
                "zone_id": "zone_temperate_field",
                "from_type": WeatherType.CLEAR.value,
                "to_type": WeatherType.RAIN.value,
                "from_intensity": WeatherIntensity.LIGHT.value,
                "to_intensity": WeatherIntensity.MODERATE.value,
                "duration": 120.0, "easing": "ease_in_out", "active": False, "progress": 0.0,
            },
            {
                "transition_id": "trans_rain_to_thunderstorm",
                "zone_id": "zone_tropical_jungle",
                "from_type": WeatherType.RAIN.value,
                "to_type": WeatherType.THUNDERSTORM.value,
                "from_intensity": WeatherIntensity.MODERATE.value,
                "to_intensity": WeatherIntensity.HEAVY.value,
                "duration": 90.0, "easing": "ease_in", "active": True, "progress": 0.0,
            },
            {
                "transition_id": "trans_clear_to_blizzard",
                "zone_id": "zone_arctic_tundra",
                "from_type": WeatherType.SNOW.value,
                "to_type": WeatherType.BLIZZARD.value,
                "from_intensity": WeatherIntensity.MODERATE.value,
                "to_intensity": WeatherIntensity.EXTREME.value,
                "duration": 150.0, "easing": "ease_in_out", "active": False, "progress": 0.0,
            },
            {
                "transition_id": "trans_fog_to_clear",
                "zone_id": "zone_temperate_field",
                "from_type": WeatherType.FOG.value,
                "to_type": WeatherType.CLEAR.value,
                "from_intensity": WeatherIntensity.MODERATE.value,
                "to_intensity": WeatherIntensity.LIGHT.value,
                "duration": 180.0, "easing": "ease_out", "active": False, "progress": 0.0,
            },
            {
                "transition_id": "trans_heat_to_sandstorm",
                "zone_id": "zone_desert_oasis",
                "from_type": WeatherType.HEAT_WAVE.value,
                "to_type": WeatherType.SANDSTORM.value,
                "from_intensity": WeatherIntensity.HEAVY.value,
                "to_intensity": WeatherIntensity.EXTREME.value,
                "duration": 100.0, "easing": "linear", "active": False, "progress": 0.0,
            },
            {
                "transition_id": "trans_aurora_to_clear",
                "zone_id": "zone_arctic_tundra",
                "from_type": WeatherType.AURORA.value,
                "to_type": WeatherType.CLEAR.value,
                "from_intensity": WeatherIntensity.LIGHT.value,
                "to_intensity": WeatherIntensity.LIGHT.value,
                "duration": 200.0, "easing": "ease_in_out", "active": False, "progress": 0.0,
            },
        ]
        for seed in transition_seeds:
            transition = WeatherTransition(
                transition_id=seed["transition_id"],
                zone_id=seed["zone_id"],
                from_type=seed["from_type"],
                to_type=seed["to_type"],
                from_intensity=seed["from_intensity"],
                to_intensity=seed["to_intensity"],
                duration=max(0.0, _safe_float(seed["duration"], 1.0)),
                easing=seed.get("easing", "linear"),
                active=bool(seed.get("active", False)),
                progress=_clamp(_safe_float(seed.get("progress"), 0.0), 0.0, 1.0),
                created_at=now,
                metadata={"seed": True},
            )
            self._transitions[transition.transition_id] = transition

        # --- Forecasts (5) ---
        forecast_seeds: List[Dict[str, Any]] = [
            {
                "forecast_id": "forecast_temperate_field",
                "zone_id": "zone_temperate_field",
                "hours_ahead": 24,
                "entries": [
                    {"weather_type": WeatherType.CLEAR.value, "intensity": WeatherIntensity.LIGHT.value, "temperature": 18.0, "hour_offset": 0},
                    {"weather_type": WeatherType.CLOUDY.value, "intensity": WeatherIntensity.MODERATE.value, "temperature": 17.0, "hour_offset": 6},
                    {"weather_type": WeatherType.RAIN.value, "intensity": WeatherIntensity.MODERATE.value, "temperature": 15.0, "hour_offset": 12},
                    {"weather_type": WeatherType.CLEAR.value, "intensity": WeatherIntensity.LIGHT.value, "temperature": 16.0, "hour_offset": 18},
                ],
                "confidence": 0.82,
            },
            {
                "forecast_id": "forecast_desert_oasis",
                "zone_id": "zone_desert_oasis",
                "hours_ahead": 12,
                "entries": [
                    {"weather_type": WeatherType.HEAT_WAVE.value, "intensity": WeatherIntensity.EXTREME.value, "temperature": 42.0, "hour_offset": 0},
                    {"weather_type": WeatherType.CLEAR.value, "intensity": WeatherIntensity.LIGHT.value, "temperature": 28.0, "hour_offset": 6},
                    {"weather_type": WeatherType.WINDY.value, "intensity": WeatherIntensity.MODERATE.value, "temperature": 30.0, "hour_offset": 12},
                ],
                "confidence": 0.75,
            },
            {
                "forecast_id": "forecast_arctic_tundra",
                "zone_id": "zone_arctic_tundra",
                "hours_ahead": 48,
                "entries": [
                    {"weather_type": WeatherType.SNOW.value, "intensity": WeatherIntensity.MODERATE.value, "temperature": -8.0, "hour_offset": 0},
                    {"weather_type": WeatherType.BLIZZARD.value, "intensity": WeatherIntensity.EXTREME.value, "temperature": -18.0, "hour_offset": 12},
                    {"weather_type": WeatherType.SNOW.value, "intensity": WeatherIntensity.LIGHT.value, "temperature": -10.0, "hour_offset": 24},
                    {"weather_type": WeatherType.AURORA.value, "intensity": WeatherIntensity.LIGHT.value, "temperature": -22.0, "hour_offset": 36},
                ],
                "confidence": 0.68,
            },
            {
                "forecast_id": "forecast_tropical_jungle",
                "zone_id": "zone_tropical_jungle",
                "hours_ahead": 24,
                "entries": [
                    {"weather_type": WeatherType.RAIN.value, "intensity": WeatherIntensity.MODERATE.value, "temperature": 27.0, "hour_offset": 0},
                    {"weather_type": WeatherType.THUNDERSTORM.value, "intensity": WeatherIntensity.HEAVY.value, "temperature": 25.0, "hour_offset": 8},
                    {"weather_type": WeatherType.HEAVY_RAIN.value, "intensity": WeatherIntensity.HEAVY.value, "temperature": 24.0, "hour_offset": 16},
                ],
                "confidence": 0.79,
            },
            {
                "forecast_id": "forecast_coastal_bay",
                "zone_id": "zone_coastal_bay",
                "hours_ahead": 36,
                "entries": [
                    {"weather_type": WeatherType.WINDY.value, "intensity": WeatherIntensity.MODERATE.value, "temperature": 16.0, "hour_offset": 0},
                    {"weather_type": WeatherType.FOG.value, "intensity": WeatherIntensity.MODERATE.value, "temperature": 14.0, "hour_offset": 12},
                    {"weather_type": WeatherType.CLEAR.value, "intensity": WeatherIntensity.LIGHT.value, "temperature": 18.0, "hour_offset": 24},
                ],
                "confidence": 0.71,
            },
        ]
        for seed in forecast_seeds:
            forecast = WeatherForecast(
                forecast_id=seed["forecast_id"],
                zone_id=seed["zone_id"],
                hours_ahead=max(1, _safe_int(seed["hours_ahead"], 24)),
                issued_at=now,
                entries=list(seed.get("entries", [])),
                confidence=_clamp(
                    _safe_float(seed.get("confidence"), 0.8),
                    _CONFIDENCE_MIN, _CONFIDENCE_MAX,
                ),
                created_at=now,
                metadata={"seed": True},
            )
            self._forecasts[forecast.forecast_id] = forecast

        # --- Events (6) ---
        event_seeds: List[Tuple[str, str, str]] = [
            (
                WeatherEventKind.ZONE_CREATED.value, "zone_temperate_field",
                "Seeded zone 'Temperate Field'",
            ),
            (
                WeatherEventKind.ZONE_CREATED.value, "zone_arctic_tundra",
                "Seeded zone 'Arctic Tundra'",
            ),
            (
                WeatherEventKind.WEATHER_CHANGED.value, "zone_tropical_jungle",
                "Set weather to 'rain' on 'Tropical Jungle'",
            ),
            (
                WeatherEventKind.STORM_STARTED.value, "zone_tropical_jungle",
                "Storm 'thunderstorm' began on 'Tropical Jungle'",
            ),
            (
                WeatherEventKind.WIND_SHIFTED.value, "zone_coastal_bay",
                "Wind shifted to E at 12 m/s on 'Coastal Bay'",
            ),
            (
                WeatherEventKind.WEATHER_CHANGED.value, "zone_desert_oasis",
                "Set weather to 'heat_wave' on 'Desert Oasis'",
            ),
        ]
        for (etype, zid, desc) in event_seeds:
            self._event_counter += 1
            self._events.append(
                WeatherEvent(
                    event_id=f"wevt_{self._event_counter:08d}",
                    timestamp=now,
                    event_type=etype,
                    zone_id=zid,
                    description=desc,
                    metadata={"seed": True},
                )
            )

        # --- Stats ---
        self._refresh_stats()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        zone_id: str = "",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event and trim the event log to capacity."""
        self._event_counter += 1
        event = WeatherEvent(
            event_id=f"wevt_{self._event_counter:08d}",
            timestamp=_now(),
            event_type=event_type,
            zone_id=zone_id,
            description=description,
            metadata=metadata or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from the current stores."""
        self._stats.total_zones = len(self._zones)
        self._stats.total_patterns = len(self._patterns)
        self._stats.total_transitions = len(self._transitions)
        self._stats.total_forecasts = len(self._forecasts)
        self._stats.active_zones = sum(
            1 for z in self._zones.values() if z.active
        )
        self._stats.active_transitions = sum(
            1 for t in self._transitions.values() if t.active
        )
        self._stats.tick_count = self._tick_count

    def _resolve_zone(self, zone_id: str) -> Optional[WeatherZone]:
        """Return a zone or None; taking the lock is the caller's job."""
        return self._zones.get(zone_id)

    def _resolve_pattern(self, pattern_id: str) -> Optional[WeatherPattern]:
        return self._patterns.get(pattern_id)

    def _resolve_transition(self, transition_id: str) -> Optional[WeatherTransition]:
        return self._transitions.get(transition_id)

    def _resolve_forecast(self, forecast_id: str) -> Optional[WeatherForecast]:
        return self._forecasts.get(forecast_id)

    def _normalize_weather_type(self, weather_type: str) -> str:
        """Return the canonical weather type value name for an input.

        Accepts either a WeatherType member, its value, or a raw string.
        Unknown strings are returned as-is so custom weather types remain
        usable.
        """
        if isinstance(weather_type, WeatherType):
            return weather_type.value
        return str(weather_type)

    def _apply_state_to_zone(
        self, zone: WeatherZone, state: WeatherState
    ) -> None:
        """Write a weather state onto a zone and synchronize its wind,
        atmosphere, and cloud layer to match the state's scalars."""
        zone.current_state = state
        # Synchronize the wind state.
        if zone.wind is None:
            zone.wind = _make_wind_state(
                direction=state.wind_direction, speed=state.wind_speed
            )
        else:
            zone.wind.direction = state.wind_direction
            zone.wind.speed = state.wind_speed
            zone.wind.gusts = max(zone.wind.gusts, state.wind_speed * 1.4)
            zone.wind.updated_at = _now()
        # Synchronize the atmosphere.
        if zone.atmosphere is None:
            zone.atmosphere = _make_atmosphere(
                temperature=state.temperature,
                humidity=state.humidity,
                pressure=state.pressure,
                visibility=state.visibility,
            )
        else:
            zone.atmosphere.temperature = state.temperature
            zone.atmosphere.humidity = state.humidity
            zone.atmosphere.pressure = state.pressure
            zone.atmosphere.visibility = state.visibility
            zone.atmosphere.updated_at = _now()
        # Synchronize the cloud layer.
        if zone.cloud_layer is None:
            zone.cloud_layer = _make_cloud_layer(coverage=state.cloud_coverage)
        else:
            zone.cloud_layer.coverage = state.cloud_coverage
            zone.cloud_layer.updated_at = _now()
        zone.updated_at = _now()

    # ------------------------------------------------------------------
    # Zone Management
    # ------------------------------------------------------------------

    def register_zone(
        self,
        zone_id: str,
        name: str,
        biome: str = "temperate",
        season: str = Season.SPRING.value,
        latitude: float = 0.0,
        longitude: float = 0.0,
        area: float = 0.0,
        weather_type: str = WeatherType.CLEAR.value,
        intensity: str = WeatherIntensity.LIGHT.value,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        wind_direction: str = WindDirection.N.value,
        wind_speed: float = 0.0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[WeatherZone]]:
        """Register a new weather zone.

        Args:
            zone_id: Unique zone identifier.
            name: Display name.
            biome: Free-form biome name (e.g. "temperate", "desert").
            season: The Season value name.
            latitude: Latitude in decimal degrees.
            longitude: Longitude in decimal degrees.
            area: Area in square kilometers.
            weather_type: The initial WeatherType value name.
            intensity: The initial WeatherIntensity value name.
            temperature: Optional initial temperature; defaults to the
                biome/season baseline blended with the weather type.
            humidity: Optional initial humidity; defaults to the weather
                type property.
            wind_direction: The initial WindDirection value name.
            wind_speed: Initial sustained wind speed in m/s.
            tags: Searchable tags.
            metadata: Free-form extension data.

        Returns:
            A ``(ok, message, zone)`` tuple. ``ok`` is False when the id
            already exists or the id is empty.
        """
        if not zone_id:
            return False, "zone_id is required", None
        with self._lock:
            if zone_id in self._zones:
                return False, "zone_id already exists", None
            if len(self._zones) >= self._config.max_zones:
                _evict_fifo_dict(self._zones, self._config.max_zones)

            season_enum = _coerce_enum(Season, season, Season.SPRING)
            direction_enum = _coerce_enum(WindDirection, wind_direction, WindDirection.N)

            # Resolve the effective temperature: caller value first, then a
            # blend of the biome/season baseline and the weather-type
            # default so seeded geography is reflected.
            if temperature is None:
                biome_temp = _biome_base_temperature(biome, season_enum.value)
                props_temp = _weather_properties(
                    self._normalize_weather_type(weather_type)
                )["temperature"]
                effective_temp = (biome_temp + props_temp) / 2.0
            else:
                effective_temp = _safe_float(temperature, 20.0)

            state = _make_weather_state(
                weather_type=weather_type,
                intensity=intensity,
                temperature=effective_temp,
                humidity=humidity,
                wind_direction=direction_enum.value,
                wind_speed=wind_speed,
                duration=3600.0,
            )
            wind = _make_wind_state(
                direction=direction_enum.value, speed=wind_speed
            )
            atmosphere = _make_atmosphere(
                temperature=state.temperature,
                humidity=state.humidity,
                pressure=state.pressure,
                visibility=state.visibility,
            )
            cloud = _make_cloud_layer(coverage=state.cloud_coverage)
            now = _now()
            zone = WeatherZone(
                zone_id=zone_id,
                name=name or zone_id,
                biome=biome or "temperate",
                season=season_enum.value,
                latitude=_clamp(
                    _safe_float(latitude, 0.0), _LATITUDE_MIN, _LATITUDE_MAX
                ),
                longitude=_clamp(
                    _safe_float(longitude, 0.0),
                    _LONGITUDE_MIN, _LONGITUDE_MAX,
                ),
                area=max(0.0, _safe_float(area, 0.0)),
                current_state=state,
                wind=wind,
                atmosphere=atmosphere,
                cloud_layer=cloud,
                status=WeatherStatus.ACTIVE.value,
                active=True,
                tags=list(tags or []),
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._zones[zone_id] = zone
            self._refresh_stats()
            self._emit(
                WeatherEventKind.ZONE_CREATED.value,
                zone_id,
                f"Registered zone '{zone.name}'",
                {"biome": zone.biome, "season": zone.season},
            )
            return True, "registered", zone

    def get_zone(self, zone_id: str) -> Optional[WeatherZone]:
        """Retrieve a zone by its identifier."""
        with self._lock:
            return self._resolve_zone(zone_id)

    def list_zones(
        self,
        biome: Optional[str] = None,
        season: Optional[str] = None,
        active: Optional[bool] = None,
        weather_type: Optional[str] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[WeatherZone]:
        """List zones with optional filters.

        Args:
            biome: Filter by biome name.
            season: Filter by Season value name.
            active: Filter by active state.
            weather_type: Filter by current WeatherType value name.
            limit: Maximum number of zones to return.

        Returns:
            A list of matching WeatherZone objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            season_value = None
            if season is not None:
                season_enum = _coerce_enum(Season, season, None)
                season_value = season_enum.value if season_enum else season
            type_value = None
            if weather_type is not None:
                type_enum = _coerce_enum(WeatherType, weather_type, None)
                type_value = type_enum.value if type_enum else weather_type
            results: List[WeatherZone] = []
            for zone in self._zones.values():
                if biome is not None and zone.biome != biome:
                    continue
                if season_value is not None and zone.season != season_value:
                    continue
                if active is not None and zone.active != active:
                    continue
                if type_value is not None and (
                    zone.current_state is None
                    or zone.current_state.weather_type != type_value
                ):
                    continue
                results.append(zone)
                if len(results) >= cap:
                    break
            return results

    def remove_zone(self, zone_id: str) -> Tuple[bool, str]:
        """Remove a zone by its identifier.

        Also removes any transitions and forecasts bound to the zone.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return False, "not found"
            del self._zones[zone_id]
            # Detach transitions bound to this zone.
            for tid in [
                t.transition_id
                for t in self._transitions.values()
                if t.zone_id == zone_id
            ]:
                self._transitions.pop(tid, None)
            # Detach forecasts bound to this zone.
            for fid in [
                f.forecast_id
                for f in self._forecasts.values()
                if f.zone_id == zone_id
            ]:
                self._forecasts.pop(fid, None)
            self._refresh_stats()
            self._emit(
                WeatherEventKind.ZONE_REMOVED.value,
                zone_id,
                f"Removed zone '{zone.name}'",
            )
            return True, "removed"

    def update_zone(
        self, zone_id: str, **kwargs: Any
    ) -> Tuple[bool, str, Optional[WeatherZone]]:
        """Update mutable fields on an existing zone.

        Accepts any subset of WeatherZone scalar fields (``name``,
        ``biome``, ``latitude``, ``longitude``, ``area``, ``active``,
        ``tags``, ``metadata``). Enum-typed fields (``season``) are
        coerced via their respective enums. The ``updated_at`` timestamp
        is refreshed.

        Returns:
            A ``(ok, message, zone)`` tuple.
        """
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return False, "not found", None
            # Scalar string fields.
            for key in ("name", "biome"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(zone, key, str(kwargs[key]))
            # Numeric fields.
            if "latitude" in kwargs and kwargs["latitude"] is not None:
                zone.latitude = _clamp(
                    _safe_float(kwargs["latitude"], zone.latitude),
                    _LATITUDE_MIN, _LATITUDE_MAX,
                )
            if "longitude" in kwargs and kwargs["longitude"] is not None:
                zone.longitude = _clamp(
                    _safe_float(kwargs["longitude"], zone.longitude),
                    _LONGITUDE_MIN, _LONGITUDE_MAX,
                )
            if "area" in kwargs and kwargs["area"] is not None:
                zone.area = max(0.0, _safe_float(kwargs["area"], zone.area))
            # Boolean fields.
            if "active" in kwargs and kwargs["active"] is not None:
                zone.active = bool(kwargs["active"])
            # List fields.
            if "tags" in kwargs and kwargs["tags"] is not None:
                zone.tags = list(kwargs["tags"])
            # Metadata merge.
            if "metadata" in kwargs and kwargs["metadata"] is not None:
                if isinstance(kwargs["metadata"], dict):
                    zone.metadata.update(kwargs["metadata"])
            # Enum fields.
            if "season" in kwargs and kwargs["season"] is not None:
                enum_val = _coerce_enum(Season, kwargs["season"], None)
                if enum_val is not None:
                    zone.season = enum_val.value
            zone.updated_at = _now()
            self._refresh_stats()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                zone_id,
                f"Updated zone '{zone.name}'",
            )
            return True, "updated", zone

    # ------------------------------------------------------------------
    # Weather Control
    # ------------------------------------------------------------------

    def set_weather(
        self,
        zone_id: str,
        weather_type: str,
        intensity: str = WeatherIntensity.MODERATE.value,
        duration: float = 3600.0,
    ) -> Tuple[bool, str, Optional[WeatherState]]:
        """Set the weather on a zone, replacing its current state.

        Builds a new WeatherState from the weather-type defaults (with
        the caller-supplied intensity and duration), synchronizes the
        zone's wind, atmosphere, and cloud layer, and emits a
        weather-changed (or storm-started) event.

        Args:
            zone_id: The zone to update.
            weather_type: The WeatherType value name to apply.
            intensity: The WeatherIntensity value name.
            duration: Intended duration of the condition in seconds.

        Returns:
            A ``(ok, message, state)`` tuple.
        """
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return False, "zone not found", None
            type_enum = _coerce_enum(WeatherType, weather_type, WeatherType.CLEAR)
            intensity_enum = _coerce_enum(
                WeatherIntensity, intensity, WeatherIntensity.MODERATE
            )
            # Preserve the zone's current wind direction and a blended
            # temperature so the change feels continuous.
            prev_direction = (
                zone.wind.direction if zone.wind else WindDirection.N.value
            )
            prev_temp = (
                zone.current_state.temperature
                if zone.current_state is not None
                else _biome_base_temperature(zone.biome, zone.season)
            )
            props = _weather_properties(type_enum.value)
            blended_temp = (prev_temp + props["temperature"]) / 2.0
            state = _make_weather_state(
                weather_type=type_enum.value,
                intensity=intensity_enum.value,
                temperature=blended_temp,
                wind_direction=prev_direction,
                wind_speed=props["wind_speed"],
                duration=duration,
            )
            # Apply global fog toggle from config.
            if not self._config.enable_fog and state.fog_type != FogType.NONE.value:
                state.fog_type = FogType.NONE.value
            self._apply_state_to_zone(zone, state)
            zone.status = WeatherStatus.ACTIVE.value
            self._stats.total_weather_changes += 1
            self._refresh_stats()
            event_kind = WeatherEventKind.WEATHER_CHANGED.value
            if type_enum.value in _STORM_WEATHER_TYPES:
                event_kind = WeatherEventKind.STORM_STARTED.value
                self._stats.total_storms += 1
            self._emit(
                event_kind,
                zone_id,
                f"Set weather to '{type_enum.value}' on '{zone.name}'",
                {
                    "weather_type": type_enum.value,
                    "intensity": intensity_enum.value,
                    "duration": state.duration,
                },
            )
            return True, "set", state

    def get_weather(self, zone_id: str) -> Optional[WeatherState]:
        """Return the current weather state for a zone, or None."""
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return None
            return zone.current_state

    def transition_to(
        self,
        zone_id: str,
        target_type: str,
        duration: float = 120.0,
        target_intensity: Optional[str] = None,
        easing: str = "ease_in_out",
    ) -> Tuple[bool, str, Optional[WeatherTransition]]:
        """Begin a smooth transition to a target weather type.

        Creates a WeatherTransition from the zone's current weather type
        to the target type over the given duration. The transition is
        marked active and advanced by ``tick``; when it completes the
        target weather is applied to the zone.

        Args:
            zone_id: The zone to transition.
            target_type: The destination WeatherType value name.
            duration: Transition duration in seconds.
            target_intensity: Optional destination WeatherIntensity value
                name; defaults to the target type's default intensity.
            easing: Easing function name.

        Returns:
            A ``(ok, message, transition)`` tuple.
        """
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return False, "zone not found", None
            type_enum = _coerce_enum(WeatherType, target_type, WeatherType.CLEAR)
            props = _weather_properties(type_enum.value)
            intensity_enum = _coerce_enum(
                WeatherIntensity, target_intensity, None
            )
            if intensity_enum is None:
                intensity_enum = WeatherIntensity(props["default_intensity"])
            from_state = zone.current_state
            from_type = (
                from_state.weather_type if from_state else WeatherType.CLEAR.value
            )
            from_intensity = (
                from_state.intensity if from_state else WeatherIntensity.LIGHT.value
            )
            self._transition_counter += 1
            transition_id = f"trans_{self._transition_counter:08d}"
            transition = WeatherTransition(
                transition_id=transition_id,
                zone_id=zone_id,
                from_type=from_type,
                to_type=type_enum.value,
                from_intensity=from_intensity,
                to_intensity=intensity_enum.value,
                duration=max(0.0, _safe_float(duration, 120.0)),
                easing=easing or "ease_in_out",
                active=True,
                progress=0.0,
                created_at=_now(),
                metadata={},
            )
            self._transitions[transition_id] = transition
            _evict_fifo_dict(self._transitions, self._config.max_transitions)
            zone.status = WeatherStatus.TRANSITIONING.value
            zone.updated_at = _now()
            self._refresh_stats()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                zone_id,
                f"Transitioning '{zone.name}' to '{type_enum.value}'",
                {
                    "transition_id": transition_id,
                    "from_type": from_type,
                    "to_type": type_enum.value,
                    "duration": transition.duration,
                },
            )
            return True, "transitioning", transition

    def get_transition(self, transition_id: str) -> Optional[WeatherTransition]:
        """Retrieve a transition by its identifier."""
        with self._lock:
            return self._resolve_transition(transition_id)

    def list_transitions(
        self,
        zone_id: Optional[str] = None,
        active_only: Optional[bool] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[WeatherTransition]:
        """List transitions with optional filters.

        Args:
            zone_id: Filter by zone id.
            active_only: When ``True`` return only active transitions; when
                ``False`` return only inactive ones; when ``None`` return
                all transitions regardless of active state.
            limit: Maximum number of transitions to return.

        Returns:
            A list of matching WeatherTransition objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            results: List[WeatherTransition] = []
            for transition in self._transitions.values():
                if zone_id is not None and transition.zone_id != zone_id:
                    continue
                if active_only is True and not transition.active:
                    continue
                if active_only is False and transition.active:
                    continue
                results.append(transition)
                if len(results) >= cap:
                    break
            return results

    def update_transition(
        self, transition_id: str, progress: float
    ) -> Tuple[bool, str, Optional[WeatherTransition]]:
        """Update the progress of a transition.

        Progress is clamped to ``[0.0, 1.0]``. When progress reaches 1.0
        the transition is marked inactive and the target weather is
        applied to the zone. When progress moves above 0.0 the transition
        is marked active.

        Returns:
            A ``(ok, message, transition)`` tuple.
        """
        with self._lock:
            transition = self._resolve_transition(transition_id)
            if transition is None:
                return False, "not found", None
            transition.progress = _clamp(_safe_float(progress, 0.0), 0.0, 1.0)
            transition.active = 0.0 < transition.progress < 1.0
            if transition.progress >= 1.0:
                # Apply the target weather to the zone on completion.
                zone = self._resolve_zone(transition.zone_id)
                if zone is not None:
                    self.set_weather(
                        transition.zone_id,
                        transition.to_type,
                        transition.to_intensity,
                    )
                    zone.status = WeatherStatus.ACTIVE.value
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                transition.zone_id,
                f"Updated transition '{transition_id}' progress to {transition.progress}",
                {"transition_id": transition_id, "progress": transition.progress},
            )
            return True, "updated", transition

    def remove_transition(self, transition_id: str) -> Tuple[bool, str]:
        """Remove a transition by its identifier.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            transition = self._transitions.get(transition_id)
            if transition is None:
                return False, "not found"
            del self._transitions[transition_id]
            self._refresh_stats()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                transition.zone_id,
                f"Removed transition '{transition_id}'",
                {"transition_id": transition_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Pattern Management
    # ------------------------------------------------------------------

    def register_pattern(
        self,
        pattern_id: str,
        name: str,
        weather_type: str = WeatherType.CLEAR.value,
        description: str = "",
        intensity: str = WeatherIntensity.MODERATE.value,
        duration: float = 3600.0,
        wind_direction: str = WindDirection.N.value,
        wind_speed: float = 0.0,
        temperature: float = 20.0,
        humidity: float = 50.0,
        cloud_coverage: str = CloudCoverage.SCATTERED.value,
        fog_type: str = FogType.NONE.value,
        visibility: float = 10000.0,
        steps: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[WeatherPattern]]:
        """Register a new weather pattern.

        Args:
            pattern_id: Unique pattern identifier.
            name: Display name.
            weather_type: The WeatherType value name the pattern produces.
            description: Human-readable description.
            intensity: The WeatherIntensity value name.
            duration: Pattern duration in seconds.
            wind_direction: The WindDirection value name.
            wind_speed: Wind speed in m/s.
            temperature: Target temperature in Celsius.
            humidity: Target humidity in percent.
            cloud_coverage: The CloudCoverage value name.
            fog_type: The FogType value name.
            visibility: Target visibility in meters.
            steps: Ordered list of step dicts describing the sequence.
            tags: Searchable tags.
            enabled: Whether the pattern is eligible for application.
            metadata: Free-form extension data.

        Returns:
            A ``(ok, message, pattern)`` tuple. ``ok`` is False when the
            id already exists or the id is empty.
        """
        if not pattern_id:
            return False, "pattern_id is required", None
        with self._lock:
            if pattern_id in self._patterns:
                return False, "pattern_id already exists", None
            if len(self._patterns) >= self._config.max_patterns:
                _evict_fifo_dict(self._patterns, self._config.max_patterns)

            type_enum = _coerce_enum(WeatherType, weather_type, WeatherType.CLEAR)
            intensity_enum = _coerce_enum(
                WeatherIntensity, intensity, WeatherIntensity.MODERATE
            )
            direction_enum = _coerce_enum(WindDirection, wind_direction, WindDirection.N)
            cloud_enum = _coerce_enum(
                CloudCoverage, cloud_coverage, CloudCoverage.SCATTERED
            )
            fog_enum = _coerce_enum(FogType, fog_type, FogType.NONE)
            now = _now()
            pattern = WeatherPattern(
                pattern_id=pattern_id,
                name=name or pattern_id,
                description=description,
                weather_type=type_enum.value,
                intensity=intensity_enum.value,
                duration=max(0.0, _safe_float(duration, 3600.0)),
                wind_direction=direction_enum.value,
                wind_speed=_clamp(
                    _safe_float(wind_speed, 0.0),
                    _WIND_SPEED_MIN, _WIND_SPEED_MAX,
                ),
                temperature=_clamp(
                    _safe_float(temperature, 20.0),
                    _TEMPERATURE_MIN, _TEMPERATURE_MAX,
                ),
                humidity=_clamp(
                    _safe_float(humidity, 50.0),
                    _HUMIDITY_MIN, _HUMIDITY_MAX,
                ),
                cloud_coverage=cloud_enum.value,
                fog_type=fog_enum.value,
                visibility=_clamp(
                    _safe_float(visibility, 10000.0),
                    _VISIBILITY_MIN, _VISIBILITY_MAX,
                ),
                steps=list(steps or []),
                tags=list(tags or []),
                enabled=bool(enabled),
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._patterns[pattern_id] = pattern
            self._refresh_stats()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                "",
                f"Registered pattern '{pattern.name}'",
                {"pattern_id": pattern_id, "weather_type": pattern.weather_type},
            )
            return True, "registered", pattern

    def get_pattern(self, pattern_id: str) -> Optional[WeatherPattern]:
        """Retrieve a pattern by its identifier."""
        with self._lock:
            return self._resolve_pattern(pattern_id)

    def list_patterns(
        self,
        weather_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        tag: Optional[str] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[WeatherPattern]:
        """List patterns with optional filters.

        Args:
            weather_type: Filter by WeatherType value name.
            enabled: Filter by enabled state.
            tag: Filter by tag membership.
            limit: Maximum number of patterns to return.

        Returns:
            A list of matching WeatherPattern objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            type_value = None
            if weather_type is not None:
                type_enum = _coerce_enum(WeatherType, weather_type, None)
                type_value = type_enum.value if type_enum else weather_type
            results: List[WeatherPattern] = []
            for pattern in self._patterns.values():
                if type_value is not None and pattern.weather_type != type_value:
                    continue
                if enabled is not None and pattern.enabled != enabled:
                    continue
                if tag is not None and tag not in pattern.tags:
                    continue
                results.append(pattern)
                if len(results) >= cap:
                    break
            return results

    def remove_pattern(self, pattern_id: str) -> Tuple[bool, str]:
        """Remove a pattern by its identifier.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            pattern = self._patterns.get(pattern_id)
            if pattern is None:
                return False, "not found"
            del self._patterns[pattern_id]
            self._refresh_stats()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                "",
                f"Removed pattern '{pattern.name}'",
                {"pattern_id": pattern_id},
            )
            return True, "removed"

    def update_pattern(
        self, pattern_id: str, **kwargs: Any
    ) -> Tuple[bool, str, Optional[WeatherPattern]]:
        """Update mutable fields on an existing pattern.

        Accepts any subset of WeatherPattern fields. Enum-typed fields
        (``weather_type``, ``intensity``, ``wind_direction``,
        ``cloud_coverage``, ``fog_type``) are coerced via their respective
        enums. Numeric fields are clamped. The ``updated_at`` timestamp is
        refreshed.

        Returns:
            A ``(ok, message, pattern)`` tuple.
        """
        with self._lock:
            pattern = self._resolve_pattern(pattern_id)
            if pattern is None:
                return False, "not found", None
            # Scalar string fields.
            for key in ("name", "description"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(pattern, key, str(kwargs[key]))
            # Boolean fields.
            if "enabled" in kwargs and kwargs["enabled"] is not None:
                pattern.enabled = bool(kwargs["enabled"])
            # Numeric fields.
            numeric_bounds = {
                "duration": (0.0, None),
                "wind_speed": (_WIND_SPEED_MIN, _WIND_SPEED_MAX),
                "temperature": (_TEMPERATURE_MIN, _TEMPERATURE_MAX),
                "humidity": (_HUMIDITY_MIN, _HUMIDITY_MAX),
                "visibility": (_VISIBILITY_MIN, _VISIBILITY_MAX),
            }
            for key, (lo, hi) in numeric_bounds.items():
                if key in kwargs and kwargs[key] is not None:
                    val = _safe_float(kwargs[key], getattr(pattern, key))
                    if hi is not None:
                        val = _clamp(val, lo, hi)
                    else:
                        val = max(lo, val)
                    setattr(pattern, key, val)
            # List fields.
            if "tags" in kwargs and kwargs["tags"] is not None:
                pattern.tags = list(kwargs["tags"])
            if "steps" in kwargs and kwargs["steps"] is not None:
                pattern.steps = list(kwargs["steps"])
            # Metadata merge.
            if "metadata" in kwargs and kwargs["metadata"] is not None:
                if isinstance(kwargs["metadata"], dict):
                    pattern.metadata.update(kwargs["metadata"])
            # Enum fields.
            enum_fields = {
                "weather_type": WeatherType,
                "intensity": WeatherIntensity,
                "wind_direction": WindDirection,
                "cloud_coverage": CloudCoverage,
                "fog_type": FogType,
            }
            for key, enum_cls in enum_fields.items():
                if key in kwargs and kwargs[key] is not None:
                    enum_val = _coerce_enum(enum_cls, kwargs[key], None)
                    if enum_val is not None:
                        setattr(pattern, key, enum_val.value)
            pattern.updated_at = _now()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                "",
                f"Updated pattern '{pattern.name}'",
            )
            return True, "updated", pattern

    def apply_pattern(
        self, zone_id: str, pattern_id: str
    ) -> Tuple[bool, str, Optional[WeatherState]]:
        """Apply a registered pattern to a zone.

        Builds a WeatherState from the pattern's target properties and
        writes it onto the zone. The pattern's wind, temperature,
        humidity, cloud coverage, fog type, and visibility are all
        applied. Storm patterns emit a storm-started event.

        Args:
            zone_id: The zone to apply the pattern to.
            pattern_id: The pattern to apply.

        Returns:
            A ``(ok, message, state)`` tuple. Fails when the zone or
            pattern is missing or the pattern is disabled.
        """
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return False, "zone not found", None
            pattern = self._resolve_pattern(pattern_id)
            if pattern is None:
                return False, "pattern not found", None
            if not pattern.enabled:
                return False, "pattern is disabled", None
            state = _make_weather_state(
                weather_type=pattern.weather_type,
                intensity=pattern.intensity,
                temperature=pattern.temperature,
                humidity=pattern.humidity,
                visibility=pattern.visibility,
                wind_direction=pattern.wind_direction,
                wind_speed=pattern.wind_speed,
                cloud_coverage=pattern.cloud_coverage,
                fog_type=pattern.fog_type,
                duration=pattern.duration,
            )
            if not self._config.enable_fog and state.fog_type != FogType.NONE.value:
                state.fog_type = FogType.NONE.value
            self._apply_state_to_zone(zone, state)
            zone.status = WeatherStatus.ACTIVE.value
            self._stats.total_patterns_applied += 1
            self._stats.total_weather_changes += 1
            self._refresh_stats()
            event_kind = WeatherEventKind.WEATHER_CHANGED.value
            if pattern.weather_type in _STORM_WEATHER_TYPES:
                event_kind = WeatherEventKind.STORM_STARTED.value
                self._stats.total_storms += 1
            self._emit(
                event_kind,
                zone_id,
                f"Applied pattern '{pattern.name}' to '{zone.name}'",
                {
                    "pattern_id": pattern_id,
                    "weather_type": pattern.weather_type,
                },
            )
            return True, "applied", state

    # ------------------------------------------------------------------
    # Forecast Management
    # ------------------------------------------------------------------

    def create_forecast(
        self,
        zone_id: str,
        hours_ahead: int = 24,
    ) -> Tuple[bool, str, Optional[WeatherForecast]]:
        """Create a weather forecast for a zone.

        Generates a sequence of forecast entries by projecting the zone's
        current weather forward and introducing plausible variations
        (clearing, clouding, precipitation) based on the biome and
        season. Confidence decreases with the forecast horizon.

        Args:
            zone_id: The zone to forecast.
            hours_ahead: Number of hours to project forward.

        Returns:
            A ``(ok, message, forecast)`` tuple.
        """
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return False, "zone not found", None
            hours = max(1, _safe_int(hours_ahead, 24))
            now = _now()
            # Build entries by stepping forward in roughly equal chunks.
            current_type = (
                zone.current_state.weather_type
                if zone.current_state
                else WeatherType.CLEAR.value
            )
            current_temp = (
                zone.current_state.temperature
                if zone.current_state
                else _biome_base_temperature(zone.biome, zone.season)
            )
            entries: List[Dict[str, Any]] = []
            # A small plausible progression keyed off the starting weather.
            progression = self._forecast_progression(current_type, zone.biome)
            step_count = max(1, min(hours, 8))
            step_hours = max(1, hours // step_count)
            for i in range(step_count):
                idx = min(i, len(progression) - 1)
                wtype, wintensity = progression[idx]
                # Perturb the temperature slightly per step for realism.
                temp = current_temp + (i - step_count / 2.0) * 1.5
                entries.append({
                    "weather_type": wtype,
                    "intensity": wintensity,
                    "temperature": round(
                        _clamp(temp, _TEMPERATURE_MIN, _TEMPERATURE_MAX), 2
                    ),
                    "hour_offset": i * step_hours,
                })
            confidence = _clamp(
                0.9 - (hours / 72.0), _CONFIDENCE_MIN, _CONFIDENCE_MAX
            )
            self._forecast_counter += 1
            forecast_id = f"forecast_{self._forecast_counter:08d}"
            forecast = WeatherForecast(
                forecast_id=forecast_id,
                zone_id=zone_id,
                hours_ahead=hours,
                issued_at=now,
                entries=entries,
                confidence=round(confidence, 3),
                created_at=now,
                metadata={"generated": True},
            )
            self._forecasts[forecast_id] = forecast
            _evict_fifo_dict(self._forecasts, self._config.max_forecasts)
            self._refresh_stats()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                zone_id,
                f"Created {hours}h forecast for '{zone.name}'",
                {"forecast_id": forecast_id, "hours_ahead": hours},
            )
            return True, "created", forecast

    def _forecast_progression(
        self, current_type: str, biome: str
    ) -> List[Tuple[str, str]]:
        """Return a plausible weather progression from a starting type.

        Used by ``create_forecast`` to step forward in time with believable
        transitions rather than repeating the same weather for every
        entry.
        """
        base = _coerce_enum(WeatherType, current_type, WeatherType.CLEAR)
        if base.value in _STORM_WEATHER_TYPES:
            return [
                (base.value, WeatherIntensity.HEAVY.value),
                (WeatherType.RAIN.value, WeatherIntensity.MODERATE.value),
                (WeatherType.CLOUDY.value, WeatherIntensity.MODERATE.value),
                (WeatherType.CLEAR.value, WeatherIntensity.LIGHT.value),
            ]
        if base.value == WeatherType.CLEAR.value:
            if biome in ("tropical", "coastal"):
                return [
                    (WeatherType.CLEAR.value, WeatherIntensity.LIGHT.value),
                    (WeatherType.CLOUDY.value, WeatherIntensity.MODERATE.value),
                    (WeatherType.RAIN.value, WeatherIntensity.MODERATE.value),
                    (WeatherType.CLEAR.value, WeatherIntensity.LIGHT.value),
                ]
            return [
                (WeatherType.CLEAR.value, WeatherIntensity.LIGHT.value),
                (WeatherType.CLOUDY.value, WeatherIntensity.LIGHT.value),
                (WeatherType.CLEAR.value, WeatherIntensity.LIGHT.value),
                (WeatherType.CLEAR.value, WeatherIntensity.LIGHT.value),
            ]
        if base.value in (WeatherType.SNOW.value, WeatherType.AURORA.value):
            return [
                (base.value, WeatherIntensity.MODERATE.value),
                (WeatherType.SNOW.value, WeatherIntensity.LIGHT.value),
                (WeatherType.CLOUDY.value, WeatherIntensity.MODERATE.value),
                (WeatherType.SNOW.value, WeatherIntensity.LIGHT.value),
            ]
        return [
            (base.value, WeatherIntensity.MODERATE.value),
            (WeatherType.CLEAR.value, WeatherIntensity.LIGHT.value),
            (WeatherType.CLOUDY.value, WeatherIntensity.LIGHT.value),
            (WeatherType.CLEAR.value, WeatherIntensity.LIGHT.value),
        ]

    def get_forecast(self, forecast_id: str) -> Optional[WeatherForecast]:
        """Retrieve a forecast by its identifier."""
        with self._lock:
            return self._resolve_forecast(forecast_id)

    def list_forecasts(
        self,
        zone_id: Optional[str] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[WeatherForecast]:
        """List forecasts with an optional zone filter.

        Args:
            zone_id: Filter by zone id.
            limit: Maximum number of forecasts to return.

        Returns:
            A list of matching WeatherForecast objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            results: List[WeatherForecast] = []
            for forecast in self._forecasts.values():
                if zone_id is not None and forecast.zone_id != zone_id:
                    continue
                results.append(forecast)
                if len(results) >= cap:
                    break
            return results

    def remove_forecast(self, forecast_id: str) -> Tuple[bool, str]:
        """Remove a forecast by its identifier.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            forecast = self._forecasts.get(forecast_id)
            if forecast is None:
                return False, "not found"
            del self._forecasts[forecast_id]
            self._refresh_stats()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                forecast.zone_id,
                f"Removed forecast '{forecast_id}'",
                {"forecast_id": forecast_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Wind & Atmosphere
    # ------------------------------------------------------------------

    def set_wind(
        self,
        zone_id: str,
        direction: str = WindDirection.N.value,
        speed: float = 0.0,
        gusts: Optional[float] = None,
        turbulence: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[WindState]]:
        """Set the wind state for a zone.

        Updates the zone's WindState and reflects the wind speed and
        direction onto the current WeatherState's scalar fields.

        Args:
            zone_id: The zone to update.
            direction: The WindDirection value name.
            speed: Sustained wind speed in m/s.
            gusts: Optional peak gust speed in m/s.
            turbulence: Optional turbulence factor in ``[0.0, 1.0]``.

        Returns:
            A ``(ok, message, wind)`` tuple.
        """
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return False, "zone not found", None
            if not self._config.enable_wind:
                return False, "wind simulation is disabled", None
            direction_enum = _coerce_enum(WindDirection, direction, WindDirection.N)
            new_wind = _make_wind_state(
                direction=direction_enum.value,
                speed=speed,
                gusts=gusts,
                turbulence=turbulence,
                wind_id=zone.wind.wind_id if zone.wind else "",
            )
            new_wind.created_at = (
                zone.wind.created_at if zone.wind else _now()
            )
            zone.wind = new_wind
            # Reflect on the current weather state.
            if zone.current_state is not None:
                zone.current_state.wind_direction = new_wind.direction
                zone.current_state.wind_speed = new_wind.speed
                zone.current_state.updated_at = _now()
            zone.updated_at = _now()
            self._emit(
                WeatherEventKind.WIND_SHIFTED.value,
                zone_id,
                f"Wind shifted to {new_wind.direction} at {new_wind.speed} m/s on '{zone.name}'",
                {
                    "direction": new_wind.direction,
                    "speed": new_wind.speed,
                    "gusts": new_wind.gusts,
                },
            )
            return True, "set", new_wind

    def get_wind(self, zone_id: str) -> Optional[WindState]:
        """Return the wind state for a zone, or None."""
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return None
            return zone.wind

    def get_atmosphere(self, zone_id: str) -> Optional[AtmosphericConditions]:
        """Return the atmospheric conditions for a zone, or None."""
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return None
            return zone.atmosphere

    def set_cloud_layer(
        self,
        zone_id: str,
        coverage: str = CloudCoverage.SCATTERED.value,
        height: float = 1000.0,
        density: Optional[float] = None,
        cloud_type: str = "cumulus",
    ) -> Tuple[bool, str, Optional[CloudLayer]]:
        """Set the cloud layer for a zone.

        Updates the zone's CloudLayer and reflects the coverage onto the
        current WeatherState's cloud_coverage field.

        Args:
            zone_id: The zone to update.
            coverage: The CloudCoverage value name.
            height: Cloud base height in meters.
            density: Optional cloud density in ``[0.0, 1.0]``.
            cloud_type: Free-form cloud type name.

        Returns:
            A ``(ok, message, cloud)`` tuple.
        """
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return False, "zone not found", None
            if not self._config.enable_clouds:
                return False, "cloud layers are disabled", None
            new_cloud = _make_cloud_layer(
                coverage=coverage,
                height=height,
                density=density,
                cloud_type=cloud_type,
                cloud_id=zone.cloud_layer.cloud_id if zone.cloud_layer else "",
            )
            new_cloud.created_at = (
                zone.cloud_layer.created_at if zone.cloud_layer else _now()
            )
            zone.cloud_layer = new_cloud
            if zone.current_state is not None:
                zone.current_state.cloud_coverage = new_cloud.coverage
                zone.current_state.updated_at = _now()
            zone.updated_at = _now()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                zone_id,
                f"Cloud layer set to '{new_cloud.coverage}' on '{zone.name}'",
                {
                    "coverage": new_cloud.coverage,
                    "height": new_cloud.height,
                    "density": new_cloud.density,
                },
            )
            return True, "set", new_cloud

    def get_cloud_layer(self, zone_id: str) -> Optional[CloudLayer]:
        """Return the cloud layer for a zone, or None."""
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return None
            return zone.cloud_layer

    def clear_weather(
        self, zone_id: str, duration: float = 1800.0
    ) -> Tuple[bool, str, Optional[WeatherState]]:
        """Convenience method to set a zone's weather to CLEAR.

        Args:
            zone_id: The zone to clear.
            duration: Intended duration of the clear condition in seconds.

        Returns:
            A ``(ok, message, state)`` tuple.
        """
        return self.set_weather(
            zone_id=zone_id,
            weather_type=WeatherType.CLEAR.value,
            intensity=WeatherIntensity.LIGHT.value,
            duration=duration,
        )

    def list_weather_states(
        self,
        weather_type: Optional[str] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[WeatherState]:
        """List the current weather state of every (matching) zone.

        Args:
            weather_type: Filter by WeatherType value name.
            limit: Maximum number of states to return.

        Returns:
            A list of WeatherState objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            type_value = None
            if weather_type is not None:
                type_enum = _coerce_enum(WeatherType, weather_type, None)
                type_value = type_enum.value if type_enum else weather_type
            results: List[WeatherState] = []
            for zone in self._zones.values():
                if zone.current_state is None:
                    continue
                if type_value is not None and zone.current_state.weather_type != type_value:
                    continue
                results.append(zone.current_state)
                if len(results) >= cap:
                    break
            return results

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def auto_generate_weather(
        self,
        zone_id: str,
        context: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[WeatherState]]:
        """AI-generate a weather state for a zone from a context dict.

        The generator inspects the context for biome, season, time of
        day, mood, and weather hint keywords, then assembles a WeatherState
        with a weather type, intensity, temperature, humidity, wind, and
        visibility appropriate to the detected inputs. When no mood or
        hint is recognized a calm weather state tuned to the biome and
        season is produced.

        Args:
            zone_id: The zone to generate weather for.
            context: A dict that may contain ``biome``, ``season``,
                ``time_of_day`` (dawn/day/dusk/night), ``mood`` (calm,
                stormy, mysterious, harsh, pleasant, eerie, dramatic,
                festive), and ``weather_hint`` (a keyword such as "rain",
                "snow", "storm", "fog", "clear").

        Returns:
            A ``(ok, message, state)`` tuple.
        """
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return False, "zone not found", None
            if not isinstance(context, dict):
                return False, "context must be a dict", None
            biome = str(context.get("biome", zone.biome) or zone.biome)
            season = str(context.get("season", zone.season) or zone.season)
            season_enum = _coerce_enum(Season, season, Season(zone.season))
            time_of_day = str(context.get("time_of_day", "day")).lower()
            mood = str(context.get("mood", "")).lower()
            hint = str(context.get("weather_hint", "")).lower()

            # 1. Determine the weather type from hint, then mood, then a
            #    biome-aware default.
            chosen_type = self._ai_pick_weather_type(hint, mood, biome, season_enum.value)
            type_enum = _coerce_enum(WeatherType, chosen_type, WeatherType.CLEAR)
            props = _weather_properties(type_enum.value)

            # 2. Determine intensity from mood and weather type.
            intensity = self._ai_pick_intensity(mood, type_enum.value, props)

            # 3. Compute temperature from biome/season baseline blended
            #    with the weather-type default, then nudged by time of day.
            base_temp = _biome_base_temperature(biome, season_enum.value)
            temperature = (base_temp + props["temperature"]) / 2.0
            if time_of_day == "night":
                temperature -= 5.0
            elif time_of_day == "dawn":
                temperature -= 2.0
            elif time_of_day == "dusk":
                temperature -= 1.0

            # 4. Humidity and visibility from the weather type, nudged by
            #    mood (stormy lowers visibility, harsh lowers it further).
            humidity = props["humidity"]
            visibility = props["visibility"]
            if mood in ("stormy", "harsh"):
                visibility = max(_VISIBILITY_MIN, visibility * 0.5)
            if mood == "mysterious" or mood == "eerie":
                visibility = max(_VISIBILITY_MIN, visibility * 0.6)

            # 5. Wind direction and speed from the weather type, with a
            #    stormy mood pushing the speed up.
            wind_speed = props["wind_speed"]
            if mood in ("stormy", "harsh", "dramatic"):
                wind_speed = min(_WIND_SPEED_MAX, wind_speed * 1.4)
            # Pick a believable wind direction from the biome when no hint.
            wind_direction = self._ai_pick_wind_direction(biome, mood)

            # 6. Cloud coverage and fog type from the weather type, with
            #    the fog global toggle applied.
            cloud_coverage = props["cloud_coverage"]
            fog_type = props["fog_type"]
            if mood in ("mysterious", "eerie") and fog_type == FogType.NONE.value:
                fog_type = FogType.MIST.value
            if not self._config.enable_fog and fog_type != FogType.NONE.value:
                fog_type = FogType.NONE.value

            state = _make_weather_state(
                weather_type=type_enum.value,
                intensity=intensity,
                temperature=temperature,
                humidity=humidity,
                visibility=visibility,
                wind_direction=wind_direction,
                wind_speed=wind_speed,
                cloud_coverage=cloud_coverage,
                fog_type=fog_type,
                duration=max(600.0, props.get("duration", 3600.0)),
            )
            self._apply_state_to_zone(zone, state)
            zone.status = WeatherStatus.ACTIVE.value
            self._stats.total_weather_changes += 1
            self._refresh_stats()
            event_kind = WeatherEventKind.WEATHER_CHANGED.value
            if type_enum.value in _STORM_WEATHER_TYPES:
                event_kind = WeatherEventKind.STORM_STARTED.value
                self._stats.total_storms += 1
            self._emit(
                event_kind,
                zone_id,
                f"AI generated {type_enum.value} weather for '{zone.name}'",
                {
                    "ai_generated": True,
                    "biome": biome,
                    "season": season_enum.value,
                    "time_of_day": time_of_day,
                    "mood": mood,
                    "weather_hint": hint,
                },
            )
            return True, "generated", state

    def _ai_pick_weather_type(
        self, hint: str, mood: str, biome: str, season: str
    ) -> str:
        """Pick a WeatherType value from the hint, mood, biome, and season."""
        # Explicit hint keywords win over everything.
        hint_map = {
            "rain": WeatherType.RAIN.value,
            "drizzle": WeatherType.DRIZZLE.value,
            "storm": WeatherType.THUNDERSTORM.value,
            "thunder": WeatherType.THUNDERSTORM.value,
            "snow": WeatherType.SNOW.value,
            "blizzard": WeatherType.BLIZZARD.value,
            "fog": WeatherType.FOG.value,
            "mist": WeatherType.FOG.value,
            "sand": WeatherType.SANDSTORM.value,
            "sandstorm": WeatherType.SANDSTORM.value,
            "wind": WeatherType.WINDY.value,
            "windy": WeatherType.WINDY.value,
            "heat": WeatherType.HEAT_WAVE.value,
            "aurora": WeatherType.AURORA.value,
            "clear": WeatherType.CLEAR.value,
            "cloud": WeatherType.CLOUDY.value,
            "cloudy": WeatherType.CLOUDY.value,
        }
        for keyword, wtype in hint_map.items():
            if keyword in hint:
                return wtype
        # Mood-driven selection.
        if mood in ("stormy", "dramatic"):
            if biome == "desert":
                return WeatherType.SANDSTORM.value
            if biome in ("arctic", "tundra"):
                return WeatherType.BLIZZARD.value
            return WeatherType.THUNDERSTORM.value
        if mood in ("mysterious", "eerie"):
            return WeatherType.FOG.value
        if mood == "harsh":
            if biome == "desert":
                return WeatherType.HEAT_WAVE.value
            if biome in ("arctic", "tundra"):
                return WeatherType.BLIZZARD.value
            if biome == "volcanic":
                return WeatherType.SANDSTORM.value
            return WeatherType.HEAVY_RAIN.value
        if mood == "festive":
            if season == Season.WINTER.value:
                return WeatherType.AURORA.value
            return WeatherType.CLEAR.value
        if mood in ("pleasant", "calm"):
            return WeatherType.CLEAR.value
        # Biome-aware default when no mood or hint matched.
        if biome == "desert":
            return WeatherType.CLEAR.value
        if biome in ("arctic", "tundra"):
            return WeatherType.SNOW.value if season == Season.WINTER.value else WeatherType.CLOUDY.value
        if biome == "tropical":
            return WeatherType.RAIN.value
        if biome == "coastal":
            return WeatherType.WINDY.value
        if biome == "volcanic":
            return WeatherType.CLOUDY.value
        return WeatherType.CLEAR.value

    def _ai_pick_intensity(
        self, mood: str, weather_type: str, props: Dict[str, Any]
    ) -> str:
        """Pick a WeatherIntensity value from the mood and weather type."""
        if mood in ("harsh", "dramatic"):
            return WeatherIntensity.EXTREME.value
        if mood == "stormy":
            return WeatherIntensity.HEAVY.value
        if mood in ("pleasant", "calm", "festive"):
            return WeatherIntensity.LIGHT.value
        # Fall back to the weather-type default intensity.
        return props.get("default_intensity", WeatherIntensity.MODERATE.value)

    def _ai_pick_wind_direction(self, biome: str, mood: str) -> str:
        """Pick a plausible WindDirection value for a biome and mood."""
        if mood in ("stormy", "harsh", "dramatic"):
            return WindDirection.SW.value
        if biome == "coastal":
            return WindDirection.E.value
        if biome == "desert":
            return WindDirection.NE.value
        if biome in ("arctic", "tundra"):
            return WindDirection.N.value
        if biome == "tropical":
            return WindDirection.SE.value
        return WindDirection.NW.value

    def suggest_pattern(
        self,
        zone_id: str,
        goal: str,
    ) -> Tuple[bool, str, Optional[WeatherPattern]]:
        """AI-suggest a weather pattern for a gameplay goal.

        Inspects the zone's current state and the goal keyword (combat,
        stealth, exploration, racing, horror, celebration, survival) and
        either selects a matching registered pattern or builds a new
        pattern tuned to support the goal. The suggested pattern is
        registered so it can be applied immediately.

        Args:
            zone_id: The zone to suggest a pattern for.
            goal: A gameplay goal keyword.

        Returns:
            A ``(ok, message, pattern)`` tuple.
        """
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return False, "zone not found", None
            goal_lower = (goal or "").lower()
            # Map each goal to a preferred weather type, intensity, and a
            # list of tags used to find a matching registered pattern.
            goal_map = {
                "combat": {
                    "weather_type": WeatherType.THUNDERSTORM.value,
                    "intensity": WeatherIntensity.HEAVY.value,
                    "tags": ["storm", "dramatic"],
                    "name_suffix": "Combat Storm",
                },
                "stealth": {
                    "weather_type": WeatherType.FOG.value,
                    "intensity": WeatherIntensity.MODERATE.value,
                    "tags": ["fog", "mysterious"],
                    "name_suffix": "Stealth Fog",
                },
                "exploration": {
                    "weather_type": WeatherType.CLEAR.value,
                    "intensity": WeatherIntensity.LIGHT.value,
                    "tags": ["calm", "pleasant"],
                    "name_suffix": "Exploration Clear",
                },
                "racing": {
                    "weather_type": WeatherType.WINDY.value,
                    "intensity": WeatherIntensity.MODERATE.value,
                    "tags": ["wind"],
                    "name_suffix": "Racing Wind",
                },
                "horror": {
                    "weather_type": WeatherType.FOG.value,
                    "intensity": WeatherIntensity.HEAVY.value,
                    "tags": ["fog", "mysterious"],
                    "name_suffix": "Horror Fog",
                },
                "celebration": {
                    "weather_type": WeatherType.AURORA.value,
                    "intensity": WeatherIntensity.LIGHT.value,
                    "tags": ["aurora", "beautiful"],
                    "name_suffix": "Celebration Aurora",
                },
                "survival": {
                    "weather_type": WeatherType.BLIZZARD.value,
                    "intensity": WeatherIntensity.EXTREME.value,
                    "tags": ["storm", "harsh"],
                    "name_suffix": "Survival Blizzard",
                },
            }
            # Find the best matching goal entry.
            matched_key = None
            for key in goal_map:
                if key in goal_lower:
                    matched_key = key
                    break
            if matched_key is None:
                matched_key = "exploration"
            spec = goal_map[matched_key]
            # Try to find an existing enabled pattern with the preferred
            # weather type and at least one matching tag.
            for pattern in self._patterns.values():
                if not pattern.enabled:
                    continue
                if pattern.weather_type != spec["weather_type"]:
                    continue
                if any(tag in pattern.tags for tag in spec["tags"]):
                    self._emit(
                        WeatherEventKind.WEATHER_CHANGED.value,
                        zone_id,
                        f"AI suggested pattern '{pattern.name}' for goal '{goal_lower}'",
                        {"goal": matched_key, "pattern_id": pattern.pattern_id},
                    )
                    return True, "suggested", pattern
            # No matching pattern: build and register a new one tuned to
            # the goal and the zone's biome.
            props = _weather_properties(spec["weather_type"])
            biome_temp = _biome_base_temperature(zone.biome, zone.season)
            target_temp = (biome_temp + props["temperature"]) / 2.0
            pattern_id = _new_id("ai_pattern")
            pattern = WeatherPattern(
                pattern_id=pattern_id,
                name=f"AI {spec['name_suffix']}",
                description=f"AI-suggested pattern for the '{matched_key}' goal on '{zone.name}'.",
                weather_type=spec["weather_type"],
                intensity=spec["intensity"],
                duration=3600.0,
                wind_direction=self._ai_pick_wind_direction(zone.biome, matched_key),
                wind_speed=props["wind_speed"],
                temperature=target_temp,
                humidity=props["humidity"],
                cloud_coverage=props["cloud_coverage"],
                fog_type=props["fog_type"],
                visibility=props["visibility"],
                steps=[
                    {
                        "weather_type": spec["weather_type"],
                        "intensity": spec["intensity"],
                        "offset_seconds": 0,
                    }
                ],
                tags=["ai_suggested"] + spec["tags"],
                enabled=True,
                created_at=_now(),
                updated_at=_now(),
                metadata={
                    "ai_suggested": True,
                    "goal": matched_key,
                    "zone_id": zone_id,
                },
            )
            self._patterns[pattern_id] = pattern
            _evict_fifo_dict(self._patterns, self._config.max_patterns)
            self._refresh_stats()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                zone_id,
                f"AI suggested new pattern '{pattern.name}' for goal '{goal_lower}'",
                {"goal": matched_key, "pattern_id": pattern_id},
            )
            return True, "suggested", pattern

    def optimize_transitions(
        self, zone_id: str
    ) -> Tuple[bool, str, List[str]]:
        """AI-optimize transition durations for realism.

        Inspects every transition bound to a zone and adjusts its
        duration so that the change feels natural: small weather shifts
        get shorter transitions, large or extreme shifts get longer
        ones, and storm onsets are kept brisk for drama while storm
        dissipation is drawn out for a gradual recovery.

        Args:
            zone_id: The zone whose transitions should be optimized.

        Returns:
            A ``(ok, message, changes)`` tuple where ``changes`` is a list
            of human-readable descriptions of every duration adjustment.
        """
        with self._lock:
            zone = self._resolve_zone(zone_id)
            if zone is None:
                return False, "zone not found", []
            transitions = [
                t for t in self._transitions.values() if t.zone_id == zone_id
            ]
            if not transitions:
                return False, "no transitions for zone", []
            changes: List[str] = []
            for transition in transitions:
                original = transition.duration
                optimized = self._ai_optimal_duration(
                    transition.from_type, transition.to_type,
                    transition.from_intensity, transition.to_intensity,
                )
                if abs(optimized - original) < 0.5:
                    continue
                transition.duration = optimized
                changes.append(
                    f"{transition.transition_id}: {original:.1f}s -> {optimized:.1f}s "
                    f"({transition.from_type}->{transition.to_type})"
                )
            self._refresh_stats()
            self._emit(
                WeatherEventKind.WEATHER_CHANGED.value,
                zone_id,
                f"AI optimized {len(changes)} transitions for '{zone.name}'",
                {"changes": changes},
            )
            if not changes:
                return True, "no changes needed", []
            return True, "optimized", changes

    def _ai_optimal_duration(
        self,
        from_type: str,
        to_type: str,
        from_intensity: str,
        to_intensity: str,
    ) -> float:
        """Return an optimized transition duration in seconds.

        Combines a base duration with modifiers for the weather-type
        difference, the intensity delta, and whether the change is a
        storm onset (brisk) or a storm dissipation (gradual).
        """
        # Base duration in seconds.
        duration = 120.0
        # Type difference: identical types collapse quickly.
        if from_type == to_type:
            duration = 30.0
        else:
            # Larger semantic jumps take longer.
            type_cost = self._weather_type_distance(from_type, to_type)
            duration += type_cost * 30.0
        # Intensity delta: bigger intensity changes take longer.
        intensity_order = [
            WeatherIntensity.LIGHT.value,
            WeatherIntensity.MODERATE.value,
            WeatherIntensity.HEAVY.value,
            WeatherIntensity.EXTREME.value,
        ]
        try:
            from_idx = intensity_order.index(from_intensity)
            to_idx = intensity_order.index(to_intensity)
        except ValueError:
            from_idx, to_idx = 1, 1
        duration += abs(to_idx - from_idx) * 20.0
        # Storm onset should be brisk (dramatic), storm dissipation gradual.
        from_storm = from_type in _STORM_WEATHER_TYPES
        to_storm = to_type in _STORM_WEATHER_TYPES
        if to_storm and not from_storm:
            duration *= 0.7
        elif from_storm and not to_storm:
            duration *= 1.4
        # Clamp to a sensible range.
        return round(_clamp(duration, 15.0, 600.0), 1)

    def _weather_type_distance(self, from_type: str, to_type: str) -> int:
        """Return a rough semantic distance (0-3) between two weather types.

        0 means the types are identical or very close (e.g. RAIN to
        HEAVY_RAIN), 3 means a large jump (e.g. CLEAR to BLIZZARD).
        """
        if from_type == to_type:
            return 0
        # Families of related weather types.
        families = [
            {WeatherType.CLEAR.value, WeatherType.WINDY.value, WeatherType.CLOUDY.value},
            {WeatherType.DRIZZLE.value, WeatherType.RAIN.value, WeatherType.HEAVY_RAIN.value, WeatherType.THUNDERSTORM.value},
            {WeatherType.SNOW.value, WeatherType.BLIZZARD.value, WeatherType.HAIL.value},
            {WeatherType.FOG.value},
            {WeatherType.SANDSTORM.value, WeatherType.HEAT_WAVE.value},
            {WeatherType.AURORA.value},
        ]
        from_family = None
        to_family = None
        for family in families:
            if from_type in family:
                from_family = family
            if to_type in family:
                to_family = family
        if from_family is not None and to_family is not None and from_family is to_family:
            return 1
        # Cross-family but both are precipitation/storms.
        stormish = {
            WeatherType.DRIZZLE.value, WeatherType.RAIN.value,
            WeatherType.HEAVY_RAIN.value, WeatherType.THUNDERSTORM.value,
            WeatherType.SNOW.value, WeatherType.BLIZZARD.value,
            WeatherType.HAIL.value,
        }
        if from_type in stormish and to_type in stormish:
            return 2
        # Otherwise a large jump.
        return 3

    # ------------------------------------------------------------------
    # System Lifecycle
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_zones": len(self._zones),
                "total_patterns": len(self._patterns),
                "total_transitions": len(self._transitions),
                "total_forecasts": len(self._forecasts),
                "total_events": len(self._events),
                "active_zones": sum(1 for z in self._zones.values() if z.active),
                "active_transitions": sum(
                    1 for t in self._transitions.values() if t.active
                ),
                "storm_zones": sum(
                    1 for z in self._zones.values()
                    if z.current_state is not None
                    and z.current_state.weather_type in _STORM_WEATHER_TYPES
                ),
                "tick_count": self._tick_count,
            }

    def get_stats(self) -> WeatherStats:
        """Return aggregate statistics (refreshed before return)."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> WeatherSnapshot:
        """Return an immutable snapshot of the whole system.

        The zone, transition, forecast, and event lists are bounded so
        the snapshot stays reasonably sized for transmission and logging.
        """
        with self._lock:
            self._refresh_stats()
            return WeatherSnapshot(
                timestamp=_now(),
                zones=[
                    z.to_dict() for z in list(self._zones.values())[:50]
                ],
                patterns=[
                    p.to_dict() for p in list(self._patterns.values())[:50]
                ],
                transitions=[
                    t.to_dict() for t in list(self._transitions.values())[:50]
                ],
                forecasts=[
                    f.to_dict() for f in list(self._forecasts.values())[:50]
                ],
                events=[
                    e.to_dict() for e in list(self._events)[-50:]
                ],
                stats=self._stats.to_dict(),
            )

    def get_config(self) -> WeatherConfig:
        """Return the current runtime configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, WeatherConfig]:
        """Update runtime configuration fields.

        Accepts any subset of WeatherConfig fields. Numeric capacity
        fields are coerced and floored at one; boolean toggles are
        coerced; the ``default_season`` field is coerced via the Season
        enum; ``simulation_speed`` is clamped to its valid range; and
        ``metadata`` is merged when supplied as a dict.
        """
        with self._lock:
            for key in ("max_zones", "max_patterns", "max_transitions",
                        "max_forecasts", "max_events"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(
                        self._config, key,
                        max(1, _safe_int(kwargs[key], getattr(self._config, key))),
                    )
            for key in ("enable_wind", "enable_fog", "enable_clouds"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(self._config, key, bool(kwargs[key]))
            if "default_season" in kwargs and kwargs["default_season"] is not None:
                enum_val = _coerce_enum(Season, kwargs["default_season"], None)
                if enum_val is not None:
                    self._config.default_season = enum_val.value
            if "simulation_speed" in kwargs and kwargs["simulation_speed"] is not None:
                self._config.simulation_speed = _clamp(
                    _safe_float(kwargs["simulation_speed"], 1.0),
                    _SIM_SPEED_MIN, _SIM_SPEED_MAX,
                )
            if "metadata" in kwargs and kwargs["metadata"] is not None:
                if isinstance(kwargs["metadata"], dict):
                    self._config.metadata.update(kwargs["metadata"])
            self._emit(
                WeatherEventKind.CONFIG_CHANGED.value,
                "",
                "Configuration updated",
            )
            return True, "updated", self._config

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance the simulation by ``dt`` seconds.

        Steps the global tick counter, advances every active transition
        forward by the simulation-speed-scaled delta, applies completed
        transitions to their zones (emitting storm-started / storm-ended
        events when the storm boundary is crossed), advances each zone's
        current weather state elapsed time and lifecycle phase, and trims
        the event log to capacity.

        Args:
            dt: Delta time in seconds (unscaled).

        Returns:
            A dict summarizing the post-tick system state.
        """
        with self._lock:
            sim_dt = _clamp(
                _safe_float(dt, 0.016) * self._config.simulation_speed,
                0.0, 86400.0,
            )
            self._tick_count += 1
            # Advance active transitions.
            completed: List[WeatherTransition] = []
            for transition in self._transitions.values():
                if not transition.active:
                    continue
                if transition.duration <= 0.0:
                    transition.progress = 1.0
                else:
                    transition.progress = _clamp(
                        transition.progress + sim_dt / transition.duration,
                        0.0, 1.0,
                    )
                if transition.progress >= 1.0:
                    transition.active = False
                    completed.append(transition)
            # Apply completed transitions to their zones.
            for transition in completed:
                zone = self._resolve_zone(transition.zone_id)
                if zone is None:
                    continue
                prev_type = (
                    zone.current_state.weather_type
                    if zone.current_state is not None
                    else WeatherType.CLEAR.value
                )
                target_enum = _coerce_enum(
                    WeatherType, transition.to_type, WeatherType.CLEAR
                )
                intensity_enum = _coerce_enum(
                    WeatherIntensity, transition.to_intensity,
                    WeatherIntensity.MODERATE,
                )
                state = _make_weather_state(
                    weather_type=target_enum.value,
                    intensity=intensity_enum.value,
                    wind_direction=(
                        zone.wind.direction if zone.wind else WindDirection.N.value
                    ),
                    duration=3600.0,
                )
                self._apply_state_to_zone(zone, state)
                zone.status = WeatherStatus.ACTIVE.value
                self._stats.total_weather_changes += 1
                was_storm = prev_type in _STORM_WEATHER_TYPES
                is_storm = target_enum.value in _STORM_WEATHER_TYPES
                if is_storm and not was_storm:
                    self._stats.total_storms += 1
                    self._emit(
                        WeatherEventKind.STORM_STARTED.value,
                        zone.zone_id,
                        f"Storm '{target_enum.value}' began on '{zone.name}'",
                        {"weather_type": target_enum.value},
                    )
                elif was_storm and not is_storm:
                    self._emit(
                        WeatherEventKind.STORM_ENDED.value,
                        zone.zone_id,
                        f"Storm ended on '{zone.name}'",
                        {"weather_type": target_enum.value},
                    )
                else:
                    self._emit(
                        WeatherEventKind.WEATHER_CHANGED.value,
                        zone.zone_id,
                        f"Transition completed to '{target_enum.value}' on '{zone.name}'",
                        {"transition_id": transition.transition_id},
                    )
            # Advance weather state elapsed time and lifecycle phase.
            for zone in self._zones.values():
                state = zone.current_state
                if state is None or not zone.active:
                    continue
                state.elapsed += sim_dt
                state.updated_at = _now()
                if state.duration <= 0.0:
                    continue
                ratio = state.elapsed / state.duration
                if ratio >= 1.0:
                    state.phase = WeatherPhase.CLEARING.value
                elif ratio >= 0.75:
                    state.phase = WeatherPhase.DISSIPATING.value
                elif ratio >= 0.25:
                    state.phase = WeatherPhase.PEAK.value
                else:
                    state.phase = WeatherPhase.DEVELOPING.value
            # Trim the event log to capacity.
            _evict_fifo_list(self._events, self._config.max_events)
            self._refresh_stats()
            return {
                "tick_count": self._tick_count,
                "sim_dt": sim_dt,
                "active_transitions": sum(
                    1 for t in self._transitions.values() if t.active
                ),
                "completed_transitions": len(completed),
                "total_zones": len(self._zones),
                "active_zones": sum(1 for z in self._zones.values() if z.active),
                "storm_zones": sum(
                    1 for z in self._zones.values()
                    if z.current_state is not None
                    and z.current_state.weather_type in _STORM_WEATHER_TYPES
                ),
            }

    def reset(self) -> None:
        """Reset the system to its initial seeded state.

        Clears all zones, patterns, transitions, forecasts, and events,
        restores the configuration, statistics, and counters to their
        defaults, then re-seeds the default data set. The instance lock
        is held for the duration so concurrent callers observe a
        consistent state.
        """
        with self._lock:
            self._zones.clear()
            self._patterns.clear()
            self._transitions.clear()
            self._forecasts.clear()
            self._events.clear()
            self._config = WeatherConfig()
            self._stats = WeatherStats()
            self._tick_count = 0
            self._event_counter = 0
            self._transition_counter = 0
            self._forecast_counter = 0
            self._seed()
            self._emit(
                WeatherEventKind.SYSTEM_RESET.value,
                "",
                "System reset to defaults",
            )

    def list_events(self, limit: int = 100) -> List[WeatherEvent]:
        """Return the most recent audit events.

        Events are returned newest-last so callers can iterate in
        chronological order. The result is bounded by ``limit`` (clamped
        to the configured maximum list limit).

        Args:
            limit: Maximum number of events to return.

        Returns:
            A list of WeatherEvent objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            return list(self._events[-cap:])


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------


def get_dynamic_weather_system() -> DynamicWeatherSystem:
    """Return the shared DynamicWeatherSystem singleton instance.

    Convenience accessor that delegates to
    :meth:`DynamicWeatherSystem.get_instance`.
    """
    return DynamicWeatherSystem.get_instance()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "WeatherType",
    "WeatherIntensity",
    "WeatherPhase",
    "WindDirection",
    "CloudCoverage",
    "WeatherStatus",
    "Season",
    "FogType",
    "WeatherEventKind",
    # Data classes
    "WindState",
    "CloudLayer",
    "AtmosphericConditions",
    "WeatherState",
    "WeatherZone",
    "WeatherPattern",
    "WeatherTransition",
    "WeatherForecast",
    "WeatherConfig",
    "WeatherStats",
    "WeatherSnapshot",
    "WeatherEvent",
    # Main system
    "DynamicWeatherSystem",
    "get_dynamic_weather_system",
]