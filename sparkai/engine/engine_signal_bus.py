"""
SparkLabs Engine - Signal Bus

Decoupled signal/event communication system providing a unified
signal bus and observer pattern communication layer. Game systems
communicate via typed signals without direct references, using
namespace-isolated signal definitions, priority-ordered listener
connections, and multiple emission strategies including synchronous,
asynchronous, and batched atomic delivery.

Architecture:
  SignalBus
    |-- SignalDefinition (typed signal metadata with parameter schema)
    |-- SignalConnection (listener binding with priority and lifecycle)
    |-- SignalEmission (discrete emission record with payload tracking)
    |-- NamespaceRegistry (isolated signal spaces for modularity)
    |-- EmissionRouter (priority-sorted, one-shot-aware delivery engine)

Signal Flow:
  1. define_signal(name, parameters, category, namespace) → signal_id
  2. connect(signal_id, listener_id, callback, priority) → connection_id
  3. emit(signal_id, payload, emitted_by) → delivery to all listeners
  4. One-shot connections auto-disconnect after first successful delivery
  5. emit_async dispatches non-blocking emission on a worker thread
  6. batch_emit delivers multiple signals atomically under a single lock
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class SignalCategory(Enum):
    GAMEPLAY = "gameplay"
    PHYSICS = "physics"
    INPUT = "input"
    UI = "ui"
    AUDIO = "audio"
    NETWORK = "network"
    ANIMATION = "animation"
    LIFECYCLE = "lifecycle"
    CUSTOM = "custom"


class ConnectionState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ONE_SHOT_PENDING = "one_shot_pending"
    DISCONNECTED = "disconnected"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SignalDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    category: SignalCategory = SignalCategory.CUSTOM
    namespace: str = "default"
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parameters": [
                {"name": p.get("name", ""), "type": p.get("type", "any"), "default": p.get("default")}
                for p in self.parameters
            ],
            "category": self.category.value,
            "namespace": self.namespace,
            "created_at": self.created_at,
        }


@dataclass
class SignalConnection:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    signal_id: str = ""
    listener_id: str = ""
    callback_name: str = ""
    priority: int = 0
    one_shot: bool = False
    enabled: bool = True
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "listener_id": self.listener_id,
            "callback_name": self.callback_name,
            "priority": self.priority,
            "one_shot": self.one_shot,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


@dataclass
class SignalEmission:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    signal_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    emitted_by: str = ""
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "payload_summary": {k: str(v)[:80] for k, v in list(self.payload.items())[:8]},
            "emitted_by": self.emitted_by,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# SignalBus — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class SignalBus:
    """
    Decoupled signal/event communication bus with priority-based delivery,
    namespace isolation, one-shot auto-disconnect, and asynchronous emission.

    Systems register typed signal definitions and connect listeners via
    named callbacks. Emissions are routed to all connected listeners in
    descending priority order. One-shot connections automatically
    disconnect after their first successful invocation.

    Thread-safe via a reentrant lock. Use get_signal_bus() or
    SignalBus.get_instance() to obtain the singleton instance.

    Usage:
        bus = get_signal_bus()
        sig_id = bus.define_signal(
            "entity_damaged",
            "Fires when an entity takes damage",
            [{"name": "entity_id", "type": "str", "default": ""},
             {"name": "amount", "type": "float", "default": 0.0},
             {"name": "source", "type": "str", "default": "unknown"}],
            SignalCategory.GAMEPLAY,
            namespace="combat",
        )
        conn_id = bus.connect(sig_id, "health_system", "on_entity_damaged", callback, priority=10)
        bus.emit(sig_id, {"entity_id": "ent_1", "amount": 25.0, "source": "fire"}, "combat_system")
    """

    _instance: Optional["SignalBus"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_HISTORY_PER_SIGNAL = 500
    MAX_CONNECTIONS_PER_SIGNAL = 200
    MAX_BATCH_SIZE = 100
    DEFAULT_NAMESPACE = "default"

    def __new__(cls) -> "SignalBus":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._definitions: Dict[str, SignalDefinition] = {}
        self._connections: Dict[str, SignalConnection] = {}
        self._emission_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.MAX_HISTORY_PER_SIGNAL)
        )
        self._callback_registry: Dict[Tuple[str, str], Callable[..., Any]] = {}
        self._listener_connections: Dict[str, Set[str]] = defaultdict(set)
        self._signal_connections: Dict[str, Set[str]] = defaultdict(set)
        self._namespace_index: Dict[str, Set[str]] = defaultdict(set)
        self._batches: Dict[str, List[Tuple[str, Dict[str, Any], str]]] = {}
        self._total_emissions: int = 0
        self._total_deliveries: int = 0
        self._total_drops: int = 0
        self._cumulative_delivery_ms: float = 0.0
        self._delivery_samples: int = 0
        self._paused_signals: Set[str] = set()
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "SignalBus":
        return cls()

    # ------------------------------------------------------------------
    # Signal Definition
    # ------------------------------------------------------------------

    def define_signal(
        self,
        name: str,
        description: str = "",
        parameters: Optional[List[Dict[str, Any]]] = None,
        category: SignalCategory = SignalCategory.CUSTOM,
        namespace: str = DEFAULT_NAMESPACE,
    ) -> str:
        with self._lock:
            definition = SignalDefinition(
                name=name,
                description=description,
                parameters=parameters or [],
                category=category,
                namespace=namespace or self.DEFAULT_NAMESPACE,
            )
            self._definitions[definition.id] = definition
            self._signal_connections[definition.id] = set()
            self._namespace_index[definition.namespace].add(definition.id)
            return definition.id

    def get_signal_definition(self, signal_id: str) -> Optional[SignalDefinition]:
        with self._lock:
            return self._definitions.get(signal_id)

    def find_signals_by_name(self, name: str, namespace: Optional[str] = None) -> List[SignalDefinition]:
        with self._lock:
            results = [d for d in self._definitions.values() if d.name == name]
            if namespace is not None:
                results = [d for d in results if d.namespace == namespace]
            return results

    def list_definitions(
        self,
        namespace: Optional[str] = None,
        category: Optional[SignalCategory] = None,
    ) -> List[SignalDefinition]:
        with self._lock:
            results = list(self._definitions.values())
            if namespace is not None:
                results = [d for d in results if d.namespace == namespace]
            if category is not None:
                results = [d for d in results if d.category == category]
            return results

    def remove_signal_definition(self, signal_id: str) -> bool:
        with self._lock:
            definition = self._definitions.pop(signal_id, None)
            if definition is None:
                return False
            self._namespace_index[definition.namespace].discard(signal_id)
            conn_ids = list(self._signal_connections.get(signal_id, set()))
            for conn_id in conn_ids:
                connection = self._connections.pop(conn_id, None)
                if connection is not None:
                    self._listener_connections[connection.listener_id].discard(conn_id)
            self._signal_connections.pop(signal_id, None)
            self._emission_history.pop(signal_id, None)
            self._paused_signals.discard(signal_id)
            return True

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------

    def connect(
        self,
        signal_id: str,
        listener_id: str,
        callback_name: str,
        callback: Callable[..., Any],
        priority: int = 0,
        one_shot: bool = False,
        enabled: bool = True,
    ) -> Optional[str]:
        with self._lock:
            if signal_id not in self._definitions:
                return None

            existing_connections = self._signal_connections.get(signal_id, set())
            if len(existing_connections) >= self.MAX_CONNECTIONS_PER_SIGNAL:
                return None

            connection = SignalConnection(
                signal_id=signal_id,
                listener_id=listener_id,
                callback_name=callback_name,
                priority=priority,
                one_shot=one_shot,
                enabled=enabled,
            )
            self._connections[connection.id] = connection
            self._signal_connections[signal_id].add(connection.id)
            self._listener_connections[listener_id].add(connection.id)
            self._callback_registry[(listener_id, callback_name)] = callback
            return connection.id

    def disconnect(self, connection_id: str) -> bool:
        with self._lock:
            connection = self._connections.pop(connection_id, None)
            if connection is None:
                return False
            self._signal_connections.get(connection.signal_id, set()).discard(connection_id)
            self._listener_connections.get(connection.listener_id, set()).discard(connection_id)
            remaining = any(
                conn_id in self._signal_connections.get(connection.signal_id, set())
                for conn_id in self._listener_connections.get(connection.listener_id, set())
            )
            if not remaining:
                self._callback_registry.pop((connection.listener_id, connection.callback_name), None)
            return True

    def disconnect_group(self, listener_id: str) -> int:
        with self._lock:
            conn_ids = list(self._listener_connections.get(listener_id, set()))
            count = 0
            for conn_id in conn_ids:
                connection = self._connections.pop(conn_id, None)
                if connection is not None:
                    self._signal_connections.get(connection.signal_id, set()).discard(conn_id)
                    count += 1
            self._listener_connections.pop(listener_id, None)
            keys_to_remove = [
                key for key in self._callback_registry if key[0] == listener_id
            ]
            for key in keys_to_remove:
                del self._callback_registry[key]
            return count

    def pause_connection(self, connection_id: str) -> bool:
        with self._lock:
            connection = self._connections.get(connection_id)
            if connection is not None and connection.enabled:
                connection.enabled = False
                return True
            return False

    def resume_connection(self, connection_id: str) -> bool:
        with self._lock:
            connection = self._connections.get(connection_id)
            if connection is not None and not connection.enabled:
                connection.enabled = True
                return True
            return False

    def get_connection(self, connection_id: str) -> Optional[SignalConnection]:
        with self._lock:
            return self._connections.get(connection_id)

    # ------------------------------------------------------------------
    # Listener Querying
    # ------------------------------------------------------------------

    def get_listeners(self, signal_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            conn_ids = self._signal_connections.get(signal_id, set())
            listeners: List[Dict[str, Any]] = []
            for conn_id in conn_ids:
                connection = self._connections.get(conn_id)
                if connection is not None:
                    listeners.append(connection.to_dict())
            listeners.sort(key=lambda l: -l["priority"])
            return listeners

    def get_listener_connections(self, listener_id: str) -> List[SignalConnection]:
        with self._lock:
            conn_ids = self._listener_connections.get(listener_id, set())
            return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    # ------------------------------------------------------------------
    # Signal Emission
    # ------------------------------------------------------------------

    def emit(
        self,
        signal_id: str,
        payload: Optional[Dict[str, Any]] = None,
        emitted_by: str = "",
    ) -> Dict[str, Any]:
        data = payload or {}
        with self._lock:
            definition = self._definitions.get(signal_id)
            if definition is None:
                return {"success": False, "error": "unknown_signal", "signal_id": signal_id}

            if signal_id in self._paused_signals:
                return {"success": False, "error": "signal_paused", "signal_id": signal_id}

            if not self._validate_payload(definition, data):
                return {"success": False, "error": "payload_validation_failed", "signal_id": signal_id}

            return self._deliver(signal_id, data, emitted_by)

    def emit_async(
        self,
        signal_id: str,
        payload: Optional[Dict[str, Any]] = None,
        emitted_by: str = "",
    ) -> Dict[str, Any]:
        with self._lock:
            definition = self._definitions.get(signal_id)
            if definition is None:
                return {"success": False, "error": "unknown_signal", "signal_id": signal_id}

        thread = threading.Thread(
            target=self._emit_async_target,
            args=(signal_id, payload or {}, emitted_by),
            daemon=True,
        )
        thread.start()
        return {"success": True, "delivery": "async_dispatched", "signal_id": signal_id}

    def _emit_async_target(
        self,
        signal_id: str,
        payload: Dict[str, Any],
        emitted_by: str,
    ) -> None:
        with self._lock:
            definition = self._definitions.get(signal_id)
            if definition is None:
                return
            if signal_id in self._paused_signals:
                return
            if not self._validate_payload(definition, payload):
                return
            self._deliver(signal_id, payload, emitted_by)

    def batch_emit(
        self,
        emissions: List[Tuple[str, Dict[str, Any], str]],
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if len(emissions) > self.MAX_BATCH_SIZE:
            return {"success": False, "error": "batch_too_large", "max_size": self.MAX_BATCH_SIZE}

        batch_id = batch_id or uuid.uuid4().hex
        delivered_total = 0
        dropped_total = 0
        errors: List[Dict[str, Any]] = []

        with self._lock:
            for signal_id, payload, emitted_by in emissions:
                definition = self._definitions.get(signal_id)
                if definition is None:
                    errors.append({"signal_id": signal_id, "error": "unknown_signal"})
                    continue
                if signal_id in self._paused_signals:
                    errors.append({"signal_id": signal_id, "error": "signal_paused"})
                    continue
                if not self._validate_payload(definition, payload):
                    errors.append({"signal_id": signal_id, "error": "payload_validation_failed"})
                    continue
                result = self._deliver(signal_id, payload, emitted_by)
                delivered_total += result.get("delivered", 0)
                dropped_total += result.get("dropped", 0)

        return {
            "success": True,
            "batch_id": batch_id,
            "signals_in_batch": len(emissions),
            "delivered": delivered_total,
            "dropped": dropped_total,
            "errors": errors,
        }

    def _deliver(
        self,
        signal_id: str,
        payload: Dict[str, Any],
        emitted_by: str,
    ) -> Dict[str, Any]:
        start = _time_module.perf_counter()

        emission = SignalEmission(
            signal_id=signal_id,
            payload=payload,
            emitted_by=emitted_by,
        )
        self._emission_history[signal_id].append(emission)
        self._total_emissions += 1

        conn_ids = list(self._signal_connections.get(signal_id, set()))
        connections: List[SignalConnection] = []
        for conn_id in conn_ids:
            conn = self._connections.get(conn_id)
            if conn is None:
                continue
            if not conn.enabled:
                continue
            connections.append(conn)

        connections.sort(key=lambda c: -c.priority)

        delivered = 0
        dropped = 0
        disconnected: List[str] = []

        for conn in connections:
            callback = self._callback_registry.get((conn.listener_id, conn.callback_name))
            if callback is None:
                dropped += 1
                continue
            try:
                callback(**payload)
                delivered += 1
                if conn.one_shot:
                    disconnected.append(conn.id)
            except Exception:
                dropped += 1

        for conn_id in disconnected:
            conn = self._connections.pop(conn_id, None)
            if conn is not None:
                self._signal_connections.get(conn.signal_id, set()).discard(conn_id)
                self._listener_connections.get(conn.listener_id, set()).discard(conn_id)

        elapsed = (_time_module.perf_counter() - start) * 1000.0
        self._total_deliveries += delivered
        self._total_drops += dropped
        self._cumulative_delivery_ms += elapsed
        self._delivery_samples += 1

        return {
            "success": True,
            "delivery": "immediate",
            "emission_id": emission.id,
            "delivered": delivered,
            "dropped": dropped,
            "delivery_ms": round(elapsed, 3),
        }

    def _validate_payload(self, definition: SignalDefinition, payload: Dict[str, Any]) -> bool:
        if not definition.parameters:
            return True
        for param in definition.parameters:
            param_name = param.get("name", "")
            param_type = param.get("type", "any")
            default = param.get("default")
            if param_name not in payload:
                if default is not None:
                    payload[param_name] = default
                else:
                    return False
            if param_type != "any":
                value = payload[param_name]
                if not self._check_type(value, param_type):
                    if default is not None:
                        payload[param_name] = default
                    else:
                        return False
        return True

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        type_map = {
            "str": str, "string": str,
            "int": int, "integer": int,
            "float": float, "number": float,
            "bool": bool, "boolean": bool,
            "list": list, "array": list,
            "dict": dict, "object": dict,
        }
        python_type = type_map.get(expected_type.lower())
        if python_type is None:
            return True
        return isinstance(value, python_type)

    # ------------------------------------------------------------------
    # Signal Pausing
    # ------------------------------------------------------------------

    def pause_signal(self, signal_id: str) -> bool:
        with self._lock:
            if signal_id in self._definitions:
                self._paused_signals.add(signal_id)
                return True
            return False

    def resume_signal(self, signal_id: str) -> bool:
        with self._lock:
            if signal_id in self._paused_signals:
                self._paused_signals.discard(signal_id)
                return True
            return False

    def is_signal_paused(self, signal_id: str) -> bool:
        with self._lock:
            return signal_id in self._paused_signals

    # ------------------------------------------------------------------
    # Namespace Management
    # ------------------------------------------------------------------

    def clear_namespace(self, namespace: str) -> Dict[str, Any]:
        with self._lock:
            signal_ids = list(self._namespace_index.get(namespace, set()))
            definitions_removed = 0
            connections_removed = 0

            for sig_id in signal_ids:
                self._definitions.pop(sig_id, None)
                definitions_removed += 1

                conn_ids = list(self._signal_connections.pop(sig_id, set()))
                for conn_id in conn_ids:
                    conn = self._connections.pop(conn_id, None)
                    if conn is not None:
                        self._listener_connections.get(conn.listener_id, set()).discard(conn_id)
                        connections_removed += 1

                self._emission_history.pop(sig_id, None)
                self._paused_signals.discard(sig_id)

            self._namespace_index.pop(namespace, None)

            return {
                "success": True,
                "namespace": namespace,
                "definitions_removed": definitions_removed,
                "connections_removed": connections_removed,
            }

    def get_namespace_signals(self, namespace: str) -> List[SignalDefinition]:
        with self._lock:
            signal_ids = self._namespace_index.get(namespace, set())
            return [self._definitions[sid] for sid in signal_ids if sid in self._definitions]

    def list_namespaces(self) -> List[str]:
        with self._lock:
            return sorted(self._namespace_index.keys())

    # ------------------------------------------------------------------
    # Signal History
    # ------------------------------------------------------------------

    def get_emission_history(self, signal_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            history = self._emission_history.get(signal_id)
            if history is None:
                return []
            items = list(history)[-limit:]
            return [e.to_dict() for e in items]

    # ------------------------------------------------------------------
    # Bus Statistics
    # ------------------------------------------------------------------

    def get_signal_bus_stats(self) -> Dict[str, Any]:
        with self._lock:
            namespace_counts: Dict[str, int] = {}
            for ns, sig_ids in self._namespace_index.items():
                namespace_counts[ns] = len(sig_ids)

            category_counts: Dict[str, int] = {}
            for definition in self._definitions.values():
                cat = definition.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1

            avg_delivery_ms = (
                round(self._cumulative_delivery_ms / self._delivery_samples, 3)
                if self._delivery_samples > 0
                else 0.0
            )

            active_connections = sum(
                1 for conn in self._connections.values() if conn.enabled
            )
            one_shot_connections = sum(
                1 for conn in self._connections.values() if conn.one_shot and conn.enabled
            )

            return {
                "total_definitions": len(self._definitions),
                "total_connections": len(self._connections),
                "active_connections": active_connections,
                "one_shot_connections": one_shot_connections,
                "total_listeners": len(self._listener_connections),
                "unique_namespaces": len(self._namespace_index),
                "namespace_distribution": namespace_counts,
                "category_distribution": category_counts,
                "total_emissions": self._total_emissions,
                "total_deliveries": self._total_deliveries,
                "total_drops": self._total_drops,
                "avg_delivery_ms": avg_delivery_ms,
                "delivery_samples": self._delivery_samples,
                "paused_signals": len(self._paused_signals),
                "max_history_per_signal": self.MAX_HISTORY_PER_SIGNAL,
                "max_connections_per_signal": self.MAX_CONNECTIONS_PER_SIGNAL,
                "max_batch_size": self.MAX_BATCH_SIZE,
            }

    def get_bus_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "version": "1.0",
                "definitions": len(self._definitions),
                "listeners": len(self._listener_connections),
                "connections": len(self._connections),
                "namespaces": len(self._namespace_index),
                "total_emissions": self._total_emissions,
                "total_deliveries": self._total_deliveries,
                "total_drops": self._total_drops,
            }

    # ------------------------------------------------------------------
    # Bus Lifecycle
    # ------------------------------------------------------------------

    def clear_bus(self) -> Dict[str, Any]:
        with self._lock:
            def_count = len(self._definitions)
            conn_count = len(self._connections)
            listener_count = len(self._listener_connections)

            self._definitions.clear()
            self._connections.clear()
            self._emission_history.clear()
            self._callback_registry.clear()
            self._listener_connections.clear()
            self._signal_connections.clear()
            self._namespace_index.clear()
            self._batches.clear()
            self._paused_signals.clear()

            self._total_emissions = 0
            self._total_deliveries = 0
            self._total_drops = 0
            self._cumulative_delivery_ms = 0.0
            self._delivery_samples = 0

            return {
                "success": True,
                "definitions_cleared": def_count,
                "connections_cleared": conn_count,
                "listeners_cleared": listener_count,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive SignalBus subsystem statistics."""
        return {
            "total_definitions": len(self._definitions),
            "total_connections": len(self._connections),
            "total_listeners": sum(len(c.listeners) for c in self._connections.values()),
            "total_emissions": self._delivery_samples if hasattr(self, '_delivery_samples') else 0,
            "definitions_by_category": {
                d.category.value: d.name for d in self._definitions.values()
            } if self._definitions else {},
        }


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_signal_bus() -> SignalBus:
    return SignalBus.get_instance()