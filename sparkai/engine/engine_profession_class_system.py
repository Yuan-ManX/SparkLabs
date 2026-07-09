"""
SparkLabs Engine - Profession & Class System

Provides character class definitions with abilities, talent trees,
class switching, profession mastery, and crafting profession specializations.
Designed as a self-contained singleton system with seed data for
immediate integration testing.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


_MAX_CLASSES = 100
_MAX_ABILITIES = 500
_MAX_TALENTS = 500
_MAX_TALENT_NODES = 1000
_MAX_PLAYER_CLASSES = 2000
_MAX_PLAYER_ABILITIES = 5000
_MAX_PLAYER_TALENTS = 5000
_MAX_PROFESSIONS = 100
_MAX_RECIPES = 1000
_MAX_PLAYER_PROFESSIONS = 5000
_MAX_CRAFT_HISTORY = 5000
_MAX_EVENTS = 5000

# XP curves
def _xp_for_level(level: int) -> int:
    # Each level requires progressively more XP
    return int(100 * (level ** 1.5)) + (level - 1) * 50


def _level_from_xp(xp: int) -> Tuple[int, int]:
    """Return (level, xp_into_next_level) from total xp."""
    level = 1
    remaining = xp
    while True:
        needed = _xp_for_level(level)
        if remaining < needed:
            return level, remaining
        remaining -= needed
        level += 1
        if level > 200:
            return 200, 0


# Class stat weights for computing base stats from class
CLASS_BASE_STATS: Dict[str, Dict[str, float]] = {
    "warrior": {"strength": 20.0, "agility": 10.0, "intellect": 5.0, "vitality": 18.0, "spirit": 8.0},
    "mage": {"strength": 5.0, "agility": 8.0, "intellect": 22.0, "vitality": 8.0, "spirit": 14.0},
    "rogue": {"strength": 12.0, "agility": 22.0, "intellect": 8.0, "vitality": 10.0, "spirit": 8.0},
    "archer": {"strength": 10.0, "agility": 20.0, "intellect": 8.0, "vitality": 10.0, "spirit": 10.0},
    "cleric": {"strength": 8.0, "agility": 8.0, "intellect": 14.0, "vitality": 12.0, "spirit": 22.0},
    "paladin": {"strength": 16.0, "agility": 8.0, "intellect": 10.0, "vitality": 16.0, "spirit": 14.0},
    "berserker": {"strength": 24.0, "agility": 12.0, "intellect": 4.0, "vitality": 14.0, "spirit": 6.0},
    "necromancer": {"strength": 6.0, "agility": 6.0, "intellect": 20.0, "vitality": 8.0, "spirit": 16.0},
}


def _evict_fifo_list(items: List[Any], max_size: int) -> None:
    while len(items) > max_size:
        items.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for field_name in obj.__dataclass_fields__:
            val = getattr(obj, field_name)
            if hasattr(val, "__dataclass_fields__"):
                result[field_name] = _dataclass_to_dict(val)
            elif hasattr(val, "to_dict") and callable(val.to_dict):
                result[field_name] = val.to_dict()
            elif isinstance(val, list):
                result[field_name] = [_dataclass_to_dict(item) for item in val]
            elif isinstance(val, tuple):
                result[field_name] = [_dataclass_to_dict(item) for item in val]
            elif isinstance(val, dict):
                result[field_name] = {k: _dataclass_to_dict(v) for k, v in val.items()}
            else:
                result[field_name] = val
        return result
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ClassArchetype(str, Enum):
    TANK = "tank"
    DPS_MELEE = "dps_melee"
    DPS_RANGED = "dps_ranged"
    HEALER = "healer"
    SUPPORT = "support"
    HYBRID = "hybrid"


class ClassResource(str, Enum):
    RAGE = "rage"
    MANA = "mana"
    ENERGY = "energy"
    FOCUS = "focus"
    FAITH = "faith"
    RUNIC_POWER = "runic_power"
    SOUL_SHARD = "soul_shard"


class AbilityType(str, Enum):
    ACTIVE = "active"
    PASSIVE = "passive"
    TOGGLE = "toggle"


class AbilitySchool(str, Enum):
    PHYSICAL = "physical"
    FIRE = "fire"
    FROST = "frost"
    ARCANE = "arcane"
    NATURE = "nature"
    SHADOW = "shadow"
    HOLY = "holy"
    LIGHTNING = "lightning"


class AbilityCategory(str, Enum):
    BASIC_ATTACK = "basic_attack"
    SKILL = "skill"
    ULTIMATE = "ultimate"
    BUFF = "buff"
    DEBUFF = "debuff"
    HEAL = "heal"
    CROWD_CONTROL = "crowd_control"
    MOBILITY = "mobility"
    DEFENSIVE = "defensive"
    UTILITY = "utility"


class TalentNodeType(str, Enum):
    STAT = "stat"
    ABILITY = "ability"
    MASTERY = "mastery"
    KEYSTONE = "keystone"


class PlayerClassStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"


class ProfessionType(str, Enum):
    GATHERING = "gathering"
    CRAFTING = "crafting"
    SERVICE = "service"


class ProfessionCategory(str, Enum):
    MINING = "mining"
    HERBALISM = "herbalism"
    SKINNING = "skinning"
    FISHING = "fishing"
    BLACKSMITHING = "blacksmithing"
    ALCHEMY = "alchemy"
    ENCHANTING = "enchanting"
    ENGINEERING = "engineering"
    TAILORING = "tailoring"
    LEATHERWORKING = "leatherworking"
    JEWELCRAFTING = "jewelcrafting"
    INSCRIPTION = "inscription"
    COOKING = "cooking"
    FIRST_AID = "first_aid"


class RecipeRarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class RecipeStatus(str, Enum):
    KNOWN = "known"
    LEARNED = "learned"
    FORGOTTEN = "forgotten"


class CraftResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    CRITICAL = "critical"
    DISCOVERY = "discovery"


class ProfessionEventKind(str, Enum):
    CLASS_REGISTERED = "class_registered"
    CLASS_REMOVED = "class_removed"
    CLASS_UNLOCKED = "class_unlocked"
    PLAYER_CLASS_SET = "player_class_set"
    PLAYER_CLASS_SWITCHED = "player_class_switched"
    ABILITY_LEARNED = "ability_learned"
    ABILITY_FORGOTTEN = "ability_forgotten"
    ABILITY_USED = "ability_used"
    TALENT_LEARNED = "talent_learned"
    TALENT_RESET = "talent_reset"
    TALENT_TREE_RESET = "talent_tree_reset"
    PROFESSION_REGISTERED = "profession_registered"
    RECIPE_REGISTERED = "recipe_registered"
    PROFESSION_LEARNED = "profession_learned"
    RECIPE_LEARNED = "recipe_learned"
    CRAFT_PERFORMED = "craft_performed"
    PROFESSION_LEVEL_UP = "profession_level_up"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ClassAbility:
    ability_id: str
    name: str
    description: str = ""
    ability_type: str = AbilityType.ACTIVE.value
    school: str = AbilitySchool.PHYSICAL.value
    category: str = AbilityCategory.SKILL.value
    class_id: str = ""
    required_level: int = 1
    cooldown_seconds: float = 5.0
    resource_cost: float = 20.0
    resource_type: str = ClassResource.MANA.value
    cast_time: float = 0.0
    range_value: float = 5.0
    damage_base: float = 0.0
    damage_scaling: float = 0.0
    healing_base: float = 0.0
    healing_scaling: float = 0.0
    duration_seconds: float = 0.0
    buff_stats: Dict[str, float] = field(default_factory=dict)
    debuff_stats: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TalentNode:
    node_id: str
    name: str
    description: str = ""
    node_type: str = TalentNodeType.STAT.value
    tree_id: str = ""
    max_rank: int = 1
    current_rank: int = 0
    required_points: int = 1
    prerequisite_node_ids: List[str] = field(default_factory=list)
    stat_bonuses: Dict[str, float] = field(default_factory=dict)
    granted_ability_id: str = ""
    position_x: int = 0
    position_y: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TalentTree:
    tree_id: str
    name: str
    description: str = ""
    class_id: str = ""
    max_points: int = 30
    spent_points: int = 0
    nodes: List[TalentNode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ClassDefinition:
    class_id: str
    name: str
    description: str = ""
    archetype: str = ClassArchetype.DPS_MELEE.value
    resource_type: str = ClassResource.MANA.value
    max_resource: float = 100.0
    resource_regen: float = 5.0
    base_stats: Dict[str, float] = field(default_factory=dict)
    growth_stats: Dict[str, float] = field(default_factory=dict)
    allowed_weapon_types: List[str] = field(default_factory=list)
    allowed_armor_types: List[str] = field(default_factory=list)
    ability_ids: List[str] = field(default_factory=list)
    talent_tree_ids: List[str] = field(default_factory=list)
    icon: str = ""
    color: str = "#FFFFFF"
    difficulty: str = "normal"
    unlocked: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerClassState:
    """Represents a player's progression with a specific class."""
    state_id: str
    player_id: str
    class_id: str
    status: str = PlayerClassStatus.INACTIVE.value
    level: int = 1
    experience: int = 0
    current_resource: float = 100.0
    max_resource: float = 100.0
    learned_abilities: List[str] = field(default_factory=list)
    equipped_abilities: List[str] = field(default_factory=list)
    max_equipped: int = 8
    talent_spent: Dict[str, int] = field(default_factory=dict)
    talent_points_available: int = 0
    total_talent_points: int = 0
    playtime_seconds: float = 0.0
    last_used: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RecipeIngredient:
    item_id: str
    item_name: str = ""
    quantity: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RecipeOutput:
    item_id: str
    item_name: str = ""
    quantity: int = 1
    chance: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Recipe:
    recipe_id: str
    name: str
    description: str = ""
    profession_id: str = ""
    category: str = ProfessionCategory.BLACKSMITHING.value
    required_level: int = 1
    rarity: str = RecipeRarity.COMMON.value
    ingredients: List[RecipeIngredient] = field(default_factory=list)
    outputs: List[RecipeOutput] = field(default_factory=list)
    craft_time_seconds: float = 5.0
    success_chance: float = 0.95
    critical_chance: float = 0.05
    discovery_chance: float = 0.0
    skill_xp: int = 10
    station_required: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProfessionDefinition:
    profession_id: str
    name: str
    description: str = ""
    profession_type: str = ProfessionType.CRAFTING.value
    category: str = ProfessionCategory.BLACKSMITHING.value
    max_level: int = 100
    parent_profession_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerProfession:
    pp_id: str
    player_id: str
    profession_id: str
    level: int = 1
    experience: int = 0
    skill_points: int = 0
    known_recipes: List[str] = field(default_factory=list)
    craft_count: int = 0
    critical_count: int = 0
    failure_count: int = 0
    discovery_count: int = 0
    learned_at: float = field(default_factory=_now)
    last_crafted_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.craft_count
        if total == 0:
            return 1.0
        return (total - self.failure_count) / total

    def to_dict(self) -> Dict[str, Any]:
        result = _dataclass_to_dict(self)
        result["success_rate"] = self.success_rate
        return result


@dataclass
class CraftRecord:
    record_id: str
    player_id: str
    profession_id: str
    recipe_id: str
    result: str = CraftResult.SUCCESS.value
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    ingredients_consumed: List[Dict[str, Any]] = field(default_factory=list)
    xp_gained: int = 0
    timestamp: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProfessionConfig:
    max_player_classes: int = 10
    max_active_classes: int = 1
    max_professions_per_player: int = 2
    max_recipes_per_profession: int = 200
    starting_talent_points: int = 0
    talent_points_per_level: int = 1
    class_switch_cooldown: float = 300.0
    craft_xp_curve_multiplier: float = 1.0
    allow_recipe_discovery: bool = True
    allow_critical_crafts: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProfessionStats:
    total_classes: int = 0
    total_abilities: int = 0
    total_talent_trees: int = 0
    total_player_classes: int = 0
    total_professions: int = 0
    total_recipes: int = 0
    total_player_professions: int = 0
    total_crafts: int = 0
    total_critical_crafts: int = 0
    total_discoveries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProfessionSnapshot:
    classes: List[Dict[str, Any]] = field(default_factory=list)
    professions: List[Dict[str, Any]] = field(default_factory=list)
    player_classes: List[Dict[str, Any]] = field(default_factory=list)
    player_professions: List[Dict[str, Any]] = field(default_factory=list)
    recipes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProfessionEvent:
    event_id: str
    kind: str
    timestamp: float = field(default_factory=_now)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Main system
# ---------------------------------------------------------------------------

class ProfessionClassSystem:
    """Singleton profession & class system."""

    _instance: Optional["ProfessionClassSystem"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "ProfessionClassSystem":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._init_state()
        self._seed()
        self._initialized = True

    def _init_state(self) -> None:
        self._classes: Dict[str, ClassDefinition] = {}
        self._abilities: Dict[str, ClassAbility] = {}
        self._talent_trees: Dict[str, TalentTree] = {}
        self._talent_nodes: Dict[str, TalentNode] = {}
        self._player_classes: Dict[str, PlayerClassState] = {}
        self._player_classes_by_player: Dict[str, List[str]] = {}
        self._player_active_class: Dict[str, str] = {}
        self._professions: Dict[str, ProfessionDefinition] = {}
        self._recipes: Dict[str, Recipe] = {}
        self._recipes_by_profession: Dict[str, List[str]] = {}
        self._player_professions: Dict[str, PlayerProfession] = {}
        self._player_professions_by_player: Dict[str, List[str]] = {}
        self._craft_history: List[CraftRecord] = []
        self._events: List[ProfessionEvent] = []
        self._config = ProfessionConfig()
        self._tick_count: int = 0

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        # === Classes ===
        warrior = ClassDefinition(
            class_id="class_warrior",
            name="Warrior",
            description="A sturdy melee fighter relying on raw strength and rage.",
            archetype=ClassArchetype.TANK.value,
            resource_type=ClassResource.RAGE.value,
            max_resource=100.0,
            resource_regen=10.0,
            base_stats=CLASS_BASE_STATS["warrior"].copy(),
            growth_stats={"strength": 3.0, "vitality": 2.5, "agility": 1.5},
            allowed_weapon_types=["sword", "axe", "mace", "shield"],
            allowed_armor_types=["plate", "heavy"],
            ability_ids=["abl_warrior_slash", "abl_warrior_shield_block", "abl_warrior_whirlwind"],
            talent_tree_ids=["tree_warrior_arms"],
            icon="warrior_icon",
            color="#C79C6E",
            difficulty="easy",
        )
        mage = ClassDefinition(
            class_id="class_mage",
            name="Mage",
            description="A master of arcane arts who hurls devastating spells.",
            archetype=ClassArchetype.DPS_RANGED.value,
            resource_type=ClassResource.MANA.value,
            max_resource=200.0,
            resource_regen=8.0,
            base_stats=CLASS_BASE_STATS["mage"].copy(),
            growth_stats={"intellect": 3.5, "spirit": 2.0, "vitality": 1.0},
            allowed_weapon_types=["staff", "wand"],
            allowed_armor_types=["cloth"],
            ability_ids=["abl_mage_fireball", "abl_mage_frost_nova", "abl_mage_arcane_blast"],
            talent_tree_ids=["tree_mage_arcane"],
            icon="mage_icon",
            color="#69CCF0",
            difficulty="hard",
        )
        rogue = ClassDefinition(
            class_id="class_rogue",
            name="Rogue",
            description="A cunning assassin who strikes from the shadows.",
            archetype=ClassArchetype.DPS_MELEE.value,
            resource_type=ClassResource.ENERGY.value,
            max_resource=100.0,
            resource_regen=20.0,
            base_stats=CLASS_BASE_STATS["rogue"].copy(),
            growth_stats={"agility": 3.5, "strength": 2.0, "vitality": 1.5},
            allowed_weapon_types=["dagger", "sword"],
            allowed_armor_types=["leather"],
            ability_ids=["abl_rogue_backstab", "abl_rogue_stealth", "abl_rogue_eviscerate"],
            talent_tree_ids=["tree_rogue_subtlety"],
            icon="rogue_icon",
            color="#FFF569",
            difficulty="normal",
        )
        cleric = ClassDefinition(
            class_id="class_cleric",
            name="Cleric",
            description="A divine healer who mends wounds and smites undead.",
            archetype=ClassArchetype.HEALER.value,
            resource_type=ClassResource.FAITH.value,
            max_resource=150.0,
            resource_regen=10.0,
            base_stats=CLASS_BASE_STATS["cleric"].copy(),
            growth_stats={"spirit": 3.5, "intellect": 2.5, "vitality": 1.5},
            allowed_weapon_types=["mace", "staff"],
            allowed_armor_types=["cloth", "leather"],
            ability_ids=["abl_cleric_heal", "abl_cleric_smite", "abl_cleric_blessing"],
            talent_tree_ids=["tree_cleric_holy"],
            icon="cleric_icon",
            color="#FFFFFF",
            difficulty="normal",
        )
        paladin = ClassDefinition(
            class_id="class_paladin",
            name="Paladin",
            description="A holy knight who blends martial prowess with divine power.",
            archetype=ClassArchetype.HYBRID.value,
            resource_type=ClassResource.FAITH.value,
            max_resource=120.0,
            resource_regen=8.0,
            base_stats=CLASS_BASE_STATS["paladin"].copy(),
            growth_stats={"strength": 2.5, "vitality": 2.5, "spirit": 2.0},
            allowed_weapon_types=["sword", "mace", "shield"],
            allowed_armor_types=["plate", "heavy"],
            ability_ids=["abl_paladin_judgment", "abl_paladin_lay_hands", "abl_paladin_aura"],
            talent_tree_ids=["tree_paladin_retribution"],
            icon="paladin_icon",
            color="#F58CBA",
            difficulty="normal",
        )
        for c in (warrior, mage, rogue, cleric, paladin):
            self._classes[c.class_id] = c

        # === Abilities ===
        abilities_data = [
            ("abl_warrior_slash", "Slash", "A powerful melee strike.",
             AbilityType.ACTIVE.value, AbilitySchool.PHYSICAL.value, AbilityCategory.BASIC_ATTACK.value,
             "class_warrior", 1, 3.0, 15.0, ClassResource.RAGE.value, 0.0, 5.0,
             50.0, 1.0, 0.0, 0.0, 0.0, {}, {}, ["melee"]),
            ("abl_warrior_shield_block", "Shield Block", "Raise your shield to block incoming attacks.",
             AbilityType.ACTIVE.value, AbilitySchool.PHYSICAL.value, AbilityCategory.DEFENSIVE.value,
             "class_warrior", 3, 15.0, 20.0, ClassResource.RAGE.value, 0.0, 0.0,
             0.0, 0.0, 0.0, 0.0, 6.0, {"armor": 50.0}, {}, ["defense"]),
            ("abl_warrior_whirlwind", "Whirlwind", "Spin your weapon to damage all nearby enemies.",
             AbilityType.ACTIVE.value, AbilitySchool.PHYSICAL.value, AbilityCategory.ULTIMATE.value,
             "class_warrior", 10, 20.0, 50.0, ClassResource.RAGE.value, 0.0, 8.0,
             120.0, 1.5, 0.0, 0.0, 0.0, {}, {}, ["aoe", "ultimate"]),
            ("abl_mage_fireball", "Fireball", "Hurl a flaming sphere at the target.",
             AbilityType.ACTIVE.value, AbilitySchool.FIRE.value, AbilityCategory.BASIC_ATTACK.value,
             "class_mage", 1, 2.5, 25.0, ClassResource.MANA.value, 1.5, 30.0,
             60.0, 1.8, 0.0, 0.0, 0.0, {}, {"movement_speed": -0.2}, ["ranged"]),
            ("abl_mage_frost_nova", "Frost Nova", "Freeze nearby enemies in place.",
             AbilityType.ACTIVE.value, AbilitySchool.FROST.value, AbilityCategory.CROWD_CONTROL.value,
             "class_mage", 5, 18.0, 30.0, ClassResource.MANA.value, 0.0, 8.0,
             30.0, 0.5, 0.0, 0.0, 4.0, {}, {"movement_speed": -1.0}, ["cc", "aoe"]),
            ("abl_mage_arcane_blast", "Arcane Blast", "Unleash a massive burst of arcane energy.",
             AbilityType.ACTIVE.value, AbilitySchool.ARCANE.value, AbilityCategory.ULTIMATE.value,
             "class_mage", 12, 25.0, 60.0, ClassResource.MANA.value, 2.0, 25.0,
             200.0, 2.5, 0.0, 0.0, 0.0, {}, {}, ["ultimate", "aoe"]),
            ("abl_rogue_backstab", "Backstab", "Strike from behind for massive damage.",
             AbilityType.ACTIVE.value, AbilitySchool.PHYSICAL.value, AbilityCategory.SKILL.value,
             "class_rogue", 1, 4.0, 30.0, ClassResource.ENERGY.value, 0.0, 3.0,
             80.0, 2.0, 0.0, 0.0, 0.0, {}, {}, ["positional"]),
            ("abl_rogue_stealth", "Stealth", "Become invisible to enemies.",
             AbilityType.TOGGLE.value, AbilitySchool.SHADOW.value, AbilityCategory.UTILITY.value,
             "class_rogue", 1, 0.0, 20.0, ClassResource.ENERGY.value, 0.0, 0.0,
             0.0, 0.0, 0.0, 0.0, 0.0, {"stealth": 1.0}, {}, ["stealth"]),
            ("abl_rogue_eviscerate", "Eviscerate", "A devastating finishing move.",
             AbilityType.ACTIVE.value, AbilitySchool.PHYSICAL.value, AbilityCategory.ULTIMATE.value,
             "class_rogue", 10, 15.0, 50.0, ClassResource.ENERGY.value, 0.0, 3.0,
             150.0, 2.0, 0.0, 0.0, 0.0, {}, {}, ["finisher"]),
            ("abl_cleric_heal", "Heal", "Restore health to a friendly target.",
             AbilityType.ACTIVE.value, AbilitySchool.HOLY.value, AbilityCategory.HEAL.value,
             "class_cleric", 1, 2.0, 30.0, ClassResource.FAITH.value, 1.5, 30.0,
             0.0, 0.0, 100.0, 2.0, 0.0, {}, {}, ["heal"]),
            ("abl_cleric_smite", "Smite", "Call down divine wrath on the target.",
             AbilityType.ACTIVE.value, AbilitySchool.HOLY.value, AbilityCategory.SKILL.value,
             "class_cleric", 3, 4.0, 25.0, ClassResource.FAITH.value, 1.0, 25.0,
             70.0, 1.2, 0.0, 0.0, 0.0, {}, {}, ["ranged"]),
            ("abl_cleric_blessing", "Blessing", "Bless the target with divine favor.",
             AbilityType.ACTIVE.value, AbilitySchool.HOLY.value, AbilityCategory.BUFF.value,
             "class_cleric", 5, 10.0, 35.0, ClassResource.FAITH.value, 0.0, 30.0,
             0.0, 0.0, 0.0, 0.0, 30.0, {"all_stats": 0.1}, {}, ["buff"]),
            ("abl_paladin_judgment", "Judgment", "Judge the target with holy power.",
             AbilityType.ACTIVE.value, AbilitySchool.HOLY.value, AbilityCategory.SKILL.value,
             "class_paladin", 1, 6.0, 20.0, ClassResource.FAITH.value, 0.0, 10.0,
             60.0, 1.0, 0.0, 0.0, 0.0, {}, {"armor": -0.2}, ["ranged"]),
            ("abl_paladin_lay_hands", "Lay on Hands", "Instantly heal a target to full health.",
             AbilityType.ACTIVE.value, AbilitySchool.HOLY.value, AbilityCategory.ULTIMATE.value,
             "class_paladin", 15, 300.0, 100.0, ClassResource.FAITH.value, 0.0, 10.0,
             0.0, 0.0, 99999.0, 0.0, 0.0, {}, {}, ["ultimate", "heal"]),
            ("abl_paladin_aura", "Devotion Aura", "Project an aura that protects nearby allies.",
             AbilityType.TOGGLE.value, AbilitySchool.HOLY.value, AbilityCategory.BUFF.value,
             "class_paladin", 8, 0.0, 10.0, ClassResource.FAITH.value, 0.0, 0.0,
             0.0, 0.0, 0.0, 0.0, 0.0, {"armor": 0.1, "all_resist": 0.1}, {}, ["aura"]),
        ]
        for row in abilities_data:
            (aid, name, desc, atype, school, cat, cid, lvl, cd, cost, rtype,
             cast, rng, dmg_b, dmg_s, heal_b, heal_s, dur, buff, debuff, tags) = row
            self._abilities[aid] = ClassAbility(
                ability_id=aid, name=name, description=desc, ability_type=atype,
                school=school, category=cat, class_id=cid, required_level=lvl,
                cooldown_seconds=cd, resource_cost=cost, resource_type=rtype,
                cast_time=cast, range_value=rng, damage_base=dmg_b, damage_scaling=dmg_s,
                healing_base=heal_b, healing_scaling=heal_s, duration_seconds=dur,
                buff_stats=buff, debuff_stats=debuff, tags=tags,
            )

        # === Talent Trees ===
        # Warrior Arms tree
        warrior_tree = TalentTree(
            tree_id="tree_warrior_arms", name="Arms", description="Master of two-handed weapons.",
            class_id="class_warrior", max_points=30, spent_points=0,
        )
        w_nodes = [
            TalentNode(node_id="tn_w_1", name="Strength Training", description="+5% strength",
                       tree_id="tree_warrior_arms", node_type=TalentNodeType.STAT.value,
                       max_rank=5, required_points=1, stat_bonuses={"strength_pct": 0.05},
                       position_x=0, position_y=0),
            TalentNode(node_id="tn_w_2", name="Toughness", description="+10% vitality",
                       tree_id="tree_warrior_arms", node_type=TalentNodeType.STAT.value,
                       max_rank=3, required_points=1, stat_bonuses={"vitality_pct": 0.10},
                       position_x=1, position_y=0),
            TalentNode(node_id="tn_w_3", name="Weapon Mastery", description="Increases weapon damage",
                       tree_id="tree_warrior_arms", node_type=TalentNodeType.MASTERY.value,
                       max_rank=3, required_points=2, prerequisite_node_ids=["tn_w_1"],
                       stat_bonuses={"weapon_damage_pct": 0.05}, position_x=0, position_y=1),
            TalentNode(node_id="tn_w_4", name="Berserker Rage", description="Grants Berserker Rage ability",
                       tree_id="tree_warrior_arms", node_type=TalentNodeType.ABILITY.value,
                       max_rank=1, required_points=3, prerequisite_node_ids=["tn_w_3"],
                       granted_ability_id="abl_warrior_whirlwind", position_x=0, position_y=2),
            TalentNode(node_id="tn_w_5", name="Bladestorm", description="Ultimate keystone",
                       tree_id="tree_warrior_arms", node_type=TalentNodeType.KEYSTONE.value,
                       max_rank=1, required_points=5, prerequisite_node_ids=["tn_w_4"],
                       stat_bonuses={"aoe_damage_pct": 0.20}, position_x=0, position_y=3),
        ]
        warrior_tree.nodes = w_nodes
        self._talent_trees[warrior_tree.tree_id] = warrior_tree
        for n in w_nodes:
            self._talent_nodes[n.node_id] = n

        # Mage Arcane tree
        mage_tree = TalentTree(
            tree_id="tree_mage_arcane", name="Arcane", description="Master of arcane magic.",
            class_id="class_mage", max_points=30, spent_points=0,
        )
        m_nodes = [
            TalentNode(node_id="tn_m_1", name="Arcane Focus", description="+5% spell power",
                       tree_id="tree_mage_arcane", node_type=TalentNodeType.STAT.value,
                       max_rank=5, required_points=1, stat_bonuses={"spell_power_pct": 0.05},
                       position_x=0, position_y=0),
            TalentNode(node_id="tn_m_2", name="Mana Pool", description="+10% max mana",
                       tree_id="tree_mage_arcane", node_type=TalentNodeType.STAT.value,
                       max_rank=3, required_points=1, stat_bonuses={"max_mana_pct": 0.10},
                       position_x=1, position_y=0),
            TalentNode(node_id="tn_m_3", name="Spell Penetration", description="Reduces target resistances",
                       tree_id="tree_mage_arcane", node_type=TalentNodeType.MASTERY.value,
                       max_rank=3, required_points=2, prerequisite_node_ids=["tn_m_1"],
                       stat_bonuses={"spell_penetration": 0.05}, position_x=0, position_y=1),
            TalentNode(node_id="tn_m_4", name="Arcane Power", description="Grants Arcane Blast ability",
                       tree_id="tree_mage_arcane", node_type=TalentNodeType.ABILITY.value,
                       max_rank=1, required_points=3, prerequisite_node_ids=["tn_m_3"],
                       granted_ability_id="abl_mage_arcane_blast", position_x=0, position_y=2),
            TalentNode(node_id="tn_m_5", name="Archmage", description="Ultimate keystone",
                       tree_id="tree_mage_arcane", node_type=TalentNodeType.KEYSTONE.value,
                       max_rank=1, required_points=5, prerequisite_node_ids=["tn_m_4"],
                       stat_bonuses={"spell_crit_pct": 0.15}, position_x=0, position_y=3),
        ]
        mage_tree.nodes = m_nodes
        self._talent_trees[mage_tree.tree_id] = mage_tree
        for n in m_nodes:
            self._talent_nodes[n.node_id] = n

        # Rogue Subtlety tree
        rogue_tree = TalentTree(
            tree_id="tree_rogue_subtlety", name="Subtlety", description="Master of stealth and assassination.",
            class_id="class_rogue", max_points=30, spent_points=0,
        )
        r_nodes = [
            TalentNode(node_id="tn_r_1", name="Agility Training", description="+5% agility",
                       tree_id="tree_rogue_subtlety", node_type=TalentNodeType.STAT.value,
                       max_rank=5, required_points=1, stat_bonuses={"agility_pct": 0.05},
                       position_x=0, position_y=0),
            TalentNode(node_id="tn_r_2", name="Stealth Mastery", description="+10% stealth duration",
                       tree_id="tree_rogue_subtlety", node_type=TalentNodeType.STAT.value,
                       max_rank=3, required_points=1, stat_bonuses={"stealth_duration_pct": 0.10},
                       position_x=1, position_y=0),
            TalentNode(node_id="tn_r_3", name="Critical Strike", description="+5% crit chance",
                       tree_id="tree_rogue_subtlety", node_type=TalentNodeType.MASTERY.value,
                       max_rank=3, required_points=2, prerequisite_node_ids=["tn_r_1"],
                       stat_bonuses={"crit_chance_pct": 0.05}, position_x=0, position_y=1),
            TalentNode(node_id="tn_r_4", name="Assassination", description="Grants Eviscerate ability",
                       tree_id="tree_rogue_subtlety", node_type=TalentNodeType.ABILITY.value,
                       max_rank=1, required_points=3, prerequisite_node_ids=["tn_r_3"],
                       granted_ability_id="abl_rogue_eviscerate", position_x=0, position_y=2),
            TalentNode(node_id="tn_r_5", name="Shadow Dance", description="Ultimate keystone",
                       tree_id="tree_rogue_subtlety", node_type=TalentNodeType.KEYSTONE.value,
                       max_rank=1, required_points=5, prerequisite_node_ids=["tn_r_4"],
                       stat_bonuses={"backstab_damage_pct": 0.30}, position_x=0, position_y=3),
        ]
        rogue_tree.nodes = r_nodes
        self._talent_trees[rogue_tree.tree_id] = rogue_tree
        for n in r_nodes:
            self._talent_nodes[n.node_id] = n

        # Cleric Holy tree
        cleric_tree = TalentTree(
            tree_id="tree_cleric_holy", name="Holy", description="Master of divine healing.",
            class_id="class_cleric", max_points=30, spent_points=0,
        )
        c_nodes = [
            TalentNode(node_id="tn_c_1", name="Spiritual Focus", description="+5% healing power",
                       tree_id="tree_cleric_holy", node_type=TalentNodeType.STAT.value,
                       max_rank=5, required_points=1, stat_bonuses={"healing_power_pct": 0.05},
                       position_x=0, position_y=0),
            TalentNode(node_id="tn_c_2", name="Faith", description="+10% max faith",
                       tree_id="tree_cleric_holy", node_type=TalentNodeType.STAT.value,
                       max_rank=3, required_points=1, stat_bonuses={"max_faith_pct": 0.10},
                       position_x=1, position_y=0),
            TalentNode(node_id="tn_c_3", name="Divine Light", description="Reduces heal cast time",
                       tree_id="tree_cleric_holy", node_type=TalentNodeType.MASTERY.value,
                       max_rank=3, required_points=2, prerequisite_node_ids=["tn_c_1"],
                       stat_bonuses={"cast_time_reduction_pct": 0.05}, position_x=0, position_y=1),
            TalentNode(node_id="tn_c_4", name="Holy Nova", description="Grants area healing",
                       tree_id="tree_cleric_holy", node_type=TalentNodeType.ABILITY.value,
                       max_rank=1, required_points=3, prerequisite_node_ids=["tn_c_3"],
                       granted_ability_id="abl_cleric_blessing", position_x=0, position_y=2),
            TalentNode(node_id="tn_c_5", name="Divine Miracle", description="Ultimate keystone",
                       tree_id="tree_cleric_holy", node_type=TalentNodeType.KEYSTONE.value,
                       max_rank=1, required_points=5, prerequisite_node_ids=["tn_c_4"],
                       stat_bonuses={"heal_crit_pct": 0.20}, position_x=0, position_y=3),
        ]
        cleric_tree.nodes = c_nodes
        self._talent_trees[cleric_tree.tree_id] = cleric_tree
        for n in c_nodes:
            self._talent_nodes[n.node_id] = n

        # Paladin Retribution tree
        paladin_tree = TalentTree(
            tree_id="tree_paladin_retribution", name="Retribution", description="Holy justice through strength.",
            class_id="class_paladin", max_points=30, spent_points=0,
        )
        p_nodes = [
            TalentNode(node_id="tn_p_1", name="Divine Strength", description="+5% strength",
                       tree_id="tree_paladin_retribution", node_type=TalentNodeType.STAT.value,
                       max_rank=5, required_points=1, stat_bonuses={"strength_pct": 0.05},
                       position_x=0, position_y=0),
            TalentNode(node_id="tn_p_2", name="Conviction", description="+5% crit chance",
                       tree_id="tree_paladin_retribution", node_type=TalentNodeType.STAT.value,
                       max_rank=3, required_points=1, stat_bonuses={"crit_chance_pct": 0.05},
                       position_x=1, position_y=0),
            TalentNode(node_id="tn_p_3", name="Two-Handed Mastery", description="+10% two-handed damage",
                       tree_id="tree_paladin_retribution", node_type=TalentNodeType.MASTERY.value,
                       max_rank=3, required_points=2, prerequisite_node_ids=["tn_p_1"],
                       stat_bonuses={"two_handed_damage_pct": 0.10}, position_x=0, position_y=1),
            TalentNode(node_id="tn_p_4", name="Divine Storm", description="Grants area attack",
                       tree_id="tree_paladin_retribution", node_type=TalentNodeType.ABILITY.value,
                       max_rank=1, required_points=3, prerequisite_node_ids=["tn_p_3"],
                       granted_ability_id="abl_paladin_judgment", position_x=0, position_y=2),
            TalentNode(node_id="tn_p_5", name="Avenging Wrath", description="Ultimate keystone",
                       tree_id="tree_paladin_retribution", node_type=TalentNodeType.KEYSTONE.value,
                       max_rank=1, required_points=5, prerequisite_node_ids=["tn_p_4"],
                       stat_bonuses={"damage_pct": 0.20, "healing_pct": 0.20}, position_x=0, position_y=3),
        ]
        paladin_tree.nodes = p_nodes
        self._talent_trees[paladin_tree.tree_id] = paladin_tree
        for n in p_nodes:
            self._talent_nodes[n.node_id] = n

        # === Player Class States ===
        # Player starter as a Warrior level 10
        ps_warrior = PlayerClassState(
            state_id="pcs_starter_warrior",
            player_id="player_starter",
            class_id="class_warrior",
            status=PlayerClassStatus.ACTIVE.value,
            level=10,
            experience=500,
            current_resource=100.0,
            max_resource=100.0,
            learned_abilities=["abl_warrior_slash", "abl_warrior_shield_block", "abl_warrior_whirlwind"],
            equipped_abilities=["abl_warrior_slash", "abl_warrior_shield_block", "abl_warrior_whirlwind"],
            talent_spent={"tn_w_1": 5, "tn_w_2": 3, "tn_w_3": 2},
            talent_points_available=0,
            total_talent_points=10,
            playtime_seconds=36000.0,
        )
        self._player_classes[ps_warrior.state_id] = ps_warrior
        self._player_classes_by_player.setdefault("player_starter", []).append(ps_warrior.state_id)
        self._player_active_class["player_starter"] = ps_warrior.state_id

        # Player starter also has Mage class (inactive)
        ps_mage = PlayerClassState(
            state_id="pcs_starter_mage",
            player_id="player_starter",
            class_id="class_mage",
            status=PlayerClassStatus.INACTIVE.value,
            level=5,
            experience=200,
            current_resource=200.0,
            max_resource=200.0,
            learned_abilities=["abl_mage_fireball", "abl_mage_frost_nova"],
            equipped_abilities=["abl_mage_fireball", "abl_mage_frost_nova"],
            talent_spent={"tn_m_1": 3},
            talent_points_available=2,
            total_talent_points=5,
            playtime_seconds=18000.0,
        )
        self._player_classes[ps_mage.state_id] = ps_mage
        self._player_classes_by_player.setdefault("player_starter", []).append(ps_mage.state_id)

        # Player veteran as a Rogue level 20
        pv_rogue = PlayerClassState(
            state_id="pcs_veteran_rogue",
            player_id="player_veteran",
            class_id="class_rogue",
            status=PlayerClassStatus.ACTIVE.value,
            level=20,
            experience=1500,
            current_resource=100.0,
            max_resource=100.0,
            learned_abilities=["abl_rogue_backstab", "abl_rogue_stealth", "abl_rogue_eviscerate"],
            equipped_abilities=["abl_rogue_backstab", "abl_rogue_stealth", "abl_rogue_eviscerate"],
            talent_spent={"tn_r_1": 5, "tn_r_2": 3, "tn_r_3": 3, "tn_r_4": 1, "tn_r_5": 1},
            talent_points_available=7,
            total_talent_points=20,
            playtime_seconds=72000.0,
        )
        self._player_classes[pv_rogue.state_id] = pv_rogue
        self._player_classes_by_player.setdefault("player_veteran", []).append(pv_rogue.state_id)
        self._player_active_class["player_veteran"] = pv_rogue.state_id

        # === Professions ===
        mining = ProfessionDefinition(
            profession_id="prof_mining", name="Mining",
            description="Extract valuable ores and gems from mineral deposits.",
            profession_type=ProfessionType.GATHERING.value, category=ProfessionCategory.MINING.value,
            max_level=100,
        )
        blacksmithing = ProfessionDefinition(
            profession_id="prof_blacksmithing", name="Blacksmithing",
            description="Forge weapons and heavy armor from metal ingots.",
            profession_type=ProfessionType.CRAFTING.value, category=ProfessionCategory.BLACKSMITHING.value,
            max_level=100,
        )
        alchemy = ProfessionDefinition(
            profession_id="prof_alchemy", name="Alchemy",
            description="Brew potent potions and elixirs from herbs.",
            profession_type=ProfessionType.CRAFTING.value, category=ProfessionCategory.ALCHEMY.value,
            max_level=100,
        )
        herbalism = ProfessionDefinition(
            profession_id="prof_herbalism", name="Herbalism",
            description="Gather herbs and plant materials from the wild.",
            profession_type=ProfessionType.GATHERING.value, category=ProfessionCategory.HERBALISM.value,
            max_level=100,
        )
        cooking = ProfessionDefinition(
            profession_id="prof_cooking", name="Cooking",
            description="Prepare food that provides buffs and restoration.",
            profession_type=ProfessionType.SERVICE.value, category=ProfessionCategory.COOKING.value,
            max_level=100,
        )
        for p in (mining, blacksmithing, alchemy, herbalism, cooking):
            self._professions[p.profession_id] = p

        # === Recipes ===
        recipes_data = [
            # Blacksmithing recipes
            ("recipe_iron_sword", "Iron Sword", "A basic iron sword.",
             "prof_blacksmithing", ProfessionCategory.BLACKSMITHING.value, 1, RecipeRarity.COMMON.value,
             [("item_iron_ingot", "Iron Ingot", 3)], [("item_iron_sword", "Iron Sword", 1, 1.0)],
             5.0, 0.95, 0.05, 0.0, 10, "anvil"),
            ("recipe_steel_blade", "Steel Blade", "A refined steel blade.",
             "prof_blacksmithing", ProfessionCategory.BLACKSMITHING.value, 25, RecipeRarity.UNCOMMON.value,
             [("item_steel_ingot", "Steel Ingot", 4), ("item_leather_strip", "Leather Strip", 2)],
             [("item_steel_blade", "Steel Blade", 1, 1.0)], 8.0, 0.90, 0.08, 0.02, 25, "anvil"),
            ("recipe_dragon_armor", "Dragon Armor", "Legendary armor forged from dragon scales.",
             "prof_blacksmithing", ProfessionCategory.BLACKSMITHING.value, 80, RecipeRarity.LEGENDARY.value,
             [("item_dragon_scale", "Dragon Scale", 10), ("item_mithril_ingot", "Mithril Ingot", 5)],
             [("item_dragon_armor", "Dragon Armor", 1, 1.0)], 30.0, 0.75, 0.15, 0.05, 100, "anvil"),
            # Alchemy recipes
            ("recipe_health_potion", "Health Potion", "Restores health when consumed.",
             "prof_alchemy", ProfessionCategory.ALCHEMY.value, 1, RecipeRarity.COMMON.value,
             [("item_herb_mountain", "Mountain Herb", 2)], [("item_health_potion", "Health Potion", 1, 1.0)],
             3.0, 0.98, 0.03, 0.0, 8, "alchemy_table"),
            ("recipe_mana_elixir", "Mana Elixir", "Restores mana when consumed.",
             "prof_alchemy", ProfessionCategory.ALCHEMY.value, 15, RecipeRarity.UNCOMMON.value,
             [("item_herb_moonleaf", "Moonleaf Herb", 3), ("item_crystal_dust", "Crystal Dust", 1)],
             [("item_mana_elixir", "Mana Elixir", 1, 1.0)], 5.0, 0.95, 0.05, 0.01, 15, "alchemy_table"),
            ("recipe_greater_strength", "Greater Strength Potion", "Temporarily increases strength.",
             "prof_alchemy", ProfessionCategory.ALCHEMY.value, 40, RecipeRarity.RARE.value,
             [("item_herb_bloodroot", "Bloodroot", 2), ("item_iron_essence", "Iron Essence", 1)],
             [("item_greater_strength", "Greater Strength Potion", 1, 1.0)],
             8.0, 0.90, 0.08, 0.02, 35, "alchemy_table"),
            # Cooking recipes
            ("recipe_roasted_meat", "Roasted Meat", "A hearty meal that restores health.",
             "prof_cooking", ProfessionCategory.COOKING.value, 1, RecipeRarity.COMMON.value,
             [("item_raw_meat", "Raw Meat", 1)], [("item_roasted_meat", "Roasted Meat", 1, 1.0)],
             2.0, 0.99, 0.02, 0.0, 5, "cooking_fire"),
            ("recipe_feast", "Grand Feast", "A feast that boosts the entire party.",
             "prof_cooking", ProfessionCategory.COOKING.value, 50, RecipeRarity.EPIC.value,
             [("item_raw_meat", "Raw Meat", 5), ("item_spices", "Spices", 3), ("item_vegetables", "Vegetables", 5)],
             [("item_feast", "Grand Feast", 1, 1.0)], 15.0, 0.85, 0.10, 0.03, 60, "cooking_fire"),
        ]
        for row in recipes_data:
            (rid, name, desc, pid, cat, lvl, rar, ings, outs, ct, sc, cc, dc, xp, station) = row
            ingredients = [RecipeIngredient(item_id=i[0], item_name=i[1], quantity=i[2]) for i in ings]
            outputs = [RecipeOutput(item_id=o[0], item_name=o[1], quantity=o[2], chance=o[3]) for o in outs]
            self._recipes[rid] = Recipe(
                recipe_id=rid, name=name, description=desc, profession_id=pid, category=cat,
                required_level=lvl, rarity=rar, ingredients=ingredients, outputs=outputs,
                craft_time_seconds=ct, success_chance=sc, critical_chance=cc, discovery_chance=dc,
                skill_xp=xp, station_required=station,
            )
            self._recipes_by_profession.setdefault(pid, []).append(rid)

        # === Player Professions ===
        # Player starter has Blacksmithing level 15
        pp_bs = PlayerProfession(
            pp_id="pp_starter_bs", player_id="player_starter", profession_id="prof_blacksmithing",
            level=15, experience=800, skill_points=15,
            known_recipes=["recipe_iron_sword", "recipe_steel_blade"],
            craft_count=50, critical_count=5, failure_count=2, discovery_count=0,
        )
        self._player_professions[pp_bs.pp_id] = pp_bs
        self._player_professions_by_player.setdefault("player_starter", []).append(pp_bs.pp_id)

        # Player starter has Mining level 20
        pp_mining = PlayerProfession(
            pp_id="pp_starter_mining", player_id="player_starter", profession_id="prof_mining",
            level=20, experience=1500, skill_points=20,
            known_recipes=[], craft_count=200, critical_count=10, failure_count=0, discovery_count=0,
        )
        self._player_professions[pp_mining.pp_id] = pp_mining
        self._player_professions_by_player.setdefault("player_starter", []).append(pp_mining.pp_id)

        # Player veteran has Alchemy level 50
        pp_alch = PlayerProfession(
            pp_id="pp_veteran_alch", player_id="player_veteran", profession_id="prof_alchemy",
            level=50, experience=8000, skill_points=50,
            known_recipes=["recipe_health_potion", "recipe_mana_elixir", "recipe_greater_strength"],
            craft_count=500, critical_count=40, failure_count=10, discovery_count=3,
        )
        self._player_professions[pp_alch.pp_id] = pp_alch
        self._player_professions_by_player.setdefault("player_veteran", []).append(pp_alch.pp_id)

        # Player veteran has Cooking level 30
        pp_cook = PlayerProfession(
            pp_id="pp_veteran_cook", player_id="player_veteran", profession_id="prof_cooking",
            level=30, experience=3000, skill_points=30,
            known_recipes=["recipe_roasted_meat"],
            craft_count=150, critical_count=15, failure_count=3, discovery_count=1,
        )
        self._player_professions[pp_cook.pp_id] = pp_cook
        self._player_professions_by_player.setdefault("player_veteran", []).append(pp_cook.pp_id)

        self._log_event(ProfessionEventKind.TICK.value, {"note": "seeded"})

    def _log_event(self, kind: str, data: Optional[Dict[str, Any]] = None) -> None:
        event = ProfessionEvent(event_id=_new_id("evt"), kind=kind, data=data or {})
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Class management
    # ------------------------------------------------------------------

    def register_class(self, class_id: str, name: str, description: str = "",
                       archetype: str = ClassArchetype.DPS_MELEE.value,
                       resource_type: str = ClassResource.MANA.value,
                       max_resource: float = 100.0, resource_regen: float = 5.0,
                       base_stats: Optional[Dict[str, float]] = None,
                       growth_stats: Optional[Dict[str, float]] = None,
                       allowed_weapon_types: Optional[List[str]] = None,
                       allowed_armor_types: Optional[List[str]] = None,
                       icon: str = "", color: str = "#FFFFFF",
                       difficulty: str = "normal", unlocked: bool = True) -> Tuple[bool, str, Optional[ClassDefinition]]:
        with _LOCK:
            if class_id in self._classes:
                return False, "class_exists", None
            if len(self._classes) >= _MAX_CLASSES:
                return False, "max_classes", None
            cls = ClassDefinition(
                class_id=class_id, name=name, description=description,
                archetype=archetype, resource_type=resource_type,
                max_resource=max_resource, resource_regen=resource_regen,
                base_stats=base_stats or {}, growth_stats=growth_stats or {},
                allowed_weapon_types=allowed_weapon_types or [],
                allowed_armor_types=allowed_armor_types or [],
                icon=icon, color=color, difficulty=difficulty, unlocked=unlocked,
            )
            self._classes[class_id] = cls
            self._log_event(ProfessionEventKind.CLASS_REGISTERED.value, {"class_id": class_id})
            return True, "registered", cls

    def remove_class(self, class_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if class_id not in self._classes:
                return False, "not_found"
            # Remove talent trees for this class
            tree_ids_to_remove = [tid for tid, t in self._talent_trees.items() if t.class_id == class_id]
            for tid in tree_ids_to_remove:
                tree = self._talent_trees.pop(tid)
                for n in tree.nodes:
                    self._talent_nodes.pop(n.node_id, None)
            # Remove abilities for this class
            abil_ids_to_remove = [aid for aid, a in self._abilities.items() if a.class_id == class_id]
            for aid in abil_ids_to_remove:
                del self._abilities[aid]
            del self._classes[class_id]
            self._log_event(ProfessionEventKind.CLASS_REMOVED.value, {"class_id": class_id})
            return True, "removed"

    def get_class(self, class_id: str) -> Optional[ClassDefinition]:
        with _LOCK:
            return self._classes.get(class_id)

    def list_classes(self, limit: int = 50, offset: int = 0,
                     archetype: Optional[str] = None) -> List[ClassDefinition]:
        with _LOCK:
            items = list(self._classes.values())
            if archetype:
                items = [c for c in items if c.archetype == archetype]
            return items[offset:offset + limit]

    def unlock_class(self, class_id: str) -> Tuple[bool, str, Optional[ClassDefinition]]:
        with _LOCK:
            cls = self._classes.get(class_id)
            if cls is None:
                return False, "not_found", None
            cls.unlocked = True
            self._log_event(ProfessionEventKind.CLASS_UNLOCKED.value, {"class_id": class_id})
            return True, "unlocked", cls

    # ------------------------------------------------------------------
    # Ability management
    # ------------------------------------------------------------------

    def register_ability(self, ability_id: str, name: str, description: str = "",
                         ability_type: str = AbilityType.ACTIVE.value,
                         school: str = AbilitySchool.PHYSICAL.value,
                         category: str = AbilityCategory.SKILL.value,
                         class_id: str = "", required_level: int = 1,
                         cooldown_seconds: float = 5.0, resource_cost: float = 20.0,
                         resource_type: str = ClassResource.MANA.value,
                         cast_time: float = 0.0, range_value: float = 5.0,
                         damage_base: float = 0.0, damage_scaling: float = 0.0,
                         healing_base: float = 0.0, healing_scaling: float = 0.0,
                         duration_seconds: float = 0.0,
                         buff_stats: Optional[Dict[str, float]] = None,
                         debuff_stats: Optional[Dict[str, float]] = None,
                         tags: Optional[List[str]] = None) -> Tuple[bool, str, Optional[ClassAbility]]:
        with _LOCK:
            if ability_id in self._abilities:
                return False, "ability_exists", None
            if len(self._abilities) >= _MAX_ABILITIES:
                return False, "max_abilities", None
            abil = ClassAbility(
                ability_id=ability_id, name=name, description=description,
                ability_type=ability_type, school=school, category=category,
                class_id=class_id, required_level=required_level,
                cooldown_seconds=cooldown_seconds, resource_cost=resource_cost,
                resource_type=resource_type, cast_time=cast_time, range_value=range_value,
                damage_base=damage_base, damage_scaling=damage_scaling,
                healing_base=healing_base, healing_scaling=healing_scaling,
                duration_seconds=duration_seconds,
                buff_stats=buff_stats or {}, debuff_stats=debuff_stats or {},
                tags=tags or [],
            )
            self._abilities[ability_id] = abil
            # Link to class if specified
            if class_id and class_id in self._classes:
                if ability_id not in self._classes[class_id].ability_ids:
                    self._classes[class_id].ability_ids.append(ability_id)
            return True, "registered", abil

    def get_ability(self, ability_id: str) -> Optional[ClassAbility]:
        with _LOCK:
            return self._abilities.get(ability_id)

    def list_abilities(self, limit: int = 50, offset: int = 0,
                       class_id: Optional[str] = None,
                       category: Optional[str] = None) -> List[ClassAbility]:
        with _LOCK:
            items = list(self._abilities.values())
            if class_id:
                items = [a for a in items if a.class_id == class_id]
            if category:
                items = [a for a in items if a.category == category]
            return items[offset:offset + limit]

    # ------------------------------------------------------------------
    # Talent tree management
    # ------------------------------------------------------------------

    def register_talent_tree(self, tree_id: str, name: str, description: str = "",
                             class_id: str = "", max_points: int = 30) -> Tuple[bool, str, Optional[TalentTree]]:
        with _LOCK:
            if tree_id in self._talent_trees:
                return False, "tree_exists", None
            if len(self._talent_trees) >= _MAX_TALENTS:
                return False, "max_talent_trees", None
            tree = TalentTree(
                tree_id=tree_id, name=name, description=description,
                class_id=class_id, max_points=max_points,
            )
            self._talent_trees[tree_id] = tree
            if class_id and class_id in self._classes:
                if tree_id not in self._classes[class_id].talent_tree_ids:
                    self._classes[class_id].talent_tree_ids.append(tree_id)
            return True, "registered", tree

    def get_talent_tree(self, tree_id: str) -> Optional[TalentTree]:
        with _LOCK:
            return self._talent_trees.get(tree_id)

    def list_talent_trees(self, limit: int = 50, offset: int = 0,
                          class_id: Optional[str] = None) -> List[TalentTree]:
        with _LOCK:
            items = list(self._talent_trees.values())
            if class_id:
                items = [t for t in items if t.class_id == class_id]
            return items[offset:offset + limit]

    def add_talent_node(self, tree_id: str, node_id: str, name: str, description: str = "",
                        node_type: str = TalentNodeType.STAT.value,
                        max_rank: int = 1, required_points: int = 1,
                        prerequisite_node_ids: Optional[List[str]] = None,
                        stat_bonuses: Optional[Dict[str, float]] = None,
                        granted_ability_id: str = "",
                        position_x: int = 0, position_y: int = 0) -> Tuple[bool, str, Optional[TalentNode]]:
        with _LOCK:
            tree = self._talent_trees.get(tree_id)
            if tree is None:
                return False, "tree_not_found", None
            if node_id in self._talent_nodes:
                return False, "node_exists", None
            if len(self._talent_nodes) >= _MAX_TALENT_NODES:
                return False, "max_nodes", None
            node = TalentNode(
                node_id=node_id, name=name, description=description,
                node_type=node_type, tree_id=tree_id, max_rank=max_rank,
                required_points=required_points,
                prerequisite_node_ids=prerequisite_node_ids or [],
                stat_bonuses=stat_bonuses or {},
                granted_ability_id=granted_ability_id,
                position_x=position_x, position_y=position_y,
            )
            tree.nodes.append(node)
            self._talent_nodes[node_id] = node
            return True, "added", node

    # ------------------------------------------------------------------
    # Player class management
    # ------------------------------------------------------------------

    def set_player_class(self, player_id: str, class_id: str,
                         level: int = 1, experience: int = 0) -> Tuple[bool, str, Optional[PlayerClassState]]:
        """Assigns a class to a player (creates a new PlayerClassState)."""
        with _LOCK:
            cls = self._classes.get(class_id)
            if cls is None:
                return False, "class_not_found", None
            if not cls.unlocked:
                return False, "class_locked", None
            # Check if player already has this class
            existing_ids = self._player_classes_by_player.get(player_id, [])
            for sid in existing_ids:
                state = self._player_classes.get(sid)
                if state and state.class_id == class_id:
                    return False, "already_has_class", state
            # Check max classes per player
            if len(existing_ids) >= self._config.max_player_classes:
                return False, "max_player_classes", None
            state_id = _new_id("pcs")
            state = PlayerClassState(
                state_id=state_id, player_id=player_id, class_id=class_id,
                status=PlayerClassStatus.INACTIVE.value, level=level, experience=experience,
                max_resource=cls.max_resource, current_resource=cls.max_resource,
                talent_points_available=self._config.starting_talent_points + (level - 1) * self._config.talent_points_per_level,
                total_talent_points=self._config.starting_talent_points + (level - 1) * self._config.talent_points_per_level,
            )
            self._player_classes[state_id] = state
            self._player_classes_by_player.setdefault(player_id, []).append(state_id)
            self._log_event(ProfessionEventKind.PLAYER_CLASS_SET.value,
                            {"player_id": player_id, "class_id": class_id})
            return True, "set", state

    def switch_player_class(self, player_id: str, class_id: str) -> Tuple[bool, str, Optional[PlayerClassState]]:
        """Activates a player's class (deactivating their current active one)."""
        with _LOCK:
            existing_ids = self._player_classes_by_player.get(player_id, [])
            target_state: Optional[PlayerClassState] = None
            for sid in existing_ids:
                state = self._player_classes.get(sid)
                if state and state.class_id == class_id:
                    target_state = state
                    break
            if target_state is None:
                return False, "class_not_owned", None
            if target_state.status == PlayerClassStatus.LOCKED.value:
                return False, "class_locked", None
            # Deactivate current active class
            current_active_id = self._player_active_class.get(player_id)
            if current_active_id and current_active_id in self._player_classes:
                current = self._player_classes[current_active_id]
                if current.status == PlayerClassStatus.ACTIVE.value:
                    current.status = PlayerClassStatus.INACTIVE.value
            # Activate target
            target_state.status = PlayerClassStatus.ACTIVE.value
            target_state.last_used = _now()
            self._player_active_class[player_id] = target_state.state_id
            self._log_event(ProfessionEventKind.PLAYER_CLASS_SWITCHED.value,
                            {"player_id": player_id, "class_id": class_id})
            return True, "switched", target_state

    def get_player_class_state(self, state_id: str) -> Optional[PlayerClassState]:
        with _LOCK:
            return self._player_classes.get(state_id)

    def get_player_active_class(self, player_id: str) -> Optional[PlayerClassState]:
        with _LOCK:
            active_id = self._player_active_class.get(player_id)
            if active_id is None:
                return None
            return self._player_classes.get(active_id)

    def list_player_classes(self, player_id: str) -> List[PlayerClassState]:
        with _LOCK:
            ids = self._player_classes_by_player.get(player_id, [])
            return [self._player_classes[sid] for sid in ids if sid in self._player_classes]

    def add_player_experience(self, state_id: str, xp: int) -> Tuple[bool, str, Optional[PlayerClassState], bool]:
        """Adds XP to a player class state. Returns (success, msg, state, leveled_up)."""
        with _LOCK:
            state = self._player_classes.get(state_id)
            if state is None:
                return False, "not_found", None, False
            state.experience += xp
            leveled_up = False
            while True:
                needed = _xp_for_level(state.level)
                if state.experience < needed:
                    break
                state.experience -= needed
                state.level += 1
                state.talent_points_available += self._config.talent_points_per_level
                state.total_talent_points += self._config.talent_points_per_level
                leveled_up = True
            return True, "added", state, leveled_up

    # ------------------------------------------------------------------
    # Player ability management
    # ------------------------------------------------------------------

    def learn_ability(self, state_id: str, ability_id: str) -> Tuple[bool, str, Optional[PlayerClassState]]:
        with _LOCK:
            state = self._player_classes.get(state_id)
            if state is None:
                return False, "state_not_found", None
            abil = self._abilities.get(ability_id)
            if abil is None:
                return False, "ability_not_found", None
            # Check class match (or no class restriction)
            if abil.class_id and abil.class_id != state.class_id:
                return False, "wrong_class", None
            if state.level < abil.required_level:
                return False, "level_too_low", None
            if ability_id in state.learned_abilities:
                return False, "already_learned", None
            state.learned_abilities.append(ability_id)
            # Auto-equip if room
            if len(state.equipped_abilities) < state.max_equipped:
                state.equipped_abilities.append(ability_id)
            self._log_event(ProfessionEventKind.ABILITY_LEARNED.value,
                            {"state_id": state_id, "ability_id": ability_id})
            return True, "learned", state

    def forget_ability(self, state_id: str, ability_id: str) -> Tuple[bool, str, Optional[PlayerClassState]]:
        with _LOCK:
            state = self._player_classes.get(state_id)
            if state is None:
                return False, "state_not_found", None
            if ability_id not in state.learned_abilities:
                return False, "not_learned", None
            state.learned_abilities.remove(ability_id)
            if ability_id in state.equipped_abilities:
                state.equipped_abilities.remove(ability_id)
            self._log_event(ProfessionEventKind.ABILITY_FORGOTTEN.value,
                            {"state_id": state_id, "ability_id": ability_id})
            return True, "forgotten", state

    def equip_ability(self, state_id: str, ability_id: str) -> Tuple[bool, str, Optional[PlayerClassState]]:
        with _LOCK:
            state = self._player_classes.get(state_id)
            if state is None:
                return False, "state_not_found", None
            if ability_id not in state.learned_abilities:
                return False, "not_learned", None
            if ability_id in state.equipped_abilities:
                return False, "already_equipped", None
            if len(state.equipped_abilities) >= state.max_equipped:
                return False, "no_slot", None
            state.equipped_abilities.append(ability_id)
            return True, "equipped", state

    def unequip_ability(self, state_id: str, ability_id: str) -> Tuple[bool, str, Optional[PlayerClassState]]:
        with _LOCK:
            state = self._player_classes.get(state_id)
            if state is None:
                return False, "state_not_found", None
            if ability_id not in state.equipped_abilities:
                return False, "not_equipped", None
            state.equipped_abilities.remove(ability_id)
            return True, "unequipped", state

    def use_ability(self, state_id: str, ability_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Simulates using an ability: checks resource, deducts cost."""
        with _LOCK:
            state = self._player_classes.get(state_id)
            if state is None:
                return False, "state_not_found", None
            abil = self._abilities.get(ability_id)
            if abil is None:
                return False, "ability_not_found", None
            if ability_id not in state.equipped_abilities:
                return False, "not_equipped", None
            if state.current_resource < abil.resource_cost:
                return False, "insufficient_resource", None
            state.current_resource -= abil.resource_cost
            result = {
                "ability_id": ability_id,
                "ability_name": abil.name,
                "damage": abil.damage_base + (state.level * abil.damage_scaling),
                "healing": abil.healing_base + (state.level * abil.healing_scaling),
                "resource_consumed": abil.resource_cost,
                "remaining_resource": state.current_resource,
            }
            self._log_event(ProfessionEventKind.ABILITY_USED.value,
                            {"state_id": state_id, "ability_id": ability_id})
            return True, "used", result

    # ------------------------------------------------------------------
    # Player talent management
    # ------------------------------------------------------------------

    def learn_talent(self, state_id: str, node_id: str, points: int = 1) -> Tuple[bool, str, Optional[PlayerClassState]]:
        with _LOCK:
            state = self._player_classes.get(state_id)
            if state is None:
                return False, "state_not_found", None
            node = self._talent_nodes.get(node_id)
            if node is None:
                return False, "node_not_found", None
            # Check tree belongs to player's class
            tree = self._talent_trees.get(node.tree_id)
            if tree is None or tree.class_id != state.class_id:
                return False, "wrong_class_tree", None
            current_rank = state.talent_spent.get(node_id, 0)
            if current_rank >= node.max_rank:
                return False, "max_rank", None
            if current_rank + points > node.max_rank:
                return False, "exceeds_max_rank", None
            if state.talent_points_available < points:
                return False, "insufficient_points", None
            # Check prerequisites
            for prereq_id in node.prerequisite_node_ids:
                prereq = self._talent_nodes.get(prereq_id)
                if prereq is None:
                    return False, "prereq_not_found", None
                prereq_rank = state.talent_spent.get(prereq_id, 0)
                if prereq_rank < prereq.max_rank:
                    return False, "prereq_not_met", None
            state.talent_spent[node_id] = current_rank + points
            state.talent_points_available -= points
            tree = self._talent_trees.get(node.tree_id)
            if tree:
                tree.spent_points += points
            # Grant ability if this is an ability node
            if node.granted_ability_id and node.granted_ability_id not in state.learned_abilities:
                state.learned_abilities.append(node.granted_ability_id)
            self._log_event(ProfessionEventKind.TALENT_LEARNED.value,
                            {"state_id": state_id, "node_id": node_id, "points": points})
            return True, "learned", state

    def reset_talent_node(self, state_id: str, node_id: str) -> Tuple[bool, str, Optional[PlayerClassState]]:
        with _LOCK:
            state = self._player_classes.get(state_id)
            if state is None:
                return False, "state_not_found", None
            if node_id not in state.talent_spent or state.talent_spent[node_id] == 0:
                return False, "not_learned", None
            refunded = state.talent_spent.pop(node_id)
            state.talent_points_available += refunded
            node = self._talent_nodes.get(node_id)
            if node:
                tree = self._talent_trees.get(node.tree_id)
                if tree:
                    tree.spent_points = max(0, tree.spent_points - refunded)
                # Remove granted ability if no longer qualified
                if node.granted_ability_id and node.granted_ability_id in state.learned_abilities:
                    state.learned_abilities.remove(node.granted_ability_id)
            self._log_event(ProfessionEventKind.TALENT_RESET.value,
                            {"state_id": state_id, "node_id": node_id})
            return True, "reset", state

    def reset_talent_tree(self, state_id: str, tree_id: str) -> Tuple[bool, str, Optional[PlayerClassState]]:
        with _LOCK:
            state = self._player_classes.get(state_id)
            if state is None:
                return False, "state_not_found", None
            tree = self._talent_trees.get(tree_id)
            if tree is None:
                return False, "tree_not_found", None
            # Find all nodes belonging to this tree that the player has invested in
            nodes_to_reset = [nid for nid, _ in state.talent_spent.items()
                              if nid in self._talent_nodes and self._talent_nodes[nid].tree_id == tree_id]
            total_refunded = 0
            for nid in nodes_to_reset:
                refunded = state.talent_spent.pop(nid)
                total_refunded += refunded
                node = self._talent_nodes.get(nid)
                if node and node.granted_ability_id and node.granted_ability_id in state.learned_abilities:
                    state.learned_abilities.remove(node.granted_ability_id)
            state.talent_points_available += total_refunded
            tree.spent_points = 0
            self._log_event(ProfessionEventKind.TALENT_TREE_RESET.value,
                            {"state_id": state_id, "tree_id": tree_id, "refunded": total_refunded})
            return True, "reset", state

    # ------------------------------------------------------------------
    # Profession management
    # ------------------------------------------------------------------

    def register_profession(self, profession_id: str, name: str, description: str = "",
                            profession_type: str = ProfessionType.CRAFTING.value,
                            category: str = ProfessionCategory.BLACKSMITHING.value,
                            max_level: int = 100) -> Tuple[bool, str, Optional[ProfessionDefinition]]:
        with _LOCK:
            if profession_id in self._professions:
                return False, "profession_exists", None
            if len(self._professions) >= _MAX_PROFESSIONS:
                return False, "max_professions", None
            prof = ProfessionDefinition(
                profession_id=profession_id, name=name, description=description,
                profession_type=profession_type, category=category, max_level=max_level,
            )
            self._professions[profession_id] = prof
            return True, "registered", prof

    def get_profession(self, profession_id: str) -> Optional[ProfessionDefinition]:
        with _LOCK:
            return self._professions.get(profession_id)

    def list_professions(self, limit: int = 50, offset: int = 0,
                         profession_type: Optional[str] = None) -> List[ProfessionDefinition]:
        with _LOCK:
            items = list(self._professions.values())
            if profession_type:
                items = [p for p in items if p.profession_type == profession_type]
            return items[offset:offset + limit]

    # ------------------------------------------------------------------
    # Recipe management
    # ------------------------------------------------------------------

    def register_recipe(self, recipe_id: str, name: str, description: str = "",
                        profession_id: str = "", category: str = ProfessionCategory.BLACKSMITHING.value,
                        required_level: int = 1, rarity: str = RecipeRarity.COMMON.value,
                        craft_time_seconds: float = 5.0, success_chance: float = 0.95,
                        critical_chance: float = 0.05, discovery_chance: float = 0.0,
                        skill_xp: int = 10, station_required: str = "",
                        ingredients: Optional[List[Dict[str, Any]]] = None,
                        outputs: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, str, Optional[Recipe]]:
        with _LOCK:
            if recipe_id in self._recipes:
                return False, "recipe_exists", None
            if len(self._recipes) >= _MAX_RECIPES:
                return False, "max_recipes", None
            ings = [RecipeIngredient(
                item_id=i.get("item_id", ""),
                item_name=i.get("item_name", ""),
                quantity=_safe_int(i.get("quantity", 1)),
            ) for i in (ingredients or [])]
            outs = [RecipeOutput(
                item_id=o.get("item_id", ""),
                item_name=o.get("item_name", ""),
                quantity=_safe_int(o.get("quantity", 1)),
                chance=_safe_float(o.get("chance", 1.0)),
            ) for o in (outputs or [])]
            recipe = Recipe(
                recipe_id=recipe_id, name=name, description=description,
                profession_id=profession_id, category=category,
                required_level=required_level, rarity=rarity,
                ingredients=ings, outputs=outs,
                craft_time_seconds=craft_time_seconds,
                success_chance=success_chance, critical_chance=critical_chance,
                discovery_chance=discovery_chance, skill_xp=skill_xp,
                station_required=station_required,
            )
            self._recipes[recipe_id] = recipe
            self._recipes_by_profession.setdefault(profession_id, []).append(recipe_id)
            self._log_event(ProfessionEventKind.RECIPE_REGISTERED.value, {"recipe_id": recipe_id})
            return True, "registered", recipe

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        with _LOCK:
            return self._recipes.get(recipe_id)

    def list_recipes(self, limit: int = 50, offset: int = 0,
                     profession_id: Optional[str] = None,
                     rarity: Optional[str] = None) -> List[Recipe]:
        with _LOCK:
            items = list(self._recipes.values())
            if profession_id:
                items = [r for r in items if r.profession_id == profession_id]
            if rarity:
                items = [r for r in items if r.rarity == rarity]
            return items[offset:offset + limit]

    # ------------------------------------------------------------------
    # Player profession management
    # ------------------------------------------------------------------

    def learn_profession(self, player_id: str, profession_id: str) -> Tuple[bool, str, Optional[PlayerProfession]]:
        with _LOCK:
            prof = self._professions.get(profession_id)
            if prof is None:
                return False, "profession_not_found", None
            existing = self._player_professions_by_player.get(player_id, [])
            for pid in existing:
                pp = self._player_professions.get(pid)
                if pp and pp.profession_id == profession_id:
                    return False, "already_learned", pp
            if len(existing) >= self._config.max_professions_per_player:
                return False, "max_professions", None
            pp_id = _new_id("pp")
            pp = PlayerProfession(
                pp_id=pp_id, player_id=player_id, profession_id=profession_id,
            )
            self._player_professions[pp_id] = pp
            self._player_professions_by_player.setdefault(player_id, []).append(pp_id)
            self._log_event(ProfessionEventKind.PROFESSION_LEARNED.value,
                            {"player_id": player_id, "profession_id": profession_id})
            return True, "learned", pp

    def get_player_profession(self, pp_id: str) -> Optional[PlayerProfession]:
        with _LOCK:
            return self._player_professions.get(pp_id)

    def list_player_professions(self, player_id: str) -> List[PlayerProfession]:
        with _LOCK:
            ids = self._player_professions_by_player.get(player_id, [])
            return [self._player_professions[pid] for pid in ids if pid in self._player_professions]

    def learn_recipe(self, pp_id: str, recipe_id: str) -> Tuple[bool, str, Optional[PlayerProfession]]:
        with _LOCK:
            pp = self._player_professions.get(pp_id)
            if pp is None:
                return False, "pp_not_found", None
            recipe = self._recipes.get(recipe_id)
            if recipe is None:
                return False, "recipe_not_found", None
            if recipe.profession_id != pp.profession_id:
                return False, "wrong_profession", None
            if recipe_id in pp.known_recipes:
                return False, "already_known", None
            pp.known_recipes.append(recipe_id)
            self._log_event(ProfessionEventKind.RECIPE_LEARNED.value,
                            {"pp_id": pp_id, "recipe_id": recipe_id})
            return True, "learned", pp

    def perform_craft(self, pp_id: str, recipe_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Simulates crafting an item. Returns (success, msg, result_dict)."""
        with _LOCK:
            pp = self._player_professions.get(pp_id)
            if pp is None:
                return False, "pp_not_found", None
            recipe = self._recipes.get(recipe_id)
            if recipe is None:
                return False, "recipe_not_found", None
            if recipe.profession_id != pp.profession_id:
                return False, "wrong_profession", None
            if recipe_id not in pp.known_recipes:
                return False, "recipe_not_known", None
            if pp.level < recipe.required_level:
                return False, "level_too_low", None
            # Determine craft result
            import random
            roll = random.random()
            is_critical = False
            is_discovery = False
            if roll < recipe.success_chance:
                # Success - check for critical
                if self._config.allow_critical_crafts and random.random() < recipe.critical_chance:
                    craft_result = CraftResult.CRITICAL.value
                    is_critical = True
                else:
                    craft_result = CraftResult.SUCCESS.value
            else:
                craft_result = CraftResult.FAILURE.value
            # Check for discovery (only on success)
            if (craft_result != CraftResult.FAILURE.value and
                    self._config.allow_recipe_discovery and
                    random.random() < recipe.discovery_chance):
                is_discovery = True
            # Calculate outputs
            outputs: List[Dict[str, Any]] = []
            if craft_result != CraftResult.FAILURE.value:
                for out in recipe.outputs:
                    qty = out.quantity
                    if is_critical:
                        qty = int(qty * 2)  # Critical doubles output
                    outputs.append({
                        "item_id": out.item_id,
                        "item_name": out.item_name,
                        "quantity": qty,
                        "critical": is_critical,
                    })
            # Update player profession stats
            pp.craft_count += 1
            if craft_result == CraftResult.FAILURE.value:
                pp.failure_count += 1
            elif craft_result == CraftResult.CRITICAL.value:
                pp.critical_count += 1
            if is_discovery:
                pp.discovery_count += 1
            # Award XP
            xp_gain = recipe.skill_xp
            if craft_result == CraftResult.FAILURE.value:
                xp_gain = int(xp_gain * 0.2)  # Minimal XP on failure
            elif craft_result == CraftResult.CRITICAL.value:
                xp_gain = int(xp_gain * 1.5)  # Bonus XP on critical
            pp.experience += xp_gain
            pp.last_crafted_at = _now()
            # Check for level up
            leveled_up = False
            while pp.level < self._professions[pp.profession_id].max_level:
                needed = _xp_for_level(pp.level)
                if pp.experience < needed:
                    break
                pp.experience -= needed
                pp.level += 1
                pp.skill_points += 1
                leveled_up = True
            if leveled_up:
                self._log_event(ProfessionEventKind.PROFESSION_LEVEL_UP.value,
                                {"pp_id": pp_id, "level": pp.level})
            # Record craft
            record = CraftRecord(
                record_id=_new_id("craft"), player_id=pp.player_id,
                profession_id=pp.profession_id, recipe_id=recipe_id,
                result=craft_result, outputs=outputs,
                ingredients_consumed=[_dataclass_to_dict(i) for i in recipe.ingredients],
                xp_gained=xp_gain,
            )
            self._craft_history.append(record)
            _evict_fifo_list(self._craft_history, _MAX_CRAFT_HISTORY)
            self._log_event(ProfessionEventKind.CRAFT_PERFORMED.value,
                            {"record_id": record.record_id, "result": craft_result})
            result_dict = {
                "record_id": record.record_id,
                "result": craft_result,
                "outputs": outputs,
                "xp_gained": xp_gain,
                "leveled_up": leveled_up,
                "new_level": pp.level,
                "critical": is_critical,
                "discovery": is_discovery,
            }
            return True, "crafted", result_dict

    def get_craft_history(self, player_id: Optional[str] = None, limit: int = 50) -> List[CraftRecord]:
        with _LOCK:
            items = self._craft_history
            if player_id:
                items = [c for c in items if c.player_id == player_id]
            return list(reversed(items))[:limit]

    # ------------------------------------------------------------------
    # System management
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            # Regen resources for active player classes
            for player_id, state_id in self._player_active_class.items():
                state = self._player_classes.get(state_id)
                if state and state.status == PlayerClassStatus.ACTIVE.value:
                    cls = self._classes.get(state.class_id)
                    if cls:
                        state.current_resource = min(
                            state.max_resource,
                            state.current_resource + cls.resource_regen,
                        )
            self._log_event(ProfessionEventKind.TICK.value, {"tick": self._tick_count})
            return {"tick_count": self._tick_count}

    def set_config(self, config: Dict[str, Any]) -> ProfessionConfig:
        with _LOCK:
            if "max_player_classes" in config:
                self._config.max_player_classes = _safe_int(config["max_player_classes"], 10)
            if "max_active_classes" in config:
                self._config.max_active_classes = _safe_int(config["max_active_classes"], 1)
            if "max_professions_per_player" in config:
                self._config.max_professions_per_player = _safe_int(config["max_professions_per_player"], 2)
            if "max_recipes_per_profession" in config:
                self._config.max_recipes_per_profession = _safe_int(config["max_recipes_per_profession"], 200)
            if "starting_talent_points" in config:
                self._config.starting_talent_points = _safe_int(config["starting_talent_points"], 0)
            if "talent_points_per_level" in config:
                self._config.talent_points_per_level = _safe_int(config["talent_points_per_level"], 1)
            if "class_switch_cooldown" in config:
                self._config.class_switch_cooldown = _safe_float(config["class_switch_cooldown"], 300.0)
            if "craft_xp_curve_multiplier" in config:
                self._config.craft_xp_curve_multiplier = _safe_float(config["craft_xp_curve_multiplier"], 1.0)
            if "allow_recipe_discovery" in config:
                self._config.allow_recipe_discovery = bool(config["allow_recipe_discovery"])
            if "allow_critical_crafts" in config:
                self._config.allow_critical_crafts = bool(config["allow_critical_crafts"])
            self._log_event(ProfessionEventKind.CONFIG_UPDATED.value, {})
            return self._config

    def get_config(self) -> ProfessionConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 50, kind: Optional[str] = None) -> List[ProfessionEvent]:
        with _LOCK:
            items = self._events
            if kind:
                items = [e for e in items if e.kind == kind]
            return list(reversed(items))[:limit]

    def get_stats(self) -> ProfessionStats:
        with _LOCK:
            return ProfessionStats(
                total_classes=len(self._classes),
                total_abilities=len(self._abilities),
                total_talent_trees=len(self._talent_trees),
                total_player_classes=len(self._player_classes),
                total_professions=len(self._professions),
                total_recipes=len(self._recipes),
                total_player_professions=len(self._player_professions),
                total_crafts=sum(p.craft_count for p in self._player_professions.values()),
                total_critical_crafts=sum(p.critical_count for p in self._player_professions.values()),
                total_discoveries=sum(p.discovery_count for p in self._player_professions.values()),
            )

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            return {
                "initialized": self._initialized,
                "total_classes": len(self._classes),
                "total_abilities": len(self._abilities),
                "total_talent_trees": len(self._talent_trees),
                "total_talent_nodes": len(self._talent_nodes),
                "total_player_classes": len(self._player_classes),
                "total_professions": len(self._professions),
                "total_recipes": len(self._recipes),
                "total_player_professions": len(self._player_professions),
                "total_craft_records": len(self._craft_history),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> ProfessionSnapshot:
        with _LOCK:
            return ProfessionSnapshot(
                classes=[_dataclass_to_dict(c) for c in list(self._classes.values())[:10]],
                professions=[_dataclass_to_dict(p) for p in list(self._professions.values())[:10]],
                player_classes=[_dataclass_to_dict(s) for s in list(self._player_classes.values())[:10]],
                player_professions=[_dataclass_to_dict(p) for p in list(self._player_professions.values())[:10]],
                recipes=[_dataclass_to_dict(r) for r in list(self._recipes.values())[:10]],
            )

    def reset(self) -> None:
        with _LOCK:
            self._init_state()
            self._seed()
            self._initialized = True
            self._log_event(ProfessionEventKind.RESET.value, {})


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_system_instance: Optional[ProfessionClassSystem] = None
_factory_lock = threading.Lock()


def get_profession_class_system() -> ProfessionClassSystem:
    global _system_instance
    if _system_instance is None:
        with _factory_lock:
            if _system_instance is None:
                _system_instance = ProfessionClassSystem()
    return _system_instance


def reset_profession_class_system() -> None:
    global _system_instance
    with _factory_lock:
        _system_instance = None
