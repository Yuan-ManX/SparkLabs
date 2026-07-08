"""
SparkLabs Engine - Day/Night Cycle System

A time-of-day progression system for the SparkLabs AI-native game engine.
This system simulates the cyclical passage of time across a full day —
tracking the sun and moon positions, computing sky color gradients based
on solar altitude, transitioning ambient light intensity and color
temperature, and emitting phase-change events (dawn, noon, dusk, midnight).

The system is distinct from the weather system (which handles
precipitation, cloud cover, and atmospheric conditions) and the lighting
director (which manages individual light placement and shadow casting).
Day/night cycle governs the global time-of-day clock that those systems
sample from.

Architecture:
  DayNightCycleSystem (singleton)
    |-- TimePhase, CelestialBody, SkyPreset, DayNightEventKind
    |-- CelestialState, SkyColorStop, DayNightConfig, DayNightStats,
       DayNightSnapshot, DayNightEvent
    |-- get_day_night_cycle

Core Capabilities:
  - set_time / get_time / advance_time: control the time-of-day clock.
  - set_time_scale / get_time_scale: control how fast game time flows.
  - get_sun / get_moon: retrieve celestial body positions (altitude,
    azimuth, direction vector).
  - get_sky_color: sample the sky color gradient at the current time.
  - get_ambient_light: compute ambient light intensity and color
    temperature for the current time.
  - register_sky_preset / get_sky_preset / list_sky_presets /
    remove_sky_preset: manage named sky color gradient presets.
  - set_phase / get_phase / list_phases: manage time-of-day phases
    (dawn, day, dusk, night) with transition boundaries.
  - tick: advance the simulation by delta time, updating celestial
    positions, sky colors, and emitting phase-change events.
  - set_config / get_config: global tuning for day length, latitude,
    and starting time.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`DayNightCycleSystem.get_instance` or the module-level
:func:`get_day_night_cycle` factory.
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
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SKY_PRESETS: int = 200
_MAX_PHASES: int = 50
_MAX_EVENTS: int = 5000

_DEFAULT_DAY_LENGTH: float = 1200.0
_DEFAULT_START_TIME: float = 8.0
_DEFAULT_LATITUDE: float = 45.0


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * _clamp(t, 0.0, 1.0)


def _lerp_color(c1: Tuple[float, float, float], c2: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
    return (
        round(_lerp(c1[0], c2[0], t), 4),
        round(_lerp(c1[1], c2[1], t), 4),
        round(_lerp(c1[2], c2[2], t), 4),
    )


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class TimePhase(str, Enum):
    """Time-of-day phases."""
    MIDNIGHT = "midnight"
    PRE_DAWN = "pre_dawn"
    DAWN = "dawn"
    SUNRISE = "sunrise"
    MORNING = "morning"
    FORENOON = "forenoon"
    NOON = "noon"
    AFTERNOON = "afternoon"
    GOLDEN_HOUR = "golden_hour"
    SUNSET = "sunset"
    DUSK = "dusk"
    TWILIGHT = "twilight"
    NIGHT = "night"


class CelestialBody(str, Enum):
    """Celestial body types."""
    SUN = "sun"
    MOON = "moon"


class DayNightEventKind(str, Enum):
    """Audit event types emitted by the day/night cycle system."""
    TIME_SET = "time_set"
    TIME_ADVANCED = "time_advanced"
    TIME_SCALE_CHANGED = "time_scale_changed"
    PHASE_CHANGED = "phase_changed"
    SUNRISE = "sunrise"
    SUNSET = "sunset"
    MOONRISE = "moonrise"
    MOONSET = "moonset"
    SKY_PRESET_REGISTERED = "sky_preset_registered"
    SKY_PRESET_REMOVED = "sky_preset_removed"
    CONFIG_UPDATED = "config_updated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CelestialState:
    """Position and visibility of a celestial body."""
    body: str = CelestialBody.SUN.value
    altitude: float = 0.0
    azimuth: float = 0.0
    direction: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    visible: bool = True
    brightness: float = 1.0
    angular_size: float = 0.53

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SkyColorStop:
    """A color stop in the sky gradient at a specific time."""
    time: float = 0.0
    zenith_color: Tuple[float, float, float] = (0.1, 0.2, 0.5)
    horizon_color: Tuple[float, float, float] = (0.5, 0.6, 0.8)
    sun_color: Tuple[float, float, float] = (1.0, 0.9, 0.7)
    sun_glow: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SkyPreset:
    """A named sky color gradient preset."""
    preset_id: str = ""
    name: str = ""
    description: str = ""
    color_stops: List[SkyColorStop] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhaseDefinition:
    """Definition of a time-of-day phase boundary."""
    phase: str = TimePhase.MORNING.value
    start_time: float = 6.0
    end_time: float = 9.0
    ambient_intensity: float = 0.6
    ambient_color: Tuple[float, float, float] = (1.0, 0.95, 0.85)
    color_temperature: float = 5500.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DayNightConfig:
    """Global tuning parameters for the day/night cycle."""
    day_length_seconds: float = _DEFAULT_DAY_LENGTH
    time_scale: float = 1.0
    latitude: float = _DEFAULT_LATITUDE
    start_time: float = _DEFAULT_START_TIME
    axial_tilt: float = 23.5
    moon_cycle_days: float = 29.5
    auto_advance: bool = True
    star_intensity: float = 0.8
    cloud_shadow_factor: float = 0.3

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DayNightStats:
    """Aggregate statistics for the day/night cycle."""
    total_ticks: int = 0
    total_days_elapsed: int = 0
    total_sunrises: int = 0
    total_sunsets: int = 0
    total_moonrises: int = 0
    total_moonsets: int = 0
    current_phase: str = TimePhase.MORNING.value
    time_of_day: float = 8.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DayNightSnapshot:
    """Full state snapshot of the day/night cycle."""
    current_time: float = 8.0
    day_count: int = 0
    sun: CelestialState = field(default_factory=CelestialState)
    moon: CelestialState = field(default_factory=CelestialState)
    sky_color: Dict[str, Any] = field(default_factory=dict)
    ambient_light: Dict[str, Any] = field(default_factory=dict)
    current_phase: str = TimePhase.MORNING.value
    config: DayNightConfig = field(default_factory=DayNightConfig)
    stats: DayNightStats = field(default_factory=DayNightStats)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DayNightEvent:
    """An audit event emitted by the day/night cycle system."""
    timestamp: str = ""
    kind: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton System
# ---------------------------------------------------------------------------


class DayNightCycleSystem:
    """Time-of-day progression and celestial body tracking system.

    Manages the cyclical passage of game time — computing sun and moon
    positions, sampling sky color gradients, transitioning ambient light,
    and emitting phase-change events. Designed to be sampled by weather,
    lighting, and rendering systems.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["DayNightCycleSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._current_time: float = _DEFAULT_START_TIME
        self._day_count: int = 0
        self._time_scale: float = 1.0
        self._sun: CelestialState = CelestialState(body=CelestialBody.SUN.value)
        self._moon: CelestialState = CelestialState(body=CelestialBody.MOON.value)
        self._sky_presets: Dict[str, SkyPreset] = {}
        self._phases: List[PhaseDefinition] = []
        self._events: List[DayNightEvent] = []
        self._config: DayNightConfig = DayNightConfig()
        self._stats: DayNightStats = DayNightStats()
        self._tick_count: int = 0
        self._last_phase: str = ""
        self._sun_was_visible: bool = True
        self._moon_was_visible: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "DayNightCycleSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed the system with default phases and sky presets."""
        default_phases = [
            PhaseDefinition(phase=TimePhase.MIDNIGHT.value, start_time=0.0, end_time=4.0,
                            ambient_intensity=0.05, ambient_color=(0.3, 0.35, 0.5),
                            color_temperature=4100.0),
            PhaseDefinition(phase=TimePhase.PRE_DAWN.value, start_time=4.0, end_time=5.5,
                            ambient_intensity=0.12, ambient_color=(0.4, 0.4, 0.55),
                            color_temperature=4200.0),
            PhaseDefinition(phase=TimePhase.DAWN.value, start_time=5.5, end_time=6.5,
                            ambient_intensity=0.3, ambient_color=(0.7, 0.6, 0.5),
                            color_temperature=4500.0),
            PhaseDefinition(phase=TimePhase.SUNRISE.value, start_time=6.5, end_time=7.5,
                            ambient_intensity=0.5, ambient_color=(1.0, 0.75, 0.55),
                            color_temperature=4800.0),
            PhaseDefinition(phase=TimePhase.MORNING.value, start_time=7.5, end_time=10.0,
                            ambient_intensity=0.7, ambient_color=(1.0, 0.95, 0.85),
                            color_temperature=5500.0),
            PhaseDefinition(phase=TimePhase.FORENOON.value, start_time=10.0, end_time=12.0,
                            ambient_intensity=0.85, ambient_color=(1.0, 0.98, 0.92),
                            color_temperature=5800.0),
            PhaseDefinition(phase=TimePhase.NOON.value, start_time=12.0, end_time=14.0,
                            ambient_intensity=0.95, ambient_color=(1.0, 1.0, 0.95),
                            color_temperature=6500.0),
            PhaseDefinition(phase=TimePhase.AFTERNOON.value, start_time=14.0, end_time=16.5,
                            ambient_intensity=0.85, ambient_color=(1.0, 0.95, 0.85),
                            color_temperature=5800.0),
            PhaseDefinition(phase=TimePhase.GOLDEN_HOUR.value, start_time=16.5, end_time=18.0,
                            ambient_intensity=0.6, ambient_color=(1.0, 0.8, 0.55),
                            color_temperature=4800.0),
            PhaseDefinition(phase=TimePhase.SUNSET.value, start_time=18.0, end_time=19.0,
                            ambient_intensity=0.4, ambient_color=(0.9, 0.55, 0.4),
                            color_temperature=4200.0),
            PhaseDefinition(phase=TimePhase.DUSK.value, start_time=19.0, end_time=20.0,
                            ambient_intensity=0.2, ambient_color=(0.55, 0.4, 0.45),
                            color_temperature=4000.0),
            PhaseDefinition(phase=TimePhase.TWILIGHT.value, start_time=20.0, end_time=21.5,
                            ambient_intensity=0.1, ambient_color=(0.35, 0.35, 0.5),
                            color_temperature=4100.0),
            PhaseDefinition(phase=TimePhase.NIGHT.value, start_time=21.5, end_time=24.0,
                            ambient_intensity=0.05, ambient_color=(0.25, 0.3, 0.45),
                            color_temperature=4100.0),
        ]
        self._phases = default_phases

        default_sky = SkyPreset(
            preset_id="sky_default",
            name="Default Sky",
            description="Standard temperate latitude sky gradient",
            color_stops=[
                SkyColorStop(time=0.0, zenith_color=(0.02, 0.03, 0.08), horizon_color=(0.05, 0.06, 0.12), sun_color=(0.1, 0.1, 0.15), sun_glow=0.0),
                SkyColorStop(time=5.0, zenith_color=(0.08, 0.1, 0.2), horizon_color=(0.3, 0.25, 0.35), sun_color=(0.6, 0.4, 0.3), sun_glow=0.2),
                SkyColorStop(time=6.5, zenith_color=(0.15, 0.25, 0.5), horizon_color=(0.8, 0.5, 0.35), sun_color=(1.0, 0.6, 0.3), sun_glow=0.6),
                SkyColorStop(time=8.0, zenith_color=(0.2, 0.45, 0.8), horizon_color=(0.6, 0.75, 0.9), sun_color=(1.0, 0.95, 0.8), sun_glow=0.4),
                SkyColorStop(time=12.0, zenith_color=(0.15, 0.4, 0.85), horizon_color=(0.55, 0.7, 0.9), sun_color=(1.0, 1.0, 0.95), sun_glow=0.3),
                SkyColorStop(time=16.0, zenith_color=(0.2, 0.45, 0.8), horizon_color=(0.7, 0.75, 0.85), sun_color=(1.0, 0.9, 0.7), sun_glow=0.4),
                SkyColorStop(time=18.0, zenith_color=(0.15, 0.2, 0.45), horizon_color=(0.85, 0.5, 0.3), sun_color=(1.0, 0.5, 0.2), sun_glow=0.7),
                SkyColorStop(time=19.5, zenith_color=(0.05, 0.08, 0.2), horizon_color=(0.25, 0.2, 0.35), sun_color=(0.4, 0.25, 0.2), sun_glow=0.15),
                SkyColorStop(time=21.0, zenith_color=(0.02, 0.03, 0.1), horizon_color=(0.05, 0.06, 0.15), sun_color=(0.1, 0.1, 0.15), sun_glow=0.0),
                SkyColorStop(time=24.0, zenith_color=(0.02, 0.03, 0.08), horizon_color=(0.05, 0.06, 0.12), sun_color=(0.1, 0.1, 0.15), sun_glow=0.0),
            ],
        )
        self._sky_presets[default_sky.preset_id] = default_sky

        desert_sky = SkyPreset(
            preset_id="sky_desert",
            name="Desert Sky",
            description="Warm arid sky with intense golden hours",
            color_stops=[
                SkyColorStop(time=0.0, zenith_color=(0.05, 0.05, 0.1), horizon_color=(0.1, 0.08, 0.1), sun_color=(0.15, 0.1, 0.1), sun_glow=0.0),
                SkyColorStop(time=6.5, zenith_color=(0.25, 0.3, 0.5), horizon_color=(0.9, 0.55, 0.3), sun_color=(1.0, 0.5, 0.15), sun_glow=0.8),
                SkyColorStop(time=12.0, zenith_color=(0.1, 0.35, 0.7), horizon_color=(0.75, 0.65, 0.55), sun_color=(1.0, 0.95, 0.75), sun_glow=0.5),
                SkyColorStop(time=18.0, zenith_color=(0.2, 0.2, 0.4), horizon_color=(0.95, 0.45, 0.2), sun_color=(1.0, 0.4, 0.1), sun_glow=0.9),
                SkyColorStop(time=21.0, zenith_color=(0.05, 0.05, 0.12), horizon_color=(0.1, 0.08, 0.12), sun_color=(0.15, 0.1, 0.1), sun_glow=0.0),
            ],
        )
        self._sky_presets[desert_sky.preset_id] = desert_sky

        arctic_sky = SkyPreset(
            preset_id="sky_arctic",
            name="Arctic Sky",
            description="Cool polar sky with soft light transitions",
            color_stops=[
                SkyColorStop(time=0.0, zenith_color=(0.05, 0.08, 0.15), horizon_color=(0.1, 0.12, 0.2), sun_color=(0.2, 0.2, 0.25), sun_glow=0.1),
                SkyColorStop(time=6.5, zenith_color=(0.2, 0.3, 0.5), horizon_color=(0.6, 0.65, 0.75), sun_color=(0.9, 0.85, 0.8), sun_glow=0.4),
                SkyColorStop(time=12.0, zenith_color=(0.15, 0.3, 0.55), horizon_color=(0.65, 0.7, 0.8), sun_color=(1.0, 0.98, 0.92), sun_glow=0.3),
                SkyColorStop(time=18.0, zenith_color=(0.15, 0.2, 0.4), horizon_color=(0.55, 0.55, 0.65), sun_color=(0.85, 0.75, 0.7), sun_glow=0.4),
                SkyColorStop(time=21.0, zenith_color=(0.05, 0.08, 0.15), horizon_color=(0.1, 0.12, 0.2), sun_color=(0.2, 0.2, 0.25), sun_glow=0.1),
            ],
        )
        self._sky_presets[arctic_sky.preset_id] = arctic_sky

        self._current_time = self._config.start_time
        self._update_celestial_positions()
        self._stats.current_phase = self._compute_phase(self._current_time)
        self._stats.time_of_day = self._current_time
        self._last_phase = self._stats.current_phase
        self._sun_was_visible = self._sun.visible
        self._moon_was_visible = self._moon.visible
        self._initialized = True

    # ------------------------------------------------------------------
    # Time Management
    # ------------------------------------------------------------------

    def set_time(self, hours: float) -> float:
        """Set the current time of day (0-24 hours)."""
        hours = _clamp(hours, 0.0, 24.0)
        old_time = self._current_time
        self._current_time = hours
        self._update_celestial_positions()
        new_phase = self._compute_phase(hours)
        self._stats.time_of_day = hours
        self._stats.current_phase = new_phase
        self._emit_event(DayNightEventKind.TIME_SET.value, {
            "old_time": round(old_time, 4),
            "new_time": round(hours, 4),
            "phase": new_phase,
        })
        if new_phase != self._last_phase:
            self._emit_event(DayNightEventKind.PHASE_CHANGED.value, {
                "old_phase": self._last_phase,
                "new_phase": new_phase,
            })
            self._last_phase = new_phase
        self._check_celestial_events()
        return hours

    def get_time(self) -> float:
        """Get the current time of day (0-24 hours)."""
        return round(self._current_time, 4)

    def advance_time(self, hours: float) -> float:
        """Advance time by a number of hours."""
        new_time = self._current_time + hours
        while new_time >= 24.0:
            new_time -= 24.0
            self._day_count += 1
            self._stats.total_days_elapsed += 1
        while new_time < 0.0:
            new_time += 24.0
            self._day_count = max(0, self._day_count - 1)
        return self.set_time(new_time)

    def set_time_scale(self, scale: float) -> float:
        """Set the time scale multiplier (1.0 = real-time game time)."""
        scale = max(0.0, float(scale))
        self._time_scale = scale
        self._config.time_scale = scale
        self._emit_event(DayNightEventKind.TIME_SCALE_CHANGED.value, {"scale": scale})
        return scale

    def get_time_scale(self) -> float:
        return self._time_scale

    def get_day_count(self) -> int:
        return self._day_count

    # ------------------------------------------------------------------
    # Celestial Body Computation
    # ------------------------------------------------------------------

    def _update_celestial_positions(self) -> None:
        """Compute sun and moon positions from the current time."""
        time = self._current_time
        latitude = self._config.latitude
        lat_rad = math.radians(latitude)
        axial_tilt = math.radians(self._config.axial_tilt)

        # Sun: peaks at noon (12.0), below horizon at midnight (0.0)
        sun_hour_angle = math.radians((time - 12.0) * 15.0)
        sun_declination = axial_tilt * math.sin(2 * math.pi * self._day_count / 365.25)
        sun_alt = math.asin(
            math.sin(lat_rad) * math.sin(sun_declination) +
            math.cos(lat_rad) * math.cos(sun_declination) * math.cos(sun_hour_angle)
        )
        sun_alt_deg = math.degrees(sun_alt)
        sun_az = math.atan2(
            -math.sin(sun_hour_angle),
            math.cos(lat_rad) * math.tan(sun_declination) - math.sin(lat_rad) * math.cos(sun_hour_angle)
        )
        sun_az_deg = (math.degrees(sun_az) + 180.0) % 360.0

        sun_dir = (
            round(math.cos(sun_alt) * math.sin(math.radians(sun_az_deg)), 6),
            round(math.sin(sun_alt), 6),
            round(math.cos(sun_alt) * math.cos(math.radians(sun_az_deg)), 6),
        )

        sun_brightness = _clamp(sun_alt_deg / 90.0, 0.0, 1.0) if sun_alt_deg > -6.0 else 0.0
        self._sun = CelestialState(
            body=CelestialBody.SUN.value,
            altitude=round(sun_alt_deg, 4),
            azimuth=round(sun_az_deg, 4),
            direction=sun_dir,
            visible=sun_alt_deg > -6.0,
            brightness=round(sun_brightness, 4),
            angular_size=0.53,
        )

        # Moon: peaks at opposite time (0.0 / 24.0), with lunar cycle phase
        moon_hour_angle = math.radians((time - 0.0) * 15.0)
        moon_phase_angle = 2 * math.pi * (self._day_count % max(1, int(self._config.moon_cycle_days))) / max(1.0, self._config.moon_cycle_days)
        moon_declination = -axial_tilt * 0.3 * math.sin(moon_phase_angle)
        moon_alt = math.asin(
            math.sin(lat_rad) * math.sin(moon_declination) +
            math.cos(lat_rad) * math.cos(moon_declination) * math.cos(moon_hour_angle)
        )
        moon_alt_deg = math.degrees(moon_alt)
        moon_az = math.atan2(
            -math.sin(moon_hour_angle),
            math.cos(lat_rad) * math.tan(moon_declination) - math.sin(lat_rad) * math.cos(moon_hour_angle)
        )
        moon_az_deg = (math.degrees(moon_az) + 180.0) % 360.0

        moon_dir = (
            round(math.cos(moon_alt) * math.sin(math.radians(moon_az_deg)), 6),
            round(math.sin(moon_alt), 6),
            round(math.cos(moon_alt) * math.cos(math.radians(moon_az_deg)), 6),
        )

        moon_brightness = _clamp(moon_alt_deg / 90.0, 0.0, 1.0) if moon_alt_deg > -6.0 else 0.0
        moon_phase = (1 - math.cos(moon_phase_angle)) / 2.0
        self._moon = CelestialState(
            body=CelestialBody.MOON.value,
            altitude=round(moon_alt_deg, 4),
            azimuth=round(moon_az_deg, 4),
            direction=moon_dir,
            visible=moon_alt_deg > -6.0,
            brightness=round(moon_brightness * moon_phase, 4),
            angular_size=0.52,
        )

    def _check_celestial_events(self) -> None:
        """Check for sunrise/sunset/moonrise/moonset events."""
        if self._sun_was_visible and not self._sun.visible:
            self._emit_event(DayNightEventKind.SUNSET.value, {"time": round(self._current_time, 4)})
            self._stats.total_sunsets += 1
        elif not self._sun_was_visible and self._sun.visible:
            self._emit_event(DayNightEventKind.SUNRISE.value, {"time": round(self._current_time, 4)})
            self._stats.total_sunrises += 1

        if self._moon_was_visible and not self._moon.visible:
            self._emit_event(DayNightEventKind.MOONSET.value, {"time": round(self._current_time, 4)})
            self._stats.total_moonsets += 1
        elif not self._moon_was_visible and self._moon.visible:
            self._emit_event(DayNightEventKind.MOONRISE.value, {"time": round(self._current_time, 4)})
            self._stats.total_moonrises += 1

        self._sun_was_visible = self._sun.visible
        self._moon_was_visible = self._moon.visible

    def get_sun(self) -> CelestialState:
        return self._sun

    def get_moon(self) -> CelestialState:
        return self._moon

    # ------------------------------------------------------------------
    # Sky Color and Ambient Light
    # ------------------------------------------------------------------

    def get_sky_color(self, preset_id: Optional[str] = None) -> Dict[str, Any]:
        """Sample the sky color gradient at the current time."""
        preset = self._sky_presets.get(preset_id or "sky_default", self._sky_presets.get("sky_default"))
        if preset is None or not preset.color_stops:
            return {
                "zenith_color": [0.1, 0.2, 0.5],
                "horizon_color": [0.5, 0.6, 0.8],
                "sun_color": [1.0, 0.9, 0.7],
                "sun_glow": 0.5,
            }

        stops = sorted(preset.color_stops, key=lambda s: s.time)
        time = self._current_time

        if time <= stops[0].time:
            s = stops[0]
        elif time >= stops[-1].time:
            s = stops[-1]
        else:
            s = None
            for i in range(len(stops) - 1):
                if stops[i].time <= time <= stops[i + 1].time:
                    t = (time - stops[i].time) / max(stops[i + 1].time - stops[i].time, 0.001)
                    s = SkyColorStop(
                        time=time,
                        zenith_color=_lerp_color(stops[i].zenith_color, stops[i + 1].zenith_color, t),
                        horizon_color=_lerp_color(stops[i].horizon_color, stops[i + 1].horizon_color, t),
                        sun_color=_lerp_color(stops[i].sun_color, stops[i + 1].sun_color, t),
                        sun_glow=round(_lerp(stops[i].sun_glow, stops[i + 1].sun_glow, t), 4),
                    )
                    break
            if s is None:
                s = stops[-1]

        return {
            "zenith_color": list(s.zenith_color),
            "horizon_color": list(s.horizon_color),
            "sun_color": list(s.sun_color),
            "sun_glow": s.sun_glow,
            "preset_id": preset.preset_id,
        }

    def get_ambient_light(self) -> Dict[str, Any]:
        """Compute ambient light intensity and color temperature."""
        phase = self._find_phase(self._current_time)
        if phase is None:
            return {
                "intensity": 0.5,
                "color": [1.0, 1.0, 1.0],
                "color_temperature": 5500.0,
            }
        return {
            "intensity": phase.ambient_intensity,
            "color": list(phase.ambient_color),
            "color_temperature": phase.color_temperature,
            "phase": phase.phase,
        }

    # ------------------------------------------------------------------
    # Phase Management
    # ------------------------------------------------------------------

    def _compute_phase(self, time: float) -> str:
        """Compute the current phase name from the time."""
        phase = self._find_phase(time)
        return phase.phase if phase else TimePhase.MORNING.value

    def _find_phase(self, time: float) -> Optional[PhaseDefinition]:
        """Find the phase definition for a given time."""
        for p in self._phases:
            if p.start_time <= time < p.end_time:
                return p
        if self._phases:
            return self._phases[0]
        return None

    def get_phase(self) -> str:
        """Get the current time-of-day phase name."""
        return self._compute_phase(self._current_time)

    def list_phases(self) -> List[PhaseDefinition]:
        """List all phase definitions."""
        return list(self._phases)

    def set_phase(self, phase_name: str) -> Optional[str]:
        """Jump to the start of a named phase."""
        for p in self._phases:
            if p.phase == phase_name:
                self.set_time(p.start_time)
                return p.phase
        return None

    # ------------------------------------------------------------------
    # Sky Preset Management
    # ------------------------------------------------------------------

    def register_sky_preset(self, preset: SkyPreset) -> SkyPreset:
        """Register a sky color gradient preset."""
        if not preset.preset_id:
            preset.preset_id = _new_id("sky")
        with self._init_lock:
            self._sky_presets[preset.preset_id] = preset
            _evict_fifo_dict(self._sky_presets, _MAX_SKY_PRESETS)
            self._emit_event(DayNightEventKind.SKY_PRESET_REGISTERED.value, {"preset_id": preset.preset_id})
        return preset

    def get_sky_preset(self, preset_id: str) -> Optional[SkyPreset]:
        return self._sky_presets.get(preset_id)

    def list_sky_presets(self) -> List[SkyPreset]:
        return list(self._sky_presets.values())

    def remove_sky_preset(self, preset_id: str) -> bool:
        with self._init_lock:
            existed = preset_id in self._sky_presets
            if existed and preset_id != "sky_default":
                del self._sky_presets[preset_id]
                self._emit_event(DayNightEventKind.SKY_PRESET_REMOVED.value, {"preset_id": preset_id})
                return True
            return False

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016, current_time: Optional[float] = None) -> Dict[str, Any]:
        """Advance the day/night simulation by delta time."""
        self._tick_count += 1
        self._stats.total_ticks += 1

        if self._config.auto_advance:
            game_hours_per_second = 24.0 / max(self._config.day_length_seconds, 1.0)
            hours_to_advance = game_hours_per_second * self._time_scale * delta_time
            new_time = self._current_time + hours_to_advance
            while new_time >= 24.0:
                new_time -= 24.0
                self._day_count += 1
                self._stats.total_days_elapsed += 1
            self._current_time = new_time

        self._update_celestial_positions()
        new_phase = self._compute_phase(self._current_time)
        self._stats.time_of_day = round(self._current_time, 4)
        self._stats.current_phase = new_phase

        events_emitted = 0
        if new_phase != self._last_phase:
            self._emit_event(DayNightEventKind.PHASE_CHANGED.value, {
                "old_phase": self._last_phase,
                "new_phase": new_phase,
            })
            self._last_phase = new_phase
            events_emitted += 1

        self._check_celestial_events()

        return {
            "tick_count": self._tick_count,
            "current_time": round(self._current_time, 4),
            "phase": new_phase,
            "sun_altitude": self._sun.altitude,
            "moon_altitude": self._moon.altitude,
        }

    # ------------------------------------------------------------------
    # Config and Observability
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, details: Dict[str, Any]) -> None:
        event = DayNightEvent(timestamp=_now(), kind=kind, details=details)
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def get_config(self) -> DayNightConfig:
        return self._config

    def set_config(self, config: DayNightConfig) -> DayNightConfig:
        self._config = config
        self._time_scale = config.time_scale
        self._emit_event(DayNightEventKind.CONFIG_UPDATED.value, {})
        return config

    def list_events(self, limit: int = 100) -> List[DayNightEvent]:
        return list(self._events[-max(0, int(limit)):])

    def get_stats(self) -> DayNightStats:
        self._stats.time_of_day = round(self._current_time, 4)
        self._stats.current_phase = self._compute_phase(self._current_time)
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "current_time": round(self._current_time, 4),
            "day_count": self._day_count,
            "time_scale": self._time_scale,
            "current_phase": self._compute_phase(self._current_time),
            "sun_visible": self._sun.visible,
            "moon_visible": self._moon.visible,
            "total_sky_presets": len(self._sky_presets),
            "total_phases": len(self._phases),
            "tick_count": self._tick_count,
            "config": self._config.to_dict(),
        }

    def get_snapshot(self) -> DayNightSnapshot:
        return DayNightSnapshot(
            current_time=round(self._current_time, 4),
            day_count=self._day_count,
            sun=self._sun,
            moon=self._moon,
            sky_color=self.get_sky_color(),
            ambient_light=self.get_ambient_light(),
            current_phase=self._compute_phase(self._current_time),
            config=self._config,
            stats=self.get_stats(),
        )

    def reset(self) -> None:
        with self._init_lock:
            self._initialized = False
            self._current_time = _DEFAULT_START_TIME
            self._day_count = 0
            self._time_scale = 1.0
            self._sun = CelestialState(body=CelestialBody.SUN.value)
            self._moon = CelestialState(body=CelestialBody.MOON.value)
            self._sky_presets = {}
            self._phases = []
            self._events = []
            self._config = DayNightConfig()
            self._stats = DayNightStats()
            self._tick_count = 0
            self._last_phase = ""
            self._sun_was_visible = True
            self._moon_was_visible = False
            self._seed()


def get_day_night_cycle() -> DayNightCycleSystem:
    """Factory function to get the singleton DayNightCycleSystem instance."""
    return DayNightCycleSystem.get_instance()
