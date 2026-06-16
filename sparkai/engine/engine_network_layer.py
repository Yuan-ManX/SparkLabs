"""
SparkLabs Engine - Network Layer

AI-optimized networking layer for multiplayer games. Provides state
synchronization, latency compensation, matchmaking, and session
management across multiple network topologies. Simulates real-world
network conditions for development and testing.

Architecture:
  NetworkLayerEngine (Singleton)
    |-- NetworkSession           — active game session with topology and sync config
    |-- PlayerConnection         — per-player connection metadata and health
    |-- SyncPacket               — individual network packet with reliability flags
    |-- MatchmakingQuery         — player matchmaking request with preferences
    |-- NetworkTopology          — server architecture model
    |-- SyncStrategy             — state synchronization approach
    |-- ConnectionState          — player connection lifecycle states

Network Topologies:
  - CLIENT_SERVER: one host relays all traffic
  - PEER_TO_PEER: each peer communicates directly with others
  - AUTHORITATIVE_SERVER: server owns game state, clients send inputs
  - HYBRID: server arbitrates critical state, peers share non-critical
  - DEDICATED_SERVER: headless server instance runs the simulation

Sync Strategies:
  - FULL_STATE: transmit complete entity state each tick
  - DELTA: transmit only changed properties since last sync
  - INTERPOLATION: smooth between two known snapshots
  - PREDICTION: client-side extrapolation of state
  - ROLLBACK: re-simulate on misprediction
  - SNAPSHOT: periodic full captures with interpolation
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class NetworkTopology(Enum):
    """Server architecture model for the network session."""
    CLIENT_SERVER = "client_server"
    PEER_TO_PEER = "peer_to_peer"
    AUTHORITATIVE_SERVER = "authoritative_server"
    HYBRID = "hybrid"
    DEDICATED_SERVER = "dedicated_server"


class SyncStrategy(Enum):
    """State synchronization approach between peers."""
    FULL_STATE = "full_state"
    DELTA = "delta"
    INTERPOLATION = "interpolation"
    PREDICTION = "prediction"
    ROLLBACK = "rollback"
    SNAPSHOT = "snapshot"


class ConnectionState(Enum):
    """Lifecycle state of a player connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    TIMEOUT = "timeout"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class NetworkSession:
    """Active game session with topology, sync strategy, and player capacity.

    Attributes:
        session_id: Unique identifier for this session.
        name: Human-readable session label.
        topology: Network architecture model for this session.
        max_players: Upper limit on concurrent players.
        current_players: Number of currently connected players.
        sync_strategy: How game state is replicated between participants.
        tick_rate: Server simulation ticks per second.
        created_at: Unix timestamp of session creation.
        state: Whether the session is live, paused, or ended.
    """
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    topology: NetworkTopology = NetworkTopology.AUTHORITATIVE_SERVER
    max_players: int = 16
    current_players: int = 0
    sync_strategy: SyncStrategy = SyncStrategy.FULL_STATE
    tick_rate: int = 30
    created_at: float = field(default_factory=time.time)
    state: str = "lobby"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "topology": self.topology.value,
            "max_players": self.max_players,
            "current_players": self.current_players,
            "sync_strategy": self.sync_strategy.value,
            "tick_rate": self.tick_rate,
            "created_at": self.created_at,
            "state": self.state,
        }


@dataclass
class PlayerConnection:
    """Per-player connection metadata and health tracking.

    Attributes:
        connection_id: Unique identifier for this connection instance.
        player_id: Logical player identifier (may span reconnects).
        session_id: Session this player belongs to.
        state: Current connection lifecycle state.
        ip_address: Network address of the player.
        ping_ms: Measured round-trip latency in milliseconds.
        packet_loss: Fraction of packets lost (0.0 to 1.0).
        connected_at: Unix timestamp when connection was established.
        last_heartbeat: Unix timestamp of last received heartbeat.
    """
    connection_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    session_id: str = ""
    state: ConnectionState = ConnectionState.DISCONNECTED
    ip_address: str = "127.0.0.1"
    ping_ms: float = 0.0
    packet_loss: float = 0.0
    connected_at: float = 0.0
    last_heartbeat: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "player_id": self.player_id,
            "session_id": self.session_id,
            "state": self.state.value,
            "ip_address": self.ip_address,
            "ping_ms": round(self.ping_ms, 1),
            "packet_loss": round(self.packet_loss, 3),
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
        }


@dataclass
class SyncPacket:
    """Individual network packet with sequence tracking and reliability flags.

    Attributes:
        packet_id: Unique identifier for this packet.
        session_id: Session this packet belongs to.
        sender_id: Player or server that originated this packet.
        sequence: Monotonically increasing sequence number.
        data: Serialized payload of the packet.
        timestamp: Unix timestamp when the packet was created.
        size_bytes: Approximate size of the serialized payload.
        reliable: Whether the packet requires acknowledgment.
    """
    packet_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    sender_id: str = ""
    sequence: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    size_bytes: int = 0
    reliable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "session_id": self.session_id,
            "sender_id": self.sender_id,
            "sequence": self.sequence,
            "data": self.data,
            "timestamp": self.timestamp,
            "size_bytes": self.size_bytes,
            "reliable": self.reliable,
        }


@dataclass
class MatchmakingQuery:
    """Player matchmaking request with preferences and skill constraints.

    Attributes:
        query_id: Unique identifier for this matchmaking request.
        player_id: Player seeking a match.
        preferences: Dict of game-mode, map, or rule preferences.
        skill_range: Allowed skill deviation from the player's rating.
        region: Geographic region for latency-aware matching.
        created_at: Unix timestamp when the query was submitted.
    """
    query_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    preferences: Dict[str, Any] = field(default_factory=dict)
    skill_range: float = 200.0
    region: str = "default"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "player_id": self.player_id,
            "preferences": self.preferences,
            "skill_range": self.skill_range,
            "region": self.region,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# NetworkLayerEngine
# ---------------------------------------------------------------------------


class NetworkLayerEngine:
    """AI-optimized networking layer for multiplayer game state management.

    Manages game sessions, player connections, packet transmission, state
    synchronization (full/delta/interpolation/prediction), latency
    compensation, and skill-based matchmaking. Simulates network conditions
    to enable offline development and testing.
    """

    _instance: Optional["NetworkLayerEngine"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._sessions: Dict[str, NetworkSession] = {}
        self._connections: Dict[str, PlayerConnection] = {}
        self._session_connections: Dict[str, List[str]] = {}
        self._session_entities: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._session_entity_versions: Dict[str, Dict[str, int]] = {}
        self._session_deltas: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._session_state_snapshots: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self._session_packets: Dict[str, List[SyncPacket]] = {}
        self._sequence_counters: Dict[str, int] = {}
        self._tick_counters: Dict[str, int] = {}
        self._matchmaking_queue: Dict[str, MatchmakingQuery] = {}
        self._matchmaking_pool: Dict[str, Dict[str, Any]] = {}
        self._player_skill_ratings: Dict[str, float] = {}
        self._session_tick_rates: Dict[str, int] = {}
        self._simulated_latency_ms: float = 0.0
        self._simulated_packet_loss: float = 0.0
        self._simulated_jitter_ms: float = 0.0
        self._total_packets_sent: int = 0
        self._total_packets_lost: int = 0
        self._total_bytes_sent: int = 0

    @classmethod
    def get_instance(cls) -> "NetworkLayerEngine":
        """Return the singleton instance of NetworkLayerEngine."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -----------------------------------------------------------------------
    # Session Management
    # -----------------------------------------------------------------------

    def create_session(
        self,
        name: str = "",
        topology: NetworkTopology = NetworkTopology.AUTHORITATIVE_SERVER,
        max_players: int = 16,
        sync_strategy: SyncStrategy = SyncStrategy.FULL_STATE,
        tick_rate: int = 30,
    ) -> NetworkSession:
        """Create a new game session with the specified topology and sync strategy.

        Args:
            name: Human-readable label for the session.
            topology: Network architecture model.
            max_players: Maximum number of concurrent players.
            sync_strategy: State replication strategy.
            tick_rate: Server simulation ticks per second.

        Returns:
            The newly created NetworkSession.
        """
        session = NetworkSession(
            name=name or f"Session_{random.randint(1000, 9999)}",
            topology=topology,
            max_players=max_players,
            sync_strategy=sync_strategy,
            tick_rate=tick_rate,
        )
        with self._lock:
            self._sessions[session.session_id] = session
            self._session_connections[session.session_id] = []
            self._session_entities[session.session_id] = {}
            self._session_entity_versions[session.session_id] = {}
            self._session_deltas[session.session_id] = {}
            self._session_state_snapshots[session.session_id] = {}
            self._session_packets[session.session_id] = []
            self._sequence_counters[session.session_id] = 0
            self._tick_counters[session.session_id] = 0
            self._session_tick_rates[session.session_id] = tick_rate
        return session

    def get_session(self, session_id: str) -> Optional[NetworkSession]:
        """Retrieve a session by its identifier."""
        return self._sessions.get(session_id)

    def _get_session(self, session_id: str) -> NetworkSession:
        """Internal helper: get session or raise KeyError."""
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")
        return self._sessions[session_id]

    # -----------------------------------------------------------------------
    # Player Connection Management
    # -----------------------------------------------------------------------

    def connect_player(
        self,
        session_id: str,
        player_id: str,
        ip_address: str = "127.0.0.1",
    ) -> PlayerConnection:
        """Connect a player to an existing session.

        Simulates network connection establishment including ping measurement
        and packet loss estimation. Rejects connections when the session is full.

        Args:
            session_id: Target session identifier.
            player_id: Logical player identifier.
            ip_address: Network address of the connecting player.

        Returns:
            The PlayerConnection instance.

        Raises:
            KeyError: If the session does not exist.
            ValueError: If the session is full.
        """
        session = self._get_session(session_id)
        with self._lock:
            if session.current_players >= session.max_players:
                raise ValueError(
                    f"Session {session_id} is full ({session.current_players}/{session.max_players})"
                )
            connection = PlayerConnection(
                player_id=player_id,
                session_id=session_id,
                state=ConnectionState.CONNECTING,
                ip_address=ip_address,
                connected_at=time.time(),
                last_heartbeat=time.time(),
            )
            # Simulate connection handshake and ping measurement
            connection.ping_ms = self._simulate_ping(session.topology)
            connection.packet_loss = self._simulate_packet_loss_rate()
            connection.state = ConnectionState.CONNECTED
            self._connections[connection.connection_id] = connection
            self._session_connections[session_id].append(connection.connection_id)
            session.current_players = len(self._session_connections[session_id])
            # Assign a default skill rating if not already present
            if player_id not in self._player_skill_ratings:
                self._player_skill_ratings[player_id] = random.uniform(800.0, 1200.0)
        return connection

    def disconnect_player(
        self,
        session_id: str,
        player_id: str,
    ) -> PlayerConnection:
        """Disconnect a player from a session.

        Sets the connection state to DISCONNECTED and updates the session
        player count. Returns the last known connection state.

        Args:
            session_id: Session to disconnect from.
            player_id: Player to disconnect.

        Returns:
            The updated PlayerConnection.

        Raises:
            KeyError: If the session or player connection is not found.
        """
        self._get_session(session_id)
        connection = self._find_connection_by_player(session_id, player_id)
        if connection is None:
            raise KeyError(
                f"Player {player_id} not found in session {session_id}"
            )
        with self._lock:
            connection.state = ConnectionState.DISCONNECTED
            connection.last_heartbeat = time.time()
            if connection.connection_id in self._session_connections.get(session_id, []):
                self._session_connections[session_id].remove(connection.connection_id)
            session = self._sessions[session_id]
            session.current_players = len(self._session_connections[session_id])
        return connection

    def _find_connection_by_player(
        self, session_id: str, player_id: str
    ) -> Optional[PlayerConnection]:
        """Find a player's connection within a session."""
        for conn_id in self._session_connections.get(session_id, []):
            conn = self._connections.get(conn_id)
            if conn and conn.player_id == player_id:
                return conn
        return None

    def get_player_connection(
        self, session_id: str, player_id: str
    ) -> Optional[PlayerConnection]:
        """Retrieve the connection for a player in a session."""
        return self._find_connection_by_player(session_id, player_id)

    # -----------------------------------------------------------------------
    # Packet Transmission
    # -----------------------------------------------------------------------

    def send_packet(
        self,
        session_id: str,
        sender_id: str,
        data: Dict[str, Any],
        reliable: bool = True,
    ) -> SyncPacket:
        """Send a packet through the simulated network layer.

        Applies simulated latency, jitter, and packet loss. Increments
        the session sequence counter. Tracks total bytes sent.

        Args:
            session_id: Target session.
            sender_id: Originator of the packet.
            data: Payload to transmit.
            reliable: Whether the packet requires acknowledgment.

        Returns:
            The SyncPacket that was queued for transmission.

        Raises:
            KeyError: If the session does not exist.
        """
        self._get_session(session_id)
        with self._lock:
            seq = self._sequence_counters.get(session_id, 0) + 1
            self._sequence_counters[session_id] = seq
            payload_json = json.dumps(data, default=str)
            size_bytes = len(payload_json.encode("utf-8"))
            packet = SyncPacket(
                session_id=session_id,
                sender_id=sender_id,
                sequence=seq,
                data=data,
                size_bytes=size_bytes,
                reliable=reliable,
            )
            # Simulate packet loss
            loss_rate = self._simulated_packet_loss
            if loss_rate > 0 and random.random() < loss_rate:
                self._total_packets_lost += 1
                return packet
            self._session_packets.setdefault(session_id, []).append(packet)
            self._total_packets_sent += 1
            self._total_bytes_sent += size_bytes
        return packet

    def get_pending_packets(self, session_id: str) -> List[SyncPacket]:
        """Retrieve all packets queued for a session since last retrieval."""
        self._get_session(session_id)
        with self._lock:
            packets = list(self._session_packets.get(session_id, []))
            self._session_packets[session_id] = []
        return packets

    # -----------------------------------------------------------------------
    # State Synchronization
    # -----------------------------------------------------------------------

    def synchronize_state(self, session_id: str) -> Dict[str, Any]:
        """Synchronize game state for a session using the configured strategy.

        Performs both full-state and delta synchronization, then compares
        the two approaches to report efficiency metrics. Updates entity
        version tracking and delta caches for subsequent syncs.

        Args:
            session_id: Session to synchronize.

        Returns:
            Dict with sync results, entity counts, delta stats, and strategy used.
        """
        session = self._get_session(session_id)
        entities = self._session_entities.get(session_id, {})
        versions = self._session_entity_versions.get(session_id, {})
        deltas = self._session_deltas.setdefault(session_id, {})

        # Build full state snapshot
        full_state: Dict[str, Any] = {}
        for entity_id, properties in entities.items():
            full_state[entity_id] = dict(properties)

        full_size = len(json.dumps(full_state, default=str).encode("utf-8"))

        # Compute delta: only entities that changed since last sync
        delta_state: Dict[str, Any] = {}
        changed_entities = 0
        for entity_id, properties in entities.items():
            current_version = versions.get(entity_id, 0)
            if entity_id not in deltas:
                # First sync: include full entity
                delta_state[entity_id] = dict(properties)
                deltas[entity_id] = dict(properties)
                changed_entities += 1
            else:
                previous = deltas[entity_id]
                diff = self._compute_entity_delta(previous, properties)
                if diff:
                    delta_state[entity_id] = diff
                    deltas[entity_id] = dict(properties)
                    changed_entities += 1
            versions[entity_id] = current_version + 1

        delta_size = len(json.dumps(delta_state, default=str).encode("utf-8"))

        # Store snapshot for interpolation
        tick = self._tick_counters.get(session_id, 0)
        snapshots = self._session_state_snapshots.setdefault(session_id, {})
        snapshots[tick] = dict(full_state)

        # Keep last 60 snapshots
        if len(snapshots) > 60:
            oldest = min(snapshots.keys())
            del snapshots[oldest]

        return {
            "session_id": session_id,
            "strategy": session.sync_strategy.value,
            "tick": tick,
            "total_entities": len(entities),
            "changed_entities": changed_entities,
            "full_state_size_bytes": full_size,
            "delta_state_size_bytes": delta_size,
            "compression_ratio": (
                round(delta_size / max(1, full_size), 4)
            ),
            "delta_entities": list(delta_state.keys()),
            "timestamp": time.time(),
        }

    def _compute_entity_delta(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute the difference between two entity state snapshots.

        Returns a dict containing only the properties that have changed.
        If nothing changed, returns an empty dict.
        """
        delta: Dict[str, Any] = {}
        for key, value in current.items():
            prev_value = previous.get(key)
            if prev_value != value:
                delta[key] = value
        return delta

    def interpolate_state(
        self,
        session_id: str,
        player_id: str,
        tick: int,
    ) -> Dict[str, Any]:
        """Interpolate game state between two known snapshots for a given tick.

        Used for client-side rendering to smooth out state received from
        the server. Finds the two snapshots bracketing the requested tick
        and linearly interpolates entity properties.

        Args:
            session_id: Session to interpolate for.
            player_id: Player requesting the interpolation.
            tick: Target simulation tick to interpolate to.

        Returns:
            Dict with interpolated entity states and interpolation metadata.
        """
        self._get_session(session_id)
        snapshots = self._session_state_snapshots.get(session_id, {})

        if not snapshots:
            return {
                "session_id": session_id,
                "player_id": player_id,
                "tick": tick,
                "interpolated": False,
                "reason": "no_snapshots_available",
                "state": {},
            }

        tick_keys = sorted(snapshots.keys())
        previous_tick = None
        next_tick = None

        for t in tick_keys:
            if t <= tick:
                previous_tick = t
            if t >= tick and next_tick is None:
                next_tick = t

        if previous_tick is None:
            previous_tick = tick_keys[0]
        if next_tick is None:
            next_tick = tick_keys[-1]

        if previous_tick == next_tick:
            return {
                "session_id": session_id,
                "player_id": player_id,
                "tick": tick,
                "interpolated": False,
                "reason": "exact_tick_match",
                "snapshot_tick": previous_tick,
                "state": snapshots[previous_tick],
            }

        prev_state = snapshots[previous_tick]
        next_state = snapshots[next_tick]
        tick_range = next_tick - previous_tick
        alpha = (tick - previous_tick) / max(1, tick_range)

        interpolated: Dict[str, Any] = {}
        all_entity_ids = set(prev_state.keys()) | set(next_state.keys())
        for entity_id in all_entity_ids:
            prev_entity = prev_state.get(entity_id, {})
            next_entity = next_state.get(entity_id, {})
            interpolated_entity: Dict[str, Any] = {}
            all_keys = set(prev_entity.keys()) | set(next_entity.keys())
            for key in all_keys:
                pv = prev_entity.get(key)
                nv = next_entity.get(key)
                if isinstance(pv, (int, float)) and isinstance(nv, (int, float)):
                    interpolated_entity[key] = pv + (nv - pv) * alpha
                elif alpha < 0.5:
                    interpolated_entity[key] = pv
                else:
                    interpolated_entity[key] = nv
            interpolated[entity_id] = interpolated_entity

        return {
            "session_id": session_id,
            "player_id": player_id,
            "tick": tick,
            "interpolated": True,
            "previous_tick": previous_tick,
            "next_tick": next_tick,
            "alpha": round(alpha, 4),
            "state": interpolated,
        }

    def predict_state(
        self,
        session_id: str,
        player_id: str,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform client-side prediction of game state based on player inputs.

        Takes the last known authoritative state and extrapolates forward
        using the provided input data. Simulates physics integration for
        position, velocity, and rotation properties.

        Args:
            session_id: Session to predict for.
            player_id: Player whose state is being predicted.
            inputs: Input data (e.g., movement direction, actions).

        Returns:
            Dict with predicted entity states, confidence score, and metadata.
        """
        self._get_session(session_id)
        entities = self._session_entities.get(session_id, {})

        # Find the player's own entity
        player_entity_id = None
        for entity_id, props in entities.items():
            if props.get("owner_id") == player_id or props.get("player_id") == player_id:
                player_entity_id = entity_id
                break

        if player_entity_id is None:
            return {
                "session_id": session_id,
                "player_id": player_id,
                "predicted": False,
                "reason": "no_player_entity_found",
                "state": {},
            }

        last_state = dict(entities.get(player_entity_id, {}))
        connection = self._find_connection_by_player(session_id, player_id)
        ping_ms = connection.ping_ms if connection else 50.0

        # Predict forward by ping-based time offset
        predict_seconds = ping_ms / 1000.0
        predicted: Dict[str, Any] = dict(last_state)

        # Apply input-based prediction
        move_x = float(inputs.get("move_x", 0.0))
        move_y = float(inputs.get("move_y", 0.0))
        speed = float(last_state.get("speed", 1.0))

        if move_x != 0.0 or move_y != 0.0:
            magnitude = math.sqrt(move_x * move_x + move_y * move_y)
            if magnitude > 0:
                move_x /= magnitude
                move_y /= magnitude

            pos_x = float(last_state.get("x", last_state.get("position_x", 0.0)))
            pos_y = float(last_state.get("y", last_state.get("position_y", 0.0)))
            vel_x = float(last_state.get("velocity_x", 0.0))
            vel_y = float(last_state.get("velocity_y", 0.0))

            predicted["x"] = pos_x + move_x * speed * predict_seconds
            predicted["y"] = pos_y + move_y * speed * predict_seconds
            predicted["position_x"] = predicted["x"]
            predicted["position_y"] = predicted["y"]
            predicted["velocity_x"] = move_x * speed
            predicted["velocity_y"] = move_y * speed

        # Confidence decays with prediction distance
        confidence = max(0.0, 1.0 - predict_seconds * 2.0)

        return {
            "session_id": session_id,
            "player_id": player_id,
            "predicted": True,
            "entity_id": player_entity_id,
            "predict_seconds": round(predict_seconds, 4),
            "ping_ms": round(ping_ms, 1),
            "confidence": round(confidence, 4),
            "state": predicted,
            "inputs_applied": {
                "move_x": move_x,
                "move_y": move_y,
            },
        }

    def compensate_latency(
        self,
        session_id: str,
        player_id: str,
    ) -> Dict[str, Any]:
        """Analyze latency and recommend compensation adjustments.

        Measures the player's ping, jitter, and packet loss. Suggests
        tick rate adjustments, sync strategy changes, and interpolation
        buffer sizes to mitigate latency effects.

        Args:
            session_id: Session to analyze.
            player_id: Player to analyze latency for.

        Returns:
            Dict with latency metrics, compensation suggestions, and
            recommended configuration changes.
        """
        session = self._get_session(session_id)
        connection = self._find_connection_by_player(session_id, player_id)
        if connection is None:
            return {
                "session_id": session_id,
                "player_id": player_id,
                "compensated": False,
                "reason": "player_not_connected",
            }

        ping_ms = connection.ping_ms
        packet_loss = connection.packet_loss
        jitter = self._simulated_jitter_ms

        # Determine recommended tick rate based on ping
        if ping_ms < 20:
            suggested_tick_rate = 60
        elif ping_ms < 50:
            suggested_tick_rate = 30
        elif ping_ms < 100:
            suggested_tick_rate = 20
        else:
            suggested_tick_rate = 10

        # Determine interpolation buffer size (in ticks)
        if ping_ms < 30:
            interpolation_buffer = 2
        elif ping_ms < 80:
            interpolation_buffer = 3
        elif ping_ms < 150:
            interpolation_buffer = 5
        else:
            interpolation_buffer = 8

        # Suggest sync strategy changes
        strategy_suggestion = session.sync_strategy
        if ping_ms > 100 and session.sync_strategy == SyncStrategy.FULL_STATE:
            strategy_suggestion = SyncStrategy.DELTA
        elif ping_ms > 200:
            strategy_suggestion = SyncStrategy.SNAPSHOT

        # Adjust tick rate if needed
        current_tick_rate = self._session_tick_rates.get(session_id, session.tick_rate)
        self._session_tick_rates[session_id] = suggested_tick_rate

        # Quality assessment
        if ping_ms < 30 and packet_loss < 0.01:
            quality = "excellent"
        elif ping_ms < 80 and packet_loss < 0.05:
            quality = "good"
        elif ping_ms < 150 and packet_loss < 0.10:
            quality = "fair"
        elif ping_ms < 300 and packet_loss < 0.25:
            quality = "poor"
        else:
            quality = "unplayable"

        return {
            "session_id": session_id,
            "player_id": player_id,
            "compensated": True,
            "ping_ms": round(ping_ms, 1),
            "jitter_ms": round(jitter, 1),
            "packet_loss": round(packet_loss, 4),
            "connection_quality": quality,
            "current_tick_rate": current_tick_rate,
            "suggested_tick_rate": suggested_tick_rate,
            "interpolation_buffer_ticks": interpolation_buffer,
            "current_strategy": session.sync_strategy.value,
            "suggested_strategy": strategy_suggestion.value,
            "recommendations": self._build_latency_recommendations(
                ping_ms, packet_loss, quality
            ),
        }

    def _build_latency_recommendations(
        self,
        ping_ms: float,
        packet_loss: float,
        quality: str,
    ) -> List[str]:
        """Build human-readable latency compensation recommendations."""
        recs: List[str] = []
        if ping_ms > 100:
            recs.append("Reduce tick rate to lower bandwidth usage")
        if packet_loss > 0.05:
            recs.append("Increase reliable packet ratio for critical state")
        if quality in ("poor", "unplayable"):
            recs.append("Consider switching to snapshot-based sync")
        if ping_ms > 50:
            recs.append("Enable client-side prediction for responsive input")
        if ping_ms > 30:
            recs.append("Increase interpolation buffer to smooth jitter")
        if not recs:
            recs.append("Connection quality is optimal; no changes needed")
        return recs

    # -----------------------------------------------------------------------
    # Matchmaking
    # -----------------------------------------------------------------------

    def create_matchmaking_query(
        self,
        player_id: str,
        preferences: Dict[str, Any],
        skill_range: float = 200.0,
        region: str = "default",
    ) -> MatchmakingQuery:
        """Create a matchmaking query for a player seeking a game.

        Adds the player to the matchmaking pool with their skill rating
        and preferences. The query is queued for matching.

        Args:
            player_id: Player seeking a match.
            preferences: Game-mode, map, and rule preferences.
            skill_range: Acceptable skill deviation from player's rating.
            region: Geographic region for latency grouping.

        Returns:
            The MatchmakingQuery that was created.
        """
        query = MatchmakingQuery(
            player_id=player_id,
            preferences=preferences,
            skill_range=skill_range,
            region=region,
        )
        with self._lock:
            self._matchmaking_queue[query.query_id] = query
            if player_id not in self._player_skill_ratings:
                self._player_skill_ratings[player_id] = random.uniform(800.0, 1200.0)
            self._matchmaking_pool[player_id] = {
                "query_id": query.query_id,
                "skill_rating": self._player_skill_ratings[player_id],
                "preferences": preferences,
                "region": region,
                "skill_range": skill_range,
                "entered_at": query.created_at,
            }
        return query

    def find_match(self, query_id: str) -> Dict[str, Any]:
        """Find a match for the given query from the matchmaking pool.

        Matches players based on skill proximity, region, preference
        overlap, and wait time. Players with longer wait times receive
        progressively wider skill range tolerance.

        Args:
            query_id: The matchmaking query to find a match for.

        Returns:
            Dict with match results, matched players, and scoring metadata.
        """
        query = self._matchmaking_queue.get(query_id)
        if query is None:
            return {
                "query_id": query_id,
                "matched": False,
                "reason": "query_not_found",
            }

        player_id = query.player_id
        player_skill = self._player_skill_ratings.get(player_id, 1000.0)
        player_region = query.region
        player_prefs = query.preferences

        # Expand skill range based on wait time
        wait_seconds = time.time() - query.created_at
        wait_factor = 1.0 + (wait_seconds / 30.0)  # Expand every 30 seconds
        effective_skill_range = query.skill_range * wait_factor

        candidates: List[Tuple[str, float]] = []
        for other_id, other_data in self._matchmaking_pool.items():
            if other_id == player_id:
                continue
            if other_data.get("region", "default") != player_region:
                continue

            other_skill = other_data.get("skill_rating", 1000.0)
            skill_diff = abs(player_skill - other_skill)
            if skill_diff > effective_skill_range:
                continue

            # Score based on skill proximity and preference overlap
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
                "query_id": query_id,
                "player_id": player_id,
                "matched": False,
                "reason": "no_suitable_candidates",
                "wait_seconds": round(wait_seconds, 1),
                "skill_rating": player_skill,
                "effective_skill_range": round(effective_skill_range, 1),
                "pool_size": len(self._matchmaking_pool) - 1,
            }

        candidates.sort(key=lambda x: x[1], reverse=True)
        best_match_id, best_score = candidates[0]

        # Generate a new session for the matched players
        session = self.create_session(
            name=f"Match_{player_id[:8]}_{best_match_id[:8]}",
            topology=NetworkTopology.AUTHORITATIVE_SERVER,
            max_players=4,
            sync_strategy=SyncStrategy.FULL_STATE,
            tick_rate=30,
        )

        # Clean up both players from pool
        with self._lock:
            self._matchmaking_queue.pop(query_id, None)
            self._matchmaking_pool.pop(player_id, None)
            matched_query_id = self._matchmaking_pool.get(best_match_id, {}).get("query_id", "")
            if matched_query_id:
                self._matchmaking_queue.pop(matched_query_id, None)
            self._matchmaking_pool.pop(best_match_id, None)

        return {
            "query_id": query_id,
            "player_id": player_id,
            "matched": True,
            "matched_player_id": best_match_id,
            "match_score": round(best_score, 4),
            "skill_diff": round(abs(player_skill - self._player_skill_ratings.get(best_match_id, 1000.0)), 1),
            "session_id": session.session_id,
            "session_name": session.name,
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
        keys_a = set(prefs_a.keys())
        keys_b = set(prefs_b.keys())
        common_keys = keys_a & keys_b
        if not common_keys:
            return 0.1  # Slight baseline for non-empty preferences
        matches = 0
        for key in common_keys:
            if prefs_a[key] == prefs_b[key]:
                matches += 1
        return matches / len(common_keys)

    # -----------------------------------------------------------------------
    # Stats and Reporting
    # -----------------------------------------------------------------------

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get detailed statistics for a specific session.

        Includes player counts, connection states, packet metrics,
        entity counts, and sync strategy information.

        Args:
            session_id: Session to get stats for.

        Returns:
            Dict with comprehensive session statistics.
        """
        session = self._get_session(session_id)
        conn_ids = self._session_connections.get(session_id, [])
        connections = [self._connections[cid] for cid in conn_ids if cid in self._connections]

        connected_count = sum(
            1 for c in connections if c.state == ConnectionState.CONNECTED
        )
        total_ping = sum(c.ping_ms for c in connections)
        avg_ping = total_ping / max(1, len(connections))
        total_packet_loss = sum(c.packet_loss for c in connections)
        avg_packet_loss = total_packet_loss / max(1, len(connections))

        entities = self._session_entities.get(session_id, {})
        snapshots = self._session_state_snapshots.get(session_id, {})
        sequence = self._sequence_counters.get(session_id, 0)
        tick = self._tick_counters.get(session_id, 0)

        return {
            "session_id": session_id,
            "name": session.name,
            "topology": session.topology.value,
            "sync_strategy": session.sync_strategy.value,
            "state": session.state,
            "tick_rate": self._session_tick_rates.get(session_id, session.tick_rate),
            "tick_count": tick,
            "max_players": session.max_players,
            "current_players": session.current_players,
            "connected_players": connected_count,
            "total_connections": len(connections),
            "total_entities": len(entities),
            "total_snapshots": len(snapshots),
            "total_packets": sequence,
            "avg_ping_ms": round(avg_ping, 1),
            "avg_packet_loss": round(avg_packet_loss, 4),
            "session_age_seconds": round(time.time() - session.created_at, 1),
            "connection_details": [c.to_dict() for c in connections],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics across all sessions.

        Includes session counts, total packet metrics, matchmaking pool
        size, and simulated network conditions.

        Returns:
            Dict with aggregate networking statistics.
        """
        total_players = sum(
            len(conns) for conns in self._session_connections.values()
        )
        total_entities = sum(
            len(entities) for entities in self._session_entities.values()
        )
        total_sequences = sum(self._sequence_counters.values())
        total_ticks = sum(self._tick_counters.values())

        active_sessions = sum(
            1 for s in self._sessions.values() if s.state == "live"
        )
        lobby_sessions = sum(
            1 for s in self._sessions.values() if s.state == "lobby"
        )

        all_connections: List[PlayerConnection] = []
        for conn_ids in self._session_connections.values():
            for cid in conn_ids:
                if cid in self._connections:
                    all_connections.append(self._connections[cid])

        connected_count = sum(
            1 for c in all_connections if c.state == ConnectionState.CONNECTED
        )
        total_ping = sum(c.ping_ms for c in all_connections if c.ping_ms > 0)
        ping_count = sum(1 for c in all_connections if c.ping_ms > 0)
        avg_ping = total_ping / max(1, ping_count)

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active_sessions,
            "lobby_sessions": lobby_sessions,
            "total_connections": len(all_connections),
            "connected_players": connected_count,
            "total_players_tracked": total_players,
            "total_entities": total_entities,
            "total_packets_sent": self._total_packets_sent,
            "total_packets_lost": self._total_packets_lost,
            "total_bytes_sent": self._total_bytes_sent,
            "total_sequences": total_sequences,
            "total_ticks": total_ticks,
            "matchmaking_pool_size": len(self._matchmaking_pool),
            "matchmaking_queue_size": len(self._matchmaking_queue),
            "avg_ping_ms": round(avg_ping, 1),
            "simulated_latency_ms": self._simulated_latency_ms,
            "simulated_packet_loss": round(self._simulated_packet_loss, 4),
            "simulated_jitter_ms": self._simulated_jitter_ms,
        }

    # -----------------------------------------------------------------------
    # Entity State Management (internal helpers)
    # -----------------------------------------------------------------------

    def _set_entity_state(
        self,
        session_id: str,
        entity_id: str,
        properties: Dict[str, Any],
    ) -> None:
        """Set or update the state of an entity within a session.

        Args:
            session_id: Session the entity belongs to.
            entity_id: Unique entity identifier.
            properties: Entity properties to set.
        """
        self._get_session(session_id)
        with self._lock:
            entities = self._session_entities.setdefault(session_id, {})
            if entity_id in entities:
                entities[entity_id].update(properties)
            else:
                entities[entity_id] = dict(properties)

    def _get_entity_state(
        self,
        session_id: str,
        entity_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the current state of an entity within a session."""
        entities = self._session_entities.get(session_id, {})
        return entities.get(entity_id)

    def _remove_entity_state(
        self,
        session_id: str,
        entity_id: str,
    ) -> bool:
        """Remove an entity's state from a session.

        Returns True if the entity was removed, False if it did not exist.
        """
        entities = self._session_entities.get(session_id, {})
        if entity_id in entities:
            with self._lock:
                del entities[entity_id]
                self._session_deltas.get(session_id, {}).pop(entity_id, None)
                self._session_entity_versions.get(session_id, {}).pop(entity_id, None)
            return True
        return False

    # -----------------------------------------------------------------------
    # Network Simulation
    # -----------------------------------------------------------------------

    def set_simulation_conditions(
        self,
        latency_ms: float = 0.0,
        packet_loss_pct: float = 0.0,
        jitter_ms: float = 0.0,
    ) -> None:
        """Configure simulated network conditions for testing.

        Args:
            latency_ms: Simulated one-way latency in milliseconds.
            packet_loss_pct: Percentage of packets to drop (0-100).
            jitter_ms: Random latency variation in milliseconds.
        """
        self._simulated_latency_ms = max(0.0, latency_ms)
        self._simulated_packet_loss = max(0.0, min(1.0, packet_loss_pct / 100.0))
        self._simulated_jitter_ms = max(0.0, jitter_ms)

    def _simulate_ping(self, topology: NetworkTopology) -> float:
        """Simulate a realistic ping measurement based on topology.

        Different topologies imply different latency profiles:
        - DEDICATED_SERVER: moderate, stable ping
        - PEER_TO_PEER: variable, depends on peer distance
        - AUTHORITATIVE_SERVER: server-dependent latency
        - CLIENT_SERVER: host-based, lower for host
        - HYBRID: mixed, moderate latency
        """
        base_latency = self._simulated_latency_ms
        if topology == NetworkTopology.DEDICATED_SERVER:
            base_latency += random.uniform(15, 60)
        elif topology == NetworkTopology.PEER_TO_PEER:
            base_latency += random.uniform(5, 80)
        elif topology == NetworkTopology.AUTHORITATIVE_SERVER:
            base_latency += random.uniform(20, 90)
        elif topology == NetworkTopology.HYBRID:
            base_latency += random.uniform(10, 70)
        else:
            base_latency += random.uniform(5, 50)
        # Add jitter
        jitter = random.uniform(-self._simulated_jitter_ms, self._simulated_jitter_ms)
        return max(0.0, base_latency + jitter)

    def _simulate_packet_loss_rate(self) -> float:
        """Simulate a packet loss rate for a new connection."""
        if self._simulated_packet_loss > 0:
            return self._simulated_packet_loss * random.uniform(0.5, 1.5)
        return max(0.0, random.uniform(0.0, 0.02))

    def tick(self, delta_time: float = 0.016) -> None:
        """Advance the network simulation by one frame.

        Updates tick counters, processes heartbeats, and detects
        timeout conditions for inactive connections.

        Args:
            delta_time: Time elapsed since last tick in seconds.
        """
        with self._lock:
            for session_id in list(self._sessions.keys()):
                tick = self._tick_counters.get(session_id, 0) + 1
                self._tick_counters[session_id] = tick

                # Heartbeat check for connections
                conn_ids = self._session_connections.get(session_id, [])
                now = time.time()
                for cid in conn_ids:
                    conn = self._connections.get(cid)
                    if conn is None:
                        continue
                    if conn.state == ConnectionState.CONNECTED:
                        heartbeat_age = now - conn.last_heartbeat
                        if heartbeat_age > 30.0:
                            conn.state = ConnectionState.TIMEOUT
                        elif heartbeat_age > 15.0:
                            conn.ping_ms = self._simulate_ping(
                                self._sessions[session_id].topology
                            )
                            conn.last_heartbeat = now

    # -----------------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire network layer to its initial state."""
        with self._lock:
            self._sessions.clear()
            self._connections.clear()
            self._session_connections.clear()
            self._session_entities.clear()
            self._session_entity_versions.clear()
            self._session_deltas.clear()
            self._session_state_snapshots.clear()
            self._session_packets.clear()
            self._sequence_counters.clear()
            self._tick_counters.clear()
            self._matchmaking_queue.clear()
            self._matchmaking_pool.clear()
            self._player_skill_ratings.clear()
            self._session_tick_rates.clear()
            self._total_packets_sent = 0
            self._total_packets_lost = 0
            self._total_bytes_sent = 0


# ---------------------------------------------------------------------------
# Module-level convenience accessor
# ---------------------------------------------------------------------------


def get_network_layer_engine() -> NetworkLayerEngine:
    """Return the singleton instance of NetworkLayerEngine."""
    return NetworkLayerEngine.get_instance()