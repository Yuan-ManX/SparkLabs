"""
SparkLabs Engine - Dynamic Weather and Environment System"""

from __future__ import annotations

import json
import math
import random
import threading
import time as _time_module
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WeatherType(Enum):
    """All supported weather condition types in the simulation."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    BLIZZARD = "blizzard"
    FOG = "fog"
    HEAVY_FOG = "heavy_fog"
    WINDY = "windy"
    STORM = "storm"
    SANDSTORM = "sandstorm"
    HEATWAVE = "heatwave"
    METEOR_SHOWER = "meteor_shower"


class TimeOfDay(Enum):
    """Discrete phases within the day/night cycle."""
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    EVENING = "evening"
    NIGHT = "night"
    MIDNIGHT = "midnight"


class Season(Enum):
    """Calendar seasons for modulating weather probabilities."""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class WeatherIntensity(Enum):
    """Severity level of the active weather condition."""
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    EXTREME = "extreme"


class ClimateZone(Enum):
    """Biome-level climate classification for a weather region."""
    TROPICAL = "tropical"
    TEMPERATE = "temperate"
    ARID = "arid"
    POLAR = "polar"
    ALPINE = "alpine"
    COASTAL = "coastal"
    VOLCANIC = "volcanic"


class WeatherEventType(Enum):
    """Discrete dynamic weather events that can spawn in a region."""
    LIGHTNING_STRIKE = "lightning_strike"
    GUST_BURST = "gust_burst"
    HAIL_STORM = "hail_storm"
    FLASH_FLOOD = "flash_flood"
    HEAT_STEAM = "heat_steam"
    METEOR_IMPACT = "meteor_impact"
    SNOW_DRIFT = "snow_drift"
    TORNADO = "tornado"


class InfluenceKind(Enum):
    """Atmospheric parameters that external forces can perturb."""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"
    WIND_DIRECTION = "wind_direction"
    VISIBILITY = "visibility"
    PRECIPITATION = "precipitation"


class EventStatus(Enum):
    """Lifecycle status of a spawned weather event."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WeatherCondition:
    """Snapshot of weather state at a point in time.

    Contains all atmospheric parameters, timing information, and
    identifiers needed to describe a complete weather condition
    for rendering, gameplay, and forecasting purposes.
    """
    condition_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    weather_type: WeatherType = WeatherType.CLEAR
    intensity: WeatherIntensity = WeatherIntensity.MODERATE
    temperature: float = 22.0
    humidity: float = 0.40
    wind_speed: float = 0.05
    wind_direction: float = 0.0
    visibility: float = 1.0
    particle_density: float = 0.0
    duration: float = -1.0
    transition_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "weather_type": self.weather_type.value,
            "intensity": self.intensity.value,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "visibility": self.visibility,
            "particle_density": self.particle_density,
            "duration": self.duration,
            "transition_time": self.transition_time,
        }


@dataclass
class DayNightCycle:
    """Diurnal cycle state with ambient and sky rendering parameters.

    Tracks the progression of in-game time through the day/night cycle,
    computing the current TimeOfDay phase and associated visual parameters
    (ambient light color, sky color, shadow length) for the renderer.
    """
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    current_time: float = 0.0
    day_length_seconds: float = 86400.0
    time_of_day: TimeOfDay = TimeOfDay.MORNING
    sunrise_time: float = 21600.0
    sunset_time: float = 64800.0
    ambient_light_color: Tuple[float, float, float] = (0.8, 0.85, 1.0)
    sky_color: Tuple[float, float, float] = (0.45, 0.70, 1.0)
    shadow_length: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "current_time": self.current_time,
            "day_length_seconds": self.day_length_seconds,
            "time_of_day": self.time_of_day.value,
            "sunrise_time": self.sunrise_time,
            "sunset_time": self.sunset_time,
            "ambient_light_color": list(self.ambient_light_color),
            "sky_color": list(self.sky_color),
            "shadow_length": self.shadow_length,
        }


@dataclass
class WeatherEffect:
    """Visual particle effect definition tied to a weather type.

    Describes the spawn parameters for weather-driven particle systems
    such as rain, snow, fog, or sandstorm particles. Each effect is
    bound to one or more weather types and can be influenced by wind.
    """
    effect_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "default_effect"
    effect_type: str = "particle"
    weather_type: WeatherType = WeatherType.CLEAR
    particle_count: int = 100
    particle_size: float = 1.0
    particle_color: Tuple[int, int, int, int] = (255, 255, 255, 200)
    spawn_rate: float = 10.0
    lifetime: float = 2.0
    affected_by_wind: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "name": self.name,
            "effect_type": self.effect_type,
            "weather_type": self.weather_type.value,
            "particle_count": self.particle_count,
            "particle_size": self.particle_size,
            "particle_color": list(self.particle_color),
            "spawn_rate": self.spawn_rate,
            "lifetime": self.lifetime,
            "affected_by_wind": self.affected_by_wind,
        }


@dataclass
class WeatherRegion:
    """A spatial zone with its own climate and local weather condition.

    Regions create spatial variety in the world. Each region carries a base
    climate zone and an optional local weather condition that overrides the
    global weather inside its bounds. Priority resolves overlaps between
    regions.
    """
    region_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "region"
    climate_zone: ClimateZone = ClimateZone.TEMPERATE
    bounds: Dict[str, float] = field(default_factory=dict)
    priority: int = 0
    local_condition: Optional[WeatherCondition] = None
    base_temperature: float = 22.0
    base_humidity: float = 0.45

    def contains(self, position: Tuple[float, float, float]) -> bool:
        """Check whether a position falls inside this region's bounds."""
        if not self.bounds:
            return False
        cx = self.bounds.get("center_x", 0.0)
        cy = self.bounds.get("center_y", 0.0)
        cz = self.bounds.get("center_z", 0.0)
        rx = self.bounds.get("radius_x", self.bounds.get("radius", 0.0))
        ry = self.bounds.get("radius_y", rx)
        rz = self.bounds.get("radius_z", rx)
        dx = (position[0] - cx) / rx if rx else float("inf")
        dy = (position[1] - cy) / ry if ry else float("inf")
        dz = (position[2] - cz) / rz if rz else float("inf")
        return (dx * dx + dy * dy + dz * dz) <= 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "name": self.name,
            "climate_zone": self.climate_zone.value,
            "bounds": self.bounds,
            "priority": self.priority,
            "local_condition": self.local_condition.to_dict() if self.local_condition else None,
            "base_temperature": self.base_temperature,
            "base_humidity": self.base_humidity,
        }


@dataclass
class WeatherInfluence:
    """A transient external force perturbing a region's atmosphere.

    Skills, spells, and world interactions push an atmospheric parameter
    (temperature, humidity, wind, etc.) by an amount that decays over time,
    making weather a two-way interactive system rather than a one-way output.
    """
    influence_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_id: str = ""
    kind: InfluenceKind = InfluenceKind.TEMPERATURE
    amount: float = 0.0
    decay_rate: float = 0.05
    created_elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "influence_id": self.influence_id,
            "source_id": self.source_id,
            "kind": self.kind.value,
            "amount": self.amount,
            "decay_rate": self.decay_rate,
            "created_elapsed": self.created_elapsed,
        }


@dataclass
class WeatherEvent:
    """A discrete dynamic weather event active in a region.

    Represents transient hazards and phenomena (lightning, gust bursts,
    hail, floods, meteor impacts, tornadoes) that unfold over a duration
    at a position with a given radius and magnitude.
    """
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: WeatherEventType = WeatherEventType.GUST_BURST
    region_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 5.0
    magnitude: float = 1.0
    started_elapsed: float = 0.0
    duration: float = 10.0
    status: EventStatus = EventStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "region_id": self.region_id,
            "position": list(self.position),
            "radius": self.radius,
            "magnitude": self.magnitude,
            "started_elapsed": self.started_elapsed,
            "duration": self.duration,
            "status": self.status.value,
        }


# ---------------------------------------------------------------------------
# Weather Atmospheric Presets
# ---------------------------------------------------------------------------

_WEATHER_PRESETS: Dict[WeatherType, Dict[str, Any]] = {
    WeatherType.CLEAR: {
        "temperature": 22.0, "humidity": 0.35, "wind_speed": 0.03,
        "visibility": 1.0, "particle_density": 0.0, "wind_direction": 0.0,
    },
    WeatherType.CLOUDY: {
        "temperature": 18.0, "humidity": 0.55, "wind_speed": 0.10,
        "visibility": 0.90, "particle_density": 0.0, "wind_direction": 45.0,
    },
    WeatherType.OVERCAST: {
        "temperature": 15.0, "humidity": 0.70, "wind_speed": 0.15,
        "visibility": 0.75, "particle_density": 0.05, "wind_direction": 90.0,
    },
    WeatherType.RAIN: {
        "temperature": 14.0, "humidity": 0.85, "wind_speed": 0.18,
        "visibility": 0.70, "particle_density": 0.35, "wind_direction": 120.0,
    },
    WeatherType.HEAVY_RAIN: {
        "temperature": 12.0, "humidity": 0.95, "wind_speed": 0.25,
        "visibility": 0.45, "particle_density": 0.70, "wind_direction": 135.0,
    },
    WeatherType.THUNDERSTORM: {
        "temperature": 11.0, "humidity": 1.00, "wind_speed": 0.45,
        "visibility": 0.30, "particle_density": 0.85, "wind_direction": 160.0,
    },
    WeatherType.SNOW: {
        "temperature": -2.0, "humidity": 0.65, "wind_speed": 0.12,
        "visibility": 0.65, "particle_density": 0.30, "wind_direction": 200.0,
    },
    WeatherType.BLIZZARD: {
        "temperature": -12.0, "humidity": 0.90, "wind_speed": 0.55,
        "visibility": 0.15, "particle_density": 0.80, "wind_direction": 220.0,
    },
    WeatherType.FOG: {
        "temperature": 13.0, "humidity": 0.92, "wind_speed": 0.04,
        "visibility": 0.35, "particle_density": 0.10, "wind_direction": 0.0,
    },
    WeatherType.HEAVY_FOG: {
        "temperature": 11.0, "humidity": 0.98, "wind_speed": 0.02,
        "visibility": 0.10, "particle_density": 0.15, "wind_direction": 0.0,
    },
    WeatherType.WINDY: {
        "temperature": 16.0, "humidity": 0.40, "wind_speed": 0.50,
        "visibility": 0.85, "particle_density": 0.05, "wind_direction": 270.0,
    },
    WeatherType.STORM: {
        "temperature": 10.0, "humidity": 0.95, "wind_speed": 0.70,
        "visibility": 0.20, "particle_density": 0.90, "wind_direction": 180.0,
    },
    WeatherType.SANDSTORM: {
        "temperature": 34.0, "humidity": 0.08, "wind_speed": 0.60,
        "visibility": 0.15, "particle_density": 0.65, "wind_direction": 250.0,
    },
    WeatherType.HEATWAVE: {
        "temperature": 38.0, "humidity": 0.15, "wind_speed": 0.06,
        "visibility": 0.95, "particle_density": 0.0, "wind_direction": 0.0,
    },
    WeatherType.METEOR_SHOWER: {
        "temperature": 15.0, "humidity": 0.30, "wind_speed": 0.02,
        "visibility": 0.90, "particle_density": 0.40, "wind_direction": 0.0,
    },
}

# ---------------------------------------------------------------------------
# Weather Transition Graph
# ---------------------------------------------------------------------------

_WEATHER_TRANSITIONS: Dict[WeatherType, List[WeatherType]] = {
    WeatherType.CLEAR: [
        WeatherType.CLOUDY, WeatherType.FOG, WeatherType.WINDY,
        WeatherType.HEATWAVE, WeatherType.METEOR_SHOWER,
    ],
    WeatherType.CLOUDY: [
        WeatherType.CLEAR, WeatherType.OVERCAST, WeatherType.RAIN,
        WeatherType.SNOW, WeatherType.FOG, WeatherType.WINDY,
    ],
    WeatherType.OVERCAST: [
        WeatherType.CLOUDY, WeatherType.RAIN, WeatherType.HEAVY_RAIN,
        WeatherType.SNOW, WeatherType.FOG, WeatherType.HEAVY_FOG,
    ],
    WeatherType.RAIN: [
        WeatherType.CLOUDY, WeatherType.OVERCAST, WeatherType.HEAVY_RAIN,
        WeatherType.THUNDERSTORM, WeatherType.CLEAR,
    ],
    WeatherType.HEAVY_RAIN: [
        WeatherType.RAIN, WeatherType.THUNDERSTORM, WeatherType.STORM,
        WeatherType.OVERCAST,
    ],
    WeatherType.THUNDERSTORM: [
        WeatherType.HEAVY_RAIN, WeatherType.STORM, WeatherType.RAIN,
        WeatherType.OVERCAST, WeatherType.CLOUDY,
    ],
    WeatherType.SNOW: [
        WeatherType.CLOUDY, WeatherType.OVERCAST, WeatherType.BLIZZARD,
        WeatherType.CLEAR,
    ],
    WeatherType.BLIZZARD: [
        WeatherType.SNOW, WeatherType.STORM, WeatherType.OVERCAST,
    ],
    WeatherType.FOG: [
        WeatherType.CLEAR, WeatherType.CLOUDY, WeatherType.OVERCAST,
        WeatherType.HEAVY_FOG,
    ],
    WeatherType.HEAVY_FOG: [
        WeatherType.FOG, WeatherType.OVERCAST, WeatherType.CLOUDY,
    ],
    WeatherType.WINDY: [
        WeatherType.CLEAR, WeatherType.CLOUDY, WeatherType.SANDSTORM,
        WeatherType.STORM,
    ],
    WeatherType.STORM: [
        WeatherType.WINDY, WeatherType.HEAVY_RAIN, WeatherType.THUNDERSTORM,
        WeatherType.OVERCAST, WeatherType.CLOUDY,
    ],
    WeatherType.SANDSTORM: [
        WeatherType.CLEAR, WeatherType.WINDY, WeatherType.CLOUDY,
    ],
    WeatherType.HEATWAVE: [
        WeatherType.CLEAR, WeatherType.CLOUDY, WeatherType.WINDY,
    ],
    WeatherType.METEOR_SHOWER: [
        WeatherType.CLEAR, WeatherType.CLOUDY,
    ],
}

# ---------------------------------------------------------------------------
# Seasonal Weather Probability Weights
# ---------------------------------------------------------------------------

_SEASON_WEIGHTS: Dict[Season, Dict[WeatherType, float]] = {
    Season.SPRING: {
        WeatherType.CLEAR: 0.30, WeatherType.CLOUDY: 0.20,
        WeatherType.OVERCAST: 0.10, WeatherType.RAIN: 0.20,
        WeatherType.HEAVY_RAIN: 0.05, WeatherType.WINDY: 0.10,
        WeatherType.FOG: 0.05,
    },
    Season.SUMMER: {
        WeatherType.CLEAR: 0.40, WeatherType.CLOUDY: 0.15,
        WeatherType.RAIN: 0.10, WeatherType.THUNDERSTORM: 0.10,
        WeatherType.WINDY: 0.08, WeatherType.HEATWAVE: 0.10,
        WeatherType.FOG: 0.02, WeatherType.METEOR_SHOWER: 0.05,
    },
    Season.AUTUMN: {
        WeatherType.CLEAR: 0.22, WeatherType.CLOUDY: 0.20,
        WeatherType.OVERCAST: 0.15, WeatherType.RAIN: 0.15,
        WeatherType.HEAVY_RAIN: 0.08, WeatherType.WINDY: 0.12,
        WeatherType.FOG: 0.05, WeatherType.HEAVY_FOG: 0.03,
    },
    Season.WINTER: {
        WeatherType.CLOUDY: 0.18, WeatherType.OVERCAST: 0.15,
        WeatherType.SNOW: 0.25, WeatherType.BLIZZARD: 0.12,
        WeatherType.CLEAR: 0.10, WeatherType.FOG: 0.08,
        WeatherType.HEAVY_FOG: 0.05, WeatherType.WINDY: 0.07,
    },
}

# ---------------------------------------------------------------------------
# Intensity Multipliers
# ---------------------------------------------------------------------------

_INTENSITY_MULTIPLIERS: Dict[WeatherIntensity, float] = {
    WeatherIntensity.LIGHT: 0.40,
    WeatherIntensity.MODERATE: 0.70,
    WeatherIntensity.HEAVY: 0.90,
    WeatherIntensity.EXTREME: 1.00,
}

# ---------------------------------------------------------------------------
# Climate Zone Base Presets
# ---------------------------------------------------------------------------

_CLIMATE_PRESETS: Dict[ClimateZone, Dict[str, Any]] = {
    ClimateZone.TROPICAL: {"base_temperature": 28.0, "base_humidity": 0.80},
    ClimateZone.TEMPERATE: {"base_temperature": 18.0, "base_humidity": 0.60},
    ClimateZone.ARID: {"base_temperature": 34.0, "base_humidity": 0.15},
    ClimateZone.POLAR: {"base_temperature": -8.0, "base_humidity": 0.55},
    ClimateZone.ALPINE: {"base_temperature": 6.0, "base_humidity": 0.65},
    ClimateZone.COASTAL: {"base_temperature": 20.0, "base_humidity": 0.72},
    ClimateZone.VOLCANIC: {"base_temperature": 32.0, "base_humidity": 0.30},
}

# ---------------------------------------------------------------------------
# Day/Night Ambient Light Presets
# ---------------------------------------------------------------------------

_AMBIENT_PRESETS: Dict[TimeOfDay, Dict[str, Any]] = {
    TimeOfDay.DAWN: {
        "ambient_light_color": (0.90, 0.70, 0.50),
        "sky_color": (0.80, 0.50, 0.30),
        "shadow_length": 2.5,
    },
    TimeOfDay.MORNING: {
        "ambient_light_color": (0.85, 0.88, 1.00),
        "sky_color": (0.45, 0.70, 1.00),
        "shadow_length": 1.5,
    },
    TimeOfDay.NOON: {
        "ambient_light_color": (1.00, 1.00, 1.00),
        "sky_color": (0.35, 0.60, 1.00),
        "shadow_length": 0.3,
    },
    TimeOfDay.AFTERNOON: {
        "ambient_light_color": (0.95, 0.90, 0.85),
        "sky_color": (0.50, 0.65, 0.95),
        "shadow_length": 1.2,
    },
    TimeOfDay.DUSK: {
        "ambient_light_color": (0.85, 0.55, 0.35),
        "sky_color": (0.80, 0.40, 0.20),
        "shadow_length": 2.8,
    },
    TimeOfDay.EVENING: {
        "ambient_light_color": (0.25, 0.28, 0.45),
        "sky_color": (0.15, 0.18, 0.35),
        "shadow_length": 4.0,
    },
    TimeOfDay.NIGHT: {
        "ambient_light_color": (0.12, 0.14, 0.25),
        "sky_color": (0.05, 0.06, 0.15),
        "shadow_length": 5.0,
    },
    TimeOfDay.MIDNIGHT: {
        "ambient_light_color": (0.08, 0.10, 0.18),
        "sky_color": (0.03, 0.04, 0.10),
        "shadow_length": 5.0,
    },
}


# ---------------------------------------------------------------------------
# Helper: lerp / smoothstep
# ---------------------------------------------------------------------------

def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by factor t."""
    return a + (b - a) * max(0.0, min(1.0, t))


def _lerp_tuple(a: Tuple[float, ...], b: Tuple[float, ...],
                t: float) -> Tuple[float, ...]:
    """Linearly interpolate each component of two tuples."""
    return tuple(_lerp(a[i], b[i], t) for i in range(len(a)))


def _smoothstep(t: float) -> float:
    """Smoothstep easing function for natural transitions."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# Main Singleton Class
# ---------------------------------------------------------------------------

class WeatherSystemEngine:
    """Dynamic weather and environment simulation engine.

    Manages the complete environmental state of the game world including
    weather conditions, day/night cycles, atmospheric parameters, particle
    effects, seasonal modulation, and gameplay-impacting modifiers derived
    from environmental conditions.

    Usage:
        ws = get_weather_system()
        ws.set_day_night_cycle(86400.0, 21600.0, 64800.0)
        ws.set_weather(WeatherType.RAIN, WeatherIntensity.MODERATE, 300.0, 0.0)
        ws.advance_time(16.0)
        current = ws.get_current_weather()
        modifiers = ws.get_gameplay_modifiers()
    """

    _instance: Optional["WeatherSystemEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "WeatherSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # -- Weather state --
        self._current_weather: WeatherCondition = WeatherCondition()
        self._transition_from: Optional[WeatherCondition] = None
        self._transition_to: Optional[WeatherCondition] = None
        self._transition_start: float = 0.0
        self._transition_duration: float = 0.0

        # -- Day/night cycle --
        self._day_night: DayNightCycle = DayNightCycle()

        # -- Season --
        self._season: Season = Season.SUMMER

        # -- Weather effects --
        self._effects: Dict[str, WeatherEffect] = {}

        # -- Regional weather --
        self._regions: Dict[str, WeatherRegion] = {}

        # -- Bidirectional influences (world -> weather) --
        self._influences: Dict[str, WeatherInfluence] = {}

        # -- Dynamic events --
        self._events: List[WeatherEvent] = []
        self._listeners: List[Any] = []

        # -- Statistics --
        self._weather_history: deque = deque(maxlen=200)
        self._total_transitions: int = 0
        self._total_elapsed: float = 0.0
        self._update_count: int = 0

    # ------------------------------------------------------------------
    # Weather State Management
    # ------------------------------------------------------------------

    def set_weather(
        self,
        weather_type: WeatherType,
        intensity: WeatherIntensity = WeatherIntensity.MODERATE,
        duration: float = -1.0,
        transition_time: float = 0.0,
        region_id: str = "",
    ) -> WeatherCondition:
        """Immediately set a weather condition globally or for a region.

        Cancels any active transition and applies the requested weather
        type with the given intensity immediately. Atmospheric parameters
        are drawn from preset defaults and scaled by the intensity level.
        When region_id targets a registered region, the condition is applied
        locally to that region instead of the global weather.

        Args:
            weather_type: The target weather type to apply.
            intensity: Severity level of the weather.
            duration: How long this weather persists in seconds (-1 = indefinite).
            transition_time: Not used for immediate set (kept for API symmetry).
            region_id: Optional id of a registered region to apply weather to.

        Returns:
            The newly created WeatherCondition that is now active.
        """
        with self._lock:
            # Cancel any active transition
            self._transition_from = None
            self._transition_to = None
            self._transition_duration = 0.0

            preset = _WEATHER_PRESETS.get(weather_type,
                                          _WEATHER_PRESETS[WeatherType.CLEAR])
            intensity_mult = _INTENSITY_MULTIPLIERS.get(intensity, 0.70)

            condition = WeatherCondition(
                weather_type=weather_type,
                intensity=intensity,
                temperature=preset["temperature"],
                humidity=preset["humidity"],
                wind_speed=preset["wind_speed"] * intensity_mult,
                wind_direction=preset["wind_direction"],
                visibility=preset["visibility"] * (1.0 - 0.3 * (intensity_mult - 0.4)),
                particle_density=preset["particle_density"] * intensity_mult,
                duration=duration,
                transition_time=transition_time,
            )

            if region_id and region_id in self._regions:
                self._regions[region_id].local_condition = condition
                return condition

            self._current_weather = condition
            self._weather_history.append(condition)
            return condition

    def transition_weather(
        self,
        weather_type: WeatherType,
        intensity: WeatherIntensity = WeatherIntensity.MODERATE,
        duration: float = -1.0,
        transition_time: float = 5.0,
    ) -> WeatherCondition:
        """Initiate a smooth transition to a target weather condition.

        The current weather parameters are interpolated toward the target
        weather's parameters over the specified transition_time using
        smoothstep easing. The transition progresses each time
        advance_time() is called.

        Args:
            weather_type: The target weather type to transition to.
            intensity: Severity level of the target weather.
            duration: How long the target weather persists after transition.
            transition_time: Duration of the interpolation in seconds.

        Returns:
            The target WeatherCondition that the system is transitioning toward.
        """
        with self._lock:
            preset = _WEATHER_PRESETS.get(weather_type,
                                          _WEATHER_PRESETS[WeatherType.CLEAR])
            intensity_mult = _INTENSITY_MULTIPLIERS.get(intensity, 0.70)

            target = WeatherCondition(
                weather_type=weather_type,
                intensity=intensity,
                temperature=preset["temperature"],
                humidity=preset["humidity"],
                wind_speed=preset["wind_speed"] * intensity_mult,
                wind_direction=preset["wind_direction"],
                visibility=preset["visibility"] * (1.0 - 0.3 * (intensity_mult - 0.4)),
                particle_density=preset["particle_density"] * intensity_mult,
                duration=duration,
                transition_time=transition_time,
            )

            # Snapshot the current weather as the transition origin
            self._transition_from = WeatherCondition(
                weather_type=self._current_weather.weather_type,
                intensity=self._current_weather.intensity,
                temperature=self._current_weather.temperature,
                humidity=self._current_weather.humidity,
                wind_speed=self._current_weather.wind_speed,
                wind_direction=self._current_weather.wind_direction,
                visibility=self._current_weather.visibility,
                particle_density=self._current_weather.particle_density,
                duration=self._current_weather.duration,
                transition_time=transition_time,
            )
            self._transition_to = target
            self._transition_start = self._total_elapsed
            self._transition_duration = max(0.01, transition_time)
            self._total_transitions += 1

            return target

    def get_current_weather(self, region_id: str = "") -> WeatherCondition:
        """Get the current effective weather condition.

        If a transition is active, returns an interpolated WeatherCondition
        between the origin and target. Otherwise returns the current
        weather directly. When region_id targets a registered region with a
        local condition, that region's weather is returned.

        Args:
            region_id: Optional id of a registered region.

        Returns:
            The active WeatherCondition, interpolated during transitions.
        """
        with self._lock:
            region = self._regions.get(region_id)
            if region is not None and region.local_condition is not None:
                return self._apply_influences_to_condition(
                    region.local_condition, region_id,
                )

            if self._transition_from is None or self._transition_to is None:
                return self._current_weather

            elapsed = self._total_elapsed - self._transition_start
            if elapsed >= self._transition_duration:
                # Transition complete
                self._current_weather = self._transition_to
                self._weather_history.append(self._transition_to)
                self._transition_from = None
                self._transition_to = None
                self._transition_duration = 0.0
                return self._current_weather

            raw_t = elapsed / self._transition_duration
            t = _smoothstep(raw_t)

            return WeatherCondition(
                weather_type=self._transition_to.weather_type,
                intensity=self._transition_to.intensity,
                temperature=_lerp(
                    self._transition_from.temperature,
                    self._transition_to.temperature, t,
                ),
                humidity=_lerp(
                    self._transition_from.humidity,
                    self._transition_to.humidity, t,
                ),
                wind_speed=_lerp(
                    self._transition_from.wind_speed,
                    self._transition_to.wind_speed, t,
                ),
                wind_direction=_lerp(
                    self._transition_from.wind_direction,
                    self._transition_to.wind_direction, t,
                ),
                visibility=_lerp(
                    self._transition_from.visibility,
                    self._transition_to.visibility, t,
                ),
                particle_density=_lerp(
                    self._transition_from.particle_density,
                    self._transition_to.particle_density, t,
                ),
                duration=self._transition_to.duration,
                transition_time=self._transition_duration - elapsed,
            )

    # ------------------------------------------------------------------
    # Day/Night Cycle
    # ------------------------------------------------------------------

    def set_day_night_cycle(
        self,
        day_length_seconds: float = 86400.0,
        sunrise_time: float = 21600.0,
        sunset_time: float = 64800.0,
    ) -> DayNightCycle:
        """Configure the day/night cycle parameters.

        Args:
            day_length_seconds: Total length of a full day in seconds.
            sunrise_time: Time offset (seconds) within the day when sunrise occurs.
            sunset_time: Time offset (seconds) within the day when sunset occurs.

        Returns:
            The updated DayNightCycle object.
        """
        with self._lock:
            self._day_night.day_length_seconds = max(60.0, day_length_seconds)
            self._day_night.sunrise_time = sunrise_time % self._day_night.day_length_seconds
            self._day_night.sunset_time = sunset_time % self._day_night.day_length_seconds
            self._day_night.current_time = self._day_night.current_time % self._day_night.day_length_seconds
            self._update_time_of_day()
            return self._day_night

    def set_season(self, season: Season) -> None:
        """Set the current season for weather probability modulation.

        Args:
            season: The new season to apply.
        """
        with self._lock:
            self._season = season

    def get_time_of_day(self) -> TimeOfDay:
        """Get the current time of day phase.

        Returns:
            The active TimeOfDay enum value.
        """
        with self._lock:
            return self._day_night.time_of_day

    def advance_time(self, delta_seconds: float) -> DayNightCycle:
        """Advance the simulation clock by the given delta.

        Progresses the day/night cycle, updates the time of day phase,
        animates active weather transitions, updates weather condition
        durations, and ticks regional weather, influences, and dynamic events.

        Args:
            delta_seconds: Time to advance in seconds.

        Returns:
            The updated DayNightCycle object.
        """
        dt = max(0.0, delta_seconds)
        with self._lock:
            self._total_elapsed += dt
            self._update_count += 1

            # Advance day/night cycle
            self._day_night.current_time += dt
            self._day_night.current_time %= self._day_night.day_length_seconds
            self._update_time_of_day()

            # Handle weather duration expiry
            if self._current_weather.duration > 0:
                self._current_weather.duration = max(
                    0.0, self._current_weather.duration - dt,
                )

            # Tick region local weather durations
            for region in self._regions.values():
                if region.local_condition is not None and region.local_condition.duration > 0:
                    region.local_condition.duration = max(
                        0.0, region.local_condition.duration - dt,
                    )

            # Tick transient dynamics (influences and events)
            self._tick_dynamics(dt)

            return self._day_night

    def update(self, delta_time_ms: float = 1000.0) -> Dict[str, Any]:
        """Tick the simulation from a backend request.

        Convenience wrapper over advance_time accepting milliseconds, used by
        API-driven game loops.

        Args:
            delta_time_ms: Time to advance in milliseconds.

        Returns:
            Current weather statistics after the tick.
        """
        delta_seconds = max(0.0, float(delta_time_ms)) / 1000.0
        self.advance_time(delta_seconds)
        return self.get_stats()

    def transition(
        self,
        region_id: str,
        target_weather: str,
        duration_ms: float = 5000.0,
        intensity: str = "moderate",
    ) -> WeatherCondition:
        """Transition weather for a region or the global weather.

        Convenience wrapper for API consumers using string weather names and
        millisecond durations.

        Args:
            region_id: Target region (empty targets global weather).
            target_weather: Target weather type name.
            duration_ms: Transition duration in milliseconds.
            intensity: Intensity level name for the target weather.

        Returns:
            The target WeatherCondition the system transitions toward.
        """
        wt = self._parse_weather_type(target_weather)
        iv = self._parse_intensity(intensity)
        transition_time = max(0.1, float(duration_ms)) / 1000.0
        target = self.transition_weather(wt, iv, -1.0, transition_time)
        return target

    @staticmethod
    def _parse_weather_type(name: str) -> WeatherType:
        """Parse a weather type name string into a WeatherType enum."""
        for wt in WeatherType:
            if wt.value == name or wt.name.lower() == name.lower():
                return wt
        return WeatherType.CLEAR

    @staticmethod
    def _parse_intensity(name: str) -> WeatherIntensity:
        """Parse an intensity name string into a WeatherIntensity enum."""
        for iv in WeatherIntensity:
            if iv.value == name or iv.name.lower() == name.lower():
                return iv
        return WeatherIntensity.MODERATE

    def _update_time_of_day(self) -> None:
        """Compute the current TimeOfDay phase from cycle parameters."""
        t = self._day_night.current_time
        day_len = self._day_night.day_length_seconds
        sunrise = self._day_night.sunrise_time
        sunset = self._day_night.sunset_time

        dawn_window = 1800.0  # 30 minutes
        dusk_window = 1800.0

        dawn_start = (sunrise - dawn_window) % day_len
        dawn_end = (sunrise + dawn_window) % day_len
        dusk_start = (sunset - dusk_window) % day_len
        dusk_end = (sunset + dusk_window) % day_len

        noon_time = day_len / 2.0
        noon_window = 1800.0

        if _time_in_range(t, dawn_start, dawn_end, day_len):
            new_tod = TimeOfDay.DAWN
        elif _time_in_range(t, dawn_end, noon_time - noon_window, day_len):
            new_tod = TimeOfDay.MORNING
        elif _time_in_range(t, noon_time - noon_window, noon_time + noon_window, day_len):
            new_tod = TimeOfDay.NOON
        elif _time_in_range(t, noon_time + noon_window, dusk_start, day_len):
            new_tod = TimeOfDay.AFTERNOON
        elif _time_in_range(t, dusk_start, dusk_end, day_len):
            new_tod = TimeOfDay.DUSK
        elif _time_in_range(t, dusk_end, day_len * 0.85, day_len):
            new_tod = TimeOfDay.EVENING
        elif _time_in_range(t, day_len * 0.85, day_len * 0.94, day_len):
            new_tod = TimeOfDay.NIGHT
        else:
            new_tod = TimeOfDay.MIDNIGHT

        if new_tod != self._day_night.time_of_day:
            self._day_night.time_of_day = new_tod
            preset = _AMBIENT_PRESETS.get(new_tod, _AMBIENT_PRESETS[TimeOfDay.NOON])
            self._day_night.ambient_light_color = preset["ambient_light_color"]
            self._day_night.sky_color = preset["sky_color"]
            self._day_night.shadow_length = preset["shadow_length"]

    # ------------------------------------------------------------------
    # Weather Effects
    # ------------------------------------------------------------------

    def add_weather_effect(
        self,
        name: str,
        weather_type: WeatherType,
        particle_count: int = 100,
        particle_size: float = 1.0,
        particle_color: Tuple[int, int, int, int] = (255, 255, 255, 200),
        spawn_rate: float = 10.0,
        lifetime: float = 2.0,
        affected_by_wind: bool = True,
    ) -> WeatherEffect:
        """Register a new weather particle effect.

        Creates a WeatherEffect definition that the renderer can use to
        spawn particle systems when the associated weather type is active.

        Args:
            name: Human-readable name for the effect.
            weather_type: The weather type this effect is bound to.
            particle_count: Maximum number of simultaneous particles.
            particle_size: Base size of each particle.
            particle_color: RGBA color tuple for particles.
            spawn_rate: Particles spawned per second.
            lifetime: Average lifetime of each particle in seconds.
            affected_by_wind: Whether wind influences particle motion.

        Returns:
            The newly created WeatherEffect.
        """
        with self._lock:
            effect = WeatherEffect(
                name=name,
                effect_type="particle",
                weather_type=weather_type,
                particle_count=particle_count,
                particle_size=particle_size,
                particle_color=particle_color,
                spawn_rate=spawn_rate,
                lifetime=lifetime,
                affected_by_wind=affected_by_wind,
            )
            self._effects[effect.effect_id] = effect
            return effect

    def get_weather_effects(self) -> List[WeatherEffect]:
        """Get all registered weather effects.

        Returns:
            List of all WeatherEffect objects currently registered.
        """
        with self._lock:
            return list(self._effects.values())

    # ------------------------------------------------------------------
    # Regional Weather
    # ------------------------------------------------------------------

    def register_region(
        self,
        name: str,
        climate_zone: ClimateZone = ClimateZone.TEMPERATE,
        bounds: Optional[Dict[str, float]] = None,
        priority: int = 0,
    ) -> WeatherRegion:
        """Register a spatial weather region with its own climate.

        Args:
            name: Human-readable region name.
            climate_zone: Base climate classification for the region.
            bounds: Ellipsoid bounds dict with center_x/y/z and radius_x/y/z
                (or a shared radius). Empty bounds match no positions.
            priority: Higher priority regions win when bounds overlap.

        Returns:
            The newly registered WeatherRegion.
        """
        with self._lock:
            preset = _CLIMATE_PRESETS.get(
                climate_zone, _CLIMATE_PRESETS[ClimateZone.TEMPERATE],
            )
            region = WeatherRegion(
                name=name,
                climate_zone=climate_zone,
                bounds=bounds or {},
                priority=priority,
                base_temperature=preset["base_temperature"],
                base_humidity=preset["base_humidity"],
            )
            self._regions[region.region_id] = region
            return region

    def unregister_region(self, region_id: str) -> bool:
        """Remove a region and its local weather from the simulation."""
        with self._lock:
            return self._regions.pop(region_id, None) is not None

    def get_regions(self) -> List[WeatherRegion]:
        """Get all registered weather regions."""
        with self._lock:
            return list(self._regions.values())

    def set_climate(self, region_id: str, climate_zone: ClimateZone) -> WeatherRegion:
        """Change the climate zone of an existing region."""
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                raise KeyError(f"Region not found: {region_id}")
            preset = _CLIMATE_PRESETS.get(
                climate_zone, _CLIMATE_PRESETS[ClimateZone.TEMPERATE],
            )
            region.climate_zone = climate_zone
            region.base_temperature = preset["base_temperature"]
            region.base_humidity = preset["base_humidity"]
            return region

    def get_weather_at(self, position: Tuple[float, float, float]) -> Tuple[str, WeatherCondition]:
        """Resolve the effective weather at a world position.

        Finds the highest-priority region containing the position and returns
        its weather (region local condition blended with influences), falling
        back to the global weather when no region contains the position.

        Args:
            position: World-space coordinates (x, y, z).

        Returns:
            A tuple of (region_id or "", resolved WeatherCondition).
        """
        with self._lock:
            best_region: Optional[WeatherRegion] = None
            for region in self._regions.values():
                if region.contains(position):
                    if best_region is None or region.priority > best_region.priority:
                        best_region = region
            if best_region is not None:
                if best_region.local_condition is not None:
                    return best_region.region_id, self._apply_influences_to_condition(
                        best_region.local_condition, best_region.region_id,
                    )
                return best_region.region_id, self._region_derived_condition(best_region)
            return "", self.get_current_weather()

    def get_current(self, region_id: str = "") -> WeatherCondition:
        """Alias for get_current_weather with region support."""
        return self.get_current_weather(region_id)

    def get_forecast(self, region_id: str = "", forecast_seconds: float = 3600.0) -> List[WeatherCondition]:
        """Produce a weather forecast for a region or the global weather."""
        with self._lock:
            if region_id and region_id in self._regions:
                region = self._regions[region_id]
                base = region.local_condition or self._region_derived_condition(region)
                return self._forecast_from(base, forecast_seconds)
            return self.predict_weather(forecast_seconds)

    def get_particles(self, region_id: str = "") -> List[WeatherEffect]:
        """Get particle effects matching the active weather of a region."""
        with self._lock:
            condition = self.get_current_weather(region_id)
            return [e for e in self._effects.values() if e.weather_type == condition.weather_type]

    def _region_derived_condition(self, region: WeatherRegion) -> WeatherCondition:
        """Build a WeatherCondition from a region's base climate and the global weather."""
        global_cond = self._current_weather
        temp = region.base_temperature + (global_cond.temperature - 22.0)
        humidity = max(0.0, min(1.0, region.base_humidity + (global_cond.humidity - 0.45)))
        return WeatherCondition(
            weather_type=global_cond.weather_type,
            intensity=global_cond.intensity,
            temperature=temp,
            humidity=humidity,
            wind_speed=global_cond.wind_speed,
            wind_direction=global_cond.wind_direction,
            visibility=global_cond.visibility,
            particle_density=global_cond.particle_density,
            duration=global_cond.duration,
            transition_time=global_cond.transition_time,
        )

    def _forecast_from(self, base: WeatherCondition, forecast_seconds: float) -> List[WeatherCondition]:
        """Run the probabilistic forecast seeded from a given condition."""
        forecast_seconds = max(1.0, forecast_seconds)
        predictions: List[WeatherCondition] = []
        time_remaining = forecast_seconds
        current_wt = base.weather_type

        first_duration = min(
            base.duration if base.duration > 0 else 120.0, time_remaining,
        )
        predictions.append(WeatherCondition(
            weather_type=current_wt,
            intensity=base.intensity,
            temperature=base.temperature,
            humidity=base.humidity,
            wind_speed=base.wind_speed,
            wind_direction=base.wind_direction,
            visibility=base.visibility,
            particle_density=base.particle_density,
            duration=first_duration,
            transition_time=0.0,
        ))
        time_remaining -= first_duration

        max_steps = 20
        step = 0
        while time_remaining > 0 and step < max_steps:
            step += 1
            candidates = _WEATHER_TRANSITIONS.get(current_wt, [WeatherType.CLEAR])
            season_weights = _SEASON_WEIGHTS.get(self._season, {})
            weighted = [
                (wt_c, max(0.01, season_weights.get(wt_c, 0.02)))
                for wt_c in candidates
            ]
            if not weighted:
                break
            weathers, weights = zip(*weighted)
            total_w = sum(weights)
            next_wt = random.choices(weathers, weights=[w / total_w for w in weights], k=1)[0]
            step_duration = min(random.uniform(60.0, 600.0), time_remaining)
            intensity = random.choices(
                list(WeatherIntensity), weights=[0.15, 0.40, 0.30, 0.15], k=1,
            )[0]
            preset = _WEATHER_PRESETS.get(next_wt, _WEATHER_PRESETS[WeatherType.CLEAR])
            intensity_mult = _INTENSITY_MULTIPLIERS.get(intensity, 0.70)
            predictions.append(WeatherCondition(
                weather_type=next_wt,
                intensity=intensity,
                temperature=preset["temperature"],
                humidity=preset["humidity"],
                wind_speed=preset["wind_speed"] * intensity_mult,
                wind_direction=preset["wind_direction"],
                visibility=preset["visibility"],
                particle_density=preset["particle_density"] * intensity_mult,
                duration=step_duration,
                transition_time=random.uniform(3.0, 15.0),
            ))
            time_remaining -= step_duration
            current_wt = next_wt

        return predictions

    # ------------------------------------------------------------------
    # Bidirectional Influence (World -> Weather)
    # ------------------------------------------------------------------

    def apply_weather_influence(
        self,
        region_id: str,
        source_id: str,
        kind: InfluenceKind,
        amount: float,
        decay_rate: float = 0.05,
    ) -> WeatherInfluence:
        """Push an atmospheric parameter in a region from a world action.

        Skills, spells, and world events can heat, chill, dampen, or stir the
        air. The influence accumulates and decays over time, enabling a
        two-way loop where the world shapes the weather.

        Args:
            region_id: Target region (empty targets the global weather).
            source_id: Identifier of the acting entity or skill.
            kind: The atmospheric parameter to perturb.
            amount: Signed magnitude of the perturbation.
            decay_rate: Fraction of the influence lost per second.

        Returns:
            The registered WeatherInfluence.
        """
        with self._lock:
            influence = WeatherInfluence(
                source_id=source_id,
                kind=kind,
                amount=amount,
                decay_rate=max(0.0, min(1.0, decay_rate)),
                created_elapsed=self._total_elapsed,
            )
            if region_id not in self._regions:
                region_id = ""
            influence.region_id = region_id
            self._influences[influence.influence_id] = influence
            return influence

    def get_influences(self, region_id: str = "") -> List[WeatherInfluence]:
        """Get active influences for a region (or global when empty)."""
        with self._lock:
            return [
                inf for inf in self._influences.values()
                if (inf.region_id == region_id) or (region_id == "" and inf.region_id == "")
            ]

    def _apply_influences_to_condition(
        self, condition: WeatherCondition, region_id: str,
    ) -> WeatherCondition:
        """Return a copy of a condition with active influences applied."""
        influences = [
            inf for inf in self._influences.values() if inf.region_id == region_id
        ]
        if not influences:
            return condition

        temp = condition.temperature
        humidity = condition.humidity
        wind_speed = condition.wind_speed
        wind_dir = condition.wind_direction
        visibility = condition.visibility
        for inf in influences:
            if inf.kind == InfluenceKind.TEMPERATURE:
                temp += inf.amount
            elif inf.kind == InfluenceKind.HUMIDITY:
                humidity = max(0.0, min(1.0, humidity + inf.amount))
            elif inf.kind == InfluenceKind.WIND_SPEED:
                wind_speed = max(0.0, wind_speed + inf.amount)
            elif inf.kind == InfluenceKind.WIND_DIRECTION:
                wind_dir = (wind_dir + inf.amount) % 360.0
            elif inf.kind == InfluenceKind.VISIBILITY:
                visibility = max(0.0, min(1.0, visibility + inf.amount))
            elif inf.kind == InfluenceKind.PRECIPITATION:
                humidity = max(0.0, min(1.0, humidity + inf.amount * 0.5))

        return WeatherCondition(
            condition_id=condition.condition_id,
            weather_type=condition.weather_type,
            intensity=condition.intensity,
            temperature=temp,
            humidity=humidity,
            wind_speed=wind_speed,
            wind_direction=wind_dir,
            visibility=visibility,
            particle_density=condition.particle_density,
            duration=condition.duration,
            transition_time=condition.transition_time,
        )

    def _tick_influences(self, dt: float) -> None:
        """Decay active influences over time and prune exhausted ones."""
        expired: List[str] = []
        for inf_id, inf in self._influences.items():
            inf.amount *= (1.0 - inf.decay_rate * dt)
            if abs(inf.amount) < 0.01:
                expired.append(inf_id)
        for inf_id in expired:
            self._influences.pop(inf_id, None)

    # ------------------------------------------------------------------
    # Dynamic Events & Hazards
    # ------------------------------------------------------------------

    def spawn_weather_event(
        self,
        event_type: WeatherEventType,
        region_id: str = "",
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        radius: float = 5.0,
        magnitude: float = 1.0,
        duration: float = 10.0,
    ) -> WeatherEvent:
        """Spawn a discrete dynamic weather event in a region.

        Emits the event to registered listeners so the game loop can react
        (e.g. lightning damage, gust knockback, meteor impact).

        Args:
            event_type: The hazard or phenomenon to spawn.
            region_id: Region the event belongs to (empty = global).
            position: World-space origin of the event.
            radius: Effective radius of the event in world units.
            magnitude: Severity multiplier for the event.
            duration: How long the event persists in seconds.

        Returns:
            The spawned WeatherEvent.
        """
        with self._lock:
            if region_id not in self._regions:
                region_id = ""
            event = WeatherEvent(
                event_type=event_type,
                region_id=region_id,
                position=position,
                radius=radius,
                magnitude=magnitude,
                started_elapsed=self._total_elapsed,
                duration=max(0.1, duration),
                status=EventStatus.ACTIVE,
            )
            self._events.append(event)
            self._emit_event("weather_event_spawned", event)
            return event

    def get_active_events(self, region_id: str = "") -> List[WeatherEvent]:
        """Get active weather events for a region (or globally)."""
        with self._lock:
            return [
                ev for ev in self._events
                if ev.status == EventStatus.ACTIVE
                and (not region_id or ev.region_id == region_id)
            ]

    def cancel_weather_event(self, event_id: str) -> bool:
        """Cancel an active weather event by id."""
        with self._lock:
            for ev in self._events:
                if ev.event_id == event_id and ev.status == EventStatus.ACTIVE:
                    ev.status = EventStatus.CANCELLED
                    return True
            return False

    def _tick_events(self, dt: float) -> None:
        """Advance active events and expire completed ones."""
        elapsed = self._total_elapsed
        for ev in self._events:
            if ev.status != EventStatus.ACTIVE:
                continue
            if elapsed - ev.started_elapsed >= ev.duration:
                ev.status = EventStatus.EXPIRED
                self._emit_event("weather_event_expired", ev)

    def _emit_event(self, kind: str, event: WeatherEvent) -> None:
        """Broadcast a weather event to registered listeners."""
        payload = {"kind": kind, "event": event.to_dict()}
        for listener in list(self._listeners):
            try:
                listener(payload)
            except Exception:
                continue

    def register_weather_listener(self, listener: Any) -> None:
        """Register a callable that receives weather event notifications."""
        self._listeners.append(listener)

    # ------------------------------------------------------------------
    # Agent / NPC Perception Context
    # ------------------------------------------------------------------

    def get_perception_context(
        self,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        agent_id: str = "",
    ) -> Dict[str, Any]:
        """Build a weather perception snapshot for an Agent or NPC.

        Combines the local weather, gameplay modifiers, active events, and
        safety hints into a compact context an Agent can consume to react to
        the environment.

        Args:
            position: World-space position of the perceiving entity.
            agent_id: Identifier of the perceiving entity (for tracking).

        Returns:
            Dictionary with weather, modifiers, events, and safety hints.
        """
        with self._lock:
            region_id, condition = self.get_weather_at(position)
            modifiers = self.get_gameplay_modifiers(region_id)
            events = [
                ev.to_dict() for ev in self.get_active_events(region_id)
            ]
            tod = self._day_night.time_of_day.value

            hazards: List[str] = []
            for ev in events:
                if ev["event_type"] in (
                    "lightning_strike", "tornado", "flash_flood",
                ):
                    hazards.append(ev["event_type"])
            if modifiers["npc_behavior"]["seek_shelter"]:
                hazards.append("seek_shelter")

            return {
                "agent_id": agent_id,
                "region_id": region_id,
                "weather": condition.to_dict(),
                "time_of_day": tod,
                "season": self._season.value,
                "modifiers": modifiers,
                "active_events": events,
                "hazards": hazards,
            }

    # ------------------------------------------------------------------
    # Game Logic IR Context
    # ------------------------------------------------------------------

    def to_condition_context(self, region_id: str = "") -> Dict[str, Any]:
        """Export weather state as a flat context for Game Logic IR conditions.

        Produces scalar values the Game Logic runtime can reference as
        condition sources, e.g. weather.visibility, weather.temperature,
        weather.wind_speed, weather.intensity.

        Args:
            region_id: Optional region to resolve weather from.

        Returns:
            Flat dictionary keyed for IR condition evaluation.
        """
        with self._lock:
            condition = self.get_current_weather(region_id)
            return {
                "weather.type": condition.weather_type.value,
                "weather.intensity": condition.intensity.value,
                "weather.temperature": condition.temperature,
                "weather.humidity": condition.humidity,
                "weather.wind_speed": condition.wind_speed,
                "weather.wind_direction": condition.wind_direction,
                "weather.visibility": condition.visibility,
                "weather.particle_density": condition.particle_density,
                "weather.time_of_day": self._day_night.time_of_day.value,
                "weather.season": self._season.value,
                "weather.event_count": len(self.get_active_events(region_id)),
            }

    def _tick_dynamics(self, dt: float) -> None:
        """Tick transient dynamics (influences and events)."""
        self._tick_influences(dt)
        self._tick_events(dt)

    # ------------------------------------------------------------------
    # Gameplay Modifiers
    # ------------------------------------------------------------------

    def get_gameplay_modifiers(self, region_id: str = "") -> Dict[str, Any]:
        """Compute gameplay-impacting modifiers from current conditions.

        Derives movement speed adjustments, visibility penalties, damage
        modifiers, elemental bonuses, and NPC behavior hints based on the
        active weather, time of day, and season. When region_id is provided,
        modifiers derive from that region's resolved weather.

        Args:
            region_id: Optional region id to compute modifiers for.

        Returns:
            Dictionary of gameplay modifier categories and their values.
        """
        with self._lock:
            weather = self.get_current_weather(region_id)
            tod = self._day_night.time_of_day
            wt = weather.weather_type

            # -- Movement Speed Modifiers --
            movement_speed = 1.0
            movement_breakdown: Dict[str, float] = {}
            if wt == WeatherType.RAIN:
                movement_speed -= 0.10
                movement_breakdown["rain"] = -0.10
            if wt == WeatherType.HEAVY_RAIN:
                movement_speed -= 0.15
                movement_breakdown["heavy_rain"] = -0.15
            if wt == WeatherType.SNOW:
                movement_speed -= 0.20
                movement_breakdown["snow"] = -0.20
            if wt == WeatherType.BLIZZARD:
                movement_speed -= 0.35
                movement_breakdown["blizzard"] = -0.35
            if wt == WeatherType.STORM:
                movement_speed -= 0.30
                movement_breakdown["storm"] = -0.30
            if wt == WeatherType.SANDSTORM:
                movement_speed -= 0.15
                movement_breakdown["sandstorm"] = -0.15
            if wt == WeatherType.WINDY:
                movement_speed -= 0.05
                movement_breakdown["windy"] = -0.05

            # -- Visibility Modifiers --
            visibility = 1.0
            visibility_breakdown: Dict[str, float] = {}
            if wt == WeatherType.FOG:
                visibility -= 0.50
                visibility_breakdown["fog"] = -0.50
            if wt == WeatherType.HEAVY_FOG:
                visibility -= 0.70
                visibility_breakdown["heavy_fog"] = -0.70
            if wt == WeatherType.STORM:
                visibility -= 0.60
                visibility_breakdown["storm"] = -0.60
            if wt == WeatherType.BLIZZARD:
                visibility -= 0.75
                visibility_breakdown["blizzard"] = -0.75
            if wt == WeatherType.SANDSTORM:
                visibility -= 0.55
                visibility_breakdown["sandstorm"] = -0.55
            if wt == WeatherType.HEAVY_RAIN:
                visibility -= 0.30
                visibility_breakdown["heavy_rain"] = -0.30
            if wt == WeatherType.RAIN:
                visibility -= 0.15
                visibility_breakdown["rain"] = -0.15
            if wt == WeatherType.OVERCAST:
                visibility -= 0.10
                visibility_breakdown["overcast"] = -0.10
            if tod in (TimeOfDay.NIGHT, TimeOfDay.MIDNIGHT):
                visibility -= 0.40
                visibility_breakdown["night"] = -0.40
            if tod == TimeOfDay.EVENING:
                visibility -= 0.20
                visibility_breakdown["evening"] = -0.20

            # -- Damage Modifiers --
            damage_modifiers: Dict[str, Any] = {
                "lightning_damage": False,
                "lightning_damage_chance": 0.0,
                "cold_damage_over_time": 0.0,
                "heat_damage_over_time": 0.0,
                "wind_knockback": 0.0,
            }
            if wt == WeatherType.THUNDERSTORM:
                damage_modifiers["lightning_damage"] = True
                damage_modifiers["lightning_damage_chance"] = 0.15
            if wt == WeatherType.STORM:
                damage_modifiers["lightning_damage"] = True
                damage_modifiers["lightning_damage_chance"] = 0.08
                damage_modifiers["wind_knockback"] = 0.30
            if wt == WeatherType.BLIZZARD:
                damage_modifiers["cold_damage_over_time"] = 2.0
            if wt == WeatherType.HEATWAVE:
                damage_modifiers["heat_damage_over_time"] = 1.5
            if wt == WeatherType.SANDSTORM:
                damage_modifiers["heat_damage_over_time"] = 0.5

            # -- Elemental Bonuses --
            elemental_bonuses: Dict[str, float] = {
                "fire": 0.0,
                "water": 0.0,
                "ice": 0.0,
                "lightning": 0.0,
                "earth": 0.0,
                "wind": 0.0,
            }
            if wt in (WeatherType.RAIN, WeatherType.HEAVY_RAIN):
                elemental_bonuses["fire"] = -0.20
                elemental_bonuses["water"] = 0.20
            if wt == WeatherType.THUNDERSTORM:
                elemental_bonuses["lightning"] = 0.30
                elemental_bonuses["water"] = 0.10
            if wt in (WeatherType.SNOW, WeatherType.BLIZZARD):
                elemental_bonuses["ice"] = 0.20
                elemental_bonuses["fire"] = -0.10
            if wt == WeatherType.HEATWAVE:
                elemental_bonuses["fire"] = 0.25
                elemental_bonuses["ice"] = -0.30
            if wt == WeatherType.WINDY:
                elemental_bonuses["wind"] = 0.15
            if wt == WeatherType.STORM:
                elemental_bonuses["wind"] = 0.20
                elemental_bonuses["lightning"] = 0.15
                elemental_bonuses["water"] = 0.15
            if wt == WeatherType.SANDSTORM:
                elemental_bonuses["earth"] = 0.20
                elemental_bonuses["wind"] = 0.10

            # -- NPC Behavior Hints --
            npc_behavior: Dict[str, Any] = {
                "seek_shelter": False,
                "shelter_reasons": [],
                "reduced_activity": False,
                "reduced_activity_reason": "",
                "aggression_modifier": 0.0,
            }
            shelter_weathers = {
                WeatherType.STORM, WeatherType.BLIZZARD,
                WeatherType.THUNDERSTORM, WeatherType.HEAVY_RAIN,
                WeatherType.SANDSTORM,
            }
            if wt in shelter_weathers:
                npc_behavior["seek_shelter"] = True
                npc_behavior["shelter_reasons"].append(wt.value)
            if wt == WeatherType.HEATWAVE:
                npc_behavior["seek_shelter"] = True
                npc_behavior["shelter_reasons"].append("heatwave")
            if tod in (TimeOfDay.NIGHT, TimeOfDay.MIDNIGHT):
                npc_behavior["reduced_activity"] = True
                npc_behavior["reduced_activity_reason"] = "nighttime"
            if wt == WeatherType.STORM:
                npc_behavior["aggression_modifier"] = -0.30
            if wt == WeatherType.THUNDERSTORM:
                npc_behavior["aggression_modifier"] = -0.20

            return {
                "movement_speed_multiplier": round(movement_speed, 3),
                "movement_breakdown": movement_breakdown,
                "visibility_multiplier": round(max(0.0, visibility), 3),
                "visibility_breakdown": visibility_breakdown,
                "damage_modifiers": damage_modifiers,
                "elemental_bonuses": elemental_bonuses,
                "npc_behavior": npc_behavior,
            }

    # ------------------------------------------------------------------
    # Weather Forecasting
    # ------------------------------------------------------------------

    def predict_weather(self, forecast_seconds: float) -> List[WeatherCondition]:
        """Generate a probabilistic weather forecast.

        Predicts a sequence of weather conditions over the specified time
        horizon. Uses the current weather as the starting point and
        probabilistically transitions through the weather graph based on
        seasonal weights, generating a new WeatherCondition at each change.

        Args:
            forecast_seconds: How far into the future to forecast.

        Returns:
            List of WeatherCondition predictions in chronological order.
        """
        forecast_seconds = max(1.0, forecast_seconds)
        with self._lock:
            current = self._current_weather
            predictions: List[WeatherCondition] = []
            time_remaining = forecast_seconds
            current_wt = current.weather_type

            # Start with current weather
            first_duration = min(current.duration, time_remaining) if current.duration > 0 else 120.0
            first_duration = min(first_duration, time_remaining)
            predictions.append(WeatherCondition(
                weather_type=current_wt,
                intensity=current.intensity,
                temperature=current.temperature,
                humidity=current.humidity,
                wind_speed=current.wind_speed,
                wind_direction=current.wind_direction,
                visibility=current.visibility,
                particle_density=current.particle_density,
                duration=first_duration,
                transition_time=0.0,
            ))
            time_remaining -= first_duration

            # Generate subsequent weather changes
            max_steps = 20
            step = 0
            while time_remaining > 0 and step < max_steps:
                step += 1

                candidates = _WEATHER_TRANSITIONS.get(current_wt, [WeatherType.CLEAR])
                season_weights = _SEASON_WEIGHTS.get(self._season, {})

                # Weight candidates by season
                weighted: List[Tuple[WeatherType, float]] = []
                for wt_candidate in candidates:
                    w = season_weights.get(wt_candidate, 0.02)
                    weighted.append((wt_candidate, max(0.01, w)))

                if not weighted:
                    break

                weathers, weights = zip(*weighted)
                total_w = sum(weights)
                normalized = [w / total_w for w in weights]
                next_wt = random.choices(weathers, weights=normalized, k=1)[0]

                # Duration for this forecast step
                step_duration = random.uniform(60.0, min(600.0, time_remaining))
                step_duration = min(step_duration, time_remaining)

                intensity = random.choices(
                    list(WeatherIntensity),
                    weights=[0.15, 0.40, 0.30, 0.15],
                    k=1,
                )[0]

                preset = _WEATHER_PRESETS.get(next_wt,
                                              _WEATHER_PRESETS[WeatherType.CLEAR])
                intensity_mult = _INTENSITY_MULTIPLIERS.get(intensity, 0.70)

                predictions.append(WeatherCondition(
                    weather_type=next_wt,
                    intensity=intensity,
                    temperature=preset["temperature"],
                    humidity=preset["humidity"],
                    wind_speed=preset["wind_speed"] * intensity_mult,
                    wind_direction=preset["wind_direction"],
                    visibility=preset["visibility"],
                    particle_density=preset["particle_density"] * intensity_mult,
                    duration=step_duration,
                    transition_time=random.uniform(3.0, 15.0),
                ))

                time_remaining -= step_duration
                current_wt = next_wt

            return predictions

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the weather simulation.

        Returns:
            Dictionary with current weather summary, day/night state,
            transition info, effect counts, and historical data.
        """
        with self._lock:
            current = self._current_weather
            is_transitioning = (
                self._transition_from is not None
                and self._transition_to is not None
            )

            transition_info: Dict[str, Any] = {}
            if is_transitioning and self._transition_to is not None:
                elapsed = self._total_elapsed - self._transition_start
                progress = min(1.0, elapsed / self._transition_duration)
                transition_info = {
                    "active": True,
                    "from": self._transition_from.weather_type.value if self._transition_from else None,
                    "to": self._transition_to.weather_type.value,
                    "progress": round(progress, 3),
                    "remaining_seconds": round(
                        max(0.0, self._transition_duration - elapsed), 2,
                    ),
                }
            else:
                transition_info = {"active": False}

            effects_by_type: Dict[str, int] = {}
            for effect in self._effects.values():
                key = effect.weather_type.value
                effects_by_type[key] = effects_by_type.get(key, 0) + 1

            recent_history = [
                {
                    "weather_type": h.weather_type.value,
                    "intensity": h.intensity.value,
                    "temperature": h.temperature,
                }
                for h in list(self._weather_history)[-10:]
            ]

            active_events = [
                ev.to_dict() for ev in self._events
                if ev.status == EventStatus.ACTIVE
            ]

            return {
                "current_weather": current.to_dict(),
                "day_night": self._day_night.to_dict(),
                "season": self._season.value,
                "transition": transition_info,
                "total_transitions": self._total_transitions,
                "total_effects": len(self._effects),
                "effects_by_weather_type": effects_by_type,
                "regions": [r.to_dict() for r in self._regions.values()],
                "total_regions": len(self._regions),
                "active_influences": [i.to_dict() for i in self._influences.values()],
                "active_events": active_events,
                "total_events": len(active_events),
                "total_elapsed_seconds": round(self._total_elapsed, 2),
                "update_count": self._update_count,
                "recent_weather_history": recent_history,
            }


# ---------------------------------------------------------------------------
# Helper: Time Range Check
# ---------------------------------------------------------------------------

def _time_in_range(t: float, start: float, end: float,
                   cycle_length: float) -> bool:
    """Check if time t falls within [start, end] on a cyclic timeline.

    Handles the wrap-around case where start > end (e.g. midnight span).
    """
    t = t % cycle_length
    start = start % cycle_length
    end = end % cycle_length
    if start <= end:
        return start <= t <= end
    else:
        return t >= start or t <= end


# ---------------------------------------------------------------------------
# Global Accessor
# ---------------------------------------------------------------------------

def get_weather_system() -> WeatherSystemEngine:
    """Get the global WeatherSystemEngine singleton instance."""
    return WeatherSystemEngine()