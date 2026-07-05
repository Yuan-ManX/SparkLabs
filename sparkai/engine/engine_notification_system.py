"""
SparkLabs Engine - Notification System

A queue-managed toast and alert system for the SparkLabs AI-native
game engine. It manages notification queueing, priority, stacking,
fade animations, and dismissal rules. The system handles achievement
popups, quest updates, item pickups, system messages, and any
transient player-facing communication with consistent visual
treatment and accessibility support.

Architecture:
  NotificationSystem (singleton)
    |-- Notification, NotificationTemplate, NotificationQueue,
       NotificationStats, NotificationSnapshot, NotificationEvent
    |-- NotificationUrgency, NotificationKind, NotificationStatus,
       NotificationEventKind

Core Capabilities:
  - register_template / get_template / list_templates / remove_template:
    notification template lifecycle with kind, urgency, and styling.
  - create_notification / get_notification / list_notifications /
    remove_notification: notification lifecycle with urgency-based
    queueing.
  - enqueue / dequeue: priority-ordered queue management with
    stacking rules.
  - dismiss / expire: notification lifecycle transitions.
  - set_priority: dynamic priority adjustment.
  - list_active / list_queued / list_history: filtered views into
    the notification store.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`NotificationSystem.get_instance` or the module-level
:func:`get_notification_system` factory.
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

_MAX_TEMPLATES: int = 500
_MAX_NOTIFICATIONS: int = 10000
_MAX_QUEUE: int = 200
_MAX_HISTORY: int = 5000
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


class NotificationUrgency(Enum):
    """Urgency tier that controls queue ordering and display prominence."""
    TRIVIAL = "trivial"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationKind(Enum):
    """Functional classification of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ACHIEVEMENT = "achievement"
    QUEST = "quest"
    ITEM = "item"
    SYSTEM = "system"
    SOCIAL = "social"
    COMBAT = "combat"


class NotificationStatus(Enum):
    """Lifecycle state of a notification."""
    QUEUED = "queued"
    ACTIVE = "active"
    DISPLAYED = "displayed"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class NotificationEventKind(Enum):
    """Audit event types emitted by the notification system."""
    TEMPLATE_REGISTERED = "template_registered"
    TEMPLATE_REMOVED = "template_removed"
    NOTIFICATION_CREATED = "notification_created"
    NOTIFICATION_ENQUEUED = "notification_enqueued"
    NOTIFICATION_DEQUEUED = "notification_dequeued"
    NOTIFICATION_DISMISSED = "notification_dismissed"
    NOTIFICATION_EXPIRED = "notification_expired"
    PRIORITY_CHANGED = "priority_changed"
    NOTIFICATION_REMOVED = "notification_removed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class NotificationTemplate:
    """A reusable template for generating notifications."""
    template_id: str = field(default_factory=lambda: _new_id("tpl"))
    name: str = ""
    description: str = ""
    kind: str = NotificationKind.INFO.value
    default_urgency: str = NotificationUrgency.NORMAL.value
    title_template: str = ""
    body_template: str = ""
    icon: str = ""
    color: str = "#FFFFFF"
    sound: str = ""
    duration_ms: int = 5000
    dismissible: bool = True
    stack_key: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Notification:
    """A discrete notification instance."""
    notification_id: str = field(default_factory=lambda: _new_id("ntf"))
    template_id: str = ""
    kind: str = NotificationKind.INFO.value
    urgency: str = NotificationUrgency.NORMAL.value
    status: str = NotificationStatus.QUEUED.value
    title: str = ""
    body: str = ""
    icon: str = ""
    color: str = "#FFFFFF"
    sound: str = ""
    duration_ms: int = 5000
    dismissible: bool = True
    stack_key: str = ""
    target_player_id: str = ""
    display_at_ms: int = 0
    expires_at_ms: int = 0
    enqueued_at: str = field(default_factory=_now)
    displayed_at: str = ""
    dismissed_at: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NotificationQueue:
    """Priority-ordered queue of active notifications per player."""
    player_id: str = ""
    entries: List[Dict[str, Any]] = field(default_factory=list)
    max_active: int = 5
    stack_duplicates: bool = True
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NotificationStats:
    """Aggregate counters for the notification system."""
    total_templates: int = 0
    total_notifications: int = 0
    total_enqueued: int = 0
    total_displayed: int = 0
    total_dismissed: int = 0
    total_expired: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NotificationSnapshot:
    """Immutable point-in-time capture of notification state."""
    templates: Dict[str, Any] = field(default_factory=dict)
    notifications: Dict[str, Any] = field(default_factory=dict)
    queues: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NotificationEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("aud"))
    kind: str = NotificationEventKind.NOTIFICATION_CREATED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Static Lookup Tables
# ---------------------------------------------------------------------------

_URGENCY_RANK: Dict[str, int] = {
    NotificationUrgency.TRIVIAL.value: 0,
    NotificationUrgency.LOW.value: 1,
    NotificationUrgency.NORMAL.value: 2,
    NotificationUrgency.HIGH.value: 3,
    NotificationUrgency.CRITICAL.value: 4,
}

_KIND_DEFAULT_COLOR: Dict[str, str] = {
    NotificationKind.INFO.value: "#4A90E2",
    NotificationKind.SUCCESS.value: "#27AE60",
    NotificationKind.WARNING.value: "#F39C12",
    NotificationKind.ERROR.value: "#E74C3C",
    NotificationKind.ACHIEVEMENT.value: "#F1C40F",
    NotificationKind.QUEST.value: "#9B59B6",
    NotificationKind.ITEM.value: "#16A085",
    NotificationKind.SYSTEM.value: "#34495E",
    NotificationKind.SOCIAL.value: "#E91E63",
    NotificationKind.COMBAT.value: "#C0392B",
}


# ---------------------------------------------------------------------------
# Notification System Singleton
# ---------------------------------------------------------------------------


class NotificationSystem:
    """Singleton engine system that manages toast and alert notifications.

    The system maintains notification templates, active notifications,
    and per-player priority queues. It supports enqueue/dequeue
    operations, lifecycle transitions (dismiss/expire), and filtered
    views into the notification store.
    """

    _instance: Optional["NotificationSystem"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._templates: Dict[str, NotificationTemplate] = {}
        self._notifications: Dict[str, Notification] = {}
        self._queues: Dict[str, NotificationQueue] = {}
        self._history: List[Dict[str, Any]] = []
        self._total_enqueued: int = 0
        self._total_displayed: int = 0
        self._total_dismissed: int = 0
        self._total_expired: int = 0
        self._audit: List[NotificationEvent] = []

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "NotificationSystem":
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
        """Seed a small set of default templates."""
        defaults = [
            ("tpl_achievement_unlocked", "Achievement Unlocked",
             "Toast shown when an achievement is unlocked.",
             NotificationKind.ACHIEVEMENT, NotificationUrgency.HIGH,
             "Achievement Unlocked!", "{achievement_name} ({tier})",
             "trophy", "#F1C40F", "achievement_chime", 6000, True, "achievement"),
            ("tpl_quest_updated", "Quest Updated",
             "Toast shown when a quest stage advances.",
             NotificationKind.QUEST, NotificationUrgency.NORMAL,
             "Quest Update", "{quest_name}: {stage_description}",
             "scroll", "#9B59B6", "quest_chime", 5000, True, "quest"),
            ("tpl_item_pickup", "Item Pickup",
             "Toast shown when the player picks up an item.",
             NotificationKind.ITEM, NotificationUrgency.LOW,
             "Item Acquired", "{item_name} x{quantity}",
             "backpack", "#16A085", "item_pickup", 3500, True, "item"),
            ("tpl_system_message", "System Message",
             "Toast shown for system-level messages.",
             NotificationKind.SYSTEM, NotificationUrgency.NORMAL,
             "System", "{message}",
             "gear", "#34495E", "", 4000, True, "system"),
            ("tpl_combat_alert", "Combat Alert",
             "Toast shown for critical combat events.",
             NotificationKind.COMBAT, NotificationUrgency.CRITICAL,
             "Combat Alert", "{alert_text}",
             "sword", "#C0392B", "combat_alert", 4500, True, "combat"),
        ]
        for tid, name, desc, kind, urgency, title, body, icon, color, sound, duration, dismissible, stack_key in defaults:
            template = NotificationTemplate(
                template_id=tid,
                name=name,
                description=desc,
                kind=kind.value,
                default_urgency=urgency.value,
                title_template=title,
                body_template=body,
                icon=icon,
                color=color,
                sound=sound,
                duration_ms=duration,
                dismissible=dismissible,
                stack_key=stack_key,
            )
            self._templates[tid] = template
            self._record_event(NotificationEventKind.TEMPLATE_REGISTERED, {
                "template_id": tid, "name": name,
            })

    # ------------------------------------------------------------------
    # Audit Helpers
    # ------------------------------------------------------------------

    def _record_event(self, kind: NotificationEventKind, payload: Dict[str, Any]) -> None:
        event = NotificationEvent(kind=kind.value, payload=payload)
        self._audit.append(event)
        _evict_fifo_list(self._audit, _MAX_EVENTS)

    def _ensure_queue(self, player_id: str) -> NotificationQueue:
        if player_id not in self._queues:
            self._queues[player_id] = NotificationQueue(player_id=player_id)
        return self._queues[player_id]

    def _sort_queue(self, queue: NotificationQueue) -> None:
        # Sort by urgency rank descending, then by enqueued_at ascending (FIFO within same urgency)
        queue.entries.sort(
            key=lambda e: (-_URGENCY_RANK.get(e.get("urgency", ""), 0), e.get("enqueued_at", "")),
        )
        queue.updated_at = _now()

    def _render_template(self, template: NotificationTemplate, params: Dict[str, Any]) -> Dict[str, str]:
        title = template.title_template
        body = template.body_template
        for key, value in params.items():
            placeholder = "{" + key + "}"
            title = title.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        return {"title": title, "body": body}

    # ------------------------------------------------------------------
    # Template Lifecycle
    # ------------------------------------------------------------------

    def register_template(
        self,
        template_id: str = "",
        name: str = "",
        description: str = "",
        kind: str = NotificationKind.INFO.value,
        default_urgency: str = NotificationUrgency.NORMAL.value,
        title_template: str = "",
        body_template: str = "",
        icon: str = "",
        color: str = "",
        sound: str = "",
        duration_ms: int = 5000,
        dismissible: bool = True,
        stack_key: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationTemplate:
        with self._lock:
            tid = template_id or _new_id("tpl")
            template = NotificationTemplate(
                template_id=tid,
                name=name,
                description=description,
                kind=kind,
                default_urgency=default_urgency,
                title_template=title_template,
                body_template=body_template,
                icon=icon,
                color=color or _KIND_DEFAULT_COLOR.get(kind, "#FFFFFF"),
                sound=sound,
                duration_ms=_safe_int(duration_ms, 5000),
                dismissible=dismissible,
                stack_key=stack_key,
                metadata=dict(metadata or {}),
            )
            self._templates[tid] = template
            _evict_fifo_dict(self._templates, _MAX_TEMPLATES)
            self._record_event(NotificationEventKind.TEMPLATE_REGISTERED, {
                "template_id": tid, "name": name,
            })
            return template

    def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        with self._lock:
            return self._templates.get(template_id)

    def list_templates(
        self,
        kind: str = "",
        limit: int = 100,
    ) -> List[NotificationTemplate]:
        with self._lock:
            results: List[NotificationTemplate] = []
            for template in self._templates.values():
                if kind and template.kind != kind:
                    continue
                results.append(template)
            return results[:max(0, int(limit))]

    def remove_template(self, template_id: str) -> bool:
        with self._lock:
            existed = self._templates.pop(template_id, None) is not None
            if existed:
                self._record_event(NotificationEventKind.TEMPLATE_REMOVED, {"template_id": template_id})
            return existed

    # ------------------------------------------------------------------
    # Notification Lifecycle
    # ------------------------------------------------------------------

    def create_notification(
        self,
        template_id: str = "",
        kind: str = "",
        urgency: str = "",
        title: str = "",
        body: str = "",
        icon: str = "",
        color: str = "",
        sound: str = "",
        duration_ms: int = 0,
        dismissible: bool = True,
        stack_key: str = "",
        target_player_id: str = "",
        display_at_ms: int = 0,
        expires_at_ms: int = 0,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        notification_id: str = "",
    ) -> Notification:
        with self._lock:
            template = self._templates.get(template_id) if template_id else None
            params = params or {}
            effective_kind = kind or (template.kind if template else NotificationKind.INFO.value)
            effective_urgency = urgency or (template.default_urgency if template else NotificationUrgency.NORMAL.value)
            if template and (title == "" or body == ""):
                rendered = self._render_template(template, params)
                if title == "":
                    title = rendered["title"]
                if body == "":
                    body = rendered["body"]
            effective_icon = icon or (template.icon if template else "")
            effective_color = color or (template.color if template else _KIND_DEFAULT_COLOR.get(effective_kind, "#FFFFFF"))
            effective_sound = sound or (template.sound if template else "")
            effective_duration = duration_ms or (template.duration_ms if template else 5000)
            effective_dismissible = dismissible if dismissible is not None else (template.dismissible if template else True)
            effective_stack_key = stack_key or (template.stack_key if template else "")
            nid = notification_id or _new_id("ntf")
            notification = Notification(
                notification_id=nid,
                template_id=template_id,
                kind=effective_kind,
                urgency=effective_urgency,
                status=NotificationStatus.QUEUED.value,
                title=title,
                body=body,
                icon=effective_icon,
                color=effective_color,
                sound=effective_sound,
                duration_ms=effective_duration,
                dismissible=effective_dismissible,
                stack_key=effective_stack_key,
                target_player_id=target_player_id,
                display_at_ms=display_at_ms,
                expires_at_ms=expires_at_ms,
                payload=dict(payload or {}),
                metadata=dict(metadata or {}),
            )
            self._notifications[nid] = notification
            _evict_fifo_dict(self._notifications, _MAX_NOTIFICATIONS)
            self._record_event(NotificationEventKind.NOTIFICATION_CREATED, {
                "notification_id": nid, "kind": effective_kind,
            })
            return notification

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        with self._lock:
            return self._notifications.get(notification_id)

    def list_notifications(
        self,
        kind: str = "",
        urgency: str = "",
        status: str = "",
        target_player_id: str = "",
        limit: int = 100,
    ) -> List[Notification]:
        with self._lock:
            results: List[Notification] = []
            for notification in self._notifications.values():
                if kind and notification.kind != kind:
                    continue
                if urgency and notification.urgency != urgency:
                    continue
                if status and notification.status != status:
                    continue
                if target_player_id and notification.target_player_id != target_player_id:
                    continue
                results.append(notification)
            return results[:max(0, int(limit))]

    def remove_notification(self, notification_id: str) -> bool:
        with self._lock:
            existed = self._notifications.pop(notification_id, None) is not None
            if existed:
                # Also remove from any queue
                for queue in self._queues.values():
                    queue.entries = [e for e in queue.entries if e.get("notification_id") != notification_id]
                    queue.updated_at = _now()
                self._record_event(NotificationEventKind.NOTIFICATION_REMOVED, {
                    "notification_id": notification_id,
                })
            return existed

    # ------------------------------------------------------------------
    # Queue Management
    # ------------------------------------------------------------------

    def enqueue(self, notification_id: str) -> Optional[Notification]:
        with self._lock:
            notification = self._notifications.get(notification_id)
            if notification is None:
                return None
            target_player = notification.target_player_id or "_global"
            queue = self._ensure_queue(target_player)
            # Stacking: if a notification with the same stack_key exists, replace it
            if notification.stack_key:
                queue.entries = [
                    e for e in queue.entries
                    if e.get("stack_key") != notification.stack_key
                ]
            entry = {
                "notification_id": notification.notification_id,
                "kind": notification.kind,
                "urgency": notification.urgency,
                "title": notification.title,
                "body": notification.body,
                "icon": notification.icon,
                "color": notification.color,
                "stack_key": notification.stack_key,
                "enqueued_at": notification.enqueued_at,
                "display_at_ms": notification.display_at_ms,
                "expires_at_ms": notification.expires_at_ms,
            }
            queue.entries.append(entry)
            self._sort_queue(queue)
            # Cap the queue
            _evict_fifo_list(queue.entries, _MAX_QUEUE)
            notification.status = NotificationStatus.QUEUED.value
            self._total_enqueued += 1
            self._record_event(NotificationEventKind.NOTIFICATION_ENQUEUED, {
                "notification_id": notification_id,
                "player_id": target_player,
            })
            return notification

    def dequeue(self, player_id: str = "") -> Optional[Notification]:
        """Pop the highest-urgency notification from the queue."""
        with self._lock:
            target_player = player_id or "_global"
            queue = self._queues.get(target_player)
            if queue is None or not queue.entries:
                return None
            entry = queue.entries.pop(0)
            queue.updated_at = _now()
            notification = self._notifications.get(entry.get("notification_id", ""))
            if notification is None:
                return None
            notification.status = NotificationStatus.ACTIVE.value
            self._total_displayed += 1
            self._record_event(NotificationEventKind.NOTIFICATION_DEQUEUED, {
                "notification_id": notification.notification_id,
                "player_id": target_player,
            })
            return notification

    def dismiss(self, notification_id: str) -> Optional[Notification]:
        with self._lock:
            notification = self._notifications.get(notification_id)
            if notification is None:
                return None
            notification.status = NotificationStatus.DISMISSED.value
            notification.dismissed_at = _now()
            self._total_dismissed += 1
            # Add to history
            self._history.append(notification.to_dict())
            _evict_fifo_list(self._history, _MAX_HISTORY)
            self._record_event(NotificationEventKind.NOTIFICATION_DISMISSED, {
                "notification_id": notification_id,
            })
            return notification

    def expire(self, notification_id: str) -> Optional[Notification]:
        with self._lock:
            notification = self._notifications.get(notification_id)
            if notification is None:
                return None
            notification.status = NotificationStatus.EXPIRED.value
            self._total_expired += 1
            # Add to history
            self._history.append(notification.to_dict())
            _evict_fifo_list(self._history, _MAX_HISTORY)
            self._record_event(NotificationEventKind.NOTIFICATION_EXPIRED, {
                "notification_id": notification_id,
            })
            return notification

    def set_priority(self, notification_id: str, urgency: str) -> Optional[Notification]:
        with self._lock:
            notification = self._notifications.get(notification_id)
            if notification is None:
                return None
            old_urgency = notification.urgency
            notification.urgency = urgency
            # Re-sort the queue if the notification is enqueued
            target_player = notification.target_player_id or "_global"
            queue = self._queues.get(target_player)
            if queue is not None:
                for entry in queue.entries:
                    if entry.get("notification_id") == notification_id:
                        entry["urgency"] = urgency
                self._sort_queue(queue)
            self._record_event(NotificationEventKind.PRIORITY_CHANGED, {
                "notification_id": notification_id,
                "old_urgency": old_urgency,
                "new_urgency": urgency,
            })
            return notification

    # ------------------------------------------------------------------
    # Filtered Views
    # ------------------------------------------------------------------

    def list_active(self, player_id: str = "", limit: int = 100) -> List[Notification]:
        with self._lock:
            target_player = player_id or "_global"
            queue = self._queues.get(target_player)
            if queue is None:
                return []
            results: List[Notification] = []
            for entry in queue.entries:
                notification = self._notifications.get(entry.get("notification_id", ""))
                if notification is not None:
                    results.append(notification)
            return results[:max(0, int(limit))]

    def list_queued(self, player_id: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            target_player = player_id or "_global"
            queue = self._queues.get(target_player)
            if queue is None:
                return []
            return list(queue.entries[:max(0, int(limit))])

    def list_history(
        self,
        player_id: str = "",
        kind: str = "",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            results: List[Dict[str, Any]] = []
            for entry in self._history:
                if player_id and entry.get("target_player_id") != player_id:
                    continue
                if kind and entry.get("kind") != kind:
                    continue
                results.append(entry)
            return results[:max(0, int(limit))]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[NotificationEvent]:
        with self._lock:
            return list(self._audit[:max(0, int(limit))])

    def get_stats(self) -> NotificationStats:
        with self._lock:
            return NotificationStats(
                total_templates=len(self._templates),
                total_notifications=len(self._notifications),
                total_enqueued=self._total_enqueued,
                total_displayed=self._total_displayed,
                total_dismissed=self._total_dismissed,
                total_expired=self._total_expired,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "templates": len(self._templates),
                "notifications": len(self._notifications),
                "queues": len(self._queues),
                "history_entries": len(self._history),
                "total_enqueued": self._total_enqueued,
                "total_displayed": self._total_displayed,
                "total_dismissed": self._total_dismissed,
                "total_expired": self._total_expired,
                "events": len(self._audit),
            }

    def get_snapshot(self) -> NotificationSnapshot:
        with self._lock:
            return NotificationSnapshot(
                templates={tid: t.to_dict() for tid, t in self._templates.items()},
                notifications={nid: n.to_dict() for nid, n in self._notifications.items()},
                queues={pid: q.to_dict() for pid, q in self._queues.items()},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._templates.clear()
            self._notifications.clear()
            self._queues.clear()
            self._history.clear()
            self._total_enqueued = 0
            self._total_displayed = 0
            self._total_dismissed = 0
            self._total_expired = 0
            self._audit.clear()
            self._seed_defaults()
            self._initialized = True


# ---------------------------------------------------------------------------
# Module Factory
# ---------------------------------------------------------------------------


def get_notification_system() -> NotificationSystem:
    return NotificationSystem.get_instance()
