"""
SparkLabs Engine - Dynamic Weather Simulation System

A comprehensive dynamic weather simulation engine for the
AI-native game engine. Provides real-time weather rendering,
smooth transitions between weather states, particle-based
precipitation effects, atmospheric parameter blending, and
climate-driven seasonal forecasting.

Architecture:
  EngineWeatherSystem (Singleton)
    |-- WeatherController (current weather, transitions, intensity)
    |-- ClimateProfile (regional climate definitions)
    |-- ParticleSimulator (rain/snow/sandstorm particle effects)
    |-- AtmosphericEffects (fog, wind, lightning, rainbow)
    |-- WeatherForecast (predict weather changes)
    |-- VisualSettings (color grading, sky tint, ambient light per weather)

Weather States:
  CLEAR, CLOUDY, OVERCAST, LIGHT_RAIN, HEAVY_RAIN,
  THUNDERSTORM, LIGHT_SNOW, BLIZZARD, FOGGY, SANDSTORM,
  WINDY, HEATWAVE, RAINBOW

Key Features:
  - Smooth interpolation between weather states with configurable duration
  - Per-region climate profiles with seasonal probability tables
  - Rain drop, snow flake, and sand particle simulation with physics
  - Atmospheric effects: fog density, wind, lightning, rainbow conditions
  - Visual settings per weather: sky tint, ambient light, post-processing
  - Probability-based weather progression and forecast generation
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WeatherType(Enum):
    """All supported weather condition types."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    LIGHT_SNOW = "light_snow"
    BLIZZARD = "blizzard"
    FOGGY = "foggy"
    SANDSTORM = "sandstorm"
    WINDY = "windy"
    HEATWAVE = "heatwave"
    RAINBOW = "rainbow"


class WeatherIntensity(Enum):
    """Intensity level of the current weather condition."""
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    EXTREME = "extreme"


class WindDirection(Enum):
    """Compass direction of wind origin."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NE = "ne"
    NW = "nw"
    SE = "se"
    SW = "sw"
    NONE = "none"


class ClimateZone(Enum):
    """Geographic climate classification for regions."""
    TROPICAL = "tropical"
    TEMPERATE = "temperate"
    ARID = "arid"
    POLAR = "polar"
    MOUNTAIN = "mountain"
    COASTAL = "coastal"


class Season(Enum):
    """Calendar season for seasonal weather probability tables."""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class ParticleType(Enum):
    """Types of weather particles for rendering."""
    RAINDROP = "raindrop"
    SNOWFLAKE = "snowflake"
    SAND = "sand"
    LIGHTNING_BOLT = "lightning_bolt"
    HEAT_HAZE = "heat_haze"


# ---------------------------------------------------------------------------
# Visual Preset Constants
# ---------------------------------------------------------------------------

@dataclass
class VisualSettings:
    """Rendering parameters for a given weather condition.

    Contains color grading, sky tinting, ambient light levels,
    fog coloring, and post-processing parameters that the render
    pipeline uses when a weather type is active.
    """
    sky_tint_r: float = 1.0
    sky_tint_g: float = 1.0
    sky_tint_b: float = 1.0
    ambient_light: float = 1.0
    fog_color_r: float = 0.8
    fog_color_g: float = 0.8
    fog_color_b: float = 0.8
    cloud_opacity: float = 0.0
    sun_visibility: float = 1.0
    post_contrast: float = 1.0
    post_saturation: float = 1.0
    post_exposure: float = 1.0
    shadow_strength: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sky_tint": [self.sky_tint_r, self.sky_tint_g, self.sky_tint_b],
            "ambient_light": self.ambient_light,
            "fog_color": [self.fog_color_r, self.fog_color_g, self.fog_color_b],
            "cloud_opacity": self.cloud_opacity,
            "sun_visibility": self.sun_visibility,
            "post_contrast": self.post_contrast,
            "post_saturation": self.post_saturation,
            "post_exposure": self.post_exposure,
            "shadow_strength": self.shadow_strength,
        }

    def lerp(self, other: VisualSettings, t: float) -> VisualSettings:
        """Linearly interpolate between two visual settings by factor t."""
        t = max(0.0, min(1.0, t))
        return VisualSettings(
            sky_tint_r=self.sky_tint_r + (other.sky_tint_r - self.sky_tint_r) * t,
            sky_tint_g=self.sky_tint_g + (other.sky_tint_g - self.sky_tint_g) * t,
            sky_tint_b=self.sky_tint_b + (other.sky_tint_b - self.sky_tint_b) * t,
            ambient_light=self.ambient_light + (other.ambient_light - self.ambient_light) * t,
            fog_color_r=self.fog_color_r + (other.fog_color_r - self.fog_color_r) * t,
            fog_color_g=self.fog_color_g + (other.fog_color_g - self.fog_color_g) * t,
            fog_color_b=self.fog_color_b + (other.fog_color_b - self.fog_color_b) * t,
            cloud_opacity=self.cloud_opacity + (other.cloud_opacity - self.cloud_opacity) * t,
            sun_visibility=self.sun_visibility + (other.sun_visibility - self.sun_visibility) * t,
            post_contrast=self.post_contrast + (other.post_contrast - self.post_contrast) * t,
            post_saturation=self.post_saturation + (other.post_saturation - self.post_saturation) * t,
            post_exposure=self.post_exposure + (other.post_exposure - self.post_exposure) * t,
            shadow_strength=self.shadow_strength + (other.shadow_strength - self.shadow_strength) * t,
        )


# ---------------------------------------------------------------------------
# Default Visual Presets per Weather Type
# ---------------------------------------------------------------------------

DEFAULT_WEATHER_VISUALS: Dict[WeatherType, VisualSettings] = {
    WeatherType.CLEAR: VisualSettings(
        sky_tint_r=0.45, sky_tint_g=0.70, sky_tint_b=1.00,
        ambient_light=1.0, fog_color_r=0.85, fog_color_g=0.90, fog_color_b=1.00,
        cloud_opacity=0.05, sun_visibility=1.0,
        post_contrast=1.0, post_saturation=1.0, post_exposure=1.0, shadow_strength=1.0,
    ),
    WeatherType.CLOUDY: VisualSettings(
        sky_tint_r=0.70, sky_tint_g=0.70, sky_tint_b=0.75,
        ambient_light=0.85, fog_color_r=0.65, fog_color_g=0.65, fog_color_b=0.70,
        cloud_opacity=0.60, sun_visibility=0.50,
        post_contrast=0.95, post_saturation=0.85, post_exposure=0.95, shadow_strength=0.70,
    ),
    WeatherType.OVERCAST: VisualSettings(
        sky_tint_r=0.55, sky_tint_g=0.55, sky_tint_b=0.60,
        ambient_light=0.70, fog_color_r=0.50, fog_color_g=0.50, fog_color_b=0.55,
        cloud_opacity=0.90, sun_visibility=0.15,
        post_contrast=0.90, post_saturation=0.70, post_exposure=0.85, shadow_strength=0.50,
    ),
    WeatherType.LIGHT_RAIN: VisualSettings(
        sky_tint_r=0.50, sky_tint_g=0.55, sky_tint_b=0.65,
        ambient_light=0.80, fog_color_r=0.55, fog_color_g=0.60, fog_color_b=0.65,
        cloud_opacity=0.80, sun_visibility=0.35,
        post_contrast=0.92, post_saturation=0.80, post_exposure=0.90, shadow_strength=0.60,
    ),
    WeatherType.HEAVY_RAIN: VisualSettings(
        sky_tint_r=0.40, sky_tint_g=0.45, sky_tint_b=0.55,
        ambient_light=0.55, fog_color_r=0.40, fog_color_g=0.45, fog_color_b=0.50,
        cloud_opacity=0.95, sun_visibility=0.10,
        post_contrast=0.85, post_saturation=0.60, post_exposure=0.75, shadow_strength=0.40,
    ),
    WeatherType.THUNDERSTORM: VisualSettings(
        sky_tint_r=0.30, sky_tint_g=0.30, sky_tint_b=0.45,
        ambient_light=0.40, fog_color_r=0.30, fog_color_g=0.30, fog_color_b=0.45,
        cloud_opacity=1.0, sun_visibility=0.05,
        post_contrast=1.10, post_saturation=0.50, post_exposure=0.60, shadow_strength=1.20,
    ),
    WeatherType.LIGHT_SNOW: VisualSettings(
        sky_tint_r=0.75, sky_tint_g=0.80, sky_tint_b=0.90,
        ambient_light=0.90, fog_color_r=0.85, fog_color_g=0.88, fog_color_b=0.95,
        cloud_opacity=0.70, sun_visibility=0.55,
        post_contrast=0.95, post_saturation=0.70, post_exposure=1.05, shadow_strength=0.65,
    ),
    WeatherType.BLIZZARD: VisualSettings(
        sky_tint_r=0.80, sky_tint_g=0.82, sky_tint_b=0.88,
        ambient_light=0.50, fog_color_r=0.90, fog_color_g=0.92, fog_color_b=0.95,
        cloud_opacity=1.0, sun_visibility=0.05,
        post_contrast=0.85, post_saturation=0.40, post_exposure=1.15, shadow_strength=0.35,
    ),
    WeatherType.FOGGY: VisualSettings(
        sky_tint_r=0.70, sky_tint_g=0.72, sky_tint_b=0.78,
        ambient_light=0.75, fog_color_r=0.72, fog_color_g=0.75, fog_color_b=0.80,
        cloud_opacity=0.30, sun_visibility=0.40,
        post_contrast=0.80, post_saturation=0.55, post_exposure=0.90, shadow_strength=0.45,
    ),
    WeatherType.SANDSTORM: VisualSettings(
        sky_tint_r=0.90, sky_tint_g=0.70, sky_tint_b=0.35,
        ambient_light=0.55, fog_color_r=0.80, fog_color_g=0.60, fog_color_b=0.30,
        cloud_opacity=0.40, sun_visibility=0.20,
        post_contrast=0.75, post_saturation=0.85, post_exposure=0.80, shadow_strength=0.40,
    ),
    WeatherType.WINDY: VisualSettings(
        sky_tint_r=0.55, sky_tint_g=0.70, sky_tint_b=0.90,
        ambient_light=0.95, fog_color_r=0.75, fog_color_g=0.80, fog_color_b=0.90,
        cloud_opacity=0.30, sun_visibility=0.80,
        post_contrast=1.05, post_saturation=0.95, post_exposure=1.02, shadow_strength=0.90,
    ),
    WeatherType.HEATWAVE: VisualSettings(
        sky_tint_r=1.00, sky_tint_g=0.85, sky_tint_b=0.30,
        ambient_light=1.20, fog_color_r=0.90, fog_color_g=0.80, fog_color_b=0.40,
        cloud_opacity=0.01, sun_visibility=1.0,
        post_contrast=1.10, post_saturation=1.15, post_exposure=1.25, shadow_strength=0.70,
    ),
    WeatherType.RAINBOW: VisualSettings(
        sky_tint_r=0.50, sky_tint_g=0.72, sky_tint_b=1.00,
        ambient_light=1.05, fog_color_r=0.80, fog_color_g=0.85, fog_color_b=1.00,
        cloud_opacity=0.40, sun_visibility=0.85,
        post_contrast=1.05, post_saturation=1.20, post_exposure=1.05, shadow_strength=0.85,
    ),
}


# ---------------------------------------------------------------------------
# Atmospheric Presets per Weather Type
# ---------------------------------------------------------------------------

DEFAULT_ATMOSPHERIC_PRESETS: Dict[WeatherType, Dict[str, Any]] = {
    WeatherType.CLEAR: {
        "temperature": 22.0, "humidity": 0.30, "pressure": 1013.0,
        "wind_speed": 0.05, "fog_density": 0.0, "lightning_chance": 0.0,
        "precipitation_intensity": 0.0, "cloud_coverage": 0.05,
    },
    WeatherType.CLOUDY: {
        "temperature": 18.0, "humidity": 0.55, "pressure": 1010.0,
        "wind_speed": 0.15, "fog_density": 0.05, "lightning_chance": 0.0,
        "precipitation_intensity": 0.0, "cloud_coverage": 0.55,
    },
    WeatherType.OVERCAST: {
        "temperature": 16.0, "humidity": 0.70, "pressure": 1008.0,
        "wind_speed": 0.20, "fog_density": 0.10, "lightning_chance": 0.02,
        "precipitation_intensity": 0.05, "cloud_coverage": 0.85,
    },
    WeatherType.LIGHT_RAIN: {
        "temperature": 15.0, "humidity": 0.85, "pressure": 1005.0,
        "wind_speed": 0.25, "fog_density": 0.20, "lightning_chance": 0.05,
        "precipitation_intensity": 0.35, "cloud_coverage": 0.80,
    },
    WeatherType.HEAVY_RAIN: {
        "temperature": 13.0, "humidity": 0.95, "pressure": 1000.0,
        "wind_speed": 0.35, "fog_density": 0.30, "lightning_chance": 0.10,
        "precipitation_intensity": 0.75, "cloud_coverage": 0.90,
    },
    WeatherType.THUNDERSTORM: {
        "temperature": 12.0, "humidity": 1.00, "pressure": 995.0,
        "wind_speed": 0.60, "fog_density": 0.25, "lightning_chance": 0.50,
        "precipitation_intensity": 0.90, "cloud_coverage": 1.00,
    },
    WeatherType.LIGHT_SNOW: {
        "temperature": -2.0, "humidity": 0.65, "pressure": 1015.0,
        "wind_speed": 0.15, "fog_density": 0.10, "lightning_chance": 0.0,
        "precipitation_intensity": 0.25, "cloud_coverage": 0.65,
    },
    WeatherType.BLIZZARD: {
        "temperature": -12.0, "humidity": 0.90, "pressure": 1020.0,
        "wind_speed": 0.75, "fog_density": 0.40, "lightning_chance": 0.03,
        "precipitation_intensity": 0.85, "cloud_coverage": 1.00,
    },
    WeatherType.FOGGY: {
        "temperature": 14.0, "humidity": 0.95, "pressure": 1012.0,
        "wind_speed": 0.03, "fog_density": 0.80, "lightning_chance": 0.0,
        "precipitation_intensity": 0.0, "cloud_coverage": 0.20,
    },
    WeatherType.SANDSTORM: {
        "temperature": 36.0, "humidity": 0.05, "pressure": 1005.0,
        "wind_speed": 0.70, "fog_density": 0.60, "lightning_chance": 0.0,
        "precipitation_intensity": 0.0, "cloud_coverage": 0.30,
    },
    WeatherType.WINDY: {
        "temperature": 17.0, "humidity": 0.40, "pressure": 1010.0,
        "wind_speed": 0.55, "fog_density": 0.05, "lightning_chance": 0.0,
        "precipitation_intensity": 0.0, "cloud_coverage": 0.20,
    },
    WeatherType.HEATWAVE: {
        "temperature": 38.0, "humidity": 0.15, "pressure": 1015.0,
        "wind_speed": 0.08, "fog_density": 0.02, "lightning_chance": 0.0,
        "precipitation_intensity": 0.0, "cloud_coverage": 0.02,
    },
    WeatherType.RAINBOW: {
        "temperature": 20.0, "humidity": 0.60, "pressure": 1012.0,
        "wind_speed": 0.08, "fog_density": 0.05, "lightning_chance": 0.0,
        "precipitation_intensity": 0.05, "cloud_coverage": 0.35,
    },
}


# ---------------------------------------------------------------------------
# Weather Transition Graph
# ---------------------------------------------------------------------------

WEATHER_TRANSITION_GRAPH: Dict[WeatherType, List[WeatherType]] = {
    WeatherType.CLEAR: [WeatherType.CLOUDY, WeatherType.FOGGY, WeatherType.WINDY, WeatherType.HEATWAVE, WeatherType.RAINBOW],
    WeatherType.CLOUDY: [WeatherType.CLEAR, WeatherType.OVERCAST, WeatherType.LIGHT_RAIN, WeatherType.LIGHT_SNOW, WeatherType.FOGGY, WeatherType.WINDY],
    WeatherType.OVERCAST: [WeatherType.CLOUDY, WeatherType.LIGHT_RAIN, WeatherType.HEAVY_RAIN, WeatherType.LIGHT_SNOW, WeatherType.FOGGY],
    WeatherType.LIGHT_RAIN: [WeatherType.CLOUDY, WeatherType.OVERCAST, WeatherType.HEAVY_RAIN, WeatherType.THUNDERSTORM, WeatherType.RAINBOW],
    WeatherType.HEAVY_RAIN: [WeatherType.LIGHT_RAIN, WeatherType.THUNDERSTORM, WeatherType.OVERCAST],
    WeatherType.THUNDERSTORM: [WeatherType.HEAVY_RAIN, WeatherType.LIGHT_RAIN, WeatherType.OVERCAST],
    WeatherType.LIGHT_SNOW: [WeatherType.CLOUDY, WeatherType.OVERCAST, WeatherType.BLIZZARD],
    WeatherType.BLIZZARD: [WeatherType.LIGHT_SNOW, WeatherType.OVERCAST],
    WeatherType.FOGGY: [WeatherType.CLEAR, WeatherType.CLOUDY, WeatherType.OVERCAST],
    WeatherType.SANDSTORM: [WeatherType.CLEAR, WeatherType.WINDY],
    WeatherType.WINDY: [WeatherType.CLEAR, WeatherType.CLOUDY, WeatherType.SANDSTORM],
    WeatherType.HEATWAVE: [WeatherType.CLEAR, WeatherType.CLOUDY],
    WeatherType.RAINBOW: [WeatherType.CLEAR, WeatherType.CLOUDY, WeatherType.LIGHT_RAIN],
}


# ---------------------------------------------------------------------------
# Default Seasonal Weights per Climate Zone
# ---------------------------------------------------------------------------

def _build_default_seasonal_weights(
    weights: Dict[Season, Dict[WeatherType, float]],
) -> Dict[Season, Dict[WeatherType, float]]:
    """Normalize seasonal weights so each season's weights sum to 1.0."""
    normalized: Dict[Season, Dict[WeatherType, float]] = {}
    for season, weather_map in weights.items():
        total = sum(weather_map.values())
        if total > 0:
            normalized[season] = {w: v / total for w, v in weather_map.items()}
        else:
            normalized[season] = {WeatherType.CLEAR: 1.0}
    return normalized


DEFAULT_CLIMATE_WEIGHTS: Dict[ClimateZone, Dict[Season, Dict[WeatherType, float]]] = {
    ClimateZone.TROPICAL: _build_default_seasonal_weights({
        Season.SPRING: {WeatherType.CLEAR: 0.30, WeatherType.CLOUDY: 0.20, WeatherType.LIGHT_RAIN: 0.25, WeatherType.HEAVY_RAIN: 0.15, WeatherType.THUNDERSTORM: 0.10},
        Season.SUMMER: {WeatherType.CLEAR: 0.25, WeatherType.CLOUDY: 0.15, WeatherType.LIGHT_RAIN: 0.15, WeatherType.HEAVY_RAIN: 0.15, WeatherType.THUNDERSTORM: 0.20, WeatherType.HEATWAVE: 0.10},
        Season.AUTUMN: {WeatherType.CLEAR: 0.30, WeatherType.CLOUDY: 0.20, WeatherType.LIGHT_RAIN: 0.25, WeatherType.HEAVY_RAIN: 0.15, WeatherType.THUNDERSTORM: 0.10},
        Season.WINTER: {WeatherType.CLEAR: 0.35, WeatherType.CLOUDY: 0.30, WeatherType.LIGHT_RAIN: 0.20, WeatherType.OVERCAST: 0.15},
    }),
    ClimateZone.TEMPERATE: _build_default_seasonal_weights({
        Season.SPRING: {WeatherType.CLEAR: 0.25, WeatherType.CLOUDY: 0.20, WeatherType.OVERCAST: 0.15, WeatherType.LIGHT_RAIN: 0.20, WeatherType.HEAVY_RAIN: 0.10, WeatherType.WINDY: 0.05, WeatherType.RAINBOW: 0.05},
        Season.SUMMER: {WeatherType.CLEAR: 0.40, WeatherType.CLOUDY: 0.20, WeatherType.LIGHT_RAIN: 0.10, WeatherType.THUNDERSTORM: 0.10, WeatherType.WINDY: 0.10, WeatherType.HEATWAVE: 0.10},
        Season.AUTUMN: {WeatherType.CLEAR: 0.20, WeatherType.CLOUDY: 0.20, WeatherType.OVERCAST: 0.20, WeatherType.LIGHT_RAIN: 0.15, WeatherType.WINDY: 0.15, WeatherType.FOGGY: 0.10},
        Season.WINTER: {WeatherType.CLOUDY: 0.20, WeatherType.OVERCAST: 0.20, WeatherType.LIGHT_SNOW: 0.25, WeatherType.BLIZZARD: 0.15, WeatherType.CLEAR: 0.15, WeatherType.FOGGY: 0.05},
    }),
    ClimateZone.ARID: _build_default_seasonal_weights({
        Season.SPRING: {WeatherType.CLEAR: 0.55, WeatherType.WINDY: 0.25, WeatherType.SANDSTORM: 0.10, WeatherType.CLOUDY: 0.10},
        Season.SUMMER: {WeatherType.CLEAR: 0.25, WeatherType.HEATWAVE: 0.35, WeatherType.SANDSTORM: 0.20, WeatherType.WINDY: 0.15, WeatherType.CLOUDY: 0.05},
        Season.AUTUMN: {WeatherType.CLEAR: 0.45, WeatherType.WINDY: 0.25, WeatherType.SANDSTORM: 0.15, WeatherType.CLOUDY: 0.15},
        Season.WINTER: {WeatherType.CLEAR: 0.60, WeatherType.CLOUDY: 0.20, WeatherType.WINDY: 0.15, WeatherType.LIGHT_RAIN: 0.05},
    }),
    ClimateZone.POLAR: _build_default_seasonal_weights({
        Season.SPRING: {WeatherType.LIGHT_SNOW: 0.30, WeatherType.CLEAR: 0.20, WeatherType.CLOUDY: 0.20, WeatherType.OVERCAST: 0.15, WeatherType.WINDY: 0.15},
        Season.SUMMER: {WeatherType.CLEAR: 0.25, WeatherType.CLOUDY: 0.25, WeatherType.LIGHT_SNOW: 0.20, WeatherType.OVERCAST: 0.15, WeatherType.FOGGY: 0.15},
        Season.AUTUMN: {WeatherType.LIGHT_SNOW: 0.30, WeatherType.OVERCAST: 0.25, WeatherType.CLOUDY: 0.20, WeatherType.WINDY: 0.15, WeatherType.CLEAR: 0.10},
        Season.WINTER: {WeatherType.BLIZZARD: 0.40, WeatherType.LIGHT_SNOW: 0.35, WeatherType.OVERCAST: 0.15, WeatherType.CLOUDY: 0.10},
    }),
    ClimateZone.MOUNTAIN: _build_default_seasonal_weights({
        Season.SPRING: {WeatherType.CLEAR: 0.30, WeatherType.CLOUDY: 0.20, WeatherType.LIGHT_RAIN: 0.15, WeatherType.WINDY: 0.20, WeatherType.FOGGY: 0.15},
        Season.SUMMER: {WeatherType.CLEAR: 0.35, WeatherType.CLOUDY: 0.20, WeatherType.THUNDERSTORM: 0.20, WeatherType.LIGHT_RAIN: 0.15, WeatherType.WINDY: 0.10},
        Season.AUTUMN: {WeatherType.CLOUDY: 0.25, WeatherType.OVERCAST: 0.20, WeatherType.LIGHT_RAIN: 0.20, WeatherType.FOGGY: 0.15, WeatherType.WINDY: 0.20},
        Season.WINTER: {WeatherType.LIGHT_SNOW: 0.30, WeatherType.BLIZZARD: 0.25, WeatherType.CLOUDY: 0.20, WeatherType.OVERCAST: 0.15, WeatherType.CLEAR: 0.10},
    }),
    ClimateZone.COASTAL: _build_default_seasonal_weights({
        Season.SPRING: {WeatherType.CLEAR: 0.30, WeatherType.CLOUDY: 0.20, WeatherType.LIGHT_RAIN: 0.15, WeatherType.WINDY: 0.20, WeatherType.FOGGY: 0.15},
        Season.SUMMER: {WeatherType.CLEAR: 0.40, WeatherType.CLOUDY: 0.20, WeatherType.WINDY: 0.20, WeatherType.LIGHT_RAIN: 0.10, WeatherType.RAINBOW: 0.10},
        Season.AUTUMN: {WeatherType.CLOUDY: 0.20, WeatherType.OVERCAST: 0.20, WeatherType.WINDY: 0.25, WeatherType.LIGHT_RAIN: 0.20, WeatherType.FOGGY: 0.15},
        Season.WINTER: {WeatherType.CLOUDY: 0.25, WeatherType.OVERCAST: 0.20, WeatherType.LIGHT_RAIN: 0.20, WeatherType.WINDY: 0.20, WeatherType.CLEAR: 0.15},
    }),
}


# ---------------------------------------------------------------------------
# Particle Emission Configurations
# ---------------------------------------------------------------------------

PARTICLE_EMISSION_RATES: Dict[WeatherType, Tuple[int, int]] = {
    WeatherType.LIGHT_RAIN: (20, 50),
    WeatherType.HEAVY_RAIN: (80, 150),
    WeatherType.THUNDERSTORM: (100, 200),
    WeatherType.LIGHT_SNOW: (10, 30),
    WeatherType.BLIZZARD: (60, 120),
    WeatherType.SANDSTORM: (40, 80),
}

_PARTICLE_MAX_COUNT: Dict[WeatherType, int] = {
    WeatherType.LIGHT_RAIN: 300,
    WeatherType.HEAVY_RAIN: 800,
    WeatherType.THUNDERSTORM: 1000,
    WeatherType.LIGHT_SNOW: 300,
    WeatherType.BLIZZARD: 600,
    WeatherType.SANDSTORM: 400,
}

PARTICLE_LIFETIME_RANGE: Dict[WeatherType, Tuple[float, float]] = {
    WeatherType.LIGHT_RAIN: (0.5, 1.5),
    WeatherType.HEAVY_RAIN: (0.3, 1.0),
    WeatherType.THUNDERSTORM: (0.2, 0.8),
    WeatherType.LIGHT_SNOW: (2.0, 6.0),
    WeatherType.BLIZZARD: (1.0, 4.0),
    WeatherType.SANDSTORM: (0.5, 2.0),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WeatherState:
    """Current weather state for a specific region.

    Tracks the active weather type, intensity, and transition
    parameters for smooth interpolation between weather conditions.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    weather_type: WeatherType = WeatherType.CLEAR
    intensity: WeatherIntensity = WeatherIntensity.NONE
    transition_progress: float = 1.0
    started_at: float = field(default_factory=_time_module.time)
    duration: float = -1.0
    target_weather: Optional[WeatherType] = None
    wind_speed: float = 0.05
    wind_direction: WindDirection = WindDirection.NONE
    temperature: float = 22.0
    humidity: float = 0.30
    pressure: float = 1013.0
    fog_density: float = 0.0
    lightning_chance: float = 0.0
    particle_count: int = 0
    cloud_coverage: float = 0.05
    precipitation_intensity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "weather_type": self.weather_type.value if hasattr(self.weather_type, 'value') else self.weather_type,
            "intensity": self.intensity.value if hasattr(self.intensity, 'value') else self.intensity,
            "transition_progress": self.transition_progress,
            "started_at": self.started_at,
            "duration": self.duration,
            "target_weather": self.target_weather.value if hasattr(self.target_weather, 'value') else self.target_weather if self.target_weather else None,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction.value if hasattr(self.wind_direction, 'value') else self.wind_direction,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "fog_density": self.fog_density,
            "lightning_chance": self.lightning_chance,
            "particle_count": self.particle_count,
            "cloud_coverage": self.cloud_coverage,
            "precipitation_intensity": self.precipitation_intensity,
        }


@dataclass
class ClimateProfile:
    """Regional climate definition with seasonal weather probabilities.

    Defines the weather behavior for a geographic region including
    baseline temperature, humidity, and wind ranges, along with
    per-season probability tables for each weather type.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Default Climate"
    climate_zone: ClimateZone = ClimateZone.TEMPERATE
    seasonal_weights: Dict[Season, Dict[WeatherType, float]] = field(default_factory=dict)
    base_temperature: float = 20.0
    temperature_range: float = 15.0
    humidity_range: float = 0.50
    wind_range: float = 0.30
    min_transition_ms: float = 3000.0
    max_transition_ms: float = 15000.0
    auto_progress_chance: float = 0.03

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "climate_zone": self.climate_zone.value,
            "seasonal_weights": {
                season.value: {wt.value: w for wt, w in weathers.items()}
                for season, weathers in self.seasonal_weights.items()
            },
            "base_temperature": self.base_temperature,
            "temperature_range": self.temperature_range,
            "humidity_range": self.humidity_range,
            "wind_range": self.wind_range,
            "min_transition_ms": self.min_transition_ms,
            "max_transition_ms": self.max_transition_ms,
            "auto_progress_chance": self.auto_progress_chance,
        }


@dataclass
class WeatherParticle:
    """An individual weather particle (raindrop, snowflake, sand grain).

    Tracks position, velocity, lifetime, and visual properties for
    per-particle rendering and physics-based motion simulation.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    particle_type: ParticleType = ParticleType.RAINDROP
    x: float = 0.0
    y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    lifetime: float = 1.0
    max_lifetime: float = 1.0
    size: float = 1.0
    opacity: float = 1.0
    rotation: float = 0.0
    wind_affected: bool = True
    flutter_phase: float = 0.0
    flutter_amplitude: float = 0.0
    flutter_frequency: float = 0.0

    @property
    def is_alive(self) -> bool:
        """Whether this particle is still active (lifetime > 0)."""
        return self.lifetime > 0.0

    @property
    def life_ratio(self) -> float:
        """Remaining lifetime as a ratio of max lifetime (0=dead, 1=full)."""
        if self.max_lifetime <= 0:
            return 0.0
        return max(0.0, self.lifetime / self.max_lifetime)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "particle_type": self.particle_type.value,
            "x": self.x,
            "y": self.y,
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
            "lifetime": self.lifetime,
            "max_lifetime": self.max_lifetime,
            "size": self.size,
            "opacity": self.opacity,
            "rotation": self.rotation,
            "wind_affected": self.wind_affected,
            "is_alive": self.is_alive,
        }


@dataclass
class WeatherTransition:
    """Tracks a smooth weather transition between two weather types.

    Handles interpolation progress from the source weather to the
    target weather over a configurable duration.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_weather: WeatherType = WeatherType.CLEAR
    to_weather: WeatherType = WeatherType.CLOUDY
    progress: float = 0.0
    duration_ms: float = 5000.0
    started_at: float = field(default_factory=_time_module.time)
    completed: bool = False

    @property
    def elapsed_ms(self) -> float:
        """Milliseconds elapsed since transition started."""
        return (_time_module.time() - self.started_at) * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_weather": self.from_weather.value,
            "to_weather": self.to_weather.value,
            "progress": self.progress,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "completed": self.completed,
            "elapsed_ms": round(self.elapsed_ms, 1),
        }


@dataclass
class WeatherForecast:
    """Predicted future weather state with confidence and alternatives.

    Provides probabilistic forecasting of upcoming weather changes
    based on climate profile data and current weather conditions.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    predicted_weather: WeatherType = WeatherType.CLEAR
    confidence: float = 0.5
    time_to_change_ticks: int = 10000
    alternative_weathers: List[WeatherType] = field(default_factory=list)
    issued_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "predicted_weather": self.predicted_weather.value,
            "confidence": self.confidence,
            "time_to_change_ticks": self.time_to_change_ticks,
            "alternative_weathers": [w.value for w in self.alternative_weathers],
            "issued_at": self.issued_at,
        }


# ---------------------------------------------------------------------------
# Wind Direction Vector Map
# ---------------------------------------------------------------------------

_WIND_DIRECTION_VECTORS: Dict[WindDirection, Tuple[float, float]] = {
    WindDirection.NORTH: (0.0, -1.0),
    WindDirection.SOUTH: (0.0, 1.0),
    WindDirection.EAST: (1.0, 0.0),
    WindDirection.WEST: (-1.0, 0.0),
    WindDirection.NE: (0.7071, -0.7071),
    WindDirection.NW: (-0.7071, -0.7071),
    WindDirection.SE: (0.7071, 0.7071),
    WindDirection.SW: (-0.7071, 0.7071),
    WindDirection.NONE: (0.0, 0.0),
}


# ---------------------------------------------------------------------------
# Intensity to Precipitation Multiplier
# ---------------------------------------------------------------------------

_INTENSITY_PRECIPITATION_MULT: Dict[WeatherIntensity, float] = {
    WeatherIntensity.NONE: 0.0,
    WeatherIntensity.LIGHT: 0.35,
    WeatherIntensity.MODERATE: 0.65,
    WeatherIntensity.HEAVY: 0.85,
    WeatherIntensity.EXTREME: 1.0,
}


# ---------------------------------------------------------------------------
# Season Determination
# ---------------------------------------------------------------------------

def _get_season_for_timestamp(timestamp: float) -> Season:
    """Map a UNIX timestamp to a season (Northern Hemisphere).

    Uses a simple month-based approach:
      - Spring: March-May (months 3-5)
      - Summer: June-August (months 6-8)
      - Autumn: September-November (months 9-11)
      - Winter: December-February (months 12, 1, 2)
    """
    month = (_time_module.gmtime(timestamp).tm_mon) - 1  # 0-based
    # Adjust: Jan/Feb are winter, Mar-May spring, etc.
    # Northern hemisphere standard
    seasonal_index = ((month + 1) % 12) // 3  # 0=winter(JFM), 1=spring(AMJ), 2=summer(JAS), 3=autumn(OND)

    # Actually, let's use the correct formula:
    # month 0=Jan..11=Dec -> season: spring=2,3,4; summer=5,6,7; autumn=8,9,10; winter=11,0,1
    if month in (2, 3, 4):
        return Season.SPRING
    elif month in (5, 6, 7):
        return Season.SUMMER
    elif month in (8, 9, 10):
        return Season.AUTUMN
    else:
        return Season.WINTER  # months 11, 0, 1


# ---------------------------------------------------------------------------
# Main Singleton Class
# ---------------------------------------------------------------------------

class EngineWeatherSystem:
    """
    Dynamic weather simulation engine for the SparkLabs AI-native game engine.

    Manages per-region weather state, smooth transitions between weather
    types, particle-based precipitation rendering, atmospheric parameter
    blending, seasonal climate profiles, and forecast generation.

    Usage:
        weather_sys = EngineWeatherSystem()
        weather_sys.set_climate_profile("forest_01", temperate_forest_profile)
        weather_sys.update(delta_time_ms)
        particles = weather_sys.get_particles("forest_01")
        visuals = weather_sys.get_visual_settings("forest_01")
    """

    _instance: Optional["EngineWeatherSystem"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EngineWeatherSystem":
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

        # Region-level weather state
        self._weather_states: Dict[str, WeatherState] = {}
        # Climate profiles assigned to regions
        self._climate_profiles: Dict[str, ClimateProfile] = {}
        # Active weather transitions per region
        self._transitions: Dict[str, WeatherTransition] = {}
        # Active particles per region
        self._particles: Dict[str, List[WeatherParticle]] = {}
        # Forecasts per region
        self._forecasts: Dict[str, WeatherForecast] = {}
        # Visual settings cache per region
        self._visual_cache: Dict[str, VisualSettings] = {}
        # Total simulation time in ms
        self._total_elapsed_ms: float = 0.0
        # Update counter
        self._update_count: int = 0
        # Simulation area width / height defaults for particle spawning
        self._simulation_width: float = 1920.0
        self._simulation_height: float = 1080.0

    # ------------------------------------------------------------------
    # Climate Profile Management
    # ------------------------------------------------------------------

    def set_climate_profile(self, region_id: str, profile: ClimateProfile) -> None:
        """Assign a climate profile to a region.

        Accepts both a ClimateProfile object and a string (climate zone name).
        If a string is provided, a default ClimateProfile is created for that zone.

        Initializes the region's weather state to CLEAR if this is the
        first time the region is registered.
        """
        # If a string is passed, create a default ClimateProfile from the zone name
        if isinstance(profile, str):
            try:
                zone = ClimateZone(profile)
            except ValueError:
                zone = ClimateZone.TEMPERATE
            profile = ClimateProfile(
                name=f"{profile.capitalize()} Climate",
                climate_zone=zone,
                seasonal_weights=dict(DEFAULT_CLIMATE_WEIGHTS.get(
                    zone, DEFAULT_CLIMATE_WEIGHTS[ClimateZone.TEMPERATE],
                )),
            )

        self._climate_profiles[region_id] = profile
        if region_id not in self._weather_states:
            self._weather_states[region_id] = self._build_weather_state(
                WeatherType.CLEAR, WeatherIntensity.NONE,
            )
            self._forecasts[region_id] = self._generate_forecast(
                region_id, WeatherType.CLEAR,
            )
            self._visual_cache[region_id] = DEFAULT_WEATHER_VISUALS[WeatherType.CLEAR]
            self._particles[region_id] = []

    @staticmethod
    def _build_weather_state(weather_type: WeatherType,
                             intensity: WeatherIntensity) -> WeatherState:
        """Build a new WeatherState from presets for the given type and intensity."""
        preset = DEFAULT_ATMOSPHERIC_PRESETS.get(
            weather_type, DEFAULT_ATMOSPHERIC_PRESETS[WeatherType.CLEAR],
        )
        intensity_mult = _INTENSITY_PRECIPITATION_MULT.get(intensity, 0.65)
        return WeatherState(
            weather_type=weather_type,
            intensity=intensity,
            transition_progress=1.0,
            started_at=_time_module.time(),
            wind_speed=preset.get("wind_speed", 0.05),
            temperature=preset.get("temperature", 22.0),
            humidity=preset.get("humidity", 0.30),
            pressure=preset.get("pressure", 1013.0),
            fog_density=preset.get("fog_density", 0.0),
            lightning_chance=preset.get("lightning_chance", 0.0),
            cloud_coverage=preset.get("cloud_coverage", 0.05),
            precipitation_intensity=(
                preset.get("precipitation_intensity", 0.0) * intensity_mult
            ),
        )

    def remove_region(self, region_id: str) -> bool:
        """Remove a region and all its weather data."""
        removed = False
        self._weather_states.pop(region_id, None) and (removed := True)  # type: ignore[func-returns-value]
        self._climate_profiles.pop(region_id, None)
        self._transitions.pop(region_id, None)
        self._particles.pop(region_id, None)
        self._forecasts.pop(region_id, None)
        self._visual_cache.pop(region_id, None)
        return removed

    # ------------------------------------------------------------------
    # Weather State Access
    # ------------------------------------------------------------------

    def get_current_weather(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get the current weather state for a region as a dictionary."""
        state = self._weather_states.get(region_id)
        if state is None:
            return None
        return state.to_dict()

    def get_weather_state(self, region_id: str) -> Optional[WeatherState]:
        """Get the raw WeatherState object for a region."""
        return self._weather_states.get(region_id)

    def set_weather(self, region_id: str, weather_type: WeatherType,
                    intensity: WeatherIntensity = WeatherIntensity.MODERATE,
                    **kwargs: Any) -> bool:
        """Manually set the weather for a region.

        Args:
            region_id: The region identifier.
            weather_type: The target weather type.
            intensity: The weather intensity level.
            **kwargs: Additional overrides (duration, wind_speed, etc.).

        Returns:
            True if the region was found and weather was set.
        """
        # Convert string to enum if needed
        if isinstance(weather_type, str):
            try:
                weather_type = WeatherType(weather_type)
            except ValueError:
                return False
        if isinstance(intensity, str):
            try:
                intensity = WeatherIntensity(intensity)
            except ValueError:
                intensity = WeatherIntensity.MODERATE

        state = self._weather_states.get(region_id)
        if state is None:
            return False

        # Cancel any active transition for this region
        self._transitions.pop(region_id, None)

        # Apply atmospheric defaults from presets
        preset = DEFAULT_ATMOSPHERIC_PRESETS.get(weather_type,
                                                  DEFAULT_ATMOSPHERIC_PRESETS[WeatherType.CLEAR])
        duration = kwargs.pop("duration", preset.get("duration", -1.0))

        # Build new weather state
        state.weather_type = weather_type
        state.intensity = intensity
        state.transition_progress = 1.0
        state.started_at = _time_module.time()
        state.duration = duration
        state.target_weather = None
        state.temperature = kwargs.pop("temperature", preset.get("temperature", 22.0))
        state.humidity = kwargs.pop("humidity", preset.get("humidity", 0.3))
        state.pressure = kwargs.pop("pressure", preset.get("pressure", 1013.0))
        state.wind_speed = kwargs.pop("wind_speed", preset.get("wind_speed", 0.05))
        state.fog_density = kwargs.pop("fog_density", preset.get("fog_density", 0.0))
        state.lightning_chance = kwargs.pop("lightning_chance", preset.get("lightning_chance", 0.0))
        state.cloud_coverage = kwargs.pop("cloud_coverage", preset.get("cloud_coverage", 0.05))
        state.precipitation_intensity = (
            _INTENSITY_PRECIPITATION_MULT.get(intensity, 0.65)
            * preset.get("precipitation_intensity", 0.0)
        )

        # Update particle count target based on weather
        max_count = _PARTICLE_MAX_COUNT.get(weather_type, 0)
        rate = PARTICLE_EMISSION_RATES.get(weather_type, (0, 0))
        state.particle_count = min(max_count, rate[1])

        # Update visual cache
        self._visual_cache[region_id] = DEFAULT_WEATHER_VISUALS.get(
            weather_type, VisualSettings(),
        )

        # Regenerate forecast
        self._forecasts[region_id] = self._generate_forecast(region_id, weather_type)

        # Clear particles on weather change
        self._particles[region_id] = []

        return True

    # ------------------------------------------------------------------
    # Weather Transitions
    # ------------------------------------------------------------------

    def transition_weather(self, region_id: str,
                           target_weather: WeatherType,
                           duration_ms: float = 5000.0) -> bool:
        """Initiate a smooth transition to a target weather type.

        The current weather parameters will be linearly interpolated
        toward the target weather's parameters over duration_ms.

        Args:
            region_id: The region identifier.
            target_weather: The weather type to transition to.
            duration_ms: Duration of the transition in milliseconds.

        Returns:
            True if the transition was started successfully.
        """
        state = self._weather_states.get(region_id)
        if state is None:
            return False

        # Don't transition to the same weather
        if state.weather_type == target_weather:
            return False

        # Cancel any existing transition
        self._transitions.pop(region_id, None)

        transition = WeatherTransition(
            from_weather=state.weather_type,
            to_weather=target_weather,
            progress=0.0,
            duration_ms=max(1.0, duration_ms),
            started_at=_time_module.time(),
            completed=False,
        )
        self._transitions[region_id] = transition

        # Mark the state as transitioning
        state.target_weather = target_weather
        state.transition_progress = 0.0

        return True

    # ------------------------------------------------------------------
    # Wind Control
    # ------------------------------------------------------------------

    def set_wind(self, region_id: str, speed: float,
                 direction: WindDirection) -> bool:
        """Set wind speed and direction for a region.

        Args:
            region_id: The region identifier.
            speed: Wind speed factor (0.0 to 1.0+).
            direction: Compass wind direction.

        Returns:
            True if the region was found.
        """
        state = self._weather_states.get(region_id)
        if state is None:
            return False
        state.wind_speed = max(0.0, speed)
        state.wind_direction = direction
        return True

    # ------------------------------------------------------------------
    # Atmospheric State
    # ------------------------------------------------------------------

    def get_atmospheric_state(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get the complete atmospheric state for a region.

        Returns a dictionary with temperature, humidity, pressure,
        fog density, wind speed, wind direction, lightning chance,
        cloud coverage, and precipitation intensity.
        """
        state = self._weather_states.get(region_id)
        if state is None:
            return None
        return {
            "temperature": state.temperature,
            "humidity": state.humidity,
            "pressure": state.pressure,
            "fog_density": state.fog_density,
            "wind_speed": state.wind_speed,
            "wind_direction": state.wind_direction.value if hasattr(state.wind_direction, 'value') else state.wind_direction,
            "wind_vector": _WIND_DIRECTION_VECTORS.get(state.wind_direction, (0.0, 0.0)),
            "lightning_chance": state.lightning_chance,
            "cloud_coverage": state.cloud_coverage,
            "precipitation_intensity": state.precipitation_intensity,
            "weather_type": state.weather_type.value if hasattr(state.weather_type, 'value') else state.weather_type,
            "intensity": state.intensity.value if hasattr(state.intensity, 'value') else state.intensity,
        }

    # ------------------------------------------------------------------
    # Visual Settings
    # ------------------------------------------------------------------

    def get_visual_settings(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get the current visual rendering parameters for a region.

        During a weather transition, visual settings are interpolated
        between the source and target weather presets.
        """
        state = self._weather_states.get(region_id)
        if state is None:
            return None

        transition = self._transitions.get(region_id)

        if transition is None or transition.completed:
            # No active transition; return cached or current visuals
            cached = self._visual_cache.get(region_id)
            if cached is None:
                cached = DEFAULT_WEATHER_VISUALS.get(
                    state.weather_type, VisualSettings(),
                )
                self._visual_cache[region_id] = cached
            return cached.to_dict()

        # Interpolate between from and to weather visuals
        from_visuals = DEFAULT_WEATHER_VISUALS.get(
            transition.from_weather, VisualSettings(),
        )
        to_visuals = DEFAULT_WEATHER_VISUALS.get(
            transition.to_weather, VisualSettings(),
        )
        progress = max(0.0, min(1.0, transition.progress))
        interpolated = from_visuals.lerp(to_visuals, progress)
        return interpolated.to_dict()

    # ------------------------------------------------------------------
    # Particle System
    # ------------------------------------------------------------------

    def get_particles(self, region_id: str) -> List[Dict[str, Any]]:
        """Get the list of active weather particles for a region.

        Returns a list of particle dictionaries for the rendering
        pipeline to draw rain, snow, sand, or other weather effects.
        """
        particles = self._particles.get(region_id, [])
        return [p.to_dict() for p in particles if p.is_alive]

    def _emit_particles(self, region_id: str, weather_type: WeatherType,
                        delta_seconds: float, wind_speed: float,
                        wind_dir: WindDirection) -> None:
        """Spawn new weather particles based on emission rates."""
        rate = PARTICLE_EMISSION_RATES.get(weather_type)
        if rate is None:
            return

        min_rate, max_rate = rate
        max_count = _PARTICLE_MAX_COUNT.get(weather_type, 0)
        current = self._particles.get(region_id, [])

        # Don't exceed max particle count
        alive_count = sum(1 for p in current if p.is_alive)
        if alive_count >= max_count:
            return

        # Calculate how many to spawn this frame
        to_spawn = int(random.uniform(min_rate, max_rate) * delta_seconds)
        can_spawn = min(to_spawn, max_count - alive_count)

        wind_vec = _WIND_DIRECTION_VECTORS.get(wind_dir, (0.0, 0.0))
        lifetime_range = PARTICLE_LIFETIME_RANGE.get(
            weather_type, (0.5, 1.5),
        )

        for _ in range(can_spawn):
            particle = self._create_particle(
                weather_type, wind_speed, wind_vec, lifetime_range,
            )
            current.append(particle)

    def _create_particle(self, weather_type: WeatherType,
                         wind_speed: float,
                         wind_vec: Tuple[float, float],
                         lifetime_range: Tuple[float, float]) -> WeatherParticle:
        """Create a single weather particle with appropriate physics."""
        x = random.uniform(0.0, self._simulation_width)
        y = random.uniform(-50.0, 0.0)  # Spawn above visible area

        max_life = random.uniform(lifetime_range[0], lifetime_range[1])

        if weather_type in (WeatherType.LIGHT_RAIN, WeatherType.HEAVY_RAIN,
                            WeatherType.THUNDERSTORM):
            return self._make_raindrop(x, y, wind_speed, wind_vec, max_life)
        elif weather_type in (WeatherType.LIGHT_SNOW, WeatherType.BLIZZARD):
            return self._make_snowflake(x, y, wind_speed, wind_vec, max_life)
        elif weather_type == WeatherType.SANDSTORM:
            return self._make_sand_particle(x, y, wind_speed, wind_vec, max_life)
        else:
            # Default fallback: slow raindrop
            return self._make_raindrop(x, y, wind_speed, wind_vec, max_life)

    @staticmethod
    def _make_raindrop(x: float, y: float, wind_speed: float,
                       wind_vec: Tuple[float, float],
                       max_life: float) -> WeatherParticle:
        """Create a raindrop particle with gravity-driven motion."""
        base_fall_speed = random.uniform(400.0, 700.0)
        wind_drift_x = wind_vec[0] * wind_speed * random.uniform(30.0, 80.0)
        wind_drift_y = wind_vec[1] * wind_speed * random.uniform(10.0, 30.0)
        return WeatherParticle(
            particle_type=ParticleType.RAINDROP,
            x=x, y=y,
            velocity_x=wind_drift_x,
            velocity_y=base_fall_speed + wind_drift_y,
            lifetime=max_life, max_lifetime=max_life,
            size=random.uniform(1.5, 3.5),
            opacity=random.uniform(0.6, 0.95),
            rotation=random.uniform(-0.3, 0.3),
            wind_affected=True,
        )

    @staticmethod
    def _make_snowflake(x: float, y: float, wind_speed: float,
                        wind_vec: Tuple[float, float],
                        max_life: float) -> WeatherParticle:
        """Create a snowflake particle with flutter and wind drift."""
        base_fall_speed = random.uniform(20.0, 60.0)
        wind_drift_x = wind_vec[0] * wind_speed * random.uniform(40.0, 120.0)
        wind_drift_y = wind_vec[1] * wind_speed * random.uniform(5.0, 15.0)
        return WeatherParticle(
            particle_type=ParticleType.SNOWFLAKE,
            x=x, y=y,
            velocity_x=wind_drift_x,
            velocity_y=base_fall_speed + wind_drift_y,
            lifetime=max_life, max_lifetime=max_life,
            size=random.uniform(2.0, 6.0),
            opacity=random.uniform(0.5, 0.9),
            rotation=random.uniform(0.0, math.pi * 2),
            wind_affected=True,
            flutter_phase=random.uniform(0.0, math.pi * 2),
            flutter_amplitude=random.uniform(0.8, 2.5),
            flutter_frequency=random.uniform(1.5, 4.0),
        )

    @staticmethod
    def _make_sand_particle(x: float, y: float, wind_speed: float,
                            wind_vec: Tuple[float, float],
                            max_life: float) -> WeatherParticle:
        """Create a sand particle for sandstorm effects."""
        base_speed = random.uniform(80.0, 200.0)
        wind_drift_x = wind_vec[0] * wind_speed * random.uniform(100.0, 250.0)
        wind_drift_y = wind_vec[1] * wind_speed * random.uniform(20.0, 80.0)
        return WeatherParticle(
            particle_type=ParticleType.SAND,
            x=x, y=y,
            velocity_x=base_speed * random.choice([-1.0, 1.0]) + wind_drift_x,
            velocity_y=wind_drift_y + random.uniform(-20.0, 10.0),
            lifetime=max_life, max_lifetime=max_life,
            size=random.uniform(1.0, 2.5),
            opacity=random.uniform(0.3, 0.7),
            rotation=random.uniform(0.0, math.pi * 2),
            wind_affected=True,
        )

    def _update_particles(self, region_id: str, delta_seconds: float) -> None:
        """Update all particles for a region: move, age, cull dead ones."""
        particles = self._particles.get(region_id, [])
        if not particles:
            return

        for p in particles:
            if not p.is_alive:
                continue

            # Advance lifetime
            p.lifetime -= delta_seconds

            # Update position
            if p.particle_type == ParticleType.SNOWFLAKE and p.wind_affected:
                # Apply flutter (sinusoidal horizontal oscillation)
                p.flutter_phase += p.flutter_frequency * delta_seconds
                flutter_offset = math.sin(p.flutter_phase) * p.flutter_amplitude
                p.x += (p.velocity_x + flutter_offset) * delta_seconds
                p.y += p.velocity_y * delta_seconds
                p.rotation += delta_seconds * 0.5
            else:
                p.x += p.velocity_x * delta_seconds
                p.y += p.velocity_y * delta_seconds
                if p.particle_type == ParticleType.RAINDROP:
                    p.rotation += delta_seconds * 0.2
                elif p.particle_type == ParticleType.SAND:
                    p.rotation += delta_seconds * 2.0

            # Fade out near end of life
            life_frac = p.life_ratio
            if life_frac < 0.3:
                p.opacity = p.opacity * life_frac / 0.3

        # Cull dead particles
        self._particles[region_id] = [p for p in particles if p.is_alive]

    # ------------------------------------------------------------------
    # Weather Forecast
    # ------------------------------------------------------------------

    def get_forecast(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get the current weather forecast for a region."""
        forecast = self._forecasts.get(region_id)
        if forecast is None:
            return None
        return forecast.to_dict()

    def _generate_forecast(self, region_id: str,
                           current_weather: WeatherType) -> WeatherForecast:
        """Generate a probabilistic weather forecast based on climate profile."""
        profile = self._climate_profiles.get(region_id)
        if profile is None:
            return WeatherForecast(
                predicted_weather=WeatherType.CLEAR,
                confidence=1.0,
                time_to_change_ticks=60000,
            )

        # Determine current season
        season = _get_season_for_timestamp(_time_module.time())

        # Get seasonal weights for this climate zone (fall back to global defaults)
        seasonal_weights = profile.seasonal_weights
        if not seasonal_weights:
            seasonal_weights = DEFAULT_CLIMATE_WEIGHTS.get(
                profile.climate_zone,
                DEFAULT_CLIMATE_WEIGHTS[ClimateZone.TEMPERATE],
            )

        season_weights = seasonal_weights.get(season, {WeatherType.CLEAR: 1.0})

        # Get possible transitions from current weather
        candidates = WEATHER_TRANSITION_GRAPH.get(current_weather,
                                                   [WeatherType.CLEAR])

        # Filter candidates to those with seasonal weights
        candidates_with_weights = [
            (w, season_weights.get(w, 0.0)) for w in candidates
        ]

        if not candidates_with_weights:
            return WeatherForecast(
                predicted_weather=current_weather,
                confidence=1.0,
                time_to_change_ticks=60000,
            )

        # Sort by weight descending
        candidates_with_weights.sort(key=lambda x: x[1], reverse=True)

        # Top candidate is the most likely
        predicted = candidates_with_weights[0][0]
        confidence = candidates_with_weights[0][1]

        # Normalize confidence against sum of all candidates
        total_weight = sum(w for _, w in candidates_with_weights)
        if total_weight > 0:
            confidence = candidates_with_weights[0][1] / total_weight

        # Alternatives are the other candidates
        alternatives = [w for w, _ in candidates_with_weights[1:4]]

        # Time to change: based on transition duration range
        base_ticks = (profile.min_transition_ms + profile.max_transition_ms) / 2
        variation = random.uniform(0.5, 2.0)
        time_ticks = int(base_ticks * variation)

        return WeatherForecast(
            predicted_weather=predicted,
            confidence=confidence,
            time_to_change_ticks=time_ticks,
            alternative_weathers=alternatives,
            issued_at=_time_module.time(),
        )

    # ------------------------------------------------------------------
    # Simulation Area Configuration
    # ------------------------------------------------------------------

    def set_simulation_area(self, width: float, height: float) -> None:
        """Set the simulation area dimensions for particle spawning."""
        self._simulation_width = max(1.0, width)
        self._simulation_height = max(1.0, height)

    # ------------------------------------------------------------------
    # Main Update Loop
    # ------------------------------------------------------------------

    def update(self, delta_time_ms: float) -> None:
        """Update the weather simulation for all regions.

        This method should be called every frame with the delta time
        in milliseconds. It advances transitions, interpolates weather
        parameters, emits and updates particles, regenerates forecasts,
        and performs probabilistic weather changes based on climate
        profiles.

        Args:
            delta_time_ms: Frame delta time in milliseconds.
        """
        delta_seconds = max(0.0, delta_time_ms / 1000.0)
        self._total_elapsed_ms += delta_time_ms
        self._update_count += 1

        for region_id, state in list(self._weather_states.items()):
            profile = self._climate_profiles.get(region_id)

            # --- Update active transition ---
            transition = self._transitions.get(region_id)
            if transition is not None and not transition.completed:
                # Advance transition progress
                if transition.duration_ms > 0:
                    progress_delta = delta_time_ms / transition.duration_ms
                    transition.progress = min(1.0, transition.progress + progress_delta)
                    state.transition_progress = transition.progress
                else:
                    transition.progress = 1.0
                    state.transition_progress = 1.0

                # Interpolate atmospheric parameters between from and to weather
                from_preset = DEFAULT_ATMOSPHERIC_PRESETS.get(
                    transition.from_weather,
                    DEFAULT_ATMOSPHERIC_PRESETS[WeatherType.CLEAR],
                )
                to_preset = DEFAULT_ATMOSPHERIC_PRESETS.get(
                    transition.to_weather,
                    DEFAULT_ATMOSPHERIC_PRESETS[WeatherType.CLEAR],
                )
                t = transition.progress
                # Smooth easing for more natural transitions
                t_eased = t * t * (3.0 - 2.0 * t)  # smoothstep

                for param in ("temperature", "humidity", "pressure",
                              "wind_speed", "fog_density", "lightning_chance",
                              "cloud_coverage"):
                    from_val = from_preset.get(param, 0.0)
                    to_val = to_preset.get(param, 0.0)
                    setattr(state, param, from_val + (to_val - from_val) * t_eased)

                # Precipitation intensity with intensity multiplier
                intensity_mult = _INTENSITY_PRECIPITATION_MULT.get(state.intensity, 0.65)
                from_precip = from_preset.get("precipitation_intensity", 0.0)
                to_precip = to_preset.get("precipitation_intensity", 0.0)
                state.precipitation_intensity = (
                    (from_precip + (to_precip - from_precip) * t_eased) * intensity_mult
                )

                # Check if transition complete
                if transition.progress >= 1.0:
                    transition.completed = True
                    state.weather_type = transition.to_weather
                    state.target_weather = None
                    state.started_at = _time_module.time()
                    state.transition_progress = 1.0

                    # Update visual cache
                    self._visual_cache[region_id] = DEFAULT_WEATHER_VISUALS.get(
                        transition.to_weather, VisualSettings(),
                    )

                    # Regenerate forecast
                    self._forecasts[region_id] = self._generate_forecast(
                        region_id, state.weather_type,
                    )

                    # Clear particles on transition complete
                    self._particles[region_id] = []

                    # Remove completed transition
                    del self._transitions[region_id]

            # --- Emit and update particles ---
            if state.weather_type in PARTICLE_EMISSION_RATES:
                wind_dir = state.wind_direction
                wind_speed = state.wind_speed
                self._emit_particles(
                    region_id, state.weather_type,
                    delta_seconds, wind_speed, wind_dir,
                )
            self._update_particles(region_id, delta_seconds)

            # --- Update particle count based on precipitation intensity ---
            max_particles = _PARTICLE_MAX_COUNT.get(state.weather_type, 0)
            current_count = sum(
                1 for p in self._particles.get(region_id, []) if p.is_alive
            )
            state.particle_count = current_count

            # --- Probabilistic auto weather progression ---
            if transition is None or transition.completed:
                if profile is not None and random.random() < profile.auto_progress_chance:
                    self._random_weather_progression(region_id, state)

            # --- Regenerate forecast if no transition active ---
            if transition is None:
                forecast = self._forecasts.get(region_id)
                if forecast is not None:
                    forecast.time_to_change_ticks = max(
                        0, forecast.time_to_change_ticks - int(delta_time_ms),
                    )
                    if forecast.time_to_change_ticks <= 0:
                        self._forecasts[region_id] = self._generate_forecast(
                            region_id, state.weather_type,
                        )

            # --- Natural temperature drift toward climate baseline ---
            if transition is None and profile is not None:
                drift_rate = 0.02 * delta_seconds
                state.temperature += (
                    profile.base_temperature - state.temperature
                ) * drift_rate

    def _random_weather_progression(self, region_id: str,
                                    state: WeatherState) -> None:
        """Attempt a probabilistic transition to a neighboring weather type."""
        profile = self._climate_profiles.get(region_id)
        if profile is None:
            return

        season = _get_season_for_timestamp(_time_module.time())
        seasonal_weights = profile.seasonal_weights
        if not seasonal_weights:
            seasonal_weights = DEFAULT_CLIMATE_WEIGHTS.get(
                profile.climate_zone,
                DEFAULT_CLIMATE_WEIGHTS[ClimateZone.TEMPERATE],
            )
        season_weights = seasonal_weights.get(season, {WeatherType.CLEAR: 1.0})

        # Get valid transitions from current weather
        candidates = WEATHER_TRANSITION_GRAPH.get(
            state.weather_type, [WeatherType.CLEAR],
        )

        # Build weighted candidates
        weighted: List[Tuple[WeatherType, float]] = []
        for w in candidates:
            weight = season_weights.get(w, 0.05)
            weighted.append((w, max(0.01, weight)))

        if not weighted:
            return

        weathers, weights_list = zip(*weighted)  # type: ignore[arg-type]
        total_w = sum(weights_list)
        if total_w <= 0:
            return

        normalized_weights = [w / total_w for w in weights_list]
        chosen: WeatherType = random.choices(  # type: ignore[assignment]
            list(weathers), weights=normalized_weights, k=1,
        )[0]

        # Transition duration from profile
        duration_ms = random.uniform(
            profile.min_transition_ms, profile.max_transition_ms,
        )

        self.transition_weather(region_id, chosen, duration_ms)

    # ------------------------------------------------------------------
    # Statistics and Serialization
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the weather simulation."""
        region_stats = {}
        total_particles = 0
        total_transitions_active = 0

        for region_id, state in self._weather_states.items():
            transition = self._transitions.get(region_id)
            particles = self._particles.get(region_id, [])
            alive = sum(1 for p in particles if p.is_alive)
            total_particles += alive

            if transition is not None and not transition.completed:
                total_transitions_active += 1

            region_stats[region_id] = {
                "weather_type": state.weather_type.value if hasattr(state.weather_type, 'value') else state.weather_type,
                "intensity": state.intensity.value if hasattr(state.intensity, 'value') else state.intensity,
                "temperature": round(state.temperature, 1),
                "humidity": round(state.humidity, 3),
                "wind_speed": round(state.wind_speed, 3),
                "fog_density": round(state.fog_density, 3),
                "particle_count": alive,
                "transitioning": transition is not None and not transition.completed,
                "precipitation": round(state.precipitation_intensity, 3),
            }

        return {
            "total_ticks": self._update_count,
            "total_regions": len(self._weather_states),
            "total_profiles": len(self._climate_profiles),
            "total_particles": total_particles,
            "active_transitions": total_transitions_active,
            "total_elapsed_ms": round(self._total_elapsed_ms, 1),
            "update_count": self._update_count,
            "simulation_area": {
                "width": self._simulation_width,
                "height": self._simulation_height,
            },
            "regions": region_stats,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entire weather system state to a dictionary."""
        return {
            "weather_states": {
                rid: ws.to_dict()
                for rid, ws in self._weather_states.items()
            },
            "climate_profiles": {
                rid: cp.to_dict()
                for rid, cp in self._climate_profiles.items()
            },
            "transitions": {
                rid: tr.to_dict()
                for rid, tr in self._transitions.items()
            },
            "forecasts": {
                rid: fc.to_dict()
                for rid, fc in self._forecasts.items()
            },
            "particle_counts": {
                rid: sum(1 for p in plist if p.is_alive)
                for rid, plist in self._particles.items()
            },
            "total_elapsed_ms": round(self._total_elapsed_ms, 1),
            "update_count": self._update_count,
            "simulation_area": {
                "width": self._simulation_width,
                "height": self._simulation_height,
            },
        }

    def get_transition_state(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get the current transition state for a region, if any."""
        transition = self._transitions.get(region_id)
        if transition is None:
            return None
        return transition.to_dict()

    def is_transitioning(self, region_id: str) -> bool:
        """Check whether a region is currently undergoing a weather transition."""
        transition = self._transitions.get(region_id)
        if transition is None:
            return False
        return not transition.completed

    def cancel_transition(self, region_id: str) -> bool:
        """Cancel an active weather transition for a region."""
        transition = self._transitions.pop(region_id, None)
        if transition is not None:
            state = self._weather_states.get(region_id)
            if state is not None:
                state.target_weather = None
                state.transition_progress = 1.0
            return True
        return False


# ---------------------------------------------------------------------------
# Global Accessor
# ---------------------------------------------------------------------------

def get_weather_system() -> EngineWeatherSystem:
    """Get the global EngineWeatherSystem singleton."""
    return EngineWeatherSystem()