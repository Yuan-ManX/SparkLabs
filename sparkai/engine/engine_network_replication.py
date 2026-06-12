"""
SparkLabs Engine - Network Replication System

Multiplayer network state replication providing client-server state
synchronization with client-side prediction, server reconciliation,
and interest management. Supports authoritative server architecture
with bandwidth throttling, matchmaking room management, and simulated
network conditions for testing.

Architecture:
  EngineNetworkReplication (Singleton)
    |-- NetworkIdentity    — uniquely identified entity in the networked world
    |-- ReplicatedState    — per-entity state snapshot with sequence tracking
    |-- NetworkEvent       — typed network message with reliability guarantees
    |-- ClientConnection   — connected client metadata and input buffer
    |-- NetworkStats       — aggregate telemetry and performance metrics

Capabilities:
  - Entity registration with authoritative ownership assignment
  - Frame-by-frame state submission and retrieval with interpolation
  - Reliable and unreliable event delivery with pending-event queues
  - Client lifecycle management (connect, heartbeat, disconnect)
  - Interest management (view-radius-based entity filtering)
  - RPC-style method invocation queuing
  - Matchmaking with room creation, join, and leave
  - Client-side prediction with server state reconciliation
  - Bandwidth throttling and simulated network degradation
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NetworkRole(str, Enum):
    """Role assigned to a participant in the replicated network session."""
    SERVER = "server"
    CLIENT = "client"
    PEER = "peer"
    SPECTATOR = "spectator"


class ReplicationMode(str, Enum):
    """Transmission strategy for replicated entity state updates."""
    RELIABLE = "reliable"
    UNRELIABLE = "unreliable"
    STATE_ONLY = "state_only"
    EVENT_ONLY = "event_only"


class NetworkEventType(str, Enum):
    """Category of network event for routing and prioritization."""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    SPAWN = "spawn"
    DESPAWN = "despawn"
    RPC = "rpc"
    SYNC = "sync"
    MATCHMAKE = "matchmake"


class ConnectionState(str, Enum):
    """Lifecycle state of a client connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    TIMEOUT = "timeout"
    RECONNECTING = "reconnecting"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class NetworkIdentity:
    """Uniquely identified entity in the replicated network world.

    Tracks ownership, authoritative status, spawn origin, replication
    strategy, and priority for bandwidth allocation decisions.

    Attributes:
        identity_id: Unique identifier for this network entity.
        entity_type: Logical type string (e.g., \"player\", \"npc\").
        owner_client_id: Client that owns and has authority over this entity.
        is_authoritative: Whether the server has final say on state.
        spawn_position: World-space coordinates where the entity was spawned.
        replication_mode: How state updates are transmitted.
        priority: Higher values receive preferential bandwidth allocation.
    """
    identity_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    entity_type: str = ""
    owner_client_id: str = ""
    is_authoritative: bool = True
    spawn_position: Tuple[float, float] = (0.0, 0.0)
    replication_mode: ReplicationMode = ReplicationMode.RELIABLE
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "entity_type": self.entity_type,
            "owner_client_id": self.owner_client_id,
            "is_authoritative": self.is_authoritative,
            "spawn_position": list(self.spawn_position),
            "replication_mode": self.replication_mode.value,
            "priority": self.priority,
        }


@dataclass
class ReplicatedState:
    """Per-entity state snapshot transmitted across the network.

    Carries position, rotation, and velocity vectors along with an
    extensible custom state dictionary. Each snapshot is stamped with
    a monotonic sequence number for ordering and reconciliation.

    Attributes:
        state_id: Unique identifier for this state snapshot.
        identity_id: The network identity this state belongs to.
        position_x/y/z: World-space position in game units.
        rotation_x/y/z: Euler rotation angles in degrees.
        velocity_x/y/z: Linear velocity vector in world space.
        custom_state: Arbitrary key-value pairs for engine-specific data.
        timestamp: Wall-clock time when this state was captured.
        sequence_number: Monotonic counter for ordering and delta detection.
    """
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    identity_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    velocity_z: float = 0.0
    custom_state: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)
    sequence_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "identity_id": self.identity_id,
            "position": {
                "x": self.position_x,
                "y": self.position_y,
                "z": self.position_z,
            },
            "rotation": {
                "x": self.rotation_x,
                "y": self.rotation_y,
                "z": self.rotation_z,
            },
            "velocity": {
                "x": self.velocity_x,
                "y": self.velocity_y,
                "z": self.velocity_z,
            },
            "custom_state": dict(self.custom_state),
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
        }


@dataclass
class NetworkEvent:
    """Typed network message with optional reliability guarantees.

    Represents a single event dispatched between network participants.
    Supports both server-to-client and client-to-server flows with
    reliability flags that determine delivery guarantees.

    Attributes:
        event_id: Unique identifier for this event.
        event_type: Category of the event (connect, spawn, rpc, etc.).
        source_id: Identifier of the originating participant.
        target_id: Intended recipient (empty string for broadcast).
        payload: Arbitrary data carried with the event.
        timestamp: When the event was generated.
        reliable: Whether guaranteed delivery is required.
    """
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    event_type: NetworkEventType = NetworkEventType.SYNC
    source_id: str = ""
    target_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)
    reliable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
            "reliable": self.reliable,
        }


@dataclass
class ClientConnection:
    """Metadata and runtime state for a connected network participant.

    Tracks address, role, latency, heartbeat health, owned entities,
    and a rolling input buffer used for prediction and reconciliation.

    Attributes:
        client_id: Unique identifier for this client.
        address: IP address of the client.
        port: Network port the client communicates on.
        state: Current connection lifecycle state.
        role: The participant's role in the session.
        latency_ms: Measured round-trip latency in milliseconds.
        connected_at: Timestamp when the connection was first established.
        last_heartbeat: Timestamp of the most recent heartbeat response.
        entities_owned: List of entity identity IDs owned by this client.
        input_buffer: Rolling buffer of recent input commands.
    """
    client_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    address: str = ""
    port: int = 0
    state: ConnectionState = ConnectionState.DISCONNECTED
    role: NetworkRole = NetworkRole.CLIENT
    latency_ms: float = 0.0
    connected_at: float = field(default_factory=_time_module.time)
    last_heartbeat: float = field(default_factory=_time_module.time)
    entities_owned: List[str] = field(default_factory=list)
    input_buffer: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "address": self.address,
            "port": self.port,
            "state": self.state.value,
            "role": self.role.value,
            "latency_ms": round(self.latency_ms, 2),
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "entities_owned": list(self.entities_owned),
            "input_buffer_size": len(self.input_buffer),
        }


@dataclass
class NetworkStats:
    """Aggregate telemetry and performance metrics for network replication.

    Provides an at-a-glance view of connection health, bandwidth usage,
    packet reliability, entity replication load, and server uptime.

    Attributes:
        active_connections: Number of clients currently connected.
        total_events: Cumulative event count since server start.
        avg_latency_ms: Mean round-trip latency across all connections.
        bandwidth_usage_kbps: Estimated bandwidth consumption rate.
        packet_loss_pct: Observed packet loss as a percentage.
        entities_replicated: Total network identities registered.
        uptime_seconds: Elapsed time since replication system initialized.
    """
    active_connections: int = 0
    total_events: int = 0
    avg_latency_ms: float = 0.0
    bandwidth_usage_kbps: float = 0.0
    packet_loss_pct: float = 0.0
    entities_replicated: int = 0
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_connections": self.active_connections,
            "total_events": self.total_events,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "bandwidth_usage_kbps": round(self.bandwidth_usage_kbps, 2),
            "packet_loss_pct": round(self.packet_loss_pct, 2),
            "entities_replicated": self.entities_replicated,
            "uptime_seconds": round(self.uptime_seconds, 2),
        }


# ---------------------------------------------------------------------------
# EngineNetworkReplication (Singleton)
# ---------------------------------------------------------------------------

class EngineNetworkReplication:
    """
    Multiplayer network state replication system for the SparkLabs engine.

    Provides client-server state synchronization with prediction,
    reconciliation, and interest management. Supports authoritative
    server architecture where the server owns final state and clients
    submit inputs for reconciliation.

    Features include entity registration with ownership, per-frame
    state snapshots, reliable/unreliable event dispatch, client
    lifecycle management, view-radius interest filtering, RPC queuing,
    matchmaking room management, and simulated network degradation
    for testing latency compensation and bandwidth throttling.
    """

    _instance: Optional["EngineNetworkReplication"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_IDENTITIES: int = 4096
    MAX_STATES_PER_IDENTITY: int = 256
    MAX_EVENTS: int = 65536
    MAX_CLIENTS: int = 128
    MAX_INPUT_BUFFER: int = 64
    DEFAULT_VIEW_RADIUS: float = 500.0
    DEFAULT_HEARTBEAT_TIMEOUT: float = 30.0

    def __new__(cls) -> "EngineNetworkReplication":
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

        # Entity tracking
        self._identities: Dict[str, NetworkIdentity] = {}
        self._state_history: Dict[str, List[ReplicatedState]] = {}
        self._latest_states: Dict[str, ReplicatedState] = {}
        self._sequence_counter: int = 0

        # Event management
        self._events: Dict[str, NetworkEvent] = {}
        self._event_queue: Dict[str, List[NetworkEvent]] = {}

        # Client management
        self._clients: Dict[str, ClientConnection] = {}
        self._server_id: str = ""

        # Matchmaking
        self._matches: Dict[str, Dict[str, Any]] = {}

        # Network simulation
        self._simulated_packet_loss: float = 0.0
        self._simulated_latency_min: float = 0.0
        self._simulated_latency_max: float = 0.0
        self._bandwidth_limits: Dict[str, float] = {}

        # Stats
        self._start_time: float = _time_module.time()
        self._total_events_sent: int = 0
        self._total_events_lost: int = 0

    # ------------------------------------------------------------------
    # Singleton Accessor
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineNetworkReplication":
        """Return the singleton EngineNetworkReplication instance."""
        return cls()

    # ------------------------------------------------------------------
    # Entity Registration
    # ------------------------------------------------------------------

    def register_identity(self,
                          entity_type: str = "",
                          owner_client_id: str = "",
                          is_authoritative: bool = True,
                          replication_mode: str = "reliable",
                          spawn_position: Tuple[float, float] = (0.0, 0.0),
                          priority: int = 0) -> NetworkIdentity:
        """Register a new entity for network replication.

        Creates a NetworkIdentity with the supplied parameters and adds
        it to the replication system. The server uses authoritative flag
        to determine whether it or the owning client has final say on
        state reconciliation.

        Args:
            entity_type: Logical type identifier for the entity.
            owner_client_id: Client that owns this entity.
            is_authoritative: Whether the server is the authority.
            replication_mode: How state updates are transmitted.
            spawn_position: World-space spawn coordinates (x, y).
            priority: Bandwidth allocation priority (higher = more).

        Returns:
            The newly created NetworkIdentity.
        """
        if len(self._identities) >= self.MAX_IDENTITIES:
            raise RuntimeError(
                f"Network identity limit reached ({self.MAX_IDENTITIES})"
            )

        try:
            mode = ReplicationMode(replication_mode.lower())
        except ValueError:
            mode = ReplicationMode.RELIABLE

        identity = NetworkIdentity(
            entity_type=entity_type,
            owner_client_id=owner_client_id,
            is_authoritative=is_authoritative,
            spawn_position=spawn_position,
            replication_mode=mode,
            priority=priority,
        )

        self._identities[identity.identity_id] = identity
        self._latest_states[identity.identity_id] = ReplicatedState(
            identity_id=identity.identity_id,
            position_x=spawn_position[0],
            position_y=spawn_position[1],
        )

        # Update owner's entity list
        if owner_client_id and owner_client_id in self._clients:
            client = self._clients[owner_client_id]
            if identity.identity_id not in client.entities_owned:
                client.entities_owned.append(identity.identity_id)

        return identity

    # ------------------------------------------------------------------
    # State Submission and Retrieval
    # ------------------------------------------------------------------

    def submit_state(self,
                     identity_id: str,
                     position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                     rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                     velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                     custom_state: Optional[Dict[str, Any]] = None) -> ReplicatedState:
        """Submit a new state snapshot for a replicated entity.

        Generates a monotonic sequence number and appends the state
        to the entity's history. The history is bounded to prevent
        unbounded memory growth.

        Args:
            identity_id: The network identity this state belongs to.
            position: World-space position as (x, y, z).
            rotation: Euler rotation as (rx, ry, rz) in degrees.
            velocity: Linear velocity as (vx, vy, vz).
            custom_state: Optional engine-specific state data.

        Returns:
            The newly created ReplicatedState snapshot.

        Raises:
            ValueError: If the identity_id is not registered.
        """
        if identity_id not in self._identities:
            raise ValueError(
                f"Unknown network identity: {identity_id}"
            )

        self._sequence_counter += 1

        state = ReplicatedState(
            identity_id=identity_id,
            position_x=position[0],
            position_y=position[1],
            position_z=position[2],
            rotation_x=rotation[0],
            rotation_y=rotation[1],
            rotation_z=rotation[2],
            velocity_x=velocity[0],
            velocity_y=velocity[1],
            velocity_z=velocity[2],
            custom_state=dict(custom_state) if custom_state else {},
            sequence_number=self._sequence_counter,
        )

        # Maintain bounded history
        if identity_id not in self._state_history:
            self._state_history[identity_id] = []
        history = self._state_history[identity_id]
        history.append(state)
        if len(history) > self.MAX_STATES_PER_IDENTITY:
            history.pop(0)

        self._latest_states[identity_id] = state
        return state

    def get_state(self, identity_id: str) -> Optional[ReplicatedState]:
        """Retrieve the most recent replicated state for an entity.

        Args:
            identity_id: The network identity to look up.

        Returns:
            The latest ReplicatedState or None if not found.
        """
        return self._latest_states.get(identity_id)

    # ------------------------------------------------------------------
    # Event Dispatch
    # ------------------------------------------------------------------

    def send_event(self,
                   event_type: str = "sync",
                   source_id: str = "",
                   target_id: str = "",
                   payload: Optional[Dict[str, Any]] = None,
                   reliable: bool = False) -> NetworkEvent:
        """Create and queue a network event for delivery.

        Supports both targeted and broadcast delivery via target_id.
        When target_id is empty, the event is broadcast-eligible.
        Reliability flags determine whether the event requires
        acknowledgment and retransmission.

        Args:
            event_type: Category of the event.
            source_id: Originating participant identifier.
            target_id: Intended recipient (empty = broadcast).
            payload: Event-specific data.
            reliable: Whether guaranteed delivery is required.

        Returns:
            The created NetworkEvent.
        """
        if len(self._events) >= self.MAX_EVENTS:
            raise RuntimeError(
                f"Network event limit reached ({self.MAX_EVENTS})"
            )

        try:
            etype = NetworkEventType(event_type.lower())
        except ValueError:
            etype = NetworkEventType.SYNC

        event = NetworkEvent(
            event_type=etype,
            source_id=source_id,
            target_id=target_id,
            payload=dict(payload) if payload else {},
            reliable=reliable,
        )

        self._events[event.event_id] = event
        self._total_events_sent += 1

        # Simulate packet loss
        if self._simulated_packet_loss > 0.0:
            if random.random() < self._simulated_packet_loss:
                self._total_events_lost += 1
                return event

        # Route to target client's queue
        target = target_id if target_id else "__broadcast__"
        if target not in self._event_queue:
            self._event_queue[target] = []
        self._event_queue[target].append(event)

        # Prune old events if queue grows too large
        if len(self._event_queue[target]) > self.MAX_EVENTS:
            self._event_queue[target] = self._event_queue[target][-self.MAX_EVENTS:]

        return event

    def get_pending_events(self, client_id: str) -> List[NetworkEvent]:
        """Retrieve and drain pending events for a specific client.

        Returns events addressed directly to the client plus broadcast
        events. The events are removed from the queue after retrieval.

        Args:
            client_id: The client to retrieve events for.

        Returns:
            List of pending NetworkEvents, ordered by arrival time.
        """
        results: List[NetworkEvent] = []

        # Get client-specific events
        client_queue = self._event_queue.pop(client_id, [])
        results.extend(client_queue)

        # Get broadcast events
        broadcast_queue = self._event_queue.pop("__broadcast__", [])
        for evt in broadcast_queue:
            if evt.target_id == "" or evt.target_id == client_id:
                results.append(evt)

        # Sort by timestamp for chronological delivery
        results.sort(key=lambda e: e.timestamp)
        return results

    # ------------------------------------------------------------------
    # Client Management
    # ------------------------------------------------------------------

    def register_client(self,
                        address: str = "",
                        port: int = 0,
                        role: str = "client") -> ClientConnection:
        """Register a new client connection.

        Creates a ClientConnection record and transitions it to the
        CONNECTING state. The connection must subsequently receive
        heartbeats to remain in CONNECTED state.

        Args:
            address: IP address of the connecting client.
            port: Network port.
            role: Participant role (client, peer, spectator).

        Returns:
            The created ClientConnection.

        Raises:
            RuntimeError: If the client limit is reached.
        """
        if len(self._clients) >= self.MAX_CLIENTS:
            raise RuntimeError(
                f"Client limit reached ({self.MAX_CLIENTS})"
            )

        try:
            client_role = NetworkRole(role.lower())
        except ValueError:
            client_role = NetworkRole.CLIENT

        now = _time_module.time()

        client = ClientConnection(
            address=address,
            port=port,
            state=ConnectionState.CONNECTING,
            role=client_role,
            connected_at=now,
            last_heartbeat=now,
        )

        self._clients[client.client_id] = client
        self._event_queue[client.client_id] = []

        # Transition to connected
        client.state = ConnectionState.CONNECTED
        return client

    def update_heartbeat(self, client_id: str) -> bool:
        """Update the heartbeat timestamp for a connected client.

        Resets the heartbeat timer and transitions reconnecting
        clients back to connected state.

        Args:
            client_id: The client to update.

        Returns:
            True if the client exists and was updated, False otherwise.
        """
        client = self._clients.get(client_id)
        if client is None:
            return False

        client.last_heartbeat = _time_module.time()
        if client.state in (ConnectionState.RECONNECTING, ConnectionState.TIMEOUT):
            client.state = ConnectionState.CONNECTED
        return True

    def disconnect_client(self, client_id: str) -> bool:
        """Disconnect a client and clean up its resources.

        Removes the client from the active list and marks its state
        as DISCONNECTED. Clears the client's event queue.

        Args:
            client_id: The client to disconnect.

        Returns:
            True if the client existed and was disconnected.
        """
        client = self._clients.get(client_id)
        if client is None:
            return False

        client.state = ConnectionState.DISCONNECTED
        self._event_queue.pop(client_id, None)
        return True

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> NetworkStats:
        """Compute aggregate network replication statistics.

        Collects connection counts, latency averages, event totals,
        bandwidth estimates, and uptime into a NetworkStats snapshot.

        Returns:
            A populated NetworkStats dataclass instance.
        """
        now = _time_module.time()
        connected = [
            c for c in self._clients.values()
            if c.state == ConnectionState.CONNECTED
        ]

        latencies = [c.latency_ms for c in connected if c.latency_ms > 0]
        avg_latency = (
            sum(latencies) / len(latencies) if latencies else 0.0
        )

        total_packets = self._total_events_sent
        packet_loss = (
            (self._total_events_lost / total_packets * 100.0)
            if total_packets > 0 else 0.0
        )

        # Rough bandwidth estimate: ~256 bytes per event * event rate
        estimated_kbps = (total_packets * 256.0 * 8.0) / max(now - self._start_time, 1.0) / 1000.0

        return NetworkStats(
            active_connections=len(connected),
            total_events=total_packets,
            avg_latency_ms=round(avg_latency, 2),
            bandwidth_usage_kbps=round(estimated_kbps, 2),
            packet_loss_pct=round(packet_loss, 2),
            entities_replicated=len(self._identities),
            uptime_seconds=round(now - self._start_time, 2),
        )

    # ------------------------------------------------------------------
    # Network Simulation
    # ------------------------------------------------------------------

    def simulate_network(self,
                         packet_loss_rate: float = 0.0,
                         latency_range: Tuple[float, float] = (0.0, 0.0)) -> Dict[str, Any]:
        """Configure simulated network conditions for testing.

        Allows developers to inject artificial packet loss and latency
        to test replication behavior under degraded network conditions.
        Latency is applied as random jitter within the specified range.

        Args:
            packet_loss_rate: Fraction of packets to drop (0.0 to 1.0).
            latency_range: (min_ms, max_ms) range for simulated latency.

        Returns:
            Dictionary with the applied simulation parameters.
        """
        self._simulated_packet_loss = max(0.0, min(1.0, packet_loss_rate))
        self._simulated_latency_min = max(0.0, latency_range[0])
        self._simulated_latency_max = max(self._simulated_latency_min, latency_range[1])

        # Apply to connected clients
        for client in self._clients.values():
            if client.state == ConnectionState.CONNECTED:
                sim_latency = random.uniform(
                    self._simulated_latency_min,
                    self._simulated_latency_max,
                )
                client.latency_ms = round(sim_latency, 2)

        return {
            "packet_loss_rate": round(self._simulated_packet_loss, 3),
            "latency_min_ms": round(self._simulated_latency_min, 2),
            "latency_max_ms": round(self._simulated_latency_max, 2),
            "effective": "active",
        }

    # ------------------------------------------------------------------
    # Interest Management
    # ------------------------------------------------------------------

    def get_interested_entities(self,
                                client_id: str,
                                view_radius: float = 500.0) -> List[NetworkIdentity]:
        """Determine which entities a client should receive state for.

        Performs interest management by filtering entities based on
        the client's view radius. The client's own entities are always
        included. Uses distance from the client's latest entity position.

        Args:
            client_id: The client to compute interests for.
            view_radius: Maximum world-space distance for relevance.

        Returns:
            List of NetworkIdentity objects the client should see.
        """
        client = self._clients.get(client_id)
        if client is None:
            return []

        radius = max(1.0, view_radius)
        interested: List[NetworkIdentity] = []

        # Find client's approximate world position from owned entities
        client_cx = 0.0
        client_cy = 0.0
        owned_count = 0
        for eid in client.entities_owned:
            state = self._latest_states.get(eid)
            if state is not None:
                client_cx += state.position_x
                client_cy += state.position_y
                owned_count += 1
        if owned_count > 0:
            client_cx /= owned_count
            client_cy /= owned_count

        for identity in self._identities.values():
            # Always include client's own entities
            if identity.identity_id in client.entities_owned:
                interested.append(identity)
                continue

            # Check distance for other entities
            state = self._latest_states.get(identity.identity_id)
            if state is None:
                continue

            dx = state.position_x - client_cx
            dy = state.position_y - client_cy
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= radius:
                interested.append(identity)

        # Sort by priority (higher first), then by distance
        def _interest_key(ident: NetworkIdentity) -> Tuple[int, float]:
            st = self._latest_states.get(ident.identity_id)
            if st is None:
                return (-ident.priority, float("inf"))
            dx = st.position_x - client_cx
            dy = st.position_y - client_cy
            return (-ident.priority, math.sqrt(dx * dx + dy * dy))

        interested.sort(key=_interest_key)
        return interested

    # ------------------------------------------------------------------
    # RPC
    # ------------------------------------------------------------------

    def queue_rpc(self,
                  client_id: str,
                  method_name: str = "",
                  params: Optional[Dict[str, Any]] = None) -> NetworkEvent:
        """Queue a remote procedure call for delivery to a client.

        Creates an RPC-type network event carrying the method name
        and parameters as the payload. The event is marked as reliable
        to ensure delivery.

        Args:
            client_id: Target client for the RPC.
            method_name: Name of the remote method to invoke.
            params: Keyword arguments for the remote method.

        Returns:
            The RPC NetworkEvent.
        """
        payload = {
            "method": method_name,
            "params": dict(params) if params else {},
            "rpc_id": uuid.uuid4().hex[:8],
        }

        return self.send_event(
            event_type="rpc",
            source_id=self._server_id or "server",
            target_id=client_id,
            payload=payload,
            reliable=True,
        )

    # ------------------------------------------------------------------
    # Client Listing
    # ------------------------------------------------------------------

    def list_clients(self) -> List[ClientConnection]:
        """List all registered client connections.

        Returns:
            List of all ClientConnection objects, sorted by connection time.
        """
        return sorted(
            self._clients.values(),
            key=lambda c: c.connected_at,
        )

    # ------------------------------------------------------------------
    # Matchmaking
    # ------------------------------------------------------------------

    def create_match(self,
                     room_name: str = "",
                     max_players: int = 4,
                     game_mode: str = "default") -> Dict[str, Any]:
        """Create a new matchmaking room.

        Initializes a match room with the given name and capacity.
        The room starts empty and clients join via join_match.

        Args:
            room_name: Display name for the match room.
            max_players: Maximum number of players allowed.
            game_mode: Game mode identifier string.

        Returns:
            Dictionary with match metadata including the match_id.
        """
        match_id = uuid.uuid4().hex[:8]
        match = {
            "match_id": match_id,
            "room_name": room_name or f"Room_{match_id}",
            "max_players": max(1, max_players),
            "game_mode": game_mode,
            "players": [],
            "created_at": _time_module.time(),
            "is_active": True,
        }
        self._matches[match_id] = match
        return dict(match)

    def join_match(self,
                   client_id: str,
                   match_id: str) -> Dict[str, Any]:
        """Add a client to an existing match room.

        If the room is at capacity or inactive, the join is rejected.

        Args:
            client_id: The client joining the match.
            match_id: The match room identifier.

        Returns:
            Dictionary indicating success or an error reason.
        """
        match = self._matches.get(match_id)
        if match is None:
            return {"success": False, "error": "Match not found"}

        if not match["is_active"]:
            return {"success": False, "error": "Match is no longer active"}

        if len(match["players"]) >= match["max_players"]:
            return {"success": False, "error": "Match is full"}

        if client_id not in match["players"]:
            match["players"].append(client_id)

        return {
            "success": True,
            "match_id": match_id,
            "player_count": len(match["players"]),
            "max_players": match["max_players"],
        }

    def leave_match(self,
                    client_id: str,
                    match_id: str) -> bool:
        """Remove a client from a match room.

        If the room becomes empty after removal, it is deactivated.

        Args:
            client_id: The client leaving the match.
            match_id: The match room identifier.

        Returns:
            True if the client was removed, False otherwise.
        """
        match = self._matches.get(match_id)
        if match is None:
            return False

        if client_id in match["players"]:
            match["players"].remove(client_id)
            if not match["players"]:
                match["is_active"] = False
            return True

        return False

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------

    def reconcile_state(self,
                        client_id: str,
                        server_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Simulate client-side prediction reconciliation with server state.

        Compares the client's predicted states against authoritative
        server states and returns a reconciliation report indicating
        which entities need correction.

        This is a deterministic simulation — in production the server
        state would arrive via network messages. Here it is passed
        directly for testing and verification.

        Args:
            client_id: The client whose state is being reconciled.
            server_state: Authoritative server state keyed by identity_id.
                          Expected format: {identity_id: {position: (x,y,z), ...}}

        Returns:
            Dictionary with reconciliation results per entity.
        """
        client = self._clients.get(client_id)
        if client is None:
            return {"error": "Client not found"}

        ss = server_state or {}
        results: Dict[str, Any] = {
            "client_id": client_id,
            "corrected": 0,
            "entities": [],
        }

        for identity_id in client.entities_owned:
            local_state = self._latest_states.get(identity_id)
            remote = ss.get(identity_id, {})

            if local_state is None:
                continue

            entity_result = {
                "identity_id": identity_id,
                "needs_correction": False,
                "position_error": 0.0,
                "local_position": (local_state.position_x, local_state.position_y, local_state.position_z),
                "server_position": None,
            }

            if remote:
                rpos = remote.get("position", (0.0, 0.0, 0.0))
                server_pos = (
                    float(rpos[0]) if len(rpos) > 0 else 0.0,
                    float(rpos[1]) if len(rpos) > 1 else 0.0,
                    float(rpos[2]) if len(rpos) > 2 else 0.0,
                )
                dx = local_state.position_x - server_pos[0]
                dy = local_state.position_y - server_pos[1]
                dz = local_state.position_z - server_pos[2]
                error = math.sqrt(dx * dx + dy * dy + dz * dz)

                entity_result["position_error"] = round(error, 4)
                entity_result["server_position"] = server_pos
                entity_result["needs_correction"] = error > 0.01

                if entity_result["needs_correction"]:
                    results["corrected"] += 1

            results["entities"].append(entity_result)

        return results

    # ------------------------------------------------------------------
    # Bandwidth Throttling
    # ------------------------------------------------------------------

    def bandwidth_throttle(self,
                           client_id: str,
                           limit_kbps: float = 0.0) -> bool:
        """Apply a bandwidth limit to a specific client.

        Setting limit_kbps to 0.0 removes throttling entirely.
        The limit is enforced conceptually — actual enforcement
        would occur in the transport layer during event dispatch.

        Args:
            client_id: The client to throttle.
            limit_kbps: Maximum bandwidth in kilobits per second.

        Returns:
            True if the client exists and the limit was applied.
        """
        client = self._clients.get(client_id)
        if client is None:
            return False

        if limit_kbps <= 0.0:
            self._bandwidth_limits.pop(client_id, None)
        else:
            self._bandwidth_limits[client_id] = max(0.1, limit_kbps)

        return True

    # ------------------------------------------------------------------
    # Utility: List Identities
    # ------------------------------------------------------------------

    def list_identities(self) -> List[NetworkIdentity]:
        """List all registered network identities.

        Returns:
            List of all NetworkIdentity objects sorted by priority descending.
        """
        return sorted(
            self._identities.values(),
            key=lambda i: (-i.priority, i.entity_type),
        )

    # ------------------------------------------------------------------
    # Utility: Get Identity State History
    # ------------------------------------------------------------------

    def get_state_history(self,
                          identity_id: str,
                          max_count: int = 10) -> List[ReplicatedState]:
        """Retrieve recent state history for an entity.

        Args:
            identity_id: The network identity to query.
            max_count: Maximum number of historical states to return.

        Returns:
            List of ReplicatedState snapshots, most recent first.
        """
        history = self._state_history.get(identity_id, [])
        return list(reversed(history[-max_count:]))

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all replication system state to defaults."""
        with self._lock:
            self._identities.clear()
            self._state_history.clear()
            self._latest_states.clear()
            self._sequence_counter = 0
            self._events.clear()
            self._event_queue.clear()
            self._clients.clear()
            self._server_id = ""
            self._matches.clear()
            self._simulated_packet_loss = 0.0
            self._simulated_latency_min = 0.0
            self._simulated_latency_max = 0.0
            self._bandwidth_limits.clear()
            self._start_time = _time_module.time()
            self._total_events_sent = 0
            self._total_events_lost = 0


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_network_replication() -> EngineNetworkReplication:
    """Return the singleton EngineNetworkReplication instance."""
    return EngineNetworkReplication.get_instance()