"""
SparkLabs Agent - Temporal Director"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class TimeScale(Enum):
    """Game time flow modes."""
    REAL_TIME = "real_time"
    SLOW_MOTION = "slow_motion"        # 0.2x speed
    BULLET_TIME = "bullet_time"        # 0.1x speed
    FAST_FORWARD = "fast_forward"      # 3x speed
    FROZEN = "frozen"                  # paused
    FLASHBACK = "flashback"            # rewinding


class PacingPhase(Enum):
    """Narrative pacing rhythm phases."""
    CALM = "calm"
    BUILDING = "building"
    CLIMAX = "climax"
    RELEASE = "release"
    REST = "rest"


class TemporalPhase(Enum):
    """Phases of the temporal director cycle."""
    TICK = "tick"
    ASSESS = "assess"
    SCHEDULE = "schedule"
    DISPATCH = "dispatch"
    VERIFY = "verify"


class ScheduledEventType(Enum):
    """Types of scheduled events for AI modules."""
    STORY_BEAT = "story_beat"
    FRAME_TRANSITION = "frame_transition"
    TUNER_CYCLE = "tuner_cycle"
    MUSIC_SHIFT = "music_shift"
    DIFFICULTY_ADJUST = "difficulty_adjust"
    WORLD_EVENT = "world_event"
    CUTSCENE_TRIGGER = "cutscene_trigger"
    AMBIENCE_CHANGE = "ambience_change"


class DayPhase(Enum):
    """Day/night cycle phases."""
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    NIGHT = "night"
    MIDNIGHT = "midnight"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class ScheduledEvent:
    """An event scheduled for a future game time."""
    event_id: str
    event_type: ScheduledEventType
    target_module: str
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    scheduled_time: float = 0.0  # game time when it should fire
    priority: int = 0
    fired: bool = False
    result: Optional[Dict[str, Any]] = None
    label: str = ""


@dataclass
class PacingState:
    """Current pacing rhythm state."""
    phase: PacingPhase = PacingPhase.CALM
    tension_level: float = 0.2  # 0.0 = fully calm, 1.0 = peak climax
    phase_started_at: float = 0.0
    phase_duration_s: float = 30.0  # target duration for current phase
    build_rate: float = 0.01  # tension increase per tick
    release_rate: float = 0.03  # tension decrease per tick


@dataclass
class TemporalStats:
    """Statistics for the temporal director."""
    total_ticks: int = 0
    total_events_scheduled: int = 0
    total_events_fired: int = 0
    total_events_cancelled: int = 0
    total_time_scale_changes: int = 0
    total_day_phases_passed: int = 0
    avg_pacing_tension: float = 0.2
    current_time_scale: str = "real_time"
    last_tick_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Temporal Director
# =============================================================================

class AgentTemporalDirector:
    """
    Singleton agent that manages game time, pacing, and event scheduling.

    The director runs a 5-phase cycle:
      1. TICK     - Advance game time by the current time scale
      2. ASSESS   - Evaluate pacing rhythm and tension trajectory
      3. SCHEDULE - Plan event timing for AI modules
      4. DISPATCH - Emit timed directives for due events
      5. VERIFY   - Confirm events fired correctly

    The director ensures all AI modules act at the RIGHT time, creating
    a coherent rhythm rather than chaotic simultaneous actions.
    """

    _instance: Optional["AgentTemporalDirector"] = None
    _instance_lock = threading.Lock()

    # Time scale multipliers
    TIME_SCALE_MULTIPLIERS: Dict[TimeScale, float] = {
        TimeScale.REAL_TIME: 1.0,
        TimeScale.SLOW_MOTION: 0.2,
        TimeScale.BULLET_TIME: 0.1,
        TimeScale.FAST_FORWARD: 3.0,
        TimeScale.FROZEN: 0.0,
        TimeScale.FLASHBACK: -1.0,  # negative = reversing
    }

    # Day phase durations (in game-time seconds)
    DAY_PHASE_DURATIONS: Dict[DayPhase, float] = {
        DayPhase.DAWN: 600.0,
        DayPhase.MORNING: 1800.0,
        DayPhase.NOON: 1200.0,
        DayPhase.AFTERNOON: 1800.0,
        DayPhase.DUSK: 600.0,
        DayPhase.NIGHT: 2400.0,
        DayPhase.MIDNIGHT: 900.0,
    }

    # Pacing phase transitions
    PACING_TRANSITIONS: Dict[PacingPhase, PacingPhase] = {
        PacingPhase.CALM: PacingPhase.BUILDING,
        PacingPhase.BUILDING: PacingPhase.CLIMAX,
        PacingPhase.CLIMAX: PacingPhase.RELEASE,
        PacingPhase.RELEASE: PacingPhase.REST,
        PacingPhase.REST: PacingPhase.CALM,
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._game_time: float = 0.0  # accumulated game time in seconds
        self._real_time: float = time.time()
        self._time_scale: TimeScale = TimeScale.REAL_TIME
        self._pacing = PacingState(phase_started_at=0.0)
        self._day_phase: DayPhase = DayPhase.DAWN
        self._day_phase_started_at: float = 0.0
        self._scheduled_events: Dict[str, ScheduledEvent] = {}
        self._event_history: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._stats = TemporalStats()
        self._cycle_count: int = 0
        self._last_cycle_at: float = 0.0
        self._cycle_interval_s: float = 1.0
        self._active: bool = False
        self._temporal_effects: Deque[Dict[str, Any]] = deque(maxlen=50)

    @classmethod
    def get_instance(cls) -> "AgentTemporalDirector":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Phase 1: TICK - Advance game time
    # -------------------------------------------------------------------------

    def set_time_scale(self, scale: str) -> Dict[str, Any]:
        """Set the game time scale. Accepts enum name or value (case-insensitive)."""
        with self._lock:
            ts = self._resolve_time_scale(scale)
            if ts is None:
                return {"error": f"Invalid time scale: {scale}"}
            old_scale = self._time_scale
            self._time_scale = ts
            self._stats.total_time_scale_changes += 1
            self._stats.current_time_scale = ts.value
            self._temporal_effects.append({
                "type": "time_scale_change",
                "from": old_scale.value,
                "to": ts.value,
                "game_time": self._game_time,
                "timestamp": time.time(),
            })
            return {"time_scale": ts.value, "multiplier": self.TIME_SCALE_MULTIPLIERS[ts]}

    def _advance_time(self, delta_real_s: float) -> float:
        """Advance game time by the scaled delta. Returns the game-time delta."""
        multiplier = self.TIME_SCALE_MULTIPLIERS[self._time_scale]
        delta_game = delta_real_s * multiplier
        self._game_time += delta_game
        return delta_game

    def _advance_day_phase(self) -> None:
        """Check if the current day phase should transition."""
        phase_duration = self.DAY_PHASE_DURATIONS[self._day_phase]
        elapsed = self._game_time - self._day_phase_started_at
        if elapsed >= phase_duration:
            phases = list(DayPhase)
            idx = phases.index(self._day_phase)
            self._day_phase = phases[(idx + 1) % len(phases)]
            self._day_phase_started_at = self._game_time
            self._stats.total_day_phases_passed += 1
            self._temporal_effects.append({
                "type": "day_phase_change",
                "new_phase": self._day_phase.value,
                "game_time": self._game_time,
                "timestamp": time.time(),
            })

    # -------------------------------------------------------------------------
    # Phase 2: ASSESS - Evaluate pacing rhythm
    # -------------------------------------------------------------------------

    def _assess_pacing(self) -> None:
        """Evaluate and update the pacing rhythm."""
        now = self._game_time
        phase_elapsed = now - self._pacing.phase_started_at

        # Update tension based on current phase
        if self._pacing.phase == PacingPhase.BUILDING:
            self._pacing.tension_level = min(1.0,
                self._pacing.tension_level + self._pacing.build_rate)
        elif self._pacing.phase == PacingPhase.RELEASE:
            self._pacing.tension_level = max(0.0,
                self._pacing.tension_level - self._pacing.release_rate)
        elif self._pacing.phase == PacingPhase.CLIMAX:
            self._pacing.tension_level = max(self._pacing.tension_level, 0.85)
        elif self._pacing.phase in (PacingPhase.CALM, PacingPhase.REST):
            self._pacing.tension_level = max(0.0,
                self._pacing.tension_level - self._pacing.release_rate * 0.5)

        # Check if phase should transition
        if phase_elapsed >= self._pacing.phase_duration_s:
            old_phase = self._pacing.phase
            self._pacing.phase = self.PACING_TRANSITIONS[old_phase]
            self._pacing.phase_started_at = now
            # Set appropriate duration and rates for new phase
            if self._pacing.phase == PacingPhase.CALM:
                self._pacing.phase_duration_s = 30.0
                self._pacing.build_rate = 0.005
            elif self._pacing.phase == PacingPhase.BUILDING:
                self._pacing.phase_duration_s = 45.0
                self._pacing.build_rate = 0.015
            elif self._pacing.phase == PacingPhase.CLIMAX:
                self._pacing.phase_duration_s = 15.0
                self._pacing.build_rate = 0.0
            elif self._pacing.phase == PacingPhase.RELEASE:
                self._pacing.phase_duration_s = 20.0
                self._pacing.release_rate = 0.04
            elif self._pacing.phase == PacingPhase.REST:
                self._pacing.phase_duration_s = 25.0
                self._pacing.release_rate = 0.02

            self._temporal_effects.append({
                "type": "pacing_phase_change",
                "from": old_phase.value,
                "to": self._pacing.phase.value,
                "tension": round(self._pacing.tension_level, 3),
                "game_time": now,
                "timestamp": time.time(),
            })

    # -------------------------------------------------------------------------
    # Phase 3: SCHEDULE - Plan event timing
    # -------------------------------------------------------------------------

    def schedule_event(self, event_type: str, target_module: str,
                       method: str, delay_s: float,
                       params: Optional[Dict[str, Any]] = None,
                       priority: int = 0, label: str = "") -> Dict[str, Any]:
        """Schedule an event to fire after a delay (in game-time seconds)."""
        with self._lock:
            et = self._resolve_event_type(event_type)
            if et is None:
                return {"error": f"Invalid event type: {event_type}"}
            event_id = f"evt_{int(time.time() * 1000)}_{self._stats.total_events_scheduled}"
            event = ScheduledEvent(
                event_id=event_id,
                event_type=et,
                target_module=target_module,
                method=method,
                params=params or {},
                scheduled_time=self._game_time + delay_s,
                priority=priority,
                label=label,
            )
            self._scheduled_events[event_id] = event
            self._stats.total_events_scheduled += 1
            return self._event_to_dict(event)

    def _auto_schedule(self) -> None:
        """Automatically schedule events based on pacing rhythm."""
        # During BUILDING phase, schedule story beats
        if self._pacing.phase == PacingPhase.BUILDING and self._cycle_count % 10 == 0:
            self.schedule_event(
                "story_beat", "story_director", "run_cycle",
                delay_s=5.0, priority=5,
                label="pacing-driven story beat",
            )

        # During CLIMAX, schedule frame transitions more frequently
        if self._pacing.phase == PacingPhase.CLIMAX and self._cycle_count % 3 == 0:
            self.schedule_event(
                "frame_transition", "frame_architect", "run_cycle",
                delay_s=2.0, priority=8,
                label="climax frame transition",
            )

        # During CALM, schedule tuner cycles for optimization
        if self._pacing.phase == PacingPhase.CALM and self._cycle_count % 15 == 0:
            self.schedule_event(
                "tuner_cycle", "live_tuner", "run_cycle",
                delay_s=10.0, priority=3,
                label="calm optimization cycle",
            )

    # -------------------------------------------------------------------------
    # Phase 4: DISPATCH - Fire due events
    # -------------------------------------------------------------------------

    def _dispatch_due_events(self) -> List[Dict[str, Any]]:
        """Fire all events whose scheduled time has arrived."""
        fired: List[Dict[str, Any]] = []
        due_events = [
            (eid, evt) for eid, evt in self._scheduled_events.items()
            if not evt.fired and self._game_time >= evt.scheduled_time
        ]
        # Sort by priority (descending)
        due_events.sort(key=lambda x: x[1].priority, reverse=True)

        for eid, evt in due_events:
            evt.fired = True
            result = self._execute_event(evt)
            evt.result = result
            fired.append(self._event_to_dict(evt))
            self._stats.total_events_fired += 1
            self._event_history.append({
                "event_id": eid,
                "event_type": evt.event_type.value,
                "target_module": evt.target_module,
                "label": evt.label,
                "fired_at": self._game_time,
                "result": result,
            })

        # Clean up fired events (keep last 50)
        if len(self._scheduled_events) > 100:
            fired_ids = [eid for eid, evt in self._scheduled_events.items() if evt.fired]
            for eid in fired_ids[:50]:
                del self._scheduled_events[eid]

        return fired

    def _execute_event(self, evt: ScheduledEvent) -> Dict[str, Any]:
        """Execute a scheduled event by calling the target module."""
        try:
            if evt.target_module == "story_director":
                from sparkai.agent.agent_story_director import AgentStoryDirector
                result = AgentStoryDirector.get_instance().run_cycle()
            elif evt.target_module == "frame_architect":
                from sparkai.agent.agent_frame_architect import AgentFrameArchitect
                result = AgentFrameArchitect.get_instance().run_cycle()
            elif evt.target_module == "live_tuner":
                from sparkai.engine.engine_live_tuner import EngineLiveTuner
                result = EngineLiveTuner.get_instance().run_cycle()
            else:
                return {"success": False, "error": f"Unknown module: {evt.target_module}"}
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Phase 5: VERIFY - Confirm events fired
    # -------------------------------------------------------------------------

    def _verify_events(self, fired: List[Dict[str, Any]]) -> int:
        """Verify that fired events produced results. Returns success count."""
        success = 0
        for f in fired:
            result = f.get("result", {})
            if result.get("success") or result.get("phase"):
                success += 1
        return success

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single temporal director cycle.

        Phases: TICK -> ASSESS -> SCHEDULE -> DISPATCH -> VERIFY
        """
        start_time = time.time()
        with self._lock:
            self._active = True
            phase = TemporalPhase.TICK

            # Phase 1: TICK - advance game time
            now = time.time()
            delta_real = now - self._real_time
            self._real_time = now
            delta_game = self._advance_time(delta_real)
            self._advance_day_phase()

            # Phase 2: ASSESS - evaluate pacing
            phase = TemporalPhase.ASSESS
            self._assess_pacing()

            # Phase 3: SCHEDULE - auto-schedule events
            phase = TemporalPhase.SCHEDULE
            self._auto_schedule()

            # Phase 4: DISPATCH - fire due events
            phase = TemporalPhase.DISPATCH
            fired = self._dispatch_due_events()

            # Phase 5: VERIFY
            phase = TemporalPhase.VERIFY
            verified = self._verify_events(fired)

            # Update stats
            self._cycle_count += 1
            self._stats.total_ticks = self._cycle_count
            self._stats.avg_pacing_tension = (
                (self._stats.avg_pacing_tension * (self._cycle_count - 1) +
                 self._pacing.tension_level) / self._cycle_count
            )
            self._stats.last_tick_time_ms = (time.time() - start_time) * 1000
            self._stats.active = True
            self._last_cycle_at = time.time()

            return {
                "phase": phase.value,
                "game_time": round(self._game_time, 2),
                "time_scale": self._time_scale.value,
                "time_multiplier": self.TIME_SCALE_MULTIPLIERS[self._time_scale],
                "day_phase": self._day_phase.value,
                "pacing_phase": self._pacing.phase.value,
                "pacing_tension": round(self._pacing.tension_level, 3),
                "events_fired": len(fired),
                "events_verified": verified,
                "pending_events": sum(1 for e in self._scheduled_events.values() if not e.fired),
                "cycle": self._cycle_count,
            }

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the temporal director."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "game_time": round(self._game_time, 2),
                "time_scale": self._time_scale.value,
                "time_multiplier": self.TIME_SCALE_MULTIPLIERS[self._time_scale],
                "day_phase": self._day_phase.value,
                "day_phase_elapsed": round(self._game_time - self._day_phase_started_at, 1),
                "pacing": {
                    "phase": self._pacing.phase.value,
                    "tension_level": round(self._pacing.tension_level, 3),
                    "phase_elapsed": round(self._game_time - self._pacing.phase_started_at, 1),
                    "phase_duration": self._pacing.phase_duration_s,
                },
                "pending_events": sum(1 for e in self._scheduled_events.values() if not e.fired),
                "stats": {
                    "total_ticks": self._stats.total_ticks,
                    "total_events_scheduled": self._stats.total_events_scheduled,
                    "total_events_fired": self._stats.total_events_fired,
                    "total_events_cancelled": self._stats.total_events_cancelled,
                    "total_time_scale_changes": self._stats.total_time_scale_changes,
                    "total_day_phases_passed": self._stats.total_day_phases_passed,
                    "avg_pacing_tension": round(self._stats.avg_pacing_tension, 3),
                    "current_time_scale": self._stats.current_time_scale,
                    "last_tick_time_ms": round(self._stats.last_tick_time_ms, 2),
                    "active": self._stats.active,
                },
            }

    def get_events(self, limit: int = 20, include_fired: bool = True) -> List[Dict[str, Any]]:
        """Get scheduled events."""
        with self._lock:
            events = list(self._scheduled_events.values())
            if not include_fired:
                events = [e for e in events if not e.fired]
            events.sort(key=lambda e: e.scheduled_time)
            if limit > 0:
                events = events[:limit]
            return [self._event_to_dict(e) for e in events]

    def cancel_event(self, event_id: str) -> bool:
        """Cancel a scheduled event."""
        with self._lock:
            if event_id in self._scheduled_events:
                del self._scheduled_events[event_id]
                self._stats.total_events_cancelled += 1
                return True
            return False

    def get_event_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the history of fired events."""
        with self._lock:
            history = list(self._event_history)
            if limit > 0:
                history = history[-limit:]
            return list(reversed(history))

    def get_temporal_effects(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent temporal effects (time scale changes, day phase changes, etc.)."""
        with self._lock:
            effects = list(self._temporal_effects)
            if limit > 0:
                effects = effects[-limit:]
            return list(reversed(effects))

    def force_pacing_phase(self, phase: str) -> Dict[str, Any]:
        """Force the pacing to a specific phase."""
        with self._lock:
            pp = self._resolve_pacing_phase(phase)
            if pp is None:
                return {"error": f"Invalid pacing phase: {phase}"}
            old = self._pacing.phase
            self._pacing.phase = pp
            self._pacing.phase_started_at = self._game_time
            if pp == PacingPhase.CLIMAX:
                self._pacing.tension_level = max(self._pacing.tension_level, 0.85)
                self._pacing.phase_duration_s = 15.0
            elif pp == PacingPhase.CALM:
                self._pacing.tension_level = 0.1
                self._pacing.phase_duration_s = 30.0
            return {"phase": pp.value, "previous": old.value, "tension": round(self._pacing.tension_level, 3)}

    def simulate(self, ticks: int = 20) -> Dict[str, Any]:
        """Run multiple ticks with simulated time advancement."""
        with self._lock:
            total_fired = 0
            for _ in range(ticks):
                # Simulate real time passage
                self._real_time -= 1.0  # make delta ~1 second
                result = self.run_cycle()
                total_fired += result.get("events_fired", 0)
            return {
                "ticks_run": ticks,
                "total_events_fired": total_fired,
                "final_game_time": round(self._game_time, 2),
                "final_pacing_phase": self._pacing.phase.value,
                "final_tension": round(self._pacing.tension_level, 3),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the temporal director to initial state."""
        with self._lock:
            self._game_time = 0.0
            self._real_time = time.time()
            self._time_scale = TimeScale.REAL_TIME
            self._pacing = PacingState(phase_started_at=0.0)
            self._day_phase = DayPhase.DAWN
            self._day_phase_started_at = 0.0
            self._scheduled_events.clear()
            self._event_history.clear()
            self._temporal_effects.clear()
            self._stats = TemporalStats()
            self._cycle_count = 0
            self._last_cycle_at = 0.0
            self._active = False
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Enum Resolvers (case-insensitive)
    # -------------------------------------------------------------------------

    @staticmethod
    def _resolve_time_scale(name: str) -> Optional[TimeScale]:
        key = name.strip().lower()
        for ts in TimeScale:
            if ts.value == key or ts.name.lower() == key:
                return ts
        return None

    @staticmethod
    def _resolve_event_type(name: str) -> Optional[ScheduledEventType]:
        key = name.strip().lower()
        for et in ScheduledEventType:
            if et.value == key or et.name.lower() == key:
                return et
        return None

    @staticmethod
    def _resolve_pacing_phase(name: str) -> Optional[PacingPhase]:
        key = name.strip().lower()
        for pp in PacingPhase:
            if pp.value == key or pp.name.lower() == key:
                return pp
        return None

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _event_to_dict(self, evt: ScheduledEvent) -> Dict[str, Any]:
        return {
            "event_id": evt.event_id,
            "event_type": evt.event_type.value,
            "target_module": evt.target_module,
            "method": evt.method,
            "params": evt.params,
            "scheduled_time": round(evt.scheduled_time, 2),
            "priority": evt.priority,
            "fired": evt.fired,
            "result": evt.result,
            "label": evt.label,
        }
