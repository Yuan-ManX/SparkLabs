"""
SparkLabs Engine - Fast Travel System

Manages fast travel networks that allow players to instantly traverse
between discovered locations in a game world. Each travel point can
belong to one or more networks, has discovery requirements, and may
charge a travel cost (currency, items, or cooldown). The system tracks
per-player discovery state, travel history, and enforces travel
restrictions such as locked destinations, hostile area blocking, or
cooldown timers.

Architecture:
  FastTravelSystem (singleton)
    |-- TravelPoint, TravelNetwork, TravelConnection, TravelCost,
    |   TravelRequirement, DiscoveryRecord, TravelRecord, TravelCooldown,
    |   TravelStats, TravelSnapshot, TravelEvent
    |-- PointStatus, TravelMode, CostType, RequirementType,
        TravelEventKind

Core Capabilities:
  - register_point / update_point / get_point / list_points /
    delete_point: travel point catalog with coordinates, status, and
    network membership.
  - create_network / update_network / get_network / list_networks:
    group travel points into named networks (e.g. "overworld",
    "underground").
  - connect / disconnect / list_connections: define directed or
    bidirectional connections between travel points.
  - discover / undiscover / is_discovered / list_discoveries: per-player
    discovery tracking with optional requirements check.
  - travel / can_travel / get_travel_cost: attempt travel between two
    points, enforcing discovery, requirements, cooldowns, and cost.
  - list_travel_history / list_cooldowns: query recent travel activity
    and active cooldowns for a player.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_POINTS: int = 1000
_MAX_NETWORKS: int = 100
_MAX_CONNECTIONS: int = 5000
_MAX_PLAYERS: int = 2000
_MAX_DISCOVERIES_PER_PLAYER: int = 1000
_MAX_TRAVEL_HISTORY: int = 10000
_MAX_COOLDOWNS_PER_PLAYER: int = 200
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert ``value`` into something safe to drop into a JSON payload."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance to a plain dictionary."""
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class PointStatus(Enum):
    """Lifecycle status of a travel point."""
    LOCKED = "locked"
    DISCOVERED = "discovered"
    ACTIVE = "active"
    DISABLED = "disabled"
    HIDDEN = "hidden"


class TravelMode(Enum):
    """Mode of transportation for a travel action."""
    INSTANT = "instant"
    AIRSHIP = "airship"
    TELEPORT = "teleport"
    CARRIAGE = "carriage"
    BOAT = "boat"
    MOUNT = "mount"
    PORTAL = "portal"


class CostType(Enum):
    """Type of resource charged for travel."""
    FREE = "free"
    GOLD = "gold"
    GEMS = "gems"
    STAMINA = "stamina"
    ITEM = "item"
    XP = "xp"


class RequirementType(Enum):
    """Type of requirement to discover or travel to a point."""
    QUEST_COMPLETE = "quest_complete"
    LEVEL = "level"
    ITEM_OWNED = "item_owned"
    ACHIEVEMENT = "achievement"
    FACTION_RANK = "faction_rank"
    NONE = "none"


class TravelEventKind(Enum):
    """Audit event kinds emitted by the fast travel system."""
    POINT_REGISTERED = "point_registered"
    POINT_UPDATED = "point_updated"
    POINT_DELETED = "point_deleted"
    NETWORK_CREATED = "network_created"
    NETWORK_UPDATED = "network_updated"
    NETWORK_DELETED = "network_deleted"
    CONNECTION_ADDED = "connection_added"
    CONNECTION_REMOVED = "connection_removed"
    POINT_DISCOVERED = "point_discovered"
    POINT_UNDISCOVERED = "point_undiscovered"
    TRAVEL_STARTED = "travel_started"
    TRAVEL_COMPLETED = "travel_completed"
    TRAVEL_BLOCKED = "travel_blocked"
    COOLDOWN_STARTED = "cooldown_started"
    COOLDOWN_EXPIRED = "cooldown_expired"
    SYSTEM_RESET = "system_reset"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class TravelCost:
    """The cost of a single travel action."""
    cost_type: CostType = CostType.FREE
    amount: float = 0.0
    item_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TravelRequirement:
    """A requirement that must be met to discover or travel."""
    requirement_type: RequirementType = RequirementType.NONE
    target_id: str = ""  # quest id, item id, achievement id, etc.
    target_value: float = 0.0  # level number, faction rank, etc.

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TravelPoint:
    """A fast travel destination in the game world."""
    point_id: str
    name: str
    network_id: str
    coordinates: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    description: str = ""
    status: PointStatus = PointStatus.ACTIVE
    travel_mode: TravelMode = TravelMode.INSTANT
    base_cost: TravelCost = field(default_factory=TravelCost)
    discovery_requirement: TravelRequirement = field(default_factory=TravelRequirement)
    travel_requirement: TravelRequirement = field(default_factory=TravelRequirement)
    region: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TravelNetwork:
    """A named group of travel points."""
    network_id: str
    name: str
    description: str = ""
    color: str = "#4f8cff"
    icon: str = ""
    enabled: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TravelConnection:
    """A directed or bidirectional connection between two travel points."""
    connection_id: str
    from_point_id: str
    to_point_id: str
    bidirectional: bool = True
    cost_override: Optional[TravelCost] = None
    travel_time_seconds: float = 0.0
    enabled: bool = True
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DiscoveryRecord:
    """A record of a player discovering a travel point."""
    player_id: str
    point_id: str
    discovered_at: str = field(default_factory=_now)
    context: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TravelRecord:
    """A single travel action record."""
    record_id: str
    player_id: str
    from_point_id: str
    to_point_id: str
    travel_mode: TravelMode
    cost: TravelCost = field(default_factory=TravelCost)
    travel_time_seconds: float = 0.0
    completed: bool = True
    blocked_reason: str = ""
    traveled_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TravelCooldown:
    """An active cooldown preventing immediate re-travel."""
    player_id: str
    point_id: str
    expires_at: str
    started_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TravelStats:
    """Aggregate statistics for the fast travel system."""
    total_points: int = 0
    total_networks: int = 0
    total_connections: int = 0
    total_players: int = 0
    total_discoveries: int = 0
    total_travels: int = 0
    completed_travels: int = 0
    blocked_travels: int = 0
    active_cooldowns: int = 0
    total_events: int = 0
    point_counter: int = 0
    network_counter: int = 0
    connection_counter: int = 0
    travel_counter: int = 0
    event_counter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TravelSnapshot:
    """A point-in-time snapshot of the entire fast travel system state."""
    points: List[Dict[str, Any]] = field(default_factory=list)
    networks: List[Dict[str, Any]] = field(default_factory=list)
    connections: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TravelEvent:
    """An audit event emitted by the fast travel system."""
    event_id: str
    kind: TravelEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Fast Travel System Singleton
# ---------------------------------------------------------------------------


class FastTravelSystem:
    """Engine-level fast travel network manager.

    Tracks travel points, networks, connections, per-player discovery
    state, travel history, and cooldowns. Enforces discovery
    requirements, travel costs, and cooldown timers.
    """

    _instance: Optional["FastTravelSystem"] = None
    _inner_lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "FastTravelSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._points: Dict[str, TravelPoint] = {}
            self._networks: Dict[str, TravelNetwork] = {}
            self._connections: Dict[str, TravelConnection] = {}
            self._discoveries: Dict[str, Dict[str, DiscoveryRecord]] = {}
            self._travel_history: List[TravelRecord] = []
            self._cooldowns: Dict[str, Dict[str, TravelCooldown]] = {}
            self._events: List[TravelEvent] = []
            self._stats = TravelStats()
            self._seed_data()
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, kind: TravelEventKind, data: Dict[str, Any]) -> None:
        event = TravelEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        self._stats.event_counter += 1
        self._stats.total_events = len(self._events)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _seed_data(self) -> None:
        """Seed demo travel networks, points, connections, and discoveries."""
        # Networks
        net_overworld = TravelNetwork(
            network_id="net_overworld",
            name="Overworld",
            description="Surface travel network connecting major cities.",
            color="#4f8cff",
            icon="map",
        )
        net_underground = TravelNetwork(
            network_id="net_underground",
            name="Underground",
            description="Subterranean cavern and dungeon network.",
            color="#8a6d3b",
            icon="cave",
        )
        self._networks[net_overworld.network_id] = net_overworld
        self._networks[net_underground.network_id] = net_underground
        self._stats.network_counter = 2
        self._stats.total_networks = 2

        # Points
        points_data = [
            ("tp_capital", "Capital City", "net_overworld", (0.0, 0.0, 0.0),
             "The bustling capital of the realm.", PointStatus.ACTIVE, TravelMode.CARRIAGE,
             CostType.FREE, 0.0, "Central"),
            ("tp_riverside", "Riverside Village", "net_overworld", (120.0, 40.0, 0.0),
             "A peaceful fishing village by the river.", PointStatus.ACTIVE, TravelMode.CARRIAGE,
             CostType.GOLD, 25.0, "Central"),
            ("tp_mountain", "Mountain Pass", "net_overworld", (300.0, 200.0, 50.0),
             "A treacherous mountain pass.", PointStatus.ACTIVE, TravelMode.MOUNT,
             CostType.GOLD, 50.0, "Northern"),
            ("tp_port", "Harbor Town", "net_overworld", (80.0, -180.0, 0.0),
             "A busy port with ships to distant lands.", PointStatus.ACTIVE, TravelMode.BOAT,
             CostType.GOLD, 40.0, "Southern"),
            ("tp_forest", "Enchanted Forest", "net_overworld", (200.0, -80.0, 0.0),
             "A mystical forest with ancient secrets.", PointStatus.ACTIVE, TravelMode.MOUNT,
             CostType.GOLD, 35.0, "Eastern"),
            ("tp_caverns", "Crystal Caverns", "net_underground", (100.0, 50.0, -60.0),
             "Glittering crystal formations underground.", PointStatus.ACTIVE, TravelMode.PORTAL,
             CostType.STAMINA, 10.0, "Depths"),
            ("tp_abyss", "The Abyss", "net_underground", (150.0, 80.0, -200.0),
             "A forbidden chasm deep below.", PointStatus.LOCKED, TravelMode.PORTAL,
             CostType.GEMS, 3.0, "Depths"),
        ]
        for pid, name, nid, coords, desc, status, mode, ctype, amount, region in points_data:
            point = TravelPoint(
                point_id=pid,
                name=name,
                network_id=nid,
                coordinates=coords,
                description=desc,
                status=status,
                travel_mode=mode,
                base_cost=TravelCost(cost_type=CostType(ctype), amount=amount),
                region=region,
            )
            self._points[pid] = point
            self._stats.point_counter += 1
        self._stats.total_points = len(self._points)

        # Connections (bidirectional within same network)
        connections_def = [
            ("tp_capital", "tp_riverside", True),
            ("tp_capital", "tp_port", True),
            ("tp_capital", "tp_forest", True),
            ("tp_riverside", "tp_mountain", True),
            ("tp_port", "tp_forest", True),
            ("tp_capital", "tp_caverns", True),
            ("tp_caverns", "tp_abyss", False),
        ]
        for from_id, to_id, bidir in connections_def:
            conn_id = _new_id("conn")
            self._connections[conn_id] = TravelConnection(
                connection_id=conn_id,
                from_point_id=from_id,
                to_point_id=to_id,
                bidirectional=bidir,
            )
            self._stats.connection_counter += 1
        self._stats.total_connections = len(self._connections)

        # Discovery records for a seed player
        player_id = "player_seed_1"
        discovered_points = ["tp_capital", "tp_riverside", "tp_mountain", "tp_port", "tp_caverns"]
        self._discoveries[player_id] = {}
        for pid in discovered_points:
            self._discoveries[player_id][pid] = DiscoveryRecord(
                player_id=player_id,
                point_id=pid,
                context="seed",
            )
        self._stats.total_players = 1
        self._stats.total_discoveries = len(discovered_points)

        # Seed events
        self._emit(TravelEventKind.POINT_REGISTERED, {"point_id": "tp_capital"})
        self._emit(TravelEventKind.NETWORK_CREATED, {"network_id": "net_overworld"})
        self._emit(TravelEventKind.CONNECTION_ADDED, {"from": "tp_capital", "to": "tp_riverside"})
        self._emit(TravelEventKind.POINT_DISCOVERED, {"player_id": player_id, "point_id": "tp_capital"})

    # ------------------------------------------------------------------
    # Point management
    # ------------------------------------------------------------------

    def register_point(
        self,
        name: str,
        network_id: str,
        coordinates: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        description: str = "",
        status: PointStatus = PointStatus.ACTIVE,
        travel_mode: TravelMode = TravelMode.INSTANT,
        base_cost: Optional[TravelCost] = None,
        discovery_requirement: Optional[TravelRequirement] = None,
        travel_requirement: Optional[TravelRequirement] = None,
        region: str = "",
        tags: Optional[List[str]] = None,
        point_id: Optional[str] = None,
    ) -> TravelPoint:
        """Register a new travel point."""
        with self._lock:
            pid = point_id or _new_id("tp")
            if pid in self._points:
                raise ValueError(f"Travel point already exists: {pid}")
            if network_id not in self._networks:
                raise ValueError(f"Network does not exist: {network_id}")
            point = TravelPoint(
                point_id=pid,
                name=name,
                network_id=network_id,
                coordinates=coordinates,
                description=description,
                status=status,
                travel_mode=travel_mode,
                base_cost=base_cost or TravelCost(),
                discovery_requirement=discovery_requirement or TravelRequirement(),
                travel_requirement=travel_requirement or TravelRequirement(),
                region=region,
                tags=tags or [],
            )
            self._points[pid] = point
            self._stats.point_counter += 1
            self._stats.total_points = len(self._points)
            _evict_fifo_dict(self._points, _MAX_POINTS)
            self._emit(TravelEventKind.POINT_REGISTERED, {"point_id": pid, "name": name})
            return point

    def update_point(self, point_id: str, updates: Dict[str, Any]) -> TravelPoint:
        """Update an existing travel point."""
        with self._lock:
            if point_id not in self._points:
                raise KeyError(f"Travel point not found: {point_id}")
            point = self._points[point_id]
            for key, value in updates.items():
                if key in ("point_id", "created_at"):
                    continue
                if key == "status" and isinstance(value, str):
                    value = PointStatus(value)
                elif key == "travel_mode" and isinstance(value, str):
                    value = TravelMode(value)
                elif key == "base_cost" and isinstance(value, dict):
                    value = TravelCost(
                        cost_type=CostType(value.get("cost_type", "free")),
                        amount=float(value.get("amount", 0.0)),
                        item_id=str(value.get("item_id", "")),
                    )
                elif key == "discovery_requirement" and isinstance(value, dict):
                    value = TravelRequirement(
                        requirement_type=RequirementType(value.get("requirement_type", "none")),
                        target_id=str(value.get("target_id", "")),
                        target_value=float(value.get("target_value", 0.0)),
                    )
                elif key == "travel_requirement" and isinstance(value, dict):
                    value = TravelRequirement(
                        requirement_type=RequirementType(value.get("requirement_type", "none")),
                        target_id=str(value.get("target_id", "")),
                        target_value=float(value.get("target_value", 0.0)),
                    )
                elif key == "coordinates" and isinstance(value, list):
                    value = tuple(value)
                if hasattr(point, key):
                    setattr(point, key, value)
            point.updated_at = _now()
            self._emit(TravelEventKind.POINT_UPDATED, {"point_id": point_id})
            return point

    def get_point(self, point_id: str) -> Optional[TravelPoint]:
        """Get a travel point by id."""
        with self._lock:
            return self._points.get(point_id)

    def list_points(
        self,
        network_id: Optional[str] = None,
        region: Optional[str] = None,
        status: Optional[PointStatus] = None,
    ) -> List[TravelPoint]:
        """List travel points with optional filters."""
        with self._lock:
            result = []
            for point in self._points.values():
                if network_id and point.network_id != network_id:
                    continue
                if region and point.region != region:
                    continue
                if status and point.status != status:
                    continue
                result.append(point)
            return result

    def delete_point(self, point_id: str) -> bool:
        """Delete a travel point and its connections."""
        with self._lock:
            if point_id not in self._points:
                return False
            del self._points[point_id]
            self._stats.total_points = len(self._points)
            # Remove connections involving this point
            to_remove = [
                cid for cid, conn in self._connections.items()
                if conn.from_point_id == point_id or conn.to_point_id == point_id
            ]
            for cid in to_remove:
                del self._connections[cid]
            self._stats.total_connections = len(self._connections)
            self._emit(TravelEventKind.POINT_DELETED, {"point_id": point_id})
            return True

    # ------------------------------------------------------------------
    # Network management
    # ------------------------------------------------------------------

    def create_network(
        self,
        name: str,
        description: str = "",
        color: str = "#4f8cff",
        icon: str = "",
        enabled: bool = True,
        network_id: Optional[str] = None,
    ) -> TravelNetwork:
        """Create a new travel network."""
        with self._lock:
            nid = network_id or _new_id("net")
            if nid in self._networks:
                raise ValueError(f"Network already exists: {nid}")
            network = TravelNetwork(
                network_id=nid,
                name=name,
                description=description,
                color=color,
                icon=icon,
                enabled=enabled,
            )
            self._networks[nid] = network
            self._stats.network_counter += 1
            self._stats.total_networks = len(self._networks)
            _evict_fifo_dict(self._networks, _MAX_NETWORKS)
            self._emit(TravelEventKind.NETWORK_CREATED, {"network_id": nid, "name": name})
            return network

    def update_network(self, network_id: str, updates: Dict[str, Any]) -> TravelNetwork:
        """Update an existing travel network."""
        with self._lock:
            if network_id not in self._networks:
                raise KeyError(f"Network not found: {network_id}")
            network = self._networks[network_id]
            for key, value in updates.items():
                if key in ("network_id", "created_at"):
                    continue
                if hasattr(network, key):
                    setattr(network, key, value)
            network.updated_at = _now()
            self._emit(TravelEventKind.NETWORK_UPDATED, {"network_id": network_id})
            return network

    def get_network(self, network_id: str) -> Optional[TravelNetwork]:
        """Get a travel network by id."""
        with self._lock:
            return self._networks.get(network_id)

    def list_networks(self, enabled_only: bool = False) -> List[TravelNetwork]:
        """List all travel networks."""
        with self._lock:
            if enabled_only:
                return [n for n in self._networks.values() if n.enabled]
            return list(self._networks.values())

    def delete_network(self, network_id: str) -> bool:
        """Delete a travel network. Points in the network are also removed."""
        with self._lock:
            if network_id not in self._networks:
                return False
            del self._networks[network_id]
            self._stats.total_networks = len(self._networks)
            # Remove points belonging to this network
            to_remove = [
                pid for pid, point in self._points.items() if point.network_id == network_id
            ]
            for pid in to_remove:
                del self._points[pid]
            self._stats.total_points = len(self._points)
            self._emit(TravelEventKind.NETWORK_DELETED, {"network_id": network_id})
            return True

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(
        self,
        from_point_id: str,
        to_point_id: str,
        bidirectional: bool = True,
        cost_override: Optional[TravelCost] = None,
        travel_time_seconds: float = 0.0,
        enabled: bool = True,
    ) -> TravelConnection:
        """Create a connection between two travel points."""
        with self._lock:
            if from_point_id not in self._points:
                raise KeyError(f"From point not found: {from_point_id}")
            if to_point_id not in self._points:
                raise KeyError(f"To point not found: {to_point_id}")
            conn_id = _new_id("conn")
            conn = TravelConnection(
                connection_id=conn_id,
                from_point_id=from_point_id,
                to_point_id=to_point_id,
                bidirectional=bidirectional,
                cost_override=cost_override,
                travel_time_seconds=travel_time_seconds,
                enabled=enabled,
            )
            self._connections[conn_id] = conn
            self._stats.connection_counter += 1
            self._stats.total_connections = len(self._connections)
            _evict_fifo_dict(self._connections, _MAX_CONNECTIONS)
            self._emit(TravelEventKind.CONNECTION_ADDED, {
                "connection_id": conn_id,
                "from": from_point_id,
                "to": to_point_id,
            })
            return conn

    def disconnect(self, connection_id: str) -> bool:
        """Remove a connection between travel points."""
        with self._lock:
            if connection_id not in self._connections:
                return False
            conn = self._connections[connection_id]
            del self._connections[connection_id]
            self._stats.total_connections = len(self._connections)
            self._emit(TravelEventKind.CONNECTION_REMOVED, {
                "connection_id": connection_id,
                "from": conn.from_point_id,
                "to": conn.to_point_id,
            })
            return True

    def list_connections(
        self, point_id: Optional[str] = None
    ) -> List[TravelConnection]:
        """List connections, optionally filtered by a point."""
        with self._lock:
            if point_id is None:
                return list(self._connections.values())
            result = []
            for conn in self._connections.values():
                if conn.from_point_id == point_id or (
                    conn.bidirectional and conn.to_point_id == point_id
                ):
                    result.append(conn)
            return result

    # ------------------------------------------------------------------
    # Discovery management
    # ------------------------------------------------------------------

    def discover(
        self,
        player_id: str,
        point_id: str,
        context: str = "",
        skip_requirement_check: bool = False,
    ) -> DiscoveryRecord:
        """Mark a travel point as discovered for a player."""
        with self._lock:
            if point_id not in self._points:
                raise KeyError(f"Travel point not found: {point_id}")
            point = self._points[point_id]
            if not skip_requirement_check:
                if point.status == PointStatus.LOCKED:
                    raise ValueError(f"Point is locked: {point_id}")
                if point.discovery_requirement.requirement_type != RequirementType.NONE:
                    # In a real engine this would check player state; we accept here.
                    pass
            if player_id not in self._discoveries:
                self._discoveries[player_id] = {}
                self._stats.total_players += 1
            if point_id in self._discoveries[player_id]:
                return self._discoveries[player_id][point_id]
            record = DiscoveryRecord(
                player_id=player_id,
                point_id=point_id,
                context=context,
            )
            self._discoveries[player_id][point_id] = record
            _evict_fifo_dict(self._discoveries[player_id], _MAX_DISCOVERIES_PER_PLAYER)
            self._stats.total_discoveries += 1
            self._emit(TravelEventKind.POINT_DISCOVERED, {
                "player_id": player_id,
                "point_id": point_id,
            })
            return record

    def undiscover(self, player_id: str, point_id: str) -> bool:
        """Remove a discovery record for a player."""
        with self._lock:
            if player_id not in self._discoveries:
                return False
            if point_id not in self._discoveries[player_id]:
                return False
            del self._discoveries[player_id][point_id]
            self._stats.total_discoveries = max(0, self._stats.total_discoveries - 1)
            self._emit(TravelEventKind.POINT_UNDISCOVERED, {
                "player_id": player_id,
                "point_id": point_id,
            })
            return True

    def is_discovered(self, player_id: str, point_id: str) -> bool:
        """Check whether a player has discovered a point."""
        with self._lock:
            return (
                player_id in self._discoveries
                and point_id in self._discoveries[player_id]
            )

    def list_discoveries(self, player_id: str) -> List[DiscoveryRecord]:
        """List all discoveries for a player."""
        with self._lock:
            return list(self._discoveries.get(player_id, {}).values())

    # ------------------------------------------------------------------
    # Travel management
    # ------------------------------------------------------------------

    def get_travel_cost(
        self,
        from_point_id: str,
        to_point_id: str,
        connection_id: Optional[str] = None,
    ) -> TravelCost:
        """Compute the travel cost between two points."""
        with self._lock:
            if to_point_id not in self._points:
                raise KeyError(f"To point not found: {to_point_id}")
            to_point = self._points[to_point_id]
            if connection_id and connection_id in self._connections:
                conn = self._connections[connection_id]
                if conn.cost_override:
                    return conn.cost_override
            return to_point.base_cost

    def can_travel(
        self,
        player_id: str,
        from_point_id: str,
        to_point_id: str,
    ) -> Tuple[bool, str]:
        """Check whether a player can travel between two points."""
        with self._lock:
            if from_point_id not in self._points:
                return False, f"From point not found: {from_point_id}"
            if to_point_id not in self._points:
                return False, f"To point not found: {to_point_id}"
            from_point = self._points[from_point_id]
            to_point = self._points[to_point_id]
            if to_point.status in (PointStatus.LOCKED, PointStatus.DISABLED, PointStatus.HIDDEN):
                return False, f"Destination is {to_point.status.value}"
            if not self.is_discovered(player_id, to_point_id):
                return False, "Destination not discovered"
            # Check cooldown
            if (
                player_id in self._cooldowns
                and to_point_id in self._cooldowns[player_id]
            ):
                return False, "Cooldown active"
            # Check connection exists (if connections are defined)
            has_conn = False
            for conn in self._connections.values():
                if not conn.enabled:
                    continue
                if conn.from_point_id == from_point_id and conn.to_point_id == to_point_id:
                    has_conn = True
                    break
                if conn.bidirectional and conn.from_point_id == to_point_id and conn.to_point_id == from_point_id:
                    has_conn = True
                    break
            if self._connections and not has_conn:
                return False, "No connection between points"
            return True, ""

    def travel(
        self,
        player_id: str,
        from_point_id: str,
        to_point_id: str,
        cooldown_seconds: float = 0.0,
        skip_checks: bool = False,
    ) -> TravelRecord:
        """Attempt to travel from one point to another."""
        with self._lock:
            if not skip_checks:
                ok, reason = self.can_travel(player_id, from_point_id, to_point_id)
                if not ok:
                    record = TravelRecord(
                        record_id=_new_id("trv"),
                        player_id=player_id,
                        from_point_id=from_point_id,
                        to_point_id=to_point_id,
                        travel_mode=self._points.get(to_point_id, TravelPoint(
                            point_id="", name="", network_id=""
                        )).travel_mode if to_point_id in self._points else TravelMode.INSTANT,
                        completed=False,
                        blocked_reason=reason,
                    )
                    self._travel_history.append(record)
                    _evict_fifo_list(self._travel_history, _MAX_TRAVEL_HISTORY)
                    self._stats.total_travels += 1
                    self._stats.blocked_travels += 1
                    self._emit(TravelEventKind.TRAVEL_BLOCKED, {
                        "player_id": player_id,
                        "from": from_point_id,
                        "to": to_point_id,
                        "reason": reason,
                    })
                    return record
            to_point = self._points[to_point_id]
            cost = self.get_travel_cost(from_point_id, to_point_id)
            travel_time = 0.0
            for conn in self._connections.values():
                if (
                    conn.from_point_id == from_point_id
                    and conn.to_point_id == to_point_id
                ):
                    travel_time = conn.travel_time_seconds
                    break
            record = TravelRecord(
                record_id=_new_id("trv"),
                player_id=player_id,
                from_point_id=from_point_id,
                to_point_id=to_point_id,
                travel_mode=to_point.travel_mode,
                cost=cost,
                travel_time_seconds=travel_time,
                completed=True,
            )
            self._travel_history.append(record)
            _evict_fifo_list(self._travel_history, _MAX_TRAVEL_HISTORY)
            self._stats.total_travels += 1
            self._stats.completed_travels += 1
            # Apply cooldown
            if cooldown_seconds > 0:
                if player_id not in self._cooldowns:
                    self._cooldowns[player_id] = {}
                from datetime import datetime, timedelta
                expires = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
                cooldown = TravelCooldown(
                    player_id=player_id,
                    point_id=to_point_id,
                    expires_at=expires.isoformat() + "Z",
                )
                self._cooldowns[player_id][to_point_id] = cooldown
                _evict_fifo_dict(self._cooldowns[player_id], _MAX_COOLDOWNS_PER_PLAYER)
                self._stats.active_cooldowns += 1
                self._emit(TravelEventKind.COOLDOWN_STARTED, {
                    "player_id": player_id,
                    "point_id": to_point_id,
                    "expires_at": cooldown.expires_at,
                })
            self._emit(TravelEventKind.TRAVEL_COMPLETED, {
                "player_id": player_id,
                "from": from_point_id,
                "to": to_point_id,
                "record_id": record.record_id,
            })
            return record

    def list_travel_history(
        self,
        player_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[TravelRecord]:
        """List travel history, optionally filtered by player."""
        with self._lock:
            records = self._travel_history
            if player_id:
                records = [r for r in records if r.player_id == player_id]
            return list(records[-limit:])

    def list_cooldowns(self, player_id: str) -> List[TravelCooldown]:
        """List active cooldowns for a player."""
        with self._lock:
            return list(self._cooldowns.get(player_id, {}).values())

    def clear_cooldown(self, player_id: str, point_id: str) -> bool:
        """Clear a cooldown for a player at a specific point."""
        with self._lock:
            if player_id not in self._cooldowns:
                return False
            if point_id not in self._cooldowns[player_id]:
                return False
            del self._cooldowns[player_id][point_id]
            self._stats.active_cooldowns = max(0, self._stats.active_cooldowns - 1)
            self._emit(TravelEventKind.COOLDOWN_EXPIRED, {
                "player_id": player_id,
                "point_id": point_id,
            })
            return True

    # ------------------------------------------------------------------
    # Observability and lifecycle
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[TravelEvent]:
        """List recent audit events."""
        with self._lock:
            return list(self._events[-limit:])

    def get_stats(self) -> TravelStats:
        """Return aggregate statistics."""
        with self._lock:
            self._stats.total_points = len(self._points)
            self._stats.total_networks = len(self._networks)
            self._stats.total_connections = len(self._connections)
            self._stats.total_players = len(self._discoveries)
            self._stats.active_cooldowns = sum(
                len(cds) for cds in self._cooldowns.values()
            )
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Return a status summary."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_points": len(self._points),
                "total_networks": len(self._networks),
                "total_connections": len(self._connections),
                "total_players": len(self._discoveries),
                "total_discoveries": self._stats.total_discoveries,
                "total_travels": self._stats.total_travels,
                "completed_travels": self._stats.completed_travels,
                "blocked_travels": self._stats.blocked_travels,
                "active_cooldowns": sum(len(cds) for cds in self._cooldowns.values()),
                "total_events": len(self._events),
                "capacities": {
                    "max_points": _MAX_POINTS,
                    "max_networks": _MAX_NETWORKS,
                    "max_connections": _MAX_CONNECTIONS,
                    "max_players": _MAX_PLAYERS,
                    "max_travel_history": _MAX_TRAVEL_HISTORY,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> TravelSnapshot:
        """Capture a snapshot of the entire system state."""
        with self._lock:
            return TravelSnapshot(
                points=[p.to_dict() for p in self._points.values()],
                networks=[n.to_dict() for n in self._networks.values()],
                connections=[c.to_dict() for c in self._connections.values()],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        """Reset the system to an empty state (clears all data)."""
        with self._lock:
            self._points.clear()
            self._networks.clear()
            self._connections.clear()
            self._discoveries.clear()
            self._travel_history.clear()
            self._cooldowns.clear()
            self._events.clear()
            self._stats = TravelStats()
            self._emit(TravelEventKind.SYSTEM_RESET, {})


def get_fast_travel_system() -> FastTravelSystem:
    """Return the singleton FastTravelSystem instance."""
    return FastTravelSystem()
