"""
SparkLabs Engine - Weather System

Dynamic environmental weather simulation with atmospheric effects
that influence gameplay mechanics, visual presentation, and AI
behavior. Supports configurable weather patterns, transitions,
zone-specific climates, and gameplay-impacting conditions.

Architecture:
  WeatherSystem
    |-- ClimateZone (per-region weather configuration)
    |-- WeatherPattern (transitional weather state machine)
    |-- AtmosphericParams (lighting, particle, and audio modifiers)
    |-- GameplayEffect (weather-driven mechanic modifications)
    |-- ForecastEngine (predictive weather scheduling)

Weather States:
  - CLEAR, CLOUDY, RAIN, HEAVY_RAIN, STORM
  - SNOW, BLIZZARD, FOG, SANDSTORM, WINDY
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class WeatherState(Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    STORM = "storm"
    SNOW = "snow"
    BLIZZARD = "blizzard"
    FOG = "fog"
    SANDSTORM = "sandstorm"
    WINDY = "windy"


class TransitionType(Enum):
    SMOOTH = "smooth"
    ABRUPT = "abrupt"
    GRADUAL = "gradual"


@dataclass
class AtmosphericParams:
    cloud_coverage: float = 0.0
    precipitation_intensity: float = 0.0
    wind_speed: float = 0.0
    visibility_range: float = 100.0
    temperature: float = 20.0
    humidity: float = 0.5
    lightning_chance: float = 0.0
    ambient_color: Tuple[float, float, float] = (1.0, 1.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cloud_coverage": self.cloud_coverage,
            "precipitation_intensity": self.precipitation_intensity,
            "wind_speed": self.wind_speed,
            "visibility_range": self.visibility_range,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "lightning_chance": self.lightning_chance,
        }


@dataclass
class ClimateZone:
    zone_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    allowed_states: List[WeatherState] = field(default_factory=list)
    default_state: WeatherState = WeatherState.CLEAR
    state_weights: Dict[WeatherState, float] = field(default_factory=dict)
    min_transition_time: float = 30.0
    max_transition_time: float = 300.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "allowed_states": [s.value for s in self.allowed_states],
            "current_state": self.default_state.value,
        }


DEFAULT_ATMOSPHERIC_PRESETS: Dict[WeatherState, Dict[str, Any]] = {
    WeatherState.CLEAR: {
        "cloud_coverage": 0.05, "precipitation_intensity": 0.0,
        "wind_speed": 0.1, "visibility_range": 100.0,
        "temperature": 22.0, "humidity": 0.3, "lightning_chance": 0.0,
    },
    WeatherState.CLOUDY: {
        "cloud_coverage": 0.7, "precipitation_intensity": 0.0,
        "wind_speed": 0.2, "visibility_range": 80.0,
        "temperature": 18.0, "humidity": 0.6, "lightning_chance": 0.0,
    },
    WeatherState.RAIN: {
        "cloud_coverage": 0.85, "precipitation_intensity": 0.4,
        "wind_speed": 0.3, "visibility_range": 60.0,
        "temperature": 15.0, "humidity": 0.9, "lightning_chance": 0.05,
    },
    WeatherState.HEAVY_RAIN: {
        "cloud_coverage": 0.95, "precipitation_intensity": 0.8,
        "wind_speed": 0.5, "visibility_range": 30.0,
        "temperature": 12.0, "humidity": 1.0, "lightning_chance": 0.15,
    },
    WeatherState.STORM: {
        "cloud_coverage": 1.0, "precipitation_intensity": 1.0,
        "wind_speed": 1.0, "visibility_range": 15.0,
        "temperature": 10.0, "humidity": 1.0, "lightning_chance": 0.5,
    },
    WeatherState.SNOW: {
        "cloud_coverage": 0.8, "precipitation_intensity": 0.3,
        "wind_speed": 0.2, "visibility_range": 50.0,
        "temperature": -2.0, "humidity": 0.7, "lightning_chance": 0.0,
    },
    WeatherState.BLIZZARD: {
        "cloud_coverage": 1.0, "precipitation_intensity": 0.9,
        "wind_speed": 0.9, "visibility_range": 5.0,
        "temperature": -10.0, "humidity": 1.0, "lightning_chance": 0.05,
    },
    WeatherState.FOG: {
        "cloud_coverage": 0.3, "precipitation_intensity": 0.0,
        "wind_speed": 0.05, "visibility_range": 10.0,
        "temperature": 14.0, "humidity": 0.95, "lightning_chance": 0.0,
    },
    WeatherState.SANDSTORM: {
        "cloud_coverage": 0.6, "precipitation_intensity": 0.0,
        "wind_speed": 0.8, "visibility_range": 8.0,
        "temperature": 35.0, "humidity": 0.05, "lightning_chance": 0.0,
    },
    WeatherState.WINDY: {
        "cloud_coverage": 0.2, "precipitation_intensity": 0.0,
        "wind_speed": 0.7, "visibility_range": 90.0,
        "temperature": 17.0, "humidity": 0.4, "lightning_chance": 0.0,
    },
}


class WeatherSystem:
    _instance: Optional[WeatherSystem] = None

    def __init__(self):
        self._zones: Dict[str, ClimateZone] = {}
        self._current_states: Dict[str, WeatherState] = {}
        self._current_params: Dict[str, AtmosphericParams] = {}
        self._transition_progress: Dict[str, float] = {}
        self._prev_params: Dict[str, AtmosphericParams] = {}
        self._time_since_change: Dict[str, float] = {}
        self._elapsed_time: float = 0.0

    @classmethod
    def get_instance(cls) -> WeatherSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_zone(self, zone: ClimateZone) -> str:
        self._zones[zone.zone_id] = zone
        self._current_states[zone.zone_id] = zone.default_state
        self._current_params[zone.zone_id] = self._params_for_state(zone.default_state)
        self._prev_params[zone.zone_id] = self._current_params[zone.zone_id]
        self._transition_progress[zone.zone_id] = 1.0
        self._time_since_change[zone.zone_id] = 0.0
        return zone.zone_id

    def _params_for_state(self, state: WeatherState) -> AtmosphericParams:
        preset = DEFAULT_ATMOSPHERIC_PRESETS.get(state, DEFAULT_ATMOSPHERIC_PRESETS[WeatherState.CLEAR])
        return AtmosphericParams(**preset)

    def set_weather(self, zone_id: str, state: WeatherState) -> bool:
        zone = self._zones.get(zone_id)
        if zone is None:
            return False
        if state not in zone.allowed_states and zone.allowed_states:
            return False
        self._prev_params[zone_id] = self._current_params[zone_id]
        self._current_states[zone_id] = state
        self._current_params[zone_id] = self._params_for_state(state)
        self._transition_progress[zone_id] = 0.0
        self._time_since_change[zone_id] = 0.0
        return True

    def randomize_weather(self, zone_id: str) -> Optional[WeatherState]:
        zone = self._zones.get(zone_id)
        if zone is None or not zone.allowed_states:
            return None

        weights = zone.state_weights if zone.state_weights else None
        if weights:
            states = list(weights.keys())
            w = [weights[s] for s in states]
            new_state = random.choices(states, weights=w, k=1)[0]
        else:
            new_state = random.choice(zone.allowed_states)

        self.set_weather(zone_id, new_state)
        return new_state

    def update(self, delta_seconds: float):
        self._elapsed_time += delta_seconds

        for zone_id in self._zones:
            self._time_since_change[zone_id] = self._time_since_change.get(zone_id, 0.0) + delta_seconds
            zone = self._zones[zone_id]
            transition_duration = (zone.min_transition_time + zone.max_transition_time) / 2
            if transition_duration > 0:
                self._transition_progress[zone_id] = min(
                    1.0,
                    self._transition_progress.get(zone_id, 0.0) + delta_seconds / transition_duration,
                )

            if self._time_since_change.get(zone_id, 0) > transition_duration * 1.5:
                if random.random() < 0.05:
                    self.randomize_weather(zone_id)

    def get_current_params(self, zone_id: str) -> Optional[AtmosphericParams]:
        if zone_id not in self._current_params:
            return None
        target = self._current_params[zone_id]
        prev = self._prev_params.get(zone_id, target)
        t = self._transition_progress.get(zone_id, 1.0)

        if t >= 1.0:
            return target

        return AtmosphericParams(
            cloud_coverage=prev.cloud_coverage + (target.cloud_coverage - prev.cloud_coverage) * t,
            precipitation_intensity=prev.precipitation_intensity + (target.precipitation_intensity - prev.precipitation_intensity) * t,
            wind_speed=prev.wind_speed + (target.wind_speed - prev.wind_speed) * t,
            visibility_range=prev.visibility_range + (target.visibility_range - prev.visibility_range) * t,
            temperature=prev.temperature + (target.temperature - prev.temperature) * t,
            humidity=prev.humidity + (target.humidity - prev.humidity) * t,
            lightning_chance=prev.lightning_chance + (target.lightning_chance - prev.lightning_chance) * t,
        )

    def get_current_state(self, zone_id: str) -> Optional[WeatherState]:
        return self._current_states.get(zone_id)

    def get_all_zones(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for zone_id, zone in self._zones.items():
            state = self._current_states.get(zone_id, zone.default_state)
            result[zone_id] = {
                "name": zone.name,
                "current_state": state.value,
                "allowed_states": [s.value for s in zone.allowed_states],
            }
        return result

    def get_gameplay_modifiers(self, zone_id: str) -> Dict[str, float]:
        state = self._current_states.get(zone_id, WeatherState.CLEAR)
        params = self._current_params.get(zone_id)
        if params is None:
            return {}

        modifiers = {
            "movement_speed": 1.0,
            "visibility_penalty": 0.0,
            "accuracy_penalty": 0.0,
            "fire_damage_modifier": 1.0,
            "electric_damage_modifier": 1.0,
        }

        if state == WeatherState.RAIN:
            modifiers["fire_damage_modifier"] = 0.7
            modifiers["electric_damage_modifier"] = 1.3
        elif state == WeatherState.STORM:
            modifiers["fire_damage_modifier"] = 0.4
            modifiers["electric_damage_modifier"] = 1.6
            modifiers["accuracy_penalty"] = 0.2
        elif state in (WeatherState.FOG, WeatherState.SANDSTORM):
            modifiers["visibility_penalty"] = 0.7
        elif state in (WeatherState.SNOW, WeatherState.BLIZZARD):
            modifiers["movement_speed"] = 0.7
        elif state == WeatherState.WINDY:
            modifiers["accuracy_penalty"] = 0.15

        return modifiers

    def get_stats(self) -> Dict[str, Any]:
        zone_status = {}
        for zone_id, zone in self._zones.items():
            state = self._current_states.get(zone_id, zone.default_state)
            progress = round(self._transition_progress.get(zone_id, 1.0), 3)
            zone_status[zone_id] = {
                "name": zone.name,
                "state": state.value,
                "transition_progress": progress,
            }
        return {
            "total_zones": len(self._zones),
            "zones": zone_status,
            "elapsed_time": round(self._elapsed_time, 2),
        }


def get_weather_system() -> WeatherSystem:
    return WeatherSystem.get_instance()