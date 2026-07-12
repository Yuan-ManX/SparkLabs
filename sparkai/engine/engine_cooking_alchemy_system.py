"""
SparkLabs Engine - Cooking & Alchemy System

Manages recipe-based crafting of consumable items through cooking and
alchemy. Players gather ingredients, discover recipes, operate crafting
stations, and produce food buffs and potions with stacking effects,
quality tiers, and skill-based crafting outcomes.

Architecture:
  CookingAlchemySystem (singleton)
    |-- RecipeType, IngredientCategory, CraftingStation, CraftQuality,
       EffectKind, CookingAlchemyEventKind
    |-- IngredientDefinition, RecipeDefinition, CraftingStationInstance,
       CraftedItem, ActiveEffect, CraftingSkill, RecipeDiscovery,
       CookingAlchemyConfig, CookingAlchemyStats, CookingAlchemySnapshot,
       CookingAlchemyEvent
    |-- get_cooking_alchemy_system

Core Capabilities:
  - register_ingredient / remove_ingredient / get_ingredient / list_ingredients
  - register_recipe / remove_recipe / get_recipe / list_recipes
  - register_station / remove_station / get_station / list_stations
  - craft_item / get_crafted_item / list_crafted_items
  - get_active_effects / apply_effect / dispel_effect
  - get_crafting_skill / level_up_skill / get_skill_rank
  - discover_recipe / get_discoveries / list_discoveries
  - get_recipe_suggestions / get_ingredient_substitutes
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`CookingAlchemySystem.get_instance` or the module-level
:func:`get_cooking_alchemy_system` factory.
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

_MAX_INGREDIENTS: int = 2000
_MAX_RECIPES: int = 3000
_MAX_STATIONS: int = 500
_MAX_CRAFTED_ITEMS: int = 500000
_MAX_ACTIVE_EFFECTS: int = 100000
_MAX_DISCOVERIES: int = 100000
_MAX_EVENTS: int = 10000


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

class RecipeType(str, Enum):
    """Type of crafting recipe."""
    COOKING = "cooking"
    ALCHEMY = "alchemy"
    BREWING = "brewing"
    MIXING = "mixing"
    DISTILLING = "distilling"
    FERMENTING = "fermenting"


class IngredientCategory(str, Enum):
    """Category of a crafting ingredient."""
    HERB = "herb"
    SPICE = "spice"
    MEAT = "meat"
    FISH = "fish"
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    GRAIN = "grain"
    DAIRY = "dairy"
    MINERAL = "mineral"
    MONSTER_PART = "monster_part"
    MAGICAL = "magical"
    LIQUID = "liquid"


class CraftingStation(str, Enum):
    """Type of crafting station."""
    CAMPFIRE = "campfire"
    KITCHEN = "kitchen"
    CAULDRON = "cauldron"
    ALCHEMY_BENCH = "alchemy_bench"
    BREWING_BARREL = "brewing_barrel"
    DISTILLERY = "distillery"
    FERMENTATION_VAT = "fermentation_vat"


class CraftQuality(str, Enum):
    """Quality tier of a crafted item."""
    FAILED = "failed"
    POOR = "poor"
    COMMON = "common"
    GOOD = "good"
    EXCELLENT = "excellent"
    PERFECT = "perfect"
    MASTERWORK = "masterwork"


class EffectKind(str, Enum):
    """Types of effects granted by crafted consumables."""
    HEAL = "heal"
    MANA_RESTORE = "mana_restore"
    STAMINA_RESTORE = "stamina_restore"
    BUFF_ATTACK = "buff_attack"
    BUFF_DEFENSE = "buff_defense"
    BUFF_SPEED = "buff_speed"
    BUFF_CRITICAL = "buff_critical"
    RESIST_FIRE = "resist_fire"
    RESIST_ICE = "resist_ice"
    RESIST_POISON = "resist_poison"
    RESIST_LIGHTNING = "resist_lightning"
    CURE_POISON = "cure_poison"
    CURE_DISEASE = "cure_disease"
    INVISIBILITY = "invisibility"
    NIGHT_VISION = "night_vision"
    WATER_BREATHING = "water_breathing"
    REGENERATION = "regeneration"
    FORTIFY_HEALTH = "fortify_health"
    FORTIFY_MANA = "fortify_mana"
    FORTIFY_STAMINA = "fortify_stamina"


class CookingAlchemyEventKind(str, Enum):
    """Audit event types emitted by the cooking & alchemy system."""
    INGREDIENT_REGISTERED = "ingredient_registered"
    INGREDIENT_REMOVED = "ingredient_removed"
    RECIPE_REGISTERED = "recipe_registered"
    RECIPE_REMOVED = "recipe_removed"
    STATION_REGISTERED = "station_registered"
    STATION_REMOVED = "station_removed"
    ITEM_CRAFTED = "item_crafted"
    EFFECT_APPLIED = "effect_applied"
    EFFECT_DISPELLED = "effect_dispelled"
    EFFECT_EXPIRED = "effect_expired"
    SKILL_LEVELED = "skill_leveled"
    RECIPE_DISCOVERED = "recipe_discovered"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class IngredientDefinition:
    """Definition of a crafting ingredient."""
    ingredient_id: str
    name: str
    description: str = ""
    category: str = IngredientCategory.HERB.value
    rarity: str = "common"
    base_value: float = 1.0
    gathering_skill_required: int = 0
    gathering_location: str = ""
    season: str = ""
    is_magical: bool = False
    potency: float = 1.0
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RecipeIngredient:
    """An ingredient requirement in a recipe."""
    ingredient_id: str
    quantity: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RecipeEffect:
    """An effect produced by consuming a crafted item."""
    effect_kind: str = EffectKind.HEAL.value
    magnitude: float = 10.0
    duration_seconds: float = 0.0
    stacking_rule: str = "refresh"  # refresh, stack, no_stack

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RecipeDefinition:
    """Definition of a cooking or alchemy recipe."""
    recipe_id: str
    name: str
    description: str = ""
    recipe_type: str = RecipeType.COOKING.value
    required_station: str = CraftingStation.CAMPFIRE.value
    ingredients: List[RecipeIngredient] = field(default_factory=list)
    effects: List[RecipeEffect] = field(default_factory=list)
    required_skill_level: int = 1
    base_craft_time: float = 10.0
    output_item_name: str = ""
    output_quantity: int = 1
    icon: str = ""
    is_learned_by_default: bool = False
    discovery_xp: int = 50
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CraftingStationInstance:
    """A placed crafting station in the world."""
    station_id: str
    station_type: str = CraftingStation.CAMPFIRE.value
    name: str = ""
    location_x: float = 0.0
    location_y: float = 0.0
    location_z: float = 0.0
    is_public: bool = True
    owner_player_id: str = ""
    upgrade_level: int = 1
    craft_speed_multiplier: float = 1.0
    quality_bonus: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CraftedItem:
    """An item produced through crafting."""
    item_id: str
    recipe_id: str
    crafter_player_id: str
    name: str = ""
    quality: str = CraftQuality.COMMON.value
    effects: List[RecipeEffect] = field(default_factory=list)
    potency_multiplier: float = 1.0
    duration_multiplier: float = 1.0
    crafted_at: float = field(default_factory=_now)
    expires_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at <= 0:
            return False
        return _now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["is_expired"] = self.is_expired
        return d


@dataclass
class ActiveEffect:
    """An active effect on a player from a consumed item."""
    effect_id: str
    player_id: str
    effect_kind: str = EffectKind.HEAL.value
    magnitude: float = 10.0
    remaining_duration: float = 0.0
    total_duration: float = 0.0
    source_item_id: str = ""
    stacking_rule: str = "refresh"
    applied_at: float = field(default_factory=_now)
    stacks: int = 1

    @property
    def is_expired(self) -> bool:
        if self.remaining_duration <= 0:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["is_expired"] = self.is_expired
        return d


@dataclass
class CraftingSkill:
    """A player's crafting skill progression."""
    player_id: str
    cooking_level: int = 1
    cooking_xp: int = 0
    alchemy_level: int = 1
    alchemy_xp: int = 0
    brewing_level: int = 1
    brewing_xp: int = 0
    total_crafts: int = 0
    perfect_crafts: int = 0
    masterwork_crafts: int = 0
    discovered_recipe_ids: List[str] = field(default_factory=list)

    def get_skill_level(self, recipe_type: str) -> int:
        if recipe_type == RecipeType.COOKING.value:
            return self.cooking_level
        elif recipe_type in (RecipeType.ALCHEMY.value, RecipeType.MIXING.value):
            return self.alchemy_level
        elif recipe_type in (RecipeType.BREWING.value, RecipeType.FERMENTING.value, RecipeType.DISTILLING.value):
            return self.brewing_level
        return 1

    def get_skill_xp(self, recipe_type: str) -> int:
        if recipe_type == RecipeType.COOKING.value:
            return self.cooking_xp
        elif recipe_type in (RecipeType.ALCHEMY.value, RecipeType.MIXING.value):
            return self.alchemy_xp
        elif recipe_type in (RecipeType.BREWING.value, RecipeType.FERMENTING.value, RecipeType.DISTILLING.value):
            return self.brewing_xp
        return 0

    def add_xp(self, recipe_type: str, xp: int) -> int:
        """Add XP and return levels gained."""
        levels_gained = 0
        if recipe_type == RecipeType.COOKING.value:
            self.cooking_xp += xp
            while self.cooking_xp >= self.cooking_level * 100:
                self.cooking_xp -= self.cooking_level * 100
                self.cooking_level += 1
                levels_gained += 1
        elif recipe_type in (RecipeType.ALCHEMY.value, RecipeType.MIXING.value):
            self.alchemy_xp += xp
            while self.alchemy_xp >= self.alchemy_level * 100:
                self.alchemy_xp -= self.alchemy_level * 100
                self.alchemy_level += 1
                levels_gained += 1
        elif recipe_type in (RecipeType.BREWING.value, RecipeType.FERMENTING.value, RecipeType.DISTILLING.value):
            self.brewing_xp += xp
            while self.brewing_xp >= self.brewing_level * 100:
                self.brewing_xp -= self.brewing_level * 100
                self.brewing_level += 1
                levels_gained += 1
        return levels_gained

    def get_rank(self, recipe_type: str) -> str:
        level = self.get_skill_level(recipe_type)
        if level >= 50:
            return "grandmaster"
        elif level >= 30:
            return "master"
        elif level >= 15:
            return "journeyman"
        elif level >= 5:
            return "apprentice"
        return "novice"

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["cooking_rank"] = self.get_rank(RecipeType.COOKING.value)
        d["alchemy_rank"] = self.get_rank(RecipeType.ALCHEMY.value)
        d["brewing_rank"] = self.get_rank(RecipeType.BREWING.value)
        return d


@dataclass
class RecipeDiscovery:
    """Record of a player discovering a recipe."""
    discovery_id: str
    player_id: str
    recipe_id: str
    discovery_method: str = "experiment"  # experiment, quest, npc, scroll
    xp_gained: int = 50
    discovered_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CookingAlchemyConfig:
    """Global tuning parameters."""
    max_ingredients: int = 2000
    max_recipes: int = 3000
    max_stations: int = 500
    max_crafted_items_per_player: int = 1000
    max_active_effects_per_player: int = 20
    base_craft_xp: int = 10
    perfect_craft_xp_bonus: int = 20
    masterwork_craft_xp_bonus: int = 50
    discovery_xp_base: int = 50
    effect_tick_interval: float = 1.0
    item_expiry_hours: float = 24.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CookingAlchemyStats:
    """Aggregate statistics."""
    total_ingredients: int = 0
    total_recipes: int = 0
    total_stations: int = 0
    total_crafted_items: int = 0
    total_active_effects: int = 0
    total_discoveries: int = 0
    total_perfect_crafts: int = 0
    total_masterwork_crafts: int = 0
    total_failed_crafts: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CookingAlchemySnapshot:
    """Full state snapshot."""
    ingredients: List[Dict[str, Any]] = field(default_factory=list)
    recipes: List[Dict[str, Any]] = field(default_factory=list)
    stations: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CookingAlchemyEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    ingredient_id: str = ""
    recipe_id: str = ""
    station_id: str = ""
    item_id: str = ""
    player_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Cooking & Alchemy System
# ---------------------------------------------------------------------------

class CookingAlchemySystem:
    """Manages cooking and alchemy crafting, ingredients, and effects."""

    _instance: Optional["CookingAlchemySystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._ingredients: Dict[str, IngredientDefinition] = {}
        self._recipes: Dict[str, RecipeDefinition] = {}
        self._stations: Dict[str, CraftingStationInstance] = {}
        self._crafted_items: Dict[str, CraftedItem] = {}
        self._player_items: Dict[str, List[str]] = {}
        self._active_effects: Dict[str, List[ActiveEffect]] = {}
        self._crafting_skills: Dict[str, CraftingSkill] = {}
        self._discoveries: Dict[str, RecipeDiscovery] = {}
        self._player_discoveries: Dict[str, List[str]] = {}
        self._events: List[CookingAlchemyEvent] = []
        self._stats = CookingAlchemyStats()
        self._config = CookingAlchemyConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "CookingAlchemySystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            # Ingredients
            ingredients = [
                ("ing_herbmint", "Wild Mint", "A refreshing herb", IngredientCategory.HERB.value, "common", 2.0, 0, "forest"),
                ("ing_herbchamomile", "Chamomile", "Calming flower", IngredientCategory.HERB.value, "common", 3.0, 0, "meadow"),
                ("ing_herbmoonleaf", "Moonleaf", "Glows under moonlight", IngredientCategory.HERB.value, "rare", 15.0, 10, "forest_night"),
                ("ing_herbfirebloom", "Firebloom", "Hot to the touch", IngredientCategory.HERB.value, "rare", 20.0, 15, "volcanic"),
                ("ing_spicesalt", "Sea Salt", "Common seasoning", IngredientCategory.SPICE.value, "common", 1.0, 0, "coast"),
                ("ing_spicepepper", "Black Pepper", "Pungent spice", IngredientCategory.SPICE.value, "common", 2.0, 0, "market"),
                ("ing_meatwolf", "Wolf Meat", "Tough but nutritious", IngredientCategory.MEAT.value, "common", 5.0, 0, "hunt"),
                ("ing_meatboar", "Boar Meat", "Rich and savory", IngredientCategory.MEAT.value, "common", 8.0, 0, "hunt"),
                ("ing_fishtROUT", "Trout", "Fresh river fish", IngredientCategory.FISH.value, "common", 6.0, 0, "river"),
                ("ing_fishsalmon", "Salmon", "Premium fish", IngredientCategory.FISH.value, "uncommon", 12.0, 5, "river"),
                ("ing_vegcabbage", "Cabbage", "Leafy vegetable", IngredientCategory.VEGETABLE.value, "common", 2.0, 0, "farm"),
                ("ing_vegcarrot", "Carrot", "Root vegetable", IngredientCategory.VEGETABLE.value, "common", 2.0, 0, "farm"),
                ("ing_fruitapple", "Apple", "Sweet fruit", IngredientCategory.FRUIT.value, "common", 3.0, 0, "orchard"),
                ("ing_fruitberry", "Glowberry", "Magical berry", IngredientCategory.FRUIT.value, "uncommon", 8.0, 5, "forest"),
                ("ing_grainwheat", "Wheat", "Basic grain", IngredientCategory.GRAIN.value, "common", 1.0, 0, "farm"),
                ("ing_dairycheese", "Cheese", "Aged dairy", IngredientCategory.DAIRY.value, "common", 5.0, 0, "market"),
                ("ing_mineralcrystal", "Mana Crystal", "Crystallized magic", IngredientCategory.MINERAL.value, "epic", 50.0, 25, "caves"),
                ("ing_monster_essence", "Monster Essence", "Raw monster energy", IngredientCategory.MONSTER_PART.value, "rare", 25.0, 15, "hunt_boss"),
                ("ing_magicalsoul", "Soul Dust", "Refined spiritual essence", IngredientCategory.MAGICAL.value, "epic", 40.0, 20, "alchemy"),
                ("ing_liquidwater", "Pure Water", "Clean water", IngredientCategory.LIQUID.value, "common", 1.0, 0, "any"),
            ]
            for ing_id, name, desc, cat, rarity, val, skill_req, loc in ingredients:
                ing = IngredientDefinition(
                    ingredient_id=ing_id, name=name, description=desc,
                    category=cat, rarity=rarity, base_value=val,
                    gathering_skill_required=skill_req, gathering_location=loc,
                )
                self._ingredients[ing_id] = ing

            # Recipes - Cooking
            recipes_cooking = [
                ("rec_cook_stew", "Hearty Stew", "A warm filling stew", RecipeType.COOKING.value, CraftingStation.CAMPFIRE.value,
                 [("ing_meatwolf", 2), ("ing_vegcabbage", 1), ("ing_spicesalt", 1)],
                 [(EffectKind.HEAL.value, 30.0, 0.0, "refresh"), (EffectKind.FORTIFY_HEALTH.value, 20.0, 300.0, "refresh")],
                 1, 15.0, "Hearty Stew", 1, True),
                ("rec_cook_roast", "Boar Roast", "Tender roasted boar", RecipeType.COOKING.value, CraftingStation.KITCHEN.value,
                 [("ing_meatboar", 2), ("ing_spicepepper", 1), ("ing_spicesalt", 1)],
                 [(EffectKind.HEAL.value, 50.0, 0.0, "refresh"), (EffectKind.BUFF_ATTACK.value, 15.0, 600.0, "refresh")],
                 5, 20.0, "Boar Roast", 1, True),
                ("rec_cook_fishpie", "Trout Pie", "Delicious fish pie", RecipeType.COOKING.value, CraftingStation.KITCHEN.value,
                 [("ing_fishtROUT", 2), ("ing_grainwheat", 2), ("ing_vegcabbage", 1)],
                 [(EffectKind.HEAL.value, 35.0, 0.0, "refresh"), (EffectKind.BUFF_DEFENSE.value, 10.0, 300.0, "refresh")],
                 3, 18.0, "Trout Pie", 1, True),
                ("rec_cook_feast", "Royal Feast", "A magnificent meal", RecipeType.COOKING.value, CraftingStation.KITCHEN.value,
                 [("ing_meatboar", 3), ("ing_fishsalmon", 2), ("ing_fruitapple", 2), ("ing_dairycheese", 1), ("ing_spicesalt", 1)],
                 [(EffectKind.HEAL.value, 100.0, 0.0, "refresh"), (EffectKind.BUFF_ATTACK.value, 25.0, 900.0, "refresh"),
                  (EffectKind.BUFF_DEFENSE.value, 25.0, 900.0, "refresh"), (EffectKind.REGENERATION.value, 10.0, 600.0, "refresh")],
                 20, 45.0, "Royal Feast", 1, False),
            ]

            # Recipes - Alchemy
            recipes_alchemy = [
                ("rec_alch_heal_potion", "Healing Potion", "Restores health", RecipeType.ALCHEMY.value, CraftingStation.ALCHEMY_BENCH.value,
                 [("ing_herbmint", 2), ("ing_liquidwater", 1)],
                 [(EffectKind.HEAL.value, 50.0, 0.0, "refresh")],
                 1, 10.0, "Healing Potion", 1, True),
                ("rec_alch_mana_potion", "Mana Potion", "Restores mana", RecipeType.ALCHEMY.value, CraftingStation.ALCHEMY_BENCH.value,
                 [("ing_herbmoonleaf", 1), ("ing_liquidwater", 1)],
                 [(EffectKind.MANA_RESTORE.value, 50.0, 0.0, "refresh")],
                 5, 12.0, "Mana Potion", 1, True),
                ("rec_alch_fire_resist", "Fire Resistance Potion", "Grants fire resistance", RecipeType.ALCHEMY.value, CraftingStation.ALCHEMY_BENCH.value,
                 [("ing_herbfirebloom", 1), ("ing_liquidwater", 1)],
                 [(EffectKind.RESIST_FIRE.value, 50.0, 300.0, "refresh")],
                 10, 15.0, "Fire Resistance Potion", 1, False),
                ("rec_alch_invisibility", "Invisibility Potion", "Grants temporary invisibility", RecipeType.ALCHEMY.value, CraftingStation.ALCHEMY_BENCH.value,
                 [("ing_herbmoonleaf", 2), ("ing_magicalsoul", 1), ("ing_liquidwater", 1)],
                 [(EffectKind.INVISIBILITY.value, 100.0, 30.0, "no_stack")],
                 25, 30.0, "Invisibility Potion", 1, False),
                ("rec_alch_greater_heal", "Greater Healing Potion", "Powerful healing", RecipeType.ALCHEMY.value, CraftingStation.ALCHEMY_BENCH.value,
                 [("ing_herbmoonleaf", 2), ("ing_herbfirebloom", 1), ("ing_liquidwater", 1)],
                 [(EffectKind.HEAL.value, 150.0, 0.0, "refresh"), (EffectKind.REGENERATION.value, 15.0, 300.0, "refresh")],
                 15, 20.0, "Greater Healing Potion", 1, False),
            ]

            # Recipes - Brewing
            recipes_brewing = [
                ("rec_brew_ale", "Craft Ale", "Refreshing drink", RecipeType.BREWING.value, CraftingStation.BREWING_BARREL.value,
                 [("ing_grainwheat", 3), ("ing_fruitapple", 1), ("ing_liquidwater", 2)],
                 [(EffectKind.STAMINA_RESTORE.value, 30.0, 0.0, "refresh"), (EffectKind.BUFF_SPEED.value, 5.0, 120.0, "refresh")],
                 1, 60.0, "Craft Ale", 1, True),
                ("rec_brew_elixir", "Mana Elixir", "Powerful mana restoration", RecipeType.BREWING.value, CraftingStation.BREWING_BARREL.value,
                 [("ing_herbmoonleaf", 2), ("ing_magicalsoul", 1), ("ing_liquidwater", 2)],
                 [(EffectKind.MANA_RESTORE.value, 100.0, 0.0, "refresh"), (EffectKind.FORTIFY_MANA.value, 30.0, 600.0, "refresh")],
                 15, 120.0, "Mana Elixir", 1, False),
            ]

            all_recipes = recipes_cooking + recipes_alchemy + recipes_brewing
            for rec_id, name, desc, rtype, station, ings, effects, skill_req, craft_time, output_name, output_qty, learned in all_recipes:
                recipe = RecipeDefinition(
                    recipe_id=rec_id, name=name, description=desc,
                    recipe_type=rtype, required_station=station,
                    ingredients=[RecipeIngredient(ingredient_id=i[0], quantity=i[1]) for i in ings],
                    effects=[RecipeEffect(effect_kind=e[0], magnitude=e[1], duration_seconds=e[2], stacking_rule=e[3]) for e in effects],
                    required_skill_level=skill_req,
                    base_craft_time=craft_time,
                    output_item_name=output_name,
                    output_quantity=output_qty,
                    is_learned_by_default=learned,
                )
                self._recipes[rec_id] = recipe

            # Stations
            stations = [
                ("station_campfire_01", CraftingStation.CAMPFIRE.value, "Starter Campfire", 0, 0, 0, True, "", 1, 1.0, 0.0),
                ("station_kitchen_01", CraftingStation.KITCHEN.value, "Village Kitchen", 50, 0, 50, True, "", 1, 1.2, 0.05),
                ("station_alchemy_01", CraftingStation.ALCHEMY_BENCH.value, "Alchemy Bench", 100, 0, 100, True, "", 1, 1.0, 0.0),
                ("station_brewing_01", CraftingStation.BREWING_BARREL.value, "Brewing Barrel", 150, 0, 150, True, "", 1, 1.0, 0.0),
                ("station_cauldron_01", CraftingStation.CAULDRON.value, "Witch's Cauldron", -50, 0, -50, False, "player_starter", 2, 1.3, 0.1),
            ]
            for sid, stype, name, x, y, z, is_pub, owner, lvl, spd, qual in stations:
                station = CraftingStationInstance(
                    station_id=sid, station_type=stype, name=name,
                    location_x=x, location_y=y, location_z=z,
                    is_public=is_pub, owner_player_id=owner,
                    upgrade_level=lvl, craft_speed_multiplier=spd, quality_bonus=qual,
                )
                self._stations[sid] = station

            # Crafting skill for starter player
            skill = CraftingSkill(
                player_id="player_starter",
                cooking_level=8,
                cooking_xp=120,
                alchemy_level=5,
                alchemy_xp=80,
                brewing_level=3,
                brewing_xp=40,
                total_crafts=15,
                perfect_crafts=3,
                masterwork_crafts=0,
                discovered_recipe_ids=["rec_cook_stew", "rec_cook_roast", "rec_alch_heal_potion", "rec_alch_mana_potion"],
            )
            self._crafting_skills["player_starter"] = skill

            # Seeded crafted item
            item1 = CraftedItem(
                item_id="item_starter_heal_potion_01",
                recipe_id="rec_alch_heal_potion",
                crafter_player_id="player_starter",
                name="Healing Potion",
                quality=CraftQuality.GOOD.value,
                effects=[RecipeEffect(effect_kind=EffectKind.HEAL.value, magnitude=55.0, duration_seconds=0.0, stacking_rule="refresh")],
                potency_multiplier=1.1,
            )
            self._crafted_items[item1.item_id] = item1
            self._player_items.setdefault("player_starter", []).append(item1.item_id)

            # Seeded discovery
            disc1 = RecipeDiscovery(
                discovery_id="disc_starter_01",
                player_id="player_starter",
                recipe_id="rec_alch_heal_potion",
                discovery_method="npc",
                xp_gained=50,
            )
            self._discoveries[disc1.discovery_id] = disc1
            self._player_discoveries.setdefault("player_starter", []).append(disc1.discovery_id)

            # Seeded active effect
            eff1 = ActiveEffect(
                effect_id="eff_starter_01",
                player_id="player_starter",
                effect_kind=EffectKind.BUFF_ATTACK.value,
                magnitude=15.0,
                remaining_duration=500.0,
                total_duration=600.0,
                source_item_id="item_starter_heal_potion_01",
                stacking_rule="refresh",
            )
            self._active_effects.setdefault("player_starter", []).append(eff1)

            # Update stats
            self._stats.total_ingredients = len(self._ingredients)
            self._stats.total_recipes = len(self._recipes)
            self._stats.total_stations = len(self._stations)
            self._stats.total_crafted_items = len(self._crafted_items)
            self._stats.total_active_effects = 1
            self._stats.total_discoveries = len(self._discoveries)
            self._stats.total_perfect_crafts = 3

            self._initialized = True

    def _emit(self, kind: str, **kwargs: Any) -> None:
        self._event_counter += 1
        event = CookingAlchemyEvent(
            event_id=f"caevt_{self._event_counter:08d}",
            kind=kind,
            timestamp=_now(),
            **kwargs,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _get_or_create_skill(self, player_id: str) -> CraftingSkill:
        if player_id not in self._crafting_skills:
            self._crafting_skills[player_id] = CraftingSkill(player_id=player_id)
        return self._crafting_skills[player_id]

    # ------------------------------------------------------------------
    # Ingredients
    # ------------------------------------------------------------------

    def register_ingredient(
        self, ingredient_id: str, name: str, description: str = "",
        category: str = IngredientCategory.HERB.value, rarity: str = "common",
        base_value: float = 1.0, gathering_skill_required: int = 0,
        gathering_location: str = "", is_magical: bool = False, potency: float = 1.0,
    ) -> Tuple[bool, str, Optional[IngredientDefinition]]:
        if ingredient_id in self._ingredients:
            return False, "already_exists", None
        ing = IngredientDefinition(
            ingredient_id=ingredient_id, name=name, description=description,
            category=category, rarity=rarity, base_value=base_value,
            gathering_skill_required=gathering_skill_required,
            gathering_location=gathering_location,
            is_magical=is_magical, potency=potency,
        )
        self._ingredients[ingredient_id] = ing
        self._stats.total_ingredients = len(self._ingredients)
        self._emit(CookingAlchemyEventKind.INGREDIENT_REGISTERED.value,
                   ingredient_id=ingredient_id,
                   description=f"Ingredient registered: {ingredient_id}")
        return True, "registered", ing

    def remove_ingredient(self, ingredient_id: str) -> Tuple[bool, str]:
        if ingredient_id not in self._ingredients:
            return False, "not_found"
        del self._ingredients[ingredient_id]
        self._stats.total_ingredients = len(self._ingredients)
        self._emit(CookingAlchemyEventKind.INGREDIENT_REMOVED.value,
                   ingredient_id=ingredient_id,
                   description=f"Ingredient removed: {ingredient_id}")
        return True, "removed"

    def get_ingredient(self, ingredient_id: str) -> Optional[IngredientDefinition]:
        return self._ingredients.get(ingredient_id)

    def list_ingredients(self, category: str = "") -> List[IngredientDefinition]:
        if category:
            return [i for i in self._ingredients.values() if i.category == category]
        return list(self._ingredients.values())

    # ------------------------------------------------------------------
    # Recipes
    # ------------------------------------------------------------------

    def register_recipe(
        self, recipe_id: str, name: str, description: str = "",
        recipe_type: str = RecipeType.COOKING.value,
        required_station: str = CraftingStation.CAMPFIRE.value,
        ingredients: Optional[List[Dict[str, Any]]] = None,
        effects: Optional[List[Dict[str, Any]]] = None,
        required_skill_level: int = 1, base_craft_time: float = 10.0,
        output_item_name: str = "", output_quantity: int = 1,
        is_learned_by_default: bool = False,
    ) -> Tuple[bool, str, Optional[RecipeDefinition]]:
        if recipe_id in self._recipes:
            return False, "already_exists", None
        recipe = RecipeDefinition(
            recipe_id=recipe_id, name=name, description=description,
            recipe_type=recipe_type, required_station=required_station,
            ingredients=[RecipeIngredient(**i) for i in (ingredients or [])],
            effects=[RecipeEffect(**e) for e in (effects or [])],
            required_skill_level=required_skill_level,
            base_craft_time=base_craft_time,
            output_item_name=output_item_name or name,
            output_quantity=output_quantity,
            is_learned_by_default=is_learned_by_default,
        )
        self._recipes[recipe_id] = recipe
        self._stats.total_recipes = len(self._recipes)
        self._emit(CookingAlchemyEventKind.RECIPE_REGISTERED.value,
                   recipe_id=recipe_id,
                   description=f"Recipe registered: {recipe_id}")
        return True, "registered", recipe

    def remove_recipe(self, recipe_id: str) -> Tuple[bool, str]:
        if recipe_id not in self._recipes:
            return False, "not_found"
        del self._recipes[recipe_id]
        self._stats.total_recipes = len(self._recipes)
        self._emit(CookingAlchemyEventKind.RECIPE_REMOVED.value,
                   recipe_id=recipe_id,
                   description=f"Recipe removed: {recipe_id}")
        return True, "removed"

    def get_recipe(self, recipe_id: str) -> Optional[RecipeDefinition]:
        return self._recipes.get(recipe_id)

    def list_recipes(self, recipe_type: str = "") -> List[RecipeDefinition]:
        if recipe_type:
            return [r for r in self._recipes.values() if r.recipe_type == recipe_type]
        return list(self._recipes.values())

    # ------------------------------------------------------------------
    # Stations
    # ------------------------------------------------------------------

    def register_station(
        self, station_id: str, station_type: str = CraftingStation.CAMPFIRE.value,
        name: str = "", location_x: float = 0.0, location_y: float = 0.0, location_z: float = 0.0,
        is_public: bool = True, owner_player_id: str = "",
        upgrade_level: int = 1, craft_speed_multiplier: float = 1.0, quality_bonus: float = 0.0,
    ) -> Tuple[bool, str, Optional[CraftingStationInstance]]:
        if station_id in self._stations:
            return False, "already_exists", None
        station = CraftingStationInstance(
            station_id=station_id, station_type=station_type, name=name,
            location_x=location_x, location_y=location_y, location_z=location_z,
            is_public=is_public, owner_player_id=owner_player_id,
            upgrade_level=upgrade_level,
            craft_speed_multiplier=craft_speed_multiplier,
            quality_bonus=quality_bonus,
        )
        self._stations[station_id] = station
        self._stats.total_stations = len(self._stations)
        self._emit(CookingAlchemyEventKind.STATION_REGISTERED.value,
                   station_id=station_id,
                   description=f"Station registered: {station_id}")
        return True, "registered", station

    def remove_station(self, station_id: str) -> Tuple[bool, str]:
        if station_id not in self._stations:
            return False, "not_found"
        del self._stations[station_id]
        self._stats.total_stations = len(self._stations)
        self._emit(CookingAlchemyEventKind.STATION_REMOVED.value,
                   station_id=station_id,
                   description=f"Station removed: {station_id}")
        return True, "removed"

    def get_station(self, station_id: str) -> Optional[CraftingStationInstance]:
        return self._stations.get(station_id)

    def list_stations(self, station_type: str = "") -> List[CraftingStationInstance]:
        if station_type:
            return [s for s in self._stations.values() if s.station_type == station_type]
        return list(self._stations.values())

    # ------------------------------------------------------------------
    # Crafting
    # ------------------------------------------------------------------

    def craft_item(
        self, recipe_id: str, player_id: str, station_id: str = "",
    ) -> Tuple[bool, str, Optional[CraftedItem], int]:
        """Craft an item. Returns (ok, msg, item, xp_gained)."""
        recipe = self._recipes.get(recipe_id)
        if recipe is None:
            return False, "recipe_not_found", None, 0

        skill = self._get_or_create_skill(player_id)
        skill_level = skill.get_skill_level(recipe.recipe_type)
        if skill_level < recipe.required_skill_level:
            return False, "skill_too_low", None, 0

        station = None
        if station_id:
            station = self._stations.get(station_id)
            if station is None:
                return False, "station_not_found", None, 0
            if station.station_type != recipe.required_station:
                return False, "wrong_station_type", None, 0
            if not station.is_public and station.owner_player_id != player_id:
                return False, "station_not_accessible", None, 0

        # Determine quality
        quality = self._determine_quality(skill_level, recipe.required_skill_level, station)

        if quality == CraftQuality.FAILED.value:
            skill.total_crafts += 1
            self._stats.total_failed_crafts += 1
            xp = self._config.base_craft_xp // 2
            skill.add_xp(recipe.recipe_type, xp)
            self._emit(CookingAlchemyEventKind.ITEM_CRAFTED.value,
                       recipe_id=recipe_id, player_id=player_id,
                       description=f"Craft failed: {recipe.name}")
            return True, "failed", None, xp

        # Calculate effect multipliers
        quality_multiplier = self._quality_multiplier(quality)
        station_bonus = station.quality_bonus if station else 0.0
        potency_mult = quality_multiplier + station_bonus
        duration_mult = 1.0 + (potency_mult - 1.0) * 0.5

        item_id = _new_id("item")
        crafted = CraftedItem(
            item_id=item_id,
            recipe_id=recipe_id,
            crafter_player_id=player_id,
            name=recipe.output_item_name or recipe.name,
            quality=quality,
            effects=[RecipeEffect(
                effect_kind=e.effect_kind,
                magnitude=round(e.magnitude * potency_mult, 2),
                duration_seconds=round(e.duration_seconds * duration_mult, 2),
                stacking_rule=e.stacking_rule,
            ) for e in recipe.effects],
            potency_multiplier=round(potency_mult, 3),
            duration_multiplier=round(duration_mult, 3),
        )
        self._crafted_items[item_id] = crafted
        self._player_items.setdefault(player_id, []).append(item_id)
        self._stats.total_crafted_items = len(self._crafted_items)

        skill.total_crafts += 1
        if quality == CraftQuality.PERFECT.value:
            skill.perfect_crafts += 1
            self._stats.total_perfect_crafts += 1
        elif quality == CraftQuality.MASTERWORK.value:
            skill.masterwork_crafts += 1
            self._stats.total_masterwork_crafts += 1

        xp = self._config.base_craft_xp
        if quality == CraftQuality.PERFECT.value:
            xp += self._config.perfect_craft_xp_bonus
        elif quality == CraftQuality.MASTERWORK.value:
            xp += self._config.masterwork_craft_xp_bonus
        levels_gained = skill.add_xp(recipe.recipe_type, xp)

        self._emit(CookingAlchemyEventKind.ITEM_CRAFTED.value,
                   recipe_id=recipe_id, player_id=player_id, item_id=item_id,
                   description=f"Crafted: {crafted.name} ({quality})")

        if levels_gained > 0:
            self._emit(CookingAlchemyEventKind.SKILL_LEVELED.value,
                       player_id=player_id,
                       description=f"Skill leveled up {levels_gained} times")

        return True, "crafted", crafted, xp

    def _determine_quality(self, skill_level: int, required_level: int, station: Optional[CraftingStationInstance]) -> str:
        import random
        diff = skill_level - required_level
        station_bonus = station.quality_bonus if station else 0.0
        base_chance = 0.5 + (diff * 0.05) + station_bonus
        roll = random.random()
        if roll < base_chance + 0.15:
            if roll < 0.02 + (station_bonus * 0.1):
                return CraftQuality.MASTERWORK.value
            elif roll < 0.08 + (station_bonus * 0.05):
                return CraftQuality.PERFECT.value
            elif roll < 0.2 + (diff * 0.03):
                return CraftQuality.EXCELLENT.value
            else:
                return CraftQuality.GOOD.value
        elif roll < 0.9:
            return CraftQuality.COMMON.value
        elif roll < 0.97:
            return CraftQuality.POOR.value
        return CraftQuality.FAILED.value

    def _quality_multiplier(self, quality: str) -> float:
        multipliers = {
            CraftQuality.FAILED.value: 0.0,
            CraftQuality.POOR.value: 0.7,
            CraftQuality.COMMON.value: 1.0,
            CraftQuality.GOOD.value: 1.15,
            CraftQuality.EXCELLENT.value: 1.3,
            CraftQuality.PERFECT.value: 1.5,
            CraftQuality.MASTERWORK.value: 2.0,
        }
        return multipliers.get(quality, 1.0)

    def get_crafted_item(self, item_id: str) -> Optional[CraftedItem]:
        return self._crafted_items.get(item_id)

    def list_crafted_items(self, player_id: str = "") -> List[CraftedItem]:
        if player_id:
            ids = self._player_items.get(player_id, [])
            return [self._crafted_items[iid] for iid in ids if iid in self._crafted_items]
        return list(self._crafted_items.values())

    # ------------------------------------------------------------------
    # Effects
    # ------------------------------------------------------------------

    def consume_item(self, item_id: str, player_id: str) -> Tuple[bool, str, List[ActiveEffect]]:
        """Consume a crafted item and apply its effects."""
        item = self._crafted_items.get(item_id)
        if item is None:
            return False, "item_not_found", []
        if item.crafter_player_id != player_id and player_id not in self._player_items:
            return False, "not_owner", []

        effects_applied: List[ActiveEffect] = []
        for eff in item.effects:
            active = self._apply_effect_internal(
                player_id, eff.effect_kind, eff.magnitude,
                eff.duration_seconds, item.item_id, eff.stacking_rule,
            )
            if active:
                effects_applied.append(active)

        # Remove consumed item
        del self._crafted_items[item_id]
        if player_id in self._player_items:
            try:
                self._player_items[player_id].remove(item_id)
            except ValueError:
                pass
        self._stats.total_crafted_items = len(self._crafted_items)

        self._emit(CookingAlchemyEventKind.EFFECT_APPLIED.value,
                   item_id=item_id, player_id=player_id,
                   description=f"Item consumed: {item.name}")
        return True, "consumed", effects_applied

    def _apply_effect_internal(
        self, player_id: str, effect_kind: str, magnitude: float,
        duration: float, source_item_id: str, stacking_rule: str,
    ) -> Optional[ActiveEffect]:
        player_effects = self._active_effects.setdefault(player_id, [])

        # Check stacking
        existing = [e for e in player_effects if e.effect_kind == effect_kind]
        if existing:
            if stacking_rule == "no_stack":
                return None
            elif stacking_rule == "refresh":
                for e in existing:
                    e.remaining_duration = duration
                    e.total_duration = duration
                    e.magnitude = max(e.magnitude, magnitude)
                return existing[0]
            elif stacking_rule == "stack":
                e = existing[0]
                e.stacks += 1
                e.magnitude += magnitude * 0.5
                e.remaining_duration = max(e.remaining_duration, duration)
                return e

        effect_id = _new_id("eff")
        active = ActiveEffect(
            effect_id=effect_id,
            player_id=player_id,
            effect_kind=effect_kind,
            magnitude=magnitude,
            remaining_duration=duration,
            total_duration=duration,
            source_item_id=source_item_id,
            stacking_rule=stacking_rule,
        )
        player_effects.append(active)

        # Enforce max effects
        if len(player_effects) > self._config.max_active_effects_per_player:
            player_effects.pop(0)

        self._stats.total_active_effects = sum(len(v) for v in self._active_effects.values())
        return active

    def apply_effect(
        self, player_id: str, effect_kind: str, magnitude: float,
        duration: float = 0.0, source_item_id: str = "", stacking_rule: str = "refresh",
    ) -> Tuple[bool, str, Optional[ActiveEffect]]:
        active = self._apply_effect_internal(
            player_id, effect_kind, magnitude, duration, source_item_id, stacking_rule,
        )
        if active:
            self._emit(CookingAlchemyEventKind.EFFECT_APPLIED.value,
                       player_id=player_id,
                       description=f"Effect applied: {effect_kind}")
            return True, "applied", active
        return False, "not_applied", None

    def dispel_effect(self, player_id: str, effect_kind: str = "") -> Tuple[bool, str, int]:
        player_effects = self._active_effects.get(player_id, [])
        if not player_effects:
            return False, "no_effects", 0
        if effect_kind:
            before = len(player_effects)
            self._active_effects[player_id] = [e for e in player_effects if e.effect_kind != effect_kind]
            dispelled = before - len(self._active_effects[player_id])
        else:
            dispelled = len(player_effects)
            self._active_effects[player_id] = []
        self._stats.total_active_effects = sum(len(v) for v in self._active_effects.values())
        self._emit(CookingAlchemyEventKind.EFFECT_DISPELLED.value,
                   player_id=player_id,
                   description=f"Effects dispelled: {dispelled}")
        return True, "dispelled", dispelled

    def get_active_effects(self, player_id: str) -> List[ActiveEffect]:
        return [e for e in self._active_effects.get(player_id, []) if not e.is_expired]

    # ------------------------------------------------------------------
    # Skill
    # ------------------------------------------------------------------

    def get_crafting_skill(self, player_id: str) -> Optional[CraftingSkill]:
        return self._crafting_skills.get(player_id)

    def level_up_skill(self, player_id: str, recipe_type: str) -> Tuple[bool, str, Optional[CraftingSkill]]:
        skill = self._get_or_create_skill(player_id)
        levels_gained = skill.add_xp(recipe_type, skill.get_skill_level(recipe_type) * 100)
        if levels_gained > 0:
            self._emit(CookingAlchemyEventKind.SKILL_LEVELED.value,
                       player_id=player_id,
                       description=f"Skill leveled: {recipe_type}")
            return True, "leveled", skill
        return False, "no_level", skill

    def get_skill_rank(self, player_id: str, recipe_type: str) -> str:
        skill = self._crafting_skills.get(player_id)
        if skill is None:
            return "novice"
        return skill.get_rank(recipe_type)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_recipe(
        self, player_id: str, recipe_id: str, discovery_method: str = "experiment",
    ) -> Tuple[bool, str, Optional[RecipeDiscovery]]:
        recipe = self._recipes.get(recipe_id)
        if recipe is None:
            return False, "recipe_not_found", None
        skill = self._get_or_create_skill(player_id)
        if recipe_id in skill.discovered_recipe_ids:
            return False, "already_discovered", None
        skill.discovered_recipe_ids.append(recipe_id)
        discovery_id = _new_id("disc")
        discovery = RecipeDiscovery(
            discovery_id=discovery_id,
            player_id=player_id,
            recipe_id=recipe_id,
            discovery_method=discovery_method,
            xp_gained=self._config.discovery_xp_base,
        )
        self._discoveries[discovery_id] = discovery
        self._player_discoveries.setdefault(player_id, []).append(discovery_id)
        self._stats.total_discoveries = len(self._discoveries)
        skill.add_xp(recipe.recipe_type, self._config.discovery_xp_base)
        self._emit(CookingAlchemyEventKind.RECIPE_DISCOVERED.value,
                   player_id=player_id, recipe_id=recipe_id,
                   description=f"Recipe discovered: {recipe.name}")
        return True, "discovered", discovery

    def get_discoveries(self, player_id: str) -> List[RecipeDiscovery]:
        ids = self._player_discoveries.get(player_id, [])
        return [self._discoveries[did] for did in ids if did in self._discoveries]

    def list_discoveries(self) -> List[RecipeDiscovery]:
        return list(self._discoveries.values())

    # ------------------------------------------------------------------
    # Suggestions & Substitutes
    # ------------------------------------------------------------------

    def get_recipe_suggestions(self, player_id: str, available_ingredient_ids: List[str]) -> List[RecipeDefinition]:
        """Suggest recipes the player can craft with available ingredients."""
        skill = self._crafting_skills.get(player_id)
        suggestions: List[RecipeDefinition] = []
        available_set = set(available_ingredient_ids)
        for recipe in self._recipes.values():
            has_all = all(ri.ingredient_id in available_set for ri in recipe.ingredients)
            if not has_all:
                continue
            if skill:
                skill_level = skill.get_skill_level(recipe.recipe_type)
                if skill_level < recipe.required_skill_level:
                    continue
                if recipe_id_not_learned(recipe, skill):
                    continue
            suggestions.append(recipe)
        return suggestions

    def get_ingredient_substitutes(self, ingredient_id: str) -> List[IngredientDefinition]:
        """Find ingredients in the same category as potential substitutes."""
        ing = self._ingredients.get(ingredient_id)
        if ing is None:
            return []
        return [i for i in self._ingredients.values()
                if i.category == ing.category and i.ingredient_id != ingredient_id]

    # ------------------------------------------------------------------
    # Tick / Config / Status
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        self._tick_count += 1
        expired_count = 0
        for player_id, effects in self._active_effects.items():
            remaining = []
            for e in effects:
                if e.remaining_duration > 0:
                    e.remaining_duration -= self._config.effect_tick_interval
                    if e.remaining_duration > 0:
                        remaining.append(e)
                    else:
                        expired_count += 1
                else:
                    remaining.append(e)
            self._active_effects[player_id] = remaining
        if expired_count > 0:
            self._stats.total_active_effects = sum(len(v) for v in self._active_effects.values())
            self._emit(CookingAlchemyEventKind.EFFECT_EXPIRED.value,
                       description=f"Effects expired: {expired_count}")
        self._stats.tick_count = self._tick_count
        self._emit(CookingAlchemyEventKind.TICK.value,
                   description=f"Tick #{self._tick_count}")
        return {
            "tick_count": self._tick_count,
            "expired_effects": expired_count,
            "total_active_effects": self._stats.total_active_effects,
        }

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, CookingAlchemyConfig]:
        if not isinstance(config, dict):
            return False, "invalid_config", self._config
        for key, value in config.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self._emit(CookingAlchemyEventKind.CONFIG_UPDATED.value,
                   description="Config updated")
        return True, "updated", self._config

    def get_config(self) -> CookingAlchemyConfig:
        return self._config

    def list_events(self, limit: int = 100, kind: str = "") -> List[CookingAlchemyEvent]:
        events = self._events if not kind else [e for e in self._events if e.kind == kind]
        if limit > 0:
            events = events[-limit:]
        return list(events)

    def get_stats(self) -> CookingAlchemyStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_ingredients": len(self._ingredients),
            "total_recipes": len(self._recipes),
            "total_stations": len(self._stations),
            "total_crafted_items": len(self._crafted_items),
            "total_active_effects": sum(len(v) for v in self._active_effects.values()),
            "total_discoveries": len(self._discoveries),
            "total_perfect_crafts": self._stats.total_perfect_crafts,
            "total_masterwork_crafts": self._stats.total_masterwork_crafts,
            "total_failed_crafts": self._stats.total_failed_crafts,
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> CookingAlchemySnapshot:
        return CookingAlchemySnapshot(
            ingredients=[i.to_dict() for i in self._ingredients.values()],
            recipes=[r.to_dict() for r in self._recipes.values()],
            stations=[s.to_dict() for s in self._stations.values()],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Tuple[bool, str]:
        with self._init_lock:
            self._ingredients.clear()
            self._recipes.clear()
            self._stations.clear()
            self._crafted_items.clear()
            self._player_items.clear()
            self._active_effects.clear()
            self._crafting_skills.clear()
            self._discoveries.clear()
            self._player_discoveries.clear()
            self._events.clear()
            self._stats = CookingAlchemyStats()
            self._config = CookingAlchemyConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
            self._emit(CookingAlchemyEventKind.RESET.value,
                       description="System reset")
        return True, "reset"


def recipe_id_not_learned(recipe: RecipeDefinition, skill: CraftingSkill) -> bool:
    """Check if a recipe is not learned by the player."""
    if recipe.is_learned_by_default:
        return False
    return recipe.recipe_id not in skill.discovered_recipe_ids


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_cooking_alchemy_system() -> CookingAlchemySystem:
    return CookingAlchemySystem.get_instance()
