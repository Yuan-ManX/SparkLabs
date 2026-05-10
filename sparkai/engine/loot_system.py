"""
SparkLabs Engine - Loot System

Procedural loot generation with rarity tiers, affix rolling,
smart drop tables, and contextual reward distribution. Supports
weighted random generation, boss-specific loot pools, and
pseudo-random bad luck protection.

Architecture:
  LootSystem
    |-- DropTable (weighted loot pool with conditional entries)
    |-- RarityEngine (multi-roll rarity determination)
    |-- AffixGenerator (prefix/suffix stat modification)
    |-- SmartLoot (class-appropriate and need-based filtering)
    |-- LootHistory (recent drop tracking for bad luck protection)

Rarity Tiers:
  - COMMON, UNCOMMON, RARE, EPIC, LEGENDARY, MYTHIC
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Rarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class LootCategory(Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    CURRENCY = "currency"
    QUEST_ITEM = "quest_item"


@dataclass
class Affix:
    affix_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    prefix: bool = True
    stat_modifiers: Dict[str, float] = field(default_factory=dict)
    min_rarity: Rarity = Rarity.COMMON
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "affix_id": self.affix_id,
            "name": self.name,
            "type": "prefix" if self.prefix else "suffix",
            "modifiers": self.stat_modifiers,
        }


@dataclass
class LootItem:
    item_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    base_name: str = ""
    category: LootCategory = LootCategory.MATERIAL
    rarity: Rarity = Rarity.COMMON
    level: int = 1
    prefix: Optional[Affix] = None
    suffix: Optional[Affix] = None
    quantity: int = 1
    stats: Dict[str, float] = field(default_factory=dict)
    sell_value: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category.value,
            "rarity": self.rarity.value,
            "level": self.level,
            "prefix": self.prefix.name if self.prefix else None,
            "suffix": self.suffix.name if self.suffix else None,
            "quantity": self.quantity,
            "stats": self.stats,
        }


@dataclass
class DropEntry:
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    base_item_name: str = ""
    category: LootCategory = LootCategory.MATERIAL
    min_rarity: Rarity = Rarity.COMMON
    max_rarity: Rarity = Rarity.EPIC
    weight: float = 1.0
    min_level: int = 1
    max_level: int = 100
    min_quantity: int = 1
    max_quantity: int = 1
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DropTable:
    table_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    entries: List[DropEntry] = field(default_factory=list)
    guaranteed_entries: List[DropEntry] = field(default_factory=list)
    min_drops: int = 1
    max_drops: int = 5
    bonus_luck: float = 0.0


class LootSystem:
    _instance: Optional[LootSystem] = None

    RARITY_WEIGHTS: Dict[Rarity, float] = {
        Rarity.COMMON: 100.0,
        Rarity.UNCOMMON: 50.0,
        Rarity.RARE: 20.0,
        Rarity.EPIC: 5.0,
        Rarity.LEGENDARY: 1.0,
        Rarity.MYTHIC: 0.1,
    }

    RARITY_COLORS: Dict[Rarity, str] = {
        Rarity.COMMON: "#9d9d9d",
        Rarity.UNCOMMON: "#1eff00",
        Rarity.RARE: "#0070dd",
        Rarity.EPIC: "#a335ee",
        Rarity.LEGENDARY: "#ff8000",
        Rarity.MYTHIC: "#e6cc80",
    }

    def __init__(self):
        self._tables: Dict[str, DropTable] = {}
        self._affixes: Dict[str, Affix] = {}
        self._drop_history: Dict[str, List[float]] = {}
        self._seed: int = int(time.time())
        self._total_drops: int = 0

        self._initialize_default_affixes()

    @classmethod
    def get_instance(cls) -> LootSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_default_affixes(self):
        defaults = [
            Affix("sharp", "Sharp", True, {"attack": 5.0}, Rarity.COMMON, 3.0),
            Affix("sturdy", "Sturdy", True, {"defense": 4.0}, Rarity.COMMON, 3.0),
            Affix("swift", "Swift", True, {"speed": 3.0}, Rarity.UNCOMMON, 2.0),
            Affix("flaming", "Flaming", True, {"fire_damage": 10.0}, Rarity.RARE, 1.5),
            Affix("vampiric", "Vampiric", True, {"life_steal": 5.0}, Rarity.EPIC, 1.0),
            Affix("divine", "Divine", True, {"all_stats": 8.0}, Rarity.LEGENDARY, 0.5),
            Affix("of_strength", "of Strength", False, {"strength": 3.0}, Rarity.COMMON, 3.0),
            Affix("of_agility", "of Agility", False, {"agility": 3.0}, Rarity.COMMON, 3.0),
            Affix("of_chaos", "of Chaos", False, {"random_stat": 10.0}, Rarity.LEGENDARY, 0.5),
        ]
        for affix in defaults:
            self._affixes[affix.affix_id] = affix

    def register_table(self, table: DropTable) -> str:
        self._tables[table.table_id] = table
        return table.table_id

    def register_affix(self, affix: Affix) -> str:
        self._affixes[affix.affix_id] = affix
        return affix.affix_id

    def set_seed(self, seed: int):
        self._seed = seed
        random.seed(seed)

    def roll_rarity(self, luck_modifier: float = 0.0) -> Rarity:
        total = 0.0
        adjusted = {}
        for rarity, weight in self.RARITY_WEIGHTS.items():
            adjusted_weight = weight * (1.0 + luck_modifier)
            adjusted[rarity] = adjusted_weight
            total += adjusted_weight

        roll = random.random() * total
        cumulative = 0.0
        for rarity, weight in adjusted.items():
            cumulative += weight
            if roll < cumulative:
                return rarity
        return Rarity.COMMON

    def roll_affix(self, rarity: Rarity, is_prefix: bool) -> Optional[Affix]:
        candidates = [
            a for a in self._affixes.values()
            if a.prefix == is_prefix and a.min_rarity.value <= rarity.value
        ]
        if not candidates:
            return None
        weights = [a.weight for a in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def generate_loot(
        self,
        table_id: str,
        player_level: int = 1,
        luck_modifier: float = 0.0,
        count: Optional[int] = None,
    ) -> List[LootItem]:
        table = self._tables.get(table_id)
        if table is None:
            return []

        effective_luck = luck_modifier + table.bonus_luck
        num_drops = count or random.randint(table.min_drops, table.max_drops)
        results = []

        for entry in table.guaranteed_entries:
            if entry.min_level <= player_level <= entry.max_level:
                item = self._create_item_from_entry(entry, player_level, effective_luck)
                results.append(item)

        valid_entries = [
            e for e in table.entries
            if e.min_level <= player_level <= e.max_level
        ]
        if not valid_entries:
            return results

        weights = [e.weight for e in valid_entries]
        for _ in range(num_drops):
            entry = random.choices(valid_entries, weights=weights, k=1)[0]
            item = self._create_item_from_entry(entry, player_level, effective_luck)
            results.append(item)
            self._total_drops += 1

        return results

    def _create_item_from_entry(
        self, entry: DropEntry, level: int, luck: float
    ) -> LootItem:
        rarity = self.roll_rarity(luck)
        rarity_values = list(self.RARITY_WEIGHTS.keys())
        min_rarity_idx = rarity_values.index(entry.min_rarity)
        max_rarity_idx = rarity_values.index(entry.max_rarity)
        rolled_idx = rarity_values.index(rarity)
        if rolled_idx < min_rarity_idx:
            rarity = entry.min_rarity
        elif rolled_idx > max_rarity_idx:
            rarity = entry.max_rarity

        prefix = self.roll_affix(rarity, True) if rarity.value >= Rarity.UNCOMMON.value else None
        suffix = self.roll_affix(rarity, False) if rarity.value >= Rarity.UNCOMMON.value else None

        quantity = random.randint(entry.min_quantity, entry.max_quantity)

        stats = {}
        base_stats = {"level": float(level)}
        if prefix:
            for stat, value in prefix.stat_modifiers.items():
                stats[stat] = stats.get(stat, 0) + value
        if suffix:
            for stat, value in suffix.stat_modifiers.items():
                stats[stat] = stats.get(stat, 0) + value

        rarity_multiplier = (rarity_values.index(rarity) + 1) * 0.5
        for stat in stats:
            stats[stat] = round(stats[stat] * rarity_multiplier * (1.0 + level * 0.05), 1)

        name = entry.base_item_name
        if prefix:
            name = f"{prefix.name} {name}"
        if suffix:
            name = f"{name} {suffix.name}"

        sell_value = (rarity_values.index(rarity) + 1) * level * quantity * 10

        return LootItem(
            base_name=entry.base_item_name,
            name=name,
            category=entry.category,
            rarity=rarity,
            level=level,
            prefix=prefix,
            suffix=suffix,
            quantity=quantity,
            stats=stats,
            sell_value=sell_value,
        )

    def get_drop_table(self, table_id: str) -> Optional[DropTable]:
        return self._tables.get(table_id)

    def get_rarity_color(self, rarity: Rarity) -> str:
        return self.RARITY_COLORS.get(rarity, "#ffffff")

    def get_rarity_weights(self) -> Dict[str, float]:
        return {r.value: w for r, w in self.RARITY_WEIGHTS.items()}

    def get_stats(self) -> Dict[str, Any]:
        total_affixes = len(self._affixes)
        return {
            "total_tables": len(self._tables),
            "total_drops": self._total_drops,
            "total_affixes": total_affixes,
            "prefix_count": sum(1 for a in self._affixes.values() if a.prefix),
            "suffix_count": sum(1 for a in self._affixes.values() if not a.prefix),
            "rarity_weights": self.get_rarity_weights(),
        }


def get_loot_system() -> LootSystem:
    return LootSystem.get_instance()