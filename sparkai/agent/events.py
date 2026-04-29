"""
SparkAI Agent - Event Bus

Centralized pub/sub communication system for the SparkLabs engine.
All modules communicate through the event bus, enabling loose coupling
and reactive architecture.

Event flow:
  Publisher -> EventBus -> Subscribers (priority-ordered)

Built-in event channels cover the full game engine lifecycle:
  - Engine lifecycle (start, stop, tick)
  - Entity operations (create, update, destroy)
  - Component mutations (add, remove, change)
  - Agent actions (think, act, verify)
  - Pipeline progression (stage_start, stage_complete)
  - Asset lifecycle (generate, import, export)
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class EventChannel(Enum):
    ENGINE = "engine"
    ENTITY = "entity"
    COMPONENT = "component"
    SYSTEM = "system"
    AGENT = "agent"
    PIPELINE = "pipeline"
    ASSET = "asset"
    NARRATIVE = "narrative"
    NPC = "npc"
    WORKFLOW = "workflow"
    SESSION = "session"
    MEMORY = "memory"
    COMMAND = "command"
    RUNTIME = "runtime"
    UI = "ui"


@dataclass
class Event:
    """
    A single event in the SparkLabs event system.
    Events carry typed data through the bus with full traceability.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel: EventChannel = EventChannel.RUNTIME
    topic: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = ""
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "channel": self.channel.value,
            "topic": self.topic,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "priority": self.priority,
        }


@dataclass
class Subscription:
    """
    A subscription to events on a specific channel and topic pattern.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel: Optional[EventChannel] = None
    topic_pattern: str = ""
    handler: Optional[Callable] = None
    priority: int = 0
    active: bool = True
    call_count: int = 0
    last_called: Optional[float] = None

    def matches(self, event: Event) -> bool:
        if not self.active:
            return False
        if self.channel and self.channel != event.channel:
            return False
        if self.topic_pattern:
            if self.topic_pattern == "*":
                return True
            if self.topic_pattern.endswith(".*"):
                prefix = self.topic_pattern[:-2]
                return event.topic.startswith(prefix)
            return self.topic_pattern == event.topic
        return True


class EventBus:
    """
    Centralized event bus for the SparkLabs AI-Native Game Engine.

    Provides pub/sub communication between all engine modules.
    Subscribers register with channel/topic filters and priority ordering.
    Events are dispatched synchronously or asynchronously based on handler type.

    Usage:
        bus = EventBus()
        bus.subscribe(EventChannel.ENTITY, "created", on_entity_created)
        bus.emit(Event(channel=EventChannel.ENTITY, topic="created", data={...}))
    """

    def __init__(self, max_history: int = 1000):
        self._subscriptions: Dict[str, Subscription] = {}
        self._history: List[Event] = []
        self._max_history = max_history
        self._channel_index: Dict[EventChannel, List[str]] = {}
        self._stats = {
            "total_emitted": 0,
            "total_dispatched": 0,
            "total_errors": 0,
            "by_channel": {},
        }

    def subscribe(
        self,
        channel: EventChannel,
        topic: str = "*",
        handler: Optional[Callable] = None,
        priority: int = 0,
    ) -> str:
        """
        Subscribe to events on a channel and topic pattern.
        Returns subscription ID for later unsubscription.
        """
        sub = Subscription(
            channel=channel,
            topic_pattern=topic,
            handler=handler,
            priority=priority,
        )
        self._subscriptions[sub.id] = sub

        if channel not in self._channel_index:
            self._channel_index[channel] = []
        self._channel_index[channel].append(sub.id)

        return sub.id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by ID."""
        if subscription_id in self._subscriptions:
            sub = self._subscriptions[subscription_id]
            if sub.channel and sub.channel in self._channel_index:
                try:
                    self._channel_index[sub.channel].remove(subscription_id)
                except ValueError:
                    pass
            del self._subscriptions[subscription_id]
            return True
        return False

    def emit(self, event: Event) -> int:
        """
        Emit an event to all matching subscribers.
        Returns the number of subscribers that received the event.
        """
        self._stats["total_emitted"] += 1
        channel_stats = self._stats["by_channel"]
        ch_name = event.channel.value
        channel_stats[ch_name] = channel_stats.get(ch_name, 0) + 1

        self._add_to_history(event)

        matched = self._find_matching_subscriptions(event)
        matched.sort(key=lambda s: s.priority, reverse=True)

        dispatched = 0
        for sub in matched:
            try:
                if sub.handler:
                    if asyncio.iscoroutinefunction(sub.handler):
                        asyncio.get_event_loop().create_task(
                            sub.handler(event)
                        )
                    else:
                        sub.handler(event)
                    sub.call_count += 1
                    sub.last_called = time.time()
                    dispatched += 1
                    self._stats["total_dispatched"] += 1
            except Exception:
                self._stats["total_errors"] += 1

        return dispatched

    async def emit_async(self, event: Event) -> int:
        """
        Emit an event asynchronously, awaiting all async handlers.
        Returns the number of subscribers that received the event.
        """
        self._stats["total_emitted"] += 1
        channel_stats = self._stats["by_channel"]
        ch_name = event.channel.value
        channel_stats[ch_name] = channel_stats.get(ch_name, 0) + 1

        self._add_to_history(event)

        matched = self._find_matching_subscriptions(event)
        matched.sort(key=lambda s: s.priority, reverse=True)

        dispatched = 0
        for sub in matched:
            try:
                if sub.handler:
                    if asyncio.iscoroutinefunction(sub.handler):
                        await sub.handler(event)
                    else:
                        sub.handler(event)
                    sub.call_count += 1
                    sub.last_called = time.time()
                    dispatched += 1
                    self._stats["total_dispatched"] += 1
            except Exception:
                self._stats["total_errors"] += 1

        return dispatched

    def _find_matching_subscriptions(self, event: Event) -> List[Subscription]:
        matched = []
        for sub in self._subscriptions.values():
            if sub.matches(event):
                matched.append(sub)
        return matched

    def _add_to_history(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(
        self,
        channel: Optional[EventChannel] = None,
        topic: Optional[str] = None,
        limit: int = 50,
    ) -> List[Event]:
        """Get event history, optionally filtered by channel and topic."""
        events = self._history
        if channel:
            events = [e for e in events if e.channel == channel]
        if topic:
            events = [e for e in events if e.topic == topic]
        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "subscription_count": len(self._subscriptions),
            "active_subscriptions": sum(
                1 for s in self._subscriptions.values() if s.active
            ),
            "history_size": len(self._history),
        }

    def clear_history(self) -> None:
        self._history.clear()

    def reset_stats(self) -> None:
        self._stats = {
            "total_emitted": 0,
            "total_dispatched": 0,
            "total_errors": 0,
            "by_channel": {},
        }

    def list_subscriptions(self, channel: Optional[EventChannel] = None) -> List[Dict[str, Any]]:
        subs = self._subscriptions.values()
        if channel:
            subs = [s for s in subs if s.channel == channel]
        return [
            {
                "id": s.id,
                "channel": s.channel.value if s.channel else None,
                "topic_pattern": s.topic_pattern,
                "priority": s.priority,
                "active": s.active,
                "call_count": s.call_count,
                "last_called": s.last_called,
            }
            for s in subs
        ]


_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global EventBus singleton."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


def reset_event_bus() -> None:
    """Reset the global EventBus singleton."""
    global _global_bus
    _global_bus = None
