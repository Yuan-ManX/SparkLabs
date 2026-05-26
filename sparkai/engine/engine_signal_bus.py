"""
SparkLabs Engine - Signal Bus

Typed, decoupled event communication system where game systems
communicate via signals without direct references. Inspired by Godot's
signal system but designed for the SparkLabs AI-native engine,
providing priority-based delivery, scoped emission, and multiple
delivery strategies.

Architecture:
  SignalBus
    |-- SignalRegistry (signal type definitions and metadata)
    |-- ConnectionManager (listener registration and lifecycle)
    |-- EmissionEngine (immediate, deferred, queued, batched delivery)
    |-- SignalHistory (emission tracking for debugging and replay)
    |-- BusMonitor (aggregate statistics and health metrics)

Signal Scopes:
  - LOCAL: confined to the emitting system
  - SCENE: broadcast within the current scene
  - GLOBAL: reach all systems across all scenes
  - PERSISTENT: survive scene transitions, always active

Delivery Modes:
  - IMMEDIATE: synchronous delivery during the current frame
  - DEFERRED: scheduled for a later frame after a delay
  - QUEUED: placed in a FIFO queue for ordered processing
  - BATCHED: grouped and emitted atomically as a unit
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

_time_module = time


class SignalPriority(Enum):
    LOWEST = -2
    LOW = -1
    NORMAL = 0
    HIGH = 1
    HIGHEST = 2
    CRITICAL = 3


class SignalScope(Enum):
    LOCAL = "local"
    SCENE = "scene"
    GLOBAL = "global"
    PERSISTENT = "persistent"


class DeliveryMode(Enum):
    IMMEDIATE = "immediate"
    DEFERRED = "deferred"
    QUEUED = "queued"
    BATCHED = "batched"


class ConnectionState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ONE_SHOT = "one_shot"
    DISCONNECTED = "disconnected"


@dataclass
class SignalStats:
    total_emitted: int = 0
    total_received: int = 0
    total_dropped: int = 0
    peak_queue_size: int = 0
    avg_delivery_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_emitted": self.total_emitted,
            "total_received": self.total_received,
            "total_dropped": self.total_dropped,
            "peak_queue_size": self.peak_queue_size,
            "avg_delivery_ms": round(self.avg_delivery_ms, 3),
        }


@dataclass
class SignalDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    parameters: List[str] = field(default_factory=list)
    scope: SignalScope = SignalScope.LOCAL
    delivery: DeliveryMode = DeliveryMode.IMMEDIATE
    category: str = "general"
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "scope": self.scope.value,
            "delivery": self.delivery.value,
            "category": self.category,
            "created_at": self.created_at,
        }


@dataclass
class SignalConnection:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    signal_id: str = ""
    listener_id: str = ""
    callback: Callable[..., Any] = lambda *args, **kwargs: None
    priority: SignalPriority = SignalPriority.NORMAL
    state: ConnectionState = ConnectionState.ACTIVE
    filter_condition: Optional[Callable[..., bool]] = None
    connection_count: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "listener_id": self.listener_id,
            "priority": self.priority.value,
            "state": self.state.value,
            "has_filter": self.filter_condition is not None,
            "connection_count": self.connection_count,
            "created_at": self.created_at,
        }


@dataclass
class SignalEmission:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    signal_id: str = ""
    emitter_id: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)
    scope: SignalScope = SignalScope.LOCAL
    emission_id: str = ""
    batch_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "emitter_id": self.emitter_id,
            "parameters_summary": {k: str(v)[:60] for k, v in list(self.parameters.items())[:5]},
            "timestamp": self.timestamp,
            "scope": self.scope.value,
            "emission_id": self.emission_id,
            "batch_id": self.batch_id,
        }


@dataclass
class SignalListener:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    owner_system: str = ""
    is_async: bool = False
    max_queue_size: int = 100
    stats: SignalStats = field(default_factory=SignalStats)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "owner_system": self.owner_system,
            "is_async": self.is_async,
            "max_queue_size": self.max_queue_size,
            "stats": self.stats.to_dict(),
            "created_at": self.created_at,
        }


PRIORITY_SORT_ORDER: Dict[SignalPriority, int] = {
    SignalPriority.CRITICAL: 0,
    SignalPriority.HIGHEST: 1,
    SignalPriority.HIGH: 2,
    SignalPriority.NORMAL: 3,
    SignalPriority.LOW: 4,
    SignalPriority.LOWEST: 5,
}


class SignalBus:
    """
    Typed event communication bus with priority-based delivery,
    scoped emission, and multiple delivery strategies.

    Game systems register signals and connect listeners through
    this central bus, enabling fully decoupled communication
    without direct object references.

    Usage:
        bus = get_signal_bus()
        sig_id = bus.define_signal("entity_damaged", "Fires when entity takes damage",
                                    ["entity_id", "amount", "source"], SignalScope.SCENE, DeliveryMode.IMMEDIATE)
        conn_id = bus.register_listener(sig_id, "health_system_listener", handle_damage,
                                         SignalPriority.HIGH, ConnectionState.ACTIVE)
        bus.emit_signal(sig_id, "combat_system", {"entity_id": "ent_1", "amount": 25, "source": "fire"}, SignalScope.SCENE)
    """

    _instance: Optional["SignalBus"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_HISTORY = 500
    MAX_DEFERRED = 1000
    MAX_BATCH_SIZE = 50
    MAX_CONNECTIONS_PER_SIGNAL = 200

    def __init__(self):
        self._definitions: Dict[str, SignalDefinition] = {}
        self._connections: Dict[str, SignalConnection] = {}
        self._listeners: Dict[str, SignalListener] = {}
        self._emissions: Dict[str, SignalEmission] = {}
        self._signal_history: Dict[str, deque] = {}
        self._deferred_queue: deque = deque()
        self._queued_emissions: Dict[str, deque] = {}
        self._active_batches: Dict[str, List[Tuple[str, str, Dict[str, Any], SignalScope]]] = {}
        self._connection_index: Dict[str, Set[str]] = {}
        self._listener_index: Dict[str, Set[str]] = {}
        self._stats: SignalStats = SignalStats()
        self._total_delivery_ms: float = 0.0
        self._total_deliveries: int = 0
        self._paused_signals: Set[str] = set()
        self._global_listeners: Set[str] = set()

    @classmethod
    def get_instance(cls) -> "SignalBus":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Signal Definition
    # ------------------------------------------------------------------

    def define_signal(
        self,
        name: str,
        description: str = "",
        parameters: Optional[List[str]] = None,
        scope: SignalScope = SignalScope.LOCAL,
        delivery: DeliveryMode = DeliveryMode.IMMEDIATE,
        category: str = "general",
    ) -> str:
        definition = SignalDefinition(
            name=name,
            description=description,
            parameters=parameters or [],
            scope=scope,
            delivery=delivery,
            category=category,
        )
        with self._lock:
            self._definitions[definition.id] = definition
            self._connection_index[definition.id] = set()
            self._signal_history[definition.id] = deque(maxlen=self.MAX_HISTORY)
            if delivery == DeliveryMode.QUEUED:
                self._queued_emissions[definition.id] = deque()
        return definition.id

    def get_signal_definition(self, signal_id: str) -> Optional[SignalDefinition]:
        return self._definitions.get(signal_id)

    def list_signal_definitions(
        self,
        scope: Optional[SignalScope] = None,
        category: Optional[str] = None,
    ) -> List[SignalDefinition]:
        results = list(self._definitions.values())
        if scope is not None:
            results = [s for s in results if s.scope == scope]
        if category is not None:
            results = [s for s in results if s.category == category]
        return results

    def remove_signal_definition(self, signal_id: str) -> bool:
        with self._lock:
            if signal_id not in self._definitions:
                return False
            connection_ids = list(self._connection_index.get(signal_id, set()))
            for conn_id in connection_ids:
                self._connections.pop(conn_id, None)
            del self._connection_index[signal_id]
            self._signal_history.pop(signal_id, None)
            self._queued_emissions.pop(signal_id, None)
            del self._definitions[signal_id]
        return True

    # ------------------------------------------------------------------
    # Listener Management
    # ------------------------------------------------------------------

    def create_listener(
        self,
        name: str,
        owner_system: str = "",
        max_queue_size: int = 100,
        is_async: bool = False,
    ) -> str:
        listener = SignalListener(
            name=name,
            owner_system=owner_system,
            is_async=is_async,
            max_queue_size=max_queue_size,
        )
        with self._lock:
            self._listeners[listener.id] = listener
            self._listener_index[listener.id] = set()
        return listener.id

    def get_listener(self, listener_id: str) -> Optional[SignalListener]:
        return self._listeners.get(listener_id)

    def list_listeners(self, owner_system: Optional[str] = None) -> List[SignalListener]:
        results = list(self._listeners.values())
        if owner_system is not None:
            results = [l for l in results if l.owner_system == owner_system]
        return results

    def remove_listener(self, listener_id: str) -> bool:
        with self._lock:
            if listener_id not in self._listeners:
                return False
            connection_ids = list(self._listener_index.get(listener_id, set()))
            for conn_id in connection_ids:
                self._connections.pop(conn_id, None)
                for sig_connections in self._connection_index.values():
                    sig_connections.discard(conn_id)
            del self._listener_index[listener_id]
            del self._listeners[listener_id]
        return True

    # ------------------------------------------------------------------
    # Connection Registration
    # ------------------------------------------------------------------

    def register_listener(
        self,
        signal_id: str,
        listener_name: str,
        callback: Callable[..., Any],
        priority: SignalPriority = SignalPriority.NORMAL,
        state: ConnectionState = ConnectionState.ACTIVE,
        filter_condition: Optional[Callable[..., bool]] = None,
    ) -> Optional[str]:
        if signal_id not in self._definitions:
            return None

        existing = self._connection_index.get(signal_id, set())
        if len(existing) >= self.MAX_CONNECTIONS_PER_SIGNAL:
            return None

        listener = SignalListener(name=listener_name)
        self._listeners[listener.id] = listener
        self._listener_index[listener.id] = set()

        connection = SignalConnection(
            signal_id=signal_id,
            listener_id=listener.id,
            callback=callback,
            priority=priority,
            state=state,
            filter_condition=filter_condition,
        )

        with self._lock:
            self._connections[connection.id] = connection
            self._connection_index[signal_id].add(connection.id)
            self._listener_index[listener.id].add(connection.id)

        return connection.id

    def connect_listener(
        self,
        signal_id: str,
        listener_id: str,
        callback: Callable[..., Any],
        priority: SignalPriority = SignalPriority.NORMAL,
        state: ConnectionState = ConnectionState.ACTIVE,
        filter_condition: Optional[Callable[..., bool]] = None,
    ) -> Optional[str]:
        if signal_id not in self._definitions:
            return None
        if listener_id not in self._listeners:
            return None

        existing = self._connection_index.get(signal_id, set())
        if len(existing) >= self.MAX_CONNECTIONS_PER_SIGNAL:
            return None

        connection = SignalConnection(
            signal_id=signal_id,
            listener_id=listener_id,
            callback=callback,
            priority=priority,
            state=state,
            filter_condition=filter_condition,
        )

        with self._lock:
            self._connections[connection.id] = connection
            self._connection_index[signal_id].add(connection.id)
            self._listener_index[listener_id].add(connection.id)

        return connection.id

    def disconnect_listener(self, connection_id: str) -> bool:
        with self._lock:
            connection = self._connections.get(connection_id)
            if connection is None:
                return False
            connection.state = ConnectionState.DISCONNECTED
            signal_connections = self._connection_index.get(connection.signal_id, set())
            signal_connections.discard(connection_id)
            listener_connections = self._listener_index.get(connection.listener_id, set())
            listener_connections.discard(connection_id)
            del self._connections[connection_id]
        return True

    def pause_connection(self, connection_id: str) -> bool:
        connection = self._connections.get(connection_id)
        if connection is None:
            return False
        if connection.state == ConnectionState.ACTIVE:
            connection.state = ConnectionState.PAUSED
            return True
        return False

    def resume_connection(self, connection_id: str) -> bool:
        connection = self._connections.get(connection_id)
        if connection is None:
            return False
        if connection.state == ConnectionState.PAUSED:
            connection.state = ConnectionState.ACTIVE
            return True
        return False

    def get_connection(self, connection_id: str) -> Optional[SignalConnection]:
        return self._connections.get(connection_id)

    def list_connections(
        self,
        signal_id: Optional[str] = None,
        listener_id: Optional[str] = None,
    ) -> List[SignalConnection]:
        results = list(self._connections.values())
        if signal_id is not None:
            results = [c for c in results if c.signal_id == signal_id]
        if listener_id is not None:
            results = [c for c in results if c.listener_id == listener_id]
        return results

    # ------------------------------------------------------------------
    # Signal Emission
    # ------------------------------------------------------------------

    def emit_signal(
        self,
        signal_id: str,
        emitter_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        scope: Optional[SignalScope] = None,
    ) -> Dict[str, Any]:
        params = parameters or {}
        definition = self._definitions.get(signal_id)

        if definition is None:
            return {"success": False, "error": "Unknown signal", "signal_id": signal_id}

        if signal_id in self._paused_signals:
            return {"success": False, "error": "Signal paused", "signal_id": signal_id}

        emission_scope = scope if scope is not None else definition.scope
        effective_delivery = definition.delivery

        emission = SignalEmission(
            signal_id=signal_id,
            emitter_id=emitter_id,
            parameters=params,
            scope=emission_scope,
            emission_id=uuid.uuid4().hex,
        )

        self._emissions[emission.emission_id] = emission

        history = self._signal_history.get(signal_id)
        if history is not None:
            history.append(emission)

        if effective_delivery == DeliveryMode.DEFERRED:
            self._deferred_queue.append((signal_id, emitter_id, params, emission_scope, _time_module.time()))
            if len(self._deferred_queue) > self.MAX_DEFERRED:
                self._deferred_queue.popleft()
            return {"success": True, "delivery": "deferred", "emission_id": emission.emission_id}

        if effective_delivery == DeliveryMode.QUEUED:
            queue = self._queued_emissions.get(signal_id)
            if queue is not None:
                queue.append(emission)
                peak = max(self._stats.peak_queue_size, len(queue))
                self._stats.peak_queue_size = peak
            return {"success": True, "delivery": "queued", "emission_id": emission.emission_id}

        if effective_delivery == DeliveryMode.BATCHED:
            batch_key = emission_scope.value
            if batch_key not in self._active_batches:
                self._active_batches[batch_key] = []
            batch = self._active_batches[batch_key]
            if len(batch) < self.MAX_BATCH_SIZE:
                batch.append((signal_id, emitter_id, params, emission_scope))
            return {"success": True, "delivery": "batched", "emission_id": emission.emission_id}

        return self._deliver_immediate(signal_id, emitter_id, params, emission_scope, emission.emission_id)

    def _deliver_immediate(
        self,
        signal_id: str,
        emitter_id: str,
        parameters: Dict[str, Any],
        scope: SignalScope,
        emission_id: str,
    ) -> Dict[str, Any]:
        start = _time_module.time()
        connection_ids = self._connection_index.get(signal_id, set()).copy()

        connections: List[Tuple[SignalPriority, SignalConnection]] = []
        for conn_id in connection_ids:
            conn = self._connections.get(conn_id)
            if conn is None:
                continue
            if conn.state not in (ConnectionState.ACTIVE, ConnectionState.ONE_SHOT):
                continue
            connections.append((conn.priority, conn))

        connections.sort(key=lambda item: PRIORITY_SORT_ORDER.get(item[0], 99))

        delivered = 0
        dropped = 0

        for _, conn in connections:
            if conn.filter_condition is not None:
                try:
                    if not conn.filter_condition(**parameters):
                        dropped += 1
                        continue
                except Exception:
                    dropped += 1
                    continue

            try:
                conn.callback(**parameters)
                conn.connection_count += 1
                delivered += 1
                if conn.state == ConnectionState.ONE_SHOT:
                    conn.state = ConnectionState.DISCONNECTED
                    self._connection_index.get(signal_id, set()).discard(conn.id)
                    self._listener_index.get(conn.listener_id, set()).discard(conn.id)
            except Exception:
                dropped += 1

        elapsed = (_time_module.time() - start) * 1000
        self._total_deliveries += 1
        self._total_delivery_ms += elapsed
        self._stats.total_emitted += 1
        self._stats.total_received += delivered
        self._stats.total_dropped += dropped
        if self._total_deliveries > 0:
            self._stats.avg_delivery_ms = self._total_delivery_ms / self._total_deliveries

        return {
            "success": True,
            "delivery": "immediate",
            "emission_id": emission_id,
            "delivered": delivered,
            "dropped": dropped,
            "delivery_ms": round(elapsed, 3),
        }

    def defer_emission(
        self,
        signal_id: str,
        emitter_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        delay_ms: float = 0.0,
    ) -> Optional[str]:
        if signal_id not in self._definitions:
            return None
        if len(self._deferred_queue) >= self.MAX_DEFERRED:
            return None

        params = parameters or {}
        target_time = _time_module.time() + (delay_ms / 1000.0)
        emission_id = uuid.uuid4().hex

        self._deferred_queue.append((signal_id, emitter_id, params, SignalScope.LOCAL, target_time, emission_id))

        return emission_id

    def process_deferred(self, max_count: int = 50) -> int:
        now = _time_module.time()
        processed = 0

        for _ in range(min(max_count, len(self._deferred_queue))):
            if not self._deferred_queue:
                break

            entry = self._deferred_queue[0]
            if len(entry) == 6:
                signal_id, emitter_id, params, scope, target_time, _ = entry
            else:
                signal_id, emitter_id, params, scope, target_time = entry

            if now < target_time:
                break

            self._deferred_queue.popleft()
            self._deliver_immediate(signal_id, emitter_id, params, scope, uuid.uuid4().hex)
            processed += 1

        return processed

    def batch_emit(self, signals: List[Tuple[str, str, Dict[str, Any], SignalScope]], batch_id: Optional[str] = None) -> Optional[str]:
        if len(signals) > self.MAX_BATCH_SIZE:
            return None

        batch_id = batch_id or uuid.uuid4().hex
        self._active_batches[batch_id] = []

        for signal_id, emitter_id, params, scope in signals:
            if signal_id not in self._definitions:
                continue
            emission = SignalEmission(
                signal_id=signal_id,
                emitter_id=emitter_id,
                parameters=params,
                scope=scope,
                batch_id=batch_id,
            )
            self._active_batches[batch_id].append((signal_id, emitter_id, params, scope))
            history = self._signal_history.get(signal_id)
            if history is not None:
                history.append(emission)

        return batch_id

    def flush_batch(self, batch_id: str) -> Dict[str, Any]:
        batch = self._active_batches.pop(batch_id, None)
        if batch is None:
            return {"success": False, "error": "Batch not found"}

        delivered = 0
        dropped = 0

        for signal_id, emitter_id, params, scope in batch:
            result = self._deliver_immediate(signal_id, emitter_id, params, scope, uuid.uuid4().hex)
            delivered += result.get("delivered", 0)
            dropped += result.get("dropped", 0)

        return {
            "success": True,
            "batch_id": batch_id,
            "signals_in_batch": len(batch),
            "delivered": delivered,
            "dropped": dropped,
        }

    def cancel_batch(self, batch_id: str) -> bool:
        if batch_id in self._active_batches:
            del self._active_batches[batch_id]
            return True
        return False

    def flush_signal_queue(self, signal_id: Optional[str] = None) -> Dict[str, Any]:
        if signal_id is not None:
            queue = self._queued_emissions.get(signal_id)
            if queue is None:
                return {"success": False, "error": "No queue for signal"}
            flushed = len(queue)
            while queue:
                emission = queue.popleft()
                self._deliver_immediate(
                    emission.signal_id, emission.emitter_id,
                    emission.parameters, emission.scope, emission.emission_id,
                )
            return {"success": True, "signal_id": signal_id, "flushed": flushed}

        total_flushed = 0
        for q_signal_id, queue in list(self._queued_emissions.items()):
            while queue:
                emission = queue.popleft()
                self._deliver_immediate(
                    emission.signal_id, emission.emitter_id,
                    emission.parameters, emission.scope, emission.emission_id,
                )
                total_flushed += 1

        return {"success": True, "flushed": total_flushed, "queues_cleared": len(self._queued_emissions)}

    # ------------------------------------------------------------------
    # Signal Pausing
    # ------------------------------------------------------------------

    def pause_signal(self, signal_id: str) -> bool:
        if signal_id in self._definitions:
            self._paused_signals.add(signal_id)
            return True
        return False

    def resume_signal(self, signal_id: str) -> bool:
        if signal_id in self._paused_signals:
            self._paused_signals.discard(signal_id)
            return True
        return False

    def is_signal_paused(self, signal_id: str) -> bool:
        return signal_id in self._paused_signals

    # ------------------------------------------------------------------
    # Global Listeners
    # ------------------------------------------------------------------

    def add_global_listener(
        self,
        listener_id: str,
        callback: Callable[..., Any],
    ) -> bool:
        if listener_id not in self._listeners:
            return False
        self._global_listeners.add(listener_id)
        for sig_id in self._definitions:
            self.connect_listener(sig_id, listener_id, callback)
        return True

    def remove_global_listener(self, listener_id: str) -> bool:
        if listener_id not in self._global_listeners:
            return False
        self._global_listeners.discard(listener_id)
        conn_ids = list(self._listener_index.get(listener_id, set()))
        for conn_id in conn_ids:
            self.disconnect_listener(conn_id)
        return True

    # ------------------------------------------------------------------
    # Signal History
    # ------------------------------------------------------------------

    def get_signal_history(self, signal_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        history = self._signal_history.get(signal_id)
        if history is None:
            return []
        recent = list(history)[-limit:]
        return [e.to_dict() for e in recent]

    def get_emission(self, emission_id: str) -> Optional[Dict[str, Any]]:
        emission = self._emissions.get(emission_id)
        if emission:
            return emission.to_dict()
        return None

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        batch = self._active_batches.get(batch_id)
        if batch is None:
            return None
        return {
            "batch_id": batch_id,
            "pending_count": len(batch),
            "signals": [s[0] for s in batch[:20]],
        }

    def list_active_batches(self) -> List[Dict[str, Any]]:
        return [
            {"batch_id": bid, "pending_count": len(b)}
            for bid, b in self._active_batches.items()
        ]

    # ------------------------------------------------------------------
    # Bus Statistics
    # ------------------------------------------------------------------

    def get_bus_stats(self) -> Dict[str, Any]:
        deferred_count = len(self._deferred_queue)
        queue_sizes = {}
        for sig_id, queue in self._queued_emissions.items():
            if queue:
                queue_sizes[sig_id] = len(queue)

        total_connections = len(self._connections)
        scope_counts: Dict[str, int] = {}
        category_counts: Dict[str, int] = {}
        for definition in self._definitions.values():
            scope_key = definition.scope.value
            scope_counts[scope_key] = scope_counts.get(scope_key, 0) + 1
            cat = definition.category
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total_definitions": len(self._definitions),
            "total_listeners": len(self._listeners),
            "total_connections": total_connections,
            "active_connections": sum(
                1 for c in self._connections.values()
                if c.state == ConnectionState.ACTIVE
            ),
            "paused_connections": sum(
                1 for c in self._connections.values()
                if c.state == ConnectionState.PAUSED
            ),
            "disconnected_connections": sum(
                1 for c in self._connections.values()
                if c.state == ConnectionState.DISCONNECTED
            ),
            "paused_signals": len(self._paused_signals),
            "deferred_queued": deferred_count,
            "queued_emissions": {k: v for k, v in queue_sizes.items() if v > 0},
            "active_batches": len(self._active_batches),
            "global_listeners": len(self._global_listeners),
            "emission_stats": self._stats.to_dict(),
            "scope_distribution": scope_counts,
            "category_distribution": category_counts,
            "max_history": self.MAX_HISTORY,
            "max_deferred": self.MAX_DEFERRED,
            "max_batch_size": self.MAX_BATCH_SIZE,
        }

    def get_listener_stats(self, listener_id: str) -> Optional[Dict[str, Any]]:
        listener = self._listeners.get(listener_id)
        if listener is None:
            return None

        connection_count = len(self._listener_index.get(listener_id, set()))
        return {
            "listener": listener.to_dict(),
            "active_connections": connection_count,
            "connection_ids": list(self._listener_index.get(listener_id, set())),
        }

    def get_signal_connections_detail(self, signal_id: str) -> Optional[Dict[str, Any]]:
        definition = self._definitions.get(signal_id)
        if definition is None:
            return None

        connection_ids = self._connection_index.get(signal_id, set())
        connections = []
        for conn_id in connection_ids:
            conn = self._connections.get(conn_id)
            if conn is not None:
                connections.append(conn.to_dict())

        return {
            "signal": definition.to_dict(),
            "connection_count": len(connections),
            "connections": connections,
            "history_size": len(self._signal_history.get(signal_id, deque())),
        }

    # ------------------------------------------------------------------
    # Bus Lifecycle
    # ------------------------------------------------------------------

    def clear_signal(self, signal_id: str) -> Dict[str, Any]:
        if signal_id not in self._definitions:
            return {"success": False, "error": "Unknown signal"}

        connection_ids = list(self._connection_index.get(signal_id, set()))
        for conn_id in connection_ids:
            conn = self._connections.pop(conn_id, None)
            if conn is not None:
                self._listener_index.get(conn.listener_id, set()).discard(conn_id)

        self._connection_index[signal_id].clear()
        self._signal_history[signal_id].clear()
        if signal_id in self._queued_emissions:
            self._queued_emissions[signal_id].clear()
        self._paused_signals.discard(signal_id)

        return {"success": True, "connections_removed": len(connection_ids)}

    def clear_bus(self) -> Dict[str, Any]:
        with self._lock:
            def_count = len(self._definitions)
            conn_count = len(self._connections)
            listener_count = len(self._listeners)
            deferred_count = len(self._deferred_queue)
            batch_count = len(self._active_batches)

            self._definitions.clear()
            self._connections.clear()
            self._listeners.clear()
            self._emissions.clear()
            self._signal_history.clear()
            self._deferred_queue.clear()
            self._queued_emissions.clear()
            self._active_batches.clear()
            self._connection_index.clear()
            self._listener_index.clear()
            self._paused_signals.clear()
            self._global_listeners.clear()

            self._stats = SignalStats()
            self._total_delivery_ms = 0.0
            self._total_deliveries = 0

        return {
            "success": True,
            "definitions_cleared": def_count,
            "connections_cleared": conn_count,
            "listeners_cleared": listener_count,
            "deferred_cleared": deferred_count,
            "batches_cancelled": batch_count,
        }

    def get_bus_summary(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "definitions": len(self._definitions),
            "listeners": len(self._listeners),
            "connections": len(self._connections),
            "total_emitted": self._stats.total_emitted,
            "total_received": self._stats.total_received,
            "total_dropped": self._stats.total_dropped,
            "avg_delivery_ms": round(self._stats.avg_delivery_ms, 3),
            "deferred_pending": len(self._deferred_queue),
            "active_batches": len(self._active_batches),
            "paused_signals": len(self._paused_signals),
        }

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        emissions = list(self._emissions.values())
        emissions.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in emissions[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        active_connections = sum(
            1 for conn in self._connections.values()
            if conn.state == ConnectionState.ACTIVE
        )

        return {
            "total_signals": len(self._definitions),
            "active_connections": active_connections,
            "total_emissions": self._stats.total_emitted,
            "listener_count": len(self._listeners),
        }


def get_signal_bus() -> SignalBus:
    return SignalBus.get_instance()