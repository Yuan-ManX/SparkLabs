"""
SparkLabs Engine - Talent Constellation System

Manages a star-map themed talent tree system where players allocate talent
points into constellations made of interconnected nodes. Each constellation
belongs to a thematic category, nodes are linked by paths, and activating
nodes of matching resonance types unlocks stacking resonance bonuses.

Architecture:
  TalentConstellationSystem (singleton)
    |-- ConstellationCategory, TalentNodeType, ResonanceType, NodeState,
       TalentConstellationEventKind
    |-- Constellation, TalentNode, TalentPath, PlayerConstellationProgress,
       ResonanceBonus, TalentConstellationConfig, TalentConstellationStats,
       TalentConstellationSnapshot, TalentConstellationEvent
    |-- get_talent_constellation_system

Core Capabilities:
  - register_constellation / get_constellation / list_constellations / remove_constellation
  - register_talent_node / get_talent_node / list_talent_nodes / remove_talent_node
  - register_path / get_path / list_paths / remove_path
  - register_resonance_bonus / get_resonance_bonus / list_resonance_bonuses
  - allocate_point / remove_point
  - get_player_progress / list_player_progress
  - check_requirements / calculate_resonance / get_active_bonuses
  - respec_all / tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`TalentConstellationSystem.get_instance` or the module-level
:func:`get_talent_constellation_system` factory.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_CONSTELLATIONS: int = 100
_MAX_NODES: int = 5000
_MAX_PATHS: int = 5000
_MAX_RESONANCE_BONUSES: int = 500
_MAX_PLAYER_PROGRESS: int = 500000
_MAX_EVENTS: int = 20000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ConstellationCategory(str, Enum):
    """Thematic category for a talent constellation."""
    WARFARE = "warfare"
    ARCANE = "arcane"
    SURVIVAL = "survival"
    DIVINE = "divine"
    SHADOW = "shadow"
    NATURE = "nature"
    TECH = "tech"
    VOID = "void"


class TalentNodeType(str, Enum):
    """Functional type of a talent node."""
    ACTIVE = "active"
    PASSIVE = "passive"
    KEYSTONE = "keystone"
    MILESTONE = "milestone"


class ResonanceType(str, Enum):
    """Elemental or thematic resonance carried by a talent node."""
    FIRE = "fire"
    FROST = "frost"
    LIGHTNING = "lightning"
    EARTH = "earth"
    WIND = "wind"
    HOLY = "holy"
    DARK = "dark"
    ARCANE = "arcane"
    VOID = "void"
    NONE = "none"


class NodeState(str, Enum):
    """Lifecycle state of a node for a given player."""
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    ACTIVATED = "activated"
    EMPOWERED = "empowered"


class TalentConstellationEventKind(str, Enum):
    """Audit event types emitted by the talent constellation system."""
    CONSTELLATION_REGISTERED = "constellation_registered"
    CONSTELLATION_REMOVED = "constellation_removed"
    NODE_REGISTERED = "node_registered"
    NODE_REMOVED = "node_removed"
    PATH_REGISTERED = "path_registered"
    PATH_REMOVED = "path_removed"
    RESONANCE_BONUS_REGISTERED = "resonance_bonus_registered"
    POINT_ALLOCATED = "point_allocated"
    POINT_REMOVED = "point_removed"
    REQUIREMENTS_CHECKED = "requirements_checked"
    RESONANCE_CALCULATED = "resonance_calculated"
    BONUS_ACTIVATED = "bonus_activated"
    RESPEC_PERFORMED = "respec_performed"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Constellation:
    """A star-map constellation grouping several talent nodes.

    Attributes:
        constellation_id: Unique identifier for the constellation.
        name: Display name of the constellation.
        description: Flavor text describing the constellation.
        category: Thematic category (see ConstellationCategory).
        max_points: Maximum talent points a player may spend here.
        resonance_type: Primary resonance for the whole constellation.
        node_ids: Identifiers of nodes belonging to this constellation.
        path_ids: Identifiers of paths belonging to this constellation.
        icon: Icon asset identifier.
        metadata: Arbitrary additional data.
        created_at: Timestamp when the constellation was created.
    """
    constellation_id: str
    name: str
    description: str = ""
    category: str = ConstellationCategory.WARFARE.value
    max_points: int = 30
    resonance_type: str = ResonanceType.NONE.value
    node_ids: List[str] = field(default_factory=list)
    path_ids: List[str] = field(default_factory=list)
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TalentNode:
    """A single talent node within a constellation.

    Attributes:
        node_id: Unique identifier for the node.
        constellation_id: Owner constellation identifier.
        name: Display name of the node.
        description: Flavor text describing the node effect.
        node_type: Functional type (active, passive, keystone, milestone).
        max_rank: Maximum rank a player may allocate to this node.
        point_cost_per_rank: Talent point cost for each rank.
        prerequisite_node_ids: Nodes that must be activated first.
        effects: Stat bonuses applied per allocated rank.
        position_x: Horizontal position on the star map.
        position_y: Vertical position on the star map.
        resonance_type: Resonance carried by this node.
        icon: Icon asset identifier.
        metadata: Arbitrary additional data.
        created_at: Timestamp when the node was created.
    """
    node_id: str
    constellation_id: str
    name: str
    description: str = ""
    node_type: str = TalentNodeType.PASSIVE.value
    max_rank: int = 1
    point_cost_per_rank: int = 1
    prerequisite_node_ids: List[str] = field(default_factory=list)
    effects: Dict[str, float] = field(default_factory=dict)
    position_x: float = 0.0
    position_y: float = 0.0
    resonance_type: str = ResonanceType.NONE.value
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TalentPath:
    """A directed or bidirectional link between two talent nodes.

    Attributes:
        path_id: Unique identifier for the path.
        constellation_id: Owner constellation identifier.
        from_node_id: Source node identifier.
        to_node_id: Destination node identifier.
        is_bidirectional: Whether the path can be traversed both ways.
        required_rank: Minimum rank on the source node to traverse.
        metadata: Arbitrary additional data.
        created_at: Timestamp when the path was created.
    """
    path_id: str
    constellation_id: str
    from_node_id: str = ""
    to_node_id: str = ""
    is_bidirectional: bool = True
    required_rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerConstellationProgress:
    """Per-player progress within a single constellation.

    Attributes:
        player_id: The player this progress belongs to.
        constellation_id: The constellation being progressed.
        progress_id: Unique identifier for this progress record.
        allocated_points: Total talent points currently spent.
        max_points: Maximum points permitted in this constellation.
        node_ranks: Mapping of node_id to allocated rank.
        node_states: Mapping of node_id to current NodeState value.
        activated_at: Timestamp when progress was first started.
        last_updated: Timestamp of the most recent allocation change.
    """
    player_id: str
    constellation_id: str
    progress_id: str = field(default_factory=lambda: _new_id("prog"))
    allocated_points: int = 0
    max_points: int = 30
    node_ranks: Dict[str, int] = field(default_factory=dict)
    node_states: Dict[str, str] = field(default_factory=dict)
    activated_at: Optional[float] = None
    last_updated: float = field(default_factory=_now)

    @property
    def activated_node_count(self) -> int:
        return sum(1 for r in self.node_ranks.values() if r > 0)

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["activated_node_count"] = self.activated_node_count
        return d


@dataclass
class ResonanceBonus:
    """A bonus unlocked when enough nodes of a resonance type are active.

    Attributes:
        bonus_id: Unique identifier for the bonus.
        name: Display name of the bonus.
        resonance_type: Resonance type that triggers the bonus.
        required_count: Number of active nodes needed to trigger.
        target_stat: Stat that the bonus modifies.
        bonus_value: Magnitude of the bonus.
        is_percentage: Whether the bonus value is a percentage.
        description: Flavor text describing the bonus.
        metadata: Arbitrary additional data.
        created_at: Timestamp when the bonus was created.
    """
    bonus_id: str
    name: str
    resonance_type: str = ResonanceType.NONE.value
    required_count: int = 1
    target_stat: str = ""
    bonus_value: float = 0.0
    is_percentage: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TalentConstellationConfig:
    """Runtime configuration for the talent constellation system."""
    max_constellations: int = _MAX_CONSTELLATIONS
    max_nodes_per_constellation: int = 200
    max_paths_per_constellation: int = 200
    max_resonance_bonuses: int = _MAX_RESONANCE_BONUSES
    max_player_progress: int = _MAX_PLAYER_PROGRESS
    default_max_points: int = 30
    allow_respec: bool = True
    respec_cost: float = 0.0
    respec_currency: str = "gold"
    respect_prerequisites: bool = True
    point_cost_multiplier: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TalentConstellationStats:
    """Aggregated statistics for the talent constellation system."""
    total_constellations: int = 0
    total_nodes: int = 0
    total_paths: int = 0
    total_resonance_bonuses: int = 0
    total_player_progress: int = 0
    total_points_allocated: int = 0
    total_nodes_activated: int = 0
    total_nodes_empowered: int = 0
    total_respecs: int = 0
    active_bonuses_count: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TalentConstellationSnapshot:
    """A complete snapshot of the talent constellation system state."""
    constellations: List[Dict[str, Any]] = field(default_factory=list)
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    paths: List[Dict[str, Any]] = field(default_factory=list)
    resonance_bonuses: List[Dict[str, Any]] = field(default_factory=list)
    player_progress: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    taken_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TalentConstellationEvent:
    """An audit event emitted by the talent constellation system.

    Attributes:
        event_id: Unique identifier for the event.
        kind: Event kind (see TalentConstellationEventKind).
        payload: Event-specific data.
        timestamp: When the event was emitted.
    """
    event_id: str
    kind: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Talent Constellation System
# ---------------------------------------------------------------------------

class TalentConstellationSystem:
    """Manages talent constellations, nodes, paths, and player allocations."""

    _instance: Optional["TalentConstellationSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._constellations: Dict[str, Constellation] = {}
        self._nodes: Dict[str, TalentNode] = {}
        self._paths: Dict[str, TalentPath] = {}
        self._resonance_bonuses: Dict[str, ResonanceBonus] = {}
        self._player_progress: Dict[str, PlayerConstellationProgress] = {}
        self._events: List[TalentConstellationEvent] = []
        self._stats = TalentConstellationStats()
        self._config = TalentConstellationConfig()
        self._tick_count: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    # -- singleton ----------------------------------------------------------
    @classmethod
    def get_instance(cls) -> "TalentConstellationSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -- internal helpers ---------------------------------------------------
    def _emit(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> None:
        ev = TalentConstellationEvent(
            event_id=_new_id("evt"),
            kind=kind,
            payload=payload or {},
        )
        self._events.append(ev)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _progress_key(self, player_id: str, constellation_id: str) -> str:
        return f"{player_id}:{constellation_id}"

    def _get_or_create_progress(
        self, player_id: str, constellation_id: str, max_points: int
    ) -> Optional[PlayerConstellationProgress]:
        key = self._progress_key(player_id, constellation_id)
        progress = self._player_progress.get(key)
        if progress is not None:
            return progress
        if len(self._player_progress) >= self._config.max_player_progress:
            return None
        progress = PlayerConstellationProgress(
            player_id=player_id,
            constellation_id=constellation_id,
            max_points=max_points,
            activated_at=_now(),
        )
        self._player_progress[key] = progress
        return progress

    def _prereqs_met(self, progress: PlayerConstellationProgress, node: TalentNode) -> bool:
        if not self._config.respect_prerequisites:
            return True
        for prereq_id in node.prerequisite_node_ids:
            if progress.node_ranks.get(prereq_id, 0) < 1:
                return False
        return True

    def _recompute_states(self, progress: PlayerConstellationProgress, constellation_id: str) -> None:
        for node in self._nodes.values():
            if node.constellation_id != constellation_id:
                continue
            rank = progress.node_ranks.get(node.node_id, 0)
            if rank >= node.max_rank and node.max_rank > 0:
                progress.node_states[node.node_id] = NodeState.EMPOWERED.value
            elif rank > 0:
                progress.node_states[node.node_id] = NodeState.ACTIVATED.value
            elif self._prereqs_met(progress, node):
                progress.node_states[node.node_id] = NodeState.UNLOCKED.value
            else:
                progress.node_states[node.node_id] = NodeState.LOCKED.value

    def _update_stats(self) -> None:
        self._stats.total_constellations = len(self._constellations)
        self._stats.total_nodes = len(self._nodes)
        self._stats.total_paths = len(self._paths)
        self._stats.total_resonance_bonuses = len(self._resonance_bonuses)
        self._stats.total_player_progress = len(self._player_progress)
        self._stats.total_points_allocated = sum(
            p.allocated_points for p in self._player_progress.values()
        )
        self._stats.total_nodes_activated = sum(
            p.activated_node_count for p in self._player_progress.values()
        )
        self._stats.total_nodes_empowered = sum(
            1
            for p in self._player_progress.values()
            for state in p.node_states.values()
            if state == NodeState.EMPOWERED.value
        )
        self._stats.tick_count = self._tick_count

    # -- constellation catalog ---------------------------------------------
    def register_constellation(
        self,
        constellation_id: str,
        name: str,
        description: str = "",
        category: str = ConstellationCategory.WARFARE.value,
        max_points: int = 30,
        resonance_type: str = ResonanceType.NONE.value,
        node_ids: Optional[List[str]] = None,
        path_ids: Optional[List[str]] = None,
        icon: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Constellation]]:
        with _LOCK:
            if constellation_id in self._constellations:
                return False, "exists", None
            if len(self._constellations) >= self._config.max_constellations:
                return False, "capacity", None
            constellation = Constellation(
                constellation_id=constellation_id,
                name=name,
                description=description,
                category=category,
                max_points=_safe_int(max_points, self._config.default_max_points),
                resonance_type=resonance_type,
                node_ids=list(node_ids or []),
                path_ids=list(path_ids or []),
                icon=icon,
                metadata=dict(metadata or {}),
            )
            self._constellations[constellation_id] = constellation
            self._emit(TalentConstellationEventKind.CONSTELLATION_REGISTERED.value, {
                "constellation_id": constellation_id,
                "name": name,
                "category": category,
            })
            return True, "registered", constellation

    def get_constellation(self, constellation_id: str) -> Optional[Constellation]:
        with _LOCK:
            return self._constellations.get(constellation_id)

    def list_constellations(self, category: str = "") -> List[Constellation]:
        with _LOCK:
            if category:
                return [c for c in self._constellations.values() if c.category == category]
            return list(self._constellations.values())

    def remove_constellation(self, constellation_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if constellation_id not in self._constellations:
                return False, "not_found"
            constellation = self._constellations[constellation_id]
            for node_id in constellation.node_ids:
                self._nodes.pop(node_id, None)
            for path_id in constellation.path_ids:
                self._paths.pop(path_id, None)
            stale_keys = [
                key for key, prog in self._player_progress.items()
                if prog.constellation_id == constellation_id
            ]
            for key in stale_keys:
                del self._player_progress[key]
            del self._constellations[constellation_id]
            self._emit(TalentConstellationEventKind.CONSTELLATION_REMOVED.value, {
                "constellation_id": constellation_id,
            })
            return True, "removed"

    # -- talent node catalog -----------------------------------------------
    def register_talent_node(
        self,
        node_id: str,
        constellation_id: str,
        name: str,
        description: str = "",
        node_type: str = TalentNodeType.PASSIVE.value,
        max_rank: int = 1,
        point_cost_per_rank: int = 1,
        prerequisite_node_ids: Optional[List[str]] = None,
        effects: Optional[Dict[str, float]] = None,
        position_x: float = 0.0,
        position_y: float = 0.0,
        resonance_type: str = ResonanceType.NONE.value,
        icon: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[TalentNode]]:
        with _LOCK:
            if node_id in self._nodes:
                return False, "exists", None
            constellation = self._constellations.get(constellation_id)
            if constellation is None:
                return False, "constellation_not_found", None
            nodes_in_const = [n for n in self._nodes.values() if n.constellation_id == constellation_id]
            if len(nodes_in_const) >= self._config.max_nodes_per_constellation:
                return False, "capacity", None
            node = TalentNode(
                node_id=node_id,
                constellation_id=constellation_id,
                name=name,
                description=description,
                node_type=node_type,
                max_rank=max(1, _safe_int(max_rank, 1)),
                point_cost_per_rank=max(1, _safe_int(point_cost_per_rank, 1)),
                prerequisite_node_ids=list(prerequisite_node_ids or []),
                effects=dict(effects or {}),
                position_x=_safe_float(position_x, 0.0),
                position_y=_safe_float(position_y, 0.0),
                resonance_type=resonance_type,
                icon=icon,
                metadata=dict(metadata or {}),
            )
            self._nodes[node_id] = node
            if node_id not in constellation.node_ids:
                constellation.node_ids.append(node_id)
            self._emit(TalentConstellationEventKind.NODE_REGISTERED.value, {
                "node_id": node_id,
                "constellation_id": constellation_id,
                "node_type": node_type,
            })
            return True, "registered", node

    def get_talent_node(self, node_id: str) -> Optional[TalentNode]:
        with _LOCK:
            return self._nodes.get(node_id)

    def list_talent_nodes(self, constellation_id: str = "") -> List[TalentNode]:
        with _LOCK:
            if constellation_id:
                return [n for n in self._nodes.values() if n.constellation_id == constellation_id]
            return list(self._nodes.values())

    def remove_talent_node(self, node_id: str) -> Tuple[bool, str]:
        with _LOCK:
            node = self._nodes.get(node_id)
            if node is None:
                return False, "not_found"
            constellation = self._constellations.get(node.constellation_id)
            if constellation is not None and node_id in constellation.node_ids:
                constellation.node_ids.remove(node_id)
            for path in list(self._paths.values()):
                if path.from_node_id == node_id or path.to_node_id == node_id:
                    if constellation is not None and path.path_id in constellation.path_ids:
                        constellation.path_ids.remove(path.path_id)
                    self._paths.pop(path.path_id, None)
            for progress in self._player_progress.values():
                if progress.constellation_id == node.constellation_id:
                    progress.node_ranks.pop(node_id, None)
                    progress.node_states.pop(node_id, None)
                    self._recompute_states(progress, node.constellation_id)
            del self._nodes[node_id]
            self._emit(TalentConstellationEventKind.NODE_REMOVED.value, {
                "node_id": node_id,
            })
            return True, "removed"

    # -- path catalog -------------------------------------------------------
    def register_path(
        self,
        path_id: str,
        constellation_id: str,
        from_node_id: str = "",
        to_node_id: str = "",
        is_bidirectional: bool = True,
        required_rank: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[TalentPath]]:
        with _LOCK:
            if path_id in self._paths:
                return False, "exists", None
            constellation = self._constellations.get(constellation_id)
            if constellation is None:
                return False, "constellation_not_found", None
            paths_in_const = [p for p in self._paths.values() if p.constellation_id == constellation_id]
            if len(paths_in_const) >= self._config.max_paths_per_constellation:
                return False, "capacity", None
            path = TalentPath(
                path_id=path_id,
                constellation_id=constellation_id,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                is_bidirectional=is_bidirectional,
                required_rank=_safe_int(required_rank, 0),
                metadata=dict(metadata or {}),
            )
            self._paths[path_id] = path
            if path_id not in constellation.path_ids:
                constellation.path_ids.append(path_id)
            self._emit(TalentConstellationEventKind.PATH_REGISTERED.value, {
                "path_id": path_id,
                "constellation_id": constellation_id,
                "from_node_id": from_node_id,
                "to_node_id": to_node_id,
            })
            return True, "registered", path

    def get_path(self, path_id: str) -> Optional[TalentPath]:
        with _LOCK:
            return self._paths.get(path_id)

    def list_paths(self, constellation_id: str = "") -> List[TalentPath]:
        with _LOCK:
            if constellation_id:
                return [p for p in self._paths.values() if p.constellation_id == constellation_id]
            return list(self._paths.values())

    def remove_path(self, path_id: str) -> Tuple[bool, str]:
        with _LOCK:
            path = self._paths.get(path_id)
            if path is None:
                return False, "not_found"
            constellation = self._constellations.get(path.constellation_id)
            if constellation is not None and path_id in constellation.path_ids:
                constellation.path_ids.remove(path_id)
            del self._paths[path_id]
            self._emit(TalentConstellationEventKind.PATH_REMOVED.value, {
                "path_id": path_id,
            })
            return True, "removed"

    # -- resonance bonus catalog -------------------------------------------
    def register_resonance_bonus(
        self,
        bonus_id: str,
        name: str,
        resonance_type: str = ResonanceType.NONE.value,
        required_count: int = 1,
        target_stat: str = "",
        bonus_value: float = 0.0,
        is_percentage: bool = False,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ResonanceBonus]]:
        with _LOCK:
            if bonus_id in self._resonance_bonuses:
                return False, "exists", None
            if len(self._resonance_bonuses) >= self._config.max_resonance_bonuses:
                return False, "capacity", None
            bonus = ResonanceBonus(
                bonus_id=bonus_id,
                name=name,
                resonance_type=resonance_type,
                required_count=max(1, _safe_int(required_count, 1)),
                target_stat=target_stat,
                bonus_value=_safe_float(bonus_value, 0.0),
                is_percentage=bool(is_percentage),
                description=description,
                metadata=dict(metadata or {}),
            )
            self._resonance_bonuses[bonus_id] = bonus
            self._emit(TalentConstellationEventKind.RESONANCE_BONUS_REGISTERED.value, {
                "bonus_id": bonus_id,
                "resonance_type": resonance_type,
                "required_count": bonus.required_count,
            })
            return True, "registered", bonus

    def get_resonance_bonus(self, bonus_id: str) -> Optional[ResonanceBonus]:
        with _LOCK:
            return self._resonance_bonuses.get(bonus_id)

    def list_resonance_bonuses(self, resonance_type: str = "") -> List[ResonanceBonus]:
        with _LOCK:
            if resonance_type:
                return [b for b in self._resonance_bonuses.values() if b.resonance_type == resonance_type]
            return list(self._resonance_bonuses.values())

    # -- point allocation ---------------------------------------------------
    def allocate_point(
        self,
        player_id: str,
        constellation_id: str,
        node_id: str,
        points: int = 1,
    ) -> Tuple[bool, str, Optional[PlayerConstellationProgress]]:
        with _LOCK:
            constellation = self._constellations.get(constellation_id)
            if constellation is None:
                return False, "constellation_not_found", None
            node = self._nodes.get(node_id)
            if node is None:
                return False, "node_not_found", None
            if node.constellation_id != constellation_id:
                return False, "node_not_in_constellation", None
            pts = max(1, _safe_int(points, 1))
            progress = self._get_or_create_progress(player_id, constellation_id, constellation.max_points)
            if progress is None:
                return False, "player_capacity", None
            current_rank = progress.node_ranks.get(node_id, 0)
            if current_rank >= node.max_rank:
                return False, "node_max_rank_reached", progress
            if current_rank + pts > node.max_rank:
                return False, "rank_exceeds_max", progress
            if not self._prereqs_met(progress, node):
                return False, "prerequisite_not_met", progress
            cost = max(1, int(round(node.point_cost_per_rank * self._config.point_cost_multiplier)))
            total_cost = cost * pts
            if progress.allocated_points + total_cost > progress.max_points:
                return False, "max_points_reached", progress
            progress.node_ranks[node_id] = current_rank + pts
            progress.allocated_points += total_cost
            progress.last_updated = _now()
            self._recompute_states(progress, constellation_id)
            self._emit(TalentConstellationEventKind.POINT_ALLOCATED.value, {
                "player_id": player_id,
                "constellation_id": constellation_id,
                "node_id": node_id,
                "points": pts,
                "new_rank": progress.node_ranks[node_id],
            })
            return True, "allocated", progress

    def remove_point(
        self,
        player_id: str,
        constellation_id: str,
        node_id: str,
        points: int = 1,
    ) -> Tuple[bool, str, Optional[PlayerConstellationProgress]]:
        with _LOCK:
            constellation = self._constellations.get(constellation_id)
            if constellation is None:
                return False, "constellation_not_found", None
            node = self._nodes.get(node_id)
            if node is None:
                return False, "node_not_found", None
            progress = self._player_progress.get(self._progress_key(player_id, constellation_id))
            if progress is None:
                return False, "progress_not_found", None
            current_rank = progress.node_ranks.get(node_id, 0)
            if current_rank <= 0:
                return False, "node_not_allocated", progress
            pts = max(1, _safe_int(points, 1))
            remove = min(pts, current_rank)
            cost = max(1, int(round(node.point_cost_per_rank * self._config.point_cost_multiplier)))
            progress.node_ranks[node_id] = current_rank - remove
            progress.allocated_points = max(0, progress.allocated_points - cost * remove)
            progress.last_updated = _now()
            if progress.node_ranks[node_id] <= 0:
                progress.node_ranks.pop(node_id, None)
            self._recompute_states(progress, constellation_id)
            self._emit(TalentConstellationEventKind.POINT_REMOVED.value, {
                "player_id": player_id,
                "constellation_id": constellation_id,
                "node_id": node_id,
                "points": remove,
                "new_rank": progress.node_ranks.get(node_id, 0),
            })
            return True, "removed", progress

    # -- player progress ----------------------------------------------------
    def get_player_progress(
        self, player_id: str, constellation_id: str
    ) -> Optional[PlayerConstellationProgress]:
        with _LOCK:
            return self._player_progress.get(self._progress_key(player_id, constellation_id))

    def list_player_progress(self, player_id: str = "") -> List[PlayerConstellationProgress]:
        with _LOCK:
            if player_id:
                return [p for p in self._player_progress.values() if p.player_id == player_id]
            return list(self._player_progress.values())

    # -- requirements & resonance -------------------------------------------
    def check_requirements(
        self, player_id: str, constellation_id: str, node_id: str
    ) -> Tuple[bool, str]:
        with _LOCK:
            node = self._nodes.get(node_id)
            if node is None:
                return False, "node_not_found"
            if node.constellation_id != constellation_id:
                return False, "node_not_in_constellation"
            progress = self._player_progress.get(self._progress_key(player_id, constellation_id))
            if progress is None:
                if node.prerequisite_node_ids:
                    return False, "prerequisite_not_met"
                self._emit(TalentConstellationEventKind.REQUIREMENTS_CHECKED.value, {
                    "player_id": player_id,
                    "node_id": node_id,
                    "met": True,
                })
                return True, "ok"
            met = self._prereqs_met(progress, node)
            self._emit(TalentConstellationEventKind.REQUIREMENTS_CHECKED.value, {
                "player_id": player_id,
                "node_id": node_id,
                "met": met,
            })
            if not met:
                return False, "prerequisite_not_met"
            return True, "ok"

    def calculate_resonance(self, player_id: str) -> Dict[str, Any]:
        with _LOCK:
            counts: Dict[str, int] = {}
            for progress in self._player_progress.values():
                if progress.player_id != player_id:
                    continue
                for node_id, rank in progress.node_ranks.items():
                    if rank <= 0:
                        continue
                    node = self._nodes.get(node_id)
                    if node is None:
                        continue
                    rtype = node.resonance_type or ResonanceType.NONE.value
                    counts[rtype] = counts.get(rtype, 0) + 1
            total = sum(counts.values())
            self._emit(TalentConstellationEventKind.RESONANCE_CALCULATED.value, {
                "player_id": player_id,
                "counts": counts,
                "total_nodes": total,
            })
            return {
                "player_id": player_id,
                "counts": counts,
                "total_nodes": total,
            }

    def get_active_bonuses(self, player_id: str) -> List[ResonanceBonus]:
        with _LOCK:
            resonance = self.calculate_resonance(player_id)
            counts: Dict[str, int] = resonance.get("counts", {})
            active: List[ResonanceBonus] = []
            for bonus in self._resonance_bonuses.values():
                if counts.get(bonus.resonance_type, 0) >= bonus.required_count:
                    active.append(bonus)
            if active:
                self._emit(TalentConstellationEventKind.BONUS_ACTIVATED.value, {
                    "player_id": player_id,
                    "active_bonus_ids": [b.bonus_id for b in active],
                })
            return active

    # -- respec -------------------------------------------------------------
    def respec_all(self, player_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if not self._config.allow_respec:
                return False, "respec_disabled"
            targets = [
                p for p in self._player_progress.values() if p.player_id == player_id
            ]
            if not targets:
                return False, "no_progress_found"
            for progress in targets:
                progress.node_ranks.clear()
                progress.node_states.clear()
                progress.allocated_points = 0
                progress.last_updated = _now()
                self._recompute_states(progress, progress.constellation_id)
            self._stats.total_respecs += 1
            self._emit(TalentConstellationEventKind.RESPEC_PERFORMED.value, {
                "player_id": player_id,
                "constellations_reset": len(targets),
            })
            return True, "respeced"

    # -- lifecycle ----------------------------------------------------------
    def tick(self) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            self._update_stats()
            self._emit(TalentConstellationEventKind.TICK.value, {"tick": self._tick_count})
            return {
                "tick_count": self._tick_count,
                "total_constellations": len(self._constellations),
                "total_nodes": len(self._nodes),
                "total_player_progress": len(self._player_progress),
            }

    def set_config(self, updates: Optional[Dict[str, Any]]) -> Tuple[bool, str, TalentConstellationConfig]:
        with _LOCK:
            if not updates:
                return True, "noop", self._config
            changed: List[str] = []
            for k, v in updates.items():
                if hasattr(self._config, k):
                    old_val = getattr(self._config, k)
                    setattr(self._config, k, v)
                    changed.append(f"{k}: {old_val}->{v}")
            if changed:
                self._emit(TalentConstellationEventKind.CONFIG_UPDATED.value, {"changes": changed})
            return True, "updated", self._config

    def get_config(self) -> TalentConstellationConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 100) -> List[TalentConstellationEvent]:
        with _LOCK:
            lim = max(1, _safe_int(limit, 100))
            return list(self._events)[-lim:]

    def get_stats(self) -> TalentConstellationStats:
        with _LOCK:
            self._update_stats()
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            self._update_stats()
            return {
                "initialized": self._initialized,
                "total_constellations": len(self._constellations),
                "total_nodes": len(self._nodes),
                "total_paths": len(self._paths),
                "total_resonance_bonuses": len(self._resonance_bonuses),
                "total_player_progress": len(self._player_progress),
                "total_points_allocated": self._stats.total_points_allocated,
                "total_respecs": self._stats.total_respecs,
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> TalentConstellationSnapshot:
        with _LOCK:
            self._update_stats()
            return TalentConstellationSnapshot(
                constellations=[c.to_dict() for c in list(self._constellations.values())[:50]],
                nodes=[n.to_dict() for n in list(self._nodes.values())[:50]],
                paths=[p.to_dict() for p in list(self._paths.values())[:50]],
                resonance_bonuses=[b.to_dict() for b in list(self._resonance_bonuses.values())[:50]],
                player_progress=[p.to_dict() for p in list(self._player_progress.values())[:50]],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
            )

    # -- seeding ------------------------------------------------------------
    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            # -- Constellations --------------------------------------------
            constellation_defs = [
                ("constellation_blade_master", "The Blade Master",
                 "A constellation forged in the fires of endless war, empowering martial prowess.",
                 ConstellationCategory.WARFARE.value, 30, ResonanceType.NONE.value, "icon_blade_master"),
                ("constellation_arcane_weaver", "The Arcane Weaver",
                 "A constellation woven from raw magic, threading spells into devastating patterns.",
                 ConstellationCategory.ARCANE.value, 30, ResonanceType.ARCANE.value, "icon_arcane_weaver"),
                ("constellation_survivor", "The Survivor",
                 "A constellation born of hardship, granting resilience against certain death.",
                 ConstellationCategory.SURVIVAL.value, 24, ResonanceType.EARTH.value, "icon_survivor"),
                ("constellation_shadow_dancer", "The Shadow Dancer",
                 "A constellation that moves between heartbeats, striking from unseen angles.",
                 ConstellationCategory.SHADOW.value, 24, ResonanceType.DARK.value, "icon_shadow_dancer"),
                ("constellation_void_touched", "The Void Touched",
                 "A constellation whispered into being by the abyss, fracturing reality itself.",
                 ConstellationCategory.VOID.value, 20, ResonanceType.VOID.value, "icon_void_touched"),
            ]
            for cid, name, desc, cat, mp, res, icon in constellation_defs:
                self.register_constellation(
                    cid, name, desc, category=cat, max_points=mp,
                    resonance_type=res, icon=icon,
                )

            # -- Talent nodes ----------------------------------------------
            # Tuple: (node_id, constellation_id, name, description, node_type,
            #         max_rank, point_cost, [prereqs], {effects}, pos_x, pos_y, resonance)
            node_defs = [
                # The Blade Master (warfare)
                ("node_bm_01", "constellation_blade_master", "Sword Mastery",
                 "Grants attack power with each rank of blade training.",
                 TalentNodeType.PASSIVE.value, 5, 1, [],
                 {"attack_power": 5.0}, 0.0, 100.0, ResonanceType.NONE.value),
                ("node_bm_02", "constellation_blade_master", "Parry",
                 "Improves defense by deflecting incoming blows.",
                 TalentNodeType.PASSIVE.value, 3, 1, ["node_bm_01"],
                 {"defense": 4.0}, -80.0, 200.0, ResonanceType.NONE.value),
                ("node_bm_03", "constellation_blade_master", "Cleave",
                 "Unlocks a sweeping strike that damages multiple foes.",
                 TalentNodeType.ACTIVE.value, 1, 2, ["node_bm_01"],
                 {"cleave_damage": 25.0}, 80.0, 200.0, ResonanceType.NONE.value),
                ("node_bm_04", "constellation_blade_master", "Weapon Specialization",
                 "Increases critical strike chance with melee weapons.",
                 TalentNodeType.PASSIVE.value, 3, 1, ["node_bm_02"],
                 {"crit_chance_percent": 2.0}, -150.0, 300.0, ResonanceType.NONE.value),
                ("node_bm_05", "constellation_blade_master", "Whirlwind",
                 "Unlocks a spinning assault striking all nearby enemies.",
                 TalentNodeType.ACTIVE.value, 1, 3, ["node_bm_03"],
                 {"whirlwind_damage": 40.0}, 150.0, 300.0, ResonanceType.NONE.value),
                ("node_bm_06", "constellation_blade_master", "Berserker Stance",
                 "Raises attack speed at the cost of controlled defense.",
                 TalentNodeType.PASSIVE.value, 3, 2, ["node_bm_04"],
                 {"attack_speed_percent": 3.0}, -200.0, 400.0, ResonanceType.FIRE.value),
                ("node_bm_07", "constellation_blade_master", "Executioner",
                 "Mark a milestone: deal lethal damage to wounded targets.",
                 TalentNodeType.MILESTONE.value, 1, 3, ["node_bm_05", "node_bm_06"],
                 {"execute_threshold_percent": 15.0}, 0.0, 450.0, ResonanceType.NONE.value),
                ("node_bm_08", "constellation_blade_master", "Blade Storm",
                 "Keystone: become a storm of steel, devastating all around you.",
                 TalentNodeType.KEYSTONE.value, 1, 5, ["node_bm_07"],
                 {"blade_storm_damage": 120.0}, 0.0, 550.0, ResonanceType.FIRE.value),

                # The Arcane Weaver (arcane)
                ("node_aw_01", "constellation_arcane_weaver", "Arcane Fundamentals",
                 "Expands the mana pool through foundational study.",
                 TalentNodeType.PASSIVE.value, 5, 1, [],
                 {"max_mana": 20.0}, 0.0, 100.0, ResonanceType.ARCANE.value),
                ("node_aw_02", "constellation_arcane_weaver", "Spell Focus",
                 "Concentrates magical energy to raise spell power.",
                 TalentNodeType.PASSIVE.value, 5, 1, ["node_aw_01"],
                 {"spell_power": 6.0}, -80.0, 200.0, ResonanceType.ARCANE.value),
                ("node_aw_03", "constellation_arcane_weaver", "Frost Bolt",
                 "Hurls a shard of ice that chills the target.",
                 TalentNodeType.ACTIVE.value, 1, 2, ["node_aw_01"],
                 {"frost_damage": 30.0}, 80.0, 200.0, ResonanceType.FROST.value),
                ("node_aw_04", "constellation_arcane_weaver", "Fire Ball",
                 "Launches a roaring sphere of flame at the enemy.",
                 TalentNodeType.ACTIVE.value, 1, 2, ["node_aw_01"],
                 {"fire_damage": 35.0}, 160.0, 200.0, ResonanceType.FIRE.value),
                ("node_aw_05", "constellation_arcane_weaver", "Mana Surge",
                 "Accelerates mana regeneration between casts.",
                 TalentNodeType.PASSIVE.value, 3, 1, ["node_aw_02"],
                 {"mana_regen_percent": 4.0}, -150.0, 300.0, ResonanceType.ARCANE.value),
                ("node_aw_06", "constellation_arcane_weaver", "Elemental Fusion",
                 "Combines elements for greater destructive output.",
                 TalentNodeType.PASSIVE.value, 3, 2, ["node_aw_03", "node_aw_04"],
                 {"elemental_damage_percent": 3.0}, 120.0, 320.0, ResonanceType.LIGHTNING.value),
                ("node_aw_07", "constellation_arcane_weaver", "Spell Weaving",
                 "Milestone: chain spells together with rising speed.",
                 TalentNodeType.MILESTONE.value, 1, 3, ["node_aw_05", "node_aw_06"],
                 {"cast_speed_percent": 10.0}, 0.0, 430.0, ResonanceType.ARCANE.value),
                ("node_aw_08", "constellation_arcane_weaver", "Arcane Nova",
                 "Keystone: unleash a shockwave of pure arcane force.",
                 TalentNodeType.KEYSTONE.value, 1, 5, ["node_aw_07"],
                 {"arcane_nova_damage": 140.0}, 0.0, 540.0, ResonanceType.ARCANE.value),

                # The Survivor (survival)
                ("node_sv_01", "constellation_survivor", "Toughness",
                 "Reinforces the body to withstand heavier blows.",
                 TalentNodeType.PASSIVE.value, 5, 1, [],
                 {"max_health": 30.0}, 0.0, 100.0, ResonanceType.EARTH.value),
                ("node_sv_02", "constellation_survivor", "Regeneration",
                 "Speeds up natural recovery of lost health.",
                 TalentNodeType.PASSIVE.value, 3, 1, ["node_sv_01"],
                 {"health_regen_percent": 2.0}, -80.0, 200.0, ResonanceType.EARTH.value),
                ("node_sv_03", "constellation_survivor", "Foraging",
                 "Improves the yield of gathered provisions.",
                 TalentNodeType.PASSIVE.value, 3, 1, ["node_sv_01"],
                 {"gathering_yield_percent": 5.0}, 80.0, 200.0, ResonanceType.EARTH.value),
                ("node_sv_04", "constellation_survivor", "Second Wind",
                 "Restores a surge of health when wounded in battle.",
                 TalentNodeType.ACTIVE.value, 1, 2, ["node_sv_02"],
                 {"heal_amount": 80.0}, -150.0, 320.0, ResonanceType.HOLY.value),
                ("node_sv_05", "constellation_survivor", "Iron Skin",
                 "Hardens the skin to reduce incoming physical damage.",
                 TalentNodeType.PASSIVE.value, 3, 2, ["node_sv_02", "node_sv_03"],
                 {"armor": 8.0}, 120.0, 320.0, ResonanceType.EARTH.value),
                ("node_sv_06", "constellation_survivor", "Undying",
                 "Keystone: cheat death once when struck down.",
                 TalentNodeType.KEYSTONE.value, 1, 5, ["node_sv_04", "node_sv_05"],
                 {"cheat_death_cooldown": 300.0}, 0.0, 440.0, ResonanceType.HOLY.value),

                # The Shadow Dancer (shadow)
                ("node_sd_01", "constellation_shadow_dancer", "Stealth",
                 "Grants the ability to move unseen among foes.",
                 TalentNodeType.PASSIVE.value, 3, 1, [],
                 {"stealth_power": 5.0}, 0.0, 100.0, ResonanceType.DARK.value),
                ("node_sd_02", "constellation_shadow_dancer", "Backstab",
                 "Deals amplified damage when striking from stealth.",
                 TalentNodeType.ACTIVE.value, 3, 2, ["node_sd_01"],
                 {"crit_damage_percent": 8.0}, -80.0, 200.0, ResonanceType.DARK.value),
                ("node_sd_03", "constellation_shadow_dancer", "Evasion",
                 "Raises the chance to dodge incoming attacks.",
                 TalentNodeType.PASSIVE.value, 3, 1, ["node_sd_01"],
                 {"dodge_chance_percent": 2.0}, 80.0, 200.0, ResonanceType.WIND.value),
                ("node_sd_04", "constellation_shadow_dancer", "Shadow Step",
                 "Blink through shadow to a target location instantly.",
                 TalentNodeType.ACTIVE.value, 1, 3, ["node_sd_02", "node_sd_03"],
                 {"blink_range": 15.0}, 0.0, 320.0, ResonanceType.DARK.value),
                ("node_sd_05", "constellation_shadow_dancer", "Venom",
                 "Coats blades with toxin that festers over time.",
                 TalentNodeType.PASSIVE.value, 3, 2, ["node_sd_02"],
                 {"poison_damage": 6.0}, -150.0, 320.0, ResonanceType.DARK.value),
                ("node_sd_06", "constellation_shadow_dancer", "Shadow Dance",
                 "Keystone: become a blur of deadly shadow strikes.",
                 TalentNodeType.KEYSTONE.value, 1, 5, ["node_sd_04", "node_sd_05"],
                 {"shadow_dance_damage": 110.0}, 0.0, 440.0, ResonanceType.DARK.value),

                # The Void Touched (void)
                ("node_vt_01", "constellation_void_touched", "Void Whisper",
                 "Hear the abyss, deepening your reserve of power.",
                 TalentNodeType.PASSIVE.value, 3, 1, [],
                 {"insanity_cap": 10.0}, 0.0, 100.0, ResonanceType.VOID.value),
                ("node_vt_02", "constellation_void_touched", "Eldritch Bolt",
                 "Hurls a bolt of unmaking that tears at reality.",
                 TalentNodeType.ACTIVE.value, 1, 2, ["node_vt_01"],
                 {"void_damage": 45.0}, -80.0, 220.0, ResonanceType.VOID.value),
                ("node_vt_03", "constellation_void_touched", "Null Shield",
                 "Wraps the bearer in a barrier of consuming emptiness.",
                 TalentNodeType.ACTIVE.value, 1, 2, ["node_vt_01"],
                 {"absorb_amount": 60.0}, 80.0, 220.0, ResonanceType.VOID.value),
                ("node_vt_04", "constellation_void_touched", "Reality Tear",
                 "Sunders the fabric of space for sustained void damage.",
                 TalentNodeType.PASSIVE.value, 3, 2, ["node_vt_02", "node_vt_03"],
                 {"void_damage_percent": 4.0}, 0.0, 340.0, ResonanceType.VOID.value),
                ("node_vt_05", "constellation_void_touched", "Void Form",
                 "Keystone: transform into a vessel of raw void energy.",
                 TalentNodeType.KEYSTONE.value, 1, 5, ["node_vt_04"],
                 {"void_form_duration": 12.0}, 0.0, 450.0, ResonanceType.VOID.value),
            ]
            for (nid, cid, name, desc, ntype, mr, cost, prereqs,
                 effects, px, py, res) in node_defs:
                self.register_talent_node(
                    nid, cid, name, description=desc, node_type=ntype,
                    max_rank=mr, point_cost_per_rank=cost,
                    prerequisite_node_ids=prereqs, effects=effects,
                    position_x=px, position_y=py, resonance_type=res,
                )

            # -- Talent paths ----------------------------------------------
            # Tuple: (path_id, constellation_id, from_node_id, to_node_id)
            path_defs = [
                # Blade Master
                ("path_bm_01", "constellation_blade_master", "node_bm_01", "node_bm_02"),
                ("path_bm_02", "constellation_blade_master", "node_bm_01", "node_bm_03"),
                ("path_bm_03", "constellation_blade_master", "node_bm_02", "node_bm_04"),
                ("path_bm_04", "constellation_blade_master", "node_bm_03", "node_bm_05"),
                ("path_bm_05", "constellation_blade_master", "node_bm_04", "node_bm_06"),
                ("path_bm_06", "constellation_blade_master", "node_bm_05", "node_bm_07"),
                ("path_bm_07", "constellation_blade_master", "node_bm_06", "node_bm_07"),
                ("path_bm_08", "constellation_blade_master", "node_bm_07", "node_bm_08"),
                # Arcane Weaver
                ("path_aw_01", "constellation_arcane_weaver", "node_aw_01", "node_aw_02"),
                ("path_aw_02", "constellation_arcane_weaver", "node_aw_01", "node_aw_03"),
                ("path_aw_03", "constellation_arcane_weaver", "node_aw_01", "node_aw_04"),
                ("path_aw_04", "constellation_arcane_weaver", "node_aw_02", "node_aw_05"),
                ("path_aw_05", "constellation_arcane_weaver", "node_aw_03", "node_aw_06"),
                ("path_aw_06", "constellation_arcane_weaver", "node_aw_04", "node_aw_06"),
                ("path_aw_07", "constellation_arcane_weaver", "node_aw_05", "node_aw_07"),
                ("path_aw_08", "constellation_arcane_weaver", "node_aw_06", "node_aw_07"),
                ("path_aw_09", "constellation_arcane_weaver", "node_aw_07", "node_aw_08"),
                # Survivor
                ("path_sv_01", "constellation_survivor", "node_sv_01", "node_sv_02"),
                ("path_sv_02", "constellation_survivor", "node_sv_01", "node_sv_03"),
                ("path_sv_03", "constellation_survivor", "node_sv_02", "node_sv_04"),
                ("path_sv_04", "constellation_survivor", "node_sv_02", "node_sv_05"),
                ("path_sv_05", "constellation_survivor", "node_sv_03", "node_sv_05"),
                ("path_sv_06", "constellation_survivor", "node_sv_04", "node_sv_06"),
                ("path_sv_07", "constellation_survivor", "node_sv_05", "node_sv_06"),
                # Shadow Dancer
                ("path_sd_01", "constellation_shadow_dancer", "node_sd_01", "node_sd_02"),
                ("path_sd_02", "constellation_shadow_dancer", "node_sd_01", "node_sd_03"),
                ("path_sd_03", "constellation_shadow_dancer", "node_sd_02", "node_sd_04"),
                ("path_sd_04", "constellation_shadow_dancer", "node_sd_03", "node_sd_04"),
                ("path_sd_05", "constellation_shadow_dancer", "node_sd_02", "node_sd_05"),
                ("path_sd_06", "constellation_shadow_dancer", "node_sd_04", "node_sd_06"),
                ("path_sd_07", "constellation_shadow_dancer", "node_sd_05", "node_sd_06"),
                # Void Touched
                ("path_vt_01", "constellation_void_touched", "node_vt_01", "node_vt_02"),
                ("path_vt_02", "constellation_void_touched", "node_vt_01", "node_vt_03"),
                ("path_vt_03", "constellation_void_touched", "node_vt_02", "node_vt_04"),
                ("path_vt_04", "constellation_void_touched", "node_vt_03", "node_vt_04"),
                ("path_vt_05", "constellation_void_touched", "node_vt_04", "node_vt_05"),
            ]
            for pid, cid, from_n, to_n in path_defs:
                self.register_path(
                    pid, cid, from_node_id=from_n, to_node_id=to_n,
                    is_bidirectional=True, required_rank=1,
                )

            # -- Resonance bonuses -----------------------------------------
            resonance_defs = [
                ("resonance_inferno", "Inferno Resonance",
                 "Three or more fire-aligned nodes ignite a burning aura.",
                 ResonanceType.FIRE.value, 3, "fire_damage", 10.0, True),
                ("resonance_glacier", "Glacier Resonance",
                 "Three or more frost-aligned nodes summon a biting chill.",
                 ResonanceType.FROST.value, 3, "frost_damage", 10.0, True),
                ("resonance_storm", "Storm Resonance",
                 "Three or more lightning-aligned nodes crackle with power.",
                 ResonanceType.LIGHTNING.value, 3, "lightning_damage", 10.0, True),
                ("resonance_arcane", "Arcane Resonance",
                 "Two or more arcane-aligned nodes amplify spellcraft.",
                 ResonanceType.ARCANE.value, 2, "spell_power", 15.0, False),
                ("resonance_void", "Void Resonance",
                 "Two or more void-aligned nodes erode nearby reality.",
                 ResonanceType.VOID.value, 2, "void_damage", 8.0, True),
                ("resonance_radiant", "Radiant Resonance",
                 "Two or more holy-aligned nodes radiate restorative light.",
                 ResonanceType.HOLY.value, 2, "healing_power", 12.0, True),
            ]
            for bid, name, desc, rtype, req, stat, val, pct in resonance_defs:
                self.register_resonance_bonus(
                    bid, name, resonance_type=rtype, required_count=req,
                    target_stat=stat, bonus_value=val, is_percentage=pct,
                    description=desc,
                )

            # -- Player progress records -----------------------------------
            warrior = self._get_or_create_progress(
                "player_warrior", "constellation_blade_master", 30
            )
            if warrior is not None:
                warrior.node_ranks["node_bm_01"] = 3
                warrior.node_ranks["node_bm_02"] = 2
                warrior.node_ranks["node_bm_04"] = 1
                warrior.allocated_points = 6
                warrior.activated_at = _now() - 3600
                warrior.last_updated = _now() - 60
                self._recompute_states(warrior, "constellation_blade_master")

            mage = self._get_or_create_progress(
                "player_mage", "constellation_arcane_weaver", 30
            )
            if mage is not None:
                mage.node_ranks["node_aw_01"] = 5
                mage.node_ranks["node_aw_02"] = 3
                mage.node_ranks["node_aw_03"] = 1
                mage.node_ranks["node_aw_05"] = 1
                mage.allocated_points = 10
                mage.activated_at = _now() - 7200
                mage.last_updated = _now() - 30
                self._recompute_states(mage, "constellation_arcane_weaver")

            self._update_stats()
            self._initialized = True

    def reset(self) -> None:
        with _LOCK:
            self._constellations.clear()
            self._nodes.clear()
            self._paths.clear()
            self._resonance_bonuses.clear()
            self._player_progress.clear()
            self._events.clear()
            self._stats = TalentConstellationStats()
            self._config = TalentConstellationConfig()
            self._tick_count = 0
            self._initialized = False
            self._emit(TalentConstellationEventKind.RESET.value, {})
            self._seed()


# ---------------------------------------------------------------------------
# Module-level singleton factory
# ---------------------------------------------------------------------------

def get_talent_constellation_system() -> TalentConstellationSystem:
    """Factory that returns the singleton TalentConstellationSystem instance."""
    return TalentConstellationSystem.get_instance()
