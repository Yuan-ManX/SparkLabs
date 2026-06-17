"""
SparkLabs Engine - Dynamic Weather and Environment System

A runtime weather and environment simulation module for the AI-native game
engine. Manages weather patterns, day/night cycles, atmospheric effects,
particle-based weather rendering, and gameplay-impacting environmental
conditions with smooth transitions and probabilistic forecasting.

Architecture:
  WeatherSystemEngine (Singleton)
    |-- WeatherCondition   — current or predicted weather state snapshot
    |-- DayNightCycle      — diurnal cycle with ambient and sky parameters
    |-- WeatherEffect      — visual particle effect tied to weather types
    |-- WeatherIntensity   — severity scaling (LIGHT through EXTREME)
    |-- TimeOfDay          — discrete phase within the day/night cycle
    |-- Season             — seasonal modulation of weather probabilities

Usage:
    ws = get_weather_system()
    ws.set_weather(WeatherType.RAIN, WeatherIntensity.MODERATE, 120.0, 0.0)
    ws.set_day_night_cycle(86400.0, 21600.0, 64800.0)
    ws.advance_time(60.0)
    modifiers = ws.get_gameplay_modifiers()
"""

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
    ) -> WeatherCondition:
        """Immediately set the global weather condition.

        Cancels any active transition and applies the requested weather
        type with the given intensity immediately. Atmospheric parameters
        are drawn from preset defaults and scaled by the intensity level.

        Args:
            weather_type: The target weather type to apply.
            intensity: Severity level of the weather.
            duration: How long this weather persists in seconds (-1 = indefinite).
            transition_time: Not used for immediate set (kept for API symmetry).

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

    def get_current_weather(self) -> WeatherCondition:
        """Get the current effective weather condition.

        If a transition is active, returns an interpolated WeatherCondition
        between the origin and target. Otherwise returns the current
        weather directly.

        Returns:
            The active WeatherCondition, interpolated during transitions.
        """
        with self._lock:
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
        animates active weather transitions, and updates weather
        condition durations.

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

            return self._day_night

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
    # Gameplay Modifiers
    # ------------------------------------------------------------------

    def get_gameplay_modifiers(self) -> Dict[str, Any]:
        """Compute gameplay-impacting modifiers from current conditions.

        Derives movement speed adjustments, visibility penalties, damage
        modifiers, elemental bonuses, and NPC behavior hints based on the
        active weather, time of day, and season.

        Returns:
            Dictionary of gameplay modifier categories and their values.
        """
        with self._lock:
            weather = self._current_weather
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

            return {
                "current_weather": current.to_dict(),
                "day_night": self._day_night.to_dict(),
                "season": self._season.value,
                "transition": transition_info,
                "total_transitions": self._total_transitions,
                "total_effects": len(self._effects),
                "effects_by_weather_type": effects_by_type,
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