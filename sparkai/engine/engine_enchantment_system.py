"""
SparkLabs Engine - Enchantment System

A gem socketing and item enchantment system for the SparkLabs AI-native game
engine. Manages enchantable items with socket slots, gem definitions, socket
insertion/removal, enchantment application/removal, and enchantment tier
progression. Supports gem rarity tiers, enchantment effect modifiers, socket
unlocking, and enchantment durability.

Each enchantable item has a fixed number of socket slots (some locked, some
unlocked). Gems are inserted into unlocked sockets to apply stat modifiers.
Enchantments are persistent effects applied directly to items, independent
of gems. The system tracks enchantment durability (degrades with use) and
tier-based potency scaling.

Architecture:
  EnchantmentSystem (singleton)
    |-- GemRarity, EnchantmentTier, SocketState, EnchantEventKind
    |-- GemDefinition, EnchantmentDefinition, SocketSlot, EnchantableItem,
       EnchantmentInstance, EnchantConfig, EnchantStats, EnchantSnapshot,
       EnchantEvent
    |-- get_enchantment_system

Core Capabilities:
  - register_gem / remove_gem / get_gem / list_gems: manage the gem catalog.
  - register_enchantment / remove_enchantment / get_enchantment /
    list_enchantments: manage the enchantment definition catalog.
  - register_item / remove_item / get_item / list_items: manage enchantable
    items with socket slots.
  - insert_gem / remove_gem_from_socket: socket and unsocket gems.
  - apply_enchantment / remove_enchantment_from_item: apply and remove
    persistent enchantments.
  - unlock_socket: unlock a locked socket slot on an item.
  - repair_enchantment: restore enchantment durability.
  - tick: advance durability decay and time-based features.
  - set_config / get_config: global tuning.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`EnchantmentSystem.get_instance` or the module-level
:func:`get_enchantment_system` factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_GEMS: int = 500
_MAX_ENCHANTMENTS: int = 500
_MAX_ITEMS: int = 2000
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

class GemRarity(str, Enum):
    """Rarity tier of a gem."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class EnchantmentTier(str, Enum):
    """Tier of an enchantment definition."""
    MINOR = "minor"
    MAJOR = "major"
    SUPERIOR = "superior"
    SUPREME = "supreme"
    CELESTIAL = "celestial"


class SocketState(str, Enum):
    """State of a socket slot on an item."""
    EMPTY = "empty"
    LOCKED = "locked"
    FILLED = "filled"


class EnchantEventKind(str, Enum):
    """Audit event types emitted by the enchantment system."""
    GEM_REGISTERED = "gem_registered"
    GEM_REMOVED = "gem_removed"
    ENCHANTMENT_REGISTERED = "enchantment_registered"
    ENCHANTMENT_REMOVED = "enchantment_removed"
    ITEM_REGISTERED = "item_registered"
    ITEM_REMOVED = "item_removed"
    GEM_INSERTED = "gem_inserted"
    GEM_REMOVED_FROM_SOCKET = "gem_removed_from_socket"
    ENCHANTMENT_APPLIED = "enchantment_applied"
    ENCHANTMENT_REMOVED_FROM_ITEM = "enchantment_removed_from_item"
    SOCKET_UNLOCKED = "socket_unlocked"
    ENCHANTMENT_REPAIRED = "enchantment_repaired"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class GemDefinition:
    """A gem catalog entry."""
    gem_id: str
    name: str = ""
    rarity: str = GemRarity.COMMON.value
    description: str = ""
    stat_key: str = ""
    stat_value: float = 0.0
    stat_percent: float = 0.0
    element_type: str = ""
    tier: int = 1
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EnchantmentDefinition:
    """An enchantment definition in the catalog."""
    enchantment_id: str
    name: str = ""
    tier: str = EnchantmentTier.MINOR.value
    description: str = ""
    stat_key: str = ""
    stat_value: float = 0.0
    stat_percent: float = 0.0
    max_durability: int = 1000
    element_type: str = ""
    required_item_level: int = 1
    compatible_categories: List[str] = field(default_factory=list)
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SocketSlot:
    """A socket slot on an enchantable item."""
    slot_index: int
    state: str = SocketState.LOCKED.value
    gem_id: str = ""
    unlocked_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EnchantmentInstance:
    """An enchantment applied to a specific item."""
    instance_id: str
    enchantment_id: str
    item_id: str
    current_durability: int = 1000
    max_durability: int = 1000
    applied_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EnchantableItem:
    """An item that can hold gems and enchantments."""
    item_id: str
    name: str = ""
    item_category: str = "weapon"
    item_level: int = 1
    sockets: List[SocketSlot] = field(default_factory=list)
    enchantments: List[EnchantmentInstance] = field(default_factory=list)
    owner_id: str = ""
    base_stats: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EnchantConfig:
    """Global tuning parameters for the enchantment system."""
    max_gems: int = 500
    max_enchantments: int = 500
    max_items: int = 2000
    max_sockets_per_item: int = 6
    socket_unlock_cost: int = 1000
    durability_decay_per_tick: float = 0.01
    min_durability: int = 0
    allow_enchantment_overlap: bool = False
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EnchantStats:
    """Aggregate statistics for the enchantment system."""
    total_gems: int = 0
    total_enchantments: int = 0
    total_items: int = 0
    total_sockets: int = 0
    total_filled_sockets: int = 0
    total_active_enchantments: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EnchantSnapshot:
    """Full state snapshot of the enchantment system."""
    gems: List[Dict[str, Any]] = field(default_factory=list)
    enchantments: List[Dict[str, Any]] = field(default_factory=list)
    items: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EnchantEvent:
    """An audit event emitted by the enchantment system."""
    event_id: str
    kind: str
    timestamp: float
    gem_id: Optional[str] = None
    enchantment_id: Optional[str] = None
    item_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Enchantment System
# ---------------------------------------------------------------------------

class EnchantmentSystem:
    """Manages gem socketing and item enchantment."""

    _instance: Optional["EnchantmentSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._gems: Dict[str, GemDefinition] = {}
        self._enchantments: Dict[str, EnchantmentDefinition] = {}
        self._items: Dict[str, EnchantableItem] = {}
        self._events: List[EnchantEvent] = []
        self._stats = EnchantStats()
        self._config = EnchantConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._instance_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "EnchantmentSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample gems, enchantments, and items."""
        with self._init_lock:
            if self._initialized:
                return

            gems = [
                GemDefinition(
                    gem_id="gem_ruby_fire",
                    name="Fire Ruby",
                    rarity=GemRarity.RARE.value,
                    description="A glowing ruby imbued with fire.",
                    stat_key="fire_damage",
                    stat_value=25.0,
                    stat_percent=0.0,
                    element_type="fire",
                    tier=3,
                ),
                GemDefinition(
                    gem_id="gem_sapphire_frost",
                    name="Frost Sapphire",
                    rarity=GemRarity.RARE.value,
                    description="A cold sapphire radiating frost.",
                    stat_key="ice_damage",
                    stat_value=25.0,
                    element_type="ice",
                    tier=3,
                ),
                GemDefinition(
                    gem_id="gem_emerald_vitality",
                    name="Emerald of Vitality",
                    rarity=GemRarity.EPIC.value,
                    description="An emerald pulsing with life energy.",
                    stat_key="max_health",
                    stat_value=0.0,
                    stat_percent=0.10,
                    element_type="nature",
                    tier=4,
                ),
                GemDefinition(
                    gem_id="gem_diamond_precision",
                    name="Diamond of Precision",
                    rarity=GemRarity.LEGENDARY.value,
                    description="A flawless diamond enhancing accuracy.",
                    stat_key="crit_chance",
                    stat_value=0.0,
                    stat_percent=0.15,
                    tier=5,
                ),
            ]
            for g in gems:
                self._gems[g.gem_id] = g

            ench_defs = [
                EnchantmentDefinition(
                    enchantment_id="ench_flameburst",
                    name="Flameburst",
                    tier=EnchantmentTier.MAJOR.value,
                    description="Weapon bursts into flames on hit.",
                    stat_key="fire_damage",
                    stat_value=15.0,
                    max_durability=2000,
                    element_type="fire",
                    required_item_level=5,
                    compatible_categories=["weapon"],
                ),
                EnchantmentDefinition(
                    enchantment_id="ench_frostguard",
                    name="Frostguard",
                    tier=EnchantmentTier.SUPERIOR.value,
                    description="Armor radiates protective frost.",
                    stat_key="ice_resist",
                    stat_value=30.0,
                    max_durability=3000,
                    element_type="ice",
                    required_item_level=10,
                    compatible_categories=["armor", "shield"],
                ),
                EnchantmentDefinition(
                    enchantment_id="ench_swiftness",
                    name="Swiftness",
                    tier=EnchantmentTier.MINOR.value,
                    description="Increases movement speed.",
                    stat_key="move_speed",
                    stat_value=0.0,
                    stat_percent=0.08,
                    max_durability=1500,
                    required_item_level=1,
                    compatible_categories=["boots", "weapon", "armor"],
                ),
            ]
            for e in ench_defs:
                self._enchantments[e.enchantment_id] = e

            item = EnchantableItem(
                item_id="item_sword_flame",
                name="Flame Sword",
                item_category="weapon",
                item_level=15,
                owner_id="player_starter",
                base_stats={"attack": 120.0, "crit_chance": 0.05},
                sockets=[
                    SocketSlot(slot_index=0, state=SocketState.FILLED.value, gem_id="gem_ruby_fire", unlocked_at=_now()),
                    SocketSlot(slot_index=1, state=SocketState.EMPTY.value, unlocked_at=_now()),
                    SocketSlot(slot_index=2, state=SocketState.LOCKED.value),
                ],
            )
            self._instance_counter += 1
            item.enchantments.append(EnchantmentInstance(
                instance_id=f"ei_{self._instance_counter}",
                enchantment_id="ench_flameburst",
                item_id="item_sword_flame",
                current_durability=1800,
                max_durability=2000,
            ))
            self._items[item.item_id] = item

            self._stats.total_gems = len(gems)
            self._stats.total_enchantments = len(ench_defs)
            self._stats.total_items = 1
            self._stats.total_sockets = sum(len(i.sockets) for i in self._items.values())
            self._stats.total_filled_sockets = sum(
                1 for i in self._items.values() for s in i.sockets if s.state == SocketState.FILLED.value
            )
            self._stats.total_active_enchantments = sum(len(i.enchantments) for i in self._items.values())
            self._initialized = True

    # ------------------------------------------------------------------
    # Gem Catalog
    # ------------------------------------------------------------------

    def register_gem(self, gem: GemDefinition) -> Dict[str, Any]:
        if not gem.gem_id:
            return {"success": False, "reason": "missing_gem_id"}
        with self._lock:
            if gem.gem_id in self._gems:
                return {"success": False, "reason": "gem_id_exists"}
            if len(self._gems) >= self._config.max_gems:
                return {"success": False, "reason": "max_gems_reached"}
            self._gems[gem.gem_id] = gem
            self._stats.total_gems = len(self._gems)
            self._emit_event(EnchantEventKind.GEM_REGISTERED.value, gem_id=gem.gem_id,
                             details={"name": gem.name, "rarity": gem.rarity})
            return {"gem_id": gem.gem_id, "registered": True}

    def remove_gem(self, gem_id: str) -> Dict[str, Any]:
        with self._lock:
            if gem_id not in self._gems:
                return {"removed": False, "reason": "gem_not_found"}
            del self._gems[gem_id]
            self._stats.total_gems = len(self._gems)
            self._emit_event(EnchantEventKind.GEM_REMOVED.value, gem_id=gem_id)
            return {"gem_id": gem_id, "removed": True}

    def get_gem(self, gem_id: str) -> Optional[GemDefinition]:
        return self._gems.get(gem_id)

    def list_gems(self, rarity: Optional[str] = None, element_type: Optional[str] = None,
                  limit: int = 100) -> List[GemDefinition]:
        gems = list(self._gems.values())
        if rarity:
            gems = [g for g in gems if g.rarity == rarity]
        if element_type:
            gems = [g for g in gems if g.element_type == element_type]
        return gems[:limit]

    # ------------------------------------------------------------------
    # Enchantment Catalog
    # ------------------------------------------------------------------

    def register_enchantment(self, ench: EnchantmentDefinition) -> Dict[str, Any]:
        if not ench.enchantment_id:
            return {"success": False, "reason": "missing_enchantment_id"}
        with self._lock:
            if ench.enchantment_id in self._enchantments:
                return {"success": False, "reason": "enchantment_id_exists"}
            if len(self._enchantments) >= self._config.max_enchantments:
                return {"success": False, "reason": "max_enchantments_reached"}
            self._enchantments[ench.enchantment_id] = ench
            self._stats.total_enchantments = len(self._enchantments)
            self._emit_event(EnchantEventKind.ENCHANTMENT_REGISTERED.value,
                             enchantment_id=ench.enchantment_id,
                             details={"name": ench.name, "tier": ench.tier})
            return {"enchantment_id": ench.enchantment_id, "registered": True}

    def remove_enchantment(self, enchantment_id: str) -> Dict[str, Any]:
        with self._lock:
            if enchantment_id not in self._enchantments:
                return {"removed": False, "reason": "enchantment_not_found"}
            del self._enchantments[enchantment_id]
            self._stats.total_enchantments = len(self._enchantments)
            self._emit_event(EnchantEventKind.ENCHANTMENT_REMOVED.value, enchantment_id=enchantment_id)
            return {"enchantment_id": enchantment_id, "removed": True}

    def get_enchantment(self, enchantment_id: str) -> Optional[EnchantmentDefinition]:
        return self._enchantments.get(enchantment_id)

    def list_enchantments(self, tier: Optional[str] = None, element_type: Optional[str] = None,
                          limit: int = 100) -> List[EnchantmentDefinition]:
        enchs = list(self._enchantments.values())
        if tier:
            enchs = [e for e in enchs if e.tier == tier]
        if element_type:
            enchs = [e for e in enchs if e.element_type == element_type]
        return enchs[:limit]

    # ------------------------------------------------------------------
    # Item Management
    # ------------------------------------------------------------------

    def register_item(self, item: EnchantableItem) -> Dict[str, Any]:
        if not item.item_id:
            return {"success": False, "reason": "missing_item_id"}
        with self._lock:
            if item.item_id in self._items:
                return {"success": False, "reason": "item_id_exists"}
            if len(self._items) >= self._config.max_items:
                return {"success": False, "reason": "max_items_reached"}
            self._items[item.item_id] = item
            self._stats.total_items = len(self._items)
            self._stats.total_sockets = sum(len(i.sockets) for i in self._items.values())
            self._stats.total_filled_sockets = sum(
                1 for i in self._items.values() for s in i.sockets if s.state == SocketState.FILLED.value
            )
            self._emit_event(EnchantEventKind.ITEM_REGISTERED.value, item_id=item.item_id,
                             details={"name": item.name, "category": item.item_category})
            return {"item_id": item.item_id, "registered": True}

    def remove_item(self, item_id: str) -> Dict[str, Any]:
        with self._lock:
            if item_id not in self._items:
                return {"removed": False, "reason": "item_not_found"}
            del self._items[item_id]
            self._stats.total_items = len(self._items)
            self._stats.total_sockets = sum(len(i.sockets) for i in self._items.values())
            self._stats.total_filled_sockets = sum(
                1 for i in self._items.values() for s in i.sockets if s.state == SocketState.FILLED.value
            )
            self._stats.total_active_enchantments = sum(len(i.enchantments) for i in self._items.values())
            self._emit_event(EnchantEventKind.ITEM_REMOVED.value, item_id=item_id)
            return {"item_id": item_id, "removed": True}

    def get_item(self, item_id: str) -> Optional[EnchantableItem]:
        return self._items.get(item_id)

    def list_items(self, owner_id: Optional[str] = None, item_category: Optional[str] = None,
                   limit: int = 100) -> List[EnchantableItem]:
        items = list(self._items.values())
        if owner_id:
            items = [i for i in items if i.owner_id == owner_id]
        if item_category:
            items = [i for i in items if i.item_category == item_category]
        return items[:limit]

    # ------------------------------------------------------------------
    # Socket Operations
    # ------------------------------------------------------------------

    def insert_gem(self, item_id: str, slot_index: int, gem_id: str) -> Dict[str, Any]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return {"success": False, "reason": "item_not_found"}
            gem = self._gems.get(gem_id)
            if gem is None:
                return {"success": False, "reason": "gem_not_found"}
            slot = None
            for s in item.sockets:
                if s.slot_index == slot_index:
                    slot = s
                    break
            if slot is None:
                return {"success": False, "reason": "slot_not_found"}
            if slot.state == SocketState.LOCKED.value:
                return {"success": False, "reason": "slot_locked"}
            if slot.state == SocketState.FILLED.value:
                return {"success": False, "reason": "slot_occupied"}
            slot.state = SocketState.FILLED.value
            slot.gem_id = gem_id
            self._stats.total_filled_sockets = sum(
                1 for i in self._items.values() for s in i.sockets if s.state == SocketState.FILLED.value
            )
            self._emit_event(EnchantEventKind.GEM_INSERTED.value, gem_id=gem_id, item_id=item_id,
                             details={"slot_index": slot_index})
            return {"item_id": item_id, "slot_index": slot_index, "gem_id": gem_id, "success": True}

    def remove_gem_from_socket(self, item_id: str, slot_index: int) -> Dict[str, Any]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return {"success": False, "reason": "item_not_found"}
            slot = None
            for s in item.sockets:
                if s.slot_index == slot_index:
                    slot = s
                    break
            if slot is None:
                return {"success": False, "reason": "slot_not_found"}
            if slot.state != SocketState.FILLED.value:
                return {"success": False, "reason": "slot_empty"}
            old_gem_id = slot.gem_id
            slot.state = SocketState.EMPTY.value
            slot.gem_id = ""
            self._stats.total_filled_sockets = sum(
                1 for i in self._items.values() for s in i.sockets if s.state == SocketState.FILLED.value
            )
            self._emit_event(EnchantEventKind.GEM_REMOVED_FROM_SOCKET.value, gem_id=old_gem_id,
                             item_id=item_id, details={"slot_index": slot_index})
            return {"item_id": item_id, "slot_index": slot_index, "gem_id": old_gem_id, "success": True}

    def unlock_socket(self, item_id: str, slot_index: int) -> Dict[str, Any]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return {"success": False, "reason": "item_not_found"}
            slot = None
            for s in item.sockets:
                if s.slot_index == slot_index:
                    slot = s
                    break
            if slot is None:
                return {"success": False, "reason": "slot_not_found"}
            if slot.state != SocketState.LOCKED.value:
                return {"success": False, "reason": "slot_not_locked"}
            slot.state = SocketState.EMPTY.value
            slot.unlocked_at = _now()
            self._emit_event(EnchantEventKind.SOCKET_UNLOCKED.value, item_id=item_id,
                             details={"slot_index": slot_index})
            return {"item_id": item_id, "slot_index": slot_index, "unlocked": True}

    # ------------------------------------------------------------------
    # Enchantment Operations
    # ------------------------------------------------------------------

    def apply_enchantment(self, item_id: str, enchantment_id: str) -> Dict[str, Any]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return {"success": False, "reason": "item_not_found"}
            ench = self._enchantments.get(enchantment_id)
            if ench is None:
                return {"success": False, "reason": "enchantment_not_found"}
            if item.item_level < ench.required_item_level:
                return {"success": False, "reason": "item_level_too_low"}
            if ench.compatible_categories and item.item_category not in ench.compatible_categories:
                return {"success": False, "reason": "category_incompatible"}
            if not self._config.allow_enchantment_overlap:
                for e in item.enchantments:
                    if e.enchantment_id == enchantment_id:
                        return {"success": False, "reason": "enchantment_already_applied"}
            self._instance_counter += 1
            instance = EnchantmentInstance(
                instance_id=f"ei_{self._instance_counter}",
                enchantment_id=enchantment_id,
                item_id=item_id,
                current_durability=ench.max_durability,
                max_durability=ench.max_durability,
            )
            item.enchantments.append(instance)
            self._stats.total_active_enchantments = sum(len(i.enchantments) for i in self._items.values())
            self._emit_event(EnchantEventKind.ENCHANTMENT_APPLIED.value, enchantment_id=enchantment_id,
                             item_id=item_id, details={"instance_id": instance.instance_id})
            return {"instance_id": instance.instance_id, "item_id": item_id, "success": True}

    def remove_enchantment_from_item(self, item_id: str, instance_id: str) -> Dict[str, Any]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return {"success": False, "reason": "item_not_found"}
            for i, e in enumerate(item.enchantments):
                if e.instance_id == instance_id:
                    item.enchantments.pop(i)
                    self._stats.total_active_enchantments = sum(len(it.enchantments) for it in self._items.values())
                    self._emit_event(EnchantEventKind.ENCHANTMENT_REMOVED_FROM_ITEM.value,
                                     enchantment_id=e.enchantment_id, item_id=item_id,
                                     details={"instance_id": instance_id})
                    return {"instance_id": instance_id, "success": True}
            return {"success": False, "reason": "instance_not_found"}

    def repair_enchantment(self, item_id: str, instance_id: str, amount: int = 0) -> Dict[str, Any]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return {"success": False, "reason": "item_not_found"}
            for e in item.enchantments:
                if e.instance_id == instance_id:
                    repair_amount = amount if amount > 0 else e.max_durability
                    e.current_durability = min(e.max_durability, e.current_durability + repair_amount)
                    self._emit_event(EnchantEventKind.ENCHANTMENT_REPAIRED.value,
                                     enchantment_id=e.enchantment_id, item_id=item_id,
                                     details={"instance_id": instance_id, "repaired_to": e.current_durability})
                    return {"instance_id": instance_id, "current_durability": e.current_durability, "success": True}
            return {"success": False, "reason": "instance_not_found"}

    # ------------------------------------------------------------------
    # Tick, Config, Events, Stats
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        decay = int(self._config.durability_decay_per_tick * delta_time)
        if decay > 0:
            with self._lock:
                for item in self._items.values():
                    for e in item.enchantments:
                        e.current_durability = max(self._config.min_durability, e.current_durability - decay)
        self._emit_event(EnchantEventKind.TICK.value, details={"delta_time": delta_time})
        return {"tick": self._tick_count}

    def get_config(self) -> EnchantConfig:
        return self._config

    def set_config(self, config: EnchantConfig) -> Dict[str, Any]:
        with self._lock:
            self._config = config
            self._emit_event(EnchantEventKind.CONFIG_UPDATED.value)
            return {"updated": True}

    def _emit_event(self, kind: str, gem_id: Optional[str] = None,
                    enchantment_id: Optional[str] = None,
                    item_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None) -> None:
        self._event_counter += 1
        event = EnchantEvent(
            event_id=f"ee_{self._event_counter}",
            kind=kind,
            timestamp=_now(),
            gem_id=gem_id,
            enchantment_id=enchantment_id,
            item_id=item_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, item_id: Optional[str] = None, gem_id: Optional[str] = None,
                    enchantment_id: Optional[str] = None, limit: int = 100) -> List[EnchantEvent]:
        events = self._events
        if item_id:
            events = [e for e in events if e.item_id == item_id]
        if gem_id:
            events = [e for e in events if e.gem_id == gem_id]
        if enchantment_id:
            events = [e for e in events if e.enchantment_id == enchantment_id]
        return list(reversed(events[-limit:]))

    def get_stats(self) -> EnchantStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_gems": len(self._gems),
            "total_enchantments": len(self._enchantments),
            "total_items": len(self._items),
            "total_sockets": self._stats.total_sockets,
            "total_filled_sockets": self._stats.total_filled_sockets,
            "total_active_enchantments": self._stats.total_active_enchantments,
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> EnchantSnapshot:
        return EnchantSnapshot(
            gems=[g.to_dict() for g in self._gems.values()],
            enchantments=[e.to_dict() for e in self._enchantments.values()],
            items=[i.to_dict() for i in self._items.values()],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._gems.clear()
            self._enchantments.clear()
            self._items.clear()
            self._events.clear()
            self._stats = EnchantStats()
            self._tick_count = 0
            self._event_counter = 0
            self._instance_counter = 0
            self._initialized = False
            self._seed()
            self._emit_event(EnchantEventKind.RESET.value)
            return {"reset": True, "status": self.get_status()}


def get_enchantment_system() -> EnchantmentSystem:
    return EnchantmentSystem.get_instance()
