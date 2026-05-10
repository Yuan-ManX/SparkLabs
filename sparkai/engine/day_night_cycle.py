"""
SparkLabs Engine - Day/Night Cycle

Dynamic time-of-day system with smooth phase transitions,
lighting parameters, scheduled time-based events, and
game-world state integration. Supports configurable
day length, phase duration ratios, and custom event
scheduling tied to specific times or phases.

Architecture:
  DayNightCycle
    |-- TimeTracker (accumulated game time with configurable speed)
    |-- PhaseEngine (dawn/day/dusk/night transition logic)
    |-- LightingParameters (ambient color, intensity per phase)
    |-- EventScheduler (time-triggered world state changes)
    |-- WorldStateBridge (integration with other subsystems)

Phases:
  - DAWN: sunrise transition, low warm light
  - DAY: full illumination, neutral white light
  - DUSK: sunset transition, warm orange dimming
  - NIGHT: minimal ambient, cool blue moonlight
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class TimePhase(Enum):
    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"


@dataclass
class LightingParams:
    ambient_color: Tuple[float, float, float] = (0.2, 0.2, 0.3)
    ambient_intensity: float = 0.3
    sun_color: Tuple[float, float, float] = (1.0, 0.95, 0.8)
    sun_intensity: float = 0.8
    sun_angle: float = 45.0
    fog_color: Tuple[float, float, float] = (0.5, 0.5, 0.6)
    fog_density: float = 0.01
    shadow_strength: float = 0.5


@dataclass
class DayNightConfig:
    day_length_seconds: float = 600.0
    dawn_duration: float = 0.1
    day_duration: float = 0.4
    dusk_duration: float = 0.1
    night_duration: float = 0.4
    time_scale: float = 1.0


@dataclass
class TimeEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    trigger_time: float = 0.0
    trigger_phase: Optional[TimePhase] = None
    callback_data: Dict[str, Any] = field(default_factory=dict)
    is_repeating: bool = False
    has_triggered: bool = False


class DayNightCycle:
    """
    Dynamic day/night cycle engine with phase-driven
    lighting and scheduled time-based events.
    """

    _instance: Optional[DayNightCycle] = None

    PRESET_LIGHTING: Dict[TimePhase, LightingParams] = {
        TimePhase.DAWN: LightingParams(
            ambient_color=(0.4, 0.35, 0.5),
            ambient_intensity=0.5,
            sun_color=(1.0, 0.7, 0.4),
            sun_intensity=0.4,
            sun_angle=15.0,
            shadow_strength=0.6,
        ),
        TimePhase.DAY: LightingParams(
            ambient_color=(0.6, 0.65, 0.8),
            ambient_intensity=0.8,
            sun_color=(1.0, 0.95, 0.85),
            sun_intensity=1.0,
            sun_angle=75.0,
            shadow_strength=0.3,
        ),
        TimePhase.DUSK: LightingParams(
            ambient_color=(0.5, 0.3, 0.4),
            ambient_intensity=0.5,
            sun_color=(1.0, 0.5, 0.2),
            sun_intensity=0.4,
            sun_angle=15.0,
            shadow_strength=0.6,
        ),
        TimePhase.NIGHT: LightingParams(
            ambient_color=(0.1, 0.1, 0.25),
            ambient_intensity=0.2,
            sun_color=(0.4, 0.5, 1.0),
            sun_intensity=0.05,
            sun_angle=-15.0,
            shadow_strength=0.9,
        ),
    }

    @classmethod
    def get_instance(cls) -> DayNightCycle:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._config = DayNightConfig()
        self._elapsed_time: float = 0.0
        self._day_count: int = 0
        self._events: List[TimeEvent] = []
        self._hooks: Dict[str, List[Callable]] = {}
        self._is_paused: bool = False
        self._last_phase: Optional[TimePhase] = None

    def configure(
        self,
        day_length: float = 600.0,
        dawn_ratio: float = 0.1,
        day_ratio: float = 0.4,
        dusk_ratio: float = 0.1,
        night_ratio: float = 0.4,
        time_scale: float = 1.0,
    ) -> None:
        total = dawn_ratio + day_ratio + dusk_ratio + night_ratio
        if total <= 0:
            return
        self._config = DayNightConfig(
            day_length_seconds=day_length,
            dawn_duration=dawn_ratio / total,
            day_duration=day_ratio / total,
            dusk_duration=dusk_ratio / total,
            night_duration=night_ratio / total,
            time_scale=time_scale,
        )

    def update(self, delta_seconds: float) -> TimePhase:
        if self._is_paused:
            return self.get_phase()
        self._elapsed_time += delta_seconds * self._config.time_scale

        full_days = int(self._elapsed_time / self._config.day_length_seconds)
        if full_days > self._day_count:
            self._day_count = full_days
            self._reset_daily_events()

        current_phase = self._phase_at_time(self._time_in_current_day())
        if self._last_phase != current_phase:
            self._last_phase = current_phase
            self._dispatch_phase_change(current_phase)

        self._process_events()
        return current_phase

    def _time_in_current_day(self) -> float:
        return self._elapsed_time % self._config.day_length_seconds

    def _phase_at_time(self, day_time: float) -> TimePhase:
        dl = self._config.day_length_seconds
        normalized = day_time / dl
        cfg = self._config

        dawn_end = cfg.dawn_duration
        day_end = dawn_end + cfg.day_duration
        dusk_end = day_end + cfg.dusk_duration

        if normalized < dawn_end:
            return TimePhase.DAWN
        elif normalized < day_end:
            return TimePhase.DAY
        elif normalized < dusk_end:
            return TimePhase.DUSK
        else:
            return TimePhase.NIGHT

    def get_phase(self) -> TimePhase:
        return self._phase_at_time(self._time_in_current_day())

    def get_time_of_day(self) -> float:
        return self._time_in_current_day() / self._config.day_length_seconds

    def get_day_count(self) -> int:
        return self._day_count

    def get_lighting_params(self) -> Dict[str, Any]:
        phase = self.get_phase()
        base = self.PRESET_LIGHTING.get(phase, LightingParams())

        progress = self._phase_progress()
        next_phase_map = {
            TimePhase.DAWN: TimePhase.DAY,
            TimePhase.DAY: TimePhase.DUSK,
            TimePhase.DUSK: TimePhase.NIGHT,
            TimePhase.NIGHT: TimePhase.DAWN,
        }
        next_phase = next_phase_map.get(phase, TimePhase.DAY)
        next_base = self.PRESET_LIGHTING.get(next_phase, base)

        t = progress
        ambient_color = tuple(base.ambient_color[i] + (next_base.ambient_color[i] - base.ambient_color[i]) * t for i in range(3))
        sun_color = tuple(base.sun_color[i] + (next_base.sun_color[i] - base.sun_color[i]) * t for i in range(3))

        return {
            "phase": phase.value,
            "ambient_color": [round(c, 3) for c in ambient_color],
            "ambient_intensity": round(base.ambient_intensity + (next_base.ambient_intensity - base.ambient_intensity) * t, 3),
            "sun_color": [round(c, 3) for c in sun_color],
            "sun_intensity": round(base.sun_intensity + (next_base.sun_intensity - base.sun_intensity) * t, 3),
            "sun_angle": round(base.sun_angle + (next_base.sun_angle - base.sun_angle) * t, 1),
            "shadow_strength": round(base.shadow_strength + (next_base.shadow_strength - base.shadow_strength) * t, 3),
            "time_of_day": round(self.get_time_of_day(), 3),
            "day_count": self._day_count,
        }

    def _phase_progress(self) -> float:
        day_time = self._time_in_current_day()
        dl = self._config.day_length_seconds
        cfg = self._config

        dawn_end = dl * cfg.dawn_duration
        day_end = dawn_end + dl * cfg.day_duration
        dusk_end = day_end + dl * cfg.dusk_duration

        if day_time < dawn_end:
            return day_time / max(dawn_end, 0.001)
        elif day_time < day_end:
            return (day_time - dawn_end) / max(day_end - dawn_end, 0.001)
        elif day_time < dusk_end:
            return (day_time - day_end) / max(dusk_end - day_end, 0.001)
        else:
            remaining = dl - dusk_end
            return (day_time - dusk_end) / max(remaining, 0.001)

    def schedule_event(
        self,
        name: str,
        trigger_time: float,
        trigger_phase: Optional[str] = None,
        callback_data: Optional[Dict[str, Any]] = None,
        is_repeating: bool = False,
    ) -> str:
        phase = None
        if trigger_phase:
            try:
                phase = TimePhase(trigger_phase)
            except ValueError:
                pass

        event = TimeEvent(
            name=name,
            trigger_time=trigger_time,
            trigger_phase=phase,
            callback_data=callback_data or {},
            is_repeating=is_repeating,
        )
        self._events.append(event)
        return event.event_id

    def cancel_event(self, event_id: str) -> bool:
        for i, event in enumerate(self._events):
            if event.event_id == event_id:
                self._events.pop(i)
                return True
        return False

    def _process_events(self) -> None:
        day_time = self._time_in_current_day()
        for event in self._events[:]:
            if event.has_triggered and not event.is_repeating:
                continue
            should_trigger = False
            if event.trigger_phase is not None:
                if self.get_phase() == event.trigger_phase:
                    should_trigger = True
            elif day_time >= event.trigger_time - 0.5:
                should_trigger = True

            if should_trigger and not event.has_triggered:
                event.has_triggered = True
                for callback in self._hooks.get("time_event", []):
                    callback(event)

    def _reset_daily_events(self) -> None:
        for event in self._events:
            if event.is_repeating:
                event.has_triggered = False

    def _dispatch_phase_change(self, new_phase: TimePhase) -> None:
        for callback in self._hooks.get("phase_change", []):
            callback(new_phase)

    def register_hook(self, event_type: str, callback: Callable) -> None:
        self._hooks.setdefault(event_type, []).append(callback)

    def set_paused(self, paused: bool) -> None:
        self._is_paused = paused

    def get_stats(self) -> Dict[str, Any]:
        return {
            "elapsed_time": round(self._elapsed_time, 1),
            "day_count": self._day_count,
            "current_phase": self.get_phase().value,
            "time_of_day": round(self.get_time_of_day(), 3),
            "day_length": self._config.day_length_seconds,
            "time_scale": self._config.time_scale,
            "is_paused": self._is_paused,
            "scheduled_events": len(self._events),
            "pending_events": sum(1 for e in self._events if not e.has_triggered),
        }

    def reset(self) -> None:
        self._elapsed_time = 0.0
        self._day_count = 0
        self._events.clear()
        self._hooks.clear()
        self._is_paused = False


_day_night_cycle = DayNightCycle.get_instance()


def get_day_night_cycle() -> DayNightCycle:
    return _day_night_cycle