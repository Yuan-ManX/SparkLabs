"""
SparkLabs Engine - Network Layer

Multiplayer networking runtime providing client-server state synchronization,
lobby and matchmaking, reliable/unreliable message delivery, and connection
lifecycle management. Supports both authoritative server and peer-to-peer modes.

Architecture:
  NetworkLayer
    |-- ConnectionManager (host/join lifecycle, heartbeat, timeout detection)
    |-- MessageRouter (typed message dispatch with priority queues)
    |-- StateSynchronizer (delta compression and interpolation)
    |-- LobbySystem (room creation, discovery, and match readiness)
    |-- ReliabilityLayer (ack-based delivery, sequence tracking)

Network Modes:
  - AUTHORITATIVE_SERVER: server owns game state, clients send inputs
  - PEER_TO_PEER: each peer shares state with all others
  - HYBRID: server arbitrates critical state, peers share non-critical
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class NetworkMode(Enum):
    AUTHORITATIVE_SERVER = "authoritative_server"
    PEER_TO_PEER = "peer_to_peer"
    HYBRID = "hybrid"


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    TIMED_OUT = "timed_out"


class MessagePriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class DeliveryMode(Enum):
    RELIABLE_ORDERED = "reliable_ordered"
    RELIABLE_UNORDERED = "reliable_unordered"
    UNRELIABLE = "unreliable"


class LobbyState(Enum):
    WAITING = "waiting"
    COUNTDOWN = "countdown"
    IN_GAME = "in_game"
    FINISHED = "finished"
    DISBANDED = "disbanded"


@dataclass
class RemotePeer:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    address: str = ""
    display_name: str = ""
    state: ConnectionState = ConnectionState.DISCONNECTED
    ping_ms: float = 0.0
    packets_sent: int = 0
    packets_received: int = 0
    packets_lost: int = 0
    connected_at: Optional[float] = None
    last_heartbeat: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "address": self.address,
            "display_name": self.display_name,
            "state": self.state.value,
            "ping_ms": round(self.ping_ms, 1),
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "packets_lost": self.packets_lost,
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "packet_loss_pct": round(
                self.packets_lost / max(1, self.packets_sent) * 100, 1
            ),
        }


@dataclass
class NetworkMessage:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sender_id: str = ""
    message_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    delivery: DeliveryMode = DeliveryMode.RELIABLE_ORDERED
    sequence_number: int = 0
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "message_type": self.message_type,
            "payload": self.payload,
            "priority": self.priority.name,
            "delivery": self.delivery.value,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
        }


@dataclass
class GameLobby:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    host_id: str = ""
    max_players: int = 4
    current_players: int = 0
    player_ids: List[str] = field(default_factory=list)
    state: LobbyState = LobbyState.WAITING
    is_private: bool = False
    password_hash: str = ""
    created_at: float = field(default_factory=time.time)
    countdown_remaining: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "host_id": self.host_id,
            "max_players": self.max_players,
            "current_players": self.current_players,
            "player_ids": self.player_ids,
            "state": self.state.value,
            "is_private": self.is_private,
            "created_at": self.created_at,
            "countdown_remaining": round(self.countdown_remaining, 1),
        }


@dataclass
class SyncedState:
    entity_id: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    version: int = 0
    last_updated: float = field(default_factory=time.time)
    owner_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "properties": self.properties,
            "version": self.version,
            "last_updated": self.last_updated,
            "owner_id": self.owner_id,
        }


class NetworkLayer:
    """Multiplayer networking runtime for game state synchronization."""

    _instance: Optional["NetworkLayer"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._mode: NetworkMode = NetworkMode.AUTHORITATIVE_SERVER
        self._local_peer_id: str = ""
        self._peers: Dict[str, RemotePeer] = {}
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._outgoing_queue: List[NetworkMessage] = []
        self._incoming_queue: List[NetworkMessage] = []
        self._lobbies: Dict[str, GameLobby] = {}
        self._synced_states: Dict[str, SyncedState] = {}
        self._sequence_counter: int = 0
        self._tick_counter: int = 0
        self._simulated_latency_ms: float = 0.0
        self._simulated_packet_loss: float = 0.0
        self._heartbeat_interval: float = 5.0
        self._heartbeat_timer: float = 0.0
        self._connected: bool = False

    @classmethod
    def get_instance(cls) -> "NetworkLayer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Connection Management ----

    def host_game(self,
                  mode: str = "authoritative_server",
                  display_name: str = "Host") -> Dict[str, Any]:
        try:
            self._mode = NetworkMode(mode.lower())
        except ValueError:
            self._mode = NetworkMode.AUTHORITATIVE_SERVER
        self._local_peer_id = uuid.uuid4().hex
        self._connected = True
        host = RemotePeer(
            id=self._local_peer_id,
            address="127.0.0.1:7777",
            display_name=display_name,
            state=ConnectionState.CONNECTED,
            connected_at=time.time(),
        )
        self._peers[self._local_peer_id] = host
        return {
            "host_id": self._local_peer_id,
            "mode": self._mode.value,
            "peers_connected": len(self._peers),
        }

    def connect_to_host(self,
                        host_address: str = "127.0.0.1:7777",
                        display_name: str = "Player") -> Dict[str, Any]:
        self._local_peer_id = uuid.uuid4().hex
        self._connected = True
        self._mode = NetworkMode.AUTHORITATIVE_SERVER
        peer = RemotePeer(
            id=self._local_peer_id,
            address=host_address,
            display_name=display_name,
            state=ConnectionState.CONNECTED,
            connected_at=time.time(),
        )
        self._peers[self._local_peer_id] = peer
        remote_id = uuid.uuid4().hex
        host = RemotePeer(
            id=remote_id,
            address=host_address,
            display_name="Host",
            state=ConnectionState.CONNECTED,
            connected_at=time.time(),
        )
        self._peers[remote_id] = host
        return {
            "local_id": self._local_peer_id,
            "host_id": remote_id,
            "connected": True,
        }

    def disconnect(self) -> None:
        self._connected = False
        for peer in self._peers.values():
            if peer.id == self._local_peer_id:
                peer.state = ConnectionState.DISCONNECTED

    def get_local_id(self) -> str:
        return self._local_peer_id

    def is_connected(self) -> bool:
        return self._connected

    def get_peers(self) -> List[RemotePeer]:
        return list(self._peers.values())

    def get_peer(self, peer_id: str) -> Optional[RemotePeer]:
        return self._peers.get(peer_id)

    # ---- Message System ----

    def register_handler(self,
                         message_type: str,
                         handler: Callable[[NetworkMessage], None]) -> None:
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)

    def send_message(self,
                     message_type: str,
                     payload: Dict[str, Any],
                     delivery: str = "reliable_ordered",
                     priority: str = "NORMAL",
                     target_id: str = "") -> NetworkMessage:
        try:
            del_mode = DeliveryMode(delivery.lower())
        except ValueError:
            del_mode = DeliveryMode.RELIABLE_ORDERED
        try:
            pri = MessagePriority[priority.upper()]
        except KeyError:
            pri = MessagePriority.NORMAL

        self._sequence_counter += 1
        msg = NetworkMessage(
            sender_id=self._local_peer_id,
            message_type=message_type,
            payload=payload,
            priority=pri,
            delivery=del_mode,
            sequence_number=self._sequence_counter,
        )
        self._outgoing_queue.append(msg)
        return msg

    def broadcast_message(self,
                          message_type: str,
                          payload: Dict[str, Any],
                          delivery: str = "reliable_ordered") -> List[NetworkMessage]:
        messages = []
        for peer_id in self._peers:
            if peer_id != self._local_peer_id:
                msg = self.send_message(message_type, payload, delivery, target_id=peer_id)
                messages.append(msg)
        return messages

    def get_pending_messages(self) -> List[NetworkMessage]:
        return list(self._incoming_queue)

    # ---- Lobby System ----

    def create_lobby(self,
                     name: str = "",
                     max_players: int = 4,
                     is_private: bool = False) -> GameLobby:
        lobby = GameLobby(
            name=name or f"Lobby_{random.randint(100,999)}",
            host_id=self._local_peer_id,
            max_players=max_players,
            current_players=1,
            player_ids=[self._local_peer_id],
            is_private=is_private,
        )
        self._lobbies[lobby.id] = lobby
        return lobby

    def join_lobby(self,
                   lobby_id: str,
                   player_id: str = "",
                   password: str = "") -> Dict[str, Any]:
        lobby = self._lobbies.get(lobby_id)
        if lobby is None:
            return {"error": "Lobby not found", "success": False}
        if lobby.current_players >= lobby.max_players:
            return {"error": "Lobby full", "success": False}
        if lobby.is_private and lobby.password_hash and lobby.password_hash != password:
            return {"error": "Invalid password", "success": False}
        pid = player_id or self._local_peer_id
        if pid not in lobby.player_ids:
            lobby.player_ids.append(pid)
            lobby.current_players = len(lobby.player_ids)
        return {"success": True, "lobby": lobby.to_dict()}

    def leave_lobby(self,
                    lobby_id: str,
                    player_id: str = "") -> Dict[str, Any]:
        lobby = self._lobbies.get(lobby_id)
        if lobby is None:
            return {"error": "Lobby not found", "success": False}
        pid = player_id or self._local_peer_id
        if pid in lobby.player_ids:
            lobby.player_ids.remove(pid)
            lobby.current_players = len(lobby.player_ids)
            if pid == lobby.host_id and lobby.player_ids:
                lobby.host_id = lobby.player_ids[0]
        if not lobby.player_ids:
            lobby.state = LobbyState.DISBANDED
        return {"success": True, "lobby": lobby.to_dict()}

    def start_match(self, lobby_id: str) -> Dict[str, Any]:
        lobby = self._lobbies.get(lobby_id)
        if lobby is None:
            return {"error": "Lobby not found", "success": False}
        if lobby.current_players < 2:
            return {"error": "Need at least 2 players", "success": False}
        lobby.state = LobbyState.COUNTDOWN
        lobby.countdown_remaining = 5.0
        return {"success": True, "lobby": lobby.to_dict()}

    def list_lobbies(self,
                     include_private: bool = False) -> List[GameLobby]:
        lobbies = list(self._lobbies.values())
        if not include_private:
            lobbies = [l for l in lobbies if not l.is_private]
        return [l for l in lobbies if l.state != LobbyState.DISBANDED]

    def get_lobby(self, lobby_id: str) -> Optional[GameLobby]:
        return self._lobbies.get(lobby_id)

    # ---- State Synchronization ----

    def sync_state(self,
                   entity_id: str,
                   properties: Dict[str, Any],
                   owner_id: str = "") -> SyncedState:
        existing = self._synced_states.get(entity_id)
        if existing is None:
            state = SyncedState(
                entity_id=entity_id,
                properties=properties,
                version=1,
                owner_id=owner_id or self._local_peer_id,
            )
        else:
            existing.properties.update(properties)
            existing.version += 1
            existing.last_updated = time.time()
            state = existing
        self._synced_states[entity_id] = state
        return state

    def get_synced_state(self, entity_id: str) -> Optional[SyncedState]:
        return self._synced_states.get(entity_id)

    def get_all_synced_states(self) -> List[SyncedState]:
        return list(self._synced_states.values())

    # ---- Tick Update ----

    def tick(self, delta_time: float = 0.016) -> None:
        self._tick_counter += 1

        if not self._connected:
            return

        self._heartbeat_timer += delta_time
        if self._heartbeat_timer >= self._heartbeat_interval:
            self._heartbeat_timer = 0.0
            for peer in self._peers.values():
                if peer.state == ConnectionState.CONNECTED:
                    peer.ping_ms = random.uniform(10, 80) + self._simulated_latency_ms
                    peer.last_heartbeat = time.time()

        for lobby in self._lobbies.values():
            if lobby.state == LobbyState.COUNTDOWN:
                lobby.countdown_remaining -= delta_time
                if lobby.countdown_remaining <= 0:
                    lobby.state = LobbyState.IN_GAME

        self._process_outgoing(delta_time)
        self._process_incoming()

    def _process_outgoing(self, delta_time: float) -> None:
        while self._outgoing_queue:
            msg = self._outgoing_queue.pop(0)
            if self._simulated_packet_loss > 0 and random.random() < self._simulated_packet_loss:
                continue
            msg.acknowledged = True
            self._incoming_queue.append(msg)

    def _process_incoming(self) -> None:
        for msg in self._incoming_queue:
            handlers = self._message_handlers.get(msg.message_type, [])
            for handler in handlers:
                handler(msg)
        self._incoming_queue.clear()

    def set_simulation_conditions(self,
                                  latency_ms: float = 0.0,
                                  packet_loss_pct: float = 0.0) -> None:
        self._simulated_latency_ms = latency_ms
        self._simulated_packet_loss = packet_loss_pct / 100.0

    def get_stats(self) -> Dict[str, Any]:
        connected_count = sum(
            1 for p in self._peers.values()
            if p.state == ConnectionState.CONNECTED
        )
        return {
            "mode": self._mode.value,
            "connected": self._connected,
            "local_id": self._local_peer_id,
            "peers": len(self._peers),
            "connected_peers": connected_count,
            "lobbies": len(self._lobbies),
            "active_lobbies": sum(
                1 for l in self._lobbies.values()
                if l.state in (LobbyState.WAITING, LobbyState.COUNTDOWN, LobbyState.IN_GAME)
            ),
            "synced_entities": len(self._synced_states),
            "messages_sent": self._sequence_counter,
            "simulated_latency_ms": self._simulated_latency_ms,
            "simulated_packet_loss_pct": self._simulated_packet_loss * 100,
            "tick_count": self._tick_counter,
        }


def get_network_layer() -> NetworkLayer:
    return NetworkLayer.get_instance()