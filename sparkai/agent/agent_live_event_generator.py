"""
SparkLabs Agent - AI Live Event & Seasonal Content Generator

A runtime module that generates time-limited events, seasonal festivals,
and rotating challenges for the SparkLabs AI-native game engine. The
generator designs event content, attaches rewards, schedules activation
windows, manages the full event lifecycle (draft -> scheduled ->
announced -> active -> ending -> completed), tracks participants, and
exposes reusable templates for recurring seasonal content.

This module embodies the AI-native principle: live content is not a
static calendar authored by hand but a generative, observable system
that an intelligent agent provisions, schedules, and retunes while
players are in-session.

Architecture:
  LiveEventGenerator (singleton)
    |-- LiveEvent, EventReward, EventSchedule, EventTemplate,
        EventParticipant, EventMetrics, LiveEventStats, LiveEventSnapshot,
        LiveEventEvent
    |-- EventType, EventStatus, EventScope, RewardType, EventTemplateType,
        LiveEventEventKind

Core Capabilities:
  - create_event / update_event / get_event / list_events / delete_event:
    full CRUD over live event definitions.
  - schedule_event / announce_event / activate_event / complete_event /
    cancel_event: event lifecycle management from draft to completion.
  - register_participant / list_participants: participant tracking and
    scoring per event.
  - create_template / get_template / list_templates: reusable event
    templates for seasonal and recurring content.
  - create_reward / list_rewards: reward catalog attachable to events.
  - list_events_log / get_stats / get_status / get_snapshot / reset:
    observability and state management.
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

_MAX_EVENTS: int = 1000
_MAX_TEMPLATES: int = 200
_MAX_REWARDS: int = 500
_MAX_SCHEDULES: int = 1000
_MAX_PARTICIPANTS_PER_EVENT: int = 10000
_MAX_METRICS: int = 1000
_MAX_EVENT_LOG: int = 5000


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
    if isinstance(value, (list, tuple)):
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


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class EventType(Enum):
    TOURNAMENT = "tournament"
    SEASONAL_FESTIVAL = "seasonal_festival"
    COMMUNITY_CHALLENGE = "community_challenge"
    LIMITED_TIME_QUEST = "limited_time_quest"
    DOUBLE_XP_WEEKEND = "double_xp_weekend"
    BOSS_RAID = "boss_raid"
    TRADING_FAIR = "trading_fair"
    LEADERBOARD_RACE = "leaderboard_race"
    CUSTOM = "custom"


class EventStatus(Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ANNOUNCED = "announced"
    ACTIVE = "active"
    ENDING = "ending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventScope(Enum):
    GLOBAL = "global"
    REGIONAL = "regional"
    CLAN = "clan"
    GUILD = "guild"
    SERVER = "server"


class RewardType(Enum):
    CURRENCY = "currency"
    ITEM = "item"
    COSMETIC = "cosmetic"
    XP = "xp"
    BADGE = "badge"
    TITLE = "title"
    BUNDLE = "bundle"


class EventTemplateType(Enum):
    HOLIDAY = "holiday"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    MILESTONE = "milestone"
    SPONTANEOUS = "spontaneous"


class LiveEventEventKind(Enum):
    EVENT_CREATED = "event_created"
    EVENT_UPDATED = "event_updated"
    EVENT_DELETED = "event_deleted"
    EVENT_SCHEDULED = "event_scheduled"
    EVENT_ANNOUNCED = "event_announced"
    EVENT_ACTIVATED = "event_activated"
    EVENT_COMPLETED = "event_completed"
    EVENT_CANCELLED = "event_cancelled"
    PARTICIPANT_REGISTERED = "participant_registered"
    TEMPLATE_CREATED = "template_created"
    REWARD_CREATED = "reward_created"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class EventReward:
    """A reward definition attachable to one or more live events."""
    reward_id: str
    name: str
    reward_type: RewardType
    description: str = ""
    amount: int = 0
    rarity: str = "common"
    item_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EventSchedule:
    """Scheduling window and recurrence rules for a live event."""
    schedule_id: str
    start_time: str = ""
    end_time: str = ""
    timezone: str = "UTC"
    recurrence: str = "none"
    recurrence_interval_days: int = 0
    duration_minutes: int = 0
    blackout_windows: List[Dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LiveEvent:
    """A live event definition: content, scope, status, and reward links."""
    event_id: str
    name: str
    event_type: EventType
    description: str = ""
    scope: EventScope = EventScope.GLOBAL
    status: EventStatus = EventStatus.DRAFT
    schedule_id: str = ""
    reward_ids: List[str] = field(default_factory=list)
    theme: str = ""
    min_level: int = 0
    max_participants: int = 0
    participant_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    started_at: str = ""
    ended_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EventTemplate:
    """A reusable template for recurring or seasonal event generation."""
    template_id: str
    name: str
    template_type: EventTemplateType
    event_type: EventType
    description: str = ""
    default_duration_minutes: int = 60
    default_scope: EventScope = EventScope.GLOBAL
    default_min_level: int = 0
    reward_blueprint: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EventParticipant:
    """A participant registered for a specific live event."""
    participant_id: str
    event_id: str
    player_id: str
    clan_id: str = ""
    registered_at: str = field(default_factory=_now)
    score: float = 0.0
    rank: int = 0
    rewards_claimed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EventMetrics:
    """Aggregated participation and engagement metrics for an event."""
    metrics_id: str
    event_id: str
    participants_joined: int = 0
    participants_completed: int = 0
    peak_concurrent: int = 0
    total_score: float = 0.0
    rewards_distributed: int = 0
    engagement_score: float = 0.0
    satisfaction_score: float = 0.0
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LiveEventStats:
    total_events: int = 0
    active_events: int = 0
    scheduled_events: int = 0
    completed_events: int = 0
    cancelled_events: int = 0
    total_participants: int = 0
    total_rewards: int = 0
    total_templates: int = 0
    total_schedules: int = 0
    total_event_log: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LiveEventSnapshot:
    events: List[Dict[str, Any]] = field(default_factory=list)
    templates: List[Dict[str, Any]] = field(default_factory=list)
    rewards: List[Dict[str, Any]] = field(default_factory=list)
    schedules: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LiveEventEvent:
    """An internal audit-log entry recording a state transition."""
    event_id: str
    kind: LiveEventEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Live Event Generator Singleton
# ---------------------------------------------------------------------------


class LiveEventGenerator:
    """AI-native generator for time-limited events and seasonal content."""

    _instance: Optional["LiveEventGenerator"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "LiveEventGenerator":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "LiveEventGenerator":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._events: Dict[str, LiveEvent] = {}
            self._rewards: Dict[str, EventReward] = {}
            self._schedules: Dict[str, EventSchedule] = {}
            self._templates: Dict[str, EventTemplate] = {}
            self._participants: Dict[str, List[EventParticipant]] = {}
            self._metrics: Dict[str, EventMetrics] = {}
            self._event_log: List[LiveEventEvent] = []
            self._seed_data()
            self._initialized = True

    def _emit(self, kind: LiveEventEventKind, data: Dict[str, Any]) -> None:
        entry = LiveEventEvent(
            event_id=_new_id("log"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._event_log.append(entry)
        _evict_fifo_list(self._event_log, _MAX_EVENT_LOG)

    # ------------------------------------------------------------------
    # Event Management
    # ------------------------------------------------------------------

    def create_event(
        self,
        name: str,
        event_type: EventType,
        description: str = "",
        scope: EventScope = EventScope.GLOBAL,
        theme: str = "",
        min_level: int = 0,
        max_participants: int = 0,
        tags: List[str] = None,
        reward_ids: List[str] = None,
        start_time: str = "",
        end_time: str = "",
        timezone: str = "UTC",
        recurrence: str = "none",
        recurrence_interval_days: int = 0,
        metadata: Dict[str, Any] = None,
    ) -> LiveEvent:
        with self._lock:
            schedule_id = ""
            if start_time or end_time:
                schedule = EventSchedule(
                    schedule_id=_new_id("sch"),
                    start_time=start_time,
                    end_time=end_time,
                    timezone=timezone,
                    recurrence=recurrence,
                    recurrence_interval_days=recurrence_interval_days,
                )
                self._schedules[schedule.schedule_id] = schedule
                _evict_fifo_dict(self._schedules, _MAX_SCHEDULES)
                schedule_id = schedule.schedule_id

            event = LiveEvent(
                event_id=_new_id("evt"),
                name=name,
                event_type=event_type,
                description=description,
                scope=scope,
                theme=theme,
                min_level=min_level,
                max_participants=max_participants,
                tags=tags or [],
                reward_ids=reward_ids or [],
                schedule_id=schedule_id,
                metadata=metadata or {},
            )
            self._events[event.event_id] = event
            _evict_fifo_dict(self._events, _MAX_EVENTS)

            self._participants[event.event_id] = []
            self._metrics[event.event_id] = EventMetrics(
                metrics_id=_new_id("mtx"),
                event_id=event.event_id,
            )
            _evict_fifo_dict(self._metrics, _MAX_METRICS)

            self._emit(LiveEventEventKind.EVENT_CREATED, {
                "event_id": event.event_id,
                "name": name,
                "event_type": event_type.value,
            })
            return event

    def update_event(
        self,
        event_id: str,
        updates: Dict[str, Any],
    ) -> Optional[LiveEvent]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            terminal = (EventStatus.COMPLETED, EventStatus.CANCELLED)
            if event.status in terminal:
                return None
            for k, v in updates.items():
                if k in ("event_id", "created_at", "started_at", "ended_at"):
                    continue
                if k == "event_type" and isinstance(v, str):
                    try:
                        v = EventType(v)
                    except ValueError:
                        continue
                if k == "scope" and isinstance(v, str):
                    try:
                        v = EventScope(v)
                    except ValueError:
                        continue
                if k == "status" and isinstance(v, str):
                    try:
                        v = EventStatus(v)
                    except ValueError:
                        continue
                if hasattr(event, k):
                    setattr(event, k, v)
            event.updated_at = _now()
            self._emit(LiveEventEventKind.EVENT_UPDATED, {"event_id": event_id})
            return event

    def get_event(self, event_id: str) -> Optional[LiveEvent]:
        with self._lock:
            return self._events.get(event_id)

    def list_events(
        self,
        event_type: EventType = None,
        status: EventStatus = None,
        scope: EventScope = None,
        limit: int = 100,
    ) -> List[LiveEvent]:
        with self._lock:
            items = list(self._events.values())
            if event_type is not None:
                items = [e for e in items if e.event_type == event_type]
            if status is not None:
                items = [e for e in items if e.status == status]
            if scope is not None:
                items = [e for e in items if e.scope == scope]
            return items[-limit:]

    def delete_event(self, event_id: str) -> bool:
        with self._lock:
            if event_id not in self._events:
                return False
            del self._events[event_id]
            self._participants.pop(event_id, None)
            self._metrics.pop(event_id, None)
            self._emit(LiveEventEventKind.EVENT_DELETED, {"event_id": event_id})
            return True

    # ------------------------------------------------------------------
    # Event Lifecycle
    # ------------------------------------------------------------------

    def schedule_event(
        self,
        event_id: str,
        start_time: str = "",
        end_time: str = "",
        timezone: str = "UTC",
        recurrence: str = "none",
        recurrence_interval_days: int = 0,
    ) -> Optional[LiveEvent]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            if event.status != EventStatus.DRAFT:
                return None
            if not event.schedule_id:
                schedule = EventSchedule(
                    schedule_id=_new_id("sch"),
                    start_time=start_time,
                    end_time=end_time,
                    timezone=timezone,
                    recurrence=recurrence,
                    recurrence_interval_days=recurrence_interval_days,
                )
                self._schedules[schedule.schedule_id] = schedule
                _evict_fifo_dict(self._schedules, _MAX_SCHEDULES)
                event.schedule_id = schedule.schedule_id
            else:
                schedule = self._schedules.get(event.schedule_id)
                if schedule is not None:
                    if start_time:
                        schedule.start_time = start_time
                    if end_time:
                        schedule.end_time = end_time
                    if timezone:
                        schedule.timezone = timezone
                    if recurrence:
                        schedule.recurrence = recurrence
                    if recurrence_interval_days:
                        schedule.recurrence_interval_days = recurrence_interval_days
            event.status = EventStatus.SCHEDULED
            event.updated_at = _now()
            self._emit(LiveEventEventKind.EVENT_SCHEDULED, {"event_id": event_id})
            return event

    def announce_event(self, event_id: str) -> Optional[LiveEvent]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            if event.status != EventStatus.SCHEDULED:
                return None
            event.status = EventStatus.ANNOUNCED
            event.updated_at = _now()
            self._emit(LiveEventEventKind.EVENT_ANNOUNCED, {"event_id": event_id})
            return event

    def activate_event(self, event_id: str) -> Optional[LiveEvent]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            if event.status not in (EventStatus.ANNOUNCED, EventStatus.SCHEDULED):
                return None
            event.status = EventStatus.ACTIVE
            event.started_at = _now()
            event.updated_at = _now()
            self._emit(LiveEventEventKind.EVENT_ACTIVATED, {"event_id": event_id})
            return event

    def complete_event(self, event_id: str) -> Optional[LiveEvent]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            if event.status not in (EventStatus.ACTIVE, EventStatus.ENDING):
                return None
            event.status = EventStatus.COMPLETED
            event.ended_at = _now()
            event.updated_at = _now()
            metrics = self._metrics.get(event_id)
            if metrics is not None:
                participants = self._participants.get(event_id, [])
                metrics.participants_joined = len(participants)
                metrics.participants_completed = sum(
                    1 for p in participants if p.rewards_claimed
                )
                metrics.total_score = sum(p.score for p in participants)
                metrics.updated_at = _now()
            self._emit(LiveEventEventKind.EVENT_COMPLETED, {"event_id": event_id})
            return event

    def cancel_event(self, event_id: str) -> Optional[LiveEvent]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            terminal = (EventStatus.COMPLETED, EventStatus.CANCELLED)
            if event.status in terminal:
                return None
            event.status = EventStatus.CANCELLED
            event.ended_at = _now()
            event.updated_at = _now()
            self._emit(LiveEventEventKind.EVENT_CANCELLED, {"event_id": event_id})
            return event

    # ------------------------------------------------------------------
    # Participant Management
    # ------------------------------------------------------------------

    def register_participant(
        self,
        event_id: str,
        player_id: str,
        clan_id: str = "",
        score: float = 0.0,
        metadata: Dict[str, Any] = None,
    ) -> Optional[EventParticipant]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            open_states = (
                EventStatus.ANNOUNCED,
                EventStatus.ACTIVE,
                EventStatus.ENDING,
            )
            if event.status not in open_states:
                return None
            participants = self._participants.setdefault(event_id, [])
            for p in participants:
                if p.player_id == player_id:
                    return p
            if (
                event.max_participants
                and len(participants) >= event.max_participants
            ):
                return None
            participant = EventParticipant(
                participant_id=_new_id("par"),
                event_id=event_id,
                player_id=player_id,
                clan_id=clan_id,
                score=score,
                metadata=metadata or {},
            )
            participants.append(participant)
            _evict_fifo_list(participants, _MAX_PARTICIPANTS_PER_EVENT)
            event.participant_count = len(participants)
            event.updated_at = _now()
            self._emit(LiveEventEventKind.PARTICIPANT_REGISTERED, {
                "event_id": event_id,
                "player_id": player_id,
            })
            return participant

    def list_participants(
        self,
        event_id: str,
        limit: int = 100,
    ) -> List[EventParticipant]:
        with self._lock:
            participants = self._participants.get(event_id, [])
            return list(participants[-limit:])

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def create_template(
        self,
        name: str,
        template_type: EventTemplateType,
        event_type: EventType,
        description: str = "",
        default_duration_minutes: int = 60,
        default_scope: EventScope = EventScope.GLOBAL,
        default_min_level: int = 0,
        reward_blueprint: List[Dict[str, Any]] = None,
        tags: List[str] = None,
    ) -> EventTemplate:
        with self._lock:
            template = EventTemplate(
                template_id=_new_id("tpl"),
                name=name,
                template_type=template_type,
                event_type=event_type,
                description=description,
                default_duration_minutes=default_duration_minutes,
                default_scope=default_scope,
                default_min_level=default_min_level,
                reward_blueprint=reward_blueprint or [],
                tags=tags or [],
            )
            self._templates[template.template_id] = template
            _evict_fifo_dict(self._templates, _MAX_TEMPLATES)
            self._emit(LiveEventEventKind.TEMPLATE_CREATED, {
                "template_id": template.template_id,
                "name": name,
            })
            return template

    def get_template(self, template_id: str) -> Optional[EventTemplate]:
        with self._lock:
            return self._templates.get(template_id)

    def list_templates(
        self,
        template_type: EventTemplateType = None,
        event_type: EventType = None,
        limit: int = 100,
    ) -> List[EventTemplate]:
        with self._lock:
            items = list(self._templates.values())
            if template_type is not None:
                items = [t for t in items if t.template_type == template_type]
            if event_type is not None:
                items = [t for t in items if t.event_type == event_type]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Reward Catalog
    # ------------------------------------------------------------------

    def create_reward(
        self,
        name: str,
        reward_type: RewardType,
        description: str = "",
        amount: int = 0,
        rarity: str = "common",
        item_id: str = "",
        metadata: Dict[str, Any] = None,
    ) -> EventReward:
        with self._lock:
            reward = EventReward(
                reward_id=_new_id("rwd"),
                name=name,
                reward_type=reward_type,
                description=description,
                amount=amount,
                rarity=rarity,
                item_id=item_id,
                metadata=metadata or {},
            )
            self._rewards[reward.reward_id] = reward
            _evict_fifo_dict(self._rewards, _MAX_REWARDS)
            self._emit(LiveEventEventKind.REWARD_CREATED, {
                "reward_id": reward.reward_id,
                "name": name,
                "reward_type": reward_type.value,
            })
            return reward

    def list_rewards(
        self,
        reward_type: RewardType = None,
        limit: int = 100,
    ) -> List[EventReward]:
        with self._lock:
            items = list(self._rewards.values())
            if reward_type is not None:
                items = [r for r in items if r.reward_type == reward_type]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events_log(
        self,
        kind: LiveEventEventKind = None,
        limit: int = 100,
    ) -> List[LiveEventEvent]:
        with self._lock:
            items = list(self._event_log)
            if kind is not None:
                items = [e for e in items if e.kind == kind]
            return items[-limit:]

    def get_stats(self) -> LiveEventStats:
        with self._lock:
            active = sum(
                1 for e in self._events.values()
                if e.status in (EventStatus.ACTIVE, EventStatus.ENDING)
            )
            scheduled = sum(
                1 for e in self._events.values()
                if e.status in (EventStatus.SCHEDULED, EventStatus.ANNOUNCED)
            )
            completed = sum(
                1 for e in self._events.values()
                if e.status == EventStatus.COMPLETED
            )
            cancelled = sum(
                1 for e in self._events.values()
                if e.status == EventStatus.CANCELLED
            )
            total_participants = sum(
                len(p) for p in self._participants.values()
            )
            return LiveEventStats(
                total_events=len(self._events),
                active_events=active,
                scheduled_events=scheduled,
                completed_events=completed,
                cancelled_events=cancelled,
                total_participants=total_participants,
                total_rewards=len(self._rewards),
                total_templates=len(self._templates),
                total_schedules=len(self._schedules),
                total_event_log=len(self._event_log),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "events": len(self._events),
                "rewards": len(self._rewards),
                "schedules": len(self._schedules),
                "templates": len(self._templates),
                "participants": sum(len(p) for p in self._participants.values()),
                "metrics": len(self._metrics),
                "event_log": len(self._event_log),
            }

    def get_snapshot(self) -> LiveEventSnapshot:
        with self._lock:
            return LiveEventSnapshot(
                events=[e.to_dict() for e in list(self._events.values())[:20]],
                templates=[t.to_dict() for t in list(self._templates.values())[:20]],
                rewards=[r.to_dict() for r in list(self._rewards.values())[:20]],
                schedules=[s.to_dict() for s in list(self._schedules.values())[:20]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._rewards.clear()
            self._schedules.clear()
            self._templates.clear()
            self._participants.clear()
            self._metrics.clear()
            self._event_log.clear()
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        # Reward 1: Festival Crown cosmetic
        crown = EventReward(
            reward_id="rwd_seed_crown",
            name="Summer Festival Crown",
            reward_type=RewardType.COSMETIC,
            description="Exclusive crown cosmetic for festival participants",
            amount=1,
            rarity="legendary",
            metadata={"slot": "head", "tradeable": False},
        )
        self._rewards[crown.reward_id] = crown

        # Reward 2: Tournament Gold Pack currency
        gold = EventReward(
            reward_id="rwd_seed_gold",
            name="Tournament Gold Pack",
            reward_type=RewardType.CURRENCY,
            description="Gold currency awarded to top tournament finishers",
            amount=5000,
            rarity="rare",
            metadata={"currency": "gold"},
        )
        self._rewards[gold.reward_id] = gold

        # Event 1: Summer Festival (seasonal festival, scheduled)
        summer_schedule = EventSchedule(
            schedule_id="sch_seed_summer",
            start_time="2026-07-15T00:00:00Z",
            end_time="2026-08-15T00:00:00Z",
            timezone="UTC",
            recurrence="yearly",
            recurrence_interval_days=365,
            duration_minutes=44640,
        )
        self._schedules[summer_schedule.schedule_id] = summer_schedule

        summer = LiveEvent(
            event_id="evt_seed_summer",
            name="Summer Festival",
            event_type=EventType.SEASONAL_FESTIVAL,
            description="A month-long seasonal festival with daily quests, "
                        "exclusive cosmetics, and community challenges.",
            scope=EventScope.GLOBAL,
            status=EventStatus.SCHEDULED,
            schedule_id=summer_schedule.schedule_id,
            reward_ids=[crown.reward_id],
            theme="summer_beach",
            min_level=5,
            max_participants=0,
            tags=["seasonal", "summer", "cosmetics"],
            metadata={"version": 3, "region_lock": False},
        )
        self._events[summer.event_id] = summer
        self._participants[summer.event_id] = []
        self._metrics[summer.event_id] = EventMetrics(
            metrics_id=_new_id("mtx"),
            event_id=summer.event_id,
        )

        # Event 2: Weekly PvP Tournament (tournament, draft)
        pvp_schedule = EventSchedule(
            schedule_id="sch_seed_pvp",
            start_time="2026-07-06T18:00:00Z",
            end_time="2026-07-06T22:00:00Z",
            timezone="UTC",
            recurrence="weekly",
            recurrence_interval_days=7,
            duration_minutes=240,
        )
        self._schedules[pvp_schedule.schedule_id] = pvp_schedule

        pvp = LiveEvent(
            event_id="evt_seed_pvp",
            name="Weekly PvP Tournament",
            event_type=EventType.TOURNAMENT,
            description="Recurring weekly PvP bracket tournament with "
                        "leaderboard placement rewards.",
            scope=EventScope.SERVER,
            status=EventStatus.DRAFT,
            schedule_id=pvp_schedule.schedule_id,
            reward_ids=[gold.reward_id],
            theme="arena_combat",
            min_level=20,
            max_participants=256,
            tags=["pvp", "weekly", "competitive"],
            metadata={"bracket_size": 256, "format": "single_elim"},
        )
        self._events[pvp.event_id] = pvp
        self._participants[pvp.event_id] = []
        self._metrics[pvp.event_id] = EventMetrics(
            metrics_id=_new_id("mtx"),
            event_id=pvp.event_id,
        )

        # Template 1: Weekly Tournament Template
        template = EventTemplate(
            template_id="tpl_seed_weekly_tournament",
            name="Weekly Tournament Template",
            template_type=EventTemplateType.WEEKLY,
            event_type=EventType.TOURNAMENT,
            description="Reusable blueprint for recurring weekly competitive "
                        "tournaments across any scope.",
            default_duration_minutes=240,
            default_scope=EventScope.SERVER,
            default_min_level=15,
            reward_blueprint=[
                {"reward_type": "currency", "amount": 5000, "rarity": "rare"},
                {"reward_type": "badge", "amount": 1, "rarity": "epic"},
            ],
            tags=["pvp", "weekly", "tournament"],
        )
        self._templates[template.template_id] = template


def get_live_event_generator() -> LiveEventGenerator:
    """Factory function returning the singleton LiveEventGenerator instance."""
    return LiveEventGenerator.get_instance()
