"""
SparkLabs Agent - Atmospheric Weather Director

An atmospheric and weather orchestration agent for the SparkLabs
AI-native game engine. It orchestrates weather state machines toward
dramatic and emergent outcomes, schedules transitions around player
heartbeat and story arc, and seeds weather-modified gameplay
opportunities. The director fuses mood alignment, narrative beats,
and biome ecology to produce cohesive atmospheric experiences.

Architecture:
  AtmosphericWeatherDirector (singleton)
    |-- WeatherState, WeatherSchedule, WeatherBeat, MoodAlignment,
       DirectorStats, DirectorSnapshot, DirectorEvent
    |-- WeatherMood, WeatherPhase, WeatherIntensity,
       DirectorEventKind

Core Capabilities:
  - register_state / get_state / list_states / update_state /
    remove_state: weather state lifecycle with mood, intensity,
    and biome metadata.
  - register_schedule / get_schedule / list_schedules / remove_schedule:
    scheduled weather transitions that gate progression beats.
  - add_beat / get_beat / list_beats / remove_beat: narrative beats
    that trigger weather changes.
  - assess_mood: score alignment between current weather and a target
    narrative mood.
  - suggest_transition: propose a weather transition that fits the
    current narrative context.
  - advance_schedule: progress the schedule and emit state changes.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`AtmosphericWeatherDirector.get_instance` or the module-level
:func:`get_atmospheric_weather_director` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_STATES: int = 500
_MAX_SCHEDULES: int = 500
_MAX_BEATS: int = 2000
_MAX_MOOD_LOG: int = 2000
_MAX_EVENTS: int = 5000


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


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class WeatherMood(Enum):
    """Emotional mood that a weather state conveys."""
    SERENE = "serene"
    TENSE = "tense"
    OMINOUS = "ominous"
    JOYFUL = "joyful"
    MELANCHOLIC = "melancholic"
    CHAOTIC = "chaotic"
    HOPEFUL = "hopeful"
    MYSTERIOUS = "mysterious"


class WeatherPhase(Enum):
    """Phase of a weather state's lifecycle."""
    CALM = "calm"
    BUILDING = "building"
    PEAK = "peak"
    DISSIPATING = "dissipating"


class WeatherIntensity(Enum):
    """Intensity tier of a weather state."""
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    EXTREME = "extreme"


class DirectorEventKind(Enum):
    """Audit event types emitted by the atmospheric weather director."""
    STATE_REGISTERED = "state_registered"
    STATE_UPDATED = "state_updated"
    STATE_REMOVED = "state_removed"
    SCHEDULE_REGISTERED = "schedule_registered"
    SCHEDULE_REMOVED = "schedule_removed"
    BEAT_ADDED = "beat_added"
    BEAT_REMOVED = "beat_removed"
    TRANSITION_SUGGESTED = "transition_suggested"
    SCHEDULE_ADVANCED = "schedule_advanced"
    MOOD_ASSESSED = "mood_assessed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class WeatherState:
    """A discrete atmospheric state with mood and intensity."""
    state_id: str = field(default_factory=lambda: _new_id("wst"))
    name: str = ""
    description: str = ""
    mood: str = WeatherMood.SERENE.value
    phase: str = WeatherPhase.CALM.value
    intensity: str = WeatherIntensity.LIGHT.value
    precipitation: float = 0.0
    wind_speed: float = 0.0
    fog_density: float = 0.0
    cloud_cover: float = 0.0
    temperature: float = 20.0
    lighting_multiplier: float = 1.0
    visibility: float = 1.0
    ambient_color: str = "#FFFFFF"
    biome_tags: List[str] = field(default_factory=list)
    gameplay_modifiers: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherSchedule:
    """A scheduled sequence of weather transitions."""
    schedule_id: str = field(default_factory=lambda: _new_id("sch"))
    name: str = ""
    description: str = ""
    state_sequence: List[Dict[str, Any]] = field(default_factory=list)
    current_index: int = 0
    loop: bool = True
    biome_tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WeatherBeat:
    """A narrative beat that triggers a weather state transition."""
    beat_id: str = field(default_factory=lambda: _new_id("bet"))
    name: str = ""
    description: str = ""
    target_state_id: str = ""
    trigger_event: str = ""
    priority: int = 0
    duration_ms: int = 0
    fade_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MoodAlignment:
    """Result of comparing current weather mood to a target mood."""
    alignment_id: str = field(default_factory=lambda: _new_id("mal"))
    current_state_id: str = ""
    target_mood: str = WeatherMood.SERENE.value
    alignment_score: float = 0.0
    intensity_match: float = 0.0
    suggested_state_id: str = ""
    notes: str = ""
    assessed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorStats:
    """Aggregate counters for the atmospheric weather director."""
    total_states: int = 0
    total_schedules: int = 0
    total_beats: int = 0
    total_transitions_suggested: int = 0
    total_schedules_advanced: int = 0
    total_mood_assessments: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorSnapshot:
    """Immutable point-in-time capture of director state."""
    states: Dict[str, Any] = field(default_factory=dict)
    schedules: Dict[str, Any] = field(default_factory=dict)
    beats: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("aud"))
    kind: str = DirectorEventKind.STATE_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Static Lookup Tables
# ---------------------------------------------------------------------------

_MOOD_INTENSITY_PROFILE: Dict[str, Dict[str, float]] = {
    WeatherMood.SERENE.value: {"precipitation": 0.05, "wind": 0.1, "fog": 0.05, "cloud": 0.2},
    WeatherMood.TENSE.value: {"precipitation": 0.3, "wind": 0.5, "fog": 0.2, "cloud": 0.7},
    WeatherMood.OMINOUS.value: {"precipitation": 0.4, "wind": 0.6, "fog": 0.4, "cloud": 0.85},
    WeatherMood.JOYFUL.value: {"precipitation": 0.0, "wind": 0.2, "fog": 0.0, "cloud": 0.1},
    WeatherMood.MELANCHOLIC.value: {"precipitation": 0.5, "wind": 0.3, "fog": 0.3, "cloud": 0.7},
    WeatherMood.CHAOTIC.value: {"precipitation": 0.8, "wind": 0.9, "fog": 0.2, "cloud": 0.95},
    WeatherMood.HOPEFUL.value: {"precipitation": 0.15, "wind": 0.25, "fog": 0.1, "cloud": 0.4},
    WeatherMood.MYSTERIOUS.value: {"precipitation": 0.2, "wind": 0.2, "fog": 0.6, "cloud": 0.6},
}

_MOOD_AFFINITY: Dict[str, Dict[str, float]] = {
    WeatherMood.SERENE.value: {WeatherMood.HOPEFUL.value: 0.7, WeatherMood.JOYFUL.value: 0.8, WeatherMood.MELANCHOLIC.value: 0.4},
    WeatherMood.TENSE.value: {WeatherMood.OMINOUS.value: 0.8, WeatherMood.CHAOTIC.value: 0.7, WeatherMood.SERENE.value: 0.2},
    WeatherMood.OMINOUS.value: {WeatherMood.TENSE.value: 0.8, WeatherMood.MYSTERIOUS.value: 0.6, WeatherMood.CHAOTIC.value: 0.7},
    WeatherMood.JOYFUL.value: {WeatherMood.HOPEFUL.value: 0.85, WeatherMood.SERENE.value: 0.8, WeatherMood.MELANCHOLIC.value: 0.3},
    WeatherMood.MELANCHOLIC.value: {WeatherMood.MYSTERIOUS.value: 0.6, WeatherMood.SERENE.value: 0.4, WeatherMood.OMINOUS.value: 0.5},
    WeatherMood.CHAOTIC.value: {WeatherMood.TENSE.value: 0.7, WeatherMood.OMINOUS.value: 0.7, WeatherMood.SERENE.value: 0.1},
    WeatherMood.HOPEFUL.value: {WeatherMood.JOYFUL.value: 0.85, WeatherMood.SERENE.value: 0.7, WeatherMood.TENSE.value: 0.4},
    WeatherMood.MYSTERIOUS.value: {WeatherMood.OMINOUS.value: 0.6, WeatherMood.MELANCHOLIC.value: 0.6, WeatherMood.SERENE.value: 0.4},
}


# ---------------------------------------------------------------------------
# Atmospheric Weather Director Singleton
# ---------------------------------------------------------------------------


class AtmosphericWeatherDirector:
    """Singleton agent that orchestrates atmospheric weather.

    The director maintains weather states, schedules, and narrative
    beats. It assesses mood alignment, suggests transitions that fit
    the current narrative context, and advances schedules to drive
    emergent atmospheric storytelling.
    """

    _instance: Optional["AtmosphericWeatherDirector"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._states: Dict[str, WeatherState] = {}
        self._schedules: Dict[str, WeatherSchedule] = {}
        self._beats: Dict[str, WeatherBeat] = {}
        self._mood_log: List[MoodAlignment] = []
        self._transitions_suggested: int = 0
        self._schedules_advanced: int = 0
        self._audit: List[DirectorEvent] = []

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AtmosphericWeatherDirector":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_defaults()
            self._initialized = True

    def _seed_defaults(self) -> None:
        """Seed a small set of default weather states, schedule, and beat."""
        defaults = [
            ("wst_clear_skies", "Clear Skies", "Calm, sunny weather.",
             WeatherMood.SERENE, WeatherPhase.CALM, WeatherIntensity.LIGHT,
             0.0, 0.1, 0.0, 0.1, 22.0, 1.0, 1.0, "#FFF5E1", ["plains", "coast"]),
            ("wst_light_rain", "Light Rain", "Gentle rain with soft cloud cover.",
             WeatherMood.MELANCHOLIC, WeatherPhase.CALM, WeatherIntensity.LIGHT,
             0.3, 0.3, 0.1, 0.5, 16.0, 0.85, 0.85, "#B0C4DE", ["forest", "plains"]),
            ("wst_thunderstorm", "Thunderstorm", "Heavy rain, lightning, strong winds.",
             WeatherMood.CHAOTIC, WeatherPhase.PEAK, WeatherIntensity.EXTREME,
             0.9, 0.85, 0.2, 0.95, 14.0, 0.5, 0.4, "#3A4A5C", ["mountains", "coast"]),
            ("wst_dense_fog", "Dense Fog", "Mysterious low-visibility fog.",
             WeatherMood.MYSTERIOUS, WeatherPhase.BUILDING, WeatherIntensity.MODERATE,
             0.1, 0.15, 0.85, 0.6, 12.0, 0.7, 0.3, "#9FA8B5", ["swamp", "forest"]),
            ("wst_golden_hour", "Golden Hour", "Warm hopeful light at dawn or dusk.",
             WeatherMood.HOPEFUL, WeatherPhase.CALM, WeatherIntensity.LIGHT,
             0.0, 0.1, 0.0, 0.2, 19.0, 1.1, 1.0, "#FFB347", ["plains", "desert"]),
        ]
        for sid, name, desc, mood, phase, intensity, precip, wind, fog, cloud, temp, lighting, visibility, color, biomes in defaults:
            state = WeatherState(
                state_id=sid,
                name=name,
                description=desc,
                mood=mood.value,
                phase=phase.value,
                intensity=intensity.value,
                precipitation=precip,
                wind_speed=wind,
                fog_density=fog,
                cloud_cover=cloud,
                temperature=temp,
                lighting_multiplier=lighting,
                visibility=visibility,
                ambient_color=color,
                biome_tags=biomes,
            )
            self._states[sid] = state
            self._record_event(DirectorEventKind.STATE_REGISTERED, {
                "state_id": sid, "name": name,
            })

        # Default day cycle schedule
        day_schedule = WeatherSchedule(
            schedule_id="sch_day_cycle",
            name="Day Cycle",
            description="A complete day-night atmospheric progression.",
            state_sequence=[
                {"state_id": "wst_golden_hour", "duration_ms": 3600000, "fade_ms": 60000},
                {"state_id": "wst_clear_skies", "duration_ms": 14400000, "fade_ms": 120000},
                {"state_id": "wst_light_rain", "duration_ms": 7200000, "fade_ms": 180000},
                {"state_id": "wst_clear_skies", "duration_ms": 10800000, "fade_ms": 120000},
                {"state_id": "wst_golden_hour", "duration_ms": 3600000, "fade_ms": 60000},
            ],
            current_index=0,
            loop=True,
            biome_tags=["plains", "coast"],
        )
        self._schedules[day_schedule.schedule_id] = day_schedule
        self._record_event(DirectorEventKind.SCHEDULE_REGISTERED, {
            "schedule_id": day_schedule.schedule_id, "name": day_schedule.name,
        })

        # Default narrative beat
        boss_beat = WeatherBeat(
            beat_id="bet_boss_approach",
            name="Boss Approach",
            description="Weather turns ominous as the boss encounter nears.",
            target_state_id="wst_thunderstorm",
            trigger_event="boss_approach",
            priority=10,
            duration_ms=600000,
            fade_ms=30000,
        )
        self._beats[boss_beat.beat_id] = boss_beat
        self._record_event(DirectorEventKind.BEAT_ADDED, {
            "beat_id": boss_beat.beat_id, "name": boss_beat.name,
        })

    # ------------------------------------------------------------------
    # Audit Helpers
    # ------------------------------------------------------------------

    def _record_event(self, kind: DirectorEventKind, payload: Dict[str, Any]) -> None:
        event = DirectorEvent(kind=kind.value, payload=payload)
        self._audit.append(event)
        _evict_fifo_list(self._audit, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Weather State Lifecycle
    # ------------------------------------------------------------------

    def register_state(
        self,
        state_id: str = "",
        name: str = "",
        description: str = "",
        mood: str = WeatherMood.SERENE.value,
        phase: str = WeatherPhase.CALM.value,
        intensity: str = WeatherIntensity.LIGHT.value,
        precipitation: float = 0.0,
        wind_speed: float = 0.0,
        fog_density: float = 0.0,
        cloud_cover: float = 0.0,
        temperature: float = 20.0,
        lighting_multiplier: float = 1.0,
        visibility: float = 1.0,
        ambient_color: str = "#FFFFFF",
        biome_tags: Optional[List[str]] = None,
        gameplay_modifiers: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WeatherState:
        with self._lock:
            sid = state_id or _new_id("wst")
            state = WeatherState(
                state_id=sid,
                name=name,
                description=description,
                mood=mood,
                phase=phase,
                intensity=intensity,
                precipitation=_clamp(_safe_float(precipitation, 0.0), 0.0, 1.0),
                wind_speed=_clamp(_safe_float(wind_speed, 0.0), 0.0, 1.0),
                fog_density=_clamp(_safe_float(fog_density, 0.0), 0.0, 1.0),
                cloud_cover=_clamp(_safe_float(cloud_cover, 0.0), 0.0, 1.0),
                temperature=_safe_float(temperature, 20.0),
                lighting_multiplier=_safe_float(lighting_multiplier, 1.0),
                visibility=_clamp(_safe_float(visibility, 1.0), 0.0, 1.0),
                ambient_color=ambient_color,
                biome_tags=list(biome_tags or []),
                gameplay_modifiers=dict(gameplay_modifiers or {}),
                metadata=dict(metadata or {}),
            )
            self._states[sid] = state
            _evict_fifo_dict(self._states, _MAX_STATES)
            self._record_event(DirectorEventKind.STATE_REGISTERED, {
                "state_id": sid, "name": name,
            })
            return state

    def get_state(self, state_id: str) -> Optional[WeatherState]:
        with self._lock:
            return self._states.get(state_id)

    def list_states(
        self,
        mood: str = "",
        intensity: str = "",
        biome: str = "",
        limit: int = 100,
    ) -> List[WeatherState]:
        with self._lock:
            results: List[WeatherState] = []
            for state in self._states.values():
                if mood and state.mood != mood:
                    continue
                if intensity and state.intensity != intensity:
                    continue
                if biome and biome not in state.biome_tags:
                    continue
                results.append(state)
            return results[:max(0, int(limit))]

    def update_state(self, state_id: str, **kwargs: Any) -> Optional[WeatherState]:
        with self._lock:
            state = self._states.get(state_id)
            if state is None:
                return None
            for key, value in kwargs.items():
                if hasattr(state, key) and key not in ("state_id", "created_at"):
                    if key in ("precipitation", "wind_speed", "fog_density", "cloud_cover", "visibility"):
                        setattr(state, key, _clamp(_safe_float(value, getattr(state, key)), 0.0, 1.0))
                    elif key in ("temperature", "lighting_multiplier"):
                        setattr(state, key, _safe_float(value, getattr(state, key)))
                    else:
                        setattr(state, key, value)
            self._record_event(DirectorEventKind.STATE_UPDATED, {"state_id": state_id})
            return state

    def remove_state(self, state_id: str) -> bool:
        with self._lock:
            existed = self._states.pop(state_id, None) is not None
            if existed:
                self._record_event(DirectorEventKind.STATE_REMOVED, {"state_id": state_id})
            return existed

    # ------------------------------------------------------------------
    # Schedule Lifecycle
    # ------------------------------------------------------------------

    def register_schedule(
        self,
        schedule_id: str = "",
        name: str = "",
        description: str = "",
        state_sequence: Optional[List[Dict[str, Any]]] = None,
        loop: bool = True,
        biome_tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WeatherSchedule:
        with self._lock:
            sid = schedule_id or _new_id("sch")
            schedule = WeatherSchedule(
                schedule_id=sid,
                name=name,
                description=description,
                state_sequence=list(state_sequence or []),
                current_index=0,
                loop=loop,
                biome_tags=list(biome_tags or []),
                metadata=dict(metadata or {}),
            )
            self._schedules[sid] = schedule
            _evict_fifo_dict(self._schedules, _MAX_SCHEDULES)
            self._record_event(DirectorEventKind.SCHEDULE_REGISTERED, {
                "schedule_id": sid, "name": name,
            })
            return schedule

    def get_schedule(self, schedule_id: str) -> Optional[WeatherSchedule]:
        with self._lock:
            return self._schedules.get(schedule_id)

    def list_schedules(
        self,
        biome: str = "",
        limit: int = 100,
    ) -> List[WeatherSchedule]:
        with self._lock:
            results: List[WeatherSchedule] = []
            for schedule in self._schedules.values():
                if biome and biome not in schedule.biome_tags:
                    continue
                results.append(schedule)
            return results[:max(0, int(limit))]

    def remove_schedule(self, schedule_id: str) -> bool:
        with self._lock:
            existed = self._schedules.pop(schedule_id, None) is not None
            if existed:
                self._record_event(DirectorEventKind.SCHEDULE_REMOVED, {"schedule_id": schedule_id})
            return existed

    def advance_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if schedule is None or not schedule.state_sequence:
                return None
            next_index = schedule.current_index + 1
            if next_index >= len(schedule.state_sequence):
                if schedule.loop:
                    next_index = 0
                else:
                    return {
                        "schedule_id": schedule_id,
                        "completed": True,
                        "current_index": schedule.current_index,
                        "current_step": schedule.state_sequence[schedule.current_index],
                    }
            schedule.current_index = next_index
            self._schedules_advanced += 1
            current_step = schedule.state_sequence[next_index]
            self._record_event(DirectorEventKind.SCHEDULE_ADVANCED, {
                "schedule_id": schedule_id,
                "current_index": next_index,
            })
            return {
                "schedule_id": schedule_id,
                "completed": False,
                "current_index": next_index,
                "current_step": current_step,
            }

    # ------------------------------------------------------------------
    # Narrative Beats
    # ------------------------------------------------------------------

    def add_beat(
        self,
        beat_id: str = "",
        name: str = "",
        description: str = "",
        target_state_id: str = "",
        trigger_event: str = "",
        priority: int = 0,
        duration_ms: int = 0,
        fade_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WeatherBeat:
        with self._lock:
            bid = beat_id or _new_id("bet")
            beat = WeatherBeat(
                beat_id=bid,
                name=name,
                description=description,
                target_state_id=target_state_id,
                trigger_event=trigger_event,
                priority=_safe_int(priority, 0),
                duration_ms=_safe_int(duration_ms, 0),
                fade_ms=_safe_int(fade_ms, 0),
                metadata=dict(metadata or {}),
            )
            self._beats[bid] = beat
            _evict_fifo_dict(self._beats, _MAX_BEATS)
            self._record_event(DirectorEventKind.BEAT_ADDED, {
                "beat_id": bid, "name": name,
            })
            return beat

    def get_beat(self, beat_id: str) -> Optional[WeatherBeat]:
        with self._lock:
            return self._beats.get(beat_id)

    def list_beats(
        self,
        trigger_event: str = "",
        target_state_id: str = "",
        limit: int = 100,
    ) -> List[WeatherBeat]:
        with self._lock:
            results: List[WeatherBeat] = []
            for beat in self._beats.values():
                if trigger_event and beat.trigger_event != trigger_event:
                    continue
                if target_state_id and beat.target_state_id != target_state_id:
                    continue
                results.append(beat)
            # Sort by priority descending
            results.sort(key=lambda b: b.priority, reverse=True)
            return results[:max(0, int(limit))]

    def remove_beat(self, beat_id: str) -> bool:
        with self._lock:
            existed = self._beats.pop(beat_id, None) is not None
            if existed:
                self._record_event(DirectorEventKind.BEAT_REMOVED, {"beat_id": beat_id})
            return existed

    # ------------------------------------------------------------------
    # Mood Intelligence
    # ------------------------------------------------------------------

    def assess_mood(
        self,
        current_state_id: str,
        target_mood: str,
    ) -> Optional[MoodAlignment]:
        """Score alignment between current weather and a target mood."""
        with self._lock:
            current = self._states.get(current_state_id)
            if current is None:
                return None
            current_mood = current.mood
            if current_mood == target_mood:
                alignment_score = 1.0
            else:
                affinity = _MOOD_AFFINITY.get(current_mood, {})
                alignment_score = affinity.get(target_mood, 0.2)
            # Intensity match: extreme moods prefer heavy/intense weather
            target_profile = _MOOD_INTENSITY_PROFILE.get(target_mood, {})
            intensity_match = 1.0 - (
                abs(current.precipitation - target_profile.get("precipitation", 0.0))
                + abs(current.wind_speed - target_profile.get("wind", 0.0))
                + abs(current.fog_density - target_profile.get("fog", 0.0))
                + abs(current.cloud_cover - target_profile.get("cloud", 0.0))
            ) / 4.0
            intensity_match = _clamp(intensity_match)
            # Suggest best state for target mood
            suggested_state_id = self._find_best_state_for_mood(target_mood, exclude_id=current_state_id)
            alignment = MoodAlignment(
                current_state_id=current_state_id,
                target_mood=target_mood,
                alignment_score=round(alignment_score, 3),
                intensity_match=round(intensity_match, 3),
                suggested_state_id=suggested_state_id,
                notes=self._build_mood_notes(alignment_score, intensity_match, suggested_state_id),
            )
            self._mood_log.append(alignment)
            _evict_fifo_list(self._mood_log, _MAX_MOOD_LOG)
            self._record_event(DirectorEventKind.MOOD_ASSESSED, {
                "current_state_id": current_state_id,
                "target_mood": target_mood,
                "alignment_score": alignment.alignment_score,
            })
            return alignment

    def _find_best_state_for_mood(self, mood: str, exclude_id: str = "") -> str:
        best_id = ""
        best_score = -1.0
        for sid, state in self._states.items():
            if sid == exclude_id:
                continue
            if state.mood == mood:
                # Direct match — prefer higher intensity for chaotic/ominous, lower for serene
                target_profile = _MOOD_INTENSITY_PROFILE.get(mood, {})
                fit = 1.0 - (
                    abs(state.precipitation - target_profile.get("precipitation", 0.0))
                    + abs(state.wind_speed - target_profile.get("wind", 0.0))
                    + abs(state.fog_density - target_profile.get("fog", 0.0))
                    + abs(state.cloud_cover - target_profile.get("cloud", 0.0))
                ) / 4.0
                if fit > best_score:
                    best_score = fit
                    best_id = sid
            else:
                affinity = _MOOD_AFFINITY.get(state.mood, {}).get(mood, 0.0)
                if affinity > best_score:
                    best_score = affinity
                    best_id = sid
        return best_id

    def _build_mood_notes(self, alignment: float, intensity: float, suggested: str) -> str:
        if alignment >= 0.8 and intensity >= 0.7:
            return "Excellent match — no transition needed."
        if alignment >= 0.5:
            return "Acceptable match; transition optional."
        if suggested:
            return f"Mismatch detected; consider transitioning to '{suggested}'."
        return "Mismatch detected; no suitable alternative state available."

    def suggest_transition(
        self,
        current_state_id: str,
        target_mood: str = "",
        narrative_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Propose a weather transition that fits the narrative context."""
        with self._lock:
            current = self._states.get(current_state_id)
            if current is None:
                return None
            narrative_context = narrative_context or {}
            effective_mood = target_mood or narrative_context.get("mood", "")
            if not effective_mood:
                # Infer mood from narrative beat if provided
                beat_event = narrative_context.get("trigger_event", "")
                if beat_event:
                    for beat in self._beats.values():
                        if beat.trigger_event == beat_event:
                            target_state = self._states.get(beat.target_state_id)
                            if target_state is not None:
                                effective_mood = target_state.mood
                                break
            if not effective_mood:
                effective_mood = WeatherMood.SERENE.value
            suggested_state_id = self._find_best_state_for_mood(effective_mood, exclude_id=current_state_id)
            suggested_state = self._states.get(suggested_state_id, None) if suggested_state_id else None
            self._transitions_suggested += 1
            self._record_event(DirectorEventKind.TRANSITION_SUGGESTED, {
                "current_state_id": current_state_id,
                "target_mood": effective_mood,
                "suggested_state_id": suggested_state_id,
            })
            return {
                "current_state_id": current_state_id,
                "current_mood": current.mood,
                "target_mood": effective_mood,
                "suggested_state_id": suggested_state_id,
                "suggested_state": suggested_state.to_dict() if suggested_state else None,
                "narrative_context": narrative_context,
            }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[DirectorEvent]:
        with self._lock:
            return list(self._audit[:max(0, int(limit))])

    def get_stats(self) -> DirectorStats:
        with self._lock:
            return DirectorStats(
                total_states=len(self._states),
                total_schedules=len(self._schedules),
                total_beats=len(self._beats),
                total_transitions_suggested=self._transitions_suggested,
                total_schedules_advanced=self._schedules_advanced,
                total_mood_assessments=len(self._mood_log),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "states": len(self._states),
                "schedules": len(self._schedules),
                "beats": len(self._beats),
                "mood_assessments": len(self._mood_log),
                "transitions_suggested": self._transitions_suggested,
                "schedules_advanced": self._schedules_advanced,
                "events": len(self._audit),
            }

    def get_snapshot(self) -> DirectorSnapshot:
        with self._lock:
            return DirectorSnapshot(
                states={sid: s.to_dict() for sid, s in self._states.items()},
                schedules={sid: s.to_dict() for sid, s in self._schedules.items()},
                beats={bid: b.to_dict() for bid, b in self._beats.items()},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._states.clear()
            self._schedules.clear()
            self._beats.clear()
            self._mood_log.clear()
            self._transitions_suggested = 0
            self._schedules_advanced = 0
            self._audit.clear()
            self._seed_defaults()
            self._initialized = True


# ---------------------------------------------------------------------------
# Module Factory
# ---------------------------------------------------------------------------


def get_atmospheric_weather_director() -> AtmosphericWeatherDirector:
    return AtmosphericWeatherDirector.get_instance()
