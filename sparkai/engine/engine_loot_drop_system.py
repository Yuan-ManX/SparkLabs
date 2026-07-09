"""
SparkLabs Engine - Loot & Drop System

Manages loot tables, drop chances, item rarity weighting, bonus loot
rolls, loot sharing rules, and individual/player loot history. Supports
conditional drops, luck modifiers, loot specialization, and party
distribution modes for cooperative gameplay.

Architecture:
  LootDropSystem (singleton)
    |-- ItemRarity, DropCondition, LootShareMode, LootEventKind
    |-- LootItem, LootEntry, LootTable, LootRoll, PlayerLuck,
       PartyLootDistribution, LootConfig, LootStats, LootSnapshot, LootEvent
    |-- get_loot_drop_system

Core Capabilities:
  - register_table / remove_table / get_table / list_tables
  - add_entry / remove_entry / get_entry / list_entries
  - roll_loot / roll_table / multi_roll
  - register_player_luck / get_player_luck / update_player_luck
  - create_distribution / resolve_distribution / get_distribution
  - get_player_history / get_drop_history
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`LootDropSystem.get_instance` or the module-level
:func:`get_loot_drop_system` factory.
"""

from __future__ import annotations

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

_MAX_TABLES: int = 500
_MAX_ENTRIES_PER_TABLE: int = 200
_MAX_ROLLS: int = 100000
_MAX_PLAYER_LUCK: int = 50000
_MAX_DISTRIBUTIONS: int = 5000
_MAX_HISTORY: int = 50000
_MAX_EVENTS: int = 10000


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

class ItemRarity(str, Enum):
    """Rarity tiers for loot items."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"
    CURRENCY = "currency"


class DropCondition(str, Enum):
    """Conditions that must be met for a drop to be eligible."""
    ALWAYS = "always"
    NIGHT_ONLY = "night_only"
    DAY_ONLY = "day_only"
    BOSS_KILL = "boss_kill"
    FIRST_KILL = "first_kill"
    LUCK_THRESHOLD = "luck_threshold"
    PARTY_SIZE = "party_size"
    SEASONAL = "seasonal"


class LootShareMode(str, Enum):
    """How loot is distributed among party members."""
    FREE_FOR_ALL = "free_for_all"
    ROUND_ROBIN = "round_robin"
    MASTER_LOOTER = "master_looter"
    NEED_BEFORE_GREED = "need_before_greed"
    PERSONAL = "personal"


class LootEventKind(str, Enum):
    """Audit event types emitted by the loot drop system."""
    TABLE_REGISTERED = "table_registered"
    TABLE_REMOVED = "table_removed"
    ENTRY_ADDED = "entry_added"
    ENTRY_REMOVED = "entry_removed"
    LOOT_ROLLED = "loot_rolled"
    BONUS_LOOT = "bonus_loot"
    LUCK_UPDATED = "luck_updated"
    DISTRIBUTION_CREATED = "distribution_created"
    DISTRIBUTION_RESOLVED = "distribution_resolved"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Rarity Weights
# ---------------------------------------------------------------------------

RARITY_WEIGHTS: Dict[str, float] = {
    ItemRarity.COMMON.value: 1000.0,
    ItemRarity.UNCOMMON.value: 400.0,
    ItemRarity.RARE.value: 100.0,
    ItemRarity.EPIC.value: 25.0,
    ItemRarity.LEGENDARY.value: 5.0,
    ItemRarity.MYTHIC.value: 0.5,
    ItemRarity.CURRENCY.value: 500.0,
}

RARITY_LUCK_SCALING: Dict[str, float] = {
    ItemRarity.COMMON.value: 0.0,
    ItemRarity.UNCOMMON.value: 0.1,
    ItemRarity.RARE.value: 0.3,
    ItemRarity.EPIC.value: 0.5,
    ItemRarity.LEGENDARY.value: 0.8,
    ItemRarity.MYTHIC.value: 1.0,
    ItemRarity.CURRENCY.value: 0.0,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class LootItem:
    """An item that can be dropped from a loot table."""
    item_id: str
    name: str
    rarity: str = ItemRarity.COMMON.value
    quantity_min: int = 1
    quantity_max: int = 1
    icon: str = ""
    description: str = ""
    stackable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LootEntry:
    """A single entry in a loot table."""
    entry_id: str
    table_id: str
    item: LootItem
    drop_chance: float = 1.0
    weight: float = 100.0
    min_amount: int = 1
    max_amount: int = 1
    condition: str = DropCondition.ALWAYS.value
    condition_value: str = ""
    is_guaranteed: bool = False
    is_bonus: bool = False
    luck_modified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LootTable:
    """A loot table containing multiple drop entries."""
    table_id: str
    name: str
    description: str = ""
    source_type: str = "monster"
    source_id: str = ""
    min_drops: int = 1
    max_drops: int = 3
    bonus_drop_chance: float = 0.1
    entries: List[LootEntry] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LootRoll:
    """A result of a loot roll."""
    roll_id: str
    table_id: str
    player_id: str
    source_type: str = "monster"
    source_id: str = ""
    items_dropped: List[Dict[str, Any]] = field(default_factory=list)
    bonus_items: List[Dict[str, Any]] = field(default_factory=list)
    luck_value: float = 0.0
    rolled_at: float = field(default_factory=_now)
    party_size: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerLuck:
    """A player's luck stat and modifiers."""
    player_id: str
    base_luck: float = 0.0
    bonus_luck: float = 0.0
    total_rolls: int = 0
    rare_drops: int = 0
    epic_drops: int = 0
    legendary_drops: int = 0
    mythic_drops: int = 0
    last_roll: float = 0.0

    @property
    def total_luck(self) -> float:
        return self.base_luck + self.bonus_luck

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["total_luck"] = self.total_luck
        return d


@dataclass
class PartyLootDistribution:
    """A loot distribution for a party."""
    distribution_id: str
    table_id: str
    source_id: str = ""
    share_mode: str = LootShareMode.PERSONAL.value
    party_members: List[str] = field(default_factory=list)
    rolls: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"
    created_at: float = field(default_factory=_now)
    resolved_at: float = 0.0
    master_looter: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LootConfig:
    """Global tuning parameters."""
    max_tables: int = 500
    max_entries_per_table: int = 200
    max_rolls: int = 100000
    max_player_luck: int = 50000
    max_distributions: int = 5000
    max_history: int = 50000
    global_luck_multiplier: float = 1.0
    bonus_drop_base_chance: float = 0.1
    rare_drop_threshold: float = 0.05
    personal_loot_mode: bool = True
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LootStats:
    """Aggregate statistics."""
    total_tables: int = 0
    total_entries: int = 0
    total_rolls: int = 0
    total_items_dropped: int = 0
    total_bonus_drops: int = 0
    common_drops: int = 0
    uncommon_drops: int = 0
    rare_drops: int = 0
    epic_drops: int = 0
    legendary_drops: int = 0
    mythic_drops: int = 0
    currency_drops: int = 0
    total_distributions: int = 0
    pending_distributions: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LootSnapshot:
    """Full state snapshot."""
    tables: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LootEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    table_id: str = ""
    player_id: str = ""
    entry_id: str = ""
    roll_id: str = ""
    distribution_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Loot Drop System
# ---------------------------------------------------------------------------

class LootDropSystem:
    """Manages loot tables, drop rolls, and party loot distribution."""

    _instance: Optional["LootDropSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._tables: Dict[str, LootTable] = {}
        self._entries: Dict[str, LootEntry] = {}
        self._rolls: List[LootRoll] = []
        self._player_luck: Dict[str, PlayerLuck] = {}
        self._distributions: Dict[str, PartyLootDistribution] = {}
        self._history: List[LootRoll] = []
        self._events: List[LootEvent] = []
        self._stats = LootStats()
        self._config = LootConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._roll_counter: int = 0
        self._entry_counter: int = 0
        self._distribution_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "LootDropSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed initial loot tables, entries, and player luck."""
        with self._init_lock:
            if self._initialized:
                return

            # Table 1: Goblin Raider drops
            t1 = LootTable(
                table_id="table_goblin_raider",
                name="Goblin Raider Loot",
                description="Drops from goblin raider enemies.",
                source_type="monster",
                source_id="mob_goblin_raider",
                min_drops=1,
                max_drops=3,
                bonus_drop_chance=0.1,
            )
            entries1 = [
                LootEntry(
                    entry_id="entry_gob_001",
                    table_id=t1.table_id,
                    item=LootItem(
                        item_id="item_rusty_dagger",
                        name="Rusty Dagger",
                        rarity=ItemRarity.COMMON.value,
                        quantity_min=1,
                        quantity_max=1,
                    ),
                    drop_chance=0.8,
                    weight=500.0,
                ),
                LootEntry(
                    entry_id="entry_gob_002",
                    table_id=t1.table_id,
                    item=LootItem(
                        item_id="item_copper_coins",
                        name="Copper Coins",
                        rarity=ItemRarity.CURRENCY.value,
                        quantity_min=5,
                        quantity_max=50,
                    ),
                    drop_chance=1.0,
                    weight=800.0,
                    is_guaranteed=True,
                    luck_modified=False,
                ),
                LootEntry(
                    entry_id="entry_gob_003",
                    table_id=t1.table_id,
                    item=LootItem(
                        item_id="item_goblin_ear",
                        name="Goblin Ear",
                        rarity=ItemRarity.COMMON.value,
                        quantity_min=1,
                        quantity_max=2,
                    ),
                    drop_chance=0.6,
                    weight=300.0,
                ),
                LootEntry(
                    entry_id="entry_gob_004",
                    table_id=t1.table_id,
                    item=LootItem(
                        item_id="item_sharp_blade",
                        name="Sharp Blade",
                        rarity=ItemRarity.UNCOMMON.value,
                    ),
                    drop_chance=0.15,
                    weight=100.0,
                ),
                LootEntry(
                    entry_id="entry_gob_005",
                    table_id=t1.table_id,
                    item=LootItem(
                        item_id="item_goblin_charm",
                        name="Goblin Charm",
                        rarity=ItemRarity.RARE.value,
                    ),
                    drop_chance=0.03,
                    weight=20.0,
                ),
            ]
            t1.entries = entries1
            self._tables[t1.table_id] = t1
            for e in entries1:
                self._entries[e.entry_id] = e

            # Table 2: Dragon Boss drops
            t2 = LootTable(
                table_id="table_dragon_boss",
                name="Ancient Dragon Loot",
                description="Drops from the ancient dragon boss.",
                source_type="boss",
                source_id="boss_ancient_dragon",
                min_drops=3,
                max_drops=6,
                bonus_drop_chance=0.25,
            )
            entries2 = [
                LootEntry(
                    entry_id="entry_drag_001",
                    table_id=t2.table_id,
                    item=LootItem(
                        item_id="item_gold_coins",
                        name="Gold Coins",
                        rarity=ItemRarity.CURRENCY.value,
                        quantity_min=100,
                        quantity_max=500,
                    ),
                    drop_chance=1.0,
                    weight=1000.0,
                    is_guaranteed=True,
                    luck_modified=False,
                ),
                LootEntry(
                    entry_id="entry_drag_002",
                    table_id=t2.table_id,
                    item=LootItem(
                        item_id="item_dragon_scale",
                        name="Dragon Scale",
                        rarity=ItemRarity.EPIC.value,
                        quantity_min=2,
                        quantity_max=5,
                    ),
                    drop_chance=0.9,
                    weight=200.0,
                ),
                LootEntry(
                    entry_id="entry_drag_003",
                    table_id=t2.table_id,
                    item=LootItem(
                        item_id="item_dragon_bone",
                        name="Dragon Bone",
                        rarity=ItemRarity.RARE.value,
                        quantity_min=1,
                        quantity_max=3,
                    ),
                    drop_chance=0.8,
                    weight=150.0,
                ),
                LootEntry(
                    entry_id="entry_drag_004",
                    table_id=t2.table_id,
                    item=LootItem(
                        item_id="item_dragonslayer_sword",
                        name="Dragonslayer Sword",
                        rarity=ItemRarity.LEGENDARY.value,
                    ),
                    drop_chance=0.05,
                    weight=10.0,
                ),
                LootEntry(
                    entry_id="entry_drag_005",
                    table_id=t2.table_id,
                    item=LootItem(
                        item_id="item_dragon_heart",
                        name="Dragon Heart",
                        rarity=ItemRarity.MYTHIC.value,
                    ),
                    drop_chance=0.005,
                    weight=1.0,
                    is_bonus=True,
                ),
                LootEntry(
                    entry_id="entry_drag_006",
                    table_id=t2.table_id,
                    item=LootItem(
                        item_id="item_ancient_rune",
                        name="Ancient Rune",
                        rarity=ItemRarity.EPIC.value,
                    ),
                    drop_chance=0.2,
                    weight=50.0,
                    condition=DropCondition.BOSS_KILL.value,
                ),
            ]
            t2.entries = entries2
            self._tables[t2.table_id] = t2
            for e in entries2:
                self._entries[e.entry_id] = e

            # Table 3: Treasure Chest
            t3 = LootTable(
                table_id="table_treasure_chest",
                name="Treasure Chest",
                description="Random treasure chest contents.",
                source_type="chest",
                source_id="chest_golden",
                min_drops=2,
                max_drops=4,
                bonus_drop_chance=0.15,
            )
            entries3 = [
                LootEntry(
                    entry_id="entry_chest_001",
                    table_id=t3.table_id,
                    item=LootItem(
                        item_id="item_silver_coins",
                        name="Silver Coins",
                        rarity=ItemRarity.CURRENCY.value,
                        quantity_min=20,
                        quantity_max=100,
                    ),
                    drop_chance=1.0,
                    weight=800.0,
                    is_guaranteed=True,
                    luck_modified=False,
                ),
                LootEntry(
                    entry_id="entry_chest_002",
                    table_id=t3.table_id,
                    item=LootItem(
                        item_id="item_health_potion",
                        name="Health Potion",
                        rarity=ItemRarity.COMMON.value,
                        quantity_min=1,
                        quantity_max=3,
                    ),
                    drop_chance=0.7,
                    weight=400.0,
                ),
                LootEntry(
                    entry_id="entry_chest_003",
                    table_id=t3.table_id,
                    item=LootItem(
                        item_id="item_mana_potion",
                        name="Mana Potion",
                        rarity=ItemRarity.COMMON.value,
                        quantity_min=1,
                        quantity_max=2,
                    ),
                    drop_chance=0.5,
                    weight=300.0,
                ),
                LootEntry(
                    entry_id="entry_chest_004",
                    table_id=t3.table_id,
                    item=LootItem(
                        item_id="item_enchanted_ring",
                        name="Enchanted Ring",
                        rarity=ItemRarity.RARE.value,
                    ),
                    drop_chance=0.1,
                    weight=30.0,
                ),
                LootEntry(
                    entry_id="entry_chest_005",
                    table_id=t3.table_id,
                    item=LootItem(
                        item_id="item_treasure_map",
                        name="Treasure Map",
                        rarity=ItemRarity.EPIC.value,
                    ),
                    drop_chance=0.03,
                    weight=5.0,
                ),
            ]
            t3.entries = entries3
            self._tables[t3.table_id] = t3
            for e in entries3:
                self._entries[e.entry_id] = e

            # Player luck
            self._player_luck["player_starter"] = PlayerLuck(
                player_id="player_starter",
                base_luck=10.0,
                bonus_luck=5.0,
                total_rolls=0,
            )
            self._player_luck["player_veteran"] = PlayerLuck(
                player_id="player_veteran",
                base_luck=50.0,
                bonus_luck=25.0,
                total_rolls=0,
            )

            self._update_stats()
            self._initialized = True

    def _update_stats(self) -> None:
        self._stats.total_tables = len(self._tables)
        self._stats.total_entries = len(self._entries)
        self._stats.total_rolls = len(self._rolls)
        self._stats.total_distributions = len(self._distributions)
        self._stats.pending_distributions = sum(
            1 for d in self._distributions.values() if d.status == "pending"
        )

    def _record_event(
        self,
        kind: str,
        table_id: str = "",
        player_id: str = "",
        entry_id: str = "",
        roll_id: str = "",
        distribution_id: str = "",
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = LootEvent(
            event_id=f"evt_{self._event_counter:08d}",
            kind=kind,
            timestamp=_now(),
            table_id=table_id,
            player_id=player_id,
            entry_id=entry_id,
            roll_id=roll_id,
            distribution_id=distribution_id,
            description=description,
            details=details or {},
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _get_or_create_luck(self, player_id: str) -> PlayerLuck:
        luck = self._player_luck.get(player_id)
        if luck is None:
            luck = PlayerLuck(player_id=player_id)
            self._player_luck[player_id] = luck
            self._update_stats()
        return luck

    # ------------------------------------------------------------------
    # Table management
    # ------------------------------------------------------------------

    def register_table(
        self,
        table_id: str,
        name: str,
        description: str = "",
        source_type: str = "monster",
        source_id: str = "",
        min_drops: int = 1,
        max_drops: int = 3,
        bonus_drop_chance: float = 0.1,
    ) -> Tuple[bool, str, Optional[LootTable]]:
        if table_id in self._tables:
            return False, "exists", None
        if len(self._tables) >= _MAX_TABLES:
            return False, "capacity", None
        table = LootTable(
            table_id=table_id,
            name=name,
            description=description,
            source_type=source_type,
            source_id=source_id,
            min_drops=min_drops,
            max_drops=max_drops,
            bonus_drop_chance=bonus_drop_chance,
        )
        self._tables[table_id] = table
        self._record_event(
            LootEventKind.TABLE_REGISTERED.value,
            table_id=table_id,
            description=f"Table '{name}' registered",
        )
        self._update_stats()
        return True, "registered", table

    def remove_table(self, table_id: str) -> Tuple[bool, str]:
        if table_id not in self._tables:
            return False, "not_found"
        del self._tables[table_id]
        for eid in list(self._entries.keys()):
            if self._entries[eid].table_id == table_id:
                del self._entries[eid]
        self._record_event(
            LootEventKind.TABLE_REMOVED.value,
            table_id=table_id,
            description=f"Table removed",
        )
        self._update_stats()
        return True, "removed"

    def get_table(self, table_id: str) -> Optional[LootTable]:
        return self._tables.get(table_id)

    def list_tables(
        self, source_type: str = "", limit: int = 50, offset: int = 0
    ) -> List[LootTable]:
        tables = list(self._tables.values())
        if source_type:
            tables = [t for t in tables if t.source_type == source_type]
        return tables[offset : offset + limit]

    # ------------------------------------------------------------------
    # Entry management
    # ------------------------------------------------------------------

    def add_entry(
        self,
        entry_id: str,
        table_id: str,
        item_id: str,
        name: str,
        rarity: str = ItemRarity.COMMON.value,
        drop_chance: float = 1.0,
        weight: float = 100.0,
        min_amount: int = 1,
        max_amount: int = 1,
        condition: str = DropCondition.ALWAYS.value,
        condition_value: str = "",
        is_guaranteed: bool = False,
        is_bonus: bool = False,
        luck_modified: bool = True,
        icon: str = "",
        description: str = "",
        stackable: bool = True,
    ) -> Tuple[bool, str, Optional[LootEntry]]:
        if entry_id in self._entries:
            return False, "exists", None
        table = self._tables.get(table_id)
        if table is None:
            return False, "table_not_found", None
        if len(table.entries) >= _MAX_ENTRIES_PER_TABLE:
            return False, "capacity", None
        entry = LootEntry(
            entry_id=entry_id,
            table_id=table_id,
            item=LootItem(
                item_id=item_id,
                name=name,
                rarity=rarity,
                quantity_min=min_amount,
                quantity_max=max_amount,
                icon=icon,
                description=description,
                stackable=stackable,
            ),
            drop_chance=drop_chance,
            weight=weight,
            min_amount=min_amount,
            max_amount=max_amount,
            condition=condition,
            condition_value=condition_value,
            is_guaranteed=is_guaranteed,
            is_bonus=is_bonus,
            luck_modified=luck_modified,
        )
        self._entries[entry_id] = entry
        table.entries.append(entry)
        self._record_event(
            LootEventKind.ENTRY_ADDED.value,
            table_id=table_id,
            entry_id=entry_id,
            description=f"Entry '{name}' added to table {table_id}",
        )
        self._update_stats()
        return True, "added", entry

    def remove_entry(self, entry_id: str) -> Tuple[bool, str]:
        entry = self._entries.get(entry_id)
        if entry is None:
            return False, "not_found"
        del self._entries[entry_id]
        table = self._tables.get(entry.table_id)
        if table:
            table.entries = [e for e in table.entries if e.entry_id != entry_id]
        self._record_event(
            LootEventKind.ENTRY_REMOVED.value,
            table_id=entry.table_id,
            entry_id=entry_id,
            description=f"Entry removed",
        )
        self._update_stats()
        return True, "removed"

    def get_entry(self, entry_id: str) -> Optional[LootEntry]:
        return self._entries.get(entry_id)

    def list_entries(
        self, table_id: str = "", limit: int = 100, offset: int = 0
    ) -> List[LootEntry]:
        entries = list(self._entries.values())
        if table_id:
            entries = [e for e in entries if e.table_id == table_id]
        return entries[offset : offset + limit]

    # ------------------------------------------------------------------
    # Loot rolling
    # ------------------------------------------------------------------

    def roll_loot(
        self,
        table_id: str,
        player_id: str,
        source_id: str = "",
        party_size: int = 1,
    ) -> Tuple[bool, str, Optional[LootRoll]]:
        table = self._tables.get(table_id)
        if table is None:
            return False, "table_not_found", None
        luck = self._get_or_create_luck(player_id)
        total_luck = luck.total_luck * self._config.global_luck_multiplier
        num_drops = random.randint(table.min_drops, table.max_drops)
        eligible = [
            e for e in table.entries
            if not e.is_bonus
        ]
        bonus_eligible = [e for e in table.entries if e.is_bonus]
        dropped: List[Dict[str, Any]] = []
        bonus_dropped: List[Dict[str, Any]] = []

        guaranteed = [e for e in eligible if e.is_guaranteed]
        non_guaranteed = [e for e in eligible if not e.is_guaranteed]

        for entry in guaranteed:
            qty = random.randint(entry.min_amount, entry.max_amount)
            dropped.append({
                "item_id": entry.item.item_id,
                "name": entry.item.name,
                "rarity": entry.item.rarity,
                "quantity": qty,
                "entry_id": entry.entry_id,
            })

        remaining = max(0, num_drops - len(guaranteed))
        weighted_pool: List[Tuple[LootEntry, float]] = []
        for entry in non_guaranteed:
            effective_chance = entry.drop_chance
            if entry.luck_modified:
                luck_scale = RARITY_LUCK_SCALING.get(entry.item.rarity, 0.0)
                effective_chance = entry.drop_chance * (1.0 + total_luck * luck_scale * 0.01)
            effective_chance = _clamp(effective_chance, 0.0, 1.0)
            weighted_pool.append((entry, effective_chance))

        random.shuffle(weighted_pool)
        for entry, chance in weighted_pool:
            if remaining <= 0:
                break
            if random.random() < chance:
                qty = random.randint(entry.min_amount, entry.max_amount)
                dropped.append({
                    "item_id": entry.item.item_id,
                    "name": entry.item.name,
                    "rarity": entry.item.rarity,
                    "quantity": qty,
                    "entry_id": entry.entry_id,
                })
                remaining -= 1

        if bonus_eligible and random.random() < table.bonus_drop_chance:
            for entry in bonus_eligible:
                effective_chance = entry.drop_chance
                if entry.luck_modified:
                    luck_scale = RARITY_LUCK_SCALING.get(entry.item.rarity, 0.0)
                    effective_chance = entry.drop_chance * (1.0 + total_luck * luck_scale * 0.01)
                effective_chance = _clamp(effective_chance, 0.0, 1.0)
                if random.random() < effective_chance:
                    qty = random.randint(entry.min_amount, entry.max_amount)
                    bonus_dropped.append({
                        "item_id": entry.item.item_id,
                        "name": entry.item.name,
                        "rarity": entry.item.rarity,
                        "quantity": qty,
                        "entry_id": entry.entry_id,
                    })

        roll = LootRoll(
            roll_id=f"roll_{self._roll_counter:08d}",
            table_id=table_id,
            player_id=player_id,
            source_type=table.source_type,
            source_id=source_id or table.source_id,
            items_dropped=dropped,
            bonus_items=bonus_dropped,
            luck_value=total_luck,
            party_size=party_size,
        )
        self._roll_counter += 1
        self._rolls.append(roll)
        _evict_fifo_list(self._rolls, _MAX_ROLLS)
        self._history.append(roll)
        _evict_fifo_list(self._history, _MAX_HISTORY)

        luck.total_rolls += 1
        luck.last_roll = _now()
        all_drops = dropped + bonus_dropped
        for item in all_drops:
            rarity = item["rarity"]
            if rarity == ItemRarity.COMMON.value:
                self._stats.common_drops += 1
            elif rarity == ItemRarity.UNCOMMON.value:
                self._stats.uncommon_drops += 1
            elif rarity == ItemRarity.RARE.value:
                self._stats.rare_drops += 1
                luck.rare_drops += 1
            elif rarity == ItemRarity.EPIC.value:
                self._stats.epic_drops += 1
                luck.epic_drops += 1
            elif rarity == ItemRarity.LEGENDARY.value:
                self._stats.legendary_drops += 1
                luck.legendary_drops += 1
            elif rarity == ItemRarity.MYTHIC.value:
                self._stats.mythic_drops += 1
                luck.mythic_drops += 1
            elif rarity == ItemRarity.CURRENCY.value:
                self._stats.currency_drops += 1
        self._stats.total_items_dropped += len(all_drops)
        if bonus_dropped:
            self._stats.total_bonus_drops += len(bonus_dropped)
            self._record_event(
                LootEventKind.BONUS_LOOT.value,
                table_id=table_id,
                player_id=player_id,
                roll_id=roll.roll_id,
                description=f"Bonus loot dropped for {player_id}",
                details={"bonus_items": bonus_dropped},
            )
        self._record_event(
            LootEventKind.LOOT_ROLLED.value,
            table_id=table_id,
            player_id=player_id,
            roll_id=roll.roll_id,
            description=f"Loot rolled: {len(dropped)} items, {len(bonus_dropped)} bonus",
            details={"dropped": dropped, "bonus": bonus_dropped},
        )
        self._update_stats()
        return True, "rolled", roll

    def multi_roll(
        self,
        table_id: str,
        player_id: str,
        count: int = 1,
        source_id: str = "",
    ) -> Tuple[bool, str, List[LootRoll]]:
        rolls: List[LootRoll] = []
        for _ in range(count):
            ok, msg, roll = self.roll_loot(table_id, player_id, source_id)
            if ok and roll:
                rolls.append(roll)
        if not rolls:
            return False, "no_rolls", []
        return True, "rolled", rolls

    # ------------------------------------------------------------------
    # Player luck
    # ------------------------------------------------------------------

    def register_player_luck(
        self,
        player_id: str,
        base_luck: float = 0.0,
        bonus_luck: float = 0.0,
    ) -> Tuple[bool, str, Optional[PlayerLuck]]:
        if player_id in self._player_luck:
            return False, "exists", None
        luck = PlayerLuck(
            player_id=player_id,
            base_luck=base_luck,
            bonus_luck=bonus_luck,
        )
        self._player_luck[player_id] = luck
        self._record_event(
            LootEventKind.LUCK_UPDATED.value,
            player_id=player_id,
            description=f"Luck registered: base={base_luck}, bonus={bonus_luck}",
        )
        self._update_stats()
        return True, "registered", luck

    def get_player_luck(self, player_id: str) -> Optional[PlayerLuck]:
        return self._player_luck.get(player_id)

    def update_player_luck(
        self,
        player_id: str,
        base_luck: Optional[float] = None,
        bonus_luck: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[PlayerLuck]]:
        luck = self._get_or_create_luck(player_id)
        if base_luck is not None:
            luck.base_luck = base_luck
        if bonus_luck is not None:
            luck.bonus_luck = bonus_luck
        self._record_event(
            LootEventKind.LUCK_UPDATED.value,
            player_id=player_id,
            description=f"Luck updated: base={luck.base_luck}, bonus={luck.bonus_luck}",
        )
        return True, "updated", luck

    # ------------------------------------------------------------------
    # Party distribution
    # ------------------------------------------------------------------

    def create_distribution(
        self,
        table_id: str,
        source_id: str = "",
        party_members: Optional[List[str]] = None,
        share_mode: str = LootShareMode.PERSONAL.value,
        master_looter: str = "",
    ) -> Tuple[bool, str, Optional[PartyLootDistribution]]:
        if table_id not in self._tables:
            return False, "table_not_found", None
        if not party_members:
            return False, "no_members", None
        if len(self._distributions) >= _MAX_DISTRIBUTIONS:
            return False, "capacity", None
        dist_id = f"dist_{self._distribution_counter:08d}"
        self._distribution_counter += 1
        dist = PartyLootDistribution(
            distribution_id=dist_id,
            table_id=table_id,
            source_id=source_id,
            share_mode=share_mode,
            party_members=list(party_members),
            master_looter=master_looter,
        )
        if share_mode == LootShareMode.PERSONAL.value:
            for member in party_members:
                ok, msg, roll = self.roll_loot(table_id, member, source_id, len(party_members))
                if ok and roll:
                    dist.rolls.append({
                        "player_id": member,
                        "roll": roll.to_dict(),
                    })
            dist.status = "resolved"
            dist.resolved_at = _now()
        elif share_mode == LootShareMode.FREE_FOR_ALL.value:
            ok, msg, roll = self.roll_loot(table_id, party_members[0], source_id, len(party_members))
            if ok and roll:
                dist.rolls.append({
                    "player_id": party_members[0],
                    "roll": roll.to_dict(),
                })
            dist.status = "resolved"
            dist.resolved_at = _now()
        elif share_mode == LootShareMode.ROUND_ROBIN.value:
            for i, member in enumerate(party_members):
                ok, msg, roll = self.roll_loot(table_id, member, source_id, len(party_members))
                if ok and roll:
                    dist.rolls.append({
                        "player_id": member,
                        "roll": roll.to_dict(),
                        "round": i,
                    })
            dist.status = "resolved"
            dist.resolved_at = _now()
        elif share_mode == LootShareMode.MASTER_LOOTER.value:
            ok, msg, roll = self.roll_loot(table_id, master_looter or party_members[0], source_id, len(party_members))
            if ok and roll:
                dist.rolls.append({
                    "player_id": master_looter or party_members[0],
                    "roll": roll.to_dict(),
                    "pending_assignment": True,
                })
            dist.status = "pending"
        elif share_mode == LootShareMode.NEED_BEFORE_GREED.value:
            ok, msg, roll = self.roll_loot(table_id, party_members[0], source_id, len(party_members))
            if ok and roll:
                dist.rolls.append({
                    "player_id": party_members[0],
                    "roll": roll.to_dict(),
                    "pending_roll": True,
                })
            dist.status = "pending"
        self._distributions[dist_id] = dist
        self._record_event(
            LootEventKind.DISTRIBUTION_CREATED.value,
            table_id=table_id,
            distribution_id=dist_id,
            description=f"Distribution created: mode={share_mode}, members={len(party_members)}",
        )
        self._update_stats()
        return True, "created", dist

    def resolve_distribution(
        self,
        distribution_id: str,
        assignments: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str, Optional[PartyLootDistribution]]:
        dist = self._distributions.get(distribution_id)
        if dist is None:
            return False, "not_found", None
        if dist.status != "pending":
            return False, "not_pending", None
        if assignments:
            for roll_data in dist.rolls:
                roll_id = roll_data.get("roll", {}).get("roll_id", "")
                if roll_id in assignments:
                    roll_data["assigned_to"] = assignments[roll_id]
        dist.status = "resolved"
        dist.resolved_at = _now()
        self._record_event(
            LootEventKind.DISTRIBUTION_RESOLVED.value,
            distribution_id=distribution_id,
            description=f"Distribution resolved",
        )
        self._update_stats()
        return True, "resolved", dist

    def get_distribution(
        self, distribution_id: str
    ) -> Optional[PartyLootDistribution]:
        return self._distributions.get(distribution_id)

    def list_distributions(
        self,
        status: str = "",
        table_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[PartyLootDistribution]:
        dists = list(self._distributions.values())
        if status:
            dists = [d for d in dists if d.status == status]
        if table_id:
            dists = [d for d in dists if d.table_id == table_id]
        return dists[offset : offset + limit]

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_player_history(
        self, player_id: str, limit: int = 50
    ) -> List[LootRoll]:
        history = [r for r in self._history if r.player_id == player_id]
        return history[-limit:]

    def get_drop_history(
        self, table_id: str = "", limit: int = 50
    ) -> List[LootRoll]:
        history = list(self._history)
        if table_id:
            history = [r for r in history if r.table_id == table_id]
        return history[-limit:]

    # ------------------------------------------------------------------
    # System operations
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        self._tick_count += 1
        self._record_event(
            LootEventKind.TICK.value,
            description=f"Tick #{self._tick_count}",
        )
        return {"tick_count": self._tick_count}

    def set_config(self, config: Dict[str, Any]) -> LootConfig:
        if "max_tables" in config:
            self._config.max_tables = _safe_int(config["max_tables"], self._config.max_tables)
        if "max_entries_per_table" in config:
            self._config.max_entries_per_table = _safe_int(config["max_entries_per_table"], self._config.max_entries_per_table)
        if "max_rolls" in config:
            self._config.max_rolls = _safe_int(config["max_rolls"], self._config.max_rolls)
        if "max_player_luck" in config:
            self._config.max_player_luck = _safe_int(config["max_player_luck"], self._config.max_player_luck)
        if "max_distributions" in config:
            self._config.max_distributions = _safe_int(config["max_distributions"], self._config.max_distributions)
        if "max_history" in config:
            self._config.max_history = _safe_int(config["max_history"], self._config.max_history)
        if "global_luck_multiplier" in config:
            self._config.global_luck_multiplier = _safe_float(config["global_luck_multiplier"], self._config.global_luck_multiplier)
        if "bonus_drop_base_chance" in config:
            self._config.bonus_drop_base_chance = _safe_float(config["bonus_drop_base_chance"], self._config.bonus_drop_base_chance)
        if "rare_drop_threshold" in config:
            self._config.rare_drop_threshold = _safe_float(config["rare_drop_threshold"], self._config.rare_drop_threshold)
        if "personal_loot_mode" in config:
            self._config.personal_loot_mode = bool(config["personal_loot_mode"])
        if "tick_rate_hz" in config:
            self._config.tick_rate_hz = _safe_float(config["tick_rate_hz"], self._config.tick_rate_hz)
        self._record_event(
            LootEventKind.CONFIG_UPDATED.value,
            description="Configuration updated",
        )
        return self._config

    def get_config(self) -> LootConfig:
        return self._config

    def list_events(
        self,
        table_id: str = "",
        player_id: str = "",
        limit: int = 100,
    ) -> List[LootEvent]:
        events = list(self._events)
        if table_id:
            events = [e for e in events if e.table_id == table_id]
        if player_id:
            events = [e for e in events if e.player_id == player_id]
        return events[-limit:]

    def get_stats(self) -> LootStats:
        self._update_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        self._update_stats()
        return {
            "initialized": self._initialized,
            "total_tables": len(self._tables),
            "total_entries": len(self._entries),
            "total_rolls": len(self._rolls),
            "total_player_luck": len(self._player_luck),
            "total_distributions": len(self._distributions),
            "pending_distributions": sum(
                1 for d in self._distributions.values() if d.status == "pending"
            ),
            "total_history": len(self._history),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> LootSnapshot:
        self._update_stats()
        return LootSnapshot(
            tables=[t.to_dict() for t in self._tables.values()],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Dict[str, Any]:
        with self._init_lock:
            self._tables.clear()
            self._entries.clear()
            self._rolls.clear()
            self._player_luck.clear()
            self._distributions.clear()
            self._history.clear()
            self._events.clear()
            self._stats = LootStats()
            self._config = LootConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._roll_counter = 0
            self._entry_counter = 0
            self._distribution_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(
            LootEventKind.RESET.value,
            description="System reset and re-seeded",
        )
        return self.get_status()


def get_loot_drop_system() -> LootDropSystem:
    """Factory function for the singleton LootDropSystem."""
    return LootDropSystem.get_instance()
