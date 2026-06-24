"""
SparkLabs Engine - Dynamic Weather System

A comprehensive dynamic weather and atmosphere simulation system
providing weather profiles, smooth transitions, localized weather
zones, weather-driven particle systems, and atmospheric scattering
calculations for the SparkLabs game engine.

Architecture:
  DynamicWeatherEngine (Singleton)
    |-- WeatherProfile       — temperature, humidity, wind, precipitation
    |-- WeatherTransition    — smooth interpolation between weather states
    |-- WeatherZone          — localized weather effect region
    |-- WeatherParticleSystem — rain/snow/fog particle simulation
    |-- AtmosphereSimulator  — Rayleigh/Mie scattering computation

Weather Pipeline:
  1. WeatherProfile defines atmospheric parameters
  2. WeatherTransition blends between profiles over time
  3. WeatherZones apply localized weather overrides
  4. WeatherParticleSystem renders visual effects
  5. AtmosphereSimulator computes sky color and lighting

Usage:
    engine = get_dynamic_weather_engine()
    engine.set_weather_profile(WeatherType.RAIN, intensity=0.7)
    engine.create_weather_zone(center=(500, 200), radius=100.0)
    engine.update(delta_time)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WeatherType(Enum):
    """Classification of weather conditions."""
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    DRIZZLE = "drizzle"
    SNOW = "snow"
    BLIZZARD = "blizzard"
    FOG = "fog"
    DENSE_FOG = "dense_fog"
    WINDY = "windy"
    GALE = "gale"
    SANDSTORM = "sandstorm"
    HEATWAVE = "heatwave"
    HAIL = "hail"
    SLEET = "sleet"


class PrecipitationType(Enum):
    """Type of precipitation particles."""
    NONE = "none"
    RAIN = "rain"
    SNOW = "snow"
    HAIL = "hail"
    SLEET = "sleet"


class TransitionCurve(Enum):
    """Interpolation curve for weather transitions."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    SMOOTHSTEP = "smoothstep"


class ScatteringModel(Enum):
    """Atmospheric scattering computation model."""
    RAYLEIGH = "rayleigh"
    MIE = "mie"
    COMBINED = "combined"
    PRE_COMPUTED = "pre_computed"


class CloudType(Enum):
    """Cloud formation types for sky rendering."""
    CUMULUS = "cumulus"
    STRATUS = "stratus"
    CIRRUS = "cirrus"
    CUMULONIMBUS = "cumulonimbus"
    NIMBOSTRATUS = "nimbostratus"
    NONE = "none"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WeatherProfile:
    """Complete atmospheric profile defining weather conditions.

    Contains all parameters needed to describe a weather state:
    temperature, humidity, wind, precipitation, cloud cover, and
    visual atmospheric properties for rendering.
    """
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    weather_type: WeatherType = WeatherType.CLEAR
    temperature: float = 22.0
    humidity: float = 0.40
    wind_speed: float = 0.05
    wind_direction: float = 0.0
    wind_gust_factor: float = 0.1
    precipitation_type: PrecipitationType = PrecipitationType.NONE
    precipitation_intensity: float = 0.0
    cloud_cover: float = 0.0
    cloud_type: CloudType = CloudType.CUMULUS
    visibility: float = 1.0
    fog_density: float = 0.0
    fog_color: Tuple[float, float, float] = (0.7, 0.75, 0.8)
    ambient_temperature: float = 22.0
    ground_wetness: float = 0.0
    lightning_probability: float = 0.0
    thunder_interval: float = 0.0
    air_pressure: float = 1013.25
    uv_index: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "weather_type": self.weather_type.value,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "wind_gust_factor": self.wind_gust_factor,
            "precipitation_type": self.precipitation_type.value,
            "precipitation_intensity": self.precipitation_intensity,
            "cloud_cover": self.cloud_cover,
            "cloud_type": self.cloud_type.value,
            "visibility": self.visibility,
            "fog_density": self.fog_density,
            "fog_color": list(self.fog_color),
            "ambient_temperature": self.ambient_temperature,
            "ground_wetness": self.ground_wetness,
            "lightning_probability": self.lightning_probability,
            "thunder_interval": self.thunder_interval,
            "air_pressure": self.air_pressure,
            "uv_index": self.uv_index,
        }


@dataclass
class WeatherTransition:
    """Smooth transition between two weather profiles.

    Interpolates all atmospheric parameters between a source and
    target weather profile over a configurable duration with a
    choice of easing curves.
    """
    transition_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_profile: Optional[WeatherProfile] = None
    target_profile: Optional[WeatherProfile] = None
    duration: float = 60.0
    elapsed: float = 0.0
    curve: TransitionCurve = TransitionCurve.EASE_IN_OUT
    is_complete: bool = False
    current_profile: Optional[WeatherProfile] = None

    def progress(self, delta_time: float) -> float:
        """Advance the transition and return the current blend factor (0.0-1.0)."""
        self.elapsed += delta_time
        t = min(self.elapsed / self.duration, 1.0) if self.duration > 0 else 1.0

        if self.curve == TransitionCurve.LINEAR:
            factor = t
        elif self.curve == TransitionCurve.EASE_IN:
            factor = t * t
        elif self.curve == TransitionCurve.EASE_OUT:
            factor = 1.0 - (1.0 - t) * (1.0 - t)
        elif self.curve == TransitionCurve.EASE_IN_OUT:
            factor = 3.0 * t * t - 2.0 * t * t * t
        elif self.curve == TransitionCurve.SMOOTHSTEP:
            factor = 6.0 * t ** 5 - 15.0 * t ** 4 + 10.0 * t ** 3
        else:
            factor = t

        self.is_complete = t >= 1.0
        return factor

    def get_blended_profile(self) -> Optional[WeatherProfile]:
        """Get the current blended profile between source and target."""
        if self.source_profile is None or self.target_profile is None:
            return self.target_profile

        t = self.progress(0.0)
        if self.is_complete:
            return self.target_profile

        def lerp(a: float, b: float, f: float) -> float:
            return a + (b - a) * f

        def lerp_color(a: Tuple[float, float, float],
                       b: Tuple[float, float, float],
                       f: float) -> Tuple[float, float, float]:
            return (lerp(a[0], b[0], f), lerp(a[1], b[1], f), lerp(a[2], b[2], f))

        return WeatherProfile(
            weather_type=self.target_profile.weather_type,
            temperature=lerp(self.source_profile.temperature,
                             self.target_profile.temperature, t),
            humidity=lerp(self.source_profile.humidity,
                          self.target_profile.humidity, t),
            wind_speed=lerp(self.source_profile.wind_speed,
                            self.target_profile.wind_speed, t),
            wind_direction=lerp(self.source_profile.wind_direction,
                                self.target_profile.wind_direction, t),
            precipitation_intensity=lerp(self.source_profile.precipitation_intensity,
                                         self.target_profile.precipitation_intensity, t),
            cloud_cover=lerp(self.source_profile.cloud_cover,
                             self.target_profile.cloud_cover, t),
            visibility=lerp(self.source_profile.visibility,
                            self.target_profile.visibility, t),
            fog_density=lerp(self.source_profile.fog_density,
                             self.target_profile.fog_density, t),
            fog_color=lerp_color(self.source_profile.fog_color,
                                 self.target_profile.fog_color, t),
            ground_wetness=lerp(self.source_profile.ground_wetness,
                                self.target_profile.ground_wetness, t),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "duration": self.duration,
            "elapsed": self.elapsed,
            "curve": self.curve.value,
            "is_complete": self.is_complete,
            "progress": self.elapsed / self.duration if self.duration > 0 else 1.0,
        }


@dataclass
class WeatherZone:
    """Localized weather effect region with smooth blending.

    Defines a spatial region (circle or ellipse) where weather
    parameters differ from the global weather. Zones can have
    smooth transition boundaries.
    """
    zone_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    center: Tuple[float, float] = (0.0, 0.0)
    radius_x: float = 50.0
    radius_y: float = 50.0
    profile: Optional[WeatherProfile] = None
    blend_width: float = 10.0
    priority: int = 0
    is_active: bool = True

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is within the zone's influence region."""
        nx = (x - self.center[0]) / self.radius_x
        ny = (y - self.center[1]) / self.radius_y
        return (nx * nx + ny * ny) <= 1.0

    def get_influence_factor(self, x: float, y: float) -> float:
        """Get the weather influence factor (0.0-1.0) at a point."""
        nx = (x - self.center[0]) / self.radius_x
        ny = (y - self.center[1]) / self.radius_y
        distance = math.sqrt(nx * nx + ny * ny)

        inner_radius = 1.0 - (self.blend_width / max(self.radius_x, self.radius_y, 0.001))
        if distance <= inner_radius:
            return 1.0
        if distance >= 1.0:
            return 0.0

        t = (1.0 - distance) / (1.0 - inner_radius)
        return 3.0 * t * t - 2.0 * t * t * t

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "center": list(self.center),
            "radius_x": self.radius_x,
            "radius_y": self.radius_y,
            "priority": self.priority,
            "is_active": self.is_active,
            "blend_width": self.blend_width,
            "profile": self.profile.to_dict() if self.profile else None,
        }


@dataclass
class WeatherParticle:
    """Individual weather particle (rain drop, snowflake, fog volume)."""
    particle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity: List[float] = field(default_factory=lambda: [0.0, -1.0, 0.0])
    lifetime: float = 2.0
    age: float = 0.0
    size: float = 1.0
    alpha: float = 1.0
    particle_type: PrecipitationType = PrecipitationType.RAIN
    is_alive: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "particle_id": self.particle_id,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "lifetime": self.lifetime,
            "age": self.age,
            "size": self.size,
            "alpha": self.alpha,
            "particle_type": self.particle_type.value,
            "is_alive": self.is_alive,
        }


@dataclass
class WeatherParticleSystem:
    """Manages weather-driven particle effects (rain, snow, fog)."""
    system_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    max_particles: int = 10000
    spawn_rate: float = 100.0
    particle_type: PrecipitationType = PrecipitationType.RAIN
    spawn_area: Tuple[float, float, float, float] = (-50.0, 50.0, -50.0, 50.0)
    spawn_height: float = 20.0
    particle_size: float = 1.0
    particle_lifetime: float = 2.0
    wind_influence: float = 0.5
    gravity: float = 9.81
    _particles: List[WeatherParticle] = field(default_factory=list, repr=False)
    _spawn_accumulator: float = 0.0
    _active_count: int = 0

    def update(self, delta_time: float, wind_speed: float,
               wind_direction: float) -> None:
        """Update all particles in the system."""
        self._spawn_accumulator += self.spawn_rate * delta_time
        spawn_count = int(self._spawn_accumulator)
        self._spawn_accumulator -= spawn_count

        for _ in range(min(spawn_count, self.max_particles - len(self._particles))):
            self._spawn_particle()

        wind_vx = wind_speed * math.cos(math.radians(wind_direction))
        wind_vy = wind_speed * math.sin(math.radians(wind_direction))

        alive = []
        for p in self._particles:
            p.age += delta_time
            if p.age >= p.lifetime:
                p.is_alive = False
                continue

            if self.particle_type == PrecipitationType.RAIN:
                p.velocity[1] -= self.gravity * delta_time
                p.velocity[0] += wind_vx * self.wind_influence * delta_time
            elif self.particle_type == PrecipitationType.SNOW:
                p.velocity[0] += wind_vx * self.wind_influence * 0.5 * delta_time
                p.velocity[1] = -0.5 + wind_vy * 0.1
                p.velocity[0] += random.uniform(-0.1, 0.1)
            elif self.particle_type == PrecipitationType.HAIL:
                p.velocity[1] -= self.gravity * 1.5 * delta_time
                p.velocity[0] += wind_vx * self.wind_influence * 0.3 * delta_time

            p.position[0] += p.velocity[0] * delta_time
            p.position[1] += p.velocity[1] * delta_time
            p.position[2] += p.velocity[2] * delta_time

            alive.append(p)

        self._particles = alive
        self._active_count = len(self._particles)

    def _spawn_particle(self) -> None:
        """Spawn a new particle within the spawn area."""
        x = random.uniform(self.spawn_area[0], self.spawn_area[1])
        y = self.spawn_height
        z = random.uniform(self.spawn_area[2], self.spawn_area[3])

        particle = WeatherParticle(
            position=[x, y, z],
            velocity=[0.0, -random.uniform(0.5, 2.0), 0.0],
            lifetime=self.particle_lifetime * random.uniform(0.8, 1.2),
            size=self.particle_size * random.uniform(0.8, 1.2),
            particle_type=self.particle_type,
        )
        self._particles.append(particle)

    def get_active_particles(self) -> List[WeatherParticle]:
        return [p for p in self._particles if p.is_alive]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "max_particles": self.max_particles,
            "spawn_rate": self.spawn_rate,
            "particle_type": self.particle_type.value,
            "active_count": self._active_count,
            "total_particles": len(self._particles),
        }


@dataclass
class AtmosphereSimulator:
    """Computes atmospheric scattering for sky and lighting.

    Implements Rayleigh and Mie scattering models to compute sky
    color, sun color, ambient light, and atmospheric haze based on
    weather conditions and time of day.
    """
    simulator_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    scattering_model: ScatteringModel = ScatteringModel.COMBINED
    sun_direction: List[float] = field(default_factory=lambda: [0.0, 1.0, 0.5])
    sun_intensity: float = 1.0
    rayleigh_coefficients: Tuple[float, float, float] = (5.8e-6, 13.5e-6, 33.1e-6)
    mie_coefficient: float = 2.0e-5
    mie_asymmetry: float = 0.76
    planet_radius: float = 6371000.0
    atmosphere_height: float = 80000.0
    sky_color: Tuple[float, float, float] = (0.45, 0.70, 1.0)
    sun_color: Tuple[float, float, float] = (1.0, 0.95, 0.8)
    ambient_color: Tuple[float, float, float] = (0.3, 0.35, 0.4)
    haze_factor: float = 0.0

    def compute_scattering(self, weather_profile: WeatherProfile,
                           time_of_day: float = 0.5) -> Dict[str, Any]:
        """Compute scattering parameters based on weather and time of day."""
        visibility = weather_profile.visibility
        fog = weather_profile.fog_density
        cloud = weather_profile.cloud_cover

        sun_angle = time_of_day * math.pi * 2
        self.sun_direction = [
            math.cos(sun_angle) * 0.7,
            math.sin(sun_angle),
            0.5,
        ]

        rayleigh_strength = 1.0 - fog * 0.8
        mie_strength = fog * 0.9 + cloud * 0.3

        sky_r = self.rayleigh_coefficients[0] * rayleigh_strength + self.mie_coefficient * mie_strength
        sky_g = self.rayleigh_coefficients[1] * rayleigh_strength + self.mie_coefficient * mie_strength
        sky_b = self.rayleigh_coefficients[2] * rayleigh_strength + self.mie_coefficient * mie_strength

        self.sky_color = (
            min(1.0, 0.45 + sky_r * 1e5 * visibility),
            min(1.0, 0.70 + sky_g * 1e5 * visibility),
            min(1.0, 1.0 + sky_b * 1e5 * visibility),
        )

        self.sun_color = (
            min(1.0, 1.0 - fog * 0.6 - cloud * 0.3),
            min(1.0, 0.95 - fog * 0.5 - cloud * 0.25),
            min(1.0, 0.8 - fog * 0.4 - cloud * 0.2),
        )

        self.ambient_color = (
            0.3 * visibility,
            0.35 * visibility,
            0.4 * visibility,
        )

        self.haze_factor = fog + cloud * 0.5

        return {
            "sky_color": list(self.sky_color),
            "sun_color": list(self.sun_color),
            "ambient_color": list(self.ambient_color),
            "sun_direction": list(self.sun_direction),
            "haze_factor": self.haze_factor,
            "sun_intensity": self.sun_intensity * visibility,
        }

    def get_lighting_params(self) -> Dict[str, Any]:
        return {
            "sky_color": list(self.sky_color),
            "sun_color": list(self.sun_color),
            "ambient_color": list(self.ambient_color),
            "sun_direction": list(self.sun_direction),
            "sun_intensity": self.sun_intensity,
            "haze_factor": self.haze_factor,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_lighting_params()


# ---------------------------------------------------------------------------
# Weather Presets
# ---------------------------------------------------------------------------

_WEATHER_PRESETS: Dict[WeatherType, Dict[str, Any]] = {
    WeatherType.CLEAR: {
        "temperature": 22.0, "humidity": 0.35, "wind_speed": 0.03,
        "visibility": 1.0, "cloud_cover": 0.05, "precipitation_intensity": 0.0,
        "fog_density": 0.0, "lightning_probability": 0.0,
    },
    WeatherType.PARTLY_CLOUDY: {
        "temperature": 20.0, "humidity": 0.45, "wind_speed": 0.08,
        "visibility": 0.95, "cloud_cover": 0.35, "precipitation_intensity": 0.0,
        "fog_density": 0.0, "lightning_probability": 0.0,
    },
    WeatherType.OVERCAST: {
        "temperature": 16.0, "humidity": 0.65, "wind_speed": 0.12,
        "visibility": 0.80, "cloud_cover": 0.85, "precipitation_intensity": 0.0,
        "fog_density": 0.05, "lightning_probability": 0.0,
    },
    WeatherType.RAIN: {
        "temperature": 14.0, "humidity": 0.85, "wind_speed": 0.15,
        "visibility": 0.70, "cloud_cover": 0.90, "precipitation_intensity": 0.4,
        "fog_density": 0.10, "lightning_probability": 0.05,
    },
    WeatherType.HEAVY_RAIN: {
        "temperature": 12.0, "humidity": 0.95, "wind_speed": 0.22,
        "visibility": 0.45, "cloud_cover": 0.95, "precipitation_intensity": 0.75,
        "fog_density": 0.15, "lightning_probability": 0.10,
    },
    WeatherType.THUNDERSTORM: {
        "temperature": 11.0, "humidity": 0.98, "wind_speed": 0.35,
        "visibility": 0.30, "cloud_cover": 1.0, "precipitation_intensity": 0.85,
        "fog_density": 0.20, "lightning_probability": 0.40,
    },
    WeatherType.SNOW: {
        "temperature": -2.0, "humidity": 0.65, "wind_speed": 0.10,
        "visibility": 0.65, "cloud_cover": 0.80, "precipitation_intensity": 0.3,
        "fog_density": 0.08, "lightning_probability": 0.0,
    },
    WeatherType.BLIZZARD: {
        "temperature": -12.0, "humidity": 0.85, "wind_speed": 0.45,
        "visibility": 0.15, "cloud_cover": 1.0, "precipitation_intensity": 0.8,
        "fog_density": 0.30, "lightning_probability": 0.0,
    },
    WeatherType.FOG: {
        "temperature": 13.0, "humidity": 0.92, "wind_speed": 0.04,
        "visibility": 0.35, "cloud_cover": 0.60, "precipitation_intensity": 0.0,
        "fog_density": 0.60, "lightning_probability": 0.0,
    },
    WeatherType.DENSE_FOG: {
        "temperature": 11.0, "humidity": 0.98, "wind_speed": 0.02,
        "visibility": 0.10, "cloud_cover": 0.70, "precipitation_intensity": 0.0,
        "fog_density": 0.90, "lightning_probability": 0.0,
    },
    WeatherType.GALE: {
        "temperature": 15.0, "humidity": 0.50, "wind_speed": 0.70,
        "visibility": 0.75, "cloud_cover": 0.60, "precipitation_intensity": 0.0,
        "fog_density": 0.05, "lightning_probability": 0.0,
    },
    WeatherType.SANDSTORM: {
        "temperature": 35.0, "humidity": 0.10, "wind_speed": 0.55,
        "visibility": 0.15, "cloud_cover": 0.50, "precipitation_intensity": 0.0,
        "fog_density": 0.70, "lightning_probability": 0.0,
    },
}


# ---------------------------------------------------------------------------
# DynamicWeatherEngine — Unified Dynamic Weather Singleton
# ---------------------------------------------------------------------------

class DynamicWeatherEngine:
    """Complete dynamic weather simulation engine for SparkLabs.

    Manages weather profiles, smooth transitions, localized weather
    zones, particle effects, and atmospheric scattering. Provides
    a unified API for weather-driven gameplay and rendering.
    """

    _instance: Optional["DynamicWeatherEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "DynamicWeatherEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "DynamicWeatherEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._current_profile: WeatherProfile = WeatherProfile()
        self._target_profile: Optional[WeatherProfile] = None
        self._transition: Optional[WeatherTransition] = None
        self._zones: Dict[str, WeatherZone] = {}
        self._particle_system = WeatherParticleSystem()
        self._atmosphere = AtmosphereSimulator()
        self._time_of_day: float = 0.5
        self._frame_count: int = 0
        self._transition_count: int = 0
        self._last_lightning_time: float = 0.0

    def set_weather_profile(self, weather_type: WeatherType,
                            intensity: float = 0.5,
                            transition_duration: float = 0.0,
                            transition_curve: TransitionCurve = TransitionCurve.EASE_IN_OUT) -> WeatherTransition:
        """Set a target weather profile with an optional transition."""
        preset = _WEATHER_PRESETS.get(weather_type, _WEATHER_PRESETS[WeatherType.CLEAR])
        new_profile = WeatherProfile(
            weather_type=weather_type,
            temperature=preset["temperature"],
            humidity=preset["humidity"],
            wind_speed=preset["wind_speed"] * intensity,
            visibility=1.0 - (1.0 - preset["visibility"]) * intensity,
            cloud_cover=preset["cloud_cover"] * intensity,
            precipitation_intensity=preset["precipitation_intensity"] * intensity,
            fog_density=preset["fog_density"] * intensity,
            lightning_probability=preset["lightning_probability"] * intensity,
            precipitation_type=self._precipitation_for_weather(weather_type),
            cloud_type=self._cloud_for_weather(weather_type),
        )

        self._target_profile = new_profile

        if transition_duration > 0:
            self._transition = WeatherTransition(
                source_profile=self._current_profile,
                target_profile=new_profile,
                duration=transition_duration,
                curve=transition_curve,
            )
            self._transition_count += 1
        else:
            self._current_profile = new_profile
            self._transition = None
            self._transition_count += 1

        return self._transition if self._transition else WeatherTransition(
            source_profile=new_profile, target_profile=new_profile,
            duration=0.0, is_complete=True
        )

    def _precipitation_for_weather(self, weather_type: WeatherType) -> PrecipitationType:
        if weather_type in (WeatherType.RAIN, WeatherType.HEAVY_RAIN,
                            WeatherType.THUNDERSTORM, WeatherType.DRIZZLE):
            return PrecipitationType.RAIN
        elif weather_type in (WeatherType.SNOW, WeatherType.BLIZZARD):
            return PrecipitationType.SNOW
        elif weather_type == WeatherType.HAIL:
            return PrecipitationType.HAIL
        elif weather_type == WeatherType.SLEET:
            return PrecipitationType.SLEET
        return PrecipitationType.NONE

    def _cloud_for_weather(self, weather_type: WeatherType) -> CloudType:
        if weather_type in (WeatherType.CLEAR,):
            return CloudType.NONE
        elif weather_type == WeatherType.PARTLY_CLOUDY:
            return CloudType.CUMULUS
        elif weather_type in (WeatherType.OVERCAST, WeatherType.RAIN,
                              WeatherType.HEAVY_RAIN, WeatherType.DRIZZLE):
            return CloudType.STRATUS
        elif weather_type == WeatherType.THUNDERSTORM:
            return CloudType.CUMULONIMBUS
        elif weather_type in (WeatherType.SNOW, WeatherType.BLIZZARD):
            return CloudType.NIMBOSTRATUS
        return CloudType.STRATUS

    def create_weather_zone(self, name: str = "",
                            center: Tuple[float, float] = (0.0, 0.0),
                            radius: float = 50.0,
                            profile: Optional[WeatherProfile] = None,
                            priority: int = 0) -> WeatherZone:
        """Create a localized weather zone."""
        zone = WeatherZone(
            name=name, center=center, radius_x=radius, radius_y=radius,
            profile=profile, priority=priority,
        )
        self._zones[zone.zone_id] = zone
        return zone

    def get_weather_zone(self, zone_id: str) -> Optional[WeatherZone]:
        return self._zones.get(zone_id)

    def remove_weather_zone(self, zone_id: str) -> bool:
        if zone_id in self._zones:
            del self._zones[zone_id]
            return True
        return False

    def get_weather_at_position(self, x: float, y: float) -> WeatherProfile:
        """Get the effective weather profile at a world position."""
        base = self._current_profile

        active_zones = sorted(
            [z for z in self._zones.values() if z.is_active and z.profile],
            key=lambda z: z.priority, reverse=True
        )

        for zone in active_zones:
            factor = zone.get_influence_factor(x, y)
            if factor > 0.0 and zone.profile:
                base = self._blend_profiles(base, zone.profile, factor)

        return base

    def _blend_profiles(self, a: WeatherProfile, b: WeatherProfile,
                        t: float) -> WeatherProfile:
        def lerp(v1: float, v2: float, f: float) -> float:
            return v1 + (v2 - v1) * f

        return WeatherProfile(
            weather_type=b.weather_type if t > 0.5 else a.weather_type,
            temperature=lerp(a.temperature, b.temperature, t),
            humidity=lerp(a.humidity, b.humidity, t),
            wind_speed=lerp(a.wind_speed, b.wind_speed, t),
            wind_direction=lerp(a.wind_direction, b.wind_direction, t),
            precipitation_intensity=lerp(a.precipitation_intensity,
                                         b.precipitation_intensity, t),
            cloud_cover=lerp(a.cloud_cover, b.cloud_cover, t),
            visibility=lerp(a.visibility, b.visibility, t),
            fog_density=lerp(a.fog_density, b.fog_density, t),
            ground_wetness=lerp(a.ground_wetness, b.ground_wetness, t),
            lightning_probability=lerp(a.lightning_probability,
                                       b.lightning_probability, t),
        )

    def set_time_of_day(self, time_of_day: float) -> None:
        """Set the normalized time of day (0.0 = midnight, 0.5 = noon)."""
        self._time_of_day = max(0.0, min(1.0, time_of_day))

    def get_current_profile(self) -> WeatherProfile:
        return self._current_profile

    def get_atmosphere_params(self) -> Dict[str, Any]:
        return self._atmosphere.compute_scattering(
            self._current_profile, self._time_of_day
        )

    def update(self, delta_time: float) -> None:
        """Execute one frame of the weather simulation."""
        if self._transition and not self._transition.is_complete:
            self._transition.progress(delta_time)
            blended = self._transition.get_blended_profile()
            if blended:
                self._current_profile = blended
            if self._transition.is_complete and self._target_profile:
                self._current_profile = self._target_profile
                self._transition = None

        profile = self._current_profile
        if profile.precipitation_intensity > 0.01:
            ppt = profile.precipitation_type
            if ppt != PrecipitationType.NONE:
                self._particle_system.particle_type = ppt
                self._particle_system.spawn_rate = 100.0 * profile.precipitation_intensity
                self._particle_system.update(
                    delta_time, profile.wind_speed, profile.wind_direction
                )
        else:
            self._particle_system.update(delta_time, 0.0, 0.0)

        if profile.lightning_probability > 0:
            current_time = _time_module.time()
            if current_time - self._last_lightning_time > 3.0:
                if random.random() < profile.lightning_probability * delta_time:
                    self._last_lightning_time = current_time

        self._atmosphere.compute_scattering(profile, self._time_of_day)
        self._frame_count += 1

    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_weather": self._current_profile.weather_type.value,
            "temperature": self._current_profile.temperature,
            "humidity": self._current_profile.humidity,
            "wind_speed": self._current_profile.wind_speed,
            "visibility": self._current_profile.visibility,
            "precipitation": self._current_profile.precipitation_intensity,
            "cloud_cover": self._current_profile.cloud_cover,
            "fog_density": self._current_profile.fog_density,
            "time_of_day": self._time_of_day,
            "zone_count": len(self._zones),
            "active_zones": sum(1 for z in self._zones.values() if z.is_active),
            "transition_active": self._transition is not None and not self._transition.is_complete,
            "transition_count": self._transition_count,
            "particle_system": self._particle_system.to_dict(),
            "atmosphere": self._atmosphere.to_dict(),
            "frame_count": self._frame_count,
        }


# ---------------------------------------------------------------------------
# Convenience Accessor
# ---------------------------------------------------------------------------

def get_dynamic_weather_engine() -> DynamicWeatherEngine:
    """Get the global DynamicWeatherEngine singleton instance."""
    return DynamicWeatherEngine()