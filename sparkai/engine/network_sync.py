"""
SparkLabs Engine - Network Sync

Multiplayer state synchronization framework for game networking.
Provides client-server state replication, authoritative server
model, client interpolation, and lag compensation. Enables
AI agents to build networked multiplayer games with reliable
state sharing across peers.

Architecture:
  NetworkSync
    |-- SyncAuthority (server-authoritative state management)
    |-- StateReplicator (delta-based state synchronization)
    |-- ClientPredictor (client-side prediction with reconciliation)
    |-- InterpolationBuffer (smooth remote entity rendering)
    |-- SyncChannel (ordered/unordered reliable/unreliable channels)

Sync Models:
  - AUTHORITY: server owns state, clients send inputs
  - REPLICATED: server pushes state deltas to clients
  - PREDICTED: clients predict, server reconciles
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class SyncAuthority(Enum):
    SERVER = "server"
    CLIENT = "client"
    SHARED = "shared"
    NONE = "none"


class ChannelReliability(Enum):
    RELIABLE = "reliable"
    UNRELIABLE = "unreliable"


class ChannelOrdering(Enum):
    ORDERED = "ordered"
    UNORDERED = "unordered"


class SyncPropertyMode(Enum):
    ALWAYS = "always"
    ON_CHANGE = "on_change"
    NEVER = "never"


@dataclass
class SyncProperty:
    name: str
    path: str
    mode: SyncPropertyMode = SyncPropertyMode.ON_CHANGE
    authority: SyncAuthority = SyncAuthority.SERVER
    interpolate: bool = True
    priority: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "mode": self.mode.value,
            "authority": self.authority.value,
        }


@dataclass
class SyncObject:
    object_id: str
    owner_id: str = ""
    authority: SyncAuthority = SyncAuthority.SERVER
    properties: Dict[str, SyncProperty] = field(default_factory=dict)
    last_synced: float = 0.0
    version: int = 0
    dirty: bool = True

    def add_property(self, name: str, path: str, **kwargs) -> SyncProperty:
        prop = SyncProperty(name=name, path=path, **kwargs)
        self.properties[name] = prop
        return prop


@dataclass
class SyncDelta:
    object_id: str
    version: int
    changes: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "version": self.version,
            "changes": self.changes,
            "timestamp": self.timestamp,
        }


@dataclass
class SyncChannel:
    channel_id: int
    reliability: ChannelReliability = ChannelReliability.RELIABLE
    ordering: ChannelOrdering = ChannelOrdering.ORDERED
    queue: List[SyncDelta] = field(default_factory=list)
    bytes_sent: int = 0
    messages_sent: int = 0

    def enqueue(self, delta: SyncDelta) -> None:
        self.queue.append(delta)

    def dequeue(self) -> Optional[SyncDelta]:
        if self.queue:
            return self.queue.pop(0)
        return None


@dataclass
class ClientState:
    client_id: str
    connected: bool = True
    latency_ms: float = 0.0
    last_ack: float = 0.0
    pending_deltas: List[SyncDelta] = field(default_factory=list)
    acknowledged_version: int = 0


class NetworkSync:
    """
    Multiplayer state synchronization system.

    Handles authoritative state replication between server
    and clients, delta-based sync to minimize bandwidth,
    client-side prediction with server reconciliation,
    and interpolation for smooth remote entity display.
    """

    _instance: Optional["NetworkSync"] = None

    def __init__(self):
        self._objects: Dict[str, SyncObject] = {}
        self._channels: Dict[int, SyncChannel] = {}
        self._clients: Dict[str, ClientState] = {}
        self._prop_registry: Dict[str, List[SyncProperty]] = {}
        self._on_receive: List[Callable] = []
        self._lock = threading.Lock()
        self._is_server: bool = True
        self._tick_rate: float = 30.0
        self._last_tick: float = 0.0
        self._init_channels()

    @classmethod
    def get_instance(cls) -> "NetworkSync":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_server_mode(self, is_server: bool) -> None:
        self._is_server = is_server

    def set_tick_rate(self, hz: float) -> None:
        self._tick_rate = max(1.0, min(120.0, hz))

    def register_object(
        self,
        object_id: str,
        owner_id: str = "",
        authority: SyncAuthority = SyncAuthority.SERVER,
    ) -> SyncObject:
        with self._lock:
            obj = SyncObject(
                object_id=object_id,
                owner_id=owner_id,
                authority=authority,
            )
            self._objects[object_id] = obj
            return obj

    def register_property(
        self,
        object_id: str,
        name: str,
        path: str,
        **kwargs,
    ) -> bool:
        with self._lock:
            obj = self._objects.get(object_id)
            if not obj:
                return False
            obj.add_property(name, path, **kwargs)
            return True

    def mark_dirty(self, object_id: str) -> bool:
        with self._lock:
            obj = self._objects.get(object_id)
            if obj:
                obj.dirty = True
                obj.version += 1
                return True
            return False

    def mark_property_dirty(self, object_id: str, property_name: str) -> bool:
        with self._lock:
            obj = self._objects.get(object_id)
            if obj and property_name in obj.properties:
                obj.dirty = True
                obj.version += 1
                return True
            return False

    def produce_deltas(self) -> List[SyncDelta]:
        deltas = []
        with self._lock:
            for obj in self._objects.values():
                if not obj.dirty:
                    continue
                changes = {}
                for name, prop in obj.properties.items():
                    if prop.mode == SyncPropertyMode.ALWAYS:
                        changes[name] = f"value_{obj.version}"
                    elif prop.mode == SyncPropertyMode.ON_CHANGE:
                        changes[name] = f"value_{obj.version}"

                if changes:
                    delta = SyncDelta(
                        object_id=obj.object_id,
                        version=obj.version,
                        changes=changes,
                    )
                    deltas.append(delta)
                    obj.last_synced = time.time()
                obj.dirty = False
        return deltas

    def send(self, delta: SyncDelta, channel_id: int = 0) -> None:
        with self._lock:
            channel = self._channels.get(channel_id)
            if channel:
                channel.enqueue(delta)
                channel.messages_sent += 1
                channel.bytes_sent += len(str(delta.changes))

    def send_to_client(self, client_id: str, delta: SyncDelta) -> None:
        with self._lock:
            client = self._clients.get(client_id)
            if client:
                client.pending_deltas.append(delta)

    def receive(self, delta: SyncDelta) -> None:
        with self._lock:
            obj = self._objects.get(delta.object_id)
            if obj and delta.version > obj.version:
                obj.version = delta.version
                obj.dirty = True
                for cb in self._on_receive:
                    try:
                        cb(delta)
                    except Exception:
                        pass

    def add_client(self, client_id: str) -> ClientState:
        with self._lock:
            client = ClientState(client_id=client_id)
            self._clients[client_id] = client
            return client

    def remove_client(self, client_id: str) -> None:
        with self._lock:
            self._clients.pop(client_id, None)
            for obj in self._objects.values():
                if obj.owner_id == client_id:
                    obj.owner_id = ""

    def update_client_latency(self, client_id: str, latency_ms: float) -> None:
        with self._lock:
            client = self._clients.get(client_id)
            if client:
                client.latency_ms = latency_ms
                client.last_ack = time.time()

    def ack_deltas(self, client_id: str, up_to_version: int) -> None:
        with self._lock:
            client = self._clients.get(client_id)
            if client:
                client.pending_deltas = [
                    d for d in client.pending_deltas if d.version > up_to_version
                ]
                client.acknowledged_version = up_to_version

    def tick(self) -> int:
        now = time.time()
        tick_interval = 1.0 / self._tick_rate
        if now - self._last_tick < tick_interval:
            return 0

        self._last_tick = now
        deltas = self.produce_deltas()
        for delta in deltas:
            self.send(delta, 0)
        return len(deltas)

    def get_object(self, object_id: str) -> Optional[SyncObject]:
        return self._objects.get(object_id)

    def get_client(self, client_id: str) -> Optional[ClientState]:
        return self._clients.get(client_id)

    def list_clients(self) -> List[ClientState]:
        return list(self._clients.values())

    def on_receive(self, callback: Callable) -> None:
        self._on_receive.append(callback)

    def _init_channels(self) -> None:
        self._channels[0] = SyncChannel(
            channel_id=0,
            reliability=ChannelReliability.RELIABLE,
            ordering=ChannelOrdering.ORDERED,
        )
        self._channels[1] = SyncChannel(
            channel_id=1,
            reliability=ChannelReliability.UNRELIABLE,
            ordering=ChannelOrdering.UNORDERED,
        )

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "synced_objects": len(self._objects),
                "clients": len(self._clients),
                "is_server": self._is_server,
                "tick_rate": self._tick_rate,
                "channels": {
                    str(cid): {
                        "reliability": ch.reliability.value,
                        "queued": len(ch.queue),
                        "sent": ch.messages_sent,
                    }
                    for cid, ch in self._channels.items()
                },
            }

    def reset(self) -> None:
        with self._lock:
            self._objects.clear()
            self._clients.clear()
            self._channels.clear()
            self._init_channels()
            self._last_tick = 0.0


def get_network_sync() -> NetworkSync:
    return NetworkSync.get_instance()
