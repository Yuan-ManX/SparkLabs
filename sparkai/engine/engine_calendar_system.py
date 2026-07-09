"""
SparkLabs Engine - Calendar & Event Schedule System

A scheduled event and seasonal content management system for the
SparkLabs AI-native game engine. Manages calendar events with start/end
timestamps, recurring schedules, seasonal content rotations, countdown
timers, event phases, reward tracks, and participation tracking.

Each calendar event defines a schedule with start and end times,
recurrence patterns, event phases, associated rewards, participation
requirements, and active state tracking. Designed for live-service game
events, seasonal festivals, limited-time modes, daily/weekly rotations,
and community challenges.

Architecture:
  CalendarSystem (singleton)
    |-- EventType, EventPhase, RecurrencePattern, CalendarEventKind
    |-- EventReward, EventPhaseDef, CalendarEvent, RewardTrack,
       CalendarConfig, CalendarStats, CalendarSnapshot, CalendarEvent_
    |-- get_calendar_system

Core Capabilities:
  - register_event / remove_event / get_event / list_events: manage
    scheduled calendar events with phases and rewards.
  - activate_event / deactivate_event: control event active state.
  - advance_phase / get_current_phase: manage event phase progression.
  - register_reward_track / claim_reward: event reward track progression.
  - track_participation / get_participation: player participation
    tracking per event.
  - get_upcoming / get_active / get_expired: query events by schedule
    state.
  - set_recurrence / get_next_occurrence: recurring event scheduling.
  - tick: advance event timers, auto-activate and auto-expire events.
  - set_config / get_config: global tuning for max events and phases.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`CalendarSystem.get_instance` or the module-level
:func:`get_calendar_system` factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_EVENTS: int = 500
_MAX_REWARD_TRACKS: int = 1000
_MAX_PARTICIPATIONS: int = 50000
_MAX_EVENTS_LIST: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


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
# Enums
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    """Type of calendar event."""
    SEASONAL = "seasonal"
    FESTIVAL = "festival"
    LIMITED_MODE = "limited_mode"
    COMMUNITY = "community"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ONE_TIME = "one_time"


class EventPhase(str, Enum):
    """Phase of a calendar event lifecycle."""
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ENDING_SOON = "ending_soon"
    ENDED = "ended"
    CANCELLED = "cancelled"


class RecurrencePattern(str, Enum):
    """Recurrence pattern for repeating events."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SEASONAL = "seasonal"


class CalendarEventKind(str, Enum):
    """Audit event types emitted by the calendar system."""
    EVENT_REGISTERED = "event_registered"
    EVENT_REMOVED = "event_removed"
    EVENT_ACTIVATED = "event_activated"
    EVENT_DEACTIVATED = "event_deactivated"
    PHASE_ADVANCED = "phase_advanced"
    REWARD_REGISTERED = "reward_registered"
    REWARD_CLAIMED = "reward_claimed"
    PARTICIPATION_TRACKED = "participation_tracked"
    RECURRENCE_SET = "recurrence_set"
    EVENT_EXPIRED = "event_expired"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class EventReward:
    """A reward entry in a calendar event or reward track."""
    reward_id: str
    name: str = ""
    item_id: str = ""
    quantity: int = 1
    currency: int = 0
    currency_type: str = "gold"
    rarity: str = "common"
    icon: str = ""
    claimable: bool = True
    claimed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EventPhaseDef:
    """A phase definition within a calendar event."""
    phase_id: str
    name: str = ""
    description: str = ""
    start_offset: float = 0.0
    duration: float = 0.0
    rewards: List[EventReward] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CalendarEvent:
    """A scheduled calendar event with phases and rewards."""
    event_id: str
    name: str = ""
    event_type: str = EventType.SEASONAL.value
    description: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    phase: str = EventPhase.SCHEDULED.value
    phases: List[EventPhaseDef] = field(default_factory=list)
    current_phase_index: int = 0
    recurrence: str = RecurrencePattern.NONE.value
    recurrence_interval: int = 1
    min_level: int = 1
    max_participants: int = 0
    active: bool = False
    icon: str = ""
    banner: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RewardTrack:
    """A reward track for a calendar event with tiered rewards."""
    track_id: str
    event_id: str
    name: str = ""
    max_tier: int = 10
    current_tier: int = 0
    points: int = 0
    points_per_tier: int = 100
    rewards: List[EventReward] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticipationRecord:
    """A player's participation record for a calendar event."""
    record_id: str
    event_id: str
    player_id: str
    join_time: float = field(default_factory=_now)
    points_earned: int = 0
    rewards_claimed: List[str] = field(default_factory=list)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CalendarConfig:
    """Global tuning parameters for the calendar system."""
    max_events: int = 200
    max_reward_tracks: int = 500
    max_participations: int = 20000
    default_event_duration_days: int = 7
    ending_soon_threshold_hours: float = 24.0
    auto_activate: bool = True
    auto_expire: bool = True
    tick_rate_hz: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CalendarStats:
    """Aggregate statistics for the calendar system."""
    total_events: int = 0
    active_events: int = 0
    scheduled_events: int = 0
    ended_events: int = 0
    total_reward_tracks: int = 0
    total_participations: int = 0
    total_rewards_claimed: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CalendarSnapshot:
    """Full state snapshot of the calendar system."""
    events: List[Dict[str, Any]] = field(default_factory=list)
    reward_tracks: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CalendarEvent_:
    """An audit event emitted by the calendar system."""
    event_id: str
    kind: str
    timestamp: float
    calendar_event_id: Optional[str] = None
    player_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Calendar System
# ---------------------------------------------------------------------------

class CalendarSystem:
    """Manages scheduled events, seasonal content, and reward tracks."""

    _instance: Optional["CalendarSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._events: Dict[str, CalendarEvent] = {}
        self._reward_tracks: Dict[str, RewardTrack] = {}
        self._participations: Dict[str, ParticipationRecord] = {}
        self._events_list: List[CalendarEvent_] = []
        self._stats = CalendarStats()
        self._config = CalendarConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "CalendarSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample calendar events, reward tracks, and participations."""
        with self._init_lock:
            if self._initialized:
                return
            now = _now()
            event1 = CalendarEvent(
                event_id="evt_spring_festival",
                name="Spring Festival",
                event_type=EventType.SEASONAL.value,
                description="Celebrate the spring season with special rewards!",
                start_time=now - 86400,
                end_time=now + 7 * 86400,
                phase=EventPhase.ACTIVE.value,
                active=True,
                phases=[
                    EventPhaseDef(phase_id="ph_opening", name="Opening",
                                  start_offset=0.0, duration=86400.0,
                                  rewards=[EventReward(reward_id="rw_opening",
                                                       name="Festival Banner",
                                                       item_id="item_fest_banner",
                                                       rarity="rare")]),
                    EventPhaseDef(phase_id="ph_main", name="Main Event",
                                  start_offset=86400.0, duration=5 * 86400.0,
                                  rewards=[EventReward(reward_id="rw_main",
                                                       name="Spring Crown",
                                                       item_id="item_spring_crown",
                                                       rarity="epic")]),
                    EventPhaseDef(phase_id="ph_finale", name="Finale",
                                  start_offset=6 * 86400.0, duration=86400.0,
                                  rewards=[EventReward(reward_id="rw_finale",
                                                       name="Spring Throne",
                                                       item_id="item_spring_throne",
                                                       rarity="legendary")]),
                ],
                current_phase_index=1,
                recurrence=RecurrencePattern.SEASONAL.value,
                recurrence_interval=1,
                icon="spring_festival_icon",
                banner="spring_festival_banner",
            )
            self._events[event1.event_id] = event1

            event2 = CalendarEvent(
                event_id="evt_weekly_dungeon",
                name="Weekly Dungeon Challenge",
                event_type=EventType.WEEKLY.value,
                description="Complete the weekly dungeon for bonus rewards.",
                start_time=now + 86400,
                end_time=now + 8 * 86400,
                phase=EventPhase.SCHEDULED.value,
                active=False,
                recurrence=RecurrencePattern.WEEKLY.value,
                recurrence_interval=1,
                min_level=10,
                icon="weekly_dungeon_icon",
            )
            self._events[event2.event_id] = event2

            event3 = CalendarEvent(
                event_id="evt_expired_event",
                name="Past Event",
                event_type=EventType.ONE_TIME.value,
                description="This event has ended.",
                start_time=now - 30 * 86400,
                end_time=now - 10 * 86400,
                phase=EventPhase.ENDED.value,
                active=False,
                icon="past_event_icon",
            )
            self._events[event3.event_id] = event3

            track1 = RewardTrack(
                track_id="rt_spring_01",
                event_id="evt_spring_festival",
                name="Spring Festival Track",
                max_tier=10,
                current_tier=3,
                points=350,
                points_per_tier=100,
                rewards=[
                    EventReward(reward_id="rt_rw_1", name="Tier 1 Reward",
                                item_id="item_rw_t1", rarity="common"),
                    EventReward(reward_id="rt_rw_5", name="Tier 5 Reward",
                                item_id="item_rw_t5", rarity="rare"),
                    EventReward(reward_id="rt_rw_10", name="Tier 10 Reward",
                                item_id="item_rw_t10", rarity="legendary"),
                ],
            )
            self._reward_tracks[track1.track_id] = track1

            part1 = ParticipationRecord(
                record_id="part_evt_spring_festival_player_starter",
                event_id="evt_spring_festival",
                player_id="player_starter",
                points_earned=350,
                rewards_claimed=["rt_rw_1"],
            )
            self._participations[part1.record_id] = part1

            self._stats.total_events = len(self._events)
            self._stats.active_events = sum(1 for e in self._events.values() if e.active)
            self._stats.scheduled_events = sum(1 for e in self._events.values()
                                               if e.phase == EventPhase.SCHEDULED.value)
            self._stats.ended_events = sum(1 for e in self._events.values()
                                           if e.phase == EventPhase.ENDED.value)
            self._stats.total_reward_tracks = len(self._reward_tracks)
            self._stats.total_participations = len(self._participations)
            self._initialized = True

    # ------------------------------------------------------------------
    # Event Management
    # ------------------------------------------------------------------

    def register_event(self, event: CalendarEvent) -> Dict[str, Any]:
        with self._lock:
            if len(self._events) >= _MAX_EVENTS:
                return {"registered": False, "reason": "capacity_reached"}
            if event.event_id in self._events:
                return {"registered": False, "reason": "event_exists"}
            if event.end_time == 0:
                event.end_time = event.start_time + self._config.default_event_duration_days * 86400
            self._events[event.event_id] = event
            self._stats.total_events = len(self._events)
            if event.active:
                self._stats.active_events += 1
            elif event.phase == EventPhase.SCHEDULED.value:
                self._stats.scheduled_events += 1
            self._emit_event(CalendarEventKind.EVENT_REGISTERED.value,
                             calendar_event_id=event.event_id)
            return {"registered": True, "event_id": event.event_id}

    def remove_event(self, event_id: str) -> Dict[str, Any]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return {"removed": False, "reason": "event_not_found"}
            if event.active:
                self._stats.active_events = max(0, self._stats.active_events - 1)
            if event.phase == EventPhase.SCHEDULED.value:
                self._stats.scheduled_events = max(0, self._stats.scheduled_events - 1)
            del self._events[event_id]
            self._stats.total_events = len(self._events)
            self._emit_event(CalendarEventKind.EVENT_REMOVED.value,
                             calendar_event_id=event_id)
            return {"removed": True, "event_id": event_id}

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        with self._lock:
            return self._events.get(event_id)

    def list_events(self, event_type: Optional[str] = None, phase: Optional[str] = None,
                    active: Optional[bool] = None, limit: int = 100) -> List[CalendarEvent]:
        with self._lock:
            result = []
            for e in self._events.values():
                if event_type and e.event_type != event_type:
                    continue
                if phase and e.phase != phase:
                    continue
                if active is not None and e.active != active:
                    continue
                result.append(e)
            return result[:limit]

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def activate_event(self, event_id: str) -> Dict[str, Any]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return {"activated": False, "reason": "event_not_found"}
            if event.active:
                return {"activated": False, "reason": "already_active"}
            if event.phase == EventPhase.ENDED.value:
                return {"activated": False, "reason": "event_ended"}
            event.active = True
            event.phase = EventPhase.ACTIVE.value
            event.updated_at = _now()
            self._stats.active_events += 1
            if event.phase == EventPhase.SCHEDULED.value:
                self._stats.scheduled_events = max(0, self._stats.scheduled_events - 1)
            self._emit_event(CalendarEventKind.EVENT_ACTIVATED.value,
                             calendar_event_id=event_id)
            return {"activated": True, "event_id": event_id}

    def deactivate_event(self, event_id: str) -> Dict[str, Any]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return {"deactivated": False, "reason": "event_not_found"}
            if not event.active:
                return {"deactivated": False, "reason": "not_active"}
            event.active = False
            event.phase = EventPhase.SCHEDULED.value
            event.updated_at = _now()
            self._stats.active_events = max(0, self._stats.active_events - 1)
            self._stats.scheduled_events += 1
            self._emit_event(CalendarEventKind.EVENT_DEACTIVATED.value,
                             calendar_event_id=event_id)
            return {"deactivated": True, "event_id": event_id}

    # ------------------------------------------------------------------
    # Phase Management
    # ------------------------------------------------------------------

    def advance_phase(self, event_id: str) -> Dict[str, Any]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return {"success": False, "reason": "event_not_found"}
            if event.current_phase_index >= len(event.phases) - 1:
                return {"success": False, "reason": "max_phase"}
            event.current_phase_index += 1
            event.updated_at = _now()
            self._emit_event(CalendarEventKind.PHASE_ADVANCED.value,
                             calendar_event_id=event_id,
                             details={"new_phase_index": event.current_phase_index})
            return {"success": True, "event_id": event_id,
                    "new_phase_index": event.current_phase_index}

    def get_current_phase(self, event_id: str) -> Dict[str, Any]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return {"found": False, "reason": "event_not_found"}
            if not event.phases:
                return {"found": True, "event_id": event_id, "phase": None}
            phase = event.phases[event.current_phase_index]
            return {"found": True, "event_id": event_id,
                    "phase_index": event.current_phase_index,
                    "phase": phase.to_dict()}

    # ------------------------------------------------------------------
    # Reward Tracks
    # ------------------------------------------------------------------

    def register_reward_track(self, track: RewardTrack) -> Dict[str, Any]:
        with self._lock:
            if len(self._reward_tracks) >= _MAX_REWARD_TRACKS:
                return {"registered": False, "reason": "capacity_reached"}
            if track.track_id in self._reward_tracks:
                return {"registered": False, "reason": "track_exists"}
            self._reward_tracks[track.track_id] = track
            self._stats.total_reward_tracks = len(self._reward_tracks)
            self._emit_event(CalendarEventKind.REWARD_REGISTERED.value,
                             details={"track_id": track.track_id})
            return {"registered": True, "track_id": track.track_id}

    def get_reward_track(self, track_id: str) -> Optional[RewardTrack]:
        with self._lock:
            return self._reward_tracks.get(track_id)

    def list_reward_tracks(self, event_id: Optional[str] = None,
                           limit: int = 100) -> List[RewardTrack]:
        with self._lock:
            result = []
            for t in self._reward_tracks.values():
                if event_id and t.event_id != event_id:
                    continue
                result.append(t)
            return result[:limit]

    def add_track_points(self, track_id: str, points: int) -> Dict[str, Any]:
        with self._lock:
            track = self._reward_tracks.get(track_id)
            if track is None:
                return {"success": False, "reason": "track_not_found"}
            track.points += max(0, points)
            old_tier = track.current_tier
            track.current_tier = min(track.max_tier, track.points // track.points_per_tier)
            tier_up = track.current_tier > old_tier
            return {"success": True, "track_id": track_id,
                    "new_points": track.points, "new_tier": track.current_tier,
                    "tier_up": tier_up}

    def claim_reward(self, track_id: str, reward_id: str) -> Dict[str, Any]:
        with self._lock:
            track = self._reward_tracks.get(track_id)
            if track is None:
                return {"success": False, "reason": "track_not_found"}
            for r in track.rewards:
                if r.reward_id == reward_id:
                    if r.claimed:
                        return {"success": False, "reason": "already_claimed"}
                    if not r.claimable:
                        return {"success": False, "reason": "not_claimable"}
                    r.claimed = True
                    self._stats.total_rewards_claimed += 1
                    self._emit_event(CalendarEventKind.REWARD_CLAIMED.value,
                                     details={"track_id": track_id, "reward_id": reward_id})
                    return {"success": True, "track_id": track_id,
                            "reward_id": reward_id, "item_id": r.item_id}
            return {"success": False, "reason": "reward_not_found"}

    # ------------------------------------------------------------------
    # Participation
    # ------------------------------------------------------------------

    def track_participation(self, event_id: str, player_id: str,
                            points: int = 0) -> Dict[str, Any]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return {"success": False, "reason": "event_not_found"}
            record_id = f"part_{event_id}_{player_id}"
            record = self._participations.get(record_id)
            if record is None:
                if len(self._participations) >= _MAX_PARTICIPATIONS:
                    return {"success": False, "reason": "capacity_reached"}
                record = ParticipationRecord(
                    record_id=record_id,
                    event_id=event_id,
                    player_id=player_id,
                    points_earned=points,
                )
                self._participations[record_id] = record
                self._stats.total_participations += 1
            else:
                record.points_earned += points
            self._emit_event(CalendarEventKind.PARTICIPATION_TRACKED.value,
                             calendar_event_id=event_id, player_id=player_id,
                             details={"points": points, "total": record.points_earned})
            return {"success": True, "record_id": record_id,
                    "points_earned": record.points_earned}

    def get_participation(self, event_id: str, player_id: str) -> Dict[str, Any]:
        with self._lock:
            record_id = f"part_{event_id}_{player_id}"
            record = self._participations.get(record_id)
            if record is None:
                return {"found": False, "reason": "no_participation"}
            return {"found": True, "record": record.to_dict()}

    def list_participations(self, event_id: Optional[str] = None,
                            player_id: Optional[str] = None,
                            limit: int = 100) -> List[ParticipationRecord]:
        with self._lock:
            result = []
            for p in self._participations.values():
                if event_id and p.event_id != event_id:
                    continue
                if player_id and p.player_id != player_id:
                    continue
                result.append(p)
            return result[:limit]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_upcoming(self, limit: int = 10) -> List[CalendarEvent]:
        with self._lock:
            now = _now()
            result = [e for e in self._events.values()
                      if e.start_time > now and e.phase != EventPhase.ENDED.value]
            result.sort(key=lambda e: e.start_time)
            return result[:limit]

    def get_active(self, limit: int = 10) -> List[CalendarEvent]:
        with self._lock:
            result = [e for e in self._events.values() if e.active]
            result.sort(key=lambda e: e.end_time)
            return result[:limit]

    def get_expired(self, limit: int = 10) -> List[CalendarEvent]:
        with self._lock:
            now = _now()
            result = [e for e in self._events.values()
                      if e.end_time < now and e.phase != EventPhase.ENDED.value]
            return result[:limit]

    # ------------------------------------------------------------------
    # Recurrence
    # ------------------------------------------------------------------

    def set_recurrence(self, event_id: str, pattern: str,
                       interval: int = 1) -> Dict[str, Any]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return {"success": False, "reason": "event_not_found"}
            event.recurrence = pattern
            event.recurrence_interval = max(1, interval)
            event.updated_at = _now()
            self._emit_event(CalendarEventKind.RECURRENCE_SET.value,
                             calendar_event_id=event_id,
                             details={"pattern": pattern, "interval": interval})
            return {"success": True, "event_id": event_id,
                    "pattern": pattern, "interval": interval}

    def get_next_occurrence(self, event_id: str) -> Dict[str, Any]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return {"found": False, "reason": "event_not_found"}
            now = _now()
            if event.recurrence == RecurrencePattern.NONE.value:
                return {"found": True, "event_id": event_id,
                        "next_start": event.start_time if event.start_time > now else 0.0}
            interval_sec = 0
            if event.recurrence == RecurrencePattern.DAILY.value:
                interval_sec = 86400 * event.recurrence_interval
            elif event.recurrence == RecurrencePattern.WEEKLY.value:
                interval_sec = 7 * 86400 * event.recurrence_interval
            elif event.recurrence == RecurrencePattern.MONTHLY.value:
                interval_sec = 30 * 86400 * event.recurrence_interval
            elif event.recurrence == RecurrencePattern.SEASONAL.value:
                interval_sec = 90 * 86400 * event.recurrence_interval
            if interval_sec == 0:
                return {"found": True, "event_id": event_id, "next_start": event.start_time}
            next_start = event.start_time
            while next_start < now:
                next_start += interval_sec
            return {"found": True, "event_id": event_id, "next_start": next_start}

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> Dict[str, Any]:
        with self._lock:
            self._tick_count += 1
            now = _now()
            threshold = self._config.ending_soon_threshold_hours * 3600
            activated = 0
            expired = 0
            for event in self._events.values():
                if self._config.auto_activate:
                    if (not event.active and event.phase != EventPhase.ENDED.value
                            and event.start_time <= now < event.end_time):
                        result = self.activate_event(event.event_id)
                        if result.get("activated"):
                            activated += 1
                if self._config.auto_expire:
                    if (event.active and event.end_time < now):
                        event.active = False
                        event.phase = EventPhase.ENDED.value
                        self._stats.active_events = max(0, self._stats.active_events - 1)
                        self._stats.ended_events += 1
                        expired += 1
                        self._emit_event(CalendarEventKind.EVENT_EXPIRED.value,
                                         calendar_event_id=event.event_id)
                if (event.active and event.phase != EventPhase.ENDING_SOON.value
                        and event.end_time - now < threshold and event.end_time > now):
                    event.phase = EventPhase.ENDING_SOON.value
            self._stats.tick_count = self._tick_count
            self._emit_event(CalendarEventKind.TICK.value,
                             details={"delta_time": delta_time,
                                      "activated": activated, "expired": expired})
            return {"tick_count": self._tick_count,
                    "activated": activated, "expired": expired}

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def get_config(self) -> CalendarConfig:
        with self._lock:
            return self._config

    def set_config(self, config: CalendarConfig) -> Dict[str, Any]:
        with self._lock:
            self._config = config
            self._emit_event(CalendarEventKind.CONFIG_UPDATED.value)
            return {"success": True}

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, calendar_event_id: Optional[str] = None,
                    player_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None) -> None:
        self._event_counter += 1
        event = CalendarEvent_(
            event_id=f"ce_{self._event_counter}",
            kind=kind,
            timestamp=_now(),
            calendar_event_id=calendar_event_id,
            player_id=player_id,
            details=details or {},
        )
        self._events_list.append(event)
        _evict_fifo_list(self._events_list, _MAX_EVENTS_LIST)

    def list_events_audit(self, event_id: Optional[str] = None,
                          limit: int = 100) -> List[CalendarEvent_]:
        with self._lock:
            result = []
            for e in self._events_list:
                if event_id and e.calendar_event_id != event_id:
                    continue
                result.append(e)
            return result[:limit]

    def get_stats(self) -> CalendarStats:
        with self._lock:
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_events": len(self._events),
                "active_events": sum(1 for e in self._events.values() if e.active),
                "scheduled_events": sum(1 for e in self._events.values()
                                        if e.phase == EventPhase.SCHEDULED.value),
                "ended_events": sum(1 for e in self._events.values()
                                    if e.phase == EventPhase.ENDED.value),
                "total_reward_tracks": len(self._reward_tracks),
                "total_participations": len(self._participations),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> CalendarSnapshot:
        with self._lock:
            return CalendarSnapshot(
                events=[e.to_dict() for e in self._events.values()],
                reward_tracks=[t.to_dict() for t in self._reward_tracks.values()],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._events.clear()
            self._reward_tracks.clear()
            self._participations.clear()
            self._events_list.clear()
            self._stats = CalendarStats()
            self._config = CalendarConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._emit_event(CalendarEventKind.RESET.value)
            self._seed()
            return {"success": True, "reset": True}


def get_calendar_system() -> CalendarSystem:
    """Factory function for the CalendarSystem singleton."""
    return CalendarSystem.get_instance()
