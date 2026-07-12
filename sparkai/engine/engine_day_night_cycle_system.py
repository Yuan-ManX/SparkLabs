"""
SparkLabs Engine - Atmospheric Cycle System

Manages astronomical time progression, sun and moon positioning, lighting
transitions, weather modifiers, aurora effects, and time-based world
triggers. Provides a unified clock that drives visual atmosphere changes
and scheduled world events across the game engine.

Architecture:
  AtmosphericCycleSystem (singleton)
    |-- AtmosphericPhase, CelestialBodyType, WeatherModifier, AtmosphericEventKind
    |-- CelestialPosition, LightingProfile, TimeTrigger, ScheduledEvent,
       AuroraInstance, AtmosphericCycleConfig, AtmosphericCycleStats,
       AtmosphericCycleSnapshot, AtmosphericCycleEvent
    |-- get_atmospheric_cycle_system

Core Capabilities:
  - register_phase / remove_phase / get_phase / list_phases
  - register_lighting_profile / get_lighting_profile / list_lighting_profiles
  - register_trigger / remove_trigger / get_trigger / list_triggers
  - schedule_event / cancel_event / list_scheduled_events
  - get_current_time / set_current_time / advance_time
  - get_celestial_position / get_sun_position / get_moon_position
  - get_current_lighting / get_active_auroras / spawn_aurora / dismiss_aurora
  - register_weather_modifier / remove_weather_modifier
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`AtmosphericCycleSystem.get_instance` or the module-level
:func:`get_atmospheric_cycle_system` factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PHASES: int = 50
_MAX_LIGHTING_PROFILES: int = 100
_MAX_TRIGGERS: int = 500
_MAX_SCHEDULED_EVENTS: int = 2000
_MAX_WEATHER_MODIFIERS: int = 50
_MAX_AURORAS: int = 20
_MAX_EVENTS: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


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


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
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
# Enums
# ---------------------------------------------------------------------------

class AtmosphericPhase(str, Enum):
    """Named phases of a full day cycle."""
    MIDNIGHT = "midnight"
    PRE_DAWN = "pre_dawn"
    DAWN = "dawn"
    SUNRISE = "sunrise"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    GOLDEN_HOUR = "golden_hour"
    SUNSET = "sunset"
    DUSK = "dusk"
    EVENING = "evening"
    NIGHT = "night"


class CelestialBodyType(str, Enum):
    """Celestial bodies tracked by the system."""
    SUN = "sun"
    MOON = "moon"
    STARS = "stars"


class WeatherModifier(str, Enum):
    """Weather conditions that affect lighting and visibility."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    STORM = "storm"
    FOG = "fog"
    SNOW = "snow"
    SANDSTORM = "sandstorm"


class AtmosphericEventKind(str, Enum):
    """Audit event types emitted by the day/night cycle system."""
    PHASE_REGISTERED = "phase_registered"
    PHASE_REMOVED = "phase_removed"
    LIGHTING_PROFILE_REGISTERED = "lighting_profile_registered"
    TRIGGER_REGISTERED = "trigger_registered"
    TRIGGER_REMOVED = "trigger_removed"
    TRIGGER_FIRED = "trigger_fired"
    EVENT_SCHEDULED = "event_scheduled"
    EVENT_CANCELLED = "event_cancelled"
    EVENT_FIRED = "event_fired"
    TIME_ADVANCED = "time_advanced"
    TIME_SET = "time_set"
    AURORA_SPAWNED = "aurora_spawned"
    AURORA_DISMISSED = "aurora_dismissed"
    WEATHER_MODIFIER_REGISTERED = "weather_modifier_registered"
    WEATHER_MODIFIER_REMOVED = "weather_modifier_removed"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class AtmosphericPhaseDefinition:
    """Definition of a named time-of-day phase."""
    phase_id: str
    name: str
    start_hour: float
    end_hour: float
    description: str = ""
    ambient_color: str = "#FFFFFF"
    sun_color: str = "#FFFFAA"
    moon_color: str = "#AABBFF"
    fog_density: float = 0.0
    star_visibility: float = 0.0
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LightingProfile:
    """A complete lighting setup for a specific time window."""
    profile_id: str
    name: str
    hour: float
    ambient_intensity: float = 1.0
    directional_intensity: float = 1.0
    ambient_color: str = "#FFFFFF"
    sun_color: str = "#FFFFAA"
    moon_color: str = "#AABBFF"
    shadow_softness: float = 0.5
    exposure: float = 1.0
    bloom_threshold: float = 0.8
    fog_color: str = "#CCCCCC"
    fog_density: float = 0.0
    sky_tint: str = "#87CEEB"
    horizon_tint: str = "#FFE4B5"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CelestialPosition:
    """Computed position of a celestial body."""
    body: str
    azimuth: float = 0.0
    altitude: float = 0.0
    visible: bool = True
    intensity: float = 1.0
    color: str = "#FFFFFF"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TimeTrigger:
    """A trigger that fires when the world clock reaches a specific time."""
    trigger_id: str
    name: str
    fire_hour: float
    description: str = ""
    repeat_daily: bool = True
    action_type: str = "event"
    action_payload: Dict[str, Any] = field(default_factory=dict)
    last_fired_date: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ScheduledEvent:
    """A one-time or recurring scheduled world event."""
    event_id: str
    name: str
    fire_time: float
    description: str = ""
    event_type: str = "world"
    payload: Dict[str, Any] = field(default_factory=dict)
    recurring: bool = False
    recurring_interval_hours: float = 24.0
    fired: bool = False
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AuroraInstance:
    """An aurora effect instance in the sky."""
    aurora_id: str
    name: str
    intensity: float = 0.5
    color_primary: str = "#00FF66"
    color_secondary: str = "#AA66FF"
    wave_speed: float = 1.0
    wave_amplitude: float = 0.3
    duration: float = 3600.0
    spawned_at: float = field(default_factory=_now)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherModifierEntry:
    """A weather condition that modifies lighting and atmosphere."""
    modifier_id: str
    weather: str
    ambient_multiplier: float = 1.0
    directional_multiplier: float = 1.0
    fog_multiplier: float = 1.0
    star_visibility_multiplier: float = 1.0
    sky_tint_override: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AtmosphericCycleConfig:
    """Global tuning parameters."""
    day_length_real_seconds: float = 1200.0
    start_hour: float = 8.0
    max_phases: int = 50
    max_triggers: int = 500
    max_scheduled_events: int = 2000
    max_weather_modifiers: int = 50
    max_auroras: int = 20
    sun_azimuth_offset: float = 0.0
    moon_cycle_days: float = 27.3
    latitude_degrees: float = 45.0
    enable_seasonal_variation: bool = True
    seasonal_amplitude: float = 0.3
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AtmosphericCycleStats:
    """Aggregate statistics."""
    total_phases: int = 0
    total_lighting_profiles: int = 0
    total_triggers: int = 0
    total_scheduled_events: int = 0
    total_triggers_fired: int = 0
    total_events_fired: int = 0
    total_auroras_spawned: int = 0
    total_weather_modifiers: int = 0
    current_day: int = 1
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AtmosphericCycleSnapshot:
    """Full state snapshot."""
    current_hour: float = 0.0
    current_phase: str = ""
    sun_position: Dict[str, Any] = field(default_factory=dict)
    moon_position: Dict[str, Any] = field(default_factory=dict)
    active_lighting: Dict[str, Any] = field(default_factory=dict)
    active_auroras: List[Dict[str, Any]] = field(default_factory=list)
    active_weather: str = "clear"
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AtmosphericCycleEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    phase_id: str = ""
    trigger_id: str = ""
    event_id_ref: str = ""
    aurora_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Day/Night Cycle System
# ---------------------------------------------------------------------------

class AtmosphericCycleSystem:
    """Manages world time, celestial positions, and lighting transitions."""

    _instance: Optional["AtmosphericCycleSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._phases: Dict[str, AtmosphericPhaseDefinition] = {}
        self._lighting_profiles: Dict[str, LightingProfile] = {}
        self._triggers: Dict[str, TimeTrigger] = {}
        self._scheduled_events: Dict[str, ScheduledEvent] = {}
        self._weather_modifiers: Dict[str, WeatherModifierEntry] = {}
        self._auroras: Dict[str, AuroraInstance] = {}
        self._events: List[AtmosphericCycleEvent] = []
        self._stats = AtmosphericCycleStats()
        self._config = AtmosphericCycleConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._current_hour: float = self._config.start_hour
        self._current_day: int = 1
        self._active_weather: str = WeatherModifier.CLEAR.value
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "AtmosphericCycleSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            phases_data = [
                ("phase_midnight", "Midnight", 0.0, 4.0,
                 "Deep night with stars at maximum visibility.",
                 "#1a1a3e", "#223366", "#8899FF", 0.02, 1.0, "icon_midnight"),
                ("phase_pre_dawn", "Pre-Dawn", 4.0, 5.5,
                 "The sky begins to lighten before sunrise.",
                 "#2a2a4e", "#334477", "#7788DD", 0.05, 0.7, "icon_pre_dawn"),
                ("phase_dawn", "Dawn", 5.5, 6.5,
                 "First light breaks over the horizon.",
                 "#4a3a5e", "#886644", "#6677BB", 0.08, 0.3, "icon_dawn"),
                ("phase_sunrise", "Sunrise", 6.5, 7.5,
                 "The sun rises with warm golden colors.",
                 "#FF9966", "#FFAA44", "#5566AA", 0.06, 0.1, "icon_sunrise"),
                ("phase_morning", "Morning", 7.5, 11.0,
                 "Bright morning with clear skies.",
                 "#87CEEB", "#FFFFCC", "#445599", 0.02, 0.0, "icon_morning"),
                ("phase_midday", "Midday", 11.0, 13.0,
                 "Sun at its peak with intense light.",
                 "#AAEEFF", "#FFFFFF", "#334488", 0.01, 0.0, "icon_midday"),
                ("phase_afternoon", "Afternoon", 13.0, 16.0,
                 "Warm afternoon light.",
                 "#99DDFF", "#FFEEBB", "#445599", 0.02, 0.0, "icon_afternoon"),
                ("phase_golden_hour", "Golden Hour", 16.0, 17.5,
                 "Warm golden light before sunset.",
                 "#FFAA77", "#FFCC55", "#5566AA", 0.05, 0.0, "icon_golden"),
                ("phase_sunset", "Sunset", 17.5, 18.5,
                 "The sun sets with vibrant colors.",
                 "#FF7744", "#FF8833", "#6677BB", 0.08, 0.1, "icon_sunset"),
                ("phase_dusk", "Dusk", 18.5, 19.5,
                 "Light fades after sunset.",
                 "#554477", "#776655", "#7788CC", 0.06, 0.3, "icon_dusk"),
                ("phase_evening", "Evening", 19.5, 21.0,
                 "Early night with residual light.",
                 "#332255", "#445577", "#8899DD", 0.04, 0.6, "icon_evening"),
                ("phase_night", "Night", 21.0, 24.0,
                 "Full night with moon and stars.",
                 "#1a1a3e", "#223366", "#8899FF", 0.02, 1.0, "icon_night"),
            ]

            for pid, name, start, end, desc, amb, sun, moon, fog, stars, icon in phases_data:
                phase = AtmosphericPhaseDefinition(
                    phase_id=pid, name=name, start_hour=start, end_hour=end,
                    description=desc, ambient_color=amb, sun_color=sun,
                    moon_color=moon, fog_density=fog, star_visibility=stars,
                    icon=icon,
                )
                self._phases[pid] = phase

            profiles_data = [
                ("lp_dawn", "Dawn Lighting", 6.0, 0.4, 0.5, "#4a3a5e", "#886644",
                 "#6677BB", 0.8, 1.2, 0.6, "#AA8899", 0.08, "#554477", "#FF9966"),
                ("lp_morning", "Morning Lighting", 9.0, 0.8, 1.0, "#87CEEB",
                 "#FFFFCC", "#445599", 0.5, 1.0, 0.8, "#CCCCCC", 0.02, "#87CEEB", "#FFE4B5"),
                ("lp_midday", "Midday Lighting", 12.0, 1.0, 1.2, "#AAEEFF",
                 "#FFFFFF", "#334488", 0.3, 0.9, 1.0, "#DDDDDD", 0.01, "#87CEEB", "#FFF8DC"),
                ("lp_afternoon", "Afternoon Lighting", 15.0, 0.9, 1.0, "#99DDFF",
                 "#FFEEBB", "#445599", 0.5, 1.0, 0.8, "#CCCCCC", 0.02, "#87CEEB", "#FFE4B5"),
                ("lp_sunset", "Sunset Lighting", 18.0, 0.5, 0.8, "#FF7744",
                 "#FF8833", "#6677BB", 0.7, 1.1, 0.7, "#FF9966", 0.08, "#FF7744", "#FFAA44"),
                ("lp_night", "Night Lighting", 22.0, 0.15, 0.2, "#1a1a3e",
                 "#223366", "#8899FF", 0.9, 1.5, 0.4, "#223366", 0.02, "#1a1a2e", "#223366"),
            ]

            for pid, name, hour, ambi, dir_int, amb_c, sun_c, moon_c, shadow, exp, bloom, fog_c, fog_d, sky, horizon in profiles_data:
                profile = LightingProfile(
                    profile_id=pid, name=name, hour=hour,
                    ambient_intensity=ambi, directional_intensity=dir_int,
                    ambient_color=amb_c, sun_color=sun_c, moon_color=moon_c,
                    shadow_softness=shadow, exposure=exp, bloom_threshold=bloom,
                    fog_color=fog_c, fog_density=fog_d,
                    sky_tint=sky, horizon_tint=horizon,
                )
                self._lighting_profiles[pid] = profile

            triggers_data = [
                ("trg_dawn_chorus", "Dawn Chorus", 5.5, " Birds begin singing at first light.",
                 "ambient", {"sound_id": "dawn_chorus", "volume": 0.3}),
                ("trg_shop_open", "Shops Open", 8.0, " NPC shops open for business.",
                 "world", {"action": "open_shops"}),
                ("trg_noon_bell", "Noon Bell", 12.0, " The town bell rings at noon.",
                 "sound", {"sound_id": "noon_bell", "volume": 0.5}),
                ("trg_sunset_festival", "Sunset Festival", 18.0, " Festival begins at sunset.",
                 "world", {"action": "start_festival", "festival_id": "sunset"}),
                ("trg_night_creatures", "Night Creatures Spawn", 21.0, " Nocturnal creatures appear.",
                 "spawn", {"table_id": "nocturnal_table", "count": 10}),
                ("trg_midnight_reset", "Midnight Reset", 0.0, " Daily quests and resources reset.",
                 "world", {"action": "daily_reset"}),
            ]

            for tid, name, hour, desc, atype, payload in triggers_data:
                trigger = TimeTrigger(
                    trigger_id=tid, name=name, fire_hour=hour,
                    description=desc, action_type=atype, action_payload=payload,
                )
                self._triggers[tid] = trigger

            weather_data = [
                ("wm_clear", WeatherModifier.CLEAR.value, 1.0, 1.0, 1.0, 1.0, "", "Clear skies"),
                ("wm_cloudy", WeatherModifier.CLOUDY.value, 0.8, 0.7, 1.2, 0.8, "#999999", "Scattered clouds"),
                ("wm_overcast", WeatherModifier.OVERCAST.value, 0.6, 0.4, 1.5, 0.5, "#777777", "Heavy cloud cover"),
                ("wm_rain", WeatherModifier.RAIN.value, 0.5, 0.3, 2.0, 0.3, "#666677", "Rainfall"),
                ("wm_storm", WeatherModifier.STORM.value, 0.3, 0.2, 3.0, 0.1, "#445566", "Thunderstorm"),
                ("wm_fog", WeatherModifier.FOG.value, 0.7, 0.5, 5.0, 0.2, "#AAAAAA", "Dense fog"),
            ]

            for mid, weather, amb_m, dir_m, fog_m, star_m, tint, desc in weather_data:
                modifier = WeatherModifierEntry(
                    modifier_id=mid, weather=weather,
                    ambient_multiplier=amb_m, directional_multiplier=dir_m,
                    fog_multiplier=fog_m, star_visibility_multiplier=star_m,
                    sky_tint_override=tint, description=desc,
                )
                self._weather_modifiers[mid] = modifier

            aurora1 = AuroraInstance(
                aurora_id="aurora_northern_01",
                name="Northern Lights",
                intensity=0.7,
                color_primary="#00FF66",
                color_secondary="#AA66FF",
                wave_speed=0.8,
                wave_amplitude=0.4,
                duration=7200.0,
            )
            self._auroras[aurora1.aurora_id] = aurora1

            self._update_stats()
            self._initialized = True

    def _log_event(self, kind: str, details: Dict[str, Any],
                   phase_id: str = "", trigger_id: str = "",
                   event_id_ref: str = "", aurora_id: str = "",
                   description: str = "") -> None:
        self._event_counter += 1
        ev = AtmosphericCycleEvent(
            event_id=f"dnev_{self._event_counter:06d}",
            kind=kind, timestamp=_now(),
            phase_id=phase_id, trigger_id=trigger_id,
            event_id_ref=event_id_ref, aurora_id=aurora_id,
            description=description, details=details,
        )
        self._events.append(ev)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _update_stats(self) -> None:
        self._stats.total_phases = len(self._phases)
        self._stats.total_lighting_profiles = len(self._lighting_profiles)
        self._stats.total_triggers = len(self._triggers)
        self._stats.total_scheduled_events = len(self._scheduled_events)
        self._stats.total_weather_modifiers = len(self._weather_modifiers)
        self._stats.current_day = self._current_day
        self._stats.tick_count = self._tick_count

    # ------------------------------------------------------------------
    # Phase Management
    # ------------------------------------------------------------------

    def register_phase(self, phase_id: str, name: str, start_hour: float,
                       end_hour: float, description: str = "",
                       ambient_color: str = "#FFFFFF", sun_color: str = "#FFFFAA",
                       moon_color: str = "#AABBFF", fog_density: float = 0.0,
                       star_visibility: float = 0.0, icon: str = ""
                       ) -> Tuple[bool, str, Optional[AtmosphericPhaseDefinition]]:
        with _LOCK:
            if phase_id in self._phases:
                return False, "already_exists", self._phases[phase_id]
            if len(self._phases) >= _MAX_PHASES:
                return False, "capacity_reached", None
            phase = AtmosphericPhaseDefinition(
                phase_id=phase_id, name=name, start_hour=start_hour,
                end_hour=end_hour, description=description,
                ambient_color=ambient_color, sun_color=sun_color,
                moon_color=moon_color, fog_density=fog_density,
                star_visibility=star_visibility, icon=icon,
            )
            self._phases[phase_id] = phase
            self._log_event(AtmosphericEventKind.PHASE_REGISTERED.value,
                            {"name": name, "start": start_hour, "end": end_hour},
                            phase_id=phase_id, description=name)
            self._update_stats()
            return True, "registered", phase

    def remove_phase(self, phase_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if phase_id not in self._phases:
                return False, "not_found"
            del self._phases[phase_id]
            self._log_event(AtmosphericEventKind.PHASE_REMOVED.value,
                            {"phase_id": phase_id}, phase_id=phase_id)
            self._update_stats()
            return True, "removed"

    def get_phase(self, phase_id: str) -> Optional[AtmosphericPhaseDefinition]:
        with _LOCK:
            return self._phases.get(phase_id)

    def list_phases(self) -> List[AtmosphericPhaseDefinition]:
        with _LOCK:
            return sorted(self._phases.values(), key=lambda p: p.start_hour)

    def get_current_phase(self) -> Optional[AtmosphericPhaseDefinition]:
        with _LOCK:
            hour = self._current_hour % 24.0
            for phase in self._phases.values():
                if phase.start_hour <= phase.end_hour:
                    if phase.start_hour <= hour < phase.end_hour:
                        return phase
                else:
                    if hour >= phase.start_hour or hour < phase.end_hour:
                        return phase
            return None

    # ------------------------------------------------------------------
    # Lighting Profiles
    # ------------------------------------------------------------------

    def register_lighting_profile(self, profile_id: str, name: str, hour: float,
                                  ambient_intensity: float = 1.0,
                                  directional_intensity: float = 1.0,
                                  ambient_color: str = "#FFFFFF",
                                  sun_color: str = "#FFFFAA",
                                  moon_color: str = "#AABBFF",
                                  shadow_softness: float = 0.5,
                                  exposure: float = 1.0,
                                  bloom_threshold: float = 0.8,
                                  fog_color: str = "#CCCCCC",
                                  fog_density: float = 0.0,
                                  sky_tint: str = "#87CEEB",
                                  horizon_tint: str = "#FFE4B5",
                                  description: str = ""
                                  ) -> Tuple[bool, str, Optional[LightingProfile]]:
        with _LOCK:
            if profile_id in self._lighting_profiles:
                return False, "already_exists", self._lighting_profiles[profile_id]
            if len(self._lighting_profiles) >= _MAX_LIGHTING_PROFILES:
                return False, "capacity_reached", None
            profile = LightingProfile(
                profile_id=profile_id, name=name, hour=hour,
                ambient_intensity=ambient_intensity,
                directional_intensity=directional_intensity,
                ambient_color=ambient_color, sun_color=sun_color,
                moon_color=moon_color, shadow_softness=shadow_softness,
                exposure=exposure, bloom_threshold=bloom_threshold,
                fog_color=fog_color, fog_density=fog_density,
                sky_tint=sky_tint, horizon_tint=horizon_tint,
                description=description,
            )
            self._lighting_profiles[profile_id] = profile
            self._log_event(AtmosphericEventKind.LIGHTING_PROFILE_REGISTERED.value,
                            {"name": name, "hour": hour})
            self._update_stats()
            return True, "registered", profile

    def get_lighting_profile(self, profile_id: str) -> Optional[LightingProfile]:
        with _LOCK:
            return self._lighting_profiles.get(profile_id)

    def list_lighting_profiles(self) -> List[LightingProfile]:
        with _LOCK:
            return sorted(self._lighting_profiles.values(), key=lambda p: p.hour)

    def get_current_lighting(self) -> Dict[str, Any]:
        with _LOCK:
            hour = self._current_hour % 24.0
            profiles = sorted(self._lighting_profiles.values(), key=lambda p: p.hour)
            if not profiles:
                return {"hour": hour, "ambient_intensity": 1.0, "directional_intensity": 1.0}
            below = None
            above = None
            for p in profiles:
                if p.hour <= hour:
                    below = p
                if p.hour > hour and above is None:
                    above = p
            if below is None:
                below = profiles[-1]
            if above is None:
                above = profiles[0]
            span = (above.hour - below.hour) if above.hour > below.hour else (24.0 - below.hour + above.hour)
            t = ((hour - below.hour) / span) if span > 0 else 0.0
            t = _clamp(t, 0.0, 1.0)

            weather_mod = None
            for wm in self._weather_modifiers.values():
                if wm.weather == self._active_weather:
                    weather_mod = wm
                    break

            amb_int = below.ambient_intensity + (above.ambient_intensity - below.ambient_intensity) * t
            dir_int = below.directional_intensity + (above.directional_intensity - below.directional_intensity) * t
            fog_d = below.fog_density + (above.fog_density - below.fog_density) * t

            if weather_mod:
                amb_int *= weather_mod.ambient_multiplier
                dir_int *= weather_mod.directional_multiplier
                fog_d *= weather_mod.fog_multiplier

            sky_tint = weather_mod.sky_tint_override if weather_mod and weather_mod.sky_tint_override else below.sky_tint

            return {
                "hour": round(hour, 2),
                "ambient_intensity": round(amb_int, 3),
                "directional_intensity": round(dir_int, 3),
                "ambient_color": below.ambient_color,
                "sun_color": below.sun_color,
                "moon_color": below.moon_color,
                "shadow_softness": round(below.shadow_softness + (above.shadow_softness - below.shadow_softness) * t, 3),
                "exposure": round(below.exposure + (above.exposure - below.exposure) * t, 3),
                "bloom_threshold": round(below.bloom_threshold + (above.bloom_threshold - below.bloom_threshold) * t, 3),
                "fog_color": below.fog_color,
                "fog_density": round(fog_d, 4),
                "sky_tint": sky_tint,
                "horizon_tint": below.horizon_tint,
                "weather": self._active_weather,
            }

    # ------------------------------------------------------------------
    # Time Management
    # ------------------------------------------------------------------

    def get_current_time(self) -> Dict[str, Any]:
        with _LOCK:
            hour = self._current_hour % 24.0
            phase = self.get_current_phase()
            return {
                "hour": round(hour, 2),
                "day": self._current_day,
                "phase_id": phase.phase_id if phase else "",
                "phase_name": phase.name if phase else "",
                "weather": self._active_weather,
            }

    def set_current_time(self, hour: float, day: int = 0) -> Tuple[bool, str, Dict[str, Any]]:
        with _LOCK:
            self._current_hour = _clamp(hour % 24.0, 0.0, 24.0)
            if day > 0:
                self._current_day = day
            phase = self.get_current_phase()
            result = {
                "hour": round(self._current_hour, 2),
                "day": self._current_day,
                "phase_id": phase.phase_id if phase else "",
                "phase_name": phase.name if phase else "",
            }
            self._log_event(AtmosphericEventKind.TIME_SET.value,
                            {"hour": self._current_hour, "day": self._current_day})
            self._update_stats()
            return True, "set", result

    def advance_time(self, hours: float) -> Tuple[bool, str, Dict[str, Any]]:
        with _LOCK:
            old_hour = self._current_hour
            old_day = self._current_day
            self._current_hour += hours
            while self._current_hour >= 24.0:
                self._current_hour -= 24.0
                self._current_day += 1
            self._check_triggers(old_hour, self._current_hour, old_day, self._current_day)
            self._check_scheduled_events()
            phase = self.get_current_phase()
            result = {
                "hour": round(self._current_hour, 2),
                "day": self._current_day,
                "phase_id": phase.phase_id if phase else "",
                "phase_name": phase.name if phase else "",
                "advanced_hours": hours,
            }
            self._log_event(AtmosphericEventKind.TIME_ADVANCED.value,
                            {"hours": hours, "new_hour": self._current_hour,
                             "new_day": self._current_day})
            self._update_stats()
            return True, "advanced", result

    # ------------------------------------------------------------------
    # Celestial Positioning
    # ------------------------------------------------------------------

    def get_celestial_position(self, body: str) -> CelestialPosition:
        with _LOCK:
            hour = self._current_hour % 24.0
            if body == CelestialBodyType.SUN.value:
                return self._compute_sun_position(hour)
            elif body == CelestialBodyType.MOON.value:
                return self._compute_moon_position(hour)
            elif body == CelestialBodyType.STARS.value:
                phase = self.get_current_phase()
                visibility = phase.star_visibility if phase else 0.0
                return CelestialPosition(
                    body=CelestialBodyType.STARS.value,
                    azimuth=0.0, altitude=90.0,
                    visible=visibility > 0.1,
                    intensity=visibility,
                    color="#FFFFFF",
                )
            return CelestialPosition(body=body)

    def _compute_sun_position(self, hour: float) -> CelestialPosition:
        sun_angle = ((hour - 6.0) / 12.0) * math.pi
        altitude = math.sin(sun_angle) * 90.0
        azimuth = ((hour - 6.0) / 12.0) * 180.0
        visible = 6.0 <= hour <= 18.0
        intensity = max(0.0, math.sin(sun_angle)) if visible else 0.0
        phase = self.get_current_phase()
        color = phase.sun_color if phase else "#FFFFAA"
        return CelestialPosition(
            body=CelestialBodyType.SUN.value,
            azimuth=round(azimuth, 2),
            altitude=round(altitude, 2),
            visible=visible,
            intensity=round(intensity, 3),
            color=color,
        )

    def _compute_moon_position(self, hour: float) -> CelestialPosition:
        moon_angle = ((hour - 18.0) / 12.0) * math.pi
        if hour < 6.0:
            moon_angle = ((hour + 6.0) / 12.0) * math.pi
        altitude = math.sin(moon_angle) * 90.0
        azimuth = ((hour - 18.0) / 12.0) * 180.0
        if hour < 6.0:
            azimuth = 180.0 + (hour / 6.0) * 90.0
        visible = hour >= 18.0 or hour < 6.0
        intensity = max(0.0, math.sin(moon_angle)) if visible else 0.0
        phase = self.get_current_phase()
        color = phase.moon_color if phase else "#AABBFF"
        return CelestialPosition(
            body=CelestialBodyType.MOON.value,
            azimuth=round(azimuth, 2),
            altitude=round(altitude, 2),
            visible=visible,
            intensity=round(intensity, 3),
            color=color,
        )

    def get_sun_position(self) -> CelestialPosition:
        with _LOCK:
            return self._compute_sun_position(self._current_hour % 24.0)

    def get_moon_position(self) -> CelestialPosition:
        with _LOCK:
            return self._compute_moon_position(self._current_hour % 24.0)

    # ------------------------------------------------------------------
    # Triggers
    # ------------------------------------------------------------------

    def register_trigger(self, trigger_id: str, name: str, fire_hour: float,
                         description: str = "", repeat_daily: bool = True,
                         action_type: str = "event",
                         action_payload: Optional[Dict[str, Any]] = None
                         ) -> Tuple[bool, str, Optional[TimeTrigger]]:
        with _LOCK:
            if trigger_id in self._triggers:
                return False, "already_exists", self._triggers[trigger_id]
            if len(self._triggers) >= _MAX_TRIGGERS:
                return False, "capacity_reached", None
            trigger = TimeTrigger(
                trigger_id=trigger_id, name=name, fire_hour=fire_hour,
                description=description, repeat_daily=repeat_daily,
                action_type=action_type, action_payload=action_payload or {},
            )
            self._triggers[trigger_id] = trigger
            self._log_event(AtmosphericEventKind.TRIGGER_REGISTERED.value,
                            {"name": name, "fire_hour": fire_hour},
                            trigger_id=trigger_id)
            self._update_stats()
            return True, "registered", trigger

    def remove_trigger(self, trigger_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if trigger_id not in self._triggers:
                return False, "not_found"
            del self._triggers[trigger_id]
            self._log_event(AtmosphericEventKind.TRIGGER_REMOVED.value,
                            {"trigger_id": trigger_id}, trigger_id=trigger_id)
            self._update_stats()
            return True, "removed"

    def get_trigger(self, trigger_id: str) -> Optional[TimeTrigger]:
        with _LOCK:
            return self._triggers.get(trigger_id)

    def list_triggers(self, enabled_only: bool = False) -> List[TimeTrigger]:
        with _LOCK:
            results = list(self._triggers.values())
            if enabled_only:
                results = [t for t in results if t.enabled]
            return sorted(results, key=lambda t: t.fire_hour)

    def _check_triggers(self, old_hour: float, new_hour: float,
                        old_day: int, new_day: int) -> None:
        fired_any = False
        for trigger in self._triggers.values():
            if not trigger.enabled:
                continue
            should_fire = False
            if old_day < new_day:
                if old_hour < trigger.fire_hour:
                    pass
                if trigger.fire_hour <= new_hour or trigger.fire_hour >= old_hour:
                    should_fire = True
            else:
                if old_hour <= trigger.fire_hour <= new_hour:
                    should_fire = True
            if should_fire and trigger.last_fired_date < new_day:
                trigger.last_fired_date = new_day
                self._log_event(AtmosphericEventKind.TRIGGER_FIRED.value,
                                {"action_type": trigger.action_type,
                                 "payload": trigger.action_payload},
                                trigger_id=trigger.trigger_id,
                                description=trigger.name)
                self._stats.total_triggers_fired += 1
                fired_any = True
        if fired_any:
            self._update_stats()

    # ------------------------------------------------------------------
    # Scheduled Events
    # ------------------------------------------------------------------

    def schedule_event(self, name: str, fire_time: float,
                       description: str = "", event_type: str = "world",
                       payload: Optional[Dict[str, Any]] = None,
                       recurring: bool = False,
                       recurring_interval_hours: float = 24.0
                       ) -> Tuple[bool, str, Optional[ScheduledEvent]]:
        with _LOCK:
            if len(self._scheduled_events) >= _MAX_SCHEDULED_EVENTS:
                return False, "capacity_reached", None
            event_id = _new_id("sched")
            event = ScheduledEvent(
                event_id=event_id, name=name, fire_time=fire_time,
                description=description, event_type=event_type,
                payload=payload or {}, recurring=recurring,
                recurring_interval_hours=recurring_interval_hours,
            )
            self._scheduled_events[event_id] = event
            self._log_event(AtmosphericEventKind.EVENT_SCHEDULED.value,
                            {"name": name, "fire_time": fire_time},
                            event_id_ref=event_id)
            self._update_stats()
            return True, "scheduled", event

    def cancel_event(self, event_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if event_id not in self._scheduled_events:
                return False, "not_found"
            del self._scheduled_events[event_id]
            self._log_event(AtmosphericEventKind.EVENT_CANCELLED.value,
                            {"event_id": event_id}, event_id_ref=event_id)
            self._update_stats()
            return True, "cancelled"

    def list_scheduled_events(self, include_fired: bool = False) -> List[ScheduledEvent]:
        with _LOCK:
            results = list(self._scheduled_events.values())
            if not include_fired:
                results = [e for e in results if not e.fired]
            return sorted(results, key=lambda e: e.fire_time)

    def _check_scheduled_events(self) -> None:
        current_epoch = _now()
        fired_any = False
        for event in self._scheduled_events.values():
            if event.fired:
                continue
            if current_epoch >= event.fire_time:
                event.fired = True
                self._log_event(AtmosphericEventKind.EVENT_FIRED.value,
                                {"name": event.name, "event_type": event.event_type,
                                 "payload": event.payload},
                                event_id_ref=event.event_id,
                                description=event.name)
                self._stats.total_events_fired += 1
                fired_any = True
                if event.recurring:
                    event.fire_time = current_epoch + event.recurring_interval_hours * 3600.0
                    event.fired = False
        if fired_any:
            self._update_stats()

    # ------------------------------------------------------------------
    # Weather Modifiers
    # ------------------------------------------------------------------

    def register_weather_modifier(self, modifier_id: str, weather: str,
                                  ambient_multiplier: float = 1.0,
                                  directional_multiplier: float = 1.0,
                                  fog_multiplier: float = 1.0,
                                  star_visibility_multiplier: float = 1.0,
                                  sky_tint_override: str = "",
                                  description: str = ""
                                  ) -> Tuple[bool, str, Optional[WeatherModifierEntry]]:
        with _LOCK:
            if modifier_id in self._weather_modifiers:
                return False, "already_exists", self._weather_modifiers[modifier_id]
            if len(self._weather_modifiers) >= _MAX_WEATHER_MODIFIERS:
                return False, "capacity_reached", None
            modifier = WeatherModifierEntry(
                modifier_id=modifier_id, weather=weather,
                ambient_multiplier=ambient_multiplier,
                directional_multiplier=directional_multiplier,
                fog_multiplier=fog_multiplier,
                star_visibility_multiplier=star_visibility_multiplier,
                sky_tint_override=sky_tint_override,
                description=description,
            )
            self._weather_modifiers[modifier_id] = modifier
            self._log_event(AtmosphericEventKind.WEATHER_MODIFIER_REGISTERED.value,
                            {"weather": weather, "modifier_id": modifier_id})
            self._update_stats()
            return True, "registered", modifier

    def remove_weather_modifier(self, modifier_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if modifier_id not in self._weather_modifiers:
                return False, "not_found"
            del self._weather_modifiers[modifier_id]
            self._log_event(AtmosphericEventKind.WEATHER_MODIFIER_REMOVED.value,
                            {"modifier_id": modifier_id})
            self._update_stats()
            return True, "removed"

    def set_active_weather(self, weather: str) -> Tuple[bool, str]:
        with _LOCK:
            self._active_weather = weather
            return True, "set"

    def get_active_weather(self) -> str:
        with _LOCK:
            return self._active_weather

    # ------------------------------------------------------------------
    # Auroras
    # ------------------------------------------------------------------

    def spawn_aurora(self, name: str, intensity: float = 0.5,
                     color_primary: str = "#00FF66",
                     color_secondary: str = "#AA66FF",
                     wave_speed: float = 1.0, wave_amplitude: float = 0.3,
                     duration: float = 3600.0
                     ) -> Tuple[bool, str, Optional[AuroraInstance]]:
        with _LOCK:
            if len(self._auroras) >= _MAX_AURORAS:
                return False, "capacity_reached", None
            aurora_id = _new_id("aurora")
            aurora = AuroraInstance(
                aurora_id=aurora_id, name=name, intensity=intensity,
                color_primary=color_primary, color_secondary=color_secondary,
                wave_speed=wave_speed, wave_amplitude=wave_amplitude,
                duration=duration,
            )
            self._auroras[aurora_id] = aurora
            self._stats.total_auroras_spawned += 1
            self._log_event(AtmosphericEventKind.AURORA_SPAWNED.value,
                            {"name": name, "intensity": intensity},
                            aurora_id=aurora_id)
            self._update_stats()
            return True, "spawned", aurora

    def dismiss_aurora(self, aurora_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if aurora_id not in self._auroras:
                return False, "not_found"
            self._auroras[aurora_id].active = False
            del self._auroras[aurora_id]
            self._log_event(AtmosphericEventKind.AURORA_DISMISSED.value,
                            {"aurora_id": aurora_id}, aurora_id=aurora_id)
            self._update_stats()
            return True, "dismissed"

    def get_active_auroras(self) -> List[AuroraInstance]:
        with _LOCK:
            return [a for a in self._auroras.values() if a.active]

    # ------------------------------------------------------------------
    # Tick / Config / Status
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            hours_per_second = 24.0 / self._config.day_length_real_seconds
            hours_advanced = hours_per_second * dt
            old_hour = self._current_hour
            old_day = self._current_day
            self._current_hour += hours_advanced
            while self._current_hour >= 24.0:
                self._current_hour -= 24.0
                self._current_day += 1
            self._check_triggers(old_hour, self._current_hour, old_day, self._current_day)
            self._check_scheduled_events()
            current_time = _now()
            expired = [aid for aid, a in self._auroras.items()
                       if current_time - a.spawned_at > a.duration]
            for aid in expired:
                self._auroras[aid].active = False
                del self._auroras[aid]
            if self._tick_count % 60 == 0:
                self._log_event(AtmosphericEventKind.TICK.value,
                                {"tick": self._tick_count, "dt": dt,
                                 "hour": self._current_hour, "day": self._current_day})
            self._update_stats()
            return {"tick_count": self._tick_count,
                    "current_hour": round(self._current_hour, 2),
                    "current_day": self._current_day}

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, AtmosphericCycleConfig]:
        with _LOCK:
            for k, v in config.items():
                if hasattr(self._config, k):
                    setattr(self._config, k, v)
            self._log_event(AtmosphericEventKind.CONFIG_UPDATED.value,
                            {"keys": list(config.keys())})
            return True, "updated", self._config

    def get_config(self) -> AtmosphericCycleConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 100, kind: str = "") -> List[AtmosphericCycleEvent]:
        with _LOCK:
            results = list(self._events)
            if kind:
                results = [e for e in results if e.kind == kind]
            if limit > 0:
                results = results[-limit:]
            return results

    def get_stats(self) -> AtmosphericCycleStats:
        with _LOCK:
            self._update_stats()
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            phase = self.get_current_phase()
            return {
                "initialized": self._initialized,
                "current_hour": round(self._current_hour, 2),
                "current_day": self._current_day,
                "current_phase": phase.name if phase else "",
                "active_weather": self._active_weather,
                "total_phases": len(self._phases),
                "total_lighting_profiles": len(self._lighting_profiles),
                "total_triggers": len(self._triggers),
                "total_scheduled_events": len(self._scheduled_events),
                "total_weather_modifiers": len(self._weather_modifiers),
                "active_auroras": len([a for a in self._auroras.values() if a.active]),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> AtmosphericCycleSnapshot:
        with _LOCK:
            phase = self.get_current_phase()
            sun = self.get_sun_position()
            moon = self.get_moon_position()
            lighting = self.get_current_lighting()
            auroras = [a.to_dict() for a in self._auroras.values() if a.active]
            self._update_stats()
            snap = AtmosphericCycleSnapshot(
                current_hour=round(self._current_hour, 2),
                current_phase=phase.phase_id if phase else "",
                sun_position=sun.to_dict(),
                moon_position=moon.to_dict(),
                active_lighting=lighting,
                active_auroras=auroras,
                active_weather=self._active_weather,
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )
            return snap

    def reset(self) -> Dict[str, Any]:
        with _LOCK:
            self._log_event(AtmosphericEventKind.RESET.value, {})
            self._phases.clear()
            self._lighting_profiles.clear()
            self._triggers.clear()
            self._scheduled_events.clear()
            self._weather_modifiers.clear()
            self._auroras.clear()
            self._events.clear()
            self._stats = AtmosphericCycleStats()
            self._tick_count = 0
            self._current_hour = self._config.start_hour
            self._current_day = 1
            self._active_weather = WeatherModifier.CLEAR.value
            self._initialized = False
            self._seed()
            return self.get_status()


def get_atmospheric_cycle_system() -> AtmosphericCycleSystem:
    """Factory function to get the singleton AtmosphericCycleSystem instance."""
    return AtmosphericCycleSystem.get_instance()
