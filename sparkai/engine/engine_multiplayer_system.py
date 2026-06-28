"""
SparkLabs Engine - Multiplayer Networking System

Comprehensive multiplayer networking system for the SparkLabs AI-native
game engine. Provides client-server architecture, peer-to-peer support,
state synchronization, lag compensation, and matchmaking capabilities
across multiple network topologies and sync strategies.

Architecture:
  MultiplayerSystem (Singleton)
    |-- NetworkConfig          — global network configuration
    |-- PlayerConnection       — per-player connection metadata and health
    |-- GameRoom               — match lobby with player list and state
    |-- NetworkMessage         — typed message with priority and sequencing
    |-- SyncState              — state synchronization tracking data
    |-- NetworkStats           — aggregated network performance metrics
    |-- MultiplayerSnapshot    — complete system state snapshot
    |-- NetworkTopology (enum) — server architecture model
    |-- ConnectionState (enum) — player connection lifecycle
    |-- SyncStrategy (enum)    — state replication approach
    |-- MatchmakingMode (enum) — matchmaking queue classification

Core Capabilities:
  - initialize: Bootstrap the multiplayer system with configuration
  - create_room: Create a new game room from configuration
  - join_room: Connect a player to an existing room
  - leave_room: Remove a player from a room
  - send_message: Dispatch a typed message to room participants
  - broadcast_message: Fan-out a message to all players in a room
  - sync_game_state: Synchronize game state with delta compression
  - handle_disconnect: Gracefully handle player disconnection
  - start_matchmaking: Enqueue a player into the matchmaking pool
  - get_room_state: Retrieve the current state of a room
  - get_status: Aggregate system-wide multiplayer metrics
  - shutdown: Gracefully tear down all connections and rooms
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
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class NetworkTopology(Enum):
    """Server architecture model for the network session."""
    CLIENT_SERVER = "client_server"
    PEER_TO_PEER = "peer_to_peer"
    HYBRID = "hybrid"
    DEDICATED_SERVER = "dedicated_server"
    LISTEN_SERVER = "listen_server"


class ConnectionState(Enum):
    """Lifecycle state of a player connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    TIMEOUT = "timeout"
    ERROR = "error"


class SyncStrategy(Enum):
    """State synchronization approach between peers."""
    FULL_STATE = "full_state"
    DELTA_COMPRESSION = "delta_compression"
    INTEREST_MANAGEMENT = "interest_management"
    PREDICTIVE = "predictive"
    ROLLBACK = "rollback"


class MatchmakingMode(Enum):
    """Matchmaking queue classification."""
    QUICK_MATCH = "quick_match"
    RANKED = "ranked"
    CUSTOM = "custom"
    INVITE_ONLY = "invite_only"
    PARTY = "party"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class NetworkConfig:
    """Global network configuration for the multiplayer system.

    Attributes:
        topology: Server architecture model.
        sync_strategy: State replication approach.
        max_rooms: Maximum number of concurrent game rooms.
        max_players_per_room: Player capacity per room.
        tick_rate: Simulation ticks per second.
        heartbeat_interval_seconds: Interval between heartbeat pings.
        timeout_seconds: Disconnection timeout threshold.
        max_message_queue_size: Per-room message queue capacity.
        enable_lag_compensation: Whether to apply latency compensation.
        enable_prediction: Whether to allow client-side prediction.
        simulated_latency_ms: Simulated network latency for testing.
        simulated_packet_loss: Simulated packet loss ratio (0.0-1.0).
        region: Geographic region identifier.
        metadata: Arbitrary key-value configuration overrides.
    """
    topology: NetworkTopology = NetworkTopology.DEDICATED_SERVER
    sync_strategy: SyncStrategy = SyncStrategy.FULL_STATE
    max_rooms: int = 1000
    max_players_per_room: int = 32
    tick_rate: int = 30
    heartbeat_interval_seconds: float = 5.0
    timeout_seconds: float = 30.0
    max_message_queue_size: int = 5000
    enable_lag_compensation: bool = True
    enable_prediction: bool = False
    simulated_latency_ms: float = 0.0
    simulated_packet_loss: float = 0.0
    region: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topology": self.topology.value,
            "sync_strategy": self.sync_strategy.value,
            "max_rooms": self.max_rooms,
            "max_players_per_room": self.max_players_per_room,
            "tick_rate": self.tick_rate,
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            "timeout_seconds": self.timeout_seconds,
            "max_message_queue_size": self.max_message_queue_size,
            "enable_lag_compensation": self.enable_lag_compensation,
            "enable_prediction": self.enable_prediction,
            "simulated_latency_ms": self.simulated_latency_ms,
            "simulated_packet_loss": round(self.simulated_packet_loss, 4),
            "region": self.region,
            "metadata": self.metadata,
        }


@dataclass
class PlayerConnection:
    """A connected player's state and health information.

    Attributes:
        connection_id: Unique connection identifier.
        player_id: Logical player identifier (may span reconnects).
        player_name: Human-readable display name.
        state: Current connection lifecycle state.
        ip_address: Network address of the player.
        ping_ms: Measured round-trip latency in milliseconds.
        packet_loss: Fraction of packets lost (0.0 to 1.0).
        connected_at: Unix timestamp when connection was established.
        last_heartbeat: Unix timestamp of last received heartbeat.
        room_id: Room the player is currently in, if any.
        metadata: Arbitrary key-value data attached to the player.
    """
    connection_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    player_name: str = ""
    state: ConnectionState = ConnectionState.DISCONNECTED
    ip_address: str = "127.0.0.1"
    ping_ms: float = 0.0
    packet_loss: float = 0.0
    connected_at: float = 0.0
    last_heartbeat: float = 0.0
    room_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "state": self.state.value,
            "ip_address": self.ip_address,
            "ping_ms": round(self.ping_ms, 1),
            "packet_loss": round(self.packet_loss, 3),
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "room_id": self.room_id,
            "metadata": self.metadata,
        }


@dataclass
class GameRoom:
    """A game room or lobby hosting a multiplayer session.

    Attributes:
        room_id: Unique room identifier.
        name: Human-readable room name.
        host_player_id: Player who owns and administers the room.
        topology: Network topology for this room.
        sync_strategy: State synchronization strategy.
        max_players: Maximum number of players allowed.
        current_players: Number of currently connected players.
        player_ids: Ordered list of player IDs in the room.
        state: Room lifecycle state (lobby, playing, ended, etc.).
        password_hash: Optional hashed room password for private rooms.
        game_state: Current serialized game state for the room.
        state_version: Monotonically increasing state version counter.
        sync_tick: Current synchronization tick counter.
        created_at: Unix timestamp of room creation.
        started_at: Unix timestamp when the game started, if any.
        metadata: Arbitrary key-value room configuration.
    """
    room_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    host_player_id: str = ""
    topology: NetworkTopology = NetworkTopology.DEDICATED_SERVER
    sync_strategy: SyncStrategy = SyncStrategy.FULL_STATE
    max_players: int = 32
    current_players: int = 0
    player_ids: List[str] = field(default_factory=list)
    state: str = "lobby"
    password_hash: Optional[str] = None
    game_state: Dict[str, Any] = field(default_factory=dict)
    state_version: int = 0
    sync_tick: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "name": self.name,
            "host_player_id": self.host_player_id,
            "topology": self.topology.value,
            "sync_strategy": self.sync_strategy.value,
            "max_players": self.max_players,
            "current_players": self.current_players,
            "player_ids": list(self.player_ids),
            "state": self.state,
            "state_version": self.state_version,
            "sync_tick": self.sync_tick,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "metadata": self.metadata,
        }


@dataclass
class NetworkMessage:
    """A typed network message with priority and sequencing.

    Attributes:
        message_id: Unique message identifier.
        message_type: Semantic classification of the message.
        sender_id: Player or system that originated the message.
        room_id: Target room for the message.
        data: Serialized payload of the message.
        priority: Transmission priority (0 = highest, 255 = lowest).
        sequence: Monotonically increasing sequence number.
        timestamp: Unix timestamp when the message was created.
        reliable: Whether the message requires acknowledgment.
        ttl: Time-to-live in seconds; messages older than this are discarded.
    """
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    message_type: str = "custom"
    sender_id: str = ""
    room_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 128
    sequence: int = 0
    timestamp: float = field(default_factory=time.time)
    reliable: bool = True
    ttl: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "sender_id": self.sender_id,
            "room_id": self.room_id,
            "data": self.data,
            "priority": self.priority,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "reliable": self.reliable,
            "ttl": self.ttl,
        }


@dataclass
class SyncState:
    """State synchronization data tracking deltas and versions.

    Attributes:
        entity_id: Entity being synchronized.
        full_state: Complete entity state at the last full sync.
        delta: Changed properties since the previous sync.
        version: Monotonically increasing state version.
        last_sync_timestamp: Unix timestamp of the most recent sync.
        sync_strategy: Strategy used for this state.
        owner_id: Authoritative player for this state.
    """
    entity_id: str = ""
    full_state: Dict[str, Any] = field(default_factory=dict)
    delta: Dict[str, Any] = field(default_factory=dict)
    version: int = 0
    last_sync_timestamp: float = field(default_factory=time.time)
    sync_strategy: SyncStrategy = SyncStrategy.FULL_STATE
    owner_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "full_state": self.full_state,
            "delta": self.delta,
            "version": self.version,
            "last_sync_timestamp": self.last_sync_timestamp,
            "sync_strategy": self.sync_strategy.value,
            "owner_id": self.owner_id,
        }


@dataclass
class NetworkStats:
    """Aggregated network performance statistics.

    Attributes:
        total_messages_sent: Cumulative messages dispatched.
        total_messages_received: Cumulative messages received.
        total_bytes_sent: Cumulative bytes transmitted.
        total_bytes_received: Cumulative bytes received.
        total_packets_lost: Cumulative packets dropped due to loss simulation.
        avg_ping_ms: Average round-trip latency across all connections.
        avg_packet_loss: Average packet loss ratio across all connections.
        active_connections: Number of currently connected players.
        active_rooms: Number of rooms with at least one player.
        total_rooms_created: Cumulative rooms created.
        total_connections_handled: Cumulative connections established.
        total_disconnections: Cumulative disconnections processed.
        total_matchmaking_queries: Cumulative matchmaking requests.
        uptime_seconds: System uptime in seconds.
    """
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    total_packets_lost: int = 0
    avg_ping_ms: float = 0.0
    avg_packet_loss: float = 0.0
    active_connections: int = 0
    active_rooms: int = 0
    total_rooms_created: int = 0
    total_connections_handled: int = 0
    total_disconnections: int = 0
    total_matchmaking_queries: int = 0
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "total_bytes_sent": self.total_bytes_sent,
            "total_bytes_received": self.total_bytes_received,
            "total_packets_lost": self.total_packets_lost,
            "avg_ping_ms": round(self.avg_ping_ms, 1),
            "avg_packet_loss": round(self.avg_packet_loss, 4),
            "active_connections": self.active_connections,
            "active_rooms": self.active_rooms,
            "total_rooms_created": self.total_rooms_created,
            "total_connections_handled": self.total_connections_handled,
            "total_disconnections": self.total_disconnections,
            "total_matchmaking_queries": self.total_matchmaking_queries,
            "uptime_seconds": round(self.uptime_seconds, 1),
        }


@dataclass
class MultiplayerSnapshot:
    """Complete snapshot of the multiplayer system state for debugging.

    Attributes:
        config: Current network configuration.
        stats: Aggregated network statistics.
        rooms: List of all room summaries.
        connections: List of all connection summaries.
        matchmaking_queue: Active matchmaking queue entries.
        timestamp: Unix timestamp when the snapshot was captured.
    """
    config: NetworkConfig = field(default_factory=NetworkConfig)
    stats: NetworkStats = field(default_factory=NetworkStats)
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    connections: List[Dict[str, Any]] = field(default_factory=list)
    matchmaking_queue: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "stats": self.stats.to_dict(),
            "rooms": self.rooms,
            "connections": self.connections,
            "matchmaking_queue": self.matchmaking_queue,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# MultiplayerSystem — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class MultiplayerSystem:
    """Comprehensive multiplayer networking system for the SparkLabs
    AI-native game engine.

    Manages game rooms, player connections, network message routing,
    state synchronization with delta compression, lag compensation,
    and skill-based matchmaking across multiple network topologies.

    Thread-safe via a reentrant lock. Use get_multiplayer_system() or
    MultiplayerSystem.get_instance() to obtain the singleton.

    Usage:
        system = get_multiplayer_system()
        config = NetworkConfig(topology=NetworkTopology.DEDICATED_SERVER, tick_rate=60)
        system.initialize(config)
        room = system.create_room({"name": "My Game", "max_players": 8})
        system.join_room(room.room_id, "player_001")
        system.broadcast_message(room.room_id, NetworkMessage(
            message_type="chat", sender_id="player_001",
            data={"text": "Hello everyone!"},
        ))
    """

    _instance: Optional["MultiplayerSystem"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_DELTA_HISTORY: int = 64
    MAX_MATCHMAKING_POOL_SIZE: int = 10000
    MAX_MESSAGE_QUEUE_PER_ROOM: int = 5000

    def __new__(cls) -> "MultiplayerSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initialize internal network state, rooms, connections, and sync engine."""
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._config: Optional[NetworkConfig] = None
        self._rooms: Dict[str, GameRoom] = {}
        self._connections: Dict[str, PlayerConnection] = {}
        self._player_connections: Dict[str, str] = {}
        self._room_messages: Dict[str, List[NetworkMessage]] = defaultdict(list)
        self._room_sequence_counters: Dict[str, int] = defaultdict(int)
        self._room_state_history: Dict[str, Dict[int, Dict[str, Any]]] = defaultdict(dict)
        self._room_sync_states: Dict[str, Dict[str, SyncState]] = defaultdict(dict)
        self._matchmaking_pool: Dict[str, Dict[str, Any]] = {}
        self._player_skill_ratings: Dict[str, float] = {}
        self._started_at: float = time.time()
        self._stats: NetworkStats = NetworkStats()

        # Internal counters
        self._total_rooms_created: int = 0
        self._total_connections_handled: int = 0
        self._total_disconnections: int = 0
        self._total_messages_sent: int = 0
        self._total_messages_received: int = 0
        self._total_bytes_sent: int = 0
        self._total_bytes_received: int = 0
        self._total_packets_lost: int = 0
        self._total_matchmaking_queries: int = 0

    @classmethod
    def get_instance(cls) -> "MultiplayerSystem":
        """Return the singleton instance of MultiplayerSystem."""
        return cls()

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _get_room(self, room_id: str) -> GameRoom:
        """Retrieve a room by id, raising KeyError if not found."""
        if room_id not in self._rooms:
            raise KeyError(f"Room not found: {room_id}")
        return self._rooms[room_id]

    def _get_connection(self, connection_id: str) -> PlayerConnection:
        """Retrieve a connection by id, raising KeyError if not found."""
        if connection_id not in self._connections:
            raise KeyError(f"Connection not found: {connection_id}")
        return self._connections[connection_id]

    def _get_connection_by_player(self, player_id: str) -> Optional[PlayerConnection]:
        """Find a player's connection by player ID."""
        conn_id = self._player_connections.get(player_id)
        if conn_id is None:
            return None
        return self._connections.get(conn_id)

    def _next_sequence(self, room_id: str) -> int:
        """Increment and return the next sequence number for a room."""
        seq = self._room_sequence_counters.get(room_id, 0) + 1
        self._room_sequence_counters[room_id] = seq
        return seq

    def _compute_delta(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute the difference between two state dicts.

        Returns a dict containing only properties that have changed.
        If nothing changed, returns an empty dict.
        """
        delta: Dict[str, Any] = {}
        for key, value in current.items():
            if key not in previous or previous[key] != value:
                delta[key] = value
        return delta

    def _simulate_latency(self) -> float:
        """Simulate a realistic network latency based on configured settings."""
        base = self._config.simulated_latency_ms if self._config else 0.0
        if base > 0:
            return base + random.uniform(-base * 0.2, base * 0.2)
        return random.uniform(5.0, 60.0)

    def _simulate_packet_loss(self) -> bool:
        """Simulate whether a packet should be dropped based on configured loss rate."""
        if self._config is None:
            return False
        loss_rate = self._config.simulated_packet_loss
        if loss_rate <= 0:
            return False
        return random.random() < loss_rate

    def _estimate_message_size(self, message: NetworkMessage) -> int:
        """Estimate the serialized size of a network message in bytes."""
        try:
            payload = json.dumps(message.to_dict(), default=str)
            return len(payload.encode("utf-8"))
        except (TypeError, ValueError):
            return 0

    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------

    def initialize(self, config: NetworkConfig) -> None:
        """Initialize the multiplayer system with the given configuration.

        Sets up the network topology, sync strategy, room and player limits,
        heartbeat intervals, and simulated network conditions. This method
        must be called before any other operations.

        Args:
            config: NetworkConfig instance with desired settings.
        """
        with self._lock:
            self._config = config
            self._rooms.clear()
            self._connections.clear()
            self._player_connections.clear()
            self._room_messages.clear()
            self._room_sequence_counters.clear()
            self._room_state_history.clear()
            self._room_sync_states.clear()
            self._matchmaking_pool.clear()
            self._player_skill_ratings.clear()
            self._started_at = time.time()
            self._stats = NetworkStats()
            self._total_rooms_created = 0
            self._total_connections_handled = 0
            self._total_disconnections = 0
            self._total_messages_sent = 0
            self._total_messages_received = 0
            self._total_bytes_sent = 0
            self._total_bytes_received = 0
            self._total_packets_lost = 0
            self._total_matchmaking_queries = 0

    # -----------------------------------------------------------------------
    # Room Management
    # -----------------------------------------------------------------------

    def create_room(self, room_config: Dict[str, Any]) -> GameRoom:
        """Create a new game room from the provided configuration.

        Args:
            room_config: Dictionary with room settings. Supported keys:
                - name: Human-readable room name.
                - host_player_id: Player who owns the room.
                - max_players: Maximum number of players (defaults to config limit).
                - topology: NetworkTopology or string value.
                - sync_strategy: SyncStrategy or string value.
                - password_hash: Optional hashed password for private rooms.
                - metadata: Arbitrary key-value room metadata.

        Returns:
            The newly created GameRoom.

        Raises:
            RuntimeError: If the system has not been initialized.
            ValueError: If the room limit has been reached.
        """
        if self._config is None:
            raise RuntimeError("MultiplayerSystem not initialized. Call initialize() first.")

        with self._lock:
            if len(self._rooms) >= self._config.max_rooms:
                raise ValueError(
                    f"Room limit reached ({self._config.max_rooms}). Cannot create new room."
                )

            topology = self._config.topology
            if "topology" in room_config:
                topo_val = room_config["topology"]
                if isinstance(topo_val, str):
                    topology = NetworkTopology(topo_val.lower())
                elif isinstance(topo_val, NetworkTopology):
                    topology = topo_val

            sync_strategy = self._config.sync_strategy
            if "sync_strategy" in room_config:
                strat_val = room_config["sync_strategy"]
                if isinstance(strat_val, str):
                    sync_strategy = SyncStrategy(strat_val.lower())
                elif isinstance(strat_val, SyncStrategy):
                    sync_strategy = strat_val

            max_players = room_config.get(
                "max_players", self._config.max_players_per_room
            )

            room = GameRoom(
                name=room_config.get("name", f"Room_{self._total_rooms_created + 1}"),
                host_player_id=room_config.get("host_player_id", ""),
                topology=topology,
                sync_strategy=sync_strategy,
                max_players=max_players,
                password_hash=room_config.get("password_hash"),
                metadata=room_config.get("metadata", {}),
            )

            self._rooms[room.room_id] = room
            self._room_messages[room.room_id] = []
            self._room_sequence_counters[room.room_id] = 0
            self._room_state_history[room.room_id] = {}
            self._room_sync_states[room.room_id] = {}
            self._total_rooms_created += 1

        return room

    def join_room(self, room_id: str, player_id: str) -> PlayerConnection:
        """Join an existing room with the given player.

        Establishes a player connection with simulated latency and packet loss
        metrics. Adds the player to the room's player list. Rejects the join
        if the room is full or if the player is already in the room.

        Args:
            room_id: Target room identifier.
            player_id: Logical player identifier.

        Returns:
            The PlayerConnection instance for the joined player.

        Raises:
            RuntimeError: If the system has not been initialized.
            KeyError: If the room does not exist.
            ValueError: If the room is full or player is already in the room.
        """
        if self._config is None:
            raise RuntimeError("MultiplayerSystem not initialized. Call initialize() first.")

        room = self._get_room(room_id)

        with self._lock:
            if len(room.player_ids) >= room.max_players:
                raise ValueError(
                    f"Room {room_id} is full ({len(room.player_ids)}/{room.max_players})"
                )

            if player_id in room.player_ids:
                raise ValueError(
                    f"Player {player_id} is already in room {room_id}"
                )

            # Check if player already has a connection; reuse or create
            existing = self._get_connection_by_player(player_id)
            if existing is not None:
                existing.room_id = room_id
                existing.state = ConnectionState.CONNECTED
                existing.last_heartbeat = time.time()
                connection = existing
            else:
                connection = PlayerConnection(
                    player_id=player_id,
                    player_name=f"Player_{player_id[:8]}",
                    state=ConnectionState.CONNECTING,
                    ip_address=f"192.168.1.{random.randint(2, 254)}",
                    connected_at=time.time(),
                    last_heartbeat=time.time(),
                    room_id=room_id,
                )
                connection.ping_ms = self._simulate_latency()
                connection.packet_loss = (
                    self._config.simulated_packet_loss
                    if self._config.simulated_packet_loss > 0
                    else random.uniform(0.0, 0.02)
                )
                connection.state = ConnectionState.CONNECTED
                self._connections[connection.connection_id] = connection
                self._player_connections[player_id] = connection.connection_id
                self._total_connections_handled += 1

            room.player_ids.append(player_id)
            room.current_players = len(room.player_ids)

            if player_id not in self._player_skill_ratings:
                self._player_skill_ratings[player_id] = random.uniform(800.0, 1200.0)

        return connection

    def leave_room(self, room_id: str, player_id: str) -> None:
        """Remove a player from a room.

        If the player was the host, the host is reassigned to another player
        in the room, if any remain. If the room becomes empty and the state
        was 'ended', the room is removed.

        Args:
            room_id: Room to leave.
            player_id: Player to remove.

        Raises:
            KeyError: If the room does not exist or the player is not in the room.
        """
        room = self._get_room(room_id)

        if player_id not in room.player_ids:
            raise KeyError(
                f"Player {player_id} is not in room {room_id}"
            )

        with self._lock:
            room.player_ids.remove(player_id)
            room.current_players = len(room.player_ids)

            # Reassign host if the leaving player was the host
            if room.host_player_id == player_id:
                room.host_player_id = room.player_ids[0] if room.player_ids else ""

            # Update connection state
            conn = self._get_connection_by_player(player_id)
            if conn is not None:
                conn.room_id = None
                conn.last_heartbeat = time.time()

            # Clean up empty ended rooms
            if not room.player_ids and room.state == "ended":
                self._rooms.pop(room_id, None)
                self._room_messages.pop(room_id, None)
                self._room_sequence_counters.pop(room_id, None)
                self._room_state_history.pop(room_id, None)
                self._room_sync_states.pop(room_id, None)

    def get_room_state(self, room_id: str) -> Dict[str, Any]:
        """Retrieve the current state of a room.

        Returns the room summary, connected player details, and the current
        game state with its version.

        Args:
            room_id: Room to query.

        Returns:
            Dict with room summary, player list, and game state.

        Raises:
            KeyError: If the room does not exist.
        """
        room = self._get_room(room_id)
        player_details = []
        for pid in room.player_ids:
            conn = self._get_connection_by_player(pid)
            if conn:
                player_details.append(conn.to_dict())
            else:
                player_details.append({"player_id": pid, "state": "unknown"})

        return {
            "room": room.to_dict(),
            "players": player_details,
            "game_state": room.game_state,
            "state_version": room.state_version,
            "sync_tick": room.sync_tick,
        }

    # -----------------------------------------------------------------------
    # Messaging
    # -----------------------------------------------------------------------

    def send_message(
        self,
        room_id: str,
        sender_id: str,
        message: NetworkMessage,
    ) -> NetworkMessage:
        """Send a network message from a sender to their room.

        Assigns a sequence number and timestamp to the message. Simulates
        packet loss based on the configured loss rate. Appends the message
        to the room's message queue for retrieval by other players.

        Args:
            room_id: Target room identifier.
            sender_id: ID of the player sending the message.
            message: The NetworkMessage to send.

        Returns:
            The NetworkMessage with sequence and timestamp assigned.

        Raises:
            KeyError: If the room does not exist.
        """
        room = self._get_room(room_id)

        with self._lock:
            seq = self._next_sequence(room_id)
            message.sequence = seq
            message.sender_id = sender_id
            message.room_id = room_id
            message.timestamp = time.time()

            size = self._estimate_message_size(message)

            # Simulate packet loss
            if self._simulate_packet_loss():
                self._total_packets_lost += 1
                return message

            queue = self._room_messages[room_id]
            queue.append(message)
            if len(queue) > self._config.max_message_queue_size:
                self._room_messages[room_id] = queue[
                    -self._config.max_message_queue_size:
                ]

            self._total_messages_sent += 1
            self._total_bytes_sent += size

        return message

    def broadcast_message(
        self,
        room_id: str,
        message: NetworkMessage,
    ) -> int:
        """Broadcast a message to all players in a room.

        Assigns a sequence number and fans out the message to every player
        currently in the room. The sender_id on the message is used as-is.

        Args:
            room_id: Target room identifier.
            message: The NetworkMessage to broadcast.

        Returns:
            The number of players the message was sent to.

        Raises:
            KeyError: If the room does not exist.
        """
        room = self._get_room(room_id)

        with self._lock:
            seq = self._next_sequence(room_id)
            message.sequence = seq
            message.room_id = room_id
            message.timestamp = time.time()

            size = self._estimate_message_size(message)

            # Simulate packet loss
            if self._simulate_packet_loss():
                self._total_packets_lost += 1
                return 0

            recipient_count = len(room.player_ids)
            queue = self._room_messages[room_id]
            queue.append(message)
            if len(queue) > self._config.max_message_queue_size:
                self._room_messages[room_id] = queue[
                    -self._config.max_message_queue_size:
                ]

            self._total_messages_sent += 1
            self._total_bytes_sent += size

        return recipient_count

    # -----------------------------------------------------------------------
    # State Synchronization
    # -----------------------------------------------------------------------

    def sync_game_state(self, room_id: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronize game state for a room using the configured strategy.

        Performs a state synchronization pass: increments the state version,
        computes deltas if the room uses delta compression, stores a snapshot
        in the state history, and updates the room's game state.

        Args:
            room_id: Room to synchronize.
            game_state: Dict mapping entity IDs to their state properties.

        Returns:
            Dict with sync results including version, tick, delta sizes,
            and strategy used.

        Raises:
            KeyError: If the room does not exist.
        """
        room = self._get_room(room_id)
        strategy = room.sync_strategy

        with self._lock:
            room.sync_tick += 1
            room.state_version += 1

            previous_state = dict(room.game_state)
            room.game_state = dict(game_state)

            # Store tick-based snapshot
            history = self._room_state_history[room_id]
            history[room.sync_tick] = dict(game_state)
            if len(history) > self.MAX_DELTA_HISTORY:
                oldest = min(history.keys())
                del history[oldest]

            # Compute delta if using delta compression
            delta_state: Dict[str, Any] = {}
            if strategy == SyncStrategy.DELTA_COMPRESSION and previous_state:
                delta_state = self._compute_delta(previous_state, game_state)

            # Update per-entity sync states
            sync_states = self._room_sync_states[room_id]
            for entity_id, entity_data in game_state.items():
                if entity_id in sync_states:
                    ss = sync_states[entity_id]
                    ss.full_state = dict(entity_data)
                    ss.delta = self._compute_delta(ss.full_state, entity_data)
                    ss.version += 1
                    ss.last_sync_timestamp = time.time()
                else:
                    sync_states[entity_id] = SyncState(
                        entity_id=entity_id,
                        full_state=dict(entity_data),
                        delta={},
                        version=1,
                        last_sync_timestamp=time.time(),
                        sync_strategy=strategy,
                    )

            full_size = len(json.dumps(game_state, default=str).encode("utf-8"))
            delta_size = len(json.dumps(delta_state, default=str).encode("utf-8"))

            return {
                "room_id": room_id,
                "strategy": strategy.value,
                "tick": room.sync_tick,
                "state_version": room.state_version,
                "entity_count": len(game_state),
                "full_state_size_bytes": full_size,
                "delta_state_size_bytes": delta_size,
                "compression_ratio": round(
                    delta_size / max(1, full_size), 4
                ),
                "has_delta": bool(delta_state),
                "timestamp": time.time(),
            }

    # -----------------------------------------------------------------------
    # Disconnection Handling
    # -----------------------------------------------------------------------

    def handle_disconnect(self, player_id: str) -> Dict[str, Any]:
        """Handle a player disconnection gracefully.

        Marks the player's connection as DISCONNECTED, removes them from
        any room they were in, and handles host reassignment. Updates
        aggregate disconnection statistics.

        Args:
            player_id: Player to disconnect.

        Returns:
            Dict with disconnection details including affected rooms,
            player info, and whether the player was found.
        """
        result: Dict[str, Any] = {
            "player_id": player_id,
            "disconnected": False,
            "affected_rooms": [],
            "was_host": False,
        }

        conn = self._get_connection_by_player(player_id)
        if conn is None:
            result["reason"] = "player_not_found"
            return result

        with self._lock:
            conn.state = ConnectionState.DISCONNECTED
            conn.last_heartbeat = time.time()

            room_id = conn.room_id
            if room_id is not None:
                room = self._rooms.get(room_id)
                if room and player_id in room.player_ids:
                    result["affected_rooms"].append(room_id)
                    result["was_host"] = (room.host_player_id == player_id)

                    room.player_ids.remove(player_id)
                    room.current_players = len(room.player_ids)

                    if room.host_player_id == player_id:
                        room.host_player_id = room.player_ids[0] if room.player_ids else ""

                conn.room_id = None

            self._total_disconnections += 1
            result["disconnected"] = True
            result["connection_id"] = conn.connection_id

        return result

    # -----------------------------------------------------------------------
    # Matchmaking
    # -----------------------------------------------------------------------

    def start_matchmaking(
        self,
        mode: MatchmakingMode,
        criteria: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Start matchmaking for a player with the given mode and criteria.

        Adds the player to the matchmaking pool. If criteria includes a
        player_id, the player is identified; otherwise a new anonymous
        entry is created. The system attempts to find a match immediately
        and returns the result.

        Args:
            mode: Matchmaking queue classification.
            criteria: Dict with player_id, skill_rating, preferences,
                skill_range, and region.

        Returns:
            Dict with matchmaking result including matched status,
            room ID if matched, and pool statistics.
        """
        if self._config is None:
            raise RuntimeError("MultiplayerSystem not initialized. Call initialize() first.")

        player_id = criteria.get("player_id", uuid.uuid4().hex)

        with self._lock:
            if len(self._matchmaking_pool) >= self.MAX_MATCHMAKING_POOL_SIZE:
                return {
                    "player_id": player_id,
                    "mode": mode.value,
                    "matched": False,
                    "reason": "matchmaking_pool_full",
                    "pool_size": len(self._matchmaking_pool),
                }

            if player_id not in self._player_skill_ratings:
                self._player_skill_ratings[player_id] = criteria.get(
                    "skill_rating", random.uniform(800.0, 1200.0)
                )

            self._matchmaking_pool[player_id] = {
                "mode": mode.value,
                "skill_rating": self._player_skill_ratings[player_id],
                "preferences": criteria.get("preferences", {}),
                "skill_range": criteria.get("skill_range", 200.0),
                "region": criteria.get("region", self._config.region),
                "entered_at": time.time(),
            }
            self._total_matchmaking_queries += 1

        # Attempt to find a match
        return self._find_match(player_id, mode)

    def _find_match(
        self,
        player_id: str,
        mode: MatchmakingMode,
    ) -> Dict[str, Any]:
        """Find a suitable match for a player from the matchmaking pool.

        Matches based on mode compatibility, skill proximity, and region.
        Players with longer wait times get expanded skill range tolerance.

        Args:
            player_id: Player seeking a match.
            mode: Matchmaking mode to match within.

        Returns:
            Dict with match result details.
        """
        player_data = self._matchmaking_pool.get(player_id)
        if player_data is None:
            return {
                "player_id": player_id,
                "mode": mode.value,
                "matched": False,
                "reason": "player_not_in_pool",
            }

        player_skill = player_data["skill_rating"]
        player_region = player_data["region"]
        player_prefs = player_data["preferences"]
        skill_range = player_data["skill_range"]
        wait_seconds = time.time() - player_data["entered_at"]

        # Expand skill range based on wait time
        wait_factor = 1.0 + (wait_seconds / 30.0)
        effective_skill_range = skill_range * wait_factor

        candidates: List[Tuple[str, float]] = []
        for other_id, other_data in self._matchmaking_pool.items():
            if other_id == player_id:
                continue
            if other_data["mode"] != mode.value:
                continue
            if other_data.get("region", "default") != player_region:
                continue

            other_skill = other_data["skill_rating"]
            skill_diff = abs(player_skill - other_skill)
            if skill_diff > effective_skill_range:
                continue

            skill_score = 1.0 - (skill_diff / effective_skill_range)
            pref_score = self._compute_preference_overlap(
                player_prefs, other_data.get("preferences", {})
            )
            other_wait = time.time() - other_data.get("entered_at", time.time())
            wait_score = min(1.0, other_wait / 60.0)

            total_score = skill_score * 0.5 + pref_score * 0.3 + wait_score * 0.2
            candidates.append((other_id, total_score))

        if not candidates:
            return {
                "player_id": player_id,
                "mode": mode.value,
                "matched": False,
                "reason": "no_suitable_candidates",
                "wait_seconds": round(wait_seconds, 1),
                "skill_rating": player_skill,
                "effective_skill_range": round(effective_skill_range, 1),
                "pool_size": max(0, len(self._matchmaking_pool) - 1),
            }

        candidates.sort(key=lambda x: x[1], reverse=True)
        best_match_id, best_score = candidates[0]

        # Create a room for the matched players
        room = self.create_room({
            "name": f"Match_{player_id[:8]}_{best_match_id[:8]}",
            "host_player_id": player_id,
            "max_players": 4,
            "metadata": {
                "matchmaking_mode": mode.value,
                "match_score": round(best_score, 4),
            },
        })

        # Clean up both players from the pool
        with self._lock:
            self._matchmaking_pool.pop(player_id, None)
            self._matchmaking_pool.pop(best_match_id, None)

        return {
            "player_id": player_id,
            "mode": mode.value,
            "matched": True,
            "matched_player_id": best_match_id,
            "match_score": round(best_score, 4),
            "skill_diff": round(
                abs(player_skill - self._player_skill_ratings.get(best_match_id, 1000.0)), 1
            ),
            "room_id": room.room_id,
            "room_name": room.name,
            "wait_seconds": round(wait_seconds, 1),
            "candidates_evaluated": len(candidates),
        }

    def _compute_preference_overlap(
        self,
        prefs_a: Dict[str, Any],
        prefs_b: Dict[str, Any],
    ) -> float:
        """Compute overlap score between two preference sets.

        Returns a value between 0.0 (no overlap) and 1.0 (identical).
        """
        if not prefs_a and not prefs_b:
            return 1.0
        if not prefs_a or not prefs_b:
            return 0.0
        common_keys = set(prefs_a.keys()) & set(prefs_b.keys())
        if not common_keys:
            return 0.1
        matches = sum(
            1 for key in common_keys if prefs_a[key] == prefs_b[key]
        )
        return matches / len(common_keys)

    # -----------------------------------------------------------------------
    # Status and Statistics
    # -----------------------------------------------------------------------

    def get_status(self) -> MultiplayerSnapshot:
        """Get a complete snapshot of the multiplayer system status.

        Returns a MultiplayerSnapshot containing the current configuration,
        aggregated network statistics, room summaries, connection details,
        and matchmaking queue state.

        Returns:
            MultiplayerSnapshot with full system state.
        """
        with self._lock:
            # Compute live stats
            active_connections = sum(
                1 for c in self._connections.values()
                if c.state == ConnectionState.CONNECTED
            )
            active_rooms = sum(
                1 for r in self._rooms.values()
                if r.current_players > 0
            )

            total_ping = sum(
                c.ping_ms for c in self._connections.values()
                if c.state == ConnectionState.CONNECTED
            )
            avg_ping = total_ping / max(1, active_connections)

            total_pl = sum(
                c.packet_loss for c in self._connections.values()
                if c.state == ConnectionState.CONNECTED
            )
            avg_pl = total_pl / max(1, active_connections)

            self._stats = NetworkStats(
                total_messages_sent=self._total_messages_sent,
                total_messages_received=self._total_messages_received,
                total_bytes_sent=self._total_bytes_sent,
                total_bytes_received=self._total_bytes_received,
                total_packets_lost=self._total_packets_lost,
                avg_ping_ms=avg_ping,
                avg_packet_loss=avg_pl,
                active_connections=active_connections,
                active_rooms=active_rooms,
                total_rooms_created=self._total_rooms_created,
                total_connections_handled=self._total_connections_handled,
                total_disconnections=self._total_disconnections,
                total_matchmaking_queries=self._total_matchmaking_queries,
                uptime_seconds=time.time() - self._started_at,
            )

            room_summaries = [r.to_dict() for r in self._rooms.values()]
            connection_summaries = [c.to_dict() for c in self._connections.values()]
            queue_summaries = [
                {"player_id": pid, **data}
                for pid, data in self._matchmaking_pool.items()
            ]

            return MultiplayerSnapshot(
                config=self._config or NetworkConfig(),
                stats=self._stats,
                rooms=room_summaries,
                connections=connection_summaries,
                matchmaking_queue=queue_summaries,
            )

    # -----------------------------------------------------------------------
    # Shutdown
    # -----------------------------------------------------------------------

    def shutdown(self) -> None:
        """Perform a graceful shutdown of the multiplayer system.

        Disconnects all players, closes all rooms, clears the matchmaking
        pool, and resets all statistics. The system remains in an
        uninitialized state and must be re-initialized before further use.
        """
        with self._lock:
            # Disconnect all players
            for conn in list(self._connections.values()):
                if conn.state == ConnectionState.CONNECTED:
                    conn.state = ConnectionState.DISCONNECTED
                    conn.last_heartbeat = time.time()
                    conn.room_id = None

            # Clear all rooms
            self._rooms.clear()

            # Clear all state
            self._connections.clear()
            self._player_connections.clear()
            self._room_messages.clear()
            self._room_sequence_counters.clear()
            self._room_state_history.clear()
            self._room_sync_states.clear()
            self._matchmaking_pool.clear()
            self._player_skill_ratings.clear()

            self._config = None
            self._total_rooms_created = 0
            self._total_connections_handled = 0
            self._total_disconnections = 0
            self._total_messages_sent = 0
            self._total_messages_received = 0
            self._total_bytes_sent = 0
            self._total_bytes_received = 0
            self._total_packets_lost = 0
            self._total_matchmaking_queries = 0
            self._stats = NetworkStats()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_multiplayer_system() -> MultiplayerSystem:
    """Get the MultiplayerSystem singleton instance."""
    return MultiplayerSystem.get_instance()