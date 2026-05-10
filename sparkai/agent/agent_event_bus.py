"""
SparkLabs Agent - Event Bus

Centralized publish-subscribe event bus for inter-agent and
agent-to-engine communication. Enables decoupled message
passing between agents, game systems, and editor components
using typed event channels with priority routing.

Architecture:
  AgentEventBus
    |-- EventChannel (typed message topic)
    |-- Subscription (agent + filter + handler binding)
    |-- PriorityRouter (order events by importance)
    |-- AsyncDispatcher (non-blocking event delivery)
    |-- EventTrace (audit trail of all dispatched events)

Event Domains:
  - AGENT_LIFECYCLE: agent creation, destruction, state changes
  - GAME_EVENT: entity spawn, collision, score changes
  - EDITOR_EVENT: file save, scene switch, build start
  - USER_ACTION: input, selection, command execution
  - SYSTEM_ALERT: errors, warnings, performance thresholds
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class EventPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class EventDomain(Enum):
    AGENT_LIFECYCLE = "agent_lifecycle"
    GAME_EVENT = "game_event"
    EDITOR_EVENT = "editor_event"
    USER_ACTION = "user_action"
    SYSTEM_ALERT = "system_alert"
    CUSTOM = "custom"


@dataclass
class AgentEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    domain: EventDomain = EventDomain.CUSTOM
    event_type: str = ""
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "domain": self.domain.value,
            "event_type": self.event_type,
            "source": self.source,
            "priority": self.priority.name,
            "timestamp": self.timestamp,
        }


@dataclass
class Subscription:
    sub_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    domain: Optional[EventDomain] = None
    event_type: Optional[str] = None
    handler: Optional[Callable[[AgentEvent], None]] = None
    subscriber_name: str = ""
    filter_fn: Optional[Callable[[AgentEvent], bool]] = None

    def matches(self, event: AgentEvent) -> bool:
        if self.domain and event.domain != self.domain:
            return False
        if self.event_type and event.event_type != self.event_type:
            return False
        if self.filter_fn and not self.filter_fn(event):
            return False
        return True


class AgentEventBus:
    """Centralized publish-subscribe event bus for agent communication."""

    _instance: Optional["AgentEventBus"] = None
    _lock = threading.Lock()

    MAX_EVENT_HISTORY = 1000
    MAX_SUBSCRIBERS = 500

    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}
        self._event_history: deque = deque(maxlen=self.MAX_EVENT_HISTORY)
        self._priority_queues: Dict[EventPriority, deque] = {
            p: deque() for p in EventPriority
        }
        self._domain_subscribers: Dict[EventDomain, List[str]] = defaultdict(list)
        self._stats: Dict[str, int] = defaultdict(int)

    @classmethod
    def get_instance(cls) -> "AgentEventBus":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def subscribe(
        self,
        handler: Callable[[AgentEvent], None],
        subscriber_name: str = "",
        domain: Optional[EventDomain] = None,
        event_type: Optional[str] = None,
        filter_fn: Optional[Callable[[AgentEvent], bool]] = None,
    ) -> Subscription:
        sub = Subscription(
            domain=domain,
            event_type=event_type,
            handler=handler,
            subscriber_name=subscriber_name,
            filter_fn=filter_fn,
        )
        self._subscriptions[sub.sub_id] = sub
        if domain:
            self._domain_subscribers[domain].append(sub.sub_id)
        return sub

    def unsubscribe(self, sub_id: str) -> bool:
        if sub_id in self._subscriptions:
            sub = self._subscriptions[sub_id]
            if sub.domain:
                self._domain_subscribers[sub.domain].remove(sub_id)
            del self._subscriptions[sub_id]
            return True
        return False

    def emit(
        self,
        domain: EventDomain,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        source: str = "",
        priority: EventPriority = EventPriority.NORMAL,
    ) -> AgentEvent:
        event = AgentEvent(
            domain=domain,
            event_type=event_type,
            data=data or {},
            source=source,
            priority=priority,
        )
        self._priority_queues[priority].append(event)
        self._event_history.append(event)
        self._stats[f"{domain.value}:{event_type}"] += 1
        return event

    def dispatch(self, max_events: int = 50) -> int:
        dispatched = 0
        for priority in EventPriority:
            queue = self._priority_queues[priority]
            for _ in range(min(max_events - dispatched, len(queue))):
                if not queue:
                    break
                event = queue.popleft()

                candidates = list(self._subscriptions.values())
                if event.domain:
                    domain_subs = [
                        self._subscriptions[sid]
                        for sid in self._domain_subscribers.get(event.domain, [])
                        if sid in self._subscriptions
                    ]
                    global_subs = [
                        s for s in candidates if not s.domain
                    ]
                    candidates = domain_subs + global_subs

                for sub in candidates:
                    if sub.matches(event) and sub.handler:
                        try:
                            sub.handler(event)
                            dispatched += 1
                        except Exception:
                            pass

                if dispatched >= max_events:
                    break
            if dispatched >= max_events:
                break
        return dispatched

    def emit_and_dispatch(
        self,
        domain: EventDomain,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        source: str = "",
        priority: EventPriority = EventPriority.NORMAL,
    ) -> AgentEvent:
        event = self.emit(domain, event_type, data, source, priority)
        self.dispatch(max_events=10)
        return event

    def get_history(
        self,
        domain: Optional[EventDomain] = None,
        limit: int = 50,
    ) -> List[AgentEvent]:
        events = list(self._event_history)
        if domain:
            events = [e for e in events if e.domain == domain]
        return events[-limit:]

    def get_subscribers(self, domain: Optional[EventDomain] = None) -> List[Subscription]:
        if domain:
            return [
                self._subscriptions[sid]
                for sid in self._domain_subscribers.get(domain, [])
                if sid in self._subscriptions
            ]
        return list(self._subscriptions.values())

    def get_pending_count(self) -> int:
        return sum(len(q) for q in self._priority_queues.values())

    def clear_history(self) -> None:
        self._event_history.clear()
        self._stats.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "subscriptions": len(self._subscriptions),
            "event_history": len(self._event_history),
            "pending_events": self.get_pending_count(),
            "total_event_types": len(self._stats),
            "domain_counts": {
                d.value: len(sids)
                for d, sids in self._domain_subscribers.items()
            },
            "top_event_types": sorted(
                self._stats.items(), key=lambda x: -x[1]
            )[:10],
        }


def get_agent_event_bus() -> AgentEventBus:
    return AgentEventBus.get_instance()