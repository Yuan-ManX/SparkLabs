"""
SparkLabs AI-Native Game Engine - Agent Daily Routine System
============================================================

Daily routine and schedule management for AI agents in the
SparkLabs AI-native game engine.

This module equips each agent with a structured yet flexible daily routine.
An agent's day is modeled as an hourly
schedule composed of discrete *activity blocks*. Agents generate a schedule
at the start of their day, execute activities in sequence, react to
unexpected events that disrupt the plan, and replan the remainder of the
day when the original plan no longer fits reality.

Core Concepts
-------------

1. **Hourly Schedule Generation** -- ``generate_schedule`` produces a
   ``DailySchedule`` that fills the agent's wake period (from ``wake_time``
   to ``sleep_time``) with a sequence of ``ActivityBlock`` entries. Each
   block carries a category (WORK, LEISURE, MEAL, ...), a start hour in
   [0, 24], a duration, a location, and a priority. Schedules may be
   generated from a reusable ``RoutineTemplate``, from caller-supplied
   preferences, or from sensible defaults.

2. **Activity Blocks** -- The atomic unit of a routine. Activities move
   through a lifecycle: PENDING -> IN_PROGRESS -> COMPLETED (or SKIPPED /
   INTERRUPTED). The engine exposes ``start_activity``,
   ``complete_activity``, ``skip_activity``, ``interrupt_activity``, and
   ``update_activity`` to drive that lifecycle.

3. **Event Reactions** -- When the world surprises an agent (an unexpected
   visitor, a sudden storm, an urgent message), ``react_to_event`` records
   a ``ScheduleReaction`` and applies it to the affected activities. The
   reaction type determines the effect: RESCHEDULE shifts activities,
   CANCEL removes them, SUBSTITUTE replaces them, DELAY pushes them back,
   EXPEDITE moves them earlier, and MULTI_TASK merges them into one.

4. **Replanning** -- ``replan_schedule`` regenerates the remaining PENDING
   activities of a schedule based on what has already been completed or
   interrupted, producing a new schedule version. This lets agents adapt
   when a significant portion of the day has been disrupted.

5. **Routine Templates** -- Reusable day-shape templates
   (``RoutineTemplate``) capture the structure of a typical day for an
   agent on a given day of the week. Templates can be created, listed,
   fetched, and applied to existing schedules via ``apply_template``.

The engine is a process-wide singleton accessed via ``get_instance()`` or
the module-level ``get_daily_routine()`` helper. All public methods are
guarded by a reentrant lock for thread safety. In-memory stores are
bounded by capacity constants and use FIFO eviction so the engine never
grows without limit.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity constants
# ---------------------------------------------------------------------------

_MAX_SCHEDULES: int = 5000
_MAX_ACTIVITIES: int = 50000
_MAX_TEMPLATES: int = 200
_MAX_EVENTS: int = 2000
_MAX_REACTIONS: int = 5000


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Return a 16-character hexadecimal identifier."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive range [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key
    returned by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    while len(store) > max_size:
        store.pop(0)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ActivityCategory(Enum):
    """Classification of an activity block by life domain."""
    WORK = "work"
    LEISURE = "leisure"
    SOCIAL = "social"
    REST = "rest"
    MEAL = "meal"
    EXERCISE = "exercise"
    LEARNING = "learning"
    CREATIVE = "creative"
    MAINTENANCE = "maintenance"
    TRAVEL = "travel"
    ERRAND = "errand"
    SPIRITUAL = "spiritual"
    ENTERTAINMENT = "entertainment"


class ScheduleStatus(Enum):
    """Lifecycle state of a daily schedule."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


class ActivityStatus(Enum):
    """Lifecycle state of a single activity block."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    INTERRUPTED = "interrupted"


class TimeOfDay(Enum):
    """Coarse time-of-day band used for routine shaping."""
    EARLY_MORNING = "early_morning"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    LATE_NIGHT = "late_night"


class DayOfWeek(Enum):
    """Day of the week for routine templates and schedules."""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class ReactionType(Enum):
    """How an agent reacts to an unexpected event affecting its schedule."""
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    SUBSTITUTE = "substitute"
    DELAY = "delay"
    EXPEDITE = "expedite"
    MULTI_TASK = "multi_task"


class RoutineEventKind(Enum):
    """Observable event kind emitted by the daily routine engine."""
    SCHEDULE_GENERATED = "schedule_generated"
    ACTIVITY_STARTED = "activity_started"
    ACTIVITY_COMPLETED = "activity_completed"
    ACTIVITY_INTERRUPTED = "activity_interrupted"
    EVENT_REACTED = "event_reacted"
    SCHEDULE_REPLANNED = "schedule_replanned"
    TEMPLATE_CREATED = "template_created"
    TEMPLATE_APPLIED = "template_applied"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ActivityBlock:
    """A single time-bounded activity within a daily schedule.

    Activities are the atomic unit of an agent's routine. Each block is
    owned by a schedule and an agent, occupies a contiguous span of the
    day (``start_hour`` to ``start_hour + duration_hours``), and moves
    through a lifecycle from PENDING to COMPLETED/SKIPPED/INTERRUPTED.
    """

    activity_id: str = field(default_factory=_new_id)
    schedule_id: str = ""
    agent_id: str = ""
    title: str = ""
    description: str = ""
    category: ActivityCategory = ActivityCategory.LEISURE
    start_hour: float = 0.0
    duration_hours: float = 1.0
    location: str = ""
    priority: int = 3
    status: ActivityStatus = ActivityStatus.PENDING
    participants: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this activity block to a JSON-friendly dict.

        Enum fields are serialized via ``.value`` and nested lists/dicts
        are copied so the returned dict is safe to mutate.
        """
        return {
            "activity_id": self.activity_id,
            "schedule_id": self.schedule_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "start_hour": self.start_hour,
            "duration_hours": self.duration_hours,
            "location": self.location,
            "priority": self.priority,
            "status": self.status.value,
            "participants": list(self.participants),
            "tags": list(self.tags),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class DailySchedule:
    """A complete daily schedule for one agent on one date.

    A schedule owns an ordered list of ``ActivityBlock`` entries that
    together fill the agent's wake period. Schedules move through a
    lifecycle: DRAFT -> ACTIVE -> COMPLETED (or INTERRUPTED / CANCELLED).
    """

    schedule_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    date: str = ""
    day_of_week: DayOfWeek = DayOfWeek.MONDAY
    activities: List[ActivityBlock] = field(default_factory=list)
    status: ScheduleStatus = ScheduleStatus.DRAFT
    wake_time: float = 7.0
    sleep_time: float = 23.0
    total_scheduled_hours: float = 0.0
    total_activity_hours: float = 0.0
    generated_at: str = field(default_factory=_now)
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this schedule to a JSON-friendly dict."""
        return {
            "schedule_id": self.schedule_id,
            "agent_id": self.agent_id,
            "date": self.date,
            "day_of_week": self.day_of_week.value,
            "activities": [a.to_dict() for a in self.activities],
            "status": self.status.value,
            "wake_time": self.wake_time,
            "sleep_time": self.sleep_time,
            "total_scheduled_hours": self.total_scheduled_hours,
            "total_activity_hours": self.total_activity_hours,
            "generated_at": self.generated_at,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class RoutineTemplate:
    """A reusable day-shape template for an agent on a given weekday.

    A template captures the structure of a typical day: the wake/sleep
    window and a list of activity templates (plain dicts) that can be
    instantiated into ``ActivityBlock`` entries when the template is
    applied to a schedule.
    """

    template_id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    agent_id: str = ""
    day_of_week: DayOfWeek = DayOfWeek.MONDAY
    wake_time: float = 7.0
    sleep_time: float = 23.0
    activity_templates: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this template to a JSON-friendly dict.

        Activity templates are plain dicts; each is deep-copied so the
        returned representation is safe to mutate. Enum values inside
        the activity templates are converted to their string values so
        the result is always JSON-serializable.
        """
        converted_templates = []
        for at in self.activity_templates:
            converted = {}
            for key, value in at.items():
                if isinstance(value, Enum):
                    converted[key] = value.value
                else:
                    converted[key] = value
            converted_templates.append(converted)
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "agent_id": self.agent_id,
            "day_of_week": self.day_of_week.value,
            "wake_time": self.wake_time,
            "sleep_time": self.sleep_time,
            "activity_templates": converted_templates,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ScheduleReaction:
    """A recorded reaction to an unexpected event affecting a schedule.

    When an agent reacts to a disruption, the engine records a
    ``ScheduleReaction`` describing the trigger, the reaction type, the
    affected activities, and an optional replacement activity. The
    reaction is then applied to the affected activities in place.
    """

    reaction_id: str = field(default_factory=_new_id)
    schedule_id: str = ""
    agent_id: str = ""
    trigger_event: str = ""
    reaction_type: ReactionType = ReactionType.RESCHEDULE
    affected_activity_ids: List[str] = field(default_factory=list)
    replacement_activity: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reaction to a JSON-friendly dict."""
        return {
            "reaction_id": self.reaction_id,
            "schedule_id": self.schedule_id,
            "agent_id": self.agent_id,
            "trigger_event": self.trigger_event,
            "reaction_type": self.reaction_type.value,
            "affected_activity_ids": list(self.affected_activity_ids),
            "replacement_activity": (
                dict(self.replacement_activity)
                if self.replacement_activity is not None
                else None
            ),
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


@dataclass
class RoutineStats:
    """Aggregate statistics over the daily routine engine's stores."""

    total_schedules: int = 0
    total_activities: int = 0
    total_templates: int = 0
    total_reactions: int = 0
    schedules_by_status: Dict[str, int] = field(default_factory=dict)
    activities_by_category: Dict[str, int] = field(default_factory=dict)
    avg_activities_per_schedule: float = 0.0
    completion_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dict."""
        return {
            "total_schedules": self.total_schedules,
            "total_activities": self.total_activities,
            "total_templates": self.total_templates,
            "total_reactions": self.total_reactions,
            "schedules_by_status": dict(self.schedules_by_status),
            "activities_by_category": dict(self.activities_by_category),
            "avg_activities_per_schedule": self.avg_activities_per_schedule,
            "completion_rate": self.completion_rate,
        }


@dataclass
class RoutineEvent:
    """An observable event emitted by the daily routine engine."""

    event_id: str = field(default_factory=_new_id)
    kind: RoutineEventKind = RoutineEventKind.SCHEDULE_GENERATED
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dict."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }


@dataclass
class RoutineSnapshot:
    """A point-in-time snapshot of the entire daily routine engine state."""

    initialized: bool = False
    schedules: List[DailySchedule] = field(default_factory=list)
    activities: List[ActivityBlock] = field(default_factory=list)
    templates: List[RoutineTemplate] = field(default_factory=list)
    reactions: List[ScheduleReaction] = field(default_factory=list)
    events: List[RoutineEvent] = field(default_factory=list)
    stats: RoutineStats = field(default_factory=RoutineStats)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dict."""
        return {
            "initialized": self.initialized,
            "schedules": [s.to_dict() for s in self.schedules],
            "activities": [a.to_dict() for a in self.activities],
            "templates": [t.to_dict() for t in self.templates],
            "reactions": [r.to_dict() for r in self.reactions],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


# ---------------------------------------------------------------------------
# DailyRoutineEngine Singleton
# ---------------------------------------------------------------------------

class DailyRoutineEngine:
    """Singleton engine that manages agent daily routines and schedules.

    The engine generates daily schedules composed of activity blocks,
    drives the activity lifecycle, records reactions to unexpected events,
    replans disrupted schedules, and maintains reusable routine templates.
    All public methods are thread-safe, guarded by a reentrant lock.
    """

    _instance: Optional["DailyRoutineEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton construction
    # ------------------------------------------------------------------

    def __new__(cls) -> "DailyRoutineEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "DailyRoutineEngine":
        """Return the singleton DailyRoutineEngine instance.

        Uses double-checked locking so that calls after initialization
        take the fast path without acquiring the lock. Does NOT reset
        ``_initialized``; only constructs the singleton if it is absent.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Core storage keyed by entity id
            self._schedules: Dict[str, DailySchedule] = {}
            self._activities: Dict[str, ActivityBlock] = {}
            self._templates: Dict[str, RoutineTemplate] = {}
            self._reactions: Dict[str, ScheduleReaction] = {}

            # Observable event log (chronological append-only list)
            self._events: List[RoutineEvent] = []

            # Monotonic counters for diagnostics
            self._schedule_counter: int = 0
            self._activity_counter: int = 0
            self._template_counter: int = 0
            self._reaction_counter: int = 0
            self._event_counter: int = 0

            # Mark initialization complete, then seed baseline data.
            # _seed_data is called at the END of init as required.
            self._initialized: bool = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline routine content.

        Seeds one routine template (``Standard Workday`` for agent_alpha on
        Monday), two daily schedules (agent_alpha and agent_beta on
        2026-07-01), and one schedule reaction (agent_alpha reschedules
        evening leisure to host an unexpected visitor).
        """
        now = _now()

        # --- Routine Template: Standard Workday ----------------------
        workday_template = RoutineTemplate(
            template_id="tpl_workday_alpha",
            name="Standard Workday",
            description=(
                "A typical Monday workday for agent_alpha: morning "
                "routine, commute, focused work, lunch, afternoon work, "
                "and evening leisure."
            ),
            agent_id="agent_alpha",
            day_of_week=DayOfWeek.MONDAY,
            wake_time=7.0,
            sleep_time=23.0,
            activity_templates=[
                {
                    "title": "Breakfast",
                    "description": "Morning meal to start the day.",
                    "category": ActivityCategory.MEAL,
                    "start_hour": 7.0,
                    "duration_hours": 0.5,
                    "location": "Kitchen",
                    "priority": 4,
                    "tags": ["morning", "meal"],
                },
                {
                    "title": "Morning Routine",
                    "description": "Hygiene, dressing, and preparation.",
                    "category": ActivityCategory.MAINTENANCE,
                    "start_hour": 7.5,
                    "duration_hours": 0.5,
                    "location": "Home",
                    "priority": 3,
                    "tags": ["morning", "routine"],
                },
                {
                    "title": "Commute",
                    "description": "Travel to the workplace.",
                    "category": ActivityCategory.TRAVEL,
                    "start_hour": 8.0,
                    "duration_hours": 0.5,
                    "location": "Transit",
                    "priority": 3,
                    "tags": ["travel"],
                },
                {
                    "title": "Morning Work",
                    "description": "Focused deep-work session.",
                    "category": ActivityCategory.WORK,
                    "start_hour": 8.5,
                    "duration_hours": 3.5,
                    "location": "Office",
                    "priority": 5,
                    "tags": ["work", "deep"],
                },
                {
                    "title": "Lunch",
                    "description": "Midday meal and short break.",
                    "category": ActivityCategory.MEAL,
                    "start_hour": 12.0,
                    "duration_hours": 1.0,
                    "location": "Cafeteria",
                    "priority": 4,
                    "tags": ["meal", "break"],
                },
                {
                    "title": "Afternoon Work",
                    "description": "Meetings and collaborative work.",
                    "category": ActivityCategory.WORK,
                    "start_hour": 13.0,
                    "duration_hours": 4.0,
                    "location": "Office",
                    "priority": 5,
                    "tags": ["work", "meetings"],
                },
                {
                    "title": "Evening Leisure",
                    "description": "Relaxation, hobbies, and wind-down.",
                    "category": ActivityCategory.LEISURE,
                    "start_hour": 18.0,
                    "duration_hours": 4.0,
                    "location": "Home",
                    "priority": 2,
                    "tags": ["evening", "leisure"],
                },
            ],
            created_at=now,
            updated_at=now,
        )
        self._templates[workday_template.template_id] = workday_template
        self._template_counter += 1
        self._record_event(
            RoutineEventKind.TEMPLATE_CREATED,
            {
                "template_id": workday_template.template_id,
                "name": workday_template.name,
                "agent_id": workday_template.agent_id,
            },
        )

        # --- Schedule 1: agent_alpha on 2026-07-01 --------------------
        alpha_schedule = DailySchedule(
            schedule_id="sched_alpha_20260701",
            agent_id="agent_alpha",
            date="2026-07-01",
            day_of_week=DayOfWeek.MONDAY,
            status=ScheduleStatus.ACTIVE,
            wake_time=7.0,
            sleep_time=23.0,
            generated_at=now,
            metadata={"source": "seed", "template_id": workday_template.template_id},
        )

        alpha_specs = [
            ("act_alpha_breakfast", "Breakfast", "Morning meal to start the day.",
             ActivityCategory.MEAL, 7.0, 0.5, "Kitchen", 4, ActivityStatus.COMPLETED),
            ("act_alpha_morning", "Morning Routine", "Hygiene, dressing, and preparation.",
             ActivityCategory.MAINTENANCE, 7.5, 0.5, "Home", 3, ActivityStatus.COMPLETED),
            ("act_alpha_commute", "Commute", "Travel to the workplace.",
             ActivityCategory.TRAVEL, 8.0, 0.5, "Transit", 3, ActivityStatus.COMPLETED),
            ("act_alpha_morning_work", "Morning Work", "Focused deep-work session.",
             ActivityCategory.WORK, 8.5, 3.5, "Office", 5, ActivityStatus.IN_PROGRESS),
            ("act_alpha_lunch", "Lunch", "Midday meal and short break.",
             ActivityCategory.MEAL, 12.0, 1.0, "Cafeteria", 4, ActivityStatus.PENDING),
            ("act_alpha_afternoon_work", "Afternoon Work", "Meetings and collaborative work.",
             ActivityCategory.WORK, 13.0, 4.0, "Office", 5, ActivityStatus.PENDING),
            ("act_alpha_leisure", "Evening Leisure", "Relaxation, hobbies, and wind-down.",
             ActivityCategory.LEISURE, 18.0, 4.0, "Home", 2, ActivityStatus.PENDING),
        ]
        for (aid, title, desc, cat, start, dur, loc, prio,
             status) in alpha_specs:
            activity = ActivityBlock(
                activity_id=aid,
                schedule_id=alpha_schedule.schedule_id,
                agent_id=alpha_schedule.agent_id,
                title=title,
                description=desc,
                category=cat,
                start_hour=start,
                duration_hours=dur,
                location=loc,
                priority=prio,
                status=status,
                created_at=now,
                started_at=now if status != ActivityStatus.PENDING else None,
                completed_at=(
                    now if status == ActivityStatus.COMPLETED else None
                ),
            )
            alpha_schedule.activities.append(activity)
            self._activities[activity.activity_id] = activity
            self._activity_counter += 1
        alpha_schedule.total_scheduled_hours = (
            alpha_schedule.sleep_time - alpha_schedule.wake_time
        )
        alpha_schedule.total_activity_hours = sum(
            a.duration_hours for a in alpha_schedule.activities
        )
        self._schedules[alpha_schedule.schedule_id] = alpha_schedule
        self._schedule_counter += 1
        self._record_event(
            RoutineEventKind.SCHEDULE_GENERATED,
            {
                "schedule_id": alpha_schedule.schedule_id,
                "agent_id": alpha_schedule.agent_id,
                "date": alpha_schedule.date,
            },
        )

        # --- Schedule 2: agent_beta on 2026-07-01 ---------------------
        beta_schedule = DailySchedule(
            schedule_id="sched_beta_20260701",
            agent_id="agent_beta",
            date="2026-07-01",
            day_of_week=DayOfWeek.MONDAY,
            status=ScheduleStatus.ACTIVE,
            wake_time=6.5,
            sleep_time=22.5,
            generated_at=now,
            metadata={"source": "seed"},
        )

        beta_specs = [
            ("act_beta_exercise", "Morning Exercise", "Early cardio and stretching.",
             ActivityCategory.EXERCISE, 6.5, 0.75, "Park", 4, ActivityStatus.COMPLETED),
            ("act_beta_breakfast", "Breakfast", "Quick morning meal.",
             ActivityCategory.MEAL, 7.25, 0.5, "Kitchen", 4, ActivityStatus.COMPLETED),
            ("act_beta_study", "Study Session", "Deep learning and coursework.",
             ActivityCategory.LEARNING, 8.0, 4.0, "Library", 5, ActivityStatus.IN_PROGRESS),
            ("act_beta_lunch", "Lunch", "Midday meal and rest.",
             ActivityCategory.MEAL, 12.0, 1.0, "Cafeteria", 4, ActivityStatus.PENDING),
            ("act_beta_research", "Research", "Afternoon research and experiments.",
             ActivityCategory.WORK, 13.5, 3.5, "Lab", 5, ActivityStatus.PENDING),
            ("act_beta_social", "Evening Social", "Dinner with friends.",
             ActivityCategory.SOCIAL, 18.0, 3.0, "Restaurant", 3, ActivityStatus.PENDING),
        ]
        for (aid, title, desc, cat, start, dur, loc, prio,
             status) in beta_specs:
            activity = ActivityBlock(
                activity_id=aid,
                schedule_id=beta_schedule.schedule_id,
                agent_id=beta_schedule.agent_id,
                title=title,
                description=desc,
                category=cat,
                start_hour=start,
                duration_hours=dur,
                location=loc,
                priority=prio,
                status=status,
                created_at=now,
                started_at=now if status != ActivityStatus.PENDING else None,
                completed_at=(
                    now if status == ActivityStatus.COMPLETED else None
                ),
            )
            beta_schedule.activities.append(activity)
            self._activities[activity.activity_id] = activity
            self._activity_counter += 1
        beta_schedule.total_scheduled_hours = (
            beta_schedule.sleep_time - beta_schedule.wake_time
        )
        beta_schedule.total_activity_hours = sum(
            a.duration_hours for a in beta_schedule.activities
        )
        self._schedules[beta_schedule.schedule_id] = beta_schedule
        self._schedule_counter += 1
        self._record_event(
            RoutineEventKind.SCHEDULE_GENERATED,
            {
                "schedule_id": beta_schedule.schedule_id,
                "agent_id": beta_schedule.agent_id,
                "date": beta_schedule.date,
            },
        )

        # --- Reaction: agent_alpha reschedules evening leisure --------
        reaction = ScheduleReaction(
            reaction_id="react_alpha_visitor",
            schedule_id=alpha_schedule.schedule_id,
            agent_id=alpha_schedule.agent_id,
            trigger_event="Unexpected visitor arrived",
            reaction_type=ReactionType.RESCHEDULE,
            affected_activity_ids=["act_alpha_leisure"],
            replacement_activity={
                "title": "Host Visitor",
                "description": "Welcome and entertain the unexpected guest.",
                "category": ActivityCategory.SOCIAL.value,
                "start_hour": 18.0,
                "duration_hours": 2.0,
                "location": "Home",
                "priority": 4,
                "tags": ["social", "visitor"],
            },
            timestamp=now,
            metadata={"source": "seed"},
        )
        self._reactions[reaction.reaction_id] = reaction
        self._reaction_counter += 1
        self._record_event(
            RoutineEventKind.EVENT_REACTED,
            {
                "reaction_id": reaction.reaction_id,
                "schedule_id": reaction.schedule_id,
                "trigger_event": reaction.trigger_event,
                "reaction_type": reaction.reaction_type.value,
            },
        )

        # Enforce capacity bounds after seeding.
        _evict_fifo_dict(self._schedules, _MAX_SCHEDULES)
        _evict_fifo_dict(self._activities, _MAX_ACTIVITIES)
        _evict_fifo_dict(self._templates, _MAX_TEMPLATES)
        _evict_fifo_dict(self._reactions, _MAX_REACTIONS)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _time_of_day(self, hour: float) -> TimeOfDay:
        """Map an hour in [0, 24) to a coarse ``TimeOfDay`` band.

        Assumes the caller already holds ``self._lock``.
        """
        h = _clamp(hour, 0.0, 24.0)
        if h < 4.0:
            return TimeOfDay.LATE_NIGHT
        if h < 6.0:
            return TimeOfDay.EARLY_MORNING
        if h < 9.0:
            return TimeOfDay.MORNING
        if h < 12.0:
            return TimeOfDay.MIDDAY
        if h < 17.0:
            return TimeOfDay.AFTERNOON
        if h < 21.0:
            return TimeOfDay.EVENING
        return TimeOfDay.NIGHT

    def _record_event(
        self, kind: RoutineEventKind, payload: Dict[str, Any]
    ) -> None:
        """Record an observable routine event.

        Assumes the caller already holds ``self._lock``. The event log
        is bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = RoutineEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _recompute_schedule_totals(self, schedule: DailySchedule) -> None:
        """Recompute the aggregate hour totals for a schedule in place.

        ``total_scheduled_hours`` is the length of the wake window; the
        ``total_activity_hours`` is the sum of every activity's duration.
        Assumes the caller already holds ``self._lock``.
        """
        schedule.total_scheduled_hours = _clamp(
            schedule.sleep_time - schedule.wake_time, 0.0, 24.0
        )
        schedule.total_activity_hours = sum(
            a.duration_hours for a in schedule.activities
        )

    def _generate_default_activities(
        self,
        agent_id: str,
        schedule_id: str,
        wake_time: float,
        sleep_time: float,
        preferences: Optional[Dict[str, Any]],
    ) -> List[ActivityBlock]:
        """Generate a default set of activities filling the wake period.

        Produces a balanced day: breakfast, a morning work/study block,
        lunch, an afternoon activity, dinner, evening leisure, and a
        wind-down block. ``preferences`` may override titles, categories,
        locations, and tags for each slot. Assumes the caller holds the
        lock.
        """
        now = _now()
        prefs = preferences or {}
        activities: List[ActivityBlock] = []

        # Resolve window bounds, clamped to a sane day length.
        wake = _clamp(wake_time, 0.0, 24.0)
        sleep = _clamp(sleep_time, 0.0, 24.0)
        if sleep <= wake:
            sleep = wake + 16.0  # default to a 16h wake window

        # Breakfast shortly after waking.
        breakfast_start = wake + 0.25
        breakfast = ActivityBlock(
            schedule_id=schedule_id,
            agent_id=agent_id,
            title=prefs.get("breakfast_title", "Breakfast"),
            description=prefs.get(
                "breakfast_description", "Morning meal to start the day."
            ),
            category=ActivityCategory.MEAL,
            start_hour=breakfast_start,
            duration_hours=0.5,
            location=prefs.get("breakfast_location", "Kitchen"),
            priority=4,
            tags=["morning", "meal"],
            created_at=now,
        )
        activities.append(breakfast)

        # Morning work / study block.
        morning_start = breakfast_start + 0.5
        morning_duration = _clamp(
            12.0 - morning_start, 1.0, 5.0
        )
        morning_work = ActivityBlock(
            schedule_id=schedule_id,
            agent_id=agent_id,
            title=prefs.get("morning_title", "Morning Work"),
            description=prefs.get(
                "morning_description", "Focused deep-work session."
            ),
            category=ActivityCategory.WORK,
            start_hour=morning_start,
            duration_hours=morning_duration,
            location=prefs.get("morning_location", "Office"),
            priority=5,
            tags=["work", "deep"],
            created_at=now,
        )
        activities.append(morning_work)

        # Lunch at midday.
        lunch = ActivityBlock(
            schedule_id=schedule_id,
            agent_id=agent_id,
            title=prefs.get("lunch_title", "Lunch"),
            description=prefs.get(
                "lunch_description", "Midday meal and short break."
            ),
            category=ActivityCategory.MEAL,
            start_hour=12.0,
            duration_hours=1.0,
            location=prefs.get("lunch_location", "Cafeteria"),
            priority=4,
            tags=["meal", "break"],
            created_at=now,
        )
        activities.append(lunch)

        # Afternoon activity (work or learning).
        afternoon_start = 13.0
        afternoon_duration = _clamp(17.0 - afternoon_start, 1.0, 5.0)
        afternoon = ActivityBlock(
            schedule_id=schedule_id,
            agent_id=agent_id,
            title=prefs.get("afternoon_title", "Afternoon Work"),
            description=prefs.get(
                "afternoon_description",
                "Meetings and collaborative work.",
            ),
            category=ActivityCategory.WORK,
            start_hour=afternoon_start,
            duration_hours=afternoon_duration,
            location=prefs.get("afternoon_location", "Office"),
            priority=5,
            tags=["work", "meetings"],
            created_at=now,
        )
        activities.append(afternoon)

        # Dinner in the early evening.
        dinner_start = 18.0
        dinner = ActivityBlock(
            schedule_id=schedule_id,
            agent_id=agent_id,
            title=prefs.get("dinner_title", "Dinner"),
            description=prefs.get(
                "dinner_description", "Evening meal."
            ),
            category=ActivityCategory.MEAL,
            start_hour=dinner_start,
            duration_hours=1.0,
            location=prefs.get("dinner_location", "Home"),
            priority=4,
            tags=["meal", "evening"],
            created_at=now,
        )
        activities.append(dinner)

        # Evening leisure.
        leisure_start = dinner_start + 1.0
        leisure_duration = _clamp(
            sleep - 1.0 - leisure_start, 0.5, 4.0
        )
        evening_leisure = ActivityBlock(
            schedule_id=schedule_id,
            agent_id=agent_id,
            title=prefs.get("leisure_title", "Evening Leisure"),
            description=prefs.get(
                "leisure_description",
                "Relaxation, hobbies, and downtime.",
            ),
            category=ActivityCategory.LEISURE,
            start_hour=leisure_start,
            duration_hours=leisure_duration,
            location=prefs.get("leisure_location", "Home"),
            priority=2,
            tags=["evening", "leisure"],
            created_at=now,
        )
        activities.append(evening_leisure)

        # Wind-down before sleep.
        wind_start = leisure_start + leisure_duration
        wind_duration = _clamp(sleep - wind_start, 0.25, 1.0)
        if wind_duration > 0.0:
            wind_down = ActivityBlock(
                schedule_id=schedule_id,
                agent_id=agent_id,
                title=prefs.get("winddown_title", "Wind-Down"),
                description=prefs.get(
                    "winddown_description",
                    "Prepare for sleep: reading, hygiene, reflection.",
                ),
                category=ActivityCategory.REST,
                start_hour=wind_start,
                duration_hours=wind_duration,
                location=prefs.get("winddown_location", "Bedroom"),
                priority=3,
                tags=["rest", "sleep"],
                created_at=now,
            )
            activities.append(wind_down)

        return activities

    def _instantiate_template(
        self,
        template: RoutineTemplate,
        agent_id: str,
        schedule_id: str,
    ) -> List[ActivityBlock]:
        """Instantiate a template's activity templates into activity blocks.

        Assumes the caller holds the lock.
        """
        now = _now()
        activities: List[ActivityBlock] = []
        for spec in template.activity_templates:
            category = spec.get("category", ActivityCategory.LEISURE)
            if isinstance(category, ActivityCategory):
                cat = category
            elif isinstance(category, str):
                # Tolerate string values coming from serialized templates.
                cat = ActivityCategory(category)
            else:
                cat = ActivityCategory.LEISURE
            activity = ActivityBlock(
                schedule_id=schedule_id,
                agent_id=agent_id,
                title=spec.get("title", "Activity"),
                description=spec.get("description", ""),
                category=cat,
                start_hour=float(spec.get("start_hour", 0.0)),
                duration_hours=float(spec.get("duration_hours", 1.0)),
                location=spec.get("location", ""),
                priority=int(spec.get("priority", 3)),
                tags=list(spec.get("tags", [])),
                created_at=now,
            )
            activities.append(activity)
        return activities

    # ------------------------------------------------------------------
    # Schedule generation and lookup
    # ------------------------------------------------------------------

    def generate_schedule(
        self,
        agent_id: str,
        date: str,
        day_of_week: DayOfWeek,
        wake_time: float = 7.0,
        sleep_time: float = 23.0,
        template_id: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> DailySchedule:
        """Generate a daily schedule with activity blocks.

        If ``template_id`` is provided, the matching ``RoutineTemplate``
        is used to instantiate activities; otherwise activities are
        generated from ``preferences`` or sensible defaults. The wake
        period is filled with meal, work, leisure, social, and rest
        blocks. ``total_scheduled_hours`` and ``total_activity_hours``
        are computed before the schedule is stored.
        """
        with self._lock:
            now = _now()
            schedule = DailySchedule(
                agent_id=agent_id,
                date=date,
                day_of_week=day_of_week,
                status=ScheduleStatus.ACTIVE,
                wake_time=_clamp(wake_time, 0.0, 24.0),
                sleep_time=_clamp(sleep_time, 0.0, 24.0),
                generated_at=now,
                metadata={"source": "generated"},
            )

            if template_id is not None:
                template = self._templates.get(template_id)
                if template is not None:
                    schedule.activities = self._instantiate_template(
                        template, agent_id, schedule.schedule_id
                    )
                    schedule.wake_time = template.wake_time
                    schedule.sleep_time = template.sleep_time
                    schedule.metadata["template_id"] = template_id
                else:
                    # Fall back to defaults if the template is missing.
                    schedule.activities = self._generate_default_activities(
                        agent_id,
                        schedule.schedule_id,
                        schedule.wake_time,
                        schedule.sleep_time,
                        preferences,
                    )
            else:
                schedule.activities = self._generate_default_activities(
                    agent_id,
                    schedule.schedule_id,
                    schedule.wake_time,
                    schedule.sleep_time,
                    preferences,
                )

            # Register every activity in the global activity store.
            for activity in schedule.activities:
                self._activities[activity.activity_id] = activity
                self._activity_counter += 1
            _evict_fifo_dict(self._activities, _MAX_ACTIVITIES)

            self._recompute_schedule_totals(schedule)

            self._schedules[schedule.schedule_id] = schedule
            self._schedule_counter += 1
            _evict_fifo_dict(self._schedules, _MAX_SCHEDULES)

            self._record_event(
                RoutineEventKind.SCHEDULE_GENERATED,
                {
                    "schedule_id": schedule.schedule_id,
                    "agent_id": schedule.agent_id,
                    "date": schedule.date,
                    "template_id": template_id,
                    "activity_count": len(schedule.activities),
                },
            )
            return schedule

    def list_schedules(
        self,
        agent_id: Optional[str] = None,
        status: Optional[ScheduleStatus] = None,
        date: Optional[str] = None,
    ) -> List[DailySchedule]:
        """Return schedules filtered by agent, status, and/or date."""
        with self._lock:
            results: List[DailySchedule] = []
            for schedule in self._schedules.values():
                if agent_id is not None and schedule.agent_id != agent_id:
                    continue
                if status is not None and schedule.status != status:
                    continue
                if date is not None and schedule.date != date:
                    continue
                results.append(schedule)
            return results

    def get_schedule(self, schedule_id: str) -> Optional[DailySchedule]:
        """Return the schedule with the given id, or None if absent."""
        with self._lock:
            return self._schedules.get(schedule_id)

    # ------------------------------------------------------------------
    # Activity lifecycle
    # ------------------------------------------------------------------

    def add_activity(
        self,
        schedule_id: str,
        title: str,
        description: str,
        category: ActivityCategory,
        start_hour: float,
        duration_hours: float,
        location: str = "",
        priority: int = 3,
        participants: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ActivityBlock]:
        """Add a new activity block to an existing schedule.

        Returns the created ``ActivityBlock``, or ``None`` if the
        schedule was not found. The schedule's hour totals are
        recomputed after insertion.
        """
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if schedule is None:
                return None

            activity = ActivityBlock(
                schedule_id=schedule_id,
                agent_id=schedule.agent_id,
                title=title,
                description=description,
                category=category,
                start_hour=_clamp(start_hour, 0.0, 24.0),
                duration_hours=max(0.0, duration_hours),
                location=location,
                priority=int(_clamp(priority, 1, 5)),
                participants=list(participants) if participants else [],
                tags=list(tags) if tags else [],
                metadata=dict(metadata) if metadata else {},
            )
            schedule.activities.append(activity)
            self._activities[activity.activity_id] = activity
            self._activity_counter += 1
            _evict_fifo_dict(self._activities, _MAX_ACTIVITIES)

            self._recompute_schedule_totals(schedule)
            return activity

    def list_activities(
        self,
        schedule_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        category: Optional[ActivityCategory] = None,
        status: Optional[ActivityStatus] = None,
    ) -> List[ActivityBlock]:
        """Return activities filtered by schedule, agent, category, status."""
        with self._lock:
            results: List[ActivityBlock] = []
            for activity in self._activities.values():
                if schedule_id is not None and activity.schedule_id != schedule_id:
                    continue
                if agent_id is not None and activity.agent_id != agent_id:
                    continue
                if category is not None and activity.category != category:
                    continue
                if status is not None and activity.status != status:
                    continue
                results.append(activity)
            return results

    def get_activity(self, activity_id: str) -> Optional[ActivityBlock]:
        """Return the activity with the given id, or None if absent."""
        with self._lock:
            return self._activities.get(activity_id)

    def start_activity(self, activity_id: str) -> Optional[ActivityBlock]:
        """Mark an activity as IN_PROGRESS and record its start time."""
        with self._lock:
            activity = self._activities.get(activity_id)
            if activity is None:
                return None
            activity.status = ActivityStatus.IN_PROGRESS
            activity.started_at = _now()
            self._record_event(
                RoutineEventKind.ACTIVITY_STARTED,
                {
                    "activity_id": activity.activity_id,
                    "schedule_id": activity.schedule_id,
                    "title": activity.title,
                },
            )
            return activity

    def complete_activity(self, activity_id: str) -> Optional[ActivityBlock]:
        """Mark an activity as COMPLETED and record its completion time."""
        with self._lock:
            activity = self._activities.get(activity_id)
            if activity is None:
                return None
            activity.status = ActivityStatus.COMPLETED
            activity.completed_at = _now()
            if activity.started_at is None:
                activity.started_at = activity.completed_at
            self._record_event(
                RoutineEventKind.ACTIVITY_COMPLETED,
                {
                    "activity_id": activity.activity_id,
                    "schedule_id": activity.schedule_id,
                    "title": activity.title,
                },
            )
            return activity

    def skip_activity(self, activity_id: str) -> Optional[ActivityBlock]:
        """Mark an activity as SKIPPED."""
        with self._lock:
            activity = self._activities.get(activity_id)
            if activity is None:
                return None
            activity.status = ActivityStatus.SKIPPED
            return activity

    def interrupt_activity(self, activity_id: str) -> Optional[ActivityBlock]:
        """Mark an activity as INTERRUPTED and emit an interruption event."""
        with self._lock:
            activity = self._activities.get(activity_id)
            if activity is None:
                return None
            activity.status = ActivityStatus.INTERRUPTED
            self._record_event(
                RoutineEventKind.ACTIVITY_INTERRUPTED,
                {
                    "activity_id": activity.activity_id,
                    "schedule_id": activity.schedule_id,
                    "title": activity.title,
                },
            )
            return activity

    def update_activity(
        self, activity_id: str, **kwargs: Any
    ) -> Optional[ActivityBlock]:
        """Update one or more fields of an activity block.

        Only known ``ActivityBlock`` fields are applied; unknown keys are
        ignored. Enum-valued fields accept either an enum member or a
        string value.
        """
        with self._lock:
            activity = self._activities.get(activity_id)
            if activity is None:
                return None

            known_fields = {
                "title", "description", "category", "start_hour",
                "duration_hours", "location", "priority", "status",
                "participants", "tags", "started_at", "completed_at",
                "metadata",
            }
            for key, value in kwargs.items():
                if key not in known_fields:
                    continue
                if key == "category" and isinstance(value, str):
                    value = ActivityCategory(value)
                if key == "status" and isinstance(value, str):
                    value = ActivityStatus(value)
                if key in ("participants", "tags") and value is not None:
                    value = list(value)
                if key == "metadata" and value is not None:
                    value = dict(value)
                if key == "start_hour":
                    value = _clamp(float(value), 0.0, 24.0)
                if key == "duration_hours":
                    value = max(0.0, float(value))
                if key == "priority":
                    value = int(_clamp(value, 1, 5))
                setattr(activity, key, value)

            # Propagate changes to the owning schedule's activity list.
            schedule = self._schedules.get(activity.schedule_id)
            if schedule is not None:
                for i, a in enumerate(schedule.activities):
                    if a.activity_id == activity.activity_id:
                        schedule.activities[i] = activity
                        break
                self._recompute_schedule_totals(schedule)
            return activity

    # ------------------------------------------------------------------
    # Event reactions and replanning
    # ------------------------------------------------------------------

    def react_to_event(
        self,
        schedule_id: str,
        trigger_event: str,
        reaction_type: ReactionType,
        affected_activity_ids: List[str],
        replacement_activity: Optional[Dict[str, Any]] = None,
    ) -> ScheduleReaction:
        """Record a reaction to an unexpected event and apply it.

        The reaction is applied to each affected activity according to
        ``reaction_type``:

        * RESCHEDULE -- shift affected activities to the replacement's
          start time when one is supplied.
        * CANCEL -- remove the affected activities from the schedule.
        * SUBSTITUTE -- replace each affected activity with the
          replacement activity spec.
        * DELAY -- push each affected activity later by the replacement's
          ``duration_hours`` (default 1.0).
        * EXPEDITE -- move each affected activity earlier by the
          replacement's ``duration_hours`` (default 1.0).
        * MULTI_TASK -- merge the affected activities into a single
          combined activity.

        The returned ``ScheduleReaction`` is also stored in the engine.
        """
        with self._lock:
            now = _now()
            schedule = self._schedules.get(schedule_id)
            agent_id = schedule.agent_id if schedule is not None else ""

            reaction = ScheduleReaction(
                schedule_id=schedule_id,
                agent_id=agent_id,
                trigger_event=trigger_event,
                reaction_type=reaction_type,
                affected_activity_ids=list(affected_activity_ids),
                replacement_activity=(
                    dict(replacement_activity)
                    if replacement_activity is not None
                    else None
                ),
                timestamp=now,
                metadata={"applied": True},
            )
            self._reactions[reaction.reaction_id] = reaction
            self._reaction_counter += 1
            _evict_fifo_dict(self._reactions, _MAX_REACTIONS)

            if schedule is None:
                self._record_event(
                    RoutineEventKind.EVENT_REACTED,
                    {
                        "reaction_id": reaction.reaction_id,
                        "schedule_id": schedule_id,
                        "trigger_event": trigger_event,
                        "reaction_type": reaction_type.value,
                        "applied": False,
                    },
                )
                return reaction

            affected = [
                a for a in schedule.activities
                if a.activity_id in affected_activity_ids
            ]

            if reaction_type == ReactionType.RESCHEDULE:
                if replacement_activity is not None:
                    new_start = float(
                        replacement_activity.get("start_hour", 18.0)
                    )
                    for a in affected:
                        a.start_hour = _clamp(new_start, 0.0, 24.0)
            elif reaction_type == ReactionType.CANCEL:
                cancel_ids = set(affected_activity_ids)
                schedule.activities = [
                    a for a in schedule.activities
                    if a.activity_id not in cancel_ids
                ]
                for a in affected:
                    a.status = ActivityStatus.INTERRUPTED
            elif reaction_type == ReactionType.SUBSTITUTE:
                if replacement_activity is not None:
                    for a in affected:
                        a.title = replacement_activity.get(
                            "title", a.title
                        )
                        a.description = replacement_activity.get(
                            "description", a.description
                        )
                        cat_val = replacement_activity.get(
                            "category", a.category
                        )
                        if isinstance(cat_val, str):
                            a.category = ActivityCategory(cat_val)
                        elif isinstance(cat_val, ActivityCategory):
                            a.category = cat_val
                        a.start_hour = _clamp(
                            float(
                                replacement_activity.get(
                                    "start_hour", a.start_hour
                                )
                            ),
                            0.0,
                            24.0,
                        )
                        a.duration_hours = float(
                            replacement_activity.get(
                                "duration_hours", a.duration_hours
                            )
                        )
                        a.location = replacement_activity.get(
                            "location", a.location
                        )
                        a.priority = int(
                            replacement_activity.get("priority", a.priority)
                        )
            elif reaction_type == ReactionType.DELAY:
                shift = float(
                    (replacement_activity or {}).get("duration_hours", 1.0)
                )
                for a in affected:
                    a.start_hour = _clamp(
                        a.start_hour + shift, 0.0, 24.0
                    )
            elif reaction_type == ReactionType.EXPEDITE:
                shift = float(
                    (replacement_activity or {}).get("duration_hours", 1.0)
                )
                for a in affected:
                    a.start_hour = _clamp(
                        a.start_hour - shift, 0.0, 24.0
                    )
            elif reaction_type == ReactionType.MULTI_TASK:
                if affected:
                    first = affected[0]
                    total_dur = sum(
                        a.duration_hours for a in affected
                    )
                    first.title = "Multi-Task: " + " + ".join(
                        a.title for a in affected
                    )
                    first.duration_hours = total_dur
                    first.tags = sorted(
                        set().union(*(a.tags for a in affected))
                    )
                    merged_ids = {
                        a.activity_id for a in affected[1:]
                    }
                    schedule.activities = [
                        a for a in schedule.activities
                        if a.activity_id not in merged_ids
                    ]
                    for a in affected[1:]:
                        a.status = ActivityStatus.INTERRUPTED

            self._recompute_schedule_totals(schedule)

            self._record_event(
                RoutineEventKind.EVENT_REACTED,
                {
                    "reaction_id": reaction.reaction_id,
                    "schedule_id": schedule_id,
                    "trigger_event": trigger_event,
                    "reaction_type": reaction_type.value,
                    "affected_count": len(affected),
                    "applied": True,
                },
            )
            return reaction

    def list_reactions(
        self,
        schedule_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[ScheduleReaction]:
        """Return reactions filtered by schedule and/or agent."""
        with self._lock:
            results: List[ScheduleReaction] = []
            for reaction in self._reactions.values():
                if schedule_id is not None and reaction.schedule_id != schedule_id:
                    continue
                if agent_id is not None and reaction.agent_id != agent_id:
                    continue
                results.append(reaction)
            return results

    def replan_schedule(self, schedule_id: str) -> Optional[DailySchedule]:
        """Regenerate the pending activities of a schedule.

        Completed and interrupted activities are preserved. Remaining
        PENDING activities are discarded and regenerated to fill the
        window from the last completed/interrupted activity's end to the
        sleep time. A new schedule version is created and stored; the
        original schedule is marked INTERRUPTED.
        """
        with self._lock:
            original = self._schedules.get(schedule_id)
            if original is None:
                return None

            now = _now()
            new_schedule = DailySchedule(
                agent_id=original.agent_id,
                date=original.date,
                day_of_week=original.day_of_week,
                status=ScheduleStatus.ACTIVE,
                wake_time=original.wake_time,
                sleep_time=original.sleep_time,
                generated_at=now,
                metadata={
                    "source": "replan",
                    "replan_of": original.schedule_id,
                },
            )

            # Carry over completed and interrupted activities.
            carried: List[ActivityBlock] = []
            for activity in original.activities:
                if activity.status in (
                    ActivityStatus.COMPLETED,
                    ActivityStatus.INTERRUPTED,
                ):
                    carried.append(activity)
            carried.sort(key=lambda a: a.start_hour)

            # Determine where to resume scheduling.
            if carried:
                last = carried[-1]
                resume_hour = _clamp(
                    last.start_hour + last.duration_hours,
                    original.wake_time,
                    original.sleep_time,
                )
            else:
                resume_hour = original.wake_time

            # Regenerate pending activities for the remaining window.
            remaining_prefs = {
                "morning_title": "Continued Work",
                "morning_description": "Resumed focused work after replan.",
                "afternoon_title": "Continued Work",
                "afternoon_description": "Resumed afternoon work after replan.",
            }
            regenerated = self._generate_default_activities(
                original.agent_id,
                new_schedule.schedule_id,
                resume_hour,
                original.sleep_time,
                remaining_prefs,
            )
            # Shift regenerated activities so they begin at resume_hour.
            if regenerated:
                base_start = regenerated[0].start_hour
                shift = resume_hour - base_start
                if shift != 0.0:
                    for a in regenerated:
                        a.start_hour = _clamp(
                            a.start_hour + shift, 0.0, 24.0
                        )

            new_schedule.activities = carried + regenerated
            for activity in regenerated:
                self._activities[activity.activity_id] = activity
                self._activity_counter += 1
            _evict_fifo_dict(self._activities, _MAX_ACTIVITIES)

            self._recompute_schedule_totals(new_schedule)

            # Mark the original schedule as interrupted.
            original.status = ScheduleStatus.INTERRUPTED

            self._schedules[new_schedule.schedule_id] = new_schedule
            self._schedule_counter += 1
            _evict_fifo_dict(self._schedules, _MAX_SCHEDULES)

            self._record_event(
                RoutineEventKind.SCHEDULE_REPLANNED,
                {
                    "original_schedule_id": original.schedule_id,
                    "new_schedule_id": new_schedule.schedule_id,
                    "agent_id": new_schedule.agent_id,
                    "carried_count": len(carried),
                    "regenerated_count": len(regenerated),
                },
            )
            return new_schedule

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def create_template(
        self,
        name: str,
        description: str,
        agent_id: str,
        day_of_week: DayOfWeek,
        wake_time: float,
        sleep_time: float,
        activity_templates: List[Dict[str, Any]],
    ) -> RoutineTemplate:
        """Create and store a new routine template."""
        with self._lock:
            now = _now()
            template = RoutineTemplate(
                name=name,
                description=description,
                agent_id=agent_id,
                day_of_week=day_of_week,
                wake_time=_clamp(wake_time, 0.0, 24.0),
                sleep_time=_clamp(sleep_time, 0.0, 24.0),
                activity_templates=[dict(at) for at in activity_templates],
                created_at=now,
                updated_at=now,
            )
            self._templates[template.template_id] = template
            self._template_counter += 1
            _evict_fifo_dict(self._templates, _MAX_TEMPLATES)
            self._record_event(
                RoutineEventKind.TEMPLATE_CREATED,
                {
                    "template_id": template.template_id,
                    "name": template.name,
                    "agent_id": template.agent_id,
                },
            )
            return template

    def list_templates(
        self,
        agent_id: Optional[str] = None,
        day_of_week: Optional[DayOfWeek] = None,
    ) -> List[RoutineTemplate]:
        """Return templates filtered by agent and/or day of week."""
        with self._lock:
            results: List[RoutineTemplate] = []
            for template in self._templates.values():
                if agent_id is not None and template.agent_id != agent_id:
                    continue
                if day_of_week is not None and template.day_of_week != day_of_week:
                    continue
                results.append(template)
            return results

    def get_template(self, template_id: str) -> Optional[RoutineTemplate]:
        """Return the template with the given id, or None if absent."""
        with self._lock:
            return self._templates.get(template_id)

    def apply_template(
        self, schedule_id: str, template_id: str
    ) -> Optional[DailySchedule]:
        """Apply a template to an existing schedule, replacing activities.

        The schedule's wake/sleep window is updated to match the
        template, all existing activities are dropped, and the template's
        activity templates are instantiated in their place. Returns the
        updated schedule, or ``None`` if either the schedule or the
        template is missing.
        """
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if schedule is None:
                return None
            template = self._templates.get(template_id)
            if template is None:
                return None

            # Drop existing activities from the global store.
            for old_activity in schedule.activities:
                self._activities.pop(old_activity.activity_id, None)

            schedule.wake_time = template.wake_time
            schedule.sleep_time = template.sleep_time
            schedule.activities = self._instantiate_template(
                template, schedule.agent_id, schedule.schedule_id
            )
            for activity in schedule.activities:
                self._activities[activity.activity_id] = activity
                self._activity_counter += 1
            _evict_fifo_dict(self._activities, _MAX_ACTIVITIES)

            self._recompute_schedule_totals(schedule)
            schedule.metadata["template_id"] = template_id

            self._record_event(
                RoutineEventKind.TEMPLATE_APPLIED,
                {
                    "schedule_id": schedule.schedule_id,
                    "template_id": template_id,
                    "activity_count": len(schedule.activities),
                },
            )
            return schedule

    # ------------------------------------------------------------------
    # Schedule completion
    # ------------------------------------------------------------------

    def complete_schedule(self, schedule_id: str) -> Optional[DailySchedule]:
        """Mark a schedule as COMPLETED and record its completion time."""
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if schedule is None:
                return None
            schedule.status = ScheduleStatus.COMPLETED
            schedule.completed_at = _now()
            return schedule

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[RoutineEvent]:
        """Return the most recent routine events, newest first."""
        with self._lock:
            if limit <= 0:
                return []
            events = list(self._events)
            events.reverse()
            return events[:limit]

    def get_stats(self) -> RoutineStats:
        """Compute aggregate statistics over the engine's stores."""
        with self._lock:
            total_schedules = len(self._schedules)
            total_activities = len(self._activities)
            total_templates = len(self._templates)
            total_reactions = len(self._reactions)

            schedules_by_status: Dict[str, int] = {}
            for schedule in self._schedules.values():
                key = schedule.status.value
                schedules_by_status[key] = (
                    schedules_by_status.get(key, 0) + 1
                )

            activities_by_category: Dict[str, int] = {}
            for activity in self._activities.values():
                key = activity.category.value
                activities_by_category[key] = (
                    activities_by_category.get(key, 0) + 1
                )

            if total_schedules > 0:
                avg_activities = total_activities / total_schedules
            else:
                avg_activities = 0.0

            completed_schedules = schedules_by_status.get(
                ScheduleStatus.COMPLETED.value, 0
            )
            if total_schedules > 0:
                completion_rate = completed_schedules / total_schedules
            else:
                completion_rate = 0.0

            return RoutineStats(
                total_schedules=total_schedules,
                total_activities=total_activities,
                total_templates=total_templates,
                total_reactions=total_reactions,
                schedules_by_status=schedules_by_status,
                activities_by_category=activities_by_category,
                avg_activities_per_schedule=avg_activities,
                completion_rate=completion_rate,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the engine.

        The ``initialized`` flag is always the first key so callers can
        cheaply verify the engine is ready before inspecting counts.
        """
        with self._lock:
            return {
                "initialized": self._initialized,
                "engine_id": id(self),
                "total_schedules": len(self._schedules),
                "total_activities": len(self._activities),
                "total_templates": len(self._templates),
                "total_reactions": len(self._reactions),
                "total_events": len(self._events),
                "schedule_counter": self._schedule_counter,
                "activity_counter": self._activity_counter,
                "template_counter": self._template_counter,
                "reaction_counter": self._reaction_counter,
                "event_counter": self._event_counter,
                "max_schedules": _MAX_SCHEDULES,
                "max_activities": _MAX_ACTIVITIES,
                "max_templates": _MAX_TEMPLATES,
                "max_events": _MAX_EVENTS,
                "max_reactions": _MAX_REACTIONS,
            }

    def get_snapshot(self) -> RoutineSnapshot:
        """Capture a point-in-time snapshot of the engine state."""
        with self._lock:
            return RoutineSnapshot(
                initialized=self._initialized,
                schedules=list(self._schedules.values()),
                activities=list(self._activities.values()),
                templates=list(self._templates.values()),
                reactions=list(self._reactions.values()),
                events=list(self._events),
                stats=self.get_stats(),
            )

    def reset(self) -> None:
        """Reset the engine to its initial seeded state."""
        with self._lock:
            self._schedules.clear()
            self._activities.clear()
            self._templates.clear()
            self._reactions.clear()
            self._events.clear()
            self._schedule_counter = 0
            self._activity_counter = 0
            self._template_counter = 0
            self._reaction_counter = 0
            self._event_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_daily_routine() -> DailyRoutineEngine:
    """Return the singleton DailyRoutineEngine instance."""
    return DailyRoutineEngine.get_instance()
