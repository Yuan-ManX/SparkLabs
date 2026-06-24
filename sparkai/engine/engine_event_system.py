"""
SparkLabs Engine - Event System Engine

Game-wide event bus with priority-based dispatch, event filtering, async
handling, and event replay for debugging. Supports multiple channels for
organized event routing and batched dispatch for performance.

Architecture:
  EventSystemEngine (Singleton)
    |-- GameEvent        — typed event with priority, channel, and payload
    |-- EventListener    — registered handler with filter and priority
    |-- EventRecord      — historical record of dispatched events

Event Pipeline:
  1. Emit     — create and queue an event
  2. Match    — find listeners matching the event type and channel
  3. Filter   — apply listener filter conditions
  4. Dispatch  — invoke handlers in priority order
  5. Record   — store event in history for replay and debugging
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Set


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EventPriority(Enum):
    """Priority level for event dispatch order (highest first)."""
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4
    CRITICAL = 5


class EventChannel(Enum):
    """Channel for organizing events by domain."""
    GLOBAL = "global"
    GAMEPLAY = "gameplay"
    UI = "ui"
    AUDIO = "audio"
    PHYSICS = "physics"
    INPUT = "input"
    NETWORK = "network"
    AI = "ai"


class DispatchMode(Enum):
    """Mode determining when events are dispatched to listeners."""
    IMMEDIATE = "immediate"
    QUEUED = "queued"
    DEFERRED = "deferred"
    BATCHED = "batched"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class GameEvent:
    """A typed event carrying data through the event system."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: str = ""
    channel: EventChannel = EventChannel.GLOBAL
    priority: EventPriority = EventPriority.NORMAL
    source_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    ttl: float = 0.0  # 0 means no expiration
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the event has exceeded its time-to-live."""
        if self.ttl <= 0.0:
            return False
        return (time.time() - self.timestamp) > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "channel": self.channel.value,
            "priority": self.priority.name,
            "source_id": self.source_id,
            "data": dict(self.data),
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "metadata": dict(self.metadata),
        }


@dataclass
class EventListener:
    """A registered handler for game events with filtering and priority."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    listener_id: str = ""
    event_types: List[str] = field(default_factory=list)
    channels: List[EventChannel] = field(default_factory=list)
    handler_ref: Callable[[GameEvent], Any] = field(default_factory=lambda: lambda _: None)
    priority: EventPriority = EventPriority.NORMAL
    filter_condition: Optional[Callable[[GameEvent], bool]] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches(self, event: GameEvent) -> bool:
        """Check if this listener can handle the given event."""
        if not self.is_active:
            return False
        if self.event_types and event.event_type not in self.event_types:
            return False
        if self.channels and event.channel not in self.channels:
            return False
        if self.filter_condition is not None:
            try:
                if not self.filter_condition(event):
                    return False
            except Exception:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "listener_id": self.listener_id,
            "event_types": list(self.event_types),
            "channels": [c.value for c in self.channels],
            "priority": self.priority.name,
            "has_filter": self.filter_condition is not None,
            "is_active": self.is_active,
            "metadata": dict(self.metadata),
        }


@dataclass
class EventRecord:
    """Historical record of a dispatched event with response data."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event: GameEvent = field(default_factory=GameEvent)
    dispatch_time: float = 0.0
    listeners_notified: int = 0
    responses: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event": self.event.to_dict(),
            "dispatch_time": round(self.dispatch_time, 4),
            "listeners_notified": self.listeners_notified,
            "response_count": len(self.responses),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Event System Engine
# ---------------------------------------------------------------------------

class EventSystemEngine:
    """
    Game-wide event bus with priority-based dispatch and event replay.

    Manages event emission, listener subscription, filtered dispatch,
    and event history recording. Supports immediate, queued, deferred,
    and batched dispatch modes for performance tuning.
    """

    _instance: Optional["EventSystemEngine"] = None
    _lock = threading.RLock()

    _MAX_HISTORY_SIZE: int = 1000
    _MAX_QUEUE_SIZE: int = 500
    _DEFAULT_TTL: float = 0.0

    def __new__(cls) -> "EventSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EventSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._listeners: Dict[str, EventListener] = {}
        self._event_queue: deque = deque()
        self._deferred_queue: List[Tuple[GameEvent, float]] = []
        self._batch_queue: List[GameEvent] = []
        self._history: List[EventRecord] = []
        self._emit_count: int = 0
        self._dispatch_count: int = 0
        self._replay_count: int = 0
        self._creation_time: float = time.time()
        self._dispatch_mode: DispatchMode = DispatchMode.IMMEDIATE

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------

    def emit(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        channel: EventChannel = EventChannel.GLOBAL,
        priority: EventPriority = EventPriority.NORMAL,
        source_id: str = "",
        ttl: float = _DEFAULT_TTL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GameEvent:
        """Create and emit a game event.

        Depending on the dispatch mode, the event is either dispatched
        immediately, queued for later dispatch, or deferred.

        Args:
            event_type: The type/category of the event (e.g., "player_damaged").
            data: Payload data for the event.
            channel: The domain channel for routing.
            priority: Dispatch priority level.
            source_id: Identifier of the entity that emitted the event.
            ttl: Time-to-live in seconds (0 = no expiration).
            metadata: Optional arbitrary metadata.

        Returns:
            The created GameEvent.
        """
        with self._lock:
            event = GameEvent(
                event_type=event_type,
                channel=channel,
                priority=priority,
                source_id=source_id,
                data=data or {},
                ttl=ttl,
                metadata=metadata or {},
            )
            self._emit_count += 1

            if self._dispatch_mode == DispatchMode.IMMEDIATE:
                self._dispatch_event(event)
            elif self._dispatch_mode == DispatchMode.QUEUED:
                if len(self._event_queue) >= self._MAX_QUEUE_SIZE:
                    self._event_queue.popleft()
                self._event_queue.append(event)
            elif self._dispatch_mode == DispatchMode.DEFERRED:
                self._deferred_queue.append((event, time.time()))
            elif self._dispatch_mode == DispatchMode.BATCHED:
                self._batch_queue.append(event)

            return event

    def _dispatch_event(self, event: GameEvent) -> EventRecord:
        """Dispatch a single event to all matching listeners.

        Listeners are sorted by priority (highest first) before dispatch.
        """
        if event.is_expired():
            return EventRecord(
                event=event,
                dispatch_time=0.0,
                listeners_notified=0,
                responses=[],
            )

        start_time = time.time()
        responses: List[Any] = []
        notified = 0

        # Collect matching listeners sorted by priority
        matching: List[EventListener] = [
            listener for listener in self._listeners.values()
            if listener.matches(event)
        ]
        matching.sort(key=lambda l: l.priority.value, reverse=True)

        for listener in matching:
            try:
                response = listener.handler_ref(event)
                responses.append(response)
                notified += 1
            except Exception:
                pass

        dispatch_time = time.time() - start_time
        self._dispatch_count += 1

        record = EventRecord(
            event=event,
            dispatch_time=dispatch_time,
            listeners_notified=notified,
            responses=responses,
        )

        # Record in history
        self._history.append(record)
        while len(self._history) > self._MAX_HISTORY_SIZE:
            self._history.pop(0)

        return record

    # ------------------------------------------------------------------
    # Subscribe / Unsubscribe
    # ------------------------------------------------------------------

    def subscribe(
        self,
        listener_id: str,
        handler: Callable[[GameEvent], Any],
        event_types: Optional[List[str]] = None,
        channels: Optional[List[EventChannel]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        filter_condition: Optional[Callable[[GameEvent], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EventListener:
        """Register a listener to receive events.

        If a listener with the same listener_id already exists, it is
        updated with the new configuration.

        Args:
            listener_id: A unique identifier for the listener.
            handler: Callback function invoked when the event matches.
            event_types: List of event types to listen for (empty = all types).
            channels: List of channels to listen on (empty = all channels).
            priority: Dispatch priority for this listener.
            filter_condition: Optional function to filter specific events.
            metadata: Optional arbitrary metadata.

        Returns:
            The registered or updated EventListener.
        """
        with self._lock:
            # Check if listener_id already registered
            existing = None
            for lid, listener in self._listeners.items():
                if listener.listener_id == listener_id:
                    existing = listener
                    break

            if existing is not None:
                # Update existing listener
                existing.event_types = list(event_types or [])
                existing.channels = list(channels or [])
                existing.handler_ref = handler
                existing.priority = priority
                existing.filter_condition = filter_condition
                existing.is_active = True
                existing.metadata = metadata or {}
                return existing

            listener = EventListener(
                listener_id=listener_id,
                event_types=list(event_types or []),
                channels=list(channels or []),
                handler_ref=handler,
                priority=priority,
                filter_condition=filter_condition,
                is_active=True,
                metadata=metadata or {},
            )
            self._listeners[listener.id] = listener
            return listener

    def unsubscribe(self, listener_id: str) -> bool:
        """Remove a listener by its listener_id.

        Returns:
            True if a listener was found and removed, False otherwise.
        """
        with self._lock:
            for lid, listener in list(self._listeners.items()):
                if listener.listener_id == listener_id:
                    del self._listeners[lid]
                    return True
            return False

    def set_listener_active(self, listener_id: str, active: bool) -> bool:
        """Enable or disable a listener without removing it."""
        with self._lock:
            for listener in self._listeners.values():
                if listener.listener_id == listener_id:
                    listener.is_active = active
                    return True
            return False

    def get_listeners(
        self,
        event_type: Optional[str] = None,
        channel: Optional[EventChannel] = None,
    ) -> List[EventListener]:
        """Get all listeners, optionally filtered by event type or channel."""
        with self._lock:
            result = list(self._listeners.values())
            if event_type is not None:
                result = [
                    l for l in result
                    if not l.event_types or event_type in l.event_types
                ]
            if channel is not None:
                result = [
                    l for l in result
                    if not l.channels or channel in l.channels
                ]
            return result

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, event: GameEvent) -> EventRecord:
        """Manually dispatch a specific event."""
        with self._lock:
            return self._dispatch_event(event)

    def dispatch_all(self) -> int:
        """Dispatch all queued events.

        Used when the dispatch mode is QUEUED, DEFERRED, or BATCHED.

        Returns:
            The number of events dispatched.
        """
        with self._lock:
            dispatched = 0

            # Process queued events
            while self._event_queue:
                event = self._event_queue.popleft()
                self._dispatch_event(event)
                dispatched += 1

            # Process deferred events
            now = time.time()
            ready: List[GameEvent] = []
            remaining: List[Tuple[GameEvent, float]] = []
            for event, deferred_time in self._deferred_queue:
                if now - deferred_time >= 0.0:  # Dispatch immediately
                    ready.append(event)
                else:
                    remaining.append((event, deferred_time))
            self._deferred_queue = remaining

            for event in ready:
                self._dispatch_event(event)
                dispatched += 1

            # Process batched events
            if self._batch_queue:
                for event in self._batch_queue:
                    self._dispatch_event(event)
                    dispatched += 1
                self._batch_queue.clear()

            return dispatched

    def set_dispatch_mode(self, mode: DispatchMode) -> None:
        """Set the dispatch mode for future events.

        Changing from QUEUED/DEFERRED/BATCHED to IMMEDIATE will flush
        all pending events.
        """
        with self._lock:
            old_mode = self._dispatch_mode
            self._dispatch_mode = mode
            if old_mode != DispatchMode.IMMEDIATE and mode == DispatchMode.IMMEDIATE:
                self.dispatch_all()

    # ------------------------------------------------------------------
    # Event History
    # ------------------------------------------------------------------

    def get_event_history(
        self,
        event_type: Optional[str] = None,
        channel: Optional[EventChannel] = None,
        limit: int = 100,
    ) -> List[EventRecord]:
        """Get recent event records, optionally filtered.

        Args:
            event_type: Filter by event type.
            channel: Filter by channel.
            limit: Maximum number of records to return.

        Returns:
            List of matching EventRecords, most recent first.
        """
        with self._lock:
            result = list(self._history)
            if event_type is not None:
                result = [r for r in result if r.event.event_type == event_type]
            if channel is not None:
                result = [r for r in result if r.event.channel == channel]
            result.reverse()  # Most recent first
            return result[:limit]

    def replay_events(
        self,
        event_type: Optional[str] = None,
        channel: Optional[EventChannel] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> int:
        """Replay historical events to current listeners.

        This is useful for debugging: replaying events can reproduce
        a game state from a recorded sequence.

        Args:
            event_type: Filter by event type.
            channel: Filter by channel.
            start_time: Only replay events after this timestamp.
            end_time: Only replay events before this timestamp.

        Returns:
            The number of events replayed.
        """
        with self._lock:
            replayed = 0
            for record in self._history:
                event = record.event
                if event_type is not None and event.event_type != event_type:
                    continue
                if channel is not None and event.channel != channel:
                    continue
                if start_time is not None and event.timestamp < start_time:
                    continue
                if end_time is not None and event.timestamp > end_time:
                    continue

                self._dispatch_event(event)
                replayed += 1
                self._replay_count += 1

            return replayed

    def clear_history(self) -> int:
        """Clear all event history records.

        Returns:
            The number of records cleared.
        """
        with self._lock:
            count = len(self._history)
            self._history.clear()
            return count

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics including listener counts and dispatch metrics."""
        with self._lock:
            active_listeners = sum(1 for l in self._listeners.values() if l.is_active)
            inactive_listeners = len(self._listeners) - active_listeners

            listeners_by_priority: Dict[str, int] = {}
            for listener in self._listeners.values():
                pname = listener.priority.name
                listeners_by_priority[pname] = listeners_by_priority.get(pname, 0) + 1

            events_by_channel: Dict[str, int] = {}
            for record in self._history:
                cname = record.event.channel.value
                events_by_channel[cname] = events_by_channel.get(cname, 0) + 1

            events_by_type: Dict[str, int] = {}
            for record in self._history:
                etype = record.event.event_type
                events_by_type[etype] = events_by_type.get(etype, 0) + 1

            return {
                "total_listeners": len(self._listeners),
                "active_listeners": active_listeners,
                "inactive_listeners": inactive_listeners,
                "listeners_by_priority": listeners_by_priority,
                "emit_count": self._emit_count,
                "dispatch_count": self._dispatch_count,
                "replay_count": self._replay_count,
                "history_size": len(self._history),
                "queue_size": len(self._event_queue),
                "deferred_count": len(self._deferred_queue),
                "batch_count": len(self._batch_queue),
                "dispatch_mode": self._dispatch_mode.value,
                "events_by_channel": events_by_channel,
                "events_by_type": events_by_type,
                "uptime_seconds": round(time.time() - self._creation_time, 1),
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire event system engine state."""
        with self._lock:
            self._listeners.clear()
            self._event_queue.clear()
            self._deferred_queue.clear()
            self._batch_queue.clear()
            self._history.clear()
            self._emit_count = 0
            self._dispatch_count = 0
            self._replay_count = 0
            self._dispatch_mode = DispatchMode.IMMEDIATE
            self._creation_time = time.time()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_event_system() -> EventSystemEngine:
    """Get or create the singleton EventSystemEngine instance."""
    return EventSystemEngine.get_instance()