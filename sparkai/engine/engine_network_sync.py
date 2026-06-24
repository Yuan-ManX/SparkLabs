"""
SparkLabs Engine - Network State Synchronization Engine

AI-optimized network state synchronization for multiplayer game state
management. Provides full-state and delta-based entity synchronization,
connection lifecycle management, snapshot-based state history, and
multi-authority session orchestration across server, client, and
peer-to-peer topologies.

Architecture:
  NetworkSyncEngine (Singleton)
    |-- NetworkEntity         — synchronized game entity with ownership and channels
    |-- SyncMessage           — network message with priority, sequence, and ack
    |-- ConnectionInfo        — per-peer connection metadata and health
    |-- SyncSnapshot          — point-in-time capture of entity state
    |-- SyncSession           — managed sync session with authority and strategy
    |-- SyncAuthority (enum)  — state ownership model for the session
    |-- SyncStrategy (enum)   — replication strategy between peers
    |-- ConnectionState (enum) — connection lifecycle state machine
    |-- SyncChannel (enum)    — data channel classification
    |-- MessagePriority (enum) — message urgency tiers

Core Capabilities:
  - create_session: Create a sync session with authority and strategy
  - connect: Establish a peer connection with latency/packet-loss tracking
  - register_entity: Register a game entity for network synchronization
  - sync_state: Transmit entity state through a sync channel
  - get_snapshot: Retrieve a point-in-time state snapshot for an entity
  - get_connections: List all active connections for a session
  - get_stats: Global engine statistics and health summary
"""

from __future__ import annotations

import json
import random
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SyncAuthority(Enum):
    """State ownership model for the network session."""
    SERVER = "server"
    CLIENT = "client"
    PEER_TO_PEER = "peer_to_peer"
    HYBRID = "hybrid"


class SyncStrategy(Enum):
    """Replication strategy between peers."""
    FULL_STATE = "full_state"
    DELTA = "delta"
    INTERPOLATION = "interpolation"
    EXTRAPOLATION = "extrapolation"
    PREDICTION = "prediction"


class ConnectionState(Enum):
    """Connection lifecycle state machine."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    TIMEOUT = "timeout"


class SyncChannel(Enum):
    """Data channel classification for network messages."""
    POSITION = "position"
    ANIMATION = "animation"
    PHYSICS = "physics"
    INPUT = "input"
    EVENTS = "events"
    CHAT = "chat"
    CUSTOM = "custom"


class MessagePriority(Enum):
    """Message urgency tiers for transmission ordering."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class NetworkEntity:
    """A synchronized game entity with ownership and channel configuration.

    Attributes:
        id: Unique entity identifier.
        entity_type: Semantic classification of the entity (e.g., "player", "npc").
        owner_id: Peer that owns and is authoritative for this entity.
        sync_channels: Set of channels this entity synchronizes on.
        last_sync: ISO-8601 timestamp of the most recent sync.
        priority: Transmission priority for this entity's messages.
        metadata: Arbitrary key-value data attached to the entity.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_type: str = ""
    owner_id: str = ""
    sync_channels: List[SyncChannel] = field(default_factory=list)
    last_sync: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "owner_id": self.owner_id,
            "sync_channels": [ch.value for ch in self.sync_channels],
            "last_sync": self.last_sync,
            "priority": self.priority.value,
            "metadata": self.metadata,
        }


@dataclass
class SyncMessage:
    """A network message with priority, sequence tracking, and acknowledgment.

    Attributes:
        id: Unique message identifier.
        channel: Data channel this message belongs to.
        sender_id: Peer that originated this message.
        entity_id: Entity this message is associated with.
        data: Serialized payload of the message.
        priority: Urgency tier for transmission ordering.
        sequence: Monotonically increasing sequence number.
        timestamp: ISO-8601 creation timestamp.
        ack_required: Whether the receiver must acknowledge this message.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    channel: SyncChannel = SyncChannel.CUSTOM
    sender_id: str = ""
    entity_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    sequence: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    ack_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "channel": self.channel.value,
            "sender_id": self.sender_id,
            "entity_id": self.entity_id,
            "data": self.data,
            "priority": self.priority.value,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "ack_required": self.ack_required,
        }


@dataclass
class ConnectionInfo:
    """Per-peer connection metadata and health tracking.

    Attributes:
        id: Unique connection identifier.
        address: Network address of the peer (e.g., "192.168.1.100:9000").
        latency_ms: Measured round-trip latency in milliseconds.
        packet_loss: Fraction of packets lost (0.0 to 1.0).
        bandwidth: Estimated available bandwidth in bytes per second.
        state: Current connection lifecycle state.
        connected_at: ISO-8601 timestamp when connection was established.
        last_heartbeat: ISO-8601 timestamp of last received heartbeat.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    address: str = "127.0.0.1:9000"
    latency_ms: float = 0.0
    packet_loss: float = 0.0
    bandwidth: float = 0.0
    state: ConnectionState = ConnectionState.DISCONNECTED
    connected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "address": self.address,
            "latency_ms": round(self.latency_ms, 1),
            "packet_loss": round(self.packet_loss, 3),
            "bandwidth": round(self.bandwidth, 1),
            "state": self.state.value,
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
        }


@dataclass
class SyncSnapshot:
    """A point-in-time capture of entity state for replay and interpolation.

    Attributes:
        id: Unique snapshot identifier.
        entity_id: Entity this snapshot belongs to.
        full_state: Complete entity state dict at this point in time.
        delta: Changed properties since the previous snapshot, if any.
        timestamp: ISO-8601 capture timestamp.
        version: Monotonically increasing snapshot version number.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    full_state: Dict[str, Any] = field(default_factory=dict)
    delta: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "full_state": self.full_state,
            "delta": self.delta,
            "timestamp": self.timestamp,
            "version": self.version,
        }


@dataclass
class SyncSession:
    """A managed sync session with authority, strategy, and entity tracking.

    Attributes:
        id: Unique session identifier.
        authority: State ownership model (server, client, peer-to-peer, hybrid).
        strategy: Replication strategy (full_state, delta, interpolation, etc.).
        connections: Set of connection IDs participating in this session.
        entities: Set of entity IDs registered in this session.
        tick_rate: Sync ticks per second.
        started_at: ISO-8601 timestamp when the session was created.
        stats: Session-level aggregate statistics.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    authority: SyncAuthority = SyncAuthority.SERVER
    strategy: SyncStrategy = SyncStrategy.FULL_STATE
    connections: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    tick_rate: int = 30
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "authority": self.authority.value,
            "strategy": self.strategy.value,
            "connections": list(self.connections),
            "entities": list(self.entities),
            "tick_rate": self.tick_rate,
            "started_at": self.started_at,
            "stats": self.stats,
        }


# ---------------------------------------------------------------------------
# NetworkSyncEngine — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class NetworkSyncEngine:
    """AI-optimized network state synchronization engine for multiplayer
    game state management.

    Manages sync sessions with configurable authority and strategy,
    peer connections with health monitoring, entity registration and
    state synchronization across multiple channels, snapshot-based
    state history, and priority-ordered message transmission with
    sequencing and acknowledgment tracking.

    Thread-safe via a reentrant lock. Use get_network_sync() or
    NetworkSyncEngine.get_instance() to obtain the singleton.

    Usage:
        engine = get_network_sync()
        session = engine.create_session(SyncAuthority.SERVER, SyncStrategy.DELTA, 30)
        conn = engine.connect(session.id, "192.168.1.100:9000")
        entity = engine.register_entity(session.id, "player", conn.id, [SyncChannel.POSITION])
        msg = engine.sync_state(session.id, entity.id, {"x": 100, "y": 200}, SyncChannel.POSITION)
    """

    _instance: Optional["NetworkSyncEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SNAPSHOTS_PER_ENTITY: int = 120
    MAX_MESSAGES_PER_SESSION: int = 10000

    def __new__(cls) -> "NetworkSyncEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._sessions: Dict[str, SyncSession] = {}
        self._connections: Dict[str, ConnectionInfo] = {}
        self._session_connections: Dict[str, List[str]] = defaultdict(list)
        self._entities: Dict[str, NetworkEntity] = {}
        self._session_entities: Dict[str, List[str]] = defaultdict(list)
        self._entity_states: Dict[str, Dict[str, Any]] = {}
        self._entity_snapshots: Dict[str, List[SyncSnapshot]] = defaultdict(list)
        self._entity_versions: Dict[str, int] = defaultdict(int)
        self._messages: Dict[str, List[SyncMessage]] = defaultdict(list)
        self._sequence_counters: Dict[str, int] = defaultdict(int)
        self._total_sessions: int = 0
        self._total_connections: int = 0
        self._total_entities: int = 0
        self._total_messages: int = 0
        self._total_snapshots: int = 0

    @classmethod
    def get_instance(cls) -> "NetworkSyncEngine":
        return cls()

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _get_session(self, session_id: str) -> SyncSession:
        """Retrieve a session by id, raising KeyError if not found."""
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")
        return self._sessions[session_id]

    def _get_connection(self, connection_id: str) -> ConnectionInfo:
        """Retrieve a connection by id, raising KeyError if not found."""
        if connection_id not in self._connections:
            raise KeyError(f"Connection not found: {connection_id}")
        return self._connections[connection_id]

    def _get_entity(self, entity_id: str) -> NetworkEntity:
        """Retrieve an entity by id, raising KeyError if not found."""
        if entity_id not in self._entities:
            raise KeyError(f"Entity not found: {entity_id}")
        return self._entities[entity_id]

    def _next_sequence(self, session_id: str) -> int:
        """Increment and return the next sequence number for a session."""
        seq = self._sequence_counters.get(session_id, 0) + 1
        self._sequence_counters[session_id] = seq
        return seq

    def _compute_delta(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute the difference between two entity state dicts.

        Returns a dict containing only properties that have changed.
        If nothing changed, returns an empty dict.
        """
        delta: Dict[str, Any] = {}
        for key, value in current.items():
            if key not in previous or previous[key] != value:
                delta[key] = value
        return delta

    def _simulate_latency(self) -> float:
        """Simulate a realistic network latency in milliseconds."""
        return random.uniform(5.0, 80.0)

    def _simulate_packet_loss(self) -> float:
        """Simulate a realistic packet loss rate (0.0 to 0.05)."""
        return random.uniform(0.0, 0.03)

    # -----------------------------------------------------------------------
    # Session Management
    # -----------------------------------------------------------------------

    def create_session(
        self,
        authority: SyncAuthority = SyncAuthority.SERVER,
        strategy: SyncStrategy = SyncStrategy.FULL_STATE,
        tick_rate: int = 30,
    ) -> SyncSession:
        """Create a new sync session with the specified authority and strategy.

        Args:
            authority: State ownership model for the session.
            strategy: Replication strategy between peers.
            tick_rate: Sync ticks per second.

        Returns:
            The newly created SyncSession.
        """
        session = SyncSession(
            authority=authority,
            strategy=strategy,
            tick_rate=max(1, tick_rate),
        )
        with self._lock:
            self._sessions[session.id] = session
            self._session_connections[session.id] = []
            self._session_entities[session.id] = []
            self._total_sessions += 1
        return session

    def get_session(self, session_id: str) -> Optional[SyncSession]:
        """Retrieve a session by its identifier, or None if not found."""
        return self._sessions.get(session_id)

    # -----------------------------------------------------------------------
    # Connection Management
    # -----------------------------------------------------------------------

    def connect(self, session_id: str, address: str) -> ConnectionInfo:
        """Establish a peer connection to a session.

        Simulates connection handshake including latency measurement
        and packet loss estimation. Adds the connection to the session's
        active connection list.

        Args:
            session_id: Target session identifier.
            address: Network address of the connecting peer.

        Returns:
            The ConnectionInfo instance.

        Raises:
            KeyError: If the session does not exist.
        """
        self._get_session(session_id)
        with self._lock:
            connection = ConnectionInfo(
                address=address,
                state=ConnectionState.CONNECTING,
            )
            # Simulate connection handshake
            connection.latency_ms = self._simulate_latency()
            connection.packet_loss = self._simulate_packet_loss()
            connection.bandwidth = random.uniform(1_000_000.0, 50_000_000.0)
            connection.state = ConnectionState.CONNECTED
            connection.last_heartbeat = datetime.utcnow().isoformat()

            self._connections[connection.id] = connection
            self._session_connections[session_id].append(connection.id)
            self._total_connections += 1

            # Update session stats
            session = self._sessions[session_id]
            session.connections = list(self._session_connections[session_id])
            session.stats["connection_count"] = len(session.connections)
        return connection

    def disconnect(self, connection_id: str) -> ConnectionInfo:
        """Disconnect a peer from all sessions.

        Sets the connection state to DISCONNECTED and removes it from
        session connection lists.

        Args:
            connection_id: Connection to disconnect.

        Returns:
            The updated ConnectionInfo.

        Raises:
            KeyError: If the connection does not exist.
        """
        connection = self._get_connection(connection_id)
        with self._lock:
            connection.state = ConnectionState.DISCONNECTED
            connection.last_heartbeat = datetime.utcnow().isoformat()
            # Remove from all session connection lists
            for session_id, conn_ids in self._session_connections.items():
                if connection_id in conn_ids:
                    conn_ids.remove(connection_id)
                    session = self._sessions.get(session_id)
                    if session:
                        session.connections = list(conn_ids)
                        session.stats["connection_count"] = len(conn_ids)
        return connection

    def get_connections(self, session_id: str) -> List[ConnectionInfo]:
        """List all active connections for a session.

        Args:
            session_id: Session to query connections for.

        Returns:
            List of ConnectionInfo for all connections in the session.

        Raises:
            KeyError: If the session does not exist.
        """
        self._get_session(session_id)
        conn_ids = self._session_connections.get(session_id, [])
        return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    # -----------------------------------------------------------------------
    # Entity Management
    # -----------------------------------------------------------------------

    def register_entity(
        self,
        session_id: str,
        entity_type: str,
        owner_id: str,
        sync_channels: Optional[List[SyncChannel]] = None,
    ) -> NetworkEntity:
        """Register a game entity for network synchronization within a session.

        Args:
            session_id: Session the entity belongs to.
            entity_type: Semantic classification of the entity.
            owner_id: Connection ID of the authoritative owner.
            sync_channels: Data channels to synchronize on (defaults to all).

        Returns:
            The newly created NetworkEntity.

        Raises:
            KeyError: If the session does not exist.
        """
        self._get_session(session_id)
        if sync_channels is None:
            sync_channels = list(SyncChannel)

        with self._lock:
            entity = NetworkEntity(
                entity_type=entity_type,
                owner_id=owner_id,
                sync_channels=sync_channels,
            )
            self._entities[entity.id] = entity
            self._session_entities[session_id].append(entity.id)
            self._entity_states[entity.id] = {}
            self._entity_versions[entity.id] = 0
            self._total_entities += 1

            # Update session entity list
            session = self._sessions[session_id]
            session.entities = list(self._session_entities[session_id])
            session.stats["entity_count"] = len(session.entities)
        return entity

    def get_entity(self, entity_id: str) -> Optional[NetworkEntity]:
        """Retrieve an entity by its identifier, or None if not found."""
        return self._entities.get(entity_id)

    # -----------------------------------------------------------------------
    # State Synchronization
    # -----------------------------------------------------------------------

    def sync_state(
        self,
        session_id: str,
        entity_id: str,
        data: Dict[str, Any],
        channel: SyncChannel = SyncChannel.CUSTOM,
    ) -> SyncMessage:
        """Transmit entity state data through a sync channel.

        Updates the entity's internal state, computes a delta if the
        session uses delta-based sync, creates a snapshot of the new
        state, and returns a sequenced SyncMessage for transmission.

        Args:
            session_id: Session the entity belongs to.
            entity_id: Entity to synchronize.
            data: State data to transmit.
            channel: Data channel to use for this sync.

        Returns:
            The SyncMessage queued for transmission.

        Raises:
            KeyError: If the session or entity does not exist.
        """
        session = self._get_session(session_id)
        entity = self._get_entity(entity_id)

        with self._lock:
            seq = self._next_sequence(session_id)

            # Capture previous state for delta computation
            previous_state = dict(self._entity_states.get(entity_id, {}))

            if entity_id in self._entity_states:
                self._entity_states[entity_id].update(data)
            else:
                self._entity_states[entity_id] = dict(data)

            current_state = dict(self._entity_states[entity_id])

            # Compute delta for delta-based sync strategies
            delta: Dict[str, Any] = {}
            if session.strategy == SyncStrategy.DELTA and previous_state:
                delta = self._compute_delta(previous_state, current_state)

            # Create snapshot
            version = self._entity_versions.get(entity_id, 0) + 1
            self._entity_versions[entity_id] = version

            snapshot = SyncSnapshot(
                entity_id=entity_id,
                full_state=current_state,
                delta=delta,
                version=version,
            )

            # Manage snapshot history size
            snapshots = self._entity_snapshots[entity_id]
            snapshots.append(snapshot)
            if len(snapshots) > self.MAX_SNAPSHOTS_PER_ENTITY:
                snapshots.pop(0)
            self._total_snapshots += 1

            # Update entity metadata
            entity.last_sync = datetime.utcnow().isoformat()

            # Create sync message
            payload = (
                delta if (session.strategy == SyncStrategy.DELTA and delta)
                else current_state
            )

            message = SyncMessage(
                channel=channel,
                sender_id=entity.owner_id,
                entity_id=entity_id,
                data=payload,
                priority=entity.priority,
                sequence=seq,
                ack_required=True,
            )

            self._messages[session_id].append(message)
            if len(self._messages[session_id]) > self.MAX_MESSAGES_PER_SESSION:
                self._messages[session_id] = self._messages[session_id][
                    -self.MAX_MESSAGES_PER_SESSION:
                ]
            self._total_messages += 1

            # Update session stats
            session.stats["message_count"] = len(self._messages[session_id])
            session.stats["snapshot_count"] = self._total_snapshots
        return message

    # -----------------------------------------------------------------------
    # Snapshot Retrieval
    # -----------------------------------------------------------------------

    def get_snapshot(self, session_id: str, entity_id: str) -> Optional[SyncSnapshot]:
        """Retrieve the most recent state snapshot for an entity.

        Args:
            session_id: Session the entity belongs to.
            entity_id: Entity to get the snapshot for.

        Returns:
            The most recent SyncSnapshot, or None if no snapshots exist.

        Raises:
            KeyError: If the session does not exist.
        """
        self._get_session(session_id)
        snapshots = self._entity_snapshots.get(entity_id, [])
        if not snapshots:
            return None
        return snapshots[-1]

    def get_snapshot_history(
        self,
        session_id: str,
        entity_id: str,
        limit: int = 10,
    ) -> List[SyncSnapshot]:
        """Retrieve the most recent N snapshots for an entity.

        Args:
            session_id: Session the entity belongs to.
            entity_id: Entity to get snapshots for.
            limit: Maximum number of snapshots to return.

        Returns:
            List of the most recent SyncSnapshots, newest first.
        """
        self._get_session(session_id)
        snapshots = list(self._entity_snapshots.get(entity_id, []))
        return snapshots[-limit:][::-1]

    # -----------------------------------------------------------------------
    # Message Retrieval
    # -----------------------------------------------------------------------

    def get_pending_messages(self, session_id: str) -> List[SyncMessage]:
        """Retrieve all messages queued for a session since last retrieval.

        Args:
            session_id: Session to retrieve messages for.

        Returns:
            List of pending SyncMessages (the queue is cleared after retrieval).

        Raises:
            KeyError: If the session does not exist.
        """
        self._get_session(session_id)
        with self._lock:
            messages = list(self._messages.get(session_id, []))
            self._messages[session_id] = []
        return messages

    # -----------------------------------------------------------------------
    # Heartbeat
    # -----------------------------------------------------------------------

    def heartbeat(self, connection_id: str) -> bool:
        """Update the heartbeat timestamp for a connection.

        Args:
            connection_id: Connection to update heartbeat for.

        Returns:
            True if the heartbeat was updated, False if the connection was not found.
        """
        connection = self._connections.get(connection_id)
        if connection is None:
            return False
        with self._lock:
            connection.last_heartbeat = datetime.utcnow().isoformat()
        return True

    def check_timeouts(self, timeout_seconds: float = 30.0) -> List[str]:
        """Check all connections for heartbeat timeout.

        Marks connections that have exceeded the timeout as TIMEOUT.

        Args:
            timeout_seconds: Maximum allowed time since last heartbeat.

        Returns:
            List of connection IDs that have timed out.
        """
        timed_out: List[str] = []
        now = datetime.utcnow()
        with self._lock:
            for conn_id, conn in list(self._connections.items()):
                if conn.state not in (ConnectionState.CONNECTED, ConnectionState.RECONNECTING):
                    continue
                try:
                    last_hb = datetime.fromisoformat(conn.last_heartbeat)
                    if (now - last_hb).total_seconds() > timeout_seconds:
                        conn.state = ConnectionState.TIMEOUT
                        timed_out.append(conn_id)
                except (ValueError, TypeError):
                    pass
        return timed_out

    # -----------------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return global engine statistics and health summary.

        Returns:
            Dict with session counts, connection metrics, entity counts,
            message totals, and snapshot totals.
        """
        with self._lock:
            connected_count = sum(
                1 for c in self._connections.values()
                if c.state == ConnectionState.CONNECTED
            )
            total_latency = sum(
                c.latency_ms for c in self._connections.values()
                if c.state == ConnectionState.CONNECTED
            )
            avg_latency = total_latency / max(1, connected_count)

            authority_distribution: Dict[str, int] = defaultdict(int)
            strategy_distribution: Dict[str, int] = defaultdict(int)
            for session in self._sessions.values():
                authority_distribution[session.authority.value] += 1
                strategy_distribution[session.strategy.value] += 1

            return {
                "total_sessions": len(self._sessions),
                "total_sessions_created": self._total_sessions,
                "total_connections": len(self._connections),
                "total_connections_created": self._total_connections,
                "connected_peers": connected_count,
                "total_entities": len(self._entities),
                "total_entities_registered": self._total_entities,
                "total_messages": self._total_messages,
                "total_snapshots": self._total_snapshots,
                "avg_latency_ms": round(avg_latency, 1),
                "authority_distribution": dict(authority_distribution),
                "strategy_distribution": dict(strategy_distribution),
                "max_snapshots_per_entity": self.MAX_SNAPSHOTS_PER_ENTITY,
                "max_messages_per_session": self.MAX_MESSAGES_PER_SESSION,
            }

    def reset(self) -> None:
        """Reset the entire network sync engine to its initial state."""
        with self._lock:
            self._sessions.clear()
            self._connections.clear()
            self._session_connections.clear()
            self._entities.clear()
            self._session_entities.clear()
            self._entity_states.clear()
            self._entity_snapshots.clear()
            self._entity_versions.clear()
            self._messages.clear()
            self._sequence_counters.clear()
            self._total_sessions = 0
            self._total_connections = 0
            self._total_entities = 0
            self._total_messages = 0
            self._total_snapshots = 0


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_network_sync(name: str = "default") -> NetworkSyncEngine:
    """Return the singleton NetworkSyncEngine instance.

    Args:
        name: Logical name for the instance (reserved for future multi-instance support).

    Returns:
        The singleton NetworkSyncEngine.
    """
    return NetworkSyncEngine.get_instance()