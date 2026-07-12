"""
SparkLabs Engine - Gem Socketing System

Provides equipment socket management where players insert gems into
socketed items to gain stat bonuses, set effects, and conditional
modifiers. Sockets can be unlocked, gems crafted, and set bonuses
triggered when multiple gems of the same set are equipped across
a character's gear.

Architecture:
  GemSocketingSystem (singleton)
    |-- GemType, GemRarity, SocketColor, SocketState, GemSetBonusType,
       SocketEventKind
    |-- GemDefinition, GemSetDefinition, SocketDefinition,
       SocketedGem, PlayerSocketItem, GemCraftRecipe, GemCraftResult,
       SocketBonus, SocketConfig, SocketStats, SocketSnapshot, SocketEvent
    |-- get_gem_socketing_system

Core Capabilities:
  - register_gem / remove_gem / get_gem / list_gems
  - register_gem_set / get_gem_set / list_gem_sets
  - register_socket_item / get_socket_item / list_socket_items
  - add_socket_to_item / unlock_socket / get_socket
  - insert_gem / remove_gem / get_socketed_gems
  - compute_socket_bonuses / compute_set_bonuses
  - get_player_bonuses / get_active_set_bonuses
  - register_recipe / get_recipe / list_recipes / craft_gem
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`GemSocketingSystem.get_instance` or the module-level
:func:`get_gem_socketing_system` factory.
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

_MAX_GEMS: int = 1000
_MAX_GEM_SETS: int = 100
_MAX_SOCKET_ITEMS: int = 5000
_MAX_PLAYER_SOCKET_ITEMS: int = 500000
_MAX_RECIPES: int = 500
_MAX_CRAFT_HISTORY: int = 50000
_MAX_SOCKET_EVENTS: int = 20000
_MAX_BONUS_HISTORY: int = 10000


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
    """Recursively convert dataclass instances to dictionaries.

    Inspects ``__dataclass_fields__`` BEFORE checking for ``to_dict`` so
    that custom ``to_dict`` implementations can layer computed fields on
    top without recursing into this helper.
    """
    if obj is None:
        return None
    if isinstance(obj, list):
        return [_dataclass_to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        out: Dict[str, Any] = {}
        for fname in obj.__dataclass_fields__:
            out[fname] = _dataclass_to_dict(getattr(obj, fname, None))
        return out
    if isinstance(obj, Enum):
        return obj.value
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GemType(str, Enum):
    RUBY = "ruby"
    SAPPHIRE = "sapphire"
    EMERALD = "emerald"
    TOPAZ = "topaz"
    AMETHYST = "amethyst"
    DIAMOND = "diamond"
    ONYX = "onyx"
    OPAL = "opal"
    PEARL = "pearl"
    ALEXANDRITE = "alexandrite"


class GemRarity(str, Enum):
    CHIPPED = "chipped"
    FLAWED = "flawed"
    COMMON = "common"
    FLAWLESS = "flawless"
    PERFECT = "perfect"
    RADIANT = "radiant"
    MYTHIC = "mythic"


class SocketColor(str, Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    PURPLE = "purple"
    ORANGE = "orange"
    PRISMATIC = "prismatic"
    META = "meta"


class SocketState(str, Enum):
    LOCKED = "locked"
    EMPTY = "empty"
    FILLED = "filled"
    BROKEN = "broken"


class GemSetBonusType(str, Enum):
    STAT_FLAT = "stat_flat"
    STAT_PERCENT = "stat_percent"
    SKILL_BONUS = "skill_bonus"
    ELEMENTAL_RESIST = "elemental_resist"
    CRITICAL_BONUS = "critical_bonus"
    MOVEMENT_SPEED = "movement_speed"
    RESOURCE_REGEN = "resource_regen"
    SPECIAL_PROC = "special_proc"
    DAMAGE_AURA = "damage_aura"
    DEFENSE_AURA = "defense_aura"


class SocketEventKind(str, Enum):
    GEM_REGISTERED = "gem_registered"
    GEM_REMOVED_CATALOG = "gem_removed_catalog"
    SET_REGISTERED = "set_registered"
    ITEM_REGISTERED = "item_registered"
    SOCKET_ADDED = "socket_added"
    SOCKET_UNLOCKED = "socket_unlocked"
    GEM_INSERTED = "gem_inserted"
    GEM_REMOVED = "gem_removed"
    BONUS_COMPUTED = "bonus_computed"
    SET_BONUS_TRIGGERED = "set_bonus_triggered"
    RECIPE_REGISTERED = "recipe_registered"
    GEM_CRAFTED = "gem_crafted"
    CONFIG_UPDATED = "config_updated"
    SYSTEM_RESET = "system_reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class GemDefinition:
    gem_id: str
    name: str
    description: str
    gem_type: str
    rarity: str
    color: str
    level_requirement: int = 1
    stat_bonuses: Dict[str, float] = field(default_factory=dict)
    set_id: Optional[str] = None
    vendor_value: float = 0.0
    icon: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GemSetDefinition:
    set_id: str
    name: str
    description: str
    bonuses: List[Dict[str, Any]] = field(default_factory=list)
    required_count: int = 2
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocketDefinition:
    socket_id: str
    color: str
    state: str = SocketState.LOCKED.value
    unlock_cost: float = 100.0
    unlock_currency: str = "gold"
    locked_at: float = field(default_factory=_now)
    unlocked_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocketedGem:
    socket_id: str
    gem_id: str
    inserted_at: float = field(default_factory=_now)
    inserted_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerSocketItem:
    player_id: str
    item_id: str
    item_name: str
    item_slot: str
    sockets: List[SocketDefinition] = field(default_factory=list)
    socketed_gems: List[SocketedGem] = field(default_factory=list)
    acquired_at: float = field(default_factory=_now)

    @property
    def filled_sockets(self) -> int:
        return len(self.socketed_gems)

    @property
    def total_sockets(self) -> int:
        return len(self.sockets)

    @property
    def empty_sockets(self) -> int:
        unlocked = [s for s in self.sockets if s.state == SocketState.EMPTY.value]
        return len(unlocked)

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["filled_sockets"] = self.filled_sockets
        d["total_sockets"] = self.total_sockets
        d["empty_sockets"] = self.empty_sockets
        return d


@dataclass
class GemCraftRecipe:
    recipe_id: str
    name: str
    description: str
    result_gem_id: str
    result_quantity: int = 1
    ingredient_gems: Dict[str, int] = field(default_factory=dict)
    ingredient_currencies: Dict[str, float] = field(default_factory=dict)
    required_skill: int = 0
    success_chance: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GemCraftResult:
    craft_id: str
    recipe_id: str
    crafter_id: str
    result_gem_id: str
    result_quantity: int
    success: bool
    consumed_ingredients: Dict[str, Any] = field(default_factory=dict)
    crafted_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocketBonus:
    bonus_id: str
    source: str  # gem_id, set_id, or socket_color_match
    bonus_type: str
    target_stat: str
    bonus_value: float
    is_percentage: bool = False
    conditions: Dict[str, Any] = field(default_factory=dict)
    computed_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocketConfig:
    max_sockets_per_item: int = 4
    default_socket_unlock_cost: float = 100.0
    allow_color_match_bonus: bool = True
    color_match_bonus_multiplier: float = 1.5
    allow_meta_socket_bonus: bool = True
    craft_failure_refund_rate: float = 0.5
    max_recipes: int = _MAX_RECIPES
    max_gems: int = _MAX_GEMS
    max_gem_sets: int = _MAX_GEM_SETS

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocketStats:
    total_gems: int = 0
    total_gem_sets: int = 0
    total_socket_items: int = 0
    total_player_items: int = 0
    total_sockets: int = 0
    filled_sockets: int = 0
    unlocked_sockets: int = 0
    locked_sockets: int = 0
    total_recipes: int = 0
    total_crafts: int = 0
    successful_crafts: int = 0
    failed_crafts: int = 0
    active_set_bonuses: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocketSnapshot:
    gems: List[Dict[str, Any]] = field(default_factory=list)
    gem_sets: List[Dict[str, Any]] = field(default_factory=list)
    socket_items: List[Dict[str, Any]] = field(default_factory=list)
    player_items: List[Dict[str, Any]] = field(default_factory=list)
    recipes: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    taken_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocketEvent:
    event_id: str
    kind: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Main System
# ---------------------------------------------------------------------------

class GemSocketingSystem:
    """Manages gems, sockets, set bonuses, and gem crafting recipes."""

    _instance: Optional["GemSocketingSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._lock_internal = threading.RLock()
        self._gems: Dict[str, GemDefinition] = {}
        self._gem_sets: Dict[str, GemSetDefinition] = {}
        self._socket_items: Dict[str, PlayerSocketItem] = {}
        self._player_item_keys: Dict[str, List[str]] = {}
        self._recipes: Dict[str, GemCraftRecipe] = {}
        self._craft_history: List[GemCraftResult] = []
        self._bonus_history: List[SocketBonus] = []
        self._events: List[SocketEvent] = []
        self._config = SocketConfig()
        self._stats = SocketStats()
        self._tick_count: int = 0
        self._initialized: bool = False

    # -- singleton ----------------------------------------------------------
    @classmethod
    def get_instance(cls) -> "GemSocketingSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    # -- internal helpers ---------------------------------------------------
    def _emit(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> None:
        ev = SocketEvent(
            event_id=_new_id("evt"),
            kind=kind,
            payload=payload or {},
        )
        self._events.append(ev)
        _evict_fifo_list(self._events, _MAX_SOCKET_EVENTS)

    def _player_item_key(self, player_id: str, item_id: str) -> str:
        return f"{player_id}:{item_id}"

    def _item_color_match_bonus(self, item: PlayerSocketItem) -> float:
        """Return multiplier when all sockets match color with inserted gems."""
        if not self._config.allow_color_match_bonus:
            return 1.0
        matched = 0
        total = 0
        for sg in item.socketed_gems:
            sock = next((s for s in item.sockets if s.socket_id == sg.socket_id), None)
            if sock is None:
                continue
            gem = self._gems.get(sg.gem_id)
            if gem is None:
                continue
            total += 1
            if sock.color == gem.color or sock.color == SocketColor.PRISMATIC.value:
                matched += 1
        if total == 0 or matched != total:
            return 1.0
        return self._config.color_match_bonus_multiplier

    # -- gem catalog --------------------------------------------------------
    def register_gem(
        self,
        gem_id: str,
        name: str,
        description: str,
        gem_type: str = GemType.RUBY.value,
        rarity: str = GemRarity.COMMON.value,
        color: str = SocketColor.RED.value,
        level_requirement: int = 1,
        stat_bonuses: Optional[Dict[str, float]] = None,
        set_id: Optional[str] = None,
        vendor_value: float = 0.0,
        icon: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[GemDefinition]]:
        with self._lock_internal:
            if gem_id in self._gems:
                return False, "exists", None
            if len(self._gems) >= self._config.max_gems:
                return False, "capacity", None
            gem = GemDefinition(
                gem_id=gem_id,
                name=name,
                description=description,
                gem_type=gem_type,
                rarity=rarity,
                color=color,
                level_requirement=_safe_int(level_requirement, 1),
                stat_bonuses=dict(stat_bonuses or {}),
                set_id=set_id,
                vendor_value=_safe_float(vendor_value, 0.0),
                icon=icon,
                tags=list(tags or []),
                metadata=dict(metadata or {}),
            )
            self._gems[gem_id] = gem
            self._stats.total_gems = len(self._gems)
            self._emit(SocketEventKind.GEM_REGISTERED.value, {"gem_id": gem_id})
            return True, "registered", gem

    def remove_gem(self, gem_id: str) -> Tuple[bool, str]:
        with self._lock_internal:
            if gem_id not in self._gems:
                return False, "not_found"
            del self._gems[gem_id]
            self._stats.total_gems = len(self._gems)
            self._emit(SocketEventKind.GEM_REMOVED_CATALOG.value, {"gem_id": gem_id})
            return True, "removed"

    def get_gem(self, gem_id: str) -> Optional[GemDefinition]:
        with self._lock_internal:
            return self._gems.get(gem_id)

    def list_gems(
        self,
        gem_type: Optional[str] = None,
        rarity: Optional[str] = None,
        color: Optional[str] = None,
        set_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[GemDefinition]:
        with self._lock_internal:
            out: List[GemDefinition] = []
            limit = max(1, _safe_int(limit, 100))
            for gem in self._gems.values():
                if gem_type and gem.gem_type != gem_type:
                    continue
                if rarity and gem.rarity != rarity:
                    continue
                if color and gem.color != color:
                    continue
                if set_id and gem.set_id != set_id:
                    continue
                out.append(gem)
                if len(out) >= limit:
                    break
            return out

    # -- gem sets -----------------------------------------------------------
    def register_gem_set(
        self,
        set_id: str,
        name: str,
        description: str,
        bonuses: Optional[List[Dict[str, Any]]] = None,
        required_count: int = 2,
        icon: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[GemSetDefinition]]:
        with self._lock_internal:
            if set_id in self._gem_sets:
                return False, "exists", None
            if len(self._gem_sets) >= self._config.max_gem_sets:
                return False, "capacity", None
            gs = GemSetDefinition(
                set_id=set_id,
                name=name,
                description=description,
                bonuses=list(bonuses or []),
                required_count=max(1, _safe_int(required_count, 2)),
                icon=icon,
                metadata=dict(metadata or {}),
            )
            self._gem_sets[set_id] = gs
            self._stats.total_gem_sets = len(self._gem_sets)
            self._emit(SocketEventKind.SET_REGISTERED.value, {"set_id": set_id})
            return True, "registered", gs

    def get_gem_set(self, set_id: str) -> Optional[GemSetDefinition]:
        with self._lock_internal:
            return self._gem_sets.get(set_id)

    def list_gem_sets(self, limit: int = 100) -> List[GemSetDefinition]:
        with self._lock_internal:
            limit = max(1, _safe_int(limit, 100))
            return list(self._gem_sets.values())[:limit]

    # -- socket items -------------------------------------------------------
    def register_socket_item(
        self,
        player_id: str,
        item_id: str,
        item_name: str,
        item_slot: str = "weapon",
        sockets: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[bool, str, Optional[PlayerSocketItem]]:
        with self._lock_internal:
            key = self._player_item_key(player_id, item_id)
            if key in self._socket_items:
                return False, "exists", None
            if len(self._socket_items) >= _MAX_PLAYER_SOCKET_ITEMS:
                return False, "capacity", None
            psi = PlayerSocketItem(
                player_id=player_id,
                item_id=item_id,
                item_name=item_name,
                item_slot=item_slot,
            )
            existing_count = len(sockets or [])
            cap = min(existing_count, self._config.max_sockets_per_item)
            for idx, s in enumerate((sockets or [])[:cap]):
                sock = SocketDefinition(
                    socket_id=s.get("socket_id", f"sock_{idx+1}"),
                    color=s.get("color", SocketColor.PRISMATIC.value),
                    state=s.get("state", SocketState.LOCKED.value),
                    unlock_cost=_safe_float(s.get("unlock_cost"), self._config.default_socket_unlock_cost),
                    unlock_currency=s.get("unlock_currency", "gold"),
                )
                psi.sockets.append(sock)
            self._socket_items[key] = psi
            self._player_item_keys.setdefault(player_id, []).append(key)
            self._stats.total_player_items = len(self._socket_items)
            self._stats.total_socket_items = len(self._socket_items)
            self._emit(SocketEventKind.ITEM_REGISTERED.value, {"key": key})
            return True, "registered", psi

    def get_socket_item(self, player_id: str, item_id: str) -> Optional[PlayerSocketItem]:
        with self._lock_internal:
            return self._socket_items.get(self._player_item_key(player_id, item_id))

    def list_socket_items(
        self,
        player_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[PlayerSocketItem]:
        with self._lock_internal:
            limit = max(1, _safe_int(limit, 100))
            if player_id:
                keys = self._player_item_keys.get(player_id, [])
                return [self._socket_items[k] for k in keys if k in self._socket_items][:limit]
            return list(self._socket_items.values())[:limit]

    def add_socket_to_item(
        self,
        player_id: str,
        item_id: str,
        color: str = SocketColor.PRISMATIC.value,
        unlock_cost: Optional[float] = None,
        unlock_currency: str = "gold",
    ) -> Tuple[bool, str, Optional[SocketDefinition]]:
        with self._lock_internal:
            psi = self._socket_items.get(self._player_item_key(player_id, item_id))
            if psi is None:
                return False, "not_found", None
            if len(psi.sockets) >= self._config.max_sockets_per_item:
                return False, "max_sockets", None
            sock = SocketDefinition(
                socket_id=_new_id("sock"),
                color=color,
                state=SocketState.LOCKED.value,
                unlock_cost=_safe_float(unlock_cost, self._config.default_socket_unlock_cost),
                unlock_currency=unlock_currency,
            )
            psi.sockets.append(sock)
            self._emit(SocketEventKind.SOCKET_ADDED.value, {
                "player_id": player_id,
                "item_id": item_id,
                "socket_id": sock.socket_id,
            })
            return True, "added", sock

    def unlock_socket(
        self,
        player_id: str,
        item_id: str,
        socket_id: str,
    ) -> Tuple[bool, str, Optional[SocketDefinition]]:
        with self._lock_internal:
            psi = self._socket_items.get(self._player_item_key(player_id, item_id))
            if psi is None:
                return False, "item_not_found", None
            sock = next((s for s in psi.sockets if s.socket_id == socket_id), None)
            if sock is None:
                return False, "socket_not_found", None
            if sock.state != SocketState.LOCKED.value:
                return False, "not_locked", None
            sock.state = SocketState.EMPTY.value
            sock.unlocked_at = _now()
            self._emit(SocketEventKind.SOCKET_UNLOCKED.value, {
                "player_id": player_id,
                "item_id": item_id,
                "socket_id": socket_id,
            })
            return True, "unlocked", sock

    def get_socket(
        self,
        player_id: str,
        item_id: str,
        socket_id: str,
    ) -> Optional[SocketDefinition]:
        with self._lock_internal:
            psi = self._socket_items.get(self._player_item_key(player_id, item_id))
            if psi is None:
                return None
            return next((s for s in psi.sockets if s.socket_id == socket_id), None)

    # -- gem insertion ------------------------------------------------------
    def insert_gem(
        self,
        player_id: str,
        item_id: str,
        socket_id: str,
        gem_id: str,
        inserted_by: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[SocketedGem]]:
        with self._lock_internal:
            psi = self._socket_items.get(self._player_item_key(player_id, item_id))
            if psi is None:
                return False, "item_not_found", None
            gem = self._gems.get(gem_id)
            if gem is None:
                return False, "gem_not_found", None
            sock = next((s for s in psi.sockets if s.socket_id == socket_id), None)
            if sock is None:
                return False, "socket_not_found", None
            if sock.state != SocketState.EMPTY.value:
                return False, "socket_not_empty", None
            existing = next((sg for sg in psi.socketed_gems if sg.socket_id == socket_id), None)
            if existing is not None:
                return False, "already_filled", None
            sg = SocketedGem(
                socket_id=socket_id,
                gem_id=gem_id,
                inserted_by=inserted_by,
            )
            psi.socketed_gems.append(sg)
            sock.state = SocketState.FILLED.value
            self._emit(SocketEventKind.GEM_INSERTED.value, {
                "player_id": player_id,
                "item_id": item_id,
                "socket_id": socket_id,
                "gem_id": gem_id,
            })
            return True, "inserted", sg

    def remove_socketed_gem(
        self,
        player_id: str,
        item_id: str,
        socket_id: str,
        destroy_gem: bool = False,
    ) -> Tuple[bool, str, Optional[str]]:
        with self._lock_internal:
            psi = self._socket_items.get(self._player_item_key(player_id, item_id))
            if psi is None:
                return False, "item_not_found", None
            sg = next((x for x in psi.socketed_gems if x.socket_id == socket_id), None)
            if sg is None:
                return False, "gem_not_found", None
            sock = next((s for s in psi.sockets if s.socket_id == socket_id), None)
            psi.socketed_gems = [x for x in psi.socketed_gems if x.socket_id != socket_id]
            if sock is not None:
                sock.state = SocketState.EMPTY.value
            removed_gem_id = sg.gem_id
            self._emit(SocketEventKind.GEM_REMOVED.value, {
                "player_id": player_id,
                "item_id": item_id,
                "socket_id": socket_id,
                "gem_id": removed_gem_id,
                "destroyed": destroy_gem,
            })
            return True, "removed", removed_gem_id

    def get_socketed_gems(
        self,
        player_id: str,
        item_id: str,
    ) -> List[SocketedGem]:
        with self._lock_internal:
            psi = self._socket_items.get(self._player_item_key(player_id, item_id))
            if psi is None:
                return []
            return list(psi.socketed_gems)

    # -- bonus computation --------------------------------------------------
    def compute_socket_bonuses(
        self,
        player_id: str,
        item_id: str,
    ) -> List[SocketBonus]:
        with self._lock_internal:
            psi = self._socket_items.get(self._player_item_key(player_id, item_id))
            if psi is None:
                return []
            bonuses: List[SocketBonus] = []
            match_mult = self._item_color_match_bonus(psi)
            for sg in psi.socketed_gems:
                gem = self._gems.get(sg.gem_id)
                if gem is None:
                    continue
                for stat, value in gem.stat_bonuses.items():
                    actual_value = value
                    if self._config.allow_color_match_bonus and match_mult > 1.0:
                        actual_value = value * match_mult
                    bonus = SocketBonus(
                        bonus_id=_new_id("bonus"),
                        source=gem.gem_id,
                        bonus_type=GemSetBonusType.STAT_FLAT.value,
                        target_stat=stat,
                        bonus_value=actual_value,
                        is_percentage=stat.endswith("_percent") or stat.endswith("_pct"),
                        conditions={"gem_color": gem.color, "socket_id": sg.socket_id},
                    )
                    bonuses.append(bonus)
            if bonuses:
                self._bonus_history.append(bonuses[0])
                _evict_fifo_list(self._bonus_history, _MAX_BONUS_HISTORY)
                self._emit(SocketEventKind.BONUS_COMPUTED.value, {
                    "player_id": player_id,
                    "item_id": item_id,
                    "bonus_count": len(bonuses),
                })
            return bonuses

    def compute_set_bonuses(
        self,
        player_id: str,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Aggregate set bonuses for a player across all socketed items."""
        with self._lock_internal:
            keys = self._player_item_keys.get(player_id, [])
            gem_set_counts: Dict[str, List[str]] = {}
            for key in keys:
                psi = self._socket_items.get(key)
                if psi is None:
                    continue
                for sg in psi.socketed_gems:
                    gem = self._gems.get(sg.gem_id)
                    if gem is None or not gem.set_id:
                        continue
                    gem_set_counts.setdefault(gem.set_id, [])
                    if gem.gem_id not in gem_set_counts[gem.set_id]:
                        gem_set_counts[gem.set_id].append(gem.gem_id)
            active: List[Tuple[str, Dict[str, Any]]] = []
            for set_id, gem_ids in gem_set_counts.items():
                gs = self._gem_sets.get(set_id)
                if gs is None:
                    continue
                if len(gem_ids) < gs.required_count:
                    continue
                for bonus in gs.bonuses:
                    threshold = _safe_int(bonus.get("required_count", gs.required_count), gs.required_count)
                    if len(gem_ids) < threshold:
                        continue
                    active.append((set_id, bonus))
                    self._emit(SocketEventKind.SET_BONUS_TRIGGERED.value, {
                        "player_id": player_id,
                        "set_id": set_id,
                        "bonus": bonus,
                        "count": len(gem_ids),
                    })
            self._stats.active_set_bonuses = len(active)
            return active

    def get_player_bonuses(
        self,
        player_id: str,
    ) -> Dict[str, Any]:
        with self._lock_internal:
            keys = self._player_item_keys.get(player_id, [])
            item_bonuses: List[Dict[str, Any]] = []
            aggregate: Dict[str, float] = {}
            for key in keys:
                psi = self._socket_items.get(key)
                if psi is None:
                    continue
                bonuses = self.compute_socket_bonuses(player_id, psi.item_id)
                if not bonuses:
                    continue
                item_bonuses.append({
                    "item_id": psi.item_id,
                    "item_name": psi.item_name,
                    "bonuses": [b.to_dict() for b in bonuses],
                })
                for b in bonuses:
                    stat = b.target_stat
                    if b.is_percentage:
                        # aggregate additively for percentages too
                        aggregate[stat] = aggregate.get(stat, 0.0) + b.bonus_value
                    else:
                        aggregate[stat] = aggregate.get(stat, 0.0) + b.bonus_value
            set_bonuses = self.compute_set_bonuses(player_id)
            return {
                "player_id": player_id,
                "item_bonuses": item_bonuses,
                "aggregate_stats": aggregate,
                "set_bonuses": [
                    {"set_id": sid, "bonus": b} for sid, b in set_bonuses
                ],
            }

    def get_active_set_bonuses(
        self,
        player_id: str,
    ) -> List[Dict[str, Any]]:
        return [
            {"set_id": sid, "bonus": b}
            for sid, b in self.compute_set_bonuses(player_id)
        ]

    # -- recipes and crafting -----------------------------------------------
    def register_recipe(
        self,
        recipe_id: str,
        name: str,
        description: str,
        result_gem_id: str,
        ingredient_gems: Optional[Dict[str, int]] = None,
        ingredient_currencies: Optional[Dict[str, float]] = None,
        required_skill: int = 0,
        success_chance: float = 1.0,
        result_quantity: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[GemCraftRecipe]]:
        with self._lock_internal:
            if recipe_id in self._recipes:
                return False, "exists", None
            if len(self._recipes) >= self._config.max_recipes:
                return False, "capacity", None
            recipe = GemCraftRecipe(
                recipe_id=recipe_id,
                name=name,
                description=description,
                result_gem_id=result_gem_id,
                result_quantity=max(1, _safe_int(result_quantity, 1)),
                ingredient_gems=dict(ingredient_gems or {}),
                ingredient_currencies=dict(ingredient_currencies or {}),
                required_skill=_safe_int(required_skill, 0),
                success_chance=_clamp(_safe_float(success_chance, 1.0), 0.0, 1.0),
                metadata=dict(metadata or {}),
            )
            self._recipes[recipe_id] = recipe
            self._stats.total_recipes = len(self._recipes)
            self._emit(SocketEventKind.RECIPE_REGISTERED.value, {"recipe_id": recipe_id})
            return True, "registered", recipe

    def get_recipe(self, recipe_id: str) -> Optional[GemCraftRecipe]:
        with self._lock_internal:
            return self._recipes.get(recipe_id)

    def list_recipes(self, limit: int = 100) -> List[GemCraftRecipe]:
        with self._lock_internal:
            limit = max(1, _safe_int(limit, 100))
            return list(self._recipes.values())[:limit]

    def craft_gem(
        self,
        recipe_id: str,
        crafter_id: str,
        crafter_skill: int = 0,
        available_gems: Optional[Dict[str, int]] = None,
        available_currencies: Optional[Dict[str, float]] = None,
        deterministic: bool = False,
    ) -> Tuple[bool, str, Optional[GemCraftResult]]:
        import random as _random
        with self._lock_internal:
            recipe = self._recipes.get(recipe_id)
            if recipe is None:
                return False, "recipe_not_found", None
            if crafter_skill < recipe.required_skill:
                return False, "skill_too_low", None
            available_gems = available_gems or {}
            available_currencies = available_currencies or {}
            for gem_id, qty in recipe.ingredient_gems.items():
                if available_gems.get(gem_id, 0) < qty:
                    return False, "missing_ingredient", None
            for cur, amt in recipe.ingredient_currencies.items():
                if available_currencies.get(cur, 0.0) < amt:
                    return False, "missing_currency", None
            success_chance = recipe.success_chance
            success = deterministic or (_random.random() < success_chance)
            result_qty = recipe.result_quantity if success else 0
            refund_rate = self._config.craft_failure_refund_rate if not success else 1.0
            consumed: Dict[str, Any] = {
                "gems": {k: v for k, v in recipe.ingredient_gems.items()},
                "currencies": {k: v for k, v in recipe.ingredient_currencies.items()},
                "refund_rate": refund_rate,
            }
            result = GemCraftResult(
                craft_id=_new_id("craft"),
                recipe_id=recipe_id,
                crafter_id=crafter_id,
                result_gem_id=recipe.result_gem_id,
                result_quantity=result_qty,
                success=success,
                consumed_ingredients=consumed,
            )
            self._craft_history.append(result)
            _evict_fifo_list(self._craft_history, _MAX_CRAFT_HISTORY)
            self._stats.total_crafts = len(self._craft_history)
            if success:
                self._stats.successful_crafts += 1
            else:
                self._stats.failed_crafts += 1
            self._emit(SocketEventKind.GEM_CRAFTED.value, {
                "craft_id": result.craft_id,
                "recipe_id": recipe_id,
                "success": success,
                "result_gem_id": recipe.result_gem_id,
                "result_quantity": result_qty,
            })
            msg = "crafted" if success else "failed"
            return True, msg, result

    # -- lifecycle ----------------------------------------------------------
    def tick(self) -> Dict[str, Any]:
        with self._lock_internal:
            self._tick_count += 1
            self._stats.tick_count = self._tick_count
            self._emit(SocketEventKind.TICK.value, {"tick": self._tick_count})
            return {
                "tick_count": self._tick_count,
                "total_gems": len(self._gems),
                "total_player_items": len(self._socket_items),
                "total_recipes": len(self._recipes),
            }

    def set_config(self, updates: Optional[Dict[str, Any]]) -> SocketConfig:
        with self._lock_internal:
            if updates:
                for k, v in updates.items():
                    if hasattr(self._config, k):
                        setattr(self._config, k, v)
                self._emit(SocketEventKind.CONFIG_UPDATED.value, dict(updates))
            return self._config

    def get_config(self) -> SocketConfig:
        with self._lock_internal:
            return self._config

    def list_events(self, limit: int = 100) -> List[SocketEvent]:
        with self._lock_internal:
            limit = max(1, _safe_int(limit, 100))
            return list(self._events)[-limit:]

    def get_stats(self) -> SocketStats:
        with self._lock_internal:
            self._stats.total_gems = len(self._gems)
            self._stats.total_gem_sets = len(self._gem_sets)
            self._stats.total_socket_items = len(self._socket_items)
            self._stats.total_player_items = len(self._socket_items)
            self._stats.total_sockets = sum(len(psi.sockets) for psi in self._socket_items.values())
            self._stats.filled_sockets = sum(len(psi.socketed_gems) for psi in self._socket_items.values())
            self._stats.unlocked_sockets = sum(
                1 for psi in self._socket_items.values()
                for s in psi.sockets
                if s.state in (SocketState.EMPTY.value, SocketState.FILLED.value)
            )
            self._stats.locked_sockets = sum(
                1 for psi in self._socket_items.values()
                for s in psi.sockets
                if s.state == SocketState.LOCKED.value
            )
            self._stats.total_recipes = len(self._recipes)
            self._stats.total_crafts = len(self._craft_history)
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with self._lock_internal:
            return {
                "initialized": self._initialized,
                "total_gems": len(self._gems),
                "total_gem_sets": len(self._gem_sets),
                "total_socket_items": len(self._socket_items),
                "total_player_items": len(self._socket_items),
                "total_sockets": sum(len(psi.sockets) for psi in self._socket_items.values()),
                "filled_sockets": sum(len(psi.socketed_gems) for psi in self._socket_items.values()),
                "total_recipes": len(self._recipes),
                "total_crafts": len(self._craft_history),
                "active_set_bonuses": self._stats.active_set_bonuses,
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> SocketSnapshot:
        with self._lock_internal:
            return SocketSnapshot(
                gems=[g.to_dict() for g in list(self._gems.values())[:50]],
                gem_sets=[gs.to_dict() for gs in list(self._gem_sets.values())[:50]],
                socket_items=[psi.to_dict() for psi in list(self._socket_items.values())[:50]],
                player_items=[psi.to_dict() for psi in list(self._socket_items.values())[:50]],
                recipes=[r.to_dict() for r in list(self._recipes.values())[:50]],
                stats=self.get_stats().to_dict(),
                config=self._config.to_dict(),
            )

    # -- seeding ------------------------------------------------------------
    def _seed(self) -> None:
        # Gems
        self.register_gem(
            "gem_ruby_001", "Flawless Ruby", "A brilliant red ruby pulsing with fire",
            gem_type=GemType.RUBY.value, rarity=GemRarity.FLAWLESS.value,
            color=SocketColor.RED.value, level_requirement=10,
            stat_bonuses={"strength": 15.0, "fire_resist": 10.0},
            set_id="set_inferno", vendor_value=500.0, icon="ruby_flawless",
            tags=["fire", "strength"],
        )
        self.register_gem(
            "gem_ruby_002", "Perfect Ruby", "A perfect ruby burning with eternal flame",
            gem_type=GemType.RUBY.value, rarity=GemRarity.PERFECT.value,
            color=SocketColor.RED.value, level_requirement=25,
            stat_bonuses={"strength": 30.0, "fire_resist": 20.0, "fire_damage_percent": 5.0},
            set_id="set_inferno", vendor_value=1500.0, icon="ruby_perfect",
            tags=["fire", "strength"],
        )
        self.register_gem(
            "gem_sapphire_001", "Flawless Sapphire", "A deep blue sapphire crackling with frost",
            gem_type=GemType.SAPPHIRE.value, rarity=GemRarity.FLAWLESS.value,
            color=SocketColor.BLUE.value, level_requirement=10,
            stat_bonuses={"intellect": 15.0, "frost_resist": 10.0},
            set_id="set_glacier", vendor_value=500.0, icon="sapphire_flawless",
            tags=["frost", "intellect"],
        )
        self.register_gem(
            "gem_sapphire_002", "Perfect Sapphire", "A perfect sapphire radiating eternal winter",
            gem_type=GemType.SAPPHIRE.value, rarity=GemRarity.PERFECT.value,
            color=SocketColor.BLUE.value, level_requirement=25,
            stat_bonuses={"intellect": 30.0, "frost_resist": 20.0, "frost_damage_percent": 5.0},
            set_id="set_glacier", vendor_value=1500.0, icon="sapphire_perfect",
            tags=["frost", "intellect"],
        )
        self.register_gem(
            "gem_emerald_001", "Flawless Emerald", "A verdant emerald humming with life",
            gem_type=GemType.EMERALD.value, rarity=GemRarity.FLAWLESS.value,
            color=SocketColor.GREEN.value, level_requirement=10,
            stat_bonuses={"agility": 15.0, "nature_resist": 10.0},
            set_id="set_wildwood", vendor_value=500.0, icon="emerald_flawless",
            tags=["nature", "agility"],
        )
        self.register_gem(
            "gem_emerald_002", "Perfect Emerald", "A perfect emerald singing with primal energy",
            gem_type=GemType.EMERALD.value, rarity=GemRarity.PERFECT.value,
            color=SocketColor.GREEN.value, level_requirement=25,
            stat_bonuses={"agility": 30.0, "nature_resist": 20.0, "crit_chance_percent": 3.0},
            set_id="set_wildwood", vendor_value=1500.0, icon="emerald_perfect",
            tags=["nature", "agility"],
        )
        self.register_gem(
            "gem_topaz_001", "Radiant Topaz", "A golden topaz glowing with sunlight",
            gem_type=GemType.TOPAZ.value, rarity=GemRarity.RADIANT.value,
            color=SocketColor.YELLOW.value, level_requirement=15,
            stat_bonuses={"stamina": 20.0, "holy_resist": 15.0},
            set_id=None, vendor_value=400.0, icon="topaz_radiant",
            tags=["holy", "stamina"],
        )
        self.register_gem(
            "gem_amethyst_001", "Mystic Amethyst", "A purple amethyst shimmering with arcane power",
            gem_type=GemType.AMETHYST.value, rarity=GemRarity.FLAWLESS.value,
            color=SocketColor.PURPLE.value, level_requirement=15,
            stat_bonuses={"spirit": 18.0, "arcane_resist": 12.0},
            set_id=None, vendor_value=450.0, icon="amethyst_mystic",
            tags=["arcane", "spirit"],
        )
        self.register_gem(
            "gem_diamond_001", "Perfect Diamond", "A flawless diamond reflecting all colors",
            gem_type=GemType.DIAMOND.value, rarity=GemRarity.PERFECT.value,
            color=SocketColor.PRISMATIC.value, level_requirement=30,
            stat_bonuses={"all_stats": 10.0, "crit_damage_percent": 5.0},
            set_id=None, vendor_value=3000.0, icon="diamond_perfect",
            tags=["prismatic", "all_stats"],
        )
        self.register_gem(
            "gem_onyx_001", "Shadow Onyx", "A dark onyx absorbing surrounding light",
            gem_type=GemType.ONYX.value, rarity=GemRarity.RADIANT.value,
            color=SocketColor.ORANGE.value, level_requirement=20,
            stat_bonuses={"shadow_damage_percent": 4.0, "lifesteal_percent": 2.0},
            set_id=None, vendor_value=800.0, icon="onyx_shadow",
            tags=["shadow", "lifesteal"],
        )

        # Gem sets
        self.register_gem_set(
            "set_inferno", "Inferno Set", "Empowers the bearer with the fury of flame",
            bonuses=[
                {
                    "bonus_type": GemSetBonusType.STAT_PERCENT.value,
                    "target_stat": "fire_damage",
                    "value": 5.0,
                    "required_count": 2,
                },
                {
                    "bonus_type": GemSetBonusType.DAMAGE_AURA.value,
                    "target_stat": "fire_aura",
                    "value": 10.0,
                    "required_count": 3,
                },
            ],
            required_count=2,
            icon="set_inferno",
        )
        self.register_gem_set(
            "set_glacier", "Glacier Set", "Wraps the bearer in eternal frost",
            bonuses=[
                {
                    "bonus_type": GemSetBonusType.STAT_PERCENT.value,
                    "target_stat": "frost_damage",
                    "value": 5.0,
                    "required_count": 2,
                },
                {
                    "bonus_type": GemSetBonusType.DEFENSE_AURA.value,
                    "target_stat": "frost_armor",
                    "value": 15.0,
                    "required_count": 3,
                },
            ],
            required_count=2,
            icon="set_glacier",
        )
        self.register_gem_set(
            "set_wildwood", "Wildwood Set", "Channels the primal energies of the wild",
            bonuses=[
                {
                    "bonus_type": GemSetBonusType.CRITICAL_BONUS.value,
                    "target_stat": "crit_chance",
                    "value": 2.0,
                    "required_count": 2,
                },
                {
                    "bonus_type": GemSetBonusType.MOVEMENT_SPEED.value,
                    "target_stat": "movement_speed",
                    "value": 5.0,
                    "required_count": 3,
                },
            ],
            required_count=2,
            icon="set_wildwood",
        )

        # Socket items
        self.register_socket_item(
            "player_starter", "item_sword_starter", "Starter Longsword", "weapon",
            sockets=[
                {"socket_id": "sock_sword_1", "color": SocketColor.RED.value, "state": SocketState.EMPTY.value, "unlock_cost": 0},
                {"socket_id": "sock_sword_2", "color": SocketColor.PRISMATIC.value, "state": SocketState.LOCKED.value, "unlock_cost": 200},
            ],
        )
        self.register_socket_item(
            "player_starter", "item_helmet_starter", "Starter Helm", "head",
            sockets=[
                {"socket_id": "sock_helm_1", "color": SocketColor.BLUE.value, "state": SocketState.EMPTY.value, "unlock_cost": 0},
            ],
        )
        self.register_socket_item(
            "player_veteran", "item_chest_legendary", "Dragonscale Chestplate", "chest",
            sockets=[
                {"socket_id": "sock_chest_1", "color": SocketColor.RED.value, "state": SocketState.FILLED.value, "unlock_cost": 0},
                {"socket_id": "sock_chest_2", "color": SocketColor.RED.value, "state": SocketState.FILLED.value, "unlock_cost": 0},
                {"socket_id": "sock_chest_3", "color": SocketColor.PRISMATIC.value, "state": SocketState.EMPTY.value, "unlock_cost": 0},
                {"socket_id": "sock_chest_4", "color": SocketColor.META.value, "state": SocketState.LOCKED.value, "unlock_cost": 1000},
            ],
        )

        # Pre-fill veteran's chest with two inferno rubies (set bonus active)
        veteran_key = self._player_item_key("player_veteran", "item_chest_legendary")
        psi = self._socket_items.get(veteran_key)
        if psi is not None:
            psi.socketed_gems.append(SocketedGem(socket_id="sock_chest_1", gem_id="gem_ruby_001"))
            psi.socketed_gems.append(SocketedGem(socket_id="sock_chest_2", gem_id="gem_ruby_002"))

        # Recipes
        self.register_recipe(
            "recipe_combine_rubies", "Combine Rubies", "Combine three flawed rubies into one perfect ruby",
            result_gem_id="gem_ruby_002",
            ingredient_gems={"gem_ruby_001": 3},
            ingredient_currencies={"gold": 500.0},
            required_skill=50,
            success_chance=0.8,
            result_quantity=1,
        )
        self.register_recipe(
            "recipe_combine_sapphires", "Combine Sapphires", "Combine three flawed sapphires into one perfect sapphire",
            result_gem_id="gem_sapphire_002",
            ingredient_gems={"gem_sapphire_001": 3},
            ingredient_currencies={"gold": 500.0},
            required_skill=50,
            success_chance=0.8,
            result_quantity=1,
        )
        self.register_recipe(
            "recipe_combine_emeralds", "Combine Emeralds", "Combine three flawed emeralds into one perfect emerald",
            result_gem_id="gem_emerald_002",
            ingredient_gems={"gem_emerald_001": 3},
            ingredient_currencies={"gold": 500.0},
            required_skill=50,
            success_chance=0.8,
            result_quantity=1,
        )
        self.register_recipe(
            "recipe_diamond_polish", "Polish Diamond", "Polish a diamond to perfect quality",
            result_gem_id="gem_diamond_001",
            ingredient_gems={},
            ingredient_currencies={"gold": 5000.0, "dust": 10.0},
            required_skill=100,
            success_chance=0.6,
            result_quantity=1,
        )

        self._initialized = True

    def reset(self) -> None:
        with self._lock_internal:
            self._gems.clear()
            self._gem_sets.clear()
            self._socket_items.clear()
            self._player_item_keys.clear()
            self._recipes.clear()
            self._craft_history.clear()
            self._bonus_history.clear()
            self._events.clear()
            self._config = SocketConfig()
            self._stats = SocketStats()
            self._tick_count = 0
            self._initialized = False
            self._emit(SocketEventKind.SYSTEM_RESET.value, {})
            self._seed()


# ---------------------------------------------------------------------------
# Module-level singleton initialization
# ---------------------------------------------------------------------------

def get_gem_socketing_system() -> GemSocketingSystem:
    """Return the shared singleton instance, seeding on first use."""
    inst = GemSocketingSystem.get_instance()
    if not inst._initialized:
        with _LOCK:
            if not inst._initialized:
                inst._seed()
    return inst


# Initialize the singleton on import
with _LOCK:
    _sys = GemSocketingSystem.get_instance()
    if not _sys._initialized:
        _sys._seed()
