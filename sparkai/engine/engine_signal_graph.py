"""
SparkLabs Engine - Signal Graph

First-class signal/event graph system with introspectable connections.
Provides a structured graph representation of signal sources, targets, and
the connections that bind them. The graph is fully introspectable so that
tooling (editors, LLM agents, debuggers) can query the topology of signal
flow without inspecting individual participant internals.

Architecture:
  SignalGraph (Singleton)
    |-- SignalNode        (a participant that may emit or receive signals)
    |-- SignalConnection  (a directed link between a source and a target)
    |-- SignalGraphSnapshot (immutable snapshot of the entire graph)

Lifecycle:
  1. register_node(node_id, node_name, signals) -> SignalNode
  2. connect(source, signal, target, callback) -> SignalConnection
  3. emit(source, signal, args) -> int (number of listeners notified)
  4. disconnect(connection_id) -> bool
  5. get_snapshot() -> SignalGraphSnapshot
  6. reset() -> None

Usage:
    graph = get_signal_graph()
    graph.register_node("player", "Player", ["moved", "damaged"])
    graph.register_node("hud", "HUD", [])
    graph.connect("player", "damaged", "hud", "on_player_damaged")
    graph.emit("player", "damaged", {"amount": 25})
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SignalConnection:
    """A directed connection between a source node and a target node.

    Attributes:
        connection_id: Unique identifier (auto-generated).
        signal_name: The name of the signal being routed.
        source_node: Identifier of the emitting node.
        target_node: Identifier of the receiving node.
        callback_name: Name of the callback invoked on the target.
        is_active: Whether this connection is currently active.
        call_count: Number of times this connection has been invoked.
    """
    connection_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    signal_name: str = ""
    source_node: str = ""
    target_node: str = ""
    callback_name: str = ""
    is_active: bool = True
    call_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "signal_name": self.signal_name,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "callback_name": self.callback_name,
            "is_active": self.is_active,
            "call_count": self.call_count,
        }


@dataclass
class SignalNode:
    """A participant in the signal graph that may emit or receive signals.

    Attributes:
        node_id: Unique identifier for the node.
        node_name: Human-readable name of the node.
        signals: List of signal names this node can emit.
        connections: List of connections originating from or arriving at this node.
    """
    node_id: str = ""
    node_name: str = ""
    signals: List[str] = field(default_factory=list)
    connections: List[SignalConnection] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "signals": list(self.signals),
            "connections": [c.to_dict() for c in self.connections],
        }


@dataclass
class SignalGraphSnapshot:
    """Immutable snapshot of the signal graph state at a point in time.

    Attributes:
        graph_id: Identifier of the graph (auto-generated at snapshot time).
        nodes: List of all nodes captured in the snapshot.
        connections: List of all connections captured in the snapshot.
        total_signals: Total number of distinct signals across all nodes.
        total_connections: Total number of connections in the graph.
        timestamp: Time the snapshot was taken.
    """
    graph_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    nodes: List[SignalNode] = field(default_factory=list)
    connections: List[SignalConnection] = field(default_factory=list)
    total_signals: int = 0
    total_connections: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "connections": [c.to_dict() for c in self.connections],
            "total_signals": self.total_signals,
            "total_connections": self.total_connections,
            "timestamp": self.timestamp,
        }


# =============================================================================
# Signal Graph (Singleton)
# =============================================================================


class SignalGraph:
    """Singleton signal/event graph with introspectable connections.

    Maintains a registry of signal-emitting nodes and the directed
    connections between them. The graph supports emitting signals to all
    connected listeners and provides rich introspection of the topology.
    All public methods are thread-safe.

    Typical usage::

        graph = SignalGraph.get_instance()
        graph.register_node("player", "Player", ["damaged"])
        graph.connect("player", "damaged", "hud", "on_player_damaged")
        graph.emit("player", "damaged", {"amount": 25})
    """

    _instance: Optional["SignalGraph"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "SignalGraph":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._nodes: Dict[str, SignalNode] = {}
        self._connections: Dict[str, SignalConnection] = {}
        # Indexes for fast lookup.
        self._signal_connections: Dict[str, List[str]] = {}
        self._callbacks: Dict[str, Callable[..., Any]] = {}
        self._total_emissions: int = 0
        self._total_deliveries: int = 0

    @classmethod
    def get_instance(cls) -> "SignalGraph":
        """Return the singleton SignalGraph instance (thread-safe)."""
        return cls()

    # ------------------------------------------------------------------
    # Node Management
    # ------------------------------------------------------------------

    def register_node(
        self,
        node_id: str,
        node_name: str = "",
        signals: Optional[List[str]] = None,
    ) -> SignalNode:
        """Register a node in the signal graph.

        If a node with the given id already exists, it is updated with the
        provided name and any additional signals.

        Args:
            node_id: Unique identifier for the node.
            node_name: Human-readable name of the node.
            signals: List of signal names this node can emit.

        Returns:
            The registered (or updated) SignalNode.
        """
        with self._instance_lock:
            node = self._nodes.get(node_id)
            if node is None:
                node = SignalNode(
                    node_id=node_id,
                    node_name=node_name or node_id,
                    signals=list(signals) if signals else [],
                )
                self._nodes[node_id] = node
            else:
                if node_name:
                    node.node_name = node_name
                if signals:
                    for sig in signals:
                        if sig not in node.signals:
                            node.signals.append(sig)
            return node

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------

    def connect(
        self,
        source: str,
        signal: str,
        target: str,
        callback: Any,
        callback_name: str = "",
    ) -> SignalConnection:
        """Create a directed connection between two nodes for a signal.

        Args:
            source: Identifier of the emitting node.
            signal: Name of the signal to route.
            target: Identifier of the receiving node.
            callback: Callable invoked when the signal is emitted. May also
                be a string name; in that case it is treated as the callback
                name and no runtime callback is registered.
            callback_name: Optional name of the callback. If omitted, the
                callback's ``__name__`` is used when available.

        Returns:
            The created SignalConnection.
        """
        if callback_name == "":
            if callable(callback):
                callback_name = getattr(callback, "__name__", "callback")
            else:
                callback_name = str(callback)

        with self._instance_lock:
            # Ensure both endpoints exist as nodes.
            if source not in self._nodes:
                self.register_node(source, source, [signal])
            else:
                if signal not in self._nodes[source].signals:
                    self._nodes[source].signals.append(signal)
            if target not in self._nodes:
                self.register_node(target, target)

            connection = SignalConnection(
                signal_name=signal,
                source_node=source,
                target_node=target,
                callback_name=callback_name,
            )
            self._connections[connection.connection_id] = connection
            self._signal_connections.setdefault(signal, []).append(
                connection.connection_id
            )
            # Track the connection on both endpoints.
            self._nodes[source].connections.append(connection)
            self._nodes[target].connections.append(connection)
            if callable(callback):
                self._callbacks[connection.connection_id] = callback
            return connection

    def disconnect(self, connection_id: str) -> bool:
        """Remove a connection from the graph.

        Args:
            connection_id: Identifier of the connection to remove.

        Returns:
            True if the connection was removed, False if not found.
        """
        with self._instance_lock:
            connection = self._connections.pop(connection_id, None)
            if connection is None:
                return False
            signal = connection.signal_name
            ids = self._signal_connections.get(signal, [])
            if connection_id in ids:
                ids.remove(connection_id)
            if not ids:
                self._signal_connections.pop(signal, None)
            source = self._nodes.get(connection.source_node)
            if source is not None:
                source.connections = [
                    c for c in source.connections if c.connection_id != connection_id
                ]
            target = self._nodes.get(connection.target_node)
            if target is not None:
                target.connections = [
                    c for c in target.connections if c.connection_id != connection_id
                ]
            self._callbacks.pop(connection_id, None)
            return True

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------

    def emit(
        self,
        source: str,
        signal: str,
        args: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Emit a signal from a source node to all connected listeners.

        Args:
            source: Identifier of the emitting node.
            signal: Name of the signal to emit.
            args: Optional payload passed to each listener callback.

        Returns:
            The number of listeners that were notified.
        """
        payload = args or {}
        with self._instance_lock:
            conn_ids = list(self._signal_connections.get(signal, []))
            notified = 0
            self._total_emissions += 1
            for conn_id in conn_ids:
                connection = self._connections.get(conn_id)
                if connection is None or not connection.is_active:
                    continue
                callback = self._callbacks.get(conn_id)
                if callback is None:
                    # No runtime callback registered; still count as a routed
                    # connection so introspection remains consistent.
                    connection.call_count += 1
                    notified += 1
                    continue
                try:
                    callback(**payload)
                    connection.call_count += 1
                    notified += 1
                except Exception:
                    # A failing listener must not prevent other deliveries.
                    pass
            self._total_deliveries += notified
            return notified

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_connections_for(self, signal_name: str) -> List[SignalConnection]:
        """Return all connections registered for the given signal name."""
        with self._instance_lock:
            ids = self._signal_connections.get(signal_name, [])
            return [
                self._connections[cid]
                for cid in ids
                if cid in self._connections
            ]

    def get_node_signals(self, node_id: str) -> List[str]:
        """Return the list of signal names a node can emit."""
        with self._instance_lock:
            node = self._nodes.get(node_id)
            if node is None:
                return []
            return list(node.signals)

    def get_node(self, node_id: str) -> Optional[SignalNode]:
        """Return the node with the given id, if registered."""
        with self._instance_lock:
            return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[SignalNode]:
        """Return a copy of all registered nodes."""
        with self._instance_lock:
            return list(self._nodes.values())

    # ------------------------------------------------------------------
    # Status and Snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current graph state."""
        with self._instance_lock:
            active_connections = sum(
                1 for c in self._connections.values() if c.is_active
            )
            distinct_signals = set()
            for node in self._nodes.values():
                distinct_signals.update(node.signals)
            return {
                "total_nodes": len(self._nodes),
                "total_connections": len(self._connections),
                "active_connections": active_connections,
                "distinct_signals": len(distinct_signals),
                "total_emissions": self._total_emissions,
                "total_deliveries": self._total_deliveries,
            }

    def get_snapshot(self) -> SignalGraphSnapshot:
        """Capture an immutable snapshot of the entire graph."""
        with self._instance_lock:
            nodes = [self._clone_node(n) for n in self._nodes.values()]
            connections = [
                SignalConnection(
                    connection_id=c.connection_id,
                    signal_name=c.signal_name,
                    source_node=c.source_node,
                    target_node=c.target_node,
                    callback_name=c.callback_name,
                    is_active=c.is_active,
                    call_count=c.call_count,
                )
                for c in self._connections.values()
            ]
            distinct_signals = set()
            for node in self._nodes.values():
                distinct_signals.update(node.signals)
            return SignalGraphSnapshot(
                nodes=nodes,
                connections=connections,
                total_signals=len(distinct_signals),
                total_connections=len(connections),
                timestamp=time.time(),
            )

    @staticmethod
    def _clone_node(node: SignalNode) -> SignalNode:
        return SignalNode(
            node_id=node.node_id,
            node_name=node.node_name,
            signals=list(node.signals),
            connections=[
                SignalConnection(
                    connection_id=c.connection_id,
                    signal_name=c.signal_name,
                    source_node=c.source_node,
                    target_node=c.target_node,
                    callback_name=c.callback_name,
                    is_active=c.is_active,
                    call_count=c.call_count,
                )
                for c in node.connections
            ],
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all nodes, connections, and statistics."""
        with self._instance_lock:
            self._nodes.clear()
            self._connections.clear()
            self._signal_connections.clear()
            self._callbacks.clear()
            self._total_emissions = 0
            self._total_deliveries = 0


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_signal_graph() -> SignalGraph:
    """Return the singleton SignalGraph instance."""
    return SignalGraph.get_instance()
