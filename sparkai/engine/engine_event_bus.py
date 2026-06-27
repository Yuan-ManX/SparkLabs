"""
SparkLabs Engine - Event Bus System

Bidirectional event communication framework that bridges the AI agent layer
and the game engine runtime. Provides a publish-subscribe event architecture
with priority-based routing, event filtering, and cross-system event
propagation between agents, engine subsystems, and the game world.

Architecture:
  EngineEventBus (Singleton)
    |-- EventChannel (named communication channel with subscribers)
    |-- EventPublisher (emits events with priority and routing)
    |-- EventSubscriber (receives and filters events by type)
    |-- EventRouter (routes events between agent and engine layers)
    |-- EventBuffer (queues events for ordered delivery)

Event Categories:
  - AGENT: agent decisions, state changes, learning events
  - ENGINE: render, physics, audio, input events
  - GAME: entity lifecycle, collision, scoring events
  - WORLD: weather, time, terrain, ecosystem events
  - UI: interface events, user input, display updates
  - SYSTEM: initialization, shutdown, error events

Usage:
    eb = get_engine_event_bus()
    eb.initialize()

    # Subscribe to agent events
    eb.subscribe("agent_decisions", handle_agent_decision, EventCategory.AGENT)

    # Publish an event
    eb.publish(EngineEvent(
        event_type="entity_spawned",
        category=EventCategory.GAME,
        data={"entity_id": "e123", "position": (100, 200)},
    ))

    # Route events between agent and engine
    eb.route_agent_to_engine(agent_event)
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class EventCategory(Enum):
    """Categories of events in the engine."""
    AGENT = "agent"          # Agent-related events
    ENGINE = "engine"        # Engine subsystem events
    GAME = "game"            # Game logic events
    WORLD = "world"          # World and environment events
    UI = "ui"                # User interface events
    SYSTEM = "system"        # System lifecycle events
    NETWORK = "network"      # Network events
    CUSTOM = "custom"        # User-defined events


class EventPriority(Enum):
    """Priority levels for event delivery."""
    CRITICAL = 0    # Delivered immediately, blocks publisher
    HIGH = 1        # Delivered before normal events
    NORMAL = 2      # Standard delivery order
    LOW = 3         # Delivered after normal events
    BACKGROUND = 4  # Delivered when idle


class EventDeliveryMode(Enum):
    """How events are delivered to subscribers."""
    SYNCHRONOUS = "synchronous"      # Block until all subscribers process
    ASYNCHRONOUS = "asynchronous"    # Queue for later delivery
    BROADCAST = "broadcast"          # Send to all subscribers simultaneously
    ROUND_ROBIN = "round_robin"      # Send to one subscriber at a time


class EventChannelState(Enum):
    """State of an event channel."""
    ACTIVE = "active"
    PAUSED = "paused"
    DRAINING = "draining"
    CLOSED = "closed"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class EngineEvent:
    """An event in the engine event bus."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: str = ""
    category: EventCategory = EventCategory.CUSTOM
    priority: EventPriority = EventPriority.NORMAL
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    ttl: float = 0.0  # Time-to-live in seconds, 0 = no expiry
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "category": self.category.value,
            "priority": self.priority.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "ttl": self.ttl,
            "tags": self.tags,
        }

    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return (time.time() - self.timestamp) > self.ttl


@dataclass
class EventSubscription:
    """A subscription to an event channel."""
    subscription_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    subscriber_id: str = ""
    event_types: List[str] = field(default_factory=list)
    categories: List[EventCategory] = field(default_factory=list)
    handler: Optional[Callable[[EngineEvent], None]] = None
    filter_fn: Optional[Callable[[EngineEvent], bool]] = None
    created_at: float = field(default_factory=time.time)
    active: bool = True
    events_received: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "subscriber_id": self.subscriber_id,
            "event_types": self.event_types,
            "categories": [c.value for c in self.categories],
            "active": self.active,
            "events_received": self.events_received,
            "created_at": self.created_at,
        }


@dataclass
class EventChannel:
    """A named event channel with subscribers."""
    channel_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    state: EventChannelState = EventChannelState.ACTIVE
    subscriptions: Dict[str, EventSubscription] = field(default_factory=dict)
    event_buffer: List[EngineEvent] = field(default_factory=list)
    max_buffer_size: int = 1000
    created_at: float = field(default_factory=time.time)
    total_events: int = 0
    total_delivered: int = 0
    total_dropped: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "state": self.state.value,
            "subscriber_count": len(self.subscriptions),
            "buffer_size": len(self.event_buffer),
            "total_events": self.total_events,
            "total_delivered": self.total_delivered,
            "total_dropped": self.total_dropped,
        }


@dataclass
class EventDeliveryResult:
    """Result of delivering an event."""
    event_id: str = ""
    delivered_to: int = 0
    failed_for: int = 0
    skipped: int = 0
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "delivered_to": self.delivered_to,
            "failed_for": self.failed_for,
            "skipped": self.skipped,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
        }


@dataclass
class EventBusStats:
    """Statistics for the event bus."""
    total_events_published: int = 0
    total_events_delivered: int = 0
    total_events_dropped: int = 0
    active_channels: int = 0
    total_subscribers: int = 0
    avg_delivery_ms: float = 0.0
    events_per_second: float = 0.0
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_events_published": self.total_events_published,
            "total_events_delivered": self.total_events_delivered,
            "total_events_dropped": self.total_events_dropped,
            "active_channels": self.active_channels,
            "total_subscribers": self.total_subscribers,
            "avg_delivery_ms": round(self.avg_delivery_ms, 2),
            "events_per_second": round(self.events_per_second, 2),
            "uptime_seconds": round(self.uptime_seconds, 2),
        }


# =============================================================================
# EngineEventBus (Singleton)
# =============================================================================


class EngineEventBus:
    """Bidirectional event bus bridging agent and engine layers.

    Provides a publish-subscribe event system that enables communication
    between AI agents, game engine subsystems, and the game world. Supports
    priority-based routing, event filtering, and buffered delivery.

    Usage:
        eb = EngineEventBus.get_instance()
        eb.initialize()

        eb.subscribe("my_handler", handle_event, [EventCategory.GAME])
        eb.publish(EngineEvent(event_type="score_changed", category=EventCategory.GAME))
    """

    _instance: Optional["EngineEventBus"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if EngineEventBus._instance is not None:
            raise RuntimeError("Use EngineEventBus.get_instance()")
        self._initialized: bool = False
        self._lock = threading.RLock()
        self._start_time: float = time.time()
        self._channels: Dict[str, EventChannel] = {}
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._event_history: List[EngineEvent] = []
        self._delivery_results: List[EventDeliveryResult] = []
        self._route_table: Dict[str, List[str]] = defaultdict(list)
        self._global_filters: List[Callable[[EngineEvent], bool]] = []
        self._stats = EventBusStats()

    @classmethod
    def get_instance(cls) -> "EngineEventBus":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}

            self._start_time = time.time()

            # Create default channels
            for category in EventCategory:
                self._channels[category.value] = EventChannel(
                    name=category.value,
                )

            self._initialized = True
            return {
                "status": "initialized",
                "success": True,
                "channels": list(self._channels.keys()),
            }

    def shutdown(self) -> Dict[str, Any]:
        with self._lock:
            self._initialized = False
            # Drain all channels
            for channel in self._channels.values():
                channel.state = EventChannelState.CLOSED
                channel.event_buffer.clear()
            return {
                "success": True,
                "stats": self._stats.to_dict(),
            }

    # -------------------------------------------------------------------------
    # Channel Management
    # -------------------------------------------------------------------------

    def create_channel(self, name: str, max_buffer: int = 1000) -> Dict[str, Any]:
        """Create a custom event channel."""
        with self._lock:
            if name in self._channels:
                return {"success": False, "error": f"Channel '{name}' already exists"}
            channel = EventChannel(name=name, max_buffer_size=max_buffer)
            self._channels[name] = channel
            return {"success": True, "channel": channel.to_dict()}

    def get_channel(self, name: str) -> Optional[Dict[str, Any]]:
        """Get channel info by name."""
        channel = self._channels.get(name)
        return channel.to_dict() if channel else None

    def list_channels(self) -> List[Dict[str, Any]]:
        """List all event channels."""
        return [c.to_dict() for c in self._channels.values()]

    # -------------------------------------------------------------------------
    # Subscription Management
    # -------------------------------------------------------------------------

    def subscribe(self, subscriber_id: str,
                  handler: Callable[[EngineEvent], None],
                  categories: Optional[List[EventCategory]] = None,
                  event_types: Optional[List[str]] = None,
                  filter_fn: Optional[Callable[[EngineEvent], bool]] = None) -> Dict[str, Any]:
        """Subscribe to events with optional filtering."""
        with self._lock:
            subscription = EventSubscription(
                subscriber_id=subscriber_id,
                event_types=event_types or [],
                categories=categories or [],
                handler=handler,
                filter_fn=filter_fn,
            )

            self._subscriptions[subscription.subscription_id] = subscription

            # Register with relevant channels
            target_categories = categories or list(EventCategory)
            for cat in target_categories:
                channel = self._channels.get(cat.value)
                if channel:
                    channel.subscriptions[subscription.subscription_id] = subscription

            return {
                "success": True,
                "subscription_id": subscription.subscription_id,
                "subscriber_id": subscriber_id,
            }

    def unsubscribe(self, subscription_id: str) -> Dict[str, Any]:
        """Remove a subscription."""
        with self._lock:
            sub = self._subscriptions.pop(subscription_id, None)
            if not sub:
                return {"success": False, "error": "Subscription not found"}

            # Remove from all channels
            for channel in self._channels.values():
                channel.subscriptions.pop(subscription_id, None)

            return {"success": True, "subscription_id": subscription_id}

    def list_subscriptions(self) -> List[Dict[str, Any]]:
        """List all subscriptions."""
        return [s.to_dict() for s in self._subscriptions.values()]

    # -------------------------------------------------------------------------
    # Event Publishing
    # -------------------------------------------------------------------------

    def publish(self, event: EngineEvent,
                delivery_mode: EventDeliveryMode = EventDeliveryMode.ASYNCHRONOUS) -> Dict[str, Any]:
        """Publish an event to the bus."""
        if not self._initialized:
            return {"success": False, "error": "Event bus not initialized"}

        # Check global filters
        for filt in self._global_filters:
            if not filt(event):
                self._stats.total_events_dropped += 1
                return {"success": False, "error": "Event filtered out"}

        # Route to appropriate channel
        channel = self._channels.get(event.category.value)
        if not channel:
            channel = self._channels.get(EventCategory.CUSTOM.value)

        if channel and channel.state != EventChannelState.ACTIVE:
            return {"success": False, "error": f"Channel '{channel.name}' is {channel.state.value}"}

        self._stats.total_events_published += 1

        if delivery_mode == EventDeliveryMode.SYNCHRONOUS:
            return self._deliver_sync(event, channel)
        else:
            return self._deliver_async(event, channel)

    def publish_batch(self, events: List[EngineEvent],
                      delivery_mode: EventDeliveryMode = EventDeliveryMode.ASYNCHRONOUS) -> Dict[str, Any]:
        """Publish multiple events at once."""
        results = []
        for event in events:
            results.append(self.publish(event, delivery_mode))
        return {"success": True, "published": len(results), "results": results}

    def _deliver_sync(self, event: EngineEvent,
                      channel: Optional[EventChannel]) -> Dict[str, Any]:
        """Deliver event synchronously to all subscribers."""
        start = time.time()
        delivered = 0
        failed = 0
        errors = []

        if channel:
            for sub in list(channel.subscriptions.values()):
                if not sub.active:
                    continue
                if sub.event_types and event.event_type not in sub.event_types:
                    continue
                if sub.filter_fn and not sub.filter_fn(event):
                    continue

                try:
                    if sub.handler:
                        sub.handler(event)
                        sub.events_received += 1
                        delivered += 1
                except Exception as e:
                    failed += 1
                    errors.append(str(e))

        result = EventDeliveryResult(
            event_id=event.event_id,
            delivered_to=delivered,
            failed_for=failed,
            duration_ms=(time.time() - start) * 1000,
            errors=errors,
        )

        self._record_delivery(event, result, channel)
        return {"success": True, "delivery": result.to_dict()}

    def _deliver_async(self, event: EngineEvent,
                       channel: Optional[EventChannel]) -> Dict[str, Any]:
        """Queue event for asynchronous delivery."""
        if channel:
            if len(channel.event_buffer) >= channel.max_buffer_size:
                channel.total_dropped += 1
                self._stats.total_events_dropped += 1
                return {"success": False, "error": "Channel buffer full"}

            channel.event_buffer.append(event)
            channel.total_events += 1

        # Process buffer in background (simulated)
        self._process_buffer(channel)

        return {
            "success": True,
            "event_id": event.event_id,
            "queued": True,
            "channel": channel.name if channel else "unknown",
        }

    def _process_buffer(self, channel: Optional[EventChannel]) -> None:
        """Process buffered events in the channel."""
        if not channel:
            return

        while channel.event_buffer:
            event = channel.event_buffer.pop(0)
            if event.is_expired():
                channel.total_dropped += 1
                continue

            delivered = 0
            for sub in list(channel.subscriptions.values()):
                if not sub.active:
                    continue
                if sub.event_types and event.event_type not in sub.event_types:
                    continue
                if sub.filter_fn and not sub.filter_fn(event):
                    continue

                try:
                    if sub.handler:
                        sub.handler(event)
                        sub.events_received += 1
                        delivered += 1
                except Exception:
                    pass

            channel.total_delivered += delivered
            self._stats.total_events_delivered += delivered

    def _record_delivery(self, event: EngineEvent,
                         result: EventDeliveryResult,
                         channel: Optional[EventChannel]) -> None:
        """Record delivery for history."""
        self._event_history.append(event)
        if len(self._event_history) > 5000:
            self._event_history = self._event_history[-2500:]

        self._delivery_results.append(result)
        if len(self._delivery_results) > 1000:
            self._delivery_results = self._delivery_results[-500:]

        if channel:
            channel.total_delivered += result.delivered_to

        self._stats.total_events_delivered += result.delivered_to

    # -------------------------------------------------------------------------
    # Agent-Engine Routing
    # -------------------------------------------------------------------------

    def route_agent_to_engine(self, agent_event: Dict[str, Any]) -> Dict[str, Any]:
        """Route an agent event to the engine layer."""
        event_type = agent_event.get("event_type", "agent_event")
        engine_event = EngineEvent(
            event_type=f"agent.{event_type}",
            category=EventCategory.AGENT,
            source="agent_layer",
            data=agent_event,
            tags=["agent_to_engine"],
        )
        return self.publish(engine_event, EventDeliveryMode.ASYNCHRONOUS)

    def route_engine_to_agent(self, engine_event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route an engine event to the agent layer."""
        event_type = engine_event_data.get("event_type", "engine_event")
        agent_event = EngineEvent(
            event_type=f"engine.{event_type}",
            category=EventCategory.ENGINE,
            source="engine_layer",
            data=engine_event_data,
            tags=["engine_to_agent"],
        )
        return self.publish(agent_event, EventDeliveryMode.ASYNCHRONOUS)

    def add_route(self, source_type: str, target_channel: str) -> Dict[str, Any]:
        """Add a routing rule between event types and channels."""
        with self._lock:
            self._route_table[source_type].append(target_channel)
            return {"success": True, "source": source_type, "target": target_channel}

    # -------------------------------------------------------------------------
    # Filtering
    # -------------------------------------------------------------------------

    def add_global_filter(self,
                          filter_fn: Callable[[EngineEvent], bool]) -> Dict[str, Any]:
        """Add a global event filter."""
        with self._lock:
            self._global_filters.append(filter_fn)
            return {"success": True, "filter_count": len(self._global_filters)}

    def clear_filters(self) -> Dict[str, Any]:
        """Remove all global filters."""
        with self._lock:
            count = len(self._global_filters)
            self._global_filters.clear()
            return {"success": True, "removed": count}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_event_history(self, category: Optional[EventCategory] = None,
                          limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent event history."""
        events = self._event_history
        if category:
            events = [e for e in events if e.category == category]
        return [e.to_dict() for e in events[-limit:]]

    def get_delivery_stats(self) -> Dict[str, Any]:
        """Get event delivery statistics."""
        updates = {
            "active_channels": sum(
                1 for c in self._channels.values()
                if c.state == EventChannelState.ACTIVE
            ),
            "total_subscribers": len(self._subscriptions),
            "uptime_seconds": time.time() - self._start_time,
        }
        for k, v in updates.items():
            setattr(self._stats, k, v)

        if self._stats.uptime_seconds > 0:
            self._stats.events_per_second = (
                self._stats.total_events_published / self._stats.uptime_seconds
            )

        return self._stats.to_dict()

    def get_status(self) -> Dict[str, Any]:
        """Get current bus status."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "channels": len(self._channels),
                "subscriptions": len(self._subscriptions),
                "events_published": self._stats.total_events_published,
                "events_delivered": self._stats.total_events_delivered,
                "events_dropped": self._stats.total_events_dropped,
                "uptime_seconds": time.time() - self._start_time,
            }


# ── Module Accessor ──

def get_engine_event_bus() -> EngineEventBus:
    """Get the singleton engine event bus instance."""
    return EngineEventBus.get_instance()