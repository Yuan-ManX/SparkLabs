"""
SparkLabs Engine - Signal System

Observer pattern implementation for decoupled game communication.
Enables nodes, components, and AI agents to communicate through
typed signals without direct references. Supports connecting any
callable to any signal, parameter passing, deferred emission, and
one-shot connections that auto-disconnect after first invocation.

Architecture:
  SignalBus
    |-- SignalConnection (tracked connection between signal and slot)
    |-- SignalGroup (related signals grouped by owner)
    |-- EmissionMode (IMMEDIATE, DEFERRED, QUEUED)

Connection Types:
  - PERSISTENT: stays connected until manually disconnected
  - ONE_SHOT: auto-disconnects after first emission
  - CONDITIONAL: emits only when condition function returns True
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ConnectionType(Enum):
    PERSISTENT = "persistent"
    ONE_SHOT = "one_shot"
    CONDITIONAL = "conditional"


class EmissionMode(Enum):
    IMMEDIATE = "immediate"
    DEFERRED = "deferred"


@dataclass
class SignalConnection:
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    signal_name: str = ""
    callback: Callable = lambda *args, **kwargs: None
    owner_id: str = ""
    connection_type: ConnectionType = ConnectionType.PERSISTENT
    condition: Optional[Callable[[], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_emit(self) -> bool:
        if self.connection_type == ConnectionType.CONDITIONAL and self.condition:
            return self.condition()
        return True

    def is_alive(self) -> bool:
        return self.connection_type != ConnectionType.ONE_SHOT


class SignalBus:
    """
    Decoupled signal/slot communication bus.

    Manages typed signal connections between game objects.
    Any node, component, or agent can emit signals and any
    other can listen without owning references to each other.

    Usage:
        bus = SignalBus()
        cid = bus.connect(owner, "health_changed", on_health_changed)
        bus.emit(owner, "health_changed", old=50, new=30)
        bus.disconnect(cid)
    """

    def __init__(self):
        self._connections: Dict[str, SignalConnection] = {}
        self._signal_index: Dict[str, Set[str]] = {}
        self._owner_index: Dict[str, Set[str]] = {}
        self._deferred_queue: List[Tuple[str, Tuple, Dict]] = []
        self._global_listeners: Set[str] = set()

    def connect(
        self,
        signal_name: str,
        callback: Callable,
        owner_id: str = "__anonymous__",
        connection_type: ConnectionType = ConnectionType.PERSISTENT,
        condition: Optional[Callable[[], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        conn = SignalConnection(
            signal_name=signal_name,
            callback=callback,
            owner_id=owner_id,
            connection_type=connection_type,
            condition=condition,
            metadata=metadata or {},
        )
        self._connections[conn.connection_id] = conn

        key = f"{owner_id}:{signal_name}"
        self._signal_index.setdefault(key, set()).add(conn.connection_id)
        self._owner_index.setdefault(owner_id, set()).add(conn.connection_id)

        return conn.connection_id

    def connect_global(
        self,
        signal_name: str,
        callback: Callable,
    ) -> str:
        conn = SignalConnection(
            signal_name=signal_name,
            callback=callback,
            owner_id="__global__",
        )
        self._connections[conn.connection_id] = conn
        self._global_listeners.add(conn.connection_id)
        key = f"__any__:{signal_name}"
        self._signal_index.setdefault(key, set()).add(conn.connection_id)
        return conn.connection_id

    def disconnect(self, connection_id: str) -> bool:
        conn = self._connections.pop(connection_id, None)
        if not conn:
            return False
        key = f"{conn.owner_id}:{conn.signal_name}"
        if key in self._signal_index:
            self._signal_index[key].discard(connection_id)
        self._owner_index.get(conn.owner_id, set()).discard(connection_id)
        self._global_listeners.discard(connection_id)
        return True

    def disconnect_all(self, owner_id: str) -> int:
        cids = list(self._owner_index.get(owner_id, set()))
        count = 0
        for cid in cids:
            if self.disconnect(cid):
                count += 1
        return count

    def emit(
        self, signal_name: str, *args: Any, owner_id: str = "__anonymous__",
        mode: EmissionMode = EmissionMode.IMMEDIATE, **kwargs: Any
    ) -> int:
        if mode == EmissionMode.DEFERRED:
            self._deferred_queue.append((f"{owner_id}:{signal_name}", args, kwargs))
            return 0

        cids = self._get_listeners(owner_id, signal_name)
        dead_connections: List[str] = []

        for cid in cids:
            conn = self._connections.get(cid)
            if not conn:
                continue
            if not conn.can_emit():
                continue
            try:
                conn.callback(*args, **kwargs)
            except Exception:
                pass
            if conn.connection_type == ConnectionType.ONE_SHOT:
                dead_connections.append(cid)

        for cid in dead_connections:
            self.disconnect(cid)

        return len(cids)

    def flush_deferred(self) -> int:
        queue = self._deferred_queue[:]
        self._deferred_queue.clear()
        count = 0
        for key, args, kwargs in queue:
            parts = key.split(":", 1)
            if len(parts) == 2:
                owner_id, signal_name = parts
                self.emit(owner_id, signal_name, *args, **kwargs)
                count += 1
        return count

    def _get_listeners(self, owner_id: str, signal_name: str) -> Set[str]:
        cids: Set[str] = set()
        key = f"{owner_id}:{signal_name}"
        cids.update(self._signal_index.get(key, set()))
        global_key = f"__any__:{signal_name}"
        cids.update(self._signal_index.get(global_key, set()))
        return cids

    def get_connection_count(self) -> int:
        return len(self._connections)

    def get_connection(self, connection_id: str) -> Optional[SignalConnection]:
        return self._connections.get(connection_id)

    def has_listeners(self, owner_id: str, signal_name: str) -> bool:
        return len(self._get_listeners(owner_id, signal_name)) > 0

    def clear_deferred(self) -> None:
        self._deferred_queue.clear()

    def clear(self) -> None:
        self._connections.clear()
        self._signal_index.clear()
        self._owner_index.clear()
        self._global_listeners.clear()
        self._deferred_queue.clear()


_global_signal_bus: Optional[SignalBus] = None


def get_signal_bus() -> SignalBus:
    global _global_signal_bus
    if _global_signal_bus is None:
        _global_signal_bus = SignalBus()
    return _global_signal_bus
