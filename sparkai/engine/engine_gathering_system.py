"""
SparkLabs Engine - Gathering System

A resource collection system for the SparkLabs AI-native game engine.
Manages harvestable resource nodes (mining veins, herb patches, fishing
spots, woodcutting trees, hunting grounds), tool requirements, yield
calculation with skill-based bonuses, node depletion and regeneration
cycles, and gathering minigame state tracking.

Each resource node has a type, position, maximum yield, current remaining
amount, required tool tier, skill requirement, regeneration timer, and
loot table for yield distribution. Designed for survival crafting games,
MMORPG gathering professions, and farming simulations.

Architecture:
  GatheringSystem (singleton)
    |-- ResourceType, NodeState, GatherEventKind, MinigamePhase
    |-- YieldEntry, ResourceNode, ToolSpec, GatherSession,
       GatherConfig, GatherStats, GatherSnapshot, GatherEvent
    |-- get_gathering_system

Core Capabilities:
  - register_node / remove_node / get_node / list_nodes: manage
    harvestable resource nodes in the world.
  - register_tool / get_tool / list_tools: define gathering tools
    with tier, efficiency, and applicable resource types.
  - start_gather / complete_gather / cancel_gather: execute gathering
    operations with tool checks, skill validation, yield rolls, and
    node depletion.
  - list_sessions / get_session: track active and completed gathering
    operations.
  - tick: advance node regeneration timers and active gathering
    sessions.
  - set_config / get_config: global tuning for max nodes, regen
    rates, and yield multipliers.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`GatheringSystem.get_instance` or the module-level
:func:`get_gathering_system` factory.
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_NODES: int = 2000
_MAX_TOOLS: int = 200
_MAX_SESSIONS: int = 500
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


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


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
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

class ResourceType(str, Enum):
    """Type of harvestable resource."""
    MINING = "mining"
    HERBALISM = "herbalism"
    FISHING = "fishing"
    WOODCUTTING = "woodcutting"
    HUNTING = "hunting"
    FARMING = "farming"
    SKINNING = "skinning"
    SALVAGING = "salvaging"


class NodeState(str, Enum):
    """Operational state of a resource node."""
    AVAILABLE = "available"
    DEPLETED = "depleted"
    REGENERATING = "regenerating"
    LOCKED = "locked"
    REMOVED = "removed"


class MinigamePhase(str, Enum):
    """Phase of a gathering minigame."""
    IDLE = "idle"
    CASTING = "casting"
    WAITING = "waiting"
    HOOKED = "hooked"
    REELING = "reeling"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GatherEventKind(str, Enum):
    """Audit event types emitted by the gathering system."""
    NODE_REGISTERED = "node_registered"
    NODE_REMOVED = "node_removed"
    NODE_DEPLETED = "node_depleted"
    NODE_REGENERATED = "node_regenerated"
    TOOL_REGISTERED = "tool_registered"
    GATHER_STARTED = "gather_started"
    GATHER_COMPLETED = "gather_completed"
    GATHER_CANCELLED = "gather_cancelled"
    GATHER_FAILED = "gather_failed"
    YIELD_AWARDED = "yield_awarded"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class YieldEntry:
    """A possible yield item from a resource node."""
    item_id: str
    item_name: str = ""
    min_quantity: int = 1
    max_quantity: int = 1
    drop_chance: float = 1.0
    quality_min: float = 0.0
    quality_max: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ToolSpec:
    """Specification of a gathering tool."""
    tool_id: str
    name: str = ""
    tool_type: str = ResourceType.MINING.value
    tier: int = 1
    efficiency: float = 1.0
    durability: int = 100
    max_durability: int = 100
    bonus_yield_percent: float = 0.0
    bonus_speed_percent: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ResourceNode:
    """A harvestable resource node in the world."""
    node_id: str
    name: str = ""
    resource_type: str = ResourceType.MINING.value
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    state: str = NodeState.AVAILABLE.value
    max_yield: int = 10
    current_yield: int = 10
    required_tool_tier: int = 1
    required_skill_level: int = 1
    base_gather_time: float = 3.0
    regen_time: float = 60.0
    regen_timer: float = 0.0
    yield_table: List[YieldEntry] = field(default_factory=list)
    locked_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GatherSession:
    """An active or completed gathering operation."""
    session_id: str
    node_id: str
    player_id: str
    tool_id: str = ""
    resource_type: str = ResourceType.MINING.value
    phase: str = MinigamePhase.IDLE.value
    skill_level: int = 1
    gather_time: float = 3.0
    elapsed: float = 0.0
    yield_results: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = False
    started_at: float = field(default_factory=_now)
    completed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GatherConfig:
    """Global tuning parameters for the gathering system."""
    max_nodes: int = 1000
    max_tools: int = 100
    max_sessions: int = 200
    global_yield_multiplier: float = 1.0
    global_regen_multiplier: float = 1.0
    skill_bonus_per_level: float = 0.05
    tool_durability_loss_per_gather: int = 1
    auto_deplete_on_zero: bool = True
    tick_rate_hz: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GatherStats:
    """Aggregate statistics for the gathering system."""
    total_nodes: int = 0
    available_nodes: int = 0
    depleted_nodes: int = 0
    total_tools: int = 0
    total_gathers: int = 0
    successful_gathers: int = 0
    failed_gathers: int = 0
    cancelled_gathers: int = 0
    total_yield_items: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GatherSnapshot:
    """Full state snapshot of the gathering system."""
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    active_sessions: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GatherEvent:
    """An audit event emitted by the gathering system."""
    event_id: str
    kind: str
    timestamp: float
    node_id: Optional[str] = None
    player_id: Optional[str] = None
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Gathering System
# ---------------------------------------------------------------------------

class GatheringSystem:
    """Manages resource nodes, gathering tools, and harvest operations."""

    _instance: Optional["GatheringSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._nodes: Dict[str, ResourceNode] = {}
        self._tools: Dict[str, ToolSpec] = {}
        self._sessions: Dict[str, GatherSession] = {}
        self._events: List[GatherEvent] = []
        self._stats = GatherStats()
        self._config = GatherConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._session_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "GatheringSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample resource nodes and tools."""
        iron_vein = ResourceNode(
            node_id="node_iron_vein_01",
            name="Iron Ore Vein",
            resource_type=ResourceType.MINING.value,
            position=(50.0, 0.0, 30.0),
            max_yield=15,
            current_yield=15,
            required_tool_tier=1,
            required_skill_level=1,
            base_gather_time=3.0,
            regen_time=120.0,
            yield_table=[
                YieldEntry(item_id="ore_iron", item_name="Iron Ore", min_quantity=1, max_quantity=3, drop_chance=1.0),
                YieldEntry(item_id="gem_ruby", item_name="Ruby", min_quantity=1, max_quantity=1, drop_chance=0.05),
            ],
        )
        self._nodes[iron_vein.node_id] = iron_vein

        herb_patch = ResourceNode(
            node_id="node_herb_patch_01",
            name="Embergrass Patch",
            resource_type=ResourceType.HERBALISM.value,
            position=(20.0, 0.0, 80.0),
            max_yield=8,
            current_yield=8,
            required_tool_tier=0,
            required_skill_level=1,
            base_gather_time=2.0,
            regen_time=60.0,
            yield_table=[
                YieldEntry(item_id="herb_embergrass", item_name="Embergrass", min_quantity=1, max_quantity=2, drop_chance=1.0),
                YieldEntry(item_id="seed_embergrass", item_name="Embergrass Seed", min_quantity=1, max_quantity=1, drop_chance=0.2),
            ],
        )
        self._nodes[herb_patch.node_id] = herb_patch

        fishing_spot = ResourceNode(
            node_id="node_fishing_spot_01",
            name="Crystal Lake Fishing Spot",
            resource_type=ResourceType.FISHING.value,
            position=(0.0, 0.0, 100.0),
            max_yield=20,
            current_yield=20,
            required_tool_tier=1,
            required_skill_level=1,
            base_gather_time=5.0,
            regen_time=30.0,
            yield_table=[
                YieldEntry(item_id="fish_trout", item_name="Rainbow Trout", min_quantity=1, max_quantity=1, drop_chance=0.5),
                YieldEntry(item_id="fish_bass", item_name="Largemouth Bass", min_quantity=1, max_quantity=1, drop_chance=0.3),
                YieldEntry(item_id="fish_golden", item_name="Golden Koi", min_quantity=1, max_quantity=1, drop_chance=0.02),
            ],
        )
        self._nodes[fishing_spot.node_id] = fishing_spot

        pickaxe = ToolSpec(
            tool_id="tool_pickaxe_iron",
            name="Iron Pickaxe",
            tool_type=ResourceType.MINING.value,
            tier=1,
            efficiency=1.0,
            durability=100,
            max_durability=100,
            bonus_yield_percent=0.0,
            bonus_speed_percent=0.0,
        )
        self._tools[pickaxe.tool_id] = pickaxe

        fishing_rod = ToolSpec(
            tool_id="tool_fishing_rod_01",
            name="Basic Fishing Rod",
            tool_type=ResourceType.FISHING.value,
            tier=1,
            efficiency=1.0,
            durability=80,
            max_durability=80,
        )
        self._tools[fishing_rod.tool_id] = fishing_rod

        self._stats.total_nodes = len(self._nodes)
        self._stats.available_nodes = len(self._nodes)
        self._stats.total_tools = len(self._tools)
        self._initialized = True

    # ------------------------------------------------------------------
    # Node Management
    # ------------------------------------------------------------------

    def register_node(self, node: ResourceNode) -> Dict[str, Any]:
        if not node.node_id:
            node.node_id = f"node_{_new_id()}"
        node.created_at = _now()
        node.updated_at = _now()
        if len(self._nodes) >= _MAX_NODES:
            oldest = next(iter(self._nodes), None)
            if oldest:
                self._nodes.pop(oldest, None)
        self._nodes[node.node_id] = node
        self._stats.total_nodes = len(self._nodes)
        if node.state == NodeState.AVAILABLE.value:
            self._stats.available_nodes += 1
        self._record_event(GatherEventKind.NODE_REGISTERED, node_id=node.node_id,
                           details={"name": node.name, "type": node.resource_type})
        return {"node_id": node.node_id, "registered": True}

    def remove_node(self, node_id: str) -> Dict[str, Any]:
        node = self._nodes.pop(node_id, None)
        if node is None:
            return {"node_id": node_id, "removed": False}
        if node.state == NodeState.AVAILABLE.value:
            self._stats.available_nodes = max(0, self._stats.available_nodes - 1)
        self._stats.total_nodes = len(self._nodes)
        self._record_event(GatherEventKind.NODE_REMOVED, node_id=node_id)
        return {"node_id": node_id, "removed": True}

    def get_node(self, node_id: str) -> Optional[ResourceNode]:
        return self._nodes.get(node_id)

    def list_nodes(self, resource_type: Optional[str] = None, state: Optional[str] = None,
                   limit: int = 100) -> List[ResourceNode]:
        result = []
        for n in self._nodes.values():
            if resource_type is not None and n.resource_type != resource_type:
                continue
            if state is not None and n.state != state:
                continue
            result.append(n)
        return result[:limit]

    # ------------------------------------------------------------------
    # Tool Management
    # ------------------------------------------------------------------

    def register_tool(self, tool: ToolSpec) -> Dict[str, Any]:
        if not tool.tool_id:
            tool.tool_id = f"tool_{_new_id()}"
        if len(self._tools) >= _MAX_TOOLS:
            oldest = next(iter(self._tools), None)
            if oldest:
                self._tools.pop(oldest, None)
        self._tools[tool.tool_id] = tool
        self._stats.total_tools = len(self._tools)
        self._record_event(GatherEventKind.TOOL_REGISTERED,
                           details={"tool_id": tool.tool_id, "name": tool.name})
        return {"tool_id": tool.tool_id, "registered": True}

    def get_tool(self, tool_id: str) -> Optional[ToolSpec]:
        return self._tools.get(tool_id)

    def list_tools(self, tool_type: Optional[str] = None, limit: int = 100) -> List[ToolSpec]:
        result = []
        for t in self._tools.values():
            if tool_type is not None and t.tool_type != tool_type:
                continue
            result.append(t)
        return result[:limit]

    # ------------------------------------------------------------------
    # Gathering Operations
    # ------------------------------------------------------------------

    def start_gather(self, node_id: str, player_id: str, tool_id: str = "",
                     skill_level: int = 1) -> Dict[str, Any]:
        node = self._nodes.get(node_id)
        if node is None:
            return {"success": False, "reason": "node_not_found"}
        if node.state != NodeState.AVAILABLE.value:
            return {"success": False, "reason": "node_unavailable", "state": node.state}
        if node.current_yield <= 0:
            return {"success": False, "reason": "node_depleted"}
        if skill_level < node.required_skill_level:
            return {"success": False, "reason": "skill_too_low",
                    "required": node.required_skill_level, "actual": skill_level}

        tool = None
        if tool_id:
            tool = self._tools.get(tool_id)
            if tool is None:
                return {"success": False, "reason": "tool_not_found"}
            if tool.tier < node.required_tool_tier:
                return {"success": False, "reason": "tool_tier_too_low",
                        "required": node.required_tool_tier, "actual": tool.tier}

        gather_time = node.base_gather_time
        if tool and tool.bonus_speed_percent > 0:
            gather_time *= (1.0 - _clamp(tool.bonus_speed_percent / 100.0, 0.0, 0.9))

        session_id = f"sess_{self._session_counter}"
        self._session_counter += 1
        session = GatherSession(
            session_id=session_id,
            node_id=node_id,
            player_id=player_id,
            tool_id=tool_id,
            resource_type=node.resource_type,
            phase=MinigamePhase.CASTING.value,
            skill_level=skill_level,
            gather_time=gather_time,
        )
        self._sessions[session_id] = session
        if len(self._sessions) > _MAX_SESSIONS:
            oldest = next(iter(self._sessions), None)
            if oldest:
                self._sessions.pop(oldest, None)

        node.locked_by = player_id
        node.updated_at = _now()

        self._record_event(GatherEventKind.GATHER_STARTED, node_id=node_id, player_id=player_id,
                           session_id=session_id,
                           details={"tool_id": tool_id, "gather_time": gather_time})
        return {"success": True, "session_id": session_id, "gather_time": gather_time}

    def complete_gather(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {"success": False, "reason": "session_not_found"}
        node = self._nodes.get(session.node_id)
        if node is None:
            return {"success": False, "reason": "node_not_found"}

        tool = self._tools.get(session.tool_id) if session.tool_id else None
        skill_bonus = session.skill_level * self._config.skill_bonus_per_level
        tool_bonus = (tool.bonus_yield_percent / 100.0) if tool else 0.0
        total_multiplier = (1.0 + skill_bonus + tool_bonus) * self._config.global_yield_multiplier

        yield_results = []
        total_items = 0
        for entry in node.yield_table:
            if random.random() > entry.drop_chance:
                continue
            base_qty = random.randint(entry.min_quantity, entry.max_quantity)
            adjusted_qty = max(1, int(base_qty * total_multiplier))
            quality = random.uniform(entry.quality_min, entry.quality_max) if entry.quality_max > entry.quality_min else entry.quality_max
            yield_results.append({
                "item_id": entry.item_id,
                "item_name": entry.item_name,
                "quantity": adjusted_qty,
                "quality": round(quality, 4),
            })
            total_items += adjusted_qty

        node.current_yield = max(0, node.current_yield - 1)
        node.locked_by = ""
        node.updated_at = _now()

        if node.current_yield <= 0 and self._config.auto_deplete_on_zero:
            node.state = NodeState.DEPLETED.value
            node.regen_timer = node.regen_time * self._config.global_regen_multiplier
            self._stats.depleted_nodes += 1
            self._stats.available_nodes = max(0, self._stats.available_nodes - 1)
            self._record_event(GatherEventKind.NODE_DEPLETED, node_id=node.node_id)

        if tool and self._config.tool_durability_loss_per_gather > 0:
            tool.durability = max(0, tool.durability - self._config.tool_durability_loss_per_gather)

        session.phase = MinigamePhase.SUCCESS.value
        session.success = True
        session.yield_results = yield_results
        session.completed_at = _now()

        self._stats.total_gathers += 1
        self._stats.successful_gathers += 1
        self._stats.total_yield_items += total_items

        self._record_event(GatherEventKind.GATHER_COMPLETED, node_id=node.node_id,
                           player_id=session.player_id, session_id=session_id,
                           details={"yield_count": len(yield_results), "total_items": total_items})
        return {
            "success": True,
            "session_id": session_id,
            "node_id": node.node_id,
            "yield": yield_results,
            "total_items": total_items,
            "node_remaining": node.current_yield,
        }

    def cancel_gather(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {"success": False, "reason": "session_not_found"}
        session.phase = MinigamePhase.CANCELLED.value
        session.completed_at = _now()
        node = self._nodes.get(session.node_id)
        if node:
            node.locked_by = ""
            node.updated_at = _now()
        self._stats.total_gathers += 1
        self._stats.cancelled_gathers += 1
        self._record_event(GatherEventKind.GATHER_CANCELLED, node_id=session.node_id,
                           player_id=session.player_id, session_id=session_id)
        return {"success": True, "session_id": session_id, "cancelled": True}

    def get_session(self, session_id: str) -> Optional[GatherSession]:
        return self._sessions.get(session_id)

    def list_sessions(self, player_id: Optional[str] = None, node_id: Optional[str] = None,
                      phase: Optional[str] = None, limit: int = 100) -> List[GatherSession]:
        result = []
        for s in self._sessions.values():
            if player_id is not None and s.player_id != player_id:
                continue
            if node_id is not None and s.node_id != node_id:
                continue
            if phase is not None and s.phase != phase:
                continue
            result.append(s)
        return result[:limit]

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.1) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        regenerated = []
        for node in self._nodes.values():
            if node.state == NodeState.DEPLETED.value:
                node.regen_timer -= delta_time
                if node.regen_timer <= 0:
                    node.state = NodeState.AVAILABLE.value
                    node.current_yield = node.max_yield
                    node.regen_timer = 0.0
                    node.updated_at = _now()
                    self._stats.depleted_nodes = max(0, self._stats.depleted_nodes - 1)
                    self._stats.available_nodes += 1
                    regenerated.append(node.node_id)
        if regenerated:
            for nid in regenerated:
                self._record_event(GatherEventKind.NODE_REGENERATED, node_id=nid)
        return {"tick_count": self._tick_count, "regenerated": regenerated}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def get_config(self) -> GatherConfig:
        return self._config

    def set_config(self, config: GatherConfig) -> Dict[str, Any]:
        self._config = config
        self._record_event(GatherEventKind.CONFIG_UPDATED)
        return {"updated": True}

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _record_event(self, kind: GatherEventKind, node_id: Optional[str] = None,
                      player_id: Optional[str] = None, session_id: Optional[str] = None,
                      details: Optional[Dict[str, Any]] = None) -> None:
        event_id = f"evt_{self._event_counter}"
        self._event_counter += 1
        event = GatherEvent(
            event_id=event_id,
            kind=kind.value,
            timestamp=_now(),
            node_id=node_id,
            player_id=player_id,
            session_id=session_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, node_id: Optional[str] = None, player_id: Optional[str] = None,
                    kind: Optional[str] = None, limit: int = 100) -> List[GatherEvent]:
        result = []
        for e in reversed(self._events):
            if node_id is not None and e.node_id != node_id:
                continue
            if player_id is not None and e.player_id != player_id:
                continue
            if kind is not None and e.kind != kind:
                continue
            result.append(e)
            if len(result) >= limit:
                break
        return result

    def get_stats(self) -> GatherStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_nodes": len(self._nodes),
            "available_nodes": self._stats.available_nodes,
            "depleted_nodes": self._stats.depleted_nodes,
            "total_tools": len(self._tools),
            "active_sessions": sum(1 for s in self._sessions.values()
                                   if s.phase not in (MinigamePhase.SUCCESS.value,
                                                       MinigamePhase.FAILED.value,
                                                       MinigamePhase.CANCELLED.value)),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> GatherSnapshot:
        return GatherSnapshot(
            nodes=[n.to_dict() for n in self._nodes.values()],
            tools=[t.to_dict() for t in self._tools.values()],
            active_sessions=[s.to_dict() for s in self._sessions.values()
                             if s.phase not in (MinigamePhase.SUCCESS.value,
                                                 MinigamePhase.FAILED.value,
                                                 MinigamePhase.CANCELLED.value)],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Dict[str, Any]:
        with self._init_lock:
            self._nodes.clear()
            self._tools.clear()
            self._sessions.clear()
            self._events.clear()
            self._stats = GatherStats()
            self._config = GatherConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._session_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(GatherEventKind.RESET)
        return {"reset": True, "initialized": self._initialized}


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_gathering_system() -> GatheringSystem:
    return GatheringSystem.get_instance()
